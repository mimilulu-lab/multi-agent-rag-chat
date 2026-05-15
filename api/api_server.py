#!/usr/bin/env python3
"""
FastAPI 后端 - MsgHub 多 Agent RPG 系统
每个 Agent 独立配置模型和 API
"""
import os
import sys
import uuid
import asyncio
import traceback
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import subprocess
import argparse
import json

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Agent 系统
from agents import ChatAgent, ManagerAgent, WorkerAgent
from agentscope.message import Msg
from agentscope.pipeline import MsgHub
from config.agents_config import agents_config_manager, AgentConfig
from config.manager_config import manager_config_manager
from api.agents_api import router as agents_router
from api.providers_api import router as providers_router
from api.tools_api import router as tools_router
from api.manager_api import router as manager_router
from api.knowledge_base_api import router as kb_router
from api.conversation_api import router as conversation_router
from api.conversation_store import get_conversation_store, ChatMessageRecord
import time

# ============== 全局状态 ==============
system_state = {
    "initialized": False,
    "agents": [],  # Agent 实例列表 (兼容模式)
    "manager": None,  # Manager Agent 实例
    "workers": [],  # Worker Agent 列表
    "use_manager_mode": False,  # 是否使用Manager-Worker模式
    "msghub": None,  # MsgHub 实例
}

# ============== 命令行参数 ==============
parser = argparse.ArgumentParser(description="RPG Chat API Server")
parser.add_argument(
    "--dev",
    action="store_true",
    help="开发模式：不构建前端，仅提供 API 服务"
)
parser.add_argument(
    "--build",
    action="store_true",
    help="构建前端后启动（生产模式）"
)
args, _ = parser.parse_known_args()  # parse_known_args 忽略 uvicorn 等未知参数，避免直接启动时崩溃

# 默认生产模式（构建前端）
DEV_MODE = args.dev
BUILD_FRONTEND = args.build or not args.dev

# ============== 数据模型 ==============

class ChatRequest(BaseModel):
    message: str
    agent_id: Optional[str] = None  # 指定与哪个 Agent 对话
    conversation_id: Optional[str] = None  # 关联的历史会话ID


class AgentResponse(BaseModel):
    agent_name: str
    agent_role: str
    content: str


class ChatResponse(BaseModel):
    responses: List[AgentResponse]


class AgentInfo(BaseModel):
    id: str
    name: str
    role: str
    personality: str
    avatar_type: str


class AgentListResponse(BaseModel):
    agents: List[AgentInfo]


class StreamChunk(BaseModel):
    """流式响应数据块"""
    type: str  # start, agent_start, chunk, done, agent_done, all_done, error
    agent_name: Optional[str] = None
    agent_role: Optional[str] = None
    content: Optional[str] = None
    index: Optional[int] = None
    message: Optional[str] = None


# ============== 会话持久化辅助函数 ==============

def _get_or_create_conversation(request: ChatRequest) -> Optional[str]:
    """获取或创建会话，返回 conversation_id"""
    store = get_conversation_store()

    if request.conversation_id:
        conv = store.get_conversation(request.conversation_id)
        if conv:
            return conv.conversation_id

    # 自动创建新会话，标题取消息前20字
    title = request.message.strip()[:20] or "新对话"
    if len(request.message.strip()) > 20:
        title += "..."

    conversation = store.create_conversation(
        title=title,
        agent_id=request.agent_id,
    )
    return conversation.conversation_id


def _persist_chat_message(
    conversation_id: str,
    role: str,
    content: str,
    agent_name: Optional[str] = None,
    agent_role: Optional[str] = None,
):
    """持久化单条聊天消息"""
    store = get_conversation_store()
    store.append_message(
        conversation_id,
        ChatMessageRecord(
            id=f"msg_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}",
            role=role,
            content=content,
            timestamp=time.time(),
            agent_name=agent_name,
            agent_role=agent_role,
        )
    )


# ============== 前端构建 ==============

def build_frontend():
    """构建前端静态文件"""
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "rpg-frontend")
    dist_dir = os.path.join(frontend_dir, "dist")

    # 如果已经构建过，跳过
    if os.path.exists(dist_dir) and os.path.exists(os.path.join(dist_dir, "index.html")):
        print("📦 前端已构建，跳过构建步骤")
        return dist_dir

    # 检查是否有 node_modules
    if not os.path.exists(os.path.join(frontend_dir, "node_modules")):
        print("📦 安装前端依赖...")
        try:
            subprocess.run(
                ["npm", "install"],
                cwd=frontend_dir,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"⚠️ 前端依赖安装失败: {e}")
            return None
        except FileNotFoundError:
            print("⚠️ 未找到 npm，请安装 Node.js")
            return None

    print("🔨 构建前端...")
    try:
        subprocess.run(
            ["npm", "run", "build"],
            cwd=frontend_dir,
            check=True,
            capture_output=True,
        )
        print("✅ 前端构建完成")
        return dist_dir
    except subprocess.CalledProcessError as e:
        print(f"⚠️ 前端构建失败: {e}")
        return None


# ============== 生命周期管理 ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    print("🚀 正在初始化多 Agent 系统...")
    await init_system()

    # 仅在非开发模式下构建前端
    if BUILD_FRONTEND:
        dist_dir = build_frontend()
        if dist_dir:
            print(f"📦 前端资源路径: {dist_dir}")
            setup_static_files()
    else:
        print("🔧 开发模式：不构建前端，仅提供 API 服务")
        print("   请运行: cd rpg-frontend && npm run dev")

    yield

    # 关闭时清理
    print("🛑 正在关闭系统...")


async def init_system():
    """初始化多 Agent 系统 - 支持 Manager-Worker 模式"""
    print("🚀 Initializing multi-agent system...")

    if system_state["initialized"]:
        print("   System already initialized, skipping...")
        return

    # 重置状态
    system_state["agents"] = []
    system_state["manager"] = None
    system_state["workers"] = []
    system_state["use_manager_mode"] = False

    # 获取 Manager 配置
    manager_config = manager_config_manager.get_config()

    # 获取 Worker Agent 配置
    worker_configs = agents_config_manager.get_active_agents()
    print(f"   Found {len(worker_configs)} active worker configs")
    print(f"   Manager config: is_active={manager_config.is_active}, provider_id={manager_config.provider_id}")

    # 如果 Manager 已启用且配置了 Provider，使用 Manager-Worker 模式
    if manager_config.is_active and manager_config.provider_id:
        system_state["use_manager_mode"] = True
        await _init_manager_worker_mode(manager_config, worker_configs)
    else:
        # 使用传统 MsgHub 模式
        system_state["use_manager_mode"] = False
        await _init_msghub_mode(worker_configs)

    system_state["initialized"] = True
    print("✅ 多 Agent 系统初始化完成")


async def _init_manager_worker_mode(manager_config: Any, worker_configs: List[AgentConfig]):
    """初始化 Manager-Worker 模式"""
    print("🔧 使用 Manager-Worker 协作模式")

    from providers import provider_manager

    # 创建 Manager
    provider = provider_manager.get_provider(manager_config.provider_id)

    if provider and provider.api_key:
        try:
            llm_config = manager_config.to_llm_config()
            print(f"👔 创建 Manager: {manager_config.name}")

            manager = ManagerAgent(
                name=manager_config.name,
                role=manager_config.role,
                personality=manager_config.personality,
                llm_config=llm_config,
                kb_id=manager_config.kb_id if manager_config.kb_id else None,
            )
            system_state["manager"] = manager
        except Exception as e:
            print(f"⚠️ 创建 Manager {manager_config.name} 失败: {e}")

    # 创建 Workers
    workers = []
    for config in worker_configs:
        provider = provider_manager.get_provider(config.provider_id)
        if not provider or not provider.api_key:
            print(f"⚠️ Worker {config.name} 配置不完整，跳过")
            continue

        try:
            llm_config = config.to_llm_config()
            print(f"🛠️  创建 Worker: {config.name} ({config.specialty})")

            worker = WorkerAgent(
                name=config.name,
                role=config.role,
                personality=config.personality,
                specialty=config.specialty or "通用任务",
                expertise=config.expertise or config.role,
                llm_config=llm_config,
                kb_id=config.kb_id if config.kb_id else None,
            )
            worker.id = config.id  # 保存配置ID用于前端匹配
            workers.append(worker)
        except Exception as e:
            print(f"⚠️ 创建 Worker {config.name} 失败: {e}")
            continue

    # 注册 Workers 到 Manager
    if system_state["manager"]:
        for worker in workers:
            system_state["manager"].register_worker(worker)

    system_state["workers"] = workers

    # 将 Manager 也放入 agents 列表用于前端显示
    if system_state["manager"]:
        system_state["agents"] = [system_state["manager"]] + workers

    print(f"✅ Manager-Worker 模式就绪: 1 Manager, {len(workers)} Workers")


async def _init_msghub_mode(worker_configs: List[AgentConfig]):
    """初始化传统 MsgHub 模式"""
    print("🔧 使用传统 MsgHub 协作模式")

    agents = []
    for config in worker_configs:
        from providers import provider_manager
        provider = provider_manager.get_provider(config.provider_id)
        if not provider:
            print(f"⚠️ Agent {config.name} 的 Provider {config.provider_id} 不存在，跳过")
            continue

        if not provider.api_key:
            print(f"⚠️ Agent {config.name} 的 Provider 未配置 API Key，跳过")
            continue

        try:
            llm_config = config.to_llm_config()
            print(f"🤖 创建 Agent: {config.name} ({config.role}) - 使用模型 {provider.model_id}")

            agent = ChatAgent(
                name=config.name,
                role=config.role,
                personality=config.personality,
                llm_config=llm_config,
            )
            agents.append(agent)
        except Exception as e:
            print(f"⚠️ 创建 Agent {config.name} 失败: {e}")
            continue

    system_state["agents"] = agents

    print(f"✅ 已创建 {len(agents)} 个 Agent:")
    for agent in agents:
        print(f"   - {agent.name} ({agent.role})")


# ============== FastAPI 应用 ==============

app = FastAPI(
    title="RPG Chat API",
    description="MsgHub 多 Agent RPG 系统 API - 每个 Agent 独立配置",
    version="0.3.0",
    lifespan=lifespan,
)

# CORS 配置
ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"] if BUILD_FRONTEND else ["*"]
if DEV_MODE:
    ALLOWED_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加 Agent 配置路由
app.include_router(agents_router)

# 添加 Provider 配置路由
app.include_router(providers_router)

# 添加工具管理路由
app.include_router(tools_router)

# 添加 Manager 配置路由
app.include_router(manager_router)

# 添加知识库管理路由
app.include_router(kb_router)

# 添加会话管理路由
app.include_router(conversation_router)


# ============== API 端点 ==============

@app.get("/api/agents", response_model=AgentListResponse)
async def list_agents():
    """获取所有启用的 Agent 信息（包含 Manager）"""
    from config.manager_config import manager_config_manager

    # 获取 Worker Agents
    worker_agents = agents_config_manager.get_active_agents()

    # 获取 Manager 配置
    manager_config = manager_config_manager.get_config()

    result_agents = []

    # 如果 Manager 已启用，添加到列表
    if manager_config.is_active and manager_config.provider_id:
        result_agents.append(AgentInfo(
            id="manager_default",
            name=manager_config.name,
            role=manager_config.role,
            personality=manager_config.personality,
            avatar_type="manager"
        ))

    # 添加 Worker Agents
    for a in worker_agents:
        result_agents.append(AgentInfo(
            id=a.id,
            name=a.name,
            role=a.role,
            personality=a.personality,
            avatar_type=a.avatar_type
        ))

    return AgentListResponse(agents=result_agents)


@app.post("/api/system/reinitialize")
async def reinitialize():
    """重新初始化系统"""
    try:
        print("🔄 Reinitializing system...")
        # 重置所有系统状态
        system_state["initialized"] = False
        system_state["agents"] = []
        system_state["manager"] = None
        system_state["workers"] = []
        system_state["use_manager_mode"] = False

        # 重新加载 Provider 和 Agent 配置
        print("📋 Reloading configs...")
        from providers import provider_manager
        from config.manager_config import manager_config_manager
        provider_manager._load_config()
        agents_config_manager._load_config()
        manager_config_manager._load_config()

        await init_system()

        agent_count = len(system_state["agents"])
        print(f"✅ System reinitialized with {agent_count} agents")

        return {
            "success": True,
            "message": "系统已重新初始化",
            "agent_count": agent_count,
        }
    except Exception as e:
        print(f"❌ Reinitialization failed: {e}")
        raise HTTPException(status_code=500, detail=f"重新初始化失败: {str(e)}")


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """聊天接口 - 支持 Manager-Worker 和 MsgHub 两种模式"""
    if not system_state["initialized"]:
        raise HTTPException(status_code=503, detail="系统未初始化")

    try:
        # 获取或创建会话
        conversation_id = _get_or_create_conversation(request)
        _persist_chat_message(conversation_id, "user", request.message)

        # 根据模式选择处理方式
        if system_state["use_manager_mode"] and system_state["manager"]:
            response = await _chat_with_manager(request)
        else:
            response = await _chat_with_msghub(request)

        # 持久化助手回复
        for resp in response.responses:
            _persist_chat_message(
                conversation_id,
                "assistant",
                resp.content,
                agent_name=resp.agent_name,
                agent_role=resp.agent_role,
            )

        return response

    except Exception as e:
        print(f"❌ 对话失败: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"对话失败: {str(e)}")


async def _chat_with_manager(request: ChatRequest) -> ChatResponse:
    """使用 Manager-Worker 模式处理对话"""
    manager = system_state["manager"]

    user_msg = Msg(name="User", content=request.message, role="user")

    # Manager 分析任务并分派给 Workers
    response = await manager.reply(user_msg)

    # 提取响应内容
    content = response.content
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                texts.append(item["text"])
            elif isinstance(item, str):
                texts.append(item)
        answer = "\n".join(texts)
    elif isinstance(content, dict):
        answer = content.get("text", str(content))
    else:
        answer = str(content)

    # 获取任务执行详情（如果有）
    task_details = []
    if manager._task_history:
        latest_task = manager._task_history[-1]
        if latest_task.status == "completed":
            for step in latest_task.steps:
                result = latest_task.results.get(step["step_id"], {})
                if result.get("status") == "completed":
                    task_details.append(AgentResponse(
                        agent_name=step.get("agent_name", "Unknown"),
                        agent_role=f"执行: {step.get('task', '')[:20]}...",
                        content=str(result.get("result", ""))[:200]
                    ))

    responses = [
        AgentResponse(
            agent_name=manager.name,
            agent_role=manager.role,
            content=answer,
        )
    ]

    # 添加任务执行详情
    responses.extend(task_details)

    return ChatResponse(responses=responses)


async def _chat_with_msghub(request: ChatRequest) -> ChatResponse:
    """使用传统 MsgHub 模式处理对话"""
    agents = system_state["agents"]
    if not agents:
        raise HTTPException(status_code=400, detail="未配置任何可用的 Agent")

    responses = []

    async with MsgHub(participants=agents, enable_auto_broadcast=True):
        # 让第一个 Agent 主导对话
        primary_agent = agents[0]
        user_msg = Msg(name="User", content=request.message, role="user")
        response = await primary_agent(user_msg)

        # 提取响应内容
        content = response.content
        if isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    texts.append(item["text"])
                elif isinstance(item, str):
                    texts.append(item)
            answer = "\n".join(texts)
        elif isinstance(content, dict):
            answer = content.get("text", str(content))
        else:
            answer = str(content)

        responses.append(AgentResponse(
            agent_name=primary_agent.name,
            agent_role=primary_agent.role,
            content=answer,
        ))

        # 其他 Agent 也参与对话
        for agent in agents[1:]:
            agent_msg = Msg(name="User", content=request.message, role="user")
            agent_response = await agent(agent_msg)

            content = agent_response.content
            if isinstance(content, list):
                texts = []
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        texts.append(item["text"])
                    elif isinstance(item, str):
                        texts.append(item)
                answer = "\n".join(texts)
            elif isinstance(content, dict):
                answer = content.get("text", str(content))
            else:
                answer = str(content)

            responses.append(AgentResponse(
                agent_name=agent.name,
                agent_role=agent.role,
                content=answer,
            ))

    return ChatResponse(responses=responses)


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """流式聊天接口 - 使用 Server-Sent Events"""
    if not system_state["initialized"]:
        raise HTTPException(status_code=503, detail="系统未初始化")

    async def generate_stream():
        """生成流式响应"""
        conversation_id = None
        try:
            # 获取或创建会话，并记录用户消息
            conversation_id = _get_or_create_conversation(request)
            _persist_chat_message(conversation_id, "user", request.message)

            # 如果指定了 agent_id，直接与该 Worker 对话
            if request.agent_id and request.agent_id != "manager_default":
                worker = None
                for w in system_state.get("workers", []):
                    if getattr(w, 'id', None) == request.agent_id:
                        worker = w
                        break

                if worker:
                    user_msg = Msg(name="User", content=request.message, role="user")

                    # 发送开始事件
                    yield f"data: {json.dumps({'type': 'start', 'agent_name': worker.name, 'agent_role': worker.role, 'index': 0})}\n\n"

                    # 调用 Worker
                    response = await worker.reply(user_msg)
                    content = response.content
                    if isinstance(content, list):
                        texts = [item.get("text", "") if isinstance(item, dict) else str(item) for item in content]
                        answer = "\n".join(texts)
                    elif isinstance(content, dict):
                        answer = content.get("text", str(content))
                    else:
                        answer = str(content)

                    # 流式输出
                    chunk_size = 10
                    for i in range(0, len(answer), chunk_size):
                        chunk = answer[i:i + chunk_size]
                        yield f"data: {json.dumps({'type': 'chunk', 'content': chunk, 'agent_name': worker.name, 'index': 0})}\n\n"
                        await asyncio.sleep(0.05)

                    # 持久化助手回复
                    if conversation_id:
                        _persist_chat_message(
                            conversation_id, "assistant", answer,
                            agent_name=worker.name, agent_role=worker.role
                        )

                    # 发送完成事件
                    yield f"data: {json.dumps({'type': 'done', 'agent_name': worker.name, 'index': 0})}\n\n"
                    yield f"data: {json.dumps({'type': 'all_done'})}\n\n"
                    return
                else:
                    yield f"data: {json.dumps({'type': 'error', 'message': f'Worker {request.agent_id} 未找到'})}\n\n"
                    return

            if system_state["use_manager_mode"] and system_state["manager"]:
                # Manager-Worker 模式流式输出
                manager = system_state["manager"]
                user_msg = Msg(name="User", content=request.message, role="user")

                # 发送开始事件
                yield f"data: {json.dumps({'type': 'start', 'agent_name': manager.name, 'agent_role': manager.role, 'index': 0})}\n\n"

                # 调用 Manager（目前先模拟流式，将完整响应分段发送）
                response = await manager.reply(user_msg)
                content = response.content
                if isinstance(content, list):
                    texts = [item.get("text", "") if isinstance(item, dict) else str(item) for item in content]
                    answer = "\n".join(texts)
                elif isinstance(content, dict):
                    answer = content.get("text", str(content))
                else:
                    answer = str(content)

                # 模拟流式输出：每 10 个字符发送一次
                chunk_size = 10
                for i in range(0, len(answer), chunk_size):
                    chunk = answer[i:i + chunk_size]
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk, 'agent_name': manager.name, 'index': 0})}\n\n"
                    await asyncio.sleep(0.05)  # 模拟打字延迟

                # 持久化助手回复
                if conversation_id:
                    _persist_chat_message(
                        conversation_id, "assistant", answer,
                        agent_name=manager.name, agent_role=manager.role
                    )

                # 发送完成事件
                yield f"data: {json.dumps({'type': 'done', 'agent_name': manager.name, 'index': 0})}\n\n"

                # 发送全部完成事件
                yield f"data: {json.dumps({'type': 'all_done'})}\n\n"

            else:
                # MsgHub 模式 - 支持多 Agent 流式输出
                agents = system_state["agents"]
                if not agents:
                    yield f"data: {json.dumps({'type': 'error', 'message': '未配置任何可用的 Agent'})}\n\n"
                    return

                async with MsgHub(participants=agents, enable_auto_broadcast=True):
                    for idx, agent in enumerate(agents):
                        user_msg = Msg(name="User", content=request.message, role="user")

                        # 发送 Agent 开始事件
                        yield f"data: {json.dumps({'type': 'agent_start', 'agent_name': agent.name, 'agent_role': agent.role, 'index': idx})}\n\n"

                        # 获取响应
                        response = await agent(user_msg)
                        content = response.content
                        if isinstance(content, list):
                            texts = [item.get("text", "") if isinstance(item, dict) else str(item) for item in content]
                            answer = "\n".join(texts)
                        elif isinstance(content, dict):
                            answer = content.get("text", str(content))
                        else:
                            answer = str(content)

                        # 流式输出内容
                        chunk_size = 8
                        for i in range(0, len(answer), chunk_size):
                            chunk = answer[i:i + chunk_size]
                            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk, 'agent_name': agent.name, 'index': idx})}\n\n"
                            await asyncio.sleep(0.03)

                        # 持久化助手回复
                        if conversation_id:
                            _persist_chat_message(
                                conversation_id, "assistant", answer,
                                agent_name=agent.name, agent_role=agent.role
                            )

                        # 发送 Agent 完成事件
                        yield f"data: {json.dumps({'type': 'agent_done', 'agent_name': agent.name, 'index': idx})}\n\n"

                        # Agent 之间的延迟
                        if idx < len(agents) - 1:
                            await asyncio.sleep(0.5)

                # 发送全部完成事件
                yield f"data: {json.dumps({'type': 'all_done'})}\n\n"

        except Exception as e:
            error_msg = f"流式输出错误: {str(e)}"
            print(f"❌ {error_msg}")
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "initialized": system_state["initialized"],
        "agent_count": len(system_state.get("agents", [])),
        "mode": "manager-worker" if system_state.get("use_manager_mode") else "msghub",
        "manager": system_state["manager"].name if system_state.get("manager") else None,
        "worker_count": len(system_state.get("workers", [])),
    }


# ============== 静态文件服务 ==============

def setup_static_files():
    """配置静态文件服务"""
    dist_dir = os.path.join(os.path.dirname(__file__), "..", "rpg-frontend", "dist")

    if os.path.exists(dist_dir):
        app.mount("/assets", StaticFiles(directory=os.path.join(dist_dir, "assets")), name="assets")

        @app.get("/")
        async def serve_index():
            return FileResponse(os.path.join(dist_dir, "index.html"))

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="Not Found")

            index_file = os.path.join(dist_dir, "index.html")
            if os.path.exists(index_file):
                return FileResponse(index_file)
            raise HTTPException(status_code=404, detail="Frontend not built")

        print(f"📦 静态文件服务已配置: {dist_dir}")
    else:
        print("⚠️ 前端未构建，运行开发模式")


# ============== 主入口 ==============

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

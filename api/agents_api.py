# -*- coding: utf-8 -*-
"""API routes for agents configuration."""

from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config.agents_config import agents_config_manager, AgentConfig

router = APIRouter(prefix="/api/agents-config", tags=["agents-config"])


class CreateAgentRequest(BaseModel):
    """创建 Worker Agent 请求 - 引用 Provider"""
    name: str = Field(..., description="Agent 名称")
    role: str = Field(..., description="Agent 角色")
    personality: str = Field(..., description="Agent 性格描述")
    avatar_type: Optional[str] = Field(default=None, description="头像类型: aiden 或 wrench，不传则随机分配")
    provider_id: str = Field(..., description="关联的 Provider ID")
    kb_id: Optional[str] = Field(default=None, description="关联的知识库 ID")
    specialty: str = Field(default="通用任务", description="专业领域")
    expertise: str = Field(default="", description="具体专长描述")


class UpdateAgentRequest(BaseModel):
    """更新 Worker Agent 请求 - 引用 Provider"""
    name: Optional[str] = Field(default=None)
    role: Optional[str] = Field(default=None)
    personality: Optional[str] = Field(default=None)
    avatar_type: Optional[str] = Field(default=None)
    provider_id: Optional[str] = Field(default=None, description="关联的 Provider ID")
    kb_id: Optional[str] = Field(default=None, description="关联的知识库 ID")
    specialty: Optional[str] = Field(default=None, description="专业领域")
    expertise: Optional[str] = Field(default=None, description="具体专长描述")
    is_active: Optional[bool] = Field(default=None)


class TestConnectionResponse(BaseModel):
    """连接测试响应"""
    success: bool
    message: str


@router.get("")
async def list_agents(include_inactive: bool = False):
    """获取所有 Agent 配置（包含 Manager）"""
    from config.manager_config import manager_config_manager

    agents = agents_config_manager.list_agents(include_inactive=include_inactive)

    # 添加 Manager 配置作为特殊 Agent
    manager_info = manager_config_manager.to_info()

    print(f"📋 API list_agents called, include_inactive={include_inactive}, found {len(agents)} workers, manager_active={manager_info['is_active']}")

    # 将 Manager 放在列表最前面
    all_agents = [manager_info] + [agent.to_info(mask_secret=True) for agent in agents]

    return {
        "agents": all_agents
    }


@router.post("")
async def create_agent(request: CreateAgentRequest):
    """创建新 Agent"""
    try:
        print(f"📝 Creating agent: {request.name}")
        agent = agents_config_manager.create_agent(request.model_dump())
        print(f"✅ Agent created: {agent.id}, is_active={agent.is_active}")
        return agent.to_info(mask_secret=True)
    except ValueError as e:
        print(f"❌ Failed to create agent: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    """获取单个 Agent 配置"""
    agent = agents_config_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent.to_info(mask_secret=True)


@router.put("/{agent_id}")
async def update_agent(agent_id: str, request: UpdateAgentRequest):
    """更新 Agent 配置"""
    update_data = {k: v for k, v in request.model_dump().items() if v is not None}
    agent = agents_config_manager.update_agent(agent_id, update_data)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent.to_info(mask_secret=True)


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str):
    """删除 Agent"""
    success = agents_config_manager.delete_agent(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"success": True}


@router.post("/{agent_id}/test")
async def test_agent_connection(agent_id: str):
    """测试 Agent 的模型连接"""
    agent = agents_config_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # 通过 provider_id 获取 Provider 信息
    from providers import provider_manager
    provider = provider_manager.get_provider(agent.provider_id)
    if not provider:
        raise HTTPException(status_code=400, detail=f"Provider {agent.provider_id} not found")

    # 导入测试连接函数
    from providers import test_model_connection

    success, message = await test_model_connection(
        provider_type=provider.provider_type,
        api_key=provider.api_key,
        model_id=provider.model_id,
        base_url=provider.base_url if provider.base_url else None
    )

    return TestConnectionResponse(success=success, message=message)


class TestConnectionRequest(BaseModel):
    """临时测试连接请求"""
    provider_type: str = Field(..., description="提供商类型: dashscope/anthropic/openai/custom")
    api_key: str = Field(..., description="API key")
    model_id: str = Field(..., description="模型ID")
    base_url: str = Field(default="", description="Base URL (可选)")


@router.post("/test-connection")
async def test_connection_temp(request: TestConnectionRequest):
    """临时测试连接（不保存配置）"""
    from providers import test_model_connection

    success, message = await test_model_connection(
        provider_type=request.provider_type,
        api_key=request.api_key,
        model_id=request.model_id,
        base_url=request.base_url if request.base_url else None
    )

    return TestConnectionResponse(success=success, message=message)


@router.get("/provider-types")
async def get_provider_types():
    """获取支持的提供商类型"""
    return {
        "types": [
            {
                "id": "dashscope",
                "name": "阿里云 DashScope",
                "description": "阿里云大模型服务平台",
                "required_fields": ["api_key", "model_id"],
                "optional_fields": [],
                "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            },
            {
                "id": "anthropic",
                "name": "Anthropic 协议",
                "description": "支持 Anthropic Claude API 协议的模型",
                "required_fields": ["api_key", "base_url", "model_id"],
                "optional_fields": [],
            },
            {
                "id": "openai",
                "name": "OpenAI",
                "description": "OpenAI 官方 API",
                "required_fields": ["api_key", "model_id"],
                "optional_fields": ["base_url"],
            },
            {
                "id": "custom",
                "name": "自定义 OpenAI 兼容",
                "description": "任何 OpenAI 兼容的 API 服务",
                "required_fields": ["api_key", "base_url", "model_id"],
                "optional_fields": [],
            },
        ]
    }


@router.get("/provider-models")
async def get_provider_models():
    """获取推荐的模型列表 - 从providers目录动态获取"""
    # 从providers目录导入模型配置
    from providers import DashScopeProvider, AnthropicProvider

    # DashScope 模型列表
    dashscope_models = [
        {"id": "qwen-max", "name": "通义千问 Max", "description": "最强性能"},
        {"id": "qwen-plus", "name": "通义千问 Plus", "description": "均衡选择"},
        {"id": "qwen-turbo", "name": "通义千问 Turbo", "description": "快速经济"},
        {"id": "qwen3.5-flash", "name": "通义千问3.5 Flash", "description": "轻量快速"},
    ]

    # Anthropic 协议模型列表
    anthropic_models = [
        {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "description": "最强性能"},
        {"id": "claude-3-sonnet-20240229", "name": "Claude 3 Sonnet", "description": "均衡选择"},
        {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku", "description": "快速经济"},
    ]

    # OpenAI 官方模型列表
    openai_models = [
        {"id": "gpt-4o", "name": "GPT-4o", "description": "最强性能"},
        {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "description": "高性能"},
        {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "description": "经济选择"},
    ]

    # 自定义模型 - 用户自己输入
    custom_models = [
        {"id": "custom", "name": "自定义模型", "description": "输入任意模型ID"},
    ]

    return {
        "models": {
            "dashscope": dashscope_models,
            "anthropic": anthropic_models,
            "openai": openai_models,
            "custom": custom_models,
        }
    }

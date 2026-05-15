"""
管理者智能体 - 负责任务分析、规划和分派
基于 AgentScope 实现 Manager-Worker 协作模式
"""
from typing import Optional, Dict, Any, List, Callable
import json
import uuid
import asyncio
import openai
from agentscope.agent import AgentBase
from agentscope.message import Msg

from tools import get_toolkit


class TaskPlan:
    """任务计划"""
    def __init__(self, task_id: str, description: str, steps: List[Dict]):
        self.task_id = task_id
        self.description = description
        self.steps = steps  # 每个步骤包含: agent_name, action, input
        self.results = {}   # 存储每个步骤的结果
        self.status = "pending"  # pending, running, completed, failed

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "steps": self.steps,
            "results": self.results,
            "status": self.status
        }


class ManagerAgent(AgentBase):
    """
    管理者智能体 - 任务协调中心

    职责:
    1. 分析用户请求，拆解为子任务
    2. 根据Worker能力分派任务
    3. 收集Worker结果，整合回复
    4. 管理任务执行顺序和依赖
    """

    def __init__(
        self,
        name: str = "任务管理器",
        role: str = "项目协调经理",
        personality: str = "专业、有条理、善于规划和协调，能够准确分析需求并合理分配任务",
        model_name: str = "qwen-max",
        api_key: Optional[str] = None,
        llm_config: Optional[Dict[str, Any]] = None,
        kb_id: Optional[str] = None,  # 关联的知识库ID
    ):
        super().__init__()
        self.name = name
        self.role = role
        self.personality = personality
        self.kb_id = kb_id  # 知识库ID

        # 初始化模型
        if llm_config:
            self.provider = llm_config.get("provider", "dashscope")
            self.model_name = llm_config.get("model_id", model_name)
            self.api_key = llm_config.get("api_key") or api_key
            raw_base_url = llm_config.get("base_url")
            self.base_url = raw_base_url if self.provider != "dashscope" else None
        else:
            self.provider = "dashscope"
            self.model_name = model_name
            self.api_key = api_key
            self.base_url = None

        self._openai_client = None  # 直接 OpenAI 客户端
        self.model = self._create_model()

        # Worker注册表
        self._workers: Dict[str, 'WorkerAgent'] = {}

        # 任务历史
        self._task_history: List[TaskPlan] = []

        # RAG 知识库引用
        self._kb = None
        if kb_id:
            try:
                from rag_knowledge_base import KnowledgeBaseManager
                kb_manager = KnowledgeBaseManager()
                self._kb = kb_manager.load_knowledge_base(kb_id)
                if self._kb:
                    print(f"✅ Manager 已关联知识库: {kb_id}")
                else:
                    print(f"⚠️ Manager 关联知识库失败: {kb_id} 不存在")
            except Exception as e:
                print(f"⚠️ Manager 加载知识库失败: {e}")

    def _create_model(self):
        """创建 OpenAI 客户端 - 直接使用 openai 库"""
        # 确定 base_url
        if self.provider == "dashscope":
            base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        elif self.provider == "kimi":
            base_url = "https://api.moonshot.cn/v1"
        else:
            base_url = self.base_url

        # 创建 AsyncOpenAI 客户端
        self._openai_client = openai.AsyncOpenAI(
            api_key=self.api_key,
            base_url=base_url
        )

        return self._openai_client

    def register_worker(self, worker: 'WorkerAgent'):
        """注册Worker Agent（以 worker.id 为键）"""
        self._workers[worker.id] = worker
        worker.set_manager(self)  # 告诉Worker谁是Manager
        print(f"✅ Manager 注册 Worker: {worker.name} (id={worker.id}, 专长={worker.specialty})")

    def get_worker_capabilities(self) -> str:
        """获取所有Worker的能力描述（含 id，供任务规划时引用）"""
        capabilities = []
        for wid, worker in self._workers.items():
            capabilities.append(
                f"- agent_id: {wid}, name: {worker.name}\n  专长: {worker.expertise}"
            )
        return "\n".join(capabilities)

    def _extract_text_from_response(self, content) -> str:
        """从模型响应中提取文本内容"""
        if isinstance(content, list):
            # 查找 type='text' 的元素
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    return item.get("text", "")
            # 如果没找到，取第一个字典的 text 字段或字符串表示
            if content:
                first = content[0]
                if isinstance(first, dict):
                    return first.get("text", str(first))
                return str(first)
            return ""
        elif isinstance(content, dict):
            return content.get("text", str(content))
        else:
            return str(content)

    async def reply(self, msg: Msg) -> Msg:
        """
        处理用户请求 - Manager的核心逻辑

        流程:
        1. 分析请求，理解意图
        2. 拆解为子任务
        3. 分派给合适的Worker
        4. 收集结果并整合
        """
        user_content = msg.content
        print(f"\n{'='*60}")
        print(f"🎯 [Manager] 收到用户请求: {user_content[:50]}...")
        print(f"{'='*60}")

        # 步骤1: 分析请求并制定计划
        print(f"\n📋 [Manager] 步骤1: 分析请求并制定计划...")
        task_plan = await self._create_task_plan(user_content)

        if not task_plan.steps:
            # 不需要分派，自己处理
            print(f"✅ [Manager] 判断: 不需要分派，直接处理")
            return await self._handle_directly(msg)

        print(f"✅ [Manager] 任务计划创建完成:")
        print(f"   任务ID: {task_plan.task_id}")
        print(f"   步骤数: {len(task_plan.steps)}")
        for i, step in enumerate(task_plan.steps, 1):
            print(f"   步骤{i}: {step.get('agent_name')} -> {step.get('task', '')[:30]}...")

        # 步骤2: 执行计划，分派任务
        print(f"\n🚀 [Manager] 步骤2: 开始分派任务...")
        await self._execute_plan(task_plan)

        # 步骤3: 整合结果
        print(f"\n🔀 [Manager] 步骤3: 整合所有Worker结果...")
        final_response = await self._integrate_results(task_plan)

        print(f"\n✅ [Manager] 任务完成，返回最终回复")
        print(f"{'='*60}\n")

        return Msg(
            name=self.name,
            content=final_response,
            role="assistant"
        )

    async def _create_task_plan(self, user_request: str) -> TaskPlan:
        """分析用户请求，创建任务执行计划"""

        system_prompt = f"""你是{self.name}，{self.role}。

你的团队成员及其专长：
{self.get_worker_capabilities()}

请分析用户的请求，判断是否需要分派给团队成员：
1. 如果请求简单，直接回复 "DIRECT"，不需要分派
2. 如果需要多个步骤或不同专长，制定分派计划

请以JSON格式回复（注意：agent_id 必须使用上面列出的 agent_id 值）：
{{
    "need_dispatch": true/false,
    "reason": "为什么需要/不需要分派",
    "steps": [
        {{
            "step_id": 1,
            "agent_id": "上面列出的 agent_id",
            "agent_name": "Agent显示名称（仅供参考）",
            "task": "具体任务描述",
            "input": "需要传递给Agent的输入",
            "depends_on": []
        }}
    ]
}}
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_request}
        ]

        # 最多重试 2 次
        plan_data = None
        for attempt in range(2):
            content = await self._call_llm(messages)
            print(f"\n🤔 [Manager] AI规划思考 (attempt {attempt+1}):\n{content[:500]}...")
            try:
                json_str = self._extract_json(content)
                plan_data = json.loads(json_str)
                break  # 解析成功，跳出重试循环
            except Exception as e:
                print(f"   ⚠️ JSON 解析失败 (attempt {attempt+1}): {e}")
                if attempt == 0:
                    # 第一次失败：追加明确提示后重试
                    messages.append({"role": "assistant", "content": content})
                    messages.append({
                        "role": "user",
                        "content": "你的回复不是合法的JSON，请只输出纯JSON，不要加任何说明文字或markdown代码块。"
                    })

        if plan_data is None:
            print(f"\n⚠️ [Manager] 计划解析彻底失败，将直接处理")
            return TaskPlan(
                task_id=f"task_{len(self._task_history)}",
                description=user_request,
                steps=[]
            )

        try:
            need_dispatch = plan_data.get("need_dispatch", False)
            reason = plan_data.get("reason", "")
            print(f"\n📊 [Manager] 决策分析:")
            print(f"   需要分派: {need_dispatch}")
            print(f"   原因: {reason[:100]}...")

            if not need_dispatch:
                print(f"   结论: 任务简单，Manager直接处理")
                return TaskPlan(
                    task_id=f"task_{len(self._task_history)}",
                    description=user_request,
                    steps=[]
                )

            steps = plan_data.get("steps", [])
            print(f"   结论: 需要分派给{len(steps)}个Worker执行")

            # 创建任务计划
            task_plan = TaskPlan(
                task_id=f"task_{len(self._task_history)}",
                description=user_request,
                steps=steps
            )
            self._task_history.append(task_plan)

            return task_plan

        except Exception as e:
            print(f"\n⚠️ [Manager] 计划构建失败: {e}, 将直接处理")
            return TaskPlan(
                task_id=f"task_{len(self._task_history)}",
                description=user_request,
                steps=[]
            )

    async def _execute_plan(self, task_plan: TaskPlan):
        """执行任务计划"""
        task_plan.status = "running"

        # 按依赖顺序执行任务
        completed_steps = set()
        print(f"\n📋 [Manager] 开始执行{len(task_plan.steps)}个步骤...")

        while len(completed_steps) < len(task_plan.steps):
            # 找到可以执行的任务（依赖已满足）
            ready_steps = [
                step for step in task_plan.steps
                if step["step_id"] not in completed_steps
                and all(dep in completed_steps for dep in step.get("depends_on", []))
            ]

            if not ready_steps:
                print(f"⚠️ [Manager] 没有可执行的步骤，可能存在循环依赖")
                break

            print(f"\n   🔄 本轮可执行步骤: {[s.get('agent_name') for s in ready_steps]}")

            # 并行执行准备好的任务
            tasks = []
            for step in ready_steps:
                task = self._execute_step(step, task_plan)
                tasks.append(task)

            await asyncio.gather(*tasks)

            for step in ready_steps:
                completed_steps.add(step["step_id"])
                print(f"   ✅ 步骤完成: {step.get('agent_name')} - {step.get('task', '')[:30]}...")

        task_plan.status = "completed"
        print(f"\n✅ [Manager] 所有步骤执行完成")

    async def _execute_step(self, step: Dict, task_plan: TaskPlan):
        """执行单个步骤（优先按 agent_id 查找，兜底按 agent_name 模糊匹配）"""
        agent_id = step.get("agent_id")
        agent_name = step.get("agent_name", "")
        task_description = step.get("task")
        task_input = step.get("input", "")

        print(f"\n   📤 [Manager] 分派任务给 {agent_name} (id={agent_id}):")
        print(f"      任务: {task_description[:50]}...")

        # 优先按 UUID 查找
        worker = self._workers.get(agent_id) if agent_id else None

        # Fallback：按名称模糊匹配（兼容旧格式）
        if not worker and agent_name:
            for wid, w in self._workers.items():
                if w.name == agent_name:
                    worker = w
                    break

        if not worker:
            print(f"      ❌ Worker {agent_name}(id={agent_id}) 未找到")
            task_plan.results[step["step_id"]] = {
                "status": "failed",
                "error": f"Worker {agent_name} 未找到"
            }
            return

        # 构建任务消息
        task_msg = Msg(
            name=self.name,
            content=f"【任务分派】\n任务: {task_description}\n输入: {task_input}\n请执行此任务并返回结果。",
            role="user"
        )

        try:
            # 调用Worker
            print(f"      ⏳ 等待 {agent_name} 执行...")
            response = await worker.reply(task_msg)

            result_preview = str(response.content)[:100] if response.content else ""
            print(f"      ✅ {agent_name} 完成，结果: {result_preview}...")

            task_plan.results[step["step_id"]] = {
                "status": "completed",
                "agent": agent_name,
                "result": response.content
            }

        except Exception as e:
            print(f"      ❌ {agent_name} 执行失败: {e}")
            task_plan.results[step["step_id"]] = {
                "status": "failed",
                "agent": agent_name,
                "error": str(e)
            }

    async def _integrate_results(self, task_plan: TaskPlan) -> str:
        """整合所有Worker的结果"""

        results_summary = []
        for step in task_plan.steps:
            step_id = step["step_id"]
            result = task_plan.results.get(step_id, {})

            if result.get("status") == "completed":
                results_summary.append(
                    f"步骤 {step_id} ({step.get('agent_name')}):\n"
                    f"{result.get('result', '')}"
                )
            else:
                results_summary.append(
                    f"步骤 {step_id} ({step.get('agent_name')}):\n"
                    f"执行失败: {result.get('error', '未知错误')}"
                )

        all_results = "\n\n---\n\n".join(results_summary)
        print(f"\n   📊 [Manager] 收集到{len(results_summary)}个Worker的结果")

        # 让Manager整合结果
        system_prompt = f"""你是{self.name}，{self.role}。

原始用户请求: {task_plan.description}

各团队成员的执行结果：
{all_results}

请以你的角色整合以上结果，给用户一个完整、连贯的回复。
保持你的人设，回答应该简洁、专业。
"""

        messages = [{"role": "system", "content": system_prompt}]

        final_content = await self._call_llm(messages)

        print(f"   ✅ [Manager] 结果整合完成，生成回复长度: {len(final_content)}字符")

        return final_content

    async def _call_llm(self, messages: List[Dict]) -> str:
        """调用 LLM API"""
        response = await self._openai_client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.7,
        )
        return response.choices[0].message.content

    async def _query_knowledge_base(self, query: str) -> str:
        """查询知识库获取上下文"""
        if not self._kb:
            return ""

        try:
            result = await self._kb.query(query, top_k=5, min_similarity=0.5)
            return result.get("context", "")
        except Exception as e:
            print(f"   ⚠️ 知识库查询失败: {e}")
            return ""

    async def _handle_directly(self, msg: Msg) -> Msg:
        """直接处理请求（不需要分派），支持RAG"""
        user_content = msg.content

        # 如果有知识库，先检索相关内容
        context = ""
        if self._kb:
            print(f"\n   📚 [Manager] 查询知识库...")
            context = await self._query_knowledge_base(user_content)
            if context:
                print(f"   ✅ [Manager] 检索到相关知识，长度: {len(context)}字符")
            else:
                print(f"   ⚠️ [Manager] 未检索到相关知识")

        # 构建系统提示
        if context:
            system_prompt = f"""你是{self.name}，{self.role}。

你的性格特点：{self.personality}

你可以访问知识库来回答用户问题。请基于以下参考资料回答：

## 参考资料
{context}

回答要求：
1. 基于参考资料回答，不要编造信息
2. 如果参考资料不足，请明确说明
3. 引用相关文档时注明来源"""
        else:
            system_prompt = f"""你是{self.name}，{self.role}。

你的性格特点：{self.personality}

可以直接回答用户的问题，不需要分派给团队成员。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        print(f"\n   🧠 [Manager] 直接处理请求（{'使用RAG增强' if context else '不经过Workers'}）...")
        content = await self._call_llm(messages)

        print(f"   ✅ [Manager] 直接回复完成，长度: {len(content)}字符")

        return Msg(name=self.name, content=content, role="assistant")

    def _extract_json(self, text: str) -> str:
        """从文本中提取JSON，兼容 markdown 代码块和裸 JSON"""
        # 优先处理 ```json ... ``` 代码块
        import re
        code_block = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', text, re.DOTALL)
        if code_block:
            return code_block.group(1).strip()

        # 找到最外层的 { } 对
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start:end+1]

        return text

    async def __call__(self, msg: Msg) -> Msg:
        """使 Agent 可以直接被调用"""
        return await self.reply(msg)


class WorkerAgent:
    """
    Worker Agent 接口 - 被Manager调用的Agent
    支持知识库检索（RAG）
    """

    def __init__(
        self,
        name: str,
        role: str,
        personality: str,
        specialty: str,  # 专业领域
        expertise: str,  # 具体专长描述
        model_name: str = "qwen-max",
        api_key: Optional[str] = None,
        llm_config: Optional[Dict[str, Any]] = None,
        tools: Optional[List[str]] = None,  # 该Worker可用的工具
        kb_id: Optional[str] = None,  # 关联的知识库ID
    ):
        self.id = uuid.uuid4().hex[:8]  # 唯一 ID，供 Manager 字典键使用
        self.name = name
        self.role = role
        self.personality = personality
        self.specialty = specialty
        self.expertise = expertise
        self._manager: Optional[ManagerAgent] = None
        self._available_tools = tools or []
        self.kb_id = kb_id

        # 初始化底层Agent
        from .chat_agent import ChatAgent

        # 构建带工具限制的llm_config
        worker_llm_config = llm_config or {
            "provider": "dashscope",
            "model_id": model_name,
            "api_key": api_key
        }

        self._agent = ChatAgent(
            name=name,
            role=role,
            personality=personality,
            llm_config=worker_llm_config
        )

        # 加载知识库
        self._kb = None
        if kb_id:
            try:
                from rag_knowledge_base import KnowledgeBaseManager
                kb_manager = KnowledgeBaseManager()
                self._kb = kb_manager.load_knowledge_base(kb_id)
                if self._kb:
                    print(f"✅ Worker {name} 已关联知识库: {kb_id}")
                else:
                    print(f"⚠️ Worker {name} 关联知识库失败: {kb_id} 不存在")
            except Exception as e:
                print(f"⚠️ Worker {name} 加载知识库失败: {e}")

    def set_manager(self, manager: ManagerAgent):
        """设置Manager"""
        self._manager = manager

    async def _query_knowledge_base(self, query: str) -> str:
        """查询知识库获取上下文"""
        if not self._kb:
            return ""

        try:
            result = await self._kb.query(query, top_k=3, min_similarity=0.5)
            return result.get("context", "")
        except Exception as e:
            print(f"   ⚠️ Worker {self.name} 知识库查询失败: {e}")
            return ""

    async def reply(self, msg: Msg) -> Msg:
        """响应Manager分派的任务，支持RAG"""
        task_content = msg.content

        # 如果有知识库，先检索相关内容
        context = ""
        if self._kb:
            print(f"\n   📚 [{self.name}] 查询知识库...")
            # 提取任务的核心查询（去掉"任务分派"等前缀）
            query = task_content
            if "【任务分派】" in query:
                # 尝试提取任务描述
                lines = query.split('\n')
                for line in lines:
                    if line.startswith("任务:"):
                        query = line.replace("任务:", "").strip()
                        break

            context = await self._query_knowledge_base(query)
            if context:
                print(f"   ✅ [{self.name}] 检索到相关知识，长度: {len(context)}字符")
            else:
                print(f"   ⚠️ [{self.name}] 未检索到相关知识")

        # 构建增强提示
        if context:
            enhanced_content = f"""{task_content}

## 参考资料
{context}

请基于以上参考资料回答。如果参考资料不足，请明确说明。"""
        else:
            enhanced_content = f"""{task_content}

记住你是{self.name}，{self.role}，你的专长是：{self.expertise}
请用符合你人设的方式回复。"""

        enhanced_msg = Msg(
            name=msg.name,
            content=enhanced_content,
            role=msg.role
        )

        return await self._agent.reply(enhanced_msg)

    async def __call__(self, msg: Msg) -> Msg:
        return await self.reply(msg)

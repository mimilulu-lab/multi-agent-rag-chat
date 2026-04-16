"""
聊天智能体 - 基于 AgentScope ReActAgent
支持 MsgHub 多 Agent 通信，集成工具调用能力
"""
from typing import Optional, Dict, Any, List
from agentscope.agent import AgentBase
from agentscope.message import Msg
from agentscope.model import DashScopeChatModel, OpenAIChatModel
from agentscope.agent import ReActAgent
from agentscope.formatter import OpenAIChatFormatter

from tools import get_toolkit


class ChatAgent(AgentBase):
    """
    聊天智能体 - 支持多 Agent 协作对话

    Attributes:
        name: Agent 名称
        role: Agent 角色描述（用于 system prompt）
        personality: Agent 性格特点
    """

    def __init__(
        self,
        name: str,
        role: str,
        personality: str,
        model_name: str = "qwen-max",
        api_key: Optional[str] = None,
        llm_config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化聊天智能体

        Args:
            name: Agent 名称（如"小蓝"、"小红"）
            role: Agent 角色（如"办公室助理"、"技术专家"）
            personality: Agent 性格描述
            model_name: 使用的语言模型名称
            api_key: API 密钥
            llm_config: 语言模型配置字典
        """
        super().__init__()
        self.name = name
        self.role = role
        self.personality = personality

        # 使用 llm_config 或回退到旧参数
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

        # 初始化语言模型
        if not self.api_key:
            raise ValueError(f"API key is required for agent {name}")

        self.model = self._create_model()
        formatter = self._create_formatter()

        # 获取全局 Toolkit（所有 Agent 共享）
        toolkit = get_toolkit()

        # 创建 ReAct 智能体，使用角色化的 system prompt
        sys_prompt = self._create_system_prompt()
        self.react_agent = ReActAgent(
            name=name,
            sys_prompt=sys_prompt,
            model=self.model,
            formatter=formatter,
            toolkit=toolkit,  # 注册工具
            max_iters=10,
        )

    def _create_system_prompt(self) -> str:
        """创建角色化的 system prompt"""
        from tools import list_tools
        available_tools = list_tools()
        tools_info = "、".join(available_tools) if available_tools else "暂无"

        return f"""你是{self.name}，{self.role}。

你的性格特点：{self.personality}

你可以使用的工具：{tools_info}

请记住：
1. 始终保持你的角色人设，用符合性格的方式说话
2. 当其他同事（其他 Agent）发言时，你可以回应或补充
3. 你的回答应该简洁、有趣、有互动性
4. 不要透露你是 AI，始终保持角色扮演
5. 需要时使用工具完成任务，但不要过度依赖
"""

    def _create_model(self):
        """根据配置创建对应的模型实例"""
        if self.provider == "dashscope":
            return OpenAIChatModel(
                model_name=self.model_name,
                api_key=self.api_key,
                client_kwargs={"base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
                stream=False,  # 禁用流式，避免 async_generator 问题
            )
        elif self.provider in ["openai", "anthropic", "custom", "kimi"]:
            client_kwargs = {}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url
            return OpenAIChatModel(
                model_name=self.model_name,
                api_key=self.api_key,
                client_kwargs=client_kwargs if client_kwargs else None,
                stream=False,  # 禁用流式，避免 async_generator 问题
            )
        else:
            return DashScopeChatModel(
                model_name=self.model_name,
                api_key=self.api_key
            )

    def _create_formatter(self):
        """根据配置创建对应的 formatter"""
        return OpenAIChatFormatter()

    async def reply(self, msg: Msg) -> Msg:
        """
        处理消息并生成回复

        Args:
            msg: 输入消息

        Returns:
            Agent 的回复消息
        """
        return await self.react_agent.reply(msg)

    async def __call__(self, msg: Msg) -> Msg:
        """使 Agent 可以直接被调用"""
        return await self.reply(msg)


def create_default_agents(llm_config: Dict[str, Any]) -> List[ChatAgent]:
    """
    创建默认的双 Agent 配置

    Args:
        llm_config: 语言模型配置

    Returns:
        包含两个 Agent 的列表
    """
    agent1 = ChatAgent(
        name="小智",
        role="办公室技术专家",
        personality="专业、理性、喜欢分享技术知识，说话简洁明了，偶尔会给出实用的建议",
        llm_config=llm_config,
    )

    agent2 = ChatAgent(
        name="小美",
        role="办公室行政助理",
        personality="热情、友好、善于沟通，说话温柔体贴，喜欢帮助同事解决问题",
        llm_config=llm_config,
    )

    return [agent1, agent2]

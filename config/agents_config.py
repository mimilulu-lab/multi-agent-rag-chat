"""
Agent 配置管理模块
支持每个 Agent 独立配置模型、API、角色和性格
"""
import json
import os
import random
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

# 配置文件路径 - 放在项目根目录
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "agents_config.json")

# 确保 data 目录存在
os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)


class AgentConfig(BaseModel):
    """Agent 配置模型 - 引用 Provider"""
    id: str = Field(..., description="Agent 唯一标识")
    name: str = Field(..., description="Agent 名称")
    role: str = Field(..., description="Agent 角色")
    personality: str = Field(..., description="Agent 性格描述")
    avatar_type: str = Field(default="aiden", description="头像类型: aiden 或 wrench")

    # Agent 类型和协作配置
    agent_type: str = Field(default="worker", description="Agent 类型: manager/worker")
    specialty: str = Field(default="", description="专业领域（Worker需要）")
    expertise: str = Field(default="", description="具体专长描述（Worker需要）")

    # 引用 Provider
    provider_id: str = Field(..., description="关联的 Provider ID")

    # 引用知识库（可选）
    kb_id: str = Field(default="", description="关联的知识库 ID（可选）")

    # 元数据
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    is_active: bool = Field(default=True, description="是否启用")

    def to_info(self, mask_secret: bool = True) -> Dict[str, Any]:
        """转换为信息字典"""
        # 获取 provider 信息
        from providers import provider_manager
        provider = provider_manager.get_provider(self.provider_id)
        provider_info = None
        if provider:
            provider_info = {
                "id": provider.id,
                "name": provider.name,
                "provider_type": provider.provider_type,
                "model_id": provider.model_id,
                "model_name": provider.model_name,
            }

        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "personality": self.personality,
            "avatar_type": self.avatar_type,
            "agent_type": self.agent_type,
            "specialty": self.specialty,
            "expertise": self.expertise,
            "provider_id": self.provider_id,
            "kb_id": self.kb_id,
            "provider": provider_info,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_active": self.is_active,
        }

    def to_llm_config(self) -> Dict[str, Any]:
        """转换为 LLM 配置字典 - 从 Provider 获取"""
        from providers import provider_manager
        provider = provider_manager.get_provider(self.provider_id)
        if not provider:
            raise ValueError(f"Provider {self.provider_id} not found")

        return {
            "provider": provider.provider_type,
            "model_id": provider.model_id,
            "api_key": provider.api_key,
            "base_url": provider.base_url if provider.base_url else None,
        }


class AgentsConfigManager:
    """Agent 配置管理器"""

    def __init__(self):
        self.agents: Dict[str, AgentConfig] = {}
        self._load_config()

    def _load_config(self):
        """从文件加载配置"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for agent_data in data.get("agents", []):
                        agent = AgentConfig(**agent_data)
                        self.agents[agent.id] = agent
                print(f"✅ 已加载 {len(self.agents)} 个 Agent 配置")
            except Exception as e:
                print(f"⚠️ 加载 Agent 配置失败: {e}")
                # 加载失败时创建空配置
                self._create_empty_config()
        else:
            print("📄 Agent 配置文件不存在，创建空配置")
            self._create_empty_config()

    def _save_config(self):
        """保存配置到文件"""
        try:
            data = {
                "agents": [agent.model_dump() for agent in self.agents.values()]
            }
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"⚠️ 保存 Agent 配置失败: {e}")
            return False

    def _create_empty_config(self):
        """创建空配置（初始状态）"""
        self.agents = {}
        self._save_config()

    def list_agents(self, include_inactive: bool = False) -> List[AgentConfig]:
        """获取所有 Agent 配置"""
        agents = list(self.agents.values())
        if not include_inactive:
            agents = [a for a in agents if a.is_active]
        return agents

    def get_agent(self, agent_id: str) -> Optional[AgentConfig]:
        """获取单个 Agent 配置"""
        return self.agents.get(agent_id)

    def create_agent(self, data: Dict[str, Any]) -> AgentConfig:
        """创建新 Agent"""
        import uuid
        agent_id = data.get("id") or f"agent_{uuid.uuid4().hex[:8]}"

        # 确保ID唯一
        while agent_id in self.agents:
            agent_id = f"agent_{uuid.uuid4().hex[:8]}"

        # 如果没有提供 avatar_type，随机分配
        if not data.get("avatar_type"):
            data["avatar_type"] = random.choice(["aiden", "wrench"])

        agent = AgentConfig(id=agent_id, **{k: v for k, v in data.items() if k != "id"})
        self.agents[agent_id] = agent
        self._save_config()
        return agent

    def update_agent(self, agent_id: str, data: Dict[str, Any]) -> Optional[AgentConfig]:
        """更新 Agent 配置"""
        agent = self.agents.get(agent_id)
        if not agent:
            return None

        # 更新字段 - 只包含 Agent 自身属性，模型配置通过 provider_id 引用
        for field in ["name", "role", "personality", "avatar_type", "agent_type", "specialty", "expertise", "provider_id", "kb_id", "is_active"]:
            if field in data:
                setattr(agent, field, data[field])

        agent.updated_at = datetime.now().isoformat()
        self._save_config()
        return agent

    def delete_agent(self, agent_id: str) -> bool:
        """删除 Agent"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            self._save_config()
            return True
        return False

    def get_active_agents(self) -> List[AgentConfig]:
        """获取所有启用的 Agent"""
        return [a for a in self.agents.values() if a.is_active]


# 全局配置管理器实例
agents_config_manager = AgentsConfigManager()

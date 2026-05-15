"""
会话存储管理 - 保留48小时内的历史对话
采用简单 JSON 文件存储，与项目现有模式一致
"""
import json
import uuid
import time
import threading
from typing import List, Optional, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field


class ChatMessageRecord(BaseModel):
    """聊天记录"""
    id: str
    role: str  # user | assistant | error
    content: str
    timestamp: float
    agent_name: Optional[str] = None
    agent_role: Optional[str] = None


class Conversation(BaseModel):
    """会话"""
    conversation_id: str
    title: str
    agent_id: Optional[str] = None  # null 表示团队模式
    messages: List[ChatMessageRecord] = Field(default_factory=list)
    created_at: float
    updated_at: float


class ConversationStore:
    """会话存储管理器"""

    TTL_SECONDS = 48 * 3600  # 48小时

    def __init__(self, persist_path: str = "./data/conversations.json"):
        self.persist_path = Path(persist_path)
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        self._conversations: Dict[str, Conversation] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self):
        """从文件加载会话数据（调用方不持有锁）"""
        if not self.persist_path.exists():
            return

        try:
            with open(self.persist_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for item in data:
                conv = Conversation(**item)
                self._conversations[conv.conversation_id] = conv

            self._cleanup_expired()
        except Exception as e:
            print(f"⚠️ 加载会话数据失败: {e}")
            self._conversations = {}

    def _save(self):
        """保存会话数据到文件（调用方已持有锁，此处不再加锁）"""
        try:
            self._cleanup_expired()
            data = [conv.model_dump() for conv in self._conversations.values()]
            with open(self.persist_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ 保存会话数据失败: {e}")

    def _cleanup_expired(self):
        """清理超过48小时的过期会话"""
        cutoff = time.time() - self.TTL_SECONDS
        expired_ids = [
            cid for cid, conv in self._conversations.items()
            if conv.updated_at < cutoff
        ]
        for cid in expired_ids:
            del self._conversations[cid]

        if expired_ids:
            print(f"🧹 已清理 {len(expired_ids)} 个过期会话")

    def create_conversation(
        self,
        title: str,
        agent_id: Optional[str] = None
    ) -> Conversation:
        """创建新会话"""
        now = time.time()
        conversation = Conversation(
            conversation_id=f"conv_{uuid.uuid4().hex[:8]}",
            title=title,
            agent_id=agent_id,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._conversations[conversation.conversation_id] = conversation
            self._save()
        return conversation

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """获取单个会话"""
        with self._lock:
            self._cleanup_expired()
            return self._conversations.get(conversation_id)

    def list_conversations(
        self,
        agent_id: Optional[str] = None
    ) -> List[Conversation]:
        """列出未过期会话，按 updated_at 倒序"""
        with self._lock:
            self._cleanup_expired()
            conversations = list(self._conversations.values())

            if agent_id is not None:
                conversations = [
                    c for c in conversations
                    if c.agent_id == agent_id
                ]

            return sorted(
                conversations,
                key=lambda c: c.updated_at,
                reverse=True
            )

    def append_message(
        self,
        conversation_id: str,
        message: ChatMessageRecord
    ) -> bool:
        """追加消息到会话"""
        with self._lock:
            conv = self._conversations.get(conversation_id)
            if not conv:
                return False

            conv.messages.append(message)
            conv.updated_at = time.time()
            self._save()
            return True

    def delete_conversation(self, conversation_id: str) -> bool:
        """删除会话"""
        with self._lock:
            if conversation_id in self._conversations:
                del self._conversations[conversation_id]
                self._save()
                return True
            return False

    def get_latest_conversation(
        self,
        agent_id: Optional[str] = None
    ) -> Optional[Conversation]:
        """获取指定 agent 的最近一个会话"""
        conversations = self.list_conversations(agent_id=agent_id)
        return conversations[0] if conversations else None


# 全局单例
_conversation_store: Optional[ConversationStore] = None


def get_conversation_store() -> ConversationStore:
    """获取全局会话存储实例"""
    global _conversation_store
    if _conversation_store is None:
        _conversation_store = ConversationStore()
    return _conversation_store

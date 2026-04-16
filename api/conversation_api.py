"""
会话管理 API
提供历史会话的 CRUD 接口
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.conversation_store import get_conversation_store, ChatMessageRecord

router = APIRouter(prefix="/api/conversations", tags=["conversation"])


# ===== 请求/响应模型 =====

class CreateConversationRequest(BaseModel):
    title: str = "新对话"
    agent_id: Optional[str] = None


class ConversationSummary(BaseModel):
    conversation_id: str
    title: str
    agent_id: Optional[str]
    message_count: int
    updated_at: float


class ConversationDetail(BaseModel):
    conversation_id: str
    title: str
    agent_id: Optional[str]
    messages: List[dict]
    created_at: float
    updated_at: float


# ===== API 路由 =====

@router.get("")
async def list_conversations(agent_id: Optional[str] = None):
    """列出历史会话"""
    store = get_conversation_store()
    conversations = store.list_conversations(agent_id=agent_id)

    return {
        "success": True,
        "conversations": [
            ConversationSummary(
                conversation_id=c.conversation_id,
                title=c.title,
                agent_id=c.agent_id,
                message_count=len(c.messages),
                updated_at=c.updated_at,
            ).model_dump()
            for c in conversations
        ]
    }


@router.post("")
async def create_conversation(request: CreateConversationRequest):
    """创建新会话"""
    store = get_conversation_store()
    conversation = store.create_conversation(
        title=request.title,
        agent_id=request.agent_id,
    )
    return {
        "success": True,
        "conversation": ConversationSummary(
            conversation_id=conversation.conversation_id,
            title=conversation.title,
            agent_id=conversation.agent_id,
            message_count=0,
            updated_at=conversation.updated_at,
        ).model_dump()
    }


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str):
    """获取会话详情（含消息）"""
    store = get_conversation_store()
    conversation = store.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")

    return {
        "success": True,
        "conversation": ConversationDetail(
            conversation_id=conversation.conversation_id,
            title=conversation.title,
            agent_id=conversation.agent_id,
            messages=[m.model_dump() for m in conversation.messages],
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        ).model_dump()
    }


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """删除会话"""
    store = get_conversation_store()
    success = store.delete_conversation(conversation_id)

    if not success:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")

    return {"success": True, "message": "会话已删除"}

"""
RAG Agent - 知识库检索智能体
专门负责从知识库中检索相关信息
"""
from typing import Optional, Dict, Any, List
import os

from agentscope.message import Msg
from .chat_agent import ChatAgent


class RAGAgent(ChatAgent):
    """
    RAG 智能体 - 知识库检索专家

    职责:
    1. 理解用户查询意图
    2. 从知识库检索相关文档
    3. 基于检索结果生成回答
    """

    def __init__(
        self,
        name: str = "知识库助手",
        role: str = "知识检索专家",
        personality: str = "擅长从知识库中检索准确信息，回答有据可查",
        kb_id: Optional[str] = None,
        llm_config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            name=name,
            role=role,
            personality=personality,
            llm_config=llm_config
        )
        self.kb_id = kb_id
        self._kb = None

    async def _get_knowledge_base(self):
        """获取知识库实例"""
        if self._kb is None and self.kb_id:
            from rag_knowledge_base import KnowledgeBaseManager
            manager = KnowledgeBaseManager()
            self._kb = manager.load_knowledge_base(self.kb_id)
        return self._kb

    async def reply(self, msg: Msg) -> Msg:
        """
        RAG 回复流程:
        1. 检索相关知识
        2. 构建增强提示
        3. 生成回答
        """
        query = msg.content

        # 1. 检索知识库
        context = ""
        sources = []

        kb = await self._get_knowledge_base()
        if kb:
            try:
                result = await kb.query(query, top_k=5, min_similarity=0.5)
                context = result.get("context", "")
                sources = result.get("sources", [])
                print(f"📚 [RAG] 检索到 {len(sources)} 条相关知识")
            except Exception as e:
                print(f"⚠️ [RAG] 知识库检索失败: {e}")
        else:
            print(f"⚠️ [RAG] 知识库未加载")

        # 2. 构建增强提示
        if context and sources:
            enhanced_prompt = f"""请基于以下参考资料回答问题：

## 参考资料
{context}

## 用户问题
{query}

## 回答要求
1. 基于参考资料回答，不要编造信息
2. 如果参考资料不足以回答，请明确说明
3. 引用相关文档时注明来源
"""
        else:
            # 没有检索到相关内容，直接回答
            enhanced_prompt = query

        # 3. 生成回答
        enhanced_msg = Msg(
            name=msg.name,
            content=enhanced_prompt,
            role=msg.role
        )

        response = await super().reply(enhanced_msg)

        # 添加来源信息
        if sources:
            source_info = "\n\n📚 **参考来源**: " + ", ".join([
                f"[{i+1}] {s.get('metadata', {}).get('filename', '未知')} (相似度: {s['similarity']})"
                for i, s in enumerate(sources[:3])
            ])
            response.content = response.content + source_info

        return response


class KnowledgeBaseWorker:
    """
    Worker 专用 RAG 工具类
    供其他 Worker 调用以检索知识
    """

    def __init__(self, kb_id: Optional[str] = None):
        self.kb_id = kb_id
        self._kb = None

    async def _get_kb(self):
        if self._kb is None and self.kb_id:
            from rag_knowledge_base import KnowledgeBaseManager
            manager = KnowledgeBaseManager()
            self._kb = manager.load_knowledge_base(self.kb_id)
        return self._kb

    async def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """搜索知识库"""
        kb = await self._get_kb()
        if not kb:
            return []
        return await kb.search(query, top_k=top_k)

    async def query(self, question: str, top_k: int = 5) -> Dict[str, Any]:
        """查询并返回上下文"""
        kb = await self._get_kb()
        if not kb:
            return {"context": "", "sources": []}
        return await kb.query(question, top_k=top_k)

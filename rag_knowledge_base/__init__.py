"""
RAG 知识库模块

提供完整的 RAG 功能：
- 文档加载与处理
- 文本分块与向量化
- 向量存储与检索
- 知识库管理

使用示例:
    from rag_knowledge_base import KnowledgeBase, KnowledgeBaseConfig

    # 创建知识库
    config = KnowledgeBaseConfig(name="我的知识库")
    kb = KnowledgeBase(config)

    # 添加文档
    await kb.add_documents("./docs")

    # 搜索
    results = await kb.search("查询内容")
"""

from .document_loader import DocumentLoader, Document, load_documents
from .text_splitter import TextSplitter, RecursiveTextSplitter, TextChunk, split_documents
from .embeddings import EmbeddingService, EmbeddingProvider, embed_texts
from .vector_store import VectorStore, SimpleVectorStore
from .knowledge_base import (
    KnowledgeBase,
    KnowledgeBaseConfig,
    KnowledgeBaseManager,
    create_knowledge_base,
)

__all__ = [
    # 文档加载
    "DocumentLoader",
    "Document",
    "load_documents",
    # 文本分割
    "TextSplitter",
    "RecursiveTextSplitter",
    "TextChunk",
    "split_documents",
    # 向量化
    "EmbeddingService",
    "EmbeddingProvider",
    "embed_texts",
    # 向量存储
    "VectorStore",
    "SimpleVectorStore",
    # 知识库
    "KnowledgeBase",
    "KnowledgeBaseConfig",
    "KnowledgeBaseManager",
    "create_knowledge_base",
]

__version__ = "0.1.0"

"""
知识库管理 API
提供知识库的 CRUD 和文档检索接口
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel, Field
import os
import shutil
from pathlib import Path

from rag_knowledge_base import (
    KnowledgeBase,
    KnowledgeBaseConfig,
    KnowledgeBaseManager,
)
from providers import provider_manager

router = APIRouter(prefix="/api/knowledge-bases", tags=["knowledge-base"])

# 全局知识库管理器
_kb_manager: Optional[KnowledgeBaseManager] = None
_upload_dir = Path("./data/uploads")
_upload_dir.mkdir(parents=True, exist_ok=True)


def get_kb_manager() -> KnowledgeBaseManager:
    """获取知识库管理器实例"""
    global _kb_manager
    if _kb_manager is None:
        _kb_manager = KnowledgeBaseManager()
    return _kb_manager


# ===== 请求/响应模型 =====

class CreateKBRequest(BaseModel):
    """创建知识库请求"""
    name: str = Field(..., description="知识库名称")
    description: str = Field(default="", description="知识库描述")
    embedding_provider: str = Field(default="kimi", description="向量化提供商 (kimi/openai/fake)")
    chunk_size: int = Field(default=500, description="分块大小")
    chunk_overlap: int = Field(default=50, description="分块重叠")


class KBResponse(BaseModel):
    """知识库响应"""
    kb_id: str
    name: str
    description: str
    embedding_provider: str
    total_documents: int


class KBListResponse(BaseModel):
    """知识库列表响应"""
    knowledge_bases: List[Dict[str, Any]]


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., description="查询文本")
    top_k: int = Field(default=5, description="返回结果数量")
    min_similarity: float = Field(default=0.0, description="最小相似度")


class SearchResult(BaseModel):
    """搜索结果"""
    id: str
    content: str
    similarity: float
    metadata: Dict[str, Any]


class SearchResponse(BaseModel):
    """搜索响应"""
    query: str
    results: List[SearchResult]
    total: int


class QueryContextResponse(BaseModel):
    """带上下文的查询响应"""
    question: str
    context: str
    sources: List[SearchResult]
    source_count: int


# ===== API 路由 =====

@router.post("", response_model=KBResponse)
async def create_knowledge_base(request: CreateKBRequest):
    """创建新知识库"""
    try:
        manager = get_kb_manager()

        # 自动获取对应 Embedding Provider 的 API Key
        api_key = None
        if request.embedding_provider != "fake":
            # 1. 优先使用活跃的 Embedding Provider
            active_embedding_id = getattr(provider_manager, '_active_embedding_provider_id', None)
            if active_embedding_id:
                provider = provider_manager.get_provider(active_embedding_id)
                if provider and provider.api_key:
                    api_key = provider.api_key

            # 2. 否则按 provider_type 匹配第一个可用的 provider
            if not api_key:
                for provider in provider_manager._providers.values():
                    if provider.provider_type == request.embedding_provider and provider.api_key:
                        api_key = provider.api_key
                        break

        kb = manager.create_knowledge_base(
            name=request.name,
            description=request.description,
            embedding_provider=request.embedding_provider,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            api_key=api_key,
        )

        return KBResponse(
            kb_id=kb.kb_id,
            name=kb.config.name,
            description=kb.config.description,
            embedding_provider=kb.config.embedding_provider,
            total_documents=0
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建知识库失败: {str(e)}")


@router.get("", response_model=KBListResponse)
async def list_knowledge_bases():
    """列出所有知识库"""
    manager = get_kb_manager()
    knowledge_bases = manager.list_knowledge_bases()
    return KBListResponse(knowledge_bases=knowledge_bases)


@router.get("/{kb_id}", response_model=KBResponse)
async def get_knowledge_base(kb_id: str):
    """获取知识库详情"""
    manager = get_kb_manager()
    kb = manager.load_knowledge_base(kb_id)

    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    stats = kb.get_stats()
    return KBResponse(
        kb_id=kb.kb_id,
        name=kb.config.name,
        description=kb.config.description,
        embedding_provider=kb.config.embedding_provider,
        total_documents=stats.get("total_documents", 0)
    )


@router.post("/{kb_id}/documents")
async def add_documents(
    kb_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """上传文档到知识库"""
    manager = get_kb_manager()
    kb = manager.load_knowledge_base(kb_id)

    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    # 保存上传的文件
    file_path = _upload_dir / f"{kb_id}_{file.filename}"
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")
    finally:
        file.file.close()

    # 异步处理文档
    try:
        result = await kb.add_documents(file_path)

        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "处理失败"))

        return {
            "success": True,
            "message": f"成功处理文档",
            "documents": result.get("documents", 0),
            "chunks": result.get("chunks", 0),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文档处理失败: {str(e)}")


@router.get("/{kb_id}/documents")
async def list_documents(kb_id: str):
    """获取知识库中的文档列表"""
    manager = get_kb_manager()
    kb = manager.load_knowledge_base(kb_id)

    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    try:
        documents = kb.list_documents()
        return {
            "success": True,
            "documents": documents,
            "total": len(documents),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档列表失败: {str(e)}")


@router.post("/{kb_id}/documents/directory")
async def add_documents_from_directory(
    kb_id: str,
    directory_path: str = Form(..., description="服务器上的目录路径"),
):
    """从目录添加文档到知识库"""
    manager = get_kb_manager()
    kb = manager.load_knowledge_base(kb_id)

    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    if not os.path.exists(directory_path):
        raise HTTPException(status_code=400, detail="目录不存在")

    try:
        result = await kb.add_documents(directory_path)

        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "处理失败"))

        return {
            "success": True,
            "message": f"成功处理目录",
            "documents": result.get("documents", 0),
            "chunks": result.get("chunks", 0),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文档处理失败: {str(e)}")


@router.post("/{kb_id}/search", response_model=SearchResponse)
async def search_knowledge_base(
    kb_id: str,
    request: SearchRequest,
):
    """搜索知识库"""
    manager = get_kb_manager()
    kb = manager.load_knowledge_base(kb_id)

    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    try:
        results = await kb.search(
            query=request.query,
            top_k=request.top_k,
            min_similarity=request.min_similarity
        )

        return SearchResponse(
            query=request.query,
            results=[
                SearchResult(
                    id=r["id"],
                    content=r["content"],
                    similarity=r["similarity"],
                    metadata=r["metadata"]
                ) for r in results
            ],
            total=len(results)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.post("/{kb_id}/query", response_model=QueryContextResponse)
async def query_with_context(
    kb_id: str,
    request: SearchRequest,
):
    """查询知识库并返回上下文"""
    manager = get_kb_manager()
    kb = manager.load_knowledge_base(kb_id)

    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    try:
        result = await kb.query(
            question=request.query,
            top_k=request.top_k,
            min_similarity=request.min_similarity
        )

        return QueryContextResponse(
            question=result["question"],
            context=result["context"],
            sources=[
                SearchResult(
                    id=s["id"],
                    content=s["content"],
                    similarity=s["similarity"],
                    metadata=s["metadata"]
                ) for s in result["sources"]
            ],
            source_count=result["source_count"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.delete("/{kb_id}")
async def delete_knowledge_base(kb_id: str):
    """删除知识库"""
    manager = get_kb_manager()
    kb = manager.load_knowledge_base(kb_id)

    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    try:
        await manager.delete_knowledge_base(kb_id)
        return {"success": True, "message": "知识库已删除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.get("/{kb_id}/stats")
async def get_knowledge_base_stats(kb_id: str):
    """获取知识库统计信息"""
    manager = get_kb_manager()
    kb = manager.load_knowledge_base(kb_id)

    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    return kb.get_stats()

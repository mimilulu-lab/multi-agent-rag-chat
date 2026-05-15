"""
知识库管理 - 整合文档处理全流程
提供高层次的 RAG 接口（支持 Hybrid Search + 轻量 Rerank）
"""
import os
import re
import uuid
from typing import List, Optional, Dict, Any, Union
from pathlib import Path
from dataclasses import dataclass, asdict

try:
    from rank_bm25 import BM25Okapi
    _BM25_AVAILABLE = True
except ImportError:
    _BM25_AVAILABLE = False
    print("⚠️ rank_bm25 未安装，Hybrid Search 将退化为纯向量检索")

from .document_loader import DocumentLoader, Document
from .text_splitter import RecursiveTextSplitter, TextChunk
from .embeddings import EmbeddingService
from .vector_store import VectorStore, SimpleVectorStore


def _tokenize(text: str) -> List[str]:
    """
    简单分词：中文按字，英文按词，支持混合文本。
    适用于 BM25 索引，无需外部依赖。
    """
    # 提取中文字符（单字）
    cn_chars = re.findall(r'[一-鿿]', text)
    # 提取英文单词（转小写）
    en_words = re.findall(r'[a-zA-Z0-9]+', text.lower())
    return cn_chars + en_words


def _rrf_merge(
    vector_results: List[Dict[str, Any]],
    bm25_results: List[Dict[str, Any]],
    top_k: int,
    k: int = 60
) -> List[Dict[str, Any]]:
    """
    Reciprocal Rank Fusion 合并向量检索和 BM25 检索结果。
    score = Σ 1/(k + rank_i)
    """
    scores: Dict[str, float] = {}
    content_map: Dict[str, Dict[str, Any]] = {}

    for rank, result in enumerate(vector_results, 1):
        doc_id = result["id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank)
        content_map[doc_id] = result

    for rank, result in enumerate(bm25_results, 1):
        doc_id = result["id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (k + rank)
        if doc_id not in content_map:
            content_map[doc_id] = result

    # 按 RRF 分数排序
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:top_k]
    merged = []
    for rank, doc_id in enumerate(sorted_ids, 1):
        item = dict(content_map[doc_id])
        item["rrf_score"] = round(scores[doc_id], 6)
        item["rank"] = rank
        merged.append(item)

    return merged


@dataclass
class KnowledgeBaseConfig:
    """知识库配置"""
    name: str
    description: str = ""
    embedding_provider: str = "kimi"
    embedding_model: str = "text-embedding-v1"
    chunk_size: int = 500
    chunk_overlap: int = 50
    api_key: Optional[str] = None


class KnowledgeBase:
    """
    知识库 - RAG 核心组件

    使用流程：
    1. 创建知识库: kb = KnowledgeBase(config)
    2. 添加文档: kb.add_documents(file_path)
    3. 搜索: results = kb.search(query)
    """

    def __init__(
        self,
        config: KnowledgeBaseConfig,
        kb_id: Optional[str] = None,
        persist_dir: str = "./data/knowledge_bases"
    ):
        """
        Args:
            config: 知识库配置
            kb_id: 知识库ID（不指定则自动生成）
            persist_dir: 持久化目录
        """
        self.config = config
        self.kb_id = kb_id or f"kb_{uuid.uuid4().hex[:8]}"
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        # 初始化组件
        self.document_loader = DocumentLoader()
        self.text_splitter = RecursiveTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap
        )
        self.embedding_service = EmbeddingService(
            provider=config.embedding_provider,
            api_key=config.api_key or os.getenv("KIMI_API_KEY")
        )

        # 向量存储
        vector_db_path = str(self.persist_dir / "vector_db")
        try:
            self.vector_store = VectorStore(
                collection_name=f"kb_{self.kb_id}",
                persist_directory=vector_db_path,
                embedding_service=self.embedding_service
            )
        except Exception as e:
            print(f"⚠️ 无法初始化 ChromaDB: {e}，使用简单存储")
            self.vector_store = SimpleVectorStore(
                embedding_service=self.embedding_service,
                persist_path=str(self.persist_dir / f"{self.kb_id}_vectors.json")
            )

        # 元数据存储
        self.metadata_path = self.persist_dir / f"{self.kb_id}_meta.json"
        self._save_metadata()

        # BM25 索引（懒加载，首次 search 时构建）
        self._bm25_index = None          # BM25Okapi 实例
        self._bm25_corpus: List[Dict[str, Any]] = []  # [{id, content, metadata}]
        self._bm25_dirty = True          # 标记：需要重建索引

        print(f"✅ 知识库创建成功: {self.kb_id}")
        print(f"   名称: {config.name}")
        print(f"   描述: {config.description}")

    def _save_metadata(self):
        """保存知识库元数据"""
        import json
        metadata = {
            "kb_id": self.kb_id,
            **asdict(self.config)
        }
        with open(self.metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    async def add_documents(
        self,
        source: Union[str, Path],
        file_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        添加文档到知识库

        Args:
            source: 文件或目录路径
            file_filter: 文件类型过滤，如 ['.md', '.txt']

        Returns:
            处理结果统计
        """
        print(f"\n📚 开始处理文档: {source}")

        # 1. 加载文档
        try:
            documents = self.document_loader.load(source)
            print(f"   ✅ 加载了 {len(documents)} 个文档")
        except Exception as e:
            print(f"   ❌ 文档加载失败: {e}")
            return {"success": False, "error": str(e)}

        if not documents:
            return {"success": True, "documents": 0, "chunks": 0}

        # 2. 文本分块
        chunks = self.text_splitter.split(documents)
        print(f"   ✅ 分割为 {len(chunks)} 个文本块")

        # 3. 向量化
        print(f"   ⏳ 正在进行向量化...")
        embedding_results = await self.embedding_service.embed_chunks(chunks)
        print(f"   ✅ 向量化完成")

        # 4. 存储到向量数据库
        doc_ids = await self.vector_store.add_documents(
            embedding_results,
            knowledge_base_id=self.kb_id
        )

        result = {
            "success": True,
            "documents": len(documents),
            "chunks": len(chunks),
            "doc_ids": doc_ids[:5] if len(doc_ids) > 5 else doc_ids,  # 只显示前5个
        }

        # 标记 BM25 索引需要重建
        self._bm25_dirty = True

        print(f"   ✅ 文档处理完成!")
        print(f"      - 原始文档: {result['documents']}")
        print(f"      - 文本块: {result['chunks']}")

        return result

    async def search(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        搜索知识库

        Args:
            query: 查询文本
            top_k: 返回结果数量
            min_similarity: 最小相似度阈值

        Returns:
            搜索结果列表
        """
        results = await self.vector_store.search(
            query=query,
            top_k=top_k,
            knowledge_base_id=self.kb_id
        )

        # 过滤低相似度结果
        if min_similarity > 0:
            results = [r for r in results if r["similarity"] >= min_similarity]

        return results

    def _rebuild_bm25_index(self):
        """从向量存储加载所有文档，重建 BM25 索引"""
        if not _BM25_AVAILABLE:
            return

        try:
            raw_docs = self.vector_store.get_documents(knowledge_base_id=self.kb_id)
        except Exception as e:
            print(f"   ⚠️ BM25 索引构建失败（获取文档出错）: {e}")
            return

        # get_documents 只返回按文件聚合的摘要，需要全量 chunks
        # 从 vector_store 获取完整内容
        try:
            if hasattr(self.vector_store, 'collection'):
                # ChromaDB
                result = self.vector_store.collection.get(
                    where={"knowledge_base_id": self.kb_id},
                    include=["documents", "metadatas"]
                )
                self._bm25_corpus = [
                    {
                        "id": doc_id,
                        "content": content,
                        "metadata": meta,
                        "tokens": _tokenize(content),
                    }
                    for doc_id, content, meta in zip(
                        result["ids"],
                        result["documents"],
                        result["metadatas"]
                    )
                ]
            elif hasattr(self.vector_store, 'documents'):
                # SimpleVectorStore
                self._bm25_corpus = [
                    {
                        "id": doc_id,
                        "content": doc["text"],
                        "metadata": doc.get("metadata", {}),
                        "tokens": _tokenize(doc["text"]),
                    }
                    for doc_id, doc in self.vector_store.documents.items()
                    if doc.get("metadata", {}).get("knowledge_base_id") == self.kb_id
                ]
            else:
                self._bm25_corpus = []
        except Exception as e:
            print(f"   ⚠️ BM25 语料加载失败: {e}")
            self._bm25_corpus = []
            return

        if not self._bm25_corpus:
            return

        tokenized = [doc["tokens"] for doc in self._bm25_corpus]
        self._bm25_index = BM25Okapi(tokenized)
        self._bm25_dirty = False
        print(f"   📚 BM25 索引已构建，语料规模: {len(self._bm25_corpus)} chunks")

    def _bm25_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """BM25 关键词检索"""
        if not _BM25_AVAILABLE or not self._bm25_corpus:
            return []

        if self._bm25_dirty or self._bm25_index is None:
            self._rebuild_bm25_index()

        if not self._bm25_index:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scores = self._bm25_index.get_scores(query_tokens)

        # 取 top_k 结果
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        results = []
        for rank, idx in enumerate(top_indices, 1):
            doc = self._bm25_corpus[idx]
            bm25_score = float(scores[idx])
            if bm25_score <= 0:
                continue
            results.append({
                "id": doc["id"],
                "content": doc["content"],
                "metadata": doc["metadata"],
                "similarity": round(bm25_score / (bm25_score + 1), 4),  # 归一化到 [0,1)
                "rank": rank,
                "bm25_score": round(bm25_score, 4),
            })

        return results

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.0,
        alpha: float = 0.5,  # 0=纯BM25, 1=纯向量
    ) -> List[Dict[str, Any]]:
        """
        混合检索：向量 + BM25，用 RRF 合并结果。

        Args:
            query: 查询文本
            top_k: 最终返回数量
            min_similarity: 向量检索最低分（BM25 不受此限制）
            alpha: 预留参数（RRF 本身不用 alpha，但供未来加权使用）

        Returns:
            按 RRF 分数排序的结果列表
        """
        fetch_k = top_k * 2  # 各路多取一些，合并后裁剪

        # 向量检索
        vector_results = await self.search(query, fetch_k, min_similarity)

        # BM25 检索
        if _BM25_AVAILABLE:
            bm25_results = self._bm25_search(query, fetch_k)
        else:
            bm25_results = []

        # 若 BM25 不可用，直接返回向量结果
        if not bm25_results:
            return vector_results[:top_k]

        # RRF 合并
        merged = _rrf_merge(vector_results, bm25_results, top_k)
        return merged

    def _keyword_rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        weight: float = 0.2
    ) -> List[Dict[str, Any]]:
        """
        轻量关键词 Rerank：在原始 similarity 基础上，按关键词命中数加分。
        无需额外 API 调用，延迟近零。
        """
        query_tokens = set(_tokenize(query))
        if not query_tokens:
            return results

        reranked = []
        for item in results:
            content_tokens = set(_tokenize(item["content"]))
            overlap = len(query_tokens & content_tokens) / max(len(query_tokens), 1)
            # 加权融合
            boosted = item["similarity"] * (1 - weight) + overlap * weight
            new_item = dict(item)
            new_item["rerank_score"] = round(boosted, 4)
            reranked.append(new_item)

        reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
        return reranked

    async def query(
        self,
        question: str,
        top_k: int = 5,
        min_similarity: float = 0.5,
        use_hybrid: bool = True,
    ) -> Dict[str, Any]:
        """
        查询知识库并生成上下文

        Args:
            question: 问题
            top_k: 检索结果数量
            min_similarity: 最小相似度

        Returns:
            包含上下文和搜索结果的字典
        """
        # 1. 检索相关文档（hybrid 模式或纯向量）
        if use_hybrid and _BM25_AVAILABLE:
            results = await self.hybrid_search(question, top_k, min_similarity)
        else:
            results = await self.search(question, top_k, min_similarity)

        # 2. 轻量 Rerank（关键词加权）
        if results:
            results = self._keyword_rerank(question, results)

        # 3. 构建上下文
        if results:
            context_parts = []
            for i, result in enumerate(results, 1):
                context_parts.append(
                    f"[文档{i}] (相似度: {result['similarity']})\n{result['content']}"
                )
            context = "\n\n---\n\n".join(context_parts)
        else:
            context = "未找到相关文档。"

        return {
            "question": question,
            "context": context,
            "sources": results,
            "source_count": len(results)
        }

    def list_documents(self) -> List[Dict[str, Any]]:
        """获取知识库中的文档列表"""
        return self.vector_store.get_documents(knowledge_base_id=self.kb_id)

    def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        return {
            "kb_id": self.kb_id,
            "name": self.config.name,
            **self.vector_store.get_stats()
        }

    async def delete(self):
        """删除知识库"""
        # 删除向量数据
        self.vector_store.delete_documents(knowledge_base_id=self.kb_id)

        # 删除元数据文件
        if self.metadata_path.exists():
            self.metadata_path.unlink()

        print(f"✅ 知识库已删除: {self.kb_id}")


class KnowledgeBaseManager:
    """知识库管理器 - 管理多个知识库"""

    def __init__(self, persist_dir: str = "./data/knowledge_bases"):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._knowledge_bases: Dict[str, KnowledgeBase] = {}

    def create_knowledge_base(
        self,
        name: str,
        description: str = "",
        embedding_provider: str = "kimi",
        **kwargs
    ) -> KnowledgeBase:
        """创建新知识库"""
        config = KnowledgeBaseConfig(
            name=name,
            description=description,
            embedding_provider=embedding_provider,
            **kwargs
        )

        kb = KnowledgeBase(config, persist_dir=str(self.persist_dir))
        self._knowledge_bases[kb.kb_id] = kb

        return kb

    def load_knowledge_base(self, kb_id: str) -> Optional[KnowledgeBase]:
        """加载已有知识库"""
        if kb_id in self._knowledge_bases:
            return self._knowledge_bases[kb_id]

        # 从文件加载配置
        import json
        meta_path = self.persist_dir / f"{kb_id}_meta.json"

        if not meta_path.exists():
            return None

        with open(meta_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        config = KnowledgeBaseConfig(**{k: v for k, v in data.items() if k != 'kb_id'})
        kb = KnowledgeBase(config, kb_id=kb_id, persist_dir=str(self.persist_dir))
        self._knowledge_bases[kb_id] = kb

        return kb

    def list_knowledge_bases(self) -> List[Dict[str, Any]]:
        """列出所有知识库"""
        import json
        knowledge_bases = []

        for meta_file in self.persist_dir.glob("*_meta.json"):
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    knowledge_bases.append({
                        "kb_id": data.get("kb_id", meta_file.stem.replace("_meta", "")),
                        "name": data.get("name", "Unknown"),
                        "description": data.get("description", ""),
                        "embedding_provider": data.get("embedding_provider", "kimi"),
                    })
            except Exception as e:
                print(f"⚠️ 读取元数据失败: {meta_file}: {e}")

        return knowledge_bases

    async def delete_knowledge_base(self, kb_id: str):
        """删除知识库"""
        kb = self.load_knowledge_base(kb_id)
        if kb:
            await kb.delete()
            if kb_id in self._knowledge_bases:
                del self._knowledge_bases[kb_id]


# 便捷函数
async def create_knowledge_base(
    name: str,
    documents_path: Optional[Union[str, Path]] = None,
    **kwargs
) -> KnowledgeBase:
    """
    便捷函数：创建知识库并添加文档

    Args:
        name: 知识库名称
        documents_path: 文档路径（可选）
        **kwargs: 其他配置

    Returns:
        KnowledgeBase 实例
    """
    manager = KnowledgeBaseManager()
    kb = manager.create_knowledge_base(name, **kwargs)

    if documents_path:
        await kb.add_documents(documents_path)

    return kb

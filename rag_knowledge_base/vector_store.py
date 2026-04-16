"""
向量存储 - 基于 ChromaDB 的向量数据库
支持文档存储、检索和相似度搜索
"""
import os
import json
from typing import List, Optional, Dict, Any
from pathlib import Path
import numpy as np

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None
    print("⚠️ ChromaDB 未安装，运行: pip install chromadb")

from .embeddings import EmbeddingService, EmbeddingResult


class VectorStore:
    """向量存储 - 基于 ChromaDB"""

    def __init__(
        self,
        collection_name: str = "knowledge_base",
        persist_directory: Optional[str] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        """
        Args:
            collection_name: 集合名称
            persist_directory: 持久化目录
            embedding_service: 向量化服务
        """
        if chromadb is None:
            raise ImportError("请先安装 ChromaDB: pip install chromadb")

        self.collection_name = collection_name
        self.persist_directory = persist_directory or "./data/chroma_db"
        self.embedding_service = embedding_service

        # 创建客户端
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True,
            )
        )

        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
        )

        print(f"✅ 向量存储已初始化: {collection_name}")
        print(f"   持久化目录: {self.persist_directory}")
        print(f"   当前文档数: {self.collection.count()}")

    async def add_documents(
        self,
        embedding_results: List[EmbeddingResult],
        knowledge_base_id: Optional[str] = None
    ) -> List[str]:
        """
        添加文档到向量存储

        Args:
            embedding_results: 向量化结果列表
            knowledge_base_id: 知识库ID（用于隔离不同知识库）

        Returns:
            文档ID列表
        """
        if not embedding_results:
            return []

        ids = []
        documents = []
        embeddings = []
        metadatas = []

        for i, result in enumerate(embedding_results):
            # 生成唯一ID
            doc_id = f"{knowledge_base_id or 'kb'}_{result.index}_{hash(result.text) % 10000000}"

            # 准备元数据
            metadata = result.metadata.copy()
            metadata["knowledge_base_id"] = knowledge_base_id or "default"
            metadata["text_preview"] = result.text[:100]  # 预览用于调试

            # 序列化复杂类型
            for key, value in metadata.items():
                if isinstance(value, (list, dict)):
                    metadata[key] = json.dumps(value, ensure_ascii=False)

            ids.append(doc_id)
            documents.append(result.text)
            embeddings.append(result.embedding)
            metadatas.append(metadata)

        # 批量添加
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )

        print(f"✅ 已添加 {len(ids)} 个文档到向量存储")
        return ids

    async def search(
        self,
        query: str,
        top_k: int = 5,
        knowledge_base_id: Optional[str] = None,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索相似文档

        Args:
            query: 查询文本
            top_k: 返回结果数量
            knowledge_base_id: 知识库ID过滤
            filter_dict: 额外过滤条件

        Returns:
            搜索结果列表，包含文档内容和相似度分数
        """
        # 向量化查询
        if self.embedding_service is None:
            raise ValueError("需要提供 embedding_service 才能进行搜索")

        query_embedding = await self.embedding_service.embed(query)

        # 构建过滤条件
        where_clause = {}
        if knowledge_base_id:
            where_clause["knowledge_base_id"] = knowledge_base_id
        if filter_dict:
            where_clause.update(filter_dict)

        # 执行搜索
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_clause if where_clause else None,
            include=["documents", "metadatas", "distances"]
        )

        # 格式化结果
        search_results = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                # ChromaDB 返回的是距离（越小越相似），转换为相似度分数
                distance = results["distances"][0][i]
                similarity = 1 - distance  # 余弦距离转相似度

                search_results.append({
                    "id": doc_id,
                    "content": results["documents"][0][i],
                    "metadata": self._parse_metadata(results["metadatas"][0][i]),
                    "similarity": round(similarity, 4),
                    "rank": i + 1
                })

        return search_results

    def _parse_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """解析元数据中的JSON字符串"""
        parsed = {}
        for key, value in metadata.items():
            if isinstance(value, str):
                try:
                    parsed[key] = json.loads(value)
                except json.JSONDecodeError:
                    parsed[key] = value
            else:
                parsed[key] = value
        return parsed

    def delete_documents(
        self,
        doc_ids: Optional[List[str]] = None,
        knowledge_base_id: Optional[str] = None
    ) -> int:
        """
        删除文档

        Args:
            doc_ids: 要删除的文档ID列表
            knowledge_base_id: 删除整个知识库的所有文档

        Returns:
            删除的文档数量
        """
        if doc_ids:
            self.collection.delete(ids=doc_ids)
            return len(doc_ids)
        elif knowledge_base_id:
            self.collection.delete(
                where={"knowledge_base_id": knowledge_base_id}
            )
            return self.collection.count()
        else:
            raise ValueError("需要提供 doc_ids 或 knowledge_base_id")

    def get_documents(
        self,
        knowledge_base_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """获取知识库中的文档列表（按原始文件去重）"""
        where_clause = {"knowledge_base_id": knowledge_base_id} if knowledge_base_id else None
        results = self.collection.get(
            where=where_clause,
            include=["metadatas"]
        )

        # 按 source 去重，统计每个原始文件的 chunks 数
        docs_map: Dict[str, Dict[str, Any]] = {}
        if results["metadatas"]:
            for metadata in results["metadatas"]:
                source = metadata.get("source", "unknown")
                if source not in docs_map:
                    ft = metadata.get("file_type", "")
                    if ft and not ft.startswith("."):
                        ft = "." + ft
                    docs_map[source] = {
                        "filename": metadata.get("filename", Path(source).name),
                        "source": source,
                        "file_type": ft,
                        "chunks": 0,
                    }
                docs_map[source]["chunks"] += 1

        return sorted(docs_map.values(), key=lambda x: x["source"])

    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        return {
            "collection_name": self.collection_name,
            "total_documents": self.collection.count(),
            "persist_directory": self.persist_directory,
        }

    def list_knowledge_bases(self) -> List[str]:
        """列出所有知识库ID"""
        # 获取所有元数据
        results = self.collection.get(
            include=["metadatas"]
        )

        kb_ids = set()
        if results["metadatas"]:
            for metadata in results["metadatas"]:
                kb_id = metadata.get("knowledge_base_id", "default")
                kb_ids.add(kb_id)

        return sorted(list(kb_ids))

    def reset(self):
        """清空所有数据（谨慎使用）"""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        print(f"⚠️ 已清空集合: {self.collection_name}")


class SimpleVectorStore:
    """
    简单向量存储 - 纯 Python 实现，不依赖外部数据库
    适合小规模数据和测试
    """

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        persist_path: Optional[str] = None
    ):
        self.embedding_service = embedding_service
        self.persist_path = persist_path
        self.documents: Dict[str, Dict[str, Any]] = {}

        # 如果存在持久化文件，加载它
        if persist_path and os.path.exists(persist_path):
            self._load()

    async def add_documents(
        self,
        embedding_results: List[EmbeddingResult],
        knowledge_base_id: Optional[str] = None
    ) -> List[str]:
        """添加文档"""
        ids = []
        for result in embedding_results:
            doc_id = f"{knowledge_base_id or 'kb'}_{result.index}_{hash(result.text) % 10000000}"
            self.documents[doc_id] = {
                "text": result.text,
                "embedding": result.embedding,
                "metadata": {**(result.metadata or {}), "knowledge_base_id": knowledge_base_id or "default"},
            }
            ids.append(doc_id)

        if self.persist_path:
            self._save()

        return ids

    async def search(
        self,
        query: str,
        top_k: int = 5,
        knowledge_base_id: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """搜索相似文档"""
        if self.embedding_service is None:
            raise ValueError("需要提供 embedding_service")

        query_embedding = await self.embedding_service.embed(query)

        # 计算相似度
        similarities = []
        for doc_id, doc in self.documents.items():
            # 过滤知识库
            if knowledge_base_id:
                doc_kb = doc["metadata"].get("knowledge_base_id", "default")
                if doc_kb != knowledge_base_id:
                    continue

            # 计算余弦相似度
            doc_emb = np.array(doc["embedding"])
            query_emb = np.array(query_embedding)

            dot_product = np.dot(doc_emb, query_emb)
            norm_doc = np.linalg.norm(doc_emb)
            norm_query = np.linalg.norm(query_emb)

            if norm_doc > 0 and norm_query > 0:
                similarity = dot_product / (norm_doc * norm_query)
            else:
                similarity = 0.0

            similarities.append((doc_id, similarity))

        # 排序并返回前 top_k
        similarities.sort(key=lambda x: x[1], reverse=True)

        results = []
        for rank, (doc_id, similarity) in enumerate(similarities[:top_k], 1):
            doc = self.documents[doc_id]
            results.append({
                "id": doc_id,
                "content": doc["text"],
                "metadata": doc["metadata"],
                "similarity": round(similarity, 4),
                "rank": rank
            })

        return results

    def get_documents(
        self,
        knowledge_base_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """获取知识库中的文档列表（按原始文件去重）"""
        docs_map: Dict[str, Dict[str, Any]] = {}
        for doc_id, doc in self.documents.items():
            meta = doc.get("metadata", {})
            kb = meta.get("knowledge_base_id", "default")
            if knowledge_base_id and kb != knowledge_base_id:
                continue
            source = meta.get("source", doc_id)
            if source not in docs_map:
                ft = meta.get("file_type", "")
                if ft and not ft.startswith("."):
                    ft = "." + ft
                docs_map[source] = {
                    "filename": meta.get("filename", Path(source).name),
                    "source": source,
                    "file_type": ft,
                    "chunks": 0,
                }
            docs_map[source]["chunks"] += 1
        return sorted(docs_map.values(), key=lambda x: x["source"])

    def _save(self):
        """保存到文件"""
        if self.persist_path:
            os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)
            with open(self.persist_path, 'w', encoding='utf-8') as f:
                json.dump(self.documents, f, ensure_ascii=False, default=str)

    def _load(self):
        """从文件加载"""
        with open(self.persist_path, 'r', encoding='utf-8') as f:
            # 将列表转回 numpy 数组
            data = json.load(f)
            for doc_id, doc in data.items():
                doc["embedding"] = [float(x) for x in doc["embedding"]]
            self.documents = data

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_documents": len(self.documents),
            "persist_path": self.persist_path,
        }

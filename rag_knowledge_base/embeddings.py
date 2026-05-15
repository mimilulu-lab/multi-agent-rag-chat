"""
向量化模块 - 将文本转换为向量
支持多种 Embedding API：Kimi、OpenAI、本地模型等
"""
import hashlib
import os
from typing import List, Optional, Union
import asyncio
import aiohttp
import numpy as np
from dataclasses import dataclass

from .text_splitter import TextChunk


@dataclass
class EmbeddingResult:
    """向量化结果"""
    text: str
    embedding: List[float]
    metadata: dict
    index: int


class EmbeddingProvider:
    """向量提供商基类"""

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """将文本列表转换为向量列表"""
        raise NotImplementedError

    async def embed_chunks(self, chunks: List[TextChunk]) -> List[EmbeddingResult]:
        """将 TextChunk 列表转换为 EmbeddingResult"""
        texts = [chunk.content for chunk in chunks]
        embeddings = await self.embed(texts)

        return [
            EmbeddingResult(
                text=chunk.content,
                embedding=embedding,
                metadata=chunk.metadata,
                index=chunk.index
            )
            for chunk, embedding in zip(chunks, embeddings)
        ]


class KimiEmbeddingProvider(EmbeddingProvider):
    """Kimi (Moonshot) Embedding API"""

    API_URL = "https://api.moonshot.cn/v1/embeddings"
    MODEL = "text-embedding-v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("KIMI_API_KEY")
        if not self.api_key:
            raise ValueError("Kimi API Key 未提供")

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """调用 Kimi Embedding API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Kimi API 支持批量，但每次最多 100 条
        batch_size = 100
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            payload = {
                "model": self.MODEL,
                "input": batch
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.API_URL,
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Embedding API 错误: {response.status} - {error_text}")

                    data = await response.json()

                    # 按 index 排序
                    embeddings = sorted(
                        data["data"],
                        key=lambda x: x["index"]
                    )

                    all_embeddings.extend([e["embedding"] for e in embeddings])

        return all_embeddings


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI Embedding API"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "text-embedding-3-small"
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API Key 未提供")

        self.base_url = base_url or "https://api.openai.com/v1"
        self.model = model

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """调用 OpenAI Embedding API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        url = f"{self.base_url}/embeddings"

        batch_size = 100
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            payload = {
                "model": self.model,
                "input": batch
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Embedding API 错误: {response.status} - {error_text}")

                    data = await response.json()
                    embeddings = sorted(data["data"], key=lambda x: x["index"])
                    all_embeddings.extend([e["embedding"] for e in embeddings])

        return all_embeddings


class FakeEmbeddingProvider(EmbeddingProvider):
    """
    假的向量提供商，用于测试
    生成随机向量，不调用外部 API
    """

    def __init__(self, dimension: int = 1536, api_key: Optional[str] = None, **kwargs):
        self.dimension = dimension

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """生成随机向量"""
        # 使用文本的 hash 作为 seed，保证相同的文本得到相同的向量
        np.random.seed(42)
        embeddings = []
        for text in texts:
            # 基于文本内容生成伪随机向量
            seed = sum(ord(c) for c in text) % (2**32)
            np.random.seed(seed)
            embedding = np.random.randn(self.dimension).tolist()
            # 归一化
            norm = np.linalg.norm(embedding)
            embedding = [x / norm for x in embedding]
            embeddings.append(embedding)
        return embeddings


class EmbeddingService:
    """向量化服务 - 统一接口"""

    PROVIDERS = {
        "kimi": KimiEmbeddingProvider,
        "openai": OpenAIEmbeddingProvider,
        "fake": FakeEmbeddingProvider,
    }

    def __init__(
        self,
        provider: str = "kimi",
        api_key: Optional[str] = None,
        **kwargs
    ):
        """
        Args:
            provider: 提供商名称 ("kimi", "openai", "fake")
            api_key: API Key
            **kwargs: 其他参数传递给 Provider
        """
        provider_class = self.PROVIDERS.get(provider)
        if not provider_class:
            raise ValueError(f"不支持的提供商: {provider}")

        self.provider = provider_class(api_key=api_key, **kwargs)
        self._cache: dict = {}  # MD5(text) → embedding vector
        self._cache_hits = 0
        self._cache_misses = 0

    async def embed(self, texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        向量化文本（带缓存）

        Args:
            texts: 单个文本或文本列表

        Returns:
            单个向量或向量列表
        """
        single = isinstance(texts, str)
        if single:
            texts = [texts]

        results: List[Optional[List[float]]] = [None] * len(texts)
        to_embed_indices: List[int] = []
        to_embed_texts: List[str] = []

        # 1. 检查缓存
        for i, text in enumerate(texts):
            cache_key = hashlib.md5(text.encode('utf-8')).hexdigest()
            if cache_key in self._cache:
                results[i] = self._cache[cache_key]
                self._cache_hits += 1
            else:
                to_embed_indices.append(i)
                to_embed_texts.append(text)
                self._cache_misses += 1

        # 2. 批量向量化未命中的文本
        if to_embed_texts:
            new_embeddings = await self.provider.embed(to_embed_texts)
            for idx, (text_idx, text) in enumerate(zip(to_embed_indices, to_embed_texts)):
                cache_key = hashlib.md5(text.encode('utf-8')).hexdigest()
                self._cache[cache_key] = new_embeddings[idx]
                results[text_idx] = new_embeddings[idx]

        if single:
            return results[0]
        return results

    async def embed_chunks(self, chunks: List[TextChunk]) -> List[EmbeddingResult]:
        """向量化 TextChunk 列表"""
        return await self.provider.embed_chunks(chunks)

    def compute_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """计算两个向量的余弦相似度"""
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def compute_similarities(
        self,
        query_embedding: List[float],
        embeddings: List[List[float]]
    ) -> List[float]:
        """计算查询向量与多个文档向量的相似度"""
        return [
            self.compute_similarity(query_embedding, emb)
            for emb in embeddings
        ]

    def cache_stats(self) -> dict:
        """返回缓存统计信息"""
        total = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total if total > 0 else 0
        return {
            "cached_vectors": len(self._cache),
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": round(hit_rate, 3),
        }

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0


# 便捷函数
async def embed_texts(
    texts: List[str],
    provider: str = "kimi",
    api_key: Optional[str] = None
) -> List[List[float]]:
    """
    便捷函数：向量化文本列表

    Args:
        texts: 文本列表
        provider: 提供商 ("kimi", "openai", "fake")
        api_key: API Key

    Returns:
        向量列表
    """
    service = EmbeddingService(provider=provider, api_key=api_key)
    return await service.embed(texts)

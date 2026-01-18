"""
向量化缓存管理

提供多级缓存机制，加速向量化操作：
- 内存LRU缓存（快速访问）
- Redis缓存（持久化，可选）

Author: Qingyu AI Team
Date: 2025-10-28
"""

from typing import List, Dict, Optional
import hashlib
import json
from functools import lru_cache
from collections import OrderedDict

from src.core.config import settings
from src.core.logger import logger
from src.core.exceptions import CacheError


class LRUCache:
    """
    内存LRU（Least Recently Used）缓存

    使用OrderedDict实现，自动淘汰最久未使用的项
    """

    def __init__(self, capacity: int = 1000):
        """
        初始化LRU缓存

        Args:
            capacity: 最大容量
        """
        self.capacity = capacity
        self.cache: OrderedDict = OrderedDict()
        self._hit_count = 0
        self._miss_count = 0

        logger.info("lru_cache_initialized", capacity=capacity)

    def get(self, key: str) -> Optional[List[float]]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            向量或None
        """
        if key in self.cache:
            # 移到末尾（最近使用）
            self.cache.move_to_end(key)
            self._hit_count += 1
            logger.debug("lru_cache_hit", key=key[:50])
            return self.cache[key]

        self._miss_count += 1
        logger.debug("lru_cache_miss", key=key[:50])
        return None

    def set(self, key: str, value: List[float]):
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 向量
        """
        if key in self.cache:
            # 更新并移到末尾
            self.cache.move_to_end(key)
        else:
            # 新增，检查容量
            if len(self.cache) >= self.capacity:
                # 移除最久未使用的项
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                logger.debug("lru_cache_evict", evicted_key=oldest_key[:50])

        self.cache[key] = value
        logger.debug("lru_cache_set", key=key[:50], size=len(self.cache))

    def get_stats(self) -> Dict:
        """
        获取缓存统计信息

        Returns:
            统计字典
        """
        total = self._hit_count + self._miss_count
        hit_rate = (self._hit_count / total * 100) if total > 0 else 0

        return {
            "size": len(self.cache),
            "capacity": self.capacity,
            "hit_count": self._hit_count,
            "miss_count": self._miss_count,
            "total_requests": total,
            "hit_rate_percent": round(hit_rate, 2),
            "usage_percent": round(len(self.cache) / self.capacity * 100, 2)
        }

    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self._hit_count = 0
        self._miss_count = 0
        logger.info("lru_cache_cleared")


class EmbeddingCache:
    """
    向量化缓存管理器

    提供多级缓存：
    1. 内存LRU缓存（毫秒级）
    2. Redis缓存（毫秒级，可选）

    使用文本hash作为key，避免存储重复向量
    """

    def __init__(
        self,
        redis_client=None,
        lru_size: int = None,
        ttl: int = None,
        enabled: bool = None
    ):
        """
        初始化缓存管理器

        Args:
            redis_client: Redis客户端（可选）
            lru_size: LRU缓存大小
            ttl: Redis缓存TTL（秒）
            enabled: 是否启用缓存
        """
        self.enabled = enabled if enabled is not None else settings.embedding_cache_enabled
        self.lru_size = lru_size or 1000
        self.ttl = ttl or settings.embedding_cache_ttl
        self.redis_client = redis_client

        # 内存LRU缓存（总是启用）
        self.lru_cache = LRUCache(capacity=self.lru_size)

        # Redis缓存（可选）
        self.redis_enabled = redis_client is not None

        logger.info(
            "embedding_cache_initialized",
            enabled=self.enabled,
            lru_size=self.lru_size,
            redis_enabled=self.redis_enabled,
            ttl=self.ttl
        )

    def _make_key(self, text: str, model: str) -> str:
        """
        生成缓存键

        使用SHA256哈希文本+模型名称

        Args:
            text: 文本
            model: 模型名称

        Returns:
            缓存键
        """
        content = f"{model}:{text}"
        hash_obj = hashlib.sha256(content.encode('utf-8'))
        return f"embed:{hash_obj.hexdigest()}"

    async def get(
        self,
        text: str,
        model: str
    ) -> Optional[List[float]]:
        """
        获取缓存的向量

        优先查找LRU缓存，然后查找Redis

        Args:
            text: 文本
            model: 模型名称

        Returns:
            向量或None
        """
        if not self.enabled:
            return None

        key = self._make_key(text, model)

        # 1. 查找LRU缓存
        embedding = self.lru_cache.get(key)
        if embedding is not None:
            logger.debug("embedding_cache_hit_lru", model=model)
            return embedding

        # 2. 查找Redis缓存
        if self.redis_enabled:
            try:
                redis_value = await self.redis_client.get(key)
                if redis_value:
                    embedding = json.loads(redis_value)
                    # 回填到LRU缓存
                    self.lru_cache.set(key, embedding)
                    logger.debug("embedding_cache_hit_redis", model=model)
                    return embedding
            except Exception as e:
                logger.warning(
                    "redis_cache_get_failed",
                    key=key[:50],
                    error=str(e)
                )

        logger.debug("embedding_cache_miss", model=model)
        return None

    async def set(
        self,
        text: str,
        model: str,
        embedding: List[float],
        ttl: Optional[int] = None
    ):
        """
        设置缓存

        同时写入LRU和Redis（如果启用）

        Args:
            text: 文本
            model: 模型名称
            embedding: 向量
            ttl: TTL（秒），默认使用配置的值
        """
        if not self.enabled:
            return

        key = self._make_key(text, model)
        ttl = ttl or self.ttl

        # 1. 写入LRU缓存
        self.lru_cache.set(key, embedding)

        # 2. 写入Redis缓存
        if self.redis_enabled:
            try:
                redis_value = json.dumps(embedding)
                await self.redis_client.setex(key, ttl, redis_value)
                logger.debug(
                    "embedding_cache_set_redis",
                    model=model,
                    ttl=ttl
                )
            except Exception as e:
                logger.warning(
                    "redis_cache_set_failed",
                    key=key[:50],
                    error=str(e)
                )

    async def get_batch(
        self,
        texts: List[str],
        model: str
    ) -> Dict[str, List[float]]:
        """
        批量获取缓存

        Args:
            texts: 文本列表
            model: 模型名称

        Returns:
            {text: embedding} 字典（只包含命中的）
        """
        if not self.enabled:
            return {}

        result = {}

        for text in texts:
            embedding = await self.get(text, model)
            if embedding is not None:
                result[text] = embedding

        logger.debug(
            "embedding_cache_batch_get",
            total=len(texts),
            hits=len(result),
            hit_rate=f"{len(result)/len(texts)*100:.1f}%"
        )

        return result

    async def set_batch(
        self,
        data: Dict[str, List[float]],
        model: str,
        ttl: Optional[int] = None
    ):
        """
        批量设置缓存

        Args:
            data: {text: embedding} 字典
            model: 模型名称
            ttl: TTL（秒）
        """
        if not self.enabled:
            return

        for text, embedding in data.items():
            await self.set(text, model, embedding, ttl)

        logger.debug(
            "embedding_cache_batch_set",
            count=len(data),
            model=model
        )

    def get_stats(self) -> Dict:
        """
        获取缓存统计信息

        Returns:
            统计字典
        """
        stats = {
            "enabled": self.enabled,
            "lru": self.lru_cache.get_stats(),
            "redis_enabled": self.redis_enabled
        }

        return stats

    def clear(self):
        """清空所有缓存"""
        self.lru_cache.clear()

        if self.redis_enabled:
            # Redis需要异步清除，这里只记录日志
            logger.warning(
                "redis_cache_clear_skipped",
                message="Redis cache needs to be cleared manually or via async method"
            )

        logger.info("embedding_cache_cleared")


# 全局单例
_embedding_cache_instance: Optional[EmbeddingCache] = None


def get_embedding_cache(redis_client=None) -> EmbeddingCache:
    """
    获取全局EmbeddingCache实例（单例模式）

    Args:
        redis_client: Redis客户端（首次调用时设置）

    Returns:
        EmbeddingCache实例
    """
    global _embedding_cache_instance

    if _embedding_cache_instance is None:
        _embedding_cache_instance = EmbeddingCache(redis_client=redis_client)

    return _embedding_cache_instance


"""RAG Service - RAG服务

管理RAG系统的索引和检索
"""

import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from collections import defaultdict

from src.core.logger import get_logger
from src.rag.rag_pipeline import RAGPipeline

logger = get_logger(__name__)


class RAGService:
    """RAG服务

    特性：
    - 文档索引
    - 混合检索
    - 健康检查
    """

    def __init__(self):
        """初始化服务"""
        self.rag_pipeline: Optional[RAGPipeline] = None
        self._initialized = False

        # 查询缓存
        self._cache_enabled = False
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl_seconds = 300  # 5分钟

        # 统计信息
        self._stats = defaultdict(lambda: {
            "total_searches": 0,
            "total_indexes": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        })

        logger.info("RAGService created")

    async def initialize(self) -> None:
        """初始化服务"""
        if self._initialized:
            return

        logger.info("Initializing RAGService...")

        # 初始化RAG Pipeline
        self.rag_pipeline = RAGPipeline()
        await self.rag_pipeline.initialize()

        self._initialized = True
        logger.info("RAGService initialized successfully")

    async def search(
        self,
        query_text: str,
        project_id: str,
        user_id: Optional[str] = None,
        content_types: Optional[List[str]] = None,
        top_k: int = 5,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """检索相关文档

        Args:
            query_text: 查询文本
            project_id: 项目ID
            user_id: 用户ID
            content_types: 内容类型过滤
            top_k: 返回结果数量
            use_cache: 是否使用缓存

        Returns:
            检索结果列表
        """
        if not self._initialized:
            await self.initialize()

        logger.info(
            "RAG search",
            query_length=len(query_text),
            project_id=project_id,
            top_k=top_k,
            content_types=content_types,
        )

        # 更新统计
        self._stats[project_id]["total_searches"] += 1

        try:
            # 检查缓存
            cache_key = None
            if use_cache and self._cache_enabled:
                cache_key = self._make_cache_key(
                    query_text, project_id, content_types, top_k
                )
                cached_result = self._get_from_cache(cache_key)
                if cached_result is not None:
                    self._stats[project_id]["cache_hits"] += 1
                    logger.info("RAG search cache hit")
                    return cached_result
                else:
                    self._stats[project_id]["cache_misses"] += 1

            # 调用RAG Pipeline
            results = await self.rag_pipeline.search(
                query_text=query_text,
                project_id=project_id,
                content_types=content_types,
                top_k=top_k,
            )

            # 缓存结果
            if use_cache and self._cache_enabled and cache_key:
                self._put_to_cache(cache_key, results)

            logger.info(f"RAG search completed", results_count=len(results))
            return results

        except Exception as e:
            logger.error(f"RAG search failed: {e}", exc_info=True)
            raise

    async def index(
        self,
        document_id: str,
        content: str,
        metadata: Dict[str, Any],
        project_id: str,
        user_id: Optional[str] = None,
    ) -> bool:
        """索引文档

        Args:
            document_id: 文档ID
            content: 文档内容
            metadata: 元数据
            project_id: 项目ID
            user_id: 用户ID

        Returns:
            是否成功
        """
        if not self._initialized:
            await self.initialize()

        logger.info(
            "Indexing document",
            document_id=document_id,
            content_length=len(content),
            project_id=project_id,
        )

        try:
            # 调用RAG Pipeline的索引方法
            await self.rag_pipeline.index_document(
                document_id=document_id,
                content=content,
                metadata=metadata,
                project_id=project_id,
            )

            # 更新统计
            self._stats[project_id]["total_indexes"] += 1

            # 清除相关缓存
            if self._cache_enabled:
                self._invalidate_cache_for_project(project_id)

            logger.info(f"Document indexed successfully", document_id=document_id)
            return True

        except Exception as e:
            logger.error(f"Document indexing failed: {e}", exc_info=True)
            return False

    async def index_batch(
        self,
        documents: List[Dict[str, Any]],
        project_id: str,
        user_id: Optional[str] = None,
        parallel: bool = True,
    ) -> Dict[str, Any]:
        """批量索引文档

        Args:
            documents: 文档列表，每项包含 {document_id, content, metadata}
            project_id: 项目ID
            user_id: 用户ID
            parallel: 是否并行执行

        Returns:
            批量索引结果 {success_count, failure_count, errors}
        """
        if not self._initialized:
            await self.initialize()

        logger.info(f"Batch indexing {len(documents)} documents", project_id=project_id)

        success_count = 0
        failure_count = 0
        errors = []

        if parallel:
            # 并行索引
            tasks = [
                self.index(
                    document_id=doc["document_id"],
                    content=doc["content"],
                    metadata=doc.get("metadata", {}),
                    project_id=project_id,
                    user_id=user_id,
                )
                for doc in documents
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failure_count += 1
                    errors.append({
                        "document_id": documents[i]["document_id"],
                        "error": str(result)
                    })
                elif result:
                    success_count += 1
                else:
                    failure_count += 1
        else:
            # 顺序索引
            for doc in documents:
                try:
                    success = await self.index(
                        document_id=doc["document_id"],
                        content=doc["content"],
                        metadata=doc.get("metadata", {}),
                        project_id=project_id,
                        user_id=user_id,
                    )
                    if success:
                        success_count += 1
                    else:
                        failure_count += 1
                except Exception as e:
                    failure_count += 1
                    errors.append({
                        "document_id": doc["document_id"],
                        "error": str(e)
                    })

        logger.info(
            f"Batch indexing completed",
            success_count=success_count,
            failure_count=failure_count,
        )

        return {
            "success_count": success_count,
            "failure_count": failure_count,
            "errors": errors,
        }

    async def update(
        self,
        document_id: str,
        content: str,
        metadata: Dict[str, Any],
        project_id: str,
        user_id: Optional[str] = None,
    ) -> bool:
        """更新文档索引

        Args:
            document_id: 文档ID
            content: 新内容
            metadata: 新元数据
            project_id: 项目ID
            user_id: 用户ID

        Returns:
            是否成功
        """
        # 先删除后索引
        try:
            await self.delete(document_id, project_id)
            return await self.index(document_id, content, metadata, project_id, user_id)
        except Exception as e:
            logger.error(f"Document update failed: {e}", exc_info=True)
            return False

    async def delete(
        self,
        document_id: str,
        project_id: str,
    ) -> bool:
        """删除文档索引

        Args:
            document_id: 文档ID
            project_id: 项目ID

        Returns:
            是否成功
        """
        if not self._initialized:
            await self.initialize()

        logger.info("Deleting document index", document_id=document_id)

        try:
            # 调用RAG Pipeline的删除方法
            await self.rag_pipeline.delete_document(
                document_id=document_id,
                project_id=project_id,
            )

            # 清除相关缓存
            if self._cache_enabled:
                self._invalidate_cache_for_project(project_id)

            logger.info(f"Document index deleted", document_id=document_id)
            return True

        except Exception as e:
            logger.error(f"Document deletion failed: {e}", exc_info=True)
            return False

    def _make_cache_key(
        self,
        query_text: str,
        project_id: str,
        content_types: Optional[List[str]],
        top_k: int,
    ) -> str:
        """生成缓存键

        Args:
            query_text: 查询文本
            project_id: 项目ID
            content_types: 内容类型
            top_k: 返回数量

        Returns:
            缓存键
        """
        # 使用哈希确保键长度一致
        content_types_str = ",".join(sorted(content_types)) if content_types else ""
        key_str = f"{query_text}:{project_id}:{content_types_str}:{top_k}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """从缓存获取

        Args:
            cache_key: 缓存键

        Returns:
            缓存的结果（如果存在且未过期）
        """
        if cache_key not in self._cache:
            return None

        entry = self._cache[cache_key]
        expires_at = entry["expires_at"]

        # 检查是否过期
        if datetime.utcnow() > expires_at:
            del self._cache[cache_key]
            return None

        return entry["results"]

    def _put_to_cache(self, cache_key: str, results: List[Dict[str, Any]]) -> None:
        """放入缓存

        Args:
            cache_key: 缓存键
            results: 结果
        """
        expires_at = datetime.utcnow() + timedelta(seconds=self._cache_ttl_seconds)
        self._cache[cache_key] = {
            "results": results,
            "expires_at": expires_at,
        }

    def _invalidate_cache_for_project(self, project_id: str) -> None:
        """清除项目相关的缓存

        Args:
            project_id: 项目ID
        """
        # 简单实现：清空所有缓存
        # 生产环境应该有更精细的缓存失效策略
        self._cache.clear()
        logger.info(f"Invalidated cache for project", project_id=project_id)

    def enable_cache(self, enabled: bool = True, ttl_seconds: int = 300) -> None:
        """启用/禁用缓存

        Args:
            enabled: 是否启用
            ttl_seconds: 缓存TTL（秒）
        """
        self._cache_enabled = enabled
        self._cache_ttl_seconds = ttl_seconds
        if not enabled:
            self._cache.clear()
        logger.info(
            f"RAG cache {'enabled' if enabled else 'disabled'}",
            ttl_seconds=ttl_seconds
        )

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()
        logger.info("RAG cache cleared")

    def get_stats(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """获取统计信息

        Args:
            project_id: 项目ID（可选，None表示所有项目）

        Returns:
            统计信息
        """
        if project_id:
            return dict(self._stats.get(project_id, {}))
        else:
            return {
                pid: dict(stats)
                for pid, stats in self._stats.items()
            }

    async def health_check(self) -> Dict[str, Any]:
        """健康检查

        Returns:
            健康状态
        """
        if not self._initialized:
            return {"healthy": False, "reason": "Not initialized"}

        try:
            # 检查RAG Pipeline健康状态
            pipeline_healthy = await self.rag_pipeline.health_check()

            total_searches = sum(
                stats["total_searches"] for stats in self._stats.values()
            )
            total_indexes = sum(
                stats["total_indexes"] for stats in self._stats.values()
            )

            return {
                "healthy": pipeline_healthy,
                "components": {
                    "embedding": pipeline_healthy,
                    "vector_db": pipeline_healthy,
                },
                "stats": {
                    "total_searches": total_searches,
                    "total_indexes": total_indexes,
                    "cache_enabled": self._cache_enabled,
                    "cache_size": len(self._cache),
                },
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"healthy": False, "error": str(e)}

    async def close(self) -> None:
        """关闭服务"""
        if self.rag_pipeline:
            await self.rag_pipeline.close()
        self._cache.clear()
        logger.info("RAGService closed")


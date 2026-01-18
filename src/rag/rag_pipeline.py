"""
RAG Pipeline - 端到端RAG流程

提供完整的RAG（Retrieval Augmented Generation）流程：
1. 检索相关文档
2. 可选重排序
3. 构建上下文
4. 引用标注

Author: Qingyu AI Team
Date: 2025-10-28
"""

from typing import List, Dict, Any, Optional
import asyncio

from src.rag.schemas import RetrievalResult, RAGContext
from src.rag.embedding_manager import EmbeddingManager
from src.rag.milvus_client import MilvusClient
from src.core.logger import get_logger
from src.core.config import settings
from src.core.exceptions import RAGError

logger = get_logger(__name__)


class RAGPipeline:
    """
    RAG Pipeline

    端到端的RAG流程编排，提供统一的检索和上下文构建接口
    """

    def __init__(
        self,
        embedding_manager: EmbeddingManager,
        milvus_client: MilvusClient,
        reranker: Optional[Any] = None,  # Optional[Reranker]
        context_builder: Optional[Any] = None  # Optional[ContextBuilder]
    ):
        """
        初始化RAG Pipeline

        Args:
            embedding_manager: 向量化管理器
            milvus_client: Milvus客户端
            reranker: 重排序器（可选）
            context_builder: 上下文构建器（可选）
        """
        self.embedding_manager = embedding_manager
        self.milvus_client = milvus_client
        self.reranker = reranker
        self.context_builder = context_builder

        # 从配置加载参数
        self.default_top_k = settings.rag_top_k
        self.default_rerank_top_k = settings.rag_rerank_top_k
        self.default_max_tokens = settings.rag_max_context_tokens
        self.use_reranker = settings.rag_use_reranker and reranker is not None

        logger.info(
            "rag_pipeline_initialized",
            use_reranker=self.use_reranker,
            default_top_k=self.default_top_k
        )

    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict] = None
    ) -> List[RetrievalResult]:
        """
        检索相关文档

        Args:
            query: 查询文本
            top_k: 返回结果数量
            filters: 元数据过滤条件

        Returns:
            检索结果列表

        Raises:
            RAGError: 检索失败
        """
        try:
            top_k = top_k or self.default_top_k

            logger.info("rag_retrieve_start", query=query[:50], top_k=top_k)

            # 1. 向量化查询
            query_vector = await self.embedding_manager.embed_query(query)

            # 2. 向量检索
            search_results = self.milvus_client.search(
                query_vectors=[query_vector],
                top_k=top_k,
                filter_expr=self._build_filter_expr(filters) if filters else None
            )

            # 3. 转换为RetrievalResult
            results = []
            for hit in search_results[0]:  # search_results是嵌套列表
                entity = hit.get('entity', {})
                result = RetrievalResult(
                    id=entity.get('id', ''),
                    text=entity.get('text', ''),
                    score=float(hit.get('distance', 0.0)),
                    source=entity.get('source', 'unknown'),
                    document_id=entity.get('document_id', ''),
                    chunk_id=int(entity.get('chunk_id', 0)),
                    metadata=entity.get('metadata', {})
                )
                results.append(result)

            logger.info(
                "rag_retrieve_success",
                query=query[:50],
                result_count=len(results)
            )

            return results

        except Exception as e:
            logger.error(
                "rag_retrieve_failed",
                query=query[:50],
                error=str(e)
            )
            raise RAGError(
                f"Failed to retrieve documents: {str(e)}",
                details={"query": query[:100]}
            ) from e

    async def retrieve_and_rerank(
        self,
        query: str,
        top_k: Optional[int] = None,
        rerank_top_k: Optional[int] = None
    ) -> List[RetrievalResult]:
        """
        检索并重排序

        先进行向量检索，然后使用Reranker重排序

        Args:
            query: 查询文本
            top_k: 初始检索数量（传给向量检索）
            rerank_top_k: 重排序后返回数量

        Returns:
            重排序后的结果列表
        """
        try:
            top_k = top_k or self.default_top_k * 2  # 检索更多，然后重排序
            rerank_top_k = rerank_top_k or self.default_rerank_top_k

            # 1. 向量检索
            results = await self.retrieve(query, top_k=top_k)

            if not results:
                return []

            # 2. 重排序（如果启用）
            if self.use_reranker and self.reranker:
                logger.info("rag_reranking", query=query[:50], result_count=len(results))

                # 提取文本列表
                texts = [r.text for r in results]

                # 调用reranker
                reranked_indices = await self.reranker.rerank(
                    query=query,
                    documents=texts,
                    top_k=rerank_top_k
                )

                # 按新排序重组结果
                reranked_results = []
                for idx, score in reranked_indices[:rerank_top_k]:
                    result = results[idx]
                    # 更新分数为rerank分数
                    result.score = score
                    reranked_results.append(result)

                logger.info(
                    "rag_rerank_success",
                    original_count=len(results),
                    reranked_count=len(reranked_results)
                )

                return reranked_results
            else:
                # 不使用reranker，直接返回top_k结果
                return results[:rerank_top_k]

        except Exception as e:
            logger.error(
                "rag_rerank_failed",
                query=query[:50],
                error=str(e)
            )
            # 重排序失败，降级到原始结果
            return results[:rerank_top_k] if 'results' in locals() else []

    async def build_context(
        self,
        query: str,
        results: List[RetrievalResult],
        max_tokens: Optional[int] = None,
        template: Optional[str] = None
    ) -> str:
        """
        构建RAG上下文

        Args:
            query: 查询文本
            results: 检索结果
            max_tokens: 最大token数
            template: 自定义模板

        Returns:
            构建的上下文文本
        """
        if not results:
            return f"没有找到与「{query}」相关的资料。"

        # 使用ContextBuilder（如果有）
        if self.context_builder:
            return self.context_builder.build_context(
                query=query,
                results=results,
                max_tokens=max_tokens or self.default_max_tokens,
                template=template
            )

        # 简单的上下文构建（默认）
        max_tokens = max_tokens or self.default_max_tokens

        context_parts = ["基于以下参考资料回答问题：\n"]

        # 添加每个资料
        for i, result in enumerate(results, 1):
            source_text = f"\n[资料{i}] 来源：{result.source}\n{result.text}\n"
            context_parts.append(source_text)

            # 简单的token估算（中文约1.5字符/token）
            estimated_tokens = len("".join(context_parts)) / 1.5
            if estimated_tokens > max_tokens * 0.8:  # 留20%给问题和提示
                break

        context_parts.append(f"\n问题：{query}\n")
        context_parts.append("请基于上述资料回答，并在回答中标注引用来源（如[1]、[2]）。")

        return "".join(context_parts)

    async def retrieve_with_context(
        self,
        query: str,
        top_k: Optional[int] = None,
        max_tokens: Optional[int] = None,
        use_reranker: Optional[bool] = None
    ) -> RAGContext:
        """
        完整RAG流程（检索+上下文构建）

        Args:
            query: 查询文本
            top_k: 返回结果数量
            max_tokens: 最大token数
            use_reranker: 是否使用重排序

        Returns:
            RAGContext对象
        """
        try:
            logger.info("rag_full_pipeline_start", query=query[:50])

            # 决定是否使用reranker
            should_rerank = (
                use_reranker if use_reranker is not None
                else self.use_reranker
            )

            # 1. 检索
            if should_rerank:
                results = await self.retrieve_and_rerank(
                    query=query,
                    rerank_top_k=top_k
                )
            else:
                results = await self.retrieve(
                    query=query,
                    top_k=top_k
                )

            # 2. 构建上下文
            context_text = await self.build_context(
                query=query,
                results=results,
                max_tokens=max_tokens
            )

            # 3. 估算token数（简单估算）
            estimated_tokens = len(context_text) / 1.5

            # 4. 构建RAGContext
            rag_context = RAGContext(
                query=query,
                context=context_text,
                sources=results,
                total_tokens=int(estimated_tokens),
                retrieved_count=len(results),
                reranked=should_rerank,
                metadata={
                    'top_k': top_k or self.default_top_k,
                    'max_tokens': max_tokens or self.default_max_tokens
                }
            )

            logger.info(
                "rag_full_pipeline_success",
                query=query[:50],
                source_count=len(results),
                total_tokens=rag_context.total_tokens
            )

            return rag_context

        except Exception as e:
            logger.error(
                "rag_full_pipeline_failed",
                query=query[:50],
                error=str(e)
            )
            raise RAGError(
                f"RAG pipeline failed: {str(e)}",
                details={"query": query[:100]}
            ) from e

    def _build_filter_expr(self, filters: Dict) -> str:
        """
        构建Milvus过滤表达式

        Args:
            filters: 过滤条件字典

        Returns:
            过滤表达式字符串
        """
        expressions = []

        for key, value in filters.items():
            if isinstance(value, str):
                expressions.append(f'{key} == "{value}"')
            elif isinstance(value, (int, float)):
                expressions.append(f'{key} == {value}')
            elif isinstance(value, list):
                # IN操作
                if isinstance(value[0], str):
                    values_str = ', '.join([f'"{v}"' for v in value])
                else:
                    values_str = ', '.join([str(v) for v in value])
                expressions.append(f'{key} in [{values_str}]')

        return ' and '.join(expressions) if expressions else ""

    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查

        Returns:
            健康状态字典
        """
        try:
            # 检查各组件
            embedding_health = await self.embedding_manager.health_check()
            milvus_health = self.milvus_client.health_check()

            return {
                "status": "healthy",
                "embedding_manager": embedding_health.get("status", "unknown"),
                "milvus_client": "healthy" if milvus_health else "unhealthy",
                "reranker_enabled": self.use_reranker
            }

        except Exception as e:
            logger.error("rag_health_check_failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# 全局单例（可选）
_rag_pipeline_instance: Optional[RAGPipeline] = None


def get_rag_pipeline(
    embedding_manager: Optional[EmbeddingManager] = None,
    milvus_client: Optional[MilvusClient] = None
) -> RAGPipeline:
    """
    获取全局RAGPipeline实例（单例模式）

    Args:
        embedding_manager: 向量化管理器（首次调用时设置）
        milvus_client: Milvus客户端（首次调用时设置）

    Returns:
        RAGPipeline实例
    """
    global _rag_pipeline_instance

    if _rag_pipeline_instance is None:
        if embedding_manager is None or milvus_client is None:
            raise ValueError(
                "First call to get_rag_pipeline requires "
                "embedding_manager and milvus_client"
            )
        _rag_pipeline_instance = RAGPipeline(
            embedding_manager=embedding_manager,
            milvus_client=milvus_client
        )

    return _rag_pipeline_instance


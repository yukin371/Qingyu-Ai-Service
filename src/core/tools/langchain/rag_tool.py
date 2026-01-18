"""RAG检索工具

从向量数据库检索相关知识
"""

from typing import List, Optional

from pydantic import Field

from src.core.logger import get_logger
from src.core.tools.base import BaseTool, ToolInputSchema, ToolMetadata, ToolResult

logger = get_logger(__name__)


class RAGToolInput(ToolInputSchema):
    """RAG工具输入"""

    query: str = Field(..., description="查询文本")
    project_id: str = Field(..., description="项目ID")
    content_types: Optional[List[str]] = Field(
        None, description="内容类型过滤: character, location, outline, timeline"
    )
    top_k: int = Field(default=5, description="返回结果数量", ge=1, le=20)
    enable_rerank: bool = Field(default=True, description="是否启用重排序")


class RAGTool(BaseTool):
    """RAG检索工具

    从向量数据库检索项目相关知识，支持：
    - 内容类型过滤
    - 混合检索（向量+元数据）
    - 结果重排序
    """

    def __init__(self, rag_service=None, auth_context: dict = None):
        """初始化

        Args:
            rag_service: RAG服务实例（可选，用于测试）
            auth_context: 认证上下文
        """
        metadata = ToolMetadata(
            name="rag_tool",
            description="检索项目相关知识，包括角色、设定、大纲、时间线等内容",
            category="knowledge",
            requires_auth=True,
            requires_project=True,
            timeout_seconds=10,
        )
        super().__init__(metadata, auth_context)

        # RAG服务（延迟注入）
        self._rag_service = rag_service

    @property
    def input_schema(self):
        return RAGToolInput

    async def _execute_impl(self, validated_input: RAGToolInput) -> ToolResult:
        """执行RAG检索

        Args:
            validated_input: 已验证的输入

        Returns:
            检索结果
        """
        try:
            # 获取RAG服务
            if not self._rag_service:
                # 延迟导入避免循环依赖
                from rag.rag_pipeline import RAGPipeline

                self._rag_service = RAGPipeline()
                await self._rag_service.initialize()

            # 构建检索请求
            search_params = {
                "query_text": validated_input.query,
                "project_id": validated_input.project_id,
                "top_k": validated_input.top_k,
            }

            # 添加内容类型过滤
            if validated_input.content_types:
                search_params["content_types"] = validated_input.content_types

            self.logger.info(
                "Executing RAG search",
                query=validated_input.query[:100],
                project_id=validated_input.project_id,
                top_k=validated_input.top_k,
                content_types=validated_input.content_types,
            )

            # 执行检索
            search_results = await self._rag_service.search(**search_params)

            # 可选重排序
            if validated_input.enable_rerank and search_results:
                self.logger.debug("Reranking enabled, applying reranker")
                # TODO: 实现Reranker
                # reranker = Reranker()
                # search_results = reranker.rerank(
                #     query=validated_input.query,
                #     results=search_results,
                #     top_k=validated_input.top_k
                # )

            # 格式化结果
            formatted_results = []
            for result in search_results:
                formatted_results.append({
                    "content": result.get("text", ""),
                    "score": result.get("score", 0.0),
                    "content_type": result.get("metadata", {}).get("content_type", ""),
                    "document_id": result.get("document_id", ""),
                    "chunk_id": result.get("chunk_id", ""),
                    "metadata": result.get("metadata", {}),
                })

            self.logger.info(
                "RAG search completed",
                results_count=len(formatted_results),
                top_score=formatted_results[0]["score"] if formatted_results else 0,
            )

            return ToolResult(
                success=True,
                data={
                    "results": formatted_results,
                    "total": len(formatted_results),
                    "query": validated_input.query,
                },
                metadata={
                    "query": validated_input.query,
                    "project_id": validated_input.project_id,
                    "top_k": validated_input.top_k,
                    "reranked": validated_input.enable_rerank,
                },
            )

        except Exception as e:
            self.logger.error(f"RAG search failed: {e}", exc_info=True)
            return ToolResult(success=False, error=f"RAG search failed: {str(e)}")


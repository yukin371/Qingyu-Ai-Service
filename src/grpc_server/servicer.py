"""
gRPC Servicer 实现
"""
import json
from typing import Any, Optional

import grpc
from google.protobuf import timestamp_pb2

from src.core.logger import get_logger
from src.services.agent_service import AgentService
from src.services.rag_service import RAGService

from . import ai_service_pb2, ai_service_pb2_grpc

logger = get_logger(__name__)


class AIServicer(ai_service_pb2_grpc.AIServiceServicer):
    """AI Service gRPC 实现"""

    def __init__(
        self,
        agent_service: Optional[AgentService] = None,
        rag_service: Optional[RAGService] = None,
    ):
        """初始化服务

        Args:
            agent_service: Agent服务实例
            rag_service: RAG服务实例
        """
        logger.info("Initializing AIServicer")

        # 服务依赖
        self.agent_service = agent_service or AgentService()
        self.rag_service = rag_service or RAGService()

        logger.info("AIServicer initialized")

    async def GenerateContent(
        self,
        request: ai_service_pb2.GenerateContentRequest,
        context: grpc.aio.ServicerContext
    ) -> ai_service_pb2.GenerateContentResponse:
        """生成内容"""
        logger.info(
            "generate_content_called",
            project_id=request.project_id,
            chapter_id=request.chapter_id
        )

        try:
            # TODO: 实现内容生成逻辑
            # 1. 获取上下文
            # 2. 构建 Prompt
            # 3. 调用 LLM
            # 4. 返回结果

            return ai_service_pb2.GenerateContentResponse(
                content="TODO: Implement content generation",
                tokens_used=0,
                model=request.options.model if request.options else "gpt-4",
                generated_at=int(timestamp_pb2.Timestamp().GetCurrentTime().seconds)
            )

        except Exception as e:
            logger.error("generate_content_failed", error=str(e), exc_info=True)
            await context.abort(
                grpc.StatusCode.INTERNAL,
                f"Failed to generate content: {str(e)}"
            )

    async def QueryKnowledge(
        self,
        request: ai_service_pb2.RAGQueryRequest,
        context: grpc.aio.ServicerContext
    ) -> ai_service_pb2.RAGQueryResponse:
        """RAG 查询"""
        logger.info(
            "QueryKnowledge called",
            query=request.query[:100],
            project_id=request.project_id,
            top_k=request.top_k
        )

        try:
            # 调用RAG服务
            results = await self.rag_service.search(
                query_text=request.query,
                project_id=request.project_id,
                user_id=request.user_id or None,
                content_types=list(request.content_types) if request.content_types else None,
                top_k=request.top_k or 5,
            )

            # 转换为gRPC响应
            rag_results = []
            for result in results:
                rag_results.append(
                    ai_service_pb2.RAGResult(
                        text=result.get("text", ""),
                        score=result.get("score", 0.0),
                        document_id=result.get("document_id", ""),
                        chunk_id=result.get("chunk_id", ""),
                        metadata=json.dumps(result.get("metadata", {})),
                    )
                )

            logger.info("QueryKnowledge completed", results_count=len(rag_results))

            return ai_service_pb2.RAGQueryResponse(
                results=rag_results,
                total=len(rag_results)
            )

        except Exception as e:
            logger.error("QueryKnowledge failed", error=str(e), exc_info=True)
            await context.abort(
                grpc.StatusCode.INTERNAL,
                f"Failed to query knowledge: {str(e)}"
            )

    async def GetContext(
        self,
        request: ai_service_pb2.ContextRequest,
        context: grpc.aio.ServicerContext
    ) -> ai_service_pb2.ContextResponse:
        """获取工作区上下文"""
        logger.info(
            "get_context_called",
            project_id=request.project_id,
            chapter_id=request.chapter_id,
            task_type=request.task_type
        )

        try:
            # TODO: 实现上下文获取逻辑
            # 1. 识别任务类型
            # 2. 调用 Go Service 获取数据
            # 3. 调用 RAG 获取相关信息
            # 4. 构建结构化上下文

            return ai_service_pb2.ContextResponse(
                task_type=request.task_type,
                context=ai_service_pb2.WorkspaceContext(),
                token_count=0
            )

        except Exception as e:
            logger.error("get_context_failed", error=str(e), exc_info=True)
            await context.abort(
                grpc.StatusCode.INTERNAL,
                f"Failed to get context: {str(e)}"
            )

    async def ExecuteAgent(
        self,
        request: ai_service_pb2.AgentExecutionRequest,
        context: grpc.aio.ServicerContext
    ) -> ai_service_pb2.AgentExecutionResponse:
        """执行 Agent 工作流"""
        logger.info(
            "ExecuteAgent called",
            workflow_type=request.workflow_type,
            project_id=request.project_id,
            task_length=len(request.task),
        )

        try:
            # 解析上下文
            agent_context = json.loads(request.context) if request.context else {}

            # 调用Agent服务
            result = await self.agent_service.execute(
                agent_type=request.workflow_type,
                task=request.task,
                context=agent_context,
                tools=list(request.tools),
                user_id=request.user_id or None,
                project_id=request.project_id or None,
            )

            logger.info(
                "ExecuteAgent completed",
                status=result.status,
                output_length=len(result.output),
            )

            # 构建响应
            return ai_service_pb2.AgentExecutionResponse(
                execution_id=f"exec-{request.project_id}",
                status=result.status,
                result=result.output,
                errors=[],  # TODO: 从result中提取errors
                tokens_used=result.metadata.get("tokens_used", 0),
            )

        except Exception as e:
            logger.error("ExecuteAgent failed", error=str(e), exc_info=True)
            await context.abort(
                grpc.StatusCode.INTERNAL,
                f"Failed to execute agent: {str(e)}"
            )

    async def EmbedText(
        self,
        request: ai_service_pb2.EmbedRequest,
        context: grpc.aio.ServicerContext
    ) -> ai_service_pb2.EmbedResponse:
        """向量化文本"""
        logger.info(
            "embed_text_called",
            num_texts=len(request.texts),
            model=request.model
        )

        try:
            # TODO: 实现向量化逻辑
            # 1. 加载 Embedding 模型
            # 2. 批量向量化
            # 3. 返回结果

            embeddings = []
            for _ in request.texts:
                # 占位：返回空向量
                embeddings.append(
                    ai_service_pb2.Embedding(vector=[], dimension=1024)
                )

            return ai_service_pb2.EmbedResponse(embeddings=embeddings)

        except Exception as e:
            logger.error("embed_text_failed", error=str(e), exc_info=True)
            await context.abort(
                grpc.StatusCode.INTERNAL,
                f"Failed to embed text: {str(e)}"
            )

    async def HealthCheck(
        self,
        request: ai_service_pb2.HealthCheckRequest,
        context: grpc.aio.ServicerContext
    ) -> ai_service_pb2.HealthCheckResponse:
        """健康检查"""
        logger.debug("HealthCheck called")

        try:
            # 检查各个服务的健康状态
            agent_health = await self.agent_service.health_check()
            rag_health = await self.rag_service.health_check()

            checks = {
                "agent_service": "ok" if agent_health.get("healthy") else "error",
                "rag_service": "ok" if rag_health.get("healthy") else "error",
                "workflows": "ok" if agent_health.get("workflows") else "error",
            }

            # 总体状态
            status = "healthy" if all(v == "ok" for v in checks.values()) else "degraded"

            return ai_service_pb2.HealthCheckResponse(
                status=status,
                checks=checks
            )

        except Exception as e:
            logger.error("HealthCheck failed", error=str(e))
            return ai_service_pb2.HealthCheckResponse(
                status="unhealthy",
                checks={"error": str(e)}
            )


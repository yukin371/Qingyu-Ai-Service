"""
gRPC Servicer 实现
"""
import json
from typing import Any, Optional

import grpc
from google.protobuf import timestamp_pb2

from src.core.logger import get_logger
from src.services.agent_service import AgentService
from src.services.quota_service import QuotaService
from src.services.rag_service import RAGService

from . import ai_service_pb2, ai_service_pb2_grpc

logger = get_logger(__name__)


class AIServicer(ai_service_pb2_grpc.AIServiceServicer):
    """AI Service gRPC 实现"""

    def __init__(
        self,
        agent_service: Optional[AgentService] = None,
        rag_service: Optional[RAGService] = None,
        quota_service: Optional[QuotaService] = None,
    ):
        """初始化服务

        Args:
            agent_service: Agent服务实例
            rag_service: RAG服务实例
            quota_service: 配额服务实例
        """
        logger.info("Initializing AIServicer")

        # 服务依赖
        self.agent_service = agent_service or AgentService()
        self.rag_service = rag_service or RAGService()
        self.quota_service = quota_service  # 必须从外部注入

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
            now = timestamp_pb2.Timestamp()
            now.GetCurrentTime()

            return ai_service_pb2.GenerateContentResponse(
                content="TODO: Implement content generation",
                tokens_used=0,
                model=request.options.model if request.options else "gpt-4",
                generated_at=int(now.seconds)
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
            filters = request.filters if request.HasField("filters") else None
            content_types = list(filters.doc_types) if filters and filters.doc_types else None
            results = await self.rag_service.search(
                query_text=request.query,
                project_id=request.project_id,
                content_types=content_types,
                top_k=request.top_k or 5,
            )

            # 转换为gRPC响应
            rag_results = []
            for result in results:
                metadata = result.get("metadata", {})
                metadata = metadata if isinstance(metadata, dict) else {}
                metadata = {str(key): str(value) for key, value in metadata.items()}
                doc_type = (
                    result.get("doc_type")
                    or result.get("source")
                    or metadata.get("doc_type")
                    or ""
                )
                rag_results.append(
                    ai_service_pb2.RAGResult(
                        id=result.get("id") or result.get("document_id", ""),
                        content=result.get("content", "") or result.get("text", ""),
                        score=result.get("score", 0.0),
                        doc_type=doc_type,
                        metadata=metadata,
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
            task_length=len(request.parameters.get("task", "")),
        )

        try:
            parameters = dict(request.parameters) if request.parameters else {}
            task = parameters.get("task", "")
            context_raw = parameters.get("context", "")
            tools_raw = parameters.get("tools", "")
            user_id = parameters.get("user_id") or None
            project_id = request.project_id or parameters.get("project_id") or None

            # 解析上下文
            agent_context = {}
            if context_raw:
                try:
                    agent_context = json.loads(context_raw)
                except json.JSONDecodeError:
                    logger.warning(
                        "ExecuteAgent context parse failed, using empty context"
                    )

            tools = []
            if tools_raw:
                try:
                    parsed_tools = json.loads(tools_raw)
                    if isinstance(parsed_tools, list):
                        tools = [str(tool) for tool in parsed_tools]
                except json.JSONDecodeError:
                    tools = [tool.strip() for tool in tools_raw.split(",") if tool.strip()]

            # 调用Agent服务
            result = await self.agent_service.execute(
                agent_type=request.workflow_type,
                task=task,
                context=agent_context,
                tools=tools,
                user_id=user_id,
                project_id=project_id,
            )

            logger.info(
                "ExecuteAgent completed",
                status=result.status,
                output_length=len(result.output),
            )

            # 构建响应
            return ai_service_pb2.AgentExecutionResponse(
                execution_id=result.execution_id or f"exec-{project_id or 'unknown'}",
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

    async def ConsumeQuota(
        self,
        request: ai_service_pb2.QuotaConsumptionRequest,
        context: grpc.aio.ServicerContext
    ) -> ai_service_pb2.QuotaConsumptionResponse:
        """配额消费 RPC（供后端调用）

        记录用户的 AI 服务配额消费

        Args:
            request: 配额消费请求
                - user_id: 用户 ID
                - workflow_type: 工作流类型 (chat, writing, creative)
                - tokens_used: 使用的 token 数量
                - metadata: 额外的元数据
            context: gRPC 上下文

        Returns:
            QuotaConsumptionResponse: 配额消费响应
                - success: 是否成功
                - message: 响应消息
                - record_id: 记录 ID
        """
        logger.info(
            "ConsumeQuota called",
            user_id=request.user_id,
            workflow_type=request.workflow_type,
            tokens_used=request.tokens_used
        )

        try:
            # 参数验证
            if not request.user_id:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "user_id is required"
                )

            if not request.workflow_type:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "workflow_type is required"
                )

            if request.tokens_used < 0:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "tokens_used must be non-negative"
                )

            # 检查配额服务是否可用
            if not self.quota_service:
                logger.error("QuotaService not initialized")
                await context.abort(
                    grpc.StatusCode.INTERNAL,
                    "Quota service not available"
                )

            # 调用 QuotaService 记录消费
            metadata = dict(request.metadata) if request.metadata else {}
            record_id = await self.quota_service.record_consumption(
                user_id=request.user_id,
                workflow_type=request.workflow_type,
                tokens_used=request.tokens_used,
                metadata=metadata
            )

            logger.info(
                "ConsumeQuota completed",
                user_id=request.user_id,
                record_id=record_id,
                tokens_used=request.tokens_used
            )

            return ai_service_pb2.QuotaConsumptionResponse(
                success=True,
                message=f"Quota consumption recorded successfully",
                record_id=record_id
            )

        except Exception as e:
            logger.error("ConsumeQuota failed", error=str(e), exc_info=True)
            await context.abort(
                grpc.StatusCode.INTERNAL,
                f"Failed to consume quota: {str(e)}"
            )

    async def GetQuotaConsumption(
        self,
        request: ai_service_pb2.QuotaConsumptionQuery,
        context: grpc.aio.ServicerContext
    ) -> ai_service_pb2.QuotaConsumptionResponse:
        """查询配额消费

        查询用户的配额消费统计和详细记录

        Args:
            request: 配额消费查询请求
                - user_id: 用户 ID
                - time_range: 时间范围 (day, week, month, all)
                - workflow_type: 工作流类型过滤（可选）
            context: gRPC 上下文

        Returns:
            QuotaConsumptionResponse: 配额消费响应
                - success: 是否成功
                - total_tokens: 总 token 数量
                - total_records: 总记录数
                - records: 消费记录列表
        """
        logger.info(
            "GetQuotaConsumption called",
            user_id=request.user_id,
            time_range=request.time_range,
            workflow_type=request.workflow_type
        )

        try:
            # 参数验证
            if not request.user_id:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "user_id is required"
                )

            # 检查配额服务是否可用
            if not self.quota_service:
                logger.error("QuotaService not initialized")
                await context.abort(
                    grpc.StatusCode.INTERNAL,
                    "Quota service not available"
                )

            # 获取总消费统计
            time_range = request.time_range if request.time_range else "day"
            total_tokens = await self.quota_service.get_user_consumption(
                user_id=request.user_id,
                time_range=time_range
            )

            # 获取消费记录列表
            records_data = await self.quota_service.get_consumption_records(
                user_id=request.user_id,
                limit=100,
                offset=0
            )

            # 过滤工作流类型（如果指定）
            if request.workflow_type:
                records_data = [
                    r for r in records_data
                    if r.get("workflow_type") == request.workflow_type
                ]

            # 转换为 gRPC 格式
            records = []
            for record in records_data:
                records.append(
                    ai_service_pb2.QuotaRecord(
                        id=record.get("id", 0),
                        user_id=record.get("user_id", ""),
                        workflow_type=record.get("workflow_type", ""),
                        tokens_used=record.get("tokens_used", 0),
                        consumed_at=str(record.get("consumed_at", ""))
                    )
                )

            logger.info(
                "GetQuotaConsumption completed",
                user_id=request.user_id,
                total_tokens=total_tokens,
                records_count=len(records)
            )

            return ai_service_pb2.QuotaConsumptionResponse(
                success=True,
                message=f"Retrieved {len(records)} consumption records",
                total_tokens=total_tokens,
                total_records=len(records),
                records=records
            )

        except Exception as e:
            logger.error("GetQuotaConsumption failed", error=str(e), exc_info=True)
            await context.abort(
                grpc.StatusCode.INTERNAL,
                f"Failed to get quota consumption: {str(e)}"
            )

    async def SyncQuotaToBackend(
        self,
        request: ai_service_pb2.QuotaSyncRequest,
        context: grpc.aio.ServicerContext
    ) -> ai_service_pb2.QuotaSyncResponse:
        """同步配额到后端

        将用户的配额消费记录同步到后端系统

        Args:
            request: 配额同步请求
                - user_ids: 用户 ID 列表
                - force_sync: 是否强制同步
            context: gRPC 上下文

        Returns:
            QuotaSyncResponse: 配额同步响应
                - synced_count: 成功同步的用户数量
                - failed_user_ids: 失败的用户 ID 列表
                - message: 响应消息
        """
        logger.info(
            "SyncQuotaToBackend called",
            user_count=len(request.user_ids),
            force_sync=request.force_sync
        )

        try:
            # 参数验证
            if not request.user_ids:
                await context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "user_ids list is required"
                )

            # 检查配额服务是否可用
            if not self.quota_service:
                logger.error("QuotaService not initialized")
                await context.abort(
                    grpc.StatusCode.INTERNAL,
                    "Quota service not available"
                )

            # 调用 QuotaService 同步到后端
            # 注意：这里需要传入后端客户端，但当前 QuotaService.sync_to_backend
            # 需要后端客户端作为参数，我们需要考虑如何处理
            # 暂时返回未实现错误
            logger.warning("SyncQuotaToBackend: backend client integration not yet implemented")

            # TODO: 实现后端客户端集成
            # result = await self.quota_service.sync_to_backend(
            #     backend_client=self.backend_client,
            #     user_ids=list(request.user_ids)
            # )

            # 临时返回成功响应
            return ai_service_pb2.QuotaSyncResponse(
                synced_count=0,
                failed_user_ids=list(request.user_ids),
                message="Backend sync not yet implemented"
            )

        except Exception as e:
            logger.error("SyncQuotaToBackend failed", error=str(e), exc_info=True)
            await context.abort(
                grpc.StatusCode.INTERNAL,
                f"Failed to sync quota to backend: {str(e)}"
            )

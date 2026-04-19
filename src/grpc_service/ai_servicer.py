"""
gRPC AI服务实现 - Phase3专业Agent集成
"""
import asyncio
import time
import uuid
from typing import Dict, Any, Optional
from concurrent import futures
import grpc

from src.core import settings
from src.core.logger import get_logger
from src.agents.specialized import OutlineAgent, CharacterAgent, PlotAgent
from src.agents.states.pipeline_state_v2 import create_initial_pipeline_state_v2
from src.grpc_service.converters import (
    outline_dict_to_proto_data,
    characters_dict_to_proto_data,
    plot_dict_to_proto_data,
    diagnostic_report_dict_to_proto_data,
)
from src.grpc_service.proto_builders import (
    build_outline_proto,
    build_characters_proto,
    build_plot_proto,
)
from src.grpc_service import ai_service_pb2, ai_service_pb2_grpc
from src.llm.llm_factory import LLMFactory

logger = get_logger(__name__)


class AIServicer(ai_service_pb2_grpc.AIServiceServicer):
    """
    AI服务Servicer实现

    提供Phase3专业Agent的gRPC接口
    """

    def __init__(self, db_pool=None, backend_client=None):
        """初始化服务

        Args:
            db_pool: PostgreSQL 数据库连接池
            backend_client: 后端 gRPC 客户端（用于同步）
        """
        super().__init__()
        self.logger = logger
        self.db_pool = db_pool
        self.backend_client = backend_client
        self.outline_agent = None
        self.character_agent = None
        self.plot_agent = None
        self._initialize_agents()
        self._initialize_quota_service()

    def _initialize_quota_service(self):
        """初始化配额服务"""
        try:
            from src.services.quota_service import QuotaService
            if self.db_pool:
                self.quota_service = QuotaService(self.db_pool)
                self.logger.info("✅ 配额服务初始化成功")
            else:
                self.quota_service = None
                self.logger.warning("⚠️ 未提供数据库连接池，配额服务将不可用")
        except Exception as e:
            self.logger.error(f"❌ 配额服务初始化失败: {e}")
            self.quota_service = None

    def _initialize_agents(self):
        """初始化所有Agent"""
        try:
            llm_provider, llm_model = self._resolve_llm_config()

            self.outline_agent = OutlineAgent(
                llm_provider=llm_provider,
                llm_model=llm_model,
                temperature=0.7
            )
            self.character_agent = CharacterAgent(
                llm_provider=llm_provider,
                llm_model=llm_model,
                temperature=0.7
            )
            self.plot_agent = PlotAgent(
                llm_provider=llm_provider,
                llm_model=llm_model,
                temperature=0.7
            )
            self.logger.info(
                "✅ Phase3 Agents初始化成功",
                provider=llm_provider,
                model=llm_model,
            )
        except Exception as e:
            self.logger.error(f"❌ Agent初始化失败: {e}")
            raise

    def _resolve_llm_config(self, requested_model: Optional[str] = None) -> tuple[str, str]:
        """根据本地默认配置解析 LLM 提供商与模型，并兼容旧的智谱模型名。"""
        provider = settings.default_llm_provider
        model = requested_model or settings.default_llm_model

        if provider != "zhipu" and model.startswith("glm-"):
            self.logger.warning(
                "deprecated_zhipu_model_overridden",
                requested_model=model,
                provider=provider,
                fallback_model=settings.default_llm_model,
            )
            model = settings.default_llm_model

        return provider, model

    async def ExecuteCreativeWorkflow(self, request, context):
        """
        执行完整的创作工作流（Outline -> Character -> Plot）

        Args:
            request: CreativeWorkflowRequest
            context: gRPC context

        Returns:
            CreativeWorkflowResponse
        """
        execution_id = str(uuid.uuid4())
        start_time = time.time()

        try:
            self.logger.info(f"🚀 开始执行创作工作流 - ID: {execution_id}")
            self.logger.info(f"📝 任务: {request.task}")

            # 创建初始状态
            initial_state = create_initial_pipeline_state_v2(
                task=request.task,
                user_id=request.user_id,
                project_id=request.project_id,
                workspace_context=dict(request.workspace_context) if request.workspace_context else None,
            )

            execution_times = {}

            # 1. 执行OutlineAgent
            self.logger.info("📖 步骤1: 生成大纲...")
            outline_start = time.time()
            state_after_outline = await self.outline_agent.execute(initial_state)
            execution_times["outline"] = time.time() - outline_start

            outline_output = state_after_outline.get("agent_outputs", {}).get("outline_agent", {})
            self.logger.info(f"✅ 大纲生成完成 - 耗时: {execution_times['outline']:.2f}秒")

            # 2. 执行CharacterAgent
            self.logger.info("👤 步骤2: 生成角色...")
            character_start = time.time()
            state_after_character = await self.character_agent.execute(state_after_outline)
            execution_times["character"] = time.time() - character_start

            character_output = state_after_character.get("agent_outputs", {}).get("character_agent", {})
            self.logger.info(f"✅ 角色生成完成 - 耗时: {execution_times['character']:.2f}秒")

            # 3. 执行PlotAgent
            self.logger.info("📊 步骤3: 生成情节...")
            plot_start = time.time()
            state_after_plot = await self.plot_agent.execute(state_after_character)
            execution_times["plot"] = time.time() - plot_start

            plot_output = state_after_plot.get("agent_outputs", {}).get("plot_agent", {})
            self.logger.info(f"✅ 情节生成完成 - 耗时: {execution_times['plot']:.2f}秒")

            # 构建响应
            total_time = time.time() - start_time

            # 转换为protobuf格式
            outline_proto_dict = outline_dict_to_proto_data(outline_output)
            characters_proto_dict = characters_dict_to_proto_data(character_output)
            plot_proto_dict = plot_dict_to_proto_data(plot_output)

            # 构建protobuf消息对象
            outline_proto = build_outline_proto(outline_proto_dict)
            characters_proto = build_characters_proto(characters_proto_dict)
            plot_proto = build_plot_proto(plot_proto_dict)

            # 简化的审核结果（暂时设为通过）
            review_passed = True

            # 估算 token 使用量（简化计算）
            tokens_used = self._estimate_tokens(state_after_plot)

            # 记录配额消费
            await self._record_quota_if_available(
                user_id=request.user_id,
                workflow_type="creative_workflow",
                tokens_used=tokens_used,
                metadata={
                    "task": request.task,
                    "project_id": request.project_id,
                    "execution_id": execution_id,
                    "agent_types": ["outline", "character", "plot"]
                }
            )

            # 构建protobuf响应对象
            response = ai_service_pb2.CreativeWorkflowResponse(
                execution_id=execution_id,
                review_passed=review_passed,
                reflection_count=0,
                outline=outline_proto,
                characters=characters_proto,
                plot=plot_proto,
                reasoning=state_after_plot.get("reasoning", []),
                execution_times=execution_times,
                tokens_used=tokens_used,
            )

            self.logger.info(f"✨ 工作流执行成功 - 总耗时: {total_time:.2f}秒, Tokens: {tokens_used}")
            return response

        except Exception as e:
            self.logger.error(f"❌ 工作流执行失败: {e}")
            context.abort(
                grpc.StatusCode.INTERNAL,
                f"工作流执行失败: {str(e)}"
            )

    async def GenerateOutline(self, request, context):
        """
        生成大纲

        Args:
            request: OutlineRequest
            context: gRPC context

        Returns:
            OutlineResponse
        """
        start_time = time.time()

        try:
            self.logger.info(f"📖 生成大纲 - 任务: {request.task}")

            # 创建初始状态
            initial_state = create_initial_pipeline_state_v2(
                task=request.task,
                user_id=request.user_id,
                project_id=request.project_id,
                workspace_context=dict(request.workspace_context) if request.workspace_context else None,
            )

            # 如果有修正提示，添加到状态
            if request.correction_prompt:
                initial_state["correction_prompts"] = {
                    "OutlineAgent": request.correction_prompt
                }

            # 执行OutlineAgent
            state = await self.outline_agent.execute(initial_state)

            outline_output = state.get("agent_outputs", {}).get("outline_agent", {})
            execution_time = time.time() - start_time

            # 🔍 调试日志：检查Agent输出
            self.logger.debug(f"📊 State keys: {list(state.keys())}")
            self.logger.debug(f"📊 Agent outputs keys: {list(state.get('agent_outputs', {}).keys())}")
            self.logger.debug(f"📊 OutlineAgent output keys: {list(outline_output.keys())}")
            if outline_output:
                self.logger.info(f"✅ 大纲数据: title='{outline_output.get('title', 'N/A')}', chapters={len(outline_output.get('chapters', []))}")
            else:
                self.logger.warning("⚠️ OutlineAgent返回空输出!")

            # 转换为protobuf格式
            outline_proto_dict = outline_dict_to_proto_data(outline_output)

            # 构建protobuf响应对象
            response = ai_service_pb2.OutlineResponse(
                outline=build_outline_proto(outline_proto_dict),
                execution_time=execution_time,
            )

            self.logger.info(f"✅ 大纲生成完成 - 耗时: {execution_time:.2f}秒")
            return response

        except Exception as e:
            self.logger.error(f"❌ 大纲生成失败: {e}")
            context.abort(
                grpc.StatusCode.INTERNAL,
                f"大纲生成失败: {str(e)}"
            )

    async def GenerateCharacters(self, request, context):
        """
        生成角色

        Args:
            request: CharactersRequest
            context: gRPC context

        Returns:
            CharactersResponse
        """
        start_time = time.time()

        try:
            self.logger.info(f"👤 生成角色 - 任务: {request.task}")

            # 创建初始状态
            initial_state = create_initial_pipeline_state_v2(
                task=request.task,
                user_id=request.user_id,
                project_id=request.project_id,
                workspace_context=dict(request.workspace_context) if request.workspace_context else None,
            )

            # 添加大纲输出到状态
            if request.HasField("outline"):
                outline_dict = self._proto_outline_to_dict(request.outline)
                initial_state["agent_outputs"] = {
                    "outline_agent": outline_dict
                }
                # 提取outline_nodes
                initial_state["outline_nodes"] = outline_dict.get("chapters", [])

            # 如果有修正提示，添加到状态
            if request.correction_prompt:
                initial_state["correction_prompts"] = {
                    "CharacterAgent": request.correction_prompt
                }

            # 执行CharacterAgent
            state = await self.character_agent.execute(initial_state)

            character_output = state.get("agent_outputs", {}).get("character_agent", {})
            execution_time = time.time() - start_time

            # 🔍 调试日志：检查Agent输出
            self.logger.debug(f"📊 CharacterAgent output keys: {list(character_output.keys())}")
            if character_output:
                self.logger.info(f"✅ 角色数据: characters={len(character_output.get('characters', []))}")
            else:
                self.logger.warning("⚠️ CharacterAgent返回空输出!")

            # 转换为protobuf格式
            characters_proto_dict = characters_dict_to_proto_data(character_output)

            # 构建protobuf响应对象
            response = ai_service_pb2.CharactersResponse(
                characters=build_characters_proto(characters_proto_dict),
                execution_time=execution_time,
            )

            self.logger.info(f"✅ 角色生成完成 - 耗时: {execution_time:.2f}秒")
            return response

        except Exception as e:
            self.logger.error(f"❌ 角色生成失败: {e}")
            context.abort(
                grpc.StatusCode.INTERNAL,
                f"角色生成失败: {str(e)}"
            )

    async def GeneratePlot(self, request, context):
        """
        生成情节

        Args:
            request: PlotRequest
            context: gRPC context

        Returns:
            PlotResponse
        """
        start_time = time.time()

        try:
            self.logger.info(f"📊 生成情节 - 任务: {request.task}")

            # 创建初始状态
            initial_state = create_initial_pipeline_state_v2(
                task=request.task,
                user_id=request.user_id,
                project_id=request.project_id,
                workspace_context=dict(request.workspace_context) if request.workspace_context else None,
            )

            agent_outputs = {}

            # 添加大纲输出到状态
            if request.HasField("outline"):
                outline_dict = self._proto_outline_to_dict(request.outline)
                agent_outputs["outline_agent"] = outline_dict
                initial_state["outline_nodes"] = outline_dict.get("chapters", [])

            # 添加角色输出到状态
            if request.HasField("characters"):
                characters_dict = self._proto_characters_to_dict(request.characters)
                agent_outputs["character_agent"] = characters_dict

            initial_state["agent_outputs"] = agent_outputs

            # 如果有修正提示，添加到状态
            if request.correction_prompt:
                initial_state["correction_prompts"] = {
                    "PlotAgent": request.correction_prompt
                }

            # 执行PlotAgent
            state = await self.plot_agent.execute(initial_state)

            plot_output = state.get("agent_outputs", {}).get("plot_agent", {})
            execution_time = time.time() - start_time

            # 🔍 调试日志：检查Agent输出
            self.logger.debug(f"📊 PlotAgent output keys: {list(plot_output.keys())}")
            if plot_output:
                self.logger.info(f"✅ 情节数据: events={len(plot_output.get('timeline_events', []))}, threads={len(plot_output.get('plot_threads', []))}")
            else:
                self.logger.warning("⚠️ PlotAgent返回空输出!")

            # 转换为protobuf格式
            plot_proto_dict = plot_dict_to_proto_data(plot_output)

            # 构建protobuf响应对象
            response = ai_service_pb2.PlotResponse(
                plot=build_plot_proto(plot_proto_dict),
                execution_time=execution_time,
            )

            self.logger.info(f"✅ 情节生成完成 - 耗时: {execution_time:.2f}秒")
            return response

        except Exception as e:
            self.logger.error(f"❌ 情节生成失败: {e}")
            context.abort(
                grpc.StatusCode.INTERNAL,
                f"情节生成失败: {str(e)}"
            )

    async def StoryWrite(self, request, context):
        """
        故事上下文写作
        
        Args:
            request: StoryContextRequest
            context: gRPC context
            
        Returns:
            StoryContextResponse
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"✍️ 故事写作 - 项目: {request.project_id}, 文档: {request.document_id}, 模式: {request.mode}")
            
            # 验证必需参数
            if not request.assembled_prompt:
                context.abort(
                    grpc.StatusCode.INVALID_ARGUMENT,
                    "assembled_prompt 不能为空"
                )
            
            requested_model = request.options.model if request.options.model else None
            provider, model = self._resolve_llm_config(requested_model=requested_model)
            temperature = request.options.temperature if request.options.temperature > 0 else 0.7
            max_tokens = request.options.max_tokens if request.options.max_tokens > 0 else 2000

            llm = LLMFactory.create_llm(
                provider=provider,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            self.logger.info(
                "🤖 调用 LLM",
                provider=provider,
                model=model,
                temperature=temperature,
            )
            response_msg = await llm.ainvoke(request.assembled_prompt)
            generated_content = response_msg.content

            usage_metadata = getattr(response_msg, "usage_metadata", {}) or {}
            prompt_tokens = usage_metadata.get("input_tokens", 0) or len(request.assembled_prompt) // 2
            completion_tokens = usage_metadata.get("output_tokens", 0) or len(generated_content) // 2
            total_tokens = usage_metadata.get("total_tokens", 0) or (prompt_tokens + completion_tokens)

            execution_time = time.time() - start_time
            generated_at = int(time.time())

            # 构建上下文统计（模拟值，实际应该从后端传递）
            context_stats = ai_service_pb2.StoryContextStats(
                stage_tokens=prompt_tokens // 4,
                outline_tokens=prompt_tokens // 4,
                rag_tokens=prompt_tokens // 4,
                total_tokens=prompt_tokens
            )

            self.logger.info(f"✅ 故事写作完成 - 耗时: {execution_time:.2f}秒, Tokens: {total_tokens}")

            response = ai_service_pb2.StoryContextResponse(
                content=generated_content,
                tokens_used=total_tokens,
                model=model,
                generated_at=generated_at,
                context_stats=context_stats
            )

            return response
                
        except Exception as e:
            self.logger.error(f"❌ 故事写作失败: {e}")
            context.abort(
                grpc.StatusCode.INTERNAL,
                f"故事写作失败: {str(e)}"
            )

    def _proto_outline_to_dict(self, outline_proto) -> Dict[str, Any]:
        """将protobuf Outline消息转换为Python字典"""
        chapters = []
        for chapter in outline_proto.chapters:
            chapters.append({
                "chapter_id": chapter.chapter_id,
                "title": chapter.title,
                "summary": chapter.summary,
                "key_events": list(chapter.key_events),
                "characters_involved": list(chapter.characters_involved),
                "conflict_type": chapter.conflict_type,
                "emotional_tone": chapter.emotional_tone,
                "estimated_word_count": chapter.estimated_word_count,
                "chapter_goal": chapter.chapter_goal,
                "cliffhanger": chapter.cliffhanger,
            })

        story_arc = {
            "setup": list(outline_proto.story_arc.setup),
            "rising_action": list(outline_proto.story_arc.rising_action),
            "climax": list(outline_proto.story_arc.climax),
            "falling_action": list(outline_proto.story_arc.falling_action),
            "resolution": list(outline_proto.story_arc.resolution),
        }

        return {
            "title": outline_proto.title,
            "genre": outline_proto.genre,
            "core_theme": outline_proto.core_theme,
            "target_audience": outline_proto.target_audience,
            "estimated_total_words": outline_proto.estimated_total_words,
            "chapters": chapters,
            "story_arc": story_arc,
        }

    def _proto_characters_to_dict(self, characters_proto) -> Dict[str, Any]:
        """将protobuf Characters消息转换为Python字典"""
        characters = []
        for char in characters_proto.characters:
            relationships = []
            for rel in char.relationships:
                relationships.append({
                    "character": rel.character,
                    "relation_type": rel.relation_type,
                    "description": rel.description,
                    "dynamics": rel.dynamics,
                })

            characters.append({
                "character_id": char.character_id,
                "name": char.name,
                "role_type": char.role_type,
                "importance": char.importance,
                "age": char.age,
                "gender": char.gender,
                "appearance": char.appearance,
                "personality": {
                    "traits": list(char.personality.traits),
                    "strengths": list(char.personality.strengths),
                    "weaknesses": list(char.personality.weaknesses),
                    "core_values": char.personality.core_values,
                    "fears": char.personality.fears,
                },
                "background": {
                    "summary": char.background.summary,
                    "family": char.background.family,
                    "education": char.background.education,
                    "key_experiences": list(char.background.key_experiences),
                },
                "motivation": char.motivation,
                "relationships": relationships,
                "development_arc": {
                    "starting_point": char.development_arc.starting_point,
                    "turning_points": list(char.development_arc.turning_points),
                    "ending_point": char.development_arc.ending_point,
                    "growth_theme": char.development_arc.growth_theme,
                },
                "role_in_story": char.role_in_story,
                "first_appearance": char.first_appearance,
                "chapters_involved": list(char.chapters_involved),
            })

        network = {
            "alliances": [list(a.members) for a in characters_proto.relationship_network.alliances],
            "conflicts": [list(c.parties) for c in characters_proto.relationship_network.conflicts],
            "mentorships": [
                {"mentor": m.mentor, "student": m.student}
                for m in characters_proto.relationship_network.mentorships
            ],
        }

        return {
            "characters": characters,
            "relationship_network": network,
        }

    async def HealthCheck(self, request, context):
        """
        健康检查

        Args:
            request: HealthCheckRequest
            context: gRPC context

        Returns:
            HealthCheckResponse
        """
        try:
            checks = {
                "outline_agent": "healthy" if self.outline_agent else "unhealthy",
                "character_agent": "healthy" if self.character_agent else "unhealthy",
                "plot_agent": "healthy" if self.plot_agent else "unhealthy",
            }

            all_healthy = all(status == "healthy" for status in checks.values())

            return ai_service_pb2.HealthCheckResponse(
                status="healthy" if all_healthy else "degraded",
                checks=checks,
            )
        except Exception as e:
            self.logger.error(f"❌ 健康检查失败: {e}")
            return ai_service_pb2.HealthCheckResponse(
                status="unhealthy",
                checks={"error": str(e)},
            )

    # ============ 配额管理 RPC (v1.1.0) ============

    async def ConsumeQuota(self, request, context):
        """配额消费 RPC（供后端调用）

        Args:
            request: QuotaConsumptionRequest
            context: gRPC context

        Returns:
            QuotaConsumptionResponse
        """
        try:
            if not self.quota_service:
                context.abort(
                    grpc.StatusCode.UNAVAILABLE,
                    "配额服务未初始化"
                )

            record_id = await self.quota_service.record_consumption(
                user_id=request.user_id,
                workflow_type=request.workflow_type,
                tokens_used=request.tokens_used,
                metadata=dict(request.metadata)
            )

            return ai_service_pb2.QuotaConsumptionResponse(
                success=True,
                message="Quota recorded successfully",
                quota_remaining=0,  # 由后端计算
                record_id=record_id
            )

        except Exception as e:
            self.logger.error(f"❌ ConsumeQuota failed: {e}")
            return ai_service_pb2.QuotaConsumptionResponse(
                success=False,
                message=str(e)
            )

    async def GetQuotaConsumption(self, request, context):
        """查询配额消费

        Args:
            request: QuotaConsumptionQuery
            context: gRPC context

        Returns:
            QuotaConsumptionResponse
        """
        try:
            if not self.quota_service:
                context.abort(
                    grpc.StatusCode.UNAVAILABLE,
                    "配额服务未初始化"
                )

            consumption = await self.quota_service.get_user_consumption(
                user_id=request.user_id,
                time_range=request.time_range or "day"
            )

            # 获取详细记录
            records = await self.quota_service.get_consumption_records(
                user_id=request.user_id,
                limit=100
            )

            # 转换记录为 protobuf 格式
            proto_records = []
            for record in records:
                proto_records.append(ai_service_pb2.QuotaRecord(
                    id=record['id'],
                    user_id=record['user_id'],
                    workflow_type=record['workflow_type'],
                    tokens_used=record['tokens_used'],
                    consumed_at=record['consumed_at'].isoformat()
                ))

            return ai_service_pb2.QuotaConsumptionResponse(
                success=True,
                total_tokens=consumption,
                total_records=len(proto_records),
                records=proto_records
            )

        except Exception as e:
            self.logger.error(f"❌ GetQuotaConsumption failed: {e}")
            return ai_service_pb2.QuotaConsumptionResponse(
                success=False,
                error_message=str(e)
            )

    async def SyncQuotaToBackend(self, request, context):
        """同步配额到后端

        Args:
            request: QuotaSyncRequest
            context: gRPC context

        Returns:
            QuotaSyncResponse
        """
        if not self.backend_client:
            return ai_service_pb2.QuotaSyncResponse(
                synced_count=0,
                failed_user_ids=list(request.user_ids),
                message="Backend client not configured"
            )

        if not self.quota_service:
            return ai_service_pb2.QuotaSyncResponse(
                synced_count=0,
                failed_user_ids=list(request.user_ids),
                message="Quota service not configured"
            )

        try:
            result = await self.quota_service.sync_to_backend(
                self.backend_client,
                list(request.user_ids)
            )

            return ai_service_pb2.QuotaSyncResponse(
                synced_count=result["synced"],
                failed_user_ids=result["failed"],
                message=f"Synced {result['synced']} users"
            )

        except Exception as e:
            self.logger.error(f"❌ SyncQuotaToBackend failed: {e}")
            return ai_service_pb2.QuotaSyncResponse(
                synced_count=0,
                failed_user_ids=list(request.user_ids),
                message=str(e)
            )

    # ============ 配额辅助方法 ============

    async def _record_quota_if_available(
        self,
        user_id: str,
        workflow_type: str,
        tokens_used: int,
        metadata: Dict[str, Any]
    ):
        """如果配额服务可用，记录配额消费

        Args:
            user_id: 用户 ID
            workflow_type: 工作流类型
            tokens_used: 使用的 token 数量
            metadata: 元数据
        """
        if not self.quota_service:
            return

        try:
            await self.quota_service.record_consumption(
                user_id=user_id,
                workflow_type=workflow_type,
                tokens_used=tokens_used,
                metadata=metadata
            )
            self.logger.info(f"✅ 配额已记录: user={user_id}, tokens={tokens_used}")
        except Exception as e:
            # 配额记录失败不应影响主流程
            self.logger.warning(f"⚠️ 配额记录失败: {e}")

    def _estimate_tokens(self, state: Dict[str, Any]) -> int:
        """估算使用的 token 数量

        Args:
            state: Agent 执行状态

        Returns:
            int: 估算的 token 数量
        """
        # 尝试从 state 中提取 token 使用量
        if "token_usage" in state:
            return state["token_usage"].get("total_tokens", 0)

        # 估算：基于输出内容长度
        # 假设平均 1 token ≈ 4 字符（中文约 1.5 字符/token）
        total_chars = 0

        # 计算各 Agent 输出的字符数
        agent_outputs = state.get("agent_outputs", {})
        for agent_name, output in agent_outputs.items():
            if isinstance(output, dict):
                # 估算输出文本长度
                total_chars += len(str(output.get("title", "")))
                total_chars += len(str(output.get("content", "")))
                total_chars += len(str(output.get("description", "")))

                # 对于列表（如 chapters, characters）
                for key in ["chapters", "characters", "timeline_events", "plot_threads"]:
                    if key in output and isinstance(output[key], list):
                        total_chars += len(str(output[key]))

        # 简单估算：字符数 / 3 ≈ token 数
        estimated_tokens = max(100, total_chars // 3)
        return estimated_tokens


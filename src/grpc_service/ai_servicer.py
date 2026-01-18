"""
gRPC AI服务实现 - Phase3专业Agent集成
"""
import asyncio
import time
import uuid
from typing import Dict, Any, Optional
from concurrent import futures
import grpc

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

logger = get_logger(__name__)


class AIServicer(ai_service_pb2_grpc.AIServiceServicer):
    """
    AI服务Servicer实现

    提供Phase3专业Agent的gRPC接口
    """

    def __init__(self):
        """初始化服务"""
        super().__init__()
        self.logger = logger
        self.outline_agent = None
        self.character_agent = None
        self.plot_agent = None
        self._initialize_agents()

    def _initialize_agents(self):
        """初始化所有Agent"""
        try:
            # 使用Gemini 2.0 Flash
            self.outline_agent = OutlineAgent(
                llm_provider="gemini",
                llm_model="gemini-2.0-flash-exp",
                temperature=0.7
            )
            self.character_agent = CharacterAgent(
                llm_provider="gemini",
                llm_model="gemini-2.0-flash-exp",
                temperature=0.7
            )
            self.plot_agent = PlotAgent(
                llm_provider="gemini",
                llm_model="gemini-2.0-flash-exp",
                temperature=0.7
            )
            self.logger.info("✅ Phase3 Agents初始化成功")
        except Exception as e:
            self.logger.error(f"❌ Agent初始化失败: {e}")
            raise

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
                tokens_used=0,  # TODO: 从state中提取token统计
            )

            self.logger.info(f"✨ 工作流执行成功 - 总耗时: {total_time:.2f}秒")
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


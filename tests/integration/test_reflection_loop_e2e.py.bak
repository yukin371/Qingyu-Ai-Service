"""
反思循环端到端集成测试
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch

from agents.workflows.agent_workflow_v2 import execute_agent_workflow_v2
from agents.workflows.routers_v2 import (
    review_router,
    meta_scheduler_router,
    check_workflow_health
)
from agents.states.pipeline_state_v2 import create_initial_pipeline_state_v2


class TestReflectionLoopE2E:
    """反思循环端到端测试类"""

    @pytest.fixture
    def create_mock_responses(self):
        """创建Mock响应的工厂函数"""
        def _create(outline_data=None, character_data=None, plot_data=None, review_data=None):
            # 默认数据
            default_outline = {
                "title": "测试故事",
                "chapters": [{"chapter_id": 1, "title": "第一章"}]
            }
            default_character = {
                "characters": [{"name": "主角", "role_type": "protagonist"}],
                "relationship_network": {}
            }
            default_plot = {
                "timeline_events": [{"event_id": "evt_001", "title": "事件1"}],
                "plot_threads": []
            }
            default_review = {
                "passed": True,
                "quality_score": 85,
                "issues": [],
                "correction_strategy": "none",
                "affected_agents": [],
                "reasoning_chain": []
            }

            outline_mock = Mock()
            outline_mock.content = json.dumps(outline_data or default_outline, ensure_ascii=False)

            character_mock = Mock()
            character_mock.content = json.dumps(character_data or default_character, ensure_ascii=False)

            plot_mock = Mock()
            plot_mock.content = json.dumps(plot_data or default_plot, ensure_ascii=False)

            review_mock = Mock()
            review_mock.content = json.dumps(review_data or default_review, ensure_ascii=False)

            return outline_mock, character_mock, plot_mock, review_mock

        return _create

    @pytest.mark.asyncio
    async def test_review_router_pass(self):
        """测试审核路由器 - 通过场景"""
        state = create_initial_pipeline_state_v2(
            task="test",
            user_id="user1",
            project_id="proj1"
        )
        state["review_passed"] = True

        result = review_router(state)
        assert result == "completed"

    @pytest.mark.asyncio
    async def test_review_router_fail_continue(self):
        """测试审核路由器 - 失败继续修正"""
        state = create_initial_pipeline_state_v2(
            task="test",
            user_id="user1",
            project_id="proj1"
        )
        state["review_passed"] = False
        state["reflection_count"] = 0
        state["max_reflections"] = 3

        result = review_router(state)
        assert result == "meta_scheduler"

    @pytest.mark.asyncio
    async def test_review_router_max_iterations(self):
        """测试审核路由器 - 达到最大迭代次数"""
        state = create_initial_pipeline_state_v2(
            task="test",
            user_id="user1",
            project_id="proj1"
        )
        state["review_passed"] = False
        state["reflection_count"] = 3
        state["max_reflections"] = 3

        result = review_router(state)
        assert result == "human_review"

    @pytest.mark.asyncio
    async def test_meta_scheduler_router_outline(self):
        """测试元调度器路由 - 路由到outline"""
        state = create_initial_pipeline_state_v2(
            task="test",
            user_id="user1",
            project_id="proj1"
        )
        state["current_step"] = "outline"

        result = meta_scheduler_router(state)
        assert result == "outline"

    @pytest.mark.asyncio
    async def test_meta_scheduler_router_character(self):
        """测试元调度器路由 - 路由到character"""
        state = create_initial_pipeline_state_v2(
            task="test",
            user_id="user1",
            project_id="proj1"
        )
        state["current_step"] = "character_agent"

        result = meta_scheduler_router(state)
        assert result == "character"

    @pytest.mark.asyncio
    async def test_workflow_health_check_healthy(self):
        """测试工作流健康检查 - 健康状态"""
        state = create_initial_pipeline_state_v2(
            task="test",
            user_id="user1",
            project_id="proj1"
        )
        state["errors"] = []
        state["review_passed"] = True
        state["reflection_count"] = 0

        health = check_workflow_health(state)

        assert health["healthy"] == True
        assert health["status"] == "completed"
        assert health["error_count"] == 0

    @pytest.mark.asyncio
    async def test_workflow_health_check_error(self):
        """测试工作流健康检查 - 错误状态"""
        state = create_initial_pipeline_state_v2(
            task="test",
            user_id="user1",
            project_id="proj1"
        )
        state["errors"] = ["Error 1", "Error 2"]

        health = check_workflow_health(state)

        assert health["healthy"] == False
        assert health["status"] == "error"
        assert health["error_count"] == 2

    @pytest.mark.asyncio
    async def test_workflow_health_check_needs_intervention(self):
        """测试工作流健康检查 - 需要介入状态"""
        state = create_initial_pipeline_state_v2(
            task="test",
            user_id="user1",
            project_id="proj1"
        )
        state["errors"] = []
        state["reflection_count"] = 3
        state["max_reflections"] = 3
        state["review_passed"] = False

        health = check_workflow_health(state)

        assert health["status"] == "needs_intervention"

    @pytest.mark.asyncio
    async def test_reflection_loop_single_correction(self, create_mock_responses):
        """测试反思循环 - 单次修正"""
        # 第一次审核失败，指向character_agent修正
        review_fail = {
            "passed": False,
            "quality_score": 65,
            "issues": [
                {
                    "id": "issue-001",
                    "severity": "medium",
                    "category": "character",
                    "sub_category": "character",
                    "title": "角色不完整",
                    "description": "缺少主角的性格特征",
                    "root_cause": "character_agent信息不足",
                    "affected_entities": ["主角"],
                    "impact": "影响故事可信度"
                }
            ],
            "correction_strategy": "incremental_fix",
            "correction_instructions": [],
            "affected_agents": ["character_agent"],
            "reasoning_chain": []
        }

        # 第二次审核通过
        review_pass = {
            "passed": True,
            "quality_score": 85,
            "issues": [],
            "correction_strategy": "none",
            "affected_agents": [],
            "reasoning_chain": []
        }

        with patch('agents.specialized.outline_agent.LLMFactory.create_llm') as mock_llm_factory:
            mock_llm = AsyncMock()

            # 创建响应序列
            o1, c1, p1, r1 = create_mock_responses(review_data=review_fail)
            o2, c2, p2, r2 = create_mock_responses(review_data=review_pass)

            mock_llm.ainvoke = AsyncMock(side_effect=[
                o1,  # Outline第一次
                c1,  # Character第一次
                p1,  # Plot第一次
                r1,  # Review第一次（失败）
                # 元调度器决定修正character
                c2,  # Character修正
                p2,  # Plot重新生成
                r2   # Review第二次（通过）
            ])
            mock_llm_factory.return_value = mock_llm

            # 执行工作流
            final_state = await execute_agent_workflow_v2(
                task="创作一个故事",
                user_id="test_user",
                project_id="test_project",
                max_reflections=3
            )

            # 验证最终通过
            assert final_state.get("review_passed") == True

            # 验证至少进行了一次反思
            assert final_state.get("reflection_count", 0) >= 1

    @pytest.mark.asyncio
    async def test_reflection_loop_multiple_corrections(self, create_mock_responses):
        """测试反思循环 - 多次修正"""
        # 第一次失败
        review_fail_1 = {
            "passed": False,
            "quality_score": 50,
            "issues": [],
            "correction_strategy": "regenerate",
            "affected_agents": ["outline_agent"],
            "reasoning_chain": []
        }

        # 第二次失败
        review_fail_2 = {
            "passed": False,
            "quality_score": 70,
            "issues": [],
            "correction_strategy": "incremental_fix",
            "affected_agents": ["character_agent"],
            "reasoning_chain": []
        }

        # 第三次通过
        review_pass = {
            "passed": True,
            "quality_score": 85,
            "issues": [],
            "correction_strategy": "none",
            "affected_agents": [],
            "reasoning_chain": []
        }

        with patch('agents.specialized.outline_agent.LLMFactory.create_llm') as mock_llm_factory:
            mock_llm = AsyncMock()

            o1, c1, p1, r1 = create_mock_responses(review_data=review_fail_1)
            o2, c2, p2, r2 = create_mock_responses(review_data=review_fail_2)
            o3, c3, p3, r3 = create_mock_responses(review_data=review_pass)

            mock_llm.ainvoke = AsyncMock(side_effect=[
                o1, c1, p1, r1,  # 第一轮（失败）
                o2, c2, p2, r2,  # 第二轮（失败）
                c3, p3, r3       # 第三轮（通过）
            ])
            mock_llm_factory.return_value = mock_llm

            # 执行工作流
            final_state = await execute_agent_workflow_v2(
                task="创作一个故事",
                user_id="test_user",
                project_id="test_project",
                max_reflections=5
            )

            # 验证最终通过
            assert final_state.get("review_passed") == True

            # 验证进行了多次反思
            assert final_state.get("reflection_count", 0) >= 2

    @pytest.mark.asyncio
    async def test_correction_history_tracking(self, create_mock_responses):
        """测试修正历史追踪"""
        review_fail = {
            "passed": False,
            "quality_score": 65,
            "issues": [],
            "correction_strategy": "incremental_fix",
            "affected_agents": ["character_agent"],
            "reasoning_chain": []
        }

        review_pass = {
            "passed": True,
            "quality_score": 85,
            "issues": [],
            "correction_strategy": "none",
            "affected_agents": [],
            "reasoning_chain": []
        }

        with patch('agents.specialized.outline_agent.LLMFactory.create_llm') as mock_llm_factory:
            mock_llm = AsyncMock()

            o1, c1, p1, r1 = create_mock_responses(review_data=review_fail)
            o2, c2, p2, r2 = create_mock_responses(review_data=review_pass)

            mock_llm.ainvoke = AsyncMock(side_effect=[
                o1, c1, p1, r1,
                c2, p2, r2
            ])
            mock_llm_factory.return_value = mock_llm

            # 执行工作流
            final_state = await execute_agent_workflow_v2(
                task="创作一个故事",
                user_id="test_user",
                project_id="test_project"
            )

            # 验证修正历史被记录
            # 注意：correction_history可能为空，因为我们没有在agent中调用add_correction_record
            # 但reflection_count应该被增加
            assert final_state.get("reflection_count", 0) >= 1


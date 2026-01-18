"""
Agent Workflow端到端集成测试
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch

from agents.workflows.agent_workflow_v2 import (
    create_agent_workflow_v2,
    execute_agent_workflow_v2
)
from agents.states.pipeline_state_v2 import create_initial_pipeline_state_v2


class TestAgentWorkflowE2E:
    """Agent Workflow端到端测试类"""

    @pytest.fixture
    def mock_outline_response(self):
        """Mock大纲Agent响应"""
        outline_json = {
            "title": "测试故事",
            "genre": "奇幻",
            "chapters": [
                {
                    "chapter_id": 1,
                    "title": "开始",
                    "summary": "故事开始",
                    "characters_involved": ["主角"]
                }
            ]
        }
        mock_response = Mock()
        mock_response.content = json.dumps(outline_json, ensure_ascii=False)
        return mock_response

    @pytest.fixture
    def mock_character_response(self):
        """Mock角色Agent响应"""
        characters_json = {
            "characters": [
                {
                    "character_id": "char_001",
                    "name": "主角",
                    "role_type": "protagonist",
                    "personality": {"traits": ["勇敢"]}
                }
            ],
            "relationship_network": {"conflicts": []}
        }
        mock_response = Mock()
        mock_response.content = json.dumps(characters_json, ensure_ascii=False)
        return mock_response

    @pytest.fixture
    def mock_plot_response(self):
        """Mock情节Agent响应"""
        plot_json = {
            "timeline_events": [
                {
                    "event_id": "evt_001",
                    "title": "事件1",
                    "participants": ["主角"]
                }
            ],
            "plot_threads": [
                {"thread_id": "main", "title": "主线", "type": "main"}
            ]
        }
        mock_response = Mock()
        mock_response.content = json.dumps(plot_json, ensure_ascii=False)
        return mock_response

    @pytest.fixture
    def mock_review_pass_response(self):
        """Mock审核通过响应"""
        review_json = {
            "passed": True,
            "quality_score": 85,
            "issues": [],
            "correction_strategy": "none",
            "affected_agents": [],
            "reasoning_chain": ["内容质量良好"],
            "suggestions_for_improvement": []
        }
        mock_response = Mock()
        mock_response.content = json.dumps(review_json, ensure_ascii=False)
        return mock_response

    @pytest.fixture
    def mock_review_fail_response(self):
        """Mock审核失败响应"""
        review_json = {
            "passed": False,
            "quality_score": 60,
            "issues": [
                {
                    "id": "issue-001",
                    "severity": "medium",
                    "category": "completeness",
                    "sub_category": "character",
                    "title": "角色描述不足",
                    "description": "主角性格不够立体",
                    "root_cause": "角色Agent生成时信息不足",
                    "affected_entities": ["主角"],
                    "impact": "影响角色可信度"
                }
            ],
            "correction_strategy": "incremental_fix",
            "correction_instructions": [
                {
                    "issue_id": "issue-001",
                    "target_agent": "character_agent",
                    "action": "update",
                    "specific_instruction": "为主角增加更多性格特征",
                    "parameters": {},
                    "priority": 7
                }
            ],
            "affected_agents": ["character_agent"],
            "reasoning_chain": ["发现角色描述不足"],
            "suggestions_for_improvement": []
        }
        mock_response = Mock()
        mock_response.content = json.dumps(review_json, ensure_ascii=False)
        return mock_response

    @pytest.mark.asyncio
    async def test_create_workflow(self):
        """测试创建工作流"""
        workflow = create_agent_workflow_v2(
            max_reflections=3,
            enable_human_review=True
        )

        assert workflow is not None
        # 验证工作流可以获取图结构
        graph = workflow.get_graph()
        assert graph is not None

    @pytest.mark.asyncio
    async def test_basic_workflow_execution_success(
        self,
        mock_outline_response,
        mock_character_response,
        mock_plot_response,
        mock_review_pass_response
    ):
        """测试基础工作流执行（审核通过）"""
        # Mock所有LLM调用
        with patch('agents.specialized.outline_agent.LLMFactory.create_llm') as mock_llm_factory:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(side_effect=[
                mock_outline_response,  # OutlineAgent
                mock_character_response,  # CharacterAgent
                mock_plot_response,  # PlotAgent
                mock_review_pass_response  # ReviewAgent
            ])
            mock_llm_factory.return_value = mock_llm

            # 执行工作流
            final_state = await execute_agent_workflow_v2(
                task="创作一个测试故事",
                user_id="test_user",
                project_id="test_project",
                max_reflections=3,
                enable_human_review=False
            )

            # 验证
            assert final_state is not None
            assert final_state.get("review_passed") == True
            assert "outline_agent" in final_state.get("agent_outputs", {})
            assert "character_agent" in final_state.get("agent_outputs", {})
            assert "plot_agent" in final_state.get("agent_outputs", {})

            # 验证迭代次数为0（一次通过）
            assert final_state.get("reflection_count", 0) == 0

    @pytest.mark.asyncio
    async def test_workflow_with_one_correction(
        self,
        mock_outline_response,
        mock_character_response,
        mock_plot_response,
        mock_review_fail_response,
        mock_review_pass_response
    ):
        """测试工作流执行（一次修正后通过）"""
        with patch('agents.specialized.outline_agent.LLMFactory.create_llm') as mock_llm_factory:
            mock_llm = AsyncMock()

            # 第一轮：outline -> character -> plot -> review (失败)
            # 第二轮：character (修正) -> plot -> review (通过)
            mock_llm.ainvoke = AsyncMock(side_effect=[
                mock_outline_response,  # 1. OutlineAgent
                mock_character_response,  # 2. CharacterAgent
                mock_plot_response,  # 3. PlotAgent
                mock_review_fail_response,  # 4. ReviewAgent (失败)
                mock_character_response,  # 5. CharacterAgent (修正)
                mock_plot_response,  # 6. PlotAgent
                mock_review_pass_response  # 7. ReviewAgent (通过)
            ])
            mock_llm_factory.return_value = mock_llm

            # 执行工作流
            final_state = await execute_agent_workflow_v2(
                task="创作一个测试故事",
                user_id="test_user",
                project_id="test_project",
                max_reflections=3,
                enable_human_review=False
            )

            # 验证
            assert final_state is not None
            assert final_state.get("review_passed") == True

            # 验证进行了一次反思循环
            # 注意：由于meta_scheduler会增加reflection_count
            reflection_count = final_state.get("reflection_count", 0)
            assert reflection_count >= 1

    @pytest.mark.asyncio
    async def test_workflow_max_iterations_reached(
        self,
        mock_outline_response,
        mock_character_response,
        mock_plot_response,
        mock_review_fail_response
    ):
        """测试达到最大迭代次数"""
        with patch('agents.specialized.outline_agent.LLMFactory.create_llm') as mock_llm_factory:
            mock_llm = AsyncMock()

            # 总是返回失败的审核
            responses = []
            for i in range(20):  # 提供足够多的响应
                responses.extend([
                    mock_outline_response,
                    mock_character_response,
                    mock_plot_response,
                    mock_review_fail_response
                ])

            mock_llm.ainvoke = AsyncMock(side_effect=responses)
            mock_llm_factory.return_value = mock_llm

            # 执行工作流（最多3次反思）
            final_state = await execute_agent_workflow_v2(
                task="创作一个测试故事",
                user_id="test_user",
                project_id="test_project",
                max_reflections=2,  # 设置较小的值以加快测试
                enable_human_review=False
            )

            # 验证
            assert final_state is not None

            # 应该达到最大迭代次数
            reflection_count = final_state.get("reflection_count", 0)
            assert reflection_count >= 2

            # 审核应该还是未通过
            assert final_state.get("review_passed") == False

    @pytest.mark.asyncio
    async def test_workflow_execution_times(
        self,
        mock_outline_response,
        mock_character_response,
        mock_plot_response,
        mock_review_pass_response
    ):
        """测试工作流执行时间追踪"""
        with patch('agents.specialized.outline_agent.LLMFactory.create_llm') as mock_llm_factory:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(side_effect=[
                mock_outline_response,
                mock_character_response,
                mock_plot_response,
                mock_review_pass_response
            ])
            mock_llm_factory.return_value = mock_llm

            # 执行工作流
            final_state = await execute_agent_workflow_v2(
                task="创作一个测试故事",
                user_id="test_user",
                project_id="test_project"
            )

            # 验证执行时间被记录
            agent_times = final_state.get("agent_execution_times", {})
            assert "outline_agent" in agent_times
            assert "character_agent" in agent_times
            assert "plot_agent" in agent_times

            # 验证所有时间都大于0
            for agent, exec_time in agent_times.items():
                assert exec_time > 0, f"{agent} execution time should be > 0"

    @pytest.mark.asyncio
    async def test_workflow_reasoning_chain(
        self,
        mock_outline_response,
        mock_character_response,
        mock_plot_response,
        mock_review_pass_response
    ):
        """测试工作流推理链"""
        with patch('agents.specialized.outline_agent.LLMFactory.create_llm') as mock_llm_factory:
            mock_llm = AsyncMock()
            mock_llm.ainvoke = AsyncMock(side_effect=[
                mock_outline_response,
                mock_character_response,
                mock_plot_response,
                mock_review_pass_response
            ])
            mock_llm_factory.return_value = mock_llm

            # 执行工作流
            final_state = await execute_agent_workflow_v2(
                task="创作一个测试故事",
                user_id="test_user",
                project_id="test_project"
            )

            # 验证推理链
            reasoning = final_state.get("reasoning", [])
            assert len(reasoning) > 0

            # 验证包含各个Agent的推理
            reasoning_text = "\n".join(reasoning)
            assert "OutlineAgent" in reasoning_text
            assert "CharacterAgent" in reasoning_text
            assert "PlotAgent" in reasoning_text


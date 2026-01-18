"""
测试BaseAgent和PipelineStateV2

测试Agent基类和新状态管理的功能。
"""

import pytest
import time
from src.agents.base_agent import BaseAgent, LLMAgentMixin, ExampleAgent
from src.agents.states.pipeline_state_v2 import (
    PipelineStateV2,
    create_initial_pipeline_state_v2,
    ExecutionStatus,
    CorrectionStrategy,
    DiagnosticReport,
    DiagnosticIssue,
    ExecutionPlan,
    WorkspaceContext,
    update_agent_output,
    add_diagnostic_report,
    should_continue_reflection,
    get_execution_summary
)


class TestPipelineStateV2:
    """测试Pipeline State v2.0"""
    
    def test_create_initial_state(self):
        """测试创建初始状态"""
        state = create_initial_pipeline_state_v2(
            task="测试任务",
            user_id="user_123",
            project_id="proj_123"
        )
        
        assert state["task"] == "测试任务"
        assert state["user_id"] == "user_123"
        assert state["project_id"] == "proj_123"
        assert state["status"] == ExecutionStatus.PLANNING.value
        assert state["reflection_count"] == 0
        assert state["max_reflections"] == 3
        assert "execution_id" in state
        assert isinstance(state["agent_outputs"], dict)
    
    def test_workspace_context(self):
        """测试工作区上下文"""
        context = WorkspaceContext(
            task_type="continue_writing",
            project_info={"title": "测试项目"},
            characters=[{"name": "张三"}],
            outline_nodes=[{"title": "第一章"}]
        )
        
        # 测试转换为字典
        context_dict = context.to_dict()
        assert context_dict["task_type"] == "continue_writing"
        assert len(context_dict["characters"]) == 1
        
        # 测试在state中使用
        state = create_initial_pipeline_state_v2(
            task="测试",
            user_id="user",
            project_id="proj",
            workspace_context=context
        )
        
        assert state["workspace_context"] is not None
        assert state["workspace_context"]["task_type"] == "continue_writing"
    
    def test_diagnostic_report(self):
        """测试诊断报告"""
        issue = DiagnosticIssue(
            id="issue-001",
            severity="high",
            category="character",
            root_cause="角色性格不一致",
            affected_entities=["张三"],
            correction_instruction="保持角色性格一致性"
        )
        
        report = DiagnosticReport(
            passed=False,
            quality_score=65,
            issues=[issue],
            correction_strategy=CorrectionStrategy.INCREMENTAL_FIX,
            affected_agents=["character_agent"],
            reasoning_chain=["检测到性格不一致", "需要增量修复"]
        )
        
        # 测试转换
        report_dict = report.to_dict()
        assert report_dict["passed"] == False
        assert report_dict["quality_score"] == 65
        assert len(report_dict["issues"]) == 1
        
        # 测试从字典创建
        report2 = DiagnosticReport.from_dict(report_dict)
        assert report2.passed == False
        assert len(report2.issues) == 1
    
    def test_update_agent_output(self):
        """测试更新Agent输出"""
        state = create_initial_pipeline_state_v2("test", "user", "proj")
        
        update = update_agent_output(
            state,
            agent_name="test_agent",
            output={"result": "success"}
        )
        
        assert "agent_outputs" in update
        assert "test_agent" in update["agent_outputs"]
        assert update["current_agent"] == "test_agent"
    
    def test_add_diagnostic_report(self):
        """测试添加诊断报告"""
        state = create_initial_pipeline_state_v2("test", "user", "proj")
        
        report = DiagnosticReport(
            passed=True,
            quality_score=90,
            issues=[]
        )
        
        update = add_diagnostic_report(state, report)
        
        assert "diagnostic_report" in update
        assert update["review_passed"] == True
        assert update["status"] == ExecutionStatus.COMPLETED.value
    
    def test_should_continue_reflection(self):
        """测试反思循环判断"""
        # 未通过审核，未达到最大次数
        state1 = create_initial_pipeline_state_v2("test", "user", "proj")
        state1["review_passed"] = False
        state1["reflection_count"] = 1
        assert should_continue_reflection(state1) == True
        
        # 通过审核
        state2 = create_initial_pipeline_state_v2("test", "user", "proj")
        state2["review_passed"] = True
        state2["reflection_count"] = 1
        assert should_continue_reflection(state2) == False
        
        # 达到最大次数
        state3 = create_initial_pipeline_state_v2("test", "user", "proj")
        state3["review_passed"] = False
        state3["reflection_count"] = 3
        state3["max_reflections"] = 3
        assert should_continue_reflection(state3) == False
    
    def test_execution_summary(self):
        """测试执行摘要"""
        state = create_initial_pipeline_state_v2("test", "user", "proj")
        state["start_time"] = time.time() - 10  # 10秒前
        state["reflection_count"] = 2
        state["review_passed"] = True
        state["tokens_used"] = 500
        state["agent_outputs"] = {"agent1": {}, "agent2": {}}
        
        summary = get_execution_summary(state)
        
        assert "execution_id" in summary
        assert summary["status"] == ExecutionStatus.PLANNING.value
        assert summary["reflection_count"] == 2
        assert summary["review_passed"] == True
        assert summary["tokens_used"] == 500
        assert len(summary["agents_executed"]) == 2
        assert summary["duration_seconds"] > 0


class TestLLMAgentMixin:
    """测试LLM Agent Mixin"""
    
    def test_build_system_prompt(self):
        """测试构建系统提示词"""
        class TestAgent(LLMAgentMixin):
            pass
        
        agent = TestAgent()
        prompt = agent.build_system_prompt(
            role_description="你是一个测试Agent",
            guidelines=["准则1", "准则2"]
        )
        
        assert "你是一个测试Agent" in prompt
        assert "准则1" in prompt
        assert "准则2" in prompt
    
    def test_build_user_prompt_with_context(self):
        """测试构建用户提示词"""
        class TestAgent(LLMAgentMixin):
            pass
        
        agent = TestAgent()
        
        context = WorkspaceContext(
            task_type="continue_writing",
            project_info={"title": "测试项目"},
            characters=[{"name": "张三"}],
            outline_nodes=[{"title": "第一章"}],
            previous_content="前面的内容..."
        )
        
        prompt = agent.build_user_prompt_with_context(
            task="继续写作",
            workspace_context=context,
            additional_context="额外信息"
        )
        
        assert "继续写作" in prompt
        assert "测试项目" in prompt
        assert "张三" in prompt
        assert "前面的内容" in prompt
        assert "额外信息" in prompt
    
    def test_estimate_tokens(self):
        """测试Token估算"""
        class TestAgent(LLMAgentMixin):
            pass
        
        agent = TestAgent()
        
        # 英文
        english_tokens = agent.estimate_tokens("Hello world")
        assert english_tokens > 0
        
        # 中文
        chinese_tokens = agent.estimate_tokens("你好世界")
        assert chinese_tokens > 0
        
        # 混合
        mixed_tokens = agent.estimate_tokens("Hello 你好 world 世界")
        assert mixed_tokens > 0


class TestBaseAgent:
    """测试BaseAgent基类"""
    
    @pytest.mark.asyncio
    async def test_example_agent_execution(self):
        """测试ExampleAgent执行"""
        agent = ExampleAgent()
        
        state = create_initial_pipeline_state_v2(
            task="测试任务",
            user_id="user_123",
            project_id="proj_123"
        )
        
        result = await agent.execute(state)
        
        assert "agent_outputs" in result
        assert "example_agent" in result["agent_outputs"]
        assert result["agent_outputs"]["example_agent"]["success"] == True
        assert "reasoning" in result
        assert "tokens_used" in result
    
    @pytest.mark.asyncio
    async def test_agent_with_workspace_context(self):
        """测试带工作区上下文的Agent执行"""
        from src.tools.workspace import WorkspaceContextTool
        
        workspace_tool = WorkspaceContextTool()
        agent = ExampleAgent(workspace_tool=workspace_tool)
        
        # 创建带工作区上下文的状态
        workspace_context = WorkspaceContext(
            task_type="test",
            project_info={"title": "测试项目"}
        )
        
        state = create_initial_pipeline_state_v2(
            task="测试任务",
            user_id="user_123",
            project_id="proj_123",
            workspace_context=workspace_context
        )
        
        result = await agent.execute(state)
        
        assert "agent_outputs" in result
        assert "example_agent" in result["agent_outputs"]
    
    def test_agent_stats(self):
        """测试Agent统计信息"""
        agent = ExampleAgent()
        
        # 初始统计
        stats = agent.get_stats()
        assert stats["execution_count"] == 0
        assert stats["total_tokens"] == 0
        
        # 模拟更新
        agent._update_stats(duration=1.5, tokens=100)
        agent._update_stats(duration=2.0, tokens=150)
        
        stats = agent.get_stats()
        assert stats["execution_count"] == 0  # 不会自动增加
        assert stats["total_tokens"] == 250
        assert stats["total_duration"] == 3.5
        
        # 重置统计
        agent.reset_stats()
        stats = agent.get_stats()
        assert stats["total_tokens"] == 0
    
    def test_agent_repr(self):
        """测试Agent字符串表示"""
        agent = ExampleAgent()
        repr_str = repr(agent)
        
        assert "ExampleAgent" in repr_str
        assert "example_agent" in repr_str


class TestCustomAgent:
    """测试自定义Agent实现"""
    
    @pytest.mark.asyncio
    async def test_custom_agent(self):
        """测试自定义Agent"""
        
        class CustomAgent(BaseAgent):
            """自定义测试Agent"""
            
            def __init__(self):
                super().__init__(
                    name="custom_agent",
                    description="自定义测试Agent"
                )
            
            async def _execute_impl(self, state, workspace_context, **kwargs):
                """实现具体逻辑"""
                return {
                    "agent_outputs": {
                        self.name: {
                            "custom_field": "custom_value",
                            "workspace_available": workspace_context is not None
                        }
                    },
                    "reasoning": ["Custom agent executed"],
                    "tokens_used": 50
                }
        
        # 创建并执行
        agent = CustomAgent()
        state = create_initial_pipeline_state_v2("test", "user", "proj")
        
        result = await agent.execute(state)
        
        assert "agent_outputs" in result
        assert "custom_agent" in result["agent_outputs"]
        assert result["agent_outputs"]["custom_agent"]["custom_field"] == "custom_value"
    
    @pytest.mark.asyncio
    async def test_agent_error_handling(self):
        """测试Agent错误处理"""
        
        class FailingAgent(BaseAgent):
            """会失败的Agent"""
            
            def __init__(self):
                super().__init__(
                    name="failing_agent",
                    description="故意失败的Agent"
                )
            
            async def _execute_impl(self, state, workspace_context, **kwargs):
                """抛出异常"""
                raise ValueError("Intentional error")
        
        # 创建并执行
        agent = FailingAgent()
        state = create_initial_pipeline_state_v2("test", "user", "proj")
        
        result = await agent.execute(state)
        
        # 应该返回错误状态而不是抛出异常
        assert "errors" in result
        assert len(result["errors"]) > 0
        assert "failing_agent" in result["errors"][0]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


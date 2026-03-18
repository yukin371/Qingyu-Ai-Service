"""
测试BaseAgentV2和PipelineStateV2

测试Agent基类和新状态管理的功能。
更新于v2.0：使用BaseAgentV2作为主基类
"""

import pytest
import time
from src.agents.base_agent import BaseAgentV2
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


class TestBaseAgentV2:
    """测试BaseAgentV2基类"""

    def test_agent_initialization(self):
        """测试Agent初始化"""

        class TestAgent(BaseAgentV2):
            """测试Agent"""

            def __init__(self):
                super().__init__(
                    name="test_agent",
                    description="测试Agent",
                    version="v1.0"
                )

            def get_runnable(self):
                from langchain_core.runnables import RunnableLambda
                return RunnableLambda(lambda state: state)

            async def execute(self, state):
                return state

        agent = TestAgent()

        assert agent.name == "test_agent"
        assert agent.description == "测试Agent"
        assert agent.version == "v1.0"

    def test_agent_repr(self):
        """测试Agent字符串表示"""

        class TestAgent(BaseAgentV2):
            def __init__(self):
                super().__init__("test", "desc")

            def get_runnable(self):
                from langchain_core.runnables import RunnableLambda
                return RunnableLambda(lambda x: x)

            async def execute(self, state):
                return state

        agent = TestAgent()
        repr_str = repr(agent)

        assert "test" in repr_str
        assert "v1.0" in repr_str


class TestCustomAgentV2:
    """测试自定义Agent实现（v2.0）"""

    @pytest.mark.asyncio
    async def test_custom_agent(self):
        """测试自定义Agent"""

        class CustomAgent(BaseAgentV2):
            """自定义测试Agent"""

            def __init__(self):
                super().__init__(
                    name="custom_agent",
                    description="自定义测试Agent"
                )

            def get_runnable(self):
                from langchain_core.runnables import RunnableLambda
                return RunnableLambda(lambda state: state)

            async def execute(self, state):
                """实现具体逻辑"""
                return update_agent_output(
                    state,
                    agent_name=self.name,
                    output={"custom_field": "custom_value"}
                )

        # 创建并执行
        agent = CustomAgent()
        state = create_initial_pipeline_state_v2("test", "user", "proj")

        result = await agent.execute(state)

        assert "agent_outputs" in result
        assert "custom_agent" in result["agent_outputs"]
        assert result["agent_outputs"]["custom_agent"]["custom_field"] == "custom_value"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


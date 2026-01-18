"""
测试增强审核Agent v2.0
"""
import os
import sys

import pytest

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agents.review import (
    CorrectionStrategy,
    DiagnosticIssue,
    DiagnosticReport,
    IssueCategory,
    IssueSeverity,
    ReviewAgentV2,
)
from agents.states.pipeline_state_v2 import PipelineStateV2
from core.logger import get_logger

logger = get_logger(__name__)


# ===== 测试诊断报告数据结构 =====


def test_diagnostic_issue():
    """测试诊断问题"""
    issue = DiagnosticIssue(
        id="issue-001",
        severity=IssueSeverity.HIGH,
        category=IssueCategory.CONSISTENCY,
        sub_category="character",
        title="角色定义缺失",
        description="角色'李四'在大纲中被提及，但未在角色列表中定义",
        root_cause="角色生成Agent未检测到大纲中提及的角色",
        affected_entities=["大纲节点：第三章", "角色列表"],
        impact="导致情节无法展开，角色关系不明确",
    )

    assert issue.id == "issue-001"
    assert issue.severity == IssueSeverity.HIGH
    assert issue.category == IssueCategory.CONSISTENCY
    assert "角色定义缺失" in issue.title
    logger.info(f"Diagnostic issue: {issue}")


def test_diagnostic_report():
    """测试诊断报告"""
    issues = [
        DiagnosticIssue(
            id="issue-001",
            severity=IssueSeverity.HIGH,
            category=IssueCategory.CONSISTENCY,
            sub_category="character",
            title="角色定义缺失",
            description="测试问题",
            root_cause="测试根因",
            affected_entities=["测试实体"],
            impact="测试影响",
        ),
        DiagnosticIssue(
            id="issue-002",
            severity=IssueSeverity.CRITICAL,
            category=IssueCategory.COMPLETENESS,
            sub_category="outline",
            title="大纲不完整",
            description="测试问题2",
            root_cause="测试根因2",
            affected_entities=["测试实体2"],
            impact="测试影响2",
        ),
    ]

    report = DiagnosticReport(
        passed=False,
        quality_score=65,
        issues=issues,
        correction_strategy=CorrectionStrategy.INCREMENTAL_FIX,
        correction_instructions=[],
        affected_agents=["character_agent"],
        reasoning_chain=["推理步骤1", "推理步骤2"],
    )

    assert report.passed is False
    assert report.quality_score == 65
    assert report.total_issues_count == 2
    assert report.critical_issues_count == 1
    assert report.high_issues_count == 1
    assert report.has_critical_issues() is True
    logger.info(f"Diagnostic report: {report.summary()}")


def test_diagnostic_report_queries():
    """测试诊断报告查询方法"""
    issues = [
        DiagnosticIssue(
            id=f"issue-{i}",
            severity=severity,
            category=category,
            sub_category="test",
            title=f"Test Issue {i}",
            description="Test",
            root_cause="Test",
            affected_entities=[],
            impact="Test",
        )
        for i, (severity, category) in enumerate(
            [
                (IssueSeverity.CRITICAL, IssueCategory.CONSISTENCY),
                (IssueSeverity.HIGH, IssueCategory.COMPLETENESS),
                (IssueSeverity.MEDIUM, IssueCategory.CONSISTENCY),
                (IssueSeverity.LOW, IssueCategory.QUALITY),
            ]
        )
    ]

    report = DiagnosticReport(
        passed=False,
        quality_score=60,
        issues=issues,
        correction_strategy=CorrectionStrategy.REGENERATE,
    )

    # 测试按严重程度查询
    critical = report.get_critical_issues()
    assert len(critical) == 1

    high = report.get_issues_by_severity(IssueSeverity.HIGH)
    assert len(high) == 1

    # 测试按类别查询
    consistency = report.get_issues_by_category(IssueCategory.CONSISTENCY)
    assert len(consistency) == 2

    logger.info(f"Report queries: critical={len(critical)}, high={len(high)}, consistency={len(consistency)}")


# ===== 测试ReviewAgentV2 =====


@pytest.mark.asyncio
async def test_review_agent_initialization():
    """测试ReviewAgent初始化"""
    # 设置Gemini API Key
    os.environ["GOOGLE_API_KEY"] = "AIzaSyD-q07WgZPd8mw4f1hVKVw44yXNUWrAuOk"
    os.environ["DEFAULT_LLM_PROVIDER"] = "gemini"
    os.environ["GEMINI_MODEL"] = "gemini-2.0-flash-exp"
    os.environ["GEMINI_TRANSPORT"] = "rest"

    agent = ReviewAgentV2(
        llm_provider="gemini",
        llm_model="gemini-2.0-flash-exp",
        temperature=0.3,
    )

    assert agent.get_name() == "ReviewAgentV2"
    assert agent.get_version() == "v2.0"
    assert agent.llm is not None

    logger.info(f"ReviewAgent initialized: {agent}")


@pytest.mark.asyncio
async def test_review_agent_with_simple_content():
    """测试ReviewAgent审核简单内容"""
    # 设置环境变量
    os.environ["GOOGLE_API_KEY"] = "AIzaSyD-q07WgZPd8mw4f1hVKVw44yXNUWrAuOk"
    os.environ["DEFAULT_LLM_PROVIDER"] = "gemini"

    agent = ReviewAgentV2()

    # 准备测试状态
    state: PipelineStateV2 = {
        "task": "创建一个科幻小说的开场",
        "user_id": "test_user",
        "project_id": "test_project",
        "session_id": "test_session",
        "constraints": {},
        "workspace_context": None,
        "messages": [],
        "reasoning": [],
        "current_step": "review",
        "plan": [],
        "current_plan_index": 0,
        "iteration_count": 0,
        "max_iterations": 3,
        "rag_results": [],
        "retrieved_context": "",
        "generated_content": "时间旅行者艾米丽站在实验室中，望着墙上逆转的时钟...",
        "content_draft": "",
        "tool_calls": [],
        "tools_to_use": [],
        "review_report": None,
        "review_passed": False,
        "correction_strategy": "",
        "affected_agents": [],
        "correction_instructions": [],
        "final_output": "",
        "output_metadata": {},
        "errors": [],
        "warnings": [],
        "start_time": 0.0,
        "tokens_used": 0,
    }

    # 执行审核
    logger.info("Executing ReviewAgent...")
    result_state = await agent.execute(state)

    # 验证结果
    assert "review_report" in result_state
    assert result_state["review_report"] is not None

    report_dict = result_state["review_report"]
    assert "passed" in report_dict
    assert "quality_score" in report_dict
    assert "issues" in report_dict

    logger.info(f"Review completed:")
    logger.info(f"  - Passed: {report_dict['passed']}")
    logger.info(f"  - Quality Score: {report_dict['quality_score']}")
    logger.info(f"  - Issues Count: {len(report_dict['issues'])}")
    logger.info(f"  - Correction Strategy: {report_dict.get('correction_strategy')}")


@pytest.mark.asyncio
async def test_review_agent_with_problematic_content():
    """测试ReviewAgent审核有问题的内容"""
    # 设置环境变量
    os.environ["GOOGLE_API_KEY"] = "AIzaSyD-q07WgZPd8mw4f1hVKVw44yXNUWrAuOk"
    os.environ["DEFAULT_LLM_PROVIDER"] = "gemini"

    agent = ReviewAgentV2()

    # 准备包含明显问题的内容
    state: PipelineStateV2 = {
        "task": "续写科幻小说第三章",
        "user_id": "test_user",
        "project_id": "test_project",
        "session_id": "test_session",
        "constraints": {},
        "workspace_context": {
            "task_type": "continue_writing",
            "previous_content": {
                "content": "第一章：主角艾米丽是一个物理学家。"
            },
            "characters": [
                {"name": "艾米丽", "role_type": "protagonist", "traits": ["聪明", "谨慎"]}
            ],
            "outline": {
                "nodes": [
                    {"name": "第一章", "description": "介绍主角"},
                    {"name": "第二章", "description": "主角发现时间机器"},
                    {
                        "name": "第三章",
                        "description": "主角与李四一起进行时间旅行实验",
                    },
                ]
            },
        },
        "messages": [],
        "reasoning": [],
        "current_step": "review",
        "plan": [],
        "current_plan_index": 0,
        "iteration_count": 0,
        "max_iterations": 3,
        "rag_results": [],
        "retrieved_context": "",
        "generated_content": """第三章：时间旅行

艾米丽和李四站在时间机器前。李四说："我们应该去2077年看看。"
艾米丽点头同意，两人启动了时间机器...""",
        "content_draft": "",
        "tool_calls": [],
        "tools_to_use": [],
        "review_report": None,
        "review_passed": False,
        "correction_strategy": "",
        "affected_agents": [],
        "correction_instructions": [],
        "final_output": "",
        "output_metadata": {},
        "errors": [],
        "warnings": [],
        "start_time": 0.0,
        "tokens_used": 0,
    }

    # 执行审核
    logger.info("Executing ReviewAgent with problematic content...")
    result_state = await agent.execute(state)

    # 验证结果
    report_dict = result_state["review_report"]

    logger.info(f"Review completed:")
    logger.info(f"  - Passed: {report_dict['passed']}")
    logger.info(f"  - Quality Score: {report_dict['quality_score']}")
    logger.info(f"  - Issues Count: {len(report_dict['issues'])}")
    logger.info(f"  - Correction Strategy: {report_dict.get('correction_strategy')}")

    if report_dict["issues"]:
        logger.info(f"\nIssues found:")
        for issue in report_dict["issues"]:
            logger.info(f"  - [{issue['severity']}] {issue['title']}")
            logger.info(f"    Root Cause: {issue['root_cause']}")


@pytest.mark.asyncio
async def test_review_agent_error_handling():
    """测试ReviewAgent错误处理"""
    # 设置环境变量
    os.environ["GOOGLE_API_KEY"] = "AIzaSyD-q07WgZPd8mw4f1hVKVw44yXNUWrAuOk"
    os.environ["DEFAULT_LLM_PROVIDER"] = "gemini"

    agent = ReviewAgentV2()

    # 准备空状态（应该触发错误处理）
    state: PipelineStateV2 = {
        "task": "",
        "user_id": "test_user",
        "project_id": "test_project",
        "session_id": "test_session",
        "constraints": {},
        "workspace_context": None,
        "messages": [],
        "reasoning": [],
        "current_step": "review",
        "plan": [],
        "current_plan_index": 0,
        "iteration_count": 0,
        "max_iterations": 3,
        "rag_results": [],
        "retrieved_context": "",
        "generated_content": "",
        "content_draft": "",
        "tool_calls": [],
        "tools_to_use": [],
        "review_report": None,
        "review_passed": False,
        "correction_strategy": "",
        "affected_agents": [],
        "correction_instructions": [],
        "final_output": "",
        "output_metadata": {},
        "errors": [],
        "warnings": [],
        "start_time": 0.0,
        "tokens_used": 0,
    }

    # 执行审核
    logger.info("Testing error handling...")
    result_state = await agent.execute(state)

    # 应该有review_report（可能是默认通过）
    assert "review_report" in result_state

    logger.info(f"Error handling test completed")


# ===== 主测试入口 =====


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-k", "test_review_agent"])


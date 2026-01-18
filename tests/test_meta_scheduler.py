"""
测试元调度器
"""
import os
import sys

import pytest

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agents.meta import CorrectionPromptBuilder, MetaScheduler
from agents.review import (
    CorrectionInstruction,
    CorrectionStrategy,
    DiagnosticIssue,
    DiagnosticReport,
    IssueCategory,
    IssueSeverity,
)
from agents.states.pipeline_state_v2 import PipelineStateV2
from core.logger import get_logger

logger = get_logger(__name__)


# ===== 测试CorrectionPromptBuilder =====


def test_correction_prompt_builder():
    """测试修正Prompt构建器"""
    # 创建诊断报告
    issues = [
        DiagnosticIssue(
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
    ]

    instructions = [
        CorrectionInstruction(
            issue_id="issue-001",
            target_agent="character_agent",
            action="create",
            specific_instruction="创建角色'李四'，设定为：配角，主角的挚友，性格开朗但有些冲动。",
            parameters={"name": "李四", "role_type": "supporting", "traits": ["开朗", "冲动"]},
            priority=8,
        )
    ]

    report = DiagnosticReport(
        passed=False,
        quality_score=65,
        issues=issues,
        correction_strategy=CorrectionStrategy.INCREMENTAL_FIX,
        correction_instructions=instructions,
        affected_agents=["character_agent"],
        reasoning_chain=["检查大纲", "发现问题", "制定策略"],
    )

    # 构建修正Prompt
    prompt = CorrectionPromptBuilder.build_correction_prompt(
        agent_name="character_agent",
        instructions=instructions,
        diagnostic_report=report,
        original_output=None,
        correction_mode="incremental",
    )

    assert "修正任务" in prompt
    assert "增量修复" in prompt
    assert "李四" in prompt
    assert "质量分数: 65" in prompt
    assert "角色生成Agent未检测到大纲中提及的角色" in prompt

    logger.info(f"Generated correction prompt ({len(prompt)} chars)")


def test_batch_correction_prompts():
    """测试批量构建修正Prompt"""
    issues = [
        DiagnosticIssue(
            id="issue-001",
            severity=IssueSeverity.HIGH,
            category=IssueCategory.CONSISTENCY,
            sub_category="character",
            title="角色定义缺失",
            description="测试",
            root_cause="测试",
            affected_entities=[],
            impact="测试",
        ),
        DiagnosticIssue(
            id="issue-002",
            severity=IssueSeverity.MEDIUM,
            category=IssueCategory.COMPLETENESS,
            sub_category="outline",
            title="大纲不完整",
            description="测试",
            root_cause="测试",
            affected_entities=[],
            impact="测试",
        ),
    ]

    instructions = [
        CorrectionInstruction(
            issue_id="issue-001",
            target_agent="character_agent",
            action="create",
            specific_instruction="创建角色",
            parameters={},
            priority=8,
        ),
        CorrectionInstruction(
            issue_id="issue-002",
            target_agent="outline_agent",
            action="update",
            specific_instruction="补充大纲",
            parameters={},
            priority=7,
        ),
    ]

    report = DiagnosticReport(
        passed=False,
        quality_score=60,
        issues=issues,
        correction_strategy=CorrectionStrategy.INCREMENTAL_FIX,
        correction_instructions=instructions,
        affected_agents=["character_agent", "outline_agent"],
        reasoning_chain=[],
    )

    # 批量构建
    prompts = CorrectionPromptBuilder.build_batch_correction_prompts(
        affected_agents=["character_agent", "outline_agent"],
        diagnostic_report=report,
        correction_mode="incremental",
    )

    assert len(prompts) == 2
    assert "character_agent" in prompts
    assert "outline_agent" in prompts

    logger.info(f"Generated {len(prompts)} correction prompts")


# ===== 测试MetaScheduler =====


def test_meta_scheduler_initialization():
    """测试MetaScheduler初始化"""
    scheduler = MetaScheduler(max_iterations=3, auto_downgrade_threshold=0.3)

    assert scheduler.get_name() == "MetaScheduler"
    assert scheduler.max_iterations == 3
    assert scheduler.auto_downgrade_threshold == 0.3

    logger.info(f"MetaScheduler initialized: {scheduler}")


@pytest.mark.asyncio
async def test_meta_scheduler_basic_execution():
    """测试MetaScheduler基本执行"""
    scheduler = MetaScheduler(max_iterations=3)

    # 创建诊断报告
    issues = [
        DiagnosticIssue(
            id="issue-001",
            severity=IssueSeverity.HIGH,
            category=IssueCategory.CONSISTENCY,
            sub_category="character",
            title="角色定义缺失",
            description="测试",
            root_cause="测试",
            affected_entities=[],
            impact="测试",
        )
    ]

    instructions = [
        CorrectionInstruction(
            issue_id="issue-001",
            target_agent="character_agent",
            action="create",
            specific_instruction="创建角色",
            parameters={},
            priority=8,
        )
    ]

    report = DiagnosticReport(
        passed=False,
        quality_score=65,
        issues=issues,
        correction_strategy=CorrectionStrategy.INCREMENTAL_FIX,
        correction_instructions=instructions,
        affected_agents=["character_agent"],
        reasoning_chain=[],
    )

    # 准备状态
    state: PipelineStateV2 = {
        "task": "测试任务",
        "user_id": "test_user",
        "project_id": "test_project",
        "session_id": "test_session",
        "constraints": {},
        "workspace_context": None,
        "messages": [],
        "reasoning": [],
        "current_step": "meta_scheduler",
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
        "review_report": report.model_dump(),
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

    # 执行元调度
    result_state = await scheduler.execute(state)

    # 验证结果
    assert result_state["iteration_count"] == 1
    assert "correction_prompts" in result_state
    assert "correction_mode" in result_state
    assert result_state["correction_mode"] == "incremental"
    assert result_state["current_step"] == "character_agent"
    assert "character_agent" in result_state["affected_agents"]

    logger.info(f"MetaScheduler execution result:")
    logger.info(f"  - Iteration: {result_state['iteration_count']}/3")
    logger.info(f"  - Correction mode: {result_state['correction_mode']}")
    logger.info(f"  - Restart agent: {result_state['current_step']}")
    logger.info(f"  - Affected agents: {result_state['affected_agents']}")


@pytest.mark.asyncio
async def test_meta_scheduler_max_iterations():
    """测试MetaScheduler最大迭代次数"""
    scheduler = MetaScheduler(max_iterations=3)

    report = DiagnosticReport(
        passed=False,
        quality_score=50,
        issues=[],
        correction_strategy=CorrectionStrategy.REGENERATE,
        correction_instructions=[],
        affected_agents=["outline_agent"],
        reasoning_chain=[],
    )

    # 准备状态（已达到最大迭代次数）
    state: PipelineStateV2 = {
        "task": "测试任务",
        "user_id": "test_user",
        "project_id": "test_project",
        "session_id": "test_session",
        "constraints": {},
        "workspace_context": None,
        "messages": [],
        "reasoning": [],
        "current_step": "meta_scheduler",
        "plan": [],
        "current_plan_index": 0,
        "iteration_count": 3,  # 已经3次了
        "max_iterations": 3,
        "rag_results": [],
        "retrieved_context": "",
        "generated_content": "",
        "content_draft": "",
        "tool_calls": [],
        "tools_to_use": [],
        "review_report": report.model_dump(),
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

    # 执行元调度
    result_state = await scheduler.execute(state)

    # 应该升级到人工审核
    assert result_state["current_step"] == "human_review"
    assert "达到最大迭代次数" in result_state["reasoning"][-2]

    logger.info("Max iterations reached, escalated to human review")


@pytest.mark.asyncio
async def test_meta_scheduler_regenerate_mode():
    """测试MetaScheduler全量重生成模式"""
    scheduler = MetaScheduler()

    # 创建包含严重问题的诊断报告
    issues = [
        DiagnosticIssue(
            id="issue-001",
            severity=IssueSeverity.CRITICAL,
            category=IssueCategory.COMPLETENESS,
            sub_category="outline",
            title="大纲缺失",
            description="测试",
            root_cause="测试",
            affected_entities=[],
            impact="测试",
        )
    ]

    instructions = [
        CorrectionInstruction(
            issue_id="issue-001",
            target_agent="outline_agent",
            action="regenerate",
            specific_instruction="重新生成大纲",
            parameters={},
            priority=10,
        )
    ]

    report = DiagnosticReport(
        passed=False,
        quality_score=40,  # 低质量分数
        issues=issues,
        correction_strategy=CorrectionStrategy.REGENERATE,
        correction_instructions=instructions,
        affected_agents=["outline_agent"],
        reasoning_chain=[],
    )

    state: PipelineStateV2 = {
        "task": "测试任务",
        "user_id": "test_user",
        "project_id": "test_project",
        "session_id": "test_session",
        "constraints": {},
        "workspace_context": None,
        "messages": [],
        "reasoning": [],
        "current_step": "meta_scheduler",
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
        "review_report": report.model_dump(),
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
        "outline_agent_output": {"some": "output"},  # 模拟原有输出
    }

    # 执行元调度
    result_state = await scheduler.execute(state)

    # 应该是全量重生成模式
    assert result_state["correction_mode"] == "regenerate"
    # 原有输出应该被清除
    assert "outline_agent_output" not in result_state

    logger.info(f"Regenerate mode activated, outputs cleared")


# ===== 主测试入口 =====


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])







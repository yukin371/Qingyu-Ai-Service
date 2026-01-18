"""
Routers v2.0 - 工作流路由函数

决定工作流的下一个节点，支持反思循环
"""
from typing import Any, Dict

from src.agents.states.pipeline_state_v2 import PipelineStateV2
from src.core.logger import get_logger

logger = get_logger(__name__)


def review_router(state: PipelineStateV2) -> str:
    """审核后的路由决策

    决定审核后的下一步：
    - completed: 审核通过，流程完成
    - meta_scheduler: 审核不通过，进入元调度器修正
    - human_review: 达到最大迭代次数，需要人工审核

    Args:
        state: 当前状态

    Returns:
        下一个节点名称
    """
    # 检查审核是否通过
    review_passed = state.get("review_passed", False)

    if review_passed:
        logger.info("Review passed, completing workflow")
        return "completed"

    # 检查迭代次数
    reflection_count = state.get("reflection_count", 0)
    max_reflections = state.get("max_reflections", 3)

    if reflection_count >= max_reflections:
        logger.warning(
            f"Max reflections ({max_reflections}) reached, escalating to human review"
        )
        return "human_review"

    # 检查修正策略
    correction_strategy = state.get("correction_strategy", "")

    if correction_strategy == "human_review":
        logger.info("Correction strategy requires human review")
        return "human_review"

    # 默认：进入元调度器
    logger.info(
        f"Review failed (reflection {reflection_count + 1}/{max_reflections}), "
        f"proceeding to meta_scheduler"
    )
    return "meta_scheduler"


def meta_scheduler_router(state: PipelineStateV2) -> str:
    """元调度器的路由决策

    根据诊断报告，决定从哪个Agent重新开始：
    - outline: 从大纲Agent重新开始
    - character: 从角色Agent重新开始
    - plot: 从情节Agent重新开始
    - completed: 无需修正，完成
    - human_review: 无法自动修正，需要人工审核

    Args:
        state: 当前状态

    Returns:
        下一个节点名称
    """
    # 获取当前步骤（由元调度器设置）
    current_step = state.get("current_step", "")

    # 特殊情况：已完成或需要人工审核
    if current_step == "completed":
        logger.info("Meta scheduler determined: completed")
        return "completed"

    if current_step == "human_review":
        logger.info("Meta scheduler determined: human_review")
        return "human_review"

    # Agent路由
    agent_routes = {
        "outline": "outline",
        "character": "character",
        "plot": "plot",
        "outline_agent": "outline",
        "character_agent": "character",
        "plot_agent": "plot"
    }

    next_node = agent_routes.get(current_step, "outline")

    logger.info(f"Meta scheduler routing to: {next_node} (from step: {current_step})")
    return next_node


def should_end_workflow(state: PipelineStateV2) -> bool:
    """判断是否应该结束工作流

    Args:
        state: 当前状态

    Returns:
        是否结束
    """
    # 审核通过
    if state.get("review_passed", False):
        return True

    # 达到最大迭代次数
    reflection_count = state.get("reflection_count", 0)
    max_reflections = state.get("max_reflections", 3)

    if reflection_count >= max_reflections:
        return True

    # 当前步骤是completed或human_review
    current_step = state.get("current_step", "")
    if current_step in ["completed", "human_review", "error"]:
        return True

    # 有严重错误
    errors = state.get("errors", [])
    if len(errors) > 0:
        logger.warning(f"Workflow has errors: {len(errors)}")
        # 注意：有错误不一定立即结束，可能会尝试修正
        # 这里只是记录，不强制结束

    return False


def get_next_agent_in_sequence(state: PipelineStateV2) -> str:
    """获取序列中的下一个Agent

    用于顺序执行场景（非反思循环）

    Args:
        state: 当前状态

    Returns:
        下一个Agent名称
    """
    current_agent = state.get("current_agent", "")

    # 正常顺序
    sequence = {
        "": "outline",
        "outline": "character",
        "outline_agent": "character",
        "character": "plot",
        "character_agent": "plot",
        "plot": "review",
        "plot_agent": "review"
    }

    next_agent = sequence.get(current_agent, "outline")

    logger.debug(f"Next agent in sequence: {next_agent} (after {current_agent})")
    return next_agent


def check_workflow_health(state: PipelineStateV2) -> Dict[str, Any]:
    """检查工作流健康状态

    Args:
        state: 当前状态

    Returns:
        健康状态信息
    """
    errors = state.get("errors", [])
    warnings = state.get("warnings", [])
    reflection_count = state.get("reflection_count", 0)
    max_reflections = state.get("max_reflections", 3)
    review_passed = state.get("review_passed", False)

    health = {
        "healthy": len(errors) == 0,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "reflection_count": reflection_count,
        "max_reflections": max_reflections,
        "reflection_utilization": reflection_count / max(max_reflections, 1),
        "review_passed": review_passed,
        "status": "healthy"
    }

    # 确定状态
    if len(errors) > 0:
        health["status"] = "error"
    elif reflection_count >= max_reflections and not review_passed:
        health["status"] = "needs_intervention"
    elif reflection_count > 0:
        health["status"] = "correcting"
    elif review_passed:
        health["status"] = "completed"

    return health


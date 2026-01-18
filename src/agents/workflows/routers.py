"""Router Functions - 工作流路由函数

决定工作流的下一个节点
"""

from src.agents.states.creative_state import CreativeAgentState
from src.core.logger import get_logger

logger = get_logger(__name__)


def should_regenerate(state: CreativeAgentState) -> str:
    """决定是否重新生成

    在审核节点后调用，决定下一步

    Args:
        state: 当前状态

    Returns:
        下一个节点名称：
        - "finalize": 审核通过，进入最终化
        - "regenerate": 审核不通过，重新生成
        - "restart": 分数太低，重新理解任务
        - "force_finalize": 重试次数耗尽，强制完成
    """
    # 如果审核通过，进入最终化
    if state.get("review_passed", False):
        logger.info("Review passed, proceeding to finalize")
        return "finalize"

    # 检查重试次数
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)

    if retry_count >= max_retries:
        logger.warning(f"Max retries ({max_retries}) reached, forcing finalize")
        return "force_finalize"

    # 检查严重问题
    review_result = state.get("review_result", {})
    score = review_result.get("score", 0)

    if score < 40:
        # 分数太低，需要重新理解任务
        logger.info("Score too low, restarting from understanding")
        return "restart"

    # 普通重试，回到生成节点
    logger.info(f"Review failed (score: {score}), regenerating...")
    return "regenerate"


def should_continue_plan(state: CreativeAgentState) -> str:
    """决定是否继续执行计划

    在计划执行过程中调用

    Args:
        state: 当前状态

    Returns:
        下一个节点名称
    """
    plan = state.get("plan", [])
    current_index = state.get("current_plan_index", 0)

    if current_index >= len(plan):
        logger.info("Plan completed, proceeding to generation")
        return "generation"

    # 获取当前计划步骤
    current_step = plan[current_index]
    tool = current_step.get("tool", "")

    # 根据工具类型路由到不同节点
    if tool == "rag_tool":
        return "rag_retrieval"
    elif tool in ["character_tool", "outline_tool", "timeline_tool"]:
        return "tool_execution"
    else:
        return "generation"


def check_errors(state: CreativeAgentState) -> str:
    """检查是否有严重错误

    在每个节点后可选调用

    Args:
        state: 当前状态

    Returns:
        下一个节点名称：
        - "error_handler": 有错误
        - "continue": 无错误，继续
    """
    errors = state.get("errors", [])

    if errors:
        logger.error(f"Errors detected: {len(errors)}")
        return "error_handler"

    return "continue"


def route_after_understanding(state: CreativeAgentState) -> str:
    """理解任务后的路由

    Args:
        state: 当前状态

    Returns:
        下一个节点名称
    """
    # 检查是否有错误
    if state.get("errors"):
        return "error"

    # 检查是否需要RAG
    tools_to_use = state.get("tools_to_use", [])

    if "rag_tool" in tools_to_use:
        logger.info("RAG required, proceeding to retrieval")
        return "rag_retrieval"
    else:
        logger.info("No RAG required, proceeding to generation")
        return "generation"


"""Finalize Node - 最终化节点

整理最终输出，添加元数据
"""

import time
from typing import Dict

from src.agents.states.creative_state import CreativeAgentState
from src.core.logger import get_logger

logger = get_logger(__name__)


async def finalize_node(state: CreativeAgentState) -> Dict:
    """最终化节点

    职责：
    1. 整理最终输出
    2. 添加元数据
    3. 准备返回结果

    Args:
        state: 当前状态

    Returns:
        更新后的状态
    """
    logger.info("Finalizing output...")

    # 计算总耗时
    start_time = state.get("start_time", time.time())
    total_duration = time.time() - start_time

    # 构建输出元数据
    output_metadata = {
        "tokens_used": state.get("tokens_used", 0),
        "retry_count": state.get("retry_count", 0),
        "review_score": state.get("review_result", {}).get("score", 0),
        "rag_sources_count": len(state.get("rag_results", [])),
        "tool_calls_count": len(state.get("tool_calls", [])),
        "reasoning_steps": len(state.get("reasoning", [])),
        "total_duration_seconds": round(total_duration, 2),
        "warnings_count": len(state.get("warnings", [])),
        "errors_count": len(state.get("errors", [])),
    }

    logger.info(
        "Finalization completed",
        output_length=len(state.get("generated_content", "")),
        total_duration=output_metadata["total_duration_seconds"],
        tokens_used=output_metadata["tokens_used"],
    )

    return {
        "final_output": state.get("generated_content", ""),
        "output_metadata": output_metadata,
        "current_step": "completed",
        "reasoning": [
            "任务完成",
            f"总耗时：{output_metadata['total_duration_seconds']}秒",
            f"总Token使用：{output_metadata['tokens_used']}",
        ],
    }


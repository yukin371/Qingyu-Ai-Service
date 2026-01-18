"""RAG Retrieval Node - RAG检索节点

从向量数据库检索相关知识，构建上下文
"""

from typing import Dict

from src.agents.states.creative_state import CreativeAgentState
from src.core.logger import get_logger

logger = get_logger(__name__)


async def rag_retrieval_node(state: CreativeAgentState) -> Dict:
    """RAG检索节点

    职责：
    1. 构建检索查询
    2. 调用RAG Tool
    3. 组织检索结果

    Args:
        state: 当前状态

    Returns:
        更新后的状态
    """
    logger.info("Retrieving relevant knowledge...")

    # 检查是否需要RAG
    if "rag_tool" not in state.get("tools_to_use", []):
        logger.info("RAG not required, skipping...")
        return {
            "current_step": "generation",
            "reasoning": ["跳过RAG检索"],
        }

    # 构建查询（从任务中提取关键词）
    query = state["task"]
    project_id = state["project_id"]

    try:
        # 从状态中获取RAG Tool（由工作流注入）
        rag_tool = state.get("_rag_tool")

        if rag_tool:
            # 调用RAG Tool
            result = await rag_tool.execute(
                params={
                    "query": query,
                    "project_id": project_id,
                    "content_types": ["character", "location", "outline", "timeline"],
                    "top_k": 5,
                    "enable_rerank": True,
                },
                user_id=state["user_id"],
                project_id=project_id,
            )

            if result.success:
                rag_results = result.data.get("results", [])

                # 组织检索结果为上下文
                context_parts = []
                for i, res in enumerate(rag_results, 1):
                    context_parts.append(
                        f"""【参考资料 {i}】（类型：{res.get('content_type', 'unknown')}，相关度：{res.get('score', 0):.2f}）
{res.get('content', '')}
"""
                    )

                retrieved_context = "\n".join(context_parts)

                logger.info(
                    "RAG retrieval completed",
                    results_count=len(rag_results),
                    top_score=rag_results[0]["score"] if rag_results else 0,
                )

                return {
                    "rag_results": rag_results,
                    "retrieved_context": retrieved_context,
                    "current_step": "generation",
                    "reasoning": [f"RAG检索完成，找到 {len(rag_results)} 条相关资料"],
                }
            else:
                logger.warning(f"RAG retrieval failed: {result.error}")
                return {
                    "current_step": "generation",
                    "warnings": [f"RAG检索失败: {result.error}"],
                    "reasoning": ["RAG检索失败，继续执行"],
                }
        else:
            logger.warning("RAG tool not available in state")
            return {
                "current_step": "generation",
                "warnings": ["RAG工具不可用"],
                "reasoning": ["RAG工具不可用，跳过检索"],
            }

    except Exception as e:
        logger.error(f"RAG retrieval node failed: {e}", exc_info=True)
        return {
            "current_step": "generation",
            "warnings": [f"RAG检索异常: {str(e)}"],
            "reasoning": ["RAG检索异常，继续执行"],
        }


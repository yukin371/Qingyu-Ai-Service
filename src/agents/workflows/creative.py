"""Creative Workflow - 创作工作流

使用LangGraph编排创作Agent的完整流程
"""

from typing import Dict

from langgraph.graph import END, StateGraph

from src.agents.nodes import (
    finalize_node,
    generation_node,
    rag_retrieval_node,
    review_node,
    understand_task_node,
)
from src.agents.states.creative_state import CreativeAgentState
from src.agents.workflows.routers import route_after_understanding, should_regenerate
from src.core.logger import get_logger

logger = get_logger(__name__)


def create_creative_workflow():
    """创建创作工作流

    工作流程：
    1. understand -> 理解任务
    2. rag_retrieval -> RAG检索（可选）
    3. generation -> 生成内容
    4. review -> 审核内容
    5. regenerate -> 重新生成（如果审核不通过）
    6. finalize -> 最终化输出

    Returns:
        编译后的工作流
    """
    logger.info("Creating creative workflow...")

    # 创建状态图
    workflow = StateGraph(CreativeAgentState)

    # 添加节点
    workflow.add_node("understand", understand_task_node)
    workflow.add_node("rag_retrieval", rag_retrieval_node)
    workflow.add_node("generation", generation_node)
    workflow.add_node("review", review_node)
    workflow.add_node("finalize", finalize_node)

    # 添加regenerate节点（增加重试计数）
    async def regenerate_node(state: CreativeAgentState) -> Dict:
        """重新生成节点（增加重试计数）"""
        return {
            "retry_count": state.get("retry_count", 0) + 1,
            "reasoning": ["重试生成"],
        }

    workflow.add_node("regenerate", regenerate_node)

    # 设置入口点
    workflow.set_entry_point("understand")

    # 添加条件边：理解任务后的路由
    workflow.add_conditional_edges(
        "understand",
        route_after_understanding,
        {
            "rag_retrieval": "rag_retrieval",
            "generation": "generation",
            "error": END,
        },
    )

    # RAG检索后进入生成
    workflow.add_edge("rag_retrieval", "generation")

    # 生成后进入审核
    workflow.add_edge("generation", "review")

    # 添加条件边：审核后的路由
    workflow.add_conditional_edges(
        "review",
        should_regenerate,
        {
            "finalize": "finalize",
            "regenerate": "regenerate",
            "restart": "understand",
            "force_finalize": "finalize",
        },
    )

    # regenerate回到generation
    workflow.add_edge("regenerate", "generation")

    # 最终化后结束
    workflow.add_edge("finalize", END)

    # 编译工作流
    app = workflow.compile()

    logger.info("Creative workflow created successfully")
    return app


def visualize_workflow(workflow):
    """可视化工作流（生成Mermaid图）

    Args:
        workflow: 编译后的工作流

    Returns:
        Mermaid图字符串
    """
    try:
        # 获取Mermaid图
        mermaid_str = workflow.get_graph().draw_mermaid()
        return mermaid_str
    except Exception as e:
        logger.error(f"Failed to generate Mermaid diagram: {e}")
        return None


async def execute_creative_workflow(
    task: str,
    user_id: str,
    project_id: str,
    constraints: Dict = None,
    context: Dict = None,
    max_retries: int = 3,
    rag_tool=None,
):
    """执行创作工作流

    Args:
        task: 创作任务
        user_id: 用户ID
        project_id: 项目ID
        constraints: 创作约束
        context: 上下文信息
        max_retries: 最大重试次数
        rag_tool: RAG工具实例（可选注入）

    Returns:
        最终状态
    """
    from agents.states.creative_state import create_initial_creative_state

    # 创建初始状态
    initial_state = create_initial_creative_state(
        task=task,
        user_id=user_id,
        project_id=project_id,
        constraints=constraints,
        context=context,
        max_retries=max_retries,
    )

    # 注入RAG工具到状态（如果提供）
    if rag_tool:
        initial_state["_rag_tool"] = rag_tool

    # 创建工作流
    workflow = create_creative_workflow()

    # 执行工作流
    logger.info(
        "Executing creative workflow",
        task=task[:100],
        user_id=user_id,
        project_id=project_id,
    )

    final_state = await workflow.ainvoke(initial_state)

    logger.info(
        "Creative workflow completed",
        status=final_state.get("current_step"),
        output_length=len(final_state.get("final_output", "")),
    )

    return final_state


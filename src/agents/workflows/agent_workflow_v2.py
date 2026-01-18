"""
Agent Workflow v2.0 - 基于LangGraph的Agent协作工作流

特点：
1. 支持反思循环（Reflection Loop）
2. 动态Agent路由
3. 元调度器智能修正
4. 完整的错误处理
"""
from typing import Dict, Any

from langgraph.graph import END, StateGraph

from src.agents.specialized import OutlineAgent, CharacterAgent, PlotAgent
from src.agents.review.review_agent_v2 import ReviewAgentV2
from src.agents.meta.meta_scheduler import MetaScheduler
from src.agents.states.pipeline_state_v2 import PipelineStateV2
from src.agents.workflows.routers_v2 import (
    review_router,
    meta_scheduler_router,
    should_end_workflow
)
from src.core.logger import get_logger

logger = get_logger(__name__)


# ===== Node适配器函数 =====
# 将Agent的execute方法适配为LangGraph节点

async def outline_node(state: PipelineStateV2) -> Dict[str, Any]:
    """大纲生成节点"""
    logger.info("Executing outline_node")
    agent = OutlineAgent()
    return await agent.execute(state)


async def character_node(state: PipelineStateV2) -> Dict[str, Any]:
    """角色设计节点"""
    logger.info("Executing character_node")
    agent = CharacterAgent()
    return await agent.execute(state)


async def plot_node(state: PipelineStateV2) -> Dict[str, Any]:
    """情节安排节点"""
    logger.info("Executing plot_node")
    agent = PlotAgent()
    return await agent.execute(state)


async def review_node_v2(state: PipelineStateV2) -> Dict[str, Any]:
    """审核节点（v2.0）"""
    logger.info("Executing review_node_v2")
    agent = ReviewAgentV2()
    return await agent.execute(state)


async def meta_scheduler_node(state: PipelineStateV2) -> Dict[str, Any]:
    """元调度器节点"""
    logger.info("Executing meta_scheduler_node")
    agent = MetaScheduler()
    return await agent.execute(state)


async def human_review_node(state: PipelineStateV2) -> Dict[str, Any]:
    """人工审核节点（占位）"""
    logger.info("Executing human_review_node - waiting for human intervention")

    return {
        **state,
        "current_step": "human_review_pending",
        "reasoning": state.get("reasoning", []) + [
            "工作流已暂停，等待人工审核"
        ]
    }


# ===== 工作流创建函数 =====

def create_agent_workflow_v2(
    max_reflections: int = 3,
    enable_human_review: bool = True
) -> StateGraph:
    """创建Agent协作工作流v2.0

    工作流程：
    1. outline -> 生成大纲
    2. character -> 生成角色
    3. plot -> 生成情节
    4. review -> 审核内容
    5. 如果审核不通过：
       - meta_scheduler -> 智能修正规划
       - 回到对应Agent重新执行
       - 循环直到通过或达到最大迭代次数
    6. 如果达到最大迭代次数：
       - human_review -> 人工审核（可选）

    Args:
        max_reflections: 最大反思次数
        enable_human_review: 是否启用人工审核

    Returns:
        编译后的工作流
    """
    logger.info(
        f"Creating agent workflow v2.0 (max_reflections={max_reflections}, "
        f"enable_human_review={enable_human_review})"
    )

    # 创建状态图
    workflow = StateGraph(PipelineStateV2)

    # ===== 添加节点 =====
    workflow.add_node("outline", outline_node)
    workflow.add_node("character", character_node)
    workflow.add_node("plot", plot_node)
    workflow.add_node("review", review_node_v2)
    workflow.add_node("meta_scheduler", meta_scheduler_node)

    if enable_human_review:
        workflow.add_node("human_review", human_review_node)

    # ===== 设置入口点 =====
    workflow.set_entry_point("outline")

    # ===== 添加边 =====
    # 基础流程：outline -> character -> plot -> review
    workflow.add_edge("outline", "character")
    workflow.add_edge("character", "plot")
    workflow.add_edge("plot", "review")

    # ===== 添加条件边 =====

    # 1. 审核后的路由
    review_routes = {
        "completed": END,
        "meta_scheduler": "meta_scheduler"
    }

    if enable_human_review:
        review_routes["human_review"] = "human_review"
        # 人工审核后结束
        workflow.add_edge("human_review", END)

    workflow.add_conditional_edges(
        "review",
        review_router,
        review_routes
    )

    # 2. 元调度器的动态路由（回到需要修正的Agent）
    workflow.add_conditional_edges(
        "meta_scheduler",
        meta_scheduler_router,
        {
            "outline": "outline",
            "character": "character",
            "plot": "plot",
            "completed": END,
            "human_review": "human_review" if enable_human_review else END
        }
    )

    # ===== 编译工作流 =====
    app = workflow.compile()

    logger.info("Agent workflow v2.0 created successfully")
    return app


def visualize_workflow_v2(workflow) -> str:
    """可视化工作流（生成Mermaid图）

    Args:
        workflow: 编译后的工作流

    Returns:
        Mermaid图字符串
    """
    try:
        mermaid_str = workflow.get_graph().draw_mermaid()
        logger.info("Workflow visualization generated")
        return mermaid_str
    except Exception as e:
        logger.error(f"Failed to generate workflow visualization: {e}")
        return None


async def execute_agent_workflow_v2(
    task: str,
    user_id: str,
    project_id: str,
    execution_id: str = None,
    max_reflections: int = 3,
    workspace_context: Dict[str, Any] = None,
    enable_human_review: bool = True
) -> Dict[str, Any]:
    """执行Agent协作工作流v2.0

    Args:
        task: 创作任务
        user_id: 用户ID
        project_id: 项目ID
        execution_id: 执行ID（可选）
        max_reflections: 最大反思次数
        workspace_context: 工作区上下文
        enable_human_review: 是否启用人工审核

    Returns:
        最终状态
    """
    from agents.states.pipeline_state_v2 import create_initial_pipeline_state_v2

    # 创建初始状态
    initial_state = create_initial_pipeline_state_v2(
        task=task,
        user_id=user_id,
        project_id=project_id,
        execution_id=execution_id,
        max_reflections=max_reflections,
        workspace_context=workspace_context
    )

    # 创建工作流
    workflow = create_agent_workflow_v2(
        max_reflections=max_reflections,
        enable_human_review=enable_human_review
    )

    # 执行工作流
    logger.info(
        "Executing agent workflow v2.0",
        task=task[:100],
        user_id=user_id,
        project_id=project_id,
        execution_id=initial_state.get("execution_id")
    )

    final_state = await workflow.ainvoke(initial_state)

    # 获取执行摘要
    from agents.states.pipeline_state_v2 import get_execution_summary
    summary = get_execution_summary(final_state)

    logger.info(
        "Agent workflow v2.0 completed",
        summary=summary
    )

    return final_state


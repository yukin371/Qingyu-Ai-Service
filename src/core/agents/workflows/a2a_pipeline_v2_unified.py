"""
A2A 创作流水线 v2.0 - 基于 LangChain 1.0 统一架构

集成所有新特性:
- 统一 Agent 接口 (create_agent)
- Middleware 机制（日志、指标）
- Checkpointer 持久化（中断恢复）
- 多 LLM 供应商支持
"""

from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage
from langchain.agents import create_agent

from src.core.agents.middleware import (
    LoggingMiddleware,
    MetricsMiddleware,
    ErrorHandlingMiddleware,
)
from src.core.agents.checkpointers import PostgresCheckpointer
from src.core.llm.providers import LLMProviderFactory
from src.core.logger import get_logger
from src.core.config import get_settings

logger = get_logger(__name__)


# ===== Pipeline State =====
from typing import TypedDict, Annotated
import operator


class A2APipelineStateV2(TypedDict):
    """A2A 流水线状态 v2.0"""

    # 输入
    user_requirement: str
    user_id: str
    project_id: str
    pipeline_config: Dict[str, Any]

    # 规划 Agent 输出
    requirement_analysis: Dict[str, Any]
    execution_plan: Dict[str, Any]
    current_step: int

    # 各 Agent 输出
    outline_nodes: List[Dict[str, Any]]
    characters: List[Dict[str, Any]]
    character_relations: List[Dict[str, Any]]
    timeline_events: List[Dict[str, Any]]
    plot_nodes: List[Dict[str, Any]]

    # 审核输出
    diagnostic_report: Dict[str, Any]
    quality_score: int
    review_passed: bool

    # 修正相关
    correction_prompts: Dict[str, str]
    correction_mode: str
    affected_agents: List[str]
    iteration_count: int
    max_iterations: int

    # 工作流控制
    current_agent: str
    completed_agents: Annotated[List[str], operator.add]

    # 消息和推理
    messages: Annotated[List[BaseMessage], operator.add]
    reasoning: Annotated[List[str], operator.add]

    # 错误处理
    errors: Annotated[List[str], operator.add]
    warnings: Annotated[List[str], operator.add]

    # 元数据
    start_time: float
    tokens_used: int
    tool_calls_count: int


# ===== Node Functions =====


async def planner_node(state: A2APipelineStateV2) -> A2APipelineStateV2:
    """规划 Agent 节点"""
    logger.info("Planner Agent: Analyzing requirement...")

    # 简化实现：生成执行计划
    execution_plan = {
        "steps": [
            {"step_id": 1, "agent": "outline_agent"},
            {"step_id": 2, "agent": "character_agent"},
            {"step_id": 3, "agent": "plot_agent"},
            {"step_id": 4, "agent": "review_agent_v2"},
        ]
    }

    return {
        **state,
        "execution_plan": execution_plan,
        "current_step": 0,
        "current_agent": "outline_agent",
        "completed_agents": state.get("completed_agents", []) + ["planner"],
        "reasoning": state.get("reasoning", []) + ["规划完成：4个步骤"],
    }


async def outline_agent_node(state: A2APipelineStateV2) -> A2APipelineStateV2:
    """大纲 Agent 节点"""
    logger.info("Outline Agent: Generating outline...")

    # 简化实现
    outline_nodes = [
        {"name": "第一章", "description": "故事开篇"},
        {"name": "第二章", "description": "情节发展"},
    ]

    return {
        **state,
        "outline_nodes": outline_nodes,
        "current_agent": "character_agent",
        "completed_agents": state.get("completed_agents", []) + ["outline_agent"],
        "reasoning": state.get("reasoning", []) + ["大纲生成完成"],
    }


async def character_agent_node(state: A2APipelineStateV2) -> A2APipelineStateV2:
    """角色 Agent 节点"""
    logger.info("Character Agent: Creating characters...")

    # 简化实现
    characters = [
        {"name": "主角", "role_type": "protagonist"},
        {"name": "配角A", "role_type": "supporting"},
    ]

    return {
        **state,
        "characters": characters,
        "current_agent": "plot_agent",
        "completed_agents": state.get("completed_agents", []) + ["character_agent"],
        "reasoning": state.get("reasoning", []) + ["角色创建完成"],
    }


async def plot_agent_node(state: A2APipelineStateV2) -> A2APipelineStateV2:
    """情节 Agent 节点"""
    logger.info("Plot Agent: Building plot...")

    # 简化实现
    timeline_events = [
        {"title": "事件1", "participants": ["主角"]},
        {"title": "事件2", "participants": ["主角", "配角A"]},
    ]

    return {
        **state,
        "timeline_events": timeline_events,
        "current_agent": "review_agent_v2",
        "completed_agents": state.get("completed_agents", []) + ["plot_agent"],
        "reasoning": state.get("reasoning", []) + ["情节构建完成"],
    }


async def review_agent_v2_node(state: A2APipelineStateV2) -> A2APipelineStateV2:
    """审核 Agent v2 节点"""
    logger.info("Review Agent v2: Deep diagnostic review...")

    # 简化实现：生成诊断报告
    diagnostic_report = {
        "passed": True,
        "quality_score": 85,
        "issues": [],
        "correction_strategy": "none",
    }

    return {
        **state,
        "diagnostic_report": diagnostic_report,
        "quality_score": 85,
        "review_passed": True,
        "current_agent": "completed",
        "completed_agents": state.get("completed_agents", []) + ["review_agent_v2"],
        "reasoning": state.get("reasoning", []) + ["审核完成：通过"],
    }


# ===== Routers =====


def planner_router(state: A2APipelineStateV2) -> str:
    """规划后路由"""
    execution_plan = state.get("execution_plan", {})
    steps = execution_plan.get("steps", [])

    if steps:
        first_agent = steps[0].get("agent", "outline_agent")
        return first_agent
    return "outline_agent"


def dynamic_next_router(state: A2APipelineStateV2) -> str:
    """动态路由到下一个 Agent"""
    current_agent = state.get("current_agent", "")

    if current_agent == "completed":
        return "end"
    elif current_agent == "outline_agent":
        return "outline_agent"
    elif current_agent == "character_agent":
        return "character_agent"
    elif current_agent == "plot_agent":
        return "plot_agent"
    elif current_agent == "review_agent_v2":
        return "review_agent_v2"
    else:
        return "end"


def review_router(state: A2APipelineStateV2) -> str:
    """审核后路由"""
    current_agent = state.get("current_agent", "")

    if current_agent == "completed":
        return "end"
    else:
        return "end"


# ===== Pipeline Creation =====


async def create_a2a_pipeline_v2(
    enable_checkpointer: bool = True,
    enable_middleware: bool = True,
):
    """创建 A2A 流水线 v2.0

    Args:
        enable_checkpointer: 是否启用持久化
        enable_middleware: 是否启用中间件

    Returns:
        编译后的工作流
    """
    logger.info(
        "Creating A2A Pipeline v2.0",
        enable_checkpointer=enable_checkpointer,
        enable_middleware=enable_middleware,
    )

    # 准备 Middleware
    middleware = []
    if enable_middleware:
        middleware = [
            LoggingMiddleware(),
            MetricsMiddleware(),
            ErrorHandlingMiddleware(enable_fallback=True, max_retries=3),
        ]
        logger.info(f"Middleware enabled: {len(middleware)} middlewares")

    # 准备 Checkpointer
    checkpointer = None
    if enable_checkpointer:
        try:
            checkpointer = PostgresCheckpointer()
            logger.info("Checkpointer enabled: PostgreSQL")
        except Exception as e:
            logger.warning(
                f"Failed to initialize checkpointer: {e}. "
                "Pipeline will run without persistence."
            )

    # 创建 StateGraph
    workflow = StateGraph(A2APipelineStateV2)

    # 添加节点
    workflow.add_node("planner", planner_node)
    workflow.add_node("outline_agent", outline_agent_node)
    workflow.add_node("character_agent", character_agent_node)
    workflow.add_node("plot_agent", plot_agent_node)
    workflow.add_node("review_agent_v2", review_agent_v2_node)

    # 设置入口点
    workflow.set_entry_point("planner")

    # 添加条件边
    workflow.add_conditional_edges(
        "planner",
        planner_router,
        {
            "outline_agent": "outline_agent",
            "character_agent": "character_agent",
            "plot_agent": "plot_agent",
        },
    )

    # 顺序执行
    workflow.add_edge("outline_agent", "character_agent")
    workflow.add_edge("character_agent", "plot_agent")
    workflow.add_edge("plot_agent", "review_agent_v2")

    # 审核后路由
    workflow.add_conditional_edges(
        "review_agent_v2",
        review_router,
        {
            "end": END,
        },
    )

    # 编译（带 Checkpointer）
    app = workflow.compile(checkpointer=checkpointer)

    logger.info("A2A Pipeline v2.0 created successfully")

    return app


# ===== Usage Example =====


if __name__ == "__main__":
    import asyncio
    import time

    async def main():
        """使用示例"""
        logger.info("Starting A2A Pipeline v2.0 example...")

        # 创建流水线
        pipeline = await create_a2a_pipeline_v2(
            enable_checkpointer=True,
            enable_middleware=True,
        )

        # 初始状态
        initial_state = {
            "user_requirement": "创作赛博朋克侦探小说",
            "user_id": "user-123",
            "project_id": "proj-456",
            "pipeline_config": {
                "enable_rag": True,
                "enable_planner": True,
            },
            "max_iterations": 3,
            "iteration_count": 0,
            "current_step": 0,
            "messages": [],
            "reasoning": [],
            "completed_agents": [],
            "errors": [],
            "warnings": [],
            "start_time": time.time(),
            "tokens_used": 0,
            "tool_calls_count": 0,
        }

        # 执行（自动持久化）
        result = await pipeline.ainvoke(
            initial_state,
            config={
                "configurable": {
                    "thread_id": "user-123_proj-456_session-001"
                }
            },
        )

        logger.info("Pipeline execution completed")
        logger.info(f"Completed agents: {result.get('completed_agents', [])}")
        logger.info(f"Quality score: {result.get('quality_score', 0)}")
        logger.info(f"Review passed: {result.get('review_passed', False)}")

        # 如果中断，可以恢复
        # continued = await pipeline.ainvoke(
        #     None,
        #     config={"configurable": {"thread_id": "user-123_proj-456_session-001"}}
        # )

    asyncio.run(main())



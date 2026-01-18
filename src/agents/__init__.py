"""Agents模块

提供Agent实现和工作流
"""

# 新版本Agent (v2.0)
from src.agents.base_agent import BaseAgent
from src.agents.review import ReviewAgentV2

# 旧版本（暂时保留，但不导入有问题的模块）
# from .nodes import (
#     finalize_node,
#     generation_node,
#     rag_retrieval_node,
#     review_node,
#     understand_task_node,
# )
# from .states import BaseAgentState, CreativeAgentState, create_initial_creative_state
# from .workflows import create_creative_workflow, execute_creative_workflow

__all__ = [
    # v2.0 Agents
    "BaseAgent",
    "ReviewAgentV2",
    # States (v2.0)
    # "BaseAgentState",
    # "CreativeAgentState",
    # "create_initial_creative_state",
    # Nodes (v1.0 - deprecated)
    # "understand_task_node",
    # "rag_retrieval_node",
    # "generation_node",
    # "review_node",
    # "finalize_node",
    # Workflows (v1.0 - deprecated)
    # "create_creative_workflow",
    # "execute_creative_workflow",
]

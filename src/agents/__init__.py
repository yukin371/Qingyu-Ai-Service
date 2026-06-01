"""Agents模块

提供Agent实现和工作流

v2.0版本统一使用BaseAgentV2作为基类
"""

# v2.0 Agent基类（主版本）
from src.agents.base_agent import BaseAgentV2

# 专业Agent
from src.agents.review import ReviewAgentV2

# 兼容性别名：BaseAgent -> BaseAgentV2
BaseAgent = BaseAgentV2

__all__ = [
    # v2.0 Agent基类
    "BaseAgentV2",
    "BaseAgent",  # 兼容性别名
    # 专业Agent
    "ReviewAgentV2",
]

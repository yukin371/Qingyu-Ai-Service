"""
BaseAgentV2 - 简化的Agent基类（v2.0）

专为Phase 3 Agent系统设计的轻量级基类：
1. 只有两个抽象方法：execute和get_runnable
2. 不强制要求特定的内部实现
3. 专注于统一接口，而非实现细节
"""
from abc import ABC, abstractmethod
from typing import Optional

from langchain_core.runnables import Runnable

from src.agents.states.pipeline_state_v2 import PipelineStateV2
from src.core.logger import get_logger

logger = get_logger(__name__)


class BaseAgentV2(ABC):
    """Agent基类 v2.0

    所有v2.0 Agent的抽象基类，提供通用接口和核心功能。

    特点：
    - 简化设计，只定义必要的接口
    - 不强制内部实现细节
    - 专注于PipelineStateV2状态管理
    """

    def __init__(self, name: str, description: str, version: str = "v1.0"):
        """初始化Agent

        Args:
            name: Agent名称
            description: Agent描述
            version: Agent版本
        """
        self.name = name
        self.description = description
        self.version = version
        logger.info(f"Agent initialized: {self.name} (v{self.version})")

    @abstractmethod
    def get_runnable(self) -> Runnable[PipelineStateV2, PipelineStateV2]:
        """获取Agent的可执行链（LangChain Runnable）

        Returns:
            Runnable: LangChain可执行链
        """
        pass

    @abstractmethod
    async def execute(self, state: PipelineStateV2) -> PipelineStateV2:
        """执行Agent的核心逻辑

        Args:
            state: 流水线状态

        Returns:
            PipelineStateV2: 更新后的状态
        """
        pass

    def get_name(self) -> str:
        """获取Agent名称"""
        return self.name

    def get_description(self) -> str:
        """获取Agent描述"""
        return self.description

    def get_version(self) -> str:
        """获取Agent版本"""
        return self.version

    def __repr__(self) -> str:
        return f"<{self.name}Agent v{self.version}>"

    def __str__(self) -> str:
        return self.get_name()







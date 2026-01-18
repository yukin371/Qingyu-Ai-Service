"""
统一 Agent 基类 - 基于 LangChain 1.0 create_agent() 接口

这是 LangChain 1.0 重构后的统一 Agent 基类，所有 Agent 应继承此类。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncGenerator
from langchain_core.runnables import RunnableConfig, Runnable
from langchain_core.messages import BaseMessage
from langchain_core.language_models import BaseChatModel

try:
    from langchain.agents import create_agent
    LANGCHAIN_1_0_AVAILABLE = True
except ImportError:
    LANGCHAIN_1_0_AVAILABLE = False
    # 为了兼容性，定义一个占位符
    def create_agent(*args, **kwargs):
        raise NotImplementedError("LangChain 1.0 create_agent not available")

from src.core.logger import get_logger

logger = get_logger(__name__)


class BaseAgentUnified(ABC):
    """统一 Agent 基类 - 基于 LangChain 1.0 create_agent() 接口

    所有 Agent 应继承此类，并实现必要的抽象方法。

    主要特性：
    - 使用 LangChain 1.0 统一的 create_agent() 接口
    - 支持 Middleware 机制
    - 支持 Checkpointer 持久化
    - 统一的执行和流式接口
    """

    def __init__(
        self,
        agent_name: str,
        llm: BaseChatModel,
        tools: List = None,
        agent_type: str = "react",
        checkpointer=None,
        middleware: List = None,
        **kwargs
    ):
        """初始化 Agent

        Args:
            agent_name: Agent 名称
            llm: LLM 实例
            tools: 工具列表
            agent_type: Agent 类型（react, openai-tools, xml, structured-chat）
            checkpointer: Checkpointer 实例（可选）
            middleware: Middleware 列表（可选）
            **kwargs: 额外参数
        """
        if not LANGCHAIN_1_0_AVAILABLE:
            raise ImportError(
                "LangChain 1.0 is required. "
                "Please upgrade: pip install langchain>=1.0.0"
            )

        self.agent_name = agent_name
        self.llm = llm
        self.tools = tools or []
        self.agent_type = agent_type
        self.checkpointer = checkpointer
        self.middleware = middleware or []
        self.extra_params = kwargs

        # 使用 create_agent 创建 Agent
        self._agent = self._create_agent()

        logger.info(
            f"Agent initialized",
            agent_name=agent_name,
            agent_type=agent_type,
            tools_count=len(self.tools),
            middleware_count=len(self.middleware),
            has_checkpointer=checkpointer is not None,
        )

    def _create_agent(self) -> Runnable:
        """使用 LangChain 1.0 create_agent() 创建 Agent

        Returns:
            Runnable: LangChain Agent 实例
        """
        try:
            agent = create_agent(
                llm=self.llm,
                tools=self.tools,
                agent_type=self.agent_type,
                checkpointer=self.checkpointer,
                middleware=self.middleware,
                **self.extra_params
            )

            logger.info(f"Agent created successfully: {self.agent_name}")
            return agent

        except Exception as e:
            logger.error(
                f"Failed to create agent",
                agent_name=self.agent_name,
                error=str(e),
            )
            raise

    @property
    def agent(self) -> Runnable:
        """获取 Agent 实例"""
        return self._agent

    async def execute(
        self,
        input_data: Dict[str, Any],
        config: Optional[RunnableConfig] = None,
    ) -> Dict[str, Any]:
        """执行 Agent（同步返回完整结果）

        Args:
            input_data: 输入数据
            config: 运行配置（可选）

        Returns:
            Dict[str, Any]: 执行结果
        """
        # 准备配置
        if config is None:
            config = {}

        # 添加 agent_name 到配置
        if "configurable" not in config:
            config["configurable"] = {}
        config["configurable"]["agent_name"] = self.agent_name

        try:
            logger.info(f"Executing agent: {self.agent_name}")

            # 调用 Agent
            result = await self._agent.ainvoke(input_data, config=config)

            logger.info(
                f"Agent execution completed",
                agent_name=self.agent_name,
            )

            return result

        except Exception as e:
            logger.error(
                f"Agent execution failed",
                agent_name=self.agent_name,
                error=str(e),
                exc_info=True,
            )
            raise

    async def stream(
        self,
        input_data: Dict[str, Any],
        config: Optional[RunnableConfig] = None,
    ) -> AsyncGenerator[Any, None]:
        """流式执行 Agent

        Args:
            input_data: 输入数据
            config: 运行配置（可选）

        Yields:
            Any: 流式输出
        """
        # 准备配置
        if config is None:
            config = {}

        if "configurable" not in config:
            config["configurable"] = {}
        config["configurable"]["agent_name"] = self.agent_name

        try:
            logger.info(f"Starting stream execution: {self.agent_name}")

            # 流式调用 Agent
            async for chunk in self._agent.astream(input_data, config=config):
                yield chunk

            logger.info(f"Stream execution completed: {self.agent_name}")

        except Exception as e:
            logger.error(
                f"Stream execution failed",
                agent_name=self.agent_name,
                error=str(e),
            )
            raise

    async def resume(
        self,
        thread_id: str,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """从 Checkpoint 恢复执行

        Args:
            thread_id: 线程 ID
            input_data: 输入数据（可选，None 表示从 checkpoint 恢复）

        Returns:
            Dict[str, Any]: 执行结果
        """
        if not self.checkpointer:
            raise ValueError("Checkpointer is not enabled for this agent")

        config = {
            "configurable": {
                "thread_id": thread_id,
                "agent_name": self.agent_name,
            }
        }

        logger.info(
            f"Resuming agent from checkpoint",
            agent_name=self.agent_name,
            thread_id=thread_id,
        )

        return await self.execute(input_data, config=config)

    @abstractmethod
    def get_agent_name(self) -> str:
        """获取 Agent 名称

        子类必须实现此方法
        """
        pass

    @abstractmethod
    def get_agent_description(self) -> str:
        """获取 Agent 描述

        子类必须实现此方法
        """
        pass

    def get_agent_type(self) -> str:
        """获取 Agent 类型"""
        return self.agent_type

    def get_tools(self) -> List:
        """获取工具列表"""
        return self.tools

    def add_tool(self, tool) -> None:
        """添加工具

        注意：添加工具后需要重新创建 Agent
        """
        self.tools.append(tool)
        self._agent = self._create_agent()
        logger.info(f"Tool added to agent: {self.agent_name}")

    def add_middleware(self, middleware) -> None:
        """添加 Middleware

        注意：添加 Middleware 后需要重新创建 Agent
        """
        self.middleware.append(middleware)
        self._agent = self._create_agent()
        logger.info(f"Middleware added to agent: {self.agent_name}")

    def health_check(self) -> bool:
        """健康检查

        Returns:
            bool: 健康状态
        """
        try:
            # 检查 LLM 是否可用
            if self.llm is None:
                return False

            # 检查 Checkpointer（如果启用）
            if self.checkpointer:
                # 可以添加 checkpointer 健康检查
                pass

            return True

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}("
            f"name={self.agent_name}, "
            f"type={self.agent_type}, "
            f"tools={len(self.tools)}, "
            f"middleware={len(self.middleware)}"
            f")>"
        )



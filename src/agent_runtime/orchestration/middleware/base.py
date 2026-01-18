"""
Middleware Base Classes - 中间件基类系统

实现洋葱模型的中间件系统，用于处理 Agent 执行过程中的横切关注点。

设计原则:
- 洋葱模型: request 进 → middleware 1 → middleware 2 → handler
                       response ← middleware 1 ← middleware 2 ← handler
- 可组合: 中间件可以组合成管道
- 可排序: 支持按 order 排序
- 可禁用: 支持运行时禁用中间件
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from src.common.types.agent_types import AgentContext, AgentResult


logger = logging.getLogger(__name__)


# =============================================================================
# Middleware Context
# =============================================================================

class MiddlewareContext:
    """
    中间件上下文

    在中间件链中传递的上下文对象，包含请求和响应数据。

    Attributes:
        agent_context: Agent 执行上下文
        request_data: 请求数据键值对存储
        response_data: 响应数据
        metadata: 中间件元数据
    """

    def __init__(
        self,
        agent_context: AgentContext,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化中间件上下文

        Args:
            agent_context: Agent 上下文
            metadata: 元数据
        """
        self.agent_context = agent_context
        self.request_data: Dict[str, Any] = {}
        self.response_data: Any = None
        self.metadata: Dict[str, Any] = metadata or {}

    def set(self, key: str, value: Any) -> None:
        """设置请求数据"""
        self.request_data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """获取请求数据"""
        return self.request_data.get(key, default)

    def set_response(self, data: Any) -> None:
        """设置响应数据"""
        self.response_data = data

    def has_response(self) -> bool:
        """检查是否有响应数据"""
        return self.response_data is not None


# =============================================================================
# Middleware Result
# =============================================================================

class MiddlewareResult(BaseModel):
    """
    中间件处理结果

    Attributes:
        success: 是否成功
        agent_result: Agent 执行结果（仅当成功时）
        error: 错误信息（仅当失败时）
        metadata: 额外的元数据
    """

    success: bool = Field(..., description="Whether processing succeeded")
    agent_result: Optional[AgentResult] = Field(
        default=None,
        description="Agent execution result"
    )
    error: Optional[str] = Field(default=None, description="Error message")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# =============================================================================
# Agent Middleware Base Class
# =============================================================================

class AgentMiddleware(ABC):
    """
    Agent 中间件抽象基类

    所有中间件必须继承此类并实现 process 方法。

    中间件执行顺序（洋葱模型）:
        1. Middleware1.before
        2. Middleware2.before
        3. Handler (Agent执行)
        4. Middleware2.after
        5. Middleware1.after

    使用示例:
        ```python
        class AuthMiddleware(AgentMiddleware):
            def __init__(self):
                super().__init__(name="auth", order=10)

            async def process(
                self,
                context: AgentContext,
                next_call: Callable
            ) -> MiddlewareResult:
                # 前置处理
                if not is_authenticated(context):
                    return MiddlewareResult(
                        success=False,
                        error="Not authenticated"
                    )

                # 调用下一个中间件或处理器
                result = await next_call()

                # 后置处理
                return result
        ```
    """

    def __init__(
        self,
        name: str,
        order: int = 100,
        enabled: bool = True,
    ):
        """
        初始化中间件

        Args:
            name: 中间件名称（必须唯一）
            order: 执行顺序（数字越小越先执行）
            enabled: 是否启用
        """
        self.name = name
        self.order = order
        self.enabled = enabled

    @abstractmethod
    async def process(
        self,
        context: AgentContext,
        next_call: Callable[[], Awaitable[MiddlewareResult]],
    ) -> MiddlewareResult:
        """
        处理请求

        Args:
            context: Agent 上下文
            next_call: 下一个中间件或处理器的调用函数

        Returns:
            MiddlewareResult 处理结果

        Raises:
            NotImplementedError: 子类必须实现此方法
        """
        raise NotImplementedError("Middleware must implement process method")

    def enable(self) -> None:
        """启用中间件"""
        self.enabled = True
        logger.debug(f"Middleware {self.name} enabled")

    def disable(self) -> None:
        """禁用中间件"""
        self.enabled = False
        logger.debug(f"Middleware {self.name} disabled")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, order={self.order}, enabled={self.enabled})"


# =============================================================================
# Middleware Pipeline
# =============================================================================

class MiddlewarePipeline:
    """
    中间件管道

    管理和执行中间件链，按照洋葱模型处理请求。

    使用示例:
        ```python
        # 创建中间件
        auth = AuthMiddleware()
        logging = LoggingMiddleware()

        # 创建管道
        pipeline = MiddlewarePipeline()
        pipeline.add(auth)
        pipeline.add(logging)

        # 执行
        result = await pipeline.execute(
            context=agent_context,
            handler=agent_handler,
        )
        ```
    """

    def __init__(self, middlewares: Optional[List[AgentMiddleware]] = None):
        """
        初始化管道

        Args:
            middlewares: 初始中间件列表
        """
        self._middlewares: List[AgentMiddleware] = middlewares or []

    @property
    def middlewares(self) -> List[AgentMiddleware]:
        """
        获取排序后的中间件列表

        Returns:
            按 order 排序的中间件列表（仅包含已启用的）
        """
        # 过滤已启用的中间件并按 order 排序
        enabled = [m for m in self._middlewares if m.enabled]
        return sorted(enabled, key=lambda m: m.order)

    def add(self, middleware: AgentMiddleware) -> None:
        """
        添加中间件

        Args:
            middleware: 中间件实例
        """
        # 检查名称是否已存在
        if any(m.name == middleware.name for m in self._middlewares):
            logger.warning(f"Middleware {middleware.name} already exists, replacing")

        self._middlewares.append(middleware)
        logger.info(f"Added middleware: {middleware.name}")

    def remove(self, name: str) -> bool:
        """
        移除中间件

        Args:
            name: 中间件名称

        Returns:
            是否成功移除
        """
        for i, m in enumerate(self._middlewares):
            if m.name == name:
                del self._middlewares[i]
                logger.info(f"Removed middleware: {name}")
                return True

        logger.warning(f"Middleware not found: {name}")
        return False

    def get(self, name: str) -> Optional[AgentMiddleware]:
        """
        获取中间件

        Args:
            name: 中间件名称

        Returns:
            中间件实例或 None
        """
        for m in self._middlewares:
            if m.name == name:
                return m
        return None

    def enable(self, name: str) -> bool:
        """
        启用中间件

        Args:
            name: 中间件名称

        Returns:
            是否成功
        """
        middleware = self.get(name)
        if middleware:
            middleware.enable()
            return True
        return False

    def disable(self, name: str) -> bool:
        """
        禁用中间件

        Args:
            name: 中间件名称

        Returns:
            是否成功
        """
        middleware = self.get(name)
        if middleware:
            middleware.disable()
            return True
        return False

    async def execute(
        self,
        context: AgentContext,
        handler: Callable[[AgentContext], Awaitable[MiddlewareResult]],
    ) -> MiddlewareResult:
        """
        执行中间件管道

        按照洋葱模型执行中间件链。

        Args:
            context: Agent 上下文
            handler: 最终处理函数（Agent 执行器）

        Returns:
            MiddlewareResult 处理结果

        Raises:
            Exception: 如果处理过程中抛出异常
        """
        middlewares = self.middlewares

        # 构建中间件链
        async def execute_chain(index: int = 0) -> MiddlewareResult:
            """
            递归执行中间件链

            Args:
                index: 当前中间件索引
            """
            # 如果所有中间件都执行完毕，调用 handler
            if index >= len(middlewares):
                logger.debug("All middleware executed, calling handler")
                return await handler(context)

            # 获取当前中间件
            middleware = middlewares[index]

            # 定义下一个调用
            async def next_call() -> MiddlewareResult:
                return await execute_chain(index + 1)

            # 执行当前中间件
            logger.debug(f"Executing middleware: {middleware.name}")
            return await middleware.process(context, next_call)

        # 开始执行链
        try:
            result = await execute_chain(0)
            logger.info(f"Pipeline execution completed: success={result.success}")
            return result

        except Exception as e:
            logger.error(f"Pipeline execution error: {e}")
            raise

    def __len__(self) -> int:
        """返回中间件数量"""
        return len(self._middlewares)

    def __repr__(self) -> str:
        enabled_count = len([m for m in self._middlewares if m.enabled])
        return f"MiddlewarePipeline(middlewares={len(self._middlewares)}, enabled={enabled_count})"


# =============================================================================
# Convenience Functions
# =============================================================================

async def execute_with_middleware(
    context: AgentContext,
    handler: Callable[[AgentContext], Awaitable[MiddlewareResult]],
    middlewares: List[AgentMiddleware],
) -> MiddlewareResult:
    """
    使用中间件执行处理器的快捷函数

    Args:
        context: Agent 上下文
        handler: 处理函数
        middlewares: 中间件列表

    Returns:
        MiddlewareResult 处理结果
    """
    pipeline = MiddlewarePipeline(middlewares=middlewares)
    return await pipeline.execute(context, handler)

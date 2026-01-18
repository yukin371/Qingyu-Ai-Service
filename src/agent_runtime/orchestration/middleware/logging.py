"""
Logging Middleware - 日志中间件

记录 Agent 执行过程中的请求和响应信息。
"""

import logging
import time
from typing import Any, Awaitable, Callable, Dict

from src.agent_runtime.orchestration.middleware.base import (
    AgentMiddleware,
    MiddlewareResult,
)
from src.common.types.agent_types import AgentContext


logger = logging.getLogger(__name__)


class LoggingMiddleware(AgentMiddleware):
    """
    日志中间件

    记录请求、响应和执行时间。

    Attributes:
        log_level: 日志级别
        log_body: 是否记录请求/响应体
        log_execution_time: 是否记录执行时间
    """

    def __init__(
        self,
        log_level: int = logging.INFO,
        log_body: bool = False,
        log_execution_time: bool = True,
    ):
        """
        初始化日志中间件

        Args:
            log_level: 日志级别
            log_body: 是否记录请求/响应体
            log_execution_time: 是否记录执行时间
        """
        super().__init__(name="logging", order=100)
        self.log_level = log_level
        self.log_body = log_body
        self.log_execution_time = log_execution_time

    async def process(
        self,
        context: AgentContext,
        next_call: Callable[[], Awaitable[MiddlewareResult]],
    ) -> MiddlewareResult:
        """
        处理日志记录

        Args:
            context: Agent 上下文
            next_call: 下一个中间件或处理器

        Returns:
            MiddlewareResult 处理结果
        """
        start_time = time.time()

        # 记录请求
        self._log_request(context)

        # 执行下一个中间件
        result = await next_call()

        # 计算执行时间
        execution_time = time.time() - start_time

        # 记录响应
        self._log_response(context, result, execution_time)

        return result

    def _log_request(self, context: AgentContext) -> None:
        """记录请求信息"""
        log_data = {
            "agent_id": context.agent_id,
            "user_id": context.user_id,
            "session_id": context.session_id,
            "task": context.current_task,
        }

        log_message = f"Agent request: {context.agent_id}"
        if self.log_body:
            log_data["conversation_length"] = len(context.conversation_history)
            log_data["variables"] = context.variables

        logger.log(self.log_level, log_message, extra=log_data)

    def _log_response(
        self,
        context: AgentContext,
        result: MiddlewareResult,
        execution_time: float,
    ) -> None:
        """记录响应信息"""
        log_data = {
            "agent_id": context.agent_id,
            "user_id": context.user_id,
            "success": result.success,
        }

        log_message = f"Agent response: {context.agent_id} - {'SUCCESS' if result.success else 'FAILED'}"

        if self.log_execution_time:
            log_data["execution_time_seconds"] = execution_time
            log_message += f" ({execution_time:.3f}s)"

        if self.log_body and result.agent_result:
            log_data["output_length"] = len(result.agent_result.output or "")
            log_data["tokens_used"] = result.agent_result.tokens_used

        if result.error:
            log_data["error"] = result.error

        logger.log(self.log_level, log_message, extra=log_data)

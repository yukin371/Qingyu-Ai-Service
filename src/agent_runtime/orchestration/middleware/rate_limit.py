"""
Rate Limiting Middleware - 限流中间件

提供基于用户或 IP 的请求速率限制。
"""

import asyncio
import logging
import time
from typing import Awaitable, Callable, Dict, Optional, Tuple
from collections import deque

from src.agent_runtime.orchestration.middleware.base import (
    AgentMiddleware,
    MiddlewareResult,
)
from src.common.types.agent_types import AgentContext


logger = logging.getLogger(__name__)


class RateLimitMiddleware(AgentMiddleware):
    """
    限流中间件

    使用滑动窗口算法实现速率限制。

    Attributes:
        requests_per_window: 时间窗口内的请求数限制
        window_size: 时间窗口大小（秒）
        user_limits: 用户特定的限制
        request_history: 请求历史记录
    """

    def __init__(
        self,
        requests_per_window: int = 60,
        window_size: int = 60,
        user_limits: Optional[Dict[str, int]] = None,
    ):
        """
        初始化限流中间件

        Args:
            requests_per_window: 时间窗口内的请求数限制
            window_size: 时间窗口大小（秒）
            user_limits: 用户特定的限制 (user_id -> requests_per_window)
        """
        super().__init__(name="rate_limit", order=20)
        self.requests_per_window = requests_per_window
        self.window_size = window_size
        self.user_limits = user_limits or {}
        self.request_history: Dict[str, deque] = {}
        self._lock = asyncio.Lock()

    async def process(
        self,
        context: AgentContext,
        next_call: Callable[[], Awaitable[MiddlewareResult]],
    ) -> MiddlewareResult:
        """
        处理请求，检查速率限制

        Args:
            context: Agent 上下文
            next_call: 下一个中间件或处理器

        Returns:
            MiddlewareResult 处理结果
        """
        # 获取限制
        limit = self.user_limits.get(context.user_id, self.requests_per_window)

        # 检查是否超过限制
        async with self._lock:
            if not self._check_rate_limit(context.user_id, limit):
                logger.warning(
                    f"Rate limit exceeded: user={context.user_id}, "
                    f"limit={limit}/window"
                )
                return MiddlewareResult(
                    success=False,
                    error="Rate limit exceeded. Please try again later.",
                )

            # 记录请求
            self._record_request(context.user_id)

        # 执行下一个中间件
        return await next_call()

    def _check_rate_limit(self, user_id: str, limit: int) -> bool:
        """
        检查是否超过速率限制

        Args:
            user_id: 用户 ID
            limit: 限制数量

        Returns:
            是否允许请求
        """
        now = time.time()
        window_start = now - self.window_size

        # 获取用户请求历史
        if user_id not in self.request_history:
            self.request_history[user_id] = deque()

        history = self.request_history[user_id]

        # 移除窗口外的记录
        while history and history[0] < window_start:
            history.popleft()

        # 检查是否超过限制
        return len(history) < limit

    def _record_request(self, user_id: str) -> None:
        """
        记录请求

        Args:
            user_id: 用户 ID
        """
        now = time.time()
        if user_id not in self.request_history:
            self.request_history[user_id] = deque()

        self.request_history[user_id].append(now)

    def get_user_request_count(self, user_id: str) -> int:
        """
        获取用户当前窗口内的请求数

        Args:
            user_id: 用户 ID

        Returns:
            当前窗口内的请求数
        """
        if user_id not in self.request_history:
            return 0

        now = time.time()
        window_start = now - self.window_size
        history = self.request_history[user_id]

        # 计算窗口内的请求数
        count = 0
        for timestamp in history:
            if timestamp >= window_start:
                count += 1

        return count

    def clear_user_history(self, user_id: str) -> None:
        """
        清除用户请求历史

        Args:
            user_id: 用户 ID
        """
        if user_id in self.request_history:
            del self.request_history[user_id]
            logger.info(f"Cleared rate limit history for user: {user_id}")

    def set_user_limit(self, user_id: str, limit: int) -> None:
        """
        设置用户特定的限制

        Args:
            user_id: 用户 ID
            limit: 请求数限制
        """
        self.user_limits[user_id] = limit
        logger.info(f"Set rate limit for user {user_id}: {limit}/window")

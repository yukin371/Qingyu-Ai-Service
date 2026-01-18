"""
Cost Tracking Middleware - 成本追踪中间件

追踪 Agent 执行的 Token 使用量和成本。
"""

import logging
from typing import Awaitable, Callable, Dict, Optional, Tuple

from src.agent_runtime.orchestration.middleware.base import (
    AgentMiddleware,
    MiddlewareResult,
)
from src.common.types.agent_types import AgentContext


logger = logging.getLogger(__name__)


class CostTrackingMiddleware(AgentMiddleware):
    """
    成本追踪中间件

    记录 Agent 执行的 Token 使用量和计算成本。

    Attributes:
        token_prices: Token 价格映射 (model -> (prompt_price, completion_price))
        user_quotas: 用户配额映射 (user_id -> token_limit)
        user_usage: 用户使用量映射 (user_id -> tokens_used)
    """

    # 默认 Token 价格（每 1K tokens 的美元价格）
    DEFAULT_PRICES = {
        "gpt-4": (0.03, 0.06),
        "gpt-4-turbo": (0.01, 0.03),
        "gpt-3.5-turbo": (0.0005, 0.0015),
        "claude-3-opus": (0.015, 0.075),
        "claude-3-sonnet": (0.003, 0.015),
    }

    def __init__(
        self,
        token_prices: Optional[Dict[str, tuple]] = None,
        user_quotas: Optional[Dict[str, int]] = None,
    ):
        """
        初始化成本追踪中间件

        Args:
            token_prices: Token 价格映射
            user_quotas: 用户配额
        """
        super().__init__(name="cost_tracking", order=50)
        self.token_prices = token_prices or self.DEFAULT_PRICES.copy()
        self.user_quotas = user_quotas or {}
        self.user_usage: Dict[str, int] = {}

    async def process(
        self,
        context: AgentContext,
        next_call: Callable[[], Awaitable[MiddlewareResult]],
    ) -> MiddlewareResult:
        """
        处理请求，追踪 Token 使用和成本

        Args:
            context: Agent 上下文
            next_call: 下一个中间件或处理器

        Returns:
            MiddlewareResult 处理结果
        """
        # 检查用户配额
        if context.user_id in self.user_quotas:
            quota = self.user_quotas[context.user_id]
            used = self.user_usage.get(context.user_id, 0)

            if used >= quota:
                logger.warning(
                    f"User quota exceeded: {context.user_id}, "
                    f"used={used}, quota={quota}"
                )
                return MiddlewareResult(
                    success=False,
                    error=f"Token quota exceeded: {used}/{quota}",
                )

        # 执行下一个中间件
        result = await next_call()

        # 追踪 Token 使用
        if result.success and result.agent_result:
            tokens_used = result.agent_result.tokens_used
            if tokens_used:
                self._track_usage(context.user_id, tokens_used)
                cost = self._calculate_cost(context.agent_id, tokens_used)

                # 记录成本信息
                logger.info(
                    f"Cost tracking: user={context.user_id}, "
                    f"tokens={tokens_used.get('total', 0)}, "
                    f"cost=${cost:.4f}"
                )

                # 添加到结果元数据
                result.metadata["cost"] = cost
                result.metadata["tokens_used"] = tokens_used

        return result

    def _track_usage(self, user_id: str, tokens_used: Dict[str, int]) -> None:
        """追踪用户使用量"""
        total = tokens_used.get("total", 0)
        self.user_usage[user_id] = self.user_usage.get(user_id, 0) + total

    def _calculate_cost(self, model: str, tokens_used: Dict[str, int]) -> float:
        """计算成本"""
        # 从 model 名称提取基础模型
        base_model = model.split("-")[0] + "-" + model.split("-")[1] if "-" in model else model

        prices = self.token_prices.get(base_model, self.token_prices.get("gpt-3.5-turbo", (0.0005, 0.0015)))
        prompt_price, completion_price = prices

        prompt_tokens = tokens_used.get("prompt", 0)
        completion_tokens = tokens_used.get("completion", 0)

        # 计算成本（价格是每 1K tokens）
        prompt_cost = (prompt_tokens / 1000) * prompt_price
        completion_cost = (completion_tokens / 1000) * completion_price

        return prompt_cost + completion_cost

    def get_user_usage(self, user_id: str) -> int:
        """获取用户使用量"""
        return self.user_usage.get(user_id, 0)

    def reset_user_usage(self, user_id: str) -> None:
        """重置用户使用量"""
        if user_id in self.user_usage:
            del self.user_usage[user_id]
            logger.info(f"Reset usage for user: {user_id}")

    def set_user_quota(self, user_id: str, quota: int) -> None:
        """设置用户配额"""
        self.user_quotas[user_id] = quota
        logger.info(f"Set quota for user {user_id}: {quota} tokens")

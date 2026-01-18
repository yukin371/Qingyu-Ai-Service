"""
Middleware Pipeline - 中间件管道

实现洋葱模型的中间件管道，用于处理 Agent 执行的横切关注点。
"""

from .base import (
    AgentMiddleware,
    MiddlewareContext,
    MiddlewarePipeline,
    MiddlewareResult,
    execute_with_middleware,
)

__all__ = [
    "AgentMiddleware",
    "MiddlewareContext",
    "MiddlewarePipeline",
    "MiddlewareResult",
    "execute_with_middleware",
]

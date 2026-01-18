"""
Agent Runtime Layer - 运行时集成层

这个模块提供了 Agent 的统一执行环境，整合了 Memory、Tools、Workflows 三大模块。

核心组件:
- AgentFactory: Agent 工厂，组装各模块
- AgentCallbackHandler: 全局回调处理
- SessionManager: 会话管理（Redis）
- AgentExecutor: 统一执行器
- Middleware: 中间件管道（认证、成本追踪、日志、限流）
- EventBus: 事件驱动架构
- Monitoring: 监控和成本追踪

架构:
    用户请求 → 认证中间件 → 限流中间件 → 成本追踪中间件 → 日志中间件 → Agent执行器
                    ↓                                                              ↓
                SessionManager                                              CallbackHandler
                    ↓                                                              ↓
                Redis 存储                                                    LangSmith 日志
"""

__version__ = "1.2.0"

from .factory import AgentFactory, AgentTemplate

# TODO: Import other modules as they are implemented
# from .callback_handler import AgentCallbackHandler
# from .session_manager import SessionManager, Session
# from .orchestration.executor import AgentExecutor
# from .orchestration.middleware.base import AgentMiddleware
# from .orchestration.middleware.auth import AuthMiddleware
# from .orchestration.middleware.cost import CostTrackingMiddleware
# from .orchestration.middleware.logging import LoggingMiddleware
# from .orchestration.middleware.rate_limit import RateLimitMiddleware
# from .event_bus.consumer import EventBusConsumer
# from .event_bus.trigger_handler import TriggerHandler
# from .monitoring.metrics import MetricsCollector
# from .monitoring.cost_tracker import CostTracker

__all__ = [
    "AgentFactory",
    "AgentTemplate",
    # "AgentCallbackHandler",
    # "SessionManager",
    # "Session",
    # "AgentExecutor",
    # "AgentMiddleware",
    # "AuthMiddleware",
    # "CostTrackingMiddleware",
    # "LoggingMiddleware",
    # "RateLimitMiddleware",
    # "EventBusConsumer",
    # "TriggerHandler",
    # "MetricsCollector",
    # "CostTracker",
]

"""
结构化日志模块
使用 structlog 实现结构化日志输出
"""
import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from .config import settings


def add_service_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """添加服务上下文"""
    event_dict["service"] = settings.service_name
    return event_dict


def configure_logging() -> None:
    """配置日志系统"""

    # 配置标准库 logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )

    # 配置 structlog
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_service_context,
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # 开发环境使用彩色输出，生产环境使用 JSON
    if settings.log_level.upper() == "DEBUG":
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """获取 logger 实例"""
    return structlog.get_logger(name)


# 初始化日志系统
configure_logging()

# 导出便捷函数
logger = get_logger(__name__)


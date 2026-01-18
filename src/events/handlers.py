"""
事件处理器接口

定义事件处理器的抽象接口

Author: Qingyu AI Team
Date: 2025-10-28
"""

from abc import ABC, abstractmethod
from typing import Optional
from src.events.document_events import DocumentEvent
from src.core.logger import logger


class EventHandler(ABC):
    """
    事件处理器基类

    所有事件处理器必须继承此类并实现handle方法
    """

    def __init__(self, handler_name: Optional[str] = None):
        """
        初始化事件处理器

        Args:
            handler_name: 处理器名称
        """
        self.handler_name = handler_name or self.__class__.__name__
        logger.info(
            "event_handler_initialized",
            handler=self.handler_name
        )

    @abstractmethod
    async def handle(self, event: DocumentEvent) -> None:
        """
        处理事件

        Args:
            event: 文档事件

        Raises:
            Exception: 处理失败时抛出异常
        """
        pass

    @abstractmethod
    def can_handle(self, event: DocumentEvent) -> bool:
        """
        判断是否能处理此事件

        Args:
            event: 文档事件

        Returns:
            True if can handle, False otherwise
        """
        pass

    async def on_error(self, event: DocumentEvent, error: Exception) -> None:
        """
        错误处理回调

        Args:
            event: 文档事件
            error: 异常对象
        """
        logger.error(
            "event_handler_error",
            handler=self.handler_name,
            event_id=event.event_id,
            event_type=event.event_type,
            error=str(error),
            exc_info=True
        )

    async def on_success(self, event: DocumentEvent) -> None:
        """
        成功处理回调

        Args:
            event: 文档事件
        """
        logger.info(
            "event_handler_success",
            handler=self.handler_name,
            event_id=event.event_id,
            event_type=event.event_type
        )


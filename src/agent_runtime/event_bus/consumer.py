"""
Event Bus - 事件总线

提供异步事件发布和订阅功能，支持内存和 Kafka（预留接口）。
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime
from collections import defaultdict
from pydantic import BaseModel, Field

from src.common.types.event_types import EventType, SystemEvent


logger = logging.getLogger(__name__)


# =============================================================================
# Event Handler
# =============================================================================

class EventHandler(BaseModel):
    """
    事件处理器

    Attributes:
        name: 处理器名称
        event_types: 支持的事件类型列表
        handler: 处理函数
        enabled: 是否启用
    """

    name: str = Field(..., description="Handler name")
    event_types: List[EventType] = Field(..., description="Supported event types")
    handler: Callable = Field(..., description="Handler function")
    enabled: bool = Field(default=True, description="Whether enabled")

    model_config = {"arbitrary_types_allowed": True}


# =============================================================================
# Event Bus
# =============================================================================

class EventBus:
    """
    事件总线

    提供发布-订阅模式的事件系统。

    使用示例:
        ```python
        bus = EventBus()

        # 订阅事件
        def my_handler(event):
            print(f"Received: {event.data}")

        bus.subscribe(EventType.AGENT_STARTED, my_handler)

        # 发布事件
        await bus.publish(SystemEvent(
            type=EventType.AGENT_STARTED,
            agent_id="agent_123",
            data={"task": "test"},
        ))
        ```
    """

    def __init__(self, enable_kafka: bool = False, max_history: int = 1000):
        """
        初始化事件总线

        Args:
            enable_kafka: 是否启用 Kafka（预留接口）
            max_history: 事件历史最大数量
        """
        self._handlers: Dict[EventType, List[EventHandler]] = defaultdict(list)
        self._event_history: List[SystemEvent] = []
        self._max_history = max_history
        self._enable_kafka = enable_kafka
        self._lock = asyncio.Lock()

        logger.info(f"Created EventBus (kafka={enable_kafka}, max_history={max_history})")

    async def subscribe(
        self,
        event_type: EventType,
        handler: Callable,
        name: Optional[str] = None,
    ) -> None:
        """
        订阅事件

        Args:
            event_type: 事件类型
            handler: 处理函数
            name: 处理器名称（可选）
        """
        handler_name = name or f"{event_type.value}_handler_{id(handler)}"
        event_handler = EventHandler(
            name=handler_name,
            event_types=[event_type],
            handler=handler,
        )

        async with self._lock:
            self._handlers[event_type].append(event_handler)

        logger.info(f"Subscribed to {event_type.value}: {handler_name}")

    async def unsubscribe(
        self,
        event_type: EventType,
        handler_name: str,
    ) -> bool:
        """
        取消订阅

        Args:
            event_type: 事件类型
            handler_name: 处理器名称

        Returns:
            是否成功取消
        """
        async with self._lock:
            handlers = self._handlers.get(event_type, [])
            for i, h in enumerate(handlers):
                if h.name == handler_name:
                    handlers.pop(i)
                    logger.info(f"Unsubscribed from {event_type.value}: {handler_name}")
                    return True

        logger.warning(f"Handler not found: {handler_name}")
        return False

    async def publish(self, event: SystemEvent) -> None:
        """
        发布事件

        Args:
            event: 系统事件
        """
        logger.debug(f"Publishing event: {event.event_type.value}")

        # 添加到历史
        self._add_to_history(event)

        # 获取处理器
        async with self._lock:
            handlers = self._handlers.get(event.event_type, []).copy()

        # 异步调用所有处理器
        if handlers:
            tasks = []
            for handler in handlers:
                if handler.enabled:
                    tasks.append(self._call_handler(handler, event))

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        # Kafka 发布（预留）
        if self._enable_kafka:
            await self._publish_to_kafka(event)

    async def _call_handler(self, handler: EventHandler, event: SystemEvent) -> None:
        """
        调用处理器

        Args:
            handler: 事件处理器
            event: 系统事件
        """
        try:
            if asyncio.iscoroutinefunction(handler.handler):
                await handler.handler(event)
            else:
                handler.handler(event)
        except Exception as e:
            logger.error(f"Handler error ({handler.name}): {e}")

    def _add_to_history(self, event: SystemEvent) -> None:
        """添加事件到历史"""
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

    async def _publish_to_kafka(self, event: SystemEvent) -> None:
        """发布到 Kafka（预留接口）"""
        # TODO: 实现 Kafka 发布
        pass

    async def get_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 100,
    ) -> List[SystemEvent]:
        """
        获取事件历史

        Args:
            event_type: 可选的事件类型过滤
            limit: 最大数量

        Returns:
            事件列表
        """
        if event_type:
            events = [e for e in self._event_history if e.event_type == event_type]
        else:
            events = self._event_history.copy()

        return events[-limit:]

    def get_handler_count(self, event_type: Optional[EventType] = None) -> int:
        """
        获取处理器数量

        Args:
            event_type: 可选的事件类型

        Returns:
            处理器数量
        """
        if event_type:
            return len(self._handlers.get(event_type, []))
        return sum(len(handlers) for handlers in self._handlers.values())

    def enable_handler(self, event_type: EventType, handler_name: str) -> bool:
        """启用处理器"""
        handlers = self._handlers.get(event_type, [])
        for h in handlers:
            if h.name == handler_name:
                h.enabled = True
                return True
        return False

    def disable_handler(self, event_type: EventType, handler_name: str) -> bool:
        """禁用处理器"""
        handlers = self._handlers.get(event_type, [])
        for h in handlers:
            if h.name == handler_name:
                h.enabled = False
                return True
        return False


# =============================================================================
# Global Event Bus Instance
# =============================================================================

_global_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """获取全局事件总线实例"""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus

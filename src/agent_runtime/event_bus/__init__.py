"""
Event Bus - 事件总线

实现事件驱动的 Agent 触发机制。
"""

from .consumer import EventBus, get_event_bus

__all__ = ["EventBus", "get_event_bus"]

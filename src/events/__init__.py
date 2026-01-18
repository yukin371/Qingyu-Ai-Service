"""
事件系统

提供文档变更事件的定义和处理

Author: Qingyu AI Team
Date: 2025-10-28
"""

from src.events.document_events import (
    DocumentEvent,
    DocumentCreatedEvent,
    DocumentUpdatedEvent,
    DocumentDeletedEvent
)
from src.events.handlers import EventHandler

__all__ = [
    'DocumentEvent',
    'DocumentCreatedEvent',
    'DocumentUpdatedEvent',
    'DocumentDeletedEvent',
    'EventHandler',
]


"""
文档事件定义

定义文档生命周期中的各种事件

Author: Qingyu AI Team
Date: 2025-10-28
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum
import uuid


class EventType(str, Enum):
    """事件类型"""
    DOCUMENT_CREATED = "document.created"
    DOCUMENT_UPDATED = "document.updated"
    DOCUMENT_DELETED = "document.deleted"
    BATCH_REINDEX = "batch.reindex"


@dataclass
class DocumentEvent:
    """
    文档事件基类

    所有文档相关事件的基类
    """
    event_id: str
    event_type: str
    document_id: str
    timestamp: datetime
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理"""
        # 确保timestamp是datetime对象
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'document_id': self.document_id,
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'metadata': self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentEvent':
        """从字典创建"""
        return cls(**data)


@dataclass
class DocumentCreatedEvent(DocumentEvent):
    """
    文档创建事件

    当新文档被创建时触发
    """
    content: str                         # 文档内容
    source: str                          # 来源（project/chapter等）
    title: Optional[str] = None          # 文档标题
    tags: list = field(default_factory=list)  # 标签

    def __post_init__(self):
        super().__post_init__()
        self.event_type = EventType.DOCUMENT_CREATED

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        d = super().to_dict()
        d.update({
            'content': self.content,
            'source': self.source,
            'title': self.title,
            'tags': self.tags
        })
        return d


@dataclass
class DocumentUpdatedEvent(DocumentEvent):
    """
    文档更新事件

    当文档内容被修改时触发
    """
    content: str                         # 新内容
    old_content: Optional[str] = None    # 旧内容（可选）
    source: str = "unknown"              # 来源
    title: Optional[str] = None          # 文档标题
    tags: list = field(default_factory=list)  # 标签

    def __post_init__(self):
        super().__post_init__()
        self.event_type = EventType.DOCUMENT_UPDATED

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        d = super().to_dict()
        d.update({
            'content': self.content,
            'old_content': self.old_content,
            'source': self.source,
            'title': self.title,
            'tags': self.tags
        })
        return d


@dataclass
class DocumentDeletedEvent(DocumentEvent):
    """
    文档删除事件

    当文档被删除时触发
    """
    source: Optional[str] = None         # 来源

    def __post_init__(self):
        super().__post_init__()
        self.event_type = EventType.DOCUMENT_DELETED

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        d = super().to_dict()
        d['source'] = self.source
        return d


@dataclass
class BatchReindexEvent(DocumentEvent):
    """
    批量重建索引事件

    用于批量重建文档索引
    """
    document_ids: list = field(default_factory=list)  # 文档ID列表
    force: bool = False                   # 是否强制重建

    def __post_init__(self):
        super().__post_init__()
        self.event_type = EventType.BATCH_REINDEX

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        d = super().to_dict()
        d.update({
            'document_ids': self.document_ids,
            'force': self.force
        })
        return d


def create_event(
    event_type: str,
    document_id: str,
    user_id: Optional[str] = None,
    **kwargs
) -> DocumentEvent:
    """
    工厂函数：创建事件

    Args:
        event_type: 事件类型
        document_id: 文档ID
        user_id: 用户ID
        **kwargs: 其他参数

    Returns:
        对应的事件对象
    """
    event_id = str(uuid.uuid4())
    timestamp = datetime.now()

    base_params = {
        'event_id': event_id,
        'event_type': event_type,
        'document_id': document_id,
        'timestamp': timestamp,
        'user_id': user_id
    }

    if event_type == EventType.DOCUMENT_CREATED:
        return DocumentCreatedEvent(**base_params, **kwargs)
    elif event_type == EventType.DOCUMENT_UPDATED:
        return DocumentUpdatedEvent(**base_params, **kwargs)
    elif event_type == EventType.DOCUMENT_DELETED:
        return DocumentDeletedEvent(**base_params, **kwargs)
    elif event_type == EventType.BATCH_REINDEX:
        return BatchReindexEvent(**base_params, **kwargs)
    else:
        return DocumentEvent(**base_params, **kwargs)


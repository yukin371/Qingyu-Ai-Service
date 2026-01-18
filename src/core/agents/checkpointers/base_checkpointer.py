"""
Checkpointer 基类
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Checkpoint:
    """检查点数据结构"""

    thread_id: str
    checkpoint_id: str
    parent_checkpoint_id: Optional[str]
    state: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class BaseCheckpointer(ABC):
    """Checkpointer 基类"""

    @abstractmethod
    async def save(
        self, thread_id: str, checkpoint_id: str, state: Dict[str, Any], metadata: Dict[str, Any] = None
    ) -> None:
        """保存检查点"""
        pass

    @abstractmethod
    async def load(self, thread_id: str) -> Optional[Checkpoint]:
        """加载最新检查点"""
        pass

    @abstractmethod
    async def load_by_id(self, thread_id: str, checkpoint_id: str) -> Optional[Checkpoint]:
        """根据 checkpoint_id 加载"""
        pass

    @abstractmethod
    async def list_checkpoints(self, thread_id: str, limit: int = 10) -> List[Checkpoint]:
        """列出所有检查点"""
        pass

    @abstractmethod
    async def delete(self, thread_id: str) -> None:
        """删除所有检查点"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查"""
        pass



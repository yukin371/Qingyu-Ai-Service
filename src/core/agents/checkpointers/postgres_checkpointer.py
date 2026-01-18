"""
PostgreSQL Checkpointer - 基于 PostgreSQL 的持久化实现
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import uuid

try:
    from langgraph.checkpoint.postgres import PostgresSaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

from .base_checkpointer import BaseCheckpointer, Checkpoint
from src.core.logger import get_logger
from src.core.config import get_settings

logger = get_logger(__name__)


class PostgresCheckpointer(BaseCheckpointer):
    """PostgreSQL 持久化实现

    使用 LangGraph 的 PostgresSaver 作为底层实现
    """

    def __init__(self, conn_string: Optional[str] = None):
        if not LANGGRAPH_AVAILABLE:
            raise ImportError(
                "langgraph-checkpoint-postgres is not installed. "
                "Please install it: pip install langgraph-checkpoint-postgres"
            )

        settings = get_settings()
        self.conn_string = conn_string or settings.postgres_dsn

        if not self.conn_string:
            raise ValueError("PostgreSQL connection string is required")

        # 初始化 LangGraph PostgresSaver
        try:
            self.saver = PostgresSaver.from_conn_string(self.conn_string)
            logger.info("PostgresCheckpointer initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PostgresCheckpointer: {e}")
            raise

    async def save(
        self,
        thread_id: str,
        checkpoint_id: str,
        state: Dict[str, Any],
        metadata: Dict[str, Any] = None,
    ) -> None:
        """保存检查点"""
        try:
            config = {"configurable": {"thread_id": thread_id}}

            # 准备 checkpoint 数据
            checkpoint_data = {
                "id": checkpoint_id,
                "state": state,
                "metadata": metadata or {},
                "created_at": datetime.now().isoformat(),
            }

            # 使用 LangGraph 的 aput 方法
            await self.saver.aput(config=config, checkpoint=checkpoint_data)

            logger.info(
                f"Checkpoint saved",
                thread_id=thread_id,
                checkpoint_id=checkpoint_id,
            )

        except Exception as e:
            logger.error(
                f"Failed to save checkpoint",
                thread_id=thread_id,
                error=str(e),
            )
            raise

    async def load(self, thread_id: str) -> Optional[Checkpoint]:
        """加载最新检查点"""
        try:
            config = {"configurable": {"thread_id": thread_id}}

            # 使用 LangGraph 的 aget 方法
            checkpoint_data = await self.saver.aget(config=config)

            if not checkpoint_data:
                logger.debug(f"No checkpoint found for thread_id: {thread_id}")
                return None

            # 转换为 Checkpoint 对象
            return self._to_checkpoint(thread_id, checkpoint_data)

        except Exception as e:
            logger.error(
                f"Failed to load checkpoint",
                thread_id=thread_id,
                error=str(e),
            )
            return None

    async def load_by_id(
        self, thread_id: str, checkpoint_id: str
    ) -> Optional[Checkpoint]:
        """根据 checkpoint_id 加载"""
        try:
            config = {
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_id": checkpoint_id,
                }
            }

            checkpoint_data = await self.saver.aget(config=config)

            if not checkpoint_data:
                return None

            return self._to_checkpoint(thread_id, checkpoint_data)

        except Exception as e:
            logger.error(
                f"Failed to load checkpoint by id",
                thread_id=thread_id,
                checkpoint_id=checkpoint_id,
                error=str(e),
            )
            return None

    async def list_checkpoints(
        self, thread_id: str, limit: int = 10
    ) -> List[Checkpoint]:
        """列出所有检查点"""
        try:
            config = {"configurable": {"thread_id": thread_id}}

            # 使用 LangGraph 的 alist 方法
            checkpoints_data = await self.saver.alist(config=config, limit=limit)

            checkpoints = []
            for cp_data in checkpoints_data:
                checkpoint = self._to_checkpoint(thread_id, cp_data)
                if checkpoint:
                    checkpoints.append(checkpoint)

            logger.debug(
                f"Listed {len(checkpoints)} checkpoints for thread_id: {thread_id}"
            )

            return checkpoints

        except Exception as e:
            logger.error(
                f"Failed to list checkpoints",
                thread_id=thread_id,
                error=str(e),
            )
            return []

    async def delete(self, thread_id: str) -> None:
        """删除所有检查点"""
        try:
            # LangGraph 的 PostgresSaver 可能不直接支持删除
            # 这里需要根据实际 API 实现
            logger.warning(
                f"Delete checkpoint not implemented for thread_id: {thread_id}"
            )

        except Exception as e:
            logger.error(
                f"Failed to delete checkpoints",
                thread_id=thread_id,
                error=str(e),
            )
            raise

    async def health_check(self) -> bool:
        """健康检查"""
        try:
            # 简单的健康检查：尝试创建一个临时 checkpoint
            test_thread_id = f"health_check_{uuid.uuid4()}"
            await self.save(
                thread_id=test_thread_id,
                checkpoint_id="health_check",
                state={"test": True},
            )

            # 尝试加载
            result = await self.load(test_thread_id)

            # 清理
            await self.delete(test_thread_id)

            return result is not None

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def _to_checkpoint(
        self, thread_id: str, checkpoint_data: Dict[str, Any]
    ) -> Optional[Checkpoint]:
        """将原始数据转换为 Checkpoint 对象"""
        try:
            return Checkpoint(
                thread_id=thread_id,
                checkpoint_id=checkpoint_data.get("id", ""),
                parent_checkpoint_id=checkpoint_data.get("parent_id"),
                state=checkpoint_data.get("state", {}),
                metadata=checkpoint_data.get("metadata", {}),
                created_at=datetime.fromisoformat(
                    checkpoint_data.get("created_at", datetime.now().isoformat())
                ),
                updated_at=datetime.now(),
            )
        except Exception as e:
            logger.error(f"Failed to convert checkpoint data: {e}")
            return None



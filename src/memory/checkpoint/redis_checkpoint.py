"""
Redis Checkpoint Implementation

Provides checkpoint persistence using Redis backend for LangChain workflows.
Supports saving, loading, and managing conversation state checkpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
import json
import asyncio


class CheckpointNotFoundError(Exception):
    """Raised when checkpoint is not found."""

    pass


class CheckpointData(BaseModel):
    """
    Checkpoint data model.

    Attributes:
        thread_id: Conversation thread identifier
        checkpoint_id: Unique checkpoint identifier
        state: Conversation state
        metadata: Checkpoint metadata
        created_at: Creation timestamp
    """

    thread_id: str = Field(..., description="Thread identifier")
    checkpoint_id: str = Field(default_factory=lambda: f"ckpt_{datetime.now().timestamp()}")
    state: Dict[str, Any] = Field(default_factory=dict, description="Conversation state")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Checkpoint metadata")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation time")

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})


class RedisCheckpoint:
    """
    Redis-based checkpoint saver for LangChain workflows.

    Provides persistent storage of conversation checkpoints using Redis.
    Supports TTL for automatic expiration of old checkpoints.

    Example:
        ```python
        import redis

        # Create Redis connection
        conn = redis.Redis(host='localhost', port=6379, decode_responses=True)

        # Create checkpoint saver
        checkpoint = RedisCheckpoint(conn=conn, ttl=3600)

        # Save checkpoint
        await checkpoint.save("thread_123", {
            "thread_id": "thread_123",
            "state": {"messages": ["hello"]},
            "metadata": {}
        })

        # Load checkpoint
        data = await checkpoint.load("thread_123")
        ```
    """

    def __init__(self, conn: Optional[Any] = None, ttl: int = 3600, prefix: str = "checkpoint"):
        """
        Initialize RedisCheckpoint.

        Args:
            conn: Redis connection (if None, uses mock storage for testing)
            ttl: Time-to-live for checkpoints in seconds (0 = no expiry)
            prefix: Key prefix for Redis storage
        """
        self.conn = conn
        self.ttl = ttl
        self.prefix = prefix
        self._mock_storage = {} if conn is None else None

    def _make_key(self, thread_id: str) -> str:
        """
        Generate Redis key for thread.

        Args:
            thread_id: Thread identifier

        Returns:
            Redis key string
        """
        return f"{self.prefix}:{thread_id}"

    async def save(self, thread_id: str, checkpoint: Dict[str, Any]) -> CheckpointData:
        """
        Save checkpoint to Redis.

        Args:
            thread_id: Thread identifier
            checkpoint: Checkpoint data dictionary

        Returns:
            Saved CheckpointData object

        Raises:
            Exception: If save fails
        """
        try:
            # Create checkpoint data
            if isinstance(checkpoint, dict):
                checkpoint_data = CheckpointData(
                    thread_id=thread_id,
                    checkpoint_id=checkpoint.get("checkpoint_id"),
                    state=checkpoint.get("state", {}),
                    metadata=checkpoint.get("metadata", {}),
                )
            else:
                checkpoint_data = checkpoint

            key = self._make_key(thread_id)
            value = checkpoint_data.model_dump_json()

            # Save to Redis or mock storage
            if self.conn is not None:
                if self.ttl > 0:
                    await self.conn.set(key, value, ex=self.ttl)
                else:
                    await self.conn.set(key, value)
            else:
                # Mock storage for testing
                self._mock_storage[key] = value

            return checkpoint_data

        except Exception as e:
            raise Exception(f"Failed to save checkpoint: {e}") from e

    async def load(self, thread_id: str) -> Dict[str, Any]:
        """
        Load checkpoint from Redis.

        Args:
            thread_id: Thread identifier

        Returns:
            Checkpoint data dictionary

        Raises:
            CheckpointNotFoundError: If checkpoint not found
        """
        try:
            key = self._make_key(thread_id)

            # Load from Redis or mock storage
            if self.conn is not None:
                value = await self.conn.get(key)
            else:
                value = self._mock_storage.get(key)

            if value is None:
                raise CheckpointNotFoundError(
                    f"Checkpoint not found for thread: {thread_id}"
                )

            # Parse JSON
            data = json.loads(value)
            return data

        except CheckpointNotFoundError:
            raise
        except Exception as e:
            raise Exception(f"Failed to load checkpoint: {e}") from e

    async def list(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List all checkpoints.

        Args:
            limit: Maximum number of checkpoints to return
            offset: Offset for pagination

        Returns:
            List of checkpoint data dictionaries
        """
        try:
            pattern = f"{self.prefix}:*"

            if self.conn is not None:
                # Get keys from Redis
                keys = await self.conn.keys(pattern)
            else:
                # Get keys from mock storage
                keys = [k for k in self._mock_storage.keys() if k.startswith(self.prefix)]

            # Apply pagination
            keys = keys[offset : offset + limit]

            checkpoints = []
            for key in keys:
                if self.conn is not None:
                    value = await self.conn.get(key)
                else:
                    value = self._mock_storage.get(key)

                if value:
                    data = json.loads(value)
                    checkpoints.append(data)

            return checkpoints

        except Exception as e:
            raise Exception(f"Failed to list checkpoints: {e}") from e

    async def delete(self, thread_id: str) -> bool:
        """
        Delete checkpoint from Redis.

        Args:
            thread_id: Thread identifier

        Returns:
            True if deleted
        """
        try:
            key = self._make_key(thread_id)

            if self.conn is not None:
                await self.conn.delete(key)
            else:
                if key in self._mock_storage:
                    del self._mock_storage[key]

            return True

        except Exception as e:
            raise Exception(f"Failed to delete checkpoint: {e}") from e

    async def exists(self, thread_id: str) -> bool:
        """
        Check if checkpoint exists.

        Args:
            thread_id: Thread identifier

        Returns:
            True if checkpoint exists
        """
        try:
            key = self._make_key(thread_id)

            if self.conn is not None:
                value = await self.conn.get(key)
            else:
                value = self._mock_storage.get(key)

            return value is not None

        except Exception:
            return False

    async def get_metadata(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """
        Get checkpoint metadata only.

        Args:
            thread_id: Thread identifier

        Returns:
            Metadata dictionary or None
        """
        try:
            checkpoint = await self.load(thread_id)
            return checkpoint.get("metadata")

        except CheckpointNotFoundError:
            return None
        except Exception:
            return None

    async def update_metadata(
        self, thread_id: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update checkpoint metadata.

        Args:
            thread_id: Thread identifier
            metadata: New metadata (will be merged)

        Returns:
            Updated metadata

        Raises:
            CheckpointNotFoundError: If checkpoint not found
        """
        checkpoint = await self.load(thread_id)
        checkpoint["metadata"].update(metadata)

        # Save updated checkpoint
        await self.save(thread_id, checkpoint)
        return checkpoint["metadata"]

    async def get_state(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """
        Get checkpoint state only.

        Args:
            thread_id: Thread identifier

        Returns:
            State dictionary or None
        """
        try:
            checkpoint = await self.load(thread_id)
            return checkpoint.get("state")

        except CheckpointNotFoundError:
            return None
        except Exception:
            return None

    async def update_state(
        self, thread_id: str, state: Dict[str, Any], merge: bool = True
    ) -> Dict[str, Any]:
        """
        Update checkpoint state.

        Args:
            thread_id: Thread identifier
            state: New state
            merge: If True, merge with existing state; if False, replace

        Returns:
            Updated state

        Raises:
            CheckpointNotFoundError: If checkpoint not found
        """
        checkpoint = await self.load(thread_id)

        if merge:
            checkpoint["state"].update(state)
        else:
            checkpoint["state"] = state

        # Save updated checkpoint
        await self.save(thread_id, checkpoint)
        return checkpoint["state"]

    async def clear_all(self) -> int:
        """
        Clear all checkpoints.

        Returns:
            Number of checkpoints deleted
        """
        try:
            pattern = f"{self.prefix}:*"

            if self.conn is not None:
                keys = await self.conn.keys(pattern)
                if keys:
                    await self.conn.delete(*keys)
                return len(keys)
            else:
                count = len(self._mock_storage)
                self._mock_storage.clear()
                return count

        except Exception as e:
            raise Exception(f"Failed to clear checkpoints: {e}") from e

    async def get_count(self) -> int:
        """
        Get total number of checkpoints.

        Returns:
            Number of checkpoints
        """
        try:
            pattern = f"{self.prefix}:*"

            if self.conn is not None:
                keys = await self.conn.keys(pattern)
                return len(keys)
            else:
                return len(self._mock_storage)

        except Exception:
            return 0

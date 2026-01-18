"""
Redis Store Implementation

Provides Redis backend implementation for memory storage.
"""

import json
from typing import Any, List, Optional
from src.memory.store.interface import IMemoryStore, StorageError


class RedisStore(IMemoryStore):
    """
    Redis-based memory store implementation.

    Provides persistent storage using Redis backend with support for:
    - Key-value storage with JSON serialization
    - TTL (time-to-live) for automatic expiration
    - Pattern-based key lookup
    - Atomic operations

    Example:
        ```python
        import redis

        # Create Redis connection
        conn = redis.Redis(host='localhost', port=6379, decode_responses=True)

        # Create store
        store = RedisStore(conn=conn, prefix="memory")

        # Save data
        await store.save("user:123", {"name": "Alice", "age": 30})

        # Load data
        data = await store.load("user:123")

        # Delete data
        await store.delete("user:123")
        ```
    """

    def __init__(self, conn: Optional[Any] = None, prefix: str = "memory"):
        """
        Initialize RedisStore.

        Args:
            conn: Redis connection (if None, uses mock storage for testing)
            prefix: Key prefix for namespacing
        """
        self.conn = conn
        self.prefix = prefix
        self._mock_storage = {} if conn is None else None

    def _make_key(self, key: str) -> str:
        """
        Generate full Redis key with prefix.

        Args:
            key: Original key

        Returns:
            Full key with prefix
        """
        return f"{self.prefix}:{key}" if self.prefix else key

    def _serialize(self, value: Any) -> str:
        """
        Serialize value to JSON string.

        Args:
            value: Value to serialize

        Returns:
            JSON string

        Raises:
            StorageError: If serialization fails
        """
        try:
            return json.dumps(value)
        except (TypeError, ValueError) as e:
            raise StorageError(f"Failed to serialize value: {e}") from e

    def _deserialize(self, value: str) -> Any:
        """
        Deserialize JSON string to value.

        Args:
            value: JSON string

        Returns:
            Deserialized value

        Raises:
            StorageError: If deserialization fails
        """
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError) as e:
            raise StorageError(f"Failed to deserialize value: {e}") from e

    async def save(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Save value to Redis.

        Args:
            key: Storage key
            value: Value to store
            ttl: Optional TTL in seconds

        Returns:
            True if successful

        Raises:
            StorageError: If save fails
        """
        try:
            full_key = self._make_key(key)
            serialized = self._serialize(value)

            if self.conn is not None:
                if ttl:
                    await self.conn.set(full_key, serialized, ex=ttl)
                else:
                    await self.conn.set(full_key, serialized)
            else:
                # Mock storage (doesn't support TTL)
                self._mock_storage[full_key] = serialized

            return True

        except Exception as e:
            raise StorageError(f"Failed to save key '{key}': {e}") from e

    async def load(self, key: str) -> Optional[Any]:
        """
        Load value from Redis.

        Args:
            key: Storage key

        Returns:
            Loaded value or None if not found

        Raises:
            StorageError: If load fails
        """
        try:
            full_key = self._make_key(key)

            if self.conn is not None:
                serialized = await self.conn.get(full_key)
            else:
                serialized = self._mock_storage.get(full_key)

            if serialized is None:
                return None

            return self._deserialize(serialized)

        except StorageError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to load key '{key}': {e}") from e

    async def delete(self, key: str) -> bool:
        """
        Delete value from Redis.

        Args:
            key: Storage key

        Returns:
            True if deleted or didn't exist

        Raises:
            StorageError: If delete fails
        """
        try:
            full_key = self._make_key(key)

            if self.conn is not None:
                await self.conn.delete(full_key)
            else:
                if full_key in self._mock_storage:
                    del self._mock_storage[full_key]

            return True

        except Exception as e:
            raise StorageError(f"Failed to delete key '{key}': {e}") from e

    async def exists(self, key: str) -> bool:
        """
        Check if key exists in Redis.

        Args:
            key: Storage key

        Returns:
            True if key exists

        Raises:
            StorageError: If check fails
        """
        try:
            full_key = self._make_key(key)

            if self.conn is not None:
                return await self.conn.exists(full_key) > 0
            else:
                return full_key in self._mock_storage

        except Exception as e:
            raise StorageError(f"Failed to check existence of key '{key}': {e}") from e

    async def keys(self, pattern: str = "*") -> List[str]:
        """
        List all keys matching pattern.

        Args:
            pattern: Key pattern (supports * wildcards)

        Returns:
            List of keys (without prefix)

        Raises:
            StorageError: If operation fails
        """
        try:
            # Add prefix to pattern
            full_pattern = self._make_key(pattern.replace("*", "")) + "*"

            if self.conn is not None:
                full_keys = await self.conn.keys(full_pattern)
            else:
                full_keys = [k for k in self._mock_storage.keys() if full_pattern.replace("*", "") in k]

            # Remove prefix from returned keys
            prefix_len = len(self.prefix) + 1 if self.prefix else 0
            keys = [k[prefix_len:] for k in full_keys]

            return keys

        except Exception as e:
            raise StorageError(f"Failed to list keys with pattern '{pattern}': {e}") from e

    async def clear(self) -> bool:
        """
        Clear all data from Redis (with configured prefix).

        Returns:
            True if successful

        Raises:
            StorageError: If clear fails
        """
        try:
            pattern = self._make_key("*")

            if self.conn is not None:
                keys = await self.conn.keys(pattern)
                if keys:
                    await self.conn.delete(*keys)
            else:
                self._mock_storage.clear()

            return True

        except Exception as e:
            raise StorageError(f"Failed to clear storage: {e}") from e

    async def update(self, key: str, updates: dict, ttl: Optional[int] = None) -> bool:
        """
        Update existing value with partial updates.

        Args:
            key: Storage key
            updates: Dictionary of updates to merge
            ttl: Optional new TTL

        Returns:
            True if successful

        Raises:
            StorageError: If update fails or key doesn't exist
        """
        try:
            # Load existing
            value = await self.load(key)
            if value is None:
                raise StorageError(f"Key '{key}' not found for update")

            # Update if dict
            if isinstance(value, dict):
                value.update(updates)
            else:
                raise StorageError(f"Cannot update non-dict value for key '{key}'")

            # Save back
            return await self.save(key, value, ttl)

        except StorageError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to update key '{key}': {e}") from e

    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment a numeric value.

        Args:
            key: Storage key
            amount: Amount to increment (can be negative)

        Returns:
            New value

        Raises:
            StorageError: If increment fails
        """
        try:
            # Load current
            value = await self.load(key)
            if value is None:
                new_value = amount
            else:
                if not isinstance(value, (int, float)):
                    raise StorageError(f"Cannot increment non-numeric value for key '{key}'")
                new_value = value + amount

            # Save back
            await self.save(key, new_value)
            return new_value

        except StorageError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to increment key '{key}': {e}") from e

    async def get_ttl(self, key: str) -> Optional[int]:
        """
        Get remaining TTL for key.

        Args:
            key: Storage key

        Returns:
            TTL in seconds, or None if no expiry / key doesn't exist

        Raises:
            StorageError: If operation fails
        """
        try:
            full_key = self._make_key(key)

            if self.conn is not None:
                ttl = await self.conn.ttl(full_key)
                return ttl if ttl > 0 else None
            else:
                # Mock storage doesn't support TTL
                return None

        except Exception as e:
            raise StorageError(f"Failed to get TTL for key '{key}': {e}") from e

    async def set_ttl(self, key: str, ttl: int) -> bool:
        """
        Set TTL for existing key.

        Args:
            key: Storage key
            ttl: TTL in seconds

        Returns:
            True if successful

        Raises:
            StorageError: If operation fails
        """
        try:
            full_key = self._make_key(key)

            if self.conn is not None:
                await self.conn.expire(full_key, ttl)

            # Mock storage doesn't support TTL
            return True

        except Exception as e:
            raise StorageError(f"Failed to set TTL for key '{key}': {e}") from e

"""
Memory Store Interface

Defines the unified storage interface for memory backends.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional


class StorageError(Exception):
    """Base exception for storage operations."""

    pass


class IMemoryStore(ABC):
    """
    Interface for memory storage backends.

    All storage implementations must implement these methods.
    Supports multiple backends: Redis, PostgreSQL, etc.
    """

    @abstractmethod
    async def save(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Save value to storage.

        Args:
            key: Storage key
            value: Value to store (will be serialized)
            ttl: Optional time-to-live in seconds

        Returns:
            True if successful

        Raises:
            StorageError: If save fails
        """
        pass

    @abstractmethod
    async def load(self, key: str) -> Optional[Any]:
        """
        Load value from storage.

        Args:
            key: Storage key

        Returns:
            Loaded value or None if not found

        Raises:
            StorageError: If load fails
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete value from storage.

        Args:
            key: Storage key

        Returns:
            True if deleted or didn't exist

        Raises:
            StorageError: If delete fails
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in storage.

        Args:
            key: Storage key

        Returns:
            True if key exists

        Raises:
            StorageError: If check fails
        """
        pass

    @abstractmethod
    async def keys(self, pattern: str = "*") -> List[str]:
        """
        List all keys matching pattern.

        Args:
            pattern: Key pattern (supports wildcards)

        Returns:
            List of keys

        Raises:
            StorageError: If operation fails
        """
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """
        Clear all data from storage.

        Returns:
            True if successful

        Raises:
            StorageError: If clear fails
        """
        pass

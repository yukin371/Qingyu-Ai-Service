"""
Memory Store Submodule

This module provides persistent storage backends for memory systems.

Storage Backends:
- RedisStore: Redis-based storage (implemented)
- PostgresStore: PostgreSQL-based storage (planned)

Features:
- Unified storage interface (IMemoryStore)
- JSON serialization
- TTL support
- Pattern-based key lookup
- Error handling
"""

from src.memory.store.interface import IMemoryStore, StorageError
from src.memory.store.redis_store import RedisStore

__all__ = [
    "IMemoryStore",
    "StorageError",
    "RedisStore",
]

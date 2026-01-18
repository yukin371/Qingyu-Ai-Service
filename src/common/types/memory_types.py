"""
Memory Type Definitions

This module defines all types related to memory management, including
memory entries, configurations, and user profiles.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Enums
# =============================================================================

class MemoryType(str, Enum):
    """Types of memory storage."""

    EPISODIC = "episodic"  # Specific experiences/events
    SEMANTIC = "semantic"  # General knowledge
    WORKING = "working"    # Temporary/task-specific
    LONG_TERM = "long_term"  # Persistent storage


class MemoryScope(str, Enum):
    """Scope of memory visibility."""

    GLOBAL = "global"      # System-wide
    USER = "user"          # User-specific
    SESSION = "session"    # Session-specific
    AGENT = "agent"        # Agent-specific


# =============================================================================
# Memory Entry
# =============================================================================

class MemoryEntry(BaseModel):
    """
    A single memory entry.

    Attributes:
        entry_id: Unique identifier for the entry
        memory_type: Type of memory
        scope: Visibility scope
        content: The memory content
        embeddings: Vector embeddings (if available)
        metadata: Additional metadata
        importance: Importance score (0-1)
        access_count: Number of times accessed
        last_accessed: Last access timestamp
        expires_at: Optional expiration time
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    entry_id: UUID = Field(default_factory=uuid4)
    memory_type: MemoryType
    scope: MemoryScope
    content: str
    embeddings: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    access_count: int = Field(default=0, ge=0)
    last_accessed: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(use_enum_values=False)

    def is_expired(self) -> bool:
        """Check if memory entry is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def touch(self) -> None:
        """Update access timestamp and count."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()
        self.updated_at = datetime.utcnow()


# =============================================================================
# Memory Configuration
# =============================================================================

class MemoryConfig(BaseModel):
    """
    Configuration for memory management.

    Attributes:
        max_entries: Maximum number of entries to store
        max_size_bytes: Maximum size in bytes
        ttl: Time-to-live for entries
        cleanup_interval: Interval for cleanup operations
        enable_embeddings: Whether to generate embeddings
        embedding_model: Model to use for embeddings
        retention_policy: Policy for memory retention
        index_types: Types of memory to index
    """

    max_entries: int = Field(default=10000, ge=1)
    max_size_bytes: Optional[int] = Field(default=None, ge=1)
    ttl: Optional[timedelta] = None
    cleanup_interval: timedelta = Field(default=timedelta(hours=1))
    enable_embeddings: bool = False
    embedding_model: Optional[str] = None
    retention_policy: str = Field(default="lru")  # lru, lfu, fifo
    index_types: List[MemoryType] = Field(default_factory=lambda: [MemoryType.EPISODIC])

    model_config = ConfigDict(use_enum_values=False)


# =============================================================================
# User Profile
# =============================================================================

class UserProfile(BaseModel):
    """
    User profile for personalized memory.

    Attributes:
        user_id: Unique user identifier
        name: User's name
        preferences: User preferences
        attributes: Custom attributes
        stats: Usage statistics
        created_at: Account creation time
        last_seen: Last activity time
    """

    user_id: str
    name: Optional[str] = None
    preferences: Dict[str, Any] = Field(default_factory=dict)
    attributes: Dict[str, Any] = Field(default_factory=dict)
    stats: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)

    def update_last_seen(self) -> None:
        """Update last seen timestamp."""
        self.last_seen = datetime.utcnow()

    def set_preference(self, key: str, value: Any) -> None:
        """Set a user preference."""
        self.preferences[key] = value

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        return self.preferences.get(key, default)


# =============================================================================
# Memory Query
# =============================================================================

class MemoryQuery(BaseModel):
    """
    Query for memory retrieval.

    Attributes:
        query_text: Text to search for
        memory_types: Types of memory to search
        scope: Scope to search within
        filters: Additional filters
        limit: Maximum results to return
        threshold: Similarity threshold (0-1)
    """

    query_text: str
    memory_types: List[MemoryType] = Field(default_factory=list)
    scope: Optional[MemoryScope] = None
    filters: Dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=10, ge=1, le=100)
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)

    model_config = ConfigDict(use_enum_values=False)


# =============================================================================
# Memory Search Result
# =============================================================================

class MemorySearchResult(BaseModel):
    """
    Result of a memory search.

    Attributes:
        entry: The memory entry
        score: Similarity score
        highlights: Highlighted matching parts
    """

    entry: MemoryEntry
    score: float = Field(ge=0.0, le=1.0)
    highlights: List[str] = Field(default_factory=list)


# =============================================================================
# Export all types
# =============================================================================

__all__ = [
    # Enums
    "MemoryType",
    "MemoryScope",
    # Memory
    "MemoryEntry",
    "MemoryConfig",
    # User
    "UserProfile",
    # Query
    "MemoryQuery",
    "MemorySearchResult",
]

"""
Tests for memory type definitions
"""

import pytest
from datetime import datetime, timedelta

from src.common.types.memory_types import (
    MemoryType,
    MemoryScope,
    MemoryEntry,
    MemoryConfig,
    UserProfile,
    MemoryQuery,
    MemorySearchResult,
)


class TestMemoryType:
    """Test MemoryType enum."""

    def test_values(self):
        """Test memory type values."""
        assert MemoryType.EPISODIC.value == "episodic"
        assert MemoryType.SEMANTIC.value == "semantic"
        assert MemoryType.WORKING.value == "working"
        assert MemoryType.LONG_TERM.value == "long_term"


class TestMemoryScope:
    """Test MemoryScope enum."""

    def test_values(self):
        """Test scope values."""
        assert MemoryScope.GLOBAL.value == "global"
        assert MemoryScope.USER.value == "user"
        assert MemoryScope.SESSION.value == "session"
        assert MemoryScope.AGENT.value == "agent"


class TestMemoryEntry:
    """Test MemoryEntry."""

    def test_create_entry(self):
        """Test creating memory entry."""
        entry = MemoryEntry(
            memory_type=MemoryType.EPISODIC,
            scope=MemoryScope.USER,
            content="Test memory"
        )
        assert entry.memory_type == MemoryType.EPISODIC
        assert entry.content == "Test memory"
        assert entry.importance == 0.5

    def test_expiration_check(self):
        """Test expiration check."""
        entry = MemoryEntry(
            memory_type=MemoryType.WORKING,
            scope=MemoryScope.SESSION,
            content="Temporary",
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        assert not entry.is_expired()

    def test_touch_method(self):
        """Test touch method."""
        entry = MemoryEntry(
            memory_type=MemoryType.EPISODIC,
            scope=MemoryScope.USER,
            content="Test"
        )
        initial_count = entry.access_count
        entry.touch()
        assert entry.access_count == initial_count + 1
        assert entry.last_accessed is not None


class TestMemoryConfig:
    """Test MemoryConfig."""

    def test_create_config(self):
        """Test creating config."""
        config = MemoryConfig()
        assert config.max_entries == 10000
        assert config.enable_embeddings is False
        assert config.retention_policy == "lru"

    def test_custom_config(self):
        """Test custom configuration."""
        config = MemoryConfig(
            max_entries=5000,
            enable_embeddings=True,
            embedding_model="text-embedding-ada-002"
        )
        assert config.max_entries == 5000
        assert config.enable_embeddings is True
        assert config.embedding_model == "text-embedding-ada-002"


class TestUserProfile:
    """Test UserProfile."""

    def test_create_profile(self):
        """Test creating user profile."""
        profile = UserProfile(user_id="user_1")
        assert profile.user_id == "user_1"
        assert profile.name is None

    def test_preferences(self):
        """Test preference management."""
        profile = UserProfile(user_id="user_1")
        profile.set_preference("theme", "dark")
        assert profile.get_preference("theme") == "dark"
        assert profile.get_preference("missing", "default") == "default"

    def test_update_last_seen(self):
        """Test updating last seen."""
        profile = UserProfile(user_id="user_1")
        initial_time = profile.last_seen
        profile.update_last_seen()
        assert profile.last_seen >= initial_time


class TestMemoryQuery:
    """Test MemoryQuery."""

    def test_create_query(self):
        """Test creating query."""
        query = MemoryQuery(query_text="test query")
        assert query.query_text == "test query"
        assert query.limit == 10
        assert query.threshold == 0.7

    def test_query_with_filters(self):
        """Test query with filters."""
        query = MemoryQuery(
            query_text="test",
            memory_types=[MemoryType.EPISODIC],
            scope=MemoryScope.USER,
            limit=20
        )
        assert len(query.memory_types) == 1
        assert query.scope == MemoryScope.USER
        assert query.limit == 20


class TestMemorySearchResult:
    """Test MemorySearchResult."""

    def test_create_result(self):
        """Test creating search result."""
        entry = MemoryEntry(
            memory_type=MemoryType.EPISODIC,
            scope=MemoryScope.USER,
            content="Test"
        )
        result = MemorySearchResult(entry=entry, score=0.9)
        assert result.entry == entry
        assert result.score == 0.9
        assert result.highlights == []

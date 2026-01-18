"""
Test suite for Memory Store implementations

Tests unified storage interface with Redis and PostgreSQL backends.
"""

import pytest
from typing import Any
from src.memory.store.redis_store import RedisStore
from src.memory.store.interface import IMemoryStore, StorageError


class MockRedis:
    """Mock Redis for testing."""

    def __init__(self):
        self.storage = {}

    async def set(self, key, value, ex=None):
        """Set key-value pair."""
        self.storage[key] = value

    async def get(self, key):
        """Get value by key."""
        return self.storage.get(key)

    async def delete(self, *keys):
        """Delete key(s)."""
        for key in keys:
            if key in self.storage:
                del self.storage[key]

    async def exists(self, key):
        """Check if key exists."""
        return key in self.storage

    async def keys(self, pattern="*"):
        """Get keys matching pattern."""
        if pattern == "*":
            return list(self.storage.keys())
        return [k for k in self.storage.keys() if pattern.replace("*", "") in k]


@pytest.fixture
def mock_redis():
    """Create mock Redis instance."""
    return MockRedis()


@pytest.fixture
def redis_store(mock_redis):
    """Create RedisStore with mock Redis."""
    store = RedisStore(conn=mock_redis, prefix="test")
    return store


class TestIMemoryStore:
    """Test IMemoryStore interface."""

    def test_interface_definition(self):
        """Test that IMemoryStore defines required methods."""
        required_methods = ["save", "load", "delete", "exists", "clear", "keys"]

        for method in required_methods:
            assert hasattr(IMemoryStore, method), f"Missing method: {method}"


class TestRedisStore:
    """Test RedisStore implementation."""

    @pytest.mark.asyncio
    async def test_save_and_load(self, redis_store):
        """Test saving and loading data."""
        key = "test_key"
        value = {"data": "test_value", "counter": 123}

        # Save
        await redis_store.save(key, value)

        # Load
        loaded = await redis_store.load(key)
        assert loaded is not None
        assert loaded["data"] == "test_value"
        assert loaded["counter"] == 123

    @pytest.mark.asyncio
    async def test_save_string_value(self, redis_store):
        """Test saving string value."""
        key = "string_key"
        value = "simple_string_value"

        await redis_store.save(key, value)
        loaded = await redis_store.load(key)

        assert loaded == value

    @pytest.mark.asyncio
    async def test_save_complex_object(self, redis_store):
        """Test saving complex nested object."""
        key = "complex_key"
        value = {
            "user": {"id": 123, "name": "test"},
            "items": [{"id": 1}, {"id": 2}],
            "metadata": {"tags": ["tag1", "tag2"], "count": 5},
        }

        await redis_store.save(key, value)
        loaded = await redis_store.load(key)

        assert loaded["user"]["name"] == "test"
        assert loaded["items"][0]["id"] == 1
        assert loaded["metadata"]["tags"][0] == "tag1"

    @pytest.mark.asyncio
    async def test_load_nonexistent_key(self, redis_store):
        """Test loading non-existent key."""
        result = await redis_store.load("nonexistent_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_key(self, redis_store):
        """Test deleting key."""
        key = "delete_key"
        value = {"data": "to_delete"}

        # Save
        await redis_store.save(key, value)
        assert await redis_store.load(key) is not None

        # Delete
        await redis_store.delete(key)
        assert await redis_store.load(key) is None

    @pytest.mark.asyncio
    async def test_exists(self, redis_store):
        """Test checking if key exists."""
        key = "exists_key"

        # Not exists initially
        assert await redis_store.exists(key) is False

        # Save
        await redis_store.save(key, {"data": "test"})

        # Now exists
        assert await redis_store.exists(key) is True

    @pytest.mark.asyncio
    async def test_keys(self, redis_store):
        """Test listing keys."""
        # Save multiple keys
        await redis_store.save("key1", {"data": 1})
        await redis_store.save("key2", {"data": 2})
        await redis_store.save("key3", {"data": 3})

        # List all keys
        keys = await redis_store.keys()
        assert len(keys) == 3
        assert "key1" in keys
        assert "key2" in keys
        assert "key3" in keys

    @pytest.mark.asyncio
    async def test_keys_with_pattern(self, redis_store):
        """Test listing keys with pattern."""
        # Save keys with different prefixes
        await redis_store.save("user:1", {"name": "Alice"})
        await redis_store.save("user:2", {"name": "Bob"})
        await redis_store.save("session:1", {"token": "abc"})

        # List user keys
        user_keys = await redis_store.keys(pattern="user")
        assert len(user_keys) == 2
        assert "user:1" in user_keys

    @pytest.mark.asyncio
    async def test_clear(self, redis_store):
        """Test clearing all data."""
        # Save multiple keys
        await redis_store.save("key1", {"data": 1})
        await redis_store.save("key2", {"data": 2})

        # Clear all
        await redis_store.clear()
        keys = await redis_store.keys()
        assert len(keys) == 0

    @pytest.mark.asyncio
    async def test_update_existing_key(self, redis_store):
        """Test updating existing key."""
        key = "update_key"

        # Save initial value
        await redis_store.save(key, {"version": 1, "data": "old"})
        loaded = await redis_store.load(key)
        assert loaded["version"] == 1

        # Update
        await redis_store.save(key, {"version": 2, "data": "new"})
        loaded = await redis_store.load(key)
        assert loaded["version"] == 2
        assert loaded["data"] == "new"

    @pytest.mark.asyncio
    async def test_save_with_ttl(self, mock_redis):
        """Test saving with TTL."""
        from unittest.mock import patch

        store = RedisStore(conn=mock_redis, prefix="test")

        # Save with TTL
        await store.save("ttl_key", {"data": "test"}, ttl=60)

        # Verify save was called
        assert await store.exists("ttl_key") is True

    @pytest.mark.asyncio
    async def test_save_list(self, redis_store):
        """Test saving list value."""
        key = "list_key"
        value = [1, 2, 3, 4, 5]

        await redis_store.save(key, value)
        loaded = await redis_store.load(key)

        assert loaded == value
        assert len(loaded) == 5

    @pytest.mark.asyncio
    async def test_save_none_value(self, redis_store):
        """Test saving None value."""
        key = "none_key"
        value = None

        await redis_store.save(key, value)
        loaded = await redis_store.load(key)

        assert loaded is None

    @pytest.mark.asyncio
    async def test_save_numeric_values(self, redis_store):
        """Test saving various numeric types."""
        key_int = "int_key"
        key_float = "float_key"

        await redis_store.save(key_int, 42)
        await redis_store.save(key_float, 3.14)

        assert await redis_store.load(key_int) == 42
        assert await redis_store.load(key_float) == 3.14

    @pytest.mark.asyncio
    async def test_save_boolean(self, redis_store):
        """Test saving boolean values."""
        await redis_store.save("bool_true", True)
        await redis_store.save("bool_false", False)

        assert await redis_store.load("bool_true") is True
        assert await redis_store.load("bool_false") is False

    @pytest.mark.asyncio
    async def test_empty_string_key(self, redis_store):
        """Test handling empty string key."""
        # Should handle gracefully
        await redis_store.save("", {"data": "test"})
        loaded = await redis_store.load("")
        assert loaded is not None

    @pytest.mark.asyncio
    async def test_special_characters_in_key(self, redis_store):
        """Test keys with special characters."""
        key = "key:with:colons:and-dashes"

        await redis_store.save(key, {"data": "special"})
        loaded = await redis_store.load(key)

        assert loaded is not None
        assert loaded["data"] == "special"

    @pytest.mark.asyncio
    async def test_large_value(self, redis_store):
        """Test saving large value."""
        key = "large_key"
        large_value = {"data": "x" * 10000}  # 10KB string

        await redis_store.save(key, large_value)
        loaded = await redis_store.load(key)

        assert len(loaded["data"]) == 10000

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self, redis_store):
        """Test deleting non-existent key (should not raise error)."""
        # Should not raise
        await redis_store.delete("nonexistent_key")

    @pytest.mark.asyncio
    async def test_multiple_operations_sequential(self, redis_store):
        """Test multiple sequential operations."""
        # Save
        await redis_store.save("key1", {"counter": 1})
        assert await redis_store.exists("key1") is True

        # Update
        await redis_store.save("key1", {"counter": 2})
        loaded = await redis_store.load("key1")
        assert loaded["counter"] == 2

        # Delete
        await redis_store.delete("key1")
        assert await redis_store.exists("key1") is False

    @pytest.mark.asyncio
    async def test_unicode_values(self, redis_store):
        """Test saving unicode values."""
        key = "unicode_key"
        value = {"message": "你好世界", "emoji": "🎉"}

        await redis_store.save(key, value)
        loaded = await redis_store.load(key)

        assert loaded["message"] == "你好世界"
        assert loaded["emoji"] == "🎉"


class TestStorageError:
    """Test StorageError exception."""

    def test_storage_error_creation(self):
        """Test creating StorageError."""
        error = StorageError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

"""
Test suite for Redis Checkpoint

Tests checkpoint persistence using Redis backend.
"""

import pytest
from datetime import datetime
import json
from src.memory.checkpoint.redis_checkpoint import (
    RedisCheckpoint,
    CheckpointData,
    CheckpointNotFoundError,
)


@pytest.fixture
def redis_checkpoint():
    """Create a RedisCheckpoint instance for testing."""
    # Note: This uses a mock/fake Redis for testing
    # In real implementation, you'd use a test Redis instance
    from unittest.mock import MagicMock

    checkpoint = RedisCheckpoint(conn=None)  # Will use mock internally
    checkpoint._mock_storage = {}
    yield checkpoint
    # Cleanup
    checkpoint._mock_storage.clear()


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

    async def delete(self, key):
        """Delete key."""
        if key in self.storage:
            del self.storage[key]

    async def keys(self, pattern):
        """Get keys matching pattern."""
        return [k for k in self.storage.keys() if pattern.replace("*", "") in k]

    async def ttl(self, key):
        """Get TTL for key."""
        return -1  # No expiry


@pytest.fixture
def mock_redis():
    """Create mock Redis instance."""
    return MockRedis()


@pytest.fixture
def redis_checkpoint_with_mock(mock_redis):
    """Create RedisCheckpoint with mock Redis."""
    checkpoint = RedisCheckpoint(conn=mock_redis, ttl=3600)
    return checkpoint


class TestCheckpointData:
    """Test CheckpointData model."""

    def test_checkpoint_data_creation(self):
        """Test creating checkpoint data."""
        data = CheckpointData(
            thread_id="thread_123",
            checkpoint_id="checkpoint_456",
            state={"messages": ["hello", "world"]},
            metadata={"step": 5},
        )

        assert data.thread_id == "thread_123"
        assert data.checkpoint_id == "checkpoint_456"
        assert data.state["messages"] == ["hello", "world"]
        assert data.metadata["step"] == 5

    def test_checkpoint_data_default_values(self):
        """Test checkpoint data with defaults."""
        data = CheckpointData(thread_id="thread_123")

        assert data.thread_id == "thread_123"
        assert data.checkpoint_id is not None
        assert data.state == {}
        assert data.metadata == {}


class TestRedisCheckpoint:
    """Test RedisCheckpoint functionality."""

    @pytest.mark.asyncio
    async def test_save_checkpoint(self, redis_checkpoint_with_mock):
        """Test saving a checkpoint."""
        checkpoint_data = {
            "thread_id": "thread_1",
            "checkpoint_id": "ckpt_1",
            "state": {"messages": ["test"]},
            "metadata": {"step": 1},
        }

        await redis_checkpoint_with_mock.save(
            checkpoint_data["thread_id"], checkpoint_data
        )

        # Verify save
        loaded = await redis_checkpoint_with_mock.load(checkpoint_data["thread_id"])
        assert loaded is not None
        assert loaded["thread_id"] == "thread_1"
        assert loaded["state"]["messages"] == ["test"]

    @pytest.mark.asyncio
    async def test_load_checkpoint(self, redis_checkpoint_with_mock):
        """Test loading a checkpoint."""
        checkpoint_data = {
            "thread_id": "thread_2",
            "checkpoint_id": "ckpt_2",
            "state": {"counter": 10},
            "metadata": {},
        }

        # Save first
        await redis_checkpoint_with_mock.save(
            checkpoint_data["thread_id"], checkpoint_data
        )

        # Load
        loaded = await redis_checkpoint_with_mock.load(checkpoint_data["thread_id"])
        assert loaded is not None
        assert loaded["state"]["counter"] == 10

    @pytest.mark.asyncio
    async def test_load_nonexistent_checkpoint(self, redis_checkpoint_with_mock):
        """Test loading non-existent checkpoint."""
        with pytest.raises(CheckpointNotFoundError):
            await redis_checkpoint_with_mock.load("nonexistent_thread")

    @pytest.mark.asyncio
    async def test_list_checkpoints(self, redis_checkpoint_with_mock):
        """Test listing checkpoints."""
        # Save multiple checkpoints
        for i in range(3):
            checkpoint_data = {
                "thread_id": f"thread_{i}",
                "checkpoint_id": f"ckpt_{i}",
                "state": {"index": i},
                "metadata": {},
            }
            await redis_checkpoint_with_mock.save(
                checkpoint_data["thread_id"], checkpoint_data
            )

        # List all
        checkpoints = await redis_checkpoint_with_mock.list(limit=10)
        assert len(checkpoints) == 3

    @pytest.mark.asyncio
    async def test_list_checkpoints_with_limit(self, redis_checkpoint_with_mock):
        """Test listing checkpoints with limit."""
        # Save multiple checkpoints
        for i in range(10):
            checkpoint_data = {
                "thread_id": f"thread_{i}",
                "checkpoint_id": f"ckpt_{i}",
                "state": {"index": i},
                "metadata": {},
            }
            await redis_checkpoint_with_mock.save(
                checkpoint_data["thread_id"], checkpoint_data
            )

        # List with limit
        checkpoints = await redis_checkpoint_with_mock.list(limit=5)
        assert len(checkpoints) <= 5

    @pytest.mark.asyncio
    async def test_delete_checkpoint(self, redis_checkpoint_with_mock):
        """Test deleting a checkpoint."""
        checkpoint_data = {
            "thread_id": "thread_delete",
            "checkpoint_id": "ckpt_delete",
            "state": {},
            "metadata": {},
        }

        # Save
        await redis_checkpoint_with_mock.save(
            checkpoint_data["thread_id"], checkpoint_data
        )
        assert await redis_checkpoint_with_mock.load(checkpoint_data["thread_id"]) is not None

        # Delete
        await redis_checkpoint_with_mock.delete(checkpoint_data["thread_id"])

        # Verify deleted
        with pytest.raises(CheckpointNotFoundError):
            await redis_checkpoint_with_mock.load(checkpoint_data["thread_id"])

    @pytest.mark.asyncio
    async def test_update_checkpoint(self, redis_checkpoint_with_mock):
        """Test updating an existing checkpoint."""
        thread_id = "thread_update"

        # Save initial
        initial_data = {
            "thread_id": thread_id,
            "checkpoint_id": "ckpt_1",
            "state": {"version": 1},
            "metadata": {},
        }
        await redis_checkpoint_with_mock.save(thread_id, initial_data)

        # Update
        updated_data = {
            "thread_id": thread_id,
            "checkpoint_id": "ckpt_2",
            "state": {"version": 2},
            "metadata": {},
        }
        await redis_checkpoint_with_mock.save(thread_id, updated_data)

        # Verify update
        loaded = await redis_checkpoint_with_mock.load(thread_id)
        assert loaded["state"]["version"] == 2
        assert loaded["checkpoint_id"] == "ckpt_2"

    @pytest.mark.asyncio
    async def test_checkpoint_metadata(self, redis_checkpoint_with_mock):
        """Test checkpoint metadata handling."""
        checkpoint_data = {
            "thread_id": "thread_meta",
            "checkpoint_id": "ckpt_meta",
            "state": {},
            "metadata": {"step": 5, "timestamp": "2024-01-01T00:00:00", "user": "test_user"},
        }

        await redis_checkpoint_with_mock.save(checkpoint_data["thread_id"], checkpoint_data)

        loaded = await redis_checkpoint_with_mock.load(checkpoint_data["thread_id"])
        assert loaded["metadata"]["step"] == 5
        assert loaded["metadata"]["user"] == "test_user"

    @pytest.mark.asyncio
    async def test_checkpoint_with_complex_state(self, redis_checkpoint_with_mock):
        """Test checkpoint with complex nested state."""
        complex_state = {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ],
            "context": {"user_id": "123", "session_id": "abc"},
            "counters": {"messages_sent": 1, "tokens_used": 10},
        }

        checkpoint_data = {
            "thread_id": "thread_complex",
            "checkpoint_id": "ckpt_complex",
            "state": complex_state,
            "metadata": {},
        }

        await redis_checkpoint_with_mock.save(checkpoint_data["thread_id"], checkpoint_data)

        loaded = await redis_checkpoint_with_mock.load(checkpoint_data["thread_id"])
        assert loaded["state"]["messages"][0]["role"] == "user"
        assert loaded["state"]["context"]["user_id"] == "123"

    @pytest.mark.asyncio
    async def test_ttl_configuration(self, mock_redis):
        """Test TTL configuration."""
        # Create checkpoint with custom TTL
        checkpoint = RedisCheckpoint(conn=mock_redis, ttl=7200)

        assert checkpoint.ttl == 7200

    @pytest.mark.asyncio
    async def test_checkpoint_exists(self, redis_checkpoint_with_mock):
        """Test checking if checkpoint exists."""
        thread_id = "thread_exists"

        # Not exists initially
        assert await redis_checkpoint_with_mock.exists(thread_id) is False

        # Save
        checkpoint_data = {
            "thread_id": thread_id,
            "checkpoint_id": "ckpt_exists",
            "state": {},
            "metadata": {},
        }
        await redis_checkpoint_with_mock.save(thread_id, checkpoint_data)

        # Now exists
        assert await redis_checkpoint_with_mock.exists(thread_id) is True

    @pytest.mark.asyncio
    async def test_get_checkpoint_metadata(self, redis_checkpoint_with_mock):
        """Test getting only checkpoint metadata."""
        thread_id = "thread_metadata_only"

        checkpoint_data = {
            "thread_id": thread_id,
            "checkpoint_id": "ckpt_meta",
            "state": {"data": "value"},
            "metadata": {"created_at": "2024-01-01", "version": 2},
        }

        await redis_checkpoint_with_mock.save(thread_id, checkpoint_data)

        metadata = await redis_checkpoint_with_mock.get_metadata(thread_id)
        assert metadata is not None
        assert metadata["created_at"] == "2024-01-01"
        assert metadata["version"] == 2

    @pytest.mark.asyncio
    async def test_multiple_checkpoints_same_thread(self, redis_checkpoint_with_mock):
        """Test saving multiple checkpoints for same thread."""
        thread_id = "thread_multiple"

        # Save first checkpoint
        ckpt1 = {
            "thread_id": thread_id,
            "checkpoint_id": "ckpt_1",
            "state": {"step": 1},
            "metadata": {},
        }
        await redis_checkpoint_with_mock.save(thread_id, ckpt1)

        # Save second checkpoint (should overwrite)
        ckpt2 = {
            "thread_id": thread_id,
            "checkpoint_id": "ckpt_2",
            "state": {"step": 2},
            "metadata": {},
        }
        await redis_checkpoint_with_mock.save(thread_id, ckpt2)

        # Should have latest
        loaded = await redis_checkpoint_with_mock.load(thread_id)
        assert loaded["checkpoint_id"] == "ckpt_2"
        assert loaded["state"]["step"] == 2

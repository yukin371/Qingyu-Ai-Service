"""
SessionManager Tests

Tests for the SessionManager class which handles distributed session management.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from src.agent_runtime.session_manager import SessionManager, Session
from src.common.types.agent_types import AgentContext, Message, MessageRole


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_redis():
    """Mock Redis connection for testing."""
    return None


@pytest.fixture
def session_manager(mock_redis):
    """Create SessionManager instance."""
    return SessionManager(conn=mock_redis, ttl=3600)


@pytest.fixture
def sample_context():
    """Create sample AgentContext."""
    return AgentContext(
        agent_id="agent_123",
        user_id="user_456",
        session_id="session_789",
        conversation_history=[
            Message(role=MessageRole.USER, content="Hello"),
            Message(role=MessageRole.ASSISTANT, content="Hi there"),
        ],
    )


# =============================================================================
# Session Model Tests
# =============================================================================

class TestSessionModel:
    """Tests for Session data model."""

    def test_session_creation(self):
        """Test creating a Session instance."""
        session = Session(
            session_id="session_123",
            user_id="user_456",
            agent_id="agent_789",
            context=AgentContext(
                agent_id="agent_789",
                user_id="user_456",
                session_id="session_123",
            ),
        )

        assert session.session_id == "session_123"
        assert session.user_id == "user_456"
        assert session.agent_id == "agent_789"
        assert session.status == "active"

    def test_session_to_dict(self):
        """Test serializing session to dictionary."""
        session = Session(
            session_id="session_123",
            user_id="user_456",
            agent_id="agent_789",
        )

        data = session.model_dump()

        assert data["session_id"] == "session_123"
        assert data["user_id"] == "user_456"
        assert data["agent_id"] == "agent_789"

    def test_session_from_dict(self):
        """Test deserializing session from dictionary."""
        data = {
            "session_id": "session_123",
            "user_id": "user_456",
            "agent_id": "agent_789",
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        session = Session(**data)

        assert session.session_id == "session_123"
        assert session.user_id == "user_456"
        assert session.agent_id == "agent_789"
        assert session.status == "active"


# =============================================================================
# Session Creation Tests
# =============================================================================

class TestSessionCreation:
    """Tests for session creation."""

    @pytest.mark.asyncio
    async def test_create_session(self, session_manager):
        """Test creating a new session."""
        session = await session_manager.create_session(
            user_id="user_123",
            agent_id="agent_456",
        )

        assert session.session_id is not None
        assert session.user_id == "user_123"
        assert session.agent_id == "agent_456"
        assert session.status == "active"
        assert session.context is not None

    @pytest.mark.asyncio
    async def test_create_session_with_context(self, session_manager, sample_context):
        """Test creating a session with initial context."""
        session = await session_manager.create_session(
            user_id="user_123",
            agent_id="agent_456",
            context=sample_context,
        )

        assert session.session_id is not None
        assert session.context.conversation_history
        assert len(session.context.conversation_history) == 2

    @pytest.mark.asyncio
    async def test_create_session_with_metadata(self, session_manager):
        """Test creating a session with metadata."""
        session = await session_manager.create_session(
            user_id="user_123",
            agent_id="agent_456",
            metadata={"source": "web", "tier": "premium"},
        )

        assert session.metadata["source"] == "web"
        assert session.metadata["tier"] == "premium"

    @pytest.mark.asyncio
    async def test_create_session_generates_unique_ids(self, session_manager):
        """Test that each session gets a unique ID."""
        session1 = await session_manager.create_session("user_123", "agent_456")
        session2 = await session_manager.create_session("user_123", "agent_456")

        assert session1.session_id != session2.session_id


# =============================================================================
# Session Retrieval Tests
# =============================================================================

class TestSessionRetrieval:
    """Tests for session retrieval."""

    @pytest.mark.asyncio
    async def test_get_existing_session(self, session_manager):
        """Test retrieving an existing session."""
        created = await session_manager.create_session("user_123", "agent_456")
        retrieved = await session_manager.get_session(created.session_id)

        assert retrieved is not None
        assert retrieved.session_id == created.session_id
        assert retrieved.user_id == created.user_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, session_manager):
        """Test retrieving a non-existent session."""
        session = await session_manager.get_session("nonexistent_session")

        assert session is None

    @pytest.mark.asyncio
    async def test_get_session_by_user(self, session_manager):
        """Test retrieving sessions by user ID."""
        await session_manager.create_session("user_123", "agent_1")
        await session_manager.create_session("user_123", "agent_2")
        await session_manager.create_session("user_456", "agent_3")

        sessions = await session_manager.get_sessions_by_user("user_123")

        assert len(sessions) == 2
        assert all(s.user_id == "user_123" for s in sessions)

    @pytest.mark.asyncio
    async def test_session_exists(self, session_manager):
        """Test checking if a session exists."""
        created = await session_manager.create_session("user_123", "agent_456")

        assert await session_manager.session_exists(created.session_id) is True
        assert await session_manager.session_exists("nonexistent") is False


# =============================================================================
# Session Update Tests
# =============================================================================

class TestSessionUpdate:
    """Tests for session updates."""

    @pytest.mark.asyncio
    async def test_update_session_context(self, session_manager):
        """Test updating session context."""
        session = await session_manager.create_session("user_123", "agent_456")

        new_message = Message(role=MessageRole.USER, content="New message")
        session.context.add_message(new_message)

        await session_manager.update_session(session)

        retrieved = await session_manager.get_session(session.session_id)
        assert len(retrieved.context.conversation_history) == 1

    @pytest.mark.asyncio
    async def test_update_session_metadata(self, session_manager):
        """Test updating session metadata."""
        session = await session_manager.create_session("user_123", "agent_456")
        session.metadata["updated"] = True
        session.metadata["count"] = 42

        await session_manager.update_session(session)

        retrieved = await session_manager.get_session(session.session_id)
        assert retrieved.metadata["updated"] is True
        assert retrieved.metadata["count"] == 42

    @pytest.mark.asyncio
    async def test_update_session_status(self, session_manager):
        """Test updating session status."""
        session = await session_manager.create_session("user_123", "agent_456")
        session.status = "completed"

        await session_manager.update_session(session)

        retrieved = await session_manager.get_session(session.session_id)
        assert retrieved.status == "completed"


# =============================================================================
# Checkpoint Tests
# =============================================================================

class TestCheckpointManagement:
    """Tests for checkpoint management."""

    @pytest.mark.asyncio
    async def test_save_checkpoint(self, session_manager):
        """Test saving a checkpoint."""
        session = await session_manager.create_session("user_123", "agent_456")

        checkpoint_data = {
            "step": 5,
            "state": {"variable": "value"},
            "timestamp": datetime.utcnow().isoformat(),
        }

        checkpoint_id = await session_manager.save_checkpoint(
            session.session_id,
            checkpoint_data,
        )

        assert checkpoint_id is not None

    @pytest.mark.asyncio
    async def test_get_checkpoint(self, session_manager):
        """Test retrieving a checkpoint."""
        session = await session_manager.create_session("user_123", "agent_456")

        checkpoint_data = {
            "step": 5,
            "state": {"variable": "value"},
        }

        checkpoint_id = await session_manager.save_checkpoint(
            session.session_id,
            checkpoint_data,
        )

        retrieved = await session_manager.get_checkpoint(session.session_id, checkpoint_id)
        assert retrieved["step"] == 5
        assert retrieved["state"]["variable"] == "value"

    @pytest.mark.asyncio
    async def test_list_checkpoints(self, session_manager):
        """Test listing checkpoints for a session."""
        session = await session_manager.create_session("user_123", "agent_456")

        await session_manager.save_checkpoint(session.session_id, {"step": 1})
        await session_manager.save_checkpoint(session.session_id, {"step": 2})
        await session_manager.save_checkpoint(session.session_id, {"step": 3})

        checkpoints = await session_manager.list_checkpoints(session.session_id)

        assert len(checkpoints) == 3

    @pytest.mark.asyncio
    async def test_get_latest_checkpoint(self, session_manager):
        """Test getting the latest checkpoint."""
        session = await session_manager.create_session("user_123", "agent_456")

        await session_manager.save_checkpoint(session.session_id, {"step": 1})
        await session_manager.save_checkpoint(session.session_id, {"step": 2})

        latest = await session_manager.get_latest_checkpoint(session.session_id)

        assert latest["step"] == 2


# =============================================================================
# Session Lifecycle Tests
# =============================================================================

class TestSessionLifecycle:
    """Tests for session lifecycle management."""

    @pytest.mark.asyncio
    async def test_close_session(self, session_manager):
        """Test closing a session."""
        session = await session_manager.create_session("user_123", "agent_456")

        await session_manager.close_session(session.session_id)

        retrieved = await session_manager.get_session(session.session_id)
        assert retrieved.status == "closed"

    @pytest.mark.asyncio
    async def test_delete_session(self, session_manager):
        """Test deleting a session."""
        session = await session_manager.create_session("user_123", "agent_456")

        await session_manager.delete_session(session.session_id)

        retrieved = await session_manager.get_session(session.session_id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, session_manager):
        """Test cleaning up expired sessions."""
        # Create session manager with short TTL
        manager = SessionManager(conn=None, ttl=1)

        session1 = await manager.create_session("user_1", "agent_1")
        session2 = await manager.create_session("user_2", "agent_2")

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Create new session (not expired)
        session3 = await manager.create_session("user_3", "agent_3")

        # Cleanup expired
        await manager.cleanup_expired()

        assert await manager.session_exists(session1.session_id) is False
        assert await manager.session_exists(session2.session_id) is False
        assert await manager.session_exists(session3.session_id) is True


# =============================================================================
# Session Resume Tests
# =============================================================================

class TestSessionResume:
    """Tests for session resumption."""

    @pytest.mark.asyncio
    async def test_resume_session(self, session_manager, sample_context):
        """Test resuming a session from checkpoint."""
        session = await session_manager.create_session(
            "user_123",
            "agent_456",
            context=sample_context,
        )

        # Save checkpoint
        checkpoint_data = {
            "context": sample_context.model_dump(),
            "step": 10,
        }

        checkpoint_id = await session_manager.save_checkpoint(
            session.session_id,
            checkpoint_data,
        )

        # Resume from checkpoint
        resumed = await session_manager.resume_session(
            session.session_id,
            checkpoint_id,
        )

        assert resumed is not None
        assert resumed.session_id == session.session_id

    @pytest.mark.asyncio
    async def test_resume_from_latest_checkpoint(self, session_manager):
        """Test resuming from the latest checkpoint."""
        session = await session_manager.create_session("user_123", "agent_456")

        await session_manager.save_checkpoint(session.session_id, {"step": 1})
        await session_manager.save_checkpoint(session.session_id, {"step": 2})

        resumed = await session_manager.resume_from_latest(session.session_id)

        assert resumed is not None
        assert resumed.session_id == session.session_id


# =============================================================================
# Statistics Tests
# =============================================================================

class TestSessionStatistics:
    """Tests for session statistics."""

    @pytest.mark.asyncio
    async def test_get_session_count(self, session_manager):
        """Test getting total session count."""
        await session_manager.create_session("user_1", "agent_1")
        await session_manager.create_session("user_2", "agent_2")
        await session_manager.create_session("user_3", "agent_3")

        count = await session_manager.get_session_count()

        assert count == 3

    @pytest.mark.asyncio
    async def test_get_active_session_count(self, session_manager):
        """Test getting active session count."""
        session1 = await session_manager.create_session("user_1", "agent_1")
        session2 = await session_manager.create_session("user_2", "agent_2")
        session3 = await session_manager.create_session("user_3", "agent_3")

        await session_manager.close_session(session2.session_id)

        count = await session_manager.get_active_session_count()

        assert count == 2

    @pytest.mark.asyncio
    async def test_get_user_session_count(self, session_manager):
        """Test getting session count for a specific user."""
        await session_manager.create_session("user_1", "agent_1")
        await session_manager.create_session("user_1", "agent_2")
        await session_manager.create_session("user_2", "agent_3")

        count = await session_manager.get_user_session_count("user_1")

        assert count == 2


# =============================================================================
# Batch Operations Tests
# =============================================================================

class TestBatchOperations:
    """Tests for batch operations."""

    @pytest.mark.asyncio
    async def test_close_user_sessions(self, session_manager):
        """Test closing all sessions for a user."""
        await session_manager.create_session("user_1", "agent_1")
        await session_manager.create_session("user_1", "agent_2")
        await session_manager.create_session("user_2", "agent_3")

        await session_manager.close_user_sessions("user_1")

        sessions = await session_manager.get_sessions_by_user("user_1")
        assert all(s.status == "closed" for s in sessions)

    @pytest.mark.asyncio
    async def test_delete_user_sessions(self, session_manager):
        """Test deleting all sessions for a user."""
        await session_manager.create_session("user_1", "agent_1")
        await session_manager.create_session("user_1", "agent_2")
        await session_manager.create_session("user_2", "agent_3")

        count = await session_manager.delete_user_sessions("user_1")

        assert count == 2

        sessions = await session_manager.get_sessions_by_user("user_1")
        assert len(sessions) == 0

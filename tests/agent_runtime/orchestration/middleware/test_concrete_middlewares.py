"""
Concrete Middleware Tests

Tests for AuthMiddleware and LoggingMiddleware.
"""

import pytest
import logging
from unittest.mock import AsyncMock

from src.agent_runtime.orchestration.middleware.auth import AuthMiddleware
from src.agent_runtime.orchestration.middleware.logging import LoggingMiddleware
from src.agent_runtime.orchestration.middleware.base import (
    MiddlewareContext,
    MiddlewarePipeline,
    MiddlewareResult,
)
from src.common.types.agent_types import AgentContext


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_context():
    """Create sample AgentContext."""
    return AgentContext(
        agent_id="agent_123",
        user_id="user_456",
        session_id="session_789",
    )


# =============================================================================
# AuthMiddleware Tests
# =============================================================================

class TestAuthMiddleware:
    """Tests for AuthMiddleware."""

    @pytest.mark.asyncio
    async def test_authenticated_user_passes(self, sample_context):
        """Test that authenticated users pass."""
        auth = AuthMiddleware(authenticated_users={"user_456"})

        next_call = AsyncMock(return_value=MiddlewareResult(success=True))

        result = await auth.process(sample_context, next_call)

        assert result.success is True
        assert next_call.called

    @pytest.mark.asyncio
    async def test_unauthenticated_user_blocked(self, sample_context):
        """Test that unauthenticated users are blocked."""
        auth = AuthMiddleware(authenticated_users={"other_user"}, require_auth=True)

        next_call = AsyncMock(return_value=MiddlewareResult(success=True))

        result = await auth.process(sample_context, next_call)

        assert result.success is False
        assert result.error == "Authentication required"
        assert not next_call.called

    @pytest.mark.asyncio
    async def test_require_auth_false_allows_all(self, sample_context):
        """Test that require_auth=False allows unauthenticated users."""
        auth = AuthMiddleware(authenticated_users=set(), require_auth=False)

        next_call = AsyncMock(return_value=MiddlewareResult(success=True))

        result = await auth.process(sample_context, next_call)

        assert result.success is True
        assert next_call.called

    @pytest.mark.asyncio
    async def test_permission_check_pass(self, sample_context):
        """Test that permission check passes when user has permissions."""
        auth = AuthMiddleware(
            authenticated_users={"user_456"},
            permissions={"user_456": {"read", "write"}},
        )
        sample_context.metadata["required_permissions"] = ["read"]

        next_call = AsyncMock(return_value=MiddlewareResult(success=True))

        result = await auth.process(sample_context, next_call)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_permission_check_fails(self, sample_context):
        """Test that permission check fails when user lacks permissions."""
        auth = AuthMiddleware(
            authenticated_users={"user_456"},
            permissions={"user_456": {"read"}},
        )
        sample_context.metadata["required_permissions"] = ["write"]

        next_call = AsyncMock(return_value=MiddlewareResult(success=True))

        result = await auth.process(sample_context, next_call)

        assert result.success is False
        assert result.error == "Permission denied"

    def test_add_user(self):
        """Test adding a user."""
        auth = AuthMiddleware()
        auth.add_user("user_123", permissions=["read", "write"])

        assert "user_123" in auth.authenticated_users
        assert auth.permissions["user_123"] == {"read", "write"}

    def test_remove_user(self):
        """Test removing a user."""
        auth = AuthMiddleware(authenticated_users={"user_123"})
        auth.remove_user("user_123")

        assert "user_123" not in auth.authenticated_users


# =============================================================================
# LoggingMiddleware Tests
# =============================================================================

class TestLoggingMiddleware:
    """Tests for LoggingMiddleware."""

    @pytest.mark.asyncio
    async def test_logging_middleware_passes_through(self, sample_context):
        """Test that logging middleware passes through."""
        logging_mw = LoggingMiddleware()

        next_call = AsyncMock(return_value=MiddlewareResult(success=True))

        result = await logging_mw.process(sample_context, next_call)

        assert result.success is True
        assert next_call.called

    @pytest.mark.asyncio
    async def test_logging_middleware_logs_failure(self, sample_context):
        """Test that logging middleware logs failures."""
        logging_mw = LoggingMiddleware(log_level=logging.DEBUG)

        next_call = AsyncMock(
            return_value=MiddlewareResult(success=False, error="Test error")
        )

        result = await logging_mw.process(sample_context, next_call)

        assert result.success is False
        assert result.error == "Test error"

    @pytest.mark.asyncio
    async def test_logging_execution_time(self, sample_context):
        """Test that execution time is logged."""
        logging_mw = LoggingMiddleware(log_execution_time=True)

        async def slow_handler():
            import time
            time.sleep(0.01)
            return MiddlewareResult(success=True)

        result = await logging_mw.process(sample_context, slow_handler)

        assert result.success is True

    def test_logging_configuration(self):
        """Test logging middleware configuration."""
        mw = LoggingMiddleware(
            log_level=logging.DEBUG,
            log_body=True,
            log_execution_time=True,
        )

        assert mw.log_level == logging.DEBUG
        assert mw.log_body is True
        assert mw.log_execution_time is True


# =============================================================================
# Integration Tests
# =============================================================================

class TestMiddlewareIntegration:
    """Integration tests for multiple middlewares."""

    @pytest.mark.asyncio
    async def test_auth_and_logging_pipeline(self, sample_context):
        """Test auth and logging middleware together."""
        auth = AuthMiddleware(authenticated_users={"user_456"})
        logging_mw = LoggingMiddleware()

        pipeline = MiddlewarePipeline(middlewares=[auth, logging_mw])

        async def handler(ctx):
            return MiddlewareResult(success=True)

        result = await pipeline.execute(sample_context, handler)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_auth_blocks_before_logging(self, sample_context):
        """Test that auth blocks before logging reaches handler."""
        auth = AuthMiddleware(authenticated_users={"other_user"}, require_auth=True)
        logging_mw = LoggingMiddleware()

        pipeline = MiddlewarePipeline(middlewares=[auth, logging_mw])

        handler_called = False

        async def handler(ctx):
            nonlocal handler_called
            handler_called = True
            return MiddlewareResult(success=True)

        result = await pipeline.execute(sample_context, handler)

        assert result.success is False
        assert handler_called is False  # Handler should not be called

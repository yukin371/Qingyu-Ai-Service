"""
Middleware Chain Integration Tests

Tests for middleware pipeline execution including:
- Complete middleware chain execution
- Middleware short-circuit scenarios
- Error propagation through chain
- Context data passing between middlewares
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from src.agent_runtime.orchestration.middleware.base import (
    AgentMiddleware,
    MiddlewarePipeline,
    MiddlewareContext,
    MiddlewareResult,
)
from src.agent_runtime.orchestration.middleware.auth import AuthMiddleware
from src.agent_runtime.orchestration.middleware.logging import LoggingMiddleware
from src.agent_runtime.orchestration.middleware.cost import CostTrackingMiddleware
from src.agent_runtime.orchestration.middleware.rate_limit import RateLimitMiddleware
from src.agent_runtime.session_manager import AgentContext
from src.agent_runtime.orchestration.executor import ExecutionResult
from src.common.types.agent_types import AgentResult


# =============================================================================
# Helper Functions
# =============================================================================

def create_middleware_context(user_id: str, agent_id: str = "test_agent", session_id: str = "test_session") -> AgentContext:
    """Helper to create AgentContext for middleware tests."""
    return AgentContext(
        user_id=user_id,
        agent_id=agent_id,
        session_id=session_id,
        current_task="Test task",
    )


# =============================================================================
# Custom Test Middlewares
# =============================================================================

class TestMiddleware(AgentMiddleware):
    """Test middleware for integration testing."""

    def __init__(self, name: str, transform_response: bool = False, fail: bool = False, order: int = 100):
        super().__init__(name=name, order=order)
        self.transform_response = transform_response
        self.fail = fail
        self.called = False
        self.call_count = 0

    async def process(self, context: AgentContext, next_call) -> MiddlewareResult:
        self.called = True
        self.call_count += 1

        # Store test data in context metadata
        context.metadata[f"{self.name}_called"] = True

        if self.fail:
            return MiddlewareResult(success=False, error=f"{self.name} failed")

        # Call next middleware
        result = await next_call()

        if not result.success:
            return result

        # Transform response if enabled
        if self.transform_response and result.agent_result:
            response = result.agent_result.output or ""
            result.agent_result.output = f"{response} [{self.name}]"

        return result


class TransformMiddleware(AgentMiddleware):
    """Middleware that transforms context data."""

    def __init__(self):
        super().__init__(name="transform", order=50)

    async def process(self, context: AgentContext, next_call) -> MiddlewareResult:
        # Add data to context metadata
        context.metadata["transformed"] = True

        # Call next
        result = await next_call()

        # Modify response
        if result.success and result.agent_result:
            response = result.agent_result.output or ""
            result.agent_result.output = f"Transformed: {response}"

        return result


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def sample_agent_context():
    """Create sample agent context."""
    from src.agent_runtime.session_manager import AgentContext
    return AgentContext(
        user_id="test_user",
        agent_id="test_agent",
        session_id="test_session",
        current_task="Hello",
    )


@pytest.fixture
def sample_context(sample_agent_context):
    """Create sample middleware context."""
    return sample_agent_context


@pytest.fixture
def sample_handler():
    """Create sample request handler."""
    async def handler(context: AgentContext):
        return MiddlewareResult(success=True, agent_result=AgentResult(success=True, output="Handler response"))
    return handler


# =============================================================================
# Complete Middleware Chain Tests
# =============================================================================

class TestCompleteMiddlewareChain:
    """Tests for complete middleware chain execution."""

    @pytest.mark.asyncio
    async def test_all_middlewares_execute_in_order(self, sample_context, sample_handler):
        """Test all middlewares execute in correct order."""

        pipeline = MiddlewarePipeline()

        # Add middlewares with different orders
        m1 = TestMiddleware(name="first", order=10)
        m2 = TestMiddleware(name="second", order=20)
        m3 = TestMiddleware(name="third", order=30)

        pipeline.add(m1)
        pipeline.add(m2)
        pipeline.add(m3)

        # Execute
        result = await pipeline.execute(sample_context, sample_handler)

        assert result.success is True
        assert m1.called
        assert m2.called
        assert m3.called

        # Verify execution order
        execution_order = [
            k for k in sample_context.metadata.keys()
            if k.endswith("_called")
        ]
        assert execution_order == ["first_called", "second_called", "third_called"]

    @pytest.mark.asyncio
    async def test_middleware_data_propagation(self, sample_context, sample_handler):
        """Test data passing between middlewares."""

        pipeline = MiddlewarePipeline()

        m1 = TestMiddleware(name="m1", order=10)
        m2 = TestMiddleware(name="m2", order=20)
        pipeline.add(m1)
        pipeline.add(m2)

        # Execute
        result = await pipeline.execute(sample_context, sample_handler)

        assert result.success is True
        assert sample_context.metadata.get("m1_called") is True
        assert sample_context.metadata.get("m2_called") is True

    @pytest.mark.asyncio
    async def test_response_transformation_chain(self, sample_context):
        """Test response transformation through middleware chain."""

        pipeline = MiddlewarePipeline()

        # Add middlewares that transform response
        m1 = TestMiddleware(name="m1", transform_response=True, order=10)
        m2 = TestMiddleware(name="m2", transform_response=True, order=20)
        pipeline.add(m1)
        pipeline.add(m2)

        # Handler returns response
        async def handler(context: AgentContext):
            return MiddlewareResult(success=True, agent_result=AgentResult(success=True, output="Original"))

        result = await pipeline.execute(sample_context, handler)

        assert result.success is True
        # Transformations applied in reverse order (onion model)
        assert "[m2]" in result.agent_result.output
        assert "[m1]" in result.agent_result.output

    @pytest.mark.asyncio
    async def test_all_concrete_middlewares_together(self, sample_context, sample_handler):
        """Test all concrete middlewares work together."""

        pipeline = MiddlewarePipeline()

        # Add all concrete middlewares
        auth = AuthMiddleware(authenticated_users={"test_user"})
        logging = LoggingMiddleware(log_level=40)  # ERROR only
        cost = CostTrackingMiddleware()
        rate_limit = RateLimitMiddleware(requests_per_window=100, window_size=60)

        pipeline.add(auth)
        pipeline.add(logging)
        pipeline.add(cost)
        pipeline.add(rate_limit)

        # Execute with authenticated user
        result = await pipeline.execute(sample_context, sample_handler)

        assert result.success is True

        # Verify cost tracking (get_user_usage returns int - tokens used count)
        # The handler didn't specify tokens_used, so usage stays at 0
        usage = cost.get_user_usage("test_user")
        assert usage == 0  # No tokens were used in this test

        # Verify rate limiting
        count = rate_limit.get_user_request_count("test_user")
        assert count == 1


# =============================================================================
# Short-Circuit Tests
# =============================================================================

class TestMiddlewareShortCircuit:
    """Tests for middleware short-circuit scenarios."""

    @pytest.mark.asyncio
    async def test_auth_blocks_unauthenticated_user(self):
        """Test auth middleware blocks unauthenticated users."""

        pipeline = MiddlewarePipeline()

        auth = AuthMiddleware(authenticated_users={"alice", "bob"})
        m1 = TestMiddleware(name="m1", order=20)
        m2 = TestMiddleware(name="m2", order=30)

        pipeline.add(auth)
        pipeline.add(m1)
        pipeline.add(m2)

        # Create context for unauthenticated user
        context = create_middleware_context(
            user_id="eve",  # Not in authenticated_users
        )

        async def handler(context: AgentContext):
            return MiddlewareResult(success=True, agent_result=AgentResult(success=True, output="Should not reach"))

        result = await pipeline.execute(context, handler)

        # Should be blocked by auth
        assert result.success is False
        assert "authentication" in result.error.lower() or "unauthorized" in result.error.lower()

        # Later middlewares should not execute
        assert not m1.called
        assert not m2.called

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_over_limit(self, sample_context):
        """Test rate limiting blocks when over limit."""

        pipeline = MiddlewarePipeline()

        rate_limit = RateLimitMiddleware(requests_per_window=2, window_size=60)
        m1 = TestMiddleware(name="m1", order=20)

        pipeline.add(rate_limit)
        pipeline.add(m1)

        async def handler(context: AgentContext):
            return MiddlewareResult(success=True, agent_result=AgentResult(success=True, output="Response"))

        # First two requests should succeed
        for i in range(2):
            result = await pipeline.execute(sample_context, handler)
            assert result.success is True

        # Third request should be rate limited
        result = await pipeline.execute(sample_context, handler)
        assert result.success is False
        assert "rate limit" in result.error.lower()

    @pytest.mark.asyncio
    async def test_middleware_returns_error_early(self, sample_context):
        """Test middleware returning error stops chain."""

        pipeline = MiddlewarePipeline()

        m1 = TestMiddleware(name="m1", order=10)
        m_fail = TestMiddleware(name="fail_middleware", fail=True, order=20)
        m2 = TestMiddleware(name="m2", order=30)

        pipeline.add(m1)
        pipeline.add(m_fail)
        pipeline.add(m2)

        async def handler(context: AgentContext):
            return MiddlewareResult(success=True, agent_result=AgentResult(success=True, output="Should not reach"))

        result = await pipeline.execute(sample_context, handler)

        assert result.success is False
        assert "fail_middleware failed" in result.error

        # Middleware after failed one should not execute
        assert not m2.called

    @pytest.mark.asyncio
    async def test_cost_quota_enforcement(self, sample_context):
        """Test cost middleware enforces quota."""

        pipeline = MiddlewarePipeline()

        cost = CostTrackingMiddleware()
        # Quota is in tokens, set a low quota
        cost.set_user_quota("test_user", quota=10)  # Only 10 tokens

        m1 = TestMiddleware(name="m1", order=20)

        pipeline.add(cost)
        pipeline.add(m1)

        async def handler(context: AgentContext):
            # Simulate token usage - set on AgentResult
            return MiddlewareResult(
                success=True,
                agent_result=AgentResult(
                    success=True,
                    output="Response",
                    tokens_used={"total": 15, "prompt": 10, "completion": 5}
                ),
            )

        # First request should use tokens and be tracked
        result = await pipeline.execute(sample_context, handler)
        assert result.success is True

        # Check quota was enforced - usage should be tracked
        usage = cost.get_user_usage("test_user")
        assert usage == 15  # 15 tokens were used

        # Second request should be blocked (quota exceeded)
        result2 = await pipeline.execute(sample_context, handler)
        assert result2.success is False
        assert "quota exceeded" in result2.error.lower()


# =============================================================================
# Error Propagation Tests
# =============================================================================

class TestErrorPropagation:
    """Tests for error propagation through middleware chain."""

    @pytest.mark.asyncio
    async def test_handler_exception_propagates(self, sample_context):
        """Test exception in handler propagates through middlewares."""

        pipeline = MiddlewarePipeline()

        m1 = TestMiddleware(name="m1", order=10)
        m2 = TestMiddleware(name="m2", order=20)

        pipeline.add(m1)
        pipeline.add(m2)

        async def failing_handler(context: AgentContext):
            raise ValueError("Handler error")

        # Pipeline re-raises exceptions from handler
        with pytest.raises(ValueError, match="Handler error"):
            await pipeline.execute(sample_context, failing_handler)

        # Both middlewares should have been called (onion model)
        assert m1.called
        assert m2.called

    @pytest.mark.asyncio
    async def test_middleware_exception_propagates(self, sample_context):
        """Test exception in middleware propagates correctly."""

        pipeline = MiddlewarePipeline()

        class FailingMiddleware(AgentMiddleware):
            def __init__(self):
                super().__init__(name="failing", order=10)

            async def process(self, context, next_call):
                raise RuntimeError("Middleware error")

        pipeline.add(FailingMiddleware())
        pipeline.add(TestMiddleware(name="m2", order=20))

        async def handler(context: AgentContext):
            return MiddlewareResult(success=True, agent_result=AgentResult(success=True, output="Response"))

        # Pipeline re-raises exceptions from middleware
        with pytest.raises(RuntimeError, match="Middleware error"):
            await pipeline.execute(sample_context, handler)

    @pytest.mark.asyncio
    async def test_error_metadata_preserved(self, sample_context):
        """Test error metadata is preserved through chain."""

        pipeline = MiddlewarePipeline()

        m1 = TestMiddleware(name="m1", order=10)
        m2 = TestMiddleware(name="m2", order=20)

        pipeline.add(m1)
        pipeline.add(m2)

        async def handler(context: AgentContext):
            return MiddlewareResult(
                success=False,
                error="Handler error",
                metadata={"error_code": "TEST_001"}
            )

        result = await pipeline.execute(sample_context, handler)

        assert result.success is False
        assert result.metadata.get("error_code") == "TEST_001"


# =============================================================================
# Context Isolation Tests
# =============================================================================

class TestContextIsolation:
    """Tests for middleware context isolation."""

    @pytest.mark.asyncio
    async def test_context_not_shared_between_requests(self):
        """Test context is isolated between different requests."""

        pipeline = MiddlewarePipeline()

        m1 = TestMiddleware(name="m1", order=10)
        pipeline.add(m1)

        async def handler(context: AgentContext):
            # Add user-specific data to context metadata
            context.metadata["handler_data"] = f"value_for_{context.user_id}"
            return MiddlewareResult(success=True, agent_result=AgentResult(success=True, output="Response"))

        # First request
        context1 = create_middleware_context("user1", "agent1", "session1")

        result1 = await pipeline.execute(context1, handler)

        assert result1.success is True
        assert context1.metadata.get("handler_data") == "value_for_user1"

        # Verify context1 still has its original value (wasn't affected by context2)
        assert context1.metadata.get("handler_data") == "value_for_user1"

        # Second request should have isolated context
        context2 = create_middleware_context("user2", "agent2", "session2")

        result2 = await pipeline.execute(context2, handler)

        assert result2.success is True
        assert context2.metadata.get("handler_data") == "value_for_user2"

        # Verify contexts are independent
        assert context1.metadata.get("handler_data") == "value_for_user1"
        assert context2.metadata.get("handler_data") == "value_for_user2"
        assert context1.metadata.get("handler_data") != context2.metadata.get("handler_data")

    @pytest.mark.asyncio
    async def test_response_data_does_not_leak_to_request(self, sample_context):
        """Test response data doesn't leak into request context."""

        pipeline = MiddlewarePipeline()

        pipeline.add(TestMiddleware(name="m1", order=10))

        async def handler(context: AgentContext):
            # Verify metadata doesn't have response data yet
            assert "handler_meta" not in context.metadata

            return MiddlewareResult(
                success=True,
                agent_result=AgentResult(success=True, output="Response"),
                metadata={"handler_meta": "value"}
            )

        result = await pipeline.execute(sample_context, handler)

        assert result.success is True
        # Request context metadata should not have response metadata
        assert "handler_meta" not in sample_context.metadata


# =============================================================================
# Concurrent Execution Tests
# =============================================================================

class TestConcurrentMiddlewareExecution:
    """Tests for concurrent middleware execution."""

    @pytest.mark.asyncio
    async def test_concurrent_requests_separate_contexts(self):
        """Test concurrent requests maintain separate contexts."""

        pipeline = MiddlewarePipeline()

        m1 = TestMiddleware(name="m1", order=10)
        pipeline.add(m1)

        async def handler(context: AgentContext):
            # Simulate async work
            await asyncio.sleep(0.01)
            context.metadata["processed_by"] = context.user_id
            return MiddlewareResult(success=True, agent_result=AgentResult(success=True, output=f"Response for {context.user_id}"))

        # Create multiple concurrent requests
        contexts = [
            create_middleware_context(f"user{i}", "agent", f"session{i}")
            for i in range(5)
        ]

        # Execute concurrently
        tasks = [
            pipeline.execute(ctx, handler)
            for ctx in contexts
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(r.success for r in results)

        # Each context should have its own data
        for i, ctx in enumerate(contexts):
            assert ctx.metadata.get("processed_by") == f"user{i}"

    @pytest.mark.asyncio
    async def test_middleware_thread_safety(self):
        """Test middleware is thread-safe under concurrent load."""

        pipeline = MiddlewarePipeline()

        m1 = TestMiddleware(name="m1", order=10)
        m2 = TestMiddleware(name="m2", order=20)
        pipeline.add(m1)
        pipeline.add(m2)

        async def handler(context: AgentContext):
            await asyncio.sleep(0.001)
            return MiddlewareResult(success=True, agent_result=AgentResult(success=True, output="Response"))

        # Execute many concurrent requests
        tasks = []
        for i in range(50):
            context = create_middleware_context(f"user{i}", "agent", f"session{i}")
            tasks.append(pipeline.execute(context, handler))

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 50
        assert all(r.success for r in results)

        # Both middlewares should have been called for each request
        assert m1.call_count == 50
        assert m2.call_count == 50

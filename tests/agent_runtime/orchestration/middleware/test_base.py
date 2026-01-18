"""
Middleware Base Tests

Tests for the middleware base class and onion model implementation.
"""

import pytest
from typing import Any, Dict
from unittest.mock import AsyncMock, patch

from src.agent_runtime.orchestration.middleware.base import (
    AgentMiddleware,
    MiddlewareContext,
    MiddlewareResult,
    MiddlewarePipeline,
)
from src.common.types.agent_types import AgentContext, AgentResult


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


@pytest.fixture
def sample_result():
    """Create sample AgentResult."""
    return AgentResult(
        success=True,
        output="Test output",
    )


# =============================================================================
# MiddlewareContext Tests
# =============================================================================

class TestMiddlewareContext:
    """Tests for MiddlewareContext."""

    def test_create_context(self, sample_context):
        """Test creating a middleware context."""
        ctx = MiddlewareContext(
            agent_context=sample_context,
            metadata={"key": "value"},
        )

        assert ctx.agent_context == sample_context
        assert ctx.metadata["key"] == "value"
        assert ctx.request_data == {}
        assert ctx.response_data is None

    def test_set_request_data(self, sample_context):
        """Test setting request data."""
        ctx = MiddlewareContext(agent_context=sample_context)
        ctx.set("key1", "value1")
        ctx.set("key2", {"nested": "data"})

        assert ctx.get("key1") == "value1"
        assert ctx.get("key2") == {"nested": "data"}

    def test_get_with_default(self, sample_context):
        """Test getting values with defaults."""
        ctx = MiddlewareContext(agent_context=sample_context)

        assert ctx.get("nonexistent") is None
        assert ctx.get("nonexistent", "default") == "default"

    def test_set_response_data(self, sample_context):
        """Test setting response data."""
        ctx = MiddlewareContext(agent_context=sample_context)
        ctx.set_response({"status": "ok"})

        assert ctx.response_data == {"status": "ok"}

    def test_has_response(self, sample_context):
        """Test checking if response exists."""
        ctx = MiddlewareContext(agent_context=sample_context)

        assert ctx.has_response() is False

        ctx.set_response({"data": "value"})
        assert ctx.has_response() is True


# =============================================================================
# MiddlewareResult Tests
# =============================================================================

class TestMiddlewareResult:
    """Tests for MiddlewareResult."""

    def test_success_result(self, sample_result):
        """Test creating a success result."""
        result = MiddlewareResult(
            success=True,
            agent_result=sample_result,
        )

        assert result.success is True
        assert result.agent_result == sample_result
        assert result.error is None

    def test_error_result(self):
        """Test creating an error result."""
        result = MiddlewareResult(
            success=False,
            error="Test error",
        )

        assert result.success is False
        assert result.error == "Test error"
        assert result.agent_result is None

    def test_result_with_metadata(self, sample_result):
        """Test creating result with metadata."""
        result = MiddlewareResult(
            success=True,
            agent_result=sample_result,
            metadata={"middleware": "auth"},
        )

        assert result.metadata["middleware"] == "auth"


# =============================================================================
# AgentMiddleware Base Class Tests
# =============================================================================

class TestAgentMiddleware:
    """Tests for AgentMiddleware base class."""

    @pytest.mark.asyncio
    async def test_middleware_properties(self):
        """Test middleware properties."""
        class TestMiddleware(AgentMiddleware):
            def __init__(self):
                super().__init__(
                    name="test_middleware",
                    order=10,
                )

            async def process(self, context, next_call):
                return await next_call()

        middleware = TestMiddleware()

        assert middleware.name == "test_middleware"
        assert middleware.order == 10
        assert middleware.enabled is True

    @pytest.mark.asyncio
    async def test_middleware_enable_disable(self):
        """Test enabling and disabling middleware."""
        class TestMiddleware(AgentMiddleware):
            def __init__(self):
                super().__init__(name="test")

            async def process(self, context, next_call):
                return await next_call()

        middleware = TestMiddleware()

        assert middleware.enabled is True

        middleware.disable()
        assert middleware.enabled is False

        middleware.enable()
        assert middleware.enabled is True

    @pytest.mark.asyncio
    async def test_cannot_instantiate_abstract_middleware(self):
        """Test that abstract middleware cannot be instantiated."""
        # ABC prevents instantiation of classes with abstract methods
        class IncompleteMiddleware(AgentMiddleware):
            def __init__(self):
                super().__init__(name="incomplete")

        # TypeError is raised when trying to instantiate
        with pytest.raises(TypeError, match="abstract"):
            IncompleteMiddleware()


# =============================================================================
# Concrete Middleware Implementation for Testing
# =============================================================================

class AuthMiddleware(AgentMiddleware):
    """Simple auth middleware for testing."""

    def __init__(self):
        super().__init__(name="auth", order=10)

    async def process(self, context: AgentContext, next_call) -> MiddlewareResult:
        # Check if user is authenticated
        if context.metadata.get("authenticated"):
            return await next_call()
        else:
            return MiddlewareResult(
                success=False,
                error="Authentication required",
            )


class LoggingMiddleware(AgentMiddleware):
    """Simple logging middleware for testing."""

    def __init__(self):
        super().__init__(name="logging", order=100)
        self.logs = []

    async def process(self, context: AgentContext, next_call) -> MiddlewareResult:
        self.logs.append(f"Before: {context.agent_id}")
        result = await next_call()
        self.logs.append(f"After: {result.success}")
        return result


class TransformMiddleware(AgentMiddleware):
    """Middleware that transforms context."""

    def __init__(self):
        super().__init__(name="transform", order=50)

    async def process(self, context: AgentContext, next_call) -> MiddlewareResult:
        # Add metadata
        context.metadata["transformed"] = True
        return await next_call()


# =============================================================================
# Middleware Processing Tests
# =============================================================================

class TestMiddlewareProcessing:
    """Tests for middleware processing."""

    @pytest.mark.asyncio
    async def test_auth_middleware_passes(self, sample_context):
        """Test auth middleware allows authenticated requests."""
        middleware = AuthMiddleware()
        sample_context.metadata["authenticated"] = True

        next_call = AsyncMock(
            return_value=MiddlewareResult(success=True)
        )

        result = await middleware.process(sample_context, next_call)

        assert result.success is True
        assert next_call.called

    @pytest.mark.asyncio
    async def test_auth_middleware_blocks(self, sample_context):
        """Test auth middleware blocks unauthenticated requests."""
        middleware = AuthMiddleware()

        next_call = AsyncMock(
            return_value=MiddlewareResult(success=True)
        )

        result = await middleware.process(sample_context, next_call)

        assert result.success is False
        assert result.error == "Authentication required"
        assert not next_call.called

    @pytest.mark.asyncio
    async def test_logging_middleware_logs(self, sample_context):
        """Test logging middleware logs before and after."""
        middleware = LoggingMiddleware()

        next_call = AsyncMock(
            return_value=MiddlewareResult(success=True)
        )

        result = await middleware.process(sample_context, next_call)

        assert result.success is True
        assert len(middleware.logs) == 2
        assert middleware.logs[0] == f"Before: {sample_context.agent_id}"
        assert middleware.logs[1] == "After: True"

    @pytest.mark.asyncio
    async def test_transform_middleware_modifies_context(self, sample_context):
        """Test transform middleware modifies context."""
        middleware = TransformMiddleware()

        next_call = AsyncMock(
            return_value=MiddlewareResult(success=True)
        )

        await middleware.process(sample_context, next_call)

        assert sample_context.metadata.get("transformed") is True


# =============================================================================
# MiddlewarePipeline Tests
# =============================================================================

class TestMiddlewarePipeline:
    """Tests for MiddlewarePipeline."""

    def test_create_pipeline(self):
        """Test creating a pipeline."""
        auth = AuthMiddleware()
        logging = LoggingMiddleware()

        pipeline = MiddlewarePipeline(middlewares=[auth, logging])

        assert len(pipeline.middlewares) == 2

    def test_add_middleware(self):
        """Test adding middleware to pipeline."""
        pipeline = MiddlewarePipeline()

        assert len(pipeline.middlewares) == 0

        pipeline.add(AuthMiddleware())
        pipeline.add(LoggingMiddleware())

        assert len(pipeline.middlewares) == 2

    def test_sort_middleware_by_order(self):
        """Test that middleware are sorted by order."""
        class OrderTestMiddleware(AgentMiddleware):
            def __init__(self, name, order):
                super().__init__(name=name, order=order)
            async def process(self, context, next_call):
                return await next_call()

        m1 = OrderTestMiddleware(name="first", order=10)
        m2 = OrderTestMiddleware(name="second", order=5)
        m3 = OrderTestMiddleware(name="third", order=15)

        pipeline = MiddlewarePipeline(middlewares=[m1, m2, m3])

        # Should be sorted: m2 (5), m1 (10), m3 (15)
        assert pipeline.middlewares[0].name == "second"
        assert pipeline.middlewares[1].name == "first"
        assert pipeline.middlewares[2].name == "third"

    def test_remove_middleware(self):
        """Test removing middleware from pipeline."""
        auth = AuthMiddleware()
        pipeline = MiddlewarePipeline(middlewares=[auth])

        pipeline.remove("auth")

        assert len(pipeline.middlewares) == 0

    def test_get_middleware(self):
        """Test getting middleware by name."""
        auth = AuthMiddleware()
        pipeline = MiddlewarePipeline(middlewares=[auth])

        retrieved = pipeline.get("auth")

        assert retrieved is not None
        assert retrieved.name == "auth"

    @pytest.mark.asyncio
    async def test_pipeline_execution_all_pass(self, sample_context):
        """Test pipeline with all middleware passing."""
        auth = AuthMiddleware()
        transform = TransformMiddleware()
        logging = LoggingMiddleware()

        pipeline = MiddlewarePipeline(middlewares=[auth, transform, logging])
        sample_context.metadata["authenticated"] = True

        # Mock handler
        async def handler(ctx):
            return MiddlewareResult(success=True)

        result = await pipeline.execute(sample_context, handler)

        assert result.success is True
        assert len(logging.logs) == 2  # Before and after

    @pytest.mark.asyncio
    async def test_pipeline_execution_auth_blocks(self, sample_context):
        """Test pipeline with auth blocking."""
        auth = AuthMiddleware()
        transform = TransformMiddleware()
        logging = LoggingMiddleware()

        pipeline = MiddlewarePipeline(middlewares=[auth, transform, logging])
        # Don't set authenticated

        async def handler(ctx):
            return MiddlewareResult(success=True)

        result = await pipeline.execute(sample_context, handler)

        assert result.success is False
        assert result.error == "Authentication required"
        # Logging should not have been called
        assert len(logging.logs) == 0

    @pytest.mark.asyncio
    async def test_pipeline_with_disabled_middleware(self, sample_context):
        """Test that disabled middleware is skipped."""
        auth = AuthMiddleware()
        logging = LoggingMiddleware()
        logging.disable()

        pipeline = MiddlewarePipeline(middlewares=[auth, logging])
        sample_context.metadata["authenticated"] = True

        async def handler(ctx):
            return MiddlewareResult(success=True)

        result = await pipeline.execute(sample_context, handler)

        assert result.success is True
        # Logging should not have been called (disabled)
        assert len(logging.logs) == 0

    @pytest.mark.asyncio
    async def test_empty_pipeline(self, sample_context):
        """Test pipeline with no middleware."""
        pipeline = MiddlewarePipeline()

        async def handler(ctx):
            return MiddlewareResult(success=True)

        result = await pipeline.execute(sample_context, handler)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_pipeline_error_propagation(self, sample_context):
        """Test that errors are propagated through pipeline."""
        auth = AuthMiddleware()

        pipeline = MiddlewarePipeline(middlewares=[auth])
        sample_context.metadata["authenticated"] = True

        async def handler(ctx):
            raise ValueError("Handler error")

        with pytest.raises(ValueError, match="Handler error"):
            await pipeline.execute(sample_context, handler)


# =============================================================================
# Middleware Chain Tests
# =============================================================================

class TestMiddlewareChain:
    """Tests for middleware chaining."""

    @pytest.mark.asyncio
    async def test_onion_model_execution(self, sample_context):
        """Test that middleware executes in onion model order."""
        order = []

        class M1(AgentMiddleware):
            async def process(self, context, next_call):
                order.append("M1-before")
                result = await next_call()
                order.append("M1-after")
                return result

        class M2(AgentMiddleware):
            async def process(self, context, next_call):
                order.append("M2-before")
                result = await next_call()
                order.append("M2-after")
                return result

        pipeline = MiddlewarePipeline(middlewares=[M1(name="m1", order=1), M2(name="m2", order=2)])

        async def handler(ctx):
            order.append("handler")
            return MiddlewareResult(success=True)

        await pipeline.execute(sample_context, handler)

        # Should be: M1-before -> M2-before -> handler -> M2-after -> M1-after
        assert order == ["M1-before", "M2-before", "handler", "M2-after", "M1-after"]

    @pytest.mark.asyncio
    async def test_middleware_can_short_circuit(self, sample_context):
        """Test that middleware can short-circuit the chain."""
        order = []

        class M1(AgentMiddleware):
            async def process(self, context, next_call):
                order.append("M1")
                # Short circuit - don't call next
                return MiddlewareResult(success=False, error="Blocked")

        class M2(AgentMiddleware):
            async def process(self, context, next_call):
                order.append("M2")
                return await next_call()

        pipeline = MiddlewarePipeline(middlewares=[M1(name="m1", order=1), M2(name="m2", order=2)])

        async def handler(ctx):
            order.append("handler")
            return MiddlewareResult(success=True)

        result = await pipeline.execute(sample_context, handler)

        # M2 and handler should not be called
        assert order == ["M1"]
        assert result.success is False

    @pytest.mark.asyncio
    async def test_middleware_context_isolation(self, sample_context):
        """Test that middleware can modify context without affecting others."""
        m1_metadata = {}
        m2_metadata = {}

        class M1(AgentMiddleware):
            async def process(self, context, next_call):
                context.metadata["m1"] = "value1"
                m1_metadata.update(context.metadata)
                return await next_call()

        class M2(AgentMiddleware):
            async def process(self, context, next_call):
                # M1's changes should be visible
                m2_metadata.update(context.metadata)
                context.metadata["m2"] = "value2"
                return await next_call()

        pipeline = MiddlewarePipeline(middlewares=[M1(name="m1", order=1), M2(name="m2", order=2)])

        async def handler(ctx):
            return MiddlewareResult(success=True)

        await pipeline.execute(sample_context, handler)

        # M1's metadata should be visible to M2
        assert "m1" in m2_metadata
        assert m2_metadata["m1"] == "value1"

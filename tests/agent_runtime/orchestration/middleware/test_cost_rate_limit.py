"""
Cost and RateLimit Middleware Tests

Tests for CostTrackingMiddleware and RateLimitMiddleware.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock

from src.agent_runtime.orchestration.middleware.cost import CostTrackingMiddleware
from src.agent_runtime.orchestration.middleware.rate_limit import RateLimitMiddleware
from src.agent_runtime.orchestration.middleware.base import MiddlewareResult
from src.common.types.agent_types import AgentContext, AgentResult


@pytest.fixture
def sample_context():
    """Create sample AgentContext."""
    return AgentContext(
        agent_id="agent_123",
        user_id="user_456",
        session_id="session_789",
    )


# =============================================================================
# CostTrackingMiddleware Tests
# =============================================================================

class TestCostTrackingMiddleware:
    """Tests for CostTrackingMiddleware."""

    @pytest.mark.asyncio
    async def test_tracks_token_usage(self, sample_context):
        """Test that token usage is tracked."""
        cost_mw = CostTrackingMiddleware()

        next_call = AsyncMock(
            return_value=MiddlewareResult(
                success=True,
                agent_result=AgentResult(
                    success=True,
                    output="Response",
                    tokens_used={"total": 1000, "prompt": 700, "completion": 300},
                ),
            )
        )

        result = await cost_mw.process(sample_context, next_call)

        assert result.success is True
        assert "cost" in result.metadata
        assert result.metadata["tokens_used"]["total"] == 1000
        assert cost_mw.get_user_usage("user_456") == 1000

    @pytest.mark.asyncio
    async def test_calculates_cost(self, sample_context):
        """Test that cost is calculated correctly."""
        cost_mw = CostTrackingMiddleware()

        # Use a context with a model name that matches the price dict
        sample_context.agent_id = "gpt-4-agent"

        next_call = AsyncMock(
            return_value=MiddlewareResult(
                success=True,
                agent_result=AgentResult(
                    success=True,
                    output="Response",
                    tokens_used={"total": 1000, "prompt": 700, "completion": 300},
                ),
            )
        )

        result = await cost_mw.process(sample_context, next_call)

        # GPT-4 prices: $0.03/1K prompt, $0.06/1K completion
        # Expected: (700/1000 * 0.03) + (300/1000 * 0.06) = 0.021 + 0.018 = 0.039
        assert "cost" in result.metadata
        assert 0.03 <= result.metadata["cost"] <= 0.05  # Allow some tolerance

    @pytest.mark.asyncio
    async def test_enforces_quota(self, sample_context):
        """Test that quota is enforced."""
        cost_mw = CostTrackingMiddleware(user_quotas={"user_456": 500})
        cost_mw.user_usage["user_456"] = 500  # Already at quota

        next_call = AsyncMock(
            return_value=MiddlewareResult(success=True)
        )

        result = await cost_mw.process(sample_context, next_call)

        assert result.success is False
        assert "quota" in result.error.lower()
        assert not next_call.called

    def test_get_user_usage(self, sample_context):
        """Test getting user usage."""
        cost_mw = CostTrackingMiddleware()
        cost_mw.user_usage["user_456"] = 1000

        assert cost_mw.get_user_usage("user_456") == 1000
        assert cost_mw.get_user_usage("nonexistent") == 0

    def test_reset_user_usage(self, sample_context):
        """Test resetting user usage."""
        cost_mw = CostTrackingMiddleware()
        cost_mw.user_usage["user_456"] = 1000

        cost_mw.reset_user_usage("user_456")

        assert cost_mw.get_user_usage("user_456") == 0

    def test_set_user_quota(self):
        """Test setting user quota."""
        cost_mw = CostTrackingMiddleware()
        cost_mw.set_user_quota("user_123", 10000)

        assert cost_mw.user_quotas["user_123"] == 10000


# =============================================================================
# RateLimitMiddleware Tests
# =============================================================================

class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""

    @pytest.mark.asyncio
    async def test_allows_within_limit(self, sample_context):
        """Test that requests within limit are allowed."""
        rate_mw = RateLimitMiddleware(requests_per_window=10, window_size=1)

        next_call = AsyncMock(
            return_value=MiddlewareResult(success=True)
        )

        # Make 5 requests
        for _ in range(5):
            result = await rate_mw.process(sample_context, next_call)
            assert result.success is True

        assert next_call.call_count == 5

    @pytest.mark.asyncio
    async def test_blocks_over_limit(self, sample_context):
        """Test that requests over limit are blocked."""
        rate_mw = RateLimitMiddleware(requests_per_window=3, window_size=1)

        next_call = AsyncMock(
            return_value=MiddlewareResult(success=True)
        )

        # Make 5 requests (should be blocked after 3)
        results = []
        for _ in range(5):
            result = await rate_mw.process(sample_context, next_call)
            results.append(result.success)

        # First 3 should succeed, next 2 should fail
        assert results.count(True) == 3
        assert results.count(False) == 2
        assert next_call.call_count == 3

    @pytest.mark.asyncio
    async def test_window_sliding(self, sample_context):
        """Test that the sliding window works correctly."""
        rate_mw = RateLimitMiddleware(requests_per_window=2, window_size=1)

        next_call = AsyncMock(
            return_value=MiddlewareResult(success=True)
        )

        # Make 2 requests (at limit)
        result1 = await rate_mw.process(sample_context, next_call)
        result2 = await rate_mw.process(sample_context, next_call)

        assert result1.success is True
        assert result2.success is True

        # Third request should be blocked
        result3 = await rate_mw.process(sample_context, next_call)
        assert result3.success is False

        # Wait for window to slide
        await asyncio.sleep(1.1)

        # Now should be allowed again
        result4 = await rate_mw.process(sample_context, next_call)
        assert result4.success is True

    @pytest.mark.asyncio
    async def test_user_specific_limits(self, sample_context):
        """Test user-specific rate limits."""
        rate_mw = RateLimitMiddleware(
            requests_per_window=10,
            user_limits={"user_456": 2},  # Lower limit for this user
        )

        next_call = AsyncMock(
            return_value=MiddlewareResult(success=True)
        )

        # Make 3 requests for user_456
        results = []
        for _ in range(3):
            result = await rate_mw.process(sample_context, next_call)
            results.append(result.success)

        # First 2 should succeed, 3rd should fail
        assert results.count(True) == 2
        assert results.count(False) == 1

    def test_get_user_request_count(self, sample_context):
        """Test getting user request count."""
        rate_mw = RateLimitMiddleware(requests_per_window=10, window_size=1)

        # Record some requests
        rate_mw._record_request("user_123")
        rate_mw._record_request("user_123")
        rate_mw._record_request("user_123")

        count = rate_mw.get_user_request_count("user_123")
        assert count == 3

    def test_clear_user_history(self, sample_context):
        """Test clearing user history."""
        rate_mw = RateLimitMiddleware()
        rate_mw._record_request("user_123")

        assert rate_mw.get_user_request_count("user_123") == 1

        rate_mw.clear_user_history("user_123")

        assert rate_mw.get_user_request_count("user_123") == 0

    def test_set_user_limit(self):
        """Test setting user limit."""
        rate_mw = RateLimitMiddleware()
        rate_mw.set_user_limit("user_123", 100)

        assert rate_mw.user_limits["user_123"] == 100


# =============================================================================
# Integration Tests
# =============================================================================

class TestCostAndRateLimitIntegration:
    """Integration tests for cost and rate limiting."""

    @pytest.mark.asyncio
    async def test_cost_and_rate_limit_pipeline(self, sample_context):
        """Test cost tracking and rate limiting together."""
        cost_mw = CostTrackingMiddleware(user_quotas={"user_456": 10000})
        rate_mw = RateLimitMiddleware(requests_per_window=10)

        from src.agent_runtime.orchestration.middleware.base import MiddlewarePipeline

        pipeline = MiddlewarePipeline(middlewares=[rate_mw, cost_mw])

        next_call = AsyncMock(
            return_value=MiddlewareResult(
                success=True,
                agent_result=AgentResult(
                    success=True,
                    output="Response",
                    tokens_used={"total": 500},
                ),
            )
        )

        # Execute through pipeline
        handler = lambda ctx: next_call()

        result = await pipeline.execute(sample_context, handler)

        assert result.success is True

        # Rate limit should have tracked
        assert rate_mw.get_user_request_count("user_456") == 1

        # Cost tracking should have tracked
        assert cost_mw.get_user_usage("user_456") == 500

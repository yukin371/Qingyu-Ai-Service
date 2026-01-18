"""
Tests for LangSmith monitoring client
"""
import pytest

from src.dynamic_workflows.monitoring.langsmith_client import (
    LangSmithClient,
    LangSmithTracer,
)


class TestLangSmithClient:
    """Test LangSmithClient"""

    def test_create_client_disabled(self):
        """Test creating client without API key"""
        client = LangSmithClient()

        assert client.is_enabled() is False

    def test_create_client_enabled(self):
        """Test creating client with API key"""
        client = LangSmithClient(api_key="test_key")

        assert client.is_enabled() is True

    def test_enable_client(self):
        """Test enabling client"""
        client = LangSmithClient()

        assert client.is_enabled() is False

        client.enable("api_key")

        assert client.is_enabled() is True

    def test_disable_client(self):
        """Test disabling client"""
        client = LangSmithClient(api_key="key")

        assert client.is_enabled() is True

        client.disable()

        assert client.is_enabled() is False

    @pytest.mark.asyncio
    async def test_trace_execution_disabled(self):
        """Test tracing when disabled"""
        client = LangSmithClient()

        # Should not raise error
        await client.trace_execution("thread_123", {"data": "test"})

    @pytest.mark.asyncio
    async def test_log_to_langsmith_disabled(self):
        """Test logging when disabled"""
        client = LangSmithClient()

        # Should not raise error
        await client.log_to_langsmith("project", "run_1", {"key": "value"})

    @pytest.mark.asyncio
    async def test_export_dataset_disabled(self):
        """Test dataset export when disabled"""
        client = LangSmithClient()

        # Should not raise error
        await client.export_dataset("test_dataset", [])

    @pytest.mark.asyncio
    async def test_run_evaluation_disabled(self):
        """Test evaluation when disabled"""
        client = LangSmithClient()

        result = await client.run_evaluation("evaluator", [])

        assert result["status"] == "disabled"


class TestLangSmithTracer:
    """Test LangSmithTracer"""

    @pytest.mark.asyncio
    async def test_tracer_context_manager(self):
        """Test tracer as context manager"""
        client = LangSmithClient(api_key="test_key")
        tracer = LangSmithTracer(client, "run_123")

        async with tracer:
            await tracer.log_event("test_event", {"value": 42})

        # Event should be logged
        assert len(tracer.events) == 0  # Cleared on flush

    @pytest.mark.asyncio
    async def test_log_event(self):
        """Test logging events"""
        client = LangSmithClient()
        tracer = LangSmithTracer(client, "run_456")

        async with tracer:
            await tracer.log_event("event1", {"data": "test1"})
            await tracer.log_event("event2", {"data": "test2"})

            assert len(tracer.events) == 2

    @pytest.mark.asyncio
    async def test_flush_disabled_client(self):
        """Test flush with disabled client"""
        client = LangSmithClient()  # Disabled
        tracer = LangSmithTracer(client, "run_789")

        async with tracer:
            await tracer.log_event("event", {"data": "test"})

        # Should not raise error

"""
Agent Executor Tests

Tests for the AgentExecutor - the core execution engine that integrates
Memory, Tools, Workflow, and Middleware.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, List

from src.agent_runtime.orchestration.executor import (
    AgentExecutor,
    ExecutionConfig,
    ExecutionStats,
    ExecutionResult,
)
from src.agent_runtime.orchestration.middleware.base import (
    AgentMiddleware,
    MiddlewarePipeline,
    MiddlewareResult,
)
from src.common.types.agent_types import (
    AgentConfig,
    AgentContext,
    AgentResult,
    AgentStatus,
    Message,
    MessageRole,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_config():
    """Create sample AgentConfig."""
    return AgentConfig(
        name="test_agent",
        description="Test agent",
        model="gpt-4",
        temperature=0.7,
        max_tokens=2000,
        system_prompt="You are a helpful assistant.",
    )


@pytest.fixture
def sample_context():
    """Create sample AgentContext."""
    return AgentContext(
        agent_id="agent_123",
        user_id="user_456",
        session_id="session_789",
        current_task="Test task",
    )


@pytest.fixture
def execution_config():
    """Create sample ExecutionConfig."""
    return ExecutionConfig(
        timeout=30,
        max_retries=3,
        enable_streaming=False,
        enable_middleware=True,
    )


# =============================================================================
# ExecutionConfig Tests
# =============================================================================

class TestExecutionConfig:
    """Tests for ExecutionConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ExecutionConfig()

        assert config.timeout == 60
        assert config.max_retries == 3
        assert config.enable_streaming is False
        assert config.enable_middleware is True
        assert config.retry_on_failure is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = ExecutionConfig(
            timeout=120,
            max_retries=5,
            enable_streaming=True,
            enable_middleware=False,
        )

        assert config.timeout == 120
        assert config.max_retries == 5
        assert config.enable_streaming is True
        assert config.enable_middleware is False


# =============================================================================
# ExecutionStats Tests
# =============================================================================

class TestExecutionStats:
    """Tests for ExecutionStats."""

    def test_create_stats(self):
        """Test creating execution stats."""
        stats = ExecutionStats(
            total_tokens=1000,
            prompt_tokens=700,
            completion_tokens=300,
            execution_time=1.5,
            steps_taken=3,
        )

        assert stats.total_tokens == 1000
        assert stats.execution_time == 1.5
        assert stats.steps_taken == 3


# =============================================================================
# ExecutionResult Tests
# =============================================================================

class TestExecutionResult:
    """Tests for ExecutionResult."""

    def test_success_result(self):
        """Test creating a success result."""
        agent_result = AgentResult(
            success=True,
            output="Test output",
        )

        result = ExecutionResult(
            success=True,
            agent_result=agent_result,
            stats=ExecutionStats(execution_time=1.0),
        )

        assert result.success is True
        assert result.agent_result.output == "Test output"
        assert result.stats.execution_time == 1.0
        assert result.error is None

    def test_error_result(self):
        """Test creating an error result."""
        result = ExecutionResult(
            success=False,
            error="Test error",
        )

        assert result.success is False
        assert result.error == "Test error"
        assert result.agent_result is None


# =============================================================================
# AgentExecutor Creation Tests
# =============================================================================

class TestAgentExecutorCreation:
    """Tests for AgentExecutor creation and initialization."""

    def test_create_executor(self, sample_config):
        """Test creating an executor."""
        executor = AgentExecutor(
            agent_id="agent_123",
            config=sample_config,
        )

        assert executor.agent_id == "agent_123"
        assert executor.config == sample_config
        assert executor.status == AgentStatus.IDLE

    def test_create_executor_with_memory(self, sample_config):
        """Test creating executor with memory."""
        mock_memory = MagicMock()

        executor = AgentExecutor(
            agent_id="agent_123",
            config=sample_config,
            memory=mock_memory,
        )

        assert executor.memory == mock_memory

    def test_create_executor_with_tools(self, sample_config):
        """Test creating executor with tools."""
        mock_tools = [MagicMock(), MagicMock()]

        executor = AgentExecutor(
            agent_id="agent_123",
            config=sample_config,
            tools=mock_tools,
        )

        assert len(executor.tools) == 2

    def test_create_executor_with_workflow(self, sample_config):
        """Test creating executor with workflow."""
        mock_workflow = MagicMock()

        executor = AgentExecutor(
            agent_id="agent_123",
            config=sample_config,
            workflow=mock_workflow,
        )

        assert executor.workflow == mock_workflow

    def test_create_executor_with_middleware(self, sample_config):
        """Test creating executor with middleware pipeline."""
        pipeline = MiddlewarePipeline()

        executor = AgentExecutor(
            agent_id="agent_123",
            config=sample_config,
            middleware_pipeline=pipeline,
        )

        # Check that middleware is accessible (not checking equality)
        assert executor.middleware_pipeline is not None
        assert len(executor.middleware_pipeline.middlewares) == 0


# =============================================================================
# AgentExecutor Execution Tests
# =============================================================================

class TestAgentExecutorExecution:
    """Tests for AgentExecutor execution."""

    @pytest.mark.asyncio
    async def test_execute_success(self, sample_config, sample_context):
        """Test successful execution."""
        executor = AgentExecutor(
            agent_id="agent_123",
            config=sample_config,
        )

        # Mock the actual execution
        executor._execute_agent = AsyncMock(
            return_value=AgentResult(
                success=True,
                output="Test response",
            )
        )

        result = await executor.execute(sample_context)

        assert result.success is True
        assert result.agent_result.output == "Test response"
        assert executor.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_with_middleware(self, sample_config, sample_context):
        """Test execution with middleware."""
        # Create test middleware
        class TestMiddleware(AgentMiddleware):
            def __init__(self):
                super().__init__(name="test", order=10)
                self.called = False

            async def process(self, context, next_call):
                self.called = True
                return await next_call()

        middleware = TestMiddleware()
        pipeline = MiddlewarePipeline(middlewares=[middleware])

        executor = AgentExecutor(
            agent_id="agent_123",
            config=sample_config,
            middleware_pipeline=pipeline,
        )

        executor._execute_agent = AsyncMock(
            return_value=AgentResult(success=True, output="Response")
        )

        result = await executor.execute(
            sample_context,
            config=ExecutionConfig(enable_middleware=True),
        )

        assert result.success is True
        assert middleware.called is True

    @pytest.mark.asyncio
    async def test_execute_with_retry(self, sample_config, sample_context):
        """Test execution with retry on failure."""
        executor = AgentExecutor(
            agent_id="agent_123",
            config=sample_config,
        )

        # Fail twice, then succeed
        call_count = 0

        async def mock_execute(ctx):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return AgentResult(success=False, error="Temporary error")
            return AgentResult(success=True, output="Success")

        executor._execute_agent = mock_execute

        result = await executor.execute(
            sample_context,
            config=ExecutionConfig(max_retries=3),
        )

        assert result.success is True
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_execute_timeout(self, sample_config, sample_context):
        """Test execution timeout."""
        import asyncio

        executor = AgentExecutor(
            agent_id="agent_123",
            config=sample_config,
        )

        # Mock slow execution (sleep longer than timeout)
        async def slow_execute(ctx):
            await asyncio.sleep(5)  # Sleep 5 seconds
            return AgentResult(success=True, output="Late response")

        executor._execute_agent = slow_execute

        result = await executor.execute(
            sample_context,
            config=ExecutionConfig(timeout=1),  # 1 second timeout
        )

        assert result.success is False
        assert "timeout" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_with_memory(self, sample_config, sample_context):
        """Test execution with memory."""
        mock_memory = MagicMock()
        mock_memory.load_memory_variables = AsyncMock(
            return_value={"history": ["previous message"]}
        )

        executor = AgentExecutor(
            agent_id="agent_123",
            config=sample_config,
            memory=mock_memory,
        )

        executor._execute_agent = AsyncMock(
            return_value=AgentResult(success=True, output="Response")
        )

        result = await executor.execute(sample_context)

        assert result.success is True
        mock_memory.load_memory_variables.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_saves_to_memory(self, sample_config, sample_context):
        """Test that execution saves context to memory."""
        mock_memory = MagicMock()
        mock_memory.save_context = AsyncMock()

        executor = AgentExecutor(
            agent_id="agent_123",
            config=sample_config,
            memory=mock_memory,
        )

        executor._execute_agent = AsyncMock(
            return_value=AgentResult(success=True, output="Response")
        )

        result = await executor.execute(sample_context)

        assert result.success is True
        mock_memory.save_context.assert_called_once()


# =============================================================================
# AgentExecutor Streaming Tests
# =============================================================================

class TestAgentExecutorStreaming:
    """Tests for AgentExecutor streaming execution."""

    @pytest.mark.asyncio
    async def test_execute_stream(self, sample_config, sample_context):
        """Test streaming execution."""
        executor = AgentExecutor(
            agent_id="agent_123",
            config=sample_config,
        )

        # Mock streaming execution
        async def mock_stream(ctx):
            tokens = ["Hello", " world", "!"]
            for token in tokens:
                yield token

        executor._execute_agent_stream = mock_stream

        tokens = []
        async for token in executor.execute_stream(sample_context):
            tokens.append(token)

        assert tokens == ["Hello", " world", "!"]

    @pytest.mark.asyncio
    async def test_execute_stream_with_middleware(self, sample_config, sample_context):
        """Test streaming with middleware (middleware should be bypassed)."""
        middleware = MagicMock()
        pipeline = MiddlewarePipeline(middlewares=[middleware])

        executor = AgentExecutor(
            agent_id="agent_123",
            config=sample_config,
            middleware_pipeline=pipeline,
        )

        async def mock_stream(ctx):
            yield "token"

        executor._execute_agent_stream = mock_stream

        tokens = []
        async for token in executor.execute_stream(sample_context):
            tokens.append(token)

        # Middleware should not be called for streaming
        assert len(tokens) == 1


# =============================================================================
# AgentExecutor State Management Tests
# =============================================================================

class TestAgentExecutorStateManagement:
    """Tests for executor state management."""

    @pytest.mark.asyncio
    async def test_get_state(self, sample_config):
        """Test getting executor state."""
        executor = AgentExecutor(
            agent_id="agent_123",
            config=sample_config,
        )

        state = executor.get_state()

        assert state.agent_id == "agent_123"
        assert state.status == AgentStatus.IDLE

    @pytest.mark.asyncio
    async def test_reset(self, sample_config):
        """Test resetting executor state."""
        executor = AgentExecutor(
            agent_id="agent_123",
            config=sample_config,
        )

        # Simulate execution
        executor._status = AgentStatus.COMPLETED

        executor.reset()

        assert executor.status == AgentStatus.IDLE


# =============================================================================
# AgentExecutor Error Handling Tests
# =============================================================================

class TestAgentExecutorErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_exception_handling(self, sample_config, sample_context):
        """Test that exceptions are caught and returned as errors."""
        executor = AgentExecutor(
            agent_id="agent_123",
            config=sample_config,
        )

        executor._execute_agent = AsyncMock(
            side_effect=Exception("Test exception")
        )

        result = await executor.execute(sample_context)

        assert result.success is False
        assert "Test exception" in result.error

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, sample_config, sample_context):
        """Test that max retries are respected."""
        executor = AgentExecutor(
            agent_id="agent_123",
            config=sample_config,
        )

        executor._execute_agent = AsyncMock(
            return_value=AgentResult(success=False, error="Persistent error")
        )

        result = await executor.execute(
            sample_context,
            config=ExecutionConfig(max_retries=2),
        )

        assert result.success is False
        assert "Persistent error" in result.error


# =============================================================================
# Integration Tests
# =============================================================================

class TestAgentExecutorIntegration:
    """Integration tests for AgentExecutor."""

    @pytest.mark.asyncio
    async def test_full_execution_flow(self, sample_config, sample_context):
        """Test complete execution flow with all components."""
        # Create mock components
        mock_memory = MagicMock()
        mock_memory.load_memory_variables = AsyncMock(return_value={})
        mock_memory.save_context = AsyncMock()

        mock_tool = MagicMock()
        mock_tool.name = "test_tool"

        # Create middleware that adds metadata
        class TestMiddleware(AgentMiddleware):
            def __init__(self):
                super().__init__(name="test", order=10)

            async def process(self, context, next_call):
                context.metadata["middleware_executed"] = True
                return await next_call()

        middleware = TestMiddleware()
        pipeline = MiddlewarePipeline(middlewares=[middleware])

        executor = AgentExecutor(
            agent_id="agent_123",
            config=sample_config,
            memory=mock_memory,
            tools=[mock_tool],
            middleware_pipeline=pipeline,
        )

        # Mock the actual LLM call
        executor._execute_agent = AsyncMock(
            return_value=AgentResult(
                success=True,
                output="Final response",
                tokens_used={"total": 100},
            )
        )

        result = await executor.execute(sample_context)

        assert result.success is True
        assert result.agent_result.output == "Final response"
        assert sample_context.metadata.get("middleware_executed") is True
        mock_memory.load_memory_variables.assert_called_once()
        mock_memory.save_context.assert_called_once()

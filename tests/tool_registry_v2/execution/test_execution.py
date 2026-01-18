"""
Tests for ExecutionEngine and ErrorHandler

This module tests the execution engine and error handling functionality.
"""

import pytest
from typing import Any
from datetime import datetime

from src.common.interfaces.tool_interface import ITool
from src.common.types.tool_types import (
    ToolCategory,
    ToolExecutionContext,
    ToolExecutionResult,
    ToolMetadata,
    ToolRiskLevel,
    ToolStatus,
)
from src.tool_registry_v2.execution.execution_engine import ExecutionEngine
from src.tool_registry_v2.execution.error_handler import ErrorHandler


# =============================================================================
# Mock Tools for Testing
# =============================================================================

class SimpleTool(ITool):
    """Simple tool that succeeds."""

    def __init__(self, name: str = "simple_tool"):
        self.name = name
        self.call_count = 0

    async def execute(
        self,
        input_data: dict,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        self.call_count += 1
        return ToolExecutionResult(
            success=True,
            output=f"Result from {self.name}",
            tool_name=self.name,
            user_id=context.user_id,
            execution_time=0.01,
        )

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name=self.name,
            display_name=self.name.title(),
            description=f"Simple tool: {self.name}",
            category=ToolCategory.CUSTOM,
            risk_level=ToolRiskLevel.LOW,
            status=ToolStatus.ENABLED,
        )

    def validate_input(self, input_data: dict) -> bool:
        return isinstance(input_data, dict)

    async def initialize(self) -> None:
        pass

    async def cleanup(self) -> None:
        pass


class FailingTool(ITool):
    """Tool that fails then succeeds."""

    def __init__(self, name: str = "failing_tool", fail_count: int = 2):
        self.name = name
        self.fail_count = fail_count
        self.current_attempt = 0

    async def execute(
        self,
        input_data: dict,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        self.current_attempt += 1
        if self.current_attempt <= self.fail_count:
            raise Exception(f"Tool failed (attempt {self.current_attempt})")

        return ToolExecutionResult(
            success=True,
            output=f"Success on attempt {self.current_attempt}",
            tool_name=self.name,
            user_id=context.user_id,
            execution_time=0.01,
        )

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name=self.name,
            display_name=self.name.title(),
            description=f"Failing tool: {self.name}",
            category=ToolCategory.CUSTOM,
            risk_level=ToolRiskLevel.LOW,
            status=ToolStatus.ENABLED,
        )

    def validate_input(self, input_data: dict) -> bool:
        return True

    async def initialize(self) -> None:
        pass

    async def cleanup(self) -> None:
        pass


class SlowTool(ITool):
    """Tool that takes too long."""

    def __init__(self, name: str = "slow_tool", delay: float = 2.0):
        self.name = name
        self.delay = delay

    async def execute(
        self,
        input_data: dict,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        import asyncio
        await asyncio.sleep(self.delay)
        return ToolExecutionResult(
            success=True,
            output="Done",
            tool_name=self.name,
            user_id=context.user_id,
            execution_time=self.delay,
        )

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name=self.name,
            display_name=self.name.title(),
            description=f"Slow tool: {self.name}",
            category=ToolCategory.CUSTOM,
            risk_level=ToolRiskLevel.LOW,
            status=ToolStatus.ENABLED,
        )

    def validate_input(self, input_data: dict) -> bool:
        return True

    async def initialize(self) -> None:
        pass

    async def cleanup(self) -> None:
        pass


# =============================================================================
# ExecutionEngine Tests
# =============================================================================

class TestExecutionEngine:
    """Test cases for ExecutionEngine."""

    @pytest.fixture
    def engine(self):
        """Create a fresh engine instance for each test."""
        return ExecutionEngine()

    @pytest.fixture
    def execution_context(self):
        """Create an execution context."""
        return ToolExecutionContext(
            tool_name="test_tool",
            user_id="user_123",
            session_id="session_456",
        )

    @pytest.mark.asyncio
    async def test_execute_with_timeout_success(self, engine, execution_context):
        """Test execution with timeout (success case)."""
        tool = SimpleTool()

        result = await engine.execute_with_timeout(
            tool=tool,
            input_data={},
            context=execution_context,
            timeout=5,
        )

        assert result.success is True
        assert tool.call_count == 1

    @pytest.mark.asyncio
    async def test_execute_with_timeout_failure(self, engine, execution_context):
        """Test execution with timeout (timeout exceeded)."""
        tool = SlowTool(delay=5.0)

        result = await engine.execute_with_timeout(
            tool=tool,
            input_data={},
            context=execution_context,
            timeout=1,
        )

        assert result.success is False
        # Check for timeout error (case insensitive)
        assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_execute_async(self, engine, execution_context):
        """Test async execution."""
        tool = SimpleTool()

        result = await engine.execute_async(
            tool=tool,
            input_data={},
            context=execution_context,
        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_batch(self, engine, execution_context):
        """Test batch execution."""
        tools = [SimpleTool(f"tool_{i}") for i in range(3)]

        results = await engine.execute_batch(
            tools=tools,
            input_data_list=[{}, {}, {}],
            context=execution_context,
        )

        assert len(results) == 3
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_execute_with_retry(self, engine, execution_context):
        """Test execution with automatic retry."""
        tool = FailingTool(fail_count=2)

        result = await engine.execute_with_retry(
            tool=tool,
            input_data={},
            context=execution_context,
            max_retries=3,
        )

        assert result.success is True
        assert tool.current_attempt == 3  # 2 failures + 1 success


# =============================================================================
# ErrorHandler Tests
# =============================================================================

class TestErrorHandler:
    """Test cases for ErrorHandler."""

    @pytest.fixture
    def handler(self):
        """Create a fresh handler instance for each test."""
        return ErrorHandler()

    @pytest.fixture
    def execution_context(self):
        """Create an execution context."""
        return ToolExecutionContext(
            tool_name="test_tool",
            user_id="user_123",
            session_id="session_456",
        )

    @pytest.mark.asyncio
    async def test_auto_retry_success(self, handler, execution_context):
        """Test automatic retry on failure."""
        tool = FailingTool(fail_count=2)

        result = await handler.auto_retry(
            tool=tool,
            input_data={},
            context=execution_context,
            max_retries=3,
        )

        assert result.success is True
        assert tool.current_attempt == 3

    @pytest.mark.asyncio
    async def test_auto_retry_exhausted(self, handler, execution_context):
        """Test automatic retry exhausted."""
        tool = FailingTool(fail_count=5)

        result = await handler.auto_retry(
            tool=tool,
            input_data={},
            context=execution_context,
            max_retries=3,
        )

        assert result.success is False
        assert "exhausted" in result.error.lower()

    @pytest.mark.asyncio
    async def test_fallback_success(self, handler, execution_context):
        """Test fallback to alternative tool."""
        primary_tool = FailingTool(fail_count=10)
        fallback_tool = SimpleTool("fallback_tool")

        result = await handler.fallback(
            primary_tool=primary_tool,
            fallback_tool=fallback_tool,
            input_data={},
            context=execution_context,
        )

        assert result.success is True
        assert result.output == "Result from fallback_tool"

    @pytest.mark.asyncio
    async def test_fallback_both_fail(self, handler, execution_context):
        """Test fallback when both tools fail."""
        primary_tool = FailingTool("primary", fail_count=10)
        fallback_tool = FailingTool("fallback", fail_count=10)

        result = await handler.fallback(
            primary_tool=primary_tool,
            fallback_tool=fallback_tool,
            input_data={},
            context=execution_context,
        )

        assert result.success is False

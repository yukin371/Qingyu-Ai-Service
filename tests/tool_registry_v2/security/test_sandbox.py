"""
Tests for SandboxExecution

This module tests the sandbox execution functionality.
"""

import pytest
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from src.common.interfaces.tool_interface import ITool
from src.common.types.tool_types import (
    ToolCategory,
    ToolExecutionContext,
    ToolExecutionResult,
    ToolMetadata,
    ToolRiskLevel,
    ToolStatus,
)
from src.tool_registry_v2.security.sandbox import SandboxExecution


# =============================================================================
# Mock Tool for Testing
# =============================================================================

class SimpleTool(ITool):
    """Simple mock tool."""

    def __init__(self, name: str = "simple_tool"):
        self.name = name

    async def execute(
        self,
        input_data: dict,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        return ToolExecutionResult(
            success=True,
            output=f"Executed {self.name}",
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


# =============================================================================
# SandboxExecution Tests
# =============================================================================

class TestSandboxExecution:
    """Test cases for SandboxExecution."""

    @pytest.fixture
    def sandbox(self):
        """Create a fresh sandbox instance for each test."""
        return SandboxExecution()

    @pytest.fixture
    def mock_tool(self):
        """Create a mock tool."""
        return SimpleTool("test_tool")

    @pytest.fixture
    def execution_context(self):
        """Create an execution context."""
        return ToolExecutionContext(
            tool_name="test_tool",
            user_id="user_123",
            session_id="session_456",
        )

    @pytest.mark.asyncio
    async def test_execute_local(self, sandbox, mock_tool, execution_context):
        """Test local execution (default mode)."""
        result = await sandbox.execute_in_docker(
            tool=mock_tool,
            input_data={"test": "data"},
            context=execution_context,
        )

        assert result.success is True
        assert result.output == "Executed test_tool"
        assert result.tool_name == "test_tool"

    @pytest.mark.asyncio
    async def test_execute_with_timeout(self, sandbox, mock_tool, execution_context):
        """Test execution with timeout."""
        result = await sandbox.execute_in_docker(
            tool=mock_tool,
            input_data={},
            context=execution_context,
            timeout=5,
        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_in_e2b(self, sandbox, mock_tool, execution_context):
        """Test E2B execution (should fall back to local for MVP)."""
        result = await sandbox.execute_in_e2b(
            tool=mock_tool,
            input_data={},
            context=execution_context,
        )

        # MVP: E2B falls back to local execution
        assert result.success is True

    @pytest.mark.asyncio
    async def test_is_available(self, sandbox):
        """Test checking if sandbox is available."""
        # Local execution is always available
        assert await sandbox.is_docker_available() is True
        # E2B is not configured in MVP
        assert await sandbox.is_e2b_available() is False

    @pytest.mark.asyncio
    async def test_execute_failing_tool(self, sandbox, execution_context):
        """Test executing a tool that fails."""
        class FailingTool(ITool):
            def __init__(self):
                self.name = "failing_tool"

            async def execute(self, input_data: dict, context: ToolExecutionContext):
                raise Exception("Intentional failure")

            def get_metadata(self) -> ToolMetadata:
                return ToolMetadata(
                    name="failing_tool",
                    display_name="Failing Tool",
                    description="A tool that always fails",
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

        failing_tool = FailingTool()
        result = await sandbox.execute_in_docker(
            tool=failing_tool,
            input_data={},
            context=execution_context,
        )

        assert result.success is False
        assert "Intentional failure" in result.error

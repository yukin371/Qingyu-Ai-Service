"""
Tests for ToolRegistryV2

This module tests the central tool registry functionality.
"""

import pytest
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from src.common.exceptions import (
    ToolNotFoundError,
    ToolExecutionError,
    ToolRegistrationError,
)
from src.common.interfaces.tool_interface import ITool
from src.common.types.agent_types import AgentContext
from src.common.types.tool_types import (
    ToolCategory,
    ToolExecutionContext,
    ToolExecutionResult,
    ToolMetadata,
    ToolRiskLevel,
    ToolStatus,
    ToolStats,
)


# =============================================================================
# Mock Tool Implementation
# =============================================================================

class MockTool(ITool):
    """Mock tool for testing."""

    def __init__(
        self,
        name: str = "test_tool",
        execute_result: Any = "success",
        category: ToolCategory = ToolCategory.CUSTOM,
    ):
        self.name = name
        self.execute_result = execute_result
        self._category = category
        self.initialized = False
        self.cleaned_up = False

    async def execute(
        self,
        input_data: dict,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        return ToolExecutionResult(
            success=True,
            output=self.execute_result,
            tool_name=self.name,
            user_id=context.user_id,
            execution_time=0.1,
        )

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name=self.name,
            display_name=self.name.replace("_", " ").title(),
            description=f"Test tool: {self.name}",
            category=self._category,
            risk_level=ToolRiskLevel.LOW,
            status=ToolStatus.ENABLED,
        )

    def validate_input(self, input_data: dict) -> bool:
        return isinstance(input_data, dict)

    async def initialize(self) -> None:
        self.initialized = True

    async def cleanup(self) -> None:
        self.cleaned_up = True


class FailingMockTool(ITool):
    """Mock tool that always fails."""

    def __init__(self, name: str = "failing_tool"):
        self.name = name
        self.initialized = False

    async def execute(
        self,
        input_data: dict,
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        raise ToolExecutionError(
            tool_name=self.name,
            reason="Intentional failure for testing",
        )

    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name=self.name,
            display_name=self.name.replace("_", " ").title(),
            description="Failing test tool",
            category=ToolCategory.CUSTOM,
            risk_level=ToolRiskLevel.LOW,
            status=ToolStatus.ENABLED,
        )

    def validate_input(self, input_data: dict) -> bool:
        return True

    async def initialize(self) -> None:
        self.initialized = True

    async def cleanup(self) -> None:
        pass


# =============================================================================
# ToolRegistryV2 Tests
# =============================================================================

class TestToolRegistryV2:
    """Test cases for ToolRegistryV2."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry instance for each test."""
        # Import here to avoid initialization issues
        from src.tool_registry_v2.registry import ToolRegistryV2
        return ToolRegistryV2()

    @pytest.fixture
    def mock_tool(self):
        """Create a mock tool."""
        return MockTool("test_tool")

    @pytest.fixture
    def agent_context(self):
        """Create an agent context."""
        return AgentContext(
            agent_id="agent_123",
            user_id="user_456",
            session_id="session_789",
        )

    @pytest.mark.asyncio
    async def test_register_tool(self, registry, mock_tool):
        """Test registering a tool."""
        await registry.register_tool(mock_tool)

        # Verify tool was registered
        tool = await registry.get_tool("test_tool")
        assert tool is not None
        assert tool.name == "test_tool"
        assert mock_tool.initialized

    @pytest.mark.asyncio
    async def test_register_duplicate_tool(self, registry, mock_tool):
        """Test registering a duplicate tool raises an error."""
        await registry.register_tool(mock_tool)

        with pytest.raises(ToolRegistrationError):
            await registry.register_tool(mock_tool)

    @pytest.mark.asyncio
    async def test_unregister_tool(self, registry, mock_tool):
        """Test unregistering a tool."""
        await registry.register_tool(mock_tool)
        await registry.unregister_tool("test_tool")

        # Verify tool was unregistered
        tool = await registry.get_tool("test_tool")
        assert tool is None
        assert mock_tool.cleaned_up

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_tool(self, registry):
        """Test unregistering a nonexistent tool raises an error."""
        with pytest.raises(ToolNotFoundError):
            await registry.unregister_tool("nonexistent_tool")

    @pytest.mark.asyncio
    async def test_get_tool(self, registry, mock_tool):
        """Test getting a tool by name."""
        await registry.register_tool(mock_tool)

        tool = await registry.get_tool("test_tool")
        assert tool is not None
        assert tool.name == "test_tool"

    @pytest.mark.asyncio
    async def test_get_nonexistent_tool(self, registry):
        """Test getting a nonexistent tool returns None."""
        tool = await registry.get_tool("nonexistent_tool")
        assert tool is None

    @pytest.mark.asyncio
    async def test_list_tools(self, registry):
        """Test listing all tools."""
        # Register multiple tools
        tools = [
            MockTool("tool1"),
            MockTool("tool2"),
            MockTool("tool3"),
        ]

        for tool in tools:
            await registry.register_tool(tool)

        # List tools
        tool_list = await registry.list_tools()
        assert len(tool_list) == 3
        tool_names = [info.metadata.name for info in tool_list]
        assert "tool1" in tool_names
        assert "tool2" in tool_names
        assert "tool3" in tool_names

    @pytest.mark.asyncio
    async def test_list_tools_by_category(self, registry):
        """Test listing tools filtered by category."""
        # Register tools with different categories
        tool1 = MockTool("search_tool", category=ToolCategory.SEARCH)
        tool2 = MockTool("db_tool", category=ToolCategory.DATABASE)

        await registry.register_tool(tool1)
        await registry.register_tool(tool2)

        # List tools by category
        search_tools = await registry.list_tools(category=ToolCategory.SEARCH)
        assert len(search_tools) == 1
        assert search_tools[0].metadata.name == "search_tool"

    @pytest.mark.asyncio
    async def test_execute_safe(self, registry, mock_tool, agent_context):
        """Test executing a tool safely."""
        await registry.register_tool(mock_tool)

        result = await registry.execute_safe(
            tool_name="test_tool",
            input_data={"test": "data"},
            context=agent_context,
        )

        assert result.success is True
        assert result.output == "success"
        assert result.tool_name == "test_tool"

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self, registry, agent_context):
        """Test executing a nonexistent tool raises an error."""
        with pytest.raises(ToolNotFoundError):
            await registry.execute_safe(
                tool_name="nonexistent_tool",
                input_data={},
                context=agent_context,
            )

    @pytest.mark.asyncio
    async def test_execute_failing_tool(self, registry, agent_context):
        """Test executing a tool that fails."""
        failing_tool = FailingMockTool("failing_tool")
        await registry.register_tool(failing_tool)

        result = await registry.execute_safe(
            tool_name="failing_tool",
            input_data={},
            context=agent_context,
        )

        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_check_permission_default_allow(self, registry):
        """Test that permission check allows by default."""
        # By default, all users should have access to all tools
        has_permission = await registry.check_permission(
            tool_name="test_tool",
            user_id="user_123",
        )
        assert has_permission is True

    @pytest.mark.asyncio
    async def test_tool_stats_updated(self, registry, mock_tool, agent_context):
        """Test that tool statistics are updated after execution."""
        await registry.register_tool(mock_tool)

        # Execute tool
        await registry.execute_safe(
            tool_name="test_tool",
            input_data={},
            context=agent_context,
        )

        # Check stats
        tool_list = await registry.list_tools()
        test_tool_info = next(
            (info for info in tool_list if info.metadata.name == "test_tool"),
            None,
        )
        assert test_tool_info is not None
        assert test_tool_info.stats.total_calls == 1
        assert test_tool_info.stats.successful_calls == 1
        assert test_tool_info.stats.last_called_at is not None

    @pytest.mark.asyncio
    async def test_concurrent_registration(self, registry):
        """Test registering multiple tools concurrently."""
        import asyncio

        tools = [MockTool(f"tool_{i}") for i in range(10)]

        # Register all tools concurrently
        await asyncio.gather(*[
            registry.register_tool(tool) for tool in tools
        ])

        # Verify all tools were registered
        tool_list = await registry.list_tools()
        assert len(tool_list) == 10

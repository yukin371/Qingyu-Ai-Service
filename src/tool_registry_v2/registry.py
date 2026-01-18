"""
Tool Registry V2 - Central Registry

This module provides the central tool registry that manages tool registration,
retrieval, and safe execution with proper error handling and security checks.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.common.exceptions import (
    ToolExecutionError,
    ToolNotFoundError,
    ToolRegistrationError,
    ToolValidationError,
)
from src.common.interfaces.tool_interface import ITool
from src.common.types.agent_types import AgentContext
from src.common.types.tool_types import (
    ToolCategory,
    ToolExecutionContext,
    ToolExecutionResult,
    ToolInfo,
    ToolMetadata,
    ToolSchema,
    ToolStats,
)


# =============================================================================
# Tool Registry V2
# =============================================================================

class ToolRegistryV2:
    """
    Central tool registry with safe execution and security controls.

    The registry manages:
    - Tool registration and lifecycle
    - Tool retrieval with permission checking
    - Safe execution with error handling
    - Tool statistics tracking
    - Concurrent access support

    Example:
        ```python
        registry = ToolRegistryV2()

        # Register a tool
        await registry.register_tool(my_tool)

        # Execute safely
        result = await registry.execute_safe(
            tool_name="search",
            input_data={"query": "test"},
            context=AgentContext(
                user_id="user_123",
                session_id="session_abc",
                agent_id="agent_xyz",
            ),
        )
        ```
    """

    def __init__(self):
        """Initialize the tool registry."""
        # Thread-safe tool storage
        self._tools: Dict[str, ITool] = {}
        self._tool_stats: Dict[str, ToolStats] = {}
        self._lock = asyncio.Lock()

        # Permission system (whitelist/blacklist, ACL)
        # For MVP: allow all by default
        self._permission_whitelist: Optional[List[str]] = None  # None = allow all
        self._permission_blacklist: List[str] = []
        self._acl: Dict[str, List[str]] = {}  # user_id -> [tool_names]

        # TODO: Will integrate with security, auth, and execution modules later
        # from .security.permission_policy import PermissionPolicy
        # from .authentication.credential_manager import CredentialManager
        # from .execution.execution_engine import ExecutionEngine

    # -------------------------------------------------------------------------
    # Tool Registration
    # -------------------------------------------------------------------------

    async def register_tool(self, tool: ITool) -> None:
        """
        Register a tool.

        Args:
            tool: Tool instance to register

        Raises:
            ToolRegistrationError: If tool registration fails
        """
        async with self._lock:
            metadata = tool.get_metadata()
            tool_name = metadata.name

            # Check if tool already exists
            if tool_name in self._tools:
                raise ToolRegistrationError(
                    tool_name=tool_name,
                    reason=f"Tool '{tool_name}' is already registered",
                )

            # Validate tool metadata
            self._validate_metadata(metadata)

            # Initialize the tool
            try:
                await tool.initialize()
            except Exception as e:
                raise ToolRegistrationError(
                    tool_name=tool_name,
                    reason=f"Tool initialization failed: {str(e)}",
                ) from e

            # Store the tool
            self._tools[tool_name] = tool
            self._tool_stats[tool_name] = ToolStats()

    async def unregister_tool(self, tool_name: str) -> None:
        """
        Unregister a tool.

        Args:
            tool_name: Name of the tool to unregister

        Raises:
            ToolNotFoundError: If tool is not found
        """
        async with self._lock:
            if tool_name not in self._tools:
                raise ToolNotFoundError(
                    tool_name=tool_name,
                )

            # Get tool and cleanup
            tool = self._tools.pop(tool_name)
            self._tool_stats.pop(tool_name, None)

            try:
                await tool.cleanup()
            except Exception as e:
                # Log error but don't raise
                pass

    # -------------------------------------------------------------------------
    # Tool Retrieval
    # -------------------------------------------------------------------------

    async def get_tool(
        self,
        tool_name: str,
        user_id: Optional[str] = None,
    ) -> Optional[ITool]:
        """
        Get a tool by name.

        Args:
            tool_name: Name of the tool
            user_id: Optional user ID for permission checking

        Returns:
            ITool: Tool instance if found and accessible, None otherwise
        """
        async with self._lock:
            tool = self._tools.get(tool_name)

            # Check permission if user_id is provided
            if tool and user_id:
                if not await self.check_permission(tool_name, user_id):
                    return None

            return tool

    async def list_tools(
        self,
        user_id: Optional[str] = None,
        category: Optional[ToolCategory] = None,
    ) -> List[ToolInfo]:
        """
        List all available tools.

        Args:
            user_id: Optional user ID for filtering by permission
            category: Optional category filter

        Returns:
            List[ToolInfo]: List of tool information objects
        """
        async with self._lock:
            tool_infos = []

            for tool_name, tool in self._tools.items():
                # Check permission
                if user_id and not await self.check_permission(tool_name, user_id):
                    continue

                # Check category filter
                metadata = tool.get_metadata()
                if category and metadata.category != category:
                    continue

                # Create tool info
                tool_infos.append(ToolInfo(
                    metadata=metadata,
                    tool_schema=ToolSchema(),  # TODO: Extract from tool if available
                    stats=self._tool_stats[tool_name],
                    is_builtin=False,  # TODO: Mark builtin tools appropriately
                ))

            return tool_infos

    # -------------------------------------------------------------------------
    # Safe Execution
    # -------------------------------------------------------------------------

    async def execute_safe(
        self,
        tool_name: str,
        input_data: Dict[str, Any],
        context: AgentContext,
    ) -> ToolExecutionResult:
        """
        Safely execute a tool with proper error handling and security checks.

        Args:
            tool_name: Name of the tool to execute
            input_data: Input data for the tool
            context: Agent context including user and session info

        Returns:
            ToolExecutionResult: Result of the execution

        Raises:
            ToolNotFoundError: If tool is not found
        """
        start_time = datetime.utcnow()

        # Get tool
        tool = await self.get_tool(tool_name, context.user_id)
        if not tool:
            raise ToolNotFoundError(tool_name=tool_name)

        try:
            # Validate input
            if not tool.validate_input(input_data):
                raise ToolValidationError(
                    tool_name=tool_name,
                    validation_issue="Input validation failed",
                )

            # Create execution context
            exec_context = ToolExecutionContext(
                tool_name=tool_name,
                user_id=context.user_id,
                session_id=context.session_id,
                agent_id=context.agent_id,
                input_data=input_data,
                timeout=tool.get_metadata().timeout,
                use_sandbox=False,  # TODO: Integrate with sandbox
            )

            # Execute tool
            result = await tool.execute(input_data, exec_context)

            # Update stats
            await self._update_stats(tool_name, True, datetime.utcnow() - start_time)

            return result

        except Exception as e:
            # Update stats with failure
            await self._update_stats(tool_name, False, datetime.utcnow() - start_time, str(e))

            # Return error result
            return ToolExecutionResult(
                success=False,
                error=str(e),
                tool_name=tool_name,
                user_id=context.user_id,
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
            )

    # -------------------------------------------------------------------------
    # Permission Checking
    # -------------------------------------------------------------------------

    async def check_permission(
        self,
        tool_name: str,
        user_id: str,
    ) -> bool:
        """
        Check if a user has permission to use a tool.

        Args:
            tool_name: Name of the tool
            user_id: ID of the user

        Returns:
            bool: True if user has permission, False otherwise
        """
        # Check blacklist
        if tool_name in self._permission_blacklist:
            return False

        # Check whitelist (if configured)
        if self._permission_whitelist is not None:
            if tool_name not in self._permission_whitelist:
                return False

        # Check ACL (user-specific permissions)
        if user_id in self._acl:
            if tool_name not in self._acl[user_id]:
                return False

        return True

    # -------------------------------------------------------------------------
    # Permission Management
    # -------------------------------------------------------------------------

    def set_whitelist(self, tool_names: Optional[List[str]]) -> None:
        """
        Set the permission whitelist.

        Args:
            tool_names: List of allowed tool names, or None to allow all
        """
        self._permission_whitelist = tool_names

    def set_blacklist(self, tool_names: List[str]) -> None:
        """
        Set the permission blacklist.

        Args:
            tool_names: List of forbidden tool names
        """
        self._permission_blacklist = tool_names

    def set_user_permissions(self, user_id: str, tool_names: List[str]) -> None:
        """
        Set user-specific tool permissions.

        Args:
            user_id: ID of the user
            tool_names: List of tools the user can access
        """
        self._acl[user_id] = tool_names

    # -------------------------------------------------------------------------
    # Statistics Tracking
    # -------------------------------------------------------------------------

    async def _update_stats(
        self,
        tool_name: str,
        success: bool,
        execution_time,
        error: Optional[str] = None,
    ) -> None:
        """
        Update tool statistics after execution.

        Args:
            tool_name: Name of the tool
            success: Whether execution was successful
            execution_time: Time taken to execute
            error: Error message if execution failed
        """
        async with self._lock:
            if tool_name not in self._tool_stats:
                return

            stats = self._tool_stats[tool_name]
            stats.total_calls += 1
            stats.last_called_at = datetime.utcnow()

            if success:
                stats.successful_calls += 1
            else:
                stats.failed_calls += 1
                stats.last_error = error

            # Update average execution time
            total_time = stats.avg_execution_time * (stats.total_calls - 1)
            stats.avg_execution_time = (total_time + execution_time.total_seconds()) / stats.total_calls

    def get_stats(self, tool_name: str) -> Optional[ToolStats]:
        """
        Get statistics for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            ToolStats: Tool statistics if found, None otherwise
        """
        return self._tool_stats.get(tool_name)

    # -------------------------------------------------------------------------
    # Validation Helpers
    # -------------------------------------------------------------------------

    def _validate_metadata(self, metadata: ToolMetadata) -> None:
        """
        Validate tool metadata.

        Args:
            metadata: Metadata to validate

        Raises:
            ToolValidationError: If validation fails
        """
        # Check required fields
        if not metadata.name:
            raise ToolValidationError(
                tool_name=metadata.name or "unknown",
                validation_issue="Tool name is required",
            )

        if not metadata.description:
            raise ToolValidationError(
                tool_name=metadata.name,
                validation_issue="Tool description is required",
            )

        # Validate timeout
        if metadata.timeout <= 0:
            raise ToolValidationError(
                tool_name=metadata.name,
                validation_issue="Tool timeout must be positive",
            )

    # -------------------------------------------------------------------------
    # Lifecycle Management
    # -------------------------------------------------------------------------

    async def cleanup_all(self) -> None:
        """
        Cleanup all registered tools.

        This should be called when shutting down the service.
        """
        async with self._lock:
            for tool_name, tool in self._tools.items():
                try:
                    await tool.cleanup()
                except Exception as e:
                    # Log error but continue with other tools
                    pass

            self._tools.clear()
            self._tool_stats.clear()

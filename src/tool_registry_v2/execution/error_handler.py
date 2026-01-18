"""
Error Handler

This module provides error handling for tool execution:
- Automatic retry with exponential backoff
- Fallback to alternative tools
- Error logging and metrics
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, Optional

from src.common.interfaces.tool_interface import ITool
from src.common.types.tool_types import (
    ToolExecutionContext,
    ToolExecutionResult,
)


# =============================================================================
# Error Handler
# =============================================================================

class ErrorHandler:
    """
    Error handler for tool execution.

    Features:
    - Automatic retry with exponential backoff
    - Fallback to alternative tools
    - Error logging and metrics

    Example:
        ```python
        handler = ErrorHandler()

        # Retry on failure
        result = await handler.auto_retry(
            tool=my_tool,
            input_data={"query": "test"},
            context=execution_context,
            max_retries=3,
        )

        # Fallback to alternative tool
        result = await handler.fallback(
            primary_tool=primary_tool,
            fallback_tool=fallback_tool,
            input_data={"query": "test"},
            context=execution_context,
        )
        ```
    """

    def __init__(self):
        """Initialize the error handler."""
        # TODO: Add metrics/logging
        self._error_counts: Dict[str, int] = {}
        self._retry_counts: Dict[str, int] = {}

    # -------------------------------------------------------------------------
    # Retry Mechanism
    # -------------------------------------------------------------------------

    async def auto_retry(
        self,
        tool: ITool,
        input_data: Dict[str, Any],
        context: ToolExecutionContext,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
        timeout: int = 300,
    ) -> ToolExecutionResult:
        """
        Execute a tool with automatic retry on failure.

        Uses exponential backoff between retries.

        Args:
            tool: Tool to execute
            input_data: Input data for the tool
            context: Execution context
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay before first retry in seconds
            backoff_factor: Multiplier for delay after each retry
            timeout: Timeout for each attempt in seconds

        Returns:
            ToolExecutionResult: Result of the execution
        """
        last_error = None
        delay = initial_delay
        tool_name = tool.get_metadata().name

        for attempt in range(max_retries + 1):  # +1 for initial attempt
            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    tool.execute(input_data, context),
                    timeout=timeout,
                )

                # If successful, update metrics and return
                if result.success:
                    if attempt > 0:
                        self._retry_counts[tool_name] = self._retry_counts.get(tool_name, 0) + attempt
                    return result

                # If unsuccessful, store error and continue to retry
                last_error = result.error

            except asyncio.TimeoutError:
                last_error = f"Execution timed out after {timeout} seconds"

            except Exception as e:
                last_error = str(e)

            # If this was the last attempt, don't delay
            if attempt < max_retries:
                # Wait before retry with exponential backoff
                await asyncio.sleep(delay)
                delay *= backoff_factor

        # All retries exhausted
        self._error_counts[tool_name] = self._error_counts.get(tool_name, 0) + 1

        return ToolExecutionResult(
            success=False,
            error=f"Retry exhausted after {max_retries + 1} attempts. Last error: {last_error}",
            tool_name=tool_name,
            user_id=context.user_id,
            execution_time=0.0,
        )

    # -------------------------------------------------------------------------
    # Fallback Mechanism
    # -------------------------------------------------------------------------

    async def fallback(
        self,
        primary_tool: ITool,
        fallback_tool: ITool,
        input_data: Dict[str, Any],
        context: ToolExecutionContext,
        timeout: int = 300,
    ) -> ToolExecutionResult:
        """
        Execute a tool with fallback to alternative tool.

        Args:
            primary_tool: Primary tool to execute
            fallback_tool: Fallback tool if primary fails
            input_data: Input data for the tool
            context: Execution context
            timeout: Timeout for each attempt in seconds

        Returns:
            ToolExecutionResult: Result of the execution
        """
        primary_name = primary_tool.get_metadata().name
        fallback_name = fallback_tool.get_metadata().name

        # Try primary tool
        try:
            result = await asyncio.wait_for(
                primary_tool.execute(input_data, context),
                timeout=timeout,
            )

            if result.success:
                return result

        except Exception as e:
            # Log error and continue to fallback
            pass

        # Try fallback tool
        try:
            result = await asyncio.wait_for(
                fallback_tool.execute(input_data, context),
                timeout=timeout,
            )

            # Update context to indicate fallback was used
            result.metadata = result.metadata or {}
            result.metadata["fallback_used"] = True
            result.metadata["primary_tool"] = primary_name
            result.metadata["fallback_tool"] = fallback_name

            return result

        except Exception as e:
            # Both tools failed
            return ToolExecutionResult(
                success=False,
                error=f"Both primary and fallback tools failed. Fallback error: {str(e)}",
                tool_name=primary_name,
                user_id=context.user_id,
                execution_time=0.0,
            )

    # -------------------------------------------------------------------------
    # Error Metrics
    # -------------------------------------------------------------------------

    def get_error_count(self, tool_name: str) -> int:
        """
        Get the number of errors for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            int: Number of errors
        """
        return self._error_counts.get(tool_name, 0)

    def get_retry_count(self, tool_name: str) -> int:
        """
        Get the number of retries for a tool.

        Args:
            tool_name: Name of the tool

        Returns:
            int: Number of retries
        """
        return self._retry_counts.get(tool_name, 0)

    def reset_metrics(self, tool_name: Optional[str] = None) -> None:
        """
        Reset error metrics.

        Args:
            tool_name: Name of the tool, or None to reset all
        """
        if tool_name:
            self._error_counts.pop(tool_name, None)
            self._retry_counts.pop(tool_name, None)
        else:
            self._error_counts.clear()
            self._retry_counts.clear()

    def get_all_metrics(self) -> Dict[str, Dict[str, int]]:
        """
        Get all error metrics.

        Returns:
            Dict: Tool name -> {"errors": int, "retries": int}
        """
        metrics = {}
        for tool_name in set(list(self._error_counts.keys()) + list(self._retry_counts.keys())):
            metrics[tool_name] = {
                "errors": self._error_counts.get(tool_name, 0),
                "retries": self._retry_counts.get(tool_name, 0),
            }
        return metrics

"""
Execution Engine

This module provides the unified execution layer for tools:
- Timeout control
- Async execution
- Batch execution
- Retry mechanisms
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List

from src.common.interfaces.tool_interface import ITool
from src.common.types.tool_types import (
    ToolExecutionContext,
    ToolExecutionResult,
)
from .error_handler import ErrorHandler


# =============================================================================
# Execution Engine
# =============================================================================

class ExecutionEngine:
    """
    Unified execution engine for tools.

    Features:
    - Timeout control
    - Async execution
    - Batch execution
    - Integration with error handler for retry and fallback

    Example:
        ```python
        engine = ExecutionEngine()

        # Execute with timeout
        result = await engine.execute_with_timeout(
            tool=my_tool,
            input_data={"query": "test"},
            context=execution_context,
            timeout=30,
        )

        # Execute batch
        results = await engine.execute_batch(
            tools=[tool1, tool2, tool3],
            input_data_list=[data1, data2, data3],
            context=execution_context,
        )
        ```
    """

    def __init__(self):
        """Initialize the execution engine."""
        self.error_handler = ErrorHandler()

    # -------------------------------------------------------------------------
    # Execution Methods
    # -------------------------------------------------------------------------

    async def execute_with_timeout(
        self,
        tool: ITool,
        input_data: Dict[str, Any],
        context: ToolExecutionContext,
        timeout: int,
    ) -> ToolExecutionResult:
        """
        Execute a tool with timeout control.

        Args:
            tool: Tool to execute
            input_data: Input data for the tool
            context: Execution context
            timeout: Timeout in seconds

        Returns:
            ToolExecutionResult: Result of the execution
        """
        start_time = datetime.utcnow()

        try:
            result = await asyncio.wait_for(
                tool.execute(input_data, context),
                timeout=timeout,
            )
            return result

        except asyncio.TimeoutError:
            return ToolExecutionResult(
                success=False,
                error=f"Tool execution timed out after {timeout} seconds",
                tool_name=context.tool_name,
                user_id=context.user_id,
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
            )

        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=str(e),
                tool_name=context.tool_name,
                user_id=context.user_id,
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
            )

    async def execute_async(
        self,
        tool: ITool,
        input_data: Dict[str, Any],
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        """
        Execute a tool asynchronously.

        Args:
            tool: Tool to execute
            input_data: Input data for the tool
            context: Execution context

        Returns:
            ToolExecutionResult: Result of the execution
        """
        start_time = datetime.utcnow()

        try:
            result = await tool.execute(input_data, context)
            return result

        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=str(e),
                tool_name=context.tool_name,
                user_id=context.user_id,
                execution_time=(datetime.utcnow() - start_time).total_seconds(),
            )

    async def execute_batch(
        self,
        tools: List[ITool],
        input_data_list: List[Dict[str, Any]],
        context: ToolExecutionContext,
        timeout: int = 300,
    ) -> List[ToolExecutionResult]:
        """
        Execute multiple tools in parallel.

        Args:
            tools: List of tools to execute
            input_data_list: List of input data for each tool
            context: Execution context
            timeout: Timeout for each tool in seconds

        Returns:
            List[ToolExecutionResult]: Results of the executions

        Raises:
            ValueError: If tools and input_data_list have different lengths
        """
        if len(tools) != len(input_data_list):
            raise ValueError(
                f"Number of tools ({len(tools)}) must match "
                f"number of input data ({len(input_data_list)})"
            )

        # Create tasks for parallel execution
        tasks = [
            self.execute_with_timeout(
                tool=tool,
                input_data=input_data,
                context=context,
                timeout=timeout,
            )
            for tool, input_data in zip(tools, input_data_list)
        ]

        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions in results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    ToolExecutionResult(
                        success=False,
                        error=str(result),
                        tool_name=tools[i].get_metadata().name,
                        user_id=context.user_id,
                        execution_time=0.0,
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    async def execute_with_retry(
        self,
        tool: ITool,
        input_data: Dict[str, Any],
        context: ToolExecutionContext,
        max_retries: int = 3,
        timeout: int = 300,
    ) -> ToolExecutionResult:
        """
        Execute a tool with automatic retry on failure.

        Args:
            tool: Tool to execute
            input_data: Input data for the tool
            context: Execution context
            max_retries: Maximum number of retry attempts
            timeout: Timeout for each attempt in seconds

        Returns:
            ToolExecutionResult: Result of the execution
        """
        return await self.error_handler.auto_retry(
            tool=tool,
            input_data=input_data,
            context=context,
            max_retries=max_retries,
            timeout=timeout,
        )

    async def execute_with_fallback(
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
        return await self.error_handler.fallback(
            primary_tool=primary_tool,
            fallback_tool=fallback_tool,
            input_data=input_data,
            context=context,
            timeout=timeout,
        )

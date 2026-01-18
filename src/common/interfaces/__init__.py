"""
Common Interfaces Module

This module contains abstract interface definitions for core components.
These interfaces define the contracts that implementations must follow,
enabling dependency injection and testing.

Interface Categories:
- memory_interface: Memory storage and message history interfaces
- tool_interface: Tool definition and registry interfaces
- workflow_interface: Workflow management interfaces
- executor_interface: Agent and workflow executor interfaces

All interfaces use ABC (Abstract Base Classes) and define clear contracts
for implementations. This enables:
- Easy mocking and testing
- Multiple implementation strategies
- Runtime type checking with mypy
- Clear separation of concerns
"""

# Note: Interfaces will be imported when individual modules are implemented
# This avoids circular imports and allows gradual implementation

__all__ = [
    # Memory interfaces
    "IMemoryStore",
    "IMessageHistory",
    # Tool interfaces
    "ITool",
    "IToolRegistry",
    # Workflow interfaces
    "IWorkflow",
    "IWorkflowEngine",
    # Executor interfaces
    "IExecutor",
    "IAgentExecutor",
    "IWorkflowExecutor",
]

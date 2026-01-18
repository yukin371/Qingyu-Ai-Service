"""
Common Types Module

This module contains type definitions used across the AI service.
All types are designed to be compatible with LangChain 1.2.x and Pydantic v2.

Type Categories:
- agent_types: Agent configuration, context, result, and message types
- event_types: Event system types for system and tool events
- memory_types: Memory storage and retrieval types
- workflow_types: Workflow state and configuration types
- tool_types: Tool registry, execution, and authentication types

These types ensure type safety and consistency across the application,
particularly when working with LangChain's type system and serialization.
"""

# Note: Types will be imported when individual modules are implemented
# This allows gradual implementation and avoids import errors

__all__ = [
    # Agent types
    "AgentConfig",
    "AgentContext",
    "AgentResult",
    "Message",
    "MessageRole",
    # Event types
    "EventType",
    "SystemEvent",
    "ToolEvent",
    "EventPriority",
    # Memory types
    "MemoryConfig",
    "MemoryEntry",
    "UserProfile",
    "MemoryType",
    # Workflow types
    "WorkflowState",
    "WorkflowConfig",
    "WorkflowStatus",
    # Tool types
    "ToolCategory",
    "ToolRiskLevel",
    "ToolStatus",
    "ToolMetadata",
    "ToolSchema",
    "ToolInfo",
    "ToolStats",
    "ToolExecutionContext",
    "ToolExecutionResult",
    "CredentialType",
    "Credential",
    "PermissionType",
    "AccessControlEntry",
]

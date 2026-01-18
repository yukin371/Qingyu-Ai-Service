"""
Agent Type Definitions

This module defines all types related to AI agents, including configuration,
context, results, and messaging. All types are compatible with LangChain 1.2.x
and Pydantic v2.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Enums
# =============================================================================

class MessageRole(str, Enum):
    """Role of the message sender."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    FUNCTION = "function"


class AgentStatus(str, Enum):
    """Current status of an agent."""

    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    WAITING = "waiting"
    ERROR = "error"
    COMPLETED = "completed"


class AgentCapability(str, Enum):
    """Capabilities that an agent can possess."""

    TEXT_GENERATION = "text_generation"
    TOOL_USE = "tool_use"
    CODE_EXECUTION = "code_execution"
    WEB_SEARCH = "web_search"
    FILE_OPERATIONS = "file_operations"
    DATABASE_ACCESS = "database_access"
    API_CALLS = "api_calls"
    MEMORY_ACCESS = "memory_access"
    MULTI_MODAL = "multi_modal"
    REASONING = "reasoning"


# =============================================================================
# Message Types
# =============================================================================

class Message(BaseModel):
    """
    A message in a conversation.

    Attributes:
        role: The role of the message sender
        content: The message content
        metadata: Additional metadata about the message
        timestamp: When the message was created
        tool_calls: Tool calls made in this message (for assistant/tool roles)
        tool_call_id: ID of the tool call this message is responding to
    """

    role: MessageRole
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None

    model_config = ConfigDict(use_enum_values=False)


class ToolCall(BaseModel):
    """
    Represents a tool call request.

    Attributes:
        id: Unique identifier for this tool call
        name: Name of the tool to call
        arguments: Arguments to pass to the tool
        result: Result of the tool call (populated after execution)
    """

    id: str
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Any] = None


# =============================================================================
# Agent Configuration
# =============================================================================

class AgentConfig(BaseModel):
    """
    Configuration for an AI agent.

    Attributes:
        name: Human-readable name of the agent
        description: Description of what the agent does
        model: LLM model to use (e.g., "gpt-4", "claude-3-opus")
        temperature: Sampling temperature (0.0 to 2.0)
        max_tokens: Maximum tokens to generate
        capabilities: List of agent capabilities
        tools: List of tool names the agent can use
        system_prompt: System prompt for the agent
        max_iterations: Maximum iterations for reasoning loops
        timeout: Timeout in seconds for agent execution
        memory_config: Configuration for agent memory
        verbose: Whether to enable verbose logging
    """

    name: str
    description: str
    model: str
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2000, ge=1)
    capabilities: List[AgentCapability] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    system_prompt: Optional[str] = None
    max_iterations: int = Field(default=10, ge=1)
    timeout: int = Field(default=60, ge=1)
    memory_config: Dict[str, Any] = Field(default_factory=dict)
    verbose: bool = False

    model_config = ConfigDict(use_enum_values=False)


# =============================================================================
# Agent Context
# =============================================================================

class AgentContext(BaseModel):
    """
    Runtime context for an agent execution.

    Attributes:
        agent_id: Unique identifier for the agent
        user_id: ID of the user who initiated the agent
        session_id: ID of the current session
        conversation_history: List of messages in the conversation
        current_task: Description of the current task
        variables: Runtime variables accessible to the agent
        metadata: Additional metadata about the context
        created_at: When the context was created
        updated_at: When the context was last updated
    """

    agent_id: str
    user_id: str
    session_id: str
    conversation_history: List[Message] = Field(default_factory=list)
    current_task: Optional[str] = None
    variables: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def add_message(self, message: Message) -> None:
        """Add a message to the conversation history."""
        self.conversation_history.append(message)
        self.updated_at = datetime.utcnow()

    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a variable from the context."""
        return self.variables.get(key, default)

    def set_variable(self, key: str, value: Any) -> None:
        """Set a variable in the context."""
        self.variables[key] = value
        self.updated_at = datetime.utcnow()


# =============================================================================
# Agent Result
# =============================================================================

class AgentResult(BaseModel):
    """
    Result of an agent execution.

    Attributes:
        success: Whether the execution was successful
        output: The main output from the agent
        error: Error message if execution failed
        tool_calls: Tool calls made during execution
        steps: Intermediate steps taken (for multi-step reasoning)
        metadata: Additional metadata about the result
        execution_time: Time taken to execute in seconds
        tokens_used: Number of tokens used (if available)
        status: Final status of the agent
    """

    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    tool_calls: List[ToolCall] = Field(default_factory=list)
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    execution_time: float = Field(default=0.0)
    tokens_used: Optional[Dict[str, int]] = None
    status: AgentStatus = AgentStatus.COMPLETED

    model_config = ConfigDict(use_enum_values=False)


# =============================================================================
# Agent State
# =============================================================================

class AgentState(BaseModel):
    """
    Current state of an agent.

    Attributes:
        agent_id: Unique identifier for the agent
        status: Current status of the agent
        current_task: Task the agent is currently working on
        context: Current agent context
        result: Most recent result (if any)
        error: Most recent error (if any)
        created_at: When the agent was created
        started_at: When the agent started execution
        completed_at: When the agent completed (if completed)
    """

    agent_id: str
    status: AgentStatus = AgentStatus.IDLE
    current_task: Optional[str] = None
    context: Optional[AgentContext] = None
    result: Optional[AgentResult] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(use_enum_values=False)

    def start(self, task: str) -> None:
        """Mark the agent as started."""
        self.status = AgentStatus.ACTING
        self.current_task = task
        self.started_at = datetime.utcnow()

    def complete(self, result: AgentResult) -> None:
        """Mark the agent as completed."""
        self.status = AgentStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.utcnow()

    def fail(self, error: str) -> None:
        """Mark the agent as failed."""
        self.status = AgentStatus.ERROR
        self.error = error
        self.completed_at = datetime.utcnow()


# =============================================================================
# Agent Request
# =============================================================================

class AgentRequest(BaseModel):
    """
    Request to execute an agent.

    Attributes:
        agent_id: ID of the agent to execute
        task: Task description or prompt
        user_id: ID of the user making the request
        session_id: ID of the session
        context: Optional context to start with
        variables: Optional variables to set
        config_overrides: Optional configuration overrides
    """

    agent_id: str
    task: str
    user_id: str
    session_id: str
    context: Optional[AgentContext] = None
    variables: Dict[str, Any] = Field(default_factory=dict)
    config_overrides: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Export all types
# =============================================================================

__all__ = [
    # Enums
    "MessageRole",
    "AgentStatus",
    "AgentCapability",
    # Message types
    "Message",
    "ToolCall",
    # Configuration
    "AgentConfig",
    # Context
    "AgentContext",
    # Result
    "AgentResult",
    # State
    "AgentState",
    # Request
    "AgentRequest",
]

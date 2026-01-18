"""
Global Exception Definitions

This module defines all custom exceptions used throughout the AI service.
All exceptions inherit from a base AIServiceException for consistent error handling.

Exception Categories:
- Base Exceptions: Root exception classes
- Agent Exceptions: Agent-related errors
- Memory Exceptions: Memory storage and retrieval errors
- Tool Exceptions: Tool execution and registration errors
- Workflow Exceptions: Workflow execution and state management errors
- Configuration Exceptions: Configuration and setup errors
- Event Exceptions: Event system errors
"""

from typing import Any, Dict, Optional


# =============================================================================
# Base Exceptions
# =============================================================================

class AIServiceException(Exception):
    """
    Base exception for all AI service errors.

    Attributes:
        message: Human-readable error message
        details: Additional error details (optional)
        error_code: Unique error code for tracking (optional)
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        self.message = message
        self.details = details or {}
        self.error_code = error_code
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "error_code": self.error_code,
        }


class ValidationError(AIServiceException):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        if field:
            message = f"Validation failed for field '{field}': {message}"
        super().__init__(message, details=details, error_code="VALIDATION_ERROR")
        self.field = field


# =============================================================================
# Agent Exceptions
# =============================================================================

class AgentException(AIServiceException):
    """Base exception for agent-related errors."""
    pass


class AgentNotFoundError(AgentException):
    """Raised when an agent is not found."""

    def __init__(
        self,
        agent_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Agent '{agent_id}' not found",
            details=details,
            error_code="AGENT_NOT_FOUND"
        )
        self.agent_id = agent_id


class AgentInitializationError(AgentException):
    """Raised when agent initialization fails."""

    def __init__(
        self,
        agent_id: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Failed to initialize agent '{agent_id}': {reason}",
            details=details,
            error_code="AGENT_INIT_ERROR"
        )
        self.agent_id = agent_id


class AgentExecutionError(AgentException):
    """Raised when agent execution fails."""

    def __init__(
        self,
        agent_id: str,
        task: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Agent '{agent_id}' failed to execute task '{task}': {reason}",
            details=details,
            error_code="AGENT_EXECUTION_ERROR"
        )
        self.agent_id = agent_id
        self.task = task


class AgentConfigError(AgentException):
    """Raised when agent configuration is invalid."""

    def __init__(
        self,
        agent_id: str,
        config_issue: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Invalid configuration for agent '{agent_id}': {config_issue}",
            details=details,
            error_code="AGENT_CONFIG_ERROR"
        )
        self.agent_id = agent_id


# =============================================================================
# Memory Exceptions
# =============================================================================

class MemoryException(AIServiceException):
    """Base exception for memory-related errors."""
    pass


class MemoryNotFoundError(MemoryException):
    """Raised when memory entry is not found."""

    def __init__(
        self,
        memory_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Memory entry '{memory_id}' not found",
            details=details,
            error_code="MEMORY_NOT_FOUND"
        )
        self.memory_id = memory_id


class MemoryStorageError(MemoryException):
    """Raised when memory storage operation fails."""

    def __init__(
        self,
        operation: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Memory storage operation '{operation}' failed: {reason}",
            details=details,
            error_code="MEMORY_STORAGE_ERROR"
        )
        self.operation = operation


class MemoryRetrievalError(MemoryException):
    """Raised when memory retrieval fails."""

    def __init__(
        self,
        query: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Memory retrieval failed for query '{query}': {reason}",
            details=details,
            error_code="MEMORY_RETRIEVAL_ERROR"
        )
        self.query = query


class MemoryConfigError(MemoryException):
    """Raised when memory configuration is invalid."""

    def __init__(
        self,
        config_issue: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Invalid memory configuration: {config_issue}",
            details=details,
            error_code="MEMORY_CONFIG_ERROR"
        )


class MemoryValidationError(MemoryException):
    """Raised when memory data validation fails."""

    def __init__(
        self,
        validation_error: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Memory validation failed: {validation_error}",
            details=details,
            error_code="MEMORY_VALIDATION_ERROR"
        )


class MemoryOperationError(MemoryException):
    """Raised when memory operation fails."""

    def __init__(
        self,
        operation_error: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Memory operation failed: {operation_error}",
            details=details,
            error_code="MEMORY_OPERATION_ERROR"
        )


class MemoryLimitExceededError(MemoryException):
    """Raised when memory limit is exceeded."""

    def __init__(
        self,
        limit_type: str,
        current: int,
        maximum: int,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Memory {limit_type} limit exceeded: {current}/{maximum}",
            details=details,
            error_code="MEMORY_LIMIT_EXCEEDED"
        )
        self.current = current
        self.maximum = maximum


class MemoryExpiredError(MemoryException):
    """Raised when accessing expired memory."""

    def __init__(
        self,
        memory_id: str,
        expired_at: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Memory entry '{memory_id}' expired at {expired_at}",
            details=details,
            error_code="MEMORY_EXPIRED"
        )
        self.memory_id = memory_id


# =============================================================================
# Tool Exceptions
# =============================================================================

class ToolException(AIServiceException):
    """Base exception for tool-related errors."""
    pass


class ToolNotFoundError(ToolException):
    """Raised when a tool is not found."""

    def __init__(
        self,
        tool_name: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Tool '{tool_name}' not found",
            details=details,
            error_code="TOOL_NOT_FOUND"
        )
        self.tool_name = tool_name


class ToolExecutionError(ToolException):
    """Raised when tool execution fails."""

    def __init__(
        self,
        tool_name: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Tool '{tool_name}' execution failed: {reason}",
            details=details,
            error_code="TOOL_EXECUTION_ERROR"
        )
        self.tool_name = tool_name


class ToolRegistrationError(ToolException):
    """Raised when tool registration fails."""

    def __init__(
        self,
        tool_name: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Failed to register tool '{tool_name}': {reason}",
            details=details,
            error_code="TOOL_REGISTRATION_ERROR"
        )
        self.tool_name = tool_name


class ToolValidationError(ToolException):
    """Raised when tool input/output validation fails."""

    def __init__(
        self,
        tool_name: str,
        validation_issue: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Tool '{tool_name}' validation failed: {validation_issue}",
            details=details,
            error_code="TOOL_VALIDATION_ERROR"
        )
        self.tool_name = tool_name


# =============================================================================
# Workflow Exceptions
# =============================================================================

class WorkflowException(AIServiceException):
    """Base exception for workflow-related errors."""
    pass


class WorkflowNotFoundError(WorkflowException):
    """Raised when a workflow is not found."""

    def __init__(
        self,
        workflow_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Workflow '{workflow_id}' not found",
            details=details,
            error_code="WORKFLOW_NOT_FOUND"
        )
        self.workflow_id = workflow_id


class WorkflowExecutionError(WorkflowException):
    """Raised when workflow execution fails."""

    def __init__(
        self,
        workflow_id: str,
        stage: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Workflow '{workflow_id}' failed at stage '{stage}': {reason}",
            details=details,
            error_code="WORKFLOW_EXECUTION_ERROR"
        )
        self.workflow_id = workflow_id
        self.stage = stage


class WorkflowStateError(WorkflowException):
    """Raised when workflow state is invalid."""

    def __init__(
        self,
        workflow_id: str,
        state_issue: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Invalid state for workflow '{workflow_id}': {state_issue}",
            details=details,
            error_code="WORKFLOW_STATE_ERROR"
        )
        self.workflow_id = workflow_id


class WorkflowConfigError(WorkflowException):
    """Raised when workflow configuration is invalid."""

    def __init__(
        self,
        workflow_id: str,
        config_issue: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Invalid configuration for workflow '{workflow_id}': {config_issue}",
            details=details,
            error_code="WORKFLOW_CONFIG_ERROR"
        )
        self.workflow_id = workflow_id


# =============================================================================
# Configuration Exceptions
# =============================================================================

class ConfigurationException(AIServiceException):
    """Base exception for configuration-related errors."""
    pass


class ConfigNotFoundError(ConfigurationException):
    """Raised when configuration file or value is not found."""

    def __init__(
        self,
        config_path: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Configuration not found: {config_path}",
            details=details,
            error_code="CONFIG_NOT_FOUND"
        )
        self.config_path = config_path


class ConfigValidationError(ConfigurationException):
    """Raised when configuration validation fails."""

    def __init__(
        self,
        config_issue: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Configuration validation failed: {config_issue}",
            details=details,
            error_code="CONFIG_VALIDATION_ERROR"
        )


class EnvironmentError(ConfigurationException):
    """Raised when environment variable is missing or invalid."""

    def __init__(
        self,
        env_var: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Environment variable '{env_var}' is missing or invalid",
            details=details,
            error_code="ENVIRONMENT_ERROR"
        )
        self.env_var = env_var


# =============================================================================
# Event Exceptions
# =============================================================================

class EventException(AIServiceException):
    """Base exception for event-related errors."""
    pass


class EventPublishError(EventException):
    """Raised when event publishing fails."""

    def __init__(
        self,
        event_type: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Failed to publish event '{event_type}': {reason}",
            details=details,
            error_code="EVENT_PUBLISH_ERROR"
        )
        self.event_type = event_type


class EventSubscriptionError(EventException):
    """Raised when event subscription fails."""

    def __init__(
        self,
        event_type: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Failed to subscribe to event '{event_type}': {reason}",
            details=details,
            error_code="EVENT_SUBSCRIPTION_ERROR"
        )
        self.event_type = event_type


class EventHandlerError(EventException):
    """Raised when event handler fails."""

    def __init__(
        self,
        event_type: str,
        handler: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Event handler '{handler}' failed for event '{event_type}': {reason}",
            details=details,
            error_code="EVENT_HANDLER_ERROR"
        )
        self.event_type = event_type
        self.handler = handler


# =============================================================================
# LLM Exceptions
# =============================================================================

class LLMException(AIServiceException):
    """Base exception for LLM-related errors."""
    pass


class LLMConnectionError(LLMException):
    """Raised when LLM connection fails."""

    def __init__(
        self,
        provider: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Failed to connect to LLM provider '{provider}': {reason}",
            details=details,
            error_code="LLM_CONNECTION_ERROR"
        )
        self.provider = provider


class LLMResponseError(LLMException):
    """Raised when LLM response is invalid or malformed."""

    def __init__(
        self,
        provider: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Invalid response from LLM provider '{provider}': {reason}",
            details=details,
            error_code="LLM_RESPONSE_ERROR"
        )
        self.provider = provider


class LLMRateLimitError(LLMException):
    """Raised when LLM rate limit is exceeded."""

    def __init__(
        self,
        provider: str,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        message = f"Rate limit exceeded for LLM provider '{provider}'"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        super().__init__(
            message,
            details=details,
            error_code="LLM_RATE_LIMIT_ERROR"
        )
        self.provider = provider
        self.retry_after = retry_after


# =============================================================================
# RAG Exceptions
# =============================================================================

class RAGException(AIServiceException):
    """Base exception for RAG-related errors."""
    pass


class DocumentNotFoundError(RAGException):
    """Raised when a document is not found in the RAG system."""

    def __init__(
        self,
        doc_id: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Document '{doc_id}' not found in RAG system",
            details=details,
            error_code="DOCUMENT_NOT_FOUND"
        )
        self.doc_id = doc_id


class RetrievalError(RAGException):
    """Raised when document retrieval fails."""

    def __init__(
        self,
        query: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Document retrieval failed for query '{query}': {reason}",
            details=details,
            error_code="RETRIEVAL_ERROR"
        )
        self.query = query


class EmbeddingError(RAGException):
    """Raised when embedding generation fails."""

    def __init__(
        self,
        text: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            f"Failed to generate embedding: {reason}",
            details=details,
            error_code="EMBEDDING_ERROR"
        )
        self.text = text[:100]  # Store first 100 chars for debugging


# =============================================================================
# Export all exceptions
# =============================================================================

__all__ = [
    # Base
    "AIServiceException",
    "ValidationError",
    # Agent
    "AgentException",
    "AgentNotFoundError",
    "AgentInitializationError",
    "AgentExecutionError",
    "AgentConfigError",
    # Memory
    "MemoryException",
    "MemoryNotFoundError",
    "MemoryStorageError",
    "MemoryRetrievalError",
    "MemoryConfigError",
    "MemoryValidationError",
    "MemoryOperationError",
    "MemoryLimitExceededError",
    "MemoryExpiredError",
    # Tool
    "ToolException",
    "ToolNotFoundError",
    "ToolExecutionError",
    "ToolRegistrationError",
    "ToolValidationError",
    # Workflow
    "WorkflowException",
    "WorkflowNotFoundError",
    "WorkflowExecutionError",
    "WorkflowStateError",
    "WorkflowConfigError",
    # Configuration
    "ConfigurationException",
    "ConfigNotFoundError",
    "ConfigValidationError",
    "EnvironmentError",
    # Event
    "EventException",
    "EventPublishError",
    "EventSubscriptionError",
    "EventHandlerError",
    # LLM
    "LLMException",
    "LLMConnectionError",
    "LLMResponseError",
    "LLMRateLimitError",
    # RAG
    "RAGException",
    "DocumentNotFoundError",
    "RetrievalError",
    "EmbeddingError",
]

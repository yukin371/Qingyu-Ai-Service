"""
Tests for common exceptions
"""

import pytest

from src.common.exceptions import (
    AIServiceException,
    ValidationError,
    AgentException,
    AgentNotFoundError,
    AgentInitializationError,
    AgentExecutionError,
    AgentConfigError,
    MemoryException,
    MemoryNotFoundError,
    MemoryStorageError,
    MemoryRetrievalError,
    MemoryConfigError,
    ToolException,
    ToolNotFoundError,
    ToolExecutionError,
    ToolRegistrationError,
    ToolValidationError,
    WorkflowException,
    WorkflowNotFoundError,
    WorkflowExecutionError,
    WorkflowStateError,
    WorkflowConfigError,
    ConfigurationException,
    ConfigNotFoundError,
    ConfigValidationError,
    EnvironmentError,
    EventException,
    EventPublishError,
    EventSubscriptionError,
    EventHandlerError,
    LLMException,
    LLMConnectionError,
    LLMResponseError,
    LLMRateLimitError,
    RAGException,
    DocumentNotFoundError,
    RetrievalError,
    EmbeddingError,
)


class TestAIServiceException:
    """Test base AIServiceException."""

    def test_basic_exception(self):
        """Test basic exception creation."""
        exc = AIServiceException("Test error")
        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.details == {}
        assert exc.error_code is None

    def test_exception_with_details(self):
        """Test exception with details."""
        details = {"key": "value"}
        exc = AIServiceException("Test error", details=details)
        assert exc.details == details

    def test_exception_with_error_code(self):
        """Test exception with error code."""
        exc = AIServiceException("Test error", error_code="TEST_ERROR")
        assert str(exc) == "[TEST_ERROR] Test error"
        assert exc.error_code == "TEST_ERROR"

    def test_to_dict(self):
        """Test exception to dictionary conversion."""
        exc = AIServiceException(
            "Test error",
            details={"key": "value"},
            error_code="TEST_ERROR"
        )
        result = exc.to_dict()
        assert result["error_type"] == "AIServiceException"
        assert result["message"] == "Test error"
        assert result["details"] == {"key": "value"}
        assert result["error_code"] == "TEST_ERROR"


class TestValidationError:
    """Test ValidationError."""

    def test_basic_validation_error(self):
        """Test basic validation error."""
        exc = ValidationError("Invalid input")
        assert "VALIDATION_ERROR" in str(exc)
        assert "Invalid input" in str(exc)

    def test_validation_error_with_field(self):
        """Test validation error with field name."""
        exc = ValidationError("Invalid input", field="username")
        assert "username" in str(exc)
        assert exc.field == "username"


class TestAgentExceptions:
    """Test agent-related exceptions."""

    def test_agent_not_found(self):
        """Test AgentNotFoundError."""
        exc = AgentNotFoundError("agent-123")
        assert "agent-123" in str(exc)
        assert exc.agent_id == "agent-123"
        assert exc.error_code == "AGENT_NOT_FOUND"

    def test_agent_initialization_error(self):
        """Test AgentInitializationError."""
        exc = AgentInitializationError("agent-123", "Missing config")
        assert "agent-123" in str(exc)
        assert "Missing config" in str(exc)
        assert exc.agent_id == "agent-123"
        assert exc.error_code == "AGENT_INIT_ERROR"

    def test_agent_execution_error(self):
        """Test AgentExecutionError."""
        exc = AgentExecutionError("agent-123", "task-1", "Timeout")
        assert "agent-123" in str(exc)
        assert "task-1" in str(exc)
        assert "Timeout" in str(exc)
        assert exc.agent_id == "agent-123"
        assert exc.task == "task-1"
        assert exc.error_code == "AGENT_EXECUTION_ERROR"

    def test_agent_config_error(self):
        """Test AgentConfigError."""
        exc = AgentConfigError("agent-123", "Invalid model")
        assert "agent-123" in str(exc)
        assert "Invalid model" in str(exc)
        assert exc.agent_id == "agent-123"
        assert exc.error_code == "AGENT_CONFIG_ERROR"


class TestMemoryExceptions:
    """Test memory-related exceptions."""

    def test_memory_not_found(self):
        """Test MemoryNotFoundError."""
        exc = MemoryNotFoundError("mem-123")
        assert "mem-123" in str(exc)
        assert exc.memory_id == "mem-123"
        assert exc.error_code == "MEMORY_NOT_FOUND"

    def test_memory_storage_error(self):
        """Test MemoryStorageError."""
        exc = MemoryStorageError("save", "Disk full")
        assert "save" in str(exc)
        assert "Disk full" in str(exc)
        assert exc.operation == "save"
        assert exc.error_code == "MEMORY_STORAGE_ERROR"

    def test_memory_retrieval_error(self):
        """Test MemoryRetrievalError."""
        exc = MemoryRetrievalError("query-1", "Index error")
        assert "query-1" in str(exc)
        assert "Index error" in str(exc)
        assert exc.query == "query-1"
        assert exc.error_code == "MEMORY_RETRIEVAL_ERROR"

    def test_memory_config_error(self):
        """Test MemoryConfigError."""
        exc = MemoryConfigError("Invalid max_size")
        assert "Invalid max_size" in str(exc)
        assert exc.error_code == "MEMORY_CONFIG_ERROR"


class TestToolExceptions:
    """Test tool-related exceptions."""

    def test_tool_not_found(self):
        """Test ToolNotFoundError."""
        exc = ToolNotFoundError("search_tool")
        assert "search_tool" in str(exc)
        assert exc.tool_name == "search_tool"
        assert exc.error_code == "TOOL_NOT_FOUND"

    def test_tool_execution_error(self):
        """Test ToolExecutionError."""
        exc = ToolExecutionError("search_tool", "API timeout")
        assert "search_tool" in str(exc)
        assert "API timeout" in str(exc)
        assert exc.tool_name == "search_tool"
        assert exc.error_code == "TOOL_EXECUTION_ERROR"

    def test_tool_registration_error(self):
        """Test ToolRegistrationError."""
        exc = ToolRegistrationError("search_tool", "Duplicate name")
        assert "search_tool" in str(exc)
        assert "Duplicate name" in str(exc)
        assert exc.tool_name == "search_tool"
        assert exc.error_code == "TOOL_REGISTRATION_ERROR"

    def test_tool_validation_error(self):
        """Test ToolValidationError."""
        exc = ToolValidationError("search_tool", "Invalid schema")
        assert "search_tool" in str(exc)
        assert "Invalid schema" in str(exc)
        assert exc.tool_name == "search_tool"
        assert exc.error_code == "TOOL_VALIDATION_ERROR"


class TestWorkflowExceptions:
    """Test workflow-related exceptions."""

    def test_workflow_not_found(self):
        """Test WorkflowNotFoundError."""
        exc = WorkflowNotFoundError("workflow-123")
        assert "workflow-123" in str(exc)
        assert exc.workflow_id == "workflow-123"
        assert exc.error_code == "WORKFLOW_NOT_FOUND"

    def test_workflow_execution_error(self):
        """Test WorkflowExecutionError."""
        exc = WorkflowExecutionError("workflow-123", "stage-1", "Task failed")
        assert "workflow-123" in str(exc)
        assert "stage-1" in str(exc)
        assert "Task failed" in str(exc)
        assert exc.workflow_id == "workflow-123"
        assert exc.stage == "stage-1"
        assert exc.error_code == "WORKFLOW_EXECUTION_ERROR"

    def test_workflow_state_error(self):
        """Test WorkflowStateError."""
        exc = WorkflowStateError("workflow-123", "Invalid transition")
        assert "workflow-123" in str(exc)
        assert "Invalid transition" in str(exc)
        assert exc.workflow_id == "workflow-123"
        assert exc.error_code == "WORKFLOW_STATE_ERROR"

    def test_workflow_config_error(self):
        """Test WorkflowConfigError."""
        exc = WorkflowConfigError("workflow-123", "Missing dependencies")
        assert "workflow-123" in str(exc)
        assert "Missing dependencies" in str(exc)
        assert exc.workflow_id == "workflow-123"
        assert exc.error_code == "WORKFLOW_CONFIG_ERROR"


class TestConfigurationExceptions:
    """Test configuration-related exceptions."""

    def test_config_not_found(self):
        """Test ConfigNotFoundError."""
        exc = ConfigNotFoundError("config.yaml")
        assert "config.yaml" in str(exc)
        assert exc.config_path == "config.yaml"
        assert exc.error_code == "CONFIG_NOT_FOUND"

    def test_config_validation_error(self):
        """Test ConfigValidationError."""
        exc = ConfigValidationError("Invalid API key format")
        assert "Invalid API key format" in str(exc)
        assert exc.error_code == "CONFIG_VALIDATION_ERROR"

    def test_environment_error(self):
        """Test EnvironmentError."""
        exc = EnvironmentError("OPENAI_API_KEY")
        assert "OPENAI_API_KEY" in str(exc)
        assert exc.env_var == "OPENAI_API_KEY"
        assert exc.error_code == "ENVIRONMENT_ERROR"


class TestEventExceptions:
    """Test event-related exceptions."""

    def test_event_publish_error(self):
        """Test EventPublishError."""
        exc = EventPublishError("user.login", "Broker unavailable")
        assert "user.login" in str(exc)
        assert "Broker unavailable" in str(exc)
        assert exc.event_type == "user.login"
        assert exc.error_code == "EVENT_PUBLISH_ERROR"

    def test_event_subscription_error(self):
        """Test EventSubscriptionError."""
        exc = EventSubscriptionError("user.login", "Invalid handler")
        assert "user.login" in str(exc)
        assert "Invalid handler" in str(exc)
        assert exc.event_type == "user.login"
        assert exc.error_code == "EVENT_SUBSCRIPTION_ERROR"

    def test_event_handler_error(self):
        """Test EventHandlerError."""
        exc = EventHandlerError("user.login", "handle_login", "Exception in handler")
        assert "user.login" in str(exc)
        assert "handle_login" in str(exc)
        assert exc.event_type == "user.login"
        assert exc.handler == "handle_login"
        assert exc.error_code == "EVENT_HANDLER_ERROR"


class TestLLMExceptions:
    """Test LLM-related exceptions."""

    def test_llm_connection_error(self):
        """Test LLMConnectionError."""
        exc = LLMConnectionError("openai", "Connection timeout")
        assert "openai" in str(exc)
        assert "Connection timeout" in str(exc)
        assert exc.provider == "openai"
        assert exc.error_code == "LLM_CONNECTION_ERROR"

    def test_llm_response_error(self):
        """Test LLMResponseError."""
        exc = LLMResponseError("openai", "Malformed JSON")
        assert "openai" in str(exc)
        assert "Malformed JSON" in str(exc)
        assert exc.provider == "openai"
        assert exc.error_code == "LLM_RESPONSE_ERROR"

    def test_llm_rate_limit_error(self):
        """Test LLMRateLimitError."""
        exc = LLMRateLimitError("openai", retry_after=60)
        assert "openai" in str(exc)
        assert "60 seconds" in str(exc)
        assert exc.provider == "openai"
        assert exc.retry_after == 60
        assert exc.error_code == "LLM_RATE_LIMIT_ERROR"

    def test_llm_rate_limit_error_no_retry(self):
        """Test LLMRateLimitError without retry_after."""
        exc = LLMRateLimitError("openai")
        assert "openai" in str(exc)
        assert exc.provider == "openai"
        assert exc.retry_after is None


class TestRAGExceptions:
    """Test RAG-related exceptions."""

    def test_document_not_found(self):
        """Test DocumentNotFoundError."""
        exc = DocumentNotFoundError("doc-123")
        assert "doc-123" in str(exc)
        assert exc.doc_id == "doc-123"
        assert exc.error_code == "DOCUMENT_NOT_FOUND"

    def test_retrieval_error(self):
        """Test RetrievalError."""
        exc = RetrievalError("test query", "Vector index error")
        assert "test query" in str(exc)
        assert "Vector index error" in str(exc)
        assert exc.query == "test query"
        assert exc.error_code == "RETRIEVAL_ERROR"

    def test_embedding_error(self):
        """Test EmbeddingError."""
        long_text = "a" * 200
        exc = EmbeddingError(long_text, "Model unavailable")
        assert "Model unavailable" in str(exc)
        assert exc.error_code == "EMBEDDING_ERROR"
        # Check that text is truncated
        assert len(exc.text) == 100


class TestExceptionInheritance:
    """Test exception inheritance hierarchy."""

    def test_agent_exception_inheritance(self):
        """Test that all agent exceptions inherit from AgentException."""
        assert issubclass(AgentNotFoundError, AgentException)
        assert issubclass(AgentInitializationError, AgentException)
        assert issubclass(AgentExecutionError, AgentException)
        assert issubclass(AgentConfigError, AgentException)

    def test_memory_exception_inheritance(self):
        """Test that all memory exceptions inherit from MemoryException."""
        assert issubclass(MemoryNotFoundError, MemoryException)
        assert issubclass(MemoryStorageError, MemoryException)
        assert issubclass(MemoryRetrievalError, MemoryException)
        assert issubclass(MemoryConfigError, MemoryException)

    def test_tool_exception_inheritance(self):
        """Test that all tool exceptions inherit from ToolException."""
        assert issubclass(ToolNotFoundError, ToolException)
        assert issubclass(ToolExecutionError, ToolException)
        assert issubclass(ToolRegistrationError, ToolException)
        assert issubclass(ToolValidationError, ToolException)

    def test_workflow_exception_inheritance(self):
        """Test that all workflow exceptions inherit from WorkflowException."""
        assert issubclass(WorkflowNotFoundError, WorkflowException)
        assert issubclass(WorkflowExecutionError, WorkflowException)
        assert issubclass(WorkflowStateError, WorkflowException)
        assert issubclass(WorkflowConfigError, WorkflowException)

    def test_all_inherit_from_base(self):
        """Test that all exceptions inherit from AIServiceException."""
        assert issubclass(ValidationError, AIServiceException)
        assert issubclass(AgentException, AIServiceException)
        assert issubclass(MemoryException, AIServiceException)
        assert issubclass(ToolException, AIServiceException)
        assert issubclass(WorkflowException, AIServiceException)
        assert issubclass(ConfigurationException, AIServiceException)
        assert issubclass(EventException, AIServiceException)
        assert issubclass(LLMException, AIServiceException)
        assert issubclass(RAGException, AIServiceException)

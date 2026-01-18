"""
Tests for agent type definitions
"""

import pytest

from src.common.types.agent_types import (
    MessageRole,
    AgentStatus,
    AgentCapability,
    Message,
    ToolCall,
    AgentConfig,
    AgentContext,
    AgentResult,
    AgentState,
    AgentRequest,
)


class TestMessageRole:
    """Test MessageRole enum."""

    def test_values(self):
        """Test enum values."""
        assert MessageRole.SYSTEM.value == "system"
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.TOOL.value == "tool"
        assert MessageRole.FUNCTION.value == "function"


class TestAgentStatus:
    """Test AgentStatus enum."""

    def test_values(self):
        """Test enum values."""
        assert AgentStatus.IDLE.value == "idle"
        assert AgentStatus.THINKING.value == "thinking"
        assert AgentStatus.ACTING.value == "acting"
        assert AgentStatus.WAITING.value == "waiting"
        assert AgentStatus.ERROR.value == "error"
        assert AgentStatus.COMPLETED.value == "completed"


class TestAgentCapability:
    """Test AgentCapability enum."""

    def test_values(self):
        """Test enum values."""
        assert AgentCapability.TEXT_GENERATION.value == "text_generation"
        assert AgentCapability.TOOL_USE.value == "tool_use"
        assert AgentCapability.CODE_EXECUTION.value == "code_execution"


class TestMessage:
    """Test Message type."""

    def test_create_basic_message(self):
        """Test creating a basic message."""
        msg = Message(role=MessageRole.USER, content="Hello")
        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"
        assert msg.metadata == {}
        assert msg.tool_calls is None
        assert msg.tool_call_id is None

    def test_create_message_with_metadata(self):
        """Test creating a message with metadata."""
        msg = Message(
            role=MessageRole.ASSISTANT,
            content="Hi there",
            metadata={"source": "test"}
        )
        assert msg.metadata["source"] == "test"

    def test_create_message_with_tool_calls(self):
        """Test creating a message with tool calls."""
        tool_calls = [{"id": "call_1", "name": "search", "arguments": {"query": "test"}}]
        msg = Message(
            role=MessageRole.ASSISTANT,
            content="",
            tool_calls=tool_calls
        )
        assert msg.tool_calls == tool_calls

    def test_create_tool_message(self):
        """Test creating a tool response message."""
        msg = Message(
            role=MessageRole.TOOL,
            content="Tool result",
            tool_call_id="call_1"
        )
        assert msg.tool_call_id == "call_1"

    def test_message_serialization(self):
        """Test message serialization."""
        msg = Message(role=MessageRole.USER, content="Test")
        data = msg.model_dump()
        assert data["role"] == MessageRole.USER
        assert data["content"] == "Test"


class TestToolCall:
    """Test ToolCall type."""

    def test_create_tool_call(self):
        """Test creating a tool call."""
        call = ToolCall(
            id="call_1",
            name="search",
            arguments={"query": "test"}
        )
        assert call.id == "call_1"
        assert call.name == "search"
        assert call.arguments == {"query": "test"}
        assert call.result is None

    def test_tool_call_with_result(self):
        """Test creating a tool call with result."""
        call = ToolCall(
            id="call_1",
            name="search",
            arguments={"query": "test"},
            result={"results": ["item1", "item2"]}
        )
        assert call.result == {"results": ["item1", "item2"]}


class TestAgentConfig:
    """Test AgentConfig type."""

    def test_create_basic_config(self):
        """Test creating basic agent config."""
        config = AgentConfig(
            name="Test Agent",
            description="A test agent",
            model="gpt-4"
        )
        assert config.name == "Test Agent"
        assert config.description == "A test agent"
        assert config.model == "gpt-4"
        assert config.temperature == 0.7  # default
        assert config.max_tokens == 2000  # default

    def test_config_with_capabilities(self):
        """Test config with capabilities."""
        config = AgentConfig(
            name="Test Agent",
            description="A test agent",
            model="gpt-4",
            capabilities=[AgentCapability.TEXT_GENERATION, AgentCapability.TOOL_USE]
        )
        assert AgentCapability.TEXT_GENERATION in config.capabilities
        assert AgentCapability.TOOL_USE in config.capabilities

    def test_config_with_tools(self):
        """Test config with tools."""
        config = AgentConfig(
            name="Test Agent",
            description="A test agent",
            model="gpt-4",
            tools=["search", "calculator"]
        )
        assert "search" in config.tools
        assert "calculator" in config.tools

    def test_config_validation(self):
        """Test config validation."""
        # Valid temperature
        config = AgentConfig(
            name="Test Agent",
            description="A test agent",
            model="gpt-4",
            temperature=1.5
        )
        assert config.temperature == 1.5

        # Invalid temperature (should fail validation)
        with pytest.raises(ValueError):
            AgentConfig(
                name="Test Agent",
                description="A test agent",
                model="gpt-4",
                temperature=3.0  # > 2.0
            )

    def test_config_serialization(self):
        """Test config serialization."""
        config = AgentConfig(
            name="Test Agent",
            description="A test agent",
            model="gpt-4"
        )
        data = config.model_dump()
        assert data["name"] == "Test Agent"
        assert data["model"] == "gpt-4"


class TestAgentContext:
    """Test AgentContext type."""

    def test_create_basic_context(self):
        """Test creating basic context."""
        context = AgentContext(
            agent_id="agent_1",
            user_id="user_1",
            session_id="session_1"
        )
        assert context.agent_id == "agent_1"
        assert context.user_id == "user_1"
        assert context.session_id == "session_1"
        assert context.conversation_history == []
        assert context.variables == {}

    def test_add_message(self):
        """Test adding a message to context."""
        context = AgentContext(
            agent_id="agent_1",
            user_id="user_1",
            session_id="session_1"
        )
        msg = Message(role=MessageRole.USER, content="Hello")
        context.add_message(msg)
        assert len(context.conversation_history) == 1
        assert context.conversation_history[0].content == "Hello"

    def test_variable_operations(self):
        """Test variable get/set operations."""
        context = AgentContext(
            agent_id="agent_1",
            user_id="user_1",
            session_id="session_1"
        )
        context.set_variable("key1", "value1")
        assert context.get_variable("key1") == "value1"
        assert context.get_variable("key2", "default") == "default"

    def test_context_with_history(self):
        """Test creating context with existing history."""
        history = [
            Message(role=MessageRole.USER, content="Hello"),
            Message(role=MessageRole.ASSISTANT, content="Hi")
        ]
        context = AgentContext(
            agent_id="agent_1",
            user_id="user_1",
            session_id="session_1",
            conversation_history=history
        )
        assert len(context.conversation_history) == 2


class TestAgentResult:
    """Test AgentResult type."""

    def test_create_successful_result(self):
        """Test creating a successful result."""
        result = AgentResult(
            success=True,
            output="Task completed"
        )
        assert result.success is True
        assert result.output == "Task completed"
        assert result.error is None
        assert result.status == AgentStatus.COMPLETED

    def test_create_failed_result(self):
        """Test creating a failed result."""
        result = AgentResult(
            success=False,
            error="Task failed"
        )
        assert result.success is False
        assert result.output is None
        assert result.error == "Task failed"

    def test_result_with_tool_calls(self):
        """Test result with tool calls."""
        tool_calls = [
            ToolCall(id="call_1", name="search", arguments={}, result="result")
        ]
        result = AgentResult(
            success=True,
            output="Done",
            tool_calls=tool_calls
        )
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "search"

    def test_result_with_steps(self):
        """Test result with intermediate steps."""
        steps = [
            {"step": 1, "action": "think"},
            {"step": 2, "action": "act"}
        ]
        result = AgentResult(
            success=True,
            output="Done",
            steps=steps
        )
        assert len(result.steps) == 2
        assert result.steps[0]["action"] == "think"

    def test_result_with_token_usage(self):
        """Test result with token usage."""
        result = AgentResult(
            success=True,
            output="Done",
            tokens_used={"prompt": 10, "completion": 20, "total": 30}
        )
        assert result.tokens_used["total"] == 30


class TestAgentState:
    """Test AgentState type."""

    def test_create_initial_state(self):
        """Test creating initial agent state."""
        state = AgentState(agent_id="agent_1")
        assert state.agent_id == "agent_1"
        assert state.status == AgentStatus.IDLE
        assert state.current_task is None
        assert state.result is None

    def test_start_agent(self):
        """Test starting an agent."""
        state = AgentState(agent_id="agent_1")
        state.start("Do something")
        assert state.status == AgentStatus.ACTING
        assert state.current_task == "Do something"
        assert state.started_at is not None

    def test_complete_agent(self):
        """Test completing an agent."""
        state = AgentState(agent_id="agent_1")
        result = AgentResult(success=True, output="Done")
        state.complete(result)
        assert state.status == AgentStatus.COMPLETED
        assert state.result == result
        assert state.completed_at is not None

    def test_fail_agent(self):
        """Test failing an agent."""
        state = AgentState(agent_id="agent_1")
        state.fail("Error occurred")
        assert state.status == AgentStatus.ERROR
        assert state.error == "Error occurred"
        assert state.completed_at is not None

    def test_state_with_context(self):
        """Test state with context."""
        context = AgentContext(
            agent_id="agent_1",
            user_id="user_1",
            session_id="session_1"
        )
        state = AgentState(agent_id="agent_1", context=context)
        assert state.context == context


class TestAgentRequest:
    """Test AgentRequest type."""

    def test_create_basic_request(self):
        """Test creating basic request."""
        request = AgentRequest(
            agent_id="agent_1",
            task="Do something",
            user_id="user_1",
            session_id="session_1"
        )
        assert request.agent_id == "agent_1"
        assert request.task == "Do something"
        assert request.user_id == "user_1"
        assert request.session_id == "session_1"

    def test_request_with_context(self):
        """Test request with context."""
        context = AgentContext(
            agent_id="agent_1",
            user_id="user_1",
            session_id="session_1"
        )
        request = AgentRequest(
            agent_id="agent_1",
            task="Do something",
            user_id="user_1",
            session_id="session_1",
            context=context
        )
        assert request.context == context

    def test_request_with_variables(self):
        """Test request with variables."""
        request = AgentRequest(
            agent_id="agent_1",
            task="Do something",
            user_id="user_1",
            session_id="session_1",
            variables={"key": "value"}
        )
        assert request.variables["key"] == "value"

    def test_request_with_config_overrides(self):
        """Test request with config overrides."""
        request = AgentRequest(
            agent_id="agent_1",
            task="Do something",
            user_id="user_1",
            session_id="session_1",
            config_overrides={"temperature": 0.5}
        )
        assert request.config_overrides["temperature"] == 0.5


class TestTypeCompatibility:
    """Test compatibility with Pydantic and LangChain."""

    def test_pydantic_validation(self):
        """Test that types work with Pydantic validation."""
        # This should not raise an exception
        msg = Message(**{"role": MessageRole.USER, "content": "Test"})
        assert msg.content == "Test"

    def test_json_serialization(self):
        """Test JSON serialization of types."""
        config = AgentConfig(
            name="Test",
            description="Test agent",
            model="gpt-4"
        )
        json_str = config.model_dump_json()
        assert "Test" in json_str

    def test_dict_conversion(self):
        """Test dictionary conversion."""
        result = AgentResult(success=True, output="Done")
        data = result.model_dump()
        assert isinstance(data, dict)
        assert data["success"] is True

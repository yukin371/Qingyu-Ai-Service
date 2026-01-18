"""
Tests for Buffer Memory Implementation
"""

import pytest
from datetime import datetime
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.memory.conversation.buffer_memory import BufferMemory
from src.common.types.memory_types import MemoryType, MemoryScope
from src.common.types.agent_types import Message, MessageRole
from src.common.exceptions import (
    MemoryValidationError,
    MemoryOperationError,
)


class TestBufferMemory:
    """Test suite for BufferMemory class."""

    @pytest.fixture
    def memory_config(self):
        """Create a memory configuration for testing."""
        return {
            "max_messages": 10,
            "memory_type": MemoryType.WORKING,
            "scope": MemoryScope.SESSION,
            "session_id": str(uuid4()),
        }

    @pytest.fixture
    def buffer_memory(self, memory_config):
        """Create a BufferMemory instance for testing."""
        return BufferMemory(**memory_config)

    def test_initialization(self, buffer_memory, memory_config):
        """Test memory initialization."""
        assert buffer_memory.max_messages == memory_config["max_messages"]
        assert buffer_memory.memory_type == memory_config["memory_type"]
        assert buffer_memory.scope == memory_config["scope"]
        assert buffer_memory.session_id == memory_config["session_id"]
        assert len(buffer_memory.messages) == 0
        assert buffer_memory.return_messages is True

    def test_initialization_with_custom_params(self):
        """Test initialization with custom parameters."""
        memory = BufferMemory(
            max_messages=5,
            memory_type=MemoryType.EPISODIC,
            scope=MemoryScope.USER,
            user_id="user123",
            return_messages=False,
        )
        assert memory.max_messages == 5
        assert memory.memory_type == MemoryType.EPISODIC
        assert memory.scope == MemoryScope.USER
        assert memory.user_id == "user123"
        assert memory.return_messages is False

    def test_add_message(self, buffer_memory):
        """Test adding a single message."""
        message = Message(
            role=MessageRole.USER,
            content="Hello, how are you?"
        )
        buffer_memory.add_message(message)

        assert len(buffer_memory.messages) == 1
        assert buffer_memory.messages[0].role == MessageRole.USER
        assert buffer_memory.messages[0].content == "Hello, how are you?"

    def test_add_multiple_messages(self, buffer_memory):
        """Test adding multiple messages."""
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
            Message(role=MessageRole.ASSISTANT, content="Hi there!"),
            Message(role=MessageRole.USER, content="How are you?"),
        ]

        for msg in messages:
            buffer_memory.add_message(msg)

        assert len(buffer_memory.messages) == 3
        assert buffer_memory.messages[0].content == "Hello"
        assert buffer_memory.messages[1].content == "Hi there!"
        assert buffer_memory.messages[2].content == "How are you?"

    def test_add_message_langchain_compatibility(self, buffer_memory):
        """Test adding LangChain messages."""
        lc_message = HumanMessage(content="Hello from LangChain")
        buffer_memory.add_message(lc_message)

        assert len(buffer_memory.messages) == 1
        # Should be converted to our Message type
        assert buffer_memory.messages[0].content == "Hello from LangChain"

    def test_max_messages_limit(self, buffer_memory):
        """Test that max_messages limit is respected."""
        # Add more messages than max_messages
        for i in range(15):
            message = Message(
                role=MessageRole.USER,
                content=f"Message {i}"
            )
            buffer_memory.add_message(message)

        # Should only keep last 10 messages
        assert len(buffer_memory.messages) == 10
        assert buffer_memory.messages[0].content == "Message 5"
        assert buffer_memory.messages[-1].content == "Message 14"

    def test_get_messages(self, buffer_memory):
        """Test retrieving messages."""
        messages = [
            Message(role=MessageRole.USER, content="First"),
            Message(role=MessageRole.ASSISTANT, content="Second"),
            Message(role=MessageRole.USER, content="Third"),
        ]

        for msg in messages:
            buffer_memory.add_message(msg)

        retrieved = buffer_memory.get_messages()
        assert len(retrieved) == 3
        assert retrieved[0].content == "First"
        assert retrieved[1].content == "Second"
        assert retrieved[2].content == "Third"

    def test_get_messages_empty(self, buffer_memory):
        """Test getting messages from empty memory."""
        messages = buffer_memory.get_messages()
        assert len(messages) == 0

    def test_get_messages_with_limit(self, buffer_memory):
        """Test getting messages with a limit."""
        for i in range(5):
            buffer_memory.add_message(
                Message(role=MessageRole.USER, content=f"Message {i}")
            )

        messages = buffer_memory.get_messages(limit=3)
        assert len(messages) == 3
        assert messages[0].content == "Message 2"
        assert messages[1].content == "Message 3"
        assert messages[2].content == "Message 4"

    def test_clear(self, buffer_memory):
        """Test clearing memory."""
        for i in range(3):
            buffer_memory.add_message(
                Message(role=MessageRole.USER, content=f"Message {i}")
            )

        assert len(buffer_memory.messages) == 3

        buffer_memory.clear()

        assert len(buffer_memory.messages) == 0

    def test_save_context(self, buffer_memory):
        """Test saving context (LangChain compatibility)."""
        buffer_memory.save_context(
            {"input": "Hello"},
            {"output": "Hi there!"}
        )

        assert len(buffer_memory.messages) == 2
        assert buffer_memory.messages[0].content == "Hello"
        assert buffer_memory.messages[1].content == "Hi there!"

    def test_load_context(self, buffer_memory):
        """Test loading context (LangChain compatibility)."""
        buffer_memory.add_message(
            Message(role=MessageRole.USER, content="Test message")
        )

        context = buffer_memory.load_memory_variables({})
        assert "history" in context
        assert len(context["history"]) == 1

    def test_message_count(self, buffer_memory):
        """Test getting message count."""
        assert buffer_memory.message_count == 0

        for i in range(3):
            buffer_memory.add_message(
                Message(role=MessageRole.USER, content=f"Message {i}")
            )

        assert buffer_memory.message_count == 3

    def test_get_last_message(self, buffer_memory):
        """Test getting the last message."""
        buffer_memory.add_message(
            Message(role=MessageRole.USER, content="First")
        )
        buffer_memory.add_message(
            Message(role=MessageRole.ASSISTANT, content="Second")
        )

        last = buffer_memory.get_last_message()
        assert last is not None
        assert last.content == "Second"
        assert last.role == MessageRole.ASSISTANT

    def test_get_last_message_empty(self, buffer_memory):
        """Test getting last message from empty memory."""
        last = buffer_memory.get_last_message()
        assert last is None

    def test_trim_messages(self, buffer_memory):
        """Test manual message trimming."""
        for i in range(15):
            buffer_memory.add_message(
                Message(role=MessageRole.USER, content=f"Message {i}")
            )

        assert len(buffer_memory.messages) == 10

        # Trim to 5
        buffer_memory.trim_messages(max_messages=5)
        assert len(buffer_memory.messages) == 5
        assert buffer_memory.messages[0].content == "Message 10"

    def test_get_conversation_summary(self, buffer_memory):
        """Test getting conversation summary."""
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
            Message(role=MessageRole.ASSISTANT, content="Hi!"),
            Message(role=MessageRole.USER, content="How are you?"),
        ]

        for msg in messages:
            buffer_memory.add_message(msg)

        summary = buffer_memory.get_conversation_summary()
        assert "messages" in summary
        assert summary["messages"] == 3
        assert "summary" in summary

    def test_filter_by_role(self, buffer_memory):
        """Test filtering messages by role."""
        messages = [
            Message(role=MessageRole.USER, content="User 1"),
            Message(role=MessageRole.ASSISTANT, content="AI 1"),
            Message(role=MessageRole.USER, content="User 2"),
            Message(role=MessageRole.ASSISTANT, content="AI 2"),
        ]

        for msg in messages:
            buffer_memory.add_message(msg)

        user_messages = buffer_memory.filter_by_role(MessageRole.USER)
        assert len(user_messages) == 2
        assert all(msg.role == MessageRole.USER for msg in user_messages)

        ai_messages = buffer_memory.filter_by_role(MessageRole.ASSISTANT)
        assert len(ai_messages) == 2
        assert all(msg.role == MessageRole.ASSISTANT for msg in ai_messages)

    def test_invalid_message_type(self, buffer_memory):
        """Test adding invalid message type."""
        with pytest.raises(MemoryValidationError):
            buffer_memory.add_message(12345)  # Invalid type

    def test_negative_max_messages(self):
        """Test initialization with negative max_messages."""
        with pytest.raises(MemoryValidationError):
            BufferMemory(max_messages=-1)

    def test_concurrent_access(self, buffer_memory):
        """Test thread-safe message addition."""
        import threading

        def add_messages():
            for i in range(10):
                buffer_memory.add_message(
                    Message(role=MessageRole.USER, content=f"Thread message {i}")
                )

        threads = [threading.Thread(target=add_messages) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Should have max_messages (10) due to limit
        assert len(buffer_memory.messages) <= buffer_memory.max_messages

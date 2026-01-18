"""
Tests for Summary Memory Implementation
"""

import pytest
from unittest.mock import Mock, MagicMock

from src.memory.conversation.summary_memory import SummaryMemory
from src.common.types.memory_types import MemoryType, MemoryScope
from src.common.types.agent_types import Message, MessageRole
from src.common.exceptions import MemoryOperationError


class TestSummaryMemory:
    """Test suite for SummaryMemory class."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM."""
        llm = Mock()
        response = Mock()
        response.content = "Summary of conversation"
        llm.invoke = Mock(return_value=response)
        return llm

    @pytest.fixture
    def summary_memory(self, mock_llm):
        """Create a SummaryMemory instance for testing."""
        return SummaryMemory(
            llm=mock_llm,
            max_messages=5,
            memory_type=MemoryType.EPISODIC,
            scope=MemoryScope.SESSION,
        )

    def test_initialization(self, summary_memory, mock_llm):
        """Test memory initialization."""
        assert summary_memory.max_messages == 5
        assert summary_memory.llm == mock_llm
        assert summary_memory.current_summary is None
        assert len(summary_memory.messages) == 0

    def test_add_message_below_limit(self, summary_memory):
        """Test adding messages below the limit."""
        for i in range(3):
            summary_memory.add_message(
                Message(role=MessageRole.USER, content=f"Message {i}")
            )

        assert len(summary_memory.messages) == 3
        assert summary_memory.current_summary is None

    def test_add_message_triggers_summarization(self, summary_memory):
        """Test that exceeding limit triggers summarization."""
        # Add more messages than limit
        for i in range(7):
            summary_memory.add_message(
                Message(role=MessageRole.USER, content=f"Message {i}")
            )

        # Should have triggered summarization
        assert len(summary_memory.messages) <= 5  # max_messages
        # Some messages should be summarized
        assert summary_memory.current_summary is not None

    def test_get_summary(self, summary_memory):
        """Test getting the current summary."""
        assert summary_memory.get_summary() is None

        summary_memory.add_message(
            Message(role=MessageRole.USER, content="Test")
        )

        # Before summarization
        assert summary_memory.get_summary() is None

    def test_get_messages_with_summary(self, summary_memory):
        """Test getting messages with summary."""
        result = summary_memory.get_messages_with_summary()

        assert "summary" in result
        assert "messages" in result
        assert result["summary"] is None
        assert len(result["messages"]) == 0

    def test_clear(self, summary_memory):
        """Test clearing memory and summary."""
        summary_memory.add_message(
            Message(role=MessageRole.USER, content="Test")
        )

        summary_memory.clear()

        assert len(summary_memory.messages) == 0
        assert summary_memory.current_summary is None

    def test_get_conversation_summary(self, summary_memory):
        """Test getting conversation summary."""
        summary = summary_memory.get_conversation_summary()

        assert "has_summary" in summary
        assert "summary_length" in summary
        assert summary["has_summary"] is False
        assert summary["summary_length"] == 0

    def test_repr(self, summary_memory):
        """Test string representation."""
        repr_str = repr(summary_memory)
        assert "SummaryMemory" in repr_str
        assert "messages=0" in repr_str
        assert "has_summary=False" in repr_str


# Basic tests only - comprehensive tests would require mocking LLM behavior more thoroughly

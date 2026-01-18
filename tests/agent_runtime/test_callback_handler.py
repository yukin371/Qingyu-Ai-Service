"""
Tests for AgentCallbackHandler

Tests the callback handler's ability to handle agent lifecycle events.
"""
import pytest
from typing import Any, Dict, List, Optional
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langchain_core.outputs import LLMResult

from src.agent_runtime.callback_handler import AgentCallbackHandler, CallbackEvent


# =============================================================================
# AgentCallbackHandler Tests
# =============================================================================

class TestAgentCallbackHandler:
    """Test AgentCallbackHandler"""

    @pytest.fixture
    def handler(self):
        """Create a callback handler"""
        return AgentCallbackHandler(
            session_id="test_session",
            user_id="test_user",
            enable_langsmith=True,
            enable_streaming=True,
        )

    def test_handler_initialization(self, handler):
        """Test handler initialization"""
        assert handler.session_id == "test_session"
        assert handler.user_id == "test_user"
        assert handler.enable_langsmith is True
        assert handler.enable_streaming is True
        assert len(handler.events) == 0

    def test_on_llm_start(self, handler):
        """Test LLM start event"""
        handler.on_llm_start(
            prompts=["Hello, world!"],
            invocation_params={"model": "gpt-4", "temperature": 0.7},
        )

        assert len(handler.events) == 1
        event = handler.events[0]
        assert event.event_type == "llm_start"
        assert "prompts" in event.data

    def test_on_llm_end(self, handler):
        """Test LLM end event"""
        # Create a mock LLMResult
        llm_result = MagicMock()
        llm_result.generations = [[MagicMock(text="Hello!")]]
        llm_result.llm_output = {"token_usage": {"total_tokens": 10}}

        handler.on_llm_end(llm_result)

        assert len(handler.events) == 1
        event = handler.events[0]
        assert event.event_type == "llm_end"
        assert "output" in event.data

    def test_on_llm_error(self, handler):
        """Test LLM error event"""
        error = Exception("Test error")

        handler.on_llm_error(error)

        assert len(handler.events) == 1
        event = handler.events[0]
        assert event.event_type == "llm_error"
        assert "error" in event.data
        assert event.data["error"] == "Test error"

    def test_on_chain_start(self, handler):
        """Test chain start event"""
        handler.on_chain_start(
            inputs={"text": "test"},
        )

        assert len(handler.events) == 1
        event = handler.events[0]
        assert event.event_type == "chain_start"

    def test_on_chain_end(self, handler):
        """Test chain end event"""
        handler.on_chain_end(
            outputs={"result": "success"},
        )

        assert len(handler.events) == 1
        event = handler.events[0]
        assert event.event_type == "chain_end"
        assert event.data["outputs"]["result"] == "success"

    def test_on_chain_error(self, handler):
        """Test chain error event"""
        error = ValueError("Chain failed")

        handler.on_chain_error(error)

        assert len(handler.events) == 1
        event = handler.events[0]
        assert event.event_type == "chain_error"

    def test_on_tool_start(self, handler):
        """Test tool start event"""
        handler.on_tool_start(
            tool_name="search",
            input_str={"query": "test"},
        )

        assert len(handler.events) == 1
        event = handler.events[0]
        assert event.event_type == "tool_start"
        assert event.data["tool_name"] == "search"

    def test_on_tool_end(self, handler):
        """Test tool end event"""
        handler.on_tool_end(
            output="Search results",
        )

        assert len(handler.events) == 1
        event = handler.events[0]
        assert event.event_type == "tool_end"
        assert event.data["output"] == "Search results"

    def test_on_tool_error(self, handler):
        """Test tool error event"""
        error = RuntimeError("Tool failed")

        handler.on_tool_error(error)

        assert len(handler.events) == 1
        event = handler.events[0]
        assert event.event_type == "tool_error"

    def test_get_events_by_type(self, handler):
        """Test filtering events by type"""
        handler.on_llm_start(["test"])
        handler.on_llm_new_token("token")
        handler.on_llm_end(MagicMock())

        llm_events = handler.get_events_by_type("llm_")
        assert len(llm_events) == 3

        tool_events = handler.get_events_by_type("tool_")
        assert len(tool_events) == 0

    def test_get_events_since(self, handler):
        """Test filtering events by time"""
        import time

        handler.on_llm_start(["test1"])
        time.sleep(0.01)
        timestamp = datetime.utcnow()
        time.sleep(0.01)
        handler.on_llm_start(["test2"])

        recent_events = handler.get_events_since(timestamp)
        assert len(recent_events) == 1
        assert recent_events[0].event_type == "llm_start"

    def test_clear_events(self, handler):
        """Test clearing events"""
        handler.on_llm_start(["test"])
        assert len(handler.events) == 1

        handler.clear_events()
        assert len(handler.events) == 0

    def test_get_summary(self, handler):
        """Test getting event summary"""
        handler.on_llm_start(["test"])
        handler.on_tool_start("search", {"query": "test"})
        handler.on_tool_end("result")
        handler.on_llm_end(MagicMock())

        summary = handler.get_summary()
        assert summary["total_events"] == 4
        assert summary["llm_calls"] == 1
        assert summary["tool_calls"] == 1

    def test_stream_to_client(self, handler):
        """Test streaming to client"""
        # Mock streaming callback
        streaming_callback = MagicMock()
        handler.streaming_callback = streaming_callback

        handler.on_llm_new_token("Hello")

        streaming_callback.assert_called_once_with("Hello")

    def test_multiple_sessions(self):
        """Test handlers for different sessions"""
        handler1 = AgentCallbackHandler(session_id="session1", user_id="user1")
        handler2 = AgentCallbackHandler(session_id="session2", user_id="user2")

        handler1.on_llm_start(["test1"])
        handler2.on_llm_start(["test2"])

        assert len(handler1.events) == 1
        assert len(handler2.events) == 1
        assert handler1.events[0].data["prompts"] == ["test1"]
        assert handler2.events[0].data["prompts"] == ["test2"]


# =============================================================================
# CallbackEvent Tests
# =============================================================================

class TestCallbackEvent:
    """Test CallbackEvent"""

    def test_event_creation(self):
        """Test creating an event"""
        event = CallbackEvent(
            event_type="test_event",
            data={"key": "value"},
            session_id="test_session",
            user_id="test_user",
        )

        assert event.event_type == "test_event"
        assert event.data["key"] == "value"
        assert event.session_id == "test_session"
        assert event.user_id == "test_user"
        assert isinstance(event.timestamp, datetime)

    def test_event_to_dict(self):
        """Test converting event to dict"""
        event = CallbackEvent(
            event_type="test",
            data={"key": "value"},
            session_id="session",
            user_id="user",
        )

        event_dict = event.to_dict()
        assert event_dict["event_type"] == "test"
        assert event_dict["data"]["key"] == "value"
        assert "timestamp" in event_dict

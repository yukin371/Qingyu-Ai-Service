"""
Tests for event type definitions
"""

import pytest

from src.common.types.event_types import (
    EventType,
    EventPriority,
    BaseEvent,
    SystemEvent,
    ToolEvent,
    AgentEvent,
    EventSubscription,
)


class TestEventType:
    """Test EventType enum."""

    def test_system_events(self):
        """Test system event types."""
        assert EventType.SYSTEM_STARTUP.value == "system.startup"
        assert EventType.SYSTEM_SHUTDOWN.value == "system.shutdown"
        assert EventType.SYSTEM_ERROR.value == "system.error"

    def test_agent_events(self):
        """Test agent event types."""
        assert EventType.AGENT_CREATED.value == "agent.created"
        assert EventType.AGENT_STARTED.value == "agent.started"
        assert EventType.AGENT_COMPLETED.value == "agent.completed"

    def test_tool_events(self):
        """Test tool event types."""
        assert EventType.TOOL_REGISTERED.value == "tool.registered"
        assert EventType.TOOL_CALLED.value == "tool.called"
        assert EventType.TOOL_COMPLETED.value == "tool.completed"


class TestEventPriority:
    """Test EventPriority enum."""

    def test_values(self):
        """Test priority values."""
        assert EventPriority.CRITICAL.value == "critical"
        assert EventPriority.HIGH.value == "high"
        assert EventPriority.MEDIUM.value == "medium"
        assert EventPriority.LOW.value == "low"


class TestBaseEvent:
    """Test BaseEvent."""

    def test_create_base_event(self):
        """Test creating base event."""
        event = BaseEvent(
            event_type=EventType.SYSTEM_STARTUP,
            source="system"
        )
        assert event.event_type == EventType.SYSTEM_STARTUP
        assert event.source == "system"
        assert event.priority == EventPriority.MEDIUM

    def test_event_with_metadata(self):
        """Test event with metadata."""
        event = BaseEvent(
            event_type=EventType.AGENT_STARTED,
            source="agent_manager",
            metadata={"agent_id": "agent_1"}
        )
        assert event.metadata["agent_id"] == "agent_1"


class TestSystemEvent:
    """Test SystemEvent."""

    def test_create_system_event(self):
        """Test creating system event."""
        event = SystemEvent(
            event_type=EventType.SYSTEM_ERROR,
            source="database",
            component="database",
            message="Connection failed"
        )
        assert event.component == "database"
        assert event.message == "Connection failed"


class TestToolEvent:
    """Test ToolEvent."""

    def test_create_tool_event(self):
        """Test creating tool event."""
        event = ToolEvent(
            event_type=EventType.TOOL_CALLED,
            tool_name="search",
            source="agent_1",
            agent_id="agent_1"
        )
        assert event.tool_name == "search"
        assert event.agent_id == "agent_1"

    def test_tool_event_with_result(self):
        """Test tool event with result."""
        event = ToolEvent(
            event_type=EventType.TOOL_COMPLETED,
            tool_name="calculator",
            source="agent_1",
            result=42,
            execution_time=0.5
        )
        assert event.result == 42
        assert event.execution_time == 0.5


class TestAgentEvent:
    """Test AgentEvent."""

    def test_create_agent_event(self):
        """Test creating agent event."""
        event = AgentEvent(
            event_type=EventType.AGENT_STARTED,
            agent_id="agent_1",
            source="agent_manager"
        )
        assert event.agent_id == "agent_1"


class TestEventSubscription:
    """Test EventSubscription."""

    def test_create_subscription(self):
        """Test creating subscription."""
        subscription = EventSubscription(
            subscriber_id="service_1",
            event_types=[EventType.AGENT_STARTED, EventType.AGENT_COMPLETED]
        )
        assert subscription.subscriber_id == "service_1"
        assert len(subscription.event_types) == 2
        assert subscription.active is True

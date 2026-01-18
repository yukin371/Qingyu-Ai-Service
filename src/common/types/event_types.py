"""
Event Type Definitions

This module defines all types related to the event system, including
event types, priorities, and event structures.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# Enums
# =============================================================================

class EventType(str, Enum):
    """Types of events in the system."""

    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"

    # Agent events
    AGENT_CREATED = "agent.created"
    AGENT_STARTED = "agent.started"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    AGENT_THINKING = "agent.thinking"
    AGENT_ACTION = "agent.action"

    # Tool events
    TOOL_REGISTERED = "tool.registered"
    TOOL_CALLED = "tool.called"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"

    # Memory events
    MEMORY_STORED = "memory.stored"
    MEMORY_RETRIEVED = "memory.retrieved"
    MEMORY_DELETED = "memory.deleted"

    # Workflow events
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_STEP_COMPLETED = "workflow.step_completed"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"

    # User events
    USER_CONNECTED = "user.connected"
    USER_DISCONNECTED = "user.disconnect"
    USER_MESSAGE = "user.message"


class EventPriority(str, Enum):
    """Priority levels for events."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# =============================================================================
# Base Event
# =============================================================================

class BaseEvent(BaseModel):
    """
    Base class for all events.

    Attributes:
        event_id: Unique identifier for the event
        event_type: Type of the event
        timestamp: When the event occurred
        priority: Priority level of the event
        source: Source of the event
        metadata: Additional metadata
    """

    event_id: UUID = Field(default_factory=uuid4)
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    priority: EventPriority = EventPriority.MEDIUM
    source: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=False)


# =============================================================================
# System Events
# =============================================================================

class SystemEvent(BaseEvent):
    """
    System-level event.

    Attributes:
        component: Component that generated the event
        message: Human-readable message
        details: Additional details about the event
    """

    event_type: EventType
    component: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Tool Events
# =============================================================================

class ToolEvent(BaseEvent):
    """
    Tool-related event.

    Attributes:
        tool_name: Name of the tool
        agent_id: ID of the agent using the tool
        arguments: Arguments passed to the tool
        result: Result of the tool execution (if completed)
        error: Error message (if failed)
        execution_time: Time taken to execute the tool
    """

    event_type: EventType
    tool_name: str
    agent_id: Optional[str] = None
    arguments: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None


# =============================================================================
# Agent Events
# =============================================================================

class AgentEvent(BaseEvent):
    """
    Agent-related event.

    Attributes:
        agent_id: ID of the agent
        task: Task the agent is working on
        status: Current status of the agent
        context: Context information
    """

    event_type: EventType
    agent_id: str
    task: Optional[str] = None
    status: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Event Subscription
# =============================================================================

class EventSubscription(BaseModel):
    """
    Subscription to events.

    Attributes:
        subscription_id: Unique identifier for the subscription
        subscriber_id: ID of the subscriber
        event_types: List of event types to subscribe to
        filter_criteria: Optional filter criteria
        callback_url: URL to send events to (if using webhook)
        active: Whether the subscription is active
        created_at: When the subscription was created
    """

    subscription_id: UUID = Field(default_factory=uuid4)
    subscriber_id: str
    event_types: List[EventType]
    filter_criteria: Dict[str, Any] = Field(default_factory=dict)
    callback_url: Optional[str] = None
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(use_enum_values=False)


# =============================================================================
# Export all types
# =============================================================================

__all__ = [
    # Enums
    "EventType",
    "EventPriority",
    # Base
    "BaseEvent",
    # System
    "SystemEvent",
    # Tool
    "ToolEvent",
    # Agent
    "AgentEvent",
    # Subscription
    "EventSubscription",
]

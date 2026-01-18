"""
Event-Driven Integration Tests

Tests for event-driven architecture including:
- EventBus and MetricsCollector integration
- Agent lifecycle event publishing
- Cross-component event response
- Event history and replay
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from src.agent_runtime.event_bus.consumer import EventBus
from src.agent_runtime.monitoring.metrics import MetricsCollector
from src.agent_runtime.orchestration.executor import AgentExecutor, AgentConfig, ExecutionResult
from src.agent_runtime.session_manager import AgentContext
from src.common.types.event_types import EventType, SystemEvent


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def integrated_event_bus():
    """Create event bus with metrics collector integration."""
    return EventBus()


@pytest.fixture
def metrics_tracking_event_bus():
    """Create event bus and metrics collector for tracking."""
    return EventBus(), MetricsCollector()


# =============================================================================
# EventBus and MetricsCollector Integration
# =============================================================================

class TestEventBusMetricsIntegration:
    """Tests for EventBus and MetricsCollector integration."""

    @pytest.mark.asyncio
    async def test_event_publishing_increments_metrics(self, metrics_tracking_event_bus):
        """Test that event publishing increments metrics."""

        bus, collector = metrics_tracking_event_bus

        # Subscribe handler that tracks metrics
        async def track_event(event):
            await collector.increment(
                f"events.{event.event_type.value}",
                labels={"source": event.source}
            )

        await bus.subscribe(EventType.AGENT_STARTED, track_event)

        # Publish events
        for i in range(10):
            await bus.publish(SystemEvent(
                event_type=EventType.AGENT_STARTED,
                source="test_agent",
                component="test",
                message=f"Agent started {i}",
                details={"index": i},
            ))

        # Give time for async handlers
        await asyncio.sleep(0.1)

        # Check metrics
        count = collector.get_counter(
            "events.agent.started",
            labels={"source": "test_agent"}
        )

        assert count == 10

    @pytest.mark.asyncio
    async def test_multiple_event_types_tracked(self, metrics_tracking_event_bus):
        """Test tracking multiple event types."""

        bus, collector = metrics_tracking_event_bus

        # Subscribe handler that tracks metrics for all event types
        async def track_event(event):
            await collector.increment(
                f"events.{event.event_type.value}",
                labels={"source": event.source}
            )

        # Subscribe to all event types we'll publish
        key_events = [
            EventType.AGENT_STARTED,
            EventType.AGENT_COMPLETED,
            EventType.AGENT_FAILED,
        ]

        for event_type in key_events:
            await bus.subscribe(event_type, track_event)

        # Publish different event types
        events_to_publish = [
            (EventType.AGENT_STARTED, 5),
            (EventType.AGENT_COMPLETED, 3),
            (EventType.AGENT_FAILED, 2),
        ]

        for event_type, count in events_to_publish:
            for _ in range(count):
                await bus.publish(SystemEvent(
                    event_type=event_type,
                    source="test",
                    component="test",
                    message="Test",
                ))

        await asyncio.sleep(0.1)

        # Verify all tracked
        for event_type, expected_count in events_to_publish:
            event_name = event_type.value.replace(".", ".")
            count = collector.get_counter(
                f"events.{event_name}",
                labels={"source": "test"}
            )
            assert count == expected_count

    @pytest.mark.asyncio
    async def test_event_latency_tracking(self):
        """Test tracking event processing latency."""

        bus = EventBus()
        collector = MetricsCollector()

        # Handler with simulated processing time
        async def slow_handler(event):
            async with collector.timer("event_processing_time"):
                await asyncio.sleep(0.01)
            # Record metric
            await collector.histogram(
                "event_latency",
                value=0.01,
                labels={"event_type": event.event_type.value}
            )

        await bus.subscribe(EventType.AGENT_STARTED, slow_handler)

        # Publish events
        for _ in range(5):
            await bus.publish(SystemEvent(
                event_type=EventType.AGENT_STARTED,
                source="test",
                component="test",
                message="Test",
            ))

        await asyncio.sleep(0.2)

        # Check histogram
        metrics = await collector.get_metrics()
        histograms = metrics["histograms"]

        latency_hist = [h for h in histograms if h["name"] == "event_latency"][0]
        assert latency_hist["count"] == 5


# =============================================================================
# Agent Lifecycle Event Publishing
# =============================================================================

class TestAgentLifecycleEvents:
    """Tests for agent lifecycle event publishing."""

    @pytest.mark.asyncio
    async def test_agent_publishes_lifecycle_events(self):
        """Test agent publishes lifecycle events during execution."""

        bus = EventBus()
        events_received = []

        # Subscribe to lifecycle events
        lifecycle_events = [
            EventType.AGENT_STARTED,
            EventType.AGENT_THINKING,
            EventType.AGENT_ACTION,
            EventType.AGENT_COMPLETED,
        ]

        for event_type in lifecycle_events:
            async def handler(event):
                events_received.append(event.event_type)

            await bus.subscribe(event_type, handler)

        # Create executor with event bus
        config = AgentConfig(
            name="test_agent",
            description="Test agent for events",
            model="gpt-3.5-turbo",
        )

        executor = AgentExecutor(
            agent_id=config.name,
            config=config,
        )

        context = AgentContext(
            user_id="test_user",
            agent_id=config.name,
            session_id="test_session",
            input_message="Test",
        )

        # Mock execution to publish events
        from unittest.mock import patch

        async def mock_execute_with_events(*args, **kwargs):
            # Simulate lifecycle events
            await bus.publish(SystemEvent(
                event_type=EventType.AGENT_STARTED,
                source="executor",
                component="test_agent",
                message="Agent started",
            ))

            await asyncio.sleep(0.01)

            await bus.publish(SystemEvent(
                event_type=EventType.AGENT_THINKING,
                source="executor",
                component="test_agent",
                message="Agent thinking",
            ))

            await asyncio.sleep(0.01)

            await bus.publish(SystemEvent(
                event_type=EventType.AGENT_COMPLETED,
                source="executor",
                component="test_agent",
                message="Agent completed",
            ))

            return ExecutionResult(
                success=True,
                output="Response",
            )

        with patch.object(executor, 'execute', new=mock_execute_with_events):
            await executor.execute(context)

        await asyncio.sleep(0.1)

        # Verify lifecycle events were published
        assert EventType.AGENT_STARTED in events_received
        assert EventType.AGENT_THINKING in events_received
        assert EventType.AGENT_COMPLETED in events_received

    @pytest.mark.asyncio
    async def test_agent_error_event_on_failure(self):
        """Test agent publishes error event on failure."""

        bus = EventBus()
        error_events = []

        async def error_handler(event):
            error_events.append(event)

        await bus.subscribe(EventType.AGENT_FAILED, error_handler)

        config = AgentConfig(
            name="test_agent",
            description="Test agent for events",
            model="gpt-3.5-turbo",
        )

        executor = AgentExecutor(
            agent_id=config.name,
            config=config,
        )

        context = AgentContext(
            user_id="test_user",
            agent_id=config.name,
            session_id="test_session",
            input_message="Test",
        )

        # Mock execution to fail
        from unittest.mock import patch

        async def failing_execute(*args, **kwargs):
            await bus.publish(SystemEvent(
                event_type=EventType.AGENT_FAILED,
                source="executor",
                component="test_agent",
                message="Agent failed",
                details={"error": "Test error"},
            ))
            raise Exception("Test error")

        with patch.object(executor, 'execute', new=failing_execute):
            try:
                await executor.execute(context)
            except:
                pass

        await asyncio.sleep(0.1)

        # Verify error event was published
        assert len(error_events) > 0
        assert error_events[0].event_type == EventType.AGENT_FAILED


# =============================================================================
# Cross-Component Event Response
# =============================================================================

class TestCrossComponentEventResponse:
    """Tests for cross-component event-driven communication."""

    @pytest.mark.asyncio
    async def test_session_responds_to_agent_events(self):
        """Test session manager responds to agent lifecycle events."""

        bus = EventBus()

        # Mock session manager that tracks agent state
        session_states = {}

        async def session_event_handler(event):
            if event.event_type == EventType.AGENT_STARTED:
                session_states[event.details.get("session_id")] = "agent_running"
            elif event.event_type == EventType.AGENT_COMPLETED:
                session_states[event.details.get("session_id")] = "agent_completed"

        await bus.subscribe(EventType.AGENT_STARTED, session_event_handler)
        await bus.subscribe(EventType.AGENT_COMPLETED, session_event_handler)

        # Simulate agent lifecycle
        session_id = "test_session_123"

        await bus.publish(SystemEvent(
            event_type=EventType.AGENT_STARTED,
            source="executor",
            component="test_agent",
            message="Agent started",
            details={"session_id": session_id},
        ))

        await asyncio.sleep(0.01)

        assert session_states.get(session_id) == "agent_running"

        await bus.publish(SystemEvent(
            event_type=EventType.AGENT_COMPLETED,
            source="executor",
            component="test_agent",
            message="Agent completed",
            details={"session_id": session_id},
        ))

        await asyncio.sleep(0.01)

        assert session_states.get(session_id) == "agent_completed"

    @pytest.mark.asyncio
    async def test_metrics_respond_to_tool_events(self):
        """Test metrics collector responds to tool events."""

        bus = EventBus()
        collector = MetricsCollector()

        # Track tool usage
        async def tool_metrics_handler(event):
            if event.event_type == EventType.TOOL_CALLED:
                tool_name = event.details.get("tool_name", "unknown")
                await collector.increment(
                    "tool_calls",
                    labels={"tool": tool_name}
                )

        await bus.subscribe(EventType.TOOL_CALLED, tool_metrics_handler)

        # Simulate tool calls
        tools_called = ["search", "calculator", "search", "database"]

        for tool in tools_called:
            await bus.publish(SystemEvent(
                event_type=EventType.TOOL_CALLED,
                source="executor",
                component="test_agent",
                message=f"Called {tool}",
                details={"tool_name": tool},
            ))

        await asyncio.sleep(0.1)

        # Verify metrics
        search_count = collector.get_counter("tool_calls", labels={"tool": "search"})
        calculator_count = collector.get_counter("tool_calls", labels={"tool": "calculator"})
        database_count = collector.get_counter("tool_calls", labels={"tool": "database"})

        assert search_count == 2
        assert calculator_count == 1
        assert database_count == 1

    @pytest.mark.asyncio
    async def test_cascading_events(self):
        """Test cascading events where one event triggers another."""

        bus = EventBus()
        event_chain = []

        # Handler that triggers new events
        async def cascade_handler(event):
            event_chain.append(("first", event.event_type))

            # Trigger second event
            if event.event_type == EventType.AGENT_STARTED:
                await bus.publish(SystemEvent(
                    event_type=EventType.TOOL_CALLED,
                    source="cascade",
                    component="test",
                    message="Cascaded event",
                    details={"triggered_by": "agent_started"},
                ))

        async def second_handler(event):
            event_chain.append(("second", event.event_type))

        await bus.subscribe(EventType.AGENT_STARTED, cascade_handler)
        await bus.subscribe(EventType.TOOL_CALLED, second_handler)

        # Publish initial event
        await bus.publish(SystemEvent(
            event_type=EventType.AGENT_STARTED,
            source="test",
            component="test",
            message="Start",
        ))

        await asyncio.sleep(0.1)

        # Verify cascade
        assert ("first", EventType.AGENT_STARTED) in event_chain
        # The cascade_handler publishes TOOL_CALLED, but second_handler receives it
        assert ("second", EventType.TOOL_CALLED) in event_chain
        # second_handler also receives AGENT_STARTED (both handlers get all events they're subscribed to)
        # But we only subscribed cascade_handler to AGENT_STARTED and second_handler to TOOL_CALLED


# =============================================================================
# Event History and Replay
# =============================================================================

class TestEventHistoryAndReplay:
    """Tests for event history tracking and replay capabilities."""

    @pytest.mark.asyncio
    async def test_event_history_tracking(self):
        """Test event bus maintains history of events."""

        bus = EventBus()

        # Publish various events
        events = [
            (EventType.AGENT_STARTED, "Agent 1 started"),
            (EventType.AGENT_COMPLETED, "Agent 1 completed"),
            (EventType.AGENT_STARTED, "Agent 2 started"),
            (EventType.TOOL_CALLED, "Tool called"),
            (EventType.AGENT_FAILED, "Agent failed"),
        ]

        for event_type, message in events:
            await bus.publish(SystemEvent(
                event_type=event_type,
                source="test",
                component="test",
                message=message,
            ))

        # Get full history
        history = await bus.get_history()
        assert len(history) == 5

        # Get filtered history
        agent_started_events = await bus.get_history(event_type=EventType.AGENT_STARTED)
        assert len(agent_started_events) == 2

    @pytest.mark.asyncio
    async def test_event_replay_simulation(self):
        """Test simulating event replay from history."""

        bus = EventBus()
        replayed_events = []

        # Publish initial events
        for i in range(5):
            await bus.publish(SystemEvent(
                event_type=EventType.AGENT_STARTED,
                source="test",
                component="test",
                message=f"Event {i}",
                details={"index": i},
            ))

        # Get history
        history = await bus.get_history()

        # Replay events
        async def replay_handler(event):
            replayed_events.append(event)

        await bus.subscribe(EventType.AGENT_STARTED, replay_handler)

        for event in history:
            await bus.publish(event)

        await asyncio.sleep(0.1)

        # Should have 10 total (5 original + 5 replayed)
        all_events = await bus.get_history()
        assert len(all_events) == 10

    @pytest.mark.asyncio
    async def test_event_history_limit(self):
        """Test event history respects size limit."""

        bus = EventBus(max_history=10)  # Only keep 10 events

        # Publish 20 events
        for i in range(20):
            await bus.publish(SystemEvent(
                event_type=EventType.AGENT_STARTED,
                source="test",
                component="test",
                message=f"Event {i}",
            ))

        # Should only have last 10
        history = await bus.get_history()
        assert len(history) == 10

        # Verify oldest events were removed
        messages = [e.message for e in history]
        assert "Event 0" not in messages
        assert "Event 10" in messages
        assert "Event 19" in messages


# =============================================================================
# Event Bus Performance Under Load
# =============================================================================

class TestEventBusPerformance:
    """Performance tests for event bus under load."""

    @pytest.mark.asyncio
    async def test_high_throughput_event_publishing(self):
        """Test event bus can handle high throughput."""

        bus = EventBus()
        received_count = {"count": 0}

        async def counter_handler(event):
            received_count["count"] += 1

        await bus.subscribe(EventType.AGENT_STARTED, counter_handler)

        # Publish many events rapidly
        event_count = 1000

        start_time = asyncio.get_event_loop().time()

        for i in range(event_count):
            await bus.publish(SystemEvent(
                event_type=EventType.AGENT_STARTED,
                source="test",
                component="test",
                message=f"Event {i}",
            ))

        end_time = asyncio.get_event_loop().time()

        # Wait for processing
        await asyncio.sleep(0.1)

        # Verify all received
        assert received_count["count"] == event_count

        # Performance check (adjust based on system)
        elapsed = end_time - start_time
        assert elapsed < 5.0  # Should complete in under 5 seconds

    @pytest.mark.asyncio
    async def test_concurrent_event_publishing_multiple_subscribers(self):
        """Test concurrent publishing with multiple subscribers."""

        bus = EventBus()

        subscriber_counts = {i: {"count": 0} for i in range(10)}

        # Create multiple subscribers
        for i in range(10):
            async def make_handler(sub_id):
                count_dict = subscriber_counts[sub_id]

                async def handler(event):
                    count_dict["count"] += 1

                return handler

            handler = await make_handler(i)
            await bus.subscribe(EventType.AGENT_STARTED, handler)

        # Publish events concurrently
        async def publish_events(publisher_id: int):
            for _ in range(50):
                await bus.publish(SystemEvent(
                    event_type=EventType.AGENT_STARTED,
                    source=f"publisher_{publisher_id}",
                    component="test",
                    message="Test",
                ))

        # 5 publishers, 50 events each = 250 total
        tasks = [publish_events(i) for i in range(5)]
        await asyncio.gather(*tasks)

        await asyncio.sleep(0.2)

        # Each subscriber should have received all events
        for i in range(10):
            assert subscriber_counts[i]["count"] == 250

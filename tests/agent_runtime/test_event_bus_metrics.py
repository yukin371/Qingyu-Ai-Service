"""
EventBus and Metrics Tests

Tests for EventBus and MetricsCollector.
"""

import pytest
import asyncio

from src.agent_runtime.event_bus.consumer import EventBus, get_event_bus
from src.agent_runtime.monitoring.metrics import MetricsCollector, get_metrics_collector, _TimerContext
from src.common.types.event_types import EventType, SystemEvent


# =============================================================================
# EventBus Tests
# =============================================================================

class TestEventBus:
    """Tests for EventBus."""

    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self):
        """Test subscribing and publishing events."""
        bus = EventBus()

        received = []

        def handler(event):
            received.append(event)

        await bus.subscribe(EventType.AGENT_STARTED, handler)

        await bus.publish(SystemEvent(
            event_type=EventType.AGENT_STARTED,
            source="test",
            component="test_agent",
            message="Agent started",
            details={"agent_id": "agent_123", "task": "test"},
        ))

        assert len(received) == 1
        assert received[0].details["agent_id"] == "agent_123"

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self):
        """Test multiple subscribers to same event."""
        bus = EventBus()

        results = []

        async def handler1(event):
            results.append("handler1")

        async def handler2(event):
            results.append("handler2")

        await bus.subscribe(EventType.AGENT_STARTED, handler1)
        await bus.subscribe(EventType.AGENT_STARTED, handler2)

        await bus.publish(SystemEvent(
            event_type=EventType.AGENT_STARTED,
            source="test",
            component="test_agent",
            message="Agent started",
            details={"agent_id": "agent_123"},
        ))

        assert len(results) == 2
        assert "handler1" in results
        assert "handler2" in results

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        """Test unsubscribing from events."""
        bus = EventBus()

        received = []

        def handler(event):
            received.append(event)

        await bus.subscribe(EventType.AGENT_STARTED, handler, name="my_handler")

        # Publish first event
        await bus.publish(SystemEvent(
            event_type=EventType.AGENT_STARTED,
            source="test",
            component="test_agent",
            message="Agent started",
            details={"agent_id": "agent_123"},
        ))
        assert len(received) == 1

        # Unsubscribe
        await bus.unsubscribe(EventType.AGENT_STARTED, "my_handler")

        # Publish second event
        await bus.publish(SystemEvent(
            event_type=EventType.AGENT_STARTED,
            source="test",
            component="test_agent",
            message="Agent started",
            details={"agent_id": "agent_456"},
        ))
        assert len(received) == 1  # No new events

    @pytest.mark.asyncio
    async def test_event_history(self):
        """Test event history tracking."""
        bus = EventBus()

        await bus.publish(SystemEvent(
            event_type=EventType.AGENT_STARTED,
            source="test",
            component="agent",
            message="Started",
            details={"agent_id": "agent_1"},
        ))
        await bus.publish(SystemEvent(
            event_type=EventType.AGENT_COMPLETED,
            source="test",
            component="agent",
            message="Completed",
            details={"agent_id": "agent_1"},
        ))
        await bus.publish(SystemEvent(
            event_type=EventType.AGENT_STARTED,
            source="test",
            component="agent",
            message="Started",
            details={"agent_id": "agent_2"},
        ))

        history = await bus.get_history()
        assert len(history) == 3

        # Filter by type
        started_events = await bus.get_history(event_type=EventType.AGENT_STARTED)
        assert len(started_events) == 2

    @pytest.mark.asyncio
    async def test_get_handler_count(self):
        """Test getting handler count."""
        bus = EventBus()

        async def handler1(event):
            pass

        async def handler2(event):
            pass

        await bus.subscribe(EventType.AGENT_STARTED, handler1)
        await bus.subscribe(EventType.AGENT_STARTED, handler2)
        await bus.subscribe(EventType.AGENT_COMPLETED, handler1)

        assert bus.get_handler_count(EventType.AGENT_STARTED) == 2
        assert bus.get_handler_count(EventType.AGENT_COMPLETED) == 1

    @pytest.mark.asyncio
    async def test_enable_disable_handler(self):
        """Test enabling and disabling handlers."""
        bus = EventBus()

        received = []

        def handler(event):
            received.append(event)

        await bus.subscribe(EventType.AGENT_STARTED, handler, name="my_handler")

        # Publish with enabled handler
        await bus.publish(SystemEvent(
            event_type=EventType.AGENT_STARTED,
            source="test",
            component="test",
            message="Started",
            details={"agent_id": "agent_1"},
        ))
        assert len(received) == 1

        # Disable handler
        assert bus.disable_handler(EventType.AGENT_STARTED, "my_handler") is True

        # Publish with disabled handler
        await bus.publish(SystemEvent(
            event_type=EventType.AGENT_STARTED,
            source="test",
            component="test",
            message="Started",
            details={"agent_id": "agent_2"},
        ))
        assert len(received) == 1  # No new events

        # Re-enable handler
        assert bus.enable_handler(EventType.AGENT_STARTED, "my_handler") is True

        # Publish with re-enabled handler
        await bus.publish(SystemEvent(
            event_type=EventType.AGENT_STARTED,
            source="test",
            component="test",
            message="Started",
            details={"agent_id": "agent_3"},
        ))
        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_global_event_bus(self):
        """Test global event bus instance."""
        bus1 = get_event_bus()
        bus2 = get_event_bus()

        assert bus1 is bus2  # Same instance


# =============================================================================
# MetricsCollector Tests
# =============================================================================

class TestMetricsCollector:
    """Tests for MetricsCollector."""

    @pytest.mark.asyncio
    async def test_increment_counter(self):
        """Test incrementing counters."""
        collector = MetricsCollector()

        await collector.increment("requests_total", value=1)
        await collector.increment("requests_total", value=2)

        assert collector.get_counter("requests_total") == 3

    @pytest.mark.asyncio
    async def test_counter_with_labels(self):
        """Test counters with labels."""
        collector = MetricsCollector()

        await collector.increment("requests_total", labels={"endpoint": "/api/chat"})
        await collector.increment("requests_total", labels={"endpoint": "/api/completion"})

        assert collector.get_counter("requests_total", labels={"endpoint": "/api/chat"}) == 1
        assert collector.get_counter("requests_total", labels={"endpoint": "/api/completion"}) == 1

    @pytest.mark.asyncio
    async def test_decrement_counter(self):
        """Test decrementing counters."""
        collector = MetricsCollector()

        await collector.increment("active_connections", value=10)
        await collector.decrement("active_connections", value=3)

        assert collector.get_counter("active_connections") == 7

    @pytest.mark.asyncio
    async def test_set_gauge(self):
        """Test setting gauge values."""
        collector = MetricsCollector()

        await collector.gauge("memory_usage", 80.5)
        await collector.gauge("cpu_usage", 45.2)

        assert collector.get_gauge("memory_usage") == 80.5
        assert collector.get_gauge("cpu_usage") == 45.2

    @pytest.mark.asyncio
    async def test_histogram(self):
        """Test histogram recording."""
        collector = MetricsCollector()

        await collector.histogram("request_duration", 0.5)
        await collector.histogram("request_duration", 1.5)
        await collector.histogram("request_duration", 5.0)

        metrics = await collector.get_metrics()
        histograms = metrics["histograms"]

        assert len(histograms) == 1
        assert histograms[0]["count"] == 3
        assert histograms[0]["sum"] == 7.0

    @pytest.mark.asyncio
    async def test_timer_context(self):
        """Test timer context manager."""
        collector = MetricsCollector()

        async with collector.timer("operation_duration"):
            await asyncio.sleep(0.01)

        metrics = await collector.get_metrics()
        histograms = metrics["histograms"]

        # Find the histogram for our operation
        op_hist = None
        for h in histograms:
            if h["name"] == "operation_duration":
                op_hist = h
                break

        assert op_hist is not None, f"operation_duration histogram not found. Available: {[h['name'] for h in histograms]}"
        assert op_hist["count"] == 1
        assert op_hist["sum"] > 0

    @pytest.mark.asyncio
    async def test_get_metrics(self):
        """Test getting all metrics."""
        collector = MetricsCollector()

        await collector.increment("counter1", value=5)
        await collector.gauge("gauge1", value=100)
        await collector.histogram("hist1", value=1.0)

        metrics = await collector.get_metrics()

        assert "counters" in metrics
        assert "gauges" in metrics
        assert "histograms" in metrics
        assert len(metrics["counters"]) == 1
        assert len(metrics["gauges"]) == 1
        assert len(metrics["histograms"]) == 1

    @pytest.mark.asyncio
    async def test_reset(self):
        """Test resetting metrics."""
        collector = MetricsCollector()

        await collector.increment("test", value=5)
        await collector.gauge("test", value=100)

        assert collector.get_counter("test") == 5
        assert collector.get_gauge("test") == 100

        await collector.reset()

        metrics = await collector.get_metrics()
        assert len(metrics["counters"]) == 0
        assert len(metrics["gauges"]) == 0

    @pytest.mark.asyncio
    async def test_global_metrics_collector(self):
        """Test global metrics collector instance."""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()

        assert collector1 is collector2  # Same instance

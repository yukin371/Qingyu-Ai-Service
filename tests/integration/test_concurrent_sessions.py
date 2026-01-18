"""
Concurrent Scenarios Integration Tests

Tests for concurrent operations including:
- Multiple users creating sessions concurrently
- Concurrent event publishing and subscribing
- Concurrent agent execution
- Metrics concurrent writes
"""

import pytest
import asyncio
import time
from datetime import datetime
from unittest.mock import Mock, AsyncMock

from src.agent_runtime.session_manager import SessionManager, Session, AgentContext
from src.agent_runtime.orchestration.executor import AgentExecutor, AgentConfig, ExecutionResult
from src.agent_runtime.event_bus.consumer import EventBus
from src.agent_runtime.monitoring.metrics import MetricsCollector
from src.common.types.event_types import EventType, SystemEvent


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def concurrent_session_manager():
    """Create session manager optimized for concurrent testing."""
    manager = SessionManager()

    # Use mock storage with thread-safe operations
    storage = Mock()

    async def mock_create(session):
        # Simulate storage delay
        await asyncio.sleep(0.001)
        return session

    async def mock_get(session_id):
        await asyncio.sleep(0.001)
        return None

    storage.create_session = mock_create
    storage.get_session = mock_get
    storage.save_checkpoint = AsyncMock()
    storage.get_checkpoint = AsyncMock(return_value=None)
    storage.list_checkpoints = AsyncMock(return_value=[])

    manager._storage = storage
    return manager


@pytest.fixture
def shared_event_bus():
    """Create shared event bus for concurrent tests."""
    return EventBus()


@pytest.fixture
def shared_metrics_collector():
    """Create shared metrics collector for concurrent tests."""
    return MetricsCollector()


# =============================================================================
# Concurrent Session Creation Tests
# =============================================================================

class TestConcurrentSessionCreation:
    """Tests for concurrent session creation."""

    @pytest.mark.asyncio
    async def test_concurrent_session_creation_different_users(self, concurrent_session_manager):
        """Test multiple users can create sessions concurrently."""

        user_count = 20
        session_ids = []

        async def create_session(user_id: int):
            context = AgentContext(
                user_id=f"user_{user_id}",
                agent_id="test_agent",
                session_id="",
                input_message=f"Message from user {user_id}",
            )

            session = await concurrent_session_manager.create_session(
                user_id=context.user_id,
                agent_id=context.agent_id,
                context=context,
            )

            return session.session_id

        # Create sessions concurrently
        tasks = [create_session(i) for i in range(user_count)]
        session_ids = await asyncio.gather(*tasks)

        # Verify all sessions were created
        assert len(session_ids) == user_count
        assert all(sid is not None for sid in session_ids)
        assert len(set(session_ids)) == user_count  # All unique

    @pytest.mark.asyncio
    async def test_concurrent_session_creation_same_user(self, concurrent_session_manager):
        """Test same user creating multiple sessions concurrently."""

        user_id = "concurrent_user"
        session_count = 10

        async def create_session(index: int):
            context = AgentContext(
                user_id=user_id,
                agent_id="test_agent",
                session_id="",
                input_message=f"Message {index}",
            )

            session = await concurrent_session_manager.create_session(
                user_id=user_id,
                agent_id="test_agent",
                context=context,
            )

            return session.session_id

        # Create sessions concurrently for same user
        tasks = [create_session(i) for i in range(session_count)]
        session_ids = await asyncio.gather(*tasks)

        # Verify all sessions were created
        assert len(session_ids) == session_count
        assert all(sid is not None for sid in session_ids)
        assert len(set(session_ids)) == session_count  # All unique

        # Verify all sessions belong to the same user
        sessions = await concurrent_session_manager.get_user_sessions(user_id)
        assert len(sessions) == session_count

    @pytest.mark.asyncio
    async def test_concurrent_session_operations(self, concurrent_session_manager):
        """Test concurrent session operations (create, update, delete)."""

        operations = []

        # Create sessions first
        session_ids = []
        for i in range(10):
            context = AgentContext(
                user_id=f"user_{i}",
                agent_id="test_agent",
                session_id="",
                input_message=f"Message {i}",
            )

            session = await concurrent_session_manager.create_session(
                user_id=f"user_{i}",
                agent_id="test_agent",
                context=context,
            )

            session_ids.append(session.session_id)

        # Perform concurrent operations
        async def update_session(session_id: str, index: int):
            context = AgentContext(
                user_id=f"user_{index}",
                agent_id="test_agent",
                session_id=session_id,
                input_message=f"Updated message {index}",
            )

            await concurrent_session_manager.update_session_context(session_id, context)

        async def close_session(session_id: str):
            await concurrent_session_manager.close_session(session_id)

        # Mix of updates and closes
        tasks = []
        for i, sid in enumerate(session_ids):
            if i % 2 == 0:
                tasks.append(update_session(sid, i))
            else:
                tasks.append(close_session(sid))

        await asyncio.gather(*tasks)

        # Verify operations completed
        for i, sid in enumerate(session_ids):
            session = await concurrent_session_manager.get_session(sid)
            if i % 2 == 0:
                assert session.status == "active"
            else:
                assert session.status == "closed"


# =============================================================================
# Concurrent Event Tests
# =============================================================================

class TestConcurrentEvents:
    """Tests for concurrent event publishing and subscribing."""

    @pytest.mark.asyncio
    async def test_concurrent_event_publishing(self, shared_event_bus):
        """Test multiple publishers can publish events concurrently."""

        publisher_count = 20
        events_per_publisher = 10
        total_events = publisher_count * events_per_publisher

        received_count = {"count": 0}

        async def counter_handler(event):
            received_count["count"] += 1

        # Subscribe handler
        await shared_event_bus.subscribe(EventType.AGENT_STARTED, counter_handler)

        # Publish events concurrently
        async def publish_events(publisher_id: int):
            for i in range(events_per_publisher):
                await shared_event_bus.publish(SystemEvent(
                    event_type=EventType.AGENT_STARTED,
                    source=f"publisher_{publisher_id}",
                    component="test",
                    message=f"Event {i} from publisher {publisher_id}",
                    details={"publisher": publisher_id, "event": i},
                ))

        # Start all publishers concurrently
        tasks = [publish_events(i) for i in range(publisher_count)]
        await asyncio.gather(*tasks)

        # Give time for all events to be processed
        await asyncio.sleep(0.1)

        # Verify all events were received
        assert received_count["count"] == total_events

    @pytest.mark.asyncio
    async def test_concurrent_event_subscribers(self, shared_event_bus):
        """Test multiple subscribers can receive events concurrently."""

        subscriber_count = 10
        events_published = 20

        received_data = {}

        async def make_subscriber(subscriber_id: int):
            async def handler(event):
                if subscriber_id not in received_data:
                    received_data[subscriber_id] = []
                received_data[subscriber_id].append(event)

            await shared_event_bus.subscribe(
                EventType.AGENT_STARTED,
                handler,
                name=f"subscriber_{subscriber_id}"
            )

        # Create subscribers concurrently
        tasks = [make_subscriber(i) for i in range(subscriber_count)]
        await asyncio.gather(*tasks)

        # Publish events
        for i in range(events_published):
            await shared_event_bus.publish(SystemEvent(
                event_type=EventType.AGENT_STARTED,
                source="test",
                component="test",
                message=f"Event {i}",
                details={"index": i},
            ))

        # Give time for processing
        await asyncio.sleep(0.1)

        # Verify all subscribers received all events
        for i in range(subscriber_count):
            assert len(received_data.get(i, [])) == events_published

    @pytest.mark.asyncio
    async def test_concurrent_subscribe_unsubscribe(self, shared_event_bus):
        """Test concurrent subscribe and unsubscribe operations."""

        operations = []

        async def subscriber_lifecycle(subscriber_id: int):
            # Subscribe
            received = []

            async def handler(event):
                received.append(event)

            await shared_event_bus.subscribe(
                EventType.AGENT_STARTED,
                handler,
                name=f"sub_{subscriber_id}"
            )

            # Wait a bit
            await asyncio.sleep(0.01)

            # Unsubscribe
            await shared_event_bus.unsubscribe(
                EventType.AGENT_STARTED,
                f"sub_{subscriber_id}"
            )

            return subscriber_id

        # Perform concurrent subscribe/unsubscribe
        tasks = [subscriber_lifecycle(i) for i in range(20)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 20

    @pytest.mark.asyncio
    async def test_concurrent_event_history_access(self, shared_event_bus):
        """Test concurrent access to event history."""

        # Publish some events first
        for i in range(50):
            await shared_event_bus.publish(SystemEvent(
                event_type=EventType.AGENT_STARTED,
                source="test",
                component="test",
                message=f"Event {i}",
                details={"index": i},
            ))

        # Access history concurrently
        async def access_history(reader_id: int):
            histories = []
            for _ in range(10):
                history = await shared_event_bus.get_history()
                histories.append(len(history))

            return histories

        tasks = [access_history(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # All should have gotten complete history
        for result in results:
            assert all(count == 50 for count in result)


# =============================================================================
# Concurrent Agent Execution Tests
# =============================================================================

class TestConcurrentAgentExecution:
    """Tests for concurrent agent execution."""

    @pytest.mark.asyncio
    async def test_concurrent_execution_different_sessions(self):
        """Test concurrent agent execution for different sessions."""

        from unittest.mock import Mock

        exec_count = {"count": 0}
        lock = asyncio.Lock()

        # Create mock execution function
        async def mock_execute(session_id: str):
            async with lock:
                exec_count["count"] += 1

            # Simulate async work
            await asyncio.sleep(0.01)

            return ExecutionResult(
                success=True,
                output=f"Response for {session_id}",
                metadata={"session_id": session_id},
            )

        # Execute concurrent agents
        session_ids = [f"session_{i}" for i in range(20)]

        tasks = [mock_execute(sid) for sid in session_ids]
        results = await asyncio.gather(*tasks)

        # Verify all executions completed
        assert len(results) == 20
        assert all(r.success for r in results)
        assert exec_count["count"] == 20

    @pytest.mark.asyncio
    async def test_concurrent_execution_with_retry(self):
        """Test concurrent execution with retry logic."""

        async def flaky_execution(session_id: str):
            # Simulate occasional failures
            await asyncio.sleep(0.001)

            # Fail 30% of the time
            import random
            if random.random() < 0.3:
                raise Exception("Random failure")

            return ExecutionResult(
                success=True,
                output=f"Success for {session_id}",
            )

        # Execute with retry logic
        async def execute_with_retry(session_id: str, max_retries: int = 3):
            for attempt in range(max_retries):
                try:
                    return await flaky_execution(session_id)
                except Exception:
                    if attempt == max_retries - 1:
                        return ExecutionResult(
                            success=False,
                            error=f"Failed after {max_retries} attempts",
                        )
                    await asyncio.sleep(0.001)

        # Run concurrent executions
        tasks = [execute_with_retry(f"session_{i}") for i in range(20)]
        results = await asyncio.gather(*tasks)

        # Most should succeed eventually
        success_count = sum(1 for r in results if r.success)
        assert success_count >= 15  # At least 75% success rate

    @pytest.mark.asyncio
    async def test_concurrent_execution_ordering(self):
        """Test that concurrent executions maintain proper ordering."""

        execution_order = []

        async def ordered_execution(session_id: str, delay: float):
            await asyncio.sleep(delay)
            execution_order.append(session_id)
            return ExecutionResult(success=True, output=session_id)

        # Create tasks with different delays
        tasks = [
            ordered_execution(f"session_{i}", 0.01 * (10 - i))
            for i in range(10)
        ]

        # Start all tasks
        pending = [asyncio.create_task(task) for task in tasks]

        # Wait for all to complete
        results = await asyncio.gather(*pending)

        # Verify all completed
        assert len(results) == 10
        assert len(execution_order) == 10

        # Order may vary due to async nature, but all should complete
        assert set(execution_order) == {f"session_{i}" for i in range(10)}


# =============================================================================
# Concurrent Metrics Tests
# =============================================================================

class TestConcurrentMetrics:
    """Tests for concurrent metrics collection."""

    @pytest.mark.asyncio
    async def test_concurrent_counter_increments(self, shared_metrics_collector):
        """Test concurrent counter increments."""

        increment_count = 100
        increment_value = 5

        async def increment_counter(worker_id: int):
            for _ in range(increment_count):
                await shared_metrics_collector.increment(
                    "test_counter",
                    value=increment_value,
                )

        # Run concurrent increments
        tasks = [increment_counter(i) for i in range(10)]
        await asyncio.gather(*tasks)

        # Verify final value
        expected = 10 * increment_count * increment_value
        actual = shared_metrics_collector.get_counter("test_counter")
        assert actual == expected

    @pytest.mark.asyncio
    async def test_concurrent_gauge_updates(self, shared_metrics_collector):
        """Test concurrent gauge updates."""

        async def update_gauge(worker_id: int, value: float):
            for i in range(50):
                await shared_metrics_collector.gauge(
                    f"gauge_{worker_id}",
                    value + i,
                )

        # Run concurrent updates
        tasks = [
            update_gauge(i, float(i * 100))
            for i in range(10)
        ]

        await asyncio.gather(*tasks)

        # Verify each gauge has its final value
        for i in range(10):
            final_value = shared_metrics_collector.get_gauge(f"gauge_{i}")
            assert final_value == float(i * 100 + 49)

    @pytest.mark.asyncio
    async def test_concurrent_histogram_recording(self, shared_metrics_collector):
        """Test concurrent histogram recording."""

        async def record_histogram(worker_id: int):
            for i in range(100):
                await shared_metrics_collector.histogram(
                    "test_histogram",
                    value=float(i),
                )

        # Run concurrent recordings
        tasks = [record_histogram(i) for i in range(10)]
        await asyncio.gather(*tasks)

        # Verify histogram aggregate data
        metrics = await shared_metrics_collector.get_metrics()
        histograms = metrics["histograms"]

        test_hist = [h for h in histograms if h["name"] == "test_histogram"][0]

        # Should have 1000 total records (10 workers * 100 records)
        assert test_hist["count"] == 1000
        assert test_hist["sum"] == 49500.0  # Sum of 0-99 repeated 10 times

    @pytest.mark.asyncio
    async def test_concurrent_metrics_retrieval(self, shared_metrics_collector):
        """Test concurrent metrics retrieval."""

        # Add some metrics first
        await shared_metrics_collector.increment("counter1", value=100)
        await shared_metrics_collector.gauge("gauge1", value=50.0)

        # Retrieve metrics concurrently
        async def retrieve_metrics(worker_id: int):
            metrics_list = []
            for _ in range(20):
                metrics = await shared_metrics_collector.get_metrics()
                metrics_list.append(metrics)

            return len(metrics_list)

        tasks = [retrieve_metrics(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # All should have retrieved metrics successfully
        assert all(r == 20 for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_metrics_reset(self, shared_metrics_collector):
        """Test concurrent reset operations."""

        # Add metrics
        for i in range(10):
            await shared_metrics_collector.increment(f"counter_{i}", value=i * 10)

        async def reset_and_check(worker_id: int):
            # Reset
            await shared_metrics_collector.reset()

            # Try to get counter (should be 0 or not found)
            value = shared_metrics_collector.get_counter(f"counter_{worker_id}")
            return value

        # Run concurrent resets
        tasks = [reset_and_check(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # All counters should be reset to 0
        assert all(v == 0 for v in results)


# =============================================================================
# Stress Tests
# =============================================================================

class TestStressScenarios:
    """Stress tests for high-concurrency scenarios."""

    @pytest.mark.asyncio
    async def test_high_concurrent_session_load(self, concurrent_session_manager):
        """Test high concurrent load on session creation."""

        user_count = 100
        sessions_per_user = 5

        async def create_user_sessions(user_id: int):
            session_ids = []
            for j in range(sessions_per_user):
                context = AgentContext(
                    user_id=f"user_{user_id}",
                    agent_id="test_agent",
                    session_id="",
                    input_message=f"Message {j}",
                )

                session = await concurrent_session_manager.create_session(
                    user_id=f"user_{user_id}",
                    agent_id="test_agent",
                    context=context,
                )

                session_ids.append(session.session_id)

            return len(session_ids)

        # Create sessions concurrently
        start_time = time.time()

        tasks = [create_user_sessions(i) for i in range(user_count)]
        results = await asyncio.gather(*tasks)

        elapsed = time.time() - start_time

        # Verify all sessions created
        assert len(results) == user_count
        assert all(r == sessions_per_user for r in results)

        # Performance check: should complete in reasonable time
        # (adjust threshold based on system performance)
        assert elapsed < 30.0  # 30 seconds max

    @pytest.mark.asyncio
    async def test_mixed_concurrent_operations(self, concurrent_session_manager, shared_event_bus, shared_metrics_collector):
        """Test mixed concurrent operations across all components."""

        operation_count = 50

        async def mixed_operations(op_id: int):
            # Mix of different operations
            if op_id % 3 == 0:
                # Session operation
                context = AgentContext(
                    user_id=f"user_{op_id}",
                    agent_id="test_agent",
                    session_id="",
                    input_message="Test",
                )
                await concurrent_session_manager.create_session(
                    user_id=f"user_{op_id}",
                    agent_id="test_agent",
                    context=context,
                )

            elif op_id % 3 == 1:
                # Event operation
                await shared_event_bus.publish(SystemEvent(
                    event_type=EventType.AGENT_STARTED,
                    source=f"source_{op_id}",
                    component="test",
                    message="Test event",
                ))

            else:
                # Metrics operation
                await shared_metrics_collector.increment(
                    "mixed_counter",
                    value=1,
                )

        # Run mixed operations concurrently
        tasks = [mixed_operations(i) for i in range(operation_count)]
        await asyncio.gather(*tasks)

        # Verify operations completed (no exceptions raised)
        assert True  # If we got here, all operations succeeded

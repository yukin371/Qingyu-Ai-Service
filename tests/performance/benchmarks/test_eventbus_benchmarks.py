"""
EventBus Performance Benchmarks

Performance targets (from Phase 6 plan):
- subscribe: < 0.5ms
- publish: < 0.1ms (without handlers)
- publish with handlers: < 1ms
- get_history: < 0.5ms
"""

import asyncio
import pytest

from src.agent_runtime.event_bus import EventBus
from src.common.types.event_types import EventType, SystemEvent


class TestEventBusBenchmarks:
    """EventBus 性能基准测试"""

    @pytest.fixture
    def event_bus(self):
        """创建 EventBus 实例"""
        return EventBus(enable_kafka=False, max_history=1000)

    # -------------------------------------------------------------------------
    # Subscribe Benchmarks
    # -------------------------------------------------------------------------

    def test_bench_subscribe(self, benchmark, event_bus):
        """基准测试: 订阅事件 - 目标 < 0.5ms"""

        async def subscribe():
            handler = lambda e: None
            await event_bus.subscribe(EventType.AGENT_STARTED, handler)

        benchmark(lambda: asyncio.run(subscribe()))

    def test_bench_subscribe_batch_10(self, benchmark, event_bus):
        """基准测试: 批量订阅 10 个处理器"""

        async def subscribe_batch():
            for i in range(10):
                handler = lambda e, idx=i: None
                await event_bus.subscribe(EventType.AGENT_STARTED, handler, name=f"handler_{i}")

        benchmark(lambda: asyncio.run(subscribe_batch()))

    def test_bench_subscribe_multiple_types(self, benchmark, event_bus):
        """基准测试: 订阅多种事件类型"""

        async def subscribe_types():
            event_types = [
                EventType.AGENT_STARTED,
                EventType.AGENT_COMPLETED,
                EventType.TOOL_CALLED,
                EventType.SYSTEM_ERROR,
            ]
            for et in event_types:
                handler = lambda e: None
                await event_bus.subscribe(et, handler)

        benchmark(lambda: asyncio.run(subscribe_types()))

    # -------------------------------------------------------------------------
    # Publish Benchmarks
    # -------------------------------------------------------------------------

    def test_bench_publish_no_handler(self, benchmark, event_bus):
        """基准测试: 发布事件（无处理器）- 目标 < 0.1ms"""

        event = SystemEvent(
            event_type=EventType.AGENT_STARTED,
            source="test",
            component="benchmark",
            message="Test event",
        )

        async def publish():
            await event_bus.publish(event)

        benchmark(lambda: asyncio.run(publish()))

    def test_bench_publish_single_handler(self, benchmark, event_bus):
        """基准测试: 发布事件（单个处理器）- 目标 < 1ms"""

        received = []

        async def handler(event):
            received.append(event)

        async def setup_and_publish():
            # Setup
            await event_bus.subscribe(EventType.AGENT_STARTED, handler)

            # Publish
            event = SystemEvent(
                event_type=EventType.AGENT_STARTED,
                source="test",
                component="benchmark",
                message="Test event",
            )
            await event_bus.publish(event)

        benchmark(lambda: asyncio.run(setup_and_publish()))
        assert len(received) >= 1

    def test_bench_publish_multiple_handlers(self, benchmark, event_bus):
        """基准测试: 发布事件（多个处理器）"""

        async def setup_and_publish():
            # Setup 5 handlers
            for i in range(5):
                async def handler(event, idx=i):
                    pass
                await event_bus.subscribe(EventType.AGENT_STARTED, handler, name=f"h_{i}")

            # Publish
            event = SystemEvent(
                event_type=EventType.AGENT_STARTED,
                source="test",
                component="benchmark",
                message="Test event",
            )
            await event_bus.publish(event)

        benchmark(lambda: asyncio.run(setup_and_publish()))

    def test_bench_publish_batch_10(self, benchmark, event_bus):
        """基准测试: 批量发布 10 个事件"""

        async def publish_batch():
            for i in range(10):
                event = SystemEvent(
                    event_type=EventType.AGENT_STARTED,
                    source="test",
                    component="benchmark",
                    message=f"Test event {i}",
                    details={"index": i},
                )
                await event_bus.publish(event)

        benchmark(lambda: asyncio.run(publish_batch()))

    # -------------------------------------------------------------------------
    # Unsubscribe Benchmarks
    # -------------------------------------------------------------------------

    def test_bench_unsubscribe(self, benchmark, event_bus):
        """基准测试: 取消订阅"""

        async def setup_and_unsubscribe():
            # Setup
            handler = lambda e: None
            await event_bus.subscribe(EventType.AGENT_STARTED, handler, name="test_handler")

            # Unsubscribe
            return await event_bus.unsubscribe(EventType.AGENT_STARTED, "test_handler")

        result = benchmark(lambda: asyncio.run(setup_and_unsubscribe()))
        assert result is True

    # -------------------------------------------------------------------------
    # History Benchmarks
    # -------------------------------------------------------------------------

    @pytest.fixture
    def event_bus_with_history(self, event_bus):
        """创建包含历史事件的 EventBus"""
        for i in range(20):
            event = SystemEvent(
                event_type=EventType.AGENT_STARTED,
                source="test",
                component="benchmark",
                message=f"Event {i}",
                details={"index": i},
            )
            # Add to history directly (synchronously)
            event_bus._add_to_history(event)
        return event_bus

    def test_bench_get_history(self, benchmark, event_bus_with_history):
        """基准测试: 获取事件历史 - 目标 < 0.5ms"""

        async def get_history():
            return await event_bus_with_history.get_history(limit=10)

        events = benchmark(lambda: asyncio.run(get_history()))
        assert len(events) == 10

    def test_bench_get_history_filtered(self, benchmark, event_bus_with_history):
        """基准测试: 获取过滤后的事件历史"""

        async def get_history():
            return await event_bus_with_history.get_history(
                event_type=EventType.AGENT_STARTED,
                limit=5,
            )

        events = benchmark(lambda: asyncio.run(get_history()))
        assert len(events) == 5

    # -------------------------------------------------------------------------
    # Handler Management Benchmarks
    # -------------------------------------------------------------------------

    def test_bench_enable_handler(self, benchmark, event_bus):
        """基准测试: 启用处理器"""

        async def setup():
            handler = lambda e: None
            await event_bus.subscribe(EventType.AGENT_STARTED, handler, name="test_handler")
            event_bus.disable_handler(EventType.AGENT_STARTED, "test_handler")

        asyncio.run(setup())

        def enable_handler():
            return event_bus.enable_handler(EventType.AGENT_STARTED, "test_handler")

        result = benchmark(enable_handler)
        assert result is True

    def test_bench_disable_handler(self, benchmark, event_bus):
        """基准测试: 禁用处理器"""

        async def setup():
            handler = lambda e: None
            await event_bus.subscribe(EventType.AGENT_STARTED, handler, name="test_handler")

        asyncio.run(setup())

        def disable_handler():
            return event_bus.disable_handler(EventType.AGENT_STARTED, "test_handler")

        result = benchmark(disable_handler)
        assert result is True

    def test_bench_get_handler_count(self, benchmark, event_bus):
        """基准测试: 获取处理器数量"""

        async def setup():
            for i in range(5):
                handler = lambda e, idx=i: None
                await event_bus.subscribe(EventType.AGENT_STARTED, handler, name=f"h_{i}")

        asyncio.run(setup())

        def get_count():
            return event_bus.get_handler_count(EventType.AGENT_STARTED)

        count = benchmark(get_count)
        assert count == 5

    def test_bench_get_handler_count_all(self, benchmark, event_bus):
        """基准测试: 获取所有处理器数量"""

        async def setup():
            for i in range(3):
                handler = lambda e, idx=i: None
                await event_bus.subscribe(EventType.AGENT_STARTED, handler, name=f"h_start_{i}")

            for i in range(4):
                handler = lambda e, idx=i: None
                await event_bus.subscribe(EventType.TOOL_CALLED, handler, name=f"h_tool_{i}")

        asyncio.run(setup())

        def get_count():
            return event_bus.get_handler_count()

        count = benchmark(get_count)
        assert count == 7

    # -------------------------------------------------------------------------
    # Concurrency Benchmarks
    # -------------------------------------------------------------------------

    def test_bench_concurrent_publish(self, benchmark, event_bus):
        """基准测试: 并发发布事件"""

        async def handler(event):
            pass

        async def concurrent_publish():
            # Setup handler
            await event_bus.subscribe(EventType.AGENT_STARTED, handler)

            # Publish concurrently
            tasks = []
            for i in range(10):
                event = SystemEvent(
                    event_type=EventType.AGENT_STARTED,
                    source="test",
                    component="benchmark",
                    message=f"Event {i}",
                )
                tasks.append(event_bus.publish(event))
            await asyncio.gather(*tasks)

        benchmark(lambda: asyncio.run(concurrent_publish()))

    def test_bench_high_throughput(self, benchmark, event_bus):
        """基准测试: 高吞吐量发布"""

        async def high_throughput():
            for i in range(100):
                event = SystemEvent(
                    event_type=EventType.AGENT_STARTED,
                    source="test",
                    component="benchmark",
                    message=f"Event {i}",
                )
                await event_bus.publish(event)

        benchmark(lambda: asyncio.run(high_throughput()))

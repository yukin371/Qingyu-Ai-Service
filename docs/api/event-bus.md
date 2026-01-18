# EventBus API 参考

EventBus 实现了发布-订阅模式的事件系统，支持组件之间的松耦合通信。

## 类定义

```python
from src.agent_runtime.event_bus import EventBus

class EventBus:
    def __init__(
        self,
        max_queue_size: int = 1000,
        enable_metrics: bool = False,
    ):
        """
        初始化 EventBus

        Args:
            max_queue_size: 最大队列大小，默认 1000
            enable_metrics: 是否启用指标收集，默认 False
        """
```

## 方法

### subscribe()

订阅事件。

```python
async def subscribe(
    self,
    event_type: EventType,
    handler: Callable[[SystemEvent], Awaitable[None]],
) -> str:
    """
    订阅事件

    Args:
        event_type: 事件类型，EventType.ANY 表示订阅所有事件
        handler: 事件处理器（异步函数）

    Returns:
        str: 订阅 ID

    Raises:
        ValueError: 如果参数无效

    Example:
        >>> async def my_handler(event: SystemEvent):
        ...     print(f"Event: {event.event_type}")

        >>> subscription_id = await event_bus.subscribe(
        ...     EventType.AGENT_STARTED,
        ...     my_handler,
        ... )
        >>> print(subscription_id)
        'sub_abc123'
    """
```

### unsubscribe()

取消订阅。

```python
async def unsubscribe(
    self,
    subscription_id: str,
) -> bool:
    """
    取消订阅

    Args:
        subscription_id: 订阅 ID

    Returns:
        bool: 是否取消成功

    Example:
        >>> success = await event_bus.unsubscribe("sub_abc123")
    """
```

### unsubscribe_handler()

取消处理器的所有订阅。

```python
async def unsubscribe_handler(
    self,
    handler: Callable,
) -> int:
    """
    取消处理器的所有订阅

    Args:
        handler: 事件处理器

    Returns:
        int: 取消的订阅数量

    Example:
        >>> count = await event_bus.unsubscribe_handler(my_handler)
        >>> print(f"Unsubscribed {count} handlers")
    """
```

### publish()

发布事件（异步）。

```python
async def publish(
    self,
    event: SystemEvent,
) -> int:
    """
    发布事件

    Args:
        event: 事件对象

    Returns:
        int: 接收到事件的订阅者数量

    Example:
        >>> event = SystemEvent(
        ...     event_type=EventType.AGENT_STARTED,
        ...     agent_id="chatbot",
        ...     timestamp=datetime.now(),
        ... )
        >>> count = await event_bus.publish(event)
        >>> print(f"Delivered to {count} subscribers")
    """
```

### publish_sync()

发布事件（同步）。

```python
def publish_sync(
    self,
    event: SystemEvent,
) -> int:
    """
    同步发布事件

    Args:
        event: 事件对象

    Returns:
        int: 接收到事件的订阅者数量

    Example:
        >>> event = SystemEvent(...)
        >>> count = event_bus.publish_sync(event)
    """
```

### clear()

清空所有订阅。

```python
def clear(
    self,
) -> None:
    """
    清空所有订阅

    Example:
        >>> event_bus.clear()
    """
```

### get_subscriber_count()

获取订阅者数量。

```python
def get_subscriber_count(
    self,
    event_type: EventType = None,
) -> int:
    """
    获取订阅者数量

    Args:
        event_type: 可选的事件类型，如果提供则返回该类型的订阅者数量

    Returns:
        int: 订阅者数量

    Example:
        >>> count = event_bus.get_subscriber_count(EventType.AGENT_STARTED)
        >>> print(count)
        3
    """
```

## 数据类型

### EventType

```python
class EventType(Enum):
    # Agent 生命周期事件
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    ERROR_OCCURRED = "error_occurred"

    # 会话事件
    SESSION_CREATED = "session_created"
    SESSION_EXPIRED = "session_expired"
    CHECKPOINT_SAVED = "checkpoint_saved"
    CHECKPOINT_RESTORED = "checkpoint_restored"

    # 中间件事件
    MIDDLEWARE_EXECUTED = "middleware_executed"
    MIDDLEWARE_FAILED = "middleware_failed"

    # 自定义事件
    CUSTOM = "custom"

    # 通配符
    ANY = "any"
```

### SystemEvent

```python
class SystemEvent(BaseModel):
    event_type: EventType              # 事件类型
    agent_id: str                      # Agent ID
    user_id: str = None                # 用户 ID（可选）
    session_id: str = None             # 会话 ID（可选）
    timestamp: datetime                # 时间戳
    metadata: Dict[str, Any] = {}      # 元数据

    # 可选字段
    execution_time_ms: int = None      # 执行时间（毫秒）
    error_message: str = None          # 错误消息
    error_type: str = None             # 错误类型
    trace_id: str = None               # 追踪 ID
```

## 使用示例

### 基本订阅

```python
import asyncio
from src.agent_runtime.event_bus import EventBus, EventType

async def main():
    # 创建事件总线
    event_bus = EventBus()

    # 定义事件处理器
    async def on_agent_started(event: SystemEvent):
        print(f"Agent {event.agent_id} started at {event.timestamp}")

    async def on_agent_completed(event: SystemEvent):
        if event.execution_time_ms:
            print(f"Agent completed in {event.execution_time_ms}ms")

    # 订阅事件
    await event_bus.subscribe(EventType.AGENT_STARTED, on_agent_started)
    await event_bus.subscribe(EventType.AGENT_COMPLETED, on_agent_completed)

    # 发布事件
    from datetime import datetime

    event = SystemEvent(
        event_type=EventType.AGENT_STARTED,
        agent_id="chatbot",
        timestamp=datetime.now(),
    )

    await event_bus.publish(event)
    # 输出: Agent chatbot started at 2025-01-17 10:00:00

asyncio.run(main())
```

### 订阅所有事件

```python
async def log_all_events(event: SystemEvent):
    """记录所有事件"""
    print(f"Event: {event.event_type.value}, Agent: {event.agent_id}")

await event_bus.subscribe(EventType.ANY, log_all_events)
```

### 取消订阅

```python
async def main():
    event_bus = EventBus()

    async def my_handler(event):
        print(f"Handling: {event.event_type}")

    # 订阅
    sub_id = await event_bus.subscribe(EventType.AGENT_STARTED, my_handler)

    # 发布事件 - 会被处理
    event = SystemEvent(...)
    await event_bus.publish(event)

    # 取消订阅
    await event_bus.unsubscribe(sub_id)

    # 再次发布 - 不会被处理
    await event_bus.publish(event)

asyncio.run(main())
```

### 事件处理错误

```python
async def safe_handler(event: SystemEvent):
    """安全的事件处理器"""
    try:
        # 处理事件
        print(f"Processing {event.event_type}")

    except Exception as e:
        # 记录错误但不影响其他处理器
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in event handler: {e}")

await event_bus.subscribe(EventType.ANY, safe_handler)
```

### 带优先级的处理

```python
from heapq import heappush, heappop

class PriorityEventBus(EventBus):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.priority_queues = {}

    async def publish(self, event: SystemEvent, priority: int = 0):
        """发布带优先级的事件"""
        event_type = event.event_type

        if event_type not in self.priority_queues:
            self.priority_queues[event_type] = []

        heappush(self.priority_queues[event_type], (priority, event))

        # 按优先级处理
        while self.priority_queues[event_type]:
            _, next_event = heappop(self.priority_queues[event_type])
            await super().publish(next_event)

# 使用
priority_bus = PriorityEventBus()

await priority_bus.publish(
    SystemEvent(...),
    priority=1,  # 数字越小优先级越高
)
```

### 事件过滤

```python
class FilteredEventHandler:
    def __init__(self, condition, handler):
        self.condition = condition
        self.handler = handler

    async def __call__(self, event: SystemEvent):
        """只在满足条件时处理"""
        if self.condition(event):
            await self.handler(event)

# 使用：只处理特定 Agent 的事件
async def handle_chatbot_events(event: SystemEvent):
    print(f"Chatbot event: {event.event_type}")

filtered_handler = FilteredEventHandler(
    condition=lambda e: e.agent_id == "chatbot",
    handler=handle_chatbot_events,
)

await event_bus.subscribe(EventType.ANY, filtered_handler)
```

### 事件聚合

```python
from collections import defaultdict

class EventAggregator:
    def __init__(self, event_bus: EventBus, window_seconds=60):
        self.event_bus = event_bus
        self.window = timedelta(seconds=window_seconds)
        self.events = defaultdict(list)

    async def aggregate(self, event: SystemEvent):
        """聚合事件"""
        key = f"{event.event_type.value}_{event.agent_id}"
        now = datetime.now()

        # 清理旧事件
        self.events[key] = [
            e for e in self.events[key]
            if now - e.timestamp < self.window
        ]

        # 添加新事件
        self.events[key].append(event)

        # 检查阈值
        if len(self.events[key]) >= 10:
            await self._handle_aggregation(key, self.events[key])

    async def _handle_aggregation(self, key, events):
        """处理聚合的事件"""
        print(f"Aggregated {len(events)} events for {key}")

# 使用
aggregator = EventAggregator(event_bus)
await event_bus.subscribe(EventType.ANY, aggregator.aggregate)
```

## 高级模式

### 事件链

```python
class EventChain:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.chains = {}

    def define_chain(self, chain_id: str, event_sequence: List[EventType]):
        """定义事件链"""
        self.chains[chain_id] = {
            "sequence": event_sequence,
            "current_index": 0,
            "context": {},
        }

    async def process_event(self, event: SystemEvent):
        """处理事件链"""
        for chain_id, chain in self.chains.items():
            sequence = chain["sequence"]
            current = chain["current_index"]

            if event.event_type == sequence[current]:
                chain["current_index"] += 1

                # 链完成
                if chain["current_index"] >= len(sequence):
                    await self._on_chain_complete(chain_id, chain)

    async def _on_chain_complete(self, chain_id: str, chain: dict):
        """事件链完成"""
        print(f"Chain {chain_id} completed")
```

### 事件重试

```python
class EventRetryHandler:
    def __init__(self, handler, max_attempts=3, delay=1.0):
        self.handler = handler
        self.max_attempts = max_attempts
        self.delay = delay

    async def __call__(self, event: SystemEvent):
        """带重试的事件处理"""
        for attempt in range(self.max_attempts):
            try:
                await self.handler(event)
                return  # 成功，退出
            except Exception as e:
                if attempt < self.max_attempts - 1:
                    await asyncio.sleep(self.delay * (attempt + 1))
                else:
                    raise  # 最后一次也失败了

# 使用
retry_handler = EventRetryHandler(my_handler, max_attempts=3)
await event_bus.subscribe(EventType.ANY, retry_handler)
```

### 事件缓存

```python
from functools import lru_cache

class CachedEventBus(EventBus):
    def __init__(self, cache_size=1000, **kwargs):
        super().__init__(**kwargs)
        self._cache = lru_cache(maxsize=cache_size)(self._get_cached_event)

    def _get_cached_event(self, event_id: str):
        """获取缓存的事件"""
        return None

    async def publish(self, event: SystemEvent):
        """发布事件到缓存"""
        event_id = f"{event.event_type.value}_{event.agent_id}_{int(event.timestamp.timestamp())}"
        self._cache(event_id)

        await super().publish(event)
```

## 性能考虑

### 并发处理

```python
import asyncio

class ConcurrentEventBus(EventBus):
    def __init__(self, max_concurrent=10, **kwargs):
        super().__init__(**kwargs)
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def publish(self, event: SystemEvent):
        """并发处理事件"""
        handlers = self._get_handlers(event.event_type)

        tasks = []
        for handler in handlers:
            async def wrapped_handler():
                async with self.semaphore:
                    await handler(event)

            tasks.append(wrapped_handler())

        await asyncio.gather(*tasks, return_exceptions=True)
```

### 批量发布

```python
async def publish_batch(
    event_bus: EventBus,
    events: List[SystemEvent],
) -> int:
    """批量发布事件"""
    tasks = [event_bus.publish(event) for event in events]
    results = await asyncio.gather(*tasks)

    return sum(results)
```

## 相关文档

- [AgentExecutor API](executor.md) - 执行器 API
- [SessionManager API](session-manager.md) - 会话管理 API
- [事件系统概念](../concepts/event-system.md) - 事件系统概念

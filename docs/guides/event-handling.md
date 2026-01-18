# 事件处理指南

本指南介绍如何使用和处理 Qingyu Backend AI 的事件系统。

## 事件系统基础

### 事件类型

```python
from src.agent_runtime.event_bus import EventType

# Agent 生命周期事件
EventType.AGENT_STARTED      # Agent 开始执行
EventType.AGENT_COMPLETED    # Agent 执行完成
EventType.ERROR_OCCURRED      # 发生错误

# 会话事件
EventType.SESSION_CREATED     # 会话创建
EventType.SESSION_EXPIRED     # 会话过期
EventType.CHECKPOINT_SAVED    # 检查点保存
EventType.CHECKPOINT_RESTORED # 检查点恢复

# 中间件事件
EventType.MIDDLEWARE_EXECUTED # 中间件执行
EventType.MIDDLEWARE_FAILED   # 中间件失败

# 通配符
EventType.ANY                 # 所有事件
```

### SystemEvent 结构

```python
from src.agent_runtime.event_bus import SystemEvent
from datetime import datetime

event = SystemEvent(
    event_type=EventType.AGENT_STARTED,
    agent_id="chatbot",
    user_id="user_123",
    session_id="sess_abc",
    timestamp=datetime.now(),
    metadata={
        "model": "gpt-3.5-turbo",
        "task": "Hello",
    },
    # 可选字段
    execution_time_ms=1234,
    error_message="Error details",
    error_type="ValidationError",
    trace_id="trace_123",
)
```

## 订阅事件

### 基本订阅

```python
from src.agent_runtime.event_bus import EventBus

# 创建事件总线
event_bus = EventBus()

# 定义处理器
async def on_agent_started(event: SystemEvent):
    print(f"Agent {event.agent_id} started")

# 订阅
await event_bus.subscribe(
    EventType.AGENT_STARTED,
    on_agent_started,
)
```

### 订阅所有事件

```python
async def log_all_events(event: SystemEvent):
    """记录所有事件"""
    print(f"Event: {event.event_type.value}")
    print(f"Agent: {event.agent_id}")
    print(f"Time: {event.timestamp}")

await event_bus.subscribe(
    EventType.ANY,
    log_all_events,
)
```

### 取消订阅

```python
# 订阅时获取 ID
subscription_id = await event_bus.subscribe(
    EventType.AGENT_STARTED,
    handler,
)

# 取消订阅
await event_bus.unsubscribe(subscription_id)

# 或取消处理器的所有订阅
await event_bus.unsubscribe_handler(handler)
```

## 事件处理模式

### 1. 日志记录

```python
import logging

logger = logging.getLogger(__name__)

class EventLogger:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    async def log_agent_lifecycle(self, event: SystemEvent):
        """记录 Agent 生命周期"""
        if event.event_type == EventType.AGENT_STARTED:
            logger.info(f"Agent started: {event.agent_id}")
        elif event.event_type == EventType.AGENT_COMPLETED:
            duration = event.execution_time_ms or 0
            logger.info(
                f"Agent completed: {event.agent_id} "
                f"({duration}ms)"
            )

    async def log_errors(self, event: SystemEvent):
        """记录错误"""
        if event.event_type == EventType.ERROR_OCCURRED:
            logger.error(
                f"Error in {event.agent_id}: {event.error_message}",
                extra={
                    "error_type": event.error_type,
                    "user_id": event.user_id,
                },
            )

    # 注册处理器
    async def setup(self):
        await self.event_bus.subscribe(
            EventType.ANY,
            self.log_agent_lifecycle,
        )
        await self.event_bus.subscribe(
            EventType.ERROR_OCCURRED,
            self.log_errors,
        )
```

### 2. 指标收集

```python
from collections import defaultdict
import time

class MetricsCollector:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.metrics = defaultdict(list)

    async def collect_metrics(self, event: SystemEvent):
        """收集指标"""
        if event.event_type == EventType.AGENT_COMPLETED:
            agent_id = event.agent_id

            # 记录执行时间
            if event.execution_time_ms:
                self.metrics[f"{agent_id}_duration"].append(
                    event.execution_time_ms
                )

            # 记录成功/失败
            self.metrics[f"{agent_id}_total"] += 1

    def get_stats(self, agent_id: str) -> dict:
        """获取统计信息"""
        durations = self.metrics.get(f"{agent_id}_duration", [])
        total = self.metrics.get(f"{agent_id}_total", 0)

        return {
            "total_executions": total,
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
            "min_duration_ms": min(durations) if durations else 0,
            "max_duration_ms": max(durations) if durations else 0,
        }
```

### 3. 告警通知

```python
class AlertingHandler:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    async def on_error(self, event: SystemEvent):
        """错误时发送告警"""
        if event.event_type == EventType.ERROR_OCCURRED:
            await self.send_alert(
                severity="high",
                title=f"Agent Error: {event.agent_id}",
                message=event.error_message,
            )

    async def on_slow_execution(self, event: SystemEvent):
        """执行缓慢时告警"""
        if (event.event_type == EventType.AGENT_COMPLETED and
            event.execution_time_ms and
            event.execution_time_ms > 5000):  # 5秒
            await self.send_alert(
                severity="warning",
                title=f"Slow Agent: {event.agent_id}",
                message=f"Execution took {event.execution_time_ms}ms",
            )

    async def send_alert(self, severity: str, title: str, message: str):
        """发送告警"""
        # 实现告警发送逻辑
        print(f"[{severity.upper()}] {title}: {message}")
```

### 4. 事件聚合

```python
from datetime import datetime, timedelta

class EventAggregator:
    def __init__(self, window_seconds: int = 60):
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

    async def _handle_aggregation(self, key: str, events: list):
        """处理聚合事件"""
        print(f"Aggregated {len(events)} events for {key}")
        # 发送汇总通知等
```

### 5. 事件过滤

```python
class FilteredEventHandler:
    def __init__(self, condition, handler):
        self.condition = condition
        self.handler = handler

    async def __call__(self, event: SystemEvent):
        """只在满足条件时处理"""
        if self.condition(event):
            await self.handler(event)

# 使用：只处理特定用户的事件
async def handle_premium_user_events(event: SystemEvent):
    print(f"Premium user event: {event.event_type}")

filtered_handler = FilteredEventHandler(
    condition=lambda e: e.metadata.get("tier") == "premium",
    handler=handle_premium_user_events,
)

await event_bus.subscribe(EventType.ANY, filtered_handler)
```

## 高级模式

### 事件链处理

```python
class EventChain:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.chains = {}
        self.current_position = {}

    def define_chain(
        self,
        chain_id: str,
        event_sequence: List[EventType],
        handler: Callable,
    ):
        """定义事件链"""
        self.chains[chain_id] = {
            "sequence": event_sequence,
            "handler": handler,
        }
        self.current_position[chain_id] = 0

    async def process_event(self, event: SystemEvent):
        """处理事件并检查链"""
        for chain_id, chain in self.chains.items():
            sequence = chain["sequence"]
            current = self.current_position[chain_id]

            if event.event_type == sequence[current]:
                self.current_position[chain_id] += 1

                # 链完成
                if self.current_position[chain_id] >= len(sequence):
                    await chain["handler"](event)
                    self.current_position[chain_id] = 0
```

### 事件转换

```python
class EventTransformer:
    def __init__(self, transform_func, actual_handler):
        self.transform = transform_func
        self.handler = actual_handler

    async def __call__(self, event: SystemEvent):
        """转换事件后处理"""
        transformed_event = self.transform(event)
        await self.handler(transformed_event)

# 使用：添加额外元数据
def add_metadata(event):
    event.metadata["processed_at"] = datetime.now().isoformat()
    event.metadata["hostname"] = os.hostname()
    return event

transformer = EventTransformer(
    transform_func=add_metadata,
    actual_handler=my_handler,
)
```

### 事件重试

```python
class RetryEventHandler:
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
                    # 最后一次也失败了
                    logger.error(f"Event handler failed after {self.max_attempts} attempts: {e}")
```

## 与 Executor 集成

### 设置事件总线

```python
from src.agent_runtime.orchestration.executor import AgentExecutor

executor = AgentExecutor(
    agent_id="chatbot",
    config=AgentConfig(
        name="chatbot",
        description="A helpful chatbot",
        model="gpt-3.5-turbo",
    ),
)

# 设置事件总线
executor.set_event_bus(event_bus)
```

### 自定义事件发布

```python
class CustomEventExecutor(AgentExecutor):
    async def execute(self, context: AgentContext) -> AgentResult:
        """执行并发布自定义事件"""

        # 发布开始事件
        await self.event_bus.publish(SystemEvent(
            event_type=EventType.AGENT_STARTED,
            agent_id=self.agent_id,
            user_id=context.user_id,
            session_id=context.session_id,
            timestamp=datetime.now(),
            metadata={
                "task": context.current_task,
            },
        ))

        start_time = time.time()

        try:
            # 执行 Agent
            result = await super().execute(context)

            # 发布完成事件
            await self.event_bus.publish(SystemEvent(
                event_type=EventType.AGENT_COMPLETED,
                agent_id=self.agent_id,
                user_id=context.user_id,
                session_id=context.session_id,
                timestamp=datetime.now(),
                execution_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "success": result.success,
                },
            ))

            return result

        except Exception as e:
            # 发布错误事件
            await self.event_bus.publish(SystemEvent(
                event_type=EventType.ERROR_OCCURRED,
                agent_id=self.agent_id,
                user_id=context.user_id,
                session_id=context.session_id,
                timestamp=datetime.now(),
                error_message=str(e),
                error_type=type(e).__name__,
            ))

            raise
```

## 自定义事件

### 定义自定义事件类型

```python
from enum import Enum

class CustomEventType(Enum):
    # 业务事件
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"

    # 工作流事件
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_STEP_COMPLETED = "workflow_step_completed"
    WORKFLOW_COMPLETED = "workflow_completed"
```

### 发布自定义事件

```python
async def publish_custom_event():
    event = SystemEvent(
        event_type=CustomEventType.USER_LOGIN,
        agent_id="auth_agent",
        user_id="user_123",
        timestamp=datetime.now(),
        metadata={
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0...",
        },
    )

    await event_bus.publish(event)
```

## 性能考虑

### 异步处理

```python
import asyncio

class AsyncEventHandler:
    """异步事件处理器，不阻塞主流程"""

    def __init__(self, max_concurrent=10):
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def __call__(self, event: SystemEvent):
        """在后台处理事件"""
        async with self.semaphore:
            await self._process_event(event)

    async def _process_event(self, event: SystemEvent):
        """实际处理逻辑"""
        # 可能很慢的操作
        await asyncio.sleep(1)
        print(f"Processed: {event.event_type}")
```

### 批量处理

```python
class BatchEventProcessor:
    def __init__(self, batch_size=100, flush_interval=5):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.buffer = []

    async def __call__(self, event: SystemEvent):
        """收集事件到缓冲区"""
        self.buffer.append(event)

        if len(self.buffer) >= self.batch_size:
            await self._flush()

    async def _flush(self):
        """批量处理事件"""
        if not self.buffer:
            return

        # 批量处理
        await self._process_batch(self.buffer)

        # 清空缓冲区
        self.buffer.clear()
```

## 最佳实践

### 1. 处理器应该是幂等的

```python
# ✅ 好：幂等处理器
async def increment_counter(event):
    """多次执行结果相同"""
    count = await db.get_counter(event.id)
    await db.set_counter(event.id, count + 1)

# ❌ 不好：非幂等处理器
async def append_log(event):
    """每次执行都会追加"""
    await db.log.append(event)  # 会重复
```

### 2. 处理器应该快速返回

```python
# ✅ 好：异步处理
async def handle_event(event):
    # 快速返回
    asyncio.create_task(long_running_task(event))

# ❌ 不好：阻塞等待
async def handle_event(event):
    # 阻塞事件总线
    await long_running_task(event)
```

### 3. 错误隔离

```python
async def safe_handler(handler):
    """错误隔离的包装器"""
    async def wrapper(event):
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Handler error: {e}")
            # 不影响其他处理器
    return wrapper
```

## 相关文档

- [EventBus API](../api/event-bus.md) - 事件总线 API
- [事件系统概念](../concepts/event-system.md) - 事件系统概念
- [错误处理指南](error-handling.md) - 错误处理模式

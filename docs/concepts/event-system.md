# 事件系统

本文档详细介绍 Qingyu Backend AI 的事件驱动架构系统。

## 概述

事件系统实现了发布-订阅模式，允许组件之间松耦合通信。Agent 执行过程中的关键事件都会被发布，订阅者可以监听并响应这些事件。

### 核心组件

```
┌─────────────┐         ┌─────────────┐
│   Source    │         │  Subscriber │
│  (Publisher)│         │  (Handler)  │
└──────┬──────┘         └──────┬──────┘
       │                       │
       │ publish               │ subscribe
       │                       │
       ▼                       ▼
┌─────────────────────────────────────┐
│           EventBus                  │
│  - Event Queue                      │
│  - Subscriber Registry              │
│  - Event Dispatcher                 │
└─────────────────────────────────────┘
```

## 事件类型

### EventType 枚举

```python
from src.agent_runtime.event_bus import EventType

class EventType(Enum):
    # Agent 生命周期事件
    AGENT_STARTED = "agent_started"           # Agent 开始执行
    AGENT_COMPLETED = "agent_completed"       # Agent 执行完成
    ERROR_OCCURRED = "error_occurred"         # 发生错误

    # 会话事件
    SESSION_CREATED = "session_created"       # 会话创建
    SESSION_EXPIRED = "session_expired"       # 会话过期
    CHECKPOINT_SAVED = "checkpoint_saved"     # 检查点保存
    CHECKPOINT_RESTORED = "checkpoint_restored"  # 检查点恢复

    # 中间件事件
    MIDDLEWARE_EXECUTED = "middleware_executed"  # 中间件执行
    MIDDLEWARE_FAILED = "middleware_failed"      # 中间件失败

    # 自定义事件
    CUSTOM = "custom"
```

### SystemEvent

事件对象结构：

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
)
```

## EventBus 基础

### 创建 EventBus

```python
from src.agent_runtime.event_bus import EventBus

# 创建基本的事件总线
event_bus = EventBus()

# 或者使用依赖注入
event_bus = EventBus(
    max_queue_size=1000,     # 最大队列大小
    enable_metrics=True,     # 启用指标收集
)
```

### 订阅事件

```python
# 定义事件处理器
async def on_agent_started(event: SystemEvent):
    print(f"Agent {event.agent_id} started at {event.timestamp}")

# 订阅单个事件类型
await event_bus.subscribe(
    EventType.AGENT_STARTED,
    on_agent_started,
)

# 订阅所有事件
await event_bus.subscribe(
    EventType.ANY,
    log_all_events,
)
```

### 发布事件

```python
# 创建事件
event = SystemEvent(
    event_type=EventType.AGENT_STARTED,
    agent_id="chatbot",
    timestamp=datetime.now(),
)

# 发布事件（异步）
await event_bus.publish(event)

# 发布事件（同步）
event_bus.publish_sync(event)
```

### 取消订阅

```python
# 保存订阅 ID
subscription_id = await event_bus.subscribe(
    EventType.AGENT_STARTED,
    handler,
)

# 取消订阅
await event_bus.unsubscribe(subscription_id)

# 取消特定处理器的所有订阅
await event_bus.unsubscribe_handler(handler)
```

## 事件处理器

### 基本处理器

```python
async def simple_handler(event: SystemEvent):
    """简单的事件处理器"""
    if event.event_type == EventType.AGENT_STARTED:
        print(f"Agent started: {event.agent_id}")
    elif event.event_type == EventType.AGENT_COMPLETED:
        print(f"Agent completed in {event.execution_time_ms}ms")
```

### 指标收集处理器

```python
from collections import defaultdict

class MetricsCollector:
    def __init__(self):
        self.metrics = defaultdict(list)

    async def collect_metrics(self, event: SystemEvent):
        if event.event_type == EventType.AGENT_COMPLETED:
            agent_id = event.agent_id
            duration = event.execution_time_ms

            self.metrics[f"{agent_id}_duration"].append(duration)
            self.metrics[f"{agent_id}_count"] += 1

    def get_stats(self):
        """获取统计信息"""
        stats = {}
        for key, values in self.metrics.items():
            if isinstance(values, list):
                stats[key] = {
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "count": len(values),
                }
        return stats

# 使用
collector = MetricsCollector()
await event_bus.subscribe(EventType.AGENT_COMPLETED, collector.collect_metrics)
```

### 告警处理器

```python
class AlertingHandler:
    def __init__(self, alert_service):
        self.alert_service = alert_service

    async def on_error(self, event: SystemEvent):
        """错误时发送告警"""
        if event.event_type == EventType.ERROR_OCCURRED:
            await self.alert_service.send_alert(
                severity="high",
                title=f"Agent Error: {event.agent_id}",
                message=event.error_message,
            )

    async def on_slow_execution(self, event: SystemEvent):
        """执行缓慢时告警"""
        if (event.event_type == EventType.AGENT_COMPLETED and
            event.execution_time_ms > 5000):
            await self.alert_service.send_alert(
                severity="warning",
                title=f"Slow Agent: {event.agent_id}",
                message=f"Execution took {event.execution_time_ms}ms",
            )
```

### 日志处理器

```python
import logging

logger = logging.getLogger(__name__)

class LoggingHandler:
    async def log_event(self, event: SystemEvent):
        """记录所有事件"""
        logger.info(
            f"Event: {event.event_type.value}, "
            f"Agent: {event.agent_id}, "
            f"User: {event.user_id}"
        )

    async def log_error(self, event: SystemEvent):
        """记录错误详情"""
        if event.event_type == EventType.ERROR_OCCURRED:
            logger.error(
                f"Error in {event.agent_id}: {event.error_message}",
                extra={
                    "error_type": event.error_type,
                    "user_id": event.user_id,
                    "session_id": event.session_id,
                },
            )
```

### 过滤处理器

```python
class FilteredHandler:
    def __init__(self, condition_func, actual_handler):
        self.condition = condition_func
        self.handler = actual_handler

    async def __call__(self, event: SystemEvent):
        """只处理满足条件的事件"""
        if self.condition(event):
            await self.handler(event)

# 使用示例
async def premium_user_handler(event: SystemEvent):
    print(f"Premium user event: {event.user_id}")

# 只处理 premium 用户的事件
filtered = FilteredHandler(
    condition_func=lambda e: e.metadata.get("tier") == "premium",
    actual_handler=premium_user_handler,
)

await event_bus.subscribe(EventType.ANY, filtered)
```

## 与 Executor 集成

### 设置 EventBus

```python
from src.agent_runtime.orchestration.executor import AgentExecutor

executor = AgentExecutor(
    agent_id="my_agent",
    config=AgentConfig(
        name="my_agent",
        description="My Agent",
        model="gpt-3.5-turbo",
    ),
)

# 设置事件总线
executor.set_event_bus(event_bus)

# 现在 executor 会自动发布事件
result = await executor.execute(context)
# 发布: AGENT_STARTED, AGENT_COMPLETED
```

### 事件流

```
Executor.execute(context)
    │
    ├─> EventBus.publish(AGENT_STARTED)
    │       └─> Handler1.on_agent_started()
    │       └─> Handler2.on_agent_started()
    │
    ├─> Middleware Pipeline
    │
    ├─> LLM Execution
    │
    ├─> EventBus.publish(AGENT_COMPLETED)
    │       └─> Handler1.on_agent_completed()
    │       └─> Handler2.collect_metrics()
    │
    └─> Return result
```

### 错误事件流

```
Executor.execute(context)
    │
    ├─> EventBus.publish(AGENT_STARTED)
    │
    ├─> Middleware Pipeline
    │       └─> Error!
    │
    ├─> EventBus.publish(ERROR_OCCURRED)
    │       └─> AlertingHandler.send_alert()
    │       └─> LoggingHandler.log_error()
    │
    └─> Return error result
```

## 高级模式

### 事件聚合

```python
from collections import defaultdict
from datetime import datetime, timedelta

class EventAggregator:
    def __init__(self, window_seconds=60):
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

        # 检查是否触发聚合条件
        if len(self.events[key]) >= 10:
            await self._handle_aggregation(key, self.events[key])

    async def _handle_aggregation(self, key, events):
        """处理聚合的事件"""
        print(f"Aggregated {len(events)} events for {key}")
        # 发送汇总通知等
```

### 事件重试

```python
class RetryHandler:
    def __init__(self, max_attempts=3, delay=1.0):
        self.max_attempts = max_attempts
        self.delay = delay
        self.failed_events = []

    async def handle_with_retry(self, handler, event: SystemEvent):
        """带重试的事件处理"""
        for attempt in range(self.max_attempts):
            try:
                await handler(event)
                return  # 成功，退出
            except Exception as e:
                if attempt < self.max_attempts - 1:
                    await asyncio.sleep(self.delay * (attempt + 1))
                else:
                    # 最后一次也失败了
                    self.failed_events.append(event)
                    raise
```

### 事件转换

```python
class EventTransformer:
    def __init__(self, transform_func, actual_handler):
        self.transform = transform_func
        self.handler = actual_handler

    async def __call__(self, event: SystemEvent):
        """转换事件后再处理"""
        transformed_event = self.transform(event)
        await self.handler(transformed_event)

# 使用示例
def add_metadata(event):
    """为事件添加元数据"""
    event.metadata["processed_at"] = datetime.now().isoformat()
    event.metadata["hostname"] = os.hostname()
    return event

transformer = EventTransformer(
    transform_func=add_metadata,
    actual_handler=my_handler,
)
```

### 事件路由

```python
class EventRouter:
    def __init__(self):
        self.routes = {}

    def route(self, event_type):
        """装饰器：注册路由"""
        def decorator(handler):
            if event_type not in self.routes:
                self.routes[event_type] = []
            self.routes[event_type].append(handler)
            return handler
        return decorator

    async def dispatch(self, event: SystemEvent):
        """分发事件到对应的处理器"""
        handlers = self.routes.get(event.event_type, [])
        for handler in handlers:
            await handler(event)

# 使用示例
router = EventRouter()

@router.route(EventType.AGENT_STARTED)
async def handle_started(event):
    print(f"Started: {event.agent_id}")

@router.route(EventType.AGENT_COMPLETED)
async def handle_completed(event):
    print(f"Completed: {event.agent_id}")

# 订阅路由器
await event_bus.subscribe(EventType.ANY, router.dispatch)
```

## 自定义事件

### 定义自定义事件类型

```python
from enum import Enum

class CustomEventType(Enum):
    # 业务特定事件
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

### 处理自定义事件

```python
class CustomEventHandler:
    async def on_user_login(self, event: SystemEvent):
        """用户登录处理"""
        # 记录登录日志
        await self.log_login(event)

        # 更新用户状态
        await self.update_user_status(event.user_id, "online")

        # 发送欢迎消息
        await self.send_welcome_message(event.user_id)

    async def on_payment_success(self, event: SystemEvent):
        """支付成功处理"""
        # 更新订单状态
        await self.update_order_status(event.metadata["order_id"], "paid")

        # 发送确认邮件
        await self.send_confirmation_email(event.user_id)
```

## 性能考虑

### 异步事件处理

```python
import asyncio

class AsyncEventHandler:
    def __init__(self, max_concurrent=10):
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def handle_event(self, event: SystemEvent):
        """限制并发的事件处理"""
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
class BatchEventHandler:
    def __init__(self, batch_size=100, flush_interval=5):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.buffer = []

    async def handle_event(self, event: SystemEvent):
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

    async def _process_batch(self, events):
        """批量处理逻辑"""
        # 例如：批量写入数据库
        await self.db.insert_many(events)
```

### 事件优先级

```python
from enum import Enum
import heapq

class Priority(Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3

class PriorityEventBus(EventBus):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.priority_queue = []

    async def publish(self, event: SystemEvent, priority: Priority = Priority.MEDIUM):
        """发布带优先级的事件"""
        heapq.heappush(
            self.priority_queue,
            (priority.value, event),
        )

    async def dispatch_events(self):
        """按优先级分发事件"""
        while self.priority_queue:
            priority, event = heapq.heappop(self.priority_queue)
            await super().publish(event)
```

## 监控和调试

### 事件追踪

```python
class EventTracer:
    def __init__(self):
        self.event_log = []

    async def trace(self, event: SystemEvent):
        """追踪所有事件"""
        trace = {
            "type": event.event_type.value,
            "agent": event.agent_id,
            "user": event.user_id,
            "timestamp": event.timestamp.isoformat(),
            "metadata": event.metadata,
        }

        self.event_log.append(trace)

        # 如果是错误，记录详细信息
        if event.event_type == EventType.ERROR_OCCURRED:
            trace["error"] = {
                "message": event.error_message,
                "type": event.error_type,
            }

    def get_trace_log(self):
        """获取追踪日志"""
        return self.event_log

    def get_events_for_session(self, session_id: str):
        """获取特定会话的事件"""
        return [
            e for e in self.event_log
            if e.get("session_id") == session_id
        ]
```

### 事件统计

```python
from collections import Counter

class EventStatistics:
    def __init__(self):
        self.counter = Counter()
        self.timing = {}

    async def record(self, event: SystemEvent):
        """记录事件统计"""
        self.counter[event.event_type.value] += 1

        if event.execution_time_ms:
            agent = event.agent_id
            if agent not in self.timing:
                self.timing[agent] = []

            self.timing[agent].append(event.execution_time_ms)

    def get_summary(self):
        """获取统计摘要"""
        summary = {
            "total_events": sum(self.counter.values()),
            "by_type": dict(self.counter),
        }

        # 计算平均执行时间
        timing_summary = {}
        for agent, times in self.timing.items():
            timing_summary[agent] = {
                "avg": sum(times) / len(times),
                "min": min(times),
                "max": max(times),
                "count": len(times),
            }

        summary["timing"] = timing_summary

        return summary
```

## 最佳实践

### 1. 事件处理器应该是幂等的

```python
# ✅ 幂等处理器
async def increment_counter(event):
    """多次执行结果相同"""
    count = await db.get_counter(event.id)
    await db.set_counter(event.id, count + 1)

# ❌ 非幂等处理器
async def append_log(event):
    """每次执行都会追加"""
    await db.log.append(event)  # 会重复
```

### 2. 处理器应该快速返回

```python
# ✅ 异步处理
async def handle_event(event):
    # 快速返回
    asyncio.create_task(long_running_task(event))

# ❌ 同步等待
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

### 4. 使用事件溯源

```python
class EventSourcingHandler:
    async def handle(self, event: SystemEvent):
        """将事件持久化用于溯源"""
        await self.event_store.append(event)

        # 根据事件更新状态
        await self.update_state(event)
```

## 相关文档

- [系统架构](architecture.md) - 事件系统在架构中的位置
- [Agent 生命周期](lifecycle.md) - Agent 执行过程中的事件
- [中间件系统](middleware.md) - 中间件事件处理

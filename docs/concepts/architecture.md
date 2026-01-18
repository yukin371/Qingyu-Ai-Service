# 系统架构

本文档介绍 Qingyu Backend AI 服务的整体架构设计。

## 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                         应用层 (Application)                      │
├─────────────────────────────────────────────────────────────────┤
│  API Gateway  │  WebSocket Handler  │  Cron Jobs  │  Webhooks   │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      服务层 (Service Layer)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │   Agent     │  │   Session    │  │      Event           │   │
│  │  Executor   │  │   Manager    │  │       Bus            │   │
│  └──────┬──────┘  └──────┬───────┘  └──────────┬───────────┘   │
│         │                │                     │                 │
│  ┌──────▼──────┐  ┌──────▼───────┐  ┌──────────▼───────────┐   │
│  │ Middleware  │  │   Checkpoint │  │   Event Handlers     │   │
│  │  Pipeline   │  │    Storage   │  │   (Subscribers)      │   │
│  └─────────────┘  └──────────────┘  └──────────────────────┘   │
│                                                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    集成层 (Integration Layer)                    │
├─────────────────────────────────────────────────────────────────┤
│  LLM Providers  │  Vector DB  │  Cache  │  Message Queue        │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    基础设施层 (Infrastructure)                   │
├─────────────────────────────────────────────────────────────────┤
│  Redis  │  MongoDB  │  PostgreSQL  │  S3  │  Monitoring         │
└─────────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. AgentExecutor (执行器)

**职责**: 协调 Agent 执行的核心引擎

```python
from src.agent_runtime.orchestration.executor import AgentExecutor

executor = AgentExecutor(
    agent_id="my_agent",
    config=AgentConfig(
        name="my_agent",
        description="A helpful assistant",
        model="gpt-3.5-turbo",
    ),
)

# 设置中间件管道
executor.set_middleware_pipeline(middleware_pipeline)

# 设置事件总线
executor.set_event_bus(event_bus)

# 执行任务
result = await executor.execute(context)
```

**关键特性**:
- 支持同步/异步执行
- 可插拔的中间件系统
- 事件驱动通知
- 自动错误处理和重试

### 2. SessionManager (会话管理器)

**职责**: 管理用户会话和状态持久化

```python
from src.agent_runtime.session_manager import SessionManager

session_manager = SessionManager(
    conn=redis_client,
    ttl=3600,  # 1小时过期
)

# 创建会话
session = await session_manager.create_session(
    user_id="user_123",
    agent_id="assistant",
)

# 保存检查点
checkpoint_id = await session_manager.save_checkpoint(
    session_id=session.session_id,
    data={"state": "conversation_active"},
)

# 检索会话
retrieved = await session_manager.get_session(session.session_id)
```

**关键特性**:
- 会话创建和检索
- 检查点保存和恢复
- 用户会话列表查询
- 自动过期清理
- 并发安全

### 3. EventBus (事件总线)

**职责**: 实现发布-订阅模式的事件系统

```python
from src.agent_runtime.event_bus import EventBus, EventType

event_bus = EventBus()

# 订阅事件
async def handler(event):
    print(f"Event: {event.event_type}")

await event_bus.subscribe(EventType.AGENT_STARTED, handler)

# 发布事件
event = SystemEvent(
    event_type=EventType.AGENT_STARTED,
    agent_id="my_agent",
    timestamp=datetime.now(),
)

await event_bus.publish(event)
```

**事件类型**:
- `AGENT_STARTED` - Agent 开始执行
- `AGENT_COMPLETED` - Agent 执行完成
- `ERROR_OCCURRED` - 发生错误
- `CHECKPOINT_SAVED` - 检查点已保存
- `MIDDLEWARE_EXECUTED` - 中间件执行

### 4. MiddlewarePipeline (中间件管道)

**职责**: 实现洋葱模型的中间件处理

```python
from src.middleware.pipeline import MiddlewarePipeline
from src.middleware.basic_middleware import (
    LoggingMiddleware,
    AuthMiddleware,
    RateLimitMiddleware,
)

pipeline = MiddlewarePipeline()

# 添加中间件（按执行顺序）
pipeline.add(LoggingMiddleware(name="logger"))
pipeline.add(AuthMiddleware(name="auth"))
pipeline.add(RateLimitMiddleware(name="rate_limit", max_requests=100))

# 应用到执行器
executor.set_middleware_pipeline(pipeline)
```

**执行顺序**（洋葱模型）:
```
Request → Logging → Auth → RateLimit → Agent → RateLimit → Auth → Logging → Response
           Pre                                    Post
```

## 数据流

### 请求执行流程

```
1. Client Request
   ↓
2. API Gateway / Handler
   ↓
3. Create AgentContext
   - user_id
   - agent_id
   - session_id
   - current_task
   ↓
4. AgentExecutor.execute(context)
   ↓
5. Middleware Pipeline (Pre-processing)
   - Logging
   - Authentication
   - Rate Limiting
   - Validation
   ↓
6. LLM Invocation
   - Build prompt
   - Call LLM API
   - Stream response
   ↓
7. Middleware Pipeline (Post-processing)
   - Response formatting
   - Error handling
   - Metrics collection
   ↓
8. Event Publishing
   - AGENT_COMPLETED
   - Metrics update
   ↓
9. Return AgentResult
   - success
   - output
   - metadata
   ↓
10. Client Response
```

### 事件流

```
┌─────────────┐
│   Source    │
│  (Executor) │
└──────┬──────┘
       │ publish(event)
       ▼
┌─────────────┐
│  EventBus   │
└──────┬──────┘
       │
       ├──────────────► ┌──────────────┐
       │                │ Handler 1    │
       │                │ (Logging)    │
       ├──────────────► └──────────────┘
       │
       │                ┌──────────────┐
       │                │ Handler 2    │
       │                │ (Metrics)    │
       └──────────────► └──────────────┘
       │                ┌──────────────┐
       │                │ Handler 3    │
       │                │ (Alerting)   │
       └──────────────► └──────────────┘
```

## 设计模式

### 1. 依赖注入

所有组件都支持依赖注入：

```python
# 注入依赖
executor = AgentExecutor(
    agent_id="my_agent",
    config=config,
    llm_client=custom_llm_client,  # 可选
    event_bus=custom_event_bus,    # 可选
)
```

### 2. 中间件模式

洋葱模型的中间件处理：

```python
class CustomMiddleware(BaseMiddleware):
    async def process(self, context: AgentContext) -> MiddlewareResult:
        # 前置处理
        print(f"Before: {context.current_task}")

        # 调用下一个中间件
        result = await self.call_next(context)

        # 后置处理
        print(f"After: {result.agent_result.output}")

        return result
```

### 3. 发布-订阅模式

事件驱动的松耦合架构：

```python
# 发布者不关心订阅者
await event_bus.publish(event)

# 订阅者互不影响
await event_bus.subscribe(EventType.ANY, handler1)
await event_bus.subscribe(EventType.ANY, handler2)
```

### 4. 策略模式

不同的执行策略：

```python
# 同步执行
result = await executor.execute(context)

# 流式执行
async for chunk in executor.execute_stream(context):
    print(chunk)

# 批量执行
results = await executor.execute_batch([context1, context2])
```

## 扩展点

### 1. 自定义中间件

```python
from src.middleware.base import BaseMiddleware

class CacheMiddleware(BaseMiddleware):
    def __init__(self, name: str, cache_client):
        super().__init__(name)
        self.cache = cache_client

    async def process(self, context: AgentContext) -> MiddlewareResult:
        # 检查缓存
        cached = await self.cache.get(context.current_task)
        if cached:
            return MiddlewareResult(
                success=True,
                agent_result=AgentResult(
                    success=True,
                    output=cached,
                ),
                skip_agent=True,  # 跳过 Agent 执行
            )

        # 执行
        result = await self.call_next(context)

        # 缓存结果
        await self.cache.set(context.current_task, result.agent_result.output)

        return result
```

### 2. 自定义事件处理器

```python
async def alerting_handler(event: SystemEvent):
    if event.event_type == EventType.ERROR_OCCURRED:
        # 发送告警
        await send_alert(
            subject=f"Agent Error: {event.agent_id}",
            message=event.error_message,
        )

await event_bus.subscribe(EventType.ERROR_OCCURRED, alerting_handler)
```

### 3. 自定义 LLM 客户端

```python
from src.llm.base import BaseLLMClient

class CustomLLMClient(BaseLLMClient):
    async def generate(self, prompt: str, **kwargs) -> str:
        # 自定义 LLM 调用逻辑
        response = await my_custom_llm_api.call(prompt)
        return response.text
```

## 性能考虑

### 并发处理

```python
# 并发执行多个 Agent
async def execute_concurrently():
    tasks = [
        executor.execute(context1),
        executor.execute(context2),
        executor.execute(context3),
    ]
    results = await asyncio.gather(*tasks)
    return results
```

### 连接池

```python
# Redis 连接池
redis_pool = redis.ConnectionPool(
    host='localhost',
    port=6379,
    max_connections=50,
)

session_manager = SessionManager(
    conn=redis.Redis(connection_pool=redis_pool),
)
```

### 缓存策略

```python
# 使用中间件实现缓存
class CacheMiddleware(BaseMiddleware):
    def __init__(self, name: str, ttl: int = 300):
        super().__init__(name)
        self.cache = {}
        self.ttl = ttl

    async def process(self, context: AgentContext) -> MiddlewareResult:
        cache_key = hashlib.md5(context.current_task.encode()).hexdigest()

        if cache_key in self.cache:
            return self.cache[cache_key]

        result = await self.call_next(context)
        self.cache[cache_key] = result

        return result
```

## 安全架构

### 安全层

```
┌────────────────────────────────────────┐
│         应用安全 (Application)          │
│  - 输入验证                            │
│  - 输出清洗                            │
│  - 速率限制                            │
└────────────────┬───────────────────────┘
                 │
┌────────────────▼───────────────────────┐
│       认证授权 (Auth & Authz)           │
│  - 会话验证                            │
│  - 权限检查                            │
│  - Token 管理                          │
└────────────────┬───────────────────────┘
                 │
┌────────────────▼───────────────────────┐
│       数据安全 (Data Security)          │
│  - 加密传输 (TLS)                      │
│  - 敏感数据加密                        │
│  - 审计日志                            │
└────────────────────────────────────────┘
```

### 安全中间件顺序

```python
pipeline = MiddlewarePipeline()

# 1. 首先验证输入
pipeline.add(ValidationMiddleware(name="validation"))

# 2. 然后认证
pipeline.add(AuthMiddleware(name="auth"))

# 3. 检查授权
pipeline.add(AuthorizationMiddleware(name="authorization"))

# 4. 速率限制
pipeline.add(RateLimitMiddleware(name="rate_limit"))

# 5. 审计日志
pipeline.add(AuditMiddleware(name="audit"))
```

## 监控和可观测性

### 指标收集

```python
from src.middleware.metrics_middleware import MetricsCollector

metrics = MetricsCollector()

# 在事件处理器中收集指标
async def metrics_handler(event: SystemEvent):
    if event.execution_time_ms:
        await metrics.record_latency(
            agent_id=event.agent_id,
            latency_ms=event.execution_time_ms,
        )

await event_bus.subscribe(EventType.AGENT_COMPLETED, metrics_handler)
```

### 日志记录

```python
import logging

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseMiddleware):
    async def process(self, context: AgentContext) -> MiddlewareResult:
        logger.info(f"Executing agent: {context.agent_id}")
        logger.debug(f"Task: {context.current_task}")

        start_time = time.time()
        result = await self.call_next(context)
        duration = time.time() - start_time

        logger.info(f"Agent completed in {duration:.2f}s")

        return result
```

### 分布式追踪

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

class TracingMiddleware(BaseMiddleware):
    async def process(self, context: AgentContext) -> MiddlewareResult:
        with tracer.start_as_current_span("agent_execution") as span:
            span.set_attribute("agent_id", context.agent_id)
            span.set_attribute("user_id", context.user_id)

            result = await self.call_next(context)

            span.set_attribute("success", result.success)

            return result
```

## 相关文档

- [Agent 生命周期](lifecycle.md) - 了解 Agent 的创建和执行
- [会话管理](session.md) - 深入了解会话状态管理
- [中间件系统](middleware.md) - 中间件开发指南
- [事件系统](event-system.md) - 事件驱动架构详解

# Agent 生命周期

本文档详细介绍 Agent 从创建到销毁的完整生命周期。

## 生命周期阶段

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Creation │───►│ Execution │───►│ Completion│───►│ Cleanup  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
                    │
                    ▼
              ┌──────────┐
              │   Error  │
              └──────────┘
```

## 1. 创建阶段 (Creation)

### AgentConfig 初始化

```python
from src.common.types.agent_types import AgentConfig

config = AgentConfig(
    name="chatbot_agent",
    description="A helpful chatbot assistant",
    model="gpt-3.5-turbo",
    temperature=0.7,
    max_tokens=1000,
    # 额外配置
    timeout=30,
    retry_attempts=3,
)
```

**配置字段**:
- `name` (必需): Agent 唯一标识符
- `description` (必需): Agent 描述
- `model`: 使用的 LLM 模型
- `temperature`: 输出随机性 (0.0-1.0)
- `max_tokens`: 最大输出 tokens
- `timeout`: 执行超时时间（秒）
- `retry_attempts`: 失败重试次数

### Executor 实例化

```python
from src.agent_runtime.orchestration.executor import AgentExecutor

executor = AgentExecutor(
    agent_id=config.name,
    config=config,
)
```

**可选依赖注入**:
```python
executor = AgentExecutor(
    agent_id=config.name,
    config=config,
    llm_client=custom_llm_client,    # 自定义 LLM 客户端
    event_bus=custom_event_bus,      # 自定义事件总线
    metrics_collector=custom_metrics,  # 自定义指标收集
)
```

### 中间件管道设置

```python
from src.middleware.pipeline import MiddlewarePipeline
from src.middleware.basic_middleware import (
    LoggingMiddleware,
    ValidationMiddleware,
)

pipeline = MiddlewarePipeline()
pipeline.add(LoggingMiddleware(name="logger"))
pipeline.add(ValidationMiddleware(name="validator"))

executor.set_middleware_pipeline(pipeline)
```

## 2. 执行阶段 (Execution)

### 上下文创建

```python
from src.common.types.agent_types import AgentContext

context = AgentContext(
    agent_id="chatbot_agent",
    user_id="user_123",
    session_id="sess_abc123",
    current_task="What is the weather today?",
    metadata={
        "location": "Beijing",
        "language": "zh-CN",
        "timestamp": "2025-01-17T10:00:00Z",
    },
)
```

### 执行流程

```python
# 启动执行
result = await executor.execute(context)
```

**内部执行步骤**:

```
1. 事件: AGENT_STARTED
   ↓
2. 中间件预处理 (Pre-processing)
   │
   ├─ LoggingMiddleware: 记录请求
   ├─ ValidationMiddleware: 验证输入
   ├─ AuthMiddleware: 检查权限
   └─ RateLimitMiddleware: 速率限制
   ↓
3. LLM 调用
   │
   ├─ 构建 Prompt
   ├─ 调用 LLM API
   └─ 处理响应
   ↓
4. 中间件后处理 (Post-processing)
   │
   ├─ OutputSanitizationMiddleware: 清洗输出
   ├─ CachingMiddleware: 缓存结果
   └─ MetricsMiddleware: 收集指标
   ↓
5. 事件: AGENT_COMPLETED (或 ERROR_OCCURRED)
   ↓
6. 返回 AgentResult
```

### 流式执行

```python
# 流式输出
async for chunk in executor.execute_stream(context):
    print(chunk, end="", flush=True)

# 完整示例
async def stream_example():
    full_response = ""
    async for chunk in executor.execute_stream(context):
        full_response += chunk
        print(chunk, end="", flush=True)

    print(f"\n\nFull response: {full_response}")
```

## 3. 完成阶段 (Completion)

### 成功完成

```python
if result.success:
    print(f"Output: {result.output}")
    print(f"Metadata: {result.metadata}")

    # 示例输出:
    # Output: The weather in Beijing today is sunny with a high of 25°C.
    # Metadata: {
    #   "tokens_used": 150,
    #   "execution_time_ms": 1234,
    #   "model": "gpt-3.5-turbo"
    # }
```

### 错误处理

```python
if not result.success:
    print(f"Error: {result.error}")
    print(f"Error Type: {result.metadata.get('error_type')}")

    # 错误类型:
    # - "timeout": 执行超时
    # - "rate_limit": 超出速率限制
    # - "validation_error": 输入验证失败
    # - "llm_error": LLM API 错误
    # - "auth_error": 认证/授权错误
```

### 重试机制

```python
# 配置重试
config = AgentConfig(
    name="resilient_agent",
    description="Agent with retry logic",
    retry_attempts=3,  # 最多重试 3 次
    retry_delay=1.0,   # 每次重试间隔 1 秒
)

# 自定义重试逻辑
class RetryMiddleware(BaseMiddleware):
    async def process(self, context: AgentContext) -> MiddlewareResult:
        max_attempts = context.metadata.get("retry_attempts", 3)

        for attempt in range(max_attempts):
            result = await self.call_next(context)

            if result.success or not self.is_retryable(result):
                return result

            # 等待后重试
            await asyncio.sleep(1.0)

        return result  # 返回最后一次尝试的结果
```

## 4. 清理阶段 (Cleanup)

### 资源释放

```python
# 显式清理
await executor.cleanup()

# 或者使用上下文管理器
async with executor:
    result = await executor.execute(context)
# 自动清理
```

### 会话清理

```python
# 删除会话
await session_manager.delete_session(session_id)

# 清理过期会话
await session_manager.cleanup_expired_sessions()

# 清理用户所有会话
await session_manager.delete_user_sessions(user_id)
```

### 检查点清理

```python
# 删除特定检查点
await session_manager.delete_checkpoint(session_id, checkpoint_id)

# 清理所有检查点
await session_manager.clear_checkpoints(session_id)
```

## 生命周期事件

### 事件序列

```
AGENT_STARTED (开始)
    │
    ├─ MIDDLEWARE_PRE_PROCESS (中间件预处理)
    │
    ├─ LLM_INVOCATION_START (LLM 调用开始)
    │
    ├─ LLM_INVOCATION_COMPLETE (LLM 调用完成)
    │
    ├─ MIDDLEWARE_POST_PROCESS (中间件后处理)
    │
    └─ AGENT_COMPLETED (完成) 或 ERROR_OCCURRED (错误)
```

### 监听生命周期事件

```python
from src.agent_runtime.event_bus import EventType

async def lifecycle_handler(event: SystemEvent):
    print(f"Event: {event.event_type.value}")
    print(f"Agent: {event.agent_id}")
    print(f"Timestamp: {event.timestamp}")

    if event.event_type == EventType.AGENT_STARTED:
        print("Agent execution started")
    elif event.event_type == EventType.AGENT_COMPLETED:
        print(f"Execution time: {event.execution_time_ms}ms")
    elif event.event_type == EventType.ERROR_OCCURRED:
        print(f"Error: {event.error_message}")

await event_bus.subscribe(EventType.ANY, lifecycle_handler)
```

## 生命周期钩子

### 创建钩子

```python
from src.agent_runtime.orchestration.executor import AgentExecutor

class CustomExecutor(AgentExecutor):
    async def on_create(self):
        """创建时调用"""
        print(f"Executor created for agent: {self.agent_id}")
        await self.initialize_resources()

    async def on_execute_start(self, context: AgentContext):
        """执行开始时调用"""
        print(f"Starting execution for user: {context.user_id}")

    async def on_execute_complete(self, context: AgentContext, result: AgentResult):
        """执行完成时调用"""
        print(f"Execution completed: {result.success}")

    async def on_error(self, context: AgentContext, error: Exception):
        """错误时调用"""
        print(f"Error occurred: {str(error)}")
        await self.handle_error(error)

    async def on_cleanup(self):
        """清理时调用"""
        print(f"Cleaning up executor: {self.agent_id}")
        await self.release_resources()
```

### 中间件钩子

```python
class HookMiddleware(BaseMiddleware):
    async def before_process(self, context: AgentContext):
        """处理前钩子"""
        print(f"Before: {context.current_task}")

    async def after_process(self, context: AgentContext, result: AgentResult):
        """处理后钩子"""
        print(f"After: {result.output}")

    async def on_error(self, context: AgentContext, error: Exception):
        """错误钩子"""
        print(f"Error in middleware: {str(error)}")
```

## 状态管理

### 执行状态

```python
from enum import Enum

class ExecutionState(Enum):
    CREATED = "created"         # 已创建
    STARTING = "starting"       # 启动中
    RUNNING = "running"         # 运行中
    COMPLETED = "completed"     # 已完成
    FAILED = "failed"           # 失败
    CANCELLED = "cancelled"     # 已取消
    TIMEOUT = "timeout"         # 超时
```

### 状态转换

```
┌─────────┐
│ CREATED │
└────┬────┘
     │
     ▼
┌─────────┐     ┌─────────┐
│STARTING │───►│ CANCELLED│
└────┬────┘     └─────────┘
     │
     ▼
┌─────────┐     ┌─────────┐
│ RUNNING │───►│ TIMEOUT │
└────┬────┘     └─────────┘
     │
     ├─────────────┐
     │             │
     ▼             ▼
┌─────────┐   ┌─────────┐
│COMPLETED│   │ FAILED  │
└─────────┘   └─────────┘
```

### 状态查询

```python
# 获取执行状态
state = await executor.get_state()

if state == ExecutionState.RUNNING:
    print("Agent is currently running")
elif state == ExecutionState.COMPLETED:
    print("Agent has completed")
```

## 最佳实践

### 1. 资源管理

```python
# 使用上下文管理器确保资源清理
async with AgentExecutor(agent_id="agent", config=config) as executor:
    result = await executor.execute(context)
# 自动清理资源
```

### 2. 错误处理

```python
try:
    result = await executor.execute(context)
except TimeoutError:
    print("Execution timed out")
except ValidationError as e:
    print(f"Invalid input: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
finally:
    await executor.cleanup()
```

### 3. 会话生命周期

```python
# 创建会话
session = await session_manager.create_session(user_id, agent_id)

try:
    # 执行多个任务
    for task in tasks:
        context = AgentContext(
            agent_id=agent_id,
            user_id=user_id,
            session_id=session.session_id,
            current_task=task,
        )

        result = await executor.execute(context)

        # 保存关键检查点
        if is_critical(task):
            await session_manager.save_checkpoint(
                session.session_id,
                {"task": task, "result": result.output},
            )
finally:
    # 清理会话
    await session_manager.delete_session(session.session_id)
```

### 4. 监控和追踪

```python
class TracingExecutor(AgentExecutor):
    async def execute(self, context: AgentContext) -> AgentResult:
        trace_id = str(uuid.uuid4())

        # 开始追踪
        await self.event_bus.publish(SystemEvent(
            event_type=EventType.AGENT_STARTED,
            agent_id=self.agent_id,
            trace_id=trace_id,
            timestamp=datetime.now(),
        ))

        try:
            result = await super().execute(context)

            # 记录成功
            await self.event_bus.publish(SystemEvent(
                event_type=EventType.AGENT_COMPLETED,
                agent_id=self.agent_id,
                trace_id=trace_id,
                execution_time_ms=result.metadata.get("duration_ms"),
                timestamp=datetime.now(),
            ))

            return result
        except Exception as e:
            # 记录错误
            await self.event_bus.publish(SystemEvent(
                event_type=EventType.ERROR_OCCURRED,
                agent_id=self.agent_id,
                trace_id=trace_id,
                error_message=str(e),
                timestamp=datetime.now(),
            ))
            raise
```

## 相关文档

- [系统架构](architecture.md) - 了解整体架构设计
- [会话管理](session.md) - 深入了解会话状态管理
- [中间件系统](middleware.md) - 中间件执行流程
- [事件系统](event-system.md) - 事件处理机制

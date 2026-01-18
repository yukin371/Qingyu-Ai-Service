# AgentExecutor API 参考

AgentExecutor 是 Qingyu Backend AI 的核心执行引擎，负责协调 Agent 的执行。

## 类定义

```python
from src.agent_runtime.orchestration.executor import AgentExecutor

class AgentExecutor:
    def __init__(
        self,
        agent_id: str,
        config: AgentConfig,
        llm_client: BaseLLMClient = None,
        event_bus: EventBus = None,
        metrics_collector: MetricsCollector = None,
    ):
        """
        初始化 AgentExecutor

        Args:
            agent_id: Agent 唯一标识符
            config: Agent 配置
            llm_client: 可选的 LLM 客户端
            event_bus: 可选的事件总线
            metrics_collector: 可选的指标收集器
        """
```

## 方法

### execute()

执行 Agent 任务。

```python
async def execute(
    self,
    context: AgentContext,
) -> AgentResult:
    """
    执行 Agent 任务

    Args:
        context: 执行上下文

    Returns:
        AgentResult: 执行结果

    Raises:
        ValueError: 如果 context 无效
        TimeoutError: 如果执行超时
        RuntimeError: 如果发生严重错误

    Example:
        >>> context = AgentContext(
        ...     agent_id="chatbot",
        ...     user_id="user_123",
        ...     session_id="sess_abc",
        ...     current_task="Hello, how are you?",
        ... )
        >>> result = await executor.execute(context)
        >>> print(result.output)
        'I am doing well, thank you!'
    """
```

### execute_stream()

流式执行 Agent 任务。

```python
async def execute_stream(
    self,
    context: AgentContext,
) -> AsyncIterator[str]:
    """
    流式执行 Agent 任务

    Args:
        context: 执行上下文

    Yields:
        str: 输出片段

    Example:
        >>> async for chunk in executor.execute_stream(context):
        ...     print(chunk, end="", flush=True)
    """
```

### execute_batch()

批量执行 Agent 任务。

```python
async def execute_batch(
    self,
    contexts: List[AgentContext],
) -> List[AgentResult]:
    """
    批量执行 Agent 任务

    Args:
        contexts: 执行上下文列表

    Returns:
        List[AgentResult]: 执行结果列表

    Example:
        >>> contexts = [context1, context2, context3]
        >>> results = await executor.execute_batch(contexts)
        >>> for i, result in enumerate(results):
        ...     print(f"Result {i}: {result.output}")
    """
```

### set_middleware_pipeline()

设置中间件管道。

```python
def set_middleware_pipeline(
    self,
    pipeline: MiddlewarePipeline,
) -> None:
    """
    设置中间件管道

    Args:
        pipeline: 中间件管道

    Example:
        >>> pipeline = MiddlewarePipeline()
        >>> pipeline.add(LoggingMiddleware(name="logger"))
        >>> pipeline.add(AuthMiddleware(name="auth"))
        >>> executor.set_middleware_pipeline(pipeline)
    """
```

### set_event_bus()

设置事件总线。

```python
def set_event_bus(
    self,
    event_bus: EventBus,
) -> None:
    """
    设置事件总线

    Args:
        event_bus: 事件总线

    Example:
        >>> event_bus = EventBus()
        >>> executor.set_event_bus(event_bus)
    """
```

### set_metrics_collector()

设置指标收集器。

```python
def set_metrics_collector(
    self,
    collector: MetricsCollector,
) -> None:
    """
    设置指标收集器

    Args:
        collector: 指标收集器

    Example:
        >>> collector = MetricsCollector()
        >>> executor.set_metrics_collector(collector)
    """
```

### get_state()

获取执行器状态。

```python
async def get_state(self) -> ExecutionState:
    """
    获取执行器状态

    Returns:
        ExecutionState: 当前状态

    Example:
        >>> state = await executor.get_state()
        >>> print(state)
        ExecutionState.IDLE
    """
```

### cleanup()

清理资源。

```python
async def cleanup(self) -> None:
    """
    清理执行器资源

    Example:
        >>> await executor.cleanup()
    """
```

## 使用示例

### 基本使用

```python
import asyncio
from src.agent_runtime.orchestration.executor import AgentExecutor
from src.common.types.agent_types import AgentConfig, AgentContext

async def main():
    # 创建配置
    config = AgentConfig(
        name="chatbot",
        description="A helpful chatbot",
        model="gpt-3.5-turbo",
        temperature=0.7,
    )

    # 创建执行器
    executor = AgentExecutor(
        agent_id="chatbot",
        config=config,
    )

    # 创建上下文
    context = AgentContext(
        agent_id="chatbot",
        user_id="user_123",
        session_id="sess_abc",
        current_task="What is the capital of France?",
    )

    # 执行
    result = await executor.execute(context)

    if result.success:
        print(f"Response: {result.output}")
    else:
        print(f"Error: {result.error}")

asyncio.run(main())
```

### 使用中间件

```python
from src.middleware.pipeline import MiddlewarePipeline
from src.middleware.basic_middleware import (
    LoggingMiddleware,
    AuthMiddleware,
    RateLimitMiddleware,
)

async def main():
    # 创建执行器
    executor = AgentExecutor(
        agent_id="chatbot",
        config=AgentConfig(
            name="chatbot",
            description="A helpful chatbot",
            model="gpt-3.5-turbo",
        ),
    )

    # 创建中间件管道
    pipeline = MiddlewarePipeline()
    pipeline.add(LoggingMiddleware(name="logger"))
    pipeline.add(AuthMiddleware(name="auth"))
    pipeline.add(RateLimitMiddleware(
        name="rate_limit",
        max_requests=100,
        window_seconds=60,
    ))

    # 设置管道
    executor.set_middleware_pipeline(pipeline)

    # 执行
    context = AgentContext(
        agent_id="chatbot",
        user_id="user_123",
        session_id="sess_abc",
        current_task="Hello!",
    )

    result = await executor.execute(context)

asyncio.run(main())
```

### 流式输出

```python
async def main():
    executor = AgentExecutor(
        agent_id="chatbot",
        config=AgentConfig(
            name="chatbot",
            description="A helpful chatbot",
            model="gpt-3.5-turbo",
        ),
    )

    context = AgentContext(
        agent_id="chatbot",
        user_id="user_123",
        session_id="sess_abc",
        current_task="Tell me a story",
    )

    # 流式执行
    full_response = ""
    async for chunk in executor.execute_stream(context):
        print(chunk, end="", flush=True)
        full_response += chunk

    print(f"\n\nFull response length: {len(full_response)}")

asyncio.run(main())
```

### 事件处理

```python
from src.agent_runtime.event_bus import EventBus, EventType

async def main():
    # 创建事件总线
    event_bus = EventBus()

    # 订阅事件
    async def on_agent_started(event):
        print(f"Agent {event.agent_id} started")

    async def on_agent_completed(event):
        print(f"Agent completed in {event.execution_time_ms}ms")

    await event_bus.subscribe(EventType.AGENT_STARTED, on_agent_started)
    await event_bus.subscribe(EventType.AGENT_COMPLETED, on_agent_completed)

    # 创建执行器并设置事件总线
    executor = AgentExecutor(
        agent_id="chatbot",
        config=AgentConfig(
            name="chatbot",
            description="A helpful chatbot",
            model="gpt-3.5-turbo",
        ),
    )

    executor.set_event_bus(event_bus)

    # 执行
    context = AgentContext(
        agent_id="chatbot",
        user_id="user_123",
        session_id="sess_abc",
        current_task="Hello!",
    )

    result = await executor.execute(context)

asyncio.run(main())
```

### 错误处理

```python
async def main():
    executor = AgentExecutor(
        agent_id="chatbot",
        config=AgentConfig(
            name="chatbot",
            description="A helpful chatbot",
            model="gpt-3.5-turbo",
        ),
    )

    context = AgentContext(
        agent_id="chatbot",
        user_id="user_123",
        session_id="sess_abc",
        current_task="Hello!",
    )

    try:
        result = await executor.execute(context)

        if not result.success:
            # 处理业务错误
            print(f"Agent error: {result.error}")
            print(f"Error type: {result.metadata.get('error_type')}")

            # 根据错误类型处理
            error_type = result.metadata.get('error_type')

            if error_type == "rate_limit":
                print("Rate limit exceeded, please wait")
            elif error_type == "validation_error":
                print("Invalid input")
            elif error_type == "timeout":
                print("Request timed out")
            else:
                print(f"Unknown error: {error_type}")

    except ValueError as e:
        print(f"Invalid context: {e}")
    except TimeoutError as e:
        print(f"Execution timed out: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

asyncio.run(main())
```

### 上下文管理器

```python
async def main():
    # 使用上下文管理器自动清理
    async with AgentExecutor(
        agent_id="chatbot",
        config=AgentConfig(
            name="chatbot",
            description="A helpful chatbot",
            model="gpt-3.5-turbo",
        ),
    ) as executor:
        context = AgentContext(
            agent_id="chatbot",
            user_id="user_123",
            session_id="sess_abc",
            current_task="Hello!",
        )

        result = await executor.execute(context)
        print(result.output)

    # 自动调用 cleanup()

asyncio.run(main())
```

## 配置选项

### AgentConfig

```python
class AgentConfig(BaseModel):
    name: str                          # Agent 名称（必需）
    description: str                   # Agent 描述（必需）
    model: str = "gpt-3.5-turbo"      # 使用的模型
    temperature: float = 0.7           # 温度参数 (0.0-1.0)
    max_tokens: int = 1000             # 最大 tokens
    top_p: float = 1.0                 # Top-p 采样
    frequency_penalty: float = 0.0      # 频率惩罚
    presence_penalty: float = 0.0       # 存在惩罚
    stop_sequences: List[str] = []     # 停止序列
    system_prompt: str = None          # 系统提示词
    timeout: int = 30                  # 超时时间（秒）
    retry_attempts: int = 3            # 重试次数
    retry_delay: float = 1.0           # 重试延迟（秒）
```

### AgentContext

```python
class AgentContext(BaseModel):
    agent_id: str                      # Agent ID（必需）
    user_id: str                       # 用户 ID（必需）
    session_id: str                    # 会话 ID（必需）
    current_task: str                  # 当前任务（必需）
    metadata: Dict[str, Any] = {}      # 元数据
    created_at: datetime = None        # 创建时间
```

### AgentResult

```python
class AgentResult(BaseModel):
    success: bool                      # 是否成功
    output: str = ""                   # 输出内容
    error: str = ""                    # 错误消息
    metadata: Dict[str, Any] = {}      # 元数据
    tokens_used: int = 0               # 使用的 tokens
    execution_time_ms: int = 0         # 执行时间（毫秒）
```

## 性能考虑

### 并发执行

```python
import asyncio

async def execute_concurrently():
    executor = AgentExecutor(
        agent_id="chatbot",
        config=AgentConfig(
            name="chatbot",
            description="A helpful chatbot",
            model="gpt-3.5-turbo",
        ),
    )

    # 创建多个上下文
    contexts = [
        AgentContext(
            agent_id="chatbot",
            user_id=f"user_{i}",
            session_id=f"sess_{i}",
            current_task=f"Task {i}",
        )
        for i in range(10)
    ]

    # 并发执行
    tasks = [executor.execute(ctx) for ctx in contexts]
    results = await asyncio.gather(*tasks)

    return results
```

### 批量执行

```python
async def execute_in_batches():
    executor = AgentExecutor(
        agent_id="chatbot",
        config=AgentConfig(
            name="chatbot",
            description="A helpful chatbot",
            model="gpt-3.5-turbo",
        ),
    )

    # 批量执行更高效
    contexts = [context1, context2, context3]
    results = await executor.execute_batch(contexts)

    return results
```

## 相关文档

- [AgentConfig API](config.md) - 配置 API
- [AgentContext API](context.md) - 上下文 API
- [SessionManager API](session-manager.md) - 会话管理 API
- [EventBus API](event-bus.md) - 事件总线 API
- [MiddlewarePipeline API](middleware.md) - 中间件 API

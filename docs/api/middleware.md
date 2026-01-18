# MiddlewarePipeline API 参考

MiddlewarePipeline 实现了洋葱模型的中间件处理系统。

## 类定义

```python
from src.middleware.pipeline import MiddlewarePipeline

class MiddlewarePipeline:
    def __init__(self):
        """
        初始化中间件管道
        """
```

## 方法

### add()

添加中间件。

```python
def add(
    self,
    middleware: BaseMiddleware,
) -> None:
    """
    添加中间件到管道

    Args:
        middleware: 中间件实例

    Example:
        >>> pipeline = MiddlewarePipeline()
        >>> pipeline.add(LoggingMiddleware(name="logger"))
        >>> pipeline.add(AuthMiddleware(name="auth"))
    """
```

### remove()

移除中间件。

```python
def remove(
    self,
    middleware_name: str,
) -> bool:
    """
    从管道中移除中间件

    Args:
        middleware_name: 中间件名称

    Returns:
        bool: 是否移除成功

    Example:
        >>> success = pipeline.remove("logger")
    """
```

### get()

获取中间件。

```python
def get(
    self,
    middleware_name: str,
) -> Optional[BaseMiddleware]:
    """
    获取中间件

    Args:
        middleware_name: 中间件名称

    Returns:
        Optional[BaseMiddleware]: 中间件实例，如果不存在返回 None

    Example:
        >>> middleware = pipeline.get("logger")
        >>> if middleware:
        ...     print(f"Found: {middleware.name}")
    """
```

### clear()

清空管道。

```python
def clear(
    self,
) -> None:
    """
    清空所有中间件

    Example:
        >>> pipeline.clear()
    """
```

### get_middleware_count()

获取中间件数量。

```python
def get_middleware_count(
    self,
) -> int:
    """
    获取中间件数量

    Returns:
        int: 中间件数量

    Example:
        >>> count = pipeline.get_middleware_count()
        >>> print(f"Middleware count: {count}")
    """
```

## BaseMiddleware

所有中间件都继承自 `BaseMiddleware`。

```python
from src.middleware.base import BaseMiddleware

class BaseMiddleware:
    def __init__(self, name: str):
        """
        初始化中间件

        Args:
            name: 中间件名称
        """
        self.name = name
        self.next_middleware = None

    async def process(
        self,
        context: AgentContext,
    ) -> MiddlewareResult:
        """
        处理请求

        Args:
            context: Agent 上下文

        Returns:
            MiddlewareResult: 处理结果

        Raises:
            NotImplementedError: 子类必须实现
        """
        raise NotImplementedError

    async def call_next(
        self,
        context: AgentContext,
    ) -> MiddlewareResult:
        """
        调用下一个中间件

        Args:
            context: Agent 上下文

        Returns:
            MiddlewareResult: 下一个中间件或 Agent 的结果
        """
        if self.next_middleware:
            return await self.next_middleware.process(context)
        else:
            # 没有更多中间件，返回继续
            return MiddlewareResult(
                success=True,
                agent_result=AgentResult(success=True, output=""),
                skip_agent=False,
            )
```

## MiddlewareResult

中间件处理结果。

```python
class MiddlewareResult(BaseModel):
    success: bool                      # 是否成功
    agent_result: AgentResult          # Agent 结果
    skip_agent: bool = False           # 是否跳过 Agent 执行
    skip_rest: bool = False            # 是否跳过剩余中间件
```

## 内置中间件

### LoggingMiddleware

记录请求和响应日志。

```python
from src.middleware.basic_middleware import LoggingMiddleware

middleware = LoggingMiddleware(
    name="logger",
    log_level="INFO",
    log_requests=True,
    log_responses=True,
)
```

### AuthMiddleware

验证用户身份。

```python
from src.middleware.basic_middleware import AuthMiddleware

middleware = AuthMiddleware(
    name="auth",
    require_auth=True,
    allow_anonymous=False,
)
```

### ValidationMiddleware

验证输入数据。

```python
from src.middleware.basic_middleware import ValidationMiddleware

middleware = ValidationMiddleware(
    name="validator",
    max_length=10000,
    min_length=1,
    allowed_patterns=[r"^[a-zA-Z0-9\s?!.,]+$"],
)
```

### RateLimitMiddleware

限制请求频率。

```python
from src.middleware.basic_middleware import RateLimitMiddleware

middleware = RateLimitMiddleware(
    name="rate_limit",
    max_requests=100,
    window_seconds=60,
    per_user=True,
)
```

## 使用示例

### 基本使用

```python
import asyncio
from src.middleware.pipeline import MiddlewarePipeline
from src.middleware.base import BaseMiddleware, MiddlewareResult, AgentResult
from src.common.types.agent_types import AgentContext

# 自定义中间件
class UppercaseMiddleware(BaseMiddleware):
    async def process(self, context: AgentContext) -> MiddlewareResult:
        """将任务转为大写"""
        print(f"[{self.name}] Before: {context.current_task}")

        # 调用下一个
        result = await self.call_next(context)

        # 后处理
        print(f"[{self.name}] After: {result.agent_result.output}")

        return result

async def main():
    # 创建管道
    pipeline = MiddlewarePipeline()

    # 添加中间件
    pipeline.add(UppercaseMiddleware(name="upper1"))
    pipeline.add(UppercaseMiddleware(name="upper2"))
    pipeline.add(UppercaseMiddleware(name="upper3"))

    # 创建上下文
    context = AgentContext(
        agent_id="test_agent",
        user_id="test_user",
        session_id="test_session",
        current_task="hello world",
    )

    # 执行管道
    result = await pipeline.execute(context)

asyncio.run(main())
```

### 跳过 Agent 执行

```python
class CacheMiddleware(BaseMiddleware):
    def __init__(self, name: str):
        super().__init__(name)
        self.cache = {}

    async def process(self, context: AgentContext) -> MiddlewareResult:
        """检查缓存"""
        cache_key = context.current_task

        if cache_key in self.cache:
            # 返回缓存结果，跳过 Agent
            return MiddlewareResult(
                success=True,
                agent_result=AgentResult(
                    success=True,
                    output=self.cache[cache_key],
                    metadata={"cached": True},
                ),
                skip_agent=True,  # 跳过 Agent 执行
            )

        # 执行 Agent
        result = await self.call_next(context)

        # 缓存结果
        if result.success:
            self.cache[cache_key] = result.agent_result.output

        return result
```

### 停止管道执行

```python
class ValidationMiddleware(BaseMiddleware):
    async def process(self, context: AgentContext) -> MiddlewareResult:
        """验证输入"""
        if len(context.current_task) > 1000:
            # 输入太长，停止执行
            return MiddlewareResult(
                success=False,
                agent_result=AgentResult(
                    success=False,
                    output="",
                    error="Input too long",
                ),
                skip_rest=True,  # 跳过剩余中间件
            )

        return await self.call_next(context)
```

### 修改上下文

```python
class ContextModifierMiddleware(BaseMiddleware):
    async def process(self, context: AgentContext) -> MiddlewareResult:
        """修改上下文"""
        # 添加元数据
        context.metadata["processed_by"] = self.name
        context.metadata["timestamp"] = datetime.now().isoformat()

        # 修改任务
        original_task = context.current_task
        context.current_task = f"Please help with: {original_task}"

        # 执行
        result = await self.call_next(context)

        # 恢复原始任务（如果需要）
        context.current_task = original_task

        return result
```

### 错误处理

```python
class ErrorHandlingMiddleware(BaseMiddleware):
    async def process(self, context: AgentContext) -> MiddlewareResult:
        """处理错误"""
        try:
            return await self.call_next(context)
        except ValueError as e:
            # 处理特定错误
            return MiddlewareResult(
                success=False,
                agent_result=AgentResult(
                    success=False,
                    output="",
                    error=f"Validation error: {e}",
                    metadata={"error_type": "validation_error"},
                ),
                skip_rest=True,
            )
        except Exception as e:
            # 处理其他错误
            return MiddlewareResult(
                success=False,
                agent_result=AgentResult(
                    success=False,
                    output="",
                    error=f"Unexpected error: {e}",
                    metadata={"error_type": "internal_error"},
                ),
                skip_rest=True,
            )
```

### 指标收集

```python
class MetricsMiddleware(BaseMiddleware):
    def __init__(self, name: str, metrics_collector):
        super().__init__(name)
        self.metrics = metrics_collector

    async def process(self, context: AgentContext) -> MiddlewareResult:
        """收集指标"""
        import time

        start_time = time.time()

        # 执行
        result = await self.call_next(context)

        # 记录指标
        duration = time.time() - start_time

        await self.metrics.record(
            agent_id=context.agent_id,
            user_id=context.user_id,
            duration_ms=duration * 1000,
            success=result.success,
        )

        return result
```

### 条件执行

```python
class ConditionalMiddleware(BaseMiddleware):
    def __init__(self, name: str, condition, middleware):
        super().__init__(name)
        self.condition = condition
        self.middleware = middleware

    async def process(self, context: AgentContext) -> MiddlewareResult:
        """只在满足条件时执行"""
        if self.condition(context):
            return await self.middleware.process(context)
        else:
            return await self.call_next(context)

# 使用
pipeline.add(
    ConditionalMiddleware(
        name="conditional_auth",
        condition=lambda ctx: ctx.metadata.get("require_auth", True),
        middleware=AuthMiddleware(name="auth"),
    )
)
```

### 组合中间件

```python
class CompositeMiddleware(BaseMiddleware):
    def __init__(self, name: str, middlewares: list):
        super().__init__(name)
        self.middlewares = middlewares

    async def process(self, context: AgentContext) -> MiddlewareResult:
        """组合多个中间件"""
        for middleware in self.middlewares:
            result = await middleware.process(context)

            # 如果中间件要求停止，则停止
            if hasattr(result, 'skip_rest') and result.skip_rest:
                return result

            # 如果中间件跳过 Agent，直接返回
            if hasattr(result, 'skip_agent') and result.skip_agent:
                return result

        return result

# 使用
composite = CompositeMiddleware(
    name="composite",
    middlewares=[
        LoggingMiddleware(name="logger1"),
        ValidationMiddleware(name="validator"),
        LoggingMiddleware(name="logger2"),
    ],
)

pipeline.add(composite)
```

## 与 Executor 集成

```python
from src.agent_runtime.orchestration.executor import AgentExecutor

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
    pipeline.add(RateLimitMiddleware(name="rate_limit"))

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

## 最佳实践

### 1. 单一职责

```python
# ✅ 好：每个中间件只做一件事
class LoggingMiddleware(BaseMiddleware):
    async def process(self, context: AgentContext) -> MiddlewareResult:
        print(f"Processing: {context.current_task}")
        return await self.call_next(context)

class AuthMiddleware(BaseMiddleware):
    async def process(self, context: AgentContext) -> MiddlewareResult:
        if not self.is_authenticated(context):
            return MiddlewareResult(success=False, ...)
        return await self.call_next(context)

# ❌ 不好：一个中间件做太多事
class EverythingMiddleware(BaseMiddleware):
    async def process(self, context: AgentContext) -> MiddlewareResult:
        # 日志
        print(f"Processing: {context.current_task}")

        # 认证
        if not self.is_authenticated(context):
            return MiddlewareResult(success=False, ...)

        # 验证
        if not self.is_valid(context):
            return MiddlewareResult(success=False, ...)

        # ...
```

### 2. 正确处理错误

```python
class SafeMiddleware(BaseMiddleware):
    async def process(self, context: AgentContext) -> MiddlewareResult:
        try:
            return await self.call_next(context)
        except Exception as e:
            # 返回错误而不是抛出异常
            return MiddlewareResult(
                success=False,
                agent_result=AgentResult(
                    success=False,
                    output="",
                    error=str(e),
                ),
            )
```

### 3. 使用配置

```python
class ConfigurableMiddleware(BaseMiddleware):
    def __init__(self, name: str, **options):
        super().__init__(name)
        self.options = options

    async def process(self, context: AgentContext) -> MiddlewareResult:
        # 使用配置
        enabled = self.options.get("enabled", True)

        if not enabled:
            return await self.call_next(context)

        # 正常处理
        return await self._do_process(context)
```

## 相关文档

- [AgentExecutor API](executor.md) - 执行器 API
- [中间件系统概念](../concepts/middleware.md) - 中间件概念
- [中间件开发指南](../guides/middleware.md) - 开发指南

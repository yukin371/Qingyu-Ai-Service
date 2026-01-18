# 中间件开发指南

本指南介绍如何开发和测试自定义中间件。

## 基础概念

### 什么是中间件

中间件是在 Agent 执行前后插入自定义逻辑的组件。它们按照洋葱模型执行：

```
Request → Middleware 1 → Middleware 2 → ... → Agent → ... → Middleware 2 → Middleware 1 → Response
           Pre-processing                                    Post-processing
```

### 中间件生命周期

```
┌─────────────────────────────────────────────────┐
│              Middleware.process()                │
├─────────────────────────────────────────────────┤
│                                                 │
│  1. 前置处理 (Pre-processing)                   │
│     - 检查/修改 context                          │
│     - 验证请求                                   │
│     - 记录日志                                   │
│                                                 │
│  2. 调用下一个 (call_next)                      │
│     - 调用下一个中间件或 Agent                   │
│                                                 │
│  3. 后置处理 (Post-processing)                  │
│     - 检查/修改 result                           │
│     - 记录响应                                   │
│     - 收集指标                                   │
│                                                 │
└─────────────────────────────────────────────────┘
```

## 创建基础中间件

### 模板

```python
from src.middleware.base import BaseMiddleware
from src.common.types.agent_types import AgentContext, MiddlewareResult, AgentResult

class MyCustomMiddleware(BaseMiddleware):
    def __init__(self, name: str, **options):
        """
        初始化中间件

        Args:
            name: 中间件名称
            **options: 配置选项
        """
        super().__init__(name)
        self.options = options

    async def process(self, context: AgentContext) -> MiddlewareResult:
        """
        处理请求

        Args:
            context: Agent 上下文

        Returns:
            MiddlewareResult: 处理结果
        """
        # ========== 前置处理 ==========

        # 提取信息
        user_id = context.user_id
        task = context.current_task

        # 执行前置逻辑
        # 例如：验证、检查、修改 context 等

        # ========== 调用下一个 ==========

        result = await self.call_next(context)

        # ========== 后置处理 ==========

        # 处理 Agent 的结果
        if result.success:
            # 成功时的处理
            pass
        else:
            # 失败时的处理
            pass

        # 可以修改结果
        # result.agent_result.output = modified_output

        return result
```

### 示例：计时中间件

```python
import time
from src.middleware.base import BaseMiddleware
from src.common.types.agent_types import AgentContext, MiddlewareResult

class TimingMiddleware(BaseMiddleware):
    async def process(self, context: AgentContext) -> MiddlewareResult:
        """记录执行时间"""
        start_time = time.time()

        # 执行
        result = await self.call_next(context)

        # 记录时间
        duration = time.time() - start_time

        # 添加到元数据
        result.agent_result.metadata["duration_seconds"] = duration

        # 记录日志
        print(f"[{self.name}] Execution time: {duration:.2f}s")

        return result
```

### 示例：缓存中间件

```python
import hashlib
from typing import Dict
from src.middleware.base import BaseMiddleware
from src.common.types.agent_types import AgentContext, MiddlewareResult

class CacheMiddleware(BaseMiddleware):
    def __init__(self, name: str, ttl: int = 300):
        super().__init__(name)
        self.cache: Dict[str, MiddlewareResult] = {}
        self.ttl = ttl

    def _get_cache_key(self, context: AgentContext) -> str:
        """生成缓存键"""
        data = f"{context.agent_id}:{context.current_task}"
        return hashlib.md5(data.encode()).hexdigest()

    async def process(self, context: AgentContext) -> MiddlewareResult:
        """检查并使用缓存"""
        cache_key = self._get_cache_key(context)

        # 检查缓存
        if cache_key in self.cache:
            print(f"[{self.name}] Cache hit: {cache_key}")
            return self.cache[cache_key]

        # 缓存未命中，执行
        print(f"[{self.name}] Cache miss: {cache_key}")
        result = await self.call_next(context)

        # 缓存成功的结果
        if result.success:
            self.cache[cache_key] = result

        return result
```

### 示例：验证中间件

```python
from src.middleware.base import BaseMiddleware
from src.common.types.agent_types import AgentContext, MiddlewareResult

class ValidationMiddleware(BaseMiddleware):
    def __init__(self, name: str, max_length: int = 10000):
        super().__init__(name)
        self.max_length = max_length

    async def process(self, context: AgentContext) -> MiddlewareResult:
        """验证输入"""
        # 验证长度
        if len(context.current_task) > self.max_length:
            return MiddlewareResult(
                success=False,
                agent_result=AgentResult(
                    success=False,
                    output="",
                    error=f"Input too long (max {self.max_length} chars)",
                ),
                skip_rest=True,  # 停止处理
            )

        # 继续执行
        return await self.call_next(context)
```

## 高级模式

### 跳过 Agent 执行

```python
class CachedResponseMiddleware(BaseMiddleware):
    def __init__(self, name: str):
        super().__init__(name)
        self.responses = {}

    async def process(self, context: AgentContext) -> MiddlewareResult:
        """返回缓存响应，跳过 Agent"""
        task = context.current_task

        if task in self.responses:
            # 返回缓存结果，跳过 Agent
            return MiddlewareResult(
                success=True,
                agent_result=AgentResult(
                    success=True,
                    output=self.responses[task],
                    metadata={"cached": True},
                ),
                skip_agent=True,  # 关键：跳过 Agent 执行
            )

        # 执行 Agent
        result = await self.call_next(context)

        # 缓存响应
        if result.success:
            self.responses[task] = result.agent_result.output

        return result
```

### 停止管道执行

```python
class BlockingMiddleware(BaseMiddleware):
    def __init__(self, name: str, blocked_users: list):
        super().__init__(name)
        self.blocked_users = set(blocked_users)

    async def process(self, context: AgentContext) -> MiddlewareResult:
        """阻止特定用户"""
        if context.user_id in self.blocked_users:
            # 返回错误，停止所有后续处理
            return MiddlewareResult(
                success=False,
                agent_result=AgentResult(
                    success=False,
                    output="",
                    error="User is blocked",
                ),
                skip_rest=True,  # 关键：跳过所有后续中间件
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

        # 修改任务（添加前缀）
        original_task = context.current_task
        context.current_task = f"Please assist with: {original_task}"

        # 执行
        result = await self.call_next(context)

        # 可选：恢复原始任务
        # context.current_task = original_task

        return result
```

### 修改结果

```python
class ResultModifierMiddleware(BaseMiddleware):
    async def process(self, context: AgentContext) -> MiddlewareResult:
        """修改 Agent 结果"""
        result = await self.call_next(context)

        if result.success:
            # 添加前缀
            prefix = f"[Response from {context.agent_id}]\n"
            result.agent_result.output = prefix + result.agent_result.output

            # 添加后缀
            result.agent_result.output += "\n[End of response]"

        return result
```

### 条件执行

```python
class ConditionalMiddleware(BaseMiddleware):
    def __init__(self, name: str, condition_func, actual_middleware):
        super().__init__(name)
        self.condition = condition_func
        self.middleware = actual_middleware

    async def process(self, context: AgentContext) -> MiddlewareResult:
        """只在满足条件时执行"""
        if self.condition(context):
            return await self.middleware.process(context)
        else:
            return await self.call_next(context)

# 使用示例
def is_premium_user(context):
    return context.metadata.get("tier") == "premium"

pipeline.add(
    ConditionalMiddleware(
        name="conditional_auth",
        condition_func=is_premium_user,
        actual_handler=AuthMiddleware(name="auth"),
    )
)
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
            )
        except TimeoutError as e:
            # 处理超时
            return MiddlewareResult(
                success=False,
                agent_result=AgentResult(
                    success=False,
                    output="",
                    error="Request timed out",
                    metadata={"error_type": "timeout"},
                ),
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
            )
```

### 重试逻辑

```python
import asyncio

class RetryMiddleware(BaseMiddleware):
    def __init__(self, name: str, max_attempts: int = 3, delay: float = 1.0):
        super().__init__(name)
        self.max_attempts = max_attempts
        self.delay = delay

    def _should_retry(self, result: MiddlewareResult) -> bool:
        """判断是否应该重试"""
        if result.success:
            return False

        error_type = result.agent_result.metadata.get("error_type")

        # 可重试的错误类型
        retryable_errors = ["timeout", "rate_limit", "llm_error"]

        return error_type in retryable_errors

    async def process(self, context: AgentContext) -> MiddlewareResult:
        """带重试的执行"""
        last_result = None

        for attempt in range(self.max_attempts):
            result = await self.call_next(context)

            if not self._should_retry(result):
                return result

            last_result = result

            # 等待后重试
            if attempt < self.max_attempts - 1:
                print(f"[{self.name}] Retry {attempt + 1}/{self.max_attempts}")
                await asyncio.sleep(self.delay * (attempt + 1))

        return last_result
```

## 测试中间件

### 单元测试

```python
import pytest
from unittest.mock import AsyncMock

# 测试中间件
class TestMyMiddleware:
    @pytest.fixture
    def middleware(self):
        return MyCustomMiddleware(
            name="test_middleware",
            option1="value1",
        )

    @pytest.fixture
    def mock_context(self):
        return AgentContext(
            agent_id="test_agent",
            user_id="test_user",
            session_id="test_session",
            current_task="Test task",
        )

    @pytest.mark.asyncio
    async def test_process_success(self, middleware, mock_context):
        """测试成功处理"""
        # Mock call_next
        middleware.call_next = AsyncMock(return_value=MiddlewareResult(
            success=True,
            agent_result=AgentResult(
                success=True,
                output="Test output",
            ),
        ))

        # 执行
        result = await middleware.process(mock_context)

        # 验证
        assert result.success is True
        assert result.agent_result.output == "Test output"
        assert middleware.call_next.called

    @pytest.mark.asyncio
    async def test_process_with_error(self, middleware, mock_context):
        """测试错误处理"""
        # Mock call_next 返回错误
        middleware.call_next = AsyncMock(return_value=MiddlewareResult(
            success=False,
            agent_result=AgentResult(
                success=False,
                output="",
                error="Test error",
            ),
        ))

        # 执行
        result = await middleware.process(mock_context)

        # 验证
        assert result.success is False
```

### 集成测试

```python
@pytest.mark.asyncio
async def test_middleware_in_pipeline():
    """测试中间件在管道中的行为"""
    # 创建管道
    pipeline = MiddlewarePipeline()
    pipeline.add(MyCustomMiddleware(name="test1"))
    pipeline.add(MyCustomMiddleware(name="test2"))

    # 创建执行器
    executor = AgentExecutor(
        agent_id="test_agent",
        config=AgentConfig(
            name="test_agent",
            description="Test agent",
            model="gpt-3.5-turbo",
        ),
    )
    executor.set_middleware_pipeline(pipeline)

    # 执行
    context = AgentContext(
        agent_id="test_agent",
        user_id="test_user",
        session_id="test_session",
        current_task="Test",
    )

    result = await executor.execute(context)

    # 验证
    assert result.success is True
```

## 最佳实践

### 1. 单一职责

每个中间件应该只做一件事：

```python
# ✅ 好：每个中间件一个职责
class LoggingMiddleware(BaseMiddleware):
    async def process(self, context):
        print(f"Processing: {context.current_task}")
        return await self.call_next(context)

class AuthMiddleware(BaseMiddleware):
    async def process(self, context):
        if not self.is_authenticated(context):
            return MiddlewareResult(success=False, ...)
        return await self.call_next(context)

# ❌ 不好：一个中间件做太多事
class EverythingMiddleware(BaseMiddleware):
    async def process(self, context):
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

### 2. 正确使用 skip_agent 和 skip_rest

- `skip_agent=True`: 跳过 Agent 执行，直接返回结果（用于缓存等）
- `skip_rest=True`: 跳过所有后续中间件（用于阻止、验证失败等）

```python
# 缓存：跳过 Agent
if cache_hit:
    return MiddlewareResult(
        success=True,
        agent_result=cached_result,
        skip_agent=True,  # 跳过 Agent
    )

# 验证失败：停止所有处理
if invalid:
    return MiddlewareResult(
        success=False,
        agent_result=error_result,
        skip_rest=True,  # 跳过所有后续中间件
    )
```

### 3. 错误隔离

中间件应该捕获自己的错误，不影响其他中间件：

```python
class SafeMiddleware(BaseMiddleware):
    async def process(self, context):
        try:
            # 处理逻辑
            return await self.call_next(context)
        except Exception as e:
            # 记录错误但不抛出
            logger.error(f"Middleware error: {e}")
            return MiddlewareResult(
                success=False,
                agent_result=AgentResult(
                    success=False,
                    error="Middleware error",
                ),
            )
```

### 4. 使用配置

使中间件可配置：

```python
class ConfigurableMiddleware(BaseMiddleware):
    def __init__(self, name: str, **options):
        super().__init__(name)
        self.enabled = options.get("enabled", True)
        self.cache_size = options.get("cache_size", 100)
        self.ttl = options.get("ttl", 300)

    async def process(self, context):
        if not self.enabled:
            return await self.call_next(context)

        # 使用配置
        # ...
```

### 5. 记录日志

添加详细的日志记录：

```python
import logging

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseMiddleware):
    async def process(self, context):
        logger.info(f"[{self.name}] Processing: {context.current_task}")

        result = await self.call_next(context)

        if result.success:
            logger.info(f"[{self.name}] Success")
        else:
            logger.error(f"[{self.name}] Failed: {result.agent_result.error}")

        return result
```

## 相关文档

- [MiddlewarePipeline API](../api/middleware.md) - 中间件 API
- [中间件系统概念](../concepts/middleware.md) - 中间件概念

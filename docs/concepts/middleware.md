# 中间件系统

本文档详细介绍 Qingyu Backend AI 的中间件系统，采用洋葱模型的处理模式。

## 概述

中间件系统提供了在 Agent 执行前后插入自定义逻辑的机制，支持日志记录、认证、验证、缓存等功能。

### 洋葱模型

```
         Request →
            │
    ┌───────▼───────┐
    │  Middleware 1 │
    │  (Logging)    │
    └───────┬───────┘
            │
    ┌───────▼───────┐
    │  Middleware 2 │
    │    (Auth)     │
    └───────┬───────┘
            │
    ┌───────▼───────┐
    │  Middleware 3 │
    │  (Rate Limit) │
    └───────┬───────┘
            │
    ┌───────▼───────┐
    │     Agent     │
    │   Execution   │
    └───────┬───────┘
            │
    ┌───────▲───────┐
    │  Middleware 3 │
    │  (Post Limit) │
    └───────▲───────┘
            │
    ┌───────▲───────┐
    │  Middleware 2 │
    │ (Post Auth)   │
    └───────▲───────┘
            │
    ┌───────▲───────┐
    │  Middleware 1 │
    │ (Post Log)    │
    └───────▲───────┘
            │
         ← Response
```

## 基础概念

### BaseMiddleware

所有中间件都继承自 `BaseMiddleware`:

```python
from src.middleware.base import BaseMiddleware

class CustomMiddleware(BaseMiddleware):
    def __init__(self, name: str, **options):
        super().__init__(name)
        self.options = options

    async def process(self, context: AgentContext) -> MiddlewareResult:
        # 前置处理
        print(f"Before: {context.current_task}")

        # 调用下一个中间件
        result = await self.call_next(context)

        # 后置处理
        print(f"After: {result.agent_result.output}")

        return result
```

### MiddlewareResult

中间件处理结果:

```python
from src.common.types.agent_types import AgentResult, MiddlewareResult

result = MiddlewareResult(
    success=True,
    agent_result=AgentResult(
        success=True,
        output="Response",
        metadata={"key": "value"},
    ),
    skip_agent=False,  # 是否跳过 Agent 执行
    skip_rest=False,   # 是否跳过剩余中间件
)
```

## 内置中间件

### 1. LoggingMiddleware

记录请求和响应日志:

```python
from src.middleware.basic_middleware import LoggingMiddleware

middleware = LoggingMiddleware(
    name="logger",
    log_level="INFO",
    log_requests=True,
    log_responses=True,
)
```

### 2. AuthMiddleware

验证用户身份:

```python
from src.middleware.basic_middleware import AuthMiddleware

middleware = AuthMiddleware(
    name="auth",
    require_auth=True,
    allow_anonymous=False,
)
```

### 3. ValidationMiddleware

验证输入数据:

```python
from src.middleware.basic_middleware import ValidationMiddleware

middleware = ValidationMiddleware(
    name="validator",
    max_length=10000,
    min_length=1,
    allowed_patterns=[r"^[a-zA-Z0-9\s?!.,]+$"],
)
```

### 4. RateLimitMiddleware

限制请求频率:

```python
from src.middleware.basic_middleware import RateLimitMiddleware

middleware = RateLimitMiddleware(
    name="rate_limit",
    max_requests=100,      # 最大请求数
    window_seconds=60,     # 时间窗口（秒）
    per_user=True,         # 按用户限制
)
```

## 创建自定义中间件

### 基本模板

```python
from src.middleware.base import BaseMiddleware
from src.common.types.agent_types import AgentContext, MiddlewareResult, AgentResult

class MyCustomMiddleware(BaseMiddleware):
    def __init__(self, name: str, **options):
        super().__init__(name)
        self.options = options

    async def process(self, context: AgentContext) -> MiddlewareResult:
        # ========== 前置处理 ==========

        # 1. 提取需要的信息
        user_id = context.user_id
        task = context.current_task

        # 2. 执行前置逻辑
        # 例如：验证、检查、修改 context 等

        # ========== 调用下一个 ==========

        result = await self.call_next(context)

        # ========== 后置处理 ==========

        # 3. 处理 Agent 的结果
        if result.success:
            # 成功时的处理
            pass
        else:
            # 失败时的处理
            pass

        # 4. 可以修改结果
        # result.agent_result.output = modified_output

        return result
```

### 缓存中间件示例

```python
import hashlib
import json
from typing import Optional

class CacheMiddleware(BaseMiddleware):
    def __init__(self, name: str, cache_client, ttl: int = 300):
        super().__init__(name)
        self.cache = cache_client
        self.ttl = ttl

    def _get_cache_key(self, context: AgentContext) -> str:
        """生成缓存键"""
        data = {
            "task": context.current_task,
            "agent": context.agent_id,
            "metadata": context.metadata,
        }
        return hashlib.md5(json.dumps(data).encode()).hexdigest()

    async def process(self, context: AgentContext) -> MiddlewareResult:
        cache_key = self._get_cache_key(context)

        # 尝试从缓存获取
        cached = await self.cache.get(cache_key)
        if cached:
            # 返回缓存结果，跳过 Agent 执行
            return MiddlewareResult(
                success=True,
                agent_result=AgentResult(
                    success=True,
                    output=cached,
                    metadata={"cached": True},
                ),
                skip_agent=True,
            )

        # 执行 Agent
        result = await self.call_next(context)

        # 缓存成功的结果
        if result.success:
            await self.cache.set(
                cache_key,
                result.agent_result.output,
                ex=self.ttl,
            )

        return result
```

### 输出清洗中间件示例

```python
import html
import re

class OutputSanitizationMiddleware(BaseMiddleware):
    def __init__(self, name: str, sanitize_html: bool = True):
        super().__init__(name)
        self.sanitize_html = sanitize_html

    def _sanitize_output(self, text: str) -> str:
        """清洗输出"""
        if self.sanitize_html:
            # HTML 转义
            text = html.escape(text)

        # 移除危险模式
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
        ]

        for pattern in dangerous_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        return text

    async def process(self, context: AgentContext) -> MiddlewareResult:
        result = await self.call_next(context)

        if result.success and result.agent_result.output:
            # 清洗输出
            sanitized = self._sanitize_output(result.agent_result.output)

            result.agent_result.output = sanitized

        return result
```

### 指标收集中间件示例

```python
import time
from collections import defaultdict

class MetricsMiddleware(BaseMiddleware):
    def __init__(self, name: str, metrics_collector):
        super().__init__(name)
        self.metrics = metrics_collector
        self.counters = defaultdict(int)
        self.timers = defaultdict(list)

    async def process(self, context: AgentContext) -> MiddlewareResult:
        agent_id = context.agent_id
        start_time = time.time()

        # 执行
        result = await self.call_next(context)

        # 记录指标
        duration = time.time() - start_time

        self.counters[f"{agent_id}_total"] += 1
        self.timers[f"{agent_id}_duration"].append(duration)

        if result.success:
            self.counters[f"{agent_id}_success"] += 1
        else:
            self.counters[f"{agent_id}_error"] += 1

        # 发送到指标收集器
        await self.metrics.record(
            agent_id=agent_id,
            duration_ms=duration * 1000,
            success=result.success,
        )

        return result

    def get_stats(self):
        """获取统计信息"""
        stats = {}
        for key in self.counters:
            stats[key] = self.counters[key]

        for key, values in self.timers.items():
            if values:
                stats[f"{key}_avg"] = sum(values) / len(values)
                stats[f"{key}_max"] = max(values)
                stats[f"{key}_min"] = min(values)

        return stats
```

## 中间件管道

### 创建管道

```python
from src.middleware.pipeline import MiddlewarePipeline

pipeline = MiddlewarePipeline()

# 按顺序添加中间件
pipeline.add(LoggingMiddleware(name="logger"))
pipeline.add(AuthMiddleware(name="auth"))
pipeline.add(RateLimitMiddleware(name="rate_limit"))
```

### 中间件顺序

中间件的添加顺序很重要：

```python
# 推荐顺序：
pipeline = MiddlewarePipeline()

# 1. 日志记录（最外层）
pipeline.add(LoggingMiddleware(name="logger"))

# 2. 认证授权
pipeline.add(AuthMiddleware(name="auth"))

# 3. 输入验证
pipeline.add(ValidationMiddleware(name="validator"))

# 4. 速率限制
pipeline.add(RateLimitMiddleware(name="rate_limit"))

# 5. 缓存
pipeline.add(CacheMiddleware(name="cache"))

# 6. 业务逻辑中间件...
```

### 条件中间件

```python
class ConditionalMiddleware(BaseMiddleware):
    def __init__(self, name: str, condition, middleware):
        super().__init__(name)
        self.condition = condition
        self.middleware = middleware

    async def process(self, context: AgentContext) -> MiddlewareResult:
        # 检查条件
        if self.condition(context):
            return await self.middleware.process(context)
        else:
            # 跳过此中间件
            return await self.call_next(context)

# 使用示例
pipeline.add(
    ConditionalMiddleware(
        name="conditional_auth",
        condition=lambda ctx: ctx.metadata.get("require_auth", True),
        middleware=AuthMiddleware(name="auth"),
    )
)
```

## 高级模式

### 中间件组合

```python
class CompositeMiddleware(BaseMiddleware):
    """组合多个中间件"""

    def __init__(self, name: str, middlewares: list):
        super().__init__(name)
        self.middlewares = middlewares

    async def process(self, context: AgentContext) -> MiddlewareResult:
        # 按顺序执行所有中间件
        for middleware in self.middlewares:
            result = await middleware.process(context)

            # 如果中间件返回 skip_rest，停止执行
            if hasattr(result, 'skip_rest') and result.skip_rest:
                return result

            # 如果中间件返回 skip_agent，直接返回
            if hasattr(result, 'skip_agent') and result.skip_agent:
                return result

        return result
```

### 中间件链式调用

```python
class ChainMiddleware(BaseMiddleware):
    """链式调用多个处理函数"""

    def __init__(self, name: str, handlers: list):
        super().__init__(name)
        self.handlers = handlers

    async def process(self, context: AgentContext) -> MiddlewareResult:
        result = await self.call_next(context)

        # 在结果上链式调用处理器
        for handler in self.handlers:
            result = await handler(result, context)

        return result

# 使用示例
pipeline.add(
    ChainMiddleware(
        name="post_processors",
        handlers=[
            lambda r, ctx: self.add_metadata(r, ctx),
            lambda r, ctx: self.format_output(r, ctx),
            lambda r, ctx: self.compress_result(r, ctx),
        ],
    )
)
```

### 重试中间件

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

        # 检查错误类型
        error_type = result.agent_result.metadata.get("error_type")

        # 可重试的错误类型
        retryable_errors = ["timeout", "rate_limit", "llm_error"]

        return error_type in retryable_errors

    async def process(self, context: AgentContext) -> MiddlewareResult:
        last_result = None

        for attempt in range(self.max_attempts):
            result = await self.call_next(context)

            if not self._should_retry(result):
                return result

            last_result = result

            # 等待后重试
            if attempt < self.max_attempts - 1:
                await asyncio.sleep(self.delay * (attempt + 1))

        return last_result
```

## 中间件配置

### 从配置加载

```python
import yaml

def load_middleware_from_config(config_file: str) -> MiddlewarePipeline:
    """从配置文件加载中间件"""

    with open(config_file) as f:
        config = yaml.safe_load(f)

    pipeline = MiddlewarePipeline()

    for mw_config in config.get("middlewares", []):
        cls = get_middleware_class(mw_config["type"])
        middleware = cls(**mw_config.get("options", {}))
        pipeline.add(middleware)

    return pipeline

# config.yaml
# middlewares:
#   - type: LoggingMiddleware
#     options:
#       name: logger
#       log_level: INFO
#   - type: AuthMiddleware
#     options:
#       name: auth
#       require_auth: true
```

### 环境变量配置

```python
import os

class ConfigurableMiddleware(BaseMiddleware):
    def __init__(self, name: str):
        super().__init__(name)
        self.enabled = os.getenv(f"{name.upper()}_ENABLED", "true").lower() == "true"

    async def process(self, context: AgentContext) -> MiddlewareResult:
        if not self.enabled:
            return await self.call_next(context)

        # 正常处理
        return await self._do_process(context)

    async def _do_process(self, context: AgentContext) -> MiddlewareResult:
        # 实际处理逻辑
        return await self.call_next(context)
```

## 测试中间件

### 单元测试

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_custom_middleware():
    # 创建中间件
    middleware = MyCustomMiddleware(name="test", option="value")

    # Mock call_next
    middleware.call_next = AsyncMock(return_value=MiddlewareResult(
        success=True,
        agent_result=AgentResult(success=True, output="Test"),
    ))

    # 创建上下文
    context = AgentContext(
        agent_id="test_agent",
        user_id="test_user",
        session_id="test_session",
        current_task="Test task",
    )

    # 执行中间件
    result = await middleware.process(context)

    # 验证
    assert result.success is True
    assert middleware.call_next.called
```

### 集成测试

```python
@pytest.mark.asyncio
async def test_middleware_pipeline():
    # 创建管道
    pipeline = MiddlewarePipeline()
    pipeline.add(LoggingMiddleware(name="logger"))
    pipeline.add(ValidationMiddleware(name="validator"))

    # 创建执行器
    executor = AgentExecutor(agent_id="test", config=test_config)
    executor.set_middleware_pipeline(pipeline)

    # 执行
    context = create_test_context()
    result = await executor.execute(context)

    # 验证
    assert result.success is True
```

## 最佳实践

### 1. 保持中间件单一职责

每个中间件应该只做一件事：

```python
# ✅ 好的设计
class AuthMiddleware(BaseMiddleware):
    async def process(self, context: AgentContext) -> MiddlewareResult:
        # 只处理认证
        return await self.call_next(context)

class RateLimitMiddleware(BaseMiddleware):
    async def process(self, context: AgentContext) -> MiddlewareResult:
        # 只处理速率限制
        return await self.call_next(context)

# ❌ 不好的设计
class AuthAndRateLimitMiddleware(BaseMiddleware):
    async def process(self, context: AgentContext) -> MiddlewareResult:
        # 同时处理认证和速率限制
        # 违反单一职责原则
        return await self.call_next(context)
```

### 2. 正确处理错误

```python
class SafeMiddleware(BaseMiddleware):
    async def process(self, context: AgentContext) -> MiddlewareResult:
        try:
            return await self.call_next(context)
        except Exception as e:
            # 返回错误结果而不是抛出异常
            return MiddlewareResult(
                success=False,
                agent_result=AgentResult(
                    success=False,
                    output="",
                    error=str(e),
                    metadata={"error_type": type(e).__name__},
                ),
            )
```

### 3. 避免修改原始上下文

```python
class GoodMiddleware(BaseMiddleware):
    async def process(self, context: AgentContext) -> MiddlewareResult:
        # 创建副本而不是修改原始 context
        modified_context = AgentContext(
            agent_id=context.agent_id,
            user_id=context.user_id,
            session_id=context.session_id,
            current_task=context.current_task,
            metadata=dict(context.metadata),  # 复制 metadata
        )

        # 修改副本
        modified_context.metadata["processed"] = True

        return await self.call_next(modified_context)
```

### 4. 使用中间件选项

```python
class FlexibleMiddleware(BaseMiddleware):
    def __init__(self, name: str, **options):
        super().__init__(name)
        self.option1 = options.get("option1", "default1")
        self.option2 = options.get("option2", "default2")

    async def process(self, context: AgentContext) -> MiddlewareResult:
        # 使用配置的选项
        if self.option1:
            # ...
        if self.option2:
            # ...

        return await self.call_next(context)
```

## 相关文档

- [系统架构](architecture.md) - 中间件在整体架构中的位置
- [中间件开发指南](../guides/middleware.md) - 详细的开发教程
- [Agent 生命周期](lifecycle.md) - 中间件与 Agent 执行的交互

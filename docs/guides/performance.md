# 性能优化指南

本指南介绍如何优化 Qingyu Backend AI 的性能。

## 性能基线

根据 Phase 6.2 性能测试，系统各组件的性能基线：

| 组件 | 操作 | 目标 | 实际 |
|------|------|------|------|
| SessionManager | create_session | < 5ms | ~1.66ms ✅ |
| EventBus | publish | < 1ms | ~0.99ms ✅ |
| Middleware | 10层链 | < 5ms | ~1.78ms ✅ |
| Executor | 基本执行 | < 50ms | ~1.02ms ✅ |

## 优化策略

### 1. 连接池优化

```python
import redis
from redis.connection import ConnectionPool

# ❌ 不好：每次创建新连接
def bad_redis_client():
    return redis.Redis(host='localhost', port=6379)

# ✅ 好：使用连接池
pool = ConnectionPool(
    host='localhost',
    port=6379,
    max_connections=50,
    min_idle_connections=10,
)

redis_client = redis.Redis(connection_pool=pool)

# 在 SessionManager 中使用
session_manager = SessionManager(
    conn=redis_client,
    ttl=3600,
)
```

### 2. 异步并发

```python
import asyncio

# ❌ 不好：顺序执行
async def bad_concurrent():
    results = []
    for context in contexts:
        result = await executor.execute(context)
        results.append(result)
    return results

# ✅ 好：并发执行
async def good_concurrent():
    tasks = [
        executor.execute(context)
        for context in contexts
    ]
    results = await asyncio.gather(*tasks)
    return results

# ✅ 更好：控制并发数
async def better_concurrent(contexts, max_concurrent=10):
    semaphore = asyncio.Semaphore(max_concurrent)

    async def execute_with_semaphore(context):
        async with semaphore:
            return await executor.execute(context)

    tasks = [
        execute_with_semaphore(context)
        for context in contexts
    ]
    return await asyncio.gather(*tasks)
```

### 3. 缓存策略

```python
from functools import lru_cache
import hashlib

class CacheOptimizedExecutor(AgentExecutor):
    def __init__(self, *args, cache_size=1000, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = {}
        self.cache_size = cache_size

    def _get_cache_key(self, context: AgentContext) -> str:
        """生成缓存键"""
        data = f"{context.agent_id}:{context.current_task}"
        return hashlib.md5(data.encode()).hexdigest()

    async def execute(self, context: AgentContext) -> AgentResult:
        """带缓存的执行"""
        cache_key = self._get_cache_key(context)

        # 检查缓存
        if cache_key in self.cache:
            return self.cache[cache_key]

        # 执行
        result = await super().execute(context)

        # 缓存成功的结果
        if result.success:
            # 限制缓存大小
            if len(self.cache) >= self.cache_size:
                # 删除最旧的条目
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]

            self.cache[cache_key] = result

        return result
```

### 4. 批量操作

```python
class BatchOptimizer:
    async def execute_batch_optimized(
        self,
        contexts: List[AgentContext],
        batch_size: int = 10,
    ) -> List[AgentResult]:
        """批量优化执行"""
        results = []

        for i in range(0, len(contexts), batch_size):
            batch = contexts[i:i + batch_size]

            # 并发执行批次
            batch_results = await asyncio.gather(*[
                executor.execute(context)
                for context in batch
            ])

            results.extend(batch_results)

        return results
```

### 5. 内存优化

```python
import sys

class MemoryOptimizedSessionManager(SessionManager):
    def __init__(self, *args, max_memory_mb=100, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_memory = max_memory_mb * 1024 * 1024

    async def create_session(self, *args, **kwargs):
        """创建会话时检查内存"""
        # 检查内存使用
        if self._get_memory_usage() > self.max_memory:
            # 清理过期会话
            await self.cleanup_expired_sessions()

        return await super().create_session(*args, **kwargs)

    def _get_memory_usage(self) -> int:
        """获取内存使用量"""
        import psutil
        process = psutil.Process()
        return process.memory_info().rss
```

## 中间件性能

### 轻量级中间件

```python
# ✅ 好：轻量级中间件
class FastLoggingMiddleware(BaseMiddleware):
    async def process(self, context: AgentContext) -> MiddlewareResult:
        # 快速记录
        print(f"[{context.agent_id}] Processing")

        # 继续执行
        return await self.call_next(context)

# ❌ 不好：重量级中间件
class SlowLoggingMiddleware(BaseMiddleware):
    async def process(self, context: AgentContext) -> MiddlewareResult:
        # 昂贵的操作
        await self._log_to_database(context)
        await self._send_analytics(context)

        return await self.call_next(context)
```

### 中间件短路

```python
class ShortCircuitMiddleware(BaseMiddleware):
    async def process(self, context: AgentContext) -> MiddlewareResult:
        # 快速检查
        if not self._is_allowed(context):
            # 立即返回，不执行后续中间件和 Agent
            return MiddlewareResult(
                success=False,
                agent_result=AgentResult(
                    success=False,
                    output="",
                    error="Not allowed",
                ),
                skip_rest=True,  # 关键：跳过所有后续处理
            )

        return await self.call_next(context)
```

## Agent 优化

### 系统提示词优化

```python
# ❌ 不好：过长的系统提示词
long_prompt = """
You are a helpful assistant with extensive knowledge in many fields.
Please provide detailed and comprehensive answers to all questions.
Always include examples, explanations, and additional context.
Make sure to cover all possible angles and perspectives...
"""  # 500+ tokens

# ✅ 好：简洁的系统提示词
short_prompt = """
You are a helpful assistant.
Be concise and accurate.
"""  # ~20 tokens

config = AgentConfig(
    name="efficient_agent",
    description="Efficient agent",
    system_prompt=short_prompt,
)
```

### Token 优化

```python
class TokenOptimizedExecutor(AgentExecutor):
    async def execute(self, context: AgentContext) -> AgentResult:
        """优化 token 使用"""
        # 截断过长的输入
        max_input_tokens = 3000  # 约 2250 字符

        if len(context.current_task) > max_input_tokens:
            # 智能截断（保留重要部分）
            context.current_task = self._smart_truncate(
                context.current_task,
                max_input_tokens,
            )

        return await super().execute(context)

    def _smart_truncate(self, text: str, max_length: int) -> str:
        """智能截断文本"""
        # 保留开头和结尾
        if len(text) <= max_length:
            return text

        keep_start = max_length // 2
        keep_end = max_length - keep_start

        return (
            text[:keep_start] +
            "... [truncated] ..." +
            text[-keep_end:]
        )
```

## 监控和分析

### 性能监控

```python
import time
from collections import defaultdict

class PerformanceMonitor:
    def __init__(self):
        self.metrics = defaultdict(list)
        self.slow_queries = []

    async def monitor_execution(
        self,
        agent_id: str,
        execute_func: Callable,
    ) -> AgentResult:
        """监控执行性能"""
        start_time = time.time()

        # 执行
        result = await execute_func()

        # 记录指标
        duration = time.time() - start_time
        self.metrics[agent_id].append(duration)

        # 检查慢查询
        threshold = 2.0  # 2秒
        if duration > threshold:
            self.slow_queries.append({
                "agent_id": agent_id,
                "duration": duration,
                "timestamp": datetime.now(),
            })

        return result

    def get_stats(self) -> dict:
        """获取统计信息"""
        stats = {}

        for agent_id, durations in self.metrics.items():
            stats[agent_id] = {
                "avg": sum(durations) / len(durations),
                "min": min(durations),
                "max": max(durations),
                "count": len(durations),
            }

        return stats
```

### 性能分析工具

```python
import cProfile
import pstats
from io import StringIO

def profile_executor():
    """性能分析"""
    profiler = cProfile.Profile()

    # 开始分析
    profiler.enable()

    # 执行代码
    asyncio.run(main())

    # 停止分析
    profiler.disable()

    # 输出结果
    s = StringIO()
    stats = pstats.Stats(profiler, stream=s)
    stats.strip_dirs()
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # 打印前 20 个

    print(s.getvalue())
```

## 性能测试

### 基准测试

```python
import pytest
import asyncio

@pytest.mark.asyncio
@pytest.mark.benchmark(group="executor")
async def test_executor_performance(benchmark):
    """测试 Executor 性能"""

    executor = AgentExecutor(
        agent_id="test_agent",
        config=AgentConfig(
            name="test_agent",
            description="Test agent",
            model="gpt-3.5-turbo",
        ),
    )

    context = AgentContext(
        agent_id="test_agent",
        user_id="test_user",
        session_id="test_session",
        current_task="Test",
    )

    # 基准测试
    result = benchmark(asyncio.run, executor.execute(context))

    assert result.success
```

### 负载测试

```python
async def load_test():
    """负载测试"""
    executor = AgentExecutor(...)

    # 创建大量并发请求
    contexts = [
        AgentContext(
            agent_id="test_agent",
            user_id=f"user_{i}",
            session_id=f"sess_{i}",
            current_task="Test",
        )
        for i in range(1000)
    ]

    # 测量吞吐量
    start_time = time.time()

    results = await asyncio.gather(*[
        executor.execute(context)
        for context in contexts
    ])

    duration = time.time() - start_time

    print(f"Processed {len(results)} requests in {duration:.2f}s")
    print(f"Throughput: {len(results) / duration:.2f} req/s")
```

## 最佳实践

### 1. 避免阻塞操作

```python
# ❌ 不好：阻塞事件循环
async def bad_blocking():
    # 同步 I/O 阻塞
    with open("large_file.txt") as f:
        data = f.read()  # 阻塞

# ✅ 好：使用异步 I/O
async def good_async():
    # 使用 aiofiles
    from aiofiles import open
    async with open("large_file.txt") as f:
        data = await f.read()
```

### 2. 使用连接池

```python
# ✅ 好：HTTP 连接池
import aiohttp

async with aiohttp.ClientSession(
    connector=aiohttp.TCPConnector(
        limit=100,  # 最大连接数
        limit_per_host=10,  # 每个主机的连接数
    ),
) as session:
    # 复用连接
    for url in urls:
        async with session.get(url) as response:
            data = await response.text()
```

### 3. 预分配资源

```python
# ✅ 好：预分配
async def preallocate_resources():
    # 预创建连接池
    pool = ConnectionPool(max_connections=50)

    # 预创建会话
    sessions = [
        session_manager.create_session(f"user_{i}", "agent")
        for i in range(100)
    ]
    await asyncio.gather(*sessions)

    return pool
```

### 4. 使用适当的数据结构

```python
# ❌ 不好：列表查找 O(n)
def bad_lookup(items, key):
    return key in items  # O(n)

# ✅ 好：集合查找 O(1)
def good_lookup(items, key):
    return key in set(items)  # O(1)
```

## 性能检查清单

### 部署前检查

- [ ] 使用连接池（Redis、HTTP）
- [ ] 启用并发处理
- [ ] 实施缓存策略
- [ ] 优化数据库查询
- [ ] 避免阻塞操作
- [ ] 监控资源使用
- [ ] 设置超时时间
- [ ] 实施速率限制

### 运行时监控

- [ ] CPU 使用率 < 80%
- [ ] 内存使用 < 80%
- [ ] 响应时间 < 目标值
- [ ] 错误率 < 1%
- [ ] 吞吐量 > 目标值

## 相关文档

- [Phase 6.2 性能测试报告](../reports/phase-6-completion-report.md) - 性能基线
- [中间件开发](middleware.md) - 中间件性能
- [错误处理](error-handling.md) - 错误恢复

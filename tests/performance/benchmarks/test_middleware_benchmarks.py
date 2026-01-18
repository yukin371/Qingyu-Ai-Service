"""
Middleware Performance Benchmarks

Performance targets (from Phase 6 plan):
- Single middleware: < 1ms per layer
- Full chain: < 5ms for 3-5 middlewares
"""

import asyncio
import pytest

from src.agent_runtime.orchestration.middleware.base import (
    AgentMiddleware,
    MiddlewarePipeline,
    MiddlewareResult,
)
from src.common.types.agent_types import AgentContext, AgentResult


# =============================================================================
# Test Middlewares
# =============================================================================

class NoOpMiddleware(AgentMiddleware):
    """无操作中间件 - 用于基准测试"""

    def __init__(self, name: str = "noop", order: int = 100):
        super().__init__(name=name, order=order)

    async def process(self, context, next_call):
        # 直接调用下一个
        return await next_call()


class LoggingMiddleware(AgentMiddleware):
    """模拟日志中间件 - 添加少量处理"""

    def __init__(self, name: str = "logging", order: int = 100):
        super().__init__(name=name, order=order)

    async def process(self, context, next_call):
        # 模拟日志记录
        context.metadata[f"{self.name}_start"] = True
        result = await next_call()
        context.metadata[f"{self.name}_end"] = True
        return result


class AuthMiddleware(AgentMiddleware):
    """模拟认证中间件 - 执行简单检查"""

    def __init__(self, name: str = "auth", order: int = 100):
        super().__init__(name=name, order=order)

    async def process(self, context, next_call):
        # 模拟认证检查
        if not context.user_id:
            return MiddlewareResult(success=False, error="No user_id")
        return await next_call()


# =============================================================================
# Benchmarks
# =============================================================================

class TestMiddlewareBenchmarks:
    """Middleware 性能基准测试"""

    @pytest.fixture
    def agent_context(self):
        """创建测试用的 AgentContext"""
        return AgentContext(
            agent_id="test_agent",
            user_id="test_user",
            session_id="test_session",
            current_task="Test task",
        )

    @pytest.fixture
    def mock_handler(self):
        """模拟处理器函数"""
        async def handler(context):
            return MiddlewareResult(
                success=True,
                agent_result=AgentResult(
                    success=True,
                    output="Test result",
                ),
            )
        return handler

    # -------------------------------------------------------------------------
    # Pipeline Management Benchmarks
    # -------------------------------------------------------------------------

    def test_bench_add_middleware(self, benchmark):
        """基准测试: 添加中间件"""

        def add_middleware():
            pipeline = MiddlewarePipeline()
            middleware = NoOpMiddleware("test_middleware")
            pipeline.add(middleware)
            return pipeline

        pipeline = benchmark(add_middleware)
        assert len(pipeline) == 1

    def test_bench_add_multiple_middlewares(self, benchmark):
        """基准测试: 批量添加中间件"""

        def add_multiple():
            pipeline = MiddlewarePipeline()
            for i in range(5):
                middleware = NoOpMiddleware(f"middleware_{i}", order=i * 10)
                pipeline.add(middleware)
            return pipeline

        pipeline = benchmark(add_multiple)
        assert len(pipeline) == 5

    def test_bench_remove_middleware(self, benchmark):
        """基准测试: 移除中间件"""

        def setup_and_remove():
            pipeline = MiddlewarePipeline()
            middleware = NoOpMiddleware("test_middleware")
            pipeline.add(middleware)
            pipeline.remove("test_middleware")
            return pipeline

        pipeline = benchmark(setup_and_remove)
        assert len(pipeline) == 0

    def test_bench_get_middleware(self, benchmark):
        """基准测试: 获取中间件"""

        def setup_and_get():
            pipeline = MiddlewarePipeline()
            middleware = NoOpMiddleware("test_middleware")
            pipeline.add(middleware)
            return pipeline.get("test_middleware")

        result = benchmark(setup_and_get)
        assert result is not None
        assert result.name == "test_middleware"

    def test_bench_enable_disable_middleware(self, benchmark):
        """基准测试: 启用/禁用中间件"""

        def setup_and_toggle():
            pipeline = MiddlewarePipeline()
            middleware = NoOpMiddleware("test_middleware")
            middleware.disable()
            middleware.enable()
            return middleware

        middleware = benchmark(setup_and_toggle)
        assert middleware.enabled is True

    # -------------------------------------------------------------------------
    # Single Middleware Execution
    # -------------------------------------------------------------------------

    def test_bench_single_noop_middleware(self, benchmark, agent_context, mock_handler):
        """基准测试: 单个 NoOp 中间件执行 - 目标 < 1ms"""

        async def execute():
            pipeline = MiddlewarePipeline()
            pipeline.add(NoOpMiddleware("noop"))
            return await pipeline.execute(agent_context, mock_handler)

        result = benchmark(lambda: asyncio.run(execute()))
        assert result.success is True

    def test_bench_single_logging_middleware(self, benchmark, agent_context, mock_handler):
        """基准测试: 单个 Logging 中间件执行"""

        async def execute():
            pipeline = MiddlewarePipeline()
            pipeline.add(LoggingMiddleware("logging"))
            return await pipeline.execute(agent_context, mock_handler)

        result = benchmark(lambda: asyncio.run(execute()))
        assert result.success is True
        assert agent_context.metadata.get("logging_start") is True

    def test_bench_single_auth_middleware(self, benchmark, agent_context, mock_handler):
        """基准测试: 单个 Auth 中间件执行"""

        async def execute():
            pipeline = MiddlewarePipeline()
            pipeline.add(AuthMiddleware("auth"))
            return await pipeline.execute(agent_context, mock_handler)

        result = benchmark(lambda: asyncio.run(execute()))
        assert result.success is True

    # -------------------------------------------------------------------------
    # Chain Execution Benchmarks
    # -------------------------------------------------------------------------

    def test_bench_chain_3_middlewares(self, benchmark, agent_context, mock_handler):
        """基准测试: 3 个中间件链执行 - 目标 < 5ms"""

        async def execute():
            pipeline = MiddlewarePipeline()
            pipeline.add(AuthMiddleware("auth", order=10))
            pipeline.add(LoggingMiddleware("logging", order=20))
            pipeline.add(NoOpMiddleware("noop", order=30))
            return await pipeline.execute(agent_context, mock_handler)

        result = benchmark(lambda: asyncio.run(execute()))
        assert result.success is True

    def test_bench_chain_5_middlewares(self, benchmark, agent_context, mock_handler):
        """基准测试: 5 个中间件链执行"""

        async def execute():
            pipeline = MiddlewarePipeline()
            for i in range(5):
                pipeline.add(NoOpMiddleware(f"noop_{i}", order=i * 10))
            return await pipeline.execute(agent_context, mock_handler)

        result = benchmark(lambda: asyncio.run(execute()))
        assert result.success is True

    def test_bench_chain_10_middlewares(self, benchmark, agent_context, mock_handler):
        """基准测试: 10 个中间件链执行"""

        async def execute():
            pipeline = MiddlewarePipeline()
            for i in range(10):
                pipeline.add(NoOpMiddleware(f"noop_{i}", order=i * 10))
            return await pipeline.execute(agent_context, mock_handler)

        result = benchmark(lambda: asyncio.run(execute()))
        assert result.success is True

    # -------------------------------------------------------------------------
    # Middleware Ordering Benchmarks
    # -------------------------------------------------------------------------

    def test_bench_middleware_sorting(self, benchmark):
        """基准测试: 中间件排序"""

        def setup_and_sort():
            pipeline = MiddlewarePipeline()
            # 添加乱序的中间件
            pipeline.add(NoOpMiddleware("m3", order=30))
            pipeline.add(NoOpMiddleware("m1", order=10))
            pipeline.add(NoOpMiddleware("m5", order=50))
            pipeline.add(NoOpMiddleware("m2", order=20))
            pipeline.add(NoOpMiddleware("m4", order=40))
            # 访问 middlewares 属性会触发排序
            return pipeline.middlewares

        middlewares = benchmark(setup_and_sort)
        assert len(middlewares) == 5
        # 验证排序
        assert middlewares[0].name == "m1"
        assert middlewares[4].name == "m5"

    # -------------------------------------------------------------------------
    # Mixed Middleware Types
    # -------------------------------------------------------------------------

    def test_bench_mixed_middleware_chain(self, benchmark, agent_context, mock_handler):
        """基准测试: 混合类型中间件链"""

        async def execute():
            pipeline = MiddlewarePipeline()
            pipeline.add(AuthMiddleware("auth", order=10))
            pipeline.add(LoggingMiddleware("logging", order=20))
            pipeline.add(NoOpMiddleware("noop", order=30))
            pipeline.add(LoggingMiddleware("logging2", order=40))
            return await pipeline.execute(agent_context, mock_handler)

        result = benchmark(lambda: asyncio.run(execute()))
        assert result.success is True

    # -------------------------------------------------------------------------
    # Error Handling
    # -------------------------------------------------------------------------

    def test_bench_middleware_chain_error(self, benchmark, agent_context):
        """基准测试: 中间件链错误处理"""

        async def failing_handler(context):
            return MiddlewareResult(success=False, error="Handler failed")

        async def execute():
            pipeline = MiddlewarePipeline()
            pipeline.add(NoOpMiddleware("noop", order=10))
            pipeline.add(NoOpMiddleware("noop2", order=20))
            return await pipeline.execute(agent_context, failing_handler)

        result = benchmark(lambda: asyncio.run(execute()))
        assert result.success is False

    # -------------------------------------------------------------------------
    # Property Access
    # -------------------------------------------------------------------------

    def test_bench_middlewares_property(self, benchmark):
        """基准测试: middlewares 属性访问（过滤和排序）"""

        def setup_and_access():
            pipeline = MiddlewarePipeline()
            for i in range(10):
                m = NoOpMiddleware(f"m{i}", order=i * 10)
                # 禁用一半
                if i % 2 == 0:
                    m.disable()
                pipeline.add(m)
            # 访问属性会过滤和排序
            return pipeline.middlewares

        middlewares = benchmark(setup_and_access)
        assert len(middlewares) == 5  # 只启用了一半

    def test_bench_pipeline_repr(self, benchmark):
        """基准测试: Pipeline __repr__"""

        def setup_and_repr():
            pipeline = MiddlewarePipeline()
            for i in range(5):
                m = NoOpMiddleware(f"m{i}")
                pipeline.add(m)
            return repr(pipeline)

        result = benchmark(setup_and_repr)
        assert "MiddlewarePipeline" in result
        assert "middlewares=5" in result

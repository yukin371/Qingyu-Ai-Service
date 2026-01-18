"""
AgentExecutor Performance Benchmarks

Performance targets (from Phase 6 plan):
- Basic execution: < 50ms (without LLM calls)
- State retrieval: < 0.1ms
- Reset: < 0.1ms
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock

from src.agent_runtime.orchestration.executor import (
    AgentExecutor,
    ExecutionConfig,
    ExecutionResult,
)
from src.agent_runtime.orchestration.middleware.base import (
    AgentMiddleware,
    MiddlewarePipeline,
    MiddlewareResult,
)
from src.common.types.agent_types import (
    AgentConfig,
    AgentContext,
    AgentResult,
    AgentStatus,
)


# =============================================================================
# Test Middleware
# =============================================================================

class BenchmarkMiddleware(AgentMiddleware):
    """基准测试中间件"""

    def __init__(self, name: str = "benchmark", order: int = 100):
        super().__init__(name=name, order=order)

    async def process(self, context, next_call):
        context.metadata[f"{self.name}_called"] = True
        return await next_call()


# =============================================================================
# Benchmarks
# =============================================================================

class TestExecutorBenchmarks:
    """AgentExecutor 性能基准测试"""

    @pytest.fixture
    def agent_config(self):
        """创建测试用 AgentConfig"""
        return AgentConfig(
            name="test_agent",
            description="A test agent for benchmarking",
            model="gpt-3.5-turbo",
            temperature=0.7,
        )

    @pytest.fixture
    def agent_context(self):
        """创建测试用 AgentContext"""
        return AgentContext(
            agent_id="test_agent",
            user_id="test_user",
            session_id="test_session",
            current_task="Test task for benchmarking",
        )

    @pytest.fixture
    def executor(self, agent_config):
        """创建基础 Executor 实例"""
        return AgentExecutor(
            agent_id="test_agent",
            config=agent_config,
        )

    # -------------------------------------------------------------------------
    # Executor Creation Benchmarks
    # -------------------------------------------------------------------------

    def test_bench_create_executor(self, benchmark, agent_config):
        """基准测试: 创建 Executor"""

        def create_executor():
            return AgentExecutor(
                agent_id="test_agent",
                config=agent_config,
            )

        result = benchmark(create_executor)
        assert result.agent_id == "test_agent"

    def test_bench_create_executor_with_tools(self, benchmark, agent_config):
        """基准测试: 创建带 Tools 的 Executor"""

        mock_tool = Mock()
        mock_tool.name = "test_tool"

        def create_executor():
            return AgentExecutor(
                agent_id="test_agent",
                config=agent_config,
                tools=[mock_tool],
            )

        result = benchmark(create_executor)
        assert len(result.tools) == 1

    def test_bench_create_executor_with_middleware(self, benchmark, agent_config):
        """基准测试: 创建带 Middleware 的 Executor"""

        pipeline = MiddlewarePipeline()
        pipeline.add(BenchmarkMiddleware("m1", order=10))
        pipeline.add(BenchmarkMiddleware("m2", order=20))

        def create_executor():
            return AgentExecutor(
                agent_id="test_agent",
                config=agent_config,
                middleware_pipeline=pipeline,
            )

        result = benchmark(create_executor)
        assert len(result.middleware_pipeline.middlewares) == 2

    # -------------------------------------------------------------------------
    # Basic Execution Benchmarks
    # -------------------------------------------------------------------------

    def test_bench_basic_execute(self, benchmark, executor, agent_context):
        """基准测试: 基本执行 - 目标 < 50ms"""

        async def execute():
            executor.reset()
            return await executor.execute(agent_context)

        result = benchmark(lambda: asyncio.run(execute()))
        assert result.success is True

    def test_bench_execute_with_custom_config(self, benchmark, executor, agent_context):
        """基准测试: 使用自定义配置执行"""

        config = ExecutionConfig(
            timeout=30,
            max_retries=1,
            enable_middleware=False,
        )

        async def execute():
            executor.reset()
            return await executor.execute(agent_context, config)

        result = benchmark(lambda: asyncio.run(execute()))
        assert result.success is True

    def test_bench_execute_with_middleware(self, benchmark, agent_config, agent_context):
        """基准测试: 带 Middleware 的执行"""

        pipeline = MiddlewarePipeline()
        pipeline.add(BenchmarkMiddleware("auth", order=10))
        pipeline.add(BenchmarkMiddleware("logging", order=20))

        executor = AgentExecutor(
            agent_id="test_agent",
            config=agent_config,
            middleware_pipeline=pipeline,
        )

        async def execute():
            executor.reset()
            return await executor.execute(agent_context)

        result = benchmark(lambda: asyncio.run(execute()))
        assert result.success is True
        assert agent_context.metadata.get("auth_called") is True

    # -------------------------------------------------------------------------
    # Streaming Execution Benchmarks
    # -------------------------------------------------------------------------

    def test_bench_execute_stream(self, benchmark, executor, agent_context):
        """基准测试: 流式执行"""

        async def execute_stream():
            executor.reset()
            tokens = []
            async for token in executor.execute_stream(agent_context):
                tokens.append(token)
            return len(tokens)

        token_count = benchmark(lambda: asyncio.run(execute_stream()))
        assert token_count > 0

    def test_bench_execute_stream_with_config(self, benchmark, executor, agent_context):
        """基准测试: 流式执行（带配置）"""

        config = ExecutionConfig(
            enable_streaming=True,
            timeout=30,
        )

        async def execute_stream():
            executor.reset()
            tokens = []
            async for token in executor.execute_stream(agent_context, config):
                tokens.append(token)
            return len(tokens)

        token_count = benchmark(lambda: asyncio.run(execute_stream()))
        assert token_count > 0

    # -------------------------------------------------------------------------
    # State Management Benchmarks
    # -------------------------------------------------------------------------

    def test_bench_get_state(self, benchmark, executor):
        """基准测试: 获取状态 - 目标 < 0.1ms"""

        def get_state():
            return executor.get_state()

        state = benchmark(get_state)
        assert state.agent_id == "test_agent"
        assert state.status == AgentStatus.IDLE

    def test_bench_get_state_after_execution(self, benchmark, executor, agent_context):
        """基准测试: 执行后获取状态"""

        async def setup():
            await executor.execute(agent_context)

        asyncio.run(setup())

        def get_state():
            return executor.get_state()

        state = benchmark(get_state)
        assert state.status == AgentStatus.COMPLETED

    def test_bench_reset(self, benchmark, executor):
        """基准测试: 重置状态 - 目标 < 0.1ms"""

        # 先设置一些状态
        async def setup():
            executor._status = AgentStatus.ACTING
            executor._current_task = "test_task"

        asyncio.run(setup())

        def reset_executor():
            executor.reset()
            return executor.status

        status = benchmark(reset_executor)
        assert status == AgentStatus.IDLE

    # -------------------------------------------------------------------------
    # Property Access Benchmarks
    # -------------------------------------------------------------------------

    def test_bench_status_property(self, benchmark, executor):
        """基准测试: 访问 status 属性"""

        def get_status():
            return executor.status

        status = benchmark(get_status)
        assert status == AgentStatus.IDLE

    def test_bench_executor_repr(self, benchmark, executor):
        """基准测试: Executor __repr__"""

        def get_repr():
            return repr(executor)

        result = benchmark(get_repr)
        assert "AgentExecutor" in result
        assert "test_agent" in result

    # -------------------------------------------------------------------------
    # Retry Logic Benchmarks
    # -------------------------------------------------------------------------

    def test_bench_execute_without_retry(self, benchmark, executor, agent_context):
        """基准测试: 执行（无重试）"""

        config = ExecutionConfig(
            max_retries=0,
            retry_on_failure=False,
        )

        async def execute():
            executor.reset()
            return await executor.execute(agent_context, config)

        result = benchmark(lambda: asyncio.run(execute()))
        assert result.success is True

    def test_bench_execute_with_retry_config(self, benchmark, executor, agent_context):
        """基准测试: 执行（带重试配置）"""

        config = ExecutionConfig(
            max_retries=3,
            retry_on_failure=True,
        )

        async def execute():
            executor.reset()
            return await executor.execute(agent_context, config)

        result = benchmark(lambda: asyncio.run(execute()))
        assert result.success is True

    # -------------------------------------------------------------------------
    # Memory Integration Benchmarks
    # -------------------------------------------------------------------------

    def test_bench_execute_with_memory(self, benchmark, agent_config, agent_context):
        """基准测试: 带 Memory 的执行"""

        # 创建 mock memory
        mock_memory = Mock()
        mock_memory.load_memory_variables = AsyncMock(return_value={"history": []})
        mock_memory.save_context = AsyncMock()

        executor = AgentExecutor(
            agent_id="test_agent",
            config=agent_config,
            memory=mock_memory,
        )

        async def execute():
            executor.reset()
            return await executor.execute(agent_context)

        result = benchmark(lambda: asyncio.run(execute()))
        assert result.success is True

    # -------------------------------------------------------------------------
    # Complex Scenarios
    # -------------------------------------------------------------------------

    def test_bench_full_featured_executor(self, benchmark, agent_config, agent_context):
        """基准测试: 完整功能 Executor 执行"""

        # 创建 mock memory
        mock_memory = Mock()
        mock_memory.load_memory_variables = AsyncMock(return_value={})
        mock_memory.save_context = AsyncMock()

        # 创建 middleware pipeline
        pipeline = MiddlewarePipeline()
        pipeline.add(BenchmarkMiddleware("auth", order=10))
        pipeline.add(BenchmarkMiddleware("logging", order=20))

        # 创建 mock tool
        mock_tool = Mock()
        mock_tool.name = "calculator"

        executor = AgentExecutor(
            agent_id="full_agent",
            config=agent_config,
            memory=mock_memory,
            tools=[mock_tool],
            middleware_pipeline=pipeline,
        )

        config = ExecutionConfig(
            timeout=60,
            max_retries=2,
            enable_middleware=True,
        )

        async def execute():
            executor.reset()
            return await executor.execute(agent_context, config)

        result = benchmark(lambda: asyncio.run(execute()))
        assert result.success is True

    # -------------------------------------------------------------------------
    # Concurrent Execution
    # -------------------------------------------------------------------------

    def test_bench_concurrent_executions(self, benchmark, agent_config, agent_context):
        """基准测试: 并发执行多个 Executor"""

        async def execute_concurrent():
            executors = [
                AgentExecutor(
                    agent_id=f"agent_{i}",
                    config=agent_config,
                )
                for i in range(5)
            ]

            tasks = [
                exec.execute(agent_context)
                for exec in executors
            ]
            results = await asyncio.gather(*tasks)
            return sum(1 for r in results if r.success)

        success_count = benchmark(lambda: asyncio.run(execute_concurrent()))
        assert success_count == 5

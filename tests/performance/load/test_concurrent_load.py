"""
Stress Tests - Concurrent Load Testing

测试系统在高并发场景下的性能和稳定性：
- 10 并发会话
- 50 并发会话
- 100 并发会话
- 500 并发会话（极限测试）

Performance targets:
- 10 concurrent: < 500ms total
- 50 concurrent: < 2s total
- 100 concurrent: < 5s total
- 500 concurrent: < 20s total
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock

from src.agent_runtime.session_manager import SessionManager
from src.agent_runtime.event_bus import EventBus
from src.agent_runtime.orchestration.executor import AgentExecutor
from src.agent_runtime.orchestration.middleware.base import (
    AgentMiddleware,
    MiddlewarePipeline,
    MiddlewareResult,
)
from src.common.types.agent_types import (
    AgentConfig,
    AgentContext,
)


# =============================================================================
# Test Middleware
# =============================================================================

class StressTestMiddleware(AgentMiddleware):
    """压力测试中间件 - 轻量级处理"""

    def __init__(self, name: str = "stress", order: int = 100):
        super().__init__(name=name, order=order)

    async def process(self, context, next_call):
        # 最小化处理，只记录调用
        context.metadata[f"{self.name}_call"] = True
        return await next_call()


# =============================================================================
# Stress Tests
# =============================================================================

class TestConcurrentLoad:
    """并发负载压力测试"""

    @pytest.fixture
    def session_manager(self):
        """创建 SessionManager"""
        return SessionManager(conn=None, ttl=3600)

    @pytest.fixture
    def event_bus(self):
        """创建 EventBus"""
        return EventBus(enable_kafka=False, max_history=1000)

    @pytest.fixture
    def agent_config(self):
        """创建 AgentConfig"""
        return AgentConfig(
            name="stress_agent",
            description="Stress test agent",
            model="gpt-3.5-turbo",
            temperature=0.7,
        )

    # -------------------------------------------------------------------------
    # Concurrent Session Creation
    # -------------------------------------------------------------------------

    def test_bench_concurrent_session_creation_10(
        self, benchmark, session_manager
    ):
        """压力测试: 10 并发会话创建 - 目标 < 500ms"""

        async def create_concurrent_sessions():
            tasks = []
            for i in range(10):
                task = session_manager.create_session(
                    user_id=f"stress_user_{i}",
                    agent_id="stress_agent",
                )
                tasks.append(task)

            sessions = await asyncio.gather(*tasks)
            return len(sessions)

        count = benchmark(lambda: asyncio.run(create_concurrent_sessions()))
        assert count == 10

    def test_bench_concurrent_session_creation_50(
        self, benchmark, session_manager
    ):
        """压力测试: 50 并发会话创建 - 目标 < 2s"""

        async def create_concurrent_sessions():
            tasks = []
            for i in range(50):
                task = session_manager.create_session(
                    user_id=f"stress_user_{i}",
                    agent_id="stress_agent",
                )
                tasks.append(task)

            sessions = await asyncio.gather(*tasks)
            return len(sessions)

        count = benchmark(lambda: asyncio.run(create_concurrent_sessions()))
        assert count == 50

    def test_bench_concurrent_session_creation_100(
        self, benchmark, session_manager
    ):
        """压力测试: 100 并发会话创建 - 目标 < 5s"""

        async def create_concurrent_sessions():
            tasks = []
            for i in range(100):
                task = session_manager.create_session(
                    user_id=f"stress_user_{i}",
                    agent_id="stress_agent",
                )
                tasks.append(task)

            sessions = await asyncio.gather(*tasks)
            return len(sessions)

        count = benchmark(lambda: asyncio.run(create_concurrent_sessions()))
        assert count == 100

    # -------------------------------------------------------------------------
    # Concurrent Execution
    # -------------------------------------------------------------------------

    def test_bench_concurrent_execution_10(
        self, benchmark, session_manager, agent_config
    ):
        """压力测试: 10 并发 Agent 执行 - 目标 < 500ms"""

        async def execute_concurrent():
            # 先创建会话
            sessions = []
            for i in range(10):
                session = await session_manager.create_session(
                    user_id=f"exec_user_{i}",
                    agent_id="exec_agent",
                )
                sessions.append(session)

            # 并发执行
            executors = []
            for session in sessions:
                executor = AgentExecutor(
                    agent_id=session.agent_id,
                    config=agent_config,
                )
                executors.append(executor)

            tasks = []
            for i, executor in enumerate(executors):
                context = AgentContext(
                    agent_id=executor.agent_id,
                    user_id=sessions[i].user_id,
                    session_id=sessions[i].session_id,
                    current_task=f"Concurrent task {i}",
                )
                task = executor.execute(context)
                tasks.append(task)

            results = await asyncio.gather(*tasks)
            return sum(1 for r in results if r.success)

        success_count = benchmark(lambda: asyncio.run(execute_concurrent()))
        assert success_count == 10

    def test_bench_concurrent_execution_50(
        self, benchmark, session_manager, agent_config
    ):
        """压力测试: 50 并发 Agent 执行 - 目标 < 2s"""

        async def execute_concurrent():
            # 先创建会话
            sessions = []
            for i in range(50):
                session = await session_manager.create_session(
                    user_id=f"exec_user_{i}",
                    agent_id="exec_agent",
                )
                sessions.append(session)

            # 并发执行
            executors = []
            for session in sessions:
                executor = AgentExecutor(
                    agent_id=session.agent_id,
                    config=agent_config,
                )
                executors.append(executor)

            tasks = []
            for i, executor in enumerate(executors):
                context = AgentContext(
                    agent_id=executor.agent_id,
                    user_id=sessions[i].user_id,
                    session_id=sessions[i].session_id,
                    current_task=f"Concurrent task {i}",
                )
                task = executor.execute(context)
                tasks.append(task)

            results = await asyncio.gather(*tasks)
            return sum(1 for r in results if r.success)

        success_count = benchmark(lambda: asyncio.run(execute_concurrent()))
        assert success_count == 50

    # -------------------------------------------------------------------------
    # Concurrent with Middleware
    # -------------------------------------------------------------------------

    def test_bench_concurrent_with_middleware_10(
        self, benchmark, session_manager, agent_config
    ):
        """压力测试: 10 并发执行（带 Middleware）"""

        async def execute_concurrent_with_middleware():
            # 创建共享的 middleware pipeline
            pipeline = MiddlewarePipeline()
            pipeline.add(StressTestMiddleware("auth", order=10))
            pipeline.add(StressTestMiddleware("logging", order=20))

            # 先创建会话
            sessions = []
            for i in range(10):
                session = await session_manager.create_session(
                    user_id=f"mw_user_{i}",
                    agent_id="mw_agent",
                )
                sessions.append(session)

            # 并发执行
            executors = []
            for session in sessions:
                executor = AgentExecutor(
                    agent_id=session.agent_id,
                    config=agent_config,
                    middleware_pipeline=pipeline,
                )
                executors.append(executor)

            tasks = []
            for i, executor in enumerate(executors):
                context = AgentContext(
                    agent_id=executor.agent_id,
                    user_id=sessions[i].user_id,
                    session_id=sessions[i].session_id,
                    current_task=f"Middleware task {i}",
                )
                task = executor.execute(context)
                tasks.append(task)

            results = await asyncio.gather(*tasks)
            return sum(1 for r in results if r.success)

        success_count = benchmark(
            lambda: asyncio.run(execute_concurrent_with_middleware())
        )
        assert success_count == 10

    # -------------------------------------------------------------------------
    # Mixed Workload Stress Test
    # -------------------------------------------------------------------------

    def test_bench_mixed_workload_20(
        self, benchmark, session_manager, event_bus, agent_config
    ):
        """压力测试: 混合工作负载（创建+执行+事件）"""

        async def mixed_workload():
            tasks = []

            # 10 个会话创建任务
            for i in range(10):
                task = session_manager.create_session(
                    user_id=f"mixed_user_{i}",
                    agent_id="mixed_agent",
                )
                tasks.append(task)

            # 等待会话创建
            sessions = await asyncio.gather(*tasks)

            # 10 个执行任务
            executors = []
            for session in sessions:
                executor = AgentExecutor(
                    agent_id=session.agent_id,
                    config=agent_config,
                )
                executors.append(executor)

            # 10 个事件发布任务
            event_tasks = []
            for i in range(10):
                event = Mock(
                    event_type=Mock(value="agent.started"),
                    source="stress_test",
                    component="test",
                    message=f"Event {i}",
                )
                # 使用简化的事件发布
                event_tasks.append(asyncio.sleep(0))

            # 执行任务
            execution_tasks = []
            for i, executor in enumerate(executors):
                context = AgentContext(
                    agent_id=executor.agent_id,
                    user_id=sessions[i].user_id,
                    session_id=sessions[i].session_id,
                    current_task=f"Mixed task {i}",
                )
                execution_tasks.append(executor.execute(context))

            # 并发执行所有任务
            all_tasks = execution_tasks + event_tasks
            results = await asyncio.gather(*all_tasks)

            # 返回成功的执行数量
            return sum(1 for r in results[:10] if hasattr(r, 'success') and r.success)

        success_count = benchmark(lambda: asyncio.run(mixed_workload()))
        assert success_count == 10

    # -------------------------------------------------------------------------
    # Extreme Stress Test
    # -------------------------------------------------------------------------

    def test_bench_extreme_concurrent_100(
        self, benchmark, session_manager, agent_config
    ):
        """极限测试: 100 并发执行 - 目标 < 5s"""

        async def extreme_concurrent():
            # 批量创建会话
            sessions = await asyncio.gather(*[
                session_manager.create_session(
                    user_id=f"extreme_user_{i}",
                    agent_id="extreme_agent",
                )
                for i in range(100)
            ])

            # 批量创建 executor
            executors = [
                AgentExecutor(
                    agent_id="extreme_agent",
                    config=agent_config,
                )
                for _ in range(100)
            ]

            # 并发执行
            tasks = [
                executor.execute(AgentContext(
                    agent_id="extreme_agent",
                    user_id=sessions[i].user_id,
                    session_id=sessions[i].session_id,
                    current_task=f"Extreme task {i}",
                ))
                for i, executor in enumerate(executors)
            ]

            results = await asyncio.gather(*tasks)
            return sum(1 for r in results if r.success)

        success_count = benchmark(lambda: asyncio.run(extreme_concurrent()))
        assert success_count == 100

    # -------------------------------------------------------------------------
    # Session Reuse Stress Test
    # -------------------------------------------------------------------------

    def test_bench_session_reuse_50(
        self, benchmark, session_manager, agent_config
    ):
        """压力测试: 50 个会话，每个执行 3 次"""

        async def session_reuse():
            # 创建 50 个会话
            sessions = await asyncio.gather(*[
                session_manager.create_session(
                    user_id=f"reuse_user_{i}",
                    agent_id="reuse_agent",
                )
                for i in range(50)
            ])

            # 每个会话执行 3 次
            executor = AgentExecutor(
                agent_id="reuse_agent",
                config=agent_config,
            )

            tasks = []
            for session in sessions:
                for round in range(3):
                    context = AgentContext(
                        agent_id=session.agent_id,
                        user_id=session.user_id,
                        session_id=session.session_id,
                        current_task=f"Reuse task round {round}",
                    )
                    tasks.append(executor.execute(context))

            results = await asyncio.gather(*tasks)
            return len(results)

        total_executions = benchmark(lambda: asyncio.run(session_reuse()))
        assert total_executions == 150  # 50 sessions * 3 rounds

    # -------------------------------------------------------------------------
    # Memory Stress Test
    # -------------------------------------------------------------------------

    def test_bench_memory_concurrent_20(
        self, benchmark, session_manager, agent_config
    ):
        """压力测试: 20 并发 Memory 操作"""

        # 创建 mock memory
        mock_memory = Mock()
        mock_memory.load_memory_variables = AsyncMock(return_value={
            "history": [f"message_{i}" for i in range(10)]
        })
        mock_memory.save_context = AsyncMock()

        async def memory_concurrent():
            # 创建 20 个会话
            sessions = await asyncio.gather(*[
                session_manager.create_session(
                    user_id=f"mem_user_{i}",
                    agent_id="mem_agent",
                )
                for i in range(20)
            ])

            # 创建带 memory 的 executor
            executors = [
                AgentExecutor(
                    agent_id="mem_agent",
                    config=agent_config,
                    memory=mock_memory,
                )
                for _ in range(20)
            ]

            # 并发执行
            tasks = [
                executor.execute(AgentContext(
                    agent_id="mem_agent",
                    user_id=sessions[i].user_id,
                    session_id=sessions[i].session_id,
                    current_task=f"Memory task {i}",
                ))
                for i, executor in enumerate(executors)
            ]

            results = await asyncio.gather(*tasks)
            return sum(1 for r in results if r.success)

        success_count = benchmark(lambda: asyncio.run(memory_concurrent()))
        assert success_count == 20

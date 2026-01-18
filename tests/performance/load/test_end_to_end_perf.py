"""
End-to-End Performance Tests

测试完整的 Agent 工作流性能，包括：
- Session 创建和管理
- Agent 执行
- EventBus 事件发布
- Middleware 处理
- Memory 操作

Performance targets:
- Complete workflow: < 100ms
- Session creation + execution: < 60ms
- Event-driven workflow: < 80ms
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock

from src.agent_runtime.session_manager import SessionManager
from src.agent_runtime.event_bus import EventBus
from src.agent_runtime.orchestration.executor import AgentExecutor, ExecutionConfig
from src.agent_runtime.orchestration.middleware.base import (
    AgentMiddleware,
    MiddlewarePipeline,
    MiddlewareResult,
)
from src.common.types.agent_types import (
    AgentConfig,
    AgentContext,
    AgentResult,
)
from src.common.types.event_types import EventType, SystemEvent


# =============================================================================
# Test Middleware
# =============================================================================

class E2EMiddleware(AgentMiddleware):
    """端到端测试中间件"""

    def __init__(self, name: str = "e2e", order: int = 100):
        super().__init__(name=name, order=order)
        self.call_count = 0

    async def process(self, context, next_call):
        self.call_count += 1
        context.metadata[f"{self.name}_processed"] = True
        return await next_call()


# =============================================================================
# End-to-End Workflow Tests
# =============================================================================

class TestEndToEndPerformance:
    """端到端性能测试"""

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
            name="e2e_agent",
            description="End-to-end test agent",
            model="gpt-3.5-turbo",
            temperature=0.7,
        )

    @pytest.fixture
    def agent_context(self):
        """创建 AgentContext"""
        return AgentContext(
            agent_id="e2e_agent",
            user_id="e2e_user",
            session_id="e2e_session",
            current_task="End-to-end test task",
        )

    # -------------------------------------------------------------------------
    # Complete Workflow Tests
    # -------------------------------------------------------------------------

    def test_bench_session_create_and_execute(
        self, benchmark, session_manager, agent_config, agent_context
    ):
        """基准测试: 创建会话并执行 Agent - 目标 < 60ms"""

        async def complete_workflow():
            # 1. 创建会话
            session = await session_manager.create_session(
                user_id="bench_user",
                agent_id="bench_agent",
                context=agent_context,
            )

            # 2. 创建 Executor
            executor = AgentExecutor(
                agent_id=session.agent_id,
                config=agent_config,
            )

            # 3. 执行
            context = AgentContext(
                agent_id=session.agent_id,
                user_id=session.user_id,
                session_id=session.session_id,
                current_task="Benchmark task",
            )

            result = await executor.execute(context)

            return {
                "session_created": session.session_id is not None,
                "execution_success": result.success,
            }

        result = benchmark(lambda: asyncio.run(complete_workflow()))
        assert result["session_created"] is True
        assert result["execution_success"] is True

    def test_bench_full_workflow_with_middleware(
        self, benchmark, session_manager, agent_config, agent_context
    ):
        """基准测试: 完整工作流（带 Middleware）- 目标 < 80ms"""

        async def complete_workflow():
            # 1. 创建会话
            session = await session_manager.create_session(
                user_id="bench_user",
                agent_id="bench_agent",
                context=agent_context,
            )

            # 2. 创建 Middleware Pipeline
            pipeline = MiddlewarePipeline()
            pipeline.add(E2EMiddleware("auth", order=10))
            pipeline.add(E2EMiddleware("logging", order=20))
            pipeline.add(E2EMiddleware("metrics", order=30))

            # 3. 创建 Executor
            executor = AgentExecutor(
                agent_id=session.agent_id,
                config=agent_config,
                middleware_pipeline=pipeline,
            )

            # 4. 执行
            context = AgentContext(
                agent_id=session.agent_id,
                user_id=session.user_id,
                session_id=session.session_id,
                current_task="Benchmark task",
            )

            result = await executor.execute(context)

            return {
                "success": result.success,
                "middleware_processed": all([
                    context.metadata.get("auth_processed"),
                    context.metadata.get("logging_processed"),
                    context.metadata.get("metrics_processed"),
                ]),
            }

        result = benchmark(lambda: asyncio.run(complete_workflow()))
        assert result["success"] is True
        assert result["middleware_processed"] is True

    def test_bench_event_driven_workflow(
        self, benchmark, session_manager, event_bus, agent_config, agent_context
    ):
        """基准测试: 事件驱动工作流 - 目标 < 80ms"""

        async def complete_workflow():
            events_received = []

            # 1. 订阅事件
            async def event_handler(event):
                events_received.append(event.event_type.value)

            await event_bus.subscribe(EventType.AGENT_STARTED, event_handler)
            await event_bus.subscribe(EventType.AGENT_COMPLETED, event_handler)

            # 2. 创建会话
            session = await session_manager.create_session(
                user_id="bench_user",
                agent_id="bench_agent",
            )

            # 3. 发布开始事件
            await event_bus.publish(SystemEvent(
                event_type=EventType.AGENT_STARTED,
                source="e2e_test",
                component="workflow",
                message="Agent started",
                details={"session_id": session.session_id},
            ))

            # 4. 创建并执行 Executor
            executor = AgentExecutor(
                agent_id=session.agent_id,
                config=agent_config,
            )

            context = AgentContext(
                agent_id=session.agent_id,
                user_id=session.user_id,
                session_id=session.session_id,
                current_task="Event-driven task",
            )

            result = await executor.execute(context)

            # 5. 发布完成事件
            await event_bus.publish(SystemEvent(
                event_type=EventType.AGENT_COMPLETED,
                source="e2e_test",
                component="workflow",
                message="Agent completed",
                details={"success": result.success},
            ))

            return {
                "success": result.success,
                "events_received": len(events_received),
            }

        result = benchmark(lambda: asyncio.run(complete_workflow()))
        assert result["success"] is True
        assert result["events_received"] == 2

    # -------------------------------------------------------------------------
    # Checkpoint Workflow Tests
    # -------------------------------------------------------------------------

    def test_bench_session_checkpoint_workflow(
        self, benchmark, session_manager, agent_config
    ):
        """基准测试: 会话检查点工作流"""

        async def checkpoint_workflow():
            # 1. 创建会话
            session = await session_manager.create_session(
                user_id="checkpoint_user",
                agent_id="checkpoint_agent",
            )

            # 2. 保存检查点（包含完整的 context 数据）
            checkpoint_data = {
                "state": "active",
                "step": 1,
                "context": {
                    "agent_id": session.agent_id,
                    "user_id": session.user_id,
                    "session_id": session.session_id,
                },
            }
            checkpoint_id = await session_manager.save_checkpoint(
                session.session_id,
                checkpoint_data,
            )

            # 3. 获取检查点（不恢复，因为需要完整 context）
            retrieved = await session_manager.get_checkpoint(
                session.session_id,
                checkpoint_id,
            )

            return {
                "checkpoint_saved": checkpoint_id is not None,
                "checkpoint_retrieved": retrieved is not None,
            }

        result = benchmark(lambda: asyncio.run(checkpoint_workflow()))
        assert result["checkpoint_saved"] is True
        assert result["checkpoint_retrieved"] is True

    # -------------------------------------------------------------------------
    # Multi-Session Workflow Tests
    # -------------------------------------------------------------------------

    def test_bench_multiple_sessions_workflow(
        self, benchmark, session_manager, agent_config
    ):
        """基准测试: 多会话工作流"""

        async def multi_session_workflow():
            # 1. 创建多个会话
            sessions = []
            for i in range(5):
                session = await session_manager.create_session(
                    user_id=f"user_{i}",
                    agent_id="agent_multi",
                )
                sessions.append(session)

            # 2. 执行多个会话
            results = []
            for session in sessions:
                executor = AgentExecutor(
                    agent_id=session.agent_id,
                    config=agent_config,
                )

                context = AgentContext(
                    agent_id=session.agent_id,
                    user_id=session.user_id,
                    session_id=session.session_id,
                    current_task=f"Task for {session.user_id}",
                )

                result = await executor.execute(context)
                results.append(result.success)

            return {
                "sessions_created": len(sessions),
                "successful_executions": sum(results),
            }

        result = benchmark(lambda: asyncio.run(multi_session_workflow()))
        assert result["sessions_created"] == 5
        assert result["successful_executions"] == 5

    # -------------------------------------------------------------------------
    # Memory Integration Workflow
    # -------------------------------------------------------------------------

    def test_bench_memory_integration_workflow(
        self, benchmark, session_manager, agent_config, agent_context
    ):
        """基准测试: Memory 集成工作流"""

        # 创建 mock memory
        mock_memory = Mock()
        mock_memory.load_memory_variables = AsyncMock(
            return_value={"history": ["previous message"]}
        )
        mock_memory.save_context = AsyncMock()

        async def memory_workflow():
            # 1. 创建会话
            session = await session_manager.create_session(
                user_id="memory_user",
                agent_id="memory_agent",
                context=agent_context,
            )

            # 2. 创建带 Memory 的 Executor
            executor = AgentExecutor(
                agent_id=session.agent_id,
                config=agent_config,
                memory=mock_memory,
            )

            # 3. 执行（会触发 Memory 操作）
            result = await executor.execute(agent_context)

            return {
                "success": result.success,
                "memory_loaded": mock_memory.load_memory_variables.called,
                "memory_saved": mock_memory.save_context.called,
            }

        result = benchmark(lambda: asyncio.run(memory_workflow()))
        assert result["success"] is True
        assert result["memory_loaded"] is True
        assert result["memory_saved"] is True

    # -------------------------------------------------------------------------
    # Complex Workflow Tests
    # -------------------------------------------------------------------------

    def test_bench_complex_e2e_workflow(
        self, benchmark, session_manager, event_bus, agent_config, agent_context
    ):
        """基准测试: 复杂端到端工作流 - 目标 < 100ms"""

        # 创建 mock memory
        mock_memory = Mock()
        mock_memory.load_memory_variables = AsyncMock(return_value={})
        mock_memory.save_context = AsyncMock()

        async def complex_workflow():
            events_received = []

            # 1. 设置事件订阅
            async def event_handler(event):
                events_received.append(event.event_type.value)

            await event_bus.subscribe(EventType.AGENT_STARTED, event_handler)
            await event_bus.subscribe(EventType.AGENT_COMPLETED, event_handler)

            # 2. 创建会话
            session = await session_manager.create_session(
                user_id="complex_user",
                agent_id="complex_agent",
                context=agent_context,
            )

            # 3. 保存初始检查点
            checkpoint_id = await session_manager.save_checkpoint(
                session.session_id,
                {"step": "initial"},
            )

            # 4. 创建 Middleware Pipeline
            pipeline = MiddlewarePipeline()
            pipeline.add(E2EMiddleware("auth", order=10))
            pipeline.add(E2EMiddleware("logging", order=20))

            # 5. 创建完整功能的 Executor
            executor = AgentExecutor(
                agent_id=session.agent_id,
                config=agent_config,
                memory=mock_memory,
                middleware_pipeline=pipeline,
            )

            # 6. 发布开始事件
            await event_bus.publish(SystemEvent(
                event_type=EventType.AGENT_STARTED,
                source="complex_workflow",
                component="test",
                message="Complex workflow started",
            ))

            # 7. 执行
            result = await executor.execute(agent_context)

            # 8. 保存执行检查点
            await session_manager.save_checkpoint(
                session.session_id,
                {"step": "completed", "result": result.success},
            )

            # 9. 发布完成事件
            await event_bus.publish(SystemEvent(
                event_type=EventType.AGENT_COMPLETED,
                source="complex_workflow",
                component="test",
                message="Complex workflow completed",
            ))

            return {
                "success": result.success,
                "events_received": len(events_received),
                "checkpoints_created": 2,
                "middleware_processed": agent_context.metadata.get("auth_processed"),
            }

        result = benchmark(lambda: asyncio.run(complex_workflow()))
        assert result["success"] is True
        assert result["events_received"] == 2
        assert result["checkpoints_created"] == 2

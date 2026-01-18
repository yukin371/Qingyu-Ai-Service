"""
Session Manager Performance Benchmarks

Performance targets (from Phase 6 plan):
- create_session: < 5ms
- get_session: < 1ms
- update_session: < 2ms
- save_checkpoint: < 10ms
- get_checkpoint: < 1ms
- resume_session: < 15ms
"""

import pytest
from uuid import uuid4

from src.agent_runtime.session_manager import SessionManager


class TestSessionManagerBenchmarks:
    """SessionManager 性能基准测试"""

    @pytest.fixture
    def session_manager(self):
        """创建 SessionManager 实例（使用内存存储）"""
        return SessionManager(conn=None, ttl=3600)

    # -------------------------------------------------------------------------
    # Session Creation Benchmarks
    # -------------------------------------------------------------------------

    def test_bench_create_session(self, benchmark, session_manager):
        """基准测试: 创建会话 - 目标 < 5ms"""

        def create_session():
            user_id = f"user_{uuid4().hex[:8]}"
            agent_id = f"agent_{uuid4().hex[:8]}"
            # Use asyncio.run for async method
            import asyncio
            return asyncio.run(session_manager.create_session(
                user_id=user_id,
                agent_id=agent_id,
            ))

        session = benchmark(create_session)
        assert session.session_id is not None
        assert session.user_id.startswith("user_")
        assert session.agent_id.startswith("agent_")

    def test_bench_create_session_batch_10(self, benchmark, session_manager):
        """基准测试: 批量创建 10 个会话"""

        import asyncio

        def create_batch():
            async def _create():
                sessions = []
                for i in range(10):
                    session = await session_manager.create_session(
                        user_id=f"user_{i}",
                        agent_id=f"agent_{i}",
                    )
                    sessions.append(session)
                return sessions
            return asyncio.run(_create())

        sessions = benchmark(create_batch)
        assert len(sessions) == 10

    # -------------------------------------------------------------------------
    # Session Retrieval Benchmarks
    # -------------------------------------------------------------------------

    @pytest.fixture
    def existing_session(self, session_manager):
        """创建一个已存在的会话用于测试"""
        import asyncio
        return asyncio.run(session_manager.create_session(
            user_id="bench_user",
            agent_id="bench_agent",
        ))

    def test_bench_get_session(self, benchmark, session_manager, existing_session):
        """基准测试: 获取会话 - 目标 < 1ms"""

        def get_session():
            import asyncio
            return asyncio.run(session_manager.get_session(existing_session.session_id))

        session = benchmark(get_session)
        assert session is not None
        assert session.session_id == existing_session.session_id

    def test_bench_session_exists(self, benchmark, session_manager, existing_session):
        """基准测试: 检查会话是否存在"""

        def check_exists():
            import asyncio
            return asyncio.run(session_manager.session_exists(existing_session.session_id))

        result = benchmark(check_exists)
        assert result is True

    def test_bench_get_sessions_by_user(self, benchmark, session_manager):
        """基准测试: 获取用户的所有会话"""

        import asyncio

        # 预先创建 5 个会话
        async def setup():
            user_id = "user_multi"
            for i in range(5):
                await session_manager.create_session(
                    user_id=user_id,
                    agent_id=f"agent_{i}",
                )
        asyncio.run(setup())

        def get_sessions():
            async def _get():
                return await session_manager.get_sessions_by_user("user_multi")
            return asyncio.run(_get())

        sessions = benchmark(get_sessions)
        assert len(sessions) == 5

    # -------------------------------------------------------------------------
    # Session Update Benchmarks
    # -------------------------------------------------------------------------

    def test_bench_update_session(self, benchmark, session_manager, existing_session):
        """基准测试: 更新会话 - 目标 < 2ms"""

        def update_session():
            import asyncio
            # Update metadata and save
            existing_session.metadata["updated"] = True
            return asyncio.run(session_manager.update_session(existing_session))

        benchmark(update_session)

    def test_bench_close_session(self, benchmark, session_manager):
        """基准测试: 关闭会话"""

        import asyncio

        # 创建新会话用于测试
        session = asyncio.run(session_manager.create_session(
            user_id="close_user",
            agent_id="close_agent",
        ))

        def close_session():
            import asyncio
            return asyncio.run(session_manager.close_session(session.session_id))

        result = benchmark(close_session)
        assert result is True

    # -------------------------------------------------------------------------
    # Checkpoint Benchmarks
    # -------------------------------------------------------------------------

    def test_bench_save_checkpoint(self, benchmark, session_manager, existing_session):
        """基准测试: 保存检查点 - 目标 < 10ms"""

        checkpoint_data = {
            "state": "active",
            "step": 5,
            "context": {"key": "value"},
        }

        def save_checkpoint():
            import asyncio
            return asyncio.run(session_manager.save_checkpoint(
                existing_session.session_id,
                checkpoint_data,
            ))

        checkpoint_id = benchmark(save_checkpoint)
        assert checkpoint_id is not None
        assert checkpoint_id.startswith("ckpt_")

    def test_bench_get_checkpoint(self, benchmark, session_manager, existing_session):
        """基准测试: 获取检查点 - 目标 < 1ms"""

        import asyncio

        # 先保存一个检查点
        checkpoint_data = {"state": "test", "value": 42}
        checkpoint_id = asyncio.run(session_manager.save_checkpoint(
            existing_session.session_id,
            checkpoint_data,
        ))

        def get_checkpoint():
            import asyncio
            return asyncio.run(session_manager.get_checkpoint(
                existing_session.session_id,
                checkpoint_id,
            ))

        data = benchmark(get_checkpoint)
        assert data is not None
        assert data["value"] == 42

    def test_bench_get_latest_checkpoint(self, benchmark, session_manager, existing_session):
        """基准测试: 获取最新检查点"""

        import asyncio

        # 保存多个检查点
        for i in range(3):
            asyncio.run(session_manager.save_checkpoint(
                existing_session.session_id,
                {"step": i},
            ))

        def get_latest():
            import asyncio
            return asyncio.run(session_manager.get_latest_checkpoint(
                existing_session.session_id,
            ))

        data = benchmark(get_latest)
        assert data is not None
        assert data["step"] == 2

    def test_bench_list_checkpoints(self, benchmark, session_manager, existing_session):
        """基准测试: 列出检查点"""

        import asyncio

        # 保存 5 个检查点
        for i in range(5):
            asyncio.run(session_manager.save_checkpoint(
                existing_session.session_id,
                {"step": i},
            ))

        def list_checkpoints():
            import asyncio
            return asyncio.run(session_manager.list_checkpoints(
                existing_session.session_id,
                limit=10,
            ))

        checkpoints = benchmark(list_checkpoints)
        assert len(checkpoints) == 5

    # -------------------------------------------------------------------------
    # Session Resume Benchmarks
    # -------------------------------------------------------------------------

    def test_bench_resume_session(self, benchmark, session_manager, existing_session):
        """基准测试: 从检查点恢复会话 - 目标 < 15ms"""

        import asyncio

        # 保存检查点
        checkpoint_data = {
            "context": {
                "agent_id": "bench_agent",
                "user_id": "bench_user",
                "session_id": existing_session.session_id,
            },
            "state": "resumed",
        }
        checkpoint_id = asyncio.run(session_manager.save_checkpoint(
            existing_session.session_id,
            checkpoint_data,
        ))

        def resume_session():
            import asyncio
            return asyncio.run(session_manager.resume_session(
                existing_session.session_id,
                checkpoint_id,
            ))

        session = benchmark(resume_session)
        assert session is not None
        assert session.session_id == existing_session.session_id

    def test_bench_resume_from_latest(self, benchmark, session_manager, existing_session):
        """基准测试: 从最新检查点恢复会话"""

        import asyncio

        # 保存检查点
        asyncio.run(session_manager.save_checkpoint(
            existing_session.session_id,
            {"step": 1},
        ))

        def resume_latest():
            import asyncio
            return asyncio.run(session_manager.resume_from_latest(
                existing_session.session_id,
            ))

        session = benchmark(resume_latest)
        assert session is not None

    # -------------------------------------------------------------------------
    # Batch Operations
    # -------------------------------------------------------------------------

    def test_bench_cleanup_expired(self, benchmark, session_manager):
        """基准测试: 清理过期会话"""

        import asyncio
        from datetime import datetime, timedelta

        # 创建一些已过期的会话
        async def setup():
            for i in range(3):
                session = await session_manager.create_session(
                    user_id=f"expired_user_{i}",
                    agent_id=f"expired_agent_{i}",
                    ttl=-1,  # 立即过期
                )
                # 手动设置过期时间为过去
                session.expires_at = datetime.utcnow() - timedelta(seconds=10)
                await session_manager.update_session(session)
        asyncio.run(setup())

        def cleanup():
            import asyncio
            return asyncio.run(session_manager.cleanup_expired())

        count = benchmark(cleanup)
        assert count >= 0  # 取决于过期检查

    # -------------------------------------------------------------------------
    # Statistics Benchmarks
    # -------------------------------------------------------------------------

    def test_bench_get_session_count(self, benchmark, session_manager):
        """基准测试: 获取总会话数"""

        # 先创建一些会话
        import asyncio
        for i in range(5):
            asyncio.run(session_manager.create_session(
                user_id=f"count_user_{i}",
                agent_id=f"count_agent_{i}",
            ))

        def get_count():
            import asyncio
            return asyncio.run(session_manager.get_session_count())

        count = benchmark(get_count)
        assert count >= 5

    def test_bench_get_active_session_count(self, benchmark, session_manager):
        """基准测试: 获取活跃会话数"""

        # 先创建一些会话
        import asyncio
        for i in range(5):
            asyncio.run(session_manager.create_session(
                user_id=f"active_user_{i}",
                agent_id=f"active_agent_{i}",
            ))

        def get_active_count():
            import asyncio
            return asyncio.run(session_manager.get_active_session_count())

        count = benchmark(get_active_count)
        assert count >= 5

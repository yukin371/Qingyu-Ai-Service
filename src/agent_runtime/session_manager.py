"""
Session Manager - 分布式会话管理

负责管理 Agent 会话，支持 Redis 分布式存储。

设计原则:
- 分布式：使用 Redis 支持多实例部署
- TTL：自动过期清理
- 检查点：支持会话状态保存和恢复
- 线程安全：支持并发访问
"""

import logging
import json
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict

from src.common.types.agent_types import AgentContext


logger = logging.getLogger(__name__)


# =============================================================================
# Session Model
# =============================================================================

class Session(BaseModel):
    """
    Agent 会话模型

    Attributes:
        session_id: 会话唯一标识符
        user_id: 用户 ID
        agent_id: Agent ID
        context: Agent 上下文
        status: 会话状态 (active, closed, error)
        metadata: 额外元数据
        created_at: 会话创建时间
        updated_at: 会话更新时间
        expires_at: 会话过期时间
    """

    session_id: str = Field(..., description="Session unique identifier")
    user_id: str = Field(..., description="User ID")
    agent_id: str = Field(..., description="Agent ID")
    context: AgentContext = Field(
        default_factory=lambda: None,
        description="Agent execution context"
    )
    status: str = Field(default="active", description="Session status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Session metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation time")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update time")
    expires_at: Optional[datetime] = Field(default=None, description="Expiration time")

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
        use_enum_values=False
    )

    def is_expired(self) -> bool:
        """检查会话是否已过期"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def touch(self) -> None:
        """更新会话的最后活动时间"""
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump()


# =============================================================================
# Session Manager
# =============================================================================

class SessionManager:
    """
    会话管理器

    管理 Agent 会话的生命周期，支持创建、更新、查询、删除等操作。
    使用 Redis 作为后端存储，支持分布式部署。

    使用示例:
        ```python
        # 创建会话管理器
        manager = SessionManager(conn=redis_conn, ttl=3600)

        # 创建会话
        session = await manager.create_session(
            user_id="user_123",
            agent_id="agent_456",
        )

        # 获取会话
        session = await manager.get_session(session_id)

        # 保存检查点
        checkpoint_id = await manager.save_checkpoint(
            session_id,
            {"state": "data"},
        )

        # 恢复会话
        session = await manager.resume_session(session_id, checkpoint_id)

        # 关闭会话
        await manager.close_session(session_id)
        ```
    """

    def __init__(
        self,
        conn: Optional[Any] = None,
        ttl: int = 3600,
        prefix: str = "session",
    ):
        """
        初始化会话管理器

        Args:
            conn: Redis 连接（如果为 None，使用内存存储用于测试）
            ttl: 会话默认 TTL（秒）
            prefix: Redis 键前缀
        """
        self.conn = conn
        self.ttl = ttl
        self.prefix = prefix

        # 内存存储（用于测试）
        self._mock_storage: Dict[str, str] = {}
        self._mock_checkpoints: Dict[str, List[Dict[str, Any]]] = {}

        # 并发锁
        self._lock = asyncio.Lock()

    # -------------------------------------------------------------------------
    # Key Generation
    # -------------------------------------------------------------------------

    def _make_session_key(self, session_id: str) -> str:
        """生成会话的 Redis 键"""
        return f"{self.prefix}:session:{session_id}"

    def _make_user_sessions_key(self, user_id: str) -> str:
        """生成用户会话列表的 Redis 键"""
        return f"{self.prefix}:user_sessions:{user_id}"

    def _make_checkpoint_key(self, session_id: str) -> str:
        """生成检查点列表的 Redis 键"""
        return f"{self.prefix}:checkpoints:{session_id}"

    def _make_checkpoint_id_key(self, session_id: str, checkpoint_id: str) -> str:
        """生成单个检查点的 Redis 键"""
        return f"{self.prefix}:checkpoint:{session_id}:{checkpoint_id}"

    # -------------------------------------------------------------------------
    # Session Creation
    # -------------------------------------------------------------------------

    async def create_session(
        self,
        user_id: str,
        agent_id: str,
        context: Optional[AgentContext] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> Session:
        """
        创建新会话

        Args:
            user_id: 用户 ID
            agent_id: Agent ID
            context: 初始上下文
            metadata: 元数据
            ttl: 会话 TTL（秒），None 使用默认值

        Returns:
            创建的 Session 对象
        """
        session_id = f"sess_{uuid4().hex}"

        # 计算过期时间
        session_ttl = ttl if ttl is not None else self.ttl
        expires_at = (
            datetime.utcnow() + timedelta(seconds=session_ttl)
            if session_ttl > 0
            else None
        )

        # 创建会话
        session = Session(
            session_id=session_id,
            user_id=user_id,
            agent_id=agent_id,
            context=context or AgentContext(
                agent_id=agent_id,
                user_id=user_id,
                session_id=session_id,
            ),
            metadata=metadata or {},
            expires_at=expires_at,
        )

        # 保存会话
        await self._save_session(session, session_ttl)

        # 添加到用户会话列表
        await self._add_to_user_sessions(user_id, session_id)

        logger.info(f"Created session: {session_id} for user: {user_id}")
        return session

    async def _save_session(self, session: Session, ttl: Optional[int] = None) -> None:
        """保存会话到存储"""
        key = self._make_session_key(session.session_id)
        value = session.model_dump_json()

        if self.conn is not None:
            if ttl and ttl > 0:
                await self.conn.set(key, value, ex=ttl)
            else:
                await self.conn.set(key, value)
        else:
            self._mock_storage[key] = value

    async def _add_to_user_sessions(self, user_id: str, session_id: str) -> None:
        """添加会话到用户会话列表"""
        key = self._make_user_sessions_key(user_id)

        if self.conn is not None:
            await self.conn.sadd(key, session_id)
            await self.conn.expire(key, self.ttl)
        else:
            if key not in self._mock_storage:
                self._mock_storage[key] = set()
            self._mock_storage[key].add(session_id)

    # -------------------------------------------------------------------------
    # Session Retrieval
    # -------------------------------------------------------------------------

    async def get_session(self, session_id: str) -> Optional[Session]:
        """
        获取会话

        Args:
            session_id: 会话 ID

        Returns:
            Session 对象，不存在或已过期返回 None
        """
        try:
            key = self._make_session_key(session_id)

            if self.conn is not None:
                value = await self.conn.get(key)
            else:
                value = self._mock_storage.get(key)

            if value is None:
                return None

            data = json.loads(value)
            session = Session(**data)

            # 检查是否过期（不自动删除，由调用者处理）
            if session.is_expired():
                return None

            return session

        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            return None

    async def get_sessions_by_user(
        self,
        user_id: str,
        status: Optional[str] = None,
    ) -> List[Session]:
        """
        获取用户的所有会话

        Args:
            user_id: 用户 ID
            status: 可选的状态过滤

        Returns:
            Session 列表
        """
        key = self._make_user_sessions_key(user_id)

        # 获取会话 ID 列表
        if self.conn is not None:
            session_ids = await self.conn.smembers(key)
        else:
            session_ids = self._mock_storage.get(key, set())

        # 加载会话
        sessions = []
        for session_id in session_ids:
            session = await self.get_session(session_id)
            if session:
                if status is None or session.status == status:
                    sessions.append(session)

        return sessions

    async def session_exists(self, session_id: str) -> bool:
        """
        检查会话是否存在

        Args:
            session_id: 会话 ID

        Returns:
            是否存在
        """
        key = self._make_session_key(session_id)

        if self.conn is not None:
            value = await self.conn.get(key)
        else:
            value = self._mock_storage.get(key)

        return value is not None

    # -------------------------------------------------------------------------
    # Session Update
    # -------------------------------------------------------------------------

    async def update_session(self, session: Session) -> None:
        """
        更新会话

        Args:
            session: 更新的 Session 对象
        """
        session.touch()

        # 计算 TTL
        if session.expires_at:
            ttl = int((session.expires_at - datetime.utcnow()).total_seconds())
            ttl = max(0, ttl)
        else:
            ttl = self.ttl

        await self._save_session(session, ttl)
        logger.debug(f"Updated session: {session.session_id}")

    # -------------------------------------------------------------------------
    # Session Lifecycle
    # -------------------------------------------------------------------------

    async def close_session(self, session_id: str) -> bool:
        """
        关闭会话

        Args:
            session_id: 会话 ID

        Returns:
            是否成功
        """
        session = await self.get_session(session_id)
        if not session:
            return False

        session.status = "closed"
        await self.update_session(session)

        logger.info(f"Closed session: {session_id}")
        return True

    async def delete_session(self, session_id: str) -> bool:
        """
        删除会话

        Args:
            session_id: 会话 ID

        Returns:
            是否成功
        """
        try:
            # 加载会话数据（不检查过期状态）
            key = self._make_session_key(session_id)

            if self.conn is not None:
                value = await self.conn.get(key)
            else:
                value = self._mock_storage.get(key)

            if value is None:
                return False

            data = json.loads(value)
            user_id = data.get("user_id")

            # 从用户会话列表中移除
            if user_id:
                await self._remove_from_user_sessions(user_id, session_id)

            # 删除检查点
            await self._delete_checkpoints(session_id)

            # 删除会话
            if self.conn is not None:
                await self.conn.delete(key)
            else:
                if key in self._mock_storage:
                    del self._mock_storage[key]

            logger.info(f"Deleted session: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False

    async def _remove_from_user_sessions(self, user_id: str, session_id: str) -> None:
        """从用户会话列表中移除"""
        key = self._make_user_sessions_key(user_id)

        if self.conn is not None:
            await self.conn.srem(key, session_id)
        else:
            if key in self._mock_storage:
                self._mock_storage[key].discard(session_id)

    async def _delete_checkpoints(self, session_id: str) -> None:
        """删除会话的所有检查点"""
        checkpoint_key = self._make_checkpoint_key(session_id)

        if self.conn is not None:
            # 获取所有检查点 ID
            checkpoint_ids = await self.conn.smembers(checkpoint_key)
            if checkpoint_ids:
                # 删除检查点数据
                keys = [
                    self._make_checkpoint_id_key(session_id, cid)
                    for cid in checkpoint_ids
                ]
                await self.conn.delete(*keys)
            # 删除检查点列表
            await self.conn.delete(checkpoint_key)
        else:
            # 删除所有检查点
            checkpoint_ids = self._mock_checkpoints.get(checkpoint_key, [])
            for cid in checkpoint_ids:
                key = self._make_checkpoint_id_key(session_id, cid)
                if key in self._mock_checkpoints:
                    del self._mock_checkpoints[key]
            # 删除检查点列表
            if checkpoint_key in self._mock_checkpoints:
                del self._mock_checkpoints[checkpoint_key]

    async def cleanup_expired(self) -> int:
        """
        清理过期会话

        Returns:
            清理的会话数量
        """
        try:
            pattern = f"{self.prefix}:session:*"
            cleaned = 0

            if self.conn is not None:
                keys = await self.conn.keys(pattern)
            else:
                keys = [
                    k for k in self._mock_storage.keys()
                    if k.startswith(f"{self.prefix}:session:")
                ]

            for key in keys:
                if self.conn is not None:
                    value = await self.conn.get(key)
                else:
                    value = self._mock_storage.get(key)

                if value:
                    data = json.loads(value)
                    session = Session(**data)

                    if session.is_expired():
                        await self.delete_session(session.session_id)
                        cleaned += 1

            logger.info(f"Cleaned up {cleaned} expired sessions")
            return cleaned

        except Exception as e:
            logger.error(f"Error cleaning up expired sessions: {e}")
            return 0

    # -------------------------------------------------------------------------
    # Checkpoint Management
    # -------------------------------------------------------------------------

    async def save_checkpoint(
        self,
        session_id: str,
        data: Dict[str, Any],
    ) -> str:
        """
        保存检查点

        Args:
            session_id: 会话 ID
            data: 检查点数据

        Returns:
            检查点 ID
        """
        checkpoint_id = f"ckpt_{uuid4().hex}"

        checkpoint = {
            "checkpoint_id": checkpoint_id,
            "session_id": session_id,
            "data": data,
            "created_at": datetime.utcnow().isoformat(),
        }

        # 保存检查点
        key = self._make_checkpoint_id_key(session_id, checkpoint_id)

        # 自定义 JSON 编码器处理 datetime
        def json_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        value = json.dumps(checkpoint, default=json_serializer)

        if self.conn is not None:
            await self.conn.set(key, value, ex=self.ttl)
        else:
            self._mock_checkpoints[key] = value

        # 添加到检查点列表
        list_key = self._make_checkpoint_key(session_id)
        if self.conn is not None:
            await self.conn.sadd(list_key, checkpoint_id)
            await self.conn.expire(list_key, self.ttl)
        else:
            if list_key not in self._mock_checkpoints:
                self._mock_checkpoints[list_key] = []
            if checkpoint_id not in self._mock_checkpoints[list_key]:
                self._mock_checkpoints[list_key].append(checkpoint_id)

        logger.debug(f"Saved checkpoint {checkpoint_id} for session {session_id}")
        return checkpoint_id

    async def get_checkpoint(
        self,
        session_id: str,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        获取检查点

        Args:
            session_id: 会话 ID
            checkpoint_id: 检查点 ID

        Returns:
            检查点数据，不存在返回 None
        """
        key = self._make_checkpoint_id_key(session_id, checkpoint_id)

        if self.conn is not None:
            value = await self.conn.get(key)
        else:
            value = self._mock_checkpoints.get(key)

        if value is None:
            return None

        checkpoint = json.loads(value)
        # 返回数据部分，而不是包装器
        return checkpoint.get("data")

    async def list_checkpoints(
        self,
        session_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        列出会话的所有检查点

        Args:
            session_id: 会话 ID
            limit: 最大数量

        Returns:
            检查点数据列表（按最新优先排序）
        """
        list_key = self._make_checkpoint_key(session_id)

        if self.conn is not None:
            checkpoint_ids = await self.conn.smembers(list_key)
            # Redis sets are unordered, get as list
            checkpoint_ids = list(checkpoint_ids)
        else:
            checkpoint_ids = self._mock_checkpoints.get(list_key, [])

        # 反转列表，使最新的在前（后添加的在后面，反转后最新的在前）
        checkpoint_ids = list(reversed(checkpoint_ids))

        checkpoints = []
        for cid in checkpoint_ids[:limit]:
            checkpoint_data = await self.get_checkpoint(session_id, cid)
            if checkpoint_data:
                checkpoints.append(checkpoint_data)

        return checkpoints

    async def get_latest_checkpoint(
        self,
        session_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        获取最新检查点

        Args:
            session_id: 会话 ID

        Returns:
            最新检查点数据
        """
        checkpoints = await self.list_checkpoints(session_id, limit=1)
        return checkpoints[0] if checkpoints else None

    async def _get_latest_checkpoint_id(self, session_id: str) -> Optional[str]:
        """
        获取最新检查点 ID（内部方法）

        Args:
            session_id: 会话 ID

        Returns:
            最新检查点 ID
        """
        list_key = self._make_checkpoint_key(session_id)

        if self.conn is not None:
            checkpoint_ids = await self.conn.smembers(list_key)
            # 返回第一个（最新的）
            return list(checkpoint_ids)[0] if checkpoint_ids else None
        else:
            checkpoint_ids = self._mock_checkpoints.get(list_key, [])
            return checkpoint_ids[-1] if checkpoint_ids else None

    # -------------------------------------------------------------------------
    # Session Resume
    # -------------------------------------------------------------------------

    async def resume_session(
        self,
        session_id: str,
        checkpoint_id: str,
    ) -> Optional[Session]:
        """
        从检查点恢复会话

        Args:
            session_id: 会话 ID
            checkpoint_id: 检查点 ID

        Returns:
            恢复的 Session 对象
        """
        # 获取会话
        session = await self.get_session(session_id)
        if not session:
            return None

        # 获取检查点数据
        checkpoint_data = await self.get_checkpoint(session_id, checkpoint_id)
        if not checkpoint_data:
            return None

        # 恢复状态
        if "context" in checkpoint_data:
            session.context = AgentContext(**checkpoint_data["context"])

        session.touch()
        await self.update_session(session)

        logger.info(f"Resumed session {session_id} from checkpoint {checkpoint_id}")
        return session

    async def resume_from_latest(self, session_id: str) -> Optional[Session]:
        """
        从最新检查点恢复会话

        Args:
            session_id: 会话 ID

        Returns:
            恢复的 Session 对象
        """
        checkpoint_id = await self._get_latest_checkpoint_id(session_id)
        if not checkpoint_id:
            return None

        return await self.resume_session(session_id, checkpoint_id)

    # -------------------------------------------------------------------------
    # Batch Operations
    # -------------------------------------------------------------------------

    async def close_user_sessions(self, user_id: str) -> int:
        """
        关闭用户的所有会话

        Args:
            user_id: 用户 ID

        Returns:
            关闭的会话数量
        """
        sessions = await self.get_sessions_by_user(user_id)
        count = 0

        for session in sessions:
            if await self.close_session(session.session_id):
                count += 1

        logger.info(f"Closed {count} sessions for user {user_id}")
        return count

    async def delete_user_sessions(self, user_id: str) -> int:
        """
        删除用户的所有会话

        Args:
            user_id: 用户 ID

        Returns:
            删除的会话数量
        """
        sessions = await self.get_sessions_by_user(user_id)
        count = 0

        for session in sessions:
            if await self.delete_session(session.session_id):
                count += 1

        logger.info(f"Deleted {count} sessions for user {user_id}")
        return count

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    async def get_session_count(self) -> int:
        """
        获取总会话数

        Returns:
            会话数量
        """
        try:
            pattern = f"{self.prefix}:session:*"

            if self.conn is not None:
                keys = await self.conn.keys(pattern)
            else:
                keys = [
                    k for k in self._mock_storage.keys()
                    if k.startswith(f"{self.prefix}:session:")
                ]

            return len(keys)

        except Exception:
            return 0

    async def get_active_session_count(self) -> int:
        """
        获取活跃会话数

        Returns:
            活跃会话数量
        """
        try:
            pattern = f"{self.prefix}:session:*"

            if self.conn is not None:
                keys = await self.conn.keys(pattern)
            else:
                keys = [
                    k for k in self._mock_storage.keys()
                    if k.startswith(f"{self.prefix}:session:")
                ]

            count = 0
            for key in keys:
                if self.conn is not None:
                    value = await self.conn.get(key)
                else:
                    value = self._mock_storage.get(key)

                if value:
                    data = json.loads(value)
                    session = Session(**data)
                    if session.status == "active" and not session.is_expired():
                        count += 1

            return count

        except Exception:
            return 0

    async def get_user_session_count(self, user_id: str) -> int:
        """
        获取用户的会话数

        Args:
            user_id: 用户 ID

        Returns:
            会话数量
        """
        sessions = await self.get_sessions_by_user(user_id)
        return len(sessions)

    async def get_user_sessions(
        self,
        user_id: str,
        status: Optional[str] = None,
    ) -> List[Session]:
        """
        获取用户的所有会话（别名方法）

        Args:
            user_id: 用户 ID
            status: 可选的状态过滤

        Returns:
            Session 列表
        """
        return await self.get_sessions_by_user(user_id, status)

    async def update_session_context(
        self,
        session_id: str,
        context: AgentContext,
    ) -> None:
        """
        更新会话的上下文

        Args:
            session_id: 会话 ID
            context: 新的 Agent 上下文
        """
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        # Update context
        session.context = context
        session.updated_at = datetime.utcnow()

        # Save updated session
        await self.update_session(session)
        logger.debug(f"Updated context for session: {session_id}")

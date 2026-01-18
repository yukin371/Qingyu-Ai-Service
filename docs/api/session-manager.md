# SessionManager API 参考

SessionManager 负责管理用户会话和状态持久化。

## 类定义

```python
from src.agent_runtime.session_manager import SessionManager

class SessionManager:
    def __init__(
        self,
        conn: redis.Redis,
        ttl: int = 3600,
        max_sessions: int = 10000,
    ):
        """
        初始化 SessionManager

        Args:
            conn: Redis 连接
            ttl: 会话过期时间（秒），默认 3600（1小时）
            max_sessions: 最大会话数，默认 10000
        """
```

## 方法

### create_session()

创建新会话。

```python
async def create_session(
    self,
    user_id: str,
    agent_id: str,
    metadata: Dict[str, Any] = None,
) -> Session:
    """
    创建新会话

    Args:
        user_id: 用户 ID
        agent_id: Agent ID
        metadata: 可选的元数据

    Returns:
        Session: 创建的会话对象

    Raises:
        ValueError: 如果参数无效
        RuntimeError: 如果达到最大会话数

    Example:
        >>> session = await session_manager.create_session(
        ...     user_id="user_123",
        ...     agent_id="chatbot",
        ...     metadata={"tier": "premium"},
        ... )
        >>> print(session.session_id)
        'sess_abc123'
    """
```

### get_session()

获取会话。

```python
async def get_session(
    self,
    session_id: str,
) -> Optional[Session]:
    """
    获取会话

    Args:
        session_id: 会话 ID

    Returns:
        Optional[Session]: 会话对象，如果不存在或已过期返回 None

    Example:
        >>> session = await session_manager.get_session("sess_abc123")
        >>> if session:
        ...     print(f"User: {session.user_id}")
        ...     print(f"Agent: {session.agent_id}")
    """
```

### update_session()

更新会话。

```python
async def update_session(
    self,
    session_id: str,
    **updates,
) -> bool:
    """
    更新会话

    Args:
        session_id: 会话 ID
        **updates: 要更新的字段

    Returns:
        bool: 是否更新成功

    Example:
        >>> success = await session_manager.update_session(
        ...     "sess_abc123",
        ...     metadata={"last_activity": "2025-01-17T10:00:00Z"},
        ... )
        >>> print(success)
        True
    """
```

### update_session_metadata()

更新会话元数据。

```python
async def update_session_metadata(
    self,
    session_id: str,
    metadata: Dict[str, Any],
) -> bool:
    """
    更新会话元数据

    Args:
        session_id: 会话 ID
        metadata: 元数据字典

    Returns:
        bool: 是否更新成功

    Example:
        >>> success = await session_manager.update_session_metadata(
        ...     "sess_abc123",
        ...     {"message_count": 5, "last_topic": "weather"},
        ... )
    """
```

### delete_session()

删除会话。

```python
async def delete_session(
    self,
    session_id: str,
) -> bool:
    """
    删除会话

    Args:
        session_id: 会话 ID

    Returns:
        bool: 是否删除成功

    Example:
        >>> success = await session_manager.delete_session("sess_abc123")
    """
```

### get_sessions_by_user()

获取用户的所有会话。

```python
async def get_sessions_by_user(
    self,
    user_id: str,
) -> List[Session]:
    """
    获取用户的所有会话

    Args:
        user_id: 用户 ID

    Returns:
        List[Session]: 会话列表

    Example:
        >>> sessions = await session_manager.get_sessions_by_user("user_123")
        >>> for session in sessions:
        ...     print(f"{session.session_id}: {session.agent_id}")
    """
```

### session_exists()

检查会话是否存在。

```python
async def session_exists(
    self,
    session_id: str,
) -> bool:
    """
    检查会话是否存在

    Args:
        session_id: 会话 ID

    Returns:
        bool: 会话是否存在

    Example:
        >>> exists = await session_manager.session_exists("sess_abc123")
    """
```

### get_active_session_count()

获取活跃会话数。

```python
async def get_active_session_count(
    self,
    user_id: str = None,
) -> int:
    """
    获取活跃会话数

    Args:
        user_id: 可选的用户 ID，如果提供则返回该用户的活跃会话数

    Returns:
        int: 活跃会话数

    Example:
        >>> count = await session_manager.get_active_session_count("user_123")
        >>> print(count)
        3
    """
```

### refresh_session()

刷新会话过期时间。

```python
async def refresh_session(
    self,
    session_id: str,
) -> bool:
    """
    刷新会话过期时间

    Args:
        session_id: 会话 ID

    Returns:
        bool: 是否刷新成功

    Example:
        >>> success = await session_manager.refresh_session("sess_abc123")
    """
```

## 检查点方法

### save_checkpoint()

保存检查点。

```python
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
        str: 检查点 ID

    Raises:
        ValueError: 如果会话不存在

    Example:
        >>> checkpoint_id = await session_manager.save_checkpoint(
        ...     "sess_abc123",
        ...     {
        ...         "state": "active",
        ...         "turn": 1,
        ...         "history": [{"role": "user", "content": "Hi"}],
        ...     },
        ... )
        >>> print(checkpoint_id)
        'ckpt_xyz789'
    """
```

### get_checkpoint()

获取检查点。

```python
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
        Optional[Dict[str, Any]]: 检查点数据，如果不存在返回 None

    Example:
        >>> checkpoint = await session_manager.get_checkpoint(
        ...     "sess_abc123",
        ...     "ckpt_xyz789",
        ... )
        >>> if checkpoint:
        ...     print(checkpoint["data"])
    """
```

### get_latest_checkpoint()

获取最新检查点。

```python
async def get_latest_checkpoint(
    self,
    session_id: str,
) -> Optional[Dict[str, Any]]:
    """
    获取最新检查点

    Args:
        session_id: 会话 ID

    Returns:
        Optional[Dict[str, Any]]: 最新检查点数据，如果没有返回 None

    Example:
        >>> checkpoint = await session_manager.get_latest_checkpoint("sess_abc123")
    """
```

### list_checkpoints()

列出所有检查点。

```python
async def list_checkpoints(
    self,
    session_id: str,
) -> List[Dict[str, Any]]:
    """
    列出所有检查点

    Args:
        session_id: 会话 ID

    Returns:
        List[Dict[str, Any]]: 检查点列表

    Example:
        >>> checkpoints = await session_manager.list_checkpoints("sess_abc123")
        >>> for cp in checkpoints:
        ...     print(f"{cp['checkpoint_id']}: {cp['created_at']}")
    """
```

### delete_checkpoint()

删除检查点。

```python
async def delete_checkpoint(
    self,
    session_id: str,
    checkpoint_id: str,
) -> bool:
    """
    删除检查点

    Args:
        session_id: 会话 ID
        checkpoint_id: 检查点 ID

    Returns:
        bool: 是否删除成功

    Example:
        >>> success = await session_manager.delete_checkpoint(
        ...     "sess_abc123",
        ...     "ckpt_xyz789",
        ... )
    """
```

### clear_checkpoints()

清除所有检查点。

```python
async def clear_checkpoints(
    self,
    session_id: str,
) -> int:
    """
    清除所有检查点

    Args:
        session_id: 会话 ID

    Returns:
        int: 清除的检查点数量

    Example:
        >>> count = await session_manager.clear_checkpoints("sess_abc123")
        >>> print(f"Cleared {count} checkpoints")
    """
```

## 维护方法

### cleanup_expired_sessions()

清理过期会话。

```python
async def cleanup_expired_sessions(
    self,
) -> int:
    """
    清理过期会话

    Returns:
        int: 清理的会话数量

    Example:
        >>> cleaned = await session_manager.cleanup_expired_sessions()
        >>> print(f"Cleaned {cleaned} expired sessions")
    """
```

### delete_user_sessions()

删除用户的所有会话。

```python
async def delete_user_sessions(
    self,
    user_id: str,
) -> int:
    """
    删除用户的所有会话

    Args:
        user_id: 用户 ID

    Returns:
        int: 删除的会话数量

    Example:
        >>> count = await session_manager.delete_user_sessions("user_123")
    """
```

### delete_agent_sessions()

删除 Agent 的所有会话。

```python
async def delete_agent_sessions(
    self,
    agent_id: str,
) -> int:
    """
    删除 Agent 的所有会话

    Args:
        agent_id: Agent ID

    Returns:
        int: 删除的会话数量

    Example:
        >>> count = await session_manager.delete_agent_sessions("chatbot")
    """
```

## 数据类型

### Session

```python
class Session(BaseModel):
    session_id: str                    # 会话 ID
    user_id: str                       # 用户 ID
    agent_id: str                      # Agent ID
    created_at: datetime               # 创建时间
    expires_at: datetime               # 过期时间
    metadata: Dict[str, Any] = {}      # 元数据
```

### Checkpoint

```python
class Checkpoint(BaseModel):
    checkpoint_id: str                 # 检查点 ID
    session_id: str                    # 会话 ID
    data: Dict[str, Any]               # 检查点数据
    created_at: datetime               # 创建时间
```

## 使用示例

### 基本使用

```python
import asyncio
from src.agent_runtime.session_manager import SessionManager
import redis

async def main():
    # 创建 SessionManager
    redis_client = redis.Redis(host='localhost', port=6379)
    session_manager = SessionManager(
        conn=redis_client,
        ttl=3600,  # 1小时过期
    )

    # 创建会话
    session = await session_manager.create_session(
        user_id="user_123",
        agent_id="chatbot",
    )

    print(f"Created session: {session.session_id}")

    # 检索会话
    retrieved = await session_manager.get_session(session.session_id)
    print(f"Retrieved: {retrieved.user_id}")

asyncio.run(main())
```

### 使用检查点

```python
async def main():
    session_manager = SessionManager(conn=redis_client)

    # 创建会话
    session = await session_manager.create_session(
        user_id="user_123",
        agent_id="chatbot",
    )

    # 保存检查点
    checkpoint_id = await session_manager.save_checkpoint(
        session.session_id,
        {
            "state": "conversation_active",
            "turn": 1,
            "history": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ],
        },
    )

    print(f"Saved checkpoint: {checkpoint_id}")

    # 检索检查点
    checkpoint = await session_manager.get_checkpoint(
        session.session_id,
        checkpoint_id,
    )

    print(f"Checkpoint state: {checkpoint['data']['state']}")

asyncio.run(main())
```

### 多轮对话

```python
async def multi_turn_conversation():
    session_manager = SessionManager(conn=redis_client)

    # 创建会话
    session = await session_manager.create_session(
        user_id="user_123",
        agent_id="chatbot",
    )

    conversation_history = []

    # 第一轮
    user_message_1 = "What's the weather like?"
    assistant_response_1 = "I'd be happy to help check the weather. Where are you located?"

    conversation_history.extend([
        {"role": "user", "content": user_message_1},
        {"role": "assistant", "content": assistant_response_1},
    ])

    # 保存检查点
    await session_manager.save_checkpoint(
        session.session_id,
        {
            "turn": 1,
            "history": conversation_history,
        },
    )

    # 第二轮
    user_message_2 = "I'm in Beijing"
    assistant_response_2 = "The weather in Beijing is currently sunny with a high of 25°C."

    conversation_history.extend([
        {"role": "user", "content": user_message_2},
        {"role": "assistant", "content": assistant_response_2},
    ])

    # 保存最终检查点
    await session_manager.save_checkpoint(
        session.session_id,
        {
            "turn": 2,
            "history": conversation_history,
            "complete": True,
        },
    )

asyncio.run(multi_turn_conversation())
```

### 会话过期处理

```python
async def handle_session_expiry():
    session_manager = SessionManager(
        conn=redis_client,
        ttl=60,  # 1分钟过期（用于测试）
    )

    # 创建会话
    session = await session_manager.create_session(
        user_id="user_123",
        agent_id="chatbot",
    )

    # 立即访问 - 成功
    retrieved = await session_manager.get_session(session.session_id)
    print(f"Immediate access: {retrieved is not None}")  # True

    # 等待过期
    await asyncio.sleep(61)

    # 过期后访问 - 失败
    retrieved = await session_manager.get_session(session.session_id)
    print(f"After expiry: {retrieved is not None}")  # False

asyncio.run(handle_session_expiry())
```

### 批量操作

```python
async def batch_operations():
    session_manager = SessionManager(conn=redis_client)

    # 批量创建会话
    tasks = []
    for i in range(10):
        task = session_manager.create_session(
            user_id=f"user_{i}",
            agent_id="chatbot",
        )
        tasks.append(task)

    sessions = await asyncio.gather(*tasks)
    print(f"Created {len(sessions)} sessions")

    # 获取特定用户的所有会话
    user_sessions = await session_manager.get_sessions_by_user("user_5")
    print(f"User 5 has {len(user_sessions)} sessions")

asyncio.run(batch_operations())
```

## 性能考虑

### 连接池

```python
# 使用连接池提高性能
pool = redis.ConnectionPool(
    host='localhost',
    port=6379,
    max_connections=50,
)

redis_client = redis.Redis(connection_pool=pool)
session_manager = SessionManager(conn=redis_client)
```

### 批量操作

```python
# 批量创建更高效
async def batch_create():
    session_manager = SessionManager(conn=redis_client)

    tasks = [
        session_manager.create_session(f"user_{i}", "chatbot")
        for i in range(100)
    ]

    sessions = await asyncio.gather(*tasks)
    return sessions
```

### 缓存策略

```python
from functools import lru_cache

class CachedSessionManager(SessionManager):
    def __init__(self, *args, cache_size=100, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache = {}

    async def get_session(self, session_id: str):
        # 检查缓存
        if session_id in self._cache:
            return self._cache[session_id]

        # 从 Redis 获取
        session = await super().get_session(session_id)

        # 缓存结果
        if session:
            self._cache[session_id] = session

        return session
```

## 相关文档

- [AgentExecutor API](executor.md) - 执行器 API
- [AgentContext API](context.md) - 上下文 API
- [EventBus API](event-bus.md) - 事件总线 API
- [会话管理概念](../concepts/session.md) - 会话管理概念

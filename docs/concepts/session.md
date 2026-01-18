# 会话管理

本文档详细介绍 Qingyu Backend AI 的会话管理系统。

## 概述

会话管理负责跟踪用户与 Agent 之间的交互状态，支持多轮对话、状态持久化和上下文保持。

### 核心功能

- **会话创建**: 为用户和 Agent 创建唯一会话
- **状态持久化**: 保存和恢复会话状态
- **检查点管理**: 在关键点保存会话快照
- **自动过期**: 自动清理过期会话
- **并发安全**: 支持多用户并发访问

## SessionManager

### 基本用法

```python
from src.agent_runtime.session_manager import SessionManager

# 创建会话管理器
session_manager = SessionManager(
    conn=redis_client,  # Redis 连接
    ttl=3600,          # 会话过期时间（秒）
)

# 创建会话
session = await session_manager.create_session(
    user_id="user_123",
    agent_id="chatbot",
)
```

### 会话属性

```python
from src.agent_runtime.session_manager import Session

# Session 对象包含：
session.session_id      # 唯一会话ID
session.user_id         # 用户ID
session.agent_id        # Agent ID
session.created_at      # 创建时间
session.expires_at      # 过期时间
session.metadata        # 元数据
```

## 会话操作

### 创建会话

```python
# 基本创建
session = await session_manager.create_session(
    user_id="user_123",
    agent_id="assistant",
)

# 带元数据创建
session = await session_manager.create_session(
    user_id="user_123",
    agent_id="assistant",
    metadata={
        "language": "zh-CN",
        "timezone": "Asia/Shanghai",
        "tier": "premium",
    },
)
```

### 检索会话

```python
# 通过 session_id 获取
session = await session_manager.get_session("sess_abc123")

if session:
    print(f"User: {session.user_id}")
    print(f"Agent: {session.agent_id}")
else:
    print("Session not found or expired")
```

### 更新会话

```python
# 更新元数据
await session_manager.update_session_metadata(
    session_id="sess_abc123",
    metadata={
        "last_activity": "2025-01-17T10:30:00Z",
        "message_count": 5,
    },
)

# 刷新过期时间
await session_manager.refresh_session("sess_abc123")
```

### 删除会话

```python
# 删除单个会话
await session_manager.delete_session("sess_abc123")

# 删除用户所有会话
await session_manager.delete_user_sessions("user_123")

# 删除 Agent 所有会话
await session_manager.delete_agent_sessions("chatbot")
```

### 查询会话

```python
# 获取用户的所有会话
sessions = await session_manager.get_sessions_by_user("user_123")

for session in sessions:
    print(f"{session.session_id}: {session.agent_id}")

# 获取活跃会话数
count = await session_manager.get_active_session_count("user_123")

# 检查会话是否存在
exists = await session_manager.session_exists("sess_abc123")
```

## 检查点管理

### 创建检查点

```python
# 保存检查点
checkpoint_id = await session_manager.save_checkpoint(
    session_id="sess_abc123",
    data={
        "conversation_state": "active",
        "last_message": "Hello!",
        "context": {
            "topic": "greeting",
            "turn": 1,
        },
        "history": [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ],
    },
)

print(f"Checkpoint saved: {checkpoint_id}")
```

### 检索检查点

```python
# 获取最新检查点
checkpoint = await session_manager.get_latest_checkpoint("sess_abc123")

# 获取特定检查点
checkpoint = await session_manager.get_checkpoint(
    session_id="sess_abc123",
    checkpoint_id="ckpt_xyz789",
)

if checkpoint:
    print(f"State: {checkpoint['data']['conversation_state']}")
    print(f"History: {checkpoint['data']['history']}")
```

### 管理检查点

```python
# 列出所有检查点
checkpoints = await session_manager.list_checkpoints("sess_abc123")

for cp in checkpoints:
    print(f"{cp['checkpoint_id']}: {cp['created_at']}")

# 删除检查点
await session_manager.delete_checkpoint(
    session_id="sess_abc123",
    checkpoint_id="ckpt_xyz789",
)

# 清除所有检查点
await session_manager.clear_checkpoints("sess_abc123")
```

## 会话状态

### 状态类型

```python
from enum import Enum

class SessionState(Enum):
    ACTIVE = "active"       # 活跃
    IDLE = "idle"          # 空闲
    ARCHIVED = "archived"   # 已归档
    EXPIRED = "expired"     # 已过期
```

### 状态管理

```python
# 设置会话状态
await session_manager.set_session_state(
    session_id="sess_abc123",
    state=SessionState.IDLE,
)

# 获取会话状态
state = await session_manager.get_session_state("sess_abc123")

# 自动状态转换
async def update_session_activity(session_id):
    # 获取会话
    session = await session_manager.get_session(session_id)

    # 更新活动时间
    await session_manager.update_session_metadata(
        session_id,
        {"last_activity": datetime.now().isoformat()},
    )

    # 激活会话
    await session_manager.set_session_state(
        session_id,
        SessionState.ACTIVE,
    )
```

## 多轮对话

### 保存对话历史

```python
async def multi_turn_conversation():
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
            "pending_question": "location",
        },
    )

    # 第二轮
    user_message_2 = "I'm in Beijing"
    assistant_response_2 = "The weather in Beijing is currently sunny with a high of 25°C."

    conversation_history.extend([
        {"role": "user", "content": user_message_2},
        {"role": "assistant", "content": assistant_response_2},
    ])

    # 保存最终状态
    await session_manager.save_checkpoint(
        session.session_id,
        {
            "turn": 2,
            "history": conversation_history,
            "complete": True,
        },
    )
```

### 恢复对话

```python
async def resume_conversation(session_id):
    # 获取最新检查点
    checkpoint = await session_manager.get_latest_checkpoint(session_id)

    if not checkpoint:
        print("No previous conversation found")
        return

    history = checkpoint["data"]["history"]
    turn = checkpoint["data"]["turn"]

    print(f"Resuming from turn {turn}")
    print("History:")
    for msg in history:
        print(f"  {msg['role']}: {msg['content']}")

    # 继续对话...
```

## 会话模板

### 初始化模板

```python
# 为特定 Agent 创建带模板的会话
async def create_templated_session():
    # 定义会话模板
    template = {
        "system_prompt": "You are a helpful Chinese assistant.",
        "context": {
            "language": "zh-CN",
            "tone": "friendly",
        },
        "capabilities": ["translation", "qa", "creative"],
    }

    # 创建会话
    session = await session_manager.create_session(
        user_id="user_123",
        agent_id="translator",
        metadata={"template": template},
    )

    return session
```

### 恢复模板会话

```python
async def restore_from_template(session_id):
    session = await session_manager.get_session(session_id)

    if not session or "template" not in session.metadata:
        return None

    template = session.metadata["template"]

    # 使用模板配置 Agent
    config = AgentConfig(
        name=session.agent_id,
        description=f"Agent with template: {template.get('system_prompt')}",
        system_prompt=template["system_prompt"],
    )

    return config
```

## 并发处理

### 并发会话访问

```python
import asyncio

async def handle_concurrent_requests(user_id, agent_id):
    # 创建多个会话
    tasks = []
    for i in range(5):
        task = session_manager.create_session(
            user_id=user_id,
            agent_id=agent_id,
        )
        tasks.append(task)

    # 并发创建
    sessions = await asyncio.gather(*tasks)

    print(f"Created {len(sessions)} concurrent sessions")
    return sessions
```

### 会话锁定

```python
# 防止并发修改同一会话
async def safe_session_update(session_id, update_func):
    # 获取锁
    lock = await session_manager.acquire_lock(session_id)

    try:
        # 执行更新
        session = await session_manager.get_session(session_id)
        updated_session = await update_func(session)
        await session_manager.update_session(session_id, updated_session)
    finally:
        # 释放锁
        await session_manager.release_lock(session_id, lock)
```

## 性能优化

### 批量操作

```python
# 批量创建会话
async def batch_create_sessions(users_data):
    tasks = [
        session_manager.create_session(
            user_id=data["user_id"],
            agent_id=data["agent_id"],
            metadata=data.get("metadata"),
        )
        for data in users_data
    ]

    sessions = await asyncio.gather(*tasks)
    return sessions

# 批量删除
async def batch_delete_sessions(session_ids):
    tasks = [
        session_manager.delete_session(sid)
        for sid in session_ids
    ]

    await asyncio.gather(*tasks)
```

### 缓存策略

```python
from functools import lru_cache

class CachedSessionManager(SessionManager):
    def __init__(self, *args, cache_size=100, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache = {}

    async def get_session(self, session_id):
        # 检查缓存
        if session_id in self._cache:
            return self._cache[session_id]

        # 从存储获取
        session = await super().get_session(session_id)

        # 缓存结果
        if session:
            self._cache[session_id] = session

        return session

    async def update_session(self, session_id, session):
        # 更新存储
        await super().update_session(session_id, session)

        # 更新缓存
        self._cache[session_id] = session
```

## 监控和维护

### 会话统计

```python
# 获取统计信息
async def get_session_stats():
    stats = {
        "total_sessions": await session_manager.get_total_session_count(),
        "active_sessions": await session_manager.get_active_session_count(),
        "expired_sessions": await session_manager.get_expired_session_count(),
        "avg_session_duration": await session_manager.get_avg_session_duration(),
    }

    return stats
```

### 清理过期会话

```python
# 自动清理任务
async def cleanup_expired_sessions():
    while True:
        # 清理过期会话
        cleaned = await session_manager.cleanup_expired_sessions()

        print(f"Cleaned {cleaned} expired sessions")

        # 每小时执行一次
        await asyncio.sleep(3600)
```

### 监控会话活动

```python
async def monitor_session_activity():
    # 获取活跃会话
    active_sessions = await session_manager.get_all_active_sessions()

    for session in active_sessions:
        # 检查活动时间
        last_activity = session.metadata.get("last_activity")
        if last_activity:
            activity_time = datetime.fromisoformat(last_activity)
            idle_time = datetime.now() - activity_time

            # 标记长时间空闲的会话
            if idle_time > timedelta(minutes=30):
                await session_manager.set_session_state(
                    session.session_id,
                    SessionState.IDLE,
                )
```

## 安全考虑

### 会话验证

```python
async def validate_session_access(session_id, user_id):
    session = await session_manager.get_session(session_id)

    if not session:
        raise ValueError("Session not found")

    if session.user_id != user_id:
        raise PermissionError("User does not own this session")

    return session
```

### 敏感数据处理

```python
import json

async def save_checkpoint_safe(session_id, data):
    # 移除敏感数据
    safe_data = data.copy()

    if "api_key" in safe_data:
        del safe_data["api_key"]

    if "password" in safe_data:
        del safe_data["password"]

    # 序列化时加密
    encrypted = encrypt(json.dumps(safe_data))

    await session_manager.save_checkpoint(
        session_id,
        {"encrypted_data": encrypted},
    )
```

## 最佳实践

### 1. 定期保存检查点

```python
async def auto_checkpoint_interval(session_id, interval=5):
    """每隔 N 轮对话自动保存检查点"""
    while True:
        await asyncio.sleep(interval)
        # 保存当前状态
        # ...
```

### 2. 限制会话数量

```python
async def enforce_session_limit(user_id, max_sessions=5):
    """限制每个用户的最大会话数"""
    sessions = await session_manager.get_sessions_by_user(user_id)

    if len(sessions) >= max_sessions:
        # 删除最旧的会话
        oldest_session = min(sessions, key=lambda s: s.created_at)
        await session_manager.delete_session(oldest_session.session_id)
```

### 3. 会话恢复策略

```python
async def restore_or_create_session(user_id, agent_id):
    """尝试恢复现有会话，否则创建新的"""
    sessions = await session_manager.get_sessions_by_user(user_id)

    # 查找活跃会话
    active = [s for s in sessions if s.agent_id == agent_id]

    if active:
        # 恢复最新的会话
        return active[0]
    else:
        # 创建新会话
        return await session_manager.create_session(user_id, agent_id)
```

## 相关文档

- [系统架构](architecture.md) - 了解会话管理在架构中的位置
- [Agent 生命周期](lifecycle.md) - 会话与 Agent 执行的关系
- [检查点存储](../deployment/storage.md) - 持久化存储配置

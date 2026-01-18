# 快速开始指南

本指南将帮助您在 5 分钟内创建并运行第一个 Agent。

## 前提条件

确保您已完成 [安装指南](installation.md) 中的所有步骤：

- ✅ Python 3.10+ 已安装
- ✅ 依赖已安装 (`uv sync` 或 `pip install -e .`)
- ✅ Redis 服务正在运行
- ✅ 环境变量已配置

## 第一步：创建简单的 Agent

创建文件 `my_first_agent.py`:

```python
import asyncio
from src.common.types.agent_types import AgentConfig, AgentContext
from src.agent_runtime.orchestration.executor import AgentExecutor
from src.agent_runtime.session_manager import SessionManager
from src.middleware.basic_middleware import LoggingMiddleware
from src.middleware.pipeline import MiddlewarePipeline


async def main():
    # 1. 创建 Agent 配置
    config = AgentConfig(
        name="hello_agent",
        description="A friendly agent that says hello",
        model="gpt-3.5-turbo",
        temperature=0.7,
    )

    # 2. 创建执行器
    executor = AgentExecutor(
        agent_id=config.name,
        config=config,
    )

    # 3. 创建会话
    session_manager = SessionManager(conn=None, ttl=3600)
    session = await session_manager.create_session(
        user_id="user_001",
        agent_id="hello_agent",
    )

    # 4. 创建执行上下文
    context = AgentContext(
        agent_id="hello_agent",
        user_id="user_001",
        session_id=session.session_id,
        current_task="Say hello to the world!",
    )

    # 5. 执行 Agent
    result = await executor.execute(context)

    # 6. 输出结果
    print("=== Agent Response ===")
    print(f"Success: {result.success}")
    print(f"Output: {result.output}")
    if result.error:
        print(f"Error: {result.error}")


if __name__ == "__main__":
    asyncio.run(main())
```

## 第二步：运行 Agent

```bash
uv run python my_first_agent.py
```

预期输出：

```
=== Agent Response ===
Success: True
Output: Hello! How can I assist you today?
```

## 第三步：添加中间件

让我们添加一些中间件来增强 Agent 的功能：

```python
import asyncio
from src.common.types.agent_types import AgentConfig, AgentContext
from src.agent_runtime.orchestration.executor import AgentExecutor
from src.agent_runtime.session_manager import SessionManager
from src.middleware.basic_middleware import LoggingMiddleware, AuthMiddleware
from src.middleware.pipeline import MiddlewarePipeline


async def main():
    # 1. 创建配置
    config = AgentConfig(
        name="enhanced_agent",
        description="Agent with middleware",
        model="gpt-3.5-turbo",
        temperature=0.7,
    )

    # 2. 创建中间件管道
    pipeline = MiddlewarePipeline()

    # 添加日志中间件
    logging_middleware = LoggingMiddleware(name="logger")
    pipeline.add(logging_middleware)

    # 添加认证中间件
    auth_middleware = AuthMiddleware(name="auth")
    pipeline.add(auth_middleware)

    # 3. 创建执行器并设置中间件
    executor = AgentExecutor(
        agent_id=config.name,
        config=config,
    )
    executor.set_middleware_pipeline(pipeline)

    # 4. 创建会话和上下文
    session_manager = SessionManager(conn=None, ttl=3600)
    session = await session_manager.create_session(
        user_id="user_001",
        agent_id="enhanced_agent",
    )

    context = AgentContext(
        agent_id="enhanced_agent",
        user_id="user_001",
        session_id=session.session_id,
        current_task="What is the capital of France?",
    )

    # 5. 执行
    result = await executor.execute(context)

    print("=== Enhanced Agent Response ===")
    print(f"Output: {result.output}")


if __name__ == "__main__":
    asyncio.run(main())
```

## 第四步：使用事件系统

Agent 运行时会触发各种事件，我们可以监听这些事件：

```python
import asyncio
from src.common.types.agent_types import AgentConfig, AgentContext
from src.agent_runtime.orchestration.executor import AgentExecutor
from src.agent_runtime.session_manager import SessionManager
from src.agent_runtime.event_bus import EventBus, EventType


async def main():
    # 1. 创建事件总线
    event_bus = EventBus()

    # 2. 订阅事件
    async def on_agent_started(event):
        print(f"[EVENT] Agent started: {event.agent_id}")

    async def on_agent_completed(event):
        print(f"[EVENT] Agent completed: {event.agent_id}")
        if event.execution_time_ms:
            print(f"[EVENT] Execution time: {event.execution_time_ms}ms")

    async def on_error(event):
        print(f"[EVENT] Error occurred: {event.error_message}")

    await event_bus.subscribe(EventType.AGENT_STARTED, on_agent_started)
    await event_bus.subscribe(EventType.AGENT_COMPLETED, on_agent_completed)
    await event_bus.subscribe(EventType.ERROR_OCCURRED, on_error)

    # 3. 创建和执行 Agent
    config = AgentConfig(
        name="event_agent",
        description="Agent with event tracking",
        model="gpt-3.5-turbo",
    )

    executor = AgentExecutor(
        agent_id=config.name,
        config=config,
    )
    executor.set_event_bus(event_bus)

    session_manager = SessionManager(conn=None, ttl=3600)
    session = await session_manager.create_session(
        user_id="user_001",
        agent_id="event_agent",
    )

    context = AgentContext(
        agent_id="event_agent",
        user_id="user_001",
        session_id=session.session_id,
        current_task="Calculate 15 + 27",
    )

    result = await executor.execute(context)

    print("\n=== Result ===")
    print(f"Output: {result.output}")


if __name__ == "__main__":
    asyncio.run(main())
```

## 第五步：使用会话检查点

会话检查点允许您保存和恢复 Agent 状态：

```python
import asyncio
from src.common.types.agent_types import AgentConfig, AgentContext
from src.agent_runtime.orchestration.executor import AgentExecutor
from src.agent_runtime.session_manager import SessionManager


async def main():
    session_manager = SessionManager(conn=None, ttl=3600)

    # 创建会话
    session = await session_manager.create_session(
        user_id="user_001",
        agent_id="checkpoint_agent",
    )

    # 第一次执行
    config = AgentConfig(
        name="checkpoint_agent",
        description="Agent with checkpoint support",
        model="gpt-3.5-turbo",
    )

    executor = AgentExecutor(agent_id=config.name, config=config)

    context = AgentContext(
        agent_id="checkpoint_agent",
        user_id="user_001",
        session_id=session.session_id,
        current_task="Remember: My favorite color is blue",
    )

    result1 = await executor.execute(context)
    print(f"First response: {result1.output}")

    # 保存检查点
    checkpoint_data = {
        "memory": "User's favorite color is blue",
        "conversation_history": ["What is your favorite color?", "blue"],
    }

    checkpoint_id = await session_manager.save_checkpoint(
        session.session_id,
        checkpoint_data,
    )
    print(f"Checkpoint saved: {checkpoint_id}")

    # 稍后恢复...
    # 检索检查点
    restored_checkpoint = await session_manager.get_checkpoint(
        session.session_id,
        checkpoint_id,
    )
    print(f"Checkpoint restored: {restored_checkpoint}")


if __name__ == "__main__":
    asyncio.run(main())
```

## 常见用例

### 1. 聊天机器人

```python
# 多轮对话
context = AgentContext(
    agent_id="chat_agent",
    user_id="user_001",
    session_id=session.session_id,
    current_task="Continue our conversation about AI",
    metadata={
        "history": [
            {"role": "user", "content": "What is AI?"},
            {"role": "assistant", "content": "AI is..."},
        ],
    },
)
```

### 2. 代码助手

```python
# 代码生成和调试
context = AgentContext(
    agent_id="code_agent",
    user_id="developer_001",
    session_id=session.session_id,
    current_task="Write a Python function to sort a list",
    metadata={
        "language": "python",
        "style": "pep8",
    },
)
```

### 3. 数据分析

```python
# 数据查询和分析
context = AgentContext(
    agent_id="data_agent",
    user_id="analyst_001",
    session_id=session.session_id,
    current_task="What are the sales trends for Q1?",
    metadata={
        "database": "analytics_db",
        "table": "sales",
        "quarter": "Q1",
    },
)
```

## 故障排查

### 问题 1: "ModuleNotFoundError: No module named 'src'"

**解决方案**:
```bash
# 确保从项目根目录运行
cd Qingyu_backend/python_ai_service
uv run python my_first_agent.py
```

### 问题 2: "Redis connection error"

**解决方案**:
```bash
# 检查 Redis 是否运行
redis-cli ping

# 或使用 Docker 启动
docker run -d -p 6379:6379 redis:7-alpine
```

### 问题 3: "OPENAI_API_KEY not found"

**解决方案**:
```bash
# 在 .env 文件中设置 API 密钥
echo "OPENAI_API_KEY=sk-your-key-here" >> .env
```

## 下一步

恭喜！您已经创建了第一个 Agent。接下来可以：

1. 📖 阅读 [核心概念](../concepts/architecture.md) 了解系统架构
2. 🛡️ 查看 [安全指南](../security/overview.md) 了解安全最佳实践
3. 📚 浏览 [API 参考](../api/executor.md) 了解所有可用功能
4. 🚀 探索 [部署指南](../deployment/production.md) 准备生产环境

## 完整示例

查看 `examples/` 目录获取更多完整的示例：

- `examples/basic_agent.py` - 基本 Agent 示例
- `examples/middleware_example.py` - 中间件使用
- `examples/event_driven.py` - 事件驱动架构
- `examples/multi_agent.py` - 多 Agent 协作

---

**需要帮助？** 查看 [故障排查指南](../guides/troubleshooting.md) 或提交 Issue。

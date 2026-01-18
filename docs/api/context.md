# AgentContext 和 AgentConfig API 参考

AgentContext 和 AgentConfig 是执行 Agent 时的核心数据类型。

## AgentContext

AgentContext 包含执行 Agent 所需的上下文信息。

### 类定义

```python
from src.common.types.agent_types import AgentContext

class AgentContext(BaseModel):
    agent_id: str                      # Agent ID（必需）
    user_id: str                       # 用户 ID（必需）
    session_id: str                    # 会话 ID（必需）
    current_task: str                  # 当前任务（必需）
    metadata: Dict[str, Any] = {}      # 元数据（可选）
    created_at: datetime = None        # 创建时间（可选）
```

### 字段说明

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `agent_id` | str | ✅ | 要执行的 Agent ID |
| `user_id` | str | ✅ | 发起请求的用户 ID |
| `session_id` | str | ✅ | 会话 ID，用于跟踪多轮对话 |
| `current_task` | str | ✅ | 用户请求的任务或问题 |
| `metadata` | dict | ❌ | 额外的元数据信息 |
| `created_at` | datetime | ❌ | 上下文创建时间 |

### 使用示例

#### 基本使用

```python
from src.common.types.agent_types import AgentContext

context = AgentContext(
    agent_id="chatbot",
    user_id="user_123",
    session_id="sess_abc",
    current_task="What is the capital of France?",
)

result = await executor.execute(context)
```

#### 带元数据

```python
context = AgentContext(
    agent_id="translator",
    user_id="user_123",
    session_id="sess_abc",
    current_task="Translate: Hello world",
    metadata={
        "source_language": "en",
        "target_language": "zh",
        "style": "formal",
    },
)
```

#### 多轮对话

```python
# 第一轮
context1 = AgentContext(
    agent_id="chatbot",
    user_id="user_123",
    session_id="sess_abc",
    current_task="My name is Alice",
)

# 第二轮（带历史）
context2 = AgentContext(
    agent_id="chatbot",
    user_id="user_123",
    session_id="sess_abc",  # 使用相同的 session_id
    current_task="What is my name?",
    metadata={
        "history": [
            {"role": "user", "content": "My name is Alice"},
            {"role": "assistant", "content": "Nice to meet you, Alice!"},
        ],
    },
)
```

#### 认证信息

```python
context = AgentContext(
    agent_id="admin_agent",
    user_id="admin_123",
    session_id="sess_admin",
    current_task="List all users",
    metadata={
        "auth_token": "eyJhbGciOi...",
        "user_role": "admin",
        "permissions": ["read", "write", "delete"],
    },
)
```

## AgentConfig

AgentConfig 定义了 Agent 的配置和行为。

### 类定义

```python
from src.common.types.agent_types import AgentConfig

class AgentConfig(BaseModel):
    name: str                          # Agent 名称（必需）
    description: str                   # Agent 描述（必需）
    model: str = "gpt-3.5-turbo"      # 使用的模型
    temperature: float = 0.7           # 温度参数
    max_tokens: int = 1000             # 最大 tokens
    top_p: float = 1.0                 # Top-p 采样
    frequency_penalty: float = 0.0      # 频率惩罚
    presence_penalty: float = 0.0       # 存在惩罚
    stop_sequences: List[str] = []     # 停止序列
    system_prompt: str = None          # 系统提示词
    timeout: int = 30                  # 超时时间（秒）
    retry_attempts: int = 3            # 重试次数
    retry_delay: float = 1.0           # 重试延迟（秒）
```

### 字段说明

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | str | - | Agent 唯一标识符（必需） |
| `description` | str | - | Agent 描述（必需） |
| `model` | str | "gpt-3.5-turbo" | 使用的 LLM 模型 |
| `temperature` | float | 0.7 | 输出随机性（0.0-1.0） |
| `max_tokens` | int | 1000 | 最大输出 tokens |
| `top_p` | float | 1.0 | Top-p 采样参数 |
| `frequency_penalty` | float | 0.0 | 频率惩罚（-2.0 到 2.0） |
| `presence_penalty` | float | 0.0 | 存在惩罚（-2.0 到 2.0） |
| `stop_sequences` | list | [] | 停止生成的序列 |
| `system_prompt` | str | None | 系统提示词 |
| `timeout` | int | 30 | 请求超时时间（秒） |
| `retry_attempts` | int | 3 | 失败重试次数 |
| `retry_delay` | float | 1.0 | 重试之间的延迟（秒） |

### 使用示例

#### 基本配置

```python
from src.common.types.agent_types import AgentConfig

config = AgentConfig(
    name="chatbot",
    description="A helpful chatbot assistant",
)

executor = AgentExecutor(agent_id="chatbot", config=config)
```

#### 高级配置

```python
config = AgentConfig(
    name="creative_writer",
    description="A creative writing assistant",
    model="gpt-4",
    temperature=0.9,          # 更有创造力
    max_tokens=2000,          # 更长的输出
    frequency_penalty=0.5,    # 减少重复
    presence_penalty=0.3,     # 增加多样性
    system_prompt="You are a creative writer specializing in short stories.",
)
```

#### 代码助手配置

```python
config = AgentConfig(
    name="code_assistant",
    description="A coding assistant",
    model="gpt-4",
    temperature=0.2,          # 更确定性
    max_tokens=1500,
    stop_sequences=["```", "END"],  # 停止序列
    system_prompt="""You are a coding assistant. Provide clear, concise code examples.
    Always include comments explaining the code.""",
)
```

#### 中文助手配置

```python
config = AgentConfig(
    name="chinese_assistant",
    description="中文助手",
    model="gpt-3.5-turbo",
    temperature=0.7,
    system_prompt="你是一个友好的中文助手。用简体中文回答问题。",
)
```

### 参数详解

#### temperature

控制输出的随机性：

- `0.0` - 完全确定性，相同输入总是产生相同输出
- `0.7` - 平衡创造性和一致性（推荐）
- `1.0` - 更随机和有创造性
- `1.5+` - 非常有创造性，但可能不连贯

```python
# 创意写作
creative_config = AgentConfig(
    name="writer",
    description="Creative writer",
    temperature=0.9,  # 高创造力
)

# 代码生成
code_config = AgentConfig(
    name="coder",
    description="Code generator",
    temperature=0.2,  # 低随机性，更精确
)

# 问答助手
qa_config = AgentConfig(
    name="qa_bot",
    description="Q&A assistant",
    temperature=0.5,  # 平衡
)
```

#### max_tokens

控制最大输出长度：

```python
# 简短回答
short_config = AgentConfig(
    name="short_answer",
    max_tokens=100,  # 约 75 个单词
)

# 长篇内容
long_config = AgentConfig(
    name="long_form",
    max_tokens=4000,  # 约 3000 个单词
)
```

#### frequency_penalty 和 presence_penalty

控制重复性：

```python
# 减少重复
config = AgentConfig(
    name="diverse_writer",
    frequency_penalty=0.8,  # 惩罚频繁出现的词
    presence_penalty=0.6,   # 鼓励谈论新话题
)
```

#### stop_sequences

定义停止生成的序列：

```python
config = AgentConfig(
    name="structured_output",
    stop_sequences=["\n\n\n", "END", "###"],  # 多个停止序列
)
```

#### system_prompt

定义 Agent 的行为和角色：

```python
# 简单系统提示
config = AgentConfig(
    name="assistant",
    system_prompt="You are a helpful assistant.",
)

# 复杂系统提示
config = AgentConfig(
    name="specialist",
    system_prompt="""You are a specialized assistant for technical documentation.

    Guidelines:
    - Be clear and concise
    - Use proper formatting
    - Provide code examples when relevant
    - Always explain technical terms

    If you don't know something, admit it rather than guessing.""",
)
```

### 配置模板

#### 对话式 Agent

```python
def get_chatbot_config() -> AgentConfig:
    return AgentConfig(
        name="chatbot",
        description="Friendly chatbot",
        model="gpt-3.5-turbo",
        temperature=0.7,
        max_tokens=500,
        system_prompt="You are a friendly and helpful assistant. Be conversational and engaging.",
    )
```

#### 专业领域 Agent

```python
def get_legal_assistant_config() -> AgentConfig:
    return AgentConfig(
        name="legal_assistant",
        description="Legal document assistant",
        model="gpt-4",
        temperature=0.3,  # 更精确
        max_tokens=2000,
        system_prompt="""You are a legal assistant. Help with legal documents and questions.
        Always include a disclaimer that you are not a lawyer and this is not legal advice.""",
    )
```

#### 创意写作 Agent

```python
def get_creative_writer_config() -> AgentConfig:
    return AgentConfig(
        name="creative_writer",
        description="Creative writing assistant",
        model="gpt-4",
        temperature=0.9,  # 高创造力
        max_tokens=3000,
        frequency_penalty=0.5,
        presence_penalty=0.5,
        system_prompt="You are a creative writer. Be imaginative and vivid in your descriptions.",
    )
```

### 配置验证

```python
from pydantic import ValidationError

try:
    config = AgentConfig(
        name="test",
        description="Test agent",
        temperature=1.5,  # 无效值
    )
except ValidationError as e:
    print(f"Invalid config: {e}")
```

## AgentResult

Agent 执行的结果。

### 类定义

```python
class AgentResult(BaseModel):
    success: bool                      # 是否成功
    output: str = ""                   # 输出内容
    error: str = ""                    # 错误消息
    metadata: Dict[str, Any] = {}      # 元数据
    tokens_used: int = 0               # 使用的 tokens
    execution_time_ms: int = 0         # 执行时间（毫秒）
```

### 使用示例

```python
result = await executor.execute(context)

if result.success:
    print(f"Output: {result.output}")
    print(f"Tokens: {result.tokens_used}")
    print(f"Time: {result.execution_time_ms}ms")
else:
    print(f"Error: {result.error}")
    print(f"Error type: {result.metadata.get('error_type')}")
```

## 相关文档

- [AgentExecutor API](executor.md) - 执行器 API
- [SessionManager API](session-manager.md) - 会话管理 API
- [Agent 生命周期](../concepts/lifecycle.md) - Agent 生命周期概念

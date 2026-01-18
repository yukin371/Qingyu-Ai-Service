# LangChain 1.0 迁移指南

> **文档版本**: v1.0  
> **创建时间**: 2025-11-05  
> **适用版本**: LangChain 0.1.x → 1.0.0

---

## 📋 概述

本迁移指南帮助您从 LangChain 0.1.x 迁移到 LangChain 1.0，涵盖所有破坏性变更和新特性。

---

## 🎯 主要变更

### 1. 依赖包升级

**旧版本 (0.1.x)**:
```txt
langchain==0.1.0
langchain-core==0.1.10
langchain-openai==0.0.2
langchain-anthropic==0.0.1
langgraph==0.0.20
```

**新版本 (1.0)**:
```txt
langchain==1.0.0
langchain-core==1.0.0
langchain-openai==1.0.0
langchain-anthropic==1.0.0
langchain-community==1.0.0
langgraph==1.0.0
langgraph-checkpoint-postgres==1.0.0
```

### 2. Agent 接口变更

#### 旧方式（AgentExecutor）

```python
from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4")
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)

result = agent_executor.invoke({"input": "任务描述"})
```

#### 新方式（create_agent）

```python
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4")

# 统一的 create_agent 接口
agent = create_agent(
    llm=llm,
    tools=tools,
    agent_type="react",  # 或 "openai-tools", "xml", "structured-chat"
    checkpointer=checkpointer,  # 可选：持久化
    middleware=[logging_mw, metrics_mw]  # 可选：中间件
)

# 异步调用
result = await agent.ainvoke({"input": "任务描述"})
```

### 3. Middleware 机制

#### 新增 Middleware 支持

```python
from core.agents.middleware import (
    LoggingMiddleware,
    MetricsMiddleware,
    ToolWrapperMiddleware,
    ErrorHandlingMiddleware
)

agent = create_agent(
    llm=llm,
    tools=tools,
    middleware=[
        LoggingMiddleware(),        # 日志记录
        MetricsMiddleware(),        # 指标收集
        ToolWrapperMiddleware(),    # 工具调用包装
        ErrorHandlingMiddleware()   # 错误处理
    ]
)
```

### 4. Checkpointer 持久化

#### 新增持久化能力

```python
from core.agents.checkpointers import PostgresCheckpointer

# 创建 Checkpointer
checkpointer = PostgresCheckpointer()

agent = create_agent(
    llm=llm,
    tools=tools,
    checkpointer=checkpointer  # 启用持久化
)

# 执行（自动保存检查点）
result = await agent.ainvoke(
    {"input": "任务"},
    config={
        "configurable": {
            "thread_id": "user123_session001"  # 会话 ID
        }
    }
)

# 如果中断，可以恢复
continued = await agent.ainvoke(
    None,  # 输入为 None，从 checkpoint 恢复
    config={"configurable": {"thread_id": "user123_session001"}}
)
```

### 5. 多 LLM 供应商支持

#### 新增 Provider Factory

```python
from core.llm.providers import LLMProviderFactory

# OpenAI Provider
openai_provider = LLMProviderFactory.create(
    provider="openai",
    model="gpt-4-turbo-preview"
)

# Anthropic Provider
anthropic_provider = LLMProviderFactory.create(
    provider="anthropic",
    model="claude-3-opus-20240229"
)

# 使用 Provider
response = await openai_provider.generate(messages)
```

#### 配置驱动切换

```yaml
# config.yaml
llm:
  default_provider: "openai"  # 或 "anthropic"
  default_model: "gpt-4-turbo-preview"
```

### 6. LangGraph 工作流变更

#### 旧方式

```python
from langgraph.graph import StateGraph

workflow = StateGraph(StateType)
workflow.add_node("node1", node1_func)
workflow.add_edge("node1", "node2")

app = workflow.compile()
```

#### 新方式（带持久化）

```python
from langgraph.graph import StateGraph
from core.agents.checkpointers import PostgresCheckpointer

checkpointer = PostgresCheckpointer()

workflow = StateGraph(StateType)
workflow.add_node("node1", node1_func)
workflow.add_edge("node1", "node2")

# 编译时传入 checkpointer
app = workflow.compile(checkpointer=checkpointer)
```

---

## 🔧 迁移步骤

### Step 1: 更新依赖

```bash
# 1. 备份当前环境
pip freeze > requirements_old.txt

# 2. 卸载旧版本
pip uninstall langchain langchain-core langchain-openai langchain-anthropic langgraph -y

# 3. 安装新版本
pip install -r requirements.txt

# 4. 验证安装
python -c "import langchain; print(langchain.__version__)"
```

### Step 2: 更新 Agent 代码

**查找所有使用旧 API 的代码**:
```bash
grep -r "AgentExecutor" src/
grep -r "create_react_agent" src/
```

**替换为新 API**:
- `AgentExecutor` → `create_agent()`
- `create_react_agent()` → `create_agent(agent_type="react")`

### Step 3: 添加 Middleware

在所有 Agent 创建处添加 Middleware:

```python
from core.agents.middleware import LoggingMiddleware, MetricsMiddleware

agent = create_agent(
    llm=llm,
    tools=tools,
    middleware=[LoggingMiddleware(), MetricsMiddleware()]
)
```

### Step 4: 集成 Checkpointer

对于需要持久化的 Agent:

```python
from core.agents.checkpointers import PostgresCheckpointer

checkpointer = PostgresCheckpointer()

agent = create_agent(
    llm=llm,
    tools=tools,
    checkpointer=checkpointer
)
```

### Step 5: 测试验证

```bash
# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 验证 Checkpointer
pytest tests/integration/test_checkpointer.py
```

---

## 🐛 常见问题

### Q1: ImportError: cannot import name 'AgentExecutor'

**原因**: LangChain 1.0 移除了 `AgentExecutor`

**解决方案**: 使用 `create_agent()` 替代

```python
# 旧代码
from langchain.agents import AgentExecutor
executor = AgentExecutor(agent=agent, tools=tools)

# 新代码
from langchain.agents import create_agent
agent = create_agent(llm=llm, tools=tools)
```

### Q2: langgraph-checkpoint-postgres 未安装

**原因**: 持久化功能需要额外安装

**解决方案**:
```bash
pip install langgraph-checkpoint-postgres
```

### Q3: PostgreSQL 连接失败

**原因**: 未配置 PostgreSQL 连接信息

**解决方案**: 在 `.env` 中配置:
```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DATABASE=qingyu_ai
```

### Q4: Middleware 不生效

**原因**: Middleware 需要在 `create_agent()` 时传入

**解决方案**:
```python
agent = create_agent(
    llm=llm,
    tools=tools,
    middleware=[YourMiddleware()]  # 确保传入
)
```

---

## 📊 迁移检查清单

### 依赖升级
- [ ] 更新 `requirements.txt`
- [ ] 更新 `pyproject.toml`
- [ ] 安装新依赖包
- [ ] 验证版本正确

### 代码迁移
- [ ] 替换 `AgentExecutor` 为 `create_agent()`
- [ ] 替换 `create_react_agent()` 为 `create_agent(agent_type="react")`
- [ ] 移除已弃用的 `LLMChain`
- [ ] 更新 LangGraph 工作流代码

### 新特性集成
- [ ] 添加 Middleware 层
- [ ] 集成 Checkpointer 持久化
- [ ] 配置多 LLM 供应商
- [ ] 更新配置文件

### 测试验证
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] Checkpointer 功能验证
- [ ] Middleware 功能验证
- [ ] 性能测试通过

---

## 🔗 相关资源

- [LangChain 1.0 官方文档](https://python.langchain.com/docs/)
- [LangGraph 1.0 文档](https://langchain-ai.github.io/langgraph/)
- [LangChain 1.0 发布说明](https://blog.langchain.dev/)
- [项目架构设计文档](doc/design/ai/LangChain_1.0_架构设计.md)

---

**最后更新**: 2025-11-05  
**维护者**: AI 架构组


# LangGraph 工作流 v2.0 - 基于 LangChain 1.0

> **版本**: v2.0  
> **创建时间**: 2025-11-05  
> **基于**: LangChain 1.0 + LangGraph 1.0

---

## 概述

本目录包含基于 LangChain 1.0 重构的 LangGraph 工作流，集成了所有新特性：
- ✅ 统一 Agent 接口 (create_agent)
- ✅ Middleware 机制
- ✅ Checkpointer 持久化
- ✅ 多 LLM 供应商支持

---

## 工作流列表

### 1. A2A 创作流水线 v2.0

**文件**: `a2a_pipeline_v2_unified.py`

**特性**:
- 集成所有新特性
- 支持工作流中断恢复
- 完整的可观测性
- 多 LLM 供应商支持

**节点**:
1. Planner Agent - 规划任务
2. Outline Agent - 生成大纲
3. Character Agent - 创建角色
4. Plot Agent - 构建情节
5. Review Agent v2 - 深度审核
6. Meta Scheduler - 智能修正

**使用示例**:
```python
from workflows.a2a_pipeline_v2_unified import create_a2a_pipeline_v2

# 创建流水线
pipeline = await create_a2a_pipeline_v2()

# 执行
result = await pipeline.ainvoke(
    initial_state,
    config={"configurable": {"thread_id": "session_001"}}
)

# 恢复执行
continued = await pipeline.ainvoke(
    None,
    config={"configurable": {"thread_id": "session_001"}}
)
```

### 2. Creative Workflow v2.0

**文件**: `creative_v2_unified.py`

**特性**:
- 简化的创作工作流
- 理解 → RAG → 生成 → 审核
- 支持流式输出

---

## 架构变更

### 旧版本 (v1.0)

```python
from langgraph.graph import StateGraph

workflow = StateGraph(StateType)
workflow.add_node("node1", node1_func)
app = workflow.compile()
```

### 新版本 (v2.0)

```python
from langgraph.graph import StateGraph
from core.agents.checkpointers import PostgresCheckpointer

checkpointer = PostgresCheckpointer()

workflow = StateGraph(StateType)
workflow.add_node("node1", node1_func)

# 编译时传入 checkpointer
app = workflow.compile(checkpointer=checkpointer)
```

---

## 最佳实践

1. **始终使用 Checkpointer**: 所有生产工作流应启用持久化
2. **配置 thread_id**: 确保每个会话有唯一的 thread_id
3. **使用 Middleware**: 日志和指标应默认启用
4. **错误处理**: 使用 ErrorHandlingMiddleware 自动重试

---

## 相关文档

- [BaseAgentUnified 文档](../base_agent_unified.py)
- [Middleware 文档](../middleware/README.md)
- [Checkpointer 文档](../checkpointers/README.md)

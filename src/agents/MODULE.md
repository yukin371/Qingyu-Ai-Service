# Agents

> 最后更新：2026-03-29

## 职责

LangGraph Agent 工作流引擎，管理写作 AI 的多 Agent 协作（大纲/角色/情节生成、审核、元调度）。不管理 HTTP 端点（由 api/ 负责）和 LLM 调用（由 core/llm/ 负责）。

## 数据流

```
API Request → AgentService → AgentWorkflowV2 (LangGraph StateGraph)
                                ↓
                         OutlineAgent / CharacterAgent / PlotAgent
                                ↓
                         ReviewAgentV2（审核 → 通过/打回）
                                ↓
                         MetaScheduler（元调度，决定下一步）
                                ↓
                         END 或继续循环
```

## 约定 & 陷阱

- **LangGraph 状态流转**：`PipelineStateV2` 是全局状态，在节点间传递，状态字段变更会影响后续所有节点
- **反思循环**：ReviewAgent 审核不通过时会将结果打回给上一个 Agent 重新生成，`max_retries` 控制最大循环次数
- **路由器函数**：`routers_v2.py` 中的路由函数决定工作流分支走向（`review_router`、`meta_scheduler_router`），修改路由逻辑需理解完整流程
- **Node 适配器**：每个 Agent 的 `execute` 方法被适配为 LangGraph 节点函数，签名必须兼容 StateGraph

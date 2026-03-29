# API

> 最后更新：2026-03-29

## 职责

FastAPI 端点层，暴露 HTTP 接口（聊天/写作辅助/配额管理/健康检查/go_backend gRPC 代理）。不包含 Agent 工作流逻辑。

## 数据流

```
FastAPI Router → Pydantic Model → AgentService → Agent Workflow → LLM
                     ↓
              ChatResponse / SSE Stream
```

## 约定 & 陷阱

- **SSE 流式响应**：chat 端点使用 Server-Sent Events 流式返回 AI 生成内容，前端 `useAIStream` composable 对接
- **配额检查**：`quota.py` 在请求处理前检查用户配额，超限返回 429
- **go_backend 代理**：`api/go_backend/` 目录包含与 Go 后端 gRPC 通信的代理端点
- **Pydantic 模型**：`api/models/` 下的请求/响应模型必须与 Go 后端的 proto 定义保持一致

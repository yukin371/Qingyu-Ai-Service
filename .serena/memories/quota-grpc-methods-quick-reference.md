# 配额管理 gRPC 方法快速参考

## 概述
本文档提供 AI 服务中三个配额管理 gRPC 方法的快速参考。

## RPC 方法列表

### 1. ConsumeQuota
**用途**：记录用户的 AI 服务配额消费

**请求**：`QuotaConsumptionRequest`
- `user_id` (string, required): 用户 ID
- `workflow_type` (string, required): 工作流类型 (chat, writing, creative)
- `tokens_used` (int32, required): 使用的 token 数量
- `metadata` (map<string, string>, optional): 额外的元数据

**响应**：`QuotaConsumptionResponse`
- `success` (bool): 是否成功
- `message` (string): 响应消息
- `record_id` (int64): 记录 ID

**示例调用**：
```python
response = await stub.ConsumeQuota(ai_service_pb2.QuotaConsumptionRequest(
    user_id="user123",
    workflow_type="writing",
    tokens_used=1500,
    metadata={"project_id": "proj456"}
))
```

### 2. GetQuotaConsumption
**用途**：查询用户的配额消费统计和详细记录

**请求**：`QuotaConsumptionQuery`
- `user_id` (string, required): 用户 ID
- `time_range` (string, optional): 时间范围 (day, week, month, all)，默认 "day"
- `workflow_type` (string, optional): 工作流类型过滤

**响应**：`QuotaConsumptionResponse`
- `success` (bool): 是否成功
- `message` (string): 响应消息
- `total_tokens` (int32): 总 token 数量
- `total_records` (int32): 总记录数
- `records` (repeated QuotaRecord): 消费记录列表

**示例调用**：
```python
response = await stub.GetQuotaConsumption(ai_service_pb2.QuotaConsumptionQuery(
    user_id="user123",
    time_range="week",
    workflow_type="writing"
))
```

### 3. SyncQuotaToBackend
**用途**：将用户的配额消费记录同步到后端系统

**请求**：`QuotaSyncRequest`
- `user_ids` (repeated string, required): 用户 ID 列表
- `force_sync` (bool, optional): 是否强制同步

**响应**：`QuotaSyncResponse`
- `synced_count` (int32): 成功同步的用户数量
- `failed_user_ids` (repeated string): 失败的用户 ID 列表
- `message` (string): 响应消息

**示例调用**：
```python
response = await stub.SyncQuotaToBackend(ai_service_pb2.QuotaSyncRequest(
    user_ids=["user123", "user456"],
    force_sync=True
))
```

## 错误处理
所有方法都使用标准的 gRPC 错误处理：
- `INVALID_ARGUMENT`: 参数验证失败
- `INTERNAL`: 服务器内部错误
- `UNAVAILABLE`: QuotaService 未初始化

## 日志级别
- `INFO`: 方法调用和成功完成
- `ERROR`: 方法执行失败
- `WARNING`: SyncQuotaToBackend 的后端客户端集成警告

## 相关服务
所有方法都依赖于 `QuotaService`，必须在 `AIServicer` 初始化时注入。

## 注意事项
1. **SyncQuotaToBackend** 当前未完全实现，返回 "Backend sync not yet implemented"
2. 所有方法都是异步的，使用 async/await
3. 参数验证在方法开始时进行，失败会立即返回 gRPC 错误

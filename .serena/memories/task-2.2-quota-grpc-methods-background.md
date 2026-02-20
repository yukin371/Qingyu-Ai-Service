# Task 2.2: 扩展 gRPC 服务（添加配额方法）- 任务背景

## 任务上下文
- **项目**: AI 服务迁移项目
- **阶段**: Phase 2 - gRPC 服务实现
- **前置任务**: Task 2.1 - QuotaService 已实现
- **当前任务**: Task 2.2 - 在 gRPC 服务器中添加配额相关方法

## 任务目标
在 `Qingyu-Ai-Service/src/grpc_server/servicer.py` 中实现三个配额相关的 RPC 方法：
1. ConsumeQuota - 配额消费
2. GetQuotaConsumption - 查询配额消费
3. SyncQuotaToBackend - 同步配额到后端

## 验收标准

### 最低验收标准（必须实现）：
1. ✅ 实现 ConsumeQuota 方法
2. ✅ 实现 GetQuotaConsumption 方法
3. ✅ 实现 SyncQuotaToBackend 方法
4. ✅ 集成 QuotaService（已在 Task 2.1 实现）
5. ✅ 代码无语法错误
6. ✅ 添加错误处理

### 一般验收标准：
1. 使用 async/await 异步编程
2. 添加详细的日志记录
3. 返回正确的 gRPC 响应格式
4. 处理异常情况

### 优秀验收标准：
1. 添加参数验证
2. 添加性能监控
3. 支持批量操作
4. 完整的单元测试

## 相关文件
- **实现文件**: `Qingyu-Ai-Service/src/grpc_server/servicer.py`
- **QuotaService**: `Qingyu-Ai-Service/src/services/quota_service.py`（已实现）
- **Proto 定义**: `Qingyu-Protos/ai_service.proto`（已存在）

## 实现步骤
1. 在 AIServicer.__init__ 中注入 QuotaService
2. 实现 ConsumeQuota 方法
3. 实现 GetQuotaConsumption 方法
4. 实现 SyncQuotaToBackend 方法
5. 添加导入语句
6. 验证语法正确性
7. 提交更改

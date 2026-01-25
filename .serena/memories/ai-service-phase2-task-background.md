# AI 服务迁移计划 - 阶段 2 任务背景

## 任务概述
执行 AI 服务迁移计划的阶段 2：AI 服务改造任务

## 项目位置
- 主仓库：E:\Github\Qingyu
- AI 服务：E:\Github\Qingyu\Qingyu-Ai-Service
- 协议：E:\Github\Qingyu\Qingyu-Protos

## 上下文信息

### 阶段 1 完成状态
- PostgreSQL 配额表已创建：`quota_consumption_records`, `quota_sync_status`
- Proto 定义已扩展（v1.1.0），包含配额相关 RPC 方法
- Go gRPC 客户端代码已生成
- Docker Compose 配置已更新

### 项目技术栈
- Python FastAPI + LangGraph
- PostgreSQL（数据库）
- Redis（缓存）
- Milvus（向量数据库）

## 待执行任务列表

### Task 2.1: 实现配额服务
- [ ] 创建 `src/services/quota_service.py`
  - [ ] 实现 `QuotaService` 类
  - [ ] 实现 `record_consumption` 方法
  - [ ] 实现 `get_user_consumption` 方法
  - [ ] 实现 `get_consumption_records` 方法
  - [ ] 实现 `sync_to_backend` 方法
- [ ] 创建 `tests/services/test_quota_service.py`
- [ ] 运行测试验证功能
- [ ] 提交代码

### Task 2.2: 扩展 gRPC 服务
- [ ] 修改 `src/grpc_service/server.py`
  - [ ] 添加 `ConsumeQuota` RPC 方法
  - [ ] 添加 `GetQuotaConsumption` RPC 方法
  - [ ] 添加 `SyncQuotaToBackend` RPC 方法
  - [ ] 在 `ExecuteAgent` 方法中集成配额记录
- [ ] 创建 `tests/grpc/test_quota_rpc.py`
- [ ] 运行测试验证功能
- [ ] 提交代码

### Task 2.3: 集成配额记录到执行流程
- [ ] 修改 `src/agents/executor.py`
  - [ ] 添加 `QuotaService` 依赖
  - [ ] 在 `execute` 方法中自动记录配额消费
  - [ ] 实现 `_calculate_tokens` 方法
- [ ] 提交代码

## PostgreSQL 表结构
```sql
quota_consumption_records (
  id SERIAL PRIMARY KEY,
  user_id UUID NOT NULL,
  workflow_type VARCHAR(50) NOT NULL,
  tokens_used INTEGER NOT NULL,
  quota_consumed INTEGER NOT NULL,
  metadata JSONB DEFAULT '{}'::jsonb,
  consumed_at TIMESTAMP DEFAULT NOW()
)
```

## Proto 定义位置
配额相关消息类型定义在：`E:\Github\Qingyu\Qingyu-Protos\ai_service.proto`

## 验收标准
- 所有单元测试通过
- 代码遵循项目现有风格
- 每个任务完成后提交代码
- 使用 asyncpg 进行数据库操作
- 正确处理错误和日志记录

## 开始时间
2026-01-24

## 当前状态
准备开始 Task 2.1: 实现配额服务

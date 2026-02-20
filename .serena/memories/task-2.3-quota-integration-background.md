# Task 2.3: 集成配额记录到执行流程 - 任务背景

## 任务概述
在 `Qingyu-Ai-Service/src/agent_runtime/orchestration/executor.py` 中的 Agent 执行流程中集成配额记录功能，使得每次 AI 调用都自动记录配额消费。

## 前置条件
- Task 2.1 已完成：QuotaService 已实现（位于 `src/services/quota_service.py`）
- Task 2.2 已完成：配额相关的 gRPC 方法已实现

## 任务目标
1. 在 AgentExecutor.__init__ 中注入 QuotaService
2. 在 execute 方法中添加配额记录逻辑
3. 实现 _calculate_tokens 方法计算token使用量
4. 确保配额记录失败不影响主流程

## 关键文件
- 目标文件：`src/agent_runtime/orchestration/executor.py`
- QuotaService：`src/services/quota_service.py`

## 实现要点
1. QuotaService 已实现 record_consumption 方法
2. 需要在 __init__ 中接收 db_pool 并创建 QuotaService 实例
3. 在 _execute_once 方法中添加配额记录逻辑
4. 实现 _calculate_tokens 方法，支持从 AgentResult 中提取 token 信息
5. 配额记录失败不应中断主流程（使用 try-except 包裹）

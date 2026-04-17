# Qingyu-Ai-Service 模块上下文

## 模块职责

- 提供 FastAPI 与 gRPC 形式的 AI runtime，承接写作辅助、章节分析、事实提取与工作流编排。
- 为 Editor V3 提供 AI 侧最小闭环能力，包括 `story_analysis` 相关接口和专用 agent/service。
- 负责 AI 结果的结构化输出与协议适配，不直接拥有小说业务真相。

## Owns

- `src/api/` 下的 AI 服务 HTTP 路由与输入输出模型。
- `src/agents/` 下的专用分析与生成 agent 实现。
- `src/services/` 下仅属于 AI 服务内部的编排与分析服务。
- `tests/` 下与 AI 服务自身行为对应的单元测试与 API 测试。

## Must not own

- 不直接写入主业务数据真相；需要落库时应通过 `src/api/go_backend/` 对后端公开接口进行调用。
- 不在本模块中定义前端工作区状态、UI 行为或跨仓库 roadmap 真相。
- 不把临时设计说明写回代码目录，长期边界仍由父仓库 `docs/` 持有。

## 关键依赖

- `src/main.py` 负责统一挂载 FastAPI 路由。
- `src/llm/` 与 `LLMFactory` 负责模型实例化。
- `src/api/go_backend/` 负责与 Go 后端交互。
- 父仓库 `docs/plans/v3/` 负责 Editor V3 的阶段计划与验收口径。

## 不变量

- Editor V3 相关接口优先走“新增接口、不破坏现有协议”的方式推进，避免回归 `trigger-index` 现有链路。
- AI 服务输出必须尽量结构化，便于后端、前端和测试稳定消费。
- 任何与业务真相有关的写入动作都必须经过后端 owner，不在 AI 服务内直接越权落库。

## 常见坑

1. `story_analysis` 路由是公共 HTTP API 域，改现有请求/响应结构会直接影响跨库联调。
2. 现有 review 类 agent 更偏通用审核，不应直接替代 Editor V3 的章节级协议。
3. 测试若直接走真实 LLM，容易引入不稳定；章节分析类能力应优先提供可 stub 的结构化边界。
4. `ConsistencyAgent` 不能再假定本地一定有可用 Gemini key；若显式 provider 未配置或 Gemini key 仍是占位值，应优先回退到当前已配置的可用 provider，避免 `/api/v1/story/check-consistency` 在真实联调时稳定 500。

## 文档同步触发条件

- 新增或调整 Editor V3 AI 分析接口时，需要同步父仓库 `docs/roadmap.md` 与 `docs/plans/v3/implementation/*.md`。
- 如果 AI 服务开始拥有新的跨仓库 canonical owner，必须回写父仓库架构守则与 ADR。

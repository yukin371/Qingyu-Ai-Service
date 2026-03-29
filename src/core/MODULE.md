# Core

> 最后更新：2026-03-29

## 职责

AI 服务基础设施层，管理 LLM 多模型调用（OpenAI/Anthropic/Gemini/Zhipu）、工具注册（LangChain Tools）、配置管理、日志、异常体系。不包含业务工作流逻辑。

## 数据流

```
Agent → core/llm ProviderFactory → 具体 Provider (OpenAI/Anthropic/Gemini/Zhipu)
                                      ↓
                               core/tools/registry → LangChain Tools
```

## 约定 & 陷阱

- **多模型路由**：`provider_factory` 根据请求参数选择 LLM Provider，不同模型能力差异大，Agent 应声明依赖的模型能力
- **Provider 接口统一**：所有 Provider 实现 `base_provider` 定义的统一接口，新增 Provider 必须实现全部方法
- **配置热加载**：`config.py` 支持环境变量覆盖，优先级：环境变量 > .env > 默认值
- **异常体系**：`exceptions.py` 定义了分层异常，Agent 捕获时应注意区分可重试异常和不可重试异常

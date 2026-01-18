# Qingyu AI Service

> 独立的 LangChain Agent Runtime 服务，为 Qingyu 项目提供 AI 能力

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 概述

`Qingyu-AI-Service` 是一个独立的 Python 微服务，提供基于 LangChain/LangGraph 的 AI Agent 运行时。通过 gRPC API 与 Go 后端通信，实现了完整的 AI 能力解耦。

### 核心功能

- 🤖 **Agent Runtime** - 基于 LangChain/LangGraph 1.2.x 的智能体执行引擎
- 🔄 **Session Management** - 分布式会话管理，支持检查点持久化
- 🎯 **Event System** - 事件驱动架构，支持异步事件处理
- 🔌 **Middleware Pipeline** - 可插拔的中间件系统（洋葱模型）
- 🛡️ **Security** - 提示词注入防护、输出清洗、输入验证
- 📊 **Observability** - 完整的监控、日志和指标收集
- 🔍 **RAG** - 向量检索和增强生成能力

## 架构

```
┌─────────────────────────────────────────┐
│        Qingyu-AI-Service (Python)       │
├─────────────────────────────────────────┤
│                                          │
│  ┌────────────────────────────────────┐ │
│  │  FastAPI + gRPC Server            │ │
│  │  - Port 8000 (HTTP)                │ │
│  │  - Port 50051 (gRPC)               │ │
│  └──────────────┬─────────────────────┘ │
│                 │                        │
│  ┌──────────────▼─────────────────────┐ │
│  │  Agent Runtime Layer               │ │
│  │  - AgentExecutor                   │ │
│  │  - SessionManager                  │ │
│  │  - EventBus                        │ │
│  └──────────────┬─────────────────────┘ │
│                 │                        │
│  ┌──────────────▼─────────────────────┐ │
│  │  Middleware Pipeline               │ │
│  │  - Auth → Validation → RateLimit   │ │
│  └──────────────┬─────────────────────┘ │
│                 │                        │
│  ┌──────────────▼─────────────────────┐ │
│  │  LLM Integration                   │ │
│  │  - OpenAI / Anthropic / Gemini     │ │
│  └──────────────┬─────────────────────┘ │
└────────────────┼────────────────────────┘
                 │
    ┌────────────▼─────────────────────────┐
    │     External Services                │
    ├──────────────────────────────────────┤
    │ Redis (key prefix: qingyu-ai:)      │
    │ PostgreSQL (db: qingyu_ai_service)  │
    │ Milvus (prefix: qingyu_ai_vectors_) │
    │ OpenAI / Anthropic APIs              │
    └──────────────────────────────────────┘
```

## 快速开始

### 环境要求

- Python 3.10+
- Redis 7+
- PostgreSQL 14+
- Milvus 2.3+

### 安装

```bash
# 克隆仓库
git clone https://github.com/yukin371/Qingyu-AI-Service.git
cd Qingyu-AI-Service

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置 API Keys 和数据库连接

# 初始化数据库
python scripts/init_db.py
```

### 运行

```bash
# 开发模式
uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload

# 生产模式
gunicorn src.app:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### Docker 部署

```bash
# 构建镜像
docker build -t qingyu-ai-service:v1.0.0 .

# 运行容器
docker run -d \
  --name qingyu-ai-service \
  -p 8000:8000 \
  -p 50051:50051 \
  --env-file .env \
  qingyu-ai-service:v1.0.0
```

## API 文档

### HTTP API

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### gRPC API

详见 [Proto 定义](proto/ai_service.proto)

| RPC 方法 | 描述 | 状态 |
|----------|------|------|
| GenerateContent | 生成内容 | ✅ |
| QueryKnowledge | RAG 查询 | ✅ |
| GetContext | 获取上下文 | ✅ |
| ExecuteAgent | 执行 Agent | ✅ |
| ExecuteCreativeWorkflow | 创作工作流 | ✅ |
| GenerateOutline | 生成大纲 | ✅ |
| GenerateCharacters | 生成角色 | ✅ |
| GeneratePlot | 生成情节 | ✅ |
| EmbedText | 文本向量化 | ✅ |
| HealthCheck | 健康检查 | ✅ |

## 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/integration/

# 查看覆盖率
pytest --cov=src --cov-report=html

# 性能测试
pytest tests/performance/ -v
```

**测试覆盖率**: 95%+
**测试通过率**: 373/373 ✅

## 文档

- [安装指南](docs/getting-started/installation.md)
- [快速开始](docs/getting-started/quickstart.md)
- [API 参考](docs/api/)
- [安全手册](docs/security/)
- [部署指南](docs/deployment/)
- [架构设计](docs/concepts/architecture.md)

## 版本

当前版本: **v1.0.0**

版本遵循语义化版本规范 (Semantic Versioning)：
- **主版本**: 破坏性变更
- **次版本**: 向后兼容的新功能
- **修订号**: Bug 修复

**兼容性承诺**: v1.x 版本保持 API 向后兼容

## 配置说明

### 数据隔离

为避免与 Go 后端冲突，本服务使用独立的数据命名空间：

| 资源 | Go Backend | AI Service |
|------|------------|------------|
| Redis Key 前缀 | `qingyu:` | `qingyu-ai:` |
| PostgreSQL Database | `qingyu` | `qingyu_ai_service` |
| Milvus Collection | `qingyu_vectors_*` | `qingyu_ai_vectors_*` |

## 依赖

```
langchain==1.2.5
langchain-core==1.2.5
langchain-openai==1.2.5
langchain-anthropic==1.2.5
langgraph==1.2.0
fastapi==0.109.0
uvicorn[standard]==0.27.0
grpcio==1.60.0
redis==5.2.1
psycopg2-binary==2.9.9
```

完整依赖见 [requirements.txt](requirements.txt)

## 开发

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 代码格式化
black src tests
isort src tests

# 类型检查
mypy src

# Linting
flake8 src tests
```

## 许可证

MIT License - 详见 [LICENSE](LICENSE)

## 联系方式

- 仓库: https://github.com/yukin371/Qingyu-AI-Service
- 问题反馈: https://github.com/yukin371/Qingyu-AI-Service/issues
- Proto 定义: https://github.com/yukin371/Qingyu-Protos

## 致谢

本项目基于以下优秀的开源项目：

- [LangChain](https://github.com/langchain-ai/langchain)
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [FastAPI](https://github.com/tiangolo/fastapi)
- [gRPC](https://grpc.io/)

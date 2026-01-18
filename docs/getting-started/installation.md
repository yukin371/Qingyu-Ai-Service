# 安装指南

本文档介绍如何安装和配置 Qingyu Backend AI 服务。

## 系统要求

- Python 3.10 或更高版本
- Redis 6.0 或更高版本（用于会话管理）
- uv (推荐的 Python 包管理器) 或 pip
- Git

## 快速安装

### 1. 克隆仓库

```bash
git clone https://github.com/your-org/Qingyu_backend.git
cd Qingyu_backend/python_ai_service
```

### 2. 安装依赖

#### 使用 uv（推荐）

```bash
# 安装 uv
pip install uv

# 安装项目依赖
uv sync
```

#### 使用 pip

```bash
# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate  # Windows

# 安装依赖
pip install -e .
```

## Redis 配置

### 方式 1: 本地 Redis（开发环境）

#### Windows

```bash
# 使用 Chocolatey 安装
choco install redis-64

# 启动 Redis 服务
redis-server
```

#### Linux/Mac

```bash
# 使用 Homebrew 安装
brew install redis

# 启动 Redis 服务
redis-server
```

### 方式 2: Docker Redis（推荐）

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### 方式 3: 云 Redis（生产环境）

更新 `.env` 文件中的 Redis 配置：

```env
QINGYU_REDIS_HOST=your-redis-host
QINGYU_REDIS_PORT=6379
QINGYU_REDIS_PASSWORD=your-password
```

## 环境变量配置

创建 `.env` 文件：

```env
# Redis 配置
QINGYU_REDIS_HOST=localhost
QINGYU_REDIS_PORT=6379
QINGYU_REDIS_PASSWORD=

# API Keys
OPENAI_API_KEY=sk-your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# 日志级别
LOG_LEVEL=INFO

# 会话配置
QINGYU_SESSION_TTL_SECONDS=3600
QINGYU_SESSION_MAX_COUNT=10000
```

## 验证安装

### 1. 检查 Python 版本

```bash
python --version
# 应该显示 Python 3.10+
```

### 2. 检查 Redis 连接

```bash
python -c "
from src.agent_runtime.session_manager import SessionManager
sm = SessionManager(conn=None, ttl=3600)
print('SessionManager 创建成功')
"
```

### 3. 运行测试

```bash
# 运行单元测试
uv run pytest tests/unit/ -v

# 运行集成测试
uv run pytest tests/integration/ -v
```

## 常见问题

### 问题 1: Redis 连接失败

**错误**: `redis.exceptions.ConnectionError: Error connecting to Redis`

**解决方案**:
1. 检查 Redis 服务是否运行：`redis-cli ping`
2. 检查 `.env` 中的 Redis 配置
3. 确保 Redis 端口 6379 未被占用

### 问题 2: 依赖安装失败

**错误**: `ModuleNotFoundError: No module named 'xxx'`

**解决方案**:
```bash
# 重新安装依赖
uv sync --reinstall

# 或使用 pip
pip install -e .
```

### 问题 3: LangChain 版本冲突

**错误**: `langchain_core.errors.__all__.Error: ...`

**解决方案**:
```bash
# 重新安装正确版本的 LangChain
uv pip install --force-reinstall langchain-core langchain-openai langchain-community
```

## 下一步

安装完成后，请继续阅读 [快速开始指南](quickstart.md) 了解如何创建第一个 Agent。

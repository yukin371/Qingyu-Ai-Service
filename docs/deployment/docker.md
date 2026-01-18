# Docker 部署指南

本指南介绍如何使用 Docker 容器化部署 Qingyu Backend AI。

## Dockerfile

### 基础 Dockerfile

```dockerfile
# Dockerfile

# 使用官方 Python 基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建非 root 用户
RUN useradd -m -u 1000 qingyu && \
    chown -R qingyu:qingyu /app
USER qingyu

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# 启动命令
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 多阶段构建

```dockerfile
# Dockerfile

# 构建阶段
FROM python:3.10-slim AS builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 运行阶段
FROM python:3.10-slim

WORKDIR /app

# 从构建阶段复制依赖
COPY --from=builder /root/.local /root/.local
COPY --from=builder /root/.cache /root/.cache

# 复制应用代码
COPY . .

# 创建非 root 用户
RUN useradd -m -u 1000 qingyu && \
    chown -R qingyu:qingyu /app
USER qingyu

# 更新 PATH
ENV PATH=/root/.local/bin:$PATH

EXPOSE 8000

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Docker Compose

### docker-compose.yml

```yaml
version: '3.8'

services:
  # API 服务
  api:
    build: .
    container_name: qingyu_api
    ports:
      - "8000:8000"
    environment:
      - QINGYU_REDIS_HOST=redis
      - QINGYU_REDIS_PORT=6379
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      - redis
      - mongo
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config:ro
    restart: unless-stopped
    networks:
      - qingyu_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  # Redis
  redis:
    image: redis:7-alpine
    container_name: qingyu_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    restart: unless-stopped
    networks:
      - qingyu_network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  # MongoDB (可选)
  mongo:
    image: mongo:6
    container_name: qingyu_mongo
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db
    restart: unless-stopped
    networks:
      - qingyu_network
    healthcheck:
      test: ["CMD", "mongo", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 3

  # Nginx (可选)
  nginx:
    image: nginx:alpine
    container_name: qingyu_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./static:/usr/share/nginx/html:ro
    depends_on:
      - api
    restart: unless-stopped
    networks:
      - qingyu_network

volumes:
  redis_data:
  mongo_data:

networks:
  qingyu_network:
    driver: bridge
```

### 开发环境 docker-compose

```yaml
# docker-compose.dev.yml

version: '3.8'

services:
  api:
    build: .
    container_name: qingyu_api_dev
    ports:
      - "8000:8000"
    environment:
      - LOG_LEVEL=DEBUG
      - RELOAD=true
    volumes:
      - .:/app  # 挂载源代码，支持热重载
    command: uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  redis_data:
```

## 构建和运行

### 构建镜像

```bash
# 构建镜像
docker build -t qingyu-backend:latest .

# 使用标签
docker build -t qingyu-backend:v1.0 .

# 不使用缓存
docker build --no-cache -t qingyu-backend:latest .
```

### 运行容器

```bash
# 运行单个服务
docker run -d \
  --name qingyu_api \
  -p 8000:8000 \
  -e OPENAI_API_KEY=sk-xxx \
  qingyu-backend:latest

# 使用 Docker Compose
docker-compose up -d

# 查看日志
docker-compose logs -f api

# 停止服务
docker-compose down
```

### 管理容器

```bash
# 查看运行中的容器
docker ps

# 查看所有容器
docker ps -a

# 查看容器日志
docker logs qingyu_api

# 进入容器
docker exec -it qingyu_api bash

# 重启容器
docker restart qingyu_api

# 停止容器
docker stop qingyu_api

# 删除容器
docker rm qingyu_api
```

## 生产优化

### 多阶段构建优化

```dockerfile
# 优化的 Dockerfile

FROM python:3.10-slim AS builder

# 只安装必要的构建工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先复制依赖文件，利用缓存
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 运行时镜像
FROM python:3.10-slim

# 只安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制依赖
COPY --from=builder /root/.local /root/.local

# 复制应用代码
COPY . .

# 非 root 用户
RUN useradd -m -u 1000 qingyu
USER qingyu

ENV PATH=/root/.local/bin:$PATH

EXPOSE 8000

# 使用 gunicorn + uvicorn workers
CMD ["gunicorn", "src.app:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000"]
```

### 镜像优化

```dockerfile
# 最小化镜像

FROM python:3.10-alpine AS builder

WORKDIR /app

# 安装依赖
RUN apk add --no-cache gcc musl-dev

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 运行时镜像
FROM python:3.10-alpine

WORKDIR /app

# 复制依赖
COPY --from=builder /root/.local /root/.local

# 复制应用
COPY . .

# 安装运行时依赖
RUN apk add --no-cache curl

# 非 root 用户
RUN addgroup -g 1000 qingyu && \
    adduser -D -u 1000 -G qingyu qingyu
USER qingyu

ENV PATH=/root/.local/bin:$PATH

EXPOSE 8000

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 安全配置

### 非 root 用户

```dockerfile
# 创建非 root 用户
RUN groupadd -r qingyu && useradd -r -g qingyu qingyu

# 设置目录权限
RUN chown -R qingyu:qingyu /app

USER qingyu
```

### 只读文件系统

```dockerfile
# 复制应用代码
COPY . .

# 设置权限
RUN chown -R qingyu:qingyu /app
RUN chmod -R 755 /app

# 运行时只读
USER qingyu
```

### 健康检查

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

## 数据持久化

### Docker Volumes

```yaml
version: '3.8'

services:
  api:
    volumes:
      # 命名卷
      - app_data:/app/data
      # 绑定挂载
      - ./logs:/app/logs
      # 匿名卷
      - /app/tmp

  redis:
    volumes:
      - redis_data:/data

volumes:
  app_data:
  redis_data:
```

## 监控和日志

### 日志收集

```yaml
version: '3.8'

services:
  api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

    volumes:
      # 挂载日志目录
      - ./logs:/app/logs
      - /var/log/qingyu:/var/log/qingyu
```

### Prometheus 监控

```yaml
version: '3.8'

services:
  api:
    labels:
      - "prometheus.io.scrape=true"
      - "prometheus.io.port=8000"

  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  grafana_data:
```

## 部署流程

### 本地开发

```bash
# 开发环境
docker-compose -f docker-compose.dev.yml up

# 构建并启动
docker-compose up --build

# 后台运行
docker-compose up -d
```

### 生产部署

```bash
# 1. 构建生产镜像
docker build -t qingyu-backend:v1.0 .

# 2. 标记镜像
docker tag qingyu-backend:v1.0 registry.example.com/qingyu-backend:v1.0

# 3. 推送到镜像仓库
docker push registry.example.com/qingyu-backend:v1.0

# 4. 在生产服务器上拉取
docker pull registry.example.com/qingyu-backend:v1.0

# 5. 运行容器
docker run -d \
  --name qingyu_api \
  -p 8000:8000 \
  --env-file /opt/qingyu/.env \
  registry.example.com/qingyu-backend:v1.0
```

### 滚动更新

```bash
# 1. 构建新版本
docker build -t qingyu-backend:v1.1 .

# 2. 停止旧容器
docker stop qingyu_api

# 3. 删除旧容器
docker rm qingyu_api

# 4. 启动新容器
docker run -d \
  --name qingyu_api \
  -p 8000:8000 \
  qingyu-backend:v1.1
```

## 故障排查

### 容器无法启动

```bash
# 查看容器日志
docker logs qingyu_api

# 检查容器状态
docker inspect qingyu_api

# 进入容器调试
docker run -it --rm qingyu-backend:latest bash
```

### 网络问题

```bash
# 查看网络
docker network ls
docker network inspect qingyu_network

# 测试连接
docker exec qingyu_api ping redis
```

### 资源限制

```yaml
version: '3.8'

services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

## 最佳实践

### 1. 使用 .dockerignore

```
# .dockerignore

__pycache__
*.pyc
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info
dist
build
.pytest_cache
.coverage
.tox
.git
.gitignore
venv
.venv
env
.env.local
.vscode
.idea
*.md
docs
tests
```

### 2. 多阶段构建

使用多阶段构建减小镜像大小

### 3. 缓存依赖

将依赖安装和代码复制分开，利用 Docker 缓存

### 4. 非 root 用户

始终使用非 root 用户运行应用

### 5. 健康检查

配置健康检查以便监控

### 6. 日志管理

将日志输出到 stdout/stderr，由容器引擎收集

## 相关文档

- [生产部署](production.md) - 传统部署方式
- [监控告警](monitoring.md) - 监控配置
- [日志管理](logging.md) - 日志配置

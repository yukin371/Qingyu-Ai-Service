# 生产部署指南

本指南介绍如何将 Qingyu Backend AI 部署到生产环境。

## 部署前检查清单

### 环境要求

- [ ] Python 3.10+ 已安装
- [ ] Redis 6.0+ 正在运行
- [ ] MongoDB 4.4+ (可选，用于数据持久化)
- [ ] 至少 2GB 可用内存
- [ ] 至少 10GB 可用磁盘空间

### 配置检查

- [ ] 环境变量已设置
- [ ] API 密钥已配置
- [ ] 数据库连接已测试
- [ ] Redis 连接已测试
- [ ] 日志目录已创建
- [ ] 监控已配置

### 安全检查

- [ ] 输入验证已启用
- [ ] 提示词注入防护已启用
- [ ] 输出清洗已启用
- [ ] 认证授权已配置
- [ ] 速率限制已配置
- [ ] TLS/SSL 已配置

## 环境配置

### 环境变量

创建 `.env` 文件：

```env
# Redis 配置
QINGYU_REDIS_HOST=localhost
QINGYU_REDIS_PORT=6379
QINGYU_REDIS_PASSWORD=
QINGYU_REDIS_DB=0

# MongoDB 配置（如果使用）
QINGYU_MONGO_HOST=localhost
QINGYU_MONGO_PORT=27017
QINGYU_MONGO_USERNAME=
QINGYU_MONGO_PASSWORD=
QINGYU_MONGO_DATABASE=qingyu

# API Keys
OPENAI_API_KEY=sk-your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key

# 安全配置
QINGYU_ENABLE_AUTH=true
QINGYU_RATE_LIMIT_ENABLED=true
QINGYU_RATE_LIMIT_MAX_REQUESTS=100
QINGYU_RATE_LIMIT_WINDOW_SECONDS=60

# 会话配置
QINGYU_SESSION_TTL_SECONDS=3600
QINGYU_SESSION_MAX_COUNT=10000

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=/var/log/qingyu/app.log

# 性能配置
QINGYU_MAX_WORKERS=10
QINGYU_MAX_CONCURRENT_REQUESTS=100
```

### 配置文件

`config/production.py`:

```python
import os
from typing import Optional

class ProductionConfig:
    # Redis
    REDIS_HOST: str = os.getenv("QINGYU_REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("QINGYU_REDIS_PORT", "6379"))
    REDIS_PASSWORD: Optional[str] = os.getenv("QINGYU_REDIS_PASSWORD")
    REDIS_DB: int = int(os.getenv("QINGYU_REDIS_DB", "0"))

    # MongoDB
    MONGO_HOST: str = os.getenv("QINGYU_MONGO_HOST", "localhost")
    MONGO_PORT: int = int(os.getenv("QINGYU_MONGO_PORT", "27017"))
    MONGO_USERNAME: Optional[str] = os.getenv("QINGYU_MONGO_USERNAME")
    MONGO_PASSWORD: Optional[str] = os.getenv("QINGYU_MONGO_PASSWORD")
    MONGO_DATABASE: str = os.getenv("QINGYU_MONGO_DATABASE", "qingyu")

    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY")

    # 安全
    ENABLE_AUTH: bool = os.getenv("QINGYU_ENABLE_AUTH", "true").lower() == "true"
    RATE_LIMIT_ENABLED: bool = os.getenv("QINGYU_RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_MAX_REQUESTS: int = int(os.getenv("QINGYU_RATE_LIMIT_MAX_REQUESTS", "100"))
    RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("QINGYU_RATE_LIMIT_WINDOW_SECONDS", "60"))

    # 会话
    SESSION_TTL_SECONDS: int = int(os.getenv("QINGYU_SESSION_TTL_SECONDS", "3600"))
    SESSION_MAX_COUNT: int = int(os.getenv("QINGYU_SESSION_MAX_COUNT", "10000"))

    # 日志
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "/var/log/qingyu/app.log")

    # 性能
    MAX_WORKERS: int = int(os.getenv("QINGYU_MAX_WORKERS", "10"))
    MAX_CONCURRENT_REQUESTS: int = int(os.getenv("QINGYU_MAX_CONCURRENT_REQUESTS", "100"))
```

## 应用部署

### 使用 Gunicorn

```bash
# 安装 Gunicorn
pip install gunicorn

# 启动服务
gunicorn src.app:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile /var/log/qingyu/access.log \
  --error-logfile /var/log/qingyu/error.log \
  --log-level info \
  --timeout 120
```

### 使用 Uvicorn

```bash
# 启动服务
uvicorn src.app:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info \
  --access-log \
  --reload  # 仅开发环境
```

### Systemd 服务

`/etc/systemd/system/qingyu.service`:

```ini
[Unit]
Description=Qingyu Backend AI Service
After=network.target redis.service mongodbservice.service

[Service]
Type=notify
User=qingyu
Group=qingyu
WorkingDirectory=/opt/qingyu
Environment="PATH=/opt/qingyu/venv/bin"
ExecStart=/opt/qingyu/venv/bin/gunicorn src.app:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --config /etc/qingyu/gunicorn.conf.py
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=30
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
# 重载 systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start qingyu

# 开机自启
sudo systemctl enable qingyu

# 查看状态
sudo systemctl status qingyu

# 查看日志
sudo journalctl -u qingyu -f
```

## Nginx 配置

### 反向代理

`/etc/nginx/sites-available/qingyu`:

```nginx
upstream qingyu_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.qingyu.example.com;

    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.qingyu.example.com;

    # SSL 证书
    ssl_certificate /etc/ssl/certs/qingyu.crt;
    ssl_certificate_key /etc/ssl/private/qingyu.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 日志
    access_log /var/log/nginx/qingyu_access.log;
    error_log /var/log/nginx/qingyu_error.log;

    # 基础配置
    client_max_body_size 10M;
    proxy_read_timeout 120s;
    proxy_connect_timeout 120s;
    proxy_send_timeout 120s;

    location / {
        proxy_pass http://qingyu_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 健康检查
    location /health {
        proxy_pass http://qingyu_backend/health;
        access_log off;
    }

    # 静态文件
    location /static {
        alias /opt/qingyu/static;
        expires 30d;
    }
}
```

启用配置：

```bash
# 创建符号链接
sudo ln -s /etc/nginx/sites-available/qingyu /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重载 Nginx
sudo systemctl reload nginx
```

## Redis 配置

### 生产配置

`/etc/redis/redis.conf`:

```conf
# 网络配置
bind 127.0.0.1
protected-mode yes
port 6379
tcp-backlog 511
timeout 0
tcp-keepalive 300

# 持久化
save 900 1
save 300 10
save 60 10000

# AOF
appendonly yes
appendfsync everysec
no-appendfsync-on-rewrite no

# 内存管理
maxmemory 2gb
maxmemory-policy allkeys-lru

# 日志
loglevel notice
logfile /var/log/redis/redis-server.log

# 慢查询
slowlog-log-slower-than 10000
slowlog-max-len 128
```

启动 Redis：

```bash
# 启动 Redis
sudo systemctl start redis-server

# 开机自启
sudo systemctl enable redis-server

# 检查状态
sudo systemctl status redis-server
```

## 监控配置

### Prometheus 配置

`/etc/prometheus/prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'qingyu'
    static_configs:
      - targets: ['localhost:8000']
    scrape_interval: 15s
    metrics_path: '/metrics'
```

### Grafana 仪表板

创建监控仪表板，监控：
- 请求速率
- 响应时间
- 错误率
- CPU 使用率
- 内存使用率
- Redis 连接数

## 日志配置

### 日志轮转

`/etc/logrotate.d/qingyu`:

```
/var/log/qingyu/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 qingyu qingyu
    sharedscripts
    postrotate
        systemctl reload qingyu > /dev/null 2>&1 || true
    endscript
}
```

### 结构化日志

```python
import structlog
import logging

# 配置 structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# 使用
logger = structlog.get_logger(__name__)
logger.info("Agent executed", agent_id="chatbot", duration_ms=1234)
```

## 故障排查

### 常见问题

#### 1. 服务无法启动

```bash
# 检查端口占用
sudo netstat -tlnp | grep :8000

# 检查日志
sudo journalctl -u qingyu -n 50

# 检查配置
python -c "from config.production import ProductionConfig; print(ProductionConfig().REDIS_HOST)"
```

#### 2. Redis 连接失败

```bash
# 检查 Redis 状态
sudo systemctl status redis-server

# 测试连接
redis-cli ping

# 检查配置
redis-cli CONFIG GET bind
```

#### 3. 内存不足

```bash
# 检查内存使用
free -h

# 检查进程内存
ps aux --sort=-%mem | head

# 调整 Worker 数量
# 在 systemd 服务中减少 --workers
```

#### 4. 响应缓慢

```bash
# 检查日志
tail -f /var/log/qingyu/app.log

# 检查 Redis
redis-cli INFO stats

# 检查数据库连接
# 使用 mongosh 或 mongo shell
```

## 备份和恢复

### 数据备份

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/qingyu"
DATE=$(date +%Y%m%d_%H%M%S)

# Redis 备份
redis-cli --rdb /var/lib/redis/dump.rdb
cp /var/lib/redis/dump.rdb "$BACKUP_DIR/redis_$DATE.rdb"

# MongoDB 备份（如果使用）
mongodump --host localhost --port 27017 --out "$BACKUP_DIR/mongo_$DATE"

# 清理旧备份（保留 7 天）
find $BACKUP_DIR -type f -mtime +7 -delete
```

定时备份：

```bash
# 添加到 crontab
crontab -e

# 每天凌晨 2 点备份
0 2 * * * /opt/qingyu/scripts/backup.sh
```

### 数据恢复

```bash
# Redis 恢复
redis-cli --rdb /backup/qingyu/redis_20250117_020000.rdb

# MongoDB 恢复
mongorestore --host localhost --port 27017 /backup/qingyu/mongo_20250117_020000
```

## 安全加固

### 防火墙配置

```bash
# UFW 防火墙
sudo ufw enable
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 6379/tcp   # Redis（仅本地）
sudo ufw deny 27017/tcp  # MongoDB（仅本地）
```

### TLS/SSL 配置

```bash
# 生成自签名证书（测试用）
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/qingyu.key \
  -out /etc/ssl/certs/qingyu.crt

# 或使用 Let's Encrypt
sudo certbot certonly --standalone \
  -d api.qingyu.example.com
```

## 性能调优

### Worker 数量

根据 CPU 核心数设置：

```bash
# CPU 核心数
nproc

# 推荐配置：$(nproc) + 1
WORKERS=$(($(nproc) + 1))

gunicorn ... --workers $WORKERS
```

### 连接池

```python
# Redis 连接池
pool = redis.ConnectionPool(
    host=config.REDIS_HOST,
    port=config.REDIS_PORT,
    max_connections=50,  # 根据并发量调整
    min_idle_connections=10,
)

# HTTP 连接池
connector = aiohttp.TCPConnector(
    limit=100,  # 每个主机最大连接数
    limit_per_host=10,
)
```

## 相关文档

- [Docker 部署](docker.md) - 容器化部署
- [监控告警](monitoring.md) - 监控配置
- [日志管理](logging.md) - 日志配置

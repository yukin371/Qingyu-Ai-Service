# 监控告警指南

本指南介绍如何设置 Qingyu Backend AI 的监控和告警系统。

## 监控架构

```
┌─────────────────────────────────────────────────────────┐
│                   监控层次                                │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │   应用监控 (Application Monitoring)            │   │
│  │   - 请求速率                                    │   │
│  │   - 响应时间                                    │   │
│  │   - 错误率                                      │   │
│  │   - 业务指标                                    │   │
│  └──────────────┬───────────────────────────────────┘   │
│                 │                                        │
│  ┌──────────────▼───────────────────────────────────┐   │
│  │   系统监控 (System Monitoring)                 │   │
│  │   - CPU 使用率                                  │   │
│  │   - 内存使用                                    │   │
│  │   - 磁盘 I/O                                    │   │
│  │   - 网络流量                                    │   │
│  └──────────────┬───────────────────────────────────┘   │
│                 │                                        │
│  ┌──────────────▼───────────────────────────────────┐   │
│  │   基础设施监控 (Infrastructure Monitoring)     │   │
│  │   - Redis 状态                                  │   │
│  │   - MongoDB 状态                                │   │
│  │   - 负载均衡器                                  │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Prometheus 配置

### Prometheus 安装

```bash
# 下载 Prometheus
wget https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.linux-amd64.tar.gz

# 解压
tar xvf prometheus-2.45.0.linux-amd64.tar.gz
cd prometheus-2.45.0.linux-amd64

# 启动
./prometheus --config.file=prometheus.yml
```

### Prometheus 配置

`/etc/prometheus/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'qingyu'
    env: 'production'

scrape_configs:
  # Qingyu API 监控
  - job_name: 'qingyu_api'
    static_configs:
      - targets: ['localhost:8000']
        labels:
          service: 'qingyu_api'
          env: 'production'

  # Redis 监控
  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:6379']
        labels:
          service: 'redis'

  # Node Exporter（系统监控）
  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']
        labels:
          service: 'qingyu_server'

  # cAdvisor（容器监控）
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['localhost:8080']
        labels:
          service: 'cadvisor'
```

## 应用监控

### 指标导出

`src/metrics.py`:

```python
from prometheus_client import Counter, Histogram, Gauge, Info
from prometheus_client.exposition import generate_latest

# 定义指标
request_counter = Counter(
    'qingyu_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status'],
)

request_duration = Histogram(
    'qingyu_request_duration_seconds',
    'Request duration',
    ['method', 'endpoint'],
)

active_sessions = Gauge(
    'qingyu_active_sessions',
    'Active sessions',
    ['agent_id'],
)

agent_executions = Counter(
    'qingyu_agent_executions_total',
    'Total agent executions',
    ['agent_id', 'status'],
)

agent_duration = Histogram(
    'qingyu_agent_duration_seconds',
    'Agent execution duration',
    ['agent_id'],
)

# 导出指标
def export_metrics():
    """导出 Prometheus 格式的指标"""
    return generate_latest()
```

### FastAPI 集成

`src/app.py`:

```python
from fastapi import FastAPI
from prometheus_client import make_asgi_app
from src.metrics import request_counter, request_duration

app = FastAPI()

# 指标端点
@app.get("/metrics")
async def metrics():
    from prometheus_client import generate_latest
    return Response(generate_latest(), media_type="text/plain")

# 中间件
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    # 记录开始时间
    start_time = time.time()

    # 执行请求
    response = await call_next(request)

    # 记录指标
    duration = time.time() - start_time

    request_counter.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code,
    ).inc()

    request_duration.labels(
        method=request.method,
        endpoint=request.url.path,
    ).observe(duration)

    return response

# Prometheus 端点
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

## Grafana 仪表板

### 安装 Grafana

```bash
# 使用 Docker
docker run -d \
  --name=grafana \
  -p 3000:3000 \
  -e "GF_SECURITY_ADMIN_PASSWORD=admin" \
  -e "GF_USERS_ALLOW_SIGN_UP=false" \
  grafana/grafana
```

### 数据源配置

1. 登录 Grafana (默认: admin/admin)
2. 添加 Prometheus 数据源
   - URL: `http://prometheus:9090`
   - Access: Browser

### 仪表板 JSON

```json
{
  "dashboard": {
    "title": "Qingyu Backend Dashboard",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(qingyu_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Response Time",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, qingyu_request_duration_seconds_bucket)",
            "legendFormat": "95th percentile"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(qingyu_requests_total{status=~\"5..\"}[5m]) / rate(qingyu_requests_total[5m])",
            "legendFormat": "Error Rate"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Active Sessions",
        "targets": [
          {
            "expr": "sum(qingyu_active_sessions) by (agent_id)",
            "legendFormat": "{{agent_id}}"
          }
        ],
        "type": "graph"
      }
    ]
  }
}
```

## 告警规则

### Prometheus 告警规则

`/etc/prometheus/alerts.yml`:

```yaml
groups:
  - name: qingyu_alerts
    interval: 30s
    rules:
      # 高错误率
      - alert: HighErrorRate
        expr: |
          rate(qingyu_requests_total{status=~"5.."}[5m])
          / rate(qingyu_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} for the last 5 minutes"

      # 高响应时间
      - alert: HighResponseTime
        expr: |
          histogram_quantile(0.95, qingyu_request_duration_seconds_bucket) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High response time detected"
          description: "95th percentile response time is {{ $value }}s"

      # 服务不可用
      - alert: ServiceDown
        expr: up{job="qingyu_api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Service is down"
          description: "Qingyu API service has been down for more than 1 minute"

      # Redis 连接问题
      - alert: RedisDown
        expr: up{job="redis"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Redis is down"
          description: "Redis service has been down for more than 1 minute"

      # 内存使用过高
      - alert: HighMemoryUsage
        expr: |
          (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is above 90%"
```

### Alertmanager 配置

`/etc/alertmanager/alertmanager.yml`:

```yaml
global:
  resolve_timeout: 5m

# 路由配置
route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'

  routes:
    # 关键告警立即通知
    - match:
        severity: critical
      receiver: 'pagerduty'
      continue: true

    # 警告告警延迟通知
    - match:
        severity: warning
      receiver: 'slack'

    # 信息告警仅记录
    - match:
        severity: info
      receiver: 'default'

# 接收器配置
receivers:
  - name: 'default'
    webhook_configs:
      - url: 'http://localhost:5001/alerts'

  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        channel: '#alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'

  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_SERVICE_KEY'
        description: '{{ .GroupLabels.alertname }}'
```

## 日志监控

### EFK Stack

```yaml
version: '3.8'

services:
  elasticsearch:
    image: elasticsearch:8.0.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    volumes:
      - es_data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"

  fluentd:
    image: fluent/fluentd:v1.14
    volumes:
      - ./fluentd/fluent.conf:/fluentd/etc/fluent.conf
      - /var/log:/var/log
    ports:
      - "24224:24224"

  kibana:
    image: kibana:8.0.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200

volumes:
  es_data:
```

## 系统监控

### Node Exporter

```bash
# 下载并运行 Node Exporter
wget https://github.com/prometheus/node_exporter/releases/download/v1.6.0/node_exporter-1.6.0.linux-amd64.tar.gz
tar xvf node_exporter-1.6.0.linux-amd64.tar.gz
cd node_exporter-1.6.0.linux-amd64
./node_exporter
```

### Redis Exporter

```bash
# 运行 Redis Exporter
docker run -d \
  --name redis_exporter \
  -p 9121:9121 \
  oliver006/redis_exporter \
  --redis.addr=redis:6379
```

## 自定义指标

### 业务指标

```python
from prometheus_client import Counter, Histogram, Gauge

# 业务指标
user_registrations = Counter(
    'qingyu_user_registrations_total',
    'Total user registrations',
)

agent_usage = Counter(
    'qingyu_agent_usage_total',
    'Total agent usage',
    ['agent_id'],
)

chat_messages = Histogram(
    'qingyu_chat_message_length',
    'Chat message length',
    buckets=[10, 50, 100, 500, 1000, 5000],
)

# 使用示例
def record_user_registration():
    user_registrations.inc()

def record_agent_usage(agent_id: str):
    agent_usage.labels(agent_id=agent_id).inc()

def record_chat_message(length: int):
    chat_messages.observe(length)
```

## 告警通知

### Slack 通知

```python
import requests

def send_slack_alert(title: str, message: str, severity: str = "info"):
    """发送 Slack 告警"""
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    color = {
        "critical": "danger",
        "warning": "warning",
        "info": "good",
    }

    payload = {
        "attachments": [
            {
                "color": color.get(severity, "good"),
                "title": title,
                "text": message,
                "footer": "Qingyu Backend Alert",
                "ts": int(time.time()),
            }
        ]
    }

    requests.post(webhook_url, json=payload)
```

### Email 通知

```python
import smtplib
from email.mime.text import MIMEText

def send_email_alert(subject: str, body: str):
    """发送邮件告警"""
    smtp_server = os.getenv("SMTP_SERVER", "localhost")
    smtp_port = int(os.getenv("SMTP_PORT", "25"))
    sender = os.getenv("ALERT_SENDER")
    receiver = os.getenv("ALERT_RECEIVER")

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = receiver

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.send_message(msg)
```

## 性能监控

### 性能指标

```python
from prometheus_client import Histogram, Gauge

# 性能指标
db_query_duration = Histogram(
    'qingyu_db_query_duration_seconds',
    'Database query duration',
    ['query_type'],
)

cache_hit_rate = Gauge(
    'qingyu_cache_hit_rate',
    'Cache hit rate',
    ['cache_type'],
)

# 使用示例
async def with_db_timing(query_type: str):
    """记录数据库查询时间"""
    start_time = time.time()
    try:
        result = await db.execute(query)
        return result
    finally:
        duration = time.time() - start_time
        db_query_duration.labels(query_type=query_type).observe(duration)
```

## 最佳实践

### 1. 设置合理的阈值

```yaml
# ❌ 不好：阈值太敏感
- alert: TinyError
  expr: rate(qingyu_requests_total{status=~"5.."}[1m]) > 0

# ✅ 好：合理的阈值
- alert: HighErrorRate
  expr: rate(qingyu_requests_total{status=~"5.."}[5m]) > 0.05
  for: 5m  # 持续 5 分钟
```

### 2. 分级告警

```yaml
# Critical: 立即通知
- match:
    severity: critical
  receiver: pagerduty

# Warning: 延迟通知
- match:
    severity: warning
  receiver: slack

# Info: 仅记录
- match:
    severity: info
  receiver: default
```

### 3. 提供有用的上下文

```yaml
annotations:
  summary: "High error rate detected"
  description: |
    Error rate is {{ $value | humanizePercentage }} for the last 5 minutes
    Service: {{ $labels.service }}
    Instance: {{ $labels.instance }}
    Graph: http://grafana/d/graph
```

## 相关文档

- [生产部署](production.md) - 部署配置
- [Docker 部署](docker.md) - 容器监控
- [日志管理](logging.md) - 日志配置

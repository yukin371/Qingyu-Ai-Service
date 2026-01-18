# 日志管理指南

本指南介绍如何配置和管理 Qingyu Backend AI 的日志系统。

## 日志架构

```
┌─────────────────────────────────────────────────────────┐
│                   日志架构                               │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │   应用层 (Application)                           │   │
│  │   - structlog JSON logger                       │   │
│  │   - 上下文绑定                                  │   │
│  │   - 结构化日志                                  │   │
│  └──────────────┬───────────────────────────────────┘   │
│                 │                                        │
│  ┌──────────────▼───────────────────────────────────┐   │
│  │   传输层 (Transport)                             │   │
│  │   - stdout/stderr                               │   │
│  │   - 文件轮转                                    │   │
│  │   - syslog                                      │   │
│  └──────────────┬───────────────────────────────────┘   │
│                 │                                        │
│  ┌──────────────▼───────────────────────────────────┐   │
│  │   聚合层 (Aggregation)                          │   │
│  │   - Fluentd                                     │   │
│  │   - Logstash                                    │   │
│  │   - Vector                                      │   │
│  └──────────────┬───────────────────────────────────┘   │
│                 │                                        │
│  ┌──────────────▼───────────────────────────────────┐   │
│  │   存储层 (Storage)                              │   │
│  │   - Elasticsearch                               │   │
│  │   - Loki                                        │   │
│  │   - ClickHouse                                  │   │
│  └──────────────┬───────────────────────────────────┘   │
│                 │                                        │
│  ┌──────────────▼───────────────────────────────────┐   │
│  │   可视化层 (Visualization)                       │   │
│  │   - Kibana                                      │   │
│  │   - Grafana                                     │   │
│  │   - Loki Explorer                               │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## 结构化日志

### 配置 structlog

```python
import structlog
import logging
import sys

def configure_logging(
    level: str = "INFO",
    log_file: str = None,
    json_output: bool = True,
):
    """配置结构化日志"""

    # 配置标准库 logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )

    # 配置处理器
    processors = [
        # 添加日志级别
        structlog.stdlib.add_log_level,

        # 添加日志器名称
        structlog.stdlib.add_logger_name,

        # 添加时间戳
        structlog.processors.TimeStamper(fmt="iso"),

        # 添加调用位置
        structlog.processors.CallsiteParameterAdder(
            [
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
                structlog.processors.CallsiteParameter.FUNC_NAME,
            ]
        ),

        # 异常处理
        structlog.processors.UnicodeDecoder(),

        # JSON 渲染器
        structlog.processors.JSONRenderer() if json_output
        else structlog.dev.ConsoleRenderer(),
    ]

    # 文件输出
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, level.upper()))

    # 配置 structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
```

### 使用示例

```python
import structlog

# 获取 logger
logger = structlog.get_logger(__name__)

# 基础日志
logger.info("Application started")

# 带上下文的日志
logger.info("User logged in", user_id="user_123", ip="192.168.1.1")

# 带异常的日志
try:
    result = risky_operation()
except Exception as e:
    logger.error("Operation failed", exc_info=e, operation="risky_operation")

# 警告日志
logger.warning("High memory usage", usage_percent=85.5)

# 调试日志
logger.debug("Processing request", request_id="req_456", data={"key": "value"})
```

### 上下文绑定

```python
from structlog import get_logger

class AgentService:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        # 绑定上下文
        self.logger = get_logger().bind(
            component="AgentService",
            agent_id=agent_id,
        )

    async def execute(self, task: str):
        # 添加临时上下文
        self.logger = self.logger.bind(task_id=generate_id())

        try:
            result = await self._process(task)
            self.logger.info("Task completed", result=result)
            return result
        except Exception as e:
            self.logger.error("Task failed", error=str(e))
            raise
```

## 日志级别

### 级别定义

```python
import structlog

# DEBUG: 详细的调试信息
logger.debug("Variable value", value=x, context=ctx)

# INFO: 一般信息
logger.info("Service started", port=8000)

# WARNING: 警告信息
logger.warning("Connection slow", duration_ms=5000)

# ERROR: 错误信息
logger.error("Request failed", status_code=500, url="/api/endpoint")

# CRITICAL: 严重错误
logger.critical("System shutting down", reason="out_of_memory")
```

### 动态级别

```python
import os
from typing import Optional

class LogLevelManager:
    def __init__(self):
        self.loggers = {}

    def set_level(
        self,
        logger_name: str,
        level: str,
        duration: Optional[int] = None,
    ):
        """动态设置日志级别"""
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, level.upper()))

        # 记录变更
        structlog.get_logger().info(
            "Log level changed",
            logger=logger_name,
            level=level,
            duration=duration,
        )

        # 定时恢复
        if duration:
            asyncio.create_task(self._restore_level(logger_name, duration))

    async def _restore_level(self, logger_name: str, delay: int):
        await asyncio.sleep(delay)
        self.set_level(logger_name, "INFO")
```

## 日志格式

### JSON 格式

```json
{
  "event": "Agent executed",
  "level": "info",
  "timestamp": "2025-01-17T10:30:45.123456Z",
  "logger": "src.services.agent",
  "agent_id": "chatbot",
  "user_id": "user_123",
  "session_id": "sess_456",
  "duration_ms": 1234,
  "tokens_used": 150,
  "filename": "agent.py",
  "lineno": 42,
  "func_name": "execute"
}
```

### 文本格式

```
2025-01-17 10:30:45 [INFO] Agent executed
  agent_id=chatbot user_id=user_123 session_id=sess_456
  duration_ms=1234 tokens_used=150
  file=agent.py:42 in execute
```

### 自定义格式

```python
def custom_formatter(logger, log_method, event_dict):
    """自定义日志格式"""
    return (
        f"[{event_dict['level']}] "
        f"{event_dict['event']} - "
        f"agent={event_dict.get('agent_id', 'N/A')} "
        f"user={event_dict.get('user_id', 'N/A')} "
        f"duration={event_dict.get('duration_ms', 'N/A')}ms"
    )

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        custom_formatter,
    ],
)
```

## 日志轮转

### 文件轮转

```python
import logging
from logging.handlers import RotatingFileHandler
from logging.handlers import TimedRotatingFileHandler

def setup_file_logging(
    log_file: str = "/var/log/qingyu/app.log",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
):
    """设置文件日志轮转"""

    # 按大小轮转
    handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
    )

    # 或按时间轮转
    handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",  # 每天
        interval=1,
        backupCount=30,  # 保留30天
    )

    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter('%(message)s'))

    logger = logging.getLogger()
    logger.addHandler(handler)
```

### Logrotate 配置

```bash
# /etc/logrotate.d/qingyu

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

## 日志聚合

### EFK Stack

```yaml
version: '3.8'

services:
  elasticsearch:
    image: elasticsearch:8.0.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
      - xpack.security.enabled=false
    volumes:
      - es_data:/usr/share/elasticsearch/data
    ports:
      - "9200:9200"
    networks:
      - logging

  fluentd:
    image: fluent/fluentd:v1.14
    volumes:
      - ./fluentd/fluent.conf:/fluentd/etc/fluent.conf
      - /var/log:/var/log
    ports:
      - "24224:24224"
    networks:
      - logging

  kibana:
    image: kibana:8.0.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    networks:
      - logging

volumes:
  es_data:

networks:
  logging:
```

### Fluentd 配置

```xml
<!-- fluentd/fluent.conf -->

<source>
  @type tail
  path /var/log/qingyu/*.log
  pos_file /var/log/fluentd-qingyu.log.pos
  tag qingyu.*
  <parse>
    @type json
  </parse>
</source>

<filter qingyu.**>
  @type record_transformer
  <record>
    hostname "#{Socket.gethostname}"
    tag ${tag}
    timestamp ${time}
  </record>
</filter>

<match qingyu.**>
  @type elasticsearch
  host elasticsearch
  port 9200
  logstash_format true
  logstash_prefix qingyu
  logstash_dateformat %Y%m%d
  include_tag_key true
  type_name _doc
</match>
```

### Loki Stack

```yaml
version: '3.8'

services:
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    command: -config.file=/etc/loki/local-config.yaml
    volumes:
      - ./loki-config.yaml:/etc/loki/local-config.yaml
    networks:
      - logging

  promtail:
    image: grafana/promtail:latest
    volumes:
      - /var/log:/var/log
      - ./promtail-config.yaml:/etc/promtail/config.yml
    networks:
      - logging

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    networks:
      - logging

networks:
  logging:
```

## 日志查询

### Elasticsearch 查询

```python
from elasticsearch import Elasticsearch

class LogQuery:
    def __init__(self, es_host: str = "http://localhost:9200"):
        self.es = Elasticsearch(es_host)
        self.index = "qingyu-*"

    def query_logs(
        self,
        logger_name: str = None,
        level: str = None,
        start_time: str = None,
        end_time: str = None,
        size: int = 100,
    ) -> list:
        """查询日志"""
        query = {
            "query": {
                "bool": {
                    "must": []
                }
            },
            "sort": [
                {"@timestamp": {"order": "desc"}}
            ],
            "size": size,
        }

        # 添加过滤条件
        if logger_name:
            query["query"]["bool"]["must"].append({
                "term": {"logger": logger_name}
            })

        if level:
            query["query"]["bool"]["must"].append({
                "term": {"level": level}
            })

        if start_time or end_time:
            range_filter = {"range": {"@timestamp": {}}}
            if start_time:
                range_filter["range"]["@timestamp"]["gte"] = start_time
            if end_time:
                range_filter["range"]["@timestamp"]["lte"] = end_time
            query["query"]["bool"]["must"].append(range_filter)

        # 执行查询
        response = self.es.search(index=self.index, body=query)
        return [hit["_source"] for hit in response["hits"]["hits"]]

    def count_errors(self, last_hours: int = 24) -> int:
        """统计错误数量"""
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"level": "error"}},
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": f"now-{last_hours}h"
                                }
                            }
                        }
                    ]
                }
            }
        }

        response = self.es.count(index=self.index, body=query)
        return response["count"]
```

### Grafana Loki 查询

```logql
# 查询所有错误日志
{level="error"} |= "error"

# 查询特定 Agent 的日志
{agent_id="chatbot"}

# 查询响应时间超过 1 秒的请求
{level="info"} | json | duration_ms > 1000

# 统计每分钟的错误率
rate({level="error"}[1m])

# 查询包含特定文本的日志
{~"timeout"}
```

## 性能考虑

### 异步日志

```python
import queue
import threading
from structlog import get_logger

class AsyncHandler:
    """异步日志处理器"""

    def __init__(self, handler):
        self.handler = handler
        self.queue = queue.Queue(maxsize=1000)
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _worker(self):
        """工作线程"""
        while True:
            try:
                record = self.queue.get(timeout=1)
                if record is None:
                    break
                self.handler.emit(record)
            except queue.Empty:
                continue

    def emit(self, record):
        """异步发送"""
        try:
            self.queue.put_nowait(record)
        except queue.Full:
            # 队列满时丢弃
            pass

    def close(self):
        """关闭处理器"""
        self.queue.put(None)
        self.thread.join()
```

### 日志采样

```python
import random
from typing import Optional

class SamplingLogger:
    """采样日志器"""

    def __init__(self, sample_rate: float = 0.1):
        self.sample_rate = sample_rate
        self.logger = get_logger()

    def log(self, level: str, event: str, **kwargs):
        """采样记录"""
        if random.random() < self.sample_rate:
            getattr(self.logger, level)(
                event,
                sampled=True,
                sample_rate=self.sample_rate,
                **kwargs
            )

# 使用
sampler = SamplingLogger(sample_rate=0.01)  # 1% 采样
sampler.log("info", "Request received", path="/api/endpoint")
```

## 监控告警

### 错误率监控

```python
from elasticsearch import Elasticsearch

class LogAlertManager:
    def __init__(self, es_host: str):
        self.es = Elasticsearch(es_host)

    async def check_error_rate(
        self,
        threshold: float = 0.05,  # 5%
        window_minutes: int = 5,
    ) -> bool:
        """检查错误率"""
        # 查询总请求数
        total_query = {
            "query": {
                "range": {
                    "@timestamp": {
                        "gte": f"now-{window_minutes}m"
                    }
                }
            }
        }
        total = self.es.count(index="qingyu-*", body=total_query)["count"]

        # 查询错误数
        error_query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"level": "error"}},
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": f"now-{window_minutes}m"
                                }
                            }
                        }
                    ]
                }
            }
        }
        errors = self.es.count(index="qingyu-*", body=error_query)["count"]

        # 计算错误率
        error_rate = errors / total if total > 0 else 0

        if error_rate > threshold:
            await self.send_alert(
                f"High error rate: {error_rate:.2%}",
                errors=errors,
                total=total,
            )
            return True

        return False
```

## 最佳实践

### 1. 结构化数据

```python
# ✅ 好：结构化数据
logger.info(
    "Agent executed",
    agent_id="chatbot",
    duration_ms=1234,
    tokens=150,
    success=True,
)

# ❌ 不好：非结构化数据
logger.info(
    f"Agent chatbot executed in 1234ms using 150 tokens"
)
```

### 2. 适当的日志级别

```python
# ✅ 好：正确使用级别
logger.debug("Processing item", item_id=1)
logger.info("User action", action="login")
logger.warning("Slow query", duration_ms=5000)
logger.error("API error", status_code=500)

# ❌ 不好：滥用级别
logger.error("User logged in", user_id="user_123")  # 应该用 info
logger.info("Database connection lost", error=e)    # 应该用 error
```

### 3. 避免敏感信息

```python
import re

def sanitize_log(data: dict) -> dict:
    """清理敏感信息"""
    sensitive_fields = ['password', 'token', 'api_key', 'secret']

    sanitized = data.copy()
    for field in sensitive_fields:
        if field in sanitized:
            sanitized[field] = "***REDACTED***"

    return sanitized

# 使用
logger.info("User login", **sanitize_log({
    "username": "user_123",
    "password": "secret123",  # 会被清理
}))
```

### 4. 上下文丰富

```python
# ✅ 好：丰富的上下文
logger.info(
    "API request",
    method="POST",
    path="/api/agents",
    status_code=201,
    duration_ms=123,
    user_id="user_123",
    request_id="req_456",
    ip="192.168.1.1",
    user_agent="Mozilla/5.0...",
)

# ❌ 不好：缺少上下文
logger.info("API request successful")
```

### 5. 日志ID追踪

```python
from contextvars import ContextVar
import uuid

# 请求上下文
request_id_var: ContextVar[str] = ContextVar('request_id', default='')

class RequestMiddleware:
    async def process(self, request, call_next):
        # 生成请求ID
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)

        # 绑定到 logger
        logger = structlog.get_logger().bind(request_id=request_id)

        # 处理请求
        response = await call_next(request)

        return response

# 在任何地方使用
logger = structlog.get_logger()
logger.info("Processing")  # 自动包含 request_id
```

## 相关文档

- [生产部署](production.md) - 部署配置
- [监控告警](monitoring.md) - 监控配置
- [Docker 部署](docker.md) - 容器日志

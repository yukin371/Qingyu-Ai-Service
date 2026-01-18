"""
Monitoring - 监控模块

提供指标收集和性能追踪功能。
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from collections import defaultdict
from datetime import datetime

from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


# =============================================================================
# Metric Types
# =============================================================================

class Metric(BaseModel):
    """
    指标数据

    Attributes:
        name: 指标名称
        value: 指标值
        timestamp: 时间戳
        labels: 标签
    """

    name: str = Field(..., description="Metric name")
    value: float = Field(..., description="Metric value")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp")
    labels: Dict[str, str] = Field(default_factory=dict, description="Labels")


class MetricCounter(BaseModel):
    """
    计数器指标

    Attributes:
        name: 指标名称
        count: 计数值
        labels: 标签
    """

    name: str = Field(..., description="Counter name")
    count: int = Field(default=0, description="Count value")
    labels: Dict[str, str] = Field(default_factory=dict, description="Labels")


class MetricHistogram(BaseModel):
    """
    直方图指标

    Attributes:
        name: 指标名称
        count: 样本数量
        sum: 总和
        buckets: 分桶数据
        labels: 标签
    """

    name: str = Field(..., description="Histogram name")
    count: int = Field(default=0, description="Sample count")
    sum: float = Field(default=0.0, description="Sum of values")
    buckets: Dict[str, int] = Field(default_factory=dict, description="Bucket counts")
    labels: Dict[str, str] = Field(default_factory=dict, description="Labels")


# =============================================================================
# Metrics Collector
# =============================================================================

class MetricsCollector:
    """
    指标收集器

    收集和存储应用程序指标。

    使用示例:
        ```python
        collector = MetricsCollector()

        # 计数
        collector.increment("requests_total", labels={"endpoint": "/api/chat"})

        # 记录执行时间
        with collector.timer("execution_time"):
            # do work
            pass

        # 记录值
        collector.gauge("active_connections", 100)
        ```
    """

    def __init__(self):
        """初始化指标收集器"""
        self._counters: Dict[str, MetricCounter] = {}
        self._gauges: Dict[str, Metric] = {}
        self._histograms: Dict[str, MetricHistogram] = {}
        self._lock = asyncio.Lock()

        logger.info("Created MetricsCollector")

    async def increment(
        self,
        name: str,
        value: int = 1,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        增加计数器

        Args:
            name: 指标名称
            value: 增加值
            labels: 标签
        """
        key = self._make_key(name, labels)

        async with self._lock:
            if key not in self._counters:
                self._counters[key] = MetricCounter(name=name, labels=labels or {})

            self._counters[key].count += value

        logger.debug(f"Incremented counter: {name}+{value}")

    async def decrement(
        self,
        name: str,
        value: int = 1,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        减少计数器

        Args:
            name: 指标名称
            value: 减少值
            labels: 标签
        """
        await self.increment(name, -value, labels)

    async def gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        设置仪表值

        Args:
            name: 指标名称
            value: 指标值
            labels: 标签
        """
        key = self._make_key(name, labels)

        async with self._lock:
            self._gauges[key] = Metric(
                name=name,
                value=value,
                labels=labels or {},
            )

        logger.debug(f"Set gauge: {name}={value}")

    async def histogram(
        self,
        name: str,
        value: float,
        buckets: Optional[List[float]] = None,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        记录直方图值

        Args:
            name: 指标名称
            value: 观测值
            buckets: 分桶边界
            labels: 标签
        """
        key = self._make_key(name, labels)
        default_buckets = [0.1, 0.5, 1.0, 5.0, 10.0, 60.0, 300.0]

        async with self._lock:
            if key not in self._histograms:
                self._histograms[key] = MetricHistogram(
                    name=name,
                    buckets={f"le_{b}": 0 for b in (buckets or default_buckets)},
                    labels=labels or {},
                )

            hist = self._histograms[key]
            hist.count += 1
            hist.sum += value

            # 更新分桶
            for bucket in hist.buckets:
                threshold = float(bucket.split("_")[1])
                if value <= threshold:
                    hist.buckets[bucket] += 1

        logger.debug(f"Recorded histogram: {name}={value}")

    def _make_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """生成指标键"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def timer(self, name: str, labels: Optional[Dict[str, str]] = None):
        """
        计时器上下文管理器

        Args:
            name: 指标名称
            labels: 标签

        Returns:
            上下文管理器
        """
        return _TimerContext(self, name, labels)

    async def get_metrics(self) -> Dict[str, Any]:
        """
        获取所有指标

        Returns:
            指标字典
        """
        async with self._lock:
            return {
                "counters": [m.model_dump() for m in self._counters.values()],
                "gauges": [m.model_dump() for m in self._gauges.values()],
                "histograms": [m.model_dump() for m in self._histograms.values()],
            }

    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> int:
        """获取计数器值"""
        key = self._make_key(name, labels)
        return self._counters.get(key, MetricCounter(name=name)).count

    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
        """获取仪表值"""
        key = self._make_key(name, labels)
        metric = self._gauges.get(key)
        return metric.value if metric else None

    async def reset(self) -> None:
        """重置所有指标"""
        async with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()

        logger.info("Reset all metrics")


# =============================================================================
# Timer Context
# =============================================================================

class _TimerContext:
    """计时器上下文管理器"""

    def __init__(
        self,
        collector: MetricsCollector,
        name: str,
        labels: Optional[Dict[str, str]],
    ):
        self.collector = collector
        self.name = name
        self.labels = labels
        self.start_time = None
        self._duration = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            self._duration = time.time() - self.start_time
            # Create task but don't await - sync context manager can't be async
            # Store duration for manual recording if needed
            asyncio.create_task(
                self.collector.histogram(self.name, self._duration, labels=self.labels)
            )

    async def __aenter__(self):
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            await self.collector.histogram(self.name, duration, labels=self.labels)


# =============================================================================
# Global Metrics Collector
# =============================================================================

_global_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """获取全局指标收集器"""
    global _global_metrics_collector
    if _global_metrics_collector is None:
        _global_metrics_collector = MetricsCollector()
    return _global_metrics_collector

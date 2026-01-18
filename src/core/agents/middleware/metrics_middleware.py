"""
指标中间件 - 收集性能指标
"""

import time
from typing import Dict, Any
from langchain_core.runnables import RunnableConfig
from prometheus_client import Counter, Histogram

# Prometheus 指标
agent_calls_total = Counter(
    "agent_calls_total", "Total agent calls", ["agent_name", "status"]
)

agent_duration_seconds = Histogram(
    "agent_duration_seconds", "Agent execution duration", ["agent_name"]
)

tool_calls_total = Counter(
    "tool_calls_total", "Total tool calls", ["tool_name", "agent_name", "status"]
)


class MetricsMiddleware:
    """指标中间件 - 收集性能指标"""

    def __init__(self):
        self.start_time = None
        self.agent_name = None

    async def before_model(
        self, inputs: Dict[str, Any], config: RunnableConfig
    ) -> Dict[str, Any]:
        """记录开始时间"""
        self.start_time = time.time()
        self.agent_name = config.get("configurable", {}).get("agent_name", "unknown")
        return inputs

    async def after_model(self, output: Any, config: RunnableConfig) -> Any:
        """记录执行时间和成功指标"""
        if self.start_time:
            duration = time.time() - self.start_time

            agent_calls_total.labels(
                agent_name=self.agent_name, status="success"
            ).inc()

            agent_duration_seconds.labels(agent_name=self.agent_name).observe(duration)

        return output

    def on_error(self, error: Exception, config: RunnableConfig) -> None:
        """记录失败指标"""
        agent_calls_total.labels(agent_name=self.agent_name, status="error").inc()



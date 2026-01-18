"""
工具调用包装中间件 - 统一工具调用日志和错误处理
"""

from typing import Dict, Any, Callable, Awaitable
from langchain_core.runnables import RunnableConfig
from src.core.logger import get_logger
from .metrics_middleware import tool_calls_total

logger = get_logger(__name__)


class ToolWrapperMiddleware:
    """工具调用包装 - 统一工具调用日志和错误处理"""

    async def wrap_tool_call(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_func: Callable[..., Awaitable[Any]],
        config: RunnableConfig,
    ) -> Any:
        """包装工具调用"""
        agent_name = config.get("configurable", {}).get("agent_name", "unknown")

        logger.info(f"Tool call started: {tool_name}", input=tool_input)

        try:
            result = await tool_func(tool_input)
            logger.info(f"Tool call succeeded: {tool_name}")

            # 记录成功指标
            tool_calls_total.labels(
                tool_name=tool_name, agent_name=agent_name, status="success"
            ).inc()

            return result

        except Exception as e:
            logger.error(
                f"Tool call failed: {tool_name}", error=str(e), exc_info=True
            )

            # 记录失败指标
            tool_calls_total.labels(
                tool_name=tool_name, agent_name=agent_name, status="error"
            ).inc()

            raise



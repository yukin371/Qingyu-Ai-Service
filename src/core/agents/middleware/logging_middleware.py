"""
日志中间件 - 记录所有 Agent 执行过程
"""

from typing import Dict, Any
from langchain_core.runnables import RunnableConfig
from src.core.logger import get_logger

logger = get_logger(__name__)


class LoggingMiddleware:
    """日志中间件 - 记录所有 Agent 执行"""

    async def before_model(
        self, inputs: Dict[str, Any], config: RunnableConfig
    ) -> Dict[str, Any]:
        """LLM 调用前记录"""
        configurable = config.get("configurable", {})
        logger.info(
            "Agent execution started",
            agent=configurable.get("agent_name"),
            input_length=len(str(inputs)),
            thread_id=configurable.get("thread_id"),
        )
        return inputs

    async def after_model(self, output: Any, config: RunnableConfig) -> Any:
        """LLM 调用后记录"""
        logger.info("Agent execution completed", output_length=len(str(output)))
        return output

    def on_error(self, error: Exception, config: RunnableConfig) -> None:
        """错误处理"""
        configurable = config.get("configurable", {})
        logger.error(
            "Agent execution failed",
            agent=configurable.get("agent_name"),
            error=str(error),
            exc_info=True,
        )



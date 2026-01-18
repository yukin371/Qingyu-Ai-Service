"""
错误处理中间件 - 统一错误处理和降级策略
"""

from typing import Dict, Any, Optional
from langchain_core.runnables import RunnableConfig
from src.core.logger import get_logger
from src.core.exceptions import AgentExecutionError

logger = get_logger(__name__)


class ErrorHandlingMiddleware:
    """错误处理中间件 - 统一错误处理和降级策略"""

    def __init__(self, enable_fallback: bool = True, max_retries: int = 3):
        self.enable_fallback = enable_fallback
        self.max_retries = max_retries
        self.retry_count = 0

    async def before_model(
        self, inputs: Dict[str, Any], config: RunnableConfig
    ) -> Dict[str, Any]:
        """执行前检查"""
        # 可以在这里添加预检查逻辑
        return inputs

    async def after_model(self, output: Any, config: RunnableConfig) -> Any:
        """执行后检查"""
        # 重置重试计数
        self.retry_count = 0
        return output

    def on_error(self, error: Exception, config: RunnableConfig) -> Optional[Dict]:
        """错误处理"""
        agent_name = config.get("configurable", {}).get("agent_name", "unknown")

        logger.error(
            f"Error in agent {agent_name}",
            error=str(error),
            retry_count=self.retry_count,
            exc_info=True,
        )

        # 检查是否需要重试
        if self.retry_count < self.max_retries:
            self.retry_count += 1
            logger.info(
                f"Retrying agent {agent_name}", retry_count=self.retry_count
            )
            return {"action": "retry"}

        # 如果启用降级，返回降级响应
        if self.enable_fallback:
            logger.warning(f"Max retries reached for {agent_name}, using fallback")
            return {
                "action": "fallback",
                "fallback_response": "抱歉，服务暂时不可用，请稍后重试。",
            }

        # 否则，抛出异常
        raise AgentExecutionError(f"Agent {agent_name} execution failed") from error



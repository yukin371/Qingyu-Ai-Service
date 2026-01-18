"""
创作 Agent 统一实现 - 基于 LangChain 1.0

这是一个示例实现，展示如何使用新的 BaseAgentUnified 基类
"""

from typing import List
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from src.core.agents.base_agent_unified import BaseAgentUnified
from src.core.agents.middleware import LoggingMiddleware, MetricsMiddleware
from src.core.agents.checkpointers import PostgresCheckpointer
from src.core.logger import get_logger

logger = get_logger(__name__)


class CreativeAgentUnified(BaseAgentUnified):
    """创作 Agent - 统一实现

    使用 LangChain 1.0 create_agent() 接口实现的创作 Agent
    """

    def __init__(
        self,
        llm: BaseChatModel,
        tools: List[BaseTool] = None,
        enable_checkpointer: bool = True,
        enable_middleware: bool = True,
        **kwargs
    ):
        """初始化创作 Agent

        Args:
            llm: LLM 实例
            tools: 工具列表
            enable_checkpointer: 是否启用持久化
            enable_middleware: 是否启用中间件
            **kwargs: 额外参数
        """
        # 准备 Middleware
        middleware = []
        if enable_middleware:
            middleware = [
                LoggingMiddleware(),
                MetricsMiddleware(),
            ]

        # 准备 Checkpointer
        checkpointer = None
        if enable_checkpointer:
            try:
                checkpointer = PostgresCheckpointer()
                logger.info("PostgresCheckpointer enabled for CreativeAgent")
            except Exception as e:
                logger.warning(
                    f"Failed to initialize checkpointer: {e}. "
                    "Agent will run without persistence."
                )

        # 调用父类初始化
        super().__init__(
            agent_name="creative_agent",
            llm=llm,
            tools=tools or [],
            agent_type="react",  # 使用 ReAct 类型
            checkpointer=checkpointer,
            middleware=middleware,
            **kwargs
        )

    def get_agent_name(self) -> str:
        """获取 Agent 名称"""
        return "CreativeAgent"

    def get_agent_description(self) -> str:
        """获取 Agent 描述"""
        return (
            "创作 Agent，负责生成小说内容。"
            "支持续写、创作新章节等功能。"
        )


# 使用示例
if __name__ == "__main__":
    import asyncio
    from langchain_openai import ChatOpenAI
    from core.config import get_settings

    async def main():
        """使用示例"""
        settings = get_settings()

        # 创建 LLM
        llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            model="gpt-4-turbo-preview",
        )

        # 创建 Agent
        agent = CreativeAgentUnified(
            llm=llm,
            tools=[],  # 可以添加工具
            enable_checkpointer=True,
            enable_middleware=True,
        )

        # 执行任务
        result = await agent.execute(
            input_data={"input": "写一段武侠小说的开头"},
            config={
                "configurable": {
                    "thread_id": "test_session_001"
                }
            }
        )

        print(f"Result: {result}")

        # 恢复执行（如果中断）
        # resumed = await agent.resume(
        #     thread_id="test_session_001",
        #     input_data=None  # None 表示从 checkpoint 恢复
        # )

    asyncio.run(main())



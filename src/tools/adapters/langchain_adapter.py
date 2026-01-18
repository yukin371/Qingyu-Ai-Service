"""
LangChain工具适配器

将MCP工具适配为LangChain Tool
"""
from typing import Any, Dict, Optional, Type

from langchain_core.tools import BaseTool as LangChainBaseTool
from pydantic import BaseModel

from src.core.logger import get_logger
from src.tools.base import BaseTool, ToolResult

logger = get_logger(__name__)


class LangChainToolAdapter(LangChainBaseTool):
    """LangChain工具适配器

    将MCP BaseTool适配为LangChain Tool，支持：
    - 统一的输入验证
    - 异步执行
    - 错误处理
    - 结果转换
    """

    # LangChain Tool必需字段
    name: str
    description: str
    args_schema: Type[BaseModel]

    # MCP Tool实例
    mcp_tool: BaseTool

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, mcp_tool: BaseTool, **kwargs):
        """初始化适配器

        Args:
            mcp_tool: MCP工具实例
            **kwargs: 额外参数
        """
        super().__init__(
            name=mcp_tool.metadata.name,
            description=mcp_tool.metadata.description,
            args_schema=mcp_tool.input_schema,
            mcp_tool=mcp_tool,
            **kwargs,
        )

        logger.info(f"LangChain adapter created for tool: {mcp_tool.metadata.name}")

    def _run(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """同步执行（LangChain要求）

        Note: MCP工具是异步的，这里不支持同步调用
        """
        raise NotImplementedError(
            f"Tool {self.name} does not support synchronous execution. "
            "Please use ainvoke() instead."
        )

    async def _arun(
        self,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """异步执行（LangChain要求）

        Args:
            **kwargs: 工具输入参数

        Returns:
            Dict: 执行结果（转换为字典）
        """
        try:
            logger.info(f"Executing MCP tool via LangChain adapter: {self.name}")

            # 执行MCP工具
            result: ToolResult = await self.mcp_tool.execute(kwargs)

            # 转换结果为LangChain期望的格式
            if result.success:
                return {
                    "success": True,
                    "data": result.data,
                    "message": result.message,
                    "tool_name": result.tool_name,
                    "execution_time": result.execution_time,
                    "tokens_used": result.tokens_used,
                }
            else:
                return {
                    "success": False,
                    "error": result.error,
                    "message": result.message,
                    "tool_name": result.tool_name,
                }

        except Exception as e:
            logger.error(
                f"LangChain adapter execution failed for tool {self.name}",
                exc_info=True,
            )
            return {
                "success": False,
                "error": str(e),
                "tool_name": self.name,
            }

    def to_langchain_tool(self) -> "LangChainToolAdapter":
        """转换为LangChain Tool（已经是）"""
        return self


def adapt_mcp_tool_to_langchain(mcp_tool: BaseTool) -> LangChainToolAdapter:
    """将MCP工具适配为LangChain Tool

    Args:
        mcp_tool: MCP工具实例

    Returns:
        LangChainToolAdapter: LangChain工具适配器
    """
    return LangChainToolAdapter(mcp_tool=mcp_tool)


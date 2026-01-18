"""Tool注册表

管理所有可用的Tool实例
"""

from typing import Dict, List, Optional, Type

from src.core.logger import get_logger
from src.core.tools.base import BaseTool, ToolMetadata

logger = get_logger(__name__)


class ToolRegistry:
    """工具注册表

    特性：
    - 工具注册和查询
    - 按分类获取工具
    - 工具元数据管理
    """

    def __init__(self):
        """初始化注册表"""
        self._tools: Dict[str, BaseTool] = {}
        self._tool_classes: Dict[str, Type[BaseTool]] = {}
        logger.info("ToolRegistry initialized")

    def register_tool_class(self, tool_class: Type[BaseTool]) -> None:
        """注册工具类

        Args:
            tool_class: Tool类（必须继承BaseTool）
        """
        # 获取工具名称（通过临时实例）
        # 注意：这里需要子类提供无参构造或默认参数
        tool_name = tool_class.__name__.replace("Tool", "").lower() + "_tool"

        self._tool_classes[tool_name] = tool_class
        logger.info(f"Registered tool class: {tool_name}")

    def register_tool_instance(self, tool: BaseTool) -> None:
        """注册工具实例

        Args:
            tool: Tool实例
        """
        self._tools[tool.metadata.name] = tool
        logger.info(f"Registered tool instance: {tool.metadata.name}")

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """获取工具实例

        Args:
            tool_name: 工具名称

        Returns:
            Tool实例，不存在返回None
        """
        return self._tools.get(tool_name)

    def list_tools(self) -> List[ToolMetadata]:
        """列出所有工具

        Returns:
            工具元数据列表
        """
        return [tool.metadata for tool in self._tools.values()]

    def get_tools_by_category(self, category: str) -> List[BaseTool]:
        """按分类获取工具

        Args:
            category: 分类名称（writing, knowledge, analysis等）

        Returns:
            Tool实例列表
        """
        return [
            tool for tool in self._tools.values() if tool.metadata.category == category
        ]

    def get_all_tools(self) -> List[BaseTool]:
        """获取所有工具实例

        Returns:
            Tool实例列表
        """
        return list(self._tools.values())

    def tool_exists(self, tool_name: str) -> bool:
        """检查工具是否存在

        Args:
            tool_name: 工具名称

        Returns:
            是否存在
        """
        return tool_name in self._tools

    def unregister_tool(self, tool_name: str) -> bool:
        """注销工具

        Args:
            tool_name: 工具名称

        Returns:
            是否成功
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")
            return True
        return False

    def clear(self) -> None:
        """清空注册表"""
        self._tools.clear()
        self._tool_classes.clear()
        logger.info("ToolRegistry cleared")


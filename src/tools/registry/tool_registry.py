"""
工具注册机制

管理工具的注册、查找和获取
"""
from typing import Dict, List, Optional, Type

from src.core.logger import get_logger
from src.tools.base import BaseTool, ToolCategory, ToolMetadata

logger = get_logger(__name__)


class ToolRegistry:
    """工具注册中心

    管理所有可用工具的注册和查找
    """

    def __init__(self):
        """初始化注册中心"""
        self._tools: Dict[str, Type[BaseTool]] = {}
        self._tool_instances: Dict[str, BaseTool] = {}
        self._tool_metadata: Dict[str, ToolMetadata] = {}

        logger.info("Tool registry initialized")

    # ===== 注册工具 =====

    def register(
        self,
        tool_class: Type[BaseTool],
        metadata: Optional[ToolMetadata] = None,
        override: bool = False,
    ) -> None:
        """注册工具类

        Args:
            tool_class: 工具类
            metadata: 工具元数据（可选，从实例获取）
            override: 是否覆盖已存在的工具

        Raises:
            ValueError: 工具已存在且不允许覆盖
        """
        # 创建临时实例获取元数据（如果未提供）
        if metadata is None:
            temp_instance = tool_class(
                metadata=ToolMetadata(
                    name="temp",
                    description="temp",
                    category=ToolCategory.SYSTEM,
                )
            )
            metadata = temp_instance.metadata

        tool_name = metadata.name

        # 检查是否已存在
        if tool_name in self._tools and not override:
            raise ValueError(
                f"Tool '{tool_name}' is already registered. "
                f"Use override=True to replace it."
            )

        # 注册工具
        self._tools[tool_name] = tool_class
        self._tool_metadata[tool_name] = metadata

        logger.info(
            f"Tool registered: {tool_name} (v{metadata.version}, "
            f"category={metadata.category})"
        )

    def register_instance(
        self,
        tool_instance: BaseTool,
        override: bool = False,
    ) -> None:
        """注册工具实例

        Args:
            tool_instance: 工具实例
            override: 是否覆盖已存在的实例

        Raises:
            ValueError: 实例已存在且不允许覆盖
        """
        tool_name = tool_instance.metadata.name

        # 检查是否已存在
        if tool_name in self._tool_instances and not override:
            raise ValueError(
                f"Tool instance '{tool_name}' is already registered. "
                f"Use override=True to replace it."
            )

        # 注册实例
        self._tool_instances[tool_name] = tool_instance
        self._tool_metadata[tool_name] = tool_instance.metadata

        # 同时注册类
        if tool_name not in self._tools:
            self._tools[tool_name] = type(tool_instance)

        logger.info(f"Tool instance registered: {tool_name}")

    def unregister(self, tool_name: str) -> None:
        """注销工具

        Args:
            tool_name: 工具名称
        """
        if tool_name in self._tools:
            del self._tools[tool_name]

        if tool_name in self._tool_instances:
            del self._tool_instances[tool_name]

        if tool_name in self._tool_metadata:
            del self._tool_metadata[tool_name]

        logger.info(f"Tool unregistered: {tool_name}")

    # ===== 获取工具 =====

    def get_tool_class(self, tool_name: str) -> Optional[Type[BaseTool]]:
        """获取工具类

        Args:
            tool_name: 工具名称

        Returns:
            Optional[Type[BaseTool]]: 工具类，不存在则返回None
        """
        return self._tools.get(tool_name)

    def get_tool_instance(self, tool_name: str) -> Optional[BaseTool]:
        """获取工具实例

        Args:
            tool_name: 工具名称

        Returns:
            Optional[BaseTool]: 工具实例，不存在则返回None
        """
        return self._tool_instances.get(tool_name)

    def get_tool_metadata(self, tool_name: str) -> Optional[ToolMetadata]:
        """获取工具元数据

        Args:
            tool_name: 工具名称

        Returns:
            Optional[ToolMetadata]: 工具元数据，不存在则返回None
        """
        return self._tool_metadata.get(tool_name)

    def create_tool_instance(
        self,
        tool_name: str,
        auth_context: Optional[Dict] = None,
        **kwargs,
    ) -> Optional[BaseTool]:
        """创建工具实例

        Args:
            tool_name: 工具名称
            auth_context: 认证上下文
            **kwargs: 额外参数

        Returns:
            Optional[BaseTool]: 工具实例，工具不存在则返回None
        """
        tool_class = self.get_tool_class(tool_name)
        if tool_class is None:
            logger.warning(f"Tool '{tool_name}' not found in registry")
            return None

        metadata = self.get_tool_metadata(tool_name)
        instance = tool_class(metadata=metadata, auth_context=auth_context, **kwargs)

        logger.info(f"Tool instance created: {tool_name}")
        return instance

    # ===== 查询工具 =====

    def list_tools(
        self,
        category: Optional[ToolCategory] = None,
        requires_auth: Optional[bool] = None,
        tags: Optional[List[str]] = None,
    ) -> List[str]:
        """列出工具

        Args:
            category: 按类别筛选
            requires_auth: 按认证要求筛选
            tags: 按标签筛选

        Returns:
            List[str]: 工具名称列表
        """
        tools = []

        for tool_name, metadata in self._tool_metadata.items():
            # 筛选类别
            if category is not None and metadata.category != category:
                continue

            # 筛选认证要求
            if requires_auth is not None and metadata.requires_auth != requires_auth:
                continue

            # 筛选标签
            if tags is not None:
                if not any(tag in metadata.tags for tag in tags):
                    continue

            tools.append(tool_name)

        return tools

    def list_all_tools(self) -> List[str]:
        """列出所有工具

        Returns:
            List[str]: 所有工具名称列表
        """
        return list(self._tools.keys())

    def get_tools_by_category(self, category: ToolCategory) -> List[str]:
        """获取指定类别的工具

        Args:
            category: 工具类别

        Returns:
            List[str]: 工具名称列表
        """
        return self.list_tools(category=category)

    def is_tool_registered(self, tool_name: str) -> bool:
        """检查工具是否已注册

        Args:
            tool_name: 工具名称

        Returns:
            bool: 是否已注册
        """
        return tool_name in self._tools

    def get_tool_count(self) -> int:
        """获取工具数量

        Returns:
            int: 工具数量
        """
        return len(self._tools)

    def clear(self) -> None:
        """清空注册中心"""
        self._tools.clear()
        self._tool_instances.clear()
        self._tool_metadata.clear()
        logger.info("Tool registry cleared")

    def __str__(self) -> str:
        return f"ToolRegistry({self.get_tool_count()} tools)"

    def __repr__(self) -> str:
        return self.__str__()


# ===== 全局注册中心 =====

_global_tool_registry: Optional[ToolRegistry] = None


def get_global_tool_registry() -> ToolRegistry:
    """获取全局工具注册中心

    Returns:
        ToolRegistry: 全局工具注册中心（单例）
    """
    global _global_tool_registry

    if _global_tool_registry is None:
        _global_tool_registry = ToolRegistry()
        logger.info("Global tool registry created")

    return _global_tool_registry


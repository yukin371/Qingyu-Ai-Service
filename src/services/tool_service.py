"""Tool Service - 工具服务

管理Tool的注册、执行和查询
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from collections import defaultdict

from src.core.logger import get_logger  # pylint: disable=import-error
from src.core.tools.base import BaseTool, ToolMetadata, ToolResult  # pylint: disable=import-error
from src.core.tools.langchain import CharacterTool, OutlineTool, RAGTool  # pylint: disable=import-error
from src.core.tools.registry import ToolRegistry  # pylint: disable=import-error
from src.infrastructure.go_api import GoAPIClient  # pylint: disable=import-error

logger = get_logger(__name__)


class ToolService:
    """工具服务

    特性：
    - Tool注册和管理
    - Tool执行（带权限检查）
    - Tool列表查询
    """

    def __init__(self):
        """初始化服务"""
        self.registry = ToolRegistry()
        self.go_api_client: Optional[GoAPIClient] = None
        self._initialized = False

        # 执行统计
        self._execution_stats = defaultdict(lambda: {
            "total": 0,
            "success": 0,
            "failure": 0,
            "total_duration_ms": 0,
        })

        # Tool执行缓存（可选）
        self._cache_enabled = False
        self._cache: Dict[str, ToolResult] = {}

        logger.info("ToolService created")

    async def initialize(self) -> None:
        """初始化服务"""
        if self._initialized:
            return

        logger.info("Initializing ToolService...")

        # 初始化Go API客户端
        self.go_api_client = GoAPIClient()
        await self.go_api_client.initialize()

        # 注册内置工具
        await self._register_builtin_tools()

        self._initialized = True
        logger.info("ToolService initialized successfully")

    async def _register_builtin_tools(self) -> None:
        """注册内置工具"""
        logger.info("Registering builtin tools...")

        # 注册RAGTool
        rag_tool = RAGTool()
        self.registry.register_tool_instance(rag_tool)
        logger.info("Registered RAGTool")

        # 注册CharacterTool
        character_tool = CharacterTool(go_api_client=self.go_api_client)
        self.registry.register_tool_instance(character_tool)
        logger.info("Registered CharacterTool")

        # 注册OutlineTool
        outline_tool = OutlineTool(go_api_client=self.go_api_client)
        self.registry.register_tool_instance(outline_tool)
        logger.info("Registered OutlineTool")

        logger.info(f"Registered {len(self.registry.list_tools())} builtin tools")

    async def execute_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        agent_call_id: Optional[str] = None,
        use_cache: bool = False,
    ) -> ToolResult:
        """执行工具

        Args:
            tool_name: 工具名称
            params: 工具参数
            user_id: 用户ID
            project_id: 项目ID
            agent_call_id: Agent调用ID
            use_cache: 是否使用缓存

        Returns:
            工具执行结果
        """
        if not self._initialized:
            await self.initialize()

        # 获取工具
        tool = self.registry.get_tool(tool_name)
        if not tool:
            logger.error(f"Tool not found: {tool_name}")
            return ToolResult(success=False, error=f"Tool not found: {tool_name}")

        # 检查缓存
        cache_key = None
        if use_cache and self._cache_enabled:
            cache_key = self._make_cache_key(tool_name, params, user_id, project_id)
            if cache_key in self._cache:
                logger.info(f"Tool cache hit: {tool_name}")
                return self._cache[cache_key]

        # 权限检查（如果需要）
        if not await self._check_permission(tool_name, user_id, project_id):
            logger.warning(f"Permission denied for tool: {tool_name}", user_id=user_id)
            return ToolResult(
                success=False,
                error=f"Permission denied for tool: {tool_name}"
            )

        # 执行工具
        logger.info(f"Executing tool: {tool_name}", params=params)

        try:
            result = await tool.execute(
                params=params,
                user_id=user_id,
                project_id=project_id,
                agent_call_id=agent_call_id,
            )

            # 更新统计
            self._update_stats(tool_name, result)

            # 缓存结果
            if use_cache and self._cache_enabled and cache_key and result.success:
                self._cache[cache_key] = result

            logger.info(
                f"Tool execution completed: {tool_name}",
                success=result.success,
                duration_ms=result.duration_ms,
            )

            return result

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Tool execution error: {tool_name}", error=str(e), exc_info=True)

            # 记录失败统计
            self._execution_stats[tool_name]["total"] += 1
            self._execution_stats[tool_name]["failure"] += 1

            return ToolResult(
                success=False,
                error=f"Tool execution error: {str(e)}"
            )

    def list_tools(self) -> List[ToolMetadata]:
        """列出所有工具

        Returns:
            工具元数据列表
        """
        return self.registry.list_tools()

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """获取工具实例

        Args:
            tool_name: 工具名称

        Returns:
            工具实例（如果存在）
        """
        return self.registry.get_tool(tool_name)

    def get_tools_by_category(self, category: str) -> List[BaseTool]:
        """按分类获取工具

        Args:
            category: 分类名称

        Returns:
            工具列表
        """
        return self.registry.get_tools_by_category(category)

    async def execute_tools_batch(
        self,
        tool_calls: List[Dict[str, Any]],
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        agent_call_id: Optional[str] = None,
        parallel: bool = True,
    ) -> List[ToolResult]:
        """批量执行工具

        Args:
            tool_calls: 工具调用列表，每项包含 {tool_name, params}
            user_id: 用户ID
            project_id: 项目ID
            agent_call_id: Agent调用ID
            parallel: 是否并行执行

        Returns:
            工具执行结果列表
        """
        if not self._initialized:
            await self.initialize()

        logger.info(f"Batch executing {len(tool_calls)} tools", parallel=parallel)

        if parallel:
            # 并行执行
            tasks = [
                self.execute_tool(
                    tool_name=call["tool_name"],
                    params=call.get("params", {}),
                    user_id=user_id,
                    project_id=project_id,
                    agent_call_id=agent_call_id,
                )
                for call in tool_calls
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理异常
            return [
                r if isinstance(r, ToolResult) else ToolResult(success=False, error=str(r))
                for r in results
            ]

        # 顺序执行
        results = []
        for call in tool_calls:
            result = await self.execute_tool(
                tool_name=call["tool_name"],
                params=call.get("params", {}),
                user_id=user_id,
                project_id=project_id,
                agent_call_id=agent_call_id,
            )
            results.append(result)
        return results

    async def _check_permission(
        self,
        tool_name: str,  # pylint: disable=unused-argument
        user_id: Optional[str],  # pylint: disable=unused-argument
        project_id: Optional[str],  # pylint: disable=unused-argument
    ) -> bool:
        """检查工具执行权限

        Args:
            tool_name: 工具名称
            user_id: 用户ID
            project_id: 项目ID

        Returns:
            是否有权限
        """
        # TODO: 实现实际的权限检查逻辑
        # 可以调用Go后端的权限API
        return True

    def _make_cache_key(
        self,
        tool_name: str,
        params: Dict[str, Any],
        user_id: Optional[str],
        project_id: Optional[str],
    ) -> str:
        """生成缓存键

        Args:
            tool_name: 工具名称
            params: 参数
            user_id: 用户ID
            project_id: 项目ID

        Returns:
            缓存键
        """
        params_str = json.dumps(params, sort_keys=True)
        return f"{tool_name}:{user_id}:{project_id}:{params_str}"

    def _update_stats(self, tool_name: str, result: ToolResult) -> None:
        """更新执行统计

        Args:
            tool_name: 工具名称
            result: 执行结果
        """
        stats = self._execution_stats[tool_name]
        stats["total"] += 1
        if result.success:
            stats["success"] += 1
        else:
            stats["failure"] += 1
        stats["total_duration_ms"] += result.duration_ms or 0

    def get_stats(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """获取执行统计

        Args:
            tool_name: 工具名称（可选，None表示所有工具）

        Returns:
            统计信息
        """
        if tool_name:
            return dict(self._execution_stats.get(tool_name, {}))

        return {
            name: dict(stats)
            for name, stats in self._execution_stats.items()
        }

    def enable_cache(self, enabled: bool = True) -> None:
        """启用/禁用缓存

        Args:
            enabled: 是否启用
        """
        self._cache_enabled = enabled
        if not enabled:
            self._cache.clear()
        logger.info(f"Tool cache {'enabled' if enabled else 'disabled'}")

    def clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()
        logger.info("Tool cache cleared")

    async def health_check(self) -> Dict[str, Any]:
        """健康检查

        Returns:
            健康状态
        """
        tools_list = self.registry.list_tools()
        total_executions = sum(
            stats["total"] for stats in self._execution_stats.values()
        )

        return {
            "healthy": self._initialized,
            "tools_count": len(tools_list),
            "tools": [meta.name for meta in tools_list],
            "stats": {
                "total_executions": total_executions,
                "cache_enabled": self._cache_enabled,
                "cache_size": len(self._cache),
            },
        }

    async def close(self) -> None:
        """关闭服务"""
        if self.go_api_client:
            await self.go_api_client.close()
        self._cache.clear()
        logger.info("ToolService closed")

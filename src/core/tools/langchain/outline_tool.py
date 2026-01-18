"""大纲工具

管理小说大纲树形结构
"""

from typing import Any, Dict, Optional

from pydantic import Field

from src.core.logger import get_logger
from src.core.tools.base import BaseTool, ToolInputSchema, ToolMetadata, ToolResult
from src.infrastructure.go_api import GoAPIClient

logger = get_logger(__name__)


class OutlineToolInput(ToolInputSchema):
    """大纲工具输入"""

    action: str = Field(
        ...,
        description="操作类型",
        pattern="^(create_node|update_node|get_node|list_children|move_node|delete_node)$",
    )
    project_id: str = Field(..., description="项目ID")
    node_id: Optional[str] = Field(None, description="节点ID")
    parent_id: Optional[str] = Field(None, description="父节点ID")

    # 节点数据
    name: Optional[str] = Field(None, description="节点名称")
    description: Optional[str] = Field(None, description="节点描述")
    order: Optional[int] = Field(None, description="排序顺序", ge=0)
    metadata: Optional[Dict[str, Any]] = Field(None, description="节点元数据")


class OutlineTool(BaseTool):
    """大纲工具

    管理小说大纲树形结构，支持：
    - 节点CRUD操作
    - 树形层级管理
    - 节点移动和排序
    """

    def __init__(self, go_api_client: GoAPIClient = None, auth_context: dict = None):
        """初始化

        Args:
            go_api_client: Go API客户端
            auth_context: 认证上下文
        """
        metadata = ToolMetadata(
            name="outline_tool",
            description="管理小说大纲树形结构，支持创建、更新、移动、删除节点",
            category="writing",
            requires_auth=True,
            requires_project=True,
            timeout_seconds=30,
        )
        super().__init__(metadata, auth_context)
        self.go_api_client = go_api_client or GoAPIClient()

    @property
    def input_schema(self):
        return OutlineToolInput

    async def _execute_impl(self, validated_input: OutlineToolInput) -> ToolResult:
        """执行大纲操作

        Args:
            validated_input: 已验证的输入

        Returns:
            操作结果
        """
        action = validated_input.action
        project_id = validated_input.project_id

        try:
            # 确保Go API客户端已初始化
            if not self.go_api_client._session:
                await self.go_api_client.initialize()

            # 路由到具体操作
            if action == "create_node":
                return await self._create_node(validated_input, project_id)
            elif action == "update_node":
                return await self._update_node(validated_input, project_id)
            elif action == "get_node":
                return await self._get_node(validated_input, project_id)
            elif action == "list_children":
                return await self._list_children(validated_input, project_id)
            elif action == "move_node":
                return await self._move_node(validated_input, project_id)
            elif action == "delete_node":
                return await self._delete_node(validated_input, project_id)
            else:
                return ToolResult(success=False, error=f"Unknown action: {action}")

        except Exception as e:
            self.logger.error(f"Outline tool execution failed: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))

    async def _create_node(
        self, input_data: OutlineToolInput, project_id: str
    ) -> ToolResult:
        """创建大纲节点"""
        node_data = {
            "projectId": project_id,
            "parentId": input_data.parent_id or "",
            "name": input_data.name,
            "type": "outline",
            "description": input_data.description or "",
            "order": input_data.order or 0,
            "metadata": input_data.metadata or {},
        }

        response = await self.go_api_client.call_api(
            method="POST",
            endpoint=f"/api/v1/projects/{project_id}/nodes",
            data=node_data,
            user_id=self.auth_context.get("user_id"),
            agent_call_id=self.auth_context.get("agent_call_id"),
        )

        return ToolResult(
            success=True,
            data=response.get("data"),
            metadata={
                "action": "create_node",
                "node_id": response.get("data", {}).get("id"),
            },
        )

    async def _update_node(
        self, input_data: OutlineToolInput, project_id: str
    ) -> ToolResult:
        """更新大纲节点"""
        if not input_data.node_id:
            return ToolResult(success=False, error="node_id is required for update")

        # 构建更新数据
        update_data = {}
        if input_data.name is not None:
            update_data["name"] = input_data.name
        if input_data.description is not None:
            update_data["description"] = input_data.description
        if input_data.order is not None:
            update_data["order"] = input_data.order
        if input_data.metadata is not None:
            update_data["metadata"] = input_data.metadata

        response = await self.go_api_client.call_api(
            method="PUT",
            endpoint=f"/api/v1/projects/{project_id}/nodes/{input_data.node_id}",
            data=update_data,
            user_id=self.auth_context.get("user_id"),
            agent_call_id=self.auth_context.get("agent_call_id"),
        )

        return ToolResult(
            success=True,
            data=response.get("data"),
            metadata={"action": "update_node", "node_id": input_data.node_id},
        )

    async def _get_node(
        self, input_data: OutlineToolInput, project_id: str
    ) -> ToolResult:
        """获取节点详情"""
        if not input_data.node_id:
            return ToolResult(success=False, error="node_id is required for get")

        response = await self.go_api_client.call_api(
            method="GET",
            endpoint=f"/api/v1/projects/{project_id}/nodes/{input_data.node_id}",
            user_id=self.auth_context.get("user_id"),
            agent_call_id=self.auth_context.get("agent_call_id"),
        )

        return ToolResult(
            success=True,
            data=response.get("data"),
            metadata={"action": "get_node", "node_id": input_data.node_id},
        )

    async def _list_children(
        self, input_data: OutlineToolInput, project_id: str
    ) -> ToolResult:
        """列出子节点"""
        params = {"type": "outline"}
        if input_data.parent_id:
            params["parentId"] = input_data.parent_id

        response = await self.go_api_client.call_api(
            method="GET",
            endpoint=f"/api/v1/projects/{project_id}/nodes",
            params=params,
            user_id=self.auth_context.get("user_id"),
            agent_call_id=self.auth_context.get("agent_call_id"),
        )

        nodes = response.get("data", {}).get("items", [])

        return ToolResult(
            success=True,
            data=nodes,
            metadata={"action": "list_children", "count": len(nodes)},
        )

    async def _move_node(
        self, input_data: OutlineToolInput, project_id: str
    ) -> ToolResult:
        """移动节点"""
        if not input_data.node_id:
            return ToolResult(success=False, error="node_id is required for move")

        move_data = {
            "parentId": input_data.parent_id or "",
            "order": input_data.order or 0,
        }

        response = await self.go_api_client.call_api(
            method="POST",
            endpoint=f"/api/v1/projects/{project_id}/nodes/{input_data.node_id}/move",
            data=move_data,
            user_id=self.auth_context.get("user_id"),
            agent_call_id=self.auth_context.get("agent_call_id"),
        )

        return ToolResult(
            success=True,
            data=response.get("data"),
            metadata={"action": "move_node", "node_id": input_data.node_id},
        )

    async def _delete_node(
        self, input_data: OutlineToolInput, project_id: str
    ) -> ToolResult:
        """删除节点"""
        if not input_data.node_id:
            return ToolResult(success=False, error="node_id is required for delete")

        await self.go_api_client.call_api(
            method="DELETE",
            endpoint=f"/api/v1/projects/{project_id}/nodes/{input_data.node_id}",
            user_id=self.auth_context.get("user_id"),
            agent_call_id=self.auth_context.get("agent_call_id"),
        )

        return ToolResult(
            success=True,
            data={"deleted": True},
            metadata={"action": "delete_node", "node_id": input_data.node_id},
        )


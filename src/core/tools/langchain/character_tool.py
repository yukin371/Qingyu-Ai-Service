"""角色卡工具

管理小说角色卡片，包括CRUD和关系管理
"""

from typing import List, Optional

from pydantic import Field

from src.core.logger import get_logger
from src.core.tools.base import BaseTool, ToolInputSchema, ToolMetadata, ToolResult
from src.infrastructure.go_api import GoAPIClient

logger = get_logger(__name__)


class CharacterToolInput(ToolInputSchema):
    """角色卡工具输入"""

    action: str = Field(
        ...,
        description="操作类型",
        pattern="^(create|update|get|list|delete|create_relation|list_relations|get_graph)$",
    )
    project_id: str = Field(..., description="项目ID")
    character_id: Optional[str] = Field(None, description="角色ID（update/get/delete时需要）")

    # 角色数据（create/update时使用）
    name: Optional[str] = Field(None, description="角色名称")
    alias: Optional[List[str]] = Field(None, description="别名列表")
    summary: Optional[str] = Field(None, description="角色简介")
    traits: Optional[List[str]] = Field(None, description="性格标签")
    background: Optional[str] = Field(None, description="背景故事")
    personality_prompt: Optional[str] = Field(None, description="性格提示词")
    speech_pattern: Optional[str] = Field(None, description="说话方式")

    # 关系数据（create_relation时使用）
    from_id: Optional[str] = Field(None, description="关系起始角色ID")
    to_id: Optional[str] = Field(None, description="关系目标角色ID")
    relation_type: Optional[str] = Field(None, description="关系类型")
    strength: Optional[int] = Field(None, description="关系强度0-100", ge=0, le=100)
    notes: Optional[str] = Field(None, description="关系备注")


class CharacterTool(BaseTool):
    """角色卡工具

    管理小说角色卡片，支持：
    - CRUD操作
    - 角色关系管理
    - 角色关系图查询
    """

    def __init__(self, go_api_client: GoAPIClient = None, auth_context: dict = None):
        """初始化

        Args:
            go_api_client: Go API客户端
            auth_context: 认证上下文
        """
        metadata = ToolMetadata(
            name="character_tool",
            description="管理小说角色卡片，支持创建、更新、查询、列表、删除和关系管理操作",
            category="writing",
            requires_auth=True,
            requires_project=True,
            timeout_seconds=30,
        )
        super().__init__(metadata, auth_context)
        self.go_api_client = go_api_client or GoAPIClient()

    @property
    def input_schema(self):
        return CharacterToolInput

    async def _execute_impl(self, validated_input: CharacterToolInput) -> ToolResult:
        """执行角色卡操作

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
            if action == "create":
                return await self._create_character(validated_input, project_id)
            elif action == "update":
                return await self._update_character(validated_input, project_id)
            elif action == "get":
                return await self._get_character(validated_input, project_id)
            elif action == "list":
                return await self._list_characters(project_id)
            elif action == "delete":
                return await self._delete_character(validated_input, project_id)
            elif action == "create_relation":
                return await self._create_relation(validated_input, project_id)
            elif action == "list_relations":
                return await self._list_relations(project_id)
            elif action == "get_graph":
                return await self._get_graph(project_id)
            else:
                return ToolResult(success=False, error=f"Unknown action: {action}")

        except Exception as e:
            self.logger.error(f"Character tool execution failed: {e}", exc_info=True)
            return ToolResult(success=False, error=str(e))

    async def _create_character(
        self, input_data: CharacterToolInput, project_id: str
    ) -> ToolResult:
        """创建角色卡"""
        character_data = {
            "name": input_data.name,
            "alias": input_data.alias or [],
            "summary": input_data.summary or "",
            "traits": input_data.traits or [],
            "background": input_data.background or "",
            "personalityPrompt": input_data.personality_prompt or "",
            "speechPattern": input_data.speech_pattern or "",
        }

        response = await self.go_api_client.call_api(
            method="POST",
            endpoint=f"/api/v1/projects/{project_id}/characters",
            data=character_data,
            user_id=self.auth_context.get("user_id"),
            agent_call_id=self.auth_context.get("agent_call_id"),
        )

        return ToolResult(
            success=True,
            data=response.get("data"),
            metadata={
                "action": "create",
                "character_id": response.get("data", {}).get("id"),
            },
        )

    async def _update_character(
        self, input_data: CharacterToolInput, project_id: str
    ) -> ToolResult:
        """更新角色卡"""
        if not input_data.character_id:
            return ToolResult(success=False, error="character_id is required for update")

        # 构建更新数据（只包含非None的字段）
        update_data = {}
        if input_data.name is not None:
            update_data["name"] = input_data.name
        if input_data.alias is not None:
            update_data["alias"] = input_data.alias
        if input_data.summary is not None:
            update_data["summary"] = input_data.summary
        if input_data.traits is not None:
            update_data["traits"] = input_data.traits
        if input_data.background is not None:
            update_data["background"] = input_data.background
        if input_data.personality_prompt is not None:
            update_data["personalityPrompt"] = input_data.personality_prompt
        if input_data.speech_pattern is not None:
            update_data["speechPattern"] = input_data.speech_pattern

        response = await self.go_api_client.call_api(
            method="PUT",
            endpoint=f"/api/v1/characters/{input_data.character_id}",
            data=update_data,
            user_id=self.auth_context.get("user_id"),
            agent_call_id=self.auth_context.get("agent_call_id"),
        )

        return ToolResult(
            success=True,
            data=response.get("data"),
            metadata={"action": "update", "character_id": input_data.character_id},
        )

    async def _get_character(
        self, input_data: CharacterToolInput, project_id: str
    ) -> ToolResult:
        """获取角色卡"""
        if not input_data.character_id:
            return ToolResult(success=False, error="character_id is required for get")

        response = await self.go_api_client.call_api(
            method="GET",
            endpoint=f"/api/v1/characters/{input_data.character_id}",
            user_id=self.auth_context.get("user_id"),
            agent_call_id=self.auth_context.get("agent_call_id"),
        )

        return ToolResult(
            success=True,
            data=response.get("data"),
            metadata={"action": "get", "character_id": input_data.character_id},
        )

    async def _list_characters(self, project_id: str) -> ToolResult:
        """列出所有角色卡"""
        response = await self.go_api_client.call_api(
            method="GET",
            endpoint=f"/api/v1/projects/{project_id}/characters",
            user_id=self.auth_context.get("user_id"),
            agent_call_id=self.auth_context.get("agent_call_id"),
        )

        characters = response.get("data", {}).get("items", [])

        return ToolResult(
            success=True,
            data=characters,
            metadata={"action": "list", "count": len(characters)},
        )

    async def _delete_character(
        self, input_data: CharacterToolInput, project_id: str
    ) -> ToolResult:
        """删除角色卡"""
        if not input_data.character_id:
            return ToolResult(success=False, error="character_id is required for delete")

        await self.go_api_client.call_api(
            method="DELETE",
            endpoint=f"/api/v1/characters/{input_data.character_id}",
            user_id=self.auth_context.get("user_id"),
            agent_call_id=self.auth_context.get("agent_call_id"),
        )

        return ToolResult(
            success=True,
            data={"deleted": True},
            metadata={"action": "delete", "character_id": input_data.character_id},
        )

    async def _create_relation(
        self, input_data: CharacterToolInput, project_id: str
    ) -> ToolResult:
        """创建角色关系"""
        if not input_data.from_id or not input_data.to_id:
            return ToolResult(
                success=False, error="from_id and to_id are required for create_relation"
            )

        relation_data = {
            "projectId": project_id,
            "fromId": input_data.from_id,
            "toId": input_data.to_id,
            "type": input_data.relation_type or "其他",
            "strength": input_data.strength or 50,
            "notes": input_data.notes or "",
        }

        response = await self.go_api_client.call_api(
            method="POST",
            endpoint="/api/v1/characters/relations",
            data=relation_data,
            user_id=self.auth_context.get("user_id"),
            agent_call_id=self.auth_context.get("agent_call_id"),
        )

        return ToolResult(
            success=True,
            data=response.get("data"),
            metadata={"action": "create_relation"},
        )

    async def _list_relations(self, project_id: str) -> ToolResult:
        """列出角色关系"""
        response = await self.go_api_client.call_api(
            method="GET",
            endpoint=f"/api/v1/projects/{project_id}/characters",
            user_id=self.auth_context.get("user_id"),
            agent_call_id=self.auth_context.get("agent_call_id"),
        )

        # TODO: 实际API可能需要单独的关系列表端点
        return ToolResult(
            success=True,
            data=response.get("data", {}).get("relations", []),
            metadata={"action": "list_relations"},
        )

    async def _get_graph(self, project_id: str) -> ToolResult:
        """获取角色关系图"""
        response = await self.go_api_client.call_api(
            method="GET",
            endpoint=f"/api/v1/projects/{project_id}/characters/graph",
            user_id=self.auth_context.get("user_id"),
            agent_call_id=self.auth_context.get("agent_call_id"),
        )

        return ToolResult(
            success=True,
            data=response.get("data"),
            metadata={"action": "get_graph"},
        )


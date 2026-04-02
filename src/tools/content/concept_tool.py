"""概念工具"""
from typing import Optional, List
from langchain_core.tools import tool
from structlog import get_logger

from src.api.go_backend import GoBackendClient
from src.api.go_backend.concepts import Concept, ConceptListResponse, ConceptOperations, ConceptCategory
from src.api.go_backend.exceptions import ConceptNotFoundError

logger = get_logger(__name__)


class ConceptTool:
    """
    设定概念管理工具

    用于AI助手管理世界观设定、角色、地点等概念。
    """

    def __init__(self, go_client: GoBackendClient):
        self.client = go_client
        self.concept_ops = ConceptOperations(go_client)
        self.logger = logger.bind(component="concept_tool")

    async def get_concept(
        self,
        user_id: str,
        project_id: str,
        concept_id: str
    ) -> Concept:
        """
        获取概念详情

        Args:
            user_id: 用户ID
            project_id: 项目ID
            concept_id: 概念ID

        Returns:
            Concept对象

        Raises:
            ConceptNotFoundError: 概念不存在
        """
        return await self.concept_ops.get_concept(user_id, project_id, concept_id)

    async def create_concept(
        self,
        user_id: str,
        project_id: str,
        name: str,
        category: ConceptCategory,
        content: str,
        tags: Optional[List[str]] = None
    ) -> Concept:
        """
        创建新概念

        Args:
            user_id: 用户ID
            project_id: 项目ID
            name: 概念名称
            category: 分类
            content: 详细描述
            tags: 标签列表

        Returns:
            创建的Concept对象
        """
        return await self.concept_ops.create_concept(
            user_id=user_id,
            project_id=project_id,
            name=name,
            category=category,
            content=content,
            tags=tags or []
        )

    async def update_concept(
        self,
        user_id: str,
        project_id: str,
        concept_id: str,
        name: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Concept:
        """
        更新概念

        Args:
            user_id: 用户ID
            project_id: 项目ID
            concept_id: 概念ID
            name: 新名称（可选）
            content: 新内容（可选）
            tags: 新标签（可选）

        Returns:
            更新后的Concept对象
        """
        return await self.concept_ops.update_concept(
            user_id=user_id,
            project_id=project_id,
            concept_id=concept_id,
            name=name,
            content=content,
            tags=tags
        )

    async def delete_concept(
        self,
        user_id: str,
        project_id: str,
        concept_id: str
    ) -> bool:
        """
        删除概念

        Args:
            user_id: 用户ID
            project_id: 项目ID
            concept_id: 概念ID

        Returns:
            是否删除成功
        """
        return await self.concept_ops.delete_concept(
            user_id=user_id,
            project_id=project_id,
            concept_id=concept_id
        )

    async def search_concepts(
        self,
        user_id: str,
        project_id: str,
        category: Optional[ConceptCategory] = None,
        keyword: Optional[str] = None,
        limit: int = 20
    ) -> List[Concept]:
        """
        搜索概念

        Args:
            user_id: 用户ID
            project_id: 项目ID
            category: 分类筛选
            keyword: 关键词搜索
            limit: 返回数量限制

        Returns:
            概念列表
        """
        result = await self.concept_ops.search_concepts(
            user_id=user_id,
            project_id=project_id,
            category=category,
            keyword=keyword,
            limit=limit
        )
        return result.concepts

    async def list_concepts(
        self,
        user_id: str,
        project_id: str,
        category: Optional[ConceptCategory] = None
    ) -> List[Concept]:
        """
        获取概念列表

        Args:
            user_id: 用户ID
            project_id: 项目ID
            category: 分类筛选

        Returns:
            概念列表
        """
        result = await self.concept_ops.search_concepts(
            user_id=user_id,
            project_id=project_id,
            category=category,
            limit=1000
        )
        return result.concepts

    def get_langchain_tools(self) -> List:
        """
        获取LangChain工具列表

        Returns:
            LangChain工具列表
        """
        # 使用tool装饰器创建工具
        get_concept_tool = tool(self.get_concept_info)
        get_concept_tool.name = "get_concept"
        get_concept_tool.description = "获取设定概念详情。输入：user_id, project_id, concept_id"

        create_concept_tool = tool(self.create_new_concept)
        create_concept_tool.name = "create_concept"
        create_concept_tool.description = "创建新的设定概念。输入：user_id, project_id, name, category, content, tags"

        search_concepts_tool = tool(self.search_project_concepts)
        search_concepts_tool.name = "search_concepts"
        search_concepts_tool.description = "搜索项目中的设定概念。输入：user_id, project_id, category（可选）, keyword（可选）"

        return [get_concept_tool, create_concept_tool, search_concepts_tool]

    async def get_concept_info(
        self,
        user_id: str,
        project_id: str,
        concept_id: str
    ) -> str:
        """
        获取概念信息（LangChain调用）

        用于LangChain Agent调用。
        """
        concept = await self.get_concept(user_id, project_id, concept_id)
        return f"# {concept.name} ({concept.category})\n\n{concept.content}\n\n标签: {', '.join(concept.tags)}"

    async def create_new_concept(
        self,
        user_id: str,
        project_id: str,
        name: str,
        category: ConceptCategory,
        content: str,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        创建新概念（LangChain调用）

        用于LangChain Agent调用。
        """
        concept = await self.create_concept(
            user_id=user_id,
            project_id=project_id,
            name=name,
            category=category,
            content=content,
            tags=tags or []
        )
        return f"已创建设定：{concept.name} (分类: {concept.category}, ID: {concept.id})"

    async def search_project_concepts(
        self,
        user_id: str,
        project_id: str,
        category: Optional[ConceptCategory] = None,
        keyword: Optional[str] = None
    ) -> str:
        """
        搜索概念（LangChain调用）

        用于LangChain Agent调用。
        """
        concepts = await self.search_concepts(
            user_id=user_id,
            project_id=project_id,
            category=category,
            keyword=keyword
        )
        if not concepts:
            return "未找到匹配的概念"
        return "\n\n".join([
            f"- {c.name} ({c.category}): {c.content[:100]}..."
            for c in concepts
        ])

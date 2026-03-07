"""概念操作封装"""
from typing import List, Optional, Literal
from pydantic import BaseModel
from datetime import datetime

from .client import GoBackendClient
from .exceptions import ConceptNotFoundError

# 概念分类类型别名
ConceptCategory = Literal["magic", "location", "character", "item", "organization", "event", "other"]


class Concept(BaseModel):
    """概念模型"""
    id: str
    project_id: str
    name: str
    category: ConceptCategory
    content: str
    tags: List[str] = []
    related_docs: List[str] = []
    created_at: datetime
    updated_at: datetime


class ConceptListResponse(BaseModel):
    """概念列表响应"""
    concepts: List[Concept]
    total: int


class ConceptOperations:
    """概念操作封装"""

    def __init__(self, client: GoBackendClient):
        self.client = client

    async def get_concept(
        self,
        user_id: str,
        project_id: str,
        concept_id: str
    ) -> Concept:
        """
        获取概念

        Args:
            user_id: 用户ID
            project_id: 项目ID
            concept_id: 概念ID

        Returns:
            Concept对象

        Raises:
            ConceptNotFoundError: 概念不存在
        """
        data = await self.client._request(
            "GET",
            f"/concepts/{concept_id}",
            params={"user_id": user_id, "project_id": project_id}
        )
        return Concept(**data)

    async def create_concept(
        self,
        user_id: str,
        project_id: str,
        name: str,
        category: ConceptCategory,
        content: str,
        tags: Optional[List[str]] = None,
        related_docs: Optional[List[str]] = None
    ) -> Concept:
        """
        创建概念

        Args:
            user_id: 用户ID
            project_id: 项目ID
            name: 概念名称
            category: 概念分类
            content: 概念内容
            tags: 标签列表
            related_docs: 关联文档ID列表

        Returns:
            创建的Concept对象
        """
        data = await self.client._request(
            "POST",
            "/concepts",
            json_data={
                "user_id": user_id,
                "project_id": project_id,
                "name": name,
                "category": category,
                "content": content,
                "tags": tags or [],
                "related_docs": related_docs or []
            }
        )
        return Concept(**data)

    async def update_concept(
        self,
        user_id: str,
        project_id: str,
        concept_id: str,
        name: Optional[str] = None,
        category: Optional[ConceptCategory] = None,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        related_docs: Optional[List[str]] = None
    ) -> Concept:
        """
        更新概念

        Args:
            user_id: 用户ID
            project_id: 项目ID
            concept_id: 概念ID
            name: 新名称（可选）
            category: 新分类（可选）
            content: 新内容（可选）
            tags: 新标签（可选）
            related_docs: 新关联文档（可选）

        Returns:
            更新后的Concept对象
        """
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if category is not None:
            update_data["category"] = category
        if content is not None:
            update_data["content"] = content
        if tags is not None:
            update_data["tags"] = tags
        if related_docs is not None:
            update_data["related_docs"] = related_docs

        data = await self.client._request(
            "PUT",
            f"/concepts/{concept_id}",
            params={"user_id": user_id, "project_id": project_id},
            json_data=update_data
        )
        return Concept(**data)

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
        await self.client._request(
            "DELETE",
            f"/concepts/{concept_id}",
            params={"user_id": user_id, "project_id": project_id}
        )
        return True

    async def search_concepts(
        self,
        user_id: str,
        project_id: str,
        category: Optional[ConceptCategory] = None,
        keyword: Optional[str] = None,
        limit: int = 50
    ) -> ConceptListResponse:
        """
        搜索概念

        Args:
            user_id: 用户ID
            project_id: 项目ID
            category: 按分类筛选（可选）
            keyword: 关键词搜索（可选）
            limit: 返回数量限制

        Returns:
            概念列表
        """
        params = {"user_id": user_id, "project_id": project_id, "limit": limit}
        if category:
            params["category"] = category
        if keyword:
            params["keyword"] = keyword

        data = await self.client._request(
            "GET",
            "/concepts",
            params=params
        )
        return ConceptListResponse(**data)

    async def batch_get_concepts(
        self,
        user_id: str,
        project_id: str,
        concept_ids: List[str]
    ) -> List[Concept]:
        """
        批量获取概念

        Args:
            user_id: 用户ID
            project_id: 项目ID
            concept_ids: 概念ID列表

        Returns:
            概念列表
        """
        data = await self.client._request(
            "POST",
            "/concepts/batch",
            json_data={
                "user_id": user_id,
                "project_id": project_id,
                "concept_ids": concept_ids
            }
        )
        return [Concept(**c) for c in data.get("concepts", [])]

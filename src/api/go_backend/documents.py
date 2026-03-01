"""文档操作封装"""
from typing import List, Optional, Literal
from pydantic import BaseModel
from datetime import datetime

from .client import GoBackendClient
from .exceptions import DocumentNotFoundError


class Document(BaseModel):
    """文档模型"""
    id: str
    project_id: str
    chapter_num: int
    title: str
    content: str
    format: Literal["markdown", "html", "text"] = "markdown"
    word_count: int
    version: int
    status: Literal["draft", "reviewing", "completed"] = "draft"
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    documents: List[Document]
    total: int


class DocumentOperations:
    """文档操作封装"""

    def __init__(self, client: GoBackendClient):
        self.client = client

    async def get_document(
        self,
        user_id: str,
        project_id: str,
        document_id: str
    ) -> Document:
        """
        获取文档

        Args:
            user_id: 用户ID
            project_id: 项目ID
            document_id: 文档ID

        Returns:
            Document对象

        Raises:
            DocumentNotFoundError: 文档不存在
        """
        data = await self.client._request(
            "GET",
            f"/documents/{document_id}",
            params={"user_id": user_id, "project_id": project_id}
        )
        return Document(**data)

    async def create_or_update_document(
        self,
        user_id: str,
        project_id: str,
        chapter_num: int,
        title: str,
        content: str,
        format: Literal["markdown", "html", "text"] = "markdown",
        action: Literal["create", "update", "create_or_update", "append"] = "create_or_update"
    ) -> Document:
        """
        创建或更新文档

        Args:
            user_id: 用户ID
            project_id: 项目ID
            chapter_num: 章节序号
            title: 章节标题
            content: 章节内容
            format: 内容格式
            action: 操作类型 (create/update/create_or_update/append)

        Returns:
            创建/更新后的Document对象
        """
        data = await self.client._request(
            "POST",
            "/documents",
            json_data={
                "user_id": user_id,
                "project_id": project_id,
                "action": action,
                "document": {
                    "chapter_num": chapter_num,
                    "title": title,
                    "content": content,
                    "format": format
                }
            }
        )
        return Document(**data)

    async def list_documents(
        self,
        user_id: str,
        project_id: str,
        limit: int = 50
    ) -> DocumentListResponse:
        """
        获取文档列表

        Args:
            user_id: 用户ID
            project_id: 项目ID
            limit: 返回数量限制

        Returns:
            文档列表
        """
        data = await self.client._request(
            "GET",
            "/documents",
            params={"user_id": user_id, "project_id": project_id, "limit": limit}
        )
        return DocumentListResponse(**data)

    async def delete_document(
        self,
        user_id: str,
        project_id: str,
        document_id: str
    ) -> bool:
        """
        删除文档

        Args:
            user_id: 用户ID
            project_id: 项目ID
            document_id: 文档ID

        Returns:
            是否删除成功
        """
        await self.client._request(
            "DELETE",
            f"/documents/{document_id}",
            params={"user_id": user_id, "project_id": project_id}
        )
        return True

    async def batch_get_documents(
        self,
        user_id: str,
        project_id: str,
        document_ids: List[str]
    ) -> List[Document]:
        """
        批量获取文档

        Args:
            user_id: 用户ID
            project_id: 项目ID
            document_ids: 文档ID列表

        Returns:
            文档列表
        """
        data = await self.client._request(
            "POST",
            "/documents/batch",
            json_data={
                "user_id": user_id,
                "project_id": project_id,
                "document_ids": document_ids
            }
        )
        return [Document(**d) for d in data.get("documents", [])]

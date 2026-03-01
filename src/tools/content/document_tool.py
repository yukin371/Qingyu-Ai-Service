"""文档工具"""
from typing import Optional, List
from langchain_core.tools import tool
from structlog import get_logger

from src.api.go_backend import GoBackendClient
from src.api.go_backend.documents import Document, DocumentListResponse, DocumentOperations
from src.api.go_backend.exceptions import DocumentNotFoundError

logger = get_logger(__name__)


class DocumentTool:
    """
    文档（写作草稿）管理工具

    用于AI助手在写作过程中操作用户的文档草稿。
    """

    def __init__(self, go_client: GoBackendClient):
        self.client = go_client
        self.doc_ops = DocumentOperations(go_client)
        self.logger = logger.bind(component="document_tool")

    async def get_document(
        self,
        user_id: str,
        project_id: str,
        document_id: str
    ) -> Document:
        """
        获取文档详情

        Args:
            user_id: 用户ID
            project_id: 项目ID
            document_id: 文档ID

        Returns:
            Document对象

        Raises:
            DocumentNotFoundError: 文档不存在
        """
        return await self.doc_ops.get_document(user_id, project_id, document_id)

    async def create_or_update_document(
        self,
        user_id: str,
        project_id: str,
        chapter_num: int,
        title: str,
        content: str,
        format: str = "markdown",
        action: str = "create_or_update"
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
            action: 操作类型

        Returns:
            创建/更新后的Document对象
        """
        return await self.doc_ops.create_or_update_document(
            user_id=user_id,
            project_id=project_id,
            chapter_num=chapter_num,
            title=title,
            content=content,
            format=format,
            action=action
        )

    async def list_documents(
        self,
        user_id: str,
        project_id: str,
        limit: int = 50
    ) -> List[Document]:
        """
        获取项目文档列表

        Args:
            user_id: 用户ID
            project_id: 项目ID
            limit: 返回数量限制

        Returns:
            文档列表
        """
        result = await self.doc_ops.list_documents(
            user_id=user_id,
            project_id=project_id,
            limit=limit
        )
        return result.documents

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
        return await self.doc_ops.delete_document(
            user_id=user_id,
            project_id=project_id,
            document_id=document_id
        )

    def get_langchain_tools(self) -> List:
        """
        获取LangChain工具列表

        Returns:
            LangChain工具列表
        """
        # 使用tool装饰器创建工具
        get_doc_tool = tool(self.get_document_for_context)
        get_doc_tool.name = "get_document_context"
        get_doc_tool.description = "获取文档内容作为上下文，用于续写或参考。输入：user_id, project_id, document_id"

        create_chapter_tool = tool(self.create_chapter)
        create_chapter_tool.name = "create_chapter"
        create_chapter_tool.description = "创建新章节。输入：project_id, user_id, chapter_num, title, content"

        update_chapter_tool = tool(self.update_chapter)
        update_chapter_tool.name = "update_chapter"
        update_chapter_tool.description = "更新章节内容。输入：document_id, project_id, user_id, content, title（可选）"

        return [get_doc_tool, create_chapter_tool, update_chapter_tool]

    async def get_document_for_context(
        self,
        user_id: str,
        project_id: str,
        document_id: str
    ) -> str:
        """
        获取文档作为上下文（LangChain调用）

        用于LangChain Agent调用。
        """
        doc = await self.get_document(user_id, project_id, document_id)
        return f"# {doc.title}\n\n{doc.content}"

    async def create_chapter(
        self,
        project_id: str,
        user_id: str,
        chapter_num: int,
        title: str,
        content: str
    ) -> str:
        """
        创建新章节（LangChain调用）

        用于LangChain Agent调用。
        返回创建结果的描述。
        """
        doc = await self.create_or_update_document(
            user_id=user_id,
            project_id=project_id,
            chapter_num=chapter_num,
            title=title,
            content=content,
            action="create"
        )
        return f"已创建章节：{doc.title} (ID: {doc.id})"

    async def update_chapter(
        self,
        document_id: str,
        project_id: str,
        user_id: str,
        content: str,
        title: Optional[str] = None
    ) -> str:
        """
        更新章节内容（LangChain调用）

        用于LangChain Agent调用。
        """
        # 先获取文档以确定章节序号
        doc = await self.get_document(user_id, project_id, document_id)
        chapter_num = doc.chapter_num

        doc = await self.create_or_update_document(
            user_id=user_id,
            project_id=project_id,
            chapter_num=chapter_num,
            title=title or doc.title,
            content=content,
            action="update"
        )
        return f"已更新章节：{doc.title}"

        doc = await self.create_or_update_document(
            user_id=user_id,
            project_id=project_id,
            chapter_num=chapter_num,
            title=title or doc.title,
            content=content,
            action="update"
        )
        return f"已更新章节：{doc.title}"

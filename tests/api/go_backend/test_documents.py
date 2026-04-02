"""Document操作测试"""
import pytest
from src.api.go_backend.documents import DocumentOperations
from src.api.go_backend.exceptions import DocumentNotFoundError


@pytest.mark.asyncio
async def test_get_document(mock_go_client):
    """测试获取文档"""
    ops = DocumentOperations(mock_go_client)
    doc = await ops.get_document("user-1", "project-1", "doc-1")
    assert doc.id == "507f1f77bcf86cd799439011"
    assert doc.title == "Test Chapter"
    assert doc.content == "Test content"
    assert doc.chapter_num == 1
    assert doc.format == "markdown"


@pytest.mark.asyncio
async def test_create_or_update_document(mock_go_client):
    """测试创建或更新文档"""
    ops = DocumentOperations(mock_go_client)
    doc = await ops.create_or_update_document(
        user_id="user-1",
        project_id="project-1",
        chapter_num=1,
        title="New Chapter",
        content="New content",
        action="create"
    )
    assert doc.title == "New Chapter"
    assert doc.content == "New content"
    assert doc.chapter_num == 1


@pytest.mark.asyncio
async def test_list_documents(mock_go_client):
    """测试获取文档列表"""
    ops = DocumentOperations(mock_go_client)
    result = await ops.list_documents("user-1", "project-1", limit=10)
    assert len(result.documents) >= 0
    assert result.total >= 0


@pytest.mark.asyncio
async def test_delete_document(mock_go_client):
    """测试删除文档"""
    ops = DocumentOperations(mock_go_client)
    result = await ops.delete_document("user-1", "project-1", "doc-1")
    assert result is True


@pytest.mark.asyncio
async def test_batch_get_documents(mock_go_client):
    """测试批量获取文档"""
    ops = DocumentOperations(mock_go_client)
    docs = await ops.batch_get_documents(
        "user-1",
        "project-1",
        ["doc-1", "doc-2"]
    )
    assert len(docs) >= 0


@pytest.mark.asyncio
async def test_create_or_update_with_different_actions(mock_go_client):
    """测试不同的操作类型"""
    ops = DocumentOperations(mock_go_client)

    # 测试update
    doc = await ops.create_or_update_document(
        user_id="user-1",
        project_id="project-1",
        chapter_num=1,
        title="Updated Chapter",
        content="Updated content",
        action="update"
    )
    assert doc.title == "Updated Chapter"

    # 测试create_or_update
    doc = await ops.create_or_update_document(
        user_id="user-1",
        project_id="project-1",
        chapter_num=1,
        title="Merged Chapter",
        content="Merged content",
        action="create_or_update"
    )
    assert doc.title == "Merged Chapter"

    # 测试append
    doc = await ops.create_or_update_document(
        user_id="user-1",
        project_id="project-1",
        chapter_num=1,
        title="Appended Chapter",
        content="Appended content",
        action="append"
    )
    assert doc.title == "Appended Chapter"


@pytest.mark.asyncio
async def test_create_or_update_with_different_formats(mock_go_client):
    """测试不同的内容格式"""
    ops = DocumentOperations(mock_go_client)

    # 测试html格式
    doc = await ops.create_or_update_document(
        user_id="user-1",
        project_id="project-1",
        chapter_num=1,
        title="HTML Chapter",
        content="<p>HTML content</p>",
        format="html"
    )
    assert doc.format == "html"

    # 测试text格式
    doc = await ops.create_or_update_document(
        user_id="user-1",
        project_id="project-1",
        chapter_num=1,
        title="Text Chapter",
        content="Plain text content",
        format="text"
    )
    assert doc.format == "text"

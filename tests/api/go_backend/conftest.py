"""Go后端API测试配置"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime


@pytest.fixture
def mock_go_client():
    """Mock的Go后端客户端"""
    from src.api.go_backend import GoBackendClient

    # 创建mock client
    client = GoBackendClient()

    # Mock HTTP请求方法
    async def mock_request(method, path, params=None, json_data=None):
        # 根据路径返回模拟数据
        if "documents" in path and method == "GET" and not path.endswith("/documents"):
            # 获取单个文档
            return {
                "id": "507f1f77bcf86cd799439011",
                "project_id": "test-project",
                "chapter_num": 1,
                "title": "Test Chapter",
                "content": "Test content",
                "format": "markdown",
                "word_count": 12,
                "version": 1,
                "status": "draft",
                "tags": [],
                "created_at": "2026-03-01T00:00:00Z",
                "updated_at": "2026-03-01T00:00:00Z"
            }
        elif "documents" in path and method == "POST" and "batch" in path:
            # 批量获取文档
            return {
                "documents": [
                    {
                        "id": "507f1f77bcf86cd799439011",
                        "project_id": "test-project",
                        "chapter_num": 1,
                        "title": "Test Chapter 1",
                        "content": "Test content 1",
                        "format": "markdown",
                        "word_count": 12,
                        "version": 1,
                        "status": "draft",
                        "tags": [],
                        "created_at": "2026-03-01T00:00:00Z",
                        "updated_at": "2026-03-01T00:00:00Z"
                    },
                    {
                        "id": "507f1f77bcf86cd799439012",
                        "project_id": "test-project",
                        "chapter_num": 2,
                        "title": "Test Chapter 2",
                        "content": "Test content 2",
                        "format": "markdown",
                        "word_count": 12,
                        "version": 1,
                        "status": "draft",
                        "tags": [],
                        "created_at": "2026-03-01T00:00:00Z",
                        "updated_at": "2026-03-01T00:00:00Z"
                    }
                ]
            }
        elif "documents" in path and method == "GET":
            # 获取文档列表
            return {
                "documents": [
                    {
                        "id": "507f1f77bcf86cd799439011",
                        "project_id": "test-project",
                        "chapter_num": 1,
                        "title": "Test Chapter",
                        "content": "Test content",
                        "format": "markdown",
                        "word_count": 12,
                        "version": 1,
                        "status": "draft",
                        "tags": [],
                        "created_at": "2026-03-01T00:00:00Z",
                        "updated_at": "2026-03-01T00:00:00Z"
                    }
                ],
                "total": 1
            }
        elif "documents" in path and method == "POST":
            # 创建或更新文档 - 根据传入的json_data返回相应数据
            doc_data = json_data.get("document", {})
            return {
                "id": "507f1f77bcf86cd799439013",
                "project_id": "test-project",
                "chapter_num": doc_data.get("chapter_num", 1),
                "title": doc_data.get("title", "New Chapter"),
                "content": doc_data.get("content", "New content"),
                "format": doc_data.get("format", "markdown"),
                "word_count": len(doc_data.get("content", "New content").split()),
                "version": 1,
                "status": "draft",
                "tags": [],
                "created_at": "2026-03-01T00:00:00Z",
                "updated_at": "2026-03-01T00:00:00Z"
            }
        elif "concepts" in path and method == "PUT":
            # 更新概念 - 根据传入的json_data返回相应数据
            return {
                "id": "507f1f77bcf86cd799439012",
                "project_id": "test-project",
                "name": json_data.get("name", "Test Concept"),
                "category": json_data.get("category", "magic"),
                "content": json_data.get("content", "Test description"),
                "tags": json_data.get("tags", ["test"]),
                "related_docs": json_data.get("related_docs", []),
                "created_at": "2026-03-01T00:00:00Z",
                "updated_at": "2026-03-01T00:00:00Z"
            }
        elif "concepts" in path and method == "GET" and not path.endswith("/concepts"):
            # 获取单个概念
            return {
                "id": "507f1f77bcf86cd799439012",
                "project_id": "test-project",
                "name": "Test Concept",
                "category": "magic",
                "content": "Test description",
                "tags": ["test"],
                "related_docs": [],
                "created_at": "2026-03-01T00:00:00Z",
                "updated_at": "2026-03-01T00:00:00Z"
            }
        elif "concepts" in path and method == "POST" and "batch" in path:
            # 批量获取概念
            return {
                "concepts": [
                    {
                        "id": "507f1f77bcf86cd799439012",
                        "project_id": "test-project",
                        "name": "Fireball",
                        "category": "magic",
                        "content": "A fire spell",
                        "tags": ["fire", "spell"],
                        "related_docs": [],
                        "created_at": "2026-03-01T00:00:00Z",
                        "updated_at": "2026-03-01T00:00:00Z"
                    }
                ]
            }
        elif "concepts" in path and method == "GET":
            # 获取概念列表
            return {
                "concepts": [
                    {
                        "id": "507f1f77bcf86cd799439012",
                        "project_id": "test-project",
                        "name": "Fireball",
                        "category": "magic",
                        "content": "A fire spell",
                        "tags": ["fire", "spell"],
                        "related_docs": [],
                        "created_at": "2026-03-01T00:00:00Z",
                        "updated_at": "2026-03-01T00:00:00Z"
                    }
                ],
                "total": 1
            }
        elif "concepts" in path and method == "POST":
            # 创建概念 - 根据传入的json_data返回相应数据
            return {
                "id": "507f1f77bcf86cd799439014",
                "project_id": "test-project",
                "name": json_data.get("name", "Fireball"),
                "category": json_data.get("category", "magic"),
                "content": json_data.get("content", "A spell that creates fire"),
                "tags": json_data.get("tags", ["fire"]),
                "related_docs": json_data.get("related_docs", []),
                "created_at": "2026-03-01T00:00:00Z",
                "updated_at": "2026-03-01T00:00:00Z"
            }
        return {}

    client._request = mock_request
    return client

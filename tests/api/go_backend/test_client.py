"""GoBackend客户端测试"""
import pytest
from src.api.go_backend import GoBackendClient
from src.api.go_backend.exceptions import AuthError, DocumentNotFoundError


@pytest.mark.asyncio
async def test_client_request_success(mock_go_client):
    """测试成功的请求"""
    data = await mock_go_client._request("GET", "/documents/test-id")
    assert data["id"] == "507f1f77bcf86cd799439011"
    assert data["title"] == "Test Chapter"


@pytest.mark.asyncio
async def test_client_init():
    """测试客户端初始化"""
    from src.core.config import settings
    client = GoBackendClient()
    assert client.base_url == settings.go_backend_url
    assert client.api_key == settings.ai_service_key


@pytest.mark.asyncio
async def test_client_close(mock_go_client):
    """测试客户端关闭"""
    # 应该不会抛出异常
    await mock_go_client.close()
    assert True


@pytest.mark.asyncio
async def test_client_logger(mock_go_client):
    """测试客户端日志记录器"""
    assert mock_go_client.logger is not None
    assert mock_go_client._client is not None
    assert mock_go_client._client.headers is not None
    assert "X-AI-Service-Key" in mock_go_client._client.headers

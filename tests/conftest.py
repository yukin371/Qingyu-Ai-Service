"""
Pytest 配置和共享 fixtures
"""
import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """FastAPI 测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_settings():
    """Mock 配置"""
    from src.core import settings
    return settings


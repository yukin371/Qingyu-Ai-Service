"""
Pytest 配置和共享 fixtures
"""
import sys
from pathlib import Path

# 将项目根目录添加到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

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


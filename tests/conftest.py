"""
Pytest 配置和共享 fixtures
"""
import asyncio
import os
import sys
from pathlib import Path

# 将项目根目录添加到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 单元测试一律走 mock，但不少 agent 在构造时就会校验密钥，缺了就抛 ValidationError
# （CI 没有 secret，表现出来是三十多个 error，而不是断言失败）。这里只放占位值，
# 既不联网也不进生产配置；真跑集成测试时用真实环境变量，setdefault 不会覆盖。
for _key_env in ("GOOGLE_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY"):
    os.environ.setdefault(_key_env, "test-key")

import httpx
import pytest


class SyncASGITestClient:
    """兼容 httpx 0.28 的最小同步测试客户端。"""

    def __init__(self, app, base_url: str = "http://testserver"):
        self._app = app
        self._base_url = base_url

    async def _request_async(self, method: str, url: str, **kwargs):
        transport = httpx.ASGITransport(app=self._app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url=self._base_url,
        ) as client:
            return await client.request(method, url, **kwargs)

    def request(self, method: str, url: str, **kwargs):
        return asyncio.run(self._request_async(method, url, **kwargs))

    def get(self, url: str, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs):
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs):
        return self.request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs):
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs):
        return self.request("DELETE", url, **kwargs)


@pytest.fixture
def client():
    """FastAPI 测试客户端"""
    from src.main import app
    return SyncASGITestClient(app)


@pytest.fixture
def mock_settings():
    """Mock 配置"""
    from src.core import settings
    return settings


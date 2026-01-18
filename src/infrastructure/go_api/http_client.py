"""Go API HTTP 客户端

提供异步HTTP客户端，用于调用Go后端API
"""

import asyncio
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import aiohttp
from aiohttp import ClientSession, ClientTimeout

from src.core.config import get_settings
from src.core.exceptions import ExternalServiceError
from src.core.logger import get_logger

logger = get_logger(__name__)


class GoAPIClient:
    """Go API HTTP 客户端

    特性：
    - 异步HTTP请求
    - 连接池管理
    - 自动重试
    - 统一错误处理
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """初始化

        Args:
            base_url: Go后端基础URL（默认从配置读取）
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
        """
        settings = get_settings()
        self.base_url = (base_url or settings.go_backend_url).rstrip("/")
        self.timeout = ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self._session: Optional[ClientSession] = None

        logger.info(
            "GoAPIClient initialized",
            base_url=self.base_url,
            timeout=timeout,
            max_retries=max_retries,
        )

    async def initialize(self) -> None:
        """初始化HTTP会话"""
        if self._session is None:
            self._session = ClientSession(
                timeout=self.timeout,
                connector=aiohttp.TCPConnector(
                    limit=100,  # 连接池大小
                    limit_per_host=30,
                    ttl_dns_cache=300,
                ),
            )
            logger.info("HTTP session created")

    async def close(self) -> None:
        """关闭HTTP会话"""
        if self._session:
            await self._session.close()
            self._session = None
            logger.info("HTTP session closed")

    async def call_api(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        user_id: Optional[str] = None,
        agent_call_id: Optional[str] = None,
        auth_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """调用Go API

        Args:
            method: HTTP方法（GET, POST, PUT, DELETE）
            endpoint: API端点（如 /api/v1/projects/xxx/characters）
            data: 请求体数据
            params: 查询参数
            headers: 自定义请求头
            user_id: 用户ID（添加到X-User-ID头）
            agent_call_id: Agent调用ID（添加到X-Agent-Call-ID头）
            auth_token: 认证Token

        Returns:
            API响应数据（JSON）

        Raises:
            ExternalServiceError: API调用失败
        """
        if not self._session:
            await self.initialize()

        # 构建完整URL
        url = urljoin(self.base_url, endpoint.lstrip("/"))

        # 构建请求头
        request_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if auth_token:
            request_headers["Authorization"] = f"Bearer {auth_token}"
        if user_id:
            request_headers["X-User-ID"] = user_id
        if agent_call_id:
            request_headers["X-Agent-Call-ID"] = agent_call_id
        if headers:
            request_headers.update(headers)

        # 重试逻辑
        last_error = None
        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    f"API call attempt {attempt + 1}",
                    method=method,
                    url=url,
                    params=params,
                )

                async with self._session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    headers=request_headers,
                ) as response:
                    # 读取响应
                    response_data = await response.json()

                    # 检查HTTP状态码
                    if response.status >= 400:
                        error_msg = response_data.get("message", "Unknown error")
                        logger.error(
                            "API call failed",
                            status=response.status,
                            error=error_msg,
                            url=url,
                        )
                        raise ExternalServiceError(
                            f"Go API error ({response.status}): {error_msg}",
                            service_name="go_backend",
                            status_code=response.status,
                        )

                    logger.debug(
                        "API call succeeded",
                        method=method,
                        url=url,
                        status=response.status,
                    )
                    return response_data

            except aiohttp.ClientError as e:
                last_error = e
                logger.warning(
                    f"API call attempt {attempt + 1} failed",
                    error=str(e),
                    url=url,
                )

                # 如果不是最后一次尝试，等待后重试
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # 指数退避

            except asyncio.TimeoutError as e:
                last_error = e
                logger.warning(
                    f"API call attempt {attempt + 1} timeout",
                    url=url,
                )

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        # 所有重试失败
        raise ExternalServiceError(
            f"Go API call failed after {self.max_retries} retries: {str(last_error)}",
            service_name="go_backend",
        )

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()


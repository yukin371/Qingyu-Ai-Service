"""Go后端HTTP客户端"""
import httpx
from typing import Optional, Dict, Any
from structlog import get_logger

from ...core.config import settings
from .exceptions import (
    GoBackendError,
    AuthError,
    PermissionError,
    DocumentNotFoundError,
    ConceptNotFoundError,
    ValidationError,
    APIError,
)

logger = get_logger(__name__)


class GoBackendClient:
    """
    Go后端HTTP客户端

    用于Python AI服务调用Go后端的内部API。
    """

    def __init__(self):
        self.base_url = settings.go_backend_url
        self.api_key = settings.ai_service_key
        self.logger = logger.bind(component="go_backend_client")

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "X-AI-Service-Key": self.api_key,
                "Content-Type": "application/json"
            },
            timeout=30.0
        )

    async def close(self):
        """关闭客户端"""
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        发送HTTP请求

        Args:
            method: HTTP方法
            path: 请求路径
            params: 查询参数
            json_data: JSON body

        Returns:
            响应数据

        Raises:
            GoBackendError: 请求失败
        """
        url = f"/api/v1/internal/ai{path}"

        self.logger.debug(
            "Sending request to Go backend",
            method=method,
            path=path,
            params=params
        )

        try:
            response = await self._client.request(
                method=method,
                url=url,
                params=params,
                json=json_data
            )

            if response.status_code == 401:
                raise AuthError("Invalid API key")
            elif response.status_code == 403:
                raise PermissionError("Access denied")
            elif response.status_code == 404:
                if "/concepts" in path:
                    raise ConceptNotFoundError("Concept not found")
                raise DocumentNotFoundError("Document not found")
            elif response.status_code == 400:
                raise ValidationError(response.json().get("error", "Invalid request"))
            elif response.status_code >= 400:
                raise APIError(f"API error: {response.status_code}")

            return response.json()

        except httpx.HTTPError as e:
            self.logger.error("HTTP request failed", error=str(e))
            raise GoBackendError(f"Request failed: {e}")

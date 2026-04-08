"""
Change Request 后端交互模块
"""
from typing import List, Optional
from .client import GoBackendClient
from .exceptions import GoBackendError
from ...core.logger import get_logger

logger = get_logger(__name__)


class ChangeRequestPayload:
    """Change Request 载荷"""

    def __init__(
        self,
        project_id: str,
        chapter_id: str,
        category: str,
        title: str,
        description: str,
        suggested_change: dict,
        entity_id: Optional[str] = None,
        entity_name: Optional[str] = None,
        evidence: Optional[List[str]] = None,
        confidence: float = 0.8,
    ):
        self.project_id = project_id
        self.chapter_id = chapter_id
        self.category = category
        self.entity_id = entity_id
        self.entity_name = entity_name
        self.title = title
        self.description = description
        self.suggested_change = suggested_change
        self.evidence = evidence or []
        self.confidence = confidence

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "chapter_id": self.chapter_id,
            "category": self.category,
            "entity_id": self.entity_id,
            "entity_name": self.entity_name,
            "title": self.title,
            "description": self.description,
            "suggested_change": self.suggested_change,
            "evidence": self.evidence,
            "confidence": self.confidence,
        }


class ChangeRequestOperations:
    """Change Request 操作类"""

    def __init__(self, client: GoBackendClient):
        self._client = client

    async def create(self, payload: ChangeRequestPayload) -> dict:
        """创建 Change Request"""
        try:
            logger.info(
                "create_change_request",
                project_id=payload.project_id,
                chapter_id=payload.chapter_id,
                category=payload.category,
            )
            response = await self._client._request(
                method="POST",
                path="/api/v1/writer/story-harness/change-requests",
                json=payload.to_dict(),
            )
            logger.info("change_request_created", cr_id=response.get("id"))
            return response
        except GoBackendError as e:
            logger.error("create_change_request_failed", error=str(e))
            raise

    async def create_batch(self, payloads: List[ChangeRequestPayload]) -> List[dict]:
        """批量创建 Change Request"""
        results = []
        for payload in payloads:
            try:
                result = await self.create(payload)
                results.append(result)
            except Exception as e:
                logger.warning(
                    "skipping_failed_cr",
                    error=str(e),
                    title=payload.title,
                )
        return results

    async def list_by_chapter(
        self, project_id: str, chapter_id: str
    ) -> List[dict]:
        """获取章节下的所有 CR"""
        try:
            response = await self._client._request(
                method="GET",
                path=f"/api/v1/writer/story-harness/projects/{project_id}/chapters/{chapter_id}/change-requests",
            )
            return response.get("data", [])
        except GoBackendError as e:
            logger.error("list_change_requests_failed", error=str(e))
            return []

    async def accept(self, cr_id: str) -> dict:
        """接受 CR"""
        try:
            response = await self._client._request(
                method="POST",
                path=f"/api/v1/writer/story-harness/change-requests/{cr_id}/accept",
            )
            return response
        except GoBackendError as e:
            logger.error("accept_change_request_failed", error=str(e))
            raise

    async def reject(self, cr_id: str) -> dict:
        """拒绝 CR"""
        try:
            response = await self._client._request(
                method="POST",
                path=f"/api/v1/writer/story-harness/change-requests/{cr_id}/reject",
            )
            return response
        except GoBackendError as e:
            logger.error("reject_change_request_failed", error=str(e))
            raise

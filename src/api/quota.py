"""
配额API路由
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict
from datetime import datetime, timedelta

from src.api.models.quota import (
    QuotaInfo,
    ConsumeQuotaRequest,
    ConsumeQuotaResponse
)
from ..core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

# 临时内存存储（生产环境应使用数据库）
_quota_store: Dict[str, QuotaInfo] = {}


async def get_or_create_quota(user_id: str) -> QuotaInfo:
    """获取或创建配额信息"""
    if user_id not in _quota_store:
        # 创建默认配额
        _quota_store[user_id] = QuotaInfo(
            user_id=user_id,
            quota_type="free",
            total_quota=10000,
            used_quota=0,
            remaining_quota=10000,
            reset_at=datetime.now() + timedelta(days=30)
        )
    return _quota_store[user_id]


@router.get("/{user_id}", response_model=QuotaInfo)
async def get_quota(user_id: str):
    """
    查询配额

    获取用户的配额信息。

    **响应示例**:
    ```json
    {
      "user_id": "user123",
      "quota_type": "free",
      "total_quota": 10000,
      "used_quota": 300,
      "remaining_quota": 9700,
      "reset_at": "2024-02-01T00:00:00Z"
    }
    ```
    """
    try:
        logger.info("get_quota_request", user_id=user_id)

        quota_info = await get_or_create_quota(user_id)

        logger.info(
            "get_quota_success",
            user_id=user_id,
            remaining_quota=quota_info.remaining_quota
        )
        return quota_info

    except Exception as e:
        logger.error("get_quota_error", user_id=user_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询配额失败: {str(e)}"
        )


@router.post("/{user_id}/consume", response_model=ConsumeQuotaResponse)
async def consume_quota(user_id: str, request: ConsumeQuotaRequest):
    """
    消费配额

    扣除用户配额。

    **请求示例**:
    ```json
    {
      "tokens": 100,
      "operation": "chat"
    }
    ```

    **响应示例**:
    ```json
    {
      "success": true,
      "remaining_quota": 9600,
      "message": "配额扣除成功"
    }
    ```
    """
    try:
        logger.info(
            "consume_quota_request",
            user_id=user_id,
            tokens=request.tokens,
            operation=request.operation
        )

        quota_info = await get_or_create_quota(user_id)

        # 检查配额是否足够
        if quota_info.remaining_quota < request.tokens:
            logger.warning(
                "insufficient_quota",
                user_id=user_id,
                requested=request.tokens,
                remaining=quota_info.remaining_quota
            )
            return ConsumeQuotaResponse(
                success=False,
                remaining_quota=quota_info.remaining_quota,
                message=f"配额不足：剩余 {quota_info.remaining_quota}，需要 {request.tokens}"
            )

        # 扣除配额
        quota_info.used_quota += request.tokens
        quota_info.remaining_quota -= request.tokens

        logger.info(
            "consume_quota_success",
            user_id=user_id,
            tokens_consumed=request.tokens,
            remaining_quota=quota_info.remaining_quota
        )

        return ConsumeQuotaResponse(
            success=True,
            remaining_quota=quota_info.remaining_quota,
            message=f"配额扣除成功：消费 {request.tokens} tokens"
        )

    except Exception as e:
        logger.error("consume_quota_error", user_id=user_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"消费配额失败: {str(e)}"
        )


@router.get("/statistics/{user_id}")
async def get_quota_statistics(user_id: str):
    """
    配额统计

    获取用户配额使用统计信息。

    **响应示例**:
    ```json
    {
      "user_id": "user123",
      "total_usage": 3000,
      "daily_average": 100,
      "operations": {
        "chat": 2000,
        "writing": 1000
      }
    }
    ```
    """
    try:
        logger.info("get_quota_statistics", user_id=user_id)

        quota_info = await get_or_create_quota(user_id)

        # TODO: 实现更详细的统计
        statistics = {
            "user_id": user_id,
            "total_usage": quota_info.used_quota,
            "remaining_quota": quota_info.remaining_quota,
            "usage_percentage": (quota_info.used_quota / quota_info.total_quota * 100)
            if quota_info.total_quota > 0 else 0,
            "operations": {
                "chat": quota_info.used_quota // 2,
                "writing": quota_info.used_quota // 2
            }
        }

        logger.info("get_quota_statistics_success", user_id=user_id)
        return statistics

    except Exception as e:
        logger.error("get_quota_statistics_error", user_id=user_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取配额统计失败: {str(e)}"
        )

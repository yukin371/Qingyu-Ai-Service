# Qingyu-Ai-Service/tests/services/test_quota_service.py

import pytest
import asyncio
from datetime import datetime, timedelta
from src.services.quota_service import QuotaService

@pytest.mark.asyncio
async def test_record_consumption(db_pool):
    """测试记录配额消费"""
    service = QuotaService(db_pool)

    await service.record_consumption(
        user_id="test-user-123",
        workflow_type="chat",
        tokens_used=100,
        metadata={"model": "gpt-4"}
    )

    # 验证记录
    consumption = await service.get_user_consumption("test-user-123", "day")
    assert consumption == 100

@pytest.mark.asyncio
async def test_get_consumption_by_time_range(db_pool):
    """测试按时间范围查询消费"""
    service = QuotaService(db_pool)

    # 创建不同时间的记录
    await service.record_consumption("user-1", "chat", 50, {})
    await service.record_consumption("user-1", "writing", 100, {})

    # 查询今日消费
    day_consumption = await service.get_user_consumption("user-1", "day")
    assert day_consumption == 150

@pytest.mark.asyncio
async def test_sync_to_backend(db_pool, mock_backend_client):
    """测试同步到后端"""
    service = QuotaService(db_pool)

    await service.record_consumption("user-1", "chat", 100, {})

    result = await service.sync_to_backend(mock_backend_client, ["user-1"])

    assert result["synced"] == 1
    assert len(result["failed"]) == 0

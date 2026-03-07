"""
QuotaService 单元测试

测试配额服务的核心功能：
- 记录配额消费
- 查询用户消费统计
- 同步到后端
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.quota_service import QuotaService


@pytest.fixture
def db_pool():
    """创建测试数据库连接池"""
    # Mock asyncpg Pool
    pool = MagicMock()
    pool.acquire = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock()
    pool.acquire.return_value.__aexit__ = AsyncMock()
    return pool


@pytest.fixture
def mock_backend_client():
    """创建 Mock 后端客户端"""
    client = AsyncMock()
    client.SyncQuota = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_record_consumption(db_pool):
    """测试记录配额消费"""
    service = QuotaService(db_pool)

    # Mock 数据库操作
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=1)
    db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    await service.record_consumption(
        user_id="test-user-123",
        workflow_type="chat",
        tokens_used=100,
        metadata={"model": "gpt-4"}
    )

    # 验证 SQL 被正确调用
    mock_conn.fetchval.assert_called_once()
    call_args = mock_conn.fetchval.call_args
    # 验证 SQL 语句
    assert "INSERT INTO quota_consumption_records" in call_args[0][0]
    # 验证参数（SQL 使用参数化查询，所以参数在第二个位置）
    assert call_args[0][1] == "test-user-123"
    assert call_args[0][2] == "chat"
    assert call_args[0][3] == 100


@pytest.mark.asyncio
async def test_get_user_consumption(db_pool):
    """测试获取用户消费统计"""
    service = QuotaService(db_pool)

    # Mock 数据库操作 - 返回 100 tokens
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value={"total": 100})
    db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    consumption = await service.get_user_consumption("test-user-123", "day")

    assert consumption == 100
    mock_conn.fetchrow.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_consumption_week(db_pool):
    """测试获取用户周消费统计"""
    service = QuotaService(db_pool)

    # Mock 数据库操作 - 返回 500 tokens
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value={"total": 500})
    db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    consumption = await service.get_user_consumption("test-user-123", "week")

    assert consumption == 500
    # 验证 SQL 包含时间范围过滤
    call_args = mock_conn.fetchrow.call_args
    assert "1 week" in call_args[0][0]


@pytest.mark.asyncio
async def test_get_user_consumption_month(db_pool):
    """测试获取用户月消费统计"""
    service = QuotaService(db_pool)

    # Mock 数据库操作 - 返回 2000 tokens
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value={"total": 2000})
    db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    consumption = await service.get_user_consumption("test-user-123", "month")

    assert consumption == 2000
    # 验证 SQL 包含时间范围过滤
    call_args = mock_conn.fetchrow.call_args
    assert "1 month" in call_args[0][0]


@pytest.mark.asyncio
async def test_get_user_consumption_all(db_pool):
    """测试获取用户全部消费统计"""
    service = QuotaService(db_pool)

    # Mock 数据库操作 - 返回 5000 tokens
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value={"total": 5000})
    db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    consumption = await service.get_user_consumption("test-user-123", "all")

    assert consumption == 5000
    # 验证 SQL 不包含时间范围过滤
    call_args = mock_conn.fetchrow.call_args
    sql = call_args[0][0]
    assert "1 day" not in sql
    assert "1 week" not in sql
    assert "1 month" not in sql


@pytest.mark.asyncio
async def test_get_consumption_records(db_pool):
    """测试获取用户消费记录列表"""
    service = QuotaService(db_pool)

    # Mock 数据库操作
    mock_rows = [
        {
            "id": 1,
            "user_id": "test-user-123",
            "workflow_type": "chat",
            "tokens_used": 100,
            "quota_consumed": 100,
            "metadata": {"model": "gpt-4"},
            "consumed_at": datetime.now()
        },
        {
            "id": 2,
            "user_id": "test-user-123",
            "workflow_type": "writing",
            "tokens_used": 200,
            "quota_consumed": 200,
            "metadata": {"model": "gpt-4"},
            "consumed_at": datetime.now()
        }
    ]

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=mock_rows)
    db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    records = await service.get_consumption_records("test-user-123", limit=10)

    assert len(records) == 2
    assert records[0]["workflow_type"] == "chat"
    assert records[1]["workflow_type"] == "writing"
    assert records[0]["tokens_used"] == 100
    assert records[1]["tokens_used"] == 200


@pytest.mark.asyncio
async def test_sync_to_backend_success(db_pool, mock_backend_client):
    """测试同步到后端 - 成功场景"""
    service = QuotaService(db_pool)

    # Mock 数据库操作
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value={"total": 100})
    mock_conn.execute = AsyncMock()
    db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    result = await service.sync_to_backend(mock_backend_client, ["user-1", "user-2"])

    assert result["synced"] == 2
    assert len(result["failed"]) == 0
    # 验证后端客户端被调用
    assert mock_backend_client.SyncQuota.call_count == 2


@pytest.mark.asyncio
async def test_sync_to_backend_partial_failure(db_pool, mock_backend_client):
    """测试同步到后端 - 部分失败场景"""
    service = QuotaService(db_pool)

    # Mock 数据库操作
    mock_conn = AsyncMock()
    mock_conn.fetchrow = AsyncMock(return_value={"total": 100})
    mock_conn.execute = AsyncMock()
    db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    # 第一个用户成功，第二个用户失败
    async def side_effect(user_id, consumption):
        if user_id == "user-2":
            raise Exception("Network error")
    
    mock_backend_client.SyncQuota = AsyncMock(side_effect=side_effect)

    result = await service.sync_to_backend(mock_backend_client, ["user-1", "user-2"])

    assert result["synced"] == 1
    assert len(result["failed"]) == 1
    assert "user-2" in result["failed"]


@pytest.mark.asyncio
async def test_record_consumption_with_metadata(db_pool):
    """测试记录配额消费 - 包含元数据"""
    service = QuotaService(db_pool)

    # Mock 数据库操作
    mock_conn = AsyncMock()
    mock_conn.fetchval = AsyncMock(return_value=1)
    db_pool.acquire.return_value.__aenter__.return_value = mock_conn

    metadata = {
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 2000,
        "workflow_id": "workflow-123"
    }

    await service.record_consumption(
        user_id="test-user-123",
        workflow_type="chat",
        tokens_used=150,
        metadata=metadata
    )

    # 验证 SQL 被正确调用
    mock_conn.fetchval.assert_called_once()

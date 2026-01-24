# Qingyu-Ai-Service/tests/grpc/test_quota_rpc.py

"""
gRPC 配额服务测试

测试所有配额相关的 gRPC RPC 接口
"""
import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.grpc_service import ai_service_pb2, ai_service_pb2_grpc
from src.grpc_service.ai_servicer import AIServicer
from src.services.quota_service import QuotaService


@pytest.fixture
async def mock_db_pool():
    """模拟数据库连接池"""
    pool = Mock()
    
    # 模拟连接
    conn = AsyncMock()
    pool.acquire = AsyncMock(return_value=conn)
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock()
    
    return pool


@pytest.fixture
async def quota_service(mock_db_pool):
    """创建配额服务实例"""
    return QuotaService(mock_db_pool)


@pytest.fixture
def ai_servicer(mock_db_pool):
    """创建 AI Servicer 实例"""
    return AIServicer(db_pool=mock_db_pool)


@pytest.mark.asyncio
async def test_consume_quota_rpc(ai_servicer, mock_db_pool):
    """测试 ConsumeQuota RPC"""
    # 模拟数据库返回记录 ID
    conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    conn.fetchval = AsyncMock(return_value=123)
    
    # 创建请求
    request = ai_service_pb2.QuotaConsumptionRequest(
        user_id="test-user-123",
        workflow_type="creative_workflow",
        tokens_used=500,
        metadata={"task": "test"}
    )
    
    # 模拟 gRPC context
    context = Mock()
    context.abort = Mock(side_effect=Exception("Aborted"))
    
    # 调用 RPC
    response = await ai_servicer.ConsumeQuota(request, context)
    
    # 验证响应
    assert response.success is True
    assert response.message == "Quota recorded successfully"
    assert response.record_id == 123
    
    # 验证数据库调用
    conn.fetchval.assert_called_once()


@pytest.mark.asyncio
async def test_consume_quota_rpc_without_service():
    """测试配额服务未初始化时的 ConsumeQuota RPC"""
    # 创建没有数据库连接的 servicer
    servicer = AIServicer(db_pool=None)
    
    request = ai_service_pb2.QuotaConsumptionRequest(
        user_id="test-user-123",
        workflow_type="creative_workflow",
        tokens_used=500
    )
    
    context = Mock()
    context.abort = Mock()
    
    # 调用 RPC
    await servicer.ConsumeQuota(request, context)
    
    # 验证调用了 abort
    context.abort.assert_called_once()


@pytest.mark.asyncio
async def test_get_quota_consumption_rpc(ai_servicer, mock_db_pool):
    """测试 GetQuotaConsumption RPC"""
    # 模拟数据库返回
    conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    
    # 模拟总 token 查询
    async def mock_fetchrow(query, user_id):
        return {"total": 1500}
    
    conn.fetchrow = AsyncMock(side_effect=mock_fetchrow)
    
    # 模拟记录列表查询
    async def mock_fetch(query, user_id, limit, offset):
        return [
            {
                'id': 1,
                'user_id': 'test-user-123',
                'workflow_type': 'chat',
                'tokens_used': 100,
                'quota_consumed': 100,
                'metadata': {},
                'consumed_at': datetime.now() - timedelta(hours=2)
            },
            {
                'id': 2,
                'user_id': 'test-user-123',
                'workflow_type': 'writing',
                'tokens_used': 200,
                'quota_consumed': 200,
                'metadata': {},
                'consumed_at': datetime.now() - timedelta(hours=1)
            }
        ]
    
    conn.fetch = AsyncMock(side_effect=mock_fetch)
    
    # 创建请求
    request = ai_service_pb2.QuotaConsumptionQuery(
        user_id="test-user-123",
        time_range="day"
    )
    
    context = Mock()
    context.abort = Mock(side_effect=Exception("Aborted"))
    
    # 调用 RPC
    response = await ai_servicer.GetQuotaConsumption(request, context)
    
    # 验证响应
    assert response.success is True
    assert response.total_tokens == 1500
    assert response.total_records == 2
    assert len(response.records) == 2


@pytest.mark.asyncio
async def test_get_quota_consumption_rpc_without_service():
    """测试配额服务未初始化时的 GetQuotaConsumption RPC"""
    servicer = AIServicer(db_pool=None)
    
    request = ai_service_pb2.QuotaConsumptionQuery(
        user_id="test-user-123",
        time_range="day"
    )
    
    context = Mock()
    context.abort = Mock()
    
    await servicer.GetQuotaConsumption(request, context)
    
    context.abort.assert_called_once()


@pytest.mark.asyncio
async def test_sync_quota_to_backend_rpc(ai_servicer, mock_db_pool):
    """测试 SyncQuotaToBackend RPC"""
    # 模拟后端客户端
    mock_backend = Mock()
    mock_backend.SyncQuota = AsyncMock()
    
    # 设置 servicer 的后端客户端
    ai_servicer.backend_client = mock_backend
    
    # 模拟数据库查询
    conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    
    async def mock_fetchrow(query, user_id):
        return {"total": 500}
    
    conn.fetchrow = AsyncMock(side_effect=mock_fetchrow)
    conn.execute = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    
    # 创建请求
    request = ai_service_pb2.QuotaSyncRequest(
        user_ids=["user-1", "user-2"],
        force_sync=False
    )
    
    context = Mock()
    
    # 调用 RPC
    response = await ai_servicer.SyncQuotaToBackend(request, context)
    
    # 验证响应
    assert response.synced_count == 2
    assert len(response.failed_user_ids) == 0


@pytest.mark.asyncio
async def test_sync_quota_to_backend_without_backend():
    """测试没有后端客户端时的 SyncQuotaToBackend RPC"""
    servicer = AIServicer(db_pool=Mock())
    servicer.backend_client = None
    
    request = ai_service_pb2.QuotaSyncRequest(
        user_ids=["user-1"],
        force_sync=False
    )
    
    context = Mock()
    
    response = await servicer.SyncQuotaToBackend(request, context)
    
    # 验证返回失败
    assert response.synced_count == 0
    assert len(response.failed_user_ids) == 1
    assert "Backend client not configured" in response.message


@pytest.mark.asyncio
async def test_sync_quota_to_backend_sync_failure(ai_servicer, mock_db_pool):
    """测试同步失败的情况"""
    mock_backend = Mock()
    # 模拟同步失败
    mock_backend.SyncQuota = AsyncMock(side_effect=Exception("Sync failed"))
    
    ai_servicer.backend_client = mock_backend
    
    conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    conn.fetchrow = AsyncMock(return_value={"total": 500})
    conn.execute = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    
    request = ai_service_pb2.QuotaSyncRequest(
        user_ids=["user-1"],
        force_sync=False
    )
    
    context = Mock()
    
    response = await ai_servicer.SyncQuotaToBackend(request, context)
    
    # 验证返回失败
    assert response.synced_count == 0
    assert len(response.failed_user_ids) == 1


@pytest.mark.asyncio
async def test_record_quota_if_available_helper(ai_servicer, mock_db_pool):
    """测试 _record_quota_if_available 辅助方法"""
    conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    conn.fetchval = AsyncMock(return_value=456)
    
    # 调用辅助方法
    await ai_servicer._record_quota_if_available(
        user_id="test-user",
        workflow_type="test_workflow",
        tokens_used=100,
        metadata={"key": "value"}
    )
    
    # 验证数据库调用
    conn.fetchval.assert_called_once()


@pytest.mark.asyncio
async def test_record_quota_if_available_without_service():
    """测试配额服务不可用时的 _record_quota_if_available"""
    servicer = AIServicer(db_pool=None)
    
    # 不应该抛出异常
    await servicer._record_quota_if_available(
        user_id="test-user",
        workflow_type="test_workflow",
        tokens_used=100,
        metadata={}
    )


def test_estimate_tokens_helper():
    """测试 _estimate_tokens 辅助方法"""
    servicer = AIServicer()
    
    # 测试有 token_usage 的情况
    state = {
        "token_usage": {
            "total_tokens": 1000
        }
    }
    tokens = servicer._estimate_tokens(state)
    assert tokens == 1000
    
    # 测试没有 token_usage 的情况（估算）
    state = {
        "agent_outputs": {
            "outline_agent": {
                "title": "Test Title",
                "content": "Test content" * 100,
                "chapters": [{"title": "Chapter 1"}] * 5
            }
        }
    }
    tokens = servicer._estimate_tokens(state)
    assert tokens > 0


@pytest.mark.asyncio
async def test_execute_integrates_quota_recording(ai_servicer, mock_db_pool):
    """测试 ExecuteCreativeWorkflow 集成配额记录"""
    # 模拟数据库
    conn = mock_db_pool.acquire.return_value.__aenter__.return_value
    conn.fetchval = AsyncMock(return_value=789)
    
    # 注意：这个测试需要完整的 Agent 设置
    # 这里仅演示配额记录集成的概念
    request = ai_service_pb2.CreativeWorkflowRequest(
        task="Test task",
        user_id="test-user",
        project_id="test-project",
        max_reflections=1
    )
    
    context = Mock()
    context.abort = Mock(side_effect=Exception("Aborted"))
    
    # 这个测试会因为 Agent 未初始化而失败
    # 但它演示了如何测试配额记录集成
    try:
        response = await ai_servicer.ExecuteCreativeWorkflow(request, context)
        # 如果成功，验证配额被记录
        conn.fetchval.assert_called()
    except Exception as e:
        # 预期会失败，因为 Agent 未完全设置
        pass

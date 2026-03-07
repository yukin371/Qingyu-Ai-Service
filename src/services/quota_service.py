"""
AI 服务配额管理

提供配额消费记录、查询和同步功能
"""
import asyncpg
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import logging

from src.core.logger import get_logger

logger = get_logger(__name__)


class QuotaService:
    """AI 服务配额管理"""

    def __init__(self, db_pool: asyncpg.Pool):
        """初始化配额服务

        Args:
            db_pool: PostgreSQL 连接池
        """
        self.db = db_pool

    async def record_consumption(
        self,
        user_id: str,
        workflow_type: str,
        tokens_used: int,
        metadata: Dict
    ) -> int:
        """记录配额消费

        Args:
            user_id: 用户 ID
            workflow_type: 工作流类型 (chat, writing, creative)
            tokens_used: 使用的 token 数量
            metadata: 额外的元数据

        Returns:
            int: 记录 ID
        """
        async with self.db.acquire() as conn:
            record_id = await conn.fetchval("""
                INSERT INTO quota_consumption_records
                (user_id, workflow_type, tokens_used, quota_consumed, metadata)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (user_id, consumed_at)
                DO UPDATE SET
                    tokens_used = quota_consumption_records.tokens_used + $3,
                    quota_consumed = quota_consumption_records.quota_consumed + $4
                RETURNING id
            """, user_id, workflow_type, tokens_used, tokens_used, metadata)

        logger.info(f"Recorded quota consumption: user={user_id}, tokens={tokens_used}")
        return record_id

    async def get_user_consumption(
        self,
        user_id: str,
        time_range: str = "day"
    ) -> int:
        """获取用户消费统计

        Args:
            user_id: 用户 ID
            time_range: 时间范围 (day, week, month, all)

        Returns:
            int: 消费的 token 数量
        """
        sql = """
            SELECT COALESCE(SUM(tokens_used), 0) as total
            FROM quota_consumption_records
            WHERE user_id = $1
        """

        if time_range == "day":
            sql += " AND consumed_at > NOW() - INTERVAL '1 day'"
        elif time_range == "week":
            sql += " AND consumed_at > NOW() - INTERVAL '1 week'"
        elif time_range == "month":
            sql += " AND consumed_at > NOW() - INTERVAL '1 month'"

        async with self.db.acquire() as conn:
            row = await conn.fetchrow(sql, user_id)
            return int(row['total'])

    async def get_consumption_records(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """获取用户消费记录列表

        Args:
            user_id: 用户 ID
            limit: 返回记录数量限制
            offset: 偏移量

        Returns:
            List[Dict]: 消费记录列表
        """
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, user_id, workflow_type, tokens_used,
                       quota_consumed, metadata, consumed_at
                FROM quota_consumption_records
                WHERE user_id = $1
                ORDER BY consumed_at DESC
                LIMIT $2 OFFSET $3
            """, user_id, limit, offset)

        return [dict(row) for row in rows]

    async def sync_to_backend(
        self,
        backend_client,
        user_ids: List[str]
    ) -> Dict:
        """同步消费记录到后端

        Args:
            backend_client: 后端 gRPC 客户端
            user_ids: 用户 ID 列表

        Returns:
            Dict: {"synced": int, "failed": List[str]}
        """
        results = {"synced": 0, "failed": []}

        for user_id in user_ids:
            try:
                consumption = await self.get_user_consumption(user_id, "day")

                # 调用后端同步接口
                await backend_client.SyncQuota(user_id, consumption)

                # 更新同步状态
                await self._update_sync_status(user_id, "synced", consumption)
                results["synced"] += 1

                logger.info(f"Synced quota for user={user_id}, consumption={consumption}")

            except Exception as e:
                await self._update_sync_status(user_id, "failed", 0, str(e))
                results["failed"].append(user_id)
                logger.error(f"Failed to sync quota for user={user_id}: {e}")

        return results

    async def _update_sync_status(
        self,
        user_id: str,
        status: str,
        tokens: int = 0,
        error: Optional[str] = None
    ):
        """更新同步状态

        Args:
            user_id: 用户 ID
            status: 同步状态 (synced, failed)
            tokens: 同步的 token 数量
            error: 错误信息（如果失败）
        """
        async with self.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO quota_sync_status (user_id, sync_status, last_sync_tokens, error_message)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id)
                DO UPDATE SET
                    sync_status = $2,
                    last_sync_tokens = $3,
                    error_message = $4,
                    updated_at = NOW()
            """, user_id, status, tokens, error)

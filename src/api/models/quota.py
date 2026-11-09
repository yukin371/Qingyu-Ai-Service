"""
配额相关数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class QuotaInfo(BaseModel):
    """配额信息"""
    user_id: str = Field(..., description="用户ID")
    quota_type: str = Field(..., description="配额类型: free, paid, enterprise")
    total_quota: int = Field(..., description="总配额")
    used_quota: int = Field(..., description="已使用配额")
    remaining_quota: int = Field(..., description="剩余配额")
    reset_at: Optional[datetime] = Field(None, description="重置时间")


class ConsumeQuotaRequest(BaseModel):
    """消费配额请求"""
    user_id: str = Field(..., description="用户ID")
    tokens: int = Field(..., ge=0, description="消费的token数")
    operation: str = Field(..., description="操作类型: chat, writing, etc.")


class ConsumeQuotaResponse(BaseModel):
    """消费配额响应"""
    success: bool = Field(..., description="是否成功")
    remaining_quota: int = Field(..., description="剩余配额")
    message: Optional[str] = Field(None, description="消息")

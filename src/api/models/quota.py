"""
配额 API 数据模型
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class QuotaInfo(BaseModel):
    """配额信息"""
    user_id: str = Field(..., description="用户ID")
    quota_type: str = Field(..., description="配额类型: free/premium")
    total_quota: int = Field(..., description="总配额")
    used_quota: int = Field(..., description="已使用配额")
    remaining_quota: int = Field(..., description="剩余配额")
    reset_at: datetime = Field(..., description="重置时间")


class ConsumeQuotaRequest(BaseModel):
    """消费配额请求"""
    tokens: int = Field(..., description="消费的 token 数")
    operation: str = Field(default="chat", description="操作类型: chat/writing")


class ConsumeQuotaResponse(BaseModel):
    """消费配额响应"""
    success: bool = Field(..., description="是否成功")
    remaining_quota: int = Field(..., description="剩余配额")
    message: str = Field(..., description="响应消息")

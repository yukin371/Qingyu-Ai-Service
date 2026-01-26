"""
聊天 API 数据模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class Message(BaseModel):
    """聊天消息"""
    role: str = Field(..., description="消息角色: user/assistant/system")
    content: str = Field(..., description="消息内容")


class Usage(BaseModel):
    """Token 使用统计"""
    prompt_tokens: int = Field(..., description="输入 token 数")
    completion_tokens: int = Field(..., description="输出 token 数")
    total_tokens: int = Field(..., description="总 token 数")


class ChatRequest(BaseModel):
    """聊天请求"""
    messages: List[Message] = Field(..., description="聊天消息列表")
    model: str = Field(default="gpt-4", description="使用的模型")
    temperature: Optional[float] = Field(default=0.7, description="温度参数")
    max_tokens: Optional[int] = Field(default=2000, description="最大 token 数")


class ChatResponse(BaseModel):
    """聊天响应"""
    message: str = Field(..., description="AI 回复消息")
    usage: Usage = Field(..., description="Token 使用统计")
    model: str = Field(..., description="使用的模型")
    quota_remaining: int = Field(..., description="剩余配额")

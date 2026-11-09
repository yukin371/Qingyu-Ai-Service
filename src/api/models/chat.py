"""
聊天相关数据模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class Message(BaseModel):
    """聊天消息"""
    role: str = Field(..., description="消息角色: user, assistant, system")
    content: str = Field(..., description="消息内容")


class ChatRequest(BaseModel):
    """聊天请求"""
    messages: List[Message] = Field(..., description="对话历史")
    model: str = Field(default="gpt-4", description="模型名称")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0, description="温度参数")
    max_tokens: int = Field(default=2000, ge=1, description="最大token数")
    stream: bool = Field(default=False, description="是否流式输出")


class Usage(BaseModel):
    """Token使用统计"""
    prompt_tokens: int = Field(..., description="提示词token数")
    completion_tokens: int = Field(..., description="完成token数")
    total_tokens: int = Field(..., description="总token数")


class ChatResponse(BaseModel):
    """聊天响应"""
    message: str = Field(..., description="AI回复消息")
    usage: Usage = Field(..., description="Token使用统计")
    model: str = Field(..., description="使用的模型")
    quota_remaining: int = Field(..., description="剩余配额")

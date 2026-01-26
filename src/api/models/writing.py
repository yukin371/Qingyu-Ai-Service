"""
写作 API 数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class WritingContext(BaseModel):
    """写作上下文"""
    genre: Optional[str] = Field(None, description="作品类型/题材")
    characters: Optional[list] = Field(default_factory=list, description="角色列表")
    setting: Optional[str] = Field(None, description="场景设定")
    style: Optional[str] = Field(None, description="写作风格")


class ContinueWritingRequest(BaseModel):
    """续写请求"""
    project_id: str = Field(..., description="项目ID")
    current_text: str = Field(..., description="当前文本")
    continue_length: int = Field(default=500, description="续写长度")
    context: Optional[WritingContext] = Field(None, description="写作上下文")
    model: str = Field(default="gpt-4", description="使用的模型")


class PolishRequest(BaseModel):
    """润色请求"""
    text: str = Field(..., description="待润色的文本")
    style: str = Field(default="文学", description="润色风格")
    focus_areas: list = Field(default_factory=list, description="关注领域: grammar/vocabulary/flow")
    model: str = Field(default="gpt-4", description="使用的模型")


class ExpandRequest(BaseModel):
    """扩展请求"""
    text: str = Field(..., description="待扩展的文本")
    expand_ratio: float = Field(default=1.5, description="扩展比例")
    direction: str = Field(default="详细描述", description="扩展方向")
    model: str = Field(default="gpt-4", description="使用的模型")


class WritingResponse(BaseModel):
    """写作响应"""
    generated_text: str = Field(..., description="生成的文本")
    usage: Dict[str, Any] = Field(..., description="Token 使用统计")
    quota_remaining: int = Field(..., description="剩余配额")
    model: str = Field(..., description="使用的模型")

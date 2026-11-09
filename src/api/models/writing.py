"""
写作相关数据模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class WritingContext(BaseModel):
    """写作上下文"""
    genre: Optional[str] = Field(None, description="作品类型")
    characters: List[str] = Field(default_factory=list, description="角色列表")
    timeline: Optional[str] = Field(None, description="时间线信息")
    plot_summary: Optional[str] = Field(None, description="情节摘要")


class ContinueWritingRequest(BaseModel):
    """续写请求"""
    project_id: str = Field(..., description="项目ID")
    current_text: str = Field(..., description="当前文本")
    continue_length: int = Field(default=100, ge=1, description="续写长度")
    context: Optional[WritingContext] = Field(None, description="写作上下文")
    model: str = Field(default="gpt-4", description="模型名称")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0, description="温度参数")


class PolishRequest(BaseModel):
    """润色请求"""
    text: str = Field(..., description="待润色文本")
    style: Optional[str] = Field(None, description="目标风格")
    focus_areas: List[str] = Field(
        default_factory=list,
        description="重点关注领域: grammar, vocabulary, flow, tone"
    )
    model: str = Field(default="gpt-4", description="模型名称")


class ExpandRequest(BaseModel):
    """扩展请求"""
    text: str = Field(..., description="待扩展文本")
    expand_ratio: float = Field(default=1.5, ge=1.0, le=3.0, description="扩展比例")
    direction: Optional[str] = Field(None, description="扩展方向")
    model: str = Field(default="gpt-4", description="模型名称")


class WritingResponse(BaseModel):
    """写作响应"""
    generated_text: str = Field(..., description="生成的文本")
    usage: Dict[str, int] = Field(..., description="Token使用统计")
    quota_remaining: int = Field(..., description="剩余配额")
    model: str = Field(..., description="使用的模型")

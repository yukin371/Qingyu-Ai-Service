"""
事实提取数据模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class StateChange(BaseModel):
    """状态变更"""
    entity_name: str = Field(..., description="实体名称")
    field_key: str = Field(..., description="状态字段key")
    old_value: Optional[Any] = Field(None, description="旧值")
    new_value: Any = Field(..., description="新值")
    evidence: str = Field(..., description="原文证据")


class RelationChange(BaseModel):
    """关系变更"""
    from_entity: str = Field(..., description="源实体")
    to_entity: str = Field(..., description="目标实体")
    relation_type: str = Field(..., description="关系类型")
    change_type: str = Field(..., description="变更类型: new/removed/changed")
    evidence: str = Field(..., description="原文证据")


class NewEntityMention(BaseModel):
    """新实体出场"""
    name: str = Field(..., description="实体名称")
    entity_type: str = Field(..., description="实体类型: character/item/location/organization")
    first_mention: str = Field(..., description="首次提及的原文")
    description: Optional[str] = Field(None, description="描述")


class EventFact(BaseModel):
    """事件事实"""
    description: str = Field(..., description="事件描述")
    chapter_position: Optional[str] = Field(None, description="章节位置")
    involved_entities: List[str] = Field(default_factory=list, description="涉及的实体")
    evidence: str = Field(..., description="原文证据")


class ExtractionResult(BaseModel):
    """事实提取结果"""
    state_changes: List[StateChange] = Field(default_factory=list, description="状态变更")
    relation_changes: List[RelationChange] = Field(default_factory=list, description="关系变更")
    new_entities: List[NewEntityMention] = Field(default_factory=list, description="新实体出场")
    events: List[EventFact] = Field(default_factory=list, description="事件事实")


class AnalyzeChapterRequest(BaseModel):
    """章节分析请求"""
    project_id: str = Field(..., description="项目ID")
    chapter_id: str = Field(..., description="章节ID")
    text: str = Field(..., description="章节正文")
    existing_entities: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="当前已知实体列表"
    )
    model: str = Field(default="gemini", description="模型名称")


class AnalyzeChapterResponse(BaseModel):
    """章节分析响应"""
    state_changes: List[StateChange] = Field(..., description="状态变更")
    relation_changes: List[RelationChange] = Field(..., description="关系变更")
    new_entities: List[NewEntityMention] = Field(..., description="新实体出场")
    events: List[EventFact] = Field(..., description="事件事实")
    usage: Dict[str, int] = Field(default_factory=dict, description="Token使用统计")


class ExtractFactsRequest(BaseModel):
    """提取事实请求"""
    text: str = Field(..., description="待分析文本")
    entity_type: Optional[str] = Field(None, description="实体类型筛选")
    entity_id: Optional[str] = Field(None, description="实体ID筛选")


class ExtractFactsResponse(BaseModel):
    """提取事实响应"""
    facts: List[Dict[str, Any]] = Field(..., description="提取的事实列表")
    usage: Dict[str, int] = Field(default_factory=dict, description="Token使用统计")


class ChangeRequestPayload(BaseModel):
    """Change Request 载荷（用于写入后端）"""
    project_id: str = Field(..., description="项目ID")
    chapter_id: str = Field(..., description="章节ID")
    category: str = Field(..., description="CR类别")
    entity_id: Optional[str] = Field(None, description="关联实体ID")
    entity_name: Optional[str] = Field(None, description="关联实体名称")
    title: str = Field(..., description="CR标题")
    description: str = Field(..., description="CR描述")
    suggested_change: Dict[str, Any] = Field(..., description="建议变更内容")
    evidence: List[str] = Field(default_factory=list, description="证据列表")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="置信度")

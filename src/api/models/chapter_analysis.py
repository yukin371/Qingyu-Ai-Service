"""
章节分析与变更检测数据模型
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.agents.review.diagnostic_report import IssueCategory, IssueSeverity


class PreviousChapterSummary(BaseModel):
    """前序章节摘要"""

    chapter_id: str = Field(..., description="章节ID")
    title: Optional[str] = Field(None, description="章节标题")
    summary: str = Field(..., description="章节摘要")
    key_events: List[str] = Field(default_factory=list, description="关键事件")
    time_markers: List[str] = Field(default_factory=list, description="时间标记")


class ConsistencyIssue(BaseModel):
    """章节一致性问题"""

    id: str = Field(..., description="问题ID")
    severity: IssueSeverity = Field(
        default=IssueSeverity.MEDIUM, description="问题严重程度"
    )
    category: IssueCategory = Field(
        default=IssueCategory.CONSISTENCY, description="问题类别"
    )
    issue_type: str = Field(..., description="问题类型")
    title: str = Field(..., description="问题标题")
    description: str = Field(..., description="问题说明")
    evidence: Optional[str] = Field(None, description="原文证据")
    suggestion: Optional[str] = Field(None, description="修正建议")
    affected_entities: List[str] = Field(default_factory=list, description="受影响实体")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")


class ConsistencyCheckRequest(BaseModel):
    """章节一致性检查请求"""

    project_id: str = Field(..., description="项目ID")
    chapter_id: str = Field(..., description="章节ID")
    text: str = Field(..., description="当前章节正文")
    previous_chapters: List[PreviousChapterSummary] = Field(
        default_factory=list, description="前序章节摘要"
    )
    existing_entities: List[Dict[str, Any]] = Field(
        default_factory=list, description="当前已知实体与状态"
    )


class ConsistencyCheckResponse(BaseModel):
    """章节一致性检查响应"""

    passed: bool = Field(..., description="是否通过检查")
    issues: List[ConsistencyIssue] = Field(default_factory=list, description="问题列表")
    summary: str = Field(default="", description="结果摘要")
    usage: Dict[str, int] = Field(default_factory=dict, description="Token 使用统计")


class TextChange(BaseModel):
    """文本变更片段"""

    change_type: str = Field(..., description="added/removed/modified")
    summary: str = Field(..., description="变更摘要")
    before_text: Optional[str] = Field(None, description="变更前文本")
    after_text: Optional[str] = Field(None, description="变更后文本")
    entity_mentions_added: List[str] = Field(
        default_factory=list, description="新增实体提及"
    )
    entity_mentions_removed: List[str] = Field(
        default_factory=list, description="删除实体提及"
    )


class ChangeDetectionRequest(BaseModel):
    """章节文本变更检测请求"""

    project_id: str = Field(..., description="项目ID")
    chapter_id: str = Field(..., description="章节ID")
    previous_text: str = Field(..., description="旧版本正文")
    current_text: str = Field(..., description="新版本正文")
    tracked_entities: List[str] = Field(
        default_factory=list, description="要跟踪的实体名称"
    )


class ChangeDetectionResponse(BaseModel):
    """章节文本变更检测响应"""

    changes: List[TextChange] = Field(default_factory=list, description="变更详情")
    paragraphs_added: int = Field(default=0, description="新增段落数")
    paragraphs_removed: int = Field(default=0, description="删除段落数")
    paragraphs_modified: int = Field(default=0, description="修改段落数")
    entity_mentions_added: List[str] = Field(
        default_factory=list, description="新增实体提及"
    )
    entity_mentions_removed: List[str] = Field(
        default_factory=list, description="删除实体提及"
    )

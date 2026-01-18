"""
诊断报告数据结构
"""
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class IssueSeverity(str, Enum):
    """问题严重程度"""

    CRITICAL = "critical"  # 严重 - 必须修复
    HIGH = "high"  # 高 - 应该修复
    MEDIUM = "medium"  # 中 - 建议修复
    LOW = "low"  # 低 - 可选修复


class IssueCategory(str, Enum):
    """问题类别"""

    CONSISTENCY = "consistency"  # 一致性问题
    COMPLETENESS = "completeness"  # 完整性问题
    RATIONALITY = "rationality"  # 合理性问题
    QUALITY = "quality"  # 质量问题


class CorrectionStrategy(str, Enum):
    """修正策略"""

    REGENERATE = "regenerate"  # 全量重新生成
    INCREMENTAL_FIX = "incremental_fix"  # 增量修复
    HUMAN_REVIEW = "human_review"  # 人工审核
    NONE = "none"  # 无需修正


class DiagnosticIssue(BaseModel):
    """诊断问题

    描述发现的具体问题，包含根因分析和修正建议
    """

    # 基本信息
    id: str = Field(..., description="问题ID（唯一标识符）")
    severity: IssueSeverity = Field(..., description="严重程度")
    category: IssueCategory = Field(..., description="问题类别")
    sub_category: str = Field(..., description="子类别（character, outline, plot等）")

    # 问题描述
    title: str = Field(..., description="问题标题（简短）")
    description: str = Field(..., description="问题详细描述")
    root_cause: str = Field(..., description="根本原因分析")

    # 影响范围
    affected_entities: List[str] = Field(
        default_factory=list, description="受影响的实体（章节、角色、情节等）"
    )
    impact: str = Field(..., description="影响说明")

    # 定位信息
    location: Optional[Dict[str, Any]] = Field(
        None, description="问题位置（章节ID、行号等）"
    )

    # 扩展信息
    evidence: Optional[str] = Field(None, description="问题证据（引用原文等）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")

    def __str__(self) -> str:
        return f"Issue<{self.id}: {self.title} ({self.severity})>"


class CorrectionInstruction(BaseModel):
    """修正指令

    为特定Agent提供具体的修正指令
    """

    # 关联问题
    issue_id: str = Field(..., description="关联的问题ID")

    # 目标Agent
    target_agent: str = Field(..., description="目标Agent名称")
    action: str = Field(..., description="操作类型（create, update, delete等）")

    # 具体指令
    specific_instruction: str = Field(..., description="具体修正指令（自然语言）")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="结构化参数"
    )

    # 优先级和依赖
    priority: int = Field(default=5, description="优先级（1-10）")
    dependencies: List[str] = Field(
        default_factory=list, description="依赖的其他指令ID"
    )

    def __str__(self) -> str:
        return f"Instruction<{self.target_agent}: {self.action}>"


class DiagnosticReport(BaseModel):
    """诊断报告

    审核Agent生成的结构化诊断报告，包含深度分析和修正建议
    """

    # 审核结果
    passed: bool = Field(..., description="是否通过审核")
    quality_score: int = Field(..., ge=0, le=100, description="质量分数（0-100）")

    # 问题列表
    issues: List[DiagnosticIssue] = Field(
        default_factory=list, description="发现的问题列表"
    )

    # 修正策略
    correction_strategy: CorrectionStrategy = Field(
        ..., description="整体修正策略"
    )
    correction_instructions: List[CorrectionInstruction] = Field(
        default_factory=list, description="具体修正指令"
    )

    # 受影响的Agent
    affected_agents: List[str] = Field(
        default_factory=list, description="需要修正的Agent列表"
    )

    # 推理链
    reasoning_chain: List[str] = Field(
        default_factory=list, description="推理过程（可追溯）"
    )

    # 改进建议
    suggestions_for_improvement: List[str] = Field(
        default_factory=list, description="改进建议"
    )

    # 统计信息
    total_issues_count: int = Field(default=0, description="问题总数")
    critical_issues_count: int = Field(default=0, description="严重问题数")
    high_issues_count: int = Field(default=0, description="高优先级问题数")

    # 元数据
    review_timestamp: Optional[str] = Field(None, description="审核时间戳")
    reviewer_version: str = Field(default="v2.0", description="审核器版本")
    execution_time: Optional[float] = Field(None, description="执行时间（秒）")

    def __init__(self, **data):
        super().__init__(**data)
        # 自动计算统计信息
        self.total_issues_count = len(self.issues)
        self.critical_issues_count = sum(
            1 for issue in self.issues if issue.severity == IssueSeverity.CRITICAL
        )
        self.high_issues_count = sum(
            1 for issue in self.issues if issue.severity == IssueSeverity.HIGH
        )

    def get_issues_by_severity(self, severity: IssueSeverity) -> List[DiagnosticIssue]:
        """获取指定严重程度的问题"""
        return [issue for issue in self.issues if issue.severity == severity]

    def get_issues_by_category(self, category: IssueCategory) -> List[DiagnosticIssue]:
        """获取指定类别的问题"""
        return [issue for issue in self.issues if issue.category == category]

    def get_critical_issues(self) -> List[DiagnosticIssue]:
        """获取严重问题"""
        return self.get_issues_by_severity(IssueSeverity.CRITICAL)

    def has_critical_issues(self) -> bool:
        """是否有严重问题"""
        return self.critical_issues_count > 0

    def summary(self) -> str:
        """生成诊断报告摘要"""
        return (
            f"DiagnosticReport<"
            f"passed={self.passed}, "
            f"score={self.quality_score}, "
            f"issues={self.total_issues_count} "
            f"(critical={self.critical_issues_count}, high={self.high_issues_count}), "
            f"strategy={self.correction_strategy}"
            f">"
        )

    def __str__(self) -> str:
        return self.summary()


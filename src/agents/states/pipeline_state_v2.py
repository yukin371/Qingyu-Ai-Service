"""
Pipeline State v2.0 - 支持反思循环的状态管理

相比v1.0的改进：
1. 支持反思循环（Reflection Loop）
2. 支持诊断报告（Diagnostic Report）
3. 支持元调度器（Meta-Scheduler）
4. 支持工作区上下文（Workspace Context）
5. 更完善的迭代控制
"""

import operator
from typing import Annotated, Any, Dict, List, Optional, Sequence
from dataclasses import dataclass, field, asdict
from enum import Enum

from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


class ExecutionStatus(str, Enum):
    """执行状态"""
    PLANNING = "planning"  # 规划中
    EXECUTING = "executing"  # 执行中
    REVIEWING = "reviewing"  # 审核中
    CORRECTING = "correcting"  # 修正中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


class CorrectionStrategy(str, Enum):
    """修正策略"""
    REGENERATE = "regenerate"  # 全量重新生成
    INCREMENTAL_FIX = "incremental_fix"  # 增量修复
    MANUAL_INTERVENTION = "manual_intervention"  # 人工介入


@dataclass
class DiagnosticIssue:
    """诊断问题"""
    id: str
    severity: str  # high, medium, low
    category: str  # character, plot, outline, consistency, quality
    root_cause: str  # 问题根因
    affected_entities: List[str]  # 受影响的实体（角色、章节等）
    correction_instruction: str  # 具体修正指令


@dataclass
class DiagnosticReport:
    """诊断报告（结构化）"""
    passed: bool
    quality_score: int  # 0-100
    issues: List[DiagnosticIssue] = field(default_factory=list)
    correction_strategy: CorrectionStrategy = CorrectionStrategy.REGENERATE
    affected_agents: List[str] = field(default_factory=list)  # 需要重新执行的Agent
    reasoning_chain: List[str] = field(default_factory=list)  # 推理链
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DiagnosticReport':
        """从字典创建"""
        issues = [
            DiagnosticIssue(**issue) if isinstance(issue, dict) else issue
            for issue in data.get('issues', [])
        ]
        return cls(
            passed=data['passed'],
            quality_score=data['quality_score'],
            issues=issues,
            correction_strategy=CorrectionStrategy(data.get('correction_strategy', 'regenerate')),
            affected_agents=data.get('affected_agents', []),
            reasoning_chain=data.get('reasoning_chain', [])
        )


@dataclass
class ExecutionPlan:
    """执行计划"""
    agent_sequence: List[str]  # Agent执行序列
    tools_config: Dict[str, List[str]]  # 每个Agent的工具配置
    dependencies: Dict[str, List[str]]  # Agent间依赖关系
    estimated_tokens: int = 0  # Token估算


@dataclass
class WorkspaceContext:
    """工作区上下文（来自WorkspaceContextTool）"""
    task_type: str
    project_info: Dict[str, Any]
    characters: List[Dict[str, Any]] = field(default_factory=list)
    outline_nodes: List[Dict[str, Any]] = field(default_factory=list)
    previous_content: Optional[str] = None
    retrieved_docs: List[Dict[str, Any]] = field(default_factory=list)
    context_quality_score: float = 0.0  # 上下文质量评分
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class PipelineStateV2(TypedDict, total=False):
    """
    Pipeline State v2.0 - 支持反思循环的状态管理
    
    这是v2.0架构的核心状态管理器，支持：
    - 反思循环（Reflection Loop）
    - 动态规划（Dynamic Planning）
    - 智能修正（Intelligent Correction）
    - 上下文感知（Context Awareness）
    """
    
    # ===== 基础信息 =====
    execution_id: str  # 执行ID
    task: str  # 任务描述
    user_id: str  # 用户ID
    project_id: str  # 项目ID
    
    # ===== 执行状态 =====
    status: str  # ExecutionStatus
    current_step: str  # 当前步骤
    current_agent: str  # 当前执行的Agent
    
    # ===== 规划与调度 =====
    execution_plan: Optional[Dict[str, Any]]  # 执行计划（ExecutionPlan.to_dict()）
    current_plan_index: int  # 当前执行到的计划索引
    
    # ===== 工作区上下文（v2.0新增）=====
    workspace_context: Optional[Dict[str, Any]]  # 工作区上下文（WorkspaceContext.to_dict()）
    
    # ===== 消息和推理 =====
    messages: Annotated[Sequence[BaseMessage], operator.add]  # 消息历史
    reasoning: Annotated[List[str], operator.add]  # 推理步骤
    
    # ===== Agent输出 =====
    agent_outputs: Dict[str, Any]  # 各Agent的输出 {"outline_agent": {...}, "character_agent": {...}}
    
    # 专门字段（向后兼容）
    outline_nodes: List[Dict[str, Any]]  # 大纲节点
    characters: List[Dict[str, Any]]  # 角色信息
    timeline_events: List[Dict[str, Any]]  # 时间线事件
    generated_content: str  # 生成的内容
    
    # ===== 审核和诊断（v2.0增强）=====
    review_result: Optional[Dict[str, Any]]  # 审核结果
    diagnostic_report: Optional[Dict[str, Any]]  # 诊断报告（DiagnosticReport.to_dict()）
    review_passed: bool  # 审核是否通过
    
    # ===== 反思循环（v2.0核心）=====
    reflection_count: int  # 反思次数
    max_reflections: int  # 最大反思次数
    correction_history: Annotated[List[Dict[str, Any]], operator.add]  # 修正历史
    
    # ===== 工具调用 =====
    tool_calls: Annotated[List[Dict[str, Any]], operator.add]  # 工具调用记录
    tools_to_use: List[str]  # 待使用的工具
    
    # ===== RAG检索 =====
    rag_results: List[Dict[str, Any]]  # RAG检索结果
    retrieved_context: str  # 检索到的上下文
    
    # ===== 最终输出 =====
    final_output: str  # 最终输出
    output_metadata: Dict[str, Any]  # 输出元数据
    
    # ===== 错误处理 =====
    errors: Annotated[List[str], operator.add]  # 错误列表
    warnings: Annotated[List[str], operator.add]  # 警告列表
    
    # ===== 性能指标 =====
    start_time: float  # 开始时间
    tokens_used: int  # Token使用量
    agent_execution_times: Dict[str, float]  # 各Agent执行时间


def create_initial_pipeline_state_v2(
    task: str,
    user_id: str,
    project_id: str,
    execution_id: Optional[str] = None,
    max_reflections: int = 3,
    workspace_context: Optional[WorkspaceContext] = None
) -> PipelineStateV2:
    """
    创建初始Pipeline State v2.0
    
    Args:
        task: 任务描述
        user_id: 用户ID
        project_id: 项目ID
        execution_id: 执行ID（可选）
        max_reflections: 最大反思次数
        workspace_context: 工作区上下文（可选）
    
    Returns:
        初始状态
    """
    import time
    import uuid
    
    return PipelineStateV2(
        # 基础信息
        execution_id=execution_id or str(uuid.uuid4()),
        task=task,
        user_id=user_id,
        project_id=project_id,
        
        # 执行状态
        status=ExecutionStatus.PLANNING.value,
        current_step="planning",
        current_agent="",
        
        # 规划与调度
        execution_plan=None,
        current_plan_index=0,
        
        # 工作区上下文
        workspace_context=workspace_context.to_dict() if workspace_context else None,
        
        # 消息和推理
        messages=[],
        reasoning=[],
        
        # Agent输出
        agent_outputs={},
        outline_nodes=[],
        characters=[],
        timeline_events=[],
        generated_content="",
        
        # 审核和诊断
        review_result=None,
        diagnostic_report=None,
        review_passed=False,
        
        # 反思循环
        reflection_count=0,
        max_reflections=max_reflections,
        correction_history=[],
        
        # 工具调用
        tool_calls=[],
        tools_to_use=[],
        
        # RAG检索
        rag_results=[],
        retrieved_context="",
        
        # 最终输出
        final_output="",
        output_metadata={},
        
        # 错误处理
        errors=[],
        warnings=[],
        
        # 性能指标
        start_time=time.time(),
        tokens_used=0,
        agent_execution_times={}
    )


# ===== 辅助函数 =====

def update_agent_output(
    state: PipelineStateV2,
    agent_name: str,
    output: Dict[str, Any]
) -> Dict:
    """
    更新Agent输出
    
    Args:
        state: 当前状态
        agent_name: Agent名称
        output: 输出数据
    
    Returns:
        状态更新
    """
    agent_outputs = state.get("agent_outputs", {}).copy()
    agent_outputs[agent_name] = output
    
    return {
        "agent_outputs": agent_outputs,
        "current_agent": agent_name
    }


def add_diagnostic_report(
    state: PipelineStateV2,
    report: DiagnosticReport
) -> Dict:
    """
    添加诊断报告
    
    Args:
        state: 当前状态
        report: 诊断报告
    
    Returns:
        状态更新
    """
    return {
        "diagnostic_report": report.to_dict(),
        "review_passed": report.passed,
        "status": ExecutionStatus.REVIEWING.value if not report.passed else ExecutionStatus.COMPLETED.value
    }


def add_correction_record(
    state: PipelineStateV2,
    agent_name: str,
    strategy: CorrectionStrategy,
    instructions: List[str]
) -> Dict:
    """
    添加修正记录
    
    Args:
        state: 当前状态
        agent_name: 被修正的Agent
        strategy: 修正策略
        instructions: 修正指令
    
    Returns:
        状态更新
    """
    import time
    
    correction_record = {
        "timestamp": time.time(),
        "agent": agent_name,
        "strategy": strategy.value,
        "instructions": instructions,
        "reflection_count": state.get("reflection_count", 0)
    }
    
    return {
        "correction_history": [correction_record],  # operator.add会自动累加
        "reflection_count": state.get("reflection_count", 0) + 1,
        "status": ExecutionStatus.CORRECTING.value
    }


def increment_reflection_count(state: PipelineStateV2) -> Dict:
    """
    增加反思计数
    
    Args:
        state: 当前状态
    
    Returns:
        状态更新
    """
    new_count = state.get("reflection_count", 0) + 1
    max_count = state.get("max_reflections", 3)
    
    return {
        "reflection_count": new_count,
        "warnings": [f"Reflection count: {new_count}/{max_count}"] if new_count >= max_count else []
    }


def should_continue_reflection(state: PipelineStateV2) -> bool:
    """
    判断是否继续反思循环
    
    Args:
        state: 当前状态
    
    Returns:
        是否继续
    """
    reflection_count = state.get("reflection_count", 0)
    max_reflections = state.get("max_reflections", 3)
    review_passed = state.get("review_passed", False)
    
    # 通过审核或达到最大次数则停止
    return not review_passed and reflection_count < max_reflections


def get_execution_summary(state: PipelineStateV2) -> Dict[str, Any]:
    """
    获取执行摘要
    
    Args:
        state: 当前状态
    
    Returns:
        执行摘要
    """
    import time
    
    duration = time.time() - state.get("start_time", time.time())
    
    return {
        "execution_id": state.get("execution_id"),
        "status": state.get("status"),
        "duration_seconds": round(duration, 2),
        "reflection_count": state.get("reflection_count", 0),
        "review_passed": state.get("review_passed", False),
        "tokens_used": state.get("tokens_used", 0),
        "agents_executed": list(state.get("agent_outputs", {}).keys()),
        "tool_calls_count": len(state.get("tool_calls", [])),
        "error_count": len(state.get("errors", [])),
        "warning_count": len(state.get("warnings", []))
    }


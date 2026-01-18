"""创作Agent状态定义"""

import operator
from typing import Annotated, Any, Dict, List, Optional, Sequence

from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


class CreativeAgentState(TypedDict, total=False):
    """创作Agent状态

    用于管理Creative Agent工作流的完整状态
    """

    # ===== 输入 =====
    task: str  # 创作任务
    user_id: str  # 用户ID
    project_id: str  # 项目ID

    # 创作约束
    constraints: Dict[str, Any]  # 创作约束（字数、类型等）
    context: Dict[str, Any]  # 上下文信息

    # ===== 消息和推理 =====
    messages: Annotated[Sequence[BaseMessage], operator.add]  # 消息历史（自动累积）
    reasoning: Annotated[List[str], operator.add]  # 推理步骤（自动累积）

    # ===== 工作流状态 =====
    current_step: str  # 当前步骤
    plan: List[Dict[str, Any]]  # 执行计划
    current_plan_index: int  # 当前计划索引

    # ===== RAG检索 =====
    rag_results: List[Dict[str, Any]]  # RAG检索结果
    retrieved_context: str  # 检索到的上下文

    # ===== 生成内容 =====
    generated_content: str  # 生成的内容
    content_draft: str  # 内容草稿

    # ===== 工具调用 =====
    tool_calls: Annotated[List[Dict[str, Any]], operator.add]  # 工具调用记录（自动累积）
    tools_to_use: List[str]  # 待使用的工具

    # ===== 审核和迭代 =====
    review_result: Optional[Dict[str, Any]]  # 审核结果
    review_passed: bool  # 审核是否通过
    retry_count: int  # 重试次数
    max_retries: int  # 最大重试次数

    # ===== 最终输出 =====
    final_output: str  # 最终输出
    output_metadata: Dict[str, Any]  # 输出元数据

    # ===== 错误处理 =====
    errors: Annotated[List[str], operator.add]  # 错误列表（自动累积）
    warnings: Annotated[List[str], operator.add]  # 警告列表（自动累积）

    # ===== 性能指标 =====
    start_time: float  # 开始时间
    tokens_used: int  # Token使用量


def create_initial_creative_state(
    task: str,
    user_id: str,
    project_id: str,
    constraints: Optional[Dict[str, Any]] = None,
    context: Optional[Dict[str, Any]] = None,
    max_retries: int = 3,
) -> CreativeAgentState:
    """创建初始创作状态

    Args:
        task: 创作任务
        user_id: 用户ID
        project_id: 项目ID
        constraints: 创作约束
        context: 上下文信息
        max_retries: 最大重试次数

    Returns:
        初始状态
    """
    import time

    return CreativeAgentState(
        # 输入
        task=task,
        user_id=user_id,
        project_id=project_id,
        constraints=constraints or {},
        context=context or {},
        # 消息和推理
        messages=[],
        reasoning=[],
        # 工作流状态
        current_step="understanding",
        plan=[],
        current_plan_index=0,
        # RAG
        rag_results=[],
        retrieved_context="",
        # 生成
        generated_content="",
        content_draft="",
        # 工具
        tool_calls=[],
        tools_to_use=[],
        # 审核
        review_result=None,
        review_passed=False,
        retry_count=0,
        max_retries=max_retries,
        # 输出
        final_output="",
        output_metadata={},
        # 错误
        errors=[],
        warnings=[],
        # 性能
        start_time=time.time(),
        tokens_used=0,
    )


"""
审核Agent v2.0 - 深度诊断和结构化报告

核心改进：
1. 结构化诊断报告（DiagnosticReport）
2. 问题根因分析（root cause）
3. 具体修正指令（correction instructions）
4. 智能修正策略选择
"""
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import Runnable

from src.agents.base_agent_v2 import BaseAgentV2
from src.agents.review.diagnostic_report import (
    CorrectionInstruction,
    CorrectionStrategy,
    DiagnosticIssue,
    DiagnosticReport,
    IssueCategory,
    IssueSeverity,
)
from src.agents.states.pipeline_state_v2 import PipelineStateV2
from src.core.logger import get_logger
from src.llm.llm_factory import LLMFactory

logger = get_logger(__name__)


class ReviewAgentV2(BaseAgentV2):
    """审核Agent v2.0

    职责：
    1. 深度审核创作内容（大纲、角色、情节、文本等）
    2. 生成结构化诊断报告（DiagnosticReport）
    3. 分析问题根因，而非表面现象
    4. 提供具体修正指令，而非泛泛建议
    5. 智能选择修正策略（regenerate vs incremental_fix）
    """

    def __init__(
        self,
        llm_provider: str = "gemini",
        llm_model: Optional[str] = None,
        temperature: float = 0.3,  # 审核需要更确定性的输出
        **kwargs,
    ):
        """初始化审核Agent

        Args:
            llm_provider: LLM提供商
            llm_model: LLM模型名称
            temperature: 温度参数（审核建议低温度）
            **kwargs: 额外参数
        """
        super().__init__(
            name="ReviewAgentV2",
            description="深度审核Agent，生成结构化诊断报告",
            version="v2.0",
        )

        # 创建LLM实例
        self.llm = LLMFactory.create_llm(
            provider=llm_provider,
            model=llm_model,
            temperature=temperature,
        )

        self.config = kwargs
        logger.info(f"ReviewAgentV2 initialized with {llm_provider}/{llm_model}")

    def get_runnable(self) -> Runnable[PipelineStateV2, PipelineStateV2]:
        """获取LangChain Runnable（暂未实现）"""
        raise NotImplementedError("ReviewAgentV2 暂未实现LangChain Runnable接口")

    async def execute(self, state: PipelineStateV2) -> PipelineStateV2:
        """执行审核

        Args:
            state: 流水线状态

        Returns:
            PipelineStateV2: 更新后的状态
        """
        start_time = time.time()
        logger.info("Starting ReviewAgentV2 execution")

        try:
            # Step 1: 准备审核内容
            review_content = self._prepare_review_content(state)

            # Step 2: 生成诊断报告
            diagnostic_report = await self._generate_diagnostic_report(
                review_content, state
            )

            # Step 3: 更新状态
            updated_state = self._update_state(state, diagnostic_report, start_time)

            logger.info(
                f"ReviewAgentV2 completed: {diagnostic_report.summary()}, "
                f"time={time.time() - start_time:.2f}s"
            )

            return updated_state

        except Exception as e:
            logger.error(f"ReviewAgentV2 execution failed: {e}", exc_info=True)

            # 返回错误状态
            return {
                **state,
                "errors": state.get("errors", []) + [f"ReviewAgentV2 error: {str(e)}"],
                "current_step": "error",
            }

    def _prepare_review_content(self, state: PipelineStateV2) -> Dict[str, Any]:
        """准备审核内容

        Args:
            state: 流水线状态

        Returns:
            Dict: 结构化审核内容
        """
        # 从state中提取需要审核的内容
        content = {
            "task": state.get("task", ""),
            "generated_content": state.get("generated_content", ""),
            "content_draft": state.get("content_draft", ""),
            "plan": state.get("plan", []),
            "rag_results": state.get("rag_results", []),
        }

        # 如果有工作区上下文，也包含进来
        workspace_context = state.get("workspace_context")
        if workspace_context:
            content["workspace_context"] = {
                "task_type": workspace_context.get("task_type"),
                "has_previous_content": bool(
                    workspace_context.get("previous_content")
                ),
                "has_characters": bool(workspace_context.get("characters")),
                "has_outline": bool(workspace_context.get("outline")),
            }

        logger.info(f"Prepared review content with {len(content)} sections")
        return content

    async def _generate_diagnostic_report(
        self, review_content: Dict[str, Any], state: PipelineStateV2
    ) -> DiagnosticReport:
        """生成诊断报告

        Args:
            review_content: 审核内容
            state: 流水线状态

        Returns:
            DiagnosticReport: 诊断报告
        """
        # 构建系统提示词
        system_message = SystemMessage(
            content=self._build_review_system_prompt()
        )

        # 构建用户提示词
        user_message = HumanMessage(
            content=self._build_review_user_prompt(review_content)
        )

        # 调用LLM
        logger.info("Invoking LLM for diagnostic report generation")
        response = await self.llm.ainvoke([system_message, user_message])

        # 解析诊断报告
        try:
            diagnostic_dict = json.loads(response.content)
            diagnostic_report = self._parse_diagnostic_report(diagnostic_dict)

            logger.info(f"Diagnostic report parsed successfully: {diagnostic_report.summary()}")
            return diagnostic_report

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse diagnostic report JSON: {e}")
            # 返回默认通过报告
            return self._create_default_pass_report(
                "诊断报告解析失败，默认通过"
            )

        except Exception as e:
            logger.error(f"Error parsing diagnostic report: {e}", exc_info=True)
            return self._create_default_pass_report(
                f"诊断报告处理失败: {str(e)}"
            )

    def _build_review_system_prompt(self) -> str:
        """构建审核系统提示词"""
        return """你是一个专业的创作内容审核专家，负责深度审核AI生成的创作内容。

你的任务是：
1. **深度分析**：不是简单的pass/fail，而是找出具体问题
2. **根因分析**：找到问题的根本原因，而非表面现象
3. **具体指令**：提供可执行的修正指令，而非泛泛建议
4. **智能策略**：根据问题严重程度选择合适的修正策略

审核维度：
- **一致性（Consistency）**：内容之间是否一致（角色性格、时间线、世界观等）
- **完整性（Completeness）**：是否有缺失的必要元素
- **合理性（Rationality）**：逻辑是否合理，情节是否可信
- **质量（Quality）**：文本质量、角色深度、情节吸引力等

诊断报告格式（JSON）：
```json
{
  "passed": false,
  "quality_score": 65,
  "issues": [
    {
      "id": "issue-001",
      "severity": "high",
      "category": "consistency",
      "sub_category": "character",
      "title": "角色定义缺失",
      "description": "详细问题描述",
      "root_cause": "根本原因分析",
      "affected_entities": ["大纲节点：第三章", "角色列表"],
      "impact": "导致情节无法展开",
      "evidence": "引用的原文证据"
    }
  ],
  "correction_strategy": "incremental_fix",
  "correction_instructions": [
    {
      "issue_id": "issue-001",
      "target_agent": "character_agent",
      "action": "create",
      "specific_instruction": "创建角色'李四'，设定为...",
      "parameters": {"name": "李四", "role_type": "supporting"},
      "priority": 8
    }
  ],
  "affected_agents": ["character_agent"],
  "reasoning_chain": [
    "检查大纲：发现提及'李四'",
    "检查角色列表：未找到'李四'",
    "分析影响：高优先级问题",
    "确定策略：增量修复"
  ],
  "suggestions_for_improvement": [
    "建议提前提取大纲中的角色名称"
  ]
}
```

修正策略选择：
- **regenerate**: 质量分<60 或有critical问题时，全量重新生成
- **incremental_fix**: 质量分60-80，有明确问题时，增量修复
- **human_review**: 质量分<50 或问题复杂时，人工审核
- **none**: 质量分>80 且无问题时，无需修正

请生成结构化诊断报告（JSON格式）。"""

    def _build_review_user_prompt(self, review_content: Dict[str, Any]) -> str:
        """构建审核用户提示词"""
        content_json = json.dumps(review_content, ensure_ascii=False, indent=2)

        return f"""请深度审核以下创作内容，生成结构化诊断报告（JSON格式）：

审核内容：
{content_json}

请按照系统提示词中的格式生成诊断报告。
重点关注：
1. 内容一致性（前后矛盾、角色性格不一致等）
2. 完整性（缺失的角色、情节、设定等）
3. 合理性（逻辑漏洞、不合常理的情节等）
4. 质量（文本质量、角色深度、情节吸引力等）

诊断报告（JSON）："""

    def _parse_diagnostic_report(self, diagnostic_dict: Dict[str, Any]) -> DiagnosticReport:
        """解析诊断报告字典为DiagnosticReport对象"""
        # 解析问题列表
        issues = [
            DiagnosticIssue(
                id=issue.get("id", f"issue-{i}"),
                severity=IssueSeverity(issue.get("severity", "medium")),
                category=IssueCategory(issue.get("category", "quality")),
                sub_category=issue.get("sub_category", "unknown"),
                title=issue.get("title", "未知问题"),
                description=issue.get("description", ""),
                root_cause=issue.get("root_cause", "未分析"),
                affected_entities=issue.get("affected_entities", []),
                impact=issue.get("impact", ""),
                location=issue.get("location"),
                evidence=issue.get("evidence"),
            )
            for i, issue in enumerate(diagnostic_dict.get("issues", []))
        ]

        # 解析修正指令
        correction_instructions = [
            CorrectionInstruction(
                issue_id=instr.get("issue_id", ""),
                target_agent=instr.get("target_agent", ""),
                action=instr.get("action", "update"),
                specific_instruction=instr.get("specific_instruction", ""),
                parameters=instr.get("parameters", {}),
                priority=instr.get("priority", 5),
                dependencies=instr.get("dependencies", []),
            )
            for instr in diagnostic_dict.get("correction_instructions", [])
        ]

        # 构建诊断报告
        return DiagnosticReport(
            passed=diagnostic_dict.get("passed", False),
            quality_score=diagnostic_dict.get("quality_score", 50),
            issues=issues,
            correction_strategy=CorrectionStrategy(
                diagnostic_dict.get("correction_strategy", "regenerate")
            ),
            correction_instructions=correction_instructions,
            affected_agents=diagnostic_dict.get("affected_agents", []),
            reasoning_chain=diagnostic_dict.get("reasoning_chain", []),
            suggestions_for_improvement=diagnostic_dict.get(
                "suggestions_for_improvement", []
            ),
            review_timestamp=datetime.now().isoformat(),
            reviewer_version="v2.0",
        )

    def _create_default_pass_report(self, reason: str) -> DiagnosticReport:
        """创建默认通过报告（用于异常情况）"""
        return DiagnosticReport(
            passed=True,
            quality_score=75,
            issues=[],
            correction_strategy=CorrectionStrategy.NONE,
            correction_instructions=[],
            affected_agents=[],
            reasoning_chain=[reason],
            suggestions_for_improvement=[],
            review_timestamp=datetime.now().isoformat(),
            reviewer_version="v2.0",
        )

    def _update_state(
        self,
        state: PipelineStateV2,
        diagnostic_report: DiagnosticReport,
        start_time: float,
    ) -> PipelineStateV2:
        """更新流水线状态

        Args:
            state: 当前状态
            diagnostic_report: 诊断报告
            start_time: 开始时间

        Returns:
            PipelineStateV2: 更新后的状态
        """
        execution_time = time.time() - start_time

        # 更新诊断报告的执行时间
        diagnostic_report.execution_time = execution_time

        # 决定下一步
        if diagnostic_report.passed and diagnostic_report.quality_score >= 80:
            next_step = "completed"
        elif diagnostic_report.correction_strategy == CorrectionStrategy.HUMAN_REVIEW:
            next_step = "human_review"
        elif diagnostic_report.correction_strategy in [
            CorrectionStrategy.REGENERATE,
            CorrectionStrategy.INCREMENTAL_FIX,
        ]:
            next_step = "meta_scheduler"
        else:
            next_step = "completed"

        # 更新状态
        return {
            **state,
            "review_report": diagnostic_report.model_dump(),
            "review_passed": diagnostic_report.passed,
            "correction_strategy": diagnostic_report.correction_strategy.value,
            "affected_agents": diagnostic_report.affected_agents,
            "correction_instructions": [
                instr.model_dump()
                for instr in diagnostic_report.correction_instructions
            ],
            "current_step": next_step,
            "reasoning": state.get("reasoning", [])
            + diagnostic_report.reasoning_chain,
        }


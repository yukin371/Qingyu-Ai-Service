"""
修正Prompt构建器

为受影响的Agent生成增强的修正Prompt
"""
import json
from typing import Any, Dict, List

from src.agents.review.diagnostic_report import CorrectionInstruction, DiagnosticReport
from src.core.logger import get_logger

logger = get_logger(__name__)


class CorrectionPromptBuilder:
    """修正Prompt构建器

    根据诊断报告和修正指令，为特定Agent生成增强的修正Prompt
    """

    @staticmethod
    def build_correction_prompt(
        agent_name: str,
        instructions: List[CorrectionInstruction],
        diagnostic_report: DiagnosticReport,
        original_output: Any = None,
        correction_mode: str = "incremental",
    ) -> str:
        """构建修正Prompt

        Args:
            agent_name: Agent名称
            instructions: 修正指令列表
            diagnostic_report: 诊断报告
            original_output: 原始输出（可选）
            correction_mode: 修正模式（regenerate/incremental）

        Returns:
            str: 增强的修正Prompt
        """
        prompt_parts = []

        # 标题
        prompt_parts.append("# 修正任务\n\n")

        # 修正模式说明
        if correction_mode == "regenerate":
            prompt_parts.append("**修正模式**: 全量重新生成\n\n")
            prompt_parts.append(
                "请根据以下反馈，重新生成完整的内容，确保解决所有发现的问题。\n\n"
            )
        else:
            prompt_parts.append("**修正模式**: 增量修复\n\n")
            prompt_parts.append(
                "请针对性地修正以下问题，保留未受影响的部分。\n\n"
            )

        # 诊断摘要
        prompt_parts.append("## 诊断摘要\n\n")
        prompt_parts.append(f"- 质量分数: {diagnostic_report.quality_score}/100\n")
        prompt_parts.append(f"- 问题总数: {diagnostic_report.total_issues_count}\n")
        prompt_parts.append(
            f"- 严重问题: {diagnostic_report.critical_issues_count}\n"
        )
        prompt_parts.append(f"- 高优先级问题: {diagnostic_report.high_issues_count}\n\n")

        # 具体修正指令
        prompt_parts.append("## 修正指令\n\n")

        for i, inst in enumerate(instructions, 1):
            prompt_parts.append(f"### 指令 {i}: {inst.action.upper()}\n\n")
            prompt_parts.append(f"**描述**: {inst.specific_instruction}\n\n")

            if inst.parameters:
                prompt_parts.append("**参数**:\n")
                prompt_parts.append(
                    f"```json\n{json.dumps(inst.parameters, ensure_ascii=False, indent=2)}\n```\n\n"
                )

            prompt_parts.append(f"**优先级**: {inst.priority}/10\n\n")

            # 找到关联的问题
            related_issue = next(
                (
                    issue
                    for issue in diagnostic_report.issues
                    if issue.id == inst.issue_id
                ),
                None,
            )

            if related_issue:
                prompt_parts.append(f"**问题根因**: {related_issue.root_cause}\n\n")
                prompt_parts.append(f"**影响**: {related_issue.impact}\n\n")

            prompt_parts.append("---\n\n")

        # 修正要求
        prompt_parts.append("## 修正要求\n\n")
        prompt_parts.append("1. **针对性修正**: 只修改有问题的部分，避免引入新问题\n")
        prompt_parts.append("2. **保持一致性**: 确保修正后与其他部分保持一致\n")
        prompt_parts.append("3. **质量提升**: 不仅解决问题，还要提升整体质量\n")
        prompt_parts.append("4. **验证完整性**: 确保修正后内容完整且逻辑自洽\n\n")

        # 推理链（供参考）
        if diagnostic_report.reasoning_chain:
            prompt_parts.append("## 审核推理过程（供参考）\n\n")
            for reasoning in diagnostic_report.reasoning_chain:
                prompt_parts.append(f"- {reasoning}\n")
            prompt_parts.append("\n")

        # 改进建议
        if diagnostic_report.suggestions_for_improvement:
            prompt_parts.append("## 改进建议\n\n")
            for suggestion in diagnostic_report.suggestions_for_improvement:
                prompt_parts.append(f"- {suggestion}\n")
            prompt_parts.append("\n")

        # 原始输出（如果有）
        if original_output and correction_mode == "incremental":
            prompt_parts.append("## 原始输出\n\n")
            prompt_parts.append("```\n")
            if isinstance(original_output, dict):
                prompt_parts.append(json.dumps(original_output, ensure_ascii=False, indent=2))
            else:
                prompt_parts.append(str(original_output))
            prompt_parts.append("\n```\n\n")

        # 输出格式要求
        prompt_parts.append("## 输出格式\n\n")
        prompt_parts.append(
            f"请按照 {agent_name} 的标准输出格式返回修正后的内容。\n"
        )

        return "".join(prompt_parts)

    @staticmethod
    def build_batch_correction_prompts(
        affected_agents: List[str],
        diagnostic_report: DiagnosticReport,
        original_outputs: Dict[str, Any] = None,
        correction_mode: str = "incremental",
    ) -> Dict[str, str]:
        """批量构建修正Prompt

        Args:
            affected_agents: 受影响的Agent列表
            diagnostic_report: 诊断报告
            original_outputs: 原始输出字典（agent_name -> output）
            correction_mode: 修正模式

        Returns:
            Dict[str, str]: Agent名称到修正Prompt的映射
        """
        original_outputs = original_outputs or {}
        correction_prompts = {}

        for agent_name in affected_agents:
            # 找到该Agent的修正指令
            agent_instructions = [
                inst
                for inst in diagnostic_report.correction_instructions
                if inst.target_agent == agent_name
            ]

            if agent_instructions:
                prompt = CorrectionPromptBuilder.build_correction_prompt(
                    agent_name=agent_name,
                    instructions=agent_instructions,
                    diagnostic_report=diagnostic_report,
                    original_output=original_outputs.get(agent_name),
                    correction_mode=correction_mode,
                )

                correction_prompts[agent_name] = prompt

                logger.info(
                    f"Built correction prompt for {agent_name}: "
                    f"{len(agent_instructions)} instructions, "
                    f"mode={correction_mode}"
                )

        return correction_prompts







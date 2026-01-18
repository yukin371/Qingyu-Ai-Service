"""
元调度器 - 智能分析诊断报告并生成修正计划

核心职责：
1. 解析DiagnosticReport
2. 智能定位需要修正的Agent
3. 生成增强的修正Prompt
4. 决定修正范围（全量 vs 增量）
5. 管理迭代次数和降级策略
"""
from typing import Dict, List, Optional

from langchain_core.runnables import Runnable

from src.agents.base_agent_v2 import BaseAgentV2
from src.agents.meta.correction_prompt_builder import CorrectionPromptBuilder
from src.agents.review.diagnostic_report import (
    CorrectionStrategy,
    DiagnosticReport,
    IssueCategory,
)
from src.agents.states.pipeline_state_v2 import PipelineStateV2
from src.core.logger import get_logger

logger = get_logger(__name__)


class MetaScheduler(BaseAgentV2):
    """元调度器

    分析审核Agent生成的诊断报告，智能规划修正策略：
    - 定位需要修正的Agent
    - 生成具体的修正Prompt
    - 决定修正模式（全量重生成 vs 增量修复）
    - 管理迭代次数，避免无限循环
    - 自动降级到人工审核
    """

    # Agent优先级（用于确定修正顺序）
    AGENT_PRIORITY = [
        "outline_agent",
        "character_agent",
        "plot_agent",
        "worldview_agent",
        "style_agent",
    ]

    def __init__(
        self,
        max_iterations: int = 3,
        auto_downgrade_threshold: float = 0.3,  # 质量提升低于此阈值时降级
        **kwargs,
    ):
        """初始化元调度器

        Args:
            max_iterations: 最大迭代次数
            auto_downgrade_threshold: 自动降级阈值
            **kwargs: 额外参数
        """
        super().__init__(
            name="MetaScheduler",
            description="智能分析诊断报告并生成修正计划",
            version="v1.0",
        )

        self.max_iterations = max_iterations
        self.auto_downgrade_threshold = auto_downgrade_threshold
        self.config = kwargs

        logger.info(
            f"MetaScheduler initialized: max_iterations={max_iterations}, "
            f"downgrade_threshold={auto_downgrade_threshold}"
        )

    def get_runnable(self) -> Runnable[PipelineStateV2, PipelineStateV2]:
        """获取LangChain Runnable（暂未实现）"""
        raise NotImplementedError("MetaScheduler 暂未实现LangChain Runnable接口")

    async def execute(self, state: PipelineStateV2) -> PipelineStateV2:
        """执行元调度

        Args:
            state: 流水线状态

        Returns:
            PipelineStateV2: 更新后的状态
        """
        logger.info("Starting MetaScheduler execution")

        try:
            # Step 1: 检查迭代次数
            iteration_count = state.get("iteration_count", 0)
            max_iterations = state.get("max_iterations", self.max_iterations)

            if iteration_count >= max_iterations:
                return self._handle_max_iterations_reached(state, iteration_count)

            # Step 2: 解析诊断报告
            review_report_dict = state.get("review_report")
            if not review_report_dict:
                logger.warning("No review_report found in state")
                return self._handle_no_review_report(state)

            diagnostic_report = DiagnosticReport(**review_report_dict)

            # Step 3: 检查是否需要修正
            if diagnostic_report.correction_strategy == CorrectionStrategy.NONE:
                logger.info("No correction needed, proceeding to completion")
                return {
                    **state,
                    "current_step": "completed",
                    "reasoning": state.get("reasoning", [])
                    + ["元调度器：无需修正，流程完成"],
                }

            # Step 4: 确定受影响的Agent
            affected_agents = self._determine_affected_agents(diagnostic_report)

            if not affected_agents:
                logger.warning("No affected agents determined")
                return self._handle_no_affected_agents(state)

            # Step 5: 决定修正模式
            correction_mode = self._determine_correction_mode(
                diagnostic_report, state
            )

            # Step 6: 生成修正Prompt
            correction_prompts = CorrectionPromptBuilder.build_batch_correction_prompts(
                affected_agents=affected_agents,
                diagnostic_report=diagnostic_report,
                original_outputs=self._extract_agent_outputs(state, affected_agents),
                correction_mode=correction_mode,
            )

            # Step 7: 确定重启Agent
            restart_agent = self._determine_restart_agent(affected_agents)

            # Step 8: 清理输出（如果是全量重生成）
            if correction_mode == "regenerate":
                state = self._clear_affected_outputs(state, affected_agents)

            # Step 9: 更新状态
            return {
                **state,
                "iteration_count": iteration_count + 1,
                "current_step": restart_agent,
                "correction_prompts": correction_prompts,
                "correction_mode": correction_mode,
                "affected_agents": affected_agents,
                "reasoning": state.get("reasoning", [])
                + [
                    f"元调度器：分析诊断报告（质量分数={diagnostic_report.quality_score}，问题数={diagnostic_report.total_issues_count}）",
                    f"元调度器：修正策略={diagnostic_report.correction_strategy.value}",
                    f"元调度器：受影响Agent={', '.join(affected_agents)}",
                    f"元调度器：修正模式={correction_mode}",
                    f"元调度器：从 {restart_agent} 开始修正",
                    f"元调度器：迭代次数={iteration_count + 1}/{max_iterations}",
                ],
            }

        except Exception as e:
            logger.error(f"MetaScheduler execution failed: {e}", exc_info=True)
            return {
                **state,
                "errors": state.get("errors", [])
                + [f"MetaScheduler error: {str(e)}"],
                "current_step": "error",
            }

    def _determine_affected_agents(
        self, diagnostic_report: DiagnosticReport
    ) -> List[str]:
        """确定受影响的Agent

        Args:
            diagnostic_report: 诊断报告

        Returns:
            List[str]: 受影响的Agent列表
        """
        # 首先使用诊断报告中明确指定的Agent
        affected_agents = diagnostic_report.affected_agents.copy()

        # 如果没有明确指定，使用启发式规则
        if not affected_agents:
            agents_set = set()

            for issue in diagnostic_report.issues:
                sub_category = issue.sub_category.lower()

                if "character" in sub_category:
                    agents_set.add("character_agent")
                if "outline" in sub_category:
                    agents_set.add("outline_agent")
                if "plot" in sub_category or "timeline" in sub_category:
                    agents_set.add("plot_agent")
                if "worldview" in sub_category or "setting" in sub_category:
                    agents_set.add("worldview_agent")
                if "style" in sub_category or "quality" in sub_category:
                    agents_set.add("style_agent")

            affected_agents = list(agents_set)

        # 如果还是没有，默认使用outline_agent
        if not affected_agents:
            affected_agents = ["outline_agent"]

        logger.info(f"Determined affected agents: {affected_agents}")
        return affected_agents

    def _determine_correction_mode(
        self, diagnostic_report: DiagnosticReport, state: PipelineStateV2
    ) -> str:
        """确定修正模式

        Args:
            diagnostic_report: 诊断报告
            state: 流水线状态

        Returns:
            str: 修正模式（regenerate/incremental）
        """
        # 根据修正策略决定
        if diagnostic_report.correction_strategy == CorrectionStrategy.REGENERATE:
            return "regenerate"

        # 如果有严重问题，全量重生成
        if diagnostic_report.has_critical_issues():
            logger.info("Critical issues detected, using regenerate mode")
            return "regenerate"

        # 如果质量分数很低，全量重生成
        if diagnostic_report.quality_score < 60:
            logger.info(
                f"Quality score too low ({diagnostic_report.quality_score}), "
                f"using regenerate mode"
            )
            return "regenerate"

        # 否则使用增量修复
        logger.info("Using incremental correction mode")
        return "incremental"

    def _determine_restart_agent(self, affected_agents: List[str]) -> str:
        """确定重启Agent（按优先级）

        Args:
            affected_agents: 受影响的Agent列表

        Returns:
            str: 重启Agent名称
        """
        # 按优先级顺序查找
        for agent in self.AGENT_PRIORITY:
            if agent in affected_agents:
                logger.info(f"Restart agent determined: {agent}")
                return agent

        # 如果没有找到，返回第一个
        restart_agent = affected_agents[0]
        logger.info(f"Using first affected agent as restart: {restart_agent}")
        return restart_agent

    def _extract_agent_outputs(
        self, state: PipelineStateV2, agent_names: List[str]
    ) -> Dict[str, any]:
        """提取Agent输出

        Args:
            state: 流水线状态
            agent_names: Agent名称列表

        Returns:
            Dict: Agent输出字典
        """
        outputs = {}

        for agent_name in agent_names:
            # 尝试从state中提取该Agent的输出
            output_key = f"{agent_name}_output"
            if output_key in state:
                outputs[agent_name] = state[output_key]
            # 也尝试其他可能的键名
            elif agent_name.replace("_agent", "") in state:
                outputs[agent_name] = state[agent_name.replace("_agent", "")]

        return outputs

    def _clear_affected_outputs(
        self, state: PipelineStateV2, affected_agents: List[str]
    ) -> PipelineStateV2:
        """清除受影响Agent的输出（用于全量重生成）

        Args:
            state: 流水线状态
            affected_agents: 受影响的Agent列表

        Returns:
            PipelineStateV2: 更新后的状态
        """
        new_state = state.copy()

        for agent_name in affected_agents:
            output_key = f"{agent_name}_output"
            if output_key in new_state:
                del new_state[output_key]
                logger.info(f"Cleared output for {agent_name}")

        logger.info(f"Cleared outputs for {len(affected_agents)} agents")
        return new_state

    def _handle_max_iterations_reached(
        self, state: PipelineStateV2, iteration_count: int
    ) -> PipelineStateV2:
        """处理达到最大迭代次数

        Args:
            state: 流水线状态
            iteration_count: 当前迭代次数

        Returns:
            PipelineStateV2: 更新后的状态
        """
        logger.warning(
            f"Max iterations ({self.max_iterations}) reached, "
            f"escalating to human review"
        )

        return {
            **state,
            "current_step": "human_review",
            "reasoning": state.get("reasoning", [])
            + [
                f"元调度器：达到最大迭代次数 {iteration_count}/{self.max_iterations}",
                "元调度器：自动升级到人工审核",
            ],
            "warnings": state.get("warnings", [])
            + [f"达到最大迭代次数 {iteration_count}，需要人工介入"],
        }

    def _handle_no_review_report(self, state: PipelineStateV2) -> PipelineStateV2:
        """处理没有审核报告的情况

        Args:
            state: 流水线状态

        Returns:
            PipelineStateV2: 更新后的状态
        """
        logger.warning("No review report found, proceeding to completion")

        return {
            **state,
            "current_step": "completed",
            "reasoning": state.get("reasoning", [])
            + ["元调度器：未找到审核报告，流程完成"],
            "warnings": state.get("warnings", []) + ["未找到审核报告"],
        }

    def _handle_no_affected_agents(self, state: PipelineStateV2) -> PipelineStateV2:
        """处理没有受影响Agent的情况

        Args:
            state: 流水线状态

        Returns:
            PipelineStateV2: 更新后的状态
        """
        logger.warning("No affected agents determined, proceeding to completion")

        return {
            **state,
            "current_step": "completed",
            "reasoning": state.get("reasoning", [])
            + ["元调度器：无法确定受影响的Agent，流程完成"],
            "warnings": state.get("warnings", []) + ["无法确定受影响的Agent"],
        }


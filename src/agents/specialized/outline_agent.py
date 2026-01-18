"""
OutlineAgent - 大纲生成Agent

职责：
1. 分析用户需求和创作意图
2. 设计合理的故事结构（章节、节点）
3. 确保情节连贯、冲突充足
4. 考虑角色发展和主题表达
"""
import json
import time
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable

from src.agents.base_agent_v2 import BaseAgentV2
from src.agents.states.pipeline_state_v2 import PipelineStateV2, update_agent_output
from src.core.logger import get_logger
from src.llm.llm_factory import LLMFactory

logger = get_logger(__name__)


class OutlineAgent(BaseAgentV2):
    """大纲生成Agent

    负责生成结构化的故事大纲，包括：
    - 章节结构和标题
    - 关键事件和情节点
    - 角色参与情况
    - 字数估算
    """

    def __init__(
        self,
        llm_provider: str = "gemini",
        llm_model: Optional[str] = None,
        temperature: float = 0.7,  # 大纲生成需要一定创造性
        **kwargs
    ):
        """初始化OutlineAgent

        Args:
            llm_provider: LLM提供商
            llm_model: LLM模型名称
            temperature: 温度参数
            **kwargs: 额外参数
        """
        super().__init__(
            name="OutlineAgent",
            description="专业故事大纲设计师，擅长构建完整、有吸引力的故事结构",
            version="v1.0"
        )

        # 创建LLM实例
        self.llm = LLMFactory.create_llm(
            provider=llm_provider,
            model=llm_model,
            temperature=temperature
        )

        self.config = kwargs
        logger.info(f"OutlineAgent initialized with {llm_provider}/{llm_model}")

    def get_runnable(self) -> Runnable[PipelineStateV2, PipelineStateV2]:
        """获取LangChain Runnable（暂未实现）"""
        raise NotImplementedError("OutlineAgent暂未实现LangChain Runnable接口")

    async def execute(self, state: PipelineStateV2) -> PipelineStateV2:
        """执行大纲生成

        Args:
            state: 流水线状态

        Returns:
            PipelineStateV2: 更新后的状态
        """
        start_time = time.time()
        logger.info("Starting OutlineAgent execution")

        try:
            # Step 1: 准备输入
            task = state.get("task", "")
            workspace_context = state.get("workspace_context", {})
            correction_prompts = state.get("correction_prompts", {})

            # Step 2: 生成大纲
            outline_data = await self._generate_outline(
                task=task,
                workspace_context=workspace_context,
                correction_prompt=correction_prompts.get("outline_agent", "")
            )

            # Step 3: 更新状态
            execution_time = time.time() - start_time

            updated_state = {
                **state,
                **update_agent_output(state, "outline_agent", outline_data),
                "outline_nodes": outline_data.get("chapters", []),
                "reasoning": state.get("reasoning", []) + [
                    f"OutlineAgent: 生成了{len(outline_data.get('chapters', []))}个章节",
                    f"OutlineAgent: 执行时间{execution_time:.2f}秒"
                ],
                "current_step": "character"  # 下一步：角色设计
            }

            # 更新执行时间
            agent_times = state.get("agent_execution_times", {}).copy()
            agent_times["outline_agent"] = execution_time
            updated_state["agent_execution_times"] = agent_times

            logger.info(f"OutlineAgent completed: generated {len(outline_data.get('chapters', []))} chapters")
            return updated_state

        except Exception as e:
            logger.error(f"OutlineAgent execution failed: {e}", exc_info=True)
            return {
                **state,
                "errors": state.get("errors", []) + [f"OutlineAgent error: {str(e)}"],
                "current_step": "error"
            }

    async def _generate_outline(
        self,
        task: str,
        workspace_context: Dict[str, Any],
        correction_prompt: str = ""
    ) -> Dict[str, Any]:
        """生成大纲

        Args:
            task: 创作任务
            workspace_context: 工作区上下文
            correction_prompt: 修正提示词（来自元调度器）

        Returns:
            Dict: 大纲数据
        """
        # 构建系统提示词
        system_message = SystemMessage(content=self._build_system_prompt())

        # 构建用户提示词
        user_message = HumanMessage(
            content=self._build_user_prompt(task, workspace_context, correction_prompt)
        )

        # 调用LLM
        logger.info("Invoking LLM for outline generation")
        response = await self.llm.ainvoke([system_message, user_message])

        # 解析输出
        try:
            outline_data = self._parse_outline_response(response.content)
            logger.info(f"Outline parsed successfully: {len(outline_data.get('chapters', []))} chapters")
            return outline_data
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse outline JSON: {e}")
            # 返回默认大纲
            return self._create_default_outline(task)

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return """你是一位专业的故事大纲设计师，擅长构建完整、有吸引力的故事结构。

你的任务：
1. 分析用户需求和创作意图
2. 设计合理的故事结构（章节、节点）
3. 确保情节连贯、冲突充足
4. 考虑角色发展和主题表达

设计原则：
- **结构完整**：起承转合，节奏合理
- **冲突充足**：每个章节都有明确的冲突点
- **角色发展**：主角有清晰的成长轨迹
- **主题鲜明**：通过情节体现核心主题
- **吸引力**：设置悬念和高潮

输出格式（严格JSON）：
```json
{
  "title": "故事标题",
  "genre": "玄幻/都市/科幻/历史等",
  "core_theme": "核心主题",
  "target_audience": "目标读者",
  "estimated_total_words": 100000,
  "chapters": [
    {
      "chapter_id": 1,
      "title": "章节标题",
      "summary": "章节概要（100-200字）",
      "key_events": ["事件1", "事件2", "事件3"],
      "characters_involved": ["角色A", "角色B"],
      "conflict_type": "内心冲突/外部冲突/价值观冲突",
      "emotional_tone": "紧张/悬疑/温馨/激烈",
      "estimated_word_count": 3000,
      "chapter_goal": "本章目标",
      "cliffhanger": "悬念设置（可选）"
    }
  ],
  "story_arc": {
    "setup": [1, 2],
    "rising_action": [3, 4, 5],
    "climax": [6],
    "falling_action": [7],
    "resolution": [8]
  }
}
```

请生成完整、详细的故事大纲（JSON格式）。"""

    def _build_user_prompt(
        self,
        task: str,
        workspace_context: Dict[str, Any],
        correction_prompt: str
    ) -> str:
        """构建用户提示词"""
        prompt_parts = [
            f"创作任务：{task}",
            ""
        ]

        # 添加工作区上下文（如果有）
        if workspace_context:
            task_type = workspace_context.get("task_type", "unknown")
            project_info = workspace_context.get("project_info", {})

            if task_type == "continue_writing" or task_type == "expand_outline":
                prompt_parts.append("已有项目信息：")
                if project_info:
                    prompt_parts.append(f"项目名称：{project_info.get('name', '未命名')}")
                    prompt_parts.append(f"项目类型：{project_info.get('genre', '未指定')}")

                # 如果有现有大纲，展示它
                existing_outline = workspace_context.get("outline_nodes", [])
                if existing_outline:
                    prompt_parts.append(f"\n现有大纲（{len(existing_outline)}个章节）：")
                    for node in existing_outline[:3]:  # 只展示前3个
                        prompt_parts.append(f"- {node.get('title', '未命名章节')}: {node.get('summary', '')[:50]}...")
                    if len(existing_outline) > 3:
                        prompt_parts.append(f"... 还有{len(existing_outline) - 3}个章节")

                prompt_parts.append("\n请在现有基础上扩展或完善大纲。")

        # 添加修正提示词（如果有）
        if correction_prompt:
            prompt_parts.append("\n【修正要求】")
            prompt_parts.append(correction_prompt)
            prompt_parts.append("\n请根据上述修正要求重新生成大纲。")

        prompt_parts.append("\n请生成完整的故事大纲（JSON格式）：")

        return "\n".join(prompt_parts)

    def _parse_outline_response(self, response_content: str) -> Dict[str, Any]:
        """解析LLM响应

        Args:
            response_content: LLM响应内容

        Returns:
            Dict: 解析后的大纲数据
        """
        # 尝试提取JSON（可能被包裹在markdown代码块中）
        content = response_content.strip()

        # 移除markdown代码块标记
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]

        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

        # 解析JSON
        outline_data = json.loads(content)

        # 验证必要字段
        if "chapters" not in outline_data:
            raise ValueError("Missing 'chapters' field in outline data")

        # 确保每个章节都有必要字段
        for i, chapter in enumerate(outline_data["chapters"]):
            if "chapter_id" not in chapter:
                chapter["chapter_id"] = i + 1
            if "title" not in chapter:
                chapter["title"] = f"第{i+1}章"
            if "summary" not in chapter:
                chapter["summary"] = ""
            if "key_events" not in chapter:
                chapter["key_events"] = []
            if "characters_involved" not in chapter:
                chapter["characters_involved"] = []

        return outline_data

    def _create_default_outline(self, task: str) -> Dict[str, Any]:
        """创建默认大纲（解析失败时使用）

        Args:
            task: 创作任务

        Returns:
            Dict: 默认大纲数据
        """
        logger.warning("Creating default outline due to parsing failure")

        return {
            "title": "未命名故事",
            "genre": "未指定",
            "core_theme": task[:50] if task else "待定",
            "chapters": [
                {
                    "chapter_id": 1,
                    "title": "序章",
                    "summary": "故事开篇，引入主角和背景",
                    "key_events": ["主角登场", "背景介绍"],
                    "characters_involved": ["主角"],
                    "estimated_word_count": 3000
                },
                {
                    "chapter_id": 2,
                    "title": "起始",
                    "summary": "主角接受任务或遇到挑战",
                    "key_events": ["任务接受", "初步尝试"],
                    "characters_involved": ["主角", "导师"],
                    "estimated_word_count": 3000
                },
                {
                    "chapter_id": 3,
                    "title": "发展",
                    "summary": "主角面对困难，开始成长",
                    "key_events": ["遇到困难", "寻求帮助", "小胜利"],
                    "characters_involved": ["主角", "伙伴"],
                    "estimated_word_count": 3000
                }
            ],
            "story_arc": {
                "setup": [1],
                "rising_action": [2, 3],
                "climax": [],
                "falling_action": [],
                "resolution": []
            },
            "estimated_total_words": 9000
        }


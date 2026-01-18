"""
PlotAgent - 情节安排Agent

职责：
1. 基于大纲和角色设计情节
2. 生成时间线和事件序列
3. 确保情节连贯性和逻辑性
4. 设计情节冲突和高潮
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


class PlotAgent(BaseAgentV2):
    """情节安排Agent

    负责设计详细的情节和时间线，包括：
    - 时间线事件序列
    - 情节线索（主线、支线）
    - 冲突设计和高潮安排
    - 角色参与和互动
    """

    def __init__(
        self,
        llm_provider: str = "gemini",
        llm_model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ):
        """初始化PlotAgent

        Args:
            llm_provider: LLM提供商
            llm_model: LLM模型名称
            temperature: 温度参数
            **kwargs: 额外参数
        """
        super().__init__(
            name="PlotAgent",
            description="专业情节设计师，擅长构建紧凑、引人入胜的情节",
            version="v1.0"
        )

        # 创建LLM实例
        self.llm = LLMFactory.create_llm(
            provider=llm_provider,
            model=llm_model,
            temperature=temperature
        )

        self.config = kwargs
        logger.info(f"PlotAgent initialized with {llm_provider}/{llm_model}")

    def get_runnable(self) -> Runnable[PipelineStateV2, PipelineStateV2]:
        """获取LangChain Runnable（暂未实现）"""
        raise NotImplementedError("PlotAgent暂未实现LangChain Runnable接口")

    async def execute(self, state: PipelineStateV2) -> PipelineStateV2:
        """执行情节设计

        Args:
            state: 流水线状态

        Returns:
            PipelineStateV2: 更新后的状态
        """
        start_time = time.time()
        logger.info("Starting PlotAgent execution")

        try:
            # Step 1: 获取大纲和角色信息
            agent_outputs = state.get("agent_outputs", {})
            outline_output = agent_outputs.get("outline_agent", {})
            character_output = agent_outputs.get("character_agent", {})

            outline_nodes = state.get("outline_nodes", [])
            characters = state.get("characters", [])
            task = state.get("task", "")
            workspace_context = state.get("workspace_context", {})
            correction_prompts = state.get("correction_prompts", {})

            # Step 2: 生成情节
            plot_data = await self._generate_plot(
                task=task,
                outline_output=outline_output,
                character_output=character_output,
                outline_nodes=outline_nodes,
                characters=characters,
                workspace_context=workspace_context,
                correction_prompt=correction_prompts.get("plot_agent", "")
            )

            # Step 3: 更新状态
            execution_time = time.time() - start_time

            updated_state = {
                **state,
                **update_agent_output(state, "plot_agent", plot_data),
                "timeline_events": plot_data.get("timeline_events", []),
                "reasoning": state.get("reasoning", []) + [
                    f"PlotAgent: 创建了{len(plot_data.get('timeline_events', []))}个时间线事件",
                    f"PlotAgent: 创建了{len(plot_data.get('plot_threads', []))}条情节线索",
                    f"PlotAgent: 执行时间{execution_time:.2f}秒"
                ],
                "current_step": "review"  # 下一步：审核
            }

            # 更新执行时间
            agent_times = state.get("agent_execution_times", {}).copy()
            agent_times["plot_agent"] = execution_time
            updated_state["agent_execution_times"] = agent_times

            logger.info(
                f"PlotAgent completed: {len(plot_data.get('timeline_events', []))} events, "
                f"{len(plot_data.get('plot_threads', []))} threads"
            )
            return updated_state

        except Exception as e:
            logger.error(f"PlotAgent execution failed: {e}", exc_info=True)
            return {
                **state,
                "errors": state.get("errors", []) + [f"PlotAgent error: {str(e)}"],
                "current_step": "error"
            }

    async def _generate_plot(
        self,
        task: str,
        outline_output: Dict[str, Any],
        character_output: Dict[str, Any],
        outline_nodes: List[Dict[str, Any]],
        characters: List[Dict[str, Any]],
        workspace_context: Dict[str, Any],
        correction_prompt: str = ""
    ) -> Dict[str, Any]:
        """生成情节

        Args:
            task: 创作任务
            outline_output: 大纲输出
            character_output: 角色输出
            outline_nodes: 大纲节点
            characters: 角色列表
            workspace_context: 工作区上下文
            correction_prompt: 修正提示词

        Returns:
            Dict: 情节数据
        """
        # 构建系统提示词
        system_message = SystemMessage(content=self._build_system_prompt())

        # 构建用户提示词
        user_message = HumanMessage(
            content=self._build_user_prompt(
                task, outline_output, character_output,
                outline_nodes, characters, workspace_context, correction_prompt
            )
        )

        # 调用LLM
        logger.info("Invoking LLM for plot generation")
        response = await self.llm.ainvoke([system_message, user_message])

        # 解析输出
        try:
            plot_data = self._parse_plot_response(response.content)
            logger.info(
                f"Plot parsed successfully: {len(plot_data.get('timeline_events', []))} events"
            )
            return plot_data
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse plot JSON: {e}")
            # 返回默认情节
            return self._create_default_plot(task, outline_output, character_output)

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return """你是一位专业的情节设计专家，擅长构建紧凑、引人入胜、逻辑严密的故事情节。

你的任务：
1. 基于大纲和角色设计详细情节
2. 生成时间线和事件序列
3. 设计情节冲突和高潮
4. 确保情节逻辑连贯

设计原则：
- **因果关系**：每个事件都有合理的因果
- **冲突设计**：充分利用角色关系和动机设计冲突
- **节奏控制**：张弛有度，高潮迭起
- **逻辑自洽**：时间线合理，无明显逻辑漏洞
- **角色一致**：角色行为符合其性格和动机

输出格式（严格JSON）：
```json
{
  "timeline_events": [
    {
      "event_id": "evt_001",
      "timestamp": "第1天/第1章/序章",
      "location": "地点名称",
      "title": "事件标题",
      "description": "详细事件描述（200-300字）",
      "participants": ["角色A", "角色B"],
      "event_type": "冲突/转折/高潮/铺垫/结局",
      "impact": {
        "on_plot": "对主线情节的影响",
        "on_characters": {
          "角色A": "对角色A的影响",
          "角色B": "对角色B的影响"
        },
        "emotional_impact": "情感冲击力"
      },
      "causes": ["前置事件ID"],
      "consequences": ["后续事件ID"],
      "chapter_id": 1
    }
  ],
  "plot_threads": [
    {
      "thread_id": "thread_main",
      "title": "主线：复仇之路",
      "description": "主角的复仇与成长之旅",
      "type": "main/subplot",
      "events": ["evt_001", "evt_005", "evt_010"],
      "starting_event": "evt_001",
      "climax_event": "evt_010",
      "resolution_event": "evt_015",
      "characters_involved": ["主角", "反派"]
    }
  ],
  "conflicts": [
    {
      "conflict_id": "conflict_001",
      "type": "人物冲突/内心冲突/环境冲突",
      "parties": ["角色A", "角色B"],
      "description": "冲突描述",
      "escalation_events": ["evt_003", "evt_007"],
      "resolution_event": "evt_012"
    }
  ],
  "key_plot_points": {
    "inciting_incident": "evt_001",
    "plot_point_1": "evt_005",
    "midpoint": "evt_010",
    "plot_point_2": "evt_015",
    "climax": "evt_020",
    "resolution": "evt_025"
  }
}
```

请生成完整、详细的情节设计（JSON格式）。"""

    def _build_user_prompt(
        self,
        task: str,
        outline_output: Dict[str, Any],
        character_output: Dict[str, Any],
        outline_nodes: List[Dict[str, Any]],
        characters: List[Dict[str, Any]],
        workspace_context: Dict[str, Any],
        correction_prompt: str
    ) -> str:
        """构建用户提示词"""
        prompt_parts = [
            f"创作任务：{task}",
            ""
        ]

        # 添加大纲信息
        if outline_output or outline_nodes:
            prompt_parts.append("【故事大纲】")

            if outline_output:
                title = outline_output.get("title", "未命名")
                theme = outline_output.get("core_theme", "")
                prompt_parts.append(f"标题：{title}")
                if theme:
                    prompt_parts.append(f"主题：{theme}")

            chapters = outline_output.get("chapters", outline_nodes)
            if chapters:
                prompt_parts.append(f"\n章节结构（共{len(chapters)}章）：")
                for chapter in chapters:
                    chapter_id = chapter.get("chapter_id", 0)
                    title = chapter.get("title", "")
                    summary = chapter.get("summary", "")
                    prompt_parts.append(f"{chapter_id}. {title}: {summary[:80]}...")

        # 添加角色信息
        if character_output or characters:
            prompt_parts.append("\n【角色信息】")

            char_list = character_output.get("characters", characters)
            if char_list:
                prompt_parts.append(f"共{len(char_list)}个角色：")

                for char in char_list[:5]:  # 只展示前5个
                    name = char.get("name", "未命名")
                    role_type = char.get("role_type", "")
                    motivation = char.get("motivation", "")

                    prompt_parts.append(f"\n- {name} ({role_type})")
                    if motivation:
                        prompt_parts.append(f"  动机：{motivation[:60]}...")

                    # 角色关系
                    relationships = char.get("relationships", [])
                    if relationships:
                        rel_summary = ", ".join([
                            f"{r.get('character', '')}({r.get('relation_type', '')})"
                            for r in relationships[:2]
                        ])
                        prompt_parts.append(f"  关系：{rel_summary}")

                if len(char_list) > 5:
                    prompt_parts.append(f"\n... 还有{len(char_list) - 5}个角色")

            # 角色关系网络
            if character_output.get("relationship_network"):
                network = character_output["relationship_network"]
                if network.get("conflicts"):
                    prompt_parts.append(f"\n冲突关系：{network['conflicts']}")
                if network.get("alliances"):
                    prompt_parts.append(f"联盟关系：{network['alliances']}")

        # 添加修正提示词
        if correction_prompt:
            prompt_parts.append("\n【修正要求】")
            prompt_parts.append(correction_prompt)
            prompt_parts.append("\n请根据上述修正要求重新生成情节。")

        prompt_parts.append("\n请基于大纲和角色设计详细的情节和时间线（JSON格式）：")
        prompt_parts.append("注意：")
        prompt_parts.append("1. 每个事件都要有明确的因果关系")
        prompt_parts.append("2. 充分利用角色关系设计冲突")
        prompt_parts.append("3. 事件要与章节对应")
        prompt_parts.append("4. 确保时间线逻辑合理")

        return "\n".join(prompt_parts)

    def _parse_plot_response(self, response_content: str) -> Dict[str, Any]:
        """解析LLM响应

        Args:
            response_content: LLM响应内容

        Returns:
            Dict: 解析后的情节数据
        """
        # 提取JSON
        content = response_content.strip()

        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]

        if content.endswith("```"):
            content = content[:-3]

        content = content.strip()

        # 解析JSON
        plot_data = json.loads(content)

        # 验证必要字段
        if "timeline_events" not in plot_data:
            plot_data["timeline_events"] = []

        if "plot_threads" not in plot_data:
            plot_data["plot_threads"] = []

        # 确保每个事件都有必要字段
        for i, event in enumerate(plot_data["timeline_events"]):
            if "event_id" not in event:
                event["event_id"] = f"evt_{i+1:03d}"
            if "title" not in event:
                event["title"] = f"事件{i+1}"
            if "description" not in event:
                event["description"] = ""
            if "participants" not in event:
                event["participants"] = []

        return plot_data

    def _create_default_plot(
        self,
        task: str,
        outline_output: Dict[str, Any],
        character_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建默认情节（解析失败时使用）

        Args:
            task: 创作任务
            outline_output: 大纲输出
            character_output: 角色输出

        Returns:
            Dict: 默认情节数据
        """
        logger.warning("Creating default plot due to parsing failure")

        # 从大纲和角色中提取基本信息
        title = outline_output.get("title", "未命名故事")
        chapters = outline_output.get("chapters", [])
        characters = character_output.get("characters", [])

        # 创建基础事件
        events = []
        for i, chapter in enumerate(chapters[:3], 1):
            event = {
                "event_id": f"evt_{i:03d}",
                "timestamp": f"第{chapter.get('chapter_id', i)}章",
                "title": chapter.get("title", f"第{i}章事件"),
                "description": chapter.get("summary", "待详细设计"),
                "participants": chapter.get("characters_involved", []),
                "chapter_id": chapter.get("chapter_id", i),
                "event_type": "铺垫" if i == 1 else "发展"
            }
            events.append(event)

        return {
            "timeline_events": events,
            "plot_threads": [
                {
                    "thread_id": "thread_main",
                    "title": "主线",
                    "type": "main",
                    "events": [e["event_id"] for e in events]
                }
            ],
            "conflicts": [],
            "key_plot_points": {
                "inciting_incident": events[0]["event_id"] if events else None
            }
        }


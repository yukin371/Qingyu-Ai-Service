"""
CharacterAgent - 角色设计Agent

职责：
1. 基于大纲创建角色卡
2. 分析角色关系网络
3. 生成角色发展弧线
4. 确保角色性格鲜明、立体
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


class CharacterAgent(BaseAgentV2):
    """角色设计Agent

    负责创建丰富的角色卡，包括：
    - 角色基本信息和性格特征
    - 角色关系网络
    - 角色发展弧线
    - 角色在故事中的作用
    """

    def __init__(
        self,
        llm_provider: str = "gemini",
        llm_model: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ):
        """初始化CharacterAgent

        Args:
            llm_provider: LLM提供商
            llm_model: LLM模型名称
            temperature: 温度参数
            **kwargs: 额外参数
        """
        super().__init__(
            name="CharacterAgent",
            description="专业角色设计师，擅长创建立体、鲜明的角色",
            version="v1.0"
        )

        # 创建LLM实例
        self.llm = LLMFactory.create_llm(
            provider=llm_provider,
            model=llm_model,
            temperature=temperature
        )

        self.config = kwargs
        logger.info(f"CharacterAgent initialized with {llm_provider}/{llm_model}")

    def get_runnable(self) -> Runnable[PipelineStateV2, PipelineStateV2]:
        """获取LangChain Runnable（暂未实现）"""
        raise NotImplementedError("CharacterAgent暂未实现LangChain Runnable接口")

    async def execute(self, state: PipelineStateV2) -> PipelineStateV2:
        """执行角色设计

        Args:
            state: 流水线状态

        Returns:
            PipelineStateV2: 更新后的状态
        """
        start_time = time.time()
        logger.info("Starting CharacterAgent execution")

        try:
            # Step 1: 获取大纲信息
            outline_output = state.get("agent_outputs", {}).get("outline_agent", {})
            outline_nodes = state.get("outline_nodes", [])
            task = state.get("task", "")
            workspace_context = state.get("workspace_context", {})
            correction_prompts = state.get("correction_prompts", {})

            # Step 2: 生成角色
            characters_data = await self._generate_characters(
                task=task,
                outline_output=outline_output,
                outline_nodes=outline_nodes,
                workspace_context=workspace_context,
                correction_prompt=correction_prompts.get("character_agent", "")
            )

            # Step 3: 更新状态
            execution_time = time.time() - start_time

            updated_state = {
                **state,
                **update_agent_output(state, "character_agent", characters_data),
                "characters": characters_data.get("characters", []),
                "reasoning": state.get("reasoning", []) + [
                    f"CharacterAgent: 创建了{len(characters_data.get('characters', []))}个角色",
                    f"CharacterAgent: 执行时间{execution_time:.2f}秒"
                ],
                "current_step": "plot"  # 下一步：情节设计
            }

            # 更新执行时间
            agent_times = state.get("agent_execution_times", {}).copy()
            agent_times["character_agent"] = execution_time
            updated_state["agent_execution_times"] = agent_times

            logger.info(f"CharacterAgent completed: created {len(characters_data.get('characters', []))} characters")
            return updated_state

        except Exception as e:
            logger.error(f"CharacterAgent execution failed: {e}", exc_info=True)
            return {
                **state,
                "errors": state.get("errors", []) + [f"CharacterAgent error: {str(e)}"],
                "current_step": "error"
            }

    async def _generate_characters(
        self,
        task: str,
        outline_output: Dict[str, Any],
        outline_nodes: List[Dict[str, Any]],
        workspace_context: Dict[str, Any],
        correction_prompt: str = ""
    ) -> Dict[str, Any]:
        """生成角色

        Args:
            task: 创作任务
            outline_output: 大纲输出
            outline_nodes: 大纲节点
            workspace_context: 工作区上下文
            correction_prompt: 修正提示词

        Returns:
            Dict: 角色数据
        """
        # 构建系统提示词
        system_message = SystemMessage(content=self._build_system_prompt())

        # 构建用户提示词
        user_message = HumanMessage(
            content=self._build_user_prompt(
                task, outline_output, outline_nodes, workspace_context, correction_prompt
            )
        )

        # 调用LLM
        logger.info("Invoking LLM for character generation")
        response = await self.llm.ainvoke([system_message, user_message])

        # 解析输出
        try:
            characters_data = self._parse_characters_response(response.content)
            logger.info(f"Characters parsed successfully: {len(characters_data.get('characters', []))} characters")
            return characters_data
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse characters JSON: {e}")
            # 返回默认角色
            return self._create_default_characters(task, outline_output)

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return """你是一位专业的角色设计专家，擅长创建立体、鲜明、有深度的角色。

你的任务：
1. 基于大纲创建必要的角色
2. 设计角色的性格、背景、动机
3. 构建角色关系网络
4. 规划角色发展弧线

设计原则：
- **立体性**：角色有优点也有缺点，不是扁平的
- **动机清晰**：角色行为有合理的动机支撑
- **关系合理**：角色之间的关系自然、有张力
- **成长性**：主要角色有明确的成长轨迹
- **差异化**：每个角色都有独特的性格特征

输出格式（严格JSON）：
```json
{
  "characters": [
    {
      "character_id": "char_001",
      "name": "角色名",
      "role_type": "protagonist/antagonist/supporting",
      "importance": "major/minor",
      "age": 18,
      "gender": "男/女/其他",
      "appearance": "外貌描述",
      "personality": {
        "traits": ["勇敢", "冲动", "善良"],
        "strengths": ["武艺高强", "聪明机智"],
        "weaknesses": ["过度自信", "不善交际"],
        "core_values": "正义、自由",
        "fears": "失去亲人"
      },
      "background": {
        "summary": "背景故事概要",
        "family": "家庭背景",
        "education": "教育经历",
        "key_experiences": ["关键经历1", "关键经历2"]
      },
      "motivation": "核心动机和目标",
      "relationships": [
        {
          "character": "角色B",
          "relation_type": "friend/enemy/family/mentor/rival",
          "description": "关系描述",
          "dynamics": "关系动态和发展"
        }
      ],
      "development_arc": {
        "starting_point": "起始状态",
        "turning_points": ["转折点1", "转折点2"],
        "ending_point": "结束状态",
        "growth_theme": "成长主题"
      },
      "role_in_story": "在故事中的作用",
      "first_appearance": 1,
      "chapters_involved": [1, 2, 3, 4]
    }
  ],
  "relationship_network": {
    "alliances": [["角色A", "角色B"]],
    "conflicts": [["角色A", "角色C"]],
    "mentorships": [{"mentor": "角色D", "student": "角色A"}]
  }
}
```

请生成完整、详细的角色设计（JSON格式）。"""

    def _build_user_prompt(
        self,
        task: str,
        outline_output: Dict[str, Any],
        outline_nodes: List[Dict[str, Any]],
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
                genre = outline_output.get("genre", "未指定")
                theme = outline_output.get("core_theme", "")

                prompt_parts.append(f"标题：{title}")
                prompt_parts.append(f"类型：{genre}")
                if theme:
                    prompt_parts.append(f"主题：{theme}")

            # 章节信息
            chapters = outline_output.get("chapters", outline_nodes)
            if chapters:
                prompt_parts.append(f"\n章节概要（共{len(chapters)}章）：")
                for i, chapter in enumerate(chapters[:5], 1):  # 只展示前5章
                    title = chapter.get("title", f"第{i}章")
                    summary = chapter.get("summary", "")
                    characters_mentioned = chapter.get("characters_involved", [])

                    prompt_parts.append(f"{i}. {title}")
                    if summary:
                        prompt_parts.append(f"   概要：{summary[:100]}...")
                    if characters_mentioned:
                        prompt_parts.append(f"   提及角色：{', '.join(characters_mentioned)}")

                if len(chapters) > 5:
                    prompt_parts.append(f"... 还有{len(chapters) - 5}章")

        # 添加现有角色（如果有）
        existing_characters = workspace_context.get("characters", []) if workspace_context else []
        if existing_characters:
            prompt_parts.append("\n【现有角色】")
            for char in existing_characters[:3]:
                name = char.get("name", "未命名")
                role = char.get("role_type", "")
                prompt_parts.append(f"- {name} ({role})")
            if len(existing_characters) > 3:
                prompt_parts.append(f"... 还有{len(existing_characters) - 3}个角色")
            prompt_parts.append("\n请在现有角色基础上扩展或完善。")

        # 添加修正提示词
        if correction_prompt:
            prompt_parts.append("\n【修正要求】")
            prompt_parts.append(correction_prompt)
            prompt_parts.append("\n请根据上述修正要求重新生成角色。")

        prompt_parts.append("\n请基于大纲生成完整的角色设计（JSON格式）：")
        prompt_parts.append("注意：")
        prompt_parts.append("1. 确保所有在大纲中提及的角色都被创建")
        prompt_parts.append("2. 角色性格要与其在故事中的行为一致")
        prompt_parts.append("3. 角色关系要合理，有冲突也有联盟")
        prompt_parts.append("4. 主角要有明确的成长轨迹")

        return "\n".join(prompt_parts)

    def _parse_characters_response(self, response_content: str) -> Dict[str, Any]:
        """解析LLM响应

        Args:
            response_content: LLM响应内容

        Returns:
            Dict: 解析后的角色数据
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
        characters_data = json.loads(content)

        # 验证必要字段
        if "characters" not in characters_data:
            raise ValueError("Missing 'characters' field in characters data")

        # 确保每个角色都有必要字段
        for i, char in enumerate(characters_data["characters"]):
            if "character_id" not in char:
                char["character_id"] = f"char_{i+1:03d}"
            if "name" not in char:
                char["name"] = f"角色{i+1}"
            if "role_type" not in char:
                char["role_type"] = "supporting"
            if "personality" not in char:
                char["personality"] = {
                    "traits": [],
                    "strengths": [],
                    "weaknesses": []
                }
            if "relationships" not in char:
                char["relationships"] = []

        return characters_data

    def _create_default_characters(
        self, task: str, outline_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建默认角色（解析失败时使用）

        Args:
            task: 创作任务
            outline_output: 大纲输出

        Returns:
            Dict: 默认角色数据
        """
        logger.warning("Creating default characters due to parsing failure")

        return {
            "characters": [
                {
                    "character_id": "char_001",
                    "name": "主角",
                    "role_type": "protagonist",
                    "importance": "major",
                    "personality": {
                        "traits": ["勇敢", "正直"],
                        "strengths": ["坚韧不拔"],
                        "weaknesses": ["过于理想化"],
                        "core_values": "正义",
                        "fears": "失败"
                    },
                    "background": {
                        "summary": "普通人的非凡旅程",
                        "family": "普通家庭",
                        "key_experiences": []
                    },
                    "motivation": "追求真理和正义",
                    "relationships": [],
                    "development_arc": {
                        "starting_point": "普通人",
                        "turning_points": [],
                        "ending_point": "英雄",
                        "growth_theme": "成长与蜕变"
                    },
                    "role_in_story": "故事主线推动者",
                    "first_appearance": 1,
                    "chapters_involved": [1]
                }
            ],
            "relationship_network": {
                "alliances": [],
                "conflicts": [],
                "mentorships": []
            }
        }


"""
CharacterAgent测试
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch

from src.agents.specialized.character_agent import CharacterAgent
from src.agents.states.pipeline_state_v2 import create_initial_pipeline_state_v2


class TestCharacterAgent:
    """CharacterAgent测试类"""

    @pytest.fixture
    def character_agent(self):
        """创建CharacterAgent实例"""
        return CharacterAgent(llm_provider="gemini", temperature=0.7)

    @pytest.fixture
    def initial_state_with_outline(self):
        """创建包含大纲的初始状态"""
        state = create_initial_pipeline_state_v2(
            task="创作一个关于修仙少年的玄幻故事",
            user_id="test_user",
            project_id="test_project"
        )

        # 添加大纲输出
        state["agent_outputs"] = {
            "outline_agent": {
                "title": "仙途之路",
                "genre": "玄幻",
                "core_theme": "逆天改命",
                "chapters": [
                    {
                        "chapter_id": 1,
                        "title": "废材少年",
                        "summary": "主角李云遭受冷眼",
                        "characters_involved": ["李云", "家主", "长老"]
                    },
                    {
                        "chapter_id": 2,
                        "title": "初露锋芒",
                        "summary": "李云崭露头角",
                        "characters_involved": ["李云", "宗门长老", "对手张三"]
                    }
                ]
            }
        }

        state["outline_nodes"] = state["agent_outputs"]["outline_agent"]["chapters"]

        return state

    @pytest.fixture
    def mock_llm_response(self):
        """Mock LLM响应"""
        characters_json = {
            "characters": [
                {
                    "character_id": "char_001",
                    "name": "李云",
                    "role_type": "protagonist",
                    "importance": "major",
                    "age": 16,
                    "gender": "男",
                    "appearance": "清秀少年，眼神坚定",
                    "personality": {
                        "traits": ["坚韧", "聪慧", "正直"],
                        "strengths": ["悟性极高", "意志坚定"],
                        "weaknesses": ["过于执着", "不善交际"],
                        "core_values": "公平正义",
                        "fears": "再次被轻视"
                    },
                    "background": {
                        "summary": "家族废材，因功法残缺无法修炼",
                        "family": "李家旁支",
                        "key_experiences": ["家族试炼失败", "获得神秘功法"]
                    },
                    "motivation": "证明自己，改变命运",
                    "relationships": [
                        {
                            "character": "家主",
                            "relation_type": "family",
                            "description": "冷漠的长辈",
                            "dynamics": "从被忽视到被认可"
                        }
                    ],
                    "development_arc": {
                        "starting_point": "家族废材",
                        "turning_points": ["获得功法", "突破境界"],
                        "ending_point": "修仙天才",
                        "growth_theme": "从平凡到不凡"
                    },
                    "role_in_story": "主角，推动故事发展",
                    "first_appearance": 1,
                    "chapters_involved": [1, 2]
                },
                {
                    "character_id": "char_002",
                    "name": "张三",
                    "role_type": "antagonist",
                    "importance": "minor",
                    "personality": {
                        "traits": ["傲慢", "嫉妒"],
                        "strengths": ["天赋出众"],
                        "weaknesses": ["心胸狭窄"]
                    },
                    "motivation": "打压李云，维护地位",
                    "relationships": [
                        {
                            "character": "李云",
                            "relation_type": "rival",
                            "description": "竞争对手"
                        }
                    ],
                    "role_in_story": "早期对手，衬托主角成长",
                    "first_appearance": 2,
                    "chapters_involved": [2]
                }
            ],
            "relationship_network": {
                "alliances": [],
                "conflicts": [["李云", "张三"]],
                "mentorships": []
            }
        }

        mock_response = Mock()
        mock_response.content = json.dumps(characters_json, ensure_ascii=False)
        return mock_response

    @pytest.mark.asyncio
    async def test_character_agent_initialization(self, character_agent):
        """测试CharacterAgent初始化"""
        assert character_agent.name == "CharacterAgent"
        assert character_agent.version == "v1.0"
        assert character_agent.llm is not None

    @pytest.mark.asyncio
    async def test_generate_characters_basic(
        self, character_agent, initial_state_with_outline, mock_llm_response
    ):
        """测试基础角色生成"""
        with patch.object(character_agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = mock_llm_response

            # 执行
            result_state = await character_agent.execute(initial_state_with_outline)

            # 验证
            assert "errors" not in result_state or len(result_state["errors"]) == 0
            assert "character_agent" in result_state.get("agent_outputs", {})

            character_output = result_state["agent_outputs"]["character_agent"]
            assert "characters" in character_output
            assert len(character_output["characters"]) == 2

            # 验证主角
            protagonist = character_output["characters"][0]
            assert protagonist["name"] == "李云"
            assert protagonist["role_type"] == "protagonist"
            assert "personality" in protagonist
            assert "development_arc" in protagonist

            # 验证characters字段也被更新
            assert len(result_state.get("characters", [])) == 2

            # 验证下一步设置为plot
            assert result_state.get("current_step") == "plot"

    @pytest.mark.asyncio
    async def test_generate_characters_with_outline_info(
        self, character_agent, initial_state_with_outline, mock_llm_response
    ):
        """测试使用大纲信息生成角色"""
        with patch.object(character_agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = mock_llm_response

            # 执行
            result_state = await character_agent.execute(initial_state_with_outline)

            # 验证调用了LLM
            assert mock_ainvoke.called
            call_args = mock_ainvoke.call_args[0][0]
            user_message = call_args[1].content

            # 验证用户消息包含大纲信息
            assert "故事大纲" in user_message
            assert "仙途之路" in user_message
            assert "李云" in user_message  # 大纲中提及的角色

    @pytest.mark.asyncio
    async def test_generate_characters_with_existing_characters(
        self, character_agent, initial_state_with_outline, mock_llm_response
    ):
        """测试有现有角色时的生成"""
        # 添加现有角色
        initial_state_with_outline["workspace_context"] = {
            "characters": [
                {"name": "老角色A", "role_type": "supporting"}
            ]
        }

        with patch.object(character_agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = mock_llm_response

            # 执行
            result_state = await character_agent.execute(initial_state_with_outline)

            # 验证用户消息包含现有角色信息
            call_args = mock_ainvoke.call_args[0][0]
            user_message = call_args[1].content
            assert "现有角色" in user_message
            assert "老角色A" in user_message

    @pytest.mark.asyncio
    async def test_generate_characters_with_correction(
        self, character_agent, initial_state_with_outline, mock_llm_response
    ):
        """测试带修正提示词的角色生成"""
        # 添加修正提示词
        initial_state_with_outline["correction_prompts"] = {
            "character_agent": "请为李云增加一个性格弱点：优柔寡断"
        }

        with patch.object(character_agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = mock_llm_response

            # 执行
            result_state = await character_agent.execute(initial_state_with_outline)

            # 验证用户消息包含修正提示词
            call_args = mock_ainvoke.call_args[0][0]
            user_message = call_args[1].content
            assert "修正要求" in user_message
            assert "优柔寡断" in user_message

    @pytest.mark.asyncio
    async def test_parse_characters_fills_missing_fields(self, character_agent):
        """测试解析会填充缺失字段"""
        incomplete_json = json.dumps({
            "characters": [
                {"name": "测试角色"},
                {}
            ]
        })

        result = character_agent._parse_characters_response(incomplete_json)

        # 验证填充了缺失字段
        assert result["characters"][0]["character_id"] == "char_001"
        assert result["characters"][0]["role_type"] == "supporting"
        assert "personality" in result["characters"][0]

        assert result["characters"][1]["character_id"] == "char_002"
        assert result["characters"][1]["name"] == "角色2"

    @pytest.mark.asyncio
    async def test_create_default_characters(self, character_agent):
        """测试创建默认角色"""
        task = "创作一个科幻故事"
        outline_output = {"title": "星际冒险"}

        result = character_agent._create_default_characters(task, outline_output)

        assert "characters" in result
        assert len(result["characters"]) == 1
        assert result["characters"][0]["name"] == "主角"
        assert result["characters"][0]["role_type"] == "protagonist"

    @pytest.mark.asyncio
    async def test_handle_llm_error(self, character_agent, initial_state_with_outline):
        """测试处理LLM错误"""
        with patch.object(character_agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.side_effect = Exception("LLM调用失败")

            # 执行
            result_state = await character_agent.execute(initial_state_with_outline)

            # 验证错误被捕获
            assert len(result_state.get("errors", [])) > 0
            assert "CharacterAgent error" in result_state["errors"][0]
            assert result_state.get("current_step") == "error"

    @pytest.mark.asyncio
    async def test_handle_json_parse_error(
        self, character_agent, initial_state_with_outline
    ):
        """测试处理JSON解析错误"""
        mock_response = Mock()
        mock_response.content = "这不是有效的JSON"

        with patch.object(character_agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = mock_response

            # 执行
            result_state = await character_agent.execute(initial_state_with_outline)

            # 验证返回了默认角色
            assert "character_agent" in result_state.get("agent_outputs", {})
            character_output = result_state["agent_outputs"]["character_agent"]
            assert len(character_output["characters"]) == 1
            assert character_output["characters"][0]["name"] == "主角"

    @pytest.mark.asyncio
    async def test_relationship_network(
        self, character_agent, initial_state_with_outline, mock_llm_response
    ):
        """测试角色关系网络"""
        with patch.object(character_agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = mock_llm_response

            # 执行
            result_state = await character_agent.execute(initial_state_with_outline)

            character_output = result_state["agent_outputs"]["character_agent"]

            # 验证关系网络
            assert "relationship_network" in character_output
            network = character_output["relationship_network"]
            assert "conflicts" in network
            assert ["李云", "张三"] in network["conflicts"]

    @pytest.mark.asyncio
    async def test_execution_time_tracking(
        self, character_agent, initial_state_with_outline, mock_llm_response
    ):
        """测试执行时间追踪"""
        with patch.object(character_agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = mock_llm_response

            # 执行
            result_state = await character_agent.execute(initial_state_with_outline)

            # 验证执行时间被记录
            assert "agent_execution_times" in result_state
            assert "character_agent" in result_state["agent_execution_times"]
            assert result_state["agent_execution_times"]["character_agent"] > 0


"""
OutlineAgent测试
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch

from agents.specialized.outline_agent import OutlineAgent
from agents.states.pipeline_state_v2 import create_initial_pipeline_state_v2


class TestOutlineAgent:
    """OutlineAgent测试类"""

    @pytest.fixture
    def outline_agent(self):
        """创建OutlineAgent实例"""
        return OutlineAgent(llm_provider="gemini", temperature=0.7)

    @pytest.fixture
    def initial_state(self):
        """创建初始状态"""
        return create_initial_pipeline_state_v2(
            task="创作一个关于修仙少年的玄幻故事",
            user_id="test_user",
            project_id="test_project"
        )

    @pytest.fixture
    def mock_llm_response(self):
        """Mock LLM响应"""
        outline_json = {
            "title": "仙途之路",
            "genre": "玄幻",
            "core_theme": "逆天改命，突破极限",
            "target_audience": "15-30岁男性",
            "estimated_total_words": 100000,
            "chapters": [
                {
                    "chapter_id": 1,
                    "title": "废材少年",
                    "summary": "主角李云，天赋平庸，遭受家族冷眼。一次意外获得神秘功法。",
                    "key_events": ["家族试炼失败", "发现神秘洞府", "获得功法"],
                    "characters_involved": ["李云", "家主"],
                    "conflict_type": "内心冲突",
                    "emotional_tone": "压抑转希望",
                    "estimated_word_count": 3000,
                    "chapter_goal": "引入主角和背景",
                    "cliffhanger": "功法突然发光"
                },
                {
                    "chapter_id": 2,
                    "title": "初露锋芒",
                    "summary": "李云开始修炼，实力飞速提升，在宗门考核中一鸣惊人。",
                    "key_events": ["刻苦修炼", "宗门考核", "击败天才"],
                    "characters_involved": ["李云", "宗门长老", "对手"],
                    "conflict_type": "外部冲突",
                    "emotional_tone": "紧张激烈",
                    "estimated_word_count": 3500,
                    "chapter_goal": "展现主角成长",
                    "cliffhanger": "神秘势力注意"
                }
            ],
            "story_arc": {
                "setup": [1],
                "rising_action": [2],
                "climax": [],
                "falling_action": [],
                "resolution": []
            }
        }

        mock_response = Mock()
        mock_response.content = json.dumps(outline_json, ensure_ascii=False)
        return mock_response

    @pytest.mark.asyncio
    async def test_outline_agent_initialization(self, outline_agent):
        """测试OutlineAgent初始化"""
        assert outline_agent.name == "OutlineAgent"
        assert outline_agent.version == "v1.0"
        assert outline_agent.llm is not None

    @pytest.mark.asyncio
    async def test_generate_outline_basic(self, outline_agent, initial_state, mock_llm_response):
        """测试基础大纲生成"""
        # Mock LLM调用
        with patch.object(outline_agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = mock_llm_response

            # 执行
            result_state = await outline_agent.execute(initial_state)

            # 验证
            assert "errors" not in result_state or len(result_state["errors"]) == 0
            assert "outline_agent" in result_state.get("agent_outputs", {})

            outline_output = result_state["agent_outputs"]["outline_agent"]
            assert "chapters" in outline_output
            assert len(outline_output["chapters"]) == 2
            assert outline_output["title"] == "仙途之路"

            # 验证outline_nodes也被更新
            assert len(result_state.get("outline_nodes", [])) == 2

            # 验证下一步设置为character
            assert result_state.get("current_step") == "character"

    @pytest.mark.asyncio
    async def test_generate_outline_with_context(self, outline_agent, initial_state, mock_llm_response):
        """测试带上下文的大纲生成"""
        # 添加工作区上下文
        initial_state["workspace_context"] = {
            "task_type": "expand_outline",
            "project_info": {
                "name": "修仙传",
                "genre": "玄幻"
            },
            "outline_nodes": [
                {"title": "第一章", "summary": "主角出场"}
            ]
        }

        # Mock LLM调用
        with patch.object(outline_agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = mock_llm_response

            # 执行
            result_state = await outline_agent.execute(initial_state)

            # 验证调用了LLM
            assert mock_ainvoke.called
            call_args = mock_ainvoke.call_args[0][0]
            assert len(call_args) == 2  # system + user message

            # 验证用户消息包含上下文信息
            user_message = call_args[1].content
            assert "现有大纲" in user_message or "已有项目信息" in user_message

    @pytest.mark.asyncio
    async def test_generate_outline_with_correction(self, outline_agent, initial_state, mock_llm_response):
        """测试带修正提示词的大纲生成"""
        # 添加修正提示词
        initial_state["correction_prompts"] = {
            "outline_agent": "请增加更多冲突，让第一章更有吸引力"
        }

        # Mock LLM调用
        with patch.object(outline_agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = mock_llm_response

            # 执行
            result_state = await outline_agent.execute(initial_state)

            # 验证调用了LLM
            assert mock_ainvoke.called
            call_args = mock_ainvoke.call_args[0][0]
            user_message = call_args[1].content

            # 验证用户消息包含修正提示词
            assert "修正要求" in user_message
            assert "更多冲突" in user_message

    @pytest.mark.asyncio
    async def test_parse_outline_with_markdown(self, outline_agent):
        """测试解析带markdown的JSON响应"""
        json_with_markdown = """```json
{
  "title": "测试标题",
  "chapters": [
    {
      "chapter_id": 1,
      "title": "第一章"
    }
  ]
}
```"""

        result = outline_agent._parse_outline_response(json_with_markdown)

        assert result["title"] == "测试标题"
        assert len(result["chapters"]) == 1
        assert result["chapters"][0]["chapter_id"] == 1

    @pytest.mark.asyncio
    async def test_parse_outline_fills_missing_fields(self, outline_agent):
        """测试解析会填充缺失字段"""
        incomplete_json = json.dumps({
            "chapters": [
                {"title": "第一章"},
                {}
            ]
        })

        result = outline_agent._parse_outline_response(incomplete_json)

        # 验证填充了缺失字段
        assert result["chapters"][0]["chapter_id"] == 1
        assert result["chapters"][0]["summary"] == ""
        assert result["chapters"][0]["key_events"] == []

        assert result["chapters"][1]["chapter_id"] == 2
        assert result["chapters"][1]["title"] == "第2章"

    @pytest.mark.asyncio
    async def test_create_default_outline(self, outline_agent):
        """测试创建默认大纲"""
        task = "创作一个科幻故事"

        result = outline_agent._create_default_outline(task)

        assert "chapters" in result
        assert len(result["chapters"]) == 3
        assert result["title"] == "未命名故事"
        assert result["core_theme"] == task

    @pytest.mark.asyncio
    async def test_handle_llm_error(self, outline_agent, initial_state):
        """测试处理LLM错误"""
        # Mock LLM抛出异常
        with patch.object(outline_agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.side_effect = Exception("LLM调用失败")

            # 执行
            result_state = await outline_agent.execute(initial_state)

            # 验证错误被捕获
            assert len(result_state.get("errors", [])) > 0
            assert "OutlineAgent error" in result_state["errors"][0]
            assert result_state.get("current_step") == "error"

    @pytest.mark.asyncio
    async def test_handle_json_parse_error(self, outline_agent, initial_state):
        """测试处理JSON解析错误"""
        # Mock LLM返回无效JSON
        mock_response = Mock()
        mock_response.content = "这不是有效的JSON"

        with patch.object(outline_agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = mock_response

            # 执行
            result_state = await outline_agent.execute(initial_state)

            # 验证返回了默认大纲
            assert "outline_agent" in result_state.get("agent_outputs", {})
            outline_output = result_state["agent_outputs"]["outline_agent"]
            assert outline_output["title"] == "未命名故事"
            assert len(outline_output["chapters"]) == 3

    @pytest.mark.asyncio
    async def test_execution_time_tracking(self, outline_agent, initial_state, mock_llm_response):
        """测试执行时间追踪"""
        with patch.object(outline_agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = mock_llm_response

            # 执行
            result_state = await outline_agent.execute(initial_state)

            # 验证执行时间被记录
            assert "agent_execution_times" in result_state
            assert "outline_agent" in result_state["agent_execution_times"]
            assert result_state["agent_execution_times"]["outline_agent"] > 0


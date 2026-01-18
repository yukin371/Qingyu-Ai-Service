"""
PlotAgent测试
"""
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch

from agents.specialized.plot_agent import PlotAgent
from agents.states.pipeline_state_v2 import create_initial_pipeline_state_v2


class TestPlotAgent:
    """PlotAgent测试类"""

    @pytest.fixture
    def plot_agent(self):
        """创建PlotAgent实例"""
        return PlotAgent(llm_provider="gemini", temperature=0.7)

    @pytest.fixture
    def initial_state_with_outline_and_characters(self):
        """创建包含大纲和角色的初始状态"""
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
                        "summary": "主角李云遭受冷眼，意外获得功法",
                        "characters_involved": ["李云", "家主"]
                    },
                    {
                        "chapter_id": 2,
                        "title": "初露锋芒",
                        "summary": "李云参加宗门考核，击败对手",
                        "characters_involved": ["李云", "张三"]
                    }
                ]
            },
            "character_agent": {
                "characters": [
                    {
                        "character_id": "char_001",
                        "name": "李云",
                        "role_type": "protagonist",
                        "motivation": "证明自己，改变命运",
                        "relationships": [
                            {
                                "character": "张三",
                                "relation_type": "rival"
                            }
                        ]
                    },
                    {
                        "character_id": "char_002",
                        "name": "张三",
                        "role_type": "antagonist",
                        "motivation": "打压李云"
                    }
                ],
                "relationship_network": {
                    "conflicts": [["李云", "张三"]]
                }
            }
        }

        state["outline_nodes"] = state["agent_outputs"]["outline_agent"]["chapters"]
        state["characters"] = state["agent_outputs"]["character_agent"]["characters"]

        return state

    @pytest.fixture
    def mock_llm_response(self):
        """Mock LLM响应"""
        plot_json = {
            "timeline_events": [
                {
                    "event_id": "evt_001",
                    "timestamp": "第1章",
                    "location": "李家",
                    "title": "家族试炼失败",
                    "description": "李云在家族试炼中表现不佳，遭受冷眼和嘲讽，内心痛苦但仍坚持。",
                    "participants": ["李云", "家主"],
                    "event_type": "铺垫",
                    "impact": {
                        "on_plot": "引入主角困境，为后续发展铺垫",
                        "on_characters": {
                            "李云": "激发改变命运的强烈动机"
                        },
                        "emotional_impact": "压抑、沮丧"
                    },
                    "causes": [],
                    "consequences": ["evt_002"],
                    "chapter_id": 1
                },
                {
                    "event_id": "evt_002",
                    "timestamp": "第1章",
                    "location": "神秘洞府",
                    "title": "获得神秘功法",
                    "description": "李云意外发现神秘洞府，获得古老功法，命运转折点。",
                    "participants": ["李云"],
                    "event_type": "转折",
                    "impact": {
                        "on_plot": "主线开启，主角获得改变命运的机会",
                        "on_characters": {
                            "李云": "从绝望到希望，开启修炼之路"
                        },
                        "emotional_impact": "惊喜、兴奋"
                    },
                    "causes": ["evt_001"],
                    "consequences": ["evt_003"],
                    "chapter_id": 1
                },
                {
                    "event_id": "evt_003",
                    "timestamp": "第2章",
                    "location": "宗门考核场",
                    "title": "击败张三",
                    "description": "李云在宗门考核中展现实力，击败曾经嘲笑他的张三，一鸣惊人。",
                    "participants": ["李云", "张三"],
                    "event_type": "冲突",
                    "impact": {
                        "on_plot": "主角初露锋芒，引起注意",
                        "on_characters": {
                            "李云": "自信心提升，证明自己",
                            "张三": "嫉妒加深，仇恨产生"
                        },
                        "emotional_impact": "激动、紧张"
                    },
                    "causes": ["evt_002"],
                    "consequences": [],
                    "chapter_id": 2
                }
            ],
            "plot_threads": [
                {
                    "thread_id": "thread_main",
                    "title": "主线：废材逆袭",
                    "description": "李云从家族废材到修仙天才的成长之路",
                    "type": "main",
                    "events": ["evt_001", "evt_002", "evt_003"],
                    "starting_event": "evt_001",
                    "climax_event": "evt_003",
                    "characters_involved": ["李云"]
                }
            ],
            "conflicts": [
                {
                    "conflict_id": "conflict_001",
                    "type": "人物冲突",
                    "parties": ["李云", "张三"],
                    "description": "李云与张三的竞争对抗",
                    "escalation_events": ["evt_003"],
                    "resolution_event": None
                }
            ],
            "key_plot_points": {
                "inciting_incident": "evt_001",
                "plot_point_1": "evt_002",
                "midpoint": "evt_003"
            }
        }

        mock_response = Mock()
        mock_response.content = json.dumps(plot_json, ensure_ascii=False)
        return mock_response

    @pytest.mark.asyncio
    async def test_plot_agent_initialization(self, plot_agent):
        """测试PlotAgent初始化"""
        assert plot_agent.name == "PlotAgent"
        assert plot_agent.version == "v1.0"
        assert plot_agent.llm is not None

    @pytest.mark.asyncio
    async def test_generate_plot_basic(
        self, plot_agent, initial_state_with_outline_and_characters, mock_llm_response
    ):
        """测试基础情节生成"""
        with patch.object(plot_agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = mock_llm_response

            # 执行
            result_state = await plot_agent.execute(initial_state_with_outline_and_characters)

            # 验证
            assert "errors" not in result_state or len(result_state["errors"]) == 0
            assert "plot_agent" in result_state.get("agent_outputs", {})

            plot_output = result_state["agent_outputs"]["plot_agent"]
            assert "timeline_events" in plot_output
            assert "plot_threads" in plot_output
            assert len(plot_output["timeline_events"]) == 3

            # 验证时间线事件
            first_event = plot_output["timeline_events"][0]
            assert first_event["event_id"] == "evt_001"
            assert "李云" in first_event["participants"]

            # 验证timeline_events字段也被更新
            assert len(result_state.get("timeline_events", [])) == 3

            # 验证下一步设置为review
            assert result_state.get("current_step") == "review"

    @pytest.mark.asyncio
    async def test_generate_plot_with_outline_and_characters(
        self, plot_agent, initial_state_with_outline_and_characters, mock_llm_response
    ):
        """测试使用大纲和角色信息生成情节"""
        with patch.object(plot_agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = mock_llm_response

            # 执行
            result_state = await plot_agent.execute(initial_state_with_outline_and_characters)

            # 验证调用了LLM
            assert mock_ainvoke.called
            call_args = mock_ainvoke.call_args[0][0]
            user_message = call_args[1].content

            # 验证用户消息包含大纲和角色信息
            assert "故事大纲" in user_message
            assert "仙途之路" in user_message
            assert "角色信息" in user_message
            assert "李云" in user_message
            assert "张三" in user_message

    @pytest.mark.asyncio
    async def test_generate_plot_with_correction(
        self, plot_agent, initial_state_with_outline_and_characters, mock_llm_response
    ):
        """测试带修正提示词的情节生成"""
        # 添加修正提示词
        initial_state_with_outline_and_characters["correction_prompts"] = {
            "plot_agent": "请增加更多悬念，在第一章结尾设置一个重大转折"
        }

        with patch.object(plot_agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = mock_llm_response

            # 执行
            result_state = await plot_agent.execute(initial_state_with_outline_and_characters)

            # 验证用户消息包含修正提示词
            call_args = mock_ainvoke.call_args[0][0]
            user_message = call_args[1].content
            assert "修正要求" in user_message
            assert "悬念" in user_message

    @pytest.mark.asyncio
    async def test_parse_plot_fills_missing_fields(self, plot_agent):
        """测试解析会填充缺失字段"""
        incomplete_json = json.dumps({
            "timeline_events": [
                {"title": "事件1"},
                {}
            ]
        })

        result = plot_agent._parse_plot_response(incomplete_json)

        # 验证填充了缺失字段
        assert result["timeline_events"][0]["event_id"] == "evt_001"
        assert result["timeline_events"][0]["description"] == ""
        assert result["timeline_events"][0]["participants"] == []

        assert result["timeline_events"][1]["event_id"] == "evt_002"
        assert result["timeline_events"][1]["title"] == "事件2"

        # 验证plot_threads被添加
        assert "plot_threads" in result

    @pytest.mark.asyncio
    async def test_create_default_plot(self, plot_agent):
        """测试创建默认情节"""
        outline_output = {
            "title": "测试故事",
            "chapters": [
                {"chapter_id": 1, "title": "第一章", "summary": "开始"}
            ]
        }
        character_output = {
            "characters": [{"name": "主角"}]
        }

        result = plot_agent._create_default_plot("测试任务", outline_output, character_output)

        assert "timeline_events" in result
        assert "plot_threads" in result
        assert len(result["timeline_events"]) == 1

    @pytest.mark.asyncio
    async def test_plot_threads_structure(
        self, plot_agent, initial_state_with_outline_and_characters, mock_llm_response
    ):
        """测试情节线索结构"""
        with patch.object(plot_agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = mock_llm_response

            # 执行
            result_state = await plot_agent.execute(initial_state_with_outline_and_characters)

            plot_output = result_state["agent_outputs"]["plot_agent"]

            # 验证情节线索
            assert len(plot_output["plot_threads"]) > 0
            main_thread = plot_output["plot_threads"][0]
            assert main_thread["thread_id"] == "thread_main"
            assert main_thread["type"] == "main"
            assert len(main_thread["events"]) == 3

    @pytest.mark.asyncio
    async def test_conflicts_structure(
        self, plot_agent, initial_state_with_outline_and_characters, mock_llm_response
    ):
        """测试冲突结构"""
        with patch.object(plot_agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = mock_llm_response

            # 执行
            result_state = await plot_agent.execute(initial_state_with_outline_and_characters)

            plot_output = result_state["agent_outputs"]["plot_agent"]

            # 验证冲突
            assert "conflicts" in plot_output
            assert len(plot_output["conflicts"]) > 0
            conflict = plot_output["conflicts"][0]
            assert "李云" in conflict["parties"]
            assert "张三" in conflict["parties"]

    @pytest.mark.asyncio
    async def test_handle_llm_error(
        self, plot_agent, initial_state_with_outline_and_characters
    ):
        """测试处理LLM错误"""
        with patch.object(plot_agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.side_effect = Exception("LLM调用失败")

            # 执行
            result_state = await plot_agent.execute(initial_state_with_outline_and_characters)

            # 验证错误被捕获
            assert len(result_state.get("errors", [])) > 0
            assert "PlotAgent error" in result_state["errors"][0]
            assert result_state.get("current_step") == "error"

    @pytest.mark.asyncio
    async def test_handle_json_parse_error(
        self, plot_agent, initial_state_with_outline_and_characters
    ):
        """测试处理JSON解析错误"""
        mock_response = Mock()
        mock_response.content = "这不是有效的JSON"

        with patch.object(plot_agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = mock_response

            # 执行
            result_state = await plot_agent.execute(initial_state_with_outline_and_characters)

            # 验证返回了默认情节
            assert "plot_agent" in result_state.get("agent_outputs", {})
            plot_output = result_state["agent_outputs"]["plot_agent"]
            assert "timeline_events" in plot_output
            assert "plot_threads" in plot_output

    @pytest.mark.asyncio
    async def test_execution_time_tracking(
        self, plot_agent, initial_state_with_outline_and_characters, mock_llm_response
    ):
        """测试执行时间追踪"""
        with patch.object(plot_agent.llm, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
            mock_ainvoke.return_value = mock_llm_response

            # 执行
            result_state = await plot_agent.execute(initial_state_with_outline_and_characters)

            # 验证执行时间被记录
            assert "agent_execution_times" in result_state
            assert "plot_agent" in result_state["agent_execution_times"]
            assert result_state["agent_execution_times"]["plot_agent"] > 0


"""
事实提取 Agent 测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestFactExtractionAgent:
    """FactExtractionAgent 测试"""

    def test_agent_initialization(self):
        """测试 Agent 初始化"""
        from src.agents.specialized.fact_extraction_agent import FactExtractionAgent

        agent = FactExtractionAgent(temperature=0.3)

        assert agent.name == "FactExtractionAgent"
        assert agent.version == "v1.0"
        assert agent.llm is not None

    def test_parse_json_response_valid(self):
        """测试 JSON 解析 - 有效输入"""
        from src.agents.specialized.fact_extraction_agent import FactExtractionAgent

        agent = FactExtractionAgent()

        content = '''
        {
          "state_changes": [
            {
              "entity_name": "张三",
              "field_key": "恐惧值",
              "old_value": 30,
              "new_value": 80,
              "evidence": "张三的恐惧值飙升到80%"
            }
          ],
          "relation_changes": [],
          "new_entities": [
            {
              "name": "李四",
              "entity_type": "character",
              "first_mention": "李四递给他一瓶水",
              "description": null
            }
          ],
          "events": []
        }
        '''

        result = agent._parse_json_response(content)

        assert len(result.state_changes) == 1
        assert result.state_changes[0].entity_name == "张三"
        assert result.state_changes[0].field_key == "恐惧值"
        assert result.state_changes[0].new_value == 80

        assert len(result.new_entities) == 1
        assert result.new_entities[0].name == "李四"
        assert result.new_entities[0].entity_type == "character"

    def test_parse_json_response_with_json_block(self):
        """测试 JSON 解析 - 带代码块"""
        from src.agents.specialized.fact_extraction_agent import FactExtractionAgent

        agent = FactExtractionAgent()

        content = '''
        好的，这是提取结果：
        ```json
        {
          "state_changes": [
            {
              "entity_name": "亚伯",
              "field_key": "恐惧值",
              "old_value": 30,
              "new_value": 60,
              "evidence": "亚伯的恐惧值飙升到60%"
            }
          ],
          "relation_changes": [],
          "new_entities": [],
          "events": []
        }
        ```
        '''

        result = agent._parse_json_response(content)

        assert len(result.state_changes) == 1
        assert result.state_changes[0].entity_name == "亚伯"
        assert result.state_changes[0].new_value == 60

    def test_parse_json_response_invalid(self):
        """测试 JSON 解析 - 无效输入"""
        from src.agents.specialized.fact_extraction_agent import FactExtractionAgent

        agent = FactExtractionAgent()

        result = agent._parse_json_response("这不是有效的JSON")

        assert len(result.state_changes) == 0
        assert len(result.relation_changes) == 0
        assert len(result.new_entities) == 0

    def test_parse_json_response_empty(self):
        """测试 JSON 解析 - 空数组"""
        from src.agents.specialized.fact_extraction_agent import FactExtractionAgent

        agent = FactExtractionAgent()

        content = '''
        {
          "state_changes": [],
          "relation_changes": [],
          "new_entities": [],
          "events": []
        }
        '''

        result = agent._parse_json_response(content)

        assert len(result.state_changes) == 0
        assert len(result.relation_changes) == 0
        assert len(result.new_entities) == 0
        assert len(result.events) == 0

    def test_to_change_requests_state_change(self):
        """测试转换为 Change Request - 状态变更"""
        from src.agents.specialized.fact_extraction_agent import FactExtractionAgent
        from src.api.models.fact_extraction import ExtractionResult, StateChange

        agent = FactExtractionAgent()

        extraction = ExtractionResult(
            state_changes=[
                StateChange(
                    entity_name="张三",
                    field_key="恐惧值",
                    old_value=30,
                    new_value=80,
                    evidence="张三的恐惧值飙升到80%"
                )
            ],
            relation_changes=[],
            new_entities=[],
            events=[]
        )

        crs = agent.to_change_requests(extraction, "project-1", "chapter-1")

        assert len(crs) == 1
        assert crs[0]["project_id"] == "project-1"
        assert crs[0]["chapter_id"] == "chapter-1"
        assert crs[0]["category"] == "entity_state"
        assert crs[0]["title"] == "建议更新 张三 的 恐惧值"
        assert crs[0]["suggested_change"]["field_key"] == "恐惧值"
        assert crs[0]["suggested_change"]["new_value"] == 80

    def test_to_change_requests_new_entity(self):
        """测试转换为 Change Request - 新实体"""
        from src.agents.specialized.fact_extraction_agent import FactExtractionAgent
        from src.api.models.fact_extraction import ExtractionResult, NewEntityMention

        agent = FactExtractionAgent()

        extraction = ExtractionResult(
            state_changes=[],
            relation_changes=[],
            new_entities=[
                NewEntityMention(
                    name="神秘物品",
                    entity_type="item",
                    first_mention="一个发光的盒子",
                    description="神秘的发光盒子"
                )
            ],
            events=[]
        )

        crs = agent.to_change_requests(extraction, "project-1", "chapter-1")

        assert len(crs) == 1
        assert crs[0]["category"] == "new_entity"
        assert crs[0]["entity_name"] == "神秘物品"
        assert crs[0]["suggested_change"]["entity_type"] == "item"

    def test_to_change_requests_relation_change(self):
        """测试转换为 Change Request - 关系变更"""
        from src.agents.specialized.fact_extraction_agent import FactExtractionAgent
        from src.api.models.fact_extraction import ExtractionResult, RelationChange

        agent = FactExtractionAgent()

        extraction = ExtractionResult(
            state_changes=[],
            relation_changes=[
                RelationChange(
                    from_entity="张三",
                    to_entity="李四",
                    relation_type="朋友",
                    change_type="new",
                    evidence="他们交换了一个眼神"
                )
            ],
            new_entities=[],
            events=[]
        )

        crs = agent.to_change_requests(extraction, "project-1", "chapter-1")

        assert len(crs) == 1
        assert crs[0]["category"] == "relation_change"
        assert crs[0]["suggested_change"]["from_entity"] == "张三"
        assert crs[0]["suggested_change"]["to_entity"] == "李四"
        assert crs[0]["suggested_change"]["change_type"] == "new"


class TestFactExtractionModels:
    """事实提取数据模型测试"""

    def test_state_change_model(self):
        """测试 StateChange 模型"""
        from src.api.models.fact_extraction import StateChange

        sc = StateChange(
            entity_name="张三",
            field_key="恐惧值",
            old_value=30,
            new_value=80,
            evidence="恐惧值飙升"
        )

        assert sc.entity_name == "张三"
        assert sc.field_key == "恐惧值"
        assert sc.old_value == 30
        assert sc.new_value == 80

    def test_extraction_result_model(self):
        """测试 ExtractionResult 模型"""
        from src.api.models.fact_extraction import (
            ExtractionResult,
            StateChange,
            NewEntityMention,
        )

        result = ExtractionResult(
            state_changes=[
                StateChange(
                    entity_name="张三",
                    field_key="心情",
                    old_value="平静",
                    new_value="紧张",
                    evidence="张三的心情变得紧张"
                )
            ],
            new_entities=[
                NewEntityMention(
                    name="李四",
                    entity_type="character",
                    first_mention="李四出现",
                    description=None
                )
            ]
        )

        assert len(result.state_changes) == 1
        assert len(result.new_entities) == 1
        assert result.new_entities[0].name == "李四"

    def test_analyze_chapter_request(self):
        """测试 AnalyzeChapterRequest 模型"""
        from src.api.models.fact_extraction import AnalyzeChapterRequest

        request = AnalyzeChapterRequest(
            project_id="proj-1",
            chapter_id="ch-1",
            text="这是一段测试文本",
            existing_entities=[
                {"name": "张三", "entity_type": "character"}
            ]
        )

        assert request.project_id == "proj-1"
        assert len(request.existing_entities) == 1


class TestFactExtractionPrompts:
    """Prompt 模板测试"""

    def test_system_prompt_not_empty(self):
        """测试系统提示不为空"""
        from src.agents.specialized.fact_extraction_prompts import (
            FACT_EXTRACTION_SYSTEM_PROMPT,
        )

        assert len(FACT_EXTRACTION_SYSTEM_PROMPT) > 0
        assert "state_changes" in FACT_EXTRACTION_SYSTEM_PROMPT
        assert "relation_changes" in FACT_EXTRACTION_SYSTEM_PROMPT
        assert "new_entities" in FACT_EXTRACTION_SYSTEM_PROMPT

    def test_user_prompt_format(self):
        """测试用户提示格式"""
        from src.agents.specialized.fact_extraction_prompts import (
            FACT_EXTRACTION_USER_PROMPT,
        )

        prompt = FACT_EXTRACTION_USER_PROMPT.format(
            text="测试文本",
            existing_entities="张三（character）"
        )

        assert "测试文本" in prompt
        assert "张三（character）" in prompt

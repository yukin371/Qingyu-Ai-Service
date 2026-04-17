"""
章节一致性检查 Agent 测试
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestConsistencyAgent:
    """ConsistencyAgent 测试"""

    def test_agent_initialization(self):
        """测试 Agent 初始化"""
        from src.agents.specialized.consistency_agent import ConsistencyAgent

        with patch(
            "src.agents.specialized.consistency_agent.LLMFactory.create_llm"
        ) as mock_factory:
            mock_factory.return_value = MagicMock()
            agent = ConsistencyAgent(temperature=0.2)

        assert agent.name == "ConsistencyAgent"
        assert agent.version == "v1.0"
        assert agent.llm is not None

    def test_agent_uses_default_provider_model_when_unspecified(self):
        """未显式传入 provider/model 时应对齐已配置默认值"""
        from src.agents.specialized import consistency_agent
        from src.agents.specialized.consistency_agent import ConsistencyAgent

        with (
            patch.object(consistency_agent.settings, "default_llm_provider", "deepseek"),
            patch.object(consistency_agent.settings, "deepseek_api_key", "sk-live"),
            patch.object(consistency_agent.settings, "deepseek_model", "deepseek-chat"),
            patch(
                "src.agents.specialized.consistency_agent.LLMFactory.create_llm"
            ) as mock_factory,
        ):
            mock_factory.return_value = MagicMock()
            ConsistencyAgent()

        mock_factory.assert_called_once_with(
            provider="deepseek",
            model="deepseek-chat",
            temperature=0.2,
        )

    def test_agent_falls_back_when_gemini_key_is_placeholder(self):
        """Gemini key 不可用时应回退到可用 provider，而不是继续走无效配置"""
        from src.agents.specialized import consistency_agent
        from src.agents.specialized.consistency_agent import ConsistencyAgent

        with (
            patch.object(consistency_agent.settings, "default_llm_provider", "deepseek"),
            patch.object(consistency_agent.settings, "default_llm_model", "deepseek-chat"),
            patch.object(consistency_agent.settings, "google_api_key", "xxx"),
            patch.object(consistency_agent.settings, "deepseek_api_key", "sk-live"),
            patch.object(consistency_agent.settings, "deepseek_model", "deepseek-chat"),
            patch(
                "src.agents.specialized.consistency_agent.LLMFactory.create_llm"
            ) as mock_factory,
        ):
            mock_factory.return_value = MagicMock()
            agent = ConsistencyAgent(llm_provider="gemini")

        assert agent.llm_provider == "deepseek"
        assert agent.llm_model == "deepseek-chat"
        mock_factory.assert_called_once_with(
            provider="deepseek",
            model="deepseek-chat",
            temperature=0.2,
        )

    def test_parse_json_response_valid(self):
        """测试 JSON 解析"""
        from src.agents.specialized.consistency_agent import ConsistencyAgent

        with patch(
            "src.agents.specialized.consistency_agent.LLMFactory.create_llm"
        ) as mock_factory:
            mock_factory.return_value = MagicMock()
            agent = ConsistencyAgent()

        content = """
        {
          "passed": false,
          "summary": "检测到 1 条一致性问题",
          "issues": [
            {
              "id": "issue-1",
              "severity": "high",
              "category": "consistency",
              "issue_type": "timeline_conflict",
              "title": "昼夜冲突",
              "description": "上一章仍是清晨，本章直接写成深夜且无过渡",
              "evidence": "夜色已经彻底吞没街道",
              "suggestion": "补充时间推进说明",
              "affected_entities": ["第一章", "第二章"],
              "metadata": {
                "dimension": "timeline"
              }
            }
          ]
        }
        """

        result = agent._parse_json_response(content)

        assert result.passed is False
        assert len(result.issues) == 1
        assert result.issues[0].issue_type == "timeline_conflict"
        assert result.issues[0].severity.value == "high"

    @pytest.mark.asyncio
    async def test_analyze_chapter(self):
        """测试章节一致性检查主流程"""
        from src.agents.specialized.consistency_agent import ConsistencyAgent

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(
            return_value=MagicMock(
                content="""
                {
                  "passed": false,
                  "summary": "检测到 1 条一致性问题",
                  "issues": [
                    {
                      "id": "issue-1",
                      "severity": "medium",
                      "category": "consistency",
                      "issue_type": "character_state_conflict",
                      "title": "情绪跳变",
                      "description": "角色前文仍处于恐惧状态，本章突然完全轻松",
                      "evidence": "她笑着说自己一点也不害怕",
                      "suggestion": "补充情绪转折原因",
                      "affected_entities": ["诺艾尔"],
                      "metadata": {}
                    }
                  ]
                }
                """
            )
        )

        with patch(
            "src.agents.specialized.consistency_agent.LLMFactory.create_llm",
            return_value=mock_llm,
        ):
            agent = ConsistencyAgent()
            result = await agent.analyze_chapter(
                project_id="project-1",
                chapter_id="chapter-2",
                text="诺艾尔笑着说自己一点也不害怕。",
                previous_chapters=[
                    {
                        "chapter_id": "chapter-1",
                        "title": "第一章",
                        "summary": "诺艾尔在深夜里非常恐惧。",
                        "key_events": ["诺艾尔目睹异象"],
                        "time_markers": ["深夜"],
                    }
                ],
                existing_entities=[
                    {
                        "name": "诺艾尔",
                        "entity_type": "character",
                        "current_state": "恐惧",
                        "state_fields": {"情绪": "恐惧"},
                    }
                ],
            )

        assert result.passed is False
        assert len(result.issues) == 1
        assert result.summary == "检测到 1 条一致性问题"

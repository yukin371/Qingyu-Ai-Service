"""
ConsistencyAgent - 章节一致性检查 Agent

输入当前章节正文、前序章节摘要和已知实体状态，输出结构化一致性问题列表。
"""
import json
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.base_agent_v2 import BaseAgentV2
from src.agents.states.pipeline_state_v2 import PipelineStateV2
from src.api.models.chapter_analysis import (
    ConsistencyCheckResponse,
    ConsistencyIssue,
    PreviousChapterSummary,
)
from src.core.config import settings
from src.core.logger import get_logger
from src.llm.llm_factory import LLMFactory

logger = get_logger(__name__)


CONSISTENCY_SYSTEM_PROMPT = """你是小说章节一致性检查助手。

你的任务是根据：
1. 当前章节正文
2. 前序章节摘要
3. 当前已知实体与状态

输出结构化的一致性问题列表，重点只检查以下几类问题：
- 角色状态矛盾
- 时间线冲突
- 关系逻辑断裂

要求：
1. 只输出 JSON，不要输出额外说明
2. 如果没有发现明确问题，返回空数组并将 passed 设为 true
3. 不要凭空补充剧情，只基于输入内容

输出格式：
{
  "passed": false,
  "summary": "检测到 2 条一致性问题",
  "issues": [
    {
      "id": "issue-1",
      "severity": "high",
      "category": "consistency",
      "issue_type": "character_state_conflict",
      "title": "角色状态矛盾",
      "description": "上一章仍处于恐惧状态，本章突然完全镇定且无解释",
      "evidence": "角色笑着说自己一直都很放松",
      "suggestion": "补充状态过渡或调整当前描写",
      "affected_entities": ["诺艾尔"],
      "metadata": {
        "dimension": "emotion"
      }
    }
  ]
}
"""


CONSISTENCY_USER_PROMPT = """请检查以下章节的一致性。

项目ID：{project_id}
章节ID：{chapter_id}

前序章节摘要：
{previous_chapters}

当前已知实体与状态：
{existing_entities}

当前章节正文：
---
{text}
---

请输出 JSON 结果：
"""


_PLACEHOLDER_API_KEYS = {
    "",
    "xxx",
    "your-api-key",
    "change-me-in-production",
    "sk-xxx",
}


def _has_usable_api_key(raw_value: str | None) -> bool:
    normalized = (raw_value or "").strip()
    if not normalized:
        return False

    return normalized.lower() not in _PLACEHOLDER_API_KEYS


def _default_model_for_provider(provider: str) -> str:
    provider = (provider or "").strip().lower()
    if provider == "openai":
        return settings.openai_model
    if provider == "anthropic":
        return settings.anthropic_model
    if provider == "gemini":
        return settings.gemini_model
    if provider == "zhipu":
        return settings.zhipu_model
    if provider == "deepseek":
        return settings.deepseek_model
    return settings.default_llm_model


def _provider_has_credentials(provider: str) -> bool:
    provider = (provider or "").strip().lower()
    if provider == "openai":
        return _has_usable_api_key(settings.openai_api_key)
    if provider == "anthropic":
        return _has_usable_api_key(settings.anthropic_api_key)
    if provider == "gemini":
        return _has_usable_api_key(settings.google_api_key)
    if provider == "zhipu":
        return _has_usable_api_key(settings.zhipu_api_key)
    if provider == "deepseek":
        return _has_usable_api_key(settings.deepseek_api_key)
    return False


def _pick_available_provider(*providers: str) -> str | None:
    for provider in providers:
        normalized = (provider or "").strip().lower()
        if normalized and _provider_has_credentials(normalized):
            return normalized
    return None


def _resolve_llm_config(
    llm_provider: str | None,
    llm_model: str | None,
) -> tuple[str, str]:
    requested_provider = (
        (llm_provider or "").strip().lower()
        or (settings.default_llm_provider or "").strip().lower()
        or "gemini"
    )

    resolved_provider = requested_provider
    if not _provider_has_credentials(resolved_provider):
        fallback_provider = _pick_available_provider(
            (settings.default_llm_provider or "").strip().lower(),
            "deepseek",
            "zhipu",
            "openai",
            "anthropic",
            "gemini",
        )
        if fallback_provider and fallback_provider != resolved_provider:
            logger.warning(
                "consistency_agent_provider_fallback",
                requested_provider=resolved_provider,
                fallback_provider=fallback_provider,
            )
            resolved_provider = fallback_provider

    resolved_model = (llm_model or "").strip() or _default_model_for_provider(resolved_provider)
    return resolved_provider, resolved_model


class ConsistencyAgent(BaseAgentV2):
    """章节一致性检查 Agent"""

    def __init__(
        self,
        llm_provider: str | None = None,
        llm_model: str | None = None,
        temperature: float = 0.2,
        **kwargs,
    ):
        super().__init__(
            name="ConsistencyAgent",
            description="检查章节级角色状态、时间线和关系逻辑一致性",
            version="v1.0",
        )
        resolved_provider, resolved_model = _resolve_llm_config(llm_provider, llm_model)
        self.llm_provider = resolved_provider
        self.llm_model = resolved_model
        self.llm = LLMFactory.create_llm(
            provider=resolved_provider,
            model=resolved_model,
            temperature=temperature,
        )
        self.config = kwargs

    def get_runnable(self) -> Any:
        """获取可执行链"""
        from langchain_core.runnables import RunnableLambda

        async def run(state: PipelineStateV2) -> PipelineStateV2:
            request = state.get("consistency_request", {})
            result = await self.analyze_chapter(
                project_id=request.get("project_id", ""),
                chapter_id=request.get("chapter_id", ""),
                text=request.get("text", ""),
                previous_chapters=request.get("previous_chapters", []),
                existing_entities=request.get("existing_entities", []),
            )
            state["consistency_result"] = result.model_dump()
            return state

        return RunnableLambda(run)

    async def execute(self, state: PipelineStateV2) -> PipelineStateV2:
        """执行章节一致性检查"""
        request = state.get("consistency_request", {})
        result = await self.analyze_chapter(
            project_id=request.get("project_id", ""),
            chapter_id=request.get("chapter_id", ""),
            text=request.get("text", ""),
            previous_chapters=request.get("previous_chapters", []),
            existing_entities=request.get("existing_entities", []),
        )
        state["consistency_result"] = result.model_dump()
        return state

    async def analyze_chapter(
        self,
        project_id: str,
        chapter_id: str,
        text: str,
        previous_chapters: List[PreviousChapterSummary | Dict[str, Any]],
        existing_entities: List[Dict[str, Any]],
    ) -> ConsistencyCheckResponse:
        """检查章节一致性"""
        logger.info(
            "chapter_consistency_started",
            project_id=project_id,
            chapter_id=chapter_id,
            previous_chapters=len(previous_chapters),
            existing_entities=len(existing_entities),
            text_length=len(text),
        )

        prompt = CONSISTENCY_USER_PROMPT.format(
            project_id=project_id,
            chapter_id=chapter_id,
            previous_chapters=self._format_previous_chapters(previous_chapters),
            existing_entities=self._format_existing_entities(existing_entities),
            text=text,
        )

        response = await self.llm.ainvoke(
            [
                SystemMessage(content=CONSISTENCY_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        )
        result = self._parse_json_response(response.content)

        logger.info(
            "chapter_consistency_completed",
            project_id=project_id,
            chapter_id=chapter_id,
            issues=len(result.issues),
            passed=result.passed,
        )
        return result

    def _format_previous_chapters(
        self, previous_chapters: List[PreviousChapterSummary | Dict[str, Any]]
    ) -> str:
        if not previous_chapters:
            return "（无前序章节摘要）"

        formatted: List[str] = []
        for chapter in previous_chapters:
            if isinstance(chapter, dict):
                title = chapter.get("title") or chapter.get("chapter_id") or "未命名章节"
                summary = chapter.get("summary", "")
                key_events = chapter.get("key_events", [])
                time_markers = chapter.get("time_markers", [])
            else:
                title = chapter.title or chapter.chapter_id
                summary = chapter.summary
                key_events = chapter.key_events
                time_markers = chapter.time_markers

            parts = [f"- {title}: {summary}"]
            if key_events:
                parts.append(f"  关键事件：{'；'.join(key_events)}")
            if time_markers:
                parts.append(f"  时间标记：{'；'.join(time_markers)}")
            formatted.append("\n".join(parts))

        return "\n".join(formatted)

    def _format_existing_entities(self, existing_entities: List[Dict[str, Any]]) -> str:
        if not existing_entities:
            return "（无已知实体）"

        formatted: List[str] = []
        for entity in existing_entities:
            name = entity.get("name", "unknown")
            entity_type = entity.get("entity_type", "unknown")
            state_fields = entity.get("state_fields") or {}
            current_state = entity.get("current_state")
            relations = entity.get("relations") or []

            parts = [f"- {name} ({entity_type})"]
            if current_state:
                parts.append(f"  当前状态：{current_state}")
            if state_fields:
                state_text = "；".join(
                    f"{key}={value}" for key, value in state_fields.items()
                )
                parts.append(f"  状态字段：{state_text}")
            if relations:
                parts.append(f"  关系：{'；'.join(map(str, relations[:5]))}")
            formatted.append("\n".join(parts))

        return "\n".join(formatted)

    def _parse_json_response(self, content: str) -> ConsistencyCheckResponse:
        try:
            json_str = self._extract_json_from_content(content)
            data = json.loads(json_str)
            issues = [
                ConsistencyIssue(**item) for item in data.get("issues", [])
            ]
            passed = data.get("passed", len(issues) == 0)
            summary = data.get("summary") or self._build_summary(passed, issues)
            return ConsistencyCheckResponse(
                passed=passed,
                issues=issues,
                summary=summary,
                usage={},
            )
        except json.JSONDecodeError as error:
            logger.warning(
                "consistency_json_parse_failed",
                error=str(error),
                content=content[:200],
            )
            return ConsistencyCheckResponse(
                passed=True,
                issues=[],
                summary="章节一致性结果解析失败，已回退为空问题结果",
                usage={},
            )

    def _extract_json_from_content(self, content: str) -> str:
        content = content.strip()
        if content.startswith("{"):
            return content
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end != -1:
                return content[start:end].strip()
        if "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            if end != -1:
                return content[start:end].strip()
        start = content.find("{")
        end = content.rfind("}") + 1
        if start != -1 and end > start:
            return content[start:end]
        return content

    def _build_summary(
        self, passed: bool, issues: List[ConsistencyIssue]
    ) -> str:
        if passed:
            return "未检测到明确的一致性问题"
        return f"检测到 {len(issues)} 条一致性问题"

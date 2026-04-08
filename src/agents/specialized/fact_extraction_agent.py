"""
FactExtractionAgent - 事实提取 Agent

从小说文本中提取结构化事实：
- 实体状态变化
- 关系变化
- 新实体出场
- 事件事实
"""
import json
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.base_agent_v2 import BaseAgentV2
from src.agents.states.pipeline_state_v2 import PipelineStateV2
from src.agents.specialized.fact_extraction_prompts import (
    FACT_EXTRACTION_SYSTEM_PROMPT,
    FACT_EXTRACTION_USER_PROMPT,
    CHAPTER_ANALYSIS_USER_PROMPT,
    EXTRACT_FACTS_USER_PROMPT,
    EXTRACT_FACTS_WITH_ENTITY_FILTER,
)
from src.api.models.fact_extraction import (
    ExtractionResult,
    StateChange,
    RelationChange,
    NewEntityMention,
    EventFact,
)
from src.core.logger import get_logger
from src.llm.llm_factory import LLMFactory

logger = get_logger(__name__)


class FactExtractionAgent(BaseAgentV2):
    """事实提取 Agent

    从小说文本中提取结构化事实信息。
    """

    def __init__(
        self,
        llm_provider: str = "gemini",
        llm_model: Optional[str] = None,
        temperature: float = 0.3,  # 事实提取需要低温度保证准确性
        **kwargs,
    ):
        """初始化 FactExtractionAgent

        Args:
            llm_provider: LLM 提供商
            llm_model: LLM 模型名称
            temperature: 温度参数（建议低温度）
        """
        super().__init__(
            name="FactExtractionAgent",
            description="从小说文本中提取结构化事实（状态变化、关系变化、新实体、事件）",
            version="v1.0",
        )
        self.llm = LLMFactory.create_llm(
            provider=llm_provider,
            model=llm_model,
            temperature=temperature,
        )
        self._chain = None

    def get_runnable(self) -> Any:
        """获取可执行链"""
        return self._build_chain()

    def _build_chain(self) -> Any:
        """构建 LangChain 执行链"""
        from langchain_core.runnables import RunnableLambda

        def extract_facts(state: PipelineStateV2) -> PipelineStateV2:
            text = state.get("text", "")
            existing_entities = state.get("existing_entities", [])

            result = self._extract_sync(text, existing_entities)
            state["extraction_result"] = result
            return state

        return RunnableLambda(extract_facts)

    async def execute(self, state: PipelineStateV2) -> PipelineStateV2:
        """执行事实提取"""
        text = state.get("text", "")
        existing_entities = state.get("existing_entities", [])

        result = await self._extract(text, existing_entities)
        state["extraction_result"] = result
        return state

    async def _extract(
        self, text: str, existing_entities: List[Dict[str, Any]]
    ) -> ExtractionResult:
        """执行事实提取（异步）"""
        logger.info("fact_extraction_started", text_length=len(text))

        # 构建实体列表文本
        entities_text = ""
        if existing_entities:
            entities_text = "\n".join(
                f"- {e.get('name', 'unknown')} ({e.get('entity_type', 'unknown')})"
                for e in existing_entities
            )
        else:
            entities_text = "（无已知实体）"

        # 构建提示
        prompt = FACT_EXTRACTION_USER_PROMPT.format(
            text=text,
            existing_entities=entities_text,
        )

        # 调用 LLM
        response = await self.llm.ainvoke(
            [SystemMessage(content=FACT_EXTRACTION_SYSTEM_PROMPT),
             HumanMessage(content=prompt)]
        )

        # 解析 JSON
        result = self._parse_json_response(response.content)
        logger.info(
            "fact_extraction_completed",
            state_changes=len(result.state_changes),
            relation_changes=len(result.relation_changes),
            new_entities=len(result.new_entities),
            events=len(result.events),
        )

        return result

    def _extract_sync(
        self, text: str, existing_entities: List[Dict[str, Any]]
    ) -> ExtractionResult:
        """执行事实提取（同步，用于 Runnable）"""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self._extract(text, existing_entities)
        )

    def _parse_json_response(self, content: str) -> ExtractionResult:
        """解析 LLM 返回的 JSON 内容"""
        try:
            # 尝试提取 JSON 块
            json_str = self._extract_json_from_content(content)
            data = json.loads(json_str)

            return ExtractionResult(
                state_changes=[
                    StateChange(**item) for item in data.get("state_changes", [])
                ],
                relation_changes=[
                    RelationChange(**item) for item in data.get("relation_changes", [])
                ],
                new_entities=[
                    NewEntityMention(**item) for item in data.get("new_entities", [])
                ],
                events=[
                    EventFact(**item) for item in data.get("events", [])
                ],
            )
        except json.JSONDecodeError as e:
            logger.warning("json_parse_failed", error=str(e), content=content[:200])
            return ExtractionResult()

    def _extract_json_from_content(self, content: str) -> str:
        """从内容中提取 JSON 块"""
        content = content.strip()

        # 如果直接是 JSON
        if content.startswith("{"):
            return content

        # 尝试从 ```json 块中提取
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end != -1:
                return content[start:end].strip()

        # 尝试从 ``` 块中提取
        if "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            if end != -1:
                return content[start:end].strip()

        # 尝试找到第一个 { 和最后一个 }
        start = content.find("{")
        end = content.rfind("}") + 1
        if start != -1 and end > start:
            return content[start:end]

        return content

    async def extract_for_chapter(
        self,
        project_id: str,
        chapter_id: str,
        text: str,
        existing_entities: List[Dict[str, Any]],
    ) -> ExtractionResult:
        """提取章节事实（带项目上下文）"""
        logger.info(
            "chapter_fact_extraction_started",
            project_id=project_id,
            chapter_id=chapter_id,
            text_length=len(text),
        )

        # 构建实体列表
        entities_text = ""
        if existing_entities:
            entities_text = "\n".join(
                f"- {e.get('name', 'unknown')} ({e.get('entity_type', 'unknown')})"
                for e in existing_entities
            )
        else:
            entities_text = "（无已知实体）"

        # 构建提示
        prompt = CHAPTER_ANALYSIS_USER_PROMPT.format(
            project_id=project_id,
            chapter_id=chapter_id,
            existing_entities=entities_text,
            text=text,
        )

        # 调用 LLM
        response = await self.llm.ainvoke(
            [SystemMessage(content=FACT_EXTRACTION_SYSTEM_PROMPT),
             HumanMessage(content=prompt)]
        )

        result = self._parse_json_response(response.content)

        logger.info(
            "chapter_fact_extraction_completed",
            project_id=project_id,
            chapter_id=chapter_id,
            state_changes=len(result.state_changes),
            relation_changes=len(result.relation_changes),
            new_entities=len(result.new_entities),
        )

        return result

    def to_change_requests(
        self, extraction: ExtractionResult, project_id: str, chapter_id: str
    ) -> List[Dict[str, Any]]:
        """将提取结果转为 Change Request 格式"""
        from src.api.go_backend.change_requests import ChangeRequestPayload

        crs = []

        # 状态变更 -> CR
        for change in extraction.state_changes:
            cr = ChangeRequestPayload(
                project_id=project_id,
                chapter_id=chapter_id,
                category="entity_state",
                entity_name=change.entity_name,
                title=f"建议更新 {change.entity_name} 的 {change.field_key}",
                description=f"检测到 {change.entity_name} 的 {change.field_key} 从 {change.old_value} 变为 {change.new_value}",
                suggested_change={
                    "field_key": change.field_key,
                    "old_value": change.old_value,
                    "new_value": change.new_value,
                },
                evidence=[change.evidence],
                confidence=0.8,
            )
            crs.append(cr.to_dict())

        # 关系变更 -> CR
        for change in extraction.relation_changes:
            cr = ChangeRequestPayload(
                project_id=project_id,
                chapter_id=chapter_id,
                category="relation_change",
                title=f"关系变更: {change.from_entity} - {change.to_entity}",
                description=f"检测到 {change.from_entity} 与 {change.to_entity} 的关系发生变化（{change.change_type}）",
                suggested_change={
                    "from_entity": change.from_entity,
                    "to_entity": change.to_entity,
                    "relation_type": change.relation_type,
                    "change_type": change.change_type,
                },
                evidence=[change.evidence],
                confidence=0.75,
            )
            crs.append(cr.to_dict())

        # 新实体 -> CR
        for entity in extraction.new_entities:
            cr = ChangeRequestPayload(
                project_id=project_id,
                chapter_id=chapter_id,
                category="new_entity",
                entity_name=entity.name,
                title=f"新实体出场: {entity.name}",
                description=f"在文本中首次提及 {entity.name}（{entity.entity_type}）",
                suggested_change={
                    "action": "create",
                    "entity_type": entity.entity_type,
                    "name": entity.name,
                    "description": entity.description,
                },
                evidence=[entity.first_mention],
                confidence=0.9,
            )
            crs.append(cr.to_dict())

        return crs

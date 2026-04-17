"""
故事分析 API 路由
包含事实提取和章节分析接口
"""
from fastapi import APIRouter, HTTPException, status
from structlog import get_logger

from src.api.models.fact_extraction import (
    AnalyzeChapterRequest,
    AnalyzeChapterResponse,
    ExtractFactsRequest,
    ExtractFactsResponse,
)
from src.api.models.chapter_analysis import (
    ChangeDetectionRequest,
    ChangeDetectionResponse,
    ConsistencyCheckRequest,
    ConsistencyCheckResponse,
)
from src.agents.specialized.consistency_agent import ConsistencyAgent
from src.agents.specialized.fact_extraction_agent import FactExtractionAgent
from src.api.go_backend.client import GoBackendClient
from src.api.go_backend.change_requests import ChangeRequestOperations
from src.services.change_detection_service import ChangeDetectionService

logger = get_logger(__name__)

router = APIRouter()


# 全局 Agent 实例（延迟初始化）
_agent = None
_consistency_agent = None
_backend_client = None
_cr_ops = None
_change_detection_service = None


def _get_agent() -> FactExtractionAgent:
    """获取 Agent 实例（延迟初始化）"""
    global _agent
    if _agent is None:
        _agent = FactExtractionAgent(temperature=0.3)
    return _agent


def _get_cr_ops() -> ChangeRequestOperations:
    """获取 CR 操作实例"""
    global _backend_client, _cr_ops
    if _cr_ops is None:
        _backend_client = GoBackendClient()
        _cr_ops = ChangeRequestOperations(_backend_client)
    return _cr_ops


def _get_consistency_agent() -> ConsistencyAgent:
    """获取章节一致性检查 Agent"""
    global _consistency_agent
    if _consistency_agent is None:
        _consistency_agent = ConsistencyAgent(temperature=0.2)
    return _consistency_agent


def _get_change_detection_service() -> ChangeDetectionService:
    """获取文本变更检测服务"""
    global _change_detection_service
    if _change_detection_service is None:
        _change_detection_service = ChangeDetectionService()
    return _change_detection_service


@router.post("/story/analyze-chapter", response_model=AnalyzeChapterResponse)
async def analyze_chapter(request: AnalyzeChapterRequest):
    """
    分析章节文本，提取结构化事实

    输入：项目ID、章节ID、正文、已知实体列表
    输出：状态变更、关系变更、新实体出场、事件事实
    """
    try:
        logger.info(
            "analyze_chapter_request",
            project_id=request.project_id,
            chapter_id=request.chapter_id,
            text_length=len(request.text),
        )

        agent = _get_agent()

        # 执行事实提取
        result = await agent.extract_for_chapter(
            project_id=request.project_id,
            chapter_id=request.chapter_id,
            text=request.text,
            existing_entities=request.existing_entities,
        )

        response = AnalyzeChapterResponse(
            state_changes=result.state_changes,
            relation_changes=result.relation_changes,
            new_entities=result.new_entities,
            events=result.events,
            usage={},
        )

        logger.info(
            "analyze_chapter_completed",
            project_id=request.project_id,
            chapter_id=request.chapter_id,
            state_changes=len(result.state_changes),
            new_entities=len(result.new_entities),
        )

        return response

    except Exception as e:
        logger.error("analyze_chapter_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"章节分析失败: {str(e)}",
        )


@router.post("/story/check-consistency", response_model=ConsistencyCheckResponse)
async def check_consistency(request: ConsistencyCheckRequest):
    """
    检查章节一致性

    输入：当前章节正文、前序章节摘要、已知实体状态
    输出：结构化一致性问题列表
    """
    try:
        logger.info(
            "check_consistency_request",
            project_id=request.project_id,
            chapter_id=request.chapter_id,
            previous_chapters=len(request.previous_chapters),
            existing_entities=len(request.existing_entities),
            text_length=len(request.text),
        )

        agent = _get_consistency_agent()
        result = await agent.analyze_chapter(
            project_id=request.project_id,
            chapter_id=request.chapter_id,
            text=request.text,
            previous_chapters=request.previous_chapters,
            existing_entities=request.existing_entities,
        )

        logger.info(
            "check_consistency_completed",
            project_id=request.project_id,
            chapter_id=request.chapter_id,
            issues=len(result.issues),
            passed=result.passed,
        )
        return result

    except Exception as e:
        logger.error("check_consistency_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"章节一致性检查失败: {str(e)}",
        )


@router.post("/story/detect-changes", response_model=ChangeDetectionResponse)
async def detect_changes(request: ChangeDetectionRequest):
    """
    检测章节文本变更

    输入：同一章节的两个版本正文
    输出：段落级变更及实体提及变化
    """
    try:
        logger.info(
            "detect_changes_request",
            project_id=request.project_id,
            chapter_id=request.chapter_id,
            tracked_entities=len(request.tracked_entities),
            previous_length=len(request.previous_text),
            current_length=len(request.current_text),
        )

        service = _get_change_detection_service()
        result = service.detect_changes(
            previous_text=request.previous_text,
            current_text=request.current_text,
            tracked_entities=request.tracked_entities,
        )

        logger.info(
            "detect_changes_completed",
            project_id=request.project_id,
            chapter_id=request.chapter_id,
            changes=len(result.changes),
            paragraphs_added=result.paragraphs_added,
            paragraphs_removed=result.paragraphs_removed,
            paragraphs_modified=result.paragraphs_modified,
        )
        return result

    except Exception as e:
        logger.error("detect_changes_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"章节变更检测失败: {str(e)}",
        )


@router.post("/story/extract-facts", response_model=ExtractFactsResponse)
async def extract_facts(request: ExtractFactsRequest):
    """
    从文本中提取事实

    可选按实体类型或实体ID筛选
    """
    try:
        logger.info(
            "extract_facts_request",
            text_length=len(request.text),
            entity_type=request.entity_type,
            entity_id=request.entity_id,
        )

        agent = _get_agent()

        # 构建现有实体列表
        existing_entities = []
        if request.entity_type or request.entity_id:
            existing_entities = [{"entity_type": request.entity_type, "entity_id": request.entity_id}]

        # 执行提取
        result = await agent._extract(request.text, existing_entities)

        # 转换为 dict 格式
        facts = []
        for change in result.state_changes:
            facts.append({
                "type": "state_change",
                "entity_name": change.entity_name,
                "field_key": change.field_key,
                "old_value": change.old_value,
                "new_value": change.new_value,
                "evidence": change.evidence,
            })
        for change in result.relation_changes:
            facts.append({
                "type": "relation_change",
                "from_entity": change.from_entity,
                "to_entity": change.to_entity,
                "relation_type": change.relation_type,
                "change_type": change.change_type,
                "evidence": change.evidence,
            })
        for entity in result.new_entities:
            facts.append({
                "type": "new_entity",
                "name": entity.name,
                "entity_type": entity.entity_type,
                "first_mention": entity.first_mention,
                "description": entity.description,
            })
        for event in result.events:
            facts.append({
                "type": "event",
                "description": event.description,
                "chapter_position": event.chapter_position,
                "involved_entities": event.involved_entities,
                "evidence": event.evidence,
            })

        response = ExtractFactsResponse(facts=facts, usage={})

        logger.info("extract_facts_completed", facts_count=len(facts))

        return response

    except Exception as e:
        logger.error("extract_facts_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"事实提取失败: {str(e)}",
        )


@router.post("/story/analyze-and-create-cr")
async def analyze_and_create_cr(request: AnalyzeChapterRequest):
    """
    分析章节并创建 Change Request

    这是 trigger-index 调用的主接口：
    1. 分析章节文本
    2. 生成结构化 CR
    3. 写入后端
    """
    try:
        logger.info(
            "analyze_and_create_cr_request",
            project_id=request.project_id,
            chapter_id=request.chapter_id,
        )

        agent = _get_agent()

        # 1. 执行事实提取
        extraction = await agent.extract_for_chapter(
            project_id=request.project_id,
            chapter_id=request.chapter_id,
            text=request.text,
            existing_entities=request.existing_entities,
        )

        # 2. 转为 CR 格式
        crs = agent.to_change_requests(extraction, request.project_id, request.chapter_id)

        # 3. 写入后端
        cr_ops = _get_cr_ops()
        created_crs = []
        for cr in crs:
            try:
                created = await cr_ops.create(
                    type("CR", (), cr)()
                )
                created_crs.append(created)
            except Exception as cr_err:
                logger.warning("skipping_cr_creation", error=str(cr_err), cr_title=cr.get("title"))

        logger.info(
            "analyze_and_create_cr_completed",
            project_id=request.project_id,
            chapter_id=request.chapter_id,
            created_crs=len(created_crs),
        )

        return {
            "state_changes": len(extraction.state_changes),
            "relation_changes": len(extraction.relation_changes),
            "new_entities": len(extraction.new_entities),
            "change_requests_created": len(created_crs),
        }

    except Exception as e:
        logger.error("analyze_and_create_cr_error", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分析并创建CR失败: {str(e)}",
        )

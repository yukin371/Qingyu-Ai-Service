"""
故事分析 API 测试
"""
from unittest.mock import AsyncMock

from src.api.models.chapter_analysis import (
    ConsistencyCheckResponse,
    ConsistencyIssue,
)
from src.agents.review.diagnostic_report import IssueSeverity
from src.services.change_detection_service import ChangeDetectionService


def test_analyze_chapter_route(client, monkeypatch):
    """现有章节分析接口仍可正常响应"""
    import src.api.story_analysis as story_analysis
    from src.api.models.fact_extraction import ExtractionResult

    mock_agent = type("MockFactAgent", (), {})()
    mock_agent.extract_for_chapter = AsyncMock(return_value=ExtractionResult())

    monkeypatch.setattr(story_analysis, "_get_agent", lambda: mock_agent)

    response = client.post(
        "/api/v1/story/analyze-chapter",
        json={
            "project_id": "project-1",
            "chapter_id": "chapter-1",
            "text": "测试文本",
            "existing_entities": [],
        },
    )

    assert response.status_code == 200
    assert response.json()["state_changes"] == []


def test_check_consistency_route(client, monkeypatch):
    """章节一致性检查接口返回结构化问题"""
    import src.api.story_analysis as story_analysis

    mock_agent = type("MockConsistencyAgent", (), {})()
    mock_agent.analyze_chapter = AsyncMock(
        return_value=ConsistencyCheckResponse(
            passed=False,
            summary="检测到 1 条一致性问题",
            issues=[
                ConsistencyIssue(
                    id="issue-1",
                    severity=IssueSeverity.HIGH,
                    issue_type="timeline_conflict",
                    title="昼夜冲突",
                    description="时间线从清晨突然跳到深夜",
                    evidence="夜色已经彻底吞没街道",
                    suggestion="补充时间推进说明",
                    affected_entities=["chapter-1", "chapter-2"],
                )
            ],
            usage={},
        )
    )

    monkeypatch.setattr(story_analysis, "_get_consistency_agent", lambda: mock_agent)

    response = client.post(
        "/api/v1/story/check-consistency",
        json={
            "project_id": "project-1",
            "chapter_id": "chapter-2",
            "text": "夜色已经彻底吞没街道。",
            "previous_chapters": [
                {
                    "chapter_id": "chapter-1",
                    "title": "第一章",
                    "summary": "清晨时分主角刚醒来。",
                }
            ],
            "existing_entities": [],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["passed"] is False
    assert data["issues"][0]["issue_type"] == "timeline_conflict"


def test_detect_changes_route(client, monkeypatch):
    """章节文本变更检测接口返回段落与实体变化"""
    import src.api.story_analysis as story_analysis

    service = ChangeDetectionService()
    monkeypatch.setattr(
        story_analysis, "_get_change_detection_service", lambda: service
    )

    response = client.post(
        "/api/v1/story/detect-changes",
        json={
            "project_id": "project-1",
            "chapter_id": "chapter-3",
            "previous_text": "亚伯走进酒馆。",
            "current_text": "亚伯走进酒馆。\n\n艾伦推门而入。",
            "tracked_entities": ["亚伯", "艾伦"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["paragraphs_added"] == 1
    assert data["entity_mentions_added"] == ["艾伦"]

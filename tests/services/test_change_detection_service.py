"""
章节文本变更检测服务测试
"""
from src.services.change_detection_service import ChangeDetectionService


def test_detect_changes_tracks_added_removed_and_modified_paragraphs():
    service = ChangeDetectionService()

    result = service.detect_changes(
        previous_text="亚伯走进酒馆。\n\n诺艾尔坐在角落里。",
        current_text="亚伯走进热闹的酒馆。\n\n诺艾尔坐在角落里。\n\n艾伦推门而入。",
        tracked_entities=["亚伯", "诺艾尔", "艾伦"],
    )

    assert result.paragraphs_modified == 1
    assert result.paragraphs_added == 1
    assert result.paragraphs_removed == 0
    assert "艾伦" in result.entity_mentions_added
    assert any(change.change_type == "modified" for change in result.changes)
    assert any(change.change_type == "added" for change in result.changes)


def test_detect_changes_tracks_removed_entity_mentions():
    service = ChangeDetectionService()

    result = service.detect_changes(
        previous_text="亚伯和诺艾尔并肩离开。",
        current_text="亚伯独自离开。",
        tracked_entities=["亚伯", "诺艾尔"],
    )

    assert result.paragraphs_modified == 1
    assert result.entity_mentions_removed == ["诺艾尔"]
    assert result.changes[0].entity_mentions_removed == ["诺艾尔"]

"""
章节文本变更检测服务
"""
import re
from difflib import SequenceMatcher
from typing import List, Sequence, Set

from src.api.models.chapter_analysis import ChangeDetectionResponse, TextChange


class ChangeDetectionService:
    """检测章节文本的段落级变化与实体提及变化"""

    def detect_changes(
        self,
        previous_text: str,
        current_text: str,
        tracked_entities: Sequence[str] | None = None,
    ) -> ChangeDetectionResponse:
        tracked_entities = tracked_entities or []
        previous_paragraphs = self._split_paragraphs(previous_text)
        current_paragraphs = self._split_paragraphs(current_text)
        matcher = SequenceMatcher(a=previous_paragraphs, b=current_paragraphs)

        changes: List[TextChange] = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue
            if tag == "replace":
                changes.extend(
                    self._build_replace_changes(
                        previous_paragraphs[i1:i2],
                        current_paragraphs[j1:j2],
                        tracked_entities,
                    )
                )
                continue
            if tag == "delete":
                for paragraph in previous_paragraphs[i1:i2]:
                    changes.append(
                        self._build_change(
                            "removed",
                            before_text=paragraph,
                            after_text=None,
                            tracked_entities=tracked_entities,
                        )
                    )
                continue
            if tag == "insert":
                for paragraph in current_paragraphs[j1:j2]:
                    changes.append(
                        self._build_change(
                            "added",
                            before_text=None,
                            after_text=paragraph,
                            tracked_entities=tracked_entities,
                        )
                    )

        entity_mentions_added = sorted(
            {
                entity
                for change in changes
                for entity in change.entity_mentions_added
            }
        )
        entity_mentions_removed = sorted(
            {
                entity
                for change in changes
                for entity in change.entity_mentions_removed
            }
        )

        return ChangeDetectionResponse(
            changes=changes,
            paragraphs_added=sum(1 for change in changes if change.change_type == "added"),
            paragraphs_removed=sum(
                1 for change in changes if change.change_type == "removed"
            ),
            paragraphs_modified=sum(
                1 for change in changes if change.change_type == "modified"
            ),
            entity_mentions_added=entity_mentions_added,
            entity_mentions_removed=entity_mentions_removed,
        )

    def _build_replace_changes(
        self,
        previous_paragraphs: List[str],
        current_paragraphs: List[str],
        tracked_entities: Sequence[str],
    ) -> List[TextChange]:
        changes: List[TextChange] = []
        max_length = max(len(previous_paragraphs), len(current_paragraphs))
        for index in range(max_length):
            before_text = (
                previous_paragraphs[index] if index < len(previous_paragraphs) else None
            )
            after_text = (
                current_paragraphs[index] if index < len(current_paragraphs) else None
            )
            if before_text and after_text:
                changes.append(
                    self._build_change(
                        "modified",
                        before_text=before_text,
                        after_text=after_text,
                        tracked_entities=tracked_entities,
                    )
                )
            elif before_text:
                changes.append(
                    self._build_change(
                        "removed",
                        before_text=before_text,
                        after_text=None,
                        tracked_entities=tracked_entities,
                    )
                )
            elif after_text:
                changes.append(
                    self._build_change(
                        "added",
                        before_text=None,
                        after_text=after_text,
                        tracked_entities=tracked_entities,
                    )
                )
        return changes

    def _build_change(
        self,
        change_type: str,
        before_text: str | None,
        after_text: str | None,
        tracked_entities: Sequence[str],
    ) -> TextChange:
        before_entities = self._extract_entity_mentions(before_text or "", tracked_entities)
        after_entities = self._extract_entity_mentions(after_text or "", tracked_entities)

        return TextChange(
            change_type=change_type,
            summary=self._build_summary(change_type, before_text, after_text),
            before_text=before_text,
            after_text=after_text,
            entity_mentions_added=sorted(after_entities - before_entities),
            entity_mentions_removed=sorted(before_entities - after_entities),
        )

    def _split_paragraphs(self, text: str) -> List[str]:
        if not text.strip():
            return []
        return [
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n", text)
            if paragraph.strip()
        ]

    def _extract_entity_mentions(
        self, text: str, tracked_entities: Sequence[str]
    ) -> Set[str]:
        if not text:
            return set()
        if tracked_entities:
            return {entity for entity in tracked_entities if entity and entity in text}
        return set(
            match
            for match in re.findall(
                r"\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b", text
            )
            if len(match) > 1
        )

    def _build_summary(
        self, change_type: str, before_text: str | None, after_text: str | None
    ) -> str:
        if change_type == "added":
            return f"新增段落：{self._snippet(after_text)}"
        if change_type == "removed":
            return f"删除段落：{self._snippet(before_text)}"
        return f"修改段落：{self._snippet(after_text or before_text)}"

    def _snippet(self, text: str | None) -> str:
        if not text:
            return ""
        normalized = " ".join(text.split())
        if len(normalized) <= 30:
            return normalized
        return f"{normalized[:30]}..."

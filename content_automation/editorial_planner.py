from __future__ import annotations

from typing import Any

from .editorial import (
    EMOTION_CYCLE,
    FORMAT_CYCLE,
    PILLAR_CYCLE,
    PROOF_CYCLE,
    SERIES_BY_FORMAT,
    EditorialBrief,
)


def plan_editorial_briefs(
    existing_records: list[Any],
    *,
    count: int,
    pending_payloads: list[dict[str, object]] | None = None,
) -> list[EditorialBrief]:
    briefs: list[EditorialBrief] = []
    recent_raw = [getattr(record, "raw", {}) or {} for record in existing_records[:40]]
    recent_raw = [*(pending_payloads or []), *recent_raw]
    used_formats: set[str] = set()
    for _ in range(max(0, count)):
        brief = _least_recent_brief(recent_raw, briefs, used_formats)
        briefs.append(brief)
        used_formats.add(brief.content_format)
    return briefs


def _least_recent_brief(recent_raw: list[dict[str, Any]], pending: list[EditorialBrief], used_formats: set[str]) -> EditorialBrief:
    format_key, format_label, instruction = min(
        FORMAT_CYCLE,
        key=lambda item: (_recent_count(recent_raw, pending, "content_format", item[0]), item[0] in used_formats),
    )
    pillar_key, pillar_label = min(
        PILLAR_CYCLE,
        key=lambda item: _recent_count(recent_raw, pending, "content_pillar", item[0]),
    )
    proof_key, proof_label = min(
        PROOF_CYCLE,
        key=lambda item: _recent_count(recent_raw, pending, "proof_type", item[0]),
    )
    emotion_key, emotion_label = min(
        EMOTION_CYCLE,
        key=lambda item: _recent_count(recent_raw, pending, "emotion_angle", item[0]),
    )
    return EditorialBrief(
        content_format=format_key,
        content_format_label=format_label,
        content_pillar=pillar_key,
        content_pillar_label=pillar_label,
        proof_type=proof_key,
        proof_type_label=proof_label,
        emotion_angle=emotion_key,
        emotion_angle_label=emotion_label,
        series_name=SERIES_BY_FORMAT.get(format_key, format_label),
        instruction=instruction,
    )


def _recent_count(recent_raw: list[dict[str, Any]], pending: list[EditorialBrief], field: str, value: str) -> int:
    count = sum(1 for item in recent_raw if str(item.get(field) or "") == value)
    count += sum(1 for brief in pending if str(getattr(brief, field, "") or "") == value)
    return count

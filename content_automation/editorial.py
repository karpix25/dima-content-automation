from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EditorialBrief:
    content_format: str
    content_format_label: str
    content_pillar: str
    content_pillar_label: str
    proof_type: str
    proof_type_label: str
    emotion_angle: str
    emotion_angle_label: str
    series_name: str
    instruction: str


FORMAT_CYCLE: tuple[tuple[str, str, str], ...] = (
    (
        "money_leak",
        "Money Leak",
        "Expose a hidden cost, missed upside, or operational leak that the audience can fix.",
    ),
    (
        "teardown",
        "Teardown",
        "Break down a real asset, decision, process, listing, campaign, or system and show what is wrong.",
    ),
    (
        "myth_vs_reality",
        "Myth vs Reality",
        "Contrast a popular simplistic belief with the operator-level reality behind it.",
    ),
    (
        "one_metric",
        "One Metric",
        "Teach one metric, why it is misunderstood, and what decision it should change.",
    ),
    (
        "operator_diary",
        "Operator Diary",
        "Tell a grounded decision story from the operator's seat: tradeoff, action, consequence.",
    ),
    (
        "case_study",
        "Micro Case Study",
        "Use a compact before/after or client-style example to prove the mechanism.",
    ),
    (
        "before_after",
        "Before / After",
        "Show a specific change and the business effect it creates.",
    ),
    (
        "checklist",
        "Checklist",
        "Give a tight diagnostic checklist the viewer can apply immediately.",
    ),
    (
        "contrarian_take",
        "Contrarian Take",
        "Challenge a common tactic and explain when it backfires.",
    ),
    (
        "comment_reply",
        "Comment Reply",
        "Answer a likely audience question as if replying to a smart skeptical comment.",
    ),
)

PILLAR_CYCLE: tuple[tuple[str, str], ...] = (
    ("profit_economics", "Profit & economics"),
    ("acquisition", "Traffic & acquisition"),
    ("conversion", "Conversion & offer"),
    ("cashflow_inventory", "Cash flow & inventory"),
    ("operations", "Operations & systems"),
    ("supply_partners", "Supply & partners"),
    ("market_intelligence", "Market intelligence"),
    ("founder_decisions", "Founder decisions"),
)

PROOF_CYCLE: tuple[tuple[str, str], ...] = (
    ("numbers", "Numbers"),
    ("before_after", "Before / after"),
    ("mini_case", "Mini case"),
    ("mistake", "Mistake"),
    ("framework", "Framework"),
    ("diagnostic_question", "Diagnostic question"),
)

EMOTION_CYCLE: tuple[tuple[str, str], ...] = (
    ("shock", "Shock"),
    ("curiosity", "Curiosity"),
    ("urgency", "Urgency"),
    ("relief", "Relief"),
    ("contrarian", "Contrarian"),
    ("warning", "Warning"),
)

SERIES_BY_FORMAT = {
    "money_leak": "Hidden Leaks",
    "teardown": "Operator Teardowns",
    "myth_vs_reality": "Myth vs Reality",
    "one_metric": "One Metric Lab",
    "operator_diary": "Operator Diary",
    "case_study": "Micro Case Files",
    "before_after": "Before / After",
    "checklist": "Operator Checklist",
    "contrarian_take": "Contrarian Operator",
    "comment_reply": "Audience Reply",
}


def build_editorial_briefs(*, start_index: int, count: int) -> list[EditorialBrief]:
    briefs: list[EditorialBrief] = []
    for offset in range(max(0, count)):
        index = start_index + offset
        format_key, format_label, instruction = FORMAT_CYCLE[index % len(FORMAT_CYCLE)]
        pillar_key, pillar_label = PILLAR_CYCLE[(index // len(FORMAT_CYCLE) + index) % len(PILLAR_CYCLE)]
        proof_key, proof_label = PROOF_CYCLE[(index // 2 + index) % len(PROOF_CYCLE)]
        emotion_key, emotion_label = EMOTION_CYCLE[(index // 3 + index) % len(EMOTION_CYCLE)]
        briefs.append(
            EditorialBrief(
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
        )
    return briefs


def editorial_briefs_prompt(briefs: list[EditorialBrief]) -> str:
    if not briefs:
        return ""
    lines = ["Editorial briefs to assign in order:"]
    for index, brief in enumerate(briefs, start=1):
        lines.append(
            (
                f"{index}. Format: {brief.content_format_label}; Pillar: {brief.content_pillar_label}; "
                f"Proof: {brief.proof_type_label}; Emotion: {brief.emotion_angle_label}; "
                f"Series: {brief.series_name}; Direction: {brief.instruction}"
            )
        )
    lines.append(
        "Return these exact metadata fields for each matching script: "
        "content_format, content_pillar, proof_type, emotion_angle, series_name."
    )
    lines.append(
        "Use the audience and niche from the offer/source context. If the niche is Amazon/ecommerce, make the examples concrete to that niche; otherwise adapt the same format to the actual niche."
    )
    return "\n".join(lines)


def apply_editorial_brief(payload: dict[str, object], brief: EditorialBrief | None) -> dict[str, object]:
    if brief is None:
        return payload
    next_payload = dict(payload)
    next_payload.setdefault("content_format", brief.content_format)
    next_payload.setdefault("content_format_label", brief.content_format_label)
    next_payload.setdefault("content_pillar", brief.content_pillar)
    next_payload.setdefault("content_pillar_label", brief.content_pillar_label)
    next_payload.setdefault("proof_type", brief.proof_type)
    next_payload.setdefault("proof_type_label", brief.proof_type_label)
    next_payload.setdefault("emotion_angle", brief.emotion_angle)
    next_payload.setdefault("emotion_angle_label", brief.emotion_angle_label)
    next_payload.setdefault("series_name", brief.series_name)
    return next_payload


def script_editorial_summary(raw: dict[str, Any] | None) -> str:
    data = raw or {}
    parts = [
        _label(data, "content_format", "content_format_label"),
        _label(data, "content_pillar", "content_pillar_label"),
        _label(data, "proof_type", "proof_type_label"),
        _label(data, "emotion_angle", "emotion_angle_label"),
    ]
    clean_parts = [part for part in parts if part]
    series = str(data.get("series_name") or "").strip()
    if series:
        clean_parts.append(series)
    return " · ".join(clean_parts)


def _label(data: dict[str, Any], key: str, label_key: str) -> str:
    value = str(data.get(label_key) or data.get(key) or "").strip()
    return value.replace("_", " ").title() if value and label_key not in data else value

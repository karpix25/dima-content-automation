from __future__ import annotations

import re
from dataclasses import dataclass
from textwrap import shorten

from .storage import ScriptRecord


@dataclass(frozen=True)
class TuranFormat:
    key: str
    label: str
    task_type: str
    description: str


TURAN_FORMATS: tuple[TuranFormat, ...] = (
    TuranFormat(
        key="avatar_reels",
        label="ИИ аватар Reels",
        task_type="avatar_instagram",
        description="vertical avatar script package",
    ),
    TuranFormat(
        key="gold_5s",
        label="Золотой фон 5 сек.",
        task_type="avatar_instagram_post_5s",
        description="short text-card reel package",
    ),
    TuranFormat(
        key="infographic_reels",
        label="Инфографика Reels",
        task_type="infographic_reels",
        description="visual infographic card package",
    ),
    TuranFormat(
        key="avatar_horizontal",
        label="ИИ аватар YouTube",
        task_type="avatar_horizontal",
        description="horizontal avatar script package",
    ),
)

FORMAT_BY_KEY = {item.key: item for item in TURAN_FORMATS}


def get_turan_format(key: str) -> TuranFormat | None:
    return FORMAT_BY_KEY.get((key or "").strip())


def list_turan_formats() -> tuple[TuranFormat, ...]:
    return TURAN_FORMATS


def build_turan_package(record: ScriptRecord, format_key: str) -> str:
    spec = get_turan_format(format_key)
    if not spec:
        raise ValueError(f"Unknown Turan format: {format_key}")
    if spec.key == "avatar_reels":
        return build_avatar_reels_package(record, spec)
    if spec.key == "gold_5s":
        return build_gold_5s_package(record, spec)
    if spec.key == "infographic_reels":
        return build_infographic_reels_package(record, spec)
    if spec.key == "avatar_horizontal":
        return build_avatar_horizontal_package(record, spec)
    raise ValueError(f"Unsupported Turan format: {format_key}")


def build_all_turan_packages(record: ScriptRecord) -> str:
    return "\n\n---\n\n".join(build_turan_package(record, item.key) for item in TURAN_FORMATS)


def build_avatar_reels_package(record: ScriptRecord, spec: TuranFormat) -> str:
    voiceover = _clean_voiceover(record.voiceover)
    return _join_sections(
        _header(record, spec),
        ("Format goal", "Vertical AI-avatar reel from the approved NotebookLM script."),
        ("Title", _one_line(record.title)),
        ("Hook", _one_line(record.hook)),
        ("Voiceover", voiceover),
        ("Caption", _caption(record)),
        ("Visual direction", _visual_direction(record, "talking-head vertical reel with clean business overlays")),
        ("CTA", _one_line(record.cta) or "No direct CTA."),
    )


def build_gold_5s_package(record: ScriptRecord, spec: TuranFormat) -> str:
    title = _short_overlay(record.hook or record.title, 52)
    subline = _short_overlay(record.trigger or record.angle, 72)
    return _join_sections(
        _header(record, spec),
        ("Format goal", "Five-second gold-background card in the Turan style."),
        ("On-screen title", title),
        ("On-screen subline", subline),
        ("Micro voiceover", _short_voiceover(record.voiceover, 120)),
        ("Caption", _caption(record)),
        ("Visual direction", _visual_direction(record, "gold card, bold title, fast social proof energy")),
    )


def build_infographic_reels_package(record: ScriptRecord, spec: TuranFormat) -> str:
    bullets = _insight_bullets(record)
    return _join_sections(
        _header(record, spec),
        ("Format goal", "A single infographic reel card based on the approved NotebookLM insight."),
        ("Card title", _short_overlay(record.hook or record.title, 64)),
        ("Card subtitle", _short_overlay(record.angle or record.trigger, 90)),
        ("Card bullets", "\n".join(f"- {item}" for item in bullets)),
        ("Image prompt", _image_prompt(record, bullets)),
        ("Caption", _caption(record)),
    )


def build_avatar_horizontal_package(record: ScriptRecord, spec: TuranFormat) -> str:
    voiceover = _clean_voiceover(record.voiceover)
    chapters = _chapters_from_voiceover(voiceover)
    return _join_sections(
        _header(record, spec),
        ("Format goal", "Horizontal AI-avatar YouTube segment using the approved NotebookLM text as source."),
        ("Working title", _one_line(record.title)),
        ("Opening hook", _one_line(record.hook)),
        ("Script", voiceover),
        ("Chapter beats", "\n".join(f"{idx}. {item}" for idx, item in enumerate(chapters, start=1))),
        ("Description", _caption(record)),
    )


def _header(record: ScriptRecord, spec: TuranFormat) -> str:
    return f"Turan format: {spec.label}\nTask type: {spec.task_type}\nSource script: #{record.id}"


def _join_sections(header: str, *sections: tuple[str, str]) -> str:
    parts = [header]
    for title, value in sections:
        clean_value = (value or "").strip()
        if clean_value:
            parts.append(f"{title}:\n{clean_value}")
    return "\n\n".join(parts).strip()


def _clean_voiceover(value: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", (value or "").strip())


def _one_line(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _short_overlay(value: str, limit: int) -> str:
    return shorten(_one_line(value), width=limit, placeholder="...")


def _short_voiceover(value: str, limit: int) -> str:
    clean = _one_line(value)
    return shorten(clean, width=limit, placeholder="...")


def _caption(record: ScriptRecord) -> str:
    parts = [_one_line(record.hook), _one_line(record.cta)]
    return "\n\n".join(part for part in parts if part).strip()


def _visual_direction(record: ScriptRecord, base: str) -> str:
    angle = _one_line(record.angle)
    trigger = _one_line(record.trigger)
    details = "; ".join(part for part in [angle, trigger] if part)
    return f"{base}. {details}".strip()


def _insight_bullets(record: ScriptRecord) -> list[str]:
    candidates = [
        record.angle,
        record.trigger,
        record.why_it_works,
        record.source_basis,
    ]
    bullets = [_short_overlay(item, 86) for item in candidates if _one_line(item)]
    return bullets[:3] or [_short_overlay(record.voiceover, 86)]


def _image_prompt(record: ScriptRecord, bullets: list[str]) -> str:
    bullet_text = "; ".join(bullets)
    return (
        "Create a premium 9:16 business infographic card for Amazon sellers. "
        f"Main idea: {_one_line(record.hook or record.title)}. "
        f"Supporting points: {bullet_text}. "
        "Use sharp contrast, readable hierarchy, confident founder-brand energy, no clutter."
    )


def _chapters_from_voiceover(value: str) -> list[str]:
    sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+", _one_line(value)) if item.strip()]
    if len(sentences) >= 3:
        return [_short_overlay(item, 90) for item in sentences[:5]]
    chunks = [item.strip() for item in re.split(r"[,;:]\s+", _one_line(value)) if item.strip()]
    return [_short_overlay(item, 90) for item in chunks[:5]] or [_short_overlay(value, 90)]

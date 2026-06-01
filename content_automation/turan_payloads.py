from __future__ import annotations

from .storage import ScriptRecord
from .turan_formats import TuranFormat, build_turan_package


def build_structured_payload(record: ScriptRecord, spec: TuranFormat) -> dict[str, object]:
    base = {
        "source": {
            "kind": "notebooklm_approved_script",
            "script_id": record.id,
            "title": record.title,
            "hook": record.hook,
            "source_basis": record.source_basis,
        },
        "format": {
            "key": spec.key,
            "label": spec.label,
            "task_type": spec.task_type,
            "description": spec.description,
        },
        "content": {
            "title": record.title,
            "angle": record.angle,
            "hook": record.hook,
            "trigger": record.trigger,
            "voiceover": record.voiceover,
            "cta": record.cta,
            "why_it_works": record.why_it_works,
        },
        "turan_task_input": build_turan_task_input(record, spec),
        "package_text": build_turan_package(record, spec.key),
    }
    if spec.key == "infographic_reels":
        base["infographic_reels"] = {
            "card": {
                "title": record.hook or record.title,
                "subtitle": record.angle or record.trigger,
                "description": _caption(record),
                "source_title": record.title,
                "duration_seconds": 5,
                "style": "gold_background",
            }
        }
    if spec.key in {"avatar_reels", "avatar_horizontal"}:
        base["avatar"] = {
            "script_text": record.voiceover,
            "source_title": record.title,
            "target_platform": "instagram" if spec.key == "avatar_reels" else "youtube",
        }
    return base


def build_turan_task_input(record: ScriptRecord, spec: TuranFormat) -> dict[str, object]:
    script_meta = {
        "source": "notebooklm_approved_script",
        "source_script_id": record.id,
        "format_key": spec.key,
        "format_label": spec.label,
        "hook": record.hook,
        "trigger": record.trigger,
        "angle": record.angle,
        "cta": record.cta,
        "source_basis": record.source_basis,
    }
    if spec.key == "infographic_reels":
        script_meta["infographic_reels"] = {
            "card": {
                "title": record.hook or record.title,
                "subtitle": record.angle or record.trigger,
                "description": _caption(record),
                "source_title": record.title,
                "duration_seconds": 5,
                "style": "gold_background",
            }
        }

    return {
        "source_url": f"notebooklm-script://{record.id}",
        "type": spec.task_type,
        "source_title": record.title or record.hook or f"NotebookLM script #{record.id}",
        "factual_outline": _outline(record),
        "script_text": record.voiceover,
        "script_meta": script_meta,
    }


def _outline(record: ScriptRecord) -> str:
    return "\n".join(
        part
        for part in [
            f"Hook: {record.hook}" if record.hook else "",
            f"Angle: {record.angle}" if record.angle else "",
            f"Trigger: {record.trigger}" if record.trigger else "",
            f"Source basis: {record.source_basis}" if record.source_basis else "",
            f"Why it works: {record.why_it_works}" if record.why_it_works else "",
        ]
        if part
    ).strip()


def _caption(record: ScriptRecord) -> str:
    return "\n\n".join(part for part in [record.hook, record.cta] if part).strip()

from __future__ import annotations

from dataclasses import dataclass

from .storage import ScriptRecord


@dataclass(frozen=True)
class ScriptMessageContract:
    title: str
    hook: str
    hook_type: str
    first_frame_text: str
    hook_pattern: str
    mechanism: str
    visual_proof: str
    visual_retention_plan: str
    trigger: str
    angle: str
    cta: str

    @property
    def headline(self) -> str:
        return self.first_frame_text or self.hook or self.title


def build_script_message_contract(record: ScriptRecord) -> ScriptMessageContract:
    raw = record.raw or {}
    return ScriptMessageContract(
        title=_clean(record.title),
        hook=_clean(record.hook),
        hook_type=_clean(raw.get("hook_type")),
        first_frame_text=_clean(raw.get("first_frame_text")),
        hook_pattern=_clean(raw.get("hook_pattern")),
        mechanism=_clean(raw.get("mechanism")),
        visual_proof=_clean(raw.get("visual_proof")),
        visual_retention_plan=_clean(raw.get("visual_retention_plan")),
        trigger=_clean(record.trigger),
        angle=_clean(record.angle),
        cta=_clean(record.cta),
    )


def script_hook_metadata(record: ScriptRecord) -> dict[str, str]:
    contract = build_script_message_contract(record)
    return {
        "hook_type": contract.hook_type,
        "hook_pattern": contract.hook_pattern,
        "mechanism": contract.mechanism,
        "first_frame_text": contract.first_frame_text,
        "visual_proof": contract.visual_proof,
        "visual_retention_plan": contract.visual_retention_plan,
    }


def script_hook_metadata_lines(record: ScriptRecord) -> list[str]:
    values = script_hook_metadata(record)
    labels = (
        ("hook_type", "Тип хука"),
        ("hook_pattern", "Паттерн хука"),
        ("mechanism", "Механизм"),
        ("first_frame_text", "Первый кадр"),
        ("visual_proof", "Визуальное доказательство"),
        ("visual_retention_plan", "Визуальный план удержания"),
    )
    return [f"{label}: {values[key]}" for key, label in labels if values.get(key)]


def script_hook_metadata_payload(record: ScriptRecord) -> dict[str, str]:
    contract = build_script_message_contract(record)
    return {
        "headline": contract.headline,
        "hook": contract.hook,
        "hook_type": contract.hook_type,
        "first_frame_text": contract.first_frame_text,
        "hook_pattern": contract.hook_pattern,
        "mechanism": contract.mechanism,
        "visual_proof": contract.visual_proof,
        "visual_retention_plan": contract.visual_retention_plan,
    }


def _clean(value: object) -> str:
    return " ".join(str(value or "").split())

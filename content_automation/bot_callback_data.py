from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScriptCallbackData:
    action: str
    script_id: int
    flow: str


def parse_script_callback_data(value: str | None) -> ScriptCallbackData | None:
    parts = (value or "").split(":")
    if len(parts) not in {3, 4} or parts[0] != "script":
        return None
    try:
        script_id = int(parts[2])
    except ValueError:
        return None
    return ScriptCallbackData(
        action=parts[1],
        script_id=script_id,
        flow=parts[3] if len(parts) == 4 else "review",
    )

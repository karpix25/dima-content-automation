from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .script_message_contract import script_hook_metadata_lines
from .storage import ScriptRecord


FORMAT_READY_STATUSES = {"approved", "used_for_video"}


@dataclass(frozen=True)
class ApprovedFormatSelection:
    action: str
    script_id: int | None = None


def parse_approved_format_callback(value: str | None) -> ApprovedFormatSelection | None:
    parts = (value or "").split(":")
    if parts == ["approved", "list"]:
        return ApprovedFormatSelection(action="list")
    if len(parts) == 3 and parts[:2] == ["approved", "show"]:
        try:
            return ApprovedFormatSelection(action="show", script_id=int(parts[2]))
        except ValueError:
            return None
    return None


def list_format_ready_scripts(storage: Any, user_id: str, *, limit: int = 10) -> list[ScriptRecord]:
    records = storage.list_recent_scripts(user_id, format="short", limit=100)
    return [record for record in records if record.status in FORMAT_READY_STATUSES][:limit]


def approved_scripts_message(records: list[ScriptRecord]) -> str:
    if not records:
        return "Пока нет готовых short-сценариев. Сначала прими сценарий через проверку очереди."
    lines = ["Готовые сценарии для форматов:", ""]
    for record in records:
        title = _one_line(record.title or record.hook or f"Сценарий #{record.id}", limit=68)
        status = "уже был в видео" if record.status == "used_for_video" else "одобрен"
        lines.append(f"#{record.id} · {status} · {title}")
    lines.extend(["", "Выбери сценарий, потом нажми нужный формат."])
    return "\n".join(lines)


def approved_scripts_keyboard(records: list[ScriptRecord]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text=f"#{record.id} · {_one_line(record.title or record.hook, limit=34)}", callback_data=f"approved:show:{record.id}")]
        for record in records
    ]
    rows.append([InlineKeyboardButton(text="Главное меню", callback_data="main:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def approved_script_details(record: ScriptRecord) -> str:
    status = "уже был использован для видео" if record.status == "used_for_video" else "одобрен"
    hook_lines = script_hook_metadata_lines(record)
    return "\n\n".join(
        part
        for part in [
            f"Сценарий #{record.id} · {status}",
            f"Заголовок:\n{record.title}".strip() if record.title else "",
            f"Хук:\n{record.hook}".strip() if record.hook else "",
            "Хук-механика:\n" + "\n".join(hook_lines) if hook_lines else "",
            f"Текст озвучки:\n{_one_line(record.voiceover, limit=700)}".strip() if record.voiceover else "",
            "Выбери формат ниже. Контент запустится только после нажатия конкретной кнопки.",
        ]
        if part
    )


def _one_line(value: str | None, *, limit: int) -> str:
    text = " ".join((value or "Без названия").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."

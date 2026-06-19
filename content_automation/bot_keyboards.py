from __future__ import annotations

from collections.abc import Iterable

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


FORMAT_BUTTONS = {
    "avatar_reels": "Reels/Shorts",
    "infographic_reels": "Инфографика",
    "avatar_horizontal": "YouTube horizontal",
    "all": "Все форматы",
}
VISIBLE_FORMAT_KEYS = {"avatar_reels", "infographic_reels", "avatar_horizontal", "all"}


def callback_button(text: str, callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data)


def build_main_keyboard(miniapp_url: str | None = None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [callback_button("Проверить сценарии на апрув", "main:review")],
        [
            callback_button("Собрать сценарии из NotebookLM", "main:daily"),
            callback_button("Добрать банк сценариев", "main:refill"),
        ],
        [
            callback_button("Статус очереди", "main:bank"),
            callback_button("Найти темы в Reddit", "main:reddit"),
        ],
        [callback_button("Готовые сценарии → форматы", "approved:list")],
        [callback_button("YouTube-сценарий", "main:youtube")],
        [callback_button("Нарезать YouTube через Vizard", "main:vizard")],
    ]
    if miniapp_url:
        rows.append([InlineKeyboardButton(text="Открыть Mini App", web_app=WebAppInfo(url=miniapp_url))])
    else:
        rows.append([callback_button("Настройки", "main:settings")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_format_output_keyboard(script_id: int, *, used_format_keys: Iterable[str] | None = None) -> InlineKeyboardMarkup:
    used = normalize_used_format_keys(used_format_keys or [])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                callback_button(format_button_text("avatar_reels", used), f"format:create:{script_id}:avatar_reels"),
                callback_button(format_button_text("infographic_reels", used), f"format:create:{script_id}:infographic_reels"),
            ],
            [callback_button(format_button_text("avatar_horizontal", used), f"format:create:{script_id}:avatar_horizontal")],
            [callback_button(format_button_text("all", used), f"format:create:{script_id}:all")],
            [callback_button("Главное меню", "main:home")],
        ]
    )


def format_button_text(format_key: str, used_format_keys: set[str]) -> str:
    label = FORMAT_BUTTONS.get(format_key, format_key)
    if format_key not in used_format_keys:
        return label
    return f"✓ {_strike(label)}"


def normalize_used_format_keys(values: Iterable[str]) -> set[str]:
    used = {str(value) for value in values if str(value) in VISIBLE_FORMAT_KEYS}
    if "all" in used:
        used.update(VISIBLE_FORMAT_KEYS)
    return used


def _strike(value: str) -> str:
    return "".join(f"{char}\u0336" if char != " " else char for char in value)

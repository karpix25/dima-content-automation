from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


def callback_button(text: str, callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data)


def build_main_keyboard(miniapp_url: str | None = None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [callback_button("Проверить сценарии", "main:review")],
        [
            callback_button("Создать 10 сценариев", "main:daily"),
            callback_button("Пополнить банк", "main:refill"),
        ],
        [
            callback_button("Статус банка", "main:bank"),
            callback_button("Reddit-темы", "main:reddit"),
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


def build_format_output_keyboard(script_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                callback_button("Reels/Shorts", f"format:create:{script_id}:avatar_reels"),
                callback_button("Инфографика", f"format:create:{script_id}:infographic_reels"),
            ],
            [callback_button("YouTube horizontal", f"format:create:{script_id}:avatar_horizontal")],
            [callback_button("Все форматы", f"format:create:{script_id}:all")],
            [callback_button("Главное меню", "main:home")],
        ]
    )

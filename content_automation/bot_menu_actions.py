from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from .scrapecreators import ScrapeCreatorsError
from .settings_service import get_reddit_subreddits, get_reddit_timeframe


@dataclass(frozen=True)
class BotMenuDeps:
    storage: Any
    settings: Any
    idea_bank: Any
    scrapecreators: Any
    logger: Any
    refill_if_needed: Callable[..., Awaitable[None]]
    generate_scripts_for_user: Callable[..., Awaitable[list[Any]]]
    send_scripts: Callable[..., Awaitable[None]]
    show_next_content_idea: Callable[..., Awaitable[bool]]
    collect_reddit_ideas: Callable[..., Any]
    edit_or_send_text: Callable[..., Awaitable[Message]]
    main_keyboard: Callable[[], InlineKeyboardMarkup]
    message_thread_id: Callable[[Message | None], int | None]


async def run_daily_action(callback: CallbackQuery, user_id: str, deps: BotMenuDeps) -> None:
    await deps.refill_if_needed(
        callback.message.chat.id,
        user_id,
        thread_id=deps.message_thread_id(callback.message),
        message=callback.message,
        edit=True,
        force=True,
    )


async def run_reddit_action(callback: CallbackQuery, user_id: str, deps: BotMenuDeps) -> None:
    await deps.edit_or_send_text(
        callback.message.chat.id,
        "⏳ Ищу свежие Reddit-темы...",
        thread_id=deps.message_thread_id(callback.message),
        message=callback.message,
        edit=True,
    )
    try:
        ideas = await asyncio.to_thread(
            deps.collect_reddit_ideas,
            deps.scrapecreators,
            subreddits=get_reddit_subreddits(deps.storage, deps.settings, user_id),
            timeframe=get_reddit_timeframe(deps.storage, deps.settings, user_id),
            limit=10,
        )
        inserted = deps.idea_bank.add_many(user_id, ideas)
    except ScrapeCreatorsError as exc:
        await callback.message.edit_text(f"❌ ScrapeCreators не настроен: {exc}", reply_markup=deps.main_keyboard())
        return
    except Exception as exc:
        deps.logger.exception("Failed to collect Reddit radar")
        await callback.message.edit_text(f"❌ Не удалось собрать Reddit-темы: {exc}", reply_markup=deps.main_keyboard())
        return

    prefix = f"Нашел {len(ideas)} тем, новых после дедупликации: {len(inserted)}."
    if not inserted:
        await callback.message.edit_text(
            prefix + "\nНовых тем нет. Можно попробовать позже или расширить сабреддиты.",
            reply_markup=deps.main_keyboard(),
        )
        return
    await callback.message.edit_text(prefix)
    await deps.show_next_content_idea(callback.message.chat.id, user_id, thread_id=deps.message_thread_id(callback.message))


async def run_youtube_action(callback: CallbackQuery, user_id: str, deps: BotMenuDeps) -> None:
    await deps.edit_or_send_text(
        callback.message.chat.id,
        "⏳ Запрашиваю у NotebookLM YouTube-сценарий до 15 минут...",
        thread_id=deps.message_thread_id(callback.message),
        message=callback.message,
        edit=True,
    )
    try:
        records = await deps.generate_scripts_for_user(user_id, 1, format="youtube")
    except Exception as exc:
        deps.logger.exception("Failed to generate YouTube script")
        await callback.message.edit_text(f"❌ Не удалось сгенерировать YouTube-сценарий: {exc}", reply_markup=deps.main_keyboard())
        return
    await deps.send_scripts(
        callback.message.chat.id,
        records,
        thread_id=deps.message_thread_id(callback.message),
        message=callback.message,
        edit=True,
    )


async def run_vizard_hint_action(callback: CallbackQuery, deps: BotMenuDeps) -> None:
    await deps.edit_or_send_text(
        callback.message.chat.id,
        "Пришли YouTube-ссылку обычным сообщением, и я отправлю видео в Vizard на нарезку.",
        thread_id=deps.message_thread_id(callback.message),
        message=callback.message,
        edit=True,
        reply_markup=deps.main_keyboard(),
    )

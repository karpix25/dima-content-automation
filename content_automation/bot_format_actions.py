from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from aiogram.types import InlineKeyboardMarkup

from .web_format_jobs import create_and_deliver_format_job


@dataclass(frozen=True)
class BotFormatDeps:
    storage: Any
    asset_store: Any
    settings: Any
    logger: Any
    send_to_chat_thread: Callable[..., Awaitable[Any]]
    format_output_keyboard: Callable[[int], InlineKeyboardMarkup]


async def run_format_output_job(
    *,
    chat_id: int,
    thread_id: int | None,
    user_id: str,
    script_id: int,
    format_key: str,
    deps: BotFormatDeps,
) -> None:
    try:
        job = await asyncio.to_thread(
            create_and_deliver_format_job,
            storage=deps.storage,
            asset_store=deps.asset_store,
            settings=deps.settings,
            user_id=user_id,
            script_id=script_id,
            format_key=format_key,
        )
    except Exception as exc:
        deps.logger.exception("Failed to create format from Telegram button")
        await deps.send_to_chat_thread(
            chat_id,
            f"Не удалось сделать формат для сценария #{script_id}: {exc}",
            thread_id=thread_id,
            reply_markup=deps.format_output_keyboard(script_id),
        )
        return
    await deps.send_to_chat_thread(
        chat_id,
        f"Формат для сценария #{script_id} завершен со статусом: {job.status}.",
        thread_id=thread_id,
        reply_markup=deps.format_output_keyboard(script_id),
    )

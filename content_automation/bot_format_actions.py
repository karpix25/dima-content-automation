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
    format_output_keyboard: Callable[[str, int, set[str] | None], InlineKeyboardMarkup]


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
            reply_markup=deps.format_output_keyboard(user_id, script_id, None),
        )
        return
    await deps.send_to_chat_thread(
        chat_id,
        format_completion_message(script_id=script_id, job=job),
        thread_id=thread_id,
        reply_markup=deps.format_output_keyboard(user_id, script_id, {format_key}),
    )


def format_completion_message(*, script_id: int, job: Any) -> str:
    if job.status == "delivered":
        details = _compact_job_text(job.output_text)
        return f"✅ Формат для сценария #{script_id} готов." + (f"\n{details}" if details else "")
    if job.status == "failed":
        reason = _compact_job_text(job.error or job.output_text)
        return f"⚠️ Формат для сценария #{script_id} не создан." + (f"\nПричина: {reason}" if reason else "")
    details = _compact_job_text(job.output_text)
    return f"Формат для сценария #{script_id} завершен со статусом: {job.status}." + (
        f"\n{details}" if details else ""
    )


def _compact_job_text(value: str | None, *, limit: int = 900) -> str:
    text = "\n".join(line.strip() for line in (value or "").splitlines() if line.strip())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."

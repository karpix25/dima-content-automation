from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup

from .config import Settings
from .settings_service import get_vizard_settings
from .storage import Storage
from .vizard_client import VizardApiError
from .vizard_models import VIZARD_LENGTH_OPTIONS, VIZARD_RATIO_OPTIONS, VizardUserSettings
from .vizard_service import build_vizard_client, download_vizard_clips, submit_and_wait_for_vizard_clips
from .vizard_youtube import extract_youtube_url


logger = logging.getLogger(__name__)


def vizard_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [button("9:16 вертикальный", callback_data="vizard:ratio:1")],
            [button("16:9 горизонтальный", callback_data="vizard:ratio:4")],
            [button("Длина: auto", callback_data="vizard:length:0")],
            [button("Длина: <30 сек", callback_data="vizard:length:1")],
            [button("Длина: 30-60 сек", callback_data="vizard:length:2")],
            [button("Длина: 60-90 сек", callback_data="vizard:length:3")],
            [button("Длина: 90 сек - 3 мин", callback_data="vizard:length:4")],
            [button("Удаление тишины: вкл", callback_data="vizard:silence:1")],
            [button("Удаление тишины: выкл", callback_data="vizard:silence:0")],
            [button("Показать текущие Vizard", callback_data="vizard:show")],
        ]
    )


def format_vizard_settings(settings: VizardUserSettings) -> str:
    length = ", ".join(VIZARD_LENGTH_OPTIONS.get(item, str(item)) for item in settings.prefer_length)
    return "\n".join(
        [
            "Vizard настройки:",
            f"Формат: {VIZARD_RATIO_OPTIONS.get(settings.ratio_of_clip, settings.ratio_of_clip)}",
            f"Длина клипа: {length}",
            f"Язык: {settings.lang}",
            f"Максимум клипов: {settings.max_clip_number or 'all'}",
            f"Keywords: {settings.keywords or 'пусто'}",
            f"Субтитры: {on_off(settings.subtitle_switch)}",
            f"Headline/hook: {on_off(settings.headline_switch)}",
            f"Emoji: {on_off(settings.emoji_switch)}",
            f"Highlight words: {on_off(settings.highlight_switch)}",
            f"Auto B-roll: {on_off(settings.auto_broll_switch)}",
            f"Remove silence: {on_off(settings.remove_silence_switch)}",
            f"Template ID: {settings.template_id or 'не задан'}",
        ]
    )


async def run_vizard_youtube_job(
    *,
    bot: Bot,
    storage: Storage,
    settings: Settings,
    user_id: str,
    chat_id: int,
    thread_id: int | None,
    text: str,
) -> None:
    video_url = extract_youtube_url(text)
    if not video_url:
        await bot.send_message(chat_id, "Пришли YouTube-ссылку или команду /vizard <youtube_url>.", message_thread_id=thread_id)
        return
    if not settings.vizard_api_key:
        await bot.send_message(chat_id, "Vizard API key не настроен. Добавь VIZARD_API_KEY в .env.", message_thread_id=thread_id)
        return

    user_settings = get_vizard_settings(storage, user_id)
    status = await bot.send_message(
        chat_id,
        "⏳ Отправил YouTube-ссылку в Vizard. Это может занять от нескольких минут до десятков минут.",
        message_thread_id=thread_id,
    )
    try:
        client = build_vizard_client(settings)
        project = await asyncio.to_thread(
            submit_and_wait_for_vizard_clips,
            client=client,
            user_settings=user_settings,
            video_url=video_url,
            poll_seconds=settings.vizard_poll_seconds,
            timeout_seconds=settings.vizard_timeout_seconds,
            project_name="Telegram YouTube clipping",
        )
        if not project.clips:
            await status.edit_text(f"⚠️ Vizard завершил проект {project.project_id}, но клипы пока не вернул. Попробуй позже.")
            return
        await status.edit_text(f"✅ Vizard нашел {len(project.clips)} клипов. Скачиваю и отправляю в Telegram.")
        downloaded = await download_vizard_clips(settings=settings, user_id=user_id, project=project)
        if not downloaded:
            await status.edit_text("⚠️ Vizard вернул клипы, но без доступных download URL.")
            return
        for index, item in enumerate(downloaded, start=1):
            await bot.send_video(
                chat_id,
                FSInputFile(item.path),
                caption=clip_caption(index, item.clip.title, item.clip.viral_score, item.clip.clip_editor_url),
                message_thread_id=thread_id,
            )
        await status.edit_text(f"✅ Vizard-нарезка готова: отправлено {len(downloaded)} роликов.")
    except (VizardApiError, Exception) as exc:
        logger.exception("Vizard YouTube job failed")
        await status.edit_text(f"❌ Vizard не смог нарезать видео: {exc}")


def clip_caption(index: int, title: str, viral_score: str, editor_url: str) -> str:
    lines = [f"Vizard clip #{index}"]
    if title:
        lines.append(title)
    if viral_score:
        lines.append(f"Viral score: {viral_score}")
    if editor_url:
        lines.append(editor_url)
    return "\n".join(lines)[:1000]


def button(text: str, *, callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data)


def on_off(value: bool) -> str:
    return "вкл" if value else "выкл"

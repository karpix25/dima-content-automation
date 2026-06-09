from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup

from .config import Settings
from .final_video_variants import build_final_video_variants
from .kie_image import KieImageClient, KieImageConfig
from .media_assets import MediaAssetStore
from .settings_service import get_vizard_settings
from .storage import Storage
from .vizard_client import VizardApiError
from .vizard_models import VIZARD_LENGTH_OPTIONS, VIZARD_RATIO_OPTIONS, VizardProjectResult, VizardUserSettings
from .vizard_postprocess import apply_vizard_cover_frame
from .vizard_project import extract_vizard_project_id
from .vizard_service import build_vizard_client, download_vizard_clips, submit_and_wait_for_vizard_clips
from .vizard_youtube import extract_youtube_url
from .video_overlay import probe_video_size


logger = logging.getLogger(__name__)


def vizard_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [button("📱 Формат 9:16", callback_data="vizard:ratio:1")],
            [button("🖥 Формат 16:9", callback_data="vizard:ratio:4")],
            [button("⏱ Длина: auto", callback_data="vizard:length:0")],
            [button("⚡ Длина: до 30 сек", callback_data="vizard:length:1")],
            [button("🎯 Длина: 30-60 сек", callback_data="vizard:length:2")],
            [button("🧩 Длина: 60-90 сек", callback_data="vizard:length:3")],
            [button("📼 Длина: 90 сек - 3 мин", callback_data="vizard:length:4")],
            [
                button("🔇 Удалять тишину", callback_data="vizard:silence:1"),
                button("🔈 Оставлять тишину", callback_data="vizard:silence:0"),
            ],
            [button("👀 Показать текущие Vizard", callback_data="vizard:show")],
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
    project_id = extract_vizard_project_id(text)
    video_url = extract_youtube_url(text)
    if not project_id and not video_url:
        await bot.send_message(
            chat_id,
            "Пришли YouTube-ссылку, Vizard project link или project id.",
            message_thread_id=thread_id,
        )
        return
    if not settings.vizard_api_key:
        await bot.send_message(chat_id, "Vizard API key не настроен. Добавь VIZARD_API_KEY в .env.", message_thread_id=thread_id)
        return

    user_settings = get_vizard_settings(storage, user_id)
    status_text = (
        f"⏳ Нашел Vizard project {project_id}. Забираю готовые клипы."
        if project_id
        else "⏳ Отправил YouTube-ссылку в Vizard. Это может занять от нескольких минут до десятков минут."
    )
    status = await bot.send_message(
        chat_id,
        status_text,
        message_thread_id=thread_id,
    )
    try:
        client = build_vizard_client(settings)
        if project_id:
            project = await asyncio.to_thread(client.query_project, project_id)
        else:
            project = await asyncio.to_thread(
                submit_and_wait_for_vizard_clips,
                client=client,
                user_settings=user_settings,
                video_url=video_url or "",
                poll_seconds=settings.vizard_poll_seconds,
                timeout_seconds=settings.vizard_timeout_seconds,
                project_name="Telegram YouTube clipping",
            )
        if not project.clips:
            await status.edit_text(f"⚠️ Vizard завершил проект {project.project_id}, но клипы пока не вернул. Попробуй позже.")
            return
        await status.edit_text(f"✅ Vizard нашел {len(project.clips)} клипов. Скачиваю и отправляю в Telegram.")
        delivered_count = await deliver_vizard_project_clips(
            bot=bot,
            storage=storage,
            settings=settings,
            user_id=user_id,
            chat_id=chat_id,
            thread_id=thread_id,
            project=project,
        )
        if not delivered_count:
            await status.edit_text("⚠️ Vizard вернул клипы, но без доступных download URL.")
            return
        await status.edit_text(f"✅ Vizard-нарезка готова: обработано {delivered_count} клипов.")
    except (VizardApiError, Exception) as exc:
        logger.exception("Vizard YouTube job failed")
        await status.edit_text(f"❌ Vizard не смог нарезать видео: {exc}")


async def deliver_vizard_project_clips(
    *,
    bot: Bot,
    storage: Storage,
    settings: Settings,
    user_id: str,
    chat_id: int,
    thread_id: int | None,
    project: VizardProjectResult,
) -> int:
    downloaded = await download_vizard_clips(settings=settings, user_id=user_id, project=project)
    if not downloaded:
        return 0
    asset_store = MediaAssetStore(settings.data_dir / "content_automation.sqlite3")
    kie_client = build_vizard_kie_client(settings)
    for index, item in enumerate(downloaded, start=1):
        target_size = probe_video_size(item.path)
        platforms = vizard_platforms_for_size(target_size)
        cover_format = "youtube" if target_size[0] > target_size[1] else "short"
        clip_source_path = await asyncio.to_thread(
            apply_vizard_cover_frame,
            storage=storage,
            settings=settings,
            asset_store=asset_store,
            kie_client=kie_client,
            user_id=user_id,
            clip=item.clip,
            clip_path=item.path,
            output_dir=item.path.parent,
            index=index,
            format=cover_format,
            target_size=target_size,
        )
        variants = build_final_video_variants(
            storage=storage,
            user_id=user_id,
            source_path=clip_source_path,
            output_dir=item.path.parent,
            output_stem=clip_source_path.stem,
            platforms=platforms,
        )
        for variant in variants:
            await bot.send_video(
                chat_id,
                FSInputFile(variant.path),
                caption=clip_caption(index, variant.label, item.clip.title, item.clip.viral_score, item.clip.clip_editor_url),
                message_thread_id=thread_id,
            )
    return len(downloaded)


def clip_caption(index: int, platform_label: str, title: str, viral_score: str, editor_url: str) -> str:
    lines = [f"Vizard clip #{index} - {platform_label}"]
    if title:
        lines.append(title)
    if viral_score:
        lines.append(f"Viral score: {viral_score}")
    if editor_url:
        lines.append(editor_url)
    return "\n".join(lines)[:1000]


def vizard_platforms_for_size(size: tuple[int, int]) -> tuple[str, ...]:
    width, height = size
    return ("youtube",) if width > height else ("shorts", "reels")


def button(text: str, *, callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data)


def on_off(value: bool) -> str:
    return "вкл" if value else "выкл"


def build_vizard_kie_client(settings: Settings) -> KieImageClient:
    return KieImageClient(
        KieImageConfig(
            api_key=settings.kie_api_key,
            base_url=settings.kie_base_url,
            upload_base_url=settings.kie_upload_base_url,
            model=settings.kie_image_model,
            aspect_ratio=settings.kie_image_aspect_ratio,
            resolution=settings.kie_image_resolution,
            poll_timeout_seconds=settings.kie_poll_timeout_seconds,
            poll_interval_seconds=settings.kie_poll_interval_seconds,
            create_task_max_attempts=settings.kie_create_task_max_attempts,
            create_task_retry_delay_seconds=settings.kie_create_task_retry_delay_seconds,
        )
    )

from __future__ import annotations

import asyncio
import logging
import os
import re
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Message, WebAppInfo

from .config import load_settings
from .deepgram_transcription import DeepgramConfig
from .elevenlabs_api import ElevenLabsAPIClient, ElevenLabsAPIError, ElevenLabsVoice
from .elevenlabs_mcp import ElevenLabsMCPClient, ElevenLabsMCPError
from .final_video_variants import build_final_video_variants
from .heygen import HeyGenAvatar, HeyGenClient, HeyGenError
from .heygen_video_input import extract_heygen_video_id
from .kie_image import KieImageClient, KieImageConfig
from .media_assets import MediaAssetStore
from .montage_renderer import MontageRendererConfig, render_montage_if_configured
from .notebooklm import as_script_list, extract_json
from .notebooklm_mcp import NotebookLMMCPClient, notebook_ref_to_url
from .notebooklm_py import NotebookLMPyClient
from .prompts import DEFAULT_CTA_MIX, DEFAULT_OFFER_CONTEXT, build_short_scripts_prompt, build_youtube_script_prompt
from .script_length import DEFAULT_SPOKEN_WORDS_PER_MINUTE, WordBudget, count_spoken_words, vertical_word_budget, youtube_word_budget
from .settings_service import get_user_settings
from .storage import ScriptRecord, Storage
from .topic_dedupe import (
    build_exclusion_context,
    build_payload_exclusion_context,
    payload_text,
    script_payload_is_duplicate,
)
from .turan_formats import build_all_turan_packages, build_turan_package, get_turan_format, list_turan_formats
from .post_heygen_video import apply_cover_frame, apply_post_heygen_visuals
from .reference_paths import target_from_record_format, thumbnail_reference_paths
from .video_overlay import VideoOverlayError, apply_overlay, cleanup_old_videos, download_video, remove_file
from .vizard_bot import format_vizard_settings, run_vizard_youtube_job, vizard_settings_keyboard
from .vizard_models import normalize_vizard_setting_value
from .vizard_youtube import extract_youtube_url
from .voice_speed_profile import calibrated_voice_wpm, calibrate_voice_wpm, clear_voice_wpm, has_voice_wpm_profile
from .voiceover_timing import analyze_voiceover_timing, estimate_initial_voiceover_speed
from .visual_assets import generate_post_heygen_assets


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = load_settings()
storage = Storage(settings.data_dir / "content_automation.sqlite3")
asset_store = MediaAssetStore(settings.data_dir / "content_automation.sqlite3")
if settings.notebooklm_backend == "py":
    notebooklm = NotebookLMPyClient(
        storage_path=settings.notebooklm_py_storage_path,
        timeout_seconds=settings.notebooklm_mcp_timeout_seconds,
    )
else:
    notebooklm = NotebookLMMCPClient(
        command=settings.notebooklm_mcp_command,
        timeout_seconds=settings.notebooklm_mcp_timeout_seconds,
    )
elevenlabs = ElevenLabsMCPClient(
    api_key=settings.elevenlabs_api_key,
    command=settings.elevenlabs_mcp_command,
    output_directory=settings.elevenlabs_output_directory,
)
elevenlabs_api = ElevenLabsAPIClient(api_key=settings.elevenlabs_api_key)
heygen = HeyGenClient(
    api_key=settings.heygen_api_key,
    api_base_url=settings.heygen_api_base_url,
    upload_base_url=settings.heygen_upload_base_url,
    aspect_ratio=settings.heygen_aspect_ratio,
    resolution=settings.heygen_resolution,
    output_format=settings.heygen_output_format,
    poll_seconds=settings.heygen_video_poll_seconds,
    timeout_seconds=settings.heygen_video_timeout_seconds,
    private_avatars_only=settings.heygen_private_avatars_only,
)
kie_image = KieImageClient(
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
montage_renderer_config = MontageRendererConfig(
    hyperframes_project_dir=settings.hyperframes_project_dir,
    remotion_project_dir=settings.remotion_project_dir,
    renderer=settings.montage_renderer,
    timeout_seconds=settings.montage_render_timeout_seconds,
    max_scenes=settings.montage_max_scenes,
    kie_client=kie_image,
    deepgram=DeepgramConfig(
        api_key=settings.deepgram_api_key,
        api_base_url=settings.deepgram_api_base_url,
        model=settings.deepgram_model,
        language=settings.deepgram_language,
        timeout_seconds=settings.deepgram_timeout_seconds,
    ),
)
bot = Bot(settings.telegram_bot_token)
dp = Dispatcher()

APPROVED_BANK_TARGET = 5
REFILL_BATCH_SIZE = 10
PENDING_SETTING_EDITS: dict[str, str] = {}
PENDING_OVERLAY_UPLOADS: dict[str, str] = {}
HEYGEN_AVATAR_CACHE: dict[str, list[HeyGenAvatar]] = {}
ELEVENLABS_VOICE_CACHE: dict[str, list[ElevenLabsVoice]] = {}
CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")


def user_key(message_or_callback: Message | CallbackQuery) -> str:
    user = message_or_callback.from_user
    return str(user.id if user else "unknown")


def message_thread_id(message: Message | None) -> int | None:
    return getattr(message, "message_thread_id", None) if message else None


def save_activation_context(user_id: str, chat_id: int, thread_id: int | None) -> None:
    storage.set_setting(user_id, "active_chat_id", str(chat_id))
    storage.set_setting(user_id, "active_thread_id", "" if thread_id is None else str(thread_id))


def activate_from_message(message: Message) -> str:
    user_id = user_key(message)
    save_activation_context(user_id, message.chat.id, message_thread_id(message))
    return user_id


def activate_from_callback(callback: CallbackQuery) -> str:
    user_id = user_key(callback)
    if callback.message:
        save_activation_context(user_id, callback.message.chat.id, message_thread_id(callback.message))
    return user_id


async def answer_in_same_thread(
    message: Message,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
    disable_web_page_preview: bool | None = None,
) -> Message:
    return await bot.send_message(
        message.chat.id,
        telegram_safe_text(text),
        message_thread_id=message_thread_id(message),
        reply_markup=reply_markup,
        disable_web_page_preview=disable_web_page_preview,
    )


async def send_to_chat_thread(
    chat_id: int,
    text: str,
    *,
    thread_id: int | None = None,
    reply_markup: InlineKeyboardMarkup | None = None,
    disable_web_page_preview: bool | None = None,
) -> Message:
    return await bot.send_message(
        chat_id,
        telegram_safe_text(text),
        message_thread_id=thread_id,
        reply_markup=reply_markup,
        disable_web_page_preview=disable_web_page_preview,
    )


def telegram_safe_text(text: str, *, limit: int = 3900) -> str:
    if len(text) <= limit:
        return text
    suffix = "\n\n…сообщение обрезано, полный лог смотри в Coolify/контейнере."
    return text[: max(0, limit - len(suffix))].rstrip() + suffix


async def edit_or_send_text(
    chat_id: int,
    text: str,
    *,
    thread_id: int | None = None,
    message: Message | None = None,
    edit: bool = False,
    reply_markup: InlineKeyboardMarkup | None = None,
    disable_web_page_preview: bool | None = None,
) -> Message:
    if edit and message:
        try:
            if message.photo or message.video or message.document or message.audio:
                if len(text) <= 1024:
                    await message.edit_caption(caption=text, reply_markup=reply_markup)
                    return message
            else:
                await message.edit_text(
                    text,
                    reply_markup=reply_markup,
                    disable_web_page_preview=disable_web_page_preview,
                )
                return message
        except TelegramBadRequest as exc:
            if "message is not modified" in str(exc).lower():
                return message
            logger.warning("Failed to edit Telegram message, sending a new one: %s", exc)
            try:
                await message.delete()
            except TelegramBadRequest:
                pass
    return await send_to_chat_thread(
        chat_id,
        text,
        thread_id=thread_id,
        reply_markup=reply_markup,
        disable_web_page_preview=disable_web_page_preview,
    )


def script_keyboard(script_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [button("✅ Одобрить и сделать видео", callback_data=f"script:approve:{script_id}", style="success")],
            [button("❌ Отклонить и перейти дальше", callback_data=f"script:reject:{script_id}", style="danger")],
        ]
    )


def turan_formats_keyboard(script_id: int) -> InlineKeyboardMarkup:
    rows = [
        [button(item.label, callback_data=f"turan:format:{item.key}:{script_id}", style="primary")]
        for item in list_turan_formats()
    ]
    rows.append([button("🚀 Сделать все версии", callback_data=f"turan:format:all:{script_id}", style="success")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def format_script_message(record: ScriptRecord) -> str:
    label = "Короткий" if record.format == "short" else "YouTube"
    cta_type = str(record.raw.get("cta_type") or "unknown").strip()
    cta_reason = str(record.raw.get("cta_reason") or "").strip()
    return "\n\n".join(
        [
            f"{label} сценарий #{record.id}",
            f"Тема: {record.title}",
            f"Угол: {record.angle}",
            f"Хук: {record.hook}",
            f"Триггер: {record.trigger}",
            f"Текст озвучки:\n{record.voiceover}",
            f"CTA type: {cta_type}",
            f"CTA: {record.cta}",
            f"Почему такой CTA: {cta_reason}" if cta_reason else "",
            f"Почему сработает: {record.why_it_works}",
            f"Опора из базы: {record.source_basis}",
        ]
    ).replace("\n\n\n", "\n\n").strip()


def has_cyrillic(text: str | None) -> bool:
    return bool(CYRILLIC_RE.search(text or ""))


def script_payload_has_cyrillic(payload: dict[str, object]) -> bool:
    fields = ("title", "angle", "hook", "trigger", "voiceover", "cta", "why_it_works", "source_basis")
    return any(has_cyrillic(str(payload.get(field) or "")) for field in fields)


def script_record_has_cyrillic(record: ScriptRecord) -> bool:
    return any(
        has_cyrillic(value)
        for value in (
            record.title,
            record.angle,
            record.hook,
            record.trigger,
            record.voiceover,
            record.cta,
            record.why_it_works,
            record.source_basis,
        )
    )


def reject_cyrillic_pending_scripts(user_id: str) -> int:
    rejected = 0
    while True:
        records = storage.list_scripts(user_id, format="short", status="pending", limit=100)
        bad_records = [record for record in records if script_record_has_cyrillic(record)]
        for record in bad_records:
            storage.update_script_status(user_id, record.id, "rejected")
            rejected += 1
        if len(records) < 100 or not bad_records:
            break
    return rejected


def get_int_setting(user_id: str, key: str, default: int = 0) -> int:
    value = storage.get_setting(user_id, key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def set_review_session(user_id: str, total: int) -> None:
    storage.set_setting(user_id, "review_total", str(max(total, 0)))
    storage.set_setting(user_id, "review_done", "0")


def get_review_progress(user_id: str) -> tuple[int, int]:
    done = get_int_setting(user_id, "review_done")
    total = get_int_setting(user_id, "review_total")
    pending = storage.count_scripts(user_id, format="short", status="pending")
    if total < done + pending:
        total = done + pending
        storage.set_setting(user_id, "review_total", str(total))
    return done, total


def advance_review_progress(user_id: str) -> None:
    done, _ = get_review_progress(user_id)
    storage.set_setting(user_id, "review_done", str(done + 1))


def format_review_message(record: ScriptRecord, user_id: str) -> str:
    done, total = get_review_progress(user_id)
    current = min(done + 1, total) if total else 1
    return "\n\n".join(
        [
            f"Сценарий {current}/{total or 1}",
            f"Хук:\n{record.hook}",
            f"Текст озвучки:\n{record.voiceover}",
        ]
    )


def split_telegram_text(text: str, max_len: int = 3800) -> list[str]:
    raw = (text or "").strip()
    if not raw:
        return []
    chunks: list[str] = []
    remaining = raw
    while remaining:
        if len(remaining) <= max_len:
            chunks.append(remaining)
            break
        split_at = remaining.rfind("\n\n", 0, max_len)
        if split_at < max_len // 2:
            split_at = remaining.rfind("\n", 0, max_len)
        if split_at < max_len // 2:
            split_at = remaining.rfind(" ", 0, max_len)
        if split_at < max_len // 2:
            split_at = max_len
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    return chunks


async def send_turan_package(
    chat_id: int,
    thread_id: int | None,
    user_id: str,
    script_id: int,
    format_key: str,
) -> None:
    record = storage.get_script(user_id, script_id)
    if not record:
        await send_to_chat_thread(chat_id, "Сценарий не найден.", thread_id=thread_id)
        return
    if record.status != "approved":
        await send_to_chat_thread(chat_id, "Turan-форматы доступны только для одобренных сценариев.", thread_id=thread_id)
        return

    if format_key == "all":
        package = build_all_turan_packages(record)
        title = f"Готовые Turan-форматы для сценария #{record.id}"
    else:
        spec = get_turan_format(format_key)
        if not spec:
            await send_to_chat_thread(chat_id, "Неизвестный Turan-формат.", thread_id=thread_id)
            return
        package = build_turan_package(record, format_key)
        title = f"{spec.label} для сценария #{record.id}"

    chunks = split_telegram_text(f"{title}\n\n{package}")
    for chunk in chunks:
        await send_to_chat_thread(chat_id, chunk, thread_id=thread_id, disable_web_page_preview=True)


def get_notebook_ref(user_id: str) -> str | None:
    return storage.get_setting(user_id, "notebook_id") or settings.default_notebook_id


def get_author_style(user_id: str) -> str | None:
    return storage.get_setting(user_id, "author_style")


def clear_pending_edit(user_id: str) -> None:
    PENDING_SETTING_EDITS.pop(user_id, None)
    PENDING_OVERLAY_UPLOADS.pop(user_id, None)


def get_offer_context(user_id: str) -> str:
    return storage.get_setting(user_id, "offer_context") or DEFAULT_OFFER_CONTEXT.strip()


def get_cta_mix(user_id: str) -> str:
    return storage.get_setting(user_id, "cta_mix") or DEFAULT_CTA_MIX


def format_label(format: str) -> str:
    return "YouTube" if format == "youtube" else "Instagram"


def get_overlay_path(user_id: str, format: str) -> Path | None:
    value = storage.get_setting(user_id, f"{format}_overlay_path")
    return Path(value) if value else None


def set_overlay_path(user_id: str, format: str, path: Path) -> None:
    storage.set_setting(user_id, f"{format}_overlay_path", str(path))


def get_overlay_start_percent(user_id: str, format: str) -> int:
    value = storage.get_setting(user_id, f"{format}_overlay_start_percent")
    if not value:
        return 70
    try:
        return max(0, min(100, int(value)))
    except ValueError:
        return 70


def set_overlay_start_percent(user_id: str, format: str, value: str) -> int:
    try:
        percent = int(value.strip().replace("%", ""))
    except ValueError as exc:
        raise ValueError("Отправь число от 0 до 100, например 70") from exc
    if percent < 0 or percent > 100:
        raise ValueError("Процент должен быть от 0 до 100")
    storage.set_setting(user_id, f"{format}_overlay_start_percent", str(percent))
    return percent


def overlay_directory(user_id: str) -> Path:
    path = settings.data_dir / "overlays" / user_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_active_elevenlabs_voice_id(user_id: str) -> str | None:
    return storage.get_setting(user_id, "elevenlabs_voice_id") or settings.elevenlabs_voice_id


def get_active_elevenlabs_voice_name(user_id: str) -> str:
    return storage.get_setting(user_id, "elevenlabs_voice_name") or settings.elevenlabs_voice_name


def set_active_elevenlabs_voice(user_id: str, voice: ElevenLabsVoice) -> None:
    storage.set_setting(user_id, "elevenlabs_voice_id", voice.id)
    storage.set_setting(user_id, "elevenlabs_voice_name", voice.name)
    clear_voice_wpm(storage, user_id)


async def ensure_voice_wpm(user_id: str) -> int:
    voice_id = get_active_elevenlabs_voice_id(user_id)
    if has_voice_wpm_profile(storage, user_id, voice_id):
        return calibrated_voice_wpm(storage, user_id, voice_id)
    try:
        wpm = await asyncio.to_thread(
            calibrate_voice_wpm,
            storage=storage,
            user_id=user_id,
            voice_id=voice_id,
            voice_name=get_active_elevenlabs_voice_name(user_id),
            elevenlabs=elevenlabs,
            model_id=settings.elevenlabs_model_id,
            speed=settings.elevenlabs_speed,
            stability=settings.elevenlabs_stability,
            similarity_boost=settings.elevenlabs_similarity_boost,
            style=settings.elevenlabs_style,
            language=settings.elevenlabs_language,
        )
        logger.info("Calibrated ElevenLabs voice speed for user %s: %s wpm", user_id, wpm)
        return wpm
    except Exception:
        logger.exception("ElevenLabs voice speed calibration failed; using default WPM")
        return DEFAULT_SPOKEN_WORDS_PER_MINUTE


def get_active_heygen_avatar_id(user_id: str, target: str = "vertical") -> str | None:
    if target == "horizontal":
        return storage.get_setting(user_id, "heygen_avatar_id")
    return storage.get_setting(user_id, "heygen_vertical_avatar_id")


def get_active_heygen_avatar_name(user_id: str, target: str = "vertical") -> str | None:
    if target == "horizontal":
        return storage.get_setting(user_id, "heygen_avatar_name")
    return storage.get_setting(user_id, "heygen_vertical_avatar_name")


def set_active_heygen_avatar(user_id: str, avatar: HeyGenAvatar) -> None:
    storage.set_setting(user_id, "heygen_avatar_id", avatar.id)
    storage.set_setting(user_id, "heygen_avatar_name", avatar.name)
    storage.set_setting(user_id, "heygen_vertical_avatar_id", avatar.id)
    storage.set_setting(user_id, "heygen_vertical_avatar_name", avatar.name)


def get_heygen_generation_settings(user_id: str) -> tuple[str, str]:
    api_version = (storage.get_setting(user_id, "heygen_video_api_version") or "v2").strip().lower()
    engine = (storage.get_setting(user_id, "heygen_avatar_engine") or "avatar_iv").strip().lower()
    if api_version not in {"v2", "v3"}:
        api_version = "v2"
    if engine not in {"avatar_iv", "avatar_v"}:
        engine = "avatar_iv"
    return api_version, engine


def default_photo_avatar_motion_prompt() -> str:
    return (
        os.getenv("HEYGEN_PHOTO_AVATAR_MOTION_PROMPT")
        or (
            "The subject appears as a natural, expressive presenter speaking directly to the camera. "
            "The camera stays stable and professional, while the performance feels alive, focused, and confident. "
            "Facial expression remains neutral and attentive, without a smile, with subtle changes that match "
            "the rhythm and emphasis of speech. Use natural presenter movement: small shifts in posture, "
            "controlled head movement, steady eye contact, and restrained hand movement when it supports emphasis."
        )
    ).strip()


def button(text: str, *, callback_data: str | None = None, url: str | None = None, style: str | None = None) -> InlineKeyboardButton:
    kwargs: dict[str, str] = {"text": text}
    if callback_data:
        kwargs["callback_data"] = callback_data
    if url:
        kwargs["url"] = url
    return InlineKeyboardButton(**kwargs)


async def generate_scripts_for_user(
    user_id: str,
    count: int,
    format: str = "short",
    topic_hint: str | None = None,
) -> list[ScriptRecord]:
    notebook_ref = get_notebook_ref(user_id)
    if not notebook_ref:
        raise ValueError("Сначала задай NotebookLM ID через /set_notebook <id>.")

    style = get_author_style(user_id)
    offer_context = get_offer_context(user_id)
    cta_mix = get_cta_mix(user_id)
    user_settings = get_user_settings(storage, settings, user_id)
    voice_wpm = await ensure_voice_wpm(user_id)
    if format == "youtube":
        existing_records = storage.list_recent_scripts(user_id, format=format, limit=60)
        exclusion_context = build_exclusion_context(existing_records)
        word_budget = youtube_word_budget(user_settings.youtube_long_duration_minutes, wpm=voice_wpm)
        prompt = build_youtube_script_prompt(
            style,
            offer_context=offer_context,
            cta_mix=cta_mix,
            topic_hint=topic_hint,
            exclusion_context=exclusion_context,
            word_budget=word_budget,
        )
        items = await ask_notebooklm_for_scripts(
            user_id=user_id,
            notebook_ref=notebook_ref,
            prompt=prompt,
            count=count,
            format=format,
            existing_records=existing_records,
            accepted_payloads=[],
            word_budget=word_budget,
        )
    else:
        items: list[dict[str, object]] = []
        existing_records = storage.list_recent_scripts(user_id, format=format, limit=60)
        word_budget = vertical_word_budget(user_settings.vertical_avatar_duration_mode, wpm=voice_wpm)
        while len(items) < count:
            batch_count = min(settings.notebooklm_short_batch_size, count - len(items))
            exclusion_context = "\n".join(
                part
                for part in [
                    build_exclusion_context(existing_records),
                    build_payload_exclusion_context(items),
                ]
                if part
            )
            prompt = build_short_scripts_prompt(
                count=batch_count,
                author_style=style,
                offer_context=offer_context,
                cta_mix=cta_mix,
                topic_hint=topic_hint,
                exclusion_context=exclusion_context,
                word_budget=word_budget,
            )
            new_items = await ask_notebooklm_for_scripts(
                user_id=user_id,
                notebook_ref=notebook_ref,
                prompt=prompt,
                count=batch_count,
                format=format,
                existing_records=existing_records,
                accepted_payloads=items,
                word_budget=word_budget,
            )
            if not new_items:
                break
            items.extend(new_items)
    items = items[:count]
    if not items:
        raise ValueError("NotebookLM не вернул новые английские сценарии в JSON. Попробуй /refill еще раз.")

    logger.info("Saving %s generated %s script(s) for user %s", len(items), format, user_id)
    return [storage.add_script(user_id, format, item) for item in items]


async def ask_notebooklm_for_scripts(
    *,
    user_id: str,
    notebook_ref: str,
    prompt: str,
    count: int,
    format: str,
    existing_records: list[ScriptRecord],
    accepted_payloads: list[dict[str, object]],
    word_budget: WordBudget | None = None,
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for attempt in range(3):
        logger.info(
            "Generating %s %s script(s) with NotebookLM for user %s, attempt %s/3",
            count,
            format,
            user_id,
            attempt + 1,
        )
        request_prompt = prompt
        if attempt:
            request_prompt = "\n\n".join(
                [
                    prompt,
                    "CRITICAL CORRECTION: the previous response contained Russian/Cyrillic, repeated an old idea, repeated another script in the same batch, or missed the required voiceover word count. Regenerate with fresh English-only scripts. No Cyrillic characters anywhere in JSON values. Do not reuse the excluded titles, hooks, metaphors, or problem frames.",
                ]
            )
        result = await asyncio.to_thread(notebooklm.ask, request_prompt, notebook_url=notebook_ref_to_url(notebook_ref))
        logger.info("NotebookLM returned %s characters for user %s", len(result.answer), user_id)
        payload = extract_json(result.answer)
        for item in as_script_list(payload):
            if script_payload_has_cyrillic(item):
                continue
            if word_budget and not script_payload_matches_word_budget(item, word_budget):
                continue
            if format in {"short", "youtube"} and script_payload_is_duplicate(item, existing_records, accepted_payloads + items):
                continue
            items.append(item)
        if len(items) >= count:
            break
    return items[:count]


def script_payload_matches_word_budget(payload: dict[str, object], budget: WordBudget) -> bool:
    count = count_spoken_words(payload_text(payload, "voiceover"))
    if budget.min_words <= count <= budget.max_words:
        return True
    logger.info(
        "Rejected generated script outside word budget: words=%s expected=%s-%s target=%s",
        count,
        budget.min_words,
        budget.max_words,
        budget.target_words,
    )
    return False


async def send_scripts(
    chat_id: int,
    records: list[ScriptRecord],
    *,
    thread_id: int | None = None,
    message: Message | None = None,
    edit: bool = False,
) -> None:
    first_chunk = True
    for record in records:
        chunks = split_telegram_text(format_script_message(record))
        for index, chunk in enumerate(chunks):
            is_last = index == len(chunks) - 1
            sent = await edit_or_send_text(
                chat_id,
                chunk,
                thread_id=thread_id,
                message=message if first_chunk else None,
                edit=edit and first_chunk,
                reply_markup=script_keyboard(record.id) if is_last else None,
                disable_web_page_preview=True,
            )
            if first_chunk:
                message = sent
                first_chunk = False


def format_bank_status(user_id: str) -> str:
    counts = storage.count_by_status(user_id, format="short")
    approved = counts.get("approved", 0)
    pending = counts.get("pending", 0)
    rejected = counts.get("rejected", 0)
    used = counts.get("used_for_video", 0)
    return "\n".join(
        [
            "Банк сценариев:",
            f"✅ Одобрено: {approved}/{APPROVED_BANK_TARGET}",
            f"🕒 На проверке: {pending}",
            f"🚫 Отклонено: {rejected}",
            f"🎬 Использовано для видео: {used}",
        ]
    )


async def generate_voiceover_audio(record: ScriptRecord, user_id: str) -> str:
    user_settings = get_user_settings(storage, settings, user_id)
    voice_wpm = await ensure_voice_wpm(user_id)
    word_budget = (
        youtube_word_budget(user_settings.youtube_long_duration_minutes, wpm=voice_wpm)
        if record.format == "youtube"
        else vertical_word_budget(user_settings.vertical_avatar_duration_mode, wpm=voice_wpm)
    )
    initial_speed = estimate_initial_voiceover_speed(
        text=record.voiceover,
        budget=word_budget,
        base_speed=settings.elevenlabs_speed,
        spoken_wpm=voice_wpm,
    )
    logger.info(
        "Initial voiceover speed estimate: script=%s words=%s target_seconds=%s speed=%.3f",
        record.id,
        count_spoken_words(record.voiceover),
        word_budget.target_seconds,
        initial_speed,
    )
    result = await _generate_elevenlabs_audio(record, user_id, speed=initial_speed)
    if result.file_path:
        try:
            analysis = analyze_voiceover_timing(
                text=record.voiceover,
                audio_path=Path(result.file_path),
                budget=word_budget,
                current_speed=initial_speed,
                spoken_wpm=voice_wpm,
            )
            logger.info(
                "Voiceover timing: script=%s words=%s duration=%.2fs wpm=%.1f target=%.2fs speed=%.3f",
                record.id,
                analysis.words,
                analysis.duration_seconds,
                analysis.words_per_minute,
                analysis.target_duration_seconds,
                analysis.current_speed,
            )
            if analysis.should_regenerate:
                logger.info(
                    "Regenerating voiceover with adjusted ElevenLabs speed: %.3f -> %.3f",
                    analysis.current_speed,
                    analysis.recommended_speed,
                )
                result = await _generate_elevenlabs_audio(record, user_id, speed=analysis.recommended_speed)
        except VideoOverlayError:
            logger.exception("Voiceover timing analysis failed; using first generated audio")
    return result.file_path or result.message


async def _generate_elevenlabs_audio(record: ScriptRecord, user_id: str, *, speed: float):
    return await asyncio.to_thread(
        elevenlabs.text_to_speech,
        text=record.voiceover,
        voice_name=get_active_elevenlabs_voice_name(user_id),
        voice_id=get_active_elevenlabs_voice_id(user_id),
        model_id=settings.elevenlabs_model_id,
        speed=speed,
        stability=settings.elevenlabs_stability,
        similarity_boost=settings.elevenlabs_similarity_boost,
        style=settings.elevenlabs_style,
        language=settings.elevenlabs_language,
    )


async def send_generated_audio(chat_id: int, thread_id: int | None, audio_path: str) -> None:
    path = Path(audio_path)
    if not path.exists() or not path.is_file():
        await send_to_chat_thread(chat_id, f"✅ Озвучка создана:\n{audio_path}", thread_id=thread_id)
        return
    await bot.send_audio(
        chat_id,
        FSInputFile(path),
        caption=f"Озвучка сценария: {path.name}",
        message_thread_id=thread_id,
    )


async def get_heygen_avatars(user_id: str, *, refresh: bool = False) -> list[HeyGenAvatar]:
    if not heygen.is_configured():
        raise HeyGenError("HEYGEN_API_KEY не задан")
    if refresh or user_id not in HEYGEN_AVATAR_CACHE:
        HEYGEN_AVATAR_CACHE[user_id] = await heygen.list_avatar_looks()
    return HEYGEN_AVATAR_CACHE[user_id]


async def get_elevenlabs_voices(user_id: str, *, refresh: bool = False) -> list[ElevenLabsVoice]:
    if not elevenlabs_api.is_configured():
        raise ElevenLabsAPIError("ELEVENLABS_API_KEY не задан")
    if refresh or user_id not in ELEVENLABS_VOICE_CACHE:
        ELEVENLABS_VOICE_CACHE[user_id] = await elevenlabs_api.list_voices()
    return ELEVENLABS_VOICE_CACHE[user_id]


def nav_index(index: int, total: int) -> int:
    if total <= 0:
        return 0
    return index % total


def avatar_keyboard(index: int, total: int, avatar: HeyGenAvatar) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [button("✅ Выбрать этот аватар", callback_data=f"heygen_avatar:set:{index}", style="success")],
        [
            button("⬅️", callback_data=f"heygen_avatar:show:{nav_index(index - 1, total)}", style="secondary"),
            button(f"{index + 1}/{total}", callback_data="noop", style="secondary"),
            button("➡️", callback_data=f"heygen_avatar:show:{nav_index(index + 1, total)}", style="secondary"),
        ],
    ]
    if avatar.preview_video_url:
        rows.append([button("▶️ Посмотреть пример видео", url=avatar.preview_video_url, style="primary")])
    rows.append([button("⬅️ Назад к настройкам", callback_data="main:settings", style="secondary")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def format_avatar_card(avatar: HeyGenAvatar, user_id: str, index: int, total: int) -> str:
    active_marker = "✅ Активный" if avatar.id == get_active_heygen_avatar_id(user_id) else "Не активен"
    return "\n".join(
        [
            f"🎭 HeyGen avatar {index + 1}/{total}",
            f"{active_marker}",
            f"Имя: {avatar.name}",
            f"ID: {avatar.id}",
        ]
    )


def voice_keyboard(index: int, total: int, voice: ElevenLabsVoice) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [button("✅ Выбрать этот голос", callback_data=f"eleven_voice:set:{index}", style="success")],
        [
            button("⬅️", callback_data=f"eleven_voice:show:{nav_index(index - 1, total)}", style="secondary"),
            button(f"{index + 1}/{total}", callback_data="noop", style="secondary"),
            button("➡️", callback_data=f"eleven_voice:show:{nav_index(index + 1, total)}", style="secondary"),
        ],
    ]
    if voice.preview_url:
        rows.append([button("▶️ Послушать пример", url=voice.preview_url, style="primary")])
    rows.append([button("⬅️ Назад к настройкам", callback_data="main:settings", style="secondary")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def overlay_keyboard(format: str) -> InlineKeyboardMarkup:
    label = format_label(format)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [button(f"🖼 Загрузить плашку для {label}", callback_data=f"overlay:upload:{format}", style="primary")],
            [button(f"⏱ Когда показывать {label}", callback_data=f"overlay:percent:{format}")],
            [button(f"👀 Проверить текущую плашку", callback_data=f"overlay:show:{format}")],
            [button("⬅️ Назад к настройкам", callback_data="main:settings", style="secondary")],
        ]
    )


def overlay_summary(user_id: str, format: str) -> str:
    label = format_label(format)
    overlay_path = get_overlay_path(user_id, format)
    exists = bool(overlay_path and overlay_path.exists())
    percent = get_overlay_start_percent(user_id, format)
    path_text = str(overlay_path) if overlay_path else "не загружена"
    return "\n".join(
        [
            f"Плашка {label}:",
            f"Файл: {'✅ есть' if exists else 'не загружена'}",
            f"Путь: {path_text}",
            f"Появление: с {percent}% хронометража до конца видео",
        ]
    )


async def show_heygen_avatar(
    chat_id: int,
    user_id: str,
    *,
    thread_id: int | None,
    index: int = 0,
    message: Message | None = None,
    edit: bool = False,
) -> None:
    avatars = await get_heygen_avatars(user_id)
    if not avatars:
        await edit_or_send_text(
            chat_id,
            "HeyGen не вернул аватаров.",
            thread_id=thread_id,
            message=message,
            edit=edit,
            reply_markup=settings_keyboard(),
        )
        return
    index = nav_index(index, len(avatars))
    avatar = avatars[index]
    caption = format_avatar_card(avatar, user_id, index, len(avatars))
    reply_markup = avatar_keyboard(index, len(avatars), avatar)
    if edit and message:
        try:
            if avatar.preview_image_url:
                await message.edit_media(
                    media=InputMediaPhoto(media=avatar.preview_image_url, caption=caption),
                    reply_markup=reply_markup,
                )
            else:
                await message.edit_text(caption, reply_markup=reply_markup)
            return
        except TelegramBadRequest as exc:
            if "message is not modified" in str(exc).lower():
                return
            logger.warning("Failed to edit HeyGen avatar card, sending a new one: %s", exc)
            try:
                await message.delete()
            except TelegramBadRequest:
                pass
    if avatar.preview_image_url:
        await bot.send_photo(
            chat_id,
            avatar.preview_image_url,
            caption=caption,
            message_thread_id=thread_id,
            reply_markup=reply_markup,
        )
    else:
        await send_to_chat_thread(
            chat_id,
            caption,
            thread_id=thread_id,
            reply_markup=reply_markup,
        )


def format_voice_card(voice: ElevenLabsVoice, user_id: str, index: int, total: int) -> str:
    active_marker = "✅ Активный" if voice.id == get_active_elevenlabs_voice_id(user_id) else "Не активен"
    return "\n".join(
        [
            f"🎙 ElevenLabs voice {index + 1}/{total}",
            f"{active_marker}",
            f"Имя: {voice.name}",
            f"ID: {voice.id}",
            f"Категория: {voice.category or 'не указана'}",
        ]
    )


async def show_elevenlabs_voice(
    chat_id: int,
    user_id: str,
    *,
    thread_id: int | None,
    index: int = 0,
    message: Message | None = None,
    edit: bool = False,
) -> None:
    voices = await get_elevenlabs_voices(user_id)
    if not voices:
        await edit_or_send_text(
            chat_id,
            "ElevenLabs не вернул голосов.",
            thread_id=thread_id,
            message=message,
            edit=edit,
            reply_markup=settings_keyboard(),
        )
        return
    index = nav_index(index, len(voices))
    voice = voices[index]
    await edit_or_send_text(
        chat_id,
        format_voice_card(voice, user_id, index, len(voices)),
        thread_id=thread_id,
        message=message,
        edit=edit,
        reply_markup=voice_keyboard(index, len(voices), voice),
    )


async def send_generated_video(chat_id: int, thread_id: int | None, video_url: str, caption: str) -> None:
    try:
        await bot.send_document(chat_id, video_url, caption=caption, message_thread_id=thread_id)
    except Exception:
        logger.exception("Telegram failed to send HeyGen video document by URL")
        await send_to_chat_thread(chat_id, f"{caption}\n\n{video_url}", thread_id=thread_id)


async def process_overlay_if_configured(user_id: str, record: ScriptRecord, video_path: Path) -> Path | None:
    overlay_path = get_overlay_path(user_id, record.format)
    if not overlay_path or not overlay_path.exists():
        return None
    start_percent = get_overlay_start_percent(user_id, record.format)
    output_path = settings.video_output_directory / f"final_{record.id}.mp4"
    result = await asyncio.to_thread(
        apply_overlay,
        video_path=video_path,
        overlay_path=overlay_path,
        output_path=output_path,
        start_percent=start_percent,
    )
    logger.info(
        "Overlay applied to script %s: start %.2fs / duration %.2fs",
        record.id,
        result.start_seconds,
        result.duration_seconds,
    )
    return result.output_path


async def process_post_heygen_visuals_if_enabled(record: ScriptRecord, video_path: Path) -> Path:
    if not settings.post_heygen_visuals_enabled:
        return video_path
    asset_dir = settings.video_output_directory / "visual_assets" / str(record.id)
    montage_dir = settings.video_output_directory / "montage" / str(record.id)
    try:
        montage_path = await asyncio.to_thread(
            render_montage_if_configured,
            record=record,
            video_path=video_path,
            output_dir=montage_dir,
            config=montage_renderer_config,
        )
        if montage_path:
            logger.info("Post-HeyGen montage rendered with external renderer: %s", montage_path)
            return await apply_cover_frame_to_video(record, montage_path, asset_dir)
    except VideoOverlayError as exc:
        logger.warning("External montage renderer failed; falling back to KIE+ffmpeg overlays: %s", exc)

    assets = await asyncio.to_thread(
        generate_post_heygen_assets,
        record=record,
        output_dir=asset_dir,
        broll_count=settings.post_heygen_broll_count,
        kie_client=kie_image,
        reference_paths=thumbnail_reference_paths(
            storage=storage,
            asset_store=asset_store,
            settings=settings,
            user_id=record.user_id,
            target=target_from_record_format(record.format),
        ),
    )
    output_path = settings.video_output_directory / f"visual_{record.id}.mp4"
    result = await asyncio.to_thread(
        apply_post_heygen_visuals,
        video_path=video_path,
        assets=assets,
        output_path=output_path,
        cover_seconds=settings.post_heygen_cover_seconds,
        broll_seconds=settings.post_heygen_broll_seconds,
    )
    logger.info(
        "Post-HeyGen visuals applied to script %s: cover %.2fs, broll starts=%s",
        record.id,
        result.cover_seconds,
        result.broll_starts,
    )
    return result.output_path


async def apply_cover_frame_to_video(record: ScriptRecord, video_path: Path, asset_dir: Path) -> Path:
    assets = await asyncio.to_thread(
        generate_post_heygen_assets,
        record=record,
        output_dir=asset_dir,
        broll_count=0,
        kie_client=kie_image,
        reference_paths=thumbnail_reference_paths(
            storage=storage,
            asset_store=asset_store,
            settings=settings,
            user_id=record.user_id,
            target=target_from_record_format(record.format),
        ),
    )
    output_path = settings.video_output_directory / f"{video_path.stem}_cover.mp4"
    return await asyncio.to_thread(
        apply_cover_frame,
        video_path=video_path,
        cover_path=assets.cover_path,
        output_path=output_path,
        cover_seconds=settings.post_heygen_cover_seconds,
    )


async def send_final_video(chat_id: int, thread_id: int | None, user_id: str, record: ScriptRecord, video_url: str) -> None:
    caption = f"🎬 Готовый ролик\nСценарий #{record.id}: {record.title}"
    cleaned = cleanup_old_videos(settings.video_output_directory, keep_days=settings.video_keep_days)
    if cleaned:
        logger.info("Cleaned %s old video files from %s", cleaned, settings.video_output_directory)
    raw_path = settings.video_output_directory / f"heygen_{record.id}.mp4"
    try:
        await download_video(video_url, raw_path)
    except VideoOverlayError as exc:
        logger.exception("Failed to download HeyGen video")
        await send_to_chat_thread(chat_id, f"⚠️ Не удалось скачать видео файлом: {exc}\nОтправляю ссылку.", thread_id=thread_id)
        await send_generated_video(chat_id, thread_id, video_url, caption)
        return

    final_path = raw_path
    try:
        final_path = await process_post_heygen_visuals_if_enabled(record, final_path)
    except VideoOverlayError as exc:
        logger.exception("Failed to apply post-HeyGen visuals")
        await send_to_chat_thread(chat_id, f"⚠️ Cover/перебивки не наложил: {exc}", thread_id=thread_id)

    if final_path and final_path.exists():
        await send_final_video_variants(
            chat_id=chat_id,
            thread_id=thread_id,
            user_id=user_id,
            source_path=final_path,
            output_stem=f"heygen_{record.id}",
            caption_prefix=caption,
        )
        return
    await send_generated_video(chat_id, thread_id, video_url, caption)


async def render_existing_heygen_video(
    chat_id: int,
    thread_id: int | None,
    user_id: str,
    record: ScriptRecord,
    heygen_video_id: str,
) -> None:
    if not heygen.is_configured():
        await send_to_chat_thread(chat_id, "⚠️ HEYGEN_API_KEY не задан.", thread_id=thread_id)
        return

    status_msg = await send_to_chat_thread(
        chat_id,
        (
            f"🎬 Принял HeyGen video id: {heygen_video_id}\n"
            f"Беру сценарий #{record.id} и собираю vertical smart montage без повторной генерации HeyGen."
        ),
        thread_id=thread_id,
    )
    ready = await heygen.wait_for_video(heygen_video_id)
    if not ready.video_url:
        raise HeyGenError(f"HeyGen не вернул ссылку на видео: {ready.raw}")

    cleanup_old_videos(settings.video_output_directory, keep_days=settings.video_keep_days)
    raw_path = settings.video_output_directory / f"existing_heygen_{record.id}_{heygen_video_id}.mp4"
    await download_video(ready.video_url, raw_path)
    montage_path = await process_post_heygen_visuals_if_enabled(record, raw_path)
    if not montage_path:
        raise VideoOverlayError("Post-HeyGen renderer не вернул файл.")

    await status_msg.edit_text("✅ Smart montage и cover готовы. Готовлю YouTube и Instagram версии.")
    await send_final_video_variants(
        chat_id=chat_id,
        thread_id=thread_id,
        user_id=user_id,
        source_path=montage_path,
        output_stem=f"existing_heygen_{record.id}_{heygen_video_id}",
        caption_prefix=f"🎬 Smart montage из HeyGen #{heygen_video_id}\nСценарий #{record.id}: {record.title}",
    )


async def send_final_video_variants(
    *,
    chat_id: int,
    thread_id: int | None,
    user_id: str,
    source_path: Path,
    output_stem: str,
    caption_prefix: str,
) -> None:
    variants = await asyncio.to_thread(
        build_final_video_variants,
        storage=storage,
        user_id=user_id,
        source_path=source_path,
        output_dir=settings.video_output_directory,
        output_stem=output_stem,
    )
    for variant in variants:
        caption = f"{caption_prefix}\nФормат: {variant.label}"
        await bot.send_document(chat_id, FSInputFile(variant.path), caption=caption, message_thread_id=thread_id)


async def create_and_send_video(chat_id: int, thread_id: int | None, user_id: str, record: ScriptRecord, audio_path: str) -> None:
    path = Path(audio_path)
    if not path.exists() or not path.is_file():
        await send_to_chat_thread(chat_id, f"✅ Озвучка создана:\n{audio_path}\n\n⚠️ HeyGen не получил файл аудио.", thread_id=thread_id)
        return
    avatar_id = get_active_heygen_avatar_id(user_id)
    avatar_name = get_active_heygen_avatar_name(user_id) or avatar_id
    if not heygen.is_configured():
        await send_generated_audio(chat_id, thread_id, audio_path)
        await send_to_chat_thread(chat_id, "⚠️ HEYGEN_API_KEY не задан, поэтому отправил только озвучку.", thread_id=thread_id)
        return
    if not avatar_id:
        await send_generated_audio(chat_id, thread_id, audio_path)
        await send_to_chat_thread(chat_id, "⚠️ HeyGen avatar не выбран. Открой /settings → 🎭 Аватар HeyGen.", thread_id=thread_id)
        return

    heygen_api_version, avatar_engine = get_heygen_generation_settings(user_id)
    motion_prompt = default_photo_avatar_motion_prompt() if heygen_api_version == "v3" and avatar_engine == "avatar_iv" else None
    expressiveness = (os.getenv("HEYGEN_PHOTO_AVATAR_EXPRESSIVENESS") or "high").strip().lower() if motion_prompt else None
    status_msg = await send_to_chat_thread(
        chat_id,
        (
            f"🎭 Отправляю озвучку в HeyGen {heygen_api_version}"
            f"{f' ({avatar_engine})' if heygen_api_version == 'v3' else ''}.\n"
            f"Аватар: {avatar_name}\nЭто может занять несколько минут."
        ),
        thread_id=thread_id,
    )
    asset_id = await heygen.upload_audio_file(path)
    created = await heygen.create_video_from_audio(
        avatar_id=avatar_id,
        audio_asset_id=asset_id,
        title=record.title,
        api_version=heygen_api_version,
        engine=avatar_engine,
        motion_prompt=motion_prompt,
        expressiveness=expressiveness,
    )
    await status_msg.edit_text(f"🎬 HeyGen принял задачу: {created.video_id}\nЖду готовый ролик...")
    ready = await heygen.wait_for_video(created.video_id)
    if not ready.video_url:
        raise HeyGenError(f"HeyGen не вернул ссылку на видео: {ready.raw}")
    await status_msg.edit_text("✅ Видео готово. Отправляю в эту тему.")
    await send_final_video(chat_id, thread_id, user_id, record, ready.video_url)


async def produce_media_for_approved_script(chat_id: int, thread_id: int | None, user_id: str, record: ScriptRecord) -> None:
    audio_path = ""
    try:
        status_msg = await send_to_chat_thread(
            chat_id,
            f"✅ Сценарий #{record.id} принят.\n🎙 Создаю озвучку ElevenLabs...",
            thread_id=thread_id,
        )
        audio_path = await generate_voiceover_audio(record, user_id)
        await status_msg.edit_text(f"✅ Озвучка сценария #{record.id} готова.\n🎭 Готовлю видео через HeyGen...")
        await create_and_send_video(chat_id, thread_id, user_id, record, audio_path)
    except ElevenLabsMCPError as exc:
        await send_to_chat_thread(
            chat_id,
            f"✅ Сценарий #{record.id} принят.\n⚠️ Озвучку пока не создал: {exc}",
            thread_id=thread_id,
        )
    except HeyGenError as exc:
        logger.exception("Failed to create HeyGen video")
        if audio_path:
            await send_generated_audio(chat_id, thread_id, audio_path)
        await send_to_chat_thread(
            chat_id,
            f"✅ Сценарий #{record.id} принят.\n⚠️ Видео HeyGen пока не создал: {exc}",
            thread_id=thread_id,
        )
    except Exception as exc:
        logger.exception("Failed to produce approved script media")
        await send_to_chat_thread(
            chat_id,
            f"✅ Сценарий #{record.id} принят.\n⚠️ Не удалось создать видео: {exc}",
            thread_id=thread_id,
        )


def settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [button("🎭 Выбрать аватар", callback_data="settings:heygen_avatars", style="primary")],
            [button("🎙 Выбрать голос", callback_data="settings:elevenlabs_voices", style="primary")],
            [button("🖼 Плашка YouTube", callback_data="settings:overlay:youtube")],
            [button("📱 Плашка Shorts", callback_data="settings:overlay:shorts")],
            [button("📸 Плашка Reels", callback_data="settings:overlay:reels")],
            [button("✂️ Настройки Vizard", callback_data="settings:vizard")],
            [button("📚 NotebookLM база", callback_data="settings:edit:notebook_id")],
            [button("🎯 Оффер и аудитория", callback_data="settings:edit:offer_context")],
            [button("🗣 Стиль автора", callback_data="settings:edit:author_style")],
            [button("🧲 CTA в сценариях", callback_data="settings:edit:cta_mix")],
            [button("👀 Показать все настройки", callback_data="settings:show")],
            [button("⬅️ Главное меню", callback_data="main:home")],
        ]
    )


def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [button("✅ Проверить сценарии", callback_data="main:review", style="primary")],
            [button("📝 Сгенерировать вручную", callback_data="main:refill")],
            [button("📊 Статус сценариев", callback_data="main:bank")],
        ]
    )


def format_current_settings(user_id: str) -> str:
    notebook = get_notebook_ref(user_id) or "не задано"
    author_style = get_author_style(user_id) or "по умолчанию"
    offer_context = get_offer_context(user_id)
    cta_mix = get_cta_mix(user_id)
    voice_name = get_active_elevenlabs_voice_name(user_id)
    voice_id = get_active_elevenlabs_voice_id(user_id) or "не задан"
    avatar_name = get_active_heygen_avatar_name(user_id, "horizontal") or "не выбран"
    avatar_id = get_active_heygen_avatar_id(user_id, "horizontal") or "не задан"
    vertical_avatar_name = get_active_heygen_avatar_name(user_id, "vertical") or "не выбран"
    vertical_avatar_id = get_active_heygen_avatar_id(user_id, "vertical") or "не задан"
    return "\n\n".join(
        [
            "Текущие настройки контента:",
            f"База NotebookLM:\n{notebook}",
            f"HeyGen avatar YouTube:\n{avatar_name}\n{avatar_id}",
            f"HeyGen avatar Instagram/Reels:\n{vertical_avatar_name}\n{vertical_avatar_id}",
            f"ElevenLabs voice:\n{voice_name}\n{voice_id}",
            overlay_summary(user_id, "shorts"),
            overlay_summary(user_id, "reels"),
            overlay_summary(user_id, "youtube"),
            format_vizard_settings(get_user_settings(storage, settings, user_id).vizard),
            f"Микс CTA:\n{cta_mix}",
            f"Голос автора:\n{author_style}",
            f"Контекст оффера:\n{offer_context}",
        ]
    )


async def start_review_session(
    chat_id: int,
    user_id: str,
    *,
    thread_id: int | None = None,
    message: Message | None = None,
    edit: bool = False,
) -> int:
    removed = reject_cyrillic_pending_scripts(user_id)
    pending = storage.count_scripts(user_id, format="short", status="pending")
    if pending == 0:
        if removed:
            await edit_or_send_text(
                chat_id,
                f"Убрал русские сценарии из очереди: {removed}. Запусти /refill для новой английской пачки.",
                thread_id=thread_id,
                message=message,
                edit=edit,
            )
            return 0
        await edit_or_send_text(
            chat_id,
            "Нет сценариев на ревью. Запусти /refill, чтобы создать новую пачку.",
            thread_id=thread_id,
            message=message,
            edit=edit,
        )
        return 0
    set_review_session(user_id, pending)
    record = storage.list_scripts(user_id, format="short", status="pending", limit=1)[0]
    await edit_or_send_text(
        chat_id,
        format_review_message(record, user_id),
        thread_id=thread_id,
        message=message,
        edit=edit,
        reply_markup=script_keyboard(record.id),
        disable_web_page_preview=True,
    )
    return pending


async def edit_to_next_review_card(callback: CallbackQuery, user_id: str) -> None:
    reject_cyrillic_pending_scripts(user_id)
    records = storage.list_scripts(user_id, format="short", status="pending", limit=1)
    if records:
        record = records[0]
        await callback.message.edit_text(
            format_review_message(record, user_id),
            reply_markup=script_keyboard(record.id),
            disable_web_page_preview=True,
        )
        return

    approved = storage.count_scripts(user_id, format="short", status="approved")
    if approved <= APPROVED_BANK_TARGET:
        await callback.message.edit_text(
            "\n".join(
                [
                    "Проверка очереди завершена.",
                    f"Одобрено в банке: {approved}/{APPROVED_BANK_TARGET}.",
                    f"Генерирую новую пачку из {REFILL_BATCH_SIZE} сценариев...",
                ]
            ),
            reply_markup=None,
            disable_web_page_preview=True,
        )
        try:
            await generate_scripts_for_user(user_id, REFILL_BATCH_SIZE, format="short")
        except Exception as exc:
            logger.exception("Failed to refill script bank after review")
            await callback.message.edit_text(f"❌ Не удалось пополнить банк сценариев: {exc}")
            return
        set_review_session(user_id, storage.count_scripts(user_id, format="short", status="pending"))
        await edit_to_next_review_card(callback, user_id)
        return

    await callback.message.edit_text(
        "\n".join(["Проверка очереди завершена.", format_bank_status(user_id)]),
        reply_markup=main_keyboard(),
        disable_web_page_preview=True,
    )


async def refill_if_needed(
    chat_id: int,
    user_id: str,
    *,
    thread_id: int | None = None,
    message: Message | None = None,
    edit: bool = False,
    force: bool = False,
    topic_hint: str | None = None,
) -> None:
    approved = storage.count_scripts(user_id, format="short", status="approved")
    pending = storage.count_scripts(user_id, format="short", status="pending")
    if not force and pending > 0:
        status_msg = await edit_or_send_text(
            chat_id,
            f"Уже есть сценарии на проверке: {pending}. Открываю очередь.",
            thread_id=thread_id,
            message=message,
            edit=edit,
        )
        await start_review_session(chat_id, user_id, thread_id=thread_id, message=status_msg, edit=True)
        return
    if not force and approved > APPROVED_BANK_TARGET:
        await edit_or_send_text(
            chat_id,
            "\n".join(
                [
                    f"Банк уже заполнен: {approved}/{APPROVED_BANK_TARGET}.",
                    "Новых сценариев на проверке нет.",
                    "",
                    format_bank_status(user_id),
                ]
            ),
            thread_id=thread_id,
            message=message,
            edit=edit,
        )
        return

    status_msg = await edit_or_send_text(
        chat_id,
        f"⏳ Банк одобренных: {approved}/{APPROVED_BANK_TARGET}. Генерирую пачку из {REFILL_BATCH_SIZE} сценариев...",
        thread_id=thread_id,
        message=message,
        edit=edit,
    )
    try:
        logger.info("Starting script bank refill for user %s: approved=%s pending=%s", user_id, approved, pending)
        await status_msg.edit_text(
            "⏳ Отправил запрос в NotebookLM.\n"
            "Обычно это занимает 1-4 минуты, но для большой пачки жду до 15 минут."
        )
        await generate_scripts_for_user(user_id, REFILL_BATCH_SIZE, format="short", topic_hint=topic_hint)
    except Exception as exc:
        logger.exception("Failed to refill script bank")
        await status_msg.edit_text(f"❌ Не удалось пополнить банк сценариев: {exc}")
        return
    await status_msg.edit_text("✅ Новая пачка сценариев готова.")
    await start_review_session(chat_id, user_id, thread_id=thread_id, message=status_msg, edit=True)


@dp.message(Command("start", "help"))
async def start(message: Message) -> None:
    user_id = activate_from_message(message)
    clear_pending_edit(user_id)
    await answer_in_same_thread(
        message,
        "\n".join(
            [
                "Бот готовит сценарии из NotebookLM и отправляет их на апрув.",
                "",
                "Команды:",
                "/review - открыть очередь сценариев на проверку",
                "/refill - вручную пополнить банк сценариев",
                "/bank - статус банка сценариев",
                "/daily_scripts - вручную сгенерировать 10 и открыть очередь",
                "/youtube_script - сгенерировать недельный YouTube-сценарий",
                "/vizard <youtube_url> - отправить YouTube-видео в Vizard и получить нарезку",
                "/formats - собрать Turan-форматы из последнего одобренного сценария",
                "/settings - служебные настройки, если нужно что-то поменять вручную",
            ]
        ),
        reply_markup=main_keyboard(),
    )


@dp.message(Command("settings"))
async def settings_menu(message: Message) -> None:
    user_id = activate_from_message(message)
    clear_pending_edit(user_id)
    if settings.miniapp_url:
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🎬 Открыть Mini App", web_app=WebAppInfo(url=settings.miniapp_url))],
                [button("⬅️ Главное меню", callback_data="main:home")],
            ]
        )
    else:
        markup = main_keyboard()
    await answer_in_same_thread(
        message,
        "Настройки убрал из основного меню, чтобы не мешали ревью сценариев. Менять их удобнее в Mini App.",
        reply_markup=markup,
    )


@dp.message(Command("set_notebook"))
async def set_notebook(message: Message) -> None:
    user_id = activate_from_message(message)
    clear_pending_edit(user_id)
    value = (message.text or "").split(maxsplit=1)
    if len(value) < 2 or not value[1].strip():
        await answer_in_same_thread(message, "Отправь так: /set_notebook <notebook_id>")
        return
    storage.set_setting(user_id, "notebook_id", value[1].strip())
    await answer_in_same_thread(message, "✅ NotebookLM-база сохранена.")


@dp.message(Command("set_style"))
async def set_style(message: Message) -> None:
    user_id = activate_from_message(message)
    clear_pending_edit(user_id)
    value = (message.text or "").split(maxsplit=1)
    if len(value) < 2 or not value[1].strip():
        await answer_in_same_thread(message, "Отправь так: /set_style <как говорит автор, примеры фраз, тон>")
        return
    storage.set_setting(user_id, "author_style", value[1].strip())
    await answer_in_same_thread(message, "✅ Стиль автора сохранен. Теперь сценарии будут писаться в этом голосе.")


@dp.message(lambda message: message.from_user and str(message.from_user.id) in PENDING_OVERLAY_UPLOADS)
async def handle_overlay_upload(message: Message) -> None:
    user_id = activate_from_message(message)
    format = PENDING_OVERLAY_UPLOADS.pop(user_id)
    label = format_label(format)
    photo = message.photo[-1] if message.photo else None
    document = message.document
    if not photo and not document:
        await answer_in_same_thread(message, f"Отправь картинку для плашки {label}: PNG/JPG/WebP файлом или фото.")
        PENDING_OVERLAY_UPLOADS[user_id] = format
        return

    file_id = photo.file_id if photo else document.file_id
    file_name = document.file_name if document and document.file_name else f"{format}_overlay.jpg"
    suffix = Path(file_name).suffix.lower() or ".jpg"
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        await answer_in_same_thread(message, "Плашка должна быть картинкой: PNG, JPG или WebP.")
        return

    destination = overlay_directory(user_id) / f"{format}_overlay{suffix}"
    file = await bot.get_file(file_id)
    if not file.file_path:
        await answer_in_same_thread(message, "Telegram не вернул путь к файлу. Попробуй отправить картинку еще раз.")
        return
    await bot.download_file(file.file_path, destination)
    set_overlay_path(user_id, format, destination)
    await answer_in_same_thread(
        message,
        f"✅ Плашка {label} сохранена.\n{overlay_summary(user_id, format)}",
        reply_markup=overlay_keyboard(format),
    )


@dp.message(F.text, lambda message: str(message.from_user.id) in PENDING_SETTING_EDITS and not (message.text or "").startswith("/"))
async def handle_pending_setting_edit(message: Message) -> None:
    user_id = activate_from_message(message)
    key = PENDING_SETTING_EDITS.pop(user_id)
    value = (message.text or "").strip()
    if not value:
        await answer_in_same_thread(message, "Пустое значение не сохранил. Нажми кнопку настройки еще раз.")
        return
    if key.startswith("overlay_percent:"):
        format = key.split(":", 1)[1]
        try:
            percent = set_overlay_start_percent(user_id, format, value)
        except ValueError as exc:
            await answer_in_same_thread(message, str(exc), reply_markup=overlay_keyboard(format))
            return
        await answer_in_same_thread(
            message,
            f"✅ Плашка {format_label(format)} будет появляться с {percent}% видео.",
            reply_markup=overlay_keyboard(format),
        )
        return
    storage.set_setting(user_id, key, value)
    labels = {
        "offer_context": "Контекст оффера",
        "author_style": "Голос автора",
        "cta_mix": "Микс CTA",
        "notebook_id": "База NotebookLM",
    }
    await answer_in_same_thread(message, f"✅ {labels.get(key, key)} сохранен.", reply_markup=settings_keyboard())


@dp.message(Command("cancel"))
async def cancel_pending_edit(message: Message) -> None:
    user_id = activate_from_message(message)
    if PENDING_SETTING_EDITS.pop(user_id, None):
        await answer_in_same_thread(message, "Ок, режим настройки отменен.", reply_markup=main_keyboard())
    else:
        await answer_in_same_thread(message, "Нет активной настройки.", reply_markup=main_keyboard())


@dp.callback_query(F.data.startswith("main:"))
async def main_callback(callback: CallbackQuery) -> None:
    action = (callback.data or "").split(":", 1)[1]
    user_id = activate_from_callback(callback)
    await callback.answer()
    if action == "settings":
        if settings.miniapp_url:
            markup = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🎬 Открыть Mini App", web_app=WebAppInfo(url=settings.miniapp_url))],
                    [button("⬅️ Главное меню", callback_data="main:home")],
                ]
            )
        else:
            markup = main_keyboard()
        await edit_or_send_text(
            callback.message.chat.id,
            "Настройки убрал из основного меню, чтобы не мешали ревью сценариев. Менять их удобнее в Mini App.",
            thread_id=message_thread_id(callback.message),
            message=callback.message,
            edit=True,
            reply_markup=markup,
        )
        return
    if action == "home":
        await edit_or_send_text(
            callback.message.chat.id,
            "Главное меню. Что делаем дальше?",
            thread_id=message_thread_id(callback.message),
            message=callback.message,
            edit=True,
            reply_markup=main_keyboard(),
        )
        return
    if action == "bank":
        await edit_or_send_text(
            callback.message.chat.id,
            format_bank_status(user_id),
            thread_id=message_thread_id(callback.message),
            message=callback.message,
            edit=True,
            reply_markup=main_keyboard(),
        )
        return
    if action == "review":
        await start_review_session(
            callback.message.chat.id,
            user_id,
            thread_id=message_thread_id(callback.message),
            message=callback.message,
            edit=True,
        )
        return
    if action == "refill":
        await refill_if_needed(
            callback.message.chat.id,
            user_id,
            thread_id=message_thread_id(callback.message),
            message=callback.message,
            edit=True,
        )
        return


@dp.callback_query(F.data.startswith("settings:"))
async def settings_callback(callback: CallbackQuery) -> None:
    parts = (callback.data or "").split(":")
    user_id = activate_from_callback(callback)
    if len(parts) >= 2 and parts[1] == "show":
        await callback.answer()
        await edit_or_send_text(
            callback.message.chat.id,
            format_current_settings(user_id),
            thread_id=message_thread_id(callback.message),
            message=callback.message,
            edit=True,
            reply_markup=settings_keyboard(),
        )
        return
    if len(parts) >= 2 and parts[1] == "heygen_avatars":
        await callback.answer("Загружаю аватары")
        try:
            await show_heygen_avatar(
                callback.message.chat.id,
                user_id,
                thread_id=message_thread_id(callback.message),
                message=callback.message,
                edit=True,
            )
        except HeyGenError as exc:
            await edit_or_send_text(
                callback.message.chat.id,
                f"⚠️ Не удалось получить HeyGen avatars: {exc}",
                thread_id=message_thread_id(callback.message),
                message=callback.message,
                edit=True,
                reply_markup=settings_keyboard(),
            )
        return
    if len(parts) >= 2 and parts[1] == "elevenlabs_voices":
        await callback.answer("Загружаю голоса")
        try:
            await show_elevenlabs_voice(
                callback.message.chat.id,
                user_id,
                thread_id=message_thread_id(callback.message),
                message=callback.message,
                edit=True,
            )
        except ElevenLabsAPIError as exc:
            await edit_or_send_text(
                callback.message.chat.id,
                f"⚠️ Не удалось получить ElevenLabs voices: {exc}",
                thread_id=message_thread_id(callback.message),
                message=callback.message,
                edit=True,
                reply_markup=settings_keyboard(),
            )
        return
    if len(parts) == 3 and parts[1] == "overlay" and parts[2] in {"short", "youtube", "shorts", "reels"}:
        await callback.answer()
        await edit_or_send_text(
            callback.message.chat.id,
            overlay_summary(user_id, parts[2]),
            thread_id=message_thread_id(callback.message),
            message=callback.message,
            edit=True,
            reply_markup=overlay_keyboard(parts[2]),
        )
        return
    if len(parts) == 2 and parts[1] == "vizard":
        await callback.answer()
        await edit_or_send_text(
            callback.message.chat.id,
            format_vizard_settings(get_user_settings(storage, settings, user_id).vizard),
            thread_id=message_thread_id(callback.message),
            message=callback.message,
            edit=True,
            reply_markup=vizard_settings_keyboard(),
        )
        return
    if len(parts) != 3 or parts[1] != "edit":
        await callback.answer("Некорректная команда", show_alert=True)
        return
    key = parts[2]
    if key not in {"offer_context", "author_style", "cta_mix", "notebook_id"}:
        await callback.answer("Неизвестная настройка", show_alert=True)
        return
    PENDING_SETTING_EDITS[user_id] = key
    prompts = {
        "offer_context": (
            "Отправь контекст оффера одним сообщением.\n\n"
            "Пример:\n"
            "We sell a high-ticket Amazon growth mentorship for existing sellers. "
            "Entry starts at $1400. The offer helps fix cash flow, PPC, product economics, operations, and scaling. "
            "CTA must feel specific to the script, never pasted on."
        ),
        "author_style": (
            "Отправь описание голоса автора одним сообщением.\n\n"
            "Пример:\n"
            "Direct, calm, operator-to-operator. Short punchy sentences. No hype. Uses practical examples and calls out hidden business leaks."
        ),
        "cta_mix": (
            "Отправь микс CTA одним сообщением.\n\n"
            "Пример:\n"
            "50% none, 35% soft, 15% direct"
        ),
        "notebook_id": (
            "Отправь NotebookLM ID или полную ссылку.\n\n"
            "Пример:\n"
            "https://notebooklm.google.com/notebook/055d2c3f-77ce-4d3c-8749-61c538c6c4d6"
        ),
    }
    await callback.answer("Отправь значение следующим сообщением")
    await edit_or_send_text(
        callback.message.chat.id,
        prompts[key],
        thread_id=message_thread_id(callback.message),
        message=callback.message,
        edit=True,
    )


@dp.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery) -> None:
    await callback.answer()


@dp.callback_query(F.data.startswith("heygen_avatar:"))
async def heygen_avatar_callback(callback: CallbackQuery) -> None:
    parts = (callback.data or "").split(":")
    user_id = activate_from_callback(callback)
    if len(parts) != 3:
        await callback.answer("Некорректная команда", show_alert=True)
        return
    action = parts[1]
    try:
        index = int(parts[2])
    except ValueError:
        await callback.answer("Некорректный номер", show_alert=True)
        return
    try:
        avatars = await get_heygen_avatars(user_id)
    except HeyGenError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    if not avatars:
        await callback.answer("Аватары не найдены", show_alert=True)
        return
    index = nav_index(index, len(avatars))
    avatar = avatars[index]
    if action == "set":
        set_active_heygen_avatar(user_id, avatar)
        await callback.answer("Аватар активирован")
        await show_heygen_avatar(
            callback.message.chat.id,
            user_id,
            thread_id=message_thread_id(callback.message),
            index=index,
            message=callback.message,
            edit=True,
        )
        return
    if action == "show":
        await callback.answer()
        await show_heygen_avatar(
            callback.message.chat.id,
            user_id,
            thread_id=message_thread_id(callback.message),
            index=index,
            message=callback.message,
            edit=True,
        )
        return
    await callback.answer("Некорректное действие", show_alert=True)


@dp.callback_query(F.data.startswith("eleven_voice:"))
async def eleven_voice_callback(callback: CallbackQuery) -> None:
    parts = (callback.data or "").split(":")
    user_id = activate_from_callback(callback)
    if len(parts) != 3:
        await callback.answer("Некорректная команда", show_alert=True)
        return
    action = parts[1]
    try:
        index = int(parts[2])
    except ValueError:
        await callback.answer("Некорректный номер", show_alert=True)
        return
    try:
        voices = await get_elevenlabs_voices(user_id)
    except ElevenLabsAPIError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    if not voices:
        await callback.answer("Голоса не найдены", show_alert=True)
        return
    index = nav_index(index, len(voices))
    voice = voices[index]
    if action == "set":
        set_active_elevenlabs_voice(user_id, voice)
        await callback.answer("Голос активирован")
        await show_elevenlabs_voice(
            callback.message.chat.id,
            user_id,
            thread_id=message_thread_id(callback.message),
            index=index,
            message=callback.message,
            edit=True,
        )
        return
    if action == "show":
        await callback.answer()
        await show_elevenlabs_voice(
            callback.message.chat.id,
            user_id,
            thread_id=message_thread_id(callback.message),
            index=index,
            message=callback.message,
            edit=True,
        )
        return
    await callback.answer("Некорректное действие", show_alert=True)


@dp.callback_query(F.data.startswith("overlay:"))
async def overlay_callback(callback: CallbackQuery) -> None:
    parts = (callback.data or "").split(":")
    user_id = activate_from_callback(callback)
    if len(parts) != 3 or parts[2] not in {"short", "youtube", "shorts", "reels"}:
        await callback.answer("Некорректная команда", show_alert=True)
        return
    action = parts[1]
    format = parts[2]
    label = format_label(format)
    if action == "upload":
        PENDING_OVERLAY_UPLOADS[user_id] = format
        PENDING_SETTING_EDITS.pop(user_id, None)
        await callback.answer("Отправь картинку")
        await edit_or_send_text(
            callback.message.chat.id,
            f"Отправь плашку для {label} одним сообщением: PNG/JPG/WebP файлом или фото.\n\n"
            "Лучше использовать PNG с прозрачностью и размером под формат видео.",
            thread_id=message_thread_id(callback.message),
            message=callback.message,
            edit=True,
        )
        return
    if action == "percent":
        PENDING_SETTING_EDITS[user_id] = f"overlay_percent:{format}"
        PENDING_OVERLAY_UPLOADS.pop(user_id, None)
        await callback.answer("Отправь процент")
        await edit_or_send_text(
            callback.message.chat.id,
            f"Отправь процент появления плашки {label}: число от 0 до 100.\n\n"
            "Например, 70 означает, что плашка появится с 70% хронометража и останется до конца.",
            thread_id=message_thread_id(callback.message),
            message=callback.message,
            edit=True,
        )
        return
    if action == "show":
        await callback.answer()
        overlay_path = get_overlay_path(user_id, format)
        summary = overlay_summary(user_id, format)
        if overlay_path and overlay_path.exists():
            try:
                await callback.message.edit_media(
                    media=InputMediaPhoto(media=FSInputFile(overlay_path), caption=summary),
                    reply_markup=overlay_keyboard(format),
                )
            except TelegramBadRequest as exc:
                if "message is not modified" not in str(exc).lower():
                    logger.warning("Failed to edit overlay preview, sending a new one: %s", exc)
                    try:
                        await callback.message.delete()
                    except TelegramBadRequest:
                        pass
                    await bot.send_photo(
                        callback.message.chat.id,
                        FSInputFile(overlay_path),
                        caption=summary,
                        message_thread_id=message_thread_id(callback.message),
                        reply_markup=overlay_keyboard(format),
                    )
            return
        await edit_or_send_text(
            callback.message.chat.id,
            summary,
            thread_id=message_thread_id(callback.message),
            message=callback.message,
            edit=True,
            reply_markup=overlay_keyboard(format),
        )
        return
    await callback.answer("Некорректное действие", show_alert=True)


@dp.callback_query(F.data.startswith("vizard:"))
async def vizard_callback(callback: CallbackQuery) -> None:
    parts = (callback.data or "").split(":")
    user_id = activate_from_callback(callback)
    if len(parts) == 2 and parts[1] == "show":
        await callback.answer()
    elif len(parts) == 3 and parts[1] == "ratio":
        storage.set_setting(user_id, "vizard_ratio_of_clip", normalize_vizard_setting_value("vizard_ratio_of_clip", parts[2]))
        await callback.answer("Формат сохранен")
    elif len(parts) == 3 and parts[1] == "length":
        storage.set_setting(user_id, "vizard_prefer_length", normalize_vizard_setting_value("vizard_prefer_length", parts[2]))
        await callback.answer("Длина сохранена")
    elif len(parts) == 3 and parts[1] == "silence":
        storage.set_setting(
            user_id,
            "vizard_remove_silence_switch",
            normalize_vizard_setting_value("vizard_remove_silence_switch", parts[2]),
        )
        await callback.answer("Удаление тишины сохранено")
    else:
        await callback.answer("Некорректная команда", show_alert=True)
        return
    await edit_or_send_text(
        callback.message.chat.id,
        format_vizard_settings(get_user_settings(storage, settings, user_id).vizard),
        thread_id=message_thread_id(callback.message),
        message=callback.message,
        edit=True,
        reply_markup=vizard_settings_keyboard(),
    )


@dp.message(Command("status"))
async def status(message: Message) -> None:
    user_id = activate_from_message(message)
    clear_pending_edit(user_id)
    await answer_in_same_thread(message, format_bank_status(user_id))


@dp.message(Command("bank"))
async def bank(message: Message) -> None:
    user_id = activate_from_message(message)
    clear_pending_edit(user_id)
    await answer_in_same_thread(message, format_bank_status(user_id))


@dp.message(Command("review"))
async def review(message: Message) -> None:
    user_id = activate_from_message(message)
    clear_pending_edit(user_id)
    await start_review_session(message.chat.id, user_id, thread_id=message_thread_id(message))


@dp.message(Command("refill"))
async def refill(message: Message) -> None:
    user_id = activate_from_message(message)
    clear_pending_edit(user_id)
    await refill_if_needed(
        message.chat.id,
        user_id,
        thread_id=message_thread_id(message),
        topic_hint=command_tail(message.text),
    )


@dp.message(Command("daily_scripts"))
async def daily_scripts(message: Message) -> None:
    user_id = activate_from_message(message)
    clear_pending_edit(user_id)
    topic_hint = command_tail(message.text)
    await refill_if_needed(message.chat.id, user_id, thread_id=message_thread_id(message), force=True, topic_hint=topic_hint)


@dp.message(Command("youtube_script"))
async def youtube_script(message: Message) -> None:
    user_id = activate_from_message(message)
    clear_pending_edit(user_id)
    topic_hint = command_tail(message.text)
    status_msg = await answer_in_same_thread(message, "⏳ Запрашиваю у NotebookLM YouTube-сценарий до 15 минут...")
    try:
        records = await generate_scripts_for_user(user_id, 1, format="youtube", topic_hint=topic_hint)
    except Exception as exc:
        logger.exception("Failed to generate YouTube script")
        await status_msg.edit_text(f"❌ Не удалось сгенерировать YouTube-сценарий: {exc}")
        return

    await send_scripts(
        message.chat.id,
        records,
        thread_id=message_thread_id(message),
        message=status_msg,
        edit=True,
    )


@dp.message(Command("vizard"))
async def vizard_clip_command(message: Message) -> None:
    user_id = activate_from_message(message)
    clear_pending_edit(user_id)
    asyncio.create_task(
        run_vizard_youtube_job(
            bot=bot,
            storage=storage,
            settings=settings,
            user_id=user_id,
            chat_id=message.chat.id,
            thread_id=message_thread_id(message),
            text=message.text or "",
        )
    )


@dp.message(Command("formats"))
async def turan_formats(message: Message) -> None:
    user_id = activate_from_message(message)
    clear_pending_edit(user_id)
    tail = command_tail(message.text)

    if tail:
        try:
            script_id = int(tail)
        except ValueError:
            await answer_in_same_thread(message, "Отправь так: /formats или /formats <script_id>")
            return
        record = storage.get_script(user_id, script_id)
    else:
        records = storage.list_scripts(user_id, format="short", status="approved", limit=100)
        record = records[-1] if records else None

    if not record:
        await answer_in_same_thread(message, "Нет одобренного short-сценария. Сначала прими сценарий через /review.")
        return
    if record.status != "approved":
        await answer_in_same_thread(message, "Turan-форматы можно собрать только из одобренного сценария.")
        return

    await answer_in_same_thread(
        message,
        f"Выбери Turan-формат для сценария #{record.id}:\n\n{record.hook}",
        reply_markup=turan_formats_keyboard(record.id),
        disable_web_page_preview=True,
    )


@dp.message(F.text, lambda message: not (message.text or "").startswith("/") and bool(extract_youtube_url(message.text)))
async def youtube_link_for_vizard(message: Message) -> None:
    user_id = activate_from_message(message)
    clear_pending_edit(user_id)
    asyncio.create_task(
        run_vizard_youtube_job(
            bot=bot,
            storage=storage,
            settings=settings,
            user_id=user_id,
            chat_id=message.chat.id,
            thread_id=message_thread_id(message),
            text=message.text or "",
        )
    )


@dp.message(F.text, lambda message: bool(extract_heygen_video_id(message.text)))
async def existing_heygen_video_message(message: Message) -> None:
    user_id = activate_from_message(message)
    clear_pending_edit(user_id)
    video_id = extract_heygen_video_id(message.text)
    if not video_id:
        return
    records = storage.list_approved_scripts(user_id, limit=1)
    record = records[0] if records else None
    if not record:
        await answer_in_same_thread(message, "Нет одобренного short-сценария. Сначала прими сценарий через /review.")
        return
    try:
        await render_existing_heygen_video(
            message.chat.id,
            message_thread_id(message),
            user_id,
            record,
            video_id,
        )
    except (HeyGenError, VideoOverlayError) as exc:
        logger.exception("Failed to render existing HeyGen video")
        await answer_in_same_thread(message, f"⚠️ Не удалось собрать montage из HeyGen video id {video_id}: {exc}")


@dp.callback_query(F.data.startswith("turan:format:"))
async def turan_format_callback(callback: CallbackQuery) -> None:
    parts = (callback.data or "").split(":")
    if len(parts) != 4:
        await callback.answer("Некорректная команда", show_alert=True)
        return
    _, _, format_key, script_id_raw = parts
    try:
        script_id = int(script_id_raw)
    except ValueError:
        await callback.answer("Некорректный ID", show_alert=True)
        return
    if not callback.message:
        await callback.answer("Нет сообщения для ответа", show_alert=True)
        return

    user_id = activate_from_callback(callback)
    await callback.answer("Собираю формат")
    await send_turan_package(
        callback.message.chat.id,
        message_thread_id(callback.message),
        user_id,
        script_id,
        format_key,
    )


@dp.callback_query(F.data.startswith("script:"))
async def script_review(callback: CallbackQuery) -> None:
    parts = (callback.data or "").split(":")
    if len(parts) != 3:
        await callback.answer("Некорректная команда", show_alert=True)
        return

    _, action, script_id_raw = parts
    try:
        script_id = int(script_id_raw)
    except ValueError:
        await callback.answer("Некорректный ID", show_alert=True)
        return

    user_id = activate_from_callback(callback)
    record = storage.get_script(user_id, script_id)
    if not record:
        await callback.answer("Сценарий не найден", show_alert=True)
        return

    if action == "approve":
        updated = storage.update_script_status(user_id, script_id, "approved")
        await callback.answer("Принято")
        if updated and updated.format == "short":
            advance_review_progress(user_id)
            await edit_to_next_review_card(callback, user_id)
            return
        await callback.message.edit_reply_markup(reply_markup=None)
        return

    if action == "reject":
        updated = storage.update_script_status(user_id, script_id, "rejected")
        await callback.answer("Отклонено")
        if updated and updated.format == "short":
            advance_review_progress(user_id)
            await edit_to_next_review_card(callback, user_id)
            return
        await callback.message.edit_reply_markup(reply_markup=None)
        return

    await callback.answer("Некорректное действие", show_alert=True)


def command_tail(text: str | None) -> str | None:
    parts = (text or "").split(maxsplit=1)
    if len(parts) < 2:
        return None
    return parts[1].strip() or None


async def main() -> None:
    cleaned = cleanup_old_videos(settings.video_output_directory, keep_days=settings.video_keep_days)
    if cleaned:
        logger.info("Cleaned %s old video files from %s on startup", cleaned, settings.video_output_directory)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

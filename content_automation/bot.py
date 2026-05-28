from __future__ import annotations

import asyncio
import difflib
import logging
import re
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message

from .config import load_settings
from .elevenlabs_mcp import ElevenLabsMCPClient, ElevenLabsMCPError
from .notebooklm import as_script_list, extract_json
from .notebooklm_mcp import NotebookLMMCPClient, notebook_ref_to_url
from .prompts import DEFAULT_CTA_MIX, DEFAULT_OFFER_CONTEXT, build_short_scripts_prompt, build_youtube_script_prompt
from .storage import ScriptRecord, Storage


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = load_settings()
storage = Storage(settings.data_dir / "content_automation.sqlite3")
notebooklm = NotebookLMMCPClient(command=settings.notebooklm_mcp_command)
elevenlabs = ElevenLabsMCPClient(
    api_key=settings.elevenlabs_api_key,
    command=settings.elevenlabs_mcp_command,
    output_directory=settings.elevenlabs_output_directory,
)
bot = Bot(settings.telegram_bot_token)
dp = Dispatcher()

APPROVED_BANK_TARGET = 5
REFILL_BATCH_SIZE = 10
PENDING_SETTING_EDITS: dict[str, str] = {}
CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")
WORD_RE = re.compile(r"[a-z0-9]+")


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
        text,
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
        text,
        message_thread_id=thread_id,
        reply_markup=reply_markup,
        disable_web_page_preview=disable_web_page_preview,
    )


def script_keyboard(script_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Принять", callback_data=f"script:approve:{script_id}")],
            [InlineKeyboardButton(text="🚫 Отклонить", callback_data=f"script:reject:{script_id}")],
        ]
    )


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


def normalize_for_similarity(text: str | None) -> str:
    return " ".join(WORD_RE.findall((text or "").lower()))


def similarity(left: str | None, right: str | None) -> float:
    left_norm = normalize_for_similarity(left)
    right_norm = normalize_for_similarity(right)
    if not left_norm or not right_norm:
        return 0.0
    return difflib.SequenceMatcher(None, left_norm, right_norm).ratio()


def payload_text(payload: dict[str, object], field: str) -> str:
    return str(payload.get(field) or "").strip()


def payload_is_similar_to_record(payload: dict[str, object], record: ScriptRecord) -> bool:
    return (
        similarity(payload_text(payload, "title"), record.title) >= 0.86
        or similarity(payload_text(payload, "hook"), record.hook) >= 0.78
        or similarity(payload_text(payload, "voiceover"), record.voiceover) >= 0.72
    )


def payload_is_similar_to_payload(payload: dict[str, object], other: dict[str, object]) -> bool:
    return (
        similarity(payload_text(payload, "title"), payload_text(other, "title")) >= 0.86
        or similarity(payload_text(payload, "hook"), payload_text(other, "hook")) >= 0.78
        or similarity(payload_text(payload, "voiceover"), payload_text(other, "voiceover")) >= 0.72
    )


def script_payload_is_duplicate(
    payload: dict[str, object],
    existing_records: list[ScriptRecord],
    accepted_payloads: list[dict[str, object]],
) -> bool:
    return any(payload_is_similar_to_record(payload, record) for record in existing_records) or any(
        payload_is_similar_to_payload(payload, other) for other in accepted_payloads
    )


def build_exclusion_context(records: list[ScriptRecord], *, limit: int = 30) -> str:
    lines: list[str] = []
    for record in records[:limit]:
        title = record.title.strip()
        hook = record.hook.strip()
        if title or hook:
            lines.append(f"- Title: {title}; Hook: {hook}")
    return "\n".join(lines)


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


def get_notebook_ref(user_id: str) -> str | None:
    return storage.get_setting(user_id, "notebook_id") or settings.default_notebook_id


def get_author_style(user_id: str) -> str | None:
    return storage.get_setting(user_id, "author_style")


def clear_pending_edit(user_id: str) -> None:
    PENDING_SETTING_EDITS.pop(user_id, None)


def get_offer_context(user_id: str) -> str:
    return storage.get_setting(user_id, "offer_context") or DEFAULT_OFFER_CONTEXT.strip()


def get_cta_mix(user_id: str) -> str:
    return storage.get_setting(user_id, "cta_mix") or DEFAULT_CTA_MIX


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
    existing_records = storage.list_recent_scripts(user_id, format=format, limit=60)
    exclusion_context = build_exclusion_context(existing_records) if format == "short" else ""
    if format == "youtube":
        prompt = build_youtube_script_prompt(
            style,
            offer_context=offer_context,
            cta_mix=cta_mix,
            topic_hint=topic_hint,
        )
    else:
        prompt = build_short_scripts_prompt(
            count=count,
            author_style=style,
            offer_context=offer_context,
            cta_mix=cta_mix,
            topic_hint=topic_hint,
            exclusion_context=exclusion_context,
        )

    items: list[dict[str, object]] = []
    for attempt in range(3):
        request_prompt = prompt
        if attempt:
            request_prompt = "\n\n".join(
                [
                    prompt,
                    "CRITICAL CORRECTION: the previous response contained Russian/Cyrillic, repeated an old idea, or repeated another script in the same batch. Regenerate with fresh English-only scripts. No Cyrillic characters anywhere in JSON values. Do not reuse the excluded titles, hooks, metaphors, or problem frames.",
                ]
            )
        result = await asyncio.to_thread(notebooklm.ask, request_prompt, notebook_url=notebook_ref_to_url(notebook_ref))
        payload = extract_json(result.answer)
        for item in as_script_list(payload):
            if script_payload_has_cyrillic(item):
                continue
            if format == "short" and script_payload_is_duplicate(item, existing_records, items):
                continue
            items.append(item)
        if len(items) >= count:
            break
    items = items[:count]
    if not items:
        raise ValueError("NotebookLM не вернул новые английские сценарии в JSON. Попробуй /refill еще раз.")

    return [storage.add_script(user_id, format, item) for item in items]


async def send_scripts(chat_id: int, records: list[ScriptRecord], *, thread_id: int | None = None) -> None:
    for record in records:
        chunks = split_telegram_text(format_script_message(record))
        for index, chunk in enumerate(chunks):
            is_last = index == len(chunks) - 1
            await send_to_chat_thread(
                chat_id,
                chunk,
                thread_id=thread_id,
                reply_markup=script_keyboard(record.id) if is_last else None,
                disable_web_page_preview=True,
            )


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


async def generate_voiceover_audio(record: ScriptRecord) -> str:
    result = await asyncio.to_thread(
        elevenlabs.text_to_speech,
        text=record.voiceover,
        voice_name=settings.elevenlabs_voice_name,
        model_id=settings.elevenlabs_model_id,
        speed=settings.elevenlabs_speed,
        stability=settings.elevenlabs_stability,
        similarity_boost=settings.elevenlabs_similarity_boost,
        style=settings.elevenlabs_style,
        language=settings.elevenlabs_language,
    )
    return result.file_path or result.message


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


def settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Контекст оффера", callback_data="settings:edit:offer_context")],
            [InlineKeyboardButton(text="🗣 Голос автора", callback_data="settings:edit:author_style")],
            [InlineKeyboardButton(text="🧲 Микс CTA", callback_data="settings:edit:cta_mix")],
            [InlineKeyboardButton(text="📚 База NotebookLM", callback_data="settings:edit:notebook_id")],
            [InlineKeyboardButton(text="👀 Показать текущие", callback_data="settings:show")],
        ]
    )


def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Пополнить банк", callback_data="main:refill")],
            [InlineKeyboardButton(text="🧾 Проверить очередь", callback_data="main:review")],
            [InlineKeyboardButton(text="🏦 Статус банка", callback_data="main:bank")],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="main:settings")],
        ]
    )


def format_current_settings(user_id: str) -> str:
    notebook = get_notebook_ref(user_id) or "не задано"
    author_style = get_author_style(user_id) or "по умолчанию"
    offer_context = get_offer_context(user_id)
    cta_mix = get_cta_mix(user_id)
    return "\n\n".join(
        [
            "Текущие настройки контента:",
            f"База NotebookLM:\n{notebook}",
            f"Микс CTA:\n{cta_mix}",
            f"Голос автора:\n{author_style}",
            f"Контекст оффера:\n{offer_context}",
        ]
    )


async def start_review_session(chat_id: int, user_id: str, *, thread_id: int | None = None) -> int:
    removed = reject_cyrillic_pending_scripts(user_id)
    pending = storage.count_scripts(user_id, format="short", status="pending")
    if pending == 0:
        if removed:
            await send_to_chat_thread(chat_id, f"Убрал русские сценарии из очереди: {removed}. Запусти /refill для новой английской пачки.", thread_id=thread_id)
            return 0
        await send_to_chat_thread(chat_id, "Нет сценариев на ревью. Запусти /refill, чтобы создать новую пачку.", thread_id=thread_id)
        return 0
    set_review_session(user_id, pending)
    record = storage.list_scripts(user_id, format="short", status="pending", limit=1)[0]
    await send_to_chat_thread(
        chat_id,
        format_review_message(record, user_id),
        thread_id=thread_id,
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
    force: bool = False,
    topic_hint: str | None = None,
) -> None:
    approved = storage.count_scripts(user_id, format="short", status="approved")
    pending = storage.count_scripts(user_id, format="short", status="pending")
    if not force and pending > 0:
        await send_to_chat_thread(
            chat_id,
            f"Уже есть сценарии на проверке: {pending}. Открываю очередь.",
            thread_id=thread_id,
        )
        await start_review_session(chat_id, user_id, thread_id=thread_id)
        return
    if not force and approved > APPROVED_BANK_TARGET:
        await send_to_chat_thread(
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
        )
        return

    status_msg = await send_to_chat_thread(
        chat_id,
        f"⏳ Банк одобренных: {approved}/{APPROVED_BANK_TARGET}. Генерирую пачку из {REFILL_BATCH_SIZE} сценариев...",
        thread_id=thread_id,
    )
    try:
        await generate_scripts_for_user(user_id, REFILL_BATCH_SIZE, format="short", topic_hint=topic_hint)
    except Exception as exc:
        logger.exception("Failed to refill script bank")
        await status_msg.edit_text(f"❌ Не удалось пополнить банк сценариев: {exc}")
        return
    await status_msg.edit_text("✅ Новая пачка сценариев готова.")
    await start_review_session(chat_id, user_id, thread_id=thread_id)


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
                "/set_notebook <id> - подключить NotebookLM-базу",
                "/set_style <описание стиля> - сохранить голос автора",
                "/settings - настройки оффера, CTA, стиля и NotebookLM",
                "/bank - статус банка сценариев",
                "/refill - пополнить банк, если одобрено 5 или меньше",
                "/review - открыть очередь сценариев на проверку",
                "/daily_scripts - сгенерировать 10 и открыть очередь",
                "/youtube_script - сгенерировать недельный YouTube-сценарий",
                "/status - статус банка сценариев",
            ]
        ),
        reply_markup=main_keyboard(),
    )


@dp.message(Command("settings"))
async def settings_menu(message: Message) -> None:
    user_id = activate_from_message(message)
    clear_pending_edit(user_id)
    await answer_in_same_thread(
        message,
        "Что настраиваем? Эти данные попадут в запрос к NotebookLM, чтобы CTA писался органично под оффер, а не вставлялся шаблоном.",
        reply_markup=settings_keyboard(),
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


@dp.message(F.text, lambda message: str(message.from_user.id) in PENDING_SETTING_EDITS and not (message.text or "").startswith("/"))
async def handle_pending_setting_edit(message: Message) -> None:
    user_id = activate_from_message(message)
    key = PENDING_SETTING_EDITS.pop(user_id)
    value = (message.text or "").strip()
    if not value:
        await answer_in_same_thread(message, "Пустое значение не сохранил. Нажми кнопку настройки еще раз.")
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
        await send_to_chat_thread(
            callback.message.chat.id,
            "Что настраиваем? Эти данные попадут в запрос к NotebookLM, чтобы CTA писался органично под оффер.",
            thread_id=message_thread_id(callback.message),
            reply_markup=settings_keyboard(),
        )
        return
    if action == "bank":
        await send_to_chat_thread(
            callback.message.chat.id,
            format_bank_status(user_id),
            thread_id=message_thread_id(callback.message),
            reply_markup=main_keyboard(),
        )
        return
    if action == "review":
        await start_review_session(callback.message.chat.id, user_id, thread_id=message_thread_id(callback.message))
        return
    if action == "refill":
        await refill_if_needed(callback.message.chat.id, user_id, thread_id=message_thread_id(callback.message))
        return


@dp.callback_query(F.data.startswith("settings:"))
async def settings_callback(callback: CallbackQuery) -> None:
    parts = (callback.data or "").split(":")
    user_id = activate_from_callback(callback)
    if len(parts) >= 2 and parts[1] == "show":
        await callback.answer()
        await send_to_chat_thread(
            callback.message.chat.id,
            format_current_settings(user_id),
            thread_id=message_thread_id(callback.message),
            reply_markup=settings_keyboard(),
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
    await send_to_chat_thread(callback.message.chat.id, prompts[key], thread_id=message_thread_id(callback.message))


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

    await status_msg.edit_text("✅ YouTube-сценарий готов. Отправляю на апрув.")
    await send_scripts(message.chat.id, records, thread_id=message_thread_id(message))


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
            try:
                audio_path = await generate_voiceover_audio(updated)
                await send_generated_audio(callback.message.chat.id, message_thread_id(callback.message), audio_path)
            except ElevenLabsMCPError as exc:
                await send_to_chat_thread(
                    callback.message.chat.id,
                    f"✅ Сценарий принят.\n⚠️ Озвучку пока не создал: {exc}",
                    thread_id=message_thread_id(callback.message),
                )
            except Exception as exc:
                logger.exception("Failed to generate ElevenLabs voiceover")
                await send_to_chat_thread(
                    callback.message.chat.id,
                    f"✅ Сценарий принят.\n⚠️ Не удалось создать озвучку: {exc}",
                    thread_id=message_thread_id(callback.message),
                )
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
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .content_language import normalize_content_language, prompt_language_name, viewer_text_language_instruction
from .idea_bank import ContentIdea, IdeaBank
from .notebooklm import extract_json
from .notebooklm_mcp import notebook_ref_to_url
from .notebooklm_runtime import NotebookLMAskClient
from .prompts import DEFAULT_OFFER_CONTEXT, _short_prompt_value
from .viral_prompt_rules import viral_angle_prompt

logger = logging.getLogger(__name__)

MAX_PRODUCER_PLAN_BATCH_SIZE = 1
MAX_PRODUCER_PLAN_ATTEMPT_MULTIPLIER = 3
MAX_EMPTY_PRODUCER_PLAN_ATTEMPTS = 5


async def generate_notebooklm_content_plan(
    *,
    user_id: str,
    notebook_ref: str,
    notebooklm: NotebookLMAskClient,
    idea_bank: IdeaBank,
    count: int = 30,
    content_language: str = "auto",
    offer_context: str | None = None,
    existing_ideas: list[ContentIdea] | None = None,
    extension: bool = False,
) -> list[ContentIdea]:
    if count > MAX_PRODUCER_PLAN_BATCH_SIZE:
        return await generate_notebooklm_content_plan_batches(
            user_id=user_id,
            notebook_ref=notebook_ref,
            notebooklm=notebooklm,
            idea_bank=idea_bank,
            count=count,
            content_language=content_language,
            offer_context=offer_context,
            existing_ideas=existing_ideas,
            extension=extension,
        )
    prompt = build_producer_plan_prompt(
        count=count,
        content_language=content_language,
        offer_context=offer_context,
        existing_ideas=existing_ideas,
        extension=extension,
    )
    logger.info("Generating NotebookLM producer plan: count=%s user=%s", count, user_id)
    result = await asyncio.to_thread(notebooklm.ask, prompt, notebook_url=notebook_ref_to_url(notebook_ref))
    answer = str(getattr(result, "answer", result) or "")
    payload = extract_json(answer)
    ideas = normalize_producer_plan(payload, notebook_ref=notebook_ref)
    inserted = idea_bank.add_many(user_id, ideas[:count])
    logger.info("NotebookLM producer plan generated=%s inserted=%s user=%s", len(ideas), len(inserted), user_id)
    return inserted


async def generate_notebooklm_content_plan_batches(
    *,
    user_id: str,
    notebook_ref: str,
    notebooklm: NotebookLMAskClient,
    idea_bank: IdeaBank,
    count: int,
    content_language: str,
    offer_context: str | None,
    existing_ideas: list[ContentIdea] | None,
    extension: bool,
) -> list[ContentIdea]:
    inserted: list[ContentIdea] = []
    context = list(existing_ideas or [])
    remaining = count
    batch_index = 0
    empty_attempts = 0
    max_attempts = max(count * MAX_PRODUCER_PLAN_ATTEMPT_MULTIPLIER, count + MAX_EMPTY_PRODUCER_PLAN_ATTEMPTS)
    while remaining > 0 and batch_index < max_attempts:
        batch_index += 1
        batch_count = min(MAX_PRODUCER_PLAN_BATCH_SIZE, remaining)
        logger.info(
            "Generating NotebookLM producer plan batch %s/%s: batch_count=%s remaining=%s user=%s",
            batch_index,
            max_attempts,
            batch_count,
            remaining,
            user_id,
        )
        batch = await generate_notebooklm_content_plan(
            user_id=user_id,
            notebook_ref=notebook_ref,
            notebooklm=notebooklm,
            idea_bank=idea_bank,
            count=batch_count,
            content_language=content_language,
            offer_context=offer_context,
            existing_ideas=context,
            extension=extension or batch_index > 1,
        )
        if not batch:
            empty_attempts += 1
            logger.info(
                "NotebookLM producer plan batch %s inserted no new ideas; retrying (%s/%s empty attempts)",
                batch_index,
                empty_attempts,
                MAX_EMPTY_PRODUCER_PLAN_ATTEMPTS,
            )
            if empty_attempts >= MAX_EMPTY_PRODUCER_PLAN_ATTEMPTS:
                logger.info(
                    "NotebookLM producer plan stopped after %s empty attempts; inserted=%s requested=%s user=%s",
                    empty_attempts,
                    len(inserted),
                    count,
                    user_id,
                )
                break
            continue
        empty_attempts = 0
        inserted.extend(batch)
        context.extend(batch)
        remaining = count - len(inserted)
    return inserted[:count]


def build_producer_plan_prompt(
    *,
    count: int,
    content_language: str,
    offer_context: str | None = None,
    existing_ideas: list[ContentIdea] | None = None,
    extension: bool = False,
) -> str:
    language = normalize_content_language(content_language)
    language_name = prompt_language_name(language)
    language_rule = viewer_text_language_instruction(language)
    offer = _short_prompt_value(offer_context or DEFAULT_OFFER_CONTEXT, 360)
    mode_instruction = (
        "Extend the current monthly plan with additional episodes. Do not restart the plan."
        if extension
        else "Build the first monthly plan from scratch."
    )
    existing_section = format_existing_plan_context(existing_ideas or [])
    viral_rules = viral_angle_prompt()
    return f"""
Return ONLY valid JSON, no markdown.
Act as a senior social media producer. Use NotebookLM sources as truth.
Create {count} fresh content episode(s) in {language_name}. {mode_instruction}

Language rule: {language_rule}
Offer: {offer}
Avoid repeating these saved topics:
{existing_section}

Return an array of objects with exactly these keys:
day, pillar, format, title, pain, angle, viral_angle, hook_pattern, mechanism, first_frame_text, summary, visual_note, visual_proof, source_basis.

Rules:
- title: 3-8 words, thesis-style
- format: vertical_short, infographic, or youtube_segment
- angle and visual_note must be specific enough for a video editor
- choose a source-backed hidden mistake, money leak, diagnostic, framework, or proof story
{viral_rules}
""".strip()


def format_existing_plan_context(ideas: list[ContentIdea], *, limit: int = 12) -> str:
    if not ideas:
        return "- No saved topics yet."
    lines = []
    recent_ideas = ideas[-limit:]
    for index, idea in enumerate(recent_ideas, start=1):
        meta = idea.source_meta or {}
        pillar = _text(meta.get("pillar"))
        day = _text(meta.get("day"))
        label = f"day {day}, {pillar}" if day or pillar else idea.source
        lines.append(f"- {index}. [{label}] {idea.title} | {idea.angle}")
    return "\n".join(lines)


def normalize_producer_plan(payload: Any, *, notebook_ref: str) -> list[dict[str, Any]]:
    raw_items = _plan_items(payload)
    ideas: list[dict[str, Any]] = []
    for index, item in enumerate(raw_items, start=1):
        if not isinstance(item, dict):
            continue
        title = _text(item.get("title"))
        angle = _text(item.get("angle"))
        if not title or not angle:
            continue
        day = _positive_int(item.get("day"), index)
        ideas.append(
            {
                "source": "notebooklm_plan",
                "source_url": f"notebooklm://{notebook_ref}/plan-day-{day}-{_slug(title)}",
                "title": title,
                "pain": _text(item.get("pain")),
                "angle": angle,
                "summary": _text(item.get("summary") or item.get("visual_note") or item.get("source_basis")),
                "source_meta": {
                    "notebook_ref": notebook_ref,
                    "day": day,
                    "pillar": _text(item.get("pillar")),
                    "format": _text(item.get("format")),
                    "viral_angle": _text(item.get("viral_angle")),
                    "hook_pattern": _text(item.get("hook_pattern")),
                    "mechanism": _text(item.get("mechanism")),
                    "first_frame_text": _text(item.get("first_frame_text")),
                    "visual_note": _text(item.get("visual_note")),
                    "visual_proof": _text(item.get("visual_proof")),
                    "source_basis": _text(item.get("source_basis")),
                },
            }
        )
    return ideas


def _plan_items(payload: Any) -> list[Any]:
    if isinstance(payload, dict):
        for key in ("plan", "content_plan", "episodes", "ideas", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    if isinstance(payload, list):
        return payload
    raise ValueError("NotebookLM producer plan JSON must be a list or contain plan/items")


def _positive_int(value: Any, fallback: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return fallback
    return number if number > 0 else fallback


def _text(value: Any) -> str:
    return str(value or "").strip()


def _slug(value: str) -> str:
    return "-".join("".join(char.lower() if char.isalnum() else " " for char in value).split())[:80] or "topic"

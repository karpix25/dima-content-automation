from __future__ import annotations

import asyncio
import logging
import random
import re
from typing import Any

from .content_language import normalize_content_language, prompt_language_name, viewer_text_language_instruction
from .idea_bank import ContentIdea, IdeaBank
from .kie_text import KieTextClient, KieTextError
from .notebooklm import extract_json
from .notebooklm_mcp import notebook_ref_to_url
from .notebooklm_runtime import NotebookLMAskClient
from .prompts import DEFAULT_OFFER_CONTEXT, _short_prompt_value
from .viral_prompt_rules import viral_angle_prompt

logger = logging.getLogger(__name__)

MAX_PRODUCER_PLAN_BATCH_SIZE = 6
MIN_PRODUCER_PLAN_BATCH_SIZE = 4
MAX_PRODUCER_PLAN_ATTEMPT_MULTIPLIER = 2
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
    kie_text_client: KieTextClient | None = None,
) -> list[ContentIdea]:
    if count > 1:
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
            kie_text_client=kie_text_client,
        )
    return await generate_notebooklm_content_plan_once(
        user_id=user_id,
        notebook_ref=notebook_ref,
        notebooklm=notebooklm,
        idea_bank=idea_bank,
        count=count,
        content_language=content_language,
        offer_context=offer_context,
        existing_ideas=existing_ideas,
        extension=extension,
        kie_text_client=kie_text_client,
    )


async def generate_notebooklm_content_plan_once(
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
    kie_text_client: KieTextClient | None = None,
) -> list[ContentIdea]:
    focus = producer_plan_focus(extension=extension)
    prompt = build_producer_plan_prompt(
        count=count,
        content_language=content_language,
        offer_context=offer_context,
        existing_ideas=existing_ideas,
        extension=extension,
        focus=focus,
    )
    logger.info("Generating NotebookLM producer plan: count=%s user=%s", count, user_id)
    result = await asyncio.to_thread(notebooklm.ask, prompt, notebook_url=notebook_ref_to_url(notebook_ref))
    answer = str(getattr(result, "answer", result) or "")
    payload = structure_producer_plan_answer(
        answer=answer,
        count=count,
        content_language=content_language,
        offer_context=offer_context,
        kie_text_client=kie_text_client,
    )
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
    kie_text_client: KieTextClient | None = None,
) -> list[ContentIdea]:
    inserted: list[ContentIdea] = []
    context = list(existing_ideas or [])
    remaining = count
    batch_index = 0
    empty_attempts = 0
    max_attempts = max(count * MAX_PRODUCER_PLAN_ATTEMPT_MULTIPLIER, count + MAX_EMPTY_PRODUCER_PLAN_ATTEMPTS)
    while remaining > 0 and batch_index < max_attempts:
        batch_index += 1
        batch_count = min(random.randint(MIN_PRODUCER_PLAN_BATCH_SIZE, MAX_PRODUCER_PLAN_BATCH_SIZE), remaining)
        logger.info(
            "Generating NotebookLM producer plan batch %s/%s: batch_count=%s remaining=%s user=%s",
            batch_index,
            max_attempts,
            batch_count,
            remaining,
            user_id,
        )
        batch = await generate_notebooklm_content_plan_once(
            user_id=user_id,
            notebook_ref=notebook_ref,
            notebooklm=notebooklm,
            idea_bank=idea_bank,
            count=batch_count,
            content_language=content_language,
            offer_context=offer_context,
            existing_ideas=context,
            extension=extension or batch_index > 1,
            kie_text_client=kie_text_client,
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
    focus: str | None = None,
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
    focus_line = focus or producer_plan_focus(extension=extension)
    viral_rules = viral_angle_prompt()
    return f"""
Act as a senior social media producer reviewing the source notebook.
Give me {count} fresh content episode ideas in {language_name}. {mode_instruction}

Language rule: {language_rule}
Offer: {offer}
Today's editorial focus: {focus_line}

Avoid repeating these saved topics, but use them to understand what has already been covered:
{existing_section}

Please answer naturally as a numbered editorial list, not JSON and not a table.
For each idea include:
- title
- seller pain
- angle
- mechanism or proof from the sources
- first-frame text
- visual idea
- source basis

Keep each item concise. Choose source-backed hidden mistakes, money leaks, diagnostics, frameworks, or proof stories.
{viral_rules}
""".strip()


def producer_plan_focus(*, extension: bool = False) -> str:
    base = [
        "profit leaks and hidden margin killers",
        "operational mistakes that get Amazon sellers stuck",
        "PPC, ranking, and cash-flow traps",
        "compliance, account risk, and blocked-growth stories",
        "premium-brand positioning and ways to sell ordinary products for more",
        "inventory, logistics, FBA limits, and stockout risk",
        "counterintuitive lessons from failed Amazon growth attempts",
    ]
    if extension:
        base.extend(
            [
                "new angles that do not repeat the existing plan",
                "deeper second-layer topics behind the previous ideas",
            ]
        )
    return random.choice(base)


def structure_producer_plan_answer(
    *,
    answer: str,
    count: int,
    content_language: str,
    offer_context: str | None,
    kie_text_client: KieTextClient | None,
) -> Any:
    if kie_text_client and kie_text_client.is_configured():
        try:
            structured = kie_text_client.complete(
                system=producer_plan_structurer_system_prompt(),
                user=producer_plan_structurer_user_prompt(
                    answer=answer,
                    count=count,
                    content_language=content_language,
                    offer_context=offer_context,
                ),
            )
            return extract_json(structured)
        except (KieTextError, ValueError) as exc:
            logger.warning("KIE failed to structure NotebookLM text plan; falling back to direct parsing: %s", exc)
    try:
        return extract_json(answer)
    except ValueError:
        return {"plan": heuristic_text_plan_items(answer, count=count)}


def producer_plan_structurer_system_prompt() -> str:
    return (
        "You structure editorial research notes into clean JSON. "
        "Do not invent facts, numbers, source names, or proof. "
        "Return ONLY valid JSON. No markdown."
    )


def producer_plan_structurer_user_prompt(
    *,
    answer: str,
    count: int,
    content_language: str,
    offer_context: str | None,
) -> str:
    language = normalize_content_language(content_language)
    offer = _short_prompt_value(offer_context or DEFAULT_OFFER_CONTEXT, 360)
    return f"""
Turn this natural NotebookLM answer into up to {count} structured content ideas.

Language:
- {viewer_text_language_instruction(language)}

Offer/context:
{offer}

NotebookLM answer:
{answer[:12000]}

Return ONLY JSON:
{{
  "plan": [
    {{
      "day": 1,
      "pillar": "",
      "format": "vertical_short",
      "title": "",
      "pain": "",
      "angle": "",
      "viral_angle": "",
      "hook_pattern": "",
      "mechanism": "",
      "first_frame_text": "",
      "summary": "",
      "visual_note": "",
      "visual_proof": "",
      "source_basis": ""
    }}
  ]
}}
""".strip()


def heuristic_text_plan_items(answer: str, *, count: int) -> list[dict[str, Any]]:
    chunks = split_numbered_items(answer)
    items: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunks[:count], start=1):
        title = first_nonempty_line(chunk)
        body = " ".join(line.strip("-• ").strip() for line in chunk.splitlines() if line.strip())
        if not title or len(title) > 180:
            title = f"NotebookLM idea {index}"
        items.append(
            {
                "day": index,
                "pillar": "Source insight",
                "format": "vertical_short",
                "title": clean_heading(title),
                "pain": "",
                "angle": body[:500],
                "summary": body[:900],
                "visual_note": "",
                "source_basis": body[:700],
            }
        )
    return items


def split_numbered_items(answer: str) -> list[str]:
    text = (answer or "").strip()
    if not text:
        return []
    parts = re.split(r"(?:^|\n)\s*(?:\d+[\).:-]|\-\s+)\s+", text)
    chunks = [part.strip() for part in parts if part.strip()]
    return chunks or [text]


def first_nonempty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip(" -*#\t")
        if stripped:
            return stripped
    return ""


def clean_heading(value: str) -> str:
    return re.sub(r"^[\"'«»\s]+|[\"'«»\s]+$", "", value).strip()[:120]


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

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

logger = logging.getLogger(__name__)


async def generate_notebooklm_content_plan(
    *,
    user_id: str,
    notebook_ref: str,
    notebooklm: NotebookLMAskClient,
    idea_bank: IdeaBank,
    count: int = 30,
    content_language: str = "auto",
    offer_context: str | None = None,
) -> list[ContentIdea]:
    prompt = build_producer_plan_prompt(
        count=count,
        content_language=content_language,
        offer_context=offer_context,
    )
    logger.info("Generating NotebookLM producer plan: count=%s user=%s", count, user_id)
    result = await asyncio.to_thread(notebooklm.ask, prompt, notebook_url=notebook_ref_to_url(notebook_ref))
    answer = str(getattr(result, "answer", result) or "")
    payload = extract_json(answer)
    ideas = normalize_producer_plan(payload, notebook_ref=notebook_ref)
    inserted = idea_bank.add_many(user_id, ideas[:count])
    logger.info("NotebookLM producer plan generated=%s inserted=%s user=%s", len(ideas), len(inserted), user_id)
    return inserted


def build_producer_plan_prompt(
    *,
    count: int,
    content_language: str,
    offer_context: str | None = None,
) -> str:
    language = normalize_content_language(content_language)
    language_name = prompt_language_name(language)
    language_rule = viewer_text_language_instruction(language)
    offer = _short_prompt_value(offer_context or DEFAULT_OFFER_CONTEXT, 720)
    return f"""
Return ONLY valid JSON. Use the NotebookLM sources as your source of truth.
Act as a senior social media producer for an expert creator.
Build a {count}-episode monthly content plan in {language_name}.

Producer objective:
- Turn the knowledge base into a coherent month of content, not random ideas.
- Sequence episodes so the audience moves from painful awareness to practical trust.
- Mix hidden mistakes, money leaks, contrarian takes, diagnostics, frameworks, and proof-driven stories.
- Make every episode specific enough to become a short vertical video, infographic, or YouTube segment.
- Avoid generic beginner topics and vague motivational advice.

Output language:
- {language_rule}
- Viewer-facing titles, pains, angles, summaries, and visual notes must follow that language rule.

Offer/context:
{offer}

For each episode, choose the strongest source-backed insight and return:
[
  {{
    "day": 1,
    "pillar": "Margin / Operations / PPC / Listing / Scaling / Mindset / Case Study",
    "format": "vertical_short | infographic | youtube_segment",
    "title": "short thesis headline, 3-8 words when possible",
    "pain": "specific audience pain or costly blind spot",
    "angle": "the exact producer angle for the episode",
    "summary": "what the viewer will learn and why it matters now",
    "visual_note": "what the montage or generated visual should show",
    "source_basis": "which NotebookLM material, note, transcript, or concept supports this"
  }}
]
""".strip()


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
                    "visual_note": _text(item.get("visual_note")),
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

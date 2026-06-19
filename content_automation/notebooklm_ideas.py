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


async def generate_notebooklm_ideas(
    *,
    user_id: str,
    notebook_ref: str,
    notebooklm: NotebookLMAskClient,
    idea_bank: IdeaBank,
    count: int = 8,
    content_language: str = "auto",
    offer_context: str | None = None,
) -> list[ContentIdea]:
    prompt = build_notebooklm_ideas_prompt(
        count=count,
        content_language=content_language,
        offer_context=offer_context,
    )
    logger.info("Generating %s NotebookLM idea(s) for user %s", count, user_id)
    result = await asyncio.to_thread(notebooklm.ask, prompt, notebook_url=notebook_ref_to_url(notebook_ref))
    answer = str(getattr(result, "answer", result) or "")
    payload = extract_json(answer)
    ideas = normalize_notebooklm_ideas(payload, notebook_ref=notebook_ref)
    inserted = idea_bank.add_many(user_id, ideas[:count])
    logger.info("NotebookLM ideas generated=%s inserted=%s user=%s", len(ideas), len(inserted), user_id)
    return inserted


def build_notebooklm_ideas_prompt(
    *,
    count: int,
    content_language: str,
    offer_context: str | None = None,
) -> str:
    language = normalize_content_language(content_language)
    language_name = prompt_language_name(language)
    language_rule = viewer_text_language_instruction(language)
    offer = _short_prompt_value(offer_context or DEFAULT_OFFER_CONTEXT, 520)
    viral_rules = viral_angle_prompt()
    return f"""
Return ONLY valid JSON. Use the NotebookLM sources.
Find {count} strong {language_name} content topic ideas for an expert creator in this niche.

Output language:
- {language_rule}
- Titles, pains, angles, and summaries must follow that language rule.

Offer/context:
{offer}

Pick ideas that are specific enough to become short vertical videos or YouTube scripts.
Avoid broad beginner topics. Prefer hidden mistakes, money leaks, operational bottlenecks, contrarian warnings, and specific Amazon/ecommerce mechanisms.
{viral_rules}

[
  {{
    "title": "",
    "pain": "",
    "angle": "",
    "viral_angle": "",
    "hook_pattern": "",
    "mechanism": "",
    "first_frame_text": "",
    "visual_proof": "",
    "summary": "",
    "source_basis": "which NotebookLM materials or knowledge-base idea this came from"
  }}
]
""".strip()


def normalize_notebooklm_ideas(payload: Any, *, notebook_ref: str) -> list[dict[str, Any]]:
    raw_items = payload.get("ideas") or payload.get("items") if isinstance(payload, dict) else payload
    if not isinstance(raw_items, list):
        raise ValueError("NotebookLM topics JSON must be a list or contain ideas/items")
    ideas: list[dict[str, Any]] = []
    for index, item in enumerate(raw_items, start=1):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        pain = str(item.get("pain") or "").strip()
        angle = str(item.get("angle") or "").strip()
        summary = str(item.get("summary") or item.get("source_basis") or "").strip()
        if not title or not angle:
            continue
        source_basis = str(item.get("source_basis") or "").strip()
        ideas.append(
            {
                "source": "notebooklm",
                "source_url": f"notebooklm://{notebook_ref}/idea-{index}-{_slug(title)}",
                "title": title,
                "pain": pain,
                "angle": angle,
                "summary": summary,
                "source_meta": {
                    "notebook_ref": notebook_ref,
                    "source_basis": source_basis,
                    "viral_angle": _text(item.get("viral_angle")),
                    "hook_pattern": _text(item.get("hook_pattern")),
                    "mechanism": _text(item.get("mechanism")),
                    "first_frame_text": _text(item.get("first_frame_text")),
                    "visual_proof": _text(item.get("visual_proof")),
                },
            }
        )
    return ideas


def _slug(value: str) -> str:
    return "-".join("".join(char.lower() if char.isalnum() else " " for char in value).split())[:80] or "topic"


def _text(value: Any) -> str:
    return str(value or "").strip()

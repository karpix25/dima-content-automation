from __future__ import annotations

import json
import re
from typing import Any

from .content_language import normalize_content_language, prompt_language_name, viewer_text_language_instruction
from .idea_bank import ContentIdea
from .idea_cards import idea_to_topic_hint
from .kie_text import KieTextClient, KieTextConfig
from .notebooklm import as_script_list, extract_json
from .prompts import DEFAULT_CTA_MIX, DEFAULT_OFFER_CONTEXT, DEFAULT_AUTHOR_STYLE, _short_prompt_value
from .script_length import WordBudget


def build_kie_text_client(settings: Any) -> KieTextClient:
    return KieTextClient(
        KieTextConfig(
            api_key=getattr(settings, "kie_api_key", None),
            base_url=getattr(settings, "kie_base_url", "https://api.kie.ai"),
            model=getattr(settings, "kie_text_model", "gemini-3-flash"),
            timeout_seconds=getattr(settings, "kie_text_timeout_seconds", 90),
        )
    )


def write_script_with_kie(
    *,
    client: KieTextClient,
    idea: ContentIdea,
    author_style: str,
    offer_context: str,
    cta_mix: str,
    content_language: str,
    word_budget: WordBudget,
    revision_instruction: str | None = None,
) -> dict[str, Any]:
    answer = client.complete(
        system=kie_script_system_prompt(),
        user=kie_script_user_prompt(
            idea=idea,
            author_style=author_style,
            offer_context=offer_context,
            cta_mix=cta_mix,
            content_language=content_language,
            word_budget=word_budget,
            revision_instruction=revision_instruction,
        ),
    )
    for item in as_script_list(extract_json(answer)):
        return _normalize_script_payload(item, idea)
    raise ValueError("Kie не вернул сценарий в JSON.")


def kie_script_system_prompt() -> str:
    return (
        "You are a senior social-video scriptwriter. Write from the supplied factual packet only. "
        "Do not invent claims, numbers, source names, or proof that is not present in the packet. "
        "Return ONLY valid JSON. No markdown, no commentary."
    )


def kie_script_user_prompt(
    *,
    idea: ContentIdea,
    author_style: str,
    offer_context: str,
    cta_mix: str,
    content_language: str,
    word_budget: WordBudget,
    revision_instruction: str | None = None,
) -> str:
    language = normalize_content_language(content_language)
    packet = factual_packet_from_idea(idea)
    return f"""
Write 1 short vertical-video script from this NotebookLM factual packet.

Output language:
- {viewer_text_language_instruction(language)}
- Use natural {prompt_language_name(language)} in every viewer-facing field.

Voice: {_short_prompt_value(author_style or DEFAULT_AUTHOR_STYLE, 260)}
Offer/context: {_short_prompt_value(offer_context or DEFAULT_OFFER_CONTEXT, 420)}
CTA mix: {_short_prompt_value(cta_mix or DEFAULT_CTA_MIX, 120)}
Voiceover length: {word_budget.min_words}-{word_budget.max_words} spoken words, target about {word_budget.target_words} words.

Factual packet:
{json.dumps(packet, ensure_ascii=False, indent=2)}

Rules:
- Use the packet as truth. If a detail is missing, keep it general instead of inventing.
- Make one sharp idea: pain, mechanism, proof/example, payoff.
- Hook must create tension in 1-2 seconds.
- first_frame_text: max 4 words.
- source_basis must cite the packet source_basis or topic title.
{revision_block(revision_instruction)}

Return ONLY this JSON array:
[
  {{
    "title": "",
    "content_format": "",
    "content_pillar": "",
    "proof_type": "",
    "emotion_angle": "",
    "series_name": "",
    "topic_fingerprint": "pain + mechanism + audience moment + payoff",
    "angle": "",
    "mechanism": "",
    "hook_type": "hidden mistake | contrarian warning | money leak | belief shift",
    "hook_pattern": "",
    "hook": "",
    "first_frame_text": "",
    "visual_proof": "",
    "visual_retention_plan": "",
    "trigger": "",
    "retention_beats": ["setup", "turn", "proof", "payoff"],
    "voiceover": "",
    "cta_type": "none",
    "cta": "",
    "why_it_works": "",
    "source_basis": ""
  }}
]
""".strip()


def revision_block(instruction: str | None) -> str:
    if not instruction:
        return ""
    return f"\nRevision requirement:\n- {instruction.strip()}"


def factual_packet_from_idea(idea: ContentIdea) -> dict[str, Any]:
    meta = idea.source_meta or {}
    return {
        "topic_title": idea.title,
        "pain": idea.pain,
        "angle": idea.angle,
        "summary": idea.summary,
        "source": idea.source,
        "source_url": idea.source_url,
        "source_basis": _meta_text(meta, "source_basis") or idea.summary,
        "viral_angle": _meta_text(meta, "viral_angle"),
        "hook_pattern": _meta_text(meta, "hook_pattern"),
        "mechanism": _meta_text(meta, "mechanism"),
        "first_frame_text": _meta_text(meta, "first_frame_text"),
        "visual_proof": _meta_text(meta, "visual_proof") or _meta_text(meta, "visual_note"),
        "topic_hint": idea_to_topic_hint(idea),
    }


def _normalize_script_payload(item: dict[str, Any], idea: ContentIdea) -> dict[str, Any]:
    payload = dict(item)
    meta = idea.source_meta or {}
    payload.setdefault("title", idea.title)
    payload.setdefault("angle", idea.angle)
    payload.setdefault("trigger", idea.pain or idea.summary)
    payload.setdefault("source_basis", _meta_text(meta, "source_basis") or idea.summary or idea.title)
    for key in ("hook_pattern", "mechanism", "first_frame_text", "visual_proof"):
        if not str(payload.get(key) or "").strip():
            payload[key] = _meta_text(meta, key)
    payload["writer_backend"] = "kie"
    payload["source_idea_id"] = idea.id
    payload["source_idea_url"] = idea.source_url
    return payload


def _meta_text(meta: dict[str, Any], key: str) -> str:
    return re.sub(r"\s+", " ", str(meta.get(key) or "").strip())

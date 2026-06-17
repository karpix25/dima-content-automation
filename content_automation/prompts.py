from __future__ import annotations

from .content_language import normalize_content_language, prompt_language_name, viewer_text_language_instruction
from .editorial import EditorialBrief, editorial_briefs_prompt
from .script_length import WordBudget, length_instruction, vertical_word_budget, youtube_word_budget


DEFAULT_AUTHOR_STYLE = """
Write conversationally, like an expert talking to another operator who already sells on Amazon.
No corporate phrasing, no beginner explanations, no motivational fluff.
Keep the rhythm natural, direct, practical, and confident.
"""

DEFAULT_OFFER_CONTEXT = """
We sell a high-ticket Amazon growth mentorship for existing Amazon sellers.
Entry price starts at $1400.
The offer helps sellers improve cash flow, PPC efficiency, product economics, scaling systems, operations, and marketplace expansion.
The CTA should never sound generic, pushy, or pasted on. It must fit the specific pain, belief shift, or opportunity in the script.
Do not use direct CTA, apply, book-call, or sales-call language for now.
"""

DEFAULT_CTA_MIX = "50% none, 50% soft, 0% direct"


def _short_prompt_value(value: str | None, limit: int) -> str:
    text = " ".join((value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def build_short_scripts_prompt(
    count: int,
    author_style: str | None,
    offer_context: str | None = None,
    cta_mix: str | None = None,
    topic_hint: str | None = None,
    exclusion_context: str | None = None,
    editorial_briefs: list[EditorialBrief] | None = None,
    word_budget: WordBudget | None = None,
    content_language: str = "en",
) -> str:
    style = _short_prompt_value(author_style or DEFAULT_AUTHOR_STYLE, 260)
    offer = _short_prompt_value(offer_context or DEFAULT_OFFER_CONTEXT, 420)
    cta_distribution = _short_prompt_value(cta_mix or DEFAULT_CTA_MIX, 120)
    hint = _short_prompt_value(topic_hint, 700)
    exclusions = _short_prompt_value(exclusion_context, 700)
    budget = word_budget or vertical_word_budget("original")
    language = normalize_content_language(content_language)
    language_name = prompt_language_name(language)
    language_rule = viewer_text_language_instruction(language)
    editorial = editorial_briefs_prompt(editorial_briefs or [])
    hint_line = f"\nFocus: {hint}" if hint else ""
    exclusions_line = f"\nAvoid repeating: {exclusions}" if exclusions else ""
    editorial_line = f"\n{editorial}" if editorial else ""
    return f"""
Return ONLY valid JSON. Use the NotebookLM sources.
Write {count} {language_name} short vertical-video script(s) for the target audience defined by the offer and NotebookLM sources.
Voice: {style}
Offer/context: {offer}
CTA mix: {cta_distribution}
Language rule: {language_rule}
Rules: no markdown, practical and specific. {length_instruction(budget)}{hint_line}{exclusions_line}
Social performance rules:
- One sharp idea only: a pain, a mechanism, and a payoff.
- The first sentence must create tension in 1-2 seconds: hidden mistake, contrarian warning, or specific money leak.
- Build retention as setup -> turn -> proof/example -> payoff. No generic advice.
- Use concrete niche-specific stakes. For Amazon/ecommerce: margin, PPC waste, cash flow, fees, inventory, rankings, operations, or expansion.
- Resolve the curiosity gap by the end; do not end as a vague teaser.
- Make the idea feel new compared with the avoided titles, hooks, and fingerprints.
{editorial_line}

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
    "hook_type": "hidden mistake | contrarian warning | money leak | belief shift",
    "hook": "",
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


def build_youtube_script_prompt(
    author_style: str | None,
    offer_context: str | None = None,
    cta_mix: str | None = None,
    topic_hint: str | None = None,
    exclusion_context: str | None = None,
    editorial_briefs: list[EditorialBrief] | None = None,
    word_budget: WordBudget | None = None,
    content_language: str = "en",
) -> str:
    style = (author_style or DEFAULT_AUTHOR_STYLE).strip()
    offer = (offer_context or DEFAULT_OFFER_CONTEXT).strip()
    cta_distribution = (cta_mix or DEFAULT_CTA_MIX).strip()
    budget = word_budget or youtube_word_budget(10)
    language = normalize_content_language(content_language)
    language_rule = viewer_text_language_instruction(language)
    hint = f"\nAdditional user focus: {topic_hint.strip()}\n" if topic_hint else ""
    exclusions = _short_prompt_value(exclusion_context, 1200)
    exclusions_line = f"\nAvoid repeating these prior title/hook/fingerprint patterns:\n{exclusions}\n" if exclusions else ""
    editorial = editorial_briefs_prompt(editorial_briefs or [])
    editorial_line = f"\nEditorial direction:\n{editorial}\n" if editorial else ""
    return f"""
You are a YouTube strategist and scriptwriter for a high-ticket education product in the niche defined by the offer and NotebookLM sources.

OUTPUT LANGUAGE:
- {language_rule}
- Keep the language natural, spoken, and creator-like.
- The final viewer-facing hook, trigger, voiceover, CTA, title, and explanations must all follow that language rule.

Product:
- course / mentorship for Amazon sellers;
- entry price starts at 1400 USD;
- video goal: deliver strong expert value and warm the viewer up to buy.

Audience:
- already active in the niche, not beginners;
- wants growth, systems, more profit, and control;
- does not need basic beginner explanations unless the source context explicitly says otherwise.

Author voice:
{style}

Important: preserve the author's cadence, directness, and conversational style, but follow the output language rule above.

Current offer context:
{offer}

Alex Hormozi-style funnel logic:
- open with a strong pain point or hidden mistake;
- show that the problem is systemic;
- give a new perspective and a practical framework;
- show the cost of inaction;
- softly lead to the idea that mentorship/course speeds up the path and reduces chaos.

Retention and packaging logic:
- Define one core promise for the viewer before writing.
- Open with a specific tension, not a broad topic intro.
- Add a new open loop every 45-75 seconds and close it with a concrete example.
- Include pattern interrupts: contrarian line, number, mistake, or diagnostic question.
- Keep every section tied to concrete niche-specific stakes. For Amazon/ecommerce: profit, cash flow, PPC waste, inventory, operations, or expansion.
- Avoid generic "grow your Amazon business" advice unless it is attached to a mechanism and example.

CTA strategy:
- Use this CTA mix guidance for the video's CTA placement: {cta_distribution}.
- Do not paste a generic CTA. Write CTA moments that fit the specific topic and offer context.
- Direct CTA is disabled for now. Use a soft CTA or end on a strong belief shift.

Task:
Using this NotebookLM knowledge base, write 1 YouTube script.
- {length_instruction(budget)}
- Do not make it shorter than the minimum or longer than the maximum word count.
{hint}
{exclusions_line}
{editorial_line}
Return only valid JSON. No Markdown. No prose outside JSON.
Schema:
[
  {{
    "title": "video title",
    "content_format": "",
    "content_pillar": "",
    "proof_type": "",
    "emotion_angle": "",
    "series_name": "",
    "topic_fingerprint": "pain + mechanism + audience moment + payoff",
    "angle": "main idea",
    "core_promise": "specific viewer payoff",
    "retention_beats": ["hook", "open loop", "framework", "example", "payoff"],
    "hook": "first 15 seconds hook",
    "trigger": "main trigger",
    "voiceover": "full script with approximate timing and conversational delivery",
    "cta_type": "none | soft",
    "cta_reason": "why this CTA level fits this video",
    "cta": "organic CTA moments for the middle/end, or empty string for none",
    "why_it_works": "why this warms up the high-ticket audience",
    "source_basis": "which knowledge base materials and ideas were used"
  }}
]
""".strip()

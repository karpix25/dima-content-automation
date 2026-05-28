from __future__ import annotations


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


def build_short_scripts_prompt(
    count: int,
    author_style: str | None,
    offer_context: str | None = None,
    cta_mix: str | None = None,
    topic_hint: str | None = None,
    exclusion_context: str | None = None,
) -> str:
    style = (author_style or DEFAULT_AUTHOR_STYLE).strip()
    offer = (offer_context or DEFAULT_OFFER_CONTEXT).strip()
    cta_distribution = (cta_mix or DEFAULT_CTA_MIX).strip()
    hint = f"\nAdditional user focus: {topic_hint.strip()}\n" if topic_hint else ""
    exclusions = f"\nAlready used ideas to avoid:\n{exclusion_context.strip()}\n" if exclusion_context else ""
    return f"""
Write {count} fresh short vertical-video script(s) from this NotebookLM knowledge base.

Language: English only. No Russian/Cyrillic in any value.
Audience: Amazon sellers who already sell and want growth, profit, systems, and control. Not beginners.
Offer context: high-ticket Amazon growth course/mentorship, entry from 1400 USD.
Author voice: {style}
CTA guidance: {cta_distribution}. Direct CTA is disabled. No "book a call", "apply", "DM me", or "buy now".
Hormozi logic: make the viewer feel a valuable gap between chaotic selling and a better operating system.

Each voiceover must be 30-60 seconds, conversational, practical, and specific.
Use a different pain/mechanism for each script: cash flow, PPC, margin leaks, inventory, reviews, operations, scaling, or team systems.
{hint}
{exclusions}
Avoid repeated topics, metaphors, hook structures, and problem framing.

Return ONLY valid JSON, no Markdown, with this exact compact schema:
[
  {{
    "title": "short topic",
    "angle": "specific angle",
    "hook": "first line",
    "trigger": "core pain",
    "voiceover": "spoken English script",
    "cta_type": "none or soft",
    "cta": "specific soft CTA or empty string",
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
) -> str:
    style = (author_style or DEFAULT_AUTHOR_STYLE).strip()
    offer = (offer_context or DEFAULT_OFFER_CONTEXT).strip()
    cta_distribution = (cta_mix or DEFAULT_CTA_MIX).strip()
    hint = f"\nAdditional user focus: {topic_hint.strip()}\n" if topic_hint else ""
    return f"""
You are a YouTube strategist and scriptwriter for a high-ticket education product about growing an Amazon business.

OUTPUT LANGUAGE:
- Write all content in English.
- Keep the language natural, spoken, and creator-like.
- Do not use Russian, Cyrillic, or bilingual phrasing in any JSON value.
- If the NotebookLM sources or author voice examples are in Russian, extract the meaning and rewrite it in natural spoken English.
- The final viewer-facing hook, trigger, voiceover, CTA, title, and explanations must all be English.

Product:
- course / mentorship for Amazon sellers;
- entry price starts at 1400 USD;
- video goal: deliver strong expert value and warm the viewer up to buy.

Audience:
- already selling on Amazon;
- wants growth, systems, more profit, and control;
- does not need basic explanations like "what is Amazon FBA".

Author voice:
{style}

Important: preserve the author's cadence, directness, and conversational style, but do not preserve the language if the style notes are not in English. The output must still be English.

Current offer context:
{offer}

Alex Hormozi-style funnel logic:
- open with a strong pain point or hidden mistake;
- show that the problem is systemic;
- give a new perspective and a practical framework;
- show the cost of inaction;
- softly lead to the idea that mentorship/course speeds up the path and reduces chaos.

CTA strategy:
- Use this CTA mix guidance for the video's CTA placement: {cta_distribution}.
- Do not paste a generic CTA. Write CTA moments that fit the specific topic and offer context.
- Direct CTA is disabled for now. Use a soft CTA or end on a strong belief shift.

Task:
Using this NotebookLM knowledge base, write 1 YouTube script up to 15 minutes.
{hint}
Return only valid JSON. No Markdown. No prose outside JSON.
Schema:
[
  {{
    "title": "video title",
    "angle": "main idea",
    "hook": "first 15 seconds hook",
    "trigger": "main trigger",
    "voiceover": "full English script with approximate timing and conversational delivery",
    "cta_type": "none | soft",
    "cta_reason": "why this CTA level fits this video",
    "cta": "organic CTA moments for the middle/end, or empty string for none",
    "why_it_works": "why this warms up the high-ticket audience",
    "source_basis": "which knowledge base materials and ideas were used"
  }}
]
""".strip()

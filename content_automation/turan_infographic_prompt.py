from __future__ import annotations

from .storage import ScriptRecord


def build_turan_infographic_prompt(
    *,
    record: ScriptRecord,
    bullets: list[str],
    cta_text: str | None = None,
    has_references: bool = False,
    has_face_references: bool = False,
    has_design_references: bool = False,
) -> str:
    copy = build_social_card_copy(record=record, bullets=bullets, cta_text=cta_text)
    reference_rule = reference_instruction(has_references, has_face_references, has_design_references)
    return (
        "Create a finished vertical Instagram/Reels business infographic card, 9:16. "
        f"{reference_rule}"
        "Use only the exact text below on the card. Do not invent new facts and do not rewrite it. "
        "Retention strategy: this is a 5-second video card designed to take 14-16 seconds to read, encouraging pause, rewatch, and longer average view duration. "
        "Social hook rules: the card must feel like a sharp expert social post, not a document. "
        "Keep the expert meaning from the source: Amazon margins, SQP, PPC caps, Lost Keywords, operations, or cash conversion. "
        "H1 max 48 characters, 5-9 words, direct, specific, pain-first, trigger-driven, high contrast. "
        "Subtitle max 82 characters. Main block: exactly 5 expert points, max 68 characters each. "
        "No final thought paragraph, no generic motivation, no vague claims, no numbered list above 5 items. "
        "Target 52-68 visible words total so the viewer needs longer than the 5-second video to read it. "
        "Text fit rules: no cropped words, no broken words, no ellipses, no text outside safe margins; "
        "if needed reduce copy density before reducing hierarchy. "
        f'H1/top headline exact text: "{copy.headline}". '
        f'H2/subtitle exact text: "{copy.subtitle}". '
        f"Main block items: {'; '.join(copy.items)}. "
        f'CTA window text: "{copy.cta}". '
        "Design style: one solid warm golden-sand background, exact color #EBC97C, no gradient and no shade shift. "
        "Minimal premium business infographic, no logos, no watermarks, no fake UI, no extra colors, no decorative clutter. "
        "At the top, place a large black headline directly on the gold background. "
        "Below it, place one large off-white/milky rounded rectangle block with only the 5 useful expert points. "
        "At the bottom, place a separate off-white CTA window. "
        "Use strictly Montserrat or Montserrat-like geometric sans-serif: headline ExtraBold/Black, body SemiBold, CTA ExtraBold. "
        "Do not use serif, handwritten, condensed, decorative, Arial-like, or Instagram UI fonts. "
        "Add a realistic cutout sticker of the author: man with dark hair, thick dark beard, expressive eyebrows, "
        "confident or engaged expression, pointing at the main block or CTA, 18-22% of frame height. "
        "The author must not cover important text. "
        "Text must be large, clean, readable, aligned, useful, and dense enough to reward reading without looking cluttered. "
        "The final image must look like a polished Turan five-second infographic card, ready for video."
    )


class SocialCardCopy:
    def __init__(self, *, headline: str, subtitle: str, items: list[str], cta: str) -> None:
        self.headline = headline
        self.subtitle = subtitle
        self.items = items
        self.cta = cta


def build_social_card_copy(*, record: ScriptRecord, bullets: list[str], cta_text: str | None = None) -> SocialCardCopy:
    source = " ".join(
        clean_prompt_text(item)
        for item in [
            record.title,
            record.hook,
            record.angle,
            record.trigger,
            record.voiceover,
            record.cta,
            record.source_basis,
            *bullets,
        ]
        if clean_prompt_text(item)
    )
    headline = trigger_headline(source, fallback=record.hook or record.title)
    subtitle = limit_chars(record.trigger or record.angle or record.voiceover or "Fix the bottleneck first", 70)
    items = concise_items(bullets, record)
    cta = limit_chars(cta_text or record.cta or "Follow for more", 48)
    return SocialCardCopy(headline=headline, subtitle=subtitle, items=items, cta=cta)


def trigger_headline(source: str, *, fallback: str | None) -> str:
    normalized = source.lower()
    if ("sqp" in normalized or "search query" in normalized) and ("margin" in normalized or "profit" in normalized):
        return "Your Margins Are Bleeding In SQP."
    if ("agency" in normalized or "agencies" in normalized) and ("sqp" in normalized or "search query" in normalized):
        return "Your Agency Missed The SQP Leak."
    if ("ppc" in normalized or "ad spend" in normalized or "ads" in normalized) and (
        "margin" in normalized or "profit" in normalized
    ):
        return "Your PPC Is Eating Margin."
    if "sqp" in normalized or "search query" in normalized:
        return "Check SQP Before Scaling."
    if any(word in normalized for word in ("cash", "margin", "profit")) and any(word in normalized for word in ("sales", "revenue")):
        return "Sales Up. Margin Down."
    if "agency" in normalized or "agencies" in normalized:
        return "Your Agency Missed The Leak."
    if "margin" in normalized or "profit" in normalized:
        return "Your Profit Is Leaking."
    return title_case(limit_chars(remove_soft_opening(fallback or "Fix This Before Scaling"), 48))


def concise_items(bullets: list[str], record: ScriptRecord) -> list[str]:
    source = " ".join(clean_prompt_text(item) for item in [*bullets, record.voiceover, record.trigger, record.angle] if item)
    items = expert_items_from_source(source)
    candidates = [*bullets, record.trigger, record.cta, record.angle]
    for candidate in candidates:
        clean = clean_prompt_text(candidate)
        if not clean or should_skip_item(clean):
            continue
        short = limit_chars(clean, 68).rstrip(".")
        if short and short.lower() not in {item.lower() for item in items}:
            items.append(short)
        if len(items) == 5:
            break
    fallbacks = [
        "Find the operational bottleneck before scaling",
        "Fix margin before increasing ad spend",
        "Use data before agency opinions",
        "Separate revenue growth from cash conversion",
        "Turn seller chaos into a repeatable system",
    ]
    while len(items) < 5:
        items.append(fallbacks[len(items)])
    return items[:5]


def expert_items_from_source(source: str) -> list[str]:
    normalized = source.lower()
    items: list[str] = []
    rules = [
        (("high sales", "sales volume", "revenue"), ("margin", "profit"), "High sales can hide a broken contribution margin"),
        (("agency", "agencies"), ("sqp", "search query"), "SQP exposes the leaks agency reports miss"),
        (("ppc cap", "capping", "cap on your daily ppc"), ("ppc",), "Daily PPC caps protect cash before scale"),
        (("lost keywords", "lost keyword"), ("sqp", "search query"), "Lost Keywords show where profit is leaking"),
        (("operator burnout", "burnout"), ("bottleneck", "operational"), "Operator burnout usually means an ops bottleneck"),
        (("cash conversion", "cash disappears"), ("revenue", "sales"), "Revenue growth means nothing without cash conversion"),
    ]
    for primary, secondary, text in rules:
        if any(token in normalized for token in primary) and any(token in normalized for token in secondary):
            items.append(text)
    return items


def clean_prompt_text(value: str | None) -> str:
    return " ".join((value or "").replace("\n", " ").split())


def limit_chars(value: str | None, limit: int) -> str:
    clean = clean_prompt_text(value)
    if len(clean) <= limit:
        return clean
    words: list[str] = []
    for word in clean.split():
        candidate = " ".join([*words, word]).strip()
        if len(candidate) > limit:
            break
        words.append(word)
    return " ".join(words) or clean[:limit].rstrip()


def remove_soft_opening(value: str) -> str:
    clean = clean_prompt_text(value)
    lowered = clean.lower()
    for prefix in ("if your ", "if you ", "stop listening to ", "why "):
        if lowered.startswith(prefix):
            return clean[len(prefix) :]
    return clean


def title_case(value: str) -> str:
    return " ".join(word[:1].upper() + word[1:] for word in value.split())


def should_skip_item(value: str) -> bool:
    lowered = value.lower()
    skip_markers = ("derived from", "webinar transcripts", "source", "notebooklm", "excerpt")
    return any(marker in lowered for marker in skip_markers)


def reference_instruction(has_references: bool, has_face_references: bool, has_design_references: bool) -> str:
    if not has_references:
        return ""
    parts: list[str] = []
    if has_face_references:
        parts.append("Use the uploaded face reference image only for author identity and face likeness.")
    if has_design_references:
        parts.append(
            "Use uploaded infographic design references as a style board: extract the common layout, hierarchy, spacing, visual rhythm, and composition style. "
            "If references differ, choose the cleanest least text-heavy direction."
        )
    parts.append("Do not copy old text, logos, numbers, faces, or identities from design references; replace all text with the exact text below.")
    return " ".join(parts) + " "

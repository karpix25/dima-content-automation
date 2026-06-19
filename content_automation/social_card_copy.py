from __future__ import annotations

import re

from .storage import ScriptRecord


class SocialCardCopy:
    def __init__(self, *, headline: str, subtitle: str, items: list[str], cta: str) -> None:
        self.headline = headline
        self.subtitle = subtitle
        self.items = items
        self.cta = cta


def build_social_card_copy(
    *,
    record: ScriptRecord,
    bullets: list[str],
    cta_text: str | None = None,
    content_language: str = "auto",
) -> SocialCardCopy:
    language = card_language(record, content_language)
    source = " ".join(
        clean_prompt_text(item)
        for item in [record.title, record.hook, record.angle, record.trigger, record.voiceover, record.cta, *bullets]
        if clean_prompt_text(item)
    )
    headline = trigger_headline(source, fallback=record.hook or record.title)
    subtitle = limit_chars(record.trigger or record.angle or record.voiceover or "Fix the bottleneck first", 70)
    items = concise_items(bullets, record)
    cta = limit_chars(cta_text or record.cta or default_cta(language), 48)
    return SocialCardCopy(headline=headline, subtitle=subtitle, items=items, cta=cta)


def trigger_headline(source: str, *, fallback: str | None) -> str:
    normalized = source.lower()
    if has_cyrillic(source):
        return russian_trigger_headline(normalized, fallback=fallback)
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
    fallback_headline = limit_chars(remove_soft_opening(fallback or "Fix This Before Scaling"), 48)
    return sentence_case(fallback_headline) if has_cyrillic(fallback_headline) else title_case(fallback_headline)


def russian_trigger_headline(normalized: str, *, fallback: str | None) -> str:
    if "ppc" in normalized and "выруч" in normalized:
        return "PPC не пробьет потолок выручки"
    if "ppc" in normalized and ("марж" in normalized or "прибыл" in normalized):
        return "PPC съедает маржу"
    if "касс" in normalized or "cash flow" in normalized:
        return "Кассовый разрыв ближе, чем кажется"
    if "конверс" in normalized:
        return "Сначала проверь конверсию"
    if "арбитраж" in normalized:
        return "Арбитраж не строит бренд"
    return sentence_case(limit_chars(remove_soft_opening(fallback or "Проверь это до масштабирования"), 48))


def concise_items(bullets: list[str], record: ScriptRecord) -> list[str]:
    source = " ".join(clean_prompt_text(item) for item in [*bullets, record.voiceover, record.trigger, record.angle] if item)
    items = expert_items_from_source(source)
    candidates = [
        str(record.raw.get("mechanism") or ""),
        str(record.raw.get("visual_proof") or ""),
        str(record.raw.get("visual_retention_plan") or ""),
        *bullets,
        record.trigger,
        record.cta,
        record.angle,
    ]
    for candidate in candidates:
        clean = clean_prompt_text(candidate)
        if not clean or should_skip_item(clean):
            continue
        short = limit_chars(clean, 68).rstrip(".")
        if short and short.lower() not in {item.lower() for item in items}:
            items.append(short)
        if len(items) == 5:
            break
    fallbacks = fallback_items("ru" if has_cyrillic(source) else "en")
    while len(items) < 5:
        items.append(fallbacks[len(items)])
    return items[:5]


def expert_items_from_source(source: str) -> list[str]:
    normalized = source.lower()
    if has_cyrillic(source):
        return russian_expert_items_from_source(normalized)
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


def russian_expert_items_from_source(normalized: str) -> list[str]:
    items: list[str] = []
    rules = [
        (("ppc", "реклам"), ("выруч", "потолок"), "PPC не лечит слабую конверсию"),
        (("марж", "прибыл"), ("ppc", "реклам"), "Проверь маржу до разгона рекламы"),
        (("касс", "cash flow"), ("парт", "sku", "запуск"), "Заложи вторую партию в cash flow"),
        (("карточ", "листинг"), ("конверс", "трафик"), "Сначала усили карточку, потом трафик"),
        (("арбитраж",), ("бренд", "private label"), "Арбитраж дает cash flow, не капитализацию"),
    ]
    for primary, secondary, text in rules:
        if any(token in normalized for token in primary) and any(token in normalized for token in secondary):
            items.append(text)
    return items


def clean_prompt_text(value: str | None) -> str:
    clean = " ".join((value or "").replace("\n", " ").split())
    clean = re.sub(r"\b[\w.-]+\.(?:pdf|pptx?|docx?|xlsx?)\b", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\bslides?\s+\d+(?:[-–]\d+)?\b", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\bслайды?\s+\d+(?:[-–]\d+)?\b", "", clean, flags=re.IGNORECASE)
    return " ".join(clean.split())


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


def sentence_case(value: str) -> str:
    clean = clean_prompt_text(value)
    return clean[:1].upper() + clean[1:] if clean else clean


def should_skip_item(value: str) -> bool:
    lowered = value.lower()
    skip_markers = (
        "derived from",
        "webinar transcripts",
        "source",
        "notebooklm",
        "excerpt",
        "source_basis",
        "presentation",
        "slides",
        "script ",
        "lovepdf",
        "презентац",
        "слайд",
        "скрипт ",
        "опора из базы",
        "источник",
    )
    return any(marker in lowered for marker in skip_markers) or not has_viewer_value(value)


def has_viewer_value(value: str) -> bool:
    lowered = value.lower()
    business_terms = (
        "amazon",
        "ppc",
        "sqp",
        "margin",
        "profit",
        "cash",
        "revenue",
        "fba",
        "sku",
        "bsr",
        "марж",
        "прибыл",
        "выруч",
        "реклам",
        "бюджет",
        "касс",
        "товар",
        "карточ",
        "склад",
        "запас",
        "конверс",
        "арбитраж",
    )
    return any(term in lowered for term in business_terms)


def card_language(record: ScriptRecord, content_language: str) -> str:
    if content_language in {"ru", "en"}:
        return content_language
    source = " ".join([record.title, record.hook, record.angle, record.trigger, record.voiceover, record.cta])
    return "ru" if has_cyrillic(source) else "en"


def has_cyrillic(value: str) -> bool:
    return bool(re.search(r"[\u0400-\u04FF]", value or ""))


def default_cta(language: str) -> str:
    return "Сохрани разбор" if language == "ru" else "Save this breakdown"


def fallback_items(language: str) -> list[str]:
    if language == "ru":
        return [
            "Проверь экономику до разгона рекламы",
            "Раздели рост выручки и реальную прибыль",
            "Найди узкое место в карточке товара",
            "Считай cash flow до новой партии",
            "Масштабируй только после диагностики",
        ]
    return [
        "Find the operational bottleneck before scaling",
        "Fix margin before increasing ad spend",
        "Use data before agency opinions",
        "Separate revenue growth from cash conversion",
        "Turn seller chaos into a repeatable system",
    ]

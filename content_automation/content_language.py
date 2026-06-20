from __future__ import annotations

import re

CONTENT_LANGUAGE_AUTO = "auto"
CONTENT_LANGUAGE_EN = "en"
CONTENT_LANGUAGE_RU = "ru"
CONTENT_LANGUAGE_VALUES = {CONTENT_LANGUAGE_AUTO, CONTENT_LANGUAGE_EN, CONTENT_LANGUAGE_RU}


def normalize_content_language(value: str | None) -> str:
    normalized = (value or CONTENT_LANGUAGE_AUTO).strip().lower()
    aliases = {
        "english": CONTENT_LANGUAGE_EN,
        "eng": CONTENT_LANGUAGE_EN,
        "en-us": CONTENT_LANGUAGE_EN,
        "en_us": CONTENT_LANGUAGE_EN,
        "russian": CONTENT_LANGUAGE_RU,
        "rus": CONTENT_LANGUAGE_RU,
        "ru-ru": CONTENT_LANGUAGE_RU,
        "ru_ru": CONTENT_LANGUAGE_RU,
        "source": CONTENT_LANGUAGE_AUTO,
        "original": CONTENT_LANGUAGE_AUTO,
        "detect": CONTENT_LANGUAGE_AUTO,
    }
    normalized = aliases.get(normalized, normalized)
    return normalized if normalized in CONTENT_LANGUAGE_VALUES else CONTENT_LANGUAGE_AUTO


def resolve_content_language(value: str | None, source_text: str | None = None) -> str:
    normalized = normalize_content_language(value)
    if normalized != CONTENT_LANGUAGE_AUTO:
        return normalized
    return detect_content_language(source_text or "")


def detect_content_language(text: str) -> str:
    cyrillic = len(re.findall(r"[\u0400-\u04FF]", text or ""))
    latin = len(re.findall(r"[A-Za-z]", text or ""))
    return CONTENT_LANGUAGE_RU if cyrillic > latin else CONTENT_LANGUAGE_EN


def prompt_language_name(value: str | None) -> str:
    normalized = normalize_content_language(value)
    if normalized == CONTENT_LANGUAGE_EN:
        return "English"
    if normalized == CONTENT_LANGUAGE_RU:
        return "Russian"
    return "the dominant language of the original source content"


def viewer_text_language_instruction(value: str | None) -> str:
    normalized = normalize_content_language(value)
    if normalized == CONTENT_LANGUAGE_EN:
        return (
            "All viewer-facing text must be in English. Do not use Russian, Cyrillic, "
            "or bilingual phrasing."
        )
    if normalized == CONTENT_LANGUAGE_RU:
        return (
            "All viewer-facing text must be in natural Russian. Do not write English "
            "headlines, UI labels, CTA text, or mixed bilingual copy unless the source "
            "uses a necessary Amazon term such as Buy Box, FBA, SKU, PPC, ACOS, or BSR."
        )
    return (
        "All viewer-facing text must match the dominant language of the original source "
        "content or transcript. Do not translate the visuals into a different language."
    )


def should_reject_cyrillic_scripts(value: str | None) -> bool:
    return normalize_content_language(value) == CONTENT_LANGUAGE_EN

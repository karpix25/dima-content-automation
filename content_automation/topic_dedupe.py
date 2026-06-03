from __future__ import annotations

import difflib
import re
from typing import Any


WORD_RE = re.compile(r"[a-z0-9]+")
FINGERPRINT_TERM_LIMIT = 18

STOPWORDS = {
    "about",
    "after",
    "again",
    "amazon",
    "because",
    "before",
    "business",
    "could",
    "every",
    "from",
    "have",
    "into",
    "just",
    "more",
    "seller",
    "sellers",
    "should",
    "that",
    "their",
    "there",
    "they",
    "this",
    "through",
    "video",
    "what",
    "when",
    "while",
    "with",
    "your",
}


def payload_text(payload: dict[str, object], field: str) -> str:
    return str(payload.get(field) or "").strip()


def normalize_for_similarity(text: str | None) -> str:
    return " ".join(WORD_RE.findall((text or "").lower()))


def similarity(left: str | None, right: str | None) -> float:
    left_norm = normalize_for_similarity(left)
    right_norm = normalize_for_similarity(right)
    if not left_norm or not right_norm:
        return 0.0
    return difflib.SequenceMatcher(None, left_norm, right_norm).ratio()


def script_topic_fingerprint(payload: dict[str, Any]) -> str:
    explicit = normalize_for_similarity(str(payload.get("topic_fingerprint") or ""))
    if explicit:
        return _limited_terms(explicit)
    source = " ".join(
        str(payload.get(field) or "")
        for field in ("title", "angle", "hook", "trigger")
    )
    first_voiceover_sentence = re.split(r"(?<=[.!?])\s+", str(payload.get("voiceover") or "").strip())[0]
    return _limited_terms(f"{source} {first_voiceover_sentence}")


def record_topic_fingerprint(record: Any) -> str:
    explicit = normalize_for_similarity(str(getattr(record, "topic_fingerprint", "") or ""))
    if explicit:
        return _limited_terms(explicit)
    raw = getattr(record, "raw", {}) or {}
    if isinstance(raw, dict):
        return script_topic_fingerprint(raw)
    return _limited_terms(
        " ".join(
            str(getattr(record, field, "") or "")
            for field in ("title", "angle", "hook", "trigger", "voiceover")
        )
    )


def script_payload_is_duplicate(
    payload: dict[str, object],
    existing_records: list[Any],
    accepted_payloads: list[dict[str, object]],
) -> bool:
    return any(payload_is_similar_to_record(payload, record) for record in existing_records) or any(
        payload_is_similar_to_payload(payload, other) for other in accepted_payloads
    )


def payload_is_similar_to_record(payload: dict[str, object], record: Any) -> bool:
    return (
        similarity(payload_text(payload, "title"), getattr(record, "title", "")) >= 0.86
        or similarity(payload_text(payload, "hook"), getattr(record, "hook", "")) >= 0.78
        or similarity(payload_text(payload, "voiceover"), getattr(record, "voiceover", "")) >= 0.72
        or fingerprints_are_similar(script_topic_fingerprint(payload), record_topic_fingerprint(record))
    )


def payload_is_similar_to_payload(payload: dict[str, object], other: dict[str, object]) -> bool:
    return (
        similarity(payload_text(payload, "title"), payload_text(other, "title")) >= 0.86
        or similarity(payload_text(payload, "hook"), payload_text(other, "hook")) >= 0.78
        or similarity(payload_text(payload, "voiceover"), payload_text(other, "voiceover")) >= 0.72
        or fingerprints_are_similar(script_topic_fingerprint(payload), script_topic_fingerprint(other))
    )


def fingerprints_are_similar(left: str, right: str) -> bool:
    if not left or not right:
        return False
    return similarity(left, right) >= 0.68 or token_overlap(left, right) >= 0.55


def token_overlap(left: str, right: str) -> float:
    left_terms = set(normalize_for_similarity(left).split())
    right_terms = set(normalize_for_similarity(right).split())
    if not left_terms or not right_terms:
        return 0.0
    return len(left_terms & right_terms) / min(len(left_terms), len(right_terms))


def build_exclusion_context(records: list[Any], *, limit: int = 30) -> str:
    lines: list[str] = []
    for record in records[:limit]:
        title = str(getattr(record, "title", "") or "").strip()
        hook = str(getattr(record, "hook", "") or "").strip()
        fingerprint = record_topic_fingerprint(record)
        if title or hook or fingerprint:
            lines.append(f"- Title: {title}; Hook: {hook}; Fingerprint: {fingerprint}")
    return "\n".join(lines)


def build_payload_exclusion_context(payloads: list[dict[str, object]], *, limit: int = 30) -> str:
    lines: list[str] = []
    for payload in payloads[:limit]:
        title = payload_text(payload, "title")
        hook = payload_text(payload, "hook")
        fingerprint = script_topic_fingerprint(payload)
        if title or hook or fingerprint:
            lines.append(f"- Title: {title}; Hook: {hook}; Fingerprint: {fingerprint}")
    return "\n".join(lines)


def _limited_terms(text: str) -> str:
    terms: list[str] = []
    for term in WORD_RE.findall(text.lower()):
        if len(term) < 3 or term in STOPWORDS or term in terms:
            continue
        terms.append(term)
        if len(terms) >= FINGERPRINT_TERM_LIMIT:
            break
    return " ".join(terms)

from __future__ import annotations

import re
from dataclasses import dataclass

from .content_language import detect_content_language, resolve_content_language
from .storage import ScriptRecord
from .vertical_director import build_vertical_director_scenes, build_vertical_scene_art


@dataclass(frozen=True)
class MontagePlan:
    scenes: list[dict]
    word_cues: list[dict]


def build_montage_plan(
    record: ScriptRecord,
    *,
    duration_seconds: float,
    max_scenes: int = 8,
    transcript_words: list[dict] | None = None,
    content_language: str = "auto",
) -> MontagePlan:
    timed_words = _transcript_word_cues(transcript_words)
    if record.format in {"short", "avatar_reels"} and timed_words:
        directed = build_vertical_director_scenes(
            record,
            duration_seconds=duration_seconds,
            max_scenes=max_scenes,
            transcript_words=timed_words,
            content_language=content_language,
        )
        if directed:
            return MontagePlan(scenes=directed.scenes, word_cues=directed.word_cues)
    scenes = _scenes(
        record,
        duration_seconds=duration_seconds,
        max_scenes=max_scenes,
        transcript_words=timed_words,
        content_language=content_language,
    )
    word_cues = timed_words or _word_cues(record.voiceover, duration_seconds=duration_seconds)
    return MontagePlan(scenes=scenes, word_cues=word_cues)


def _scenes(
    record: ScriptRecord,
    *,
    duration_seconds: float,
    max_scenes: int,
    transcript_words: list[dict],
    content_language: str,
) -> list[dict]:
    language = resolve_content_language(content_language, _record_viewer_text(record))
    texts = _scene_texts(record, language=language)
    titles = [_clean(item) for item in texts if _clean(item)]
    titles = titles[: max(1, max_scenes)]
    if not titles:
        titles = [_clean(record.title) or "Main idea"]
    starts = _scene_starts(titles, transcript_words, duration_seconds=duration_seconds)
    segment = max(1.0, duration_seconds / len(titles))
    scenes: list[dict] = []
    for index, title in enumerate(titles):
        start = starts[index] if index < len(starts) else round(index * segment, 3)
        next_start = starts[index + 1] if index + 1 < len(starts) else None
        fallback_end = min(duration_seconds, (index + 1) * segment)
        end = round(min(duration_seconds, next_start - 0.08 if next_start else fallback_end), 3)
        art = build_vertical_scene_art(
            title=title,
            text=title,
            index=index,
            content_language=language,
            cta=record.cta,
        )
        scenes.append(
            {
                "id": f"scene-{index + 1}",
                "start": start,
                "end": max(start + 0.5, end),
                "mode": "full" if index == 0 else "overlay",
                **art,
            }
        )
    return scenes


def _scene_texts(record: ScriptRecord, *, language: str) -> list[str]:
    primary = [
        record.hook,
    ]
    secondary = [
        record.trigger,
        record.angle,
        record.why_it_works,
        record.source_basis,
    ]
    narrative = [
        *_sentences(record.voiceover),
        record.cta,
        record.title,
    ]
    values: list[str] = []
    seen: set[str] = set()
    for item in primary:
        _append_unique(values, seen, item)
    for item in secondary:
        if _matches_language(item, language=language):
            _append_unique(values, seen, item)
    for item in narrative:
        _append_unique(values, seen, item)
    return values


def _append_unique(values: list[str], seen: set[str], value: str | None) -> None:
    clean = _clean(value)
    key = clean.lower()
    if clean and key not in seen and not _is_near_duplicate(key, seen):
        seen.add(key)
        values.append(clean)


def _is_near_duplicate(key: str, seen: set[str]) -> bool:
    if len(key) < 12:
        return False
    return any(key in existing or existing in key for existing in seen if len(existing) >= 12)


def _matches_language(value: str | None, *, language: str) -> bool:
    clean = _clean(value)
    if not clean:
        return False
    detected = detect_content_language(clean)
    if language == "ru":
        return detected == "ru"
    if language == "en":
        return detected == "en"
    return True


def _record_viewer_text(record: ScriptRecord) -> str:
    return " ".join(
        item
        for item in (record.title, record.hook, record.voiceover, record.cta)
        if _clean(item)
    )


def _transcript_word_cues(words: list[dict] | None) -> list[dict]:
    cues: list[dict] = []
    for item in words or []:
        text = str(item.get("punctuated_word") or item.get("text") or item.get("word") or "").strip()
        start = _float_or_none(item.get("start"))
        end = _float_or_none(item.get("end"))
        if not text or start is None or end is None or end <= start:
            continue
        cues.append(
            {
                "word": str(item.get("word") or text).strip(),
                "text": text,
                "punctuated_word": text,
                "start": round(start, 3),
                "end": round(end, 3),
            }
        )
    return cues


def _scene_starts(titles: list[str], transcript_words: list[dict], *, duration_seconds: float) -> list[float]:
    fallback = _fallback_starts(len(titles), duration_seconds=duration_seconds)
    if not transcript_words:
        return fallback

    transcript_terms = [_normalize_word(item.get("word") or item.get("text")) for item in transcript_words]
    starts: list[float] = []
    cursor = 0
    for index, title in enumerate(titles):
        anchor_index = _find_anchor_index(_meaningful_words(title), transcript_terms, cursor)
        min_start = starts[-1] + 0.65 if starts else 0
        if anchor_index is None:
            starts.append(round(max(min_start, fallback[index]), 3))
            continue
        raw_start = _float_or_none(transcript_words[anchor_index].get("start")) or fallback[index]
        start = max(min_start, min(raw_start, max(0, duration_seconds - 0.5)))
        starts.append(round(start, 3))
        cursor = anchor_index + 1
    return starts


def _fallback_starts(count: int, *, duration_seconds: float) -> list[float]:
    segment = max(1.0, duration_seconds / max(1, count))
    return [round(index * segment, 3) for index in range(count)]


def _find_anchor_index(title_terms: list[str], transcript_terms: list[str], cursor: int) -> int | None:
    terms = title_terms[:8]
    if not terms or not transcript_terms:
        return None
    best_index: int | None = None
    best_offset = 0
    best_score = 0.0
    window_size = max(len(terms) + 3, 5)
    for index in range(max(0, cursor), len(transcript_terms)):
        window = transcript_terms[index : index + window_size]
        if not window:
            break
        score = sum(1 for term in terms if term in window) / len(terms)
        if score > best_score:
            best_score = score
            best_index = index
            best_offset = _first_term_offset(terms, window)
    threshold = 0.45 if len(terms) >= 4 else 0.6
    return best_index + best_offset if best_index is not None and best_score >= threshold else None


def _first_term_offset(terms: list[str], window: list[str]) -> int:
    for offset, word in enumerate(window):
        if word in terms:
            return offset
    return 0


def _word_cues(text: str, *, duration_seconds: float) -> list[dict]:
    words = re.findall(r"[\w'-]+", text or "", flags=re.UNICODE)
    if not words:
        return []
    step = max(0.05, duration_seconds / len(words))
    return [
        {
            "word": word,
            "text": word,
            "punctuated_word": word,
            "start": round(index * step, 3),
            "end": round(min(duration_seconds, (index + 1) * step), 3),
        }
        for index, word in enumerate(words)
    ]


def _sentences(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"(?<=[.!?])\s+", value or "") if item.strip()]


def _visual_elements(title: str) -> list[str]:
    words = re.findall(r"[\w'-]{4,}", title or "", flags=re.UNICODE)
    return words[:4] or ["business", "analytics", "growth"]


def _clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _meaningful_words(value: str) -> list[str]:
    return [
        normalized
        for word in re.findall(r"[\w'-]{3,}", value or "", flags=re.UNICODE)
        if (normalized := _normalize_word(word))
    ]


def _normalize_word(value: object) -> str:
    return re.sub(r"[^\w'-]+", "", str(value or "").lower(), flags=re.UNICODE)


def _float_or_none(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

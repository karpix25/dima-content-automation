from __future__ import annotations

import re
from dataclasses import dataclass

from .storage import ScriptRecord


@dataclass(frozen=True)
class DirectedScene:
    scenes: list[dict]
    word_cues: list[dict]


def build_vertical_director_scenes(
    record: ScriptRecord,
    *,
    duration_seconds: float,
    max_scenes: int,
    transcript_words: list[dict],
) -> DirectedScene | None:
    sentences = _sentences_from_words(transcript_words)
    if not sentences:
        return None
    language = _detect_language(" ".join(sentence["text"] for sentence in sentences))
    selected = _select_beats(sentences, duration_seconds=duration_seconds, max_scenes=max_scenes)
    if not selected:
        return None
    scenes = [
        _scene_from_sentence(record, sentence, index=index, duration_seconds=duration_seconds, language=language)
        for index, sentence in enumerate(selected)
    ]
    return DirectedScene(scenes=scenes, word_cues=_word_cues_from_transcript(transcript_words))


def _sentences_from_words(words: list[dict]) -> list[dict]:
    sentences: list[dict] = []
    current: list[dict] = []
    for item in words:
        text = _clean(str(item.get("punctuated_word") or item.get("text") or item.get("word") or ""))
        start = _float_or_none(item.get("start"))
        end = _float_or_none(item.get("end"))
        if not text or start is None or end is None:
            continue
        current.append({"text": text, "start": start, "end": end})
        if re.search(r"[.!?]$", text) or len(current) >= 20:
            sentences.append(_pack_sentence(current))
            current = []
    if current:
        sentences.append(_pack_sentence(current))
    return [sentence for sentence in sentences if len(sentence["text"].split()) >= 5]


def _pack_sentence(words: list[dict]) -> dict:
    return {
        "text": _clean(" ".join(str(item["text"]) for item in words)),
        "start": round(float(words[0]["start"]), 3),
        "end": round(float(words[-1]["end"]), 3),
    }


def _select_beats(sentences: list[dict], *, duration_seconds: float, max_scenes: int) -> list[dict]:
    usable = [
        sentence
        for sentence in sentences
        if 1.0 <= float(sentence["start"]) <= max(1.0, duration_seconds - 2.0)
    ]
    if not usable:
        usable = sentences
    target_count = min(max(2, min(max_scenes, 5)), len(usable))
    if len(usable) <= target_count:
        return usable
    anchors = [duration_seconds * (index + 1) / (target_count + 1) for index in range(target_count)]
    selected: list[dict] = []
    for anchor in anchors:
        candidates = [item for item in usable if item not in selected]
        selected.append(min(candidates, key=lambda item: abs(float(item["start"]) - anchor)))
    return sorted(selected, key=lambda item: float(item["start"]))


def _scene_from_sentence(
    record: ScriptRecord,
    sentence: dict,
    *,
    index: int,
    duration_seconds: float,
    language: str,
) -> dict:
    text = _clean(str(sentence["text"]))
    title = _fit_title(text, language=language)
    subtitle = _fit_subtitle(text, title=title)
    start = max(0.8, float(sentence["start"]) - 0.05)
    end = min(duration_seconds, max(start + 3.8, float(sentence["end"]) + 2.2))
    terms = _visual_terms(text)
    return {
        "id": f"scene-{index + 1}",
        "start": round(start, 3),
        "end": round(end, 3),
        "mode": "director_cutaway",
        "title": title,
        "chapterTitle": title,
        "subtitle": subtitle,
        "insight": subtitle,
        "cta": _clean(record.cta),
        "language": language,
        "visualElements": terms,
        "imagePrompt": _image_prompt(title=title, subtitle=subtitle, terms=terms, language=language),
    }


def _fit_title(text: str, *, language: str) -> str:
    clean = _headline_rewrite(text) if language == "en" else text
    clean = re.sub(r"^(you are|i see|we recently|that is|this is)\s+", "", clean, flags=re.I)
    clean = re.sub(r"\b(because|without|instead of|which is exactly)\b.*$", "", clean, flags=re.I)
    words = clean.split()
    if language == "en":
        title = _trim_trailing_stopword(" ".join(words[:7]))
        title = _title_case(title)
    else:
        title = " ".join(words[:6])
    return _clean(title).rstrip(".,;:") or _clean(text).split(".")[0][:42]


def _fit_subtitle(text: str, *, title: str) -> str:
    clean = _clean(text)
    if clean.lower().startswith(title.lower()):
        clean = _clean(clean[len(title) :])
    words = clean.split()
    return " ".join(words[:12]).rstrip(".,;:") if words else title


def _headline_rewrite(text: str) -> str:
    clean = _clean(text).rstrip(".")
    patterns = [
        (r"^here is how we (.+)$", r"\1"),
        (r"^at \d+\s*(am|pm),?\s+we (.+)$", r"\2"),
        (r"^if by \d+\s*(am|pm),?\s+sales drop by more than ([^,]+),.+$", r"Sales drop means price sensitive"),
        (r"^but if (.+),\s+we keep the (.+)$", r"If \1, keep the \2"),
        (r"^we just added (.+?) to a sku.+single dollar bump.+$", r"\1 from one dollar bump"),
    ]
    for pattern, replacement in patterns:
        next_value = re.sub(pattern, replacement, clean, flags=re.I)
        if next_value != clean:
            return next_value
    return clean


def _trim_trailing_stopword(value: str) -> str:
    stopwords = {"a", "an", "and", "at", "by", "for", "from", "of", "the", "to", "with"}
    words = value.split()
    while words and words[-1].lower().strip(".,;:") in stopwords:
        words.pop()
    return " ".join(words)


def _title_case(value: str) -> str:
    keep = {"SKU", "FBA", "BSR", "PPC", "ACOS"}
    words = []
    for word in value.split():
        clean = word.strip(".,;:")
        upper = clean.upper()
        words.append(upper if upper in keep else word[:1].upper() + word[1:])
    return " ".join(words)


def _image_prompt(*, title: str, subtitle: str, terms: list[str], language: str) -> str:
    text_rule = (
        "Do not include Russian text. If any readable text appears, it must be English and limited to tiny object labels."
        if language == "en"
        else "If readable text appears, it must match the source language and be minimal."
    )
    return (
        "Premium 1:1 editorial cutaway image for a vertical Amazon seller expert video. "
        "No poster text, no headline text, no subtitles inside the image. "
        f"{text_rule} "
        "Create a concrete business visual metaphor with Amazon marketplace operations, packaging, FBA fees, SKU documents, "
        "supplier negotiation, unit economics, dashboards, product boxes, warehouse details, or margin evidence. "
        "Use one clear central subject, clean off-white background, deep navy, muted red audit marks, premium magazine style. "
        f"Director headline context: {title}. Subtitle context: {subtitle}. Visual anchors: {', '.join(terms)}."
    )


def _word_cues_from_transcript(words: list[dict]) -> list[dict]:
    cues: list[dict] = []
    for item in words:
        text = _clean(str(item.get("punctuated_word") or item.get("text") or item.get("word") or ""))
        start = _float_or_none(item.get("start"))
        end = _float_or_none(item.get("end"))
        if text and start is not None and end is not None and end > start:
            cues.append(
                {
                    "word": str(item.get("word") or text),
                    "text": text,
                    "punctuated_word": text,
                    "start": round(start, 3),
                    "end": round(end, 3),
                }
            )
    return cues


def _visual_terms(text: str) -> list[str]:
    stop = {"your", "because", "without", "checking", "exactly", "doing", "this", "that", "they", "their"}
    words = re.findall(r"[A-Za-z][A-Za-z0-9$+.-]{3,}", text)
    unique: list[str] = []
    for word in words:
        normalized = word.lower().strip(".,;:")
        if normalized in stop or normalized in unique:
            continue
        unique.append(normalized)
    return unique[:6] or ["amazon", "margin", "packaging"]


def _detect_language(text: str) -> str:
    cyrillic = len(re.findall(r"[\u0400-\u04FF]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    return "ru" if cyrillic > latin else "en"


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _float_or_none(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

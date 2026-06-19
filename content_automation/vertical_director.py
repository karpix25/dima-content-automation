from __future__ import annotations

import re
from dataclasses import dataclass

from .content_language import resolve_content_language
from .storage import ScriptRecord
from .vertical_storyboard import build_storyboard_frame, build_storyboard_image_prompt


_SUBTITLE_TRAILING_STOPS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "because",
    "but",
    "by",
    "for",
    "from",
    "if",
    "in",
    "is",
    "of",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
    "your",
}


@dataclass(frozen=True)
class DirectedScene:
    scenes: list[dict]
    word_cues: list[dict]


def build_vertical_scene_art(
    *,
    title: str,
    text: str,
    index: int,
    content_language: str = "auto",
    cta: str = "",
) -> dict:
    language = resolve_content_language(content_language, f"{title} {text}")
    clean_text = _clean(text or title)
    headline = _fit_title(title or clean_text, language=language)
    terms = _visual_terms(clean_text or headline)
    frame = build_storyboard_frame(title=headline, text=clean_text, index=index)
    subtitle = _fit_subtitle(clean_text, title=headline, role=frame.role)
    return {
        "title": headline,
        "chapterTitle": headline,
        "subtitle": subtitle,
        "insight": subtitle,
        "cta": _clean(cta),
        "language": language,
        "visualElements": terms,
        "template": frame.template,
        "motionPattern": frame.pattern,
        "cutawayRole": frame.role,
        "directorCue": frame.cue,
        "metricValue": frame.metric_value,
        "metricLabel": frame.metric_label,
        "evidenceLabel": frame.evidence,
        "storyPoint": frame.story_point,
        "visualMetaphor": frame.visual_metaphor,
        "storyContrast": frame.contrast,
        "mustShow": list(frame.must_show),
        "imagePrompt": build_storyboard_image_prompt(
            frame=frame,
            title=headline,
            subtitle=subtitle,
            terms=terms,
            language=language,
        ),
    }


def build_vertical_director_scenes(
    record: ScriptRecord,
    *,
    duration_seconds: float,
    max_scenes: int,
    transcript_words: list[dict],
    content_language: str = "auto",
) -> DirectedScene | None:
    sentences = _sentences_from_words(transcript_words)
    if not sentences:
        return None
    language = resolve_content_language(content_language, " ".join(sentence["text"] for sentence in sentences))
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
            sentences.append(_pack_sentence(current, closed=True))
            current = []
    if current:
        sentences.append(_pack_sentence(current, closed=False))
    if len(sentences) == 1 and not sentences[0]["closed"]:
        return []
    return [sentence for sentence in sentences if len(sentence["text"].split()) >= 5]


def _pack_sentence(words: list[dict], *, closed: bool) -> dict:
    return {
        "text": _clean(" ".join(str(item["text"]) for item in words)),
        "start": round(float(words[0]["start"]), 3),
        "end": round(float(words[-1]["end"]), 3),
        "closed": closed,
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
    start = max(0.8, float(sentence["start"]) - 0.05)
    end = min(duration_seconds, max(start + 3.8, float(sentence["end"]) + 2.2))
    art = build_vertical_scene_art(
        title=title,
        text=text,
        index=index,
        content_language=language,
        cta=record.cta,
    )
    return {
        "id": f"scene-{index + 1}",
        "start": round(start, 3),
        "end": round(end, 3),
        "mode": "director_cutaway",
        **art,
    }


def _fit_title(text: str, *, language: str) -> str:
    clean = _headline_rewrite(text) if language == "en" else text
    clean = re.sub(r"^(you are|i see|we recently|that is|this is)\s+", "", clean, flags=re.I)
    clean = re.sub(r"^(но|и|а)\s+", "", clean, flags=re.I)
    clean = re.sub(r"\b(because|without|instead of|which is exactly)\b.*$", "", clean, flags=re.I)
    words = clean.split()
    if language == "en":
        title = _trim_trailing_stopword(" ".join(words[:5]))
        title = _title_case(title)
    else:
        title = _trim_trailing_stopword(" ".join(words[:6]))
    return _clean(title).rstrip(".,;:") or _clean(text).split(".")[0][:42]


def _fit_subtitle(text: str, *, title: str, role: str = "") -> str:
    if role in {"proof", "greenlight", "price move"}:
        return ""
    clean = _clean(text)
    if clean.lower().startswith(title.lower()):
        clean = _clean(clean[len(title) :])
    clean = _trim_incomplete_subtitle(clean)
    words = clean.split()
    words = words[:12]
    while words and words[-1].lower().strip(".,;:") in _SUBTITLE_TRAILING_STOPS:
        words.pop()
    return " ".join(words).rstrip(".,;:") if words else ""


def _trim_incomplete_subtitle(value: str) -> str:
    clean = _clean(value).lstrip(" ,.;:-")
    if not clean:
        return ""
    clean = re.sub(r"^(but\s+if|if)\s+", "", clean, flags=re.I)
    first_clause = re.split(r"(?<=[.!?])\s+|[,;]\s+", clean, maxsplit=1)[0]
    words = first_clause.split()
    if len(words) > 14:
        words = words[:14]
    while words and words[-1].lower().strip(".,;:") in _SUBTITLE_TRAILING_STOPS:
        words.pop()
    if len(words) < 4:
        return ""
    return " ".join(words)


def _headline_rewrite(text: str) -> str:
    clean = _clean(text).rstrip(".")
    patterns = [
        (r"^here is how we test price elasticity.+$", r"Price elasticity test"),
        (r"^.*\bexactly one dollar\b.*$", r"$1 price bump"),
        (r"^.*\bbump the price by exactly\b.*$", r"$1 price bump"),
        (r"^if by \d+\s*(am|pm),?\s+sales drop by more than ([^,]+),.+$", r"Demand broke"),
        (r"^sales drop means price sensitive.+$", r"Demand broke"),
        (r"^but if velocity holds.+$", r"Velocity holds"),
        (r"^if velocity holds.+$", r"Velocity holds"),
        (r"^here is how we (.+)$", r"\1"),
        (r"^at \d+\s*(am|pm),?\s+we (.+)$", r"\2"),
        (r"^but if (.+),\s+we keep the (.+)$", r"If \1, keep the \2"),
        (r"^we just added .*pure daily profit.+$", r"Daily profit lever"),
        (r"^that .* becomes pure daily profit.+$", r"Daily profit lever"),
        (r"^we just added (.+?) to a sku.+single dollar bump.+$", r"\1 from one dollar bump"),
    ]
    for pattern, replacement in patterns:
        next_value = re.sub(pattern, replacement, clean, flags=re.I)
        if next_value != clean:
            return next_value
    return clean


def _trim_trailing_stopword(value: str) -> str:
    stopwords = {
        "a",
        "an",
        "and",
        "at",
        "by",
        "for",
        "from",
        "of",
        "the",
        "to",
        "with",
        "а",
        "без",
        "в",
        "и",
        "или",
        "как",
        "к",
        "на",
        "не",
        "но",
        "по",
        "с",
        "то",
        "что",
        "чтобы",
        "за",
    }
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
    stop = {
        "your",
        "because",
        "without",
        "checking",
        "exactly",
        "doing",
        "this",
        "that",
        "they",
        "their",
        "это",
        "как",
        "для",
        "что",
        "или",
        "ваш",
        "ваша",
        "ваши",
        "потому",
        "который",
    }
    words = re.findall(r"[\w$+.-]{3,}", text or "", flags=re.UNICODE)
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

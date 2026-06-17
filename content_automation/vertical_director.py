from __future__ import annotations

import re
from dataclasses import dataclass

from .content_language import resolve_content_language
from .storage import ScriptRecord


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
    terms = _visual_terms(text)
    visual = _visual_story(title=title, text=text, index=index)
    subtitle = _fit_subtitle(text, title=title, role=visual["role"])
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
        "template": visual["template"],
        "motionPattern": visual["pattern"],
        "cutawayRole": visual["role"],
        "directorCue": visual["cue"],
        "metricValue": visual["metric_value"],
        "metricLabel": visual["metric_label"],
        "evidenceLabel": visual["evidence"],
        "imagePrompt": _image_prompt(
            title=title,
            subtitle=subtitle,
            terms=terms,
            language=language,
            visual_story=visual["story"],
            role=visual["role"],
        ),
    }


def _fit_title(text: str, *, language: str) -> str:
    clean = _headline_rewrite(text) if language == "en" else text
    clean = re.sub(r"^(you are|i see|we recently|that is|this is)\s+", "", clean, flags=re.I)
    clean = re.sub(r"\b(because|without|instead of|which is exactly)\b.*$", "", clean, flags=re.I)
    words = clean.split()
    if language == "en":
        title = _trim_trailing_stopword(" ".join(words[:5]))
        title = _title_case(title)
    else:
        title = " ".join(words[:5])
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


def _visual_story(*, title: str, text: str, index: int) -> dict[str, str]:
    joined = f"{title} {text}".lower()
    if "sales drop" in joined or "price sensitive" in joined:
        return {
            "template": "decision",
            "pattern": "demand_drop",
            "role": "decision point",
            "cue": "Demand reaction",
            "metric_value": "50%",
            "metric_label": "drop threshold",
            "evidence": "stop if demand breaks",
            "story": "Show a seller analytics screen from first-person perspective: hourly sales line drops after a price test, conversion and BSR widgets sit nearby, and red marker annotations circle the break point.",
        }
    if "velocity" in joined and ("hold" in joined or "keep" in joined):
        return {
            "template": "greenlight",
            "pattern": "velocity_hold",
            "role": "greenlight",
            "cue": "Velocity check",
            "metric_value": "HOLD",
            "metric_label": "velocity stable",
            "evidence": "keep the bump",
            "story": "Show a seller dashboard from first-person perspective where the velocity chart stays stable after a price change; highlight the hold zone with a green check and a red bracket around the price test window.",
        }
    if "profit" in joined or "sku" in joined:
        return {
            "template": "proof",
            "pattern": "profit_proof",
            "role": "proof",
            "cue": "Profit proof",
            "metric_value": "+$1",
            "metric_label": "daily profit lever",
            "evidence": "proof beats theory",
            "story": "Show a unit-economics interface board from first-person perspective: SKU card, selling price, FBA fee, margin, daily units, and profit total, with arrows showing the extra dollar flowing into daily profit.",
        }
    if "elasticity" in joined or "test" in joined:
        return {
            "template": "diagnostic",
            "pattern": "test_setup",
            "role": "diagnostic test",
            "cue": "A/B price test setup",
            "metric_value": "A/B",
            "metric_label": "price test",
            "evidence": "measure before scaling",
            "story": "Show an Amazon listing and seller dashboard interface from first-person perspective: two price options, BSR trend, review stars, Buy Box panel, and a red circle pointing to the metric that decides the test.",
        }
    if "$1" in joined or "exactly $1" in joined or "bump the price" in joined:
        return {
            "template": "lever",
            "pattern": "price_lever",
            "role": "price move",
            "cue": "$1 price lever",
            "metric_value": "$1",
            "metric_label": "controlled bump",
            "evidence": "small move, measured risk",
            "story": "Show a seller interface mockup from first-person perspective: product listing price changes from $23.99 to $24.99, Buy Box remains visible, margin calculator updates, and red arrows connect price to profit.",
        }
    cues = ["Audit point", "Hidden lever", "Margin check", "Operator move", "Proof frame"]
    return {
        "template": "analysis",
        "pattern": "audit_point",
        "role": "analysis",
        "cue": cues[index % len(cues)],
        "metric_value": "CHECK",
        "metric_label": "operator signal",
        "evidence": "make the hidden lever visible",
        "story": "Show the practical Amazon operator consequence as a first-person interface teardown: a listing panel, seller metric cards, and red annotations that explain what the expert is pointing at.",
    }


def _image_prompt(
    *,
    title: str,
    subtitle: str,
    terms: list[str],
    language: str,
    visual_story: str,
    role: str,
) -> str:
    text_rule = (
        "Do not include Russian text. Use short English UI labels, SKU tags, values, arrows, and object annotations only when they clarify the evidence."
        if language == "en"
        else "Use short Russian UI labels, SKU tags, values, arrows, and object annotations only when they clarify the evidence."
    )
    return (
        "Create a central square first-person Amazon interface teardown image for a vertical Amazon seller expert video. "
        "It will be placed inside an HTML/CSS Hyperframes card; Hyperframes adds the headline, metric chip, and evidence caption. "
        "Do not design a full poster, thumbnail, slide, or complete card. "
        "No big headline text, no subtitles, no logos, no watermarks, no social-media thumbnail copy. "
        f"{text_rule} "
        "Make it feel like the expert is showing a real screen or printed interface board from their point of view. "
        "Use a realistic but generic Amazon-style product listing interface, seller dashboard modules, Buy Box panel, conversion card, BSR chart, review stars, price block, trust-signal checklist, unit-economics panel, product thumbnails, and metric cards when they fit the beat. "
        "Add 2-4 useful moodboard-style annotations: red hand-drawn circle, arrow, bracket, underline, check mark, cross mark, or sticky-note callout. "
        "Show the decision, consequence, or evidence through interface modules, highlighted metrics, annotated charts, short UI labels, numeric callouts, and operator notes. "
        "Make the image information-rich: include 4-7 small evidence details such as SKU card, Buy Box state, margin note, price tag, BSR line, conversion percentage, fee tier marker, trust checklist, review count, or before/after value. "
        "Keep the top-right and bottom edge visually clean for HTML overlays, but keep the main interface dense enough to teach something. "
        "No decorative filler, no generic business people. "
        f"Director role: {role}. Required visual action: {visual_story} "
        "Use a clean bright off-white workspace, light paper surfaces, pale gray UI cards, thin navy lines, realistic UI spacing, and muted red/orange annotation accents. "
        "Avoid dark dashboards, black blocks, heavy machinery, dense shadows, and cargo-heavy compositions, but keep enough labeled detail to feel analytical. "
        "Make it feel practical, premium, editorial, realistic, and easy to scan, like a consultant marking up an Amazon seller screen. "
        f"Visual anchors: {', '.join(terms)}."
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

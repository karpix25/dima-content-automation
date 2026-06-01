from __future__ import annotations

import re
from dataclasses import dataclass

from .storage import ScriptRecord


@dataclass(frozen=True)
class MontagePlan:
    scenes: list[dict]
    word_cues: list[dict]


def build_montage_plan(record: ScriptRecord, *, duration_seconds: float, max_scenes: int = 8) -> MontagePlan:
    scenes = _scenes(record, duration_seconds=duration_seconds, max_scenes=max_scenes)
    return MontagePlan(scenes=scenes, word_cues=_word_cues(record.voiceover, duration_seconds=duration_seconds))


def _scenes(record: ScriptRecord, *, duration_seconds: float, max_scenes: int) -> list[dict]:
    texts = [
        record.hook,
        record.trigger,
        record.angle,
        record.why_it_works,
        record.source_basis,
        record.cta,
        *_sentences(record.voiceover),
    ]
    titles = [_clean(item) for item in texts if _clean(item)]
    titles = titles[: max(1, max_scenes)]
    if not titles:
        titles = [_clean(record.title) or "Main idea"]
    segment = max(1.0, duration_seconds / len(titles))
    scenes: list[dict] = []
    for index, title in enumerate(titles):
        start = round(index * segment, 3)
        end = round(min(duration_seconds, (index + 1) * segment), 3)
        scenes.append(
            {
                "id": f"scene-{index + 1}",
                "start": start,
                "end": max(start + 0.5, end),
                "mode": "full" if index == 0 else "overlay",
                "title": title[:92],
                "chapterTitle": title[:64],
                "insight": _clean(record.title or record.angle)[:120],
                "cta": _clean(record.cta)[:120],
                "visualElements": _visual_elements(title),
            }
        )
    return scenes


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

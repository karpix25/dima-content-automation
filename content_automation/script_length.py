from __future__ import annotations

import re
from dataclasses import dataclass


DEFAULT_SPOKEN_WORDS_PER_MINUTE = 150
SHORT_ORIGINAL_WORD_RANGE = (80, 120)
YOUTUBE_TOLERANCE = 0.08
FIXED_VERTICAL_TOLERANCE = 0.12


@dataclass(frozen=True)
class WordBudget:
    min_words: int
    max_words: int
    target_words: int
    target_seconds: int | None
    label: str

    def contains(self, text: str) -> bool:
        count = count_spoken_words(text)
        return self.min_words <= count <= self.max_words


def count_spoken_words(text: str | None) -> int:
    return len(re.findall(r"[\w'-]+", text or "", flags=re.UNICODE))


def vertical_word_budget(mode: str | None, *, wpm: int = DEFAULT_SPOKEN_WORDS_PER_MINUTE) -> WordBudget:
    normalized = (mode or "original").strip().lower()
    if normalized == "original":
        return WordBudget(
            min_words=SHORT_ORIGINAL_WORD_RANGE[0],
            max_words=SHORT_ORIGINAL_WORD_RANGE[1],
            target_words=sum(SHORT_ORIGINAL_WORD_RANGE) // 2,
            target_seconds=None,
            label="original Shorts length",
        )
    seconds = int(normalized) if normalized in {"30", "45", "60", "90"} else 45
    return budget_from_seconds(seconds, tolerance=FIXED_VERTICAL_TOLERANCE, label=f"{seconds}s vertical avatar", wpm=wpm)


def youtube_word_budget(minutes: int, *, wpm: int = DEFAULT_SPOKEN_WORDS_PER_MINUTE) -> WordBudget:
    safe_minutes = max(3, min(30, int(minutes or 10)))
    return budget_from_seconds(
        safe_minutes * 60,
        tolerance=YOUTUBE_TOLERANCE,
        label=f"{safe_minutes} min horizontal YouTube",
        wpm=wpm,
    )


def budget_from_seconds(seconds: int, *, tolerance: float, label: str, wpm: int) -> WordBudget:
    target_words = round(max(1, seconds) * max(1, wpm) / 60)
    spread = max(8, round(target_words * tolerance))
    return WordBudget(
        min_words=max(1, target_words - spread),
        max_words=target_words + spread,
        target_words=target_words,
        target_seconds=max(1, seconds),
        label=label,
    )


def length_instruction(budget: WordBudget) -> str:
    seconds = f" ({budget.target_seconds}s)" if budget.target_seconds else ""
    return (
        f"Voiceover length: {budget.min_words}-{budget.max_words} spoken words, "
        f"target about {budget.target_words} words for {budget.label}{seconds}."
    )

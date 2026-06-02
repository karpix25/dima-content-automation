from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .script_length import DEFAULT_SPOKEN_WORDS_PER_MINUTE, WordBudget, count_spoken_words
from .video_overlay import probe_duration_seconds


MIN_ELEVENLABS_SPEED = 0.7
MAX_ELEVENLABS_SPEED = 1.2
SPEED_ADJUSTMENT_TOLERANCE = 0.08


@dataclass(frozen=True)
class VoiceoverTimingAnalysis:
    words: int
    duration_seconds: float
    words_per_minute: float
    target_duration_seconds: float
    current_speed: float
    recommended_speed: float
    should_regenerate: bool


def analyze_voiceover_timing(
    *,
    text: str,
    audio_path: Path,
    budget: WordBudget,
    current_speed: float,
    spoken_wpm: int = DEFAULT_SPOKEN_WORDS_PER_MINUTE,
) -> VoiceoverTimingAnalysis:
    words = count_spoken_words(text)
    duration = probe_duration_seconds(audio_path)
    target_duration = target_duration_seconds(words=words, budget=budget, spoken_wpm=spoken_wpm)
    ratio = duration / target_duration if target_duration > 0 else 1
    recommended = clamp_speed(current_speed * ratio)
    should_regenerate = abs(ratio - 1) > SPEED_ADJUSTMENT_TOLERANCE and abs(recommended - current_speed) >= 0.01
    return VoiceoverTimingAnalysis(
        words=words,
        duration_seconds=duration,
        words_per_minute=words / duration * 60 if duration > 0 else 0,
        target_duration_seconds=target_duration,
        current_speed=current_speed,
        recommended_speed=recommended,
        should_regenerate=should_regenerate,
    )


def estimate_initial_voiceover_speed(
    *,
    text: str,
    budget: WordBudget,
    base_speed: float,
    spoken_wpm: int = DEFAULT_SPOKEN_WORDS_PER_MINUTE,
) -> float:
    if not budget.target_seconds:
        return clamp_speed(base_speed)
    words = count_spoken_words(text)
    if words <= 0:
        return clamp_speed(base_speed)
    required_wpm = words / budget.target_seconds * 60
    return clamp_speed(base_speed * required_wpm / max(1, spoken_wpm))


def target_duration_seconds(*, words: int, budget: WordBudget, spoken_wpm: int) -> float:
    if budget.target_seconds:
        return float(budget.target_seconds)
    return max(1.0, words / max(1, spoken_wpm) * 60)


def clamp_speed(value: float) -> float:
    return round(max(MIN_ELEVENLABS_SPEED, min(MAX_ELEVENLABS_SPEED, value)), 3)

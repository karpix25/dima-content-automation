from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field


class NotebookLMScriptGenerationError(ValueError):
    pass


@dataclass
class ScriptGenerationAttemptStats:
    parsed_items: int = 0
    accepted_items: int = 0
    parse_errors: list[str] = field(default_factory=list)
    rejected: Counter[str] = field(default_factory=Counter)

    def reject(self, reason: str) -> None:
        self.rejected[reason] += 1


def merge_attempt_stats(attempts: list[ScriptGenerationAttemptStats]) -> ScriptGenerationAttemptStats:
    merged = ScriptGenerationAttemptStats()
    for attempt in attempts:
        merged.parsed_items += attempt.parsed_items
        merged.accepted_items += attempt.accepted_items
        merged.parse_errors.extend(attempt.parse_errors)
        merged.rejected.update(attempt.rejected)
    return merged


def script_generation_failure_message(stats: ScriptGenerationAttemptStats) -> str:
    if stats.accepted_items:
        return ""
    if stats.parse_errors and not stats.parsed_items:
        return (
            "NotebookLM ответил невалидным JSON после нескольких попыток. "
            "Я уже прошу по одному сценарию за раз, поэтому проблема не в размере пачки. "
            "Чаще всего NotebookLM добавляет обычный текст вместо JSON или обрывает ответ."
        )
    if stats.rejected:
        reasons = ", ".join(_reason_label(reason, count) for reason, count in stats.rejected.most_common())
        return f"NotebookLM ответил, но сценарии не прошли проверку: {reasons}."
    return "NotebookLM не вернул сценарии в ожидаемом JSON-формате."


def retry_correction_for_stats(stats: ScriptGenerationAttemptStats, *, reject_cyrillic: bool) -> str:
    if stats.parse_errors:
        return (
            "CRITICAL CORRECTION: the previous response was not valid JSON. "
            "Return ONLY a raw JSON array. No markdown, no explanation, no prose before or after JSON. "
            "Return exactly one complete script object with all required fields."
        )
    if stats.rejected.get("word_budget"):
        return (
            "CRITICAL CORRECTION: the previous script missed the required voiceover word count. "
            "Regenerate one fresh script and keep voiceover inside the requested word range."
        )
    if stats.rejected.get("duplicate"):
        return (
            "CRITICAL CORRECTION: the previous script repeated an old idea or another generated script. "
            "Use a different pain, mechanism, hook, and topic fingerprint."
        )
    if reject_cyrillic and stats.rejected.get("cyrillic"):
        return (
            "CRITICAL CORRECTION: the previous response contained Russian/Cyrillic. "
            "Regenerate in English only. No Cyrillic characters anywhere in JSON values."
        )
    return (
        "CRITICAL CORRECTION: regenerate one fresh script in the requested output language. "
        "Return ONLY valid JSON with no markdown or explanation."
    )


def _reason_label(reason: str, count: int) -> str:
    labels = {
        "cyrillic": "не тот язык",
        "word_budget": "не попал в длину озвучки",
        "exact_duplicate": "точный повтор",
        "duplicate": "похожая тема уже есть",
        "empty_json": "пустой список",
    }
    return f"{labels.get(reason, reason)} x{count}"

from pathlib import Path

import content_automation.voiceover_timing as voiceover_timing
from content_automation.script_length import vertical_word_budget


def test_analyze_voiceover_timing_recommends_speed_up_for_slow_audio(monkeypatch):
    monkeypatch.setattr(voiceover_timing, "probe_duration_seconds", lambda path: 75.0)
    budget = vertical_word_budget("60")

    analysis = voiceover_timing.analyze_voiceover_timing(
        text=" ".join(["word"] * 150),
        audio_path=Path("audio.mp3"),
        budget=budget,
        current_speed=1.0,
    )

    assert analysis.should_regenerate is True
    assert analysis.recommended_speed == 1.2
    assert round(analysis.words_per_minute) == 120


def test_analyze_voiceover_timing_keeps_speed_when_close(monkeypatch):
    monkeypatch.setattr(voiceover_timing, "probe_duration_seconds", lambda path: 62.0)
    budget = vertical_word_budget("60")

    analysis = voiceover_timing.analyze_voiceover_timing(
        text=" ".join(["word"] * 150),
        audio_path=Path("audio.mp3"),
        budget=budget,
        current_speed=1.05,
    )

    assert analysis.should_regenerate is False
    assert analysis.recommended_speed == 1.085

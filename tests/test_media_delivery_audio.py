from types import SimpleNamespace

from content_automation import media_delivery
from content_automation.storage import ScriptRecord


def test_generate_audio_keeps_first_file_when_adjusted_regeneration_returns_no_file(monkeypatch, tmp_path):
    calls = []

    class FakeElevenLabs:
        def __init__(self, **kwargs):
            pass

        def text_to_speech(self, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                return SimpleNamespace(file_path=str(tmp_path / "first.mp3"), message="first ok")
            return SimpleNamespace(file_path=None, message="second failed")

    monkeypatch.setattr(media_delivery, "ElevenLabsMCPClient", FakeElevenLabs)
    monkeypatch.setattr(media_delivery, "estimate_initial_voiceover_speed", lambda **kwargs: 1.05)
    monkeypatch.setattr(
        media_delivery,
        "analyze_voiceover_timing",
        lambda **kwargs: SimpleNamespace(
            should_regenerate=True,
            recommended_speed=1.2,
            current_speed=1.05,
            words=108,
            duration_seconds=39.89,
            words_per_minute=162.5,
            target_duration_seconds=32.89,
        ),
    )

    path = media_delivery._generate_audio(
        _record(),
        "42",
        _settings(tmp_path),
        "voice-1",
        "Voice",
        word_budget=SimpleNamespace(target_seconds=30),
        voice_wpm=190,
    )

    assert path.endswith("first.mp3")
    assert [call["speed"] for call in calls] == [1.05, 1.2]


def _settings(tmp_path):
    return SimpleNamespace(
        elevenlabs_api_key="test",
        elevenlabs_mcp_command=None,
        elevenlabs_output_directory=tmp_path,
        elevenlabs_speed=1.0,
        elevenlabs_model_id="eleven_multilingual_v2",
        elevenlabs_stability=0.5,
        elevenlabs_similarity_boost=0.8,
        elevenlabs_style=0.0,
        elevenlabs_language="en",
    )


def _record() -> ScriptRecord:
    return ScriptRecord(
        id=8,
        user_id="42",
        format="short",
        status="approved",
        title="Title",
        angle="Angle",
        hook="Hook",
        trigger="Trigger",
        voiceover="Amazon sellers should test profit before scaling.",
        cta="CTA",
        why_it_works="Why",
        source_basis="Source",
        raw={},
    )

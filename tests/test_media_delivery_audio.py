from types import SimpleNamespace

from content_automation import media_delivery
from content_automation.storage import ScriptRecord


def test_generate_audio_retries_when_first_attempt_returns_no_file(monkeypatch, tmp_path):
    calls = []

    class FakeElevenLabs:
        def __init__(self, **kwargs):
            pass

        def text_to_speech(self, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                return SimpleNamespace(file_path=None, message="first failed")
            return SimpleNamespace(file_path=str(tmp_path / "second.mp3"), message="second ok")

    monkeypatch.setattr(media_delivery, "ElevenLabsMCPClient", FakeElevenLabs)
    monkeypatch.setattr(
        media_delivery,
        "fit_voiceover_for_duration",
        lambda **kwargs: kwargs["record"],
    )

    fitted, path = media_delivery._generate_audio(
        _record(),
        "42",
        _settings(tmp_path),
        SimpleNamespace(get_setting=lambda *args: None, set_setting=lambda *args: None),
        "voice-1",
        "Voice",
        word_budget=SimpleNamespace(target_seconds=30),
    )

    assert fitted.voiceover == _record().voiceover
    assert path.endswith("second.mp3")
    assert [call["speed"] for call in calls] == [1.0, 1.0]


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
        kie_api_key=None,
        kie_base_url="https://api.kie.ai",
        kie_text_model="gemini-3-flash",
        kie_text_timeout_seconds=30,
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

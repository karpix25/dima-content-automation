from types import SimpleNamespace

from content_automation import voiceover_fit
from content_automation.storage import ScriptRecord, Storage


def test_fit_voiceover_uses_kie_when_text_misses_character_target(tmp_path, monkeypatch):
    storage = Storage(tmp_path / "db.sqlite3")
    storage.set_setting("42", "elevenlabs_voice_chars_per_second", "10")
    storage.set_setting("42", "elevenlabs_voice_chars_per_second_voice_id", "voice-a")
    prompts = []

    class FakeKieTextClient:
        def __init__(self, config):
            self.config = config

        def is_configured(self):
            return True

        def complete(self, *, system, user):
            prompts.append((system, user))
            return "Rewritten voiceover sized for the final video."

    monkeypatch.setattr(voiceover_fit, "KieTextClient", FakeKieTextClient)

    fitted = voiceover_fit.fit_voiceover_for_duration(
        record=_record(),
        user_id="42",
        settings=_settings(),
        storage=storage,
        voice_id="voice-a",
        voice_name="Voice",
        word_budget=SimpleNamespace(target_seconds=30),
        elevenlabs=SimpleNamespace(),
    )

    assert fitted.voiceover == "Rewritten voiceover sized for the final video."
    assert "Target length: 300 characters" in prompts[0][1]
    assert "same language" in prompts[0][1]


def _settings():
    return SimpleNamespace(
        elevenlabs_model_id="eleven_multilingual_v2",
        elevenlabs_speed=1.0,
        elevenlabs_stability=0.5,
        elevenlabs_similarity_boost=0.8,
        elevenlabs_style=0.0,
        elevenlabs_language="en",
        kie_api_key="key",
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
        voiceover="Too short.",
        cta="CTA",
        why_it_works="Why",
        source_basis="Source",
        raw={},
    )

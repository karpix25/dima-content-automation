from types import SimpleNamespace

import content_automation.voice_speed_profile as voice_speed_profile
from content_automation.script_length import DEFAULT_SPOKEN_WORDS_PER_MINUTE, count_spoken_words
from content_automation.storage import Storage


def test_calibrated_voice_wpm_uses_matching_voice_id(tmp_path):
    storage = Storage(tmp_path / "db.sqlite3")
    storage.set_setting("42", "elevenlabs_voice_wpm", "171")
    storage.set_setting("42", "elevenlabs_voice_wpm_voice_id", "voice-a")

    assert voice_speed_profile.calibrated_voice_wpm(storage, "42", "voice-a") == 171
    assert voice_speed_profile.has_voice_wpm_profile(storage, "42", "voice-a") is True
    assert voice_speed_profile.calibrated_voice_wpm(storage, "42", "voice-b") == DEFAULT_SPOKEN_WORDS_PER_MINUTE
    assert voice_speed_profile.has_voice_wpm_profile(storage, "42", "voice-b") is False


def test_calibrate_voice_wpm_generates_template_and_saves_profile(tmp_path, monkeypatch):
    storage = Storage(tmp_path / "db.sqlite3")
    audio_path = tmp_path / "calibration.mp3"
    audio_path.write_bytes(b"audio")
    words = count_spoken_words(voice_speed_profile.CALIBRATION_TEXT)
    monkeypatch.setattr(voice_speed_profile, "probe_duration_seconds", lambda path: words / 180 * 60)

    class FakeElevenLabs:
        def text_to_speech(self, **kwargs):
            assert kwargs["text"] == voice_speed_profile.CALIBRATION_TEXT
            assert kwargs["voice_id"] == "voice-a"
            return SimpleNamespace(file_path=str(audio_path))

    wpm = voice_speed_profile.calibrate_voice_wpm(
        storage=storage,
        user_id="42",
        voice_id="voice-a",
        voice_name="Voice A",
        elevenlabs=FakeElevenLabs(),
        model_id="eleven_multilingual_v2",
        speed=1.0,
        stability=0.9,
        similarity_boost=0.97,
        style=0.0,
        language="en",
    )

    assert wpm == 180
    assert storage.get_setting("42", "elevenlabs_voice_wpm") == "180"
    assert storage.get_setting("42", "elevenlabs_voice_wpm_voice_id") == "voice-a"

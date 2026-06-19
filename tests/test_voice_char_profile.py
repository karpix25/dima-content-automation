from types import SimpleNamespace

import content_automation.voice_char_profile as voice_char_profile
from content_automation.storage import Storage


def test_calibration_text_has_fixed_character_count():
    assert len(voice_char_profile.calibration_text()) == voice_char_profile.CALIBRATION_CHAR_COUNT


def test_calibrate_voice_chars_per_second_saves_matching_voice_profile(tmp_path, monkeypatch):
    storage = Storage(tmp_path / "db.sqlite3")
    audio_path = tmp_path / "calibration.mp3"
    audio_path.write_bytes(b"audio")
    monkeypatch.setattr(voice_char_profile, "probe_duration_seconds", lambda path: 40.0)

    class FakeElevenLabs:
        def text_to_speech(self, **kwargs):
            assert kwargs["text"] == voice_char_profile.calibration_text()
            assert kwargs["voice_id"] == "voice-a"
            return SimpleNamespace(file_path=str(audio_path), message="ok")

    cps = voice_char_profile.calibrate_voice_chars_per_second(
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

    assert cps == 12.0
    assert voice_char_profile.has_voice_chars_profile(storage, "42", "voice-a") is True
    assert voice_char_profile.calibrated_voice_chars_per_second(storage, "42", "voice-a") == 12.0
    assert voice_char_profile.has_voice_chars_profile(storage, "42", "voice-b") is False

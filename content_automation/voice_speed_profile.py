from __future__ import annotations

from pathlib import Path

from .elevenlabs_mcp import ElevenLabsMCPClient
from .script_length import DEFAULT_SPOKEN_WORDS_PER_MINUTE, count_spoken_words
from .storage import Storage
from .video_overlay import probe_duration_seconds
from .voice_char_profile import calibration_text


CALIBRATION_TEXT = calibration_text()
VOICE_WPM_KEY = "elevenlabs_voice_wpm"
VOICE_WPM_ID_KEY = "elevenlabs_voice_wpm_voice_id"


def calibrated_voice_wpm(storage: Storage, user_id: str, voice_id: str | None) -> int:
    stored_voice_id = storage.get_setting(user_id, VOICE_WPM_ID_KEY)
    raw_wpm = storage.get_setting(user_id, VOICE_WPM_KEY)
    if voice_id and stored_voice_id != voice_id:
        return DEFAULT_SPOKEN_WORDS_PER_MINUTE
    try:
        wpm = int(float(raw_wpm or ""))
    except ValueError:
        return DEFAULT_SPOKEN_WORDS_PER_MINUTE
    return wpm if 80 <= wpm <= 240 else DEFAULT_SPOKEN_WORDS_PER_MINUTE


def has_voice_wpm_profile(storage: Storage, user_id: str, voice_id: str | None) -> bool:
    raw_wpm = storage.get_setting(user_id, VOICE_WPM_KEY)
    stored_voice_id = storage.get_setting(user_id, VOICE_WPM_ID_KEY)
    if voice_id and stored_voice_id != voice_id:
        return False
    try:
        wpm = int(float(raw_wpm or ""))
    except ValueError:
        return False
    return 80 <= wpm <= 240


def clear_voice_wpm(storage: Storage, user_id: str) -> None:
    storage.set_setting(user_id, VOICE_WPM_KEY, "")
    storage.set_setting(user_id, VOICE_WPM_ID_KEY, "")


def calibrate_voice_wpm(
    *,
    storage: Storage,
    user_id: str,
    voice_id: str | None,
    voice_name: str | None,
    elevenlabs: ElevenLabsMCPClient,
    model_id: str,
    speed: float,
    stability: float,
    similarity_boost: float,
    style: float,
    language: str,
) -> int:
    result = elevenlabs.text_to_speech(
        text=CALIBRATION_TEXT,
        voice_name=voice_name,
        voice_id=voice_id,
        model_id=model_id,
        speed=speed,
        stability=stability,
        similarity_boost=similarity_boost,
        style=style,
        language=language,
    )
    if not result.file_path:
        return DEFAULT_SPOKEN_WORDS_PER_MINUTE
    duration = probe_duration_seconds(Path(result.file_path))
    wpm = round(count_spoken_words(CALIBRATION_TEXT) / duration * 60)
    storage.set_setting(user_id, VOICE_WPM_KEY, str(wpm))
    storage.set_setting(user_id, VOICE_WPM_ID_KEY, voice_id or "")
    return wpm

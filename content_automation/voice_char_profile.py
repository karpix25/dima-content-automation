from __future__ import annotations

from pathlib import Path

from .elevenlabs_mcp import ElevenLabsMCPClient
from .elevenlabs_retry import text_to_speech_with_retry
from .storage import Storage
from .video_overlay import probe_duration_seconds


VOICE_CPS_KEY = "elevenlabs_voice_chars_per_second"
VOICE_CPS_ID_KEY = "elevenlabs_voice_chars_per_second_voice_id"
DEFAULT_CHARS_PER_SECOND = 13.0
CALIBRATION_CHAR_COUNT = 480


def calibration_text() -> str:
    base = (
        "Amazon operators protect profit by checking fees, refunds, packaging, and advertising before they scale. "
        "A clear margin model turns growth into cash instead of noise. "
    )
    repeated = (base * ((CALIBRATION_CHAR_COUNT // len(base)) + 2))[:CALIBRATION_CHAR_COUNT]
    return repeated


def calibrated_voice_chars_per_second(storage: Storage, user_id: str, voice_id: str | None) -> float:
    stored_voice_id = storage.get_setting(user_id, VOICE_CPS_ID_KEY)
    raw_cps = storage.get_setting(user_id, VOICE_CPS_KEY)
    if voice_id and stored_voice_id != voice_id:
        return DEFAULT_CHARS_PER_SECOND
    try:
        cps = float(raw_cps or "")
    except ValueError:
        return DEFAULT_CHARS_PER_SECOND
    return cps if 6.0 <= cps <= 28.0 else DEFAULT_CHARS_PER_SECOND


def has_voice_chars_profile(storage: Storage, user_id: str, voice_id: str | None) -> bool:
    stored_voice_id = storage.get_setting(user_id, VOICE_CPS_ID_KEY)
    raw_cps = storage.get_setting(user_id, VOICE_CPS_KEY)
    if voice_id and stored_voice_id != voice_id:
        return False
    try:
        cps = float(raw_cps or "")
    except ValueError:
        return False
    return 6.0 <= cps <= 28.0


def clear_voice_chars_profile(storage: Storage, user_id: str) -> None:
    storage.set_setting(user_id, VOICE_CPS_KEY, "")
    storage.set_setting(user_id, VOICE_CPS_ID_KEY, "")


def calibrate_voice_chars_per_second(
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
) -> float:
    text = calibration_text()
    result = text_to_speech_with_retry(
        elevenlabs,
        text=text,
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
        return DEFAULT_CHARS_PER_SECOND
    duration = max(0.1, probe_duration_seconds(Path(result.file_path)))
    cps = round(len(text) / duration, 2)
    storage.set_setting(user_id, VOICE_CPS_KEY, str(cps))
    storage.set_setting(user_id, VOICE_CPS_ID_KEY, voice_id or "")
    return cps

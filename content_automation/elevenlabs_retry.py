from __future__ import annotations

import logging
import time
from typing import Any, Protocol

from .elevenlabs_mcp import ElevenLabsAudioResult, ElevenLabsMCPError

logger = logging.getLogger(__name__)


class ElevenLabsTextToSpeech(Protocol):
    def text_to_speech(self, **kwargs: Any) -> ElevenLabsAudioResult:
        ...


def text_to_speech_with_retry(
    elevenlabs: ElevenLabsTextToSpeech,
    *,
    attempts: int = 2,
    delay_seconds: float = 1.5,
    **kwargs: Any,
) -> ElevenLabsAudioResult:
    safe_attempts = max(1, attempts)
    last_result: ElevenLabsAudioResult | None = None
    last_error: ElevenLabsMCPError | None = None
    for attempt in range(1, safe_attempts + 1):
        try:
            result = elevenlabs.text_to_speech(**kwargs)
            if result.file_path:
                return result
            last_result = result
            logger.warning("ElevenLabs returned no audio file; retry=%s/%s", attempt, safe_attempts)
        except ElevenLabsMCPError as exc:
            last_error = exc
            logger.warning("ElevenLabs text_to_speech failed; retry=%s/%s error=%s", attempt, safe_attempts, exc)
        if attempt < safe_attempts:
            time.sleep(delay_seconds * attempt)
    if last_result:
        return last_result
    if last_error:
        raise last_error
    raise ElevenLabsMCPError("ElevenLabs text_to_speech завершился без результата")

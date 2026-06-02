from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeepgramConfig:
    api_key: str | None
    api_base_url: str = "https://api.deepgram.com"
    model: str = "nova-2"
    language: str = "en"
    timeout_seconds: int = 240


@dataclass(frozen=True)
class TranscriptResult:
    raw: dict
    words: list[dict]


def transcribe_video_with_deepgram(
    *,
    video_path: Path,
    output_dir: Path,
    config: DeepgramConfig,
) -> TranscriptResult | None:
    if not config.api_key:
        logger.info("Deepgram transcription skipped: DEEPGRAM_API_KEY is not configured")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    audio_path = output_dir / f"{video_path.stem}.deepgram.mp3"
    _extract_audio(video_path, audio_path)
    response = _request_transcript(audio_path, config)
    words = extract_deepgram_words(response)
    if not words:
        logger.warning("Deepgram returned no word-level timings for %s", video_path)
        return TranscriptResult(raw=response, words=[])
    logger.info("Deepgram transcription completed for %s: %s word(s)", video_path, len(words))
    return TranscriptResult(raw=response, words=words)


def extract_deepgram_words(payload: dict) -> list[dict]:
    channels = payload.get("results", {}).get("channels", [])
    alternatives = channels[0].get("alternatives", []) if channels else []
    raw_words = alternatives[0].get("words", []) if alternatives else []
    words: list[dict] = []
    for item in raw_words:
        word = str(item.get("punctuated_word") or item.get("word") or "").strip()
        start = _float_or_none(item.get("start"))
        end = _float_or_none(item.get("end"))
        if not word or start is None or end is None or end <= start:
            continue
        words.append(
            {
                "word": str(item.get("word") or word).strip(),
                "punctuated_word": word,
                "text": word,
                "start": round(start, 3),
                "end": round(end, 3),
            }
        )
    return words


def _extract_audio(video_path: Path, audio_path: Path) -> None:
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-acodec",
            "libmp3lame",
            "-ar",
            "44100",
            "-ac",
            "1",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        output = "\n".join(part for part in (result.stdout, result.stderr) if part)
        raise RuntimeError(f"ffmpeg audio extraction failed: {output[-2000:]}")


def _request_transcript(audio_path: Path, config: DeepgramConfig) -> dict:
    url = f"{config.api_base_url.rstrip('/')}/v1/listen"
    params = {
        "model": config.model,
        "language": config.language,
        "smart_format": "true",
        "punctuate": "true",
        "words": "true",
    }
    headers = {
        "Authorization": f"Token {config.api_key}",
        "Content-Type": "audio/mpeg",
    }
    with audio_path.open("rb") as audio_file:
        response = httpx.post(
            url,
            params=params,
            headers=headers,
            content=audio_file.read(),
            timeout=config.timeout_seconds,
        )
    response.raise_for_status()
    return response.json()


def _float_or_none(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result

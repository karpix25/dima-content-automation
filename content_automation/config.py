from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    notebooklm_cli_command: str
    notebooklm_mcp_command: str
    default_notebook_id: str | None
    elevenlabs_api_key: str | None
    elevenlabs_mcp_command: str | None
    elevenlabs_voice_id: str | None
    elevenlabs_voice_name: str
    elevenlabs_model_id: str
    elevenlabs_speed: float
    elevenlabs_stability: float
    elevenlabs_similarity_boost: float
    elevenlabs_style: float
    elevenlabs_language: str
    elevenlabs_output_directory: Path
    video_output_directory: Path
    heygen_api_key: str | None
    heygen_api_base_url: str
    heygen_upload_base_url: str
    heygen_aspect_ratio: str
    heygen_resolution: str
    heygen_output_format: str
    heygen_video_poll_seconds: int
    heygen_video_timeout_seconds: int
    data_dir: Path


def get_float_env(name: str, default: float) -> float:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def get_int_env(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def load_settings() -> Settings:
    load_dotenv()
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required. Add it to .env.")

    data_dir = Path(os.getenv("DATA_DIR", ".data")).expanduser()
    data_dir.mkdir(parents=True, exist_ok=True)
    elevenlabs_output_directory = Path(os.getenv("ELEVENLABS_OUTPUT_DIRECTORY", "outputs/elevenlabs")).expanduser()
    elevenlabs_output_directory.mkdir(parents=True, exist_ok=True)
    video_output_directory = Path(os.getenv("VIDEO_OUTPUT_DIRECTORY", "outputs/videos")).expanduser()
    video_output_directory.mkdir(parents=True, exist_ok=True)

    return Settings(
        telegram_bot_token=token,
        notebooklm_cli_command=(os.getenv("NOTEBOOKLM_CLI_COMMAND") or "notebooklm").strip(),
        notebooklm_mcp_command=(os.getenv("NOTEBOOKLM_MCP_COMMAND") or "npx notebooklm-mcp@latest").strip(),
        default_notebook_id=(os.getenv("DEFAULT_NOTEBOOK_ID") or "").strip() or None,
        elevenlabs_api_key=(os.getenv("ELEVENLABS_API_KEY") or "").strip() or None,
        elevenlabs_mcp_command=(os.getenv("ELEVENLABS_MCP_SERVER_COMMAND") or "").strip() or None,
        elevenlabs_voice_id=(os.getenv("ELEVENLABS_VOICE_ID") or "").strip() or None,
        elevenlabs_voice_name=(os.getenv("ELEVENLABS_VOICE_NAME") or "Dima Kubrak 1").strip(),
        elevenlabs_model_id=(os.getenv("ELEVENLABS_MODEL_ID") or "eleven_multilingual_v2").strip(),
        elevenlabs_speed=get_float_env("ELEVENLABS_SPEED", 1.05),
        elevenlabs_stability=get_float_env("ELEVENLABS_STABILITY", 0.9),
        elevenlabs_similarity_boost=get_float_env("ELEVENLABS_SIMILARITY_BOOST", 0.97),
        elevenlabs_style=get_float_env("ELEVENLABS_STYLE", 0.0),
        elevenlabs_language=(os.getenv("ELEVENLABS_LANGUAGE") or "en").strip(),
        elevenlabs_output_directory=elevenlabs_output_directory,
        video_output_directory=video_output_directory,
        heygen_api_key=(os.getenv("HEYGEN_API_KEY") or "").strip() or None,
        heygen_api_base_url=(os.getenv("HEYGEN_API_BASE_URL") or "https://api.heygen.com").strip().rstrip("/"),
        heygen_upload_base_url=(os.getenv("HEYGEN_UPLOAD_BASE_URL") or "https://upload.heygen.com").strip().rstrip("/"),
        heygen_aspect_ratio=(os.getenv("HEYGEN_ASPECT_RATIO") or "9:16").strip(),
        heygen_resolution=(os.getenv("HEYGEN_RESOLUTION") or "720p").strip(),
        heygen_output_format=(os.getenv("HEYGEN_OUTPUT_FORMAT") or "mp4").strip(),
        heygen_video_poll_seconds=get_int_env("HEYGEN_VIDEO_POLL_SECONDS", 15),
        heygen_video_timeout_seconds=get_int_env("HEYGEN_VIDEO_TIMEOUT_SECONDS", 900),
        data_dir=data_dir,
    )

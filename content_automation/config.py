from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    notebooklm_cli_command: str
    notebooklm_backend: str
    notebooklm_mcp_command: str
    notebooklm_mcp_timeout_seconds: int
    notebooklm_py_storage_path: Path | None
    notebooklm_short_batch_size: int
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
    video_keep_days: int
    heygen_api_key: str | None
    heygen_api_base_url: str
    heygen_upload_base_url: str
    heygen_private_avatars_only: bool
    heygen_aspect_ratio: str
    heygen_resolution: str
    heygen_output_format: str
    heygen_video_poll_seconds: int
    heygen_video_timeout_seconds: int
    data_dir: Path
    miniapp_url: str | None
    web_host: str
    web_port: int
    turan_api_base_url: str | None
    turan_api_telegram_id: str | None
    post_heygen_visuals_enabled: bool
    post_heygen_cover_seconds: float
    post_heygen_broll_count: int
    post_heygen_broll_seconds: float
    kie_api_key: str | None
    kie_base_url: str
    kie_image_model: str
    kie_image_aspect_ratio: str
    kie_image_resolution: str
    kie_poll_timeout_seconds: float
    kie_poll_interval_seconds: float
    kie_create_task_max_attempts: int
    kie_create_task_retry_delay_seconds: float
    montage_renderer: str
    hyperframes_project_dir: Path | None
    remotion_project_dir: Path | None
    montage_render_timeout_seconds: int
    montage_max_scenes: int


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


def get_bool_env(name: str, default: bool) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "y", "on"}


def normalize_notebooklm_mcp_command(value: str | None) -> str:
    command = (value or "").strip() or "npx --yes notebooklm-mcp@latest"
    if command == "npx notebooklm-mcp@latest":
        return "npx --yes notebooklm-mcp@latest"
    return command


def normalize_notebooklm_backend(value: str | None) -> str:
    backend = (value or "mcp").strip().lower()
    return backend if backend in {"mcp", "py"} else "mcp"


def get_optional_path_env(name: str) -> Path | None:
    raw = (os.getenv(name) or "").strip()
    return Path(raw).expanduser() if raw else None


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
        notebooklm_backend=normalize_notebooklm_backend(os.getenv("NOTEBOOKLM_BACKEND")),
        notebooklm_mcp_command=normalize_notebooklm_mcp_command(os.getenv("NOTEBOOKLM_MCP_COMMAND")),
        notebooklm_mcp_timeout_seconds=get_int_env("NOTEBOOKLM_MCP_TIMEOUT_SECONDS", 900),
        notebooklm_py_storage_path=get_optional_path_env("NOTEBOOKLM_PY_STORAGE_PATH"),
        notebooklm_short_batch_size=max(1, get_int_env("NOTEBOOKLM_SHORT_BATCH_SIZE", 1)),
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
        video_keep_days=get_int_env("VIDEO_KEEP_DAYS", 14),
        heygen_api_key=(os.getenv("HEYGEN_API_KEY") or "").strip() or None,
        heygen_api_base_url=(os.getenv("HEYGEN_API_BASE_URL") or "https://api.heygen.com").strip().rstrip("/"),
        heygen_upload_base_url=(os.getenv("HEYGEN_UPLOAD_BASE_URL") or "https://upload.heygen.com").strip().rstrip("/"),
        heygen_private_avatars_only=get_bool_env("HEYGEN_PRIVATE_AVATARS_ONLY", True),
        heygen_aspect_ratio=(os.getenv("HEYGEN_ASPECT_RATIO") or "9:16").strip(),
        heygen_resolution=(os.getenv("HEYGEN_RESOLUTION") or "720p").strip(),
        heygen_output_format=(os.getenv("HEYGEN_OUTPUT_FORMAT") or "mp4").strip(),
        heygen_video_poll_seconds=get_int_env("HEYGEN_VIDEO_POLL_SECONDS", 15),
        heygen_video_timeout_seconds=get_int_env("HEYGEN_VIDEO_TIMEOUT_SECONDS", 900),
        data_dir=data_dir,
        miniapp_url=(os.getenv("MINIAPP_URL") or os.getenv("WEBAPP_URL") or "").strip() or None,
        web_host=(os.getenv("WEB_HOST") or "0.0.0.0").strip(),
        web_port=get_int_env("WEB_PORT", 8000),
        turan_api_base_url=(os.getenv("TURAN_API_BASE_URL") or os.getenv("TURAN_API_URL") or "").strip().rstrip("/") or None,
        turan_api_telegram_id=(os.getenv("TURAN_API_TELEGRAM_ID") or "").strip() or None,
        post_heygen_visuals_enabled=get_bool_env("POST_HEYGEN_VISUALS_ENABLED", True),
        post_heygen_cover_seconds=get_float_env("POST_HEYGEN_COVER_SECONDS", 0.10),
        post_heygen_broll_count=max(0, get_int_env("POST_HEYGEN_BROLL_COUNT", 3)),
        post_heygen_broll_seconds=max(0.2, get_float_env("POST_HEYGEN_BROLL_SECONDS", 1.2)),
        kie_api_key=(os.getenv("KIE_API_KEY") or "").strip() or None,
        kie_base_url=(os.getenv("KIE_BASE_URL") or "https://api.kie.ai").strip().rstrip("/"),
        kie_image_model=(os.getenv("KIE_IMAGE_MODEL") or "gpt-image-1").strip(),
        kie_image_aspect_ratio=(os.getenv("KIE_IMAGE_ASPECT_RATIO") or "9:16").strip(),
        kie_image_resolution=(os.getenv("KIE_IMAGE_RESOLUTION") or "1K").strip(),
        kie_poll_timeout_seconds=get_float_env("KIE_POLL_TIMEOUT_SECONDS", 300),
        kie_poll_interval_seconds=get_float_env("KIE_POLL_INTERVAL_SECONDS", 3),
        kie_create_task_max_attempts=max(1, get_int_env("KIE_CREATE_TASK_MAX_ATTEMPTS", 4)),
        kie_create_task_retry_delay_seconds=max(0.5, get_float_env("KIE_CREATE_TASK_RETRY_DELAY_SECONDS", 3)),
        montage_renderer=(os.getenv("MONTAGE_RENDERER") or "auto").strip().lower(),
        hyperframes_project_dir=get_optional_path_env("HYPERFRAMES_PROJECT_DIR"),
        remotion_project_dir=get_optional_path_env("REMOTION_PROJECT_DIR"),
        montage_render_timeout_seconds=max(60, get_int_env("MONTAGE_RENDER_TIMEOUT_SECONDS", 3600)),
        montage_max_scenes=max(1, get_int_env("MONTAGE_MAX_SCENES", 8)),
    )

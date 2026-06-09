from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import httpx


class VideoOverlayError(RuntimeError):
    pass


@dataclass(frozen=True)
class OverlayResult:
    input_path: Path
    output_path: Path
    duration_seconds: float
    start_seconds: float


async def download_video(url: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=300, follow_redirects=True) as client:
        async with client.stream("GET", url) as response:
            if response.status_code >= 400:
                raise VideoOverlayError(f"Не удалось скачать видео: HTTP {response.status_code}")
            with output_path.open("wb") as file:
                async for chunk in response.aiter_bytes():
                    file.write(chunk)
    return output_path


def probe_duration_seconds(video_path: Path) -> float:
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(video_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise VideoOverlayError(f"ffprobe error: {proc.stderr[-1000:]}")
    try:
        payload = json.loads(proc.stdout)
        duration = float(payload["format"]["duration"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise VideoOverlayError(f"Не удалось определить длительность видео: {proc.stdout}") from exc
    if duration <= 0:
        raise VideoOverlayError("Длительность видео равна нулю")
    return duration


def probe_video_size(video_path: Path) -> tuple[int, int]:
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,sample_aspect_ratio,display_aspect_ratio",
            "-of",
            "json",
            str(video_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise VideoOverlayError(f"ffprobe size error: {proc.stderr[-1000:]}")
    try:
        stream = json.loads(proc.stdout)["streams"][0]
        width = int(stream["width"])
        height = int(stream["height"])
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise VideoOverlayError(f"Не удалось определить размер видео: {proc.stdout}") from exc
    if width <= 0 or height <= 0:
        raise VideoOverlayError(f"Некорректный размер видео: {width}x{height}")
    return _display_size(width, height, stream)


def _display_size(width: int, height: int, stream: dict) -> tuple[int, int]:
    ratio = _ratio_value(stream.get("display_aspect_ratio"))
    if ratio is None:
        sar = _ratio_value(stream.get("sample_aspect_ratio"))
        ratio = width / height * sar if sar else width / height
    if ratio > 1:
        return (round(height * ratio), height)
    if ratio < 1:
        return (width, round(width / ratio))
    return width, height


def _ratio_value(value: object) -> float | None:
    if not isinstance(value, str) or not value or value == "0:1":
        return None
    if ":" in value:
        left, right = value.split(":", 1)
        try:
            numerator = float(left)
            denominator = float(right)
        except ValueError:
            return None
        return numerator / denominator if denominator else None
    try:
        return float(value)
    except ValueError:
        return None


def apply_overlay(
    *,
    video_path: Path,
    overlay_path: Path,
    output_path: Path,
    start_percent: int,
) -> OverlayResult:
    if not video_path.exists():
        raise VideoOverlayError(f"Видео не найдено: {video_path}")
    if not overlay_path.exists():
        raise VideoOverlayError(f"Плашка не найдена: {overlay_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    duration = probe_duration_seconds(video_path)
    clamped_percent = max(0, min(100, start_percent))
    start_seconds = duration * clamped_percent / 100
    filter_complex = (
        "[1:v]format=rgba[ovraw];"
        "[ovraw][0:v]scale2ref="
        "w='min(iw,main_w)':h='min(ih,main_h)':force_original_aspect_ratio=decrease[ov][base];"
        f"[base][ov]overlay=(W-w)/2:(H-h)/2:enable='gte(t,{start_seconds:.3f})'[v]"
    )
    proc = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(overlay_path),
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "copy",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise VideoOverlayError(f"ffmpeg overlay error: {proc.stderr[-2000:]}")
    return OverlayResult(
        input_path=video_path,
        output_path=output_path,
        duration_seconds=duration,
        start_seconds=start_seconds,
    )


def cleanup_old_videos(directory: Path, *, keep_days: int) -> int:
    if keep_days <= 0 or not directory.exists():
        return 0
    cutoff = time.time() - keep_days * 24 * 60 * 60
    removed = 0
    for path in directory.glob("*.mp4"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        except OSError:
            continue
    return removed


def remove_file(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise VideoOverlayError(f"Не удалось удалить временный файл {path}: {exc}") from exc

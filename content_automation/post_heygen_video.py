from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .video_overlay import VideoOverlayError, probe_duration_seconds
from .visual_assets import VisualAssetSet


@dataclass(frozen=True)
class PostHeyGenResult:
    output_path: Path
    cover_seconds: float
    broll_starts: list[float]


def apply_post_heygen_visuals(
    *,
    video_path: Path,
    assets: VisualAssetSet,
    output_path: Path,
    cover_seconds: float,
    broll_seconds: float,
    target_size: tuple[int, int] = (1080, 1920),
) -> PostHeyGenResult:
    if not video_path.exists():
        raise VideoOverlayError(f"Видео не найдено: {video_path}")
    if not assets.cover_path.exists():
        raise VideoOverlayError(f"Cover не найден: {assets.cover_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    duration = probe_duration_seconds(video_path)
    starts = _broll_starts(duration, len(assets.broll_paths), broll_seconds)
    inputs = ["ffmpeg", "-y", "-i", str(video_path), "-loop", "1", "-i", str(assets.cover_path)]
    for path in assets.broll_paths:
        if path.exists():
            inputs.extend(["-loop", "1", "-i", str(path)])

    filter_parts = [_scale_filter(1, "cover", target_size), f"[0:v][cover]overlay=0:0:enable='lt(t,{cover_seconds:.3f})'[v1]"]
    current = "v1"
    for index, start in enumerate(starts, start=2):
        label = f"b{index}"
        next_label = f"v{index}"
        filter_parts.append(_scale_filter(index, label, target_size))
        filter_parts.append(
            f"[{current}][{label}]overlay=0:0:enable='between(t,{start:.3f},{start + broll_seconds:.3f})'[{next_label}]"
        )
        current = next_label

    cmd = [
        *inputs,
        "-filter_complex",
        ";".join(filter_parts),
        "-map",
        f"[{current}]",
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
        "-shortest",
        str(output_path),
    ]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise VideoOverlayError(f"ffmpeg post-HeyGen visuals error: {proc.stderr[-2000:]}")
    return PostHeyGenResult(output_path=output_path, cover_seconds=cover_seconds, broll_starts=starts)


def apply_cover_frame(
    *,
    video_path: Path,
    cover_path: Path,
    output_path: Path,
    cover_seconds: float,
    target_size: tuple[int, int] = (1080, 1920),
) -> Path:
    if not video_path.exists():
        raise VideoOverlayError(f"Видео не найдено: {video_path}")
    if not cover_path.exists():
        raise VideoOverlayError(f"Cover не найден: {cover_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-loop",
        "1",
        "-i",
        str(cover_path),
        "-filter_complex",
        f"{_scale_filter(1, 'cover', target_size)};[0:v][cover]overlay=0:0:enable='lt(t,{cover_seconds:.3f})'[v]",
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
        "-shortest",
        str(output_path),
    ]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise VideoOverlayError(f"ffmpeg cover frame error: {proc.stderr[-2000:]}")
    return output_path


def _scale_filter(input_index: int, label: str, target_size: tuple[int, int]) -> str:
    width, height = target_size
    return (
        f"[{input_index}:v]scale=iw*sar:ih,setsar=1,"
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},format=rgba[{label}]"
    )


def _broll_starts(duration: float, count: int, broll_seconds: float) -> list[float]:
    if count <= 0 or duration <= broll_seconds + 2:
        return []
    safe_start = max(1.5, duration * 0.18)
    safe_end = max(safe_start, duration - broll_seconds - 1.0)
    if count == 1:
        return [round((safe_start + safe_end) / 2, 3)]
    step = (safe_end - safe_start) / (count - 1)
    return [round(safe_start + step * index, 3) for index in range(count)]

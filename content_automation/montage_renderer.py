from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .montage_plan import build_montage_plan
from .storage import ScriptRecord
from .video_overlay import VideoOverlayError, probe_duration_seconds


@dataclass(frozen=True)
class MontageRendererConfig:
    hyperframes_project_dir: Path | None
    remotion_project_dir: Path | None
    renderer: str
    timeout_seconds: int
    max_scenes: int


def render_montage_if_configured(
    *,
    record: ScriptRecord,
    video_path: Path,
    output_dir: Path,
    config: MontageRendererConfig,
) -> Path | None:
    renderer = (config.renderer or "auto").strip().lower()
    candidates: list[tuple[str, Path | None]] = []
    if renderer in {"auto", "hyperframes"}:
        candidates.append(("hyperframes", config.hyperframes_project_dir))
    if renderer in {"auto", "remotion"}:
        candidates.append(("remotion", config.remotion_project_dir))

    for name, project_dir in candidates:
        if name == "hyperframes" and record.format != "youtube":
            continue
        if project_dir and (project_dir / "package.json").exists():
            rendered = _render(
                name=name,
                project_dir=project_dir,
                record=record,
                video_path=video_path,
                output_dir=output_dir,
                timeout_seconds=config.timeout_seconds,
                max_scenes=config.max_scenes,
            )
            if rendered:
                return rendered
    return None


def _render(
    *,
    name: str,
    project_dir: Path,
    record: ScriptRecord,
    video_path: Path,
    output_dir: Path,
    timeout_seconds: int,
    max_scenes: int,
) -> Path | None:
    output_dir.mkdir(parents=True, exist_ok=True)
    duration = probe_duration_seconds(video_path)
    plan = build_montage_plan(record, duration_seconds=duration, max_scenes=max_scenes)
    scene_plan_path = output_dir / f"scene-plan_{record.id}.json"
    word_cues_path = output_dir / f"scene-word-cues_{record.id}.json"
    scene_plan_path.write_text(json.dumps(plan.scenes, ensure_ascii=False, indent=2), encoding="utf-8")
    word_cues_path.write_text(json.dumps(plan.word_cues, ensure_ascii=False, indent=2), encoding="utf-8")
    output_path = output_dir / f"{name}_{record.id}.mp4"
    cmd = _command(
        name,
        record=record,
        video_path=video_path,
        scene_plan_path=scene_plan_path,
        word_cues_path=word_cues_path,
        output_path=output_path,
    )
    try:
        result = subprocess.run(
            cmd,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except Exception as exc:
        raise VideoOverlayError(f"{name} render failed to start: {exc}") from exc
    if result.returncode != 0:
        raise VideoOverlayError(f"{name} render failed: {(result.stderr or result.stdout)[-2000:]}")
    return output_path if output_path.exists() else None


def _command(
    name: str,
    *,
    record: ScriptRecord,
    video_path: Path,
    scene_plan_path: Path,
    word_cues_path: Path,
    output_path: Path,
) -> list[str]:
    if name == "hyperframes":
        return [
            "npm",
            "run",
            "render:auto",
            "--",
            "--video",
            str(video_path),
            "--scene-plan",
            str(scene_plan_path),
            "--word-cues",
            str(word_cues_path),
            "--out",
            str(output_path),
            "--layout",
            "horizontal_youtube" if record.format == "youtube" else "horizontal_simple",
        ]
    return [
        "npm",
        "run",
        "render:auto",
        "--",
        "--video",
        str(video_path),
        "--scene-plan",
        str(scene_plan_path),
        "--word-cues",
        str(word_cues_path),
        "--out",
        str(output_path),
    ]

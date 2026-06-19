from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def cleanup_delivered_video_files(
    *,
    root: Path,
    final_path: Path,
    record_id: int,
    enabled: bool,
) -> list[Path]:
    if not enabled:
        return []
    root = root.resolve()
    candidates = _candidate_video_paths(root=root, final_path=final_path, record_id=record_id)
    removed: list[Path] = []
    for path in candidates:
        if _remove_video_file(path, root=root):
            removed.append(path)
    if removed:
        logger.info("Deleted delivered video file(s) after Telegram send: %s", [str(path) for path in removed])
    return removed


def _candidate_video_paths(*, root: Path, final_path: Path, record_id: int) -> list[Path]:
    paths: dict[Path, None] = {}
    _add(paths, final_path)
    for pattern in (
        f"heygen_{record_id}.mp4",
        f"existing_heygen_{record_id}_*.mp4",
        f"miniapp_heygen_{record_id}_*.mp4",
        f"visual_{record_id}.mp4",
        f"final_{record_id}.mp4",
        f"miniapp_visual_{record_id}_*.mp4",
        f"miniapp_overlay_{record_id}_*.mp4",
        f"hyperframes_{record_id}_cover.mp4",
    ):
        for path in root.glob(pattern):
            _add(paths, path)
    for folder in (root / "montage" / str(record_id), root / "miniapp_montage" / str(record_id)):
        if folder.exists():
            for path in folder.glob("*.mp4"):
                _add(paths, path)
    infographic = root / "infographic_reels" / f"gold_card_{record_id}.mp4"
    _add(paths, infographic)
    return list(paths.keys())


def _add(paths: dict[Path, None], path: Path) -> None:
    paths[path] = None


def _remove_video_file(path: Path, *, root: Path) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return False
    if not _is_relative_to(resolved, root) or resolved.suffix.lower() != ".mp4":
        logger.warning("Skipping delivered video cleanup outside output root: %s", resolved)
        return False
    try:
        resolved.unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError:
        logger.exception("Failed to delete delivered video file: %s", resolved)
        return False


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False

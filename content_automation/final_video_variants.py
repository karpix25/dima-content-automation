from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .settings_service import get_overlay_path, get_overlay_start_percent
from .storage import Storage
from .video_overlay import apply_overlay


PLATFORM_OVERLAY_KEYS = {
    "youtube": "youtube",
    "shorts": "shorts",
    "reels": "reels",
}


@dataclass(frozen=True)
class FinalVideoVariant:
    platform: str
    label: str
    path: Path
    overlay_applied: bool


def build_final_video_variants(
    *,
    storage: Storage,
    user_id: str,
    source_path: Path,
    output_dir: Path,
    output_stem: str,
    platforms: tuple[str, ...] = ("youtube", "shorts", "reels"),
) -> list[FinalVideoVariant]:
    variants: list[FinalVideoVariant] = []
    for platform in platforms:
        overlay_key = PLATFORM_OVERLAY_KEYS.get(platform)
        if not overlay_key:
            continue
        overlay_path = get_overlay_path(storage, user_id, overlay_key)
        if not overlay_path or not overlay_path.exists():
            continue
        result = apply_overlay(
            video_path=source_path,
            overlay_path=overlay_path,
            output_path=output_dir / f"{output_stem}_{platform}.mp4",
            start_percent=get_overlay_start_percent(storage, user_id, overlay_key),
        )
        variants.append(
            FinalVideoVariant(
                platform=platform,
                label=platform_label(platform),
                path=result.output_path,
                overlay_applied=True,
            )
        )
    if variants:
        return variants
    return [
        FinalVideoVariant(
            platform="source",
            label="без плашки",
            path=source_path,
            overlay_applied=False,
        )
    ]


def platform_label(platform: str) -> str:
    if platform == "youtube":
        return "YouTube"
    if platform == "shorts":
        return "Shorts"
    if platform == "reels":
        return "Reels"
    return platform

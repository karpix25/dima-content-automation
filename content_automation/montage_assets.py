from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path

from .kie_image import KieImageClient, KieImageError

logger = logging.getLogger(__name__)


def prepare_vertical_montage_assets(
    *,
    project_dir: Path,
    scenes: list[dict],
    kie_client: KieImageClient | None,
) -> None:
    required = [(index, scene) for index, scene in enumerate(scenes) if _needs_image(scene)]
    if not required:
        return
    if not kie_client or not kie_client.is_configured():
        logger.warning("Vertical montage KIE image generation skipped: KIE_API_KEY is not configured")
        return
    montage_kie = KieImageClient(replace(kie_client.config, aspect_ratio="1:1", resolution="1K"))
    output_dir = project_dir / "assets" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    for index, scene in required:
        path = output_dir / _generated_image_file(index)
        if path.exists():
            continue
        prompt = str(scene.get("imagePrompt") or "").strip()
        if not prompt:
            logger.warning("Vertical montage scene has no image prompt: index=%s", index)
            continue
        try:
            logger.info("Generating vertical montage KIE image: scene=%s path=%s", index + 1, path)
            montage_kie.generate_image(prompt=prompt, output_path=path)
        except KieImageError:
            logger.exception("Vertical montage KIE image failed: scene=%s", index + 1)


def _needs_image(scene: dict) -> bool:
    return bool(str(scene.get("title") or scene.get("chapterTitle") or "").strip())


def _generated_image_file(index: int) -> str:
    return f"youtube-scene-{index + 1:02d}.png"

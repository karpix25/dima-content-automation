from __future__ import annotations

import logging
import time
from dataclasses import replace
from pathlib import Path

from .kie_image import KieImageClient, KieImageError

logger = logging.getLogger(__name__)

_GENERATE_ATTEMPTS = 3
_GENERATE_RETRY_DELAY_SECONDS = 4


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
    failed: list[str] = []
    for index, scene in required:
        path = output_dir / _generated_image_file(index)
        if path.exists():
            continue
        prompt = str(scene.get("imagePrompt") or "").strip()
        if not prompt:
            logger.warning("Vertical montage scene has no image prompt: index=%s", index)
            failed.append(path.name)
            continue
        if not _generate_image_with_retries(montage_kie, prompt=prompt, path=path, scene_number=index + 1):
            failed.append(path.name)
    if failed:
        raise KieImageError(f"Vertical montage KIE image generation failed for: {', '.join(failed)}")


def _generate_image_with_retries(
    client: KieImageClient,
    *,
    prompt: str,
    path: Path,
    scene_number: int,
) -> bool:
    for attempt in range(1, _GENERATE_ATTEMPTS + 1):
        try:
            logger.info(
                "Generating vertical montage KIE image: scene=%s attempt=%s/%s path=%s",
                scene_number,
                attempt,
                _GENERATE_ATTEMPTS,
                path,
            )
            client.generate_image(prompt=prompt, output_path=path)
            return True
        except KieImageError:
            if attempt >= _GENERATE_ATTEMPTS:
                logger.exception("Vertical montage KIE image failed: scene=%s", scene_number)
                return False
            logger.warning(
                "Vertical montage KIE image attempt failed; retrying: scene=%s attempt=%s/%s",
                scene_number,
                attempt,
                _GENERATE_ATTEMPTS,
                exc_info=True,
            )
            time.sleep(_GENERATE_RETRY_DELAY_SECONDS)
    return False


def _needs_image(scene: dict) -> bool:
    return bool(str(scene.get("title") or scene.get("chapterTitle") or "").strip())


def _generated_image_file(index: int) -> str:
    return f"youtube-scene-{index + 1:02d}.png"

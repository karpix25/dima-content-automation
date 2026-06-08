from __future__ import annotations

import logging
import time
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

from PIL import Image, ImageDraw

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
    output_dir = project_dir / "assets" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    if not kie_client or not kie_client.is_configured():
        logger.warning("Vertical montage KIE image generation skipped: KIE_API_KEY is not configured")
        _write_fallback_images(required, output_dir=output_dir, reason="missing KIE_API_KEY")
        return
    montage_kie = KieImageClient(replace(kie_client.config, aspect_ratio="1:1", resolution="1K"))
    for index, scene in required:
        path = output_dir / _generated_image_file(index)
        if path.exists():
            continue
        prompt = str(scene.get("imagePrompt") or "").strip()
        if not prompt:
            logger.warning("Vertical montage scene has no image prompt: index=%s", index)
            _write_fallback_image(path=path, scene=scene, reason="missing image prompt")
            continue
        if not _generate_image_with_retries(montage_kie, prompt=prompt, path=path, scene_number=index + 1):
            _write_fallback_image(path=path, scene=scene, reason="KIE generation failed")


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


def _write_fallback_images(
    required: list[tuple[int, dict]],
    *,
    output_dir: Path,
    reason: str,
) -> None:
    for index, scene in required:
        path = output_dir / _generated_image_file(index)
        if not path.exists():
            _write_fallback_image(path=path, scene=scene, reason=reason)


def _write_fallback_image(*, path: Path, scene: dict, reason: str) -> None:
    logger.warning("Writing fallback vertical montage image: path=%s reason=%s", path, reason)
    path.parent.mkdir(parents=True, exist_ok=True)
    color_seed = str(scene.get("title") or scene.get("chapterTitle") or path.stem)
    accent = _scene_accent(color_seed)
    image = Image.new("RGB", (1024, 1024), _lighten(accent, 0.78))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((72, 72, 952, 952), radius=56, fill=(248, 248, 244), outline=_lighten(accent, 0.55), width=8)
    draw.ellipse((112, 118, 240, 246), fill=accent)
    for offset, width in ((308, 560), (388, 700), (468, 620), (548, 760), (628, 520), (708, 680)):
        draw.rounded_rectangle((132, offset, 132 + width, offset + 34), radius=17, fill=_lighten(accent, 0.35))
    draw.rounded_rectangle((132, 820, 620, 870), radius=25, fill=accent)
    image.save(path, format="PNG")


def _scene_accent(value: str) -> tuple[int, int, int]:
    digest = sha256(value.encode("utf-8")).digest()
    return (72 + digest[0] % 104, 72 + digest[1] % 104, 72 + digest[2] % 104)


def _lighten(color: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(int(channel + (255 - channel) * amount) for channel in color)

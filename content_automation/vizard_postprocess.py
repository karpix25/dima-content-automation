from __future__ import annotations

from pathlib import Path

from .config import Settings
from .kie_image import KieImageClient
from .media_assets import MediaAssetStore
from .post_heygen_video import apply_cover_frame
from .reference_paths import thumbnail_face_reference_paths, thumbnail_style_reference_paths
from .storage import ScriptRecord, Storage
from .video_geometry import video_size_for_format
from .visual_assets import generate_post_heygen_assets
from .vizard_models import VizardClip


def apply_vizard_cover_frame(
    *,
    storage: Storage,
    settings: Settings,
    asset_store: MediaAssetStore,
    kie_client: KieImageClient | None,
    user_id: str,
    clip: VizardClip,
    clip_path: Path,
    output_dir: Path,
    index: int,
    format: str = "short",
) -> Path:
    record = vizard_clip_to_record(user_id=user_id, clip=clip, index=index, format=format)
    asset_dir = output_dir / "covers" / f"clip_{index:02d}"
    target = "horizontal" if format == "youtube" else "vertical"
    assets = generate_post_heygen_assets(
        record=record,
        output_dir=asset_dir,
        broll_count=0,
        kie_client=kie_client,
        face_reference_paths=thumbnail_face_reference_paths(
            storage=storage,
            settings=settings,
            user_id=user_id,
            target=target,
        ),
        style_reference_paths=thumbnail_style_reference_paths(
            asset_store=asset_store,
            user_id=user_id,
            target=target,
        ),
    )
    return apply_cover_frame(
        video_path=clip_path,
        cover_path=assets.cover_path,
        output_path=output_dir / f"{clip_path.stem}_cover.mp4",
        cover_seconds=settings.post_heygen_cover_seconds,
        target_size=video_size_for_format(format),
    )


def vizard_clip_to_record(*, user_id: str, clip: VizardClip, index: int, format: str = "short") -> ScriptRecord:
    title = _clean(clip.title) or f"Vizard clip {index}"
    transcript = _clean(clip.transcript, limit=1200)
    viral_reason = _clean(clip.viral_reason, limit=400)
    return ScriptRecord(
        id=900_000 + index,
        user_id=user_id,
        format=format,
        status="approved",
        title=title,
        angle=viral_reason or "A high-signal clip selected by Vizard.",
        hook=title,
        trigger=viral_reason or transcript[:220],
        voiceover=transcript or title,
        cta="",
        why_it_works=viral_reason,
        source_basis=f"Vizard clip {clip.video_id or index}",
        raw={
            "source": "vizard",
            "clip_id": clip.video_id,
            "clip_editor_url": clip.clip_editor_url,
            "viral_score": clip.viral_score,
        },
    )


def _clean(value: str | None, *, limit: int = 240) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."

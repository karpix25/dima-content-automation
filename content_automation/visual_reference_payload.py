from __future__ import annotations

from .media_assets import MediaAsset, MediaAssetStore
from .settings_service import get_user_settings
from .storage import Storage
from .config import Settings


def build_visual_reference_payload(
    storage: Storage,
    asset_store: MediaAssetStore,
    settings: Settings,
    user_id: str,
    format_key: str,
) -> dict[str, object]:
    state = get_user_settings(storage, settings, user_id)
    target = "horizontal" if format_key == "avatar_horizontal" else "vertical"
    avatar_id = state.heygen_avatar_id if target == "horizontal" else state.heygen_vertical_avatar_id
    avatar_name = state.heygen_avatar_name if target == "horizontal" else state.heygen_vertical_avatar_name
    return {
        "target": target,
        "heygen_avatar": {
            "id": avatar_id,
            "name": avatar_name,
        },
        "thumbnail": {
            "face_path": state.thumbnail_face_path if target == "horizontal" else state.vertical_thumbnail_face_path,
            "style_references": [
                asset_payload(item)
                for item in asset_store.list_assets(user_id, "thumbnail_reference")
                if item.target in {target, "both"}
            ],
            "reference_rule": "Use uploaded references for visual style only. Do not copy their text, layout, or identity.",
        },
        "avatar_inserts": {
            "start_percent": state.avatar_insert_start_percent,
            "end_percent": state.avatar_insert_end_percent,
            "clips_count": state.avatar_insert_clips_count,
            "clips": [asset_payload(item) for item in asset_store.list_assets(user_id, "avatar_insert")],
        },
        "instagram_post_5s": {
            "cta_text": state.instagram_post_5s_cta_text,
            "overlay_path": state.instagram_post_5s_overlay_path,
            "audio_tracks": [asset_payload(item) for item in asset_store.list_assets(user_id, "instagram_post_5s_audio")],
        },
        "youtube_description_template": state.youtube_description_template,
    }


def asset_payload(asset: MediaAsset) -> dict[str, object]:
    return {
        "id": asset.id,
        "file_path": asset.file_path,
        "file_name": asset.file_name,
        "target": asset.target,
    }

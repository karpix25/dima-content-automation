from __future__ import annotations

from pydantic import BaseModel


class FormatOut(BaseModel):
    key: str
    label: str
    task_type: str
    description: str


class ScriptOut(BaseModel):
    id: int
    title: str
    hook: str
    trigger: str
    voiceover: str
    cta: str
    source_basis: str


class CreateFormatJobIn(BaseModel):
    user_id: str
    format_key: str


class CreateExistingHeyGenJobIn(BaseModel):
    user_id: str
    format_key: str = "avatar_reels"
    heygen_video_id: str


class TextSettingIn(BaseModel):
    user_id: str
    key: str
    value: str


class SelectAssetIn(BaseModel):
    user_id: str
    id: str
    name: str
    target: str = "both"
    preview_image_url: str | None = None
    preview_video_url: str | None = None


class HeyGenModelIn(BaseModel):
    user_id: str
    model: str


class OverlayPercentIn(BaseModel):
    user_id: str
    format: str
    start_percent: int


class OverlayOut(BaseModel):
    format: str
    label: str
    has_file: bool
    file_name: str | None = None
    start_percent: int


class MediaAssetOut(BaseModel):
    id: int
    user_id: str
    kind: str
    file_path: str
    file_name: str
    target: str
    url: str
    created_at: str


class MediaTargetIn(BaseModel):
    user_id: str
    target: str


class FaceActivateIn(BaseModel):
    user_id: str
    target: str = "both"


class InstagramPost5sOut(BaseModel):
    cta_text: str
    audio_tracks: list[MediaAssetOut]
    infographic_references: list[MediaAssetOut] = []


class UserSettingsOut(BaseModel):
    notebook_id: str | None = None
    author_style: str
    offer_context: str
    cta_mix: str
    heygen_avatar_id: str | None = None
    heygen_avatar_name: str | None = None
    heygen_avatar_preview_image_url: str | None = None
    heygen_avatar_preview_video_url: str | None = None
    heygen_vertical_avatar_id: str | None = None
    heygen_vertical_avatar_name: str | None = None
    heygen_vertical_avatar_preview_image_url: str | None = None
    heygen_vertical_avatar_preview_video_url: str | None = None
    heygen_video_api_version: str = "v2"
    heygen_avatar_engine: str = "avatar_iv"
    elevenlabs_voice_id: str | None = None
    elevenlabs_voice_name: str
    thumbnail_face_path: str | None = None
    vertical_thumbnail_face_path: str | None = None
    youtube_description_template: str
    avatar_insert_start_percent: int
    avatar_insert_end_percent: int
    avatar_insert_clips_count: int
    youtube_long_duration_minutes: int
    vertical_avatar_duration_mode: str
    instagram_post_5s_cta_text: str
    overlays: list[OverlayOut]


class HeyGenAvatarOut(BaseModel):
    id: str
    name: str
    preview_image_url: str | None = None
    preview_video_url: str | None = None
    avatar_type: str = ""
    supported_engines: list[str] = []


class ElevenLabsVoiceOut(BaseModel):
    id: str
    name: str
    category: str | None = None
    preview_url: str | None = None


class FormatJobOut(BaseModel):
    id: int
    script_id: int
    format_key: str
    task_type: str
    title: str
    status: str
    output_text: str
    output_url: str | None = None
    external_task_id: str | None = None
    error: str | None = None
    raw: dict
    created_at: str
    updated_at: str

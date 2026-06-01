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


class TextSettingIn(BaseModel):
    user_id: str
    key: str
    value: str


class SelectAssetIn(BaseModel):
    user_id: str
    id: str
    name: str


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


class UserSettingsOut(BaseModel):
    notebook_id: str | None = None
    author_style: str
    offer_context: str
    cta_mix: str
    heygen_avatar_id: str | None = None
    heygen_avatar_name: str | None = None
    elevenlabs_voice_id: str | None = None
    elevenlabs_voice_name: str
    overlays: list[OverlayOut]


class HeyGenAvatarOut(BaseModel):
    id: str
    name: str
    preview_image_url: str | None = None
    preview_video_url: str | None = None


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

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import load_settings
from .elevenlabs_api import ElevenLabsAPIClient, ElevenLabsAPIError
from .heygen import HeyGenClient, HeyGenError
from .infographic_delivery import create_and_send_infographic_reels
from .media_assets import (
    AUDIO_EXTENSIONS,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    MediaAsset,
    MediaAssetStore,
    delete_asset_file,
    save_uploaded_asset,
)
from .settings_service import (
    delete_overlay_file,
    get_overlay_path,
    get_user_settings,
    save_overlay_file,
    set_active_elevenlabs_voice,
    set_active_heygen_avatar,
    set_active_thumbnail_face,
    set_heygen_generation_model,
    set_instagram_post_5s_overlay,
    set_overlay_start_percent,
    set_text_setting,
)
from .storage import Storage
from .turan_client import TuranApiClient, submit_format_job
from .turan_formats import list_turan_formats
from .turan_service import TuranServiceError, create_format_job, list_approved_scripts
from .web_models import (
    CreateFormatJobIn,
    ElevenLabsVoiceOut,
    FormatJobOut,
    FormatOut,
    FaceActivateIn,
    HeyGenModelIn,
    HeyGenAvatarOut,
    InstagramPost5sOut,
    MediaAssetOut,
    MediaTargetIn,
    OverlayOut,
    OverlayPercentIn,
    ScriptOut,
    SelectAssetIn,
    TextSettingIn,
    UserSettingsOut,
)
from .web_serializers import format_to_out, job_to_out, script_to_out


settings = load_settings()
storage = Storage(settings.data_dir / "content_automation.sqlite3")
asset_store = MediaAssetStore(settings.data_dir / "content_automation.sqlite3")
heygen = HeyGenClient(
    api_key=settings.heygen_api_key,
    api_base_url=settings.heygen_api_base_url,
    upload_base_url=settings.heygen_upload_base_url,
    aspect_ratio=settings.heygen_aspect_ratio,
    resolution=settings.heygen_resolution,
    output_format=settings.heygen_output_format,
    poll_seconds=settings.heygen_video_poll_seconds,
    timeout_seconds=settings.heygen_video_timeout_seconds,
    private_avatars_only=settings.heygen_private_avatars_only,
)
elevenlabs = ElevenLabsAPIClient(api_key=settings.elevenlabs_api_key)
static_dir = Path(__file__).with_name("static")

app = FastAPI(title="DIMA Content Mini App")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/formats", response_model=list[FormatOut])
def formats() -> list[FormatOut]:
    return [format_to_out(item) for item in list_turan_formats()]


@app.get("/api/scripts/approved", response_model=list[ScriptOut])
def approved_scripts(
    user_id: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=100),
) -> list[ScriptOut]:
    return [script_to_out(item) for item in list_approved_scripts(storage, user_id, limit=limit)]


@app.get("/api/format-jobs", response_model=list[FormatJobOut])
def format_jobs(
    user_id: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=100),
) -> list[FormatJobOut]:
    return [job_to_out(item) for item in storage.list_format_jobs(user_id, limit=limit)]


@app.get("/api/settings", response_model=UserSettingsOut)
def user_settings(user_id: str = Query(..., min_length=1)) -> UserSettingsOut:
    return settings_to_out(user_id)


@app.patch("/api/settings/text", response_model=UserSettingsOut)
def update_text_setting(payload: TextSettingIn) -> UserSettingsOut:
    try:
        set_text_setting(storage, payload.user_id, payload.key, payload.value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return settings_to_out(payload.user_id)


@app.get("/api/settings/heygen-avatars", response_model=list[HeyGenAvatarOut])
async def heygen_avatars() -> list[HeyGenAvatarOut]:
    try:
        avatars = await heygen.list_avatar_looks()
    except HeyGenError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [
        HeyGenAvatarOut(
            id=item.id,
            name=item.name,
            preview_image_url=item.preview_image_url,
            preview_video_url=item.preview_video_url,
            avatar_type=item.avatar_type,
            supported_engines=item.supported_engines,
        )
        for item in avatars
    ]


@app.post("/api/settings/heygen-avatar", response_model=UserSettingsOut)
def update_heygen_avatar(payload: SelectAssetIn) -> UserSettingsOut:
    try:
        set_active_heygen_avatar(storage, payload.user_id, payload.id, payload.name, payload.target)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return settings_to_out(payload.user_id)


@app.post("/api/settings/heygen-model", response_model=UserSettingsOut)
def update_heygen_model(payload: HeyGenModelIn) -> UserSettingsOut:
    try:
        set_heygen_generation_model(storage, payload.user_id, payload.model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return settings_to_out(payload.user_id)


@app.get("/api/settings/elevenlabs-voices", response_model=list[ElevenLabsVoiceOut])
async def elevenlabs_voices() -> list[ElevenLabsVoiceOut]:
    try:
        voices = await elevenlabs.list_voices()
    except ElevenLabsAPIError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [ElevenLabsVoiceOut(id=item.id, name=item.name, category=item.category, preview_url=item.preview_url) for item in voices]


@app.post("/api/settings/elevenlabs-voice", response_model=UserSettingsOut)
def update_elevenlabs_voice(payload: SelectAssetIn) -> UserSettingsOut:
    set_active_elevenlabs_voice(storage, payload.user_id, payload.id, payload.name)
    return settings_to_out(payload.user_id)


@app.patch("/api/settings/overlay", response_model=OverlayOut)
def update_overlay_percent(payload: OverlayPercentIn) -> OverlayOut:
    try:
        state = set_overlay_start_percent(storage, payload.user_id, payload.format, payload.start_percent)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return OverlayOut.model_validate(state.__dict__)


@app.post("/api/settings/overlay", response_model=OverlayOut)
async def upload_overlay(
    user_id: str = Form(...),
    format: str = Form(...),
    file: UploadFile = File(...),
) -> OverlayOut:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    try:
        state = save_overlay_file(storage, settings, user_id, format, file.filename or "overlay.png", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return OverlayOut.model_validate(state.__dict__)


@app.delete("/api/settings/overlay", response_model=OverlayOut)
def delete_overlay(user_id: str = Query(..., min_length=1), format: str = Query(..., min_length=1)) -> OverlayOut:
    try:
        state = delete_overlay_file(storage, user_id, format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return OverlayOut.model_validate(state.__dict__)


@app.get("/api/settings/overlay/file")
def overlay_file(user_id: str = Query(..., min_length=1), format: str = Query(..., min_length=1)) -> FileResponse:
    try:
        path = get_overlay_path(storage, user_id, format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="Overlay not found")
    return FileResponse(path)


@app.get("/api/settings/media/{asset_id}")
def media_asset_file(asset_id: int, user_id: str = Query(..., min_length=1)) -> FileResponse:
    asset = asset_store.get_asset(user_id, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    path = Path(asset.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Asset file not found")
    return FileResponse(path)


@app.get("/api/settings/thumbnail-references", response_model=list[MediaAssetOut])
def thumbnail_references(user_id: str = Query(..., min_length=1)) -> list[MediaAssetOut]:
    return [asset_to_out(item) for item in asset_store.list_assets(user_id, "thumbnail_reference")]


@app.post("/api/settings/thumbnail-references", response_model=list[MediaAssetOut])
async def upload_thumbnail_references(
    user_id: str = Form(...),
    target: str = Form("both"),
    files: list[UploadFile] = File(...),
) -> list[MediaAssetOut]:
    return [asset_to_out(await save_upload(item, user_id, "thumbnail_reference", IMAGE_EXTENSIONS, target=target)) for item in files]


@app.patch("/api/settings/thumbnail-references/{asset_id}", response_model=MediaAssetOut)
def update_thumbnail_reference(asset_id: int, payload: MediaTargetIn) -> MediaAssetOut:
    try:
        return asset_to_out(asset_store.update_target(payload.user_id, asset_id, payload.target))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.delete("/api/settings/thumbnail-references/{asset_id}")
def delete_thumbnail_reference(asset_id: int, user_id: str = Query(..., min_length=1)) -> dict[str, int]:
    try:
        asset = asset_store.delete_asset(user_id, asset_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    delete_asset_file(asset)
    return {"asset_id": asset_id}


@app.get("/api/settings/thumbnail-face-references", response_model=list[MediaAssetOut])
def thumbnail_face_references(user_id: str = Query(..., min_length=1)) -> list[MediaAssetOut]:
    return [asset_to_out(item) for item in asset_store.list_assets(user_id, "thumbnail_face")]


@app.post("/api/settings/thumbnail-faces", response_model=list[MediaAssetOut])
async def upload_thumbnail_faces(user_id: str = Form(...), files: list[UploadFile] = File(...)) -> list[MediaAssetOut]:
    created = [await save_upload(item, user_id, "thumbnail_face", IMAGE_EXTENSIONS) for item in files]
    if created and not storage.get_setting(user_id, "thumbnail_face_path") and not storage.get_setting(user_id, "vertical_thumbnail_face_path"):
        set_active_thumbnail_face(storage, user_id, created[0].file_path, "both")
    return [asset_to_out(item) for item in created]


@app.patch("/api/settings/thumbnail-face-references/{asset_id}", response_model=UserSettingsOut)
def activate_thumbnail_face(asset_id: int, payload: FaceActivateIn) -> UserSettingsOut:
    asset = asset_store.get_asset(payload.user_id, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    set_active_thumbnail_face(storage, payload.user_id, asset.file_path, payload.target)
    return settings_to_out(payload.user_id)


@app.delete("/api/settings/thumbnail-face-references/{asset_id}", response_model=UserSettingsOut)
def delete_thumbnail_face_reference(asset_id: int, user_id: str = Query(..., min_length=1)) -> UserSettingsOut:
    try:
        asset = asset_store.delete_asset(user_id, asset_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    active_paths = {storage.get_setting(user_id, "thumbnail_face_path"), storage.get_setting(user_id, "vertical_thumbnail_face_path")}
    if asset.file_path in active_paths:
        next_asset = next(iter(asset_store.list_assets(user_id, "thumbnail_face", limit=1)), None)
        set_active_thumbnail_face(storage, user_id, next_asset.file_path if next_asset else None, "both")
    delete_asset_file(asset)
    return settings_to_out(user_id)


@app.get("/api/settings/avatar-inserts", response_model=list[MediaAssetOut])
def avatar_inserts(user_id: str = Query(..., min_length=1)) -> list[MediaAssetOut]:
    return [asset_to_out(item) for item in asset_store.list_assets(user_id, "avatar_insert")]


@app.post("/api/settings/avatar-inserts", response_model=list[MediaAssetOut])
async def upload_avatar_inserts(user_id: str = Form(...), files: list[UploadFile] = File(...)) -> list[MediaAssetOut]:
    return [asset_to_out(await save_upload(item, user_id, "avatar_insert", VIDEO_EXTENSIONS)) for item in files]


@app.delete("/api/settings/avatar-inserts/{asset_id}")
def delete_avatar_insert(asset_id: int, user_id: str = Query(..., min_length=1)) -> dict[str, int]:
    try:
        asset = asset_store.delete_asset(user_id, asset_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    delete_asset_file(asset)
    return {"asset_id": asset_id}


@app.get("/api/settings/instagram-post-5s", response_model=InstagramPost5sOut)
def instagram_post_5s(user_id: str = Query(..., min_length=1)) -> InstagramPost5sOut:
    return instagram_post_5s_out(user_id)


@app.post("/api/settings/instagram-post-5s/audio", response_model=InstagramPost5sOut)
async def upload_instagram_post_5s_audio(user_id: str = Form(...), files: list[UploadFile] = File(...)) -> InstagramPost5sOut:
    for item in files:
        await save_upload(item, user_id, "instagram_post_5s_audio", AUDIO_EXTENSIONS, target="both")
    return instagram_post_5s_out(user_id)


@app.delete("/api/settings/instagram-post-5s/audio/{asset_id}", response_model=InstagramPost5sOut)
def delete_instagram_post_5s_audio(asset_id: int, user_id: str = Query(..., min_length=1)) -> InstagramPost5sOut:
    try:
        asset = asset_store.delete_asset(user_id, asset_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    delete_asset_file(asset)
    return instagram_post_5s_out(user_id)


@app.post("/api/settings/instagram-post-5s/overlay", response_model=InstagramPost5sOut)
async def upload_instagram_post_5s_overlay(user_id: str = Form(...), file: UploadFile = File(...)) -> InstagramPost5sOut:
    previous = storage.get_setting(user_id, "instagram_post_5s_overlay_path")
    asset = await save_upload(file, user_id, "instagram_post_5s_overlay", IMAGE_EXTENSIONS)
    set_instagram_post_5s_overlay(storage, user_id, asset.file_path)
    if previous and previous != asset.file_path and Path(previous).exists():
        Path(previous).unlink()
    return instagram_post_5s_out(user_id)


@app.delete("/api/settings/instagram-post-5s/overlay", response_model=InstagramPost5sOut)
def delete_instagram_post_5s_overlay(user_id: str = Query(..., min_length=1)) -> InstagramPost5sOut:
    previous = storage.get_setting(user_id, "instagram_post_5s_overlay_path")
    set_instagram_post_5s_overlay(storage, user_id, None)
    if previous and Path(previous).exists():
        Path(previous).unlink()
    return instagram_post_5s_out(user_id)


@app.get("/api/format-jobs/{job_id}", response_model=FormatJobOut)
def format_job(job_id: int, user_id: str = Query(..., min_length=1)) -> FormatJobOut:
    job = storage.get_format_job(user_id, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Format job not found")
    return job_to_out(job)


def settings_to_out(user_id: str) -> UserSettingsOut:
    return UserSettingsOut.model_validate(asdict(get_user_settings(storage, settings, user_id)))


async def save_upload(file: UploadFile, user_id: str, kind: str, extensions: set[str], *, target: str = "both") -> MediaAsset:
    try:
        return save_uploaded_asset(
            asset_store,
            settings,
            user_id,
            kind=kind,
            filename=file.filename or "asset",
            content=await file.read(),
            allowed_extensions=extensions,
            target=target,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def asset_to_out(asset: MediaAsset) -> MediaAssetOut:
    return MediaAssetOut(
        id=asset.id,
        user_id=asset.user_id,
        kind=asset.kind,
        file_path=asset.file_path,
        file_name=asset.file_name,
        target=asset.target,
        url=f"/api/settings/media/{asset.id}?user_id={asset.user_id}",
        created_at=asset.created_at,
    )


def instagram_post_5s_out(user_id: str) -> InstagramPost5sOut:
    settings_state = get_user_settings(storage, settings, user_id)
    overlay_path = settings_state.instagram_post_5s_overlay_path
    overlay_url = None
    if overlay_path:
        overlay_asset = find_asset_by_path(user_id, "instagram_post_5s_overlay", overlay_path)
        overlay_url = f"/api/settings/media/{overlay_asset.id}?user_id={user_id}" if overlay_asset else None
    return InstagramPost5sOut(
        cta_text=settings_state.instagram_post_5s_cta_text,
        overlay_path=overlay_path,
        overlay_url=overlay_url,
        audio_tracks=[asset_to_out(item) for item in asset_store.list_assets(user_id, "instagram_post_5s_audio")],
    )


def find_asset_by_path(user_id: str, kind: str, path: str) -> MediaAsset | None:
    return next((item for item in asset_store.list_assets(user_id, kind) if item.file_path == path), None)


@app.post("/api/scripts/{script_id}/format-jobs", response_model=FormatJobOut)
def create_script_format_job(script_id: int, payload: CreateFormatJobIn) -> FormatJobOut:
    try:
        job = create_format_job(
            storage,
            payload.user_id,
            script_id,
            payload.format_key,
            asset_store=asset_store,
            settings=settings,
        )
    except TuranServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if job.format_key == "infographic_reels":
        record = storage.get_script(payload.user_id, script_id)
        if not record:
            raise HTTPException(status_code=404, detail="Script not found")
        try:
            result = create_and_send_infographic_reels(
                record=record,
                user_id=payload.user_id,
                settings=settings,
                asset_store=asset_store,
            )
            job = storage.update_format_job_delivery(
                payload.user_id,
                job.id,
                status="delivered",
                external_task_id=result.telegram_message_id,
                output_url=str(result.video_path),
                output_text=(
                    "✅ Золотой фон / инфографика 5 сек. создана и отправлена в Telegram.\n"
                    f"Файл: {result.video_path}"
                ),
            )
        except Exception as exc:
            job = storage.update_format_job_delivery(
                payload.user_id,
                job.id,
                status="failed",
                error=str(exc),
                output_text=f"⚠️ Не удалось создать или отправить золотой фон: {exc}",
            )
        return job_to_out(job)
    if settings.turan_api_base_url:
        result = submit_format_job(
            job,
            TuranApiClient(settings.turan_api_base_url),
            settings.turan_api_telegram_id or payload.user_id,
        )
        job = storage.update_format_job_delivery(
            payload.user_id,
            job.id,
            status=result.status,
            external_task_id=result.external_task_id,
            error=result.error,
            raw=result.raw,
        )
    return job_to_out(job)

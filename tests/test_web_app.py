from pathlib import Path
from dataclasses import replace
from types import SimpleNamespace

from fastapi.testclient import TestClient

from content_automation import web_app, web_format_jobs
from content_automation.media_assets import MediaAssetStore
from content_automation.storage import Storage


def make_storage(tmp_path: Path) -> Storage:
    return Storage(tmp_path / "web.sqlite3")


def make_asset_store(tmp_path: Path) -> MediaAssetStore:
    return MediaAssetStore(tmp_path / "web.sqlite3")


def add_approved_script(storage: Storage, user_id: str = "42"):
    record = storage.add_script(
        user_id,
        "short",
        {
            "title": "Margin trap",
            "angle": "Profit angle",
            "hook": "Revenue is not profit",
            "trigger": "Cash conversion",
            "voiceover": "Your revenue can grow while your cash disappears.",
            "cta": "Check contribution margin.",
            "why_it_works": "Sharp seller pain.",
            "source_basis": "NotebookLM notes.",
        },
    )
    return storage.update_script_status(user_id, record.id, "approved")


def test_formats_endpoint_lists_catalog():
    client = TestClient(web_app.app)

    response = client.get("/api/formats")

    assert response.status_code == 200
    assert {item["key"] for item in response.json()} >= {"avatar_reels", "infographic_reels"}


def test_index_allows_head_probe():
    client = TestClient(web_app.app)

    response = client.head("/")

    assert response.status_code == 200


def test_approved_scripts_include_editorial_metadata(tmp_path, monkeypatch):
    storage = make_storage(tmp_path)
    record = storage.add_script(
        "42",
        "short",
        {
            "title": "Margin trap",
            "hook": "Revenue is not profit",
            "trigger": "Cash conversion",
            "voiceover": "Your revenue can grow while your cash disappears.",
            "cta": "",
            "source_basis": "NotebookLM notes.",
            "content_format": "money_leak",
            "content_format_label": "Money Leak",
            "content_pillar": "profit_economics",
            "content_pillar_label": "Profit & economics",
            "proof_type": "numbers",
            "proof_type_label": "Numbers",
            "emotion_angle": "shock",
            "emotion_angle_label": "Shock",
            "series_name": "Hidden Leaks",
            "hook_pattern": "specificity slam",
            "mechanism": "contrast revenue with cash",
            "first_frame_text": "CASH LEAK",
            "visual_proof": "cash flow chart",
            "visual_retention_plan": "headline, proof, fix",
        },
    )
    storage.update_script_status("42", record.id, "approved")
    monkeypatch.setattr(web_app, "storage", storage)
    client = TestClient(web_app.app)

    response = client.get("/api/scripts/approved", params={"user_id": "42"})

    assert response.status_code == 200
    assert response.json()[0]["editorial_summary"] == "Money Leak · Profit & economics · Numbers · Shock · Hidden Leaks"
    assert response.json()[0]["content_format"] == "money_leak"
    assert response.json()[0]["first_frame_text"] == "CASH LEAK"
    assert response.json()[0]["hook_pattern"] == "specificity slam"
    assert response.json()[0]["mechanism"] == "contrast revenue with cash"
    assert response.json()[0]["visual_proof"] == "cash flow chart"
    assert response.json()[0]["visual_retention_plan"] == "headline, proof, fix"


def test_format_job_flow_uses_temp_storage(tmp_path, monkeypatch):
    storage = make_storage(tmp_path)
    asset_store = make_asset_store(tmp_path)
    record = add_approved_script(storage)
    monkeypatch.setattr(web_app, "storage", storage)
    monkeypatch.setattr(web_app, "asset_store", asset_store)

    def fake_avatar_delivery(**kwargs):
        return SimpleNamespace(
            video_path=tmp_path / f"{kwargs['format_key']}.mp4",
            telegram_message_id=f"tg-{kwargs['format_key']}",
            heygen_video_id="heygen",
        )

    def fake_infographic_delivery(**kwargs):
        return SimpleNamespace(video_path=tmp_path / "gold.mp4", telegram_message_id="tg-gold")

    monkeypatch.setattr(web_format_jobs, "create_and_send_avatar_video", fake_avatar_delivery)
    monkeypatch.setattr(web_format_jobs, "create_and_send_infographic_reels", fake_infographic_delivery)
    client = TestClient(web_app.app)

    listed = client.get("/api/scripts/approved", params={"user_id": record.user_id})
    created = client.post(
        f"/api/scripts/{record.id}/format-jobs",
        json={"user_id": record.user_id, "format_key": "all"},
    )
    jobs = client.get("/api/format-jobs", params={"user_id": record.user_id})
    opened = client.get(f"/api/format-jobs/{created.json()['id']}", params={"user_id": record.user_id})

    assert listed.status_code == 200
    assert listed.json()[0]["id"] == record.id
    assert created.status_code == 200
    assert created.json()["status"] == "queued"
    assert created.json()["task_type"] == "turan_bundle"
    assert created.json()["raw"]["formats"][0]["turan_task_input"]["source_url"] == f"notebooklm-script://{record.id}"
    assert jobs.status_code == 200
    assert {job["format_key"] for job in jobs.json()} >= {"all", "avatar_reels", "infographic_reels", "avatar_horizontal"}
    assert any(job["id"] == created.json()["id"] for job in jobs.json())
    assert opened.status_code == 200
    assert opened.json()["status"] == "delivered"
    assert "Генерация всех форматов завершена" in opened.json()["output_text"]
    assert "gold.mp4" in opened.json()["output_text"]
    assert storage.get_script(record.user_id, record.id).status == "used_for_video"


def test_existing_heygen_job_reuses_video_id(tmp_path, monkeypatch):
    storage = make_storage(tmp_path)
    asset_store = make_asset_store(tmp_path)
    record = add_approved_script(storage)
    monkeypatch.setattr(web_app, "storage", storage)
    monkeypatch.setattr(web_app, "asset_store", asset_store)
    calls = []

    def fake_existing_delivery(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            video_path=tmp_path / "existing.mp4",
            telegram_message_id="tg-existing",
            heygen_video_id=kwargs["heygen_video_id"],
        )

    monkeypatch.setattr(web_format_jobs, "create_and_send_existing_heygen_video", fake_existing_delivery)
    client = TestClient(web_app.app)

    created = client.post(
        f"/api/scripts/{record.id}/format-jobs/existing-heygen",
        json={"user_id": record.user_id, "format_key": "avatar_reels", "heygen_video_id": "video-123"},
    )
    opened = client.get(f"/api/format-jobs/{created.json()['id']}", params={"user_id": record.user_id})

    assert created.status_code == 200
    assert created.json()["status"] == "queued"
    assert created.json()["external_task_id"] == "video-123"
    assert created.json()["raw"]["existing_heygen_video_id"] == "video-123"
    assert calls[0]["heygen_video_id"] == "video-123"
    assert calls[0]["format_key"] == "avatar_reels"
    assert opened.json()["status"] == "delivered"
    assert opened.json()["output_url"].endswith("existing.mp4")


def test_existing_heygen_job_hides_output_url_when_video_deleted(tmp_path, monkeypatch):
    storage = make_storage(tmp_path)
    asset_store = make_asset_store(tmp_path)
    record = add_approved_script(storage)
    monkeypatch.setattr(web_app, "storage", storage)
    monkeypatch.setattr(web_app, "asset_store", asset_store)

    def fake_existing_delivery(**kwargs):
        return SimpleNamespace(
            video_path=tmp_path / "existing.mp4",
            telegram_message_id="tg-existing",
            heygen_video_id=kwargs["heygen_video_id"],
            video_deleted=True,
        )

    monkeypatch.setattr(web_format_jobs, "create_and_send_existing_heygen_video", fake_existing_delivery)
    client = TestClient(web_app.app)

    created = client.post(
        f"/api/scripts/{record.id}/format-jobs/existing-heygen",
        json={"user_id": record.user_id, "format_key": "avatar_reels", "heygen_video_id": "video-123"},
    )
    opened = client.get(f"/api/format-jobs/{created.json()['id']}", params={"user_id": record.user_id})

    assert opened.json()["status"] == "delivered"
    assert opened.json()["output_url"] is None
    assert "Файл удален с сервера после отправки в Telegram" in opened.json()["output_text"]


def test_infographic_reels_job_sends_video_instead_of_prompt(tmp_path, monkeypatch):
    storage = make_storage(tmp_path)
    asset_store = make_asset_store(tmp_path)
    record = add_approved_script(storage)
    monkeypatch.setattr(web_app, "storage", storage)
    monkeypatch.setattr(web_app, "asset_store", asset_store)

    def fake_delivery(**kwargs):
        assert "overlay_path" not in kwargs
        return SimpleNamespace(video_path=tmp_path / "gold.mp4", telegram_message_id="777")

    monkeypatch.setattr(web_format_jobs, "create_and_send_infographic_reels", fake_delivery)
    client = TestClient(web_app.app)

    created = client.post(
        f"/api/scripts/{record.id}/format-jobs",
        json={"user_id": record.user_id, "format_key": "infographic_reels"},
    )

    assert created.status_code == 200
    assert created.json()["status"] == "queued"
    opened = client.get(f"/api/format-jobs/{created.json()['id']}", params={"user_id": record.user_id})
    assert opened.json()["status"] == "delivered"
    assert opened.json()["external_task_id"] == "777"
    assert "отправлена в Telegram" in opened.json()["output_text"]


def test_infographic_reels_uses_face_reference_not_cover_reference(tmp_path, monkeypatch):
    storage = make_storage(tmp_path)
    asset_store = make_asset_store(tmp_path)
    record = add_approved_script(storage)
    face_path = tmp_path / "face.jpg"
    cover_path = tmp_path / "cover.jpg"
    face_path.write_bytes(b"face")
    cover_path.write_bytes(b"cover")
    storage.set_setting(record.user_id, "vertical_thumbnail_face_path", str(face_path))
    asset_store.add_asset(record.user_id, kind="thumbnail_reference", file_path=cover_path, file_name="cover.jpg", target="vertical")
    design = asset_store.add_asset(record.user_id, kind="instagram_post_5s_reference", file_path=cover_path, file_name="cover.jpg", target="vertical")
    monkeypatch.setattr(web_app, "storage", storage)
    monkeypatch.setattr(web_app, "asset_store", asset_store)
    seen = {}

    def fake_delivery(**kwargs):
        assert "overlay_path" not in kwargs
        seen["face_reference_paths"] = kwargs["face_reference_paths"]
        seen["design_reference_paths"] = kwargs["design_reference_paths"]
        return SimpleNamespace(video_path=tmp_path / "gold.mp4", telegram_message_id="777")

    monkeypatch.setattr(web_format_jobs, "create_and_send_infographic_reels", fake_delivery)
    client = TestClient(web_app.app)

    created = client.post(
        f"/api/scripts/{record.id}/format-jobs",
        json={"user_id": record.user_id, "format_key": "infographic_reels"},
    )
    opened = client.get(f"/api/format-jobs/{created.json()['id']}", params={"user_id": record.user_id})

    assert opened.json()["status"] == "delivered"
    assert seen["face_reference_paths"] == [face_path]
    assert seen["design_reference_paths"] == [cover_path]
    assert design.file_name == "cover.jpg"


def test_instagram_post_5s_infographic_references_flow(tmp_path, monkeypatch):
    storage = make_storage(tmp_path)
    asset_store = make_asset_store(tmp_path)
    monkeypatch.setattr(web_app, "storage", storage)
    monkeypatch.setattr(web_app, "asset_store", asset_store)
    monkeypatch.setattr(web_app, "settings", replace(web_app.settings, data_dir=tmp_path))
    client = TestClient(web_app.app)

    uploaded = client.post(
        "/api/settings/instagram-post-5s/references",
        data={"user_id": "42"},
        files=[("files", ("layout.png", b"layout", "image/png"))],
    )
    loaded = client.get("/api/settings/instagram-post-5s", params={"user_id": "42"})
    deleted = client.delete(
        f"/api/settings/instagram-post-5s/references/{uploaded.json()['infographic_references'][0]['id']}",
        params={"user_id": "42"},
    )

    assert uploaded.status_code == 200
    assert "overlay_url" not in loaded.json()
    assert "overlay_path" not in loaded.json()
    assert uploaded.json()["infographic_references"][0]["file_name"] == "layout.png"
    assert loaded.json()["infographic_references"][0]["file_name"] == "layout.png"
    assert deleted.json()["infographic_references"] == []


def test_settings_flow_uses_same_storage(tmp_path, monkeypatch):
    storage = make_storage(tmp_path)
    monkeypatch.setattr(web_app, "storage", storage)
    client = TestClient(web_app.app)

    saved = client.patch(
        "/api/settings/text",
        json={"user_id": "42", "key": "author_style", "value": "Direct operator voice."},
    )
    duration = client.patch(
        "/api/settings/text",
        json={"user_id": "42", "key": "youtube_long_duration_minutes", "value": "12"},
    )
    vertical_duration = client.patch(
        "/api/settings/text",
        json={"user_id": "42", "key": "vertical_avatar_duration_mode", "value": "60"},
    )
    vizard_lengths = client.patch(
        "/api/settings/text",
        json={"user_id": "42", "key": "vizard_prefer_length", "value": "2,3"},
    )
    vizard_section = client.patch(
        "/api/settings/section",
        json={
            "user_id": "42",
            "values": {
                "vizard_ratio_of_clip": "4",
                "vizard_prefer_length": "4",
                "vizard_remove_silence_switch": "1",
            },
        },
    )
    overlay = client.patch(
        "/api/settings/overlay",
        json={"user_id": "42", "format": "short", "start_percent": 55},
    )
    settings = client.get("/api/settings", params={"user_id": "42"})

    assert saved.status_code == 200
    assert saved.json()["author_style"] == "Direct operator voice."
    assert duration.json()["youtube_long_duration_minutes"] == 12
    assert vertical_duration.json()["vertical_avatar_duration_mode"] == "60"
    assert vizard_lengths.json()["vizard"]["prefer_length"] == [2, 3]
    assert vizard_section.json()["vizard"]["ratio_of_clip"] == 4
    assert vizard_section.json()["vizard"]["prefer_length"] == [4]
    assert vizard_section.json()["vizard"]["remove_silence_switch"] is True
    assert overlay.status_code == 200
    assert overlay.json()["start_percent"] == 55
    assert settings.status_code == 200
    shorts_overlay = next(item for item in settings.json()["overlays"] if item["format"] == "shorts")
    assert shorts_overlay["start_percent"] == 55


def test_overlay_upload_and_preview(tmp_path, monkeypatch):
    storage = make_storage(tmp_path)
    monkeypatch.setattr(web_app, "storage", storage)
    monkeypatch.setattr(web_app, "settings", replace(web_app.settings, data_dir=tmp_path))
    client = TestClient(web_app.app)

    uploaded = client.post(
        "/api/settings/overlay",
        data={"user_id": "42", "format": "youtube"},
        files={"file": ("plate.png", b"fake-png", "image/png")},
    )
    preview = client.get("/api/settings/overlay/file", params={"user_id": "42", "format": "youtube"})

    assert uploaded.status_code == 200
    assert uploaded.json()["has_file"] is True
    assert preview.status_code == 200
    assert preview.content == b"fake-png"


def test_overlay_upload_appends_multiple_files(tmp_path, monkeypatch):
    storage = make_storage(tmp_path)
    monkeypatch.setattr(web_app, "storage", storage)
    monkeypatch.setattr(web_app, "settings", replace(web_app.settings, data_dir=tmp_path))
    client = TestClient(web_app.app)

    first = client.post(
        "/api/settings/overlay",
        data={"user_id": "42", "format": "reels"},
        files={"file": ("first.png", b"first", "image/png")},
    )
    second = client.post(
        "/api/settings/overlay",
        data={"user_id": "42", "format": "reels"},
        files={"file": ("second.png", b"second", "image/png")},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["file_count"] == 2
    assert second.json()["file_name"] == "2 файлов, рандомный выбор"
    assert [item["file_name"] for item in second.json()["files"]] == ["reels_overlay_1.png", "reels_overlay_2.png"]


def test_overlay_delete_single_file(tmp_path, monkeypatch):
    storage = make_storage(tmp_path)
    monkeypatch.setattr(web_app, "storage", storage)
    monkeypatch.setattr(web_app, "settings", replace(web_app.settings, data_dir=tmp_path))
    client = TestClient(web_app.app)
    for name, content in [("first.png", b"first"), ("second.png", b"second")]:
        client.post(
            "/api/settings/overlay",
            data={"user_id": "42", "format": "shorts"},
            files={"file": (name, content, "image/png")},
        )

    deleted = client.delete("/api/settings/overlay/file", params={"user_id": "42", "format": "shorts", "index": 0})

    assert deleted.status_code == 200
    assert deleted.json()["file_count"] == 1
    assert deleted.json()["files"][0]["file_name"] == "shorts_overlay_2.png"


def test_turan_style_media_settings_flow(tmp_path, monkeypatch):
    storage = make_storage(tmp_path)
    asset_store = make_asset_store(tmp_path)
    monkeypatch.setattr(web_app, "storage", storage)
    monkeypatch.setattr(web_app, "asset_store", asset_store)
    monkeypatch.setattr(web_app, "settings", replace(web_app.settings, data_dir=tmp_path))
    client = TestClient(web_app.app)

    refs = client.post(
        "/api/settings/thumbnail-references",
        data={"user_id": "42", "target": "both"},
        files=[("files", ("ref.png", b"ref", "image/png"))],
    )
    updated = client.patch(
        f"/api/settings/thumbnail-references/{refs.json()[0]['id']}",
        json={"user_id": "42", "target": "horizontal"},
    )
    faces = client.post(
        "/api/settings/thumbnail-faces",
        data={"user_id": "42"},
        files=[("files", ("face.jpg", b"face", "image/jpeg"))],
    )
    activated = client.patch(
        f"/api/settings/thumbnail-face-references/{faces.json()[0]['id']}",
        json={"user_id": "42", "target": "vertical"},
    )
    horizontal_avatar = client.post(
        "/api/settings/heygen-avatar",
        json={
            "user_id": "42",
            "id": "avatar-horizontal",
            "name": "Horizontal Dima",
            "target": "horizontal",
            "preview_image_url": "https://example.com/horizontal.jpg",
        },
    )
    vertical_avatar = client.post(
        "/api/settings/heygen-avatar",
        json={"user_id": "42", "id": "avatar-vertical", "name": "Vertical Dima", "target": "vertical"},
    )
    model = client.post(
        "/api/settings/heygen-model",
        json={"user_id": "42", "model": "avatar_iv"},
    )
    audio = client.post(
        "/api/settings/instagram-post-5s/audio",
        data={"user_id": "42"},
        files=[("files", ("sound.mp3", b"audio", "audio/mpeg"))],
    )
    record = add_approved_script(storage)

    def fake_avatar_delivery(**kwargs):
        return SimpleNamespace(
            video_path=tmp_path / f"{kwargs['format_key']}.mp4",
            telegram_message_id="888",
            heygen_video_id="heygen",
        )

    monkeypatch.setattr(web_format_jobs, "create_and_send_avatar_video", fake_avatar_delivery)
    created_job = client.post(
        f"/api/scripts/{record.id}/format-jobs",
        json={"user_id": "42", "format_key": "avatar_horizontal"},
    )
    created_vertical_job = client.post(
        f"/api/scripts/{record.id}/format-jobs",
        json={"user_id": "42", "format_key": "avatar_reels"},
    )
    settings = client.get("/api/settings", params={"user_id": "42"})

    assert refs.status_code == 200
    assert updated.json()["target"] == "horizontal"
    assert faces.status_code == 200
    assert activated.status_code == 200
    assert horizontal_avatar.json()["heygen_avatar_id"] == "avatar-horizontal"
    assert horizontal_avatar.json()["heygen_avatar_preview_image_url"] == "https://example.com/horizontal.jpg"
    assert vertical_avatar.json()["heygen_vertical_avatar_id"] == "avatar-vertical"
    assert model.json()["heygen_video_api_version"] == "v3"
    assert model.json()["heygen_avatar_engine"] == "avatar_iv"
    assert audio.json()["audio_tracks"][0]["file_name"] == "sound.mp3"
    assert created_job.json()["status"] == "queued"
    assert created_vertical_job.json()["status"] == "queued"
    opened_job = client.get(f"/api/format-jobs/{created_job.json()['id']}", params={"user_id": "42"})
    opened_vertical_job = client.get(f"/api/format-jobs/{created_vertical_job.json()['id']}", params={"user_id": "42"})
    assert opened_job.json()["status"] == "delivered"
    assert opened_vertical_job.json()["status"] == "delivered"
    assert storage.get_script("42", record.id).status == "used_for_video"
    assert created_job.json()["raw"]["turan_task_input"]["visual_reference"]["thumbnail"]["style_references"][0]["file_name"] == "ref.png"
    assert created_job.json()["raw"]["turan_task_input"]["visual_reference"]["heygen_avatar"]["id"] == "avatar-horizontal"
    assert created_job.json()["raw"]["turan_task_input"]["visual_reference"]["heygen_avatar"]["engine"] == "avatar_iv"
    assert created_job.json()["raw"]["turan_task_input"]["visual_reference"]["duration"]["youtube_long_minutes"] == 10
    assert created_job.json()["raw"]["turan_task_input"]["visual_reference"]["duration"]["vertical_avatar_mode"] == "original"
    assert created_vertical_job.json()["raw"]["turan_task_input"]["visual_reference"]["heygen_avatar"]["id"] == "avatar-vertical"
    assert settings.json()["vertical_thumbnail_face_path"].endswith(".jpg")

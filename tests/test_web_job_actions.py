from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from content_automation import web_job_actions
from content_automation.storage import Storage
from content_automation.web_job_actions import build_job_actions_router, is_stale_job


def make_storage(tmp_path: Path) -> Storage:
    return Storage(tmp_path / "jobs.sqlite3")


def add_script(storage: Storage):
    record = storage.add_script(
        "42",
        "short",
        {
            "title": "Margin leak",
            "hook": "Revenue can hide margin loss.",
            "voiceover": "Revenue can hide margin loss if fees and ads are ignored.",
        },
    )
    return storage.update_script_status("42", record.id, "approved")


def make_client(tmp_path: Path, monkeypatch) -> tuple[TestClient, Storage]:
    storage = make_storage(tmp_path)
    app = FastAPI()
    monkeypatch.setattr(web_job_actions, "deliver_existing_format_job", lambda **_: None)
    monkeypatch.setattr(web_job_actions, "deliver_existing_heygen_video_job", lambda **_: None)
    app.include_router(
        build_job_actions_router(
            storage=storage,
            asset_store=None,
            settings=SimpleNamespace(turan_api_base_url=None),
        )
    )
    return TestClient(app), storage


def test_retry_failed_job_creates_new_queued_job(tmp_path, monkeypatch):
    client, storage = make_client(tmp_path, monkeypatch)
    record = add_script(storage)
    job = storage.add_format_job("42", script_id=record.id, format_key="avatar_reels", task_type="avatar", title="Avatar", output_text="")
    storage.update_format_job_delivery("42", job.id, status="failed", error="boom")

    response = client.post(f"/api/format-jobs/{job.id}/retry", params={"user_id": "42"})

    assert response.status_code == 200
    assert response.json()["id"] != job.id
    assert response.json()["status"] == "queued"
    assert response.json()["script_id"] == record.id


def test_mark_live_job_failed(tmp_path, monkeypatch):
    client, storage = make_client(tmp_path, monkeypatch)
    record = add_script(storage)
    job = storage.add_format_job("42", script_id=record.id, format_key="avatar_reels", task_type="avatar", title="Avatar", output_text="")
    storage.update_format_job_delivery("42", job.id, status="processing")

    response = client.post(f"/api/format-jobs/{job.id}/mark-failed", params={"user_id": "42"})

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert "Stopped manually" in response.json()["error"]


def test_stale_job_detection_uses_updated_at():
    job = SimpleNamespace(status="processing", updated_at=(datetime.now() - timedelta(minutes=31)).isoformat())

    assert is_stale_job(job) is True

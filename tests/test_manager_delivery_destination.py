from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from content_automation import web_app, web_format_jobs
from content_automation.delivery_destination import telegram_delivery_chat_id
from content_automation.media_assets import MediaAssetStore
from content_automation.storage import Storage


def _storage(tmp_path: Path) -> Storage:
    return Storage(tmp_path / "manager-delivery.sqlite3")


def _asset_store(tmp_path: Path) -> MediaAssetStore:
    return MediaAssetStore(tmp_path / "manager-delivery.sqlite3")


def _approved_script(storage: Storage, user_id: str = "42"):
    record = storage.add_script(
        user_id,
        "short",
        {
            "title": "Manager delivery",
            "hook": "Manager starts generation",
            "voiceover": "Send the result to the person who started it.",
        },
    )
    return storage.update_script_status(user_id, record.id, "approved")


def test_manager_actor_overrides_project_active_chat(tmp_path: Path):
    storage = _storage(tmp_path)
    storage.set_setting("42", "active_chat_id", "owner-chat")

    assert telegram_delivery_chat_id(storage, "42", "99") == "99"


def test_project_owner_actor_overrides_stale_active_chat(tmp_path: Path):
    storage = _storage(tmp_path)
    storage.set_setting("42", "active_chat_id", "manager-chat")

    assert telegram_delivery_chat_id(storage, "42", "42") == "42"


def test_missing_actor_keeps_existing_active_chat_fallback(tmp_path: Path):
    storage = _storage(tmp_path)
    storage.set_setting("42", "active_chat_id", "manager-chat")

    assert telegram_delivery_chat_id(storage, "42", None) == "manager-chat"


def test_queued_infographic_delivery_uses_manager_actor(tmp_path: Path, monkeypatch):
    storage = _storage(tmp_path)
    asset_store = _asset_store(tmp_path)
    record = _approved_script(storage)
    settings = replace(web_app.settings, data_dir=tmp_path, video_output_directory=tmp_path)
    seen: dict[str, str | None] = {}

    def fake_delivery(**kwargs):
        seen["delivery_actor_user_id"] = kwargs["delivery_actor_user_id"]
        return SimpleNamespace(video_path=tmp_path / "gold.mp4", telegram_message_id="tg-manager")

    monkeypatch.setattr(web_format_jobs, "create_and_send_infographic_reels", fake_delivery)
    job = web_format_jobs.create_queued_format_job(
        storage=storage,
        asset_store=asset_store,
        settings=settings,
        user_id=record.user_id,
        script_id=record.id,
        format_key="infographic_reels",
        delivery_actor_user_id="99",
    )

    web_format_jobs.deliver_existing_format_job(
        storage=storage,
        asset_store=asset_store,
        settings=settings,
        user_id=record.user_id,
        job_id=job.id,
    )

    assert seen["delivery_actor_user_id"] == "99"
    delivered = storage.get_format_job(record.user_id, job.id)
    assert delivered is not None
    assert delivered.external_task_id == "tg-manager"

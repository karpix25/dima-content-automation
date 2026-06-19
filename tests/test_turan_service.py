from pathlib import Path

import pytest

from content_automation.storage import Storage
from content_automation.turan_service import TuranServiceError, create_format_job, list_approved_scripts


def make_storage(tmp_path: Path) -> Storage:
    return Storage(tmp_path / "data.sqlite3")


def add_script(storage: Storage, user_id: str = "42"):
    return storage.add_script(
        user_id,
        "short",
        {
            "title": "Amazon PPC leak",
            "angle": "Cash flow angle",
            "hook": "Stop scaling this campaign",
            "trigger": "Hidden ACOS drag",
            "voiceover": "Your PPC can look profitable while it quietly kills cash flow.",
            "cta": "Audit contribution margin before scaling.",
            "why_it_works": "Clear pain and action.",
            "source_basis": "NotebookLM notes.",
        },
    )


def test_create_format_job_requires_approved_script(tmp_path):
    storage = make_storage(tmp_path)
    record = add_script(storage)

    with pytest.raises(TuranServiceError):
        create_format_job(storage, record.user_id, record.id, "avatar_reels")


def test_create_format_job_persists_turan_package(tmp_path):
    storage = make_storage(tmp_path)
    record = add_script(storage)
    storage.update_script_status(record.user_id, record.id, "approved")

    job = create_format_job(storage, record.user_id, record.id, "avatar_reels")

    assert job.script_id == record.id
    assert job.format_key == "avatar_reels"
    assert job.task_type == "avatar_instagram"
    assert "Stop scaling this campaign" in job.output_text
    assert job.raw["avatar"]["target_platform"] == "instagram"
    assert job.raw["turan_task_input"]["source_url"] == f"notebooklm-script://{record.id}"
    assert job.raw["turan_task_input"]["script_text"] == record.voiceover
    assert "Turan text-source input JSON" in job.output_text


def test_create_all_formats_job_persists_bundle(tmp_path):
    storage = make_storage(tmp_path)
    record = add_script(storage)
    storage.update_script_status(record.user_id, record.id, "approved")

    job = create_format_job(storage, record.user_id, record.id, "all")

    assert job.format_key == "all"
    assert job.task_type == "turan_bundle"
    assert "Turan format: ИИ аватар Reels" in job.output_text
    assert "Turan format: Золотой фон / инфографика 5 сек." in job.output_text
    assert job.raw["formats"][0]["turan_task_input"]["script_text"] == record.voiceover


def test_list_approved_scripts_filters_pending(tmp_path):
    storage = make_storage(tmp_path)
    pending = add_script(storage)
    approved = add_script(storage)
    used = add_script(storage)
    rejected = add_script(storage)
    storage.update_script_status(approved.user_id, approved.id, "approved")
    storage.update_script_status(used.user_id, used.id, "used_for_video")
    storage.update_script_status(rejected.user_id, rejected.id, "rejected")

    records = list_approved_scripts(storage, pending.user_id)

    assert [record.id for record in records] == [used.id, approved.id]


def test_list_approved_scripts_returns_latest_ids_first(tmp_path):
    storage = make_storage(tmp_path)
    for index in range(60):
        record = add_script(storage)
        storage.update_script_status(record.user_id, record.id, "approved")

    records = list_approved_scripts(storage, "42", limit=50)

    assert len(records) == 50
    assert records[0].id == 60
    assert records[-1].id == 11

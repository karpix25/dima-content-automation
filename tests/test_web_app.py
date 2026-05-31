from pathlib import Path

from fastapi.testclient import TestClient

from content_automation import web_app
from content_automation.storage import Storage


def make_storage(tmp_path: Path) -> Storage:
    return Storage(tmp_path / "web.sqlite3")


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


def test_format_job_flow_uses_temp_storage(tmp_path, monkeypatch):
    storage = make_storage(tmp_path)
    record = add_approved_script(storage)
    monkeypatch.setattr(web_app, "storage", storage)
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
    assert created.json()["task_type"] == "turan_bundle"
    assert created.json()["raw"]["formats"][0]["turan_task_input"]["source_url"] == f"notebooklm-script://{record.id}"
    assert jobs.status_code == 200
    assert jobs.json()[0]["id"] == created.json()["id"]
    assert opened.status_code == 200
    assert "Revenue is not profit" in opened.json()["output_text"]

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from content_automation.storage import Storage
from content_automation.web_script_review import build_script_review_router


def test_review_scripts_lists_pending_and_approves(tmp_path: Path):
    storage = Storage(tmp_path / "review.sqlite3")
    record = storage.add_script(
        "42",
        "short",
        {
            "title": "Buy Box leak",
            "hook": "Your listing ranks but still leaks sales.",
            "trigger": "Weak trust signals",
            "voiceover": "Audit the Buy Box before buying more traffic.",
            "cta": "Fix trust first.",
            "why_it_works": "Specific Amazon operator pain.",
            "source_basis": "NotebookLM notes.",
        },
    )
    app = FastAPI()
    app.include_router(build_script_review_router(storage=storage))
    client = TestClient(app)

    listed = client.get("/api/scripts/review", params={"user_id": "42"})
    approved = client.post(f"/api/scripts/{record.id}/review", json={"user_id": "42", "action": "approve"})
    listed_after = client.get("/api/scripts/review", params={"user_id": "42"})

    assert listed.status_code == 200
    assert listed.json()[0]["id"] == record.id
    assert approved.status_code == 200
    assert storage.get_script("42", record.id).status == "approved"
    assert listed_after.json() == []


def test_review_script_rejects_already_processed(tmp_path: Path):
    storage = Storage(tmp_path / "review.sqlite3")
    record = storage.add_script(
        "42",
        "short",
        {
            "title": "Fee trap",
            "hook": "Your FBA tier changed quietly.",
            "trigger": "Packaging mistake",
            "voiceover": "Measure the box before scaling.",
            "cta": "Audit dimensions.",
            "why_it_works": "Concrete money leak.",
            "source_basis": "NotebookLM notes.",
        },
    )
    storage.update_script_status("42", record.id, "approved")
    app = FastAPI()
    app.include_router(build_script_review_router(storage=storage))
    client = TestClient(app)

    response = client.post(f"/api/scripts/{record.id}/review", json={"user_id": "42", "action": "reject"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Этот сценарий уже обработан."


def test_delete_script_soft_deletes_processed_script(tmp_path: Path):
    storage = Storage(tmp_path / "review.sqlite3")
    record = storage.add_script(
        "42",
        "short",
        {
            "title": "Fee trap",
            "hook": "Your FBA tier changed quietly.",
            "trigger": "Packaging mistake",
            "voiceover": "Measure the box before scaling.",
            "cta": "Audit dimensions.",
            "why_it_works": "Concrete money leak.",
            "source_basis": "NotebookLM notes.",
        },
    )
    storage.update_script_status("42", record.id, "approved")
    app = FastAPI()
    app.include_router(build_script_review_router(storage=storage))
    client = TestClient(app)

    response = client.request("DELETE", f"/api/scripts/{record.id}", json={"user_id": "42", "action": "delete"})

    assert response.status_code == 200
    assert response.json()["id"] == record.id
    assert storage.get_script("42", record.id).status == "deleted"
    assert storage.list_approved_scripts("42") == []


def test_delete_script_removes_pending_from_review_queue(tmp_path: Path):
    storage = Storage(tmp_path / "review.sqlite3")
    record = storage.add_script(
        "42",
        "short",
        {
            "title": "Trust gap",
            "hook": "Your listing ranks but still leaks sales.",
            "trigger": "Weak trust signals",
            "voiceover": "Audit trust before buying more traffic.",
            "cta": "",
            "why_it_works": "Specific seller pain.",
            "source_basis": "NotebookLM notes.",
        },
    )
    app = FastAPI()
    app.include_router(build_script_review_router(storage=storage))
    client = TestClient(app)

    response = client.request("DELETE", f"/api/scripts/{record.id}", json={"user_id": "42", "action": "delete"})
    listed = client.get("/api/scripts/review", params={"user_id": "42"})

    assert response.status_code == 200
    assert listed.json() == []

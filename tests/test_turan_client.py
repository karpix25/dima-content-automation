from pathlib import Path

from content_automation.storage import Storage
from content_automation.turan_client import TuranApiClient, submit_format_job
from content_automation.turan_service import create_format_job


class FakeTuranClient(TuranApiClient):
    def __init__(self) -> None:
        self.payloads = []

    def create_task(self, telegram_id: str, payload: dict) -> dict:
        self.payloads.append((telegram_id, payload))
        return {"status": "queued", "task_id": len(self.payloads)}


def make_approved_job(tmp_path: Path):
    storage = Storage(tmp_path / "data.sqlite3")
    record = storage.add_script(
        "42",
        "short",
        {
            "title": "Amazon PPC leak",
            "hook": "Stop scaling this campaign",
            "voiceover": "Approved NotebookLM text.",
        },
    )
    storage.update_script_status(record.user_id, record.id, "approved")
    return create_format_job(storage, record.user_id, record.id, "all")


def test_submit_format_job_sends_all_turan_inputs(tmp_path):
    job = make_approved_job(tmp_path)
    client = FakeTuranClient()

    result = submit_format_job(job, client, "42")

    assert result.status == "submitted"
    assert result.external_task_id == "1,2,3,4"
    assert len(client.payloads) == 4
    assert client.payloads[0][1]["source_url"] == f"notebooklm-script://{job.script_id}"
    assert client.payloads[0][1]["script_text"] == "Approved NotebookLM text."

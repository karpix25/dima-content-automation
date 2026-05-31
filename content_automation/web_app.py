from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import load_settings
from .storage import Storage
from .turan_client import TuranApiClient, submit_format_job
from .turan_formats import list_turan_formats
from .turan_service import TuranServiceError, create_format_job, list_approved_scripts
from .web_models import CreateFormatJobIn, FormatJobOut, FormatOut, ScriptOut
from .web_serializers import format_to_out, job_to_out, script_to_out


settings = load_settings()
storage = Storage(settings.data_dir / "content_automation.sqlite3")
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


@app.get("/api/format-jobs/{job_id}", response_model=FormatJobOut)
def format_job(job_id: int, user_id: str = Query(..., min_length=1)) -> FormatJobOut:
    job = storage.get_format_job(user_id, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Format job not found")
    return job_to_out(job)


@app.post("/api/scripts/{script_id}/format-jobs", response_model=FormatJobOut)
def create_script_format_job(script_id: int, payload: CreateFormatJobIn) -> FormatJobOut:
    try:
        job = create_format_job(storage, payload.user_id, script_id, payload.format_key)
    except TuranServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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

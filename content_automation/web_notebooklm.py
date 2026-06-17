from __future__ import annotations

from fastapi import APIRouter, Query

from .notebooklm_health import NotebookLMHealthStatus, NotebookLMKeepAlive


def build_notebooklm_router(keepalive: NotebookLMKeepAlive) -> APIRouter:
    router = APIRouter()

    @router.get("/api/notebooklm/status")
    async def notebooklm_status(check: bool = Query(False)) -> dict[str, object]:
        if check:
            status = await keepalive.run_once()
            return status.to_dict()
        if keepalive.last_status:
            return keepalive.last_status.to_dict()
        return NotebookLMHealthStatus(
            ok=False,
            status="not_checked",
            checked_at="",
            message="NotebookLM has not been checked yet.",
        ).to_dict()

    return router

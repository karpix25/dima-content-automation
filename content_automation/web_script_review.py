from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from .storage import Storage
from .web_models import ScriptOut, ScriptReviewIn
from .web_serializers import script_to_out

REVIEWABLE_STATUSES = {"pending"}
REVIEW_ACTIONS = {"approve": "approved", "reject": "rejected"}
DELETABLE_STATUSES = {"pending", "approved", "used_for_video", "rejected"}


def build_script_review_router(*, storage: Storage) -> APIRouter:
    router = APIRouter()

    @router.get("/api/scripts/review", response_model=list[ScriptOut])
    def review_scripts(
        user_id: str = Query(..., min_length=1),
        limit: int = Query(20, ge=1, le=50),
    ) -> list[ScriptOut]:
        records = storage.list_scripts(user_id, format="short", status="pending", limit=limit)
        return [script_to_out(item) for item in records]

    @router.post("/api/scripts/{script_id}/review", response_model=ScriptOut)
    def review_script(script_id: int, payload: ScriptReviewIn) -> ScriptOut:
        next_status = REVIEW_ACTIONS.get(payload.action)
        if not next_status:
            raise HTTPException(status_code=400, detail="Некорректное действие.")
        record = storage.get_script(payload.user_id, script_id)
        if not record:
            raise HTTPException(status_code=404, detail="Сценарий не найден.")
        if record.status not in REVIEWABLE_STATUSES:
            raise HTTPException(status_code=400, detail="Этот сценарий уже обработан.")
        updated = storage.update_script_status(payload.user_id, script_id, next_status)
        if not updated:
            raise HTTPException(status_code=404, detail="Сценарий не найден.")
        return script_to_out(updated)

    @router.delete("/api/scripts/{script_id}", response_model=ScriptOut)
    def delete_script(script_id: int, payload: ScriptReviewIn) -> ScriptOut:
        record = storage.get_script(payload.user_id, script_id)
        if not record:
            raise HTTPException(status_code=404, detail="Сценарий не найден.")
        if record.status not in DELETABLE_STATUSES:
            raise HTTPException(status_code=400, detail="Этот сценарий уже удален.")
        updated = storage.update_script_status(payload.user_id, script_id, "deleted")
        if not updated:
            raise HTTPException(status_code=404, detail="Сценарий не найден.")
        return script_to_out(updated)

    return router

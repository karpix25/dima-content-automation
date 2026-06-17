from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query

from .config import Settings
from .idea_bank import ContentIdea, IdeaBank
from .notebooklm_ideas import generate_notebooklm_ideas
from .notebooklm_runtime import NotebookLMAskClient
from .settings_service import get_user_settings
from .storage import Storage
from .web_models import ContentIdeaOut, GenerateIdeasIn, GenerateIdeasOut


def build_ideas_router(
    *,
    storage: Storage,
    idea_bank: IdeaBank,
    settings: Settings,
    notebooklm: NotebookLMAskClient,
) -> APIRouter:
    router = APIRouter()

    @router.get("/api/ideas", response_model=list[ContentIdeaOut])
    def ideas(user_id: str = Query(..., min_length=1), limit: int = Query(20, ge=1, le=100)) -> list[ContentIdeaOut]:
        return [idea_to_out(item) for item in idea_bank.list_new(user_id, limit=limit)]

    @router.post("/api/ideas/notebooklm", response_model=GenerateIdeasOut)
    async def notebooklm_ideas(payload: GenerateIdeasIn) -> GenerateIdeasOut:
        state = get_user_settings(storage, settings, payload.user_id)
        notebook_ref = state.notebook_id or settings.default_notebook_id
        if not notebook_ref:
            raise HTTPException(status_code=400, detail="Сначала задай NotebookLM ID в настройках.")
        try:
            inserted = await generate_notebooklm_ideas(
                user_id=payload.user_id,
                notebook_ref=notebook_ref,
                notebooklm=notebooklm,
                idea_bank=idea_bank,
                count=payload.count,
                content_language=state.content_language,
                offer_context=state.offer_context,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return GenerateIdeasOut(inserted=len(inserted), ideas=[idea_to_out(item) for item in inserted])

    return router


def idea_to_out(idea: ContentIdea) -> ContentIdeaOut:
    return ContentIdeaOut.model_validate(asdict(idea))

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query

from .config import Settings
from .idea_bank import ContentIdea, IdeaBank
from .notebooklm_content_plan import generate_notebooklm_content_plan
from .notebooklm_ideas import generate_notebooklm_ideas
from .notebooklm_idea_scripts import create_script_from_idea
from .notebooklm_runtime import NotebookLMAskClient
from .settings_service import get_user_settings
from .storage import Storage
from .web_models import ContentIdeaOut, GenerateIdeasIn, GenerateIdeasOut, ScriptOut
from .web_serializers import script_to_out


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

    @router.post("/api/ideas/notebooklm-plan", response_model=GenerateIdeasOut)
    async def notebooklm_content_plan(payload: GenerateIdeasIn) -> GenerateIdeasOut:
        inserted = await generate_plan(payload, extension=False)
        return GenerateIdeasOut(inserted=len(inserted), ideas=[idea_to_out(item) for item in inserted])

    @router.post("/api/ideas/notebooklm-plan/extend", response_model=GenerateIdeasOut)
    async def extend_notebooklm_content_plan(payload: GenerateIdeasIn) -> GenerateIdeasOut:
        inserted = await generate_plan(payload, extension=True)
        return GenerateIdeasOut(inserted=len(inserted), ideas=[idea_to_out(item) for item in inserted])

    async def generate_plan(payload: GenerateIdeasIn, *, extension: bool) -> list[ContentIdea]:
        state = get_user_settings(storage, settings, payload.user_id)
        notebook_ref = state.notebook_id or settings.default_notebook_id
        if not notebook_ref:
            raise HTTPException(status_code=400, detail="Сначала задай NotebookLM ID в настройках.")
        existing_ideas = idea_bank.list_new(payload.user_id, limit=100)
        try:
            return await generate_notebooklm_content_plan(
                user_id=payload.user_id,
                notebook_ref=notebook_ref,
                notebooklm=notebooklm,
                idea_bank=idea_bank,
                count=payload.count,
                content_language=state.content_language,
                offer_context=state.offer_context,
                existing_ideas=existing_ideas,
                extension=extension,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/api/ideas/{idea_id}/reject", response_model=ContentIdeaOut)
    def reject_idea(idea_id: int, payload: GenerateIdeasIn) -> ContentIdeaOut:
        idea = idea_bank.update_status(payload.user_id, idea_id, "rejected")
        if not idea:
            raise HTTPException(status_code=404, detail="Тема не найдена.")
        return idea_to_out(idea)

    @router.post("/api/ideas/{idea_id}/script", response_model=ScriptOut)
    async def script_from_idea(idea_id: int, payload: GenerateIdeasIn) -> ScriptOut:
        state = get_user_settings(storage, settings, payload.user_id)
        notebook_ref = state.notebook_id or settings.default_notebook_id
        if not notebook_ref:
            raise HTTPException(status_code=400, detail="Сначала задай NotebookLM ID в настройках.")
        idea = idea_bank.get(payload.user_id, idea_id)
        if not idea or idea.status != "new":
            raise HTTPException(status_code=404, detail="Тема не найдена или уже обработана.")
        try:
            record = await create_script_from_idea(
                storage=storage,
                user_id=payload.user_id,
                idea=idea,
                notebook_ref=notebook_ref,
                notebooklm=notebooklm,
                author_style=state.author_style,
                offer_context=state.offer_context,
                cta_mix=state.cta_mix,
                content_language=state.content_language,
                vertical_duration_mode=state.vertical_avatar_duration_mode,
            )
            idea_bank.update_status(payload.user_id, idea_id, "used_for_script")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return script_to_out(record)

    return router


def idea_to_out(idea: ContentIdea) -> ContentIdeaOut:
    return ContentIdeaOut.model_validate(asdict(idea))

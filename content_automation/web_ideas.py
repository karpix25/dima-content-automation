from __future__ import annotations

import logging
from dataclasses import asdict

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from .config import Settings
from .idea_bank import ContentIdea, IdeaBank
from .notebooklm_content_plan import generate_notebooklm_content_plan
from .notebooklm_ideas import generate_notebooklm_ideas
from .notebooklm_idea_scripts import create_script_from_idea
from .notebooklm_runtime import NotebookLMAskClient
from .kie_script_writer import build_kie_text_client
from .settings_service import get_user_settings
from .storage import Storage
from .web_models import AutoIdeaScriptsOut, ContentIdeaOut, GenerateIdeasIn, GenerateIdeasOut, ScriptOut
from .web_serializers import script_to_out

logger = logging.getLogger(__name__)


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
        inserted, message = await generate_plan(payload, extension=False)
        return GenerateIdeasOut(inserted=len(inserted), ideas=[idea_to_out(item) for item in inserted], message=message)

    @router.post("/api/ideas/notebooklm-plan/extend", response_model=GenerateIdeasOut)
    async def extend_notebooklm_content_plan(payload: GenerateIdeasIn) -> GenerateIdeasOut:
        inserted, message = await generate_plan(payload, extension=True)
        return GenerateIdeasOut(inserted=len(inserted), ideas=[idea_to_out(item) for item in inserted], message=message)

    async def generate_plan(payload: GenerateIdeasIn, *, extension: bool) -> tuple[list[ContentIdea], str]:
        state = get_user_settings(storage, settings, payload.user_id)
        notebook_ref = state.notebook_id or settings.default_notebook_id
        if not notebook_ref:
            raise HTTPException(status_code=400, detail="Сначала задай NotebookLM ID в настройках.")
        existing_ideas = idea_bank.list_new(payload.user_id, limit=100)
        existing_ids = {idea.id for idea in existing_ideas}
        try:
            inserted = await generate_notebooklm_content_plan(
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
            return inserted, f"Готово: добавлено {len(inserted)} тем."
        except Exception as exc:
            partial = [idea for idea in idea_bank.list_new(payload.user_id, limit=100) if idea.id not in existing_ids]
            if partial:
                logger.warning(
                    "NotebookLM plan partially generated: user=%s inserted=%s requested=%s error=%s",
                    payload.user_id,
                    len(partial),
                    payload.count,
                    exc,
                )
                message = f"Добавлено {len(partial)} из {payload.count} тем. NotebookLM остановился: {exc}"
                return partial, message
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
                script_writer_backend=settings.script_writer_backend,
                kie_text_client=build_kie_text_client(settings),
            )
            idea_bank.update_status(payload.user_id, idea_id, "used_for_script")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return script_to_out(record)

    @router.post("/api/ideas/scripts/auto", response_model=AutoIdeaScriptsOut)
    def auto_scripts_from_ideas(payload: GenerateIdeasIn, background_tasks: BackgroundTasks) -> AutoIdeaScriptsOut:
        state = get_user_settings(storage, settings, payload.user_id)
        notebook_ref = state.notebook_id or settings.default_notebook_id
        if not notebook_ref:
            raise HTTPException(status_code=400, detail="Сначала задай NotebookLM ID в настройках.")
        reserved = reserve_new_ideas(idea_bank, payload.user_id, limit=payload.count)
        if reserved:
            background_tasks.add_task(
                create_scripts_for_reserved_ideas,
                storage=storage,
                idea_bank=idea_bank,
                user_id=payload.user_id,
                idea_ids=[idea.id for idea in reserved],
                notebook_ref=notebook_ref,
                notebooklm=notebooklm,
                author_style=state.author_style,
                offer_context=state.offer_context,
                cta_mix=state.cta_mix,
                content_language=state.content_language,
                vertical_duration_mode=state.vertical_avatar_duration_mode,
                script_writer_backend=settings.script_writer_backend,
                kie_text_client=build_kie_text_client(settings),
            )
        return AutoIdeaScriptsOut(
            accepted=len(reserved),
            message=f"Запустил написание сценариев: {len(reserved)}",
        )

    return router


def idea_to_out(idea: ContentIdea) -> ContentIdeaOut:
    return ContentIdeaOut.model_validate(asdict(idea))


def reserve_new_ideas(idea_bank: IdeaBank, user_id: str, *, limit: int) -> list[ContentIdea]:
    reserved: list[ContentIdea] = []
    for idea in idea_bank.list_new(user_id, limit=limit):
        updated = idea_bank.update_status(user_id, idea.id, "selected")
        if updated:
            reserved.append(updated)
    return reserved


async def create_scripts_for_reserved_ideas(
    *,
    storage: Storage,
    idea_bank: IdeaBank,
    user_id: str,
    idea_ids: list[int],
    notebook_ref: str,
    notebooklm: NotebookLMAskClient,
    author_style: str,
    offer_context: str,
    cta_mix: str,
    content_language: str,
    vertical_duration_mode: str,
    script_writer_backend: str,
    kie_text_client,
) -> None:
    for idea_id in idea_ids:
        idea = idea_bank.get(user_id, idea_id)
        if not idea or idea.status != "selected":
            continue
        try:
            await create_script_from_idea(
                storage=storage,
                user_id=user_id,
                idea=idea,
                notebook_ref=notebook_ref,
                notebooklm=notebooklm,
                author_style=author_style,
                offer_context=offer_context,
                cta_mix=cta_mix,
                content_language=content_language,
                vertical_duration_mode=vertical_duration_mode,
                script_writer_backend=script_writer_backend,
                kie_text_client=kie_text_client,
            )
            idea_bank.update_status(user_id, idea_id, "used_for_script")
        except Exception:
            logger.exception("Failed to auto-create script from idea: user=%s idea_id=%s", user_id, idea_id)
            idea_bank.update_status(user_id, idea_id, "new")

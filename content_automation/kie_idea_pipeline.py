from __future__ import annotations

import logging
from typing import Any

from .idea_bank import ContentIdea, IdeaBank
from .kie_script_writer import build_kie_text_client
from .notebooklm_idea_scripts import create_script_from_idea
from .notebooklm_ideas import generate_notebooklm_ideas
from .notebooklm_runtime import NotebookLMAskClient
from .storage import ScriptRecord, Storage

logger = logging.getLogger(__name__)


async def generate_short_scripts_with_kie(
    *,
    storage: Storage,
    idea_bank: IdeaBank,
    settings: Any,
    notebooklm: NotebookLMAskClient,
    user_id: str,
    notebook_ref: str,
    count: int,
    author_style: str,
    offer_context: str,
    cta_mix: str,
    content_language: str,
    vertical_duration_mode: str,
) -> list[ScriptRecord]:
    client = build_kie_text_client(settings)
    if not client.is_configured():
        return []
    ideas = await generate_notebooklm_ideas(
        user_id=user_id,
        notebook_ref=notebook_ref,
        notebooklm=notebooklm,
        idea_bank=idea_bank,
        count=count,
        content_language=content_language,
        offer_context=offer_context,
    )
    return await create_scripts_from_ideas_with_kie(
        storage=storage,
        idea_bank=idea_bank,
        user_id=user_id,
        ideas=ideas,
        author_style=author_style,
        offer_context=offer_context,
        cta_mix=cta_mix,
        content_language=content_language,
        vertical_duration_mode=vertical_duration_mode,
        settings=settings,
        notebook_ref=notebook_ref,
        notebooklm=notebooklm,
    )


async def create_scripts_from_ideas_with_kie(
    *,
    storage: Storage,
    idea_bank: IdeaBank,
    user_id: str,
    ideas: list[ContentIdea],
    author_style: str,
    offer_context: str,
    cta_mix: str,
    content_language: str,
    vertical_duration_mode: str,
    settings: Any,
    notebook_ref: str,
    notebooklm: NotebookLMAskClient,
) -> list[ScriptRecord]:
    client = build_kie_text_client(settings)
    records: list[ScriptRecord] = []
    for idea in ideas:
        if not client.is_configured():
            break
        try:
            record = await create_script_from_idea(
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
                script_writer_backend="kie",
                kie_text_client=client,
            )
        except Exception:
            logger.exception("Kie failed to write script from idea: user=%s idea_id=%s", user_id, idea.id)
            continue
        records.append(record)
        idea_bank.update_status(user_id, idea.id, "used_for_script")
    return records

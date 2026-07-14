from __future__ import annotations

import asyncio
import logging
import re

from .content_language import normalize_content_language
from .idea_bank import ContentIdea
from .idea_cards import idea_to_topic_hint
from .kie_script_writer import write_script_with_kie
from .kie_text import KieTextClient, KieTextError
from .notebooklm import as_script_list, extract_json
from .notebooklm_mcp import notebook_ref_to_url
from .notebooklm_runtime import NotebookLMAskClient
from .prompts import build_short_scripts_prompt
from .script_length import DEFAULT_SPOKEN_WORDS_PER_MINUTE, vertical_word_budget
from .storage import DuplicateScriptError, ScriptRecord, Storage

logger = logging.getLogger(__name__)

MAX_KIE_SCRIPT_ATTEMPTS = 4


async def create_script_from_idea(
    *,
    storage: Storage,
    user_id: str,
    idea: ContentIdea,
    notebook_ref: str,
    notebooklm: NotebookLMAskClient,
    author_style: str,
    offer_context: str,
    cta_mix: str,
    content_language: str,
    vertical_duration_mode: str,
    script_writer_backend: str = "notebooklm",
    kie_text_client: KieTextClient | None = None,
) -> ScriptRecord:
    budget = vertical_word_budget(vertical_duration_mode, wpm=DEFAULT_SPOKEN_WORDS_PER_MINUTE)
    if script_writer_backend == "kie":
        if not kie_text_client or not kie_text_client.is_configured():
            raise ValueError("KIE script writer is selected, but KIE text client is not configured.")
        revision_instruction: str | None = None
        last_error: Exception | None = None
        for attempt in range(1, MAX_KIE_SCRIPT_ATTEMPTS + 1):
            try:
                item = write_script_with_kie(
                    client=kie_text_client,
                    idea=idea,
                    author_style=author_style,
                    offer_context=offer_context,
                    cta_mix=cta_mix,
                    content_language=content_language,
                    word_budget=budget,
                    revision_instruction=revision_instruction,
                )
                if not script_payload_matches_word_budget(item, budget):
                    raise ValueError("Kie написал сценарий вне нужной длины озвучки.")
                return storage.add_script(
                    user_id,
                    "short",
                    item,
                    enforce_unique=True,
                    unique_kinds=("hook", "voiceover"),
                )
            except KieTextError as exc:
                raise ValueError(f"KIE не смог написать сценарий: {exc}") from exc
            except DuplicateScriptError as exc:
                last_error = exc
                revision_instruction = (
                    "The previous draft duplicated an existing unique script key. "
                    "Write a fresh hook, title, topic_fingerprint, and opening angle that do not resemble prior drafts."
                )
            except ValueError as exc:
                last_error = exc
                revision_instruction = (
                    f"The previous draft failed validation: {exc}. "
                    f"Rewrite the voiceover to fit {budget.min_words}-{budget.max_words} spoken words and keep all fields unique."
                )
            logger.info("Retrying KIE script writer: idea_id=%s attempt=%s", idea.id, attempt + 1)
        raise ValueError(f"KIE не смог написать сценарий: {last_error}") from last_error

    prompt = build_short_scripts_prompt(
        count=1,
        author_style=author_style,
        offer_context=offer_context,
        cta_mix=cta_mix,
        topic_hint=idea_to_topic_hint(idea),
        exclusion_context=None,
        editorial_briefs=[],
        word_budget=budget,
        content_language=content_language,
    )
    result = await asyncio.to_thread(notebooklm.ask, prompt, notebook_url=notebook_ref_to_url(notebook_ref))
    answer = str(getattr(result, "answer", result) or "")
    payload = extract_json(answer)
    reject_cyrillic = normalize_content_language(content_language) == "en"

    for item in as_script_list(payload):
        if reject_cyrillic and script_payload_has_cyrillic(item):
            continue
        if not script_payload_matches_word_budget(item, budget):
            continue
        try:
            return storage.add_script(user_id, "short", item, enforce_unique=True)
        except DuplicateScriptError:
            continue
    raise ValueError("NotebookLM не вернул подходящий сценарий по этой теме.")


CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")


def script_payload_has_cyrillic(payload: dict[str, object]) -> bool:
    fields = ("title", "angle", "hook", "trigger", "voiceover", "cta", "why_it_works", "source_basis")
    return any(CYRILLIC_RE.search(str(payload.get(field) or "")) for field in fields)


def script_payload_matches_word_budget(payload: dict[str, object], budget) -> bool:
    from .script_length import count_spoken_words

    words = count_spoken_words(str(payload.get("voiceover") or ""))
    return budget.min_words <= words <= budget.max_words

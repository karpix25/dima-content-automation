from __future__ import annotations

import logging
import re
from dataclasses import replace

from .config import Settings
from .elevenlabs_mcp import ElevenLabsMCPClient
from .kie_text import KieTextClient, KieTextConfig, KieTextError
from .script_length import WordBudget
from .storage import ScriptRecord, Storage
from .voice_char_profile import (
    calibrate_voice_chars_per_second,
    calibrated_voice_chars_per_second,
    has_voice_chars_profile,
)

logger = logging.getLogger(__name__)


def fit_voiceover_for_duration(
    *,
    record: ScriptRecord,
    user_id: str,
    settings: Settings,
    storage: Storage,
    voice_id: str | None,
    voice_name: str | None,
    word_budget: WordBudget,
    elevenlabs: ElevenLabsMCPClient,
) -> ScriptRecord:
    if not word_budget.target_seconds:
        return record
    cps = _voice_chars_per_second(
        storage=storage,
        user_id=user_id,
        voice_id=voice_id,
        voice_name=voice_name,
        settings=settings,
        elevenlabs=elevenlabs,
    )
    target_chars = round(cps * word_budget.target_seconds)
    if _within_tolerance(record.voiceover, target_chars):
        return record
    client = KieTextClient(
        KieTextConfig(
            api_key=settings.kie_api_key,
            base_url=settings.kie_base_url,
            model=settings.kie_text_model,
            timeout_seconds=settings.kie_text_timeout_seconds,
        )
    )
    if not client.is_configured():
        logger.warning("KIE_API_KEY is missing; using original voiceover for script %s", record.id)
        return record
    try:
        rewritten = _rewrite_voiceover(client, record=record, target_chars=target_chars)
    except KieTextError:
        logger.exception("KIE voiceover rewrite failed; using original voiceover for script %s", record.id)
        return record
    if not rewritten:
        return record
    logger.info(
        "Voiceover fitted by chars: script=%s original_chars=%s target_chars=%s fitted_chars=%s",
        record.id,
        len(record.voiceover),
        target_chars,
        len(rewritten),
    )
    return replace(record, voiceover=rewritten)


def _voice_chars_per_second(
    *,
    storage: Storage,
    user_id: str,
    voice_id: str | None,
    voice_name: str | None,
    settings: Settings,
    elevenlabs: ElevenLabsMCPClient,
) -> float:
    if has_voice_chars_profile(storage, user_id, voice_id):
        return calibrated_voice_chars_per_second(storage, user_id, voice_id)
    return calibrate_voice_chars_per_second(
        storage=storage,
        user_id=user_id,
        voice_id=voice_id,
        voice_name=voice_name,
        elevenlabs=elevenlabs,
        model_id=settings.elevenlabs_model_id,
        speed=settings.elevenlabs_speed,
        stability=settings.elevenlabs_stability,
        similarity_boost=settings.elevenlabs_similarity_boost,
        style=settings.elevenlabs_style,
        language=settings.elevenlabs_language,
    )


def _rewrite_voiceover(client: KieTextClient, *, record: ScriptRecord, target_chars: int) -> str:
    system = (
        "You are a senior social-video script editor. Rewrite voiceover text to fit timing exactly. "
        "Preserve the original language, meaning, offer, claims, and natural spoken rhythm. "
        "Return only the final voiceover text, no markdown, no notes."
    )
    user = "\n".join(
        [
            f"Target length: {target_chars} characters, acceptable range {round(target_chars * 0.95)}-{round(target_chars * 1.05)}.",
            "Keep the same language as the original voiceover.",
            "Use concise, spoken sentences. Do not add unsupported facts.",
            f"Title: {record.title}",
            f"Hook: {record.hook}",
            f"CTA: {record.cta}",
            "Original voiceover:",
            record.voiceover,
        ]
    )
    return _clean_voiceover(client.complete(system=system, user=user))


def _clean_voiceover(value: str) -> str:
    text = re.sub(r"^```(?:text)?|```$", "", value.strip(), flags=re.IGNORECASE | re.MULTILINE).strip()
    text = re.sub(r"^(final voiceover|voiceover|озвучка)\s*:\s*", "", text, flags=re.IGNORECASE).strip()
    return " ".join(text.split())


def _within_tolerance(text: str, target_chars: int) -> bool:
    if target_chars <= 0:
        return True
    return round(target_chars * 0.95) <= len(text or "") <= round(target_chars * 1.05)

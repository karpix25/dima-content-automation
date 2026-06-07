from __future__ import annotations

import hashlib
from typing import Any

from .topic_dedupe import normalize_for_similarity, script_topic_fingerprint


def unique_script_keys(payload: dict[str, Any], normalized: dict[str, str] | None = None) -> list[tuple[str, str]]:
    data = normalized or {}
    keys: list[tuple[str, str]] = []
    topic = normalize_for_similarity(data.get("topic_fingerprint") or script_topic_fingerprint(payload))
    if topic:
        keys.append(("topic", topic))
    hook = _text_hash(data.get("hook") or payload.get("hook"))
    if hook:
        keys.append(("hook", hook))
    voiceover = _text_hash(data.get("voiceover") or payload.get("voiceover"))
    if voiceover:
        keys.append(("voiceover", voiceover))
    return keys


def _text_hash(value: object) -> str:
    normalized = normalize_for_similarity(str(value or ""))
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

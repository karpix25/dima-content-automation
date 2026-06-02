from __future__ import annotations

import re

_URL_ID_RE = re.compile(r"/videos/([A-Za-z0-9_-]{12,})")
_TOKEN_RE = re.compile(r"\b[A-Za-z0-9_-]{12,}\b")


def extract_heygen_video_id(text: str | None) -> str | None:
    value = (text or "").strip()
    if not value or value.startswith("/"):
        return None

    url_match = _URL_ID_RE.search(value)
    if url_match:
        return url_match.group(1)

    tokens = _TOKEN_RE.findall(value)
    if len(tokens) != 1:
        return None
    token = tokens[0]
    if len(token) < 16:
        return None
    return token


from __future__ import annotations

import re


YOUTUBE_URL_RE = re.compile(
    r"https?://(?:www\.)?(?:youtube\.com/(?:watch\?[^ \n]*v=|shorts/|live/)|youtu\.be/)[^\s<>]+",
    re.IGNORECASE,
)


def extract_youtube_url(text: str | None) -> str | None:
    match = YOUTUBE_URL_RE.search(text or "")
    if not match:
        return None
    return match.group(0).rstrip(").,;!?'\"")

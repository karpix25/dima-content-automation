from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse


VIZARD_URL_RE = re.compile(r"https?://[^\s<>]*vizard[^\s<>]*", re.IGNORECASE)
PROJECT_ID_RE = re.compile(r"^\s*(?:/vizard\s+)?(\d{5,})\s*$", re.IGNORECASE)
VIZARD_TEXT_ID_RE = re.compile(r"\bvizard(?:\s+project)?\s*[:#-]?\s*(\d{5,})\b", re.IGNORECASE)


def extract_vizard_project_id(text: str | None) -> str | None:
    raw = text or ""
    direct_match = PROJECT_ID_RE.match(raw)
    if direct_match:
        return direct_match.group(1)
    text_match = VIZARD_TEXT_ID_RE.search(raw)
    if text_match:
        return text_match.group(1)
    for match in VIZARD_URL_RE.finditer(raw):
        project_id = _project_id_from_url(match.group(0).rstrip(").,;!?'\""))
        if project_id:
            return project_id
    return None


def _project_id_from_url(url: str) -> str | None:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    for key, values in query.items():
        if "project" in key.lower():
            for value in values:
                if value.isdigit() and len(value) >= 5:
                    return value
    parts = [part for part in parsed.path.split("/") if part]
    for index, part in enumerate(parts):
        if part.lower() in {"project", "projects"} and index + 1 < len(parts):
            candidate = _numeric_prefix(parts[index + 1])
            if candidate:
                return candidate
    for part in reversed(parts):
        candidate = _numeric_prefix(part)
        if candidate:
            return candidate
    return None


def _numeric_prefix(value: str) -> str | None:
    match = re.match(r"(\d{5,})", value)
    return match.group(1) if match else None

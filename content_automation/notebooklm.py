from __future__ import annotations

import json
import re
import subprocess
from typing import Any


class NotebookLMClient:
    def __init__(self, command: str = "notebooklm", timeout_seconds: int = 240):
        self.command = command
        self.timeout_seconds = timeout_seconds

    def ask(self, notebook_id: str, question: str) -> str:
        notebook = (notebook_id or "").strip()
        if not notebook:
            raise ValueError("NotebookLM notebook id is required")

        result = subprocess.run(
            [self.command, "chat", "ask", notebook, question],
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if result.returncode != 0:
            error = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(f"NotebookLM CLI failed: {error[:1200]}")

        output = (result.stdout or "").strip()
        if not output:
            raise RuntimeError("NotebookLM returned an empty response")
        return output


def extract_json(text: str) -> Any:
    raw = (text or "").strip()
    if not raw:
        raise ValueError("empty response")

    fenced = re.search(r"```(?:json)?\s*(.*?)```", raw, flags=re.DOTALL | re.IGNORECASE)
    candidate = fenced.group(1).strip() if fenced else raw

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(candidate):
        if char not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(candidate[index:])
        except json.JSONDecodeError:
            continue
        return value

    raise ValueError("response does not contain valid JSON")


def as_script_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        items = payload.get("scripts") or payload.get("items") or payload.get("ideas") or []
    else:
        items = payload
    if not isinstance(items, list):
        raise ValueError("JSON payload must be a list or contain scripts/items")
    return [item for item in items if isinstance(item, dict)]

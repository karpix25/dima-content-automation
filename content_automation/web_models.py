from __future__ import annotations

from pydantic import BaseModel


class FormatOut(BaseModel):
    key: str
    label: str
    task_type: str
    description: str


class ScriptOut(BaseModel):
    id: int
    title: str
    hook: str
    trigger: str
    voiceover: str
    cta: str
    source_basis: str


class CreateFormatJobIn(BaseModel):
    user_id: str
    format_key: str


class FormatJobOut(BaseModel):
    id: int
    script_id: int
    format_key: str
    task_type: str
    title: str
    status: str
    output_text: str
    output_url: str | None = None
    external_task_id: str | None = None
    error: str | None = None
    raw: dict
    created_at: str
    updated_at: str

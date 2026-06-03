from __future__ import annotations

from .editorial import script_editorial_summary
from .storage import FormatJob, ScriptRecord
from .turan_formats import TuranFormat
from .web_models import FormatJobOut, FormatOut, ScriptOut


def format_to_out(item: TuranFormat) -> FormatOut:
    return FormatOut(
        key=item.key,
        label=item.label,
        task_type=item.task_type,
        description=item.description,
    )


def script_to_out(record: ScriptRecord) -> ScriptOut:
    raw = record.raw or {}
    return ScriptOut(
        id=record.id,
        title=record.title,
        hook=record.hook,
        trigger=record.trigger,
        voiceover=record.voiceover,
        cta=record.cta,
        source_basis=record.source_basis,
        editorial_summary=script_editorial_summary(raw),
        content_format=str(raw.get("content_format") or ""),
        content_pillar=str(raw.get("content_pillar") or ""),
        proof_type=str(raw.get("proof_type") or ""),
        emotion_angle=str(raw.get("emotion_angle") or ""),
        series_name=str(raw.get("series_name") or ""),
    )


def job_to_out(job: FormatJob) -> FormatJobOut:
    return FormatJobOut(
        id=job.id,
        script_id=job.script_id,
        format_key=job.format_key,
        task_type=job.task_type,
        title=job.title,
        status=job.status,
        output_text=job.output_text,
        output_url=job.output_url,
        external_task_id=job.external_task_id,
        error=job.error,
        raw=job.raw,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )

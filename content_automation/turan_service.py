from __future__ import annotations

import json

from .storage import FormatJob, ScriptRecord, Storage
from .turan_formats import build_all_turan_packages, build_turan_package, get_turan_format
from .turan_payloads import build_structured_payload


class TuranServiceError(ValueError):
    pass


def list_approved_scripts(storage: Storage, user_id: str, *, limit: int = 50) -> list[ScriptRecord]:
    return storage.list_approved_scripts(user_id, limit=limit)


def create_format_job(storage: Storage, user_id: str, script_id: int, format_key: str) -> FormatJob:
    record = storage.get_script(user_id, script_id)
    if not record:
        raise TuranServiceError("Script not found")
    if record.status != "approved":
        raise TuranServiceError("Only approved scripts can be formatted")

    normalized_format_key = (format_key or "").strip()
    if normalized_format_key == "all":
        payloads = [build_structured_payload(record, item) for item in _all_specs()]
        output_text = _with_input_json(
            build_all_turan_packages(record),
            {"formats": [item["turan_task_input"] for item in payloads]},
        )
        return storage.add_format_job(
            user_id,
            script_id=record.id,
            format_key="all",
            task_type="turan_bundle",
            title=f"All Turan formats: {record.title or record.hook or f'Script #{record.id}'}",
            output_text=output_text,
            raw={"formats": payloads},
        )

    spec = get_turan_format(normalized_format_key)
    if not spec:
        raise TuranServiceError("Unknown Turan format")

    raw = build_structured_payload(record, spec)
    output_text = _with_input_json(build_turan_package(record, format_key), raw["turan_task_input"])
    return storage.add_format_job(
        user_id,
        script_id=record.id,
        format_key=spec.key,
        task_type=spec.task_type,
        title=f"{spec.label}: {record.title or record.hook or f'Script #{record.id}'}",
        output_text=output_text,
        raw=raw,
    )


def _all_specs():
    from .turan_formats import list_turan_formats

    return list_turan_formats()


def _with_input_json(package_text: str, payload: object) -> str:
    return (
        f"{package_text.strip()}\n\n"
        "Turan text-source input JSON:\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )

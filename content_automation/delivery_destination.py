from __future__ import annotations

from .storage import Storage


def telegram_delivery_chat_id(storage: Storage | None, project_user_id: str, actor_user_id: str | None = None) -> str:
    actor = (actor_user_id or "").strip()
    if actor:
        return actor
    if not storage:
        return project_user_id
    return storage.get_setting(project_user_id, "active_chat_id") or project_user_id

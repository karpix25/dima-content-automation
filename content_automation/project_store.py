from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PROJECT_ROLES = {"owner", "manager", "editor", "viewer"}
MANAGE_MEMBER_ROLES = {"owner"}


@dataclass(frozen=True)
class ProjectMembership:
    project_user_id: str
    member_user_id: str
    role: str
    created_at: str
    updated_at: str


class ProjectAccessError(RuntimeError):
    pass


class ProjectStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS project_members (
                    project_user_id TEXT NOT NULL,
                    member_user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (project_user_id, member_user_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS project_actor_state (
                    actor_user_id TEXT PRIMARY KEY,
                    active_project_user_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def ensure_default_project(self, user_id: str) -> ProjectMembership:
        user_id = _clean_id(user_id)
        if not user_id:
            raise ProjectAccessError("Telegram user id is required")
        return self.add_member(user_id, user_id, role="owner", actor_user_id=user_id, bootstrap=True)

    def add_member(
        self,
        project_user_id: str,
        member_user_id: str,
        *,
        role: str = "manager",
        actor_user_id: str | None = None,
        bootstrap: bool = False,
    ) -> ProjectMembership:
        project_user_id = _clean_id(project_user_id)
        member_user_id = _clean_id(member_user_id)
        role = _normalize_role(role)
        if not bootstrap:
            self.require_role(project_user_id, _clean_id(actor_user_id), MANAGE_MEMBER_ROLES)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO project_members (project_user_id, member_user_id, role)
                VALUES (?, ?, ?)
                ON CONFLICT(project_user_id, member_user_id)
                DO UPDATE SET role = excluded.role, updated_at = CURRENT_TIMESTAMP
                """,
                (project_user_id, member_user_id, role),
            )
        membership = self.get_membership(project_user_id, member_user_id)
        if not membership:
            raise RuntimeError("failed to load project membership")
        return membership

    def remove_member(self, project_user_id: str, member_user_id: str, *, actor_user_id: str) -> None:
        project_user_id = _clean_id(project_user_id)
        member_user_id = _clean_id(member_user_id)
        self.require_role(project_user_id, _clean_id(actor_user_id), MANAGE_MEMBER_ROLES)
        if project_user_id == member_user_id:
            raise ProjectAccessError("Project owner cannot be removed")
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM project_members WHERE project_user_id = ? AND member_user_id = ?",
                (project_user_id, member_user_id),
            )

    def list_projects_for_user(self, actor_user_id: str) -> list[ProjectMembership]:
        actor_user_id = _clean_id(actor_user_id)
        self.ensure_default_project(actor_user_id)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM project_members
                WHERE member_user_id = ?
                ORDER BY CASE role WHEN 'owner' THEN 0 WHEN 'manager' THEN 1 WHEN 'editor' THEN 2 ELSE 3 END,
                         project_user_id ASC
                """,
                (actor_user_id,),
            ).fetchall()
        return [_row_to_membership(row) for row in rows]

    def active_project_for_user(self, actor_user_id: str) -> str:
        actor_user_id = _clean_id(actor_user_id)
        self.ensure_default_project(actor_user_id)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT active_project_user_id FROM project_actor_state WHERE actor_user_id = ?",
                (actor_user_id,),
            ).fetchone()
        active = str(row["active_project_user_id"]) if row else ""
        if active and self.is_member(active, actor_user_id):
            return active
        projects = self.list_projects_for_user(actor_user_id)
        shared = next((item.project_user_id for item in projects if item.project_user_id != actor_user_id), "")
        return shared or projects[0].project_user_id

    def set_active_project(self, actor_user_id: str, project_user_id: str) -> str:
        actor_user_id = _clean_id(actor_user_id)
        project_user_id = _clean_id(project_user_id)
        self.require_member(project_user_id, actor_user_id)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO project_actor_state (actor_user_id, active_project_user_id)
                VALUES (?, ?)
                ON CONFLICT(actor_user_id)
                DO UPDATE SET active_project_user_id = excluded.active_project_user_id,
                              updated_at = CURRENT_TIMESTAMP
                """,
                (actor_user_id, project_user_id),
            )
        return project_user_id

    def list_members(self, project_user_id: str, *, actor_user_id: str) -> list[ProjectMembership]:
        project_user_id = _clean_id(project_user_id)
        self.require_member(project_user_id, _clean_id(actor_user_id))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM project_members
                WHERE project_user_id = ?
                ORDER BY CASE role WHEN 'owner' THEN 0 WHEN 'manager' THEN 1 WHEN 'editor' THEN 2 ELSE 3 END,
                         member_user_id ASC
                """,
                (project_user_id,),
            ).fetchall()
        return [_row_to_membership(row) for row in rows]

    def get_membership(self, project_user_id: str, member_user_id: str) -> ProjectMembership | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM project_members WHERE project_user_id = ? AND member_user_id = ?",
                (_clean_id(project_user_id), _clean_id(member_user_id)),
            ).fetchone()
        return _row_to_membership(row) if row else None

    def is_member(self, project_user_id: str, actor_user_id: str) -> bool:
        if _clean_id(project_user_id) == _clean_id(actor_user_id):
            self.ensure_default_project(actor_user_id)
        return self.get_membership(project_user_id, actor_user_id) is not None

    def require_member(self, project_user_id: str, actor_user_id: str) -> ProjectMembership:
        membership = self.get_membership(project_user_id, actor_user_id)
        if not membership:
            raise ProjectAccessError("No access to this project")
        return membership

    def require_role(self, project_user_id: str, actor_user_id: str | None, roles: Iterable[str]) -> ProjectMembership:
        membership = self.require_member(project_user_id, actor_user_id or "")
        if membership.role not in set(roles):
            raise ProjectAccessError("Not enough permissions for this project")
        return membership


def _normalize_role(role: str) -> str:
    role = (role or "manager").strip().lower()
    if role not in PROJECT_ROLES:
        raise ProjectAccessError(f"Unsupported project role: {role}")
    return role


def _clean_id(value: str | None) -> str:
    return str(value or "").strip()


def _row_to_membership(row: sqlite3.Row) -> ProjectMembership:
    return ProjectMembership(
        project_user_id=str(row["project_user_id"]),
        member_user_id=str(row["member_user_id"]),
        role=str(row["role"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )

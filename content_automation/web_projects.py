from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from .project_store import ProjectAccessError, ProjectMembership, ProjectStore
from .web_models import ActiveProjectIn, AddProjectMemberIn, ProjectMemberOut, ProjectOut


def build_projects_router(project_store: ProjectStore) -> APIRouter:
    router = APIRouter()

    @router.get("/api/projects", response_model=list[ProjectOut])
    def list_projects(user_id: str = Query(..., min_length=1)) -> list[ProjectOut]:
        projects = project_store.list_projects_for_user(user_id)
        active = project_store.active_project_for_user(user_id)
        return [project_to_out(item, active_project_id=active) for item in projects]

    @router.post("/api/projects/active", response_model=ProjectOut)
    def set_active_project(payload: ActiveProjectIn) -> ProjectOut:
        try:
            active = project_store.set_active_project(payload.user_id, payload.project_id)
            membership = project_store.require_member(active, payload.user_id)
        except ProjectAccessError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        return project_to_out(membership, active_project_id=active)

    @router.get("/api/projects/{project_id}/members", response_model=list[ProjectMemberOut])
    def list_members(project_id: str, user_id: str = Query(..., min_length=1)) -> list[ProjectMemberOut]:
        try:
            members = project_store.list_members(project_id, actor_user_id=user_id)
        except ProjectAccessError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        return [member_to_out(item) for item in members]

    @router.post("/api/projects/members", response_model=ProjectMemberOut)
    def add_member(payload: AddProjectMemberIn) -> ProjectMemberOut:
        try:
            member = project_store.add_member(
                payload.project_id,
                payload.member_user_id,
                role=payload.role,
                actor_user_id=payload.user_id,
            )
        except ProjectAccessError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        return member_to_out(member)

    @router.delete("/api/projects/{project_id}/members/{member_user_id}", response_model=dict[str, str])
    def remove_member(project_id: str, member_user_id: str, user_id: str = Query(..., min_length=1)) -> dict[str, str]:
        try:
            project_store.remove_member(project_id, member_user_id, actor_user_id=user_id)
        except ProjectAccessError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        return {"status": "removed"}

    return router


def project_to_out(item: ProjectMembership, *, active_project_id: str) -> ProjectOut:
    return ProjectOut(
        project_id=item.project_user_id,
        member_user_id=item.member_user_id,
        role=item.role,
        is_active=item.project_user_id == active_project_id,
    )


def member_to_out(item: ProjectMembership) -> ProjectMemberOut:
    return ProjectMemberOut(
        project_id=item.project_user_id,
        user_id=item.member_user_id,
        role=item.role,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )

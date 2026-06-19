from content_automation.project_store import ProjectAccessError, ProjectStore


def test_default_project_owner_can_add_member(tmp_path):
    store = ProjectStore(tmp_path / "projects.sqlite3")

    owner = store.ensure_default_project("42")
    member = store.add_member("42", "99", role="manager", actor_user_id="42")

    assert owner.role == "owner"
    assert member.project_user_id == "42"
    assert member.member_user_id == "99"
    assert store.is_member("42", "99")


def test_non_owner_cannot_add_member(tmp_path):
    store = ProjectStore(tmp_path / "projects.sqlite3")
    store.ensure_default_project("42")
    store.add_member("42", "99", role="manager", actor_user_id="42")

    try:
        store.add_member("42", "100", role="viewer", actor_user_id="99")
    except ProjectAccessError as exc:
        assert "permissions" in str(exc)
    else:
        raise AssertionError("manager added a project member")


def test_owner_cannot_be_removed(tmp_path):
    store = ProjectStore(tmp_path / "projects.sqlite3")
    store.ensure_default_project("42")

    try:
        store.remove_member("42", "42", actor_user_id="42")
    except ProjectAccessError as exc:
        assert "owner" in str(exc)
    else:
        raise AssertionError("owner was removed")


def test_active_project_prefers_shared_membership(tmp_path):
    store = ProjectStore(tmp_path / "projects.sqlite3")
    store.ensure_default_project("42")
    store.add_member("42", "99", role="manager", actor_user_id="42")

    assert store.active_project_for_user("99") == "42"
    assert store.set_active_project("99", "99") == "99"
    assert store.active_project_for_user("99") == "99"


def test_projects_endpoint_uses_server_active_project(tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from content_automation.web_projects import build_projects_router

    store = ProjectStore(tmp_path / "projects.sqlite3")
    store.ensure_default_project("42")
    store.add_member("42", "99", role="manager", actor_user_id="42")
    store.set_active_project("99", "42")
    app = FastAPI()
    app.include_router(build_projects_router(store))

    response = TestClient(app).get("/api/projects", params={"user_id": "99", "active_project_id": "99"})

    assert response.status_code == 200
    active = [item["project_id"] for item in response.json() if item["is_active"]]
    assert active == ["42"]

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

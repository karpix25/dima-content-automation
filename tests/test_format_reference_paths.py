from pathlib import Path
from types import SimpleNamespace

from content_automation.format_reference_paths import delivery_face_reference_paths
from content_automation.storage import Storage


def test_delivery_face_reference_paths_falls_back_to_actor(tmp_path: Path):
    storage = Storage(tmp_path / "refs.sqlite3")
    face_path = tmp_path / "manager-face.jpg"
    face_path.write_bytes(b"face")
    storage.set_setting("manager", "vertical_thumbnail_face_path", str(face_path))

    paths = delivery_face_reference_paths(
        storage=storage,
        settings=SimpleNamespace(),
        user_id="project",
        target="vertical",
        delivery_actor_user_id="manager",
    )

    assert paths == [face_path]


def test_delivery_face_reference_paths_prefers_project_face(tmp_path: Path):
    storage = Storage(tmp_path / "refs.sqlite3")
    project_face = tmp_path / "project-face.jpg"
    manager_face = tmp_path / "manager-face.jpg"
    project_face.write_bytes(b"project")
    manager_face.write_bytes(b"manager")
    storage.set_setting("project", "vertical_thumbnail_face_path", str(project_face))
    storage.set_setting("manager", "vertical_thumbnail_face_path", str(manager_face))

    paths = delivery_face_reference_paths(
        storage=storage,
        settings=SimpleNamespace(),
        user_id="project",
        target="vertical",
        delivery_actor_user_id="manager",
    )

    assert paths == [project_face]

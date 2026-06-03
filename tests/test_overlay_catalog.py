from pathlib import Path

from content_automation.overlay_catalog import add_overlay_path, clear_overlay_paths, list_overlay_paths, remove_overlay_path, select_overlay_path
from content_automation.storage import Storage


def test_overlay_catalog_appends_and_selects_stably(tmp_path: Path):
    storage = Storage(tmp_path / "db.sqlite3")
    user_id = "42"
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    first.write_bytes(b"first")
    second.write_bytes(b"second")

    add_overlay_path(storage, user_id, "shorts", first)
    add_overlay_path(storage, user_id, "shorts", second)

    assert list_overlay_paths(storage, user_id, "shorts") == [first, second]
    assert select_overlay_path(storage, user_id, "shorts", seed="same") == select_overlay_path(storage, user_id, "shorts", seed="same")


def test_overlay_catalog_clears_all_paths(tmp_path: Path):
    storage = Storage(tmp_path / "db.sqlite3")
    user_id = "42"
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    add_overlay_path(storage, user_id, "reels", first)
    add_overlay_path(storage, user_id, "reels", second)

    clear_overlay_paths(storage, user_id, "reels")

    assert list_overlay_paths(storage, user_id, "reels") == []
    assert not first.exists()
    assert not second.exists()


def test_overlay_catalog_removes_one_path(tmp_path: Path):
    storage = Storage(tmp_path / "db.sqlite3")
    user_id = "42"
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    add_overlay_path(storage, user_id, "youtube", first)
    add_overlay_path(storage, user_id, "youtube", second)

    remove_overlay_path(storage, user_id, "youtube", 0)

    assert list_overlay_paths(storage, user_id, "youtube") == [second]
    assert not first.exists()
    assert second.exists()

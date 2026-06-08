from pathlib import Path

from content_automation.media_assets import MediaAssetStore
from content_automation.reference_paths import selected_thumbnail_style_reference_paths, thumbnail_style_reference_paths


def test_thumbnail_style_reference_paths_returns_all_matching_targets(tmp_path: Path):
    store = MediaAssetStore(tmp_path / "media.sqlite3")
    vertical = _asset(tmp_path, "vertical.png")
    horizontal = _asset(tmp_path, "horizontal.png")
    both = _asset(tmp_path, "both.png")
    store.add_asset("42", kind="thumbnail_reference", file_path=vertical, file_name=vertical.name, target="vertical")
    store.add_asset("42", kind="thumbnail_reference", file_path=horizontal, file_name=horizontal.name, target="horizontal")
    store.add_asset("42", kind="thumbnail_reference", file_path=both, file_name=both.name, target="both")

    paths = thumbnail_style_reference_paths(asset_store=store, user_id="42", target="vertical")

    assert paths == [both, vertical]


def test_selected_thumbnail_style_reference_paths_uses_one_deterministic_reference(tmp_path: Path):
    store = MediaAssetStore(tmp_path / "media.sqlite3")
    refs = [_asset(tmp_path, f"ref-{index}.png") for index in range(4)]
    for ref in refs:
        store.add_asset("42", kind="thumbnail_reference", file_path=ref, file_name=ref.name, target="vertical")

    first = selected_thumbnail_style_reference_paths(asset_store=store, user_id="42", target="vertical", seed=27)
    second = selected_thumbnail_style_reference_paths(asset_store=store, user_id="42", target="vertical", seed=27)

    assert len(first) == 1
    assert first == second
    assert first[0] in refs


def _asset(tmp_path: Path, name: str) -> Path:
    path = tmp_path / name
    path.write_bytes(b"image")
    return path

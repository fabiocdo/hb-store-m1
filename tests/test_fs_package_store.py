from __future__ import annotations

from pathlib import Path

import pytest

from homebrew_cdn_m1_server.config.settings_loader import SettingsLoader
from homebrew_cdn_m1_server.config.settings_models import AppConfig
from homebrew_cdn_m1_server.application.adapters.repositories.fs_package_store import FsPackageStore


def _make_store(temp_workspace: Path) -> tuple[FsPackageStore, AppConfig]:
    settings = temp_workspace / "configs" / "settings.ini"
    settings.write_text("", encoding="utf-8")
    config = SettingsLoader.load(settings)
    store = FsPackageStore(config.paths)
    return store, config


def test_fs_package_store_given_empty_workspace_when_ensure_layout_then_creates_directories(
    temp_workspace: Path,
):
    store, config = _make_store(temp_workspace)

    store.ensure_layout()

    expected_dirs = (
        config.paths.data_dir,
        config.paths.internal_dir,
        config.paths.share_dir,
        config.paths.hb_store_share_dir,
        config.paths.fpkgi_share_dir,
        config.paths.catalog_dir,
        config.paths.cache_dir,
        config.paths.logs_dir,
        config.paths.errors_dir,
        config.paths.hb_store_update_dir,
        config.paths.pkg_root,
        config.paths.media_dir,
        config.paths.app_dir,
        config.paths.game_dir,
        config.paths.dlc_dir,
        config.paths.pkg_update_dir,
        config.paths.save_dir,
        config.paths.unknown_dir,
    )
    for directory in expected_dirs:
        assert directory.exists() is True
        assert directory.is_dir() is True


def test_fs_package_store_given_init_index_when_ensure_public_index_then_copies_once(
    temp_workspace: Path,
):
    store, config = _make_store(temp_workspace)
    store.ensure_layout()

    source = config.paths.init_dir / "index.html"
    source.write_text("v1", encoding="utf-8")

    store.ensure_public_index(source)
    source.write_text("v2", encoding="utf-8")
    store.ensure_public_index(source)

    assert config.paths.public_index_path.read_text("utf-8") == "v1"


def test_fs_package_store_given_pkg_tree_when_scan_then_ignores_media_and_sorts(
    temp_workspace: Path,
):
    store, config = _make_store(temp_workspace)
    store.ensure_layout()

    game_pkg = config.paths.game_dir / "B.pkg"
    app_pkg = config.paths.app_dir / "A.pkg"
    media_pkg = config.paths.media_dir / "SHOULD_IGNORE.pkg"
    for pkg in (game_pkg, app_pkg, media_pkg):
        pkg.parent.mkdir(parents=True, exist_ok=True)
        pkg.write_bytes(b"pkg")

    files = store.scan_pkg_files()

    assert files == [app_pkg, game_pkg]


def test_fs_package_store_given_pkg_when_stat_then_returns_size_and_mtime(
    temp_workspace: Path,
):
    store, config = _make_store(temp_workspace)
    store.ensure_layout()

    pkg = config.paths.app_dir / "A.pkg"
    pkg.write_bytes(b"12345")

    size, mtime_ns = store.stat(pkg)

    assert size == 5
    assert mtime_ns > 0


def test_fs_package_store_given_non_canonical_pkg_when_move_to_canonical_then_moves(
    temp_workspace: Path,
):
    store, config = _make_store(temp_workspace)
    store.ensure_layout()

    source = config.paths.pkg_root / "incoming.pkg"
    source.write_bytes(b"pkg")

    target = store.move_to_canonical(source, "game", "CUSA00001")

    assert target == config.paths.game_dir / "CUSA00001.pkg"
    assert source.exists() is False
    assert target.read_bytes() == b"pkg"


def test_fs_package_store_given_canonical_pkg_when_move_to_canonical_then_returns_same_path(
    temp_workspace: Path,
):
    store, config = _make_store(temp_workspace)
    store.ensure_layout()

    canonical = config.paths.game_dir / "CUSA00002.pkg"
    canonical.write_bytes(b"pkg")

    resolved = store.move_to_canonical(canonical, "game", "CUSA00002")

    assert resolved == canonical
    assert canonical.read_bytes() == b"pkg"


def test_fs_package_store_given_target_exists_when_move_to_canonical_then_raises(
    temp_workspace: Path,
):
    store, config = _make_store(temp_workspace)
    store.ensure_layout()

    source = config.paths.pkg_root / "incoming.pkg"
    source.write_bytes(b"incoming")
    target = config.paths.game_dir / "CUSA00003.pkg"
    target.write_bytes(b"existing")

    with pytest.raises(FileExistsError):
        store.move_to_canonical(source, "game", "CUSA00003")


def test_fs_package_store_given_bad_pkg_when_move_to_errors_then_moves_with_reason(
    temp_workspace: Path,
):
    store, config = _make_store(temp_workspace)
    store.ensure_layout()

    source = config.paths.pkg_root / "bad.pkg"
    source.write_bytes(b"bad")

    destination = store.move_to_errors(source, "invalid metadata!")

    assert source.exists() is False
    assert destination.exists() is True
    assert destination.parent == config.paths.errors_dir
    assert destination.suffix == ".pkg"
    assert ".invalid_metadata_." in destination.name

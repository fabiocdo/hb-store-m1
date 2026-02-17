from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from homebrew_cdn_m1_server.domain.entities.catalog_item import CatalogItem
from homebrew_cdn_m1_server.domain.entities.param_sfo_snapshot import ParamSfoSnapshot
from homebrew_cdn_m1_server.domain.value_objects.app_type import AppType
from homebrew_cdn_m1_server.domain.value_objects.content_id import ContentId
from homebrew_cdn_m1_server.infrastructure.exporters.fpkgi_json_exporter import FpkgiJsonExporter
from homebrew_cdn_m1_server.infrastructure.exporters.store_db_exporter import StoreDbExporter


def _item(
    path: Path,
    content_id: str,
    app_type: AppType,
    system_ver: str = "09.00",
    pkg_size: int = 2048,
) -> CatalogItem:
    return CatalogItem(
        content_id=ContentId.parse(content_id),
        title_id="CUSA00001",
        title="My Test",
        app_type=app_type,
        category="GD",
        version="01.00",
        pubtoolinfo="c_date=20250101",
        system_ver=system_ver,
        release_date="2025-01-01",
        pkg_path=path,
        pkg_size=pkg_size,
        pkg_mtime_ns=100,
        pkg_fingerprint="fp",
        icon0_path=path,
        pic0_path=None,
        pic1_path=None,
        sfo=ParamSfoSnapshot(fields={"TITLE": "My Test"}, raw=b"sfo", hash="hash"),
    )


def test_exporters_given_catalog_items_when_export_then_generates_store_db_and_json(
    temp_workspace: Path,
):
    share_dir = temp_workspace / "data" / "share"
    share_dir.mkdir(parents=True, exist_ok=True)

    store_sql = (Path(__file__).resolve().parents[1] / "init" / "store_db.sql")
    store_output = share_dir / "hb-store" / "store.db"

    pkg_path = share_dir / "pkg" / "game" / "UP0000-TEST00000_00-TEST000000000000.pkg"
    pkg_path.parent.mkdir(parents=True, exist_ok=True)
    pkg_path.write_bytes(b"x")

    items = [
        _item(pkg_path, "UP0000-TEST00000_00-TEST000000000000", AppType.GAME),
    ]

    store_exporter = StoreDbExporter(store_output, store_sql, "http://127.0.0.1")
    exported_db = store_exporter.export(items)

    assert exported_db == [store_output]
    conn = sqlite3.connect(str(store_output))
    row = conn.execute("SELECT content_id, apptype, image FROM homebrews").fetchone()
    conn.close()
    assert row == (
        "UP0000-TEST00000_00-TEST000000000000",
        "Game",
        "http://127.0.0.1/pkg/media/UP0000-TEST00000_00-TEST000000000000_icon0.png",
    )

    json_exporter = FpkgiJsonExporter(share_dir / "fpkgi", "http://127.0.0.1")
    exported_json = json_exporter.export(items)

    games_json = share_dir / "fpkgi" / "GAMES.json"
    assert games_json in exported_json
    payload = json.loads(games_json.read_text("utf-8"))
    assert "DATA" in payload
    assert len(payload["DATA"]) == 1
    item = payload["DATA"]["http://127.0.0.1/pkg/game/UP0000-TEST00000_00-TEST000000000000.pkg"]
    assert item["cover_url"] == "http://127.0.0.1/pkg/media/UP0000-TEST00000_00-TEST000000000000_icon0.png"


def test_fpkgi_exporter_given_single_game_when_export_then_generates_all_json_stems(
    temp_workspace: Path,
):
    share_dir = temp_workspace / "data" / "share"
    share_dir.mkdir(parents=True, exist_ok=True)

    pkg_path = share_dir / "pkg" / "game" / "UP0000-TEST00000_00-TEST000000000010.pkg"
    pkg_path.parent.mkdir(parents=True, exist_ok=True)
    pkg_path.write_bytes(b"x")

    items = [
        _item(pkg_path, "UP0000-TEST00000_00-TEST000000000010", AppType.GAME),
    ]

    exporter = FpkgiJsonExporter(share_dir / "fpkgi", "http://127.0.0.1")
    exported = exporter.export(items)

    expected_stems = (
        "APPS",
        "DEMOS",
        "DLC",
        "EMULATORS",
        "GAMES",
        "HOMEBREW",
        "PS1",
        "PS2",
        "PS5",
        "PSP",
        "SAVES",
        "THEMES",
        "UNKNOWN",
        "UPDATES",
    )
    assert len(exported) == len(expected_stems)
    for stem in expected_stems:
        destination = share_dir / "fpkgi" / f"{stem}.json"
        assert destination in exported
        payload = json.loads(destination.read_text("utf-8"))
        assert "DATA" in payload
        if stem == "GAMES":
            assert len(payload["DATA"]) == 1
        else:
            assert payload["DATA"] == {}


def test_fpkgi_exporter_given_system_ver_when_export_then_normalizes_min_fw(
    temp_workspace: Path,
):
    share_dir = temp_workspace / "data" / "share"
    share_dir.mkdir(parents=True, exist_ok=True)

    pkg_a = share_dir / "pkg" / "game" / "UP0000-TEST00000_00-TEST000000000001.pkg"
    pkg_a.parent.mkdir(parents=True, exist_ok=True)
    pkg_a.write_bytes(b"a")

    pkg_b = share_dir / "pkg" / "game" / "UP0000-TEST00000_00-TEST000000000002.pkg"
    pkg_b.write_bytes(b"b")

    items = [
        _item(pkg_a, "UP0000-TEST00000_00-TEST000000000001", AppType.GAME, "0x05050000"),
        _item(pkg_b, "UP0000-TEST00000_00-TEST000000000002", AppType.GAME, ""),
    ]

    exporter = FpkgiJsonExporter(share_dir / "fpkgi", "http://127.0.0.1")
    exporter.export(items)

    payload = json.loads((share_dir / "fpkgi" / "GAMES.json").read_text("utf-8"))
    data = payload["DATA"]
    assert (
        data["http://127.0.0.1/pkg/game/UP0000-TEST00000_00-TEST000000000001.pkg"][
            "min_fw"
        ]
        == "5.05"
    )
    assert (
        data["http://127.0.0.1/pkg/game/UP0000-TEST00000_00-TEST000000000002.pkg"][
            "min_fw"
        ]
        == ""
    )


def test_fpkgi_exporter_given_pkg_sizes_when_export_then_uses_dynamic_size_units(
    temp_workspace: Path,
):
    share_dir = temp_workspace / "data" / "share"
    share_dir.mkdir(parents=True, exist_ok=True)

    pkg_small = share_dir / "pkg" / "app" / "UP0000-TEST00000_00-TEST000000000003.pkg"
    pkg_small.parent.mkdir(parents=True, exist_ok=True)
    pkg_small.write_bytes(b"a")

    pkg_medium = share_dir / "pkg" / "app" / "UP0000-TEST00000_00-TEST000000000004.pkg"
    pkg_medium.write_bytes(b"b")

    pkg_large = share_dir / "pkg" / "app" / "UP0000-TEST00000_00-TEST000000000005.pkg"
    pkg_large.write_bytes(b"c")

    items = [
        _item(
            pkg_small,
            "UP0000-TEST00000_00-TEST000000000003",
            AppType.APP,
            pkg_size=512_000,
        ),
        _item(
            pkg_medium,
            "UP0000-TEST00000_00-TEST000000000004",
            AppType.APP,
            pkg_size=25 * 1024 * 1024,
        ),
        _item(
            pkg_large,
            "UP0000-TEST00000_00-TEST000000000005",
            AppType.APP,
            pkg_size=3 * 1024 * 1024 * 1024,
        ),
    ]

    exporter = FpkgiJsonExporter(share_dir / "fpkgi", "http://127.0.0.1")
    exporter.export(items)

    payload = json.loads((share_dir / "fpkgi" / "APPS.json").read_text("utf-8"))
    data = payload["DATA"]

    assert (
        data["http://127.0.0.1/pkg/app/UP0000-TEST00000_00-TEST000000000003.pkg"][
            "size"
        ]
        == "512000 B"
    )
    assert (
        data["http://127.0.0.1/pkg/app/UP0000-TEST00000_00-TEST000000000004.pkg"][
            "size"
        ]
        == "25.00 MB"
    )
    assert (
        data["http://127.0.0.1/pkg/app/UP0000-TEST00000_00-TEST000000000005.pkg"][
            "size"
        ]
        == "3.00 GB"
    )


def test_store_db_exporter_given_existing_db_when_cleanup_then_removes_file(
    temp_workspace: Path,
):
    share_dir = temp_workspace / "data" / "share"
    share_dir.mkdir(parents=True, exist_ok=True)

    store_sql = Path(__file__).resolve().parents[1] / "init" / "store_db.sql"
    store_output = share_dir / "hb-store" / "store.db"

    pkg_path = share_dir / "pkg" / "game" / "UP0000-TEST00000_00-TEST000000000000.pkg"
    pkg_path.parent.mkdir(parents=True, exist_ok=True)
    pkg_path.write_bytes(b"x")

    item = _item(pkg_path, "UP0000-TEST00000_00-TEST000000000000", AppType.GAME)
    exporter = StoreDbExporter(store_output, store_sql, "http://127.0.0.1")
    exporter.export([item])
    assert store_output.exists() is True

    removed = exporter.cleanup()

    assert removed == [store_output]
    assert store_output.exists() is False


def test_fpkgi_exporter_given_existing_outputs_when_cleanup_then_removes_all_known_json(
    temp_workspace: Path,
):
    output_dir = temp_workspace / "data" / "share" / "fpkgi"
    output_dir.mkdir(parents=True, exist_ok=True)
    managed = [output_dir / "GAMES.json", output_dir / "DLC.json", output_dir / "APPS.json"]
    for path in managed:
        path.write_text('{"DATA":{}}', encoding="utf-8")
    extra = output_dir / "CUSTOM.json"
    extra.write_text("{}", encoding="utf-8")

    exporter = FpkgiJsonExporter(output_dir, "http://127.0.0.1")
    removed = exporter.cleanup()

    assert set(removed) == set(managed)
    for path in managed:
        assert path.exists() is False
    assert extra.exists() is True


def test_fpkgi_exporter_given_stale_json_when_export_then_resets_managed_file_to_empty_data(
    temp_workspace: Path,
):
    share_dir = temp_workspace / "data" / "share"
    share_dir.mkdir(parents=True, exist_ok=True)
    output_dir = share_dir / "fpkgi"
    output_dir.mkdir(parents=True, exist_ok=True)

    stale = output_dir / "APPS.json"
    stale.write_text('{"DATA":{"old":"data"}}', encoding="utf-8")

    pkg_path = share_dir / "pkg" / "game" / "UP0000-TEST00000_00-TEST000000000099.pkg"
    pkg_path.parent.mkdir(parents=True, exist_ok=True)
    pkg_path.write_bytes(b"x")
    items = [_item(pkg_path, "UP0000-TEST00000_00-TEST000000000099", AppType.GAME)]

    exporter = FpkgiJsonExporter(output_dir, "http://127.0.0.1")
    exported = exporter.export(items)

    assert (output_dir / "GAMES.json") in exported
    assert stale.exists() is True
    stale_payload = json.loads(stale.read_text("utf-8"))
    assert stale_payload == {"DATA": {}}

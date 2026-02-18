from __future__ import annotations

import hashlib
import http.client
import json
import logging
import sqlite3
from pathlib import Path
from typing import cast

from homebrew_cdn_m1_server.application.hb_store_api import (
    HbStoreApiResolver,
    HbStoreApiServer,
)


def _init_catalog_db(path: Path) -> None:
    schema = (Path(__file__).resolve().parents[1] / "init" / "catalog_db.sql").read_text(
        "utf-8"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(path)) as conn:
        _ = conn.executescript(schema)
        conn.commit()


def _insert_catalog_row(
    path: Path,
    *,
    content_id: str,
    title_id: str,
    app_type: str,
    version: str,
    updated_at: str,
) -> None:
    with sqlite3.connect(str(path)) as conn:
        _ = conn.execute(
            """
            INSERT INTO catalog_items (
                content_id, title_id, title, app_type, category, version,
                pubtoolinfo, system_ver, release_date, pkg_path,
                pkg_size, pkg_mtime_ns, pkg_fingerprint,
                icon0_path, pic0_path, pic1_path,
                sfo_json, sfo_raw, sfo_hash,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                content_id,
                title_id,
                "Test title",
                app_type,
                "GD",
                version,
                "c_date=20250101",
                "0x05050000",
                "2025-01-01",
                f"/tmp/{content_id}.pkg",
                100,
                1,
                "fp",
                None,
                None,
                None,
                "{}",
                b"",
                "hash",
                updated_at,
                updated_at,
            ),
        )
        conn.commit()


def _init_store_db(path: Path) -> None:
    schema = (Path(__file__).resolve().parents[1] / "init" / "store_db.sql").read_text("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(path)) as conn:
        _ = conn.executescript(schema)
        conn.commit()


def _insert_store_row(
    path: Path,
    *,
    content_id: str,
    title_id: str,
    package_url: str,
    version: str = "01.00",
    number_of_downloads: int = 0,
) -> None:
    with sqlite3.connect(str(path)) as conn:
        _ = conn.execute(
            """
            INSERT INTO homebrews (
                content_id, id, name, desc, image, package, version,
                picpath, desc_1, desc_2, ReviewStars, Size, Author,
                apptype, pv, main_icon_path, main_menu_pic, releaseddate,
                number_of_downloads, github, video, twitter, md5
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                content_id,
                title_id,
                "Test title",
                None,
                "http://127.0.0.1/pkg/media/icon0.png",
                package_url,
                version,
                None,
                None,
                None,
                None,
                100,
                None,
                "Game",
                None,
                None,
                None,
                "2025-01-01",
                number_of_downloads,
                None,
                None,
                None,
                None,
            ),
        )
        conn.commit()


def _decode_json_dict(payload: bytes) -> dict[str, str]:
    parsed = cast(object, json.loads(payload.decode("utf-8")))
    assert isinstance(parsed, dict)
    result: dict[str, str] = {}
    for key, value in cast(dict[object, object], parsed).items():
        result[str(key)] = str(value)
    return result


def test_hb_store_api_resolver_given_store_db_when_hash_requested_then_returns_md5(
    temp_workspace: Path,
) -> None:
    store_db = temp_workspace / "data" / "share" / "hb-store" / "store.db"
    _ = store_db.parent.mkdir(parents=True, exist_ok=True)
    _ = store_db.write_bytes(b"abc123")

    resolver = HbStoreApiResolver(
        catalog_db_path=temp_workspace / "data" / "internal" / "catalog" / "catalog.db",
        store_db_path=store_db,
        base_url="http://127.0.0.1",
    )

    assert resolver.store_db_hash() == hashlib.md5(b"abc123").hexdigest()


def test_hb_store_api_resolver_given_multiple_versions_when_resolve_then_returns_latest(
    temp_workspace: Path,
) -> None:
    catalog_db = temp_workspace / "data" / "internal" / "catalog" / "catalog.db"
    store_db = temp_workspace / "data" / "share" / "hb-store" / "store.db"
    _init_catalog_db(catalog_db)
    _init_store_db(store_db)

    _insert_catalog_row(
        catalog_db,
        content_id="UP0000-TEST00000_00-TEST000000000001",
        title_id="CUSA00001",
        app_type="game",
        version="01.09",
        updated_at="2025-01-01T00:00:00+00:00",
    )
    _insert_catalog_row(
        catalog_db,
        content_id="UP0000-TEST00000_00-TEST000000000002",
        title_id="CUSA00001",
        app_type="game",
        version="01.10",
        updated_at="2025-01-01T00:00:00+00:00",
    )

    resolver = HbStoreApiResolver(
        catalog_db_path=catalog_db,
        store_db_path=store_db,
        base_url="http://127.0.0.1",
    )

    assert (
        resolver.resolve_download_url("CUSA00001")
        == "http://127.0.0.1/pkg/game/UP0000-TEST00000_00-TEST000000000002.pkg"
    )


def test_hb_store_api_resolver_given_missing_catalog_entry_when_resolve_then_fallback_to_store_db(
    temp_workspace: Path,
) -> None:
    catalog_db = temp_workspace / "data" / "internal" / "catalog" / "catalog.db"
    store_db = temp_workspace / "data" / "share" / "hb-store" / "store.db"
    _init_catalog_db(catalog_db)
    _init_store_db(store_db)
    _insert_store_row(
        store_db,
        content_id="UP0000-TEST00000_00-TEST000000000999",
        title_id="CUSA00009",
        package_url="http://127.0.0.1/pkg/game/UP0000-TEST00000_00-TEST000000000999.pkg",
    )

    resolver = HbStoreApiResolver(
        catalog_db_path=catalog_db,
        store_db_path=store_db,
        base_url="http://127.0.0.1",
    )

    assert (
        resolver.resolve_download_url("CUSA00009")
        == "http://127.0.0.1/pkg/game/UP0000-TEST00000_00-TEST000000000999.pkg"
    )


def test_hb_store_api_server_given_requests_when_called_then_returns_compatible_responses(
    temp_workspace: Path,
) -> None:
    catalog_db = temp_workspace / "data" / "internal" / "catalog" / "catalog.db"
    store_db = temp_workspace / "data" / "share" / "hb-store" / "store.db"
    _init_catalog_db(catalog_db)
    _init_store_db(store_db)
    _insert_catalog_row(
        catalog_db,
        content_id="UP0000-TEST00000_00-TEST000000000100",
        title_id="CUSA00100",
        app_type="game",
        version="02.00",
        updated_at="2025-01-02T00:00:00+00:00",
    )
    _insert_store_row(
        store_db,
        content_id="UP0000-TEST00000_00-TEST000000000100",
        title_id="CUSA00100",
        package_url="http://127.0.0.1/pkg/game/UP0000-TEST00000_00-TEST000000000100.pkg",
        number_of_downloads=42,
    )

    resolver = HbStoreApiResolver(
        catalog_db_path=catalog_db,
        store_db_path=store_db,
        base_url="http://127.0.0.1",
    )
    server = HbStoreApiServer(
        resolver=resolver,
        logger=logging.getLogger("tests.hb_store_api"),
        host="127.0.0.1",
        port=0,
    )
    server.start()

    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=3)

        conn.request("GET", "/api.php?db_check_hash=true")
        response = conn.getresponse()
        body = response.read()
        assert response.status == 200
        payload = _decode_json_dict(body)
        assert payload["hash"] == resolver.store_db_hash()

        conn.request("GET", "/download.php?tid=CUSA00100&check=true")
        response = conn.getresponse()
        body = response.read()
        assert response.status == 200
        payload = _decode_json_dict(body)
        assert payload["number_of_downloads"] == "42"

        conn.request("GET", "/download.php?tid=CUSA00100")
        response = conn.getresponse()
        _ = response.read()
        assert response.status == 302
        assert (
            response.getheader("Location")
            == "http://127.0.0.1/pkg/game/UP0000-TEST00000_00-TEST000000000100.pkg"
        )

        conn.request("GET", "/download.php?tid=UNKNOWN")
        response = conn.getresponse()
        body = response.read()
        assert response.status == 404
        payload = _decode_json_dict(body)
        assert payload["error"] == "title_id_not_found"
        conn.close()
    finally:
        server.stop()

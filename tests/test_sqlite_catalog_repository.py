from __future__ import annotations

from pathlib import Path

from homebrew_cdn_m1_server.domain.models.catalog_item import CatalogItem
from homebrew_cdn_m1_server.domain.models.param_sfo_snapshot import ParamSfoSnapshot
from homebrew_cdn_m1_server.domain.models.app_type import AppType
from homebrew_cdn_m1_server.domain.models.content_id import ContentId
from homebrew_cdn_m1_server.application.repositories.sqlite_unit_of_work import SqliteUnitOfWork


def _item(path: Path) -> CatalogItem:
    return CatalogItem(
        content_id=ContentId.parse("UP0000-TEST00000_00-TEST000000000000"),
        title_id="CUSA00001",
        title="Test",
        app_type=AppType.GAME,
        category="GD",
        version="01.00",
        pubtoolinfo="c_date=20250101",
        system_ver="09.00",
        release_date="2025-01-01",
        pkg_path=path,
        pkg_size=123,
        pkg_mtime_ns=456,
        pkg_fingerprint="abc",
        icon0_path=None,
        pic0_path=None,
        pic1_path=None,
        sfo=ParamSfoSnapshot(fields={"CONTENT_ID": "UP0000-TEST00000_00-TEST000000000000"}, raw=b"x", hash="h"),
    )


def test_sqlite_repo_given_upsert_and_prune_then_persists_and_deletes(temp_workspace: Path):
    db_path = temp_workspace / "data" / "internal" / "catalog" / "catalog.db"
    sql = (Path(__file__).resolve().parents[1] / "init" / "catalog_db.sql").read_text("utf-8")

    pkg_a = temp_workspace / "data" / "share" / "pkg" / "game" / "A.pkg"
    pkg_a.parent.mkdir(parents=True, exist_ok=True)
    _ = pkg_a.write_bytes(b"x")

    with SqliteUnitOfWork(db_path) as uow:
        uow.catalog.init_schema(sql)
        uow.catalog.upsert(_item(pkg_a))
        assert uow.catalog.get_download_count("CUSA00001") == 0
        assert uow.catalog.increment_download_count("CUSA00001") == 1
        assert uow.catalog.increment_download_count("CUSA00001") == 2
        uow.commit()

    with SqliteUnitOfWork(db_path) as uow:
        items = uow.catalog.list_items()
        assert len(items) == 1
        assert items[0].downloads == 2
        removed = uow.catalog.delete_by_pkg_paths_not_in(set())
        uow.commit()

    assert removed == 1

    with SqliteUnitOfWork(db_path) as uow:
        assert uow.catalog.list_items() == []

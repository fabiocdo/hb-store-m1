from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from homebrew_cdn_m1_server.domain.protocols.catalog_repository_port import CatalogRepositoryPort
from homebrew_cdn_m1_server.domain.entities.catalog_item import CatalogItem
from homebrew_cdn_m1_server.domain.entities.param_sfo_snapshot import ParamSfoSnapshot
from homebrew_cdn_m1_server.domain.value_objects.app_type import AppType
from homebrew_cdn_m1_server.domain.value_objects.content_id import ContentId


class SqliteCatalogRepository(CatalogRepositoryPort):
    def __init__(self, conn: sqlite3.Connection, db_path: Path) -> None:
        self._conn = conn
        self._db_path = db_path

    def init_schema(self, schema_sql: str) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn.executescript(schema_sql)

    @staticmethod
    def _to_row(item: CatalogItem) -> dict[str, object]:
        now = datetime.now(UTC).replace(microsecond=0).isoformat()
        return {
            "content_id": item.content_id.value,
            "title_id": item.title_id,
            "title": item.title,
            "app_type": item.app_type.value,
            "category": item.category,
            "version": item.version,
            "pubtoolinfo": item.pubtoolinfo,
            "system_ver": item.system_ver,
            "release_date": item.release_date,
            "pkg_path": str(item.pkg_path),
            "pkg_size": int(item.pkg_size),
            "pkg_mtime_ns": int(item.pkg_mtime_ns),
            "pkg_fingerprint": item.pkg_fingerprint,
            "icon0_path": str(item.icon0_path) if item.icon0_path else None,
            "pic0_path": str(item.pic0_path) if item.pic0_path else None,
            "pic1_path": str(item.pic1_path) if item.pic1_path else None,
            "sfo_json": json.dumps(item.sfo.fields, ensure_ascii=True, sort_keys=True),
            "sfo_raw": item.sfo.raw,
            "sfo_hash": item.sfo.hash,
            "updated_at": now,
            "created_at": now,
        }

    def upsert(self, item: CatalogItem) -> None:
        row = self._to_row(item)
        self._conn.execute(
            """
            INSERT INTO catalog_items (
                content_id, title_id, title, app_type, category, version,
                pubtoolinfo, system_ver, release_date, pkg_path,
                pkg_size, pkg_mtime_ns, pkg_fingerprint,
                icon0_path, pic0_path, pic1_path,
                sfo_json, sfo_raw, sfo_hash,
                created_at, updated_at
            ) VALUES (
                :content_id, :title_id, :title, :app_type, :category, :version,
                :pubtoolinfo, :system_ver, :release_date, :pkg_path,
                :pkg_size, :pkg_mtime_ns, :pkg_fingerprint,
                :icon0_path, :pic0_path, :pic1_path,
                :sfo_json, :sfo_raw, :sfo_hash,
                :created_at, :updated_at
            )
            ON CONFLICT(content_id, app_type, version)
            DO UPDATE SET
                title_id=excluded.title_id,
                title=excluded.title,
                category=excluded.category,
                pubtoolinfo=excluded.pubtoolinfo,
                system_ver=excluded.system_ver,
                release_date=excluded.release_date,
                pkg_path=excluded.pkg_path,
                pkg_size=excluded.pkg_size,
                pkg_mtime_ns=excluded.pkg_mtime_ns,
                pkg_fingerprint=excluded.pkg_fingerprint,
                icon0_path=excluded.icon0_path,
                pic0_path=excluded.pic0_path,
                pic1_path=excluded.pic1_path,
                sfo_json=excluded.sfo_json,
                sfo_raw=excluded.sfo_raw,
                sfo_hash=excluded.sfo_hash,
                updated_at=excluded.updated_at
            """,
            row,
        )

    @staticmethod
    def _parse_row(row: sqlite3.Row) -> CatalogItem:
        sfo_json = row["sfo_json"] or "{}"
        fields = json.loads(sfo_json)
        if not isinstance(fields, dict):
            fields = {}

        return CatalogItem(
            content_id=ContentId.parse(row["content_id"]),
            title_id=str(row["title_id"] or ""),
            title=str(row["title"] or ""),
            app_type=AppType(str(row["app_type"] or "unknown")),
            category=str(row["category"] or ""),
            version=str(row["version"] or ""),
            pubtoolinfo=str(row["pubtoolinfo"] or ""),
            system_ver=str(row["system_ver"] or ""),
            release_date=str(row["release_date"] or ""),
            pkg_path=Path(str(row["pkg_path"])),
            pkg_size=int(row["pkg_size"] or 0),
            pkg_mtime_ns=int(row["pkg_mtime_ns"] or 0),
            pkg_fingerprint=str(row["pkg_fingerprint"] or ""),
            icon0_path=Path(row["icon0_path"]) if row["icon0_path"] else None,
            pic0_path=Path(row["pic0_path"]) if row["pic0_path"] else None,
            pic1_path=Path(row["pic1_path"]) if row["pic1_path"] else None,
            sfo=ParamSfoSnapshot(
                fields={str(k): str(v) for k, v in fields.items()},
                raw=bytes(row["sfo_raw"] or b""),
                hash=str(row["sfo_hash"] or ""),
            ),
            downloads=0,
        )

    def list_items(self) -> list[CatalogItem]:
        self._conn.row_factory = sqlite3.Row
        rows = self._conn.execute(
            """
            SELECT content_id, title_id, title, app_type, category, version,
                   pubtoolinfo, system_ver, release_date, pkg_path,
                   pkg_size, pkg_mtime_ns, pkg_fingerprint,
                   icon0_path, pic0_path, pic1_path,
                   sfo_json, sfo_raw, sfo_hash
            FROM catalog_items
            ORDER BY app_type, content_id, version
            """
        ).fetchall()

        items: list[CatalogItem] = []
        for row in rows:
            try:
                items.append(self._parse_row(row))
            except Exception:
                continue
        return items

    def delete_by_pkg_paths_not_in(self, existing_pkg_paths: set[str]) -> int:
        cursor = self._conn.cursor()
        if not existing_pkg_paths:
            deleted = cursor.execute("DELETE FROM catalog_items").rowcount
            return int(deleted or 0)

        placeholders = ",".join("?" for _ in existing_pkg_paths)
        deleted = cursor.execute(
            f"DELETE FROM catalog_items WHERE pkg_path NOT IN ({placeholders})",
            tuple(existing_pkg_paths),
        ).rowcount
        return int(deleted or 0)

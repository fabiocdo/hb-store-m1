from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import ClassVar, cast, final, override
from urllib.parse import parse_qs, urlparse


@final
class HbStoreApiResolver:
    _VERSION_PARTS_REGEX: ClassVar[re.Pattern[str]] = re.compile(r"\d+")
    _COUNT_ROW_SQL: ClassVar[str] = """
        SELECT number_of_downloads
        FROM homebrews
        WHERE id = ?
        ORDER BY pid DESC
        LIMIT 1
    """
    _CATALOG_ROW_SQL: ClassVar[str] = """
        SELECT
            COALESCE(content_id, ''),
            COALESCE(app_type, ''),
            COALESCE(version, ''),
            COALESCE(updated_at, '')
        FROM catalog_items
        WHERE title_id = ?
    """
    _PACKAGE_ROW_SQL: ClassVar[str] = """
        SELECT COALESCE(package, '')
        FROM homebrews
        WHERE id = ?
        ORDER BY pid DESC
        LIMIT 1
    """

    def __init__(self, catalog_db_path: Path, store_db_path: Path, base_url: str) -> None:
        self._catalog_db_path = catalog_db_path
        self._store_db_path = store_db_path
        self._base_url = base_url.rstrip("/")

    def store_db_hash(self) -> str:
        if not self._store_db_path.exists():
            return ""

        digest = hashlib.md5()
        with self._store_db_path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def download_count(self, title_id: str) -> str:
        if not title_id or not self._store_db_path.exists():
            return "0"

        try:
            with sqlite3.connect(str(self._store_db_path)) as conn:
                row_obj = cast(object, conn.execute(self._COUNT_ROW_SQL, (title_id,)).fetchone())
        except sqlite3.Error:
            return "0"

        row = cast(tuple[object] | None, row_obj)
        if row is None:
            return "0"
        value = row[0]
        if value is None:
            return "0"
        if isinstance(value, bool):
            return str(int(value))
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            return str(int(value))
        if isinstance(value, str):
            try:
                return str(int(value.strip()))
            except ValueError:
                return "0"
        if isinstance(value, (bytes, bytearray)):
            try:
                return str(int(bytes(value).decode("utf-8", errors="ignore").strip()))
            except ValueError:
                return "0"
        if isinstance(value, memoryview):
            try:
                return str(int(value.tobytes().decode("utf-8", errors="ignore").strip()))
            except ValueError:
                return "0"
        return "0"

    @classmethod
    def _version_key(cls, value: str) -> tuple[int, ...]:
        matches = cast(list[str], cls._VERSION_PARTS_REGEX.findall(str(value or "")))
        parts = [int(item) for item in matches]
        if not parts:
            return tuple()
        while len(parts) > 1 and parts[-1] == 0:
            _ = parts.pop()
        return tuple(parts)

    def _package_url_from_catalog(self, title_id: str) -> str | None:
        if not title_id or not self._catalog_db_path.exists():
            return None

        try:
            with sqlite3.connect(str(self._catalog_db_path)) as conn:
                rows_obj = conn.execute(self._CATALOG_ROW_SQL, (title_id,)).fetchall()
        except sqlite3.Error:
            return None

        rows = cast(list[tuple[str, str, str, str]], rows_obj)
        if not rows:
            return None

        best = max(
            rows,
            key=lambda row: (
                self._version_key(str(row[2] or "")),
                str(row[3] or ""),
                str(row[1] or ""),
                str(row[0] or ""),
            ),
        )

        content_id = str(best[0] or "").strip()
        app_type = str(best[1] or "").strip().lower()
        if not content_id or not app_type:
            return None

        route = f"/pkg/{app_type}/{content_id}.pkg"
        if self._base_url:
            return f"{self._base_url}{route}"
        return route

    def _package_url_from_store_db(self, title_id: str) -> str | None:
        if not title_id or not self._store_db_path.exists():
            return None

        try:
            with sqlite3.connect(str(self._store_db_path)) as conn:
                row_obj = cast(object, conn.execute(self._PACKAGE_ROW_SQL, (title_id,)).fetchone())
        except sqlite3.Error:
            return None

        row = cast(tuple[object] | None, row_obj)
        if row is None:
            return None

        package_url = str(row[0] or "").strip()
        if not package_url:
            return None
        return package_url

    def resolve_download_url(self, title_id: str) -> str | None:
        return self._package_url_from_store_db(title_id) or self._package_url_from_catalog(
            title_id
        )


@final
class HbStoreApiServer:
    def __init__(
        self,
        resolver: HbStoreApiResolver,
        logger: logging.Logger,
        host: str = "127.0.0.1",
        port: int = 18191,
    ) -> None:
        self._resolver = resolver
        self._logger = logger
        self._host = host
        self._port = int(port)
        self._server: ThreadingHTTPServer | None = None
        self._thread: Thread | None = None

    @property
    def port(self) -> int:
        server = self._server
        if server is None:
            return self._port
        return int(server.server_address[1])

    def start(self) -> None:
        if self._server is not None:
            return

        handler_cls = self._build_handler()
        server = ThreadingHTTPServer((self._host, self._port), handler_cls)
        server.daemon_threads = True
        thread = Thread(target=server.serve_forever, name="hb-store-api-http", daemon=True)
        thread.start()

        self._server = server
        self._thread = thread
        self._logger.debug(
            "HB-Store API started: host: %s, port: %d",
            self._host,
            int(server.server_address[1]),
        )

    def stop(self) -> None:
        server = self._server
        if server is None:
            return

        self._server = None
        thread = self._thread
        self._thread = None

        server.shutdown()
        server.server_close()
        if thread is not None:
            thread.join(timeout=2.0)
        self._logger.debug("HB-Store API stopped")

    def _build_handler(self) -> type[BaseHTTPRequestHandler]:
        resolver = self._resolver
        logger = self._logger

        class _Handler(BaseHTTPRequestHandler):
            server_version: str = "HomebrewCdnApi/1.0"
            sys_version: str = ""

            def do_HEAD(self) -> None:
                self._dispatch(send_body=False)

            def do_GET(self) -> None:
                self._dispatch(send_body=True)

            def _dispatch(self, send_body: bool) -> None:
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query, keep_blank_values=True)

                if parsed.path == "/api.php":
                    hash_value = resolver.store_db_hash()
                    self._write_json({"hash": hash_value}, send_body=send_body)
                    return

                if parsed.path == "/download.php":
                    title_id = str(params.get("tid", [""])[0] or "").strip()
                    check = str(params.get("check", [""])[0] or "").strip().lower()
                    if check in {"1", "true", "yes", "on"}:
                        count = resolver.download_count(title_id)
                        self._write_json(
                            {"number_of_downloads": count},
                            send_body=send_body,
                        )
                        return

                    destination = resolver.resolve_download_url(title_id)
                    if not destination:
                        self._write_json(
                            {"error": "title_id_not_found"},
                            status=404,
                            send_body=send_body,
                        )
                        return

                    self.send_response(302)
                    self.send_header("Location", destination)
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return

                self._write_json({"error": "not_found"}, status=404, send_body=send_body)

            def _write_json(
                self,
                payload: dict[str, str],
                status: int = 200,
                send_body: bool = True,
            ) -> None:
                body = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode(
                    "utf-8"
                )
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if send_body:
                    _ = self.wfile.write(body)

            @override
            def log_message(self, format: str, *args: object) -> None:
                logger.debug("HB-Store API: " + format, *args)

        return _Handler

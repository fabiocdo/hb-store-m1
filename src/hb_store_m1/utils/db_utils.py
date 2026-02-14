import hashlib
import json
import sqlite3
from urllib.parse import urljoin

from hb_store_m1.models.globals import Globals
from hb_store_m1.models.log import LogModule
from hb_store_m1.models.output import Output, Status
from hb_store_m1.models.pkg.pkg import PKG
from hb_store_m1.models.storedb import StoreDB
from hb_store_m1.utils.init_utils import InitUtils
from hb_store_m1.utils.log_utils import LogUtils

log = LogUtils(LogModule.DB_UTIL)


def _generate_row_md5(values_by_column: dict[str, object]) -> str:
    columns = [col.value for col in StoreDB.Column if col is not StoreDB.Column.ROW_MD5]
    payload = json.dumps(
        [values_by_column.get(name) for name in columns],
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.md5(payload).hexdigest()


def _generate_upsert_params(pkg: PKG) -> dict[str, object]:
    row = {
        "content_id": pkg.content_id,
        "id": pkg.title_id,
        "name": pkg.title,
        "desc": None,
        "image": urljoin(Globals.ENVS.SERVER_URL, str(pkg.icon0_png_path)),
        "package": urljoin(Globals.ENVS.SERVER_URL, str(pkg.pkg_path)),
        "version": pkg.version,
        "picpath": None,
        "desc_1": None,
        "desc_2": None,
        "ReviewStars": None,
        "Size": pkg.pkg_path.stat().st_size,
        "Author": None,
        "apptype": pkg.app_type,
        "pv": None,
        "main_icon_path": (
            urljoin(Globals.ENVS.SERVER_URL, str(pkg.pic0_png_path))
            if pkg.pic0_png_path
            else None
        ),
        "main_menu_pic": (
            urljoin(Globals.ENVS.SERVER_URL, str(pkg.pic1_png_path))
            if pkg.pic1_png_path
            else None
        ),
        "releaseddate": pkg.release_date,
        "number_of_downloads": 0,
        "github": None,
        "video": None,
        "twitter": None,
        "md5": None,
    }

    row["row_md5"] = _generate_row_md5(row)

    return row


class DBUtils:
    @staticmethod
    def _ensure_db_initialized() -> None:
        store_db_file_path = Globals.FILES.STORE_DB_FILE_PATH
        if not store_db_file_path.exists():
            InitUtils.init_db()

    @staticmethod
    def _connect() -> sqlite3.Connection:
        return sqlite3.connect(str(Globals.FILES.STORE_DB_FILE_PATH))

    @staticmethod
    def _quote(column: str) -> str:
        return f'"{column}"'

    @staticmethod
    def _build_upsert_sql() -> str:
        columns = [col.value for col in StoreDB.Column]
        conflict_key = StoreDB.Column.CONTENT_ID.value
        insert_cols = ", ".join(DBUtils._quote(col) for col in columns)
        values = ", ".join(f":{col}" for col in columns)
        update_set = ", ".join(
            f"{DBUtils._quote(col)}=excluded.{DBUtils._quote(col)}"
            for col in columns
            if col != conflict_key
        )
        return (
            f"INSERT INTO homebrews ({insert_cols}) "
            f"VALUES ({values}) "
            f"ON CONFLICT({DBUtils._quote(conflict_key)}) DO UPDATE SET {update_set}"
        )

    @staticmethod
    def select_by_content_ids(
        conn: sqlite3.Connection | None,
        content_ids: list[str],
    ) -> Output[list[dict[str, object]]]:
        DBUtils._ensure_db_initialized()

        if not content_ids:
            return Output(Status.OK, [])

        own_conn = conn is None
        if own_conn:
            conn = DBUtils._connect()

        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        placeholders = ",".join("?" for _ in content_ids)

        query = f"""
            SELECT content_id, row_md5
            FROM homebrews
            WHERE content_id IN ({placeholders})
        """
        try:
            cursor.execute(query, content_ids)
            rows = [dict(row) for row in cursor.fetchall()]
            return Output(Status.OK, rows)
        finally:
            if own_conn:
                conn.close()

    @staticmethod
    def select_content_ids(conn: sqlite3.Connection | None = None) -> Output[list[str]]:
        store_db_file_path = Globals.FILES.STORE_DB_FILE_PATH
        if not store_db_file_path.exists():
            return Output(Status.NOT_FOUND, [])

        own_conn = conn is None
        if own_conn:
            conn = DBUtils._connect()

        cursor = conn.cursor()
        try:
            cursor.execute("SELECT content_id FROM homebrews")
            return Output(
                Status.OK,
                [
                    row[0]
                    for row in cursor.fetchall()
                    if row and row[0]
                ],
            )
        except Exception as e:
            log.log_error(f"Failed to list content_ids from STORE.DB: {e}")
            return Output(Status.ERROR, [])
        finally:
            if own_conn:
                conn.close()

    @staticmethod
    def upsert(pkgs: list[PKG], conn: sqlite3.Connection | None = None) -> Output:
        DBUtils._ensure_db_initialized()

        if not pkgs:
            return Output(Status.SKIP, "Nothing to upsert")

        own_conn = conn is None
        if own_conn:
            conn = DBUtils._connect()

        content_ids = [pkg.content_id for pkg in pkgs if pkg.content_id]
        existing_output = DBUtils.select_by_content_ids(conn, content_ids)
        existing = {
            row["content_id"]: row["row_md5"] for row in (existing_output.content or [])
        }

        log.log_info(f"Attempting to upsert {len(pkgs)} PKGs in STORE.DB...")

        try:
            conn.execute("BEGIN")
            upsert_sql = DBUtils._build_upsert_sql()

            upsert_params = [
                params
                for pkg in pkgs
                if (params := _generate_upsert_params(pkg)).get("row_md5")
                != existing.get(pkg.content_id)
            ]

            if upsert_params:
                conn.executemany(upsert_sql, upsert_params)

            conn.commit()

            skipped = len(pkgs) - len(upsert_params)

            if skipped:
                log.log_info(f"Skipped {skipped} unchanged PKGs")
                return Output(Status.SKIP, None)

            log.log_info(f"{len(upsert_params)} PKGs upserted successfully")
            return Output(Status.OK, len(upsert_params))

        except Exception as e:
            conn.rollback()
            log.log_error(f"Failed to upsert {len(pkgs)} PKGs in STORE.DB: {e}")
            return Output(Status.ERROR, len(pkgs))

        finally:
            if own_conn:
                conn.close()

    @staticmethod
    def delete_by_content_ids(content_ids: list[str]) -> Output:

        store_db_file_path = Globals.FILES.STORE_DB_FILE_PATH

        if not store_db_file_path.exists():
            return Output(Status.NOT_FOUND, "STORE.DB not found")

        if not content_ids:
            return Output(Status.SKIP, "Nothing to delete")

        conn = DBUtils._connect()
        log.log_info(f"Attempting to delete {len(content_ids)} PKGs from STORE.DB...")
        try:
            conn.execute("BEGIN")

            before = conn.total_changes
            conn.executemany(
                "DELETE FROM homebrews WHERE content_id = ?",
                [(content_id,) for content_id in content_ids],
            )
            conn.commit()
            deleted = conn.total_changes - before

            log.log_info(f"{deleted} PKGs deleted successfully")
            return Output(Status.OK, deleted)
        except Exception as e:
            conn.rollback()
            log.log_error(f"Failed to delete PKGs from STORE.DB: {e}")
            return Output(Status.ERROR, len(content_ids))
        finally:
            conn.close()


DBUtils = DBUtils()

import hashlib
import json
import sqlite3

from hb_store_m1.models.globals import Globals
from hb_store_m1.models.log import LogModule
from hb_store_m1.models.output import Output, Status
from hb_store_m1.models.pkg.pkg import PKG
from hb_store_m1.models.storedb import StoreDB
from hb_store_m1.utils.init_utils import InitUtils
from hb_store_m1.utils.log_utils import LogUtils


class DBUtils:

    @staticmethod
    def upsert(pkgs: list[PKG]) -> Output:

        store_db_file_path = Globals.FILES.STORE_DB_FILE_PATH

        if not store_db_file_path.exists():
            InitUtils.init_db()

        if not pkgs:
            return Output(Status.SKIP, "Nothing to upsert")

        conn = sqlite3.connect(str(store_db_file_path))

        LogUtils.log_info(
            f"Attempting to upsert {len(pkgs)} PKGs in STORE.DB...", LogModule.DB_UTIL
        )
        try:
            conn.execute("BEGIN")

            insert_sql = """
                         INSERT INTO homebrews (content_id, id, name, "desc", image, package, version, picpath, desc_1, desc_2,
                                                ReviewStars, Size, Author, apptype, pv, main_icon_path, main_menu_pic,
                                                releaseddate, number_of_downloads, github, video, twitter, md5)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                         ON CONFLICT(content_id) DO UPDATE SET
                            id=excluded.id,
                            name=excluded.name,
                            "desc"=excluded."desc",
                            image=excluded.image,
                            package=excluded.package,
                            version=excluded.version,
                            picpath=excluded.picpath,
                            desc_1=excluded.desc_1,
                            desc_2=excluded.desc_2,
                            ReviewStars=excluded.ReviewStars,
                            Size=excluded.Size,
                            Author=excluded.Author,
                            apptype=excluded.apptype,
                            pv=excluded.pv,
                            main_icon_path=excluded.main_icon_path,
                            main_menu_pic=excluded.main_menu_pic,
                            releaseddate=excluded.releaseddate,
                            number_of_downloads=excluded.number_of_downloads,
                            github=excluded.github,
                            video=excluded.video,
                            twitter=excluded.twitter,
                            md5=excluded.md5
                         """

            rows_to_insert = []
            for pkg in pkgs:
                rows_to_insert.append(
                    (
                        pkg.content_id,
                        pkg.title_id,
                        pkg.title,
                        None,  # description
                        str(pkg.icon0_png_path),
                        str(pkg.pkg_path),
                        pkg.version,
                        None,  # picpath
                        None,  # desc1
                        None,  # desc2
                        None,  # review stars
                        pkg.pkg_path.stat().st_size,
                        None,  # author
                        pkg.app_type,
                        None,  # pv ?
                        (
                            str(pkg.pic0_png_path) if pkg.pic0_png_path else None
                        ),  # main_icon_path
                        (
                            str(pkg.pic1_png_path) if pkg.pic1_png_path else None
                        ),  # main_menu_pic
                        pkg.release_date,
                        0,  # number of downloads
                        None,  # github
                        None,  # video
                        None,  # twitter
                        None,  # md5
                    )
                )

            if rows_to_insert:
                conn.executemany(insert_sql, rows_to_insert)

            conn.commit()

            upserted_pkgs = len(rows_to_insert)
            LogUtils.log_info(
                f"{upserted_pkgs} PKGs upserted successfully", LogModule.DB_UTIL
            )

            return Output(Status.OK, len(rows_to_insert))
        except Exception as e:
            conn.rollback()
            LogUtils.log_error(
                f"Failed to upsert {len(pkgs)} PKGs in STORE.DB: {e}",
                LogModule.DB_UTIL,
            )
            return Output(Status.ERROR, len(pkgs))
        finally:
            conn.close()

    @staticmethod
    def generate_rows_md5() -> dict[str, str]:
        rows_md5_hash: dict[str, str] = {}
        store_db_file_path = Globals.FILES.STORE_DB_FILE_PATH

        if not store_db_file_path.exists():
            LogUtils.log_debug(
                f"Skipping {store_db_file_path.name.upper()} read. File not found",
                LogModule.DB_UTIL,
            )
            return rows_md5_hash

        columns = [col for col in StoreDB.Column]
        select_columns = ", ".join(f'"{name}"' for name in columns)
        query = f"SELECT {select_columns} FROM homebrews"

        conn = sqlite3.connect(str(store_db_file_path))
        conn.row_factory = sqlite3.Row
        try:
            for row in conn.execute(query).fetchall():
                key = row[StoreDB.Column.CONTENT_ID]
                values = [row[name] for name in columns]
                payload = json.dumps(
                    values, ensure_ascii=True, separators=(",", ":")
                ).encode("utf-8")
                rows_md5_hash[str(key)] = hashlib.md5(payload).hexdigest()
        except Exception as exc:
            LogUtils.log_error(
                f"Failed to generate STORE.DB md5: {exc}", LogModule.DB_UTIL
            )
        finally:
            conn.close()

        return rows_md5_hash


DBUtils = DBUtils()

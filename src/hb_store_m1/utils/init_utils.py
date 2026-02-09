import json
import sqlite3

from hb_store_m1.models.globals import Globals
from hb_store_m1.utils.log_utils import LogUtils


class InitUtils:

    @staticmethod
    def init_directories():
        LogUtils.log_debug("Initializing directories...")

        paths = Globals.PATHS
        for p in vars(paths).values():
            p.mkdir(parents=True, exist_ok=True)

        LogUtils.log_debug("Directories OK.")

    # TODO improve
    @staticmethod
    def init_db():
        store_db = Globals.FILES.STORE_DB_FILE_PATH
        store_db_init_script = Globals.FILES.STORE_DB_INIT_SCRIPT_FILE_PATH

        if store_db.exists():
            LogUtils.log_debug("store.db already exists. Skipping init.")
            return

        if not store_db_init_script.is_file():
            LogUtils.log_warn(
                f"store_db.sql not found at {store_db_init_script}. Skipping store.db init."
            )
            return

        sql = store_db_init_script.read_text("utf-8").strip()
        if not sql:
            LogUtils.log_warn(
                f"store_db.sql at {store_db_init_script} is empty. Skipping store.db init."
            )
            return

        store_db.parent.mkdir(parents=True, exist_ok=True)
        try:
            conn = sqlite3.connect(str(store_db))
            try:
                conn.executescript(sql)
                conn.commit()
            finally:
                conn.close()
            LogUtils.log_info(f"Initialized store.db at {store_db}")
        except sqlite3.Error as exc:
            LogUtils.log_error(f"Failed to initialize store.db: {exc}")

    # TODO improve
    @staticmethod
    def init_template_json():
        index_path = Globals.FILES.INDEX_JSON_FILE_PATH
        default_template = Globals.PATHS.INIT_DIR_PATH / "json_template.json"

        if index_path.exists():
            LogUtils.log_debug("index.json already exists. Skipping template init.")
            return

        if not default_template.is_file():
            LogUtils.log_warn(
                f"json_template.json not found at {default_template}. Skipping index.json init."
            )
            return

        template_raw = default_template.read_text("utf-8").strip()
        if not template_raw:
            LogUtils.log_warn(
                f"json_template.json at {default_template} is empty. Skipping index.json init."
            )
            return

        try:
            json.loads(template_raw)
        except json.JSONDecodeError as exc:
            LogUtils.log_warn(
                f"json_template.json at {default_template} is invalid JSON: {exc}"
            )
            return

        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(template_raw + "\n", encoding="utf-8")
        LogUtils.log_info(f"Initialized index.json at {index_path}")


InitUtils = InitUtils()

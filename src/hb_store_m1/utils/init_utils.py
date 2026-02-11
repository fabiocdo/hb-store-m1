import json
import sqlite3

from github import GithubException

from hb_store_m1.helpers.store_assets_client import StoreAssetClient
from hb_store_m1.models.globals import Globals
from hb_store_m1.models.log import LogModule
from hb_store_m1.utils.log_utils import LogUtils

log = LogUtils(LogModule.INIT_UTIL)


class InitUtils:

    @staticmethod
    def init_directories():
        log.log_debug("Initializing directories...")

        paths = Globals.PATHS
        for p in vars(paths).values():
            p.mkdir(parents=True, exist_ok=True)

        log.log_info("Directories OK")

    @staticmethod
    def init_db():
        store_db_file_path = Globals.FILES.STORE_DB_FILE_PATH
        store_db_init_script = Globals.FILES.STORE_DB_INIT_SCRIPT_FILE_PATH

        log.log_debug(
            f"Initializing {store_db_file_path.name} ..."
        )

        if store_db_file_path.exists():
            log.log_info(
                f"{store_db_file_path.name.upper()} OK"
            )
            return

        if not store_db_init_script.is_file():
            log.log_error(
                f"Failed to initialize {store_db_file_path.name}. "
                f"Initialization script {store_db_init_script.name} not found at {store_db_init_script.parent}"
            )
            return

        sql = store_db_init_script.read_text("utf-8").strip()
        if not sql:
            log.log_error(
                f"Failed to initialize {store_db_file_path.name}. "
                f"Initialization script {store_db_init_script.name} is empty"
            )
            return

        store_db_file_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            conn = sqlite3.connect(str(store_db_file_path))
            try:
                conn.executescript(sql)
                conn.commit()
            finally:
                conn.close()
            log.log_info(
                f"{store_db_file_path.name.upper()} OK"
            )
        except sqlite3.Error as exc:
            log.log_error(
                f"Failed to initialize {store_db_file_path.name}: {exc}"
            )

    @staticmethod
    def init_template_json():
        index_json_file_path = Globals.FILES.INDEX_JSON_FILE_PATH
        index_json_template = Globals.PATHS.INIT_DIR_PATH / "json_template.json"

        log.log_debug(
            f"Initializing {index_json_file_path.name} ..."
        )

        if index_json_file_path.exists():
            log.log_info(
                f"{index_json_file_path.name.upper()} OK"
            )
            return

        if not index_json_template.is_file():
            log.log_error(
                f"Failed to initialize {index_json_file_path.name}. "
                f"Initialization script {index_json_template.name} not found at {index_json_template.parent}"
            )
            return

        template_raw = index_json_template.read_text("utf-8").strip()
        if not template_raw:
            log.log_error(
                f"Failed to initialize {index_json_file_path.name}. "
                f"Initialization script {index_json_template.name} is empty"
            )
            return

        try:
            json.loads(template_raw)
            log.log_info(f"{index_json_file_path.name} OK")
        except json.JSONDecodeError as exc:
            log.log_error(
                f"Failed to initialize {index_json_file_path.name}: {exc}"
            )
            return

        index_json_file_path.parent.mkdir(parents=True, exist_ok=True)
        index_json_file_path.write_text(template_raw + "\n", encoding="utf-8")
        log.log_info(
            f"Initialized index.json at {index_json_file_path}"
        )

    @staticmethod
    def init_assets():
        log.log_debug("Initializing store assets...")

        assets = [
            Globals.FILES.HOMEBREW_ELF_FILE_PATH,
            Globals.FILES.HOMEBREW_ELF_SIG_FILE_PATH,
            Globals.FILES.REMOTE_MD5_FILE_PATH,
        ]

        try:
            downloaded, missing = StoreAssetClient.download_store_assets(assets)
            if missing:
                for asset in missing:
                    log.log_warn(
                        f"Failed to download asset. Assets {asset.name} not found in repository"
                    )
            else:
                log.log_info("Store assets OK...")
        except GithubException as e:
            log.log_error(
                f"Failed to download store assets: {e.data['message']}"
            )
        except Exception as e:
            log.log_error(
                f"Failed to download store assets: {e.__cause__}"
            )


InitUtils = InitUtils()

import time

from hb_store_m1.models.globals import Globals
from hb_store_m1.models.log import LogModule
from hb_store_m1.models.output import Status
from hb_store_m1.utils.cache_utils import CacheUtils
from hb_store_m1.utils.db_utils import DBUtils
from hb_store_m1.utils.log_utils import LogUtils
from hb_store_m1.utils.pkg_utils import PkgUtils


class Watcher:
    def __init__(self):
        self._interval = max(1, Globals.ENVS.WATCHER_PERIODIC_SCAN_SECONDS)
        self._cache_utils = CacheUtils
        self._pkg_utils = PkgUtils
        self._db_utils = DBUtils

    def _run_cycle(self) -> None:
        cache_output = self._cache_utils.compare_pkg_cache()
        changes = cache_output.content or {}
        changed_sections = changes.get("changed") or []

        if not changed_sections:
            LogUtils.log_info(
                "No cache changes detected. Skipping PKG scan.",
                LogModule.CACHE_UTIL,
            )
            return

        scanned_pkgs = self._pkg_utils.scan(changed_sections)
        extracted_pkgs = []
        for pkg_path in scanned_pkgs:
            result = self._pkg_utils.extract_pkg_data(pkg_path)
            if result.status is Status.OK and result.content:
                extracted_pkgs.append(result.content)

        upsert_result = self._db_utils.upsert(extracted_pkgs)
        if upsert_result.status in (Status.OK, Status.SKIP):
            self._cache_utils.write_pkg_cache()
            return

        LogUtils.log_error(
            "Store DB update failed. Cache not updated.",
            LogModule.DB_UTIL,
        )

    def start(self) -> None:
        LogUtils.log_info(
            f"Watcher started (interval: {self._interval}s)",
            LogModule.WATCHER,
        )
        while True:
            started_at = time.monotonic()
            try:
                self._run_cycle()
            except Exception as exc:
                LogUtils.log_error(
                    f"Watcher cycle failed: {exc}", LogModule.WATCHER
                )
            elapsed = time.monotonic() - started_at
            time.sleep(max(0.0, self._interval - elapsed))

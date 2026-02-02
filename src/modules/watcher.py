import os
import time
from src.utils import PkgUtils, log
from src.modules.auto_formatter import AutoFormatter
from src.modules.auto_sorter import AutoSorter
from src.modules.auto_indexer import AutoIndexer
from src.modules.helpers.watcher_planner import plan_pkgs
from src.modules.helpers.watcher_executor import execute_plan


class Watcher:
    """
    Orchestrates periodic planning, execution, and indexing.

    The watcher runs continuously with a fixed interval and skips work
    when no changes are detected.

    :param: None
    :return: None
    """

    def __init__(self):
        """
        Initialize watcher dependencies from env.

        :param: None
        :return: None
        """
        self.watcher_enabled = os.environ["WATCHER_ENABLED"].lower() == "true"
        self.periodic_scan_seconds = int(os.environ["WATCHER_PERIODIC_SCAN_SECONDS"])

        self.pkg_utils = PkgUtils()
        self.formatter = AutoFormatter()
        self.sorter = AutoSorter()
        self.indexer = AutoIndexer()

    def start(self):
        """
        Start the periodic watcher loop.

        :param: None
        :return: None
        """
        if not self.watcher_enabled:
            log("info", "Watcher is disabled. Skipping...", module="WATCHER")
            return
        interval = max(1, self.periodic_scan_seconds)
        log("info", f"Watcher started (interval: {interval}s)", module="WATCHER")
        next_run = time.monotonic()
        while True:
            now = time.monotonic()
            if now < next_run:
                time.sleep(next_run - now)
            start = time.monotonic()
            try:
                results, sfo_cache = plan_pkgs(self.pkg_utils, self.formatter, self.sorter)
                if not results:
                    next_run = start + interval
                    continue
                sfo_cache, _stats = execute_plan(
                    results,
                    sfo_cache,
                    self.pkg_utils,
                    self.formatter,
                    self.sorter,
                )
                self.indexer.run(results, sfo_cache)
            except Exception as exc:
                log("error", "Watcher cycle failed", message=str(exc), module="WATCHER")
            next_run = start + interval

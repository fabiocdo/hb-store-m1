from __future__ import annotations

import os
import time
import threading
from pathlib import Path
from src.utils import PkgUtils, log
from src.modules.auto_formatter import AutoFormatter
from src.modules.auto_sorter import AutoSorter
from src.modules.auto_indexer import AutoIndexer
from src.modules.helpers.watcher_planner import WatcherPlanner
from src.modules.helpers.watcher_executor import WatcherExecutor


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
        self.access_log_enabled = os.environ.get("WATCHER_ACCESS_LOG_TAIL").lower() == "true"
        self.access_log_path = "/data/_logs/access.log"
        self.access_log_interval = int(os.environ.get("WATCHER_ACCESS_LOG_INTERVAL"))
        self._access_log_offset = 0
        self._access_log_thread = None
        self._access_log_stop = threading.Event()

        self.pkg_utils = PkgUtils()
        self.formatter = AutoFormatter()
        self.sorter = AutoSorter()
        self.indexer = AutoIndexer()
        self.planner = WatcherPlanner(self.pkg_utils, self.formatter, self.sorter)
        self.executor = WatcherExecutor(self.pkg_utils, self.formatter, self.sorter)

    def _read_access_log(self) -> None:
        """
        Read new lines from the access log and emit them as debug logs.

        :param: None
        :return: None
        """
        if not self.access_log_enabled:
            return

        try:
            log_path = Path(self.access_log_path)
            if not log_path.exists():
                return
            size = log_path.stat().st_size
            if size < self._access_log_offset:
                self._access_log_offset = 0
            with log_path.open("r", encoding="utf-8", errors="ignore") as handle:
                handle.seek(self._access_log_offset)
                lines = handle.read().splitlines()
                self._access_log_offset = handle.tell()
            for line in lines:
                if line.strip():
                    log("debug", "Access log", message=line, module="WATCHER")
        except Exception as exc:
            log("warn", "Access log tail failed", message=str(exc), module="WATCHER")

    def _access_log_worker(self) -> None:
        """
        Background worker that tails the access log on an interval.

        :param: None
        :return: None
        """
        interval = max(1, self.access_log_interval)
        while not self._access_log_stop.is_set():
            self._read_access_log()
            self._access_log_stop.wait(interval)

    def _start_access_log_thread(self) -> None:
        """
        Start the access log tail thread if enabled.

        :param: None
        :return: None
        """
        if not self.access_log_enabled:
            return
        if self._access_log_thread and self._access_log_thread.is_alive():
            return
        self._access_log_thread = threading.Thread(target=self._access_log_worker, daemon=True)
        self._access_log_thread.start()

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
        self._start_access_log_thread()
        next_run = time.monotonic()
        while True:
            now = time.monotonic()
            if now < next_run:
                time.sleep(next_run - now)
            start = time.monotonic()
            try:
                results, sfo_cache = self.planner.plan()
                if not results:
                    next_run = start + interval
                    continue
                sfo_cache, _stats = self.executor.run(results, sfo_cache)
                self.indexer.run(results, sfo_cache)
            except Exception as exc:
                log("error", "Watcher cycle failed", message=str(exc), module="WATCHER")
            next_run = start + interval

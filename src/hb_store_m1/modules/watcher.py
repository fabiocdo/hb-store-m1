import time
from pathlib import Path

from hb_store_m1.models.globals import Globals
from hb_store_m1.models.log import LogModule
from hb_store_m1.models.output import Status
from hb_store_m1.modules.auto_organizer import AutoOrganizer
from hb_store_m1.models.pkg.section import Section
from hb_store_m1.utils.cache_utils import CacheUtils
from hb_store_m1.utils.db_utils import DBUtils
from hb_store_m1.utils.file_utils import FileUtils
from hb_store_m1.utils.log_utils import LogUtils
from hb_store_m1.utils.pkg_utils import PkgUtils


class Watcher:
    _MEDIA_SUFFIXES = ("_icon0.png", "_pic0.png", "_pic1.png")

    def __init__(self):
        self._interval = max(1, Globals.ENVS.WATCHER_PERIODIC_SCAN_SECONDS)
        self._cache_utils = CacheUtils
        self._db_utils = DBUtils
        self._auto_organizer = AutoOrganizer
        self._auto_organizer_enabled = Globals.ENVS.AUTO_ORGANIZER_ENABLED
        self._errors_dir = Globals.PATHS.ERRORS_DIR_PATH
        self._log_cache = LogUtils(LogModule.CACHE_UTIL)
        self._log_watcher = LogUtils(LogModule.WATCHER)
        self._log_db = LogUtils(LogModule.DB_UTIL)

    def _content_id_from_media(self, name: str) -> str | None:
        for suffix in self._MEDIA_SUFFIXES:
            if name.endswith(suffix):
                return name[: -len(suffix)]
        return None

    def _pkgs_from_media_changes(self, changes: dict) -> list[Path]:
        media_changes = []
        for key in ("added", "removed", "updated"):
            section_changes = changes.get(key, {})
            media_changes.extend(section_changes.get("_media", []) or [])

        if not media_changes:
            return []

        pkgs = []
        for media_name in media_changes:
            content_id = self._content_id_from_media(media_name)
            if not content_id:
                continue
            for section in Section.ALL:
                if section.name == "_media":
                    continue
                pkg_path = section.path / f"{content_id}.pkg"
                if pkg_path.exists():
                    pkgs.append(pkg_path)
                    break
        return pkgs

    def _run_cycle(self) -> None:
        cache_output = self._cache_utils.compare_pkg_cache()
        changes = cache_output.content or {}
        changed_sections = changes.get("changed") or []
        changed_section_set = set(changed_sections)

        if not changed_sections:
            self._log_cache.log_info("No changes detected.")
            return

        scan_sections = [section for section in changed_sections if section != "_media"]
        scanned_pkgs = PkgUtils.scan(scan_sections) if scan_sections else []
        scanned_pkgs.extend(self._pkgs_from_media_changes(changes))
        if scanned_pkgs:
            seen = set()
            scanned_pkgs = [
                pkg
                for pkg in scanned_pkgs
                if not (str(pkg) in seen or seen.add(str(pkg)))
            ]
        extracted_pkgs = []
        for pkg_path in scanned_pkgs:
            validation = PkgUtils.validate(pkg_path)
            if validation.status is Status.ERROR:
                FileUtils.move_to_error(
                    pkg_path,
                    self._errors_dir,
                    "validation_failed",
                )
                continue

            extract_output = PkgUtils.extract_pkg_data(pkg_path)

            if extract_output.status is not Status.OK or not extract_output.content:
                continue

            param_sfo, medias = extract_output.content
            build_output = PkgUtils.build_pkg(pkg_path, param_sfo, medias)

            if build_output.status is not Status.OK:
                continue

            pkg = build_output.content

            if (
                self._auto_organizer_enabled
                and pkg_path.parent.name in changed_section_set
            ):

                target_path = self._auto_organizer.run(pkg)

                if not target_path:
                    FileUtils.move_to_error(
                        pkg_path,
                        self._errors_dir,
                        "organizer_failed",
                    )
                    continue
                pkg.pkg_path = target_path

            extracted_pkgs.append(pkg)

        upsert_result = self._db_utils.upsert(extracted_pkgs)
        if upsert_result.status in (Status.OK, Status.SKIP):
            self._cache_utils.write_pkg_cache()
            return

        self._log_db.log_error("Store DB update failed. Cache not updated.")

    def start(self) -> None:
        self._log_watcher.log_info(f"Watcher started (interval: {self._interval}s)")
        while True:
            started_at = time.monotonic()
            try:
                self._run_cycle()
            except Exception as exc:
                self._log_watcher.log_error(f"Watcher cycle failed: {exc}")
            elapsed = time.monotonic() - started_at
            time.sleep(max(0.0, self._interval - elapsed))

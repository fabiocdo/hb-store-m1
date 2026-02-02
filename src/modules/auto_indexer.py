import os
from pathlib import Path
from src.utils import PkgUtils
from src.utils.log_utils import log
from src.utils.json_updater_utils import JsonUpdaterUtils


class AutoIndexer:
    """
    AutoIndexer handles the creation and maintenance of the store index.
    """

    def __init__(self):
        """
        Initialize the indexer.
        """
        raw_formats = os.environ["AUTO_INDEXER_OUTPUT_FORMAT"]
        self.output_formats = {
            part.strip().upper()
            for part in raw_formats.split(",")
            if part.strip()
        }

    def _scan_pkgs(self) -> tuple[list[dict], dict[str, dict]]:
        pkg_dir = Path(os.environ["PKG_DIR"])
        media_dir = Path(os.environ["MEDIA_DIR"])
        pkg_utils = PkgUtils()
        items = []
        sfo_cache: dict[str, dict] = {}

        for pkg in pkg_dir.rglob("*.pkg"):
            sfo_result, sfo_payload = pkg_utils.extract_pkg_data(pkg)
            if sfo_result != PkgUtils.ExtractResult.OK:
                continue
            sfo_cache[str(pkg)] = sfo_payload
            content_id = sfo_payload.get("content_id", "")
            icon_path = str(media_dir / f"{content_id}.png") if content_id else None
            items.append({
                "source_pkg_path": str(pkg),
                "planned_pkg_path": str(pkg),
                "planned_icon_path": icon_path,
                "planned_pkg_output": "skip",
                "planned_icon_output": "skip" if icon_path and Path(icon_path).exists() else "rejected",
            })
        return items, sfo_cache

    def dry_run(self) -> dict:
        """
        Build the index without writing it to disk.
        """
        items, sfo_cache = self._scan_pkgs()
        if "JSON" not in self.output_formats:
            return {}
        return JsonUpdaterUtils().build_index(items, sfo_cache)

    def run(self):
        """
        Execute the indexing process.
        """
        items, sfo_cache = self._scan_pkgs()
        if "JSON" in self.output_formats:
            log("info", "Writing index.json...", module="AUTO_INDEXER")
            JsonUpdaterUtils().update_json(items, sfo_cache)
            log("info", "Index update complete", module="AUTO_INDEXER")
        else:
            log("debug", "JSON output disabled. Skipping index.json", module="AUTO_INDEXER")

    def run_with_cache(self, items: list[dict], sfo_cache: dict[str, dict]) -> None:
        """
        Write the index using a provided plan and SFO cache.
        """
        if "JSON" in self.output_formats:
            JsonUpdaterUtils().update_json(items, sfo_cache)

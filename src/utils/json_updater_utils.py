import json
import os
from pathlib import Path
from urllib.parse import quote

class JsonUpdaterUtils:
    """
    Utilities for updating and reading the JSON index.
    """

    def build_index(self, items: list[dict], sfo_cache: dict[str, dict]) -> dict:
        """
        Build the JSON index in FPKGi format: {"DATA": {<pkg_url>: {...}}}.
        """
        data_dir = Path(os.environ["DATA_DIR"])
        pkg_dir = Path(os.environ["PKG_DIR"])
        base_url = os.environ["BASE_URL"].rstrip("/")

        index_data = {}
        for item in items:
            if item["planned_pkg_output"] == "rejected":
                continue

            pkg_path = Path(item["planned_pkg_path"])
            try:
                pkg_path.relative_to(pkg_dir)
            except ValueError:
                continue

            if not pkg_path.exists():
                pkg_path = Path(item["source_pkg_path"])

            try:
                rel_pkg = pkg_path.relative_to(data_dir).as_posix()
                pkg_url = f"{base_url}/{quote(rel_pkg, safe='/')}"
            except ValueError:
                pkg_url = pkg_path.name

            sfo_payload = sfo_cache.get(item["source_pkg_path"])
            if not sfo_payload:
                continue

            release_date = sfo_payload.get("release_date")
            if release_date and len(release_date) == 10:
                release_date = f"{release_date[5:7]}-{release_date[8:10]}-{release_date[0:4]}"

            cover_url = None
            if item["planned_icon_path"]:
                try:
                    rel_icon = Path(item["planned_icon_path"]).relative_to(data_dir).as_posix()
                    cover_url = f"{base_url}/{quote(rel_icon, safe='/')}"
                except ValueError:
                    cover_url = Path(item["planned_icon_path"]).name

            size_bytes = pkg_path.stat().st_size if pkg_path.exists() else 0
            index_data[pkg_url] = {
                "region": sfo_payload.get("region"),
                "name": sfo_payload.get("title"),
                "version": sfo_payload.get("version"),
                "release": release_date,
                "size": size_bytes,
                "min_fw": None,
                "cover_url": cover_url,
            }

        return {"DATA": index_data}

    def update_json(self, items: list[dict], sfo_cache: dict[str, dict]) -> None:
        """
        Update the JSON index with the latest indexed data.

        The output is written in FPKGi format: {"DATA": {<pkg_url>: {...}}}.
        """
        index_dir = Path(os.environ["INDEX_DIR"])

        index_dir.mkdir(parents=True, exist_ok=True)
        index_path = index_dir / "index.json"

        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(self.build_index(items, sfo_cache), f, ensure_ascii=False, indent=2, sort_keys=True)

    def read_json(self) -> dict:
        """
        Read data from the JSON index.
        """
        index_path = Path(os.environ["INDEX_DIR"]) / "index.json"
        if not index_path.exists():
            return {}
        with open(index_path, "r", encoding="utf-8") as f:
            return json.load(f)

from pathlib import Path
from src.utils import log


class AutoSorter:
    """
    AutoSorter handles PKG organization into category folders.

    It supports dry-run planning and real moving based on PKG category.
    """

    def __init__(self, category_map: dict | None = None):
        """
        Initialize the sorter.

        :param category_map: Dictionary mapping SFO category to folder name
        """
        self.category_map = category_map or {
            "ac": "dlc",
            "gc": "game",
            "gd": "game",
            "gp": "update",
            "sd": "save",
        }

    def dry_run(self, pkg_path: Path, category: str) -> Path | None:
        """
        Plan the PKG destination path without moving.

        :param pkg_path: Path object representing the PKG file
        :param category: SFO category (e.g. "gd", "ac")
        :return: Planned Path object
        """
        target_folder = self.category_map.get(category, "_unknown")
        destination_root = pkg_path.parent
        return destination_root / target_folder / pkg_path.name

    def run(self, pkg_path: Path, category: str) -> str | None:
        """
        Move the PKG file to its category folder.

        :param pkg_path: Path object representing the PKG file
        :param category: SFO category (e.g. "gd", "ac")
        :return: New path string if moved, otherwise None
        """
        target_path = self.dry_run(pkg_path, category)

        if not target_path or pkg_path == target_path:
            return None

        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            pkg_path.rename(target_path)
        except Exception:
            log("error", "AUTO SORTER ERROR", module="AUTO_SORTER")
            return None

        return str(target_path)

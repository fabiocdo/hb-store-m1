import settings
from pkg_metadata import load_pkg_data
from utils.rename_utils import maybe_rename_pkg


def run():
    if not settings.AUTO_RENAME_PKGS:
        return
    for pkg in settings.PKG_DIR.rglob("*.pkg"):
        if any(part.startswith("_") for part in pkg.parts):
            continue
        data, _ = load_pkg_data(pkg)
        maybe_rename_pkg(
            pkg,
            data.get("title"),
            data.get("titleid"),
            data.get("apptype"),
            data.get("region"),
            data.get("version"),
            data.get("category"),
            data.get("content_id"),
            data.get("app_type"),
        )

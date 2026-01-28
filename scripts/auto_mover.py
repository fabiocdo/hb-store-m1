import shutil

import settings
from pkg_metadata import load_pkg_data
from utils.log_utils import log


def run():
    if not settings.AUTO_MOVE_PKG:
        return
    for pkg in settings.PKG_DIR.rglob("*.pkg"):
        if any(part.startswith("_") for part in pkg.parts):
            continue
        data, _ = load_pkg_data(pkg)
        apptype = data.get("apptype")
        if apptype not in settings.APPTYPE_PATHS:
            continue
        if apptype == "app":
            continue
        if settings.APP_DIR in pkg.parents:
            continue
        target_dir = settings.APPTYPE_PATHS[apptype]
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / pkg.name

        if pkg.resolve() == target_path.resolve():
            continue
        if target_path.exists():
            log("error", f"Target already exists, skipping move: {target_path}")
            continue
        try:
            shutil.move(str(pkg), str(target_path))
            log("modified", f"Moved PKG to {target_path}")
        except Exception as e:
            log("error", f"Error moving PKG to {target_path}: {e}")

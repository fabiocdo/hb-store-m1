import shutil

import settings
from utils.log_utils import log


def run(pkgs):
    """Move PKGs into apptype folders when enabled."""
    moved = []
    skipped_existing = []
    errors = []

    excluded = set()
    if settings.AUTO_MOVER_EXCLUDED_DIRS:
        parts = [part.strip() for part in settings.AUTO_MOVER_EXCLUDED_DIRS.split(",")]
        excluded = {part for part in parts if part}
    for pkg, data in pkgs:
        apptype = data.get("apptype")
        if apptype not in settings.APPTYPE_PATHS:
            continue
        if apptype == "app":
            continue
        if settings.APP_DIR in pkg.parents:
            continue
        if any(part in excluded for part in pkg.parts):
            continue
        target_dir = settings.APPTYPE_PATHS[apptype]
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / pkg.name

        if pkg.resolve() == target_path.resolve():
            continue
        if target_path.exists():
            skipped_existing.append(str(target_path))
            continue
        try:
            shutil.move(str(pkg), str(target_path))
            moved.append((pkg, target_path))
        except Exception as e:
            errors.append((str(target_path), str(e)))

    if moved:
        log(
            "info",
            f"Moved {len(moved)} PKG(s)",
            module="AUTO_MOVER",
        )
    if skipped_existing:
        log(
            "error",
            f"Skipped {len(skipped_existing)} move(s); target already exists",
            module="AUTO_MOVER",
        )
    if errors:
        log(
            "error",
            f"Failed {len(errors)} move(s)",
            module="AUTO_MOVER",
        )

    touched_paths = []
    for src, dest in moved:
        touched_paths.extend([str(src), str(dest)])
    return {
        "moved": moved,
        "skipped_existing": skipped_existing,
        "errors": errors,
        "touched_paths": touched_paths,
    }

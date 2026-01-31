import shutil
from pathlib import Path

import settings
from utils.log_utils import format_log_line, log


def dry_run(pkgs, skip_paths=None):
    """Plan moves and report which entries can be moved."""
    plan = []
    skipped_conflict = []
    conflict_sources = []
    skip_set = {str(path) for path in (skip_paths or [])}
    skip_names = {Path(path).name for path in (skip_paths or [])}

    for pkg, data in pkgs:
        apptype = data.get("apptype")
        if apptype not in settings.APPTYPE_PATHS:
            continue
        target_dir = settings.APPTYPE_PATHS[apptype]
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / pkg.name

        if pkg.resolve() == target_path.resolve():
            continue
        if str(pkg) in skip_set or pkg.name in skip_names:
            log(
                "warn",
                "Skipped move. A file with the same name already exists in the target directory",
                module="AUTO_MOVER",
            )
            continue
        if target_path.exists():
            skipped_conflict.append(str(target_path))
            conflict_sources.append(str(pkg))
            continue
        plan.append((pkg, target_path))

    return {
        "plan": plan,
        "skipped_conflict": skipped_conflict,
        "conflict_sources": conflict_sources,
    }


def apply(dry_result):
    """Execute moves from a dry-run plan."""
    moved = []
    errors = []
    quarantined = []

    def append_error_log(error_dir, message):
        try:
            log_path = error_dir / "error_log.txt"
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(format_log_line(message, module="AUTO_MOVER") + "\n")
        except Exception:
            pass

    def quarantine_path(path):
        base = Path(path)
        if not base.exists():
            return None
        settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
        conflict_dir = settings.DATA_DIR / "_errors"
        conflict_dir.mkdir(parents=True, exist_ok=True)
        candidate = conflict_dir / base.name
        counter = 1
        while candidate.exists():
            if base.suffix:
                candidate = conflict_dir / f"{base.stem}_{counter}{base.suffix}"
            else:
                candidate = conflict_dir / f"{base.name}_{counter}"
            counter += 1
        try:
            base.rename(candidate)
            return candidate
        except Exception:
            return None
    for pkg, target_path in dry_result.get("plan", []):
        try:
            shutil.move(str(pkg), str(target_path))
            moved.append((pkg, target_path))
        except Exception as e:
            errors.append((str(target_path), str(e)))

    for src, dest in moved:
        log(
            "info",
            f"Moved: {src} -> {dest}",
            module="AUTO_MOVER",
        )
    for target in dry_result.get("skipped_conflict", []):
        log(
            "warn",
            "Skipped move. A file with the same name already exists in the target directory",
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
    for source in dry_result.get("conflict_sources", []):
        target = quarantine_path(source)
        if target is not None:
            quarantined.append(str(target))
            touched_paths.extend([source, str(target)])
            message = f"Moved file with error to {settings.DATA_DIR / '_errors'}: {source}"
            log("warn", message, module="AUTO_MOVER")
            append_error_log(settings.DATA_DIR / "_errors", message)
    return {"moved": moved, "errors": errors, "touched_paths": touched_paths, "quarantined_paths": quarantined}


def run(pkgs, skip_paths=None):
    """Move PKGs into apptype folders when enabled."""
    return apply(dry_run(pkgs, skip_paths=skip_paths))

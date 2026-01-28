import argparse
import shutil
import subprocess

import settings
from auto_indexer import run as run_indexer
from auto_mover import run as run_mover
from auto_renamer import run as run_renamer
from utils.pkg_utils import scan_pkgs
from utils.log_utils import log


def parse_settings():
    """Parse CLI args into settings."""
    parser = argparse.ArgumentParser()
    for flag, opts in settings.CLI_ARGS:
        parser.add_argument(flag, **opts)
    args = parser.parse_args()

    def parse_bool(value):
        if value is None:
            return False
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    settings.BASE_URL = args.base_url
    settings.PKG_WATCHER_ENABLED = parse_bool(args.pkg_watcher_enabled)
    settings.AUTO_RENAMER_ENABLED = parse_bool(args.auto_renamer_enabled)
    settings.AUTO_RENAMER_TEMPLATE = args.auto_renamer_template
    settings.AUTO_RENAMER_MODE = args.auto_renamer_mode.lower()
    settings.AUTO_RENAMER_EXCLUDED_DIRS = args.auto_renamer_excluded_dirs
    settings.AUTO_MOVER_ENABLED = parse_bool(args.auto_mover_enabled)
    settings.AUTO_MOVER_EXCLUDED_DIRS = args.auto_mover_excluded_dirs
    settings.AUTO_INDEXER_ENABLED = parse_bool(args.auto_indexer_enabled)


def watch(on_change):
    """Watch pkg directory and trigger rename/move/index updates."""
    if shutil.which("inotifywait") is None:
        log("error", "inotifywait not found; skipping watcher.")
        return
    if not settings.PKG_DIR.exists():
        return

    log("info", f"Starting watcher on {settings.PKG_DIR}")
    cmd = [
        "inotifywait",
        "-q",
        "-m",
        "-r",
        "-e",
        "create",
        "-e",
        "delete",
        "-e",
        "close_write",
        "-e",
        "moved_from",
        "-e",
        "moved_to",
        "--format",
        "%w%f|%e",
        str(settings.PKG_DIR),
    ]
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    if process.stdout is None:
        return

    for line in process.stdout:
        line = line.strip()
        if not line:
            continue
        if "|" not in line:
            log("debug", f"Watcher output: {line}", module="WATCHER")
            continue
        path, events = line.split("|", 1)
        log("debug", f"Captured events: {events} on {path}", module="WATCHER")
        on_change([(path, events)])


def start():
    """Entry point for the indexer watcher."""
    parse_settings()

    def parse_excluded(value):
        if not value:
            return set()
        parts = [part.strip() for part in value.split(",")]
        return {part for part in parts if part}

    def is_excluded(path, excluded_dirs):
        return any(part in excluded_dirs for part in path.parts)

    def filter_pkgs(pkgs, excluded_dirs, respect_apptype=False):
        if not excluded_dirs:
            return pkgs
        filtered = []
        for pkg, data in pkgs:
            if is_excluded(pkg, excluded_dirs):
                continue
            if respect_apptype:
                apptype = data.get("apptype")
                apptype_dir = settings.APPTYPE_PATHS.get(apptype) if apptype else None
                if apptype_dir and is_excluded(apptype_dir, excluded_dirs):
                    continue
            filtered.append((pkg, data))
        return filtered

    def run_automations(events=None):
        initial_run = events is None
        manual_events = []
        if not initial_run:
            for path, event_str in events:
                manual_events.append((path, event_str))

            if not manual_events:
                return

        if not settings.PKG_WATCHER_ENABLED:
            return
        pkgs = list(scan_pkgs()) if settings.PKG_DIR.exists() else []
        touched_paths = []
        renamer_excluded = parse_excluded(settings.AUTO_RENAMER_EXCLUDED_DIRS)
        mover_excluded = parse_excluded(settings.AUTO_MOVER_EXCLUDED_DIRS)
        blocked_sources = set()
        if settings.AUTO_RENAMER_ENABLED:
            eligible = filter_pkgs(pkgs, renamer_excluded, respect_apptype=True)
            result = run_renamer(eligible)
            touched_paths.extend(result.get("touched_paths", []))
            blocked_sources.update(result.get("blocked_sources", []))
            pkgs = list(scan_pkgs()) if settings.PKG_DIR.exists() else []
        if settings.AUTO_MOVER_ENABLED:
            if blocked_sources:
                pkgs = [(pkg, data) for pkg, data in pkgs if str(pkg) not in blocked_sources]
            eligible = filter_pkgs(pkgs, mover_excluded, respect_apptype=True)
            result = run_mover(eligible)
            touched_paths.extend(result.get("touched_paths", []))
            pkgs = list(scan_pkgs()) if settings.PKG_DIR.exists() else []
        if settings.AUTO_INDEXER_ENABLED:
            run_indexer(pkgs)


        if not initial_run:
            return

    run_automations()
    watch(run_automations)


if __name__ == "__main__":
    start()

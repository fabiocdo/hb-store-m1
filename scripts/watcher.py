import argparse
import shutil
import subprocess
import threading
import time

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
    settings.AUTO_INDEXER_DEBOUNCE_TIME_SECONDS = (
        args.auto_indexer_debounce_time_seconds
    )
    settings.WATCHER_EVENT_DEBOUNCE_SECONDS = args.watcher_event_debounce_seconds
    settings.AUTO_RENAMER_ENABLED = parse_bool(args.auto_renamer_enabled)
    settings.AUTO_RENAMER_TEMPLATE = args.auto_renamer_template
    settings.AUTO_RENAMER_MODE = args.auto_renamer_mode.lower()
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

    pending_events = []
    debounce_timer = None

    def flush_events():
        nonlocal pending_events, debounce_timer
        if not pending_events:
            debounce_timer = None
            return
        batch = pending_events
        pending_events = []
        debounce_timer = None
        on_change(batch)

    def schedule_flush():
        nonlocal debounce_timer
        if debounce_timer and debounce_timer.is_alive():
            debounce_timer.cancel()
        debounce_timer = threading.Timer(
            settings.WATCHER_EVENT_DEBOUNCE_SECONDS,
            flush_events,
        )
        debounce_timer.daemon = True
        debounce_timer.start()

    for line in process.stdout:
        line = line.strip()
        if not line:
            continue
        if "|" not in line:
            log("debug", f"Watcher output: {line}", module="WATCHER")
            continue
        path, events = line.split("|", 1)
        log("debug", f"Captured events: {events} on {path}", module="WATCHER")
        pending_events.append((path, events))
        schedule_flush()


def start():
    """Entry point for the indexer watcher."""
    parse_settings()
    debounce_timer = None
    last_event_at = None
    module_touched_until = {}

    def schedule_generate():
        nonlocal debounce_timer, last_event_at
        if not settings.AUTO_INDEXER_ENABLED:
            return
        last_event_at = time.monotonic()
        if debounce_timer and debounce_timer.is_alive():
            return

        def run():
            nonlocal debounce_timer
            now = time.monotonic()
            remaining = settings.AUTO_INDEXER_DEBOUNCE_TIME_SECONDS - (now - last_event_at)
            if remaining > 0:
                debounce_timer = threading.Timer(remaining, run)
                debounce_timer.daemon = True
                debounce_timer.start()
                return
            debounce_timer = None
            pkgs = list(scan_pkgs()) if settings.PKG_DIR.exists() else []
            run_indexer(pkgs)

        debounce_timer = threading.Timer(
            settings.AUTO_INDEXER_DEBOUNCE_TIME_SECONDS,
            run,
        )
        debounce_timer.daemon = True
        debounce_timer.start()

    def run_automations(events=None):
        initial_run = events is None
        manual_events = []
        if not initial_run:
            now = time.monotonic()
            for path, event_str in events:
                expires_at = module_touched_until.get(path)
                if expires_at is not None and expires_at >= now:
                    continue
                if expires_at is not None and expires_at < now:
                    module_touched_until.pop(path, None)
                manual_events.append((path, event_str))

            if not manual_events:
                return

        if not settings.PKG_WATCHER_ENABLED:
            return
        pkgs = list(scan_pkgs()) if settings.PKG_DIR.exists() else []
        touched_paths = []
        if settings.AUTO_RENAMER_ENABLED:
            result = run_renamer(pkgs)
            touched_paths.extend(result.get("touched_paths", []))
            pkgs = list(scan_pkgs()) if settings.PKG_DIR.exists() else []
        if settings.AUTO_MOVER_ENABLED:
            result = run_mover(pkgs)
            touched_paths.extend(result.get("touched_paths", []))
            pkgs = list(scan_pkgs()) if settings.PKG_DIR.exists() else []
        if settings.AUTO_INDEXER_ENABLED:
            if initial_run:
                run_indexer(pkgs)
            else:
                schedule_generate()

        if touched_paths:
            expires_at = time.monotonic() + settings.WATCHER_EVENT_DEBOUNCE_SECONDS
            for path in touched_paths:
                module_touched_until[path] = expires_at

        created = set()
        moved = set()
        deleted = set()
        for path, event_str in manual_events:
            events = {item.strip() for item in event_str.split(",") if item.strip()}
            if "MOVED_FROM" in events or "MOVED_TO" in events:
                moved.add(path)
                continue
            if "DELETE" in events:
                deleted.add(path)
                continue
            if "CREATE" in events or "CLOSE_WRITE" in events:
                created.add(path)

        if not initial_run and (created or moved or deleted):
            parts = []
            if created:
                parts.append(f"created {len(created)}")
            if moved:
                parts.append(f"moved {len(moved)}")
            if deleted:
                parts.append(f"deleted {len(deleted)}")
            log("debug", f"Manual changes detected: {', '.join(parts)}")

    run_automations()
    watch(run_automations)


if __name__ == "__main__":
    start()

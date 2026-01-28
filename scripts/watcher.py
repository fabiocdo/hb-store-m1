import shutil
import subprocess
import threading

from index_builder import build_index
from utils.log_utils import log
from settings import PKG_DIR


def watch_pkg_dir(auto_generate_json_period):
    if shutil.which("inotifywait") is None:
        log("error", "inotifywait not found; skipping watcher.")
        return
    if not PKG_DIR.exists():
        return

    last_moved_from = ""
    debounce_timer = None

    def schedule_generate():
        nonlocal debounce_timer
        if debounce_timer and debounce_timer.is_alive():
            debounce_timer.cancel()

        def run():
            nonlocal debounce_timer
            debounce_timer = None
            build_index(False)

        debounce_timer = threading.Timer(auto_generate_json_period, run)
        debounce_timer.daemon = True
        debounce_timer.start()

    cmd = [
        "inotifywait",
        "-m",
        "-r",
        "-e",
        "create",
        "-e",
        "delete",
        "-e",
        "move",
        "-e",
        "close_write",
        "--format",
        "%w%f|%e",
        str(PKG_DIR),
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
            log("info", line)
            continue
        path, events = line.split("|", 1)
        if "MOVED_FROM" in events:
            last_moved_from = path
            continue
        if "MOVED_TO" in events:
            if last_moved_from:
                log("modified", f"Moved: {last_moved_from} -> {path}")
                last_moved_from = ""
            else:
                log("modified", f"Moved: {path}")
            if build_index(True) == 0:
                schedule_generate()
            continue
        if "CREATE" in events or "DELETE" in events:
            if "DELETE" in events:
                log("deleted", f"Change detected: {events} {path}")
            else:
                log("created", f"Change detected: {events} {path}")
            if build_index(True) == 0:
                schedule_generate()
            continue
        log("modified", f"Change detected: {events} {path}")
        if build_index(True) == 0:
            schedule_generate()

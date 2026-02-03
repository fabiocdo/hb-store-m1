from __future__ import annotations

from os import environ
from pathlib import Path


global_paths = {
    "DATA_DIR_PATH": Path("/data"),
    "CACHE_DIR_PATH": Path("/data/_cache"),
    "ERROR_DIR_PATH": Path("/data/_error"),
    "LOGS_DIR_PATH": Path("/data/_logs"),
    "PKG_DIR_PATH": Path("/data/pkg"),
    "MEDIA_DIR_PATH": Path("/data/pkg/_media"),
    "APP_DIR_PATH": Path("/data/pkg/app"),
    "GAME_DIR_PATH": Path("/data/pkg/game"),
    "DLC_DIR_PATH": Path("/data/pkg/dlc"),
    "UPDATE_DIR_PATH": Path("/data/pkg/update"),
    "SAVE_DIR_PATH": Path("/data/pkg/save"),
    "UNKNOWN_DIR_PATH": Path("/data/pkg/_unknown"),
}
global_files = {
    "PKGTOOL_PATH": Path("/app/bin/pkgtool"),
    "INDEX_JSON_FILE_PATH": Path("/data/index.json"),
    "STORE_DB_FILE_PATH": Path("/data/store.db"),
    # metadata & dumps
    "INDEX_CACHE_JSON_FILE_PATH": Path("/data/_cache/index-cache.json"),
    "STORE_DB_JSON_FILE_PATH": Path("/data/_cache/store.db.json"),  # TODO: mudar -> é um arquivo de hash do banco
    "STORE_DB_MD5_FILE_PATH": Path("/data/_cache/store.db.md5"),  # TODO: mudar -> usar um arquivo de cache do banco só
    "HOMEBREW_ELF_FILE_PATH": Path("/data/_cache/homebrew.elf"),
    "HOMEBREW_ELF_SIG_FILE_PATH": Path("/data/_cache/homebrew.elf.sig"),
    "ERRORS_LOG_FILE_PATH": Path("/data/_error/errors.log"),
}

global_envs = {
    "SERVER_IP", environ.get("SERVER_IP", ""),
    "LOG_LEVEL", environ.get("LOG_LEVEL", "").upper(),
    "ENABLE_SSL", environ.get("ENABLE_SSL", "").upper() == True,
    "WATCHER_ENABLED", environ.get("WATCHER_ENABLED", "") == True,
    "WATCHER_PERIODIC_SCAN_SECONDS", int(environ.get("WATCHER_PERIODIC_SCAN_SECONDS", "")),
    "WATCHER_SCAN_BATCH_SIZE", int(environ.get("WATCHER_SCAN_BATCH_SIZE", "")),
    "WATCHER_SCAN_WORKERS", int(environ.get("WATCHER_SCAN_WORKERS", "")),
    "WATCHER_ACCESS_LOG_TAIL", environ.get("WATCHER_ACCESS_LOG_TAIL", "") == True, # TODO: renomeie para _ENABLED
    "WATCHER_ACCESS_LOG_INTERVAL", int(environ.get("WATCHER_ACCESS_LOG_INTERVAL", "")),
    "AUTO_INDEXER_OUTPUT_FORMAT", [item.strip().upper() for item in environ.get("AUTO_INDEXER_OUTPUT_FORMAT", "").split(",") if item.strip()],
}

def init():
    global global_paths
    global global_files
    global global_envs


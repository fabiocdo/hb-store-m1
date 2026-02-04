from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

def env(name: str, default, type_):
    v = os.getenv(name)
    if v is None:
        return default

    v = v.strip()

    if type_ is bool:
        vl = v.lower()
        if vl == "true":
            return True
        if vl == "false":
            return False
        raise ValueError(f"{name} must be 'true' or 'false', got {v!r}")

    if type_ is int:
        return default if v == "" else int(v)

    if type_ is str:
        return v

    if type_ is list:
        return default if v == "" else [p.strip() for p in v.split(",") if p.strip()]

    raise TypeError(f"Unsupported type {type_}")

@dataclass(frozen=True)
class GlobalPaths:
    DATA_DIR_PATH: Path = Path("/data")
    CACHE_DIR_PATH: Path = Path("/data/_cache")
    ERROR_DIR_PATH: Path = Path("/data/_error")
    LOGS_DIR_PATH: Path = Path("/data/_logs")
    PKG_DIR_PATH: Path = Path("/data/pkg")
    MEDIA_DIR_PATH: Path = Path("/data/pkg/_media")
    APP_DIR_PATH: Path = Path("/data/pkg/app")
    GAME_DIR_PATH: Path = Path("/data/pkg/game")
    DLC_DIR_PATH: Path = Path("/data/pkg/dlc")
    UPDATE_DIR_PATH: Path = Path("/data/pkg/update")
    SAVE_DIR_PATH: Path = Path("/data/pkg/save")
    UNKNOWN_DIR_PATH: Path = Path("/data/pkg/_unknown")


@dataclass(frozen=True)
class GlobalFiles:
    PKGTOOL_PATH: Path = Path("/app/bin/pkgtool")
    INDEX_JSON_FILE_PATH: Path = Path("/data/index.json")
    STORE_DB_FILE_PATH: Path = Path("/data/store.db")
    INDEX_CACHE_JSON_FILE_PATH: Path = Path("/data/_cache/index-cache.json")
    STORE_DB_JSON_FILE_PATH: Path = Path("/data/_cache/store.db.json")
    STORE_DB_MD5_FILE_PATH: Path = Path("/data/_cache/store.db.md5")
    HOMEBREW_ELF_FILE_PATH: Path = Path("/data/_cache/homebrew.elf")
    HOMEBREW_ELF_SIG_FILE_PATH: Path = Path("/data/_cache/homebrew.elf.sig")
    ERRORS_LOG_FILE_PATH: Path = Path("/data/_error/errors.log")


class GlobalEnvs:
    # APP_NAME: str = env(pyproject_value("name"), "", str)
    # APP_VERSION: str = env(pyproject_value("version"), "", str)
    SERVER_IP: str = env("SERVER_IP", "127.0.0.1", str)
    LOG_LEVEL: str = env("LOG_LEVEL", "info", str)
    ENABLE_SSL: bool = env("ENABLE_SSL", False, bool)
    WATCHER_ENABLED: bool = env("WATCHER_ENABLED", True, bool)
    WATCHER_PERIODIC_SCAN_SECONDS: int = env("WATCHER_PERIODIC_SCAN_SECONDS", 30, int)
    WATCHER_SCAN_BATCH_SIZE: int = env("WATCHER_SCAN_BATCH_SIZE", 50, int)
    WATCHER_EXECUTOR_WORKERS: int = env("WATCHER_EXECUTOR_WORKERS", 4, int)
    WATCHER_SCAN_WORKERS: int = env("WATCHER_SCAN_WORKERS", 4, int)
    WATCHER_ACCESS_LOG_TAIL: int = env("WATCHER_ACCESS_LOG_TAIL", True, bool)
    WATCHER_ACCESS_LOG_INTERVAL: int = env("WATCHER_ACCESS_LOG_INTERVAL", 5, int)
    AUTO_INDEXER_OUTPUT_FORMAT: list[str] = env("AUTO_INDEXER_OUTPUT_FORMAT", ['db','json'], list)


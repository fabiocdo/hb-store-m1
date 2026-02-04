from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    v = v.strip().lower()
    if v == "true":
        return True
    if v == "false":
        return False
    raise ValueError(f"{name} must be 'true' or 'false', got {v!r}")


def env_list(name: str, default: list[str]) -> list[str]:
    v = os.getenv(name)
    if not v:
        return default
    return [p.strip() for p in v.split(",") if p.strip()]

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
    PYPROJECT_TOML_FILE_PATH: Path = Path("/app/pyproject.toml")
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
    SERVER_IP = os.getenv("SERVER_IP", "127.0.0.1")
    SERVER_PORT = int(os.getenv("SERVER_PORT", "80"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
    ENABLE_SSL = env_bool("ENABLE_SSL", False)

    WATCHER_ENABLED = env_bool("WATCHER_ENABLED", True)
    WATCHER_PERIODIC_SCAN_SECONDS = int(os.getenv("WATCHER_PERIODIC_SCAN_SECONDS", "30"))
    WATCHER_SCAN_BATCH_SIZE = int(os.getenv("WATCHER_SCAN_BATCH_SIZE", "50"))
    WATCHER_EXECUTOR_WORKERS = int(os.getenv("WATCHER_EXECUTOR_WORKERS", "4"))
    WATCHER_SCAN_WORKERS = int(os.getenv("WATCHER_SCAN_WORKERS", "4"))
    WATCHER_ACCESS_LOG_TAIL = env_bool("WATCHER_ACCESS_LOG_TAIL", True)
    WATCHER_ACCESS_LOG_INTERVAL = int(os.getenv("WATCHER_ACCESS_LOG_INTERVAL", "5"))

    AUTO_INDEXER_OUTPUT_FORMAT = env_list("AUTO_INDEXER_OUTPUT_FORMAT", ["db", "json"])

    @property
    def SERVER_URL(self) -> str:
        scheme = "https" if self.ENABLE_SSL else "http"
        default_port = 443 if self.ENABLE_SSL else 80

        if self.SERVER_PORT == default_port:
            return f"{scheme}://{self.SERVER_IP}"
        return f"{scheme}://{self.SERVER_IP}:{self.SERVER_PORT}"


global_paths = GlobalPaths()
global_files = GlobalFiles()
global_envs = GlobalEnvs()

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

def _pyproject_value(path: Path, key: str, default: str = "") -> str:
    if not path.exists():
        return default

    data = tomllib.loads(path.read_text("utf-8"))
    return data.get("project", {}).get(key, default)

def _env(name: str, default, type_):
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

APP_ROOT = Path.cwd()
DATA_ROOT = APP_ROOT / "data"

@dataclass(frozen=True)
class GlobalPaths:
    DATA_DIR_PATH: Path = DATA_ROOT
    CACHE_DIR_PATH: Path = DATA_ROOT / "_cache"
    ERROR_DIR_PATH: Path = DATA_ROOT / "_error"
    LOGS_DIR_PATH: Path = DATA_ROOT / "_logs"
    PKG_DIR_PATH: Path = DATA_ROOT / "pkg"
    MEDIA_DIR_PATH: Path = PKG_DIR_PATH / "_media"
    APP_DIR_PATH: Path = PKG_DIR_PATH / "app"
    GAME_DIR_PATH: Path = PKG_DIR_PATH / "game"
    DLC_DIR_PATH: Path = PKG_DIR_PATH / "dlc"
    UPDATE_DIR_PATH: Path = PKG_DIR_PATH / "update"
    SAVE_DIR_PATH: Path = PKG_DIR_PATH / "save"
    UNKNOWN_DIR_PATH: Path = PKG_DIR_PATH / "_unknown"


@dataclass(frozen=True)
class GlobalFiles:
    PYPROJECT_PATH: Path = APP_ROOT / "pyproject.toml"
    PKGTOOL_PATH: Path = APP_ROOT / "bin" / "pkgtool"
    INDEX_JSON_FILE_PATH: Path = DATA_ROOT / "index.json"
    STORE_DB_FILE_PATH: Path = DATA_ROOT / "store.db"
    INDEX_CACHE_JSON_FILE_PATH: Path = DATA_ROOT / "_cache" / "index-cache.json"
    STORE_DB_JSON_FILE_PATH: Path = DATA_ROOT / "_cache" / "store.db.json"
    STORE_DB_MD5_FILE_PATH: Path = DATA_ROOT / "_cache" / "store.db.md5"
    HOMEBREW_ELF_FILE_PATH: Path = DATA_ROOT / "_cache" / "homebrew.elf"
    HOMEBREW_ELF_SIG_FILE_PATH: Path = DATA_ROOT / "_cache" / "homebrew.elf.sig"
    ERRORS_LOG_FILE_PATH: Path = DATA_ROOT / "_error" / "errors.log"

class GlobalEnvs:
    APP_NAME: str = _pyproject_value(GlobalFiles.PYPROJECT_PATH,"name","homebrew-store-cdn")
    APP_VERSION: str = _pyproject_value(GlobalFiles.PYPROJECT_PATH,"version","0.0.1")
    SERVER_IP: str = _env("SERVER_IP", "127.0.0.1", str)
    SERVER_PORT: str = _env("SERVER_PORT", "80", str)
    LOG_LEVEL: str = _env("LOG_LEVEL", "info", str)
    ENABLE_SSL: bool = _env("ENABLE_SSL", False, bool)
    WATCHER_ENABLED: bool = _env("WATCHER_ENABLED", True, bool)
    WATCHER_PERIODIC_SCAN_SECONDS: int = _env("WATCHER_PERIODIC_SCAN_SECONDS", 30, int)
    WATCHER_SCAN_BATCH_SIZE: int = _env("WATCHER_SCAN_BATCH_SIZE", 50, int)
    WATCHER_EXECUTOR_WORKERS: int = _env("WATCHER_EXECUTOR_WORKERS", 4, int)
    WATCHER_SCAN_WORKERS: int = _env("WATCHER_SCAN_WORKERS", 4, int)
    WATCHER_ACCESS_LOG_TAIL: bool = _env("WATCHER_ACCESS_LOG_TAIL", True, bool)
    WATCHER_ACCESS_LOG_INTERVAL: int = _env("WATCHER_ACCESS_LOG_INTERVAL", 5, int)
    AUTO_INDEXER_OUTPUT_FORMAT: list[str] = _env("AUTO_INDEXER_OUTPUT_FORMAT", ['db','json'], list)

    @property
    def SERVER_URL(self) -> str:
        scheme = "https" if self.ENABLE_SSL else "http"
        default_port = 443 if self.ENABLE_SSL else 80
        return (
            f"{scheme}://{self.SERVER_IP}"
            if self.SERVER_PORT == default_port
            else f"{scheme}://{self.SERVER_IP}:{self.SERVER_PORT}"
        )


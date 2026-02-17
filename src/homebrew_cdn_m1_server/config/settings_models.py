from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class OutputTarget(StrEnum):
    HB_STORE = "hb-store"
    FPKGI = "fpkgi"


class UserSettings(BaseModel):
    server_ip: str = Field(default="127.0.0.1")
    server_port: int = Field(default=80, ge=1, le=65535)
    enable_tls: bool = Field(default=False)
    log_level: str = Field(default="info")
    watcher_pkg_preprocess_workers: int = Field(default=1, ge=1)
    watcher_cron_expression: str = Field(default="")
    output_targets: tuple[OutputTarget, ...] = Field(
        default=(OutputTarget.HB_STORE, OutputTarget.FPKGI)
    )
    pkgtool_timeout_seconds: int = Field(default=300, ge=1)

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in {"debug", "info", "warn", "warning", "error"}:
            raise ValueError("LOG_LEVEL must be one of: debug, info, warn, error")
        return "warning" if normalized == "warn" else normalized


@dataclass(frozen=True)
class RuntimePaths:
    app_root: Path
    init_dir: Path
    data_dir: Path
    internal_dir: Path
    share_dir: Path
    hb_store_share_dir: Path
    fpkgi_share_dir: Path
    catalog_dir: Path
    cache_dir: Path
    logs_dir: Path
    errors_dir: Path
    hb_store_update_dir: Path
    public_index_path: Path
    pkg_root: Path
    media_dir: Path
    app_dir: Path
    game_dir: Path
    dlc_dir: Path
    pkg_update_dir: Path
    save_dir: Path
    unknown_dir: Path
    catalog_db_path: Path
    store_db_path: Path
    snapshot_path: Path
    settings_path: Path
    pkgtool_bin_path: Path


@dataclass(frozen=True)
class AppConfig:
    user: UserSettings
    paths: RuntimePaths
    watcher_interval_seconds: int = 30
    watcher_file_stable_seconds: int = 15

    @property
    def base_url(self) -> str:
        scheme = "https" if self.user.enable_tls else "http"
        default_port = 443 if self.user.enable_tls else 80
        if self.user.server_port == default_port:
            return f"{scheme}://{self.user.server_ip}"
        return f"{scheme}://{self.user.server_ip}:{self.user.server_port}"

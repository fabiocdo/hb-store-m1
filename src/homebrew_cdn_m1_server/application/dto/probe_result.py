from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from homebrew_cdn_m1_server.domain.value_objects.app_type import AppType
from homebrew_cdn_m1_server.domain.value_objects.content_id import ContentId


@dataclass(frozen=True, slots=True)
class ProbeResult:
    content_id: ContentId
    title_id: str
    title: str
    category: str
    version: str
    pubtoolinfo: str
    system_ver: str
    app_type: AppType
    release_date: str
    sfo_fields: Mapping[str, str]
    sfo_raw: bytes
    sfo_hash: str
    icon0_path: Path | None
    pic0_path: Path | None
    pic1_path: Path | None

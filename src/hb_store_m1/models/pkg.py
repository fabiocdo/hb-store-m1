from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class EntryKey(StrEnum):
    PARAM_SFO = "PARAM_SFO"
    ICON0_PNG = "ICON0_PNG"
    PIC0_PNG = "PIC0_PNG"
    PIC1_PNG = "PIC1_PNG"


class ParamSFOKey(StrEnum):
    APP_VER = "APP_VER"
    CATEGORY = "CATEGORY"
    CONTENT_ID = "CONTENT_ID"
    PUBTOOLINFO = "PUBTOOLINFO"
    SYSTEM_VER = "SYSTEM_VER"
    TITLE = "TITLE"
    TITLE_ID = "TITLE_ID"
    VERSION = "VERSION"


class Region(StrEnum):
    UP = "USA"
    EP = "EUR"
    JP = "JAP"
    HP = "ASIA"
    AP = "ASIA"
    KP = "ASIA"
    UNKNOWN = "UNKNOWN"


class AppType(StrEnum):
    AC = "dlc"
    GC = "game"
    GD = "game"
    GP = "update"
    SD = "save"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class PKG:
    title: str = ""
    title_id: str = ""
    content_id: str = ""
    category: str = ""
    version: str = ""
    release_date: str = ""
    region: Region | None = None
    app_type: AppType | None = None
    Entries: dict[EntryKey, int] = field(default_factory=dict)
    ParamSFO: dict[ParamSFOKey, str | int] = field(default_factory=dict)

    def __post_init__(self) -> None:

        # app_type value
        cat = self.category.strip().upper()
        self.app_type = AppType.__members__.get(cat, AppType.UNKNOWN)

        # region value
        if len(self.content_id) >= 2:
            prefix = self.content_id[:2].upper()
            self.region = Region.__members__.get(prefix, AppType.UNKNOWN)

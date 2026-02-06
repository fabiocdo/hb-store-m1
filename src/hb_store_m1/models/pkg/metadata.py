from dataclasses import dataclass
from enum import StrEnum, auto


class EntryKey(StrEnum):
    PARAM_SFO = auto()
    ICON0_PNG = auto()
    PIC0_PNG = auto()
    PIC1_PNG = auto()


@dataclass(slots=True)
class ParamSFO:
    APP_VER: str = ""
    CATEGORY: str = ""
    CONTENT_ID: str = ""
    PUBTOOLINFO: str = ""
    SYSTEM_VER: str = ""
    TITLE: str = ""
    TITLE_ID: str = ""
    VERSION: str = ""


@dataclass(slots=True)
class PKGEntry:
    key: EntryKey
    index: int

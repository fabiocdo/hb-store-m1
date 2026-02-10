import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum


@dataclass(slots=True, frozen=True)
class StoreDB:
    class Column(StrEnum):
        ID = "id"
        NAME = "name"
        CONTENT_ID = "content_id"
        DESC = "desc"
        IMAGE = "image"
        PACKAGE = "package"
        VERSION = "version"
        PIC_PATH = "picpath"
        DESC_1 = "desc_1"
        DESC_2 = "desc_2"
        REVIEW_STARS = "ReviewStars"
        SIZE = "Size"
        AUTHOR = "Author"
        APP_TYPE = "apptype"
        PV = "pv"
        MAIN_ICON_PATH = "main_icon_path"
        MAIN_MENU_PIC = "main_menu_pic"
        RELEASEDDATE = "releaseddate"
        NUMBER_OF_DOWNLOADS = "number_of_downloads"
        GITHUB = "github"
        VIDEO = "video"
        TWITTER = "twitter"
        MD5 = "md5"

    rows: tuple[dict[Column, str | float | int | None], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "rows", tuple(self.rows))

    def generate_rows_md5_hash(self) -> dict[str, str]:
        rows_md5_hash: dict[str, str] = {}

        for row in self.rows:
            key = row[self.Column.CONTENT_ID]
            values = [row[col] for col in self.Column]
            payload = json.dumps(
                values, ensure_ascii=True, separators=(",", ":")
            ).encode("utf-8")
            rows_md5_hash[str(key)] = hashlib.md5(payload).hexdigest()

        return rows_md5_hash

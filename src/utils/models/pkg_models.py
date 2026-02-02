from __future__ import annotations

from enum import Enum


class ExtractResult(Enum):
    """
    Enumeration of PKG extraction outcomes.

    :param: None
    :return: None
    """
    OK = "ok"
    NOT_FOUND = "not_found"
    INVALID = "invalid"
    ERROR = "error"


REGION_MAP = {
    "UP": "USA",
    "EP": "EUR",
    "JP": "JAP",
    "HP": "ASIA",
    "AP": "ASIA",
    "KP": "ASIA",
}

APP_TYPE_MAP = {
    "ac": "dlc",
    "gc": "game",
    "gd": "game",
    "gp": "update",
    "sd": "save",
}

SELECTED_FIELDS = (
    "TITLE",
    "TITLE_ID",
    "CONTENT_ID",
    "CATEGORY",
    "VERSION",
    "RELEASE_DATE",
    "REGION",
    "APP_TYPE",
)

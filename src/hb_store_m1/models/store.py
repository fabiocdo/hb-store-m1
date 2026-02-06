from enum import StrEnum


class Store:
    class AppType(StrEnum):
        GAME = "game"
        UPDATE = "patch"
        DLC = "dlc"
        THEME = "theme"
        APP = "app"
        SAVE = "other"
        OTHER = "other"

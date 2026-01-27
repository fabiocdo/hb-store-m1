import pathlib

DATA_DIR = pathlib.Path("/data")

PKG_DIR = DATA_DIR / "pkg"
MEDIA_DIR = DATA_DIR / "_media"
CACHE_DIR = DATA_DIR / "_cache"

GAME_DIR = PKG_DIR / "game"
DLC_DIR = PKG_DIR / "dlc"
UPDATE_DIR = PKG_DIR / "update"
APP_DIR = PKG_DIR / "app"

APPTYPE_PATHS = {
    "game": GAME_DIR,
    "dlc": DLC_DIR,
    "update": UPDATE_DIR,
    "app": APP_DIR,
}

INDEX_PATH = DATA_DIR / "index.json"
CACHE_PATH = CACHE_DIR / "index-cache.json"

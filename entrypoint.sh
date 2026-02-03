#!/bin/sh
set -e

TERM="${TERM:-xterm}"
export TERM

# PATHs
DATA_DIR="/data"
PKG_DIR="${DATA_DIR}/pkg"
GAME_DIR="${PKG_DIR}/game"
DLC_DIR="${PKG_DIR}/dlc"
UPDATE_DIR="${PKG_DIR}/update"
SAVE_DIR="${PKG_DIR}/save"
UNKNOWN_DIR="${PKG_DIR}/_unknown"
MEDIA_DIR="${PKG_DIR}/_media"
CACHE_DIR="${DATA_DIR}/_cache"
ERROR_DIR="${DATA_DIR}/_error"
LOG_DIR="${DATA_DIR}/_logs"
STORE_DIR="${DATA_DIR}"
INDEX_DIR="${DATA_DIR}"
STORE_DB_PATH="${DATA_DIR}/store.db"

log() {
  printf "%s %s\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

create_path() {
  target="$1"
  label="$2"
  root="$3"
  if [ ! -d "$target" ]; then
    mkdir -p "$target"
    if [ -n "$label" ] && [ -n "$root" ]; then
      log "Initialized ${label} directory at ${root}"
    else
      log "Initialized directory at $target"
    fi
    initialized_any="true"
  fi
}

initialize_data_dir(){
  log "Initializing directories and files..."
  initialized_any="false"
  create_path "$GAME_DIR" "game/" "$PKG_DIR/"
  create_path "$DLC_DIR" "dlc/" "$PKG_DIR/"
  create_path "$UPDATE_DIR" "update/" "$PKG_DIR/"
  create_path "$SAVE_DIR" "save/" "$PKG_DIR/"
  create_path "$UNKNOWN_DIR" "_unknown/" "$PKG_DIR/"
  create_path "$MEDIA_DIR" "_media/" "$PKG_DIR/"
  create_path "$CACHE_DIR" "_cache/" "$DATA_DIR/"
  create_path "$ERROR_DIR" "_error/" "$DATA_DIR/"
  create_path "$LOG_DIR" "_logs/" "$DATA_DIR/"
  marker_path="$PKG_DIR/_PUT_YOUR_PKGS_HERE"
  if [ ! -f "$marker_path" ]; then
    printf "%s\n" "Place PKG files in this directory or its subfolders." > "$marker_path"
    log "Initialized _PUT_YOUR_PKGS_HERE marker at $PKG_DIR/"
    initialized_any="true"
  fi
  if [ "$initialized_any" != "true" ]; then
    log "Great! Nothing to initialize!"
  fi
}

initialize_store_db() {
  if ! command -v sqlite3 >/dev/null 2>&1; then
    log "sqlite3 not found; skipping store.db initialization."
    return
  fi
  if [ ! -f "$STORE_DB_PATH" ]; then
    log "Initializing store.db at $STORE_DB_PATH"
  fi
  sqlite3 "$STORE_DB_PATH" <<'SQL'
CREATE TABLE IF NOT EXISTS homebrews (
  "pid" INTEGER,
  "id" TEXT,
  "name" TEXT,
  "desc" TEXT,
  "image" TEXT,
  "package" TEXT,
  "version" TEXT,
  "picpath" TEXT,
  "desc_1" TEXT,
  "desc_2" TEXT,
  "ReviewStars" REAL,
  "Size" INTEGER,
  "Author" TEXT,
  "apptype" TEXT,
  "pv" TEXT,
  "main_icon_path" TEXT,
  "main_menu_pic" TEXT,
  "releaseddate" TEXT,
  "number_of_downloads" TEXT,
  "github" TEXT,
  "video" TEXT,
  "twitter" TEXT,
  "md5" TEXT
);
SQL
}

initialize_data_dir

initialize_store_db

if [ "$WATCHER_ENABLED" = "true" ]; then
  exec python3 -u -m src
fi
log "Watcher is disabled."
exec tail -f /dev/null

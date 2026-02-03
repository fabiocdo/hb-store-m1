#!/bin/sh
set -e

TERM="${TERM:-xterm}"
export TERM

load_env_file_if_unset() {
  file="$1"
  [ -f "$file" ] || return 0
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      ""|\#*) continue ;;
    esac
    line="${line#export }"
    key="${line%%=*}"
    value="${line#*=}"
    key="$(printf "%s" "$key" | tr -d ' ')"
    [ -z "$key" ] && continue
    value="${value%$'\r'}"
    eval "isset=\${$key+x}"
    if [ -z "$isset" ]; then
      export "$key=$value"
    fi
  done < "$file"
}

load_env_file_if_unset /app/settings.env

# DEFAULT ENVIRONMENT VARIABLES
DEFAULT_SERVER_IP="127.0.0.1:8080"
DEFAULT_LOG_LEVEL="info"
DEFAULT_WATCHER_ENABLED="true"
DEFAULT_WATCHER_PERIODIC_SCAN_SECONDS="30"
DEFAULT_WATCHER_ACCESS_LOG_TAIL="true"
DEFAULT_WATCHER_ACCESS_LOG_INTERVAL="5"
DEFAULT_WATCHER_SCAN_BATCH_SIZE="50"
DEFAULT_WATCHER_EXECUTOR_WORKERS="4"
DEFAULT_WATCHER_SCAN_WORKERS="4"
DEFAULT_NGINX_ENABLE_HTTPS="false"
DEFAULT_AUTO_INDEXER_OUTPUT_FORMAT="db,json"
DEFAULT_ENV_VARS=""

# ENVIRONMENT VARIABLES
use_default_if_unset() {
  var="$1"
  default="$2"
  eval "isset=\${$var+x}"
  if [ -z "$isset" ]; then
    eval "$var=\$default"
    DEFAULT_ENV_VARS="${DEFAULT_ENV_VARS}${DEFAULT_ENV_VARS:+,}${var}"
  fi
  export "$var"
}

use_default_if_unset SERVER_IP "$DEFAULT_SERVER_IP"
use_default_if_unset LOG_LEVEL "$DEFAULT_LOG_LEVEL"
use_default_if_unset WATCHER_ENABLED "$DEFAULT_WATCHER_ENABLED"
use_default_if_unset AUTO_INDEXER_OUTPUT_FORMAT "$DEFAULT_AUTO_INDEXER_OUTPUT_FORMAT"
use_default_if_unset WATCHER_PERIODIC_SCAN_SECONDS "$DEFAULT_WATCHER_PERIODIC_SCAN_SECONDS"
use_default_if_unset WATCHER_ACCESS_LOG_TAIL "$DEFAULT_WATCHER_ACCESS_LOG_TAIL"
use_default_if_unset WATCHER_ACCESS_LOG_INTERVAL "$DEFAULT_WATCHER_ACCESS_LOG_INTERVAL"
use_default_if_unset WATCHER_SCAN_BATCH_SIZE "$DEFAULT_WATCHER_SCAN_BATCH_SIZE"
use_default_if_unset WATCHER_EXECUTOR_WORKERS "$DEFAULT_WATCHER_EXECUTOR_WORKERS"
use_default_if_unset WATCHER_SCAN_WORKERS "$DEFAULT_WATCHER_SCAN_WORKERS"
use_default_if_unset NGINX_ENABLE_HTTPS "$DEFAULT_NGINX_ENABLE_HTTPS"
export DEFAULT_ENV_VARS

# Normalize boolean-like values
WATCHER_ENABLED=$(printf "%s" "$WATCHER_ENABLED" | tr '[:upper:]' '[:lower:]')
WATCHER_ACCESS_LOG_TAIL=$(printf "%s" "$WATCHER_ACCESS_LOG_TAIL" | tr '[:upper:]' '[:lower:]')
NGINX_ENABLE_HTTPS=$(printf "%s" "$NGINX_ENABLE_HTTPS" | tr '[:upper:]' '[:lower:]')

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

ensure_ssl_certs() {
  cert_dir="/etc/nginx/certs"
  cert_key="${cert_dir}/localhost.key"
  cert_crt="${cert_dir}/localhost.crt"
  mkdir -p "$cert_dir"
  if [ -f "$cert_key" ] && [ -f "$cert_crt" ]; then
    return 0
  fi
  if ! command -v openssl >/dev/null 2>&1; then
    log "SSL certificates missing and openssl not found. Mount certs in ${cert_dir}."
    return 1
  fi
  log "Generating self-signed SSL certificate..."
  openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
    -keyout "$cert_key" \
    -out "$cert_crt" \
    -subj "/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,IP:localhost" \
    >/dev/null 2>&1 || \
  openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
    -keyout "$cert_key" \
    -out "$cert_crt" \
    -subj "/CN=localhost" \
    >/dev/null 2>&1
  if [ ! -f "$cert_key" ] || [ ! -f "$cert_crt" ]; then
    log "Failed to generate SSL certificates."
    return 1
  fi
  log "Self-signed SSL certificate generated at ${cert_dir}"
  return 0
}

configure_nginx() {
  nginx_source="/app/nginx.http.conf"
  if [ "$NGINX_ENABLE_HTTPS" = "true" ]; then
    nginx_source="/app/nginx.conf"
    if ! ensure_ssl_certs; then
      log "SSL certificates are required when NGINX_ENABLE_HTTPS=true."
      return 1
    fi
  fi
  if [ ! -f "$nginx_source" ]; then
    log "Missing Nginx config at $nginx_source."
    return 1
  fi
  if [ -w /etc/nginx/nginx.conf ] || [ ! -e /etc/nginx/nginx.conf ]; then
    cp "$nginx_source" /etc/nginx/nginx.conf
    NGINX_CONF_PATH="/etc/nginx/nginx.conf"
  else
    NGINX_CONF_PATH="/tmp/nginx.conf"
    cp "$nginx_source" "$NGINX_CONF_PATH"
  fi
  export NGINX_CONF_PATH
  return 0
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

hostport="$SERVER_IP"
hostport="${hostport#http://}"
hostport="${hostport#https://}"
hostport="${hostport%%/*}"
host="${hostport%%:*}"
port="${hostport##*:}"
if [ "$host" = "$hostport" ]; then
  if [ "$NGINX_ENABLE_HTTPS" = "true" ]; then
    port="443"
  else
    port="80"
  fi
fi

initialize_data_dir

if ! configure_nginx; then
  exit 1
fi

log "Starting NGINX..."
nginx -c "$NGINX_CONF_PATH"
log "NGINX is running on ${host}:${port}"
log ""

initialize_store_db

if [ "$WATCHER_ENABLED" = "true" ]; then
  exec python3 -u -m src
fi
log "Watcher is disabled."
exec tail -f /dev/null

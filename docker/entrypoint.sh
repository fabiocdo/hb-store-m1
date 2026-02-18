#!/bin/sh
set -eu

CONFIG_DIR="${CONFIG_DIR:-/app/configs}"
SETTINGS_FILE="${SETTINGS_FILE:-$CONFIG_DIR/settings.ini}"
INIT_SETTINGS_FILE="/app/init/settings.ini"
NGINX_TEMPLATE_FILE="/app/init/nginx.template.conf"
INDEX_TEMPLATE_FILE="/app/init/index.html"
PUBLIC_INDEX_FILE="/app/data/share/index.html"
ASSET_512_TEMPLATE_FILE="/app/init/assets/512.png"
PUBLIC_ASSET_512_FILE="/app/data/share/assets/512.png"
PYPROJECT_FILE="/app/pyproject.toml"

mkdir -p "$CONFIG_DIR/certs" /app/data/internal/logs

if [ ! -f "$SETTINGS_FILE" ]; then
  if [ -f "$INIT_SETTINGS_FILE" ]; then
    cp "$INIT_SETTINGS_FILE" "$SETTINGS_FILE"
    echo "[info] Generated settings.ini from /app/init/settings.ini"
  else
    echo "[fatal] Missing $INIT_SETTINGS_FILE"
    exit 1
  fi
fi

read_setting() {
  key="$1"
  sed -n -E "s/^[[:space:]]*(export[[:space:]]+)?${key}[[:space:]]*=[[:space:]]*(.*)$/\2/p" "$SETTINGS_FILE" \
    | tail -n 1 \
    | sed -E "s/^[[:space:]]+//; s/[[:space:]]+$//"
}

SERVER_PORT="$(read_setting SERVER_PORT)"
ENABLE_TLS="$(read_setting ENABLE_TLS)"
EXPORT_TARGETS="$(read_setting EXPORT_TARGETS)"

TLS_ENABLED=false
case "$(printf '%s' "${ENABLE_TLS:-false}" | tr '[:upper:]' '[:lower:]')" in
  1|true|yes|on) TLS_ENABLED=true ;;
esac

DEFAULT_PORT=80
LISTEN_SUFFIX=""
SSL_DIRECTIVE_PREFIX="# "

if [ "$TLS_ENABLED" = "true" ]; then
  DEFAULT_PORT=443
  LISTEN_SUFFIX=" ssl"
  SSL_DIRECTIVE_PREFIX=""
  TLS_DIR="$CONFIG_DIR/certs"
  TLS_CRT="${TLS_DIR}/tls.crt"
  TLS_KEY="${TLS_DIR}/tls.key"

  if [ ! -f "$TLS_CRT" ] || [ ! -f "$TLS_KEY" ]; then
    echo "[fatal] ENABLE_TLS=true but cert/key missing in $TLS_DIR"
    exit 1
  fi
fi

if [ -z "$SERVER_PORT" ]; then
  SERVER_PORT="$DEFAULT_PORT"
fi

case "$SERVER_PORT" in
  ''|*[!0-9]*)
    echo "[fatal] SERVER_PORT must be an integer between 1 and 65535"
    exit 1
    ;;
esac

if [ "$SERVER_PORT" -lt 1 ] || [ "$SERVER_PORT" -gt 65535 ]; then
  echo "[fatal] SERVER_PORT must be an integer between 1 and 65535"
  exit 1
fi

if [ ! -f "$NGINX_TEMPLATE_FILE" ]; then
  echo "[fatal] Missing $NGINX_TEMPLATE_FILE"
  exit 1
fi

sed \
  -e "s|__SERVER_LISTEN_PORT__|$SERVER_PORT|g" \
  -e "s|__SERVER_LISTEN_SSL_SUFFIX__|$LISTEN_SUFFIX|g" \
  -e "s|__SSL_DIRECTIVE_PREFIX__|$SSL_DIRECTIVE_PREFIX|g" \
  "$NGINX_TEMPLATE_FILE" > /etc/nginx/nginx.conf

APP_VERSION="unknown"
if [ -f "$PYPROJECT_FILE" ]; then
  APP_VERSION="$(
    sed -n -E 's/^[[:space:]]*version[[:space:]]*=[[:space:]]*"([^"]+)".*$/\1/p' "$PYPROJECT_FILE" \
      | head -n 1
  )"
  if [ -z "$APP_VERSION" ]; then
    APP_VERSION="unknown"
  fi
fi

if [ -f "$INDEX_TEMPLATE_FILE" ]; then
  normalized_targets="$(printf '%s' "${EXPORT_TARGETS:-}" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')"

  HB_STORE_ENABLED=false
  FPKGI_ENABLED=false

  case ",$normalized_targets," in
    *,hb-store,*) HB_STORE_ENABLED=true ;;
  esac

  case ",$normalized_targets," in
    *,fpkgi,*) FPKGI_ENABLED=true ;;
  esac

  mkdir -p "$(dirname "$PUBLIC_INDEX_FILE")"
  sed \
    -e "s|__APP_VERSION__|$APP_VERSION|g" \
    -e "s|__HB_STORE_ENABLED__|$HB_STORE_ENABLED|g" \
    -e "s|__FPKGI_ENABLED__|$FPKGI_ENABLED|g" \
    "$INDEX_TEMPLATE_FILE" > "$PUBLIC_INDEX_FILE"
fi

if [ -f "$ASSET_512_TEMPLATE_FILE" ]; then
  mkdir -p "$(dirname "$PUBLIC_ASSET_512_FILE")"
  cp "$ASSET_512_TEMPLATE_FILE" "$PUBLIC_ASSET_512_FILE"
fi

nginx -t
python -u -m homebrew_cdn_m1_server &
exec nginx -g 'daemon off;'

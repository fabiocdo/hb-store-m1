#!/bin/sh
set -e

mkdir -p /data/_logs

nginx_mode="$(printf "%s" "${ENABLE_SSL:-false}" | tr '[:upper:]' '[:lower:]')"
if [ "$nginx_mode" = "true" ]; then
  config_path="/configs/nginx.conf"
  if [ ! -f /etc/nginx/certs/localhost.crt ] || [ ! -f /etc/nginx/certs/localhost.key ]; then
    echo "Missing TLS certs in /etc/nginx/certs (localhost.crt/localhost.key)." >&2
    exit 1
  fi
else
  config_path="/configs/nginx.http.conf"
fi

if [ ! -f "$config_path" ]; then
  echo "Missing Nginx config at ${config_path}." >&2
  exit 1
fi

cp "$config_path" /etc/nginx/nginx.conf

# homebrew-cdn-m1-server

Static CDN pipeline for PS4 Homebrew catalogs.

- Internal source of truth: `data/internal/catalog/catalog.db`
- Public share root: `data/share`
- Public outputs: `store.db`, `*.json`, `/pkg/**`, `/update/*`, `/index.html`

## How it works

1. Scan `data/share/pkg/**.pkg` and compare with snapshot cache.
2. For added/updated packages:
- read `PARAM.SFO` with `pkgtool`
- extract media (`ICON0`, optional `PIC0`/`PIC1`)
- move package to canonical path `/pkg/<app_type>/<CONTENT_ID>.pkg`
- upsert full metadata into internal `catalog.db`
3. Remove catalog rows for missing files.
4. Export selected outputs (`hb-store`, `fpkgi`).

Invalid packages are moved to `data/internal/errors`.

## Public endpoints

- `/`
- `/index.html`
- `/store.db`
- `/update/remote.md5`
- `/update/homebrew.elf`
- `/update/homebrew.elf.sig`
- `/pkg/**`
- `/*.json` (known fPKGi files)

## Settings (`configs/settings.ini`)

```ini
# Host clients use to reach the service. Value type: string.
SERVER_IP=127.0.0.1
# Port that nginx listens on inside the container. Leave empty to use default (80 for HTTP, 443 for HTTPS). Value type: integer.
SERVER_PORT=80
# Set true to serve TLS/HTTPS; If enabled, "tls.crt" and "tls.key" are required and must live under configs/certs/. Value type: boolean.
ENABLE_TLS=false
# Logging verbosity (debug | info | warn | error). Value type: string.
LOG_LEVEL=info
# Keep 1 to disable parallel preprocessing.
WATCHER_PKG_PREPROCESS_WORKERS=1
# Cron expression for reconcile schedule (use https://crontab.guru/). Value type: string.
WATCHER_CRON_EXPRESSION=*/5 * * * *
# Comma-separated export targets. Supported: hb-store, fpkgi.
EXPORT_TARGETS=hb-store,fpkgi
# Generic timeout (seconds) for lightweight pkgtool commands.
PKGTOOL_TIMEOUT_SECONDS=300
```

`SERVER_PORT` can be empty:
- `ENABLE_TLS=false` -> default `80`
- `ENABLE_TLS=true` -> default `443`

## Init files

- `init/settings.ini`
- `init/catalog_db.sql`
- `init/store_db.sql`

## Development

```bash
python -m pip install -e .[test]
pytest
```

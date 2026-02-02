# homebrew-store-cdn

Local CDN for PS4 homebrew packages using Docker Compose and Nginx, with automatic
index generation and icon extraction.

## What it does

- Serves `.pkg` files over HTTP.
- Generates `index.json` (when JSON output is enabled) for Homebrew Store clients.
- Extracts `icon0.png` from each PKG and serves it from `pkg/_media`.
- Organizes PKGs into `game/`, `update/`, `dlc/`, `save/`, and `_unknown/` folders.
- Moves files with rename/move conflicts into `_error/`.
- Watches the `pkg/` tree and refreshes `index.json` after file changes.

## Requirements

- Docker + Docker Compose
- A host directory to store PKGs and generated assets

## Quick start

### Option A: Docker Run (from Docker Hub)

```bash
docker run -d \
  --name homebrew-store-cdn \
  -p 8080:80 \
  -e BASE_URL=http://127.0.0.1:8080 \
  -e LOG_LEVEL=info \
  -e WATCHER_ENABLED=true \
  -e AUTO_INDEXER_OUTPUT_FORMAT=DB,JSON \
  -e AUTO_FORMATTER_MODE=none \
  -e AUTO_FORMATTER_TEMPLATE="{title} {title_id} {app_type}" \
  -e WATCHER_PERIODIC_SCAN_SECONDS=30 \
  -v ./data:/data \
  -v ./nginx.conf:/etc/nginx/nginx.conf:ro \
  fabiocdo/homebrew-store-cdn:latest
```

### Option B: Docker Compose (from Docker Hub)

Create a `docker-compose.yml` (see example folder):

```yaml
services:
  homebrew-store-cdn:
    image: fabiocdo/homebrew-store-cdn:latest
    container_name: homebrew-store-cdn
    ports:
      - "8080:80"
    environment:
      - BASE_URL=http://127.0.0.1:8080
      - LOG_LEVEL=info
      - WATCHER_ENABLED=true
      - AUTO_INDEXER_OUTPUT_FORMAT=DB,JSON
      - AUTO_FORMATTER_MODE=none
      - AUTO_FORMATTER_TEMPLATE="{title} {title_id} {app_type}"
      - WATCHER_PERIODIC_SCAN_SECONDS=30
    volumes:
      - ./data:/data
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    restart: unless-stopped
```

Run:

```bash
docker compose up -d
```

### Option C: Build locally

1) Edit the `environment:` and `volumes:` sections in your `docker-compose.yml`
   (see example folder).

2) Build and run:

```bash
docker compose build
docker compose up -d
```

### Option D: Run locally using the example compose file

1) Copy the example compose file to the repo root:

```bash
cp example/docker-compose.yml ./docker-compose.yml
```

2) Edit the `environment:` and `volumes:` sections in `docker-compose.yml`
   if needed.

3) Build and run:

```bash
docker compose up -d --build
```

Open:

- http://127.0.0.1:8080
- http://127.0.0.1:8080/index.json

## Host data layout

The host directory mapped to `/data` must follow this layout:

```
/opt/cdn/
|-- pkg/                   # Place PKGs here
|   |-- game/              # Auto-created
|   |-- update/            # Auto-created
|   |-- dlc/               # Auto-created
|   |-- save/              # Auto-created
|   |-- _unknown/          # Auto-created
|   |-- _PUT_YOUR_PKGS_HERE
|   |-- Game Name [CUSA12345].pkg
|-- pkg/
|   |-- _media/            # Auto-generated icons
|   |-- CUSA12345.png
|-- _cache/                # Auto-generated cache
|   |-- index-cache.json
|-- _error/               # Files moved when rename/move conflicts occur
|-- index.json             # Auto-generated index
```

Notes:

- `index.json` is generated when JSON output is enabled; `pkg/_media/*.png` is generated automatically.
- PKGs are processed even if they are inside folders that start with `_`.
- PKGs placed directly in `pkg/` are processed by formatter/sorter but are not indexed.
- The `_PUT_YOUR_PKGS_HERE` file is a marker created on container startup.
- Auto-created folders and the marker are only created during container startup.
- `_cache/index-cache.json` stores metadata to speed up subsequent runs.
- The cache is updated only when `index.json` is generated.
- If a duplicate target name is detected, the file is moved to `_error/`.

## Package organization

During indexing, packages are classified by their `CATEGORY` from `param.sfo`:

- `gd` -> `game`
- `gp` -> `update`
- `ac` -> `dlc`
- `sd` -> `save`
- (anything else) -> `_unknown`

## index.json format

Example payload:

```json
{
  "DATA": {
    "http://127.0.0.1:8080/pkg/game/Example%20Game%20%5BCUSA12345%5D.pkg": {
      "region": "USA",
      "name": "Example Game",
      "version": "01.00",
      "release": "01-13-2023",
      "size": 123456789,
      "min_fw": null,
      "cover_url": "http://127.0.0.1:8080/pkg/_media/UP0000-CUSA12345_00-EXAMPLE.png"
    }
  }
}
```

Fields:

- `DATA`: mapping of `pkg_url -> metadata`.
- `region`, `name`, `version`: extracted from `param.sfo`.
- `release`: extracted from `param.sfo` and formatted as `MM-DD-YYYY`.
- `size`: file size in bytes.
- `min_fw`: currently `null`.
- `cover_url`: icon URL built from `BASE_URL` when an icon exists.

## Environment variables

| Variable                    | Description                                                                                                              | Default                          |
|-----------------------------|--------------------------------------------------------------------------------------------------------------------------|----------------------------------|
| `BASE_URL`                  | Base URL written in `index.json`.                                                                                        | `http://127.0.0.1:8080`          |
| `LOG_LEVEL`                 | Log verbosity: `debug`, `info`, `warn`, `error`.                                                                          | `info`                           |
| `WATCHER_ENABLED`           | Master switch for watcher-driven automations (format, move, index).                                                     | `true`                           |
| `WATCHER_PERIODIC_SCAN_SECONDS` | Interval in seconds for periodic PKG scans (no inotify watcher).                                                     | `30`                             |
| `AUTO_INDEXER_OUTPUT_FORMAT`| Output targets (comma-separated): `DB`, `JSON`.                                                                          | `DB`                             |
| `AUTO_FORMATTER_MODE`         | Title transform mode for `{title}`: `none`, `uppercase`, `lowercase`, `capitalize`, `snake_uppercase`, `snake_lowercase`. | `none`                           |
| `AUTO_FORMATTER_TEMPLATE`     | Template using `{title}`, `{title_id}`, `{content_id}`, `{category}`, `{version}`, `{release_date}`, `{region}`, `{app_type}`. | `{title} {title_id} {app_type}` |
| `DATA_DIR`                  | Host path mapped to `/data`.                                                                                             | `/data`                          |

Dependencies and behavior:

- `WATCHER_ENABLED=false` disables all automations (format, move, index) and the watcher does not start.
- `AUTO_INDEXER_OUTPUT_FORMAT` controls index outputs: include `JSON` to write `index.json`, include `DB` to update `store.db`.
- `AUTO_FORMATTER_TEMPLATE` and `AUTO_FORMATTER_MODE` apply during the formatting stage when the watcher is enabled.
- Conflicting files are moved to `_error/`.


## Modules

### Watcher

- Location: `src/modules/watcher.py`
- Runs periodic scans under `pkg/`.
- Runs a per-file pipeline (formatter → sorter → indexer).

### Auto Formatter

- Location: `src/modules/auto_formatter.py`
- Renames PKGs based on `AUTO_FORMATTER_TEMPLATE` and `AUTO_FORMATTER_MODE`.
- Moves conflicts to `_error/`.

Template data example:

```python
{
  "title": "Aged Wild Steak",
  "title_id": "CUSA14655",
  "content_id": "UP0700-CUSA14655_00-NEWDBZRPG0000005",
  "category": "ac",
  "version": "01.00",
  "release_date": "2023-01-13",
  "region": "USA",
  "app_type": "dlc"
}
```

### Auto Sorter

- Location: `src/modules/auto_sorter.py`
- Sorts PKGs into `game/`, `dlc/`, `update/` based on SFO metadata.
- Moves conflicts to `_error/`.

### Auto Indexer

- Location: `src/modules/auto_indexer.py`
- Builds `index.json` and `_cache/index-cache.json` from scanned PKGs.
- Only logs when content changes (or icons are extracted).
- Uses `_cache/index-cache.json` to skip reprocessing unchanged PKGs.
- Icon extraction runs per-file in the same pipeline as formatter/sorter.
- Output targets are controlled by `AUTO_INDEXER_OUTPUT_FORMAT` (e.g. `DB,JSON`).

### PKG Utilities

- Location: `src/utils/pkg_utils.py`
- Uses `pkgtool` to read SFO metadata and extract icons.

### Log Utilities

- Location: `src/utils/log_utils.py`
- Modular tagging and log level filtering.
- Provides a centralized `log` function.

**Logging Examples:**

```python
from src.utils import log

# Watcher
log("info", "Starting periodic scan", module="WATCHER")

# Auto Formatter
log("info", "Renaming file", message="old.pkg -> NEW.pkg", module="AUTO_FORMATTER")
log("error", "Failed to rename", message="Permission denied", module="AUTO_FORMATTER")

# Auto Sorter
log("info", "Moving PKG to category folder", message="game/my_game.pkg", module="AUTO_SORTER")
log("warn", "Category mapping missing", module="AUTO_SORTER")

# Auto Indexer
log("info", "Indexing started", module="AUTO_INDEXER")

# Planner / Executor
log("debug", "Planning changes", module="WATCHER_PLANNER")
log("debug", "Executing planned changes", module="WATCHER_EXECUTOR")
```

Output format: `<timestamp UTC> | [MODULE] Action: Message` (with module-specific colors).

**Colors:**
- `AUTO_INDEXER`: Green
- `AUTO_SORTER`: Yellow
- `AUTO_FORMATTER`: Blue
- `WATCHER`: White
- `WATCHER_PLANNER`: Cyan
- `WATCHER_EXECUTOR`: Gray

**Level Colors:**
- `DEBUG`: Gray
- `INFO`: White
- `WARN`: Orange
- `ERROR`: Red

Example: `2024-05-20 14:30:05 UTC | [WATCHER] Starting periodic scan` (where `[WATCHER]` is white and the message is white).

## Flow diagram (ASCII)

```
periodic scan
                |
                v
           [src/modules/watcher.py]
                |
                v
   planner -> executor
                |
                v
        [src/modules/auto_formatter.py]
                |
          (conflict?)----yes----> /data/_error
                |
               no
                v
          [src/modules/auto_sorter.py]
                |
          (conflict?)----yes----> /data/_error
                |
               no
                v
     [src/modules/auto_indexer.py]
                |
                v
     index.json / store.db
                |
                v
       _cache/index-cache.json
```

## Volume config

| Volume                                  | Description                              | Default        |
|-----------------------------------------|------------------------------------------|----------------|
| `./data:/data`                          | Host data directory mapped to `/data`.   | `./data`       |
| `./nginx.conf:/etc/nginx/nginx.conf:ro` | External Nginx config mounted read-only. | `./nginx.conf` |

## Nginx behavior

- Serves `/data` directly.
- Adds cache headers for `.pkg`, `.zip`, and image files.
- Supports HTTP range requests for large downloads.

If you want to provide your own `nginx.conf`, mount it to `/etc/nginx/nginx.conf:ro`
as shown in the quick start examples.

## Troubleshooting

- If the index is not updating, remove `/data/_cache/index-cache.json` to force a rebuild.
- If a PKG is encrypted, `pkgtool` may fail to read `param.sfo` and the PKG is moved to `_error/`.
- If icons are missing, ensure the PKG contains `ICON0_PNG` or `PIC0_PNG`.
- If a format or move conflict is detected, the PKG is moved to `/data/_error`.
- Files in `_error/` are not indexed.
- Resolve conflicts manually and move the file back into `pkg/`.
- PKG metadata errors are logged with a human-friendly stage (e.g. `Reading PKG entries`, `PARAM.SFO not found`).
- Each error move appends the full console-formatted line to `/data/_error/errors.log`.

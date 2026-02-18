CREATE TABLE IF NOT EXISTS catalog_items
(
    pid             INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id      TEXT NOT NULL,
    title_id        TEXT NOT NULL,
    title           TEXT NOT NULL,
    app_type        TEXT NOT NULL,
    category        TEXT NOT NULL,
    version         TEXT NOT NULL,
    pubtoolinfo     TEXT,
    system_ver      TEXT,
    release_date    TEXT NOT NULL,
    pkg_path        TEXT NOT NULL,
    pkg_size        INTEGER NOT NULL,
    pkg_mtime_ns    INTEGER NOT NULL,
    pkg_fingerprint TEXT NOT NULL,
    icon0_path      TEXT,
    pic0_path       TEXT,
    pic1_path       TEXT,
    sfo_json        TEXT NOT NULL,
    sfo_raw         BLOB NOT NULL,
    sfo_hash        TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    UNIQUE (content_id, app_type, version)
);

CREATE INDEX IF NOT EXISTS catalog_items_content_id_idx ON catalog_items (content_id);
CREATE INDEX IF NOT EXISTS catalog_items_pkg_path_idx ON catalog_items (pkg_path);
CREATE INDEX IF NOT EXISTS catalog_items_app_type_idx ON catalog_items (app_type);

CREATE TABLE IF NOT EXISTS download_counters
(
    title_id   TEXT PRIMARY KEY,
    downloads  INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS download_counters_downloads_idx ON download_counters (downloads);

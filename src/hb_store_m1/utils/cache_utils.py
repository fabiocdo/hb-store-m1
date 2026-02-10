import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from hb_store_m1.models.globals import Globals
from hb_store_m1.models.storedb import StoreDB


class CacheUtils:
    STORE_DB_CACHE_VERSION = 1
    INDEX_CACHE_VERSION = 1

    STORE_DB_KEY_FIELDS = ("content_id",)
    STORE_DB_HASH_FIELDS = tuple(col.value for col in StoreDB.Columns)

    @staticmethod
    def _normalize_value(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, (str, int, float, bool)):
            return value
        return str(value)

    @staticmethod
    def _get_row_value(row: Any, field: str) -> Any:
        if isinstance(row, Mapping):
            return row.get(field)
        try:
            return row[field]
        except Exception:
            return getattr(row, field, None)

    @staticmethod
    def _hash_payload(values: Sequence[Any] | bytes) -> str:
        if isinstance(values, (bytes, bytearray)):
            return hashlib.md5(values).hexdigest()
        payload = json.dumps(
            list(values), ensure_ascii=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.md5(payload).hexdigest()

    @staticmethod
    def _build_row_key(row: Any, key_fields: Sequence[str]) -> str:
        values = [
            CacheUtils._normalize_value(CacheUtils._get_row_value(row, field))
            for field in key_fields
        ]
        return json.dumps(values, ensure_ascii=True, separators=(",", ":"))

    @staticmethod
    def _build_row_hash(row: Any, hash_fields: Sequence[str]) -> str:
        values = [
            CacheUtils._normalize_value(CacheUtils._get_row_value(row, field))
            for field in hash_fields
        ]
        return CacheUtils._hash_payload(values)

    @staticmethod
    def build_store_db_cache(
        rows: Iterable[Any] | None,
        key_fields: Sequence[str] | None = None,
        hash_fields: Sequence[str] | None = None,
    ) -> dict[str, str]:
        key_fields = tuple(key_fields or CacheUtils.STORE_DB_KEY_FIELDS)
        hash_fields = tuple(hash_fields or CacheUtils.STORE_DB_HASH_FIELDS)
        cache: dict[str, str] = {}
        for row in rows or []:
            key = CacheUtils._build_row_key(row, key_fields)
            cache[key] = CacheUtils._build_row_hash(row, hash_fields)
        return cache

    @staticmethod
    def compare_store_db_cache(
        current: Mapping[str, str], previous: Mapping[str, str]
    ) -> tuple[set[str], set[str], set[str]]:
        current_keys = set(current)
        previous_keys = set(previous)
        added = current_keys - previous_keys
        removed = previous_keys - current_keys
        updated = {k for k in current_keys & previous_keys if current[k] != previous[k]}
        return added, updated, removed

    @staticmethod
    def write_cache_store_db(
        rows: Iterable[Any] | Mapping[str, str] | None = None,
        key_fields: Sequence[str] | None = None,
        hash_fields: Sequence[str] | None = None,
    ) -> dict[str, str]:
        key_fields = tuple(key_fields or CacheUtils.STORE_DB_KEY_FIELDS)
        hash_fields = tuple(hash_fields or CacheUtils.STORE_DB_HASH_FIELDS)

        if isinstance(rows, Mapping):
            if all(isinstance(v, str) for v in rows.values()):
                cache_rows = dict(rows)
            else:
                cache_rows = CacheUtils.build_store_db_cache(
                    rows.values(), key_fields=key_fields, hash_fields=hash_fields
                )
        else:
            cache_rows = CacheUtils.build_store_db_cache(
                rows, key_fields=key_fields, hash_fields=hash_fields
            )

        payload = {
            "version": CacheUtils.STORE_DB_CACHE_VERSION,
            "key_fields": list(key_fields),
            "hash_fields": list(hash_fields),
            "hash": CacheUtils._hash_payload(
                json.dumps(
                    cache_rows, ensure_ascii=True, separators=(",", ":"), sort_keys=True
                ).encode("utf-8")
            ),
            "rows": cache_rows,
        }

        path = Globals.FILES.STORE_DB_JSON_FILE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return cache_rows

    @staticmethod
    def read_cache_store_db() -> tuple[dict[str, str], dict[str, Any]]:
        path = Globals.FILES.STORE_DB_JSON_FILE_PATH
        default_meta = {
            "version": CacheUtils.STORE_DB_CACHE_VERSION,
            "key_fields": list(CacheUtils.STORE_DB_KEY_FIELDS),
            "hash_fields": list(CacheUtils.STORE_DB_HASH_FIELDS),
            "hash": None,
        }
        if not path.exists():
            return {}, default_meta

        try:
            data = json.loads(path.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}, default_meta

        if not isinstance(data, dict):
            return {}, default_meta

        if data.get("version") != CacheUtils.STORE_DB_CACHE_VERSION:
            return {}, default_meta

        rows = data.get("rows", {})
        if not isinstance(rows, dict):
            rows = {}

        meta = {
            "version": data.get("version"),
            "key_fields": data.get("key_fields", default_meta["key_fields"]),
            "hash_fields": data.get("hash_fields", default_meta["hash_fields"]),
            "hash": data.get("hash"),
        }
        return rows, meta


CacheUtils = CacheUtils()

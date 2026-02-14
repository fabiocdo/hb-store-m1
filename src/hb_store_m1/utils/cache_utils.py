import json
from pathlib import Path

from hb_store_m1.models.cache import CacheSection, CACHE_ADAPTER
from hb_store_m1.models.globals import Globals
from hb_store_m1.models.log import LogColor, LogModule
from hb_store_m1.models.output import Output, Status
from hb_store_m1.models.pkg.section import Section
from hb_store_m1.utils.log_utils import LogUtils
from hb_store_m1.utils.pkg_utils import PkgUtils

log = LogUtils(LogModule.CACHE_UTIL)
from pydantic import ValidationError


class CacheUtils:
    _SECTIONS = Section.ALL

    @staticmethod
    def read_pkg_cache():
        store_cache_json_file_path = Globals.FILES.STORE_CACHE_JSON_FILE_PATH

        if not store_cache_json_file_path.exists():
            log.log_debug(
                f"Skipping {store_cache_json_file_path.name.upper()} read. File not found"
            )
            return Output(Status.NOT_FOUND, {})

        try:
            data = CACHE_ADAPTER.validate_json(
                store_cache_json_file_path.read_text("utf-8")
            )
        except (OSError, ValueError, ValidationError) as e:
            log.log_error(f"Failed to read {store_cache_json_file_path.name}: {e}")
            return Output(Status.ERROR, {})

        return Output(Status.OK, data)

    @staticmethod
    def write_pkg_cache(
        path: Path | None = None, cached: dict[str, CacheSection] | None = None
    ):
        store_cache_path = path or Globals.FILES.STORE_CACHE_JSON_FILE_PATH
        pkg_dir_path = Globals.PATHS.PKG_DIR_PATH

        if not pkg_dir_path.exists():
            log.log_debug(
                f"Skipping {pkg_dir_path.name.upper()} scan. Directory not found"
            )
            return Output(Status.NOT_FOUND, {})

        cache = {section.name: CacheSection() for section in CacheUtils._SECTIONS}
        valid_content_ids: set[str] = set()
        if cached is None:
            cached = CacheUtils.read_pkg_cache().content or {}
        else:
            cached = cached or {}
        cached_index_by_section: dict[str, dict[str, tuple[str, str, str]]] = {}
        for section in CacheUtils._SECTIONS:
            if section.name == "_media":
                continue
            cached_section = cached.get(section.name)
            if not cached_section:
                continue
            index: dict[str, tuple[str, str, str]] = {}
            for content_id, value in cached_section.content.items():
                parts = value.split("|", 2)
                if len(parts) >= 3:
                    size_str, mtime_str, filename = parts[0], parts[1], parts[2]
                elif len(parts) >= 2:
                    size_str, mtime_str = parts[0], parts[1]
                    filename = f"{content_id}.pkg"
                else:
                    continue
                index[filename] = (content_id, size_str, mtime_str)
            cached_index_by_section[section.name] = index

        for section in CacheUtils._SECTIONS:
            section_path = section.path

            if not section_path.exists():
                continue

            for pkg_path in section_path.iterdir():
                if not section.accepts(pkg_path):
                    continue

                try:
                    stat = pkg_path.stat()

                except OSError as exc:
                    log.log_warn(f"Failed to stat {pkg_path.name}: {exc}")
                    continue

                section_cache = cache[section.name]
                section_cache.meta.count += 1
                section_cache.meta.total_size += int(stat.st_size)
                section_cache.meta.latest_mtime = max(
                    section_cache.meta.latest_mtime, int(stat.st_mtime_ns)
                )
                if section.name == "_media":
                    media_key = pkg_path.stem
                    content_id = None
                    for suffix in ("_icon0", "_pic0", "_pic1"):
                        if media_key.endswith(suffix):
                            content_id = media_key[: -len(suffix)]
                            break
                    if not content_id or content_id not in valid_content_ids:
                        continue
                    cache_key = media_key
                    cache_value = f"{stat.st_size}|{stat.st_mtime_ns}|{pkg_path.name}"
                else:
                    size_str = str(stat.st_size)
                    mtime_str = str(stat.st_mtime_ns)
                    cached_index = cached_index_by_section.get(section.name) or {}
                    cached_entry = cached_index.get(pkg_path.name)
                    if (
                        cached_entry
                        and cached_entry[1] == size_str
                        and cached_entry[2] == mtime_str
                    ):
                        cache_key = cached_entry[0] or pkg_path.stem
                        if cached_entry[0]:
                            valid_content_ids.add(cached_entry[0])
                    else:
                        content_id = PkgUtils.read_content_id(pkg_path)
                        cache_key = content_id or pkg_path.stem
                        if not content_id:
                            log.log_warn(
                                f"Failed to read content_id for {pkg_path.name}. "
                                "Falling back to filename."
                            )
                        else:
                            valid_content_ids.add(content_id)
                    cache_value = f"{size_str}|{mtime_str}|{pkg_path.name}"
                section_cache.content[cache_key] = cache_value

        store_cache_path.parent.mkdir(parents=True, exist_ok=True)
        store_cache_path.write_text(
            json.dumps(
                CACHE_ADAPTER.dump_python(cache),
                ensure_ascii=True,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        return Output(Status.OK, cache)

    @staticmethod
    def compare_pkg_cache() -> Output[dict]:
        store_cache_path = Globals.FILES.STORE_CACHE_JSON_FILE_PATH
        temp_path = store_cache_path.with_suffix(".tmp")

        cached_output = CacheUtils.read_pkg_cache()
        cached = cached_output.content or {}
        current_output = CacheUtils.write_pkg_cache(temp_path, cached)

        current = current_output.content or {}

        current_dump = CACHE_ADAPTER.dump_python(current)
        cached_dump = CACHE_ADAPTER.dump_python(cached)
        has_changes = current_dump != cached_dump

        added = {}
        removed = {}
        updated = {}
        current_files = {}
        changed_sections = []
        summary_lines = []

        if has_changes:
            for section in CacheUtils._SECTIONS:
                section_name = section.name
                current_section = current.get(section_name, CacheSection())
                cached_section = cached.get(section_name, CacheSection())
                current_meta = current_section.meta
                cached_meta = cached_section.meta
                current_content = current_section.content
                cached_content = cached_section.content
                current_keys = set(current_content)
                cached_keys = set(cached_content)

                added[section_name] = sorted(current_keys - cached_keys)
                removed[section_name] = sorted(cached_keys - current_keys)
                updated[section_name] = sorted(
                    key
                    for key in current_keys & cached_keys
                    if current_content[key] != cached_content[key]
                )
                if section_name != "_media":
                    file_map = {}
                    for key, value in current_content.items():
                        parts = value.split("|", 2)
                        if len(parts) >= 3 and parts[2]:
                            filename = parts[2]
                        else:
                            filename = f"{key}.pkg"
                        file_map[key] = filename
                    current_files[section_name] = file_map
                added_count = len(added[section_name])
                updated_count = len(updated[section_name])
                removed_count = len(removed[section_name])
                if (
                    current_meta.model_dump() != cached_meta.model_dump()
                    or added[section_name]
                    or removed[section_name]
                    or updated[section_name]
                ):
                    changed_sections.append(section_name)
                    summary = (
                        f"{section_name.upper()}: "
                        f"{LogColor.BRIGHT_GREEN if added_count != 0 else LogColor.RESET}+{added_count}{LogColor.RESET} "
                        f"{LogColor.BRIGHT_YELLOW if updated_count != 0 else LogColor.RESET}"
                        f"~{updated_count}{LogColor.RESET} "
                        f"{LogColor.BRIGHT_RED if removed_count != 0 else LogColor.RESET}-{removed_count}{LogColor.RESET}"
                    )
                    summary_lines.append(summary)

        try:
            if temp_path.exists():
                temp_path.unlink()
        except OSError as exc:
            log.log_warn(f"Failed to remove temp cache file: {exc}")
            return Output(Status.ERROR, None)

        if not has_changes:
            return Output(Status.SKIP, None)

        if summary_lines:
            log.log_info("Changes summary: " + ", ".join(summary_lines))

        return Output(
            Status.OK,
            {
                "added": added,
                "updated": updated,
                "removed": removed,
                "current_files": current_files,
                "current_cache": current,
                "changed": sorted(changed_sections),
            },
        )


CacheUtils = CacheUtils()

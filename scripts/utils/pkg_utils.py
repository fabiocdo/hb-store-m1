import json
import os
import pathlib
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

import settings
from utils.log_utils import format_log_line, log
from tools.pkgtool import run_pkgtool


STAGE_LABELS = {
    "init": "Initializing",
    "pkg_listentries": "Reading PKG entries",
    "param_sfo_not_found": "PARAM.SFO not found",
    "pkg_extractentry": "Extracting PARAM.SFO",
    "param_sfo_missing": "PARAM.SFO missing",
    "sfo_listentries": "Reading PARAM.SFO",
    "normalize": "Normalizing metadata",
    "icon_extract": "Extracting icon",
    "build_data": "Building metadata",
}


class PkgMetadataError(Exception):
    def __init__(self, stage):
        self.stage = stage
        super().__init__(stage)


def extract_pkg_data(pkg_path, include_icon=False):
    """Extract and normalize PKG metadata, optionally including icon bytes."""
    stage = "init"

    def process_entries(entries_output):
        sfo_entry = None
        icon_entry = None
        for line in entries_output.splitlines():
            line = line.strip()
            if not line or line.startswith("Offset"):
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            entry_id = parts[3]
            name = parts[5] if len(parts) >= 6 else parts[4]
            lower = name.lower()
            normalized = lower.replace(".", "_")
            if "param_sfo" in normalized:
                sfo_entry = entry_id
            elif normalized in {"icon0_png", "icon0_00_png", "pic0_png"}:
                if icon_entry is None or normalized == "icon0_png":
                    icon_entry = entry_id
        return sfo_entry, icon_entry

    def process_info(sfo_path):
        output = run_pkgtool(["sfo_listentries", str(sfo_path)])
        info = {}
        for line in output.splitlines():
            if " = " not in line or " : " not in line:
                continue
            left, value = line.split(" = ", 1)
            name = left.split(" : ", 1)[0].strip()
            info[name] = value.strip()
        return info

    def process_app_type(info):
        if "APP_TYPE" not in info:
            return
        value = info["APP_TYPE"]
        if isinstance(value, int):
            info["APP_TYPE"] = value
            return
        if not value:
            info["APP_TYPE"] = None
            return
        value_str = str(value)
        if value_str.startswith("0x"):
            try:
                info["APP_TYPE"] = int(value_str, 16)
            except ValueError:
                info["APP_TYPE"] = None
            return
        try:
            info["APP_TYPE"] = int(value_str)
        except ValueError:
            info["APP_TYPE"] = None

    def process_apptype(info):
        category = info.get("CATEGORY")
        app_type = info.get("APP_TYPE")
        apptype = "app"
        if category:
            cat = category.lower()
            category_map = {
                "gd": "game",
                "gp": "update",
                "ac": "dlc",
                "ad": "app",
                "al": "app",
                "ap": "app",
                "bd": "app",
                "dd": "app",
            }
            if cat in category_map:
                apptype = category_map[cat]
            elif app_type == 2:
                apptype = "game"
        elif app_type == 2:
            apptype = "game"
        info["APPTYPE"] = apptype

    def process_region(info):
        content_id = info.get("CONTENT_ID")
        if not content_id or len(content_id) < 2:
            return
        prefix = content_id[:2].upper()
        region_map = {
            "UP": "USA",
            "EP": "EUR",
            "JP": "JPN",
            "KP": "KOR",
            "HP": "HKG",
            "TP": "TWN",
            "CP": "CHN",
        }
        info["REGION"] = region_map.get(prefix, prefix)

    def process_icon_bytes(icon_entry, tmp_root):
        if not include_icon or icon_entry is None:
            return None
        icon_path = tmp_root / "icon0.png"
        run_pkgtool(["pkg_extractentry", str(pkg_path), str(icon_entry), str(icon_path)])
        if icon_path.exists():
            return icon_path.read_bytes()
        return None

    def build_data(info):
        title = info.get("TITLE")
        titleid = info.get("TITLE_ID")
        version = info.get("VERSION")
        category = info.get("CATEGORY")
        content_id = info.get("CONTENT_ID")
        app_type = info.get("APP_TYPE")
        apptype = info.get("APPTYPE")
        region = info.get("REGION")

        return {
            "title": title,
            "titleid": titleid,
            "version": version,
            "category": category,
            "content_id": content_id,
            "app_type": app_type,
            "apptype": apptype,
            "region": region,
        }

    try:
        with tempfile.TemporaryDirectory(prefix="pkg_extract_") as tmpdir:
            tmp_root = pathlib.Path(tmpdir)
            stage = "pkg_listentries"
            entries_output = run_pkgtool(["pkg_listentries", str(pkg_path)])
            sfo_entry, icon_entry = process_entries(entries_output)

            if sfo_entry is None:
                stage = "param_sfo_not_found"
                raise RuntimeError("PARAM_SFO not found")

            sfo_path = tmp_root / "param.sfo"
            stage = "pkg_extractentry"
            run_pkgtool(["pkg_extractentry", str(pkg_path), str(sfo_entry), str(sfo_path)])
            if not sfo_path.exists():
                stage = "param_sfo_missing"
                raise RuntimeError("PARAM_SFO not found")

            stage = "sfo_listentries"
            info = process_info(sfo_path)
            stage = "normalize"
            process_app_type(info)
            process_apptype(info)
            process_region(info)
            stage = "icon_extract"
            icon_bytes = process_icon_bytes(icon_entry, tmp_root)

            stage = "build_data"
            data = build_data(info)
            return {"data": data, "icon_bytes": icon_bytes}
    except Exception as e:
        raise PkgMetadataError(stage) from e


def iter_pkg_paths():
    """Yield PKG paths under PKG_DIR, ignoring underscore-prefixed folders."""
    for pkg in settings.PKG_DIR.rglob("*.pkg"):
        yield pkg


def scan_pkgs(paths=None, use_cache=False):
    """Yield (pkg_path, data) for PKGs; optionally use cache and parallel extraction."""

    def handle_metadata_error(pkg, stage_label):
        message = f"Failed to read PKG metadata ({stage_label}): {pkg}"
        log("error", message)
        try:
            settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
            error_dir = settings.DATA_DIR / "_errors"
            error_dir.mkdir(parents=True, exist_ok=True)
            target = error_dir / pkg.name
            counter = 1
            while target.exists():
                if pkg.suffix:
                    target = error_dir / f"{pkg.stem}_{counter}{pkg.suffix}"
                else:
                    target = error_dir / f"{pkg.name}_{counter}"
                counter += 1
            pkg.rename(target)
            warn_message = f"Moved file with error to {error_dir}: {pkg}"
            log("warn", warn_message)
            try:
                log_path = error_dir / "error_log.txt"
                with log_path.open("a", encoding="utf-8") as handle:
                    handle.write(format_log_line(message) + "\n")
                    handle.write(format_log_line(warn_message) + "\n")
            except Exception:
                pass
        except Exception as move_error:
            log("error", f"Failed to move errored PKG to _errors: {pkg} ({move_error})")

    def load_cache():
        if not use_cache or settings.INDEX_JSON_ENABLED is False:
            return {"pkgs": {}}
        try:
            if settings.CACHE_PATH.exists():
                return json.loads(settings.CACHE_PATH.read_text())
        except Exception:
            pass
        return {"pkgs": {}}

    def cache_lookup(cache, pkg):
        try:
            stat = pkg.stat()
        except Exception:
            return None
        rel = pkg.relative_to(settings.PKG_DIR).as_posix()
        entry = cache.get("pkgs", {}).get(rel)
        if (
            entry
            and entry.get("size") == stat.st_size
            and entry.get("mtime") == stat.st_mtime
            and isinstance(entry.get("data"), dict)
        ):
            return entry["data"]
        return None

    def extract_worker(pkg):
        try:
            result = extract_pkg_data(pkg, include_icon=False)
            return ("ok", pkg, result["data"])
        except PkgMetadataError as e:
            return ("pkg_error", pkg, e)
        except Exception as e:
            return ("error", pkg, e)

    cache = load_cache()
    pkg_paths = list(paths) if paths is not None else list(iter_pkg_paths())
    cache_hits = []
    to_extract = []
    for pkg in pkg_paths:
        cached = cache_lookup(cache, pkg)
        if cached is not None:
            cache_hits.append((pkg, cached))
        else:
            to_extract.append(pkg)

    for pkg, data in cache_hits:
        yield pkg, data

    if not to_extract:
        return

    max_workers = max(2, os.cpu_count() or 2)
    if len(to_extract) == 1 or max_workers <= 1:
        for pkg in to_extract:
            try:
                result = extract_pkg_data(pkg, include_icon=False)
                yield pkg, result["data"]
            except PkgMetadataError as e:
                stage_label = STAGE_LABELS.get(e.stage, "Unknown stage")
                handle_metadata_error(pkg, stage_label)
            except Exception:
                handle_metadata_error(pkg, "Unknown stage")
        return

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(extract_worker, pkg): pkg for pkg in to_extract}
        for future in as_completed(futures):
            status, pkg, payload = future.result()
            if status == "ok":
                yield pkg, payload
            elif status == "pkg_error":
                stage_label = STAGE_LABELS.get(payload.stage, "Unknown stage")
                handle_metadata_error(pkg, stage_label)
            else:
                handle_metadata_error(pkg, "Unknown stage")

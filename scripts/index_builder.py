import json
import shutil
from urllib.parse import quote

import settings
from utils.log_utils import log
from utils.pkgtool_utils import read_icon_bytes, read_pkg_info
from utils.parse_utils import parse_sfo_int
from utils.rename_utils import render_rename
from settings import (
    APP_DIR,
    APPTYPE_PATHS,
    CACHE_DIR,
    CACHE_PATH,
    INDEX_PATH,
    MEDIA_DIR,
    PKG_DIR,
)


def map_apptype(category, app_type):
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
            return category_map[cat]
    if app_type == 1:
        return "app"
    if app_type == 2:
        return "game"
    return "app"


def region_from_content_id(content_id):
    if not content_id or len(content_id) < 2:
        return None
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
    return region_map.get(prefix, prefix)


def load_cache():
    try:
        if CACHE_PATH.exists():
            return json.loads(CACHE_PATH.read_text())
    except Exception:
        pass
    return {"version": 1, "pkgs": {}}


def save_cache(cache):
    log("info", "Generating index-cache.json...")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2))
    log("created", "Generated: index-cache.json")


def build_data(info, pkg_path):
    title = info.get("TITLE", pkg_path.stem)
    titleid = info.get("TITLE_ID", pkg_path.stem)
    version = info.get("VERSION", "1.00")
    category = info.get("CATEGORY")
    content_id = info.get("CONTENT_ID")
    app_type = parse_sfo_int(info.get("APP_TYPE"))
    apptype = map_apptype(category, app_type)
    region = region_from_content_id(content_id)

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


def build_target_path(pkg_path, apptype, title, titleid, region, version, category, content_id, app_type):
    target_dir = pkg_path.parent
    if apptype in APPTYPE_PATHS and apptype != "app" and APP_DIR not in pkg_path.parents:
        target_dir = APPTYPE_PATHS[apptype]
    target_name = pkg_path.name
    if settings.AUTO_RENAME_PKGS and titleid:
        target_name = render_rename(
            settings.AUTO_RENAME_TEMPLATE,
            {
                "title": title,
                "titleid": titleid,
                "version": version or "1.00",
                "category": category or "",
                "content_id": content_id or "",
                "app_type": app_type or "",
                "apptype": apptype or "app",
                "region": region or "UNK",
            },
        )
    return target_dir / target_name


def ensure_pkg_location(pkg_path, apptype):
    if apptype not in APPTYPE_PATHS:
        return pkg_path
    if apptype == "app":
        return pkg_path
    if APP_DIR in pkg_path.parents:
        return pkg_path
    target_type = apptype
    target_dir = APPTYPE_PATHS[target_type]
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / pkg_path.name

    if pkg_path.resolve() == target_path.resolve():
        return pkg_path

    if target_path.exists():
        log("error", f"Target already exists, skipping move: {target_path}")
        return pkg_path

    try:
        shutil.move(str(pkg_path), str(target_path))
    except Exception as e:
        log("error", f"Error moving PKG to {target_path}: {e}")
        return pkg_path

    return target_path


def build_index(move_only):
    cache = load_cache()
    new_cache_pkgs = {}
    duplicate_found = False
    apps = []

    for pkg in PKG_DIR.rglob("*.pkg"):
        if any(part.startswith("_") for part in pkg.parts):
            continue
        rel_pre = pkg.relative_to(PKG_DIR).as_posix()
        try:
            stat = pkg.stat()
        except Exception:
            continue

        cache_entry = cache["pkgs"].get(rel_pre)
        cache_hit = (
                cache_entry
                and cache_entry.get("size") == stat.st_size
                and cache_entry.get("mtime") == stat.st_mtime
                and isinstance(cache_entry.get("data"), dict)
        )

        if cache_hit:
            data = cache_entry["data"]
            icon_entry = cache_entry.get("icon_entry")
        else:
            info, icon_entry = read_pkg_info(pkg)
            data = build_data(info, pkg)
            cache_entry = {
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "data": data,
                "icon_entry": icon_entry,
            }

        title = data["title"]
        titleid = data["titleid"]
        version = data["version"]
        base_category = data.get("category")
        apptype = data["apptype"]
        region = data.get("region")

        target_path = build_target_path(
            pkg,
            apptype,
            title,
            titleid,
            region,
            version,
            base_category,
            data.get("content_id"),
            data.get("app_type"),
        )
        if target_path.exists() and target_path.resolve() != pkg.resolve():
            log("error", f"Duplicate target exists, skipping: {target_path}")
            duplicate_found = True
            continue
        if target_path.resolve() != pkg.resolve():
            target_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(pkg), str(target_path))
                if target_path.name != pkg.name:
                    log("modified", f"Renamed PKG to {target_path}")
                pkg = target_path
            except Exception as e:
                log("error", f"Error moving PKG to {target_path}: {e}")
                continue
        rel = pkg.relative_to(PKG_DIR).as_posix()
        new_cache_pkgs[rel] = cache_entry

        if move_only:
            continue

        if APP_DIR in pkg.parents:
            apptype = "app"
            category = "ap"
        else:
            category = base_category

        MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        icon_out = MEDIA_DIR / f"{titleid}.png"
        if icon_entry is not None and not icon_out.exists():
            icon_bytes = read_icon_bytes(pkg, icon_entry)
            if icon_bytes:
                icon_out.write_bytes(icon_bytes)
                log("created", f"Extracted: {titleid} PKG icon to {icon_out}")

        pkg_rel = pkg.relative_to(PKG_DIR).as_posix()
        pkg_url = f"{settings.BASE_URL}/pkg/{quote(pkg_rel, safe='/')}"
        icon_url = f"{settings.BASE_URL}/_media/{quote(f'{titleid}.png')}"

        app = {
            "id": titleid,
            "name": title,
            "version": version,
            "apptype": apptype,
            "pkg": pkg_url,
            "icon": icon_url
        }
        if category:
            app["category"] = category
        if region:
            app["region"] = region
        apps.append(app)

    if move_only:
        cache["pkgs"] = new_cache_pkgs
        if duplicate_found:
            return 2
        return 0

    if duplicate_found:
        return 0

    cache["pkgs"] = new_cache_pkgs
    save_cache(cache)

    with open(INDEX_PATH, "w") as f:
        json.dump({"apps": apps}, f, indent=2)

    log("created", "Generated: index.json")
    return 0

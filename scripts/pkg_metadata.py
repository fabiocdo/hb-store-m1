from utils.parse_utils import parse_sfo_int
from utils.pkgtool_utils import read_pkg_info


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


def load_pkg_data(pkg_path):
    info, icon_entry = read_pkg_info(pkg_path)
    data = build_data(info, pkg_path)
    return data, icon_entry

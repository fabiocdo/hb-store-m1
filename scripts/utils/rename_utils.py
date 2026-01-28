import re

import settings
from utils.log_utils import log


def sanitize_filename(value):
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-![]().'")
    cleaned = []
    for ch in value:
        if ch.isalnum() or ch in allowed:
            cleaned.append(ch)
        else:
            cleaned.append("_")
    safe = "".join(cleaned)
    safe = safe.replace("/", "_").replace("\\", "_").replace("-", "_").replace(":", "_").strip()
    safe = "_".join(part for part in safe.split() if part)
    while "__" in safe:
        safe = safe.replace("__", "_")
    return safe


def format_title(value):
    return " ".join(part.capitalize() for part in value.split())


def render_rename(template, data):
    safe = {}
    for key, value in data.items():
        if value is None:
            safe[key] = ""
        elif key == "title":
            title_value = str(value)
            if settings.AUTO_RENAME_TITLE_MODE == "uppercase":
                title_value = title_value.upper()
            elif settings.AUTO_RENAME_TITLE_MODE == "lowercase":
                title_value = title_value.lower()
            elif settings.AUTO_RENAME_TITLE_MODE == "capitalize":
                title_value = format_title(title_value)
            title_value = re.sub(r"([A-Za-z])([0-9])", r"\1_\2", title_value)
            safe[key] = sanitize_filename(title_value)
        else:
            safe[key] = sanitize_filename(str(value))
    try:
        name = template.format_map(safe).strip()
    except ValueError as exc:
        log("error", f"Invalid AUTO_RENAME_TEMPLATE: {exc}. Using fallback.")
        name = "{title} [{titleid}][{apptype}]".format_map(safe).strip()
    if not name.lower().endswith(".pkg"):
        name = f"{name}.pkg"
    return name


def maybe_rename_pkg(pkg_path, title, titleid, apptype, region, version, category, content_id, app_type):
    if not settings.AUTO_RENAME_PKGS:
        return pkg_path
    if not titleid:
        return pkg_path
    new_name = render_rename(
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
    if pkg_path.name == new_name:
        return pkg_path
    target_path = pkg_path.with_name(new_name)
    if target_path.exists():
        return pkg_path
    try:
        pkg_path.rename(target_path)
        log("modified", f"Renamed PKG to {target_path}")
        return target_path
    except Exception:
        return pkg_path

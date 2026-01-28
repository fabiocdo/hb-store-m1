import os
import pathlib
import subprocess
import tempfile

from utils.log_utils import log
from utils.parse_utils import parse_sfo_entries

PKGTOOL_PATH = "/usr/local/bin/pkgtool"
DOTNET_GLOBALIZATION_ENV = "DOTNET_SYSTEM_GLOBALIZATION_INVARIANT"


def run_pkgtool(args):
    env = os.environ.copy()
    env.setdefault(DOTNET_GLOBALIZATION_ENV, "1")
    result = subprocess.run(
        [PKGTOOL_PATH] + args,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    return result.stdout


def list_pkg_entries(pkg_path):
    entries = {}
    output = run_pkgtool(["pkg_listentries", str(pkg_path)])
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("Offset"):
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        index = parts[3]
        name = parts[5] if len(parts) >= 6 else parts[4]
        entries[name] = index
    return entries


def parse_sfo_entries_from_pkg(sfo_path):
    output = run_pkgtool(["sfo_listentries", str(sfo_path)])
    return parse_sfo_entries(output)


def extract_pkg_entry(pkg_path, entry_id, out_path):
    args = ["pkg_extractentry", str(pkg_path), str(entry_id), str(out_path)]
    run_pkgtool(args)


def read_pkg_info(pkg_path):
    try:
        with tempfile.TemporaryDirectory(prefix="pkg_extract_") as tmpdir:
            entries = list_pkg_entries(pkg_path)
            sfo_entry = None
            icon_entry = None
            for name, entry_id in entries.items():
                lower = name.lower()
                normalized = lower.replace(".", "_")
                if "param_sfo" in normalized:
                    sfo_entry = entry_id
                elif normalized in {"icon0_png", "icon0_00_png", "pic0_png"}:
                    if icon_entry is None or normalized == "icon0_png":
                        icon_entry = entry_id

            if sfo_entry is None:
                log("error", f"PARAM_SFO not found in {pkg_path}")
                return {}, None

            tmp_root = pathlib.Path(tmpdir)
            sfo_path = tmp_root / "param.sfo"
            extract_pkg_entry(pkg_path, sfo_entry, sfo_path)
            info = parse_sfo_entries_from_pkg(sfo_path)

            return info, icon_entry
    except Exception:
        return {}, None


def read_icon_bytes(pkg_path, icon_entry):
    try:
        with tempfile.TemporaryDirectory(prefix="pkg_extract_") as tmpdir:
            tmp_root = pathlib.Path(tmpdir)
            icon_path = tmp_root / "icon0.png"
            extract_pkg_entry(pkg_path, icon_entry, icon_path)
            if icon_path.exists():
                return icon_path.read_bytes()
    except Exception:
        return None

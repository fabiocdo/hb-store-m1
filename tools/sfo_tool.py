import subprocess
from pathlib import Path


def _get_binary():
    root_dir = Path(__file__).resolve().parent.parent
    binary = root_dir / "bin" / "sfotool"
    return binary if binary.is_file() else None


def extract_sfo_data(pkg_path):
    binary = _get_binary()
    if binary is None:
        return ""
    try:
        return subprocess.check_output([str(binary), str(pkg_path)], text=True)
    except Exception:
        return ""

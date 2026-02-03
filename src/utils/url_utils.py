from __future__ import annotations

import os
import re


def build_base_url() -> str:
    """
    Build a base URL from SERVER_IP and ENABLE_SSL.

    :return: Base URL like http(s)://host[:port]
    """
    server_ip = os.environ.get("SERVER_IP", "").strip()
    if not server_ip:
        return ""
    server_ip = re.sub(r"^https?://", "", server_ip, flags=re.IGNORECASE)
    server_ip = server_ip.rstrip("/")
    scheme = "https" if os.environ.get("ENABLE_SSL", "").lower() == "true" else "http"
    return f"{scheme}://{server_ip}"

from __future__ import annotations

import hashlib
from pathlib import Path


def fingerprint_pkg(path: Path, size: int, mtime_ns: int) -> str:
    digest = hashlib.blake2b(digest_size=16)
    digest.update(f"{size}:{mtime_ns}".encode("utf-8"))

    with path.open("rb") as stream:
        head = stream.read(64 * 1024)
        digest.update(head)

        if size > 64 * 1024:
            tail_size = min(size, 64 * 1024)
            stream.seek(max(0, size - tail_size))
            digest.update(stream.read(tail_size))

    return digest.hexdigest()

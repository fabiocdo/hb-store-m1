from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from homebrew_cdn_m1_server.domain.protocols.snapshot_store_port import SnapshotStorePort


class JsonSnapshotStore(SnapshotStorePort):
    def __init__(self, snapshot_path: Path) -> None:
        self._snapshot_path = snapshot_path

    def load(self) -> Mapping[str, tuple[int, int]]:
        if not self._snapshot_path.exists():
            return {}
        try:
            raw = json.loads(self._snapshot_path.read_text("utf-8"))
        except (OSError, ValueError):
            return {}

        parsed: dict[str, tuple[int, int]] = {}
        for path, meta in (raw or {}).items():
            if not isinstance(meta, list) or len(meta) != 2:
                continue
            try:
                parsed[str(path)] = (int(meta[0]), int(meta[1]))
            except (TypeError, ValueError):
                continue
        return parsed

    def save(self, snapshot: Mapping[str, tuple[int, int]]) -> None:
        self._snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        data = {str(path): [int(meta[0]), int(meta[1])] for path, meta in snapshot.items()}
        self._snapshot_path.write_text(
            json.dumps(data, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

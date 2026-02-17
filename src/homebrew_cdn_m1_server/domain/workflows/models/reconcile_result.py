from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ReconcileResult:
    added: int
    updated: int
    removed: int
    failed: int
    exported_files: tuple[Path, ...]

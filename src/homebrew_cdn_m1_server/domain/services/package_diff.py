from __future__ import annotations

from homebrew_cdn_m1_server.application.dto.scan_delta import ScanDelta


def build_delta(
    previous: dict[str, tuple[int, int]],
    current: dict[str, tuple[int, int]],
) -> ScanDelta:
    previous_keys = set(previous)
    current_keys = set(current)

    added = sorted(current_keys - previous_keys)
    removed = sorted(previous_keys - current_keys)
    updated = sorted(
        key for key in previous_keys & current_keys if previous[key] != current[key]
    )

    return ScanDelta(added=tuple(added), updated=tuple(updated), removed=tuple(removed))

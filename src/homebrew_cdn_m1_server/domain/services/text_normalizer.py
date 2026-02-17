from __future__ import annotations

import unicodedata


_CONTROL_CHARACTERS = {chr(code) for code in range(0x00, 0x20)}
_CONTROL_CHARACTERS.add(chr(0x7F))


def normalize_text(value: str) -> str:
    """Normalize human-readable text to a stable Unicode representation."""
    raw = str(value or "")
    normalized = unicodedata.normalize("NFKC", raw)
    cleaned = "".join(ch for ch in normalized if ch not in _CONTROL_CHARACTERS or ch in {"\t", "\n", "\r"})
    return cleaned.strip()

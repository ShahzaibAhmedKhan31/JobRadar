"""Display labels for the known sources (also used for unknown/legacy keys)."""

from __future__ import annotations

SOURCE_LABELS: dict[str, str] = {
    "linkedin": "LinkedIn",
    "indeed": "Indeed",
    "manual_import": "Manual import",
    "fixtures": "Sample data",
    "other": "Other",
}


def source_label(key: str) -> str:
    return SOURCE_LABELS.get(key, key.replace("_", " ").title())

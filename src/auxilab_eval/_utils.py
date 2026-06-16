"""Utility helpers shared across the harness."""

from __future__ import annotations

from typing import Any, Optional


def get_field(obj: Any, path: Optional[str]) -> Any:
    """Retrieve a value from `obj` using a dotted path.

    - `path=None` returns the object itself.
    - Supports nested dicts and attribute access on objects.
    - Returns `None` if any segment is missing (no exception).
    """
    if path is None or path == "":
        return obj

    current = obj
    for segment in path.split("."):
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(segment)
        elif isinstance(current, list):
            try:
                current = current[int(segment)]
            except (ValueError, IndexError):
                return None
        else:
            current = getattr(current, segment, None)
    return current


def stringify(value: Any) -> str:
    """Coerce any value to a string for text-based evaluators."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)

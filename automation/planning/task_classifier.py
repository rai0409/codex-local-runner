from __future__ import annotations

from typing import Any

SUPPORTED_TASK_TYPES: tuple[str, ...] = (
    "inspect_read_only",
    "docs_only",
    "test_only",
    "correction_from_current_state",
    "regenerate_after_reset",
)

_FALLBACK_TASK_TYPE = "docs_only"
_ALIAS_MAP = {
    "inspect_read_only_extension": "inspect_read_only",
}


def classify_task_type(task_type: Any) -> str:
    """Return a supported task type using deterministic normalization."""
    normalized = str(task_type or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not normalized:
        return _FALLBACK_TASK_TYPE

    canonical = _ALIAS_MAP.get(normalized, normalized)
    if canonical in SUPPORTED_TASK_TYPES:
        return canonical

    return _FALLBACK_TASK_TYPE

from __future__ import annotations

from pathlib import Path

from automation.planning.task_classifier import classify_task_type

_TEMPLATE_FILES = {
    "inspect_read_only": "inspect_read_only.md",
    "docs_only": "docs_only.md",
    "test_only": "test_only.md",
    "correction_from_current_state": "correction_from_current_state.md",
    "regenerate_after_reset": "regenerate_after_reset.md",
}


def _template_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "prompts" / "templates"


def get_template_name(task_type: str) -> str:
    normalized = classify_task_type(task_type)
    return _TEMPLATE_FILES[normalized]


def get_template_path(task_type: str) -> Path:
    return _template_dir() / get_template_name(task_type)


def load_template(task_type: str) -> str:
    return get_template_path(task_type).read_text(encoding="utf-8").strip()

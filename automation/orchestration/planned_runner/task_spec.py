from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping


SUPPORTED_TASK_KINDS = ("add_function",)
_TASK_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def validate_task_spec(payload: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Validate a task spec object; returns (normalized spec, errors)."""
    errors: list[str] = []
    if not isinstance(payload, Mapping):
        return {}, ["task spec must be a JSON object"]

    task_id = _normalize_text(payload.get("task_id"))
    if not task_id or not _TASK_ID_PATTERN.match(task_id):
        errors.append("task_id must match ^[a-z0-9][a-z0-9._-]{0,63}$")

    kind = _normalize_text(payload.get("kind"))
    if kind not in SUPPORTED_TASK_KINDS:
        errors.append(f"kind must be one of {list(SUPPORTED_TASK_KINDS)}")

    repo_path = _normalize_text(payload.get("repo_path"))
    if not repo_path:
        errors.append("repo_path is required")
    elif not Path(repo_path).is_dir():
        errors.append(f"repo_path is not a directory: {repo_path}")

    target_file = _normalize_text(payload.get("target_file"))
    if not target_file or target_file.startswith("/") or ".." in target_file:
        errors.append("target_file must be a repo-relative path without '..'")

    function_name = _normalize_text(payload.get("function_name"))
    if not function_name or not function_name.isidentifier():
        errors.append("function_name must be a valid Python identifier")

    expression = _normalize_text(payload.get("expression"))
    if not expression:
        errors.append("expression is required")

    verify_commands = payload.get("verify_commands", [])
    if verify_commands and not (
        isinstance(verify_commands, list)
        and all(isinstance(cmd, (list, tuple)) and cmd for cmd in verify_commands)
    ):
        errors.append("verify_commands must be a list of non-empty argv lists")

    expected_unmodified = payload.get("expected_unmodified_files", [])
    if expected_unmodified and not isinstance(expected_unmodified, list):
        errors.append("expected_unmodified_files must be a list")

    spec = {
        "task_id": task_id,
        "kind": kind,
        "repo_path": repo_path,
        "target_file": target_file,
        "function_name": function_name,
        "expression": expression,
        "description": _normalize_text(payload.get("description")),
        "verify_commands": [
            [str(item) for item in cmd] for cmd in (verify_commands or [])
        ],
        "expected_unmodified_files": [
            _normalize_text(item) for item in (expected_unmodified or []) if _normalize_text(item)
        ],
        "allow_extra_files": bool(payload.get("allow_extra_files", False)),
    }
    return spec, errors


def load_task_spec(path: str | Path) -> tuple[dict[str, Any], list[str]]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError:
        return {}, [f"task spec unreadable: {path}"]
    except json.JSONDecodeError:
        return {}, [f"task spec is not valid JSON: {path}"]
    return validate_task_spec(payload)


__all__ = ["SUPPORTED_TASK_KINDS", "load_task_spec", "validate_task_spec"]

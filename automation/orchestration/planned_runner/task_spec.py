from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping


SUPPORTED_TASK_KINDS = ("add_function", "add_file")
_TASK_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")

# add_file safety limits.
ADD_FILE_MAX_CONTENT_BYTES = 100 * 1024  # 100 KB
# Secret-looking path patterns rejected for add_file (case-insensitive).
_SECRET_BASENAME_EXACT = {".env", "id_rsa", "id_ed25519", "id_rsa.pub", "id_ed25519.pub"}
_SECRET_SUBSTRINGS = ("secret", "token", "credential")


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _is_unsafe_relpath(target_file: str) -> bool:
    """True if the repo-relative target path is empty, absolute, or has traversal."""
    if not target_file or target_file.startswith("/") or ".." in target_file:
        return True
    if target_file.startswith("~") or "\x00" in target_file:
        return True
    return False


def _is_secret_path(target_file: str) -> bool:
    """True if the path looks like a secret/credentials file (add_file only)."""
    lowered = target_file.lower()
    name = Path(lowered).name
    if name in _SECRET_BASENAME_EXACT:
        return True
    if name == ".env" or name.startswith(".env."):
        return True
    if any(sub in lowered for sub in _SECRET_SUBSTRINGS):
        return True
    return False


def _validate_common(payload: Mapping[str, Any], errors: list[str]) -> dict[str, Any]:
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
    if _is_unsafe_relpath(target_file):
        errors.append("target_file must be a repo-relative path without '..'")

    verify_commands = payload.get("verify_commands", [])
    if verify_commands and not (
        isinstance(verify_commands, list)
        and all(isinstance(cmd, (list, tuple)) and cmd for cmd in verify_commands)
    ):
        errors.append("verify_commands must be a list of non-empty argv lists")

    expected_unmodified = payload.get("expected_unmodified_files", [])
    if expected_unmodified and not isinstance(expected_unmodified, list):
        errors.append("expected_unmodified_files must be a list")

    return {
        "task_id": task_id,
        "kind": kind,
        "repo_path": repo_path,
        "target_file": target_file,
        "description": _normalize_text(payload.get("description")),
        "verify_commands": [
            [str(item) for item in cmd] for cmd in (verify_commands or [])
        ],
        "expected_unmodified_files": [
            _normalize_text(item) for item in (expected_unmodified or []) if _normalize_text(item)
        ],
        "allow_extra_files": bool(payload.get("allow_extra_files", False)),
    }


def validate_task_spec(payload: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Validate a task spec object; returns (normalized spec, errors). Never raises."""
    errors: list[str] = []
    if not isinstance(payload, Mapping):
        return {}, ["task spec must be a JSON object"]

    spec = _validate_common(payload, errors)
    kind = spec["kind"]

    if kind == "add_function":
        function_name = _normalize_text(payload.get("function_name"))
        if not function_name or not function_name.isidentifier():
            errors.append("function_name must be a valid Python identifier")
        expression = _normalize_text(payload.get("expression"))
        if not expression:
            errors.append("expression is required")
        spec["function_name"] = function_name
        spec["expression"] = expression

    elif kind == "add_file":
        # add_file: create a NEW repo-relative text file via the existing
        # Codex/effect-gated path. Strict path + content safety here; the strict
        # effect gate enforces that ONLY the target file is created.
        target_file = spec["target_file"]
        if target_file and not _is_unsafe_relpath(target_file) and _is_secret_path(target_file):
            errors.append("target_file looks like a secret/credentials path and is rejected")
        content = payload.get("content")
        if not isinstance(content, str) or content == "":
            errors.append("content is required and must be a non-empty string")
            content = "" if not isinstance(content, str) else content
        else:
            if "\x00" in content:
                errors.append("content must be text (binary/NUL bytes rejected)")
            if len(content.encode("utf-8", errors="ignore")) > ADD_FILE_MAX_CONTENT_BYTES:
                errors.append(f"content exceeds max size {ADD_FILE_MAX_CONTENT_BYTES} bytes")
        spec["content"] = content
        spec["allow_overwrite"] = bool(payload.get("allow_overwrite", False))
        spec["create_parent_dirs"] = bool(payload.get("create_parent_dirs", False))

    return spec, errors


def load_task_spec(path: str | Path) -> tuple[dict[str, Any], list[str]]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError:
        return {}, [f"task spec unreadable: {path}"]
    except json.JSONDecodeError:
        return {}, [f"task spec is not valid JSON: {path}"]
    return validate_task_spec(payload)


__all__ = [
    "SUPPORTED_TASK_KINDS",
    "ADD_FILE_MAX_CONTENT_BYTES",
    "load_task_spec",
    "validate_task_spec",
]

"""Strict, immutable single-repository task specifications."""
from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from orchestrator.codex_execution import validate_codex_execution_timeout_seconds

REPOSITORY_SINGLE_TASK_SPEC_SCHEMA_VERSION = "1"
_FIELDS = frozenset(("schema_version", "task_id", "expected_head_sha", "prompt", "allowed_changed_paths", "commit_message", "execution_timeout_seconds"))
_REQUIRED_FIELDS = _FIELDS - {"execution_timeout_seconds"}
_TASK_ID = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
_SHA = re.compile(r"^[0-9a-f]{40}$")

class RepositorySingleTaskSpecValidationError(ValueError):
    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}")

@dataclass(frozen=True)
class RepositorySingleTaskSpec:
    schema_version: str
    task_id: str
    expected_head_sha: str
    prompt: str
    allowed_changed_paths: tuple[str, ...]
    commit_message: str
    execution_timeout_seconds: int | None = None

def _error(code: str, message: str) -> RepositorySingleTaskSpecValidationError:
    return RepositorySingleTaskSpecValidationError(code, message)

def _mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping): raise _error("single_task_spec.invalid_type", "must be an object")
    return value

def _text(value: Any, code: str, *, single: bool = True) -> str:
    if not isinstance(value, str) or not value or "\0" in value or (single and ("\n" in value or "\r" in value)):
        raise _error(code, "invalid text")
    if single and value.strip() != value: raise _error(code, "invalid surrounding whitespace")
    return value

def validate_repository_single_task_spec(value: Mapping[str, Any] | RepositorySingleTaskSpec) -> RepositorySingleTaskSpec:
    raw = asdict(value) if isinstance(value, RepositorySingleTaskSpec) else _mapping(value)
    if isinstance(value, RepositorySingleTaskSpec):
        raw["allowed_changed_paths"] = list(value.allowed_changed_paths)
        if value.execution_timeout_seconds is None:
            del raw["execution_timeout_seconds"]
    unknown = sorted(str(key) for key in raw if key not in _FIELDS)
    if unknown: raise _error(f"single_task_spec.{unknown[0]}.unknown_field", "unknown field")
    missing = next((key for key in _REQUIRED_FIELDS if key not in raw), None)
    if missing: raise _error(f"single_task_spec.{missing}.required", "required")
    if raw["schema_version"] != REPOSITORY_SINGLE_TASK_SPEC_SCHEMA_VERSION: raise _error("single_task_spec.schema_version.unsupported", "unsupported schema")
    task_id = _text(raw["task_id"], "single_task_spec.task_id.invalid")
    if not task_id.isascii() or len(task_id) > 64 or not _TASK_ID.fullmatch(task_id): raise _error("single_task_spec.task_id.invalid", "invalid task ID")
    sha = _text(raw["expected_head_sha"], "single_task_spec.expected_head_sha.invalid")
    if not _SHA.fullmatch(sha): raise _error("single_task_spec.expected_head_sha.invalid", "must be lowercase full SHA")
    prompt = _text(raw["prompt"], "single_task_spec.prompt.invalid", single=False)
    if not prompt.strip() or len(prompt.encode("utf-8")) > 200000: raise _error("single_task_spec.prompt.invalid", "invalid prompt")
    paths = raw["allowed_changed_paths"]
    if not isinstance(paths, list) or not paths: raise _error("single_task_spec.allowed_changed_paths.invalid", "must be nonempty list")
    validated=[]
    for item in paths:
        path=_text(item,"single_task_spec.allowed_changed_paths.invalid")
        parts=path.split("/")
        if path == "." or path.startswith("/") or path.endswith("/") or "\\" in path or any(part in {"", ".", "..", ".git"} for part in parts): raise _error("single_task_spec.allowed_changed_paths.invalid", "invalid repository path")
        validated.append(path)
    if len(set(validated)) != len(validated): raise _error("single_task_spec.allowed_changed_paths.duplicate", "duplicate path")
    message=_text(raw["commit_message"], "single_task_spec.commit_message.invalid")
    if len(message.encode("utf-8")) > 200: raise _error("single_task_spec.commit_message.invalid", "too long")
    timeout = None
    if "execution_timeout_seconds" in raw:
        try:
            timeout = validate_codex_execution_timeout_seconds(raw["execution_timeout_seconds"])
        except ValueError as exc:
            raise _error("single_task_spec.execution_timeout_seconds.invalid", "must be a bounded positive integer") from exc
    return RepositorySingleTaskSpec("1", task_id, sha, prompt, tuple(sorted(validated)), message, timeout)

def load_repository_single_task_spec(path: str | os.PathLike[str]) -> RepositorySingleTaskSpec:
    if isinstance(path, bool) or not isinstance(path, (str, os.PathLike)): raise _error("single_task_spec_file.invalid_type", "invalid path")
    value=os.fspath(path)
    if isinstance(value, bytes) or not value: raise _error("single_task_spec_file.invalid_type", "invalid path")
    candidate=Path(value)
    if not candidate.exists(): raise _error("single_task_spec_file.not_found", "not found")
    if not candidate.is_file(): raise _error("single_task_spec_file.not_file", "not a file")
    try: raw=json.loads(candidate.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc: raise _error("single_task_spec_file.read_failed", "invalid UTF-8") from exc
    except (OSError, json.JSONDecodeError) as exc: raise _error("single_task_spec_file.json_invalid", "invalid JSON") from exc
    return validate_repository_single_task_spec(raw)

def repository_single_task_spec_to_mapping(spec: RepositorySingleTaskSpec) -> dict[str, Any]:
    if not isinstance(spec, RepositorySingleTaskSpec): raise TypeError("spec must be RepositorySingleTaskSpec")
    value=validate_repository_single_task_spec(spec)
    return {"schema_version":value.schema_version,"task_id":value.task_id,"expected_head_sha":value.expected_head_sha,"prompt":value.prompt,"allowed_changed_paths":list(value.allowed_changed_paths),"commit_message":value.commit_message, **({"execution_timeout_seconds": value.execution_timeout_seconds} if value.execution_timeout_seconds is not None else {})}

def serialize_repository_single_task_spec(spec: RepositorySingleTaskSpec) -> str:
    return json.dumps(repository_single_task_spec_to_mapping(spec), ensure_ascii=True, sort_keys=True, separators=(",", ":"))

__all__=["REPOSITORY_SINGLE_TASK_SPEC_SCHEMA_VERSION","RepositorySingleTaskSpec","RepositorySingleTaskSpecValidationError","load_repository_single_task_spec","repository_single_task_spec_to_mapping","serialize_repository_single_task_spec","validate_repository_single_task_spec"]

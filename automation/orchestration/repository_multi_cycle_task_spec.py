"""Strict human-authored ordered queues for repository multi-cycle execution."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from automation.orchestration.repository_single_task_spec import (
    RepositorySingleTaskSpecValidationError,
    validate_repository_single_task_spec,
)

REPOSITORY_MULTI_CYCLE_TASK_SPEC_SCHEMA_VERSION = "1"
MAX_MULTI_CYCLE_TASKS = 64
_TOP_LEVEL_FIELDS = frozenset(("schema_version", "tasks"))
_TASK_FIELDS = frozenset(("task_id", "prompt", "allowed_changed_paths", "commit_message"))


class RepositoryMultiCycleTaskSpecValidationError(ValueError):
    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}")


@dataclass(frozen=True)
class RepositoryMultiCycleTask:
    task_id: str
    prompt: str
    allowed_changed_paths: tuple[str, ...]
    commit_message: str


@dataclass(frozen=True)
class RepositoryMultiCycleTaskSpec:
    schema_version: str
    tasks: tuple[RepositoryMultiCycleTask, ...]


def _error(reason_code: str, message: str) -> RepositoryMultiCycleTaskSpecValidationError:
    return RepositoryMultiCycleTaskSpecValidationError(reason_code, message)


def _task(value: Any) -> RepositoryMultiCycleTask:
    if not isinstance(value, Mapping):
        raise _error("multi_cycle_queue.task.invalid_type", "task must be an object")
    unknown = sorted(str(key) for key in value if key not in _TASK_FIELDS)
    if unknown:
        raise _error(f"multi_cycle_queue.task.{unknown[0]}.unknown_field", "unknown task field")
    missing = next((key for key in _TASK_FIELDS if key not in value), None)
    if missing:
        raise _error(f"multi_cycle_queue.task.{missing}.required", "required task field")
    try:
        single = validate_repository_single_task_spec({
            "schema_version": "1", "expected_head_sha": "0" * 40,
            "task_id": value["task_id"], "prompt": value["prompt"],
            "allowed_changed_paths": value["allowed_changed_paths"], "commit_message": value["commit_message"],
        })
    except RepositorySingleTaskSpecValidationError as exc:
        raise _error("multi_cycle_queue." + exc.reason_code.removeprefix("single_task_spec."), "invalid task field") from exc
    return RepositoryMultiCycleTask(single.task_id, single.prompt, single.allowed_changed_paths, single.commit_message)


def validate_repository_multi_cycle_task_spec(value: Mapping[str, Any] | RepositoryMultiCycleTaskSpec) -> RepositoryMultiCycleTaskSpec:
    raw = repository_multi_cycle_task_spec_to_mapping(value) if isinstance(value, RepositoryMultiCycleTaskSpec) else value
    if not isinstance(raw, Mapping):
        raise _error("multi_cycle_queue.invalid_type", "queue must be an object")
    unknown = sorted(str(key) for key in raw if key not in _TOP_LEVEL_FIELDS)
    if unknown:
        raise _error(f"multi_cycle_queue.{unknown[0]}.unknown_field", "unknown field")
    missing = next((key for key in _TOP_LEVEL_FIELDS if key not in raw), None)
    if missing:
        raise _error(f"multi_cycle_queue.{missing}.required", "required field")
    if raw["schema_version"] != REPOSITORY_MULTI_CYCLE_TASK_SPEC_SCHEMA_VERSION:
        raise _error("multi_cycle_queue.schema_version.unsupported", "unsupported schema")
    items = raw["tasks"]
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_MULTI_CYCLE_TASKS:
        raise _error("multi_cycle_queue.tasks.invalid_count", "must contain 1 to 64 tasks")
    tasks = tuple(_task(item) for item in items)
    if len({task.task_id for task in tasks}) != len(tasks):
        raise _error("multi_cycle_queue.task_id.duplicate", "duplicate task ID")
    return RepositoryMultiCycleTaskSpec("1", tasks)


def repository_multi_cycle_task_spec_to_mapping(spec: RepositoryMultiCycleTaskSpec) -> dict[str, Any]:
    if not isinstance(spec, RepositoryMultiCycleTaskSpec):
        raise TypeError("spec must be RepositoryMultiCycleTaskSpec")
    return {"schema_version": spec.schema_version, "tasks": [asdict(task) | {"allowed_changed_paths": list(task.allowed_changed_paths)} for task in spec.tasks]}


def serialize_repository_multi_cycle_task_spec(spec: RepositoryMultiCycleTaskSpec) -> str:
    return json.dumps(repository_multi_cycle_task_spec_to_mapping(spec), ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def load_repository_multi_cycle_task_spec(path: str | Path) -> RepositoryMultiCycleTaskSpec:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise _error("multi_cycle_queue_file.json_invalid", "invalid JSON") from exc
    return validate_repository_multi_cycle_task_spec(value)


__all__ = [
    "MAX_MULTI_CYCLE_TASKS", "REPOSITORY_MULTI_CYCLE_TASK_SPEC_SCHEMA_VERSION", "RepositoryMultiCycleTask",
    "RepositoryMultiCycleTaskSpec", "RepositoryMultiCycleTaskSpecValidationError", "load_repository_multi_cycle_task_spec",
    "repository_multi_cycle_task_spec_to_mapping", "serialize_repository_multi_cycle_task_spec", "validate_repository_multi_cycle_task_spec",
]

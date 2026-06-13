"""Project Task Plan model (Prompt645).

A Project Task Plan = a validated Project Intent + an ordered, bounded list of
planned tasks (with dependencies/ordering/status) that a FUTURE planner/orchestrator
will turn into daemon task specs and enqueue. This module is the pure, offline data
model only: it performs NO execution, NO enqueue, NO Codex, NO daemon-queue calls,
NO git, NO network. Validation never raises — it returns (normalized_plan, errors).

A pure offline helper (`planned_task_to_task_spec`) converts a planned-task entry
into the daemon's task-spec dict shape so future prompts can produce specs that
task_spec.validate_task_spec accepts. It does NO I/O and does NOT enqueue.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from automation.orchestration.planned_runner.project_intent import (
    PROJECT_INTENT_SCHEMA_VERSION,
    validate_project_intent,
)

PROJECT_PLAN_SCHEMA_VERSION = "v1"

PLANNED_TASK_STATUSES = (
    "planned",
    "queued",
    "running",
    "done",
    "failed",
    "blocked",
    "skipped",
)
PLAN_SOURCES = ("manual", "generated")

_TASK_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")

# task-spec fields a planned task may carry in its task_spec_payload (everything the
# daemon task spec accepts except task_id/kind, which come from the planned task).
_TASK_SPEC_PAYLOAD_FIELDS = (
    "repo_path",
    "target_file",
    "function_name",
    "expression",
    "description",
    "verify_commands",
    "expected_unmodified_files",
    "allow_extra_files",
)


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _as_int(value: Any, *, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    text = _normalize_text(value)
    if text.lstrip("-").isdigit():
        return int(text)
    return default


def _normalize_payload(raw: Any) -> dict[str, Any]:
    """Keep only recognized task-spec payload fields, preserving value types."""
    if not isinstance(raw, Mapping):
        return {}
    out: dict[str, Any] = {}
    for field in _TASK_SPEC_PAYLOAD_FIELDS:
        if field in raw:
            out[field] = raw[field]
    return out


def _normalize_task(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        return {
            "task_id": "",
            "kind": "",
            "task_spec_payload": {},
            "generated_task_spec_ref": "",
            "generated_task_spec_path": "",
            "depends_on": [],
            "order": 0,
            "status": "planned",
        }
    status = _normalize_text(raw.get("status"), default="planned")
    depends_on = (
        [_normalize_text(d) for d in raw.get("depends_on") if _normalize_text(d)]
        if isinstance(raw.get("depends_on"), (list, tuple))
        else []
    )
    return {
        "task_id": _normalize_text(raw.get("task_id")),
        "kind": _normalize_text(raw.get("kind")),
        "task_spec_payload": _normalize_payload(raw.get("task_spec_payload")),
        "generated_task_spec_ref": _normalize_text(raw.get("generated_task_spec_ref")),
        "generated_task_spec_path": _normalize_text(raw.get("generated_task_spec_path")),
        "depends_on": depends_on,
        "order": _as_int(raw.get("order"), default=0),
        "status": status,
    }


def _detect_cycle(task_ids: list[str], edges: dict[str, list[str]]) -> bool:
    """Return True if depends_on edges contain a cycle (Kahn's algorithm)."""
    indeg = {tid: 0 for tid in task_ids}
    for tid in task_ids:
        for dep in edges.get(tid, []):
            if dep in indeg:
                indeg[tid] += 1  # tid depends on dep -> edge dep -> tid
    # Build reverse adjacency dep -> [tids depending on dep]
    adj: dict[str, list[str]] = {tid: [] for tid in task_ids}
    for tid in task_ids:
        for dep in edges.get(tid, []):
            if dep in adj:
                adj[dep].append(tid)
    queue = [tid for tid in task_ids if indeg[tid] == 0]
    processed = 0
    while queue:
        node = queue.pop()
        processed += 1
        for nxt in adj[node]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    return processed != len(task_ids)


def validate_project_task_plan(payload: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Validate a project task plan object; returns (normalized plan, errors).

    Never raises. Idempotent: validating a normalized plan returns an equal plan."""
    errors: list[str] = []
    if not isinstance(payload, Mapping):
        return {}, ["project task plan must be a JSON object"]

    intent_raw = payload.get("intent")
    intent, intent_errors = validate_project_intent(intent_raw if isinstance(intent_raw, Mapping) else {})
    errors.extend(f"intent.{e}" for e in intent_errors)
    allowed_kinds = set(intent.get("allowed_task_kinds", []) or [])
    max_tasks = int(intent.get("safety_limits", {}).get("max_tasks", 0) or 0)

    raw_tasks = payload.get("tasks")
    tasks: list[dict[str, Any]] = []
    if raw_tasks is None or (isinstance(raw_tasks, (list, tuple)) and len(raw_tasks) == 0):
        errors.append("tasks must be a non-empty list")
    elif not isinstance(raw_tasks, (list, tuple)):
        errors.append("tasks must be a list")
    else:
        tasks = [_normalize_task(t) for t in raw_tasks]

    seen_ids: set[str] = set()
    for index, task in enumerate(tasks):
        tid = task["task_id"]
        loc = tid or f"index {index}"
        if not tid or not _TASK_ID_PATTERN.match(tid):
            errors.append(f"task[{loc}].task_id must match ^[a-z0-9][a-z0-9._-]{{0,63}}$")
        elif tid in seen_ids:
            errors.append(f"duplicate task_id: {tid}")
        else:
            seen_ids.add(tid)
        if task["kind"] not in allowed_kinds:
            errors.append(
                f"task[{loc}].kind '{task['kind']}' not in intent.allowed_task_kinds {sorted(allowed_kinds)}"
            )
        if not task["task_spec_payload"] and not task["generated_task_spec_ref"]:
            errors.append(
                f"task[{loc}] must provide either task_spec_payload or generated_task_spec_ref"
            )
        if task["status"] not in PLANNED_TASK_STATUSES:
            errors.append(f"task[{loc}].status must be one of {list(PLANNED_TASK_STATUSES)}")

    # Bounds: number of tasks must not exceed the intent's safety_limits.max_tasks.
    if max_tasks and len(tasks) > max_tasks:
        errors.append(f"tasks count {len(tasks)} exceeds intent safety_limits.max_tasks {max_tasks}")

    # Dependency integrity: no dangling refs, no cycles (only when ids are well-formed).
    valid_ids = {t["task_id"] for t in tasks if t["task_id"]}
    edges: dict[str, list[str]] = {}
    for index, task in enumerate(tasks):
        tid = task["task_id"]
        loc = tid or f"index {index}"
        deps = task["depends_on"]
        edges[tid] = deps
        for dep in deps:
            if dep == tid:
                errors.append(f"task[{loc}] cannot depend on itself")
            elif dep not in valid_ids:
                errors.append(f"task[{loc}] has dangling depends_on '{dep}'")
    if valid_ids and not any("dangling" in e or "depend on itself" in e for e in errors):
        if _detect_cycle([t["task_id"] for t in tasks if t["task_id"]], edges):
            errors.append("tasks contain a dependency cycle")

    source = _normalize_text(payload.get("source"), default="manual")
    if source not in PLAN_SOURCES:
        errors.append(f"source must be one of {list(PLAN_SOURCES)}")

    plan = {
        "schema_version": _normalize_text(
            payload.get("schema_version"), default=PROJECT_PLAN_SCHEMA_VERSION
        ),
        "intent": intent,
        "tasks": tasks,
        "completion_criteria": _normalize_text(payload.get("completion_criteria")),
        "generated_at": _normalize_text(payload.get("generated_at")),
        "source": source,
        "notes": _normalize_text(payload.get("notes")),
    }
    return plan, errors


def planned_task_to_task_spec(
    task: Mapping[str, Any],
    *,
    overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Pure, offline conversion of a planned-task entry into a daemon task-spec dict.

    Performs NO I/O and does NOT enqueue. The result is intended to be passed to
    task_spec.validate_task_spec (which separately checks repo_path existence at
    execution time). `overrides` may supply/replace payload fields (e.g. a concrete
    repo_path) without mutating the plan."""
    payload = dict(_normalize_payload(task.get("task_spec_payload")))
    if overrides:
        for key in _TASK_SPEC_PAYLOAD_FIELDS:
            if key in overrides:
                payload[key] = overrides[key]
    spec: dict[str, Any] = {
        "task_id": _normalize_text(task.get("task_id")),
        "kind": _normalize_text(task.get("kind")),
    }
    spec.update(payload)
    return spec


def project_plan_to_json(plan: Mapping[str, Any]) -> str:
    return json.dumps(dict(plan), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def project_plan_from_json(text: str) -> tuple[dict[str, Any], list[str]]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}, ["project task plan is not valid JSON"]
    return validate_project_task_plan(payload)


def load_project_task_plan(path: str | Path) -> tuple[dict[str, Any], list[str]]:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return {}, [f"project task plan unreadable: {path}"]
    return project_plan_from_json(text)


__all__ = [
    "PROJECT_PLAN_SCHEMA_VERSION",
    "PLANNED_TASK_STATUSES",
    "PLAN_SOURCES",
    "validate_project_task_plan",
    "planned_task_to_task_spec",
    "project_plan_to_json",
    "project_plan_from_json",
    "load_project_task_plan",
]

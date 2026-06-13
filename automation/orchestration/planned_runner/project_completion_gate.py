"""Project progress / completion gate (Prompt648).

A pure, offline, deterministic evaluator that, given a ProjectTaskPlan plus explicit
per-task result/status data, decides whether the project is complete, in_progress,
blocked, or failed. It runs NO daemon, NO Codex, mutates NO queue, and never raises.

Safety rule: the project is NEVER marked complete while any required task is
failed, blocked, pending, or unknown.
"""
from __future__ import annotations

from typing import Any, Mapping

from automation.orchestration.planned_runner.project_plan import (
    validate_project_task_plan,
)

# Supported minimal completion criteria.
SUPPORTED_COMPLETION_CRITERIA = ("all_tasks_done", "no_failed_required_tasks")
_DEFAULT_CRITERIA = ("all_tasks_done", "no_failed_required_tasks")

# Normalize raw result/status strings into effective task states.
_DONE = {"done", "success", "succeeded", "completed", "passed", "ok"}
_FAILED = {"failed", "failure", "error", "execution_error", "timeout"}
_BLOCKED = {"blocked"}
_PENDING = {"planned", "pending", "queued", "running", "claimed", ""}


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _effective_state(raw: Any) -> str:
    """Map a raw status (string or {'status': ...}) to done/failed/blocked/pending/unknown."""
    if isinstance(raw, Mapping):
        raw = raw.get("status")
    text = _normalize_text(raw).lower()
    if text in _DONE:
        return "done"
    if text in _FAILED:
        return "failed"
    if text in _BLOCKED:
        return "blocked"
    if text in _PENDING:
        return "pending"
    return "unknown"


def evaluate_project_completion(
    plan: Mapping[str, Any],
    task_results: Mapping[str, Any] | None = None,
    *,
    completion_criteria: list[str] | tuple[str, ...] | None = None,
    required_task_ids: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Evaluate project completion. Returns a structured verdict; never raises.

    - plan: a ProjectTaskPlan (validated here).
    - task_results: optional mapping task_id -> status string or {'status': ...}.
      Missing entries fall back to the plan task's own `status` field.
    - completion_criteria: subset of SUPPORTED_COMPLETION_CRITERIA (default: both).
    - required_task_ids: subset of plan task_ids treated as required (default: all).

    Result keys: status (complete|in_progress|blocked|failed|invalid), complete (bool),
    counts (per-state), task_states (id->state), required_task_ids, criteria_evaluated,
    reasons, errors.
    """
    errors: list[str] = []
    normalized_plan, plan_errors = validate_project_task_plan(plan)
    if plan_errors:
        return {
            "status": "invalid",
            "complete": False,
            "counts": {"done": 0, "failed": 0, "blocked": 0, "pending": 0, "unknown": 0, "total": 0},
            "task_states": {},
            "required_task_ids": [],
            "criteria_evaluated": [],
            "reasons": ["plan invalid"],
            "errors": [f"plan invalid: {e}" for e in plan_errors],
        }

    criteria = list(completion_criteria) if completion_criteria is not None else list(_DEFAULT_CRITERIA)
    unknown_criteria = [c for c in criteria if c not in SUPPORTED_COMPLETION_CRITERIA]
    if unknown_criteria:
        errors.append(f"unsupported completion_criteria: {unknown_criteria}")
        criteria = [c for c in criteria if c in SUPPORTED_COMPLETION_CRITERIA]

    results = task_results or {}
    if not isinstance(results, Mapping):
        errors.append("task_results must be a mapping of task_id -> status")
        results = {}

    tasks = list(normalized_plan.get("tasks", []) or [])
    all_ids = [t["task_id"] for t in tasks]
    if required_task_ids is None:
        required = set(all_ids)
    else:
        required = {tid for tid in required_task_ids if tid in all_ids}
        dangling = [tid for tid in required_task_ids if tid not in all_ids]
        if dangling:
            errors.append(f"required_task_ids not in plan: {dangling}")

    task_states: dict[str, str] = {}
    counts = {"done": 0, "failed": 0, "blocked": 0, "pending": 0, "unknown": 0}
    for task in tasks:
        tid = task["task_id"]
        raw = results.get(tid, task.get("status", "planned"))
        state = _effective_state(raw)
        task_states[tid] = state
        counts[state] += 1
    counts["total"] = len(tasks)

    req_states = [task_states[t] for t in all_ids if t in required]
    any_failed = any(s == "failed" for s in req_states)
    any_blocked = any(s == "blocked" for s in req_states)
    any_unknown = any(s == "unknown" for s in req_states)
    any_pending = any(s == "pending" for s in req_states)
    all_required_done = bool(req_states) and all(s == "done" for s in req_states)

    reasons: list[str] = []
    if any_failed:
        status = "failed"
        reasons.append("one or more required tasks failed")
    elif any_blocked:
        status = "blocked"
        reasons.append("one or more required tasks blocked")
    elif any_unknown:
        status = "in_progress"
        reasons.append("one or more required tasks have unknown status")
    elif any_pending:
        status = "in_progress"
        reasons.append("one or more required tasks pending")
    elif all_required_done:
        status = "complete"
        reasons.append("all required tasks done")
    else:
        status = "in_progress"
        reasons.append("no required tasks resolved")

    # Apply criteria gating (defense in depth): complete requires the criteria too.
    complete = status == "complete"
    if complete and "all_tasks_done" in criteria:
        if counts["done"] != counts["total"] and required == set(all_ids):
            complete = False
            status = "in_progress"
            reasons.append("all_tasks_done criterion not satisfied")
    if "no_failed_required_tasks" in criteria and any_failed:
        complete = False  # already failed above

    return {
        "status": status,
        "complete": bool(complete),
        "counts": counts,
        "task_states": task_states,
        "required_task_ids": sorted(required),
        "criteria_evaluated": criteria,
        "reasons": reasons,
        "errors": errors,
    }


__all__ = [
    "SUPPORTED_COMPLETION_CRITERIA",
    "evaluate_project_completion",
]

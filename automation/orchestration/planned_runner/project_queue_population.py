"""Project queue population (Prompt647).

A pure, offline, deterministic layer that materializes a validated ProjectTaskPlan
into daemon-queue-compatible task spec files inside an EXPLICIT caller-provided
output queue directory. It does NOT run the daemon, Codex, or any task; it does NOT
mutate any live/default queue; it does NOT claim/execute tasks.

Because the daemon queue has no dependency primitive (claim_next_task processes
pending/*.json in sorted filename order, one at a time), dependencies are represented
as PROCESSING ORDER: tasks are written in deterministic topological order with a
zero-padded numeric filename prefix so a sequential daemon claims them in dependency
order. A deterministic warning is emitted when the plan has any dependency edges,
because the queue does not hard-enforce them.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from automation.orchestration.planned_runner.daemon_queue import ensure_queue_dirs
from automation.orchestration.planned_runner.project_plan import (
    planned_task_to_task_spec,
    validate_project_task_plan,
)


def _result(
    status: str,
    *,
    errors: list[str],
    warnings: list[str],
    output_dir: str,
    written_files: list[str],
    task_count: int,
) -> dict[str, Any]:
    return {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "output_dir": output_dir,
        "written_files": written_files,
        "task_count": task_count,
    }


def _topological_order(tasks: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Deterministic topological order (Kahn's), tie-broken by (order, task_id).

    The plan validator already rejects cycles/dangling deps, so a full ordering
    exists; if a cycle somehow remains, returns [] to signal the caller."""
    by_id = {t["task_id"]: dict(t) for t in tasks if t.get("task_id")}
    deps = {
        tid: [d for d in (by_id[tid].get("depends_on") or []) if d in by_id]
        for tid in by_id
    }
    indeg = {tid: len(deps[tid]) for tid in by_id}
    dependents: dict[str, list[str]] = {tid: [] for tid in by_id}
    for tid in by_id:
        for dep in deps[tid]:
            dependents[dep].append(tid)

    def _key(tid: str) -> tuple[int, str]:
        return (int(by_id[tid].get("order", 0) or 0), tid)

    ready = sorted([tid for tid in by_id if indeg[tid] == 0], key=_key)
    ordered: list[str] = []
    while ready:
        tid = ready.pop(0)
        ordered.append(tid)
        for dependent in dependents[tid]:
            indeg[dependent] -= 1
            if indeg[dependent] == 0:
                ready.append(dependent)
        ready = sorted(ready, key=_key)
    if len(ordered) != len(by_id):
        return []
    return [by_id[tid] for tid in ordered]


def populate_queue_from_plan(
    plan: Mapping[str, Any],
    output_queue_dir: str | Path | None,
    *,
    repo_path_override: str | None = None,
    create_dirs: bool = True,
) -> dict[str, Any]:
    """Write daemon-queue-compatible task spec files from a validated ProjectTaskPlan
    into an explicit output queue directory. Never raises.

    Returns {status, errors, warnings, output_dir, written_files, task_count}.
    status is "success" only when the plan is valid, the explicit output dir is
    usable, and all task files were written deterministically."""
    warnings: list[str] = []

    # An explicit output directory is mandatory; never fall back to a live/default queue.
    output_text = "" if output_queue_dir is None else str(output_queue_dir).strip()
    if not output_text:
        return _result(
            "blocked",
            errors=["output_queue_dir is required (no live/default queue fallback)"],
            warnings=warnings,
            output_dir="",
            written_files=[],
            task_count=0,
        )

    normalized_plan, plan_errors = validate_project_task_plan(plan)
    if plan_errors:
        return _result(
            "blocked",
            errors=[f"plan invalid: {e}" for e in plan_errors],
            warnings=warnings,
            output_dir=output_text,
            written_files=[],
            task_count=0,
        )

    tasks = list(normalized_plan.get("tasks", []) or [])
    ordered = _topological_order(tasks)
    if len(ordered) != len(tasks):
        return _result(
            "blocked",
            errors=["could not compute a topological order (unexpected dependency cycle)"],
            warnings=warnings,
            output_dir=output_text,
            written_files=[],
            task_count=0,
        )

    if any((t.get("depends_on") or []) for t in tasks):
        warnings.append(
            "dependencies are represented as queue processing order only; the daemon "
            "queue has no dependency primitive and does not hard-enforce dependencies "
            "(assumes sequential single-task claiming)"
        )

    output_dir = Path(output_text)
    pending_dir = output_dir / "pending"
    if create_dirs:
        ensure_queue_dirs(output_dir)
    elif not pending_dir.is_dir():
        return _result(
            "blocked",
            errors=[f"output queue pending dir does not exist and create_dirs=False: {pending_dir.as_posix()}"],
            warnings=warnings,
            output_dir=output_text,
            written_files=[],
            task_count=0,
        )

    overrides = {"repo_path": repo_path_override} if repo_path_override else None
    width = max(3, len(str(len(ordered))))
    written_files: list[str] = []
    for index, task in enumerate(ordered):
        spec = planned_task_to_task_spec(task, overrides=overrides)
        task_id = str(spec.get("task_id") or "").strip()
        filename = f"{index:0{width}d}-{task_id}.json"
        target = pending_dir / filename
        target.write_text(
            json.dumps(spec, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written_files.append(target.as_posix())

    return _result(
        "success",
        errors=[],
        warnings=warnings,
        output_dir=output_dir.as_posix(),
        written_files=written_files,
        task_count=len(written_files),
    )


__all__ = ["populate_queue_from_plan"]

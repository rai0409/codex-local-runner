"""Project-level iterate-until-done controller (Prompt649).

A bounded, offline, deterministic controller that connects the existing project
layers into one pass:

  ProjectIntent + descriptors
    -> generate_project_task_plan (Prompt646)
    -> populate_queue_from_plan   (Prompt647, explicit output dir)
    -> evaluate_project_completion (Prompt648)
    -> decide the next step

It does NOT run the daemon or Codex by default and does NOT mutate any live/default
queue. "Iterate-until-done" is modeled deterministically: the caller may supply a
sequence of per-cycle task-result snapshots (each simulating one daemon execution
round); the controller steps through them, bounded by max_cycles, and stops as soon
as the project is complete / failed / blocked or it runs out of snapshots. It never
loops unboundedly.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from automation.orchestration.planned_runner.project_completion_gate import (
    evaluate_project_completion,
)
from automation.orchestration.planned_runner.project_queue_population import (
    populate_queue_from_plan,
)
from automation.orchestration.planned_runner.project_task_generator import (
    generate_project_task_plan,
)

# Hard upper bound on controller iterations (no infinite loops).
MAX_PROJECT_LOOP_CYCLES = 10

# next_step vocabulary
NEXT_FINISH = "finish"
NEXT_WAIT = "wait_for_execution_results"
NEXT_FIX = "fix_failures"
NEXT_MANUAL = "manual_review"


def _clamp_cycles(value: Any) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = 1
    return max(1, min(n, MAX_PROJECT_LOOP_CYCLES))


def _state(
    status: str,
    *,
    next_step: str,
    errors: list[str],
    warnings: list[str],
    plan_task_count: int = 0,
    queue_output_dir: str = "",
    written_files: list[str] | None = None,
    cycles_run: int = 0,
    per_cycle: list[dict[str, Any]] | None = None,
    final_completion: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "next_step": next_step,
        "cycles_run": cycles_run,
        "plan_task_count": plan_task_count,
        "queue_output_dir": queue_output_dir,
        "written_files": written_files or [],
        "per_cycle": per_cycle or [],
        "final_completion": final_completion or {},
        "errors": errors,
        "warnings": warnings,
    }


def run_project_loop(
    intent: Mapping[str, Any],
    task_descriptors: Sequence[Mapping[str, Any]],
    output_queue_dir: str | None,
    *,
    result_snapshots: Sequence[Mapping[str, Any]] | None = None,
    max_cycles: Any = 1,
    repo_path_override: str | None = None,
    generated_at: str = "",
) -> dict[str, Any]:
    """Run one bounded, offline project loop pass. Never raises.

    Returns a structured loop state: status (complete|in_progress|failed|blocked),
    next_step, cycles_run, plan_task_count, queue_output_dir, written_files,
    per_cycle (list of completion verdicts), final_completion, errors, warnings."""
    warnings: list[str] = []

    # Phase 1: generate the plan.
    gen = generate_project_task_plan(intent, task_descriptors, generated_at=generated_at)
    if gen["status"] != "success":
        return _state("blocked", next_step=NEXT_MANUAL, errors=list(gen["errors"]), warnings=warnings)
    plan = gen["plan"]
    warnings.extend(gen.get("warnings", []))

    # Phase 2: populate the explicit queue directory (no live/default fallback).
    pop = populate_queue_from_plan(
        plan, output_queue_dir, repo_path_override=repo_path_override
    )
    if pop["status"] != "success":
        return _state(
            "blocked",
            next_step=NEXT_MANUAL,
            errors=list(pop["errors"]),
            warnings=warnings + list(pop.get("warnings", [])),
            plan_task_count=len(plan.get("tasks", [])),
            queue_output_dir=pop.get("output_dir", ""),
        )
    warnings.extend(pop.get("warnings", []))

    # Phase 3: bounded iterate over result snapshots (each = one simulated round).
    snapshots: list[Mapping[str, Any]] = list(result_snapshots) if result_snapshots else [{}]
    bounded = min(_clamp_cycles(max_cycles), len(snapshots))
    per_cycle: list[dict[str, Any]] = []
    status = "in_progress"
    next_step = NEXT_WAIT
    final_verdict: dict[str, Any] = {}
    cycles_run = 0

    for index in range(bounded):
        results = snapshots[index] if isinstance(snapshots[index], Mapping) else {}
        verdict = evaluate_project_completion(plan, results)
        cycles_run += 1
        per_cycle.append({"cycle": index, "completion_status": verdict["status"], "counts": verdict["counts"]})
        final_verdict = verdict

        if verdict["status"] == "complete":
            status, next_step = "complete", NEXT_FINISH
            break
        if verdict["status"] == "failed":
            status, next_step = "failed", NEXT_FIX
            break
        if verdict["status"] == "blocked":
            status, next_step = "blocked", NEXT_FIX
            break
        if verdict["status"] == "invalid":
            status, next_step = "blocked", NEXT_MANUAL
            break
        # in_progress: pending/unknown -> need execution results for the next round.
        status, next_step = "in_progress", NEXT_WAIT

    return _state(
        status,
        next_step=next_step,
        errors=[],
        warnings=warnings,
        plan_task_count=len(plan.get("tasks", [])),
        queue_output_dir=pop["output_dir"],
        written_files=pop["written_files"],
        cycles_run=cycles_run,
        per_cycle=per_cycle,
        final_completion=final_verdict,
    )


__all__ = [
    "MAX_PROJECT_LOOP_CYCLES",
    "NEXT_FINISH",
    "NEXT_WAIT",
    "NEXT_FIX",
    "NEXT_MANUAL",
    "run_project_loop",
]

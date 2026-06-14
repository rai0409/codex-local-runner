"""Live auto-execution bridge (Prompt653).

Turns the proven OFFLINE project chain into a SAFE, operator-triggered, bounded,
token-gated live autonomous loop:

  intent + descriptors -> generate_project_task_plan
    -> populate_queue_from_plan (explicit queue dir)
    -> [bounded, opt-in, token-gated daemon execution via an injectable adapter]
    -> ingest REAL run_reports -> evaluate_project_completion -> next decision

Safety invariants:
- DRY-RUN by default: nothing is executed unless live is explicitly requested AND
  every enable condition is satisfied.
- The live path requires dry_run=False AND enable_live=True AND a matching enable
  token AND an explicit output queue dir AND bounded positive limits.
- The daemon runner is injectable; tests pass a FAKE adapter (no live Codex/daemon).
- Outcomes come ONLY from REAL run_reports; success is never invented from queue/plan
  files. Failures never mark the project complete. Unreliable parsing blocks safely.
- Never raises; never mutates a live/default queue.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from automation.orchestration.planned_runner.project_completion_gate import (
    evaluate_project_completion,
)
from automation.orchestration.planned_runner.project_queue_population import (
    populate_queue_from_plan,
)
from automation.orchestration.planned_runner.project_task_generator import (
    generate_project_task_plan,
)
from automation.orchestration.planned_runner.targeted_fix_retry import (
    MAX_FIX_ATTEMPTS_CAP,
)

DEFAULT_EXPECTED_ENABLE_TOKEN = "I_UNDERSTAND_THIS_RUNS_LIVE_CODEX"

# Bounds (mirror scripts/run_task_queue_daemon.py MAX_JOBS_CAP / MAX_CYCLES_CAP and
# cap the project-level cycle count). Hard upper bounds; no uncontrolled loops.
BRIDGE_MAX_DAEMON_JOBS_CAP = 5
BRIDGE_MAX_PROJECT_CYCLES_CAP = 5

# Live daemon tokens (used only by the real adapter, never in tests).
_AUTONOMOUS_ENABLE_TOKEN = "LOCAL_AUTONOMOUS_RUNTIME_ENABLE"
_LIVE_CODEX_ENABLE_TOKEN = "LOCAL_LIVE_CODEX_GATE_ENABLE"
_COMMIT_TAG_ENABLE_TOKEN = "ENABLE_SANDBOX_COMMIT_TAG_EXECUTION"

_DONE = {"success", "succeeded", "completed", "done", "passed", "ok"}
_FAILED = {"failed", "failure", "blocked", "error", "timeout"}


def _clamp(value: Any, low: int, high: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = low
    return max(low, min(n, high))


def _result(
    status: str,
    *,
    live_execution_performed: bool,
    dry_run: bool,
    errors: list[str],
    warnings: list[str],
    queue_dir: str,
    plan_result: dict,
    queue_population_result: dict,
    daemon_run_summary: dict,
    completion_gate_result: dict,
    project_complete: bool,
    next_action: str,
) -> dict[str, Any]:
    return {
        "status": status,
        "live_execution_performed": live_execution_performed,
        "dry_run": dry_run,
        "errors": errors,
        "warnings": warnings,
        "queue_dir": queue_dir,
        "plan_result": plan_result,
        "queue_population_result": queue_population_result,
        "daemon_run_summary": daemon_run_summary,
        "completion_gate_result": completion_gate_result,
        "project_complete": project_complete,
        "next_action": next_action,
    }


def _next_from_completion(verdict: Mapping[str, Any]) -> tuple[bool, str, str]:
    """Map a completion verdict -> (project_complete, status, next_action)."""
    cstatus = verdict.get("status")
    if cstatus == "complete" and verdict.get("complete"):
        return True, "success", "complete"
    if cstatus == "in_progress":
        return False, "success", "continue_project_loop"
    if cstatus in ("failed", "blocked", "invalid"):
        return False, "blocked", "manual_review_required"
    return False, "partial", "manual_review_required"


def _ingest_run_reports(runs_dir: Path) -> tuple[dict[str, str], bool, list[str]]:
    """Read REAL run_reports under runs_dir; map clean task_id -> done/failed/unknown.

    Returns (task_results, parse_ok, warnings). parse_ok is False if NO run_report
    could be read at all (unreliable outcome) so the caller can block safely."""
    warnings: list[str] = []
    results: dict[str, str] = {}
    if not runs_dir.is_dir():
        return results, False, [f"runs dir missing: {runs_dir.as_posix()}"]
    report_paths = sorted(runs_dir.glob("*/run_report.json"))
    if not report_paths:
        return results, False, ["no per-task run_report.json found"]
    read_any = False
    for path in report_paths:
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            warnings.append(f"unreadable run_report: {path.as_posix()}")
            continue
        if not isinstance(report, Mapping):
            warnings.append(f"invalid run_report (not an object): {path.as_posix()}")
            continue
        task_id = str(report.get("task_id") or "").strip()
        if not task_id:
            warnings.append(f"run_report missing task_id: {path.as_posix()}")
            continue
        read_any = True
        status = str(report.get("status") or "").strip().lower()
        if status in _DONE:
            results[task_id] = "done"
        elif status in _FAILED:
            results[task_id] = "failed"
        else:
            results[task_id] = "unknown"
            warnings.append(f"run_report '{task_id}' has unclassifiable status '{status}'")
    return results, read_any, warnings


def _default_daemon_adapter(
    *,
    queue_dir: str,
    runs_dir: str,
    work_dir: str,
    max_jobs: int,
    max_fix_attempts: int,
    cycle_index: int,
) -> dict[str, Any]:
    """Real, bounded daemon adapter (used only in the live path, never in tests).

    Lazily imports and invokes scripts/run_task_queue_daemon.main with a bounded argv
    over the EXPLICIT queue dir. Returns a small summary; outcomes are read by the
    bridge from runs_dir/<task>/run_report.json."""
    import sys

    repo_root = Path(__file__).resolve().parents[3]
    scripts_dir = (repo_root / "scripts").as_posix()
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import run_task_queue_daemon as daemon  # noqa: E402

    argv = [
        "--queue-dir", queue_dir,
        "--runs-dir", runs_dir,
        "--work-dir", work_dir,
        "--max-jobs", str(max_jobs),
        "--max-cycles", "1",
        "--max-fix-attempts", str(max_fix_attempts),
        "--sandbox-commit-tag",
        "--autonomous-enable-token", _AUTONOMOUS_ENABLE_TOKEN,
        "--live-codex-enable-token", _LIVE_CODEX_ENABLE_TOKEN,
        "--commit-tag-enable-token", _COMMIT_TAG_ENABLE_TOKEN,
    ]
    exit_code = daemon.main(argv)
    return {"adapter": "real", "cycle_index": cycle_index, "exit_code": int(exit_code), "runs_dir": runs_dir}


def run_project_live_execution_bridge(
    intent: Mapping[str, Any],
    task_descriptors: Sequence[Mapping[str, Any]],
    output_queue_dir: str | None,
    *,
    enable_live: bool = False,
    enable_token: str = "",
    expected_enable_token: str = DEFAULT_EXPECTED_ENABLE_TOKEN,
    max_project_cycles: int = 1,
    max_daemon_jobs: int = 1,
    max_fix_attempts: int = 1,
    repo_path_override: str | None = None,
    dry_run: bool = True,
    daemon_runner: Callable[..., Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run the live auto-execution bridge. Never raises. Dry-run by default."""
    warnings: list[str] = []

    # Bounds (clamped to hard caps; never uncontrolled).
    pc = _clamp(max_project_cycles, 1, BRIDGE_MAX_PROJECT_CYCLES_CAP)
    dj = _clamp(max_daemon_jobs, 1, BRIDGE_MAX_DAEMON_JOBS_CAP)
    fa = _clamp(max_fix_attempts, 0, MAX_FIX_ATTEMPTS_CAP)

    # Phase 1: plan.
    gen = generate_project_task_plan(intent, task_descriptors)
    if gen["status"] != "success":
        return _result(
            "blocked", live_execution_performed=False, dry_run=True,
            errors=[f"plan: {e}" for e in gen["errors"]], warnings=warnings,
            queue_dir="", plan_result=gen, queue_population_result={},
            daemon_run_summary={}, completion_gate_result={},
            project_complete=False, next_action="manual_review_required",
        )
    plan = gen["plan"]

    # Phase 2: explicit queue dir required; populate it.
    out_text = "" if output_queue_dir is None else str(output_queue_dir).strip()
    if not out_text:
        return _result(
            "blocked", live_execution_performed=False, dry_run=True,
            errors=["output_queue_dir is required (no live/default queue fallback)"],
            warnings=warnings, queue_dir="", plan_result=gen,
            queue_population_result={}, daemon_run_summary={}, completion_gate_result={},
            project_complete=False, next_action="manual_review_required",
        )
    pop = populate_queue_from_plan(plan, out_text, repo_path_override=repo_path_override)
    if pop["status"] != "success":
        return _result(
            "blocked", live_execution_performed=False, dry_run=True,
            errors=[f"queue population: {e}" for e in pop["errors"]],
            warnings=warnings + list(pop.get("warnings", [])), queue_dir=out_text,
            plan_result=gen, queue_population_result=pop, daemon_run_summary={},
            completion_gate_result={}, project_complete=False,
            next_action="manual_review_required",
        )
    warnings.extend(pop.get("warnings", []))
    queue_dir = pop["output_dir"]

    requested_live = (dry_run is False) and bool(enable_live)

    # Phase 3a: DRY-RUN (default, or whenever live was not requested).
    if not requested_live:
        reason = "dry_run=True (default)" if dry_run else "enable_live=False"
        warnings.append(f"dry-run: live execution NOT requested ({reason}); daemon was not run")
        summary = {
            "would_run": True, "executed": False,
            "max_project_cycles": pc, "max_daemon_jobs": dj, "max_fix_attempts": fa,
            "queue_dir": queue_dir, "pending_count": pop["task_count"],
        }
        return _result(
            "success", live_execution_performed=False, dry_run=True,
            errors=[], warnings=warnings, queue_dir=queue_dir,
            plan_result=gen, queue_population_result=pop, daemon_run_summary=summary,
            completion_gate_result={}, project_complete=False,
            next_action="continue_project_loop",
        )

    # Phase 3b: LIVE requested -> enforce the token gate (dir already validated; bounds clamped).
    if enable_token != expected_enable_token:
        return _result(
            "blocked", live_execution_performed=False, dry_run=False,
            errors=["enable_token does not match expected_enable_token; live execution refused"],
            warnings=warnings, queue_dir=queue_dir, plan_result=gen,
            queue_population_result=pop, daemon_run_summary={}, completion_gate_result={},
            project_complete=False, next_action="manual_review_required",
        )

    # Phase 4: bounded live execution via the (injectable) adapter.
    adapter = daemon_runner or _default_daemon_adapter
    base = Path(queue_dir).parent
    runs_dir = base / "runs"
    work_dir = base / "work"
    runs_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    task_results: dict[str, str] = {}
    cycle_summaries: list[dict[str, Any]] = []
    final_verdict: dict[str, Any] = {}
    parse_ok_overall = False

    for cycle_index in range(pc):
        try:
            summary = adapter(
                queue_dir=queue_dir, runs_dir=runs_dir.as_posix(), work_dir=work_dir.as_posix(),
                max_jobs=dj, max_fix_attempts=fa, cycle_index=cycle_index,
            )
        except Exception as exc:  # adapter failure must not crash the bridge
            return _result(
                "blocked", live_execution_performed=True, dry_run=False,
                errors=[f"daemon adapter raised: {exc!r}"], warnings=warnings,
                queue_dir=queue_dir, plan_result=gen, queue_population_result=pop,
                daemon_run_summary={"cycles": cycle_summaries}, completion_gate_result=final_verdict,
                project_complete=False, next_action="manual_review_required",
            )
        cycle_summaries.append(dict(summary) if isinstance(summary, Mapping) else {"adapter_summary": str(summary)})

        ingested, parse_ok, ingest_warnings = _ingest_run_reports(runs_dir)
        warnings.extend(ingest_warnings)
        parse_ok_overall = parse_ok_overall or parse_ok
        task_results.update(ingested)

        if not parse_ok:
            # No reliable outcome this cycle -> block safely.
            return _result(
                "partial", live_execution_performed=True, dry_run=False,
                errors=["daemon outcome parsing unreliable: no readable run_report"],
                warnings=warnings, queue_dir=queue_dir, plan_result=gen,
                queue_population_result=pop,
                daemon_run_summary={"cycles": cycle_summaries, "task_results": task_results},
                completion_gate_result={}, project_complete=False,
                next_action="manual_review_required",
            )

        final_verdict = evaluate_project_completion(plan, task_results)
        if final_verdict["status"] in ("complete", "failed", "blocked", "invalid"):
            break  # terminal verdict; stop iterating

    project_complete, status, next_action = _next_from_completion(final_verdict)
    return _result(
        status, live_execution_performed=True, dry_run=False,
        errors=[], warnings=warnings, queue_dir=queue_dir,
        plan_result=gen, queue_population_result=pop,
        daemon_run_summary={"cycles": cycle_summaries, "task_results": task_results},
        completion_gate_result=final_verdict, project_complete=project_complete,
        next_action=next_action,
    )


__all__ = [
    "DEFAULT_EXPECTED_ENABLE_TOKEN",
    "BRIDGE_MAX_DAEMON_JOBS_CAP",
    "BRIDGE_MAX_PROJECT_CYCLES_CAP",
    "run_project_live_execution_bridge",
]

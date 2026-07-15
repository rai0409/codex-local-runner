#!/usr/bin/env python3
"""Project-level LIVE E2E acceptance harness (Prompt654).

Operator-triggered, dry-run-by-default, token-gated, bounded harness that drives the
full project-level chain through the Prompt653 live bridge in a /tmp clone:

  ProjectIntent + descriptors -> ProjectTaskPlan -> explicit /tmp queue dir
    -> live bridge -> bounded daemon/Codex execution -> REAL run_report ingestion
    -> completion gate -> project final status

Safety:
- work_root AND queue_dir MUST be under /tmp; the main/source repo is only READ (cloned),
  never mutated by the live run.
- Live execution requires --enable-live AND the exact enable token; otherwise dry-run.
- Outcomes come ONLY from the bridge's real run_report ingestion; failures never mark the
  project complete. Never raises.
- The core function accepts injectable `bridge_runner` / `cloner` / `head_reader` so tests
  exercise gating and outcome handling WITHOUT running live Codex/daemon.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
if REPO_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, REPO_ROOT.as_posix())

from automation.orchestration.planned_runner.project_live_execution_bridge import (  # noqa: E402
    DEFAULT_EXPECTED_ENABLE_TOKEN,
    run_project_live_execution_bridge,
)

# Harness-level hard caps for a single bounded live acceptance.
ACCEPTANCE_MAX_PROJECT_CYCLES = 1
ACCEPTANCE_MAX_DAEMON_JOBS = 1
ACCEPTANCE_MAX_FIX_ATTEMPTS = 1

# Harmless, existing, deterministic target inside any clone of this repo.
_TARGET_FILE = "automation/orchestration/planned_runner/sandbox_cleanup.py"

_REPORT_FIELDS = (
    "prompt654_status", "live_acceptance_status", "live_execution_performed",
    "dry_run", "tmp_clone_or_sandbox_used", "explicit_tmp_queue_used",
    "bounded_live_execution_used", "real_daemon_execution_attempted",
    "real_run_report_ingested", "completion_gate_evaluated_real_outcomes",
    "failure_never_marked_complete", "main_repo_head_unchanged_during_live_run",
    "project_complete", "next_action", "errors", "warnings",
)


def _clamp(value: Any, low: int, high: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        n = low
    return max(low, min(n, high))


def _under_tmp(path: str) -> bool:
    try:
        resolved = Path(path).resolve().as_posix()
    except Exception:
        return False
    return resolved == "/tmp" or resolved.startswith("/tmp/")


def _real_cloner(src: str, dest: str) -> str:
    subprocess.run(
        ["git", "clone", "-q", "--no-hardlinks", src, dest],
        check=True, capture_output=True,
    )
    return dest


def _real_head_reader(repo: str) -> str:
    out = subprocess.run(
        ["git", "-C", repo, "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    )
    return out.stdout.strip()


def _build_intent_and_descriptors(clone_path: str) -> tuple[dict, list[dict]]:
    intent = {
        "project_id": "prompt654-live-e2e",
        "project_name": "Prompt654 live E2E acceptance",
        "goal": "Add a single harmless deterministic helper function to a sandbox clone",
        "repo_target": clone_path,
        "allowed_task_kinds": ["add_function"],
        "safety_limits": {"max_tasks": 1, "max_cycles_per_task": 1, "max_total_seconds": 600},
        "source": "manual",
    }
    descriptors = [
        {
            "target_file": _TARGET_FILE,
            "function_name": "prompt654_live_marker",
            "expression": "a + b",
            "verify_commands": [["python", "-m", "py_compile", _TARGET_FILE]],
        }
    ]
    return intent, descriptors


def run_live_e2e_acceptance(
    *,
    repo: str,
    work_root: str,
    queue_dir: str,
    enable_live: bool = False,
    enable_token: str = "",
    expected_enable_token: str = DEFAULT_EXPECTED_ENABLE_TOKEN,
    max_project_cycles: int = ACCEPTANCE_MAX_PROJECT_CYCLES,
    max_daemon_jobs: int = ACCEPTANCE_MAX_DAEMON_JOBS,
    max_fix_attempts: int = ACCEPTANCE_MAX_FIX_ATTEMPTS,
    dry_run: bool = True,
    bridge_runner: Callable[..., dict] | None = None,
    cloner: Callable[[str, str], str] | None = None,
    head_reader: Callable[[str], str] | None = None,
) -> dict[str, Any]:
    """Run a bounded project-level live E2E acceptance. Never raises."""
    errors: list[str] = []
    warnings: list[str] = []
    bridge_runner = bridge_runner or run_project_live_execution_bridge
    cloner = cloner or _real_cloner
    head_reader = head_reader or _real_head_reader

    def _blocked(reason: str, **extra: Any) -> dict[str, Any]:
        base = {
            "prompt654_status": "blocked",
            "live_acceptance_status": "blocked",
            "live_execution_performed": False,
            "dry_run": bool(dry_run),
            "tmp_clone_or_sandbox_used": False,
            "explicit_tmp_queue_used": _under_tmp(queue_dir or ""),
            "bounded_live_execution_used": False,
            "real_daemon_execution_attempted": False,
            "real_run_report_ingested": False,
            "completion_gate_evaluated_real_outcomes": False,
            "failure_never_marked_complete": True,
            "main_repo_head_unchanged_during_live_run": True,
            "project_complete": False,
            "next_action": "manual_review_required",
            "errors": errors + [reason],
            "warnings": warnings,
            "bridge_result": {},
        }
        base.update(extra)
        return base

    # Safety validation: explicit /tmp work_root + queue_dir; existing source repo.
    if not work_root or not _under_tmp(work_root):
        return _blocked("work_root must be an explicit path under /tmp")
    if not queue_dir or not _under_tmp(queue_dir):
        return _blocked("queue_dir must be an explicit path under /tmp")
    if not repo or not Path(repo).is_dir():
        return _blocked(f"source repo is not a directory: {repo}")

    pc = _clamp(max_project_cycles, 1, ACCEPTANCE_MAX_PROJECT_CYCLES)
    dj = _clamp(max_daemon_jobs, 1, ACCEPTANCE_MAX_DAEMON_JOBS)
    fa = _clamp(max_fix_attempts, 0, ACCEPTANCE_MAX_FIX_ATTEMPTS)

    # Capture source/main repo HEAD before anything.
    try:
        head_before = head_reader(repo)
    except Exception as exc:
        return _blocked(f"could not read source repo HEAD: {exc!r}")

    # Clone the source repo into work_root/clone (READ-only w.r.t. the source).
    clone_path = (Path(work_root) / "clone").as_posix()
    try:
        cloner(repo, clone_path)
    except Exception as exc:
        return _blocked(f"clone failed: {exc!r}")
    clone_ok = Path(clone_path).is_dir()

    intent, descriptors = _build_intent_and_descriptors(clone_path)

    # Drive the live bridge (dry-run by default; live only when fully gated).
    bridge = bridge_runner(
        intent, descriptors, queue_dir,
        enable_live=enable_live, enable_token=enable_token,
        expected_enable_token=expected_enable_token,
        max_project_cycles=pc, max_daemon_jobs=dj, max_fix_attempts=fa,
        dry_run=dry_run,
    )
    if not isinstance(bridge, dict):
        return _blocked("bridge_runner returned a non-dict result")
    warnings.extend(bridge.get("warnings", []))

    # Capture HEAD after; the live run must not mutate the source/main repo.
    try:
        head_after = head_reader(repo)
    except Exception as exc:
        head_after = head_before
        warnings.append(f"could not re-read source repo HEAD: {exc!r}")
    main_repo_head_unchanged = head_before == head_after

    live_performed = bool(bridge.get("live_execution_performed"))
    daemon_summary = bridge.get("daemon_run_summary", {}) or {}
    task_results = daemon_summary.get("task_results", {}) if isinstance(daemon_summary, dict) else {}
    completion = bridge.get("completion_gate_result", {}) or {}
    project_complete = bool(bridge.get("project_complete"))

    real_run_report_ingested = bool(live_performed and task_results)
    completion_real = bool(live_performed and completion)
    # Failures must never mark complete.
    completion_status = completion.get("status") if isinstance(completion, dict) else None
    failure_never_marked_complete = not (completion_status in ("failed", "blocked", "invalid") and project_complete)

    # Derive acceptance status.
    if not live_performed:
        live_acceptance_status = "dry_run"
        prompt654_status = "success" if bridge.get("status") == "success" else "blocked"
    else:
        bstatus = bridge.get("status")
        if project_complete:
            live_acceptance_status = "success"
            prompt654_status = "success"
        elif bstatus == "partial":
            live_acceptance_status = "partial"
            prompt654_status = "partial"
        elif bstatus == "blocked":
            live_acceptance_status = "blocked"
            prompt654_status = "blocked"
        else:
            live_acceptance_status = "failed"
            prompt654_status = "partial"

    if not main_repo_head_unchanged:
        errors.append("MAIN REPO HEAD CHANGED DURING LIVE RUN")
        prompt654_status = "blocked"
        live_acceptance_status = "blocked"

    return {
        "prompt654_status": prompt654_status,
        "live_acceptance_status": live_acceptance_status,
        "live_execution_performed": live_performed,
        "dry_run": bool(dry_run) or not live_performed,
        "tmp_clone_or_sandbox_used": clone_ok and _under_tmp(clone_path),
        "explicit_tmp_queue_used": _under_tmp(queue_dir),
        "bounded_live_execution_used": True,
        "bounds": {"max_project_cycles": pc, "max_daemon_jobs": dj, "max_fix_attempts": fa},
        "real_daemon_execution_attempted": live_performed,
        "real_run_report_ingested": real_run_report_ingested,
        "completion_gate_evaluated_real_outcomes": completion_real,
        "failure_never_marked_complete": failure_never_marked_complete,
        "main_repo_head_unchanged_during_live_run": main_repo_head_unchanged,
        "main_repo_head_before": head_before,
        "main_repo_head_after": head_after,
        "project_complete": project_complete,
        "queue_dir": bridge.get("queue_dir", queue_dir),
        "next_action": bridge.get("next_action", "manual_review_required"),
        "errors": errors,
        "warnings": warnings,
        "bridge_result": bridge,
    }


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Project-level live E2E acceptance (Prompt654)")
    p.add_argument("--repo", required=True)
    p.add_argument("--work-root", required=True)
    p.add_argument("--queue-dir", required=True)
    p.add_argument("--enable-live", action="store_true", default=False)
    p.add_argument("--enable-token", default="")
    p.add_argument("--expected-enable-token", default=DEFAULT_EXPECTED_ENABLE_TOKEN)
    p.add_argument("--max-project-cycles", type=int, default=ACCEPTANCE_MAX_PROJECT_CYCLES)
    p.add_argument("--max-daemon-jobs", type=int, default=ACCEPTANCE_MAX_DAEMON_JOBS)
    p.add_argument("--max-fix-attempts", type=int, default=ACCEPTANCE_MAX_FIX_ATTEMPTS)
    p.add_argument("--dry-run", action="store_true", default=False)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    # --enable-live implies live intent (dry_run False) unless --dry-run is explicit.
    dry_run = True if args.dry_run else (not args.enable_live)
    result = run_live_e2e_acceptance(
        repo=args.repo,
        work_root=args.work_root,
        queue_dir=args.queue_dir,
        enable_live=args.enable_live,
        enable_token=args.enable_token,
        expected_enable_token=args.expected_enable_token,
        max_project_cycles=args.max_project_cycles,
        max_daemon_jobs=args.max_daemon_jobs,
        max_fix_attempts=args.max_fix_attempts,
        dry_run=dry_run,
    )
    printable = {k: result[k] for k in _REPORT_FIELDS if k in result}
    print(json.dumps(printable, ensure_ascii=False, sort_keys=True))
    return 0 if result["prompt654_status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())

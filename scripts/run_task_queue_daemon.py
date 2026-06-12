#!/usr/bin/env python3
"""Bounded foreground task-queue daemon candidate (local-only).

Consumes task spec JSON files from <queue-dir>/pending, plans each one into
prompt/effect-spec/manifest, runs the autonomous live loop (effect-verified,
workspace-write), optionally performs a sandbox-only gated commit/tag, and
records a persistent run report and JSONL log per run.

This is NOT a production daemon: it is a bounded foreground supervisor with a
pidfile lock and crash-recovery for interrupted tasks. It never pushes, never
opens PRs, never merges, and can only commit/tag inside /tmp sandbox repos.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, REPO_ROOT.as_posix())

from automation.orchestration.planned_runner.autonomous_live_loop import (  # noqa: E402
    run_autonomous_live_loop,
)
from automation.orchestration.planned_runner.commit_tag import (  # noqa: E402
    SANDBOX_COMMIT_TAG_ENABLE_TOKEN,
    execute_sandbox_commit_tag,
)
from automation.orchestration.planned_runner.daemon_lock import (  # noqa: E402
    acquire_lock,
    release_lock,
)
from automation.orchestration.planned_runner.daemon_logs import append_log  # noqa: E402
from automation.orchestration.planned_runner.daemon_queue import (  # noqa: E402
    claim_next_task,
    complete_task,
    ensure_queue_dirs,
    list_tasks,
)
from automation.orchestration.planned_runner.daemon_state import (  # noqa: E402
    recover_interrupted_tasks,
    write_daemon_state,
)
from automation.orchestration.planned_runner.sandbox_cleanup import (  # noqa: E402
    cleanup_generated_python_artifacts,
    evaluate_sandbox_cleanliness,
)
from automation.orchestration.planned_runner.task_planner import plan_task  # noqa: E402
from automation.orchestration.planned_runner.task_spec import validate_task_spec  # noqa: E402

MAX_JOBS_CAP = 5
MAX_SECONDS_TOTAL_CAP = 1800
MAX_CYCLES_CAP = 2


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _ensure_dirty_gate_repo(work_dir: Path) -> Path:
    import subprocess

    repo = work_dir / "dirty_gate_repo"
    if not (repo / ".git").exists():
        repo.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            [
                "git", "-c", "user.email=daemon@local", "-c", "user.name=daemon",
                "commit", "-q", "--allow-empty", "-m", "clean dirty-gate repo",
            ],
            cwd=repo,
            check=True,
            capture_output=True,
        )
    return repo


def _process_task(
    *,
    task_path: Path,
    runs_dir: Path,
    work_dir: Path,
    args: argparse.Namespace,
    log_path: Path,
) -> dict:
    task_name = task_path.stem
    run_dir = runs_dir / task_name
    run_dir.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "task_file": task_path.name,
        "task_id": task_name,
        "status": "blocked",
        "stage": "load_spec",
        "started_at": _utc_now(),
        "codex_invoked_count": 0,
        "sandbox_commit_performed": False,
        "sandbox_tag_performed": False,
        "sandbox_generated_artifacts_removed": 0,
        "sandbox_generated_artifact_paths_removed": [],
        "sandbox_final_status_clean": False,
        "sandbox_final_status_short": [],
        "sandbox_untracked_after_cleanup": [],
    }
    try:
        raw_spec = json.loads(task_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        report["errors"] = [f"task spec unreadable: {exc}"]
        return report

    spec, errors = validate_task_spec(raw_spec)
    if errors:
        report["errors"] = errors
        return report
    report["task_id"] = spec["task_id"]

    report["stage"] = "plan"
    plan = plan_task(spec, run_dir / "plan")
    report["plan"] = {k: plan.get(k) for k in ("status", "manifest_path", "generated_prompt_path", "effect_spec_path")}
    if plan.get("status") != "success":
        report["errors"] = plan.get("errors", ["planning failed"])
        return report

    report["stage"] = "execute"
    dirty_gate_repo = _ensure_dirty_gate_repo(work_dir)
    loop_state = run_autonomous_live_loop(
        repo_path=dirty_gate_repo,
        out_dir=run_dir / "loop",
        generated_prompt_path=None,
        max_cycles=args.max_cycles,
        max_seconds=min(args.max_seconds_total, 300),
        autonomous_enable_token=args.autonomous_enable_token,
        live_codex_enable_token=args.live_codex_enable_token,
        live_loop_timeout_seconds=args.live_timeout_seconds,
        sandbox_mode="workspace-write",
        generated_prompt_manifest_path=plan["manifest_path"],
    )
    report["loop_state_path"] = (run_dir / "loop" / "autonomous_live_loop_state.json").as_posix()
    report["codex_invoked_count"] = int(loop_state.get("codex_invoked_count", 0) or 0)
    report["loop_status"] = loop_state.get("status")
    report["per_cycle_effect_verification_statuses"] = list(
        loop_state.get("per_cycle_effect_verification_statuses", [])
    )
    report["failure_digest_path"] = str(loop_state.get("failure_digest_path") or "")
    if loop_state.get("status") != "success":
        report["errors"] = [f"loop status {loop_state.get('status')}: {loop_state.get('stop_reason')}"]
        return report

    # Verify commands may have generated Python bytecode inside the sandbox repo;
    # remove it BEFORE the commit/tag gate and the final cleanliness evaluation.
    report["stage"] = "sandbox_cleanup"
    cleanup = cleanup_generated_python_artifacts(spec["repo_path"])
    report["sandbox_generated_artifacts_removed"] = cleanup["removed_count"]
    report["sandbox_generated_artifact_paths_removed"] = cleanup["removed_paths"]
    if cleanup["status"] != "success":
        report["errors"] = [f"sandbox cleanup blocked: {cleanup['blocked_reason']}"]
        return report

    if args.sandbox_commit_tag:
        report["stage"] = "sandbox_commit_tag"
        commit_result = execute_sandbox_commit_tag(
            repo_path=spec["repo_path"],
            allowed_files=[spec["target_file"]],
            artifact_dir=run_dir / "sandbox_commit_tag",
            task_id=spec["task_id"],
            enabled=True,
            explicit_enable_token=args.commit_tag_enable_token,
        )
        report["sandbox_commit_tag"] = {
            k: commit_result.get(k)
            for k in ("status", "blocked_reason", "commit_sha", "tag_name", "commit_performed", "tag_performed")
        }
        report["sandbox_commit_performed"] = bool(commit_result.get("commit_performed"))
        report["sandbox_tag_performed"] = bool(commit_result.get("tag_performed"))
        if commit_result.get("status") != "success":
            report["errors"] = [f"sandbox commit/tag blocked: {commit_result.get('blocked_reason')}"]
            return report

    report["stage"] = "final_clean_check"
    cleanliness = evaluate_sandbox_cleanliness(spec["repo_path"])
    report.update(cleanliness)
    if args.sandbox_commit_tag and not cleanliness["sandbox_final_status_clean"]:
        report["errors"] = [
            f"sandbox repo not clean after commit/tag: {cleanliness['sandbox_final_status_short']}"
        ]
        return report

    report["stage"] = "done"
    report["status"] = "success"
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bounded local task-queue daemon candidate")
    parser.add_argument("--queue-dir", required=True)
    parser.add_argument("--runs-dir", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--max-jobs", type=int, default=1)
    parser.add_argument("--max-seconds-total", type=int, default=600)
    parser.add_argument("--max-cycles", type=int, default=1)
    parser.add_argument("--live-timeout-seconds", type=int, default=90)
    parser.add_argument("--autonomous-enable-token", default="")
    parser.add_argument("--live-codex-enable-token", default="")
    parser.add_argument("--sandbox-commit-tag", action="store_true", default=False)
    parser.add_argument("--commit-tag-enable-token", default="")
    parser.add_argument("--recover-only", action="store_true", default=False)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    if args.max_jobs < 1 or args.max_seconds_total < 1 or args.max_cycles < 1:
        print("error: bounds must be positive", file=sys.stderr)
        return 2
    args.max_jobs = min(args.max_jobs, MAX_JOBS_CAP)
    args.max_seconds_total = min(args.max_seconds_total, MAX_SECONDS_TOTAL_CAP)
    args.max_cycles = min(args.max_cycles, MAX_CYCLES_CAP)

    queue_dir = Path(args.queue_dir)
    runs_dir = Path(args.runs_dir)
    work_dir = Path(args.work_dir)
    for path in (queue_dir, runs_dir, work_dir):
        path.mkdir(parents=True, exist_ok=True)
    ensure_queue_dirs(queue_dir)
    log_path = runs_dir / "daemon_log.jsonl"
    state_path = runs_dir / "daemon_state.json"
    lock_path = queue_dir / "daemon.lock"

    lock = acquire_lock(lock_path)
    if not lock["acquired"]:
        append_log(log_path, "lock_refused", {"existing_pid": lock["existing_pid"]})
        print(f"error: lock held by pid {lock['existing_pid']}", file=sys.stderr)
        return 1
    append_log(log_path, "daemon_started", {"pid": os.getpid(), "stale_lock_recovered": lock["stale_recovered"]})

    recovery = recover_interrupted_tasks(queue_dir)
    if recovery["recovered_count"] or recovery["exhausted_count"]:
        append_log(log_path, "recovery", recovery)

    exit_code = 0
    jobs: list[dict] = []
    started = time.monotonic()
    try:
        write_daemon_state(
            state_path,
            {"status": "running", "pid": os.getpid(), "recovery": recovery, "current_task": ""},
        )
        if not args.recover_only:
            while len(jobs) < args.max_jobs:
                if time.monotonic() - started >= args.max_seconds_total:
                    append_log(log_path, "budget_exhausted", {"elapsed": time.monotonic() - started})
                    break
                task_path = claim_next_task(queue_dir)
                if task_path is None:
                    break
                append_log(log_path, "task_claimed", {"task": task_path.name})
                write_daemon_state(
                    state_path,
                    {"status": "running", "pid": os.getpid(), "current_task": task_path.name},
                )
                run_report = _process_task(
                    task_path=task_path,
                    runs_dir=runs_dir,
                    work_dir=work_dir,
                    args=args,
                    log_path=log_path,
                )
                run_report["finished_at"] = _utc_now()
                success = run_report["status"] == "success"
                final_path = complete_task(queue_dir, task_path, success=success)
                run_report["queue_final_path"] = final_path.as_posix()
                _write_json(runs_dir / run_report["task_id"] / "run_report.json", run_report)
                append_log(
                    log_path,
                    "task_finished",
                    {"task": task_path.name, "status": run_report["status"], "stage": run_report["stage"]},
                )
                jobs.append(run_report)
                if not success:
                    exit_code = 1
    finally:
        daemon_report = {
            "status": "success" if exit_code == 0 else "blocked",
            "recover_only": bool(args.recover_only),
            "jobs_processed": len(jobs),
            "jobs": [
                {k: job.get(k) for k in ("task_id", "status", "stage", "codex_invoked_count",
                                          "sandbox_commit_performed", "sandbox_tag_performed")}
                for job in jobs
            ],
            "recovery": recovery,
            "queue": list_tasks(queue_dir),
            "bounds": {
                "max_jobs": args.max_jobs,
                "max_seconds_total": args.max_seconds_total,
                "max_cycles": args.max_cycles,
            },
            "elapsed_seconds": time.monotonic() - started,
            "lock_path": lock_path.as_posix(),
            "log_path": log_path.as_posix(),
            "state_path": state_path.as_posix(),
            "local_only": True,
            "remote_operations": False,
            "generated_at": _utc_now(),
        }
        _write_json(runs_dir / "daemon_run_report.json", daemon_report)
        write_daemon_state(
            state_path,
            {"status": "stopped", "pid": os.getpid(), "jobs_processed": len(jobs), "current_task": ""},
        )
        append_log(log_path, "daemon_stopped", {"jobs_processed": len(jobs), "exit_code": exit_code})
        release_lock(lock_path)

    if args.as_json:
        print(json.dumps(daemon_report, ensure_ascii=False, sort_keys=True))
    else:
        print(f"daemon_status={daemon_report['status']}")
        print(f"jobs_processed={daemon_report['jobs_processed']}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

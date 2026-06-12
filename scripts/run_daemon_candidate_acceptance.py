#!/usr/bin/env python3
"""End-to-end acceptance for the local bounded task-queue daemon candidate.

Creates a fresh work dir with a sandbox calculator repo, enqueues one
add_function task spec, runs the bounded queue daemon (live Codex, effect +
test-command verification, optional sandbox-only commit/tag), and validates
the full chain: queue transitions, real sandbox change, verification, sandbox
commit/tag, lock/log/state persistence, and main-repo non-mutation.

Exit codes: 0 success, 1 blocked, 2 bad usage.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, REPO_ROOT.as_posix())

from automation.orchestration.planned_runner.daemon_queue import enqueue_task, list_tasks  # noqa: E402

AUTONOMOUS_ENABLE_TOKEN = "LOCAL_AUTONOMOUS_RUNTIME_ENABLE"
LIVE_CODEX_ENABLE_TOKEN = "LOCAL_LIVE_CODEX_GATE_ENABLE"
SANDBOX_COMMIT_TAG_TOKEN = "ENABLE_SANDBOX_COMMIT_TAG_EXECUTION"

CALCULATOR_SOURCE = "def add(a, b):\n    return a + b\n"
TEST_SOURCE = "from calculator import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _git(args: list[str], cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


def _main_repo_status() -> list[str]:
    return [line for line in _git(["status", "--short"], cwd=REPO_ROOT).splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Daemon candidate end-to-end acceptance")
    parser.add_argument("--work-dir", default="/tmp/codex-local-runner-daemon-acceptance")
    parser.add_argument("--max-seconds-total", type=int, default=300)
    parser.add_argument("--live-timeout-seconds", type=int, default=90)
    parser.add_argument("--skip-sandbox-commit-tag", action="store_true", default=False)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    work_dir = Path(args.work_dir).resolve()
    if work_dir == REPO_ROOT or REPO_ROOT in work_dir.parents:
        print("error: work dir must be outside the main repo", file=sys.stderr)
        return 2
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)
    queue_dir = work_dir / "queue"
    runs_dir = work_dir / "runs"
    daemon_work_dir = work_dir / "daemon_work"

    status_before = _main_repo_status()
    head_before = _git(["rev-parse", "HEAD"], cwd=REPO_ROOT).strip()

    sandbox_repo = work_dir / "sandbox_repo"
    sandbox_repo.mkdir()
    (sandbox_repo / "calculator.py").write_text(CALCULATOR_SOURCE, encoding="utf-8")
    (sandbox_repo / "test_calculator.py").write_text(TEST_SOURCE, encoding="utf-8")
    _git(["init", "-q"], cwd=sandbox_repo)
    _git(["add", "."], cwd=sandbox_repo)
    _git(
        ["-c", "user.email=acceptance@local", "-c", "user.name=acceptance", "commit", "-q", "-m", "fixture"],
        cwd=sandbox_repo,
    )

    task_id = "daemon-acceptance-subtract"
    enqueue_task(
        queue_dir,
        {
            "task_id": task_id,
            "kind": "add_function",
            "repo_path": sandbox_repo.as_posix(),
            "target_file": "calculator.py",
            "function_name": "subtract",
            "expression": "a - b",
            "description": "daemon candidate acceptance task",
            "expected_unmodified_files": ["test_calculator.py"],
            "verify_commands": [
                ["python", "-c", "from calculator import add, subtract; assert add(2,3)==5; assert subtract(7,4)==3"]
            ],
        },
    )

    daemon_cmd = [
        sys.executable,
        (REPO_ROOT / "scripts" / "run_task_queue_daemon.py").as_posix(),
        "--queue-dir", queue_dir.as_posix(),
        "--runs-dir", runs_dir.as_posix(),
        "--work-dir", daemon_work_dir.as_posix(),
        "--max-jobs", "1",
        "--max-seconds-total", str(args.max_seconds_total),
        "--max-cycles", "1",
        "--live-timeout-seconds", str(args.live_timeout_seconds),
        "--autonomous-enable-token", AUTONOMOUS_ENABLE_TOKEN,
        "--live-codex-enable-token", LIVE_CODEX_ENABLE_TOKEN,
        "--json",
    ]
    if not args.skip_sandbox_commit_tag:
        daemon_cmd += ["--sandbox-commit-tag", "--commit-tag-enable-token", SANDBOX_COMMIT_TAG_TOKEN]
    completed = subprocess.run(daemon_cmd, capture_output=True, text=True)
    (work_dir / "daemon_stdout.txt").write_text(completed.stdout or "", encoding="utf-8")
    (work_dir / "daemon_stderr.txt").write_text(completed.stderr or "", encoding="utf-8")

    failures: list[str] = []
    if completed.returncode != 0:
        failures.append(f"daemon returncode {completed.returncode}")

    run_report_path = runs_dir / task_id / "run_report.json"
    run_report: dict = {}
    if run_report_path.is_file():
        run_report = json.loads(run_report_path.read_text(encoding="utf-8"))
    else:
        failures.append("run_report.json missing")

    queue_state = list_tasks(queue_dir)
    if queue_state["done"] != [f"{task_id}.json"]:
        failures.append(f"task not in done/: {queue_state}")

    calculator_text = (sandbox_repo / "calculator.py").read_text(encoding="utf-8")
    if "def subtract(a, b):" not in calculator_text:
        failures.append("subtract missing in sandbox repo")
    if (sandbox_repo / "test_calculator.py").read_text(encoding="utf-8") != TEST_SOURCE:
        failures.append("test_calculator.py changed")

    effect_statuses = run_report.get("per_cycle_effect_verification_statuses", [])
    if effect_statuses != ["passed"]:
        failures.append(f"effect verification not passed: {effect_statuses}")
    if run_report.get("status") != "success":
        failures.append(f"run report status: {run_report.get('status')} (stage {run_report.get('stage')})")
        digest_path = run_report.get("failure_digest_path") or ""
        if digest_path and Path(digest_path).is_file():
            failures.append(f"failure digest available: {digest_path}")

    sandbox_commit_performed = bool(run_report.get("sandbox_commit_performed"))
    sandbox_tag_performed = bool(run_report.get("sandbox_tag_performed"))
    sandbox_tags = _git(["tag"], cwd=sandbox_repo).split()
    sandbox_commits = len(_git(["log", "--oneline"], cwd=sandbox_repo).splitlines())
    if not args.skip_sandbox_commit_tag:
        if not (sandbox_commit_performed and sandbox_tag_performed):
            failures.append("sandbox commit/tag not performed")
        if sandbox_tags != [f"sandbox-{task_id}"]:
            failures.append(f"unexpected sandbox tags: {sandbox_tags}")
        if sandbox_commits != 2:
            failures.append(f"unexpected sandbox commit count: {sandbox_commits}")

    if (queue_dir / "daemon.lock").exists():
        failures.append("daemon lock not released")
    if not (runs_dir / "daemon_log.jsonl").is_file():
        failures.append("daemon log missing")
    if not (runs_dir / "daemon_run_report.json").is_file():
        failures.append("daemon run report missing")
    if not (runs_dir / "daemon_state.json").is_file():
        failures.append("daemon state missing")

    status_after = _main_repo_status()
    head_after = _git(["rev-parse", "HEAD"], cwd=REPO_ROOT).strip()
    main_repo_modified = sorted(status_before) != sorted(status_after) or head_before != head_after
    if main_repo_modified:
        failures.append("main repo modified during runtime")

    report = {
        "acceptance_status": "success" if not failures else "blocked",
        "failures": failures,
        "task_id": task_id,
        "daemon_returncode": completed.returncode,
        "queue_state": queue_state,
        "run_report_path": run_report_path.as_posix(),
        "codex_invoked_count": run_report.get("codex_invoked_count"),
        "effect_verification_statuses": effect_statuses,
        "verify_commands_used": True,
        "sandbox_commit_performed": sandbox_commit_performed,
        "sandbox_tag_performed": sandbox_tag_performed,
        "sandbox_tags": sandbox_tags,
        "sandbox_repo": sandbox_repo.as_posix(),
        "lock_released": not (queue_dir / "daemon.lock").exists(),
        "log_path": (runs_dir / "daemon_log.jsonl").as_posix(),
        "daemon_report_path": (runs_dir / "daemon_run_report.json").as_posix(),
        "main_repo_source_modified": main_repo_modified,
        "generated_at": _utc_now(),
    }
    report_path = work_dir / "daemon_candidate_acceptance_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(f"acceptance_status={report['acceptance_status']}")
        print(f"report_path={report_path.as_posix()}")
    return 0 if report["acceptance_status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())

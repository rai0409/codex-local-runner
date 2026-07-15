#!/usr/bin/env python3
"""Reproducible acceptance fixture for the integrated two-cycle live loop proof.

Recreates the Prompt625 proof from scratch: two clean sandbox repos under a
/tmp work dir, per-cycle prompts and effect specs, a manifest, then one bounded
run of the autonomous live loop with verification-only continuation and
workspace-write sandboxing. Validates real effects in both sandbox repos and
that the runtime mutated neither git history nor the main repo, and emits a
machine-readable acceptance report.

The runtime never commits, tags, stages, pushes, opens PRs, or merges.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_SCRIPT = REPO_ROOT / "scripts" / "run_planned_execution.py"

AUTONOMOUS_ENABLE_TOKEN = "LOCAL_AUTONOMOUS_RUNTIME_ENABLE"
LIVE_CODEX_ENABLE_TOKEN = "LOCAL_LIVE_CODEX_GATE_ENABLE"

CALCULATOR_SOURCE = "def add(a, b):\n    return a + b\n"
TEST_SOURCE = "from calculator import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"

CYCLE_TASKS = [
    {
        "name": "cycle1",
        "function_name": "subtract",
        "expression": "a - b",
        "summary": "cycle1 subtract function added",
    },
    {
        "name": "cycle2",
        "function_name": "multiply",
        "expression": "a * b",
        "summary": "cycle2 multiply function added",
    },
]

EXPECTED_SANDBOX_FILES = {"calculator.py", "test_calculator.py"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _run_git(args: list[str], cwd: Path) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _list_sandbox_files(repo: Path) -> set[str]:
    files: set[str] = set()
    for entry in repo.rglob("*"):
        if not entry.is_file():
            continue
        rel = entry.relative_to(repo).as_posix()
        if rel == ".git" or rel.startswith(".git/"):
            continue
        files.add(rel)
    return files


def build_prompt(repo_path: str, function_name: str, expression: str, summary: str) -> str:
    return (
        f"You are operating only inside {repo_path}.\n"
        "Modify only calculator.py.\n"
        f"Add a function named {function_name}(a, b) that returns {expression}.\n"
        "Do not modify test_calculator.py.\n"
        "Do not create new files.\n"
        "Do not commit.\n"
        "Do not tag.\n"
        "Do not push.\n"
        f"Do not modify {REPO_ROOT.as_posix()}.\n"
        "After editing, reply only with:\n"
        f'{{"status":"success","summary":"{summary}"}}\n'
    )


def build_effect_spec(repo_path: str, function_name: str, expression: str) -> dict[str, Any]:
    return {
        "repo_path": repo_path,
        "expected_modified_files": ["calculator.py"],
        "expected_unmodified_files": ["test_calculator.py"],
        "required_text": {
            "calculator.py": [
                f"def {function_name}(a, b):",
                f"return {expression}",
            ]
        },
        "forbidden_paths": [],
        "allow_extra_files": False,
    }


def create_fixture(work_dir: Path) -> dict[str, Any]:
    """Create sandbox repos, prompts, effect specs, manifest, and dirty-gate repo."""
    work_dir = Path(work_dir).resolve()
    if work_dir == REPO_ROOT or REPO_ROOT in work_dir.parents or work_dir in REPO_ROOT.parents:
        raise ValueError(f"work dir must be outside the main repo: {work_dir}")
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)

    cycles: list[dict[str, Any]] = []
    manifest_cycles: list[dict[str, str]] = []
    for task in CYCLE_TASKS:
        repo = work_dir / f"{task['name']}_sandbox_repo"
        repo.mkdir()
        (repo / "calculator.py").write_text(CALCULATOR_SOURCE, encoding="utf-8")
        (repo / "test_calculator.py").write_text(TEST_SOURCE, encoding="utf-8")
        _run_git(["init", "-q"], cwd=repo)
        _run_git(["add", "calculator.py", "test_calculator.py"], cwd=repo)
        _run_git(
            [
                "-c", "user.email=acceptance@local",
                "-c", "user.name=acceptance",
                "commit", "-q", "-m", "initial sandbox fixture",
            ],
            cwd=repo,
        )

        prompt_path = work_dir / f"{task['name']}_prompt.md"
        prompt_path.write_text(
            build_prompt(repo.as_posix(), task["function_name"], task["expression"], task["summary"]),
            encoding="utf-8",
        )
        spec_path = work_dir / f"{task['name']}_effect_spec.json"
        spec_path.write_text(
            json.dumps(build_effect_spec(repo.as_posix(), task["function_name"], task["expression"]), indent=2)
            + "\n",
            encoding="utf-8",
        )
        cycles.append(
            {
                "name": task["name"],
                "function_name": task["function_name"],
                "expression": task["expression"],
                "repo_path": repo.as_posix(),
                "prompt_path": prompt_path.as_posix(),
                "effect_spec_path": spec_path.as_posix(),
                "test_file_hash": _sha256(repo / "test_calculator.py"),
            }
        )
        manifest_cycles.append(
            {
                "generated_prompt_path": prompt_path.as_posix(),
                "repo_path": repo.as_posix(),
                "effect_spec_path": spec_path.as_posix(),
            }
        )

    manifest_path = work_dir / "manifest.json"
    manifest_path.write_text(json.dumps({"cycles": manifest_cycles}, indent=2) + "\n", encoding="utf-8")

    # The loop-level dirty guard needs a clean git repo to watch; the main repo may
    # legitimately carry uncommitted work while running acceptance. Sandbox safety
    # is enforced by the per-cycle effect specs plus this script's own before/after
    # main-repo status comparison.
    dirty_gate_repo = work_dir / "dirty_gate_repo"
    dirty_gate_repo.mkdir()
    _run_git(["init", "-q"], cwd=dirty_gate_repo)
    _run_git(
        [
            "-c", "user.email=acceptance@local",
            "-c", "user.name=acceptance",
            "commit", "-q", "--allow-empty", "-m", "clean dirty-gate repo",
        ],
        cwd=dirty_gate_repo,
    )

    return {
        "work_dir": work_dir.as_posix(),
        "manifest_path": manifest_path.as_posix(),
        "dirty_gate_repo": dirty_gate_repo.as_posix(),
        "cycles": cycles,
    }


def build_loop_command(
    fixture: Mapping[str, Any],
    out_dir: Path,
    max_cycles: int,
    max_seconds: int,
    live_timeout_seconds: int,
) -> list[str]:
    return [
        sys.executable,
        RUNNER_SCRIPT.as_posix(),
        "--autonomous-live-loop",
        "--autonomous-enable-token", AUTONOMOUS_ENABLE_TOKEN,
        "--live-codex-enable-token", LIVE_CODEX_ENABLE_TOKEN,
        "--max-cycles", str(max_cycles),
        "--max-seconds", str(max_seconds),
        "--live-loop-timeout-seconds", str(live_timeout_seconds),
        "--live-loop-verification-continue",
        "--live-loop-sandbox-mode", "workspace-write",
        "--live-loop-generated-prompt-manifest-path", str(fixture["manifest_path"]),
        "--repo-path", str(fixture["dirty_gate_repo"]),
        "--out-dir", Path(out_dir).as_posix(),
        "--json",
    ]


def validate_acceptance(
    *,
    state: Mapping[str, Any],
    fixture: Mapping[str, Any],
    main_repo_status_before: list[str],
    main_repo_status_after: list[str],
    main_repo_head_before: str,
    main_repo_head_after: str,
) -> dict[str, Any]:
    failures: list[str] = []
    cycles = list(fixture["cycles"])

    cycle_count = int(state.get("cycle_count", 0) or 0)
    codex_invoked_count = int(state.get("codex_invoked_count", 0) or 0)
    effect_statuses = list(state.get("per_cycle_effect_verification_statuses", []))

    if state.get("status") != "success":
        failures.append(f"loop status is not success: {state.get('status')}")
    if cycle_count < 2:
        failures.append(f"cycle_count below 2: {cycle_count}")
    if codex_invoked_count < 2:
        failures.append(f"codex_invoked_count below 2: {codex_invoked_count}")
    for index in range(min(2, len(cycles))):
        status = effect_statuses[index] if index < len(effect_statuses) else "missing"
        if status != "passed":
            failures.append(f"cycle {index + 1} effect verification not passed: {status}")
    if state.get("commit_performed") or state.get("tag_performed"):
        failures.append("runtime reported commit/tag performed")

    cycle_results: list[dict[str, Any]] = []
    for cycle in cycles:
        repo = Path(cycle["repo_path"])
        calculator_text = ""
        try:
            calculator_text = (repo / "calculator.py").read_text(encoding="utf-8")
        except OSError:
            failures.append(f"{cycle['name']}: calculator.py unreadable")
        function_present = (
            f"def {cycle['function_name']}(a, b):" in calculator_text
            and f"return {cycle['expression']}" in calculator_text
        )
        if not function_present:
            failures.append(f"{cycle['name']}: {cycle['function_name']} missing from calculator.py")
        test_unchanged = _sha256(repo / "test_calculator.py") == cycle["test_file_hash"]
        if not test_unchanged:
            failures.append(f"{cycle['name']}: test_calculator.py changed")
        extra_files = sorted(_list_sandbox_files(repo) - EXPECTED_SANDBOX_FILES)
        if extra_files:
            failures.append(f"{cycle['name']}: unexpected files: {extra_files}")
        try:
            commit_count = len(_run_git(["log", "--oneline"], cwd=repo).splitlines())
            tag_count = len([line for line in _run_git(["tag"], cwd=repo).splitlines() if line.strip()])
        except subprocess.CalledProcessError:
            commit_count, tag_count = -1, -1
            failures.append(f"{cycle['name']}: git inspection failed")
        if commit_count != 1:
            failures.append(f"{cycle['name']}: unexpected commit count {commit_count}")
        if tag_count != 0:
            failures.append(f"{cycle['name']}: unexpected tag count {tag_count}")
        cycle_results.append(
            {
                "name": cycle["name"],
                "repo_path": cycle["repo_path"],
                "function_present": function_present,
                "test_file_unchanged": test_unchanged,
                "no_extra_files": not extra_files,
                "extra_files": extra_files,
            }
        )

    main_repo_source_modified = sorted(main_repo_status_before) != sorted(main_repo_status_after)
    if main_repo_source_modified:
        failures.append("main repo git status changed during runtime")
    if main_repo_head_before != main_repo_head_after:
        failures.append("main repo HEAD changed during runtime")

    return {
        "acceptance_status": "success" if not failures else "blocked",
        "failures": failures,
        "cycle_count": cycle_count,
        "codex_invoked_count": codex_invoked_count,
        "commit_tag_gate_observed_count": int(state.get("commit_tag_gate_observed_count", 0) or 0),
        "effect_verification_cycle1_status": effect_statuses[0] if len(effect_statuses) > 0 else "not_run",
        "effect_verification_cycle2_status": effect_statuses[1] if len(effect_statuses) > 1 else "not_run",
        "cycle_results": cycle_results,
        "runtime_commit_or_tag_performed": bool(state.get("commit_performed") or state.get("tag_performed")),
        "main_repo_source_modified": main_repo_source_modified,
    }


def _main_repo_status() -> list[str]:
    return [line for line in _run_git(["status", "--short"], cwd=REPO_ROOT).splitlines() if line.strip()]


def _main_repo_head() -> str:
    return _run_git(["rev-parse", "HEAD"], cwd=REPO_ROOT).strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Integrated two-cycle live loop acceptance fixture")
    parser.add_argument("--work-dir", default="/tmp/codex-local-runner-acceptance")
    parser.add_argument("--out-dir", default="/tmp/codex-local-runner-acceptance-out")
    parser.add_argument("--max-cycles", type=int, default=2)
    parser.add_argument("--max-seconds", type=int, default=300)
    parser.add_argument("--live-timeout-seconds", type=int, default=90)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    if args.max_cycles < 2:
        print("error: the integrated proof requires --max-cycles >= 2", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir).resolve()
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    base_commit = _run_git(["log", "-1", "--format=%h"], cwd=REPO_ROOT).strip()
    base_tags = [t for t in _run_git(["tag", "--points-at", "HEAD"], cwd=REPO_ROOT).splitlines() if t.strip()]
    status_before = _main_repo_status()
    head_before = _main_repo_head()

    fixture = create_fixture(Path(args.work_dir))
    command = build_loop_command(
        fixture, out_dir, args.max_cycles, args.max_seconds, args.live_timeout_seconds
    )
    completed = subprocess.run(command, capture_output=True, text=True)
    (out_dir / "loop_stdout.txt").write_text(completed.stdout or "", encoding="utf-8")
    (out_dir / "loop_stderr.txt").write_text(completed.stderr or "", encoding="utf-8")

    state_path = out_dir / "autonomous_live_loop_state.json"
    state: dict[str, Any] = {}
    if state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state = {}

    status_after = _main_repo_status()
    head_after = _main_repo_head()

    validation = validate_acceptance(
        state=state,
        fixture=fixture,
        main_repo_status_before=status_before,
        main_repo_status_after=status_after,
        main_repo_head_before=head_before,
        main_repo_head_after=head_after,
    )
    if completed.returncode != 0:
        validation["acceptance_status"] = "blocked"
        validation["failures"].append(f"loop process returncode {completed.returncode}")

    cycle_results = validation["cycle_results"]
    report = {
        "acceptance_status": validation["acceptance_status"],
        "failures": validation["failures"],
        "failure_digest_path": str(state.get("failure_digest_path", "")),
        "base_commit": base_commit,
        "base_tags_at_head": base_tags,
        "command": command,
        "work_dir": fixture["work_dir"],
        "out_dir": out_dir.as_posix(),
        "process_returncode": completed.returncode,
        "autonomous_live_loop_state_path": state_path.as_posix(),
        "cycle_count": validation["cycle_count"],
        "codex_invoked_count": validation["codex_invoked_count"],
        "commit_tag_gate_observed_count": validation["commit_tag_gate_observed_count"],
        "effect_verification_cycle1_status": validation["effect_verification_cycle1_status"],
        "effect_verification_cycle2_status": validation["effect_verification_cycle2_status"],
        "cycle1_repo_path": cycle_results[0]["repo_path"] if len(cycle_results) > 0 else "",
        "cycle2_repo_path": cycle_results[1]["repo_path"] if len(cycle_results) > 1 else "",
        "cycle1_subtract_present": bool(cycle_results[0]["function_present"]) if len(cycle_results) > 0 else False,
        "cycle2_multiply_present": bool(cycle_results[1]["function_present"]) if len(cycle_results) > 1 else False,
        "cycle1_test_file_unchanged": bool(cycle_results[0]["test_file_unchanged"]) if len(cycle_results) > 0 else False,
        "cycle2_test_file_unchanged": bool(cycle_results[1]["test_file_unchanged"]) if len(cycle_results) > 1 else False,
        "cycle1_no_extra_files": bool(cycle_results[0]["no_extra_files"]) if len(cycle_results) > 0 else False,
        "cycle2_no_extra_files": bool(cycle_results[1]["no_extra_files"]) if len(cycle_results) > 1 else False,
        "runtime_commit_or_tag_performed": validation["runtime_commit_or_tag_performed"],
        "main_repo_source_modified": validation["main_repo_source_modified"],
        "final_decision": validation["acceptance_status"],
        "next_action": (
            "commit_tag_gate" if validation["acceptance_status"] == "success" else "inspect_acceptance_runtime_failure"
        ),
        "generated_at": _utc_now(),
    }
    report_path = out_dir / "integrated_live_acceptance_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(f"acceptance_status={report['acceptance_status']}")
        print(f"cycle_count={report['cycle_count']}")
        print(f"codex_invoked_count={report['codex_invoked_count']}")
        print(f"effect_verification_cycle1_status={report['effect_verification_cycle1_status']}")
        print(f"effect_verification_cycle2_status={report['effect_verification_cycle2_status']}")
        print(f"report_path={report_path.as_posix()}")
        for failure in report["failures"]:
            print(f"failure={failure}")
    return 0 if report["acceptance_status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())

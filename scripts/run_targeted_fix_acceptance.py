#!/usr/bin/env python3
"""Live acceptance for the bounded targeted-fix retry (Prompt630 capability).

Creates a scratch repo with an intentional failed-effect case: the original prompt
tells Codex to change nothing while the effect spec requires subtract(a, b). The
first gate attempt therefore fails effect verification; the retry builds a fix
prompt from the failure digest and runs one bounded fix attempt that must converge.

Local-only. Never commits, tags, stages, or pushes anywhere.
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

from automation.orchestration.planned_runner.targeted_fix_retry import (  # noqa: E402
    run_targeted_fix_retry,
)

LIVE_CODEX_ENABLE_TOKEN = "LOCAL_LIVE_CODEX_GATE_ENABLE"

CALCULATOR_SOURCE = "def add(a, b):\n    return a + b\n"
TEST_SOURCE = "from calculator import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _git(args: list[str], cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


def _main_repo_status() -> list[str]:
    return [line for line in _git(["status", "--short"], cwd=REPO_ROOT).splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Targeted-fix retry live acceptance")
    parser.add_argument("--work-dir", default="/tmp/codex-local-runner-targeted-fix-acceptance")
    parser.add_argument("--out-dir", default="/tmp/codex-local-runner-targeted-fix-acceptance-out")
    parser.add_argument("--live-timeout-seconds", type=int, default=90)
    parser.add_argument("--max-fix-attempts", type=int, default=1)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    work_dir = Path(args.work_dir).resolve()
    out_dir = Path(args.out_dir).resolve()
    if work_dir == REPO_ROOT or REPO_ROOT in work_dir.parents:
        print("error: work dir must be outside the main repo", file=sys.stderr)
        return 2
    for path in (work_dir, out_dir):
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True)

    status_before = _main_repo_status()

    repo = work_dir / "sandbox_repo"
    repo.mkdir()
    (repo / "calculator.py").write_text(CALCULATOR_SOURCE, encoding="utf-8")
    (repo / "test_calculator.py").write_text(TEST_SOURCE, encoding="utf-8")
    _git(["init", "-q"], cwd=repo)
    _git(["add", "."], cwd=repo)
    _git(
        ["-c", "user.email=acceptance@local", "-c", "user.name=acceptance", "commit", "-q", "-m", "fixture"],
        cwd=repo,
    )

    # Intentionally failing original prompt: it forbids changes while the spec
    # requires subtract -> attempt 0 must fail effect verification.
    original_prompt = work_dir / "original_prompt.md"
    original_prompt.write_text(
        f"You are operating only inside {repo.as_posix()}.\n"
        "Do not modify files.\n"
        "Do not run shell commands.\n"
        "Do not create files.\n"
        "Reply only with a single JSON object:\n"
        '{"status":"success","summary":"no change made"}\n',
        encoding="utf-8",
    )
    effect_spec = work_dir / "effect_spec.json"
    effect_spec.write_text(
        json.dumps(
            {
                "repo_path": repo.as_posix(),
                "expected_modified_files": ["calculator.py"],
                "expected_unmodified_files": ["test_calculator.py"],
                "required_text": {"calculator.py": ["def subtract(a, b):", "return a - b"]},
                "forbidden_paths": [],
                "allow_extra_files": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    payload = run_targeted_fix_retry(
        generated_prompt_path=original_prompt,
        effect_spec_path=effect_spec,
        out_dir=out_dir,
        live_codex_enable_token=LIVE_CODEX_ENABLE_TOKEN,
        sandbox_mode="workspace-write",
        timeout_seconds=args.live_timeout_seconds,
        max_fix_attempts=args.max_fix_attempts,
    )

    status_after = _main_repo_status()
    calculator_text = (repo / "calculator.py").read_text(encoding="utf-8")
    failures: list[str] = []
    if not payload.get("converged"):
        failures.append(f"retry did not converge: {payload.get('stop_reason')}")
    if payload.get("fix_attempts_used", 0) < 1:
        failures.append("expected at least one fix attempt (induced first failure)")
    if "def subtract(a, b):" not in calculator_text:
        failures.append("subtract missing after retry")
    if (repo / "test_calculator.py").read_text(encoding="utf-8") != TEST_SOURCE:
        failures.append("test_calculator.py changed")
    if len(_git(["log", "--oneline"], cwd=repo).splitlines()) != 1:
        failures.append("sandbox commit count changed")
    if _git(["tag"], cwd=repo).strip():
        failures.append("sandbox tag created")
    if sorted(status_before) != sorted(status_after):
        failures.append("main repo status changed during runtime")

    report = {
        "acceptance_status": "success" if not failures else "blocked",
        "failures": failures,
        "retry_state": payload,
        "sandbox_repo": repo.as_posix(),
        "fix_attempts_used": payload.get("fix_attempts_used"),
        "codex_invoked_count": payload.get("codex_invoked_count"),
        "converged": payload.get("converged"),
        "main_repo_source_modified": sorted(status_before) != sorted(status_after),
        "generated_at": _utc_now(),
    }
    report_path = out_dir / "targeted_fix_acceptance_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(f"acceptance_status={report['acceptance_status']}")
        print(f"report_path={report_path.as_posix()}")
    return 0 if report["acceptance_status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())

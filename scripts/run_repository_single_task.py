"""Command-line boundary for one repository-resolved local task."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from automation.orchestration.repository_resolved_single_task_controller import run_repository_single_task


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one repository-resolved local task")
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--task-spec", required=True)
    return parser


def _emit(result: object) -> None:
    fields = (
        "status", "reason_code", "receipt_path", "repository_id", "task_id",
        "task_branch", "commit_sha", "worktree_preserved",
    )
    for field in fields:
        value = getattr(result, field, "")
        print(f"{field}={'' if value is None else value}")


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        result = run_repository_single_task(
            repository_id=arguments.repository_id,
            task_spec_path=arguments.task_spec,
        )
    except (OSError, ValueError, TypeError):
        print("status=failed\nreason_code=single_task.cli.controller_failed\nreceipt_path=\nrepository_id=\ntask_id=\ntask_branch=\ncommit_sha=\nworktree_preserved=")
        print("FAILED_REPOSITORY_SINGLE_TASK")
        return 1
    _emit(result)
    if result.status == "completed":
        print("READY_FOR_PUSH_REVIEW")
        return 0
    if result.status == "blocked":
        print("BLOCKED_REPOSITORY_SINGLE_TASK")
        return 2
    print("FAILED_REPOSITORY_SINGLE_TASK")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

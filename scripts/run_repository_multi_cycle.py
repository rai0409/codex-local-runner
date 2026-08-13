"""Command-line boundary for a local repository multi-cycle task queue."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from automation.orchestration.repository_multi_cycle_task_executor import run_repository_multi_cycle


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a repository-resolved local task queue")
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--queue-spec", required=True)
    parser.add_argument("--resume-cycle-run-id")
    parser.add_argument("--registry-path")
    parser.add_argument("--bindings-path")
    parser.add_argument("--providers-path")
    parser.add_argument("--output-root")
    parser.add_argument("--single-task-output-root")
    return parser


def _emit(result: object) -> None:
    for field in ("status", "reason_code", "receipt_path", "repository_id", "source_anchor_sha", "accepted_head_sha", "completed_count", "stopped_task_id"):
        value = getattr(result, field, "")
        print(f"{field}={'' if value is None else value}")


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        kwargs = {"repository_id": arguments.repository_id, "queue_spec_path": arguments.queue_spec, "resume_cycle_run_id": arguments.resume_cycle_run_id}
        for argument, keyword in (("registry_path","registry_path"),("bindings_path","bindings_path"),("providers_path","providers_path"),("output_root","output_root"),("single_task_output_root","single_task_output_root")):
            value = getattr(arguments, argument)
            if value is not None: kwargs[keyword] = value
        result = run_repository_multi_cycle(**kwargs)
    except Exception:
        print("status=failed\nreason_code=multi_cycle.cli.controller_failed\nreceipt_path=\nrepository_id=\nsource_anchor_sha=\naccepted_head_sha=\ncompleted_count=\nstopped_task_id=")
        print("FAILED_REPOSITORY_MULTI_CYCLE")
        return 1
    _emit(result)
    if result.status == "completed":
        print("READY_FOR_MULTI_CYCLE_REVIEW"); return 0
    if result.status == "blocked":
        print("BLOCKED_REPOSITORY_MULTI_CYCLE"); return 2
    print("FAILED_REPOSITORY_MULTI_CYCLE")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

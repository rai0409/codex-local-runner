"""Read-only status view for repository multi-cycle execution."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from automation.orchestration.repository_multi_cycle_status import (
    DEFAULT_CYCLE_OUTPUT_ROOT,
    DEFAULT_SUPERVISOR_STATE_ROOT,
    inspect_repository_multi_cycle_status,
)

_FIELDS = (
    "repository_id", "queue_sha256", "state", "cycle_run_id", "supervisor_pid", "supervisor_alive",
    "worker_pid", "worker_alive", "task_count", "completed_count", "current_task_index", "current_task_id",
    "phase", "last_activity_at", "terminal_status", "reason_code", "source_anchor_sha",
    "final_accepted_head_sha", "action_required", "authoritative_source",
)


def _render(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-id", required=True)
    parser.add_argument("--queue-spec", required=True)
    parser.add_argument("--state-root", default=DEFAULT_SUPERVISOR_STATE_ROOT)
    parser.add_argument("--output-root", default=DEFAULT_CYCLE_OUTPUT_ROOT)
    args = parser.parse_args(argv)
    status = inspect_repository_multi_cycle_status(args.repository_id, args.queue_spec, state_root=args.state_root, cycle_output_root=args.output_root)
    for field in _FIELDS:
        print(f"{field}={_render(status.get(field))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.control.action_executor import ActionExecutor  # noqa: E402
from automation.execution.codex_executor_adapter import CodexExecutorAdapter  # noqa: E402
from automation.orchestration.planned_execution_runner import DryRunCodexExecutionTransport  # noqa: E402
from automation.orchestration.planned_execution_runner import PlannedExecutionRunner  # noqa: E402
from automation.scheduler.job_lease import FileJobLease  # noqa: E402
from automation.scheduler.job_registry import FileJobRegistry  # noqa: E402
from automation.scheduler.job_scheduler import JobScheduler  # noqa: E402
from automation.scheduler.run_dispatcher import RunDispatcher  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run bounded scheduler cycle(s) with local registry/lease persistence")
    parser.add_argument("--artifacts-root", required=True, help="Root directory containing per-job planning artifact directories")
    parser.add_argument("--output-root", required=True, help="Root directory for executions/<job_id> outputs")
    parser.add_argument("--registry", default=None, help="Optional registry path (default: <output-root>/job_registry.json)")
    parser.add_argument("--leases", default=None, help="Optional leases path (default: <output-root>/job_leases.json)")
    parser.add_argument("--holder", default="scheduler-cli", help="Lease holder identifier")
    parser.add_argument("--lease-seconds", type=int, default=120, help="Lease TTL seconds")
    parser.add_argument("--max-jobs", type=int, default=20, help="Maximum jobs to process per cycle")
    parser.add_argument("--max-cycles", type=int, default=1, help="Bounded number of cycles to execute")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Run planned execution in dry-run mode")
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def build_scheduler(*, output_root: Path, registry_path: Path | None, leases_path: Path | None) -> JobScheduler:
    registry = FileJobRegistry(registry_path or (output_root / "job_registry.json"))
    leases = FileJobLease(leases_path or (output_root / "job_leases.json"))
    adapter = CodexExecutorAdapter(transport=DryRunCodexExecutionTransport())
    runner = PlannedExecutionRunner(adapter=adapter)
    dispatcher = RunDispatcher(
        runner=runner,
        action_executor=ActionExecutor(),
    )
    return JobScheduler(
        dispatcher=dispatcher,
        registry=registry,
        lease_manager=leases,
    )


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    artifacts_root = Path(args.artifacts_root)
    output_root = Path(args.output_root)
    registry_path = Path(args.registry) if args.registry else None
    leases_path = Path(args.leases) if args.leases else None

    try:
        if not artifacts_root.exists() or not artifacts_root.is_dir():
            raise ValueError(f"artifacts root does not exist: {artifacts_root}")
        output_root.mkdir(parents=True, exist_ok=True)
        if args.max_cycles <= 0:
            raise ValueError("max-cycles must be a positive integer")
        if args.max_jobs <= 0:
            raise ValueError("max-jobs must be a positive integer")
        if args.lease_seconds <= 0:
            raise ValueError("lease-seconds must be a positive integer")

        scheduler = build_scheduler(
            output_root=output_root,
            registry_path=registry_path,
            leases_path=leases_path,
        )
        summary = scheduler.run_registry_cycles(
            artifacts_root=artifacts_root,
            output_root=output_root,
            holder=args.holder,
            lease_seconds=args.lease_seconds,
            max_jobs=args.max_jobs,
            max_cycles=args.max_cycles,
            dry_run=bool(args.dry_run),
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.as_json:
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    else:
        print(f"cycle_count={summary.get('cycle_count', 0)}")
        print(f"jobs_considered={summary.get('jobs_considered', 0)}")
        print(f"jobs_claimed={summary.get('jobs_claimed', 0)}")
        print(f"jobs_run={summary.get('jobs_run', 0)}")
        print(f"jobs_paused={summary.get('jobs_paused', 0)}")
        print(f"jobs_escalated={summary.get('jobs_escalated', 0)}")
        print(f"jobs_completed={summary.get('jobs_completed', 0)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


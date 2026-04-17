from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.execution.codex_executor_adapter import CodexExecutorAdapter  # noqa: E402
from automation.orchestration.planned_execution_runner import DryRunCodexExecutionTransport  # noqa: E402
from automation.orchestration.planned_execution_runner import PlannedExecutionRunner  # noqa: E402


_REQUIRED_ARTIFACT_FILES = (
    "project_brief.json",
    "repo_facts.json",
    "roadmap.json",
    "pr_plan.json",
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run planned PR-slice execution in deterministic dry-run mode")
    parser.add_argument("--artifacts-dir", required=True, help="Directory containing planning artifacts")
    parser.add_argument("--out-dir", required=True, help="Output root for execution artifacts")
    parser.add_argument("--job-id", default=None, help="Optional override for execution job_id")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Dry-run execution mode")
    parser.add_argument("--no-dry-run", action="store_true", help="Reject non-dry-run mode in this phase")
    parser.add_argument("--stop-on-failure", action="store_true", default=True, help="Stop when a unit fails")
    parser.add_argument("--continue-on-failure", action="store_true", help="Continue processing units after failures")
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def _validate_inputs(artifacts_dir: Path) -> None:
    if not artifacts_dir.exists() or not artifacts_dir.is_dir():
        raise ValueError(f"artifacts directory does not exist: {artifacts_dir}")

    missing: list[str] = []
    for filename in _REQUIRED_ARTIFACT_FILES:
        if not (artifacts_dir / filename).exists():
            missing.append(filename)
    if missing:
        raise ValueError("missing required planning artifacts: " + ", ".join(missing))


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    artifacts_dir = Path(args.artifacts_dir)
    out_dir = Path(args.out_dir)

    try:
        _validate_inputs(artifacts_dir)

        if args.no_dry_run:
            raise ValueError("non-dry-run mode is not supported in this phase")

        dry_run = bool(args.dry_run)
        stop_on_failure = False if args.continue_on_failure else bool(args.stop_on_failure)

        adapter = CodexExecutorAdapter(transport=DryRunCodexExecutionTransport())
        runner = PlannedExecutionRunner(adapter=adapter)
        manifest = runner.run(
            artifacts_input_dir=artifacts_dir,
            output_dir=out_dir,
            job_id=args.job_id,
            dry_run=dry_run,
            stop_on_failure=stop_on_failure,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.as_json:
        print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    else:
        print(f"job_id={manifest['job_id']}")
        print(f"run_status={manifest['run_status']}")
        print(f"processed_units={len(manifest.get('pr_units', []))}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

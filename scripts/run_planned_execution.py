from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from automation.execution.codex_executor_adapter import CodexExecutorAdapter  # noqa: E402
from automation.execution.codex_executor_adapter import select_execution_transport  # noqa: E402
from automation.execution.codex_live_transport import CodexLiveExecutionTransport  # noqa: E402
from automation.orchestration.planned_execution_runner import DryRunCodexExecutionTransport  # noqa: E402
from automation.orchestration.planned_execution_runner import PlannedExecutionRunner  # noqa: E402


_REQUIRED_ARTIFACT_FILES = (
    "project_brief.json",
    "repo_facts.json",
    "roadmap.json",
    "pr_plan.json",
)


def _read_json_file_if_present(path_value: str | None) -> dict[str, object] | None:
    text = str(path_value or "").strip()
    if not text:
        return None
    path = Path(text)
    if not path.exists():
        raise ValueError(f"input file does not exist: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"input file must contain a JSON object: {path}")
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run planned PR-slice execution with explicit transport mode")
    parser.add_argument("--artifacts-dir", required=True, help="Directory containing planning artifacts")
    parser.add_argument("--out-dir", required=True, help="Output root for execution artifacts")
    parser.add_argument("--job-id", default=None, help="Optional override for execution job_id")
    parser.add_argument("--retry-context", default=None, help="Optional retry context JSON path")
    parser.add_argument("--policy-snapshot", default=None, help="Optional policy snapshot JSON path")
    parser.add_argument("--github-read-evidence", default=None, help="Optional GitHub read evidence JSON path")
    parser.add_argument(
        "--transport-mode",
        default="dry-run",
        choices=("dry-run", "live"),
        help="Execution transport mode",
    )
    parser.add_argument("--enable-live-transport", action="store_true", help="Explicitly allow live transport mode")
    parser.add_argument("--repo-path", default=None, help="Repository path required for live transport mode")
    parser.add_argument("--live-timeout-seconds", type=int, default=600, help="Timeout for live Codex execution")
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

        retry_context = _read_json_file_if_present(args.retry_context)
        policy_snapshot = _read_json_file_if_present(args.policy_snapshot)
        github_read_evidence = _read_json_file_if_present(args.github_read_evidence)
        if args.transport_mode == "live":
            if not args.enable_live_transport:
                raise ValueError("live transport mode requires --enable-live-transport")
            repo_path_text = str(args.repo_path or "").strip()
            if not repo_path_text:
                raise ValueError("live transport mode requires --repo-path")
            repo_path = Path(repo_path_text)
            if not repo_path.exists() or not repo_path.is_dir():
                raise ValueError(f"repo_path does not exist or is not a directory: {repo_path}")
            if args.live_timeout_seconds <= 0:
                raise ValueError("live timeout must be a positive integer")

        dry_run_transport = DryRunCodexExecutionTransport()
        live_transport = (
            CodexLiveExecutionTransport(
                repo_path=str(Path(args.repo_path).resolve()),
                timeout_seconds=args.live_timeout_seconds,
            )
            if args.transport_mode == "live"
            else None
        )
        selected_transport, resolved_mode = select_execution_transport(
            mode=args.transport_mode,
            dry_run_transport=dry_run_transport,
            live_transport=live_transport,
            live_transport_enabled=bool(args.enable_live_transport),
        )
        dry_run = resolved_mode == "dry-run"
        stop_on_failure = False if args.continue_on_failure else bool(args.stop_on_failure)

        adapter = CodexExecutorAdapter(transport=selected_transport)
        runner = PlannedExecutionRunner(adapter=adapter)
        manifest = runner.run(
            artifacts_input_dir=artifacts_dir,
            output_dir=out_dir,
            job_id=args.job_id,
            dry_run=dry_run,
            stop_on_failure=stop_on_failure,
            retry_context=retry_context,
            policy_snapshot=policy_snapshot,
            github_read_evidence=github_read_evidence,
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
        print(f"next_action={manifest.get('decision_summary', {}).get('next_action', '')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

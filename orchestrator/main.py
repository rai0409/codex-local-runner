from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from adapters import get_registered_adapters, resolve_adapter
from orchestrator.config_loader import load_yaml_file
from orchestrator.models import TASK_STATUS_FAILED
from orchestrator.models import DispatchRequest
from orchestrator.task_bus import dispatch


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="codex-local-runner phase1 dispatch cli")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--task-type", required=True)
    parser.add_argument("--goal", required=True)
    parser.add_argument("--provider", default="codex_cli")
    parser.add_argument("--providers-config", default="config/providers.yaml")
    parser.add_argument("--routing-config", default="config/routing_rules.yaml")
    parser.add_argument("--repos-config", default="config/repos.yaml")
    parser.add_argument("--output-root", default="tasks/control_plane_dispatches")
    parser.add_argument("--execution-repo-path", default=".")
    return parser


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    args = _build_parser().parse_args()

    providers = load_yaml_file(args.providers_config)
    routing = load_yaml_file(args.routing_config)
    repos = load_yaml_file(args.repos_config)

    adapters = get_registered_adapters()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.output_root) / stamp
    suffix = 1
    while out_dir.exists():
        out_dir = Path(args.output_root) / f"{stamp}_{suffix}"
        suffix += 1
    out_dir.mkdir(parents=True, exist_ok=False)
    job_id = out_dir.name

    request = DispatchRequest(
        job_id=job_id,
        repo=args.repo,
        task_type=args.task_type,
        goal=args.goal,
        provider=args.provider,
        metadata={
            "routing_rules_version": routing.get("version"),
            "repos_version": repos.get("version"),
            "adapter_names": sorted(adapters.keys()),
        },
    )

    request_payload = {
        "job_id": request.job_id,
        "repo": request.repo,
        "task_type": request.task_type,
        "goal": request.goal,
        "provider": request.provider,
        "metadata": request.metadata,
    }
    request_path = out_dir / "request.json"
    result_path = out_dir / "result.json"

    try:
        resolved_adapter = resolve_adapter(request.provider, providers)
    except ValueError as exc:
        result_payload = {
            "status": TASK_STATUS_FAILED,
            "accepted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "job_id": request.job_id,
            "repo": request.repo,
            "task_type": request.task_type,
            "provider": request.provider,
            "message": str(exc),
            "dispatcher": "orchestrator.main.resolve_adapter",
            "artifacts": [
                str(request_path),
                str(result_path),
            ],
            "execution": {
                "adapter": request.provider,
                "status": "not_started",
                "started_at": None,
                "finished_at": None,
                "artifacts": [],
                "error": str(exc),
            },
        }
    else:
        request_payload["metadata"]["resolved_adapter"] = resolved_adapter.__class__.__name__
        result_payload = dispatch(request=request, providers_config=providers)
        result_payload["artifacts"] = [
            str(request_path),
            str(result_path),
        ]
        if result_payload["status"] == "accepted":
            try:
                execution_payload = {
                    "prompt": request.goal,
                    "repo_path": args.execution_repo_path,
                    "work_dir": str(out_dir),
                }
                execution_result = resolved_adapter.execute(execution_payload)
            except NotImplementedError as exc:
                execution_result = {
                    "adapter": resolved_adapter.name,
                    "status": "not_implemented",
                    "started_at": None,
                    "finished_at": None,
                    "artifacts": [],
                    "error": str(exc),
                }
            except Exception as exc:
                execution_result = {
                    "adapter": resolved_adapter.name,
                    "status": "failed",
                    "started_at": None,
                    "finished_at": None,
                    "artifacts": [],
                    "error": f"Unexpected execution error ({type(exc).__name__}): {exc}",
                }
        else:
            execution_result = {
                "adapter": resolved_adapter.name,
                "status": "not_started",
                "started_at": None,
                "finished_at": None,
                "artifacts": [],
                "error": "acceptance failed before execution",
            }
        result_payload["execution"] = execution_result

    _write_json(request_path, request_payload)
    _write_json(result_path, result_payload)

    print(f"dispatch_dir={out_dir}")
    print(f"request_path={request_path}")
    print(f"result_path={result_path}")
    print(f"status={result_payload['status']}")

    return 0 if result_payload["status"] == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from adapters import get_registered_adapters, resolve_adapter
from orchestrator.config_loader import load_yaml_file
from orchestrator.job_evaluator import evaluate_job_directory
from orchestrator.job_evaluator import persist_evaluation_artifacts
from orchestrator.ledger import record_job_evaluation
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
    parser.add_argument(
        "--validation-command",
        dest="validation_commands",
        action="append",
        default=[],
    )
    return parser


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    args = _build_parser().parse_args()
    validation_commands = [
        str(command).strip() for command in args.validation_commands if str(command).strip()
    ]

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
        validation_commands=validation_commands,
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
        "validation_commands": request.validation_commands,
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
                    "validation_commands": request.validation_commands,
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

    result_payload["persistence"] = {
        "evaluation_artifacts": "skipped",
        "ledger": "skipped",
    }

    _write_json(request_path, request_payload)
    _write_json(result_path, result_payload)
    if result_payload["status"] == "accepted":
        evaluation_result = None
        try:
            evaluation_result = evaluate_job_directory(out_dir)
            persist_evaluation_artifacts(out_dir, evaluation_result=evaluation_result)
        except Exception:
            result_payload["persistence"]["evaluation_artifacts"] = "failed"
        else:
            result_payload["persistence"]["evaluation_artifacts"] = "written"
        if evaluation_result is None:
            try:
                evaluation_result = evaluate_job_directory(out_dir)
            except Exception:
                evaluation_result = None
        if evaluation_result is not None:
            rubric_path = out_dir / "rubric.json"
            merge_gate_path = out_dir / "merge_gate.json"
            classification_path = out_dir / "classification.json"

            accepted_at = result_payload.get("accepted_at")
            created_at: str | None = None
            if isinstance(accepted_at, str) and accepted_at.strip():
                created_at = accepted_at.strip()
            else:
                execution_payload = result_payload.get("execution")
                if isinstance(execution_payload, dict):
                    started_at = execution_payload.get("started_at")
                    if isinstance(started_at, str) and started_at.strip():
                        created_at = started_at.strip()
            try:
                classification = evaluation_result["classification"]
                rubric = evaluation_result["rubric"]
                merge_gate = evaluation_result["merge_gate"]
                record_job_evaluation(
                    job_id=str(evaluation_result["job_id"]),
                    repo=str(request_payload.get("repo", "")),
                    task_type=str(request_payload.get("task_type", "")),
                    provider=str(request_payload.get("provider", "")),
                    accepted_status=str(result_payload.get("status", "")),
                    declared_category=str(classification.get("declared_category", "")),
                    observed_category=str(classification.get("observed_category", "")),
                    merge_eligible=bool(rubric.get("merge_eligible", False)),
                    merge_gate_passed=bool(merge_gate.get("passed", False)),
                    created_at=created_at,
                    request_path=str(request_path),
                    result_path=str(result_path),
                    rubric_path=str(rubric_path) if rubric_path.exists() else None,
                    merge_gate_path=str(merge_gate_path) if merge_gate_path.exists() else None,
                    classification_path=(
                        str(classification_path) if classification_path.exists() else None
                    ),
                )
            except Exception:
                result_payload["persistence"]["ledger"] = "failed"
            else:
                result_payload["persistence"]["ledger"] = "written"

    _write_json(result_path, result_payload)

    print(f"dispatch_dir={out_dir}")
    print(f"request_path={request_path}")
    print(f"result_path={result_path}")
    print(f"status={result_payload['status']}")

    return 0 if result_payload["status"] == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())

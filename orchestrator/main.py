from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from adapters import get_registered_adapters, resolve_adapter
from orchestrator.config_loader import load_yaml_file
from orchestrator.job_evaluator import evaluate_job_directory
from orchestrator.job_evaluator import persist_evaluation_artifacts
from orchestrator.ledger import get_execution_target_by_identity
from orchestrator.ledger import get_merge_execution_by_candidate_idempotency_key
from orchestrator.ledger import get_rollback_execution_by_trace_id
from orchestrator.ledger import get_rollback_trace_by_id
from orchestrator.ledger import record_execution_target
from orchestrator.ledger import record_job_evaluation
from orchestrator.ledger import record_merge_execution_outcome
from orchestrator.ledger import record_merge_attempt_receipt
from orchestrator.ledger import record_rollback_execution_outcome
from orchestrator.ledger import record_rollback_traceability_for_candidate
from orchestrator.merge_executor import execute_constrained_merge
from orchestrator.rollback_executor import execute_constrained_rollback
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
    parser.add_argument("--target-ref", default="")
    parser.add_argument("--source-sha", default="")
    parser.add_argument("--base-sha", default="")
    parser.add_argument("--execute-merge", action="store_true")
    parser.add_argument("--execute-rollback", action="store_true")
    parser.add_argument("--rollback-trace-id", default="")
    parser.add_argument(
        "--validation-command",
        dest="validation_commands",
        action="append",
        default=[],
    )
    return parser


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _extract_merge_attempt_signal(result_payload: dict) -> dict | None:
    execution_payload = result_payload.get("execution")
    if not isinstance(execution_payload, dict):
        return None
    merge_attempt = execution_payload.get("merge_attempt")
    if not isinstance(merge_attempt, dict):
        return None

    status = str(merge_attempt.get("status", "")).strip()
    if status not in {"attempted", "succeeded", "failed", "skipped"}:
        return None

    attempted_at_raw = merge_attempt.get("attempted_at")
    attempted_at = (
        str(attempted_at_raw).strip() if attempted_at_raw is not None else None
    )
    if attempted_at == "":
        attempted_at = None

    result_sha_raw = merge_attempt.get("result_sha")
    result_sha = str(result_sha_raw).strip() if result_sha_raw is not None else None
    if result_sha == "":
        result_sha = None

    error_raw = merge_attempt.get("error")
    error = str(error_raw).strip() if error_raw is not None else None
    if error == "":
        error = None

    return {
        "status": status,
        "attempted_at": attempted_at,
        "result_sha": result_sha,
        "error": error,
    }


def main() -> int:
    args = _build_parser().parse_args()
    validation_commands = [
        str(command).strip() for command in args.validation_commands if str(command).strip()
    ]
    target_ref = str(args.target_ref).strip()
    source_sha = str(args.source_sha).strip()
    base_sha = str(args.base_sha).strip()
    rollback_trace_id = str(args.rollback_trace_id).strip()

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
    execution_target_metadata = {
        key: value
        for key, value in (
            ("target_ref", target_ref),
            ("source_sha", source_sha),
            ("base_sha", base_sha),
        )
        if value
    }
    if execution_target_metadata:
        request.metadata["execution_target"] = execution_target_metadata

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
        "execution_target": "skipped",
        "merge_execution": "skipped",
        "merge_receipt": "skipped",
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
            classification = evaluation_result["classification"]
            rubric = evaluation_result["rubric"]
            merge_gate = evaluation_result["merge_gate"]
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

            is_execution_candidate = bool(merge_gate.get("passed", False)) and bool(
                merge_gate.get("auto_merge_allowed", False)
            )
            has_execution_identity = bool(target_ref and source_sha and base_sha)
            if is_execution_candidate and has_execution_identity:
                try:
                    record_execution_target(
                        job_id=str(evaluation_result["job_id"]),
                        repo=str(request_payload.get("repo", "")),
                        target_ref=target_ref,
                        source_sha=source_sha,
                        base_sha=base_sha,
                        created_at=created_at,
                        declared_category=str(classification.get("declared_category", "")),
                        observed_category=str(classification.get("observed_category", "")),
                        accepted_status=str(result_payload.get("status", "")),
                        merge_gate_passed=bool(merge_gate.get("passed", False)),
                    )
                except Exception:
                    result_payload["persistence"]["execution_target"] = "failed"
                else:
                    result_payload["persistence"]["execution_target"] = "written"

            merge_attempt_signal: dict | None = None
            if args.execute_merge:
                result_payload["persistence"]["rollback_trace"] = "skipped"
                merge_receipt_id: str | None = None
                candidate_key_for_rollback_trace: str | None = None
                merge_execution_payload = {
                    "status": "skipped",
                    "attempted": False,
                    "attempted_at": None,
                    "candidate_idempotency_key": None,
                    "pre_merge_sha": None,
                    "post_merge_sha": None,
                    "merge_result_sha": None,
                    "error": "merge_execution_not_requested_or_not_eligible",
                    "rollback_trace": {
                        "recorded": False,
                        "eligible": None,
                        "ineligible_reason": None,
                        "rollback_trace_id": None,
                    },
                }
                if not has_execution_identity:
                    merge_execution_payload["error"] = "execution_target_identity_missing"
                    merge_execution_payload["rollback_trace"]["ineligible_reason"] = (
                        "execution_target_identity_missing"
                    )
                else:
                    persisted_target = get_execution_target_by_identity(
                        repo=str(request_payload.get("repo", "")),
                        target_ref=target_ref,
                        source_sha=source_sha,
                        base_sha=base_sha,
                    )
                    if persisted_target is None:
                        merge_execution_payload["error"] = (
                            "execution_target_not_persisted_or_mismatched"
                        )
                        merge_execution_payload["rollback_trace"]["ineligible_reason"] = (
                            "execution_target_not_persisted_or_mismatched"
                        )
                    else:
                        candidate_key = str(
                            persisted_target.get("candidate_idempotency_key", "")
                        ).strip()
                        merge_execution_payload["candidate_idempotency_key"] = candidate_key
                        candidate_key_for_rollback_trace = candidate_key
                        prior_merge_execution = get_merge_execution_by_candidate_idempotency_key(
                            candidate_key
                        )
                        if (
                            prior_merge_execution is not None
                            and str(prior_merge_execution.get("execution_status", "")).strip()
                            == "succeeded"
                        ):
                            merge_execution_payload["status"] = "skipped"
                            merge_execution_payload["error"] = "already_merged_for_candidate"
                            merge_execution_payload["attempted_at"] = prior_merge_execution.get(
                                "executed_at"
                            )
                            merge_execution_payload["pre_merge_sha"] = prior_merge_execution.get(
                                "pre_merge_sha"
                            )
                            merge_execution_payload["post_merge_sha"] = prior_merge_execution.get(
                                "post_merge_sha"
                            )
                            merge_execution_payload["merge_result_sha"] = prior_merge_execution.get(
                                "merge_result_sha"
                            )
                        else:
                            merge_outcome = execute_constrained_merge(
                                repo_path=str(args.execution_repo_path),
                                target_ref=target_ref,
                                source_sha=source_sha,
                                base_sha=base_sha,
                            )
                            merge_execution_payload.update(merge_outcome)

                        try:
                            record_merge_execution_outcome(
                                job_id=str(evaluation_result["job_id"]),
                                repo=str(request_payload.get("repo", "")),
                                target_ref=target_ref,
                                source_sha=source_sha,
                                base_sha=base_sha,
                                execution_status=str(merge_execution_payload.get("status", "skipped")),
                                executed_at=(
                                    str(merge_execution_payload.get("attempted_at"))
                                    if merge_execution_payload.get("attempted_at") is not None
                                    else None
                                ),
                                pre_merge_sha=(
                                    str(merge_execution_payload.get("pre_merge_sha"))
                                    if merge_execution_payload.get("pre_merge_sha") is not None
                                    else None
                                ),
                                post_merge_sha=(
                                    str(merge_execution_payload.get("post_merge_sha"))
                                    if merge_execution_payload.get("post_merge_sha") is not None
                                    else None
                                ),
                                merge_result_sha=(
                                    str(merge_execution_payload.get("merge_result_sha"))
                                    if merge_execution_payload.get("merge_result_sha") is not None
                                    else None
                                ),
                                merge_error=(
                                    str(merge_execution_payload.get("error"))
                                    if merge_execution_payload.get("error") is not None
                                    else None
                                ),
                            )
                        except Exception:
                            result_payload["persistence"]["merge_execution"] = "failed"
                        else:
                            result_payload["persistence"]["merge_execution"] = "written"

                        merge_attempt_signal = {
                            "status": str(merge_execution_payload.get("status", "skipped")),
                            "attempted_at": merge_execution_payload.get("attempted_at"),
                            "result_sha": merge_execution_payload.get("merge_result_sha"),
                            "error": merge_execution_payload.get("error"),
                        }

                execution_payload = result_payload.get("execution")
                if isinstance(execution_payload, dict):
                    execution_payload["merge_execution"] = merge_execution_payload

            if merge_attempt_signal is None:
                merge_attempt_signal = _extract_merge_attempt_signal(result_payload)

            if merge_attempt_signal is not None:
                if has_execution_identity:
                    try:
                        merge_receipt_id = record_merge_attempt_receipt(
                            job_id=str(evaluation_result["job_id"]),
                            repo=str(request_payload.get("repo", "")),
                            target_ref=target_ref,
                            source_sha=source_sha,
                            base_sha=base_sha,
                            merge_attempt_status=str(merge_attempt_signal["status"]),
                            merge_attempted_at=(
                                str(merge_attempt_signal["attempted_at"])
                                if merge_attempt_signal["attempted_at"] is not None
                                else None
                            ),
                            merge_result_sha=(
                                str(merge_attempt_signal["result_sha"])
                                if merge_attempt_signal["result_sha"] is not None
                                else None
                            ),
                            merge_error=(
                                str(merge_attempt_signal["error"])
                                if merge_attempt_signal["error"] is not None
                                else None
                            ),
                        )
                    except Exception:
                        result_payload["persistence"]["merge_receipt"] = "failed"
                    else:
                        result_payload["persistence"]["merge_receipt"] = "written"

            if (
                args.execute_merge
                and candidate_key_for_rollback_trace is not None
                and result_payload["persistence"].get("merge_execution") == "written"
            ):
                try:
                    rollback_trace_row = record_rollback_traceability_for_candidate(
                        candidate_idempotency_key=candidate_key_for_rollback_trace,
                        merge_receipt_id=merge_receipt_id,
                    )
                except Exception:
                    result_payload["persistence"]["rollback_trace"] = "failed"
                    merge_execution_payload["rollback_trace"]["recorded"] = False
                    merge_execution_payload["rollback_trace"]["eligible"] = False
                    merge_execution_payload["rollback_trace"]["ineligible_reason"] = (
                        "rollback_trace_persistence_failed"
                    )
                else:
                    result_payload["persistence"]["rollback_trace"] = "written"
                    rollback_eligible = bool(rollback_trace_row.get("rollback_eligible"))
                    merge_execution_payload["rollback_trace"]["recorded"] = True
                    merge_execution_payload["rollback_trace"]["eligible"] = rollback_eligible
                    merge_execution_payload["rollback_trace"]["rollback_trace_id"] = (
                        rollback_trace_row.get("rollback_trace_id")
                    )
                    merge_execution_payload["rollback_trace"]["ineligible_reason"] = (
                        rollback_trace_row.get("ineligible_reason")
                    )

            if args.execute_rollback:
                result_payload["persistence"]["rollback_execution"] = "skipped"
                rollback_execution_payload = {
                    "status": "skipped",
                    "attempted": False,
                    "attempted_at": None,
                    "rollback_trace_id": rollback_trace_id or None,
                    "candidate_idempotency_key": None,
                    "pre_merge_sha": None,
                    "post_merge_sha": None,
                    "current_head_sha": None,
                    "rollback_result_sha": None,
                    "consistency_check_passed": False,
                    "error": "rollback_execution_not_requested_or_not_eligible",
                }
                persisted_trace = None
                should_persist_rollback_execution = False
                if not rollback_trace_id:
                    rollback_execution_payload["error"] = "rollback_trace_id_required"
                else:
                    persisted_trace = get_rollback_trace_by_id(rollback_trace_id)
                    if persisted_trace is None:
                        rollback_execution_payload["error"] = "rollback_trace_not_found"
                    else:
                        should_persist_rollback_execution = True
                        rollback_execution_payload["rollback_trace_id"] = persisted_trace.get(
                            "rollback_trace_id"
                        )
                        rollback_execution_payload["candidate_idempotency_key"] = persisted_trace.get(
                            "candidate_idempotency_key"
                        )
                        rollback_execution_payload["pre_merge_sha"] = persisted_trace.get("pre_merge_sha")
                        rollback_execution_payload["post_merge_sha"] = persisted_trace.get(
                            "post_merge_sha"
                        )
                        trace_eligible = bool(persisted_trace.get("rollback_eligible"))
                        if not trace_eligible:
                            rollback_execution_payload["error"] = (
                                str(persisted_trace.get("ineligible_reason", "")).strip()
                                or "rollback_trace_not_eligible"
                            )
                        elif (
                            not str(persisted_trace.get("pre_merge_sha") or "").strip()
                            or not str(persisted_trace.get("post_merge_sha") or "").strip()
                        ):
                            rollback_execution_payload["error"] = (
                                "rollback_trace_linkage_incomplete"
                            )
                        elif str(persisted_trace.get("repo", "")).strip() != str(
                            request_payload.get("repo", "")
                        ).strip():
                            rollback_execution_payload["error"] = "rollback_trace_repo_mismatch"
                        else:
                            prior_rollback_execution = get_rollback_execution_by_trace_id(
                                str(persisted_trace.get("rollback_trace_id", ""))
                            )
                            if (
                                prior_rollback_execution is not None
                                and str(
                                    prior_rollback_execution.get("execution_status", "")
                                ).strip()
                                == "succeeded"
                            ):
                                rollback_execution_payload["status"] = "skipped"
                                rollback_execution_payload["error"] = "already_rolled_back_for_trace"
                                rollback_execution_payload["attempted_at"] = prior_rollback_execution.get(
                                    "attempted_at"
                                )
                                rollback_execution_payload["current_head_sha"] = (
                                    prior_rollback_execution.get("current_head_sha")
                                )
                                rollback_execution_payload["rollback_result_sha"] = (
                                    prior_rollback_execution.get("rollback_result_sha")
                                )
                                rollback_execution_payload["consistency_check_passed"] = bool(
                                    prior_rollback_execution.get("consistency_check_passed")
                                )
                            else:
                                rollback_outcome = execute_constrained_rollback(
                                    repo_path=str(args.execution_repo_path),
                                    target_ref=str(persisted_trace.get("target_ref", "")),
                                    pre_merge_sha=str(persisted_trace.get("pre_merge_sha", "")),
                                    post_merge_sha=str(persisted_trace.get("post_merge_sha", "")),
                                )
                                rollback_execution_payload.update(rollback_outcome)

                if should_persist_rollback_execution and persisted_trace is not None:
                    try:
                        record_rollback_execution_outcome(
                            rollback_trace_id=str(persisted_trace.get("rollback_trace_id", "")),
                            execution_status=str(rollback_execution_payload.get("status", "skipped")),
                            attempted_at=(
                                str(rollback_execution_payload.get("attempted_at"))
                                if rollback_execution_payload.get("attempted_at") is not None
                                else None
                            ),
                            current_head_sha=(
                                str(rollback_execution_payload.get("current_head_sha"))
                                if rollback_execution_payload.get("current_head_sha") is not None
                                else None
                            ),
                            rollback_result_sha=(
                                str(rollback_execution_payload.get("rollback_result_sha"))
                                if rollback_execution_payload.get("rollback_result_sha") is not None
                                else None
                            ),
                            rollback_error=(
                                str(rollback_execution_payload.get("error"))
                                if rollback_execution_payload.get("error") is not None
                                else None
                            ),
                            consistency_check_passed=bool(
                                rollback_execution_payload.get("consistency_check_passed")
                            ),
                        )
                    except Exception:
                        result_payload["persistence"]["rollback_execution"] = "failed"
                    else:
                        result_payload["persistence"]["rollback_execution"] = "written"

                execution_payload = result_payload.get("execution")
                if isinstance(execution_payload, dict):
                    execution_payload["rollback_execution"] = rollback_execution_payload

    _write_json(result_path, result_payload)

    print(f"dispatch_dir={out_dir}")
    print(f"request_path={request_path}")
    print(f"result_path={result_path}")
    print(f"status={result_payload['status']}")

    return 0 if result_payload["status"] == "accepted" else 1


if __name__ == "__main__":
    raise SystemExit(main())

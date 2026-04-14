from __future__ import annotations

import argparse
from datetime import datetime
from datetime import timezone
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orchestrator.ledger import DEFAULT_LEDGER_DB_PATH  # noqa: E402
from orchestrator.ledger import get_job_by_id  # noqa: E402
from orchestrator.ledger import get_rollback_execution_by_trace_id  # noqa: E402
from orchestrator.ledger import get_rollback_trace_by_id  # noqa: E402
from orchestrator.ledger import get_rollback_trace_by_job_id  # noqa: E402
from orchestrator.ledger import record_rollback_execution_outcome  # noqa: E402
from orchestrator.rollback_executor import execute_constrained_rollback  # noqa: E402

DEFAULT_REVIEW_DECISION_LOG_PATH = "state/operator_review_decisions.jsonl"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Record explicit local operator review decision "
            "(local-first, explicit human action only)"
        ),
        epilog=(
            "Primary flow (recommended):\n"
            "  python scripts/operator_review_decision.py --job-id <job_id> --decision keep\n"
            "  python scripts/operator_review_decision.py --job-id <job_id> --decision rollback "
            "--execution-repo-path /path/to/repo\n"
            "  python scripts/operator_review_decision.py --job-id <job_id> --decision retry\n"
            "  python scripts/operator_review_decision.py --job-id <job_id> --decision escalate\n\n"
            "Advanced direct-trace flow:\n"
            "  python scripts/operator_review_decision.py --rollback-trace-id <trace_id> "
            "--decision rollback --execution-repo-path /path/to/repo"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument(
        "--job-id",
        help="Primary operator target: recorded job id to review.",
    )
    selector.add_argument(
        "--rollback-trace-id",
        help="Advanced direct target: persisted rollback trace id.",
    )
    parser.add_argument(
        "--decision",
        required=True,
        choices=("keep", "rollback", "retry", "escalate"),
        help=(
            "Explicit human decision. "
            "'keep' is bookkeeping-only (no execution). "
            "'rollback' requests existing constrained rollback with guardrails. "
            "'retry'/'escalate' are representation-only bookkeeping decisions."
        ),
    )
    parser.add_argument("--db-path", default=DEFAULT_LEDGER_DB_PATH)
    parser.add_argument("--execution-repo-path", default=".")
    parser.add_argument("--decision-log-path", default=DEFAULT_REVIEW_DECISION_LOG_PATH)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return False


def _append_decision_record(path: str, record: dict[str, Any]) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
        handle.write("\n")


def _decision_effect(decision: str) -> str:
    mapping = {
        "keep": "bookkeeping_only_no_execution",
        "rollback": "rollback_requested_guardrails_apply",
        "retry": "bookkeeping_only_retry_requested_no_execution",
        "escalate": "bookkeeping_only_escalation_requested_no_execution",
    }
    return mapping.get(str(decision).strip().lower(), "unsupported_decision")


def _resolve_target(
    *,
    job_id: str | None,
    rollback_trace_id: str | None,
    db_path: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, str | None]:
    resolved_job = None
    resolved_trace = None

    if rollback_trace_id:
        resolved_trace = get_rollback_trace_by_id(str(rollback_trace_id).strip(), db_path=db_path)
        if resolved_trace is not None:
            trace_job_id = str(resolved_trace.get("job_id", "")).strip()
            if trace_job_id:
                resolved_job = get_job_by_id(trace_job_id, db_path=db_path)
    elif job_id:
        resolved_job = get_job_by_id(str(job_id).strip(), db_path=db_path)
        if resolved_job is not None:
            resolved_trace = get_rollback_trace_by_job_id(
                str(resolved_job.get("job_id", "")).strip(),
                db_path=db_path,
            )

    if resolved_job is not None:
        repo = str(resolved_job.get("repo", "")).strip() or None
    elif resolved_trace is not None:
        repo = str(resolved_trace.get("repo", "")).strip() or None
    else:
        repo = None

    return resolved_job, resolved_trace, repo


def apply_operator_decision(
    *,
    decision: str,
    db_path: str,
    execution_repo_path: str,
    decision_log_path: str,
    job_id: str | None = None,
    rollback_trace_id: str | None = None,
) -> dict[str, Any]:
    normalized_decision = str(decision).strip().lower()
    decided_at = _now_utc_iso()

    resolved_job, resolved_trace, repo = _resolve_target(
        job_id=job_id,
        rollback_trace_id=rollback_trace_id,
        db_path=db_path,
    )

    resolved_job_id = (
        str(resolved_job.get("job_id", "")).strip() if resolved_job is not None else str(job_id or "").strip() or None
    )
    resolved_trace_id = (
        str(resolved_trace.get("rollback_trace_id", "")).strip()
        if resolved_trace is not None
        else str(rollback_trace_id or "").strip() or None
    )

    outcome: dict[str, Any] = {
        "decided_at": decided_at,
        "decision": normalized_decision,
        "target_mode": "rollback_trace_id" if rollback_trace_id else "job_id",
        "job_id": resolved_job_id,
        "rollback_trace_id": resolved_trace_id,
        "repo": repo,
        "decision_status": "recorded",
        "decision_error": None,
        "decision_effect": _decision_effect(normalized_decision),
        "decision_log": "skipped",
        "rollback_execution": {
            "status": "not_requested",
            "attempted": False,
            "attempted_at": None,
            "current_head_sha": None,
            "rollback_result_sha": None,
            "consistency_check_passed": False,
            "error": None,
            "persistence": "skipped",
        },
    }

    if resolved_job is None and resolved_trace is None:
        outcome["decision_status"] = "failed"
        if job_id:
            outcome["decision_error"] = f"job_not_found: {job_id}"
        elif rollback_trace_id:
            outcome["decision_error"] = f"rollback_trace_not_found: {rollback_trace_id}"
        else:
            outcome["decision_error"] = "target_not_found"

    elif normalized_decision in {"keep", "retry", "escalate"}:
        # Explicit keep/retry/escalate are human decision records only.
        # They do not trigger merge, rollback, redispatch, or any downstream execution.
        pass

    elif normalized_decision == "rollback":
        if resolved_trace is None:
            outcome["decision_status"] = "failed"
            outcome["decision_error"] = "rollback_trace_required_for_rollback_decision"
            outcome["rollback_execution"]["status"] = "skipped"
            outcome["rollback_execution"]["error"] = "rollback_trace_required_for_rollback_decision"
        else:
            trace_id = str(resolved_trace.get("rollback_trace_id", "")).strip()
            trace_eligible = _as_bool(resolved_trace.get("rollback_eligible"))
            trace_reason = str(resolved_trace.get("ineligible_reason", "")).strip() or None
            pre_merge_sha = str(resolved_trace.get("pre_merge_sha", "")).strip()
            post_merge_sha = str(resolved_trace.get("post_merge_sha", "")).strip()
            target_ref = str(resolved_trace.get("target_ref", "")).strip()

            rollback_execution_payload: dict[str, Any] = {
                "status": "skipped",
                "attempted": False,
                "attempted_at": None,
                "current_head_sha": None,
                "rollback_result_sha": None,
                "consistency_check_passed": False,
                "error": "rollback_execution_not_requested_or_not_eligible",
                "persistence": "skipped",
            }

            prior = get_rollback_execution_by_trace_id(trace_id, db_path=db_path)
            if prior is not None and str(prior.get("execution_status", "")).strip() == "succeeded":
                rollback_execution_payload["status"] = "skipped"
                rollback_execution_payload["error"] = "already_rolled_back_for_trace"
                rollback_execution_payload["attempted_at"] = prior.get("attempted_at")
                rollback_execution_payload["current_head_sha"] = prior.get("current_head_sha")
                rollback_execution_payload["rollback_result_sha"] = prior.get("rollback_result_sha")
                rollback_execution_payload["consistency_check_passed"] = _as_bool(
                    prior.get("consistency_check_passed")
                )
            elif not trace_eligible:
                rollback_execution_payload["status"] = "skipped"
                rollback_execution_payload["error"] = trace_reason or "rollback_trace_not_eligible"
            elif not pre_merge_sha or not post_merge_sha:
                rollback_execution_payload["status"] = "skipped"
                rollback_execution_payload["error"] = "rollback_trace_linkage_incomplete"
            else:
                rollback_execution_payload = execute_constrained_rollback(
                    repo_path=str(execution_repo_path),
                    target_ref=target_ref,
                    pre_merge_sha=pre_merge_sha,
                    post_merge_sha=post_merge_sha,
                )

            try:
                record_rollback_execution_outcome(
                    rollback_trace_id=trace_id,
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
                    consistency_check_passed=_as_bool(
                        rollback_execution_payload.get("consistency_check_passed")
                    ),
                    db_path=db_path,
                )
            except Exception as exc:
                rollback_execution_payload["persistence"] = "failed"
                outcome["decision_status"] = "failed"
                outcome["decision_error"] = f"rollback_execution_persistence_failed: {exc}"
            else:
                rollback_execution_payload["persistence"] = "written"

            outcome["rollback_execution"] = rollback_execution_payload

    else:
        outcome["decision_status"] = "failed"
        outcome["decision_error"] = f"unsupported_decision: {normalized_decision}"

    decision_record = {
        "decided_at": outcome["decided_at"],
        "decision": outcome["decision"],
        "decision_effect": outcome.get("decision_effect"),
        "target_mode": outcome.get("target_mode"),
        "job_id": outcome["job_id"],
        "rollback_trace_id": outcome["rollback_trace_id"],
        "repo": outcome["repo"],
        "decision_status": outcome["decision_status"],
        "decision_error": outcome["decision_error"],
        "rollback_execution_status": outcome["rollback_execution"]["status"],
        "rollback_execution_error": outcome["rollback_execution"].get("error"),
    }
    try:
        _append_decision_record(decision_log_path, decision_record)
    except Exception as exc:
        outcome["decision_log"] = "failed"
        if outcome["decision_status"] == "recorded":
            outcome["decision_status"] = "failed"
            outcome["decision_error"] = f"decision_log_write_failed: {exc}"
    else:
        outcome["decision_log"] = "written"

    return outcome


def _format_human(outcome: dict[str, Any]) -> str:
    rollback = outcome.get("rollback_execution")
    rollback_status = rollback.get("status") if isinstance(rollback, dict) else None
    rollback_attempted = rollback.get("attempted") if isinstance(rollback, dict) else None
    rollback_error = rollback.get("error") if isinstance(rollback, dict) else None
    return "\n".join(
        [
            f"decision: {outcome.get('decision')}",
            f"target_mode: {outcome.get('target_mode')}",
            f"job_id: {outcome.get('job_id')}",
            f"rollback_trace_id: {outcome.get('rollback_trace_id')}",
            f"repo: {outcome.get('repo')}",
            f"decision_status: {outcome.get('decision_status')}",
            f"decision_error: {outcome.get('decision_error')}",
            f"decision_effect: {outcome.get('decision_effect')}",
            f"decision_log: {outcome.get('decision_log')}",
            f"rollback_status: {rollback_status}",
            f"rollback_attempted: {rollback_attempted}",
            f"rollback_error: {rollback_error}",
        ]
    )


def _exit_code_from_outcome(outcome: dict[str, Any]) -> int:
    if str(outcome.get("decision_status", "")).strip() == "failed":
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    outcome = apply_operator_decision(
        decision=str(args.decision),
        db_path=str(args.db_path),
        execution_repo_path=str(args.execution_repo_path),
        decision_log_path=str(args.decision_log_path),
        job_id=str(args.job_id).strip() if args.job_id else None,
        rollback_trace_id=(
            str(args.rollback_trace_id).strip() if args.rollback_trace_id else None
        ),
    )

    if args.as_json:
        print(json.dumps(outcome, ensure_ascii=False, sort_keys=True))
    else:
        print(_format_human(outcome))

    return _exit_code_from_outcome(outcome)


if __name__ == "__main__":
    raise SystemExit(main())

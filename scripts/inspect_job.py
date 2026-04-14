from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orchestrator.ledger import DEFAULT_LEDGER_DB_PATH  # noqa: E402
from orchestrator.ledger import get_rollback_execution_by_job_id  # noqa: E402
from orchestrator.ledger import get_job_by_id  # noqa: E402
from orchestrator.ledger import get_latest_job  # noqa: E402
from orchestrator.ledger import get_rollback_trace_by_job_id  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect a recorded orchestration job")
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--job-id")
    selector.add_argument("--latest", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--db-path", default=DEFAULT_LEDGER_DB_PATH)
    return parser


def _as_optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes"}:
            return True
        if normalized in {"0", "false", "no"}:
            return False
    return None


def _read_fail_reasons(path_value: Any) -> list[str]:
    if not isinstance(path_value, str) or not path_value.strip():
        return []
    path = Path(path_value)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    raw = payload.get("fail_reasons")
    if not isinstance(raw, (list, tuple)):
        return []
    return [str(item) for item in raw]


def _read_json_object(path_value: Any) -> dict[str, Any] | None:
    if not isinstance(path_value, str) or not path_value.strip():
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _read_retry_metadata(machine_review_payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(machine_review_payload, dict):
        return {
            "retry_recommended": None,
            "retry_basis": [],
            "retry_blockers": [],
        }

    raw = machine_review_payload.get("retry_metadata")
    if not isinstance(raw, dict):
        return {
            "retry_recommended": None,
            "retry_basis": [],
            "retry_blockers": [],
        }

    raw_retry_recommended = raw.get("retry_recommended")
    retry_recommended = (
        _as_optional_bool(raw_retry_recommended)
        if raw_retry_recommended is not None
        else None
    )
    raw_retry_basis = raw.get("retry_basis")
    retry_basis = (
        [str(item) for item in raw_retry_basis]
        if isinstance(raw_retry_basis, (list, tuple))
        else []
    )
    raw_retry_blockers = raw.get("retry_blockers")
    retry_blockers = (
        [str(item) for item in raw_retry_blockers]
        if isinstance(raw_retry_blockers, (list, tuple))
        else []
    )
    return {
        "retry_recommended": retry_recommended,
        "retry_basis": retry_basis,
        "retry_blockers": retry_blockers,
    }


def _derive_recommendation_advisory(
    machine_review_payload: dict[str, Any] | None,
    *,
    retry_metadata: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(machine_review_payload, dict):
        return {
            "display_recommendation": None,
            "decision_confidence": None,
            "operator_attention_flags": [],
            "execution_allowed": False,
        }

    raw_recommendation = machine_review_payload.get("recommended_action")
    display_recommendation = (
        str(raw_recommendation).strip().lower()
        if raw_recommendation is not None
        else ""
    )
    if display_recommendation not in {"keep", "rollback", "retry", "escalate"}:
        display_recommendation = None

    requires_human_review = _as_optional_bool(
        machine_review_payload.get("requires_human_review")
    )
    policy_reasons_raw = machine_review_payload.get("policy_reasons")
    policy_reasons = (
        [str(item) for item in policy_reasons_raw]
        if isinstance(policy_reasons_raw, (list, tuple))
        else []
    )
    retry_basis = [
        str(item) for item in retry_metadata.get("retry_basis", [])
    ] if isinstance(retry_metadata.get("retry_basis"), (list, tuple)) else []
    retry_blockers = [
        str(item) for item in retry_metadata.get("retry_blockers", [])
    ] if isinstance(retry_metadata.get("retry_blockers"), (list, tuple)) else []

    operator_attention_flags: list[str] = []
    for tag in [*policy_reasons, *retry_basis, *retry_blockers]:
        if tag and tag not in operator_attention_flags:
            operator_attention_flags.append(tag)

    decision_confidence: str | None
    if display_recommendation is None:
        decision_confidence = None
    elif requires_human_review is True:
        decision_confidence = "low"
    elif display_recommendation == "retry":
        retry_recommended = retry_metadata.get("retry_recommended")
        if retry_recommended is True:
            decision_confidence = "medium" if not retry_blockers else "low"
        elif retry_recommended is False:
            decision_confidence = "low"
        else:
            decision_confidence = None
    elif display_recommendation in {"keep", "rollback"}:
        decision_confidence = "medium"
    else:
        decision_confidence = "low"

    return {
        "display_recommendation": display_recommendation,
        "decision_confidence": decision_confidence,
        "operator_attention_flags": operator_attention_flags,
        "execution_allowed": False,
    }


def _derive_execution_bridge(
    machine_review_payload: dict[str, Any] | None,
    *,
    retry_metadata: dict[str, Any],
    advisory: dict[str, Any],
) -> dict[str, Any]:
    policy_reasons = []
    if isinstance(machine_review_payload, dict):
        raw_policy_reasons = machine_review_payload.get("policy_reasons")
        if isinstance(raw_policy_reasons, (list, tuple)):
            policy_reasons = [str(item) for item in raw_policy_reasons]

    retry_blockers = []
    raw_retry_blockers = retry_metadata.get("retry_blockers")
    if isinstance(raw_retry_blockers, (list, tuple)):
        retry_blockers = [str(item) for item in raw_retry_blockers]

    advisory_flags = []
    raw_advisory_flags = advisory.get("operator_attention_flags")
    if isinstance(raw_advisory_flags, (list, tuple)):
        advisory_flags = [str(item) for item in raw_advisory_flags]

    blockers: list[str] = []
    for tag in [*policy_reasons, *retry_blockers, *advisory_flags]:
        if tag and tag not in blockers:
            blockers.append(tag)

    # Current repository posture is explicitly human-gated and non-executing.
    for foundational_blocker in (
        "explicit_operator_gate_required",
        "execution_not_implemented",
    ):
        if foundational_blocker not in blockers:
            blockers.append(foundational_blocker)

    return {
        "eligible_for_bounded_execution": False,
        "eligibility_basis": [],
        "eligibility_blockers": blockers,
        "requires_explicit_operator_decision": True,
    }


def _build_output(row: dict[str, Any], *, db_path: str) -> dict[str, Any]:
    rubric_path = row.get("rubric_path")
    merge_gate_path = row.get("merge_gate_path")
    rollback_trace = get_rollback_trace_by_job_id(
        str(row.get("job_id", "")),
        db_path=db_path,
    )
    rollback_execution = get_rollback_execution_by_job_id(
        str(row.get("job_id", "")),
        db_path=db_path,
    )
    machine_review_payload_path_value = row.get("machine_review_payload_path")
    machine_review_payload_path = (
        str(machine_review_payload_path_value).strip()
        if isinstance(machine_review_payload_path_value, str)
        else ""
    )
    machine_review_recorded = machine_review_payload_path != ""
    machine_review_payload = (
        _read_json_object(machine_review_payload_path)
        if machine_review_recorded
        else None
    )
    retry_metadata = _read_retry_metadata(machine_review_payload)
    advisory = _derive_recommendation_advisory(
        machine_review_payload,
        retry_metadata=retry_metadata,
    )
    execution_bridge = _derive_execution_bridge(
        machine_review_payload,
        retry_metadata=retry_metadata,
        advisory=advisory,
    )
    return {
        "job_id": row.get("job_id"),
        "repo": row.get("repo"),
        "task_type": row.get("task_type"),
        "provider": row.get("provider"),
        "accepted_status": row.get("accepted_status"),
        "declared_category": row.get("declared_category"),
        "observed_category": row.get("observed_category"),
        "merge_eligible": _as_optional_bool(row.get("merge_eligible")),
        "merge_gate_passed": _as_optional_bool(row.get("merge_gate_passed")),
        "created_at": row.get("created_at"),
        "paths": {
            "request": row.get("request_path"),
            "result": row.get("result_path"),
            "rubric": rubric_path,
            "merge_gate": merge_gate_path,
            "machine_review_payload": (
                machine_review_payload_path
                if machine_review_recorded
                else None
            ),
        },
        "fail_reasons": {
            "rubric": _read_fail_reasons(rubric_path),
            "merge_gate": _read_fail_reasons(merge_gate_path),
        },
        "rollback_trace": {
            "recorded": rollback_trace is not None,
            "rollback_trace_id": rollback_trace.get("rollback_trace_id") if rollback_trace else None,
            "rollback_eligible": (
                _as_optional_bool(rollback_trace.get("rollback_eligible"))
                if rollback_trace
                else None
            ),
            "ineligible_reason": rollback_trace.get("ineligible_reason") if rollback_trace else None,
            "pre_merge_sha": rollback_trace.get("pre_merge_sha") if rollback_trace else None,
            "post_merge_sha": rollback_trace.get("post_merge_sha") if rollback_trace else None,
        },
        "rollback_execution": {
            "recorded": rollback_execution is not None,
            "status": rollback_execution.get("execution_status") if rollback_execution else None,
            "attempted_at": rollback_execution.get("attempted_at") if rollback_execution else None,
            "rollback_result_sha": (
                rollback_execution.get("rollback_result_sha") if rollback_execution else None
            ),
            "rollback_error": rollback_execution.get("rollback_error") if rollback_execution else None,
        },
        "machine_review": {
            "recorded": machine_review_recorded,
            "recommended_action": (
                machine_review_payload.get("recommended_action")
                if machine_review_payload is not None
                else None
            ),
            "policy_version": (
                machine_review_payload.get("policy_version")
                if machine_review_payload is not None
                else None
            ),
            "policy_reasons": (
                machine_review_payload.get("policy_reasons")
                if machine_review_payload is not None
                else []
            ),
            "requires_human_review": (
                _as_optional_bool(machine_review_payload.get("requires_human_review"))
                if machine_review_payload is not None
                else None
            ),
            "retry_metadata": retry_metadata,
            "advisory": advisory,
            "execution_bridge": execution_bridge,
        },
    }


def _fmt(value: Any) -> str:
    if value is None:
        return "<missing>"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _format_human(output: dict[str, Any]) -> str:
    lines = [
        f"job_id: {_fmt(output.get('job_id'))}",
        f"repo: {_fmt(output.get('repo'))}",
        f"task_type: {_fmt(output.get('task_type'))}",
        f"provider: {_fmt(output.get('provider'))}",
        f"accepted_status: {_fmt(output.get('accepted_status'))}",
        f"declared_category: {_fmt(output.get('declared_category'))}",
        f"observed_category: {_fmt(output.get('observed_category'))}",
        f"merge_eligible: {_fmt(output.get('merge_eligible'))}",
        f"merge_gate_passed: {_fmt(output.get('merge_gate_passed'))}",
        f"created_at: {_fmt(output.get('created_at'))}",
        f"request_path: {_fmt(output['paths'].get('request'))}",
        f"result_path: {_fmt(output['paths'].get('result'))}",
        f"rubric_path: {_fmt(output['paths'].get('rubric'))}",
        f"merge_gate_path: {_fmt(output['paths'].get('merge_gate'))}",
        f"machine_review_payload_path: {_fmt(output['paths'].get('machine_review_payload'))}",
        "rubric_fail_reasons: "
        + (", ".join(output["fail_reasons"]["rubric"]) if output["fail_reasons"]["rubric"] else "none"),
        "merge_gate_fail_reasons: "
        + (
            ", ".join(output["fail_reasons"]["merge_gate"])
            if output["fail_reasons"]["merge_gate"]
            else "none"
        ),
        f"rollback_trace_recorded: {_fmt(output['rollback_trace'].get('recorded'))}",
        f"rollback_eligible: {_fmt(output['rollback_trace'].get('rollback_eligible'))}",
        f"rollback_ineligible_reason: {_fmt(output['rollback_trace'].get('ineligible_reason'))}",
        f"rollback_pre_merge_sha: {_fmt(output['rollback_trace'].get('pre_merge_sha'))}",
        f"rollback_post_merge_sha: {_fmt(output['rollback_trace'].get('post_merge_sha'))}",
        f"rollback_execution_recorded: {_fmt(output['rollback_execution'].get('recorded'))}",
        f"rollback_execution_status: {_fmt(output['rollback_execution'].get('status'))}",
        f"rollback_result_sha: {_fmt(output['rollback_execution'].get('rollback_result_sha'))}",
        f"rollback_error: {_fmt(output['rollback_execution'].get('rollback_error'))}",
        f"machine_review_recorded: {_fmt(output['machine_review'].get('recorded'))}",
        f"recommended_action: {_fmt(output['machine_review'].get('recommended_action'))}",
        f"policy_version: {_fmt(output['machine_review'].get('policy_version'))}",
        "policy_reasons: "
        + (
            ", ".join([str(v) for v in output["machine_review"].get("policy_reasons", [])])
            if output["machine_review"].get("policy_reasons")
            else "none"
        ),
        f"requires_human_review: {_fmt(output['machine_review'].get('requires_human_review'))}",
        f"retry_recommended: {_fmt(output['machine_review']['retry_metadata'].get('retry_recommended'))}",
        "retry_basis: "
        + (
            ", ".join(
                [str(v) for v in output["machine_review"]["retry_metadata"].get("retry_basis", [])]
            )
            if output["machine_review"]["retry_metadata"].get("retry_basis")
            else "none"
        ),
        "retry_blockers: "
        + (
            ", ".join(
                [
                    str(v)
                    for v in output["machine_review"]["retry_metadata"].get(
                        "retry_blockers", []
                    )
                ]
            )
            if output["machine_review"]["retry_metadata"].get("retry_blockers")
            else "none"
        ),
        f"advisory_display_recommendation: {_fmt(output['machine_review']['advisory'].get('display_recommendation'))}",
        f"advisory_decision_confidence: {_fmt(output['machine_review']['advisory'].get('decision_confidence'))}",
        "advisory_attention_flags: "
        + (
            ", ".join(
                [
                    str(v)
                    for v in output["machine_review"]["advisory"].get(
                        "operator_attention_flags", []
                    )
                ]
            )
            if output["machine_review"]["advisory"].get("operator_attention_flags")
            else "none"
        ),
        f"advisory_execution_allowed: {_fmt(output['machine_review']['advisory'].get('execution_allowed'))}",
        "execution_bridge_eligible_for_bounded_execution: "
        + _fmt(output["machine_review"]["execution_bridge"].get("eligible_for_bounded_execution")),
        "execution_bridge_eligibility_basis: "
        + (
            ", ".join(
                [
                    str(v)
                    for v in output["machine_review"]["execution_bridge"].get(
                        "eligibility_basis", []
                    )
                ]
            )
            if output["machine_review"]["execution_bridge"].get("eligibility_basis")
            else "none"
        ),
        "execution_bridge_eligibility_blockers: "
        + (
            ", ".join(
                [
                    str(v)
                    for v in output["machine_review"]["execution_bridge"].get(
                        "eligibility_blockers", []
                    )
                ]
            )
            if output["machine_review"]["execution_bridge"].get("eligibility_blockers")
            else "none"
        ),
        "execution_bridge_requires_explicit_operator_decision: "
        + _fmt(
            output["machine_review"]["execution_bridge"].get(
                "requires_explicit_operator_decision"
            )
        ),
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.latest:
        row = get_latest_job(db_path=args.db_path)
        if row is None:
            print("No recorded jobs found in ledger.", file=sys.stderr)
            return 1
    else:
        row = get_job_by_id(args.job_id, db_path=args.db_path)
        if row is None:
            print(f"Job not found: {args.job_id}", file=sys.stderr)
            return 1

    output = _build_output(row, db_path=str(args.db_path))
    if args.as_json:
        print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    else:
        print(_format_human(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

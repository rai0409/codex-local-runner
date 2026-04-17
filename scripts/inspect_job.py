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


def _default_replan_input() -> dict[str, Any]:
    return {
        "failure_type": None,
        "current_state": None,
        "lifecycle_state": None,
        "write_authority_state": None,
        "category": None,
        "changed_files": [],
        "prior_attempt_count": None,
        "retry_budget_total": None,
        "retry_budget_remaining": None,
        "budget_exhausted": None,
        "primary_fail_reasons": [],
        "retry_recommendation": None,
        "next_action_readiness": None,
        "retry_recommended": None,
        "escalation_required": None,
        "retriable_failure_type": None,
        "retriable_failure_types": [],
    }


def _default_write_authority_surface() -> dict[str, Any]:
    return {
        "state": None,
        "allowed_categories": [],
    }


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    normalized: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized


def _read_replan_input(path_value: Any) -> dict[str, Any]:
    payload = _read_json_object(path_value)
    if not isinstance(payload, dict):
        return _default_replan_input()

    raw = payload.get("replan_input")
    if not isinstance(raw, dict):
        return _default_replan_input()

    result = _default_replan_input()
    for key in (
        "failure_type",
        "current_state",
        "lifecycle_state",
        "write_authority_state",
        "category",
        "retry_recommendation",
        "next_action_readiness",
    ):
        if raw.get(key) is not None:
            text = str(raw.get(key)).strip()
            result[key] = text if text else None

    for key in (
        "prior_attempt_count",
        "retry_budget_total",
        "retry_budget_remaining",
    ):
        value = raw.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            result[key] = value
        elif isinstance(value, str) and value.strip().isdigit():
            result[key] = int(value.strip())

    for key in (
        "budget_exhausted",
        "retry_recommended",
        "escalation_required",
        "retriable_failure_type",
    ):
        result[key] = _as_optional_bool(raw.get(key))

    changed_files = raw.get("changed_files")
    if isinstance(changed_files, (list, tuple)):
        result["changed_files"] = [str(item) for item in changed_files]

    primary_fail_reasons = raw.get("primary_fail_reasons")
    if isinstance(primary_fail_reasons, (list, tuple)):
        result["primary_fail_reasons"] = [str(item) for item in primary_fail_reasons]

    retriable_failure_types = raw.get("retriable_failure_types")
    if isinstance(retriable_failure_types, (list, tuple)):
        result["retriable_failure_types"] = [str(item) for item in retriable_failure_types]

    return result


def _read_merge_gate_contract(
    path_value: Any,
    *,
    replan_input: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _read_json_object(path_value)
    normalized_replan = replan_input if isinstance(replan_input, dict) else _default_replan_input()

    lifecycle_state: str | None = None
    write_authority = _default_write_authority_surface()
    if isinstance(payload, dict):
        raw_lifecycle_state = payload.get("lifecycle_state")
        if raw_lifecycle_state is not None:
            text = str(raw_lifecycle_state).strip()
            lifecycle_state = text if text else None

        raw_write_authority = payload.get("write_authority")
        if isinstance(raw_write_authority, dict):
            raw_state = raw_write_authority.get("state")
            if raw_state is not None:
                text = str(raw_state).strip()
                write_authority["state"] = text if text else None
            write_authority["allowed_categories"] = _normalize_string_list(
                raw_write_authority.get("allowed_categories")
            )

    return {
        "lifecycle_state": lifecycle_state,
        "write_authority": write_authority,
        "failure_type": normalized_replan.get("failure_type"),
        "retry_recommended": _as_optional_bool(normalized_replan.get("retry_recommended")),
        "retry_recommendation": normalized_replan.get("retry_recommendation"),
        "retry_budget_remaining": normalized_replan.get("retry_budget_remaining"),
        "escalation_required": _as_optional_bool(normalized_replan.get("escalation_required")),
        "next_action_readiness": normalized_replan.get("next_action_readiness"),
        "primary_fail_reasons": _normalize_string_list(
            normalized_replan.get("primary_fail_reasons")
        ),
    }


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


def _read_recovery_policy(machine_review_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(machine_review_payload, dict):
        return None

    if isinstance(machine_review_payload.get("recovery_policy"), dict):
        return dict(machine_review_payload["recovery_policy"])

    required = (
        "score_total",
        "dimension_scores",
        "failure_codes",
        "recovery_decision",
        "decision_basis",
        "requires_human_review",
    )
    if not all(key in machine_review_payload for key in required):
        return None

    return {
        "score_total": machine_review_payload.get("score_total"),
        "dimension_scores": machine_review_payload.get("dimension_scores"),
        "failure_codes": machine_review_payload.get("failure_codes"),
        "recovery_decision": machine_review_payload.get("recovery_decision"),
        "decision_basis": machine_review_payload.get("decision_basis"),
        "requires_human_review": machine_review_payload.get("requires_human_review"),
    }


def _policy_reasons(machine_review_payload: dict[str, Any] | None) -> list[str]:
    if not isinstance(machine_review_payload, dict):
        return []
    raw_policy_reasons = machine_review_payload.get("policy_reasons")
    if isinstance(raw_policy_reasons, (list, tuple)):
        return [str(item) for item in raw_policy_reasons]
    recovery_policy = _read_recovery_policy(machine_review_payload)
    if isinstance(recovery_policy, dict):
        raw_failure_codes = recovery_policy.get("failure_codes")
        if isinstance(raw_failure_codes, (list, tuple)):
            return [str(item) for item in raw_failure_codes]
    return []


def _display_recommendation(machine_review_payload: dict[str, Any] | None) -> str | None:
    if not isinstance(machine_review_payload, dict):
        return None
    raw = machine_review_payload.get("recovery_decision")
    if raw is None:
        raw = machine_review_payload.get("recommended_action")
    normalized = str(raw).strip().lower() if raw is not None else ""
    if normalized in {
        "keep",
        "revise_current_state",
        "reset_and_retry",
        "escalate",
        "rollback",
        "retry",
    }:
        return normalized
    return None


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

    display_recommendation = _display_recommendation(machine_review_payload)

    requires_human_review = _as_optional_bool(
        machine_review_payload.get("requires_human_review")
    )
    if requires_human_review is None:
        recovery_policy = _read_recovery_policy(machine_review_payload)
        if isinstance(recovery_policy, dict):
            requires_human_review = _as_optional_bool(
                recovery_policy.get("requires_human_review")
            )
    policy_reasons = _policy_reasons(machine_review_payload)
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
    elif display_recommendation in {"retry", "reset_and_retry"}:
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
    policy_reasons = _policy_reasons(machine_review_payload)

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


def _derive_mode_visibility(
    *,
    machine_review_recorded: bool,
    advisory: dict[str, Any],
    execution_bridge: dict[str, Any],
) -> dict[str, Any]:
    mode_basis: list[str] = []
    if machine_review_recorded:
        mode_basis.append("ledger_backed_machine_review_visible")
    if execution_bridge.get("requires_explicit_operator_decision") is True:
        mode_basis.append("explicit_operator_decision_required")

    blockers: list[str] = []
    raw_bridge_blockers = execution_bridge.get("eligibility_blockers")
    if isinstance(raw_bridge_blockers, (list, tuple)):
        blockers.extend(str(item) for item in raw_bridge_blockers if str(item))

    raw_advisory_flags = advisory.get("operator_attention_flags")
    if isinstance(raw_advisory_flags, (list, tuple)):
        for item in raw_advisory_flags:
            tag = str(item)
            if tag and tag not in blockers:
                blockers.append(tag)

    for foundational_blocker in (
        "explicit_operator_gate_required",
        "execution_not_implemented",
    ):
        if foundational_blocker not in blockers:
            blockers.append(foundational_blocker)

    return {
        "current_mode": "manual_review_only",
        "next_possible_mode": None,
        "mode_basis": mode_basis,
        "mode_blockers": blockers,
    }


def _build_output(row: dict[str, Any], *, db_path: str) -> dict[str, Any]:
    rubric_path = row.get("rubric_path")
    merge_gate_path = row.get("merge_gate_path")
    replan_input = _read_replan_input(merge_gate_path)
    merge_gate_contract = _read_merge_gate_contract(
        merge_gate_path,
        replan_input=replan_input,
    )
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
    mode_visibility = _derive_mode_visibility(
        machine_review_recorded=machine_review_recorded,
        advisory=advisory,
        execution_bridge=execution_bridge,
    )
    recovery_policy = _read_recovery_policy(machine_review_payload)
    recovery_decision = (
        machine_review_payload.get("recovery_decision")
        if machine_review_payload is not None
        else None
    )
    if recovery_decision is None and recovery_policy is not None:
        recovery_decision = recovery_policy.get("recovery_decision")
    recommended_action = (
        machine_review_payload.get("recommended_action")
        if machine_review_payload is not None
        else None
    )
    if recommended_action is None:
        recommended_action = recovery_decision
    failure_codes = []
    if machine_review_payload is not None:
        raw_failure_codes = machine_review_payload.get("failure_codes")
        if isinstance(raw_failure_codes, (list, tuple)):
            failure_codes = [str(item) for item in raw_failure_codes]
    if not failure_codes and isinstance(recovery_policy, dict):
        nested_failure_codes = recovery_policy.get("failure_codes")
        if isinstance(nested_failure_codes, (list, tuple)):
            failure_codes = [str(item) for item in nested_failure_codes]
    decision_basis = []
    if machine_review_payload is not None:
        raw_decision_basis = machine_review_payload.get("decision_basis")
        if isinstance(raw_decision_basis, (list, tuple)):
            decision_basis = [str(item) for item in raw_decision_basis]
    if not decision_basis and isinstance(recovery_policy, dict):
        nested_decision_basis = recovery_policy.get("decision_basis")
        if isinstance(nested_decision_basis, (list, tuple)):
            decision_basis = [str(item) for item in nested_decision_basis]
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
        "lifecycle_state": merge_gate_contract["lifecycle_state"],
        "write_authority": merge_gate_contract["write_authority"],
        "failure_type": merge_gate_contract["failure_type"],
        "retry_recommended": merge_gate_contract["retry_recommended"],
        "retry_recommendation": merge_gate_contract["retry_recommendation"],
        "retry_budget_remaining": merge_gate_contract["retry_budget_remaining"],
        "escalation_required": merge_gate_contract["escalation_required"],
        "next_action_readiness": merge_gate_contract["next_action_readiness"],
        "primary_fail_reasons": merge_gate_contract["primary_fail_reasons"],
        "replan_input": replan_input,
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
            "recommended_action": recommended_action,
            "recovery_decision": recovery_decision,
            "policy_version": (
                machine_review_payload.get("policy_version")
                if machine_review_payload is not None
                else None
            ),
            "policy_reasons": _policy_reasons(machine_review_payload),
            "score_total": (
                machine_review_payload.get("score_total")
                if machine_review_payload is not None
                else None
            ),
            "dimension_scores": (
                machine_review_payload.get("dimension_scores")
                if machine_review_payload is not None
                else None
            ),
            "failure_codes": (
                failure_codes
            ),
            "decision_basis": (
                decision_basis
            ),
            "requires_human_review": (
                _as_optional_bool(machine_review_payload.get("requires_human_review"))
                if machine_review_payload is not None
                else None
            ),
            "recovery_policy": recovery_policy,
            "retry_metadata": retry_metadata,
            "advisory": advisory,
            "execution_bridge": execution_bridge,
            "mode_visibility": mode_visibility,
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
        f"lifecycle_state: {_fmt(output.get('lifecycle_state'))}",
        f"write_authority_state: {_fmt(output['write_authority'].get('state'))}",
        "write_authority_allowed_categories: "
        + (
            ", ".join([str(v) for v in output["write_authority"].get("allowed_categories", [])])
            if output["write_authority"].get("allowed_categories")
            else "none"
        ),
        f"failure_type: {_fmt(output.get('failure_type'))}",
        f"retry_recommended: {_fmt(output.get('retry_recommended'))}",
        f"retry_recommendation: {_fmt(output.get('retry_recommendation'))}",
        f"retry_budget_remaining: {_fmt(output.get('retry_budget_remaining'))}",
        f"escalation_required: {_fmt(output.get('escalation_required'))}",
        f"next_action_readiness: {_fmt(output.get('next_action_readiness'))}",
        "primary_fail_reasons: "
        + (
            ", ".join([str(v) for v in output.get("primary_fail_reasons", [])])
            if output.get("primary_fail_reasons")
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
        f"recovery_decision: {_fmt(output['machine_review'].get('recovery_decision'))}",
        f"policy_version: {_fmt(output['machine_review'].get('policy_version'))}",
        f"score_total: {_fmt(output['machine_review'].get('score_total'))}",
        "dimension_scores: "
        + (
            json.dumps(output["machine_review"].get("dimension_scores"), ensure_ascii=False, sort_keys=True)
            if output["machine_review"].get("dimension_scores") is not None
            else "<missing>"
        ),
        "failure_codes: "
        + (
            ", ".join([str(v) for v in output["machine_review"].get("failure_codes", [])])
            if output["machine_review"].get("failure_codes")
            else "none"
        ),
        "decision_basis: "
        + (
            ", ".join([str(v) for v in output["machine_review"].get("decision_basis", [])])
            if output["machine_review"].get("decision_basis")
            else "none"
        ),
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
        f"mode_visibility_current_mode: {_fmt(output['machine_review']['mode_visibility'].get('current_mode'))}",
        f"mode_visibility_next_possible_mode: {_fmt(output['machine_review']['mode_visibility'].get('next_possible_mode'))}",
        "mode_visibility_mode_basis: "
        + (
            ", ".join(
                [
                    str(v)
                    for v in output["machine_review"]["mode_visibility"].get(
                        "mode_basis", []
                    )
                ]
            )
            if output["machine_review"]["mode_visibility"].get("mode_basis")
            else "none"
        ),
        "mode_visibility_mode_blockers: "
        + (
            ", ".join(
                [
                    str(v)
                    for v in output["machine_review"]["mode_visibility"].get(
                        "mode_blockers", []
                    )
                ]
            )
            if output["machine_review"]["mode_visibility"].get("mode_blockers")
            else "none"
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

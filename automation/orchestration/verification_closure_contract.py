from __future__ import annotations

from typing import Any
from typing import Mapping

VERIFICATION_CLOSURE_CONTRACT_SCHEMA_VERSION = "v1"

VERIFICATION_STATUSES = {
    "verified_success",
    "verified_failure",
    "inconclusive",
    "not_verifiable",
}

VERIFICATION_OUTCOMES = {
    "objective_satisfied",
    "completion_gap",
    "objective_gap",
    "closure_followup",
    "manual_closure_only",
    "rollback_consideration",
    "external_truth_pending",
    "not_verifiable",
    "unknown",
}

VERIFICATION_VALIDITIES = {
    "valid",
    "partial",
    "malformed",
    "insufficient_truth",
}

VERIFICATION_CONFIDENCE_LEVELS = {
    "high",
    "medium",
    "low",
}

OBJECTIVE_SATISFACTION_STATUSES = {
    "satisfied",
    "not_satisfied",
    "unknown",
}

COMPLETION_SATISFACTION_STATUSES = {
    "satisfied",
    "not_satisfied",
    "unknown",
}

CLOSURE_STATUSES = {
    "safely_closable",
    "not_closable",
    "closure_pending",
    "manual_closure_only",
    "unknown",
}

CLOSURE_DECISIONS = {
    "close_ready",
    "hold_for_followup",
    "manual_close",
    "consider_rollback",
    "await_external_truth",
    "cannot_determine",
}

VERIFICATION_SOURCE_POSTURES = {
    "post_execution_verification",
    "insufficient_truth",
    "not_applicable",
}

VERIFICATION_REASON_CODES = {
    "malformed_verification_evidence",
    "insufficient_verification_truth",
    "external_truth_pending",
    "objective_gap",
    "completion_gap",
    "approval_blocker",
    "reconcile_mismatch",
    "rollback_consideration",
    "closure_followup_required",
    "manual_closure_required",
    "verified_success",
    "not_verifiable",
    "unknown",
    "no_reason",
}

VERIFICATION_REASON_ORDER = (
    "malformed_verification_evidence",
    "insufficient_verification_truth",
    "external_truth_pending",
    "objective_gap",
    "completion_gap",
    "approval_blocker",
    "reconcile_mismatch",
    "rollback_consideration",
    "closure_followup_required",
    "manual_closure_required",
    "verified_success",
    "not_verifiable",
    "unknown",
    "no_reason",
)

VERIFICATION_CLOSURE_RUN_STATE_SUMMARY_SAFE_FIELDS = (
    "verification_closure_contract_present",
    "verification_status",
    "verification_outcome",
    "verification_validity",
    "verification_confidence",
    "verification_primary_reason",
    "objective_satisfaction_status",
    "completion_satisfaction_status",
    "closure_status",
    "closure_decision",
    "objective_satisfied",
    "completion_satisfied",
    "safely_closable",
    "manual_closure_required",
    "closure_followup_required",
    "external_truth_required",
)

_ALLOWED_SUPPORTING_REFS = (
    "run_state.next_safe_action",
    "run_state.policy_primary_action",
    "run_state.lifecycle_closure_status",
    "run_state.lifecycle_primary_closure_issue",
    "run_state.policy_status",
    "objective_contract.objective_status",
    "completion_contract.completion_status",
    "completion_contract.closure_decision",
    "approval_transport.approval_status",
    "approval_transport.approval_transport_status",
    "reconcile_contract.reconcile_status",
    "reconcile_contract.reconcile_primary_mismatch",
    "execution_authorization_gate.execution_authorization_status",
    "bounded_execution_bridge.bounded_execution_status",
    "bounded_execution_bridge.bounded_execution_decision",
    "execution_result_contract.execution_result_status",
    "execution_result_contract.execution_result_outcome",
)


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes"}:
            return True
        if normalized in {"0", "false", "no"}:
            return False
    return False


def _normalize_enum(value: Any, *, allowed: set[str], default: str) -> str:
    text = _normalize_text(value, default="")
    if text in allowed:
        return text
    return default


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = _normalize_text(value, default="")
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _normalize_reason_codes(values: list[str]) -> list[str]:
    filtered = _ordered_unique(values)
    ordered: list[str] = []
    for reason in VERIFICATION_REASON_ORDER:
        if reason in filtered and reason in VERIFICATION_REASON_CODES:
            ordered.append(reason)
    return ordered


def _build_supporting_refs(
    *,
    next_safe_action: str,
    policy_primary_action: str,
    lifecycle_closure_status: str,
    lifecycle_primary_closure_issue: str,
    policy_status: str,
    objective_status: str,
    completion_status: str,
    completion_closure_decision: str,
    approval_status: str,
    approval_transport_status: str,
    reconcile_status: str,
    reconcile_primary_mismatch: str,
    execution_authorization_status: str,
    bounded_execution_status: str,
    bounded_execution_decision: str,
    execution_result_status: str,
    execution_result_outcome: str,
) -> list[str]:
    refs: list[str] = []
    if next_safe_action:
        refs.append("run_state.next_safe_action")
    if policy_primary_action:
        refs.append("run_state.policy_primary_action")
    if lifecycle_closure_status:
        refs.append("run_state.lifecycle_closure_status")
    if lifecycle_primary_closure_issue:
        refs.append("run_state.lifecycle_primary_closure_issue")
    if policy_status:
        refs.append("run_state.policy_status")
    if objective_status:
        refs.append("objective_contract.objective_status")
    if completion_status:
        refs.append("completion_contract.completion_status")
    if completion_closure_decision:
        refs.append("completion_contract.closure_decision")
    if approval_status:
        refs.append("approval_transport.approval_status")
    if approval_transport_status:
        refs.append("approval_transport.approval_transport_status")
    if reconcile_status:
        refs.append("reconcile_contract.reconcile_status")
    if reconcile_primary_mismatch:
        refs.append("reconcile_contract.reconcile_primary_mismatch")
    if execution_authorization_status:
        refs.append("execution_authorization_gate.execution_authorization_status")
    if bounded_execution_status:
        refs.append("bounded_execution_bridge.bounded_execution_status")
    if bounded_execution_decision:
        refs.append("bounded_execution_bridge.bounded_execution_decision")
    if execution_result_status:
        refs.append("execution_result_contract.execution_result_status")
    if execution_result_outcome:
        refs.append("execution_result_contract.execution_result_outcome")

    ordered: list[str] = []
    for allowed in _ALLOWED_SUPPORTING_REFS:
        if allowed in refs and allowed not in ordered:
            ordered.append(allowed)
    return ordered


def _infer_source_posture(
    *,
    bounded_execution_status: str,
    execution_result_attempted: bool,
    execution_result_status: str,
    execution_result_present: bool,
) -> str:
    if bounded_execution_status == "not_applicable" and not execution_result_attempted:
        return "not_applicable"
    if execution_result_present or execution_result_attempted or execution_result_status:
        return "post_execution_verification"
    return "insufficient_truth"


def build_verification_closure_contract_surface(
    *,
    run_id: str,
    objective_contract_payload: Mapping[str, Any] | None,
    completion_contract_payload: Mapping[str, Any] | None,
    approval_transport_payload: Mapping[str, Any] | None,
    reconcile_contract_payload: Mapping[str, Any] | None,
    execution_authorization_gate_payload: Mapping[str, Any] | None,
    bounded_execution_bridge_payload: Mapping[str, Any] | None,
    execution_result_contract_payload: Mapping[str, Any] | None,
    run_state_payload: Mapping[str, Any] | None,
    artifact_presence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    objective = dict(objective_contract_payload or {})
    completion = dict(completion_contract_payload or {})
    approval = dict(approval_transport_payload or {})
    reconcile = dict(reconcile_contract_payload or {})
    execution_authorization = dict(execution_authorization_gate_payload or {})
    bounded_execution = dict(bounded_execution_bridge_payload or {})
    execution_result = dict(execution_result_contract_payload or {})
    run_state = dict(run_state_payload or {})
    artifacts = dict(artifact_presence or {})

    objective_id = _normalize_text(
        objective.get("objective_id")
        or completion.get("objective_id")
        or approval.get("objective_id")
        or reconcile.get("objective_id")
        or execution_authorization.get("objective_id")
        or bounded_execution.get("objective_id")
        or execution_result.get("objective_id")
        or run_state.get("objective_id"),
        default="",
    )

    objective_status = _normalize_text(
        objective.get("objective_status") or run_state.get("objective_contract_status"),
        default="",
    )
    completion_status = _normalize_text(
        completion.get("completion_status") or run_state.get("completion_status"),
        default="",
    )
    completion_closure_decision = _normalize_text(
        completion.get("closure_decision") or run_state.get("closure_decision"),
        default="",
    )
    safe_closure_status = _normalize_text(
        completion.get("safe_closure_status") or run_state.get("safe_closure_status"),
        default="",
    )
    completion_blocked_reason = _normalize_text(
        completion.get("completion_blocked_reason") or run_state.get("completion_blocked_reason"),
        default="",
    )

    approval_status = _normalize_text(
        approval.get("approval_status") or run_state.get("approval_status"),
        default="",
    )
    approval_transport_status = _normalize_text(
        approval.get("approval_transport_status") or run_state.get("approval_transport_status"),
        default="",
    )
    approval_blocked_reason = _normalize_text(
        approval.get("approval_blocked_reason") or run_state.get("approval_blocked_reason"),
        default="",
    )

    reconcile_status = _normalize_text(
        reconcile.get("reconcile_status") or run_state.get("reconcile_status"),
        default="",
    )
    reconcile_primary_mismatch = _normalize_text(
        reconcile.get("reconcile_primary_mismatch") or run_state.get("reconcile_primary_mismatch"),
        default="",
    )
    reconcile_blocked_reason = _normalize_text(
        reconcile.get("reconcile_blocked_reason") or run_state.get("reconcile_blocked_reason"),
        default="",
    )
    reconcile_waiting_on_truth = _normalize_bool(
        reconcile.get("reconcile_waiting_on_truth")
        if "reconcile_waiting_on_truth" in reconcile
        else run_state.get("reconcile_waiting_on_truth")
    )

    execution_authorization_status = _normalize_text(
        execution_authorization.get("execution_authorization_status")
        or run_state.get("execution_authorization_status"),
        default="",
    )
    bounded_execution_status = _normalize_text(
        bounded_execution.get("bounded_execution_status") or run_state.get("bounded_execution_status"),
        default="",
    )
    bounded_execution_decision = _normalize_text(
        bounded_execution.get("bounded_execution_decision") or run_state.get("bounded_execution_decision"),
        default="",
    )

    execution_result_status = _normalize_text(
        execution_result.get("execution_result_status") or run_state.get("execution_result_status"),
        default="",
    )
    execution_result_outcome = _normalize_text(
        execution_result.get("execution_result_outcome") or run_state.get("execution_result_outcome"),
        default="",
    )
    execution_result_validity = _normalize_text(
        execution_result.get("execution_result_validity") or run_state.get("execution_result_validity"),
        default="",
    )
    execution_result_attempted = _normalize_bool(
        execution_result.get("execution_result_attempted")
        if "execution_result_attempted" in execution_result
        else run_state.get("execution_result_attempted")
    )

    lifecycle_closure_status = _normalize_text(run_state.get("lifecycle_closure_status"), default="")
    lifecycle_safely_closed = _normalize_bool(run_state.get("lifecycle_safely_closed"))
    lifecycle_manual_required = _normalize_bool(run_state.get("lifecycle_manual_required"))
    lifecycle_replan_required = _normalize_bool(run_state.get("lifecycle_replan_required"))
    lifecycle_execution_complete_not_closed = _normalize_bool(
        run_state.get("lifecycle_execution_complete_not_closed")
    )
    lifecycle_rollback_complete_not_closed = _normalize_bool(
        run_state.get("lifecycle_rollback_complete_not_closed")
    )
    lifecycle_primary_closure_issue = _normalize_text(
        run_state.get("lifecycle_primary_closure_issue"), default=""
    )

    next_safe_hint = _normalize_text(run_state.get("next_safe_action"), default="")
    policy_primary_action = _normalize_text(run_state.get("policy_primary_action"), default="")
    policy_status = _normalize_text(run_state.get("policy_status"), default="")

    completion_delivery_waiting = _normalize_bool(
        completion.get("delivery_complete_waiting_external_truth")
        if "delivery_complete_waiting_external_truth" in completion
        else run_state.get("delivery_complete_waiting_external_truth")
    )

    execution_result_present = bool(artifacts.get("execution_result_contract.json")) or bool(
        run_state.get("execution_result_contract_present")
    ) or bool(execution_result_status or execution_result_outcome or execution_result_validity)

    source_posture = _normalize_enum(
        _infer_source_posture(
            bounded_execution_status=bounded_execution_status,
            execution_result_attempted=execution_result_attempted,
            execution_result_status=execution_result_status,
            execution_result_present=execution_result_present,
        ),
        allowed=VERIFICATION_SOURCE_POSTURES,
        default="insufficient_truth",
    )

    malformed_evidence = execution_result_validity == "malformed"

    insufficient_truth = bool(
        not execution_result_present
        or execution_result_validity in {"missing", ""}
        or (not objective_status and not completion_status)
        or source_posture == "insufficient_truth"
    )

    explicit_external_truth_pending = bool(
        completion_status == "delivery_complete_waiting_external_truth"
        or completion_delivery_waiting
        or reconcile_status == "waiting_for_truth"
        or reconcile_waiting_on_truth
    )

    explicit_objective_gap = objective_status in {"blocked", "incomplete", "underspecified"}

    explicit_completion_gap = completion_status in {
        "not_done",
        "replan_before_closure",
        "execution_complete_not_accepted",
        "done_but_evidence_incomplete",
        "rollback_complete_not_closed",
        "manual_closure_required",
    }

    explicit_approval_blocker = bool(
        approval_status in {"denied", "deferred", "replan_requested", "absent"}
        or approval_transport_status in {"blocked", "missing", "expired", "superseded", "non_actionable"}
        or approval_blocked_reason
    )

    explicit_reconcile_mismatch = bool(
        reconcile_status in {"blocked", "inconsistent"}
        or reconcile_primary_mismatch
        or reconcile_blocked_reason
    )

    rollback_consideration_required = bool(
        execution_result_status == "failed"
        or execution_result_outcome in {"patch_failed", "tests_failed", "command_failed"}
        or _normalize_bool(run_state.get("rollback_validation_failed"))
    )

    closure_followup_required = bool(
        completion_status
        in {
            "execution_complete_not_accepted",
            "done_but_evidence_incomplete",
            "rollback_complete_not_closed",
            "manual_closure_required",
        }
        or lifecycle_execution_complete_not_closed
        or lifecycle_rollback_complete_not_closed
        or lifecycle_closure_status in {"execution_complete_not_closed", "rollback_complete_not_closed", "closure_unresolved"}
    )

    manual_closure_required = bool(
        completion_status == "manual_closure_required"
        or lifecycle_manual_required
    )

    objective_satisfaction_status = "unknown"
    if objective_status == "complete":
        objective_satisfaction_status = "satisfied"
    elif objective_status in {"blocked", "incomplete", "underspecified"}:
        objective_satisfaction_status = "not_satisfied"

    completion_satisfaction_status = "unknown"
    if completion_status == "done_and_safely_closed":
        completion_satisfaction_status = "satisfied"
    elif completion_status:
        completion_satisfaction_status = "not_satisfied"

    verified_success_ready = bool(
        execution_result_status == "succeeded"
        and objective_satisfaction_status == "satisfied"
        and completion_satisfaction_status == "satisfied"
        and safe_closure_status == "safely_closed"
        and lifecycle_safely_closed
        and not explicit_approval_blocker
        and not explicit_reconcile_mismatch
        and not rollback_consideration_required
        and not closure_followup_required
        and not manual_closure_required
        and not explicit_external_truth_pending
    )

    lead = ""
    if malformed_evidence:
        lead = "malformed_verification_evidence"
    elif insufficient_truth:
        lead = "insufficient_verification_truth"
    elif explicit_external_truth_pending:
        lead = "external_truth_pending"
    elif explicit_objective_gap:
        lead = "objective_gap"
    elif explicit_completion_gap:
        lead = "completion_gap"
    elif explicit_approval_blocker:
        lead = "approval_blocker"
    elif explicit_reconcile_mismatch:
        lead = "reconcile_mismatch"
    elif rollback_consideration_required:
        lead = "rollback_consideration"
    elif closure_followup_required:
        lead = "closure_followup_required"
    elif verified_success_ready:
        lead = "verified_success"
    else:
        lead = "unknown"

    if lead == "malformed_verification_evidence":
        verification_status = "not_verifiable"
        verification_outcome = "not_verifiable"
        verification_validity = "malformed"
        verification_confidence = "low"
        closure_status = "unknown"
        closure_decision = "cannot_determine"
        objective_satisfaction_status = "unknown"
        completion_satisfaction_status = "unknown"
    elif lead == "insufficient_verification_truth":
        verification_status = "not_verifiable"
        verification_outcome = "not_verifiable"
        verification_validity = "insufficient_truth"
        verification_confidence = "low"
        closure_status = "unknown"
        closure_decision = "cannot_determine"
    elif lead == "external_truth_pending":
        verification_status = "inconclusive"
        verification_outcome = "external_truth_pending"
        verification_validity = "partial"
        verification_confidence = "medium"
        closure_status = "closure_pending"
        closure_decision = "await_external_truth"
    elif lead == "objective_gap":
        verification_status = "verified_failure"
        verification_outcome = "objective_gap"
        verification_validity = "valid"
        verification_confidence = "medium"
        closure_status = "not_closable"
        closure_decision = "hold_for_followup"
    elif lead == "completion_gap":
        verification_status = "verified_failure"
        verification_outcome = "completion_gap"
        verification_validity = "valid"
        verification_confidence = "medium"
        closure_status = "not_closable"
        closure_decision = "hold_for_followup"
    elif lead == "approval_blocker":
        verification_status = "verified_failure"
        verification_outcome = "manual_closure_only" if manual_closure_required else "closure_followup"
        verification_validity = "valid"
        verification_confidence = "medium"
        closure_status = "manual_closure_only" if manual_closure_required else "not_closable"
        closure_decision = "manual_close" if manual_closure_required else "hold_for_followup"
    elif lead == "reconcile_mismatch":
        verification_status = "verified_failure"
        verification_outcome = "closure_followup"
        verification_validity = "valid"
        verification_confidence = "medium"
        closure_status = "not_closable"
        closure_decision = "hold_for_followup"
    elif lead == "rollback_consideration":
        verification_status = "verified_failure"
        verification_outcome = "rollback_consideration"
        verification_validity = "valid"
        verification_confidence = "medium"
        closure_status = "not_closable"
        closure_decision = "consider_rollback"
    elif lead == "closure_followup_required":
        verification_status = "verified_failure"
        verification_outcome = "closure_followup"
        verification_validity = "partial"
        verification_confidence = "medium"
        closure_status = "closure_pending"
        closure_decision = "hold_for_followup"
    elif lead == "verified_success":
        verification_status = "verified_success"
        verification_outcome = "objective_satisfied"
        verification_validity = "valid"
        verification_confidence = "high"
        closure_status = "safely_closable"
        closure_decision = "close_ready"
    else:
        verification_status = "inconclusive"
        verification_outcome = "unknown"
        verification_validity = "partial"
        verification_confidence = "low"
        closure_status = "unknown"
        closure_decision = "cannot_determine"

    external_truth_required = closure_decision == "await_external_truth"

    if closure_status == "manual_closure_only":
        manual_closure_required = True
    if manual_closure_required and closure_status != "manual_closure_only":
        closure_status = "manual_closure_only"
        if closure_decision not in {"await_external_truth", "consider_rollback"}:
            closure_decision = "manual_close"

    if closure_decision == "await_external_truth":
        external_truth_required = True
    if external_truth_required and closure_decision != "await_external_truth":
        closure_decision = "await_external_truth"

    if closure_decision == "close_ready" and not (
        verification_status == "verified_success"
        and objective_satisfaction_status == "satisfied"
        and completion_satisfaction_status == "satisfied"
        and closure_status == "safely_closable"
        and not manual_closure_required
        and not closure_followup_required
        and not external_truth_required
    ):
        closure_decision = "cannot_determine"
        closure_status = "unknown"
        verification_status = "inconclusive"
        verification_outcome = "unknown"
        verification_confidence = "low"

    objective_satisfaction_status = _normalize_enum(
        objective_satisfaction_status,
        allowed=OBJECTIVE_SATISFACTION_STATUSES,
        default="unknown",
    )
    completion_satisfaction_status = _normalize_enum(
        completion_satisfaction_status,
        allowed=COMPLETION_SATISFACTION_STATUSES,
        default="unknown",
    )

    objective_satisfied = objective_satisfaction_status == "satisfied"
    completion_satisfied = completion_satisfaction_status == "satisfied"
    safely_closable = closure_status == "safely_closable"

    verification_status = _normalize_enum(
        verification_status,
        allowed=VERIFICATION_STATUSES,
        default="not_verifiable",
    )
    verification_outcome = _normalize_enum(
        verification_outcome,
        allowed=VERIFICATION_OUTCOMES,
        default="unknown",
    )
    verification_validity = _normalize_enum(
        verification_validity,
        allowed=VERIFICATION_VALIDITIES,
        default="insufficient_truth",
    )
    verification_confidence = _normalize_enum(
        verification_confidence,
        allowed=VERIFICATION_CONFIDENCE_LEVELS,
        default="low",
    )
    closure_status = _normalize_enum(closure_status, allowed=CLOSURE_STATUSES, default="unknown")
    closure_decision = _normalize_enum(
        closure_decision,
        allowed=CLOSURE_DECISIONS,
        default="cannot_determine",
    )

    verification_succeeded = verification_status == "verified_success"
    verification_failed = verification_status == "verified_failure"
    verification_inconclusive = verification_status == "inconclusive"

    reason_candidates: list[str] = [lead]
    if manual_closure_required:
        reason_candidates.append("manual_closure_required")
    if verification_status == "not_verifiable":
        reason_candidates.append("not_verifiable")
    if verification_status == "inconclusive" and verification_outcome == "unknown":
        reason_candidates.append("unknown")
    if verification_status == "verified_success":
        reason_candidates.append("verified_success")

    reason_codes = _normalize_reason_codes(reason_candidates)
    if not reason_codes:
        reason_codes = ["no_reason"]
    verification_primary_reason = reason_codes[0]

    closure_followup_hint = ""
    for candidate in (
        lifecycle_primary_closure_issue,
        completion_blocked_reason,
        approval_blocked_reason,
        reconcile_primary_mismatch,
        reconcile_blocked_reason,
    ):
        text = _normalize_text(candidate, default="")
        if text:
            closure_followup_hint = text
            break

    payload: dict[str, Any] = {
        "schema_version": VERIFICATION_CLOSURE_CONTRACT_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "verification_status": verification_status,
        "verification_outcome": verification_outcome,
        "verification_validity": verification_validity,
        "verification_confidence": verification_confidence,
        "objective_satisfaction_status": objective_satisfaction_status,
        "completion_satisfaction_status": completion_satisfaction_status,
        "closure_status": closure_status,
        "closure_decision": closure_decision,
        "verification_primary_reason": verification_primary_reason,
        "verification_reason_codes": reason_codes,
        "verification_succeeded": verification_succeeded,
        "verification_failed": verification_failed,
        "verification_inconclusive": verification_inconclusive,
        "objective_satisfied": objective_satisfied,
        "completion_satisfied": completion_satisfied,
        "safely_closable": safely_closable,
        "manual_closure_required": bool(manual_closure_required),
        "closure_followup_required": bool(closure_followup_required),
        "rollback_consideration_required": bool(rollback_consideration_required),
        "external_truth_required": bool(external_truth_required),
        "verification_source_posture": source_posture,
        "verification_bridge_status": bounded_execution_status or "unknown",
        "verification_bridge_decision": bounded_execution_decision or "unknown",
        "verification_execution_result_status": execution_result_status or "unknown",
        "verification_execution_result_outcome": execution_result_outcome or "unknown",
        "verification_authorization_status": execution_authorization_status or "unknown",
        "supporting_compact_truth_refs": _build_supporting_refs(
            next_safe_action=next_safe_hint,
            policy_primary_action=policy_primary_action,
            lifecycle_closure_status=lifecycle_closure_status,
            lifecycle_primary_closure_issue=lifecycle_primary_closure_issue,
            policy_status=policy_status,
            objective_status=objective_status,
            completion_status=completion_status,
            completion_closure_decision=completion_closure_decision,
            approval_status=approval_status,
            approval_transport_status=approval_transport_status,
            reconcile_status=reconcile_status,
            reconcile_primary_mismatch=reconcile_primary_mismatch,
            execution_authorization_status=execution_authorization_status,
            bounded_execution_status=bounded_execution_status,
            bounded_execution_decision=bounded_execution_decision,
            execution_result_status=execution_result_status,
            execution_result_outcome=execution_result_outcome,
        ),
    }

    result_artifact_path = _normalize_text(execution_result.get("result_artifact_path"), default="")
    if result_artifact_path:
        payload["result_artifact_path"] = result_artifact_path
    execution_receipt_path = _normalize_text(execution_result.get("execution_receipt_path"), default="")
    if execution_receipt_path:
        payload["execution_receipt_path"] = execution_receipt_path
    if completion_blocked_reason:
        payload["completion_blocked_reason"] = completion_blocked_reason
    if approval_blocked_reason:
        payload["approval_blocked_reason"] = approval_blocked_reason
    if reconcile_primary_mismatch:
        payload["reconcile_primary_mismatch"] = reconcile_primary_mismatch
    if next_safe_hint:
        payload["next_safe_hint"] = next_safe_hint
    if closure_followup_hint:
        payload["closure_followup_hint"] = closure_followup_hint

    objective_summary = _normalize_text(objective.get("objective_summary") or run_state.get("objective_summary"), default="")
    requested_outcome = _normalize_text(objective.get("requested_outcome") or run_state.get("requested_outcome"), default="")
    if objective_summary:
        payload["objective_summary"] = objective_summary
    if requested_outcome:
        payload["requested_outcome"] = requested_outcome

    # Strict status/flag consistency rules.
    payload["verification_succeeded"] = payload["verification_status"] == "verified_success"
    payload["verification_failed"] = payload["verification_status"] == "verified_failure"
    payload["verification_inconclusive"] = payload["verification_status"] == "inconclusive"
    payload["objective_satisfied"] = payload["objective_satisfaction_status"] == "satisfied"
    payload["completion_satisfied"] = payload["completion_satisfaction_status"] == "satisfied"
    payload["safely_closable"] = payload["closure_status"] == "safely_closable"

    if payload["closure_status"] == "manual_closure_only":
        payload["manual_closure_required"] = True
    if payload["closure_decision"] == "await_external_truth":
        payload["external_truth_required"] = True
    if payload["external_truth_required"]:
        payload["closure_decision"] = "await_external_truth"

    if payload["closure_decision"] == "close_ready" and not (
        payload["verification_status"] == "verified_success"
        and payload["objective_satisfied"]
        and payload["completion_satisfied"]
        and payload["safely_closable"]
        and not payload["manual_closure_required"]
        and not payload["closure_followup_required"]
        and not payload["external_truth_required"]
    ):
        payload["closure_decision"] = "cannot_determine"
        payload["closure_status"] = "unknown"
        payload["verification_status"] = "inconclusive"
        payload["verification_outcome"] = "unknown"
        payload["verification_confidence"] = "low"
        payload["verification_succeeded"] = False
        payload["verification_failed"] = False
        payload["verification_inconclusive"] = True
        payload["safely_closable"] = False

    return payload


def build_verification_closure_run_state_summary_surface(
    verification_closure_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(verification_closure_payload or {})

    verification_status = _normalize_enum(
        payload.get("verification_status"),
        allowed=VERIFICATION_STATUSES,
        default="not_verifiable",
    )
    verification_outcome = _normalize_enum(
        payload.get("verification_outcome"),
        allowed=VERIFICATION_OUTCOMES,
        default="unknown",
    )
    verification_validity = _normalize_enum(
        payload.get("verification_validity"),
        allowed=VERIFICATION_VALIDITIES,
        default="insufficient_truth",
    )
    verification_confidence = _normalize_enum(
        payload.get("verification_confidence"),
        allowed=VERIFICATION_CONFIDENCE_LEVELS,
        default="low",
    )
    verification_primary_reason = _normalize_text(
        payload.get("verification_primary_reason"),
        default="",
    )
    if not verification_primary_reason or verification_primary_reason not in VERIFICATION_REASON_CODES:
        if verification_status == "verified_success":
            verification_primary_reason = "verified_success"
        elif verification_status == "not_verifiable":
            verification_primary_reason = "not_verifiable"
        elif verification_status == "verified_failure":
            verification_primary_reason = "completion_gap"
        else:
            verification_primary_reason = "unknown"

    objective_satisfaction_status = _normalize_enum(
        payload.get("objective_satisfaction_status"),
        allowed=OBJECTIVE_SATISFACTION_STATUSES,
        default="unknown",
    )
    completion_satisfaction_status = _normalize_enum(
        payload.get("completion_satisfaction_status"),
        allowed=COMPLETION_SATISFACTION_STATUSES,
        default="unknown",
    )
    closure_status = _normalize_enum(
        payload.get("closure_status"),
        allowed=CLOSURE_STATUSES,
        default="unknown",
    )
    closure_decision = _normalize_enum(
        payload.get("closure_decision"),
        allowed=CLOSURE_DECISIONS,
        default="cannot_determine",
    )

    present = bool(payload.get("verification_closure_contract_present", False)) or bool(
        verification_status or verification_outcome or closure_decision
    )

    return {
        "verification_closure_contract_present": bool(present),
        "verification_status": verification_status,
        "verification_outcome": verification_outcome,
        "verification_validity": verification_validity,
        "verification_confidence": verification_confidence,
        "verification_primary_reason": verification_primary_reason,
        "objective_satisfaction_status": objective_satisfaction_status,
        "completion_satisfaction_status": completion_satisfaction_status,
        "closure_status": closure_status,
        "closure_decision": closure_decision,
        "objective_satisfied": objective_satisfaction_status == "satisfied",
        "completion_satisfied": completion_satisfaction_status == "satisfied",
        "safely_closable": closure_status == "safely_closable",
        "manual_closure_required": _normalize_bool(payload.get("manual_closure_required")),
        "closure_followup_required": _normalize_bool(payload.get("closure_followup_required")),
        "external_truth_required": _normalize_bool(payload.get("external_truth_required")),
    }

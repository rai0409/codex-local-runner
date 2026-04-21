from __future__ import annotations

from typing import Any
from typing import Mapping

ENDGAME_CLOSURE_CONTRACT_SCHEMA_VERSION = "v1"

ENDGAME_CLOSURE_STATUSES = {
    "safely_closed",
    "not_closed",
    "closure_pending",
    "manual_only",
    "closure_unresolved",
    "not_applicable",
    "insufficient_truth",
}

ENDGAME_CLOSURE_OUTCOMES = {
    "terminal_success_closed",
    "completed_not_closed",
    "rollback_complete_not_closed",
    "manual_closure_only",
    "external_truth_pending",
    "closure_unresolved",
    "terminal_non_success_stop",
    "not_applicable",
    "unknown",
}

ENDGAME_CLOSURE_VALIDITIES = {
    "valid",
    "partial",
    "malformed",
    "insufficient_truth",
}

ENDGAME_CLOSURE_CONFIDENCE_LEVELS = {
    "high",
    "medium",
    "low",
}

FINAL_CLOSURE_CLASSES = {
    "safely_closed",
    "completed_but_not_closed",
    "rollback_complete_but_not_closed",
    "manual_closure_only",
    "external_truth_pending",
    "closure_unresolved",
    "terminal_non_success",
    "unknown",
}

TERMINAL_STOP_CLASSES = {
    "terminal_success",
    "terminal_non_success",
    "manual_terminal",
    "external_wait_terminal",
    "closure_unresolved_terminal",
    "not_terminal",
    "unknown",
}

CLOSURE_RESOLUTION_STATUSES = {
    "resolved",
    "pending",
    "manual_only",
    "unresolved",
    "unknown",
}

ENDGAME_SOURCE_POSTURES = {
    "post_loop_endgame_closure",
    "insufficient_truth",
    "not_applicable",
}

ENDGAME_REASON_CODES = {
    "malformed_endgame_inputs",
    "insufficient_endgame_truth",
    "safely_closed",
    "manual_closure_only",
    "external_truth_pending",
    "rollback_complete_not_closed",
    "completed_not_closed",
    "closure_unresolved",
    "terminal_non_success",
    "retry_exhausted",
    "reentry_exhausted",
    "same_failure_exhausted",
    "manual_escalation_required",
    "terminal_stop_required",
    "unknown",
    "no_reason",
}

ENDGAME_REASON_ORDER = (
    "malformed_endgame_inputs",
    "insufficient_endgame_truth",
    "safely_closed",
    "manual_closure_only",
    "external_truth_pending",
    "rollback_complete_not_closed",
    "completed_not_closed",
    "closure_unresolved",
    "terminal_non_success",
    "retry_exhausted",
    "reentry_exhausted",
    "same_failure_exhausted",
    "manual_escalation_required",
    "terminal_stop_required",
    "unknown",
    "no_reason",
)

ENDGAME_CLOSURE_RUN_STATE_SUMMARY_SAFE_FIELDS = (
    "endgame_closure_contract_present",
    "endgame_closure_status",
    "endgame_closure_outcome",
    "endgame_closure_validity",
    "endgame_closure_confidence",
    "final_closure_class",
    "terminal_stop_class",
    "closure_resolution_status",
    "endgame_primary_reason",
    "safely_closed",
    "completed_but_not_closed",
    "rollback_complete_but_not_closed",
    "manual_closure_only",
    "external_truth_pending",
    "closure_unresolved",
    "terminal_success",
    "terminal_non_success",
    "operator_followup_required",
    "further_retry_allowed",
    "further_reentry_allowed",
)

_ALLOWED_SUPPORTING_REFS = (
    "run_state.next_safe_action",
    "run_state.policy_primary_action",
    "run_state.policy_status",
    "run_state.lifecycle_closure_status",
    "run_state.lifecycle_primary_closure_issue",
    "completion_contract.completion_status",
    "completion_contract.completion_blocked_reason",
    "approval_transport.approval_status",
    "approval_transport.approval_blocked_reason",
    "reconcile_contract.reconcile_status",
    "reconcile_contract.reconcile_primary_mismatch",
    "execution_authorization_gate.execution_authorization_status",
    "bounded_execution_bridge.bounded_execution_status",
    "execution_result_contract.execution_result_status",
    "execution_result_contract.execution_result_outcome",
    "verification_closure_contract.verification_status",
    "verification_closure_contract.verification_outcome",
    "verification_closure_contract.closure_status",
    "verification_closure_contract.closure_decision",
    "retry_reentry_loop_contract.retry_loop_status",
    "retry_reentry_loop_contract.retry_loop_decision",
    "retry_reentry_loop_contract.retry_allowed",
    "retry_reentry_loop_contract.reentry_allowed",
    "retry_reentry_loop_contract.retry_exhausted",
    "retry_reentry_loop_contract.reentry_exhausted",
    "retry_reentry_loop_contract.same_failure_exhausted",
    "retry_reentry_loop_contract.terminal_stop_required",
    "retry_reentry_loop_contract.manual_escalation_required",
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
        text = _normalize_text(value, default="")
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


def _normalize_reason_codes(values: list[str]) -> list[str]:
    filtered = [value for value in _ordered_unique(values) if value in ENDGAME_REASON_CODES]
    ordered: list[str] = []
    for reason in ENDGAME_REASON_ORDER:
        if reason in filtered:
            ordered.append(reason)
    return ordered


def _build_supporting_refs(
    *,
    next_safe_hint: str,
    policy_primary_action: str,
    policy_status: str,
    lifecycle_closure_status: str,
    lifecycle_primary_closure_issue: str,
    completion_status: str,
    completion_blocked_reason: str,
    approval_status: str,
    approval_blocked_reason: str,
    reconcile_status: str,
    reconcile_primary_mismatch: str,
    execution_authorization_status: str,
    bounded_execution_bridge_status: str,
    execution_result_status: str,
    execution_result_outcome: str,
    verification_status: str,
    verification_outcome: str,
    closure_status: str,
    closure_decision: str,
    retry_loop_status: str,
    retry_loop_decision: str,
    retry_allowed: bool,
    reentry_allowed: bool,
    retry_exhausted: bool,
    reentry_exhausted: bool,
    same_failure_exhausted: bool,
    terminal_stop_required: bool,
    manual_escalation_required: bool,
) -> list[str]:
    refs: list[str] = []
    if next_safe_hint:
        refs.append("run_state.next_safe_action")
    if policy_primary_action:
        refs.append("run_state.policy_primary_action")
    if policy_status:
        refs.append("run_state.policy_status")
    if lifecycle_closure_status:
        refs.append("run_state.lifecycle_closure_status")
    if lifecycle_primary_closure_issue:
        refs.append("run_state.lifecycle_primary_closure_issue")
    if completion_status:
        refs.append("completion_contract.completion_status")
    if completion_blocked_reason:
        refs.append("completion_contract.completion_blocked_reason")
    if approval_status:
        refs.append("approval_transport.approval_status")
    if approval_blocked_reason:
        refs.append("approval_transport.approval_blocked_reason")
    if reconcile_status:
        refs.append("reconcile_contract.reconcile_status")
    if reconcile_primary_mismatch:
        refs.append("reconcile_contract.reconcile_primary_mismatch")
    if execution_authorization_status:
        refs.append("execution_authorization_gate.execution_authorization_status")
    if bounded_execution_bridge_status:
        refs.append("bounded_execution_bridge.bounded_execution_status")
    if execution_result_status:
        refs.append("execution_result_contract.execution_result_status")
    if execution_result_outcome:
        refs.append("execution_result_contract.execution_result_outcome")
    if verification_status:
        refs.append("verification_closure_contract.verification_status")
    if verification_outcome:
        refs.append("verification_closure_contract.verification_outcome")
    if closure_status:
        refs.append("verification_closure_contract.closure_status")
    if closure_decision:
        refs.append("verification_closure_contract.closure_decision")
    if retry_loop_status:
        refs.append("retry_reentry_loop_contract.retry_loop_status")
    if retry_loop_decision:
        refs.append("retry_reentry_loop_contract.retry_loop_decision")
    if retry_allowed:
        refs.append("retry_reentry_loop_contract.retry_allowed")
    if reentry_allowed:
        refs.append("retry_reentry_loop_contract.reentry_allowed")
    if retry_exhausted:
        refs.append("retry_reentry_loop_contract.retry_exhausted")
    if reentry_exhausted:
        refs.append("retry_reentry_loop_contract.reentry_exhausted")
    if same_failure_exhausted:
        refs.append("retry_reentry_loop_contract.same_failure_exhausted")
    if terminal_stop_required:
        refs.append("retry_reentry_loop_contract.terminal_stop_required")
    if manual_escalation_required:
        refs.append("retry_reentry_loop_contract.manual_escalation_required")

    ordered: list[str] = []
    for allowed in _ALLOWED_SUPPORTING_REFS:
        if allowed in refs and allowed not in ordered:
            ordered.append(allowed)
    return ordered


def build_endgame_closure_contract_surface(
    *,
    run_id: str,
    completion_contract_payload: Mapping[str, Any] | None,
    approval_transport_payload: Mapping[str, Any] | None,
    reconcile_contract_payload: Mapping[str, Any] | None,
    execution_authorization_gate_payload: Mapping[str, Any] | None,
    bounded_execution_bridge_payload: Mapping[str, Any] | None,
    execution_result_contract_payload: Mapping[str, Any] | None,
    verification_closure_contract_payload: Mapping[str, Any] | None,
    retry_reentry_loop_contract_payload: Mapping[str, Any] | None,
    run_state_payload: Mapping[str, Any] | None,
    artifact_presence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    completion = dict(completion_contract_payload or {})
    approval = dict(approval_transport_payload or {})
    reconcile = dict(reconcile_contract_payload or {})
    execution_authorization = dict(execution_authorization_gate_payload or {})
    bounded_execution = dict(bounded_execution_bridge_payload or {})
    execution_result = dict(execution_result_contract_payload or {})
    verification = dict(verification_closure_contract_payload or {})
    retry_loop = dict(retry_reentry_loop_contract_payload or {})
    run_state = dict(run_state_payload or {})
    artifacts = dict(artifact_presence or {})

    objective_id = _normalize_text(
        completion.get("objective_id")
        or approval.get("objective_id")
        or reconcile.get("objective_id")
        or execution_authorization.get("objective_id")
        or bounded_execution.get("objective_id")
        or execution_result.get("objective_id")
        or verification.get("objective_id")
        or retry_loop.get("objective_id")
        or run_state.get("objective_id"),
        default="",
    )

    verification_status = _normalize_text(
        verification.get("verification_status") or run_state.get("verification_status"),
        default="",
    )
    verification_outcome = _normalize_text(
        verification.get("verification_outcome") or run_state.get("verification_outcome"),
        default="",
    )
    verification_validity = _normalize_text(
        verification.get("verification_validity") or run_state.get("verification_validity"),
        default="",
    )
    closure_status = _normalize_text(
        verification.get("closure_status") or run_state.get("closure_status"),
        default="",
    )
    closure_decision = _normalize_text(
        verification.get("closure_decision") or run_state.get("closure_decision"),
        default="",
    )
    objective_satisfied_signal = _normalize_bool(
        verification.get("objective_satisfied")
        if "objective_satisfied" in verification
        else run_state.get("objective_satisfied")
    )
    completion_satisfied_signal = _normalize_bool(
        verification.get("completion_satisfied")
        if "completion_satisfied" in verification
        else run_state.get("completion_satisfied")
    )
    manual_closure_required_signal = _normalize_bool(
        verification.get("manual_closure_required")
        if "manual_closure_required" in verification
        else run_state.get("manual_closure_required")
    )
    closure_followup_required_signal = _normalize_bool(
        verification.get("closure_followup_required")
        if "closure_followup_required" in verification
        else run_state.get("closure_followup_required")
    )
    external_truth_required_signal = _normalize_bool(
        verification.get("external_truth_required")
        if "external_truth_required" in verification
        else run_state.get("external_truth_required")
    )

    retry_loop_status = _normalize_text(
        retry_loop.get("retry_loop_status") or run_state.get("retry_loop_status"),
        default="",
    )
    retry_loop_decision = _normalize_text(
        retry_loop.get("retry_loop_decision") or run_state.get("retry_loop_decision"),
        default="",
    )
    retry_loop_validity = _normalize_text(
        retry_loop.get("retry_loop_validity") or run_state.get("retry_loop_validity"),
        default="",
    )
    retry_allowed = _normalize_bool(
        retry_loop.get("retry_allowed")
        if "retry_allowed" in retry_loop
        else run_state.get("retry_allowed")
    )
    reentry_allowed = _normalize_bool(
        retry_loop.get("reentry_allowed")
        if "reentry_allowed" in retry_loop
        else run_state.get("reentry_allowed")
    )
    retry_exhausted = _normalize_bool(
        retry_loop.get("retry_exhausted")
        if "retry_exhausted" in retry_loop
        else run_state.get("retry_exhausted")
    )
    reentry_exhausted = _normalize_bool(
        retry_loop.get("reentry_exhausted")
        if "reentry_exhausted" in retry_loop
        else run_state.get("reentry_exhausted")
    )
    same_failure_exhausted = _normalize_bool(
        retry_loop.get("same_failure_exhausted")
        if "same_failure_exhausted" in retry_loop
        else run_state.get("same_failure_exhausted")
    )
    terminal_stop_required = _normalize_bool(
        retry_loop.get("terminal_stop_required")
        if "terminal_stop_required" in retry_loop
        else run_state.get("terminal_stop_required")
    )
    manual_escalation_required = _normalize_bool(
        retry_loop.get("manual_escalation_required")
        if "manual_escalation_required" in retry_loop
        else run_state.get("manual_escalation_required")
    )

    execution_result_status = _normalize_text(
        execution_result.get("execution_result_status")
        or run_state.get("execution_result_status"),
        default="",
    )
    execution_result_outcome = _normalize_text(
        execution_result.get("execution_result_outcome")
        or run_state.get("execution_result_outcome"),
        default="",
    )
    execution_result_validity = _normalize_text(
        execution_result.get("execution_result_validity")
        or run_state.get("execution_result_validity"),
        default="",
    )

    bounded_execution_bridge_status = _normalize_text(
        bounded_execution.get("bounded_execution_status")
        or run_state.get("bounded_execution_status"),
        default="",
    )
    execution_authorization_status = _normalize_text(
        execution_authorization.get("execution_authorization_status")
        or run_state.get("execution_authorization_status"),
        default="",
    )

    completion_status = _normalize_text(
        completion.get("completion_status") or run_state.get("completion_status"),
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

    lifecycle_closure_status = _normalize_text(run_state.get("lifecycle_closure_status"), default="")
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

    closure_followup_hint = _normalize_text(
        verification.get("closure_followup_hint") or lifecycle_primary_closure_issue,
        default="",
    )
    retry_hint = _normalize_text(retry_loop.get("retry_hint"), default="")
    reentry_hint = _normalize_text(retry_loop.get("reentry_hint"), default="")
    result_artifact_path = _normalize_text(execution_result.get("result_artifact_path"), default="")
    execution_receipt_path = _normalize_text(execution_result.get("execution_receipt_path"), default="")

    malformed_inputs = bool(
        verification_validity == "malformed"
        or retry_loop_validity == "malformed"
        or execution_result_validity == "malformed"
        or (
            closure_decision == "close_ready"
            and closure_status
            and closure_status != "safely_closable"
        )
    )

    has_endgame_truth = any(
        (
            verification_status,
            verification_outcome,
            closure_status,
            closure_decision,
            retry_loop_status,
            retry_loop_decision,
            execution_result_status,
            execution_result_outcome,
            lifecycle_closure_status,
        )
    )

    insufficient_truth = bool(
        not has_endgame_truth
        or verification_validity == "insufficient_truth"
        or retry_loop_validity == "insufficient_truth"
        or (
            not bool(artifacts.get("verification_closure_contract.json"))
            and not bool(artifacts.get("retry_reentry_loop_contract.json"))
            and not verification_status
            and not retry_loop_status
        )
    )

    safely_closed_lead = bool(
        verification_status == "verified_success"
        and closure_status == "safely_closable"
        and closure_decision == "close_ready"
        and not retry_allowed
        and not reentry_allowed
        and not terminal_stop_required
    )

    manual_only_lead = bool(
        manual_closure_required_signal
        or closure_status == "manual_closure_only"
        or closure_decision == "manual_close"
        or manual_escalation_required
        or retry_loop_decision == "escalate_manual"
    )

    external_pending_lead = bool(
        external_truth_required_signal
        or verification_outcome == "external_truth_pending"
        or closure_decision == "await_external_truth"
    )

    rollback_complete_not_closed_lead = bool(
        lifecycle_rollback_complete_not_closed
        or completion_status == "rollback_complete_not_closed"
    )

    completed_not_closed_lead = bool(
        not safely_closed_lead
        and not manual_only_lead
        and not external_pending_lead
        and not rollback_complete_not_closed_lead
        and (
            lifecycle_execution_complete_not_closed
            or closure_followup_required_signal
            or (
                (objective_satisfied_signal or completion_satisfied_signal or verification_status == "verified_success")
                and closure_decision != "close_ready"
            )
            or verification_outcome in {"closure_followup", "completion_gap", "objective_satisfied"}
        )
    )

    explicit_closure_unresolved = bool(
        _normalize_bool(run_state.get("closure_unresolved"))
        or lifecycle_closure_status in {"closure_unresolved", "stopped_unresolved"}
        or (
            verification_status in {"inconclusive", "not_verifiable"}
            and not completed_not_closed_lead
            and not manual_only_lead
            and not external_pending_lead
        )
    )

    terminal_non_success_fallback = bool(
        terminal_stop_required
        or retry_loop_status in {"stop_required", "exhausted"}
        or verification_status == "verified_failure"
    )

    not_applicable_lead = bool(
        retry_loop_status == "not_applicable"
        and verification_status == "not_verifiable"
        and closure_decision in {"", "cannot_determine"}
        and not execution_result_status
    )

    lead = "unknown"
    if malformed_inputs:
        lead = "malformed_endgame_inputs"
    elif insufficient_truth:
        lead = "insufficient_endgame_truth"
    elif safely_closed_lead:
        lead = "safely_closed"
    elif manual_only_lead:
        lead = "manual_closure_only"
    elif external_pending_lead:
        lead = "external_truth_pending"
    elif rollback_complete_not_closed_lead:
        lead = "rollback_complete_not_closed"
    elif completed_not_closed_lead:
        lead = "completed_not_closed"
    elif explicit_closure_unresolved:
        lead = "closure_unresolved"
    elif terminal_non_success_fallback:
        lead = "terminal_non_success"
    elif not_applicable_lead:
        lead = "not_applicable"
    else:
        lead = "unknown"

    endgame_closure_status = "insufficient_truth"
    endgame_closure_outcome = "unknown"
    endgame_closure_validity = "insufficient_truth"
    endgame_closure_confidence = "low"
    final_closure_class = "unknown"
    terminal_stop_class = "unknown"
    closure_resolution_status = "unknown"

    safely_closed = False
    completed_but_not_closed = False
    rollback_complete_but_not_closed = False
    manual_closure_only = False
    external_truth_pending = False
    closure_unresolved = False
    terminal_success = False
    terminal_non_success = False
    operator_followup_required = True

    further_retry_allowed = bool(retry_allowed)
    further_reentry_allowed = bool(reentry_allowed)

    if lead == "malformed_endgame_inputs":
        endgame_closure_status = "closure_unresolved"
        endgame_closure_outcome = "unknown"
        endgame_closure_validity = "malformed"
        endgame_closure_confidence = "low"
        final_closure_class = "closure_unresolved"
        terminal_stop_class = "closure_unresolved_terminal"
        closure_resolution_status = "unresolved"
        closure_unresolved = True
        terminal_non_success = True
    elif lead == "insufficient_endgame_truth":
        endgame_closure_status = "insufficient_truth"
        endgame_closure_outcome = "unknown"
        endgame_closure_validity = "insufficient_truth"
        endgame_closure_confidence = "low"
        final_closure_class = "unknown"
        terminal_stop_class = "unknown"
        closure_resolution_status = "unknown"
    elif lead == "safely_closed":
        endgame_closure_status = "safely_closed"
        endgame_closure_outcome = "terminal_success_closed"
        endgame_closure_validity = "valid"
        endgame_closure_confidence = "high"
        final_closure_class = "safely_closed"
        terminal_stop_class = "terminal_success"
        closure_resolution_status = "resolved"
        safely_closed = True
        terminal_success = True
        operator_followup_required = False
    elif lead == "manual_closure_only":
        endgame_closure_status = "manual_only"
        endgame_closure_outcome = "manual_closure_only"
        endgame_closure_validity = "valid"
        endgame_closure_confidence = "medium"
        final_closure_class = "manual_closure_only"
        terminal_stop_class = "manual_terminal"
        closure_resolution_status = "manual_only"
        manual_closure_only = True
        terminal_non_success = True
    elif lead == "external_truth_pending":
        endgame_closure_status = "closure_pending"
        endgame_closure_outcome = "external_truth_pending"
        endgame_closure_validity = "partial"
        endgame_closure_confidence = "medium"
        final_closure_class = "external_truth_pending"
        terminal_stop_class = "external_wait_terminal"
        closure_resolution_status = "pending"
        external_truth_pending = True
    elif lead == "rollback_complete_not_closed":
        endgame_closure_status = "not_closed"
        endgame_closure_outcome = "rollback_complete_not_closed"
        endgame_closure_validity = "valid"
        endgame_closure_confidence = "medium"
        final_closure_class = "rollback_complete_but_not_closed"
        terminal_stop_class = "terminal_non_success"
        closure_resolution_status = "pending"
        rollback_complete_but_not_closed = True
        terminal_non_success = True
    elif lead == "completed_not_closed":
        endgame_closure_status = "not_closed"
        endgame_closure_outcome = "completed_not_closed"
        endgame_closure_validity = "partial"
        endgame_closure_confidence = "medium"
        final_closure_class = "completed_but_not_closed"
        terminal_stop_class = "not_terminal" if (retry_allowed or reentry_allowed) else "terminal_non_success"
        closure_resolution_status = "pending"
        completed_but_not_closed = True
        terminal_non_success = terminal_stop_class == "terminal_non_success"
    elif lead == "closure_unresolved":
        endgame_closure_status = "closure_unresolved"
        endgame_closure_outcome = "closure_unresolved"
        endgame_closure_validity = "partial"
        endgame_closure_confidence = "low"
        final_closure_class = "closure_unresolved"
        terminal_stop_class = "closure_unresolved_terminal"
        closure_resolution_status = "unresolved"
        closure_unresolved = True
        terminal_non_success = True
    elif lead == "terminal_non_success":
        endgame_closure_status = "not_closed"
        endgame_closure_outcome = "terminal_non_success_stop"
        endgame_closure_validity = "partial"
        endgame_closure_confidence = "low"
        final_closure_class = "terminal_non_success"
        terminal_stop_class = "terminal_non_success"
        closure_resolution_status = "unresolved"
        terminal_non_success = True
    elif lead == "not_applicable":
        endgame_closure_status = "not_applicable"
        endgame_closure_outcome = "not_applicable"
        endgame_closure_validity = "partial"
        endgame_closure_confidence = "low"
        final_closure_class = "unknown"
        terminal_stop_class = "not_terminal"
        closure_resolution_status = "unknown"
    else:
        endgame_closure_status = "closure_unresolved"
        endgame_closure_outcome = "unknown"
        endgame_closure_validity = "partial"
        endgame_closure_confidence = "low"
        final_closure_class = "unknown"
        terminal_stop_class = "unknown"
        closure_resolution_status = "unknown"
        closure_unresolved = True
        terminal_non_success = True

    if terminal_stop_required:
        further_retry_allowed = False
        further_reentry_allowed = False

    if lead in {
        "malformed_endgame_inputs",
        "insufficient_endgame_truth",
        "safely_closed",
        "manual_closure_only",
        "external_truth_pending",
        "rollback_complete_not_closed",
        "closure_unresolved",
        "terminal_non_success",
    }:
        further_retry_allowed = False
        further_reentry_allowed = False

    if further_retry_allowed and not retry_allowed:
        further_retry_allowed = False
    if further_reentry_allowed and not reentry_allowed:
        further_reentry_allowed = False

    if endgame_closure_status == "safely_closed":
        terminal_stop_class = "terminal_success"
        safely_closed = True
        terminal_success = True
        terminal_non_success = False
        further_retry_allowed = False
        further_reentry_allowed = False
        operator_followup_required = False

    if endgame_closure_status == "manual_only":
        manual_closure_only = True
        terminal_stop_class = "manual_terminal"
        terminal_success = False
        terminal_non_success = True

    if endgame_closure_status == "closure_pending" and external_truth_pending:
        terminal_stop_class = "external_wait_terminal"

    if endgame_closure_status in {"closure_unresolved", "insufficient_truth"}:
        safely_closed = False

    if endgame_closure_status == "not_applicable":
        further_retry_allowed = False
        further_reentry_allowed = False

    if terminal_stop_class == "terminal_success":
        terminal_success = True
        terminal_non_success = False
    elif terminal_stop_class in {
        "terminal_non_success",
        "manual_terminal",
        "closure_unresolved_terminal",
    }:
        terminal_success = False
        terminal_non_success = True
    elif terminal_stop_class == "external_wait_terminal":
        terminal_success = False
        terminal_non_success = False

    reason_candidates: list[str] = [lead]
    if retry_exhausted:
        reason_candidates.append("retry_exhausted")
    if reentry_exhausted:
        reason_candidates.append("reentry_exhausted")
    if same_failure_exhausted:
        reason_candidates.append("same_failure_exhausted")
    if manual_escalation_required:
        reason_candidates.append("manual_escalation_required")
    if terminal_stop_required:
        reason_candidates.append("terminal_stop_required")

    reason_codes = _normalize_reason_codes(reason_candidates)
    if not reason_codes:
        reason_codes = ["no_reason"]
    endgame_primary_reason = reason_codes[0]

    endgame_source_posture = "post_loop_endgame_closure"
    if endgame_closure_status == "insufficient_truth":
        endgame_source_posture = "insufficient_truth"
    elif endgame_closure_status == "not_applicable":
        endgame_source_posture = "not_applicable"

    payload: dict[str, Any] = {
        "schema_version": ENDGAME_CLOSURE_CONTRACT_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "endgame_closure_status": _normalize_enum(
            endgame_closure_status,
            allowed=ENDGAME_CLOSURE_STATUSES,
            default="insufficient_truth",
        ),
        "endgame_closure_outcome": _normalize_enum(
            endgame_closure_outcome,
            allowed=ENDGAME_CLOSURE_OUTCOMES,
            default="unknown",
        ),
        "endgame_closure_validity": _normalize_enum(
            endgame_closure_validity,
            allowed=ENDGAME_CLOSURE_VALIDITIES,
            default="insufficient_truth",
        ),
        "endgame_closure_confidence": _normalize_enum(
            endgame_closure_confidence,
            allowed=ENDGAME_CLOSURE_CONFIDENCE_LEVELS,
            default="low",
        ),
        "final_closure_class": _normalize_enum(
            final_closure_class,
            allowed=FINAL_CLOSURE_CLASSES,
            default="unknown",
        ),
        "terminal_stop_class": _normalize_enum(
            terminal_stop_class,
            allowed=TERMINAL_STOP_CLASSES,
            default="unknown",
        ),
        "closure_resolution_status": _normalize_enum(
            closure_resolution_status,
            allowed=CLOSURE_RESOLUTION_STATUSES,
            default="unknown",
        ),
        "endgame_primary_reason": endgame_primary_reason,
        "endgame_reason_codes": reason_codes,
        "safely_closed": bool(safely_closed),
        "completed_but_not_closed": bool(completed_but_not_closed),
        "rollback_complete_but_not_closed": bool(rollback_complete_but_not_closed),
        "manual_closure_only": bool(manual_closure_only),
        "external_truth_pending": bool(external_truth_pending),
        "closure_unresolved": bool(closure_unresolved),
        "terminal_success": bool(terminal_success),
        "terminal_non_success": bool(terminal_non_success),
        "operator_followup_required": bool(operator_followup_required),
        "further_retry_allowed": bool(further_retry_allowed),
        "further_reentry_allowed": bool(further_reentry_allowed),
        "endgame_source_posture": _normalize_enum(
            endgame_source_posture,
            allowed=ENDGAME_SOURCE_POSTURES,
            default="insufficient_truth",
        ),
        "verification_status": verification_status or "unknown",
        "verification_outcome": verification_outcome or "unknown",
        "closure_status": closure_status or "unknown",
        "closure_decision": closure_decision or "cannot_determine",
        "retry_loop_status": retry_loop_status or "unknown",
        "retry_loop_decision": retry_loop_decision or "unknown",
        "retry_allowed": bool(retry_allowed),
        "reentry_allowed": bool(reentry_allowed),
        "retry_exhausted": bool(retry_exhausted),
        "reentry_exhausted": bool(reentry_exhausted),
        "same_failure_exhausted": bool(same_failure_exhausted),
        "terminal_stop_required": bool(terminal_stop_required),
        "manual_escalation_required": bool(manual_escalation_required),
        "execution_result_status": execution_result_status or "unknown",
        "execution_result_outcome": execution_result_outcome or "unknown",
        "bounded_execution_bridge_status": bounded_execution_bridge_status or "unknown",
        "execution_authorization_status": execution_authorization_status or "unknown",
        "supporting_compact_truth_refs": _build_supporting_refs(
            next_safe_hint=next_safe_hint,
            policy_primary_action=policy_primary_action,
            policy_status=policy_status,
            lifecycle_closure_status=lifecycle_closure_status,
            lifecycle_primary_closure_issue=lifecycle_primary_closure_issue,
            completion_status=completion_status,
            completion_blocked_reason=completion_blocked_reason,
            approval_status=approval_status,
            approval_blocked_reason=approval_blocked_reason,
            reconcile_status=reconcile_status,
            reconcile_primary_mismatch=reconcile_primary_mismatch,
            execution_authorization_status=execution_authorization_status,
            bounded_execution_bridge_status=bounded_execution_bridge_status,
            execution_result_status=execution_result_status,
            execution_result_outcome=execution_result_outcome,
            verification_status=verification_status,
            verification_outcome=verification_outcome,
            closure_status=closure_status,
            closure_decision=closure_decision,
            retry_loop_status=retry_loop_status,
            retry_loop_decision=retry_loop_decision,
            retry_allowed=retry_allowed,
            reentry_allowed=reentry_allowed,
            retry_exhausted=retry_exhausted,
            reentry_exhausted=reentry_exhausted,
            same_failure_exhausted=same_failure_exhausted,
            terminal_stop_required=terminal_stop_required,
            manual_escalation_required=manual_escalation_required,
        ),
    }

    if completion_blocked_reason:
        payload["completion_blocked_reason"] = completion_blocked_reason
    if approval_blocked_reason:
        payload["approval_blocked_reason"] = approval_blocked_reason
    if reconcile_primary_mismatch:
        payload["reconcile_primary_mismatch"] = reconcile_primary_mismatch
    if closure_followup_hint:
        payload["closure_followup_hint"] = closure_followup_hint
    if retry_hint:
        payload["retry_hint"] = retry_hint
    if reentry_hint:
        payload["reentry_hint"] = reentry_hint
    if next_safe_hint:
        payload["next_safe_hint"] = next_safe_hint
    if result_artifact_path:
        payload["result_artifact_path"] = result_artifact_path
    if execution_receipt_path:
        payload["execution_receipt_path"] = execution_receipt_path

    # Invariant hardening.
    payload["safely_closed"] = payload["endgame_closure_status"] == "safely_closed"
    payload["completed_but_not_closed"] = payload["final_closure_class"] == "completed_but_not_closed"
    payload["rollback_complete_but_not_closed"] = (
        payload["final_closure_class"] == "rollback_complete_but_not_closed"
    )
    payload["manual_closure_only"] = payload["final_closure_class"] == "manual_closure_only"
    payload["external_truth_pending"] = payload["final_closure_class"] == "external_truth_pending"
    payload["closure_unresolved"] = payload["final_closure_class"] == "closure_unresolved"

    payload["terminal_success"] = payload["terminal_stop_class"] == "terminal_success"
    payload["terminal_non_success"] = payload["terminal_stop_class"] in {
        "terminal_non_success",
        "manual_terminal",
        "closure_unresolved_terminal",
    }

    if payload["safely_closed"]:
        payload["final_closure_class"] = "safely_closed"
        payload["endgame_closure_outcome"] = "terminal_success_closed"
        payload["closure_resolution_status"] = "resolved"
        payload["terminal_stop_class"] = "terminal_success"
        payload["operator_followup_required"] = False
        payload["further_retry_allowed"] = False
        payload["further_reentry_allowed"] = False
        payload["terminal_success"] = True
        payload["terminal_non_success"] = False

    payload["further_retry_allowed"] = bool(payload["further_retry_allowed"]) and bool(
        payload["retry_allowed"]
    )
    payload["further_reentry_allowed"] = bool(payload["further_reentry_allowed"]) and bool(
        payload["reentry_allowed"]
    )
    if payload["terminal_stop_required"] and payload["terminal_stop_class"] in {
        "terminal_non_success",
        "manual_terminal",
        "closure_unresolved_terminal",
    }:
        payload["further_retry_allowed"] = False
        payload["further_reentry_allowed"] = False

    payload["endgame_closure_status"] = _normalize_enum(
        payload.get("endgame_closure_status"),
        allowed=ENDGAME_CLOSURE_STATUSES,
        default="insufficient_truth",
    )
    payload["endgame_closure_outcome"] = _normalize_enum(
        payload.get("endgame_closure_outcome"),
        allowed=ENDGAME_CLOSURE_OUTCOMES,
        default="unknown",
    )
    payload["endgame_closure_validity"] = _normalize_enum(
        payload.get("endgame_closure_validity"),
        allowed=ENDGAME_CLOSURE_VALIDITIES,
        default="insufficient_truth",
    )
    payload["endgame_closure_confidence"] = _normalize_enum(
        payload.get("endgame_closure_confidence"),
        allowed=ENDGAME_CLOSURE_CONFIDENCE_LEVELS,
        default="low",
    )
    payload["final_closure_class"] = _normalize_enum(
        payload.get("final_closure_class"),
        allowed=FINAL_CLOSURE_CLASSES,
        default="unknown",
    )
    payload["terminal_stop_class"] = _normalize_enum(
        payload.get("terminal_stop_class"),
        allowed=TERMINAL_STOP_CLASSES,
        default="unknown",
    )
    payload["closure_resolution_status"] = _normalize_enum(
        payload.get("closure_resolution_status"),
        allowed=CLOSURE_RESOLUTION_STATUSES,
        default="unknown",
    )
    payload["endgame_source_posture"] = _normalize_enum(
        payload.get("endgame_source_posture"),
        allowed=ENDGAME_SOURCE_POSTURES,
        default="insufficient_truth",
    )

    normalized_reason_codes = _normalize_reason_codes(
        _ordered_unique([payload.get("endgame_primary_reason", ""), *payload.get("endgame_reason_codes", [])])
    )
    if not normalized_reason_codes:
        normalized_reason_codes = ["no_reason"]
    payload["endgame_reason_codes"] = normalized_reason_codes
    payload["endgame_primary_reason"] = normalized_reason_codes[0]

    return payload


def build_endgame_closure_run_state_summary_surface(
    endgame_closure_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(endgame_closure_payload or {})
    status = _normalize_enum(
        payload.get("endgame_closure_status"),
        allowed=ENDGAME_CLOSURE_STATUSES,
        default="insufficient_truth",
    )
    outcome = _normalize_enum(
        payload.get("endgame_closure_outcome"),
        allowed=ENDGAME_CLOSURE_OUTCOMES,
        default="unknown",
    )
    validity = _normalize_enum(
        payload.get("endgame_closure_validity"),
        allowed=ENDGAME_CLOSURE_VALIDITIES,
        default="insufficient_truth",
    )
    confidence = _normalize_enum(
        payload.get("endgame_closure_confidence"),
        allowed=ENDGAME_CLOSURE_CONFIDENCE_LEVELS,
        default="low",
    )
    final_class = _normalize_enum(
        payload.get("final_closure_class"),
        allowed=FINAL_CLOSURE_CLASSES,
        default="unknown",
    )
    terminal_class = _normalize_enum(
        payload.get("terminal_stop_class"),
        allowed=TERMINAL_STOP_CLASSES,
        default="unknown",
    )
    resolution = _normalize_enum(
        payload.get("closure_resolution_status"),
        allowed=CLOSURE_RESOLUTION_STATUSES,
        default="unknown",
    )
    primary_reason = _normalize_text(payload.get("endgame_primary_reason"), default="")
    if not primary_reason or primary_reason not in ENDGAME_REASON_CODES:
        primary_reason = (
            "safely_closed"
            if status == "safely_closed"
            else "manual_closure_only"
            if status == "manual_only"
            else "external_truth_pending"
            if final_class == "external_truth_pending"
            else "insufficient_endgame_truth"
            if status == "insufficient_truth"
            else "unknown"
        )

    present = bool(payload.get("endgame_closure_contract_present", False)) or bool(
        status or outcome or final_class
    )

    safely_closed = status == "safely_closed"
    completed_but_not_closed = final_class == "completed_but_not_closed"
    rollback_complete_but_not_closed = final_class == "rollback_complete_but_not_closed"
    manual_closure_only = final_class == "manual_closure_only"
    external_truth_pending = final_class == "external_truth_pending"
    closure_unresolved = final_class == "closure_unresolved"
    terminal_success = terminal_class == "terminal_success"
    terminal_non_success = terminal_class in {
        "terminal_non_success",
        "manual_terminal",
        "closure_unresolved_terminal",
    }
    operator_followup_required = not safely_closed

    further_retry_allowed = _normalize_bool(payload.get("further_retry_allowed")) and _normalize_bool(
        payload.get("retry_allowed")
    )
    further_reentry_allowed = _normalize_bool(payload.get("further_reentry_allowed")) and _normalize_bool(
        payload.get("reentry_allowed")
    )
    if terminal_class in {"terminal_non_success", "manual_terminal", "closure_unresolved_terminal"}:
        further_retry_allowed = False
        further_reentry_allowed = False

    if safely_closed:
        further_retry_allowed = False
        further_reentry_allowed = False

    return {
        "endgame_closure_contract_present": bool(present),
        "endgame_closure_status": status,
        "endgame_closure_outcome": outcome,
        "endgame_closure_validity": validity,
        "endgame_closure_confidence": confidence,
        "final_closure_class": final_class,
        "terminal_stop_class": terminal_class,
        "closure_resolution_status": resolution,
        "endgame_primary_reason": primary_reason,
        "safely_closed": bool(safely_closed),
        "completed_but_not_closed": bool(completed_but_not_closed),
        "rollback_complete_but_not_closed": bool(rollback_complete_but_not_closed),
        "manual_closure_only": bool(manual_closure_only),
        "external_truth_pending": bool(external_truth_pending),
        "closure_unresolved": bool(closure_unresolved),
        "terminal_success": bool(terminal_success),
        "terminal_non_success": bool(terminal_non_success),
        "operator_followup_required": bool(operator_followup_required),
        "further_retry_allowed": bool(further_retry_allowed),
        "further_reentry_allowed": bool(further_reentry_allowed),
    }

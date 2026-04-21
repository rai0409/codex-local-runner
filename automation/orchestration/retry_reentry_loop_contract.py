from __future__ import annotations

from typing import Any
from typing import Mapping

RETRY_REENTRY_LOOP_CONTRACT_SCHEMA_VERSION = "v1"

RETRY_LOOP_STATUSES = {
    "retry_ready",
    "reentry_ready",
    "stop_required",
    "exhausted",
    "not_applicable",
    "insufficient_truth",
}

RETRY_LOOP_DECISIONS = {
    "same_lane_retry",
    "repair_retry",
    "recollect",
    "replan",
    "escalate_manual",
    "stop_terminal",
    "hold",
    "not_applicable",
}

RETRY_LOOP_VALIDITIES = {
    "valid",
    "partial",
    "malformed",
    "insufficient_truth",
}

RETRY_LOOP_CONFIDENCE_LEVELS = {
    "high",
    "medium",
    "low",
}

RETRY_CLASSES = {
    "same_lane",
    "repair",
    "none",
    "unknown",
}

REENTRY_CLASSES = {
    "recollect",
    "replan",
    "manual_escalation",
    "none",
    "unknown",
}

LOOP_STOP_REASONS = {
    "retry_exhausted",
    "reentry_exhausted",
    "same_failure_exhausted",
    "verification_terminal_failure",
    "manual_closure_only",
    "closure_ready",
    "insufficient_truth",
    "unstable_loop",
    "no_progress",
    "not_applicable",
    "unknown",
}

RETRY_LOOP_SOURCE_POSTURES = {
    "post_verification_loop_decision",
    "insufficient_truth",
    "not_applicable",
}

RETRY_LOOP_REASON_CODES = {
    "malformed_loop_inputs",
    "insufficient_loop_truth",
    "closure_ready",
    "manual_escalation_required",
    "retry_exhausted",
    "reentry_exhausted",
    "same_failure_exhausted",
    "unstable_loop",
    "no_progress",
    "verification_terminal_failure",
    "replan_required",
    "recollect_required",
    "repair_retry_allowed",
    "same_lane_retry_allowed",
    "non_terminal_hold",
    "not_applicable",
    "unknown",
    "no_reason",
}

RETRY_LOOP_REASON_ORDER = (
    "malformed_loop_inputs",
    "insufficient_loop_truth",
    "closure_ready",
    "manual_escalation_required",
    "retry_exhausted",
    "reentry_exhausted",
    "same_failure_exhausted",
    "unstable_loop",
    "no_progress",
    "verification_terminal_failure",
    "replan_required",
    "recollect_required",
    "repair_retry_allowed",
    "same_lane_retry_allowed",
    "non_terminal_hold",
    "not_applicable",
    "unknown",
    "no_reason",
)

RETRY_REENTRY_LOOP_RUN_STATE_SUMMARY_SAFE_FIELDS = (
    "retry_reentry_loop_contract_present",
    "retry_loop_status",
    "retry_loop_decision",
    "retry_loop_validity",
    "retry_loop_confidence",
    "loop_primary_reason",
    "attempt_count",
    "max_attempt_count",
    "reentry_count",
    "max_reentry_count",
    "same_failure_count",
    "max_same_failure_count",
    "retry_allowed",
    "reentry_allowed",
    "retry_exhausted",
    "reentry_exhausted",
    "same_failure_exhausted",
    "terminal_stop_required",
    "manual_escalation_required",
    "replan_required",
    "recollect_required",
    "same_lane_retry_allowed",
    "repair_retry_allowed",
    "no_progress_stop_required",
)

_DEFAULT_MAX_ATTEMPT_COUNT = 2
_DEFAULT_MAX_REENTRY_COUNT = 2
_DEFAULT_MAX_SAME_FAILURE_COUNT = 2

_ALLOWED_SUPPORTING_REFS = (
    "run_state.next_safe_action",
    "run_state.policy_primary_action",
    "run_state.policy_status",
    "run_state.loop_state",
    "run_state.retry_budget_remaining",
    "run_state.prior_attempt_count",
    "run_state.prior_retry_class",
    "completion_contract.completion_status",
    "completion_contract.completion_blocked_reason",
    "approval_transport.approval_status",
    "approval_transport.approval_blocked_reason",
    "reconcile_contract.reconcile_status",
    "reconcile_contract.reconcile_primary_mismatch",
    "repair_suggestion_contract.repair_suggestion_status",
    "repair_suggestion_contract.repair_suggestion_decision",
    "repair_plan_transport.repair_plan_status",
    "repair_plan_transport.repair_plan_decision",
    "repair_approval_binding.repair_approval_binding_status",
    "execution_authorization_gate.execution_authorization_status",
    "bounded_execution_bridge.bounded_execution_status",
    "bounded_execution_bridge.bounded_execution_decision",
    "execution_result_contract.execution_result_status",
    "execution_result_contract.execution_result_outcome",
    "verification_closure_contract.verification_status",
    "verification_closure_contract.verification_outcome",
    "verification_closure_contract.closure_status",
    "verification_closure_contract.closure_decision",
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


def _normalize_non_negative_int(value: Any, *, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return int(text)
    return max(0, default)


def _normalize_positive_int(value: Any, *, default: int) -> int:
    candidate = _normalize_non_negative_int(value, default=default)
    return candidate if candidate > 0 else default


def _normalize_enum(value: Any, *, allowed: set[str], default: str) -> str:
    text = _normalize_text(value, default="")
    if text in allowed:
        return text
    return default


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = _normalize_text(value, default="")
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _normalize_reason_codes(values: list[str]) -> list[str]:
    filtered = [value for value in _ordered_unique(values) if value in RETRY_LOOP_REASON_CODES]
    ordered: list[str] = []
    for reason in RETRY_LOOP_REASON_ORDER:
        if reason in filtered:
            ordered.append(reason)
    return ordered


def _build_supporting_refs(
    *,
    next_safe_action: str,
    policy_primary_action: str,
    policy_status: str,
    loop_state: str,
    retry_budget_remaining: str,
    prior_attempt_count: str,
    prior_retry_class: str,
    completion_status: str,
    completion_blocked_reason: str,
    approval_status: str,
    approval_blocked_reason: str,
    reconcile_status: str,
    reconcile_primary_mismatch: str,
    repair_suggestion_status: str,
    repair_suggestion_decision: str,
    repair_plan_status: str,
    repair_plan_decision: str,
    repair_approval_binding_status: str,
    execution_authorization_status: str,
    bounded_execution_bridge_status: str,
    bounded_execution_bridge_decision: str,
    execution_result_status: str,
    execution_result_outcome: str,
    verification_status: str,
    verification_outcome: str,
    closure_status: str,
    closure_decision: str,
) -> list[str]:
    refs: list[str] = []
    if next_safe_action:
        refs.append("run_state.next_safe_action")
    if policy_primary_action:
        refs.append("run_state.policy_primary_action")
    if policy_status:
        refs.append("run_state.policy_status")
    if loop_state:
        refs.append("run_state.loop_state")
    if retry_budget_remaining:
        refs.append("run_state.retry_budget_remaining")
    if prior_attempt_count:
        refs.append("run_state.prior_attempt_count")
    if prior_retry_class:
        refs.append("run_state.prior_retry_class")
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
    if repair_suggestion_status:
        refs.append("repair_suggestion_contract.repair_suggestion_status")
    if repair_suggestion_decision:
        refs.append("repair_suggestion_contract.repair_suggestion_decision")
    if repair_plan_status:
        refs.append("repair_plan_transport.repair_plan_status")
    if repair_plan_decision:
        refs.append("repair_plan_transport.repair_plan_decision")
    if repair_approval_binding_status:
        refs.append("repair_approval_binding.repair_approval_binding_status")
    if execution_authorization_status:
        refs.append("execution_authorization_gate.execution_authorization_status")
    if bounded_execution_bridge_status:
        refs.append("bounded_execution_bridge.bounded_execution_status")
    if bounded_execution_bridge_decision:
        refs.append("bounded_execution_bridge.bounded_execution_decision")
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

    ordered: list[str] = []
    for allowed in _ALLOWED_SUPPORTING_REFS:
        if allowed in refs and allowed not in ordered:
            ordered.append(allowed)
    return ordered


def build_retry_reentry_loop_contract_surface(
    *,
    run_id: str,
    completion_contract_payload: Mapping[str, Any] | None,
    approval_transport_payload: Mapping[str, Any] | None,
    reconcile_contract_payload: Mapping[str, Any] | None,
    repair_suggestion_contract_payload: Mapping[str, Any] | None,
    repair_plan_transport_payload: Mapping[str, Any] | None,
    repair_approval_binding_payload: Mapping[str, Any] | None,
    execution_authorization_gate_payload: Mapping[str, Any] | None,
    bounded_execution_bridge_payload: Mapping[str, Any] | None,
    execution_result_contract_payload: Mapping[str, Any] | None,
    verification_closure_contract_payload: Mapping[str, Any] | None,
    run_state_payload: Mapping[str, Any] | None,
    artifact_presence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    completion = dict(completion_contract_payload or {})
    approval = dict(approval_transport_payload or {})
    reconcile = dict(reconcile_contract_payload or {})
    repair_suggestion = dict(repair_suggestion_contract_payload or {})
    repair_plan = dict(repair_plan_transport_payload or {})
    repair_binding = dict(repair_approval_binding_payload or {})
    authorization = dict(execution_authorization_gate_payload or {})
    bounded_execution = dict(bounded_execution_bridge_payload or {})
    execution_result = dict(execution_result_contract_payload or {})
    verification = dict(verification_closure_contract_payload or {})
    run_state = dict(run_state_payload or {})
    artifacts = dict(artifact_presence or {})

    objective_id = _normalize_text(
        completion.get("objective_id")
        or approval.get("objective_id")
        or reconcile.get("objective_id")
        or repair_suggestion.get("objective_id")
        or repair_plan.get("objective_id")
        or repair_binding.get("objective_id")
        or authorization.get("objective_id")
        or bounded_execution.get("objective_id")
        or execution_result.get("objective_id")
        or verification.get("objective_id")
        or run_state.get("objective_id"),
        default="",
    )

    verification_status_raw = _normalize_text(
        verification.get("verification_status") or run_state.get("verification_status"),
        default="",
    )
    verification_outcome_raw = _normalize_text(
        verification.get("verification_outcome") or run_state.get("verification_outcome"),
        default="",
    )
    verification_validity_raw = _normalize_text(
        verification.get("verification_validity") or run_state.get("verification_validity"),
        default="",
    )
    closure_status_raw = _normalize_text(
        verification.get("closure_status") or run_state.get("closure_status"),
        default="",
    )
    closure_decision_raw = _normalize_text(
        verification.get("closure_decision") or run_state.get("closure_decision"),
        default="",
    )

    execution_result_status_raw = _normalize_text(
        execution_result.get("execution_result_status") or run_state.get("execution_result_status"),
        default="",
    )
    execution_result_outcome_raw = _normalize_text(
        execution_result.get("execution_result_outcome") or run_state.get("execution_result_outcome"),
        default="",
    )
    execution_result_validity_raw = _normalize_text(
        execution_result.get("execution_result_validity")
        or run_state.get("execution_result_validity"),
        default="",
    )
    execution_result_attempted = _normalize_bool(
        execution_result.get("execution_result_attempted")
        if "execution_result_attempted" in execution_result
        else run_state.get("execution_result_attempted")
    )

    bounded_execution_bridge_status = _normalize_text(
        bounded_execution.get("bounded_execution_status") or run_state.get("bounded_execution_status"),
        default="",
    )
    bounded_execution_bridge_decision = _normalize_text(
        bounded_execution.get("bounded_execution_decision")
        or run_state.get("bounded_execution_decision"),
        default="",
    )
    execution_authorization_status = _normalize_text(
        authorization.get("execution_authorization_status")
        or run_state.get("execution_authorization_status"),
        default="",
    )

    repair_suggestion_status = _normalize_text(
        repair_suggestion.get("repair_suggestion_status")
        or run_state.get("repair_suggestion_status"),
        default="",
    )
    repair_suggestion_decision = _normalize_text(
        repair_suggestion.get("repair_suggestion_decision")
        or run_state.get("repair_suggestion_decision"),
        default="",
    )
    repair_plan_status = _normalize_text(
        repair_plan.get("repair_plan_status") or run_state.get("repair_plan_status"),
        default="",
    )
    repair_plan_decision = _normalize_text(
        repair_plan.get("repair_plan_decision") or run_state.get("repair_plan_decision"),
        default="",
    )
    repair_plan_candidate_action = _normalize_text(
        repair_plan.get("repair_plan_candidate_action") or run_state.get("repair_plan_candidate_action"),
        default="",
    )
    repair_approval_binding_status = _normalize_text(
        repair_binding.get("repair_approval_binding_status")
        or run_state.get("repair_approval_binding_status"),
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

    next_safe_hint = _normalize_text(run_state.get("next_safe_action"), default="")
    policy_primary_action = _normalize_text(run_state.get("policy_primary_action"), default="")
    policy_status = _normalize_text(run_state.get("policy_status"), default="")
    loop_state = _normalize_text(run_state.get("loop_state"), default="")

    manual_closure_required = _normalize_bool(
        verification.get("manual_closure_required")
        if "manual_closure_required" in verification
        else run_state.get("manual_closure_required")
    )
    closure_followup_required = _normalize_bool(
        verification.get("closure_followup_required")
        if "closure_followup_required" in verification
        else run_state.get("closure_followup_required")
    )
    external_truth_required = _normalize_bool(
        verification.get("external_truth_required")
        if "external_truth_required" in verification
        else run_state.get("external_truth_required")
    )
    safely_closable = _normalize_bool(
        verification.get("safely_closable")
        if "safely_closable" in verification
        else run_state.get("safely_closable")
    )

    retry_budget_remaining = _normalize_non_negative_int(
        run_state.get("retry_budget_remaining"),
        default=0,
    )
    prior_attempt_count = _normalize_non_negative_int(
        run_state.get("prior_attempt_count"),
        default=0,
    )
    prior_retry_class = _normalize_text(run_state.get("prior_retry_class"), default="")

    attempt_count = _normalize_non_negative_int(
        run_state.get("attempt_count"),
        default=_normalize_non_negative_int(run_state.get("retry_attempt_count"), default=prior_attempt_count),
    )
    if attempt_count <= 0 and execution_result_attempted:
        attempt_count = 1

    reentry_count = _normalize_non_negative_int(
        run_state.get("reentry_count"),
        default=_normalize_non_negative_int(run_state.get("loop_reentry_count"), default=0),
    )
    same_failure_count = _normalize_non_negative_int(
        run_state.get("same_failure_count"),
        default=0,
    )

    derived_failure_signal = (
        execution_result_status_raw in {"failed", "partial", "blocked", "unknown"}
        and verification_status_raw in {"verified_failure", "inconclusive", "not_verifiable"}
    )
    if same_failure_count <= 0 and derived_failure_signal:
        same_failure_count = 1
    if _normalize_bool(run_state.get("no_progress_stop_required")) and same_failure_count < 2:
        same_failure_count = 2

    max_attempt_count = _normalize_positive_int(
        run_state.get("max_attempt_count"),
        default=_DEFAULT_MAX_ATTEMPT_COUNT,
    )
    max_reentry_count = _normalize_positive_int(
        run_state.get("max_reentry_count"),
        default=_DEFAULT_MAX_REENTRY_COUNT,
    )
    max_same_failure_count = _normalize_positive_int(
        run_state.get("max_same_failure_count"),
        default=_DEFAULT_MAX_SAME_FAILURE_COUNT,
    )

    retry_exhausted = attempt_count >= max_attempt_count
    reentry_exhausted = reentry_count >= max_reentry_count
    same_failure_exhausted = same_failure_count >= max_same_failure_count

    malformed_loop_inputs = bool(
        verification_validity_raw == "malformed"
        or execution_result_validity_raw == "malformed"
        or (
            verification_status_raw == "verified_success"
            and closure_decision_raw == "close_ready"
            and closure_status_raw not in {"safely_closable", ""}
        )
    )

    has_loop_truth = any(
        (
            verification_status_raw,
            verification_outcome_raw,
            closure_status_raw,
            closure_decision_raw,
            execution_result_status_raw,
            bounded_execution_bridge_status,
            execution_authorization_status,
            repair_suggestion_status,
            repair_plan_status,
        )
    )
    insufficient_loop_truth = bool(
        not has_loop_truth
        or verification_validity_raw == "insufficient_truth"
        or (
            verification_status_raw in {"", "not_verifiable"}
            and not execution_result_status_raw
            and not repair_suggestion_status
        )
    )

    closure_ready = bool(
        closure_decision_raw == "close_ready"
        or closure_status_raw == "safely_closable"
        or safely_closable
    )
    manual_only = bool(
        manual_closure_required
        or closure_status_raw == "manual_closure_only"
        or closure_decision_raw == "manual_close"
        or verification_outcome_raw == "manual_closure_only"
    )

    unstable_loop_suspected = bool(
        _normalize_bool(run_state.get("unstable_loop_suspected"))
        or (
            attempt_count >= 2
            and same_failure_count >= max(1, max_same_failure_count - 1)
            and verification_status_raw in {"verified_failure", "inconclusive", "not_verifiable"}
        )
    )
    no_progress_stop_required = bool(
        _normalize_bool(run_state.get("no_progress_stop_required"))
        or (
            attempt_count >= 2
            and same_failure_count >= 2
            and verification_outcome_raw
            in {"objective_gap", "completion_gap", "closure_followup", "unknown", "not_verifiable"}
        )
    )

    explicit_replan_required = bool(
        _normalize_bool(run_state.get("replan_required"))
        or _normalize_bool(run_state.get("repair_replan_required"))
        or _normalize_bool(run_state.get("repair_plan_replan_required"))
        or _normalize_bool(run_state.get("repair_approval_binding_replan_required"))
        or repair_suggestion_decision == "request_replan"
        or repair_plan_decision == "prepare_replan_plan"
        or completion_status == "replan_before_closure"
    )
    explicit_recollect_required = bool(
        _normalize_bool(run_state.get("recollect_required"))
        or _normalize_bool(run_state.get("repair_truth_gathering_required"))
        or _normalize_bool(run_state.get("repair_plan_truth_gathering_required"))
        or _normalize_bool(run_state.get("repair_approval_binding_truth_gathering_required"))
        or external_truth_required
        or verification_outcome_raw == "external_truth_pending"
        or closure_decision_raw == "await_external_truth"
        or repair_suggestion_decision == "gather_truth"
        or repair_plan_decision == "prepare_truth_gathering_plan"
        or repair_plan_candidate_action == "gather_missing_truth"
    )

    explicit_repair_retry_allowed = bool(
        not explicit_replan_required
        and not explicit_recollect_required
        and not manual_only
        and execution_result_status_raw in {"failed", "partial", "blocked", "unknown"}
        and (
            closure_followup_required
            or verification_outcome_raw == "closure_followup"
            or repair_plan_candidate_action == "request_closure_followup"
            or repair_suggestion_decision == "closure_followup"
        )
    )
    explicit_same_lane_retry_allowed = bool(
        not explicit_replan_required
        and not explicit_recollect_required
        and not manual_only
        and not closure_ready
        and execution_result_status_raw in {"failed", "partial"}
        and verification_status_raw in {"verified_failure", "inconclusive"}
        and bounded_execution_bridge_status in {"ready", "deferred"}
        and execution_authorization_status in {"eligible", "pending"}
    )

    non_terminal_hold = bool(
        not closure_ready
        and not manual_only
        and not retry_exhausted
        and not reentry_exhausted
        and not same_failure_exhausted
        and not unstable_loop_suspected
        and not no_progress_stop_required
        and not explicit_replan_required
        and not explicit_recollect_required
        and not explicit_repair_retry_allowed
        and not explicit_same_lane_retry_allowed
    )

    lead = ""
    if malformed_loop_inputs:
        lead = "malformed_loop_inputs"
    elif insufficient_loop_truth:
        lead = "insufficient_loop_truth"
    elif closure_ready:
        lead = "closure_ready"
    elif manual_only:
        lead = "manual_escalation_required"
    elif retry_exhausted:
        lead = "retry_exhausted"
    elif reentry_exhausted:
        lead = "reentry_exhausted"
    elif same_failure_exhausted:
        lead = "same_failure_exhausted"
    elif unstable_loop_suspected or no_progress_stop_required:
        lead = "no_progress" if no_progress_stop_required else "unstable_loop"
    elif explicit_replan_required:
        lead = "replan_required"
    elif explicit_recollect_required:
        lead = "recollect_required"
    elif explicit_repair_retry_allowed:
        lead = "repair_retry_allowed"
    elif explicit_same_lane_retry_allowed:
        lead = "same_lane_retry_allowed"
    elif non_terminal_hold:
        lead = "non_terminal_hold"
    else:
        lead = "not_applicable"

    retry_loop_status = "insufficient_truth"
    retry_loop_decision = "hold"
    retry_loop_validity = "insufficient_truth"
    retry_loop_confidence = "low"
    retry_class = "unknown"
    reentry_class = "unknown"
    loop_stop_reason = "unknown"
    retry_allowed = False
    reentry_allowed = False
    terminal_stop_required = False
    manual_escalation_required = False
    replan_required = False
    recollect_required = False
    same_lane_retry_allowed = False
    repair_retry_allowed = False

    if lead == "malformed_loop_inputs":
        retry_loop_status = "insufficient_truth"
        retry_loop_decision = "hold"
        retry_loop_validity = "malformed"
        retry_loop_confidence = "low"
        retry_class = "unknown"
        reentry_class = "unknown"
        loop_stop_reason = "unknown"
    elif lead == "insufficient_loop_truth":
        retry_loop_status = "insufficient_truth"
        retry_loop_decision = "hold"
        retry_loop_validity = "insufficient_truth"
        retry_loop_confidence = "low"
        retry_class = "unknown"
        reentry_class = "unknown"
        loop_stop_reason = "insufficient_truth"
    elif lead == "closure_ready":
        retry_loop_status = "not_applicable"
        retry_loop_decision = "not_applicable"
        retry_loop_validity = "valid"
        retry_loop_confidence = "high"
        retry_class = "none"
        reentry_class = "none"
        loop_stop_reason = "closure_ready"
    elif lead == "manual_escalation_required":
        retry_loop_status = "stop_required"
        retry_loop_decision = "escalate_manual"
        retry_loop_validity = "valid"
        retry_loop_confidence = "medium"
        retry_class = "none"
        reentry_class = "manual_escalation"
        loop_stop_reason = "manual_closure_only"
        manual_escalation_required = True
        terminal_stop_required = True
    elif lead in {"retry_exhausted", "reentry_exhausted", "same_failure_exhausted"}:
        retry_loop_status = "exhausted"
        retry_loop_decision = "stop_terminal"
        retry_loop_validity = "valid"
        retry_loop_confidence = "medium"
        retry_class = "none"
        reentry_class = "none"
        loop_stop_reason = {
            "retry_exhausted": "retry_exhausted",
            "reentry_exhausted": "reentry_exhausted",
            "same_failure_exhausted": "same_failure_exhausted",
        }[lead]
        terminal_stop_required = True
    elif lead in {"unstable_loop", "no_progress"}:
        retry_loop_status = "stop_required"
        retry_loop_decision = "stop_terminal"
        retry_loop_validity = "partial"
        retry_loop_confidence = "low"
        retry_class = "none"
        reentry_class = "none"
        loop_stop_reason = "no_progress" if lead == "no_progress" else "unstable_loop"
        terminal_stop_required = True
        unstable_loop_suspected = True
        if lead == "no_progress":
            no_progress_stop_required = True
    elif lead == "replan_required":
        retry_loop_status = "reentry_ready"
        retry_loop_decision = "replan"
        retry_loop_validity = "valid"
        retry_loop_confidence = "medium"
        retry_class = "none"
        reentry_class = "replan"
        reentry_allowed = True
        replan_required = True
        loop_stop_reason = "unknown"
    elif lead == "recollect_required":
        retry_loop_status = "reentry_ready"
        retry_loop_decision = "recollect"
        retry_loop_validity = "partial"
        retry_loop_confidence = "medium"
        retry_class = "none"
        reentry_class = "recollect"
        reentry_allowed = True
        recollect_required = True
        loop_stop_reason = "unknown"
    elif lead == "repair_retry_allowed":
        retry_loop_status = "retry_ready"
        retry_loop_decision = "repair_retry"
        retry_loop_validity = "partial"
        retry_loop_confidence = "medium"
        retry_class = "repair"
        reentry_class = "none"
        retry_allowed = True
        repair_retry_allowed = True
        loop_stop_reason = "unknown"
    elif lead == "same_lane_retry_allowed":
        retry_loop_status = "retry_ready"
        retry_loop_decision = "same_lane_retry"
        retry_loop_validity = "valid"
        retry_loop_confidence = "high"
        retry_class = "same_lane"
        reentry_class = "none"
        retry_allowed = True
        same_lane_retry_allowed = True
        loop_stop_reason = "unknown"
    elif lead == "non_terminal_hold":
        retry_loop_status = "stop_required"
        retry_loop_decision = "hold"
        retry_loop_validity = "partial"
        retry_loop_confidence = "low"
        retry_class = "unknown"
        reentry_class = "unknown"
        loop_stop_reason = "unknown"
    else:
        retry_loop_status = "not_applicable"
        retry_loop_decision = "not_applicable"
        retry_loop_validity = "partial"
        retry_loop_confidence = "low"
        retry_class = "none"
        reentry_class = "none"
        loop_stop_reason = "not_applicable"

    if retry_loop_decision == "same_lane_retry":
        same_lane_retry_allowed = True
        retry_allowed = True
        retry_class = "same_lane"
    else:
        same_lane_retry_allowed = False
        if retry_class == "same_lane":
            retry_class = "none"

    if retry_loop_decision == "repair_retry":
        repair_retry_allowed = True
        retry_allowed = True
        retry_class = "repair"
    else:
        repair_retry_allowed = False
        if retry_class == "repair":
            retry_class = "none"

    if retry_loop_decision == "recollect":
        recollect_required = True
        reentry_allowed = True
        reentry_class = "recollect"
    else:
        recollect_required = False
        if reentry_class == "recollect":
            reentry_class = "none"

    if retry_loop_decision == "replan":
        replan_required = True
        reentry_allowed = True
        reentry_class = "replan"
    else:
        replan_required = False
        if reentry_class == "replan":
            reentry_class = "none"

    if retry_loop_decision == "escalate_manual":
        manual_escalation_required = True
        reentry_class = "manual_escalation"
        terminal_stop_required = True
    else:
        if reentry_class == "manual_escalation":
            reentry_class = "none"

    if retry_loop_decision == "stop_terminal":
        terminal_stop_required = True

    if retry_loop_status == "retry_ready":
        retry_allowed = True
    if retry_loop_status == "reentry_ready":
        reentry_allowed = True
    if retry_loop_status == "not_applicable":
        retry_allowed = False
        reentry_allowed = False
    if retry_loop_status == "exhausted" and not (
        retry_exhausted or reentry_exhausted or same_failure_exhausted
    ):
        retry_exhausted = True

    if no_progress_stop_required:
        terminal_stop_required = True
    if terminal_stop_required:
        retry_allowed = False
        reentry_allowed = False

    if retry_loop_status == "retry_ready":
        retry_class = _normalize_enum(retry_class, allowed=RETRY_CLASSES, default="same_lane")
        if retry_class not in {"same_lane", "repair"}:
            retry_class = "same_lane"
    elif retry_class not in {"none", "unknown"}:
        retry_class = "none"

    if retry_loop_status == "reentry_ready":
        reentry_class = _normalize_enum(reentry_class, allowed=REENTRY_CLASSES, default="replan")
        if reentry_class not in {"recollect", "replan"}:
            reentry_class = "replan"
    elif retry_loop_decision == "escalate_manual":
        reentry_class = "manual_escalation"
    elif reentry_class not in {"none", "unknown"}:
        reentry_class = "none"

    if closure_ready and retry_loop_status != "not_applicable":
        retry_loop_status = "not_applicable"
        retry_loop_decision = "not_applicable"
        retry_loop_validity = "valid"
        retry_loop_confidence = "high"
        retry_allowed = False
        reentry_allowed = False
        retry_class = "none"
        reentry_class = "none"
        terminal_stop_required = False
        manual_escalation_required = False
        replan_required = False
        recollect_required = False
        same_lane_retry_allowed = False
        repair_retry_allowed = False
        loop_stop_reason = "closure_ready"

    if retry_loop_status in {"insufficient_truth"}:
        retry_loop_confidence = "low"

    if loop_stop_reason not in LOOP_STOP_REASONS:
        if retry_loop_status == "exhausted":
            if retry_exhausted:
                loop_stop_reason = "retry_exhausted"
            elif reentry_exhausted:
                loop_stop_reason = "reentry_exhausted"
            elif same_failure_exhausted:
                loop_stop_reason = "same_failure_exhausted"
            else:
                loop_stop_reason = "unknown"
        elif retry_loop_status == "not_applicable":
            loop_stop_reason = "not_applicable"
        elif retry_loop_status == "insufficient_truth":
            loop_stop_reason = "insufficient_truth"
        elif terminal_stop_required and manual_escalation_required:
            loop_stop_reason = "manual_closure_only"
        elif terminal_stop_required and no_progress_stop_required:
            loop_stop_reason = "no_progress"
        elif terminal_stop_required and unstable_loop_suspected:
            loop_stop_reason = "unstable_loop"
        elif terminal_stop_required and verification_status_raw == "verified_failure":
            loop_stop_reason = "verification_terminal_failure"
        else:
            loop_stop_reason = "unknown"

    retry_loop_source_posture = "post_verification_loop_decision"
    if retry_loop_status == "not_applicable":
        retry_loop_source_posture = "not_applicable"
    elif retry_loop_status == "insufficient_truth":
        retry_loop_source_posture = "insufficient_truth"

    reason_candidates: list[str] = [lead]
    if manual_escalation_required:
        reason_candidates.append("manual_escalation_required")
    if retry_exhausted:
        reason_candidates.append("retry_exhausted")
    if reentry_exhausted:
        reason_candidates.append("reentry_exhausted")
    if same_failure_exhausted:
        reason_candidates.append("same_failure_exhausted")
    if unstable_loop_suspected:
        reason_candidates.append("unstable_loop")
    if no_progress_stop_required:
        reason_candidates.append("no_progress")
    if retry_loop_decision == "same_lane_retry":
        reason_candidates.append("same_lane_retry_allowed")
    if retry_loop_decision == "repair_retry":
        reason_candidates.append("repair_retry_allowed")
    if retry_loop_decision == "recollect":
        reason_candidates.append("recollect_required")
    if retry_loop_decision == "replan":
        reason_candidates.append("replan_required")
    if retry_loop_decision == "hold":
        reason_candidates.append("non_terminal_hold")
    if retry_loop_decision == "not_applicable":
        reason_candidates.append("not_applicable")
    if terminal_stop_required and verification_status_raw == "verified_failure":
        reason_candidates.append("verification_terminal_failure")

    reason_codes = _normalize_reason_codes(reason_candidates)
    if not reason_codes:
        reason_codes = ["no_reason"]
    loop_primary_reason = reason_codes[0]

    retry_hint = ""
    if retry_loop_decision == "same_lane_retry":
        retry_hint = "same_lane_retry"
    elif retry_loop_decision == "repair_retry":
        retry_hint = "repair_retry"

    reentry_hint = ""
    if retry_loop_decision == "recollect":
        reentry_hint = "recollect"
    elif retry_loop_decision == "replan":
        reentry_hint = "replan"
    elif retry_loop_decision == "escalate_manual":
        reentry_hint = "manual_escalation"

    closure_followup_hint = _normalize_text(
        verification.get("closure_followup_hint") or run_state.get("lifecycle_primary_closure_issue"),
        default="",
    )

    payload: dict[str, Any] = {
        "schema_version": RETRY_REENTRY_LOOP_CONTRACT_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "retry_loop_status": _normalize_enum(
            retry_loop_status,
            allowed=RETRY_LOOP_STATUSES,
            default="insufficient_truth",
        ),
        "retry_loop_decision": _normalize_enum(
            retry_loop_decision,
            allowed=RETRY_LOOP_DECISIONS,
            default="hold",
        ),
        "retry_loop_validity": _normalize_enum(
            retry_loop_validity,
            allowed=RETRY_LOOP_VALIDITIES,
            default="insufficient_truth",
        ),
        "retry_loop_confidence": _normalize_enum(
            retry_loop_confidence,
            allowed=RETRY_LOOP_CONFIDENCE_LEVELS,
            default="low",
        ),
        "attempt_count": _normalize_non_negative_int(attempt_count, default=0),
        "max_attempt_count": _normalize_positive_int(
            max_attempt_count,
            default=_DEFAULT_MAX_ATTEMPT_COUNT,
        ),
        "reentry_count": _normalize_non_negative_int(reentry_count, default=0),
        "max_reentry_count": _normalize_positive_int(
            max_reentry_count,
            default=_DEFAULT_MAX_REENTRY_COUNT,
        ),
        "same_failure_count": _normalize_non_negative_int(same_failure_count, default=0),
        "max_same_failure_count": _normalize_positive_int(
            max_same_failure_count,
            default=_DEFAULT_MAX_SAME_FAILURE_COUNT,
        ),
        "retry_class": _normalize_enum(retry_class, allowed=RETRY_CLASSES, default="unknown"),
        "reentry_class": _normalize_enum(reentry_class, allowed=REENTRY_CLASSES, default="unknown"),
        "loop_stop_reason": _normalize_enum(
            loop_stop_reason,
            allowed=LOOP_STOP_REASONS,
            default="unknown",
        ),
        "loop_primary_reason": loop_primary_reason,
        "loop_reason_codes": reason_codes,
        "retry_allowed": bool(retry_allowed),
        "reentry_allowed": bool(reentry_allowed),
        "retry_exhausted": bool(retry_exhausted),
        "reentry_exhausted": bool(reentry_exhausted),
        "same_failure_exhausted": bool(same_failure_exhausted),
        "terminal_stop_required": bool(terminal_stop_required),
        "manual_escalation_required": bool(manual_escalation_required),
        "replan_required": bool(replan_required),
        "recollect_required": bool(recollect_required),
        "repair_retry_allowed": bool(repair_retry_allowed),
        "same_lane_retry_allowed": bool(same_lane_retry_allowed),
        "unstable_loop_suspected": bool(unstable_loop_suspected),
        "no_progress_stop_required": bool(no_progress_stop_required),
        "retry_loop_source_posture": _normalize_enum(
            retry_loop_source_posture,
            allowed=RETRY_LOOP_SOURCE_POSTURES,
            default="insufficient_truth",
        ),
        "verification_status": verification_status_raw or "unknown",
        "verification_outcome": verification_outcome_raw or "unknown",
        "closure_status": closure_status_raw or "unknown",
        "closure_decision": closure_decision_raw or "cannot_determine",
        "execution_result_status": execution_result_status_raw or "unknown",
        "execution_result_outcome": execution_result_outcome_raw or "unknown",
        "bounded_execution_bridge_status": bounded_execution_bridge_status or "unknown",
        "bounded_execution_bridge_decision": bounded_execution_bridge_decision or "unknown",
        "execution_authorization_status": execution_authorization_status or "unknown",
        "supporting_compact_truth_refs": _build_supporting_refs(
            next_safe_action=next_safe_hint,
            policy_primary_action=policy_primary_action,
            policy_status=policy_status,
            loop_state=loop_state,
            retry_budget_remaining=str(retry_budget_remaining) if retry_budget_remaining >= 0 else "",
            prior_attempt_count=str(prior_attempt_count) if prior_attempt_count >= 0 else "",
            prior_retry_class=prior_retry_class,
            completion_status=completion_status,
            completion_blocked_reason=completion_blocked_reason,
            approval_status=approval_status,
            approval_blocked_reason=approval_blocked_reason,
            reconcile_status=reconcile_status,
            reconcile_primary_mismatch=reconcile_primary_mismatch,
            repair_suggestion_status=repair_suggestion_status,
            repair_suggestion_decision=repair_suggestion_decision,
            repair_plan_status=repair_plan_status,
            repair_plan_decision=repair_plan_decision,
            repair_approval_binding_status=repair_approval_binding_status,
            execution_authorization_status=execution_authorization_status,
            bounded_execution_bridge_status=bounded_execution_bridge_status,
            bounded_execution_bridge_decision=bounded_execution_bridge_decision,
            execution_result_status=execution_result_status_raw,
            execution_result_outcome=execution_result_outcome_raw,
            verification_status=verification_status_raw,
            verification_outcome=verification_outcome_raw,
            closure_status=closure_status_raw,
            closure_decision=closure_decision_raw,
        ),
    }

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
    if retry_hint:
        payload["retry_hint"] = retry_hint
    if reentry_hint:
        payload["reentry_hint"] = reentry_hint

    # Status/decision/flag invariants.
    payload["retry_allowed"] = payload["retry_loop_status"] == "retry_ready"
    payload["reentry_allowed"] = payload["retry_loop_status"] == "reentry_ready"

    payload["same_lane_retry_allowed"] = payload["retry_loop_decision"] == "same_lane_retry"
    payload["repair_retry_allowed"] = payload["retry_loop_decision"] == "repair_retry"
    payload["recollect_required"] = payload["retry_loop_decision"] == "recollect"
    payload["replan_required"] = payload["retry_loop_decision"] == "replan"
    payload["manual_escalation_required"] = payload["retry_loop_decision"] == "escalate_manual"
    if payload["retry_loop_decision"] == "stop_terminal":
        payload["terminal_stop_required"] = True

    if payload["retry_loop_status"] == "exhausted" and not (
        payload["retry_exhausted"]
        or payload["reentry_exhausted"]
        or payload["same_failure_exhausted"]
    ):
        payload["retry_exhausted"] = True

    if payload["retry_loop_status"] == "not_applicable":
        payload["retry_allowed"] = False
        payload["reentry_allowed"] = False
        payload["terminal_stop_required"] = False
        payload["manual_escalation_required"] = False
        payload["same_lane_retry_allowed"] = False
        payload["repair_retry_allowed"] = False
        payload["recollect_required"] = False
        payload["replan_required"] = False

    if payload["no_progress_stop_required"]:
        payload["terminal_stop_required"] = True
    if payload["terminal_stop_required"]:
        payload["retry_allowed"] = False
        payload["reentry_allowed"] = False

    if payload["retry_loop_status"] == "retry_ready":
        payload["retry_class"] = "repair" if payload["repair_retry_allowed"] else "same_lane"
        payload["reentry_class"] = "none"
    elif payload["retry_loop_status"] == "reentry_ready":
        payload["retry_class"] = "none"
        if payload["recollect_required"]:
            payload["reentry_class"] = "recollect"
        elif payload["replan_required"]:
            payload["reentry_class"] = "replan"
        else:
            payload["reentry_class"] = "unknown"
    elif payload["manual_escalation_required"]:
        payload["retry_class"] = "none"
        payload["reentry_class"] = "manual_escalation"
    elif payload["retry_loop_status"] == "not_applicable":
        payload["retry_class"] = "none"
        payload["reentry_class"] = "none"

    if payload["retry_loop_status"] == "not_applicable":
        payload["loop_stop_reason"] = "not_applicable" if not closure_ready else "closure_ready"
    elif payload["retry_loop_status"] == "insufficient_truth":
        payload["loop_stop_reason"] = "insufficient_truth"
    elif payload["retry_loop_status"] == "exhausted":
        if payload["retry_exhausted"]:
            payload["loop_stop_reason"] = "retry_exhausted"
        elif payload["reentry_exhausted"]:
            payload["loop_stop_reason"] = "reentry_exhausted"
        elif payload["same_failure_exhausted"]:
            payload["loop_stop_reason"] = "same_failure_exhausted"
    elif payload["terminal_stop_required"]:
        if payload["manual_escalation_required"]:
            payload["loop_stop_reason"] = "manual_closure_only"
        elif payload["no_progress_stop_required"]:
            payload["loop_stop_reason"] = "no_progress"
        elif payload["unstable_loop_suspected"]:
            payload["loop_stop_reason"] = "unstable_loop"
        elif verification_status_raw == "verified_failure":
            payload["loop_stop_reason"] = "verification_terminal_failure"

    if payload["retry_loop_status"] == "not_applicable":
        payload["retry_loop_source_posture"] = "not_applicable"
    elif payload["retry_loop_status"] == "insufficient_truth":
        payload["retry_loop_source_posture"] = "insufficient_truth"
    else:
        payload["retry_loop_source_posture"] = "post_verification_loop_decision"

    if payload["retry_loop_status"] == "not_applicable":
        payload["retry_loop_decision"] = "not_applicable"
        payload["retry_loop_validity"] = "valid"
        payload["retry_loop_confidence"] = "high"

    # Ensure enums remain fixed.
    payload["retry_loop_status"] = _normalize_enum(
        payload.get("retry_loop_status"),
        allowed=RETRY_LOOP_STATUSES,
        default="insufficient_truth",
    )
    payload["retry_loop_decision"] = _normalize_enum(
        payload.get("retry_loop_decision"),
        allowed=RETRY_LOOP_DECISIONS,
        default="hold",
    )
    payload["retry_loop_validity"] = _normalize_enum(
        payload.get("retry_loop_validity"),
        allowed=RETRY_LOOP_VALIDITIES,
        default="insufficient_truth",
    )
    payload["retry_loop_confidence"] = _normalize_enum(
        payload.get("retry_loop_confidence"),
        allowed=RETRY_LOOP_CONFIDENCE_LEVELS,
        default="low",
    )
    payload["retry_class"] = _normalize_enum(
        payload.get("retry_class"),
        allowed=RETRY_CLASSES,
        default="unknown",
    )
    payload["reentry_class"] = _normalize_enum(
        payload.get("reentry_class"),
        allowed=REENTRY_CLASSES,
        default="unknown",
    )
    payload["loop_stop_reason"] = _normalize_enum(
        payload.get("loop_stop_reason"),
        allowed=LOOP_STOP_REASONS,
        default="unknown",
    )
    payload["retry_loop_source_posture"] = _normalize_enum(
        payload.get("retry_loop_source_posture"),
        allowed=RETRY_LOOP_SOURCE_POSTURES,
        default="insufficient_truth",
    )

    # Deterministic reason normalization after invariant repairs.
    normalized_reason_codes = _normalize_reason_codes(
        _ordered_unique([payload.get("loop_primary_reason", ""), *payload.get("loop_reason_codes", [])])
    )
    if not normalized_reason_codes:
        normalized_reason_codes = ["no_reason"]
    payload["loop_reason_codes"] = normalized_reason_codes
    payload["loop_primary_reason"] = normalized_reason_codes[0]

    # Keep source posture conservative when upstream artifacts are missing.
    if not bool(artifacts.get("verification_closure_contract.json")) and payload[
        "retry_loop_source_posture"
    ] == "post_verification_loop_decision":
        payload["retry_loop_source_posture"] = "insufficient_truth"

    return payload


def build_retry_reentry_loop_run_state_summary_surface(
    retry_reentry_loop_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(retry_reentry_loop_payload or {})

    status = _normalize_enum(
        payload.get("retry_loop_status"),
        allowed=RETRY_LOOP_STATUSES,
        default="insufficient_truth",
    )
    decision = _normalize_enum(
        payload.get("retry_loop_decision"),
        allowed=RETRY_LOOP_DECISIONS,
        default="hold",
    )
    validity = _normalize_enum(
        payload.get("retry_loop_validity"),
        allowed=RETRY_LOOP_VALIDITIES,
        default="insufficient_truth",
    )
    confidence = _normalize_enum(
        payload.get("retry_loop_confidence"),
        allowed=RETRY_LOOP_CONFIDENCE_LEVELS,
        default="low",
    )
    primary_reason = _normalize_text(payload.get("loop_primary_reason"), default="")
    if not primary_reason or primary_reason not in RETRY_LOOP_REASON_CODES:
        primary_reason = (
            "same_lane_retry_allowed"
            if decision == "same_lane_retry"
            else "repair_retry_allowed"
            if decision == "repair_retry"
            else "recollect_required"
            if decision == "recollect"
            else "replan_required"
            if decision == "replan"
            else "manual_escalation_required"
            if decision == "escalate_manual"
            else "closure_ready"
            if status == "not_applicable"
            else "insufficient_loop_truth"
            if status == "insufficient_truth"
            else "unknown"
        )

    present = bool(payload.get("retry_reentry_loop_contract_present", False)) or bool(
        status or decision
    )

    attempt_count = _normalize_non_negative_int(
        payload.get("attempt_count"),
        default=0,
    )
    max_attempt_count = _normalize_positive_int(
        payload.get("max_attempt_count"),
        default=_DEFAULT_MAX_ATTEMPT_COUNT,
    )
    reentry_count = _normalize_non_negative_int(
        payload.get("reentry_count"),
        default=0,
    )
    max_reentry_count = _normalize_positive_int(
        payload.get("max_reentry_count"),
        default=_DEFAULT_MAX_REENTRY_COUNT,
    )
    same_failure_count = _normalize_non_negative_int(
        payload.get("same_failure_count"),
        default=0,
    )
    max_same_failure_count = _normalize_positive_int(
        payload.get("max_same_failure_count"),
        default=_DEFAULT_MAX_SAME_FAILURE_COUNT,
    )

    retry_exhausted = _normalize_bool(payload.get("retry_exhausted")) or (
        attempt_count >= max_attempt_count
    )
    reentry_exhausted = _normalize_bool(payload.get("reentry_exhausted")) or (
        reentry_count >= max_reentry_count
    )
    same_failure_exhausted = _normalize_bool(payload.get("same_failure_exhausted")) or (
        same_failure_count >= max_same_failure_count
    )

    retry_allowed = status == "retry_ready"
    reentry_allowed = status == "reentry_ready"

    same_lane_retry_allowed = decision == "same_lane_retry"
    repair_retry_allowed = decision == "repair_retry"
    recollect_required = decision == "recollect"
    replan_required = decision == "replan"
    manual_escalation_required = decision == "escalate_manual"
    terminal_stop_required = _normalize_bool(payload.get("terminal_stop_required")) or (
        decision == "stop_terminal"
    )

    no_progress_stop_required = _normalize_bool(payload.get("no_progress_stop_required"))
    if no_progress_stop_required:
        terminal_stop_required = True
    if terminal_stop_required:
        retry_allowed = False
        reentry_allowed = False

    if status == "not_applicable":
        retry_allowed = False
        reentry_allowed = False
        terminal_stop_required = False
        manual_escalation_required = False
        replan_required = False
        recollect_required = False
        same_lane_retry_allowed = False
        repair_retry_allowed = False

    if status == "exhausted" and not (retry_exhausted or reentry_exhausted or same_failure_exhausted):
        retry_exhausted = True

    return {
        "retry_reentry_loop_contract_present": bool(present),
        "retry_loop_status": status,
        "retry_loop_decision": decision,
        "retry_loop_validity": validity,
        "retry_loop_confidence": confidence,
        "loop_primary_reason": primary_reason,
        "attempt_count": attempt_count,
        "max_attempt_count": max_attempt_count,
        "reentry_count": reentry_count,
        "max_reentry_count": max_reentry_count,
        "same_failure_count": same_failure_count,
        "max_same_failure_count": max_same_failure_count,
        "retry_allowed": bool(retry_allowed),
        "reentry_allowed": bool(reentry_allowed),
        "retry_exhausted": bool(retry_exhausted),
        "reentry_exhausted": bool(reentry_exhausted),
        "same_failure_exhausted": bool(same_failure_exhausted),
        "terminal_stop_required": bool(terminal_stop_required),
        "manual_escalation_required": bool(manual_escalation_required),
        "replan_required": bool(replan_required),
        "recollect_required": bool(recollect_required),
        "same_lane_retry_allowed": bool(same_lane_retry_allowed),
        "repair_retry_allowed": bool(repair_retry_allowed),
        "no_progress_stop_required": bool(no_progress_stop_required),
    }

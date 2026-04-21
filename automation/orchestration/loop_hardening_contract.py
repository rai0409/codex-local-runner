from __future__ import annotations

from typing import Any
from typing import Mapping

LOOP_HARDENING_CONTRACT_SCHEMA_VERSION = "v1"

LOOP_HARDENING_STATUSES = {
    "stable",
    "watch",
    "freeze",
    "stop_required",
    "not_applicable",
    "insufficient_truth",
}

LOOP_HARDENING_DECISIONS = {
    "continue_bounded",
    "freeze_retry",
    "cool_down",
    "escalate_manual",
    "stop_terminal",
    "not_applicable",
}

LOOP_HARDENING_VALIDITIES = {
    "valid",
    "partial",
    "malformed",
    "insufficient_truth",
}

LOOP_HARDENING_CONFIDENCE_LEVELS = {
    "high",
    "medium",
    "low",
}

SAME_FAILURE_PERSISTENCE_STATUSES = {
    "none",
    "low",
    "moderate",
    "high",
    "exhausted",
    "unknown",
}

NO_PROGRESS_STATUSES = {
    "none",
    "suspected",
    "confirmed",
    "unknown",
}

OSCILLATION_STATUSES = {
    "none",
    "suspected",
    "confirmed",
    "unknown",
}

RETRY_FREEZE_STATUSES = {
    "not_required",
    "recommended",
    "required",
    "unknown",
}

LOOP_HARDENING_SOURCE_POSTURES = {
    "post_loop_hardening",
    "insufficient_truth",
    "not_applicable",
}

SAME_FAILURE_BUCKETS = {
    "objective_gap",
    "completion_gap",
    "approval_blocker",
    "reconcile_mismatch",
    "truth_missing",
    "verification_failure",
    "closure_unresolved",
    "execution_failure",
    "unknown",
}

LOOP_HARDENING_REASON_CODES = {
    "malformed_hardening_inputs",
    "insufficient_hardening_truth",
    "not_applicable_closed",
    "same_failure_exhausted",
    "no_progress_confirmed",
    "oscillation_confirmed",
    "retry_freeze_required",
    "same_failure_watch",
    "cool_down_required",
    "forced_manual_escalation_required",
    "continue_bounded",
    "unknown",
    "no_reason",
}

LOOP_HARDENING_REASON_ORDER = (
    "malformed_hardening_inputs",
    "insufficient_hardening_truth",
    "not_applicable_closed",
    "same_failure_exhausted",
    "no_progress_confirmed",
    "oscillation_confirmed",
    "retry_freeze_required",
    "same_failure_watch",
    "cool_down_required",
    "forced_manual_escalation_required",
    "continue_bounded",
    "unknown",
    "no_reason",
)

LOOP_HARDENING_RUN_STATE_SUMMARY_SAFE_FIELDS = (
    "loop_hardening_contract_present",
    "loop_hardening_status",
    "loop_hardening_decision",
    "loop_hardening_validity",
    "loop_hardening_confidence",
    "loop_hardening_primary_reason",
    "same_failure_signature",
    "same_failure_bucket",
    "same_failure_persistence",
    "no_progress_status",
    "oscillation_status",
    "retry_freeze_status",
    "same_failure_detected",
    "same_failure_stop_required",
    "no_progress_detected",
    "no_progress_stop_required",
    "oscillation_detected",
    "unstable_loop_detected",
    "retry_freeze_required",
    "cool_down_required",
    "forced_manual_escalation_required",
    "hardening_stop_required",
)

_DEFAULT_MAX_SAME_FAILURE_COUNT = 2

_ALLOWED_SUPPORTING_REFS = (
    "run_state.next_safe_action",
    "run_state.policy_primary_action",
    "run_state.policy_status",
    "completion_contract.completion_status",
    "completion_contract.completion_blocked_reason",
    "approval_transport.approval_status",
    "approval_transport.approval_blocked_reason",
    "reconcile_contract.reconcile_status",
    "reconcile_contract.reconcile_primary_mismatch",
    "retry_reentry_loop_contract.retry_loop_status",
    "retry_reentry_loop_contract.retry_loop_decision",
    "retry_reentry_loop_contract.attempt_count",
    "retry_reentry_loop_contract.reentry_count",
    "retry_reentry_loop_contract.same_failure_count",
    "retry_reentry_loop_contract.max_same_failure_count",
    "endgame_closure_contract.final_closure_class",
    "endgame_closure_contract.closure_resolution_status",
    "verification_closure_contract.verification_outcome",
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


def _normalize_non_negative_int(value: Any, *, default: int = 0) -> int:
    if isinstance(value, bool):
        return max(0, default)
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
    ordered: list[str] = []
    for value in values:
        text = _normalize_text(value, default="")
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


def _normalize_reason_codes(values: list[str]) -> list[str]:
    filtered = [value for value in _ordered_unique(values) if value in LOOP_HARDENING_REASON_CODES]
    ordered: list[str] = []
    for reason in LOOP_HARDENING_REASON_ORDER:
        if reason in filtered:
            ordered.append(reason)
    return ordered


def _build_supporting_refs(
    *,
    next_safe_hint: str,
    policy_primary_action: str,
    policy_status: str,
    completion_status: str,
    completion_blocked_reason: str,
    approval_status: str,
    approval_blocked_reason: str,
    reconcile_status: str,
    reconcile_primary_mismatch: str,
    retry_loop_status: str,
    retry_loop_decision: str,
    attempt_count: int,
    reentry_count: int,
    same_failure_count: int,
    max_same_failure_count: int,
    final_closure_class: str,
    closure_resolution_status: str,
    verification_outcome: str,
    execution_result_status: str,
    execution_result_outcome: str,
) -> list[str]:
    refs: list[str] = []
    if next_safe_hint:
        refs.append("run_state.next_safe_action")
    if policy_primary_action:
        refs.append("run_state.policy_primary_action")
    if policy_status:
        refs.append("run_state.policy_status")
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
    if retry_loop_status:
        refs.append("retry_reentry_loop_contract.retry_loop_status")
    if retry_loop_decision:
        refs.append("retry_reentry_loop_contract.retry_loop_decision")
    if attempt_count > 0:
        refs.append("retry_reentry_loop_contract.attempt_count")
    if reentry_count > 0:
        refs.append("retry_reentry_loop_contract.reentry_count")
    if same_failure_count > 0:
        refs.append("retry_reentry_loop_contract.same_failure_count")
    if max_same_failure_count > 0:
        refs.append("retry_reentry_loop_contract.max_same_failure_count")
    if final_closure_class:
        refs.append("endgame_closure_contract.final_closure_class")
    if closure_resolution_status:
        refs.append("endgame_closure_contract.closure_resolution_status")
    if verification_outcome:
        refs.append("verification_closure_contract.verification_outcome")
    if execution_result_status:
        refs.append("execution_result_contract.execution_result_status")
    if execution_result_outcome:
        refs.append("execution_result_contract.execution_result_outcome")

    ordered: list[str] = []
    for allowed in _ALLOWED_SUPPORTING_REFS:
        if allowed in refs and allowed not in ordered:
            ordered.append(allowed)
    return ordered


def _derive_same_failure_bucket(
    *,
    objective_status: str,
    completion_status: str,
    completion_blocked_reason: str,
    approval_status: str,
    approval_blocked_reason: str,
    reconcile_status: str,
    reconcile_primary_mismatch: str,
    verification_status: str,
    verification_outcome: str,
    closure_status: str,
    final_closure_class: str,
    execution_result_status: str,
    execution_result_outcome: str,
) -> str:
    if objective_status in {"incomplete", "underspecified"} or verification_outcome == "objective_gap":
        return "objective_gap"
    if (
        completion_status in {"not_done", "replan_before_closure"}
        or completion_blocked_reason
        or verification_outcome == "completion_gap"
    ):
        return "completion_gap"
    if approval_status in {"denied", "deferred", "missing"} or approval_blocked_reason:
        return "approval_blocker"
    if reconcile_status in {"inconsistent", "blocked", "partially_aligned"} or reconcile_primary_mismatch:
        return "reconcile_mismatch"
    if verification_outcome in {"external_truth_pending", "not_verifiable"}:
        return "truth_missing"
    if verification_status == "verified_failure":
        return "verification_failure"
    if closure_status in {"unknown", "not_closable", "closure_pending"} or final_closure_class == "closure_unresolved":
        return "closure_unresolved"
    if execution_result_status in {"failed", "partial", "blocked"} or execution_result_outcome in {
        "patch_failed",
        "tests_failed",
        "command_failed",
        "blocked",
    }:
        return "execution_failure"
    return "unknown"


def _derive_same_failure_signature(
    *,
    same_failure_bucket: str,
    verification_outcome: str,
    execution_result_outcome: str,
    closure_status: str,
    closure_decision: str,
) -> str:
    return (
        f"bucket={same_failure_bucket}"
        f"|verification={verification_outcome or 'unknown'}"
        f"|execution={execution_result_outcome or 'unknown'}"
        f"|closure={closure_status or 'unknown'}"
        f"|decision={closure_decision or 'unknown'}"
    )


def build_loop_hardening_contract_surface(
    *,
    run_id: str,
    completion_contract_payload: Mapping[str, Any] | None,
    approval_transport_payload: Mapping[str, Any] | None,
    reconcile_contract_payload: Mapping[str, Any] | None,
    execution_result_contract_payload: Mapping[str, Any] | None,
    verification_closure_contract_payload: Mapping[str, Any] | None,
    retry_reentry_loop_contract_payload: Mapping[str, Any] | None,
    endgame_closure_contract_payload: Mapping[str, Any] | None,
    run_state_payload: Mapping[str, Any] | None,
    artifact_presence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    completion = dict(completion_contract_payload or {})
    approval = dict(approval_transport_payload or {})
    reconcile = dict(reconcile_contract_payload or {})
    execution_result = dict(execution_result_contract_payload or {})
    verification = dict(verification_closure_contract_payload or {})
    retry_loop = dict(retry_reentry_loop_contract_payload or {})
    endgame = dict(endgame_closure_contract_payload or {})
    run_state = dict(run_state_payload or {})
    artifacts = dict(artifact_presence or {})

    objective_id = _normalize_text(
        completion.get("objective_id")
        or approval.get("objective_id")
        or reconcile.get("objective_id")
        or execution_result.get("objective_id")
        or verification.get("objective_id")
        or retry_loop.get("objective_id")
        or endgame.get("objective_id")
        or run_state.get("objective_id"),
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
    objective_status = _normalize_text(run_state.get("objective_contract_status"), default="")

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
    retry_loop_confidence = _normalize_text(
        retry_loop.get("retry_loop_confidence") or run_state.get("retry_loop_confidence"),
        default="",
    )
    retry_same_failure_exhausted = _normalize_bool(
        retry_loop.get("same_failure_exhausted")
        if "same_failure_exhausted" in retry_loop
        else run_state.get("same_failure_exhausted")
    )
    retry_no_progress_stop_required = _normalize_bool(
        retry_loop.get("no_progress_stop_required")
        if "no_progress_stop_required" in retry_loop
        else run_state.get("no_progress_stop_required")
    )
    retry_unstable_loop_suspected = _normalize_bool(
        retry_loop.get("unstable_loop_suspected")
        if "unstable_loop_suspected" in retry_loop
        else run_state.get("unstable_loop_suspected")
    )
    retry_manual_escalation_required = _normalize_bool(
        retry_loop.get("manual_escalation_required")
        if "manual_escalation_required" in retry_loop
        else run_state.get("manual_escalation_required")
    )

    endgame_status = _normalize_text(
        endgame.get("endgame_closure_status") or run_state.get("endgame_closure_status"),
        default="",
    )
    endgame_validity = _normalize_text(
        endgame.get("endgame_closure_validity") or run_state.get("endgame_closure_validity"),
        default="",
    )
    final_closure_class = _normalize_text(
        endgame.get("final_closure_class") or run_state.get("final_closure_class"),
        default="",
    )
    closure_resolution_status = _normalize_text(
        endgame.get("closure_resolution_status") or run_state.get("closure_resolution_status"),
        default="",
    )
    safely_closed = _normalize_bool(
        endgame.get("safely_closed") if "safely_closed" in endgame else run_state.get("safely_closed")
    )

    attempt_count = _normalize_non_negative_int(
        retry_loop.get("attempt_count")
        if "attempt_count" in retry_loop
        else run_state.get("attempt_count"),
        default=0,
    )
    reentry_count = _normalize_non_negative_int(
        retry_loop.get("reentry_count")
        if "reentry_count" in retry_loop
        else run_state.get("reentry_count"),
        default=0,
    )
    same_failure_count = _normalize_non_negative_int(
        retry_loop.get("same_failure_count")
        if "same_failure_count" in retry_loop
        else run_state.get("same_failure_count"),
        default=0,
    )
    max_same_failure_count = _normalize_positive_int(
        retry_loop.get("max_same_failure_count")
        if "max_same_failure_count" in retry_loop
        else run_state.get("max_same_failure_count"),
        default=_DEFAULT_MAX_SAME_FAILURE_COUNT,
    )

    prior_retry_class = _normalize_text(run_state.get("prior_retry_class"), default="")
    retry_class = _normalize_text(run_state.get("retry_class"), default="")
    if not retry_class and retry_loop_decision == "same_lane_retry":
        retry_class = "same_lane"
    if not retry_class and retry_loop_decision == "repair_retry":
        retry_class = "repair"

    malformed_inputs = bool(
        verification_validity == "malformed"
        or execution_result_validity == "malformed"
        or retry_loop_validity == "malformed"
        or endgame_validity == "malformed"
    )

    has_truth = any(
        (
            retry_loop_status,
            retry_loop_decision,
            final_closure_class,
            verification_status,
            verification_outcome,
            execution_result_status,
        )
    )
    insufficient_truth = bool(
        not has_truth
        or retry_loop_validity == "insufficient_truth"
        or endgame_validity == "insufficient_truth"
        or (
            not retry_loop_status
            and not final_closure_class
            and not verification_outcome
            and not execution_result_status
        )
    )

    same_failure_bucket = _derive_same_failure_bucket(
        objective_status=objective_status,
        completion_status=completion_status,
        completion_blocked_reason=completion_blocked_reason,
        approval_status=approval_status,
        approval_blocked_reason=approval_blocked_reason,
        reconcile_status=reconcile_status,
        reconcile_primary_mismatch=reconcile_primary_mismatch,
        verification_status=verification_status,
        verification_outcome=verification_outcome,
        closure_status=closure_status,
        final_closure_class=final_closure_class,
        execution_result_status=execution_result_status,
        execution_result_outcome=execution_result_outcome,
    )

    same_failure_signature = _derive_same_failure_signature(
        same_failure_bucket=same_failure_bucket,
        verification_outcome=verification_outcome,
        execution_result_outcome=execution_result_outcome,
        closure_status=closure_status,
        closure_decision=closure_decision,
    )

    same_failure_persistence = "none"
    if same_failure_count <= 0:
        same_failure_persistence = "none"
    elif same_failure_count >= max_same_failure_count:
        same_failure_persistence = "exhausted"
    elif same_failure_count >= max(1, max_same_failure_count - 1):
        same_failure_persistence = "high"
    elif same_failure_count >= 2:
        same_failure_persistence = "moderate"
    else:
        same_failure_persistence = "low"
    if insufficient_truth:
        same_failure_persistence = "unknown"

    same_failure_detected = same_failure_persistence in {"low", "moderate", "high", "exhausted"}
    same_failure_stop_required = same_failure_persistence == "exhausted" or retry_same_failure_exhausted

    no_progress_detected = bool(
        retry_no_progress_stop_required
        or (
            attempt_count >= 2
            and same_failure_count >= 2
            and verification_outcome in {"objective_gap", "completion_gap", "closure_followup", "unknown"}
        )
    )
    no_progress_status = (
        "confirmed"
        if (no_progress_detected and retry_no_progress_stop_required)
        else "suspected"
        if no_progress_detected
        else "none"
    )
    if insufficient_truth:
        no_progress_status = "unknown"

    oscillation_detected = bool(
        retry_unstable_loop_suspected
        or (
            attempt_count >= 2
            and prior_retry_class
            and retry_class
            and prior_retry_class != retry_class
        )
        or _normalize_bool(run_state.get("oscillation_detected"))
    )
    oscillation_status = (
        "confirmed"
        if (
            oscillation_detected
            and (
                _normalize_bool(run_state.get("oscillation_detected"))
                or (
                    attempt_count >= 2
                    and prior_retry_class
                    and retry_class
                    and prior_retry_class != retry_class
                )
            )
        )
        else "suspected"
        if oscillation_detected
        else "none"
    )
    if insufficient_truth:
        oscillation_status = "unknown"

    unstable_loop_detected = bool(
        no_progress_detected
        or oscillation_detected
        or retry_unstable_loop_suspected
    )
    if unstable_loop_detected and not (oscillation_detected or no_progress_detected):
        oscillation_detected = True
        if oscillation_status == "none":
            oscillation_status = "suspected"

    retry_freeze_required = bool(
        same_failure_stop_required
        or no_progress_status == "confirmed"
        or oscillation_status == "confirmed"
    )
    retry_freeze_status = (
        "required"
        if retry_freeze_required
        else "recommended"
        if oscillation_status == "suspected" or same_failure_persistence in {"moderate", "high"}
        else "not_required"
    )
    if insufficient_truth:
        retry_freeze_status = "unknown"

    cool_down_required = bool(
        oscillation_status in {"suspected", "confirmed"} and not same_failure_stop_required
    )
    forced_manual_escalation_required = bool(
        retry_manual_escalation_required
        or final_closure_class == "manual_closure_only"
        or retry_loop_decision == "escalate_manual"
    )

    hardening_stop_required = bool(
        same_failure_stop_required
        or no_progress_status == "confirmed"
        or (oscillation_status == "confirmed" and retry_freeze_required)
    )

    not_applicable_closed = bool(
        safely_closed
        or endgame_status == "safely_closed"
        or final_closure_class == "safely_closed"
        or retry_loop_status == "not_applicable"
    )

    lead_reason = "unknown"
    if malformed_inputs:
        lead_reason = "malformed_hardening_inputs"
    elif insufficient_truth:
        lead_reason = "insufficient_hardening_truth"
    elif not_applicable_closed:
        lead_reason = "not_applicable_closed"
    elif same_failure_stop_required:
        lead_reason = "same_failure_exhausted"
    elif no_progress_status == "confirmed":
        lead_reason = "no_progress_confirmed"
    elif oscillation_status == "confirmed":
        lead_reason = "oscillation_confirmed"
    elif retry_freeze_status == "required":
        lead_reason = "retry_freeze_required"
    elif same_failure_persistence in {"moderate", "high"}:
        lead_reason = "same_failure_watch"
    elif retry_loop_status in {"retry_ready", "reentry_ready", "watch", "stop_required"}:
        lead_reason = "continue_bounded"
    else:
        lead_reason = "unknown"

    loop_hardening_status = "watch"
    loop_hardening_decision = "continue_bounded"
    loop_hardening_validity = "partial"
    loop_hardening_confidence = "medium"

    if lead_reason == "malformed_hardening_inputs":
        loop_hardening_status = "insufficient_truth"
        loop_hardening_decision = "stop_terminal"
        loop_hardening_validity = "malformed"
        loop_hardening_confidence = "low"
        hardening_stop_required = True
    elif lead_reason == "insufficient_hardening_truth":
        loop_hardening_status = "insufficient_truth"
        loop_hardening_decision = "stop_terminal"
        loop_hardening_validity = "insufficient_truth"
        loop_hardening_confidence = "low"
        hardening_stop_required = True
    elif lead_reason == "not_applicable_closed":
        loop_hardening_status = "not_applicable"
        loop_hardening_decision = "not_applicable"
        loop_hardening_validity = "valid"
        loop_hardening_confidence = "high"
        hardening_stop_required = False
        retry_freeze_required = False
        cool_down_required = False
        forced_manual_escalation_required = False
        same_failure_stop_required = False
        no_progress_detected = False
        no_progress_status = "none"
        oscillation_detected = False
        oscillation_status = "none"
        unstable_loop_detected = False
        retry_freeze_status = "not_required"
        same_failure_detected = False
        same_failure_persistence = "none"
        same_failure_bucket = "unknown"
        same_failure_signature = _derive_same_failure_signature(
            same_failure_bucket="unknown",
            verification_outcome=verification_outcome,
            execution_result_outcome=execution_result_outcome,
            closure_status=closure_status,
            closure_decision=closure_decision,
        )
    elif lead_reason == "same_failure_exhausted":
        loop_hardening_status = "stop_required"
        loop_hardening_decision = "stop_terminal"
        loop_hardening_validity = "valid"
        loop_hardening_confidence = "medium"
        hardening_stop_required = True
        retry_freeze_required = True
        retry_freeze_status = "required"
        same_failure_detected = True
    elif lead_reason == "no_progress_confirmed":
        loop_hardening_status = "stop_required"
        loop_hardening_decision = "stop_terminal"
        loop_hardening_validity = "partial"
        loop_hardening_confidence = "low"
        hardening_stop_required = True
        retry_freeze_required = True
        retry_freeze_status = "required"
        no_progress_detected = True
        no_progress_status = "confirmed"
    elif lead_reason == "oscillation_confirmed":
        loop_hardening_status = "freeze"
        loop_hardening_decision = "cool_down"
        loop_hardening_validity = "partial"
        loop_hardening_confidence = "low"
        retry_freeze_required = True
        retry_freeze_status = "required"
        cool_down_required = True
        unstable_loop_detected = True
    elif lead_reason == "retry_freeze_required":
        loop_hardening_status = "freeze"
        loop_hardening_decision = "freeze_retry"
        loop_hardening_validity = "partial"
        loop_hardening_confidence = "medium"
        retry_freeze_required = True
        retry_freeze_status = "required"
    elif lead_reason == "same_failure_watch":
        loop_hardening_status = "watch"
        loop_hardening_decision = "continue_bounded"
        loop_hardening_validity = "partial"
        loop_hardening_confidence = "medium"
        if retry_freeze_status == "not_required":
            retry_freeze_status = "recommended"
    elif lead_reason == "continue_bounded":
        loop_hardening_status = "stable"
        loop_hardening_decision = "continue_bounded"
        loop_hardening_validity = "valid"
        loop_hardening_confidence = (
            "high"
            if retry_loop_confidence == "high" and retry_loop_status in {"retry_ready", "reentry_ready"}
            else "medium"
        )
        retry_freeze_required = False
        if retry_freeze_status == "unknown":
            retry_freeze_status = "not_required"
    else:
        loop_hardening_status = "watch"
        loop_hardening_decision = "continue_bounded"
        loop_hardening_validity = "partial"
        loop_hardening_confidence = "low"

    if forced_manual_escalation_required and loop_hardening_status != "not_applicable":
        loop_hardening_decision = "escalate_manual"
        hardening_stop_required = True

    if loop_hardening_status == "stable":
        hardening_stop_required = False
        retry_freeze_required = False
        retry_freeze_status = "not_required"
    if loop_hardening_status == "freeze":
        retry_freeze_required = True
    if loop_hardening_status == "stop_required":
        hardening_stop_required = True

    if loop_hardening_decision == "freeze_retry":
        retry_freeze_required = True
    if loop_hardening_decision == "cool_down":
        cool_down_required = True
    if loop_hardening_decision == "escalate_manual":
        forced_manual_escalation_required = True
    if loop_hardening_decision == "stop_terminal":
        hardening_stop_required = True

    if no_progress_stop_required := (no_progress_status == "confirmed"):
        no_progress_detected = True
        hardening_stop_required = True

    if same_failure_stop_required:
        same_failure_detected = True
        hardening_stop_required = True
        retry_freeze_required = True

    if unstable_loop_detected and not (oscillation_detected or no_progress_detected):
        oscillation_detected = True

    if loop_hardening_status == "not_applicable":
        loop_hardening_decision = "not_applicable"

    reason_candidates: list[str] = [lead_reason]
    if same_failure_stop_required:
        reason_candidates.append("same_failure_exhausted")
    if no_progress_status == "confirmed":
        reason_candidates.append("no_progress_confirmed")
    if oscillation_status == "confirmed":
        reason_candidates.append("oscillation_confirmed")
    if retry_freeze_required:
        reason_candidates.append("retry_freeze_required")
    if same_failure_persistence in {"moderate", "high"}:
        reason_candidates.append("same_failure_watch")
    if cool_down_required:
        reason_candidates.append("cool_down_required")
    if forced_manual_escalation_required:
        reason_candidates.append("forced_manual_escalation_required")
    if loop_hardening_decision == "continue_bounded":
        reason_candidates.append("continue_bounded")
    if loop_hardening_status == "not_applicable":
        reason_candidates.append("not_applicable_closed")

    reason_codes = _normalize_reason_codes(reason_candidates)
    if not reason_codes:
        reason_codes = ["no_reason"]
    loop_hardening_primary_reason = reason_codes[0]

    loop_hardening_source_posture = "post_loop_hardening"
    if loop_hardening_status == "insufficient_truth":
        loop_hardening_source_posture = "insufficient_truth"
    elif loop_hardening_status == "not_applicable":
        loop_hardening_source_posture = "not_applicable"

    next_safe_hint = _normalize_text(run_state.get("next_safe_action"), default="")
    policy_primary_action = _normalize_text(run_state.get("policy_primary_action"), default="")
    policy_status = _normalize_text(run_state.get("policy_status"), default="")

    payload: dict[str, Any] = {
        "schema_version": LOOP_HARDENING_CONTRACT_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "loop_hardening_status": _normalize_enum(
            loop_hardening_status,
            allowed=LOOP_HARDENING_STATUSES,
            default="insufficient_truth",
        ),
        "loop_hardening_decision": _normalize_enum(
            loop_hardening_decision,
            allowed=LOOP_HARDENING_DECISIONS,
            default="stop_terminal",
        ),
        "loop_hardening_validity": _normalize_enum(
            loop_hardening_validity,
            allowed=LOOP_HARDENING_VALIDITIES,
            default="insufficient_truth",
        ),
        "loop_hardening_confidence": _normalize_enum(
            loop_hardening_confidence,
            allowed=LOOP_HARDENING_CONFIDENCE_LEVELS,
            default="low",
        ),
        "same_failure_signature": same_failure_signature,
        "same_failure_bucket": _normalize_enum(
            same_failure_bucket,
            allowed=SAME_FAILURE_BUCKETS,
            default="unknown",
        ),
        "same_failure_persistence": _normalize_enum(
            same_failure_persistence,
            allowed=SAME_FAILURE_PERSISTENCE_STATUSES,
            default="unknown",
        ),
        "no_progress_status": _normalize_enum(
            no_progress_status,
            allowed=NO_PROGRESS_STATUSES,
            default="unknown",
        ),
        "oscillation_status": _normalize_enum(
            oscillation_status,
            allowed=OSCILLATION_STATUSES,
            default="unknown",
        ),
        "retry_freeze_status": _normalize_enum(
            retry_freeze_status,
            allowed=RETRY_FREEZE_STATUSES,
            default="unknown",
        ),
        "loop_hardening_primary_reason": loop_hardening_primary_reason,
        "loop_hardening_reason_codes": reason_codes,
        "same_failure_detected": bool(same_failure_detected),
        "same_failure_stop_required": bool(same_failure_stop_required),
        "no_progress_detected": bool(no_progress_detected),
        "no_progress_stop_required": bool(no_progress_stop_required),
        "oscillation_detected": bool(oscillation_detected),
        "unstable_loop_detected": bool(unstable_loop_detected),
        "retry_freeze_required": bool(retry_freeze_required),
        "cool_down_required": bool(cool_down_required),
        "forced_manual_escalation_required": bool(forced_manual_escalation_required),
        "hardening_stop_required": bool(hardening_stop_required),
        "loop_hardening_source_posture": _normalize_enum(
            loop_hardening_source_posture,
            allowed=LOOP_HARDENING_SOURCE_POSTURES,
            default="insufficient_truth",
        ),
        "retry_loop_status": retry_loop_status or "unknown",
        "retry_loop_decision": retry_loop_decision or "unknown",
        "attempt_count": attempt_count,
        "reentry_count": reentry_count,
        "same_failure_count": same_failure_count,
        "max_same_failure_count": max_same_failure_count,
        "final_closure_class": final_closure_class or "unknown",
        "closure_resolution_status": closure_resolution_status or "unknown",
        "verification_outcome": verification_outcome or "unknown",
        "execution_result_status": execution_result_status or "unknown",
        "execution_result_outcome": execution_result_outcome or "unknown",
        "supporting_compact_truth_refs": _build_supporting_refs(
            next_safe_hint=next_safe_hint,
            policy_primary_action=policy_primary_action,
            policy_status=policy_status,
            completion_status=completion_status,
            completion_blocked_reason=completion_blocked_reason,
            approval_status=approval_status,
            approval_blocked_reason=approval_blocked_reason,
            reconcile_status=reconcile_status,
            reconcile_primary_mismatch=reconcile_primary_mismatch,
            retry_loop_status=retry_loop_status,
            retry_loop_decision=retry_loop_decision,
            attempt_count=attempt_count,
            reentry_count=reentry_count,
            same_failure_count=same_failure_count,
            max_same_failure_count=max_same_failure_count,
            final_closure_class=final_closure_class,
            closure_resolution_status=closure_resolution_status,
            verification_outcome=verification_outcome,
            execution_result_status=execution_result_status,
            execution_result_outcome=execution_result_outcome,
        ),
    }

    if completion_blocked_reason:
        payload["completion_blocked_reason"] = completion_blocked_reason
    if approval_blocked_reason:
        payload["approval_blocked_reason"] = approval_blocked_reason
    if reconcile_primary_mismatch:
        payload["reconcile_primary_mismatch"] = reconcile_primary_mismatch
    if _normalize_text(verification.get("closure_followup_hint") or run_state.get("closure_followup_hint"), default=""):
        payload["closure_followup_hint"] = _normalize_text(
            verification.get("closure_followup_hint") or run_state.get("closure_followup_hint"),
            default="",
        )
    if _normalize_text(retry_loop.get("retry_hint") or run_state.get("retry_hint"), default=""):
        payload["retry_hint"] = _normalize_text(
            retry_loop.get("retry_hint") or run_state.get("retry_hint"),
            default="",
        )
    if _normalize_text(retry_loop.get("reentry_hint") or run_state.get("reentry_hint"), default=""):
        payload["reentry_hint"] = _normalize_text(
            retry_loop.get("reentry_hint") or run_state.get("reentry_hint"),
            default="",
        )
    if next_safe_hint:
        payload["next_safe_hint"] = next_safe_hint

    # Alias-aware non-duplication: avoid treating compact compatibility aliases as
    # independent evidence points by collapsing equivalent counters deterministically.
    if _normalize_non_negative_int(run_state.get("same_failure_count"), default=0) == _normalize_non_negative_int(
        run_state.get("same_failure_count_compat"), default=0
    ):
        payload["same_failure_count"] = _normalize_non_negative_int(
            payload.get("same_failure_count"),
            default=0,
        )

    # Final invariant repairs.
    payload["same_failure_detected"] = payload["same_failure_persistence"] != "none"
    if payload["same_failure_stop_required"]:
        payload["same_failure_detected"] = True
    if payload["no_progress_stop_required"]:
        payload["no_progress_detected"] = True
    payload["unstable_loop_detected"] = bool(payload["oscillation_detected"] or payload["no_progress_detected"])

    if payload["loop_hardening_status"] == "stable":
        payload["hardening_stop_required"] = False
        payload["retry_freeze_required"] = False
        payload["retry_freeze_status"] = "not_required"
    if payload["loop_hardening_status"] == "freeze":
        payload["retry_freeze_required"] = True
    if payload["loop_hardening_status"] == "stop_required":
        payload["hardening_stop_required"] = True

    if payload["loop_hardening_decision"] == "freeze_retry":
        payload["retry_freeze_required"] = True
    if payload["loop_hardening_decision"] == "cool_down":
        payload["cool_down_required"] = True
    if payload["loop_hardening_decision"] == "escalate_manual":
        payload["forced_manual_escalation_required"] = True
    if payload["loop_hardening_decision"] == "stop_terminal":
        payload["hardening_stop_required"] = True

    if payload["loop_hardening_status"] == "not_applicable":
        payload["loop_hardening_decision"] = "not_applicable"
        payload["same_failure_detected"] = False
        payload["same_failure_stop_required"] = False
        payload["no_progress_detected"] = False
        payload["no_progress_stop_required"] = False
        payload["oscillation_detected"] = False
        payload["unstable_loop_detected"] = False
        payload["retry_freeze_required"] = False
        payload["cool_down_required"] = False
        payload["forced_manual_escalation_required"] = False
        payload["hardening_stop_required"] = False

    payload["loop_hardening_status"] = _normalize_enum(
        payload.get("loop_hardening_status"),
        allowed=LOOP_HARDENING_STATUSES,
        default="insufficient_truth",
    )
    payload["loop_hardening_decision"] = _normalize_enum(
        payload.get("loop_hardening_decision"),
        allowed=LOOP_HARDENING_DECISIONS,
        default="stop_terminal",
    )
    payload["loop_hardening_validity"] = _normalize_enum(
        payload.get("loop_hardening_validity"),
        allowed=LOOP_HARDENING_VALIDITIES,
        default="insufficient_truth",
    )
    payload["loop_hardening_confidence"] = _normalize_enum(
        payload.get("loop_hardening_confidence"),
        allowed=LOOP_HARDENING_CONFIDENCE_LEVELS,
        default="low",
    )
    payload["same_failure_bucket"] = _normalize_enum(
        payload.get("same_failure_bucket"),
        allowed=SAME_FAILURE_BUCKETS,
        default="unknown",
    )
    payload["same_failure_persistence"] = _normalize_enum(
        payload.get("same_failure_persistence"),
        allowed=SAME_FAILURE_PERSISTENCE_STATUSES,
        default="unknown",
    )
    payload["no_progress_status"] = _normalize_enum(
        payload.get("no_progress_status"),
        allowed=NO_PROGRESS_STATUSES,
        default="unknown",
    )
    payload["oscillation_status"] = _normalize_enum(
        payload.get("oscillation_status"),
        allowed=OSCILLATION_STATUSES,
        default="unknown",
    )
    payload["retry_freeze_status"] = _normalize_enum(
        payload.get("retry_freeze_status"),
        allowed=RETRY_FREEZE_STATUSES,
        default="unknown",
    )
    payload["loop_hardening_source_posture"] = _normalize_enum(
        payload.get("loop_hardening_source_posture"),
        allowed=LOOP_HARDENING_SOURCE_POSTURES,
        default="insufficient_truth",
    )

    normalized_reason_codes = _normalize_reason_codes(
        _ordered_unique(
            [payload.get("loop_hardening_primary_reason", ""), *payload.get("loop_hardening_reason_codes", [])]
        )
    )
    if not normalized_reason_codes:
        normalized_reason_codes = ["no_reason"]
    payload["loop_hardening_reason_codes"] = normalized_reason_codes
    payload["loop_hardening_primary_reason"] = normalized_reason_codes[0]

    if not bool(artifacts.get("retry_reentry_loop_contract.json")) and payload[
        "loop_hardening_source_posture"
    ] == "post_loop_hardening":
        payload["loop_hardening_source_posture"] = "insufficient_truth"

    return payload


def build_loop_hardening_run_state_summary_surface(
    loop_hardening_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(loop_hardening_payload or {})

    status = _normalize_enum(
        payload.get("loop_hardening_status"),
        allowed=LOOP_HARDENING_STATUSES,
        default="insufficient_truth",
    )
    decision = _normalize_enum(
        payload.get("loop_hardening_decision"),
        allowed=LOOP_HARDENING_DECISIONS,
        default="stop_terminal",
    )
    validity = _normalize_enum(
        payload.get("loop_hardening_validity"),
        allowed=LOOP_HARDENING_VALIDITIES,
        default="insufficient_truth",
    )
    confidence = _normalize_enum(
        payload.get("loop_hardening_confidence"),
        allowed=LOOP_HARDENING_CONFIDENCE_LEVELS,
        default="low",
    )
    primary_reason = _normalize_text(payload.get("loop_hardening_primary_reason"), default="")
    if not primary_reason or primary_reason not in LOOP_HARDENING_REASON_CODES:
        primary_reason = (
            "not_applicable_closed"
            if status == "not_applicable"
            else "insufficient_hardening_truth"
            if status == "insufficient_truth"
            else "retry_freeze_required"
            if decision == "freeze_retry"
            else "cool_down_required"
            if decision == "cool_down"
            else "forced_manual_escalation_required"
            if decision == "escalate_manual"
            else "same_failure_exhausted"
            if decision == "stop_terminal"
            else "continue_bounded"
        )

    summary = {
        "loop_hardening_contract_present": bool(
            payload.get("loop_hardening_contract_present", False)
        )
        or bool(status),
        "loop_hardening_status": status,
        "loop_hardening_decision": decision,
        "loop_hardening_validity": validity,
        "loop_hardening_confidence": confidence,
        "loop_hardening_primary_reason": primary_reason,
        "same_failure_signature": _normalize_text(payload.get("same_failure_signature"), default=""),
        "same_failure_bucket": _normalize_enum(
            payload.get("same_failure_bucket"),
            allowed=SAME_FAILURE_BUCKETS,
            default="unknown",
        ),
        "same_failure_persistence": _normalize_enum(
            payload.get("same_failure_persistence"),
            allowed=SAME_FAILURE_PERSISTENCE_STATUSES,
            default="unknown",
        ),
        "no_progress_status": _normalize_enum(
            payload.get("no_progress_status"),
            allowed=NO_PROGRESS_STATUSES,
            default="unknown",
        ),
        "oscillation_status": _normalize_enum(
            payload.get("oscillation_status"),
            allowed=OSCILLATION_STATUSES,
            default="unknown",
        ),
        "retry_freeze_status": _normalize_enum(
            payload.get("retry_freeze_status"),
            allowed=RETRY_FREEZE_STATUSES,
            default="unknown",
        ),
        "same_failure_detected": _normalize_bool(payload.get("same_failure_detected")),
        "same_failure_stop_required": _normalize_bool(payload.get("same_failure_stop_required")),
        "no_progress_detected": _normalize_bool(payload.get("no_progress_detected")),
        "no_progress_stop_required": _normalize_bool(payload.get("no_progress_stop_required")),
        "oscillation_detected": _normalize_bool(payload.get("oscillation_detected")),
        "unstable_loop_detected": _normalize_bool(payload.get("unstable_loop_detected")),
        "retry_freeze_required": _normalize_bool(payload.get("retry_freeze_required")),
        "cool_down_required": _normalize_bool(payload.get("cool_down_required")),
        "forced_manual_escalation_required": _normalize_bool(
            payload.get("forced_manual_escalation_required")
        ),
        "hardening_stop_required": _normalize_bool(payload.get("hardening_stop_required")),
    }

    # Consistency constraints.
    if summary["loop_hardening_status"] == "stable":
        summary["hardening_stop_required"] = False
        summary["retry_freeze_required"] = False
        summary["retry_freeze_status"] = "not_required"
    if summary["loop_hardening_status"] == "freeze":
        summary["retry_freeze_required"] = True
    if summary["loop_hardening_status"] == "stop_required":
        summary["hardening_stop_required"] = True

    if summary["loop_hardening_decision"] == "freeze_retry":
        summary["retry_freeze_required"] = True
    if summary["loop_hardening_decision"] == "cool_down":
        summary["cool_down_required"] = True
    if summary["loop_hardening_decision"] == "escalate_manual":
        summary["forced_manual_escalation_required"] = True
    if summary["loop_hardening_decision"] == "stop_terminal":
        summary["hardening_stop_required"] = True
    if summary["loop_hardening_decision"] == "not_applicable":
        summary["loop_hardening_status"] = "not_applicable"

    summary["same_failure_detected"] = summary["same_failure_persistence"] != "none"
    if summary["same_failure_stop_required"]:
        summary["same_failure_detected"] = True
    if summary["no_progress_stop_required"]:
        summary["no_progress_detected"] = True
    summary["unstable_loop_detected"] = bool(
        summary["oscillation_detected"] or summary["no_progress_detected"]
    )

    if summary["loop_hardening_status"] == "not_applicable":
        summary["same_failure_detected"] = False
        summary["same_failure_stop_required"] = False
        summary["no_progress_detected"] = False
        summary["no_progress_stop_required"] = False
        summary["oscillation_detected"] = False
        summary["unstable_loop_detected"] = False
        summary["retry_freeze_required"] = False
        summary["cool_down_required"] = False
        summary["forced_manual_escalation_required"] = False
        summary["hardening_stop_required"] = False
        summary["retry_freeze_status"] = "not_required"
        summary["same_failure_persistence"] = "none"
        summary["same_failure_bucket"] = "unknown"

    return summary

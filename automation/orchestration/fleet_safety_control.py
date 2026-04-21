from __future__ import annotations

from typing import Any
from typing import Mapping

FLEET_SAFETY_CONTROL_SCHEMA_VERSION = "v1"

FLEET_SAFETY_STATUSES = {
    "allow",
    "hold",
    "freeze",
    "stop",
    "degraded",
    "insufficient_truth",
}

FLEET_SAFETY_VALIDITIES = {
    "valid",
    "partial",
    "malformed",
    "insufficient_truth",
}

FLEET_SAFETY_CONFIDENCE_LEVELS = {
    "high",
    "medium",
    "low",
}

FLEET_SAFETY_DECISIONS = {
    "proceed",
    "hold_for_review",
    "freeze_run",
    "stop_run",
    "escalate_manual",
    "unknown",
}

FLEET_RESTART_DECISIONS = {
    "restart_allowed",
    "restart_hold",
    "restart_blocked",
    "manual_only",
    "unknown",
}

FLEET_SAFETY_SCOPES = {
    "run_only",
    "lane_sensitive",
    "bucket_sensitive",
    "fleet_sensitive",
    "unknown",
}

FLEET_LANE_RISK_CLASSES = {
    "low",
    "medium",
    "high",
    "critical",
    "unknown",
}

FLEET_BUCKET_RISK_CLASSES = {
    "low",
    "medium",
    "high",
    "critical",
    "unknown",
}

FLEET_TERMINAL_RISK_CLASSES = {
    "non_terminal",
    "terminal_safe",
    "terminal_risky",
    "manual_only",
    "external_wait",
    "unknown",
}

FLEET_REPEAT_RISK_CLASSES = {
    "none",
    "repeat_detected",
    "repeat_high_risk",
    "repeat_blocked",
    "unknown",
}

FLEET_SAFETY_REASON_CODES = {
    "malformed_safety_inputs",
    "insufficient_safety_truth",
    "retention_reference_inconsistent",
    "manual_only_terminal_posture",
    "repeat_risk_blocked",
    "lane_mismatch_high_risk",
    "critical_failure_bucket",
    "terminal_non_success_risk",
    "hold_for_review_posture",
    "allow_safe_fallback",
    "unknown_posture",
    "alias_deduplicated",
    "restart_blocked",
    "restart_held",
    "restart_allowed",
    "no_reason",
}

FLEET_SAFETY_REASON_ORDER = (
    "malformed_safety_inputs",
    "insufficient_safety_truth",
    "retention_reference_inconsistent",
    "manual_only_terminal_posture",
    "repeat_risk_blocked",
    "lane_mismatch_high_risk",
    "critical_failure_bucket",
    "terminal_non_success_risk",
    "hold_for_review_posture",
    "allow_safe_fallback",
    "unknown_posture",
    "alias_deduplicated",
    "restart_blocked",
    "restart_held",
    "restart_allowed",
    "no_reason",
)

_ALLOWED_SUPPORTING_REFS = (
    "observability_rollup_contract.observability_status",
    "failure_bucketing_hardening_contract.primary_failure_bucket",
    "failure_bucketing_hardening_contract.bucket_severity",
    "failure_bucketing_hardening_contract.bucket_stability_class",
    "failure_bucketing_hardening_contract.bucket_terminality_class",
    "lane_stabilization_contract.lane_status",
    "lane_stabilization_contract.current_lane",
    "endgame_closure_contract.final_closure_class",
    "retry_reentry_loop_contract.retry_loop_status",
    "loop_hardening_contract.loop_hardening_status",
    "artifact_retention_contract.artifact_retention_status",
    "artifact_retention_contract.retention_reference_consistent",
)

FLEET_SAFETY_CONTROL_RUN_STATE_SUMMARY_SAFE_FIELDS = (
    "fleet_safety_control_present",
)

FLEET_SAFETY_CONTROL_SUMMARY_SAFE_FIELDS = (
    "fleet_safety_status",
    "fleet_safety_validity",
    "fleet_safety_confidence",
    "fleet_safety_decision",
    "fleet_restart_decision",
    "fleet_safety_scope",
    "fleet_safety_primary_reason",
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
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes"}:
            return True
        if lowered in {"0", "false", "no"}:
            return False
    return False


def _normalize_non_negative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return int(text)
    return 0


def _normalize_enum(value: Any, *, allowed: set[str], default: str) -> str:
    text = _normalize_text(value, default="")
    if text in allowed:
        return text
    return default


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = _normalize_text(value, default="")
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _normalize_reason_codes(values: list[str]) -> list[str]:
    normalized = [value for value in _ordered_unique(values) if value in FLEET_SAFETY_REASON_CODES]
    ordered: list[str] = []
    for code in FLEET_SAFETY_REASON_ORDER:
        if code in normalized:
            ordered.append(code)
    return ordered


def _normalize_supporting_refs(values: list[str]) -> list[str]:
    allowed = set(_ALLOWED_SUPPORTING_REFS)
    return [value for value in _ordered_unique(values) if value in allowed]


def _coerce_mapping(value: Any) -> tuple[dict[str, Any], bool]:
    if isinstance(value, Mapping):
        return dict(value), False
    return {}, value is not None


def _lane_risk_class(
    *,
    lane_status: str,
    current_lane: str,
    lane_execution_allowed: bool,
    lane_mismatch_detected: bool,
    lane_transition_blocked: bool,
) -> str:
    if lane_status == "lane_stop_required":
        return "critical"
    if lane_mismatch_detected or lane_status == "lane_mismatch":
        return "high"
    if lane_transition_blocked or lane_status == "lane_transition_blocked":
        return "high"
    if lane_status in {"insufficient_truth"}:
        return "unknown"
    if current_lane in {"bounded_github_update", "bounded_local_patch"} and not lane_execution_allowed:
        return "high"
    if lane_status in {"lane_transition_ready"}:
        return "medium"
    if current_lane in {
        "truth_gathering",
        "manual_review_preparation",
        "replan_preparation",
        "closure_followup",
    }:
        return "medium"
    if lane_status == "lane_valid" and lane_execution_allowed:
        return "low"
    return "unknown"


def _terminal_risk_class(final_closure_class: str) -> str:
    if final_closure_class == "safely_closed":
        return "terminal_safe"
    if final_closure_class == "manual_closure_only":
        return "manual_only"
    if final_closure_class == "external_truth_pending":
        return "external_wait"
    if final_closure_class in {"terminal_non_success", "closure_unresolved"}:
        return "terminal_risky"
    if final_closure_class in {"completed_but_not_closed", "rollback_complete_but_not_closed"}:
        return "non_terminal"
    if final_closure_class == "unknown":
        return "unknown"
    return "non_terminal"


def build_fleet_safety_control_contract_surface(
    *,
    run_id: str,
    objective_contract_payload: Mapping[str, Any] | None,
    observability_rollup_payload: Mapping[str, Any] | None,
    failure_bucketing_hardening_payload: Mapping[str, Any] | None,
    lane_stabilization_contract_payload: Mapping[str, Any] | None,
    loop_hardening_contract_payload: Mapping[str, Any] | None,
    endgame_closure_contract_payload: Mapping[str, Any] | None,
    retry_reentry_loop_contract_payload: Mapping[str, Any] | None,
    artifact_retention_contract_payload: Mapping[str, Any] | None,
    retention_manifest_payload: Mapping[str, Any] | None,
    run_state_payload: Mapping[str, Any] | None,
    contract_artifact_index_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    objective, objective_malformed = _coerce_mapping(objective_contract_payload)
    observability, observability_malformed = _coerce_mapping(observability_rollup_payload)
    hard_bucket, hard_bucket_malformed = _coerce_mapping(failure_bucketing_hardening_payload)
    lane, lane_malformed = _coerce_mapping(lane_stabilization_contract_payload)
    loop_hardening, loop_hardening_malformed = _coerce_mapping(loop_hardening_contract_payload)
    endgame, endgame_malformed = _coerce_mapping(endgame_closure_contract_payload)
    retry_loop, retry_loop_malformed = _coerce_mapping(retry_reentry_loop_contract_payload)
    retention, retention_malformed = _coerce_mapping(artifact_retention_contract_payload)
    retention_manifest, retention_manifest_malformed = _coerce_mapping(retention_manifest_payload)
    run_state, run_state_malformed = _coerce_mapping(run_state_payload)
    artifact_index, artifact_index_malformed = _coerce_mapping(contract_artifact_index_payload)

    malformed_inputs = any(
        (
            objective_malformed,
            observability_malformed,
            hard_bucket_malformed,
            lane_malformed,
            loop_hardening_malformed,
            endgame_malformed,
            retry_loop_malformed,
            retention_malformed,
            retention_manifest_malformed,
            run_state_malformed,
            artifact_index_malformed,
        )
    )

    objective_id = _normalize_text(
        objective.get("objective_id") or run_state.get("objective_id"),
        default="",
    )

    observability_status = _normalize_text(observability.get("observability_status"), default="")
    primary_failure_bucket = _normalize_text(hard_bucket.get("primary_failure_bucket"), default="")
    bucket_severity = _normalize_text(hard_bucket.get("bucket_severity"), default="unknown")
    bucket_stability_class = _normalize_text(hard_bucket.get("bucket_stability_class"), default="unknown")
    bucket_terminality_class = _normalize_text(
        hard_bucket.get("bucket_terminality_class"),
        default="unknown",
    )
    lane_status = _normalize_text(lane.get("lane_status"), default="")
    current_lane = _normalize_text(lane.get("current_lane"), default="")
    final_closure_class = _normalize_text(endgame.get("final_closure_class"), default="")
    retry_loop_status = _normalize_text(retry_loop.get("retry_loop_status"), default="")
    loop_hardening_status = _normalize_text(loop_hardening.get("loop_hardening_status"), default="")
    artifact_retention_status = _normalize_text(
        retention.get("artifact_retention_status"),
        default="",
    )
    retention_reference_consistent = _normalize_bool(
        retention.get("retention_reference_consistent")
    )

    manual_escalation_indicator = any(
        (
            _normalize_bool(observability.get("run_manual_escalated")),
            _normalize_bool(retry_loop.get("manual_escalation_required")),
            _normalize_bool(lane.get("lane_manual_review_required")),
            final_closure_class == "manual_closure_only",
            primary_failure_bucket == "manual_only",
        )
    )
    retry_exhausted_indicator = any(
        (
            _normalize_bool(retry_loop.get("retry_exhausted")),
            retry_loop_status == "exhausted",
            primary_failure_bucket == "retry_exhausted",
        )
    )
    same_failure_count = _normalize_non_negative_int(retry_loop.get("same_failure_count"))
    same_failure_indicator = any(
        (
            _normalize_bool(retry_loop.get("same_failure_exhausted")),
            _normalize_bool(loop_hardening.get("same_failure_detected")),
            same_failure_count > 0,
            primary_failure_bucket == "same_failure_exhausted",
        )
    )
    no_progress_indicator = any(
        (
            _normalize_bool(loop_hardening.get("no_progress_detected")),
            _normalize_bool(loop_hardening.get("no_progress_stop_required")),
            primary_failure_bucket == "no_progress",
        )
    )
    oscillation_indicator = any(
        (
            _normalize_bool(loop_hardening.get("oscillation_detected")),
            _normalize_text(loop_hardening.get("oscillation_status"), default="") == "confirmed",
            primary_failure_bucket == "oscillation",
        )
    )
    lane_mismatch_indicator = any(
        (
            _normalize_bool(lane.get("lane_mismatch_detected")),
            lane_status == "lane_mismatch",
            primary_failure_bucket == "lane_mismatch",
        )
    )
    artifact_integrity_indicator = any(
        (
            artifact_retention_status in {"partial", "degraded", "insufficient_truth"},
            not retention_reference_consistent,
            not _normalize_bool(retention.get("retention_manifest_compact")),
            _normalize_text(retention.get("artifact_retention_validity"), default="")
            in {"partial", "malformed", "insufficient_truth"},
        )
    )

    lane_execution_allowed = _normalize_bool(lane.get("lane_execution_allowed"))
    lane_transition_blocked = _normalize_bool(lane.get("lane_transition_blocked"))

    fleet_lane_risk_class = _normalize_enum(
        _lane_risk_class(
            lane_status=lane_status,
            current_lane=current_lane,
            lane_execution_allowed=lane_execution_allowed,
            lane_mismatch_detected=lane_mismatch_indicator,
            lane_transition_blocked=lane_transition_blocked,
        ),
        allowed=FLEET_LANE_RISK_CLASSES,
        default="unknown",
    )

    fleet_bucket_risk_class = _normalize_enum(
        bucket_severity,
        allowed=FLEET_BUCKET_RISK_CLASSES,
        default="unknown",
    )

    fleet_terminal_risk_class = _normalize_enum(
        _terminal_risk_class(final_closure_class),
        allowed=FLEET_TERMINAL_RISK_CLASSES,
        default="unknown",
    )

    same_failure_exhausted = any(
        (
            _normalize_bool(retry_loop.get("same_failure_exhausted")),
            _normalize_bool(loop_hardening.get("same_failure_stop_required")),
            primary_failure_bucket == "same_failure_exhausted",
        )
    )
    no_progress_stop_required = _normalize_bool(loop_hardening.get("no_progress_stop_required"))
    oscillation_confirmed = any(
        (
            _normalize_text(loop_hardening.get("oscillation_status"), default="") == "confirmed",
            oscillation_indicator and _normalize_bool(loop_hardening.get("unstable_loop_detected")),
        )
    )

    if same_failure_exhausted or no_progress_stop_required or oscillation_confirmed:
        fleet_repeat_risk_class = "repeat_blocked"
    elif same_failure_indicator and (same_failure_count >= 2 or no_progress_indicator or oscillation_indicator):
        fleet_repeat_risk_class = "repeat_high_risk"
    elif same_failure_indicator or retry_exhausted_indicator:
        fleet_repeat_risk_class = "repeat_detected"
    elif retry_loop_status or loop_hardening_status:
        fleet_repeat_risk_class = "none"
    else:
        fleet_repeat_risk_class = "unknown"

    insufficient_truth = any(
        (
            observability_status in {"", "insufficient_truth"},
            primary_failure_bucket in {"", "truth_missing"},
            artifact_retention_status in {"", "insufficient_truth"},
        )
    )

    retention_inconsistency_severe = any(
        (
            not retention_reference_consistent,
            _normalize_text(retention.get("artifact_retention_validity"), default="") == "malformed",
        )
    )

    manual_only_terminal = any(
        (
            final_closure_class == "manual_closure_only",
            primary_failure_bucket == "manual_only",
            manual_escalation_indicator and fleet_terminal_risk_class == "manual_only",
        )
    )

    repeat_blocked_high_risk = any(
        (
            fleet_repeat_risk_class == "repeat_blocked",
            no_progress_stop_required,
            oscillation_confirmed,
            same_failure_exhausted,
        )
    )

    lane_mismatch_high_risk = lane_mismatch_indicator and fleet_lane_risk_class in {
        "high",
        "critical",
    }

    critical_bucket = fleet_bucket_risk_class == "critical"

    terminal_non_success_risk = any(
        (
            fleet_terminal_risk_class == "terminal_risky",
            final_closure_class in {"terminal_non_success", "closure_unresolved"},
            bucket_terminality_class == "terminal"
            and primary_failure_bucket in {"terminal_non_success", "closure_unresolved"},
        )
    )

    hold_for_review = any(
        (
            _normalize_text(hard_bucket.get("bucket_stability_class"), default="") in {"ambiguous", "unknown"},
            lane_status in {"lane_transition_blocked", "insufficient_truth"},
            artifact_integrity_indicator and not retention_inconsistency_severe,
            observability_status in {"partial", "degraded"},
        )
    )

    lead_reason = "unknown_posture"
    status = "degraded"
    validity = "partial"
    confidence = "low"
    decision = "unknown"
    scope = "unknown"

    if malformed_inputs:
        lead_reason = "malformed_safety_inputs"
        status = "degraded"
        validity = "malformed"
        confidence = "low"
        decision = "hold_for_review"
        scope = "run_only"
    elif insufficient_truth:
        lead_reason = "insufficient_safety_truth"
        status = "insufficient_truth"
        validity = "insufficient_truth"
        confidence = "low"
        decision = "hold_for_review"
        scope = "run_only"
    elif retention_inconsistency_severe:
        lead_reason = "retention_reference_inconsistent"
        status = "degraded"
        validity = "partial"
        confidence = "low"
        decision = "freeze_run"
        scope = "fleet_sensitive"
    elif manual_only_terminal:
        lead_reason = "manual_only_terminal_posture"
        status = "stop"
        validity = "valid"
        confidence = "high"
        decision = "escalate_manual"
        scope = "fleet_sensitive"
    elif repeat_blocked_high_risk:
        lead_reason = "repeat_risk_blocked"
        status = "freeze"
        validity = "valid"
        confidence = "high"
        decision = "freeze_run"
        scope = "fleet_sensitive"
    elif lane_mismatch_high_risk:
        lead_reason = "lane_mismatch_high_risk"
        status = "freeze"
        validity = "valid"
        confidence = "medium"
        decision = "freeze_run"
        scope = "lane_sensitive"
    elif critical_bucket:
        lead_reason = "critical_failure_bucket"
        status = "freeze"
        validity = "valid"
        confidence = "medium"
        decision = "freeze_run"
        scope = "bucket_sensitive"
    elif terminal_non_success_risk:
        lead_reason = "terminal_non_success_risk"
        status = "stop"
        validity = "valid"
        confidence = "medium"
        decision = "stop_run"
        scope = "run_only"
    elif hold_for_review:
        lead_reason = "hold_for_review_posture"
        status = "hold"
        validity = "partial"
        confidence = "medium"
        decision = "hold_for_review"
        scope = "run_only"
    else:
        lead_reason = "allow_safe_fallback"
        status = "allow"
        validity = "valid"
        confidence = "high"
        decision = "proceed"
        scope = "run_only"

    if lead_reason == "unknown_posture":
        status = "degraded"
        validity = "partial"
        confidence = "low"
        decision = "unknown"
        scope = "unknown"

    fleet_run_allowed = status == "allow"
    fleet_run_hold_required = status in {"hold", "degraded", "insufficient_truth"}
    fleet_run_freeze_required = status == "freeze"
    fleet_run_stop_required = status == "stop"
    fleet_manual_review_required = manual_only_terminal or decision == "escalate_manual" or manual_escalation_indicator

    if fleet_run_allowed:
        fleet_restart_decision = "restart_allowed"
        fleet_restart_allowed = True
        fleet_restart_blocked = False
        fleet_restart_block_reason = ""
    elif fleet_manual_review_required and fleet_run_stop_required:
        fleet_restart_decision = "manual_only"
        fleet_restart_allowed = False
        fleet_restart_blocked = True
        fleet_restart_block_reason = "manual_review_required"
    elif fleet_run_freeze_required or fleet_run_stop_required:
        fleet_restart_decision = "restart_blocked"
        fleet_restart_allowed = False
        fleet_restart_blocked = True
        fleet_restart_block_reason = lead_reason
    elif fleet_run_hold_required:
        fleet_restart_decision = "restart_hold"
        fleet_restart_allowed = False
        fleet_restart_blocked = False
        fleet_restart_block_reason = "hold_for_review"
    else:
        fleet_restart_decision = "unknown"
        fleet_restart_allowed = False
        fleet_restart_blocked = True
        fleet_restart_block_reason = "cannot_determine"

    if decision == "proceed":
        fleet_run_hold_required = False
        fleet_run_freeze_required = False
        fleet_run_stop_required = False
    elif decision == "hold_for_review":
        fleet_run_allowed = False
        fleet_run_hold_required = True
    elif decision == "freeze_run":
        fleet_run_allowed = False
        fleet_run_freeze_required = True
    elif decision == "stop_run":
        fleet_run_allowed = False
        fleet_run_stop_required = True
    elif decision == "escalate_manual":
        fleet_run_allowed = False
        fleet_run_stop_required = True
        fleet_manual_review_required = True

    if fleet_run_freeze_required or fleet_run_stop_required:
        fleet_run_allowed = False
    if fleet_restart_allowed:
        fleet_restart_blocked = False
    if fleet_restart_blocked:
        fleet_restart_allowed = False

    fleet_safety_degraded = status in {"degraded", "insufficient_truth"} or confidence == "low"

    alias_deduplicated = any(
        (
            _normalize_bool(retention.get("retention_alias_deduplicated")),
            _normalize_bool(retention_manifest.get("alias_deduplicated")),
            _normalize_bool(hard_bucket.get("bucket_alias_deduplicated")),
        )
    )

    reason_codes = _normalize_reason_codes(
        [
            lead_reason,
            "alias_deduplicated" if alias_deduplicated else "",
            "restart_blocked" if fleet_restart_decision == "restart_blocked" else "",
            "restart_held" if fleet_restart_decision == "restart_hold" else "",
            "restart_allowed" if fleet_restart_decision == "restart_allowed" else "",
        ]
    )
    if not reason_codes:
        reason_codes = ["no_reason"]

    supporting_refs = _normalize_supporting_refs(
        [
            "observability_rollup_contract.observability_status" if observability_status else "",
            "failure_bucketing_hardening_contract.primary_failure_bucket"
            if primary_failure_bucket
            else "",
            "failure_bucketing_hardening_contract.bucket_severity" if bucket_severity else "",
            "failure_bucketing_hardening_contract.bucket_stability_class"
            if bucket_stability_class
            else "",
            "failure_bucketing_hardening_contract.bucket_terminality_class"
            if bucket_terminality_class
            else "",
            "lane_stabilization_contract.lane_status" if lane_status else "",
            "lane_stabilization_contract.current_lane" if current_lane else "",
            "endgame_closure_contract.final_closure_class" if final_closure_class else "",
            "retry_reentry_loop_contract.retry_loop_status" if retry_loop_status else "",
            "loop_hardening_contract.loop_hardening_status" if loop_hardening_status else "",
            "artifact_retention_contract.artifact_retention_status" if artifact_retention_status else "",
            "artifact_retention_contract.retention_reference_consistent"
            if "retention_reference_consistent" in retention
            else "",
        ]
    )

    return {
        "schema_version": FLEET_SAFETY_CONTROL_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "fleet_safety_status": _normalize_enum(
            status,
            allowed=FLEET_SAFETY_STATUSES,
            default="insufficient_truth",
        ),
        "fleet_safety_validity": _normalize_enum(
            validity,
            allowed=FLEET_SAFETY_VALIDITIES,
            default="insufficient_truth",
        ),
        "fleet_safety_confidence": _normalize_enum(
            confidence,
            allowed=FLEET_SAFETY_CONFIDENCE_LEVELS,
            default="low",
        ),
        "fleet_safety_decision": _normalize_enum(
            decision,
            allowed=FLEET_SAFETY_DECISIONS,
            default="unknown",
        ),
        "fleet_restart_decision": _normalize_enum(
            fleet_restart_decision,
            allowed=FLEET_RESTART_DECISIONS,
            default="unknown",
        ),
        "fleet_restart_block_reason": _normalize_text(
            fleet_restart_block_reason,
            default="",
        ),
        "fleet_safety_scope": _normalize_enum(
            scope,
            allowed=FLEET_SAFETY_SCOPES,
            default="unknown",
        ),
        "fleet_lane_risk_class": _normalize_enum(
            fleet_lane_risk_class,
            allowed=FLEET_LANE_RISK_CLASSES,
            default="unknown",
        ),
        "fleet_bucket_risk_class": _normalize_enum(
            fleet_bucket_risk_class,
            allowed=FLEET_BUCKET_RISK_CLASSES,
            default="unknown",
        ),
        "fleet_terminal_risk_class": _normalize_enum(
            fleet_terminal_risk_class,
            allowed=FLEET_TERMINAL_RISK_CLASSES,
            default="unknown",
        ),
        "fleet_repeat_risk_class": _normalize_enum(
            fleet_repeat_risk_class,
            allowed=FLEET_REPEAT_RISK_CLASSES,
            default="unknown",
        ),
        "fleet_manual_escalation_indicator": bool(manual_escalation_indicator),
        "fleet_retry_exhausted_indicator": bool(retry_exhausted_indicator),
        "fleet_same_failure_indicator": bool(same_failure_indicator),
        "fleet_no_progress_indicator": bool(no_progress_indicator),
        "fleet_oscillation_indicator": bool(oscillation_indicator),
        "fleet_lane_mismatch_indicator": bool(lane_mismatch_indicator),
        "fleet_artifact_integrity_indicator": bool(artifact_integrity_indicator),
        "fleet_run_allowed": bool(fleet_run_allowed),
        "fleet_run_hold_required": bool(fleet_run_hold_required),
        "fleet_run_freeze_required": bool(fleet_run_freeze_required),
        "fleet_run_stop_required": bool(fleet_run_stop_required),
        "fleet_manual_review_required": bool(fleet_manual_review_required),
        "fleet_restart_allowed": bool(fleet_restart_allowed),
        "fleet_restart_blocked": bool(fleet_restart_blocked),
        "fleet_safety_degraded": bool(fleet_safety_degraded),
        "fleet_safety_primary_reason": reason_codes[0],
        "fleet_safety_reason_codes": reason_codes,
        "fleet_observability_status": observability_status or "insufficient_truth",
        "fleet_primary_failure_bucket": primary_failure_bucket or "unknown",
        "bucket_severity": bucket_severity or "unknown",
        "bucket_stability_class": bucket_stability_class or "unknown",
        "bucket_terminality_class": bucket_terminality_class or "unknown",
        "lane_status": lane_status or "unknown",
        "current_lane": current_lane or "unknown",
        "final_closure_class": final_closure_class or "unknown",
        "retry_loop_status": retry_loop_status or "unknown",
        "loop_hardening_status": loop_hardening_status or "unknown",
        "artifact_retention_status": artifact_retention_status or "insufficient_truth",
        "retention_reference_consistent": bool(retention_reference_consistent),
        "supporting_compact_truth_refs": supporting_refs,
        "completion_blocked_reason": _normalize_text(
            run_state.get("completion_blocked_reason"),
            default="",
        ),
        "approval_blocked_reason": _normalize_text(
            run_state.get("approval_blocked_reason"),
            default="",
        ),
        "reconcile_primary_mismatch": _normalize_text(
            run_state.get("reconcile_primary_mismatch"),
            default="",
        ),
        "retry_hint": _normalize_text(run_state.get("retry_hint"), default=""),
        "reentry_hint": _normalize_text(run_state.get("reentry_hint"), default=""),
        "closure_followup_hint": _normalize_text(
            run_state.get("closure_followup_hint"),
            default="",
        ),
        "next_safe_hint": _normalize_text(run_state.get("next_safe_action"), default=""),
    }


def build_fleet_safety_control_run_state_summary_surface(
    fleet_safety_control_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(fleet_safety_control_payload or {})
    return {
        "fleet_safety_control_present": bool(
            _normalize_text(payload.get("fleet_safety_status"), default="")
        )
        or _normalize_bool(payload.get("fleet_safety_control_present"))
    }


def build_fleet_safety_control_summary_surface(
    fleet_safety_control_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(fleet_safety_control_payload or {})
    return {
        "fleet_safety_status": _normalize_enum(
            payload.get("fleet_safety_status"),
            allowed=FLEET_SAFETY_STATUSES,
            default="insufficient_truth",
        ),
        "fleet_safety_validity": _normalize_enum(
            payload.get("fleet_safety_validity"),
            allowed=FLEET_SAFETY_VALIDITIES,
            default="insufficient_truth",
        ),
        "fleet_safety_confidence": _normalize_enum(
            payload.get("fleet_safety_confidence"),
            allowed=FLEET_SAFETY_CONFIDENCE_LEVELS,
            default="low",
        ),
        "fleet_safety_decision": _normalize_enum(
            payload.get("fleet_safety_decision"),
            allowed=FLEET_SAFETY_DECISIONS,
            default="unknown",
        ),
        "fleet_restart_decision": _normalize_enum(
            payload.get("fleet_restart_decision"),
            allowed=FLEET_RESTART_DECISIONS,
            default="unknown",
        ),
        "fleet_safety_scope": _normalize_enum(
            payload.get("fleet_safety_scope"),
            allowed=FLEET_SAFETY_SCOPES,
            default="unknown",
        ),
        "fleet_safety_primary_reason": _normalize_text(
            payload.get("fleet_safety_primary_reason"),
            default="no_reason",
        )
        if _normalize_text(payload.get("fleet_safety_primary_reason"), default="")
        in FLEET_SAFETY_REASON_CODES
        else "no_reason",
    }

from __future__ import annotations

from typing import Any
from typing import Mapping


FAILURE_BUCKETING_HARDENING_SCHEMA_VERSION = "v1"

FAILURE_BUCKETING_STATUSES = {
    "classified",
    "partial",
    "degraded",
    "insufficient_truth",
}

FAILURE_BUCKETING_VALIDITIES = {
    "valid",
    "partial",
    "malformed",
    "insufficient_truth",
}

FAILURE_BUCKETING_CONFIDENCE_LEVELS = {
    "high",
    "medium",
    "low",
}

HARDENED_FAILURE_BUCKET_VOCABULARY = {
    "truth_missing",
    "truth_conflict",
    "authorization_denied",
    "bridge_blocked",
    "execution_failure",
    "execution_partial",
    "verification_failure",
    "objective_gap",
    "completion_gap",
    "approval_blocker",
    "reconcile_mismatch",
    "retry_exhausted",
    "same_failure_exhausted",
    "no_progress",
    "oscillation",
    "lane_mismatch",
    "manual_only",
    "external_truth_pending",
    "closure_unresolved",
    "terminal_non_success",
    "unknown",
}

BUCKET_FAMILIES = {
    "truth",
    "authorization",
    "execution",
    "verification",
    "completion",
    "governance",
    "retry_loop",
    "hardening",
    "lane",
    "closure",
    "manual",
    "external_wait",
    "unknown",
}

BUCKET_SEVERITIES = {
    "low",
    "medium",
    "high",
    "critical",
    "unknown",
}

BUCKET_STABILITY_CLASSES = {
    "stable",
    "likely_stable",
    "ambiguous",
    "unstable",
    "unknown",
}

BUCKET_TERMINALITY_CLASSES = {
    "terminal",
    "non_terminal",
    "external_wait",
    "manual_only",
    "unknown",
}

FAILURE_BUCKETING_REASON_CODES = {
    "malformed_hardening_inputs",
    "insufficient_hardening_truth",
    "primary_truth_missing",
    "primary_truth_conflict",
    "primary_authorization_denied",
    "primary_bridge_blocked",
    "primary_lane_mismatch",
    "primary_execution_failure",
    "primary_execution_partial",
    "primary_verification_failure",
    "primary_objective_gap",
    "primary_completion_gap",
    "primary_approval_blocker",
    "primary_reconcile_mismatch",
    "primary_retry_exhausted",
    "primary_same_failure_exhausted",
    "primary_no_progress",
    "primary_oscillation",
    "primary_manual_only",
    "primary_external_truth_pending",
    "primary_closure_unresolved",
    "primary_terminal_non_success",
    "primary_unknown",
    "alias_deduplicated",
    "ambiguous_bucket",
}

FAILURE_BUCKETING_REASON_ORDER = (
    "malformed_hardening_inputs",
    "insufficient_hardening_truth",
    "primary_truth_missing",
    "primary_truth_conflict",
    "primary_authorization_denied",
    "primary_bridge_blocked",
    "primary_lane_mismatch",
    "primary_execution_failure",
    "primary_execution_partial",
    "primary_verification_failure",
    "primary_objective_gap",
    "primary_completion_gap",
    "primary_approval_blocker",
    "primary_reconcile_mismatch",
    "primary_retry_exhausted",
    "primary_same_failure_exhausted",
    "primary_no_progress",
    "primary_oscillation",
    "primary_manual_only",
    "primary_external_truth_pending",
    "primary_closure_unresolved",
    "primary_terminal_non_success",
    "primary_unknown",
    "alias_deduplicated",
    "ambiguous_bucket",
)

_PRIMARY_PRECEDENCE = (
    "truth_missing",
    "truth_conflict",
    "authorization_denied",
    "bridge_blocked",
    "lane_mismatch",
    "execution_failure",
    "execution_partial",
    "verification_failure",
    "objective_gap",
    "completion_gap",
    "approval_blocker",
    "reconcile_mismatch",
    "retry_exhausted",
    "same_failure_exhausted",
    "no_progress",
    "oscillation",
    "manual_only",
    "external_truth_pending",
    "closure_unresolved",
    "terminal_non_success",
    "unknown",
)

_PRIMARY_TO_REASON = {
    "truth_missing": "primary_truth_missing",
    "truth_conflict": "primary_truth_conflict",
    "authorization_denied": "primary_authorization_denied",
    "bridge_blocked": "primary_bridge_blocked",
    "lane_mismatch": "primary_lane_mismatch",
    "execution_failure": "primary_execution_failure",
    "execution_partial": "primary_execution_partial",
    "verification_failure": "primary_verification_failure",
    "objective_gap": "primary_objective_gap",
    "completion_gap": "primary_completion_gap",
    "approval_blocker": "primary_approval_blocker",
    "reconcile_mismatch": "primary_reconcile_mismatch",
    "retry_exhausted": "primary_retry_exhausted",
    "same_failure_exhausted": "primary_same_failure_exhausted",
    "no_progress": "primary_no_progress",
    "oscillation": "primary_oscillation",
    "manual_only": "primary_manual_only",
    "external_truth_pending": "primary_external_truth_pending",
    "closure_unresolved": "primary_closure_unresolved",
    "terminal_non_success": "primary_terminal_non_success",
    "unknown": "primary_unknown",
}

_PRIMARY_TO_FAMILY = {
    "truth_missing": "truth",
    "truth_conflict": "truth",
    "authorization_denied": "authorization",
    "bridge_blocked": "authorization",
    "execution_failure": "execution",
    "execution_partial": "execution",
    "verification_failure": "verification",
    "objective_gap": "completion",
    "completion_gap": "completion",
    "approval_blocker": "governance",
    "reconcile_mismatch": "governance",
    "retry_exhausted": "retry_loop",
    "same_failure_exhausted": "retry_loop",
    "no_progress": "hardening",
    "oscillation": "hardening",
    "lane_mismatch": "lane",
    "manual_only": "manual",
    "external_truth_pending": "external_wait",
    "closure_unresolved": "closure",
    "terminal_non_success": "closure",
    "unknown": "unknown",
}

_PRIMARY_TO_SEVERITY = {
    "truth_missing": "medium",
    "truth_conflict": "critical",
    "authorization_denied": "critical",
    "bridge_blocked": "high",
    "execution_failure": "high",
    "execution_partial": "medium",
    "verification_failure": "high",
    "objective_gap": "high",
    "completion_gap": "high",
    "approval_blocker": "high",
    "reconcile_mismatch": "high",
    "retry_exhausted": "critical",
    "same_failure_exhausted": "critical",
    "no_progress": "critical",
    "oscillation": "critical",
    "lane_mismatch": "high",
    "manual_only": "high",
    "external_truth_pending": "medium",
    "closure_unresolved": "critical",
    "terminal_non_success": "critical",
    "unknown": "unknown",
}

_SUPPORTING_REFS_ALLOWED = (
    "failure_bucket_rollup.primary_failure_bucket",
    "loop_hardening_contract.same_failure_bucket",
    "loop_hardening_contract.same_failure_signature",
    "observability_rollup_contract.observability_status",
    "endgame_closure_contract.final_closure_class",
    "endgame_closure_contract.terminal_stop_class",
    "retry_reentry_loop_contract.retry_loop_status",
    "loop_hardening_contract.loop_hardening_status",
    "lane_stabilization_contract.lane_status",
    "verification_closure_contract.verification_outcome",
    "execution_result_contract.execution_result_status",
    "bounded_execution_bridge.bounded_execution_status",
    "execution_authorization_gate.execution_authorization_status",
)

FAILURE_BUCKETING_HARDENING_RUN_STATE_SUMMARY_SAFE_FIELDS = (
    "failure_bucketing_hardening_present",
)

FAILURE_BUCKETING_HARDENING_SUMMARY_SAFE_FIELDS = (
    "failure_bucketing_status",
    "failure_bucketing_validity",
    "failure_bucketing_confidence",
    "primary_failure_bucket",
    "bucket_family",
    "bucket_severity",
    "bucket_stability_class",
    "bucket_terminality_class",
    "failure_bucketing_primary_reason",
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
    filtered = [value for value in _ordered_unique(values) if value in FAILURE_BUCKETING_REASON_CODES]
    ordered: list[str] = []
    for code in FAILURE_BUCKETING_REASON_ORDER:
        if code in filtered:
            ordered.append(code)
    return ordered


def _supporting_refs(values: list[str]) -> list[str]:
    allowed = set(_SUPPORTING_REFS_ALLOWED)
    refs = [value for value in _ordered_unique(values) if value in allowed]
    return refs


def _coerce_mapping(value: Any) -> tuple[dict[str, Any], bool]:
    if isinstance(value, Mapping):
        return dict(value), False
    return {}, value is not None


def _bucket_terminality_class(
    *,
    primary_failure_bucket: str,
    final_closure_class: str,
    terminal_stop_class: str,
    retry_loop_status: str,
    lane_status: str,
) -> str:
    if primary_failure_bucket == "external_truth_pending":
        return "external_wait"
    if primary_failure_bucket == "manual_only":
        return "manual_only"
    if final_closure_class in {
        "terminal_non_success",
        "closure_unresolved",
        "safely_closed",
        "completed_but_not_closed",
        "rollback_complete_but_not_closed",
    }:
        return "terminal"
    if terminal_stop_class in {
        "terminal_success",
        "terminal_non_success",
        "manual_terminal",
        "external_wait_terminal",
        "closure_unresolved_terminal",
    }:
        return "terminal"
    if retry_loop_status in {"retry_ready", "reentry_ready"} or lane_status in {
        "lane_valid",
        "lane_transition_ready",
    }:
        return "non_terminal"
    return "unknown"


def build_failure_bucketing_hardening_contract_surface(
    *,
    run_id: str,
    objective_contract_payload: Mapping[str, Any] | None,
    execution_result_contract_payload: Mapping[str, Any] | None,
    verification_closure_contract_payload: Mapping[str, Any] | None,
    retry_reentry_loop_contract_payload: Mapping[str, Any] | None,
    endgame_closure_contract_payload: Mapping[str, Any] | None,
    loop_hardening_contract_payload: Mapping[str, Any] | None,
    lane_stabilization_contract_payload: Mapping[str, Any] | None,
    observability_rollup_payload: Mapping[str, Any] | None,
    failure_bucket_rollup_payload: Mapping[str, Any] | None,
    bounded_execution_bridge_payload: Mapping[str, Any] | None,
    execution_authorization_gate_payload: Mapping[str, Any] | None,
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    objective, objective_malformed = _coerce_mapping(objective_contract_payload)
    execution_result, execution_result_malformed = _coerce_mapping(
        execution_result_contract_payload
    )
    verification, verification_malformed = _coerce_mapping(
        verification_closure_contract_payload
    )
    retry_loop, retry_loop_malformed = _coerce_mapping(retry_reentry_loop_contract_payload)
    endgame, endgame_malformed = _coerce_mapping(endgame_closure_contract_payload)
    loop_hardening, loop_hardening_malformed = _coerce_mapping(loop_hardening_contract_payload)
    lane, lane_malformed = _coerce_mapping(lane_stabilization_contract_payload)
    observability, observability_malformed = _coerce_mapping(observability_rollup_payload)
    failure_bucket, failure_bucket_malformed = _coerce_mapping(failure_bucket_rollup_payload)
    bounded_execution, bounded_execution_malformed = _coerce_mapping(
        bounded_execution_bridge_payload
    )
    execution_authorization, execution_authorization_malformed = _coerce_mapping(
        execution_authorization_gate_payload
    )
    run_state, run_state_malformed = _coerce_mapping(run_state_payload)

    malformed_inputs = any(
        (
            objective_malformed,
            execution_result_malformed,
            verification_malformed,
            retry_loop_malformed,
            endgame_malformed,
            loop_hardening_malformed,
            lane_malformed,
            observability_malformed,
            failure_bucket_malformed,
            bounded_execution_malformed,
            execution_authorization_malformed,
            run_state_malformed,
        )
    )

    objective_id = _normalize_text(
        objective.get("objective_id") or run_state.get("objective_id"),
        default="",
    )
    narrow_primary_failure_bucket = _normalize_text(
        failure_bucket.get("primary_failure_bucket"),
        default="",
    )
    same_failure_bucket = _normalize_text(
        loop_hardening.get("same_failure_bucket")
        or failure_bucket.get("same_failure_bucket"),
        default="",
    )
    same_failure_signature = _normalize_text(
        loop_hardening.get("same_failure_signature")
        or failure_bucket.get("same_failure_signature"),
        default="",
    )
    observability_status = _normalize_text(observability.get("observability_status"), default="")
    failure_bucket_status = _normalize_text(failure_bucket.get("failure_bucket_status"), default="")
    final_closure_class = _normalize_text(endgame.get("final_closure_class"), default="")
    terminal_stop_class = _normalize_text(endgame.get("terminal_stop_class"), default="")
    retry_loop_status = _normalize_text(retry_loop.get("retry_loop_status"), default="")
    loop_hardening_status = _normalize_text(loop_hardening.get("loop_hardening_status"), default="")
    lane_status = _normalize_text(lane.get("lane_status"), default="")
    verification_status = _normalize_text(verification.get("verification_status"), default="")
    verification_outcome = _normalize_text(verification.get("verification_outcome"), default="")
    execution_result_status = _normalize_text(
        execution_result.get("execution_result_status"),
        default="",
    )
    bounded_execution_bridge_status = _normalize_text(
        bounded_execution.get("bounded_execution_status"),
        default="",
    )
    execution_authorization_status = _normalize_text(
        execution_authorization.get("execution_authorization_status"),
        default="",
    )

    truth_missing = any(
        (
            observability_status == "insufficient_truth",
            failure_bucket_status == "insufficient_truth",
            narrow_primary_failure_bucket == "truth_missing",
            verification_status == "not_verifiable",
            _normalize_text(verification.get("verification_validity")) == "insufficient_truth",
        )
    )
    truth_conflict = any(
        (
            final_closure_class == "safely_closed"
            and narrow_primary_failure_bucket
            in {
                "execution_failure",
                "verification_failure",
                "closure_unresolved",
                "terminal_non_success",
            },
            execution_authorization_status == "denied"
            and bounded_execution_bridge_status == "ready",
            _normalize_bool(lane.get("lane_execution_allowed"))
            and loop_hardening_status in {"freeze", "stop_required"},
        )
    )
    authorization_denied = any(
        (
            execution_authorization_status == "denied",
            _normalize_text(run_state.get("approval_status")) == "denied",
        )
    )
    bridge_blocked = any(
        (
            bounded_execution_bridge_status == "blocked",
            bounded_execution_bridge_status == "insufficient_truth",
            narrow_primary_failure_bucket == "bridge_blocked",
        )
    )
    lane_mismatch = any(
        (
            lane_status == "lane_mismatch",
            narrow_primary_failure_bucket == "lane_mismatch",
            _normalize_bool(lane.get("lane_mismatch_detected")),
        )
    )
    execution_failure = any(
        (
            execution_result_status == "failed",
            narrow_primary_failure_bucket == "execution_failure",
        )
    )
    execution_partial = any(
        (
            execution_result_status == "partial",
            narrow_primary_failure_bucket == "execution_partial",
        )
    )
    verification_failure = any(
        (
            verification_status == "verified_failure"
            and verification_outcome not in {"objective_gap", "completion_gap"},
            narrow_primary_failure_bucket == "verification_failure",
        )
    )
    objective_gap = any(
        (
            verification_outcome == "objective_gap",
            _normalize_text(verification.get("objective_satisfaction_status"))
            == "not_satisfied",
            narrow_primary_failure_bucket == "objective_gap",
        )
    )
    completion_gap = any(
        (
            verification_outcome == "completion_gap",
            _normalize_text(verification.get("completion_satisfaction_status"))
            == "not_satisfied",
            narrow_primary_failure_bucket == "completion_gap",
        )
    )
    approval_blocker = any(
        (
            narrow_primary_failure_bucket == "approval_blocker",
            _normalize_text(run_state.get("approval_status")) in {"deferred", "absent"},
        )
    )
    reconcile_mismatch = any(
        (
            narrow_primary_failure_bucket == "reconcile_mismatch",
            _normalize_text(run_state.get("reconcile_status")) == "inconsistent",
            bool(_normalize_text(run_state.get("reconcile_primary_mismatch"), default="")),
        )
    )
    retry_exhausted = any(
        (
            retry_loop_status == "exhausted",
            _normalize_bool(retry_loop.get("retry_exhausted")),
            narrow_primary_failure_bucket == "retry_exhausted",
        )
    )
    same_failure_exhausted = any(
        (
            _normalize_bool(retry_loop.get("same_failure_exhausted")),
            _normalize_bool(loop_hardening.get("same_failure_stop_required"))
            and _normalize_text(loop_hardening.get("same_failure_persistence"))
            in {"high", "exhausted"},
            narrow_primary_failure_bucket == "same_failure_exhausted",
        )
    )
    no_progress = any(
        (
            _normalize_bool(loop_hardening.get("no_progress_stop_required")),
            _normalize_text(loop_hardening.get("no_progress_status")) == "confirmed",
            narrow_primary_failure_bucket == "no_progress",
        )
    )
    oscillation = any(
        (
            _normalize_text(loop_hardening.get("oscillation_status")) == "confirmed",
            _normalize_bool(loop_hardening.get("oscillation_detected"))
            and _normalize_bool(loop_hardening.get("unstable_loop_detected")),
            narrow_primary_failure_bucket == "oscillation",
        )
    )
    manual_only = any(
        (
            final_closure_class == "manual_closure_only",
            _normalize_bool(retry_loop.get("manual_escalation_required")),
            _normalize_bool(lane.get("lane_manual_review_required")),
            narrow_primary_failure_bucket == "manual_only",
        )
    )
    external_truth_pending = any(
        (
            final_closure_class == "external_truth_pending",
            verification_outcome == "external_truth_pending",
            narrow_primary_failure_bucket == "external_truth_pending",
        )
    )
    closure_unresolved = any(
        (
            final_closure_class == "closure_unresolved",
            narrow_primary_failure_bucket == "closure_unresolved",
        )
    )
    terminal_non_success = any(
        (
            final_closure_class == "terminal_non_success",
            terminal_stop_class == "terminal_non_success",
            narrow_primary_failure_bucket == "terminal_non_success",
        )
    )

    candidates = {
        "truth_missing": truth_missing,
        "truth_conflict": truth_conflict,
        "authorization_denied": authorization_denied,
        "bridge_blocked": bridge_blocked,
        "lane_mismatch": lane_mismatch,
        "execution_failure": execution_failure,
        "execution_partial": execution_partial,
        "verification_failure": verification_failure,
        "objective_gap": objective_gap,
        "completion_gap": completion_gap,
        "approval_blocker": approval_blocker,
        "reconcile_mismatch": reconcile_mismatch,
        "retry_exhausted": retry_exhausted,
        "same_failure_exhausted": same_failure_exhausted,
        "no_progress": no_progress,
        "oscillation": oscillation,
        "manual_only": manual_only,
        "external_truth_pending": external_truth_pending,
        "closure_unresolved": closure_unresolved,
        "terminal_non_success": terminal_non_success,
        "unknown": True,
    }
    true_candidates = [bucket for bucket in _PRIMARY_PRECEDENCE if candidates.get(bucket)]

    primary_failure_bucket = "unknown"
    for bucket in _PRIMARY_PRECEDENCE:
        if candidates.get(bucket):
            primary_failure_bucket = bucket
            break

    secondary_failure_buckets = [
        bucket
        for bucket in true_candidates
        if bucket != primary_failure_bucket and bucket != "unknown"
    ][:2]

    source_bucket_values = [
        narrow_primary_failure_bucket if narrow_primary_failure_bucket in HARDENED_FAILURE_BUCKET_VOCABULARY else "",
        same_failure_bucket if same_failure_bucket in HARDENED_FAILURE_BUCKET_VOCABULARY else "",
        primary_failure_bucket,
        *secondary_failure_buckets,
    ]
    source_bucket_non_empty = [value for value in source_bucket_values if value]
    unique_buckets = _ordered_unique(source_bucket_non_empty)
    bucket_alias_deduplicated = len(source_bucket_non_empty) > len(unique_buckets)
    bucket_count = len(
        _ordered_unique(
            [primary_failure_bucket, *secondary_failure_buckets]
        )
    )
    bucket_ambiguous = any(
        (
            primary_failure_bucket == "unknown",
            truth_conflict,
            len(
                [bucket for bucket in true_candidates if bucket != "unknown"]
            )
            > 1,
        )
    )

    failure_bucketing_status = "classified"
    failure_bucketing_validity = "valid"
    failure_bucketing_confidence = "high"
    if malformed_inputs:
        failure_bucketing_status = "degraded"
        failure_bucketing_validity = "malformed"
        failure_bucketing_confidence = "low"
    elif primary_failure_bucket == "truth_missing":
        failure_bucketing_status = "insufficient_truth"
        failure_bucketing_validity = "insufficient_truth"
        failure_bucketing_confidence = "low"
    elif primary_failure_bucket == "unknown" or bucket_ambiguous:
        failure_bucketing_status = "partial"
        failure_bucketing_validity = "partial"
        failure_bucketing_confidence = "medium"

    bucket_family = _PRIMARY_TO_FAMILY.get(primary_failure_bucket, "unknown")
    bucket_severity = _PRIMARY_TO_SEVERITY.get(primary_failure_bucket, "unknown")
    bucket_terminality_class = _bucket_terminality_class(
        primary_failure_bucket=primary_failure_bucket,
        final_closure_class=final_closure_class,
        terminal_stop_class=terminal_stop_class,
        retry_loop_status=retry_loop_status,
        lane_status=lane_status,
    )

    if primary_failure_bucket == "unknown":
        bucket_stability_class = "unknown"
    elif truth_conflict or primary_failure_bucket in {"oscillation", "no_progress"}:
        bucket_stability_class = "unstable"
    elif bucket_ambiguous:
        bucket_stability_class = "ambiguous"
    elif secondary_failure_buckets:
        bucket_stability_class = "likely_stable"
    else:
        bucket_stability_class = "stable"

    primary_reason_code = _PRIMARY_TO_REASON.get(primary_failure_bucket, "primary_unknown")
    reason_codes = _normalize_reason_codes(
        [
            "malformed_hardening_inputs" if malformed_inputs else "",
            "insufficient_hardening_truth"
            if failure_bucketing_status == "insufficient_truth"
            else "",
            primary_reason_code,
            "alias_deduplicated" if bucket_alias_deduplicated else "",
            "ambiguous_bucket" if bucket_ambiguous else "",
        ]
    )
    if not reason_codes:
        reason_codes = [primary_reason_code]

    bucket_normalized = primary_failure_bucket in HARDENED_FAILURE_BUCKET_VOCABULARY

    supporting_refs = _supporting_refs(
        [
            "failure_bucket_rollup.primary_failure_bucket" if narrow_primary_failure_bucket else "",
            "loop_hardening_contract.same_failure_bucket" if same_failure_bucket else "",
            "loop_hardening_contract.same_failure_signature" if same_failure_signature else "",
            "observability_rollup_contract.observability_status" if observability_status else "",
            "endgame_closure_contract.final_closure_class" if final_closure_class else "",
            "endgame_closure_contract.terminal_stop_class" if terminal_stop_class else "",
            "retry_reentry_loop_contract.retry_loop_status" if retry_loop_status else "",
            "loop_hardening_contract.loop_hardening_status" if loop_hardening_status else "",
            "lane_stabilization_contract.lane_status" if lane_status else "",
            "verification_closure_contract.verification_outcome" if verification_outcome else "",
            "execution_result_contract.execution_result_status" if execution_result_status else "",
            "bounded_execution_bridge.bounded_execution_status"
            if bounded_execution_bridge_status
            else "",
            "execution_authorization_gate.execution_authorization_status"
            if execution_authorization_status
            else "",
        ]
    )

    return {
        "schema_version": FAILURE_BUCKETING_HARDENING_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "failure_bucketing_status": _normalize_enum(
            failure_bucketing_status,
            allowed=FAILURE_BUCKETING_STATUSES,
            default="insufficient_truth",
        ),
        "failure_bucketing_validity": _normalize_enum(
            failure_bucketing_validity,
            allowed=FAILURE_BUCKETING_VALIDITIES,
            default="insufficient_truth",
        ),
        "failure_bucketing_confidence": _normalize_enum(
            failure_bucketing_confidence,
            allowed=FAILURE_BUCKETING_CONFIDENCE_LEVELS,
            default="low",
        ),
        "primary_failure_bucket": _normalize_enum(
            primary_failure_bucket,
            allowed=HARDENED_FAILURE_BUCKET_VOCABULARY,
            default="unknown",
        ),
        "secondary_failure_buckets": secondary_failure_buckets,
        "bucket_family": _normalize_enum(
            bucket_family,
            allowed=BUCKET_FAMILIES,
            default="unknown",
        ),
        "bucket_severity": _normalize_enum(
            bucket_severity,
            allowed=BUCKET_SEVERITIES,
            default="unknown",
        ),
        "bucket_stability_class": _normalize_enum(
            bucket_stability_class,
            allowed=BUCKET_STABILITY_CLASSES,
            default="unknown",
        ),
        "bucket_terminality_class": _normalize_enum(
            bucket_terminality_class,
            allowed=BUCKET_TERMINALITY_CLASSES,
            default="unknown",
        ),
        "bucket_normalized": bool(bucket_normalized),
        "bucket_ambiguous": bool(bucket_ambiguous),
        "bucket_alias_deduplicated": bool(bucket_alias_deduplicated),
        "bucket_count": _normalize_non_negative_int(bucket_count),
        "failure_bucketing_primary_reason": reason_codes[0],
        "failure_bucketing_reason_codes": reason_codes,
        "narrow_primary_failure_bucket": (
            _normalize_enum(
                narrow_primary_failure_bucket,
                allowed=HARDENED_FAILURE_BUCKET_VOCABULARY,
                default="unknown",
            )
            if narrow_primary_failure_bucket
            else "unknown"
        ),
        "same_failure_bucket": (
            _normalize_enum(
                same_failure_bucket,
                allowed=HARDENED_FAILURE_BUCKET_VOCABULARY,
                default="unknown",
            )
            if same_failure_bucket
            else "unknown"
        ),
        "same_failure_signature": same_failure_signature,
        "observability_status": observability_status or "insufficient_truth",
        "final_closure_class": final_closure_class or "unknown",
        "terminal_stop_class": terminal_stop_class or "unknown",
        "retry_loop_status": retry_loop_status or "unknown",
        "loop_hardening_status": loop_hardening_status or "unknown",
        "lane_status": lane_status or "unknown",
        "verification_outcome": verification_outcome or "unknown",
        "execution_result_status": execution_result_status or "unknown",
        "bounded_execution_bridge_status": bounded_execution_bridge_status or "unknown",
        "execution_authorization_status": execution_authorization_status or "unknown",
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


def build_failure_bucketing_hardening_run_state_summary_surface(
    failure_bucketing_hardening_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(failure_bucketing_hardening_payload or {})
    present = bool(
        _normalize_text(payload.get("failure_bucketing_status"), default="")
    ) or _normalize_bool(payload.get("failure_bucketing_hardening_present"))
    return {
        "failure_bucketing_hardening_present": present
    }


def build_failure_bucketing_hardening_summary_surface(
    failure_bucketing_hardening_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(failure_bucketing_hardening_payload or {})
    return {
        "failure_bucketing_status": _normalize_enum(
            payload.get("failure_bucketing_status"),
            allowed=FAILURE_BUCKETING_STATUSES,
            default="insufficient_truth",
        ),
        "failure_bucketing_validity": _normalize_enum(
            payload.get("failure_bucketing_validity"),
            allowed=FAILURE_BUCKETING_VALIDITIES,
            default="insufficient_truth",
        ),
        "failure_bucketing_confidence": _normalize_enum(
            payload.get("failure_bucketing_confidence"),
            allowed=FAILURE_BUCKETING_CONFIDENCE_LEVELS,
            default="low",
        ),
        "primary_failure_bucket": _normalize_enum(
            payload.get("primary_failure_bucket"),
            allowed=HARDENED_FAILURE_BUCKET_VOCABULARY,
            default="unknown",
        ),
        "bucket_family": _normalize_enum(
            payload.get("bucket_family"),
            allowed=BUCKET_FAMILIES,
            default="unknown",
        ),
        "bucket_severity": _normalize_enum(
            payload.get("bucket_severity"),
            allowed=BUCKET_SEVERITIES,
            default="unknown",
        ),
        "bucket_stability_class": _normalize_enum(
            payload.get("bucket_stability_class"),
            allowed=BUCKET_STABILITY_CLASSES,
            default="unknown",
        ),
        "bucket_terminality_class": _normalize_enum(
            payload.get("bucket_terminality_class"),
            allowed=BUCKET_TERMINALITY_CLASSES,
            default="unknown",
        ),
        "failure_bucketing_primary_reason": _normalize_text(
            payload.get("failure_bucketing_primary_reason"),
            default="primary_unknown",
        )
        if _normalize_text(payload.get("failure_bucketing_primary_reason")) in FAILURE_BUCKETING_REASON_CODES
        else "primary_unknown",
    }

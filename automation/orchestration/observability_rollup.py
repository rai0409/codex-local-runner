from __future__ import annotations

from typing import Any
from typing import Mapping

OBSERVABILITY_ROLLUP_SCHEMA_VERSION = "v1"
FAILURE_BUCKET_ROLLUP_SCHEMA_VERSION = "v1"
FLEET_RUN_ROLLUP_SCHEMA_VERSION = "v1"

OBSERVABILITY_STATUSES = {
    "ready",
    "partial",
    "degraded",
    "insufficient_truth",
}

OBSERVABILITY_VALIDITIES = {
    "valid",
    "partial",
    "malformed",
    "insufficient_truth",
}

OBSERVABILITY_CONFIDENCE_LEVELS = {
    "high",
    "medium",
    "low",
}

RUN_TERMINAL_CLASSES = {
    "safely_closed",
    "completed_not_closed",
    "manual_only",
    "external_wait",
    "terminal_non_success",
    "closure_unresolved",
    "not_terminal",
    "unknown",
}

OBSERVABILITY_REASON_CODES = {
    "malformed_observability_inputs",
    "missing_required_artifact",
    "safely_closed_terminal",
    "manual_escalation",
    "replan_required",
    "retry_exhausted_or_no_progress",
    "terminal_non_success_or_unresolved",
    "partial_or_degraded",
    "unknown",
    "no_reason",
}

OBSERVABILITY_REASON_ORDER = (
    "malformed_observability_inputs",
    "missing_required_artifact",
    "safely_closed_terminal",
    "manual_escalation",
    "replan_required",
    "retry_exhausted_or_no_progress",
    "terminal_non_success_or_unresolved",
    "partial_or_degraded",
    "unknown",
    "no_reason",
)

FAILURE_BUCKET_STATUSES = {
    "classified",
    "partial",
    "insufficient_truth",
    "not_applicable",
}

FAILURE_BUCKET_VALIDITIES = {
    "valid",
    "partial",
    "malformed",
    "insufficient_truth",
}

FAILURE_BUCKET_CONFIDENCE_LEVELS = {
    "high",
    "medium",
    "low",
}

FAILURE_BUCKET_VOCABULARY = {
    "objective_gap",
    "completion_gap",
    "approval_blocker",
    "reconcile_mismatch",
    "truth_missing",
    "verification_failure",
    "closure_unresolved",
    "execution_failure",
    "manual_only",
    "external_truth_pending",
    "unknown",
}

FAILURE_BUCKET_REASON_CODES = {
    "malformed_failure_bucket_inputs",
    "insufficient_bucket_truth",
    "not_applicable_terminal_success",
    "classified_truth_missing",
    "classified_objective_gap",
    "classified_completion_gap",
    "classified_approval_blocker",
    "classified_reconcile_mismatch",
    "classified_verification_failure",
    "classified_execution_failure",
    "classified_closure_unresolved",
    "classified_manual_only",
    "classified_external_truth_pending",
    "classified_unknown",
}

FAILURE_BUCKET_REASON_ORDER = (
    "malformed_failure_bucket_inputs",
    "insufficient_bucket_truth",
    "not_applicable_terminal_success",
    "classified_truth_missing",
    "classified_objective_gap",
    "classified_completion_gap",
    "classified_approval_blocker",
    "classified_reconcile_mismatch",
    "classified_verification_failure",
    "classified_execution_failure",
    "classified_closure_unresolved",
    "classified_manual_only",
    "classified_external_truth_pending",
    "classified_unknown",
)

FLEET_REASON_CODES = {
    "malformed_fleet_inputs",
    "insufficient_fleet_truth",
    "fleet_safely_closed",
    "fleet_manual_escalation",
    "fleet_replan_required",
    "fleet_retry_or_no_progress_stop",
    "fleet_terminal_non_success",
    "fleet_ready",
    "fleet_unknown",
}

FLEET_REASON_ORDER = (
    "malformed_fleet_inputs",
    "insufficient_fleet_truth",
    "fleet_safely_closed",
    "fleet_manual_escalation",
    "fleet_replan_required",
    "fleet_retry_or_no_progress_stop",
    "fleet_terminal_non_success",
    "fleet_ready",
    "fleet_unknown",
)

OBSERVABILITY_ROLLUP_RUN_STATE_SUMMARY_SAFE_FIELDS = (
    "observability_rollup_present",
)

OBSERVABILITY_ROLLUP_SUMMARY_SAFE_FIELDS = (
    "observability_status",
    "observability_validity",
    "observability_confidence",
    "run_terminal_class",
    "run_safely_closed",
    "run_manual_escalated",
    "run_retry_exhausted",
    "run_no_progress_stopped",
    "lane",
    "observability_primary_reason",
)

FAILURE_BUCKET_ROLLUP_SUMMARY_SAFE_FIELDS = (
    "failure_bucket_status",
    "failure_bucket_validity",
    "failure_bucket_confidence",
    "primary_failure_bucket",
    "bucket_count",
    "failure_bucket_primary_reason",
)

FLEET_RUN_ROLLUP_SUMMARY_SAFE_FIELDS = (
    "fleet_lane",
    "fleet_terminal_class",
    "fleet_primary_failure_bucket",
    "fleet_observability_status",
    "fleet_safely_closed_increment",
    "fleet_manual_escalation_increment",
    "fleet_no_progress_stop_increment",
    "fleet_retry_exhausted_increment",
    "fleet_primary_reason",
)

_REQUIRED_CONTRACT_ARTIFACTS = (
    "objective_contract.json",
    "completion_contract.json",
    "approval_transport.json",
    "reconcile_contract.json",
    "repair_suggestion_contract.json",
    "repair_plan_transport.json",
    "repair_approval_binding.json",
    "execution_authorization_gate.json",
    "bounded_execution_bridge.json",
    "execution_result_contract.json",
    "verification_closure_contract.json",
    "retry_reentry_loop_contract.json",
    "endgame_closure_contract.json",
    "loop_hardening_contract.json",
    "lane_stabilization_contract.json",
)

_OBS_ALLOWED_SUPPORTING_REFS = (
    "endgame_closure_contract.final_closure_class",
    "endgame_closure_contract.terminal_stop_class",
    "retry_reentry_loop_contract.retry_loop_status",
    "loop_hardening_contract.loop_hardening_status",
    "lane_stabilization_contract.lane_status",
    "verification_closure_contract.verification_outcome",
    "execution_result_contract.execution_result_status",
)

_FAILURE_ALLOWED_SUPPORTING_REFS = (
    "verification_closure_contract.verification_outcome",
    "retry_reentry_loop_contract.retry_loop_status",
    "loop_hardening_contract.loop_hardening_status",
    "endgame_closure_contract.final_closure_class",
    "lane_stabilization_contract.lane_status",
    "execution_result_contract.execution_result_status",
)

_FLEET_ALLOWED_SUPPORTING_REFS = (
    "endgame_closure_contract.final_closure_class",
    "lane_stabilization_contract.lane_status",
    "verification_closure_contract.verification_outcome",
    "retry_reentry_loop_contract.retry_loop_status",
    "loop_hardening_contract.loop_hardening_status",
    "execution_result_contract.execution_result_status",
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
    ordered: list[str] = []
    for value in values:
        text = _normalize_text(value, default="")
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


def _normalize_reason_codes(
    values: list[str],
    *,
    allowed: set[str],
    order: tuple[str, ...],
) -> list[str]:
    filtered = [value for value in _ordered_unique(values) if value in allowed]
    ordered: list[str] = []
    for reason in order:
        if reason in filtered:
            ordered.append(reason)
    return ordered


def _supporting_refs(values: list[str], *, allowed: tuple[str, ...]) -> list[str]:
    allowed_set = set(allowed)
    refs = [value for value in _ordered_unique(values) if value in allowed_set]
    return refs


def _map_run_terminal_class(final_closure_class: str) -> str:
    mapping = {
        "safely_closed": "safely_closed",
        "completed_but_not_closed": "completed_not_closed",
        "manual_closure_only": "manual_only",
        "external_truth_pending": "external_wait",
        "terminal_non_success": "terminal_non_success",
        "closure_unresolved": "closure_unresolved",
    }
    return mapping.get(final_closure_class, "unknown")


def _coerce_mapping(value: Any) -> tuple[dict[str, Any], bool]:
    if isinstance(value, Mapping):
        return dict(value), False
    return {}, value is not None


def _artifact_presence_count(artifact_presence: Mapping[str, Any]) -> int:
    count = 0
    for key in _REQUIRED_CONTRACT_ARTIFACTS:
        if _normalize_bool(artifact_presence.get(key)):
            count += 1
    return count


def _artifact_missing_detected(artifact_presence: Mapping[str, Any]) -> bool:
    for key in _REQUIRED_CONTRACT_ARTIFACTS:
        if not _normalize_bool(artifact_presence.get(key)):
            return True
    return False


def _surface_is_malformed(surface: Mapping[str, Any]) -> bool:
    validity_keys = (
        "validity",
        "execution_result_validity",
        "verification_validity",
        "retry_loop_validity",
        "endgame_closure_validity",
        "loop_hardening_validity",
        "lane_validity",
    )
    for key in validity_keys:
        if _normalize_text(surface.get(key), default="") == "malformed":
            return True
    return False


def build_observability_rollup_contract_surface(
    *,
    run_id: str,
    objective_contract_payload: Mapping[str, Any] | None,
    execution_result_contract_payload: Mapping[str, Any] | None,
    verification_closure_contract_payload: Mapping[str, Any] | None,
    retry_reentry_loop_contract_payload: Mapping[str, Any] | None,
    endgame_closure_contract_payload: Mapping[str, Any] | None,
    loop_hardening_contract_payload: Mapping[str, Any] | None,
    lane_stabilization_contract_payload: Mapping[str, Any] | None,
    run_state_payload: Mapping[str, Any] | None,
    artifact_presence: Mapping[str, Any] | None = None,
    contract_artifact_index_payload: Mapping[str, Any] | None = None,
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
    run_state, run_state_malformed = _coerce_mapping(run_state_payload)
    artifact_presence_map, _ = _coerce_mapping(artifact_presence)
    contract_index, contract_index_malformed = _coerce_mapping(contract_artifact_index_payload)

    malformed_inputs = any(
        (
            objective_malformed,
            execution_result_malformed,
            verification_malformed,
            retry_loop_malformed,
            endgame_malformed,
            loop_hardening_malformed,
            lane_malformed,
            run_state_malformed,
            contract_index_malformed,
        )
    )

    objective_id = _normalize_text(
        objective.get("objective_id") or run_state.get("objective_id"),
        default="",
    )
    final_closure_class = _normalize_text(endgame.get("final_closure_class"), default="")
    terminal_stop_class = _normalize_text(endgame.get("terminal_stop_class"), default="")
    retry_loop_status = _normalize_text(retry_loop.get("retry_loop_status"), default="")
    loop_hardening_status = _normalize_text(
        loop_hardening.get("loop_hardening_status"), default=""
    )
    lane_status = _normalize_text(lane.get("lane_status"), default="")
    verification_outcome = _normalize_text(verification.get("verification_outcome"), default="")
    execution_result_status = _normalize_text(
        execution_result.get("execution_result_status"), default=""
    )

    run_terminal_class = _map_run_terminal_class(final_closure_class)
    run_terminal = run_terminal_class in {
        "safely_closed",
        "completed_not_closed",
        "manual_only",
        "external_wait",
        "terminal_non_success",
        "closure_unresolved",
    }
    run_safely_closed = run_terminal_class == "safely_closed"
    run_started = bool(_normalize_text(run_state.get("state"), default="")) or bool(
        _normalize_text(run_id, default="")
    )
    run_completed = run_terminal

    run_manual_escalated = any(
        (
            _normalize_bool(retry_loop.get("manual_escalation_required")),
            _normalize_bool(loop_hardening.get("forced_manual_escalation_required")),
            _normalize_bool(lane.get("lane_manual_review_required")),
            run_terminal_class == "manual_only",
        )
    )
    run_replan_required = any(
        (
            _normalize_bool(retry_loop.get("replan_required")),
            _normalize_bool(lane.get("lane_replan_required")),
        )
    )
    run_retry_exhausted = any(
        (
            _normalize_bool(retry_loop.get("retry_exhausted")),
            _normalize_bool(retry_loop.get("reentry_exhausted")),
            _normalize_bool(retry_loop.get("same_failure_exhausted")),
            retry_loop_status == "exhausted",
        )
    )
    run_no_progress_stopped = any(
        (
            _normalize_bool(retry_loop.get("no_progress_stop_required")),
            _normalize_bool(loop_hardening.get("no_progress_stop_required")),
        )
    )
    run_unstable_loop_detected = any(
        (
            _normalize_bool(loop_hardening.get("unstable_loop_detected")),
            _normalize_bool(loop_hardening.get("oscillation_detected")),
        )
    )

    retry_attempt_count = _normalize_non_negative_int(
        retry_loop.get("attempt_count") if retry_loop.get("attempt_count") is not None else run_state.get("attempt_count")
    )
    reentry_count = _normalize_non_negative_int(
        retry_loop.get("reentry_count") if retry_loop.get("reentry_count") is not None else run_state.get("reentry_count")
    )
    same_failure_count = _normalize_non_negative_int(
        retry_loop.get("same_failure_count")
        if retry_loop.get("same_failure_count") is not None
        else run_state.get("same_failure_count")
    )

    lane_name = _normalize_text(
        lane.get("current_lane") or lane.get("target_lane"),
        default="unknown",
    )
    if not lane_name:
        lane_name = "unknown"
    lane_valid = _normalize_bool(lane.get("lane_valid"))
    lane_execution_allowed = _normalize_bool(lane.get("lane_execution_allowed"))

    artifact_missing_detected = _artifact_missing_detected(artifact_presence_map)
    artifact_contract_count = _artifact_presence_count(artifact_presence_map)
    artifact_malformed_detected = malformed_inputs or any(
        _surface_is_malformed(surface)
        for surface in (execution_result, verification, retry_loop, endgame, loop_hardening, lane)
        if isinstance(surface, Mapping)
    )
    artifact_index_present = bool(contract_index) or _normalize_bool(
        artifact_presence_map.get("contract_artifact_index.json")
    )

    essential_truth_present = any(
        (
            bool(execution_result_status),
            bool(verification_outcome),
            bool(retry_loop_status),
            bool(final_closure_class),
            bool(lane_status),
        )
    )

    observability_status = "ready"
    observability_validity = "valid"
    observability_confidence = "high"
    if malformed_inputs or artifact_malformed_detected:
        observability_status = "degraded"
        observability_validity = "malformed"
        observability_confidence = "low"
    elif not essential_truth_present:
        observability_status = "insufficient_truth"
        observability_validity = "insufficient_truth"
        observability_confidence = "low"
    elif artifact_missing_detected:
        observability_status = "partial"
        observability_validity = "partial"
        observability_confidence = "medium"

    reason_lead = "unknown"
    if malformed_inputs or artifact_malformed_detected:
        reason_lead = "malformed_observability_inputs"
    elif artifact_missing_detected:
        reason_lead = "missing_required_artifact"
    elif run_safely_closed:
        reason_lead = "safely_closed_terminal"
    elif run_manual_escalated:
        reason_lead = "manual_escalation"
    elif run_replan_required:
        reason_lead = "replan_required"
    elif run_retry_exhausted or run_no_progress_stopped or run_unstable_loop_detected:
        reason_lead = "retry_exhausted_or_no_progress"
    elif run_terminal_class in {"terminal_non_success", "closure_unresolved"}:
        reason_lead = "terminal_non_success_or_unresolved"
    elif observability_status in {"partial", "degraded"}:
        reason_lead = "partial_or_degraded"

    reason_codes = _normalize_reason_codes(
        [
            reason_lead,
            "missing_required_artifact" if artifact_missing_detected else "",
            "safely_closed_terminal" if run_safely_closed else "",
            "manual_escalation" if run_manual_escalated else "",
            "replan_required" if run_replan_required else "",
            (
                "retry_exhausted_or_no_progress"
                if run_retry_exhausted or run_no_progress_stopped or run_unstable_loop_detected
                else ""
            ),
            (
                "terminal_non_success_or_unresolved"
                if run_terminal_class in {"terminal_non_success", "closure_unresolved"}
                else ""
            ),
            "partial_or_degraded" if observability_status in {"partial", "degraded"} else "",
        ],
        allowed=OBSERVABILITY_REASON_CODES,
        order=OBSERVABILITY_REASON_ORDER,
    )
    if not reason_codes:
        reason_codes = ["no_reason"]

    supporting_refs = _supporting_refs(
        [
            "endgame_closure_contract.final_closure_class" if final_closure_class else "",
            "endgame_closure_contract.terminal_stop_class" if terminal_stop_class else "",
            "retry_reentry_loop_contract.retry_loop_status" if retry_loop_status else "",
            "loop_hardening_contract.loop_hardening_status" if loop_hardening_status else "",
            "lane_stabilization_contract.lane_status" if lane_status else "",
            "verification_closure_contract.verification_outcome" if verification_outcome else "",
            "execution_result_contract.execution_result_status" if execution_result_status else "",
        ],
        allowed=_OBS_ALLOWED_SUPPORTING_REFS,
    )

    return {
        "schema_version": OBSERVABILITY_ROLLUP_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "observability_status": _normalize_enum(
            observability_status,
            allowed=OBSERVABILITY_STATUSES,
            default="insufficient_truth",
        ),
        "observability_validity": _normalize_enum(
            observability_validity,
            allowed=OBSERVABILITY_VALIDITIES,
            default="insufficient_truth",
        ),
        "observability_confidence": _normalize_enum(
            observability_confidence,
            allowed=OBSERVABILITY_CONFIDENCE_LEVELS,
            default="low",
        ),
        "run_started": bool(run_started),
        "run_completed": bool(run_completed),
        "run_safely_closed": bool(run_safely_closed),
        "run_terminal": bool(run_terminal),
        "run_terminal_class": _normalize_enum(
            run_terminal_class,
            allowed=RUN_TERMINAL_CLASSES,
            default="unknown",
        ),
        "run_manual_escalated": bool(run_manual_escalated),
        "run_replan_required": bool(run_replan_required),
        "run_retry_exhausted": bool(run_retry_exhausted),
        "run_no_progress_stopped": bool(run_no_progress_stopped),
        "run_unstable_loop_detected": bool(run_unstable_loop_detected),
        "retry_attempt_count": retry_attempt_count,
        "reentry_count": reentry_count,
        "same_failure_count": same_failure_count,
        "lane": lane_name or "unknown",
        "lane_valid": bool(lane_valid),
        "lane_execution_allowed": bool(lane_execution_allowed),
        "artifact_missing_detected": bool(artifact_missing_detected),
        "artifact_malformed_detected": bool(artifact_malformed_detected),
        "artifact_contract_count": artifact_contract_count,
        "artifact_index_present": bool(artifact_index_present),
        "observability_primary_reason": reason_codes[0],
        "observability_reason_codes": reason_codes,
        "final_closure_class": final_closure_class or "unknown",
        "terminal_stop_class": terminal_stop_class or "unknown",
        "retry_loop_status": retry_loop_status or "unknown",
        "loop_hardening_status": loop_hardening_status or "unknown",
        "lane_status": lane_status or "unknown",
        "verification_outcome": verification_outcome or "unknown",
        "execution_result_status": execution_result_status or "unknown",
        "supporting_compact_truth_refs": supporting_refs,
    }


def build_failure_bucket_rollup_surface(
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
            run_state_malformed,
        )
    )

    objective_id = _normalize_text(
        objective.get("objective_id") or run_state.get("objective_id"),
        default="",
    )

    verification_outcome = _normalize_text(verification.get("verification_outcome"), default="")
    verification_status = _normalize_text(verification.get("verification_status"), default="")
    execution_result_status = _normalize_text(
        execution_result.get("execution_result_status"), default=""
    )
    retry_loop_status = _normalize_text(retry_loop.get("retry_loop_status"), default="")
    loop_hardening_status = _normalize_text(
        loop_hardening.get("loop_hardening_status"), default=""
    )
    final_closure_class = _normalize_text(endgame.get("final_closure_class"), default="")
    lane_status = _normalize_text(lane.get("lane_status"), default="")

    truth_missing = any(
        (
            _normalize_text(observability.get("observability_status")) == "insufficient_truth",
            _normalize_bool(observability.get("artifact_missing_detected")),
            verification_status == "not_verifiable",
            _normalize_text(verification.get("verification_validity"))
            == "insufficient_truth",
        )
    )
    objective_gap = any(
        (
            verification_outcome == "objective_gap",
            _normalize_text(verification.get("objective_satisfaction_status"))
            == "not_satisfied",
        )
    )
    completion_gap = any(
        (
            verification_outcome == "completion_gap",
            _normalize_text(verification.get("completion_satisfaction_status"))
            == "not_satisfied",
        )
    )
    approval_blocker = any(
        (
            _normalize_text(run_state.get("approval_status")) in {"denied", "deferred", "absent"},
            _normalize_text(run_state.get("approval_transport_status")) in {"missing", "incompatible"},
            verification_outcome == "manual_closure_only",
        )
    )
    reconcile_mismatch = any(
        (
            _normalize_text(run_state.get("reconcile_status")) == "inconsistent",
            bool(_normalize_text(run_state.get("reconcile_primary_mismatch"))),
        )
    )
    verification_failure = verification_status == "verified_failure"
    execution_failure = execution_result_status in {"failed", "partial"}
    closure_unresolved = final_closure_class == "closure_unresolved"
    manual_only = final_closure_class == "manual_closure_only"
    external_truth_pending = any(
        (
            final_closure_class == "external_truth_pending",
            verification_outcome == "external_truth_pending",
        )
    )

    precedence = (
        ("truth_missing", truth_missing),
        ("objective_gap", objective_gap),
        ("completion_gap", completion_gap),
        ("approval_blocker", approval_blocker),
        ("reconcile_mismatch", reconcile_mismatch),
        ("verification_failure", verification_failure),
        ("execution_failure", execution_failure),
        ("closure_unresolved", closure_unresolved),
        ("manual_only", manual_only),
        ("external_truth_pending", external_truth_pending),
    )
    primary_failure_bucket = "unknown"
    for bucket, is_true in precedence:
        if is_true:
            primary_failure_bucket = bucket
            break

    if final_closure_class == "safely_closed" and primary_failure_bucket == "unknown":
        failure_bucket_status = "not_applicable"
    elif truth_missing and primary_failure_bucket in {"truth_missing", "unknown"}:
        failure_bucket_status = "insufficient_truth"
    elif primary_failure_bucket == "unknown":
        failure_bucket_status = "partial"
    else:
        failure_bucket_status = "classified"

    failure_bucket_validity = "valid"
    if malformed_inputs:
        failure_bucket_validity = "malformed"
    elif failure_bucket_status == "insufficient_truth":
        failure_bucket_validity = "insufficient_truth"
    elif failure_bucket_status == "partial":
        failure_bucket_validity = "partial"

    failure_bucket_confidence = "high"
    if failure_bucket_validity in {"malformed", "insufficient_truth"}:
        failure_bucket_confidence = "low"
    elif failure_bucket_status in {"partial", "not_applicable"} or primary_failure_bucket == "unknown":
        failure_bucket_confidence = "medium"

    same_failure_bucket = _normalize_text(
        loop_hardening.get("same_failure_bucket"),
        default="",
    )
    if same_failure_bucket not in FAILURE_BUCKET_VOCABULARY:
        same_failure_bucket = primary_failure_bucket
    if same_failure_bucket not in FAILURE_BUCKET_VOCABULARY:
        same_failure_bucket = "unknown"

    same_failure_signature = _normalize_text(
        loop_hardening.get("same_failure_signature"),
        default="",
    )
    if not same_failure_signature:
        signature_hint = _normalize_text(
            verification_outcome or execution_result_status or final_closure_class,
            default="unknown",
        )
        same_failure_signature = f"bucket={same_failure_bucket}|hint={signature_hint}"

    secondary_candidates: list[str] = []
    for bucket, is_true in precedence:
        if not is_true or bucket == primary_failure_bucket:
            continue
        secondary_candidates.append(bucket)
    secondary_failure_buckets = _ordered_unique(secondary_candidates)[:2]
    secondary_failure_buckets = [
        bucket for bucket in secondary_failure_buckets if bucket in FAILURE_BUCKET_VOCABULARY
    ]
    emitted_buckets = _ordered_unique(
        [primary_failure_bucket] + secondary_failure_buckets
    )
    emitted_buckets = [bucket for bucket in emitted_buckets if bucket in FAILURE_BUCKET_VOCABULARY]
    bucket_count = len(emitted_buckets)

    reason_lead = "classified_unknown"
    if malformed_inputs:
        reason_lead = "malformed_failure_bucket_inputs"
    elif failure_bucket_status == "insufficient_truth":
        reason_lead = "insufficient_bucket_truth"
    elif failure_bucket_status == "not_applicable":
        reason_lead = "not_applicable_terminal_success"
    elif primary_failure_bucket in FAILURE_BUCKET_VOCABULARY:
        reason_lead = f"classified_{primary_failure_bucket}"

    reason_codes = _normalize_reason_codes(
        [
            reason_lead,
            "classified_truth_missing" if truth_missing else "",
            "classified_objective_gap" if objective_gap else "",
            "classified_completion_gap" if completion_gap else "",
            "classified_approval_blocker" if approval_blocker else "",
            "classified_reconcile_mismatch" if reconcile_mismatch else "",
            "classified_verification_failure" if verification_failure else "",
            "classified_execution_failure" if execution_failure else "",
            "classified_closure_unresolved" if closure_unresolved else "",
            "classified_manual_only" if manual_only else "",
            "classified_external_truth_pending" if external_truth_pending else "",
        ],
        allowed=FAILURE_BUCKET_REASON_CODES,
        order=FAILURE_BUCKET_REASON_ORDER,
    )
    if not reason_codes:
        reason_codes = ["classified_unknown"]

    supporting_refs = _supporting_refs(
        [
            "verification_closure_contract.verification_outcome" if verification_outcome else "",
            "retry_reentry_loop_contract.retry_loop_status" if retry_loop_status else "",
            "loop_hardening_contract.loop_hardening_status" if loop_hardening_status else "",
            "endgame_closure_contract.final_closure_class" if final_closure_class else "",
            "lane_stabilization_contract.lane_status" if lane_status else "",
            "execution_result_contract.execution_result_status" if execution_result_status else "",
        ],
        allowed=_FAILURE_ALLOWED_SUPPORTING_REFS,
    )

    return {
        "schema_version": FAILURE_BUCKET_ROLLUP_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "failure_bucket_status": _normalize_enum(
            failure_bucket_status,
            allowed=FAILURE_BUCKET_STATUSES,
            default="insufficient_truth",
        ),
        "failure_bucket_validity": _normalize_enum(
            failure_bucket_validity,
            allowed=FAILURE_BUCKET_VALIDITIES,
            default="insufficient_truth",
        ),
        "failure_bucket_confidence": _normalize_enum(
            failure_bucket_confidence,
            allowed=FAILURE_BUCKET_CONFIDENCE_LEVELS,
            default="low",
        ),
        "primary_failure_bucket": _normalize_enum(
            primary_failure_bucket,
            allowed=FAILURE_BUCKET_VOCABULARY,
            default="unknown",
        ),
        "secondary_failure_buckets": secondary_failure_buckets,
        "same_failure_bucket": _normalize_enum(
            same_failure_bucket,
            allowed=FAILURE_BUCKET_VOCABULARY,
            default="unknown",
        ),
        "same_failure_signature": same_failure_signature,
        "bucket_count": bucket_count,
        "manual_escalation_required": _normalize_bool(
            retry_loop.get("manual_escalation_required")
        )
        or _normalize_bool(lane.get("lane_manual_review_required")),
        "replan_required": _normalize_bool(retry_loop.get("replan_required"))
        or _normalize_bool(lane.get("lane_replan_required")),
        "closure_unresolved": bool(closure_unresolved),
        "no_progress_stop_required": _normalize_bool(
            retry_loop.get("no_progress_stop_required")
        )
        or _normalize_bool(loop_hardening.get("no_progress_stop_required")),
        "retry_freeze_required": _normalize_bool(loop_hardening.get("retry_freeze_required")),
        "failure_bucket_primary_reason": reason_codes[0],
        "failure_bucket_reason_codes": reason_codes,
        "verification_outcome": verification_outcome or "unknown",
        "retry_loop_status": retry_loop_status or "unknown",
        "loop_hardening_status": loop_hardening_status or "unknown",
        "final_closure_class": final_closure_class or "unknown",
        "lane_status": lane_status or "unknown",
        "execution_result_status": execution_result_status or "unknown",
        "supporting_compact_truth_refs": supporting_refs,
    }


def build_fleet_run_rollup_surface(
    *,
    run_id: str,
    objective_contract_payload: Mapping[str, Any] | None,
    observability_rollup_payload: Mapping[str, Any] | None,
    failure_bucket_rollup_payload: Mapping[str, Any] | None,
    verification_closure_contract_payload: Mapping[str, Any] | None,
    retry_reentry_loop_contract_payload: Mapping[str, Any] | None,
    endgame_closure_contract_payload: Mapping[str, Any] | None,
    loop_hardening_contract_payload: Mapping[str, Any] | None,
    lane_stabilization_contract_payload: Mapping[str, Any] | None,
    execution_result_contract_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    objective, objective_malformed = _coerce_mapping(objective_contract_payload)
    observability, observability_malformed = _coerce_mapping(observability_rollup_payload)
    failure_bucket, failure_bucket_malformed = _coerce_mapping(failure_bucket_rollup_payload)
    verification, verification_malformed = _coerce_mapping(
        verification_closure_contract_payload
    )
    retry_loop, retry_loop_malformed = _coerce_mapping(retry_reentry_loop_contract_payload)
    endgame, endgame_malformed = _coerce_mapping(endgame_closure_contract_payload)
    loop_hardening, loop_hardening_malformed = _coerce_mapping(loop_hardening_contract_payload)
    lane, lane_malformed = _coerce_mapping(lane_stabilization_contract_payload)
    execution_result, execution_result_malformed = _coerce_mapping(
        execution_result_contract_payload
    )

    malformed_inputs = any(
        (
            objective_malformed,
            observability_malformed,
            failure_bucket_malformed,
            verification_malformed,
            retry_loop_malformed,
            endgame_malformed,
            loop_hardening_malformed,
            lane_malformed,
            execution_result_malformed,
        )
    )

    objective_id = _normalize_text(objective.get("objective_id"), default="")
    run_safely_closed = _normalize_bool(observability.get("run_safely_closed"))
    run_manual_escalated = _normalize_bool(observability.get("run_manual_escalated"))
    run_replan_required = _normalize_bool(observability.get("run_replan_required"))
    run_no_progress_stopped = _normalize_bool(observability.get("run_no_progress_stopped"))
    run_retry_exhausted = _normalize_bool(observability.get("run_retry_exhausted"))
    artifact_missing_detected = _normalize_bool(observability.get("artifact_missing_detected"))
    artifact_malformed_detected = _normalize_bool(
        observability.get("artifact_malformed_detected")
    )

    final_closure_class = _normalize_text(endgame.get("final_closure_class"), default="")
    lane_status = _normalize_text(lane.get("lane_status"), default="")
    verification_outcome = _normalize_text(verification.get("verification_outcome"), default="")
    retry_loop_status = _normalize_text(retry_loop.get("retry_loop_status"), default="")
    loop_hardening_status = _normalize_text(
        loop_hardening.get("loop_hardening_status"), default=""
    )
    execution_result_status = _normalize_text(
        execution_result.get("execution_result_status"), default=""
    )

    fleet_lane = _normalize_text(
        observability.get("lane") or lane.get("current_lane") or lane.get("target_lane"),
        default="unknown",
    )
    fleet_terminal_class = _normalize_text(
        observability.get("run_terminal_class") or _map_run_terminal_class(final_closure_class),
        default="unknown",
    )
    fleet_primary_failure_bucket = _normalize_text(
        failure_bucket.get("primary_failure_bucket"),
        default="unknown",
    )
    fleet_observability_status = _normalize_text(
        observability.get("observability_status"),
        default="insufficient_truth",
    )

    reason_lead = "fleet_ready"
    if malformed_inputs:
        reason_lead = "malformed_fleet_inputs"
    elif fleet_observability_status == "insufficient_truth":
        reason_lead = "insufficient_fleet_truth"
    elif run_safely_closed:
        reason_lead = "fleet_safely_closed"
    elif run_manual_escalated:
        reason_lead = "fleet_manual_escalation"
    elif run_replan_required:
        reason_lead = "fleet_replan_required"
    elif run_retry_exhausted or run_no_progress_stopped:
        reason_lead = "fleet_retry_or_no_progress_stop"
    elif fleet_terminal_class in {"terminal_non_success", "closure_unresolved"}:
        reason_lead = "fleet_terminal_non_success"

    reason_codes = _normalize_reason_codes(
        [
            reason_lead,
            "fleet_safely_closed" if run_safely_closed else "",
            "fleet_manual_escalation" if run_manual_escalated else "",
            "fleet_replan_required" if run_replan_required else "",
            (
                "fleet_retry_or_no_progress_stop"
                if run_retry_exhausted or run_no_progress_stopped
                else ""
            ),
            (
                "fleet_terminal_non_success"
                if fleet_terminal_class in {"terminal_non_success", "closure_unresolved"}
                else ""
            ),
        ],
        allowed=FLEET_REASON_CODES,
        order=FLEET_REASON_ORDER,
    )
    if not reason_codes:
        reason_codes = ["fleet_unknown"]

    supporting_refs = _supporting_refs(
        [
            "endgame_closure_contract.final_closure_class" if final_closure_class else "",
            "lane_stabilization_contract.lane_status" if lane_status else "",
            "verification_closure_contract.verification_outcome" if verification_outcome else "",
            "retry_reentry_loop_contract.retry_loop_status" if retry_loop_status else "",
            "loop_hardening_contract.loop_hardening_status" if loop_hardening_status else "",
            "execution_result_contract.execution_result_status" if execution_result_status else "",
        ],
        allowed=_FLEET_ALLOWED_SUPPORTING_REFS,
    )

    return {
        "schema_version": FLEET_RUN_ROLLUP_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "fleet_started_increment": 1 if _normalize_bool(observability.get("run_started")) else 0,
        "fleet_completed_increment": 1 if _normalize_bool(observability.get("run_completed")) else 0,
        "fleet_safely_closed_increment": 1 if run_safely_closed else 0,
        "fleet_manual_escalation_increment": 1 if run_manual_escalated else 0,
        "fleet_replan_increment": 1 if run_replan_required else 0,
        "fleet_no_progress_stop_increment": 1 if run_no_progress_stopped else 0,
        "fleet_retry_exhausted_increment": 1 if run_retry_exhausted else 0,
        "fleet_artifact_missing_increment": 1 if artifact_missing_detected else 0,
        "fleet_artifact_malformed_increment": 1 if artifact_malformed_detected else 0,
        "fleet_lane": fleet_lane or "unknown",
        "fleet_terminal_class": fleet_terminal_class or "unknown",
        "fleet_primary_failure_bucket": _normalize_enum(
            fleet_primary_failure_bucket,
            allowed=FAILURE_BUCKET_VOCABULARY,
            default="unknown",
        ),
        "fleet_observability_status": _normalize_enum(
            fleet_observability_status,
            allowed=OBSERVABILITY_STATUSES,
            default="insufficient_truth",
        ),
        "fleet_primary_reason": reason_codes[0],
        "fleet_reason_codes": reason_codes,
        "final_closure_class": final_closure_class or "unknown",
        "lane_status": lane_status or "unknown",
        "verification_outcome": verification_outcome or "unknown",
        "retry_loop_status": retry_loop_status or "unknown",
        "loop_hardening_status": loop_hardening_status or "unknown",
        "execution_result_status": execution_result_status or "unknown",
        "supporting_compact_truth_refs": supporting_refs,
    }


def build_observability_rollup_run_state_summary_surface(
    observability_rollup_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(observability_rollup_payload or {})
    status = _normalize_text(payload.get("observability_status"), default="")
    return {
        "observability_rollup_present": _normalize_bool(
            payload.get("observability_rollup_present")
        )
        or bool(status),
    }


def build_observability_rollup_contract_summary_surface(
    observability_rollup_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(observability_rollup_payload or {})
    return {
        "observability_status": _normalize_enum(
            payload.get("observability_status"),
            allowed=OBSERVABILITY_STATUSES,
            default="insufficient_truth",
        ),
        "observability_validity": _normalize_enum(
            payload.get("observability_validity"),
            allowed=OBSERVABILITY_VALIDITIES,
            default="insufficient_truth",
        ),
        "observability_confidence": _normalize_enum(
            payload.get("observability_confidence"),
            allowed=OBSERVABILITY_CONFIDENCE_LEVELS,
            default="low",
        ),
        "run_terminal_class": _normalize_enum(
            payload.get("run_terminal_class"),
            allowed=RUN_TERMINAL_CLASSES,
            default="unknown",
        ),
        "run_safely_closed": _normalize_bool(payload.get("run_safely_closed")),
        "run_manual_escalated": _normalize_bool(payload.get("run_manual_escalated")),
        "run_retry_exhausted": _normalize_bool(payload.get("run_retry_exhausted")),
        "run_no_progress_stopped": _normalize_bool(payload.get("run_no_progress_stopped")),
        "lane": _normalize_text(payload.get("lane"), default="unknown"),
        "observability_primary_reason": _normalize_text(
            payload.get("observability_primary_reason"), default="unknown"
        ),
    }


def build_failure_bucket_rollup_summary_surface(
    failure_bucket_rollup_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(failure_bucket_rollup_payload or {})
    return {
        "failure_bucket_status": _normalize_enum(
            payload.get("failure_bucket_status"),
            allowed=FAILURE_BUCKET_STATUSES,
            default="insufficient_truth",
        ),
        "failure_bucket_validity": _normalize_enum(
            payload.get("failure_bucket_validity"),
            allowed=FAILURE_BUCKET_VALIDITIES,
            default="insufficient_truth",
        ),
        "failure_bucket_confidence": _normalize_enum(
            payload.get("failure_bucket_confidence"),
            allowed=FAILURE_BUCKET_CONFIDENCE_LEVELS,
            default="low",
        ),
        "primary_failure_bucket": _normalize_enum(
            payload.get("primary_failure_bucket"),
            allowed=FAILURE_BUCKET_VOCABULARY,
            default="unknown",
        ),
        "bucket_count": _normalize_non_negative_int(payload.get("bucket_count")),
        "failure_bucket_primary_reason": _normalize_text(
            payload.get("failure_bucket_primary_reason"),
            default="classified_unknown",
        ),
    }


def build_fleet_run_rollup_summary_surface(
    fleet_run_rollup_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(fleet_run_rollup_payload or {})
    return {
        "fleet_lane": _normalize_text(payload.get("fleet_lane"), default="unknown"),
        "fleet_terminal_class": _normalize_text(
            payload.get("fleet_terminal_class"),
            default="unknown",
        ),
        "fleet_primary_failure_bucket": _normalize_enum(
            payload.get("fleet_primary_failure_bucket"),
            allowed=FAILURE_BUCKET_VOCABULARY,
            default="unknown",
        ),
        "fleet_observability_status": _normalize_enum(
            payload.get("fleet_observability_status"),
            allowed=OBSERVABILITY_STATUSES,
            default="insufficient_truth",
        ),
        "fleet_safely_closed_increment": _normalize_non_negative_int(
            payload.get("fleet_safely_closed_increment")
        ),
        "fleet_manual_escalation_increment": _normalize_non_negative_int(
            payload.get("fleet_manual_escalation_increment")
        ),
        "fleet_no_progress_stop_increment": _normalize_non_negative_int(
            payload.get("fleet_no_progress_stop_increment")
        ),
        "fleet_retry_exhausted_increment": _normalize_non_negative_int(
            payload.get("fleet_retry_exhausted_increment")
        ),
        "fleet_primary_reason": _normalize_text(
            payload.get("fleet_primary_reason"),
            default="fleet_unknown",
        ),
    }

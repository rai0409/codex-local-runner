from __future__ import annotations

from typing import Any
from typing import Mapping


APPROVAL_SAFETY_SCHEMA_VERSION = "v1"

APPROVAL_SAFETY_STATUSES = {
    "not_applicable",
    "safe_to_deliver",
    "duplicate_pending",
    "cooldown_active",
    "delivery_deferred",
    "delivery_blocked",
    "loop_suspected",
    "insufficient_truth",
}

APPROVAL_SAFETY_VALIDITIES = {
    "valid",
    "partial",
    "malformed",
    "insufficient_truth",
}

APPROVAL_SAFETY_CONFIDENCE_LEVELS = {
    "high",
    "medium",
    "low",
}

APPROVAL_SAFETY_DECISIONS = {
    "allow_delivery",
    "suppress_duplicate",
    "defer_until_cooldown_expires",
    "block_until_response_or_clear",
    "block_loop_suspected",
    "unknown",
}

APPROVAL_SAFETY_REASON_CODES = {
    "malformed_safety_inputs",
    "insufficient_safety_truth",
    "approval_not_required",
    "duplicate_pending_uncleared",
    "cooldown_window_active",
    "loop_notification_churn_suspected",
    "response_cleared_pending_duplicate",
    "delivery_safe_to_send",
    "unknown_safety_posture",
    "alias_deduplicated",
    "no_reason",
}

APPROVAL_SAFETY_REASON_ORDER = (
    "malformed_safety_inputs",
    "insufficient_safety_truth",
    "approval_not_required",
    "duplicate_pending_uncleared",
    "cooldown_window_active",
    "loop_notification_churn_suspected",
    "delivery_safe_to_send",
    "response_cleared_pending_duplicate",
    "unknown_safety_posture",
    "alias_deduplicated",
    "no_reason",
)

_ALLOWED_SUPPORTING_REFS = (
    "approval_email_delivery_contract.approval_email_status",
    "approval_delivery_handoff_contract.approval_delivery_handoff_status",
    "approval_delivery_handoff_contract.delivery_outcome",
    "approval_delivery_handoff_contract.approval_pending_human_response",
    "approval_response_contract.approval_response_status",
    "approved_restart_contract.approved_restart_status",
    "approval_email_delivery_contract.approval_required",
    "approval_email_delivery_contract.approval_priority",
    "approval_email_delivery_contract.proposed_next_direction",
    "approval_email_delivery_contract.proposed_target_lane",
    "approval_email_delivery_contract.proposed_restart_mode",
    "lane_stabilization_contract.current_lane",
    "failure_bucketing_hardening_contract.primary_failure_bucket",
    "failure_bucketing_hardening_contract.bucket_severity",
)

APPROVAL_SAFETY_RUN_STATE_SUMMARY_SAFE_FIELDS = (
    "approval_safety_present",
)

APPROVAL_SAFETY_SUMMARY_SAFE_FIELDS = (
    "approval_safety_status",
    "approval_safety_validity",
    "approval_safety_confidence",
    "approval_safety_decision",
    "approval_duplicate_detected",
    "approval_pending_duplicate",
    "approval_cooldown_active",
    "approval_loop_suspected",
    "approval_delivery_allowed_by_safety",
    "approval_safety_primary_reason",
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
        stripped = value.strip()
        if stripped.isdigit():
            return max(0, int(stripped))
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


def _normalize_reason_codes(values: list[str]) -> list[str]:
    normalized = [value for value in _ordered_unique(values) if value in APPROVAL_SAFETY_REASON_CODES]
    ordered = [code for code in APPROVAL_SAFETY_REASON_ORDER if code in normalized]
    return ordered if ordered else ["no_reason"]


def _normalize_supporting_refs(values: list[str]) -> list[str]:
    allowed = set(_ALLOWED_SUPPORTING_REFS)
    return [value for value in _ordered_unique(values) if value in allowed]


def _coerce_mapping(value: Any) -> tuple[dict[str, Any], bool]:
    if isinstance(value, Mapping):
        return dict(value), False
    return {}, value is not None


def _build_approval_dedup_key(
    *,
    run_id: str,
    objective_id: str,
    approval_required: bool,
    proposed_next_direction: str,
    proposed_restart_mode: str,
    current_lane: str,
    primary_failure_bucket: str,
    recipient_target: str,
    recipient_class: str,
) -> str:
    return "|".join(
        [
            "v1",
            f"rid={_normalize_text(run_id, default='')}",
            f"oid={_normalize_text(objective_id, default='')}",
            f"req={1 if approval_required else 0}",
            f"dir={_normalize_text(proposed_next_direction, default='unknown')}",
            f"mode={_normalize_text(proposed_restart_mode, default='unknown')}",
            f"lane={_normalize_text(current_lane, default='unknown')}",
            f"bucket={_normalize_text(primary_failure_bucket, default='unknown')}",
            f"rcpt={_normalize_text(recipient_target, default='')}",
            f"rclass={_normalize_text(recipient_class, default='unknown')}",
        ]
    )


def build_approval_safety_contract_surface(
    *,
    run_id: str,
    objective_contract_payload: Mapping[str, Any] | None,
    approval_email_delivery_payload: Mapping[str, Any] | None,
    approval_delivery_handoff_payload: Mapping[str, Any] | None,
    approval_response_payload: Mapping[str, Any] | None,
    approved_restart_payload: Mapping[str, Any] | None,
    lane_stabilization_contract_payload: Mapping[str, Any] | None,
    failure_bucketing_hardening_payload: Mapping[str, Any] | None,
    approval_runtime_rules_payload: Mapping[str, Any] | None,
    run_state_payload: Mapping[str, Any] | None,
    contract_artifact_index_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    objective, objective_malformed = _coerce_mapping(objective_contract_payload)
    approval_email, approval_email_malformed = _coerce_mapping(approval_email_delivery_payload)
    handoff, handoff_malformed = _coerce_mapping(approval_delivery_handoff_payload)
    response, response_malformed = _coerce_mapping(approval_response_payload)
    approved_restart, approved_restart_malformed = _coerce_mapping(approved_restart_payload)
    lane, lane_malformed = _coerce_mapping(lane_stabilization_contract_payload)
    hard_bucket, hard_bucket_malformed = _coerce_mapping(failure_bucketing_hardening_payload)
    runtime_rules, runtime_rules_malformed = _coerce_mapping(approval_runtime_rules_payload)
    run_state, run_state_malformed = _coerce_mapping(run_state_payload)
    artifact_index, artifact_index_malformed = _coerce_mapping(contract_artifact_index_payload)
    _ = artifact_index

    malformed_inputs = any(
        (
            objective_malformed,
            approval_email_malformed,
            handoff_malformed,
            response_malformed,
            approved_restart_malformed,
            lane_malformed,
            hard_bucket_malformed,
            runtime_rules_malformed,
            run_state_malformed,
            artifact_index_malformed,
        )
    )

    objective_id = _normalize_text(objective.get("objective_id"), default="")
    approval_required = _normalize_bool(approval_email.get("approval_required"))
    approval_priority = _normalize_text(approval_email.get("approval_priority"), default="unknown")
    approval_email_status = _normalize_text(approval_email.get("approval_email_status"), default="insufficient_truth")
    handoff_status = _normalize_text(
        handoff.get("approval_delivery_handoff_status"),
        default="insufficient_truth",
    )
    delivery_outcome = _normalize_text(handoff.get("delivery_outcome"), default="unknown")
    approval_pending_human_response = _normalize_bool(handoff.get("approval_pending_human_response"))
    approval_response_status = _normalize_text(
        response.get("approval_response_status"),
        default="insufficient_truth",
    )
    approved_restart_status = _normalize_text(
        approved_restart.get("approved_restart_status"),
        default="insufficient_truth",
    )
    proposed_next_direction = _normalize_text(
        approval_email.get("proposed_next_direction"),
        default="unknown",
    )
    proposed_target_lane = _normalize_text(
        approval_email.get("proposed_target_lane"),
        default="unknown",
    )
    proposed_restart_mode = _normalize_text(
        approval_email.get("proposed_restart_mode"),
        default="unknown",
    )
    current_lane = _normalize_text(lane.get("current_lane"), default="unknown")
    primary_failure_bucket = _normalize_text(
        hard_bucket.get("primary_failure_bucket"),
        default="unknown",
    )
    bucket_severity = _normalize_text(hard_bucket.get("bucket_severity"), default="unknown")
    recipient_target = _normalize_text(approval_email.get("recipient_target"), default="")
    recipient_class = _normalize_text(approval_email.get("recipient_class"), default="unknown")

    response_received = _normalize_bool(response.get("response_received")) or bool(
        _normalize_text(response.get("response_command_normalized"), default="")
    )
    response_validity = _normalize_text(response.get("approval_response_validity"), default="insufficient_truth")
    response_is_valid = response_validity in {"valid", "partial"}
    response_cleared_pending = bool(
        response_received
        and response_is_valid
        and approval_response_status
        in {
            "response_accepted",
            "response_rejected",
            "response_held",
            "response_unsupported",
        }
    )

    approval_dedup_key = _build_approval_dedup_key(
        run_id=_normalize_text(run_id, default=""),
        objective_id=objective_id,
        approval_required=approval_required,
        proposed_next_direction=proposed_next_direction,
        proposed_restart_mode=proposed_restart_mode,
        current_lane=current_lane,
        primary_failure_bucket=primary_failure_bucket,
        recipient_target=recipient_target,
        recipient_class=recipient_class,
    )
    previous_dedup_key = _normalize_text(run_state.get("approval_last_dedup_key"), default="")

    prior_pending_count = _normalize_non_negative_int(
        run_state.get("approval_prior_pending_count")
    )
    prior_recent_delivery_count = _normalize_non_negative_int(
        run_state.get("approval_prior_recent_delivery_count")
    )
    same_request_class_count = _normalize_non_negative_int(
        run_state.get("approval_same_request_class_count")
    )

    if approval_pending_human_response and not response_cleared_pending and prior_pending_count == 0:
        prior_pending_count = 1
    if (
        delivery_outcome in {"sent", "draft_created", "queued_for_review"}
        and prior_recent_delivery_count == 0
    ):
        prior_recent_delivery_count = 1
    if same_request_class_count == 0:
        same_request_class_count = max(
            prior_pending_count + prior_recent_delivery_count,
            1 if approval_required else 0,
        )

    cooldown_seconds = _normalize_non_negative_int(
        run_state.get("approval_cooldown_seconds")
    )
    if cooldown_seconds == 0:
        cooldown_seconds = _normalize_non_negative_int(
            runtime_rules.get("approval_cooldown_seconds")
        )
    approval_cooldown_active = _normalize_bool(
        run_state.get("approval_cooldown_active")
    ) or bool(
        approval_required
        and cooldown_seconds > 0
        and prior_recent_delivery_count > 0
        and not response_cleared_pending
    )

    approval_duplicate_detected = bool(
        approval_required
        and (
            (previous_dedup_key and previous_dedup_key == approval_dedup_key)
            or prior_pending_count > 0
            or same_request_class_count > 1
        )
    )
    approval_pending_duplicate = bool(
        approval_duplicate_detected
        and approval_pending_human_response
        and not response_cleared_pending
    )

    approval_loop_suspected = _normalize_bool(
        run_state.get("approval_loop_suspected")
    ) or bool(
        approval_required
        and not response_cleared_pending
        and same_request_class_count >= 3
        and prior_recent_delivery_count >= 1
    )

    approval_redelivery_allowed = False
    approval_delivery_blocked_by_safety = False
    approval_delivery_deferred_by_safety = False
    approval_delivery_allowed_by_safety = False
    status = "insufficient_truth"
    validity = "valid"
    confidence = "medium"
    decision = "unknown"
    lead_reason = "unknown_safety_posture"

    insufficient_truth = bool(
        not objective_id
        or (approval_required and approval_email_status in {"", "insufficient_truth"})
        or (
            approval_required
            and proposed_next_direction == "unknown"
            and proposed_restart_mode == "unknown"
        )
    )

    if malformed_inputs:
        status = "insufficient_truth"
        validity = "malformed"
        confidence = "low"
        decision = "unknown"
        lead_reason = "malformed_safety_inputs"
    elif insufficient_truth:
        status = "insufficient_truth"
        validity = "insufficient_truth"
        confidence = "low"
        decision = "unknown"
        lead_reason = "insufficient_safety_truth"
    elif not approval_required:
        status = "not_applicable"
        validity = "valid"
        confidence = "high"
        decision = "unknown"
        lead_reason = "approval_not_required"
    elif approval_pending_duplicate:
        status = "duplicate_pending"
        validity = "valid"
        confidence = "high"
        decision = "block_until_response_or_clear"
        approval_delivery_blocked_by_safety = True
        lead_reason = "duplicate_pending_uncleared"
    elif approval_cooldown_active:
        status = "cooldown_active"
        validity = "valid"
        confidence = "high"
        decision = "defer_until_cooldown_expires"
        approval_delivery_deferred_by_safety = True
        lead_reason = "cooldown_window_active"
    elif approval_loop_suspected:
        status = "loop_suspected"
        validity = "partial"
        confidence = "medium"
        decision = "block_loop_suspected"
        approval_delivery_blocked_by_safety = True
        lead_reason = "loop_notification_churn_suspected"
    else:
        status = "safe_to_deliver"
        validity = "valid"
        confidence = "high"
        decision = "allow_delivery"
        approval_redelivery_allowed = True
        approval_delivery_allowed_by_safety = True
        lead_reason = "delivery_safe_to_send"

    if status == "safe_to_deliver":
        approval_delivery_allowed_by_safety = True
        approval_delivery_blocked_by_safety = False
        approval_delivery_deferred_by_safety = False
        approval_redelivery_allowed = True
    if status == "duplicate_pending":
        approval_duplicate_detected = True
        approval_pending_duplicate = True
        approval_delivery_blocked_by_safety = True
        approval_delivery_allowed_by_safety = False
        approval_redelivery_allowed = False
    if status == "cooldown_active":
        approval_cooldown_active = True
        approval_delivery_deferred_by_safety = True
        approval_delivery_allowed_by_safety = False
        approval_redelivery_allowed = False
    if status == "loop_suspected":
        approval_loop_suspected = True
        approval_delivery_blocked_by_safety = True
        approval_delivery_allowed_by_safety = False
        approval_redelivery_allowed = False

    reason_codes = _normalize_reason_codes(
        [
            lead_reason,
            "response_cleared_pending_duplicate"
            if response_cleared_pending and approval_duplicate_detected and not approval_pending_duplicate
            else "",
            "alias_deduplicated" if _normalize_bool(run_state.get("retention_alias_deduplicated")) else "",
        ]
    )

    last_delivery_timestamp = _normalize_text(
        run_state.get("approval_last_delivery_timestamp")
        or handoff.get("downstream_delivery_timestamp"),
        default="",
    )
    last_response_timestamp = _normalize_text(
        run_state.get("approval_last_response_timestamp")
        or response.get("response_received_timestamp"),
        default="",
    )

    supporting_refs = _normalize_supporting_refs(
        [
            "approval_email_delivery_contract.approval_email_status" if approval_email_status else "",
            "approval_delivery_handoff_contract.approval_delivery_handoff_status" if handoff_status else "",
            "approval_delivery_handoff_contract.delivery_outcome" if delivery_outcome else "",
            "approval_delivery_handoff_contract.approval_pending_human_response"
            if "approval_pending_human_response" in handoff
            else "",
            "approval_response_contract.approval_response_status" if approval_response_status else "",
            "approved_restart_contract.approved_restart_status" if approved_restart_status else "",
            "approval_email_delivery_contract.approval_required" if "approval_required" in approval_email else "",
            "approval_email_delivery_contract.approval_priority" if approval_priority else "",
            "approval_email_delivery_contract.proposed_next_direction"
            if proposed_next_direction
            else "",
            "approval_email_delivery_contract.proposed_target_lane"
            if proposed_target_lane
            else "",
            "approval_email_delivery_contract.proposed_restart_mode"
            if proposed_restart_mode
            else "",
            "lane_stabilization_contract.current_lane" if current_lane else "",
            "failure_bucketing_hardening_contract.primary_failure_bucket" if primary_failure_bucket else "",
            "failure_bucketing_hardening_contract.bucket_severity" if bucket_severity else "",
        ]
    )

    return {
        "schema_version": APPROVAL_SAFETY_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "approval_safety_status": _normalize_enum(
            status,
            allowed=APPROVAL_SAFETY_STATUSES,
            default="insufficient_truth",
        ),
        "approval_safety_validity": _normalize_enum(
            validity,
            allowed=APPROVAL_SAFETY_VALIDITIES,
            default="insufficient_truth",
        ),
        "approval_safety_confidence": _normalize_enum(
            confidence,
            allowed=APPROVAL_SAFETY_CONFIDENCE_LEVELS,
            default="low",
        ),
        "approval_dedup_key": approval_dedup_key,
        "approval_duplicate_detected": bool(approval_duplicate_detected),
        "approval_pending_duplicate": bool(approval_pending_duplicate),
        "approval_cooldown_active": bool(approval_cooldown_active),
        "approval_cooldown_seconds": _normalize_non_negative_int(cooldown_seconds),
        "approval_redelivery_allowed": bool(approval_redelivery_allowed),
        "approval_safety_decision": _normalize_enum(
            decision,
            allowed=APPROVAL_SAFETY_DECISIONS,
            default="unknown",
        ),
        "approval_delivery_blocked_by_safety": bool(approval_delivery_blocked_by_safety),
        "approval_delivery_deferred_by_safety": bool(approval_delivery_deferred_by_safety),
        "approval_delivery_allowed_by_safety": bool(approval_delivery_allowed_by_safety),
        "approval_loop_suspected": bool(approval_loop_suspected),
        "prior_pending_count": _normalize_non_negative_int(prior_pending_count),
        "prior_recent_delivery_count": _normalize_non_negative_int(prior_recent_delivery_count),
        "same_request_class_count": _normalize_non_negative_int(same_request_class_count),
        "last_delivery_timestamp": last_delivery_timestamp,
        "last_response_timestamp": last_response_timestamp,
        "approval_safety_primary_reason": reason_codes[0],
        "approval_safety_reason_codes": reason_codes,
        "approval_email_status": approval_email_status or "insufficient_truth",
        "approval_delivery_handoff_status": handoff_status or "insufficient_truth",
        "delivery_outcome": delivery_outcome or "unknown",
        "approval_pending_human_response": bool(approval_pending_human_response),
        "approval_response_status": approval_response_status or "insufficient_truth",
        "approved_restart_status": approved_restart_status or "insufficient_truth",
        "approval_required": bool(approval_required),
        "approval_priority": approval_priority,
        "proposed_next_direction": proposed_next_direction,
        "proposed_target_lane": proposed_target_lane,
        "proposed_restart_mode": proposed_restart_mode,
        "current_lane": current_lane,
        "primary_failure_bucket": primary_failure_bucket,
        "bucket_severity": bucket_severity,
        "supporting_compact_truth_refs": supporting_refs,
        "next_safe_hint": _normalize_text(run_state.get("next_safe_action"), default=""),
        "closure_followup_hint": _normalize_text(
            run_state.get("closure_followup_hint"),
            default="",
        ),
        "retry_hint": _normalize_text(run_state.get("retry_hint"), default=""),
        "reentry_hint": _normalize_text(run_state.get("reentry_hint"), default=""),
    }


def build_approval_safety_run_state_summary_surface(
    approval_safety_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(approval_safety_payload or {})
    return {
        "approval_safety_present": bool(
            _normalize_text(payload.get("approval_safety_status"), default="")
        )
        or _normalize_bool(payload.get("approval_safety_present"))
    }


def build_approval_safety_summary_surface(
    approval_safety_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(approval_safety_payload or {})
    return {
        "approval_safety_status": _normalize_enum(
            payload.get("approval_safety_status"),
            allowed=APPROVAL_SAFETY_STATUSES,
            default="insufficient_truth",
        ),
        "approval_safety_validity": _normalize_enum(
            payload.get("approval_safety_validity"),
            allowed=APPROVAL_SAFETY_VALIDITIES,
            default="insufficient_truth",
        ),
        "approval_safety_confidence": _normalize_enum(
            payload.get("approval_safety_confidence"),
            allowed=APPROVAL_SAFETY_CONFIDENCE_LEVELS,
            default="low",
        ),
        "approval_safety_decision": _normalize_enum(
            payload.get("approval_safety_decision"),
            allowed=APPROVAL_SAFETY_DECISIONS,
            default="unknown",
        ),
        "approval_duplicate_detected": _normalize_bool(
            payload.get("approval_duplicate_detected")
        ),
        "approval_pending_duplicate": _normalize_bool(
            payload.get("approval_pending_duplicate")
        ),
        "approval_cooldown_active": _normalize_bool(
            payload.get("approval_cooldown_active")
        ),
        "approval_loop_suspected": _normalize_bool(
            payload.get("approval_loop_suspected")
        ),
        "approval_delivery_allowed_by_safety": _normalize_bool(
            payload.get("approval_delivery_allowed_by_safety")
        ),
        "approval_safety_primary_reason": _normalize_text(
            payload.get("approval_safety_primary_reason"),
            default="no_reason",
        )
        if _normalize_text(payload.get("approval_safety_primary_reason"), default="")
        in APPROVAL_SAFETY_REASON_CODES
        else "no_reason",
    }

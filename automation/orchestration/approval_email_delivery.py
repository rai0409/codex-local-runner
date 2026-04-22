from __future__ import annotations

import importlib
import os
from typing import Any
from typing import Callable
from typing import Mapping

from automation.orchestration.approval_direction_rules import APPROVAL_PRIORITIES
from automation.orchestration.approval_direction_rules import PROPOSED_ACTION_CLASSES
from automation.orchestration.approval_direction_rules import PROPOSED_NEXT_DIRECTIONS
from automation.orchestration.approval_direction_rules import PROPOSED_RESTART_MODES
from automation.orchestration.approval_direction_rules import derive_direction_posture
from automation.orchestration.approval_email_templates import APPROVAL_OPTION_SETS
from automation.orchestration.approval_email_templates import derive_approval_option_set
from automation.orchestration.approval_email_templates import render_approval_body_compact
from automation.orchestration.approval_email_templates import render_approval_subject
from automation.orchestration.approval_email_templates import render_approval_summary_compact
from automation.orchestration.approval_reply_commands import ALLOWED_REPLY_COMMANDS
from automation.orchestration.approval_reply_commands import allowed_reply_commands_for_direction


APPROVAL_EMAIL_DELIVERY_SCHEMA_VERSION = "v1"

APPROVAL_EMAIL_STATUSES = {
    "not_required",
    "required",
    "delivered_for_review",
    "delivery_blocked",
    "insufficient_truth",
}

APPROVAL_EMAIL_VALIDITIES = {
    "valid",
    "partial",
    "malformed",
    "insufficient_truth",
}

APPROVAL_EMAIL_CONFIDENCE_LEVELS = {
    "high",
    "medium",
    "low",
}

APPROVAL_REASON_CLASSES = {
    "manual_only",
    "restart_blocked",
    "restart_hold",
    "lane_change_high_risk",
    "bucket_high_risk",
    "integrity_degraded",
    "closure_decision_required",
    "unknown",
}

APPROVAL_DECISION_SCOPES = {
    "restart_only",
    "direction_only",
    "restart_and_direction",
    "manual_review_only",
    "unknown",
}

RECIPIENT_CLASSES = {
    "self",
    "operator",
    "reviewer",
    "approver",
    "maintainer",
    "admin",
    "unknown",
}

DELIVERY_MODES = {
    "gmail_draft",
    "gmail_send",
    "review_queue_only",
    "not_applicable",
    "unknown",
}

DELIVERY_OUTCOMES = {
    "not_attempted",
    "draft_created",
    "sent",
    "skipped",
    "blocked",
    "failed",
    "unknown",
}

APPROVAL_EMAIL_REASON_CODES = {
    "malformed_approval_email_inputs",
    "insufficient_approval_email_truth",
    "manual_only_terminal_posture",
    "restart_blocked_by_fleet_safety",
    "high_repeat_or_freeze_posture",
    "high_risk_lane_change",
    "high_risk_failure_bucket",
    "retention_integrity_degraded",
    "closure_decision_requires_review",
    "recommended_human_review",
    "approval_not_required",
    "unknown_posture",
    "gmail_draft_mode",
    "gmail_send_mode",
    "review_queue_only_mode",
    "delivery_sent",
    "delivery_draft_created",
    "delivery_skipped",
    "delivery_blocked",
    "delivery_failed",
    "alias_deduplicated",
    "no_reason",
}

APPROVAL_EMAIL_REASON_ORDER = (
    "malformed_approval_email_inputs",
    "insufficient_approval_email_truth",
    "manual_only_terminal_posture",
    "restart_blocked_by_fleet_safety",
    "high_repeat_or_freeze_posture",
    "high_risk_lane_change",
    "high_risk_failure_bucket",
    "retention_integrity_degraded",
    "closure_decision_requires_review",
    "recommended_human_review",
    "approval_not_required",
    "unknown_posture",
    "gmail_draft_mode",
    "gmail_send_mode",
    "review_queue_only_mode",
    "delivery_sent",
    "delivery_draft_created",
    "delivery_skipped",
    "delivery_blocked",
    "delivery_failed",
    "alias_deduplicated",
    "no_reason",
)

_ALLOWED_SUPPORTING_REFS = (
    "fleet_safety_control_contract.fleet_safety_status",
    "fleet_safety_control_contract.fleet_safety_decision",
    "fleet_safety_control_contract.fleet_restart_decision",
    "failure_bucketing_hardening_contract.primary_failure_bucket",
    "failure_bucketing_hardening_contract.bucket_severity",
    "failure_bucketing_hardening_contract.bucket_terminality_class",
    "lane_stabilization_contract.lane_status",
    "lane_stabilization_contract.current_lane",
    "endgame_closure_contract.final_closure_class",
    "loop_hardening_contract.loop_hardening_status",
    "artifact_retention_contract.artifact_retention_status",
    "artifact_retention_contract.retention_reference_consistent",
)

APPROVAL_EMAIL_DELIVERY_RUN_STATE_SUMMARY_SAFE_FIELDS = (
    "approval_email_delivery_present",
)

APPROVAL_EMAIL_DELIVERY_SUMMARY_SAFE_FIELDS = (
    "approval_email_status",
    "approval_email_validity",
    "approval_email_confidence",
    "approval_required",
    "approval_priority",
    "proposed_next_direction",
    "delivery_mode",
    "delivery_outcome",
    "approval_email_primary_reason",
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
    normalized = [value for value in _ordered_unique(values) if value in APPROVAL_EMAIL_REASON_CODES]
    ordered: list[str] = []
    for code in APPROVAL_EMAIL_REASON_ORDER:
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


def _load_delivery_adapter_from_env() -> Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None:
    target = _normalize_text(os.getenv("INTERNAL_AUTOMATION_APPROVAL_EMAIL_ADAPTER"), default="")
    if not target or ":" not in target:
        return None
    module_name, function_name = target.split(":", 1)
    module_name = module_name.strip()
    function_name = function_name.strip()
    if not module_name or not function_name:
        return None
    try:
        module = importlib.import_module(module_name)
        candidate = getattr(module, function_name)
    except Exception:
        return None
    if callable(candidate):
        return candidate
    return None


def _invoke_delivery_adapter(
    *,
    adapter: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None,
    handoff_payload: Mapping[str, Any],
) -> dict[str, Any]:
    simulation = _normalize_text(os.getenv("INTERNAL_AUTOMATION_APPROVAL_EMAIL_SIMULATE"), default="")
    if simulation in DELIVERY_OUTCOMES:
        attempted = simulation in {"draft_created", "sent", "failed"}
        return {
            "delivery_attempted": attempted,
            "delivery_outcome": simulation,
            "delivery_metadata": {"adapter": "simulation"},
        }

    resolved_adapter = adapter or _load_delivery_adapter_from_env()
    if resolved_adapter is None:
        return {
            "delivery_attempted": False,
            "delivery_outcome": "blocked",
            "delivery_metadata": {
                "adapter": "internal_automation",
                "reason": "adapter_unavailable",
            },
        }

    try:
        raw = resolved_adapter(dict(handoff_payload))
    except Exception as exc:
        return {
            "delivery_attempted": True,
            "delivery_outcome": "failed",
            "delivery_metadata": {
                "adapter": "internal_automation",
                "reason": _normalize_text(str(exc), default="adapter_error"),
            },
        }

    payload = dict(raw) if isinstance(raw, Mapping) else {}
    outcome = _normalize_enum(
        payload.get("delivery_outcome"),
        allowed=DELIVERY_OUTCOMES,
        default="unknown",
    )
    attempted = _normalize_bool(payload.get("delivery_attempted"))
    if outcome in {"draft_created", "sent", "failed"}:
        attempted = True
    if outcome in {"blocked", "skipped", "not_attempted"} and "delivery_attempted" not in payload:
        attempted = False

    return {
        "delivery_attempted": attempted,
        "delivery_outcome": outcome,
        "delivery_metadata": {
            "adapter": "internal_automation",
            "adapter_status": _normalize_text(payload.get("status"), default=""),
            "adapter_reference": _normalize_text(payload.get("reference"), default=""),
            "adapter_message": _normalize_text(payload.get("message"), default=""),
        },
    }


def build_approval_email_delivery_contract_surface(
    *,
    run_id: str,
    objective_contract_payload: Mapping[str, Any] | None,
    fleet_safety_control_payload: Mapping[str, Any] | None,
    failure_bucketing_hardening_payload: Mapping[str, Any] | None,
    lane_stabilization_contract_payload: Mapping[str, Any] | None,
    loop_hardening_contract_payload: Mapping[str, Any] | None,
    endgame_closure_contract_payload: Mapping[str, Any] | None,
    retry_reentry_loop_contract_payload: Mapping[str, Any] | None,
    artifact_retention_contract_payload: Mapping[str, Any] | None,
    run_state_payload: Mapping[str, Any] | None,
    contract_artifact_index_payload: Mapping[str, Any] | None = None,
    delivery_adapter: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
) -> dict[str, Any]:
    objective, objective_malformed = _coerce_mapping(objective_contract_payload)
    fleet, fleet_malformed = _coerce_mapping(fleet_safety_control_payload)
    hard_bucket, hard_bucket_malformed = _coerce_mapping(failure_bucketing_hardening_payload)
    lane, lane_malformed = _coerce_mapping(lane_stabilization_contract_payload)
    loop_hardening, loop_hardening_malformed = _coerce_mapping(loop_hardening_contract_payload)
    endgame, endgame_malformed = _coerce_mapping(endgame_closure_contract_payload)
    retry_loop, retry_loop_malformed = _coerce_mapping(retry_reentry_loop_contract_payload)
    retention, retention_malformed = _coerce_mapping(artifact_retention_contract_payload)
    run_state, run_state_malformed = _coerce_mapping(run_state_payload)
    artifact_index, artifact_index_malformed = _coerce_mapping(contract_artifact_index_payload)

    malformed_inputs = any(
        (
            objective_malformed,
            fleet_malformed,
            hard_bucket_malformed,
            lane_malformed,
            loop_hardening_malformed,
            endgame_malformed,
            retry_loop_malformed,
            retention_malformed,
            run_state_malformed,
            artifact_index_malformed,
        )
    )

    objective_id = _normalize_text(
        objective.get("objective_id") or run_state.get("objective_id"),
        default="",
    )

    fleet_safety_status = _normalize_text(fleet.get("fleet_safety_status"), default="")
    fleet_safety_decision = _normalize_text(fleet.get("fleet_safety_decision"), default="")
    fleet_restart_decision = _normalize_text(fleet.get("fleet_restart_decision"), default="")
    primary_failure_bucket = _normalize_text(hard_bucket.get("primary_failure_bucket"), default="")
    bucket_severity = _normalize_text(hard_bucket.get("bucket_severity"), default="unknown")
    bucket_terminality_class = _normalize_text(
        hard_bucket.get("bucket_terminality_class"),
        default="unknown",
    )
    lane_status = _normalize_text(lane.get("lane_status"), default="")
    current_lane = _normalize_text(lane.get("current_lane"), default="")
    final_closure_class = _normalize_text(endgame.get("final_closure_class"), default="")
    loop_hardening_status = _normalize_text(
        loop_hardening.get("loop_hardening_status"),
        default="",
    )
    retry_loop_decision = _normalize_text(retry_loop.get("retry_loop_decision"), default="")
    artifact_retention_status = _normalize_text(
        retention.get("artifact_retention_status"),
        default="",
    )
    retention_reference_consistent = _normalize_bool(
        retention.get("retention_reference_consistent")
    )

    manual_only_terminal = any(
        (
            final_closure_class == "manual_closure_only",
            primary_failure_bucket == "manual_only",
            fleet_restart_decision == "manual_only",
            fleet_safety_decision == "escalate_manual",
        )
    )

    restart_blocked = any(
        (
            fleet_restart_decision in {"restart_blocked", "manual_only"},
            _normalize_bool(fleet.get("fleet_restart_blocked")),
        )
    )

    repeat_or_freeze_high_risk = any(
        (
            loop_hardening_status in {"freeze", "stop_required"},
            _normalize_bool(loop_hardening.get("same_failure_stop_required")),
            _normalize_bool(loop_hardening.get("no_progress_stop_required")),
            _normalize_bool(loop_hardening.get("oscillation_detected")),
            primary_failure_bucket
            in {"retry_exhausted", "same_failure_exhausted", "no_progress", "oscillation"},
        )
    )

    lane_change_high_risk = any(
        (
            lane_status in {"lane_mismatch", "lane_transition_blocked", "lane_stop_required"},
            _normalize_bool(lane.get("lane_mismatch_detected")),
        )
    )

    bucket_high_risk = any(
        (
            bucket_severity in {"high", "critical"},
            primary_failure_bucket in {
                "verification_failure",
                "execution_failure",
                "retry_exhausted",
                "same_failure_exhausted",
                "manual_only",
                "closure_unresolved",
                "terminal_non_success",
            },
        )
    )

    integrity_degraded = any(
        (
            artifact_retention_status in {"partial", "degraded", "insufficient_truth"},
            not retention_reference_consistent,
            _normalize_text(retention.get("artifact_retention_validity"), default="")
            in {"partial", "malformed", "insufficient_truth"},
        )
    )

    closure_decision_required = final_closure_class in {
        "completed_but_not_closed",
        "rollback_complete_but_not_closed",
        "external_truth_pending",
        "closure_unresolved",
    }

    recommended_human_review = any(
        (
            fleet_safety_status in {"hold", "degraded"},
            fleet_safety_decision == "hold_for_review",
            _normalize_text(bucket_terminality_class, default="") in {"terminal", "manual_only"},
        )
    )

    insufficient_truth = any(
        (
            fleet_safety_status in {"", "insufficient_truth"},
            primary_failure_bucket in {"", "truth_missing", "unknown"},
            lane_status in {"", "insufficient_truth"},
        )
    )

    lead_reason = "unknown_posture"
    approval_required = True
    status = "required"
    validity = "valid"
    confidence = "medium"

    if malformed_inputs:
        lead_reason = "malformed_approval_email_inputs"
        status = "insufficient_truth"
        validity = "malformed"
        confidence = "low"
    elif insufficient_truth:
        lead_reason = "insufficient_approval_email_truth"
        status = "insufficient_truth"
        validity = "insufficient_truth"
        confidence = "low"
    elif manual_only_terminal:
        lead_reason = "manual_only_terminal_posture"
        status = "required"
        validity = "valid"
        confidence = "high"
    elif restart_blocked:
        lead_reason = "restart_blocked_by_fleet_safety"
        status = "required"
        validity = "valid"
        confidence = "high"
    elif repeat_or_freeze_high_risk:
        lead_reason = "high_repeat_or_freeze_posture"
        status = "required"
        validity = "valid"
        confidence = "high"
    elif lane_change_high_risk:
        lead_reason = "high_risk_lane_change"
        status = "required"
        validity = "valid"
        confidence = "medium"
    elif bucket_high_risk:
        lead_reason = "high_risk_failure_bucket"
        status = "required"
        validity = "valid"
        confidence = "medium"
    elif integrity_degraded:
        lead_reason = "retention_integrity_degraded"
        status = "required"
        validity = "partial"
        confidence = "medium"
    elif closure_decision_required:
        lead_reason = "closure_decision_requires_review"
        status = "required"
        validity = "valid"
        confidence = "medium"
    elif recommended_human_review:
        lead_reason = "recommended_human_review"
        status = "required"
        validity = "partial"
        confidence = "medium"
    elif fleet_safety_status == "allow" and fleet_restart_decision == "restart_allowed":
        lead_reason = "approval_not_required"
        approval_required = False
        status = "not_required"
        validity = "valid"
        confidence = "high"
    else:
        lead_reason = "unknown_posture"
        status = "required"
        validity = "partial"
        confidence = "low"

    restart_hold = fleet_restart_decision == "restart_hold" or fleet_safety_status == "hold"
    direction_posture = derive_direction_posture(
        lead_reason=lead_reason,
        primary_failure_bucket=primary_failure_bucket,
        final_closure_class=final_closure_class,
        retry_loop_decision=retry_loop_decision,
        current_lane=current_lane,
        approval_required=approval_required,
        manual_only_terminal=manual_only_terminal,
        restart_blocked=restart_blocked,
        restart_hold=restart_hold,
        bucket_severity=bucket_severity,
        fleet_safety_status=fleet_safety_status,
    )
    approval_priority = _normalize_enum(
        direction_posture.get("approval_priority"),
        allowed=APPROVAL_PRIORITIES,
        default="unknown",
    )
    proposed_next_direction = _normalize_enum(
        direction_posture.get("proposed_next_direction"),
        allowed=PROPOSED_NEXT_DIRECTIONS,
        default="unknown",
    )
    proposed_target_lane = _normalize_text(
        direction_posture.get("proposed_target_lane"),
        default="unknown",
    )
    proposed_restart_mode = _normalize_enum(
        direction_posture.get("proposed_restart_mode"),
        allowed=PROPOSED_RESTART_MODES,
        default="unknown",
    )
    proposed_action_class = _normalize_enum(
        direction_posture.get("proposed_action_class"),
        allowed=PROPOSED_ACTION_CLASSES,
        default="unknown",
    )

    if lead_reason == "manual_only_terminal_posture":
        approval_reason_class = "manual_only"
    elif lead_reason == "restart_blocked_by_fleet_safety":
        approval_reason_class = "restart_blocked"
    elif restart_hold:
        approval_reason_class = "restart_hold"
    elif lead_reason == "high_risk_lane_change":
        approval_reason_class = "lane_change_high_risk"
    elif lead_reason == "high_risk_failure_bucket":
        approval_reason_class = "bucket_high_risk"
    elif lead_reason == "retention_integrity_degraded":
        approval_reason_class = "integrity_degraded"
    elif lead_reason == "closure_decision_requires_review":
        approval_reason_class = "closure_decision_required"
    else:
        approval_reason_class = "unknown"

    approval_reason_class = _normalize_enum(
        approval_reason_class,
        allowed=APPROVAL_REASON_CLASSES,
        default="unknown",
    )

    if not approval_required:
        approval_decision_scope = "unknown"
    elif approval_reason_class == "manual_only":
        approval_decision_scope = "manual_review_only"
    elif restart_blocked or restart_hold:
        approval_decision_scope = "restart_and_direction"
    elif proposed_next_direction in {
        "same_lane_retry",
        "repair_retry",
        "truth_gathering",
        "replan_preparation",
    }:
        approval_decision_scope = "restart_only"
    elif proposed_next_direction == "closure_followup":
        approval_decision_scope = "direction_only"
    else:
        approval_decision_scope = "unknown"

    approval_decision_scope = _normalize_enum(
        approval_decision_scope,
        allowed=APPROVAL_DECISION_SCOPES,
        default="unknown",
    )

    if manual_only_terminal:
        recipient_class = "approver"
    elif restart_blocked:
        recipient_class = "reviewer"
    elif integrity_degraded:
        recipient_class = "operator"
    else:
        recipient_class = "self"
    recipient_class = _normalize_enum(recipient_class, allowed=RECIPIENT_CLASSES, default="unknown")

    recipient_target = _normalize_text(
        run_state.get("approval_email_recipient_target")
        or run_state.get("operator_contact")
        or f"{recipient_class}:default",
        default="",
    )

    preferred_mode = _normalize_text(
        run_state.get("approval_email_delivery_mode")
        or os.getenv("APPROVAL_EMAIL_DELIVERY_MODE"),
        default="",
    )

    if not approval_required:
        delivery_mode = "not_applicable"
    elif preferred_mode in {"gmail_draft", "gmail_send", "review_queue_only"}:
        delivery_mode = preferred_mode
    else:
        delivery_mode = "gmail_send"

    delivery_mode = _normalize_enum(delivery_mode, allowed=DELIVERY_MODES, default="unknown")

    draft_required = delivery_mode == "gmail_draft"
    send_allowed = delivery_mode == "gmail_send"

    allowed_reply_commands = allowed_reply_commands_for_direction(
        proposed_next_direction
    )
    approval_option_set = _normalize_enum(
        derive_approval_option_set(
            proposed_direction=proposed_next_direction,
            restart_blocked=restart_blocked,
            restart_hold=restart_hold,
            manual_only_terminal=manual_only_terminal,
        ),
        allowed=APPROVAL_OPTION_SETS,
        default="unknown",
    )

    approval_subject = (
        render_approval_subject(
            priority=approval_priority,
            run_id=_normalize_text(run_id, default=""),
            primary_failure_bucket=primary_failure_bucket or "unknown",
            proposed_next_direction=proposed_next_direction,
        )
        if approval_required
        else ""
    )

    approval_summary_compact = (
        render_approval_summary_compact(
            primary_reason=lead_reason,
            proposed_direction=proposed_next_direction,
            restart_mode=proposed_restart_mode,
            priority=approval_priority,
        )
        if approval_required
        else ""
    )

    approval_body_compact = (
        render_approval_body_compact(
            run_id=_normalize_text(run_id, default=""),
            fleet_safety_status=fleet_safety_status or "unknown",
            primary_reason=lead_reason,
            proposed_direction=proposed_next_direction,
            restart_mode=proposed_restart_mode,
            allowed_reply_commands=allowed_reply_commands,
            hints={
                "next_safe_hint": run_state.get("next_safe_action"),
                "closure_followup_hint": run_state.get("closure_followup_hint"),
                "retry_hint": run_state.get("retry_hint"),
                "reentry_hint": run_state.get("reentry_hint"),
            },
        )
        if approval_required
        else ""
    )

    delivery_attempted = False
    delivery_outcome = "not_attempted"
    delivery_metadata: dict[str, Any] = {}

    if approval_required:
        if delivery_mode == "review_queue_only":
            delivery_attempted = False
            delivery_outcome = "skipped"
            delivery_metadata = {"reason": "review_queue_only"}
        elif delivery_mode in {"gmail_draft", "gmail_send"}:
            handoff_payload = {
                "run_id": _normalize_text(run_id, default=""),
                "objective_id": objective_id,
                "recipient_class": recipient_class,
                "recipient_target": recipient_target,
                "delivery_mode": delivery_mode,
                "approval_subject": approval_subject,
                "approval_body_compact": approval_body_compact,
                "approval_option_set": approval_option_set,
                "allowed_reply_commands": list(allowed_reply_commands),
                "approval_summary_compact": approval_summary_compact,
                "proposed_next_direction": proposed_next_direction,
                "proposed_restart_mode": proposed_restart_mode,
                "proposed_action_class": proposed_action_class,
            }
            handoff_result = _invoke_delivery_adapter(
                adapter=delivery_adapter,
                handoff_payload=handoff_payload,
            )
            delivery_attempted = _normalize_bool(handoff_result.get("delivery_attempted"))
            delivery_outcome = _normalize_enum(
                handoff_result.get("delivery_outcome"),
                allowed=DELIVERY_OUTCOMES,
                default="unknown",
            )
            delivery_metadata = dict(handoff_result.get("delivery_metadata") or {})
        else:
            delivery_attempted = False
            delivery_outcome = "blocked"
            delivery_metadata = {"reason": "unsupported_delivery_mode"}

    if not approval_required:
        status = "not_required"
    elif status not in {"insufficient_truth"}:
        if delivery_outcome in {"sent", "draft_created"}:
            status = "delivered_for_review"
        elif delivery_outcome in {"blocked", "failed"}:
            status = "delivery_blocked"
        else:
            status = "required"

    restart_blocked_pending_approval = bool(
        approval_required and restart_blocked and proposed_next_direction != "stop_no_restart"
    )
    restart_held_pending_approval = bool(
        approval_required and restart_hold and proposed_next_direction != "stop_no_restart"
    )
    approval_can_clear_restart_block = bool(
        approval_required
        and proposed_next_direction != "stop_no_restart"
        and restart_held_pending_approval
    )

    if proposed_next_direction == "stop_no_restart":
        restart_blocked_pending_approval = False
        restart_held_pending_approval = False
        approval_can_clear_restart_block = False

    if delivery_mode == "gmail_draft":
        draft_required = True
    if delivery_mode == "gmail_send":
        send_allowed = True

    alias_deduplicated = _normalize_bool(retention.get("retention_alias_deduplicated"))

    reason_codes = _normalize_reason_codes(
        [
            lead_reason,
            "gmail_draft_mode" if delivery_mode == "gmail_draft" else "",
            "gmail_send_mode" if delivery_mode == "gmail_send" else "",
            "review_queue_only_mode" if delivery_mode == "review_queue_only" else "",
            "delivery_sent" if delivery_outcome == "sent" else "",
            "delivery_draft_created" if delivery_outcome == "draft_created" else "",
            "delivery_skipped" if delivery_outcome == "skipped" else "",
            "delivery_blocked" if delivery_outcome == "blocked" else "",
            "delivery_failed" if delivery_outcome == "failed" else "",
            "alias_deduplicated" if alias_deduplicated else "",
        ]
    )
    if not reason_codes:
        reason_codes = ["no_reason"]

    supporting_refs = _normalize_supporting_refs(
        [
            "fleet_safety_control_contract.fleet_safety_status" if fleet_safety_status else "",
            "fleet_safety_control_contract.fleet_safety_decision" if fleet_safety_decision else "",
            "fleet_safety_control_contract.fleet_restart_decision" if fleet_restart_decision else "",
            "failure_bucketing_hardening_contract.primary_failure_bucket"
            if primary_failure_bucket
            else "",
            "failure_bucketing_hardening_contract.bucket_severity" if bucket_severity else "",
            "failure_bucketing_hardening_contract.bucket_terminality_class"
            if bucket_terminality_class
            else "",
            "lane_stabilization_contract.lane_status" if lane_status else "",
            "lane_stabilization_contract.current_lane" if current_lane else "",
            "endgame_closure_contract.final_closure_class" if final_closure_class else "",
            "loop_hardening_contract.loop_hardening_status" if loop_hardening_status else "",
            "artifact_retention_contract.artifact_retention_status"
            if artifact_retention_status
            else "",
            "artifact_retention_contract.retention_reference_consistent"
            if "retention_reference_consistent" in retention
            else "",
        ]
    )

    return {
        "schema_version": APPROVAL_EMAIL_DELIVERY_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "approval_email_status": _normalize_enum(
            status,
            allowed=APPROVAL_EMAIL_STATUSES,
            default="insufficient_truth",
        ),
        "approval_email_validity": _normalize_enum(
            validity,
            allowed=APPROVAL_EMAIL_VALIDITIES,
            default="insufficient_truth",
        ),
        "approval_email_confidence": _normalize_enum(
            confidence,
            allowed=APPROVAL_EMAIL_CONFIDENCE_LEVELS,
            default="low",
        ),
        "approval_required": bool(approval_required),
        "approval_priority": _normalize_enum(
            approval_priority,
            allowed=APPROVAL_PRIORITIES,
            default="unknown",
        ),
        "approval_reason_class": approval_reason_class,
        "approval_decision_scope": _normalize_enum(
            approval_decision_scope,
            allowed=APPROVAL_DECISION_SCOPES,
            default="unknown",
        ),
        "proposed_next_direction": proposed_next_direction,
        "proposed_target_lane": proposed_target_lane,
        "proposed_restart_mode": proposed_restart_mode,
        "proposed_action_class": proposed_action_class,
        "recipient_class": recipient_class,
        "recipient_target": recipient_target,
        "delivery_mode": _normalize_enum(
            delivery_mode,
            allowed=DELIVERY_MODES,
            default="unknown",
        ),
        "draft_required": bool(draft_required),
        "send_allowed": bool(send_allowed),
        "delivery_attempted": bool(delivery_attempted),
        "delivery_outcome": _normalize_enum(
            delivery_outcome,
            allowed=DELIVERY_OUTCOMES,
            default="unknown",
        ),
        "approval_subject": approval_subject,
        "approval_body_compact": approval_body_compact,
        "approval_option_set": _normalize_enum(
            approval_option_set,
            allowed=APPROVAL_OPTION_SETS,
            default="unknown",
        ),
        "allowed_reply_commands": [command for command in allowed_reply_commands if command in set(ALLOWED_REPLY_COMMANDS)],
        "approval_summary_compact": approval_summary_compact,
        "restart_blocked_pending_approval": bool(restart_blocked_pending_approval),
        "restart_held_pending_approval": bool(restart_held_pending_approval),
        "approval_can_clear_restart_block": bool(approval_can_clear_restart_block),
        "approval_email_primary_reason": reason_codes[0],
        "approval_email_reason_codes": reason_codes,
        "fleet_safety_status": fleet_safety_status or "insufficient_truth",
        "fleet_safety_decision": fleet_safety_decision or "unknown",
        "fleet_restart_decision": fleet_restart_decision or "unknown",
        "primary_failure_bucket": primary_failure_bucket or "unknown",
        "bucket_severity": bucket_severity or "unknown",
        "bucket_terminality_class": bucket_terminality_class or "unknown",
        "lane_status": lane_status or "unknown",
        "current_lane": current_lane or "unknown",
        "final_closure_class": final_closure_class or "unknown",
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
        "delivery_metadata": delivery_metadata,
    }


def build_approval_email_delivery_run_state_summary_surface(
    approval_email_delivery_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(approval_email_delivery_payload or {})
    return {
        "approval_email_delivery_present": bool(
            _normalize_text(payload.get("approval_email_status"), default="")
        )
        or _normalize_bool(payload.get("approval_email_delivery_present"))
    }


def build_approval_email_delivery_summary_surface(
    approval_email_delivery_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(approval_email_delivery_payload or {})
    return {
        "approval_email_status": _normalize_enum(
            payload.get("approval_email_status"),
            allowed=APPROVAL_EMAIL_STATUSES,
            default="insufficient_truth",
        ),
        "approval_email_validity": _normalize_enum(
            payload.get("approval_email_validity"),
            allowed=APPROVAL_EMAIL_VALIDITIES,
            default="insufficient_truth",
        ),
        "approval_email_confidence": _normalize_enum(
            payload.get("approval_email_confidence"),
            allowed=APPROVAL_EMAIL_CONFIDENCE_LEVELS,
            default="low",
        ),
        "approval_required": _normalize_bool(payload.get("approval_required")),
        "approval_priority": _normalize_enum(
            payload.get("approval_priority"),
            allowed=APPROVAL_PRIORITIES,
            default="unknown",
        ),
        "proposed_next_direction": _normalize_enum(
            payload.get("proposed_next_direction"),
            allowed=PROPOSED_NEXT_DIRECTIONS,
            default="unknown",
        ),
        "delivery_mode": _normalize_enum(
            payload.get("delivery_mode"),
            allowed=DELIVERY_MODES,
            default="unknown",
        ),
        "delivery_outcome": _normalize_enum(
            payload.get("delivery_outcome"),
            allowed=DELIVERY_OUTCOMES,
            default="unknown",
        ),
        "approval_email_primary_reason": _normalize_text(
            payload.get("approval_email_primary_reason"),
            default="no_reason",
        )
        if _normalize_text(payload.get("approval_email_primary_reason"), default="")
        in APPROVAL_EMAIL_REASON_CODES
        else "no_reason",
    }

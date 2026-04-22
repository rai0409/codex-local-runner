from __future__ import annotations

from typing import Any


APPROVAL_PRIORITIES = {
    "low",
    "medium",
    "high",
    "critical",
    "unknown",
}

PROPOSED_NEXT_DIRECTIONS = {
    "same_lane_retry",
    "repair_retry",
    "truth_gathering",
    "replan_preparation",
    "closure_followup",
    "manual_review_preparation",
    "stop_no_restart",
    "unknown",
}

PROPOSED_RESTART_MODES = {
    "blocked",
    "held",
    "approval_required_then_restart",
    "approval_required_then_manual",
    "not_applicable",
    "unknown",
}

PROPOSED_ACTION_CLASSES = {
    "review_and_restart",
    "review_and_replan",
    "review_and_recollect",
    "review_and_close_followup",
    "review_only",
    "stop_only",
    "unknown",
}


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _normalize_enum(value: Any, *, allowed: set[str], default: str) -> str:
    text = _normalize_text(value, default="")
    if text in allowed:
        return text
    return default


def derive_approval_priority(
    *,
    lead_reason: str,
    bucket_severity: str,
    fleet_safety_status: str,
) -> str:
    if lead_reason in {
        "manual_only_terminal_posture",
        "restart_blocked_by_fleet_safety",
        "high_repeat_or_freeze_posture",
    }:
        return "critical"
    if bucket_severity == "critical" or fleet_safety_status in {"freeze", "stop"}:
        return "high"
    if lead_reason in {
        "high_risk_lane_change",
        "high_risk_failure_bucket",
        "retention_integrity_degraded",
        "closure_decision_requires_review",
    }:
        return "high"
    if lead_reason == "recommended_human_review":
        return "medium"
    if lead_reason == "approval_not_required":
        return "low"
    return "unknown"


def derive_proposed_next_direction(
    *,
    lead_reason: str,
    primary_failure_bucket: str,
    final_closure_class: str,
    retry_loop_decision: str,
) -> str:
    if lead_reason == "manual_only_terminal_posture":
        return "manual_review_preparation"
    if primary_failure_bucket == "truth_missing" or retry_loop_decision == "recollect":
        return "truth_gathering"
    if primary_failure_bucket in {
        "retry_exhausted",
        "same_failure_exhausted",
        "no_progress",
        "oscillation",
    }:
        return "replan_preparation"
    if final_closure_class in {
        "completed_but_not_closed",
        "rollback_complete_but_not_closed",
        "external_truth_pending",
    }:
        return "closure_followup"
    if lead_reason == "restart_blocked_by_fleet_safety":
        return "stop_no_restart"
    if retry_loop_decision == "same_lane_retry":
        return "same_lane_retry"
    if retry_loop_decision == "repair_retry":
        return "repair_retry"
    if retry_loop_decision == "replan":
        return "replan_preparation"
    if retry_loop_decision == "escalate_manual":
        return "manual_review_preparation"
    return "unknown"


def derive_proposed_target_lane(*, proposed_direction: str, current_lane: str) -> str:
    direction = _normalize_text(proposed_direction, default="unknown")
    lane = _normalize_text(current_lane, default="")
    if direction in {"same_lane_retry", "repair_retry"}:
        return lane or "bounded_local_patch"
    if direction in {
        "truth_gathering",
        "replan_preparation",
        "closure_followup",
        "manual_review_preparation",
    }:
        return direction
    return "unknown"


def derive_proposed_restart_mode(
    *,
    approval_required: bool,
    proposed_direction: str,
    manual_only_terminal: bool,
    restart_blocked: bool,
    restart_hold: bool,
) -> str:
    if not approval_required:
        return "not_applicable"
    if proposed_direction == "stop_no_restart":
        return "blocked"
    if manual_only_terminal:
        return "approval_required_then_manual"
    if restart_blocked:
        return "blocked"
    if restart_hold:
        return "held"
    if proposed_direction in {
        "same_lane_retry",
        "repair_retry",
        "truth_gathering",
        "replan_preparation",
        "closure_followup",
    }:
        return "approval_required_then_restart"
    return "unknown"


def derive_proposed_action_class(proposed_direction: str) -> str:
    direction = _normalize_text(proposed_direction, default="unknown")
    if direction in {"same_lane_retry", "repair_retry"}:
        return "review_and_restart"
    if direction == "truth_gathering":
        return "review_and_recollect"
    if direction == "replan_preparation":
        return "review_and_replan"
    if direction == "closure_followup":
        return "review_and_close_followup"
    if direction == "manual_review_preparation":
        return "review_only"
    if direction == "stop_no_restart":
        return "stop_only"
    return "unknown"


def derive_direction_posture(
    *,
    lead_reason: str,
    primary_failure_bucket: str,
    final_closure_class: str,
    retry_loop_decision: str,
    current_lane: str,
    approval_required: bool,
    manual_only_terminal: bool,
    restart_blocked: bool,
    restart_hold: bool,
    bucket_severity: str,
    fleet_safety_status: str,
) -> dict[str, str]:
    proposed_next_direction = _normalize_enum(
        derive_proposed_next_direction(
            lead_reason=lead_reason,
            primary_failure_bucket=primary_failure_bucket,
            final_closure_class=final_closure_class,
            retry_loop_decision=retry_loop_decision,
        ),
        allowed=PROPOSED_NEXT_DIRECTIONS,
        default="unknown",
    )
    proposed_target_lane = _normalize_enum(
        derive_proposed_target_lane(
            proposed_direction=proposed_next_direction,
            current_lane=current_lane,
        ),
        allowed={
            "truth_gathering",
            "manual_review_preparation",
            "replan_preparation",
            "closure_followup",
            "bounded_github_update",
            "bounded_local_patch",
            "unknown",
        },
        default="unknown",
    )
    proposed_restart_mode = _normalize_enum(
        derive_proposed_restart_mode(
            approval_required=approval_required,
            proposed_direction=proposed_next_direction,
            manual_only_terminal=manual_only_terminal,
            restart_blocked=restart_blocked,
            restart_hold=restart_hold,
        ),
        allowed=PROPOSED_RESTART_MODES,
        default="unknown",
    )
    proposed_action_class = _normalize_enum(
        derive_proposed_action_class(proposed_next_direction),
        allowed=PROPOSED_ACTION_CLASSES,
        default="unknown",
    )
    approval_priority = _normalize_enum(
        derive_approval_priority(
            lead_reason=lead_reason,
            bucket_severity=bucket_severity,
            fleet_safety_status=fleet_safety_status,
        ),
        allowed=APPROVAL_PRIORITIES,
        default="unknown",
    )
    return {
        "proposed_next_direction": proposed_next_direction,
        "proposed_target_lane": proposed_target_lane,
        "proposed_restart_mode": proposed_restart_mode,
        "proposed_action_class": proposed_action_class,
        "approval_priority": approval_priority,
    }

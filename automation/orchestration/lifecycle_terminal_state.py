from __future__ import annotations

from typing import Any
from typing import Mapping

LIFECYCLE_SUMMARY_SAFE_FIELDS = (
    "lifecycle_closure_status",
    "lifecycle_safely_closed",
    "lifecycle_terminal",
    "lifecycle_resumable",
    "lifecycle_manual_required",
    "lifecycle_replan_required",
    "lifecycle_execution_complete_not_closed",
    "lifecycle_rollback_complete_not_closed",
    "lifecycle_blocked_reason",
    "lifecycle_primary_closure_issue",
    "lifecycle_stop_class",
)


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    normalized: list[str] = []
    for item in value:
        text = _normalize_text(item, default="")
        if text:
            normalized.append(text)
    return normalized


def _unique(values: list[str]) -> list[str]:
    unique_values: list[str] = []
    seen: set[str] = set()
    for item in values:
        if item not in seen:
            seen.add(item)
            unique_values.append(item)
    return unique_values


def _collect_blocked_reasons(payload: Mapping[str, Any]) -> list[str]:
    reasons = _unique(
        _normalize_string_list(payload.get("lifecycle_blocked_reasons"))
        + _normalize_string_list(payload.get("policy_blocked_reasons"))
        + _normalize_string_list(payload.get("loop_blocked_reasons"))
        + _normalize_string_list(payload.get("rollback_aftermath_blocked_reasons"))
        + _normalize_string_list(payload.get("remote_github_blocked_reasons"))
        + _normalize_string_list(payload.get("authority_validation_blocked_reasons"))
    )
    for key in (
        "lifecycle_blocked_reason",
        "policy_blocked_reason",
        "loop_blocked_reason",
        "rollback_aftermath_blocked_reason",
        "remote_github_blocked_reason",
        "authority_validation_blocked_reason",
    ):
        reason = _normalize_text(payload.get(key), default="")
        if reason and reason not in reasons:
            reasons.append(reason)
    return reasons


def build_lifecycle_terminal_state_surface(
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload or {})

    state = _normalize_text(payload.get("state"), default="")
    orchestration_state = _normalize_text(payload.get("orchestration_state"), default="")
    loop_state = _normalize_text(payload.get("loop_state"), default="")
    policy_status = _normalize_text(payload.get("policy_status"), default="")

    terminal = bool(payload.get("policy_terminal", False)) or bool(payload.get("terminal", False)) or (
        loop_state in {"terminal_success", "terminal_failure"}
    )
    resumable = bool(payload.get("policy_resume_allowed", False)) or bool(payload.get("resumable", False))
    replan_required = (
        bool(payload.get("policy_replan_required", False))
        or bool(payload.get("loop_replan_required", False))
        or bool(payload.get("rollback_replan_required", False))
        or policy_status == "replan_required"
    )
    lifecycle_resumable = resumable and not terminal and not replan_required
    manual_required = (
        bool(payload.get("policy_manual_required", False))
        or bool(payload.get("manual_intervention_required", False))
        or bool(payload.get("loop_manual_intervention_required", False))
        or bool(payload.get("rollback_aftermath_manual_required", False))
        or bool(payload.get("rollback_manual_followup_required", False))
        or bool(payload.get("rollback_remote_followup_required", False))
        or bool(payload.get("global_stop_recommended", False))
        or bool(payload.get("global_stop", False))
        or policy_status == "manual_only"
    )
    policy_blocked = bool(payload.get("policy_blocked", False))

    blocked_reasons = _collect_blocked_reasons(payload)
    blocked_reason = blocked_reasons[0] if blocked_reasons else ""

    rollback_execution_succeeded = bool(payload.get("rollback_execution_succeeded", False))
    rollback_execution_failed = bool(payload.get("rollback_execution_failed", False))
    rollback_aftermath_status = _normalize_text(payload.get("rollback_aftermath_status"), default="")
    rollback_complete_not_closed = rollback_execution_succeeded and (
        bool(payload.get("rollback_aftermath_blocked", False))
        or bool(payload.get("rollback_aftermath_missing_or_ambiguous", False))
        or bool(payload.get("rollback_validation_failed", False))
        or bool(payload.get("rollback_manual_followup_required", False))
        or bool(payload.get("rollback_remote_followup_required", False))
        or bool(payload.get("rollback_automatic_continuation_blocked", False))
        or (
            rollback_aftermath_status != ""
            and rollback_aftermath_status != "completed_safe"
        )
    )

    delivery_completed = bool(payload.get("delivery_completed", False)) or bool(
        payload.get("merge_execution_succeeded", False)
    )
    terminal_failure = (
        loop_state == "terminal_failure"
        or state == "failed_terminal"
        or orchestration_state == "failed_terminal"
    )
    completed_signal = (
        loop_state == "terminal_success"
        or state == "completed"
        or orchestration_state == "completed"
        or (delivery_completed and terminal)
    )
    safely_closed = (
        completed_signal
        and not terminal_failure
        and not policy_blocked
        and not manual_required
        and not replan_required
        and not rollback_complete_not_closed
        and not rollback_execution_failed
    )

    execution_complete_not_closed = delivery_completed and not safely_closed

    if safely_closed:
        closure_status = "safely_closed"
    elif rollback_complete_not_closed:
        closure_status = "rollback_complete_not_closed"
    elif execution_complete_not_closed:
        closure_status = "execution_complete_not_closed"
    elif terminal:
        closure_status = "terminal_stop"
    elif replan_required:
        closure_status = "stopped_replan_required"
    elif manual_required and not lifecycle_resumable:
        closure_status = "stopped_manual_only"
    elif lifecycle_resumable:
        closure_status = "stopped_resumable"
    else:
        closure_status = "closure_unresolved"

    if safely_closed:
        stop_class = "safely_closed"
    elif terminal:
        stop_class = "terminal_stop"
    elif replan_required:
        stop_class = "stopped_replan_required"
    elif manual_required and not lifecycle_resumable:
        stop_class = "stopped_manual_only"
    elif lifecycle_resumable:
        stop_class = "stopped_resumable"
    else:
        stop_class = "closure_unresolved"

    if safely_closed:
        primary_closure_issue = ""
    elif rollback_complete_not_closed:
        primary_closure_issue = (
            _normalize_text(payload.get("rollback_aftermath_blocked_reason"), default="")
            or rollback_aftermath_status
            or blocked_reason
            or "rollback_aftermath_unresolved"
        )
    elif execution_complete_not_closed:
        primary_closure_issue = blocked_reason or "execution_complete_closure_unresolved"
    elif terminal_failure:
        primary_closure_issue = "terminal_failure"
    elif terminal:
        primary_closure_issue = "terminal_stop"
    elif replan_required:
        primary_closure_issue = blocked_reason or "replan_required"
    elif manual_required and not lifecycle_resumable:
        primary_closure_issue = blocked_reason or "manual_followup_required"
    elif lifecycle_resumable:
        primary_closure_issue = blocked_reason or "resumable_wait_or_manual"
    else:
        primary_closure_issue = blocked_reason or "closure_unresolved"

    return {
        "lifecycle_closure_status": closure_status,
        "lifecycle_safely_closed": bool(safely_closed),
        "lifecycle_terminal": bool(terminal),
        "lifecycle_resumable": bool(lifecycle_resumable),
        "lifecycle_manual_required": bool(manual_required),
        "lifecycle_replan_required": bool(replan_required),
        "lifecycle_execution_complete_not_closed": bool(execution_complete_not_closed),
        "lifecycle_rollback_complete_not_closed": bool(rollback_complete_not_closed),
        "lifecycle_blocked_reason": blocked_reason if not safely_closed else "",
        "lifecycle_blocked_reasons": blocked_reasons if not safely_closed else [],
        "lifecycle_primary_closure_issue": primary_closure_issue,
        "lifecycle_stop_class": stop_class,
    }

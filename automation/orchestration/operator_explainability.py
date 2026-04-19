from __future__ import annotations

from typing import Any
from typing import Mapping

_EXECUTION_INTENT_ACTIONS = {
    "proceed_to_commit",
    "proceed_to_pr",
    "proceed_to_merge",
    "proceed_to_rollback",
    "rollback_required",
}

_DUPLICATE_PR_REASONS = {
    "existing_open_pr_detected",
    "blocked_existing_pr",
    "existing_pr_identity_ambiguous",
    "existing_pr_lookup_ambiguous",
}

OPERATOR_SUMMARY_SAFE_FIELDS = (
    "operator_posture_summary",
    "operator_primary_blocker_class",
    "operator_primary_action",
    "operator_action_scope",
    "operator_resume_status",
    "operator_next_safe_posture",
)

OPERATOR_RENDERING_ONLY_FIELDS = (
    "operator_guidance_summary",
    "operator_safe_actions_summary",
    "operator_unsafe_actions_summary",
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


def _build_guidance_summary(
    *,
    safe_actions_summary: str,
    unsafe_actions_summary: str,
    next_safe_posture: str,
) -> str:
    safe_now = safe_actions_summary or "none"
    unsafe_now = unsafe_actions_summary or "none"
    needed_now = next_safe_posture or "inspect"
    return f"safe_now:{safe_now}; unsafe_now:{unsafe_now}; needed_now:{needed_now}"


def build_operator_explainability_surface(
    run_state_payload: Mapping[str, Any] | None,
    *,
    include_rendering_details: bool = True,
) -> dict[str, Any]:
    payload = dict(run_state_payload or {})

    policy_status = _normalize_text(payload.get("policy_status"), default="")
    policy_primary_blocker_class = _normalize_text(
        payload.get("policy_primary_blocker_class"),
        default="none",
    )
    policy_primary_action = _normalize_text(payload.get("policy_primary_action"), default="")
    loop_state = _normalize_text(payload.get("loop_state"), default="")
    next_safe_action = _normalize_text(payload.get("next_safe_action"), default="")

    blocked_reasons = _unique(
        _normalize_string_list(payload.get("policy_blocked_reasons"))
        + _normalize_string_list(payload.get("loop_blocked_reasons"))
        + _normalize_string_list(payload.get("remote_github_blocked_reasons"))
        + _normalize_string_list(payload.get("rollback_aftermath_blocked_reasons"))
    )
    for key in (
        "policy_blocked_reason",
        "loop_blocked_reason",
        "remote_github_blocked_reason",
        "rollback_aftermath_blocked_reason",
    ):
        reason = _normalize_text(payload.get(key), default="")
        if reason and reason not in blocked_reasons:
            blocked_reasons.append(reason)

    has_run_signal = any(
        (
            _normalize_text(payload.get("state"), default=""),
            loop_state,
            policy_status,
            next_safe_action,
            policy_primary_action,
            _normalize_text(payload.get("next_run_action"), default=""),
        )
    )
    if not has_run_signal:
        base_surface = {
            "operator_posture_summary": "state_unavailable",
            "operator_primary_blocker_class": policy_primary_blocker_class,
            "operator_primary_action": policy_primary_action,
            "operator_action_scope": "unknown",
            "operator_resume_status": "unknown",
            "operator_next_safe_posture": "inspect_state",
        }
        if not include_rendering_details:
            return base_surface
        return {
            **base_surface,
            "operator_guidance_summary": "safe_now:inspect; unsafe_now:none; needed_now:inspect_state",
            "operator_safe_actions_summary": "inspect",
            "operator_unsafe_actions_summary": "",
        }

    policy_blocked = bool(payload.get("policy_blocked", False))
    policy_manual_required = bool(payload.get("policy_manual_required", False)) or bool(
        payload.get("manual_intervention_required", False)
    ) or bool(payload.get("loop_manual_intervention_required", False))
    policy_replan_required = bool(payload.get("policy_replan_required", False)) or bool(
        payload.get("loop_replan_required", False)
    ) or bool(payload.get("rollback_replan_required", False))
    policy_terminal = bool(payload.get("policy_terminal", False)) or bool(payload.get("terminal", False))
    policy_resume_allowed = bool(payload.get("policy_resume_allowed", False)) or bool(payload.get("resumable", False))
    rollback_aftermath_blocked = bool(payload.get("rollback_aftermath_blocked", False))

    disallowed_actions = _unique(_normalize_string_list(payload.get("policy_disallowed_actions")))
    allowed_actions = _unique(_normalize_string_list(payload.get("policy_allowed_actions")))

    execution_disallowed = [action for action in disallowed_actions if action in _EXECUTION_INTENT_ACTIONS]
    duplicate_pr_blocker = any(reason in _DUPLICATE_PR_REASONS for reason in blocked_reasons)
    remote_action_specific = (
        policy_primary_blocker_class == "remote_github"
        and policy_primary_action in {"proceed_to_pr", "proceed_to_merge"}
        and not policy_replan_required
        and not policy_terminal
    )
    action_specific_denial = duplicate_pr_blocker or remote_action_specific or len(execution_disallowed) == 1

    has_denial = policy_blocked or policy_manual_required or policy_replan_required or policy_terminal
    if not has_denial:
        action_scope = "none"
    elif (
        policy_primary_blocker_class in {"rollback_aftermath", "manual_gate", "missing_or_ambiguous", "terminal", "replan_required"}
        or policy_replan_required
        or policy_terminal
        or rollback_aftermath_blocked
    ):
        action_scope = "run_wide"
    elif action_specific_denial:
        action_scope = "action_specific"
    else:
        action_scope = "run_wide"

    if policy_terminal:
        posture_summary = "terminal_stop"
    elif policy_primary_blocker_class == "rollback_aftermath" and has_denial:
        posture_summary = "rollback_unresolved_manual_followup"
    elif policy_replan_required:
        posture_summary = "execution_blocked_replan_required"
    elif policy_blocked and action_scope == "action_specific":
        posture_summary = "action_specific_denial_non_terminal"
    elif (policy_blocked or policy_manual_required) and policy_resume_allowed:
        posture_summary = "execution_blocked_resumable_wait_or_manual"
    elif policy_blocked or policy_manual_required:
        posture_summary = "execution_blocked_manual_followup"
    else:
        posture_summary = "safe_to_continue"

    if policy_terminal:
        resume_status = "terminal"
    elif policy_replan_required:
        resume_status = "replan_required"
    elif policy_manual_required and not policy_resume_allowed:
        resume_status = "manual_only"
    elif policy_resume_allowed:
        resume_status = "resumable"
    elif policy_blocked:
        resume_status = "blocked_non_resumable"
    else:
        resume_status = "continue"

    if posture_summary == "safe_to_continue":
        next_safe_posture = "continue_execution"
    elif posture_summary == "action_specific_denial_non_terminal":
        next_safe_posture = "avoid_primary_denied_action"
    elif posture_summary == "execution_blocked_replan_required":
        next_safe_posture = "replan_required_before_execution"
    elif posture_summary == "rollback_unresolved_manual_followup":
        next_safe_posture = "manual_rollback_followup_required"
    elif posture_summary == "terminal_stop":
        next_safe_posture = "stop_terminal"
    elif policy_resume_allowed:
        next_safe_posture = "manual_followup_or_wait_then_resume"
    else:
        next_safe_posture = "manual_followup_required"

    if not allowed_actions:
        if posture_summary == "safe_to_continue":
            allowed_actions = ["proceed_to_commit", "proceed_to_pr", "proceed_to_merge"]
        else:
            allowed_actions = ["inspect"]
    if policy_primary_action and action_scope == "action_specific" and policy_primary_action not in disallowed_actions:
        disallowed_actions = [*disallowed_actions, policy_primary_action]

    safe_actions_summary = ", ".join(allowed_actions)
    unsafe_actions_summary = ", ".join(disallowed_actions)
    guidance_summary = _build_guidance_summary(
        safe_actions_summary=safe_actions_summary,
        unsafe_actions_summary=unsafe_actions_summary,
        next_safe_posture=next_safe_posture,
    )

    base_surface = {
        "operator_posture_summary": posture_summary,
        "operator_primary_blocker_class": policy_primary_blocker_class,
        "operator_primary_action": policy_primary_action,
        "operator_action_scope": action_scope,
        "operator_resume_status": resume_status,
        "operator_next_safe_posture": next_safe_posture,
    }
    if not include_rendering_details:
        return base_surface
    return {
        **base_surface,
        "operator_guidance_summary": guidance_summary,
        "operator_safe_actions_summary": safe_actions_summary,
        "operator_unsafe_actions_summary": unsafe_actions_summary,
    }

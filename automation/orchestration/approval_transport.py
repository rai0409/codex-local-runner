from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Mapping

APPROVAL_TRANSPORT_SCHEMA_VERSION = "v1"

APPROVAL_STATUSES = {
    "approved",
    "denied",
    "deferred",
    "replan_requested",
    "absent",
}

APPROVAL_DECISIONS = {
    "approve",
    "deny",
    "defer",
    "request_replan",
    "none",
}

APPROVAL_SCOPES = {
    "current_run",
    "current_completion_state",
    "next_safe_action_only",
    "manual_closure_only",
    "replan_only",
}

APPROVED_ACTIONS = {
    "close_run",
    "pause_run",
    "hold_for_manual_review",
    "allow_manual_closure",
    "request_replan",
    "no_action",
}

APPROVAL_COMPATIBILITY_STATUSES = {
    "compatible",
    "partially_compatible",
    "incompatible",
    "insufficient_truth",
}

APPROVAL_TRANSPORT_STATUSES = {
    "actionable",
    "non_actionable",
    "expired",
    "superseded",
    "blocked",
    "missing",
}

_ALLOWED_SUPPORTING_REFS = (
    "run_state.next_safe_action",
    "run_state.policy_primary_action",
    "run_state.lifecycle_closure_status",
    "run_state.lifecycle_primary_closure_issue",
    "run_state.policy_status",
    "completion_contract.completion_status",
    "completion_contract.closure_decision",
    "objective_contract.objective_status",
)

APPROVAL_RUN_STATE_SUMMARY_SAFE_FIELDS = (
    "approval_transport_present",
    "approval_status",
    "approval_decision",
    "approval_scope",
    "approved_action",
    "approval_required",
    "approval_transport_status",
    "approval_compatibility_status",
    "approval_blocked_reason",
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


def _normalize_enum(value: Any, *, allowed: set[str], default: str) -> str:
    text = _normalize_text(value, default="")
    if text in allowed:
        return text
    return default


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in values:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _parse_iso_datetime(value: str) -> datetime | None:
    text = _normalize_text(value, default="")
    if not text:
        return None
    normalized = text
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _derive_approval_status(approval_decision: str) -> str:
    if approval_decision == "approve":
        return "approved"
    if approval_decision == "deny":
        return "denied"
    if approval_decision == "defer":
        return "deferred"
    if approval_decision == "request_replan":
        return "replan_requested"
    return "absent"


def _derive_default_approved_action(
    *,
    approval_decision: str,
    done_status: str,
    safe_closure_status: str,
    manual_required: bool,
) -> str:
    if approval_decision == "request_replan":
        return "request_replan"
    if approval_decision == "defer":
        return "hold_for_manual_review"
    if approval_decision == "deny":
        return "hold_for_manual_review"
    if approval_decision != "approve":
        return "no_action"
    if done_status == "done" and safe_closure_status == "safely_closed":
        return "close_run"
    if manual_required:
        return "allow_manual_closure"
    return "no_action"


def _build_supporting_refs(
    *,
    next_safe_action: str,
    policy_primary_action: str,
    lifecycle_closure_status: str,
    lifecycle_primary_closure_issue: str,
    policy_status: str,
    completion_status: str,
    completion_closure_decision: str,
    objective_status: str,
) -> list[str]:
    refs: list[str] = []
    if next_safe_action:
        refs.append("run_state.next_safe_action")
    if policy_primary_action:
        refs.append("run_state.policy_primary_action")
    if lifecycle_closure_status:
        refs.append("run_state.lifecycle_closure_status")
    if lifecycle_primary_closure_issue:
        refs.append("run_state.lifecycle_primary_closure_issue")
    if policy_status:
        refs.append("run_state.policy_status")
    if completion_status:
        refs.append("completion_contract.completion_status")
    if completion_closure_decision:
        refs.append("completion_contract.closure_decision")
    if objective_status:
        refs.append("objective_contract.objective_status")

    ordered: list[str] = []
    for allowed in _ALLOWED_SUPPORTING_REFS:
        if allowed in refs and allowed not in ordered:
            ordered.append(allowed)
    return ordered


def build_approval_transport_surface(
    *,
    run_id: str,
    objective_contract_payload: Mapping[str, Any] | None,
    completion_contract_payload: Mapping[str, Any] | None,
    run_state_payload: Mapping[str, Any] | None,
    approval_input_payload: Mapping[str, Any] | None,
    evaluated_at: str,
) -> dict[str, Any]:
    objective = dict(objective_contract_payload or {})
    completion = dict(completion_contract_payload or {})
    run_state = dict(run_state_payload or {})
    approval_input = dict(approval_input_payload or {})

    objective_id = _normalize_text(
        objective.get("objective_id")
        or completion.get("objective_id")
        or run_state.get("objective_id"),
        default="",
    )
    objective_summary = _normalize_text(
        objective.get("objective_summary") or run_state.get("objective_summary"),
        default="",
    )
    requested_outcome = _normalize_text(
        objective.get("requested_outcome") or run_state.get("requested_outcome"),
        default="",
    )

    completion_status = _normalize_text(
        completion.get("completion_status") or run_state.get("completion_status"),
        default="",
    )
    done_status = _normalize_text(
        completion.get("done_status") or run_state.get("done_status"),
        default="",
    )
    safe_closure_status = _normalize_text(
        completion.get("safe_closure_status") or run_state.get("safe_closure_status"),
        default="",
    )
    completion_manual_required = _normalize_bool(
        completion.get("completion_manual_required")
        if "completion_manual_required" in completion
        else run_state.get("completion_manual_required")
    )
    completion_replan_required = _normalize_bool(
        completion.get("completion_replan_required")
        if "completion_replan_required" in completion
        else run_state.get("completion_replan_required")
    )

    lifecycle_closure_status = _normalize_text(run_state.get("lifecycle_closure_status"), default="")
    lifecycle_primary_closure_issue = _normalize_text(run_state.get("lifecycle_primary_closure_issue"), default="")
    lifecycle_manual_required = _normalize_bool(run_state.get("lifecycle_manual_required"))
    lifecycle_replan_required = _normalize_bool(run_state.get("lifecycle_replan_required"))

    next_safe_action = _normalize_text(run_state.get("next_safe_action"), default="")
    policy_primary_action = _normalize_text(run_state.get("policy_primary_action"), default="")
    policy_status = _normalize_text(run_state.get("policy_status"), default="")
    policy_manual_required = _normalize_bool(run_state.get("policy_manual_required"))
    policy_replan_required = _normalize_bool(run_state.get("policy_replan_required"))

    objective_status = _normalize_text(objective.get("objective_status"), default="")
    completion_closure_decision = _normalize_text(completion.get("closure_decision"), default="")

    explicit_decision = _normalize_text(
        approval_input.get("approval_decision") or approval_input.get("decision"),
        default="none",
    )
    approval_decision = _normalize_enum(
        explicit_decision,
        allowed=APPROVAL_DECISIONS,
        default="none",
    )

    explicit_scope = _normalize_text(
        approval_input.get("approval_scope") or approval_input.get("scope"),
        default="current_completion_state",
    )
    approval_scope = _normalize_enum(
        explicit_scope,
        allowed=APPROVAL_SCOPES,
        default="current_completion_state",
    )

    approval_actor = _normalize_text(
        approval_input.get("approval_actor") or approval_input.get("actor"),
        default="",
    )
    approval_reason = _normalize_text(
        approval_input.get("approval_reason") or approval_input.get("reason"),
        default="",
    )
    approval_notes = _normalize_text(
        approval_input.get("approval_notes") or approval_input.get("notes"),
        default="",
    )
    approval_recorded_at = _normalize_text(
        approval_input.get("approval_recorded_at")
        or approval_input.get("recorded_at")
        or approval_input.get("timestamp"),
        default="",
    )
    approval_expires_at = _normalize_text(
        approval_input.get("approval_expires_at") or approval_input.get("expires_at"),
        default="",
    )

    input_has_content = bool(approval_input)
    approval_present = bool(input_has_content and (
        approval_decision != "none"
        or approval_actor
        or approval_reason
        or approval_notes
        or approval_recorded_at
        or approval_expires_at
    ))

    approval_required = bool(
        completion_manual_required
        or completion_replan_required
        or lifecycle_manual_required
        or lifecycle_replan_required
        or policy_manual_required
        or policy_replan_required
        or _normalize_bool(run_state.get("manual_intervention_required"))
    )
    approval_requested = bool(
        approval_required
        or next_safe_action in {"require_manual_intervention", "require_replanning", "pause"}
        or policy_status in {"manual_only", "replan_required"}
    )

    approval_status = _derive_approval_status(approval_decision)
    approval_status = _normalize_enum(approval_status, allowed=APPROVAL_STATUSES, default="absent")

    explicit_action = _normalize_text(
        approval_input.get("approved_action") or approval_input.get("action"),
        default="",
    )
    approved_action = _normalize_enum(
        explicit_action,
        allowed=APPROVED_ACTIONS,
        default=_derive_default_approved_action(
            approval_decision=approval_decision,
            done_status=done_status,
            safe_closure_status=safe_closure_status,
            manual_required=approval_required,
        ),
    )

    evaluated_dt = _parse_iso_datetime(evaluated_at)
    expires_dt = _parse_iso_datetime(approval_expires_at)
    approval_stale = bool(expires_dt is not None and evaluated_dt is not None and evaluated_dt > expires_dt)

    explicit_superseded = _normalize_bool(
        approval_input.get("approval_superseded")
        if "approval_superseded" in approval_input
        else approval_input.get("superseded")
    )
    target_run_id = _normalize_text(
        approval_input.get("target_run_id") or approval_input.get("approval_for_run_id"),
        default="",
    )
    target_objective_id = _normalize_text(
        approval_input.get("target_objective_id") or approval_input.get("approval_for_objective_id"),
        default="",
    )
    target_completion_status = _normalize_text(
        approval_input.get("target_completion_status") or approval_input.get("approval_for_completion_status"),
        default="",
    )

    approval_superseded = bool(
        explicit_superseded
        or (target_run_id and target_run_id != _normalize_text(run_id, default=""))
        or (target_objective_id and objective_id and target_objective_id != objective_id)
        or (target_completion_status and completion_status and target_completion_status != completion_status)
    )

    insufficient_truth = not completion_status or not lifecycle_closure_status
    truth_needs_replan = bool(completion_replan_required or lifecycle_replan_required or policy_replan_required)
    truth_needs_manual = bool(completion_manual_required or lifecycle_manual_required or policy_manual_required)
    closure_intent = (
        approval_decision == "approve"
        and (
            approved_action in {"close_run", "allow_manual_closure"}
            or approval_scope in {"current_run", "current_completion_state", "manual_closure_only"}
        )
    )

    compatibility_status = "insufficient_truth"
    if not approval_present or approval_status == "absent":
        compatibility_status = "insufficient_truth"
    elif insufficient_truth:
        compatibility_status = "insufficient_truth"
    elif approval_decision == "request_replan":
        compatibility_status = "compatible" if truth_needs_replan else "partially_compatible"
    elif approval_decision in {"deny", "defer"}:
        compatibility_status = "partially_compatible"
    elif approval_decision == "approve":
        if closure_intent and done_status != "done":
            compatibility_status = "incompatible"
        elif closure_intent and (
            safe_closure_status != "safely_closed"
            or lifecycle_closure_status != "safely_closed"
            or truth_needs_manual
            or truth_needs_replan
        ):
            compatibility_status = "incompatible"
        elif approval_scope == "next_safe_action_only" and (truth_needs_manual or truth_needs_replan):
            compatibility_status = "partially_compatible"
        elif approval_scope == "manual_closure_only" and truth_needs_replan:
            compatibility_status = "partially_compatible"
        elif approval_scope == "replan_only" and not truth_needs_replan:
            compatibility_status = "partially_compatible"
        else:
            compatibility_status = "compatible"

    approval_compatibility_status = _normalize_enum(
        compatibility_status,
        allowed=APPROVAL_COMPATIBILITY_STATUSES,
        default="insufficient_truth",
    )

    if not approval_present or approval_status == "absent":
        approval_transport_status = "missing"
    elif approval_stale:
        approval_transport_status = "expired"
    elif approval_superseded:
        approval_transport_status = "superseded"
    elif approval_compatibility_status in {"incompatible", "insufficient_truth"}:
        approval_transport_status = "blocked"
    elif approval_status == "approved" and approval_compatibility_status == "compatible":
        approval_transport_status = "actionable"
    elif approval_status == "replan_requested" and approval_compatibility_status in {
        "compatible",
        "partially_compatible",
    }:
        approval_transport_status = "actionable"
    else:
        approval_transport_status = "non_actionable"

    approval_transport_status = _normalize_enum(
        approval_transport_status,
        allowed=APPROVAL_TRANSPORT_STATUSES,
        default="missing",
    )

    blocked_reasons: list[str] = []
    if approval_status == "absent":
        blocked_reasons.append("approval_absent")
    if approval_decision == "none":
        blocked_reasons.append("approval_decision_none")
    if approval_stale:
        blocked_reasons.append("approval_stale")
    if approval_superseded:
        blocked_reasons.append("approval_superseded")
    if approval_compatibility_status == "insufficient_truth":
        blocked_reasons.append("approval_truth_insufficient")
    if approval_compatibility_status == "incompatible":
        blocked_reasons.append("approval_incompatible")
    if approval_compatibility_status == "partially_compatible":
        blocked_reasons.append("approval_scope_partial")
    if closure_intent and done_status != "done":
        blocked_reasons.append("completion_not_done_for_closure")
    if closure_intent and safe_closure_status != "safely_closed":
        blocked_reasons.append("lifecycle_not_safely_closed_for_closure")
    if approval_status == "denied":
        blocked_reasons.append("approval_denied")
    if approval_status == "deferred":
        blocked_reasons.append("approval_deferred")
    if approval_status == "replan_requested" and not truth_needs_replan:
        blocked_reasons.append("approval_replan_not_required")
    if approval_transport_status == "missing":
        blocked_reasons.append("approval_missing")
    if approval_transport_status == "non_actionable":
        blocked_reasons.append("approval_non_actionable")

    approval_blocked_reasons = _dedupe(blocked_reasons)
    approval_blocked_reason = approval_blocked_reasons[0] if approval_blocked_reasons else ""

    if approval_transport_status == "actionable":
        approval_blocked_reason = ""
        approval_blocked_reasons = []

    payload: dict[str, Any] = {
        "schema_version": APPROVAL_TRANSPORT_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "completion_status": completion_status,
        "approval_status": approval_status,
        "approval_decision": approval_decision,
        "approval_scope": approval_scope,
        "approved_action": approved_action,
        "approval_reason": approval_reason,
        "approval_notes": approval_notes,
        "approval_requested": bool(approval_requested),
        "approval_required": bool(approval_required),
        "approval_present": bool(approval_present),
        "approval_actor": approval_actor,
        "approval_recorded_at": approval_recorded_at,
        "approval_expires_at": approval_expires_at,
        "approval_compatibility_status": approval_compatibility_status,
        "approval_blocked_reason": approval_blocked_reason,
        "approval_blocked_reasons": approval_blocked_reasons,
        "approval_superseded": bool(approval_superseded),
        "approval_stale": bool(approval_stale),
        "approval_transport_status": approval_transport_status,
        "supporting_compact_truth_refs": _build_supporting_refs(
            next_safe_action=next_safe_action,
            policy_primary_action=policy_primary_action,
            lifecycle_closure_status=lifecycle_closure_status,
            lifecycle_primary_closure_issue=lifecycle_primary_closure_issue,
            policy_status=policy_status,
            completion_status=completion_status,
            completion_closure_decision=completion_closure_decision,
            objective_status=objective_status,
        ),
    }

    if requested_outcome:
        payload["requested_outcome"] = requested_outcome
    if objective_summary:
        payload["objective_summary"] = objective_summary

    completion_blocked_reason = _normalize_text(completion.get("completion_blocked_reason"), default="")
    if completion_blocked_reason:
        payload["completion_blocked_reason"] = completion_blocked_reason
    if next_safe_action:
        payload["next_safe_action"] = next_safe_action
    if policy_primary_action:
        payload["policy_primary_action"] = policy_primary_action

    return payload


def build_approval_run_state_summary_surface(
    approval_transport_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(approval_transport_payload or {})

    approval_status = _normalize_text(payload.get("approval_status"), default="")
    approval_decision = _normalize_text(payload.get("approval_decision"), default="")
    approval_scope = _normalize_text(payload.get("approval_scope"), default="")
    approved_action = _normalize_text(payload.get("approved_action"), default="")
    approval_required = _normalize_bool(payload.get("approval_required"))
    transport_status = _normalize_text(payload.get("approval_transport_status"), default="")
    compatibility_status = _normalize_text(payload.get("approval_compatibility_status"), default="")
    blocked_reason = _normalize_text(payload.get("approval_blocked_reason"), default="")

    present = bool(payload.get("approval_transport_present", False)) or bool(
        approval_status or approval_decision or transport_status
    )

    if not approval_status:
        approval_status = "absent"
    if not approval_decision:
        approval_decision = "none"
    if not approval_scope:
        approval_scope = "current_completion_state"
    if not approved_action:
        approved_action = "no_action"
    if not transport_status:
        transport_status = "missing"
    if not compatibility_status:
        compatibility_status = "insufficient_truth"

    approval_status = _normalize_enum(approval_status, allowed=APPROVAL_STATUSES, default="absent")
    approval_decision = _normalize_enum(approval_decision, allowed=APPROVAL_DECISIONS, default="none")
    approval_scope = _normalize_enum(
        approval_scope,
        allowed=APPROVAL_SCOPES,
        default="current_completion_state",
    )
    approved_action = _normalize_enum(approved_action, allowed=APPROVED_ACTIONS, default="no_action")
    transport_status = _normalize_enum(
        transport_status,
        allowed=APPROVAL_TRANSPORT_STATUSES,
        default="missing",
    )
    compatibility_status = _normalize_enum(
        compatibility_status,
        allowed=APPROVAL_COMPATIBILITY_STATUSES,
        default="insufficient_truth",
    )

    if transport_status == "actionable":
        blocked_reason = ""
    elif not blocked_reason:
        if transport_status == "missing":
            blocked_reason = "approval_missing"
        elif transport_status == "expired":
            blocked_reason = "approval_stale"
        elif transport_status == "superseded":
            blocked_reason = "approval_superseded"
        elif transport_status == "blocked":
            blocked_reason = "approval_blocked"
        else:
            blocked_reason = "approval_non_actionable"

    return {
        "approval_transport_present": bool(present),
        "approval_status": approval_status,
        "approval_decision": approval_decision,
        "approval_scope": approval_scope,
        "approved_action": approved_action,
        "approval_required": bool(approval_required),
        "approval_transport_status": transport_status,
        "approval_compatibility_status": compatibility_status,
        "approval_blocked_reason": blocked_reason,
    }

from __future__ import annotations

from typing import Any
from typing import Mapping

REPAIR_APPROVAL_BINDING_SCHEMA_VERSION = "v1"

REPAIR_APPROVAL_BINDING_STATUSES = {
    "bound",
    "partially_bound",
    "blocked",
    "missing",
    "not_applicable",
}

REPAIR_APPROVAL_BINDING_DECISIONS = {
    "bind_for_future_execution",
    "hold_unbound",
    "manual_review_required",
    "request_replan",
    "no_binding",
}

REPAIR_APPROVAL_BINDING_SCOPES = {
    "current_plan_candidate",
    "current_repair_posture",
    "manual_review_only",
    "replan_only",
    "none",
}

REPAIR_APPROVAL_BINDING_VALIDITIES = {
    "valid",
    "stale",
    "superseded",
    "invalid",
    "insufficient_truth",
}

REPAIR_APPROVAL_BINDING_COMPATIBILITY_STATUSES = {
    "compatible",
    "partially_compatible",
    "incompatible",
    "insufficient_truth",
}

REPAIR_APPROVAL_BINDING_SOURCE_STATUSES = {
    "derived_from_plan_and_approval",
    "derived_from_plan_only",
    "derived_from_approval_only",
    "insufficient_truth",
}

REPAIR_APPROVAL_BINDING_REASON_CODES = {
    "missing_plan_candidate",
    "missing_approval",
    "approval_denied",
    "approval_deferred",
    "approval_scope_mismatch",
    "approval_stale",
    "approval_superseded",
    "approval_conflict",
    "plan_not_needed",
    "replan_required",
    "manual_intervention_required",
    "insufficient_upstream_truth",
    "no_reason",
}

REPAIR_APPROVAL_BINDING_REASON_ORDER = (
    "missing_plan_candidate",
    "missing_approval",
    "approval_denied",
    "approval_deferred",
    "approval_scope_mismatch",
    "approval_stale",
    "approval_superseded",
    "approval_conflict",
    "plan_not_needed",
    "replan_required",
    "manual_intervention_required",
    "insufficient_upstream_truth",
    "no_reason",
)

REPAIR_APPROVAL_BINDING_RUN_STATE_SUMMARY_SAFE_FIELDS = (
    "repair_approval_binding_present",
    "repair_approval_binding_status",
    "repair_approval_binding_decision",
    "repair_approval_binding_scope",
    "repair_approval_binding_validity",
    "repair_approval_binding_compatibility_status",
    "repair_approval_binding_primary_reason",
    "repair_approval_binding_manual_required",
    "repair_approval_binding_replan_required",
    "repair_approval_binding_truth_gathering_required",
)

_ALLOWED_SUPPORTING_REFS = (
    "run_state.next_safe_action",
    "run_state.policy_primary_action",
    "run_state.lifecycle_closure_status",
    "run_state.lifecycle_primary_closure_issue",
    "run_state.policy_status",
    "completion_contract.completion_status",
    "completion_contract.closure_decision",
    "approval_transport.approval_status",
    "approval_transport.approval_transport_status",
    "repair_plan_transport.repair_plan_status",
    "repair_plan_transport.repair_plan_candidate_action",
    "repair_plan_transport.repair_plan_primary_reason",
    "repair_suggestion_contract.repair_suggestion_status",
    "reconcile_contract.reconcile_status",
    "objective_contract.objective_status",
)

_PLAN_ACTION_ALLOWED_SCOPES = {
    "gather_missing_truth": {"current_run", "current_completion_state", "next_safe_action_only"},
    "request_manual_review": {
        "current_run",
        "current_completion_state",
        "next_safe_action_only",
        "manual_closure_only",
    },
    "request_replan": {"current_run", "current_completion_state", "replan_only"},
    "request_closure_followup": {"current_run", "current_completion_state", "manual_closure_only"},
    "no_action": {
        "current_run",
        "current_completion_state",
        "next_safe_action_only",
        "manual_closure_only",
        "replan_only",
    },
}

_PLAN_ACTION_PARTIAL_SCOPES = {
    "gather_missing_truth": {"manual_closure_only", "replan_only"},
    "request_manual_review": set(),
    "request_replan": {"next_safe_action_only"},
    "request_closure_followup": {"next_safe_action_only"},
    "no_action": set(),
}

_PLAN_ACTION_COMPATIBLE_APPROVED_ACTIONS = {
    "gather_missing_truth": {"no_action", "hold_for_manual_review", "pause_run"},
    "request_manual_review": {"hold_for_manual_review", "pause_run", "allow_manual_closure"},
    "request_replan": {"request_replan"},
    "request_closure_followup": {"allow_manual_closure", "hold_for_manual_review"},
    "no_action": {"no_action"},
}

_PLAN_ACTION_PARTIAL_APPROVED_ACTIONS = {
    "gather_missing_truth": {"allow_manual_closure"},
    "request_manual_review": {"no_action"},
    "request_replan": {"no_action"},
    "request_closure_followup": {"pause_run", "no_action"},
    "no_action": {"hold_for_manual_review", "pause_run"},
}


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


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = _normalize_text(value, default="")
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _normalize_reason_codes(values: list[str]) -> list[str]:
    filtered = _ordered_unique(values)
    ordered: list[str] = []
    for reason in REPAIR_APPROVAL_BINDING_REASON_ORDER:
        if reason in filtered and reason in REPAIR_APPROVAL_BINDING_REASON_CODES:
            ordered.append(reason)
    return ordered


def _build_supporting_refs(
    *,
    next_safe_action: str,
    policy_primary_action: str,
    lifecycle_closure_status: str,
    lifecycle_primary_closure_issue: str,
    policy_status: str,
    completion_status: str,
    closure_decision: str,
    approval_status: str,
    approval_transport_status: str,
    repair_plan_status: str,
    repair_plan_candidate_action: str,
    repair_plan_primary_reason: str,
    repair_suggestion_status: str,
    reconcile_status: str,
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
    if closure_decision:
        refs.append("completion_contract.closure_decision")
    if approval_status:
        refs.append("approval_transport.approval_status")
    if approval_transport_status:
        refs.append("approval_transport.approval_transport_status")
    if repair_plan_status:
        refs.append("repair_plan_transport.repair_plan_status")
    if repair_plan_candidate_action:
        refs.append("repair_plan_transport.repair_plan_candidate_action")
    if repair_plan_primary_reason:
        refs.append("repair_plan_transport.repair_plan_primary_reason")
    if repair_suggestion_status:
        refs.append("repair_suggestion_contract.repair_suggestion_status")
    if reconcile_status:
        refs.append("reconcile_contract.reconcile_status")
    if objective_status:
        refs.append("objective_contract.objective_status")

    ordered: list[str] = []
    for allowed in _ALLOWED_SUPPORTING_REFS:
        if allowed in refs and allowed not in ordered:
            ordered.append(allowed)
    return ordered


def _scope_compatibility(*, plan_action: str, approval_scope: str) -> str:
    if not plan_action or not approval_scope:
        return "insufficient_truth"
    allowed = _PLAN_ACTION_ALLOWED_SCOPES.get(plan_action, set())
    if approval_scope in allowed:
        return "compatible"
    partial = _PLAN_ACTION_PARTIAL_SCOPES.get(plan_action, set())
    if approval_scope in partial:
        return "partially_compatible"
    return "incompatible"


def _action_compatibility(
    *,
    plan_action: str,
    approval_status: str,
    approval_decision: str,
    approved_action: str,
) -> str:
    if not plan_action:
        return "insufficient_truth"
    if approval_status in {"", "absent"}:
        return "insufficient_truth"
    if approval_status == "denied":
        return "incompatible"
    if approval_status == "deferred":
        if plan_action in {"gather_missing_truth", "request_manual_review", "request_closure_followup"}:
            return "partially_compatible"
        return "incompatible"
    if approval_status == "replan_requested":
        return "compatible" if plan_action == "request_replan" else "incompatible"

    compatible_actions = _PLAN_ACTION_COMPATIBLE_APPROVED_ACTIONS.get(plan_action, set())
    partial_actions = _PLAN_ACTION_PARTIAL_APPROVED_ACTIONS.get(plan_action, set())

    if approved_action and approved_action in compatible_actions:
        return "compatible"
    if approved_action and approved_action in partial_actions:
        return "partially_compatible"

    if approval_decision == "approve":
        if plan_action in {"gather_missing_truth", "request_manual_review"}:
            return "partially_compatible"
        return "incompatible"
    if approval_decision == "request_replan":
        return "compatible" if plan_action == "request_replan" else "incompatible"
    if approval_decision == "defer":
        return "partially_compatible" if plan_action != "request_replan" else "incompatible"
    if approval_decision == "deny":
        return "incompatible"
    return "insufficient_truth"


def _combine_compatibility(*, scope: str, action: str) -> str:
    if "incompatible" in {scope, action}:
        return "incompatible"
    if "partially_compatible" in {scope, action}:
        return "partially_compatible"
    if scope == "compatible" and action == "compatible":
        return "compatible"
    return "insufficient_truth"


def _derive_source_status(*, plan_present: bool, approval_present: bool) -> str:
    if plan_present and approval_present:
        return "derived_from_plan_and_approval"
    if plan_present:
        return "derived_from_plan_only"
    if approval_present:
        return "derived_from_approval_only"
    return "insufficient_truth"


def build_repair_approval_binding_surface(
    *,
    run_id: str,
    objective_contract_payload: Mapping[str, Any] | None,
    completion_contract_payload: Mapping[str, Any] | None,
    approval_transport_payload: Mapping[str, Any] | None,
    reconcile_contract_payload: Mapping[str, Any] | None,
    repair_suggestion_contract_payload: Mapping[str, Any] | None,
    repair_plan_transport_payload: Mapping[str, Any] | None,
    run_state_payload: Mapping[str, Any] | None,
    artifact_presence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    objective = dict(objective_contract_payload or {})
    completion = dict(completion_contract_payload or {})
    approval = dict(approval_transport_payload or {})
    reconcile = dict(reconcile_contract_payload or {})
    repair_suggestion = dict(repair_suggestion_contract_payload or {})
    repair_plan = dict(repair_plan_transport_payload or {})
    run_state = dict(run_state_payload or {})
    artifacts = dict(artifact_presence or {})

    objective_id = _normalize_text(
        objective.get("objective_id")
        or completion.get("objective_id")
        or approval.get("objective_id")
        or reconcile.get("objective_id")
        or repair_suggestion.get("objective_id")
        or repair_plan.get("objective_id")
        or run_state.get("objective_id"),
        default="",
    )
    objective_summary = _normalize_text(
        objective.get("objective_summary")
        or run_state.get("objective_summary")
        or repair_suggestion.get("objective_summary"),
        default="",
    )
    requested_outcome = _normalize_text(
        objective.get("requested_outcome")
        or run_state.get("requested_outcome")
        or repair_suggestion.get("requested_outcome"),
        default="",
    )

    objective_status = _normalize_text(
        objective.get("objective_status") or run_state.get("objective_contract_status"),
        default="",
    )
    completion_status = _normalize_text(
        completion.get("completion_status") or run_state.get("completion_status"),
        default="",
    )
    closure_decision = _normalize_text(completion.get("closure_decision"), default="")
    completion_blocked_reason = _normalize_text(
        completion.get("completion_blocked_reason") or run_state.get("completion_blocked_reason"),
        default="",
    )

    approval_status = _normalize_text(
        approval.get("approval_status") or run_state.get("approval_status"),
        default="",
    )
    approval_decision = _normalize_text(
        approval.get("approval_decision") or run_state.get("approval_decision"),
        default="",
    )
    approval_scope = _normalize_text(
        approval.get("approval_scope") or run_state.get("approval_scope"),
        default="",
    )
    approved_action = _normalize_text(
        approval.get("approved_action") or run_state.get("approved_action"),
        default="",
    )
    approval_transport_status = _normalize_text(
        approval.get("approval_transport_status") or run_state.get("approval_transport_status"),
        default="",
    )
    approval_compatibility_status = _normalize_text(
        approval.get("approval_compatibility_status") or run_state.get("approval_compatibility_status"),
        default="",
    )
    approval_present_flag = _normalize_bool(
        approval.get("approval_present")
        if "approval_present" in approval
        else run_state.get("approval_transport_present")
    )
    approval_required = _normalize_bool(
        approval.get("approval_required")
        if "approval_required" in approval
        else run_state.get("approval_required")
    )
    approval_superseded = _normalize_bool(approval.get("approval_superseded"))
    approval_stale = _normalize_bool(approval.get("approval_stale"))
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

    repair_suggestion_status = _normalize_text(
        repair_suggestion.get("repair_suggestion_status")
        or run_state.get("repair_suggestion_status"),
        default="",
    )

    repair_plan_status = _normalize_text(
        repair_plan.get("repair_plan_status") or run_state.get("repair_plan_status"),
        default="",
    )
    repair_plan_decision = _normalize_text(
        repair_plan.get("repair_plan_decision") or run_state.get("repair_plan_decision"),
        default="",
    )
    repair_plan_action = _normalize_text(
        repair_plan.get("repair_plan_candidate_action") or run_state.get("repair_plan_candidate_action"),
        default="",
    )
    repair_plan_primary_reason = _normalize_text(
        repair_plan.get("repair_plan_primary_reason") or run_state.get("repair_plan_primary_reason"),
        default="",
    )
    repair_plan_manual_required = _normalize_bool(
        repair_plan.get("repair_plan_manual_required")
        if "repair_plan_manual_required" in repair_plan
        else run_state.get("repair_plan_manual_required")
    )
    repair_plan_replan_required = _normalize_bool(
        repair_plan.get("repair_plan_replan_required")
        if "repair_plan_replan_required" in repair_plan
        else run_state.get("repair_plan_replan_required")
    )
    repair_plan_truth_gathering_required = _normalize_bool(
        repair_plan.get("repair_plan_truth_gathering_required")
        if "repair_plan_truth_gathering_required" in repair_plan
        else run_state.get("repair_plan_truth_gathering_required")
    )

    next_safe_action = _normalize_text(run_state.get("next_safe_action"), default="")
    policy_primary_action = _normalize_text(run_state.get("policy_primary_action"), default="")
    policy_status = _normalize_text(run_state.get("policy_status"), default="")
    lifecycle_closure_status = _normalize_text(run_state.get("lifecycle_closure_status"), default="")
    lifecycle_primary_closure_issue = _normalize_text(
        run_state.get("lifecycle_primary_closure_issue"),
        default="",
    )
    manual_intervention_required = _normalize_bool(
        run_state.get("manual_intervention_required")
    ) or _normalize_bool(run_state.get("policy_manual_required"))

    run_state_present = bool(run_state) or _normalize_bool(artifacts.get("run_state.json"))
    plan_present = (
        bool(repair_plan)
        or _normalize_bool(run_state.get("repair_plan_transport_present"))
        or _normalize_bool(artifacts.get("repair_plan_transport.json"))
    )
    approval_present = (
        bool(approval)
        or _normalize_bool(run_state.get("approval_transport_present"))
        or _normalize_bool(artifacts.get("approval_transport.json"))
    )

    approval_missing = (
        not approval_present
        or (approval_status in {"", "absent"} and approval_decision in {"", "none"})
        or (approval_required and not approval_present_flag and approval_status in {"", "absent"})
    )
    plan_missing = (not plan_present) or not repair_plan_status
    plan_not_needed = repair_plan_status == "not_needed"
    plan_blocked = repair_plan_status == "blocked"
    plan_insufficient_truth = repair_plan_status == "insufficient_truth"

    if approval_transport_status == "superseded":
        approval_superseded = True
    if approval_transport_status == "expired":
        approval_stale = True

    scope_compatibility = _scope_compatibility(
        plan_action=repair_plan_action or "no_action",
        approval_scope=approval_scope,
    )
    action_compatibility = _action_compatibility(
        plan_action=repair_plan_action or "no_action",
        approval_status=approval_status,
        approval_decision=approval_decision,
        approved_action=approved_action,
    )
    binding_compatibility = _combine_compatibility(
        scope=scope_compatibility,
        action=action_compatibility,
    )

    if approval_compatibility_status == "incompatible":
        binding_compatibility = "incompatible"
    elif approval_compatibility_status == "partially_compatible" and binding_compatibility == "compatible":
        binding_compatibility = "partially_compatible"
    elif approval_compatibility_status == "insufficient_truth" and binding_compatibility == "compatible":
        binding_compatibility = "insufficient_truth"

    if plan_not_needed:
        binding_validity = "valid"
    elif plan_missing or approval_missing:
        binding_validity = "insufficient_truth"
    elif approval_superseded:
        binding_validity = "superseded"
    elif approval_stale:
        binding_validity = "stale"
    elif approval_status in {"denied", "deferred"}:
        binding_validity = "invalid"
    elif binding_compatibility == "incompatible":
        binding_validity = "invalid"
    elif binding_compatibility == "insufficient_truth":
        binding_validity = "insufficient_truth"
    else:
        binding_validity = "valid"

    reason_candidates: list[str] = []
    if plan_missing:
        reason_candidates.append("missing_plan_candidate")
    if approval_missing:
        reason_candidates.append("missing_approval")
    if approval_status == "denied":
        reason_candidates.append("approval_denied")
    if approval_status == "deferred":
        reason_candidates.append("approval_deferred")
    if scope_compatibility == "incompatible":
        reason_candidates.append("approval_scope_mismatch")
    if approval_stale:
        reason_candidates.append("approval_stale")
    if approval_superseded:
        reason_candidates.append("approval_superseded")
    if binding_compatibility == "incompatible":
        reason_candidates.append("approval_conflict")
    if plan_not_needed:
        reason_candidates.append("plan_not_needed")
    if repair_plan_replan_required or repair_plan_action == "request_replan" or approval_status == "replan_requested":
        reason_candidates.append("replan_required")
    if repair_plan_manual_required or manual_intervention_required:
        reason_candidates.append("manual_intervention_required")
    if (
        not run_state_present
        or plan_insufficient_truth
        or approval_transport_status in {"missing", "blocked"}
    ):
        reason_candidates.append("insufficient_upstream_truth")

    reason_codes = _normalize_reason_codes(reason_candidates)

    explicit_replan_path = bool(
        repair_plan_replan_required
        or repair_plan_action == "request_replan"
        or approval_status == "replan_requested"
    )
    material_conflict = bool(
        approval_status == "denied"
        or binding_compatibility == "incompatible"
        or approval_superseded
        or approval_stale
    )

    if plan_not_needed:
        binding_status = "not_applicable"
    elif plan_blocked:
        binding_status = "blocked"
    elif plan_missing:
        binding_status = "missing"
    elif approval_missing:
        binding_status = "missing"
    elif approval_superseded or approval_stale:
        binding_status = "blocked"
    elif approval_status == "denied":
        binding_status = "blocked"
    elif approval_status == "deferred":
        binding_status = "partially_bound" if binding_compatibility != "incompatible" else "blocked"
    elif (
        binding_validity == "valid"
        and binding_compatibility == "compatible"
        and approval_status in {"approved", "replan_requested"}
    ):
        binding_status = "bound"
    elif binding_compatibility == "partially_compatible":
        binding_status = "partially_bound"
    elif binding_compatibility == "insufficient_truth":
        binding_status = "missing"
    else:
        binding_status = "blocked"

    if binding_status == "not_applicable":
        binding_decision = "no_binding"
    elif binding_status == "bound":
        binding_decision = "bind_for_future_execution"
    elif explicit_replan_path and binding_status in {"blocked", "partially_bound"}:
        binding_decision = "request_replan"
    elif material_conflict and binding_status in {"blocked", "partially_bound"}:
        binding_decision = "manual_review_required"
    elif binding_status == "missing":
        binding_decision = "hold_unbound"
    elif binding_status == "partially_bound":
        binding_decision = "hold_unbound"
    else:
        binding_decision = "manual_review_required"

    if binding_status == "not_applicable":
        binding_scope = "none"
    elif binding_decision == "request_replan" or repair_plan_action == "request_replan":
        binding_scope = "replan_only"
    elif binding_decision == "manual_review_required" or repair_plan_action == "request_manual_review":
        binding_scope = "manual_review_only"
    elif binding_status == "bound":
        binding_scope = "current_plan_candidate"
    else:
        binding_scope = "current_repair_posture"

    binding_status = _normalize_enum(
        binding_status,
        allowed=REPAIR_APPROVAL_BINDING_STATUSES,
        default="missing",
    )
    binding_decision = _normalize_enum(
        binding_decision,
        allowed=REPAIR_APPROVAL_BINDING_DECISIONS,
        default="hold_unbound",
    )
    binding_scope = _normalize_enum(
        binding_scope,
        allowed=REPAIR_APPROVAL_BINDING_SCOPES,
        default="current_repair_posture",
    )
    binding_validity = _normalize_enum(
        binding_validity,
        allowed=REPAIR_APPROVAL_BINDING_VALIDITIES,
        default="insufficient_truth",
    )
    binding_compatibility = _normalize_enum(
        binding_compatibility,
        allowed=REPAIR_APPROVAL_BINDING_COMPATIBILITY_STATUSES,
        default="insufficient_truth",
    )
    binding_source_status = _normalize_enum(
        _derive_source_status(plan_present=plan_present, approval_present=approval_present),
        allowed=REPAIR_APPROVAL_BINDING_SOURCE_STATUSES,
        default="insufficient_truth",
    )

    if binding_status == "not_applicable":
        reason_codes = ["no_reason"]
    elif not reason_codes:
        if binding_status == "missing":
            reason_codes = ["missing_approval"]
        elif binding_status == "partially_bound":
            reason_codes = ["approval_scope_mismatch"]
        elif binding_status == "blocked":
            reason_codes = ["approval_conflict"]
        else:
            reason_codes = ["insufficient_upstream_truth"]

    binding_primary_reason = reason_codes[0] if reason_codes else "insufficient_upstream_truth"

    blocked_reason_candidates: list[str] = []
    if binding_status not in {"bound", "not_applicable"}:
        blocked_reason_candidates.extend(reason_codes)
    blocked_reasons = _normalize_reason_codes(blocked_reason_candidates)
    if binding_status == "blocked" and not blocked_reasons:
        blocked_reasons = ["approval_conflict"]
    if binding_status == "missing" and not blocked_reasons:
        blocked_reasons = ["missing_approval"]
    if binding_status in {"bound", "not_applicable"}:
        blocked_reasons = []
    blocked_reason = blocked_reasons[0] if blocked_reasons else ""

    binding_manual_required = bool(
        repair_plan_manual_required
        or binding_decision == "manual_review_required"
        or "manual_intervention_required" in reason_codes
    )
    binding_replan_required = bool(
        repair_plan_replan_required
        or binding_decision == "request_replan"
        or "replan_required" in reason_codes
    )
    binding_truth_gathering_required = bool(repair_plan_truth_gathering_required)

    if binding_status == "not_applicable":
        binding_manual_required = False
        binding_replan_required = False
        binding_truth_gathering_required = False

    payload: dict[str, Any] = {
        "schema_version": REPAIR_APPROVAL_BINDING_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "repair_plan_status": repair_plan_status or "missing",
        "approval_status": approval_status or "absent",
        "repair_approval_binding_status": binding_status,
        "repair_approval_binding_decision": binding_decision,
        "repair_approval_binding_scope": binding_scope,
        "repair_approval_binding_validity": binding_validity,
        "repair_approval_binding_compatibility_status": binding_compatibility,
        "repair_approval_binding_primary_reason": binding_primary_reason,
        "repair_approval_binding_reason_codes": reason_codes,
        "repair_approval_binding_blocked_reason": blocked_reason,
        "repair_approval_binding_blocked_reasons": blocked_reasons,
        "repair_approval_binding_manual_required": bool(binding_manual_required),
        "repair_approval_binding_replan_required": bool(binding_replan_required),
        "repair_approval_binding_truth_gathering_required": bool(binding_truth_gathering_required),
        "repair_approval_binding_execution_authorized": False,
        "repair_approval_binding_source_status": binding_source_status,
        "repair_approval_binding_plan_status": repair_plan_status or "missing",
        "repair_approval_binding_plan_action": repair_plan_action or "no_action",
        "repair_approval_binding_approval_decision": approval_decision or "none",
        "supporting_compact_truth_refs": _build_supporting_refs(
            next_safe_action=next_safe_action,
            policy_primary_action=policy_primary_action,
            lifecycle_closure_status=lifecycle_closure_status,
            lifecycle_primary_closure_issue=lifecycle_primary_closure_issue,
            policy_status=policy_status,
            completion_status=completion_status,
            closure_decision=closure_decision,
            approval_status=approval_status,
            approval_transport_status=approval_transport_status,
            repair_plan_status=repair_plan_status,
            repair_plan_candidate_action=repair_plan_action,
            repair_plan_primary_reason=repair_plan_primary_reason,
            repair_suggestion_status=repair_suggestion_status,
            reconcile_status=reconcile_status,
            objective_status=objective_status,
        ),
    }

    if requested_outcome:
        payload["requested_outcome"] = requested_outcome
    if objective_summary:
        payload["objective_summary"] = objective_summary
    if completion_blocked_reason:
        payload["completion_blocked_reason"] = completion_blocked_reason
    if approval_blocked_reason:
        payload["approval_blocked_reason"] = approval_blocked_reason
    if reconcile_primary_mismatch:
        payload["reconcile_primary_mismatch"] = reconcile_primary_mismatch
    if next_safe_action:
        payload["next_safe_action"] = next_safe_action
    if policy_primary_action:
        payload["policy_primary_action"] = policy_primary_action

    return payload


def build_repair_approval_binding_run_state_summary_surface(
    repair_approval_binding_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(repair_approval_binding_payload or {})

    status = _normalize_text(payload.get("repair_approval_binding_status"), default="")
    decision = _normalize_text(payload.get("repair_approval_binding_decision"), default="")
    scope = _normalize_text(payload.get("repair_approval_binding_scope"), default="")
    validity = _normalize_text(payload.get("repair_approval_binding_validity"), default="")
    compatibility = _normalize_text(
        payload.get("repair_approval_binding_compatibility_status"),
        default="",
    )
    primary_reason = _normalize_text(
        payload.get("repair_approval_binding_primary_reason"),
        default="",
    )
    manual_required = _normalize_bool(
        payload.get("repair_approval_binding_manual_required")
    )
    replan_required = _normalize_bool(
        payload.get("repair_approval_binding_replan_required")
    )
    truth_gathering_required = _normalize_bool(
        payload.get("repair_approval_binding_truth_gathering_required")
    )

    present = bool(payload.get("repair_approval_binding_present", False)) or bool(
        status or decision or scope
    )

    if not status:
        status = "missing"
    if not decision:
        decision = "hold_unbound"
    if not scope:
        scope = "current_repair_posture"
    if not validity:
        validity = "insufficient_truth"
    if not compatibility:
        compatibility = "insufficient_truth"

    status = _normalize_enum(
        status,
        allowed=REPAIR_APPROVAL_BINDING_STATUSES,
        default="missing",
    )
    decision = _normalize_enum(
        decision,
        allowed=REPAIR_APPROVAL_BINDING_DECISIONS,
        default="hold_unbound",
    )
    scope = _normalize_enum(
        scope,
        allowed=REPAIR_APPROVAL_BINDING_SCOPES,
        default="current_repair_posture",
    )
    validity = _normalize_enum(
        validity,
        allowed=REPAIR_APPROVAL_BINDING_VALIDITIES,
        default="insufficient_truth",
    )
    compatibility = _normalize_enum(
        compatibility,
        allowed=REPAIR_APPROVAL_BINDING_COMPATIBILITY_STATUSES,
        default="insufficient_truth",
    )

    if status == "not_applicable":
        decision = "no_binding"
        scope = "none"
        validity = "valid"
        compatibility = "compatible"
        primary_reason = "no_reason"
        manual_required = False
        replan_required = False
        truth_gathering_required = False
    elif not primary_reason or primary_reason not in REPAIR_APPROVAL_BINDING_REASON_CODES:
        if status == "missing":
            primary_reason = "missing_approval"
        elif status == "partially_bound":
            primary_reason = "approval_scope_mismatch"
        elif status == "blocked":
            primary_reason = "approval_conflict"
        else:
            primary_reason = "insufficient_upstream_truth"

    return {
        "repair_approval_binding_present": bool(present),
        "repair_approval_binding_status": status,
        "repair_approval_binding_decision": decision,
        "repair_approval_binding_scope": scope,
        "repair_approval_binding_validity": validity,
        "repair_approval_binding_compatibility_status": compatibility,
        "repair_approval_binding_primary_reason": primary_reason,
        "repair_approval_binding_manual_required": bool(manual_required),
        "repair_approval_binding_replan_required": bool(replan_required),
        "repair_approval_binding_truth_gathering_required": bool(
            truth_gathering_required
        ),
    }

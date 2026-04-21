from __future__ import annotations

from typing import Any
from typing import Mapping

BOUNDED_EXECUTION_BRIDGE_SCHEMA_VERSION = "v1"

BOUNDED_EXECUTION_STATUSES = {
    "ready",
    "blocked",
    "deferred",
    "not_applicable",
    "insufficient_truth",
}

BOUNDED_EXECUTION_DECISIONS = {
    "attempt_bounded_execution",
    "hold_blocked",
    "hold_deferred",
    "manual_review_required",
    "request_replan",
    "no_execution",
}

BOUNDED_EXECUTION_SCOPES = {
    "current_repair_plan_candidate",
    "current_bound_repair_posture",
    "manual_review_only",
    "replan_only",
    "none",
}

BOUNDED_EXECUTION_CANDIDATE_ACTIONS = {
    "attempt_truth_gathering_step",
    "attempt_manual_review_preparation",
    "attempt_replan_preparation",
    "attempt_closure_followup_step",
    "no_action",
}

BOUNDED_EXECUTION_VALIDITIES = {
    "valid",
    "stale",
    "superseded",
    "invalid",
    "insufficient_truth",
}

BOUNDED_EXECUTION_CONFIDENCE_LEVELS = {
    "strong",
    "partial",
    "conservative_low",
}

BOUNDED_EXECUTION_SOURCE_STATUSES = {
    "derived_from_execution_authorization",
    "derived_from_binding_and_plan",
    "derived_from_cross_surface_truth",
    "insufficient_truth",
}

BOUNDED_EXECUTION_REASON_CODES = {
    "authorization_not_eligible",
    "authorization_denied",
    "authorization_pending",
    "authorization_insufficient",
    "binding_invalid",
    "binding_stale",
    "binding_superseded",
    "plan_not_available",
    "plan_not_needed",
    "manual_intervention_required",
    "replan_required",
    "truth_gathering_required",
    "bounded_execution_ready",
    "no_reason",
}

BOUNDED_EXECUTION_REASON_ORDER = (
    "authorization_not_eligible",
    "authorization_denied",
    "authorization_pending",
    "authorization_insufficient",
    "binding_invalid",
    "binding_stale",
    "binding_superseded",
    "plan_not_available",
    "plan_not_needed",
    "manual_intervention_required",
    "replan_required",
    "truth_gathering_required",
    "bounded_execution_ready",
    "no_reason",
)

BOUNDED_EXECUTION_BRIDGE_RUN_STATE_SUMMARY_SAFE_FIELDS = (
    "bounded_execution_bridge_present",
    "bounded_execution_status",
    "bounded_execution_decision",
    "bounded_execution_scope",
    "bounded_execution_validity",
    "bounded_execution_confidence",
    "bounded_execution_primary_reason",
    "bounded_execution_manual_required",
    "bounded_execution_replan_required",
    "bounded_execution_truth_gathering_required",
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
    "repair_approval_binding.repair_approval_binding_status",
    "repair_approval_binding.repair_approval_binding_validity",
    "execution_authorization_gate.execution_authorization_status",
    "execution_authorization_gate.execution_authorization_validity",
    "execution_authorization_gate.execution_authorization_primary_reason",
    "repair_suggestion_contract.repair_suggestion_status",
    "reconcile_contract.reconcile_status",
    "objective_contract.objective_status",
)

_PLAN_ACTION_TO_BOUNDED_CANDIDATE_ACTION = {
    "gather_missing_truth": "attempt_truth_gathering_step",
    "request_manual_review": "attempt_manual_review_preparation",
    "request_replan": "attempt_replan_preparation",
    "request_closure_followup": "attempt_closure_followup_step",
    "no_action": "no_action",
}

_SUGGESTION_DECISION_TO_BOUNDED_CANDIDATE_ACTION = {
    "gather_truth": "attempt_truth_gathering_step",
    "manual_review": "attempt_manual_review_preparation",
    "request_replan": "attempt_replan_preparation",
    "closure_followup": "attempt_closure_followup_step",
    "hold": "no_action",
    "no_action": "no_action",
}

_BINDING_SCOPE_TO_BOUNDED_SCOPE = {
    "current_plan_candidate": "current_repair_plan_candidate",
    "current_repair_posture": "current_bound_repair_posture",
    "manual_review_only": "manual_review_only",
    "replan_only": "replan_only",
    "none": "none",
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
    for reason in BOUNDED_EXECUTION_REASON_ORDER:
        if reason in filtered and reason in BOUNDED_EXECUTION_REASON_CODES:
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
    repair_approval_binding_status: str,
    repair_approval_binding_validity: str,
    execution_authorization_status: str,
    execution_authorization_validity: str,
    execution_authorization_primary_reason: str,
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
    if repair_approval_binding_status:
        refs.append("repair_approval_binding.repair_approval_binding_status")
    if repair_approval_binding_validity:
        refs.append("repair_approval_binding.repair_approval_binding_validity")
    if execution_authorization_status:
        refs.append("execution_authorization_gate.execution_authorization_status")
    if execution_authorization_validity:
        refs.append("execution_authorization_gate.execution_authorization_validity")
    if execution_authorization_primary_reason:
        refs.append("execution_authorization_gate.execution_authorization_primary_reason")
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


def _derive_source_status(
    *,
    execution_authorization_present: bool,
    binding_present: bool,
    plan_present: bool,
    cross_surface_present: bool,
) -> str:
    if execution_authorization_present:
        return "derived_from_execution_authorization"
    if binding_present and plan_present:
        return "derived_from_binding_and_plan"
    if cross_surface_present:
        return "derived_from_cross_surface_truth"
    return "insufficient_truth"


def build_bounded_execution_bridge_surface(
    *,
    run_id: str,
    objective_contract_payload: Mapping[str, Any] | None,
    completion_contract_payload: Mapping[str, Any] | None,
    approval_transport_payload: Mapping[str, Any] | None,
    reconcile_contract_payload: Mapping[str, Any] | None,
    repair_suggestion_contract_payload: Mapping[str, Any] | None,
    repair_plan_transport_payload: Mapping[str, Any] | None,
    repair_approval_binding_payload: Mapping[str, Any] | None,
    execution_authorization_gate_payload: Mapping[str, Any] | None,
    run_state_payload: Mapping[str, Any] | None,
    artifact_presence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    objective = dict(objective_contract_payload or {})
    completion = dict(completion_contract_payload or {})
    approval = dict(approval_transport_payload or {})
    reconcile = dict(reconcile_contract_payload or {})
    repair_suggestion = dict(repair_suggestion_contract_payload or {})
    repair_plan = dict(repair_plan_transport_payload or {})
    repair_binding = dict(repair_approval_binding_payload or {})
    execution_authorization = dict(execution_authorization_gate_payload or {})
    run_state = dict(run_state_payload or {})
    artifacts = dict(artifact_presence or {})

    objective_id = _normalize_text(
        objective.get("objective_id")
        or completion.get("objective_id")
        or approval.get("objective_id")
        or reconcile.get("objective_id")
        or repair_suggestion.get("objective_id")
        or repair_plan.get("objective_id")
        or repair_binding.get("objective_id")
        or execution_authorization.get("objective_id")
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
    approval_transport_status = _normalize_text(
        approval.get("approval_transport_status") or run_state.get("approval_transport_status"),
        default="",
    )
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
    reconcile_decision = _normalize_text(
        reconcile.get("reconcile_decision") or run_state.get("reconcile_decision"),
        default="",
    )

    repair_suggestion_status = _normalize_text(
        repair_suggestion.get("repair_suggestion_status") or run_state.get("repair_suggestion_status"),
        default="",
    )
    repair_suggestion_decision = _normalize_text(
        repair_suggestion.get("repair_suggestion_decision") or run_state.get("repair_suggestion_decision"),
        default="",
    )

    repair_plan_status = _normalize_text(
        repair_plan.get("repair_plan_status") or run_state.get("repair_plan_status"),
        default="",
    )
    repair_plan_candidate_action = _normalize_text(
        repair_plan.get("repair_plan_candidate_action") or run_state.get("repair_plan_candidate_action"),
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

    binding_status = _normalize_text(
        repair_binding.get("repair_approval_binding_status")
        or run_state.get("repair_approval_binding_status"),
        default="",
    )
    binding_scope = _normalize_text(
        repair_binding.get("repair_approval_binding_scope")
        or run_state.get("repair_approval_binding_scope"),
        default="",
    )
    binding_validity = _normalize_text(
        repair_binding.get("repair_approval_binding_validity")
        or run_state.get("repair_approval_binding_validity"),
        default="",
    )
    binding_manual_required = _normalize_bool(
        repair_binding.get("repair_approval_binding_manual_required")
        if "repair_approval_binding_manual_required" in repair_binding
        else run_state.get("repair_approval_binding_manual_required")
    )
    binding_replan_required = _normalize_bool(
        repair_binding.get("repair_approval_binding_replan_required")
        if "repair_approval_binding_replan_required" in repair_binding
        else run_state.get("repair_approval_binding_replan_required")
    )
    binding_truth_gathering_required = _normalize_bool(
        repair_binding.get("repair_approval_binding_truth_gathering_required")
        if "repair_approval_binding_truth_gathering_required" in repair_binding
        else run_state.get("repair_approval_binding_truth_gathering_required")
    )

    execution_authorization_status = _normalize_text(
        execution_authorization.get("execution_authorization_status")
        or run_state.get("execution_authorization_status"),
        default="",
    )
    execution_authorization_decision = _normalize_text(
        execution_authorization.get("execution_authorization_decision")
        or run_state.get("execution_authorization_decision"),
        default="",
    )
    execution_authorization_scope = _normalize_text(
        execution_authorization.get("execution_authorization_scope")
        or run_state.get("execution_authorization_scope"),
        default="",
    )
    execution_authorization_validity = _normalize_text(
        execution_authorization.get("execution_authorization_validity")
        or run_state.get("execution_authorization_validity"),
        default="",
    )
    execution_authorization_primary_reason = _normalize_text(
        execution_authorization.get("execution_authorization_primary_reason")
        or run_state.get("execution_authorization_primary_reason"),
        default="",
    )
    execution_authorization_denied = _normalize_bool(
        execution_authorization.get("execution_authorization_denied")
        if "execution_authorization_denied" in execution_authorization
        else run_state.get("execution_authorization_denied")
    )
    execution_authorization_eligible = _normalize_bool(
        execution_authorization.get("execution_authorization_eligible")
        if "execution_authorization_eligible" in execution_authorization
        else run_state.get("execution_authorization_eligible")
    )
    execution_authorization_manual_required = _normalize_bool(
        execution_authorization.get("execution_authorization_manual_required")
        if "execution_authorization_manual_required" in execution_authorization
        else run_state.get("execution_authorization_manual_required")
    )
    execution_authorization_replan_required = _normalize_bool(
        execution_authorization.get("execution_authorization_replan_required")
        if "execution_authorization_replan_required" in execution_authorization
        else run_state.get("execution_authorization_replan_required")
    )
    execution_authorization_truth_gathering_required = _normalize_bool(
        execution_authorization.get("execution_authorization_truth_gathering_required")
        if "execution_authorization_truth_gathering_required" in execution_authorization
        else run_state.get("execution_authorization_truth_gathering_required")
    )

    next_safe_action = _normalize_text(run_state.get("next_safe_action"), default="")
    policy_primary_action = _normalize_text(run_state.get("policy_primary_action"), default="")
    policy_status = _normalize_text(run_state.get("policy_status"), default="")
    lifecycle_closure_status = _normalize_text(run_state.get("lifecycle_closure_status"), default="")
    lifecycle_primary_closure_issue = _normalize_text(
        run_state.get("lifecycle_primary_closure_issue"),
        default="",
    )

    execution_authorization_present = (
        bool(execution_authorization)
        or _normalize_bool(run_state.get("execution_authorization_gate_present"))
        or _normalize_bool(artifacts.get("execution_authorization_gate.json"))
    )
    binding_present = (
        bool(repair_binding)
        or _normalize_bool(run_state.get("repair_approval_binding_present"))
        or _normalize_bool(artifacts.get("repair_approval_binding.json"))
    )
    plan_present = (
        bool(repair_plan)
        or _normalize_bool(run_state.get("repair_plan_transport_present"))
        or _normalize_bool(artifacts.get("repair_plan_transport.json"))
    )
    cross_surface_present = bool(
        objective
        or completion
        or approval
        or reconcile
        or repair_suggestion
        or run_state
        or _normalize_bool(artifacts.get("run_state.json"))
    )

    plan_not_needed = repair_plan_status == "not_needed"
    plan_not_available = repair_plan_status in {"", "blocked", "insufficient_truth"}
    candidate_action = _PLAN_ACTION_TO_BOUNDED_CANDIDATE_ACTION.get(
        repair_plan_candidate_action,
        "",
    )
    if not candidate_action:
        candidate_action = _SUGGESTION_DECISION_TO_BOUNDED_CANDIDATE_ACTION.get(
            repair_suggestion_decision,
            "no_action",
        )
    candidate_action = _normalize_enum(
        candidate_action,
        allowed=BOUNDED_EXECUTION_CANDIDATE_ACTIONS,
        default="no_action",
    )

    explicit_denial = bool(
        execution_authorization_denied
        or execution_authorization_status == "denied"
        or approval_status == "denied"
        or approval_decision == "deny"
    )
    authorization_eligible = bool(
        execution_authorization_status == "eligible"
        or execution_authorization_eligible
    )

    manual_required = bool(
        execution_authorization_manual_required
        or binding_manual_required
        or repair_plan_manual_required
        or _normalize_bool(run_state.get("manual_intervention_required"))
        or _normalize_bool(run_state.get("policy_manual_required"))
    )
    replan_required = bool(
        execution_authorization_replan_required
        or binding_replan_required
        or repair_plan_replan_required
        or _normalize_bool(run_state.get("policy_replan_required"))
        or reconcile_decision == "request_replan"
        or execution_authorization_decision == "request_replan"
        or repair_plan_candidate_action == "request_replan"
        or repair_suggestion_decision == "request_replan"
    )
    truth_gathering_required = bool(
        execution_authorization_truth_gathering_required
        or binding_truth_gathering_required
        or repair_plan_truth_gathering_required
        or _normalize_bool(run_state.get("repair_truth_gathering_required"))
        or reconcile_status == "waiting_for_truth"
        or repair_suggestion_decision == "gather_truth"
    )

    coherent_waiting_posture = bool(
        execution_authorization_status == "pending"
        or truth_gathering_required
        or binding_status in {"missing", "partially_bound"}
        or execution_authorization_primary_reason in {"missing_binding", "approval_missing"}
    )
    coherent_candidate_action = bool(candidate_action and candidate_action != "no_action")

    missing_upstream_truth = bool(
        not cross_surface_present
        or not objective_status
        or not completion_status
        or not approval_transport_status
        or not repair_plan_status
        or not execution_authorization_status
    )

    binding_invalid = bool(binding_validity == "invalid" or binding_status == "blocked")
    binding_stale = binding_validity == "stale"
    binding_superseded = binding_validity == "superseded"

    if plan_not_needed:
        bounded_status = "not_applicable"
    elif explicit_denial:
        bounded_status = "blocked"
    elif replan_required:
        bounded_status = "blocked"
    elif manual_required:
        bounded_status = "blocked"
    elif authorization_eligible:
        if execution_authorization_validity not in {"valid", ""}:
            bounded_status = "blocked"
        elif binding_stale or binding_superseded or binding_invalid:
            bounded_status = "blocked"
        elif plan_not_available:
            bounded_status = "blocked"
        elif truth_gathering_required:
            bounded_status = "deferred"
        elif not coherent_candidate_action:
            bounded_status = "insufficient_truth"
        elif missing_upstream_truth:
            bounded_status = "insufficient_truth"
        else:
            bounded_status = "ready"
    elif execution_authorization_status == "pending":
        if coherent_waiting_posture and (plan_present or coherent_candidate_action):
            bounded_status = "deferred"
        elif missing_upstream_truth:
            bounded_status = "insufficient_truth"
        else:
            bounded_status = "deferred"
    elif execution_authorization_status in {"blocked", "denied"}:
        bounded_status = "blocked"
    elif execution_authorization_status in {"insufficient_truth", ""}:
        if coherent_waiting_posture and plan_present and not plan_not_available:
            bounded_status = "deferred"
        else:
            bounded_status = "insufficient_truth"
    else:
        bounded_status = "insufficient_truth"

    bounded_status = _normalize_enum(
        bounded_status,
        allowed=BOUNDED_EXECUTION_STATUSES,
        default="insufficient_truth",
    )

    if bounded_status == "ready":
        bounded_decision = "attempt_bounded_execution"
    elif bounded_status == "not_applicable":
        bounded_decision = "no_execution"
    elif bounded_status == "deferred":
        bounded_decision = "hold_deferred"
    elif replan_required:
        bounded_decision = "request_replan"
    elif manual_required:
        bounded_decision = "manual_review_required"
    elif bounded_status == "insufficient_truth":
        bounded_decision = "hold_deferred"
    else:
        bounded_decision = "hold_blocked"

    bounded_decision = _normalize_enum(
        bounded_decision,
        allowed=BOUNDED_EXECUTION_DECISIONS,
        default="hold_deferred",
    )

    auth_scope = _normalize_enum(
        execution_authorization_scope,
        allowed=BOUNDED_EXECUTION_SCOPES,
        default="none",
    )
    derived_binding_scope = _BINDING_SCOPE_TO_BOUNDED_SCOPE.get(binding_scope, "none")
    if bounded_status == "not_applicable":
        bounded_scope = "none"
    elif (
        replan_required
        or auth_scope == "replan_only"
        or derived_binding_scope == "replan_only"
        or repair_plan_candidate_action == "request_replan"
        or repair_suggestion_decision == "request_replan"
    ):
        bounded_scope = "replan_only"
    elif (
        manual_required
        or auth_scope == "manual_review_only"
        or derived_binding_scope == "manual_review_only"
        or repair_plan_candidate_action == "request_manual_review"
        or repair_suggestion_decision == "manual_review"
    ):
        bounded_scope = "manual_review_only"
    elif bounded_status == "ready":
        bounded_scope = auth_scope if auth_scope != "none" else derived_binding_scope
        if bounded_scope == "none":
            bounded_scope = "current_repair_plan_candidate"
    elif auth_scope != "none":
        bounded_scope = auth_scope
    elif derived_binding_scope != "none":
        bounded_scope = derived_binding_scope
    elif repair_plan_status == "available":
        bounded_scope = "current_bound_repair_posture"
    else:
        bounded_scope = "none"

    bounded_scope = _normalize_enum(
        bounded_scope,
        allowed=BOUNDED_EXECUTION_SCOPES,
        default="none",
    )

    if bounded_status == "not_applicable":
        bounded_validity = "valid"
    elif binding_superseded or execution_authorization_validity == "superseded":
        bounded_validity = "superseded"
    elif binding_stale or execution_authorization_validity == "stale":
        bounded_validity = "stale"
    elif explicit_denial or binding_invalid or execution_authorization_validity == "invalid":
        bounded_validity = "invalid"
    elif bounded_status == "ready":
        bounded_validity = "valid"
    elif execution_authorization_validity in BOUNDED_EXECUTION_VALIDITIES:
        bounded_validity = execution_authorization_validity
    else:
        bounded_validity = "insufficient_truth"

    bounded_validity = _normalize_enum(
        bounded_validity,
        allowed=BOUNDED_EXECUTION_VALIDITIES,
        default="insufficient_truth",
    )

    reason_candidates: list[str] = []
    if not authorization_eligible:
        if explicit_denial:
            reason_candidates.append("authorization_denied")
        elif execution_authorization_status == "pending":
            reason_candidates.append("authorization_pending")
        elif execution_authorization_status in {"", "insufficient_truth"}:
            reason_candidates.append("authorization_insufficient")
        else:
            reason_candidates.append("authorization_not_eligible")
    if binding_invalid:
        reason_candidates.append("binding_invalid")
    if binding_stale:
        reason_candidates.append("binding_stale")
    if binding_superseded:
        reason_candidates.append("binding_superseded")
    if plan_not_available:
        reason_candidates.append("plan_not_available")
    if plan_not_needed:
        reason_candidates.append("plan_not_needed")
    if manual_required:
        reason_candidates.append("manual_intervention_required")
    if replan_required:
        reason_candidates.append("replan_required")
    if truth_gathering_required:
        reason_candidates.append("truth_gathering_required")
    if bounded_status == "ready":
        reason_candidates.insert(0, "bounded_execution_ready")

    reason_codes = _normalize_reason_codes(reason_candidates)
    if bounded_status == "ready":
        if "bounded_execution_ready" not in reason_codes:
            reason_codes = ["bounded_execution_ready"]
        elif reason_codes[0] != "bounded_execution_ready":
            ordered = ["bounded_execution_ready"]
            ordered.extend([code for code in reason_codes if code != "bounded_execution_ready"])
            reason_codes = ordered
    elif bounded_status == "not_applicable":
        reason_codes = ["no_reason"]
    elif not reason_codes:
        if bounded_status == "deferred":
            reason_codes = ["authorization_pending"]
        elif bounded_status == "blocked" and explicit_denial:
            reason_codes = ["authorization_denied"]
        elif bounded_status == "blocked":
            reason_codes = ["authorization_not_eligible"]
        else:
            reason_codes = ["authorization_insufficient"]

    primary_reason = reason_codes[0] if reason_codes else "authorization_insufficient"

    blocked_reasons: list[str] = []
    if bounded_status not in {"ready", "not_applicable"}:
        blocked_reasons = _normalize_reason_codes(
            [code for code in reason_codes if code not in {"bounded_execution_ready", "no_reason"}]
        )
    if bounded_status == "blocked" and explicit_denial and not blocked_reasons:
        blocked_reasons = ["authorization_denied"]
    if bounded_status == "deferred" and not blocked_reasons:
        blocked_reasons = ["authorization_pending"]
    if bounded_status == "insufficient_truth" and not blocked_reasons:
        blocked_reasons = ["authorization_insufficient"]
    blocked_reason = blocked_reasons[0] if blocked_reasons else ""

    source_status = _normalize_enum(
        _derive_source_status(
            execution_authorization_present=execution_authorization_present,
            binding_present=binding_present,
            plan_present=plan_present,
            cross_surface_present=cross_surface_present,
        ),
        allowed=BOUNDED_EXECUTION_SOURCE_STATUSES,
        default="insufficient_truth",
    )

    if (
        bounded_status == "ready"
        and bounded_validity == "valid"
        and authorization_eligible
        and not explicit_denial
        and not manual_required
        and not replan_required
        and not truth_gathering_required
    ):
        bounded_confidence = "strong"
    elif bounded_validity == "valid" and bounded_status in {"deferred", "blocked", "not_applicable"}:
        bounded_confidence = "partial"
    else:
        bounded_confidence = "conservative_low"

    bounded_confidence = _normalize_enum(
        bounded_confidence,
        allowed=BOUNDED_EXECUTION_CONFIDENCE_LEVELS,
        default="conservative_low",
    )

    bounded_ready = bounded_status == "ready"
    bounded_deferred = bounded_status == "deferred"
    bounded_denied = bool(explicit_denial and bounded_status == "blocked")

    if bounded_status == "ready":
        manual_required = False
        replan_required = False
        truth_gathering_required = False
        bounded_denied = False
    elif bounded_status == "not_applicable":
        manual_required = False
        replan_required = False
        truth_gathering_required = False
        bounded_denied = False
        candidate_action = "no_action"
    elif not explicit_denial:
        bounded_denied = False

    payload: dict[str, Any] = {
        "schema_version": BOUNDED_EXECUTION_BRIDGE_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "bounded_execution_status": bounded_status,
        "bounded_execution_decision": bounded_decision,
        "bounded_execution_scope": bounded_scope,
        "bounded_execution_candidate_action": candidate_action,
        "bounded_execution_validity": bounded_validity,
        "bounded_execution_confidence": bounded_confidence,
        "bounded_execution_primary_reason": primary_reason,
        "bounded_execution_reason_codes": reason_codes,
        "bounded_execution_blocked_reason": blocked_reason,
        "bounded_execution_blocked_reasons": blocked_reasons,
        "bounded_execution_manual_required": bool(manual_required),
        "bounded_execution_replan_required": bool(replan_required),
        "bounded_execution_truth_gathering_required": bool(truth_gathering_required),
        "bounded_execution_ready": bool(bounded_ready),
        "bounded_execution_deferred": bool(bounded_deferred),
        "bounded_execution_denied": bool(bounded_denied),
        "bounded_execution_source_status": source_status,
        "bounded_execution_authorization_status": (
            execution_authorization_status or "insufficient_truth"
        ),
        "bounded_execution_binding_status": binding_status or "missing",
        "bounded_execution_plan_status": repair_plan_status or "missing",
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
            repair_plan_candidate_action=repair_plan_candidate_action,
            repair_approval_binding_status=binding_status,
            repair_approval_binding_validity=binding_validity,
            execution_authorization_status=execution_authorization_status,
            execution_authorization_validity=execution_authorization_validity,
            execution_authorization_primary_reason=execution_authorization_primary_reason,
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


def build_bounded_execution_bridge_run_state_summary_surface(
    bounded_execution_bridge_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(bounded_execution_bridge_payload or {})

    status = _normalize_text(payload.get("bounded_execution_status"), default="")
    decision = _normalize_text(payload.get("bounded_execution_decision"), default="")
    scope = _normalize_text(payload.get("bounded_execution_scope"), default="")
    validity = _normalize_text(payload.get("bounded_execution_validity"), default="")
    confidence = _normalize_text(payload.get("bounded_execution_confidence"), default="")
    primary_reason = _normalize_text(payload.get("bounded_execution_primary_reason"), default="")
    manual_required = _normalize_bool(payload.get("bounded_execution_manual_required"))
    replan_required = _normalize_bool(payload.get("bounded_execution_replan_required"))
    truth_gathering_required = _normalize_bool(
        payload.get("bounded_execution_truth_gathering_required")
    )

    present = bool(payload.get("bounded_execution_bridge_present", False)) or bool(
        status or decision or scope
    )

    if not status:
        status = "insufficient_truth"
    if not decision:
        if status == "ready":
            decision = "attempt_bounded_execution"
        elif status == "deferred":
            decision = "hold_deferred"
        elif status == "not_applicable":
            decision = "no_execution"
        else:
            decision = "hold_blocked"
    if not scope:
        scope = "none"
    if not validity:
        validity = "insufficient_truth"
    if not confidence:
        confidence = "strong" if status == "ready" else "conservative_low"

    status = _normalize_enum(
        status,
        allowed=BOUNDED_EXECUTION_STATUSES,
        default="insufficient_truth",
    )
    decision = _normalize_enum(
        decision,
        allowed=BOUNDED_EXECUTION_DECISIONS,
        default="hold_deferred",
    )
    scope = _normalize_enum(
        scope,
        allowed=BOUNDED_EXECUTION_SCOPES,
        default="none",
    )
    validity = _normalize_enum(
        validity,
        allowed=BOUNDED_EXECUTION_VALIDITIES,
        default="insufficient_truth",
    )
    confidence = _normalize_enum(
        confidence,
        allowed=BOUNDED_EXECUTION_CONFIDENCE_LEVELS,
        default="conservative_low",
    )

    if status == "ready":
        decision = "attempt_bounded_execution"
        scope = "current_repair_plan_candidate" if scope == "none" else scope
        validity = "valid"
        primary_reason = "bounded_execution_ready"
        manual_required = False
        replan_required = False
        truth_gathering_required = False
    elif status == "not_applicable":
        decision = "no_execution"
        scope = "none"
        validity = "valid"
        primary_reason = "no_reason"
        manual_required = False
        replan_required = False
        truth_gathering_required = False
    elif not primary_reason or primary_reason not in BOUNDED_EXECUTION_REASON_CODES:
        if status == "deferred":
            primary_reason = "authorization_pending"
        elif status == "blocked":
            primary_reason = "authorization_not_eligible"
        else:
            primary_reason = "authorization_insufficient"

    return {
        "bounded_execution_bridge_present": bool(present),
        "bounded_execution_status": status,
        "bounded_execution_decision": decision,
        "bounded_execution_scope": scope,
        "bounded_execution_validity": validity,
        "bounded_execution_confidence": confidence,
        "bounded_execution_primary_reason": primary_reason,
        "bounded_execution_manual_required": bool(manual_required),
        "bounded_execution_replan_required": bool(replan_required),
        "bounded_execution_truth_gathering_required": bool(truth_gathering_required),
    }

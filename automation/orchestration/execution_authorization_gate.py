from __future__ import annotations

from typing import Any
from typing import Mapping

EXECUTION_AUTHORIZATION_GATE_SCHEMA_VERSION = "v1"

EXECUTION_AUTHORIZATION_STATUSES = {
    "eligible",
    "blocked",
    "pending",
    "denied",
    "insufficient_truth",
}

EXECUTION_AUTHORIZATION_DECISIONS = {
    "authorize_future_execution",
    "hold_blocked",
    "hold_pending",
    "deny_execution",
    "request_replan",
}

EXECUTION_AUTHORIZATION_SCOPES = {
    "current_repair_plan_candidate",
    "current_bound_repair_posture",
    "manual_review_only",
    "replan_only",
    "none",
}

EXECUTION_AUTHORIZATION_VALIDITIES = {
    "valid",
    "stale",
    "superseded",
    "invalid",
    "insufficient_truth",
}

EXECUTION_AUTHORIZATION_CONFIDENCE_LEVELS = {
    "strong",
    "partial",
    "conservative_low",
}

EXECUTION_AUTHORIZATION_SOURCE_STATUSES = {
    "derived_from_binding",
    "derived_from_plan_and_approval",
    "derived_from_cross_surface_truth",
    "insufficient_truth",
}

EXECUTION_AUTHORIZATION_REASON_CODES = {
    "missing_binding",
    "binding_blocked",
    "binding_invalid",
    "binding_stale",
    "binding_superseded",
    "approval_denied",
    "approval_missing",
    "plan_not_available",
    "plan_not_needed",
    "manual_intervention_required",
    "replan_required",
    "truth_gathering_required",
    "insufficient_upstream_truth",
    "authorization_ready",
    "no_reason",
}

EXECUTION_AUTHORIZATION_REASON_ORDER = (
    "missing_binding",
    "binding_blocked",
    "binding_invalid",
    "binding_stale",
    "binding_superseded",
    "approval_denied",
    "approval_missing",
    "plan_not_available",
    "plan_not_needed",
    "manual_intervention_required",
    "replan_required",
    "truth_gathering_required",
    "insufficient_upstream_truth",
    "authorization_ready",
    "no_reason",
)

EXECUTION_AUTHORIZATION_GATE_RUN_STATE_SUMMARY_SAFE_FIELDS = (
    "execution_authorization_gate_present",
    "execution_authorization_status",
    "execution_authorization_decision",
    "execution_authorization_scope",
    "execution_authorization_validity",
    "execution_authorization_confidence",
    "execution_authorization_primary_reason",
    "execution_authorization_manual_required",
    "execution_authorization_replan_required",
    "execution_authorization_truth_gathering_required",
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
    "repair_approval_binding.repair_approval_binding_primary_reason",
    "repair_suggestion_contract.repair_suggestion_status",
    "reconcile_contract.reconcile_status",
    "objective_contract.objective_status",
)

_BINDING_SCOPE_TO_AUTH_SCOPE = {
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
    for reason in EXECUTION_AUTHORIZATION_REASON_ORDER:
        if reason in filtered and reason in EXECUTION_AUTHORIZATION_REASON_CODES:
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
    repair_approval_binding_primary_reason: str,
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
    if repair_approval_binding_primary_reason:
        refs.append("repair_approval_binding.repair_approval_binding_primary_reason")
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
    binding_present: bool,
    plan_present: bool,
    approval_present: bool,
    cross_surface_present: bool,
) -> str:
    if binding_present:
        return "derived_from_binding"
    if plan_present and approval_present:
        return "derived_from_plan_and_approval"
    if cross_surface_present:
        return "derived_from_cross_surface_truth"
    return "insufficient_truth"


def build_execution_authorization_gate_surface(
    *,
    run_id: str,
    objective_contract_payload: Mapping[str, Any] | None,
    completion_contract_payload: Mapping[str, Any] | None,
    approval_transport_payload: Mapping[str, Any] | None,
    reconcile_contract_payload: Mapping[str, Any] | None,
    repair_suggestion_contract_payload: Mapping[str, Any] | None,
    repair_plan_transport_payload: Mapping[str, Any] | None,
    repair_approval_binding_payload: Mapping[str, Any] | None,
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
        or run_state.get("objective_id"),
        default="",
    )
    objective_summary = _normalize_text(
        objective.get("objective_summary")
        or run_state.get("objective_summary"),
        default="",
    )
    requested_outcome = _normalize_text(
        objective.get("requested_outcome")
        or run_state.get("requested_outcome"),
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
    reconcile_decision = _normalize_text(
        reconcile.get("reconcile_decision") or run_state.get("reconcile_decision"),
        default="",
    )
    reconcile_primary_mismatch = _normalize_text(
        reconcile.get("reconcile_primary_mismatch") or run_state.get("reconcile_primary_mismatch"),
        default="",
    )

    repair_suggestion_status = _normalize_text(
        repair_suggestion.get("repair_suggestion_status") or run_state.get("repair_suggestion_status"),
        default="",
    )

    repair_plan_status = _normalize_text(
        repair_plan.get("repair_plan_status") or run_state.get("repair_plan_status"),
        default="",
    )
    repair_plan_candidate_action = _normalize_text(
        repair_plan.get("repair_plan_candidate_action")
        or run_state.get("repair_plan_candidate_action"),
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
    binding_compatibility = _normalize_text(
        repair_binding.get("repair_approval_binding_compatibility_status")
        or run_state.get("repair_approval_binding_compatibility_status"),
        default="",
    )
    binding_primary_reason = _normalize_text(
        repair_binding.get("repair_approval_binding_primary_reason")
        or run_state.get("repair_approval_binding_primary_reason"),
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

    next_safe_action = _normalize_text(run_state.get("next_safe_action"), default="")
    policy_primary_action = _normalize_text(run_state.get("policy_primary_action"), default="")
    policy_status = _normalize_text(run_state.get("policy_status"), default="")
    lifecycle_closure_status = _normalize_text(run_state.get("lifecycle_closure_status"), default="")
    lifecycle_primary_closure_issue = _normalize_text(
        run_state.get("lifecycle_primary_closure_issue"),
        default="",
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
    approval_present = (
        bool(approval)
        or _normalize_bool(run_state.get("approval_transport_present"))
        or _normalize_bool(artifacts.get("approval_transport.json"))
    )
    cross_surface_present = bool(
        objective
        or completion
        or reconcile
        or repair_suggestion
        or run_state
        or _normalize_bool(artifacts.get("run_state.json"))
    )

    plan_not_needed = repair_plan_status == "not_needed"
    plan_not_available = repair_plan_status in {"", "blocked", "insufficient_truth"}
    approval_missing = approval_status in {"", "absent"} and approval_decision in {"", "none"}
    approval_denied = approval_status == "denied" or approval_decision == "deny"
    binding_missing = (not binding_present) or binding_status in {"", "missing"}
    binding_blocked = binding_status == "blocked"
    binding_invalid = binding_validity == "invalid" or binding_compatibility == "incompatible"
    binding_stale = binding_validity == "stale"
    binding_superseded = binding_validity == "superseded"
    binding_insufficient = (
        binding_validity in {"", "insufficient_truth"}
        or binding_compatibility in {"", "insufficient_truth"}
        or binding_status == "partially_bound"
    )

    manual_required = bool(
        binding_manual_required
        or repair_plan_manual_required
        or _normalize_bool(run_state.get("repair_manual_required"))
        or _normalize_bool(run_state.get("manual_intervention_required"))
        or _normalize_bool(run_state.get("policy_manual_required"))
    )
    replan_required = bool(
        binding_replan_required
        or repair_plan_replan_required
        or _normalize_bool(run_state.get("repair_replan_required"))
        or _normalize_bool(run_state.get("policy_replan_required"))
        or reconcile_decision == "request_replan"
    )
    truth_gathering_required = bool(
        binding_truth_gathering_required
        or repair_plan_truth_gathering_required
        or _normalize_bool(run_state.get("repair_truth_gathering_required"))
        or reconcile_status == "waiting_for_truth"
    )

    upstream_missing = bool(
        not cross_surface_present
        or not objective_status
        or not completion_status
        or not approval_transport_status
        or not repair_plan_status
        or not binding_status
    )

    if approval_denied:
        auth_status = "denied"
    elif replan_required:
        auth_status = "blocked"
    elif manual_required:
        auth_status = "blocked"
    elif truth_gathering_required:
        auth_status = "pending"
    elif plan_not_needed:
        auth_status = "pending"
    elif binding_blocked or binding_invalid or binding_stale or binding_superseded:
        auth_status = "blocked"
    elif binding_missing:
        auth_status = "pending"
    elif binding_insufficient:
        auth_status = "pending"
    elif upstream_missing and not binding_present:
        auth_status = "insufficient_truth"
    elif (
        binding_status == "bound"
        and binding_validity == "valid"
        and binding_compatibility == "compatible"
        and repair_plan_status == "available"
        and approval_status == "approved"
    ):
        auth_status = "eligible"
    elif upstream_missing:
        auth_status = "insufficient_truth"
    else:
        auth_status = "blocked"

    auth_status = _normalize_enum(
        auth_status,
        allowed=EXECUTION_AUTHORIZATION_STATUSES,
        default="insufficient_truth",
    )

    if auth_status == "eligible":
        auth_decision = "authorize_future_execution"
    elif auth_status == "denied":
        auth_decision = "deny_execution"
    elif replan_required:
        auth_decision = "request_replan"
    elif auth_status == "pending":
        auth_decision = "hold_pending"
    else:
        auth_decision = "hold_blocked"

    auth_decision = _normalize_enum(
        auth_decision,
        allowed=EXECUTION_AUTHORIZATION_DECISIONS,
        default="hold_pending",
    )

    derived_scope = _BINDING_SCOPE_TO_AUTH_SCOPE.get(binding_scope, "")
    if auth_status == "eligible":
        auth_scope = derived_scope or "current_repair_plan_candidate"
    elif auth_decision == "request_replan" or binding_scope == "replan_only":
        auth_scope = "replan_only"
    elif manual_required or binding_scope == "manual_review_only":
        auth_scope = "manual_review_only"
    elif plan_not_needed:
        auth_scope = "none"
    elif derived_scope:
        auth_scope = derived_scope
    else:
        auth_scope = "none"

    auth_scope = _normalize_enum(
        auth_scope,
        allowed=EXECUTION_AUTHORIZATION_SCOPES,
        default="none",
    )

    if auth_status == "eligible":
        auth_validity = "valid"
    elif binding_superseded:
        auth_validity = "superseded"
    elif binding_stale:
        auth_validity = "stale"
    elif approval_denied or binding_invalid:
        auth_validity = "invalid"
    elif binding_validity in EXECUTION_AUTHORIZATION_VALIDITIES:
        auth_validity = binding_validity
    else:
        auth_validity = "insufficient_truth"

    auth_validity = _normalize_enum(
        auth_validity,
        allowed=EXECUTION_AUTHORIZATION_VALIDITIES,
        default="insufficient_truth",
    )

    reason_candidates: list[str] = []
    if binding_missing:
        reason_candidates.append("missing_binding")
    if binding_blocked:
        reason_candidates.append("binding_blocked")
    if binding_invalid:
        reason_candidates.append("binding_invalid")
    if binding_stale:
        reason_candidates.append("binding_stale")
    if binding_superseded:
        reason_candidates.append("binding_superseded")
    if approval_denied:
        reason_candidates.append("approval_denied")
    if approval_missing:
        reason_candidates.append("approval_missing")
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
    if upstream_missing or binding_insufficient:
        reason_candidates.append("insufficient_upstream_truth")
    if auth_status == "eligible":
        reason_candidates.insert(0, "authorization_ready")

    reason_codes = _normalize_reason_codes(reason_candidates)
    if auth_status == "eligible":
        if "authorization_ready" not in reason_codes:
            reason_codes = ["authorization_ready"]
        elif reason_codes[0] != "authorization_ready":
            reordered = ["authorization_ready"]
            reordered.extend([code for code in reason_codes if code != "authorization_ready"])
            reason_codes = reordered
    elif not reason_codes:
        if auth_status == "denied":
            reason_codes = ["approval_denied"]
        elif auth_status == "pending":
            reason_codes = ["missing_binding"]
        elif auth_status == "blocked":
            reason_codes = ["binding_blocked"]
        else:
            reason_codes = ["insufficient_upstream_truth"]

    primary_reason = reason_codes[0] if reason_codes else "insufficient_upstream_truth"

    blocked_reasons: list[str] = []
    if auth_status != "eligible":
        blocked_reasons = _normalize_reason_codes(
            [code for code in reason_codes if code not in {"authorization_ready", "no_reason"}]
        )
    if auth_status == "eligible":
        blocked_reasons = []
    blocked_reason = blocked_reasons[0] if blocked_reasons else ""

    source_status = _normalize_enum(
        _derive_source_status(
            binding_present=binding_present,
            plan_present=plan_present,
            approval_present=approval_present,
            cross_surface_present=cross_surface_present,
        ),
        allowed=EXECUTION_AUTHORIZATION_SOURCE_STATUSES,
        default="insufficient_truth",
    )

    if auth_status == "eligible" and auth_validity == "valid" and not (
        manual_required or replan_required or truth_gathering_required
    ):
        auth_confidence = "strong"
    elif auth_status in {"eligible", "pending", "blocked"} and source_status != "insufficient_truth":
        auth_confidence = "partial"
    else:
        auth_confidence = "conservative_low"

    auth_confidence = _normalize_enum(
        auth_confidence,
        allowed=EXECUTION_AUTHORIZATION_CONFIDENCE_LEVELS,
        default="conservative_low",
    )

    payload: dict[str, Any] = {
        "schema_version": EXECUTION_AUTHORIZATION_GATE_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "execution_authorization_status": auth_status,
        "execution_authorization_decision": auth_decision,
        "execution_authorization_scope": auth_scope,
        "execution_authorization_validity": auth_validity,
        "execution_authorization_confidence": auth_confidence,
        "execution_authorization_primary_reason": primary_reason,
        "execution_authorization_reason_codes": reason_codes,
        "execution_authorization_blocked_reason": blocked_reason,
        "execution_authorization_blocked_reasons": blocked_reasons,
        "execution_authorization_manual_required": bool(manual_required),
        "execution_authorization_replan_required": bool(replan_required),
        "execution_authorization_truth_gathering_required": bool(truth_gathering_required),
        "execution_authorization_denied": auth_status == "denied",
        "execution_authorization_eligible": auth_status == "eligible",
        "execution_authorization_source_status": source_status,
        "execution_authorization_binding_status": binding_status or "missing",
        "execution_authorization_plan_status": repair_plan_status or "missing",
        "execution_authorization_approval_status": approval_status or "absent",
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
            repair_approval_binding_primary_reason=binding_primary_reason,
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


def build_execution_authorization_gate_run_state_summary_surface(
    execution_authorization_gate_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(execution_authorization_gate_payload or {})

    status = _normalize_text(payload.get("execution_authorization_status"), default="")
    decision = _normalize_text(payload.get("execution_authorization_decision"), default="")
    scope = _normalize_text(payload.get("execution_authorization_scope"), default="")
    validity = _normalize_text(payload.get("execution_authorization_validity"), default="")
    confidence = _normalize_text(payload.get("execution_authorization_confidence"), default="")
    primary_reason = _normalize_text(payload.get("execution_authorization_primary_reason"), default="")
    manual_required = _normalize_bool(payload.get("execution_authorization_manual_required"))
    replan_required = _normalize_bool(payload.get("execution_authorization_replan_required"))
    truth_gathering_required = _normalize_bool(
        payload.get("execution_authorization_truth_gathering_required")
    )

    present = bool(payload.get("execution_authorization_gate_present", False)) or bool(
        status or decision or scope
    )

    if not status:
        status = "insufficient_truth"
    if not decision:
        decision = "hold_pending" if status == "pending" else "hold_blocked"
    if not scope:
        scope = "none"
    if not validity:
        validity = "insufficient_truth"
    if not confidence:
        confidence = "strong" if status == "eligible" else "conservative_low"

    status = _normalize_enum(
        status,
        allowed=EXECUTION_AUTHORIZATION_STATUSES,
        default="insufficient_truth",
    )
    decision = _normalize_enum(
        decision,
        allowed=EXECUTION_AUTHORIZATION_DECISIONS,
        default="hold_pending",
    )
    scope = _normalize_enum(
        scope,
        allowed=EXECUTION_AUTHORIZATION_SCOPES,
        default="none",
    )
    validity = _normalize_enum(
        validity,
        allowed=EXECUTION_AUTHORIZATION_VALIDITIES,
        default="insufficient_truth",
    )
    confidence = _normalize_enum(
        confidence,
        allowed=EXECUTION_AUTHORIZATION_CONFIDENCE_LEVELS,
        default="conservative_low",
    )

    if status == "eligible":
        decision = "authorize_future_execution"
        validity = "valid"
        scope = "current_repair_plan_candidate" if scope == "none" else scope
        primary_reason = "authorization_ready"
        manual_required = False
        replan_required = False
        truth_gathering_required = False
    elif not primary_reason or primary_reason not in EXECUTION_AUTHORIZATION_REASON_CODES:
        if status == "denied":
            primary_reason = "approval_denied"
        elif status == "pending":
            primary_reason = "missing_binding"
        elif status == "blocked":
            primary_reason = "binding_blocked"
        else:
            primary_reason = "insufficient_upstream_truth"

    return {
        "execution_authorization_gate_present": bool(present),
        "execution_authorization_status": status,
        "execution_authorization_decision": decision,
        "execution_authorization_scope": scope,
        "execution_authorization_validity": validity,
        "execution_authorization_confidence": confidence,
        "execution_authorization_primary_reason": primary_reason,
        "execution_authorization_manual_required": bool(manual_required),
        "execution_authorization_replan_required": bool(replan_required),
        "execution_authorization_truth_gathering_required": bool(truth_gathering_required),
    }

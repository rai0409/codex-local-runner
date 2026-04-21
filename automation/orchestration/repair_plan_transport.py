from __future__ import annotations

from typing import Any
from typing import Mapping

REPAIR_PLAN_TRANSPORT_SCHEMA_VERSION = "v1"

REPAIR_PLAN_STATUSES = {
    "available",
    "blocked",
    "insufficient_truth",
    "not_needed",
}

REPAIR_PLAN_DECISIONS = {
    "prepare_truth_gathering_plan",
    "prepare_manual_review_plan",
    "prepare_replan_plan",
    "prepare_closure_followup_plan",
    "no_plan",
}

REPAIR_PLAN_CLASSES = {
    "truth_gathering_plan",
    "manual_review_plan",
    "replan_plan",
    "closure_followup_plan",
    "no_plan",
}

REPAIR_PLAN_PRIORITIES = {
    "high",
    "medium",
    "low",
}

REPAIR_PLAN_CONFIDENCE_LEVELS = {
    "strong",
    "partial",
    "conservative_low",
}

REPAIR_PLAN_TARGET_SURFACES = {
    "objective",
    "completion",
    "approval",
    "lifecycle",
    "cross_surface",
    "none",
}

REPAIR_PLAN_CANDIDATE_ACTIONS = {
    "gather_missing_truth",
    "request_manual_review",
    "request_replan",
    "request_closure_followup",
    "no_action",
}

REPAIR_PLAN_PRECONDITION_STATUSES = {
    "satisfied",
    "partially_satisfied",
    "not_satisfied",
    "insufficient_truth",
}

REPAIR_PLAN_SOURCE_STATUSES = {
    "derived_from_repair_suggestion",
    "derived_from_reconcile",
    "derived_from_cross_surface_truth",
    "insufficient_truth",
}

REPAIR_PLAN_REASON_CODES = {
    "missing_upstream_truth",
    "objective_incomplete",
    "objective_underspecified",
    "completion_not_done",
    "completion_not_safely_closed",
    "approval_absent",
    "approval_conflict",
    "reconcile_inconsistent",
    "reconcile_blocked",
    "reconcile_waiting_for_truth",
    "manual_intervention_required",
    "replan_required",
    "closure_followup_required",
    "no_reason",
}

REPAIR_PLAN_REASON_ORDER = (
    "missing_upstream_truth",
    "objective_incomplete",
    "objective_underspecified",
    "completion_not_done",
    "completion_not_safely_closed",
    "approval_absent",
    "approval_conflict",
    "reconcile_inconsistent",
    "reconcile_blocked",
    "reconcile_waiting_for_truth",
    "manual_intervention_required",
    "replan_required",
    "closure_followup_required",
    "no_reason",
)

REPAIR_PLAN_TRANSPORT_RUN_STATE_SUMMARY_SAFE_FIELDS = (
    "repair_plan_transport_present",
    "repair_plan_status",
    "repair_plan_decision",
    "repair_plan_class",
    "repair_plan_priority",
    "repair_plan_confidence",
    "repair_plan_target_surface",
    "repair_plan_candidate_action",
    "repair_plan_primary_reason",
    "repair_plan_manual_required",
    "repair_plan_replan_required",
    "repair_plan_truth_gathering_required",
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
    "reconcile_contract.reconcile_status",
    "reconcile_contract.reconcile_primary_mismatch",
    "repair_suggestion_contract.repair_suggestion_status",
    "repair_suggestion_contract.repair_primary_reason",
    "objective_contract.objective_status",
)

_DECISION_TO_PLAN: dict[str, tuple[str, str, str]] = {
    "gather_truth": (
        "prepare_truth_gathering_plan",
        "truth_gathering_plan",
        "gather_missing_truth",
    ),
    "manual_review": (
        "prepare_manual_review_plan",
        "manual_review_plan",
        "request_manual_review",
    ),
    "request_replan": (
        "prepare_replan_plan",
        "replan_plan",
        "request_replan",
    ),
    "closure_followup": (
        "prepare_closure_followup_plan",
        "closure_followup_plan",
        "request_closure_followup",
    ),
    "no_action": (
        "no_plan",
        "no_plan",
        "no_action",
    ),
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


def _normalize_optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
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
    return None


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
    for reason in REPAIR_PLAN_REASON_ORDER:
        if reason in filtered and reason in REPAIR_PLAN_REASON_CODES:
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
    reconcile_status: str,
    reconcile_primary_mismatch: str,
    repair_suggestion_status: str,
    repair_primary_reason: str,
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
    if reconcile_status:
        refs.append("reconcile_contract.reconcile_status")
    if reconcile_primary_mismatch:
        refs.append("reconcile_contract.reconcile_primary_mismatch")
    if repair_suggestion_status:
        refs.append("repair_suggestion_contract.repair_suggestion_status")
    if repair_primary_reason:
        refs.append("repair_suggestion_contract.repair_primary_reason")
    if objective_status:
        refs.append("objective_contract.objective_status")

    ordered: list[str] = []
    for allowed in _ALLOWED_SUPPORTING_REFS:
        if allowed in refs and allowed not in ordered:
            ordered.append(allowed)
    return ordered


def _fallback_plan_from_truth(
    *,
    reconcile_status: str,
    reconcile_decision: str,
    repair_manual_required: bool,
    repair_replan_required: bool,
    repair_truth_gathering_required: bool,
    repair_closure_followup_required: bool,
) -> tuple[str, str, str] | None:
    if repair_truth_gathering_required or reconcile_status == "waiting_for_truth":
        return _DECISION_TO_PLAN["gather_truth"]
    if repair_replan_required or reconcile_decision == "request_replan":
        return _DECISION_TO_PLAN["request_replan"]
    if repair_closure_followup_required:
        return _DECISION_TO_PLAN["closure_followup"]
    if repair_manual_required or reconcile_status in {"blocked", "inconsistent"}:
        return _DECISION_TO_PLAN["manual_review"]
    return None


def build_repair_plan_transport_surface(
    *,
    run_id: str,
    objective_contract_payload: Mapping[str, Any] | None,
    completion_contract_payload: Mapping[str, Any] | None,
    approval_transport_payload: Mapping[str, Any] | None,
    reconcile_contract_payload: Mapping[str, Any] | None,
    repair_suggestion_contract_payload: Mapping[str, Any] | None,
    run_state_payload: Mapping[str, Any] | None,
    artifact_presence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    objective = dict(objective_contract_payload or {})
    completion = dict(completion_contract_payload or {})
    approval = dict(approval_transport_payload or {})
    reconcile = dict(reconcile_contract_payload or {})
    repair_suggestion = dict(repair_suggestion_contract_payload or {})
    run_state = dict(run_state_payload or {})
    artifacts = dict(artifact_presence or {})

    objective_id = _normalize_text(
        objective.get("objective_id")
        or completion.get("objective_id")
        or approval.get("objective_id")
        or reconcile.get("objective_id")
        or repair_suggestion.get("objective_id")
        or run_state.get("objective_id"),
        default="",
    )
    objective_summary = _normalize_text(
        objective.get("objective_summary")
        or run_state.get("objective_summary")
        or reconcile.get("objective_summary")
        or repair_suggestion.get("objective_summary"),
        default="",
    )
    requested_outcome = _normalize_text(
        objective.get("requested_outcome")
        or run_state.get("requested_outcome")
        or reconcile.get("requested_outcome")
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
    done_status = _normalize_text(
        completion.get("done_status") or run_state.get("done_status"),
        default="",
    )
    safe_closure_status = _normalize_text(
        completion.get("safe_closure_status") or run_state.get("safe_closure_status"),
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
    approval_transport_status = _normalize_text(
        approval.get("approval_transport_status") or run_state.get("approval_transport_status"),
        default="",
    )
    approval_blocked_reason = _normalize_text(
        approval.get("approval_blocked_reason") or run_state.get("approval_blocked_reason"),
        default="",
    )
    approval_required = _normalize_bool(
        approval.get("approval_required")
        if "approval_required" in approval
        else run_state.get("approval_required")
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

    suggestion_status = _normalize_text(
        repair_suggestion.get("repair_suggestion_status")
        or run_state.get("repair_suggestion_status"),
        default="",
    )
    suggestion_decision = _normalize_text(
        repair_suggestion.get("repair_suggestion_decision")
        or run_state.get("repair_suggestion_decision"),
        default="",
    )
    suggestion_class = _normalize_text(
        repair_suggestion.get("repair_suggestion_class")
        or run_state.get("repair_suggestion_class"),
        default="",
    )
    repair_primary_reason = _normalize_text(
        repair_suggestion.get("repair_primary_reason") or run_state.get("repair_primary_reason"),
        default="",
    )

    repair_manual_required = _normalize_bool(
        repair_suggestion.get("repair_manual_required")
        if "repair_manual_required" in repair_suggestion
        else run_state.get("repair_manual_required")
    )
    repair_replan_required = _normalize_bool(
        repair_suggestion.get("repair_replan_required")
        if "repair_replan_required" in repair_suggestion
        else run_state.get("repair_replan_required")
    )
    repair_truth_gathering_required = _normalize_bool(
        repair_suggestion.get("repair_truth_gathering_required")
        if "repair_truth_gathering_required" in repair_suggestion
        else run_state.get("repair_truth_gathering_required")
    )
    repair_closure_followup_required = _normalize_bool(
        repair_suggestion.get("repair_closure_followup_required")
    )

    repair_target_surface = _normalize_text(
        repair_suggestion.get("repair_target_surface"),
        default="",
    )

    lifecycle_closure_status = _normalize_text(run_state.get("lifecycle_closure_status"), default="")
    lifecycle_safely_closed = _normalize_optional_bool(run_state.get("lifecycle_safely_closed"))
    lifecycle_primary_closure_issue = _normalize_text(
        run_state.get("lifecycle_primary_closure_issue"),
        default="",
    )

    next_safe_action = _normalize_text(run_state.get("next_safe_action"), default="")
    policy_primary_action = _normalize_text(run_state.get("policy_primary_action"), default="")
    policy_status = _normalize_text(run_state.get("policy_status"), default="")

    objective_present = (
        bool(objective)
        or _normalize_bool(run_state.get("objective_contract_present"))
        or _normalize_bool(artifacts.get("objective_contract.json"))
    )
    completion_present = (
        bool(completion)
        or _normalize_bool(run_state.get("completion_contract_present"))
        or _normalize_bool(artifacts.get("completion_contract.json"))
    )
    approval_present = (
        bool(approval)
        or _normalize_bool(run_state.get("approval_transport_present"))
        or _normalize_bool(artifacts.get("approval_transport.json"))
    )
    reconcile_present = (
        bool(reconcile)
        or _normalize_bool(run_state.get("reconcile_contract_present"))
        or _normalize_bool(artifacts.get("reconcile_contract.json"))
    )
    repair_suggestion_present = (
        bool(repair_suggestion)
        or _normalize_bool(run_state.get("repair_suggestion_contract_present"))
        or _normalize_bool(artifacts.get("repair_suggestion_contract.json"))
    )
    run_state_present = bool(run_state) or _normalize_bool(artifacts.get("run_state.json"))

    missing_upstream_truth = bool(
        (not run_state_present)
        or (not objective_present or not objective_status)
        or (not completion_present or not completion_status or not done_status)
        or (not approval_present or not approval_transport_status)
        or (not reconcile_present or not reconcile_status)
        or (not repair_suggestion_present or not suggestion_status)
    )

    completion_not_done = done_status in {"not_done", "undetermined"} or completion_status in {
        "not_done",
        "execution_complete_not_accepted",
        "replan_before_closure",
        "done_but_evidence_incomplete",
    }
    completion_not_safely_closed = bool(
        safe_closure_status and safe_closure_status != "safely_closed"
    ) or (
        lifecycle_closure_status and lifecycle_closure_status != "safely_closed"
    ) or (lifecycle_safely_closed is False)

    closure_followup_required = bool(
        repair_closure_followup_required
        or suggestion_decision == "closure_followup"
        or (
            done_status == "done"
            and (
                (lifecycle_closure_status and lifecycle_closure_status != "safely_closed")
                or lifecycle_safely_closed is False
            )
        )
    )

    approval_absent = approval_status == "absent" or (
        approval_required and not _normalize_text(approval_status, default="")
    )
    approval_conflict = approval_status == "approved" and (
        completion_not_done
        or completion_not_safely_closed
        or reconcile_status in {"blocked", "inconsistent"}
    )

    repair_manual_required = bool(
        repair_manual_required
        or _normalize_bool(repair_suggestion.get("repair_manual_required"))
        or _normalize_bool(reconcile.get("reconcile_manual_required"))
        or _normalize_bool(run_state.get("manual_intervention_required"))
        or _normalize_bool(run_state.get("policy_manual_required"))
    )
    repair_replan_required = bool(
        repair_replan_required
        or _normalize_bool(repair_suggestion.get("repair_replan_required"))
        or _normalize_bool(reconcile.get("reconcile_replan_required"))
        or _normalize_bool(run_state.get("policy_replan_required"))
        or reconcile_decision == "request_replan"
    )
    repair_truth_gathering_required = bool(
        repair_truth_gathering_required
        or suggestion_decision == "gather_truth"
        or reconcile_status == "waiting_for_truth"
    )

    reason_candidates: list[str] = []
    suggestion_reasons_raw = repair_suggestion.get("repair_reason_codes")
    if isinstance(suggestion_reasons_raw, (list, tuple)):
        reason_candidates.extend([str(item) for item in suggestion_reasons_raw])

    if missing_upstream_truth:
        reason_candidates.append("missing_upstream_truth")
    if objective_status == "incomplete":
        reason_candidates.append("objective_incomplete")
    if objective_status == "underspecified":
        reason_candidates.append("objective_underspecified")
    if completion_not_done:
        reason_candidates.append("completion_not_done")
    if completion_not_safely_closed:
        reason_candidates.append("completion_not_safely_closed")
    if approval_absent:
        reason_candidates.append("approval_absent")
    if approval_conflict:
        reason_candidates.append("approval_conflict")
    if reconcile_status == "inconsistent":
        reason_candidates.append("reconcile_inconsistent")
    if reconcile_status == "blocked":
        reason_candidates.append("reconcile_blocked")
    if reconcile_status == "waiting_for_truth":
        reason_candidates.append("reconcile_waiting_for_truth")
    if repair_manual_required:
        reason_candidates.append("manual_intervention_required")
    if repair_replan_required:
        reason_candidates.append("replan_required")
    if closure_followup_required:
        reason_candidates.append("closure_followup_required")

    reason_codes = _normalize_reason_codes(reason_candidates)

    plan_tuple = _DECISION_TO_PLAN.get(suggestion_decision)
    fallback_tuple = _fallback_plan_from_truth(
        reconcile_status=reconcile_status,
        reconcile_decision=reconcile_decision,
        repair_manual_required=repair_manual_required,
        repair_replan_required=repair_replan_required,
        repair_truth_gathering_required=repair_truth_gathering_required,
        repair_closure_followup_required=closure_followup_required,
    )

    if suggestion_status == "no_repair_needed" or suggestion_decision == "no_action":
        repair_plan_status = "not_needed"
    elif plan_tuple and suggestion_decision in {
        "gather_truth",
        "manual_review",
        "request_replan",
        "closure_followup",
    }:
        repair_plan_status = "available"
    elif missing_upstream_truth or suggestion_status == "insufficient_truth":
        repair_plan_status = "insufficient_truth"
    elif fallback_tuple is not None:
        repair_plan_status = "available"
    else:
        repair_plan_status = "blocked"

    repair_plan_status = _normalize_enum(
        repair_plan_status,
        allowed=REPAIR_PLAN_STATUSES,
        default="insufficient_truth",
    )

    if repair_plan_status == "not_needed":
        repair_plan_decision, repair_plan_class, repair_plan_candidate_action = _DECISION_TO_PLAN["no_action"]
    elif repair_plan_status == "available":
        plan_choice = plan_tuple
        if plan_choice is None or suggestion_decision == "no_action":
            plan_choice = fallback_tuple
        if plan_choice is None:
            plan_choice = _DECISION_TO_PLAN["gather_truth"]
        repair_plan_decision, repair_plan_class, repair_plan_candidate_action = plan_choice
    else:
        repair_plan_decision, repair_plan_class, repair_plan_candidate_action = _DECISION_TO_PLAN["no_action"]

    repair_plan_decision = _normalize_enum(
        repair_plan_decision,
        allowed=REPAIR_PLAN_DECISIONS,
        default="no_plan",
    )
    repair_plan_class = _normalize_enum(
        repair_plan_class,
        allowed=REPAIR_PLAN_CLASSES,
        default="no_plan",
    )
    repair_plan_candidate_action = _normalize_enum(
        repair_plan_candidate_action,
        allowed=REPAIR_PLAN_CANDIDATE_ACTIONS,
        default="no_action",
    )

    if repair_plan_status == "not_needed":
        reason_codes = ["no_reason"]
    elif not reason_codes:
        if repair_plan_class == "truth_gathering_plan":
            reason_codes = ["reconcile_waiting_for_truth"]
        elif repair_plan_class == "manual_review_plan":
            reason_codes = ["manual_intervention_required"]
        elif repair_plan_class == "replan_plan":
            reason_codes = ["replan_required"]
        elif repair_plan_class == "closure_followup_plan":
            reason_codes = ["closure_followup_required"]
        elif repair_plan_status == "insufficient_truth":
            reason_codes = ["missing_upstream_truth"]
        else:
            reason_codes = ["reconcile_blocked"]

    repair_plan_primary_reason = reason_codes[0] if reason_codes else "missing_upstream_truth"

    blocked_reason_candidates: list[str] = []
    if repair_plan_status == "blocked":
        blocked_reason_candidates.extend(reason_codes)
        if suggestion_decision == "hold":
            blocked_reason_candidates.append("reconcile_blocked")
        if missing_upstream_truth:
            blocked_reason_candidates.append("missing_upstream_truth")
    elif repair_plan_status == "insufficient_truth":
        blocked_reason_candidates.append("missing_upstream_truth")

    repair_plan_blocked_reasons = _normalize_reason_codes(blocked_reason_candidates)
    if repair_plan_status == "blocked" and not repair_plan_blocked_reasons:
        repair_plan_blocked_reasons = ["reconcile_blocked"]

    if repair_plan_status in {"available", "not_needed"}:
        repair_plan_blocked_reasons = []

    repair_plan_blocked_reason = (
        repair_plan_blocked_reasons[0] if repair_plan_blocked_reasons else ""
    )

    if (
        repair_plan_decision
        in {
            "prepare_manual_review_plan",
            "prepare_replan_plan",
            "prepare_closure_followup_plan",
        }
        and reconcile_status in {"blocked", "inconsistent"}
    ):
        repair_plan_priority = "high"
    elif repair_plan_status == "available":
        repair_plan_priority = "medium"
    else:
        repair_plan_priority = "low"

    repair_plan_priority = _normalize_enum(
        repair_plan_priority,
        allowed=REPAIR_PLAN_PRIORITIES,
        default="low",
    )

    if (
        repair_plan_status == "not_needed"
        and suggestion_status == "no_repair_needed"
        and reconcile_status == "aligned"
    ):
        repair_plan_confidence = "strong"
    elif repair_plan_status == "available" and not missing_upstream_truth:
        repair_plan_confidence = "partial"
    else:
        repair_plan_confidence = "conservative_low"

    repair_plan_confidence = _normalize_enum(
        repair_plan_confidence,
        allowed=REPAIR_PLAN_CONFIDENCE_LEVELS,
        default="conservative_low",
    )

    if repair_plan_status == "not_needed":
        repair_plan_target_surface = "none"
    elif repair_target_surface in REPAIR_PLAN_TARGET_SURFACES and repair_target_surface != "none":
        repair_plan_target_surface = repair_target_surface
    elif repair_plan_class == "truth_gathering_plan":
        repair_plan_target_surface = "cross_surface"
    elif repair_plan_class == "closure_followup_plan":
        repair_plan_target_surface = "lifecycle"
    elif "approval_conflict" in reason_codes or "approval_absent" in reason_codes:
        repair_plan_target_surface = "approval"
    elif "objective_incomplete" in reason_codes or "objective_underspecified" in reason_codes:
        repair_plan_target_surface = "objective"
    elif "completion_not_done" in reason_codes:
        repair_plan_target_surface = "completion"
    elif "completion_not_safely_closed" in reason_codes:
        repair_plan_target_surface = "lifecycle"
    else:
        repair_plan_target_surface = "cross_surface"

    repair_plan_target_surface = _normalize_enum(
        repair_plan_target_surface,
        allowed=REPAIR_PLAN_TARGET_SURFACES,
        default="none",
    )

    if repair_plan_status == "not_needed":
        repair_plan_precondition_status = "satisfied"
    elif repair_plan_status == "insufficient_truth":
        repair_plan_precondition_status = "insufficient_truth"
    elif repair_plan_status == "blocked":
        repair_plan_precondition_status = "not_satisfied"
    else:
        repair_plan_precondition_status = "partially_satisfied"

    repair_plan_precondition_status = _normalize_enum(
        repair_plan_precondition_status,
        allowed=REPAIR_PLAN_PRECONDITION_STATUSES,
        default="insufficient_truth",
    )

    repair_plan_manual_required = bool(
        repair_manual_required or repair_plan_class == "manual_review_plan"
    )
    repair_plan_replan_required = bool(
        repair_replan_required or repair_plan_class == "replan_plan"
    )
    repair_plan_truth_gathering_required = bool(
        repair_truth_gathering_required or repair_plan_class == "truth_gathering_plan"
    )
    repair_plan_closure_followup_required = bool(
        closure_followup_required or repair_plan_class == "closure_followup_plan"
    )

    if repair_plan_status == "not_needed":
        repair_plan_manual_required = False
        repair_plan_replan_required = False
        repair_plan_truth_gathering_required = False
        repair_plan_closure_followup_required = False

    if missing_upstream_truth and not repair_suggestion_present:
        repair_plan_source_status = "insufficient_truth"
    elif repair_suggestion_present and suggestion_status:
        repair_plan_source_status = "derived_from_repair_suggestion"
    elif reconcile_present and reconcile_status:
        repair_plan_source_status = "derived_from_reconcile"
    elif objective_present or completion_present or approval_present:
        repair_plan_source_status = "derived_from_cross_surface_truth"
    else:
        repair_plan_source_status = "insufficient_truth"

    repair_plan_source_status = _normalize_enum(
        repair_plan_source_status,
        allowed=REPAIR_PLAN_SOURCE_STATUSES,
        default="insufficient_truth",
    )

    payload: dict[str, Any] = {
        "schema_version": REPAIR_PLAN_TRANSPORT_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "repair_plan_status": repair_plan_status,
        "repair_plan_decision": repair_plan_decision,
        "repair_plan_class": repair_plan_class,
        "repair_plan_priority": repair_plan_priority,
        "repair_plan_confidence": repair_plan_confidence,
        "repair_plan_target_surface": repair_plan_target_surface,
        "repair_plan_candidate_action": repair_plan_candidate_action,
        "repair_plan_precondition_status": repair_plan_precondition_status,
        "repair_plan_blocked_reason": repair_plan_blocked_reason,
        "repair_plan_blocked_reasons": repair_plan_blocked_reasons,
        "repair_plan_manual_required": bool(repair_plan_manual_required),
        "repair_plan_replan_required": bool(repair_plan_replan_required),
        "repair_plan_truth_gathering_required": bool(repair_plan_truth_gathering_required),
        "repair_plan_closure_followup_required": bool(repair_plan_closure_followup_required),
        "repair_plan_execution_ready": False,
        "repair_plan_source_status": repair_plan_source_status,
        "repair_plan_reconcile_status": reconcile_status or "missing",
        "repair_plan_suggestion_status": suggestion_status or "missing",
        "repair_plan_primary_reason": repair_plan_primary_reason,
        "repair_plan_reason_codes": reason_codes,
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
            reconcile_status=reconcile_status,
            reconcile_primary_mismatch=reconcile_primary_mismatch,
            repair_suggestion_status=suggestion_status,
            repair_primary_reason=repair_primary_reason,
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


def build_repair_plan_transport_run_state_summary_surface(
    repair_plan_transport_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(repair_plan_transport_payload or {})

    status = _normalize_text(payload.get("repair_plan_status"), default="")
    decision = _normalize_text(payload.get("repair_plan_decision"), default="")
    plan_class = _normalize_text(payload.get("repair_plan_class"), default="")
    priority = _normalize_text(payload.get("repair_plan_priority"), default="")
    confidence = _normalize_text(payload.get("repair_plan_confidence"), default="")
    target_surface = _normalize_text(payload.get("repair_plan_target_surface"), default="")
    candidate_action = _normalize_text(payload.get("repair_plan_candidate_action"), default="")
    primary_reason = _normalize_text(payload.get("repair_plan_primary_reason"), default="")
    manual_required = _normalize_bool(payload.get("repair_plan_manual_required"))
    replan_required = _normalize_bool(payload.get("repair_plan_replan_required"))
    truth_gathering_required = _normalize_bool(payload.get("repair_plan_truth_gathering_required"))

    present = bool(payload.get("repair_plan_transport_present", False)) or bool(
        status or decision or plan_class
    )

    if not status:
        status = "insufficient_truth"
    if not decision:
        decision = "no_plan"
    if not plan_class:
        plan_class = "no_plan"
    if not priority:
        priority = "medium" if status == "available" else "low"
    if not confidence:
        confidence = "partial" if status == "available" else "conservative_low"
    if not target_surface:
        target_surface = "none" if status == "not_needed" else "cross_surface"
    if not candidate_action:
        candidate_action = "no_action"

    status = _normalize_enum(status, allowed=REPAIR_PLAN_STATUSES, default="insufficient_truth")
    decision = _normalize_enum(decision, allowed=REPAIR_PLAN_DECISIONS, default="no_plan")
    plan_class = _normalize_enum(plan_class, allowed=REPAIR_PLAN_CLASSES, default="no_plan")
    priority = _normalize_enum(priority, allowed=REPAIR_PLAN_PRIORITIES, default="low")
    confidence = _normalize_enum(
        confidence,
        allowed=REPAIR_PLAN_CONFIDENCE_LEVELS,
        default="conservative_low",
    )
    target_surface = _normalize_enum(
        target_surface,
        allowed=REPAIR_PLAN_TARGET_SURFACES,
        default="none",
    )
    candidate_action = _normalize_enum(
        candidate_action,
        allowed=REPAIR_PLAN_CANDIDATE_ACTIONS,
        default="no_action",
    )

    if status == "not_needed":
        decision = "no_plan"
        plan_class = "no_plan"
        priority = "low"
        target_surface = "none"
        candidate_action = "no_action"
        primary_reason = "no_reason"
        manual_required = False
        replan_required = False
        truth_gathering_required = False
        if confidence not in REPAIR_PLAN_CONFIDENCE_LEVELS:
            confidence = "strong"
    else:
        if not primary_reason or primary_reason not in REPAIR_PLAN_REASON_CODES:
            primary_reason = "missing_upstream_truth" if status == "insufficient_truth" else "reconcile_blocked"
        if decision == "prepare_manual_review_plan":
            manual_required = True
        if decision == "prepare_replan_plan":
            replan_required = True
        if decision == "prepare_truth_gathering_plan":
            truth_gathering_required = True

    return {
        "repair_plan_transport_present": bool(present),
        "repair_plan_status": status,
        "repair_plan_decision": decision,
        "repair_plan_class": plan_class,
        "repair_plan_priority": priority,
        "repair_plan_confidence": confidence,
        "repair_plan_target_surface": target_surface,
        "repair_plan_candidate_action": candidate_action,
        "repair_plan_primary_reason": primary_reason,
        "repair_plan_manual_required": bool(manual_required),
        "repair_plan_replan_required": bool(replan_required),
        "repair_plan_truth_gathering_required": bool(truth_gathering_required),
    }

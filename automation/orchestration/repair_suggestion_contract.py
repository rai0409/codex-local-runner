from __future__ import annotations

from typing import Any
from typing import Mapping

REPAIR_SUGGESTION_CONTRACT_SCHEMA_VERSION = "v1"

REPAIR_SUGGESTION_STATUSES = {
    "no_repair_needed",
    "suggested",
    "blocked",
    "insufficient_truth",
}

REPAIR_SUGGESTION_DECISIONS = {
    "no_action",
    "gather_truth",
    "manual_review",
    "request_replan",
    "closure_followup",
    "hold",
}

REPAIR_SUGGESTION_CLASSES = {
    "truth_gap",
    "objective_gap",
    "completion_closure_gap",
    "approval_conflict",
    "cross_surface_inconsistency",
    "no_gap",
}

REPAIR_SUGGESTION_PRIORITIES = {
    "high",
    "medium",
    "low",
}

REPAIR_SUGGESTION_CONFIDENCE_LEVELS = {
    "strong",
    "partial",
    "conservative_low",
}

REPAIR_TARGET_SURFACES = {
    "objective",
    "completion",
    "approval",
    "lifecycle",
    "cross_surface",
    "none",
}

REPAIR_PRECONDITION_STATUSES = {
    "satisfied",
    "partially_satisfied",
    "not_satisfied",
    "insufficient_truth",
}

REPAIR_REASON_CODES = {
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

REPAIR_REASON_ORDER = (
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

REPAIR_SUGGESTION_RUN_STATE_SUMMARY_SAFE_FIELDS = (
    "repair_suggestion_contract_present",
    "repair_suggestion_status",
    "repair_suggestion_decision",
    "repair_suggestion_class",
    "repair_suggestion_priority",
    "repair_suggestion_confidence",
    "repair_primary_reason",
    "repair_manual_required",
    "repair_replan_required",
    "repair_truth_gathering_required",
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
    "objective_contract.objective_status",
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
    allowed = _ordered_unique(values)
    ordered: list[str] = []
    for reason in REPAIR_REASON_ORDER:
        if reason in allowed and reason in REPAIR_REASON_CODES:
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
    if objective_status:
        refs.append("objective_contract.objective_status")

    ordered: list[str] = []
    for allowed in _ALLOWED_SUPPORTING_REFS:
        if allowed in refs and allowed not in ordered:
            ordered.append(allowed)
    return ordered


def build_repair_suggestion_contract_surface(
    *,
    run_id: str,
    objective_contract_payload: Mapping[str, Any] | None,
    completion_contract_payload: Mapping[str, Any] | None,
    approval_transport_payload: Mapping[str, Any] | None,
    reconcile_contract_payload: Mapping[str, Any] | None,
    run_state_payload: Mapping[str, Any] | None,
    artifact_presence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    objective = dict(objective_contract_payload or {})
    completion = dict(completion_contract_payload or {})
    approval = dict(approval_transport_payload or {})
    reconcile = dict(reconcile_contract_payload or {})
    run_state = dict(run_state_payload or {})
    artifacts = dict(artifact_presence or {})

    objective_id = _normalize_text(
        objective.get("objective_id")
        or completion.get("objective_id")
        or approval.get("objective_id")
        or reconcile.get("objective_id")
        or run_state.get("objective_id"),
        default="",
    )
    objective_summary = _normalize_text(
        objective.get("objective_summary")
        or run_state.get("objective_summary")
        or reconcile.get("objective_summary"),
        default="",
    )
    requested_outcome = _normalize_text(
        objective.get("requested_outcome")
        or run_state.get("requested_outcome")
        or reconcile.get("requested_outcome"),
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
    reconcile_manual_required = _normalize_bool(
        reconcile.get("reconcile_manual_required")
        if "reconcile_manual_required" in reconcile
        else run_state.get("reconcile_manual_required")
    )
    reconcile_replan_required = _normalize_bool(
        reconcile.get("reconcile_replan_required")
        if "reconcile_replan_required" in reconcile
        else run_state.get("reconcile_replan_required")
    )

    lifecycle_closure_status = _normalize_text(run_state.get("lifecycle_closure_status"), default="")
    lifecycle_safely_closed = _normalize_optional_bool(run_state.get("lifecycle_safely_closed"))
    lifecycle_manual_required = _normalize_bool(run_state.get("lifecycle_manual_required"))
    lifecycle_replan_required = _normalize_bool(run_state.get("lifecycle_replan_required"))
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
    run_state_present = bool(run_state) or _normalize_bool(artifacts.get("run_state.json"))
    lifecycle_present = bool(lifecycle_closure_status) or lifecycle_safely_closed is not None or run_state_present

    missing_upstream_truth = bool(
        (not run_state_present)
        or (not objective_present or not objective_status)
        or (not completion_present or not completion_status or not done_status)
        or (not approval_present or not approval_transport_status)
        or (not reconcile_present or not reconcile_status)
        or (not lifecycle_present)
    )

    completion_not_done = done_status in {"not_done", "undetermined"} or completion_status in {
        "not_done",
        "execution_complete_not_accepted",
        "replan_before_closure",
    }
    completion_not_safely_closed = bool(
        safe_closure_status
        and safe_closure_status != "safely_closed"
    ) or (
        lifecycle_closure_status and lifecycle_closure_status != "safely_closed"
    ) or (lifecycle_safely_closed is False)

    closure_followup_required = bool(
        done_status == "done"
        and (
            (lifecycle_closure_status and lifecycle_closure_status != "safely_closed")
            or lifecycle_safely_closed is False
        )
    )

    approval_absent = approval_status == "absent" or (
        approval_required and not _normalize_text(approval_status, default="")
    )
    approval_conflict = approval_status == "approved" and (
        done_status != "done"
        or (
            safe_closure_status != ""
            and safe_closure_status != "safely_closed"
        )
        or (
            lifecycle_closure_status != ""
            and lifecycle_closure_status != "safely_closed"
        )
        or reconcile_status in {"blocked", "inconsistent"}
    )

    repair_manual_required = bool(
        reconcile_manual_required
        or completion_manual_required
        or lifecycle_manual_required
        or _normalize_bool(run_state.get("policy_manual_required"))
        or _normalize_bool(run_state.get("manual_intervention_required"))
    )
    repair_replan_required = bool(
        reconcile_replan_required
        or completion_replan_required
        or lifecycle_replan_required
        or _normalize_bool(run_state.get("policy_replan_required"))
        or _normalize_bool(run_state.get("rollback_replan_required"))
        or reconcile_decision == "request_replan"
    )

    reason_candidates: list[str] = []
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
    if not reason_codes:
        reason_codes = ["no_reason"]
    if reason_codes == ["no_reason"]:
        repair_primary_reason = "no_reason"
    else:
        repair_primary_reason = reason_codes[0]

    no_gap = reason_codes == ["no_reason"]
    insufficient_truth = bool(
        missing_upstream_truth and not approval_conflict and reconcile_status != "inconsistent"
    )

    if no_gap:
        repair_suggestion_decision = "no_action"
    elif insufficient_truth or reconcile_status == "waiting_for_truth":
        repair_suggestion_decision = "gather_truth"
    elif approval_conflict:
        repair_suggestion_decision = "manual_review"
    elif repair_replan_required:
        repair_suggestion_decision = "request_replan"
    elif closure_followup_required:
        repair_suggestion_decision = "closure_followup"
    elif repair_manual_required or (reconcile_status == "blocked" and reconcile_manual_required):
        repair_suggestion_decision = "manual_review"
    else:
        repair_suggestion_decision = "hold"

    repair_suggestion_decision = _normalize_enum(
        repair_suggestion_decision,
        allowed=REPAIR_SUGGESTION_DECISIONS,
        default="hold",
    )

    if no_gap:
        repair_suggestion_class = "no_gap"
    elif missing_upstream_truth or reconcile_status == "waiting_for_truth":
        repair_suggestion_class = "truth_gap"
    elif approval_conflict:
        repair_suggestion_class = "approval_conflict"
    elif reconcile_status == "inconsistent":
        repair_suggestion_class = "cross_surface_inconsistency"
    elif objective_status in {"incomplete", "underspecified"}:
        repair_suggestion_class = "objective_gap"
    elif completion_not_done or completion_not_safely_closed or closure_followup_required:
        repair_suggestion_class = "completion_closure_gap"
    elif reconcile_status == "blocked":
        repair_suggestion_class = "cross_surface_inconsistency"
    else:
        repair_suggestion_class = "truth_gap"

    repair_suggestion_class = _normalize_enum(
        repair_suggestion_class,
        allowed=REPAIR_SUGGESTION_CLASSES,
        default="truth_gap",
    )

    repair_truth_gathering_required = bool(
        repair_suggestion_decision == "gather_truth"
        or "missing_upstream_truth" in reason_codes
        or "reconcile_waiting_for_truth" in reason_codes
    )
    repair_closure_followup_required = bool(
        closure_followup_required or repair_suggestion_decision == "closure_followup"
    )

    if repair_suggestion_decision == "no_action":
        repair_suggestion_status = "no_repair_needed"
    elif insufficient_truth:
        repair_suggestion_status = "insufficient_truth"
    elif repair_suggestion_decision == "manual_review":
        repair_suggestion_status = "blocked"
    elif repair_suggestion_decision == "hold" and (
        "reconcile_blocked" in reason_codes or "reconcile_inconsistent" in reason_codes
    ):
        repair_suggestion_status = "blocked"
    else:
        repair_suggestion_status = "suggested"

    repair_suggestion_status = _normalize_enum(
        repair_suggestion_status,
        allowed=REPAIR_SUGGESTION_STATUSES,
        default="insufficient_truth",
    )

    if repair_suggestion_decision in {"manual_review", "request_replan"}:
        repair_suggestion_priority = "high"
    elif repair_suggestion_decision in {"gather_truth", "closure_followup", "hold"}:
        repair_suggestion_priority = "medium"
    else:
        repair_suggestion_priority = "low"

    repair_suggestion_priority = _normalize_enum(
        repair_suggestion_priority,
        allowed=REPAIR_SUGGESTION_PRIORITIES,
        default="medium",
    )

    if repair_suggestion_status == "no_repair_needed" and reconcile_status == "aligned":
        repair_suggestion_confidence = "strong"
    elif repair_suggestion_status == "insufficient_truth" or repair_suggestion_class in {
        "truth_gap",
        "cross_surface_inconsistency",
    }:
        repair_suggestion_confidence = "conservative_low"
    else:
        repair_suggestion_confidence = "partial"

    repair_suggestion_confidence = _normalize_enum(
        repair_suggestion_confidence,
        allowed=REPAIR_SUGGESTION_CONFIDENCE_LEVELS,
        default="conservative_low",
    )

    if repair_suggestion_class == "no_gap":
        repair_target_surface = "none"
    elif repair_suggestion_class == "objective_gap":
        repair_target_surface = "objective"
    elif repair_suggestion_class == "completion_closure_gap":
        repair_target_surface = "lifecycle" if repair_closure_followup_required else "completion"
    elif repair_suggestion_class == "approval_conflict":
        repair_target_surface = "approval"
    elif repair_suggestion_class in {"cross_surface_inconsistency", "truth_gap"}:
        repair_target_surface = "cross_surface"
    else:
        repair_target_surface = "cross_surface"

    repair_target_surface = _normalize_enum(
        repair_target_surface,
        allowed=REPAIR_TARGET_SURFACES,
        default="none",
    )

    if repair_suggestion_status == "no_repair_needed":
        repair_precondition_status = "satisfied"
    elif repair_suggestion_status == "insufficient_truth":
        repair_precondition_status = "insufficient_truth"
    elif repair_suggestion_decision in {"manual_review", "request_replan"}:
        repair_precondition_status = "not_satisfied"
    else:
        repair_precondition_status = "partially_satisfied"

    repair_precondition_status = _normalize_enum(
        repair_precondition_status,
        allowed=REPAIR_PRECONDITION_STATUSES,
        default="insufficient_truth",
    )

    payload: dict[str, Any] = {
        "schema_version": REPAIR_SUGGESTION_CONTRACT_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "repair_suggestion_status": repair_suggestion_status,
        "repair_suggestion_decision": repair_suggestion_decision,
        "repair_suggestion_class": repair_suggestion_class,
        "repair_suggestion_priority": repair_suggestion_priority,
        "repair_suggestion_confidence": repair_suggestion_confidence,
        "repair_primary_reason": repair_primary_reason,
        "repair_reason_codes": reason_codes,
        "repair_manual_required": bool(repair_manual_required),
        "repair_replan_required": bool(repair_replan_required),
        "repair_truth_gathering_required": bool(repair_truth_gathering_required),
        "repair_closure_followup_required": bool(repair_closure_followup_required),
        "repair_execution_recommended": False,
        "repair_target_surface": repair_target_surface,
        "repair_precondition_status": repair_precondition_status,
        "repair_reconcile_status": reconcile_status or "missing",
        "repair_completion_status": completion_status or "missing",
        "repair_approval_status": approval_status or "missing",
        "repair_lifecycle_status": lifecycle_closure_status or "missing",
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


def build_repair_suggestion_run_state_summary_surface(
    repair_suggestion_contract_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(repair_suggestion_contract_payload or {})

    status = _normalize_text(payload.get("repair_suggestion_status"), default="")
    decision = _normalize_text(payload.get("repair_suggestion_decision"), default="")
    suggestion_class = _normalize_text(payload.get("repair_suggestion_class"), default="")
    priority = _normalize_text(payload.get("repair_suggestion_priority"), default="")
    confidence = _normalize_text(payload.get("repair_suggestion_confidence"), default="")
    primary_reason = _normalize_text(payload.get("repair_primary_reason"), default="")
    manual_required = _normalize_bool(payload.get("repair_manual_required"))
    replan_required = _normalize_bool(payload.get("repair_replan_required"))
    truth_gathering_required = _normalize_bool(payload.get("repair_truth_gathering_required"))

    present = bool(payload.get("repair_suggestion_contract_present", False)) or bool(
        status or decision or suggestion_class
    )

    if not status:
        status = "insufficient_truth"
    if not decision:
        decision = "hold"
    if not suggestion_class:
        suggestion_class = "truth_gap"
    if not priority:
        priority = "medium"
    if not confidence:
        confidence = "conservative_low"

    status = _normalize_enum(
        status,
        allowed=REPAIR_SUGGESTION_STATUSES,
        default="insufficient_truth",
    )
    decision = _normalize_enum(
        decision,
        allowed=REPAIR_SUGGESTION_DECISIONS,
        default="hold",
    )
    suggestion_class = _normalize_enum(
        suggestion_class,
        allowed=REPAIR_SUGGESTION_CLASSES,
        default="truth_gap",
    )
    priority = _normalize_enum(
        priority,
        allowed=REPAIR_SUGGESTION_PRIORITIES,
        default="medium",
    )
    confidence = _normalize_enum(
        confidence,
        allowed=REPAIR_SUGGESTION_CONFIDENCE_LEVELS,
        default="conservative_low",
    )

    if status == "no_repair_needed":
        primary_reason = "no_reason"
        manual_required = False
        replan_required = False
        truth_gathering_required = False
        decision = "no_action"
        suggestion_class = "no_gap"
        priority = "low"
        if confidence not in REPAIR_SUGGESTION_CONFIDENCE_LEVELS:
            confidence = "strong"
    else:
        if not primary_reason or primary_reason not in REPAIR_REASON_CODES:
            primary_reason = "missing_upstream_truth" if status == "insufficient_truth" else "reconcile_blocked"
        if decision == "gather_truth":
            truth_gathering_required = True

    return {
        "repair_suggestion_contract_present": bool(present),
        "repair_suggestion_status": status,
        "repair_suggestion_decision": decision,
        "repair_suggestion_class": suggestion_class,
        "repair_suggestion_priority": priority,
        "repair_suggestion_confidence": confidence,
        "repair_primary_reason": primary_reason,
        "repair_manual_required": bool(manual_required),
        "repair_replan_required": bool(replan_required),
        "repair_truth_gathering_required": bool(truth_gathering_required),
    }

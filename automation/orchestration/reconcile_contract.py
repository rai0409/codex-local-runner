from __future__ import annotations

from typing import Any
from typing import Mapping

RECONCILE_CONTRACT_SCHEMA_VERSION = "v1"

RECONCILE_STATUSES = {
    "aligned",
    "partially_aligned",
    "blocked",
    "inconsistent",
    "waiting_for_truth",
}

RECONCILE_DECISIONS = {
    "hold",
    "manual_review",
    "request_replan",
    "wait_for_truth",
    "aligned_no_action",
}

RECONCILE_ALIGNMENT_STATUSES = {
    "objective_completion_aligned",
    "objective_completion_partial",
    "completion_lifecycle_aligned",
    "approval_completion_aligned",
    "cross_surface_partial",
    "cross_surface_misaligned",
    "insufficient_truth",
}

RECONCILE_TRANSPORT_STATUSES = {
    "stable",
    "partial",
    "blocked",
    "inconsistent",
    "missing",
}

RECONCILE_RUN_STATE_SUMMARY_SAFE_FIELDS = (
    "reconcile_contract_present",
    "reconcile_status",
    "reconcile_decision",
    "reconcile_alignment_status",
    "reconcile_primary_mismatch",
    "reconcile_blocked_reason",
    "reconcile_waiting_on_truth",
    "reconcile_manual_required",
    "reconcile_replan_required",
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


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = _normalize_text(value, default="")
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _derive_transport_status(
    *,
    approval_transport_status: str,
    approval_status: str,
    approval_present: bool,
) -> str:
    if not approval_present and not approval_transport_status and not approval_status:
        return "missing"
    if approval_transport_status in {"missing", ""}:
        return "missing" if not approval_present else "partial"
    if approval_transport_status == "blocked":
        return "blocked"
    if approval_transport_status in {"expired", "superseded"}:
        return "blocked"
    if approval_transport_status == "non_actionable":
        return "partial"
    if approval_transport_status == "actionable":
        if approval_status in {"approved", "replan_requested"}:
            return "stable"
        return "partial"
    return "partial"


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
    if objective_status:
        refs.append("objective_contract.objective_status")

    ordered: list[str] = []
    for allowed in _ALLOWED_SUPPORTING_REFS:
        if allowed in refs and allowed not in ordered:
            ordered.append(allowed)
    return ordered


def build_reconcile_contract_surface(
    *,
    run_id: str,
    objective_contract_payload: Mapping[str, Any] | None,
    completion_contract_payload: Mapping[str, Any] | None,
    approval_transport_payload: Mapping[str, Any] | None,
    run_state_payload: Mapping[str, Any] | None,
    artifact_presence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    objective = dict(objective_contract_payload or {})
    completion = dict(completion_contract_payload or {})
    approval = dict(approval_transport_payload or {})
    run_state = dict(run_state_payload or {})
    artifacts = dict(artifact_presence or {})

    objective_id = _normalize_text(
        objective.get("objective_id")
        or completion.get("objective_id")
        or approval.get("objective_id")
        or run_state.get("objective_id"),
        default="",
    )
    objective_summary = _normalize_text(
        objective.get("objective_summary")
        or run_state.get("objective_summary")
        or approval.get("objective_summary"),
        default="",
    )
    requested_outcome = _normalize_text(
        objective.get("requested_outcome")
        or run_state.get("requested_outcome")
        or approval.get("requested_outcome"),
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

    lifecycle_closure_status = _normalize_text(run_state.get("lifecycle_closure_status"), default="")
    lifecycle_safely_closed = _normalize_optional_bool(run_state.get("lifecycle_safely_closed"))
    lifecycle_manual_required = _normalize_bool(run_state.get("lifecycle_manual_required"))
    lifecycle_replan_required = _normalize_bool(run_state.get("lifecycle_replan_required"))

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
    approval_required = _normalize_bool(
        approval.get("approval_required")
        if "approval_required" in approval
        else run_state.get("approval_required")
    )
    approval_present = _normalize_bool(
        approval.get("approval_present")
        if "approval_present" in approval
        else run_state.get("approval_transport_present")
    ) or bool(approval)

    next_safe_action = _normalize_text(
        run_state.get("next_safe_action") or approval.get("next_safe_action"),
        default="",
    )
    policy_primary_action = _normalize_text(
        run_state.get("policy_primary_action") or approval.get("policy_primary_action"),
        default="",
    )
    lifecycle_primary_closure_issue = _normalize_text(
        run_state.get("lifecycle_primary_closure_issue"),
        default="",
    )
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
    approval_transport_present = (
        bool(approval)
        or _normalize_bool(run_state.get("approval_transport_present"))
        or _normalize_bool(artifacts.get("approval_transport.json"))
    )
    run_state_present = bool(run_state) or _normalize_bool(artifacts.get("run_state.json"))
    lifecycle_present = bool(lifecycle_closure_status) or lifecycle_safely_closed is not None or run_state_present

    reconcile_transport_status = _derive_transport_status(
        approval_transport_status=approval_transport_status,
        approval_status=approval_status,
        approval_present=approval_present or approval_transport_present,
    )

    run_state_objective_status = _normalize_text(run_state.get("objective_contract_status"), default="")
    run_state_completion_status = _normalize_text(run_state.get("completion_status"), default="")
    run_state_approval_status = _normalize_text(run_state.get("approval_status"), default="")

    mismatch_conflicts: list[str] = []
    if run_state_objective_status and objective_status and run_state_objective_status != objective_status:
        mismatch_conflicts.append("run_state_objective_mismatch")
    if run_state_completion_status and completion_status and run_state_completion_status != completion_status:
        mismatch_conflicts.append("run_state_completion_mismatch")
    if run_state_approval_status and approval_status and run_state_approval_status != approval_status:
        mismatch_conflicts.append("run_state_approval_mismatch")

    objective_completion_conflict = objective_status in {"blocked", "incomplete", "underspecified"} and done_status == "done"
    completion_lifecycle_conflict = (
        safe_closure_status == "safely_closed"
        and (
            (lifecycle_closure_status and lifecycle_closure_status != "safely_closed")
            or lifecycle_safely_closed is False
        )
    ) or (
        safe_closure_status == "not_safely_closed"
        and lifecycle_closure_status == "safely_closed"
        and lifecycle_safely_closed is True
    )
    approval_completion_conflict = approval_status == "approved" and (
        done_status != "done"
        or safe_closure_status != "safely_closed"
        or lifecycle_closure_status != "safely_closed"
        or reconcile_transport_status in {"blocked", "inconsistent", "missing"}
    )

    if objective_completion_conflict:
        mismatch_conflicts.append("objective_completion_conflict")
    if completion_lifecycle_conflict:
        mismatch_conflicts.append("completion_lifecycle_conflict")
    if approval_completion_conflict:
        mismatch_conflicts.append("approval_completion_conflict")

    if approval_status == "approved" and reconcile_transport_status in {"blocked", "missing"}:
        reconcile_transport_status = "inconsistent"
    if approval_status == "absent" and reconcile_transport_status == "stable":
        reconcile_transport_status = "inconsistent"

    reconcile_transport_status = _normalize_enum(
        reconcile_transport_status,
        allowed=RECONCILE_TRANSPORT_STATUSES,
        default="missing",
    )
    if reconcile_transport_status == "inconsistent":
        mismatch_conflicts.append("approval_transport_inconsistent")

    missing_truth_reasons: list[str] = []
    if not run_state_present:
        missing_truth_reasons.append("run_state_truth_missing")
    if not objective_present or not objective_status:
        missing_truth_reasons.append("objective_truth_missing")
    if not completion_present or not completion_status:
        missing_truth_reasons.append("completion_truth_missing")
    if not lifecycle_present:
        missing_truth_reasons.append("lifecycle_truth_missing")
    if not approval_transport_present or not approval_transport_status:
        missing_truth_reasons.append("approval_truth_missing")
    if completion_present and not done_status:
        missing_truth_reasons.append("completion_done_status_missing")

    missing_truth_reasons = _dedupe(missing_truth_reasons)

    reconcile_manual_required = bool(
        completion_manual_required
        or lifecycle_manual_required
        or _normalize_bool(run_state.get("manual_intervention_required"))
        or (approval_required and approval_status in {"absent", "deferred", "denied"})
    )
    reconcile_replan_required = bool(
        completion_replan_required
        or lifecycle_replan_required
        or _normalize_bool(run_state.get("policy_replan_required"))
        or _normalize_bool(run_state.get("rollback_replan_required"))
        or approval_status == "replan_requested"
    )

    blocking_reasons: list[str] = []
    if objective_status == "blocked":
        blocking_reasons.append("objective_blocked")
    elif objective_status == "incomplete":
        blocking_reasons.append("objective_incomplete")
    elif objective_status == "underspecified":
        blocking_reasons.append("objective_underspecified")

    if completion_status and completion_status != "done_and_safely_closed":
        if completion_blocked_reason:
            blocking_reasons.append(completion_blocked_reason)
        else:
            blocking_reasons.append("completion_not_closed")
    if completion_manual_required:
        blocking_reasons.append("completion_manual_required")
    if completion_replan_required:
        blocking_reasons.append("completion_replan_required")

    if lifecycle_closure_status and lifecycle_closure_status != "safely_closed":
        blocking_reasons.append(f"lifecycle_{lifecycle_closure_status}")
    elif lifecycle_safely_closed is False:
        blocking_reasons.append("lifecycle_not_safely_closed")
    if lifecycle_manual_required:
        blocking_reasons.append("lifecycle_manual_required")
    if lifecycle_replan_required:
        blocking_reasons.append("lifecycle_replan_required")

    if approval_status == "denied":
        blocking_reasons.append("approval_denied")
    elif approval_status == "deferred":
        blocking_reasons.append("approval_deferred")
    elif approval_status == "absent":
        blocking_reasons.append("approval_absent")
    if approval_blocked_reason:
        blocking_reasons.append(approval_blocked_reason)
    if reconcile_transport_status == "blocked":
        blocking_reasons.append("approval_transport_blocked")
    elif reconcile_transport_status == "partial":
        blocking_reasons.append("approval_transport_partial")
    elif reconcile_transport_status == "missing":
        blocking_reasons.append("approval_transport_missing")

    if reconcile_manual_required:
        blocking_reasons.append("manual_review_required")
    if reconcile_replan_required:
        blocking_reasons.append("replan_required")

    blocking_reasons = _dedupe(blocking_reasons)
    mismatch_conflicts = _dedupe(mismatch_conflicts)

    objective_completion_aligned = objective_status == "complete" and done_status == "done"
    completion_lifecycle_aligned = (
        completion_status == "done_and_safely_closed"
        and safe_closure_status == "safely_closed"
        and lifecycle_closure_status == "safely_closed"
    )
    approval_completion_aligned = (
        reconcile_transport_status == "stable"
        and approval_status in {"approved", "replan_requested"}
        and not approval_completion_conflict
        and bool(completion_status)
    )

    if missing_truth_reasons:
        reconcile_alignment_status = "insufficient_truth"
    elif mismatch_conflicts:
        reconcile_alignment_status = "cross_surface_misaligned"
    elif objective_completion_aligned and completion_lifecycle_aligned and approval_completion_aligned:
        reconcile_alignment_status = "objective_completion_aligned"
    elif objective_status in {"blocked", "incomplete", "underspecified"} and done_status in {"not_done", "undetermined"}:
        reconcile_alignment_status = "objective_completion_partial"
    elif completion_lifecycle_aligned:
        reconcile_alignment_status = "completion_lifecycle_aligned"
    elif approval_completion_aligned:
        reconcile_alignment_status = "approval_completion_aligned"
    else:
        reconcile_alignment_status = "cross_surface_partial"

    reconcile_alignment_status = _normalize_enum(
        reconcile_alignment_status,
        allowed=RECONCILE_ALIGNMENT_STATUSES,
        default="insufficient_truth",
    )

    fully_aligned = (
        objective_status == "complete"
        and completion_status == "done_and_safely_closed"
        and lifecycle_closure_status == "safely_closed"
        and lifecycle_safely_closed is True
        and reconcile_transport_status == "stable"
        and not reconcile_manual_required
        and not reconcile_replan_required
        and not mismatch_conflicts
        and not missing_truth_reasons
    )

    blocked_state = bool(
        objective_status in {"blocked", "incomplete", "underspecified"}
        or completion_status in {
            "not_done",
            "manual_closure_required",
            "replan_before_closure",
            "execution_complete_not_accepted",
            "rollback_complete_not_closed",
            "delivery_complete_waiting_external_truth",
            "done_but_evidence_incomplete",
        }
        or (lifecycle_closure_status and lifecycle_closure_status != "safely_closed")
        or reconcile_transport_status in {"blocked", "inconsistent", "missing"}
        or reconcile_manual_required
        or reconcile_replan_required
    )

    if mismatch_conflicts:
        reconcile_status = "inconsistent"
        blocked_reasons = _dedupe(mismatch_conflicts + blocking_reasons)
    elif missing_truth_reasons:
        reconcile_status = "waiting_for_truth"
        blocked_reasons = list(missing_truth_reasons)
    elif fully_aligned:
        reconcile_status = "aligned"
        blocked_reasons = []
    elif blocked_state:
        reconcile_status = "blocked"
        blocked_reasons = list(blocking_reasons)
    else:
        reconcile_status = "partially_aligned"
        blocked_reasons = list(blocking_reasons) if blocking_reasons else ["cross_surface_partial_alignment"]

    reconcile_status = _normalize_enum(
        reconcile_status,
        allowed=RECONCILE_STATUSES,
        default="waiting_for_truth",
    )

    if reconcile_status == "aligned":
        reconcile_decision = "aligned_no_action"
    elif reconcile_status == "waiting_for_truth":
        reconcile_decision = "wait_for_truth"
    elif reconcile_status == "inconsistent":
        reconcile_decision = "manual_review"
    elif reconcile_replan_required:
        reconcile_decision = "request_replan"
    elif reconcile_manual_required:
        reconcile_decision = "manual_review"
    else:
        reconcile_decision = "hold"

    reconcile_decision = _normalize_enum(
        reconcile_decision,
        allowed=RECONCILE_DECISIONS,
        default="hold",
    )

    reconcile_waiting_on_truth = reconcile_status == "waiting_for_truth"
    reconcile_blocked_reason = blocked_reasons[0] if blocked_reasons else ""
    reconcile_primary_mismatch = reconcile_blocked_reason

    if reconcile_status == "aligned":
        reconcile_blocked_reason = ""
        reconcile_primary_mismatch = ""
        blocked_reasons = []

    payload: dict[str, Any] = {
        "schema_version": RECONCILE_CONTRACT_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "reconcile_status": reconcile_status,
        "reconcile_decision": reconcile_decision,
        "reconcile_alignment_status": reconcile_alignment_status,
        "reconcile_primary_mismatch": reconcile_primary_mismatch,
        "reconcile_blocked_reason": reconcile_blocked_reason,
        "reconcile_blocked_reasons": blocked_reasons,
        "reconcile_waiting_on_truth": bool(reconcile_waiting_on_truth),
        "reconcile_manual_required": bool(reconcile_manual_required),
        "reconcile_replan_required": bool(reconcile_replan_required),
        "reconcile_completion_status": completion_status or "missing",
        "reconcile_approval_status": approval_status or "missing",
        "reconcile_lifecycle_status": lifecycle_closure_status or "missing",
        "reconcile_objective_status": objective_status or "missing",
        "reconcile_transport_status": reconcile_transport_status,
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
    if next_safe_action:
        payload["next_safe_action"] = next_safe_action
    if policy_primary_action:
        payload["policy_primary_action"] = policy_primary_action

    return payload


def build_reconcile_run_state_summary_surface(
    reconcile_contract_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(reconcile_contract_payload or {})

    status = _normalize_text(payload.get("reconcile_status"), default="")
    decision = _normalize_text(payload.get("reconcile_decision"), default="")
    alignment = _normalize_text(payload.get("reconcile_alignment_status"), default="")
    primary_mismatch = _normalize_text(payload.get("reconcile_primary_mismatch"), default="")
    blocked_reason = _normalize_text(payload.get("reconcile_blocked_reason"), default="")
    waiting_on_truth = _normalize_bool(payload.get("reconcile_waiting_on_truth"))
    manual_required = _normalize_bool(payload.get("reconcile_manual_required"))
    replan_required = _normalize_bool(payload.get("reconcile_replan_required"))

    present = bool(payload.get("reconcile_contract_present", False)) or bool(status or decision or alignment)

    if not status:
        status = "waiting_for_truth"
    if not decision:
        decision = "wait_for_truth"
    if not alignment:
        alignment = "insufficient_truth"

    status = _normalize_enum(status, allowed=RECONCILE_STATUSES, default="waiting_for_truth")
    decision = _normalize_enum(decision, allowed=RECONCILE_DECISIONS, default="hold")
    alignment = _normalize_enum(alignment, allowed=RECONCILE_ALIGNMENT_STATUSES, default="insufficient_truth")

    if status == "aligned":
        primary_mismatch = ""
        blocked_reason = ""
        waiting_on_truth = False
    else:
        if status == "waiting_for_truth":
            waiting_on_truth = True
        if not primary_mismatch and blocked_reason:
            primary_mismatch = blocked_reason
        if not blocked_reason and primary_mismatch:
            blocked_reason = primary_mismatch

    return {
        "reconcile_contract_present": bool(present),
        "reconcile_status": status,
        "reconcile_decision": decision,
        "reconcile_alignment_status": alignment,
        "reconcile_primary_mismatch": primary_mismatch,
        "reconcile_blocked_reason": blocked_reason,
        "reconcile_waiting_on_truth": bool(waiting_on_truth),
        "reconcile_manual_required": bool(manual_required),
        "reconcile_replan_required": bool(replan_required),
    }

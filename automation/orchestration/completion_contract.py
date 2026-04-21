from __future__ import annotations

from typing import Any
from typing import Mapping

COMPLETION_CONTRACT_SCHEMA_VERSION = "v1"

COMPLETION_STATUSES = {
    "done_and_safely_closed",
    "done_but_evidence_incomplete",
    "execution_complete_not_accepted",
    "delivery_complete_waiting_external_truth",
    "rollback_complete_not_closed",
    "manual_closure_required",
    "replan_before_closure",
    "not_done",
}

DONE_STATUSES = {
    "done",
    "not_done",
    "undetermined",
}

SAFE_CLOSURE_STATUSES = {
    "safely_closed",
    "not_safely_closed",
    "undetermined",
}

CLOSURE_DECISIONS = {
    "close",
    "hold",
    "manual_review",
    "replan",
    "not_done",
}

COMPLETION_EVIDENCE_STATUSES = {
    "sufficient",
    "partial",
    "missing",
}

LIFECYCLE_ALIGNMENT_STATUSES = {
    "aligned",
    "partially_aligned",
    "misaligned",
    "insufficient_truth",
}

COMPLETION_RUN_STATE_SUMMARY_SAFE_FIELDS = (
    "completion_contract_present",
    "completion_status",
    "done_status",
    "safe_closure_status",
    "completion_evidence_status",
    "completion_blocked_reason",
    "completion_manual_required",
    "completion_replan_required",
    "completion_lifecycle_alignment_status",
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


def _normalize_string_list(value: Any, *, sort_items: bool = False) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    seen: set[str] = set()
    normalized: list[str] = []
    for item in value:
        text = _normalize_text(item, default="")
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    if sort_items:
        return sorted(normalized)
    return normalized


def _normalize_enum(value: Any, *, allowed: set[str], default: str) -> str:
    text = _normalize_text(value, default="")
    if text in allowed:
        return text
    return default


def _count_defined_acceptance(criteria: Any) -> tuple[int, int]:
    if not isinstance(criteria, list):
        return 0, 0
    total = 0
    defined = 0
    for entry in criteria:
        if not isinstance(entry, Mapping):
            continue
        total += 1
        if _normalize_text(entry.get("status"), default="") == "defined":
            defined += 1
    return total, defined


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in values:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _build_lifecycle_alignment_status(
    *,
    lifecycle_closure_status: str,
    lifecycle_safely_closed: bool | None,
) -> str:
    if not lifecycle_closure_status and lifecycle_safely_closed is None:
        return "insufficient_truth"
    if lifecycle_safely_closed is True and lifecycle_closure_status != "safely_closed":
        return "misaligned"
    if lifecycle_safely_closed is False and lifecycle_closure_status == "safely_closed":
        return "misaligned"
    if lifecycle_safely_closed is True and lifecycle_closure_status == "safely_closed":
        return "aligned"
    return "partially_aligned"


def _build_required_evidence(
    *,
    required_artifacts: list[str],
) -> list[str]:
    required: list[str] = [
        "objective_contract.objective_status",
        "objective_contract.acceptance_status",
        "objective_contract.acceptance_criteria",
        "run_state.lifecycle_closure_status",
        "run_state.lifecycle_safely_closed",
    ]
    for artifact_name in required_artifacts:
        required.append(f"objective_contract.required_artifact:{artifact_name}")
    return _dedupe(required)


def build_completion_contract_surface(
    *,
    run_id: str,
    objective_contract_payload: Mapping[str, Any] | None,
    run_state_payload: Mapping[str, Any] | None,
    artifact_presence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    objective = dict(objective_contract_payload or {})
    run_state = dict(run_state_payload or {})
    artifact_presence_payload = dict(artifact_presence or {})

    objective_id = _normalize_text(
        objective.get("objective_id") or run_state.get("objective_id"),
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
    objective_source_status = _normalize_text(objective.get("objective_source_status"), default="")
    acceptance_status = _normalize_text(
        objective.get("acceptance_status") or run_state.get("objective_acceptance_status"),
        default="",
    )

    lifecycle_closure_status = _normalize_text(run_state.get("lifecycle_closure_status"), default="")
    lifecycle_safely_closed = _normalize_optional_bool(run_state.get("lifecycle_safely_closed"))

    lifecycle_alignment_status = _normalize_enum(
        _build_lifecycle_alignment_status(
            lifecycle_closure_status=lifecycle_closure_status,
            lifecycle_safely_closed=lifecycle_safely_closed,
        ),
        allowed=LIFECYCLE_ALIGNMENT_STATUSES,
        default="insufficient_truth",
    )

    if objective_status == "complete" and acceptance_status == "defined":
        done_status = "done"
    elif objective_status in {"blocked", "incomplete", "underspecified"} or acceptance_status in {
        "blocked",
        "undefined",
        "partially_defined",
    }:
        done_status = "not_done"
    elif objective_source_status == "missing" or not objective_status:
        done_status = "undetermined"
    else:
        done_status = "not_done"

    lifecycle_manual_required = _normalize_bool(run_state.get("lifecycle_manual_required"))
    lifecycle_replan_required = _normalize_bool(run_state.get("lifecycle_replan_required"))
    policy_manual_required = _normalize_bool(run_state.get("policy_manual_required"))
    policy_replan_required = _normalize_bool(run_state.get("policy_replan_required"))
    run_manual_required = _normalize_bool(run_state.get("manual_intervention_required"))

    completion_manual_required = lifecycle_manual_required or policy_manual_required or run_manual_required
    completion_replan_required = (
        lifecycle_replan_required
        or policy_replan_required
        or _normalize_bool(run_state.get("rollback_replan_required"))
    )

    if (
        lifecycle_closure_status == "safely_closed"
        and lifecycle_safely_closed is True
        and not completion_manual_required
        and not completion_replan_required
    ):
        safe_closure_status = "safely_closed"
    elif not lifecycle_closure_status and lifecycle_safely_closed is None:
        safe_closure_status = "undetermined"
    else:
        safe_closure_status = "not_safely_closed"

    rollback_complete_not_closed = (
        _normalize_bool(run_state.get("lifecycle_rollback_complete_not_closed"))
        or _normalize_bool(run_state.get("rollback_completed"))
        and (
            _normalize_bool(run_state.get("rollback_aftermath_blocked"))
            or _normalize_bool(run_state.get("rollback_manual_followup_required"))
            or _normalize_bool(run_state.get("rollback_remote_followup_required"))
        )
    )
    rollback_complete_not_closed = bool(rollback_complete_not_closed)

    delivery_completed = _normalize_bool(run_state.get("delivery_completed")) or _normalize_bool(
        run_state.get("merge_execution_succeeded")
    )
    delivery_complete_waiting_external_truth = bool(delivery_completed) and (
        _normalize_bool(run_state.get("remote_github_blocked"))
        or _normalize_bool(run_state.get("remote_github_missing_or_ambiguous"))
        or _normalize_bool(run_state.get("rollback_remote_followup_required"))
        or _normalize_bool(run_state.get("rollback_aftermath_missing_or_ambiguous"))
    )

    execution_completed = (
        bool(delivery_completed)
        or _normalize_bool(run_state.get("lifecycle_execution_complete_not_closed"))
        or _normalize_bool(run_state.get("rollback_completed"))
    )
    execution_complete_not_accepted = bool(execution_completed and done_status != "done")

    required_artifacts = _normalize_string_list(objective.get("required_artifacts"), sort_items=True)
    required_evidence = _build_required_evidence(required_artifacts=required_artifacts)

    acceptance_total, acceptance_defined = _count_defined_acceptance(objective.get("acceptance_criteria"))

    missing_evidence: list[str] = []
    if objective_status != "complete":
        missing_evidence.append("objective_contract.objective_status")
    if acceptance_status != "defined":
        missing_evidence.append("objective_contract.acceptance_status")
    if acceptance_total <= 0 or acceptance_defined < acceptance_total:
        missing_evidence.append("objective_contract.acceptance_criteria")
    if not lifecycle_closure_status:
        missing_evidence.append("run_state.lifecycle_closure_status")
    if lifecycle_safely_closed is None:
        missing_evidence.append("run_state.lifecycle_safely_closed")

    for artifact_name in required_artifacts:
        present = _normalize_bool(artifact_presence_payload.get(artifact_name))
        if not present:
            missing_evidence.append(f"objective_contract.required_artifact:{artifact_name}")

    missing_evidence = _dedupe(missing_evidence)

    if not missing_evidence:
        completion_evidence_status = "sufficient"
    elif required_evidence and len(missing_evidence) < len(required_evidence):
        completion_evidence_status = "partial"
    else:
        completion_evidence_status = "missing"

    completion_blocked_reasons: list[str] = []
    if objective_status == "blocked":
        completion_blocked_reasons.append("objective_blocked")
    elif objective_status == "incomplete":
        completion_blocked_reasons.append("objective_incomplete")
    elif objective_status == "underspecified":
        completion_blocked_reasons.append("objective_underspecified")
    elif done_status == "undetermined":
        completion_blocked_reasons.append("objective_truth_undetermined")

    if acceptance_status == "blocked":
        completion_blocked_reasons.append("acceptance_blocked")
    elif acceptance_status == "undefined":
        completion_blocked_reasons.append("acceptance_undefined")
    elif acceptance_status == "partially_defined":
        completion_blocked_reasons.append("acceptance_partially_defined")

    if completion_evidence_status == "partial":
        completion_blocked_reasons.append("completion_evidence_partial")
    elif completion_evidence_status == "missing":
        completion_blocked_reasons.append("completion_evidence_missing")

    if lifecycle_alignment_status == "misaligned":
        completion_blocked_reasons.append("lifecycle_truth_misaligned")
    elif lifecycle_alignment_status == "insufficient_truth":
        completion_blocked_reasons.append("lifecycle_truth_insufficient")

    if safe_closure_status == "not_safely_closed":
        completion_blocked_reasons.append("not_safely_closed")
    elif safe_closure_status == "undetermined":
        completion_blocked_reasons.append("safe_closure_undetermined")

    if completion_manual_required:
        completion_blocked_reasons.append("manual_closure_required")
    if completion_replan_required:
        completion_blocked_reasons.append("replan_before_closure")
    if rollback_complete_not_closed:
        completion_blocked_reasons.append("rollback_complete_not_closed")
    if delivery_complete_waiting_external_truth:
        completion_blocked_reasons.append("delivery_complete_waiting_external_truth")
    if execution_complete_not_accepted:
        completion_blocked_reasons.append("execution_complete_not_accepted")

    completion_blocked_reasons = _dedupe(completion_blocked_reasons)

    if (
        done_status == "done"
        and safe_closure_status == "safely_closed"
        and completion_evidence_status == "sufficient"
        and not completion_manual_required
        and not completion_replan_required
        and not rollback_complete_not_closed
        and not delivery_complete_waiting_external_truth
        and lifecycle_alignment_status == "aligned"
    ):
        completion_status = "done_and_safely_closed"
        closure_decision = "close"
        closure_reason = "objective_done_and_lifecycle_safely_closed"
    elif completion_replan_required:
        completion_status = "replan_before_closure"
        closure_decision = "replan"
        closure_reason = "replan_required_before_closure"
    elif completion_manual_required:
        completion_status = "manual_closure_required"
        closure_decision = "manual_review"
        closure_reason = "manual_closure_required"
    elif rollback_complete_not_closed:
        completion_status = "rollback_complete_not_closed"
        closure_decision = "hold"
        closure_reason = "rollback_complete_not_closed"
    elif delivery_complete_waiting_external_truth:
        completion_status = "delivery_complete_waiting_external_truth"
        closure_decision = "hold"
        closure_reason = "delivery_complete_waiting_external_truth"
    elif execution_complete_not_accepted:
        completion_status = "execution_complete_not_accepted"
        closure_decision = "hold"
        closure_reason = "execution_complete_not_accepted"
    elif done_status == "done" and completion_evidence_status in {"partial", "missing"}:
        completion_status = "done_but_evidence_incomplete"
        closure_decision = "hold"
        closure_reason = "completion_evidence_incomplete"
    else:
        completion_status = "not_done"
        closure_decision = "not_done"
        closure_reason = "objective_not_done"

    completion_status = _normalize_enum(
        completion_status,
        allowed=COMPLETION_STATUSES,
        default="not_done",
    )
    done_status = _normalize_enum(done_status, allowed=DONE_STATUSES, default="undetermined")
    safe_closure_status = _normalize_enum(
        safe_closure_status,
        allowed=SAFE_CLOSURE_STATUSES,
        default="undetermined",
    )
    closure_decision = _normalize_enum(
        closure_decision,
        allowed=CLOSURE_DECISIONS,
        default="not_done",
    )
    completion_evidence_status = _normalize_enum(
        completion_evidence_status,
        allowed=COMPLETION_EVIDENCE_STATUSES,
        default="missing",
    )

    completion_blocked_reason = ""
    if completion_status != "done_and_safely_closed" and completion_blocked_reasons:
        completion_blocked_reason = completion_blocked_reasons[0]

    if completion_status == "done_and_safely_closed":
        completion_blocked_reasons = []

    payload: dict[str, Any] = {
        "schema_version": COMPLETION_CONTRACT_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "completion_status": completion_status,
        "done_status": done_status,
        "safe_closure_status": safe_closure_status,
        "done_definition_ref": "objective_contract.json#objective_status,acceptance_status",
        "safe_closure_definition_ref": "run_state.json#lifecycle_closure_status,lifecycle_safely_closed",
        "required_evidence": required_evidence,
        "missing_evidence": missing_evidence,
        "closure_decision": closure_decision,
        "closure_reason": closure_reason,
        "completion_blocked_reason": completion_blocked_reason,
        "completion_blocked_reasons": completion_blocked_reasons,
        "completion_manual_required": bool(completion_manual_required),
        "completion_replan_required": bool(completion_replan_required),
        "execution_complete_not_accepted": bool(execution_complete_not_accepted),
        "rollback_complete_not_closed": bool(rollback_complete_not_closed),
        "delivery_complete_waiting_external_truth": bool(delivery_complete_waiting_external_truth),
        "lifecycle_alignment_status": lifecycle_alignment_status,
        "lifecycle_closure_status": lifecycle_closure_status,
        "completion_evidence_status": completion_evidence_status,
        "supporting_compact_truth_refs": [
            "objective_contract.json#objective_status",
            "objective_contract.json#acceptance_status",
            "run_state.json#lifecycle_closure_status",
            "run_state.json#lifecycle_safely_closed",
            "run_state.json#policy_status",
            "run_state.json#rollback_aftermath_status",
        ],
    }

    if objective_summary:
        payload["objective_summary"] = objective_summary
    if requested_outcome:
        payload["requested_outcome"] = requested_outcome

    return payload


def build_completion_run_state_summary_surface(
    completion_contract_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(completion_contract_payload or {})

    completion_status = _normalize_text(payload.get("completion_status"), default="")
    done_status = _normalize_text(payload.get("done_status"), default="")
    safe_closure_status = _normalize_text(payload.get("safe_closure_status"), default="")
    completion_evidence_status = _normalize_text(payload.get("completion_evidence_status"), default="")
    completion_blocked_reason = _normalize_text(payload.get("completion_blocked_reason"), default="")
    completion_manual_required = _normalize_bool(payload.get("completion_manual_required"))
    completion_replan_required = _normalize_bool(payload.get("completion_replan_required"))
    lifecycle_alignment_status = _normalize_text(
        payload.get("completion_lifecycle_alignment_status")
        if "completion_lifecycle_alignment_status" in payload
        else payload.get("lifecycle_alignment_status"),
        default="",
    )

    present = bool(payload.get("completion_contract_present", False)) or bool(
        completion_status
        or done_status
        or safe_closure_status
        or completion_evidence_status
        or lifecycle_alignment_status
    )

    if not completion_status:
        completion_status = "not_done"
    if not done_status:
        done_status = "undetermined"
    if not safe_closure_status:
        safe_closure_status = "undetermined"
    if not completion_evidence_status:
        completion_evidence_status = "missing"
    if not lifecycle_alignment_status:
        lifecycle_alignment_status = "insufficient_truth"
    if present and not completion_blocked_reason and completion_status != "done_and_safely_closed":
        completion_blocked_reason = "completion_not_closed"

    completion_status = _normalize_enum(
        completion_status,
        allowed=COMPLETION_STATUSES,
        default="not_done",
    )
    done_status = _normalize_enum(done_status, allowed=DONE_STATUSES, default="undetermined")
    safe_closure_status = _normalize_enum(
        safe_closure_status,
        allowed=SAFE_CLOSURE_STATUSES,
        default="undetermined",
    )
    completion_evidence_status = _normalize_enum(
        completion_evidence_status,
        allowed=COMPLETION_EVIDENCE_STATUSES,
        default="missing",
    )
    lifecycle_alignment_status = _normalize_enum(
        lifecycle_alignment_status,
        allowed=LIFECYCLE_ALIGNMENT_STATUSES,
        default="insufficient_truth",
    )

    if completion_status == "done_and_safely_closed":
        completion_blocked_reason = ""

    return {
        "completion_contract_present": bool(present),
        "completion_status": completion_status,
        "done_status": done_status,
        "safe_closure_status": safe_closure_status,
        "completion_evidence_status": completion_evidence_status,
        "completion_blocked_reason": completion_blocked_reason,
        "completion_manual_required": bool(completion_manual_required),
        "completion_replan_required": bool(completion_replan_required),
        "completion_lifecycle_alignment_status": lifecycle_alignment_status,
    }

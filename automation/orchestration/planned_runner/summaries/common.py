from __future__ import annotations
from typing import Any
from typing import Mapping
from automation.orchestration.planned_runner.utils import (
    _normalize_text,
    _serialize_required_signals,
)

def _resolve_approval_input_payload(
    *,
    explicit_approval_input: Mapping[str, Any] | None,
    artifacts: Mapping[str, Any],
    policy_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    candidates: list[Any] = [
        explicit_approval_input,
        artifacts.get("approval_input"),
        artifacts.get("manual_approval_input"),
        policy_snapshot.get("approval_input"),
        policy_snapshot.get("manual_approval_input"),
    ]
    for candidate in candidates:
        if isinstance(candidate, Mapping):
            return dict(candidate)
    return {}

def _unit_is_failure(*, execution_status: str, dry_run: bool) -> bool:
    if execution_status in {"failed", "timed_out"}:
        return True
    if execution_status in {"running", "not_started"}:
        return not dry_run
    return False

def _has_contract_identity_conflict(
    *,
    pr_id: str,
    bounded_step_contract: Mapping[str, Any],
    prompt_contract: Mapping[str, Any],
) -> bool:
    bounded_progression = (
        dict(bounded_step_contract.get("progression_metadata"))
        if isinstance(bounded_step_contract.get("progression_metadata"), Mapping)
        else {}
    )
    prompt_progression = (
        dict(prompt_contract.get("progression_metadata"))
        if isinstance(prompt_contract.get("progression_metadata"), Mapping)
        else {}
    )
    bounded_step_id = _normalize_text(bounded_step_contract.get("step_id"), default="")
    bounded_progression_step_id = _normalize_text(bounded_progression.get("planned_step_id"), default="")
    prompt_source_step_id = _normalize_text(prompt_contract.get("source_step_id"), default="")
    prompt_progression_step_id = _normalize_text(prompt_progression.get("planned_step_id"), default="")
    for candidate in (
        bounded_step_id,
        bounded_progression_step_id,
        prompt_source_step_id,
        prompt_progression_step_id,
    ):
        if candidate and candidate != pr_id:
            return True
    return False

def _has_missing_progression_metadata(
    *,
    bounded_step_contract: Mapping[str, Any],
    prompt_contract: Mapping[str, Any],
) -> bool:
    bounded_progression = bounded_step_contract.get("progression_metadata")
    prompt_progression = prompt_contract.get("progression_metadata")
    return not isinstance(bounded_progression, Mapping) or not isinstance(prompt_progression, Mapping)

def _is_unbounded_contract(bounded_step_contract: Mapping[str, Any]) -> bool:
    boundedness = (
        dict(bounded_step_contract.get("boundedness"))
        if isinstance(bounded_step_contract.get("boundedness"), Mapping)
        else {}
    )
    status = _normalize_text(boundedness.get("status"), default="")
    return status != "bounded"

def _is_scope_violation_detected(
    *,
    strict_scope_files: list[str],
    changed_files: list[str],
) -> bool:
    if not strict_scope_files or not changed_files:
        return False
    strict_scope = set(strict_scope_files)
    return any(path not in strict_scope for path in changed_files)

def _is_missing_required_ref_reason(reason: str) -> bool:
    if any(hint in reason for hint in _MISSING_REQUIRED_REF_HINTS):
        return any(token in reason for token in _MISSING_REQUIRED_REF_TOKENS)
    return False

def _unit_decision_summary(unit: Mapping[str, Any]) -> dict[str, Any]:
    return dict(unit.get("decision_summary")) if isinstance(unit.get("decision_summary"), Mapping) else {}

def _unit_execution_summary(unit: Mapping[str, Any], summary_key: str) -> dict[str, Any]:
    return dict(unit.get(summary_key)) if isinstance(unit.get(summary_key), Mapping) else {}

def _unit_execution_status(
    *,
    unit: Mapping[str, Any],
    decision_summary: Mapping[str, Any],
    execution_name: str,
) -> str:
    status = _normalize_text(decision_summary.get(f"{execution_name}_status"), default="")
    if status:
        return status
    summary_payload = _unit_execution_summary(unit, f"{execution_name}_summary")
    return _normalize_text(summary_payload.get("status"), default="")

def _normalize_approved_restart_execution_reason_codes(
    reason_codes: list[str],
) -> list[str]:
    normalized = _serialize_required_signals(
        [reason for reason in reason_codes if reason in _APPROVED_RESTART_EXECUTION_REASON_CODES]
    )
    ordered = [reason for reason in _APPROVED_RESTART_EXECUTION_REASON_ORDER if reason in normalized]
    return ordered if ordered else ["restart_not_executed"]

def _normalize_approval_skip_reason_codes(reason_codes: list[str]) -> list[str]:
    normalized = _serialize_required_signals(
        [reason for reason in reason_codes if reason in _APPROVAL_SKIP_REASON_CODES]
    )
    ordered = [reason for reason in _APPROVAL_SKIP_REASON_ORDER if reason in normalized]
    return ordered if ordered else ["skip_not_allowed"]

def _normalize_continuation_budget_reason_codes(reason_codes: list[str]) -> list[str]:
    normalized = _serialize_required_signals(
        [reason for reason in reason_codes if reason in _CONTINUATION_BUDGET_REASON_CODES]
    )
    ordered = [reason for reason in _CONTINUATION_BUDGET_REASON_ORDER if reason in normalized]
    return ordered if ordered else ["budget_insufficient_truth"]

def _normalize_continuation_branch_budget_reason_codes(
    reason_codes: list[str],
) -> list[str]:
    normalized = _serialize_required_signals(
        [reason for reason in reason_codes if reason in _CONTINUATION_BUDGET_BRANCH_REASON_CODES]
    )
    ordered = [
        reason
        for reason in _CONTINUATION_BUDGET_BRANCH_REASON_ORDER
        if reason in normalized
    ]
    return ordered if ordered else ["branch_budget_not_applicable"]

def _normalize_continuation_repair_playbook_reason_codes(
    reason_codes: list[str],
) -> list[str]:
    normalized = _serialize_required_signals(
        [
            reason
            for reason in reason_codes
            if reason in _CONTINUATION_REPAIR_PLAYBOOK_REASON_CODES
        ]
    )
    ordered = [
        reason
        for reason in _CONTINUATION_REPAIR_PLAYBOOK_REASON_ORDER
        if reason in normalized
    ]
    return ordered if ordered else ["playbook_insufficient_truth"]

def _normalize_continuation_next_step_reason_codes(
    reason_codes: list[str],
) -> list[str]:
    normalized = _serialize_required_signals(
        [
            reason
            for reason in reason_codes
            if reason in _CONTINUATION_NEXT_STEP_REASON_CODES
        ]
    )
    ordered = [
        reason
        for reason in _CONTINUATION_NEXT_STEP_REASON_ORDER
        if reason in normalized
    ]
    return ordered if ordered else ["next_step_not_selected"]

def _normalize_supported_repair_execution_reason_codes(
    reason_codes: list[str],
) -> list[str]:
    normalized = _serialize_required_signals(
        [
            reason
            for reason in reason_codes
            if reason in _SUPPORTED_REPAIR_EXECUTION_REASON_CODES
        ]
    )
    ordered = [
        reason
        for reason in _SUPPORTED_REPAIR_EXECUTION_REASON_ORDER
        if reason in normalized
    ]
    return ordered if ordered else ["repair_not_selected"]

def _normalize_final_human_review_gate_reason_codes(
    reason_codes: list[str],
) -> list[str]:
    normalized = _serialize_required_signals(
        [
            reason
            for reason in reason_codes
            if reason in _FINAL_HUMAN_REVIEW_GATE_REASON_CODES
        ]
    )
    ordered = [
        reason
        for reason in _FINAL_HUMAN_REVIEW_GATE_REASON_ORDER
        if reason in normalized
    ]
    return ordered if ordered else ["final_review_not_required"]

def _normalize_project_planning_summary_reason_codes(
    reason_codes: list[str],
) -> list[str]:
    normalized = _serialize_required_signals(
        [
            reason
            for reason in reason_codes
            if reason in _PROJECT_PLANNING_SUMMARY_REASON_CODES
        ]
    )
    ordered = [
        reason
        for reason in _PROJECT_PLANNING_SUMMARY_REASON_ORDER
        if reason in normalized
    ]
    return ordered if ordered else ["planning_summary_insufficient_truth"]

def _normalize_project_roadmap_reason_codes(
    reason_codes: list[str],
) -> list[str]:
    normalized = _serialize_required_signals(
        [
            reason
            for reason in reason_codes
            if reason in _PROJECT_ROADMAP_REASON_CODES
        ]
    )
    ordered = [
        reason
        for reason in _PROJECT_ROADMAP_REASON_ORDER
        if reason in normalized
    ]
    return ordered if ordered else ["roadmap_insufficient_truth"]

def _normalize_implementation_prompt_reason_codes(
    reason_codes: list[str],
) -> list[str]:
    normalized = _serialize_required_signals(
        [
            reason
            for reason in reason_codes
            if reason in _IMPLEMENTATION_PROMPT_REASON_CODES
        ]
    )
    ordered = [
        reason
        for reason in _IMPLEMENTATION_PROMPT_REASON_ORDER
        if reason in normalized
    ]
    return ordered if ordered else ["prompt_planning_insufficient_truth"]

def _normalize_review_assimilation_reason_codes(
    reason_codes: list[str],
) -> list[str]:
    normalized = _serialize_required_signals(
        [
            reason
            for reason in reason_codes
            if reason in _REVIEW_ASSIMILATION_REASON_CODES
        ]
    )
    ordered = [
        reason
        for reason in _REVIEW_ASSIMILATION_REASON_ORDER
        if reason in normalized
    ]
    return ordered if ordered else ["assimilation_result_insufficient_truth"]

def _normalize_self_healing_reason_codes(
    reason_codes: list[str],
) -> list[str]:
    normalized = _serialize_required_signals(
        [
            reason
            for reason in reason_codes
            if reason in _SELF_HEALING_REASON_CODES
        ]
    )
    ordered = [
        reason
        for reason in _SELF_HEALING_REASON_ORDER
        if reason in normalized
    ]
    return ordered if ordered else ["self_healing_insufficient_assimilation_truth"]

def _normalize_long_running_reason_codes(
    reason_codes: list[str],
) -> list[str]:
    normalized = _serialize_required_signals(
        [
            reason
            for reason in reason_codes
            if reason in _LONG_RUNNING_REASON_CODES
        ]
    )
    ordered = [
        reason
        for reason in _LONG_RUNNING_REASON_ORDER
        if reason in normalized
    ]
    return ordered if ordered else ["long_running_insufficient_truth_queue_state"]

def _normalize_objective_compiler_reason_codes(
    reason_codes: list[str],
) -> list[str]:
    normalized = _serialize_required_signals(
        [
            reason
            for reason in reason_codes
            if reason in _OBJECTIVE_COMPILER_REASON_CODES
        ]
    )
    ordered = [
        reason
        for reason in _OBJECTIVE_COMPILER_REASON_ORDER
        if reason in normalized
    ]
    return ordered if ordered else ["objective_truth_insufficient"]

def _normalize_project_autonomy_budget_reason_codes(
    reason_codes: list[str],
) -> list[str]:
    normalized = _serialize_required_signals(
        [
            reason
            for reason in reason_codes
            if reason in _PROJECT_AUTONOMY_BUDGET_REASON_CODES
        ]
    )
    ordered = [
        reason
        for reason in _PROJECT_AUTONOMY_BUDGET_REASON_ORDER
        if reason in normalized
    ]
    return ordered if ordered else ["autonomy_budget_insufficient_truth"]

def _normalize_project_quality_gate_reason_codes(
    reason_codes: list[str],
) -> list[str]:
    normalized = _serialize_required_signals(
        [
            reason
            for reason in reason_codes
            if reason in _PROJECT_QUALITY_GATE_REASON_CODES
        ]
    )
    ordered = [
        reason
        for reason in _PROJECT_QUALITY_GATE_REASON_ORDER
        if reason in normalized
    ]
    return ordered if ordered else ["quality_gate_insufficient_truth"]

def _normalize_project_failure_memory_reason_codes(
    reason_codes: list[str],
) -> list[str]:
    normalized = _serialize_required_signals(
        [
            reason
            for reason in reason_codes
            if reason in _PROJECT_FAILURE_MEMORY_REASON_CODES
        ]
    )
    ordered = [
        reason
        for reason in _PROJECT_FAILURE_MEMORY_REASON_ORDER
        if reason in normalized
    ]
    return ordered if ordered else ["failure_memory_insufficient_truth"]

def _normalize_project_external_boundary_reason_codes(
    reason_codes: list[str],
) -> list[str]:
    normalized = _serialize_required_signals(
        [
            reason
            for reason in reason_codes
            if reason in _PROJECT_EXTERNAL_BOUNDARY_REASON_CODES
        ]
    )
    ordered = [
        reason
        for reason in _PROJECT_EXTERNAL_BOUNDARY_REASON_ORDER
        if reason in normalized
    ]
    return ordered if ordered else ["external_boundary_insufficient_truth"]

def _normalize_project_human_escalation_reason_codes(
    reason_codes: list[str],
) -> list[str]:
    normalized = _serialize_required_signals(
        [
            reason
            for reason in reason_codes
            if reason in _PROJECT_HUMAN_ESCALATION_REASON_CODES
        ]
    )
    ordered = [
        reason
        for reason in _PROJECT_HUMAN_ESCALATION_REASON_ORDER
        if reason in normalized
    ]
    return ordered if ordered else ["escalation_insufficient_truth"]

def _normalize_project_approval_notification_reason_codes(
    reason_codes: list[str],
) -> list[str]:
    normalized = _serialize_required_signals(
        [
            reason
            for reason in reason_codes
            if reason in _PROJECT_APPROVAL_NOTIFICATION_REASON_CODES
        ]
    )
    ordered = [
        reason
        for reason in _PROJECT_APPROVAL_NOTIFICATION_REASON_ORDER
        if reason in normalized
    ]
    return ordered if ordered else ["approval_notification_insufficient_truth"]

def _normalize_project_multi_objective_reason_codes(
    reason_codes: list[str],
) -> list[str]:
    normalized = _serialize_required_signals(
        [
            reason
            for reason in reason_codes
            if reason in _PROJECT_MULTI_OBJECTIVE_REASON_CODES
        ]
    )
    ordered = [
        reason
        for reason in _PROJECT_MULTI_OBJECTIVE_REASON_ORDER
        if reason in normalized
    ]
    return ordered if ordered else ["multi_objective_insufficient_truth"]

def _select_approved_restart_target_unit(
    manifest_units: list[Mapping[str, Any]],
) -> dict[str, Any] | None:
    for entry in manifest_units:
        status = _normalize_text(entry.get("status"), default="")
        if status == "failed":
            return dict(entry)
    if manifest_units:
        return dict(manifest_units[0])
    return None


__all__ = [
    "_resolve_approval_input_payload",
    "_unit_is_failure",
    "_has_contract_identity_conflict",
    "_has_missing_progression_metadata",
    "_is_unbounded_contract",
    "_is_scope_violation_detected",
    "_is_missing_required_ref_reason",
    "_unit_decision_summary",
    "_unit_execution_summary",
    "_unit_execution_status",
    "_normalize_approved_restart_execution_reason_codes",
    "_normalize_approval_skip_reason_codes",
    "_normalize_continuation_budget_reason_codes",
    "_normalize_continuation_branch_budget_reason_codes",
    "_normalize_continuation_repair_playbook_reason_codes",
    "_normalize_continuation_next_step_reason_codes",
    "_normalize_supported_repair_execution_reason_codes",
    "_normalize_final_human_review_gate_reason_codes",
    "_normalize_project_planning_summary_reason_codes",
    "_normalize_project_roadmap_reason_codes",
    "_normalize_implementation_prompt_reason_codes",
    "_normalize_review_assimilation_reason_codes",
    "_normalize_self_healing_reason_codes",
    "_normalize_long_running_reason_codes",
    "_normalize_objective_compiler_reason_codes",
    "_normalize_project_autonomy_budget_reason_codes",
    "_normalize_project_quality_gate_reason_codes",
    "_normalize_project_failure_memory_reason_codes",
    "_normalize_project_external_boundary_reason_codes",
    "_normalize_project_human_escalation_reason_codes",
    "_normalize_project_approval_notification_reason_codes",
    "_normalize_project_multi_objective_reason_codes",
    "_select_approved_restart_target_unit",
]

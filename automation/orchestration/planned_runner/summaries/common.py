from __future__ import annotations
from typing import Any
from typing import Mapping
from automation.orchestration.planned_runner.utils import (
    _normalize_text,
    _serialize_required_signals,
)
from automation.orchestration.planned_runner.constants import *

_APPROVAL_SKIP_REASON_CODES = {
    "skip_allowed_low_risk",
    "skip_not_applicable_approval_not_required",
    "skip_human_response_already_present",
    "skip_invalid_or_insufficient_truth",
    "skip_safety_duplicate_pending",
    "skip_safety_cooldown_active",
    "skip_safety_loop_suspected",
    "skip_safety_delivery_blocked",
    "skip_safety_delivery_deferred",
    "skip_safety_not_clear",
    "skip_manual_review_required",
    "skip_high_risk_posture",
    "skip_unsupported_direction",
    "skip_hold_or_reject_posture",
    "skip_not_allowed",
}

_APPROVAL_SKIP_REASON_ORDER = (
    "skip_not_applicable_approval_not_required",
    "skip_human_response_already_present",
    "skip_invalid_or_insufficient_truth",
    "skip_safety_duplicate_pending",
    "skip_safety_cooldown_active",
    "skip_safety_loop_suspected",
    "skip_safety_delivery_blocked",
    "skip_safety_delivery_deferred",
    "skip_safety_not_clear",
    "skip_manual_review_required",
    "skip_high_risk_posture",
    "skip_unsupported_direction",
    "skip_hold_or_reject_posture",
    "skip_allowed_low_risk",
    "skip_not_allowed",
)

_APPROVED_RESTART_EXECUTION_REASON_CODES = {
    "invalid_approved_restart_posture",
    "response_not_approved",
    "safety_duplicate_pending",
    "safety_cooldown_active",
    "safety_loop_suspected",
    "safety_delivery_blocked",
    "safety_delivery_deferred",
    "safety_not_clear",
    "continuation_budget_insufficient_truth",
    "continuation_budget_exhausted",
    "continuation_no_progress_stop",
    "failure_bucket_continuation_denied",
    "continuation_next_step_not_selected",
    "supported_repair_qualification_failed",
    "supported_repair_verification_failed",
    "restart_target_missing",
    "restart_launch_failed",
    "restart_executed_once",
    "restart_not_executed",
}

_APPROVED_RESTART_EXECUTION_REASON_ORDER = (
    "invalid_approved_restart_posture",
    "response_not_approved",
    "safety_duplicate_pending",
    "safety_cooldown_active",
    "safety_loop_suspected",
    "safety_delivery_blocked",
    "safety_delivery_deferred",
    "safety_not_clear",
    "continuation_budget_insufficient_truth",
    "continuation_budget_exhausted",
    "continuation_no_progress_stop",
    "failure_bucket_continuation_denied",
    "continuation_next_step_not_selected",
    "supported_repair_qualification_failed",
    "supported_repair_verification_failed",
    "restart_target_missing",
    "restart_launch_failed",
    "restart_executed_once",
    "restart_not_executed",
)

_CONTINUATION_BUDGET_BRANCH_REASON_CODES = {
    "branch_budget_available",
    "branch_budget_exhausted",
    "branch_budget_not_applicable",
}

_CONTINUATION_BUDGET_BRANCH_REASON_ORDER = (
    "branch_budget_exhausted",
    "branch_budget_available",
    "branch_budget_not_applicable",
)

_CONTINUATION_BUDGET_REASON_CODES = {
    "budget_available",
    "budget_run_exhausted",
    "budget_objective_exhausted",
    "budget_lane_exhausted",
    "budget_branch_exhausted",
    "budget_insufficient_truth",
}

_CONTINUATION_BUDGET_REASON_ORDER = (
    "budget_insufficient_truth",
    "budget_lane_exhausted",
    "budget_objective_exhausted",
    "budget_run_exhausted",
    "budget_branch_exhausted",
    "budget_available",
)

_CONTINUATION_NEXT_STEP_REASON_CODES = {
    "next_step_selected_supported_repair",
    "next_step_selected_truth_gather",
    "next_step_selected_replan",
    "next_step_selected_retry",
    "next_step_insufficient_truth",
    "next_step_not_selected",
}

_CONTINUATION_NEXT_STEP_REASON_ORDER = (
    "next_step_insufficient_truth",
    "next_step_not_selected",
    "next_step_selected_supported_repair",
    "next_step_selected_truth_gather",
    "next_step_selected_replan",
    "next_step_selected_retry",
)

_CONTINUATION_REPAIR_PLAYBOOK_REASON_CODES = {
    "playbook_selected",
    "playbook_insufficient_truth",
    "playbook_bucket_unsupported",
}

_CONTINUATION_REPAIR_PLAYBOOK_REASON_ORDER = (
    "playbook_insufficient_truth",
    "playbook_bucket_unsupported",
    "playbook_selected",
)

_FINAL_HUMAN_REVIEW_GATE_REASON_CODES = {
    "final_review_manual_only_posture",
    "final_review_high_risk_posture",
    "final_review_supported_repair_verification_failed",
    "final_review_next_step_unresolved",
    "final_review_explicit_manual_review_required",
    "final_review_not_required",
}

_FINAL_HUMAN_REVIEW_GATE_REASON_ORDER = (
    "final_review_manual_only_posture",
    "final_review_high_risk_posture",
    "final_review_supported_repair_verification_failed",
    "final_review_next_step_unresolved",
    "final_review_explicit_manual_review_required",
    "final_review_not_required",
)

_IMPLEMENTATION_PROMPT_REASON_CODES = {
    "prompt_compiled",
    "prompt_planning_insufficient_truth",
    "prompt_slice_state_insufficient_truth",
    "prompt_slice_missing",
    "prompt_size_posture_unbounded",
}

_IMPLEMENTATION_PROMPT_REASON_ORDER = (
    "prompt_planning_insufficient_truth",
    "prompt_slice_state_insufficient_truth",
    "prompt_slice_missing",
    "prompt_size_posture_unbounded",
    "prompt_compiled",
)

_LONG_RUNNING_REASON_CODES = {
    "long_running_monitoring_active",
    "long_running_paused_stale_watchdog",
    "long_running_escalated_stuck_detection",
    "long_running_safe_stop_queue_empty",
    "long_running_safe_stop_queue_blocked",
    "long_running_safe_stop_human_fallback",
    "long_running_safe_stop_chain_budget_exhausted",
    "long_running_escalated_final_human_review_required",
    "long_running_insufficient_truth_queue_state",
    "long_running_resume_ready_replay_safe",
}

_LONG_RUNNING_REASON_ORDER = (
    "long_running_insufficient_truth_queue_state",
    "long_running_escalated_final_human_review_required",
    "long_running_escalated_stuck_detection",
    "long_running_paused_stale_watchdog",
    "long_running_safe_stop_human_fallback",
    "long_running_safe_stop_chain_budget_exhausted",
    "long_running_safe_stop_queue_blocked",
    "long_running_safe_stop_queue_empty",
    "long_running_resume_ready_replay_safe",
    "long_running_monitoring_active",
)

_MISSING_REQUIRED_REF_HINTS = (
    "missing",
    "unresolved",
    "not_directory",
    "not_git_worktree",
)

_MISSING_REQUIRED_REF_TOKENS = (
    "repo",
    "branch",
    "remote",
    "base",
    "head",
    "pr",
    "sha",
    "ref",
    "path",
)

_OBJECTIVE_COMPILER_REASON_CODES = {
    "objective_compiled",
    "objective_identity_missing",
    "objective_truth_insufficient",
    "done_criteria_met",
    "done_criteria_incomplete",
    "done_criteria_insufficient_truth",
    "stop_criteria_continue",
    "stop_criteria_done_met",
    "stop_criteria_human_review_required",
    "stop_criteria_stability_pause_or_escalation",
    "stop_criteria_human_fallback_preserved",
    "stop_criteria_insufficient_truth",
    "scope_drift_detected_queue_prompt_mismatch",
    "scope_drift_detected_split_signal",
    "scope_drift_clear",
    "scope_drift_insufficient_truth",
    "completion_objective_active",
    "completion_objective_completed",
    "completion_objective_blocked",
    "completion_objective_insufficient_truth",
}

_OBJECTIVE_COMPILER_REASON_ORDER = (
    "objective_identity_missing",
    "objective_truth_insufficient",
    "objective_compiled",
    "done_criteria_insufficient_truth",
    "done_criteria_met",
    "done_criteria_incomplete",
    "scope_drift_insufficient_truth",
    "scope_drift_detected_queue_prompt_mismatch",
    "scope_drift_detected_split_signal",
    "scope_drift_clear",
    "stop_criteria_insufficient_truth",
    "stop_criteria_human_review_required",
    "stop_criteria_stability_pause_or_escalation",
    "stop_criteria_human_fallback_preserved",
    "stop_criteria_done_met",
    "stop_criteria_continue",
    "completion_objective_insufficient_truth",
    "completion_objective_completed",
    "completion_objective_blocked",
    "completion_objective_active",
)

_PROJECT_APPROVAL_NOTIFICATION_REASON_CODES = {
    "approval_notification_compiled",
    "approval_notification_insufficient_truth",
    "approval_notification_ready",
    "approval_notification_not_ready",
    "approval_notification_not_required",
    "approval_reply_required",
    "approval_reply_not_required",
    "approval_channel_email_send",
    "approval_channel_email_draft",
    "approval_channel_review_queue",
    "approval_channel_manual_only",
    "approval_channel_not_required",
    "approval_channel_insufficient_truth",
    "approval_mobile_summary_available",
    "approval_mobile_summary_not_required",
    "approval_mobile_summary_insufficient_truth",
    "approval_escalation_required",
    "approval_escalation_not_required",
    "approval_response_awaiting",
    "approval_response_terminal",
}

_PROJECT_APPROVAL_NOTIFICATION_REASON_ORDER = (
    "approval_notification_insufficient_truth",
    "approval_notification_compiled",
    "approval_escalation_required",
    "approval_escalation_not_required",
    "approval_notification_ready",
    "approval_notification_not_ready",
    "approval_notification_not_required",
    "approval_reply_required",
    "approval_reply_not_required",
    "approval_channel_insufficient_truth",
    "approval_channel_manual_only",
    "approval_channel_review_queue",
    "approval_channel_email_draft",
    "approval_channel_email_send",
    "approval_channel_not_required",
    "approval_mobile_summary_insufficient_truth",
    "approval_mobile_summary_available",
    "approval_mobile_summary_not_required",
    "approval_response_awaiting",
    "approval_response_terminal",
)

_PROJECT_AUTONOMY_BUDGET_REASON_CODES = {
    "autonomy_budget_compiled",
    "autonomy_budget_insufficient_truth",
    "project_priority_active",
    "project_priority_lowered_budget_exhausted",
    "project_priority_deferred_blocked",
    "project_priority_deferred_high_risk",
    "project_priority_completed",
    "project_priority_insufficient_truth",
    "run_budget_available",
    "run_budget_exhausted",
    "run_budget_insufficient_truth",
    "objective_budget_available",
    "objective_budget_exhausted",
    "objective_budget_insufficient_truth",
    "pr_retry_budget_available",
    "pr_retry_budget_exhausted",
    "pr_retry_budget_not_applicable",
    "pr_retry_budget_insufficient_truth",
    "high_risk_defer_active",
    "high_risk_defer_clear",
    "high_risk_defer_insufficient_truth",
}

_PROJECT_AUTONOMY_BUDGET_REASON_ORDER = (
    "autonomy_budget_insufficient_truth",
    "autonomy_budget_compiled",
    "project_priority_insufficient_truth",
    "project_priority_deferred_high_risk",
    "project_priority_deferred_blocked",
    "project_priority_lowered_budget_exhausted",
    "project_priority_completed",
    "project_priority_active",
    "run_budget_insufficient_truth",
    "run_budget_exhausted",
    "run_budget_available",
    "objective_budget_insufficient_truth",
    "objective_budget_exhausted",
    "objective_budget_available",
    "pr_retry_budget_insufficient_truth",
    "pr_retry_budget_exhausted",
    "pr_retry_budget_available",
    "pr_retry_budget_not_applicable",
    "high_risk_defer_insufficient_truth",
    "high_risk_defer_active",
    "high_risk_defer_clear",
)

_PROJECT_EXTERNAL_BOUNDARY_REASON_CODES = {
    "external_boundary_compiled",
    "external_boundary_insufficient_truth",
    "external_dependency_available",
    "external_dependency_blocked",
    "external_dependency_manual_only",
    "external_boundary_manual_only",
    "external_network_boundary_clear",
    "external_network_boundary_blocked",
    "external_ci_boundary_clear",
    "external_ci_boundary_blocked",
    "external_secrets_boundary_clear",
    "external_secrets_boundary_blocked",
    "external_github_boundary_clear",
    "external_github_boundary_blocked",
    "external_api_boundary_clear",
    "external_api_boundary_blocked",
}

_PROJECT_EXTERNAL_BOUNDARY_REASON_ORDER = (
    "external_boundary_insufficient_truth",
    "external_boundary_compiled",
    "external_dependency_manual_only",
    "external_dependency_blocked",
    "external_dependency_available",
    "external_boundary_manual_only",
    "external_network_boundary_blocked",
    "external_ci_boundary_blocked",
    "external_secrets_boundary_blocked",
    "external_github_boundary_blocked",
    "external_api_boundary_blocked",
    "external_network_boundary_clear",
    "external_ci_boundary_clear",
    "external_secrets_boundary_clear",
    "external_github_boundary_clear",
    "external_api_boundary_clear",
)

_PROJECT_FAILURE_MEMORY_REASON_CODES = {
    "failure_memory_compiled",
    "failure_memory_insufficient_truth",
    "failure_memory_ineffective_retry_detected",
    "failure_memory_failed_repair_detected",
    "failure_memory_repeated_review_issue_detected",
    "failure_memory_recurring_failure_bucket_detected",
    "failure_memory_no_ineffective_retry",
    "failure_memory_no_failed_repair",
    "failure_memory_no_repeated_review_issue",
    "failure_memory_no_recurring_failure_bucket",
    "failure_memory_suppression_none",
    "failure_memory_suppression_retry",
    "failure_memory_suppression_repair",
    "failure_memory_suppression_review_issue",
    "failure_memory_suppression_failure_bucket",
}

_PROJECT_FAILURE_MEMORY_REASON_ORDER = (
    "failure_memory_insufficient_truth",
    "failure_memory_compiled",
    "failure_memory_ineffective_retry_detected",
    "failure_memory_failed_repair_detected",
    "failure_memory_repeated_review_issue_detected",
    "failure_memory_recurring_failure_bucket_detected",
    "failure_memory_no_ineffective_retry",
    "failure_memory_no_failed_repair",
    "failure_memory_no_repeated_review_issue",
    "failure_memory_no_recurring_failure_bucket",
    "failure_memory_suppression_failure_bucket",
    "failure_memory_suppression_review_issue",
    "failure_memory_suppression_repair",
    "failure_memory_suppression_retry",
    "failure_memory_suppression_none",
)

_PROJECT_HUMAN_ESCALATION_REASON_CODES = {
    "escalation_compiled",
    "escalation_insufficient_truth",
    "escalation_required",
    "escalation_not_required",
    "escalation_architecture_risk_elevated",
    "escalation_architecture_risk_clear",
    "escalation_scope_risk_elevated",
    "escalation_scope_risk_clear",
    "escalation_external_risk_elevated",
    "escalation_external_risk_clear",
    "escalation_budget_risk_elevated",
    "escalation_budget_risk_clear",
    "escalation_repeated_failure_risk_elevated",
    "escalation_repeated_failure_risk_clear",
    "escalation_manual_only_risk_elevated",
    "escalation_manual_only_risk_clear",
}

_PROJECT_HUMAN_ESCALATION_REASON_ORDER = (
    "escalation_insufficient_truth",
    "escalation_compiled",
    "escalation_required",
    "escalation_not_required",
    "escalation_manual_only_risk_elevated",
    "escalation_external_risk_elevated",
    "escalation_budget_risk_elevated",
    "escalation_repeated_failure_risk_elevated",
    "escalation_scope_risk_elevated",
    "escalation_architecture_risk_elevated",
    "escalation_manual_only_risk_clear",
    "escalation_external_risk_clear",
    "escalation_budget_risk_clear",
    "escalation_repeated_failure_risk_clear",
    "escalation_scope_risk_clear",
    "escalation_architecture_risk_clear",
)

_PROJECT_MULTI_OBJECTIVE_REASON_CODES = {
    "multi_objective_compiled",
    "multi_objective_insufficient_truth",
    "multi_objective_selected",
    "multi_objective_deferred",
    "multi_objective_blocked_objective_deferred",
    "multi_objective_blocked_objective_not_deferred",
    "multi_objective_queue_resume_selected_first",
    "multi_objective_queue_resume_blocked",
    "multi_objective_queue_resume_empty",
    "multi_objective_queue_resume_completed_waiting",
    "multi_objective_queue_deferred_non_runnable",
    "multi_objective_approval_notification_deferred",
    "multi_objective_escalation_deferred",
}

_PROJECT_MULTI_OBJECTIVE_REASON_ORDER = (
    "multi_objective_insufficient_truth",
    "multi_objective_compiled",
    "multi_objective_approval_notification_deferred",
    "multi_objective_escalation_deferred",
    "multi_objective_selected",
    "multi_objective_deferred",
    "multi_objective_blocked_objective_deferred",
    "multi_objective_blocked_objective_not_deferred",
    "multi_objective_queue_deferred_non_runnable",
    "multi_objective_queue_resume_selected_first",
    "multi_objective_queue_resume_blocked",
    "multi_objective_queue_resume_completed_waiting",
    "multi_objective_queue_resume_empty",
)

_PROJECT_PLANNING_SUMMARY_REASON_CODES = {
    "planning_summary_compiled",
    "planning_summary_insufficient_truth",
}

_PROJECT_PLANNING_SUMMARY_REASON_ORDER = (
    "planning_summary_insufficient_truth",
    "planning_summary_compiled",
)

_PROJECT_QUALITY_GATE_REASON_CODES = {
    "quality_gate_compiled",
    "quality_gate_insufficient_truth",
    "quality_gate_posture_merge_ready",
    "quality_gate_posture_review_ready",
    "quality_gate_posture_retry_needed",
    "quality_gate_posture_insufficient_truth",
    "quality_gate_changed_area_runner_and_tests",
    "quality_gate_changed_area_runner_only",
    "quality_gate_changed_area_unknown",
    "quality_gate_changed_area_insufficient_truth",
    "quality_gate_risk_high",
    "quality_gate_risk_moderate",
    "quality_gate_risk_low",
    "quality_gate_risk_insufficient_truth",
    "quality_gate_targeted_regression_enabled",
    "quality_gate_targeted_regression_not_required",
}

_PROJECT_QUALITY_GATE_REASON_ORDER = (
    "quality_gate_insufficient_truth",
    "quality_gate_posture_insufficient_truth",
    "quality_gate_changed_area_insufficient_truth",
    "quality_gate_risk_insufficient_truth",
    "quality_gate_compiled",
    "quality_gate_posture_retry_needed",
    "quality_gate_posture_review_ready",
    "quality_gate_posture_merge_ready",
    "quality_gate_changed_area_runner_and_tests",
    "quality_gate_changed_area_runner_only",
    "quality_gate_changed_area_unknown",
    "quality_gate_risk_high",
    "quality_gate_risk_moderate",
    "quality_gate_risk_low",
    "quality_gate_targeted_regression_enabled",
    "quality_gate_targeted_regression_not_required",
)

_PROJECT_ROADMAP_REASON_CODES = {
    "roadmap_compiled",
    "roadmap_insufficient_truth",
}

_PROJECT_ROADMAP_REASON_ORDER = (
    "roadmap_insufficient_truth",
    "roadmap_compiled",
)

_REVIEW_ASSIMILATION_REASON_CODES = {
    "assimilation_queue_state_insufficient_truth",
    "assimilation_queue_empty",
    "assimilation_queue_blocked",
    "assimilation_prompt_unavailable",
    "assimilation_result_insufficient_truth",
    "assimilation_accept_succeeded",
    "assimilation_retry_retryable_failure",
    "assimilation_replan_design_invalid",
    "assimilation_split_scope_signal",
    "assimilation_escalate_manual_followup",
    "assimilation_escalate_unclassified",
}

_REVIEW_ASSIMILATION_REASON_ORDER = (
    "assimilation_queue_state_insufficient_truth",
    "assimilation_queue_empty",
    "assimilation_prompt_unavailable",
    "assimilation_queue_blocked",
    "assimilation_result_insufficient_truth",
    "assimilation_escalate_manual_followup",
    "assimilation_replan_design_invalid",
    "assimilation_split_scope_signal",
    "assimilation_retry_retryable_failure",
    "assimilation_accept_succeeded",
    "assimilation_escalate_unclassified",
)

_SELF_HEALING_REASON_CODES = {
    "self_healing_executed_retry",
    "self_healing_executed_replan",
    "self_healing_executed_truth_gather",
    "self_healing_executed_alternative_supported_repair",
    "self_healing_selected_retry",
    "self_healing_selected_replan",
    "self_healing_selected_truth_gather",
    "self_healing_selected_alternative_supported_repair",
    "self_healing_not_applicable_assimilation_no_action",
    "self_healing_not_applicable_assimilation_accept",
    "self_healing_insufficient_assimilation_truth",
    "self_healing_blocked_queue_non_runnable",
    "self_healing_blocked_safety_gate",
    "self_healing_blocked_budget_exhausted",
    "self_healing_blocked_branch_budget_exhausted",
    "self_healing_blocked_final_human_review",
    "self_healing_blocked_unsupported_action",
    "self_healing_blocked_alternative_repair_not_allowed",
}

_SELF_HEALING_REASON_ORDER = (
    "self_healing_insufficient_assimilation_truth",
    "self_healing_not_applicable_assimilation_accept",
    "self_healing_not_applicable_assimilation_no_action",
    "self_healing_blocked_queue_non_runnable",
    "self_healing_blocked_safety_gate",
    "self_healing_blocked_budget_exhausted",
    "self_healing_blocked_branch_budget_exhausted",
    "self_healing_blocked_final_human_review",
    "self_healing_blocked_alternative_repair_not_allowed",
    "self_healing_blocked_unsupported_action",
    "self_healing_selected_alternative_supported_repair",
    "self_healing_selected_truth_gather",
    "self_healing_selected_replan",
    "self_healing_selected_retry",
    "self_healing_executed_alternative_supported_repair",
    "self_healing_executed_truth_gather",
    "self_healing_executed_replan",
    "self_healing_executed_retry",
)

_SUPPORTED_REPAIR_EXECUTION_REASON_CODES = {
    "repair_not_selected",
    "repair_precheck_blocked",
    "repair_qualification_failed",
    "repair_launch_failed",
    "repair_verification_passed",
    "repair_verification_failed",
}

_SUPPORTED_REPAIR_EXECUTION_REASON_ORDER = (
    "repair_precheck_blocked",
    "repair_qualification_failed",
    "repair_launch_failed",
    "repair_verification_failed",
    "repair_verification_passed",
    "repair_not_selected",
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

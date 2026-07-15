from __future__ import annotations
from automation.orchestration.planned_runner.constants import *
from typing import Any
from typing import Mapping
from automation.orchestration.planned_runner.project_browser.constants import (
    _PROJECT_BROWSER_CONTINUATION_THRESHOLD,
    _PROJECT_BROWSER_RETRY_LIMIT,
)
from automation.orchestration.planned_runner.utils import (
    _as_non_negative_int,
    _normalize_string_list,
    _normalize_text,
)

def _build_approved_restart_execution_summary_surface(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    source = dict(payload or {})
    status = _normalize_text(source.get("automatic_restart_execution_status"), default="not_executed")
    if status not in _APPROVED_RESTART_EXECUTION_STATUSES:
        status = "not_executed"
    return {
        "automatic_restart_execution_status": status,
        "automatic_restart_executed": bool(source.get("automatic_restart_executed", False)),
        "automatic_restart_execution_reason": _normalize_text(
            source.get("automatic_restart_execution_reason"),
            default="restart_not_executed",
        ),
        "automatic_restart_result_status": _normalize_text(
            source.get("automatic_restart_result_status"),
            default="not_attempted",
        ),
        "approval_skip_gate_status": _normalize_text(
            source.get("approval_skip_gate_status"),
            default="approval_required",
        ),
        "approval_skip_allowed": bool(source.get("approval_skip_allowed", False)),
        "approval_skip_applied": bool(source.get("approval_skip_applied", False)),
        "approval_skip_reason": _normalize_text(
            source.get("approval_skip_reason"),
            default="skip_not_allowed",
        ),
        "continuation_budget_status": _normalize_text(
            source.get("continuation_budget_status"),
            default="insufficient_truth",
        ),
        "continuation_budget_decision": _normalize_text(
            source.get("continuation_budget_decision"),
            default="deny_insufficient_truth",
        ),
        "continuation_budget_reason": _normalize_text(
            source.get("continuation_budget_reason"),
            default="budget_insufficient_truth",
        ),
        "automatic_continuation_run_count": _as_non_negative_int(
            source.get("automatic_continuation_run_count"),
            default=0,
        ),
        "continuation_repair_playbook_selection_status": _normalize_text(
            source.get("continuation_repair_playbook_selection_status"),
            default="insufficient_truth",
        ),
        "continuation_repair_playbook_selected": bool(
            source.get("continuation_repair_playbook_selected", False)
        ),
        "continuation_repair_playbook_class": _normalize_text(
            source.get("continuation_repair_playbook_class"),
            default="no_plan",
        ),
        "continuation_next_step_selection_status": _normalize_text(
            source.get("continuation_next_step_selection_status"),
            default="insufficient_truth",
        ),
        "continuation_next_step_selected": bool(
            source.get("continuation_next_step_selected", False)
        ),
        "continuation_next_step_target": _normalize_text(
            source.get("continuation_next_step_target"),
            default="none",
        ),
        "continuation_next_step_reason": _normalize_text(
            source.get("continuation_next_step_reason"),
            default="next_step_not_selected",
        ),
        "supported_repair_execution_status": _normalize_text(
            source.get("supported_repair_execution_status"),
            default="not_selected",
        ),
        "supported_repair_execution_reason": _normalize_text(
            source.get("supported_repair_execution_reason"),
            default="repair_not_selected",
        ),
        "supported_repair_execution_attempted": bool(
            source.get("supported_repair_execution_attempted", False)
        ),
        "supported_repair_executed": bool(
            source.get("supported_repair_executed", False)
        ),
        "supported_repair_verification_passed": bool(
            source.get("supported_repair_verification_passed", False)
        ),
        "supported_repair_verification_failed": bool(
            source.get("supported_repair_verification_failed", False)
        ),
        "final_human_review_gate_status": _normalize_text(
            source.get("final_human_review_gate_status"),
            default="not_required",
        ),
        "final_human_review_required": bool(
            source.get("final_human_review_required", False)
        ),
        "final_human_review_reason": _normalize_text(
            source.get("final_human_review_reason"),
            default="final_review_not_required",
        ),
        "final_human_gate_preserved": bool(
            source.get("final_human_gate_preserved", False)
        ),
        "project_planning_summary_status": _normalize_text(
            source.get("project_planning_summary_status"),
            default="insufficient_truth",
        ),
        "project_planning_summary_available": bool(
            source.get("project_planning_summary_available", False)
        ),
        "project_planning_summary_reason": _normalize_text(
            source.get("project_planning_summary_reason"),
            default="planning_summary_insufficient_truth",
        ),
        "project_planning_control_posture": _normalize_text(
            source.get("project_planning_control_posture"),
            default="unknown",
        ),
        "project_roadmap_status": _normalize_text(
            source.get("project_roadmap_status"),
            default="insufficient_truth",
        ),
        "project_roadmap_item_count": _as_non_negative_int(
            source.get("project_roadmap_item_count"),
            default=0,
        ),
        "project_pr_slicing_status": _normalize_text(
            source.get("project_pr_slicing_status"),
            default="insufficient_truth",
        ),
        "project_pr_slice_count": _as_non_negative_int(
            source.get("project_pr_slice_count"),
            default=0,
        ),
        "project_pr_one_pr_size_decision": _normalize_text(
            source.get("project_pr_one_pr_size_decision"),
            default="not_available",
        ),
        "implementation_prompt_status": _normalize_text(
            source.get("implementation_prompt_status"),
            default="insufficient_truth",
        ),
        "implementation_prompt_available": bool(
            source.get("implementation_prompt_available", False)
        ),
        "implementation_prompt_reason": _normalize_text(
            source.get("implementation_prompt_reason"),
            default="prompt_planning_insufficient_truth",
        ),
        "implementation_prompt_slice_id": _normalize_text(
            source.get("implementation_prompt_slice_id"),
            default="",
        ),
        "implementation_prompt_roadmap_item_id": _normalize_text(
            source.get("implementation_prompt_roadmap_item_id"),
            default="",
        ),
        "project_pr_queue_status": _normalize_text(
            source.get("project_pr_queue_status"),
            default="insufficient_truth",
        ),
        "project_pr_queue_reason": _normalize_text(
            source.get("project_pr_queue_reason"),
            default="queue_state_insufficient_truth",
        ),
        "project_pr_queue_selected_slice_id": _normalize_text(
            source.get("project_pr_queue_selected_slice_id"),
            default="",
        ),
        "project_pr_queue_handoff_prepared": bool(
            source.get("project_pr_queue_handoff_prepared", False)
        ),
        "project_pr_queue_processed_count": len(
            _normalize_string_list(source.get("project_pr_queue_processed_slice_ids"))
        ),
        "review_assimilation_status": _normalize_text(
            source.get("review_assimilation_status"),
            default="insufficient_truth",
        ),
        "review_assimilation_action": _normalize_text(
            source.get("review_assimilation_action"),
            default="none",
        ),
        "review_assimilation_reason": _normalize_text(
            source.get("review_assimilation_reason"),
            default="assimilation_result_insufficient_truth",
        ),
        "review_assimilation_available": bool(
            source.get("review_assimilation_available", False)
        ),
        "self_healing_status": _normalize_text(
            source.get("self_healing_status"),
            default="insufficient_truth",
        ),
        "self_healing_transition_target": _normalize_text(
            source.get("self_healing_transition_target"),
            default="none",
        ),
        "self_healing_transition_executed": bool(
            source.get("self_healing_transition_executed", False)
        ),
        "self_healing_reason": _normalize_text(
            source.get("self_healing_reason"),
            default="self_healing_insufficient_assimilation_truth",
        ),
        "self_healing_human_fallback_preserved": bool(
            source.get("self_healing_human_fallback_preserved", False)
        ),
        "long_running_stability_status": _normalize_text(
            source.get("long_running_stability_status"),
            default="insufficient_truth",
        ),
        "long_running_reason": _normalize_text(
            source.get("long_running_reason"),
            default="long_running_insufficient_truth_queue_state",
        ),
        "long_running_pause_required": bool(
            source.get("long_running_pause_required", True)
        ),
        "long_running_resume_allowed": bool(
            source.get("long_running_resume_allowed", False)
        ),
        "long_running_escalation_required": bool(
            source.get("long_running_escalation_required", False)
        ),
        "objective_compiler_status": _normalize_text(
            source.get("objective_compiler_status"),
            default="insufficient_truth",
        ),
        "objective_completion_posture": _normalize_text(
            source.get("objective_completion_posture"),
            default="objective_insufficient_truth",
        ),
        "objective_done_criteria_status": _normalize_text(
            source.get("objective_done_criteria_status"),
            default="insufficient_truth",
        ),
        "objective_stop_criteria_status": _normalize_text(
            source.get("objective_stop_criteria_status"),
            default="insufficient_truth",
        ),
        "objective_scope_drift_status": _normalize_text(
            source.get("objective_scope_drift_status"),
            default="insufficient_truth",
        ),
        "objective_scope_drift_detected": bool(
            source.get("objective_scope_drift_detected", False)
        ),
        "project_autonomy_budget_status": _normalize_text(
            source.get("project_autonomy_budget_status"),
            default="insufficient_truth",
        ),
        "project_priority_posture": _normalize_text(
            source.get("project_priority_posture"),
            default="insufficient_truth",
        ),
        "project_high_risk_defer_posture": _normalize_text(
            source.get("project_high_risk_defer_posture"),
            default="insufficient_truth",
        ),
        "project_run_budget_posture": _normalize_text(
            source.get("project_run_budget_posture"),
            default="insufficient_truth",
        ),
        "project_objective_budget_posture": _normalize_text(
            source.get("project_objective_budget_posture"),
            default="insufficient_truth",
        ),
        "project_pr_retry_budget_posture": _normalize_text(
            source.get("project_pr_retry_budget_posture"),
            default="insufficient_truth",
        ),
        "project_quality_gate_status": _normalize_text(
            source.get("project_quality_gate_status"),
            default="insufficient_truth",
        ),
        "project_quality_gate_posture": _normalize_text(
            source.get("project_quality_gate_posture"),
            default="insufficient_truth",
        ),
        "project_quality_gate_recommended_count": _as_non_negative_int(
            source.get("project_quality_gate_recommended_count"),
            default=0,
        ),
        "project_quality_gate_changed_area_class": _normalize_text(
            source.get("project_quality_gate_changed_area_class"),
            default="unknown",
        ),
        "project_quality_gate_risk_level": _normalize_text(
            source.get("project_quality_gate_risk_level"),
            default="insufficient_truth",
        ),
        "project_merge_branch_lifecycle_status": _normalize_text(
            source.get("project_merge_branch_lifecycle_status"),
            default="insufficient_truth",
        ),
        "project_merge_ready_posture": _normalize_text(
            source.get("project_merge_ready_posture"),
            default="insufficient_truth",
        ),
        "project_branch_cleanup_candidate_posture": _normalize_text(
            source.get("project_branch_cleanup_candidate_posture"),
            default="insufficient_truth",
        ),
        "project_branch_quarantine_candidate_posture": _normalize_text(
            source.get("project_branch_quarantine_candidate_posture"),
            default="insufficient_truth",
        ),
        "project_local_main_sync_posture": _normalize_text(
            source.get("project_local_main_sync_posture"),
            default="insufficient_truth",
        ),
        "project_failure_memory_status": _normalize_text(
            source.get("project_failure_memory_status"),
            default="insufficient_truth",
        ),
        "project_failure_memory_suppression_posture": _normalize_text(
            source.get("project_failure_memory_suppression_posture"),
            default="insufficient_truth",
        ),
        "project_failure_memory_suppression_active": bool(
            source.get("project_failure_memory_suppression_active", False)
        ),
        "project_failure_memory_retry_failure_count": _as_non_negative_int(
            source.get("project_failure_memory_retry_failure_count"),
            default=0,
        ),
        "project_failure_memory_repair_failure_count": _as_non_negative_int(
            source.get("project_failure_memory_repair_failure_count"),
            default=0,
        ),
        "project_failure_memory_review_issue_count": _as_non_negative_int(
            source.get("project_failure_memory_review_issue_count"),
            default=0,
        ),
        "project_failure_memory_failure_bucket_recurrence_count": _as_non_negative_int(
            source.get("project_failure_memory_failure_bucket_recurrence_count"),
            default=0,
        ),
        "project_external_boundary_status": _normalize_text(
            source.get("project_external_boundary_status"),
            default="insufficient_truth",
        ),
        "project_external_dependency_posture": _normalize_text(
            source.get("project_external_dependency_posture"),
            default="insufficient_truth",
        ),
        "project_external_manual_only_posture": _normalize_text(
            source.get("project_external_manual_only_posture"),
            default="insufficient_truth",
        ),
        "project_external_network_boundary_posture": _normalize_text(
            source.get("project_external_network_boundary_posture"),
            default="insufficient_truth",
        ),
        "project_external_ci_boundary_posture": _normalize_text(
            source.get("project_external_ci_boundary_posture"),
            default="insufficient_truth",
        ),
        "project_external_secrets_boundary_posture": _normalize_text(
            source.get("project_external_secrets_boundary_posture"),
            default="insufficient_truth",
        ),
        "project_external_github_boundary_posture": _normalize_text(
            source.get("project_external_github_boundary_posture"),
            default="insufficient_truth",
        ),
        "project_external_api_boundary_posture": _normalize_text(
            source.get("project_external_api_boundary_posture"),
            default="insufficient_truth",
        ),
        "project_external_dependency_blocked": bool(
            source.get("project_external_dependency_blocked", False)
        ),
        "project_external_manual_only_required": bool(
            source.get("project_external_manual_only_required", False)
        ),
        "project_human_escalation_status": _normalize_text(
            source.get("project_human_escalation_status"),
            default="insufficient_truth",
        ),
        "project_human_escalation_posture": _normalize_text(
            source.get("project_human_escalation_posture"),
            default="insufficient_truth",
        ),
        "project_human_escalation_required": bool(
            source.get("project_human_escalation_required", False)
        ),
        "project_human_escalation_reason": _normalize_text(
            source.get("project_human_escalation_reason"),
            default="escalation_insufficient_truth",
        ),
        "project_architecture_risk_posture": _normalize_text(
            source.get("project_architecture_risk_posture"),
            default="insufficient_truth",
        ),
        "project_scope_risk_posture": _normalize_text(
            source.get("project_scope_risk_posture"),
            default="insufficient_truth",
        ),
        "project_external_risk_posture": _normalize_text(
            source.get("project_external_risk_posture"),
            default="insufficient_truth",
        ),
        "project_budget_risk_posture": _normalize_text(
            source.get("project_budget_risk_posture"),
            default="insufficient_truth",
        ),
        "project_repeated_failure_risk_posture": _normalize_text(
            source.get("project_repeated_failure_risk_posture"),
            default="insufficient_truth",
        ),
        "project_manual_only_risk_posture": _normalize_text(
            source.get("project_manual_only_risk_posture"),
            default="insufficient_truth",
        ),
        "project_approval_notification_status": _normalize_text(
            source.get("project_approval_notification_status"),
            default="insufficient_truth",
        ),
        "project_approval_notification_ready_posture": _normalize_text(
            source.get("project_approval_notification_ready_posture"),
            default="insufficient_truth",
        ),
        "project_approval_notification_ready": bool(
            source.get("project_approval_notification_ready", False)
        ),
        "project_approval_reply_required_posture": _normalize_text(
            source.get("project_approval_reply_required_posture"),
            default="insufficient_truth",
        ),
        "project_approval_reply_required": bool(
            source.get("project_approval_reply_required", False)
        ),
        "project_approval_channel_posture": _normalize_text(
            source.get("project_approval_channel_posture"),
            default="insufficient_truth",
        ),
        "project_approval_mobile_summary_posture": _normalize_text(
            source.get("project_approval_mobile_summary_posture"),
            default="insufficient_truth",
        ),
        "project_approval_mobile_summary_compact": _normalize_text(
            source.get("project_approval_mobile_summary_compact"),
            default="",
        ),
        "project_approval_notification_reason": _normalize_text(
            source.get("project_approval_notification_reason"),
            default="approval_notification_insufficient_truth",
        ),
        "project_multi_objective_status": _normalize_text(
            source.get("project_multi_objective_status"),
            default="insufficient_truth",
        ),
        "project_multi_objective_reason": _normalize_text(
            source.get("project_multi_objective_reason"),
            default="multi_objective_insufficient_truth",
        ),
        "project_active_objective_selection_posture": _normalize_text(
            source.get("project_active_objective_selection_posture"),
            default="insufficient_truth",
        ),
        "project_blocked_objective_deferral_posture": _normalize_text(
            source.get("project_blocked_objective_deferral_posture"),
            default="insufficient_truth",
        ),
        "project_resumable_queue_ordering_posture": _normalize_text(
            source.get("project_resumable_queue_ordering_posture"),
            default="insufficient_truth",
        ),
        "project_resumable_queue_ordering_key": _normalize_text(
            source.get("project_resumable_queue_ordering_key"),
            default="",
        ),
        "project_resumable_queue_next_slice_id": _normalize_text(
            source.get("project_resumable_queue_next_slice_id"),
            default="",
        ),
        "project_resumable_queue_has_pending": bool(
            source.get("project_resumable_queue_has_pending", False)
        ),
        "project_browser_task_status": _normalize_text(
            source.get("project_browser_task_status"),
            default="inactive",
        ),
        "project_browser_task_reason": _normalize_text(
            source.get("project_browser_task_reason"),
            default="browser_task_inactive",
        ),
        "project_browser_task_type": _normalize_text(
            source.get("project_browser_task_type"),
            default="none",
        ),
        "project_browser_task_envelope_status": _normalize_text(
            source.get("project_browser_task_envelope_status"),
            default="inactive",
        ),
        "project_browser_response_status": _normalize_text(
            source.get("project_browser_response_status"),
            default="inactive",
        ),
        "project_browser_chat_turn_count": _as_non_negative_int(
            source.get("project_browser_chat_turn_count"),
            default=0,
        ),
        "project_browser_chat_rotation_due": bool(
            source.get("project_browser_chat_rotation_due", False)
        ),
        "project_browser_handoff_summary_required": bool(
            source.get("project_browser_handoff_summary_required", False)
        ),
        "project_browser_handoff_summary_available": bool(
            source.get("project_browser_handoff_summary_available", False)
        ),
        "project_browser_continuation_threshold": _as_non_negative_int(
            source.get("project_browser_continuation_threshold"),
            default=_PROJECT_BROWSER_CONTINUATION_THRESHOLD,
        ),
        "project_browser_retry_limit": _as_non_negative_int(
            source.get("project_browser_retry_limit"),
            default=_PROJECT_BROWSER_RETRY_LIMIT,
        ),
        "project_browser_selector_contract_status": _normalize_text(
            source.get("project_browser_selector_contract_status"),
            default="insufficient_truth",
        ),
        "project_browser_ui_readiness_status": _normalize_text(
            source.get("project_browser_ui_readiness_status"),
            default="insufficient_truth",
        ),
        "project_browser_ui_failure_status": _normalize_text(
            source.get("project_browser_ui_failure_status"),
            default="insufficient_truth",
        ),
        "project_browser_ui_recovery_recommended": _normalize_text(
            source.get("project_browser_ui_recovery_recommended"),
            default="",
        ),
        "project_browser_prompt_payload_status": _normalize_text(
            source.get("project_browser_prompt_payload_status"),
            default="insufficient_truth",
        ),
        "project_browser_prompt_context_level": _normalize_text(
            source.get("project_browser_prompt_context_level"),
            default="insufficient_truth",
        ),
        "project_browser_prompt_token_posture": _normalize_text(
            source.get("project_browser_prompt_token_posture"),
            default="blocked_insufficient_truth",
        ),
        "project_browser_response_assimilation_status": _normalize_text(
            source.get("project_browser_response_assimilation_status"),
            default="insufficient_truth",
        ),
        "project_browser_assimilated_decision": _normalize_text(
            source.get("project_browser_assimilated_decision"),
            default="unavailable",
        ),
        "project_browser_next_action_posture": _normalize_text(
            source.get("project_browser_next_action_posture"),
            default="no_action",
        ),
        "project_browser_ui_recovery_decision_status": _normalize_text(
            source.get("project_browser_ui_recovery_decision_status"),
            default="inactive",
        ),
        "project_browser_recovery_candidate": _normalize_text(
            source.get("project_browser_recovery_candidate"),
            default="none",
        ),
        "project_browser_recovery_reason": _normalize_text(
            source.get("project_browser_recovery_reason"),
            default="no_failure",
        ),
        "project_browser_retry_count_posture": _normalize_text(
            source.get("project_browser_retry_count_posture"),
            default="not_applicable",
        ),
        "project_browser_handoff_dependency_posture": _normalize_text(
            source.get("project_browser_handoff_dependency_posture"),
            default="not_required",
        ),
        "project_browser_handoff_compile_status": _normalize_text(
            source.get("project_browser_handoff_compile_status"),
            default="inactive",
        ),
        "project_browser_handoff_trigger": _normalize_text(
            source.get("project_browser_handoff_trigger"),
            default="none",
        ),
        "project_browser_handoff_payload_posture": _normalize_text(
            source.get("project_browser_handoff_payload_posture"),
            default="unavailable",
        ),
        "project_browser_execution_handoff_status": _normalize_text(
            source.get("project_browser_execution_handoff_status"),
            default="inactive",
        ),
        "project_browser_execution_handoff_kind": _normalize_text(
            source.get("project_browser_execution_handoff_kind"),
            default="none",
        ),
        "project_browser_execution_block_reason": _normalize_text(
            source.get("project_browser_execution_block_reason"),
            default="none",
        ),
        "project_browser_command_queue_status": _normalize_text(
            source.get("project_browser_command_queue_status"),
            default="inactive",
        ),
        "project_browser_command_queue_mode": _normalize_text(
            source.get("project_browser_command_queue_mode"),
            default="none",
        ),
        "project_browser_command_type": _normalize_text(
            source.get("project_browser_command_type"),
            default="none",
        ),
        "project_browser_command_source": _normalize_text(
            source.get("project_browser_command_source"),
            default="none",
        ),
        "project_browser_command_block_reason": _normalize_text(
            source.get("project_browser_command_block_reason"),
            default="none",
        ),
        "project_browser_command_receipt_status": _normalize_text(
            source.get("project_browser_command_receipt_status"),
            default="not_created",
        ),
        "project_browser_command_receipt_kind": _normalize_text(
            source.get("project_browser_command_receipt_kind"),
            default="none",
        ),
        "project_browser_command_receipt_result": _normalize_text(
            source.get("project_browser_command_receipt_result"),
            default="not_executed",
        ),
        "project_browser_playwright_boundary_status": _normalize_text(
            source.get("project_browser_playwright_boundary_status"),
            default="inactive",
        ),
        "project_browser_playwright_import_posture": _normalize_text(
            source.get("project_browser_playwright_import_posture"),
            default="not_checked",
        ),
        "project_browser_session_config_status": _normalize_text(
            source.get("project_browser_session_config_status"),
            default="inactive",
        ),
        "project_browser_session_mode": _normalize_text(
            source.get("project_browser_session_mode"),
            default="none",
        ),
        "project_browser_launch_preflight_status": _normalize_text(
            source.get("project_browser_launch_preflight_status"),
            default="inactive",
        ),
        "project_browser_launch_preflight_mode": _normalize_text(
            source.get("project_browser_launch_preflight_mode"),
            default="none",
        ),
        "project_browser_login_preflight_posture": _normalize_text(
            source.get("project_browser_login_preflight_posture"),
            default="not_checked",
        ),
        "project_browser_runtime_block_reason": _normalize_text(
            source.get("project_browser_runtime_block_reason"),
            default="none",
        ),
        "project_browser_launch_preflight_receipt_status": _normalize_text(
            source.get("project_browser_launch_preflight_receipt_status"),
            default="not_created",
        ),
        "project_browser_launch_preflight_receipt_kind": _normalize_text(
            source.get("project_browser_launch_preflight_receipt_kind"),
            default="none",
        ),
        "project_browser_launch_receipt_status": _normalize_text(
            source.get("project_browser_launch_receipt_status"),
            default="not_created",
        ),
        "project_browser_launch_receipt_kind": _normalize_text(
            source.get("project_browser_launch_receipt_kind"),
            default="none",
        ),
        "project_browser_selector_resolver_status": _normalize_text(
            source.get("project_browser_selector_resolver_status"),
            default="inactive",
        ),
        "project_browser_selector_probe_status": _normalize_text(
            source.get("project_browser_selector_probe_status"),
            default="inactive",
        ),
        "project_browser_dom_readiness_status": _normalize_text(
            source.get("project_browser_dom_readiness_status"),
            default="inactive",
        ),
        "project_browser_dom_probe_block_reason": _normalize_text(
            source.get("project_browser_dom_probe_block_reason"),
            default="none",
        ),
        "project_browser_selector_probe_receipt_status": _normalize_text(
            source.get("project_browser_selector_probe_receipt_status"),
            default="not_created",
        ),
        "project_browser_selector_probe_receipt_kind": _normalize_text(
            source.get("project_browser_selector_probe_receipt_kind"),
            default="none",
        ),
        "project_browser_prompt_fill_status": _normalize_text(
            source.get("project_browser_prompt_fill_status"),
            default="insufficient_truth",
        ),
        "project_browser_prompt_fill_source_status": _normalize_text(
            source.get("project_browser_prompt_fill_source_status"),
            default="insufficient_truth",
        ),
        "project_browser_prompt_fill_target_status": _normalize_text(
            source.get("project_browser_prompt_fill_target_status"),
            default="insufficient_truth",
        ),
        "project_browser_prompt_fill_block_reason": _normalize_text(
            source.get("project_browser_prompt_fill_block_reason"),
            default="insufficient_truth",
        ),
        "project_browser_prompt_fill_receipt_status": _normalize_text(
            source.get("project_browser_prompt_fill_receipt_status"),
            default="insufficient_truth",
        ),
        "project_browser_prompt_fill_receipt_kind": _normalize_text(
            source.get("project_browser_prompt_fill_receipt_kind"),
            default="none",
        ),
        "project_browser_prompt_send_status": _normalize_text(
            source.get("project_browser_prompt_send_status"),
            default="insufficient_truth",
        ),
        "project_browser_prompt_send_target_status": _normalize_text(
            source.get("project_browser_prompt_send_target_status"),
            default="insufficient_truth",
        ),
        "project_browser_prompt_send_block_reason": _normalize_text(
            source.get("project_browser_prompt_send_block_reason"),
            default="insufficient_truth",
        ),
        "project_browser_prompt_send_receipt_status": _normalize_text(
            source.get("project_browser_prompt_send_receipt_status"),
            default="insufficient_truth",
        ),
        "project_browser_prompt_send_receipt_kind": _normalize_text(
            source.get("project_browser_prompt_send_receipt_kind"),
            default="none",
        ),
        "project_browser_response_wait_status": _normalize_text(
            source.get("project_browser_response_wait_status"),
            default="insufficient_truth",
        ),
        "project_browser_response_read_status": _normalize_text(
            source.get("project_browser_response_read_status"),
            default="insufficient_truth",
        ),
        "project_browser_response_text_status": _normalize_text(
            source.get("project_browser_response_text_status"),
            default="insufficient_truth",
        ),
        "project_browser_response_wait_block_reason": _normalize_text(
            source.get("project_browser_response_wait_block_reason"),
            default="insufficient_truth",
        ),
        "project_browser_response_read_receipt_status": _normalize_text(
            source.get("project_browser_response_read_receipt_status"),
            default="insufficient_truth",
        ),
        "project_browser_response_read_receipt_kind": _normalize_text(
            source.get("project_browser_response_read_receipt_kind"),
            default="none",
        ),
        "project_browser_response_json_parse_status": _normalize_text(
            source.get("project_browser_response_json_parse_status"),
            default="insufficient_truth",
        ),
        "project_browser_response_json_schema_status": _normalize_text(
            source.get("project_browser_response_json_schema_status"),
            default="insufficient_truth",
        ),
        "project_browser_response_json_decision_status": _normalize_text(
            source.get("project_browser_response_json_decision_status"),
            default="insufficient_truth",
        ),
        "project_browser_execution_receipt_status": _normalize_text(
            source.get("project_browser_execution_receipt_status"),
            default="insufficient_truth",
        ),
        "project_browser_execution_receipt_kind": _normalize_text(
            source.get("project_browser_execution_receipt_kind"),
            default="none",
        ),
        "project_browser_execution_result_status": _normalize_text(
            source.get("project_browser_execution_result_status"),
            default="insufficient_truth",
        ),
        "project_browser_response_parse_block_reason": _normalize_text(
            source.get("project_browser_response_parse_block_reason"),
            default="insufficient_truth",
        ),
        "project_browser_recovery_status": _normalize_text(
            source.get("project_browser_recovery_status"),
            default="insufficient_truth",
        ),
        "project_browser_recovery_action": _normalize_text(
            source.get("project_browser_recovery_action"),
            default="none",
        ),
        "project_browser_recovery_reason_runtime": _normalize_text(
            source.get("project_browser_recovery_reason_runtime"),
            default="insufficient_truth",
        ),
        "project_browser_recovery_block_reason": _normalize_text(
            source.get("project_browser_recovery_block_reason"),
            default="insufficient_truth",
        ),
        "project_browser_recovery_receipt_status": _normalize_text(
            source.get("project_browser_recovery_receipt_status"),
            default="insufficient_truth",
        ),
        "project_browser_recovery_receipt_kind": _normalize_text(
            source.get("project_browser_recovery_receipt_kind"),
            default="none",
        ),
        "project_browser_one_command_executor_status": _normalize_text(
            source.get("project_browser_one_command_executor_status"),
            default="insufficient_truth",
        ),
        "project_browser_one_command_executor_result": _normalize_text(
            source.get("project_browser_one_command_executor_result"),
            default="insufficient_truth",
        ),
        "project_browser_one_command_executor_stop_reason": _normalize_text(
            source.get("project_browser_one_command_executor_stop_reason"),
            default="insufficient_truth",
        ),
        "project_browser_one_command_executor_receipt_status": _normalize_text(
            source.get("project_browser_one_command_executor_receipt_status"),
            default="insufficient_truth",
        ),
        "project_browser_one_command_executor_receipt_kind": _normalize_text(
            source.get("project_browser_one_command_executor_receipt_kind"),
            default="none",
        ),
        "project_browser_autonomous_dev_assimilation_status": _normalize_text(
            source.get("project_browser_autonomous_dev_assimilation_status"),
            default="insufficient_truth",
        ),
        "project_browser_autonomous_dev_outcome": _normalize_text(
            source.get("project_browser_autonomous_dev_outcome"),
            default="insufficient_truth",
        ),
        "project_browser_autonomous_dev_next_action": _normalize_text(
            source.get("project_browser_autonomous_dev_next_action"),
            default="stop",
        ),
        "project_browser_autonomous_dev_stop_reason": _normalize_text(
            source.get("project_browser_autonomous_dev_stop_reason"),
            default="insufficient_truth",
        ),
        "project_browser_same_prompt_retry_policy": _normalize_text(
            source.get("project_browser_same_prompt_retry_policy"),
            default="insufficient_truth",
        ),
        "project_browser_same_prompt_retry_reason": _normalize_text(
            source.get("project_browser_same_prompt_retry_reason"),
            default="insufficient_truth",
        ),
        "project_browser_autonomous_next_prompt_draft_status": _normalize_text(
            source.get("project_browser_autonomous_next_prompt_draft_status"),
            default="insufficient_truth",
        ),
        "project_browser_autonomous_next_prompt_kind": _normalize_text(
            source.get("project_browser_autonomous_next_prompt_kind"),
            default="none",
        ),
        "project_browser_autonomous_next_prompt_scope": _normalize_text(
            source.get("project_browser_autonomous_next_prompt_scope"),
            default="none",
        ),
        "project_browser_autonomous_next_prompt_source": _normalize_text(
            source.get("project_browser_autonomous_next_prompt_source"),
            default="insufficient_truth",
        ),
        "project_browser_autonomous_next_prompt_block_reason": _normalize_text(
            source.get("project_browser_autonomous_next_prompt_block_reason"),
            default="insufficient_truth",
        ),
        "project_browser_autonomous_md_update_draft_status": _normalize_text(
            source.get("project_browser_autonomous_md_update_draft_status"),
            default="insufficient_truth",
        ),
        "project_browser_autonomous_md_update_kind": _normalize_text(
            source.get("project_browser_autonomous_md_update_kind"),
            default="none",
        ),
        "project_browser_autonomous_md_update_command_draft_status": _normalize_text(
            source.get("project_browser_autonomous_md_update_command_draft_status"),
            default="insufficient_truth",
        ),
        "project_browser_autonomous_md_update_block_reason": _normalize_text(
            source.get("project_browser_autonomous_md_update_block_reason"),
            default="insufficient_truth",
        ),
        "project_browser_autonomous_continuation_gate_status": _normalize_text(
            source.get("project_browser_autonomous_continuation_gate_status"),
            default="insufficient_truth",
        ),
        "project_browser_autonomous_continuation_next_action": _normalize_text(
            source.get("project_browser_autonomous_continuation_next_action"),
            default="stop",
        ),
        "project_browser_autonomous_continuation_block_reason": _normalize_text(
            source.get("project_browser_autonomous_continuation_block_reason"),
            default="insufficient_truth",
        ),
        "project_browser_autonomous_duplicate_policy_status": _normalize_text(
            source.get("project_browser_autonomous_duplicate_policy_status"),
            default="insufficient_truth",
        ),
        "project_browser_autonomous_duplicate_reason": _normalize_text(
            source.get("project_browser_autonomous_duplicate_reason"),
            default="insufficient_truth",
        ),
        "project_browser_autonomous_retry_budget_posture": _normalize_text(
            source.get("project_browser_autonomous_retry_budget_posture"),
            default="insufficient_truth",
        ),
        "project_browser_autonomous_controller_status": _normalize_text(
            source.get("project_browser_autonomous_controller_status"),
            default="insufficient_truth",
        ),
        "project_browser_autonomous_controller_action": _normalize_text(
            source.get("project_browser_autonomous_controller_action"),
            default="none",
        ),
        "project_browser_autonomous_controller_action_source": _normalize_text(
            source.get("project_browser_autonomous_controller_action_source"),
            default="insufficient_truth",
        ),
        "project_browser_autonomous_controller_stop_reason": _normalize_text(
            source.get("project_browser_autonomous_controller_stop_reason"),
            default="insufficient_truth",
        ),
        "project_browser_autonomous_controller_receipt_status": _normalize_text(
            source.get("project_browser_autonomous_controller_receipt_status"),
            default="insufficient_truth",
        ),
        "project_browser_autonomous_controller_receipt_kind": _normalize_text(
            source.get("project_browser_autonomous_controller_receipt_kind"),
            default="none",
        ),
        "project_browser_launch_status": _normalize_text(
            source.get("project_browser_launch_status"),
            default="inactive",
        ),
        "project_browser_context_status": _normalize_text(
            source.get("project_browser_context_status"),
            default="inactive",
        ),
        "project_browser_page_open_status": _normalize_text(
            source.get("project_browser_page_open_status"),
            default="inactive",
        ),
        "project_browser_chatgpt_page_status": _normalize_text(
            source.get("project_browser_chatgpt_page_status"),
            default="inactive",
        ),
        "project_browser_login_interruption_status": _normalize_text(
            source.get("project_browser_login_interruption_status"),
            default="not_checked",
        ),
        "project_browser_launch_block_reason": _normalize_text(
            source.get("project_browser_launch_block_reason"),
            default="none",
        ),
        "project_browser_executor_interface_status": _normalize_text(
            source.get("project_browser_executor_interface_status"),
            default="insufficient_truth",
        ),
        "project_browser_executor_mode": _normalize_text(
            source.get("project_browser_executor_mode"),
            default="none",
        ),
        "project_browser_executor_receipt_status": _normalize_text(
            source.get("project_browser_executor_receipt_status"),
            default="not_created",
        ),
        "project_browser_executor_block_reason": _normalize_text(
            source.get("project_browser_executor_block_reason"),
            default="none",
        ),
    }


__all__ = [
    "_build_approved_restart_execution_summary_surface",
]

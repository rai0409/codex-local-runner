from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import subprocess
from typing import Any
from typing import Callable
from typing import Mapping

from automation.control.action_handoff import build_action_handoff_payload
from automation.control.next_action_controller import evaluate_next_action_from_run_dir
from automation.control.retry_context_store import FileRetryContextStore
from automation.execution.codex_executor_adapter import CodexExecutionTransport
from automation.execution.codex_executor_adapter import CodexExecutorAdapter
from automation.orchestration.approval_transport import build_approval_run_state_summary_surface
from automation.orchestration.artifact_index import build_contract_artifact_index
from automation.orchestration.approval_transport import build_approval_transport_surface
from automation.orchestration.completion_contract import build_completion_contract_surface
from automation.orchestration.completion_contract import build_completion_run_state_summary_surface
from automation.orchestration.execution_authorization_gate import (
    build_execution_authorization_gate_run_state_summary_surface,
)
from automation.orchestration.execution_authorization_gate import build_execution_authorization_gate_surface
from automation.orchestration.execution_result_contract import (
    build_execution_result_contract_run_state_summary_surface,
)
from automation.orchestration.execution_result_contract import build_execution_result_contract_surface
from automation.orchestration.verification_closure_contract import (
    build_verification_closure_contract_surface,
)
from automation.orchestration.verification_closure_contract import (
    build_verification_closure_run_state_summary_surface,
)
from automation.orchestration.retry_reentry_loop_contract import (
    build_retry_reentry_loop_contract_surface,
)
from automation.orchestration.retry_reentry_loop_contract import (
    build_retry_reentry_loop_run_state_summary_surface,
)
from automation.orchestration.endgame_closure_contract import (
    build_endgame_closure_contract_surface,
)
from automation.orchestration.endgame_closure_contract import (
    build_endgame_closure_run_state_summary_surface,
)
from automation.orchestration.loop_hardening_contract import (
    build_loop_hardening_contract_surface,
)
from automation.orchestration.loop_hardening_contract import (
    build_loop_hardening_run_state_summary_surface,
)
from automation.orchestration.lane_stabilization_contract import (
    build_lane_stabilization_contract_surface,
)
from automation.orchestration.lane_stabilization_contract import (
    build_lane_stabilization_run_state_summary_surface,
)
from automation.orchestration.observability_rollup import (
    build_failure_bucket_rollup_summary_surface,
)
from automation.orchestration.observability_rollup import (
    build_failure_bucket_rollup_surface,
)
from automation.orchestration.observability_rollup import (
    build_fleet_run_rollup_summary_surface,
)
from automation.orchestration.observability_rollup import (
    build_fleet_run_rollup_surface,
)
from automation.orchestration.observability_rollup import (
    build_observability_rollup_contract_summary_surface,
)
from automation.orchestration.observability_rollup import (
    build_observability_rollup_contract_surface,
)
from automation.orchestration.observability_rollup import (
    build_observability_rollup_run_state_summary_surface,
)
from automation.orchestration.failure_bucketing_hardening import (
    build_failure_bucketing_hardening_run_state_summary_surface,
)
from automation.orchestration.failure_bucketing_hardening import (
    build_failure_bucketing_hardening_summary_surface,
)
from automation.orchestration.failure_bucketing_hardening import (
    build_failure_bucketing_hardening_contract_surface,
)
from automation.orchestration.artifact_retention import (
    build_artifact_retention_contract_surface,
)
from automation.orchestration.artifact_retention import (
    build_artifact_retention_run_state_summary_surface,
)
from automation.orchestration.artifact_retention import (
    build_artifact_retention_summary_surface,
)
from automation.orchestration.artifact_retention import (
    build_retention_manifest_summary_surface,
)
from automation.orchestration.artifact_retention import (
    build_retention_manifest_surface,
)
from automation.orchestration.fleet_safety_control import (
    build_fleet_safety_control_contract_surface,
)
from automation.orchestration.fleet_safety_control import (
    build_fleet_safety_control_run_state_summary_surface,
)
from automation.orchestration.fleet_safety_control import (
    build_fleet_safety_control_summary_surface,
)
from automation.orchestration.approval_email_delivery import (
    build_approval_email_delivery_contract_surface,
)
from automation.orchestration.approval_email_delivery import (
    build_approval_email_delivery_run_state_summary_surface,
)
from automation.orchestration.approval_email_delivery import (
    build_approval_email_delivery_summary_surface,
)
from automation.orchestration.approval_runtime_policy import (
    build_approval_runtime_rules_contract_surface,
)
from automation.orchestration.approval_runtime_policy import (
    build_approval_runtime_rules_run_state_summary_surface,
)
from automation.orchestration.approval_runtime_policy import (
    build_approval_runtime_rules_summary_surface,
)
from automation.orchestration.approval_delivery_adapter import (
    build_approval_delivery_handoff_contract_surface,
)
from automation.orchestration.approval_delivery_adapter import (
    build_approval_delivery_handoff_run_state_summary_surface,
)
from automation.orchestration.approval_delivery_adapter import (
    build_approval_delivery_handoff_summary_surface,
)
from automation.orchestration.approval_response_ingest import (
    build_approved_restart_contract_surface,
)
from automation.orchestration.approval_response_ingest import (
    build_approved_restart_run_state_summary_surface,
)
from automation.orchestration.approval_response_ingest import (
    build_approved_restart_summary_surface,
)
from automation.orchestration.approval_response_ingest import (
    build_approval_response_contract_surface,
)
from automation.orchestration.approval_response_ingest import (
    build_approval_response_run_state_summary_surface,
)
from automation.orchestration.approval_response_ingest import (
    build_approval_response_summary_surface,
)
from automation.orchestration.approval_safety import (
    build_approval_safety_contract_surface,
)
from automation.orchestration.approval_safety import (
    build_approval_safety_run_state_summary_surface,
)
from automation.orchestration.approval_safety import (
    build_approval_safety_summary_surface,
)
from automation.orchestration.bounded_execution_bridge import (
    build_bounded_execution_bridge_run_state_summary_surface,
)
from automation.orchestration.bounded_execution_bridge import build_bounded_execution_bridge_surface
from automation.orchestration.lifecycle_terminal_state import build_lifecycle_terminal_state_surface
from automation.orchestration.objective_contract import build_objective_contract_surface
from automation.orchestration.objective_contract import build_objective_run_state_summary_surface
from automation.orchestration.operator_explainability import build_operator_explainability_surface
from automation.orchestration.repair_suggestion_contract import build_repair_suggestion_contract_surface
from automation.orchestration.repair_suggestion_contract import build_repair_suggestion_run_state_summary_surface
from automation.orchestration.repair_approval_binding import build_repair_approval_binding_run_state_summary_surface
from automation.orchestration.repair_approval_binding import build_repair_approval_binding_surface
from automation.orchestration.repair_plan_transport import build_repair_plan_transport_run_state_summary_surface
from automation.orchestration.repair_plan_transport import build_repair_plan_transport_surface
from automation.orchestration.repair_plan_transport import REPAIR_PLAN_CANDIDATE_ACTIONS
from automation.orchestration.repair_plan_transport import REPAIR_PLAN_CLASSES
from automation.orchestration.reconcile_contract import build_reconcile_contract_surface
from automation.orchestration.reconcile_contract import build_reconcile_run_state_summary_surface
from automation.orchestration.run_state_summary_contract import build_manifest_run_state_summary_contract_surface
from automation.orchestration.run_state_summary_contract import select_manifest_run_state_summary_compact
from automation.planning.prompt_compiler import compile_prompt_units
from automation.planning.prompt_compiler import load_planning_artifacts

_UNIT_PROGRESSION_SCHEMA_VERSION = "v1"

_UNIT_STATE_PLANNED = "planned"
_UNIT_STATE_PROMPT_READY = "prompt_ready"
_UNIT_STATE_EXECUTION_READY = "execution_ready"
_UNIT_STATE_EXECUTION_COMPLETED = "execution_completed"
_UNIT_STATE_REVIEWED = "reviewed"
_UNIT_STATE_ADVANCED = "advanced"
_UNIT_STATE_ESCALATED = "escalated"

_DECISION_SCHEMA_VERSION = "v1"
_CHECKPOINT_SCHEMA_VERSION = "v1"
_RUN_STATE_SCHEMA_VERSION = "v1"
_COMMIT_EXECUTION_SCHEMA_VERSION = "v1"
_PUSH_EXECUTION_SCHEMA_VERSION = "v1"
_PR_EXECUTION_SCHEMA_VERSION = "v1"
_MERGE_EXECUTION_SCHEMA_VERSION = "v1"
_ROLLBACK_EXECUTION_SCHEMA_VERSION = "v1"

_COMMIT_DECISIONS = {"allowed", "blocked", "manual_required", "unknown"}
_MERGE_DECISIONS = {"allowed", "blocked", "manual_required", "unknown"}
_ROLLBACK_DECISIONS = {"required", "not_required", "blocked", "manual_required", "unknown"}
_READINESS_STATUSES = {"ready", "not_ready", "manual_required", "blocked", "awaiting_prerequisites"}
_READINESS_NEXT_ACTIONS = {
    "prepare_commit",
    "prepare_merge",
    "prepare_rollback_evaluation",
    "await_manual_review",
    "resolve_blockers",
    "hold",
}
_CHECKPOINT_STAGES = {
    "post_execution",
    "post_review",
    "pre_commit_evaluation",
    "pre_merge_evaluation",
    "pre_rollback_evaluation",
}
_CHECKPOINT_DECISIONS = {
    "proceed",
    "pause",
    "retry",
    "manual_review_required",
    "escalate",
    "commit_evaluation_ready",
    "merge_evaluation_ready",
    "rollback_evaluation_ready",
    "global_stop_recommended",
}

_RUN_STATES = {
    "intake_received",
    "planning_completed",
    "units_generated",
    "execution_in_progress",
    "review_in_progress",
    "decision_in_progress",
    "commit_ready",
    "merge_ready",
    "post_merge_verifying",
    "paused",
    "rollback_in_progress",
    "rolled_back",
    "completed",
    "failed_terminal",
}

_RUN_STATE_ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "intake_received": ("planning_completed", "failed_terminal"),
    "planning_completed": ("units_generated", "failed_terminal"),
    "units_generated": ("execution_in_progress", "failed_terminal"),
    "execution_in_progress": ("review_in_progress", "failed_terminal"),
    "review_in_progress": ("decision_in_progress", "paused", "failed_terminal"),
    "decision_in_progress": ("commit_ready", "merge_ready", "rollback_in_progress", "paused", "failed_terminal"),
    "commit_ready": ("post_merge_verifying", "paused", "failed_terminal"),
    "merge_ready": ("post_merge_verifying", "paused", "failed_terminal"),
    "post_merge_verifying": ("completed", "rollback_in_progress", "failed_terminal"),
    "paused": ("decision_in_progress", "execution_in_progress", "failed_terminal"),
    "rollback_in_progress": ("rolled_back", "failed_terminal"),
    "rolled_back": ("completed", "failed_terminal"),
    "completed": (),
    "failed_terminal": (),
}

_ORCHESTRATION_STATES = {
    "planning_completed",
    "units_generated",
    "execution_in_progress",
    "checkpoint_evaluation_in_progress",
    "run_ready_to_continue",
    "paused_for_manual_review",
    "rollback_evaluation_pending",
    "global_stop_pending",
    "completed",
    "failed_terminal",
}

_RUN_NEXT_ACTIONS = {
    "continue_run",
    "pause_run",
    "await_manual_review",
    "evaluate_rollback",
    "hold_for_global_stop",
    "complete_run",
}

_LOOP_STATES = {
    "runnable_waiting",
    "runnable_blocked",
    "paused",
    "manual_intervention_required",
    "replan_required",
    "rollback_pending",
    "rollback_completed_blocked",
    "delivery_in_progress",
    "terminal_success",
    "terminal_failure",
    "resumable_interrupted",
}

_LOOP_NEXT_SAFE_ACTIONS = {
    "continue_waiting",
    "pause",
    "require_manual_intervention",
    "require_replanning",
    "advance_evaluation_step",
    "execute_commit",
    "execute_push",
    "execute_pr_creation",
    "execute_merge",
    "execute_rollback",
    "stop_terminal_success",
    "stop_terminal_failure",
}

_POLICY_STATUSES = {
    "allowed",
    "blocked",
    "manual_only",
    "replan_required",
    "resume_eligible",
    "terminally_stopped",
}

_POLICY_BLOCKER_CLASSES = {
    "none",
    "authority_validation",
    "remote_github",
    "rollback_aftermath",
    "missing_or_ambiguous",
    "manual_gate",
    "replan_required",
    "terminal",
}

_POLICY_EXECUTION_INTENT_ACTIONS = {
    "proceed_to_commit",
    "proceed_to_pr",
    "proceed_to_merge",
    "proceed_to_rollback",
    "rollback_required",
}

_POLICY_NON_EXECUTION_ACTIONS = {
    "signal_recollect",
    "escalate_to_human",
    "roadmap_replan",
    "inspect",
    "pause",
}

_POLICY_LOOP_ACTION_TO_EXECUTION_ACTION = {
    "execute_commit": "proceed_to_commit",
    "execute_push": "proceed_to_pr",
    "execute_pr_creation": "proceed_to_pr",
    "execute_merge": "proceed_to_merge",
    "execute_rollback": "rollback_required",
}

_POLICY_DUPLICATE_PR_REASONS = {
    "existing_open_pr_detected",
    "blocked_existing_pr",
    "existing_pr_identity_ambiguous",
    "existing_pr_lookup_ambiguous",
}

_ORCHESTRATION_ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "planning_completed": ("units_generated", "failed_terminal"),
    "units_generated": ("execution_in_progress", "failed_terminal"),
    "execution_in_progress": ("checkpoint_evaluation_in_progress", "failed_terminal"),
    "checkpoint_evaluation_in_progress": (
        "run_ready_to_continue",
        "paused_for_manual_review",
        "rollback_evaluation_pending",
        "global_stop_pending",
        "failed_terminal",
    ),
    "run_ready_to_continue": ("checkpoint_evaluation_in_progress", "completed", "failed_terminal"),
    "paused_for_manual_review": (
        "checkpoint_evaluation_in_progress",
        "rollback_evaluation_pending",
        "global_stop_pending",
        "failed_terminal",
    ),
    "rollback_evaluation_pending": ("checkpoint_evaluation_in_progress", "failed_terminal"),
    "global_stop_pending": ("checkpoint_evaluation_in_progress", "failed_terminal"),
    "completed": (),
    "failed_terminal": (),
}

_COMMIT_EXECUTION_TYPE = "git_commit"
_COMMIT_EXECUTION_STATUSES = {"blocked", "succeeded", "failed"}
_PUSH_EXECUTION_TYPE = "git_push"
_PR_EXECUTION_TYPE = "github_pr_create"
_MERGE_EXECUTION_TYPE = "github_pr_merge"
_ROLLBACK_EXECUTION_TYPE = "rollback_execution"
_PUSH_EXECUTION_STATUSES = {"blocked", "succeeded", "failed"}
_PR_EXECUTION_STATUSES = {"blocked", "succeeded", "failed"}
_MERGE_EXECUTION_STATUSES = {"blocked", "succeeded", "failed"}
_ROLLBACK_EXECUTION_STATUSES = {"blocked", "succeeded", "failed"}
_ROLLBACK_MODES = {"local_commit_only", "pushed_or_pr_open", "merged", "unknown"}
_ROLLBACK_AFTERMATH_STATUSES = {
    "completed_safe",
    "completed_manual_followup_required",
    "blocked",
    "incomplete",
    "ambiguous",
    "validation_failed",
    "remote_followup_required",
}
_ROLLBACK_VALIDATION_STATUSES = {
    "satisfied",
    "failed",
    "unavailable",
    "ambiguous",
    "not_applicable",
}
_APPROVED_RESTART_EXECUTION_SCHEMA_VERSION = "v1"
_APPROVED_RESTART_EXECUTION_STATUSES = {"executed", "not_executed"}
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
_APPROVED_RESTART_ALLOWED_DECISIONS = {
    "allow_same_lane_retry",
    "allow_repair_retry",
    "allow_truth_gathering",
    "allow_replan_preparation",
    "allow_closure_followup",
}
_APPROVAL_SKIP_GATE_STATUSES = {
    "skip_allowed",
    "approval_required",
    "not_applicable",
    "insufficient_truth",
}
_APPROVAL_SKIP_GATE_DECISIONS = {
    "skip_and_continue_once",
    "require_human_approval",
    "not_applicable",
}
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
_APPROVAL_SKIP_DIRECTION_TO_POSTURE = {
    "same_lane_retry": {
        "response_command": "OK RETRY",
        "restart_decision": "allow_same_lane_retry",
    },
    "repair_retry": {
        "response_command": "OK RETRY",
        "restart_decision": "allow_repair_retry",
    },
    "truth_gathering": {
        "response_command": "OK TRUTH",
        "restart_decision": "allow_truth_gathering",
    },
    "replan_preparation": {
        "response_command": "OK REPLAN",
        "restart_decision": "allow_replan_preparation",
    },
    "closure_followup": {
        "response_command": "OK CLOSE",
        "restart_decision": "allow_closure_followup",
    },
}
_CONTINUATION_BUDGET_SCHEMA_VERSION = "v1"
_CONTINUATION_BUDGET_STATUSES = {"available", "exhausted", "insufficient_truth"}
_CONTINUATION_BUDGET_DECISIONS = {
    "allow_under_budget",
    "deny_budget_exhausted",
    "deny_insufficient_truth",
}
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
_CONTINUATION_BUDGET_RUN_LIMIT_DEFAULT = 2
_CONTINUATION_BUDGET_OBJECTIVE_LIMIT_DEFAULT = 2
_CONTINUATION_BUDGET_LANE_LIMIT_DEFAULT = 2
_CONTINUATION_BUDGET_BRANCH_TYPES = {"retry", "replan", "truth_gather"}
_CONTINUATION_BUDGET_BRANCH_STATUSES = {"available", "exhausted", "not_applicable"}
_CONTINUATION_BUDGET_BRANCH_DECISIONS = {
    "allow_under_branch_ceiling",
    "deny_branch_ceiling_exhausted",
    "not_applicable",
}
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
_CONTINUATION_BUDGET_BRANCH_LIMIT_DEFAULTS = {
    "retry": 2,
    "replan": 2,
    "truth_gather": 2,
}
_CONTINUATION_REPAIR_PLAYBOOK_STATUSES = {
    "selected",
    "not_selected",
    "insufficient_truth",
}
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
_CONTINUATION_NEXT_STEP_SELECTION_STATUSES = {
    "selected",
    "not_selected",
    "insufficient_truth",
}
_CONTINUATION_NEXT_STEP_TARGETS = {
    "retry",
    "replan",
    "truth_gather",
    "supported_repair",
    "none",
}
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
_CONTINUATION_REPAIR_PLAYBOOKS = {
    "objective_gap": {
        "repair_plan_class": "replan_plan",
        "repair_plan_candidate_action": "request_replan",
    },
    "completion_gap": {
        "repair_plan_class": "closure_followup_plan",
        "repair_plan_candidate_action": "request_closure_followup",
    },
    "approval_blocker": {
        "repair_plan_class": "manual_review_plan",
        "repair_plan_candidate_action": "request_manual_review",
    },
    "reconcile_mismatch": {
        "repair_plan_class": "truth_gathering_plan",
        "repair_plan_candidate_action": "gather_missing_truth",
    },
    "execution_failure": {
        "repair_plan_class": "replan_plan",
        "repair_plan_candidate_action": "request_replan",
    },
    "execution_partial": {
        "repair_plan_class": "truth_gathering_plan",
        "repair_plan_candidate_action": "gather_missing_truth",
    },
    "verification_failure": {
        "repair_plan_class": "truth_gathering_plan",
        "repair_plan_candidate_action": "gather_missing_truth",
    },
    "retry_exhausted": {
        "repair_plan_class": "replan_plan",
        "repair_plan_candidate_action": "request_replan",
    },
    "same_failure_exhausted": {
        "repair_plan_class": "replan_plan",
        "repair_plan_candidate_action": "request_replan",
    },
    "no_progress": {
        "repair_plan_class": "manual_review_plan",
        "repair_plan_candidate_action": "request_manual_review",
    },
    "oscillation": {
        "repair_plan_class": "manual_review_plan",
        "repair_plan_candidate_action": "request_manual_review",
    },
    "lane_mismatch": {
        "repair_plan_class": "replan_plan",
        "repair_plan_candidate_action": "request_replan",
    },
    "closure_unresolved": {
        "repair_plan_class": "closure_followup_plan",
        "repair_plan_candidate_action": "request_closure_followup",
    },
    "terminal_non_success": {
        "repair_plan_class": "manual_review_plan",
        "repair_plan_candidate_action": "request_manual_review",
    },
}
_SUPPORTED_REPAIR_EXECUTION_STATUSES = {
    "not_selected",
    "not_executed_precheck_blocked",
    "not_executed_qualification_failed",
    "not_executed_launch_failed",
    "executed_verification_passed",
    "executed_verification_failed",
}
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
_FINAL_HUMAN_REVIEW_GATE_STATUSES = {"required", "not_required"}
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
_PROJECT_PLANNING_SUMMARY_STATUSES = {"available", "insufficient_truth"}
_PROJECT_PLANNING_SUMMARY_REASON_CODES = {
    "planning_summary_compiled",
    "planning_summary_insufficient_truth",
}
_PROJECT_PLANNING_SUMMARY_REASON_ORDER = (
    "planning_summary_insufficient_truth",
    "planning_summary_compiled",
)
_PROJECT_ROADMAP_STATUSES = {"available", "insufficient_truth"}
_PROJECT_ROADMAP_REASON_CODES = {
    "roadmap_compiled",
    "roadmap_insufficient_truth",
}
_PROJECT_ROADMAP_REASON_ORDER = (
    "roadmap_insufficient_truth",
    "roadmap_compiled",
)
_PROJECT_PR_SLICING_STATUSES = {"available", "insufficient_truth"}
_PROJECT_PR_SLICING_REASON_CODES = {
    "pr_slices_compiled",
    "pr_slices_insufficient_truth",
}
_PROJECT_PR_SLICING_REASON_ORDER = (
    "pr_slices_insufficient_truth",
    "pr_slices_compiled",
)
_PROJECT_PR_SIZE_DECISIONS = {"single_theme_single_pr", "not_available"}
_PROJECT_PR_PRIORITIZATION_MODES = {
    "blocked_last_narrow_first_prereq_first",
    "insufficient_truth",
}
_PROJECT_ROADMAP_SCOPE_CLASS_ORDER = {
    "runner_only": 0,
    "runner_and_tests": 1,
    "cross_surface": 2,
    "unknown": 3,
}
_PROJECT_ROADMAP_TOPIC_ORDER = (
    "continuation_budget",
    "branch_ceiling",
    "failure_bucket_gate",
    "next_step_selection",
    "supported_repair_posture",
    "human_review_gate",
)
_PROJECT_ROADMAP_ITEM_ORDER = {
    f"roadmap_{topic}": index
    for index, topic in enumerate(_PROJECT_ROADMAP_TOPIC_ORDER)
}
_PROJECT_ROADMAP_PREREQUISITES = {
    "roadmap_branch_ceiling": ("roadmap_continuation_budget",),
    "roadmap_failure_bucket_gate": ("roadmap_continuation_budget",),
    "roadmap_supported_repair_posture": ("roadmap_next_step_selection",),
    "roadmap_human_review_gate": ("roadmap_next_step_selection",),
}
_IMPLEMENTATION_PROMPT_STATUSES = {"available", "insufficient_truth"}
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
_PROJECT_PR_QUEUE_STATUSES = {"prepared", "blocked", "empty", "insufficient_truth"}
_PROJECT_PR_QUEUE_REASON_CODES = {
    "queue_item_prepared",
    "queue_item_blocked",
    "queue_empty",
    "queue_state_insufficient_truth",
    "prompt_unavailable_for_selected_slice",
}
_PROJECT_PR_QUEUE_REASON_ORDER = (
    "queue_state_insufficient_truth",
    "queue_empty",
    "prompt_unavailable_for_selected_slice",
    "queue_item_blocked",
    "queue_item_prepared",
)
_REVIEW_ASSIMILATION_STATUSES = {"assimilated", "no_action", "insufficient_truth"}
_REVIEW_ASSIMILATION_ACTIONS = {"accept", "retry", "replan", "split", "escalate", "none"}
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
_SELF_HEALING_STATUSES = {
    "executed",
    "selected",
    "blocked",
    "not_applicable",
    "insufficient_truth",
}
_SELF_HEALING_TRANSITION_TARGETS = {
    "retry",
    "replan",
    "truth_gather",
    "alternative_supported_repair",
    "none",
}
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
_SELF_HEALING_CHAIN_LIMIT_DEFAULT = 1
_LONG_RUNNING_STABILITY_STATUSES = {
    "monitoring",
    "paused",
    "resume_ready",
    "safe_stop",
    "escalated",
    "insufficient_truth",
}
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
_LONG_RUNNING_STALE_AFTER_SECONDS_DEFAULT = 900
_LONG_RUNNING_STUCK_CYCLE_THRESHOLD_DEFAULT = 2
_OBJECTIVE_COMPILER_STATUSES = {"available", "insufficient_truth"}
_OBJECTIVE_DONE_CRITERIA_STATUSES = {"met", "not_met", "insufficient_truth"}
_OBJECTIVE_STOP_CRITERIA_STATUSES = {"stop", "continue", "insufficient_truth"}
_OBJECTIVE_COMPLETION_POSTURES = {
    "objective_active",
    "objective_completed",
    "objective_blocked",
    "objective_insufficient_truth",
}
_OBJECTIVE_SCOPE_DRIFT_STATUSES = {"detected", "clear", "insufficient_truth"}
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
_PROJECT_AUTONOMY_BUDGET_STATUSES = {"available", "insufficient_truth"}
_PROJECT_PRIORITY_POSTURES = {
    "active",
    "lower_priority",
    "deferred",
    "completed",
    "insufficient_truth",
}
_PROJECT_BUDGET_POSTURES = {"available", "exhausted", "insufficient_truth"}
_PROJECT_PR_RETRY_BUDGET_POSTURES = {
    "available",
    "exhausted",
    "not_applicable",
    "insufficient_truth",
}
_PROJECT_HIGH_RISK_DEFER_POSTURES = {"defer", "clear", "insufficient_truth"}
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
_PROJECT_QUALITY_GATE_STATUSES = {"available", "insufficient_truth"}
_PROJECT_QUALITY_GATE_POSTURES = {
    "merge_ready",
    "review_ready",
    "retry_needed",
    "insufficient_truth",
}
_PROJECT_QUALITY_GATE_NAMES = {
    "unit",
    "targeted_regression",
    "lint",
    "typecheck",
}
_PROJECT_QUALITY_GATE_CHANGED_AREA_CLASSES = {
    "runner_and_tests",
    "runner_only",
    "unknown",
}
_PROJECT_QUALITY_GATE_RISK_LEVELS = {"high", "moderate", "low", "insufficient_truth"}
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
_PROJECT_MERGE_BRANCH_LIFECYCLE_STATUSES = {"available", "insufficient_truth"}
_PROJECT_MERGE_READY_POSTURES = {
    "merge_ready",
    "not_merge_ready",
    "insufficient_truth",
}
_PROJECT_BRANCH_CANDIDATE_POSTURES = {
    "candidate",
    "not_candidate",
    "insufficient_truth",
}
_PROJECT_LOCAL_MAIN_SYNC_POSTURES = {
    "sync_required",
    "sync_not_required",
    "insufficient_truth",
}
_PROJECT_MERGE_BRANCH_LIFECYCLE_REASON_CODES = {
    "merge_branch_lifecycle_compiled",
    "merge_branch_lifecycle_insufficient_truth",
    "merge_branch_posture_merge_ready",
    "merge_branch_posture_not_merge_ready",
    "merge_branch_posture_insufficient_truth",
    "merge_branch_cleanup_candidate_yes",
    "merge_branch_cleanup_candidate_no",
    "merge_branch_cleanup_candidate_insufficient_truth",
    "merge_branch_quarantine_candidate_yes",
    "merge_branch_quarantine_candidate_no",
    "merge_branch_quarantine_candidate_insufficient_truth",
    "merge_branch_local_main_sync_required",
    "merge_branch_local_main_sync_not_required",
    "merge_branch_local_main_sync_insufficient_truth",
}
_PROJECT_MERGE_BRANCH_LIFECYCLE_REASON_ORDER = (
    "merge_branch_lifecycle_insufficient_truth",
    "merge_branch_posture_insufficient_truth",
    "merge_branch_cleanup_candidate_insufficient_truth",
    "merge_branch_quarantine_candidate_insufficient_truth",
    "merge_branch_local_main_sync_insufficient_truth",
    "merge_branch_lifecycle_compiled",
    "merge_branch_posture_merge_ready",
    "merge_branch_posture_not_merge_ready",
    "merge_branch_cleanup_candidate_yes",
    "merge_branch_cleanup_candidate_no",
    "merge_branch_quarantine_candidate_yes",
    "merge_branch_quarantine_candidate_no",
    "merge_branch_local_main_sync_required",
    "merge_branch_local_main_sync_not_required",
)
_PROJECT_FAILURE_MEMORY_STATUSES = {"available", "insufficient_truth"}
_PROJECT_FAILURE_MEMORY_SUPPRESSION_POSTURES = {
    "none",
    "suppress_retry",
    "suppress_repair",
    "suppress_review_issue",
    "suppress_failure_bucket",
    "insufficient_truth",
}
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
_PROJECT_EXTERNAL_BOUNDARY_STATUSES = {"available", "insufficient_truth"}
_PROJECT_EXTERNAL_DEPENDENCY_POSTURES = {
    "dependency_available",
    "dependency_blocked",
    "manual_only",
    "insufficient_truth",
}
_PROJECT_EXTERNAL_BOUNDARY_POSTURES = {
    "clear",
    "blocked",
    "manual_only",
    "insufficient_truth",
}
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
_PROJECT_HUMAN_ESCALATION_STATUSES = {"available", "insufficient_truth"}
_PROJECT_HUMAN_ESCALATION_POSTURES = {
    "escalation_required",
    "not_required",
    "insufficient_truth",
}
_PROJECT_HUMAN_ESCALATION_RISK_POSTURES = {
    "elevated",
    "clear",
    "insufficient_truth",
}
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
_PROJECT_APPROVAL_NOTIFICATION_STATUSES = {"available", "insufficient_truth"}
_PROJECT_APPROVAL_NOTIFICATION_READY_POSTURES = {
    "ready",
    "not_ready",
    "not_required",
    "insufficient_truth",
}
_PROJECT_APPROVAL_REPLY_REQUIRED_POSTURES = {
    "reply_required",
    "reply_not_required",
    "insufficient_truth",
}
_PROJECT_APPROVAL_CHANNEL_POSTURES = {
    "email_send",
    "email_draft",
    "review_queue",
    "manual_only",
    "not_required",
    "insufficient_truth",
}
_PROJECT_APPROVAL_MOBILE_SUMMARY_POSTURES = {
    "available",
    "not_required",
    "insufficient_truth",
}
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
_PROJECT_MULTI_OBJECTIVE_STATUSES = {"available", "insufficient_truth"}
_PROJECT_ACTIVE_OBJECTIVE_SELECTION_POSTURES = {
    "selected",
    "deferred",
    "insufficient_truth",
}
_PROJECT_BLOCKED_OBJECTIVE_DEFERRAL_POSTURES = {
    "deferred",
    "not_deferred",
    "insufficient_truth",
}
_PROJECT_RESUMABLE_QUEUE_ORDERING_POSTURES = {
    "resume_selected_first",
    "resume_blocked",
    "resume_empty",
    "resume_completed_waiting",
    "deferred_non_runnable",
    "insufficient_truth",
}
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
_IMPLEMENTATION_PROMPT_PRESERVED_CONSTRAINTS_REFS = (
    "/home/rai/codex-local-runner/prompts/context/pr_history_index.md",
    "/home/rai/codex-local-runner/prompts/context/current_architecture_constraints.md",
    "/home/rai/codex-local-runner/prompts/base_contract_rules.md",
    "/home/rai/codex-local-runner/prompts/base_token_reduction_rules.md",
    "/home/rai/codex-local-runner/prompts/base_codex_execution_wrapper.md",
    "/home/rai/codex-local-runner/prompts/base_codex_return_format.md",
)
_IMPLEMENTATION_PROMPT_DEFAULT_PREFERRED_FILES = (
    "automation/orchestration/planned_execution_runner.py",
    "tests/test_planned_execution_runner.py",
)
_IMPLEMENTATION_PROMPT_DEFAULT_OUT_OF_SCOPE = (
    "queue execution",
    "codex invocation redesign",
    "roadmap generation redesign",
    "PR slicing redesign",
    "approval/restart/repair redesign",
    "new planner/controller framework",
    "broad autonomous execution changes",
)
_IMPLEMENTATION_PROMPT_IN_SCOPE_BY_THEME = {
    "continuation_budget": (
        "deterministic continuation-budget behavior for selected bounded slice",
        "compact runner and focused runner-test updates only",
    ),
    "branch_ceiling": (
        "deterministic branch-ceiling behavior for selected bounded slice",
        "compact runner and focused runner-test updates only",
    ),
    "failure_bucket_gate": (
        "deterministic failure-bucket gate behavior for selected bounded slice",
        "compact runner and focused runner-test updates only",
    ),
    "next_step_selection": (
        "deterministic next-step selection behavior for selected bounded slice",
        "compact runner and focused runner-test updates only",
    ),
    "supported_repair_posture": (
        "deterministic supported-repair posture behavior for selected bounded slice",
        "compact runner and focused runner-test updates only",
    ),
    "human_review_gate": (
        "deterministic final human-review gate behavior for selected bounded slice",
        "compact runner and focused runner-test updates only",
    ),
}
_SUPPORTED_REPAIR_EXECUTABLE_PLAYBOOK_CLASSES = {
    "replan_plan",
    "truth_gathering_plan",
    "closure_followup_plan",
}
_SUPPORTED_REPAIR_EXECUTABLE_CANDIDATE_ACTIONS = {
    "request_replan",
    "gather_missing_truth",
    "request_closure_followup",
}
_CONTINUATION_UNSAFE_FAILURE_BUCKETS = {
    "truth_missing",
    "truth_conflict",
    "authorization_denied",
    "bridge_blocked",
    "manual_only",
    "external_truth_pending",
}

_AUTHORITY_BLOCKER_REASONS = {
    "commit_automation_not_eligible",
    "commit_manual_intervention_required",
    "commit_readiness_not_ready",
    "commit_unresolved_blockers_present",
    "merge_automation_not_eligible",
    "merge_manual_intervention_required",
    "merge_readiness_not_ready",
    "merge_unresolved_blockers_present",
    "rollback_automation_not_eligible",
    "rollback_manual_intervention_required",
    "rollback_readiness_not_ready",
    "rollback_unresolved_blockers_present",
    "dry_run_mode",
}

_UNSAFE_REPO_BLOCKER_REASONS = {
    "changed_files_outside_strict_scope",
    "working_tree_contains_out_of_scope_changes",
    "working_tree_conflicts_present",
    "working_tree_not_clean",
    "repo_not_git_worktree",
    "git_status_failed",
    "git_add_failed",
    "git_commit_failed",
    "git_push_failed",
    "git_diff_cached_failed",
    "git_revert_failed",
}

_REMOTE_PR_AMBIGUITY_REASONS = {
    "open_pr_lookup_unavailable",
    "open_pr_lookup_api_failure",
    "open_pr_lookup_empty",
    "existing_pr_identity_ambiguous",
    "pr_number_missing_or_invalid",
}

_REMOTE_GITHUB_BLOCKER_REASONS = {
    "git_remote_missing",
    "configured_remote_missing",
    "upstream_tracking_unresolved",
    "upstream_ref_ambiguous",
    "upstream_remote_ambiguous",
    "remote_divergence_status_unavailable",
    "remote_branch_diverged",
    "remote_non_fast_forward_risk",
    "remote_branch_lookup_unavailable",
    "open_pr_lookup_unavailable",
    "open_pr_lookup_api_failure",
    "open_pr_lookup_not_found",
    "open_pr_lookup_auth_failure",
    "open_pr_lookup_unsupported_query",
    "existing_open_pr_detected",
    "existing_pr_identity_ambiguous",
    "existing_pr_lookup_ambiguous",
    "github_read_backend_unavailable",
    "github_write_backend_unavailable",
    "github_pr_status_summary_unavailable",
    "merge_pr_status_summary_unavailable",
    "merge_pr_not_open",
    "mergeability_unknown",
    "mergeability_not_ready",
    "required_checks_unsatisfied",
    "review_requirements_unsatisfied",
    "branch_protection_unsatisfied",
    "pr_number_missing_or_invalid",
}

_REMOTE_GITHUB_MISSING_OR_AMBIGUOUS_REASON_TOKENS = (
    "ambiguous",
    "unknown",
    "unavailable",
    "missing",
    "unresolved",
    "not_found",
    "api_failure",
    "auth_failure",
    "unsupported_query",
)
_ROLLBACK_AFTERMATH_MISSING_OR_AMBIGUOUS_REASON_TOKENS = (
    "unknown",
    "unavailable",
    "missing",
    "ambiguous",
    "unresolved",
    "incomplete",
    "not_found",
    "not_open",
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

# Source-of-truth ownership for bounded-loop artifacts:
# - bounded_step_contract.json: planning intent
# - pr_implementation_prompt_contract.json: prompt intent
# - result.json: execution outcome
# - unit_progression.json: per-unit lifecycle checkpoints
# - commit_decision.json / merge_decision.json / rollback_decision.json: lifecycle authorization recommendations
# - checkpoint_decision.json: stop/go checkpoint formalization for next-phase lifecycle decisions
# - push_execution.json / pr_execution.json / merge_execution.json: downstream delivery execution receipts
# - rollback_execution.json: bounded rollback execution receipt derived from rollback readiness + execution receipts
# - run_state.json: run-level lifecycle state summary
# - objective_contract.json: run-level intent and acceptance contract (objective truth owner)
# - completion_contract.json: run-level derived completion decision contract


def _iso_now(now: Callable[[], datetime]) -> str:
    return now().isoformat(timespec="seconds")


def _parse_iso_timestamp(value: str) -> datetime | None:
    text = _normalize_text(value, default="")
    if not text:
        return None
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _normalize_string_list(value: Any, *, sort_items: bool = False) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    if sort_items:
        return sorted(result)
    return result


def _as_optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text and text.lstrip("-").isdigit():
            return int(text)
    return None


def _as_non_negative_int(value: Any, *, default: int = 0) -> int:
    maybe = _as_optional_int(value)
    if maybe is None:
        return default
    return max(0, maybe)


def _merge_retry_context_inputs(
    *,
    persisted: Mapping[str, Any] | None,
    explicit: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    has_persisted = isinstance(persisted, Mapping)
    has_explicit = isinstance(explicit, Mapping)
    if not has_persisted and not has_explicit:
        return None
    merged: dict[str, Any] = {}
    if has_persisted:
        merged.update(dict(persisted or {}))
    if has_explicit:
        merged.update(dict(explicit or {}))
    return merged


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


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _read_json_object_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        return None
    return dict(payload)


def _unit_is_failure(*, execution_status: str, dry_run: bool) -> bool:
    if execution_status in {"failed", "timed_out"}:
        return True
    if execution_status in {"running", "not_started"}:
        return not dry_run
    return False


def _validate_pr_unit_order(units: list[dict[str, Any]], *, pr_plan: Mapping[str, Any]) -> None:
    planned_units = pr_plan.get("prs") if isinstance(pr_plan.get("prs"), list) else []

    planned_order: list[str] = []
    for pr in planned_units:
        if not isinstance(pr, Mapping):
            continue
        pr_id = _normalize_text(pr.get("pr_id"))
        if pr_id:
            planned_order.append(pr_id)

    compiled_order = [_normalize_text(unit.get("pr_id")) for unit in units if _normalize_text(unit.get("pr_id"))]

    if compiled_order != planned_order:
        raise ValueError("compiled prompt units are not aligned with pr_plan.prs ordering")

    seen: set[str] = set()
    for unit in units:
        pr_id = _normalize_text(unit.get("pr_id"))
        if not pr_id:
            raise ValueError("pr_unit.pr_id must be non-empty")
        if pr_id in seen:
            raise ValueError(f"duplicate pr_id in compiled units: {pr_id}")
        dependencies = _normalize_string_list(unit.get("depends_on"))
        for dependency in dependencies:
            if dependency not in seen:
                raise ValueError(
                    f"dependency order violation for {pr_id}: depends_on={dependency} not yet processed"
                )
        seen.add(pr_id)


def _normalize_contract_payload(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _extract_bounded_step_handoff(pr_id: str, contract: Mapping[str, Any]) -> dict[str, Any]:
    progression = (
        dict(contract.get("progression_metadata"))
        if isinstance(contract.get("progression_metadata"), Mapping)
        else {}
    )
    boundedness = (
        dict(contract.get("boundedness"))
        if isinstance(contract.get("boundedness"), Mapping)
        else {}
    )
    planned_step_id = _normalize_text(
        progression.get("planned_step_id") or contract.get("step_id"),
        default=pr_id,
    )
    tier_category = _normalize_text(
        progression.get("tier_category") or contract.get("tier_category"),
        default="",
    )
    strict_scope_files = _normalize_string_list(
        progression.get("strict_scope_files") or contract.get("scope_in"),
        sort_items=True,
    )
    forbidden_files = _normalize_string_list(
        progression.get("forbidden_files") or contract.get("scope_out"),
        sort_items=True,
    )
    depends_on = _normalize_string_list(
        progression.get("depends_on") or contract.get("depends_on"),
        sort_items=False,
    )
    validation_expectations = _normalize_string_list(
        contract.get("validation_expectations"),
        sort_items=False,
    )
    boundedness_status = _normalize_text(boundedness.get("status"), default="unknown")
    return {
        "schema_version": _normalize_text(contract.get("schema_version"), default=""),
        "planned_step_id": planned_step_id,
        "title": _normalize_text(contract.get("title"), default=""),
        "purpose": _normalize_text(contract.get("purpose"), default=""),
        "tier_category": tier_category,
        "depends_on": depends_on,
        "strict_scope_files": strict_scope_files,
        "forbidden_files": forbidden_files,
        "validation_expectations": validation_expectations,
        "boundedness_status": boundedness_status,
        "is_bounded": bool(boundedness.get("is_bounded", False)),
    }


def _extract_prompt_contract_handoff(pr_id: str, contract: Mapping[str, Any]) -> dict[str, Any]:
    progression = (
        dict(contract.get("progression_metadata"))
        if isinstance(contract.get("progression_metadata"), Mapping)
        else {}
    )
    task_scope = dict(contract.get("task_scope")) if isinstance(contract.get("task_scope"), Mapping) else {}
    source_step_id = _normalize_text(contract.get("source_step_id"), default=pr_id)
    strict_scope_files = _normalize_string_list(
        progression.get("strict_scope_files") or task_scope.get("scope_in"),
        sort_items=True,
    )
    forbidden_files = _normalize_string_list(
        progression.get("forbidden_files") or task_scope.get("scope_out"),
        sort_items=True,
    )
    depends_on = _normalize_string_list(
        progression.get("depends_on") or task_scope.get("depends_on"),
        sort_items=False,
    )
    tier_category = _normalize_text(
        progression.get("tier_category") or task_scope.get("tier_category"),
        default="",
    )
    required_tests = _normalize_string_list(contract.get("required_tests"), sort_items=False)
    return {
        "schema_version": _normalize_text(contract.get("schema_version"), default=""),
        "source_step_id": source_step_id,
        "source_plan_id": _normalize_text(contract.get("source_plan_id"), default=""),
        "tier_category": tier_category,
        "depends_on": depends_on,
        "strict_scope_files": strict_scope_files,
        "forbidden_files": forbidden_files,
        "required_tests": required_tests,
        "requires_explicit_validation": bool(progression.get("requires_explicit_validation", False)),
        "scope_drift_detection_ready": bool(progression.get("scope_drift_detection_ready", False)),
        "category_mismatch_detection_ready": bool(progression.get("category_mismatch_detection_ready", False)),
    }


def _build_unit_contract_handoff(
    *,
    pr_id: str,
    bounded_step_contract: Mapping[str, Any],
    prompt_contract: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "bounded_step": _extract_bounded_step_handoff(pr_id, bounded_step_contract),
        "pr_implementation_prompt": _extract_prompt_contract_handoff(pr_id, prompt_contract),
    }


def _new_unit_progression_payload(
    *,
    pr_id: str,
    now: Callable[[], datetime],
    contract_handoff: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": _UNIT_PROGRESSION_SCHEMA_VERSION,
        "pr_id": pr_id,
        "current_state": _UNIT_STATE_PLANNED,
        "checkpoints": [
            {
                "state": _UNIT_STATE_PLANNED,
                "at": _iso_now(now),
                "reason": "unit_registered_from_compiled_plan",
            }
        ],
        "contract_handoff": dict(contract_handoff),
    }


def _append_progression_checkpoint(
    payload: dict[str, Any],
    *,
    state: str,
    now: Callable[[], datetime],
    reason: str,
    metadata: Mapping[str, Any] | None = None,
    update_current_state: bool = True,
) -> None:
    checkpoints = payload.get("checkpoints")
    if not isinstance(checkpoints, list):
        checkpoints = []
        payload["checkpoints"] = checkpoints
    entry: dict[str, Any] = {
        "state": state,
        "at": _iso_now(now),
        "reason": reason,
    }
    if isinstance(metadata, Mapping) and metadata:
        entry["metadata"] = dict(metadata)
    checkpoints.append(entry)
    if update_current_state:
        payload["current_state"] = state


def _resolve_review_terminal_state(decision_payload: Mapping[str, Any]) -> str:
    next_action = _normalize_text(decision_payload.get("next_action"), default="")
    result_acceptance = _normalize_text(decision_payload.get("result_acceptance"), default="")
    if next_action in {"escalate_to_human", "rollback_required"}:
        return _UNIT_STATE_ESCALATED
    if result_acceptance == "accept_current_result" and next_action in {"proceed_to_pr", "proceed_to_merge"}:
        return _UNIT_STATE_ADVANCED
    return _UNIT_STATE_REVIEWED


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


def _build_lifecycle_signals(
    *,
    pr_id: str,
    bounded_step_contract: Mapping[str, Any],
    prompt_contract: Mapping[str, Any],
    strict_scope_files: list[str],
    normalized_result: Mapping[str, Any],
) -> dict[str, bool]:
    execution = (
        dict(normalized_result.get("execution"))
        if isinstance(normalized_result.get("execution"), Mapping)
        else {}
    )
    verify = dict(execution.get("verify")) if isinstance(execution.get("verify"), Mapping) else {}
    execution_status = _normalize_text(execution.get("status"), default="")
    verify_status = _normalize_text(verify.get("status"), default="")
    changed_files = _normalize_string_list(normalized_result.get("changed_files"), sort_items=True)
    contract_missing = not bool(bounded_step_contract) or not bool(prompt_contract)
    return {
        "execution_succeeded": execution_status == "completed" and verify_status == "passed",
        "execution_failed": execution_status in {"failed", "timed_out"},
        "validation_failed": verify_status == "failed",
        "scope_violation_detected": _is_scope_violation_detected(
            strict_scope_files=strict_scope_files,
            changed_files=changed_files,
        ),
        "contract_missing": contract_missing,
        "contract_identity_conflict": (
            False
            if contract_missing
            else _has_contract_identity_conflict(
                pr_id=pr_id,
                bounded_step_contract=bounded_step_contract,
                prompt_contract=prompt_contract,
            )
        ),
        "unbounded_contract": False if contract_missing else _is_unbounded_contract(bounded_step_contract),
        "missing_progression_metadata": (
            True
            if contract_missing
            else _has_missing_progression_metadata(
                bounded_step_contract=bounded_step_contract,
                prompt_contract=prompt_contract,
            )
        ),
        "review_passed": False,
        "review_failed": False,
        "manual_review_required": False,
        "commit_allowed": False,
        "merge_allowed": False,
        "rollback_required": False,
        "global_stop_required": False,
        "unit_blocked": False,
        "run_paused": False,
        "run_failed_terminal": False,
    }


def _serialize_required_signals(signal_names: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in signal_names:
        text = _normalize_text(item, default="")
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _classify_authority_validation_blockers(blocking_reasons: list[str]) -> tuple[list[str], list[str]]:
    authority_blockers: list[str] = []
    validation_blockers: list[str] = []
    for reason in _serialize_required_signals(blocking_reasons):
        if (
            reason in _AUTHORITY_BLOCKER_REASONS
            or reason.startswith("run_")
            or reason.endswith("_manual_intervention_required")
            or reason.endswith("_backend_unavailable")
            or reason.endswith("_capability_missing")
            or reason.endswith("_automation_not_eligible")
            or reason.endswith("_readiness_not_ready")
            or reason.endswith("_unresolved_blockers_present")
        ):
            authority_blockers.append(reason)
        else:
            validation_blockers.append(reason)
    return authority_blockers, validation_blockers


def _is_remote_github_blocker_reason(reason: str) -> bool:
    if reason in _REMOTE_GITHUB_BLOCKER_REASONS:
        return True
    if reason.startswith("open_pr_lookup_"):
        return True
    if reason.startswith("merge_pr_status_summary_"):
        return True
    return any(
        token in reason
        for token in (
            "github_",
            "remote_",
            "upstream_",
            "mergeability_",
            "required_checks",
            "review_requirements",
            "branch_protection",
            "existing_pr",
            "pr_number_missing",
        )
    )


def _is_remote_github_missing_or_ambiguous_reason(reason: str) -> bool:
    if reason.startswith("open_pr_lookup_") and reason != "open_pr_lookup_success":
        return True
    if reason.startswith("merge_pr_status_summary_") and reason != "merge_pr_status_summary_success":
        return True
    return any(token in reason for token in _REMOTE_GITHUB_MISSING_OR_AMBIGUOUS_REASON_TOKENS)


def _build_remote_delivery_surface(
    *,
    execution_type: str,
    status: str,
    blocking_reasons: list[str],
    command_summary: Mapping[str, Any],
    existing_payload: Mapping[str, Any],
) -> dict[str, Any]:
    normalized_execution_type = _normalize_text(execution_type, default="")
    normalized_status = _normalize_text(status, default="")
    normalized_blockers = _serialize_required_signals(blocking_reasons)
    remote_github_blocked_reasons = _serialize_required_signals(
        [reason for reason in normalized_blockers if _is_remote_github_blocker_reason(reason)]
    )
    remote_github_blocked = normalized_status == "blocked" and bool(remote_github_blocked_reasons)
    remote_github_missing_or_ambiguous = any(
        _is_remote_github_missing_or_ambiguous_reason(reason)
        for reason in remote_github_blocked_reasons
    )
    remote_github_status = (
        "blocked"
        if remote_github_blocked
        else "allowed"
        if normalized_status in {"succeeded", "failed"}
        else "unknown"
    )

    surface: dict[str, Any] = {
        "remote_github_status": remote_github_status,
        "remote_github_blocked": remote_github_blocked,
        "remote_github_blocked_reason": (
            remote_github_blocked_reasons[0] if remote_github_blocked_reasons else ""
        ),
        "remote_github_blocked_reasons": remote_github_blocked_reasons,
        "remote_github_missing_or_ambiguous": remote_github_missing_or_ambiguous,
    }

    if normalized_execution_type == _PUSH_EXECUTION_TYPE:
        remote_state_status = (
            "ready"
            if normalized_status == "succeeded"
            else "blocked"
            if remote_github_blocked
            else "unknown"
        )
        if "remote_non_fast_forward_risk" in remote_github_blocked_reasons:
            remote_state_status = "non_fast_forward_risk"
        elif "remote_branch_diverged" in remote_github_blocked_reasons:
            remote_state_status = "diverged"
        elif remote_github_missing_or_ambiguous:
            remote_state_status = "ambiguous"

        upstream_tracking_status = _normalize_text(
            existing_payload.get("upstream_tracking_status"),
            default="",
        )
        if not upstream_tracking_status:
            if "upstream_tracking_unresolved" in remote_github_blocked_reasons:
                upstream_tracking_status = "unresolved"
            elif "upstream_ref_ambiguous" in remote_github_blocked_reasons:
                upstream_tracking_status = "ambiguous"
            elif any(
                reason in remote_github_blocked_reasons
                for reason in {"remote_non_fast_forward_risk", "remote_branch_diverged"}
            ):
                upstream_tracking_status = "tracked"
            elif normalized_status in {"succeeded", "failed"}:
                upstream_tracking_status = "tracked"
            else:
                upstream_tracking_status = "unknown"

        remote_divergence_status = _normalize_text(
            existing_payload.get("remote_divergence_status"),
            default="",
        )
        if not remote_divergence_status:
            if "remote_non_fast_forward_risk" in remote_github_blocked_reasons:
                remote_divergence_status = "non_fast_forward_risk"
            elif "remote_branch_diverged" in remote_github_blocked_reasons:
                remote_divergence_status = "diverged"
            elif normalized_status in {"succeeded", "failed"}:
                remote_divergence_status = "none"
            else:
                remote_divergence_status = "unknown"

        surface.update(
            {
                "remote_state_status": remote_state_status,
                "remote_state_blocked": remote_github_blocked,
                "remote_state_blocked_reason": (
                    remote_github_blocked_reasons[0] if remote_github_blocked_reasons else ""
                ),
                "remote_state_missing_or_ambiguous": remote_github_missing_or_ambiguous,
                "upstream_tracking_status": upstream_tracking_status,
                "remote_divergence_status": remote_divergence_status,
                "remote_branch_status": (
                    "known"
                    if _normalize_text(existing_payload.get("head_branch"), default="")
                    else "unknown"
                ),
                "github_state_status": "not_applicable",
                "github_state_unavailable": False,
            }
        )
        return surface

    if normalized_execution_type == _PR_EXECUTION_TYPE:
        existing_pr_status = _normalize_text(existing_payload.get("existing_pr_status"), default="")
        if not existing_pr_status:
            if "existing_open_pr_detected" in remote_github_blocked_reasons:
                existing_pr_status = "existing_open"
            elif "existing_pr_identity_ambiguous" in remote_github_blocked_reasons or (
                "existing_pr_lookup_ambiguous" in remote_github_blocked_reasons
            ):
                existing_pr_status = "ambiguous"
            elif normalized_status == "succeeded":
                existing_pr_status = "none"
            else:
                existing_pr_status = "unknown"

        pr_creation_state_status = _normalize_text(
            existing_payload.get("pr_creation_state_status"),
            default="",
        )
        if not pr_creation_state_status:
            if normalized_status == "succeeded":
                pr_creation_state_status = "created"
            elif existing_pr_status == "existing_open":
                pr_creation_state_status = "blocked_existing_pr"
            elif remote_github_missing_or_ambiguous:
                pr_creation_state_status = "blocked_remote_ambiguous"
            elif remote_github_blocked:
                pr_creation_state_status = "blocked_remote"
            elif normalized_status == "failed":
                pr_creation_state_status = "failed"
            else:
                pr_creation_state_status = "unknown"

        lookup_status = _normalize_text(command_summary.get("open_pr_lookup_status"), default="")
        github_state_status = (
            lookup_status
            or _normalize_text(existing_payload.get("github_state_status"), default="")
            or "unknown"
        )
        github_state_unavailable = github_state_status in {
            "unavailable",
            "api_failure",
            "auth_failure",
            "not_found",
            "unsupported_query",
        }

        surface.update(
            {
                "existing_pr_status": existing_pr_status,
                "pr_creation_state_status": pr_creation_state_status,
                "pr_duplication_risk": (
                    "detected" if existing_pr_status == "existing_open" else "none" if normalized_status == "succeeded" else "unknown"
                ),
                "remote_state_status": "blocked" if remote_github_blocked else "ready" if normalized_status == "succeeded" else "unknown",
                "remote_state_blocked": remote_github_blocked,
                "remote_state_blocked_reason": (
                    remote_github_blocked_reasons[0] if remote_github_blocked_reasons else ""
                ),
                "remote_state_missing_or_ambiguous": remote_github_missing_or_ambiguous,
                "github_state_status": github_state_status,
                "github_state_unavailable": github_state_unavailable,
            }
        )
        return surface

    if normalized_execution_type == _MERGE_EXECUTION_TYPE:
        mergeability_status = _normalize_text(existing_payload.get("mergeability_status"), default="")
        if not mergeability_status:
            if "mergeability_unknown" in remote_github_blocked_reasons:
                mergeability_status = "unknown"
            elif "mergeability_not_ready" in remote_github_blocked_reasons:
                mergeability_status = "not_ready"
            elif normalized_status == "succeeded":
                mergeability_status = "clean"
            else:
                mergeability_status = "unknown"

        required_checks_status = _normalize_text(
            existing_payload.get("required_checks_status"),
            default="",
        )
        if not required_checks_status:
            if "required_checks_unsatisfied" in remote_github_blocked_reasons:
                required_checks_status = "unsatisfied"
            elif normalized_status == "succeeded":
                required_checks_status = "passing"
            else:
                required_checks_status = "unknown"

        review_state_status = _normalize_text(existing_payload.get("review_state_status"), default="")
        if not review_state_status:
            review_state_status = (
                "unsatisfied"
                if "review_requirements_unsatisfied" in remote_github_blocked_reasons
                else "unknown"
            )

        branch_protection_status = _normalize_text(
            existing_payload.get("branch_protection_status"),
            default="",
        )
        if not branch_protection_status:
            branch_protection_status = (
                "unsatisfied"
                if "branch_protection_unsatisfied" in remote_github_blocked_reasons
                else "unknown"
            )

        merge_requirements_status = _normalize_text(
            existing_payload.get("merge_requirements_status"),
            default="",
        )
        if not merge_requirements_status:
            if any(
                reason in remote_github_blocked_reasons
                for reason in {
                    "required_checks_unsatisfied",
                    "review_requirements_unsatisfied",
                    "branch_protection_unsatisfied",
                }
            ):
                merge_requirements_status = "unsatisfied"
            elif normalized_status == "succeeded":
                merge_requirements_status = "satisfied"
            else:
                merge_requirements_status = "unknown"

        status_summary_status = _normalize_text(
            command_summary.get("pr_status_summary_status"),
            default="",
        )
        github_state_status = (
            status_summary_status
            or _normalize_text(command_summary.get("merge_status"), default="")
            or _normalize_text(existing_payload.get("github_state_status"), default="")
            or "unknown"
        )
        github_state_unavailable = status_summary_status in {
            "unavailable",
            "api_failure",
            "auth_failure",
            "not_found",
            "unsupported_query",
            "empty",
        }

        surface.update(
            {
                "mergeability_status": mergeability_status,
                "merge_requirements_status": merge_requirements_status,
                "required_checks_status": required_checks_status,
                "review_state_status": review_state_status,
                "branch_protection_status": branch_protection_status,
                "remote_state_status": "blocked" if remote_github_blocked else "ready" if normalized_status == "succeeded" else "unknown",
                "remote_state_blocked": remote_github_blocked,
                "remote_state_blocked_reason": (
                    remote_github_blocked_reasons[0] if remote_github_blocked_reasons else ""
                ),
                "remote_state_missing_or_ambiguous": remote_github_missing_or_ambiguous,
                "github_state_status": github_state_status,
                "github_state_unavailable": github_state_unavailable,
            }
        )
        return surface

    return surface


def _is_missing_required_ref_reason(reason: str) -> bool:
    if any(hint in reason for hint in _MISSING_REQUIRED_REF_HINTS):
        return any(token in reason for token in _MISSING_REQUIRED_REF_TOKENS)
    return False


def _build_execution_gate_surface(
    *,
    status: str,
    blocking_reasons: list[str],
    attempted: bool,
    manual_intervention_required: bool,
) -> dict[str, Any]:
    normalized_status = _normalize_text(status, default="")
    normalized_blockers = _serialize_required_signals(blocking_reasons)
    authority_blockers: list[str] = []
    validation_blockers: list[str] = []
    missing_prerequisites: list[str] = []
    missing_required_refs: list[str] = []
    unsafe_repo_state: list[str] = []
    remote_pr_ambiguity: list[str] = []
    remote_github_blocked_reasons: list[str] = []
    remote_github_missing_or_ambiguous = False
    unknown_blocked = normalized_status == "blocked" and not normalized_blockers

    if normalized_status == "blocked":
        remote_github_blocked_reasons = _serialize_required_signals(
            [reason for reason in normalized_blockers if _is_remote_github_blocker_reason(reason)]
        )
        remote_github_missing_or_ambiguous = any(
            _is_remote_github_missing_or_ambiguous_reason(reason)
            for reason in remote_github_blocked_reasons
        )
        non_remote_blockers = [
            reason for reason in normalized_blockers if reason not in set(remote_github_blocked_reasons)
        ]
        authority_blockers, validation_blockers = _classify_authority_validation_blockers(non_remote_blockers)
        missing_prerequisites = _serialize_required_signals(
            [
                reason
                for reason in normalized_blockers
                if any(token in reason for token in ("prerequisite", "not_succeeded", "not_ready", "unsatisfied"))
            ]
        )
        missing_required_refs = _serialize_required_signals(
            [reason for reason in normalized_blockers if _is_missing_required_ref_reason(reason)]
        )
        unsafe_repo_state = _serialize_required_signals(
            [reason for reason in normalized_blockers if reason in _UNSAFE_REPO_BLOCKER_REASONS]
        )
        remote_pr_ambiguity = _serialize_required_signals(
            [
                reason
                for reason in normalized_blockers
                if reason in _REMOTE_PR_AMBIGUITY_REASONS
                or "ambiguous" in reason
                or reason.startswith("open_pr_lookup_")
            ]
        )
        authority_status = "unknown" if unknown_blocked else ("blocked" if authority_blockers else "allowed")
        validation_status = "unknown" if unknown_blocked else ("blocked" if validation_blockers else "passed")
        execution_allowed = False
        if unknown_blocked:
            execution_gate_status = "unknown"
        elif authority_blockers and validation_blockers:
            execution_gate_status = "blocked_authority_and_validation"
        elif authority_blockers:
            execution_gate_status = "blocked_authority"
        elif validation_blockers:
            execution_gate_status = "blocked_validation"
        elif remote_github_blocked_reasons:
            execution_gate_status = "blocked_remote_github"
        else:
            execution_gate_status = "blocked_validation"
    elif normalized_status in {"succeeded", "failed"} and attempted:
        authority_status = "allowed"
        validation_status = "passed"
        execution_allowed = True
        execution_gate_status = "allowed"
    else:
        authority_status = "unknown"
        validation_status = "unknown"
        execution_allowed = False
        execution_gate_status = "unknown"

    manual_approval_required = bool(manual_intervention_required) or normalized_status == "blocked"

    return {
        "execution_allowed": execution_allowed,
        "execution_authority_status": authority_status,
        "validation_status": validation_status,
        "execution_gate_status": execution_gate_status,
        "authority_blocked_reasons": authority_blockers,
        "validation_blocked_reasons": validation_blockers,
        "authority_blocked_reason": authority_blockers[0] if authority_blockers else "",
        "validation_blocked_reason": validation_blockers[0] if validation_blockers else "",
        "missing_prerequisites": missing_prerequisites,
        "missing_required_refs": missing_required_refs,
        "unsafe_repo_state": unsafe_repo_state,
        "remote_pr_ambiguity": remote_pr_ambiguity,
        "remote_github_status": (
            "blocked"
            if normalized_status == "blocked" and bool(remote_github_blocked_reasons)
            else "allowed"
            if normalized_status in {"succeeded", "failed"} and attempted
            else "unknown"
        ),
        "remote_github_blocked": normalized_status == "blocked" and bool(remote_github_blocked_reasons),
        "remote_github_blocked_reason": (
            remote_github_blocked_reasons[0] if remote_github_blocked_reasons else ""
        ),
        "remote_github_blocked_reasons": remote_github_blocked_reasons,
        "remote_github_missing_or_ambiguous": remote_github_missing_or_ambiguous,
        "manual_approval_required": manual_approval_required,
    }


def _with_execution_gate_surface(payload: Mapping[str, Any]) -> dict[str, Any]:
    mutable = dict(payload)
    blockers = _normalize_string_list(mutable.get("blocking_reasons"), sort_items=False)
    mutable["blocking_reasons"] = _serialize_required_signals(blockers)
    mutable.update(
        _build_execution_gate_surface(
            status=_normalize_text(mutable.get("status"), default=""),
            blocking_reasons=blockers,
            attempted=bool(mutable.get("attempted", False)),
            manual_intervention_required=bool(mutable.get("manual_intervention_required", False)),
        )
    )
    mutable.update(
        _build_remote_delivery_surface(
            execution_type=_normalize_text(mutable.get("execution_type"), default=""),
            status=_normalize_text(mutable.get("status"), default=""),
            blocking_reasons=_normalize_string_list(mutable.get("blocking_reasons"), sort_items=False),
            command_summary=dict(mutable.get("command_summary")) if isinstance(mutable.get("command_summary"), Mapping) else {},
            existing_payload=mutable,
        )
    )
    return mutable


def _resolve_readiness_action(
    *,
    decision_kind: str,
    readiness_status: str,
    unresolved_blockers: list[str],
) -> str:
    if readiness_status == "ready":
        if decision_kind == "commit":
            return "prepare_commit"
        if decision_kind == "merge":
            return "prepare_merge"
        return "prepare_rollback_evaluation"
    if readiness_status == "manual_required":
        return "await_manual_review"
    if readiness_status in {"blocked", "awaiting_prerequisites"}:
        return "resolve_blockers"
    if readiness_status == "not_ready":
        return "hold"
    if unresolved_blockers:
        return "resolve_blockers"
    return "hold"


def _resolve_readiness_overlay(
    *,
    decision_kind: str,
    decision_payload: Mapping[str, Any],
    signals: Mapping[str, bool],
    run_state_payload: Mapping[str, Any] | None,
    commit_readiness_status: str | None = None,
) -> dict[str, Any]:
    decision = _normalize_text(decision_payload.get("decision"), default="unknown")
    blocking_reasons = _normalize_string_list(decision_payload.get("blocking_reasons"), sort_items=False)
    unresolved_blockers = list(blocking_reasons)

    run_manual_required = bool(run_state_payload.get("manual_intervention_required", False)) if isinstance(run_state_payload, Mapping) else False
    run_global_stop = (
        bool(run_state_payload.get("global_stop_recommended", False)) or bool(run_state_payload.get("global_stop", False))
    ) if isinstance(run_state_payload, Mapping) else False
    run_paused = bool(run_state_payload.get("run_paused", False)) if isinstance(run_state_payload, Mapping) else False
    run_rollback_pending = bool(run_state_payload.get("rollback_evaluation_pending", False)) if isinstance(run_state_payload, Mapping) else False

    if decision_kind in {"commit", "merge"}:
        if run_manual_required:
            unresolved_blockers.append("run_manual_intervention_required")
        if run_global_stop:
            unresolved_blockers.append("run_global_stop_recommended")
        if run_rollback_pending:
            unresolved_blockers.append("run_rollback_evaluation_pending")
        if run_paused:
            unresolved_blockers.append("run_paused")

    manual_intervention_required = bool(signals.get("manual_review_required", False)) or run_manual_required
    prerequisites_satisfied = False
    readiness_status = "awaiting_prerequisites"

    if decision_kind == "commit":
        prerequisites_satisfied = bool(signals.get("review_passed", False)) and bool(
            signals.get("execution_succeeded", False)
        )
        if decision == "manual_required" or run_manual_required:
            readiness_status = "manual_required"
            manual_intervention_required = True
        elif decision == "allowed" and prerequisites_satisfied and not unresolved_blockers:
            readiness_status = "ready"
        elif decision == "blocked":
            readiness_status = "blocked"
        elif decision == "unknown":
            readiness_status = "awaiting_prerequisites"
        else:
            readiness_status = "not_ready"
    elif decision_kind == "merge":
        commit_ready = _normalize_text(commit_readiness_status, default="") == "ready"
        if not commit_ready:
            unresolved_blockers.append("commit_readiness_not_ready")
        prerequisites_satisfied = (
            bool(signals.get("review_passed", False))
            and bool(signals.get("execution_succeeded", False))
            and commit_ready
        )
        if decision == "manual_required" or run_manual_required:
            readiness_status = "manual_required"
            manual_intervention_required = True
        elif decision == "allowed" and prerequisites_satisfied and not unresolved_blockers:
            readiness_status = "ready"
        elif decision == "blocked" and "merge_not_requested" in blocking_reasons:
            readiness_status = "awaiting_prerequisites"
        elif decision == "blocked":
            readiness_status = "blocked"
        elif decision == "unknown":
            readiness_status = "awaiting_prerequisites"
        else:
            readiness_status = "not_ready"
    else:
        rollback_required = decision == "required" or bool(signals.get("rollback_required", False))
        prerequisites_satisfied = rollback_required
        if decision == "manual_required":
            readiness_status = "manual_required"
            manual_intervention_required = True
        elif rollback_required and not run_global_stop and not run_manual_required:
            readiness_status = "ready"
        elif rollback_required and (run_global_stop or run_manual_required):
            readiness_status = "awaiting_prerequisites"
        elif decision == "blocked":
            readiness_status = "blocked"
        elif decision == "not_required":
            readiness_status = "not_ready"
        else:
            readiness_status = "awaiting_prerequisites"
        if rollback_required and run_manual_required:
            unresolved_blockers.append("run_manual_intervention_required")

    unresolved_blockers = _serialize_required_signals(unresolved_blockers)
    if readiness_status not in _READINESS_STATUSES:
        readiness_status = "awaiting_prerequisites"
    readiness_next_action = _resolve_readiness_action(
        decision_kind=decision_kind,
        readiness_status=readiness_status,
        unresolved_blockers=unresolved_blockers,
    )
    if readiness_next_action not in _READINESS_NEXT_ACTIONS:
        readiness_next_action = "hold"
    automation_eligible = (
        readiness_status == "ready"
        and not manual_intervention_required
        and not unresolved_blockers
        and prerequisites_satisfied
    )
    if automation_eligible and unresolved_blockers:
        automation_eligible = False

    return {
        "readiness_status": readiness_status,
        "readiness_next_action": readiness_next_action,
        "automation_eligible": automation_eligible,
        "manual_intervention_required": manual_intervention_required,
        "unresolved_blockers": unresolved_blockers,
        "prerequisites_satisfied": prerequisites_satisfied,
    }


def _with_readiness_overlay(
    *,
    decision_kind: str,
    decision_payload: Mapping[str, Any],
    signals: Mapping[str, bool],
    run_state_payload: Mapping[str, Any] | None,
    commit_readiness_status: str | None = None,
) -> dict[str, Any]:
    overlay = _resolve_readiness_overlay(
        decision_kind=decision_kind,
        decision_payload=decision_payload,
        signals=signals,
        run_state_payload=run_state_payload,
        commit_readiness_status=commit_readiness_status,
    )
    return {
        **dict(decision_payload),
        **overlay,
    }


def _build_run_readiness_summary(manifest_units: list[Mapping[str, Any]]) -> dict[str, Any]:
    def _bucket(kind: str) -> dict[str, int]:
        statuses = {"ready": 0, "not_ready": 0, "manual_required": 0, "blocked": 0, "awaiting_prerequisites": 0}
        for unit in manifest_units:
            decision_summary = dict(unit.get("decision_summary")) if isinstance(unit.get("decision_summary"), Mapping) else {}
            key = f"{kind}_readiness_status"
            status = _normalize_text(decision_summary.get(key), default="")
            if status in statuses:
                statuses[status] += 1
        return statuses

    return {
        "commit": _bucket("commit"),
        "merge": _bucket("merge"),
        "rollback": _bucket("rollback"),
    }


def _augment_run_state_with_readiness(
    *,
    run_state_payload: Mapping[str, Any],
    manifest_units: list[Mapping[str, Any]],
) -> dict[str, Any]:
    readiness_summary = _build_run_readiness_summary(manifest_units)
    readiness_blocked = any(
        _as_non_negative_int(bucket.get("blocked"), default=0) > 0
        for bucket in readiness_summary.values()
        if isinstance(bucket, Mapping)
    )
    readiness_manual_required = any(
        _as_non_negative_int(bucket.get("manual_required"), default=0) > 0
        for bucket in readiness_summary.values()
        if isinstance(bucket, Mapping)
    )
    readiness_awaiting_prerequisites = any(
        _as_non_negative_int(bucket.get("awaiting_prerequisites"), default=0) > 0
        for bucket in readiness_summary.values()
        if isinstance(bucket, Mapping)
    )
    return {
        **dict(run_state_payload),
        "readiness_summary": readiness_summary,
        "readiness_blocked": readiness_blocked,
        "readiness_manual_required": readiness_manual_required,
        "readiness_awaiting_prerequisites": readiness_awaiting_prerequisites,
    }


def _run_git(repo_path: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", repo_path, *args],
        text=True,
        capture_output=True,
    )


def _parse_git_status_path(line: str) -> str:
    if len(line) < 4:
        return ""
    raw_path = line[3:].strip()
    if not raw_path:
        return ""
    if " -> " in raw_path:
        _, rhs = raw_path.split(" -> ", 1)
        raw_path = rhs.strip()
    if raw_path.startswith('"') and raw_path.endswith('"') and len(raw_path) >= 2:
        raw_path = raw_path[1:-1]
    return raw_path


def _extract_commit_scope_from_contract(entry: Mapping[str, Any]) -> list[str]:
    bounded_contract_path_text = _normalize_text(entry.get("bounded_step_contract_path"), default="")
    if not bounded_contract_path_text:
        return []
    bounded_contract = _read_json_object_if_exists(Path(bounded_contract_path_text))
    if not isinstance(bounded_contract, Mapping):
        return []
    progression = (
        dict(bounded_contract.get("progression_metadata"))
        if isinstance(bounded_contract.get("progression_metadata"), Mapping)
        else {}
    )
    strict_scope_files = _normalize_string_list(
        progression.get("strict_scope_files") or bounded_contract.get("scope_in"),
        sort_items=True,
    )
    return strict_scope_files


def _extract_changed_files_from_result(entry: Mapping[str, Any]) -> list[str]:
    result_path_text = _normalize_text(entry.get("result_path"), default="")
    if not result_path_text:
        return []
    result_payload = _read_json_object_if_exists(Path(result_path_text))
    if not isinstance(result_payload, Mapping):
        return []
    return _normalize_string_list(result_payload.get("changed_files"), sort_items=True)


def _default_commit_execution_payload(
    *,
    unit_id: str,
    now: Callable[[], datetime],
) -> dict[str, Any]:
    return {
        "schema_version": _COMMIT_EXECUTION_SCHEMA_VERSION,
        "unit_id": unit_id,
        "execution_type": _COMMIT_EXECUTION_TYPE,
        "status": "blocked",
        "summary": "commit execution blocked",
        "started_at": "",
        "finished_at": _iso_now(now),
        "commit_sha": "",
        "command_summary": {},
        "failure_reason": "commit_execution_not_attempted",
        "manual_intervention_required": False,
        "blocking_reasons": [],
        "attempted": False,
        "execution_allowed": False,
        "execution_authority_status": "unknown",
        "validation_status": "unknown",
        "execution_gate_status": "unknown",
        "authority_blocked_reasons": [],
        "validation_blocked_reasons": [],
        "authority_blocked_reason": "",
        "validation_blocked_reason": "",
        "missing_prerequisites": [],
        "missing_required_refs": [],
        "unsafe_repo_state": [],
        "remote_pr_ambiguity": [],
        "remote_github_status": "unknown",
        "remote_github_blocked": False,
        "remote_github_blocked_reason": "",
        "remote_github_blocked_reasons": [],
        "remote_github_missing_or_ambiguous": False,
        "remote_state_status": "unknown",
        "remote_state_blocked": False,
        "remote_state_blocked_reason": "",
        "remote_state_missing_or_ambiguous": False,
        "upstream_tracking_status": "unknown",
        "remote_divergence_status": "unknown",
        "remote_branch_status": "unknown",
        "existing_pr_status": "unknown",
        "pr_creation_state_status": "unknown",
        "pr_duplication_risk": "unknown",
        "mergeability_status": "unknown",
        "merge_requirements_status": "unknown",
        "required_checks_status": "unknown",
        "review_state_status": "unknown",
        "branch_protection_status": "unknown",
        "github_state_status": "unknown",
        "github_state_unavailable": False,
        "manual_approval_required": False,
    }


def _build_commit_execution_blocked_payload(
    *,
    unit_id: str,
    now: Callable[[], datetime],
    summary: str,
    failure_reason: str,
    blocking_reasons: list[str],
    manual_intervention_required: bool = False,
    command_summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _default_commit_execution_payload(unit_id=unit_id, now=now)
    payload["summary"] = summary
    payload["failure_reason"] = failure_reason
    payload["blocking_reasons"] = _serialize_required_signals(list(blocking_reasons))
    payload["manual_intervention_required"] = manual_intervention_required
    payload["command_summary"] = dict(command_summary) if isinstance(command_summary, Mapping) else {}
    return _with_execution_gate_surface(payload)


def _evaluate_commit_execution_blockers(
    *,
    commit_decision: Mapping[str, Any],
    run_state_payload: Mapping[str, Any],
    changed_files: list[str],
    strict_scope_files: list[str],
    execution_repo_path: str,
    dry_run: bool,
) -> list[str]:
    blockers: list[str] = []

    readiness_status = _normalize_text(commit_decision.get("readiness_status"), default="")
    if readiness_status != "ready":
        blockers.append("commit_readiness_not_ready")
    if not bool(commit_decision.get("automation_eligible", False)):
        blockers.append("commit_automation_not_eligible")
    if bool(commit_decision.get("manual_intervention_required", False)):
        blockers.append("commit_manual_intervention_required")
    if _normalize_string_list(commit_decision.get("unresolved_blockers")):
        blockers.append("commit_unresolved_blockers_present")
    if not bool(commit_decision.get("prerequisites_satisfied", False)):
        blockers.append("commit_prerequisites_unsatisfied")

    if not bool(run_state_payload.get("continue_allowed", False)):
        blockers.append("run_continue_not_allowed")
    if bool(run_state_payload.get("run_paused", False)):
        blockers.append("run_paused")
    if bool(run_state_payload.get("manual_intervention_required", False)):
        blockers.append("run_manual_intervention_required")
    if bool(run_state_payload.get("global_stop_recommended", False)) or bool(run_state_payload.get("global_stop", False)):
        blockers.append("run_global_stop_recommended")
    if bool(run_state_payload.get("rollback_evaluation_pending", False)):
        blockers.append("run_rollback_evaluation_pending")

    if dry_run:
        blockers.append("dry_run_mode")
    if not execution_repo_path.strip():
        blockers.append("execution_repo_path_missing")
    if not changed_files:
        blockers.append("result_changed_files_missing")
    if not strict_scope_files:
        blockers.append("strict_scope_unavailable")
    elif changed_files:
        strict_scope = set(strict_scope_files)
        if any(path not in strict_scope for path in changed_files):
            blockers.append("changed_files_outside_strict_scope")

    return _serialize_required_signals(blockers)


def _execute_bounded_commit(
    *,
    unit_id: str,
    job_id: str,
    repo_path: str,
    changed_files: list[str],
    strict_scope_files: list[str],
    run_state_payload: Mapping[str, Any],
    commit_decision: Mapping[str, Any],
    dry_run: bool,
    now: Callable[[], datetime],
) -> dict[str, Any]:
    blockers = _evaluate_commit_execution_blockers(
        commit_decision=commit_decision,
        run_state_payload=run_state_payload,
        changed_files=changed_files,
        strict_scope_files=strict_scope_files,
        execution_repo_path=repo_path,
        dry_run=dry_run,
    )
    if blockers:
        return _build_commit_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            summary="commit execution blocked by readiness or run-level preconditions",
            failure_reason="commit_execution_blocked_by_preconditions",
            blocking_reasons=blockers,
        )

    repo_dir = Path(repo_path)
    if not repo_dir.exists() or not repo_dir.is_dir():
        return _build_commit_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            summary="commit execution blocked because execution repo path is invalid",
            failure_reason="execution_repo_not_directory",
            blocking_reasons=["execution_repo_not_directory"],
        )

    command_summary: dict[str, Any] = {}
    worktree_result = _run_git(repo_path, ["rev-parse", "--is-inside-work-tree"])
    command_summary["rev_parse_worktree_rc"] = worktree_result.returncode
    if worktree_result.returncode != 0:
        return _build_commit_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            summary="commit execution blocked because repo is not a git worktree",
            failure_reason="repo_not_git_worktree",
            blocking_reasons=["repo_not_git_worktree"],
            command_summary=command_summary,
        )

    status_result = _run_git(repo_path, ["status", "--porcelain"])
    command_summary["status_rc"] = status_result.returncode
    if status_result.returncode != 0:
        return _build_commit_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            summary="commit execution blocked because git status failed",
            failure_reason="git_status_failed",
            blocking_reasons=["git_status_failed"],
            manual_intervention_required=True,
            command_summary=command_summary,
        )

    status_lines = [line.rstrip("\n") for line in (status_result.stdout or "").splitlines() if line.strip()]
    command_summary["status_lines"] = len(status_lines)
    changed_files_set = set(changed_files)
    status_paths = [_parse_git_status_path(line) for line in status_lines]
    status_paths = [path for path in status_paths if path]
    if not status_paths:
        return _build_commit_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            summary="commit execution blocked because no repository changes were detected",
            failure_reason="no_repository_changes",
            blocking_reasons=["no_repository_changes"],
            command_summary=command_summary,
        )

    if any(path not in changed_files_set for path in status_paths):
        return _build_commit_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            summary="commit execution blocked because working tree contains out-of-scope changes",
            failure_reason="working_tree_contains_out_of_scope_changes",
            blocking_reasons=["working_tree_contains_out_of_scope_changes"],
            command_summary=command_summary,
        )

    if not any(path in changed_files_set for path in status_paths):
        return _build_commit_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            summary="commit execution blocked because expected changed files were not present in git status",
            failure_reason="expected_changed_files_not_present",
            blocking_reasons=["expected_changed_files_not_present"],
            command_summary=command_summary,
        )

    if any(line[:2].strip() == "U" or line[:2] in {"DD", "AU", "UD", "UA", "DU", "AA", "UU"} for line in status_lines):
        return _build_commit_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            summary="commit execution blocked because merge-conflict markers were detected in git status",
            failure_reason="working_tree_conflicts_present",
            blocking_reasons=["working_tree_conflicts_present"],
            manual_intervention_required=True,
            command_summary=command_summary,
        )

    started_at = _iso_now(now)
    add_result = _run_git(repo_path, ["add", "--", *sorted(changed_files_set)])
    command_summary["git_add_rc"] = add_result.returncode
    if add_result.returncode != 0:
        return {
            "schema_version": _COMMIT_EXECUTION_SCHEMA_VERSION,
            "unit_id": unit_id,
            "execution_type": _COMMIT_EXECUTION_TYPE,
            "status": "failed",
            "summary": "commit execution failed while staging files",
            "started_at": started_at,
            "finished_at": _iso_now(now),
            "commit_sha": "",
            "command_summary": command_summary,
            "failure_reason": "git_add_failed",
            "manual_intervention_required": True,
            "blocking_reasons": ["git_add_failed"],
            "attempted": True,
        }

    staged_diff = _run_git(repo_path, ["diff", "--cached", "--quiet"])
    command_summary["staged_diff_rc"] = staged_diff.returncode
    if staged_diff.returncode == 0:
        return _build_commit_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            summary="commit execution blocked because no staged changes were available for commit",
            failure_reason="no_staged_changes",
            blocking_reasons=["no_staged_changes"],
            command_summary=command_summary,
        )
    if staged_diff.returncode not in {0, 1}:
        return {
            "schema_version": _COMMIT_EXECUTION_SCHEMA_VERSION,
            "unit_id": unit_id,
            "execution_type": _COMMIT_EXECUTION_TYPE,
            "status": "failed",
            "summary": "commit execution failed while checking staged diff",
            "started_at": started_at,
            "finished_at": _iso_now(now),
            "commit_sha": "",
            "command_summary": command_summary,
            "failure_reason": "git_diff_cached_failed",
            "manual_intervention_required": True,
            "blocking_reasons": ["git_diff_cached_failed"],
            "attempted": True,
        }

    commit_message = f"[{job_id}:{unit_id}] bounded commit execution"
    command_summary["commit_message"] = commit_message
    commit_result = _run_git(
        repo_path,
        [
            "-c",
            "user.name=Codex Local Runner",
            "-c",
            "user.email=codex-local-runner@example.com",
            "commit",
            "-m",
            commit_message,
        ],
    )
    command_summary["git_commit_rc"] = commit_result.returncode
    if commit_result.returncode != 0:
        return {
            "schema_version": _COMMIT_EXECUTION_SCHEMA_VERSION,
            "unit_id": unit_id,
            "execution_type": _COMMIT_EXECUTION_TYPE,
            "status": "failed",
            "summary": "commit execution failed during git commit",
            "started_at": started_at,
            "finished_at": _iso_now(now),
            "commit_sha": "",
            "command_summary": command_summary,
            "failure_reason": "git_commit_failed",
            "manual_intervention_required": True,
            "blocking_reasons": ["git_commit_failed"],
            "attempted": True,
        }

    rev_parse_head = _run_git(repo_path, ["rev-parse", "HEAD"])
    command_summary["rev_parse_head_rc"] = rev_parse_head.returncode
    commit_sha = (rev_parse_head.stdout or "").strip() if rev_parse_head.returncode == 0 else ""
    if not commit_sha:
        return {
            "schema_version": _COMMIT_EXECUTION_SCHEMA_VERSION,
            "unit_id": unit_id,
            "execution_type": _COMMIT_EXECUTION_TYPE,
            "status": "failed",
            "summary": "commit execution failed to resolve HEAD after successful commit",
            "started_at": started_at,
            "finished_at": _iso_now(now),
            "commit_sha": "",
            "command_summary": command_summary,
            "failure_reason": "head_resolution_failed_after_commit",
            "manual_intervention_required": True,
            "blocking_reasons": ["head_resolution_failed_after_commit"],
            "attempted": True,
        }

    return {
        "schema_version": _COMMIT_EXECUTION_SCHEMA_VERSION,
        "unit_id": unit_id,
        "execution_type": _COMMIT_EXECUTION_TYPE,
        "status": "succeeded",
        "summary": "commit execution succeeded under bounded readiness and run-state conditions",
        "started_at": started_at,
        "finished_at": _iso_now(now),
        "commit_sha": commit_sha,
        "command_summary": command_summary,
        "failure_reason": "",
        "manual_intervention_required": False,
        "blocking_reasons": [],
        "attempted": True,
    }


def _augment_run_state_with_commit_execution(
    *,
    run_state_payload: Mapping[str, Any],
    manifest_units: list[Mapping[str, Any]],
) -> dict[str, Any]:
    statuses = {"succeeded": 0, "failed": 0, "blocked": 0}
    for unit in manifest_units:
        summary = dict(unit.get("commit_execution_summary")) if isinstance(unit.get("commit_execution_summary"), Mapping) else {}
        status = _normalize_text(summary.get("status"), default="")
        if status in statuses:
            statuses[status] += 1

    commit_execution_failed = statuses["failed"] > 0
    commit_execution_manual_intervention_required = commit_execution_failed or any(
        bool(dict(unit.get("commit_execution_summary")).get("manual_intervention_required", False))
        for unit in manifest_units
        if isinstance(unit.get("commit_execution_summary"), Mapping)
    )
    return {
        **dict(run_state_payload),
        "commit_execution_summary": statuses,
        "commit_execution_executed": statuses["succeeded"] > 0,
        "commit_execution_pending": statuses["blocked"] > 0,
        "commit_execution_failed": commit_execution_failed,
        "commit_execution_manual_intervention_required": commit_execution_manual_intervention_required,
    }


def _default_delivery_execution_payload(
    *,
    schema_version: str,
    execution_type: str,
    unit_id: str,
    now: Callable[[], datetime],
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "unit_id": unit_id,
        "execution_type": execution_type,
        "status": "blocked",
        "summary": f"{execution_type} blocked",
        "started_at": "",
        "finished_at": _iso_now(now),
        "branch_name": "",
        "remote_name": "",
        "base_branch": "",
        "head_branch": "",
        "pr_number": None,
        "pr_url": "",
        "merge_commit_sha": "",
        "command_summary": {},
        "failure_reason": f"{execution_type}_not_attempted",
        "manual_intervention_required": False,
        "blocking_reasons": [],
        "attempted": False,
        "execution_allowed": False,
        "execution_authority_status": "unknown",
        "validation_status": "unknown",
        "execution_gate_status": "unknown",
        "authority_blocked_reasons": [],
        "validation_blocked_reasons": [],
        "authority_blocked_reason": "",
        "validation_blocked_reason": "",
        "missing_prerequisites": [],
        "missing_required_refs": [],
        "unsafe_repo_state": [],
        "remote_pr_ambiguity": [],
        "manual_approval_required": False,
    }


def _build_delivery_execution_blocked_payload(
    *,
    schema_version: str,
    execution_type: str,
    unit_id: str,
    now: Callable[[], datetime],
    summary: str,
    failure_reason: str,
    blocking_reasons: list[str],
    manual_intervention_required: bool = False,
    command_summary: Mapping[str, Any] | None = None,
    branch_name: str = "",
    remote_name: str = "",
    base_branch: str = "",
    head_branch: str = "",
    pr_number: int | None = None,
    pr_url: str = "",
) -> dict[str, Any]:
    payload = _default_delivery_execution_payload(
        schema_version=schema_version,
        execution_type=execution_type,
        unit_id=unit_id,
        now=now,
    )
    payload["summary"] = summary
    payload["failure_reason"] = failure_reason
    payload["blocking_reasons"] = _serialize_required_signals(list(blocking_reasons))
    payload["manual_intervention_required"] = manual_intervention_required
    payload["command_summary"] = dict(command_summary) if isinstance(command_summary, Mapping) else {}
    payload["branch_name"] = _normalize_text(branch_name, default="")
    payload["remote_name"] = _normalize_text(remote_name, default="")
    payload["base_branch"] = _normalize_text(base_branch, default="")
    payload["head_branch"] = _normalize_text(head_branch, default="")
    payload["pr_number"] = _as_optional_int(pr_number)
    payload["pr_url"] = _normalize_text(pr_url, default="")
    return _with_execution_gate_surface(payload)


def _run_state_execution_blockers(run_state_payload: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not bool(run_state_payload.get("continue_allowed", False)):
        blockers.append("run_continue_not_allowed")
    if bool(run_state_payload.get("run_paused", False)):
        blockers.append("run_paused")
    if bool(run_state_payload.get("manual_intervention_required", False)):
        blockers.append("run_manual_intervention_required")
    if bool(run_state_payload.get("global_stop_recommended", False)) or bool(run_state_payload.get("global_stop", False)):
        blockers.append("run_global_stop_recommended")
    if bool(run_state_payload.get("rollback_evaluation_pending", False)):
        blockers.append("run_rollback_evaluation_pending")
    return _serialize_required_signals(blockers)


def _resolve_open_pr_lookup(
    *,
    read_backend: Any,
    repository: str,
    head_branch: str,
    base_branch: str,
) -> tuple[str, dict[str, Any]]:
    if read_backend is None:
        return "unavailable", {}
    finder = getattr(read_backend, "find_open_pr", None)
    if not callable(finder):
        return "unavailable", {}
    try:
        payload = finder(repository, head_branch=head_branch, base_branch=base_branch)
    except Exception:
        return "api_failure", {}
    if not isinstance(payload, Mapping):
        return "api_failure", {}
    status = _normalize_text(payload.get("status"), default="")
    if not status:
        return "api_failure", dict(payload)
    data = dict(payload.get("data")) if isinstance(payload.get("data"), Mapping) else {}
    return status, data


def _build_pr_title_and_body(
    *,
    job_id: str,
    unit_id: str,
    commit_sha: str,
) -> tuple[str, str]:
    title = f"[{job_id}:{unit_id}] bounded execution slice"
    body = (
        "Automated bounded PR creation from planned execution runner.\n"
        f"- job_id: {job_id}\n"
        f"- unit_id: {unit_id}\n"
        f"- commit_sha: {commit_sha or '(unknown)'}"
    )
    return title, body


def _resolve_current_branch(repo_path: str, *, command_summary: dict[str, Any]) -> str:
    branch_result = _run_git(repo_path, ["rev-parse", "--abbrev-ref", "HEAD"])
    command_summary["branch_rc"] = branch_result.returncode
    if branch_result.returncode != 0:
        return ""
    branch_name = _normalize_text(branch_result.stdout, default="")
    if branch_name == "HEAD":
        return ""
    return branch_name


def _resolve_git_remotes(repo_path: str, *, command_summary: dict[str, Any]) -> list[str]:
    remotes_result = _run_git(repo_path, ["remote"])
    command_summary["remote_list_rc"] = remotes_result.returncode
    if remotes_result.returncode != 0:
        return []
    remotes = _normalize_string_list((remotes_result.stdout or "").splitlines(), sort_items=False)
    return remotes


def _has_conflict_status_lines(status_lines: list[str]) -> bool:
    return any(
        line[:2].strip() == "U" or line[:2] in {"DD", "AU", "UD", "UA", "DU", "AA", "UU"}
        for line in status_lines
    )


def _execute_bounded_push(
    *,
    unit_id: str,
    repo_path: str,
    remote_name: str,
    configured_head_branch: str,
    base_branch: str,
    run_state_payload: Mapping[str, Any],
    commit_execution_payload: Mapping[str, Any],
    dry_run: bool,
    now: Callable[[], datetime],
) -> dict[str, Any]:
    command_summary: dict[str, Any] = {}
    branch_name = ""
    head_branch = _normalize_text(configured_head_branch, default="")
    blockers = _run_state_execution_blockers(run_state_payload)

    commit_status = _normalize_text(commit_execution_payload.get("status"), default="")
    commit_sha = _normalize_text(commit_execution_payload.get("commit_sha"), default="")
    if commit_status != "succeeded":
        blockers.append("commit_execution_not_succeeded")
    if not commit_sha:
        blockers.append("commit_execution_commit_sha_missing")
    if dry_run:
        blockers.append("dry_run_mode")
    if not _normalize_text(repo_path, default=""):
        blockers.append("execution_repo_path_missing")

    if blockers:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked by prerequisites or run-level guardrails",
            failure_reason="push_execution_blocked_by_preconditions",
            blocking_reasons=blockers,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=remote_name,
        )

    repo_dir = Path(repo_path)
    if not repo_dir.exists() or not repo_dir.is_dir():
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because execution repo path is invalid",
            failure_reason="execution_repo_not_directory",
            blocking_reasons=["execution_repo_not_directory"],
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=remote_name,
        )

    worktree_result = _run_git(repo_path, ["rev-parse", "--is-inside-work-tree"])
    command_summary["rev_parse_worktree_rc"] = worktree_result.returncode
    if worktree_result.returncode != 0:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because repo is not a git worktree",
            failure_reason="repo_not_git_worktree",
            blocking_reasons=["repo_not_git_worktree"],
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=remote_name,
        )

    branch_name = _resolve_current_branch(repo_path, command_summary=command_summary)
    if not branch_name:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because current branch is missing or detached",
            failure_reason="current_branch_unresolved",
            blocking_reasons=["current_branch_unresolved"],
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=remote_name,
            branch_name=branch_name,
        )
    if not head_branch:
        head_branch = branch_name

    remotes = _resolve_git_remotes(repo_path, command_summary=command_summary)
    if not remotes:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because no git remote was configured",
            failure_reason="git_remote_missing",
            blocking_reasons=["git_remote_missing"],
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=remote_name,
            branch_name=branch_name,
        )

    resolved_remote = _normalize_text(remote_name, default="origin")
    if resolved_remote not in set(remotes):
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because configured remote was not found",
            failure_reason="configured_remote_missing",
            blocking_reasons=["configured_remote_missing"],
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=resolved_remote,
            branch_name=branch_name,
        )

    status_result = _run_git(repo_path, ["status", "--porcelain"])
    command_summary["status_rc"] = status_result.returncode
    if status_result.returncode != 0:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because git status failed",
            failure_reason="git_status_failed",
            blocking_reasons=["git_status_failed"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=resolved_remote,
            branch_name=branch_name,
        )
    status_lines = [line.rstrip("\n") for line in (status_result.stdout or "").splitlines() if line.strip()]
    if _has_conflict_status_lines(status_lines):
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because merge conflicts were detected",
            failure_reason="working_tree_conflicts_present",
            blocking_reasons=["working_tree_conflicts_present"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=resolved_remote,
            branch_name=branch_name,
        )

    upstream_result = _run_git(repo_path, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    command_summary["upstream_ref_rc"] = upstream_result.returncode
    if upstream_result.returncode != 0:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because upstream tracking was unresolved",
            failure_reason="upstream_tracking_unresolved",
            blocking_reasons=["upstream_tracking_unresolved"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=resolved_remote,
            branch_name=branch_name,
        )

    upstream_ref = _normalize_text(upstream_result.stdout, default="")
    command_summary["upstream_ref"] = upstream_ref
    if "/" not in upstream_ref:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because upstream ref was ambiguous",
            failure_reason="upstream_ref_ambiguous",
            blocking_reasons=["upstream_ref_ambiguous"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=resolved_remote,
            branch_name=branch_name,
        )

    upstream_remote, _, upstream_branch = upstream_ref.partition("/")
    command_summary["upstream_remote"] = upstream_remote
    command_summary["upstream_branch"] = upstream_branch
    if not upstream_remote or not upstream_branch:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because upstream remote/branch truth was ambiguous",
            failure_reason="upstream_ref_ambiguous",
            blocking_reasons=["upstream_ref_ambiguous"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=resolved_remote,
            branch_name=branch_name,
        )
    if upstream_remote != resolved_remote:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because configured remote conflicted with tracked upstream remote",
            failure_reason="upstream_remote_ambiguous",
            blocking_reasons=["upstream_remote_ambiguous"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=resolved_remote,
            branch_name=branch_name,
        )

    divergence_result = _run_git(repo_path, ["rev-list", "--left-right", "--count", "HEAD...@{u}"])
    command_summary["remote_divergence_rc"] = divergence_result.returncode
    if divergence_result.returncode != 0:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because remote divergence truth was unavailable",
            failure_reason="remote_divergence_status_unavailable",
            blocking_reasons=["remote_divergence_status_unavailable"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=resolved_remote,
            branch_name=branch_name,
        )

    divergence_fields = _normalize_text(divergence_result.stdout, default="").split()
    ahead_count = _as_non_negative_int(divergence_fields[0], default=0) if len(divergence_fields) >= 1 else 0
    behind_count = _as_non_negative_int(divergence_fields[1], default=0) if len(divergence_fields) >= 2 else 0
    command_summary["remote_ahead_count"] = ahead_count
    command_summary["remote_behind_count"] = behind_count
    if behind_count > 0 and ahead_count > 0:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because local and remote branches diverged",
            failure_reason="remote_branch_diverged",
            blocking_reasons=["remote_branch_diverged"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=resolved_remote,
            branch_name=branch_name,
        )
    if behind_count > 0:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="push execution blocked because non-fast-forward risk was detected",
            failure_reason="remote_non_fast_forward_risk",
            blocking_reasons=["remote_non_fast_forward_risk"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=resolved_remote,
            branch_name=branch_name,
        )

    started_at = _iso_now(now)
    push_result = _run_git(repo_path, ["push", resolved_remote, f"HEAD:{head_branch}"])
    command_summary["git_push_rc"] = push_result.returncode
    if push_result.returncode != 0:
        push_text = (
            _normalize_text(push_result.stderr, default="")
            + "\n"
            + _normalize_text(push_result.stdout, default="")
        ).lower()
        if any(
            marker in push_text
            for marker in (
                "non-fast-forward",
                "fetch first",
                "rejected",
                "tip of your current branch is behind",
            )
        ):
            return _build_delivery_execution_blocked_payload(
                schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
                execution_type=_PUSH_EXECUTION_TYPE,
                unit_id=unit_id,
                now=now,
                summary="push execution blocked because non-fast-forward risk was detected during push",
                failure_reason="remote_non_fast_forward_risk",
                blocking_reasons=["remote_non_fast_forward_risk"],
                manual_intervention_required=True,
                command_summary=command_summary,
                base_branch=base_branch,
                head_branch=head_branch,
                remote_name=resolved_remote,
                branch_name=branch_name,
            )
        return {
            **_default_delivery_execution_payload(
                schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
                execution_type=_PUSH_EXECUTION_TYPE,
                unit_id=unit_id,
                now=now,
            ),
            "status": "failed",
            "summary": "push execution failed during git push",
            "started_at": started_at,
            "finished_at": _iso_now(now),
            "branch_name": branch_name,
            "remote_name": resolved_remote,
            "base_branch": base_branch,
            "head_branch": head_branch,
            "command_summary": command_summary,
            "failure_reason": "git_push_failed",
            "manual_intervention_required": True,
            "blocking_reasons": ["git_push_failed"],
            "attempted": True,
            "remote_state_status": "unknown",
            "upstream_tracking_status": "tracked",
            "remote_divergence_status": "unknown",
            "remote_branch_status": "known",
        }

    return {
        **_default_delivery_execution_payload(
            schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
            execution_type=_PUSH_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
        ),
        "status": "succeeded",
        "summary": "push execution succeeded under bounded readiness and run-state conditions",
        "started_at": started_at,
        "finished_at": _iso_now(now),
        "branch_name": branch_name,
        "remote_name": resolved_remote,
        "base_branch": base_branch,
        "head_branch": head_branch,
        "failure_reason": "",
        "blocking_reasons": [],
        "attempted": True,
        "remote_state_status": "ready",
        "upstream_tracking_status": "tracked",
        "remote_divergence_status": "none",
        "remote_branch_status": "known",
    }


def _execute_bounded_pr_creation(
    *,
    unit_id: str,
    job_id: str,
    repository: str,
    base_branch: str,
    run_state_payload: Mapping[str, Any],
    merge_decision_payload: Mapping[str, Any],
    commit_execution_payload: Mapping[str, Any],
    push_execution_payload: Mapping[str, Any],
    read_backend: Any,
    write_backend: Any,
    now: Callable[[], datetime],
) -> dict[str, Any]:
    command_summary: dict[str, Any] = {}
    branch_name = _normalize_text(push_execution_payload.get("branch_name"), default="")
    remote_name = _normalize_text(push_execution_payload.get("remote_name"), default="")
    head_branch = _normalize_text(push_execution_payload.get("head_branch"), default=branch_name)
    pr_number: int | None = None
    pr_url = ""

    blockers = _run_state_execution_blockers(run_state_payload)
    if _normalize_text(commit_execution_payload.get("status"), default="") != "succeeded":
        blockers.append("commit_execution_not_succeeded")
    if _normalize_text(push_execution_payload.get("status"), default="") != "succeeded":
        blockers.append("push_execution_not_succeeded")
    if bool(merge_decision_payload.get("manual_intervention_required", False)):
        blockers.append("merge_manual_intervention_required")
    if not repository:
        blockers.append("repository_missing")
    if not base_branch:
        blockers.append("base_branch_missing")
    if not head_branch:
        blockers.append("head_branch_missing")
    if read_backend is None:
        blockers.append("github_read_backend_unavailable")
    if write_backend is None:
        blockers.append("github_write_backend_unavailable")

    unresolved = _normalize_string_list(merge_decision_payload.get("unresolved_blockers"))
    unexpected_unresolved = [item for item in unresolved if item != "merge_not_requested"]
    if unexpected_unresolved:
        blockers.append("merge_unresolved_blockers_present")

    if blockers:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PR_EXECUTION_SCHEMA_VERSION,
            execution_type=_PR_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="PR creation blocked by prerequisites or ambiguous state",
            failure_reason="pr_creation_blocked_by_preconditions",
            blocking_reasons=blockers,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=remote_name,
            branch_name=branch_name,
        )

    lookup_status, lookup_data = _resolve_open_pr_lookup(
        read_backend=read_backend,
        repository=repository,
        head_branch=head_branch,
        base_branch=base_branch,
    )
    command_summary["open_pr_lookup_status"] = lookup_status
    if lookup_status not in {"success", "empty"}:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PR_EXECUTION_SCHEMA_VERSION,
            execution_type=_PR_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="PR creation blocked because open PR state could not be resolved conservatively",
            failure_reason=f"open_pr_lookup_{lookup_status}",
            blocking_reasons=[f"open_pr_lookup_{lookup_status}"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=remote_name,
            branch_name=branch_name,
        )

    matched = bool(lookup_data.get("matched", False))
    match_count = _as_non_negative_int(lookup_data.get("match_count"), default=0)
    command_summary["open_pr_match_count"] = match_count
    matched_pr = dict(lookup_data.get("pr")) if isinstance(lookup_data.get("pr"), Mapping) else {}
    if matched and match_count > 1:
        return _build_delivery_execution_blocked_payload(
            schema_version=_PR_EXECUTION_SCHEMA_VERSION,
            execution_type=_PR_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="PR creation blocked because existing PR lookup returned ambiguous multiple matches",
            failure_reason="existing_pr_lookup_ambiguous",
            blocking_reasons=["existing_pr_lookup_ambiguous"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=remote_name,
            branch_name=branch_name,
        )
    if matched:
        pr_number = _as_optional_int(matched_pr.get("number"))
        pr_url = _normalize_text(matched_pr.get("html_url"), default="")
        if pr_number is None or pr_number <= 0:
            return _build_delivery_execution_blocked_payload(
                schema_version=_PR_EXECUTION_SCHEMA_VERSION,
                execution_type=_PR_EXECUTION_TYPE,
                unit_id=unit_id,
                now=now,
                summary="PR creation blocked because existing PR identity was ambiguous",
                failure_reason="existing_pr_identity_ambiguous",
                blocking_reasons=["existing_pr_identity_ambiguous"],
                manual_intervention_required=True,
                command_summary=command_summary,
                base_branch=base_branch,
                head_branch=head_branch,
                remote_name=remote_name,
                branch_name=branch_name,
                pr_number=pr_number,
                pr_url=pr_url,
            )
        return _build_delivery_execution_blocked_payload(
            schema_version=_PR_EXECUTION_SCHEMA_VERSION,
            execution_type=_PR_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="PR creation blocked because an existing open PR already matches head/base",
            failure_reason="existing_open_pr_detected",
            blocking_reasons=["existing_open_pr_detected"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=remote_name,
            branch_name=branch_name,
            pr_number=pr_number,
            pr_url=pr_url,
        )

    creator = getattr(write_backend, "create_draft_pr", None)
    if not callable(creator):
        return _build_delivery_execution_blocked_payload(
            schema_version=_PR_EXECUTION_SCHEMA_VERSION,
            execution_type=_PR_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="PR creation blocked because write backend does not support draft PR creation",
            failure_reason="pr_creation_capability_missing",
            blocking_reasons=["pr_creation_capability_missing"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=remote_name,
            branch_name=branch_name,
        )

    commit_sha = _normalize_text(commit_execution_payload.get("commit_sha"), default="")
    title, body = _build_pr_title_and_body(job_id=job_id, unit_id=unit_id, commit_sha=commit_sha)
    started_at = _iso_now(now)
    try:
        create_result = creator(
            repo=repository,
            title=title,
            body=body,
            head_branch=head_branch,
            base_branch=base_branch,
        )
    except Exception:
        create_result = {"status": "api_failure", "data": {}, "error": {"message": "create_pr_exception"}}
    result_map = dict(create_result) if isinstance(create_result, Mapping) else {}
    status = _normalize_text(result_map.get("status"), default="api_failure")
    command_summary["create_pr_status"] = status

    if status != "success":
        return {
            **_default_delivery_execution_payload(
                schema_version=_PR_EXECUTION_SCHEMA_VERSION,
                execution_type=_PR_EXECUTION_TYPE,
                unit_id=unit_id,
                now=now,
            ),
            "status": "failed",
            "summary": "PR creation failed during backend write operation",
            "started_at": started_at,
            "finished_at": _iso_now(now),
            "branch_name": branch_name,
            "remote_name": remote_name,
            "base_branch": base_branch,
            "head_branch": head_branch,
            "command_summary": command_summary,
            "failure_reason": f"pr_creation_failed:{status}",
            "manual_intervention_required": True,
            "blocking_reasons": [f"pr_creation_failed:{status}"],
            "attempted": True,
            "pr_creation_state_status": "failed",
            "existing_pr_status": "none",
        }

    data = dict(result_map.get("data")) if isinstance(result_map.get("data"), Mapping) else {}
    pr_data = dict(data.get("pr")) if isinstance(data.get("pr"), Mapping) else {}
    pr_number = _as_optional_int(pr_data.get("number"))
    pr_url = _normalize_text(pr_data.get("html_url"), default="")
    if pr_number is None or pr_number <= 0:
        return {
            **_default_delivery_execution_payload(
                schema_version=_PR_EXECUTION_SCHEMA_VERSION,
                execution_type=_PR_EXECUTION_TYPE,
                unit_id=unit_id,
                now=now,
            ),
            "status": "failed",
            "summary": "PR creation failed because backend response missed PR identity",
            "started_at": started_at,
            "finished_at": _iso_now(now),
            "branch_name": branch_name,
            "remote_name": remote_name,
            "base_branch": base_branch,
            "head_branch": head_branch,
            "command_summary": command_summary,
            "failure_reason": "pr_creation_identity_missing",
            "manual_intervention_required": True,
            "blocking_reasons": ["pr_creation_identity_missing"],
            "attempted": True,
            "pr_creation_state_status": "failed",
            "existing_pr_status": "none",
        }

    return {
        **_default_delivery_execution_payload(
            schema_version=_PR_EXECUTION_SCHEMA_VERSION,
            execution_type=_PR_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
        ),
        "status": "succeeded",
        "summary": "PR creation succeeded under bounded readiness and run-state conditions",
        "started_at": started_at,
        "finished_at": _iso_now(now),
        "branch_name": branch_name,
        "remote_name": remote_name,
        "base_branch": base_branch,
        "head_branch": head_branch,
        "pr_number": pr_number,
        "pr_url": pr_url,
        "command_summary": command_summary,
        "failure_reason": "",
        "manual_intervention_required": False,
        "blocking_reasons": [],
        "attempted": True,
        "existing_pr_status": "none",
        "pr_creation_state_status": "created",
    }


def _resolve_merge_decision_for_execution(
    *,
    merge_decision_payload: Mapping[str, Any],
    push_execution_payload: Mapping[str, Any],
    pr_execution_payload: Mapping[str, Any],
    commit_execution_payload: Mapping[str, Any],
    run_state_payload: Mapping[str, Any],
) -> dict[str, Any]:
    payload = dict(merge_decision_payload)
    unresolved = _normalize_string_list(payload.get("unresolved_blockers"))
    if (
        _normalize_text(payload.get("decision"), default="") == "blocked"
        and _normalize_text(payload.get("rule_id"), default="") == "merge_blocked_not_requested"
        and set(unresolved).issubset({"merge_not_requested"})
        and _normalize_text(commit_execution_payload.get("status"), default="") == "succeeded"
        and _normalize_text(push_execution_payload.get("status"), default="") == "succeeded"
        and _normalize_text(pr_execution_payload.get("status"), default="") == "succeeded"
        and not _run_state_execution_blockers(run_state_payload)
    ):
        payload["decision"] = "allowed"
        payload["rule_id"] = "merge_allowed_after_pr_creation"
        payload["summary"] = "merge recommendation allowed after bounded commit, push, and PR creation"
        payload["blocking_reasons"] = []
        payload["recommended_next_action"] = "proceed_to_merge"
        payload["readiness_status"] = "ready"
        payload["readiness_next_action"] = "prepare_merge"
        payload["automation_eligible"] = True
        payload["manual_intervention_required"] = False
        payload["unresolved_blockers"] = []
        payload["prerequisites_satisfied"] = True
    return payload


def _execute_bounded_merge(
    *,
    unit_id: str,
    repository: str,
    run_state_payload: Mapping[str, Any],
    merge_decision_payload: Mapping[str, Any],
    commit_execution_payload: Mapping[str, Any],
    push_execution_payload: Mapping[str, Any],
    pr_execution_payload: Mapping[str, Any],
    read_backend: Any,
    write_backend: Any,
    now: Callable[[], datetime],
) -> dict[str, Any]:
    command_summary: dict[str, Any] = {}
    branch_name = _normalize_text(push_execution_payload.get("branch_name"), default="")
    remote_name = _normalize_text(push_execution_payload.get("remote_name"), default="")
    base_branch = _normalize_text(pr_execution_payload.get("base_branch"), default="")
    head_branch = _normalize_text(pr_execution_payload.get("head_branch"), default=branch_name)
    pr_number = _as_optional_int(pr_execution_payload.get("pr_number"))

    blockers = _run_state_execution_blockers(run_state_payload)
    if _normalize_text(merge_decision_payload.get("readiness_status"), default="") != "ready":
        blockers.append("merge_readiness_not_ready")
    if not bool(merge_decision_payload.get("automation_eligible", False)):
        blockers.append("merge_automation_not_eligible")
    if bool(merge_decision_payload.get("manual_intervention_required", False)):
        blockers.append("merge_manual_intervention_required")
    if _normalize_string_list(merge_decision_payload.get("unresolved_blockers")):
        blockers.append("merge_unresolved_blockers_present")
    if not bool(merge_decision_payload.get("prerequisites_satisfied", False)):
        blockers.append("merge_prerequisites_unsatisfied")
    if _normalize_text(commit_execution_payload.get("status"), default="") != "succeeded":
        blockers.append("commit_execution_not_succeeded")
    commit_sha = _normalize_text(commit_execution_payload.get("commit_sha"), default="")
    if not commit_sha:
        blockers.append("commit_execution_commit_sha_missing")
    if _normalize_text(push_execution_payload.get("status"), default="") != "succeeded":
        blockers.append("push_execution_not_succeeded")
    if _normalize_text(pr_execution_payload.get("status"), default="") != "succeeded":
        blockers.append("pr_creation_not_succeeded")
    if pr_number is None or pr_number <= 0:
        blockers.append("pr_number_missing_or_invalid")
    if not repository:
        blockers.append("repository_missing")
    if read_backend is None:
        blockers.append("github_pr_status_summary_unavailable")
    if write_backend is None:
        blockers.append("github_write_backend_unavailable")

    pr_status_summary_data: dict[str, Any] = {}
    if read_backend is not None and pr_number is not None and pr_number > 0:
        status_getter = getattr(read_backend, "get_pr_status_summary", None)
        if not callable(status_getter):
            blockers.append("github_pr_status_summary_unavailable")
        else:
            try:
                status_summary_payload = status_getter(
                    repository,
                    pr_number=pr_number,
                )
            except Exception:
                status_summary_payload = {"status": "api_failure", "data": {}}
            status_summary_map = (
                dict(status_summary_payload)
                if isinstance(status_summary_payload, Mapping)
                else {"status": "api_failure", "data": {}}
            )
            status_summary_status = _normalize_text(status_summary_map.get("status"), default="api_failure")
            command_summary["pr_status_summary_status"] = status_summary_status
            pr_status_summary_data = (
                dict(status_summary_map.get("data"))
                if isinstance(status_summary_map.get("data"), Mapping)
                else {}
            )
            if status_summary_status != "success":
                blockers.append(f"merge_pr_status_summary_{status_summary_status}")
            else:
                pr_state = _normalize_text(pr_status_summary_data.get("pr_state"), default="")
                if pr_state and pr_state != "open":
                    blockers.append("merge_pr_not_open")
                mergeable_state = _normalize_text(pr_status_summary_data.get("mergeable_state"), default="")
                if not mergeable_state:
                    blockers.append("mergeability_unknown")
                elif mergeable_state not in {"clean"}:
                    blockers.append("mergeability_not_ready")
                checks_state = _normalize_text(pr_status_summary_data.get("checks_state"), default="")
                if checks_state != "passing":
                    blockers.append("required_checks_unsatisfied")
                review_state_status = _normalize_text(
                    pr_status_summary_data.get("review_state_status"),
                    default="",
                )
                if review_state_status in {"unsatisfied", "required", "changes_requested"}:
                    blockers.append("review_requirements_unsatisfied")
                branch_protection_status = _normalize_text(
                    pr_status_summary_data.get("branch_protection_status"),
                    default="",
                )
                if branch_protection_status in {"unsatisfied", "blocked", "required"}:
                    blockers.append("branch_protection_unsatisfied")
                command_summary["mergeable_state"] = mergeable_state
                command_summary["checks_state"] = checks_state
                if review_state_status:
                    command_summary["review_state_status"] = review_state_status
                if branch_protection_status:
                    command_summary["branch_protection_status"] = branch_protection_status

    if blockers:
        return _build_delivery_execution_blocked_payload(
            schema_version=_MERGE_EXECUTION_SCHEMA_VERSION,
            execution_type=_MERGE_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="merge execution blocked by readiness or run-level preconditions",
            failure_reason="merge_execution_blocked_by_preconditions",
            blocking_reasons=blockers,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=remote_name,
            branch_name=branch_name,
            pr_number=pr_number,
            pr_url=_normalize_text(pr_execution_payload.get("pr_url"), default=""),
        )

    merger = getattr(write_backend, "merge_pull_request", None)
    if not callable(merger):
        return _build_delivery_execution_blocked_payload(
            schema_version=_MERGE_EXECUTION_SCHEMA_VERSION,
            execution_type=_MERGE_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
            summary="merge execution blocked because write backend does not support merge",
            failure_reason="merge_execution_capability_missing",
            blocking_reasons=["merge_execution_capability_missing"],
            manual_intervention_required=True,
            command_summary=command_summary,
            base_branch=base_branch,
            head_branch=head_branch,
            remote_name=remote_name,
            branch_name=branch_name,
            pr_number=pr_number,
            pr_url=_normalize_text(pr_execution_payload.get("pr_url"), default=""),
        )

    started_at = _iso_now(now)
    try:
        merge_result = merger(
            repo=repository,
            pr_number=pr_number,
            expected_head_sha=commit_sha,
        )
    except Exception:
        merge_result = {"status": "api_failure", "data": {}, "error": {"message": "merge_exception"}}

    result_map = dict(merge_result) if isinstance(merge_result, Mapping) else {}
    status = _normalize_text(result_map.get("status"), default="api_failure")
    command_summary["merge_status"] = status
    if status != "success":
        return {
            **_default_delivery_execution_payload(
                schema_version=_MERGE_EXECUTION_SCHEMA_VERSION,
                execution_type=_MERGE_EXECUTION_TYPE,
                unit_id=unit_id,
                now=now,
            ),
            "status": "failed",
            "summary": "merge execution failed during backend merge operation",
            "started_at": started_at,
            "finished_at": _iso_now(now),
            "branch_name": branch_name,
            "remote_name": remote_name,
            "base_branch": base_branch,
            "head_branch": head_branch,
            "pr_number": pr_number,
            "pr_url": _normalize_text(pr_execution_payload.get("pr_url"), default=""),
            "command_summary": command_summary,
            "failure_reason": f"merge_execution_failed:{status}",
            "manual_intervention_required": True,
            "blocking_reasons": [f"merge_execution_failed:{status}"],
            "attempted": True,
            "mergeability_status": _normalize_text(
                pr_status_summary_data.get("mergeable_state"),
                default="unknown",
            ),
            "required_checks_status": _normalize_text(
                pr_status_summary_data.get("checks_state"),
                default="unknown",
            ),
            "review_state_status": _normalize_text(
                pr_status_summary_data.get("review_state_status"),
                default="unknown",
            ),
            "branch_protection_status": _normalize_text(
                pr_status_summary_data.get("branch_protection_status"),
                default="unknown",
            ),
            "merge_requirements_status": "unknown",
        }

    data = dict(result_map.get("data")) if isinstance(result_map.get("data"), Mapping) else {}
    merge_commit_sha = _normalize_text(data.get("merge_commit_sha"), default="")
    if not merge_commit_sha:
        return {
            **_default_delivery_execution_payload(
                schema_version=_MERGE_EXECUTION_SCHEMA_VERSION,
                execution_type=_MERGE_EXECUTION_TYPE,
                unit_id=unit_id,
                now=now,
            ),
            "status": "failed",
            "summary": "merge execution failed because backend response missed merge commit sha",
            "started_at": started_at,
            "finished_at": _iso_now(now),
            "branch_name": branch_name,
            "remote_name": remote_name,
            "base_branch": base_branch,
            "head_branch": head_branch,
            "pr_number": pr_number,
            "pr_url": _normalize_text(pr_execution_payload.get("pr_url"), default=""),
            "command_summary": command_summary,
            "failure_reason": "merge_commit_sha_missing",
            "manual_intervention_required": True,
            "blocking_reasons": ["merge_commit_sha_missing"],
            "attempted": True,
            "mergeability_status": _normalize_text(
                pr_status_summary_data.get("mergeable_state"),
                default="unknown",
            ),
            "required_checks_status": _normalize_text(
                pr_status_summary_data.get("checks_state"),
                default="unknown",
            ),
            "review_state_status": _normalize_text(
                pr_status_summary_data.get("review_state_status"),
                default="unknown",
            ),
            "branch_protection_status": _normalize_text(
                pr_status_summary_data.get("branch_protection_status"),
                default="unknown",
            ),
            "merge_requirements_status": "unknown",
        }

    return {
        **_default_delivery_execution_payload(
            schema_version=_MERGE_EXECUTION_SCHEMA_VERSION,
            execution_type=_MERGE_EXECUTION_TYPE,
            unit_id=unit_id,
            now=now,
        ),
        "status": "succeeded",
        "summary": "merge execution succeeded under bounded readiness and run-state conditions",
        "started_at": started_at,
        "finished_at": _iso_now(now),
        "branch_name": branch_name,
        "remote_name": remote_name,
        "base_branch": base_branch,
        "head_branch": head_branch,
        "pr_number": pr_number,
        "pr_url": _normalize_text(pr_execution_payload.get("pr_url"), default=""),
        "merge_commit_sha": merge_commit_sha,
        "command_summary": command_summary,
        "failure_reason": "",
        "manual_intervention_required": False,
        "blocking_reasons": [],
        "attempted": True,
        "mergeability_status": _normalize_text(
            pr_status_summary_data.get("mergeable_state"),
            default="clean",
        ),
        "required_checks_status": _normalize_text(
            pr_status_summary_data.get("checks_state"),
            default="passing",
        ),
        "review_state_status": _normalize_text(
            pr_status_summary_data.get("review_state_status"),
            default="unknown",
        ),
        "branch_protection_status": _normalize_text(
            pr_status_summary_data.get("branch_protection_status"),
            default="unknown",
        ),
        "merge_requirements_status": "satisfied",
    }


def _augment_run_state_with_delivery_execution(
    *,
    run_state_payload: Mapping[str, Any],
    manifest_units: list[Mapping[str, Any]],
) -> dict[str, Any]:
    def _status_counts(key: str) -> dict[str, int]:
        counts = {"succeeded": 0, "failed": 0, "blocked": 0}
        for unit in manifest_units:
            summary = dict(unit.get(key)) if isinstance(unit.get(key), Mapping) else {}
            status = _normalize_text(summary.get("status"), default="")
            if status in counts:
                counts[status] += 1
        return counts

    push_counts = _status_counts("push_execution_summary")
    pr_counts = _status_counts("pr_execution_summary")
    merge_counts = _status_counts("merge_execution_summary")
    manual_required = any(
        bool(dict(unit.get(key)).get("manual_intervention_required", False))
        for unit in manifest_units
        for key in ("push_execution_summary", "pr_execution_summary", "merge_execution_summary")
        if isinstance(unit.get(key), Mapping)
    )
    return {
        **dict(run_state_payload),
        "push_execution_summary": push_counts,
        "pr_execution_summary": pr_counts,
        "merge_execution_summary": merge_counts,
        "push_execution_succeeded": push_counts["succeeded"] > 0,
        "pr_execution_succeeded": pr_counts["succeeded"] > 0,
        "merge_execution_succeeded": merge_counts["succeeded"] > 0,
        "push_execution_pending": push_counts["blocked"] > 0,
        "pr_execution_pending": pr_counts["blocked"] > 0,
        "merge_execution_pending": merge_counts["blocked"] > 0,
        "push_execution_failed": push_counts["failed"] > 0,
        "pr_execution_failed": pr_counts["failed"] > 0,
        "merge_execution_failed": merge_counts["failed"] > 0,
        "delivery_execution_manual_intervention_required": manual_required,
    }


def _default_rollback_execution_payload(
    *,
    unit_id: str,
    now: Callable[[], datetime],
) -> dict[str, Any]:
    return {
        "schema_version": _ROLLBACK_EXECUTION_SCHEMA_VERSION,
        "unit_id": unit_id,
        "execution_type": _ROLLBACK_EXECUTION_TYPE,
        "rollback_mode": "unknown",
        "status": "blocked",
        "summary": "rollback execution blocked",
        "started_at": "",
        "finished_at": _iso_now(now),
        "trigger_reason": "",
        "source_execution_state_summary": {},
        "resulting_commit_sha": "",
        "resulting_pr_state": "",
        "resulting_branch_state": {},
        "command_summary": {},
        "failure_reason": "rollback_execution_not_attempted",
        "manual_intervention_required": False,
        "replan_required": False,
        "automatic_continuation_blocked": True,
        "blocking_reasons": [],
        "attempted": False,
        "execution_allowed": False,
        "execution_authority_status": "unknown",
        "validation_status": "unknown",
        "execution_gate_status": "unknown",
        "authority_blocked_reasons": [],
        "validation_blocked_reasons": [],
        "authority_blocked_reason": "",
        "validation_blocked_reason": "",
        "missing_prerequisites": [],
        "missing_required_refs": [],
        "unsafe_repo_state": [],
        "remote_pr_ambiguity": [],
        "manual_approval_required": False,
        # Rollback aftermath safety is intentionally tracked separately from
        # rollback execution status so successful execution does not imply
        # safely-closed recovery state.
        "rollback_aftermath_status": "incomplete",
        "rollback_aftermath_blocked": True,
        "rollback_aftermath_blocked_reason": "",
        "rollback_aftermath_blocked_reasons": [],
        "rollback_aftermath_missing_or_ambiguous": True,
        "rollback_validation_status": "unavailable",
        "rollback_manual_followup_required": False,
        "rollback_remote_followup_required": False,
        "rollback_conflict_status": "unknown",
        "rollback_remote_state_status": "unknown",
        "rollback_divergence_status": "unknown",
        "rollback_pr_state_status": "unknown",
        "rollback_branch_state_status": "unknown",
        "rollback_repo_cleanliness_status": "unknown",
        "rollback_head_state_status": "unknown",
        "rollback_revert_commit_status": "unknown",
        "rollback_post_validation_status": "unavailable",
        "rollback_remote_github_status": "unknown",
    }


def _normalize_rollback_validation_status(value: Any, *, default: str) -> str:
    normalized = _normalize_text(value, default="")
    if normalized in _ROLLBACK_VALIDATION_STATUSES:
        return normalized
    return default


def _is_rollback_aftermath_missing_or_ambiguous_reason(reason: str) -> bool:
    return any(token in reason for token in _ROLLBACK_AFTERMATH_MISSING_OR_AMBIGUOUS_REASON_TOKENS)


def _with_rollback_aftermath_surface(payload: Mapping[str, Any]) -> dict[str, Any]:
    mutable = dict(payload)
    rollback_mode = _normalize_text(mutable.get("rollback_mode"), default="unknown")
    status = _normalize_text(mutable.get("status"), default="blocked")
    failure_reason = _normalize_text(mutable.get("failure_reason"), default="")
    blocking_reasons = _serialize_required_signals(
        _normalize_string_list(mutable.get("blocking_reasons"))
    )
    manual_intervention_required = bool(mutable.get("manual_intervention_required", False))
    replan_required = bool(mutable.get("replan_required", False))
    automatic_continuation_blocked = bool(mutable.get("automatic_continuation_blocked", False))
    resulting_commit_sha = _normalize_text(mutable.get("resulting_commit_sha"), default="")
    resulting_pr_state = _normalize_text(mutable.get("resulting_pr_state"), default="")
    resulting_branch_state = (
        dict(mutable.get("resulting_branch_state"))
        if isinstance(mutable.get("resulting_branch_state"), Mapping)
        else {}
    )
    command_summary = (
        dict(mutable.get("command_summary"))
        if isinstance(mutable.get("command_summary"), Mapping)
        else {}
    )

    validation_status = _normalize_rollback_validation_status(
        mutable.get("rollback_validation_status"),
        default="",
    )
    post_validation_status = _normalize_rollback_validation_status(
        mutable.get("rollback_post_validation_status"),
        default="",
    )
    if not validation_status:
        if status == "failed":
            validation_status = "failed"
        elif status == "blocked":
            validation_status = "unavailable"
        elif status == "succeeded":
            if rollback_mode == "merged":
                validation_status = post_validation_status or "unavailable"
            elif resulting_commit_sha:
                validation_status = "satisfied"
            else:
                validation_status = "ambiguous"
        else:
            validation_status = "unavailable"
    if not post_validation_status:
        post_validation_status = validation_status

    explicit_manual_followup = mutable.get("rollback_manual_followup_required")
    manual_followup_required = (
        bool(explicit_manual_followup)
        if isinstance(explicit_manual_followup, bool)
        else False
    )
    if not manual_followup_required:
        manual_followup_required = (
            manual_intervention_required
            or replan_required
            or validation_status in {"failed", "ambiguous", "unavailable"}
            or status in {"blocked", "failed"}
        )

    explicit_remote_followup = mutable.get("rollback_remote_followup_required")
    remote_followup_required = (
        bool(explicit_remote_followup)
        if isinstance(explicit_remote_followup, bool)
        else False
    )
    if not remote_followup_required and status == "succeeded" and rollback_mode in {
        "pushed_or_pr_open",
        "merged",
    }:
        remote_followup_required = True

    aftermath_missing_or_ambiguous = bool(
        mutable.get("rollback_aftermath_missing_or_ambiguous", False)
    )
    if not aftermath_missing_or_ambiguous:
        aftermath_missing_or_ambiguous = any(
            _is_rollback_aftermath_missing_or_ambiguous_reason(reason)
            for reason in blocking_reasons
        ) or validation_status in {"ambiguous", "unavailable"}
    if status == "succeeded" and not resulting_commit_sha:
        aftermath_missing_or_ambiguous = True

    rollback_conflict_status = _normalize_text(
        mutable.get("rollback_conflict_status"),
        default="",
    )
    if not rollback_conflict_status:
        rollback_conflict_status = (
            "conflict_detected"
            if any("conflict" in reason for reason in blocking_reasons)
            or "conflict" in failure_reason
            else "none"
            if status == "succeeded"
            else "unknown"
        )

    rollback_repo_cleanliness_status = _normalize_text(
        mutable.get("rollback_repo_cleanliness_status"),
        default="",
    )
    if not rollback_repo_cleanliness_status:
        rollback_repo_cleanliness_status = (
            "not_clean"
            if "working_tree_not_clean" in blocking_reasons
            else "clean"
            if status == "succeeded"
            else "unknown"
        )

    rollback_head_state_status = _normalize_text(
        mutable.get("rollback_head_state_status"),
        default="",
    )
    if not rollback_head_state_status:
        rollback_head_state_status = (
            "confirmed"
            if status == "succeeded" and bool(resulting_commit_sha)
            else "unresolved"
            if any("head" in reason for reason in blocking_reasons)
            else "unknown"
        )

    rollback_revert_commit_status = _normalize_text(
        mutable.get("rollback_revert_commit_status"),
        default="",
    )
    if not rollback_revert_commit_status:
        rollback_revert_commit_status = (
            "created"
            if status == "succeeded" and bool(resulting_commit_sha)
            else "missing"
            if status == "succeeded"
            else "failed"
            if status == "failed"
            else "unknown"
        )

    rollback_branch_state_status = _normalize_text(
        mutable.get("rollback_branch_state_status"),
        default="",
    )
    if not rollback_branch_state_status:
        rollback_branch_state_status = (
            "aligned"
            if status == "succeeded" and bool(resulting_branch_state)
            else "unknown"
        )

    rollback_pr_state_status = _normalize_text(
        mutable.get("rollback_pr_state_status"),
        default="",
    )
    if not rollback_pr_state_status:
        rollback_pr_state_status = (
            resulting_pr_state
            if resulting_pr_state
            else "not_applicable"
            if rollback_mode == "local_commit_only"
            else "unknown"
        )

    rollback_remote_state_status = _normalize_text(
        mutable.get("rollback_remote_state_status"),
        default="",
    )
    if not rollback_remote_state_status:
        if rollback_mode == "local_commit_only":
            rollback_remote_state_status = "not_applicable"
        elif remote_followup_required and aftermath_missing_or_ambiguous:
            rollback_remote_state_status = "ambiguous"
        elif remote_followup_required:
            rollback_remote_state_status = "followup_required"
        else:
            rollback_remote_state_status = "unknown"

    rollback_remote_github_status = _normalize_text(
        mutable.get("rollback_remote_github_status"),
        default="",
    )
    if not rollback_remote_github_status:
        if rollback_mode == "local_commit_only":
            rollback_remote_github_status = "not_applicable"
        elif remote_followup_required and aftermath_missing_or_ambiguous:
            rollback_remote_github_status = "ambiguous"
        elif remote_followup_required:
            rollback_remote_github_status = "followup_required"
        else:
            rollback_remote_github_status = "unknown"

    rollback_divergence_status = _normalize_text(
        mutable.get("rollback_divergence_status"),
        default="",
    )
    if not rollback_divergence_status:
        rollback_divergence_status = (
            "unknown"
            if rollback_remote_state_status in {"followup_required", "ambiguous"}
            else "none"
            if status == "succeeded"
            else "unknown"
        )

    aftermath_status = _normalize_text(mutable.get("rollback_aftermath_status"), default="")
    if aftermath_status not in _ROLLBACK_AFTERMATH_STATUSES:
        if status == "failed":
            aftermath_status = (
                "validation_failed"
                if validation_status == "failed"
                else "blocked"
            )
        elif status == "blocked":
            aftermath_status = "ambiguous" if aftermath_missing_or_ambiguous else "blocked"
        elif status == "succeeded":
            if validation_status == "failed":
                aftermath_status = "validation_failed"
            elif remote_followup_required:
                aftermath_status = "remote_followup_required"
            elif manual_followup_required or automatic_continuation_blocked:
                aftermath_status = "completed_manual_followup_required"
            elif aftermath_missing_or_ambiguous:
                aftermath_status = "ambiguous"
            elif not resulting_commit_sha:
                aftermath_status = "incomplete"
            else:
                aftermath_status = "completed_safe"
        else:
            aftermath_status = "incomplete"

    derived_blocked_reasons = _serialize_required_signals(
        _normalize_string_list(mutable.get("rollback_aftermath_blocked_reasons"))
        + blocking_reasons
    )
    if validation_status == "failed":
        derived_blocked_reasons = _serialize_required_signals(
            [*derived_blocked_reasons, "rollback_validation_failed"]
        )
    if remote_followup_required:
        derived_blocked_reasons = _serialize_required_signals(
            [*derived_blocked_reasons, "rollback_remote_followup_required"]
        )
    if manual_followup_required:
        derived_blocked_reasons = _serialize_required_signals(
            [*derived_blocked_reasons, "rollback_manual_followup_required"]
        )
    if aftermath_missing_or_ambiguous:
        derived_blocked_reasons = _serialize_required_signals(
            [*derived_blocked_reasons, "rollback_aftermath_missing_or_ambiguous"]
        )

    aftermath_blocked = bool(mutable.get("rollback_aftermath_blocked", False))
    if not aftermath_blocked:
        aftermath_blocked = aftermath_status != "completed_safe"

    mutable.update(
        {
            "rollback_validation_status": validation_status,
            "rollback_post_validation_status": post_validation_status,
            "rollback_manual_followup_required": manual_followup_required,
            "rollback_remote_followup_required": remote_followup_required,
            "rollback_aftermath_status": aftermath_status,
            "rollback_aftermath_blocked": aftermath_blocked,
            "rollback_aftermath_blocked_reason": (
                _normalize_text(mutable.get("rollback_aftermath_blocked_reason"), default="")
                or (derived_blocked_reasons[0] if derived_blocked_reasons else "")
            ),
            "rollback_aftermath_blocked_reasons": derived_blocked_reasons,
            "rollback_aftermath_missing_or_ambiguous": aftermath_missing_or_ambiguous,
            "rollback_conflict_status": rollback_conflict_status,
            "rollback_remote_state_status": rollback_remote_state_status,
            "rollback_divergence_status": rollback_divergence_status,
            "rollback_pr_state_status": rollback_pr_state_status,
            "rollback_branch_state_status": rollback_branch_state_status,
            "rollback_repo_cleanliness_status": rollback_repo_cleanliness_status,
            "rollback_head_state_status": rollback_head_state_status,
            "rollback_revert_commit_status": rollback_revert_commit_status,
            "rollback_remote_github_status": rollback_remote_github_status,
        }
    )
    if "rollback_target_ref_drift_detected" in blocking_reasons:
        mutable["rollback_head_state_status"] = "drift_detected"
    if _normalize_text(command_summary.get("git_revert_rc"), default="") == "0":
        mutable["rollback_revert_commit_status"] = "created"
    return mutable


def _build_rollback_execution_blocked_payload(
    *,
    unit_id: str,
    now: Callable[[], datetime],
    rollback_mode: str,
    summary: str,
    failure_reason: str,
    blocking_reasons: list[str],
    trigger_reason: str,
    source_execution_state_summary: Mapping[str, Any] | None = None,
    manual_intervention_required: bool = False,
    replan_required: bool = False,
    command_summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _default_rollback_execution_payload(unit_id=unit_id, now=now)
    payload["rollback_mode"] = rollback_mode if rollback_mode in _ROLLBACK_MODES else "unknown"
    payload["summary"] = summary
    payload["failure_reason"] = failure_reason
    payload["blocking_reasons"] = _serialize_required_signals(list(blocking_reasons))
    payload["trigger_reason"] = _normalize_text(trigger_reason, default="")
    payload["source_execution_state_summary"] = (
        dict(source_execution_state_summary)
        if isinstance(source_execution_state_summary, Mapping)
        else {}
    )
    payload["manual_intervention_required"] = manual_intervention_required
    payload["replan_required"] = replan_required
    payload["command_summary"] = dict(command_summary) if isinstance(command_summary, Mapping) else {}
    return _with_execution_gate_surface(payload)


def _normalize_branch_ref(branch_name: str) -> str:
    normalized = _normalize_text(branch_name, default="")
    if not normalized:
        return ""
    if normalized.startswith("refs/"):
        return normalized
    return f"refs/heads/{normalized}"


def _resolve_rollback_mode(
    *,
    commit_execution_payload: Mapping[str, Any] | None,
    push_execution_payload: Mapping[str, Any] | None,
    pr_execution_payload: Mapping[str, Any] | None,
    merge_execution_payload: Mapping[str, Any] | None,
) -> tuple[str, dict[str, Any]]:
    commit_status = _normalize_text(
        (commit_execution_payload or {}).get("status"),
        default="missing",
    )
    push_status = _normalize_text(
        (push_execution_payload or {}).get("status"),
        default="missing",
    )
    pr_status = _normalize_text(
        (pr_execution_payload or {}).get("status"),
        default="missing",
    )
    merge_status = _normalize_text(
        (merge_execution_payload or {}).get("status"),
        default="missing",
    )

    mode = "unknown"
    if merge_status == "succeeded":
        mode = "merged"
    elif push_status == "succeeded" or pr_status == "succeeded":
        mode = "pushed_or_pr_open"
    elif commit_status == "succeeded":
        mode = "local_commit_only"

    return mode, {
        "mode": mode,
        "commit_execution_status": commit_status,
        "push_execution_status": push_status,
        "pr_execution_status": pr_status,
        "merge_execution_status": merge_status,
        "commit_sha": _normalize_text((commit_execution_payload or {}).get("commit_sha"), default=""),
        "merge_commit_sha": _normalize_text((merge_execution_payload or {}).get("merge_commit_sha"), default=""),
        "pr_number": _as_optional_int((pr_execution_payload or {}).get("pr_number")),
    }


def _rollback_readiness_allows_execution(
    *,
    rollback_decision: Mapping[str, Any],
    run_state_payload: Mapping[str, Any],
) -> tuple[bool, bool]:
    decision = _normalize_text(rollback_decision.get("decision"), default="")
    readiness_status = _normalize_text(rollback_decision.get("readiness_status"), default="")
    prerequisites_satisfied = bool(rollback_decision.get("prerequisites_satisfied", False))
    manual_required = bool(rollback_decision.get("manual_intervention_required", False))
    unresolved_blockers = _normalize_string_list(rollback_decision.get("unresolved_blockers"))
    next_run_action = _normalize_text(run_state_payload.get("next_run_action"), default="")
    rollback_pending = bool(run_state_payload.get("rollback_evaluation_pending", False)) or (
        next_run_action == "evaluate_rollback"
    )

    allowed_compat_unresolved = {
        "run_global_stop_recommended",
        "run_paused",
        "run_rollback_evaluation_pending",
    }
    unexpected_unresolved = [
        item for item in unresolved_blockers if item not in allowed_compat_unresolved
    ]
    if unexpected_unresolved:
        return False, False
    if decision != "required" or manual_required or not prerequisites_satisfied:
        return False, False
    if readiness_status == "ready":
        return True, False
    # Compatibility adapter for PR27 overlays where rollback stays
    # `awaiting_prerequisites` during rollback-evaluation pending.
    if readiness_status == "awaiting_prerequisites" and rollback_pending:
        return True, True
    return False, False


def _evaluate_rollback_execution_blockers(
    *,
    rollback_decision: Mapping[str, Any],
    run_state_payload: Mapping[str, Any],
    rollback_mode: str,
    source_execution_state_summary: Mapping[str, Any],
    execution_repo_path: str,
    dry_run: bool,
) -> tuple[list[str], bool]:
    blockers: list[str] = []
    readiness_allows_execution, compatibility_override = _rollback_readiness_allows_execution(
        rollback_decision=rollback_decision,
        run_state_payload=run_state_payload,
    )
    if not readiness_allows_execution:
        blockers.append("rollback_readiness_not_ready")

    if not bool(rollback_decision.get("prerequisites_satisfied", False)):
        blockers.append("rollback_prerequisites_unsatisfied")
    if bool(rollback_decision.get("manual_intervention_required", False)):
        blockers.append("rollback_manual_intervention_required")

    unresolved = _normalize_string_list(rollback_decision.get("unresolved_blockers"))
    allowed_compat_unresolved = {
        "run_global_stop_recommended",
        "run_paused",
        "run_rollback_evaluation_pending",
    }
    unexpected_unresolved = [item for item in unresolved if item not in allowed_compat_unresolved]
    if unexpected_unresolved:
        blockers.append("rollback_unresolved_blockers_present")

    automation_eligible = rollback_decision.get("automation_eligible")
    if automation_eligible is False and not compatibility_override:
        blockers.append("rollback_automation_not_eligible")

    run_next_action = _normalize_text(run_state_payload.get("next_run_action"), default="")
    run_continue_allowed = bool(run_state_payload.get("continue_allowed", False))
    run_manual_required = bool(run_state_payload.get("manual_intervention_required", False))
    run_rollback_pending = bool(run_state_payload.get("rollback_evaluation_pending", False)) or (
        run_next_action == "evaluate_rollback"
    )
    if run_manual_required:
        blockers.append("run_manual_intervention_required")
    if run_continue_allowed and not run_rollback_pending:
        blockers.append("run_continue_allowed_contradicts_rollback")
    if run_next_action in {"continue_run", "complete_run"} and not run_rollback_pending:
        blockers.append("run_state_not_in_rollback_phase")

    if dry_run:
        blockers.append("dry_run_mode")
    if not _normalize_text(execution_repo_path, default=""):
        blockers.append("execution_repo_path_missing")
    if rollback_mode not in _ROLLBACK_MODES or rollback_mode == "unknown":
        blockers.append("rollback_mode_ambiguous")

    source_summary = dict(source_execution_state_summary)
    commit_status = _normalize_text(source_summary.get("commit_execution_status"), default="")
    push_status = _normalize_text(source_summary.get("push_execution_status"), default="")
    pr_status = _normalize_text(source_summary.get("pr_execution_status"), default="")
    merge_status = _normalize_text(source_summary.get("merge_execution_status"), default="")
    if rollback_mode == "local_commit_only":
        if commit_status != "succeeded":
            blockers.append("commit_execution_not_succeeded")
    if rollback_mode == "pushed_or_pr_open":
        if push_status != "succeeded" and pr_status != "succeeded":
            blockers.append("push_or_pr_receipt_not_succeeded")
        if merge_status == "succeeded":
            blockers.append("merge_already_succeeded")
    if rollback_mode == "merged":
        if merge_status != "succeeded":
            blockers.append("merge_execution_not_succeeded")
        if not _normalize_text(source_summary.get("merge_commit_sha"), default=""):
            blockers.append("merge_execution_commit_sha_missing")
    if merge_status == "succeeded" and commit_status != "succeeded":
        blockers.append("merge_receipt_without_commit_receipt")

    return _serialize_required_signals(blockers), compatibility_override


def _execute_bounded_rollback(
    *,
    unit_id: str,
    repo_path: str,
    run_state_payload: Mapping[str, Any],
    rollback_decision_payload: Mapping[str, Any],
    commit_execution_payload: Mapping[str, Any] | None,
    push_execution_payload: Mapping[str, Any] | None,
    pr_execution_payload: Mapping[str, Any] | None,
    merge_execution_payload: Mapping[str, Any] | None,
    dry_run: bool,
    now: Callable[[], datetime],
) -> dict[str, Any]:
    mode, source_summary = _resolve_rollback_mode(
        commit_execution_payload=commit_execution_payload,
        push_execution_payload=push_execution_payload,
        pr_execution_payload=pr_execution_payload,
        merge_execution_payload=merge_execution_payload,
    )
    trigger_reason = _normalize_text(
        rollback_decision_payload.get("recommended_next_action"),
        default=_normalize_text(rollback_decision_payload.get("decision"), default="rollback_required"),
    )

    blockers, compatibility_override = _evaluate_rollback_execution_blockers(
        rollback_decision=rollback_decision_payload,
        run_state_payload=run_state_payload,
        rollback_mode=mode,
        source_execution_state_summary=source_summary,
        execution_repo_path=repo_path,
        dry_run=dry_run,
    )
    if blockers:
        return _build_rollback_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            rollback_mode=mode,
            summary="rollback execution blocked by readiness, run-state, or lifecycle-evidence preconditions",
            failure_reason="rollback_execution_blocked_by_preconditions",
            blocking_reasons=blockers,
            trigger_reason=trigger_reason,
            source_execution_state_summary=source_summary,
            manual_intervention_required=True,
            replan_required=False,
        )

    if mode == "pushed_or_pr_open":
        return _build_rollback_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            rollback_mode=mode,
            summary="rollback execution blocked because pushed or PR-open rollback path is not safely automated in this phase",
            failure_reason="rollback_mode_pushed_or_pr_open_requires_manual_path",
            blocking_reasons=["rollback_mode_pushed_or_pr_open_requires_manual_path"],
            trigger_reason=trigger_reason,
            source_execution_state_summary=source_summary,
            manual_intervention_required=True,
            replan_required=True,
        )

    repo_dir = Path(repo_path)
    command_summary: dict[str, Any] = {"compatibility_override_used": compatibility_override}
    if not repo_dir.exists() or not repo_dir.is_dir():
        return _build_rollback_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            rollback_mode=mode,
            summary="rollback execution blocked because execution repo path is invalid",
            failure_reason="execution_repo_not_directory",
            blocking_reasons=["execution_repo_not_directory"],
            trigger_reason=trigger_reason,
            source_execution_state_summary=source_summary,
            manual_intervention_required=True,
            command_summary=command_summary,
        )

    worktree_result = _run_git(repo_path, ["rev-parse", "--is-inside-work-tree"])
    command_summary["rev_parse_worktree_rc"] = worktree_result.returncode
    if worktree_result.returncode != 0:
        return _build_rollback_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            rollback_mode=mode,
            summary="rollback execution blocked because repo is not a git worktree",
            failure_reason="repo_not_git_worktree",
            blocking_reasons=["repo_not_git_worktree"],
            trigger_reason=trigger_reason,
            source_execution_state_summary=source_summary,
            manual_intervention_required=True,
            command_summary=command_summary,
        )

    status_result = _run_git(repo_path, ["status", "--porcelain"])
    command_summary["status_rc"] = status_result.returncode
    if status_result.returncode != 0:
        return _build_rollback_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            rollback_mode=mode,
            summary="rollback execution blocked because git status failed",
            failure_reason="git_status_failed",
            blocking_reasons=["git_status_failed"],
            trigger_reason=trigger_reason,
            source_execution_state_summary=source_summary,
            manual_intervention_required=True,
            command_summary=command_summary,
        )

    status_lines = [line.rstrip("\n") for line in (status_result.stdout or "").splitlines() if line.strip()]
    command_summary["status_lines"] = len(status_lines)
    if status_lines:
        return _build_rollback_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            rollback_mode=mode,
            summary="rollback execution blocked because working tree is not clean",
            failure_reason="working_tree_not_clean",
            blocking_reasons=["working_tree_not_clean"],
            trigger_reason=trigger_reason,
            source_execution_state_summary=source_summary,
            manual_intervention_required=True,
            command_summary=command_summary,
        )
    if _has_conflict_status_lines(status_lines):
        return _build_rollback_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            rollback_mode=mode,
            summary="rollback execution blocked because merge conflicts were detected",
            failure_reason="working_tree_conflicts_present",
            blocking_reasons=["working_tree_conflicts_present"],
            trigger_reason=trigger_reason,
            source_execution_state_summary=source_summary,
            manual_intervention_required=True,
            command_summary=command_summary,
        )

    head_result = _run_git(repo_path, ["rev-parse", "HEAD"])
    command_summary["rev_parse_head_rc"] = head_result.returncode
    current_head = (head_result.stdout or "").strip() if head_result.returncode == 0 else ""
    if not current_head:
        return _build_rollback_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            rollback_mode=mode,
            summary="rollback execution blocked because current HEAD could not be resolved",
            failure_reason="head_resolution_failed",
            blocking_reasons=["head_resolution_failed"],
            trigger_reason=trigger_reason,
            source_execution_state_summary=source_summary,
            manual_intervention_required=True,
            command_summary=command_summary,
        )

    branch_name = _resolve_current_branch(repo_path, command_summary=command_summary)
    if not branch_name:
        return _build_rollback_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            rollback_mode=mode,
            summary="rollback execution blocked because current branch is missing or detached",
            failure_reason="current_branch_unresolved",
            blocking_reasons=["current_branch_unresolved"],
            trigger_reason=trigger_reason,
            source_execution_state_summary=source_summary,
            manual_intervention_required=True,
            command_summary=command_summary,
        )

    target_branch = branch_name
    target_ref = _normalize_branch_ref(target_branch)
    if mode == "merged":
        merged_base = _normalize_text((merge_execution_payload or {}).get("base_branch"), default="")
        pr_base = _normalize_text((pr_execution_payload or {}).get("base_branch"), default="")
        push_base = _normalize_text((push_execution_payload or {}).get("base_branch"), default="")
        target_branch = merged_base or pr_base or push_base
        if not target_branch:
            return _build_rollback_execution_blocked_payload(
                unit_id=unit_id,
                now=now,
                rollback_mode=mode,
                summary="rollback execution blocked because merged rollback target branch was not available",
                failure_reason="rollback_target_branch_missing",
                blocking_reasons=["rollback_target_branch_missing"],
                trigger_reason=trigger_reason,
                source_execution_state_summary=source_summary,
                manual_intervention_required=True,
                command_summary=command_summary,
            )
        target_ref = _normalize_branch_ref(target_branch)

    target_head_result = _run_git(repo_path, ["rev-parse", target_ref])
    command_summary["target_ref_rc"] = target_head_result.returncode
    target_head = (target_head_result.stdout or "").strip() if target_head_result.returncode == 0 else ""
    if not target_head:
        return _build_rollback_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            rollback_mode=mode,
            summary="rollback execution blocked because rollback target ref could not be resolved",
            failure_reason="rollback_target_ref_unresolved",
            blocking_reasons=["rollback_target_ref_unresolved"],
            trigger_reason=trigger_reason,
            source_execution_state_summary=source_summary,
            manual_intervention_required=True,
            command_summary=command_summary,
        )
    if target_head != current_head:
        return _build_rollback_execution_blocked_payload(
            unit_id=unit_id,
            now=now,
            rollback_mode=mode,
            summary="rollback execution blocked because target ref drifted from current HEAD",
            failure_reason="rollback_target_ref_drift_detected",
            blocking_reasons=["rollback_target_ref_drift_detected"],
            trigger_reason=trigger_reason,
            source_execution_state_summary=source_summary,
            manual_intervention_required=True,
            command_summary=command_summary,
        )

    rollback_target_sha = ""
    if mode == "local_commit_only":
        rollback_target_sha = _normalize_text((commit_execution_payload or {}).get("commit_sha"), default="")
        if not rollback_target_sha:
            return _build_rollback_execution_blocked_payload(
                unit_id=unit_id,
                now=now,
                rollback_mode=mode,
                summary="rollback execution blocked because committed rollback target sha was missing",
                failure_reason="rollback_target_commit_sha_missing",
                blocking_reasons=["rollback_target_commit_sha_missing"],
                trigger_reason=trigger_reason,
                source_execution_state_summary=source_summary,
                manual_intervention_required=True,
                command_summary=command_summary,
            )
        if rollback_target_sha != current_head:
            return _build_rollback_execution_blocked_payload(
                unit_id=unit_id,
                now=now,
                rollback_mode=mode,
                summary="rollback execution blocked because current HEAD does not match committed rollback target",
                failure_reason="rollback_target_head_mismatch",
                blocking_reasons=["rollback_target_head_mismatch"],
                trigger_reason=trigger_reason,
                source_execution_state_summary=source_summary,
                manual_intervention_required=True,
                command_summary=command_summary,
            )
    else:
        rollback_target_sha = _normalize_text((merge_execution_payload or {}).get("merge_commit_sha"), default="")
        if not rollback_target_sha:
            return _build_rollback_execution_blocked_payload(
                unit_id=unit_id,
                now=now,
                rollback_mode=mode,
                summary="rollback execution blocked because merge rollback target sha was missing",
                failure_reason="rollback_target_merge_sha_missing",
                blocking_reasons=["rollback_target_merge_sha_missing"],
                trigger_reason=trigger_reason,
                source_execution_state_summary=source_summary,
                manual_intervention_required=True,
                command_summary=command_summary,
            )
        if rollback_target_sha != current_head:
            return _build_rollback_execution_blocked_payload(
                unit_id=unit_id,
                now=now,
                rollback_mode=mode,
                summary="rollback execution blocked because current HEAD does not match merged rollback target",
                failure_reason="rollback_target_head_mismatch",
                blocking_reasons=["rollback_target_head_mismatch"],
                trigger_reason=trigger_reason,
                source_execution_state_summary=source_summary,
                manual_intervention_required=True,
                command_summary=command_summary,
            )
        parent_result = _run_git(repo_path, ["rev-list", "--parents", "-n", "1", rollback_target_sha])
        command_summary["rev_list_parents_rc"] = parent_result.returncode
        parents = _normalize_string_list((parent_result.stdout or "").split(), sort_items=False)
        if parent_result.returncode != 0 or len(parents) < 3:
            return _build_rollback_execution_blocked_payload(
                unit_id=unit_id,
                now=now,
                rollback_mode=mode,
                summary="rollback execution blocked because merged rollback target was not a valid merge commit",
                failure_reason="rollback_target_not_merge_commit",
                blocking_reasons=["rollback_target_not_merge_commit"],
                trigger_reason=trigger_reason,
                source_execution_state_summary=source_summary,
                manual_intervention_required=True,
                command_summary=command_summary,
            )

    started_at = _iso_now(now)
    revert_args = [
        "-c",
        "user.name=Codex Local Runner",
        "-c",
        "user.email=codex-local-runner@example.com",
        "revert",
        "--no-edit",
    ]
    if mode == "merged":
        revert_args.extend(["-m", "1"])
    revert_args.append(rollback_target_sha)
    revert_result = _run_git(repo_path, revert_args)
    command_summary["git_revert_rc"] = revert_result.returncode
    if revert_result.returncode != 0:
        abort_result = _run_git(repo_path, ["revert", "--abort"])
        command_summary["git_revert_abort_rc"] = abort_result.returncode
        return {
            **_default_rollback_execution_payload(unit_id=unit_id, now=now),
            "rollback_mode": mode,
            "status": "failed",
            "summary": "rollback execution failed during git revert",
            "started_at": started_at,
            "finished_at": _iso_now(now),
            "trigger_reason": trigger_reason,
            "source_execution_state_summary": source_summary,
            "resulting_pr_state": "unchanged",
            "resulting_branch_state": {
                "target_ref": target_ref,
                "target_branch": target_branch,
                "before_sha": current_head,
                "after_sha": "",
            },
            "command_summary": command_summary,
            "failure_reason": "git_revert_failed",
            "manual_intervention_required": True,
            "replan_required": False,
            "automatic_continuation_blocked": True,
            "blocking_reasons": ["git_revert_failed"],
            "attempted": True,
        }

    post_head_result = _run_git(repo_path, ["rev-parse", "HEAD"])
    command_summary["post_revert_head_rc"] = post_head_result.returncode
    resulting_sha = (post_head_result.stdout or "").strip() if post_head_result.returncode == 0 else ""
    if not resulting_sha or resulting_sha == current_head:
        return {
            **_default_rollback_execution_payload(unit_id=unit_id, now=now),
            "rollback_mode": mode,
            "status": "failed",
            "summary": "rollback execution failed to produce a new commit after git revert",
            "started_at": started_at,
            "finished_at": _iso_now(now),
            "trigger_reason": trigger_reason,
            "source_execution_state_summary": source_summary,
            "resulting_pr_state": "unchanged",
            "resulting_branch_state": {
                "target_ref": target_ref,
                "target_branch": target_branch,
                "before_sha": current_head,
                "after_sha": resulting_sha,
            },
            "command_summary": command_summary,
            "failure_reason": "rollback_result_commit_missing",
            "manual_intervention_required": True,
            "replan_required": False,
            "automatic_continuation_blocked": True,
            "blocking_reasons": ["rollback_result_commit_missing"],
            "attempted": True,
        }

    return {
        **_default_rollback_execution_payload(unit_id=unit_id, now=now),
        "rollback_mode": mode,
        "status": "succeeded",
        "summary": "rollback execution succeeded under explicit readiness and lifecycle-evidence gating",
        "started_at": started_at,
        "finished_at": _iso_now(now),
        "trigger_reason": trigger_reason,
        "source_execution_state_summary": source_summary,
        "resulting_commit_sha": resulting_sha,
        "resulting_pr_state": (
            "manual_followup_required"
            if mode == "pushed_or_pr_open"
            else "unchanged"
        ),
        "resulting_branch_state": {
            "target_ref": target_ref,
            "target_branch": target_branch,
            "before_sha": current_head,
            "after_sha": resulting_sha,
        },
        "command_summary": command_summary,
        "failure_reason": "",
        "manual_intervention_required": False,
        "replan_required": True,
        "automatic_continuation_blocked": True,
        "blocking_reasons": [],
        "attempted": True,
    }


def _augment_run_state_with_rollback_execution(
    *,
    run_state_payload: Mapping[str, Any],
    manifest_units: list[Mapping[str, Any]],
) -> dict[str, Any]:
    statuses = {"succeeded": 0, "failed": 0, "blocked": 0}
    attempted_any = False
    manual_required = False
    replan_required = False
    automatic_continuation_blocked = False

    for unit in manifest_units:
        summary = dict(unit.get("rollback_execution_summary")) if isinstance(unit.get("rollback_execution_summary"), Mapping) else {}
        status = _normalize_text(summary.get("status"), default="")
        if status in statuses:
            statuses[status] += 1
        attempted_any = attempted_any or bool(summary.get("attempted", False))
        manual_required = manual_required or bool(summary.get("manual_intervention_required", False))
        replan_required = replan_required or bool(summary.get("replan_required", False))
        automatic_continuation_blocked = automatic_continuation_blocked or bool(
            summary.get("automatic_continuation_blocked", False)
        )

    rollback_failed = statuses["failed"] > 0
    rollback_succeeded = statuses["succeeded"] > 0
    rollback_pending = statuses["blocked"] > 0
    rollback_manual_intervention_required = manual_required or rollback_failed
    rollback_auto_blocked = (
        automatic_continuation_blocked
        or rollback_succeeded
        or rollback_failed
        or rollback_manual_intervention_required
    )

    return {
        **dict(run_state_payload),
        "rollback_execution_summary": statuses,
        "rollback_execution_attempted": attempted_any,
        "rollback_execution_succeeded": rollback_succeeded,
        "rollback_execution_pending": rollback_pending,
        "rollback_execution_failed": rollback_failed,
        "rollback_execution_manual_intervention_required": rollback_manual_intervention_required,
        "rollback_replan_required": replan_required,
        "rollback_automatic_continuation_blocked": rollback_auto_blocked,
    }


def _augment_run_state_with_rollback_aftermath(
    *,
    run_state_payload: Mapping[str, Any],
    manifest_units: list[Mapping[str, Any]],
) -> dict[str, Any]:
    aftermath_statuses: dict[str, int] = {
        status: 0 for status in sorted(_ROLLBACK_AFTERMATH_STATUSES)
    }
    blocked = False
    manual_required = False
    missing_or_ambiguous = False
    remote_followup_required = False
    manual_followup_required = False
    validation_failed = False
    blocked_reasons: list[str] = []
    dominant_status = "incomplete"

    for unit in manifest_units:
        summary = (
            dict(unit.get("rollback_execution_summary"))
            if isinstance(unit.get("rollback_execution_summary"), Mapping)
            else {}
        )
        if not summary:
            continue
        status = _normalize_text(summary.get("rollback_aftermath_status"), default="")
        if status in aftermath_statuses:
            aftermath_statuses[status] += 1
        stage_blocked = bool(summary.get("rollback_aftermath_blocked", False)) or status not in {
            "",
            "completed_safe",
        }
        blocked = blocked or stage_blocked
        manual_followup_required = manual_followup_required or bool(
            summary.get("rollback_manual_followup_required", False)
        )
        remote_followup_required = remote_followup_required or bool(
            summary.get("rollback_remote_followup_required", False)
        )
        manual_required = manual_required or manual_followup_required or bool(
            summary.get("manual_intervention_required", False)
        )
        stage_missing_or_ambiguous = bool(
            summary.get("rollback_aftermath_missing_or_ambiguous", False)
        )
        missing_or_ambiguous = missing_or_ambiguous or stage_missing_or_ambiguous
        validation_status = _normalize_text(summary.get("rollback_validation_status"), default="")
        if validation_status == "failed" or status == "validation_failed":
            validation_failed = True
        blocked_reasons.extend(
            _normalize_string_list(summary.get("rollback_aftermath_blocked_reasons"))
        )
        blocked_reason = _normalize_text(summary.get("rollback_aftermath_blocked_reason"), default="")
        if blocked_reason:
            blocked_reasons.append(blocked_reason)

    blocked_reasons = _serialize_required_signals(blocked_reasons)
    ranked_statuses = sorted(
        aftermath_statuses.items(),
        key=lambda item: (-item[1], item[0]),
    )
    if ranked_statuses and ranked_statuses[0][1] > 0:
        dominant_status = ranked_statuses[0][0]
    return {
        **dict(run_state_payload),
        "rollback_aftermath_summary": aftermath_statuses,
        "rollback_aftermath_status": dominant_status,
        "rollback_aftermath_blocked": blocked,
        "rollback_aftermath_manual_required": manual_required,
        "rollback_aftermath_missing_or_ambiguous": missing_or_ambiguous,
        "rollback_aftermath_blocked_reason": blocked_reasons[0] if blocked_reasons else "",
        "rollback_aftermath_blocked_reasons": blocked_reasons,
        "rollback_remote_followup_required": remote_followup_required,
        "rollback_manual_followup_required": manual_followup_required,
        "rollback_validation_failed": validation_failed,
    }


def _augment_run_state_with_authority_validation(
    *,
    run_state_payload: Mapping[str, Any],
    manifest_units: list[Mapping[str, Any]],
) -> dict[str, Any]:
    stage_keys = {
        "commit": ("commit_execution_summary",),
        "delivery": ("push_execution_summary", "pr_execution_summary", "merge_execution_summary"),
        "rollback": ("rollback_execution_summary",),
    }
    authority_validation_summary: dict[str, dict[str, int]] = {
        stage: {
            "checked": 0,
            "allowed": 0,
            "authority_blocked": 0,
            "validation_blocked": 0,
            "manual_required": 0,
            "unknown": 0,
        }
        for stage in stage_keys
    }
    blocked_reasons: list[str] = []
    execution_authority_blocked = False
    validation_blocked = False
    manual_required = False
    missing_or_ambiguous = False

    for stage, keys in stage_keys.items():
        stage_summary = authority_validation_summary[stage]
        for unit in manifest_units:
            for key in keys:
                summary = dict(unit.get(key)) if isinstance(unit.get(key), Mapping) else {}
                if not summary:
                    continue
                if "dry_run_mode" in _normalize_string_list(summary.get("blocking_reasons")):
                    continue
                stage_summary["checked"] += 1
                status = _normalize_text(summary.get("status"), default="")
                if status not in {"blocked", "failed", "succeeded"}:
                    continue
                if bool(summary.get("execution_allowed", False)):
                    stage_summary["allowed"] += 1
                authority_status = _normalize_text(summary.get("execution_authority_status"), default="")
                validation_status = _normalize_text(summary.get("validation_status"), default="")
                if authority_status == "blocked":
                    stage_summary["authority_blocked"] += 1
                    execution_authority_blocked = True
                if validation_status == "blocked":
                    stage_summary["validation_blocked"] += 1
                    validation_blocked = True
                if authority_status == "unknown" or validation_status == "unknown":
                    stage_summary["unknown"] += 1
                    missing_or_ambiguous = True
                if bool(summary.get("manual_approval_required", False)):
                    stage_summary["manual_required"] += 1
                    manual_required = True
                blocked_reasons.extend(_normalize_string_list(summary.get("authority_blocked_reasons")))
                blocked_reasons.extend(_normalize_string_list(summary.get("validation_blocked_reasons")))
                blocked_reasons.extend(_normalize_string_list(summary.get("missing_prerequisites")))
                blocked_reasons.extend(_normalize_string_list(summary.get("missing_required_refs")))
                blocked_reasons.extend(_normalize_string_list(summary.get("unsafe_repo_state")))
                blocked_reasons.extend(_normalize_string_list(summary.get("remote_pr_ambiguity")))

    blocked_reasons = _serialize_required_signals(blocked_reasons)
    authority_validation_blocked = (
        execution_authority_blocked
        or validation_blocked
        or missing_or_ambiguous
    )
    return {
        **dict(run_state_payload),
        "authority_validation_summary": authority_validation_summary,
        "authority_validation_blocked": authority_validation_blocked,
        "execution_authority_blocked": execution_authority_blocked,
        "validation_blocked": validation_blocked,
        "authority_validation_manual_required": manual_required,
        "authority_validation_missing_or_ambiguous": missing_or_ambiguous,
        "authority_validation_blocked_reason": blocked_reasons[0] if blocked_reasons else "",
        "authority_validation_blocked_reasons": blocked_reasons,
    }


def _augment_run_state_with_remote_github(
    *,
    run_state_payload: Mapping[str, Any],
    manifest_units: list[Mapping[str, Any]],
) -> dict[str, Any]:
    stage_keys = {
        "push": ("push_execution_summary",),
        "pr_creation": ("pr_execution_summary",),
        "merge": ("merge_execution_summary",),
    }
    remote_github_summary: dict[str, dict[str, int]] = {
        stage: {
            "checked": 0,
            "blocked": 0,
            "manual_required": 0,
            "missing_or_ambiguous": 0,
        }
        for stage in stage_keys
    }
    blocked = False
    manual_required = False
    missing_or_ambiguous = False
    blocked_reasons: list[str] = []

    for stage, keys in stage_keys.items():
        stage_summary = remote_github_summary[stage]
        for unit in manifest_units:
            for key in keys:
                summary = dict(unit.get(key)) if isinstance(unit.get(key), Mapping) else {}
                if not summary:
                    continue
                stage_summary["checked"] += 1
                stage_blocked = bool(summary.get("remote_github_blocked", False)) or bool(
                    summary.get("remote_state_blocked", False)
                )
                if stage_blocked:
                    stage_summary["blocked"] += 1
                    blocked = True
                stage_manual_required = bool(summary.get("manual_intervention_required", False)) and stage_blocked
                if stage_manual_required:
                    stage_summary["manual_required"] += 1
                    manual_required = True
                stage_missing_or_ambiguous = bool(
                    summary.get("remote_github_missing_or_ambiguous", False)
                ) or bool(summary.get("remote_state_missing_or_ambiguous", False))
                if stage_missing_or_ambiguous:
                    stage_summary["missing_or_ambiguous"] += 1
                    missing_or_ambiguous = True

                blocked_reasons.extend(_normalize_string_list(summary.get("remote_github_blocked_reasons")))
                blocked_reason = _normalize_text(summary.get("remote_github_blocked_reason"), default="")
                if blocked_reason:
                    blocked_reasons.append(blocked_reason)
                blocked_reasons.extend(_normalize_string_list(summary.get("remote_pr_ambiguity")))
                remote_state_blocked_reason = _normalize_text(
                    summary.get("remote_state_blocked_reason"),
                    default="",
                )
                if remote_state_blocked_reason:
                    blocked_reasons.append(remote_state_blocked_reason)

    blocked_reasons = _serialize_required_signals(blocked_reasons)
    return {
        **dict(run_state_payload),
        "remote_github_summary": remote_github_summary,
        "remote_github_blocked": blocked,
        "remote_github_manual_required": manual_required or blocked,
        "remote_github_missing_or_ambiguous": missing_or_ambiguous,
        "remote_github_blocked_reason": blocked_reasons[0] if blocked_reasons else "",
        "remote_github_blocked_reasons": blocked_reasons,
    }


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


def _unit_readiness_status(
    *,
    decision_summary: Mapping[str, Any],
    readiness_name: str,
    fallback_allowed_decision_name: str,
) -> str:
    readiness_status = _normalize_text(decision_summary.get(f"{readiness_name}_readiness_status"), default="")
    if readiness_status:
        return readiness_status
    if _normalize_text(decision_summary.get(fallback_allowed_decision_name), default="") == "allowed":
        return "ready"
    return ""


def _resolve_closed_loop_orchestration(
    *,
    run_state_payload: Mapping[str, Any],
    manifest_units: list[Mapping[str, Any]],
    run_status: str,
) -> dict[str, Any]:
    global_stop_recommended = bool(run_state_payload.get("global_stop_recommended", False)) or bool(
        run_state_payload.get("global_stop", False)
    )
    manual_intervention_required = bool(run_state_payload.get("manual_intervention_required", False))
    rollback_evaluation_pending = bool(run_state_payload.get("rollback_evaluation_pending", False)) or (
        _normalize_text(run_state_payload.get("next_run_action"), default="") == "evaluate_rollback"
    )
    run_paused = bool(run_state_payload.get("run_paused", False))
    continue_allowed = bool(run_state_payload.get("continue_allowed", False))
    units_pending = _as_non_negative_int(run_state_payload.get("units_pending"), default=0)
    rollback_execution_succeeded = bool(run_state_payload.get("rollback_execution_succeeded", False))
    rollback_execution_failed = bool(run_state_payload.get("rollback_execution_failed", False))
    rollback_replan_required = bool(run_state_payload.get("rollback_replan_required", False))
    rollback_auto_blocked = bool(run_state_payload.get("rollback_automatic_continuation_blocked", False))
    rollback_aftermath_status = _normalize_text(
        run_state_payload.get("rollback_aftermath_status"),
        default="incomplete",
    )
    rollback_aftermath_blocked = bool(run_state_payload.get("rollback_aftermath_blocked", False))
    rollback_aftermath_manual_required = bool(
        run_state_payload.get("rollback_aftermath_manual_required", False)
    )
    rollback_aftermath_missing_or_ambiguous = bool(
        run_state_payload.get("rollback_aftermath_missing_or_ambiguous", False)
    )
    rollback_aftermath_blocked_reasons = _normalize_string_list(
        run_state_payload.get("rollback_aftermath_blocked_reasons")
    )
    rollback_remote_followup_required = bool(
        run_state_payload.get("rollback_remote_followup_required", False)
    )
    rollback_manual_followup_required = bool(
        run_state_payload.get("rollback_manual_followup_required", False)
    )
    rollback_validation_failed = bool(run_state_payload.get("rollback_validation_failed", False))
    delivery_completed = bool(run_state_payload.get("merge_execution_succeeded", False))
    authority_validation_blocked = bool(run_state_payload.get("authority_validation_blocked", False))
    execution_authority_blocked = bool(run_state_payload.get("execution_authority_blocked", False))
    validation_blocked = bool(run_state_payload.get("validation_blocked", False))
    authority_validation_manual_required = bool(
        run_state_payload.get("authority_validation_manual_required", False)
    )
    authority_validation_missing_or_ambiguous = bool(
        run_state_payload.get("authority_validation_missing_or_ambiguous", False)
    )
    authority_validation_blocked_reasons = _normalize_string_list(
        run_state_payload.get("authority_validation_blocked_reasons")
    )
    remote_github_blocked = bool(run_state_payload.get("remote_github_blocked", False))
    remote_github_manual_required = bool(run_state_payload.get("remote_github_manual_required", False))
    remote_github_missing_or_ambiguous = bool(
        run_state_payload.get("remote_github_missing_or_ambiguous", False)
    )
    remote_github_blocked_reasons = _normalize_string_list(
        run_state_payload.get("remote_github_blocked_reasons")
    )

    commit_ready_pending = False
    push_pending = False
    pr_pending = False
    merge_pending = False
    rollback_ready_pending = False
    ambiguous_reasons: list[str] = []

    for unit in manifest_units:
        decision_summary = _unit_decision_summary(unit)
        if not decision_summary:
            ambiguous_reasons.append("unit_decision_summary_missing")
            continue

        commit_readiness = _unit_readiness_status(
            decision_summary=decision_summary,
            readiness_name="commit",
            fallback_allowed_decision_name="commit_decision",
        )
        merge_readiness = _unit_readiness_status(
            decision_summary=decision_summary,
            readiness_name="merge",
            fallback_allowed_decision_name="merge_decision",
        )
        rollback_readiness = _unit_readiness_status(
            decision_summary=decision_summary,
            readiness_name="rollback",
            fallback_allowed_decision_name="rollback_decision",
        )
        if (
            not rollback_readiness
            and _normalize_text(decision_summary.get("rollback_decision"), default="") == "required"
        ):
            rollback_readiness = "ready"

        commit_status = _unit_execution_status(
            unit=unit,
            decision_summary=decision_summary,
            execution_name="commit_execution",
        )
        push_status = _unit_execution_status(
            unit=unit,
            decision_summary=decision_summary,
            execution_name="push_execution",
        )
        pr_status = _unit_execution_status(
            unit=unit,
            decision_summary=decision_summary,
            execution_name="pr_execution",
        )
        merge_status = _unit_execution_status(
            unit=unit,
            decision_summary=decision_summary,
            execution_name="merge_execution",
        )
        rollback_status = _unit_execution_status(
            unit=unit,
            decision_summary=decision_summary,
            execution_name="rollback_execution",
        )

        commit_ready_pending = commit_ready_pending or (
            commit_readiness == "ready" and commit_status not in {"succeeded", "failed"}
        )
        push_pending = push_pending or (
            commit_status == "succeeded" and push_status not in {"succeeded", "failed"}
        )
        pr_pending = pr_pending or (
            push_status == "succeeded" and pr_status not in {"succeeded", "failed"}
        )
        merge_pending = merge_pending or (
            merge_readiness == "ready"
            and pr_status == "succeeded"
            and merge_status not in {"succeeded", "failed"}
        )
        rollback_ready_pending = rollback_ready_pending or (
            rollback_readiness == "ready" and rollback_status not in {"succeeded", "failed"}
        )

        if pr_status == "succeeded" and push_status == "failed":
            ambiguous_reasons.append("pr_succeeded_but_push_failed")
        if merge_status == "succeeded" and pr_status == "failed":
            ambiguous_reasons.append("merge_succeeded_but_pr_failed")
        if merge_status == "succeeded" and commit_status == "failed":
            ambiguous_reasons.append("merge_succeeded_but_commit_failed")

    loop_state = "runnable_blocked"
    next_safe_action = "pause"
    loop_blocked_reasons: list[str] = []
    terminal = False
    resumable = True
    loop_manual_required = manual_intervention_required
    loop_replan_required = rollback_replan_required
    rollback_completed = rollback_execution_succeeded or rollback_execution_failed

    if global_stop_recommended:
        loop_state = "manual_intervention_required"
        next_safe_action = "require_manual_intervention"
        loop_blocked_reasons.append("global_stop_recommended")
        loop_manual_required = True
    elif rollback_execution_failed:
        loop_state = "terminal_failure"
        next_safe_action = "stop_terminal_failure"
        loop_blocked_reasons.append("rollback_execution_failed")
        loop_manual_required = True
        terminal = True
        resumable = False
    elif rollback_execution_succeeded and (
        rollback_aftermath_blocked
        or rollback_aftermath_missing_or_ambiguous
        or rollback_validation_failed
        or rollback_remote_followup_required
        or rollback_manual_followup_required
    ):
        loop_state = "rollback_completed_blocked"
        next_safe_action = "require_manual_intervention"
        loop_blocked_reasons.extend(
            rollback_aftermath_blocked_reasons
            or [f"rollback_aftermath:{rollback_aftermath_status}"]
        )
        loop_manual_required = (
            True
            if (
                rollback_aftermath_manual_required
                or rollback_manual_followup_required
                or rollback_remote_followup_required
                or rollback_validation_failed
                or rollback_aftermath_missing_or_ambiguous
            )
            else loop_manual_required
        )
        loop_replan_required = loop_replan_required or rollback_validation_failed
        terminal = False
        resumable = True
    elif rollback_replan_required:
        loop_state = "replan_required"
        next_safe_action = "require_replanning"
        loop_blocked_reasons.append("rollback_replan_required")
        terminal = False
        resumable = False
        loop_replan_required = True
    elif rollback_execution_succeeded and rollback_auto_blocked:
        loop_state = "rollback_completed_blocked"
        next_safe_action = "pause"
        loop_blocked_reasons.append("rollback_completed_auto_continuation_blocked")
        terminal = False
        resumable = True
    elif authority_validation_blocked or authority_validation_missing_or_ambiguous:
        loop_state = "manual_intervention_required"
        next_safe_action = "require_manual_intervention"
        loop_blocked_reasons.extend(
            authority_validation_blocked_reasons
            or [
                "authority_validation_blocked"
                if authority_validation_blocked
                else "authority_validation_missing_or_ambiguous"
            ]
        )
        loop_manual_required = True
    elif remote_github_blocked or remote_github_missing_or_ambiguous:
        loop_state = "manual_intervention_required"
        next_safe_action = "require_manual_intervention"
        loop_blocked_reasons.extend(
            remote_github_blocked_reasons
            or [
                "remote_github_blocked"
                if remote_github_blocked
                else "remote_github_missing_or_ambiguous"
            ]
        )
        loop_manual_required = True
    elif manual_intervention_required:
        loop_state = "manual_intervention_required"
        next_safe_action = "require_manual_intervention"
        loop_blocked_reasons.append("manual_intervention_required")
        loop_manual_required = True
    elif ambiguous_reasons:
        loop_state = "runnable_blocked"
        next_safe_action = "pause"
        loop_blocked_reasons.extend(_serialize_required_signals(ambiguous_reasons))
        loop_manual_required = True
    elif rollback_evaluation_pending:
        if rollback_ready_pending:
            loop_state = "rollback_pending"
            next_safe_action = "execute_rollback"
        else:
            loop_state = "runnable_blocked"
            next_safe_action = "pause"
            loop_blocked_reasons.append("rollback_pending_without_ready_unit")
            loop_manual_required = True
    elif commit_ready_pending:
        loop_state = "delivery_in_progress"
        next_safe_action = "execute_commit"
    elif push_pending:
        loop_state = "delivery_in_progress"
        next_safe_action = "execute_push"
    elif pr_pending:
        loop_state = "delivery_in_progress"
        next_safe_action = "execute_pr_creation"
    elif merge_pending:
        loop_state = "delivery_in_progress"
        next_safe_action = "execute_merge"
    elif delivery_completed:
        loop_state = "terminal_success"
        next_safe_action = "stop_terminal_success"
        terminal = True
        resumable = False
    elif run_status == "failed":
        loop_state = "terminal_failure"
        next_safe_action = "stop_terminal_failure"
        loop_blocked_reasons.append("run_failed")
        terminal = True
        resumable = False
        loop_manual_required = True
    elif units_pending > 0:
        loop_state = "resumable_interrupted"
        next_safe_action = "continue_waiting"
        resumable = True
    elif run_paused:
        loop_state = "paused"
        next_safe_action = "pause"
    elif continue_allowed:
        loop_state = "runnable_waiting"
        next_safe_action = "advance_evaluation_step"
    else:
        loop_state = "runnable_waiting"
        next_safe_action = "continue_waiting"

    if loop_state not in _LOOP_STATES:
        loop_state = "runnable_blocked"
    if next_safe_action not in _LOOP_NEXT_SAFE_ACTIONS:
        next_safe_action = "pause"
        loop_blocked_reasons.append("loop_next_safe_action_unknown")

    unique_blocked_reasons = _serialize_required_signals(loop_blocked_reasons)
    return {
        "loop_state": loop_state,
        "next_safe_action": next_safe_action,
        "loop_blocked_reason": unique_blocked_reasons[0] if unique_blocked_reasons else "",
        "loop_blocked_reasons": unique_blocked_reasons,
        "resumable": resumable,
        "terminal": terminal,
        "loop_manual_intervention_required": loop_manual_required,
        "loop_replan_required": loop_replan_required,
        "rollback_completed": rollback_completed,
        "delivery_completed": delivery_completed,
        "loop_allowed_actions": sorted(_LOOP_NEXT_SAFE_ACTIONS),
        "rollback_aftermath_status": rollback_aftermath_status,
        "rollback_aftermath_blocked": rollback_aftermath_blocked,
        "rollback_aftermath_manual_required": rollback_aftermath_manual_required,
        "rollback_aftermath_missing_or_ambiguous": rollback_aftermath_missing_or_ambiguous,
        "rollback_aftermath_blocked_reason": (
            rollback_aftermath_blocked_reasons[0] if rollback_aftermath_blocked_reasons else ""
        ),
        "rollback_aftermath_blocked_reasons": rollback_aftermath_blocked_reasons,
        "rollback_remote_followup_required": rollback_remote_followup_required,
        "rollback_manual_followup_required": rollback_manual_followup_required,
        "rollback_validation_failed": rollback_validation_failed,
        "authority_validation_blocked": authority_validation_blocked,
        "execution_authority_blocked": execution_authority_blocked,
        "validation_blocked": validation_blocked,
        "authority_validation_manual_required": authority_validation_manual_required,
        "authority_validation_missing_or_ambiguous": authority_validation_missing_or_ambiguous,
        "authority_validation_blocked_reason": (
            authority_validation_blocked_reasons[0] if authority_validation_blocked_reasons else ""
        ),
        "authority_validation_blocked_reasons": authority_validation_blocked_reasons,
        "remote_github_blocked": remote_github_blocked,
        "remote_github_manual_required": remote_github_manual_required,
        "remote_github_missing_or_ambiguous": remote_github_missing_or_ambiguous,
        "remote_github_blocked_reason": (
            remote_github_blocked_reasons[0] if remote_github_blocked_reasons else ""
        ),
        "remote_github_blocked_reasons": remote_github_blocked_reasons,
    }


def _augment_run_state_with_closed_loop(
    *,
    run_state_payload: Mapping[str, Any],
    manifest_units: list[Mapping[str, Any]],
    run_status: str,
) -> dict[str, Any]:
    # Closed-loop next-step selection is derived from persisted unit/run artifacts
    # so resume/pause/manual/terminal behavior stays deterministic and inspectable.
    loop_surface = _resolve_closed_loop_orchestration(
        run_state_payload=run_state_payload,
        manifest_units=manifest_units,
        run_status=run_status,
    )
    return {
        **dict(run_state_payload),
        **loop_surface,
    }


def _augment_run_state_with_objective_contract_summary(
    *,
    run_state_payload: Mapping[str, Any],
    objective_contract_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    objective_surface = build_objective_run_state_summary_surface(objective_contract_payload)
    return {
        **payload,
        **objective_surface,
    }


def _augment_run_state_with_completion_contract_summary(
    *,
    run_state_payload: Mapping[str, Any],
    completion_contract_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    completion_surface = build_completion_run_state_summary_surface(completion_contract_payload)
    return {
        **payload,
        **completion_surface,
    }


def _augment_run_state_with_approval_transport_summary(
    *,
    run_state_payload: Mapping[str, Any],
    approval_transport_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    approval_surface = build_approval_run_state_summary_surface(approval_transport_payload)
    return {
        **payload,
        **approval_surface,
    }


def _augment_run_state_with_reconcile_contract_summary(
    *,
    run_state_payload: Mapping[str, Any],
    reconcile_contract_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    reconcile_surface = build_reconcile_run_state_summary_surface(reconcile_contract_payload)
    return {
        **payload,
        **reconcile_surface,
    }


def _augment_run_state_with_repair_suggestion_contract_summary(
    *,
    run_state_payload: Mapping[str, Any],
    repair_suggestion_contract_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    repair_surface = build_repair_suggestion_run_state_summary_surface(
        repair_suggestion_contract_payload
    )
    return {
        **payload,
        **repair_surface,
    }


def _augment_run_state_with_repair_plan_transport_summary(
    *,
    run_state_payload: Mapping[str, Any],
    repair_plan_transport_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    repair_plan_surface = build_repair_plan_transport_run_state_summary_surface(
        repair_plan_transport_payload
    )
    return {
        **payload,
        **repair_plan_surface,
    }


def _augment_run_state_with_repair_approval_binding_summary(
    *,
    run_state_payload: Mapping[str, Any],
    repair_approval_binding_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    binding_surface = build_repair_approval_binding_run_state_summary_surface(
        repair_approval_binding_payload
    )
    return {
        **payload,
        **binding_surface,
    }


def _augment_run_state_with_execution_authorization_gate_summary(
    *,
    run_state_payload: Mapping[str, Any],
    execution_authorization_gate_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    execution_authorization_surface = build_execution_authorization_gate_run_state_summary_surface(
        execution_authorization_gate_payload
    )
    return {
        **payload,
        **execution_authorization_surface,
    }


def _augment_run_state_with_bounded_execution_bridge_summary(
    *,
    run_state_payload: Mapping[str, Any],
    bounded_execution_bridge_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    bounded_execution_surface = build_bounded_execution_bridge_run_state_summary_surface(
        bounded_execution_bridge_payload
    )
    return {
        **payload,
        **bounded_execution_surface,
    }


def _augment_run_state_with_execution_result_contract_summary(
    *,
    run_state_payload: Mapping[str, Any],
    execution_result_contract_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    execution_result_surface = build_execution_result_contract_run_state_summary_surface(
        execution_result_contract_payload
    )
    return {
        **payload,
        **execution_result_surface,
    }


def _augment_run_state_with_verification_closure_contract_summary(
    *,
    run_state_payload: Mapping[str, Any],
    verification_closure_contract_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    verification_closure_surface = build_verification_closure_run_state_summary_surface(
        verification_closure_contract_payload
    )
    return {
        **payload,
        **verification_closure_surface,
    }


def _augment_run_state_with_retry_reentry_loop_contract_summary(
    *,
    run_state_payload: Mapping[str, Any],
    retry_reentry_loop_contract_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    retry_reentry_surface = build_retry_reentry_loop_run_state_summary_surface(
        retry_reentry_loop_contract_payload
    )
    return {
        **payload,
        **retry_reentry_surface,
    }


def _augment_run_state_with_endgame_closure_contract_summary(
    *,
    run_state_payload: Mapping[str, Any],
    endgame_closure_contract_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    endgame_surface = build_endgame_closure_run_state_summary_surface(
        endgame_closure_contract_payload
    )
    return {
        **payload,
        **endgame_surface,
    }


def _augment_run_state_with_loop_hardening_contract_summary(
    *,
    run_state_payload: Mapping[str, Any],
    loop_hardening_contract_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    loop_hardening_surface = build_loop_hardening_run_state_summary_surface(
        loop_hardening_contract_payload
    )
    return {
        **payload,
        **loop_hardening_surface,
    }


def _augment_run_state_with_lane_stabilization_contract_summary(
    *,
    run_state_payload: Mapping[str, Any],
    lane_stabilization_contract_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    lane_stabilization_surface = build_lane_stabilization_run_state_summary_surface(
        lane_stabilization_contract_payload
    )
    return {
        **payload,
        **lane_stabilization_surface,
    }


def _augment_run_state_with_observability_rollup_summary(
    *,
    run_state_payload: Mapping[str, Any],
    observability_rollup_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    observability_surface = build_observability_rollup_run_state_summary_surface(
        observability_rollup_payload
    )
    return {
        **payload,
        **observability_surface,
    }


def _augment_run_state_with_failure_bucketing_hardening_summary(
    *,
    run_state_payload: Mapping[str, Any],
    failure_bucketing_hardening_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    hardening_surface = build_failure_bucketing_hardening_run_state_summary_surface(
        failure_bucketing_hardening_payload
    )
    return {
        **payload,
        **hardening_surface,
    }


def _augment_run_state_with_artifact_retention_summary(
    *,
    run_state_payload: Mapping[str, Any],
    artifact_retention_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    retention_surface = build_artifact_retention_run_state_summary_surface(
        artifact_retention_payload
    )
    return {
        **payload,
        **retention_surface,
    }


def _augment_run_state_with_fleet_safety_control_summary(
    *,
    run_state_payload: Mapping[str, Any],
    fleet_safety_control_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    fleet_safety_surface = build_fleet_safety_control_run_state_summary_surface(
        fleet_safety_control_payload
    )
    return {
        **payload,
        **fleet_safety_surface,
    }


def _augment_run_state_with_approval_email_delivery_summary(
    *,
    run_state_payload: Mapping[str, Any],
    approval_email_delivery_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    approval_email_surface = build_approval_email_delivery_run_state_summary_surface(
        approval_email_delivery_payload
    )
    return {
        **payload,
        **approval_email_surface,
    }


def _augment_run_state_with_approval_runtime_rules_summary(
    *,
    run_state_payload: Mapping[str, Any],
    approval_runtime_rules_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    runtime_surface = build_approval_runtime_rules_run_state_summary_surface(
        approval_runtime_rules_payload
    )
    return {
        **payload,
        **runtime_surface,
    }


def _augment_run_state_with_approval_delivery_handoff_summary(
    *,
    run_state_payload: Mapping[str, Any],
    approval_delivery_handoff_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    handoff_surface = build_approval_delivery_handoff_run_state_summary_surface(
        approval_delivery_handoff_payload
    )
    return {
        **payload,
        **handoff_surface,
    }


def _augment_run_state_with_approval_response_summary(
    *,
    run_state_payload: Mapping[str, Any],
    approval_response_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    response_surface = build_approval_response_run_state_summary_surface(
        approval_response_payload
    )
    return {
        **payload,
        **response_surface,
    }


def _augment_run_state_with_approved_restart_summary(
    *,
    run_state_payload: Mapping[str, Any],
    approved_restart_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    restart_surface = build_approved_restart_run_state_summary_surface(
        approved_restart_payload
    )
    return {
        **payload,
        **restart_surface,
    }


def _augment_run_state_with_approval_safety_summary(
    *,
    run_state_payload: Mapping[str, Any],
    approval_safety_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    safety_surface = build_approval_safety_run_state_summary_surface(
        approval_safety_payload
    )
    return {
        **payload,
        **safety_surface,
    }


def _approval_delivery_noop_adapter(
    handoff_payload: Mapping[str, Any],
) -> Mapping[str, Any]:
    _ = handoff_payload
    return {
        "delivery_attempted": False,
        "delivery_outcome": "not_attempted",
        "delivery_metadata": {"adapter": "deferred_to_handoff_contract"},
    }


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


def _normalize_project_pr_slicing_reason_codes(
    reason_codes: list[str],
) -> list[str]:
    normalized = _serialize_required_signals(
        [
            reason
            for reason in reason_codes
            if reason in _PROJECT_PR_SLICING_REASON_CODES
        ]
    )
    ordered = [
        reason
        for reason in _PROJECT_PR_SLICING_REASON_ORDER
        if reason in normalized
    ]
    return ordered if ordered else ["pr_slices_insufficient_truth"]


def _build_project_roadmap_items(
    *,
    project_planning_summary_compact: Mapping[str, Any],
    planning_source_status: str,
) -> list[dict[str, Any]]:
    continuation_budget_status = _normalize_text(
        project_planning_summary_compact.get("continuation_budget_status"),
        default="unknown",
    )
    continuation_budget_branch_status = _normalize_text(
        project_planning_summary_compact.get("continuation_budget_branch_status"),
        default="unknown",
    )
    continuation_failure_bucket = _normalize_text(
        project_planning_summary_compact.get("continuation_failure_bucket"),
        default="unknown",
    )
    continuation_failure_bucket_denied = bool(
        project_planning_summary_compact.get("continuation_failure_bucket_denied", False)
    )
    continuation_next_step_selection_status = _normalize_text(
        project_planning_summary_compact.get("continuation_next_step_selection_status"),
        default="unknown",
    )
    continuation_next_step_target = _normalize_text(
        project_planning_summary_compact.get("continuation_next_step_target"),
        default="none",
    )
    supported_repair_execution_status = _normalize_text(
        project_planning_summary_compact.get("supported_repair_execution_status"),
        default="unknown",
    )
    final_human_review_required = bool(
        project_planning_summary_compact.get("final_human_review_required", False)
    )
    final_human_review_reason = _normalize_text(
        project_planning_summary_compact.get("final_human_review_reason"),
        default="final_review_not_required",
    )

    roadmap_items: list[dict[str, Any]] = [
        {
            "roadmap_item_id": "roadmap_continuation_budget",
            "topic_theme": "continuation_budget",
            "bounded_scope_class": "runner_only",
            "planning_source_status": planning_source_status,
            "blocked": continuation_budget_status != "available",
            "blocked_reason": (
                "budget_not_available"
                if continuation_budget_status != "available"
                else "none"
            ),
            "prerequisite_item_ids": [],
            "insufficient_reason": "",
        },
        {
            "roadmap_item_id": "roadmap_branch_ceiling",
            "topic_theme": "branch_ceiling",
            "bounded_scope_class": "runner_only",
            "planning_source_status": planning_source_status,
            "blocked": continuation_budget_branch_status != "available",
            "blocked_reason": (
                "branch_ceiling_not_available"
                if continuation_budget_branch_status != "available"
                else "none"
            ),
            "prerequisite_item_ids": [],
            "insufficient_reason": "",
        },
        {
            "roadmap_item_id": "roadmap_failure_bucket_gate",
            "topic_theme": "failure_bucket_gate",
            "bounded_scope_class": "runner_only",
            "planning_source_status": planning_source_status,
            "blocked": continuation_failure_bucket_denied,
            "blocked_reason": (
                f"failure_bucket_denied:{continuation_failure_bucket}"
                if continuation_failure_bucket_denied
                else "none"
            ),
            "prerequisite_item_ids": [],
            "insufficient_reason": "",
        },
        {
            "roadmap_item_id": "roadmap_next_step_selection",
            "topic_theme": "next_step_selection",
            "bounded_scope_class": "runner_and_tests",
            "planning_source_status": planning_source_status,
            "blocked": continuation_next_step_selection_status != "selected",
            "blocked_reason": (
                "next_step_not_selected"
                if continuation_next_step_selection_status != "selected"
                else "none"
            ),
            "prerequisite_item_ids": [],
            "insufficient_reason": "",
        },
        {
            "roadmap_item_id": "roadmap_supported_repair_posture",
            "topic_theme": "supported_repair_posture",
            "bounded_scope_class": "runner_and_tests",
            "planning_source_status": planning_source_status,
            "blocked": supported_repair_execution_status in {
                "executed_verification_failed",
                "not_executed_precheck_blocked",
                "not_executed_qualification_failed",
                "not_executed_launch_failed",
            },
            "blocked_reason": (
                f"supported_repair_status:{supported_repair_execution_status}"
                if supported_repair_execution_status
                not in {"", "not_selected", "executed_verification_passed"}
                else "none"
            ),
            "prerequisite_item_ids": [],
            "insufficient_reason": "",
        },
        {
            "roadmap_item_id": "roadmap_human_review_gate",
            "topic_theme": "human_review_gate",
            "bounded_scope_class": "runner_and_tests",
            "planning_source_status": planning_source_status,
            "blocked": final_human_review_required,
            "blocked_reason": (
                final_human_review_reason if final_human_review_required else "none"
            ),
            "prerequisite_item_ids": [],
            "insufficient_reason": "",
        },
    ]

    raw_blocked_by_id = {
        _normalize_text(item.get("roadmap_item_id"), default=""): bool(item.get("blocked", False))
        for item in roadmap_items
    }
    for item in roadmap_items:
        item_id = _normalize_text(item.get("roadmap_item_id"), default="")
        prerequisites = list(_PROJECT_ROADMAP_PREREQUISITES.get(item_id, ()))
        item["prerequisite_item_ids"] = prerequisites
        item["blocked"] = bool(
            item.get("blocked", False)
            or any(raw_blocked_by_id.get(prereq_id, False) for prereq_id in prerequisites)
        )
        if item["blocked"] and _normalize_text(item.get("blocked_reason"), default="none") == "none":
            item["blocked_reason"] = "blocked_by_prerequisite"

    ordered_items = sorted(
        roadmap_items,
        key=lambda item: (
            1 if bool(item.get("blocked", False)) else 0,
            _PROJECT_ROADMAP_SCOPE_CLASS_ORDER.get(
                _normalize_text(item.get("bounded_scope_class"), default="unknown"),
                _PROJECT_ROADMAP_SCOPE_CLASS_ORDER["unknown"],
            ),
            _PROJECT_ROADMAP_ITEM_ORDER.get(
                _normalize_text(item.get("roadmap_item_id"), default=""),
                len(_PROJECT_ROADMAP_ITEM_ORDER),
            ),
        ),
    )
    for index, item in enumerate(ordered_items, start=1):
        item["order"] = index
        item["priority"] = index
        item["priority_class"] = "blocked" if bool(item.get("blocked", False)) else "active"
    return ordered_items


def _build_project_pr_slices(
    roadmap_items: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if not roadmap_items:
        return []

    item_id_to_slice_id: dict[str, str] = {}
    slices: list[dict[str, Any]] = []
    for index, item in enumerate(roadmap_items, start=1):
        topic_theme = _normalize_text(item.get("topic_theme"), default="unknown")
        item_id = _normalize_text(item.get("roadmap_item_id"), default="")
        slice_id = f"slice_{index:02d}_{topic_theme}"
        item_id_to_slice_id[item_id] = slice_id
        slices.append(
            {
                "slice_id": slice_id,
                "order": index,
                "priority": _as_non_negative_int(item.get("priority"), default=index),
                "topic_theme": topic_theme,
                "roadmap_item_id": item_id,
                "bounded_scope_class": _normalize_text(
                    item.get("bounded_scope_class"),
                    default="unknown",
                ),
                "planning_source_status": _normalize_text(
                    item.get("planning_source_status"),
                    default="planning_summary_available",
                ),
                "blocked": bool(item.get("blocked", False)),
                "blocked_reason": _normalize_text(
                    item.get("blocked_reason"),
                    default="none",
                ),
                "one_pr_size_decision": "single_theme_single_pr",
                "insufficient_reason": _normalize_text(
                    item.get("insufficient_reason"),
                    default="",
                ),
                "prerequisite_slice_ids": [],
            }
        )
    for item, slice_entry in zip(roadmap_items, slices):
        prerequisite_ids = [
            item_id_to_slice_id[prereq_id]
            for prereq_id in item.get("prerequisite_item_ids", [])
            if prereq_id in item_id_to_slice_id
        ]
        slice_entry["prerequisite_slice_ids"] = prerequisite_ids
    return slices


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


def _build_implementation_prompt_payload(
    *,
    objective_id: str,
    project_planning_summary_status: str,
    project_pr_slicing_status: str,
    project_pr_one_pr_size_decision: str,
    project_pr_slices: list[Mapping[str, Any]],
) -> dict[str, Any]:
    prompt_status = "insufficient_truth"
    prompt_available = False
    prompt_reason = "prompt_planning_insufficient_truth"

    selected_slice: Mapping[str, Any] = {}
    if project_planning_summary_status != "available":
        prompt_reason = "prompt_planning_insufficient_truth"
    elif project_pr_slicing_status != "available":
        prompt_reason = "prompt_slice_state_insufficient_truth"
    elif project_pr_one_pr_size_decision != "single_theme_single_pr":
        prompt_reason = "prompt_size_posture_unbounded"
    elif not project_pr_slices:
        prompt_reason = "prompt_slice_missing"
    else:
        prompt_status = "available"
        prompt_available = True
        prompt_reason = "prompt_compiled"
        selected_slice = min(
            project_pr_slices,
            key=lambda item: (
                _as_non_negative_int(item.get("order"), default=0),
                _normalize_text(item.get("slice_id"), default=""),
            ),
        )

    prompt_reason_codes = _normalize_implementation_prompt_reason_codes([prompt_reason])
    slice_id = _normalize_text(selected_slice.get("slice_id"), default="")
    roadmap_item_id = _normalize_text(selected_slice.get("roadmap_item_id"), default="")
    topic_theme = _normalize_text(selected_slice.get("topic_theme"), default="unknown")
    bounded_scope_class = _normalize_text(
        selected_slice.get("bounded_scope_class"),
        default="unknown",
    )
    objective_or_theme = (
        f"{objective_id}:{topic_theme}" if objective_id and topic_theme != "unknown" else topic_theme
    )
    in_scope = list(
        _IMPLEMENTATION_PROMPT_IN_SCOPE_BY_THEME.get(
            topic_theme,
            ("deterministic bounded slice implementation only",),
        )
    )
    return {
        "prompt_status": (
            prompt_status
            if prompt_status in _IMPLEMENTATION_PROMPT_STATUSES
            else "insufficient_truth"
        ),
        "prompt_available": bool(prompt_available),
        "prompt_reason": prompt_reason_codes[0],
        "prompt_reason_codes": prompt_reason_codes,
        "slice_id": slice_id,
        "roadmap_item_id": roadmap_item_id,
        "objective_or_theme": objective_or_theme,
        "bounded_scope_class": bounded_scope_class,
        "in_scope": in_scope if prompt_available else [],
        "out_of_scope": (
            list(_IMPLEMENTATION_PROMPT_DEFAULT_OUT_OF_SCOPE) if prompt_available else []
        ),
        "preferred_files": (
            list(_IMPLEMENTATION_PROMPT_DEFAULT_PREFERRED_FILES) if prompt_available else []
        ),
        "preserved_constraints_ref": (
            list(_IMPLEMENTATION_PROMPT_PRESERVED_CONSTRAINTS_REFS) if prompt_available else []
        ),
        "suggested_validation_targets": (
            ["uv run python -m unittest tests.test_planned_execution_runner -v"]
            if prompt_available
            else []
        ),
        "return_format": (
            [
                "1. exact files changed",
                "2. tests not run by instruction",
                "3. suggested validation targets",
                "4. out-of-scope changes explicitly avoided",
                "5. prior increments / accumulated execution history / current architecture constraints explicitly preserved",
                "6. prompt-generation rule explicitly preserved",
            ]
            if prompt_available
            else []
        ),
    }


def _normalize_project_pr_queue_reason_codes(
    reason_codes: list[str],
) -> list[str]:
    normalized = _serialize_required_signals(
        [
            reason
            for reason in reason_codes
            if reason in _PROJECT_PR_QUEUE_REASON_CODES
        ]
    )
    ordered = [
        reason
        for reason in _PROJECT_PR_QUEUE_REASON_ORDER
        if reason in normalized
    ]
    return ordered if ordered else ["queue_state_insufficient_truth"]


def _build_project_pr_queue_state(
    *,
    project_pr_slicing_status: str,
    project_pr_slices: list[Mapping[str, Any]],
    implementation_prompt_payload: Mapping[str, Any],
    prior_processed_slice_ids: list[str],
) -> dict[str, Any]:
    queue_status = "insufficient_truth"
    queue_reason = "queue_state_insufficient_truth"
    queue_items: list[dict[str, Any]] = []
    selected_item: dict[str, Any] = {}
    handoff_prepared = False
    handoff_payload: dict[str, Any] = {}
    processed_before = _serialize_required_signals(prior_processed_slice_ids)
    processed_set = set(processed_before)

    if project_pr_slicing_status == "available":
        ordered_slices = sorted(
            project_pr_slices,
            key=lambda item: (
                _as_non_negative_int(item.get("order"), default=0),
                _normalize_text(item.get("slice_id"), default=""),
            ),
        )
        for item in ordered_slices:
            slice_id = _normalize_text(item.get("slice_id"), default="")
            blocked = bool(item.get("blocked", False))
            processed = bool(slice_id and slice_id in processed_set)
            runnable = bool(slice_id and not blocked and not processed)
            blocked_reason = _normalize_text(item.get("blocked_reason"), default="")
            if processed and not blocked_reason:
                blocked_reason = "already_prepared"
            queue_items.append(
                {
                    "slice_id": slice_id,
                    "roadmap_item_id": _normalize_text(item.get("roadmap_item_id"), default=""),
                    "order": _as_non_negative_int(item.get("order"), default=0),
                    "blocked": blocked,
                    "processed": processed,
                    "runnable": runnable,
                    "blocked_reason": blocked_reason,
                }
            )

        if not queue_items:
            queue_status = "empty"
            queue_reason = "queue_empty"
        else:
            runnable_items = [item for item in queue_items if bool(item.get("runnable", False))]
            if not runnable_items:
                if any(bool(item.get("processed", False)) for item in queue_items):
                    queue_status = "empty"
                    queue_reason = "queue_empty"
                else:
                    queue_status = "blocked"
                    queue_reason = "queue_item_blocked"
                    selected_item = dict(queue_items[0])
            else:
                selected_item = dict(runnable_items[0])
                prompt_available = bool(implementation_prompt_payload.get("prompt_available", False))
                prompt_slice_id = _normalize_text(
                    implementation_prompt_payload.get("slice_id"),
                    default="",
                )
                selected_slice_id = _normalize_text(selected_item.get("slice_id"), default="")
                if prompt_available and prompt_slice_id == selected_slice_id:
                    queue_status = "prepared"
                    queue_reason = "queue_item_prepared"
                    handoff_prepared = True
                    handoff_payload = {
                        "slice_id": selected_slice_id,
                        "roadmap_item_id": _normalize_text(
                            selected_item.get("roadmap_item_id"),
                            default="",
                        ),
                        "order": _as_non_negative_int(
                            selected_item.get("order"),
                            default=0,
                        ),
                        "implementation_prompt_payload": dict(implementation_prompt_payload),
                    }
                else:
                    queue_status = "blocked"
                    queue_reason = "prompt_unavailable_for_selected_slice"

    queue_reason_codes = _normalize_project_pr_queue_reason_codes([queue_reason])
    selected_slice_id = _normalize_text(selected_item.get("slice_id"), default="")
    processed_after = processed_before
    if handoff_prepared and selected_slice_id:
        processed_after = _serialize_required_signals([*processed_before, selected_slice_id])
    runnable_count = sum(1 for item in queue_items if bool(item.get("runnable", False)))
    blocked_count = sum(
        1
        for item in queue_items
        if bool(item.get("blocked", False)) or bool(item.get("processed", False))
    )
    return {
        "queue_status": (
            queue_status if queue_status in _PROJECT_PR_QUEUE_STATUSES else "insufficient_truth"
        ),
        "queue_reason": queue_reason_codes[0],
        "queue_reason_codes": queue_reason_codes,
        "queue_item_count": len(queue_items),
        "queue_runnable_count": runnable_count,
        "queue_blocked_count": blocked_count,
        "queue_selected_slice_id": selected_slice_id,
        "queue_selected_roadmap_item_id": _normalize_text(
            selected_item.get("roadmap_item_id"),
            default="",
        ),
        "queue_selected_blocked": bool(selected_item.get("blocked", False)),
        "queue_handoff_prepared": bool(handoff_prepared),
        "queue_handoff_payload": handoff_payload,
        "queue_items": queue_items,
        "queue_processed_slice_ids_before": processed_before,
        "queue_processed_slice_ids_after": processed_after,
    }


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


def _build_review_assimilation_state(
    *,
    queue_status: str,
    queue_reason: str,
    queue_handoff_prepared: bool,
    queue_handoff_payload: Mapping[str, Any] | None,
    restart_result_status: str,
    continuation_next_step_target: str,
    continuation_next_step_reason: str,
    continuation_next_step_truth_insufficiency_explicit: bool,
    final_human_review_required: bool,
    final_human_review_reason: str,
) -> dict[str, Any]:
    normalized_queue_status = _normalize_text(queue_status, default="insufficient_truth")
    normalized_queue_reason = _normalize_text(queue_reason, default="")
    normalized_result_status = _normalize_text(restart_result_status, default="not_attempted")
    normalized_next_step_target = _normalize_text(continuation_next_step_target, default="none")
    normalized_next_step_reason = _normalize_text(continuation_next_step_reason, default="")
    normalized_final_review_reason = _normalize_text(final_human_review_reason, default="")
    handoff_payload_map = (
        dict(queue_handoff_payload)
        if isinstance(queue_handoff_payload, Mapping)
        else {}
    )
    handoff_slice_id = _normalize_text(handoff_payload_map.get("slice_id"), default="")
    handoff_roadmap_item_id = _normalize_text(
        handoff_payload_map.get("roadmap_item_id"),
        default="",
    )

    assimilation_status = "insufficient_truth"
    assimilation_action = "none"
    assimilation_reason = "assimilation_result_insufficient_truth"
    reviewable = False

    if normalized_queue_status == "insufficient_truth":
        assimilation_status = "insufficient_truth"
        assimilation_reason = "assimilation_queue_state_insufficient_truth"
    elif normalized_queue_status == "empty":
        assimilation_status = "no_action"
        assimilation_reason = "assimilation_queue_empty"
    elif normalized_queue_status == "blocked":
        assimilation_status = "no_action"
        assimilation_reason = (
            "assimilation_prompt_unavailable"
            if normalized_queue_reason == "prompt_unavailable_for_selected_slice"
            else "assimilation_queue_blocked"
        )
    elif normalized_queue_status != "prepared":
        assimilation_status = "insufficient_truth"
        assimilation_reason = "assimilation_queue_state_insufficient_truth"
    elif not queue_handoff_prepared:
        assimilation_status = "no_action"
        assimilation_reason = "assimilation_queue_blocked"
    else:
        reviewable = True
        if normalized_result_status in {"", "unknown", "not_attempted", "not_started", "running"}:
            assimilation_status = "insufficient_truth"
            assimilation_reason = "assimilation_result_insufficient_truth"
        elif final_human_review_required:
            assimilation_status = "assimilated"
            assimilation_action = "escalate"
            assimilation_reason = "assimilation_escalate_manual_followup"
        elif normalized_result_status == "completed":
            assimilation_status = "assimilated"
            assimilation_action = "accept"
            assimilation_reason = "assimilation_accept_succeeded"
        elif normalized_result_status in {"failed", "timed_out"}:
            assimilation_status = "assimilated"
            if normalized_next_step_target == "replan" or normalized_next_step_reason == "next_step_selected_replan":
                assimilation_action = "replan"
                assimilation_reason = "assimilation_replan_design_invalid"
            elif (
                normalized_next_step_target == "truth_gather"
                or continuation_next_step_truth_insufficiency_explicit
            ):
                assimilation_action = "split"
                assimilation_reason = "assimilation_split_scope_signal"
            elif normalized_next_step_target in {"retry", "supported_repair"}:
                assimilation_action = "retry"
                assimilation_reason = "assimilation_retry_retryable_failure"
            elif (
                normalized_final_review_reason
                and normalized_final_review_reason != "final_review_not_required"
            ):
                assimilation_action = "escalate"
                assimilation_reason = "assimilation_escalate_manual_followup"
            else:
                assimilation_action = "escalate"
                assimilation_reason = "assimilation_escalate_unclassified"
        else:
            assimilation_status = "insufficient_truth"
            assimilation_reason = "assimilation_result_insufficient_truth"

    assimilation_reason_codes = _normalize_review_assimilation_reason_codes([assimilation_reason])
    if assimilation_status not in _REVIEW_ASSIMILATION_STATUSES:
        assimilation_status = "insufficient_truth"
    if assimilation_action not in _REVIEW_ASSIMILATION_ACTIONS:
        assimilation_action = "none"
    return {
        "review_assimilation_status": assimilation_status,
        "review_assimilation_action": assimilation_action,
        "review_assimilation_reason": assimilation_reason_codes[0],
        "review_assimilation_reason_codes": assimilation_reason_codes,
        "review_assimilation_available": bool(
            assimilation_status == "assimilated" and assimilation_action != "none"
        ),
        "review_assimilation_reviewable": bool(reviewable),
        "review_assimilation_queue_status": normalized_queue_status,
        "review_assimilation_queue_reason": normalized_queue_reason,
        "review_assimilation_result_status": normalized_result_status,
        "review_assimilation_handoff_slice_id": handoff_slice_id,
        "review_assimilation_handoff_roadmap_item_id": handoff_roadmap_item_id,
    }


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


def _build_bounded_self_healing_state(
    *,
    review_assimilation_status: str,
    review_assimilation_action: str,
    review_assimilation_available: bool,
    review_assimilation_reviewable: bool,
    review_assimilation_queue_status: str,
    continuation_next_step_truth_insufficiency_explicit: bool,
    supported_repair_execution_status: str,
    continuation_repair_playbook_selected: bool,
    continuation_repair_playbook_class: str,
    continuation_repair_playbook_candidate_action: str,
    final_human_review_required: bool,
    final_human_review_reason: str,
    continuation_budget_status: str,
    continuation_branch_budget_status: str,
    continuation_no_progress_stop_required: bool,
    continuation_failure_bucket_denied: bool,
    safety_duplicate_pending: bool,
    safety_cooldown_active: bool,
    safety_loop_suspected: bool,
    safety_delivery_blocked: bool,
    safety_delivery_deferred: bool,
    prior_self_healing_transition_count: int,
    self_healing_chain_limit: int,
    prior_continuation_retry_count: int,
    prior_continuation_replan_count: int,
    prior_continuation_truth_gather_count: int,
    continuation_retry_limit: int,
    continuation_replan_limit: int,
    continuation_truth_gather_limit: int,
) -> dict[str, Any]:
    assimilation_status = _normalize_text(
        review_assimilation_status,
        default="insufficient_truth",
    )
    assimilation_action = _normalize_text(
        review_assimilation_action,
        default="none",
    )
    queue_status = _normalize_text(
        review_assimilation_queue_status,
        default="insufficient_truth",
    )
    continuation_budget_status = _normalize_text(
        continuation_budget_status,
        default="insufficient_truth",
    )
    continuation_branch_budget_status = _normalize_text(
        continuation_branch_budget_status,
        default="not_applicable",
    )
    final_human_review_reason = _normalize_text(
        final_human_review_reason,
        default="",
    )

    transition_target = "none"
    transition_selected = False
    transition_executed = False
    transition_allowed = False
    self_healing_status = "insufficient_truth"
    self_healing_reason = "self_healing_insufficient_assimilation_truth"

    chain_limit = max(0, _as_non_negative_int(self_healing_chain_limit, default=0))
    transition_count_before = _as_non_negative_int(
        prior_self_healing_transition_count,
        default=0,
    )
    chain_budget_remaining_before = max(0, chain_limit - transition_count_before)

    assimilation_unavailable = bool(
        assimilation_status in {"insufficient_truth", ""}
        or not review_assimilation_reviewable
        or queue_status in {"insufficient_truth", "blocked", "empty"}
    )
    if assimilation_unavailable and assimilation_status == "insufficient_truth":
        self_healing_status = "insufficient_truth"
        self_healing_reason = "self_healing_insufficient_assimilation_truth"
    elif assimilation_status == "no_action" or assimilation_action == "none":
        self_healing_status = "not_applicable"
        self_healing_reason = (
            "self_healing_not_applicable_assimilation_accept"
            if assimilation_action == "accept"
            else "self_healing_not_applicable_assimilation_no_action"
        )
    elif not review_assimilation_available:
        self_healing_status = "not_applicable"
        self_healing_reason = "self_healing_not_applicable_assimilation_no_action"
    elif queue_status != "prepared":
        self_healing_status = "blocked"
        self_healing_reason = "self_healing_blocked_queue_non_runnable"
    else:
        if assimilation_action == "retry":
            transition_target = "retry"
        elif assimilation_action == "replan":
            transition_target = "replan"
        elif assimilation_action == "split":
            transition_target = "truth_gather"
        elif assimilation_action == "escalate":
            alternative_supported_repair_allowed = bool(
                supported_repair_execution_status == "executed_verification_failed"
                and continuation_repair_playbook_selected
                and continuation_repair_playbook_class in _SUPPORTED_REPAIR_EXECUTABLE_PLAYBOOK_CLASSES
                and continuation_repair_playbook_candidate_action
                in _SUPPORTED_REPAIR_EXECUTABLE_CANDIDATE_ACTIONS
            )
            if alternative_supported_repair_allowed:
                transition_target = "alternative_supported_repair"
            else:
                self_healing_status = "blocked"
                self_healing_reason = "self_healing_blocked_alternative_repair_not_allowed"
        elif assimilation_action == "accept":
            self_healing_status = "not_applicable"
            self_healing_reason = "self_healing_not_applicable_assimilation_accept"
        else:
            self_healing_status = "blocked"
            self_healing_reason = "self_healing_blocked_unsupported_action"

        if transition_target != "none":
            transition_selected = True
            selected_reason_map = {
                "retry": "self_healing_selected_retry",
                "replan": "self_healing_selected_replan",
                "truth_gather": "self_healing_selected_truth_gather",
                "alternative_supported_repair": (
                    "self_healing_selected_alternative_supported_repair"
                ),
            }
            executed_reason_map = {
                "retry": "self_healing_executed_retry",
                "replan": "self_healing_executed_replan",
                "truth_gather": "self_healing_executed_truth_gather",
                "alternative_supported_repair": (
                    "self_healing_executed_alternative_supported_repair"
                ),
            }
            self_healing_status = "selected"
            self_healing_reason = selected_reason_map.get(
                transition_target,
                "self_healing_blocked_unsupported_action",
            )

            safety_gate_blocked = bool(
                continuation_budget_status != "available"
                or continuation_no_progress_stop_required
                or continuation_failure_bucket_denied
                or safety_duplicate_pending
                or safety_cooldown_active
                or safety_loop_suspected
                or safety_delivery_blocked
                or safety_delivery_deferred
            )
            branch_budget_exhausted = False
            if transition_target == "retry":
                branch_budget_exhausted = bool(
                    prior_continuation_retry_count >= continuation_retry_limit
                )
            elif transition_target == "replan":
                branch_budget_exhausted = bool(
                    prior_continuation_replan_count >= continuation_replan_limit
                )
            elif transition_target == "truth_gather":
                branch_budget_exhausted = bool(
                    prior_continuation_truth_gather_count
                    >= continuation_truth_gather_limit
                )
            if continuation_branch_budget_status == "exhausted":
                branch_budget_exhausted = True

            allow_despite_final_review = bool(
                transition_target == "alternative_supported_repair"
                and final_human_review_reason
                == "final_review_supported_repair_verification_failed"
            )
            final_human_blocked = bool(
                final_human_review_required and not allow_despite_final_review
            )

            if chain_budget_remaining_before <= 0:
                self_healing_status = "blocked"
                self_healing_reason = "self_healing_blocked_budget_exhausted"
            elif safety_gate_blocked:
                self_healing_status = "blocked"
                self_healing_reason = "self_healing_blocked_safety_gate"
            elif branch_budget_exhausted:
                self_healing_status = "blocked"
                self_healing_reason = "self_healing_blocked_branch_budget_exhausted"
            elif final_human_blocked:
                self_healing_status = "blocked"
                self_healing_reason = "self_healing_blocked_final_human_review"
            else:
                transition_allowed = True
                transition_executed = True
                self_healing_status = "executed"
                self_healing_reason = executed_reason_map.get(
                    transition_target,
                    "self_healing_blocked_unsupported_action",
                )

    transition_count_after = transition_count_before + (1 if transition_executed else 0)
    chain_budget_remaining_after = max(0, chain_limit - transition_count_after)
    self_healing_reason_codes = _normalize_self_healing_reason_codes([self_healing_reason])
    human_fallback_preserved = bool(
        self_healing_status in {"blocked", "insufficient_truth", "not_applicable"}
    )
    if self_healing_status not in _SELF_HEALING_STATUSES:
        self_healing_status = "insufficient_truth"
    if transition_target not in _SELF_HEALING_TRANSITION_TARGETS:
        transition_target = "none"
    return {
        "self_healing_status": self_healing_status,
        "self_healing_transition_selected": bool(transition_selected),
        "self_healing_transition_target": transition_target,
        "self_healing_transition_allowed": bool(transition_allowed),
        "self_healing_transition_executed": bool(transition_executed),
        "self_healing_reason": self_healing_reason_codes[0],
        "self_healing_reason_codes": self_healing_reason_codes,
        "self_healing_chain_limit": chain_limit,
        "self_healing_transition_count_before": transition_count_before,
        "self_healing_transition_count_after": transition_count_after,
        "self_healing_chain_budget_remaining_before": chain_budget_remaining_before,
        "self_healing_chain_budget_remaining_after": chain_budget_remaining_after,
        "self_healing_human_fallback_preserved": bool(human_fallback_preserved),
        "self_healing_source_assimilation_status": assimilation_status,
        "self_healing_source_assimilation_action": assimilation_action,
        "self_healing_truth_insufficiency_signal": bool(
            continuation_next_step_truth_insufficiency_explicit
        ),
    }


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


def _build_long_running_stability_state(
    *,
    objective_id: str,
    queue_status: str,
    queue_selected_slice_id: str,
    queue_handoff_prepared: bool,
    queue_processed_count: int,
    review_assimilation_status: str,
    review_assimilation_action: str,
    review_assimilation_available: bool,
    self_healing_status: str,
    self_healing_transition_target: str,
    self_healing_transition_executed: bool,
    self_healing_human_fallback_preserved: bool,
    self_healing_chain_budget_remaining_after: int,
    self_healing_transition_count_after: int,
    final_human_review_required: bool,
    automatic_restart_executed: bool,
    automatic_continuation_run_count: int,
    prior_long_running_replay_key: str,
    prior_long_running_progress_signature: str,
    prior_long_running_stale_cycle_count: int,
    prior_long_running_stuck_cycle_count: int,
    prior_long_running_watchdog_heartbeat_at: str,
    now: Callable[[], datetime],
) -> dict[str, Any]:
    now_dt = now()
    now_at = now_dt.isoformat(timespec="seconds")
    normalized_objective_id = _normalize_text(objective_id, default="")
    normalized_queue_status = _normalize_text(queue_status, default="insufficient_truth")
    normalized_selected_slice_id = _normalize_text(queue_selected_slice_id, default="")
    normalized_assimilation_status = _normalize_text(
        review_assimilation_status,
        default="insufficient_truth",
    )
    normalized_assimilation_action = _normalize_text(
        review_assimilation_action,
        default="none",
    )
    normalized_self_healing_status = _normalize_text(
        self_healing_status,
        default="insufficient_truth",
    )
    normalized_self_healing_target = _normalize_text(
        self_healing_transition_target,
        default="none",
    )
    queue_processed_count_value = _as_non_negative_int(queue_processed_count, default=0)
    run_count_value = _as_non_negative_int(automatic_continuation_run_count, default=0)
    self_healing_transition_count_value = _as_non_negative_int(
        self_healing_transition_count_after,
        default=0,
    )
    chain_budget_remaining = _as_non_negative_int(
        self_healing_chain_budget_remaining_after,
        default=0,
    )
    current_replay_key = "|".join(
        [
            normalized_objective_id,
            normalized_selected_slice_id,
            normalized_assimilation_status,
            normalized_assimilation_action,
            normalized_self_healing_status,
            normalized_self_healing_target,
        ]
    ).strip("|")
    progress_signature = "|".join(
        [
            str(run_count_value),
            str(queue_processed_count_value),
            str(self_healing_transition_count_value),
            "restart_executed" if automatic_restart_executed else "restart_not_executed",
            "self_healing_executed" if self_healing_transition_executed else "self_healing_not_executed",
        ]
    )
    prior_replay_key = _normalize_text(prior_long_running_replay_key, default="")
    prior_progress_signature = _normalize_text(
        prior_long_running_progress_signature,
        default="",
    )
    replay_key_unchanged = bool(
        current_replay_key and prior_replay_key and current_replay_key == prior_replay_key
    )
    progress_unchanged = bool(
        replay_key_unchanged
        and progress_signature
        and prior_progress_signature
        and progress_signature == prior_progress_signature
    )
    stale_cycle_count = (
        _as_non_negative_int(prior_long_running_stale_cycle_count, default=0) + 1
        if progress_unchanged
        else 0
    )
    stuck_cycle_count = (
        _as_non_negative_int(prior_long_running_stuck_cycle_count, default=0) + 1
        if progress_unchanged
        else 0
    )
    stale_after_seconds = _LONG_RUNNING_STALE_AFTER_SECONDS_DEFAULT
    prior_heartbeat_dt = _parse_iso_timestamp(prior_long_running_watchdog_heartbeat_at)
    stale_age_seconds = 0
    if prior_heartbeat_dt is not None:
        comparable_now = now_dt
        if prior_heartbeat_dt.tzinfo is None and comparable_now.tzinfo is not None:
            prior_heartbeat_dt = prior_heartbeat_dt.replace(tzinfo=comparable_now.tzinfo)
        elif prior_heartbeat_dt.tzinfo is not None and comparable_now.tzinfo is None:
            comparable_now = comparable_now.replace(tzinfo=prior_heartbeat_dt.tzinfo)
        stale_age_seconds = max(
            0,
            int((comparable_now - prior_heartbeat_dt).total_seconds()),
        )
    stale_detected = bool(
        progress_unchanged
        and stale_age_seconds >= stale_after_seconds
    )
    stuck_detected = bool(
        progress_unchanged
        and stuck_cycle_count >= _LONG_RUNNING_STUCK_CYCLE_THRESHOLD_DEFAULT
    )

    status = "insufficient_truth"
    reason = "long_running_insufficient_truth_queue_state"
    pause_required = True
    resume_allowed = False
    escalation_required = False
    safe_stop_required = True
    watchdog_active = False

    if normalized_queue_status == "insufficient_truth":
        status = "insufficient_truth"
        reason = "long_running_insufficient_truth_queue_state"
    elif final_human_review_required:
        status = "escalated"
        reason = "long_running_escalated_final_human_review_required"
        escalation_required = True
    elif normalized_queue_status == "empty":
        status = "safe_stop"
        reason = "long_running_safe_stop_queue_empty"
    elif normalized_queue_status == "blocked":
        status = "safe_stop"
        reason = "long_running_safe_stop_queue_blocked"
    elif bool(self_healing_human_fallback_preserved):
        status = "safe_stop"
        reason = "long_running_safe_stop_human_fallback"
    elif chain_budget_remaining <= 0:
        status = "safe_stop"
        reason = "long_running_safe_stop_chain_budget_exhausted"
    elif stuck_detected:
        status = "escalated"
        reason = "long_running_escalated_stuck_detection"
        escalation_required = True
    elif stale_detected:
        status = "paused"
        reason = "long_running_paused_stale_watchdog"
        resume_allowed = bool(current_replay_key)
    elif (
        normalized_queue_status == "prepared"
        and queue_handoff_prepared
        and review_assimilation_available
    ):
        status = "monitoring"
        reason = "long_running_monitoring_active"
        pause_required = False
        safe_stop_required = False
        watchdog_active = True
    elif (
        normalized_queue_status == "prepared"
        and queue_handoff_prepared
        and current_replay_key
    ):
        status = "resume_ready"
        reason = "long_running_resume_ready_replay_safe"
        resume_allowed = True
        safe_stop_required = False
    else:
        status = "safe_stop"
        reason = "long_running_safe_stop_human_fallback"

    reason_codes = _normalize_long_running_reason_codes([reason])
    if status not in _LONG_RUNNING_STABILITY_STATUSES:
        status = "insufficient_truth"
    if status in {"monitoring"}:
        pause_required = False
    replay_safe = bool(current_replay_key and progress_signature)
    resume_token = (
        f"{current_replay_key}|{self_healing_transition_count_value}|{queue_processed_count_value}"
        if replay_safe
        else ""
    )
    return {
        "long_running_stability_status": status,
        "long_running_watchdog_active": bool(watchdog_active),
        "long_running_stale_detected": bool(stale_detected),
        "long_running_stuck_detected": bool(stuck_detected),
        "long_running_pause_required": bool(pause_required),
        "long_running_resume_allowed": bool(resume_allowed),
        "long_running_escalation_required": bool(escalation_required),
        "long_running_safe_stop_required": bool(safe_stop_required),
        "long_running_replay_safe": bool(replay_safe),
        "long_running_replay_key": current_replay_key,
        "long_running_progress_signature": progress_signature,
        "long_running_resume_token": resume_token,
        "long_running_watchdog_heartbeat_at": now_at,
        "long_running_watchdog_stale_after_seconds": stale_after_seconds,
        "long_running_watchdog_stale_age_seconds": stale_age_seconds,
        "long_running_stale_cycle_count": stale_cycle_count,
        "long_running_stuck_cycle_count": stuck_cycle_count,
        "long_running_reason": reason_codes[0],
        "long_running_reason_codes": reason_codes,
        "long_running_source_queue_status": normalized_queue_status,
        "long_running_source_review_assimilation_status": normalized_assimilation_status,
        "long_running_source_review_assimilation_action": normalized_assimilation_action,
        "long_running_source_self_healing_status": normalized_self_healing_status,
        "long_running_source_self_healing_target": normalized_self_healing_target,
    }


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


def _build_objective_done_compiler_state(
    *,
    objective_id: str,
    project_planning_summary_status: str,
    project_pr_slicing_status: str,
    project_pr_slice_count: int,
    project_pr_queue_status: str,
    project_pr_queue_reason: str,
    project_pr_queue_processed_slice_ids_after: list[str],
    review_assimilation_reason: str,
    self_healing_human_fallback_preserved: bool,
    long_running_stability_status: str,
    final_human_review_required: bool,
) -> dict[str, Any]:
    normalized_objective_id = _normalize_text(objective_id, default="")
    planning_status = _normalize_text(
        project_planning_summary_status,
        default="insufficient_truth",
    )
    slicing_status = _normalize_text(
        project_pr_slicing_status,
        default="insufficient_truth",
    )
    queue_status = _normalize_text(project_pr_queue_status, default="insufficient_truth")
    queue_reason = _normalize_text(project_pr_queue_reason, default="")
    assimilation_reason = _normalize_text(review_assimilation_reason, default="")
    long_running_status = _normalize_text(
        long_running_stability_status,
        default="insufficient_truth",
    )
    processed_slice_ids = _normalize_string_list(project_pr_queue_processed_slice_ids_after)
    processed_count = len(processed_slice_ids)
    slice_count = _as_non_negative_int(project_pr_slice_count, default=0)

    compiler_status = "insufficient_truth"
    compiler_reason = "objective_truth_insufficient"
    current_objective_available = False
    if not normalized_objective_id:
        compiler_status = "insufficient_truth"
        compiler_reason = "objective_identity_missing"
    elif planning_status != "available" and slicing_status != "available":
        compiler_status = "insufficient_truth"
        compiler_reason = "objective_truth_insufficient"
    else:
        compiler_status = "available"
        compiler_reason = "objective_compiled"
        current_objective_available = True

    scope_drift_status = "insufficient_truth"
    scope_drift_reason = "scope_drift_insufficient_truth"
    scope_drift_detected = False
    if slicing_status == "available":
        scope_drift_detected = bool(
            queue_reason == "prompt_unavailable_for_selected_slice"
            or assimilation_reason == "assimilation_split_scope_signal"
        )
        if scope_drift_detected:
            scope_drift_status = "detected"
            scope_drift_reason = (
                "scope_drift_detected_queue_prompt_mismatch"
                if queue_reason == "prompt_unavailable_for_selected_slice"
                else "scope_drift_detected_split_signal"
            )
        else:
            scope_drift_status = "clear"
            scope_drift_reason = "scope_drift_clear"

    done_status = "insufficient_truth"
    done_reason = "done_criteria_insufficient_truth"
    done_met = False
    done_remaining_count = 0
    if compiler_status == "available" and slicing_status == "available":
        done_remaining_count = max(0, slice_count - processed_count)
        done_met = bool(
            slice_count > 0
            and done_remaining_count == 0
            and queue_status == "empty"
        )
        done_status = "met" if done_met else "not_met"
        done_reason = "done_criteria_met" if done_met else "done_criteria_incomplete"

    stop_status = "insufficient_truth"
    stop_reason = "stop_criteria_insufficient_truth"
    stop_met = True
    if compiler_status == "available":
        stop_met = bool(
            final_human_review_required
            or long_running_status in {"safe_stop", "paused", "escalated"}
            or bool(self_healing_human_fallback_preserved)
        )
        stop_status = "stop" if stop_met else "continue"
        if not stop_met:
            stop_reason = "stop_criteria_continue"
        elif done_met:
            stop_reason = "stop_criteria_done_met"
        elif final_human_review_required:
            stop_reason = "stop_criteria_human_review_required"
        elif long_running_status in {"paused", "escalated"}:
            stop_reason = "stop_criteria_stability_pause_or_escalation"
        else:
            stop_reason = "stop_criteria_human_fallback_preserved"

    completion_posture = "objective_insufficient_truth"
    completion_reason = "completion_objective_insufficient_truth"
    if compiler_status != "available":
        completion_posture = "objective_insufficient_truth"
        completion_reason = "completion_objective_insufficient_truth"
    elif done_met and not scope_drift_detected:
        completion_posture = "objective_completed"
        completion_reason = "completion_objective_completed"
    elif stop_met and (
        final_human_review_required
        or queue_status == "blocked"
        or long_running_status in {"paused", "escalated"}
        or bool(self_healing_human_fallback_preserved)
    ):
        completion_posture = "objective_blocked"
        completion_reason = "completion_objective_blocked"
    else:
        completion_posture = "objective_active"
        completion_reason = "completion_objective_active"

    reason_codes = _normalize_objective_compiler_reason_codes(
        [
            compiler_reason,
            done_reason,
            scope_drift_reason,
            stop_reason,
            completion_reason,
        ]
    )
    if compiler_status not in _OBJECTIVE_COMPILER_STATUSES:
        compiler_status = "insufficient_truth"
    if done_status not in _OBJECTIVE_DONE_CRITERIA_STATUSES:
        done_status = "insufficient_truth"
    if stop_status not in _OBJECTIVE_STOP_CRITERIA_STATUSES:
        stop_status = "insufficient_truth"
    if completion_posture not in _OBJECTIVE_COMPLETION_POSTURES:
        completion_posture = "objective_insufficient_truth"
    if scope_drift_status not in _OBJECTIVE_SCOPE_DRIFT_STATUSES:
        scope_drift_status = "insufficient_truth"
    return {
        "objective_compiler_status": compiler_status,
        "objective_compiler_reason": reason_codes[0],
        "objective_compiler_reason_codes": reason_codes,
        "current_objective_id": normalized_objective_id,
        "current_objective_available": bool(current_objective_available),
        "objective_done_criteria_status": done_status,
        "objective_done_criteria_met": bool(done_met),
        "objective_done_remaining_slice_count": done_remaining_count,
        "objective_stop_criteria_status": stop_status,
        "objective_stop_criteria_met": bool(stop_met),
        "objective_completion_posture": completion_posture,
        "objective_scope_drift_status": scope_drift_status,
        "objective_scope_drift_detected": bool(scope_drift_detected),
        "objective_scope_drift_reason": scope_drift_reason,
        "objective_source_slice_count": slice_count,
        "objective_source_processed_count": processed_count,
        "objective_source_queue_status": queue_status,
    }


def _build_project_autonomy_budget_state(
    *,
    project_planning_summary_status: str,
    objective_compiler_status: str,
    objective_completion_posture: str,
    final_human_review_required: bool,
    high_risk_posture: bool,
    continuation_budget_truth_sufficient: bool,
    continuation_budget_status: str,
    continuation_budget_run_exhausted: bool,
    continuation_budget_objective_exhausted: bool,
    continuation_budget_run_limit: int,
    continuation_budget_objective_limit: int,
    continuation_budget_run_remaining: int,
    continuation_budget_objective_remaining: int,
    continuation_budget_branch_type: str,
    continuation_budget_branch_status: str,
    continuation_budget_branch_exhausted: bool,
    continuation_budget_branch_limit: int,
    continuation_budget_branch_remaining: int,
) -> dict[str, Any]:
    planning_status = _normalize_text(
        project_planning_summary_status,
        default="insufficient_truth",
    )
    objective_status = _normalize_text(
        objective_compiler_status,
        default="insufficient_truth",
    )
    completion_posture = _normalize_text(
        objective_completion_posture,
        default="objective_insufficient_truth",
    )
    budget_status = _normalize_text(
        continuation_budget_status,
        default="insufficient_truth",
    )
    branch_type = _normalize_text(continuation_budget_branch_type, default="unknown")
    branch_status = _normalize_text(
        continuation_budget_branch_status,
        default="insufficient_truth",
    )

    compiler_status = "insufficient_truth"
    priority_posture = "insufficient_truth"
    run_budget_posture = "insufficient_truth"
    objective_budget_posture = "insufficient_truth"
    pr_retry_budget_posture = "insufficient_truth"
    high_risk_defer_posture = "insufficient_truth"
    priority_deferred = False
    high_risk_defer_active = False
    pr_retry_budget_applicable = False
    pr_retry_budget_exhausted = False
    run_budget_exhausted = False
    objective_budget_exhausted = False

    reason_codes: list[str] = []
    truth_sufficient = bool(
        planning_status == "available"
        and objective_status == "available"
        and continuation_budget_truth_sufficient
        and budget_status in _CONTINUATION_BUDGET_STATUSES
    )
    if not truth_sufficient:
        reason_codes.extend(
            [
                "autonomy_budget_insufficient_truth",
                "project_priority_insufficient_truth",
                "run_budget_insufficient_truth",
                "objective_budget_insufficient_truth",
                "pr_retry_budget_insufficient_truth",
                "high_risk_defer_insufficient_truth",
            ]
        )
    else:
        compiler_status = "available"
        run_budget_exhausted = bool(continuation_budget_run_exhausted)
        objective_budget_exhausted = bool(continuation_budget_objective_exhausted)
        run_budget_posture = "exhausted" if run_budget_exhausted else "available"
        objective_budget_posture = (
            "exhausted" if objective_budget_exhausted else "available"
        )
        if branch_type == "retry":
            pr_retry_budget_applicable = True
            pr_retry_budget_exhausted = bool(continuation_budget_branch_exhausted)
            if branch_status in {"available", "exhausted"}:
                pr_retry_budget_posture = branch_status
            else:
                pr_retry_budget_posture = "insufficient_truth"
        else:
            pr_retry_budget_posture = "not_applicable"

        high_risk_defer_active = bool(
            high_risk_posture or final_human_review_required
        )
        high_risk_defer_posture = "defer" if high_risk_defer_active else "clear"
        priority_deferred = bool(
            high_risk_defer_active or completion_posture == "objective_blocked"
        )
        any_budget_exhausted = bool(
            run_budget_exhausted
            or objective_budget_exhausted
            or pr_retry_budget_exhausted
        )
        if completion_posture == "objective_completed":
            priority_posture = "completed"
        elif priority_deferred:
            priority_posture = "deferred"
        elif any_budget_exhausted:
            priority_posture = "lower_priority"
        else:
            priority_posture = "active"

        reason_codes.append("autonomy_budget_compiled")
        if priority_posture == "completed":
            reason_codes.append("project_priority_completed")
        elif priority_posture == "deferred":
            reason_codes.append(
                "project_priority_deferred_high_risk"
                if high_risk_defer_active
                else "project_priority_deferred_blocked"
            )
        elif priority_posture == "lower_priority":
            reason_codes.append("project_priority_lowered_budget_exhausted")
        else:
            reason_codes.append("project_priority_active")
        reason_codes.append(
            "run_budget_exhausted" if run_budget_exhausted else "run_budget_available"
        )
        reason_codes.append(
            "objective_budget_exhausted"
            if objective_budget_exhausted
            else "objective_budget_available"
        )
        if pr_retry_budget_posture == "available":
            reason_codes.append("pr_retry_budget_available")
        elif pr_retry_budget_posture == "exhausted":
            reason_codes.append("pr_retry_budget_exhausted")
        elif pr_retry_budget_posture == "not_applicable":
            reason_codes.append("pr_retry_budget_not_applicable")
        else:
            reason_codes.append("pr_retry_budget_insufficient_truth")
        reason_codes.append(
            "high_risk_defer_active"
            if high_risk_defer_active
            else "high_risk_defer_clear"
        )

    reason_codes = _normalize_project_autonomy_budget_reason_codes(reason_codes)
    if compiler_status not in _PROJECT_AUTONOMY_BUDGET_STATUSES:
        compiler_status = "insufficient_truth"
    if priority_posture not in _PROJECT_PRIORITY_POSTURES:
        priority_posture = "insufficient_truth"
    if run_budget_posture not in _PROJECT_BUDGET_POSTURES:
        run_budget_posture = "insufficient_truth"
    if objective_budget_posture not in _PROJECT_BUDGET_POSTURES:
        objective_budget_posture = "insufficient_truth"
    if pr_retry_budget_posture not in _PROJECT_PR_RETRY_BUDGET_POSTURES:
        pr_retry_budget_posture = "insufficient_truth"
    if high_risk_defer_posture not in _PROJECT_HIGH_RISK_DEFER_POSTURES:
        high_risk_defer_posture = "insufficient_truth"

    return {
        "project_autonomy_budget_status": compiler_status,
        "project_autonomy_budget_reason": reason_codes[0],
        "project_autonomy_budget_reason_codes": reason_codes,
        "project_priority_posture": priority_posture,
        "project_priority_deferred": bool(priority_deferred),
        "project_high_risk_defer_posture": high_risk_defer_posture,
        "project_high_risk_defer_active": bool(high_risk_defer_active),
        "project_run_budget_posture": run_budget_posture,
        "project_run_budget_limit": _as_non_negative_int(
            continuation_budget_run_limit,
            default=0,
        ),
        "project_run_budget_remaining": _as_non_negative_int(
            continuation_budget_run_remaining,
            default=0,
        ),
        "project_run_budget_exhausted": bool(run_budget_exhausted),
        "project_objective_budget_posture": objective_budget_posture,
        "project_objective_budget_limit": _as_non_negative_int(
            continuation_budget_objective_limit,
            default=0,
        ),
        "project_objective_budget_remaining": _as_non_negative_int(
            continuation_budget_objective_remaining,
            default=0,
        ),
        "project_objective_budget_exhausted": bool(objective_budget_exhausted),
        "project_pr_retry_budget_posture": pr_retry_budget_posture,
        "project_pr_retry_budget_applicable": bool(pr_retry_budget_applicable),
        "project_pr_retry_budget_limit": _as_non_negative_int(
            continuation_budget_branch_limit if branch_type == "retry" else 0,
            default=0,
        ),
        "project_pr_retry_budget_remaining": _as_non_negative_int(
            continuation_budget_branch_remaining if branch_type == "retry" else 0,
            default=0,
        ),
        "project_pr_retry_budget_exhausted": bool(pr_retry_budget_exhausted),
    }


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


def _build_project_quality_gate_state(
    *,
    project_planning_summary_status: str,
    project_pr_slicing_status: str,
    implementation_prompt_status: str,
    implementation_prompt_payload: Mapping[str, Any],
    project_pr_queue_status: str,
    review_assimilation_status: str,
    review_assimilation_action: str,
    self_healing_status: str,
    long_running_stability_status: str,
    objective_compiler_status: str,
    objective_completion_posture: str,
    objective_scope_drift_detected: bool,
    project_autonomy_budget_status: str,
    project_priority_posture: str,
    project_run_budget_posture: str,
    project_objective_budget_posture: str,
    project_pr_retry_budget_posture: str,
    project_high_risk_defer_posture: str,
    continuation_failure_bucket_denied: bool,
    continuation_no_progress_stop_required: bool,
    continuation_next_step_selection_status: str,
    continuation_next_step_target: str,
    supported_repair_execution_status: str,
    final_human_review_required: bool,
) -> dict[str, Any]:
    planning_status = _normalize_text(
        project_planning_summary_status,
        default="insufficient_truth",
    )
    slicing_status = _normalize_text(
        project_pr_slicing_status,
        default="insufficient_truth",
    )
    prompt_status = _normalize_text(
        implementation_prompt_status,
        default="insufficient_truth",
    )
    queue_status = _normalize_text(
        project_pr_queue_status,
        default="insufficient_truth",
    )
    assimilation_status = _normalize_text(
        review_assimilation_status,
        default="insufficient_truth",
    )
    assimilation_action = _normalize_text(review_assimilation_action, default="none")
    normalized_self_healing_status = _normalize_text(
        self_healing_status,
        default="insufficient_truth",
    )
    long_running_status = _normalize_text(
        long_running_stability_status,
        default="insufficient_truth",
    )
    objective_status = _normalize_text(
        objective_compiler_status,
        default="insufficient_truth",
    )
    completion_posture = _normalize_text(
        objective_completion_posture,
        default="objective_insufficient_truth",
    )
    autonomy_budget_status = _normalize_text(
        project_autonomy_budget_status,
        default="insufficient_truth",
    )
    priority_posture = _normalize_text(
        project_priority_posture,
        default="insufficient_truth",
    )
    run_budget_posture = _normalize_text(
        project_run_budget_posture,
        default="insufficient_truth",
    )
    objective_budget_posture = _normalize_text(
        project_objective_budget_posture,
        default="insufficient_truth",
    )
    pr_retry_budget_posture = _normalize_text(
        project_pr_retry_budget_posture,
        default="insufficient_truth",
    )
    high_risk_defer_posture = _normalize_text(
        project_high_risk_defer_posture,
        default="insufficient_truth",
    )
    next_step_selection_status = _normalize_text(
        continuation_next_step_selection_status,
        default="insufficient_truth",
    )
    next_step_target = _normalize_text(continuation_next_step_target, default="none")
    repair_status = _normalize_text(
        supported_repair_execution_status,
        default="not_selected",
    )

    prompt_payload = (
        dict(implementation_prompt_payload)
        if isinstance(implementation_prompt_payload, Mapping)
        else {}
    )
    preferred_files = [
        _normalize_text(path, default="")
        for path in prompt_payload.get("preferred_files", [])
        if isinstance(path, str)
    ]
    has_runner_files = any(
        path.startswith("automation/orchestration/") for path in preferred_files
    )
    has_test_files = any(path.startswith("tests/") for path in preferred_files)
    changed_area_class = "unknown"
    if has_runner_files and has_test_files:
        changed_area_class = "runner_and_tests"
    elif has_runner_files:
        changed_area_class = "runner_only"
    else:
        prompt_scope_class = _normalize_text(
            prompt_payload.get("bounded_scope_class"),
            default="unknown",
        )
        if prompt_scope_class in {"runner_and_tests", "runner_only"}:
            changed_area_class = prompt_scope_class
    if changed_area_class not in _PROJECT_QUALITY_GATE_CHANGED_AREA_CLASSES:
        changed_area_class = "unknown"

    truth_sufficient = bool(
        planning_status == "available"
        and slicing_status == "available"
        and prompt_status == "available"
        and queue_status in _PROJECT_PR_QUEUE_STATUSES
        and queue_status != "insufficient_truth"
        and objective_status == "available"
        and autonomy_budget_status == "available"
    )
    if not truth_sufficient:
        reason_codes = _normalize_project_quality_gate_reason_codes(
            [
                "quality_gate_insufficient_truth",
                "quality_gate_posture_insufficient_truth",
                "quality_gate_changed_area_insufficient_truth",
                "quality_gate_risk_insufficient_truth",
            ]
        )
        return {
            "project_quality_gate_status": "insufficient_truth",
            "project_quality_gate_reason": reason_codes[0],
            "project_quality_gate_reason_codes": reason_codes,
            "project_quality_gate_posture": "insufficient_truth",
            "project_quality_gate_merge_ready": False,
            "project_quality_gate_review_ready": False,
            "project_quality_gate_retry_needed": False,
            "project_quality_gate_recommended": [],
            "project_quality_gate_recommended_count": 0,
            "project_quality_gate_changed_area_class": "unknown",
            "project_quality_gate_risk_level": "insufficient_truth",
            "project_quality_gate_high_risk": False,
            "project_quality_gate_unavailable": True,
        }

    high_risk = bool(
        high_risk_defer_posture == "defer"
        or final_human_review_required
        or continuation_failure_bucket_denied
        or continuation_no_progress_stop_required
        or completion_posture == "objective_blocked"
        or long_running_status in {"paused", "escalated", "safe_stop"}
        or repair_status
        in {
            "executed_verification_failed",
            "not_executed_precheck_blocked",
            "not_executed_qualification_failed",
            "not_executed_launch_failed",
        }
    )
    retry_signal = bool(
        assimilation_action in {"retry", "replan", "split"}
        or (
            next_step_selection_status == "selected"
            and next_step_target in {"retry", "replan", "truth_gather", "supported_repair"}
        )
        or normalized_self_healing_status in {"selected", "executed"}
        or run_budget_posture == "exhausted"
        or objective_budget_posture == "exhausted"
        or pr_retry_budget_posture == "exhausted"
    )
    merge_ready = bool(
        completion_posture == "objective_completed"
        and assimilation_status == "assimilated"
        and assimilation_action == "accept"
        and queue_status == "empty"
        and not high_risk
        and not retry_signal
        and priority_posture not in {"deferred", "insufficient_truth"}
    )
    retry_needed = bool(not merge_ready and retry_signal)
    review_ready = bool(not merge_ready and not retry_needed)

    posture = "review_ready"
    if merge_ready:
        posture = "merge_ready"
    elif retry_needed:
        posture = "retry_needed"
    if posture not in _PROJECT_QUALITY_GATE_POSTURES:
        posture = "insufficient_truth"

    recommended = {"unit", "lint", "typecheck"}
    targeted_regression_required = bool(
        high_risk
        or retry_needed
        or changed_area_class == "runner_and_tests"
        or bool(objective_scope_drift_detected)
    )
    if targeted_regression_required:
        recommended.add("targeted_regression")
    ordered_gates = [
        gate
        for gate in ["unit", "targeted_regression", "lint", "typecheck"]
        if gate in recommended and gate in _PROJECT_QUALITY_GATE_NAMES
    ]

    risk_level = "low"
    if high_risk:
        risk_level = "high"
    elif retry_needed or bool(objective_scope_drift_detected):
        risk_level = "moderate"
    if risk_level not in _PROJECT_QUALITY_GATE_RISK_LEVELS:
        risk_level = "insufficient_truth"

    reason_codes = ["quality_gate_compiled"]
    if posture == "merge_ready":
        reason_codes.append("quality_gate_posture_merge_ready")
    elif posture == "retry_needed":
        reason_codes.append("quality_gate_posture_retry_needed")
    else:
        reason_codes.append("quality_gate_posture_review_ready")
    if changed_area_class == "runner_and_tests":
        reason_codes.append("quality_gate_changed_area_runner_and_tests")
    elif changed_area_class == "runner_only":
        reason_codes.append("quality_gate_changed_area_runner_only")
    else:
        reason_codes.append("quality_gate_changed_area_unknown")
    if risk_level == "high":
        reason_codes.append("quality_gate_risk_high")
    elif risk_level == "moderate":
        reason_codes.append("quality_gate_risk_moderate")
    else:
        reason_codes.append("quality_gate_risk_low")
    reason_codes.append(
        "quality_gate_targeted_regression_enabled"
        if targeted_regression_required
        else "quality_gate_targeted_regression_not_required"
    )
    reason_codes = _normalize_project_quality_gate_reason_codes(reason_codes)
    return {
        "project_quality_gate_status": "available",
        "project_quality_gate_reason": reason_codes[0],
        "project_quality_gate_reason_codes": reason_codes,
        "project_quality_gate_posture": posture,
        "project_quality_gate_merge_ready": bool(merge_ready),
        "project_quality_gate_review_ready": bool(review_ready),
        "project_quality_gate_retry_needed": bool(retry_needed),
        "project_quality_gate_recommended": ordered_gates,
        "project_quality_gate_recommended_count": len(ordered_gates),
        "project_quality_gate_changed_area_class": changed_area_class,
        "project_quality_gate_risk_level": risk_level,
        "project_quality_gate_high_risk": bool(high_risk),
        "project_quality_gate_unavailable": False,
    }


def _normalize_project_merge_branch_lifecycle_reason_codes(
    reason_codes: list[str],
) -> list[str]:
    normalized = _serialize_required_signals(
        [
            reason
            for reason in reason_codes
            if reason in _PROJECT_MERGE_BRANCH_LIFECYCLE_REASON_CODES
        ]
    )
    ordered = [
        reason
        for reason in _PROJECT_MERGE_BRANCH_LIFECYCLE_REASON_ORDER
        if reason in normalized
    ]
    return ordered if ordered else ["merge_branch_lifecycle_insufficient_truth"]


def _build_project_merge_branch_lifecycle_state(
    *,
    project_quality_gate_status: str,
    project_quality_gate_posture: str,
    project_quality_gate_merge_ready: bool,
    project_quality_gate_retry_needed: bool,
    project_quality_gate_high_risk: bool,
    objective_compiler_status: str,
    objective_completion_posture: str,
    project_autonomy_budget_status: str,
    project_priority_posture: str,
    project_high_risk_defer_posture: str,
    project_pr_queue_status: str,
    project_pr_queue_processed_count: int,
    review_assimilation_status: str,
    review_assimilation_action: str,
    self_healing_status: str,
    long_running_stability_status: str,
    final_human_review_required: bool,
    final_human_review_gate_status: str,
    continuation_failure_bucket_denied: bool,
    continuation_no_progress_stop_required: bool,
    supported_repair_execution_status: str,
) -> dict[str, Any]:
    quality_gate_status = _normalize_text(
        project_quality_gate_status,
        default="insufficient_truth",
    )
    quality_gate_posture = _normalize_text(
        project_quality_gate_posture,
        default="insufficient_truth",
    )
    objective_status = _normalize_text(
        objective_compiler_status,
        default="insufficient_truth",
    )
    completion_posture = _normalize_text(
        objective_completion_posture,
        default="objective_insufficient_truth",
    )
    autonomy_budget_status = _normalize_text(
        project_autonomy_budget_status,
        default="insufficient_truth",
    )
    priority_posture = _normalize_text(
        project_priority_posture,
        default="insufficient_truth",
    )
    high_risk_defer_posture = _normalize_text(
        project_high_risk_defer_posture,
        default="insufficient_truth",
    )
    queue_status = _normalize_text(
        project_pr_queue_status,
        default="insufficient_truth",
    )
    review_status = _normalize_text(
        review_assimilation_status,
        default="insufficient_truth",
    )
    review_action = _normalize_text(review_assimilation_action, default="none")
    normalized_self_healing_status = _normalize_text(
        self_healing_status,
        default="insufficient_truth",
    )
    long_running_status = _normalize_text(
        long_running_stability_status,
        default="insufficient_truth",
    )
    final_review_gate_status = _normalize_text(
        final_human_review_gate_status,
        default="not_required",
    )
    repair_status = _normalize_text(
        supported_repair_execution_status,
        default="not_selected",
    )
    processed_count = _as_non_negative_int(
        project_pr_queue_processed_count,
        default=0,
    )

    truth_sufficient = bool(
        quality_gate_status == "available"
        and quality_gate_posture in _PROJECT_QUALITY_GATE_POSTURES
        and quality_gate_posture != "insufficient_truth"
        and objective_status == "available"
        and completion_posture in _OBJECTIVE_COMPLETION_POSTURES
        and completion_posture != "objective_insufficient_truth"
        and autonomy_budget_status == "available"
        and queue_status in _PROJECT_PR_QUEUE_STATUSES
        and queue_status != "insufficient_truth"
    )
    if not truth_sufficient:
        reason_codes = _normalize_project_merge_branch_lifecycle_reason_codes(
            [
                "merge_branch_lifecycle_insufficient_truth",
                "merge_branch_posture_insufficient_truth",
                "merge_branch_cleanup_candidate_insufficient_truth",
                "merge_branch_quarantine_candidate_insufficient_truth",
                "merge_branch_local_main_sync_insufficient_truth",
            ]
        )
        return {
            "project_merge_branch_lifecycle_status": "insufficient_truth",
            "project_merge_branch_lifecycle_reason": reason_codes[0],
            "project_merge_branch_lifecycle_reason_codes": reason_codes,
            "project_merge_ready_posture": "insufficient_truth",
            "project_merge_ready": False,
            "project_branch_cleanup_candidate_posture": "insufficient_truth",
            "project_branch_cleanup_candidate": False,
            "project_branch_quarantine_candidate_posture": "insufficient_truth",
            "project_branch_quarantine_candidate": False,
            "project_local_main_sync_posture": "insufficient_truth",
            "project_local_main_sync_required": False,
            "project_merge_branch_lifecycle_unavailable": True,
        }

    quarantine_candidate = bool(
        final_human_review_required
        or final_review_gate_status == "required"
        or high_risk_defer_posture == "defer"
        or bool(project_quality_gate_high_risk)
        or continuation_failure_bucket_denied
        or continuation_no_progress_stop_required
        or completion_posture == "objective_blocked"
        or priority_posture == "deferred"
        or long_running_status in {"paused", "escalated", "safe_stop"}
        or repair_status
        in {
            "executed_verification_failed",
            "not_executed_precheck_blocked",
            "not_executed_qualification_failed",
            "not_executed_launch_failed",
        }
    )
    merge_ready = bool(
        not quarantine_candidate
        and quality_gate_posture == "merge_ready"
        and bool(project_quality_gate_merge_ready)
        and not bool(project_quality_gate_retry_needed)
        and completion_posture == "objective_completed"
        and review_status == "assimilated"
        and review_action == "accept"
        and queue_status == "empty"
        and normalized_self_healing_status in {"not_applicable", "not_selected", "executed"}
    )
    cleanup_candidate = bool(
        not quarantine_candidate
        and (
            merge_ready
            or (
                completion_posture == "objective_completed"
                and review_status == "assimilated"
                and review_action == "accept"
                and queue_status in {"empty", "blocked"}
            )
        )
    )
    local_main_sync_required = bool(
        queue_status in {"empty", "blocked"}
        and (
            merge_ready
            or cleanup_candidate
            or quarantine_candidate
            or priority_posture in {"deferred", "lower_priority"}
            or processed_count > 0
        )
    )

    merge_ready_posture = "merge_ready" if merge_ready else "not_merge_ready"
    cleanup_posture = "candidate" if cleanup_candidate else "not_candidate"
    quarantine_posture = "candidate" if quarantine_candidate else "not_candidate"
    sync_posture = "sync_required" if local_main_sync_required else "sync_not_required"

    reason_codes = ["merge_branch_lifecycle_compiled"]
    reason_codes.append(
        "merge_branch_posture_merge_ready"
        if merge_ready
        else "merge_branch_posture_not_merge_ready"
    )
    reason_codes.append(
        "merge_branch_cleanup_candidate_yes"
        if cleanup_candidate
        else "merge_branch_cleanup_candidate_no"
    )
    reason_codes.append(
        "merge_branch_quarantine_candidate_yes"
        if quarantine_candidate
        else "merge_branch_quarantine_candidate_no"
    )
    reason_codes.append(
        "merge_branch_local_main_sync_required"
        if local_main_sync_required
        else "merge_branch_local_main_sync_not_required"
    )
    reason_codes = _normalize_project_merge_branch_lifecycle_reason_codes(reason_codes)

    return {
        "project_merge_branch_lifecycle_status": "available",
        "project_merge_branch_lifecycle_reason": reason_codes[0],
        "project_merge_branch_lifecycle_reason_codes": reason_codes,
        "project_merge_ready_posture": merge_ready_posture,
        "project_merge_ready": bool(merge_ready),
        "project_branch_cleanup_candidate_posture": cleanup_posture,
        "project_branch_cleanup_candidate": bool(cleanup_candidate),
        "project_branch_quarantine_candidate_posture": quarantine_posture,
        "project_branch_quarantine_candidate": bool(quarantine_candidate),
        "project_local_main_sync_posture": sync_posture,
        "project_local_main_sync_required": bool(local_main_sync_required),
        "project_merge_branch_lifecycle_unavailable": False,
    }


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


def _build_project_failure_memory_state(
    *,
    project_merge_branch_lifecycle_status: str,
    project_branch_quarantine_candidate: bool,
    failure_bucketing_status: str,
    failure_bucketing_validity: str,
    failure_bucketing_primary_bucket: str,
    continuation_next_step_selection_status: str,
    continuation_next_step_target: str,
    continuation_no_progress_stop_required: bool,
    continuation_failure_bucket_denied: bool,
    review_assimilation_status: str,
    review_assimilation_action: str,
    self_healing_status: str,
    supported_repair_execution_status: str,
    execution_status: str,
    execution_reason: str,
    restart_result_status: str,
    final_human_review_required: bool,
    prior_retry_failure_count: int,
    prior_repair_failure_count: int,
    prior_review_issue_count: int,
    prior_failure_bucket_recurrence_count: int,
    prior_failure_bucket_value: str,
) -> dict[str, Any]:
    lifecycle_status = _normalize_text(
        project_merge_branch_lifecycle_status,
        default="insufficient_truth",
    )
    bucket_status = _normalize_text(
        failure_bucketing_status,
        default="insufficient_truth",
    )
    bucket_validity = _normalize_text(
        failure_bucketing_validity,
        default="insufficient_truth",
    )
    bucket_value = _normalize_text(
        failure_bucketing_primary_bucket,
        default="unknown",
    )
    next_step_status = _normalize_text(
        continuation_next_step_selection_status,
        default="insufficient_truth",
    )
    next_step_target = _normalize_text(
        continuation_next_step_target,
        default="none",
    )
    assimilation_status = _normalize_text(
        review_assimilation_status,
        default="insufficient_truth",
    )
    assimilation_action = _normalize_text(
        review_assimilation_action,
        default="none",
    )
    normalized_self_healing_status = _normalize_text(
        self_healing_status,
        default="insufficient_truth",
    )
    repair_status = _normalize_text(
        supported_repair_execution_status,
        default="not_selected",
    )
    normalized_execution_status = _normalize_text(
        execution_status,
        default="not_executed",
    )
    normalized_execution_reason = _normalize_text(
        execution_reason,
        default="restart_not_executed",
    )
    normalized_restart_result_status = _normalize_text(
        restart_result_status,
        default="not_attempted",
    )
    prior_bucket = _normalize_text(prior_failure_bucket_value, default="unknown")

    truth_sufficient = bool(
        lifecycle_status == "available"
        and bucket_status not in {"", "unknown", "insufficient_truth"}
        and bucket_validity in {"valid", "partial"}
        and next_step_status in {"selected", "not_selected"}
        and assimilation_status != "insufficient_truth"
        and normalized_self_healing_status != "insufficient_truth"
    )
    if not truth_sufficient:
        reason_codes = _normalize_project_failure_memory_reason_codes(
            [
                "failure_memory_insufficient_truth",
            ]
        )
        return {
            "project_failure_memory_status": "insufficient_truth",
            "project_failure_memory_reason": reason_codes[0],
            "project_failure_memory_reason_codes": reason_codes,
            "project_failure_memory_ineffective_retry": False,
            "project_failure_memory_failed_repair": False,
            "project_failure_memory_repeated_review_issue": False,
            "project_failure_memory_recurring_failure_bucket": False,
            "project_failure_memory_retry_failure_count": _as_non_negative_int(
                prior_retry_failure_count,
                default=0,
            ),
            "project_failure_memory_repair_failure_count": _as_non_negative_int(
                prior_repair_failure_count,
                default=0,
            ),
            "project_failure_memory_review_issue_count": _as_non_negative_int(
                prior_review_issue_count,
                default=0,
            ),
            "project_failure_memory_failure_bucket_recurrence_count": _as_non_negative_int(
                prior_failure_bucket_recurrence_count,
                default=0,
            ),
            "project_failure_memory_last_failure_bucket": bucket_value,
            "project_failure_memory_suppression_posture": "insufficient_truth",
            "project_failure_memory_suppression_active": False,
            "project_failure_memory_unavailable": True,
        }

    retry_failure_now = bool(
        next_step_target == "retry"
        and (
            continuation_no_progress_stop_required
            or normalized_execution_status != "executed"
            or normalized_restart_result_status not in {"completed", "not_attempted"}
            or normalized_execution_reason
            in {
                "continuation_budget_exhausted",
                "continuation_no_progress_stop",
                "failure_bucket_continuation_denied",
                "continuation_next_step_not_selected",
            }
        )
    )
    failed_repair_now = bool(
        repair_status
        in {
            "executed_verification_failed",
            "not_executed_precheck_blocked",
            "not_executed_qualification_failed",
            "not_executed_launch_failed",
        }
    )
    repeated_review_issue_now = bool(
        assimilation_status == "assimilated"
        and assimilation_action in {"retry", "replan", "split", "escalate"}
    )
    recurring_failure_bucket_now = bool(
        bucket_value not in {"", "unknown", "insufficient_truth"}
        and prior_bucket not in {"", "unknown", "insufficient_truth"}
        and bucket_value == prior_bucket
        and (
            _as_non_negative_int(prior_failure_bucket_recurrence_count, default=0) > 0
            or retry_failure_now
            or failed_repair_now
            or repeated_review_issue_now
            or bool(continuation_failure_bucket_denied)
        )
    )

    retry_failure_count = _as_non_negative_int(prior_retry_failure_count, default=0) + (
        1 if retry_failure_now else 0
    )
    repair_failure_count = _as_non_negative_int(prior_repair_failure_count, default=0) + (
        1 if failed_repair_now else 0
    )
    review_issue_count = _as_non_negative_int(prior_review_issue_count, default=0) + (
        1 if repeated_review_issue_now else 0
    )
    failure_bucket_recurrence_count = _as_non_negative_int(
        prior_failure_bucket_recurrence_count,
        default=0,
    ) + (1 if recurring_failure_bucket_now else 0)

    suppression_posture = "none"
    suppression_active = False
    if final_human_review_required and bool(project_branch_quarantine_candidate):
        if failure_bucket_recurrence_count >= 2:
            suppression_posture = "suppress_failure_bucket"
            suppression_active = True
        elif review_issue_count >= 2:
            suppression_posture = "suppress_review_issue"
            suppression_active = True
        elif repair_failure_count >= 2:
            suppression_posture = "suppress_repair"
            suppression_active = True
        elif retry_failure_count >= 2:
            suppression_posture = "suppress_retry"
            suppression_active = True
    elif failure_bucket_recurrence_count >= 3:
        suppression_posture = "suppress_failure_bucket"
        suppression_active = True
    elif review_issue_count >= 3:
        suppression_posture = "suppress_review_issue"
        suppression_active = True
    elif repair_failure_count >= 3:
        suppression_posture = "suppress_repair"
        suppression_active = True
    elif retry_failure_count >= 3:
        suppression_posture = "suppress_retry"
        suppression_active = True
    if suppression_posture not in _PROJECT_FAILURE_MEMORY_SUPPRESSION_POSTURES:
        suppression_posture = "insufficient_truth"
        suppression_active = False

    reason_codes = ["failure_memory_compiled"]
    reason_codes.append(
        "failure_memory_ineffective_retry_detected"
        if retry_failure_now
        else "failure_memory_no_ineffective_retry"
    )
    reason_codes.append(
        "failure_memory_failed_repair_detected"
        if failed_repair_now
        else "failure_memory_no_failed_repair"
    )
    reason_codes.append(
        "failure_memory_repeated_review_issue_detected"
        if repeated_review_issue_now
        else "failure_memory_no_repeated_review_issue"
    )
    reason_codes.append(
        "failure_memory_recurring_failure_bucket_detected"
        if recurring_failure_bucket_now
        else "failure_memory_no_recurring_failure_bucket"
    )
    if suppression_posture == "suppress_failure_bucket":
        reason_codes.append("failure_memory_suppression_failure_bucket")
    elif suppression_posture == "suppress_review_issue":
        reason_codes.append("failure_memory_suppression_review_issue")
    elif suppression_posture == "suppress_repair":
        reason_codes.append("failure_memory_suppression_repair")
    elif suppression_posture == "suppress_retry":
        reason_codes.append("failure_memory_suppression_retry")
    else:
        reason_codes.append("failure_memory_suppression_none")
    reason_codes = _normalize_project_failure_memory_reason_codes(reason_codes)

    return {
        "project_failure_memory_status": "available",
        "project_failure_memory_reason": reason_codes[0],
        "project_failure_memory_reason_codes": reason_codes,
        "project_failure_memory_ineffective_retry": bool(retry_failure_now),
        "project_failure_memory_failed_repair": bool(failed_repair_now),
        "project_failure_memory_repeated_review_issue": bool(repeated_review_issue_now),
        "project_failure_memory_recurring_failure_bucket": bool(
            recurring_failure_bucket_now
        ),
        "project_failure_memory_retry_failure_count": retry_failure_count,
        "project_failure_memory_repair_failure_count": repair_failure_count,
        "project_failure_memory_review_issue_count": review_issue_count,
        "project_failure_memory_failure_bucket_recurrence_count": (
            failure_bucket_recurrence_count
        ),
        "project_failure_memory_last_failure_bucket": bucket_value,
        "project_failure_memory_suppression_posture": suppression_posture,
        "project_failure_memory_suppression_active": bool(suppression_active),
        "project_failure_memory_unavailable": False,
    }


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


def _build_project_external_boundary_state(
    *,
    project_failure_memory_status: str,
    project_failure_memory_suppression_posture: str,
    project_failure_memory_suppression_active: bool,
    project_merge_branch_lifecycle_status: str,
    project_merge_ready_posture: str,
    project_branch_quarantine_candidate_posture: str,
    project_local_main_sync_posture: str,
    project_quality_gate_status: str,
    project_quality_gate_posture: str,
    project_quality_gate_risk_level: str,
    project_pr_queue_status: str,
    project_autonomy_budget_status: str,
    project_priority_posture: str,
    long_running_stability_status: str,
    supported_repair_execution_status: str,
    execution_reason: str,
    final_human_review_required: bool,
    final_human_review_gate_status: str,
    manual_only_posture_active: bool,
    fleet_manual_review_required: bool,
    approval_reason_class: str,
) -> dict[str, Any]:
    failure_memory_status = _normalize_text(
        project_failure_memory_status,
        default="insufficient_truth",
    )
    suppression_posture = _normalize_text(
        project_failure_memory_suppression_posture,
        default="insufficient_truth",
    )
    lifecycle_status = _normalize_text(
        project_merge_branch_lifecycle_status,
        default="insufficient_truth",
    )
    merge_ready_posture = _normalize_text(
        project_merge_ready_posture,
        default="insufficient_truth",
    )
    quarantine_posture = _normalize_text(
        project_branch_quarantine_candidate_posture,
        default="insufficient_truth",
    )
    local_main_sync_posture = _normalize_text(
        project_local_main_sync_posture,
        default="insufficient_truth",
    )
    quality_gate_status = _normalize_text(
        project_quality_gate_status,
        default="insufficient_truth",
    )
    quality_gate_posture = _normalize_text(
        project_quality_gate_posture,
        default="insufficient_truth",
    )
    quality_gate_risk_level = _normalize_text(
        project_quality_gate_risk_level,
        default="insufficient_truth",
    )
    queue_status = _normalize_text(
        project_pr_queue_status,
        default="insufficient_truth",
    )
    autonomy_budget_status = _normalize_text(
        project_autonomy_budget_status,
        default="insufficient_truth",
    )
    priority_posture = _normalize_text(
        project_priority_posture,
        default="insufficient_truth",
    )
    long_running_status = _normalize_text(
        long_running_stability_status,
        default="insufficient_truth",
    )
    repair_status = _normalize_text(
        supported_repair_execution_status,
        default="not_selected",
    )
    normalized_execution_reason = _normalize_text(
        execution_reason,
        default="restart_not_executed",
    )
    final_review_gate_status = _normalize_text(
        final_human_review_gate_status,
        default="not_required",
    )
    normalized_approval_reason_class = _normalize_text(
        approval_reason_class,
        default="unknown",
    )

    truth_sufficient = bool(
        failure_memory_status == "available"
        and lifecycle_status == "available"
        and quality_gate_status == "available"
        and queue_status in _PROJECT_PR_QUEUE_STATUSES
        and queue_status != "insufficient_truth"
        and autonomy_budget_status == "available"
        and priority_posture in _PROJECT_PRIORITY_POSTURES
        and priority_posture != "insufficient_truth"
    )
    if not truth_sufficient:
        reason_codes = _normalize_project_external_boundary_reason_codes(
            ["external_boundary_insufficient_truth"]
        )
        return {
            "project_external_boundary_status": "insufficient_truth",
            "project_external_boundary_reason": reason_codes[0],
            "project_external_boundary_reason_codes": reason_codes,
            "project_external_dependency_posture": "insufficient_truth",
            "project_external_dependency_available": False,
            "project_external_dependency_blocked": False,
            "project_external_manual_only_posture": "insufficient_truth",
            "project_external_manual_only_required": False,
            "project_external_network_boundary_posture": "insufficient_truth",
            "project_external_ci_boundary_posture": "insufficient_truth",
            "project_external_secrets_boundary_posture": "insufficient_truth",
            "project_external_github_boundary_posture": "insufficient_truth",
            "project_external_api_boundary_posture": "insufficient_truth",
            "project_external_boundary_unavailable": True,
        }

    manual_only_required = bool(
        manual_only_posture_active
        or final_human_review_required
        or final_review_gate_status == "required"
        or fleet_manual_review_required
        or normalized_approval_reason_class == "manual_only"
    )

    dependency_blocked = bool(
        not manual_only_required
        and (
            bool(project_failure_memory_suppression_active)
            or suppression_posture in {"suppress_retry", "suppress_repair", "suppress_review_issue", "suppress_failure_bucket"}
            or quarantine_posture == "candidate"
            or quality_gate_posture in {"retry_needed", "insufficient_truth"}
            or merge_ready_posture != "merge_ready"
            or queue_status == "blocked"
            or priority_posture == "deferred"
            or local_main_sync_posture == "sync_required"
            or long_running_status in {"paused", "escalated"}
            or normalized_execution_reason in {"restart_launch_failed"}
            or repair_status in {"not_executed_launch_failed"}
        )
    )
    dependency_available = bool(not manual_only_required and not dependency_blocked)
    dependency_posture = "dependency_available"
    if manual_only_required:
        dependency_posture = "manual_only"
    elif dependency_blocked:
        dependency_posture = "dependency_blocked"
    if dependency_posture not in _PROJECT_EXTERNAL_DEPENDENCY_POSTURES:
        dependency_posture = "insufficient_truth"

    if manual_only_required:
        network_posture = "manual_only"
        ci_posture = "manual_only"
        secrets_posture = "manual_only"
        github_posture = "manual_only"
        api_posture = "manual_only"
    else:
        network_posture = (
            "blocked"
            if (
                suppression_posture == "suppress_failure_bucket"
                or long_running_status in {"paused", "escalated"}
                or normalized_execution_reason == "restart_launch_failed"
            )
            else "clear"
        )
        ci_posture = (
            "blocked"
            if quality_gate_posture in {"retry_needed", "insufficient_truth"}
            or quality_gate_risk_level == "high"
            else "clear"
        )
        secrets_posture = (
            "blocked"
            if suppression_posture in {"suppress_repair", "suppress_failure_bucket"}
            or repair_status in {"not_executed_precheck_blocked", "not_executed_launch_failed"}
            else "clear"
        )
        github_posture = (
            "blocked"
            if merge_ready_posture != "merge_ready"
            or quarantine_posture == "candidate"
            or local_main_sync_posture == "sync_required"
            else "clear"
        )
        api_posture = (
            "blocked"
            if suppression_posture in {"suppress_repair", "suppress_failure_bucket"}
            or repair_status
            in {
                "executed_verification_failed",
                "not_executed_qualification_failed",
                "not_executed_launch_failed",
            }
            else "clear"
        )

    for boundary_posture in (
        network_posture,
        ci_posture,
        secrets_posture,
        github_posture,
        api_posture,
    ):
        if boundary_posture not in _PROJECT_EXTERNAL_BOUNDARY_POSTURES:
            reason_codes = _normalize_project_external_boundary_reason_codes(
                ["external_boundary_insufficient_truth"]
            )
            return {
                "project_external_boundary_status": "insufficient_truth",
                "project_external_boundary_reason": reason_codes[0],
                "project_external_boundary_reason_codes": reason_codes,
                "project_external_dependency_posture": "insufficient_truth",
                "project_external_dependency_available": False,
                "project_external_dependency_blocked": False,
                "project_external_manual_only_posture": "insufficient_truth",
                "project_external_manual_only_required": False,
                "project_external_network_boundary_posture": "insufficient_truth",
                "project_external_ci_boundary_posture": "insufficient_truth",
                "project_external_secrets_boundary_posture": "insufficient_truth",
                "project_external_github_boundary_posture": "insufficient_truth",
                "project_external_api_boundary_posture": "insufficient_truth",
                "project_external_boundary_unavailable": True,
            }

    reason_codes = ["external_boundary_compiled"]
    if dependency_posture == "manual_only":
        reason_codes.append("external_dependency_manual_only")
        reason_codes.append("external_boundary_manual_only")
    elif dependency_posture == "dependency_blocked":
        reason_codes.append("external_dependency_blocked")
    else:
        reason_codes.append("external_dependency_available")
    reason_codes.append(
        "external_network_boundary_blocked"
        if network_posture == "blocked"
        else "external_network_boundary_clear"
    )
    reason_codes.append(
        "external_ci_boundary_blocked"
        if ci_posture == "blocked"
        else "external_ci_boundary_clear"
    )
    reason_codes.append(
        "external_secrets_boundary_blocked"
        if secrets_posture == "blocked"
        else "external_secrets_boundary_clear"
    )
    reason_codes.append(
        "external_github_boundary_blocked"
        if github_posture == "blocked"
        else "external_github_boundary_clear"
    )
    reason_codes.append(
        "external_api_boundary_blocked"
        if api_posture == "blocked"
        else "external_api_boundary_clear"
    )
    reason_codes = _normalize_project_external_boundary_reason_codes(reason_codes)

    return {
        "project_external_boundary_status": "available",
        "project_external_boundary_reason": reason_codes[0],
        "project_external_boundary_reason_codes": reason_codes,
        "project_external_dependency_posture": dependency_posture,
        "project_external_dependency_available": bool(dependency_available),
        "project_external_dependency_blocked": bool(dependency_blocked),
        "project_external_manual_only_posture": (
            "manual_only" if manual_only_required else "clear"
        ),
        "project_external_manual_only_required": bool(manual_only_required),
        "project_external_network_boundary_posture": network_posture,
        "project_external_ci_boundary_posture": ci_posture,
        "project_external_secrets_boundary_posture": secrets_posture,
        "project_external_github_boundary_posture": github_posture,
        "project_external_api_boundary_posture": api_posture,
        "project_external_boundary_unavailable": False,
    }


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


def _build_project_human_escalation_state(
    *,
    final_human_review_gate_status: str,
    final_human_review_required: bool,
    final_human_review_reason: str,
    objective_compiler_status: str,
    objective_completion_posture: str,
    objective_scope_drift_status: str,
    project_autonomy_budget_status: str,
    project_priority_posture: str,
    project_high_risk_defer_posture: str,
    project_run_budget_posture: str,
    project_objective_budget_posture: str,
    project_pr_retry_budget_posture: str,
    project_quality_gate_status: str,
    project_quality_gate_risk_level: str,
    project_quality_gate_high_risk: bool,
    project_merge_branch_lifecycle_status: str,
    project_branch_quarantine_candidate_posture: str,
    project_failure_memory_status: str,
    project_failure_memory_suppression_posture: str,
    project_failure_memory_suppression_active: bool,
    project_failure_memory_retry_failure_count: int,
    project_failure_memory_repair_failure_count: int,
    project_failure_memory_review_issue_count: int,
    project_failure_memory_failure_bucket_recurrence_count: int,
    project_external_boundary_status: str,
    project_external_dependency_posture: str,
    project_external_manual_only_posture: str,
    project_external_manual_only_required: bool,
    long_running_stability_status: str,
    supported_repair_execution_status: str,
    manual_only_posture_active: bool,
    fleet_manual_review_required: bool,
) -> dict[str, Any]:
    final_gate_status = _normalize_text(
        final_human_review_gate_status,
        default="not_required",
    )
    final_reason = _normalize_text(
        final_human_review_reason,
        default="final_review_not_required",
    )
    objective_status = _normalize_text(
        objective_compiler_status,
        default="insufficient_truth",
    )
    completion_posture = _normalize_text(
        objective_completion_posture,
        default="objective_insufficient_truth",
    )
    scope_drift_status = _normalize_text(
        objective_scope_drift_status,
        default="insufficient_truth",
    )
    autonomy_budget_status = _normalize_text(
        project_autonomy_budget_status,
        default="insufficient_truth",
    )
    priority_posture = _normalize_text(
        project_priority_posture,
        default="insufficient_truth",
    )
    high_risk_defer_posture = _normalize_text(
        project_high_risk_defer_posture,
        default="insufficient_truth",
    )
    run_budget_posture = _normalize_text(
        project_run_budget_posture,
        default="insufficient_truth",
    )
    objective_budget_posture = _normalize_text(
        project_objective_budget_posture,
        default="insufficient_truth",
    )
    pr_retry_budget_posture = _normalize_text(
        project_pr_retry_budget_posture,
        default="insufficient_truth",
    )
    quality_gate_status = _normalize_text(
        project_quality_gate_status,
        default="insufficient_truth",
    )
    quality_gate_risk_level = _normalize_text(
        project_quality_gate_risk_level,
        default="insufficient_truth",
    )
    lifecycle_status = _normalize_text(
        project_merge_branch_lifecycle_status,
        default="insufficient_truth",
    )
    quarantine_posture = _normalize_text(
        project_branch_quarantine_candidate_posture,
        default="insufficient_truth",
    )
    failure_memory_status = _normalize_text(
        project_failure_memory_status,
        default="insufficient_truth",
    )
    suppression_posture = _normalize_text(
        project_failure_memory_suppression_posture,
        default="insufficient_truth",
    )
    external_boundary_status = _normalize_text(
        project_external_boundary_status,
        default="insufficient_truth",
    )
    external_dependency_posture = _normalize_text(
        project_external_dependency_posture,
        default="insufficient_truth",
    )
    external_manual_only_posture = _normalize_text(
        project_external_manual_only_posture,
        default="insufficient_truth",
    )
    long_running_status = _normalize_text(
        long_running_stability_status,
        default="insufficient_truth",
    )
    repair_status = _normalize_text(
        supported_repair_execution_status,
        default="not_selected",
    )

    truth_sufficient = bool(
        final_gate_status in _FINAL_HUMAN_REVIEW_GATE_STATUSES
        and objective_status == "available"
        and completion_posture in _OBJECTIVE_COMPLETION_POSTURES
        and completion_posture != "objective_insufficient_truth"
        and scope_drift_status in _OBJECTIVE_SCOPE_DRIFT_STATUSES
        and scope_drift_status != "insufficient_truth"
        and autonomy_budget_status == "available"
        and priority_posture in _PROJECT_PRIORITY_POSTURES
        and priority_posture != "insufficient_truth"
        and high_risk_defer_posture in _PROJECT_HIGH_RISK_DEFER_POSTURES
        and high_risk_defer_posture != "insufficient_truth"
        and run_budget_posture in _PROJECT_BUDGET_POSTURES
        and run_budget_posture != "insufficient_truth"
        and objective_budget_posture in _PROJECT_BUDGET_POSTURES
        and objective_budget_posture != "insufficient_truth"
        and pr_retry_budget_posture in _PROJECT_PR_RETRY_BUDGET_POSTURES
        and pr_retry_budget_posture != "insufficient_truth"
        and quality_gate_status == "available"
        and quality_gate_risk_level in _PROJECT_QUALITY_GATE_RISK_LEVELS
        and quality_gate_risk_level != "insufficient_truth"
        and lifecycle_status == "available"
        and quarantine_posture in _PROJECT_BRANCH_CANDIDATE_POSTURES
        and quarantine_posture != "insufficient_truth"
        and failure_memory_status == "available"
        and suppression_posture in _PROJECT_FAILURE_MEMORY_SUPPRESSION_POSTURES
        and suppression_posture != "insufficient_truth"
        and external_boundary_status == "available"
        and external_dependency_posture in _PROJECT_EXTERNAL_DEPENDENCY_POSTURES
        and external_dependency_posture != "insufficient_truth"
        and external_manual_only_posture in _PROJECT_EXTERNAL_BOUNDARY_POSTURES
        and external_manual_only_posture != "insufficient_truth"
        and long_running_status in _LONG_RUNNING_STABILITY_STATUSES
        and long_running_status != "insufficient_truth"
    )
    if not truth_sufficient:
        reason_codes = _normalize_project_human_escalation_reason_codes(
            ["escalation_insufficient_truth"]
        )
        return {
            "project_human_escalation_status": "insufficient_truth",
            "project_human_escalation_reason": reason_codes[0],
            "project_human_escalation_reason_codes": reason_codes,
            "project_human_escalation_posture": "insufficient_truth",
            "project_human_escalation_required": False,
            "project_architecture_risk_posture": "insufficient_truth",
            "project_scope_risk_posture": "insufficient_truth",
            "project_external_risk_posture": "insufficient_truth",
            "project_budget_risk_posture": "insufficient_truth",
            "project_repeated_failure_risk_posture": "insufficient_truth",
            "project_manual_only_risk_posture": "insufficient_truth",
            "project_human_escalation_unavailable": True,
        }

    architecture_risk_elevated = bool(
        completion_posture == "objective_blocked"
        or bool(project_quality_gate_high_risk)
        or quarantine_posture == "candidate"
        or long_running_status in {"paused", "escalated", "safe_stop"}
        or repair_status == "executed_verification_failed"
        or final_reason
        in {
            "final_review_high_risk_posture",
            "final_review_supported_repair_verification_failed",
        }
    )
    scope_risk_elevated = bool(
        scope_drift_status == "detected"
        or final_reason == "final_review_next_step_unresolved"
    )
    external_risk_elevated = bool(
        external_dependency_posture in {"dependency_blocked", "manual_only"}
        or external_manual_only_posture == "manual_only"
        or bool(project_external_manual_only_required)
    )
    budget_risk_elevated = bool(
        high_risk_defer_posture == "defer"
        or priority_posture == "deferred"
        or run_budget_posture == "exhausted"
        or objective_budget_posture == "exhausted"
        or pr_retry_budget_posture == "exhausted"
    )
    repeated_failure_risk_elevated = bool(
        bool(project_failure_memory_suppression_active)
        or suppression_posture != "none"
        or _as_non_negative_int(project_failure_memory_retry_failure_count, default=0) > 1
        or _as_non_negative_int(project_failure_memory_repair_failure_count, default=0)
        > 0
        or _as_non_negative_int(project_failure_memory_review_issue_count, default=0) > 1
        or _as_non_negative_int(
            project_failure_memory_failure_bucket_recurrence_count,
            default=0,
        )
        > 0
    )
    manual_only_risk_elevated = bool(
        bool(manual_only_posture_active)
        or bool(fleet_manual_review_required)
        or bool(project_external_manual_only_required)
        or external_manual_only_posture == "manual_only"
        or final_reason
        in {
            "final_review_manual_only_posture",
            "final_review_explicit_manual_review_required",
        }
    )

    escalation_required = bool(
        final_human_review_required
        or architecture_risk_elevated
        or scope_risk_elevated
        or external_risk_elevated
        or budget_risk_elevated
        or repeated_failure_risk_elevated
        or manual_only_risk_elevated
    )
    posture = "escalation_required" if escalation_required else "not_required"
    if posture not in _PROJECT_HUMAN_ESCALATION_POSTURES:
        posture = "insufficient_truth"

    reason_codes = ["escalation_compiled"]
    reason_codes.append(
        "escalation_required" if escalation_required else "escalation_not_required"
    )
    reason_codes.append(
        "escalation_architecture_risk_elevated"
        if architecture_risk_elevated
        else "escalation_architecture_risk_clear"
    )
    reason_codes.append(
        "escalation_scope_risk_elevated"
        if scope_risk_elevated
        else "escalation_scope_risk_clear"
    )
    reason_codes.append(
        "escalation_external_risk_elevated"
        if external_risk_elevated
        else "escalation_external_risk_clear"
    )
    reason_codes.append(
        "escalation_budget_risk_elevated"
        if budget_risk_elevated
        else "escalation_budget_risk_clear"
    )
    reason_codes.append(
        "escalation_repeated_failure_risk_elevated"
        if repeated_failure_risk_elevated
        else "escalation_repeated_failure_risk_clear"
    )
    reason_codes.append(
        "escalation_manual_only_risk_elevated"
        if manual_only_risk_elevated
        else "escalation_manual_only_risk_clear"
    )
    reason_codes = _normalize_project_human_escalation_reason_codes(reason_codes)

    return {
        "project_human_escalation_status": "available",
        "project_human_escalation_reason": reason_codes[0],
        "project_human_escalation_reason_codes": reason_codes,
        "project_human_escalation_posture": posture,
        "project_human_escalation_required": bool(escalation_required),
        "project_architecture_risk_posture": (
            "elevated" if architecture_risk_elevated else "clear"
        ),
        "project_scope_risk_posture": "elevated" if scope_risk_elevated else "clear",
        "project_external_risk_posture": (
            "elevated" if external_risk_elevated else "clear"
        ),
        "project_budget_risk_posture": "elevated" if budget_risk_elevated else "clear",
        "project_repeated_failure_risk_posture": (
            "elevated" if repeated_failure_risk_elevated else "clear"
        ),
        "project_manual_only_risk_posture": (
            "elevated" if manual_only_risk_elevated else "clear"
        ),
        "project_human_escalation_unavailable": False,
    }


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


def _build_project_approval_notification_state(
    *,
    approval_required: bool,
    approval_email_status: str,
    approval_email_validity: str,
    approval_priority: str,
    approval_reason_class: str,
    proposed_next_direction: str,
    delivery_mode: str,
    delivery_outcome: str,
    approval_response_status: str,
    approval_response_validity: str,
    response_received: bool,
    response_decision_class: str,
    project_human_escalation_status: str,
    project_human_escalation_posture: str,
    project_human_escalation_required: bool,
    project_human_escalation_reason: str,
    project_architecture_risk_posture: str,
    project_scope_risk_posture: str,
    project_external_risk_posture: str,
    project_budget_risk_posture: str,
    project_repeated_failure_risk_posture: str,
    project_manual_only_risk_posture: str,
    project_external_manual_only_posture: str,
) -> dict[str, Any]:
    normalized_email_status = _normalize_text(
        approval_email_status,
        default="insufficient_truth",
    )
    normalized_email_validity = _normalize_text(
        approval_email_validity,
        default="insufficient_truth",
    )
    normalized_priority = _normalize_text(approval_priority, default="unknown")
    normalized_reason_class = _normalize_text(approval_reason_class, default="unknown")
    normalized_direction = _normalize_text(proposed_next_direction, default="unknown")
    normalized_delivery_mode = _normalize_text(delivery_mode, default="unknown")
    normalized_delivery_outcome = _normalize_text(delivery_outcome, default="unknown")
    normalized_response_status = _normalize_text(
        approval_response_status,
        default="insufficient_truth",
    )
    normalized_response_validity = _normalize_text(
        approval_response_validity,
        default="insufficient_truth",
    )
    normalized_response_decision_class = _normalize_text(
        response_decision_class,
        default="unknown",
    )
    escalation_status = _normalize_text(
        project_human_escalation_status,
        default="insufficient_truth",
    )
    escalation_posture = _normalize_text(
        project_human_escalation_posture,
        default="insufficient_truth",
    )
    escalation_reason = _normalize_text(
        project_human_escalation_reason,
        default="escalation_insufficient_truth",
    )
    architecture_risk_posture = _normalize_text(
        project_architecture_risk_posture,
        default="insufficient_truth",
    )
    scope_risk_posture = _normalize_text(
        project_scope_risk_posture,
        default="insufficient_truth",
    )
    external_risk_posture = _normalize_text(
        project_external_risk_posture,
        default="insufficient_truth",
    )
    budget_risk_posture = _normalize_text(
        project_budget_risk_posture,
        default="insufficient_truth",
    )
    repeated_failure_risk_posture = _normalize_text(
        project_repeated_failure_risk_posture,
        default="insufficient_truth",
    )
    manual_only_risk_posture = _normalize_text(
        project_manual_only_risk_posture,
        default="insufficient_truth",
    )
    external_manual_only_posture = _normalize_text(
        project_external_manual_only_posture,
        default="insufficient_truth",
    )

    truth_sufficient = bool(
        normalized_email_validity == "valid"
        and normalized_response_validity == "valid"
        and normalized_email_status not in {"", "insufficient_truth"}
        and escalation_status == "available"
        and escalation_posture in _PROJECT_HUMAN_ESCALATION_POSTURES
        and escalation_posture != "insufficient_truth"
        and architecture_risk_posture in _PROJECT_HUMAN_ESCALATION_RISK_POSTURES
        and architecture_risk_posture != "insufficient_truth"
        and scope_risk_posture in _PROJECT_HUMAN_ESCALATION_RISK_POSTURES
        and scope_risk_posture != "insufficient_truth"
        and external_risk_posture in _PROJECT_HUMAN_ESCALATION_RISK_POSTURES
        and external_risk_posture != "insufficient_truth"
        and budget_risk_posture in _PROJECT_HUMAN_ESCALATION_RISK_POSTURES
        and budget_risk_posture != "insufficient_truth"
        and repeated_failure_risk_posture in _PROJECT_HUMAN_ESCALATION_RISK_POSTURES
        and repeated_failure_risk_posture != "insufficient_truth"
        and manual_only_risk_posture in _PROJECT_HUMAN_ESCALATION_RISK_POSTURES
        and manual_only_risk_posture != "insufficient_truth"
        and external_manual_only_posture in _PROJECT_EXTERNAL_BOUNDARY_POSTURES
        and external_manual_only_posture != "insufficient_truth"
    )
    if not truth_sufficient:
        reason_codes = _normalize_project_approval_notification_reason_codes(
            ["approval_notification_insufficient_truth"]
        )
        return {
            "project_approval_notification_status": "insufficient_truth",
            "project_approval_notification_reason": reason_codes[0],
            "project_approval_notification_reason_codes": reason_codes,
            "project_approval_notification_ready_posture": "insufficient_truth",
            "project_approval_notification_ready": False,
            "project_approval_reply_required_posture": "insufficient_truth",
            "project_approval_reply_required": False,
            "project_approval_channel_posture": "insufficient_truth",
            "project_approval_mobile_summary_posture": "insufficient_truth",
            "project_approval_mobile_summary_compact": "",
            "project_approval_mobile_summary_tokens": [],
            "project_approval_notification_unavailable": True,
        }

    escalation_required = bool(
        project_human_escalation_required
        or escalation_posture == "escalation_required"
    )
    notification_required = bool(approval_required and escalation_required)

    channel_posture = "insufficient_truth"
    if not notification_required:
        channel_posture = "not_required"
    elif (
        manual_only_risk_posture == "elevated"
        or external_manual_only_posture == "manual_only"
        or escalation_reason in {
            "escalation_manual_only_risk_elevated",
            "escalation_external_risk_elevated",
        }
    ):
        channel_posture = "manual_only"
    elif normalized_delivery_mode == "gmail_send" or normalized_delivery_outcome == "sent":
        channel_posture = "email_send"
    elif (
        normalized_delivery_mode == "gmail_draft"
        or normalized_delivery_outcome == "draft_created"
    ):
        channel_posture = "email_draft"
    elif (
        normalized_delivery_mode == "review_queue_only"
        or normalized_delivery_outcome == "queued_for_review"
    ):
        channel_posture = "review_queue"
    elif normalized_email_status in {"required", "delivered_for_review"}:
        channel_posture = "review_queue"

    if channel_posture not in _PROJECT_APPROVAL_CHANNEL_POSTURES:
        channel_posture = "insufficient_truth"

    notification_ready_posture = "insufficient_truth"
    notification_ready = False
    if not notification_required:
        notification_ready_posture = "not_required"
    elif channel_posture in {"email_send", "email_draft", "review_queue", "manual_only"}:
        if normalized_email_status in {"required", "delivered_for_review"}:
            notification_ready_posture = "ready"
            notification_ready = True
        else:
            notification_ready_posture = "not_ready"

    if notification_ready_posture not in _PROJECT_APPROVAL_NOTIFICATION_READY_POSTURES:
        notification_ready_posture = "insufficient_truth"

    terminal_response = normalized_response_status in {
        "response_accepted",
        "response_rejected",
        "response_held",
        "response_unsupported",
    } or normalized_response_decision_class in {"approved", "rejected", "held", "unsupported"}
    reply_required = bool(
        notification_required
        and not terminal_response
        and normalized_response_status in {"awaiting_response", "response_received"}
    )
    reply_required_posture = (
        "reply_required"
        if reply_required
        else (
            "reply_not_required"
            if notification_required or not notification_required
            else "insufficient_truth"
        )
    )
    if reply_required_posture not in _PROJECT_APPROVAL_REPLY_REQUIRED_POSTURES:
        reply_required_posture = "insufficient_truth"

    mobile_summary_posture = "insufficient_truth"
    summary_tokens: list[str] = []
    summary_compact = ""
    if not notification_required:
        mobile_summary_posture = "not_required"
    elif notification_ready_posture in {"ready", "not_ready"}:
        mobile_summary_posture = "available"
        elevated_risks = [
            risk_name
            for risk_name, risk_posture in (
                ("arch", architecture_risk_posture),
                ("scope", scope_risk_posture),
                ("ext", external_risk_posture),
                ("budget", budget_risk_posture),
                ("repeat", repeated_failure_risk_posture),
                ("manual", manual_only_risk_posture),
            )
            if risk_posture == "elevated"
        ]
        risk_token = "+".join(elevated_risks) if elevated_risks else "none"
        summary_tokens = _serialize_required_signals(
            [
                "escalate",
                f"prio:{normalized_priority}",
                f"dir:{normalized_direction}",
                f"ch:{channel_posture}",
                f"reply:{'yes' if reply_required else 'no'}",
                f"risk:{risk_token}",
            ]
        )
        summary_compact = " | ".join(summary_tokens[:6])

    if mobile_summary_posture not in _PROJECT_APPROVAL_MOBILE_SUMMARY_POSTURES:
        mobile_summary_posture = "insufficient_truth"

    reason_codes = ["approval_notification_compiled"]
    reason_codes.append(
        "approval_escalation_required"
        if escalation_required
        else "approval_escalation_not_required"
    )
    if notification_ready_posture == "ready":
        reason_codes.append("approval_notification_ready")
    elif notification_ready_posture == "not_ready":
        reason_codes.append("approval_notification_not_ready")
    else:
        reason_codes.append("approval_notification_not_required")
    reason_codes.append(
        "approval_reply_required"
        if reply_required
        else "approval_reply_not_required"
    )
    if channel_posture == "email_send":
        reason_codes.append("approval_channel_email_send")
    elif channel_posture == "email_draft":
        reason_codes.append("approval_channel_email_draft")
    elif channel_posture == "review_queue":
        reason_codes.append("approval_channel_review_queue")
    elif channel_posture == "manual_only":
        reason_codes.append("approval_channel_manual_only")
    elif channel_posture == "not_required":
        reason_codes.append("approval_channel_not_required")
    else:
        reason_codes.append("approval_channel_insufficient_truth")
    if mobile_summary_posture == "available":
        reason_codes.append("approval_mobile_summary_available")
    elif mobile_summary_posture == "not_required":
        reason_codes.append("approval_mobile_summary_not_required")
    else:
        reason_codes.append("approval_mobile_summary_insufficient_truth")
    reason_codes.append(
        "approval_response_awaiting"
        if not terminal_response and not response_received
        else "approval_response_terminal"
    )
    reason_codes = _normalize_project_approval_notification_reason_codes(reason_codes)

    return {
        "project_approval_notification_status": "available",
        "project_approval_notification_reason": reason_codes[0],
        "project_approval_notification_reason_codes": reason_codes,
        "project_approval_notification_ready_posture": notification_ready_posture,
        "project_approval_notification_ready": bool(notification_ready),
        "project_approval_reply_required_posture": reply_required_posture,
        "project_approval_reply_required": bool(reply_required),
        "project_approval_channel_posture": channel_posture,
        "project_approval_mobile_summary_posture": mobile_summary_posture,
        "project_approval_mobile_summary_compact": summary_compact,
        "project_approval_mobile_summary_tokens": summary_tokens,
        "project_approval_notification_unavailable": False,
    }


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


def _build_project_multi_objective_state(
    *,
    objective_id: str,
    objective_compiler_status: str,
    objective_completion_posture: str,
    project_priority_posture: str,
    project_high_risk_defer_posture: str,
    project_run_budget_posture: str,
    project_objective_budget_posture: str,
    project_pr_retry_budget_posture: str,
    project_merge_branch_lifecycle_status: str,
    project_merge_ready_posture: str,
    project_branch_quarantine_candidate_posture: str,
    project_human_escalation_status: str,
    project_human_escalation_required: bool,
    project_approval_notification_status: str,
    project_approval_notification_ready_posture: str,
    project_approval_reply_required_posture: str,
    project_pr_queue_status: str,
    project_pr_queue_selected_slice_id: str,
    project_pr_queue_processed_slice_ids_after: list[str],
    project_pr_queue_item_count: int,
    project_pr_queue_runnable_count: int,
    project_pr_queue_blocked_count: int,
    project_pr_queue_handoff_prepared: bool,
) -> dict[str, Any]:
    normalized_objective_id = _normalize_text(objective_id, default="")
    objective_status = _normalize_text(
        objective_compiler_status,
        default="insufficient_truth",
    )
    completion_posture = _normalize_text(
        objective_completion_posture,
        default="objective_insufficient_truth",
    )
    priority_posture = _normalize_text(
        project_priority_posture,
        default="insufficient_truth",
    )
    high_risk_defer_posture = _normalize_text(
        project_high_risk_defer_posture,
        default="insufficient_truth",
    )
    run_budget_posture = _normalize_text(
        project_run_budget_posture,
        default="insufficient_truth",
    )
    objective_budget_posture = _normalize_text(
        project_objective_budget_posture,
        default="insufficient_truth",
    )
    pr_retry_budget_posture = _normalize_text(
        project_pr_retry_budget_posture,
        default="insufficient_truth",
    )
    lifecycle_status = _normalize_text(
        project_merge_branch_lifecycle_status,
        default="insufficient_truth",
    )
    merge_ready_posture = _normalize_text(
        project_merge_ready_posture,
        default="insufficient_truth",
    )
    quarantine_posture = _normalize_text(
        project_branch_quarantine_candidate_posture,
        default="insufficient_truth",
    )
    escalation_status = _normalize_text(
        project_human_escalation_status,
        default="insufficient_truth",
    )
    notification_status = _normalize_text(
        project_approval_notification_status,
        default="insufficient_truth",
    )
    notification_ready_posture = _normalize_text(
        project_approval_notification_ready_posture,
        default="insufficient_truth",
    )
    reply_required_posture = _normalize_text(
        project_approval_reply_required_posture,
        default="insufficient_truth",
    )
    queue_status = _normalize_text(project_pr_queue_status, default="insufficient_truth")
    selected_slice_id = _normalize_text(project_pr_queue_selected_slice_id, default="")
    processed_slice_ids = _normalize_string_list(project_pr_queue_processed_slice_ids_after)
    queue_item_count = _as_non_negative_int(project_pr_queue_item_count, default=0)
    queue_runnable_count = _as_non_negative_int(project_pr_queue_runnable_count, default=0)
    queue_blocked_count = _as_non_negative_int(project_pr_queue_blocked_count, default=0)

    truth_sufficient = bool(
        normalized_objective_id
        and objective_status == "available"
        and completion_posture in _OBJECTIVE_COMPLETION_POSTURES
        and completion_posture != "objective_insufficient_truth"
        and priority_posture in _PROJECT_PRIORITY_POSTURES
        and priority_posture != "insufficient_truth"
        and high_risk_defer_posture in _PROJECT_HIGH_RISK_DEFER_POSTURES
        and high_risk_defer_posture != "insufficient_truth"
        and run_budget_posture in _PROJECT_BUDGET_POSTURES
        and run_budget_posture != "insufficient_truth"
        and objective_budget_posture in _PROJECT_BUDGET_POSTURES
        and objective_budget_posture != "insufficient_truth"
        and pr_retry_budget_posture in _PROJECT_PR_RETRY_BUDGET_POSTURES
        and pr_retry_budget_posture != "insufficient_truth"
        and lifecycle_status == "available"
        and merge_ready_posture in _PROJECT_MERGE_READY_POSTURES
        and merge_ready_posture != "insufficient_truth"
        and quarantine_posture in _PROJECT_BRANCH_CANDIDATE_POSTURES
        and quarantine_posture != "insufficient_truth"
        and escalation_status == "available"
        and notification_status == "available"
        and notification_ready_posture in _PROJECT_APPROVAL_NOTIFICATION_READY_POSTURES
        and notification_ready_posture != "insufficient_truth"
        and reply_required_posture in _PROJECT_APPROVAL_REPLY_REQUIRED_POSTURES
        and reply_required_posture != "insufficient_truth"
        and queue_status in _PROJECT_PR_QUEUE_STATUSES
        and queue_status != "insufficient_truth"
    )
    if not truth_sufficient:
        reason_codes = _normalize_project_multi_objective_reason_codes(
            ["multi_objective_insufficient_truth"]
        )
        return {
            "project_multi_objective_status": "insufficient_truth",
            "project_multi_objective_reason": reason_codes[0],
            "project_multi_objective_reason_codes": reason_codes,
            "project_active_objective_selection_posture": "insufficient_truth",
            "project_active_objective_id": "",
            "project_blocked_objective_deferral_posture": "insufficient_truth",
            "project_blocked_objective_deferred": False,
            "project_resumable_queue_ordering_posture": "insufficient_truth",
            "project_resumable_queue_ordering_key": "",
            "project_resumable_queue_next_slice_id": "",
            "project_resumable_queue_has_pending": False,
            "project_multi_objective_unavailable": True,
        }

    blocked_objective_deferred = bool(
        completion_posture == "objective_blocked"
        or priority_posture == "deferred"
        or high_risk_defer_posture == "defer"
        or bool(project_human_escalation_required)
        or notification_ready_posture in {"ready", "not_ready"}
        or reply_required_posture == "reply_required"
        or quarantine_posture == "candidate"
    )

    active_selection_posture = (
        "deferred" if blocked_objective_deferred else "selected"
    )
    if active_selection_posture not in _PROJECT_ACTIVE_OBJECTIVE_SELECTION_POSTURES:
        active_selection_posture = "insufficient_truth"
    blocked_deferral_posture = (
        "deferred" if blocked_objective_deferred else "not_deferred"
    )
    if blocked_deferral_posture not in _PROJECT_BLOCKED_OBJECTIVE_DEFERRAL_POSTURES:
        blocked_deferral_posture = "insufficient_truth"

    queue_ordering_posture = "insufficient_truth"
    if blocked_objective_deferred:
        queue_ordering_posture = "deferred_non_runnable"
    elif queue_status == "prepared":
        queue_ordering_posture = "resume_selected_first"
    elif queue_status == "blocked":
        queue_ordering_posture = "resume_blocked"
    elif queue_status == "empty":
        if processed_slice_ids or bool(project_pr_queue_handoff_prepared):
            queue_ordering_posture = "resume_completed_waiting"
        else:
            queue_ordering_posture = "resume_empty"
    if queue_ordering_posture not in _PROJECT_RESUMABLE_QUEUE_ORDERING_POSTURES:
        queue_ordering_posture = "insufficient_truth"

    queue_has_pending = bool(
        not blocked_objective_deferred
        and (
            queue_status == "prepared"
            or queue_runnable_count > 0
            or (queue_item_count > 0 and queue_status == "blocked" and queue_blocked_count > 0)
        )
    )
    queue_ordering_key = (
        f"{normalized_objective_id}:{queue_status}:{selected_slice_id or '-'}:{len(processed_slice_ids)}"
    )

    reason_codes = ["multi_objective_compiled"]
    reason_codes.append(
        "multi_objective_deferred"
        if blocked_objective_deferred
        else "multi_objective_selected"
    )
    reason_codes.append(
        "multi_objective_blocked_objective_deferred"
        if blocked_objective_deferred
        else "multi_objective_blocked_objective_not_deferred"
    )
    if queue_ordering_posture == "resume_selected_first":
        reason_codes.append("multi_objective_queue_resume_selected_first")
    elif queue_ordering_posture == "resume_blocked":
        reason_codes.append("multi_objective_queue_resume_blocked")
    elif queue_ordering_posture == "resume_completed_waiting":
        reason_codes.append("multi_objective_queue_resume_completed_waiting")
    elif queue_ordering_posture == "resume_empty":
        reason_codes.append("multi_objective_queue_resume_empty")
    else:
        reason_codes.append("multi_objective_queue_deferred_non_runnable")
    if notification_ready_posture in {"ready", "not_ready"} or reply_required_posture == "reply_required":
        reason_codes.append("multi_objective_approval_notification_deferred")
    if bool(project_human_escalation_required):
        reason_codes.append("multi_objective_escalation_deferred")
    reason_codes = _normalize_project_multi_objective_reason_codes(reason_codes)

    return {
        "project_multi_objective_status": "available",
        "project_multi_objective_reason": reason_codes[0],
        "project_multi_objective_reason_codes": reason_codes,
        "project_active_objective_selection_posture": active_selection_posture,
        "project_active_objective_id": normalized_objective_id,
        "project_blocked_objective_deferral_posture": blocked_deferral_posture,
        "project_blocked_objective_deferred": bool(blocked_objective_deferred),
        "project_resumable_queue_ordering_posture": queue_ordering_posture,
        "project_resumable_queue_ordering_key": queue_ordering_key,
        "project_resumable_queue_next_slice_id": selected_slice_id,
        "project_resumable_queue_has_pending": bool(queue_has_pending),
        "project_multi_objective_unavailable": False,
    }


def _classify_continuation_branch_type(
    *,
    approved_next_direction: str,
    proposed_next_direction: str,
) -> str:
    direction = _normalize_text(
        approved_next_direction or proposed_next_direction,
        default="unknown",
    )
    if direction in {"same_lane_retry", "repair_retry"}:
        return "retry"
    if direction == "replan_preparation":
        return "replan"
    if direction == "truth_gathering":
        return "truth_gather"
    return "unknown"


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
    }


def _build_approved_restart_execution_contract_surface(
    *,
    run_id: str,
    objective_contract_payload: Mapping[str, Any] | None,
    approval_email_delivery_payload: Mapping[str, Any] | None,
    fleet_safety_control_payload: Mapping[str, Any] | None,
    approval_runtime_rules_payload: Mapping[str, Any] | None,
    failure_bucketing_hardening_payload: Mapping[str, Any] | None,
    loop_hardening_contract_payload: Mapping[str, Any] | None,
    approved_restart_payload: Mapping[str, Any] | None,
    approval_response_payload: Mapping[str, Any] | None,
    approval_safety_payload: Mapping[str, Any] | None,
    prior_approved_restart_execution_payload: Mapping[str, Any] | None,
    manifest_units: list[Mapping[str, Any]],
    adapter: CodexExecutorAdapter,
    dry_run: bool,
    now: Callable[[], datetime],
) -> dict[str, Any]:
    objective = dict(objective_contract_payload or {})
    approval_email_delivery = dict(approval_email_delivery_payload or {})
    fleet_safety_control = dict(fleet_safety_control_payload or {})
    approval_runtime_rules = dict(approval_runtime_rules_payload or {})
    failure_bucketing_hardening = dict(failure_bucketing_hardening_payload or {})
    loop_hardening_contract = dict(loop_hardening_contract_payload or {})
    approved_restart = dict(approved_restart_payload or {})
    approval_response = dict(approval_response_payload or {})
    approval_safety = dict(approval_safety_payload or {})
    prior_approved_restart_execution = dict(prior_approved_restart_execution_payload or {})

    objective_id = _normalize_text(objective.get("objective_id"), default="")
    approved_restart_status = _normalize_text(
        approved_restart.get("approved_restart_status"),
        default="insufficient_truth",
    )
    approved_restart_validity = _normalize_text(
        approved_restart.get("approved_restart_validity"),
        default="insufficient_truth",
    )
    restart_decision = _normalize_text(approved_restart.get("restart_decision"), default="unknown")
    restart_allowed = bool(approved_restart.get("restart_allowed", False))
    restart_blocked = bool(approved_restart.get("restart_blocked", False))
    restart_held = bool(approved_restart.get("restart_held", False))
    restart_manual_followup = bool(approved_restart.get("restart_requires_manual_followup", False))
    approved_next_direction = _normalize_text(
        approved_restart.get("approved_next_direction"),
        default="unknown",
    )
    approved_target_lane = _normalize_text(
        approved_restart.get("approved_target_lane"),
        default="unknown",
    )
    approved_action_class = _normalize_text(
        approved_restart.get("approved_action_class"),
        default="unknown",
    )

    approval_response_status = _normalize_text(
        approval_response.get("approval_response_status"),
        default="insufficient_truth",
    )
    response_decision_class = _normalize_text(
        approval_response.get("response_decision_class"),
        default="unknown",
    )
    response_command_normalized = _normalize_text(
        approval_response.get("response_command_normalized"),
        default="",
    )
    response_received = bool(approval_response.get("response_received", False))
    response_supported = bool(approval_response.get("response_supported", False))
    approval_response_validity = _normalize_text(
        approval_response.get("approval_response_validity"),
        default="insufficient_truth",
    )

    approval_safety_status = _normalize_text(
        approval_safety.get("approval_safety_status"),
        default="insufficient_truth",
    )
    approval_safety_decision = _normalize_text(
        approval_safety.get("approval_safety_decision"),
        default="unknown",
    )
    safety_duplicate_pending = bool(
        approval_safety.get("approval_pending_duplicate", False)
    ) or approval_safety_status == "duplicate_pending"
    safety_cooldown_active = bool(
        approval_safety.get("approval_cooldown_active", False)
    ) or approval_safety_status == "cooldown_active"
    safety_loop_suspected = bool(
        approval_safety.get("approval_loop_suspected", False)
    ) or approval_safety_status == "loop_suspected"
    safety_delivery_blocked = bool(
        approval_safety.get("approval_delivery_blocked_by_safety", False)
    ) or approval_safety_status == "delivery_blocked"
    safety_delivery_deferred = bool(
        approval_safety.get("approval_delivery_deferred_by_safety", False)
    ) or approval_safety_status == "delivery_deferred"
    approval_safety_validity = _normalize_text(
        approval_safety.get("approval_safety_validity"),
        default="insufficient_truth",
    )

    approval_required = bool(approval_email_delivery.get("approval_required", False))
    approval_email_status = _normalize_text(
        approval_email_delivery.get("approval_email_status"),
        default="insufficient_truth",
    )
    approval_email_validity = _normalize_text(
        approval_email_delivery.get("approval_email_validity"),
        default="insufficient_truth",
    )
    approval_priority = _normalize_text(
        approval_email_delivery.get("approval_priority"),
        default="unknown",
    )
    approval_reason_class = _normalize_text(
        approval_email_delivery.get("approval_reason_class"),
        default="unknown",
    )
    proposed_next_direction = _normalize_text(
        approval_email_delivery.get("proposed_next_direction"),
        default="unknown",
    )
    proposed_target_lane = _normalize_text(
        approval_email_delivery.get("proposed_target_lane"),
        default="unknown",
    )
    proposed_restart_mode = _normalize_text(
        approval_email_delivery.get("proposed_restart_mode"),
        default="unknown",
    )
    proposed_action_class = _normalize_text(
        approval_email_delivery.get("proposed_action_class"),
        default="unknown",
    )
    approval_delivery_mode = _normalize_text(
        approval_email_delivery.get("delivery_mode"),
        default="unknown",
    )
    approval_delivery_outcome = _normalize_text(
        approval_email_delivery.get("delivery_outcome"),
        default="unknown",
    )

    fleet_safety_status = _normalize_text(
        fleet_safety_control.get("fleet_safety_status"),
        default="insufficient_truth",
    )
    fleet_safety_decision = _normalize_text(
        fleet_safety_control.get("fleet_safety_decision"),
        default="unknown",
    )
    fleet_restart_decision = _normalize_text(
        fleet_safety_control.get("fleet_restart_decision"),
        default="unknown",
    )
    fleet_safety_validity = _normalize_text(
        fleet_safety_control.get("fleet_safety_validity"),
        default="insufficient_truth",
    )
    fleet_manual_review_required = bool(
        fleet_safety_control.get("fleet_manual_review_required", False)
    )
    bucket_severity = _normalize_text(
        fleet_safety_control.get("bucket_severity"),
        default=_normalize_text(
            approval_email_delivery.get("bucket_severity"),
            default="unknown",
        ),
    )

    runtime_rules_mode = _normalize_text(
        approval_runtime_rules.get("direction_rule_mode"),
        default="unknown",
    )
    runtime_rules_present = bool(
        _normalize_text(approval_runtime_rules.get("runtime_rules_version"), default="")
    )
    failure_bucketing_status = _normalize_text(
        failure_bucketing_hardening.get("failure_bucketing_status"),
        default="unknown",
    )
    failure_bucketing_validity = _normalize_text(
        failure_bucketing_hardening.get("failure_bucketing_validity"),
        default="unknown",
    )
    failure_bucketing_primary_bucket = _normalize_text(
        failure_bucketing_hardening.get("primary_failure_bucket"),
        default="unknown",
    )
    loop_hardening_status = _normalize_text(
        loop_hardening_contract.get("loop_hardening_status"),
        default="unknown",
    )
    loop_hardening_validity = _normalize_text(
        loop_hardening_contract.get("loop_hardening_validity"),
        default="unknown",
    )
    loop_no_progress_status = _normalize_text(
        loop_hardening_contract.get("no_progress_status"),
        default="unknown",
    )
    loop_no_progress_detected = bool(
        loop_hardening_contract.get("no_progress_detected", False)
    )
    loop_no_progress_stop_required = bool(
        loop_hardening_contract.get("no_progress_stop_required", False)
    )

    approval_skip_allowed = False
    approval_skip_applied = False
    approval_skip_gate_status = "approval_required"
    approval_skip_gate_decision = "require_human_approval"
    approval_skip_reason = "skip_not_allowed"
    approval_skip_reason_codes: list[str] = []
    approval_skip_effective_command = ""
    approval_skip_effective_restart_decision = ""
    approval_skip_effective_next_direction = ""
    approval_skip_effective_target_lane = ""
    approval_skip_effective_action_class = ""
    approval_skip_human_gate_preserved = True

    supported_skip_direction = proposed_next_direction in _APPROVAL_SKIP_DIRECTION_TO_POSTURE
    hold_or_reject_posture = (
        response_command_normalized in {"HOLD", "REJECT"}
        or response_decision_class in {"held", "rejected"}
        or approval_response_status in {"response_held", "response_rejected"}
    )
    response_already_approved = (
        approval_response_status == "response_accepted"
        and response_decision_class == "approved"
        and (
            response_supported
            or response_command_normalized in {
                "OK RETRY",
                "OK REPLAN",
                "OK TRUTH",
                "OK CLOSE",
            }
        )
    )
    invalid_or_insufficient_truth = any(
        (
            not objective_id,
            approval_email_validity != "valid",
            approval_safety_validity != "valid",
            fleet_safety_validity != "valid",
            approval_response_validity != "valid",
            approval_email_status in {"insufficient_truth", ""},
            approval_safety_status == "insufficient_truth",
            fleet_safety_status == "insufficient_truth",
            runtime_rules_mode != "deterministic_rules_v1",
            not runtime_rules_present,
        )
    )
    safety_clear = bool(
        approval_safety_status in {"safe_to_deliver", "not_applicable"}
        and not safety_duplicate_pending
        and not safety_cooldown_active
        and not safety_loop_suspected
        and not safety_delivery_blocked
        and not safety_delivery_deferred
    )
    manual_review_required = bool(
        fleet_manual_review_required
        or fleet_restart_decision == "manual_only"
        or fleet_safety_decision == "escalate_manual"
        or proposed_next_direction == "manual_review_preparation"
        or approval_reason_class == "manual_only"
    )
    high_risk_posture = bool(
        approval_priority in {"high", "critical"}
        or bucket_severity in {"high", "critical"}
        or approval_reason_class
        in {"lane_change_high_risk", "bucket_high_risk", "integrity_degraded"}
        or fleet_safety_status in {"freeze", "stop", "degraded"}
        or fleet_safety_decision in {"freeze_run", "stop_run", "hold_for_review"}
    )
    unsupported_posture = bool(
        not supported_skip_direction
        or proposed_action_class in {"unknown", "review_only", "stop_only"}
        or proposed_restart_mode in {"blocked", "held", "approval_required_then_manual"}
    )

    if not approval_required:
        approval_skip_gate_status = "not_applicable"
        approval_skip_gate_decision = "not_applicable"
        approval_skip_reason = "skip_not_applicable_approval_not_required"
    elif response_already_approved:
        approval_skip_reason = "skip_human_response_already_present"
    elif hold_or_reject_posture:
        approval_skip_reason = "skip_hold_or_reject_posture"
    elif invalid_or_insufficient_truth:
        approval_skip_gate_status = "insufficient_truth"
        approval_skip_reason = "skip_invalid_or_insufficient_truth"
    elif safety_duplicate_pending:
        approval_skip_reason = "skip_safety_duplicate_pending"
    elif safety_cooldown_active:
        approval_skip_reason = "skip_safety_cooldown_active"
    elif safety_loop_suspected:
        approval_skip_reason = "skip_safety_loop_suspected"
    elif safety_delivery_blocked:
        approval_skip_reason = "skip_safety_delivery_blocked"
    elif safety_delivery_deferred:
        approval_skip_reason = "skip_safety_delivery_deferred"
    elif not safety_clear:
        approval_skip_reason = "skip_safety_not_clear"
    elif manual_review_required:
        approval_skip_reason = "skip_manual_review_required"
    elif high_risk_posture:
        approval_skip_reason = "skip_high_risk_posture"
    elif unsupported_posture:
        approval_skip_reason = "skip_unsupported_direction"
    else:
        approval_skip_allowed = True
        approval_skip_applied = True
        approval_skip_gate_status = "skip_allowed"
        approval_skip_gate_decision = "skip_and_continue_once"
        approval_skip_reason = "skip_allowed_low_risk"
        mapped_posture = _APPROVAL_SKIP_DIRECTION_TO_POSTURE.get(proposed_next_direction, {})
        approval_skip_effective_command = _normalize_text(
            mapped_posture.get("response_command"),
            default="",
        )
        approval_skip_effective_restart_decision = _normalize_text(
            mapped_posture.get("restart_decision"),
            default="unknown",
        )
        approval_skip_effective_next_direction = proposed_next_direction
        approval_skip_effective_target_lane = proposed_target_lane
        approval_skip_effective_action_class = proposed_action_class
        approval_response_status = "response_accepted"
        response_decision_class = "approved"
        response_command_normalized = approval_skip_effective_command
        approved_restart_status = "restart_allowed"
        approved_restart_validity = "valid"
        restart_decision = approval_skip_effective_restart_decision
        restart_allowed = True
        restart_blocked = False
        restart_held = False
        restart_manual_followup = False
        approved_next_direction = approval_skip_effective_next_direction
        approved_target_lane = approval_skip_effective_target_lane
        approved_action_class = approval_skip_effective_action_class

    approval_skip_human_gate_preserved = not approval_skip_applied
    approval_skip_reason_codes = _normalize_approval_skip_reason_codes([approval_skip_reason])

    continuation_budget_run_limit = _CONTINUATION_BUDGET_RUN_LIMIT_DEFAULT
    continuation_budget_objective_limit = _CONTINUATION_BUDGET_OBJECTIVE_LIMIT_DEFAULT
    continuation_budget_lane_limit = _CONTINUATION_BUDGET_LANE_LIMIT_DEFAULT
    continuation_budget_branch_type = _classify_continuation_branch_type(
        approved_next_direction=approved_next_direction,
        proposed_next_direction=proposed_next_direction,
    )
    continuation_budget_branch_applicable = (
        continuation_budget_branch_type in _CONTINUATION_BUDGET_BRANCH_TYPES
    )
    continuation_budget_branch_limit = _as_non_negative_int(
        _CONTINUATION_BUDGET_BRANCH_LIMIT_DEFAULTS.get(continuation_budget_branch_type),
        default=0,
    )
    continuation_budget_objective_key = _normalize_text(objective_id, default="")
    continuation_budget_lane_key = _normalize_text(
        approved_target_lane or proposed_target_lane,
        default="unknown",
    )
    prior_continuation_run_count = _as_non_negative_int(
        prior_approved_restart_execution.get("automatic_continuation_run_count"),
        default=0,
    )
    prior_continuation_objective_count = _as_non_negative_int(
        prior_approved_restart_execution.get("automatic_continuation_objective_count"),
        default=0,
    )
    prior_continuation_lane_count = _as_non_negative_int(
        prior_approved_restart_execution.get("automatic_continuation_lane_count"),
        default=0,
    )
    prior_continuation_retry_count = _as_non_negative_int(
        prior_approved_restart_execution.get("automatic_continuation_retry_count"),
        default=0,
    )
    prior_continuation_replan_count = _as_non_negative_int(
        prior_approved_restart_execution.get("automatic_continuation_replan_count"),
        default=0,
    )
    prior_continuation_truth_gather_count = _as_non_negative_int(
        prior_approved_restart_execution.get("automatic_continuation_truth_gather_count"),
        default=0,
    )
    prior_continuation_objective_key = _normalize_text(
        prior_approved_restart_execution.get("automatic_continuation_objective_key"),
        default="",
    )
    prior_continuation_lane_key = _normalize_text(
        prior_approved_restart_execution.get("automatic_continuation_lane_key"),
        default="",
    )
    continuation_run_count_before = prior_continuation_run_count
    continuation_objective_count_before = (
        prior_continuation_objective_count
        if continuation_budget_objective_key
        and continuation_budget_objective_key == prior_continuation_objective_key
        else 0
    )
    continuation_lane_count_before = (
        prior_continuation_lane_count
        if continuation_budget_lane_key
        and continuation_budget_lane_key == prior_continuation_lane_key
        else 0
    )
    continuation_branch_count_before = 0
    if continuation_budget_branch_type == "retry":
        continuation_branch_count_before = prior_continuation_retry_count
    elif continuation_budget_branch_type == "replan":
        continuation_branch_count_before = prior_continuation_replan_count
    elif continuation_budget_branch_type == "truth_gather":
        continuation_branch_count_before = prior_continuation_truth_gather_count
    continuation_budget_truth_sufficient = bool(
        continuation_budget_objective_key
        and continuation_budget_lane_key
        and continuation_budget_lane_key != "unknown"
    )
    continuation_budget_run_exhausted = (
        continuation_run_count_before >= continuation_budget_run_limit
    )
    continuation_budget_objective_exhausted = (
        continuation_objective_count_before >= continuation_budget_objective_limit
    )
    continuation_budget_lane_exhausted = (
        continuation_lane_count_before >= continuation_budget_lane_limit
    )
    continuation_budget_branch_exhausted = bool(
        continuation_budget_branch_applicable
        and continuation_branch_count_before >= continuation_budget_branch_limit
    )
    continuation_branch_budget_status = "available"
    continuation_branch_budget_decision = "allow_under_branch_ceiling"
    continuation_branch_budget_reason = "branch_budget_available"
    if not continuation_budget_branch_applicable:
        continuation_branch_budget_status = "not_applicable"
        continuation_branch_budget_decision = "not_applicable"
        continuation_branch_budget_reason = "branch_budget_not_applicable"
    elif continuation_budget_branch_exhausted:
        continuation_branch_budget_status = "exhausted"
        continuation_branch_budget_decision = "deny_branch_ceiling_exhausted"
        continuation_branch_budget_reason = "branch_budget_exhausted"
    continuation_branch_budget_reason_codes = (
        _normalize_continuation_branch_budget_reason_codes(
            [continuation_branch_budget_reason]
        )
    )
    continuation_budget_exhausted = bool(
        continuation_budget_run_exhausted
        or continuation_budget_objective_exhausted
        or continuation_budget_lane_exhausted
        or continuation_budget_branch_exhausted
    )
    continuation_budget_status = "available"
    continuation_budget_decision = "allow_under_budget"
    continuation_budget_reason = "budget_available"
    if not continuation_budget_truth_sufficient:
        continuation_budget_status = "insufficient_truth"
        continuation_budget_decision = "deny_insufficient_truth"
        continuation_budget_reason = "budget_insufficient_truth"
    elif continuation_budget_lane_exhausted:
        continuation_budget_status = "exhausted"
        continuation_budget_decision = "deny_budget_exhausted"
        continuation_budget_reason = "budget_lane_exhausted"
    elif continuation_budget_objective_exhausted:
        continuation_budget_status = "exhausted"
        continuation_budget_decision = "deny_budget_exhausted"
        continuation_budget_reason = "budget_objective_exhausted"
    elif continuation_budget_run_exhausted:
        continuation_budget_status = "exhausted"
        continuation_budget_decision = "deny_budget_exhausted"
        continuation_budget_reason = "budget_run_exhausted"
    elif continuation_budget_branch_exhausted:
        continuation_budget_status = "exhausted"
        continuation_budget_decision = "deny_budget_exhausted"
        continuation_budget_reason = "budget_branch_exhausted"
    continuation_budget_reason_codes = _normalize_continuation_budget_reason_codes(
        [continuation_budget_reason]
    )
    continuation_repeated = continuation_run_count_before >= 1
    continuation_no_progress_truth_sufficient = bool(
        loop_hardening_validity in {"valid", "partial"}
        and loop_hardening_status not in {"", "insufficient_truth", "unknown"}
    )
    continuation_no_progress_signal_detected = bool(
        loop_no_progress_stop_required
        or loop_no_progress_status == "confirmed"
        or (loop_no_progress_detected and loop_no_progress_status in {"confirmed", "suspected"})
    )
    continuation_no_progress_stop_required = bool(
        continuation_repeated
        and continuation_no_progress_truth_sufficient
        and continuation_no_progress_signal_detected
    )
    continuation_failure_bucket_truth_sufficient = bool(
        failure_bucketing_validity == "valid"
        and failure_bucketing_status == "classified"
    )
    continuation_failure_bucket_unsafe = (
        failure_bucketing_primary_bucket in _CONTINUATION_UNSAFE_FAILURE_BUCKETS
    )
    continuation_failure_bucket_denied = bool(
        continuation_failure_bucket_truth_sufficient
        and continuation_failure_bucket_unsafe
    )
    continuation_repair_playbook_truth_sufficient = bool(
        continuation_failure_bucket_truth_sufficient
        and failure_bucketing_primary_bucket not in {"", "unknown"}
    )
    continuation_repair_playbook_mapping = _CONTINUATION_REPAIR_PLAYBOOKS.get(
        failure_bucketing_primary_bucket,
        {},
    )
    continuation_repair_playbook_supported_bucket = bool(
        continuation_repair_playbook_mapping
    )
    continuation_repair_playbook_selected = bool(
        continuation_repair_playbook_truth_sufficient
        and continuation_repair_playbook_supported_bucket
    )
    continuation_repair_playbook_selection_status = "not_selected"
    continuation_repair_playbook_reason = "playbook_bucket_unsupported"
    if not continuation_repair_playbook_truth_sufficient:
        continuation_repair_playbook_selection_status = "insufficient_truth"
        continuation_repair_playbook_reason = "playbook_insufficient_truth"
    elif continuation_repair_playbook_selected:
        continuation_repair_playbook_selection_status = "selected"
        continuation_repair_playbook_reason = "playbook_selected"
    continuation_repair_playbook_class = _normalize_text(
        continuation_repair_playbook_mapping.get("repair_plan_class"),
        default="no_plan",
    )
    if continuation_repair_playbook_class not in REPAIR_PLAN_CLASSES:
        continuation_repair_playbook_class = "no_plan"
    continuation_repair_playbook_candidate_action = _normalize_text(
        continuation_repair_playbook_mapping.get("repair_plan_candidate_action"),
        default="no_action",
    )
    if continuation_repair_playbook_candidate_action not in REPAIR_PLAN_CANDIDATE_ACTIONS:
        continuation_repair_playbook_candidate_action = "no_action"
    if not continuation_repair_playbook_selected:
        continuation_repair_playbook_class = "no_plan"
        continuation_repair_playbook_candidate_action = "no_action"
    continuation_repair_playbook_reason_codes = (
        _normalize_continuation_repair_playbook_reason_codes(
            [continuation_repair_playbook_reason]
        )
    )
    continuation_next_step_truth_sufficient = bool(
        objective_id
        and approved_restart_validity == "valid"
        and approval_safety_validity == "valid"
        and approval_response_validity == "valid"
    )
    continuation_next_step_target = "none"
    continuation_next_step_reason = "next_step_not_selected"
    continuation_next_step_selection_status = "not_selected"
    continuation_next_step_retry_eligible = bool(
        approved_next_direction in {"same_lane_retry", "repair_retry"}
        or proposed_next_direction in {"same_lane_retry", "repair_retry"}
    )
    continuation_next_step_replan_eligible = bool(
        approved_next_direction == "replan_preparation"
        or proposed_next_direction == "replan_preparation"
    )
    continuation_next_step_truth_insufficiency_explicit = bool(
        failure_bucketing_primary_bucket in {"truth_missing", "external_truth_pending"}
        or failure_bucketing_status == "insufficient_truth"
        or failure_bucketing_validity == "insufficient_truth"
    )
    continuation_next_step_supported_repair_eligible = bool(
        continuation_repair_playbook_selected
    )
    if not continuation_next_step_truth_sufficient:
        continuation_next_step_selection_status = "insufficient_truth"
        continuation_next_step_reason = "next_step_insufficient_truth"
    elif continuation_next_step_supported_repair_eligible:
        continuation_next_step_selection_status = "selected"
        continuation_next_step_target = "supported_repair"
        continuation_next_step_reason = "next_step_selected_supported_repair"
    elif continuation_next_step_truth_insufficiency_explicit:
        continuation_next_step_selection_status = "selected"
        continuation_next_step_target = "truth_gather"
        continuation_next_step_reason = "next_step_selected_truth_gather"
    elif continuation_next_step_replan_eligible:
        continuation_next_step_selection_status = "selected"
        continuation_next_step_target = "replan"
        continuation_next_step_reason = "next_step_selected_replan"
    elif continuation_next_step_retry_eligible:
        continuation_next_step_selection_status = "selected"
        continuation_next_step_target = "retry"
        continuation_next_step_reason = "next_step_selected_retry"
    continuation_next_step_selected = (
        continuation_next_step_selection_status == "selected"
    )
    if continuation_next_step_target not in _CONTINUATION_NEXT_STEP_TARGETS:
        continuation_next_step_target = "none"
        continuation_next_step_selection_status = "not_selected"
        continuation_next_step_selected = False
        continuation_next_step_reason = "next_step_not_selected"
    continuation_next_step_reason_codes = (
        _normalize_continuation_next_step_reason_codes(
            [continuation_next_step_reason]
        )
    )
    supported_repair_target_selected = continuation_next_step_target == "supported_repair"
    supported_repair_execution_attempted = False
    supported_repair_executed = False
    supported_repair_verification_passed = False
    supported_repair_verification_failed = False
    supported_repair_execution_status = "not_selected"
    supported_repair_execution_reason = "repair_not_selected"
    supported_repair_execution_qualified = bool(
        supported_repair_target_selected
        and continuation_repair_playbook_selected
        and continuation_repair_playbook_class
        in _SUPPORTED_REPAIR_EXECUTABLE_PLAYBOOK_CLASSES
        and continuation_repair_playbook_candidate_action
        in _SUPPORTED_REPAIR_EXECUTABLE_CANDIDATE_ACTIONS
    )
    if supported_repair_target_selected:
        if supported_repair_execution_qualified:
            supported_repair_execution_status = "not_executed_launch_failed"
            supported_repair_execution_reason = "repair_launch_failed"
        else:
            supported_repair_execution_status = "not_executed_qualification_failed"
            supported_repair_execution_reason = "repair_qualification_failed"

    execution_status = "not_executed"
    execution_reason = "restart_not_executed"
    execution_reason_codes: list[str] = []
    automatic_restart_attempted = False
    automatic_restart_executed = False
    automatic_restart_count = 0
    restart_target_pr_id = ""
    restart_launch_pr_id = ""
    restart_run_id = ""
    restart_result_status = "not_attempted"
    restart_stdout_path = ""
    restart_stderr_path = ""
    restart_artifacts_count = 0
    restart_error = ""

    invalid_approved_restart_posture = bool(
        approved_restart_validity != "valid"
        or approved_restart_status != "restart_allowed"
        or not restart_allowed
        or restart_blocked
        or restart_held
        or restart_manual_followup
        or restart_decision not in _APPROVED_RESTART_ALLOWED_DECISIONS
        or response_decision_class == "unsupported"
        or restart_decision in {"block_restart", "manual_followup_only", "hold_restart"}
    )
    response_not_approved = bool(
        response_decision_class != "approved"
        or response_command_normalized in {"HOLD", "REJECT"}
        or approval_response_status != "response_accepted"
    )
    safety_status_clear = approval_safety_status in {"safe_to_deliver", "not_applicable"}

    if invalid_approved_restart_posture:
        execution_reason = "invalid_approved_restart_posture"
    elif response_not_approved:
        execution_reason = "response_not_approved"
    elif safety_duplicate_pending:
        execution_reason = "safety_duplicate_pending"
    elif safety_cooldown_active:
        execution_reason = "safety_cooldown_active"
    elif safety_loop_suspected:
        execution_reason = "safety_loop_suspected"
    elif safety_delivery_blocked:
        execution_reason = "safety_delivery_blocked"
    elif safety_delivery_deferred:
        execution_reason = "safety_delivery_deferred"
    elif not safety_status_clear:
        execution_reason = "safety_not_clear"
    elif not continuation_budget_truth_sufficient:
        execution_reason = "continuation_budget_insufficient_truth"
    elif continuation_budget_exhausted:
        execution_reason = "continuation_budget_exhausted"
        if approval_skip_applied:
            approval_skip_applied = False
            approval_skip_human_gate_preserved = True
    elif continuation_no_progress_stop_required:
        execution_reason = "continuation_no_progress_stop"
        if approval_skip_applied:
            approval_skip_applied = False
            approval_skip_human_gate_preserved = True
    elif continuation_failure_bucket_denied:
        execution_reason = "failure_bucket_continuation_denied"
        if approval_skip_applied:
            approval_skip_applied = False
            approval_skip_human_gate_preserved = True
    elif not continuation_next_step_selected:
        execution_reason = "continuation_next_step_not_selected"
        if approval_skip_applied:
            approval_skip_applied = False
            approval_skip_human_gate_preserved = True
    elif supported_repair_target_selected and not supported_repair_execution_qualified:
        execution_reason = "supported_repair_qualification_failed"
        if approval_skip_applied:
            approval_skip_applied = False
            approval_skip_human_gate_preserved = True
    else:
        target_entry = _select_approved_restart_target_unit(manifest_units)
        if not isinstance(target_entry, Mapping):
            execution_reason = "restart_target_missing"
            if supported_repair_target_selected:
                supported_repair_execution_status = "not_executed_launch_failed"
                supported_repair_execution_reason = "repair_launch_failed"
        else:
            restart_target_pr_id = _normalize_text(target_entry.get("pr_id"), default="")
            target_prompt_path_text = _normalize_text(
                target_entry.get("compiled_prompt_path"),
                default="",
            )
            target_prompt_path = (
                Path(target_prompt_path_text) if target_prompt_path_text else None
            )
            target_work_dir = target_prompt_path.parent if target_prompt_path else Path("")
            if (
                not restart_target_pr_id
                or not target_prompt_path_text
                or target_prompt_path is None
                or not target_prompt_path.exists()
                or not target_work_dir.exists()
            ):
                execution_reason = "restart_target_missing"
                if supported_repair_target_selected:
                    supported_repair_execution_status = "not_executed_launch_failed"
                    supported_repair_execution_reason = "repair_launch_failed"
            else:
                restart_launch_pr_id = f"{restart_target_pr_id}__approved_restart_once"
                try:
                    if supported_repair_target_selected:
                        supported_repair_execution_attempted = True
                    launch_response = dict(
                        adapter.launch_job(
                            job_id=_normalize_text(run_id, default=""),
                            pr_id=restart_launch_pr_id,
                            prompt_path=str(target_prompt_path),
                            work_dir=str(target_work_dir),
                            metadata={
                                "automatic_restart_execution": True,
                                "automatic_restart_limit": 1,
                                "automatic_restart_direction": approved_next_direction,
                                "automatic_restart_target_lane": approved_target_lane,
                                "automatic_restart_action_class": approved_action_class,
                                "automatic_restart_decision": restart_decision,
                                "automatic_restart_response_command": response_command_normalized,
                            },
                        )
                    )
                except Exception as exc:  # pragma: no cover - deterministic fallback
                    restart_error = _normalize_text(str(exc), default="automatic_restart_launch_failed")
                    execution_reason = "restart_launch_failed"
                    if supported_repair_target_selected:
                        supported_repair_execution_status = "not_executed_launch_failed"
                        supported_repair_execution_reason = "repair_launch_failed"
                else:
                    automatic_restart_attempted = True
                    restart_run_id = _normalize_text(launch_response.get("run_id"), default="")
                    if not restart_run_id:
                        execution_reason = "restart_launch_failed"
                        if supported_repair_target_selected:
                            supported_repair_execution_status = "not_executed_launch_failed"
                            supported_repair_execution_reason = "repair_launch_failed"
                    else:
                        status_response = dict(adapter.poll_status(run_id=restart_run_id))
                        artifact_response = dict(adapter.collect_artifacts(run_id=restart_run_id))
                        restart_result_status = _normalize_text(
                            status_response.get("status"),
                            default="failed",
                        ).lower()
                        if restart_result_status not in {
                            "completed",
                            "failed",
                            "timed_out",
                            "not_started",
                            "running",
                        }:
                            restart_result_status = "failed"
                        restart_stdout_path = _normalize_text(
                            artifact_response.get("stdout_path"),
                            default="",
                        )
                        restart_stderr_path = _normalize_text(
                            artifact_response.get("stderr_path"),
                            default="",
                        )
                        restart_artifacts_count = len(
                            artifact_response.get("artifacts")
                            if isinstance(artifact_response.get("artifacts"), list)
                            else []
                        )
                        automatic_restart_executed = True
                        automatic_restart_count = 1
                        execution_status = "executed"
                        execution_reason = "restart_executed_once"
                        if supported_repair_target_selected:
                            supported_repair_executed = True
                            if restart_result_status == "completed":
                                supported_repair_verification_passed = True
                                supported_repair_execution_status = (
                                    "executed_verification_passed"
                                )
                                supported_repair_execution_reason = (
                                    "repair_verification_passed"
                                )
                            else:
                                supported_repair_verification_failed = True
                                supported_repair_execution_status = (
                                    "executed_verification_failed"
                                )
                                supported_repair_execution_reason = (
                                    "repair_verification_failed"
                                )
                                execution_reason = "supported_repair_verification_failed"
                                if approval_skip_applied:
                                    approval_skip_applied = False
                                    approval_skip_human_gate_preserved = True

    if execution_status != "executed":
        automatic_restart_executed = False
        automatic_restart_count = 0
        restart_result_status = "not_attempted"
        if supported_repair_target_selected and execution_reason in {
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
        }:
            supported_repair_execution_status = "not_executed_precheck_blocked"
            supported_repair_execution_reason = "repair_precheck_blocked"
    continuation_increment = 1 if execution_status == "executed" else 0
    continuation_run_count_after = continuation_run_count_before + continuation_increment
    continuation_objective_count_after = (
        continuation_objective_count_before + continuation_increment
    )
    continuation_lane_count_after = continuation_lane_count_before + continuation_increment
    continuation_branch_increment = (
        continuation_increment if continuation_budget_branch_applicable else 0
    )
    continuation_branch_count_after = (
        continuation_branch_count_before + continuation_branch_increment
    )
    continuation_retry_count_after = prior_continuation_retry_count + (
        continuation_increment if continuation_budget_branch_type == "retry" else 0
    )
    continuation_replan_count_after = prior_continuation_replan_count + (
        continuation_increment if continuation_budget_branch_type == "replan" else 0
    )
    continuation_truth_gather_count_after = prior_continuation_truth_gather_count + (
        continuation_increment if continuation_budget_branch_type == "truth_gather" else 0
    )
    continuation_budget_run_remaining = max(
        0,
        continuation_budget_run_limit - continuation_run_count_after,
    )
    continuation_budget_objective_remaining = max(
        0,
        continuation_budget_objective_limit - continuation_objective_count_after,
    )
    continuation_budget_lane_remaining = max(
        0,
        continuation_budget_lane_limit - continuation_lane_count_after,
    )
    continuation_budget_branch_remaining = max(
        0,
        continuation_budget_branch_limit - continuation_branch_count_after,
    )

    execution_reason_codes = _normalize_approved_restart_execution_reason_codes(
        [execution_reason]
    )
    supported_repair_execution_reason_codes = (
        _normalize_supported_repair_execution_reason_codes(
            [supported_repair_execution_reason]
        )
    )
    manual_only_posture_active = bool(
        failure_bucketing_primary_bucket == "manual_only"
        or approval_reason_class == "manual_only"
        or fleet_restart_decision == "manual_only"
        or proposed_next_direction == "manual_review_preparation"
    )
    next_step_unresolved = bool(
        execution_reason == "continuation_next_step_not_selected"
        and continuation_budget_truth_sufficient
        and safety_status_clear
        and not continuation_budget_exhausted
        and not continuation_no_progress_stop_required
        and not continuation_failure_bucket_denied
    )
    supported_repair_escalation_failure = bool(
        supported_repair_execution_status == "executed_verification_failed"
    )
    final_human_review_required = False
    final_human_review_gate_status = "not_required"
    final_human_review_reason = "final_review_not_required"
    if manual_only_posture_active:
        final_human_review_required = True
        final_human_review_gate_status = "required"
        final_human_review_reason = "final_review_manual_only_posture"
    elif high_risk_posture:
        final_human_review_required = True
        final_human_review_gate_status = "required"
        final_human_review_reason = "final_review_high_risk_posture"
    elif supported_repair_escalation_failure:
        final_human_review_required = True
        final_human_review_gate_status = "required"
        final_human_review_reason = "final_review_supported_repair_verification_failed"
    elif next_step_unresolved and (manual_review_required or approval_required):
        final_human_review_required = True
        final_human_review_gate_status = "required"
        final_human_review_reason = "final_review_next_step_unresolved"
    elif manual_review_required:
        final_human_review_required = True
        final_human_review_gate_status = "required"
        final_human_review_reason = "final_review_explicit_manual_review_required"
    final_human_review_reason_codes = _normalize_final_human_review_gate_reason_codes(
        [final_human_review_reason]
    )
    project_planning_summary_status = "insufficient_truth"
    project_planning_summary_reason = "planning_summary_insufficient_truth"
    project_planning_summary_available = False
    project_planning_control_posture = "unknown"
    planning_summary_truth_sufficient = bool(
        objective_id
        and (
            final_human_review_required
            or (
                continuation_budget_status in {"available", "exhausted"}
                and continuation_branch_budget_status
                in _CONTINUATION_BUDGET_BRANCH_STATUSES
                and continuation_next_step_selection_status in {"selected", "not_selected"}
                and failure_bucketing_status not in {"", "unknown", "insufficient_truth"}
            )
        )
    )
    if planning_summary_truth_sufficient:
        project_planning_summary_status = "available"
        project_planning_summary_reason = "planning_summary_compiled"
        project_planning_summary_available = True
        if final_human_review_required:
            project_planning_control_posture = "human_review_required"
        elif execution_status == "executed":
            project_planning_control_posture = "automation_executed"
        elif execution_status == "not_executed":
            project_planning_control_posture = "automation_blocked"
    project_planning_summary_reason_codes = (
        _normalize_project_planning_summary_reason_codes(
            [project_planning_summary_reason]
        )
    )
    project_planning_summary_compact: dict[str, Any] = {}
    if project_planning_summary_available:
        project_planning_summary_compact = {
            "objective_id": objective_id,
            "control_posture": project_planning_control_posture,
            "automatic_restart_execution_status": execution_status,
            "automatic_restart_execution_reason": execution_reason_codes[0],
            "continuation_budget_status": continuation_budget_status,
            "continuation_budget_branch_status": continuation_branch_budget_status,
            "continuation_failure_bucket": failure_bucketing_primary_bucket,
            "continuation_failure_bucket_denied": bool(continuation_failure_bucket_denied),
            "continuation_repair_playbook_selection_status": (
                continuation_repair_playbook_selection_status
            ),
            "continuation_next_step_selection_status": continuation_next_step_selection_status,
            "continuation_next_step_target": continuation_next_step_target,
            "supported_repair_execution_status": supported_repair_execution_status,
            "supported_repair_verification_failed": bool(
                supported_repair_verification_failed
            ),
            "final_human_review_required": bool(final_human_review_required),
            "final_human_review_reason": final_human_review_reason_codes[0],
        }
    project_roadmap_status = "insufficient_truth"
    project_roadmap_reason = "roadmap_insufficient_truth"
    project_roadmap_available = False
    project_roadmap_items: list[dict[str, Any]] = []
    project_roadmap_item_count = 0
    project_pr_slicing_status = "insufficient_truth"
    project_pr_slicing_reason = "pr_slices_insufficient_truth"
    project_pr_slicing_available = False
    project_pr_slices: list[dict[str, Any]] = []
    project_pr_slice_count = 0
    project_pr_one_pr_size_decision = "not_available"
    project_pr_prioritization_mode = "insufficient_truth"
    if project_planning_summary_available:
        project_roadmap_status = "available"
        project_roadmap_reason = "roadmap_compiled"
        project_roadmap_available = True
        project_roadmap_items = _build_project_roadmap_items(
            project_planning_summary_compact=project_planning_summary_compact,
            planning_source_status="planning_summary_available",
        )
        project_roadmap_item_count = len(project_roadmap_items)
        project_pr_slicing_status = "available"
        project_pr_slicing_reason = "pr_slices_compiled"
        project_pr_slicing_available = True
        project_pr_slices = _build_project_pr_slices(project_roadmap_items)
        project_pr_slice_count = len(project_pr_slices)
        project_pr_one_pr_size_decision = "single_theme_single_pr"
        project_pr_prioritization_mode = "blocked_last_narrow_first_prereq_first"
    project_roadmap_reason_codes = _normalize_project_roadmap_reason_codes(
        [project_roadmap_reason]
    )
    project_pr_slicing_reason_codes = _normalize_project_pr_slicing_reason_codes(
        [project_pr_slicing_reason]
    )
    implementation_prompt_payload = _build_implementation_prompt_payload(
        objective_id=objective_id,
        project_planning_summary_status=project_planning_summary_status,
        project_pr_slicing_status=project_pr_slicing_status,
        project_pr_one_pr_size_decision=project_pr_one_pr_size_decision,
        project_pr_slices=project_pr_slices,
    )
    implementation_prompt_status = _normalize_text(
        implementation_prompt_payload.get("prompt_status"),
        default="insufficient_truth",
    )
    implementation_prompt_available = bool(
        implementation_prompt_payload.get("prompt_available", False)
    )
    implementation_prompt_reason_codes = _normalize_implementation_prompt_reason_codes(
        list(implementation_prompt_payload.get("prompt_reason_codes", []))
    )
    implementation_prompt_payload["prompt_reason"] = implementation_prompt_reason_codes[0]
    implementation_prompt_payload["prompt_reason_codes"] = implementation_prompt_reason_codes
    prior_queue_processed_slice_ids = _serialize_required_signals(
        _normalize_string_list(
            prior_approved_restart_execution.get("project_pr_queue_processed_slice_ids")
        )
    )
    project_pr_queue_state = _build_project_pr_queue_state(
        project_pr_slicing_status=project_pr_slicing_status,
        project_pr_slices=project_pr_slices,
        implementation_prompt_payload=implementation_prompt_payload,
        prior_processed_slice_ids=prior_queue_processed_slice_ids,
    )
    project_pr_queue_status = _normalize_text(
        project_pr_queue_state.get("queue_status"),
        default="insufficient_truth",
    )
    project_pr_queue_reason_codes = _normalize_project_pr_queue_reason_codes(
        list(project_pr_queue_state.get("queue_reason_codes", []))
    )
    project_pr_queue_state["queue_reason"] = project_pr_queue_reason_codes[0]
    project_pr_queue_state["queue_reason_codes"] = project_pr_queue_reason_codes
    review_assimilation_state = _build_review_assimilation_state(
        queue_status=project_pr_queue_status,
        queue_reason=project_pr_queue_reason_codes[0],
        queue_handoff_prepared=bool(project_pr_queue_state.get("queue_handoff_prepared", False)),
        queue_handoff_payload=(
            dict(project_pr_queue_state.get("queue_handoff_payload", {}))
            if isinstance(project_pr_queue_state.get("queue_handoff_payload"), Mapping)
            else {}
        ),
        restart_result_status=restart_result_status,
        continuation_next_step_target=continuation_next_step_target,
        continuation_next_step_reason=continuation_next_step_reason_codes[0],
        continuation_next_step_truth_insufficiency_explicit=bool(
            continuation_next_step_truth_insufficiency_explicit
        ),
        final_human_review_required=bool(final_human_review_required),
        final_human_review_reason=final_human_review_reason_codes[0],
    )
    review_assimilation_status = _normalize_text(
        review_assimilation_state.get("review_assimilation_status"),
        default="insufficient_truth",
    )
    review_assimilation_action = _normalize_text(
        review_assimilation_state.get("review_assimilation_action"),
        default="none",
    )
    review_assimilation_reason_codes = _normalize_review_assimilation_reason_codes(
        list(review_assimilation_state.get("review_assimilation_reason_codes", []))
    )
    review_assimilation_state["review_assimilation_reason"] = (
        review_assimilation_reason_codes[0]
    )
    review_assimilation_state["review_assimilation_reason_codes"] = (
        review_assimilation_reason_codes
    )
    prior_self_healing_transition_count = _as_non_negative_int(
        prior_approved_restart_execution.get("self_healing_transition_count"),
        default=0,
    )
    self_healing_state = _build_bounded_self_healing_state(
        review_assimilation_status=review_assimilation_status,
        review_assimilation_action=review_assimilation_action,
        review_assimilation_available=bool(
            review_assimilation_state.get("review_assimilation_available", False)
        ),
        review_assimilation_reviewable=bool(
            review_assimilation_state.get("review_assimilation_reviewable", False)
        ),
        review_assimilation_queue_status=_normalize_text(
            review_assimilation_state.get("review_assimilation_queue_status"),
            default=project_pr_queue_status,
        ),
        continuation_next_step_truth_insufficiency_explicit=bool(
            continuation_next_step_truth_insufficiency_explicit
        ),
        supported_repair_execution_status=supported_repair_execution_status,
        continuation_repair_playbook_selected=bool(
            continuation_repair_playbook_selected
        ),
        continuation_repair_playbook_class=continuation_repair_playbook_class,
        continuation_repair_playbook_candidate_action=(
            continuation_repair_playbook_candidate_action
        ),
        final_human_review_required=bool(final_human_review_required),
        final_human_review_reason=final_human_review_reason_codes[0],
        continuation_budget_status=continuation_budget_status,
        continuation_branch_budget_status=continuation_branch_budget_status,
        continuation_no_progress_stop_required=bool(
            continuation_no_progress_stop_required
        ),
        continuation_failure_bucket_denied=bool(
            continuation_failure_bucket_denied
        ),
        safety_duplicate_pending=bool(safety_duplicate_pending),
        safety_cooldown_active=bool(safety_cooldown_active),
        safety_loop_suspected=bool(safety_loop_suspected),
        safety_delivery_blocked=bool(safety_delivery_blocked),
        safety_delivery_deferred=bool(safety_delivery_deferred),
        prior_self_healing_transition_count=prior_self_healing_transition_count,
        self_healing_chain_limit=_SELF_HEALING_CHAIN_LIMIT_DEFAULT,
        prior_continuation_retry_count=prior_continuation_retry_count,
        prior_continuation_replan_count=prior_continuation_replan_count,
        prior_continuation_truth_gather_count=prior_continuation_truth_gather_count,
        continuation_retry_limit=_as_non_negative_int(
            _CONTINUATION_BUDGET_BRANCH_LIMIT_DEFAULTS.get("retry", 0),
            default=0,
        ),
        continuation_replan_limit=_as_non_negative_int(
            _CONTINUATION_BUDGET_BRANCH_LIMIT_DEFAULTS.get("replan", 0),
            default=0,
        ),
        continuation_truth_gather_limit=_as_non_negative_int(
            _CONTINUATION_BUDGET_BRANCH_LIMIT_DEFAULTS.get("truth_gather", 0),
            default=0,
        ),
    )
    self_healing_status = _normalize_text(
        self_healing_state.get("self_healing_status"),
        default="insufficient_truth",
    )
    self_healing_reason_codes = _normalize_self_healing_reason_codes(
        list(self_healing_state.get("self_healing_reason_codes", []))
    )
    self_healing_state["self_healing_reason"] = self_healing_reason_codes[0]
    self_healing_state["self_healing_reason_codes"] = self_healing_reason_codes
    prior_long_running_replay_key = _normalize_text(
        prior_approved_restart_execution.get("long_running_replay_key"),
        default="",
    )
    prior_long_running_progress_signature = _normalize_text(
        prior_approved_restart_execution.get("long_running_progress_signature"),
        default="",
    )
    prior_long_running_stale_cycle_count = _as_non_negative_int(
        prior_approved_restart_execution.get("long_running_stale_cycle_count"),
        default=0,
    )
    prior_long_running_stuck_cycle_count = _as_non_negative_int(
        prior_approved_restart_execution.get("long_running_stuck_cycle_count"),
        default=0,
    )
    prior_long_running_watchdog_heartbeat_at = _normalize_text(
        prior_approved_restart_execution.get("long_running_watchdog_heartbeat_at"),
        default="",
    )
    project_pr_queue_processed_count = len(
        _normalize_string_list(
            project_pr_queue_state.get("queue_processed_slice_ids_after")
        )
    )
    long_running_state = _build_long_running_stability_state(
        objective_id=objective_id,
        queue_status=project_pr_queue_status,
        queue_selected_slice_id=_normalize_text(
            project_pr_queue_state.get("queue_selected_slice_id"),
            default="",
        ),
        queue_handoff_prepared=bool(
            project_pr_queue_state.get("queue_handoff_prepared", False)
        ),
        queue_processed_count=project_pr_queue_processed_count,
        review_assimilation_status=review_assimilation_status,
        review_assimilation_action=review_assimilation_action,
        review_assimilation_available=bool(
            review_assimilation_state.get("review_assimilation_available", False)
        ),
        self_healing_status=self_healing_status,
        self_healing_transition_target=_normalize_text(
            self_healing_state.get("self_healing_transition_target"),
            default="none",
        ),
        self_healing_transition_executed=bool(
            self_healing_state.get("self_healing_transition_executed", False)
        ),
        self_healing_human_fallback_preserved=bool(
            self_healing_state.get("self_healing_human_fallback_preserved", True)
        ),
        self_healing_chain_budget_remaining_after=_as_non_negative_int(
            self_healing_state.get("self_healing_chain_budget_remaining_after"),
            default=0,
        ),
        self_healing_transition_count_after=_as_non_negative_int(
            self_healing_state.get("self_healing_transition_count_after"),
            default=prior_self_healing_transition_count,
        ),
        final_human_review_required=bool(final_human_review_required),
        automatic_restart_executed=bool(automatic_restart_executed),
        automatic_continuation_run_count=continuation_run_count_after,
        prior_long_running_replay_key=prior_long_running_replay_key,
        prior_long_running_progress_signature=prior_long_running_progress_signature,
        prior_long_running_stale_cycle_count=prior_long_running_stale_cycle_count,
        prior_long_running_stuck_cycle_count=prior_long_running_stuck_cycle_count,
        prior_long_running_watchdog_heartbeat_at=prior_long_running_watchdog_heartbeat_at,
        now=now,
    )
    long_running_status = _normalize_text(
        long_running_state.get("long_running_stability_status"),
        default="insufficient_truth",
    )
    long_running_reason_codes = _normalize_long_running_reason_codes(
        list(long_running_state.get("long_running_reason_codes", []))
    )
    long_running_state["long_running_reason"] = long_running_reason_codes[0]
    long_running_state["long_running_reason_codes"] = long_running_reason_codes
    objective_compiler_state = _build_objective_done_compiler_state(
        objective_id=objective_id,
        project_planning_summary_status=project_planning_summary_status,
        project_pr_slicing_status=project_pr_slicing_status,
        project_pr_slice_count=project_pr_slice_count,
        project_pr_queue_status=project_pr_queue_status,
        project_pr_queue_reason=project_pr_queue_reason_codes[0],
        project_pr_queue_processed_slice_ids_after=_normalize_string_list(
            project_pr_queue_state.get("queue_processed_slice_ids_after")
        ),
        review_assimilation_reason=review_assimilation_reason_codes[0],
        self_healing_human_fallback_preserved=bool(
            self_healing_state.get("self_healing_human_fallback_preserved", True)
        ),
        long_running_stability_status=long_running_status,
        final_human_review_required=bool(final_human_review_required),
    )
    objective_compiler_status = _normalize_text(
        objective_compiler_state.get("objective_compiler_status"),
        default="insufficient_truth",
    )
    objective_compiler_reason_codes = _normalize_objective_compiler_reason_codes(
        list(objective_compiler_state.get("objective_compiler_reason_codes", []))
    )
    objective_compiler_state["objective_compiler_reason"] = (
        objective_compiler_reason_codes[0]
    )
    objective_compiler_state["objective_compiler_reason_codes"] = (
        objective_compiler_reason_codes
    )
    objective_done_criteria_status = _normalize_text(
        objective_compiler_state.get("objective_done_criteria_status"),
        default="insufficient_truth",
    )
    if objective_done_criteria_status not in _OBJECTIVE_DONE_CRITERIA_STATUSES:
        objective_done_criteria_status = "insufficient_truth"
    objective_stop_criteria_status = _normalize_text(
        objective_compiler_state.get("objective_stop_criteria_status"),
        default="insufficient_truth",
    )
    if objective_stop_criteria_status not in _OBJECTIVE_STOP_CRITERIA_STATUSES:
        objective_stop_criteria_status = "insufficient_truth"
    objective_completion_posture = _normalize_text(
        objective_compiler_state.get("objective_completion_posture"),
        default="objective_insufficient_truth",
    )
    if objective_completion_posture not in _OBJECTIVE_COMPLETION_POSTURES:
        objective_completion_posture = "objective_insufficient_truth"
    objective_scope_drift_status = _normalize_text(
        objective_compiler_state.get("objective_scope_drift_status"),
        default="insufficient_truth",
    )
    if objective_scope_drift_status not in _OBJECTIVE_SCOPE_DRIFT_STATUSES:
        objective_scope_drift_status = "insufficient_truth"
    project_autonomy_budget_state = _build_project_autonomy_budget_state(
        project_planning_summary_status=project_planning_summary_status,
        objective_compiler_status=objective_compiler_status,
        objective_completion_posture=objective_completion_posture,
        final_human_review_required=bool(final_human_review_required),
        high_risk_posture=bool(high_risk_posture),
        continuation_budget_truth_sufficient=bool(continuation_budget_truth_sufficient),
        continuation_budget_status=continuation_budget_status,
        continuation_budget_run_exhausted=bool(continuation_budget_run_exhausted),
        continuation_budget_objective_exhausted=bool(continuation_budget_objective_exhausted),
        continuation_budget_run_limit=continuation_budget_run_limit,
        continuation_budget_objective_limit=continuation_budget_objective_limit,
        continuation_budget_run_remaining=continuation_budget_run_remaining,
        continuation_budget_objective_remaining=continuation_budget_objective_remaining,
        continuation_budget_branch_type=continuation_budget_branch_type,
        continuation_budget_branch_status=continuation_branch_budget_status,
        continuation_budget_branch_exhausted=bool(continuation_budget_branch_exhausted),
        continuation_budget_branch_limit=continuation_budget_branch_limit,
        continuation_budget_branch_remaining=continuation_budget_branch_remaining,
    )
    project_autonomy_budget_status = _normalize_text(
        project_autonomy_budget_state.get("project_autonomy_budget_status"),
        default="insufficient_truth",
    )
    if project_autonomy_budget_status not in _PROJECT_AUTONOMY_BUDGET_STATUSES:
        project_autonomy_budget_status = "insufficient_truth"
    project_priority_posture = _normalize_text(
        project_autonomy_budget_state.get("project_priority_posture"),
        default="insufficient_truth",
    )
    if project_priority_posture not in _PROJECT_PRIORITY_POSTURES:
        project_priority_posture = "insufficient_truth"
    project_high_risk_defer_posture = _normalize_text(
        project_autonomy_budget_state.get("project_high_risk_defer_posture"),
        default="insufficient_truth",
    )
    if project_high_risk_defer_posture not in _PROJECT_HIGH_RISK_DEFER_POSTURES:
        project_high_risk_defer_posture = "insufficient_truth"
    project_run_budget_posture = _normalize_text(
        project_autonomy_budget_state.get("project_run_budget_posture"),
        default="insufficient_truth",
    )
    if project_run_budget_posture not in _PROJECT_BUDGET_POSTURES:
        project_run_budget_posture = "insufficient_truth"
    project_objective_budget_posture = _normalize_text(
        project_autonomy_budget_state.get("project_objective_budget_posture"),
        default="insufficient_truth",
    )
    if project_objective_budget_posture not in _PROJECT_BUDGET_POSTURES:
        project_objective_budget_posture = "insufficient_truth"
    project_pr_retry_budget_posture = _normalize_text(
        project_autonomy_budget_state.get("project_pr_retry_budget_posture"),
        default="insufficient_truth",
    )
    if project_pr_retry_budget_posture not in _PROJECT_PR_RETRY_BUDGET_POSTURES:
        project_pr_retry_budget_posture = "insufficient_truth"
    project_autonomy_budget_reason_codes = (
        _normalize_project_autonomy_budget_reason_codes(
            list(project_autonomy_budget_state.get("project_autonomy_budget_reason_codes", []))
        )
    )
    project_autonomy_budget_state["project_autonomy_budget_reason"] = (
        project_autonomy_budget_reason_codes[0]
    )
    project_autonomy_budget_state["project_autonomy_budget_reason_codes"] = (
        project_autonomy_budget_reason_codes
    )
    project_quality_gate_state = _build_project_quality_gate_state(
        project_planning_summary_status=project_planning_summary_status,
        project_pr_slicing_status=project_pr_slicing_status,
        implementation_prompt_status=implementation_prompt_status,
        implementation_prompt_payload=implementation_prompt_payload,
        project_pr_queue_status=project_pr_queue_status,
        review_assimilation_status=review_assimilation_status,
        review_assimilation_action=review_assimilation_action,
        self_healing_status=self_healing_status,
        long_running_stability_status=long_running_status,
        objective_compiler_status=objective_compiler_status,
        objective_completion_posture=objective_completion_posture,
        objective_scope_drift_detected=bool(
            objective_compiler_state.get("objective_scope_drift_detected", False)
        ),
        project_autonomy_budget_status=project_autonomy_budget_status,
        project_priority_posture=project_priority_posture,
        project_run_budget_posture=project_run_budget_posture,
        project_objective_budget_posture=project_objective_budget_posture,
        project_pr_retry_budget_posture=project_pr_retry_budget_posture,
        project_high_risk_defer_posture=project_high_risk_defer_posture,
        continuation_failure_bucket_denied=bool(continuation_failure_bucket_denied),
        continuation_no_progress_stop_required=bool(
            continuation_no_progress_stop_required
        ),
        continuation_next_step_selection_status=continuation_next_step_selection_status,
        continuation_next_step_target=continuation_next_step_target,
        supported_repair_execution_status=supported_repair_execution_status,
        final_human_review_required=bool(final_human_review_required),
    )
    project_quality_gate_status = _normalize_text(
        project_quality_gate_state.get("project_quality_gate_status"),
        default="insufficient_truth",
    )
    if project_quality_gate_status not in _PROJECT_QUALITY_GATE_STATUSES:
        project_quality_gate_status = "insufficient_truth"
    project_quality_gate_posture = _normalize_text(
        project_quality_gate_state.get("project_quality_gate_posture"),
        default="insufficient_truth",
    )
    if project_quality_gate_posture not in _PROJECT_QUALITY_GATE_POSTURES:
        project_quality_gate_posture = "insufficient_truth"
    project_quality_gate_changed_area_class = _normalize_text(
        project_quality_gate_state.get("project_quality_gate_changed_area_class"),
        default="unknown",
    )
    if (
        project_quality_gate_changed_area_class
        not in _PROJECT_QUALITY_GATE_CHANGED_AREA_CLASSES
    ):
        project_quality_gate_changed_area_class = "unknown"
    project_quality_gate_risk_level = _normalize_text(
        project_quality_gate_state.get("project_quality_gate_risk_level"),
        default="insufficient_truth",
    )
    if project_quality_gate_risk_level not in _PROJECT_QUALITY_GATE_RISK_LEVELS:
        project_quality_gate_risk_level = "insufficient_truth"
    project_quality_gate_reason_codes = _normalize_project_quality_gate_reason_codes(
        list(project_quality_gate_state.get("project_quality_gate_reason_codes", []))
    )
    project_quality_gate_state["project_quality_gate_reason"] = (
        project_quality_gate_reason_codes[0]
    )
    project_quality_gate_state["project_quality_gate_reason_codes"] = (
        project_quality_gate_reason_codes
    )
    project_merge_branch_lifecycle_state = _build_project_merge_branch_lifecycle_state(
        project_quality_gate_status=project_quality_gate_status,
        project_quality_gate_posture=project_quality_gate_posture,
        project_quality_gate_merge_ready=bool(
            project_quality_gate_state.get("project_quality_gate_merge_ready", False)
        ),
        project_quality_gate_retry_needed=bool(
            project_quality_gate_state.get("project_quality_gate_retry_needed", False)
        ),
        project_quality_gate_high_risk=bool(
            project_quality_gate_state.get("project_quality_gate_high_risk", False)
        ),
        objective_compiler_status=objective_compiler_status,
        objective_completion_posture=objective_completion_posture,
        project_autonomy_budget_status=project_autonomy_budget_status,
        project_priority_posture=project_priority_posture,
        project_high_risk_defer_posture=project_high_risk_defer_posture,
        project_pr_queue_status=project_pr_queue_status,
        project_pr_queue_processed_count=project_pr_queue_processed_count,
        review_assimilation_status=review_assimilation_status,
        review_assimilation_action=review_assimilation_action,
        self_healing_status=self_healing_status,
        long_running_stability_status=long_running_status,
        final_human_review_required=bool(final_human_review_required),
        final_human_review_gate_status=final_human_review_gate_status,
        continuation_failure_bucket_denied=bool(continuation_failure_bucket_denied),
        continuation_no_progress_stop_required=bool(
            continuation_no_progress_stop_required
        ),
        supported_repair_execution_status=supported_repair_execution_status,
    )
    project_merge_branch_lifecycle_status = _normalize_text(
        project_merge_branch_lifecycle_state.get("project_merge_branch_lifecycle_status"),
        default="insufficient_truth",
    )
    if (
        project_merge_branch_lifecycle_status
        not in _PROJECT_MERGE_BRANCH_LIFECYCLE_STATUSES
    ):
        project_merge_branch_lifecycle_status = "insufficient_truth"
    project_merge_ready_posture = _normalize_text(
        project_merge_branch_lifecycle_state.get("project_merge_ready_posture"),
        default="insufficient_truth",
    )
    if project_merge_ready_posture not in _PROJECT_MERGE_READY_POSTURES:
        project_merge_ready_posture = "insufficient_truth"
    project_branch_cleanup_candidate_posture = _normalize_text(
        project_merge_branch_lifecycle_state.get(
            "project_branch_cleanup_candidate_posture"
        ),
        default="insufficient_truth",
    )
    if project_branch_cleanup_candidate_posture not in _PROJECT_BRANCH_CANDIDATE_POSTURES:
        project_branch_cleanup_candidate_posture = "insufficient_truth"
    project_branch_quarantine_candidate_posture = _normalize_text(
        project_merge_branch_lifecycle_state.get(
            "project_branch_quarantine_candidate_posture"
        ),
        default="insufficient_truth",
    )
    if (
        project_branch_quarantine_candidate_posture
        not in _PROJECT_BRANCH_CANDIDATE_POSTURES
    ):
        project_branch_quarantine_candidate_posture = "insufficient_truth"
    project_local_main_sync_posture = _normalize_text(
        project_merge_branch_lifecycle_state.get("project_local_main_sync_posture"),
        default="insufficient_truth",
    )
    if project_local_main_sync_posture not in _PROJECT_LOCAL_MAIN_SYNC_POSTURES:
        project_local_main_sync_posture = "insufficient_truth"
    project_merge_branch_lifecycle_reason_codes = (
        _normalize_project_merge_branch_lifecycle_reason_codes(
            list(
                project_merge_branch_lifecycle_state.get(
                    "project_merge_branch_lifecycle_reason_codes",
                    [],
                )
            )
        )
    )
    project_merge_branch_lifecycle_state["project_merge_branch_lifecycle_reason"] = (
        project_merge_branch_lifecycle_reason_codes[0]
    )
    project_merge_branch_lifecycle_state["project_merge_branch_lifecycle_reason_codes"] = (
        project_merge_branch_lifecycle_reason_codes
    )
    project_failure_memory_state = _build_project_failure_memory_state(
        project_merge_branch_lifecycle_status=project_merge_branch_lifecycle_status,
        project_branch_quarantine_candidate=bool(
            project_merge_branch_lifecycle_state.get(
                "project_branch_quarantine_candidate",
                False,
            )
        ),
        failure_bucketing_status=failure_bucketing_status,
        failure_bucketing_validity=failure_bucketing_validity,
        failure_bucketing_primary_bucket=failure_bucketing_primary_bucket,
        continuation_next_step_selection_status=continuation_next_step_selection_status,
        continuation_next_step_target=continuation_next_step_target,
        continuation_no_progress_stop_required=bool(
            continuation_no_progress_stop_required
        ),
        continuation_failure_bucket_denied=bool(continuation_failure_bucket_denied),
        review_assimilation_status=review_assimilation_status,
        review_assimilation_action=review_assimilation_action,
        self_healing_status=self_healing_status,
        supported_repair_execution_status=supported_repair_execution_status,
        execution_status=execution_status,
        execution_reason=execution_reason,
        restart_result_status=restart_result_status,
        final_human_review_required=bool(final_human_review_required),
        prior_retry_failure_count=_as_non_negative_int(
            prior_approved_restart_execution.get(
                "project_failure_memory_retry_failure_count"
            ),
            default=0,
        ),
        prior_repair_failure_count=_as_non_negative_int(
            prior_approved_restart_execution.get(
                "project_failure_memory_repair_failure_count"
            ),
            default=0,
        ),
        prior_review_issue_count=_as_non_negative_int(
            prior_approved_restart_execution.get(
                "project_failure_memory_review_issue_count"
            ),
            default=0,
        ),
        prior_failure_bucket_recurrence_count=_as_non_negative_int(
            prior_approved_restart_execution.get(
                "project_failure_memory_failure_bucket_recurrence_count"
            ),
            default=0,
        ),
        prior_failure_bucket_value=_normalize_text(
            prior_approved_restart_execution.get(
                "project_failure_memory_last_failure_bucket"
            ),
            default="unknown",
        ),
    )
    project_failure_memory_status = _normalize_text(
        project_failure_memory_state.get("project_failure_memory_status"),
        default="insufficient_truth",
    )
    if project_failure_memory_status not in _PROJECT_FAILURE_MEMORY_STATUSES:
        project_failure_memory_status = "insufficient_truth"
    project_failure_memory_suppression_posture = _normalize_text(
        project_failure_memory_state.get("project_failure_memory_suppression_posture"),
        default="insufficient_truth",
    )
    if (
        project_failure_memory_suppression_posture
        not in _PROJECT_FAILURE_MEMORY_SUPPRESSION_POSTURES
    ):
        project_failure_memory_suppression_posture = "insufficient_truth"
    project_failure_memory_reason_codes = (
        _normalize_project_failure_memory_reason_codes(
            list(project_failure_memory_state.get("project_failure_memory_reason_codes", []))
        )
    )
    project_failure_memory_state["project_failure_memory_reason"] = (
        project_failure_memory_reason_codes[0]
    )
    project_failure_memory_state["project_failure_memory_reason_codes"] = (
        project_failure_memory_reason_codes
    )
    project_external_boundary_state = _build_project_external_boundary_state(
        project_failure_memory_status=project_failure_memory_status,
        project_failure_memory_suppression_posture=project_failure_memory_suppression_posture,
        project_failure_memory_suppression_active=bool(
            project_failure_memory_state.get(
                "project_failure_memory_suppression_active",
                False,
            )
        ),
        project_merge_branch_lifecycle_status=project_merge_branch_lifecycle_status,
        project_merge_ready_posture=project_merge_ready_posture,
        project_branch_quarantine_candidate_posture=project_branch_quarantine_candidate_posture,
        project_local_main_sync_posture=project_local_main_sync_posture,
        project_quality_gate_status=project_quality_gate_status,
        project_quality_gate_posture=project_quality_gate_posture,
        project_quality_gate_risk_level=project_quality_gate_risk_level,
        project_pr_queue_status=project_pr_queue_status,
        project_autonomy_budget_status=project_autonomy_budget_status,
        project_priority_posture=project_priority_posture,
        long_running_stability_status=long_running_status,
        supported_repair_execution_status=supported_repair_execution_status,
        execution_reason=execution_reason,
        final_human_review_required=bool(final_human_review_required),
        final_human_review_gate_status=final_human_review_gate_status,
        manual_only_posture_active=bool(manual_only_posture_active),
        fleet_manual_review_required=bool(fleet_manual_review_required),
        approval_reason_class=approval_reason_class,
    )
    project_external_boundary_status = _normalize_text(
        project_external_boundary_state.get("project_external_boundary_status"),
        default="insufficient_truth",
    )
    if project_external_boundary_status not in _PROJECT_EXTERNAL_BOUNDARY_STATUSES:
        project_external_boundary_status = "insufficient_truth"
    project_external_dependency_posture = _normalize_text(
        project_external_boundary_state.get("project_external_dependency_posture"),
        default="insufficient_truth",
    )
    if (
        project_external_dependency_posture
        not in _PROJECT_EXTERNAL_DEPENDENCY_POSTURES
    ):
        project_external_dependency_posture = "insufficient_truth"
    project_external_manual_only_posture = _normalize_text(
        project_external_boundary_state.get("project_external_manual_only_posture"),
        default="insufficient_truth",
    )
    if project_external_manual_only_posture not in _PROJECT_EXTERNAL_BOUNDARY_POSTURES:
        project_external_manual_only_posture = "insufficient_truth"
    project_external_network_boundary_posture = _normalize_text(
        project_external_boundary_state.get("project_external_network_boundary_posture"),
        default="insufficient_truth",
    )
    if (
        project_external_network_boundary_posture
        not in _PROJECT_EXTERNAL_BOUNDARY_POSTURES
    ):
        project_external_network_boundary_posture = "insufficient_truth"
    project_external_ci_boundary_posture = _normalize_text(
        project_external_boundary_state.get("project_external_ci_boundary_posture"),
        default="insufficient_truth",
    )
    if project_external_ci_boundary_posture not in _PROJECT_EXTERNAL_BOUNDARY_POSTURES:
        project_external_ci_boundary_posture = "insufficient_truth"
    project_external_secrets_boundary_posture = _normalize_text(
        project_external_boundary_state.get("project_external_secrets_boundary_posture"),
        default="insufficient_truth",
    )
    if (
        project_external_secrets_boundary_posture
        not in _PROJECT_EXTERNAL_BOUNDARY_POSTURES
    ):
        project_external_secrets_boundary_posture = "insufficient_truth"
    project_external_github_boundary_posture = _normalize_text(
        project_external_boundary_state.get("project_external_github_boundary_posture"),
        default="insufficient_truth",
    )
    if (
        project_external_github_boundary_posture
        not in _PROJECT_EXTERNAL_BOUNDARY_POSTURES
    ):
        project_external_github_boundary_posture = "insufficient_truth"
    project_external_api_boundary_posture = _normalize_text(
        project_external_boundary_state.get("project_external_api_boundary_posture"),
        default="insufficient_truth",
    )
    if project_external_api_boundary_posture not in _PROJECT_EXTERNAL_BOUNDARY_POSTURES:
        project_external_api_boundary_posture = "insufficient_truth"
    project_external_boundary_reason_codes = (
        _normalize_project_external_boundary_reason_codes(
            list(
                project_external_boundary_state.get(
                    "project_external_boundary_reason_codes",
                    [],
                )
            )
        )
    )
    project_external_boundary_state["project_external_boundary_reason"] = (
        project_external_boundary_reason_codes[0]
    )
    project_external_boundary_state["project_external_boundary_reason_codes"] = (
        project_external_boundary_reason_codes
    )
    project_human_escalation_state = _build_project_human_escalation_state(
        final_human_review_gate_status=final_human_review_gate_status,
        final_human_review_required=bool(final_human_review_required),
        final_human_review_reason=final_human_review_reason_codes[0],
        objective_compiler_status=objective_compiler_status,
        objective_completion_posture=objective_completion_posture,
        objective_scope_drift_status=objective_scope_drift_status,
        project_autonomy_budget_status=project_autonomy_budget_status,
        project_priority_posture=project_priority_posture,
        project_high_risk_defer_posture=project_high_risk_defer_posture,
        project_run_budget_posture=project_run_budget_posture,
        project_objective_budget_posture=project_objective_budget_posture,
        project_pr_retry_budget_posture=project_pr_retry_budget_posture,
        project_quality_gate_status=project_quality_gate_status,
        project_quality_gate_risk_level=project_quality_gate_risk_level,
        project_quality_gate_high_risk=bool(
            project_quality_gate_state.get("project_quality_gate_high_risk", False)
        ),
        project_merge_branch_lifecycle_status=project_merge_branch_lifecycle_status,
        project_branch_quarantine_candidate_posture=project_branch_quarantine_candidate_posture,
        project_failure_memory_status=project_failure_memory_status,
        project_failure_memory_suppression_posture=project_failure_memory_suppression_posture,
        project_failure_memory_suppression_active=bool(
            project_failure_memory_state.get(
                "project_failure_memory_suppression_active",
                False,
            )
        ),
        project_failure_memory_retry_failure_count=_as_non_negative_int(
            project_failure_memory_state.get("project_failure_memory_retry_failure_count"),
            default=0,
        ),
        project_failure_memory_repair_failure_count=_as_non_negative_int(
            project_failure_memory_state.get("project_failure_memory_repair_failure_count"),
            default=0,
        ),
        project_failure_memory_review_issue_count=_as_non_negative_int(
            project_failure_memory_state.get("project_failure_memory_review_issue_count"),
            default=0,
        ),
        project_failure_memory_failure_bucket_recurrence_count=_as_non_negative_int(
            project_failure_memory_state.get(
                "project_failure_memory_failure_bucket_recurrence_count"
            ),
            default=0,
        ),
        project_external_boundary_status=project_external_boundary_status,
        project_external_dependency_posture=project_external_dependency_posture,
        project_external_manual_only_posture=project_external_manual_only_posture,
        project_external_manual_only_required=bool(
            project_external_boundary_state.get(
                "project_external_manual_only_required",
                False,
            )
        ),
        long_running_stability_status=long_running_status,
        supported_repair_execution_status=supported_repair_execution_status,
        manual_only_posture_active=bool(manual_only_posture_active),
        fleet_manual_review_required=bool(fleet_manual_review_required),
    )
    project_human_escalation_status = _normalize_text(
        project_human_escalation_state.get("project_human_escalation_status"),
        default="insufficient_truth",
    )
    if project_human_escalation_status not in _PROJECT_HUMAN_ESCALATION_STATUSES:
        project_human_escalation_status = "insufficient_truth"
    project_human_escalation_posture = _normalize_text(
        project_human_escalation_state.get("project_human_escalation_posture"),
        default="insufficient_truth",
    )
    if (
        project_human_escalation_posture
        not in _PROJECT_HUMAN_ESCALATION_POSTURES
    ):
        project_human_escalation_posture = "insufficient_truth"
    project_human_escalation_reason_codes = (
        _normalize_project_human_escalation_reason_codes(
            list(
                project_human_escalation_state.get(
                    "project_human_escalation_reason_codes",
                    [],
                )
            )
        )
    )
    project_human_escalation_state["project_human_escalation_reason"] = (
        project_human_escalation_reason_codes[0]
    )
    project_human_escalation_state["project_human_escalation_reason_codes"] = (
        project_human_escalation_reason_codes
    )
    project_architecture_risk_posture = _normalize_text(
        project_human_escalation_state.get("project_architecture_risk_posture"),
        default="insufficient_truth",
    )
    if (
        project_architecture_risk_posture
        not in _PROJECT_HUMAN_ESCALATION_RISK_POSTURES
    ):
        project_architecture_risk_posture = "insufficient_truth"
    project_scope_risk_posture = _normalize_text(
        project_human_escalation_state.get("project_scope_risk_posture"),
        default="insufficient_truth",
    )
    if project_scope_risk_posture not in _PROJECT_HUMAN_ESCALATION_RISK_POSTURES:
        project_scope_risk_posture = "insufficient_truth"
    project_external_risk_posture = _normalize_text(
        project_human_escalation_state.get("project_external_risk_posture"),
        default="insufficient_truth",
    )
    if (
        project_external_risk_posture
        not in _PROJECT_HUMAN_ESCALATION_RISK_POSTURES
    ):
        project_external_risk_posture = "insufficient_truth"
    project_budget_risk_posture = _normalize_text(
        project_human_escalation_state.get("project_budget_risk_posture"),
        default="insufficient_truth",
    )
    if project_budget_risk_posture not in _PROJECT_HUMAN_ESCALATION_RISK_POSTURES:
        project_budget_risk_posture = "insufficient_truth"
    project_repeated_failure_risk_posture = _normalize_text(
        project_human_escalation_state.get("project_repeated_failure_risk_posture"),
        default="insufficient_truth",
    )
    if (
        project_repeated_failure_risk_posture
        not in _PROJECT_HUMAN_ESCALATION_RISK_POSTURES
    ):
        project_repeated_failure_risk_posture = "insufficient_truth"
    project_manual_only_risk_posture = _normalize_text(
        project_human_escalation_state.get("project_manual_only_risk_posture"),
        default="insufficient_truth",
    )
    if (
        project_manual_only_risk_posture
        not in _PROJECT_HUMAN_ESCALATION_RISK_POSTURES
    ):
        project_manual_only_risk_posture = "insufficient_truth"
    project_approval_notification_state = _build_project_approval_notification_state(
        approval_required=bool(approval_required),
        approval_email_status=approval_email_status,
        approval_email_validity=approval_email_validity,
        approval_priority=approval_priority,
        approval_reason_class=approval_reason_class,
        proposed_next_direction=proposed_next_direction,
        delivery_mode=approval_delivery_mode,
        delivery_outcome=approval_delivery_outcome,
        approval_response_status=approval_response_status,
        approval_response_validity=approval_response_validity,
        response_received=bool(response_received),
        response_decision_class=response_decision_class,
        project_human_escalation_status=project_human_escalation_status,
        project_human_escalation_posture=project_human_escalation_posture,
        project_human_escalation_required=bool(
            project_human_escalation_state.get("project_human_escalation_required", False)
        ),
        project_human_escalation_reason=project_human_escalation_reason_codes[0],
        project_architecture_risk_posture=project_architecture_risk_posture,
        project_scope_risk_posture=project_scope_risk_posture,
        project_external_risk_posture=project_external_risk_posture,
        project_budget_risk_posture=project_budget_risk_posture,
        project_repeated_failure_risk_posture=project_repeated_failure_risk_posture,
        project_manual_only_risk_posture=project_manual_only_risk_posture,
        project_external_manual_only_posture=project_external_manual_only_posture,
    )
    project_approval_notification_status = _normalize_text(
        project_approval_notification_state.get("project_approval_notification_status"),
        default="insufficient_truth",
    )
    if (
        project_approval_notification_status
        not in _PROJECT_APPROVAL_NOTIFICATION_STATUSES
    ):
        project_approval_notification_status = "insufficient_truth"
    project_approval_notification_ready_posture = _normalize_text(
        project_approval_notification_state.get(
            "project_approval_notification_ready_posture"
        ),
        default="insufficient_truth",
    )
    if (
        project_approval_notification_ready_posture
        not in _PROJECT_APPROVAL_NOTIFICATION_READY_POSTURES
    ):
        project_approval_notification_ready_posture = "insufficient_truth"
    project_approval_reply_required_posture = _normalize_text(
        project_approval_notification_state.get(
            "project_approval_reply_required_posture"
        ),
        default="insufficient_truth",
    )
    if (
        project_approval_reply_required_posture
        not in _PROJECT_APPROVAL_REPLY_REQUIRED_POSTURES
    ):
        project_approval_reply_required_posture = "insufficient_truth"
    project_approval_channel_posture = _normalize_text(
        project_approval_notification_state.get("project_approval_channel_posture"),
        default="insufficient_truth",
    )
    if project_approval_channel_posture not in _PROJECT_APPROVAL_CHANNEL_POSTURES:
        project_approval_channel_posture = "insufficient_truth"
    project_approval_mobile_summary_posture = _normalize_text(
        project_approval_notification_state.get(
            "project_approval_mobile_summary_posture"
        ),
        default="insufficient_truth",
    )
    if (
        project_approval_mobile_summary_posture
        not in _PROJECT_APPROVAL_MOBILE_SUMMARY_POSTURES
    ):
        project_approval_mobile_summary_posture = "insufficient_truth"
    project_approval_notification_reason_codes = (
        _normalize_project_approval_notification_reason_codes(
            list(
                project_approval_notification_state.get(
                    "project_approval_notification_reason_codes",
                    [],
                )
            )
        )
    )
    project_approval_notification_state["project_approval_notification_reason"] = (
        project_approval_notification_reason_codes[0]
    )
    project_approval_notification_state["project_approval_notification_reason_codes"] = (
        project_approval_notification_reason_codes
    )
    project_multi_objective_state = _build_project_multi_objective_state(
        objective_id=objective_id,
        objective_compiler_status=objective_compiler_status,
        objective_completion_posture=objective_completion_posture,
        project_priority_posture=project_priority_posture,
        project_high_risk_defer_posture=project_high_risk_defer_posture,
        project_run_budget_posture=project_run_budget_posture,
        project_objective_budget_posture=project_objective_budget_posture,
        project_pr_retry_budget_posture=project_pr_retry_budget_posture,
        project_merge_branch_lifecycle_status=project_merge_branch_lifecycle_status,
        project_merge_ready_posture=project_merge_ready_posture,
        project_branch_quarantine_candidate_posture=project_branch_quarantine_candidate_posture,
        project_human_escalation_status=project_human_escalation_status,
        project_human_escalation_required=bool(
            project_human_escalation_state.get("project_human_escalation_required", False)
        ),
        project_approval_notification_status=project_approval_notification_status,
        project_approval_notification_ready_posture=(
            project_approval_notification_ready_posture
        ),
        project_approval_reply_required_posture=project_approval_reply_required_posture,
        project_pr_queue_status=project_pr_queue_status,
        project_pr_queue_selected_slice_id=_normalize_text(
            project_pr_queue_state.get("queue_selected_slice_id"),
            default="",
        ),
        project_pr_queue_processed_slice_ids_after=_normalize_string_list(
            project_pr_queue_state.get("queue_processed_slice_ids_after")
        ),
        project_pr_queue_item_count=_as_non_negative_int(
            project_pr_queue_state.get("queue_item_count"),
            default=0,
        ),
        project_pr_queue_runnable_count=_as_non_negative_int(
            project_pr_queue_state.get("queue_runnable_count"),
            default=0,
        ),
        project_pr_queue_blocked_count=_as_non_negative_int(
            project_pr_queue_state.get("queue_blocked_count"),
            default=0,
        ),
        project_pr_queue_handoff_prepared=bool(
            project_pr_queue_state.get("queue_handoff_prepared", False)
        ),
    )
    project_multi_objective_status = _normalize_text(
        project_multi_objective_state.get("project_multi_objective_status"),
        default="insufficient_truth",
    )
    if project_multi_objective_status not in _PROJECT_MULTI_OBJECTIVE_STATUSES:
        project_multi_objective_status = "insufficient_truth"
    project_active_objective_selection_posture = _normalize_text(
        project_multi_objective_state.get("project_active_objective_selection_posture"),
        default="insufficient_truth",
    )
    if (
        project_active_objective_selection_posture
        not in _PROJECT_ACTIVE_OBJECTIVE_SELECTION_POSTURES
    ):
        project_active_objective_selection_posture = "insufficient_truth"
    project_blocked_objective_deferral_posture = _normalize_text(
        project_multi_objective_state.get("project_blocked_objective_deferral_posture"),
        default="insufficient_truth",
    )
    if (
        project_blocked_objective_deferral_posture
        not in _PROJECT_BLOCKED_OBJECTIVE_DEFERRAL_POSTURES
    ):
        project_blocked_objective_deferral_posture = "insufficient_truth"
    project_resumable_queue_ordering_posture = _normalize_text(
        project_multi_objective_state.get("project_resumable_queue_ordering_posture"),
        default="insufficient_truth",
    )
    if (
        project_resumable_queue_ordering_posture
        not in _PROJECT_RESUMABLE_QUEUE_ORDERING_POSTURES
    ):
        project_resumable_queue_ordering_posture = "insufficient_truth"
    project_multi_objective_reason_codes = _normalize_project_multi_objective_reason_codes(
        list(project_multi_objective_state.get("project_multi_objective_reason_codes", []))
    )
    project_multi_objective_state["project_multi_objective_reason"] = (
        project_multi_objective_reason_codes[0]
    )
    project_multi_objective_state["project_multi_objective_reason_codes"] = (
        project_multi_objective_reason_codes
    )
    if project_planning_summary_available:
        project_planning_summary_compact.update(
            {
                "project_roadmap_status": project_roadmap_status,
                "project_roadmap_item_count": project_roadmap_item_count,
                "project_pr_slicing_status": project_pr_slicing_status,
                "project_pr_slice_count": project_pr_slice_count,
                "project_pr_one_pr_size_decision": project_pr_one_pr_size_decision,
                "implementation_prompt_status": implementation_prompt_status,
                "implementation_prompt_available": implementation_prompt_available,
                "implementation_prompt_reason": implementation_prompt_reason_codes[0],
                "project_pr_queue_status": project_pr_queue_status,
                "project_pr_queue_reason": project_pr_queue_reason_codes[0],
                "project_pr_queue_selected_slice_id": _normalize_text(
                    project_pr_queue_state.get("queue_selected_slice_id"),
                    default="",
                ),
                "project_pr_queue_handoff_prepared": bool(
                    project_pr_queue_state.get("queue_handoff_prepared", False)
                ),
                "review_assimilation_status": review_assimilation_status,
                "review_assimilation_action": review_assimilation_action,
                "review_assimilation_reason": review_assimilation_reason_codes[0],
                "self_healing_status": self_healing_status,
                "self_healing_transition_target": _normalize_text(
                    self_healing_state.get("self_healing_transition_target"),
                    default="none",
                ),
                "self_healing_reason": self_healing_reason_codes[0],
                "long_running_stability_status": long_running_status,
                "long_running_reason": long_running_reason_codes[0],
                "objective_compiler_status": objective_compiler_status,
                "objective_completion_posture": objective_completion_posture,
                "objective_done_criteria_status": objective_done_criteria_status,
                "objective_stop_criteria_status": objective_stop_criteria_status,
                "objective_scope_drift_status": objective_scope_drift_status,
                "project_autonomy_budget_status": project_autonomy_budget_status,
                "project_priority_posture": project_priority_posture,
                "project_high_risk_defer_posture": project_high_risk_defer_posture,
                "project_run_budget_posture": project_run_budget_posture,
                "project_objective_budget_posture": project_objective_budget_posture,
                "project_pr_retry_budget_posture": project_pr_retry_budget_posture,
                "project_quality_gate_status": project_quality_gate_status,
                "project_quality_gate_posture": project_quality_gate_posture,
                "project_quality_gate_recommended_count": _as_non_negative_int(
                    project_quality_gate_state.get("project_quality_gate_recommended_count"),
                    default=0,
                ),
                "project_quality_gate_changed_area_class": project_quality_gate_changed_area_class,
                "project_quality_gate_risk_level": project_quality_gate_risk_level,
                "project_merge_branch_lifecycle_status": project_merge_branch_lifecycle_status,
                "project_merge_ready_posture": project_merge_ready_posture,
                "project_branch_cleanup_candidate_posture": project_branch_cleanup_candidate_posture,
                "project_branch_quarantine_candidate_posture": project_branch_quarantine_candidate_posture,
                "project_local_main_sync_posture": project_local_main_sync_posture,
                "project_failure_memory_status": project_failure_memory_status,
                "project_failure_memory_suppression_posture": (
                    project_failure_memory_suppression_posture
                ),
                "project_failure_memory_suppression_active": bool(
                    project_failure_memory_state.get(
                        "project_failure_memory_suppression_active",
                        False,
                    )
                ),
                "project_external_boundary_status": project_external_boundary_status,
                "project_external_dependency_posture": project_external_dependency_posture,
                "project_external_manual_only_posture": project_external_manual_only_posture,
                "project_external_network_boundary_posture": project_external_network_boundary_posture,
                "project_external_github_boundary_posture": project_external_github_boundary_posture,
                "project_human_escalation_status": project_human_escalation_status,
                "project_human_escalation_posture": project_human_escalation_posture,
                "project_human_escalation_required": bool(
                    project_human_escalation_state.get(
                        "project_human_escalation_required",
                        False,
                    )
                ),
                "project_architecture_risk_posture": project_architecture_risk_posture,
                "project_scope_risk_posture": project_scope_risk_posture,
                "project_external_risk_posture": project_external_risk_posture,
                "project_budget_risk_posture": project_budget_risk_posture,
                "project_repeated_failure_risk_posture": (
                    project_repeated_failure_risk_posture
                ),
                "project_manual_only_risk_posture": project_manual_only_risk_posture,
                "project_approval_notification_status": project_approval_notification_status,
                "project_approval_notification_ready_posture": (
                    project_approval_notification_ready_posture
                ),
                "project_approval_reply_required_posture": (
                    project_approval_reply_required_posture
                ),
                "project_approval_channel_posture": project_approval_channel_posture,
                "project_approval_mobile_summary_posture": (
                    project_approval_mobile_summary_posture
                ),
                "project_multi_objective_status": project_multi_objective_status,
                "project_active_objective_selection_posture": (
                    project_active_objective_selection_posture
                ),
                "project_blocked_objective_deferral_posture": (
                    project_blocked_objective_deferral_posture
                ),
                "project_resumable_queue_ordering_posture": (
                    project_resumable_queue_ordering_posture
                ),
            }
        )

    supporting_compact_truth_refs = _serialize_required_signals(
        [
            "approved_restart_contract.approved_restart_status" if approved_restart_status else "",
            "approved_restart_contract.restart_decision" if restart_decision else "",
            "approval_response_contract.approval_response_status" if approval_response_status else "",
            "approval_response_contract.response_decision_class" if response_decision_class else "",
            "approval_safety_contract.approval_safety_status" if approval_safety_status else "",
            "approval_safety_contract.approval_safety_decision" if approval_safety_decision else "",
            "approval_email_delivery_contract.approval_email_status" if approval_email_status else "",
            "approval_email_delivery_contract.proposed_next_direction" if proposed_next_direction else "",
            "fleet_safety_control_contract.fleet_safety_status" if fleet_safety_status else "",
            "approval_runtime_rules_contract.direction_rule_mode" if runtime_rules_mode else "",
            "failure_bucketing_hardening_contract.primary_failure_bucket"
            if failure_bucketing_primary_bucket
            else "",
            "loop_hardening_contract.no_progress_status" if loop_no_progress_status else "",
            "approved_restart_execution_contract.project_planning_summary_status"
            if project_planning_summary_status
            else "",
            "approved_restart_execution_contract.project_roadmap_status"
            if project_roadmap_status
            else "",
            "approved_restart_execution_contract.implementation_prompt_status"
            if implementation_prompt_status
            else "",
            "approved_restart_execution_contract.project_pr_queue_status"
            if project_pr_queue_status
            else "",
            "approved_restart_execution_contract.review_assimilation_status"
            if review_assimilation_status
            else "",
            "approved_restart_execution_contract.self_healing_status"
            if self_healing_status
            else "",
            "approved_restart_execution_contract.long_running_stability_status"
            if long_running_status
            else "",
            "approved_restart_execution_contract.objective_compiler_status"
            if objective_compiler_status
            else "",
            "approved_restart_execution_contract.project_autonomy_budget_status"
            if project_autonomy_budget_status
            else "",
            "approved_restart_execution_contract.project_quality_gate_status"
            if project_quality_gate_status
            else "",
            "approved_restart_execution_contract.project_merge_branch_lifecycle_status"
            if project_merge_branch_lifecycle_status
            else "",
            "approved_restart_execution_contract.project_failure_memory_status"
            if project_failure_memory_status
            else "",
            "approved_restart_execution_contract.project_external_boundary_status"
            if project_external_boundary_status
            else "",
            "approved_restart_execution_contract.project_human_escalation_status"
            if project_human_escalation_status
            else "",
            "approved_restart_execution_contract.project_approval_notification_status"
            if project_approval_notification_status
            else "",
            "approved_restart_execution_contract.project_multi_objective_status"
            if project_multi_objective_status
            else "",
        ]
    )

    return {
        "schema_version": _APPROVED_RESTART_EXECUTION_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "automatic_restart_execution_status": (
            execution_status
            if execution_status in _APPROVED_RESTART_EXECUTION_STATUSES
            else "not_executed"
        ),
        "automatic_restart_execution_reason": execution_reason_codes[0],
        "automatic_restart_execution_reason_codes": execution_reason_codes,
        "automatic_restart_attempted": bool(automatic_restart_attempted),
        "automatic_restart_executed": bool(automatic_restart_executed),
        "automatic_restart_count": automatic_restart_count,
        "automatic_restart_limit": 1,
        "automatic_restart_additional_execution_blocked": True,
        "automatic_restart_chained": False,
        "automatic_restart_target_pr_id": restart_target_pr_id,
        "automatic_restart_launch_pr_id": restart_launch_pr_id,
        "automatic_restart_run_id": restart_run_id,
        "automatic_restart_result_status": restart_result_status,
        "automatic_restart_stdout_path": restart_stdout_path,
        "automatic_restart_stderr_path": restart_stderr_path,
        "automatic_restart_artifacts_count": restart_artifacts_count,
        "automatic_restart_error": restart_error,
        "automatic_restart_triggered_at": _iso_now(now) if automatic_restart_attempted else "",
        "dry_run": bool(dry_run),
        "approved_restart_status": approved_restart_status,
        "approved_restart_validity": approved_restart_validity,
        "restart_decision": restart_decision,
        "approved_next_direction": approved_next_direction,
        "approved_target_lane": approved_target_lane,
        "approved_action_class": approved_action_class,
        "approval_response_status": approval_response_status,
        "response_decision_class": response_decision_class,
        "response_command_normalized": response_command_normalized,
        "approval_safety_status": approval_safety_status,
        "approval_safety_decision": approval_safety_decision,
        "approval_pending_duplicate": bool(
            approval_safety.get("approval_pending_duplicate", False)
        ),
        "approval_cooldown_active": bool(
            approval_safety.get("approval_cooldown_active", False)
        ),
        "approval_loop_suspected": bool(
            approval_safety.get("approval_loop_suspected", False)
        ),
        "approval_delivery_blocked_by_safety": bool(
            approval_safety.get("approval_delivery_blocked_by_safety", False)
        ),
        "approval_delivery_deferred_by_safety": bool(
            approval_safety.get("approval_delivery_deferred_by_safety", False)
        ),
        "approval_skip_gate_status": (
            approval_skip_gate_status
            if approval_skip_gate_status in _APPROVAL_SKIP_GATE_STATUSES
            else "approval_required"
        ),
        "approval_skip_gate_decision": (
            approval_skip_gate_decision
            if approval_skip_gate_decision in _APPROVAL_SKIP_GATE_DECISIONS
            else "require_human_approval"
        ),
        "approval_skip_allowed": bool(approval_skip_allowed),
        "approval_skip_applied": bool(approval_skip_applied),
        "approval_skip_human_gate_preserved": bool(approval_skip_human_gate_preserved),
        "approval_skip_bounded_once": True,
        "approval_skip_continuation_limit": 1,
        "approval_skip_reason": approval_skip_reason_codes[0],
        "approval_skip_reason_codes": approval_skip_reason_codes,
        "approval_skip_supported_direction": bool(supported_skip_direction),
        "approval_skip_safety_clear": bool(safety_clear),
        "approval_skip_truth_sufficient": bool(not invalid_or_insufficient_truth),
        "approval_skip_manual_review_required": bool(manual_review_required),
        "approval_skip_high_risk_detected": bool(high_risk_posture),
        "approval_skip_effective_response_command": _normalize_text(
            approval_skip_effective_command,
            default="",
        ),
        "approval_skip_effective_restart_decision": _normalize_text(
            approval_skip_effective_restart_decision,
            default="",
        ),
        "approval_skip_effective_next_direction": _normalize_text(
            approval_skip_effective_next_direction,
            default="",
        ),
        "approval_skip_effective_target_lane": _normalize_text(
            approval_skip_effective_target_lane,
            default="",
        ),
        "approval_skip_effective_action_class": _normalize_text(
            approval_skip_effective_action_class,
            default="",
        ),
        "continuation_budget_schema_version": _CONTINUATION_BUDGET_SCHEMA_VERSION,
        "continuation_budget_status": (
            continuation_budget_status
            if continuation_budget_status in _CONTINUATION_BUDGET_STATUSES
            else "insufficient_truth"
        ),
        "continuation_budget_decision": (
            continuation_budget_decision
            if continuation_budget_decision in _CONTINUATION_BUDGET_DECISIONS
            else "deny_insufficient_truth"
        ),
        "continuation_budget_reason": continuation_budget_reason_codes[0],
        "continuation_budget_reason_codes": continuation_budget_reason_codes,
        "continuation_budget_truth_sufficient": bool(continuation_budget_truth_sufficient),
        "continuation_budget_exhausted": bool(continuation_budget_exhausted),
        "continuation_budget_run_exhausted": bool(continuation_budget_run_exhausted),
        "continuation_budget_objective_exhausted": bool(continuation_budget_objective_exhausted),
        "continuation_budget_lane_exhausted": bool(continuation_budget_lane_exhausted),
        "continuation_budget_run_limit": continuation_budget_run_limit,
        "continuation_budget_objective_limit": continuation_budget_objective_limit,
        "continuation_budget_lane_limit": continuation_budget_lane_limit,
        "continuation_budget_branch_type": (
            continuation_budget_branch_type
            if continuation_budget_branch_type in _CONTINUATION_BUDGET_BRANCH_TYPES
            else "unknown"
        ),
        "continuation_budget_branch_limit": continuation_budget_branch_limit,
        "continuation_budget_branch_status": (
            continuation_branch_budget_status
            if continuation_branch_budget_status in _CONTINUATION_BUDGET_BRANCH_STATUSES
            else "not_applicable"
        ),
        "continuation_budget_branch_decision": (
            continuation_branch_budget_decision
            if continuation_branch_budget_decision in _CONTINUATION_BUDGET_BRANCH_DECISIONS
            else "not_applicable"
        ),
        "continuation_budget_branch_reason": continuation_branch_budget_reason_codes[0],
        "continuation_budget_branch_reason_codes": continuation_branch_budget_reason_codes,
        "continuation_budget_branch_exhausted": bool(continuation_budget_branch_exhausted),
        "continuation_no_progress_repeated": bool(continuation_repeated),
        "continuation_no_progress_truth_sufficient": bool(
            continuation_no_progress_truth_sufficient
        ),
        "continuation_no_progress_signal_detected": bool(
            continuation_no_progress_signal_detected
        ),
        "continuation_no_progress_status": _normalize_text(
            loop_no_progress_status,
            default="unknown",
        ),
        "continuation_no_progress_stop_required": bool(
            continuation_no_progress_stop_required
        ),
        "continuation_failure_bucket_status": _normalize_text(
            failure_bucketing_status,
            default="unknown",
        ),
        "continuation_failure_bucket_validity": _normalize_text(
            failure_bucketing_validity,
            default="unknown",
        ),
        "continuation_failure_bucket": _normalize_text(
            failure_bucketing_primary_bucket,
            default="unknown",
        ),
        "continuation_failure_bucket_unsafe": bool(
            continuation_failure_bucket_unsafe
        ),
        "continuation_failure_bucket_denied": bool(
            continuation_failure_bucket_denied
        ),
        "continuation_repair_playbook_selection_status": (
            continuation_repair_playbook_selection_status
            if continuation_repair_playbook_selection_status
            in _CONTINUATION_REPAIR_PLAYBOOK_STATUSES
            else "insufficient_truth"
        ),
        "continuation_repair_playbook_selected": bool(
            continuation_repair_playbook_selected
        ),
        "continuation_repair_playbook_truth_sufficient": bool(
            continuation_repair_playbook_truth_sufficient
        ),
        "continuation_repair_playbook_supported_bucket": bool(
            continuation_repair_playbook_supported_bucket
        ),
        "continuation_repair_playbook_bucket": _normalize_text(
            failure_bucketing_primary_bucket,
            default="unknown",
        ),
        "continuation_repair_playbook_class": continuation_repair_playbook_class,
        "continuation_repair_playbook_candidate_action": (
            continuation_repair_playbook_candidate_action
        ),
        "continuation_repair_playbook_reason": continuation_repair_playbook_reason_codes[0],
        "continuation_repair_playbook_reason_codes": (
            continuation_repair_playbook_reason_codes
        ),
        "continuation_next_step_selection_status": (
            continuation_next_step_selection_status
            if continuation_next_step_selection_status
            in _CONTINUATION_NEXT_STEP_SELECTION_STATUSES
            else "insufficient_truth"
        ),
        "continuation_next_step_selected": bool(
            continuation_next_step_selected
        ),
        "continuation_next_step_target": (
            continuation_next_step_target
            if continuation_next_step_target in _CONTINUATION_NEXT_STEP_TARGETS
            else "none"
        ),
        "continuation_next_step_reason": continuation_next_step_reason_codes[0],
        "continuation_next_step_reason_codes": continuation_next_step_reason_codes,
        "continuation_next_step_truth_sufficient": bool(
            continuation_next_step_truth_sufficient
        ),
        "continuation_next_step_truth_insufficiency_explicit": bool(
            continuation_next_step_truth_insufficiency_explicit
        ),
        "continuation_next_step_supported_repair_eligible": bool(
            continuation_next_step_supported_repair_eligible
        ),
        "continuation_next_step_replan_eligible": bool(
            continuation_next_step_replan_eligible
        ),
        "continuation_next_step_retry_eligible": bool(
            continuation_next_step_retry_eligible
        ),
        "supported_repair_execution_status": (
            supported_repair_execution_status
            if supported_repair_execution_status
            in _SUPPORTED_REPAIR_EXECUTION_STATUSES
            else "not_selected"
        ),
        "supported_repair_execution_reason": supported_repair_execution_reason_codes[0],
        "supported_repair_execution_reason_codes": (
            supported_repair_execution_reason_codes
        ),
        "supported_repair_execution_attempted": bool(
            supported_repair_execution_attempted
        ),
        "supported_repair_execution_qualified": bool(
            supported_repair_execution_qualified
        ),
        "supported_repair_executed": bool(
            supported_repair_executed
        ),
        "supported_repair_verification_passed": bool(
            supported_repair_verification_passed
        ),
        "supported_repair_verification_failed": bool(
            supported_repair_verification_failed
        ),
        "final_human_review_gate_status": (
            final_human_review_gate_status
            if final_human_review_gate_status in _FINAL_HUMAN_REVIEW_GATE_STATUSES
            else "not_required"
        ),
        "final_human_review_required": bool(
            final_human_review_required
        ),
        "final_human_review_reason": final_human_review_reason_codes[0],
        "final_human_review_reason_codes": final_human_review_reason_codes,
        "final_human_gate_preserved": bool(
            final_human_review_required
        ),
        "project_planning_summary_status": (
            project_planning_summary_status
            if project_planning_summary_status in _PROJECT_PLANNING_SUMMARY_STATUSES
            else "insufficient_truth"
        ),
        "project_planning_summary_available": bool(
            project_planning_summary_available
        ),
        "project_planning_summary_reason": project_planning_summary_reason_codes[0],
        "project_planning_summary_reason_codes": (
            project_planning_summary_reason_codes
        ),
        "project_planning_control_posture": _normalize_text(
            project_planning_control_posture,
            default="unknown",
        ),
        "project_planning_summary_compact": project_planning_summary_compact,
        "project_roadmap_status": (
            project_roadmap_status
            if project_roadmap_status in _PROJECT_ROADMAP_STATUSES
            else "insufficient_truth"
        ),
        "project_roadmap_available": bool(project_roadmap_available),
        "project_roadmap_reason": project_roadmap_reason_codes[0],
        "project_roadmap_reason_codes": project_roadmap_reason_codes,
        "project_roadmap_item_count": project_roadmap_item_count,
        "project_roadmap_items": project_roadmap_items,
        "project_pr_slicing_status": (
            project_pr_slicing_status
            if project_pr_slicing_status in _PROJECT_PR_SLICING_STATUSES
            else "insufficient_truth"
        ),
        "project_pr_slicing_available": bool(project_pr_slicing_available),
        "project_pr_slicing_reason": project_pr_slicing_reason_codes[0],
        "project_pr_slicing_reason_codes": project_pr_slicing_reason_codes,
        "project_pr_slice_count": project_pr_slice_count,
        "project_pr_slices": project_pr_slices,
        "project_pr_one_pr_size_decision": (
            project_pr_one_pr_size_decision
            if project_pr_one_pr_size_decision in _PROJECT_PR_SIZE_DECISIONS
            else "not_available"
        ),
        "project_pr_prioritization_mode": (
            project_pr_prioritization_mode
            if project_pr_prioritization_mode in _PROJECT_PR_PRIORITIZATION_MODES
            else "insufficient_truth"
        ),
        "implementation_prompt_status": (
            implementation_prompt_status
            if implementation_prompt_status in _IMPLEMENTATION_PROMPT_STATUSES
            else "insufficient_truth"
        ),
        "implementation_prompt_available": bool(implementation_prompt_available),
        "implementation_prompt_reason": implementation_prompt_reason_codes[0],
        "implementation_prompt_reason_codes": implementation_prompt_reason_codes,
        "implementation_prompt_slice_id": _normalize_text(
            implementation_prompt_payload.get("slice_id"),
            default="",
        ),
        "implementation_prompt_roadmap_item_id": _normalize_text(
            implementation_prompt_payload.get("roadmap_item_id"),
            default="",
        ),
        "implementation_prompt_payload": dict(implementation_prompt_payload),
        "project_pr_queue_status": (
            project_pr_queue_status
            if project_pr_queue_status in _PROJECT_PR_QUEUE_STATUSES
            else "insufficient_truth"
        ),
        "project_pr_queue_reason": project_pr_queue_reason_codes[0],
        "project_pr_queue_reason_codes": project_pr_queue_reason_codes,
        "project_pr_queue_item_count": _as_non_negative_int(
            project_pr_queue_state.get("queue_item_count"),
            default=0,
        ),
        "project_pr_queue_runnable_count": _as_non_negative_int(
            project_pr_queue_state.get("queue_runnable_count"),
            default=0,
        ),
        "project_pr_queue_blocked_count": _as_non_negative_int(
            project_pr_queue_state.get("queue_blocked_count"),
            default=0,
        ),
        "project_pr_queue_selected_slice_id": _normalize_text(
            project_pr_queue_state.get("queue_selected_slice_id"),
            default="",
        ),
        "project_pr_queue_selected_roadmap_item_id": _normalize_text(
            project_pr_queue_state.get("queue_selected_roadmap_item_id"),
            default="",
        ),
        "project_pr_queue_selected_blocked": bool(
            project_pr_queue_state.get("queue_selected_blocked", False)
        ),
        "project_pr_queue_handoff_prepared": bool(
            project_pr_queue_state.get("queue_handoff_prepared", False)
        ),
        "project_pr_queue_handoff_payload": (
            dict(project_pr_queue_state.get("queue_handoff_payload", {}))
            if isinstance(project_pr_queue_state.get("queue_handoff_payload"), Mapping)
            else {}
        ),
        "project_pr_queue_items": (
            [
                dict(item)
                for item in project_pr_queue_state.get("queue_items", [])
                if isinstance(item, Mapping)
            ]
            if isinstance(project_pr_queue_state.get("queue_items"), list)
            else []
        ),
        "project_pr_queue_processed_slice_ids_before": _normalize_string_list(
            project_pr_queue_state.get("queue_processed_slice_ids_before")
        ),
        "project_pr_queue_processed_slice_ids_after": _normalize_string_list(
            project_pr_queue_state.get("queue_processed_slice_ids_after")
        ),
        "project_pr_queue_processed_slice_ids": _normalize_string_list(
            project_pr_queue_state.get("queue_processed_slice_ids_after")
        ),
        "project_pr_queue_outcome": (
            "queue_item_prepared"
            if bool(project_pr_queue_state.get("queue_handoff_prepared", False))
            else project_pr_queue_reason_codes[0]
        ),
        "review_assimilation_status": (
            review_assimilation_status
            if review_assimilation_status in _REVIEW_ASSIMILATION_STATUSES
            else "insufficient_truth"
        ),
        "review_assimilation_action": (
            review_assimilation_action
            if review_assimilation_action in _REVIEW_ASSIMILATION_ACTIONS
            else "none"
        ),
        "review_assimilation_reason": review_assimilation_reason_codes[0],
        "review_assimilation_reason_codes": review_assimilation_reason_codes,
        "review_assimilation_available": bool(
            review_assimilation_state.get("review_assimilation_available", False)
        ),
        "review_assimilation_reviewable": bool(
            review_assimilation_state.get("review_assimilation_reviewable", False)
        ),
        "review_assimilation_queue_status": _normalize_text(
            review_assimilation_state.get("review_assimilation_queue_status"),
            default="insufficient_truth",
        ),
        "review_assimilation_queue_reason": _normalize_text(
            review_assimilation_state.get("review_assimilation_queue_reason"),
            default="",
        ),
        "review_assimilation_result_status": _normalize_text(
            review_assimilation_state.get("review_assimilation_result_status"),
            default="not_attempted",
        ),
        "review_assimilation_handoff_slice_id": _normalize_text(
            review_assimilation_state.get("review_assimilation_handoff_slice_id"),
            default="",
        ),
        "review_assimilation_handoff_roadmap_item_id": _normalize_text(
            review_assimilation_state.get("review_assimilation_handoff_roadmap_item_id"),
            default="",
        ),
        "self_healing_status": (
            self_healing_status
            if self_healing_status in _SELF_HEALING_STATUSES
            else "insufficient_truth"
        ),
        "self_healing_transition_selected": bool(
            self_healing_state.get("self_healing_transition_selected", False)
        ),
        "self_healing_transition_target": _normalize_text(
            self_healing_state.get("self_healing_transition_target"),
            default="none",
        ),
        "self_healing_transition_allowed": bool(
            self_healing_state.get("self_healing_transition_allowed", False)
        ),
        "self_healing_transition_executed": bool(
            self_healing_state.get("self_healing_transition_executed", False)
        ),
        "self_healing_reason": self_healing_reason_codes[0],
        "self_healing_reason_codes": self_healing_reason_codes,
        "self_healing_chain_limit": _as_non_negative_int(
            self_healing_state.get("self_healing_chain_limit"),
            default=_SELF_HEALING_CHAIN_LIMIT_DEFAULT,
        ),
        "self_healing_transition_count_before": _as_non_negative_int(
            self_healing_state.get("self_healing_transition_count_before"),
            default=prior_self_healing_transition_count,
        ),
        "self_healing_transition_count_after": _as_non_negative_int(
            self_healing_state.get("self_healing_transition_count_after"),
            default=prior_self_healing_transition_count,
        ),
        "self_healing_transition_count": _as_non_negative_int(
            self_healing_state.get("self_healing_transition_count_after"),
            default=prior_self_healing_transition_count,
        ),
        "self_healing_chain_budget_remaining_before": _as_non_negative_int(
            self_healing_state.get("self_healing_chain_budget_remaining_before"),
            default=max(
                0,
                _SELF_HEALING_CHAIN_LIMIT_DEFAULT - prior_self_healing_transition_count,
            ),
        ),
        "self_healing_chain_budget_remaining_after": _as_non_negative_int(
            self_healing_state.get("self_healing_chain_budget_remaining_after"),
            default=max(
                0,
                _SELF_HEALING_CHAIN_LIMIT_DEFAULT - prior_self_healing_transition_count,
            ),
        ),
        "self_healing_human_fallback_preserved": bool(
            self_healing_state.get("self_healing_human_fallback_preserved", True)
        ),
        "self_healing_source_assimilation_status": _normalize_text(
            self_healing_state.get("self_healing_source_assimilation_status"),
            default=review_assimilation_status,
        ),
        "self_healing_source_assimilation_action": _normalize_text(
            self_healing_state.get("self_healing_source_assimilation_action"),
            default=review_assimilation_action,
        ),
        "self_healing_truth_insufficiency_signal": bool(
            self_healing_state.get("self_healing_truth_insufficiency_signal", False)
        ),
        "long_running_stability_status": (
            long_running_status
            if long_running_status in _LONG_RUNNING_STABILITY_STATUSES
            else "insufficient_truth"
        ),
        "long_running_reason": long_running_reason_codes[0],
        "long_running_reason_codes": long_running_reason_codes,
        "long_running_watchdog_active": bool(
            long_running_state.get("long_running_watchdog_active", False)
        ),
        "long_running_stale_detected": bool(
            long_running_state.get("long_running_stale_detected", False)
        ),
        "long_running_stuck_detected": bool(
            long_running_state.get("long_running_stuck_detected", False)
        ),
        "long_running_pause_required": bool(
            long_running_state.get("long_running_pause_required", True)
        ),
        "long_running_resume_allowed": bool(
            long_running_state.get("long_running_resume_allowed", False)
        ),
        "long_running_escalation_required": bool(
            long_running_state.get("long_running_escalation_required", False)
        ),
        "long_running_safe_stop_required": bool(
            long_running_state.get("long_running_safe_stop_required", True)
        ),
        "long_running_replay_safe": bool(
            long_running_state.get("long_running_replay_safe", False)
        ),
        "long_running_replay_key": _normalize_text(
            long_running_state.get("long_running_replay_key"),
            default="",
        ),
        "long_running_progress_signature": _normalize_text(
            long_running_state.get("long_running_progress_signature"),
            default="",
        ),
        "long_running_resume_token": _normalize_text(
            long_running_state.get("long_running_resume_token"),
            default="",
        ),
        "long_running_watchdog_heartbeat_at": _normalize_text(
            long_running_state.get("long_running_watchdog_heartbeat_at"),
            default="",
        ),
        "long_running_watchdog_stale_after_seconds": _as_non_negative_int(
            long_running_state.get("long_running_watchdog_stale_after_seconds"),
            default=_LONG_RUNNING_STALE_AFTER_SECONDS_DEFAULT,
        ),
        "long_running_watchdog_stale_age_seconds": _as_non_negative_int(
            long_running_state.get("long_running_watchdog_stale_age_seconds"),
            default=0,
        ),
        "long_running_stale_cycle_count": _as_non_negative_int(
            long_running_state.get("long_running_stale_cycle_count"),
            default=0,
        ),
        "long_running_stuck_cycle_count": _as_non_negative_int(
            long_running_state.get("long_running_stuck_cycle_count"),
            default=0,
        ),
        "long_running_source_queue_status": _normalize_text(
            long_running_state.get("long_running_source_queue_status"),
            default="insufficient_truth",
        ),
        "long_running_source_review_assimilation_status": _normalize_text(
            long_running_state.get("long_running_source_review_assimilation_status"),
            default="insufficient_truth",
        ),
        "long_running_source_review_assimilation_action": _normalize_text(
            long_running_state.get("long_running_source_review_assimilation_action"),
            default="none",
        ),
        "long_running_source_self_healing_status": _normalize_text(
            long_running_state.get("long_running_source_self_healing_status"),
            default="insufficient_truth",
        ),
        "long_running_source_self_healing_target": _normalize_text(
            long_running_state.get("long_running_source_self_healing_target"),
            default="none",
        ),
        "objective_compiler_status": (
            objective_compiler_status
            if objective_compiler_status in _OBJECTIVE_COMPILER_STATUSES
            else "insufficient_truth"
        ),
        "objective_compiler_reason": objective_compiler_reason_codes[0],
        "objective_compiler_reason_codes": objective_compiler_reason_codes,
        "current_objective_id": _normalize_text(
            objective_compiler_state.get("current_objective_id"),
            default="",
        ),
        "current_objective_available": bool(
            objective_compiler_state.get("current_objective_available", False)
        ),
        "objective_done_criteria_status": objective_done_criteria_status,
        "objective_done_criteria_met": bool(
            objective_compiler_state.get("objective_done_criteria_met", False)
        ),
        "objective_done_remaining_slice_count": _as_non_negative_int(
            objective_compiler_state.get("objective_done_remaining_slice_count"),
            default=0,
        ),
        "objective_stop_criteria_status": objective_stop_criteria_status,
        "objective_stop_criteria_met": bool(
            objective_compiler_state.get("objective_stop_criteria_met", False)
        ),
        "objective_completion_posture": objective_completion_posture,
        "objective_scope_drift_status": objective_scope_drift_status,
        "objective_scope_drift_detected": bool(
            objective_compiler_state.get("objective_scope_drift_detected", False)
        ),
        "objective_scope_drift_reason": _normalize_text(
            objective_compiler_state.get("objective_scope_drift_reason"),
            default="scope_drift_insufficient_truth",
        ),
        "objective_source_slice_count": _as_non_negative_int(
            objective_compiler_state.get("objective_source_slice_count"),
            default=0,
        ),
        "objective_source_processed_count": _as_non_negative_int(
            objective_compiler_state.get("objective_source_processed_count"),
            default=0,
        ),
        "objective_source_queue_status": _normalize_text(
            objective_compiler_state.get("objective_source_queue_status"),
            default="insufficient_truth",
        ),
        "project_autonomy_budget_status": project_autonomy_budget_status,
        "project_autonomy_budget_reason": project_autonomy_budget_reason_codes[0],
        "project_autonomy_budget_reason_codes": project_autonomy_budget_reason_codes,
        "project_priority_posture": project_priority_posture,
        "project_priority_deferred": bool(
            project_autonomy_budget_state.get("project_priority_deferred", False)
        ),
        "project_high_risk_defer_posture": project_high_risk_defer_posture,
        "project_high_risk_defer_active": bool(
            project_autonomy_budget_state.get("project_high_risk_defer_active", False)
        ),
        "project_run_budget_posture": project_run_budget_posture,
        "project_run_budget_limit": _as_non_negative_int(
            project_autonomy_budget_state.get("project_run_budget_limit"),
            default=0,
        ),
        "project_run_budget_remaining": _as_non_negative_int(
            project_autonomy_budget_state.get("project_run_budget_remaining"),
            default=0,
        ),
        "project_run_budget_exhausted": bool(
            project_autonomy_budget_state.get("project_run_budget_exhausted", False)
        ),
        "project_objective_budget_posture": project_objective_budget_posture,
        "project_objective_budget_limit": _as_non_negative_int(
            project_autonomy_budget_state.get("project_objective_budget_limit"),
            default=0,
        ),
        "project_objective_budget_remaining": _as_non_negative_int(
            project_autonomy_budget_state.get("project_objective_budget_remaining"),
            default=0,
        ),
        "project_objective_budget_exhausted": bool(
            project_autonomy_budget_state.get("project_objective_budget_exhausted", False)
        ),
        "project_pr_retry_budget_posture": project_pr_retry_budget_posture,
        "project_pr_retry_budget_applicable": bool(
            project_autonomy_budget_state.get("project_pr_retry_budget_applicable", False)
        ),
        "project_pr_retry_budget_limit": _as_non_negative_int(
            project_autonomy_budget_state.get("project_pr_retry_budget_limit"),
            default=0,
        ),
        "project_pr_retry_budget_remaining": _as_non_negative_int(
            project_autonomy_budget_state.get("project_pr_retry_budget_remaining"),
            default=0,
        ),
        "project_pr_retry_budget_exhausted": bool(
            project_autonomy_budget_state.get("project_pr_retry_budget_exhausted", False)
        ),
        "project_quality_gate_status": project_quality_gate_status,
        "project_quality_gate_reason": project_quality_gate_reason_codes[0],
        "project_quality_gate_reason_codes": project_quality_gate_reason_codes,
        "project_quality_gate_posture": project_quality_gate_posture,
        "project_quality_gate_merge_ready": bool(
            project_quality_gate_state.get("project_quality_gate_merge_ready", False)
        ),
        "project_quality_gate_review_ready": bool(
            project_quality_gate_state.get("project_quality_gate_review_ready", False)
        ),
        "project_quality_gate_retry_needed": bool(
            project_quality_gate_state.get("project_quality_gate_retry_needed", False)
        ),
        "project_quality_gate_recommended": _normalize_string_list(
            project_quality_gate_state.get("project_quality_gate_recommended")
        ),
        "project_quality_gate_recommended_count": _as_non_negative_int(
            project_quality_gate_state.get("project_quality_gate_recommended_count"),
            default=0,
        ),
        "project_quality_gate_changed_area_class": project_quality_gate_changed_area_class,
        "project_quality_gate_risk_level": project_quality_gate_risk_level,
        "project_quality_gate_high_risk": bool(
            project_quality_gate_state.get("project_quality_gate_high_risk", False)
        ),
        "project_quality_gate_unavailable": bool(
            project_quality_gate_state.get("project_quality_gate_unavailable", False)
        ),
        "project_merge_branch_lifecycle_status": project_merge_branch_lifecycle_status,
        "project_merge_branch_lifecycle_reason": project_merge_branch_lifecycle_reason_codes[0],
        "project_merge_branch_lifecycle_reason_codes": (
            project_merge_branch_lifecycle_reason_codes
        ),
        "project_merge_ready_posture": project_merge_ready_posture,
        "project_merge_ready": bool(
            project_merge_branch_lifecycle_state.get("project_merge_ready", False)
        ),
        "project_branch_cleanup_candidate_posture": project_branch_cleanup_candidate_posture,
        "project_branch_cleanup_candidate": bool(
            project_merge_branch_lifecycle_state.get(
                "project_branch_cleanup_candidate",
                False,
            )
        ),
        "project_branch_quarantine_candidate_posture": (
            project_branch_quarantine_candidate_posture
        ),
        "project_branch_quarantine_candidate": bool(
            project_merge_branch_lifecycle_state.get(
                "project_branch_quarantine_candidate",
                False,
            )
        ),
        "project_local_main_sync_posture": project_local_main_sync_posture,
        "project_local_main_sync_required": bool(
            project_merge_branch_lifecycle_state.get(
                "project_local_main_sync_required",
                False,
            )
        ),
        "project_merge_branch_lifecycle_unavailable": bool(
            project_merge_branch_lifecycle_state.get(
                "project_merge_branch_lifecycle_unavailable",
                False,
            )
        ),
        "project_failure_memory_status": project_failure_memory_status,
        "project_failure_memory_reason": project_failure_memory_reason_codes[0],
        "project_failure_memory_reason_codes": project_failure_memory_reason_codes,
        "project_failure_memory_ineffective_retry": bool(
            project_failure_memory_state.get(
                "project_failure_memory_ineffective_retry",
                False,
            )
        ),
        "project_failure_memory_failed_repair": bool(
            project_failure_memory_state.get(
                "project_failure_memory_failed_repair",
                False,
            )
        ),
        "project_failure_memory_repeated_review_issue": bool(
            project_failure_memory_state.get(
                "project_failure_memory_repeated_review_issue",
                False,
            )
        ),
        "project_failure_memory_recurring_failure_bucket": bool(
            project_failure_memory_state.get(
                "project_failure_memory_recurring_failure_bucket",
                False,
            )
        ),
        "project_failure_memory_retry_failure_count": _as_non_negative_int(
            project_failure_memory_state.get(
                "project_failure_memory_retry_failure_count"
            ),
            default=0,
        ),
        "project_failure_memory_repair_failure_count": _as_non_negative_int(
            project_failure_memory_state.get(
                "project_failure_memory_repair_failure_count"
            ),
            default=0,
        ),
        "project_failure_memory_review_issue_count": _as_non_negative_int(
            project_failure_memory_state.get(
                "project_failure_memory_review_issue_count"
            ),
            default=0,
        ),
        "project_failure_memory_failure_bucket_recurrence_count": _as_non_negative_int(
            project_failure_memory_state.get(
                "project_failure_memory_failure_bucket_recurrence_count"
            ),
            default=0,
        ),
        "project_failure_memory_last_failure_bucket": _normalize_text(
            project_failure_memory_state.get("project_failure_memory_last_failure_bucket"),
            default="unknown",
        ),
        "project_failure_memory_suppression_posture": (
            project_failure_memory_suppression_posture
        ),
        "project_failure_memory_suppression_active": bool(
            project_failure_memory_state.get(
                "project_failure_memory_suppression_active",
                False,
            )
        ),
        "project_failure_memory_unavailable": bool(
            project_failure_memory_state.get("project_failure_memory_unavailable", False)
        ),
        "project_external_boundary_status": project_external_boundary_status,
        "project_external_boundary_reason": project_external_boundary_reason_codes[0],
        "project_external_boundary_reason_codes": project_external_boundary_reason_codes,
        "project_external_dependency_posture": project_external_dependency_posture,
        "project_external_dependency_available": bool(
            project_external_boundary_state.get(
                "project_external_dependency_available",
                False,
            )
        ),
        "project_external_dependency_blocked": bool(
            project_external_boundary_state.get(
                "project_external_dependency_blocked",
                False,
            )
        ),
        "project_external_manual_only_posture": project_external_manual_only_posture,
        "project_external_manual_only_required": bool(
            project_external_boundary_state.get(
                "project_external_manual_only_required",
                False,
            )
        ),
        "project_external_network_boundary_posture": (
            project_external_network_boundary_posture
        ),
        "project_external_ci_boundary_posture": project_external_ci_boundary_posture,
        "project_external_secrets_boundary_posture": (
            project_external_secrets_boundary_posture
        ),
        "project_external_github_boundary_posture": (
            project_external_github_boundary_posture
        ),
        "project_external_api_boundary_posture": project_external_api_boundary_posture,
        "project_external_boundary_unavailable": bool(
            project_external_boundary_state.get(
                "project_external_boundary_unavailable",
                False,
            )
        ),
        "project_human_escalation_status": project_human_escalation_status,
        "project_human_escalation_reason": project_human_escalation_reason_codes[0],
        "project_human_escalation_reason_codes": project_human_escalation_reason_codes,
        "project_human_escalation_posture": project_human_escalation_posture,
        "project_human_escalation_required": bool(
            project_human_escalation_state.get("project_human_escalation_required", False)
        ),
        "project_architecture_risk_posture": project_architecture_risk_posture,
        "project_scope_risk_posture": project_scope_risk_posture,
        "project_external_risk_posture": project_external_risk_posture,
        "project_budget_risk_posture": project_budget_risk_posture,
        "project_repeated_failure_risk_posture": (
            project_repeated_failure_risk_posture
        ),
        "project_manual_only_risk_posture": project_manual_only_risk_posture,
        "project_human_escalation_unavailable": bool(
            project_human_escalation_state.get(
                "project_human_escalation_unavailable",
                False,
            )
        ),
        "project_approval_notification_status": project_approval_notification_status,
        "project_approval_notification_reason": project_approval_notification_reason_codes[0],
        "project_approval_notification_reason_codes": (
            project_approval_notification_reason_codes
        ),
        "project_approval_notification_ready_posture": (
            project_approval_notification_ready_posture
        ),
        "project_approval_notification_ready": bool(
            project_approval_notification_state.get(
                "project_approval_notification_ready",
                False,
            )
        ),
        "project_approval_reply_required_posture": (
            project_approval_reply_required_posture
        ),
        "project_approval_reply_required": bool(
            project_approval_notification_state.get(
                "project_approval_reply_required",
                False,
            )
        ),
        "project_approval_channel_posture": project_approval_channel_posture,
        "project_approval_mobile_summary_posture": (
            project_approval_mobile_summary_posture
        ),
        "project_approval_mobile_summary_compact": _normalize_text(
            project_approval_notification_state.get(
                "project_approval_mobile_summary_compact"
            ),
            default="",
        ),
        "project_approval_mobile_summary_tokens": _normalize_string_list(
            project_approval_notification_state.get(
                "project_approval_mobile_summary_tokens"
            )
        ),
        "project_approval_notification_unavailable": bool(
            project_approval_notification_state.get(
                "project_approval_notification_unavailable",
                False,
            )
        ),
        "project_multi_objective_status": project_multi_objective_status,
        "project_multi_objective_reason": project_multi_objective_reason_codes[0],
        "project_multi_objective_reason_codes": project_multi_objective_reason_codes,
        "project_active_objective_selection_posture": (
            project_active_objective_selection_posture
        ),
        "project_active_objective_id": _normalize_text(
            project_multi_objective_state.get("project_active_objective_id"),
            default="",
        ),
        "project_blocked_objective_deferral_posture": (
            project_blocked_objective_deferral_posture
        ),
        "project_blocked_objective_deferred": bool(
            project_multi_objective_state.get("project_blocked_objective_deferred", False)
        ),
        "project_resumable_queue_ordering_posture": (
            project_resumable_queue_ordering_posture
        ),
        "project_resumable_queue_ordering_key": _normalize_text(
            project_multi_objective_state.get("project_resumable_queue_ordering_key"),
            default="",
        ),
        "project_resumable_queue_next_slice_id": _normalize_text(
            project_multi_objective_state.get("project_resumable_queue_next_slice_id"),
            default="",
        ),
        "project_resumable_queue_has_pending": bool(
            project_multi_objective_state.get("project_resumable_queue_has_pending", False)
        ),
        "project_multi_objective_unavailable": bool(
            project_multi_objective_state.get("project_multi_objective_unavailable", False)
        ),
        "automatic_continuation_branch_count_before": continuation_branch_count_before,
        "automatic_continuation_branch_count": continuation_branch_count_after,
        "automatic_continuation_retry_count": continuation_retry_count_after,
        "automatic_continuation_replan_count": continuation_replan_count_after,
        "automatic_continuation_truth_gather_count": continuation_truth_gather_count_after,
        "automatic_continuation_run_count_before": continuation_run_count_before,
        "automatic_continuation_run_count": continuation_run_count_after,
        "automatic_continuation_objective_count_before": continuation_objective_count_before,
        "automatic_continuation_objective_count": continuation_objective_count_after,
        "automatic_continuation_lane_count_before": continuation_lane_count_before,
        "automatic_continuation_lane_count": continuation_lane_count_after,
        "automatic_continuation_objective_key": continuation_budget_objective_key,
        "automatic_continuation_lane_key": continuation_budget_lane_key,
        "continuation_budget_run_remaining": continuation_budget_run_remaining,
        "continuation_budget_objective_remaining": continuation_budget_objective_remaining,
        "continuation_budget_lane_remaining": continuation_budget_lane_remaining,
        "continuation_budget_branch_remaining": continuation_budget_branch_remaining,
        "supporting_compact_truth_refs": supporting_compact_truth_refs,
    }


def _collect_execution_result_contract_records(
    manifest_units: list[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for entry in manifest_units:
        result_path_text = _normalize_text(entry.get("result_path"), default="")
        receipt_path_text = _normalize_text(entry.get("receipt_path"), default="")

        result_path = Path(result_path_text) if result_path_text else None
        receipt_path = Path(receipt_path_text) if receipt_path_text else None

        result_exists = bool(result_path and result_path.exists())
        receipt_exists = bool(receipt_path and receipt_path.exists())
        result_payload = _read_json_object_if_exists(result_path) if result_path else None
        receipt_payload = _read_json_object_if_exists(receipt_path) if receipt_path else None

        records.append(
            {
                "pr_id": _normalize_text(entry.get("pr_id"), default=""),
                "result_path": str(result_path) if result_path else "",
                "result_exists": result_exists,
                "result_malformed": bool(result_exists and not isinstance(result_payload, Mapping)),
                "result_payload": dict(result_payload) if isinstance(result_payload, Mapping) else None,
                "receipt_path": str(receipt_path) if receipt_path else "",
                "receipt_exists": receipt_exists,
                "receipt_malformed": bool(receipt_exists and not isinstance(receipt_payload, Mapping)),
                "receipt_payload": dict(receipt_payload) if isinstance(receipt_payload, Mapping) else None,
            }
        )
    return records


def _augment_run_state_with_policy_overlay(
    *,
    run_state_payload: Mapping[str, Any],
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    loop_state = _normalize_text(payload.get("loop_state"), default="")
    loop_next_safe_action = _normalize_text(payload.get("next_safe_action"), default="")
    suggested_execution_action = _POLICY_LOOP_ACTION_TO_EXECUTION_ACTION.get(loop_next_safe_action, "")

    authority_validation_blocked = bool(payload.get("authority_validation_blocked", False))
    execution_authority_blocked = bool(payload.get("execution_authority_blocked", False))
    validation_blocked = bool(payload.get("validation_blocked", False))
    authority_validation_missing_or_ambiguous = bool(
        payload.get("authority_validation_missing_or_ambiguous", False)
    )
    remote_github_blocked = bool(payload.get("remote_github_blocked", False))
    remote_github_missing_or_ambiguous = bool(payload.get("remote_github_missing_or_ambiguous", False))
    rollback_aftermath_blocked = bool(payload.get("rollback_aftermath_blocked", False))
    rollback_aftermath_missing_or_ambiguous = bool(
        payload.get("rollback_aftermath_missing_or_ambiguous", False)
    )
    rollback_validation_failed = bool(payload.get("rollback_validation_failed", False))
    manual_intervention_required = bool(payload.get("manual_intervention_required", False))
    loop_manual_intervention_required = bool(payload.get("loop_manual_intervention_required", False))
    rollback_manual_followup_required = bool(payload.get("rollback_manual_followup_required", False))
    rollback_remote_followup_required = bool(payload.get("rollback_remote_followup_required", False))
    rollback_replan_required = bool(payload.get("rollback_replan_required", False))
    loop_replan_required = bool(payload.get("loop_replan_required", False))
    terminal = bool(payload.get("terminal", False))
    resumable = bool(payload.get("resumable", False))
    global_stop_recommended = bool(payload.get("global_stop_recommended", False)) or bool(
        payload.get("global_stop", False)
    )

    blocked_reasons = _serialize_required_signals(
        [
            *_normalize_string_list(payload.get("authority_validation_blocked_reasons")),
            *_normalize_string_list(payload.get("remote_github_blocked_reasons")),
            *_normalize_string_list(payload.get("rollback_aftermath_blocked_reasons")),
            *_normalize_string_list(payload.get("loop_blocked_reasons")),
        ]
    )
    for key in (
        "authority_validation_blocked_reason",
        "remote_github_blocked_reason",
        "rollback_aftermath_blocked_reason",
        "loop_blocked_reason",
    ):
        reason = _normalize_text(payload.get(key), default="")
        if reason:
            blocked_reasons.append(reason)
    blocked_reasons = _serialize_required_signals(blocked_reasons)

    missing_or_ambiguous = (
        authority_validation_missing_or_ambiguous
        or remote_github_missing_or_ambiguous
        or rollback_aftermath_missing_or_ambiguous
    )
    manual_gate = (
        manual_intervention_required
        or loop_manual_intervention_required
        or rollback_manual_followup_required
        or rollback_remote_followup_required
    )
    hard_execution_blocked = (
        authority_validation_blocked
        or execution_authority_blocked
        or validation_blocked
        or remote_github_blocked
        or rollback_aftermath_blocked
        or rollback_validation_failed
    )
    policy_replan_required = loop_replan_required or rollback_replan_required
    policy_terminal = terminal
    policy_resume_allowed = resumable and not policy_terminal and not policy_replan_required

    terminal_failure = loop_state == "terminal_failure"
    duplicate_pr_blocked = any(reason in _POLICY_DUPLICATE_PR_REASONS for reason in blocked_reasons)

    if policy_terminal:
        policy_status = "terminally_stopped"
    elif policy_replan_required:
        policy_status = "replan_required"
    elif hard_execution_blocked and not missing_or_ambiguous:
        policy_status = "blocked"
    elif manual_gate or missing_or_ambiguous or global_stop_recommended:
        policy_status = "manual_only"
    elif policy_resume_allowed and not bool(payload.get("continue_allowed", False)):
        policy_status = "resume_eligible"
    else:
        policy_status = "allowed"
    if policy_status not in _POLICY_STATUSES:
        policy_status = "blocked"

    policy_primary_blocker_class = "none"
    if policy_terminal:
        policy_primary_blocker_class = "terminal"
    elif policy_replan_required:
        policy_primary_blocker_class = "replan_required"
    elif rollback_aftermath_blocked or rollback_validation_failed:
        policy_primary_blocker_class = "rollback_aftermath"
    elif authority_validation_blocked or execution_authority_blocked or validation_blocked:
        policy_primary_blocker_class = "authority_validation"
    elif remote_github_blocked:
        policy_primary_blocker_class = "remote_github"
    elif missing_or_ambiguous:
        policy_primary_blocker_class = "missing_or_ambiguous"
    elif manual_gate or global_stop_recommended:
        policy_primary_blocker_class = "manual_gate"
    if policy_primary_blocker_class not in _POLICY_BLOCKER_CLASSES:
        policy_primary_blocker_class = "manual_gate"

    disallowed_actions: set[str] = set()
    manual_actions: set[str] = set()
    allowed_actions: set[str] = set(_POLICY_NON_EXECUTION_ACTIONS)
    if policy_status in {"blocked", "manual_only", "replan_required", "terminally_stopped"}:
        disallowed_actions.update(_POLICY_EXECUTION_INTENT_ACTIONS)
    else:
        allowed_actions.update(_POLICY_EXECUTION_INTENT_ACTIONS)
    if duplicate_pr_blocked:
        disallowed_actions.add("proceed_to_pr")
    if policy_status == "manual_only":
        manual_actions.update({"escalate_to_human", "inspect", "signal_recollect"})
    elif policy_status == "replan_required":
        manual_actions.update({"roadmap_replan", "escalate_to_human", "inspect"})
    elif policy_status == "terminally_stopped":
        manual_actions.update({"inspect", "escalate_to_human"})
    if suggested_execution_action and suggested_execution_action in _POLICY_EXECUTION_INTENT_ACTIONS:
        if suggested_execution_action not in disallowed_actions:
            allowed_actions.add(suggested_execution_action)

    if duplicate_pr_blocked and policy_status in {"allowed", "resume_eligible"}:
        policy_status = "blocked"
        policy_primary_blocker_class = "remote_github"
        disallowed_actions.add("proceed_to_pr")

    if policy_status == "allowed":
        policy_blocked = False
    elif policy_status == "terminally_stopped":
        policy_blocked = terminal_failure
    else:
        policy_blocked = True

    if policy_status in {"blocked", "manual_only", "replan_required", "terminally_stopped"} and not blocked_reasons:
        blocked_reasons = [f"policy_status:{policy_status}"]
    if duplicate_pr_blocked:
        blocked_reasons = _serialize_required_signals([*blocked_reasons, "existing_open_pr_detected"])

    policy_blocked_reason = blocked_reasons[0] if blocked_reasons else ""
    policy_manual_required = policy_status == "manual_only" or manual_gate
    policy_resume_allowed = (
        policy_resume_allowed and not policy_terminal and not policy_replan_required
    )

    return {
        **payload,
        "policy_status": policy_status,
        "policy_blocked": policy_blocked,
        "policy_manual_required": policy_manual_required,
        "policy_replan_required": policy_replan_required,
        "policy_resume_allowed": policy_resume_allowed,
        "policy_terminal": policy_terminal,
        "policy_blocked_reason": policy_blocked_reason,
        "policy_blocked_reasons": _serialize_required_signals(blocked_reasons),
        "policy_primary_blocker_class": policy_primary_blocker_class,
        "policy_primary_action": suggested_execution_action,
        "policy_allowed_actions": sorted(allowed_actions),
        "policy_disallowed_actions": sorted(disallowed_actions),
        "policy_manual_actions": sorted(manual_actions),
        "policy_resumable_reason": (
            "resumable_state_available"
            if policy_resume_allowed
            else "terminal_or_replan_or_manual_gate"
        ),
    }


def _augment_run_state_with_operator_explainability(
    *,
    run_state_payload: Mapping[str, Any],
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    return {
        **payload,
        **build_operator_explainability_surface(
            payload,
            include_rendering_details=False,
        ),
    }


def _augment_run_state_with_lifecycle_terminal_contract(
    *,
    run_state_payload: Mapping[str, Any],
) -> dict[str, Any]:
    payload = dict(run_state_payload)
    return {
        **payload,
        **build_lifecycle_terminal_state_surface(payload),
    }


def _build_commit_decision(
    *,
    unit_id: str,
    signals: Mapping[str, bool],
    decision_payload: Mapping[str, Any],
) -> dict[str, Any]:
    next_action = _normalize_text(decision_payload.get("next_action"), default="")
    if bool(signals.get("manual_review_required", False)):
        decision = "manual_required"
        rule_id = "commit_manual_review_required"
        summary = "commit recommendation requires manual review gate"
        blocking_reasons = ["manual_review_required", "global_stop_required"]
        recommended_next_action = "escalate_to_human"
    elif any(
        bool(signals.get(name, False))
        for name in ("contract_missing", "contract_identity_conflict", "unbounded_contract", "missing_progression_metadata")
    ):
        decision = "blocked"
        rule_id = "commit_blocked_contract_signals"
        summary = "commit recommendation blocked by contract lifecycle signals"
        blocking_reasons = [
            name
            for name in ("contract_missing", "contract_identity_conflict", "unbounded_contract", "missing_progression_metadata")
            if bool(signals.get(name, False))
        ]
        recommended_next_action = "roadmap_replan"
    elif bool(signals.get("scope_violation_detected", False)):
        decision = "blocked"
        rule_id = "commit_blocked_scope_violation"
        summary = "commit recommendation blocked by scope violation"
        blocking_reasons = ["scope_violation_detected"]
        recommended_next_action = "prompt_recompile"
    elif bool(signals.get("review_passed", False)) and bool(signals.get("execution_succeeded", False)):
        decision = "allowed"
        rule_id = "commit_allowed_review_passed"
        summary = "commit recommendation allowed for bounded reviewed execution result"
        blocking_reasons = []
        recommended_next_action = "proceed_to_pr"
    elif bool(signals.get("review_failed", False)):
        decision = "blocked"
        rule_id = "commit_blocked_review_failed"
        summary = "commit recommendation blocked because review outcome did not accept current result"
        blocking_reasons = ["review_failed"]
        recommended_next_action = next_action or "signal_recollect"
    else:
        decision = "unknown"
        rule_id = "commit_unknown_insufficient_signals"
        summary = "commit recommendation cannot be determined from available stable signals"
        blocking_reasons = ["insufficient_signals"]
        recommended_next_action = next_action or "escalate_to_human"
    if decision not in _COMMIT_DECISIONS:
        decision = "unknown"
    return {
        "schema_version": _DECISION_SCHEMA_VERSION,
        "unit_id": unit_id,
        "decision": decision,
        "rule_id": rule_id,
        "summary": summary,
        "blocking_reasons": blocking_reasons,
        "required_signals": _serialize_required_signals(
            [
                "execution_succeeded",
                "review_passed",
                "contract_missing",
                "contract_identity_conflict",
                "unbounded_contract",
                "missing_progression_metadata",
                "scope_violation_detected",
            ]
        ),
        "recommended_next_action": recommended_next_action,
    }


def _build_merge_decision(
    *,
    unit_id: str,
    signals: Mapping[str, bool],
    decision_payload: Mapping[str, Any],
) -> dict[str, Any]:
    next_action = _normalize_text(decision_payload.get("next_action"), default="")
    if bool(signals.get("manual_review_required", False)):
        decision = "manual_required"
        rule_id = "merge_manual_review_required"
        summary = "merge recommendation requires manual review gate"
        blocking_reasons = ["manual_review_required", "global_stop_required"]
        recommended_next_action = "escalate_to_human"
    elif any(
        bool(signals.get(name, False))
        for name in ("contract_missing", "contract_identity_conflict", "unbounded_contract", "missing_progression_metadata")
    ):
        decision = "blocked"
        rule_id = "merge_blocked_contract_signals"
        summary = "merge recommendation blocked by contract lifecycle signals"
        blocking_reasons = [
            name
            for name in ("contract_missing", "contract_identity_conflict", "unbounded_contract", "missing_progression_metadata")
            if bool(signals.get(name, False))
        ]
        recommended_next_action = "roadmap_replan"
    elif bool(signals.get("scope_violation_detected", False)):
        decision = "blocked"
        rule_id = "merge_blocked_scope_violation"
        summary = "merge recommendation blocked by scope violation"
        blocking_reasons = ["scope_violation_detected"]
        recommended_next_action = "prompt_recompile"
    elif bool(signals.get("review_passed", False)) and bool(signals.get("execution_succeeded", False)):
        if next_action == "proceed_to_merge":
            decision = "allowed"
            rule_id = "merge_allowed_explicit_progression"
            summary = "merge recommendation allowed by explicit progression outcome"
            blocking_reasons = []
            recommended_next_action = "proceed_to_merge"
        else:
            decision = "blocked"
            rule_id = "merge_blocked_not_requested"
            summary = "merge recommendation blocked because merge progression is not explicitly requested"
            blocking_reasons = ["merge_not_requested"]
            recommended_next_action = "proceed_to_pr"
    elif bool(signals.get("review_failed", False)):
        decision = "blocked"
        rule_id = "merge_blocked_review_failed"
        summary = "merge recommendation blocked because review outcome did not accept current result"
        blocking_reasons = ["review_failed"]
        recommended_next_action = next_action or "signal_recollect"
    else:
        decision = "unknown"
        rule_id = "merge_unknown_insufficient_signals"
        summary = "merge recommendation cannot be determined from available stable signals"
        blocking_reasons = ["insufficient_signals"]
        recommended_next_action = next_action or "escalate_to_human"
    if decision not in _MERGE_DECISIONS:
        decision = "unknown"
    return {
        "schema_version": _DECISION_SCHEMA_VERSION,
        "unit_id": unit_id,
        "decision": decision,
        "rule_id": rule_id,
        "summary": summary,
        "blocking_reasons": blocking_reasons,
        "required_signals": _serialize_required_signals(
            [
                "execution_succeeded",
                "review_passed",
                "manual_review_required",
                "contract_missing",
                "contract_identity_conflict",
                "unbounded_contract",
                "missing_progression_metadata",
                "scope_violation_detected",
            ]
        ),
        "recommended_next_action": recommended_next_action,
    }


def _build_rollback_decision(
    *,
    unit_id: str,
    signals: Mapping[str, bool],
    decision_payload: Mapping[str, Any],
) -> dict[str, Any]:
    next_action = _normalize_text(decision_payload.get("next_action"), default="")
    if next_action == "rollback_required" or bool(signals.get("rollback_required", False)):
        decision = "required"
        rule_id = "rollback_required_by_progression"
        summary = "rollback recommendation explicitly required by progression outcome"
        blocking_reasons: list[str] = []
        recommended_next_action = "rollback_required"
    elif bool(signals.get("manual_review_required", False)) and bool(signals.get("global_stop_required", False)):
        decision = "manual_required"
        rule_id = "rollback_manual_review_required"
        summary = "rollback recommendation requires explicit manual review"
        blocking_reasons = ["manual_review_required", "global_stop_required"]
        recommended_next_action = "escalate_to_human"
    elif any(
        bool(signals.get(name, False))
        for name in ("contract_missing", "contract_identity_conflict", "missing_progression_metadata")
    ):
        decision = "blocked"
        rule_id = "rollback_blocked_contract_signals"
        summary = "rollback recommendation blocked by contract lifecycle signal gaps"
        blocking_reasons = [
            name
            for name in ("contract_missing", "contract_identity_conflict", "missing_progression_metadata")
            if bool(signals.get(name, False))
        ]
        recommended_next_action = "signal_recollect"
    elif bool(signals.get("review_passed", False)) and bool(signals.get("execution_succeeded", False)):
        decision = "not_required"
        rule_id = "rollback_not_required_success_path"
        summary = "rollback recommendation not required for accepted bounded execution result"
        blocking_reasons = []
        recommended_next_action = next_action or "proceed_to_pr"
    else:
        decision = "unknown"
        rule_id = "rollback_unknown_insufficient_signals"
        summary = "rollback recommendation cannot be determined from available stable signals"
        blocking_reasons = ["insufficient_signals"]
        recommended_next_action = next_action or "escalate_to_human"
    if decision not in _ROLLBACK_DECISIONS:
        decision = "unknown"
    return {
        "schema_version": _DECISION_SCHEMA_VERSION,
        "unit_id": unit_id,
        "decision": decision,
        "rule_id": rule_id,
        "summary": summary,
        "blocking_reasons": blocking_reasons,
        "required_signals": _serialize_required_signals(
            [
                "review_passed",
                "execution_succeeded",
                "manual_review_required",
                "contract_missing",
                "contract_identity_conflict",
                "missing_progression_metadata",
                "rollback_required",
            ]
        ),
        "recommended_next_action": recommended_next_action,
    }


def _resolve_checkpoint_stage_and_decision(
    *,
    next_action: str,
    result_acceptance: str,
    manual_intervention_required: bool,
    global_stop_recommended: bool,
) -> tuple[str, str, str, str]:
    if next_action == "rollback_required":
        return (
            "pre_rollback_evaluation",
            "rollback_evaluation_ready",
            "checkpoint_rollback_evaluation_ready",
            "checkpoint marked ready for rollback evaluation",
        )
    if result_acceptance == "accept_current_result" and next_action == "proceed_to_merge":
        return (
            "pre_merge_evaluation",
            "merge_evaluation_ready",
            "checkpoint_merge_evaluation_ready",
            "checkpoint marked ready for merge evaluation",
        )
    if result_acceptance == "accept_current_result" and next_action == "proceed_to_pr":
        return (
            "pre_commit_evaluation",
            "commit_evaluation_ready",
            "checkpoint_commit_evaluation_ready",
            "checkpoint marked ready for commit evaluation",
        )
    if next_action in {"same_prompt_retry", "repair_prompt_retry"}:
        return (
            "post_review",
            "retry",
            "checkpoint_retry_recommended",
            "checkpoint recommends bounded retry",
        )
    if next_action in {"signal_recollect", "wait_for_checks", "prompt_recompile", "roadmap_replan"}:
        return (
            "post_review",
            "pause",
            "checkpoint_pause_recommended",
            "checkpoint requires pause until explicit follow-up action",
        )
    if next_action == "escalate_to_human":
        if global_stop_recommended:
            return (
                "post_review",
                "global_stop_recommended",
                "checkpoint_global_stop_recommended",
                "checkpoint recommends global stop",
            )
        if manual_intervention_required:
            return (
                "post_review",
                "manual_review_required",
                "checkpoint_manual_review_required",
                "checkpoint requires manual review before continuing",
            )
        return (
            "post_review",
            "escalate",
            "checkpoint_escalation_recommended",
            "checkpoint requires conservative escalation",
        )
    if result_acceptance == "accept_current_result":
        return (
            "post_review",
            "proceed",
            "checkpoint_proceed_post_review",
            "checkpoint allows bounded progression",
        )
    return (
        "post_execution",
        "pause",
        "checkpoint_pause_post_execution",
        "checkpoint remains paused due to incomplete review outcome",
    )


def _build_checkpoint_decision(
    *,
    unit_id: str,
    signals: Mapping[str, bool],
    decision_payload: Mapping[str, Any],
) -> dict[str, Any]:
    # Checkpoint artifacts sit between review/progression outcomes and commit/merge/rollback
    # decision artifacts so later phases can consume explicit stop/go state without prose parsing.
    next_action = _normalize_text(decision_payload.get("next_action"), default="")
    result_acceptance = _normalize_text(decision_payload.get("result_acceptance"), default="")
    manual_intervention_required = bool(signals.get("manual_review_required", False))
    global_stop_recommended = bool(signals.get("global_stop_required", False))
    checkpoint_stage, decision, rule_id, summary = _resolve_checkpoint_stage_and_decision(
        next_action=next_action,
        result_acceptance=result_acceptance,
        manual_intervention_required=manual_intervention_required,
        global_stop_recommended=global_stop_recommended,
    )
    if checkpoint_stage not in _CHECKPOINT_STAGES:
        checkpoint_stage = "post_review"
    if decision not in _CHECKPOINT_DECISIONS:
        decision = "pause"
        rule_id = "checkpoint_pause_unknown"
        summary = "checkpoint conservatively paused because decision mapping was unknown"

    blocking_reasons = [
        name
        for name in (
            "contract_missing",
            "contract_identity_conflict",
            "unbounded_contract",
            "missing_progression_metadata",
            "scope_violation_detected",
            "execution_failed",
            "validation_failed",
            "review_failed",
            "manual_review_required",
            "global_stop_required",
        )
        if bool(signals.get(name, False))
    ]
    if decision in {"retry", "pause"} and next_action:
        blocking_reasons.append(f"next_action:{next_action}")
    if decision == "rollback_evaluation_ready":
        blocking_reasons.append("rollback_evaluation_required")

    return {
        "schema_version": _CHECKPOINT_SCHEMA_VERSION,
        "unit_id": unit_id,
        "checkpoint_stage": checkpoint_stage,
        "decision": decision,
        "rule_id": rule_id,
        "summary": summary,
        "blocking_reasons": _serialize_required_signals(blocking_reasons),
        "required_signals": _serialize_required_signals(
            [
                "execution_succeeded",
                "execution_failed",
                "validation_failed",
                "scope_violation_detected",
                "contract_missing",
                "contract_identity_conflict",
                "unbounded_contract",
                "missing_progression_metadata",
                "review_passed",
                "review_failed",
                "manual_review_required",
                "rollback_required",
                "global_stop_required",
            ]
        ),
        "recommended_next_action": next_action or "escalate_to_human",
        "manual_intervention_required": manual_intervention_required,
        "global_stop_recommended": global_stop_recommended,
    }


def _resolve_run_state(
    *,
    run_status: str,
    next_action: str,
) -> str:
    if run_status == "failed" and next_action in {"escalate_to_human", "rollback_required"}:
        return "failed_terminal"
    if next_action == "proceed_to_merge":
        return "merge_ready"
    if next_action == "proceed_to_pr":
        return "commit_ready"
    if next_action == "rollback_required":
        return "rollback_in_progress"
    if next_action in {
        "same_prompt_retry",
        "repair_prompt_retry",
        "signal_recollect",
        "wait_for_checks",
        "prompt_recompile",
        "roadmap_replan",
        "escalate_to_human",
    }:
        return "paused"
    if run_status == "failed":
        return "failed_terminal"
    return "decision_in_progress"


def _resolve_orchestration_state(
    *,
    state: str,
    run_status: str,
    continue_allowed: bool,
    manual_intervention_required: bool,
    rollback_evaluation_pending: bool,
    global_stop_recommended: bool,
    units_pending: int,
) -> str:
    if state == "completed":
        return "completed"
    if rollback_evaluation_pending:
        return "rollback_evaluation_pending"
    if global_stop_recommended:
        return "global_stop_pending"
    if manual_intervention_required:
        return "paused_for_manual_review"
    if run_status == "failed" or state == "failed_terminal":
        return "failed_terminal"
    if continue_allowed:
        return "run_ready_to_continue"
    if state in {"decision_in_progress", "paused", "review_in_progress"}:
        return "checkpoint_evaluation_in_progress"
    if state == "execution_in_progress":
        return "execution_in_progress"
    if units_pending > 0:
        return "execution_in_progress"
    if state == "units_generated":
        return "units_generated"
    if state == "planning_completed":
        return "planning_completed"
    if state in _ORCHESTRATION_STATES:
        return state
    return "checkpoint_evaluation_in_progress"


def _resolve_next_run_action(
    *,
    orchestration_state: str,
    continue_allowed: bool,
    run_status: str,
) -> str:
    if orchestration_state == "completed":
        return "complete_run"
    if orchestration_state == "rollback_evaluation_pending":
        return "evaluate_rollback"
    if orchestration_state == "global_stop_pending":
        return "hold_for_global_stop"
    if orchestration_state == "paused_for_manual_review":
        return "await_manual_review"
    if continue_allowed and orchestration_state == "run_ready_to_continue":
        return "continue_run"
    if run_status == "failed" or orchestration_state == "failed_terminal":
        return "hold_for_global_stop"
    return "pause_run"


def _build_run_state_payload(
    *,
    run_id: str,
    run_status: str,
    next_action: str,
    reason: str,
    total_units_planned: int,
    manifest_units: list[Mapping[str, Any]],
) -> dict[str, Any]:
    # `state` remains the PR24 lifecycle surface for backward compatibility.
    # `orchestration_state` is additive PR26 run-level orchestration semantics
    # derived from unit/checkpoint artifacts and deterministic next-run gating.
    units_total = max(0, total_units_planned)
    units_processed = len(manifest_units)
    units_failed = sum(1 for unit in manifest_units if _normalize_text(unit.get("status"), default="") == "failed")
    units_completed = sum(
        1
        for unit in manifest_units
        if _normalize_text(unit.get("status"), default="") == "recorded"
    )
    units_pending = max(0, units_total - units_processed)
    unit_blocked = sum(
        1
        for unit in manifest_units
        if _normalize_text(unit.get("unit_progression_state"), default="")
        in {_UNIT_STATE_ESCALATED, _UNIT_STATE_REVIEWED}
    )
    checkpoint_manual_intervention_required = any(
        bool(unit.get("checkpoint_summary", {}).get("manual_intervention_required"))
        for unit in manifest_units
        if isinstance(unit.get("checkpoint_summary"), Mapping)
    )
    checkpoint_global_stop_recommended = any(
        bool(unit.get("checkpoint_summary", {}).get("global_stop_recommended"))
        for unit in manifest_units
        if isinstance(unit.get("checkpoint_summary"), Mapping)
    )
    global_stop = next_action in {"escalate_to_human", "rollback_required"}
    if checkpoint_global_stop_recommended:
        global_stop = True
    rollback_evaluation_pending = any(
        _normalize_text(unit.get("checkpoint_summary", {}).get("decision"), default="")
        == "rollback_evaluation_ready"
        for unit in manifest_units
        if isinstance(unit.get("checkpoint_summary"), Mapping)
    ) or any(
        _normalize_text(unit.get("decision_summary", {}).get("rollback_decision"), default="")
        == "required"
        for unit in manifest_units
        if isinstance(unit.get("decision_summary"), Mapping)
    )
    state = _resolve_run_state(run_status=run_status, next_action=next_action)
    if state not in _RUN_STATES:
        state = "failed_terminal"
    continue_allowed = state in {"commit_ready", "merge_ready"}
    continue_allowed = (
        continue_allowed
        and not checkpoint_manual_intervention_required
        and not global_stop
        and not rollback_evaluation_pending
    )
    orchestration_state = _resolve_orchestration_state(
        state=state,
        run_status=run_status,
        continue_allowed=continue_allowed,
        manual_intervention_required=checkpoint_manual_intervention_required,
        rollback_evaluation_pending=rollback_evaluation_pending,
        global_stop_recommended=checkpoint_global_stop_recommended or global_stop,
        units_pending=units_pending,
    )
    if orchestration_state not in _ORCHESTRATION_STATES:
        orchestration_state = "failed_terminal"
    next_run_action = _resolve_next_run_action(
        orchestration_state=orchestration_state,
        continue_allowed=continue_allowed,
        run_status=run_status,
    )
    if next_run_action not in _RUN_NEXT_ACTIONS:
        next_run_action = "pause_run"
    continue_allowed = next_run_action == "continue_run"
    run_paused = next_run_action in {
        "pause_run",
        "await_manual_review",
        "evaluate_rollback",
        "hold_for_global_stop",
    }
    return {
        "schema_version": _RUN_STATE_SCHEMA_VERSION,
        "run_id": run_id,
        "state": state,
        "orchestration_state": orchestration_state,
        "summary": reason or f"next_action={next_action}",
        "units_total": units_total,
        "units_completed": units_completed,
        "units_blocked": unit_blocked,
        "units_failed": units_failed,
        "units_pending": units_pending,
        "global_stop": global_stop,
        "global_stop_reason": reason if global_stop else "",
        "continue_allowed": continue_allowed,
        "run_paused": run_paused,
        "manual_intervention_required": checkpoint_manual_intervention_required,
        "rollback_evaluation_pending": rollback_evaluation_pending,
        "global_stop_recommended": checkpoint_global_stop_recommended or global_stop,
        "next_run_action": next_run_action,
        "unit_blocked": unit_blocked > 0,
        "latest_unit_id": _normalize_text(manifest_units[-1].get("pr_id"), default="") if manifest_units else "",
        "allowed_transitions": list(_RUN_STATE_ALLOWED_TRANSITIONS.get(state, ())),
        "orchestration_allowed_transitions": list(
            _ORCHESTRATION_ALLOWED_TRANSITIONS.get(orchestration_state, ())
        ),
    }


class DryRunCodexExecutionTransport(CodexExecutionTransport):
    def __init__(self, *, status_by_pr_id: Mapping[str, str] | None = None) -> None:
        self._status_by_pr_id = dict(status_by_pr_id or {})
        self._runs: dict[str, dict[str, Any]] = {}

    def launch_job(
        self,
        *,
        job_id: str,
        pr_id: str,
        prompt_path: str,
        work_dir: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        run_id = f"{job_id}:{pr_id}:dry-run"
        status = _normalize_text(self._status_by_pr_id.get(pr_id), default="not_started").lower()
        if status not in {"not_started", "failed", "completed", "timed_out", "running"}:
            status = "not_started"

        record = {
            "run_id": run_id,
            "job_id": job_id,
            "pr_id": pr_id,
            "status": status,
            "prompt_path": prompt_path,
            "work_dir": work_dir,
            "metadata": dict(metadata or {}),
        }
        self._runs[run_id] = record
        return {
            "run_id": run_id,
            "status": status,
            "dry_run": True,
        }

    def poll_status(self, *, run_id: str) -> Mapping[str, Any]:
        run = self._runs.get(run_id)
        if run is None:
            return {
                "run_id": run_id,
                "status": "failed",
                "error": "unknown_run_id",
            }
        return {
            "run_id": run_id,
            "status": run["status"],
            "dry_run": True,
        }

    def collect_artifacts(self, *, run_id: str) -> Mapping[str, Any]:
        run = self._runs.get(run_id)
        if run is None:
            return {
                "run_id": run_id,
                "stdout_path": "",
                "stderr_path": "",
                "artifacts": [],
            }
        work_dir = Path(str(run["work_dir"]))
        return {
            "run_id": run_id,
            "stdout_path": str(work_dir / "stdout.txt"),
            "stderr_path": str(work_dir / "stderr.txt"),
            "artifacts": [],
            "dry_run": True,
        }


@dataclass
class PlannedExecutionRunner:
    adapter: CodexExecutorAdapter
    github_read_backend: Any | None = None
    github_write_backend: Any | None = None
    now: Callable[[], datetime] = datetime.now

    def _build_raw_result_for_unit(
        self,
        *,
        unit: Mapping[str, Any],
        launch_response: Mapping[str, Any],
        status_response: Mapping[str, Any],
        artifact_response: Mapping[str, Any],
        dry_run: bool,
    ) -> dict[str, Any]:
        status = _normalize_text(
            status_response.get("status") or launch_response.get("status"),
            default="failed",
        ).lower()
        if status not in {"completed", "failed", "timed_out", "not_started", "running"}:
            status = "failed"

        verify_reason = "validation_not_run_dry_run" if dry_run else "validation_not_run"
        raw_verify = status_response.get("verify")
        if not isinstance(raw_verify, Mapping):
            raw_verify = artifact_response.get("verify")
        if not isinstance(raw_verify, Mapping):
            raw_verify = {}

        verify_status = _normalize_text(raw_verify.get("status"), default="").lower()
        if verify_status not in {"passed", "failed", "not_run"}:
            verify_status = "not_run"
        verify_commands = _normalize_string_list(raw_verify.get("commands"))
        if not verify_commands:
            verify_commands = _normalize_string_list(unit.get("validation_commands"))
        normalized_verify_reason = _normalize_text(raw_verify.get("reason"), default="")
        if not normalized_verify_reason:
            normalized_verify_reason = verify_reason
        verify_payload: dict[str, Any] = {
            "status": verify_status,
            "commands": verify_commands,
            "reason": normalized_verify_reason,
        }
        command_results = raw_verify.get("command_results")
        if isinstance(command_results, list):
            verify_payload["command_results"] = command_results

        failure_type: str | None = None
        failure_message: str | None = None
        status_error = _normalize_text(
            status_response.get("error") or launch_response.get("error"),
            default="",
        )
        status_failure_type = _normalize_text(
            status_response.get("failure_type") or launch_response.get("failure_type"),
            default="",
        )
        status_failure_message = _normalize_text(
            status_response.get("failure_message") or launch_response.get("failure_message"),
            default="",
        )
        if status in {"failed", "timed_out"}:
            failure_type = status_failure_type or "execution_failure"
            failure_message = status_failure_message or status_error or f"execution_status={status}"
        elif status in {"not_started", "running"}:
            failure_type = status_failure_type or "missing_signal"
            failure_message = (
                status_failure_message
                or ("dry_run_execution_not_performed" if dry_run else f"execution_status={status}")
            )
        elif verify_status == "failed":
            failure_type = status_failure_type or "evaluation_failure"
            failure_message = status_failure_message or normalized_verify_reason or "validation_failed"
        elif verify_status == "not_run":
            failure_type = status_failure_type or "missing_signal"
            failure_message = status_failure_message or normalized_verify_reason or "validation_not_run"

        raw_cost = status_response.get("cost") if isinstance(status_response.get("cost"), Mapping) else {}
        if not raw_cost:
            raw_cost = artifact_response.get("cost") if isinstance(artifact_response.get("cost"), Mapping) else {}
        return {
            "status": status,
            "attempt_count": _as_non_negative_int(
                status_response.get("attempt_count") or launch_response.get("attempt_count"),
                default=0 if dry_run else 1,
            ),
            "started_at": _normalize_text(
                status_response.get("started_at") or launch_response.get("started_at"),
                default=_iso_now(self.now),
            ),
            "finished_at": _normalize_text(
                status_response.get("finished_at") or launch_response.get("finished_at"),
                default=_iso_now(self.now),
            ),
            "stdout_path": _normalize_text(
                status_response.get("stdout_path") or artifact_response.get("stdout_path"),
                default="",
            ),
            "stderr_path": _normalize_text(
                status_response.get("stderr_path") or artifact_response.get("stderr_path"),
                default="",
            ),
            "verify": verify_payload,
            "changed_files": _normalize_string_list(
                status_response.get("changed_files") or artifact_response.get("changed_files"),
                sort_items=True,
            ),
            "additions": _as_non_negative_int(
                status_response.get("additions") or artifact_response.get("additions"),
                default=0,
            ),
            "deletions": _as_non_negative_int(
                status_response.get("deletions") or artifact_response.get("deletions"),
                default=0,
            ),
            "generated_patch_summary": _normalize_text(
                status_response.get("generated_patch_summary")
                or artifact_response.get("generated_patch_summary"),
                default="",
            ),
            "failure_type": failure_type,
            "failure_message": failure_message,
            "error": status_error,
            "cost": {
                "tokens_input": _as_non_negative_int(raw_cost.get("tokens_input"), default=0),
                "tokens_output": _as_non_negative_int(raw_cost.get("tokens_output"), default=0),
            },
        }

    def run(
        self,
        *,
        artifacts_input_dir: str | Path,
        output_dir: str | Path,
        job_id: str | None = None,
        dry_run: bool = True,
        stop_on_failure: bool = True,
        retry_context: Mapping[str, Any] | None = None,
        policy_snapshot: Mapping[str, Any] | None = None,
        approval_input: Mapping[str, Any] | None = None,
        approval_response_input: Mapping[str, Any] | None = None,
        github_read_evidence: Mapping[str, Any] | None = None,
        execution_repo_path: str | Path | None = None,
    ) -> dict[str, Any]:
        artifacts_root = Path(artifacts_input_dir)
        output_root = Path(output_dir)

        artifacts = load_planning_artifacts(artifacts_root)
        units = compile_prompt_units(artifacts)
        if not units:
            raise ValueError("no pr units found in planning artifacts")
        resolved_execution_repo_path = _normalize_text(execution_repo_path, default="")

        pr_plan = artifacts.get("pr_plan", {})
        _validate_pr_unit_order(units, pr_plan=pr_plan)

        project_brief = (
            dict(artifacts.get("project_brief"))
            if isinstance(artifacts.get("project_brief"), Mapping)
            else {}
        )
        repo_facts = (
            dict(artifacts.get("repo_facts"))
            if isinstance(artifacts.get("repo_facts"), Mapping)
            else {}
        )
        policy_payload = dict(policy_snapshot) if isinstance(policy_snapshot, Mapping) else {}
        approval_input_payload = _resolve_approval_input_payload(
            explicit_approval_input=approval_input,
            artifacts=artifacts,
            policy_snapshot=policy_payload,
        )
        resolved_repository = _normalize_text(
            policy_payload.get("repository"),
            default=_normalize_text(
                project_brief.get("target_repo"),
                default=_normalize_text(repo_facts.get("repo"), default=""),
            ),
        )
        resolved_base_branch = _normalize_text(
            policy_payload.get("base_branch"),
            default=_normalize_text(
                project_brief.get("target_branch"),
                default=_normalize_text(repo_facts.get("default_branch"), default=""),
            ),
        )
        configured_head_branch = _normalize_text(policy_payload.get("head_branch"), default="")
        configured_push_remote = _normalize_text(policy_payload.get("push_remote"), default="origin")
        resolved_job_id = _normalize_text(job_id, default=_normalize_text(project_brief.get("project_id"), default="planned-execution"))
        retry_context_store_path = output_root / "retry_context_store.json"
        retry_context_store = FileRetryContextStore(retry_context_store_path)
        persisted_retry_context = retry_context_store.get(resolved_job_id)
        effective_retry_context = _merge_retry_context_inputs(
            persisted=persisted_retry_context,
            explicit=retry_context,
        )

        run_root = output_root / resolved_job_id
        run_root.mkdir(parents=True, exist_ok=True)

        started_at = _iso_now(self.now)
        finished_at = started_at
        run_status = "dry_run_completed" if dry_run else "completed"
        manifest_units: list[dict[str, Any]] = []
        unit_progression_registry: dict[str, dict[str, Any]] = {}
        unit_signal_registry: dict[str, dict[str, bool]] = {}
        total_units_planned = len(units)

        for unit in units:
            pr_id = _normalize_text(unit.get("pr_id"))
            unit_dir = run_root / pr_id
            unit_dir.mkdir(parents=True, exist_ok=True)

            compiled_prompt_path = unit_dir / "compiled_prompt.md"
            compiled_prompt_path.write_text(
                _normalize_text(unit.get("codex_task_prompt_md"), default=""),
                encoding="utf-8",
            )
            bounded_step_contract_path = unit_dir / "bounded_step_contract.json"
            bounded_step_contract = (
                _normalize_contract_payload(unit.get("bounded_step_contract"))
            )
            _write_json(bounded_step_contract_path, bounded_step_contract)
            implementation_prompt_contract_path = unit_dir / "pr_implementation_prompt_contract.json"
            implementation_prompt_contract = (
                _normalize_contract_payload(unit.get("pr_implementation_prompt_contract"))
            )
            _write_json(implementation_prompt_contract_path, implementation_prompt_contract)
            contract_handoff = _build_unit_contract_handoff(
                pr_id=pr_id,
                bounded_step_contract=bounded_step_contract,
                prompt_contract=implementation_prompt_contract,
            )
            step_handoff = (
                dict(contract_handoff.get("bounded_step"))
                if isinstance(contract_handoff.get("bounded_step"), Mapping)
                else {}
            )
            prompt_handoff = (
                dict(contract_handoff.get("pr_implementation_prompt"))
                if isinstance(contract_handoff.get("pr_implementation_prompt"), Mapping)
                else {}
            )
            unit_progression_path = unit_dir / "unit_progression.json"
            checkpoint_decision_path = unit_dir / "checkpoint_decision.json"
            commit_decision_path = unit_dir / "commit_decision.json"
            merge_decision_path = unit_dir / "merge_decision.json"
            rollback_decision_path = unit_dir / "rollback_decision.json"
            commit_execution_path = unit_dir / "commit_execution.json"
            push_execution_path = unit_dir / "push_execution.json"
            pr_execution_path = unit_dir / "pr_execution.json"
            merge_execution_path = unit_dir / "merge_execution.json"
            rollback_execution_path = unit_dir / "rollback_execution.json"
            unit_progression = _new_unit_progression_payload(
                pr_id=pr_id,
                now=self.now,
                contract_handoff=contract_handoff,
            )
            _append_progression_checkpoint(
                unit_progression,
                state=_UNIT_STATE_PROMPT_READY,
                now=self.now,
                reason="prompt_and_contract_artifacts_persisted",
                metadata={
                    "compiled_prompt_path": str(compiled_prompt_path),
                    "bounded_step_contract_path": str(bounded_step_contract_path),
                    "pr_implementation_prompt_contract_path": str(implementation_prompt_contract_path),
                },
            )
            _write_json(unit_progression_path, unit_progression)

            launch_response = dict(
                self.adapter.launch_job(
                    job_id=resolved_job_id,
                    pr_id=pr_id,
                    prompt_path=str(compiled_prompt_path),
                    work_dir=str(unit_dir),
                    metadata={
                        "dry_run": dry_run,
                        "planned_step_id": _normalize_text(step_handoff.get("planned_step_id"), default=pr_id),
                        "source_step_id": _normalize_text(prompt_handoff.get("source_step_id"), default=pr_id),
                        "tier_category": _normalize_text(
                            step_handoff.get("tier_category") or prompt_handoff.get("tier_category"),
                            default="",
                        ),
                        "depends_on": _normalize_string_list(
                            step_handoff.get("depends_on") or prompt_handoff.get("depends_on"),
                            sort_items=False,
                        ),
                        "strict_scope_files": _normalize_string_list(
                            step_handoff.get("strict_scope_files") or prompt_handoff.get("strict_scope_files"),
                            sort_items=True,
                        ),
                        "forbidden_files": _normalize_string_list(
                            step_handoff.get("forbidden_files") or prompt_handoff.get("forbidden_files"),
                            sort_items=True,
                        ),
                        "validation_commands": _normalize_string_list(
                            step_handoff.get("validation_expectations") or prompt_handoff.get("required_tests"),
                            sort_items=False,
                        ),
                        "boundedness_status": _normalize_text(step_handoff.get("boundedness_status"), default="unknown"),
                        "requires_explicit_validation": bool(prompt_handoff.get("requires_explicit_validation", False)),
                    },
                )
            )
            run_id = _normalize_text(launch_response.get("run_id"), default="")
            _append_progression_checkpoint(
                unit_progression,
                state=_UNIT_STATE_EXECUTION_READY,
                now=self.now,
                reason="execution_launch_attempted",
                metadata={"run_id": run_id, "launch_succeeded": bool(run_id)},
            )
            _write_json(unit_progression_path, unit_progression)

            status_response = (
                dict(self.adapter.poll_status(run_id=run_id))
                if run_id
                else {"status": "failed", "error": "missing_run_id"}
            )
            artifact_response = (
                dict(self.adapter.collect_artifacts(run_id=run_id))
                if run_id
                else {"stdout_path": "", "stderr_path": "", "artifacts": []}
            )

            raw_result = self._build_raw_result_for_unit(
                unit=unit,
                launch_response=launch_response,
                status_response=status_response,
                artifact_response=artifact_response,
                dry_run=dry_run,
            )
            normalized_result = self.adapter.normalize_result(
                job_id=resolved_job_id,
                pr_unit=unit,
                raw_result=raw_result,
                raw_artifacts=artifact_response,
            )

            result_path = unit_dir / "result.json"
            _write_json(result_path, normalized_result)

            execution_status = _normalize_text(
                normalized_result.get("execution", {}).get("status"),
                default="failed",
            ).lower()
            unit_failed = _unit_is_failure(execution_status=execution_status, dry_run=dry_run)
            receipt_status = "failed" if unit_failed else "recorded"
            _append_progression_checkpoint(
                unit_progression,
                state=_UNIT_STATE_EXECUTION_COMPLETED,
                now=self.now,
                reason="execution_result_persisted",
                metadata={
                    "execution_status": execution_status,
                    "verify_status": _normalize_text(
                        normalized_result.get("execution", {}).get("verify", {}).get("status"),
                        default="",
                    ),
                    "receipt_status": receipt_status,
                    "result_path": str(result_path),
                },
            )
            _append_progression_checkpoint(
                unit_progression,
                state="decision_ready",
                now=self.now,
                reason="execution_and_contract_signals_ready_for_decision",
            )
            _write_json(unit_progression_path, unit_progression)
            lifecycle_signals = _build_lifecycle_signals(
                pr_id=pr_id,
                bounded_step_contract=bounded_step_contract,
                prompt_contract=implementation_prompt_contract,
                strict_scope_files=_normalize_string_list(
                    step_handoff.get("strict_scope_files") or prompt_handoff.get("strict_scope_files"),
                    sort_items=True,
                ),
                normalized_result=normalized_result,
            )
            unit_signal_registry[pr_id] = dict(lifecycle_signals)

            receipt = {
                "job_id": resolved_job_id,
                "pr_id": pr_id,
                "status": receipt_status,
                "dry_run": dry_run,
                "run_id": run_id,
                "execution_status": execution_status,
                "compiled_prompt_path": str(compiled_prompt_path),
                "bounded_step_contract_path": str(bounded_step_contract_path),
                "pr_implementation_prompt_contract_path": str(implementation_prompt_contract_path),
                "result_path": str(result_path),
                "stdout_path": _normalize_text(normalized_result.get("execution", {}).get("stdout_path"), default=""),
                "stderr_path": _normalize_text(normalized_result.get("execution", {}).get("stderr_path"), default=""),
                "tier_category": _normalize_text(
                    step_handoff.get("tier_category") or prompt_handoff.get("tier_category"),
                    default="",
                ),
                "depends_on": _normalize_string_list(
                    step_handoff.get("depends_on") or prompt_handoff.get("depends_on"),
                    sort_items=False,
                ),
                "canonical_surface_notes": _normalize_string_list(unit.get("canonical_surface_notes")),
                "compatibility_notes": _normalize_string_list(unit.get("compatibility_notes")),
                "planning_warnings": _normalize_string_list(unit.get("planning_warnings")),
                "contract_handoff": contract_handoff,
                "unit_progression_path": str(unit_progression_path),
                "unit_progression_state": _normalize_text(
                    unit_progression.get("current_state"),
                    default=_UNIT_STATE_EXECUTION_COMPLETED,
                ),
                "decision_artifact_paths": {
                    "checkpoint_decision_path": str(checkpoint_decision_path),
                    "commit_decision_path": str(commit_decision_path),
                    "merge_decision_path": str(merge_decision_path),
                    "rollback_decision_path": str(rollback_decision_path),
                    "commit_execution_path": str(commit_execution_path),
                    "push_execution_path": str(push_execution_path),
                    "pr_execution_path": str(pr_execution_path),
                    "merge_execution_path": str(merge_execution_path),
                    "rollback_execution_path": str(rollback_execution_path),
                },
                "started_at": _iso_now(self.now),
                "finished_at": _iso_now(self.now),
            }
            receipt_path = unit_dir / "execution_receipt.json"
            _write_json(receipt_path, receipt)

            manifest_units.append(
                {
                    "pr_id": pr_id,
                    "compiled_prompt_path": str(compiled_prompt_path),
                    "bounded_step_contract_path": str(bounded_step_contract_path),
                    "pr_implementation_prompt_contract_path": str(implementation_prompt_contract_path),
                    "result_path": str(result_path),
                    "receipt_path": str(receipt_path),
                    "status": receipt_status,
                    "unit_progression_path": str(unit_progression_path),
                    "unit_progression_state": _normalize_text(
                        unit_progression.get("current_state"),
                        default=_UNIT_STATE_EXECUTION_COMPLETED,
                    ),
                    "contract_handoff_summary": {
                        "planned_step_id": _normalize_text(step_handoff.get("planned_step_id"), default=pr_id),
                        "source_step_id": _normalize_text(prompt_handoff.get("source_step_id"), default=pr_id),
                        "tier_category": _normalize_text(
                            step_handoff.get("tier_category") or prompt_handoff.get("tier_category"),
                            default="",
                        ),
                        "boundedness_status": _normalize_text(step_handoff.get("boundedness_status"), default=""),
                    },
                    "checkpoint_decision_path": str(checkpoint_decision_path),
                    "commit_decision_path": str(commit_decision_path),
                    "merge_decision_path": str(merge_decision_path),
                    "rollback_decision_path": str(rollback_decision_path),
                    "commit_execution_path": str(commit_execution_path),
                    "push_execution_path": str(push_execution_path),
                    "pr_execution_path": str(pr_execution_path),
                    "merge_execution_path": str(merge_execution_path),
                    "rollback_execution_path": str(rollback_execution_path),
                }
            )
            unit_progression_registry[pr_id] = {
                "path": str(unit_progression_path),
                "payload": unit_progression,
                "checkpoint_decision_path": str(checkpoint_decision_path),
                "commit_decision_path": str(commit_decision_path),
                "merge_decision_path": str(merge_decision_path),
                "rollback_decision_path": str(rollback_decision_path),
                "commit_execution_path": str(commit_execution_path),
                "push_execution_path": str(push_execution_path),
                "pr_execution_path": str(pr_execution_path),
                "merge_execution_path": str(merge_execution_path),
                "rollback_execution_path": str(rollback_execution_path),
            }

            if unit_failed:
                run_status = "failed"
                if stop_on_failure:
                    break

            finished_at = _iso_now(self.now)

        if run_status != "failed":
            run_status = "dry_run_completed" if dry_run else "completed"

        manifest = {
            "job_id": resolved_job_id,
            "run_status": run_status,
            "artifact_input_dir": str(artifacts_root),
            "started_at": started_at,
            "finished_at": finished_at,
            "dry_run": dry_run,
            "stop_on_failure": stop_on_failure,
            "artifact_ownership": {
                "bounded_step_contract": "bounded_step_contract.json",
                "pr_implementation_prompt_contract": "pr_implementation_prompt_contract.json",
                "execution_result": "result.json",
                "unit_progression": "unit_progression.json",
                "checkpoint_decision": "checkpoint_decision.json",
                "commit_decision": "commit_decision.json",
                "merge_decision": "merge_decision.json",
                "rollback_decision": "rollback_decision.json",
                "commit_execution": "commit_execution.json",
                "push_execution": "push_execution.json",
                "pr_execution": "pr_execution.json",
                "merge_execution": "merge_execution.json",
                "rollback_execution": "rollback_execution.json",
                "run_state": "run_state.json",
                "objective_contract": "objective_contract.json",
                "completion_contract": "completion_contract.json",
                "approval_transport": "approval_transport.json",
                "reconcile_contract": "reconcile_contract.json",
                "repair_suggestion_contract": "repair_suggestion_contract.json",
                "repair_plan_transport": "repair_plan_transport.json",
                "repair_approval_binding": "repair_approval_binding.json",
                "execution_authorization_gate": "execution_authorization_gate.json",
                "bounded_execution_bridge": "bounded_execution_bridge.json",
                "execution_result_contract": "execution_result_contract.json",
                "verification_closure_contract": "verification_closure_contract.json",
                "retry_reentry_loop_contract": "retry_reentry_loop_contract.json",
                "endgame_closure_contract": "endgame_closure_contract.json",
                "loop_hardening_contract": "loop_hardening_contract.json",
                "lane_stabilization_contract": "lane_stabilization_contract.json",
                "observability_rollup_contract": "observability_rollup_contract.json",
                "failure_bucket_rollup": "failure_bucket_rollup.json",
                "fleet_run_rollup": "fleet_run_rollup.json",
                "failure_bucketing_hardening_contract": "failure_bucketing_hardening_contract.json",
                "retention_manifest": "retention_manifest.json",
                "artifact_retention_contract": "artifact_retention_contract.json",
                "fleet_safety_control_contract": "fleet_safety_control_contract.json",
                "approval_email_delivery_contract": "approval_email_delivery_contract.json",
                "approval_runtime_rules_contract": "approval_runtime_rules_contract.json",
                "approval_delivery_handoff_contract": "approval_delivery_handoff_contract.json",
                "approval_response_contract": "approval_response_contract.json",
                "approved_restart_contract": "approved_restart_contract.json",
                "approval_safety_contract": "approval_safety_contract.json",
                "approved_restart_execution_contract": "approved_restart_execution_contract.json",
            },
            "pr_units": manifest_units,
        }
        objective_contract_path = run_root / "objective_contract.json"
        objective_contract_payload = build_objective_contract_surface(
            run_id=resolved_job_id,
            artifacts=artifacts,
            units=units,
            policy_snapshot=policy_snapshot,
            execution_repo_path=resolved_execution_repo_path or None,
            artifact_ownership=manifest["artifact_ownership"],
        )
        _write_json(objective_contract_path, objective_contract_payload)
        manifest["objective_contract_summary"] = build_objective_run_state_summary_surface(
            objective_contract_payload
        )
        manifest["objective_contract_path"] = str(objective_contract_path)

        manifest_path = run_root / "manifest.json"
        _write_json(manifest_path, manifest)
        decision_path = run_root / "next_action.json"
        decision_error = ""
        try:
            decision = evaluate_next_action_from_run_dir(
                run_root,
                retry_context=effective_retry_context,
                policy_snapshot=policy_snapshot,
                pr_plan=artifacts.get("pr_plan"),
            )
        except Exception as exc:
            # Keep deterministic run-level decision handling even when the controller cannot evaluate.
            decision_error = str(exc).strip() or "next_action_evaluation_failed"
            decision = {
                "next_action": "escalate_to_human",
                "reason": f"controller_evaluation_failed: {decision_error}",
                "retry_budget_remaining": 0,
                "whether_human_required": True,
                "updated_retry_context": {
                    "prior_attempt_count": 0,
                    "prior_retry_class": None,
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 0,
                },
            }

        decision_payload = {
            **decision,
            "evaluated_at": _iso_now(self.now),
            "job_id": resolved_job_id,
        }
        _write_json(decision_path, decision_payload)
        review_terminal_state = _resolve_review_terminal_state(decision_payload)
        for entry in manifest_units:
            pr_id = _normalize_text(entry.get("pr_id"), default="")
            progression_record = (
                dict(unit_progression_registry.get(pr_id))
                if isinstance(unit_progression_registry.get(pr_id), Mapping)
                else {}
            )
            progression_payload = (
                dict(progression_record.get("payload"))
                if isinstance(progression_record.get("payload"), Mapping)
                else None
            )
            progression_path_text = _normalize_text(
                progression_record.get("path") or entry.get("unit_progression_path"),
                default="",
            )
            if progression_payload is None or not progression_path_text:
                continue
            lifecycle_signals = dict(unit_signal_registry.get(pr_id) or {})
            lifecycle_signals["review_passed"] = (
                _normalize_text(decision_payload.get("result_acceptance"), default="")
                == "accept_current_result"
            )
            lifecycle_signals["review_failed"] = not lifecycle_signals["review_passed"]
            lifecycle_signals["manual_review_required"] = bool(decision_payload.get("whether_human_required", False))
            lifecycle_signals["global_stop_required"] = _normalize_text(
                decision_payload.get("next_action"),
                default="",
            ) in {"escalate_to_human", "rollback_required"}
            rollback_decision = _build_rollback_decision(
                unit_id=pr_id,
                signals=lifecycle_signals,
                decision_payload=decision_payload,
            )
            lifecycle_signals["rollback_required"] = rollback_decision.get("decision") == "required"
            commit_decision = _build_commit_decision(
                unit_id=pr_id,
                signals=lifecycle_signals,
                decision_payload=decision_payload,
            )
            lifecycle_signals["commit_allowed"] = commit_decision.get("decision") == "allowed"
            merge_decision = _build_merge_decision(
                unit_id=pr_id,
                signals=lifecycle_signals,
                decision_payload=decision_payload,
            )
            lifecycle_signals["merge_allowed"] = merge_decision.get("decision") == "allowed"
            lifecycle_signals["unit_blocked"] = any(
                value in {"blocked", "manual_required", "unknown"}
                for value in (
                    commit_decision.get("decision"),
                    merge_decision.get("decision"),
                    rollback_decision.get("decision"),
                )
            )
            checkpoint_decision = _build_checkpoint_decision(
                unit_id=pr_id,
                signals=lifecycle_signals,
                decision_payload=decision_payload,
            )
            lifecycle_signals["global_stop_required"] = bool(checkpoint_decision.get("global_stop_recommended", False))
            lifecycle_signals["manual_review_required"] = bool(
                checkpoint_decision.get("manual_intervention_required", False)
            )
            lifecycle_signals["run_paused"] = _normalize_text(
                checkpoint_decision.get("decision"),
                default="",
            ) in {"pause", "retry", "manual_review_required", "escalate", "global_stop_recommended"}
            unit_signal_registry[pr_id] = dict(lifecycle_signals)

            checkpoint_decision_path_text = _normalize_text(
                progression_record.get("checkpoint_decision_path"),
                default="",
            )
            commit_decision_path_text = _normalize_text(
                progression_record.get("commit_decision_path"), default=""
            )
            merge_decision_path_text = _normalize_text(
                progression_record.get("merge_decision_path"), default=""
            )
            rollback_decision_path_text = _normalize_text(
                progression_record.get("rollback_decision_path"), default=""
            )
            checkpoint_decision_path = Path(checkpoint_decision_path_text) if checkpoint_decision_path_text else None
            commit_decision_path = Path(commit_decision_path_text) if commit_decision_path_text else None
            merge_decision_path = Path(merge_decision_path_text) if merge_decision_path_text else None
            rollback_decision_path = Path(rollback_decision_path_text) if rollback_decision_path_text else None
            if checkpoint_decision_path is not None:
                _write_json(checkpoint_decision_path, checkpoint_decision)
            if commit_decision_path is not None:
                _write_json(commit_decision_path, commit_decision)
            if merge_decision_path is not None:
                _write_json(merge_decision_path, merge_decision)
            if rollback_decision_path is not None:
                _write_json(rollback_decision_path, rollback_decision)

            _append_progression_checkpoint(
                progression_payload,
                state=_UNIT_STATE_REVIEWED,
                now=self.now,
                reason="review_progression_outcome_evaluated",
                metadata={
                    "next_action": _normalize_text(decision_payload.get("next_action"), default=""),
                    "progression_outcome": _normalize_text(decision_payload.get("progression_outcome"), default=""),
                    "progression_rule_id": _normalize_text(decision_payload.get("progression_rule_id"), default=""),
                    "result_acceptance": _normalize_text(decision_payload.get("result_acceptance"), default=""),
                },
            )
            _append_progression_checkpoint(
                progression_payload,
                state="commit_evaluated",
                now=self.now,
                reason="commit_decision_artifact_written",
                metadata={
                    "commit_decision_path": str(commit_decision_path or ""),
                    "decision": _normalize_text(commit_decision.get("decision"), default=""),
                    "rule_id": _normalize_text(commit_decision.get("rule_id"), default=""),
                },
            )
            _append_progression_checkpoint(
                progression_payload,
                state="checkpoint_evaluated",
                now=self.now,
                reason="checkpoint_decision_artifact_written",
                metadata={
                    "checkpoint_decision_path": str(checkpoint_decision_path or ""),
                    "checkpoint_stage": _normalize_text(checkpoint_decision.get("checkpoint_stage"), default=""),
                    "decision": _normalize_text(checkpoint_decision.get("decision"), default=""),
                    "rule_id": _normalize_text(checkpoint_decision.get("rule_id"), default=""),
                    "manual_intervention_required": bool(
                        checkpoint_decision.get("manual_intervention_required", False)
                    ),
                    "global_stop_recommended": bool(checkpoint_decision.get("global_stop_recommended", False)),
                },
            )
            _append_progression_checkpoint(
                progression_payload,
                state="merge_evaluated",
                now=self.now,
                reason="merge_decision_artifact_written",
                metadata={
                    "merge_decision_path": str(merge_decision_path or ""),
                    "decision": _normalize_text(merge_decision.get("decision"), default=""),
                    "rule_id": _normalize_text(merge_decision.get("rule_id"), default=""),
                },
            )
            _append_progression_checkpoint(
                progression_payload,
                state="rollback_evaluated",
                now=self.now,
                reason="rollback_decision_artifact_written",
                metadata={
                    "rollback_decision_path": str(rollback_decision_path or ""),
                    "decision": _normalize_text(rollback_decision.get("decision"), default=""),
                    "rule_id": _normalize_text(rollback_decision.get("rule_id"), default=""),
                },
            )
            if review_terminal_state in {_UNIT_STATE_ADVANCED, _UNIT_STATE_ESCALATED}:
                _append_progression_checkpoint(
                    progression_payload,
                    state=review_terminal_state,
                    now=self.now,
                    reason="review_terminal_state_resolved",
                    metadata={
                        "next_action": _normalize_text(decision_payload.get("next_action"), default=""),
                    },
                )
            _write_json(Path(progression_path_text), progression_payload)
            entry["unit_progression_state"] = _normalize_text(
                progression_payload.get("current_state"),
                default=review_terminal_state,
            )
            entry["decision_summary"] = {
                "checkpoint_decision": _normalize_text(checkpoint_decision.get("decision"), default="unknown"),
                "commit_decision": _normalize_text(commit_decision.get("decision"), default="unknown"),
                "merge_decision": _normalize_text(merge_decision.get("decision"), default="unknown"),
                "rollback_decision": _normalize_text(rollback_decision.get("decision"), default="unknown"),
            }
            entry["checkpoint_decision_path"] = str(checkpoint_decision_path or "")
            entry["checkpoint_summary"] = {
                "checkpoint_stage": _normalize_text(checkpoint_decision.get("checkpoint_stage"), default=""),
                "decision": _normalize_text(checkpoint_decision.get("decision"), default="unknown"),
                "rule_id": _normalize_text(checkpoint_decision.get("rule_id"), default=""),
                "manual_intervention_required": bool(
                    checkpoint_decision.get("manual_intervention_required", False)
                ),
                "global_stop_recommended": bool(checkpoint_decision.get("global_stop_recommended", False)),
            }

        run_state_path = run_root / "run_state.json"
        run_state_payload = _build_run_state_payload(
            run_id=resolved_job_id,
            run_status=run_status,
            next_action=_normalize_text(decision_payload.get("next_action"), default=""),
            reason=_normalize_text(decision_payload.get("reason"), default=""),
            total_units_planned=total_units_planned,
            manifest_units=manifest_units,
        )
        run_state_payload = _augment_run_state_with_objective_contract_summary(
            run_state_payload=run_state_payload,
            objective_contract_payload=objective_contract_payload,
        )
        # PR27 readiness gating overlays remain canonical for decision artifacts.
        # PR28 adds bounded commit execution only when readiness + run-level guardrails allow it.
        for entry in manifest_units:
            pr_id = _normalize_text(entry.get("pr_id"), default="")
            if not pr_id:
                continue
            lifecycle_signals = dict(unit_signal_registry.get(pr_id) or {})

            commit_path_text = _normalize_text(entry.get("commit_decision_path"), default="")
            merge_path_text = _normalize_text(entry.get("merge_decision_path"), default="")
            rollback_path_text = _normalize_text(entry.get("rollback_decision_path"), default="")
            if not commit_path_text or not merge_path_text or not rollback_path_text:
                continue

            commit_path = Path(commit_path_text)
            merge_path = Path(merge_path_text)
            rollback_path = Path(rollback_path_text)

            commit_decision_payload = _read_json_object_if_exists(commit_path)
            merge_decision_payload = _read_json_object_if_exists(merge_path)
            rollback_decision_payload = _read_json_object_if_exists(rollback_path)
            if (
                not isinstance(commit_decision_payload, Mapping)
                or not isinstance(merge_decision_payload, Mapping)
                or not isinstance(rollback_decision_payload, Mapping)
            ):
                continue

            commit_decision_overlay = _with_readiness_overlay(
                decision_kind="commit",
                decision_payload=commit_decision_payload,
                signals=lifecycle_signals,
                run_state_payload=run_state_payload,
            )
            merge_decision_overlay = _with_readiness_overlay(
                decision_kind="merge",
                decision_payload=merge_decision_payload,
                signals=lifecycle_signals,
                run_state_payload=run_state_payload,
                commit_readiness_status=_normalize_text(
                    commit_decision_overlay.get("readiness_status"),
                    default="",
                ),
            )
            rollback_decision_overlay = _with_readiness_overlay(
                decision_kind="rollback",
                decision_payload=rollback_decision_payload,
                signals=lifecycle_signals,
                run_state_payload=run_state_payload,
            )

            _write_json(commit_path, commit_decision_overlay)
            _write_json(merge_path, merge_decision_overlay)
            _write_json(rollback_path, rollback_decision_overlay)

            decision_summary = (
                dict(entry.get("decision_summary"))
                if isinstance(entry.get("decision_summary"), Mapping)
                else {}
            )
            decision_summary.update(
                {
                    "commit_decision": _normalize_text(
                        commit_decision_overlay.get("decision"),
                        default=decision_summary.get("commit_decision", "unknown"),
                    ),
                    "merge_decision": _normalize_text(
                        merge_decision_overlay.get("decision"),
                        default=decision_summary.get("merge_decision", "unknown"),
                    ),
                    "rollback_decision": _normalize_text(
                        rollback_decision_overlay.get("decision"),
                        default=decision_summary.get("rollback_decision", "unknown"),
                    ),
                    "commit_readiness_status": _normalize_text(
                        commit_decision_overlay.get("readiness_status"),
                        default="awaiting_prerequisites",
                    ),
                    "merge_readiness_status": _normalize_text(
                        merge_decision_overlay.get("readiness_status"),
                        default="awaiting_prerequisites",
                    ),
                    "rollback_readiness_status": _normalize_text(
                        rollback_decision_overlay.get("readiness_status"),
                        default="awaiting_prerequisites",
                    ),
                    "commit_readiness_next_action": _normalize_text(
                        commit_decision_overlay.get("readiness_next_action"),
                        default="hold",
                    ),
                    "merge_readiness_next_action": _normalize_text(
                        merge_decision_overlay.get("readiness_next_action"),
                        default="hold",
                    ),
                    "rollback_readiness_next_action": _normalize_text(
                        rollback_decision_overlay.get("readiness_next_action"),
                        default="hold",
                    ),
                    "commit_automation_eligible": bool(
                        commit_decision_overlay.get("automation_eligible", False)
                    ),
                    "merge_automation_eligible": bool(
                        merge_decision_overlay.get("automation_eligible", False)
                    ),
                    "rollback_automation_eligible": bool(
                        rollback_decision_overlay.get("automation_eligible", False)
                    ),
                    "commit_prerequisites_satisfied": bool(
                        commit_decision_overlay.get("prerequisites_satisfied", False)
                    ),
                    "merge_prerequisites_satisfied": bool(
                        merge_decision_overlay.get("prerequisites_satisfied", False)
                    ),
                    "rollback_prerequisites_satisfied": bool(
                        rollback_decision_overlay.get("prerequisites_satisfied", False)
                    ),
                    "commit_unresolved_blockers_count": len(
                        _normalize_string_list(commit_decision_overlay.get("unresolved_blockers"))
                    ),
                    "merge_unresolved_blockers_count": len(
                        _normalize_string_list(merge_decision_overlay.get("unresolved_blockers"))
                    ),
                    "rollback_unresolved_blockers_count": len(
                        _normalize_string_list(rollback_decision_overlay.get("unresolved_blockers"))
                    ),
                }
            )
            entry["decision_summary"] = decision_summary

        for entry in manifest_units:
            pr_id = _normalize_text(entry.get("pr_id"), default="")
            commit_decision_path_text = _normalize_text(entry.get("commit_decision_path"), default="")
            commit_execution_path_text = _normalize_text(entry.get("commit_execution_path"), default="")
            unit_progression_path_text = _normalize_text(entry.get("unit_progression_path"), default="")
            if not pr_id or not commit_decision_path_text or not commit_execution_path_text:
                continue

            commit_decision_payload = _read_json_object_if_exists(Path(commit_decision_path_text))
            if not isinstance(commit_decision_payload, Mapping):
                commit_execution_payload = _build_commit_execution_blocked_payload(
                    unit_id=pr_id,
                    now=self.now,
                    summary="commit execution blocked because commit decision artifact was missing",
                    failure_reason="commit_decision_artifact_missing",
                    blocking_reasons=["commit_decision_artifact_missing"],
                )
            else:
                commit_execution_payload = _execute_bounded_commit(
                    unit_id=pr_id,
                    job_id=resolved_job_id,
                    repo_path=resolved_execution_repo_path,
                    changed_files=_extract_changed_files_from_result(entry),
                    strict_scope_files=_extract_commit_scope_from_contract(entry),
                    run_state_payload=run_state_payload,
                    commit_decision=commit_decision_payload,
                    dry_run=dry_run,
                    now=self.now,
                )

            commit_execution_payload = _with_execution_gate_surface(commit_execution_payload)
            _write_json(Path(commit_execution_path_text), commit_execution_payload)
            if unit_progression_path_text:
                progression_path = Path(unit_progression_path_text)
                progression_payload = _read_json_object_if_exists(progression_path)
                if isinstance(progression_payload, Mapping):
                    progression_mutable = dict(progression_payload)
                    if bool(commit_execution_payload.get("attempted", False)):
                        _append_progression_checkpoint(
                            progression_mutable,
                            state="commit_execution_started",
                            now=self.now,
                            reason="commit_execution_started",
                            metadata={
                                "commit_execution_path": commit_execution_path_text,
                            },
                            update_current_state=False,
                        )
                    status = _normalize_text(commit_execution_payload.get("status"), default="")
                    if status == "succeeded":
                        _append_progression_checkpoint(
                            progression_mutable,
                            state="commit_executed",
                            now=self.now,
                            reason="commit_execution_succeeded",
                            metadata={
                                "commit_execution_path": commit_execution_path_text,
                                "commit_sha": _normalize_text(commit_execution_payload.get("commit_sha"), default=""),
                            },
                            update_current_state=False,
                        )
                    elif status == "failed":
                        _append_progression_checkpoint(
                            progression_mutable,
                            state="commit_execution_failed",
                            now=self.now,
                            reason="commit_execution_failed",
                            metadata={
                                "commit_execution_path": commit_execution_path_text,
                                "failure_reason": _normalize_text(
                                    commit_execution_payload.get("failure_reason"),
                                    default="",
                                ),
                            },
                            update_current_state=False,
                        )
                    _write_json(progression_path, progression_mutable)

            status = _normalize_text(commit_execution_payload.get("status"), default="blocked")
            if status not in _COMMIT_EXECUTION_STATUSES:
                status = "blocked"
            commit_execution_summary = {
                "status": status,
                "summary": _normalize_text(commit_execution_payload.get("summary"), default=""),
                "commit_sha": _normalize_text(commit_execution_payload.get("commit_sha"), default=""),
                "manual_intervention_required": bool(
                    commit_execution_payload.get("manual_intervention_required", False)
                ),
                "failure_reason": _normalize_text(commit_execution_payload.get("failure_reason"), default=""),
                "blocking_reasons": _normalize_string_list(commit_execution_payload.get("blocking_reasons")),
                "execution_allowed": bool(commit_execution_payload.get("execution_allowed", False)),
                "execution_authority_status": _normalize_text(
                    commit_execution_payload.get("execution_authority_status"), default="unknown"
                ),
                "validation_status": _normalize_text(commit_execution_payload.get("validation_status"), default="unknown"),
                "execution_gate_status": _normalize_text(
                    commit_execution_payload.get("execution_gate_status"), default="unknown"
                ),
                "authority_blocked_reason": _normalize_text(
                    commit_execution_payload.get("authority_blocked_reason"), default=""
                ),
                "validation_blocked_reason": _normalize_text(
                    commit_execution_payload.get("validation_blocked_reason"), default=""
                ),
                "manual_approval_required": bool(commit_execution_payload.get("manual_approval_required", False)),
                "authority_blocked_reasons": _normalize_string_list(
                    commit_execution_payload.get("authority_blocked_reasons")
                ),
                "validation_blocked_reasons": _normalize_string_list(
                    commit_execution_payload.get("validation_blocked_reasons")
                ),
                "missing_prerequisites": _normalize_string_list(
                    commit_execution_payload.get("missing_prerequisites")
                ),
                "missing_required_refs": _normalize_string_list(
                    commit_execution_payload.get("missing_required_refs")
                ),
                "unsafe_repo_state": _normalize_string_list(commit_execution_payload.get("unsafe_repo_state")),
                "remote_pr_ambiguity": _normalize_string_list(
                    commit_execution_payload.get("remote_pr_ambiguity")
                ),
            }
            entry["commit_execution_path"] = commit_execution_path_text
            entry["commit_execution_summary"] = commit_execution_summary
            decision_summary = (
                dict(entry.get("decision_summary"))
                if isinstance(entry.get("decision_summary"), Mapping)
                else {}
            )
            decision_summary["commit_execution_status"] = status
            decision_summary["commit_execution_manual_intervention_required"] = bool(
                commit_execution_payload.get("manual_intervention_required", False)
            )
            decision_summary["commit_execution_authority_status"] = _normalize_text(
                commit_execution_payload.get("execution_authority_status"),
                default="unknown",
            )
            decision_summary["commit_execution_validation_status"] = _normalize_text(
                commit_execution_payload.get("validation_status"),
                default="unknown",
            )
            entry["decision_summary"] = decision_summary

        for entry in manifest_units:
            pr_id = _normalize_text(entry.get("pr_id"), default="")
            commit_execution_path_text = _normalize_text(entry.get("commit_execution_path"), default="")
            push_execution_path_text = _normalize_text(entry.get("push_execution_path"), default="")
            unit_progression_path_text = _normalize_text(entry.get("unit_progression_path"), default="")
            if not pr_id or not commit_execution_path_text or not push_execution_path_text:
                continue

            commit_execution_payload = _read_json_object_if_exists(Path(commit_execution_path_text))
            if not isinstance(commit_execution_payload, Mapping):
                push_execution_payload = _build_delivery_execution_blocked_payload(
                    schema_version=_PUSH_EXECUTION_SCHEMA_VERSION,
                    execution_type=_PUSH_EXECUTION_TYPE,
                    unit_id=pr_id,
                    now=self.now,
                    summary="push execution blocked because commit execution artifact was missing",
                    failure_reason="commit_execution_artifact_missing",
                    blocking_reasons=["commit_execution_artifact_missing"],
                    base_branch=resolved_base_branch,
                    head_branch=configured_head_branch,
                    remote_name=configured_push_remote,
                )
            else:
                push_execution_payload = _execute_bounded_push(
                    unit_id=pr_id,
                    repo_path=resolved_execution_repo_path,
                    remote_name=configured_push_remote,
                    configured_head_branch=configured_head_branch,
                    base_branch=resolved_base_branch,
                    run_state_payload=run_state_payload,
                    commit_execution_payload=commit_execution_payload,
                    dry_run=dry_run,
                    now=self.now,
                )

            push_execution_payload = _with_execution_gate_surface(push_execution_payload)
            _write_json(Path(push_execution_path_text), push_execution_payload)
            if unit_progression_path_text:
                progression_path = Path(unit_progression_path_text)
                progression_payload = _read_json_object_if_exists(progression_path)
                if isinstance(progression_payload, Mapping):
                    progression_mutable = dict(progression_payload)
                    if bool(push_execution_payload.get("attempted", False)):
                        _append_progression_checkpoint(
                            progression_mutable,
                            state="push_execution_started",
                            now=self.now,
                            reason="push_execution_started",
                            metadata={"push_execution_path": push_execution_path_text},
                            update_current_state=False,
                        )
                    status = _normalize_text(push_execution_payload.get("status"), default="")
                    if status == "succeeded":
                        _append_progression_checkpoint(
                            progression_mutable,
                            state="push_executed",
                            now=self.now,
                            reason="push_execution_succeeded",
                            metadata={
                                "push_execution_path": push_execution_path_text,
                                "head_branch": _normalize_text(push_execution_payload.get("head_branch"), default=""),
                            },
                            update_current_state=False,
                        )
                    elif status == "failed":
                        _append_progression_checkpoint(
                            progression_mutable,
                            state="push_execution_failed",
                            now=self.now,
                            reason="push_execution_failed",
                            metadata={
                                "push_execution_path": push_execution_path_text,
                                "failure_reason": _normalize_text(
                                    push_execution_payload.get("failure_reason"),
                                    default="",
                                ),
                            },
                            update_current_state=False,
                        )
                    _write_json(progression_path, progression_mutable)

            push_status = _normalize_text(push_execution_payload.get("status"), default="blocked")
            if push_status not in _PUSH_EXECUTION_STATUSES:
                push_status = "blocked"
            push_execution_summary = {
                "status": push_status,
                "summary": _normalize_text(push_execution_payload.get("summary"), default=""),
                "branch_name": _normalize_text(push_execution_payload.get("branch_name"), default=""),
                "remote_name": _normalize_text(push_execution_payload.get("remote_name"), default=""),
                "head_branch": _normalize_text(push_execution_payload.get("head_branch"), default=""),
                "manual_intervention_required": bool(
                    push_execution_payload.get("manual_intervention_required", False)
                ),
                "failure_reason": _normalize_text(push_execution_payload.get("failure_reason"), default=""),
                "blocking_reasons": _normalize_string_list(push_execution_payload.get("blocking_reasons")),
                "execution_allowed": bool(push_execution_payload.get("execution_allowed", False)),
                "execution_authority_status": _normalize_text(
                    push_execution_payload.get("execution_authority_status"), default="unknown"
                ),
                "validation_status": _normalize_text(push_execution_payload.get("validation_status"), default="unknown"),
                "execution_gate_status": _normalize_text(
                    push_execution_payload.get("execution_gate_status"), default="unknown"
                ),
                "authority_blocked_reason": _normalize_text(
                    push_execution_payload.get("authority_blocked_reason"), default=""
                ),
                "validation_blocked_reason": _normalize_text(
                    push_execution_payload.get("validation_blocked_reason"), default=""
                ),
                "manual_approval_required": bool(push_execution_payload.get("manual_approval_required", False)),
                "authority_blocked_reasons": _normalize_string_list(
                    push_execution_payload.get("authority_blocked_reasons")
                ),
                "validation_blocked_reasons": _normalize_string_list(
                    push_execution_payload.get("validation_blocked_reasons")
                ),
                "missing_prerequisites": _normalize_string_list(push_execution_payload.get("missing_prerequisites")),
                "missing_required_refs": _normalize_string_list(push_execution_payload.get("missing_required_refs")),
                "unsafe_repo_state": _normalize_string_list(push_execution_payload.get("unsafe_repo_state")),
                "remote_pr_ambiguity": _normalize_string_list(push_execution_payload.get("remote_pr_ambiguity")),
                "remote_state_status": _normalize_text(push_execution_payload.get("remote_state_status"), default="unknown"),
                "remote_state_blocked": bool(push_execution_payload.get("remote_state_blocked", False)),
                "remote_state_blocked_reason": _normalize_text(
                    push_execution_payload.get("remote_state_blocked_reason"),
                    default="",
                ),
                "remote_state_missing_or_ambiguous": bool(
                    push_execution_payload.get("remote_state_missing_or_ambiguous", False)
                ),
                "upstream_tracking_status": _normalize_text(
                    push_execution_payload.get("upstream_tracking_status"),
                    default="unknown",
                ),
                "remote_divergence_status": _normalize_text(
                    push_execution_payload.get("remote_divergence_status"),
                    default="unknown",
                ),
                "remote_branch_status": _normalize_text(
                    push_execution_payload.get("remote_branch_status"),
                    default="unknown",
                ),
                "remote_github_status": _normalize_text(
                    push_execution_payload.get("remote_github_status"),
                    default="unknown",
                ),
                "remote_github_blocked": bool(push_execution_payload.get("remote_github_blocked", False)),
                "remote_github_blocked_reason": _normalize_text(
                    push_execution_payload.get("remote_github_blocked_reason"),
                    default="",
                ),
                "remote_github_blocked_reasons": _normalize_string_list(
                    push_execution_payload.get("remote_github_blocked_reasons")
                ),
                "remote_github_missing_or_ambiguous": bool(
                    push_execution_payload.get("remote_github_missing_or_ambiguous", False)
                ),
            }
            entry["push_execution_path"] = push_execution_path_text
            entry["push_execution_summary"] = push_execution_summary
            decision_summary = (
                dict(entry.get("decision_summary"))
                if isinstance(entry.get("decision_summary"), Mapping)
                else {}
            )
            decision_summary["push_execution_status"] = push_status
            decision_summary["push_execution_manual_intervention_required"] = bool(
                push_execution_payload.get("manual_intervention_required", False)
            )
            decision_summary["push_execution_authority_status"] = _normalize_text(
                push_execution_payload.get("execution_authority_status"),
                default="unknown",
            )
            decision_summary["push_execution_validation_status"] = _normalize_text(
                push_execution_payload.get("validation_status"),
                default="unknown",
            )
            entry["decision_summary"] = decision_summary

        for entry in manifest_units:
            pr_id = _normalize_text(entry.get("pr_id"), default="")
            merge_decision_path_text = _normalize_text(entry.get("merge_decision_path"), default="")
            commit_execution_path_text = _normalize_text(entry.get("commit_execution_path"), default="")
            push_execution_path_text = _normalize_text(entry.get("push_execution_path"), default="")
            pr_execution_path_text = _normalize_text(entry.get("pr_execution_path"), default="")
            unit_progression_path_text = _normalize_text(entry.get("unit_progression_path"), default="")
            if (
                not pr_id
                or not merge_decision_path_text
                or not commit_execution_path_text
                or not push_execution_path_text
                or not pr_execution_path_text
            ):
                continue

            merge_decision_payload = _read_json_object_if_exists(Path(merge_decision_path_text))
            commit_execution_payload = _read_json_object_if_exists(Path(commit_execution_path_text))
            push_execution_payload = _read_json_object_if_exists(Path(push_execution_path_text))
            if (
                not isinstance(merge_decision_payload, Mapping)
                or not isinstance(commit_execution_payload, Mapping)
                or not isinstance(push_execution_payload, Mapping)
            ):
                pr_execution_payload = _build_delivery_execution_blocked_payload(
                    schema_version=_PR_EXECUTION_SCHEMA_VERSION,
                    execution_type=_PR_EXECUTION_TYPE,
                    unit_id=pr_id,
                    now=self.now,
                    summary="PR creation blocked because prerequisite artifacts were missing",
                    failure_reason="pr_creation_prerequisite_artifact_missing",
                    blocking_reasons=["pr_creation_prerequisite_artifact_missing"],
                    base_branch=resolved_base_branch,
                    head_branch=configured_head_branch,
                    remote_name=configured_push_remote,
                )
            else:
                pr_execution_payload = _execute_bounded_pr_creation(
                    unit_id=pr_id,
                    job_id=resolved_job_id,
                    repository=resolved_repository,
                    base_branch=resolved_base_branch,
                    run_state_payload=run_state_payload,
                    merge_decision_payload=merge_decision_payload,
                    commit_execution_payload=commit_execution_payload,
                    push_execution_payload=push_execution_payload,
                    read_backend=self.github_read_backend,
                    write_backend=self.github_write_backend,
                    now=self.now,
                )

            pr_execution_payload = _with_execution_gate_surface(pr_execution_payload)
            _write_json(Path(pr_execution_path_text), pr_execution_payload)
            if unit_progression_path_text:
                progression_path = Path(unit_progression_path_text)
                progression_payload = _read_json_object_if_exists(progression_path)
                if isinstance(progression_payload, Mapping):
                    progression_mutable = dict(progression_payload)
                    if bool(pr_execution_payload.get("attempted", False)):
                        _append_progression_checkpoint(
                            progression_mutable,
                            state="pr_creation_started",
                            now=self.now,
                            reason="pr_creation_started",
                            metadata={"pr_execution_path": pr_execution_path_text},
                            update_current_state=False,
                        )
                    status = _normalize_text(pr_execution_payload.get("status"), default="")
                    if status == "succeeded":
                        _append_progression_checkpoint(
                            progression_mutable,
                            state="pr_created",
                            now=self.now,
                            reason="pr_creation_succeeded",
                            metadata={
                                "pr_execution_path": pr_execution_path_text,
                                "pr_number": _as_optional_int(pr_execution_payload.get("pr_number")),
                            },
                            update_current_state=False,
                        )
                    elif status == "failed":
                        _append_progression_checkpoint(
                            progression_mutable,
                            state="pr_creation_failed",
                            now=self.now,
                            reason="pr_creation_failed",
                            metadata={
                                "pr_execution_path": pr_execution_path_text,
                                "failure_reason": _normalize_text(
                                    pr_execution_payload.get("failure_reason"),
                                    default="",
                                ),
                            },
                            update_current_state=False,
                        )
                    _write_json(progression_path, progression_mutable)

            pr_status = _normalize_text(pr_execution_payload.get("status"), default="blocked")
            if pr_status not in _PR_EXECUTION_STATUSES:
                pr_status = "blocked"
            pr_execution_summary = {
                "status": pr_status,
                "summary": _normalize_text(pr_execution_payload.get("summary"), default=""),
                "pr_number": _as_optional_int(pr_execution_payload.get("pr_number")),
                "pr_url": _normalize_text(pr_execution_payload.get("pr_url"), default=""),
                "head_branch": _normalize_text(pr_execution_payload.get("head_branch"), default=""),
                "base_branch": _normalize_text(pr_execution_payload.get("base_branch"), default=""),
                "manual_intervention_required": bool(
                    pr_execution_payload.get("manual_intervention_required", False)
                ),
                "failure_reason": _normalize_text(pr_execution_payload.get("failure_reason"), default=""),
                "blocking_reasons": _normalize_string_list(pr_execution_payload.get("blocking_reasons")),
                "execution_allowed": bool(pr_execution_payload.get("execution_allowed", False)),
                "execution_authority_status": _normalize_text(
                    pr_execution_payload.get("execution_authority_status"), default="unknown"
                ),
                "validation_status": _normalize_text(pr_execution_payload.get("validation_status"), default="unknown"),
                "execution_gate_status": _normalize_text(
                    pr_execution_payload.get("execution_gate_status"), default="unknown"
                ),
                "authority_blocked_reason": _normalize_text(
                    pr_execution_payload.get("authority_blocked_reason"), default=""
                ),
                "validation_blocked_reason": _normalize_text(
                    pr_execution_payload.get("validation_blocked_reason"), default=""
                ),
                "manual_approval_required": bool(pr_execution_payload.get("manual_approval_required", False)),
                "authority_blocked_reasons": _normalize_string_list(
                    pr_execution_payload.get("authority_blocked_reasons")
                ),
                "validation_blocked_reasons": _normalize_string_list(
                    pr_execution_payload.get("validation_blocked_reasons")
                ),
                "missing_prerequisites": _normalize_string_list(pr_execution_payload.get("missing_prerequisites")),
                "missing_required_refs": _normalize_string_list(pr_execution_payload.get("missing_required_refs")),
                "unsafe_repo_state": _normalize_string_list(pr_execution_payload.get("unsafe_repo_state")),
                "remote_pr_ambiguity": _normalize_string_list(pr_execution_payload.get("remote_pr_ambiguity")),
                "existing_pr_status": _normalize_text(
                    pr_execution_payload.get("existing_pr_status"),
                    default="unknown",
                ),
                "pr_creation_state_status": _normalize_text(
                    pr_execution_payload.get("pr_creation_state_status"),
                    default="unknown",
                ),
                "pr_duplication_risk": _normalize_text(
                    pr_execution_payload.get("pr_duplication_risk"),
                    default="unknown",
                ),
                "remote_state_status": _normalize_text(pr_execution_payload.get("remote_state_status"), default="unknown"),
                "remote_state_blocked": bool(pr_execution_payload.get("remote_state_blocked", False)),
                "remote_state_blocked_reason": _normalize_text(
                    pr_execution_payload.get("remote_state_blocked_reason"),
                    default="",
                ),
                "remote_state_missing_or_ambiguous": bool(
                    pr_execution_payload.get("remote_state_missing_or_ambiguous", False)
                ),
                "github_state_status": _normalize_text(
                    pr_execution_payload.get("github_state_status"),
                    default="unknown",
                ),
                "github_state_unavailable": bool(
                    pr_execution_payload.get("github_state_unavailable", False)
                ),
                "remote_github_status": _normalize_text(
                    pr_execution_payload.get("remote_github_status"),
                    default="unknown",
                ),
                "remote_github_blocked": bool(pr_execution_payload.get("remote_github_blocked", False)),
                "remote_github_blocked_reason": _normalize_text(
                    pr_execution_payload.get("remote_github_blocked_reason"),
                    default="",
                ),
                "remote_github_blocked_reasons": _normalize_string_list(
                    pr_execution_payload.get("remote_github_blocked_reasons")
                ),
                "remote_github_missing_or_ambiguous": bool(
                    pr_execution_payload.get("remote_github_missing_or_ambiguous", False)
                ),
            }
            entry["pr_execution_path"] = pr_execution_path_text
            entry["pr_execution_summary"] = pr_execution_summary
            decision_summary = (
                dict(entry.get("decision_summary"))
                if isinstance(entry.get("decision_summary"), Mapping)
                else {}
            )
            decision_summary["pr_execution_status"] = pr_status
            decision_summary["pr_execution_manual_intervention_required"] = bool(
                pr_execution_payload.get("manual_intervention_required", False)
            )
            decision_summary["pr_execution_authority_status"] = _normalize_text(
                pr_execution_payload.get("execution_authority_status"),
                default="unknown",
            )
            decision_summary["pr_execution_validation_status"] = _normalize_text(
                pr_execution_payload.get("validation_status"),
                default="unknown",
            )
            decision_summary["pr_execution_pr_number"] = _as_optional_int(pr_execution_payload.get("pr_number"))
            entry["decision_summary"] = decision_summary

            if isinstance(merge_decision_payload, Mapping):
                merge_decision_effective = _resolve_merge_decision_for_execution(
                    merge_decision_payload=merge_decision_payload,
                    push_execution_payload=push_execution_payload if isinstance(push_execution_payload, Mapping) else {},
                    pr_execution_payload=pr_execution_payload,
                    commit_execution_payload=commit_execution_payload if isinstance(commit_execution_payload, Mapping) else {},
                    run_state_payload=run_state_payload,
                )
                _write_json(Path(merge_decision_path_text), merge_decision_effective)
                decision_summary["merge_decision"] = _normalize_text(
                    merge_decision_effective.get("decision"),
                    default=decision_summary.get("merge_decision", "unknown"),
                )
                decision_summary["merge_readiness_status"] = _normalize_text(
                    merge_decision_effective.get("readiness_status"),
                    default=decision_summary.get("merge_readiness_status", "awaiting_prerequisites"),
                )
                decision_summary["merge_readiness_next_action"] = _normalize_text(
                    merge_decision_effective.get("readiness_next_action"),
                    default=decision_summary.get("merge_readiness_next_action", "hold"),
                )
                decision_summary["merge_automation_eligible"] = bool(
                    merge_decision_effective.get("automation_eligible", False)
                )
                decision_summary["merge_prerequisites_satisfied"] = bool(
                    merge_decision_effective.get("prerequisites_satisfied", False)
                )
                decision_summary["merge_unresolved_blockers_count"] = len(
                    _normalize_string_list(merge_decision_effective.get("unresolved_blockers"))
                )
                entry["decision_summary"] = decision_summary

        for entry in manifest_units:
            pr_id = _normalize_text(entry.get("pr_id"), default="")
            merge_decision_path_text = _normalize_text(entry.get("merge_decision_path"), default="")
            commit_execution_path_text = _normalize_text(entry.get("commit_execution_path"), default="")
            push_execution_path_text = _normalize_text(entry.get("push_execution_path"), default="")
            pr_execution_path_text = _normalize_text(entry.get("pr_execution_path"), default="")
            merge_execution_path_text = _normalize_text(entry.get("merge_execution_path"), default="")
            unit_progression_path_text = _normalize_text(entry.get("unit_progression_path"), default="")
            if (
                not pr_id
                or not merge_decision_path_text
                or not commit_execution_path_text
                or not push_execution_path_text
                or not pr_execution_path_text
                or not merge_execution_path_text
            ):
                continue

            merge_decision_payload = _read_json_object_if_exists(Path(merge_decision_path_text))
            commit_execution_payload = _read_json_object_if_exists(Path(commit_execution_path_text))
            push_execution_payload = _read_json_object_if_exists(Path(push_execution_path_text))
            pr_execution_payload = _read_json_object_if_exists(Path(pr_execution_path_text))
            if (
                not isinstance(merge_decision_payload, Mapping)
                or not isinstance(commit_execution_payload, Mapping)
                or not isinstance(push_execution_payload, Mapping)
                or not isinstance(pr_execution_payload, Mapping)
            ):
                merge_execution_payload = _build_delivery_execution_blocked_payload(
                    schema_version=_MERGE_EXECUTION_SCHEMA_VERSION,
                    execution_type=_MERGE_EXECUTION_TYPE,
                    unit_id=pr_id,
                    now=self.now,
                    summary="merge execution blocked because prerequisite artifacts were missing",
                    failure_reason="merge_prerequisite_artifact_missing",
                    blocking_reasons=["merge_prerequisite_artifact_missing"],
                    base_branch=resolved_base_branch,
                    head_branch=configured_head_branch,
                    remote_name=configured_push_remote,
                )
            else:
                merge_execution_payload = _execute_bounded_merge(
                    unit_id=pr_id,
                    repository=resolved_repository,
                    run_state_payload=run_state_payload,
                    merge_decision_payload=merge_decision_payload,
                    commit_execution_payload=commit_execution_payload,
                    push_execution_payload=push_execution_payload,
                    pr_execution_payload=pr_execution_payload,
                    read_backend=self.github_read_backend,
                    write_backend=self.github_write_backend,
                    now=self.now,
                )

            merge_execution_payload = _with_execution_gate_surface(merge_execution_payload)
            _write_json(Path(merge_execution_path_text), merge_execution_payload)
            if unit_progression_path_text:
                progression_path = Path(unit_progression_path_text)
                progression_payload = _read_json_object_if_exists(progression_path)
                if isinstance(progression_payload, Mapping):
                    progression_mutable = dict(progression_payload)
                    if bool(merge_execution_payload.get("attempted", False)):
                        _append_progression_checkpoint(
                            progression_mutable,
                            state="merge_execution_started",
                            now=self.now,
                            reason="merge_execution_started",
                            metadata={"merge_execution_path": merge_execution_path_text},
                            update_current_state=False,
                        )
                    status = _normalize_text(merge_execution_payload.get("status"), default="")
                    if status == "succeeded":
                        _append_progression_checkpoint(
                            progression_mutable,
                            state="merge_executed",
                            now=self.now,
                            reason="merge_execution_succeeded",
                            metadata={
                                "merge_execution_path": merge_execution_path_text,
                                "merge_commit_sha": _normalize_text(
                                    merge_execution_payload.get("merge_commit_sha"),
                                    default="",
                                ),
                            },
                            update_current_state=False,
                        )
                    elif status == "failed":
                        _append_progression_checkpoint(
                            progression_mutable,
                            state="merge_execution_failed",
                            now=self.now,
                            reason="merge_execution_failed",
                            metadata={
                                "merge_execution_path": merge_execution_path_text,
                                "failure_reason": _normalize_text(
                                    merge_execution_payload.get("failure_reason"),
                                    default="",
                                ),
                            },
                            update_current_state=False,
                        )
                    _write_json(progression_path, progression_mutable)

            merge_status = _normalize_text(merge_execution_payload.get("status"), default="blocked")
            if merge_status not in _MERGE_EXECUTION_STATUSES:
                merge_status = "blocked"
            merge_execution_summary = {
                "status": merge_status,
                "summary": _normalize_text(merge_execution_payload.get("summary"), default=""),
                "pr_number": _as_optional_int(merge_execution_payload.get("pr_number")),
                "merge_commit_sha": _normalize_text(merge_execution_payload.get("merge_commit_sha"), default=""),
                "manual_intervention_required": bool(
                    merge_execution_payload.get("manual_intervention_required", False)
                ),
                "failure_reason": _normalize_text(merge_execution_payload.get("failure_reason"), default=""),
                "blocking_reasons": _normalize_string_list(merge_execution_payload.get("blocking_reasons")),
                "execution_allowed": bool(merge_execution_payload.get("execution_allowed", False)),
                "execution_authority_status": _normalize_text(
                    merge_execution_payload.get("execution_authority_status"), default="unknown"
                ),
                "validation_status": _normalize_text(merge_execution_payload.get("validation_status"), default="unknown"),
                "execution_gate_status": _normalize_text(
                    merge_execution_payload.get("execution_gate_status"), default="unknown"
                ),
                "authority_blocked_reason": _normalize_text(
                    merge_execution_payload.get("authority_blocked_reason"), default=""
                ),
                "validation_blocked_reason": _normalize_text(
                    merge_execution_payload.get("validation_blocked_reason"), default=""
                ),
                "manual_approval_required": bool(merge_execution_payload.get("manual_approval_required", False)),
                "authority_blocked_reasons": _normalize_string_list(
                    merge_execution_payload.get("authority_blocked_reasons")
                ),
                "validation_blocked_reasons": _normalize_string_list(
                    merge_execution_payload.get("validation_blocked_reasons")
                ),
                "missing_prerequisites": _normalize_string_list(
                    merge_execution_payload.get("missing_prerequisites")
                ),
                "missing_required_refs": _normalize_string_list(
                    merge_execution_payload.get("missing_required_refs")
                ),
                "unsafe_repo_state": _normalize_string_list(merge_execution_payload.get("unsafe_repo_state")),
                "remote_pr_ambiguity": _normalize_string_list(merge_execution_payload.get("remote_pr_ambiguity")),
                "mergeability_status": _normalize_text(
                    merge_execution_payload.get("mergeability_status"),
                    default="unknown",
                ),
                "merge_requirements_status": _normalize_text(
                    merge_execution_payload.get("merge_requirements_status"),
                    default="unknown",
                ),
                "required_checks_status": _normalize_text(
                    merge_execution_payload.get("required_checks_status"),
                    default="unknown",
                ),
                "review_state_status": _normalize_text(
                    merge_execution_payload.get("review_state_status"),
                    default="unknown",
                ),
                "branch_protection_status": _normalize_text(
                    merge_execution_payload.get("branch_protection_status"),
                    default="unknown",
                ),
                "remote_state_status": _normalize_text(
                    merge_execution_payload.get("remote_state_status"),
                    default="unknown",
                ),
                "remote_state_blocked": bool(merge_execution_payload.get("remote_state_blocked", False)),
                "remote_state_blocked_reason": _normalize_text(
                    merge_execution_payload.get("remote_state_blocked_reason"),
                    default="",
                ),
                "remote_state_missing_or_ambiguous": bool(
                    merge_execution_payload.get("remote_state_missing_or_ambiguous", False)
                ),
                "github_state_status": _normalize_text(
                    merge_execution_payload.get("github_state_status"),
                    default="unknown",
                ),
                "github_state_unavailable": bool(
                    merge_execution_payload.get("github_state_unavailable", False)
                ),
                "remote_github_status": _normalize_text(
                    merge_execution_payload.get("remote_github_status"),
                    default="unknown",
                ),
                "remote_github_blocked": bool(merge_execution_payload.get("remote_github_blocked", False)),
                "remote_github_blocked_reason": _normalize_text(
                    merge_execution_payload.get("remote_github_blocked_reason"),
                    default="",
                ),
                "remote_github_blocked_reasons": _normalize_string_list(
                    merge_execution_payload.get("remote_github_blocked_reasons")
                ),
                "remote_github_missing_or_ambiguous": bool(
                    merge_execution_payload.get("remote_github_missing_or_ambiguous", False)
                ),
            }
            entry["merge_execution_path"] = merge_execution_path_text
            entry["merge_execution_summary"] = merge_execution_summary
            decision_summary = (
                dict(entry.get("decision_summary"))
                if isinstance(entry.get("decision_summary"), Mapping)
                else {}
            )
            decision_summary["merge_execution_status"] = merge_status
            decision_summary["merge_execution_manual_intervention_required"] = bool(
                merge_execution_payload.get("manual_intervention_required", False)
            )
            decision_summary["merge_execution_authority_status"] = _normalize_text(
                merge_execution_payload.get("execution_authority_status"),
                default="unknown",
            )
            decision_summary["merge_execution_validation_status"] = _normalize_text(
                merge_execution_payload.get("validation_status"),
                default="unknown",
            )
            entry["decision_summary"] = decision_summary

        for entry in manifest_units:
            pr_id = _normalize_text(entry.get("pr_id"), default="")
            rollback_decision_path_text = _normalize_text(entry.get("rollback_decision_path"), default="")
            commit_execution_path_text = _normalize_text(entry.get("commit_execution_path"), default="")
            push_execution_path_text = _normalize_text(entry.get("push_execution_path"), default="")
            pr_execution_path_text = _normalize_text(entry.get("pr_execution_path"), default="")
            merge_execution_path_text = _normalize_text(entry.get("merge_execution_path"), default="")
            rollback_execution_path_text = _normalize_text(entry.get("rollback_execution_path"), default="")
            unit_progression_path_text = _normalize_text(entry.get("unit_progression_path"), default="")
            if (
                not pr_id
                or not rollback_decision_path_text
                or not rollback_execution_path_text
            ):
                continue

            rollback_decision_payload = _read_json_object_if_exists(Path(rollback_decision_path_text))
            commit_execution_payload = _read_json_object_if_exists(Path(commit_execution_path_text)) if commit_execution_path_text else None
            push_execution_payload = _read_json_object_if_exists(Path(push_execution_path_text)) if push_execution_path_text else None
            pr_execution_payload = _read_json_object_if_exists(Path(pr_execution_path_text)) if pr_execution_path_text else None
            merge_execution_payload = _read_json_object_if_exists(Path(merge_execution_path_text)) if merge_execution_path_text else None

            if not isinstance(rollback_decision_payload, Mapping):
                rollback_execution_payload = _build_rollback_execution_blocked_payload(
                    unit_id=pr_id,
                    now=self.now,
                    rollback_mode="unknown",
                    summary="rollback execution blocked because rollback decision artifact was missing",
                    failure_reason="rollback_decision_artifact_missing",
                    blocking_reasons=["rollback_decision_artifact_missing"],
                    trigger_reason="rollback_required",
                    manual_intervention_required=True,
                )
            else:
                rollback_execution_payload = _execute_bounded_rollback(
                    unit_id=pr_id,
                    repo_path=resolved_execution_repo_path,
                    run_state_payload=run_state_payload,
                    rollback_decision_payload=rollback_decision_payload,
                    commit_execution_payload=(
                        commit_execution_payload if isinstance(commit_execution_payload, Mapping) else None
                    ),
                    push_execution_payload=(
                        push_execution_payload if isinstance(push_execution_payload, Mapping) else None
                    ),
                    pr_execution_payload=(
                        pr_execution_payload if isinstance(pr_execution_payload, Mapping) else None
                    ),
                    merge_execution_payload=(
                        merge_execution_payload if isinstance(merge_execution_payload, Mapping) else None
                    ),
                    dry_run=dry_run,
                    now=self.now,
                )

            rollback_execution_payload = _with_execution_gate_surface(rollback_execution_payload)
            rollback_execution_payload = _with_rollback_aftermath_surface(rollback_execution_payload)
            _write_json(Path(rollback_execution_path_text), rollback_execution_payload)
            if unit_progression_path_text:
                progression_path = Path(unit_progression_path_text)
                progression_payload = _read_json_object_if_exists(progression_path)
                if isinstance(progression_payload, Mapping):
                    progression_mutable = dict(progression_payload)
                    if bool(rollback_execution_payload.get("attempted", False)):
                        _append_progression_checkpoint(
                            progression_mutable,
                            state="rollback_execution_started",
                            now=self.now,
                            reason="rollback_execution_started",
                            metadata={"rollback_execution_path": rollback_execution_path_text},
                            update_current_state=False,
                        )
                    status = _normalize_text(rollback_execution_payload.get("status"), default="")
                    if status == "succeeded":
                        _append_progression_checkpoint(
                            progression_mutable,
                            state="rollback_executed",
                            now=self.now,
                            reason="rollback_execution_succeeded",
                            metadata={
                                "rollback_execution_path": rollback_execution_path_text,
                                "rollback_mode": _normalize_text(
                                    rollback_execution_payload.get("rollback_mode"),
                                    default="unknown",
                                ),
                                "resulting_commit_sha": _normalize_text(
                                    rollback_execution_payload.get("resulting_commit_sha"),
                                    default="",
                                ),
                            },
                            update_current_state=False,
                        )
                    elif status == "failed":
                        _append_progression_checkpoint(
                            progression_mutable,
                            state="rollback_execution_failed",
                            now=self.now,
                            reason="rollback_execution_failed",
                            metadata={
                                "rollback_execution_path": rollback_execution_path_text,
                                "failure_reason": _normalize_text(
                                    rollback_execution_payload.get("failure_reason"),
                                    default="",
                                ),
                            },
                            update_current_state=False,
                        )
                    _write_json(progression_path, progression_mutable)

            rollback_status = _normalize_text(rollback_execution_payload.get("status"), default="blocked")
            if rollback_status not in _ROLLBACK_EXECUTION_STATUSES:
                rollback_status = "blocked"
            rollback_execution_summary = {
                "status": rollback_status,
                "summary": _normalize_text(rollback_execution_payload.get("summary"), default=""),
                "rollback_mode": _normalize_text(rollback_execution_payload.get("rollback_mode"), default="unknown"),
                "rollback_aftermath_status": _normalize_text(
                    rollback_execution_payload.get("rollback_aftermath_status"),
                    default="incomplete",
                ),
                "rollback_aftermath_blocked": bool(
                    rollback_execution_payload.get("rollback_aftermath_blocked", True)
                ),
                "rollback_aftermath_blocked_reason": _normalize_text(
                    rollback_execution_payload.get("rollback_aftermath_blocked_reason"),
                    default="",
                ),
                "rollback_aftermath_blocked_reasons": _normalize_string_list(
                    rollback_execution_payload.get("rollback_aftermath_blocked_reasons")
                ),
                "rollback_aftermath_missing_or_ambiguous": bool(
                    rollback_execution_payload.get("rollback_aftermath_missing_or_ambiguous", True)
                ),
                "rollback_validation_status": _normalize_text(
                    rollback_execution_payload.get("rollback_validation_status"),
                    default="unavailable",
                ),
                "rollback_manual_followup_required": bool(
                    rollback_execution_payload.get("rollback_manual_followup_required", False)
                ),
                "rollback_remote_followup_required": bool(
                    rollback_execution_payload.get("rollback_remote_followup_required", False)
                ),
                "rollback_conflict_status": _normalize_text(
                    rollback_execution_payload.get("rollback_conflict_status"),
                    default="unknown",
                ),
                "rollback_remote_state_status": _normalize_text(
                    rollback_execution_payload.get("rollback_remote_state_status"),
                    default="unknown",
                ),
                "rollback_divergence_status": _normalize_text(
                    rollback_execution_payload.get("rollback_divergence_status"),
                    default="unknown",
                ),
                "rollback_pr_state_status": _normalize_text(
                    rollback_execution_payload.get("rollback_pr_state_status"),
                    default="unknown",
                ),
                "rollback_branch_state_status": _normalize_text(
                    rollback_execution_payload.get("rollback_branch_state_status"),
                    default="unknown",
                ),
                "rollback_repo_cleanliness_status": _normalize_text(
                    rollback_execution_payload.get("rollback_repo_cleanliness_status"),
                    default="unknown",
                ),
                "rollback_head_state_status": _normalize_text(
                    rollback_execution_payload.get("rollback_head_state_status"),
                    default="unknown",
                ),
                "rollback_revert_commit_status": _normalize_text(
                    rollback_execution_payload.get("rollback_revert_commit_status"),
                    default="unknown",
                ),
                "rollback_post_validation_status": _normalize_text(
                    rollback_execution_payload.get("rollback_post_validation_status"),
                    default="unavailable",
                ),
                "rollback_remote_github_status": _normalize_text(
                    rollback_execution_payload.get("rollback_remote_github_status"),
                    default="unknown",
                ),
                "resulting_commit_sha": _normalize_text(
                    rollback_execution_payload.get("resulting_commit_sha"),
                    default="",
                ),
                "manual_intervention_required": bool(
                    rollback_execution_payload.get("manual_intervention_required", False)
                ),
                "replan_required": bool(rollback_execution_payload.get("replan_required", False)),
                "automatic_continuation_blocked": bool(
                    rollback_execution_payload.get("automatic_continuation_blocked", True)
                ),
                "failure_reason": _normalize_text(
                    rollback_execution_payload.get("failure_reason"),
                    default="",
                ),
                "attempted": bool(rollback_execution_payload.get("attempted", False)),
                "blocking_reasons": _normalize_string_list(rollback_execution_payload.get("blocking_reasons")),
                "execution_allowed": bool(rollback_execution_payload.get("execution_allowed", False)),
                "execution_authority_status": _normalize_text(
                    rollback_execution_payload.get("execution_authority_status"), default="unknown"
                ),
                "validation_status": _normalize_text(
                    rollback_execution_payload.get("validation_status"), default="unknown"
                ),
                "execution_gate_status": _normalize_text(
                    rollback_execution_payload.get("execution_gate_status"), default="unknown"
                ),
                "authority_blocked_reason": _normalize_text(
                    rollback_execution_payload.get("authority_blocked_reason"), default=""
                ),
                "validation_blocked_reason": _normalize_text(
                    rollback_execution_payload.get("validation_blocked_reason"), default=""
                ),
                "manual_approval_required": bool(rollback_execution_payload.get("manual_approval_required", False)),
                "authority_blocked_reasons": _normalize_string_list(
                    rollback_execution_payload.get("authority_blocked_reasons")
                ),
                "validation_blocked_reasons": _normalize_string_list(
                    rollback_execution_payload.get("validation_blocked_reasons")
                ),
                "missing_prerequisites": _normalize_string_list(
                    rollback_execution_payload.get("missing_prerequisites")
                ),
                "missing_required_refs": _normalize_string_list(
                    rollback_execution_payload.get("missing_required_refs")
                ),
                "unsafe_repo_state": _normalize_string_list(rollback_execution_payload.get("unsafe_repo_state")),
                "remote_pr_ambiguity": _normalize_string_list(
                    rollback_execution_payload.get("remote_pr_ambiguity")
                ),
            }
            entry["rollback_execution_path"] = rollback_execution_path_text
            entry["rollback_execution_summary"] = rollback_execution_summary
            decision_summary = (
                dict(entry.get("decision_summary"))
                if isinstance(entry.get("decision_summary"), Mapping)
                else {}
            )
            decision_summary["rollback_execution_status"] = rollback_status
            decision_summary["rollback_execution_manual_intervention_required"] = bool(
                rollback_execution_payload.get("manual_intervention_required", False)
            )
            decision_summary["rollback_execution_mode"] = _normalize_text(
                rollback_execution_payload.get("rollback_mode"),
                default="unknown",
            )
            decision_summary["rollback_execution_authority_status"] = _normalize_text(
                rollback_execution_payload.get("execution_authority_status"),
                default="unknown",
            )
            decision_summary["rollback_execution_validation_status"] = _normalize_text(
                rollback_execution_payload.get("validation_status"),
                default="unknown",
            )
            decision_summary["rollback_aftermath_status"] = _normalize_text(
                rollback_execution_payload.get("rollback_aftermath_status"),
                default="incomplete",
            )
            decision_summary["rollback_validation_status"] = _normalize_text(
                rollback_execution_payload.get("rollback_validation_status"),
                default="unavailable",
            )
            decision_summary["rollback_manual_followup_required"] = bool(
                rollback_execution_payload.get("rollback_manual_followup_required", False)
            )
            decision_summary["rollback_remote_followup_required"] = bool(
                rollback_execution_payload.get("rollback_remote_followup_required", False)
            )
            entry["decision_summary"] = decision_summary

        run_state_payload = _augment_run_state_with_readiness(
            run_state_payload=run_state_payload,
            manifest_units=manifest_units,
        )
        run_state_payload = _augment_run_state_with_commit_execution(
            run_state_payload=run_state_payload,
            manifest_units=manifest_units,
        )
        run_state_payload = _augment_run_state_with_delivery_execution(
            run_state_payload=run_state_payload,
            manifest_units=manifest_units,
        )
        run_state_payload = _augment_run_state_with_rollback_execution(
            run_state_payload=run_state_payload,
            manifest_units=manifest_units,
        )
        run_state_payload = _augment_run_state_with_rollback_aftermath(
            run_state_payload=run_state_payload,
            manifest_units=manifest_units,
        )
        run_state_payload = _augment_run_state_with_authority_validation(
            run_state_payload=run_state_payload,
            manifest_units=manifest_units,
        )
        run_state_payload = _augment_run_state_with_remote_github(
            run_state_payload=run_state_payload,
            manifest_units=manifest_units,
        )
        run_state_payload = _augment_run_state_with_closed_loop(
            run_state_payload=run_state_payload,
            manifest_units=manifest_units,
            run_status=run_status,
        )
        run_state_payload = _augment_run_state_with_policy_overlay(
            run_state_payload=run_state_payload,
        )
        run_state_payload = _augment_run_state_with_lifecycle_terminal_contract(
            run_state_payload=run_state_payload,
        )
        completion_contract_path = run_root / "completion_contract.json"
        completion_contract_payload = build_completion_contract_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            run_state_payload=run_state_payload,
            artifact_presence={
                "objective_contract.json": objective_contract_path.exists(),
                "run_state.json": True,
                "next_action.json": decision_path.exists(),
                "manifest.json": manifest_path.exists(),
            },
        )
        _write_json(completion_contract_path, completion_contract_payload)
        run_state_payload = _augment_run_state_with_completion_contract_summary(
            run_state_payload=run_state_payload,
            completion_contract_payload=completion_contract_payload,
        )
        approval_transport_path = run_root / "approval_transport.json"
        approval_transport_payload = build_approval_transport_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            completion_contract_payload=completion_contract_payload,
            run_state_payload=run_state_payload,
            approval_input_payload=approval_input_payload,
            evaluated_at=_normalize_text(run_state_payload.get("updated_at"), default=_iso_now(self.now)),
        )
        _write_json(approval_transport_path, approval_transport_payload)
        run_state_payload = _augment_run_state_with_approval_transport_summary(
            run_state_payload=run_state_payload,
            approval_transport_payload=approval_transport_payload,
        )
        reconcile_contract_path = run_root / "reconcile_contract.json"
        reconcile_contract_payload = build_reconcile_contract_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            completion_contract_payload=completion_contract_payload,
            approval_transport_payload=approval_transport_payload,
            run_state_payload=run_state_payload,
            artifact_presence={
                "objective_contract.json": objective_contract_path.exists(),
                "completion_contract.json": completion_contract_path.exists(),
                "approval_transport.json": approval_transport_path.exists(),
                "run_state.json": True,
            },
        )
        _write_json(reconcile_contract_path, reconcile_contract_payload)
        run_state_payload = _augment_run_state_with_reconcile_contract_summary(
            run_state_payload=run_state_payload,
            reconcile_contract_payload=reconcile_contract_payload,
        )
        repair_suggestion_contract_path = run_root / "repair_suggestion_contract.json"
        repair_suggestion_contract_payload = build_repair_suggestion_contract_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            completion_contract_payload=completion_contract_payload,
            approval_transport_payload=approval_transport_payload,
            reconcile_contract_payload=reconcile_contract_payload,
            run_state_payload=run_state_payload,
            artifact_presence={
                "objective_contract.json": objective_contract_path.exists(),
                "completion_contract.json": completion_contract_path.exists(),
                "approval_transport.json": approval_transport_path.exists(),
                "reconcile_contract.json": reconcile_contract_path.exists(),
                "run_state.json": True,
            },
        )
        _write_json(repair_suggestion_contract_path, repair_suggestion_contract_payload)
        run_state_payload = _augment_run_state_with_repair_suggestion_contract_summary(
            run_state_payload=run_state_payload,
            repair_suggestion_contract_payload=repair_suggestion_contract_payload,
        )
        repair_plan_transport_path = run_root / "repair_plan_transport.json"
        repair_plan_transport_payload = build_repair_plan_transport_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            completion_contract_payload=completion_contract_payload,
            approval_transport_payload=approval_transport_payload,
            reconcile_contract_payload=reconcile_contract_payload,
            repair_suggestion_contract_payload=repair_suggestion_contract_payload,
            run_state_payload=run_state_payload,
            artifact_presence={
                "objective_contract.json": objective_contract_path.exists(),
                "completion_contract.json": completion_contract_path.exists(),
                "approval_transport.json": approval_transport_path.exists(),
                "reconcile_contract.json": reconcile_contract_path.exists(),
                "repair_suggestion_contract.json": repair_suggestion_contract_path.exists(),
                "run_state.json": True,
            },
        )
        _write_json(repair_plan_transport_path, repair_plan_transport_payload)
        run_state_payload = _augment_run_state_with_repair_plan_transport_summary(
            run_state_payload=run_state_payload,
            repair_plan_transport_payload=repair_plan_transport_payload,
        )
        repair_approval_binding_path = run_root / "repair_approval_binding.json"
        repair_approval_binding_payload = build_repair_approval_binding_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            completion_contract_payload=completion_contract_payload,
            approval_transport_payload=approval_transport_payload,
            reconcile_contract_payload=reconcile_contract_payload,
            repair_suggestion_contract_payload=repair_suggestion_contract_payload,
            repair_plan_transport_payload=repair_plan_transport_payload,
            run_state_payload=run_state_payload,
            artifact_presence={
                "objective_contract.json": objective_contract_path.exists(),
                "completion_contract.json": completion_contract_path.exists(),
                "approval_transport.json": approval_transport_path.exists(),
                "reconcile_contract.json": reconcile_contract_path.exists(),
                "repair_suggestion_contract.json": repair_suggestion_contract_path.exists(),
                "repair_plan_transport.json": repair_plan_transport_path.exists(),
                "run_state.json": True,
            },
        )
        _write_json(repair_approval_binding_path, repair_approval_binding_payload)
        run_state_payload = _augment_run_state_with_repair_approval_binding_summary(
            run_state_payload=run_state_payload,
            repair_approval_binding_payload=repair_approval_binding_payload,
        )
        execution_authorization_gate_path = run_root / "execution_authorization_gate.json"
        execution_authorization_gate_payload = build_execution_authorization_gate_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            completion_contract_payload=completion_contract_payload,
            approval_transport_payload=approval_transport_payload,
            reconcile_contract_payload=reconcile_contract_payload,
            repair_suggestion_contract_payload=repair_suggestion_contract_payload,
            repair_plan_transport_payload=repair_plan_transport_payload,
            repair_approval_binding_payload=repair_approval_binding_payload,
            run_state_payload=run_state_payload,
            artifact_presence={
                "objective_contract.json": objective_contract_path.exists(),
                "completion_contract.json": completion_contract_path.exists(),
                "approval_transport.json": approval_transport_path.exists(),
                "reconcile_contract.json": reconcile_contract_path.exists(),
                "repair_suggestion_contract.json": repair_suggestion_contract_path.exists(),
                "repair_plan_transport.json": repair_plan_transport_path.exists(),
                "repair_approval_binding.json": repair_approval_binding_path.exists(),
                "run_state.json": True,
            },
        )
        _write_json(execution_authorization_gate_path, execution_authorization_gate_payload)
        run_state_payload = _augment_run_state_with_execution_authorization_gate_summary(
            run_state_payload=run_state_payload,
            execution_authorization_gate_payload=execution_authorization_gate_payload,
        )
        bounded_execution_bridge_path = run_root / "bounded_execution_bridge.json"
        bounded_execution_bridge_payload = build_bounded_execution_bridge_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            completion_contract_payload=completion_contract_payload,
            approval_transport_payload=approval_transport_payload,
            reconcile_contract_payload=reconcile_contract_payload,
            repair_suggestion_contract_payload=repair_suggestion_contract_payload,
            repair_plan_transport_payload=repair_plan_transport_payload,
            repair_approval_binding_payload=repair_approval_binding_payload,
            execution_authorization_gate_payload=execution_authorization_gate_payload,
            run_state_payload=run_state_payload,
            artifact_presence={
                "objective_contract.json": objective_contract_path.exists(),
                "completion_contract.json": completion_contract_path.exists(),
                "approval_transport.json": approval_transport_path.exists(),
                "reconcile_contract.json": reconcile_contract_path.exists(),
                "repair_suggestion_contract.json": repair_suggestion_contract_path.exists(),
                "repair_plan_transport.json": repair_plan_transport_path.exists(),
                "repair_approval_binding.json": repair_approval_binding_path.exists(),
                "execution_authorization_gate.json": execution_authorization_gate_path.exists(),
                "run_state.json": True,
            },
        )
        _write_json(bounded_execution_bridge_path, bounded_execution_bridge_payload)
        run_state_payload = _augment_run_state_with_bounded_execution_bridge_summary(
            run_state_payload=run_state_payload,
            bounded_execution_bridge_payload=bounded_execution_bridge_payload,
        )
        execution_result_contract_path = run_root / "execution_result_contract.json"
        execution_result_contract_payload = build_execution_result_contract_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            completion_contract_payload=completion_contract_payload,
            approval_transport_payload=approval_transport_payload,
            reconcile_contract_payload=reconcile_contract_payload,
            repair_plan_transport_payload=repair_plan_transport_payload,
            repair_approval_binding_payload=repair_approval_binding_payload,
            execution_authorization_gate_payload=execution_authorization_gate_payload,
            bounded_execution_bridge_payload=bounded_execution_bridge_payload,
            run_state_payload=run_state_payload,
            execution_records=_collect_execution_result_contract_records(manifest_units),
            artifact_presence={
                "objective_contract.json": objective_contract_path.exists(),
                "completion_contract.json": completion_contract_path.exists(),
                "approval_transport.json": approval_transport_path.exists(),
                "reconcile_contract.json": reconcile_contract_path.exists(),
                "repair_plan_transport.json": repair_plan_transport_path.exists(),
                "repair_approval_binding.json": repair_approval_binding_path.exists(),
                "execution_authorization_gate.json": execution_authorization_gate_path.exists(),
                "bounded_execution_bridge.json": bounded_execution_bridge_path.exists(),
                "run_state.json": True,
            },
        )
        _write_json(execution_result_contract_path, execution_result_contract_payload)
        run_state_payload = _augment_run_state_with_execution_result_contract_summary(
            run_state_payload=run_state_payload,
            execution_result_contract_payload=execution_result_contract_payload,
        )
        verification_closure_contract_path = run_root / "verification_closure_contract.json"
        verification_closure_contract_payload = build_verification_closure_contract_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            completion_contract_payload=completion_contract_payload,
            approval_transport_payload=approval_transport_payload,
            reconcile_contract_payload=reconcile_contract_payload,
            execution_authorization_gate_payload=execution_authorization_gate_payload,
            bounded_execution_bridge_payload=bounded_execution_bridge_payload,
            execution_result_contract_payload=execution_result_contract_payload,
            run_state_payload=run_state_payload,
            artifact_presence={
                "objective_contract.json": objective_contract_path.exists(),
                "completion_contract.json": completion_contract_path.exists(),
                "approval_transport.json": approval_transport_path.exists(),
                "reconcile_contract.json": reconcile_contract_path.exists(),
                "execution_authorization_gate.json": execution_authorization_gate_path.exists(),
                "bounded_execution_bridge.json": bounded_execution_bridge_path.exists(),
                "execution_result_contract.json": execution_result_contract_path.exists(),
                "run_state.json": True,
            },
        )
        _write_json(verification_closure_contract_path, verification_closure_contract_payload)
        run_state_payload = _augment_run_state_with_verification_closure_contract_summary(
            run_state_payload=run_state_payload,
            verification_closure_contract_payload=verification_closure_contract_payload,
        )
        retry_reentry_loop_contract_path = run_root / "retry_reentry_loop_contract.json"
        retry_reentry_loop_contract_payload = build_retry_reentry_loop_contract_surface(
            run_id=resolved_job_id,
            completion_contract_payload=completion_contract_payload,
            approval_transport_payload=approval_transport_payload,
            reconcile_contract_payload=reconcile_contract_payload,
            repair_suggestion_contract_payload=repair_suggestion_contract_payload,
            repair_plan_transport_payload=repair_plan_transport_payload,
            repair_approval_binding_payload=repair_approval_binding_payload,
            execution_authorization_gate_payload=execution_authorization_gate_payload,
            bounded_execution_bridge_payload=bounded_execution_bridge_payload,
            execution_result_contract_payload=execution_result_contract_payload,
            verification_closure_contract_payload=verification_closure_contract_payload,
            run_state_payload=run_state_payload,
            artifact_presence={
                "completion_contract.json": completion_contract_path.exists(),
                "approval_transport.json": approval_transport_path.exists(),
                "reconcile_contract.json": reconcile_contract_path.exists(),
                "repair_suggestion_contract.json": repair_suggestion_contract_path.exists(),
                "repair_plan_transport.json": repair_plan_transport_path.exists(),
                "repair_approval_binding.json": repair_approval_binding_path.exists(),
                "execution_authorization_gate.json": execution_authorization_gate_path.exists(),
                "bounded_execution_bridge.json": bounded_execution_bridge_path.exists(),
                "execution_result_contract.json": execution_result_contract_path.exists(),
                "verification_closure_contract.json": verification_closure_contract_path.exists(),
                "run_state.json": True,
            },
        )
        _write_json(retry_reentry_loop_contract_path, retry_reentry_loop_contract_payload)
        run_state_payload = _augment_run_state_with_retry_reentry_loop_contract_summary(
            run_state_payload=run_state_payload,
            retry_reentry_loop_contract_payload=retry_reentry_loop_contract_payload,
        )
        endgame_closure_contract_path = run_root / "endgame_closure_contract.json"
        endgame_closure_contract_payload = build_endgame_closure_contract_surface(
            run_id=resolved_job_id,
            completion_contract_payload=completion_contract_payload,
            approval_transport_payload=approval_transport_payload,
            reconcile_contract_payload=reconcile_contract_payload,
            execution_authorization_gate_payload=execution_authorization_gate_payload,
            bounded_execution_bridge_payload=bounded_execution_bridge_payload,
            execution_result_contract_payload=execution_result_contract_payload,
            verification_closure_contract_payload=verification_closure_contract_payload,
            retry_reentry_loop_contract_payload=retry_reentry_loop_contract_payload,
            run_state_payload=run_state_payload,
            artifact_presence={
                "completion_contract.json": completion_contract_path.exists(),
                "approval_transport.json": approval_transport_path.exists(),
                "reconcile_contract.json": reconcile_contract_path.exists(),
                "execution_authorization_gate.json": execution_authorization_gate_path.exists(),
                "bounded_execution_bridge.json": bounded_execution_bridge_path.exists(),
                "execution_result_contract.json": execution_result_contract_path.exists(),
                "verification_closure_contract.json": verification_closure_contract_path.exists(),
                "retry_reentry_loop_contract.json": retry_reentry_loop_contract_path.exists(),
                "run_state.json": True,
            },
        )
        _write_json(endgame_closure_contract_path, endgame_closure_contract_payload)
        run_state_payload = _augment_run_state_with_endgame_closure_contract_summary(
            run_state_payload=run_state_payload,
            endgame_closure_contract_payload=endgame_closure_contract_payload,
        )
        loop_hardening_contract_path = run_root / "loop_hardening_contract.json"
        loop_hardening_contract_payload = build_loop_hardening_contract_surface(
            run_id=resolved_job_id,
            completion_contract_payload=completion_contract_payload,
            approval_transport_payload=approval_transport_payload,
            reconcile_contract_payload=reconcile_contract_payload,
            execution_result_contract_payload=execution_result_contract_payload,
            verification_closure_contract_payload=verification_closure_contract_payload,
            retry_reentry_loop_contract_payload=retry_reentry_loop_contract_payload,
            endgame_closure_contract_payload=endgame_closure_contract_payload,
            run_state_payload=run_state_payload,
            artifact_presence={
                "completion_contract.json": completion_contract_path.exists(),
                "approval_transport.json": approval_transport_path.exists(),
                "reconcile_contract.json": reconcile_contract_path.exists(),
                "execution_result_contract.json": execution_result_contract_path.exists(),
                "verification_closure_contract.json": verification_closure_contract_path.exists(),
                "retry_reentry_loop_contract.json": retry_reentry_loop_contract_path.exists(),
                "endgame_closure_contract.json": endgame_closure_contract_path.exists(),
                "run_state.json": True,
            },
        )
        _write_json(loop_hardening_contract_path, loop_hardening_contract_payload)
        run_state_payload = _augment_run_state_with_loop_hardening_contract_summary(
            run_state_payload=run_state_payload,
            loop_hardening_contract_payload=loop_hardening_contract_payload,
        )
        lane_stabilization_contract_path = run_root / "lane_stabilization_contract.json"
        lane_stabilization_contract_payload = build_lane_stabilization_contract_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            completion_contract_payload=completion_contract_payload,
            approval_transport_payload=approval_transport_payload,
            reconcile_contract_payload=reconcile_contract_payload,
            execution_authorization_gate_payload=execution_authorization_gate_payload,
            bounded_execution_bridge_payload=bounded_execution_bridge_payload,
            execution_result_contract_payload=execution_result_contract_payload,
            verification_closure_contract_payload=verification_closure_contract_payload,
            retry_reentry_loop_contract_payload=retry_reentry_loop_contract_payload,
            endgame_closure_contract_payload=endgame_closure_contract_payload,
            loop_hardening_contract_payload=loop_hardening_contract_payload,
            run_state_payload=run_state_payload,
            artifact_presence={
                "objective_contract.json": objective_contract_path.exists(),
                "completion_contract.json": completion_contract_path.exists(),
                "approval_transport.json": approval_transport_path.exists(),
                "reconcile_contract.json": reconcile_contract_path.exists(),
                "execution_authorization_gate.json": execution_authorization_gate_path.exists(),
                "bounded_execution_bridge.json": bounded_execution_bridge_path.exists(),
                "execution_result_contract.json": execution_result_contract_path.exists(),
                "verification_closure_contract.json": verification_closure_contract_path.exists(),
                "retry_reentry_loop_contract.json": retry_reentry_loop_contract_path.exists(),
                "endgame_closure_contract.json": endgame_closure_contract_path.exists(),
                "loop_hardening_contract.json": loop_hardening_contract_path.exists(),
                "run_state.json": True,
            },
        )
        _write_json(lane_stabilization_contract_path, lane_stabilization_contract_payload)
        run_state_payload = _augment_run_state_with_lane_stabilization_contract_summary(
            run_state_payload=run_state_payload,
            lane_stabilization_contract_payload=lane_stabilization_contract_payload,
        )
        observability_rollup_contract_path = run_root / "observability_rollup_contract.json"
        observability_rollup_payload = build_observability_rollup_contract_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            execution_result_contract_payload=execution_result_contract_payload,
            verification_closure_contract_payload=verification_closure_contract_payload,
            retry_reentry_loop_contract_payload=retry_reentry_loop_contract_payload,
            endgame_closure_contract_payload=endgame_closure_contract_payload,
            loop_hardening_contract_payload=loop_hardening_contract_payload,
            lane_stabilization_contract_payload=lane_stabilization_contract_payload,
            run_state_payload=run_state_payload,
            artifact_presence={
                "objective_contract.json": objective_contract_path.exists(),
                "completion_contract.json": completion_contract_path.exists(),
                "approval_transport.json": approval_transport_path.exists(),
                "reconcile_contract.json": reconcile_contract_path.exists(),
                "repair_suggestion_contract.json": repair_suggestion_contract_path.exists(),
                "repair_plan_transport.json": repair_plan_transport_path.exists(),
                "repair_approval_binding.json": repair_approval_binding_path.exists(),
                "execution_authorization_gate.json": execution_authorization_gate_path.exists(),
                "bounded_execution_bridge.json": bounded_execution_bridge_path.exists(),
                "execution_result_contract.json": execution_result_contract_path.exists(),
                "verification_closure_contract.json": verification_closure_contract_path.exists(),
                "retry_reentry_loop_contract.json": retry_reentry_loop_contract_path.exists(),
                "endgame_closure_contract.json": endgame_closure_contract_path.exists(),
                "loop_hardening_contract.json": loop_hardening_contract_path.exists(),
                "lane_stabilization_contract.json": lane_stabilization_contract_path.exists(),
                "run_state.json": True,
            },
            contract_artifact_index_payload=None,
        )
        _write_json(observability_rollup_contract_path, observability_rollup_payload)
        run_state_payload = _augment_run_state_with_observability_rollup_summary(
            run_state_payload=run_state_payload,
            observability_rollup_payload=observability_rollup_payload,
        )
        failure_bucket_rollup_path = run_root / "failure_bucket_rollup.json"
        failure_bucket_rollup_payload = build_failure_bucket_rollup_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            execution_result_contract_payload=execution_result_contract_payload,
            verification_closure_contract_payload=verification_closure_contract_payload,
            retry_reentry_loop_contract_payload=retry_reentry_loop_contract_payload,
            endgame_closure_contract_payload=endgame_closure_contract_payload,
            loop_hardening_contract_payload=loop_hardening_contract_payload,
            lane_stabilization_contract_payload=lane_stabilization_contract_payload,
            observability_rollup_payload=observability_rollup_payload,
            run_state_payload=run_state_payload,
        )
        _write_json(failure_bucket_rollup_path, failure_bucket_rollup_payload)
        fleet_run_rollup_path = run_root / "fleet_run_rollup.json"
        fleet_run_rollup_payload = build_fleet_run_rollup_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            observability_rollup_payload=observability_rollup_payload,
            failure_bucket_rollup_payload=failure_bucket_rollup_payload,
            verification_closure_contract_payload=verification_closure_contract_payload,
            retry_reentry_loop_contract_payload=retry_reentry_loop_contract_payload,
            endgame_closure_contract_payload=endgame_closure_contract_payload,
            loop_hardening_contract_payload=loop_hardening_contract_payload,
            lane_stabilization_contract_payload=lane_stabilization_contract_payload,
            execution_result_contract_payload=execution_result_contract_payload,
        )
        _write_json(fleet_run_rollup_path, fleet_run_rollup_payload)
        failure_bucketing_hardening_contract_path = (
            run_root / "failure_bucketing_hardening_contract.json"
        )
        failure_bucketing_hardening_payload = (
            build_failure_bucketing_hardening_contract_surface(
                run_id=resolved_job_id,
                objective_contract_payload=objective_contract_payload,
                execution_result_contract_payload=execution_result_contract_payload,
                verification_closure_contract_payload=verification_closure_contract_payload,
                retry_reentry_loop_contract_payload=retry_reentry_loop_contract_payload,
                endgame_closure_contract_payload=endgame_closure_contract_payload,
                loop_hardening_contract_payload=loop_hardening_contract_payload,
                lane_stabilization_contract_payload=lane_stabilization_contract_payload,
                observability_rollup_payload=observability_rollup_payload,
                failure_bucket_rollup_payload=failure_bucket_rollup_payload,
                bounded_execution_bridge_payload=bounded_execution_bridge_payload,
                execution_authorization_gate_payload=execution_authorization_gate_payload,
                run_state_payload=run_state_payload,
            )
        )
        _write_json(
            failure_bucketing_hardening_contract_path,
            failure_bucketing_hardening_payload,
        )
        run_state_payload = _augment_run_state_with_failure_bucketing_hardening_summary(
            run_state_payload=run_state_payload,
            failure_bucketing_hardening_payload=failure_bucketing_hardening_payload,
        )
        manifest["completion_contract_summary"] = build_completion_run_state_summary_surface(
            completion_contract_payload
        )
        manifest["completion_contract_path"] = str(completion_contract_path)
        manifest["approval_transport_summary"] = build_approval_run_state_summary_surface(
            approval_transport_payload
        )
        manifest["approval_transport_path"] = str(approval_transport_path)
        manifest["reconcile_contract_summary"] = build_reconcile_run_state_summary_surface(
            reconcile_contract_payload
        )
        manifest["reconcile_contract_path"] = str(reconcile_contract_path)
        manifest["repair_suggestion_contract_summary"] = (
            build_repair_suggestion_run_state_summary_surface(
                repair_suggestion_contract_payload
            )
        )
        manifest["repair_suggestion_contract_path"] = str(repair_suggestion_contract_path)
        manifest["repair_plan_transport_summary"] = (
            build_repair_plan_transport_run_state_summary_surface(
                repair_plan_transport_payload
            )
        )
        manifest["repair_plan_transport_path"] = str(repair_plan_transport_path)
        manifest["repair_approval_binding_summary"] = (
            build_repair_approval_binding_run_state_summary_surface(
                repair_approval_binding_payload
            )
        )
        manifest["repair_approval_binding_path"] = str(repair_approval_binding_path)
        manifest["execution_authorization_gate_summary"] = (
            build_execution_authorization_gate_run_state_summary_surface(
                execution_authorization_gate_payload
            )
        )
        manifest["execution_authorization_gate_path"] = str(execution_authorization_gate_path)
        manifest["bounded_execution_bridge_summary"] = (
            build_bounded_execution_bridge_run_state_summary_surface(
                bounded_execution_bridge_payload
            )
        )
        manifest["bounded_execution_bridge_path"] = str(bounded_execution_bridge_path)
        manifest["execution_result_contract_summary"] = (
            build_execution_result_contract_run_state_summary_surface(
                execution_result_contract_payload
            )
        )
        manifest["execution_result_contract_path"] = str(execution_result_contract_path)
        manifest["verification_closure_contract_summary"] = (
            build_verification_closure_run_state_summary_surface(
                verification_closure_contract_payload
            )
        )
        manifest["verification_closure_contract_path"] = str(
            verification_closure_contract_path
        )
        manifest["retry_reentry_loop_contract_summary"] = (
            build_retry_reentry_loop_run_state_summary_surface(
                retry_reentry_loop_contract_payload
            )
        )
        manifest["retry_reentry_loop_contract_path"] = str(
            retry_reentry_loop_contract_path
        )
        manifest["endgame_closure_contract_summary"] = (
            build_endgame_closure_run_state_summary_surface(
                endgame_closure_contract_payload
            )
        )
        manifest["endgame_closure_contract_path"] = str(
            endgame_closure_contract_path
        )
        manifest["loop_hardening_contract_summary"] = (
            build_loop_hardening_run_state_summary_surface(
                loop_hardening_contract_payload
            )
        )
        manifest["loop_hardening_contract_path"] = str(
            loop_hardening_contract_path
        )
        manifest["lane_stabilization_contract_summary"] = (
            build_lane_stabilization_run_state_summary_surface(
                lane_stabilization_contract_payload
            )
        )
        manifest["lane_stabilization_contract_path"] = str(
            lane_stabilization_contract_path
        )
        manifest["observability_rollup_contract_summary"] = (
            build_observability_rollup_contract_summary_surface(
                observability_rollup_payload
            )
        )
        manifest["observability_rollup_contract_path"] = str(
            observability_rollup_contract_path
        )
        manifest["failure_bucket_rollup_summary"] = (
            build_failure_bucket_rollup_summary_surface(
                failure_bucket_rollup_payload
            )
        )
        manifest["failure_bucket_rollup_path"] = str(failure_bucket_rollup_path)
        manifest["fleet_run_rollup_summary"] = (
            build_fleet_run_rollup_summary_surface(fleet_run_rollup_payload)
        )
        manifest["fleet_run_rollup_path"] = str(fleet_run_rollup_path)
        manifest["failure_bucketing_hardening_contract_summary"] = (
            build_failure_bucketing_hardening_summary_surface(
                failure_bucketing_hardening_payload
            )
        )
        manifest["failure_bucketing_hardening_contract_path"] = str(
            failure_bucketing_hardening_contract_path
        )
        contract_summaries_by_role = {
            "objective_contract": manifest.get("objective_contract_summary"),
            "completion_contract": manifest.get("completion_contract_summary"),
            "approval_transport": manifest.get("approval_transport_summary"),
            "reconcile_contract": manifest.get("reconcile_contract_summary"),
            "repair_suggestion_contract": manifest.get("repair_suggestion_contract_summary"),
            "repair_plan_transport": manifest.get("repair_plan_transport_summary"),
            "repair_approval_binding": manifest.get("repair_approval_binding_summary"),
            "execution_authorization_gate": manifest.get("execution_authorization_gate_summary"),
            "bounded_execution_bridge": manifest.get("bounded_execution_bridge_summary"),
            "execution_result_contract": manifest.get("execution_result_contract_summary"),
            "verification_closure_contract": manifest.get("verification_closure_contract_summary"),
            "retry_reentry_loop_contract": manifest.get("retry_reentry_loop_contract_summary"),
            "endgame_closure_contract": manifest.get("endgame_closure_contract_summary"),
            "loop_hardening_contract": manifest.get("loop_hardening_contract_summary"),
            "lane_stabilization_contract": manifest.get("lane_stabilization_contract_summary"),
            "observability_rollup_contract": manifest.get("observability_rollup_contract_summary"),
            "failure_bucket_rollup": manifest.get("failure_bucket_rollup_summary"),
            "fleet_run_rollup": manifest.get("fleet_run_rollup_summary"),
            "failure_bucketing_hardening_contract": manifest.get(
                "failure_bucketing_hardening_contract_summary"
            ),
        }
        contract_paths_by_role = {
            "objective_contract": manifest.get("objective_contract_path"),
            "completion_contract": manifest.get("completion_contract_path"),
            "approval_transport": manifest.get("approval_transport_path"),
            "reconcile_contract": manifest.get("reconcile_contract_path"),
            "repair_suggestion_contract": manifest.get("repair_suggestion_contract_path"),
            "repair_plan_transport": manifest.get("repair_plan_transport_path"),
            "repair_approval_binding": manifest.get("repair_approval_binding_path"),
            "execution_authorization_gate": manifest.get("execution_authorization_gate_path"),
            "bounded_execution_bridge": manifest.get("bounded_execution_bridge_path"),
            "execution_result_contract": manifest.get("execution_result_contract_path"),
            "verification_closure_contract": manifest.get("verification_closure_contract_path"),
            "retry_reentry_loop_contract": manifest.get("retry_reentry_loop_contract_path"),
            "endgame_closure_contract": manifest.get("endgame_closure_contract_path"),
            "loop_hardening_contract": manifest.get("loop_hardening_contract_path"),
            "lane_stabilization_contract": manifest.get("lane_stabilization_contract_path"),
            "observability_rollup_contract": manifest.get("observability_rollup_contract_path"),
            "failure_bucket_rollup": manifest.get("failure_bucket_rollup_path"),
            "fleet_run_rollup": manifest.get("fleet_run_rollup_path"),
            "failure_bucketing_hardening_contract": manifest.get(
                "failure_bucketing_hardening_contract_path"
            ),
        }
        manifest["contract_artifact_index"] = build_contract_artifact_index(
            paths_by_role=contract_paths_by_role,
            summaries_by_role=contract_summaries_by_role,
        )
        retention_manifest_path = run_root / "retention_manifest.json"
        retention_manifest_payload = build_retention_manifest_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            paths_by_role=contract_paths_by_role,
            summaries_by_role=contract_summaries_by_role,
            contract_artifact_index_payload=manifest.get("contract_artifact_index"),
            manifest_payload=manifest,
        )
        _write_json(retention_manifest_path, retention_manifest_payload)
        artifact_retention_contract_path = run_root / "artifact_retention_contract.json"
        artifact_retention_contract_payload = build_artifact_retention_contract_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            retention_manifest_payload=retention_manifest_payload,
            contract_artifact_index_payload=manifest.get("contract_artifact_index"),
            observability_rollup_payload=observability_rollup_payload,
            failure_bucketing_hardening_payload=failure_bucketing_hardening_payload,
            endgame_closure_contract_payload=endgame_closure_contract_payload,
        )
        _write_json(artifact_retention_contract_path, artifact_retention_contract_payload)
        run_state_payload = _augment_run_state_with_artifact_retention_summary(
            run_state_payload=run_state_payload,
            artifact_retention_payload=artifact_retention_contract_payload,
        )
        fleet_safety_control_contract_path = run_root / "fleet_safety_control_contract.json"
        fleet_safety_control_contract_payload = build_fleet_safety_control_contract_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            observability_rollup_payload=observability_rollup_payload,
            failure_bucketing_hardening_payload=failure_bucketing_hardening_payload,
            lane_stabilization_contract_payload=lane_stabilization_contract_payload,
            loop_hardening_contract_payload=loop_hardening_contract_payload,
            endgame_closure_contract_payload=endgame_closure_contract_payload,
            retry_reentry_loop_contract_payload=retry_reentry_loop_contract_payload,
            artifact_retention_contract_payload=artifact_retention_contract_payload,
            retention_manifest_payload=retention_manifest_payload,
            run_state_payload=run_state_payload,
            contract_artifact_index_payload=manifest.get("contract_artifact_index"),
        )
        _write_json(
            fleet_safety_control_contract_path,
            fleet_safety_control_contract_payload,
        )
        run_state_payload = _augment_run_state_with_fleet_safety_control_summary(
            run_state_payload=run_state_payload,
            fleet_safety_control_payload=fleet_safety_control_contract_payload,
        )
        approval_email_delivery_contract_path = (
            run_root / "approval_email_delivery_contract.json"
        )
        approval_email_delivery_contract_payload = (
            build_approval_email_delivery_contract_surface(
                run_id=resolved_job_id,
                objective_contract_payload=objective_contract_payload,
                fleet_safety_control_payload=fleet_safety_control_contract_payload,
                failure_bucketing_hardening_payload=failure_bucketing_hardening_payload,
                lane_stabilization_contract_payload=lane_stabilization_contract_payload,
                loop_hardening_contract_payload=loop_hardening_contract_payload,
                endgame_closure_contract_payload=endgame_closure_contract_payload,
                retry_reentry_loop_contract_payload=retry_reentry_loop_contract_payload,
                artifact_retention_contract_payload=artifact_retention_contract_payload,
                run_state_payload=run_state_payload,
                contract_artifact_index_payload=manifest.get("contract_artifact_index"),
                delivery_adapter=_approval_delivery_noop_adapter,
            )
        )
        _write_json(
            approval_email_delivery_contract_path,
            approval_email_delivery_contract_payload,
        )
        run_state_payload = _augment_run_state_with_approval_email_delivery_summary(
            run_state_payload=run_state_payload,
            approval_email_delivery_payload=approval_email_delivery_contract_payload,
        )
        approval_runtime_rules_contract_path = (
            run_root / "approval_runtime_rules_contract.json"
        )
        approval_runtime_rules_contract_payload = (
            build_approval_runtime_rules_contract_surface(
                run_id=resolved_job_id,
                objective_contract_payload=objective_contract_payload,
                approval_email_delivery_payload=approval_email_delivery_contract_payload,
                contract_artifact_index_payload=manifest.get("contract_artifact_index"),
            )
        )
        _write_json(
            approval_runtime_rules_contract_path,
            approval_runtime_rules_contract_payload,
        )
        run_state_payload = _augment_run_state_with_approval_runtime_rules_summary(
            run_state_payload=run_state_payload,
            approval_runtime_rules_payload=approval_runtime_rules_contract_payload,
        )
        approval_delivery_handoff_contract_path = (
            run_root / "approval_delivery_handoff_contract.json"
        )
        approval_delivery_handoff_contract_payload = (
            build_approval_delivery_handoff_contract_surface(
                run_id=resolved_job_id,
                objective_contract_payload=objective_contract_payload,
                approval_email_delivery_payload=approval_email_delivery_contract_payload,
                approval_runtime_rules_payload=approval_runtime_rules_contract_payload,
                fleet_safety_control_payload=fleet_safety_control_contract_payload,
                failure_bucketing_hardening_payload=failure_bucketing_hardening_payload,
                lane_stabilization_contract_payload=lane_stabilization_contract_payload,
                run_state_payload=run_state_payload,
                contract_artifact_index_payload=manifest.get("contract_artifact_index"),
            )
        )
        _write_json(
            approval_delivery_handoff_contract_path,
            approval_delivery_handoff_contract_payload,
        )
        run_state_payload = _augment_run_state_with_approval_delivery_handoff_summary(
            run_state_payload=run_state_payload,
            approval_delivery_handoff_payload=approval_delivery_handoff_contract_payload,
        )
        approval_response_contract_path = run_root / "approval_response_contract.json"
        approval_response_contract_payload = build_approval_response_contract_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            approval_delivery_handoff_payload=approval_delivery_handoff_contract_payload,
            approval_email_delivery_payload=approval_email_delivery_contract_payload,
            approval_runtime_rules_payload=approval_runtime_rules_contract_payload,
            fleet_safety_control_payload=fleet_safety_control_contract_payload,
            run_state_payload=run_state_payload,
            contract_artifact_index_payload=manifest.get("contract_artifact_index"),
            response_payload=approval_response_input,
        )
        _write_json(
            approval_response_contract_path,
            approval_response_contract_payload,
        )
        run_state_payload = _augment_run_state_with_approval_response_summary(
            run_state_payload=run_state_payload,
            approval_response_payload=approval_response_contract_payload,
        )
        approved_restart_contract_path = run_root / "approved_restart_contract.json"
        approved_restart_contract_payload = build_approved_restart_contract_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            approval_response_payload=approval_response_contract_payload,
            approval_delivery_handoff_payload=approval_delivery_handoff_contract_payload,
            approval_email_delivery_payload=approval_email_delivery_contract_payload,
            fleet_safety_control_payload=fleet_safety_control_contract_payload,
            failure_bucketing_hardening_payload=failure_bucketing_hardening_payload,
            lane_stabilization_contract_payload=lane_stabilization_contract_payload,
            run_state_payload=run_state_payload,
            contract_artifact_index_payload=manifest.get("contract_artifact_index"),
        )
        _write_json(
            approved_restart_contract_path,
            approved_restart_contract_payload,
        )
        run_state_payload = _augment_run_state_with_approved_restart_summary(
            run_state_payload=run_state_payload,
            approved_restart_payload=approved_restart_contract_payload,
        )
        approval_safety_contract_path = run_root / "approval_safety_contract.json"
        approval_safety_contract_payload = build_approval_safety_contract_surface(
            run_id=resolved_job_id,
            objective_contract_payload=objective_contract_payload,
            approval_email_delivery_payload=approval_email_delivery_contract_payload,
            approval_delivery_handoff_payload=approval_delivery_handoff_contract_payload,
            approval_response_payload=approval_response_contract_payload,
            approved_restart_payload=approved_restart_contract_payload,
            lane_stabilization_contract_payload=lane_stabilization_contract_payload,
            failure_bucketing_hardening_payload=failure_bucketing_hardening_payload,
            approval_runtime_rules_payload=approval_runtime_rules_contract_payload,
            run_state_payload=run_state_payload,
            contract_artifact_index_payload=manifest.get("contract_artifact_index"),
        )
        _write_json(
            approval_safety_contract_path,
            approval_safety_contract_payload,
        )
        run_state_payload = _augment_run_state_with_approval_safety_summary(
            run_state_payload=run_state_payload,
            approval_safety_payload=approval_safety_contract_payload,
        )
        approved_restart_execution_contract_path = (
            run_root / "approved_restart_execution_contract.json"
        )
        prior_approved_restart_execution_contract_payload = _read_json_object_if_exists(
            approved_restart_execution_contract_path
        )
        approved_restart_execution_contract_payload = (
            _build_approved_restart_execution_contract_surface(
                run_id=resolved_job_id,
                objective_contract_payload=objective_contract_payload,
                approval_email_delivery_payload=approval_email_delivery_contract_payload,
                fleet_safety_control_payload=fleet_safety_control_contract_payload,
                approval_runtime_rules_payload=approval_runtime_rules_contract_payload,
                failure_bucketing_hardening_payload=failure_bucketing_hardening_payload,
                loop_hardening_contract_payload=loop_hardening_contract_payload,
                approved_restart_payload=approved_restart_contract_payload,
                approval_response_payload=approval_response_contract_payload,
                approval_safety_payload=approval_safety_contract_payload,
                prior_approved_restart_execution_payload=prior_approved_restart_execution_contract_payload,
                manifest_units=manifest_units,
                adapter=self.adapter,
                dry_run=dry_run,
                now=self.now,
            )
        )
        _write_json(
            approved_restart_execution_contract_path,
            approved_restart_execution_contract_payload,
        )
        run_state_payload = _augment_run_state_with_operator_explainability(
            run_state_payload=run_state_payload,
        )
        _write_json(run_state_path, run_state_payload)
        manifest["retention_manifest_summary"] = build_retention_manifest_summary_surface(
            retention_manifest_payload
        )
        manifest["retention_manifest_path"] = str(retention_manifest_path)
        manifest["artifact_retention_contract_summary"] = build_artifact_retention_summary_surface(
            artifact_retention_contract_payload
        )
        manifest["artifact_retention_contract_path"] = str(
            artifact_retention_contract_path
        )
        manifest["fleet_safety_control_contract_summary"] = (
            build_fleet_safety_control_summary_surface(
                fleet_safety_control_contract_payload
            )
        )
        manifest["fleet_safety_control_contract_path"] = str(
            fleet_safety_control_contract_path
        )
        manifest["approval_email_delivery_contract_summary"] = (
            build_approval_email_delivery_summary_surface(
                approval_email_delivery_contract_payload
            )
        )
        manifest["approval_email_delivery_contract_path"] = str(
            approval_email_delivery_contract_path
        )
        manifest["approval_runtime_rules_contract_summary"] = (
            build_approval_runtime_rules_summary_surface(
                approval_runtime_rules_contract_payload
            )
        )
        manifest["approval_runtime_rules_contract_path"] = str(
            approval_runtime_rules_contract_path
        )
        manifest["approval_delivery_handoff_contract_summary"] = (
            build_approval_delivery_handoff_summary_surface(
                approval_delivery_handoff_contract_payload
            )
        )
        manifest["approval_delivery_handoff_contract_path"] = str(
            approval_delivery_handoff_contract_path
        )
        manifest["approval_response_contract_summary"] = (
            build_approval_response_summary_surface(
                approval_response_contract_payload
            )
        )
        manifest["approval_response_contract_path"] = str(
            approval_response_contract_path
        )
        manifest["approved_restart_contract_summary"] = (
            build_approved_restart_summary_surface(
                approved_restart_contract_payload
            )
        )
        manifest["approved_restart_contract_path"] = str(
            approved_restart_contract_path
        )
        manifest["approval_safety_contract_summary"] = (
            build_approval_safety_summary_surface(
                approval_safety_contract_payload
            )
        )
        manifest["approval_safety_contract_path"] = str(
            approval_safety_contract_path
        )
        manifest["approved_restart_execution_contract_summary"] = (
            _build_approved_restart_execution_summary_surface(
                approved_restart_execution_contract_payload
            )
        )
        manifest["approved_restart_execution_contract_path"] = str(
            approved_restart_execution_contract_path
        )
        contract_summaries_by_role["retention_manifest"] = manifest.get(
            "retention_manifest_summary"
        )
        contract_summaries_by_role["artifact_retention_contract"] = manifest.get(
            "artifact_retention_contract_summary"
        )
        contract_summaries_by_role["fleet_safety_control_contract"] = manifest.get(
            "fleet_safety_control_contract_summary"
        )
        contract_summaries_by_role["approval_email_delivery_contract"] = manifest.get(
            "approval_email_delivery_contract_summary"
        )
        contract_summaries_by_role["approval_runtime_rules_contract"] = manifest.get(
            "approval_runtime_rules_contract_summary"
        )
        contract_summaries_by_role["approval_delivery_handoff_contract"] = manifest.get(
            "approval_delivery_handoff_contract_summary"
        )
        contract_summaries_by_role["approval_response_contract"] = manifest.get(
            "approval_response_contract_summary"
        )
        contract_summaries_by_role["approved_restart_contract"] = manifest.get(
            "approved_restart_contract_summary"
        )
        contract_summaries_by_role["approval_safety_contract"] = manifest.get(
            "approval_safety_contract_summary"
        )
        contract_paths_by_role["retention_manifest"] = manifest.get(
            "retention_manifest_path"
        )
        contract_paths_by_role["artifact_retention_contract"] = manifest.get(
            "artifact_retention_contract_path"
        )
        contract_paths_by_role["fleet_safety_control_contract"] = manifest.get(
            "fleet_safety_control_contract_path"
        )
        contract_paths_by_role["approval_email_delivery_contract"] = manifest.get(
            "approval_email_delivery_contract_path"
        )
        contract_paths_by_role["approval_runtime_rules_contract"] = manifest.get(
            "approval_runtime_rules_contract_path"
        )
        contract_paths_by_role["approval_delivery_handoff_contract"] = manifest.get(
            "approval_delivery_handoff_contract_path"
        )
        contract_paths_by_role["approval_response_contract"] = manifest.get(
            "approval_response_contract_path"
        )
        contract_paths_by_role["approved_restart_contract"] = manifest.get(
            "approved_restart_contract_path"
        )
        contract_paths_by_role["approval_safety_contract"] = manifest.get(
            "approval_safety_contract_path"
        )
        manifest["contract_artifact_index"] = build_contract_artifact_index(
            paths_by_role=contract_paths_by_role,
            summaries_by_role=contract_summaries_by_role,
        )

        handoff_path = run_root / "action_handoff.json"
        handoff_error = ""
        retry_context_store_error = ""
        try:
            handoff_payload = build_action_handoff_payload(
                job_id=resolved_job_id,
                decision_payload=decision_payload,
                now=self.now,
                external_evidence=github_read_evidence,
            )
        except Exception as exc:
            handoff_error = str(exc).strip() or "action_handoff_generation_failed"
            handoff_payload = {
                "handoff_schema_version": "v1",
                "job_id": resolved_job_id,
                "next_action": _normalize_text(decision_payload.get("next_action"), default=""),
                "reason": f"action_handoff_generation_failed: {handoff_error}",
                "whether_human_required": True,
                "retry_budget_remaining": _as_non_negative_int(
                    decision_payload.get("retry_budget_remaining"),
                    default=0,
                ),
                "updated_retry_context": (
                    dict(decision_payload.get("updated_retry_context"))
                    if isinstance(decision_payload.get("updated_retry_context"), Mapping)
                    else {
                        "prior_attempt_count": 0,
                        "prior_retry_class": None,
                        "missing_signal_count": 0,
                        "retry_budget_remaining": 0,
                    }
                ),
                "action_consumable": False,
                "unsupported_reason": "action_handoff_generation_failed",
                "retry_class": None,
                "evidence_summary": {
                    "provided": bool(github_read_evidence),
                    "items_total": 0,
                    "items": [],
                    "status_counts": {
                        "success": 0,
                        "empty": 0,
                        "not_found": 0,
                        "auth_failure": 0,
                        "api_failure": 0,
                        "unsupported_query": 0,
                    },
                },
                "evidence_constraints": [],
                "handoff_created_at": _iso_now(self.now),
            }
        _write_json(handoff_path, handoff_payload)

        try:
            retry_context_to_store = (
                dict(handoff_payload.get("updated_retry_context"))
                if isinstance(handoff_payload.get("updated_retry_context"), Mapping)
                else {
                    "prior_attempt_count": 0,
                    "prior_retry_class": None,
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 0,
                }
            )
            retry_context_store.set(
                job_id=resolved_job_id,
                retry_context=retry_context_to_store,
                updated_at=_normalize_text(handoff_payload.get("handoff_created_at"), default=_iso_now(self.now)),
            )
        except Exception as exc:
            retry_context_store_error = str(exc).strip() or "retry_context_store_update_failed"

        manifest["decision_summary"] = {
            "next_action": _normalize_text(decision_payload.get("next_action"), default=""),
            "whether_human_required": bool(decision_payload.get("whether_human_required", False)),
            "decision_path": str(decision_path),
            "evaluated_at": _normalize_text(decision_payload.get("evaluated_at"), default=""),
        }
        if decision_error:
            manifest["decision_summary"]["decision_error"] = decision_error
        manifest["progression_summary"] = {
            "final_unit_state": review_terminal_state,
            "units_reviewed": len(manifest_units),
            "next_action": _normalize_text(decision_payload.get("next_action"), default=""),
            "progression_outcome": _normalize_text(decision_payload.get("progression_outcome"), default=""),
            "result_acceptance": _normalize_text(decision_payload.get("result_acceptance"), default=""),
            "progression_rule_id": _normalize_text(decision_payload.get("progression_rule_id"), default=""),
        }
        run_state_summary_compact = select_manifest_run_state_summary_compact(
            run_state_payload,
        )
        manifest["run_state_summary_compact"] = run_state_summary_compact
        # Compatibility alias: PR52 slims manifest summaries to compact-only fields.
        manifest["run_state_summary"] = dict(run_state_summary_compact)
        manifest["run_state_summary_contract"] = build_manifest_run_state_summary_contract_surface()

        manifest["handoff_summary"] = {
            "next_action": _normalize_text(handoff_payload.get("next_action"), default=""),
            "action_consumable": bool(handoff_payload.get("action_consumable", False)),
            "unsupported_reason": _normalize_text(handoff_payload.get("unsupported_reason"), default=""),
            "handoff_path": str(handoff_path),
            "handoff_created_at": _normalize_text(handoff_payload.get("handoff_created_at"), default=""),
            "evidence_constraints_count": len(
                handoff_payload.get("evidence_constraints")
                if isinstance(handoff_payload.get("evidence_constraints"), list)
                else []
            ),
        }
        if handoff_error:
            manifest["handoff_summary"]["handoff_error"] = handoff_error
        if retry_context_store_error:
            manifest["handoff_summary"]["retry_context_store_error"] = retry_context_store_error

        manifest["manifest_path"] = str(manifest_path)
        manifest["next_action_path"] = str(decision_path)
        manifest["action_handoff_path"] = str(handoff_path)
        manifest["run_state_path"] = str(run_state_path)
        manifest["retry_context_store_path"] = str(retry_context_store_path)
        _write_json(manifest_path, manifest)
        return manifest

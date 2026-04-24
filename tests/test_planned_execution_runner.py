from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from automation.execution.codex_executor_adapter import CodexExecutorAdapter
from automation.orchestration.approval_transport import APPROVAL_COMPATIBILITY_STATUSES
from automation.orchestration.approval_transport import APPROVAL_DECISIONS
from automation.orchestration.approval_transport import APPROVAL_RUN_STATE_SUMMARY_SAFE_FIELDS
from automation.orchestration.approval_transport import APPROVAL_SCOPES
from automation.orchestration.approval_transport import APPROVAL_STATUSES
from automation.orchestration.approval_transport import APPROVAL_TRANSPORT_STATUSES
from automation.orchestration.approval_transport import APPROVED_ACTIONS
from automation.orchestration.approval_transport import build_approval_run_state_summary_surface
from automation.orchestration.approval_transport import build_approval_transport_surface
from automation.orchestration.artifact_index import CONTRACT_ARTIFACT_ROLES
from automation.orchestration.artifact_index import build_contract_artifact_index
from automation.orchestration.completion_contract import COMPLETION_RUN_STATE_SUMMARY_SAFE_FIELDS
from automation.orchestration.completion_contract import COMPLETION_EVIDENCE_STATUSES
from automation.orchestration.completion_contract import COMPLETION_STATUSES
from automation.orchestration.completion_contract import CLOSURE_DECISIONS
from automation.orchestration.completion_contract import DONE_STATUSES
from automation.orchestration.completion_contract import LIFECYCLE_ALIGNMENT_STATUSES
from automation.orchestration.completion_contract import SAFE_CLOSURE_STATUSES
from automation.orchestration.completion_contract import build_completion_contract_surface
from automation.orchestration.completion_contract import build_completion_run_state_summary_surface
from automation.orchestration.bounded_execution_bridge import (
    BOUNDED_EXECUTION_BRIDGE_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.bounded_execution_bridge import (
    BOUNDED_EXECUTION_CANDIDATE_ACTIONS,
)
from automation.orchestration.bounded_execution_bridge import BOUNDED_EXECUTION_CONFIDENCE_LEVELS
from automation.orchestration.bounded_execution_bridge import BOUNDED_EXECUTION_DECISIONS
from automation.orchestration.bounded_execution_bridge import BOUNDED_EXECUTION_REASON_CODES
from automation.orchestration.bounded_execution_bridge import BOUNDED_EXECUTION_SCOPES
from automation.orchestration.bounded_execution_bridge import BOUNDED_EXECUTION_SOURCE_STATUSES
from automation.orchestration.bounded_execution_bridge import BOUNDED_EXECUTION_STATUSES
from automation.orchestration.bounded_execution_bridge import BOUNDED_EXECUTION_VALIDITIES
from automation.orchestration.bounded_execution_bridge import (
    build_bounded_execution_bridge_run_state_summary_surface,
)
from automation.orchestration.bounded_execution_bridge import (
    build_bounded_execution_bridge_surface,
)
from automation.orchestration.execution_authorization_gate import (
    EXECUTION_AUTHORIZATION_CONFIDENCE_LEVELS,
)
from automation.orchestration.execution_authorization_gate import EXECUTION_AUTHORIZATION_DECISIONS
from automation.orchestration.execution_authorization_gate import EXECUTION_AUTHORIZATION_GATE_RUN_STATE_SUMMARY_SAFE_FIELDS
from automation.orchestration.execution_authorization_gate import EXECUTION_AUTHORIZATION_REASON_CODES
from automation.orchestration.execution_authorization_gate import EXECUTION_AUTHORIZATION_SCOPES
from automation.orchestration.execution_authorization_gate import EXECUTION_AUTHORIZATION_SOURCE_STATUSES
from automation.orchestration.execution_authorization_gate import EXECUTION_AUTHORIZATION_STATUSES
from automation.orchestration.execution_authorization_gate import EXECUTION_AUTHORIZATION_VALIDITIES
from automation.orchestration.execution_authorization_gate import (
    build_execution_authorization_gate_run_state_summary_surface,
)
from automation.orchestration.execution_authorization_gate import (
    build_execution_authorization_gate_surface,
)
from automation.orchestration.execution_result_contract import (
    EXECUTION_RESULT_CONFIDENCE_LEVELS,
)
from automation.orchestration.execution_result_contract import EXECUTION_RESULT_OUTCOMES
from automation.orchestration.execution_result_contract import EXECUTION_RESULT_REASON_CODES
from automation.orchestration.execution_result_contract import (
    EXECUTION_RESULT_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.execution_result_contract import EXECUTION_RESULT_SOURCE_POSTURES
from automation.orchestration.execution_result_contract import EXECUTION_RESULT_STATUSES
from automation.orchestration.execution_result_contract import EXECUTION_RESULT_VALIDITIES
from automation.orchestration.execution_result_contract import (
    build_execution_result_contract_run_state_summary_surface,
)
from automation.orchestration.execution_result_contract import (
    build_execution_result_contract_surface,
)
from automation.orchestration.verification_closure_contract import (
    CLOSURE_DECISIONS as VERIFICATION_CLOSURE_DECISIONS,
)
from automation.orchestration.verification_closure_contract import (
    CLOSURE_STATUSES as VERIFICATION_CLOSURE_STATUSES,
)
from automation.orchestration.verification_closure_contract import (
    COMPLETION_SATISFACTION_STATUSES,
)
from automation.orchestration.verification_closure_contract import (
    OBJECTIVE_SATISFACTION_STATUSES,
)
from automation.orchestration.verification_closure_contract import (
    VERIFICATION_CLOSURE_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.verification_closure_contract import (
    VERIFICATION_CONFIDENCE_LEVELS,
)
from automation.orchestration.verification_closure_contract import (
    VERIFICATION_OUTCOMES,
)
from automation.orchestration.verification_closure_contract import (
    VERIFICATION_REASON_CODES,
)
from automation.orchestration.verification_closure_contract import (
    VERIFICATION_SOURCE_POSTURES,
)
from automation.orchestration.verification_closure_contract import (
    VERIFICATION_STATUSES,
)
from automation.orchestration.verification_closure_contract import (
    VERIFICATION_VALIDITIES,
)
from automation.orchestration.verification_closure_contract import (
    build_verification_closure_contract_surface,
)
from automation.orchestration.verification_closure_contract import (
    build_verification_closure_run_state_summary_surface,
)
from automation.orchestration.retry_reentry_loop_contract import LOOP_STOP_REASONS
from automation.orchestration.retry_reentry_loop_contract import REENTRY_CLASSES
from automation.orchestration.retry_reentry_loop_contract import RETRY_CLASSES
from automation.orchestration.retry_reentry_loop_contract import RETRY_LOOP_CONFIDENCE_LEVELS
from automation.orchestration.retry_reentry_loop_contract import RETRY_LOOP_DECISIONS
from automation.orchestration.retry_reentry_loop_contract import RETRY_LOOP_REASON_CODES
from automation.orchestration.retry_reentry_loop_contract import (
    RETRY_REENTRY_LOOP_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.retry_reentry_loop_contract import RETRY_LOOP_SOURCE_POSTURES
from automation.orchestration.retry_reentry_loop_contract import RETRY_LOOP_STATUSES
from automation.orchestration.retry_reentry_loop_contract import RETRY_LOOP_VALIDITIES
from automation.orchestration.retry_reentry_loop_contract import (
    build_retry_reentry_loop_contract_surface,
)
from automation.orchestration.retry_reentry_loop_contract import (
    build_retry_reentry_loop_run_state_summary_surface,
)
from automation.orchestration.endgame_closure_contract import (
    CLOSURE_RESOLUTION_STATUSES,
)
from automation.orchestration.endgame_closure_contract import (
    ENDGAME_CLOSURE_CONFIDENCE_LEVELS,
)
from automation.orchestration.endgame_closure_contract import ENDGAME_CLOSURE_OUTCOMES
from automation.orchestration.endgame_closure_contract import (
    ENDGAME_CLOSURE_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.endgame_closure_contract import ENDGAME_CLOSURE_STATUSES
from automation.orchestration.endgame_closure_contract import ENDGAME_CLOSURE_VALIDITIES
from automation.orchestration.endgame_closure_contract import ENDGAME_REASON_CODES
from automation.orchestration.endgame_closure_contract import ENDGAME_SOURCE_POSTURES
from automation.orchestration.endgame_closure_contract import FINAL_CLOSURE_CLASSES
from automation.orchestration.endgame_closure_contract import TERMINAL_STOP_CLASSES
from automation.orchestration.endgame_closure_contract import (
    build_endgame_closure_contract_surface,
)
from automation.orchestration.endgame_closure_contract import (
    build_endgame_closure_run_state_summary_surface,
)
from automation.orchestration.loop_hardening_contract import LOOP_HARDENING_CONFIDENCE_LEVELS
from automation.orchestration.loop_hardening_contract import LOOP_HARDENING_DECISIONS
from automation.orchestration.loop_hardening_contract import LOOP_HARDENING_REASON_CODES
from automation.orchestration.loop_hardening_contract import (
    LOOP_HARDENING_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.loop_hardening_contract import LOOP_HARDENING_SOURCE_POSTURES
from automation.orchestration.loop_hardening_contract import LOOP_HARDENING_STATUSES
from automation.orchestration.loop_hardening_contract import LOOP_HARDENING_VALIDITIES
from automation.orchestration.loop_hardening_contract import NO_PROGRESS_STATUSES
from automation.orchestration.loop_hardening_contract import OSCILLATION_STATUSES
from automation.orchestration.loop_hardening_contract import RETRY_FREEZE_STATUSES
from automation.orchestration.loop_hardening_contract import SAME_FAILURE_BUCKETS
from automation.orchestration.loop_hardening_contract import SAME_FAILURE_PERSISTENCE_STATUSES
from automation.orchestration.loop_hardening_contract import (
    build_loop_hardening_contract_surface,
)
from automation.orchestration.loop_hardening_contract import (
    build_loop_hardening_run_state_summary_surface,
)
from automation.orchestration.lane_stabilization_contract import LANE_CONFIDENCE_LEVELS
from automation.orchestration.lane_stabilization_contract import LANE_DECISIONS
from automation.orchestration.lane_stabilization_contract import LANE_ESCALATION_POLICY_CLASSES
from automation.orchestration.lane_stabilization_contract import LANE_PRECONDITIONS_STATUSES
from automation.orchestration.lane_stabilization_contract import LANE_REASON_CODES
from automation.orchestration.lane_stabilization_contract import LANE_RETRY_POLICY_CLASSES
from automation.orchestration.lane_stabilization_contract import (
    LANE_SOURCE_POSTURES,
)
from automation.orchestration.lane_stabilization_contract import LANE_STATUSES
from automation.orchestration.lane_stabilization_contract import (
    LANE_STABILIZATION_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.lane_stabilization_contract import LANE_TRANSITION_DECISIONS
from automation.orchestration.lane_stabilization_contract import LANE_TRANSITION_STATUSES
from automation.orchestration.lane_stabilization_contract import LANE_VALIDITIES
from automation.orchestration.lane_stabilization_contract import LANE_VERIFICATION_POLICY_CLASSES
from automation.orchestration.lane_stabilization_contract import LANE_VOCABULARY
from automation.orchestration.lane_stabilization_contract import (
    build_lane_stabilization_contract_surface,
)
from automation.orchestration.lane_stabilization_contract import (
    build_lane_stabilization_run_state_summary_surface,
)
from automation.orchestration.observability_rollup import (
    FAILURE_BUCKET_CONFIDENCE_LEVELS,
)
from automation.orchestration.observability_rollup import FAILURE_BUCKET_REASON_CODES
from automation.orchestration.observability_rollup import (
    FAILURE_BUCKET_ROLLUP_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.observability_rollup import FAILURE_BUCKET_STATUSES
from automation.orchestration.observability_rollup import FAILURE_BUCKET_VALIDITIES
from automation.orchestration.observability_rollup import FAILURE_BUCKET_VOCABULARY
from automation.orchestration.observability_rollup import (
    FLEET_RUN_ROLLUP_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.observability_rollup import (
    OBSERVABILITY_CONFIDENCE_LEVELS,
)
from automation.orchestration.observability_rollup import OBSERVABILITY_REASON_CODES
from automation.orchestration.observability_rollup import (
    OBSERVABILITY_ROLLUP_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.observability_rollup import (
    OBSERVABILITY_ROLLUP_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.observability_rollup import OBSERVABILITY_STATUSES
from automation.orchestration.observability_rollup import OBSERVABILITY_VALIDITIES
from automation.orchestration.observability_rollup import RUN_TERMINAL_CLASSES
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
    BUCKET_SEVERITIES,
)
from automation.orchestration.failure_bucketing_hardening import (
    BUCKET_STABILITY_CLASSES,
)
from automation.orchestration.failure_bucketing_hardening import (
    BUCKET_TERMINALITY_CLASSES,
)
from automation.orchestration.failure_bucketing_hardening import (
    FAILURE_BUCKETING_CONFIDENCE_LEVELS,
)
from automation.orchestration.failure_bucketing_hardening import (
    FAILURE_BUCKETING_HARDENING_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.failure_bucketing_hardening import (
    FAILURE_BUCKETING_HARDENING_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.failure_bucketing_hardening import (
    FAILURE_BUCKETING_REASON_CODES,
)
from automation.orchestration.failure_bucketing_hardening import (
    FAILURE_BUCKETING_STATUSES,
)
from automation.orchestration.failure_bucketing_hardening import (
    FAILURE_BUCKETING_VALIDITIES,
)
from automation.orchestration.failure_bucketing_hardening import (
    HARDENED_FAILURE_BUCKET_VOCABULARY,
)
from automation.orchestration.failure_bucketing_hardening import (
    build_failure_bucketing_hardening_contract_surface,
)
from automation.orchestration.failure_bucketing_hardening import (
    build_failure_bucketing_hardening_run_state_summary_surface,
)
from automation.orchestration.failure_bucketing_hardening import (
    build_failure_bucketing_hardening_summary_surface,
)
from automation.orchestration.artifact_retention import (
    ARTIFACT_RETENTION_CONFIDENCE_LEVELS,
)
from automation.orchestration.artifact_retention import (
    ARTIFACT_RETENTION_REASON_CODES,
)
from automation.orchestration.artifact_retention import (
    ARTIFACT_RETENTION_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.artifact_retention import (
    ARTIFACT_RETENTION_STATUSES,
)
from automation.orchestration.artifact_retention import (
    ARTIFACT_RETENTION_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.artifact_retention import (
    ARTIFACT_RETENTION_VALIDITIES,
)
from automation.orchestration.artifact_retention import (
    RETENTION_MANIFEST_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.artifact_retention import (
    RETENTION_POLICY_CLASSES,
)
from automation.orchestration.artifact_retention import (
    RETENTION_COMPACTION_CLASSES,
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
    FLEET_BUCKET_RISK_CLASSES,
)
from automation.orchestration.fleet_safety_control import (
    FLEET_LANE_RISK_CLASSES,
)
from automation.orchestration.fleet_safety_control import (
    FLEET_REPEAT_RISK_CLASSES,
)
from automation.orchestration.fleet_safety_control import (
    FLEET_RESTART_DECISIONS,
)
from automation.orchestration.fleet_safety_control import (
    FLEET_SAFETY_CONFIDENCE_LEVELS,
)
from automation.orchestration.fleet_safety_control import (
    FLEET_SAFETY_CONTROL_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.fleet_safety_control import (
    FLEET_SAFETY_CONTROL_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.fleet_safety_control import (
    FLEET_SAFETY_DECISIONS,
)
from automation.orchestration.fleet_safety_control import (
    FLEET_SAFETY_REASON_CODES,
)
from automation.orchestration.fleet_safety_control import (
    FLEET_SAFETY_SCOPES,
)
from automation.orchestration.fleet_safety_control import (
    FLEET_SAFETY_STATUSES,
)
from automation.orchestration.fleet_safety_control import (
    FLEET_SAFETY_VALIDITIES,
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
    APPROVAL_DECISION_SCOPES,
)
from automation.orchestration.approval_email_delivery import (
    APPROVAL_EMAIL_CONFIDENCE_LEVELS,
)
from automation.orchestration.approval_email_delivery import (
    APPROVAL_EMAIL_DELIVERY_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.approval_email_delivery import (
    APPROVAL_EMAIL_DELIVERY_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.approval_email_delivery import (
    APPROVAL_EMAIL_REASON_CODES,
)
from automation.orchestration.approval_email_delivery import (
    APPROVAL_EMAIL_STATUSES,
)
from automation.orchestration.approval_email_delivery import (
    APPROVAL_EMAIL_VALIDITIES,
)
from automation.orchestration.approval_email_delivery import (
    APPROVAL_OPTION_SETS,
)
from automation.orchestration.approval_email_delivery import APPROVAL_PRIORITIES
from automation.orchestration.approval_email_delivery import APPROVAL_REASON_CLASSES
from automation.orchestration.approval_email_delivery import DELIVERY_MODES
from automation.orchestration.approval_email_delivery import DELIVERY_OUTCOMES
from automation.orchestration.approval_email_delivery import PROPOSED_ACTION_CLASSES
from automation.orchestration.approval_email_delivery import PROPOSED_NEXT_DIRECTIONS
from automation.orchestration.approval_email_delivery import PROPOSED_RESTART_MODES
from automation.orchestration.approval_email_delivery import RECIPIENT_CLASSES
from automation.orchestration.approval_email_delivery import (
    build_approval_email_delivery_contract_surface,
)
from automation.orchestration.approval_email_delivery import (
    build_approval_email_delivery_run_state_summary_surface,
)
from automation.orchestration.approval_email_delivery import (
    build_approval_email_delivery_summary_surface,
)
from automation.orchestration.approval_direction_rules import derive_direction_posture
from automation.orchestration.approval_email_templates import render_approval_body_compact
from automation.orchestration.approval_email_templates import render_approval_subject
from automation.orchestration.approval_reply_commands import ALLOWED_REPLY_COMMANDS
from automation.orchestration.approval_reply_commands import is_supported_reply_command
from automation.orchestration.approval_reply_commands import map_approved_reply_command
from automation.orchestration.approval_reply_commands import normalize_reply_command
from automation.orchestration.approval_runtime_policy import (
    APPROVAL_RUNTIME_RULES_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.approval_runtime_policy import (
    APPROVAL_RUNTIME_RULES_SUMMARY_SAFE_FIELDS,
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
    APPROVAL_DELIVERY_HANDOFF_CONFIDENCE_LEVELS,
)
from automation.orchestration.approval_delivery_adapter import (
    APPROVAL_DELIVERY_HANDOFF_REASON_CODES,
)
from automation.orchestration.approval_delivery_adapter import (
    APPROVAL_DELIVERY_HANDOFF_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.approval_delivery_adapter import (
    APPROVAL_DELIVERY_HANDOFF_STATUSES,
)
from automation.orchestration.approval_delivery_adapter import (
    APPROVAL_DELIVERY_HANDOFF_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.approval_delivery_adapter import (
    APPROVAL_DELIVERY_HANDOFF_VALIDITIES,
)
from automation.orchestration.approval_delivery_adapter import (
    DOWNSTREAM_ADAPTERS,
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
    APPROVAL_RESPONSE_CONFIDENCE_LEVELS,
)
from automation.orchestration.approval_response_ingest import (
    APPROVAL_RESPONSE_REASON_CODES,
)
from automation.orchestration.approval_response_ingest import (
    APPROVAL_RESPONSE_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.approval_response_ingest import (
    APPROVAL_RESPONSE_STATUSES,
)
from automation.orchestration.approval_response_ingest import (
    APPROVAL_RESPONSE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.approval_response_ingest import (
    APPROVAL_RESPONSE_VALIDITIES,
)
from automation.orchestration.approval_response_ingest import (
    APPROVED_RESTART_CONFIDENCE_LEVELS,
)
from automation.orchestration.approval_response_ingest import (
    APPROVED_RESTART_REASON_CODES,
)
from automation.orchestration.approval_response_ingest import (
    APPROVED_RESTART_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.approval_response_ingest import (
    APPROVED_RESTART_STATUSES,
)
from automation.orchestration.approval_response_ingest import (
    APPROVED_RESTART_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.approval_response_ingest import (
    APPROVED_RESTART_VALIDITIES,
)
from automation.orchestration.approval_response_ingest import RESTART_DECISIONS
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
    APPROVAL_SAFETY_CONFIDENCE_LEVELS,
)
from automation.orchestration.approval_safety import (
    APPROVAL_SAFETY_DECISIONS,
)
from automation.orchestration.approval_safety import (
    APPROVAL_SAFETY_REASON_CODES,
)
from automation.orchestration.approval_safety import (
    APPROVAL_SAFETY_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.approval_safety import (
    APPROVAL_SAFETY_STATUSES,
)
from automation.orchestration.approval_safety import (
    APPROVAL_SAFETY_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.approval_safety import (
    APPROVAL_SAFETY_VALIDITIES,
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
from automation.orchestration.objective_contract import OBJECTIVE_RUN_STATE_SUMMARY_SAFE_FIELDS
from automation.orchestration.objective_contract import build_objective_contract_surface
from automation.orchestration.objective_contract import build_objective_run_state_summary_surface
from automation.orchestration.planned_execution_runner import DryRunCodexExecutionTransport
from automation.orchestration.planned_execution_runner import PlannedExecutionRunner
from automation.orchestration.planned_execution_runner import _augment_run_state_with_closed_loop
from automation.orchestration.planned_execution_runner import _augment_run_state_with_lifecycle_terminal_contract
from automation.orchestration.planned_execution_runner import _augment_run_state_with_operator_explainability
from automation.orchestration.planned_execution_runner import _augment_run_state_with_policy_overlay
from automation.orchestration.planned_execution_runner import _augment_run_state_with_rollback_aftermath
from automation.orchestration.planned_execution_runner import _execute_bounded_merge
from automation.orchestration.planned_execution_runner import _execute_bounded_pr_creation
from automation.orchestration.planned_execution_runner import _execute_bounded_push
from automation.orchestration.planned_execution_runner import _execute_bounded_rollback
from automation.orchestration.planned_execution_runner import _build_bounded_self_healing_state
from automation.orchestration.planned_execution_runner import _build_project_external_boundary_state
from automation.orchestration.planned_execution_runner import _build_project_failure_memory_state
from automation.orchestration.planned_execution_runner import _build_project_approval_notification_state
from automation.orchestration.planned_execution_runner import _build_project_human_escalation_state
from automation.orchestration.planned_execution_runner import _build_project_multi_objective_state
from automation.orchestration.planned_execution_runner import _build_long_running_stability_state
from automation.orchestration.planned_execution_runner import _build_objective_done_compiler_state
from automation.orchestration.planned_execution_runner import _build_project_autonomy_budget_state
from automation.orchestration.planned_execution_runner import _build_project_merge_branch_lifecycle_state
from automation.orchestration.planned_execution_runner import _build_project_quality_gate_state
from automation.orchestration.planned_execution_runner import _build_review_assimilation_state
from automation.orchestration.planned_execution_runner import _with_rollback_aftermath_surface
from automation.orchestration.repair_suggestion_contract import REPAIR_PRECONDITION_STATUSES
from automation.orchestration.repair_suggestion_contract import REPAIR_REASON_CODES
from automation.orchestration.repair_suggestion_contract import REPAIR_SUGGESTION_CLASSES
from automation.orchestration.repair_suggestion_contract import REPAIR_SUGGESTION_CONFIDENCE_LEVELS
from automation.orchestration.repair_suggestion_contract import REPAIR_SUGGESTION_DECISIONS
from automation.orchestration.repair_suggestion_contract import REPAIR_SUGGESTION_PRIORITIES
from automation.orchestration.repair_suggestion_contract import REPAIR_SUGGESTION_RUN_STATE_SUMMARY_SAFE_FIELDS
from automation.orchestration.repair_suggestion_contract import REPAIR_SUGGESTION_STATUSES
from automation.orchestration.repair_suggestion_contract import REPAIR_TARGET_SURFACES
from automation.orchestration.repair_suggestion_contract import build_repair_suggestion_contract_surface
from automation.orchestration.repair_suggestion_contract import build_repair_suggestion_run_state_summary_surface
from automation.orchestration.repair_approval_binding import (
    REPAIR_APPROVAL_BINDING_COMPATIBILITY_STATUSES,
)
from automation.orchestration.repair_approval_binding import REPAIR_APPROVAL_BINDING_DECISIONS
from automation.orchestration.repair_approval_binding import REPAIR_APPROVAL_BINDING_REASON_CODES
from automation.orchestration.repair_approval_binding import (
    REPAIR_APPROVAL_BINDING_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.repair_approval_binding import REPAIR_APPROVAL_BINDING_SCOPES
from automation.orchestration.repair_approval_binding import REPAIR_APPROVAL_BINDING_SOURCE_STATUSES
from automation.orchestration.repair_approval_binding import REPAIR_APPROVAL_BINDING_STATUSES
from automation.orchestration.repair_approval_binding import REPAIR_APPROVAL_BINDING_VALIDITIES
from automation.orchestration.repair_approval_binding import (
    build_repair_approval_binding_run_state_summary_surface,
)
from automation.orchestration.repair_approval_binding import build_repair_approval_binding_surface
from automation.orchestration.repair_plan_transport import REPAIR_PLAN_CANDIDATE_ACTIONS
from automation.orchestration.repair_plan_transport import REPAIR_PLAN_CLASSES
from automation.orchestration.repair_plan_transport import REPAIR_PLAN_CONFIDENCE_LEVELS
from automation.orchestration.repair_plan_transport import REPAIR_PLAN_DECISIONS
from automation.orchestration.repair_plan_transport import REPAIR_PLAN_PRECONDITION_STATUSES
from automation.orchestration.repair_plan_transport import REPAIR_PLAN_PRIORITIES
from automation.orchestration.repair_plan_transport import REPAIR_PLAN_REASON_CODES
from automation.orchestration.repair_plan_transport import REPAIR_PLAN_SOURCE_STATUSES
from automation.orchestration.repair_plan_transport import REPAIR_PLAN_STATUSES
from automation.orchestration.repair_plan_transport import REPAIR_PLAN_TARGET_SURFACES
from automation.orchestration.repair_plan_transport import REPAIR_PLAN_TRANSPORT_RUN_STATE_SUMMARY_SAFE_FIELDS
from automation.orchestration.repair_plan_transport import build_repair_plan_transport_run_state_summary_surface
from automation.orchestration.repair_plan_transport import build_repair_plan_transport_surface
from automation.orchestration.reconcile_contract import RECONCILE_ALIGNMENT_STATUSES
from automation.orchestration.reconcile_contract import RECONCILE_DECISIONS
from automation.orchestration.reconcile_contract import RECONCILE_RUN_STATE_SUMMARY_SAFE_FIELDS
from automation.orchestration.reconcile_contract import RECONCILE_STATUSES
from automation.orchestration.reconcile_contract import RECONCILE_TRANSPORT_STATUSES
from automation.orchestration.reconcile_contract import build_reconcile_contract_surface
from automation.orchestration.reconcile_contract import build_reconcile_run_state_summary_surface
from automation.orchestration.run_state_summary_contract import build_manifest_run_state_summary_contract_surface
from automation.orchestration.run_state_summary_contract import is_manifest_summary_safe_field
from automation.orchestration.run_state_summary_contract import select_manifest_run_state_summary_compact


class _RecordingDryRunTransport(DryRunCodexExecutionTransport):
    def __init__(self, *, status_by_pr_id: dict[str, str] | None = None) -> None:
        super().__init__(status_by_pr_id=status_by_pr_id)
        self.launch_order: list[str] = []

    def launch_job(self, **kwargs):  # type: ignore[override]
        self.launch_order.append(str(kwargs.get("pr_id", "")))
        return super().launch_job(**kwargs)


class _RecordingLiveTransport:
    def __init__(
        self,
        *,
        status_by_pr_id: dict[str, str] | None = None,
        verify_status_by_pr_id: dict[str, str] | None = None,
    ) -> None:
        self.status_by_pr_id = dict(status_by_pr_id or {})
        self.verify_status_by_pr_id = dict(verify_status_by_pr_id or {})
        self.launch_order: list[str] = []
        self.runs: dict[str, dict[str, object]] = {}

    def launch_job(self, **kwargs):  # type: ignore[override]
        pr_id = str(kwargs.get("pr_id", "")).strip()
        job_id = str(kwargs.get("job_id", "")).strip()
        run_id = f"{job_id}:{pr_id}:live"
        self.launch_order.append(pr_id)

        status = self.status_by_pr_id.get(pr_id, "completed")
        if status not in {"completed", "failed", "timed_out", "not_started", "running"}:
            status = "failed"
        verify_status = self.verify_status_by_pr_id.get(pr_id, "passed")
        if verify_status not in {"passed", "failed", "not_run"}:
            verify_status = "not_run"

        verify_reason = (
            "validation_passed"
            if verify_status == "passed"
            else "validation_failed" if verify_status == "failed" else "validation_not_run"
        )
        failure_type = None
        failure_message = None
        if status == "failed":
            failure_type = "execution_failure"
            failure_message = "mocked execution failure"
        elif status == "timed_out":
            failure_type = "transport_timeout"
            failure_message = "mocked timeout"
        elif status == "not_started":
            failure_type = "transport_submission_failure"
            failure_message = "mocked submission failure"
        elif verify_status == "failed":
            failure_type = "evaluation_failure"
            failure_message = "mocked verify failure"
        elif verify_status == "not_run":
            failure_type = "missing_signal"
            failure_message = "mocked verify missing"

        run_payload = {
            "run_id": run_id,
            "status": status,
            "attempt_count": 1,
            "started_at": "2026-04-18T00:00:00",
            "finished_at": "2026-04-18T00:00:01",
            "stdout_path": f"/tmp/{pr_id}_stdout.txt",
            "stderr_path": f"/tmp/{pr_id}_stderr.txt",
            "verify": {
                "status": verify_status,
                "commands": ["python3 -m unittest tests.test_planned_execution_runner -v"],
                "reason": verify_reason,
            },
            "changed_files": [],
            "additions": 1,
            "deletions": 0,
            "generated_patch_summary": "mocked live execution",
            "failure_type": failure_type,
            "failure_message": failure_message,
            "cost": {"tokens_input": 100, "tokens_output": 50},
            "artifacts": [],
        }
        self.runs[run_id] = run_payload
        return {"run_id": run_id, "status": status, "dry_run": False}

    def poll_status(self, **kwargs):  # type: ignore[override]
        run_id = str(kwargs.get("run_id", ""))
        payload = dict(self.runs[run_id])
        payload["dry_run"] = False
        return payload

    def collect_artifacts(self, **kwargs):  # type: ignore[override]
        run_id = str(kwargs.get("run_id", ""))
        payload = self.runs[run_id]
        return {
            "run_id": run_id,
            "stdout_path": str(payload["stdout_path"]),
            "stderr_path": str(payload["stderr_path"]),
            "artifacts": [],
            "dry_run": False,
        }


class _RollbackSignalLiveTransport(_RecordingLiveTransport):
    def launch_job(self, **kwargs):  # type: ignore[override]
        payload = super().launch_job(**kwargs)
        run_id = str(payload.get("run_id", ""))
        if run_id in self.runs:
            self.runs[run_id]["status"] = "failed"
            self.runs[run_id]["failure_type"] = "rollback_required"
            self.runs[run_id]["failure_message"] = "mocked rollback requirement"
            payload["status"] = "failed"
        return payload


class _CommitReadyLiveTransport(_RecordingLiveTransport):
    def __init__(
        self,
        *,
        changed_files_by_pr_id: dict[str, list[str]] | None = None,
    ) -> None:
        super().__init__(status_by_pr_id=None, verify_status_by_pr_id=None)
        self.changed_files_by_pr_id = dict(changed_files_by_pr_id or {})

    def launch_job(self, **kwargs):  # type: ignore[override]
        payload = super().launch_job(**kwargs)
        pr_id = str(kwargs.get("pr_id", "")).strip()
        run_id = str(payload.get("run_id", ""))
        if run_id in self.runs:
            self.runs[run_id]["changed_files"] = list(self.changed_files_by_pr_id.get(pr_id, []))
            self.runs[run_id]["status"] = "completed"
            self.runs[run_id]["verify"] = {
                "status": "passed",
                "commands": ["python3 -m unittest tests.test_planned_execution_runner -v"],
                "reason": "validation_passed",
            }
            self.runs[run_id]["failure_type"] = None
            self.runs[run_id]["failure_message"] = None
            payload["status"] = "completed"
        return payload


class _FakeGitHubReadBackend:
    def __init__(
        self,
        *,
        lookup_status: str = "success",
        matched: bool = False,
        pr_number: int | None = None,
        pr_url: str = "",
        match_count: int = 0,
        pr_status_status: str = "success",
        pr_state: str = "open",
        mergeable_state: str = "clean",
        checks_state: str = "passing",
        review_state_status: str = "satisfied",
        branch_protection_status: str = "satisfied",
    ) -> None:
        self.lookup_status = lookup_status
        self.matched = matched
        self.pr_number = pr_number
        self.pr_url = pr_url
        self.match_count = match_count
        self.pr_status_status = pr_status_status
        self.pr_state = pr_state
        self.mergeable_state = mergeable_state
        self.checks_state = checks_state
        self.review_state_status = review_state_status
        self.branch_protection_status = branch_protection_status
        self.calls: list[tuple[str, str, str]] = []
        self.status_calls: list[tuple[str, int | None, str | None]] = []

    def find_open_pr(self, repo: str, *, head_branch: str, base_branch: str):  # type: ignore[override]
        self.calls.append((repo, head_branch, base_branch))
        if self.lookup_status != "success":
            return {"operation": "find_open_pr", "status": self.lookup_status, "data": {}}
        pr_payload: dict[str, object] = {}
        if self.matched:
            pr_payload = {
                "number": self.pr_number,
                "html_url": self.pr_url or "",
            }
        return {
            "operation": "find_open_pr",
            "status": "success",
            "data": {
                "matched": self.matched,
                "match_count": self.match_count if self.match_count > 0 else (1 if self.matched else 0),
                "pr": pr_payload,
            },
        }

    def get_pr_status_summary(
        self,
        repo: str,
        *,
        pr_number: int | None = None,
        commit_sha: str | None = None,
    ):  # type: ignore[override]
        self.status_calls.append((repo, pr_number, commit_sha))
        if self.pr_status_status != "success":
            return {
                "operation": "get_pr_status_summary",
                "status": self.pr_status_status,
                "data": {},
            }
        return {
            "operation": "get_pr_status_summary",
            "status": "success",
            "data": {
                "repository": repo,
                "pr_number": pr_number,
                "pr_state": self.pr_state,
                "mergeable_state": self.mergeable_state,
                "checks_state": self.checks_state,
                "review_state_status": self.review_state_status,
                "branch_protection_status": self.branch_protection_status,
            },
        }


class _FakeGitHubWriteBackend:
    def __init__(
        self,
        *,
        create_status: str = "success",
        merge_status: str = "success",
        created_pr_number: int = 101,
        created_pr_url: str = "https://example.local/pr/101",
        merge_commit_sha: str = "d" * 40,
    ) -> None:
        self.create_status = create_status
        self.merge_status = merge_status
        self.created_pr_number = created_pr_number
        self.created_pr_url = created_pr_url
        self.merge_commit_sha = merge_commit_sha
        self.create_calls: list[dict[str, object]] = []
        self.merge_calls: list[dict[str, object]] = []

    def create_draft_pr(
        self,
        *,
        repo: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str,
    ):  # type: ignore[override]
        self.create_calls.append(
            {
                "repo": repo,
                "title": title,
                "body": body,
                "head_branch": head_branch,
                "base_branch": base_branch,
            }
        )
        if self.create_status != "success":
            return {"operation": "create_draft_pr", "status": self.create_status, "data": {}}
        return {
            "operation": "create_draft_pr",
            "status": "success",
            "data": {
                "pr": {
                    "number": self.created_pr_number,
                    "html_url": self.created_pr_url,
                }
            },
        }

    def merge_pull_request(
        self,
        *,
        repo: str,
        pr_number: int,
        expected_head_sha: str | None = None,
        merge_method: str = "merge",
    ):  # type: ignore[override]
        self.merge_calls.append(
            {
                "repo": repo,
                "pr_number": pr_number,
                "expected_head_sha": expected_head_sha,
                "merge_method": merge_method,
            }
        )
        if self.merge_status != "success":
            return {"operation": "merge_pull_request", "status": self.merge_status, "data": {}}
        return {
            "operation": "merge_pull_request",
            "status": "success",
            "data": {
                "pr_number": pr_number,
                "merge_commit_sha": self.merge_commit_sha,
            },
        }


class PlannedExecutionRunnerTests(unittest.TestCase):
    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _script_path(self) -> Path:
        return self._repo_root() / "scripts" / "run_planned_execution.py"

    def _write_planning_artifacts(self, root: Path) -> Path:
        artifacts_dir = root / "planning_artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        project_brief = {
            "project_id": "project-planned-exec",
            "objective": "Run deterministic planned dry-run execution",
            "success_definition": "Each PR slice gets prompt, result, and receipt",
            "constraints": ["additive only"],
            "non_goals": ["no scheduler"],
            "allowed_risk_level": "conservative",
            "target_repo": "codex-local-runner",
            "target_branch": "main",
            "requested_by": "operator",
            "created_at": "2026-04-18T00:00:00+00:00",
        }
        repo_facts = {
            "repo": "codex-local-runner",
            "default_branch": "main",
            "relevant_paths": ["automation/planning", "automation/execution", "automation/orchestration"],
            "entrypoints": ["scripts/run_planned_execution.py"],
            "tests_available": ["tests/test_planned_execution_runner.py"],
            "build_commands": ["python3 -m unittest discover -s tests"],
            "lint_commands": [],
            "current_branch_rules": ["require_ci_green=true"],
            "sensitive_paths": ["orchestrator/**"],
            "source_of_truth_commit": "abc123",
        }
        roadmap = {
            "roadmap_id": "project-planned-exec-roadmap-v1",
            "milestones": [
                {
                    "milestone_id": "m-01",
                    "title": "ordered slices",
                    "tier_category": "runtime_fix_low_risk",
                    "pr_ids": [
                        "project-planned-exec-pr-01",
                        "project-planned-exec-pr-02",
                        "project-planned-exec-pr-03",
                    ],
                }
            ],
            "dependency_edges": [
                {"from": "project-planned-exec-pr-01", "to": "project-planned-exec-pr-02"},
                {"from": "project-planned-exec-pr-02", "to": "project-planned-exec-pr-03"},
            ],
            "blocked_by": [],
            "estimated_risk": "medium",
        }
        pr_plan = {
            "plan_id": "project-planned-exec-plan-v1",
            "prs": [
                {
                    "pr_id": "project-planned-exec-pr-01",
                    "title": "[planning] first slice",
                    "exact_scope": "Create first scoped unit",
                    "touched_files": ["automation/planning/prompt_compiler.py"],
                    "forbidden_files": ["orchestrator/main.py"],
                    "acceptance_criteria": ["first unit compiled"],
                    "validation_commands": ["python3 -m unittest tests.test_prompt_compiler -v"],
                    "rollback_notes": "revert slice 1",
                    "tier_category": "runtime_fix_low_risk",
                    "depends_on": [],
                },
                {
                    "pr_id": "project-planned-exec-pr-02",
                    "title": "[execution] second slice",
                    "exact_scope": "Create second scoped unit",
                    "touched_files": ["automation/execution/codex_executor_adapter.py"],
                    "forbidden_files": ["orchestrator/merge_executor.py"],
                    "acceptance_criteria": ["second unit compiled"],
                    "validation_commands": ["python3 -m unittest tests.test_codex_executor_adapter -v"],
                    "rollback_notes": "revert slice 2",
                    "tier_category": "runtime_fix_high_risk",
                    "depends_on": ["project-planned-exec-pr-01"],
                },
                {
                    "pr_id": "project-planned-exec-pr-03",
                    "title": "[orchestration] third slice",
                    "exact_scope": "Create third scoped unit",
                    "touched_files": ["automation/orchestration/planned_execution_runner.py"],
                    "forbidden_files": ["orchestrator/rollback_executor.py"],
                    "acceptance_criteria": ["third unit compiled"],
                    "validation_commands": ["python3 -m unittest tests.test_planned_execution_runner -v"],
                    "rollback_notes": "revert slice 3",
                    "tier_category": "runtime_fix_high_risk",
                    "depends_on": ["project-planned-exec-pr-02"],
                },
            ],
            "canonical_surface_notes": ["inspect_job remains authority"],
            "compatibility_notes": ["legacy replan_input.* preserved"],
            "planning_warnings": [],
        }

        write_map = {
            "project_brief.json": project_brief,
            "repo_facts.json": repo_facts,
            "roadmap.json": roadmap,
            "pr_plan.json": pr_plan,
        }
        for filename, payload in write_map.items():
            (artifacts_dir / filename).write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return artifacts_dir

    def _shrink_to_single_pr_slice(self, artifacts_dir: Path) -> str:
        pr_plan_path = artifacts_dir / "pr_plan.json"
        roadmap_path = artifacts_dir / "roadmap.json"
        pr_plan = json.loads(pr_plan_path.read_text(encoding="utf-8"))
        roadmap = json.loads(roadmap_path.read_text(encoding="utf-8"))
        first_pr = dict(pr_plan["prs"][0])
        first_pr["depends_on"] = []
        pr_plan["prs"] = [first_pr]
        roadmap["milestones"][0]["pr_ids"] = [first_pr["pr_id"]]
        roadmap["dependency_edges"] = []
        pr_plan_path.write_text(json.dumps(pr_plan, ensure_ascii=False, indent=2), encoding="utf-8")
        roadmap_path.write_text(json.dumps(roadmap, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(first_pr["touched_files"][0])

    def _init_git_repo_with_dirty_file(self, repo_dir: Path, *, changed_file: str) -> str:
        target = repo_dir / changed_file
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("baseline\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo_dir), "init"], check=True, capture_output=True, text=True)
        subprocess.run(
            ["git", "-C", str(repo_dir), "config", "user.name", "Test Runner"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-C", str(repo_dir), "config", "user.email", "test-runner@example.com"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(["git", "-C", str(repo_dir), "add", "--", changed_file], check=True, capture_output=True, text=True)
        subprocess.run(
            ["git", "-C", str(repo_dir), "commit", "-m", "initial"],
            check=True,
            capture_output=True,
            text=True,
        )
        target.write_text("baseline\nupdated\n", encoding="utf-8")
        head_before = subprocess.run(
            ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        return head_before

    def _attach_origin_remote_and_push_initial(self, repo_dir: Path) -> Path:
        remote_dir = repo_dir.parent / "origin.git"
        subprocess.run(
            ["git", "init", "--bare", str(remote_dir)],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-C", str(repo_dir), "remote", "add", "origin", str(remote_dir)],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-C", str(repo_dir), "push", "-u", "origin", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return remote_dir

    def _git_commit(self, repo_dir: Path, message: str) -> str:
        subprocess.run(
            [
                "git",
                "-C",
                str(repo_dir),
                "-c",
                "user.name=Test Runner",
                "-c",
                "user.email=test-runner@example.com",
                "commit",
                "-m",
                message,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return subprocess.run(
            ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def _init_merged_repo(self, repo_dir: Path) -> dict[str, str]:
        subprocess.run(["git", "-C", str(repo_dir), "init"], check=True, capture_output=True, text=True)
        subprocess.run(
            ["git", "-C", str(repo_dir), "config", "user.name", "Test Runner"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-C", str(repo_dir), "config", "user.email", "test-runner@example.com"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "-C", str(repo_dir), "checkout", "-b", "main"],
            check=True,
            capture_output=True,
            text=True,
        )
        readme = repo_dir / "README.md"
        readme.write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo_dir), "add", "--", "README.md"], check=True, capture_output=True, text=True)
        pre_merge_sha = self._git_commit(repo_dir, "base")

        subprocess.run(
            ["git", "-C", str(repo_dir), "checkout", "-b", "feature"],
            check=True,
            capture_output=True,
            text=True,
        )
        feature = repo_dir / "feature.txt"
        feature.write_text("feature\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo_dir), "add", "--", "feature.txt"], check=True, capture_output=True, text=True)
        source_sha = self._git_commit(repo_dir, "feature")

        subprocess.run(
            ["git", "-C", str(repo_dir), "checkout", "main"],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(repo_dir),
                "-c",
                "user.name=Test Runner",
                "-c",
                "user.email=test-runner@example.com",
                "merge",
                "--no-ff",
                "--no-edit",
                source_sha,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        merge_sha = subprocess.run(
            ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        return {
            "target_branch": "main",
            "pre_merge_sha": pre_merge_sha,
            "merge_sha": merge_sha,
        }

    def _build_retry_loop_payload(
        self,
        *,
        verification: dict[str, object] | None = None,
        execution_result: dict[str, object] | None = None,
        run_state: dict[str, object] | None = None,
        repair_suggestion: dict[str, object] | None = None,
        repair_plan: dict[str, object] | None = None,
        artifacts: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return build_retry_reentry_loop_contract_surface(
            run_id="job-retry-loop",
            completion_contract_payload={"completion_status": "not_done"},
            approval_transport_payload={"approval_status": "approved"},
            reconcile_contract_payload={"reconcile_status": "aligned"},
            repair_suggestion_contract_payload=repair_suggestion or {},
            repair_plan_transport_payload=repair_plan or {},
            repair_approval_binding_payload={"repair_approval_binding_status": "bound"},
            execution_authorization_gate_payload={"execution_authorization_status": "eligible"},
            bounded_execution_bridge_payload={"bounded_execution_status": "ready", "bounded_execution_decision": "attempt_bounded_execution"},
            execution_result_contract_payload=execution_result or {},
            verification_closure_contract_payload=verification or {},
            run_state_payload=run_state or {},
            artifact_presence=artifacts or {"verification_closure_contract.json": True, "run_state.json": True},
        )

    def _build_endgame_payload(
        self,
        *,
        verification: dict[str, object] | None = None,
        retry_loop: dict[str, object] | None = None,
        execution_result: dict[str, object] | None = None,
        run_state: dict[str, object] | None = None,
        artifacts: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return build_endgame_closure_contract_surface(
            run_id="job-endgame",
            completion_contract_payload={"objective_id": "objective-endgame", "completion_status": "not_done"},
            approval_transport_payload={"approval_status": "approved"},
            reconcile_contract_payload={"reconcile_status": "aligned"},
            execution_authorization_gate_payload={"execution_authorization_status": "eligible"},
            bounded_execution_bridge_payload={"bounded_execution_status": "ready"},
            execution_result_contract_payload=execution_result or {},
            verification_closure_contract_payload=verification or {},
            retry_reentry_loop_contract_payload=retry_loop or {},
            run_state_payload=run_state or {},
            artifact_presence=artifacts
            or {
                "verification_closure_contract.json": True,
                "retry_reentry_loop_contract.json": True,
                "run_state.json": True,
            },
        )

    def _build_loop_hardening_payload(
        self,
        *,
        completion: dict[str, object] | None = None,
        approval: dict[str, object] | None = None,
        reconcile: dict[str, object] | None = None,
        execution_result: dict[str, object] | None = None,
        verification: dict[str, object] | None = None,
        retry_loop: dict[str, object] | None = None,
        endgame: dict[str, object] | None = None,
        run_state: dict[str, object] | None = None,
        artifacts: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return build_loop_hardening_contract_surface(
            run_id="job-loop-hardening",
            completion_contract_payload=completion or {"completion_status": "not_done"},
            approval_transport_payload=approval or {"approval_status": "approved"},
            reconcile_contract_payload=reconcile or {"reconcile_status": "aligned"},
            execution_result_contract_payload=execution_result or {},
            verification_closure_contract_payload=verification or {},
            retry_reentry_loop_contract_payload=retry_loop or {},
            endgame_closure_contract_payload=endgame or {},
            run_state_payload=run_state or {},
            artifact_presence=artifacts
            or {
                "retry_reentry_loop_contract.json": True,
                "endgame_closure_contract.json": True,
                "run_state.json": True,
            },
        )

    def _build_lane_stabilization_payload(
        self,
        *,
        objective: dict[str, object] | None = None,
        completion: dict[str, object] | None = None,
        approval: dict[str, object] | None = None,
        reconcile: dict[str, object] | None = None,
        execution_authorization: dict[str, object] | None = None,
        bounded_execution: dict[str, object] | None = None,
        execution_result: dict[str, object] | None = None,
        verification: dict[str, object] | None = None,
        retry_loop: dict[str, object] | None = None,
        endgame: dict[str, object] | None = None,
        loop_hardening: dict[str, object] | None = None,
        run_state: dict[str, object] | None = None,
        artifacts: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return build_lane_stabilization_contract_surface(
            run_id="job-lane-stabilization",
            objective_contract_payload=objective or {"objective_id": "objective-lane"},
            completion_contract_payload=completion or {"completion_status": "not_done"},
            approval_transport_payload=approval or {"approval_status": "approved"},
            reconcile_contract_payload=reconcile or {"reconcile_status": "aligned"},
            execution_authorization_gate_payload=execution_authorization
            or {"execution_authorization_status": "pending"},
            bounded_execution_bridge_payload=bounded_execution
            or {"bounded_execution_status": "deferred"},
            execution_result_contract_payload=execution_result or {},
            verification_closure_contract_payload=verification or {},
            retry_reentry_loop_contract_payload=retry_loop or {},
            endgame_closure_contract_payload=endgame or {},
            loop_hardening_contract_payload=loop_hardening or {},
            run_state_payload=run_state or {},
            artifact_presence=artifacts
            or {
                "retry_reentry_loop_contract.json": True,
                "loop_hardening_contract.json": True,
                "endgame_closure_contract.json": True,
                "run_state.json": True,
            },
        )

    def _build_observability_payload(
        self,
        *,
        objective: dict[str, object] | None = None,
        execution_result: dict[str, object] | None = None,
        verification: dict[str, object] | None = None,
        retry_loop: dict[str, object] | None = None,
        endgame: dict[str, object] | None = None,
        loop_hardening: dict[str, object] | None = None,
        lane: dict[str, object] | None = None,
        run_state: dict[str, object] | None = None,
        artifact_presence: dict[str, object] | None = None,
    ) -> dict[str, object]:
        default_artifact_presence = {
            "objective_contract.json": True,
            "completion_contract.json": True,
            "approval_transport.json": True,
            "reconcile_contract.json": True,
            "repair_suggestion_contract.json": True,
            "repair_plan_transport.json": True,
            "repair_approval_binding.json": True,
            "execution_authorization_gate.json": True,
            "bounded_execution_bridge.json": True,
            "execution_result_contract.json": True,
            "verification_closure_contract.json": True,
            "retry_reentry_loop_contract.json": True,
            "endgame_closure_contract.json": True,
            "loop_hardening_contract.json": True,
            "lane_stabilization_contract.json": True,
            "contract_artifact_index.json": True,
            "run_state.json": True,
        }
        return build_observability_rollup_contract_surface(
            run_id="job-observability",
            objective_contract_payload=objective or {"objective_id": "objective-observability"},
            execution_result_contract_payload=execution_result or {},
            verification_closure_contract_payload=verification or {},
            retry_reentry_loop_contract_payload=retry_loop or {},
            endgame_closure_contract_payload=endgame or {},
            loop_hardening_contract_payload=loop_hardening or {},
            lane_stabilization_contract_payload=lane or {},
            run_state_payload=run_state or {"state": "paused"},
            artifact_presence=artifact_presence or default_artifact_presence,
            contract_artifact_index_payload={
                "objective_contract": {"path": "objective_contract.json"}
            },
        )

    def _build_failure_bucketing_hardening_payload(
        self,
        *,
        objective: dict[str, object] | None = None,
        execution_result: dict[str, object] | None = None,
        verification: dict[str, object] | None = None,
        retry_loop: dict[str, object] | None = None,
        endgame: dict[str, object] | None = None,
        loop_hardening: dict[str, object] | None = None,
        lane: dict[str, object] | None = None,
        observability: dict[str, object] | None = None,
        failure_bucket_rollup: dict[str, object] | None = None,
        bounded_execution: dict[str, object] | None = None,
        execution_authorization: dict[str, object] | None = None,
        run_state: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return build_failure_bucketing_hardening_contract_surface(
            run_id="job-failure-bucketing-hardening",
            objective_contract_payload=objective or {"objective_id": "objective-failure-bucketing"},
            execution_result_contract_payload=execution_result or {},
            verification_closure_contract_payload=verification or {},
            retry_reentry_loop_contract_payload=retry_loop or {},
            endgame_closure_contract_payload=endgame or {},
            loop_hardening_contract_payload=loop_hardening or {},
            lane_stabilization_contract_payload=lane or {},
            observability_rollup_payload=observability or {},
            failure_bucket_rollup_payload=failure_bucket_rollup or {},
            bounded_execution_bridge_payload=bounded_execution or {},
            execution_authorization_gate_payload=execution_authorization or {},
            run_state_payload=run_state or {},
        )

    def _build_retention_manifest_payload(
        self,
        *,
        paths_by_role: dict[str, object] | None = None,
        summaries_by_role: dict[str, object] | None = None,
        artifact_index: dict[str, object] | None = None,
        manifest: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return build_retention_manifest_surface(
            run_id="job-retention-manifest",
            objective_contract_payload={"objective_id": "objective-retention"},
            paths_by_role=paths_by_role
            or {
                "objective_contract": "/tmp/objective_contract.json",
                "failure_bucket_rollup": "/tmp/failure_bucket_rollup.json",
                "failure_bucketing_hardening_contract": "/tmp/failure_bucketing_hardening_contract.json",
            },
            summaries_by_role=summaries_by_role
            or {
                "objective_contract": {"objective_contract_present": True},
                "failure_bucket_rollup": {"failure_bucket_status": "classified"},
                "failure_bucketing_hardening_contract": {
                    "failure_bucketing_status": "classified"
                },
            },
            contract_artifact_index_payload=artifact_index
            or {
                "objective_contract": {"path": "/tmp/objective_contract.json"},
                "failure_bucket_rollup": {"path": "/tmp/failure_bucket_rollup.json"},
                "failure_bucketing_hardening_contract": {
                    "path": "/tmp/failure_bucketing_hardening_contract.json"
                },
            },
            manifest_payload=manifest
            or {
                "run_state_summary": {"state": "paused"},
                "run_state_summary_compact": {"state": "paused"},
            },
        )

    def _build_artifact_retention_payload(
        self,
        *,
        retention_manifest: dict[str, object] | None = None,
        artifact_index: dict[str, object] | None = None,
        observability: dict[str, object] | None = None,
        failure_hardening: dict[str, object] | None = None,
        endgame: dict[str, object] | None = None,
    ) -> dict[str, object]:
        manifest_payload = retention_manifest or self._build_retention_manifest_payload()
        return build_artifact_retention_contract_surface(
            run_id="job-artifact-retention",
            objective_contract_payload={"objective_id": "objective-retention"},
            retention_manifest_payload=manifest_payload,
            contract_artifact_index_payload=artifact_index
            or {
                role: {"path": path}
                for role, path in manifest_payload.get("path_refs", {}).items()
            },
            observability_rollup_payload=observability or {"observability_status": "ready"},
            failure_bucketing_hardening_payload=failure_hardening
            or {"failure_bucketing_status": "classified"},
            endgame_closure_contract_payload=endgame
            or {"final_closure_class": "terminal_non_success"},
        )

    def _build_fleet_safety_payload(
        self,
        *,
        objective: dict[str, object] | None = None,
        observability: dict[str, object] | None = None,
        hard_bucket: dict[str, object] | None = None,
        lane: dict[str, object] | None = None,
        loop_hardening: dict[str, object] | None = None,
        endgame: dict[str, object] | None = None,
        retry_loop: dict[str, object] | None = None,
        retention: dict[str, object] | None = None,
        retention_manifest: dict[str, object] | None = None,
        run_state: dict[str, object] | None = None,
        artifact_index: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return build_fleet_safety_control_contract_surface(
            run_id="job-fleet-safety",
            objective_contract_payload=objective or {"objective_id": "objective-fleet-safety"},
            observability_rollup_payload=observability
            or {"observability_status": "ready"},
            failure_bucketing_hardening_payload=hard_bucket
            or {
                "primary_failure_bucket": "execution_failure",
                "bucket_severity": "low",
                "bucket_stability_class": "stable",
                "bucket_terminality_class": "non_terminal",
            },
            lane_stabilization_contract_payload=lane
            or {
                "lane_status": "lane_valid",
                "current_lane": "closure_followup",
                "lane_execution_allowed": True,
                "lane_mismatch_detected": False,
                "lane_transition_blocked": False,
            },
            loop_hardening_contract_payload=loop_hardening
            or {"loop_hardening_status": "stable"},
            endgame_closure_contract_payload=endgame
            or {"final_closure_class": "completed_but_not_closed"},
            retry_reentry_loop_contract_payload=retry_loop
            or {"retry_loop_status": "hold", "same_failure_count": 0},
            artifact_retention_contract_payload=retention
            or {
                "artifact_retention_status": "ready",
                "artifact_retention_validity": "valid",
                "retention_reference_consistent": True,
                "retention_manifest_compact": True,
                "retention_alias_deduplicated": False,
            },
            retention_manifest_payload=retention_manifest
            or {"alias_deduplicated": False},
            run_state_payload=run_state or {},
            contract_artifact_index_payload=artifact_index or {},
        )

    def _build_approval_email_payload(
        self,
        *,
        objective: dict[str, object] | None = None,
        fleet_safety: dict[str, object] | None = None,
        hard_bucket: dict[str, object] | None = None,
        lane: dict[str, object] | None = None,
        loop_hardening: dict[str, object] | None = None,
        endgame: dict[str, object] | None = None,
        retry_loop: dict[str, object] | None = None,
        retention: dict[str, object] | None = None,
        run_state: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return build_approval_email_delivery_contract_surface(
            run_id="job-approval-email",
            objective_contract_payload=objective or {"objective_id": "objective-approval-email"},
            fleet_safety_control_payload=fleet_safety
            or {
                "fleet_safety_status": "freeze",
                "fleet_safety_decision": "freeze_run",
                "fleet_restart_decision": "restart_blocked",
            },
            failure_bucketing_hardening_payload=hard_bucket
            or {
                "primary_failure_bucket": "retry_exhausted",
                "bucket_severity": "critical",
                "bucket_terminality_class": "terminal",
            },
            lane_stabilization_contract_payload=lane
            or {
                "lane_status": "lane_transition_blocked",
                "current_lane": "bounded_local_patch",
                "lane_mismatch_detected": True,
            },
            loop_hardening_contract_payload=loop_hardening
            or {
                "loop_hardening_status": "freeze",
                "same_failure_stop_required": True,
            },
            endgame_closure_contract_payload=endgame
            or {"final_closure_class": "closure_unresolved"},
            retry_reentry_loop_contract_payload=retry_loop
            or {"retry_loop_decision": "replan", "retry_exhausted": True},
            artifact_retention_contract_payload=retention
            or {
                "artifact_retention_status": "ready",
                "artifact_retention_validity": "valid",
                "retention_reference_consistent": True,
                "retention_alias_deduplicated": False,
            },
            run_state_payload=run_state or {},
            contract_artifact_index_payload={},
        )

    def test_deterministic_processing_order_for_multiple_pr_slices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            transport = _RecordingDryRunTransport()
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest_a = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
                retry_context={
                    "prior_attempt_count": 0,
                    "prior_retry_class": None,
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 1,
                },
            )
            order_a = list(transport.launch_order)

            transport_b = _RecordingDryRunTransport()
            runner_b = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport_b))
            manifest_b = runner_b.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
                retry_context={
                    "prior_attempt_count": 0,
                    "prior_retry_class": None,
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 1,
                },
            )
            order_b = list(transport_b.launch_order)

        self.assertEqual(
            order_a,
            [
                "project-planned-exec-pr-01",
                "project-planned-exec-pr-02",
                "project-planned-exec-pr-03",
            ],
        )
        self.assertEqual(order_a, order_b)
        self.assertEqual(
            [entry["pr_id"] for entry in manifest_a["pr_units"]],
            [entry["pr_id"] for entry in manifest_b["pr_units"]],
        )

    def test_pr_id_mapping_and_artifact_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            transport = _RecordingDryRunTransport()
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )

            run_root = out_dir / manifest["job_id"]
            self.assertTrue((run_root / "manifest.json").exists())
            self.assertTrue((run_root / "next_action.json").exists())
            self.assertTrue((run_root / "action_handoff.json").exists())

            for entry in manifest["pr_units"]:
                pr_id = entry["pr_id"]
                unit_dir = run_root / pr_id
                self.assertTrue(unit_dir.exists())
                self.assertTrue((unit_dir / "compiled_prompt.md").exists())
                self.assertTrue((unit_dir / "bounded_step_contract.json").exists())
                self.assertTrue((unit_dir / "pr_implementation_prompt_contract.json").exists())
                self.assertTrue((unit_dir / "unit_progression.json").exists())
                self.assertTrue((unit_dir / "checkpoint_decision.json").exists())
                self.assertTrue((unit_dir / "commit_decision.json").exists())
                self.assertTrue((unit_dir / "merge_decision.json").exists())
                self.assertTrue((unit_dir / "rollback_decision.json").exists())
                self.assertTrue((unit_dir / "commit_execution.json").exists())
                self.assertTrue((unit_dir / "push_execution.json").exists())
                self.assertTrue((unit_dir / "pr_execution.json").exists())
                self.assertTrue((unit_dir / "merge_execution.json").exists())
                self.assertTrue((unit_dir / "rollback_execution.json").exists())
                self.assertTrue((unit_dir / "result.json").exists())
                self.assertTrue((unit_dir / "execution_receipt.json").exists())

                result_payload = json.loads((unit_dir / "result.json").read_text(encoding="utf-8"))
                receipt_payload = json.loads((unit_dir / "execution_receipt.json").read_text(encoding="utf-8"))
                prompt_text = (unit_dir / "compiled_prompt.md").read_text(encoding="utf-8")
                bounded_step_contract = json.loads(
                    (unit_dir / "bounded_step_contract.json").read_text(encoding="utf-8")
                )
                prompt_contract = json.loads(
                    (unit_dir / "pr_implementation_prompt_contract.json").read_text(encoding="utf-8")
                )
                unit_progression_payload = json.loads(
                    (unit_dir / "unit_progression.json").read_text(encoding="utf-8")
                )

                self.assertEqual(result_payload["pr_id"], pr_id)
                self.assertEqual(receipt_payload["pr_id"], pr_id)
                self.assertIn(f"Execute exactly one PR slice: {pr_id}", prompt_text)
                self.assertEqual(bounded_step_contract["step_id"], pr_id)
                self.assertEqual(prompt_contract["source_step_id"], pr_id)
                self.assertEqual(unit_progression_payload["pr_id"], pr_id)
                self.assertIn("contract_handoff", unit_progression_payload)
                self.assertEqual(
                    prompt_contract["progression_metadata"]["planned_step_id"],
                    pr_id,
                )
                commit_decision = json.loads((unit_dir / "commit_decision.json").read_text(encoding="utf-8"))
                merge_decision = json.loads((unit_dir / "merge_decision.json").read_text(encoding="utf-8"))
                rollback_decision = json.loads((unit_dir / "rollback_decision.json").read_text(encoding="utf-8"))
                checkpoint_decision = json.loads((unit_dir / "checkpoint_decision.json").read_text(encoding="utf-8"))
                commit_execution = json.loads((unit_dir / "commit_execution.json").read_text(encoding="utf-8"))
                self.assertEqual(
                    set(checkpoint_decision.keys()),
                    {
                        "schema_version",
                        "unit_id",
                        "checkpoint_stage",
                        "decision",
                        "rule_id",
                        "summary",
                        "blocking_reasons",
                        "required_signals",
                        "recommended_next_action",
                        "manual_intervention_required",
                        "global_stop_recommended",
                    },
                )
                self.assertEqual(
                    set(commit_decision.keys()),
                    {
                        "schema_version",
                        "unit_id",
                        "decision",
                        "rule_id",
                        "summary",
                        "blocking_reasons",
                        "required_signals",
                        "recommended_next_action",
                        "readiness_status",
                        "readiness_next_action",
                        "automation_eligible",
                        "manual_intervention_required",
                        "unresolved_blockers",
                        "prerequisites_satisfied",
                    },
                )
                self.assertEqual(
                    set(merge_decision.keys()),
                    {
                        "schema_version",
                        "unit_id",
                        "decision",
                        "rule_id",
                        "summary",
                        "blocking_reasons",
                        "required_signals",
                        "recommended_next_action",
                        "readiness_status",
                        "readiness_next_action",
                        "automation_eligible",
                        "manual_intervention_required",
                        "unresolved_blockers",
                        "prerequisites_satisfied",
                    },
                )
                self.assertEqual(
                    set(rollback_decision.keys()),
                    {
                        "schema_version",
                        "unit_id",
                        "decision",
                        "rule_id",
                        "summary",
                        "blocking_reasons",
                        "required_signals",
                        "recommended_next_action",
                        "readiness_status",
                        "readiness_next_action",
                        "automation_eligible",
                        "manual_intervention_required",
                        "unresolved_blockers",
                        "prerequisites_satisfied",
                    },
                )
                self.assertEqual(commit_decision["unit_id"], pr_id)
                self.assertEqual(merge_decision["unit_id"], pr_id)
                self.assertEqual(rollback_decision["unit_id"], pr_id)
                self.assertEqual(checkpoint_decision["unit_id"], pr_id)
                self.assertEqual(commit_execution["unit_id"], pr_id)
                self.assertEqual(commit_execution["execution_type"], "git_commit")
                self.assertIn(commit_execution["status"], {"blocked", "succeeded", "failed"})
                self.assertIn(
                    checkpoint_decision["checkpoint_stage"],
                    {
                        "post_execution",
                        "post_review",
                        "pre_commit_evaluation",
                        "pre_merge_evaluation",
                        "pre_rollback_evaluation",
                    },
                )
                self.assertIn(
                    checkpoint_decision["decision"],
                    {
                        "proceed",
                        "pause",
                        "retry",
                        "manual_review_required",
                        "escalate",
                        "commit_evaluation_ready",
                        "merge_evaluation_ready",
                        "rollback_evaluation_ready",
                        "global_stop_recommended",
                    },
                )
                self.assertIn(commit_decision["decision"], {"allowed", "blocked", "manual_required", "unknown"})
                self.assertIn(merge_decision["decision"], {"allowed", "blocked", "manual_required", "unknown"})
                self.assertIn(
                    rollback_decision["decision"],
                    {"required", "not_required", "blocked", "manual_required", "unknown"},
                )

            decision_payload = json.loads((run_root / "next_action.json").read_text(encoding="utf-8"))
            handoff_payload = json.loads((run_root / "action_handoff.json").read_text(encoding="utf-8"))
            run_state_payload = json.loads((run_root / "run_state.json").read_text(encoding="utf-8"))
            self.assertEqual(decision_payload["job_id"], manifest["job_id"])
            self.assertIn("next_action", decision_payload)
            self.assertIn("reason", decision_payload)
            self.assertIn("updated_retry_context", decision_payload)
            self.assertIn("progression_outcome", decision_payload)
            self.assertIn("progression_rule_id", decision_payload)
            self.assertEqual(handoff_payload["job_id"], manifest["job_id"])
            self.assertIn("action_consumable", handoff_payload)
            self.assertIn("handoff_created_at", handoff_payload)
            self.assertEqual(run_state_payload["run_id"], manifest["job_id"])
            self.assertIn(run_state_payload["state"], {
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
            })
            self.assertIn(
                run_state_payload["orchestration_state"],
                {
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
                },
            )
            self.assertIn(
                run_state_payload["next_run_action"],
                {
                    "continue_run",
                    "pause_run",
                    "await_manual_review",
                    "evaluate_rollback",
                    "hold_for_global_stop",
                    "complete_run",
                },
            )
            self.assertEqual(
                set(run_state_payload.keys()),
                {
                    "schema_version",
                    "run_id",
                    "state",
                    "orchestration_state",
                    "summary",
                    "units_total",
                    "units_completed",
                    "units_blocked",
                    "units_failed",
                    "units_pending",
                    "global_stop",
                    "global_stop_reason",
                    "continue_allowed",
                    "run_paused",
                    "manual_intervention_required",
                    "rollback_evaluation_pending",
                    "global_stop_recommended",
                    "next_run_action",
                    "loop_state",
                    "next_safe_action",
                    "loop_blocked_reason",
                    "loop_blocked_reasons",
                    "resumable",
                    "terminal",
                    "loop_manual_intervention_required",
                    "loop_replan_required",
                    "rollback_completed",
                    "delivery_completed",
                    "loop_allowed_actions",
                    "unit_blocked",
                    "latest_unit_id",
                    "allowed_transitions",
                    "orchestration_allowed_transitions",
                    "readiness_summary",
                    "readiness_blocked",
                    "readiness_manual_required",
                    "readiness_awaiting_prerequisites",
                    "commit_execution_summary",
                    "commit_execution_executed",
                    "commit_execution_pending",
                    "commit_execution_failed",
                    "commit_execution_manual_intervention_required",
                    "push_execution_summary",
                    "pr_execution_summary",
                    "merge_execution_summary",
                    "push_execution_succeeded",
                    "pr_execution_succeeded",
                    "merge_execution_succeeded",
                    "push_execution_pending",
                    "pr_execution_pending",
                    "merge_execution_pending",
                    "push_execution_failed",
                    "pr_execution_failed",
                    "merge_execution_failed",
                    "delivery_execution_manual_intervention_required",
                    "rollback_execution_summary",
                    "rollback_execution_attempted",
                    "rollback_execution_succeeded",
                    "rollback_execution_pending",
                    "rollback_execution_failed",
                    "rollback_execution_manual_intervention_required",
                    "rollback_replan_required",
                    "rollback_automatic_continuation_blocked",
                    "rollback_aftermath_summary",
                    "rollback_aftermath_status",
                    "rollback_aftermath_blocked",
                    "rollback_aftermath_manual_required",
                    "rollback_aftermath_missing_or_ambiguous",
                    "rollback_aftermath_blocked_reason",
                    "rollback_aftermath_blocked_reasons",
                    "rollback_remote_followup_required",
                    "rollback_manual_followup_required",
                    "rollback_validation_failed",
                    "authority_validation_summary",
                    "authority_validation_blocked",
                    "execution_authority_blocked",
                    "validation_blocked",
                    "authority_validation_manual_required",
                    "authority_validation_missing_or_ambiguous",
                    "authority_validation_blocked_reason",
                    "authority_validation_blocked_reasons",
                    "remote_github_summary",
                    "remote_github_blocked",
                    "remote_github_manual_required",
                    "remote_github_missing_or_ambiguous",
                    "remote_github_blocked_reason",
                    "remote_github_blocked_reasons",
                    "policy_status",
                    "policy_blocked",
                    "policy_manual_required",
                    "policy_replan_required",
                    "policy_resume_allowed",
                    "policy_terminal",
                    "policy_blocked_reason",
                    "policy_blocked_reasons",
                    "policy_primary_blocker_class",
                    "policy_primary_action",
                    "policy_allowed_actions",
                    "policy_disallowed_actions",
                    "policy_manual_actions",
                    "policy_resumable_reason",
                    "objective_contract_present",
                    "objective_id",
                    "objective_summary",
                    "objective_type",
                    "requested_outcome",
                    "objective_acceptance_status",
                    "objective_required_artifacts_status",
                    "objective_scope_status",
                    "objective_contract_status",
                    "objective_contract_blocked_reason",
                    "completion_contract_present",
                    "completion_status",
                    "done_status",
                    "safe_closure_status",
                    "completion_evidence_status",
                    "completion_blocked_reason",
                    "completion_manual_required",
                    "completion_replan_required",
                    "completion_lifecycle_alignment_status",
                    "approval_transport_present",
                    "approval_status",
                    "approval_decision",
                    "approval_scope",
                    "approved_action",
                    "approval_required",
                    "approval_transport_status",
                    "approval_compatibility_status",
                    "approval_blocked_reason",
                    "reconcile_contract_present",
                    "reconcile_status",
                    "reconcile_decision",
                    "reconcile_alignment_status",
                    "reconcile_primary_mismatch",
                    "reconcile_blocked_reason",
                    "reconcile_waiting_on_truth",
                    "reconcile_manual_required",
                    "reconcile_replan_required",
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
                    "repair_approval_binding_present",
                    "repair_approval_binding_status",
                    "repair_approval_binding_decision",
                    "repair_approval_binding_scope",
                    "repair_approval_binding_validity",
                    "repair_approval_binding_compatibility_status",
                    "repair_approval_binding_primary_reason",
                    "repair_approval_binding_manual_required",
                    "repair_approval_binding_replan_required",
                    "repair_approval_binding_truth_gathering_required",
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
                    "execution_result_contract_present",
                    "execution_result_status",
                    "execution_result_outcome",
                    "execution_result_validity",
                    "execution_result_confidence",
                    "execution_result_primary_reason",
                    "execution_result_attempted",
                    "execution_result_receipt_present",
                    "execution_result_output_present",
                    "execution_result_manual_followup_required",
                    "verification_closure_contract_present",
                    "verification_status",
                    "verification_outcome",
                    "verification_validity",
                    "verification_confidence",
                    "verification_primary_reason",
                    "objective_satisfaction_status",
                    "completion_satisfaction_status",
                    "closure_status",
                    "closure_decision",
                    "objective_satisfied",
                    "completion_satisfied",
                    "safely_closable",
                    "manual_closure_required",
                    "closure_followup_required",
                    "external_truth_required",
                    "retry_reentry_loop_contract_present",
                    "retry_loop_status",
                    "retry_loop_decision",
                    "retry_loop_validity",
                    "retry_loop_confidence",
                    "loop_primary_reason",
                    "attempt_count",
                    "max_attempt_count",
                    "reentry_count",
                    "max_reentry_count",
                    "same_failure_count",
                    "max_same_failure_count",
                    "retry_allowed",
                    "reentry_allowed",
                    "retry_exhausted",
                    "reentry_exhausted",
                    "same_failure_exhausted",
                    "terminal_stop_required",
                    "manual_escalation_required",
                    "replan_required",
                    "recollect_required",
                    "same_lane_retry_allowed",
                    "repair_retry_allowed",
                    "no_progress_stop_required",
                    "endgame_closure_contract_present",
                    "endgame_closure_status",
                    "endgame_closure_outcome",
                    "endgame_closure_validity",
                    "endgame_closure_confidence",
                    "final_closure_class",
                    "terminal_stop_class",
                    "closure_resolution_status",
                    "endgame_primary_reason",
                    "safely_closed",
                    "completed_but_not_closed",
                    "rollback_complete_but_not_closed",
                    "manual_closure_only",
                    "external_truth_pending",
                    "closure_unresolved",
                    "terminal_success",
                    "terminal_non_success",
                    "operator_followup_required",
                    "further_retry_allowed",
                    "further_reentry_allowed",
                    "loop_hardening_contract_present",
                    "loop_hardening_status",
                    "loop_hardening_decision",
                    "loop_hardening_validity",
                    "loop_hardening_confidence",
                    "loop_hardening_primary_reason",
                    "same_failure_signature",
                    "same_failure_bucket",
                    "same_failure_persistence",
                    "no_progress_status",
                    "oscillation_status",
                    "retry_freeze_status",
                    "same_failure_detected",
                    "same_failure_stop_required",
                    "no_progress_detected",
                    "oscillation_detected",
                    "unstable_loop_detected",
                    "retry_freeze_required",
                    "cool_down_required",
                    "forced_manual_escalation_required",
                    "hardening_stop_required",
                    "lane_stabilization_contract_present",
                    "lane_status",
                    "lane_decision",
                    "lane_validity",
                    "lane_confidence",
                    "current_lane",
                    "target_lane",
                    "lane_transition_status",
                    "lane_transition_decision",
                    "lane_preconditions_status",
                    "lane_retry_policy_class",
                    "lane_verification_policy_class",
                    "lane_escalation_policy_class",
                    "lane_attempt_budget",
                    "lane_reentry_budget",
                    "lane_transition_count",
                    "max_lane_transition_count",
                    "lane_primary_reason",
                    "lane_valid",
                    "lane_mismatch_detected",
                    "lane_transition_required",
                    "lane_transition_allowed",
                    "lane_transition_blocked",
                    "lane_stop_required",
                    "lane_manual_review_required",
                    "lane_replan_required",
                    "lane_truth_gathering_required",
                    "lane_execution_allowed",
                    "observability_rollup_present",
                    "failure_bucketing_hardening_present",
                    "artifact_retention_present",
                    "fleet_safety_control_present",
                    "approval_email_delivery_present",
                    "approval_runtime_rules_present",
                    "approval_delivery_handoff_present",
                    "approval_response_present",
                    "approved_restart_present",
                    "approval_safety_present",
                    "operator_posture_summary",
                    "operator_primary_blocker_class",
                    "operator_primary_action",
                    "operator_action_scope",
                    "operator_resume_status",
                    "operator_next_safe_posture",
                    "lifecycle_closure_status",
                    "lifecycle_safely_closed",
                    "lifecycle_terminal",
                    "lifecycle_resumable",
                    "lifecycle_manual_required",
                    "lifecycle_replan_required",
                    "lifecycle_execution_complete_not_closed",
                    "lifecycle_rollback_complete_not_closed",
                    "lifecycle_blocked_reason",
                    "lifecycle_blocked_reasons",
                    "lifecycle_primary_closure_issue",
                    "lifecycle_stop_class",
                },
            )

    def test_launch_metadata_uses_structured_contract_surfaces(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"
            transport = _RecordingDryRunTransport()
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )

            first = manifest["pr_units"][0]
            unit_dir = Path(first["compiled_prompt_path"]).parent
            bounded = json.loads((unit_dir / "bounded_step_contract.json").read_text(encoding="utf-8"))
            prompt_contract = json.loads(
                (unit_dir / "pr_implementation_prompt_contract.json").read_text(encoding="utf-8")
            )
            run_ids = sorted(transport._runs.keys())  # type: ignore[attr-defined]
            first_run = transport._runs[run_ids[0]]  # type: ignore[attr-defined]
            metadata = first_run["metadata"]

        self.assertEqual(metadata["planned_step_id"], bounded["step_id"])
        self.assertEqual(metadata["source_step_id"], prompt_contract["source_step_id"])
        self.assertEqual(
            metadata["strict_scope_files"],
            bounded["progression_metadata"]["strict_scope_files"],
        )
        self.assertEqual(
            metadata["validation_commands"],
            bounded["validation_expectations"],
        )

    def test_manifest_generation_and_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=_RecordingDryRunTransport()))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )

        self.assertIn("job_id", manifest)
        self.assertIn("run_status", manifest)
        self.assertIn("artifact_input_dir", manifest)
        self.assertIn("artifact_ownership", manifest)
        self.assertIn("started_at", manifest)
        self.assertIn("finished_at", manifest)
        self.assertIn("pr_units", manifest)
        self.assertEqual(manifest["run_status"], "dry_run_completed")
        self.assertGreaterEqual(len(manifest["pr_units"]), 1)
        self.assertIn("decision_summary", manifest)
        self.assertIn("progression_summary", manifest)
        self.assertIn("run_state_summary", manifest)
        self.assertIn("run_state_summary_compact", manifest)
        self.assertIn("run_state_summary_contract", manifest)
        self.assertIn("objective_contract_summary", manifest)
        self.assertIn("objective_contract_path", manifest)
        self.assertIn("completion_contract_summary", manifest)
        self.assertIn("completion_contract_path", manifest)
        self.assertIn("approval_transport_summary", manifest)
        self.assertIn("approval_transport_path", manifest)
        self.assertIn("reconcile_contract_summary", manifest)
        self.assertIn("reconcile_contract_path", manifest)
        self.assertIn("repair_suggestion_contract_summary", manifest)
        self.assertIn("repair_suggestion_contract_path", manifest)
        self.assertIn("repair_plan_transport_summary", manifest)
        self.assertIn("repair_plan_transport_path", manifest)
        self.assertIn("repair_approval_binding_summary", manifest)
        self.assertIn("repair_approval_binding_path", manifest)
        self.assertIn("execution_authorization_gate_summary", manifest)
        self.assertIn("execution_authorization_gate_path", manifest)
        self.assertIn("bounded_execution_bridge_summary", manifest)
        self.assertIn("bounded_execution_bridge_path", manifest)
        self.assertIn("execution_result_contract_summary", manifest)
        self.assertIn("execution_result_contract_path", manifest)
        self.assertIn("verification_closure_contract_summary", manifest)
        self.assertIn("verification_closure_contract_path", manifest)
        self.assertIn("retry_reentry_loop_contract_summary", manifest)
        self.assertIn("retry_reentry_loop_contract_path", manifest)
        self.assertIn("endgame_closure_contract_summary", manifest)
        self.assertIn("endgame_closure_contract_path", manifest)
        self.assertIn("loop_hardening_contract_summary", manifest)
        self.assertIn("loop_hardening_contract_path", manifest)
        self.assertIn("lane_stabilization_contract_summary", manifest)
        self.assertIn("lane_stabilization_contract_path", manifest)
        self.assertIn("observability_rollup_contract_summary", manifest)
        self.assertIn("observability_rollup_contract_path", manifest)
        self.assertIn("failure_bucket_rollup_summary", manifest)
        self.assertIn("failure_bucket_rollup_path", manifest)
        self.assertIn("fleet_run_rollup_summary", manifest)
        self.assertIn("fleet_run_rollup_path", manifest)
        self.assertIn("failure_bucketing_hardening_contract_summary", manifest)
        self.assertIn("failure_bucketing_hardening_contract_path", manifest)
        self.assertIn("retention_manifest_summary", manifest)
        self.assertIn("retention_manifest_path", manifest)
        self.assertIn("artifact_retention_contract_summary", manifest)
        self.assertIn("artifact_retention_contract_path", manifest)
        self.assertIn("fleet_safety_control_contract_summary", manifest)
        self.assertIn("fleet_safety_control_contract_path", manifest)
        self.assertIn("approval_email_delivery_contract_summary", manifest)
        self.assertIn("approval_email_delivery_contract_path", manifest)
        self.assertIn("approval_runtime_rules_contract_summary", manifest)
        self.assertIn("approval_runtime_rules_contract_path", manifest)
        self.assertIn("approval_delivery_handoff_contract_summary", manifest)
        self.assertIn("approval_delivery_handoff_contract_path", manifest)
        self.assertIn("approval_response_contract_summary", manifest)
        self.assertIn("approval_response_contract_path", manifest)
        self.assertIn("approved_restart_contract_summary", manifest)
        self.assertIn("approved_restart_contract_path", manifest)
        self.assertIn("approval_safety_contract_summary", manifest)
        self.assertIn("approval_safety_contract_path", manifest)
        self.assertIn("contract_artifact_index", manifest)
        self.assertIn("manifest_path", manifest)
        self.assertIn("next_action_path", manifest)
        self.assertIn("action_handoff_path", manifest)
        self.assertIn("run_state_path", manifest)
        self.assertIn("retry_context_store_path", manifest)
        self.assertIn("handoff_summary", manifest)
        self.assertEqual(
            manifest["decision_summary"]["next_action"],
            "signal_recollect",
        )
        self.assertEqual(
            manifest["handoff_summary"]["next_action"],
            "signal_recollect",
        )
        self.assertEqual(manifest["progression_summary"]["final_unit_state"], "reviewed")
        self.assertEqual(manifest["run_state_summary_compact"]["state"], "paused")
        self.assertEqual(
            manifest["run_state_summary"],
            manifest["run_state_summary_compact"],
        )
        self.assertNotIn("loop_blocked_reasons", manifest["run_state_summary"])
        self.assertNotIn("policy_blocked_reasons", manifest["run_state_summary"])
        self.assertNotIn("lifecycle_blocked_reasons", manifest["run_state_summary"])
        self.assertNotIn("reconcile_blocked_reasons", manifest["run_state_summary"])
        self.assertNotIn("operator_guidance_summary", manifest["run_state_summary"])
        self.assertNotIn("operator_safe_actions_summary", manifest["run_state_summary"])
        self.assertNotIn("operator_unsafe_actions_summary", manifest["run_state_summary"])
        self.assertIn("loop_hardening_contract_present", manifest["run_state_summary_compact"])
        self.assertIn("loop_hardening_status", manifest["run_state_summary_compact"])
        self.assertIn("loop_hardening_decision", manifest["run_state_summary_compact"])
        self.assertIn("loop_hardening_primary_reason", manifest["run_state_summary_compact"])
        self.assertIn("lane_stabilization_contract_present", manifest["run_state_summary_compact"])
        self.assertIn("lane_status", manifest["run_state_summary_compact"])
        self.assertIn("lane_decision", manifest["run_state_summary_compact"])
        self.assertIn("lane_primary_reason", manifest["run_state_summary_compact"])
        self.assertIn("observability_rollup_present", manifest["run_state_summary_compact"])
        self.assertIn("failure_bucketing_hardening_present", manifest["run_state_summary_compact"])
        self.assertIn("artifact_retention_present", manifest["run_state_summary_compact"])
        self.assertIn("fleet_safety_control_present", manifest["run_state_summary_compact"])
        self.assertIn("approval_email_delivery_present", manifest["run_state_summary_compact"])
        self.assertIn("approval_runtime_rules_present", manifest["run_state_summary_compact"])
        self.assertIn("approval_delivery_handoff_present", manifest["run_state_summary_compact"])
        self.assertIn("approval_response_present", manifest["run_state_summary_compact"])
        self.assertIn("approved_restart_present", manifest["run_state_summary_compact"])
        self.assertIn("approval_safety_present", manifest["run_state_summary_compact"])
        self.assertNotIn("observability_status", manifest["run_state_summary_compact"])
        self.assertNotIn("primary_failure_bucket", manifest["run_state_summary_compact"])
        self.assertNotIn("fleet_terminal_class", manifest["run_state_summary_compact"])
        self.assertNotIn("bucket_family", manifest["run_state_summary_compact"])
        self.assertNotIn("bucket_severity", manifest["run_state_summary_compact"])
        self.assertNotIn("artifact_retention_status", manifest["run_state_summary_compact"])
        self.assertNotIn("fleet_safety_status", manifest["run_state_summary_compact"])
        self.assertNotIn("approval_email_status", manifest["run_state_summary_compact"])
        self.assertNotIn("runtime_rules_version", manifest["run_state_summary_compact"])
        self.assertNotIn("approval_delivery_handoff_status", manifest["run_state_summary_compact"])
        self.assertNotIn("approval_response_status", manifest["run_state_summary_compact"])
        self.assertNotIn("approved_restart_status", manifest["run_state_summary_compact"])
        self.assertNotIn("approval_safety_status", manifest["run_state_summary_compact"])
        self.assertIn("lifecycle_closure_status", manifest["run_state_summary_compact"])
        self.assertIn("lifecycle_safely_closed", manifest["run_state_summary_compact"])
        self.assertIn("lifecycle_terminal", manifest["run_state_summary_compact"])
        self.assertIn("lifecycle_resumable", manifest["run_state_summary_compact"])
        self.assertIn("lifecycle_manual_required", manifest["run_state_summary_compact"])
        self.assertIn("lifecycle_replan_required", manifest["run_state_summary_compact"])
        self.assertIn("lifecycle_execution_complete_not_closed", manifest["run_state_summary_compact"])
        self.assertIn("lifecycle_rollback_complete_not_closed", manifest["run_state_summary_compact"])
        self.assertIn("lifecycle_blocked_reason", manifest["run_state_summary_compact"])
        self.assertIn("lifecycle_primary_closure_issue", manifest["run_state_summary_compact"])
        self.assertIn("lifecycle_stop_class", manifest["run_state_summary_compact"])
        self.assertNotIn("lifecycle_blocked_reasons", manifest["run_state_summary_compact"])
        self.assertIn("operator_posture_summary", manifest["run_state_summary_compact"])
        self.assertIn("operator_primary_blocker_class", manifest["run_state_summary_compact"])
        self.assertIn("operator_primary_action", manifest["run_state_summary_compact"])
        self.assertIn("operator_resume_status", manifest["run_state_summary_compact"])
        self.assertIn("operator_next_safe_posture", manifest["run_state_summary_compact"])
        self.assertIn("objective_contract_present", manifest["run_state_summary_compact"])
        self.assertIn("objective_id", manifest["run_state_summary_compact"])
        self.assertIn("objective_summary", manifest["run_state_summary_compact"])
        self.assertIn("objective_type", manifest["run_state_summary_compact"])
        self.assertIn("requested_outcome", manifest["run_state_summary_compact"])
        self.assertIn("objective_acceptance_status", manifest["run_state_summary_compact"])
        self.assertIn("objective_required_artifacts_status", manifest["run_state_summary_compact"])
        self.assertIn("objective_scope_status", manifest["run_state_summary_compact"])
        self.assertIn("objective_contract_status", manifest["run_state_summary_compact"])
        self.assertIn("objective_contract_blocked_reason", manifest["run_state_summary_compact"])
        self.assertIn("completion_contract_present", manifest["run_state_summary_compact"])
        self.assertIn("completion_status", manifest["run_state_summary_compact"])
        self.assertIn("done_status", manifest["run_state_summary_compact"])
        self.assertIn("safe_closure_status", manifest["run_state_summary_compact"])
        self.assertIn("completion_evidence_status", manifest["run_state_summary_compact"])
        self.assertIn("completion_blocked_reason", manifest["run_state_summary_compact"])
        self.assertIn("completion_manual_required", manifest["run_state_summary_compact"])
        self.assertIn("completion_replan_required", manifest["run_state_summary_compact"])
        self.assertIn("completion_lifecycle_alignment_status", manifest["run_state_summary_compact"])
        self.assertIn("approval_transport_present", manifest["run_state_summary_compact"])
        self.assertIn("approval_status", manifest["run_state_summary_compact"])
        self.assertIn("approval_decision", manifest["run_state_summary_compact"])
        self.assertIn("approval_scope", manifest["run_state_summary_compact"])
        self.assertIn("approved_action", manifest["run_state_summary_compact"])
        self.assertIn("approval_required", manifest["run_state_summary_compact"])
        self.assertIn("approval_transport_status", manifest["run_state_summary_compact"])
        self.assertIn("approval_compatibility_status", manifest["run_state_summary_compact"])
        self.assertIn("approval_blocked_reason", manifest["run_state_summary_compact"])
        self.assertIn("reconcile_contract_present", manifest["run_state_summary_compact"])
        self.assertIn("reconcile_status", manifest["run_state_summary_compact"])
        self.assertIn("reconcile_decision", manifest["run_state_summary_compact"])
        self.assertIn("reconcile_alignment_status", manifest["run_state_summary_compact"])
        self.assertIn("reconcile_primary_mismatch", manifest["run_state_summary_compact"])
        self.assertIn("reconcile_blocked_reason", manifest["run_state_summary_compact"])
        self.assertIn("reconcile_waiting_on_truth", manifest["run_state_summary_compact"])
        self.assertIn("reconcile_manual_required", manifest["run_state_summary_compact"])
        self.assertIn("reconcile_replan_required", manifest["run_state_summary_compact"])
        self.assertIn("repair_suggestion_contract_present", manifest["run_state_summary_compact"])
        self.assertIn("repair_suggestion_status", manifest["run_state_summary_compact"])
        self.assertIn("repair_suggestion_decision", manifest["run_state_summary_compact"])
        self.assertIn("repair_suggestion_class", manifest["run_state_summary_compact"])
        self.assertIn("repair_suggestion_priority", manifest["run_state_summary_compact"])
        self.assertIn("repair_suggestion_confidence", manifest["run_state_summary_compact"])
        self.assertIn("repair_primary_reason", manifest["run_state_summary_compact"])
        self.assertIn("repair_manual_required", manifest["run_state_summary_compact"])
        self.assertIn("repair_replan_required", manifest["run_state_summary_compact"])
        self.assertIn("repair_truth_gathering_required", manifest["run_state_summary_compact"])
        self.assertIn("repair_plan_transport_present", manifest["run_state_summary_compact"])
        self.assertIn("repair_plan_status", manifest["run_state_summary_compact"])
        self.assertIn("repair_plan_decision", manifest["run_state_summary_compact"])
        self.assertIn("repair_plan_class", manifest["run_state_summary_compact"])
        self.assertIn("repair_plan_priority", manifest["run_state_summary_compact"])
        self.assertIn("repair_plan_confidence", manifest["run_state_summary_compact"])
        self.assertIn("repair_plan_target_surface", manifest["run_state_summary_compact"])
        self.assertIn("repair_plan_candidate_action", manifest["run_state_summary_compact"])
        self.assertIn("repair_plan_primary_reason", manifest["run_state_summary_compact"])
        self.assertIn("repair_plan_manual_required", manifest["run_state_summary_compact"])
        self.assertIn("repair_plan_replan_required", manifest["run_state_summary_compact"])
        self.assertIn("repair_plan_truth_gathering_required", manifest["run_state_summary_compact"])
        self.assertIn("repair_approval_binding_present", manifest["run_state_summary_compact"])
        self.assertIn("repair_approval_binding_status", manifest["run_state_summary_compact"])
        self.assertIn("repair_approval_binding_decision", manifest["run_state_summary_compact"])
        self.assertIn("repair_approval_binding_scope", manifest["run_state_summary_compact"])
        self.assertIn("repair_approval_binding_validity", manifest["run_state_summary_compact"])
        self.assertIn(
            "repair_approval_binding_compatibility_status",
            manifest["run_state_summary_compact"],
        )
        self.assertIn("repair_approval_binding_primary_reason", manifest["run_state_summary_compact"])
        self.assertIn("repair_approval_binding_manual_required", manifest["run_state_summary_compact"])
        self.assertIn("repair_approval_binding_replan_required", manifest["run_state_summary_compact"])
        self.assertIn(
            "repair_approval_binding_truth_gathering_required",
            manifest["run_state_summary_compact"],
        )
        self.assertIn("execution_authorization_gate_present", manifest["run_state_summary_compact"])
        self.assertIn("execution_authorization_status", manifest["run_state_summary_compact"])
        self.assertIn("execution_authorization_decision", manifest["run_state_summary_compact"])
        self.assertIn("execution_authorization_scope", manifest["run_state_summary_compact"])
        self.assertIn("execution_authorization_validity", manifest["run_state_summary_compact"])
        self.assertIn("execution_authorization_confidence", manifest["run_state_summary_compact"])
        self.assertIn("execution_authorization_primary_reason", manifest["run_state_summary_compact"])
        self.assertIn("execution_authorization_manual_required", manifest["run_state_summary_compact"])
        self.assertIn("execution_authorization_replan_required", manifest["run_state_summary_compact"])
        self.assertIn(
            "execution_authorization_truth_gathering_required",
            manifest["run_state_summary_compact"],
        )
        self.assertIn("bounded_execution_bridge_present", manifest["run_state_summary_compact"])
        self.assertIn("bounded_execution_status", manifest["run_state_summary_compact"])
        self.assertIn("bounded_execution_decision", manifest["run_state_summary_compact"])
        self.assertIn("bounded_execution_scope", manifest["run_state_summary_compact"])
        self.assertIn("bounded_execution_validity", manifest["run_state_summary_compact"])
        self.assertIn("bounded_execution_confidence", manifest["run_state_summary_compact"])
        self.assertIn("bounded_execution_primary_reason", manifest["run_state_summary_compact"])
        self.assertIn("bounded_execution_manual_required", manifest["run_state_summary_compact"])
        self.assertIn("bounded_execution_replan_required", manifest["run_state_summary_compact"])
        self.assertIn(
            "bounded_execution_truth_gathering_required",
            manifest["run_state_summary_compact"],
        )
        self.assertIn(
            "verification_closure_contract_present",
            manifest["run_state_summary_compact"],
        )
        self.assertIn("verification_status", manifest["run_state_summary_compact"])
        self.assertIn("verification_outcome", manifest["run_state_summary_compact"])
        self.assertIn("verification_validity", manifest["run_state_summary_compact"])
        self.assertIn("verification_confidence", manifest["run_state_summary_compact"])
        self.assertIn("verification_primary_reason", manifest["run_state_summary_compact"])
        self.assertIn("objective_satisfaction_status", manifest["run_state_summary_compact"])
        self.assertIn("completion_satisfaction_status", manifest["run_state_summary_compact"])
        self.assertIn("closure_status", manifest["run_state_summary_compact"])
        self.assertIn("closure_decision", manifest["run_state_summary_compact"])
        self.assertIn("objective_satisfied", manifest["run_state_summary_compact"])
        self.assertIn("completion_satisfied", manifest["run_state_summary_compact"])
        self.assertIn("safely_closable", manifest["run_state_summary_compact"])
        self.assertIn("manual_closure_required", manifest["run_state_summary_compact"])
        self.assertIn("closure_followup_required", manifest["run_state_summary_compact"])
        self.assertIn("external_truth_required", manifest["run_state_summary_compact"])
        self.assertIn("retry_reentry_loop_contract_present", manifest["run_state_summary_compact"])
        self.assertIn("retry_loop_status", manifest["run_state_summary_compact"])
        self.assertIn("retry_loop_decision", manifest["run_state_summary_compact"])
        self.assertIn("retry_loop_validity", manifest["run_state_summary_compact"])
        self.assertIn("retry_loop_confidence", manifest["run_state_summary_compact"])
        self.assertIn("loop_primary_reason", manifest["run_state_summary_compact"])
        self.assertIn("attempt_count", manifest["run_state_summary_compact"])
        self.assertIn("max_attempt_count", manifest["run_state_summary_compact"])
        self.assertIn("reentry_count", manifest["run_state_summary_compact"])
        self.assertIn("max_reentry_count", manifest["run_state_summary_compact"])
        self.assertIn("same_failure_count", manifest["run_state_summary_compact"])
        self.assertIn("max_same_failure_count", manifest["run_state_summary_compact"])
        self.assertIn("retry_allowed", manifest["run_state_summary_compact"])
        self.assertIn("reentry_allowed", manifest["run_state_summary_compact"])
        self.assertIn("retry_exhausted", manifest["run_state_summary_compact"])
        self.assertIn("reentry_exhausted", manifest["run_state_summary_compact"])
        self.assertIn("same_failure_exhausted", manifest["run_state_summary_compact"])
        self.assertIn("terminal_stop_required", manifest["run_state_summary_compact"])
        self.assertIn("manual_escalation_required", manifest["run_state_summary_compact"])
        self.assertIn("replan_required", manifest["run_state_summary_compact"])
        self.assertIn("recollect_required", manifest["run_state_summary_compact"])
        self.assertIn("same_lane_retry_allowed", manifest["run_state_summary_compact"])
        self.assertIn("repair_retry_allowed", manifest["run_state_summary_compact"])
        self.assertIn("no_progress_stop_required", manifest["run_state_summary_compact"])
        self.assertIn("endgame_closure_contract_present", manifest["run_state_summary_compact"])
        self.assertIn("endgame_closure_status", manifest["run_state_summary_compact"])
        self.assertIn("endgame_closure_outcome", manifest["run_state_summary_compact"])
        self.assertIn("endgame_closure_validity", manifest["run_state_summary_compact"])
        self.assertIn("endgame_closure_confidence", manifest["run_state_summary_compact"])
        self.assertIn("final_closure_class", manifest["run_state_summary_compact"])
        self.assertIn("terminal_stop_class", manifest["run_state_summary_compact"])
        self.assertIn("closure_resolution_status", manifest["run_state_summary_compact"])
        self.assertIn("endgame_primary_reason", manifest["run_state_summary_compact"])
        self.assertIn("safely_closed", manifest["run_state_summary_compact"])
        self.assertIn("completed_but_not_closed", manifest["run_state_summary_compact"])
        self.assertIn(
            "rollback_complete_but_not_closed",
            manifest["run_state_summary_compact"],
        )
        self.assertIn("manual_closure_only", manifest["run_state_summary_compact"])
        self.assertIn("external_truth_pending", manifest["run_state_summary_compact"])
        self.assertIn("closure_unresolved", manifest["run_state_summary_compact"])
        self.assertIn("terminal_success", manifest["run_state_summary_compact"])
        self.assertIn("terminal_non_success", manifest["run_state_summary_compact"])
        self.assertIn("operator_followup_required", manifest["run_state_summary_compact"])
        self.assertIn("further_retry_allowed", manifest["run_state_summary_compact"])
        self.assertIn("further_reentry_allowed", manifest["run_state_summary_compact"])
        self.assertIn("lane_stabilization_contract_present", manifest["run_state_summary_compact"])
        self.assertIn("lane_status", manifest["run_state_summary_compact"])
        self.assertIn("lane_decision", manifest["run_state_summary_compact"])
        self.assertIn("lane_primary_reason", manifest["run_state_summary_compact"])
        self.assertIn("current_lane", manifest["run_state_summary_compact"])
        self.assertIn("target_lane", manifest["run_state_summary_compact"])
        self.assertNotIn("reconcile_blocked_reasons", manifest["run_state_summary_compact"])
        self.assertNotIn("repair_reason_codes", manifest["run_state_summary_compact"])
        self.assertNotIn("repair_plan_reason_codes", manifest["run_state_summary_compact"])
        self.assertNotIn("repair_plan_blocked_reasons", manifest["run_state_summary_compact"])
        self.assertNotIn("repair_approval_binding_reason_codes", manifest["run_state_summary_compact"])
        self.assertNotIn("repair_approval_binding_blocked_reasons", manifest["run_state_summary_compact"])
        self.assertNotIn("execution_authorization_reason_codes", manifest["run_state_summary_compact"])
        self.assertNotIn("execution_authorization_blocked_reasons", manifest["run_state_summary_compact"])
        self.assertNotIn("bounded_execution_reason_codes", manifest["run_state_summary_compact"])
        self.assertNotIn("bounded_execution_blocked_reasons", manifest["run_state_summary_compact"])
        self.assertNotIn("verification_reason_codes", manifest["run_state_summary_compact"])
        self.assertNotIn("loop_reason_codes", manifest["run_state_summary_compact"])
        self.assertNotIn("endgame_reason_codes", manifest["run_state_summary_compact"])
        self.assertNotIn("operator_guidance_summary", manifest["run_state_summary_compact"])
        self.assertNotIn("operator_safe_actions_summary", manifest["run_state_summary_compact"])
        self.assertNotIn("operator_unsafe_actions_summary", manifest["run_state_summary_compact"])
        self.assertEqual(
            manifest["run_state_summary_contract"]["canonical_run_truth_owner"],
            "run_state.json",
        )
        self.assertEqual(
            manifest["run_state_summary_contract"]["compatibility_summary_field"],
            "run_state_summary",
        )
        self.assertEqual(
            manifest["run_state_summary_contract"]["compatibility_summary_mode"],
            "alias_to_compact_deprecated_verbose",
        )
        self.assertIn(
            "operator_guidance_summary",
            manifest["run_state_summary_contract"]["rendering_only_operator_fields"],
        )
        self.assertIn(
            "lifecycle_closure_status",
            manifest["run_state_summary_contract"]["lifecycle_summary_safe_fields"],
        )
        self.assertEqual(
            set(manifest["run_state_summary_contract"]["objective_summary_safe_fields"]),
            set(OBJECTIVE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(manifest["run_state_summary_contract"]["completion_summary_safe_fields"]),
            set(COMPLETION_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(manifest["run_state_summary_contract"]["approval_summary_safe_fields"]),
            set(APPROVAL_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(manifest["run_state_summary_contract"]["reconcile_summary_safe_fields"]),
            set(RECONCILE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(manifest["run_state_summary_contract"]["repair_suggestion_summary_safe_fields"]),
            set(REPAIR_SUGGESTION_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(manifest["run_state_summary_contract"]["repair_plan_transport_summary_safe_fields"]),
            set(REPAIR_PLAN_TRANSPORT_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(manifest["run_state_summary_contract"]["repair_approval_binding_summary_safe_fields"]),
            set(REPAIR_APPROVAL_BINDING_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(manifest["run_state_summary_contract"]["execution_authorization_summary_safe_fields"]),
            set(EXECUTION_AUTHORIZATION_GATE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(manifest["run_state_summary_contract"]["bounded_execution_summary_safe_fields"]),
            set(BOUNDED_EXECUTION_BRIDGE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(manifest["run_state_summary_contract"]["execution_result_summary_safe_fields"]),
            set(EXECUTION_RESULT_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(manifest["run_state_summary_contract"]["verification_closure_summary_safe_fields"]),
            set(VERIFICATION_CLOSURE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(manifest["run_state_summary_contract"]["retry_reentry_loop_summary_safe_fields"]),
            set(RETRY_REENTRY_LOOP_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(manifest["run_state_summary_contract"]["endgame_closure_summary_safe_fields"]),
            set(ENDGAME_CLOSURE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(manifest["run_state_summary_contract"]["loop_hardening_summary_safe_fields"]),
            set(LOOP_HARDENING_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(manifest["run_state_summary_contract"]["lane_stabilization_summary_safe_fields"]),
            set(LANE_STABILIZATION_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(manifest["run_state_summary_contract"]["observability_summary_safe_fields"]),
            set(OBSERVABILITY_ROLLUP_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(
                manifest["run_state_summary_contract"][
                    "failure_bucketing_hardening_summary_safe_fields"
                ]
            ),
            set(FAILURE_BUCKETING_HARDENING_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(
                manifest["run_state_summary_contract"][
                    "artifact_retention_summary_safe_fields"
                ]
            ),
            set(ARTIFACT_RETENTION_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(
                manifest["run_state_summary_contract"][
                    "fleet_safety_control_summary_safe_fields"
                ]
            ),
            set(FLEET_SAFETY_CONTROL_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(
                manifest["run_state_summary_contract"][
                    "approval_email_delivery_summary_safe_fields"
                ]
            ),
            set(APPROVAL_EMAIL_DELIVERY_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(
                manifest["run_state_summary_contract"][
                    "approval_runtime_rules_summary_safe_fields"
                ]
            ),
            set(APPROVAL_RUNTIME_RULES_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(
                manifest["run_state_summary_contract"][
                    "approval_delivery_handoff_summary_safe_fields"
                ]
            ),
            set(APPROVAL_DELIVERY_HANDOFF_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(
                manifest["run_state_summary_contract"][
                    "approval_safety_summary_safe_fields"
                ]
            ),
            set(APPROVAL_SAFETY_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(manifest["objective_contract_summary"].keys()),
            set(OBJECTIVE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(str(manifest["objective_contract_path"]).endswith("objective_contract.json"))
        self.assertEqual(
            set(manifest["completion_contract_summary"].keys()),
            set(COMPLETION_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(str(manifest["completion_contract_path"]).endswith("completion_contract.json"))
        self.assertEqual(
            set(manifest["approval_transport_summary"].keys()),
            set(APPROVAL_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(str(manifest["approval_transport_path"]).endswith("approval_transport.json"))
        self.assertEqual(
            set(manifest["reconcile_contract_summary"].keys()),
            set(RECONCILE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(str(manifest["reconcile_contract_path"]).endswith("reconcile_contract.json"))
        self.assertEqual(
            set(manifest["repair_suggestion_contract_summary"].keys()),
            set(REPAIR_SUGGESTION_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(
            str(manifest["repair_suggestion_contract_path"]).endswith(
                "repair_suggestion_contract.json"
            )
        )
        self.assertEqual(
            set(manifest["repair_plan_transport_summary"].keys()),
            set(REPAIR_PLAN_TRANSPORT_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(
            str(manifest["repair_plan_transport_path"]).endswith(
                "repair_plan_transport.json"
            )
        )
        self.assertEqual(
            set(manifest["repair_approval_binding_summary"].keys()),
            set(REPAIR_APPROVAL_BINDING_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(
            str(manifest["repair_approval_binding_path"]).endswith(
                "repair_approval_binding.json"
            )
        )
        self.assertEqual(
            set(manifest["execution_authorization_gate_summary"].keys()),
            set(EXECUTION_AUTHORIZATION_GATE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(
            str(manifest["execution_authorization_gate_path"]).endswith(
                "execution_authorization_gate.json"
            )
        )
        self.assertEqual(
            set(manifest["bounded_execution_bridge_summary"].keys()),
            set(BOUNDED_EXECUTION_BRIDGE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(
            str(manifest["bounded_execution_bridge_path"]).endswith(
                "bounded_execution_bridge.json"
            )
        )
        self.assertEqual(
            set(manifest["execution_result_contract_summary"].keys()),
            set(EXECUTION_RESULT_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(
            str(manifest["execution_result_contract_path"]).endswith(
                "execution_result_contract.json"
            )
        )
        self.assertEqual(
            set(manifest["verification_closure_contract_summary"].keys()),
            set(VERIFICATION_CLOSURE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(
            str(manifest["verification_closure_contract_path"]).endswith(
                "verification_closure_contract.json"
            )
        )
        self.assertEqual(
            set(manifest["retry_reentry_loop_contract_summary"].keys()),
            set(RETRY_REENTRY_LOOP_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(
            str(manifest["retry_reentry_loop_contract_path"]).endswith(
                "retry_reentry_loop_contract.json"
            )
        )
        self.assertEqual(
            set(manifest["endgame_closure_contract_summary"].keys()),
            set(ENDGAME_CLOSURE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(
            str(manifest["endgame_closure_contract_path"]).endswith(
                "endgame_closure_contract.json"
            )
        )
        self.assertEqual(
            set(manifest["lane_stabilization_contract_summary"].keys()),
            set(LANE_STABILIZATION_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(
            str(manifest["lane_stabilization_contract_path"]).endswith(
                "lane_stabilization_contract.json"
            )
        )
        self.assertEqual(
            set(manifest["observability_rollup_contract_summary"].keys()),
            set(OBSERVABILITY_ROLLUP_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(
            str(manifest["observability_rollup_contract_path"]).endswith(
                "observability_rollup_contract.json"
            )
        )
        self.assertEqual(
            set(manifest["failure_bucket_rollup_summary"].keys()),
            set(FAILURE_BUCKET_ROLLUP_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(
            str(manifest["failure_bucket_rollup_path"]).endswith("failure_bucket_rollup.json")
        )
        self.assertEqual(
            set(manifest["fleet_run_rollup_summary"].keys()),
            set(FLEET_RUN_ROLLUP_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(
            str(manifest["fleet_run_rollup_path"]).endswith("fleet_run_rollup.json")
        )
        self.assertEqual(
            set(manifest["failure_bucketing_hardening_contract_summary"].keys()),
            set(FAILURE_BUCKETING_HARDENING_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(
            str(manifest["failure_bucketing_hardening_contract_path"]).endswith(
                "failure_bucketing_hardening_contract.json"
            )
        )
        self.assertEqual(
            set(manifest["retention_manifest_summary"].keys()),
            set(RETENTION_MANIFEST_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(
            str(manifest["retention_manifest_path"]).endswith(
                "retention_manifest.json"
            )
        )
        self.assertEqual(
            set(manifest["artifact_retention_contract_summary"].keys()),
            set(ARTIFACT_RETENTION_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(
            str(manifest["artifact_retention_contract_path"]).endswith(
                "artifact_retention_contract.json"
            )
        )
        self.assertEqual(
            set(manifest["fleet_safety_control_contract_summary"].keys()),
            set(FLEET_SAFETY_CONTROL_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(
            str(manifest["fleet_safety_control_contract_path"]).endswith(
                "fleet_safety_control_contract.json"
            )
        )
        self.assertEqual(
            set(manifest["approval_email_delivery_contract_summary"].keys()),
            set(APPROVAL_EMAIL_DELIVERY_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(
            str(manifest["approval_email_delivery_contract_path"]).endswith(
                "approval_email_delivery_contract.json"
            )
        )
        self.assertEqual(
            set(manifest["approval_runtime_rules_contract_summary"].keys()),
            set(APPROVAL_RUNTIME_RULES_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(
            str(manifest["approval_runtime_rules_contract_path"]).endswith(
                "approval_runtime_rules_contract.json"
            )
        )
        self.assertEqual(
            set(manifest["approval_delivery_handoff_contract_summary"].keys()),
            set(APPROVAL_DELIVERY_HANDOFF_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(
            str(manifest["approval_delivery_handoff_contract_path"]).endswith(
                "approval_delivery_handoff_contract.json"
            )
        )
        self.assertEqual(
            set(manifest["approval_response_contract_summary"].keys()),
            set(APPROVAL_RESPONSE_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(
            str(manifest["approval_response_contract_path"]).endswith(
                "approval_response_contract.json"
            )
        )
        self.assertEqual(
            set(manifest["approved_restart_contract_summary"].keys()),
            set(APPROVED_RESTART_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(
            str(manifest["approved_restart_contract_path"]).endswith(
                "approved_restart_contract.json"
            )
        )
        self.assertEqual(
            set(manifest["approval_safety_contract_summary"].keys()),
            set(APPROVAL_SAFETY_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(
            str(manifest["approval_safety_contract_path"]).endswith(
                "approval_safety_contract.json"
            )
        )
        contract_artifact_index = manifest["contract_artifact_index"]
        self.assertEqual(list(contract_artifact_index.keys()), list(CONTRACT_ARTIFACT_ROLES))
        for role in CONTRACT_ARTIFACT_ROLES:
            self.assertIn("path", contract_artifact_index[role])
            self.assertIn("summary", contract_artifact_index[role])
            self.assertIsInstance(contract_artifact_index[role]["summary"], dict)
        objective_compact_fields = {
            key
            for key in manifest["run_state_summary_compact"]
            if (key.startswith("objective_") and key not in {"objective_satisfaction_status", "objective_satisfied"})
            or key == "requested_outcome"
        }
        self.assertEqual(
            objective_compact_fields,
            set(OBJECTIVE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        objective_run_state_fields = {
            key
            for key in manifest["run_state_summary"]
            if (key.startswith("objective_") and key not in {"objective_satisfaction_status", "objective_satisfied"})
            or key == "requested_outcome"
        }
        self.assertEqual(
            objective_run_state_fields,
            set(OBJECTIVE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        completion_compact_fields = {
            key
            for key in manifest["run_state_summary_compact"]
            if (key.startswith("completion_") and key not in {"completion_satisfaction_status", "completion_satisfied"})
            or key in {"done_status", "safe_closure_status"}
        }
        self.assertEqual(
            completion_compact_fields,
            set(COMPLETION_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        completion_run_state_fields = {
            key
            for key in manifest["run_state_summary"]
            if (key.startswith("completion_") and key not in {"completion_satisfaction_status", "completion_satisfied"})
            or key in {"done_status", "safe_closure_status"}
        }
        self.assertEqual(
            completion_run_state_fields,
            set(COMPLETION_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        approval_compact_fields = {
            key
            for key in manifest["run_state_summary_compact"]
            if (
                key.startswith("approval_")
                and key
                not in {
                    "approval_email_delivery_present",
                    "approval_runtime_rules_present",
                    "approval_delivery_handoff_present",
                    "approval_response_present",
                    "approved_restart_present",
                    "approval_safety_present",
                }
            )
            or key == "approved_action"
        }
        self.assertEqual(
            approval_compact_fields,
            set(APPROVAL_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        approval_run_state_fields = {
            key
            for key in manifest["run_state_summary"]
            if (
                key.startswith("approval_")
                and key
                not in {
                    "approval_email_delivery_present",
                    "approval_runtime_rules_present",
                    "approval_delivery_handoff_present",
                    "approval_response_present",
                    "approved_restart_present",
                    "approval_safety_present",
                }
            )
            or key == "approved_action"
        }
        self.assertEqual(
            approval_run_state_fields,
            set(APPROVAL_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        reconcile_compact_fields = {
            key
            for key in manifest["run_state_summary_compact"]
            if key.startswith("reconcile_")
        }
        self.assertEqual(
            reconcile_compact_fields,
            set(RECONCILE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        reconcile_run_state_fields = {
            key
            for key in manifest["run_state_summary"]
            if key.startswith("reconcile_")
        }
        self.assertEqual(
            reconcile_run_state_fields,
            set(RECONCILE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        repair_compact_fields = {
            key
            for key in manifest["run_state_summary_compact"]
            if key in set(REPAIR_SUGGESTION_RUN_STATE_SUMMARY_SAFE_FIELDS)
        }
        self.assertEqual(
            repair_compact_fields,
            set(REPAIR_SUGGESTION_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        repair_run_state_fields = {
            key
            for key in manifest["run_state_summary"]
            if key in set(REPAIR_SUGGESTION_RUN_STATE_SUMMARY_SAFE_FIELDS)
        }
        self.assertEqual(
            repair_run_state_fields,
            set(REPAIR_SUGGESTION_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        repair_plan_compact_fields = {
            key
            for key in manifest["run_state_summary_compact"]
            if key.startswith("repair_plan_")
        }
        self.assertEqual(
            repair_plan_compact_fields,
            set(REPAIR_PLAN_TRANSPORT_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        repair_plan_run_state_fields = {
            key
            for key in manifest["run_state_summary"]
            if key.startswith("repair_plan_")
        }
        self.assertEqual(
            repair_plan_run_state_fields,
            set(REPAIR_PLAN_TRANSPORT_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        execution_authorization_compact_fields = {
            key
            for key in manifest["run_state_summary_compact"]
            if key in set(EXECUTION_AUTHORIZATION_GATE_RUN_STATE_SUMMARY_SAFE_FIELDS)
        }
        self.assertEqual(
            execution_authorization_compact_fields,
            set(EXECUTION_AUTHORIZATION_GATE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        execution_authorization_run_state_fields = {
            key
            for key in manifest["run_state_summary"]
            if key in set(EXECUTION_AUTHORIZATION_GATE_RUN_STATE_SUMMARY_SAFE_FIELDS)
        }
        self.assertEqual(
            execution_authorization_run_state_fields,
            set(EXECUTION_AUTHORIZATION_GATE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        bounded_execution_compact_fields = {
            key
            for key in manifest["run_state_summary_compact"]
            if key in set(BOUNDED_EXECUTION_BRIDGE_RUN_STATE_SUMMARY_SAFE_FIELDS)
        }
        self.assertEqual(
            bounded_execution_compact_fields,
            set(BOUNDED_EXECUTION_BRIDGE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        bounded_execution_run_state_fields = {
            key
            for key in manifest["run_state_summary"]
            if key in set(BOUNDED_EXECUTION_BRIDGE_RUN_STATE_SUMMARY_SAFE_FIELDS)
        }
        self.assertEqual(
            bounded_execution_run_state_fields,
            set(BOUNDED_EXECUTION_BRIDGE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        endgame_compact_fields = {
            key
            for key in manifest["run_state_summary_compact"]
            if key in set(ENDGAME_CLOSURE_RUN_STATE_SUMMARY_SAFE_FIELDS)
        }
        self.assertEqual(
            endgame_compact_fields,
            set(ENDGAME_CLOSURE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        endgame_run_state_fields = {
            key
            for key in manifest["run_state_summary"]
            if key in set(ENDGAME_CLOSURE_RUN_STATE_SUMMARY_SAFE_FIELDS)
        }
        self.assertEqual(
            endgame_run_state_fields,
            set(ENDGAME_CLOSURE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )

    def test_stop_on_failure_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            transport = _RecordingDryRunTransport(
                status_by_pr_id={"project-planned-exec-pr-02": "failed"}
            )
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )

            decision_payload = json.loads(
                Path(manifest["next_action_path"]).read_text(encoding="utf-8")
            )

        self.assertEqual(manifest["run_status"], "failed")
        self.assertEqual(
            [entry["pr_id"] for entry in manifest["pr_units"]],
            [
                "project-planned-exec-pr-01",
                "project-planned-exec-pr-02",
            ],
        )
        self.assertIn(decision_payload["next_action"], {"same_prompt_retry", "escalate_to_human"})

    def test_dry_run_transport_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=_RecordingDryRunTransport()))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )
            first = manifest["pr_units"][0]
            result_payload = json.loads(Path(first["result_path"]).read_text(encoding="utf-8"))
            decision_payload = json.loads(
                Path(manifest["next_action_path"]).read_text(encoding="utf-8")
            )
            handoff_payload = json.loads(
                Path(manifest["action_handoff_path"]).read_text(encoding="utf-8")
            )

        self.assertEqual(result_payload["execution"]["status"], "not_started")
        self.assertEqual(result_payload["execution"]["verify"]["status"], "not_run")
        self.assertEqual(result_payload["failure_type"], "missing_signal")
        self.assertEqual(decision_payload["next_action"], "signal_recollect")
        self.assertEqual(handoff_payload["next_action"], "signal_recollect")
        self.assertFalse(decision_payload["next_action"] in {"proceed_to_pr", "proceed_to_merge"})

    def test_live_transport_path_integrates_with_controller(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            transport = _RecordingLiveTransport()
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
            )

            decision_payload = json.loads(
                Path(manifest["next_action_path"]).read_text(encoding="utf-8")
            )
            first = manifest["pr_units"][0]
            result_payload = json.loads(Path(first["result_path"]).read_text(encoding="utf-8"))
            handoff_payload = json.loads(
                Path(manifest["action_handoff_path"]).read_text(encoding="utf-8")
            )
            commit_decision = json.loads((Path(first["compiled_prompt_path"]).parent / "commit_decision.json").read_text(encoding="utf-8"))
            merge_decision = json.loads((Path(first["compiled_prompt_path"]).parent / "merge_decision.json").read_text(encoding="utf-8"))

        self.assertEqual(manifest["run_status"], "completed")
        self.assertEqual(result_payload["execution"]["status"], "completed")
        self.assertEqual(result_payload["execution"]["verify"]["status"], "passed")
        self.assertEqual(decision_payload["next_action"], "proceed_to_pr")
        self.assertEqual(handoff_payload["next_action"], "proceed_to_pr")
        self.assertTrue(handoff_payload["action_consumable"])
        self.assertFalse(decision_payload["whether_human_required"])
        self.assertEqual(manifest["progression_summary"]["final_unit_state"], "advanced")
        self.assertEqual(commit_decision["readiness_status"], "ready")
        self.assertEqual(commit_decision["readiness_next_action"], "prepare_commit")
        self.assertTrue(commit_decision["automation_eligible"])
        self.assertTrue(commit_decision["prerequisites_satisfied"])
        self.assertEqual(merge_decision["readiness_status"], "awaiting_prerequisites")
        self.assertEqual(merge_decision["readiness_next_action"], "resolve_blockers")
        self.assertFalse(merge_decision["automation_eligible"])

    def test_checkpoint_decision_maps_progression_to_commit_evaluation_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            transport = _RecordingLiveTransport()
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
            )

            first = manifest["pr_units"][0]
            checkpoint_payload = json.loads(
                Path(first["checkpoint_decision_path"]).read_text(encoding="utf-8")
            )
            run_state_payload = json.loads(Path(manifest["run_state_path"]).read_text(encoding="utf-8"))
            first = manifest["pr_units"][0]
            commit_decision = json.loads(
                (Path(first["compiled_prompt_path"]).parent / "commit_decision.json").read_text(
                    encoding="utf-8"
                )
            )
            merge_decision = json.loads(
                (Path(first["compiled_prompt_path"]).parent / "merge_decision.json").read_text(
                    encoding="utf-8"
                )
            )
            first = manifest["pr_units"][0]
            commit_decision = json.loads((Path(first["compiled_prompt_path"]).parent / "commit_decision.json").read_text(encoding="utf-8"))
            merge_decision = json.loads((Path(first["compiled_prompt_path"]).parent / "merge_decision.json").read_text(encoding="utf-8"))
            first = manifest["pr_units"][0]
            commit_decision = json.loads((Path(first["compiled_prompt_path"]).parent / "commit_decision.json").read_text(encoding="utf-8"))
            merge_decision = json.loads((Path(first["compiled_prompt_path"]).parent / "merge_decision.json").read_text(encoding="utf-8"))

        self.assertEqual(checkpoint_payload["decision"], "commit_evaluation_ready")
        self.assertEqual(checkpoint_payload["checkpoint_stage"], "pre_commit_evaluation")
        self.assertFalse(checkpoint_payload["manual_intervention_required"])
        self.assertFalse(checkpoint_payload["global_stop_recommended"])
        self.assertTrue(run_state_payload["continue_allowed"])
        self.assertEqual(run_state_payload["orchestration_state"], "run_ready_to_continue")
        self.assertEqual(run_state_payload["next_run_action"], "continue_run")
        self.assertFalse(run_state_payload["run_paused"])
        self.assertFalse(run_state_payload["rollback_evaluation_pending"])
        self.assertEqual(run_state_payload["readiness_summary"]["commit"]["ready"], 3)
        self.assertEqual(
            run_state_payload["readiness_summary"]["merge"]["awaiting_prerequisites"],
            3,
        )
        self.assertFalse(run_state_payload["readiness_blocked"])
        self.assertFalse(run_state_payload["readiness_manual_required"])
        self.assertTrue(run_state_payload["readiness_awaiting_prerequisites"])

    def test_run_state_orchestration_global_stop_pending_when_manual_gate_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            transport = _RecordingLiveTransport(verify_status_by_pr_id={"project-planned-exec-pr-01": "failed"})
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
                retry_context={
                    "prior_attempt_count": 0,
                    "prior_retry_class": None,
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 0,
                },
            )
            run_state_payload = json.loads(Path(manifest["run_state_path"]).read_text(encoding="utf-8"))
            first = manifest["pr_units"][0]
            commit_decision = json.loads(
                (Path(first["compiled_prompt_path"]).parent / "commit_decision.json").read_text(
                    encoding="utf-8"
                )
            )
            merge_decision = json.loads(
                (Path(first["compiled_prompt_path"]).parent / "merge_decision.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(run_state_payload["state"], "paused")
        self.assertEqual(run_state_payload["orchestration_state"], "global_stop_pending")
        self.assertEqual(run_state_payload["next_run_action"], "hold_for_global_stop")
        self.assertFalse(run_state_payload["continue_allowed"])
        self.assertTrue(run_state_payload["run_paused"])
        self.assertTrue(run_state_payload["manual_intervention_required"])
        self.assertTrue(run_state_payload["global_stop_recommended"])
        self.assertEqual(commit_decision["readiness_status"], "manual_required")
        self.assertFalse(commit_decision["automation_eligible"])
        self.assertTrue(commit_decision["manual_intervention_required"])
        self.assertEqual(merge_decision["readiness_status"], "manual_required")
        self.assertFalse(merge_decision["automation_eligible"])

    def test_run_state_orchestration_rollback_evaluation_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            transport = _RollbackSignalLiveTransport()
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
                retry_context={
                    "prior_attempt_count": 0,
                    "prior_retry_class": None,
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 2,
                },
            )
            run_state_payload = json.loads(Path(manifest["run_state_path"]).read_text(encoding="utf-8"))
            first = manifest["pr_units"][0]
            rollback_decision = json.loads((Path(first["compiled_prompt_path"]).parent / "rollback_decision.json").read_text(encoding="utf-8"))

        self.assertTrue(run_state_payload["rollback_evaluation_pending"])
        self.assertEqual(run_state_payload["orchestration_state"], "rollback_evaluation_pending")
        self.assertEqual(run_state_payload["next_run_action"], "evaluate_rollback")
        self.assertFalse(run_state_payload["continue_allowed"])
        self.assertTrue(run_state_payload["run_paused"])
        self.assertEqual(rollback_decision["decision"], "required")
        self.assertEqual(rollback_decision["readiness_status"], "awaiting_prerequisites")
        self.assertEqual(rollback_decision["readiness_next_action"], "resolve_blockers")
        self.assertFalse(rollback_decision["automation_eligible"])
        self.assertTrue(rollback_decision["prerequisites_satisfied"])

    def test_closed_loop_next_action_prefers_commit_when_commit_ready_and_not_executed(self) -> None:
        run_state = {
            "continue_allowed": True,
            "run_paused": False,
            "manual_intervention_required": False,
            "rollback_evaluation_pending": False,
            "global_stop_recommended": False,
            "global_stop": False,
            "merge_execution_succeeded": False,
            "rollback_execution_succeeded": False,
            "rollback_execution_failed": False,
            "rollback_replan_required": False,
            "rollback_automatic_continuation_blocked": False,
            "units_pending": 0,
        }
        manifest_units = [
            {
                "decision_summary": {
                    "commit_readiness_status": "ready",
                    "commit_execution_status": "blocked",
                },
                "commit_execution_summary": {"status": "blocked"},
            }
        ]

        augmented = _augment_run_state_with_closed_loop(
            run_state_payload=run_state,
            manifest_units=manifest_units,
            run_status="completed",
        )

        self.assertEqual(augmented["loop_state"], "delivery_in_progress")
        self.assertEqual(augmented["next_safe_action"], "execute_commit")
        self.assertTrue(augmented["resumable"])
        self.assertFalse(augmented["terminal"])

    def test_closed_loop_next_action_blocks_on_manual_and_global_stop(self) -> None:
        run_state = {
            "continue_allowed": False,
            "run_paused": True,
            "manual_intervention_required": True,
            "rollback_evaluation_pending": False,
            "global_stop_recommended": True,
            "global_stop": True,
            "merge_execution_succeeded": False,
            "rollback_execution_succeeded": False,
            "rollback_execution_failed": False,
            "rollback_replan_required": False,
            "rollback_automatic_continuation_blocked": False,
            "units_pending": 0,
        }

        augmented = _augment_run_state_with_closed_loop(
            run_state_payload=run_state,
            manifest_units=[
                {
                    "decision_summary": {
                        "merge_readiness_status": "ready",
                        "merge_execution_status": "succeeded",
                        "pr_execution_status": "succeeded",
                        "push_execution_status": "succeeded",
                        "commit_execution_status": "succeeded",
                    }
                }
            ],
            run_status="completed",
        )

        self.assertEqual(augmented["loop_state"], "manual_intervention_required")
        self.assertEqual(augmented["next_safe_action"], "require_manual_intervention")
        self.assertTrue(augmented["loop_manual_intervention_required"])
        self.assertFalse(augmented["terminal"])

    def test_closed_loop_next_action_requires_replan_after_rollback(self) -> None:
        run_state = {
            "continue_allowed": False,
            "run_paused": True,
            "manual_intervention_required": False,
            "rollback_evaluation_pending": False,
            "global_stop_recommended": False,
            "global_stop": False,
            "merge_execution_succeeded": False,
            "rollback_execution_succeeded": True,
            "rollback_execution_failed": False,
            "rollback_replan_required": True,
            "rollback_automatic_continuation_blocked": True,
            "units_pending": 0,
        }

        augmented = _augment_run_state_with_closed_loop(
            run_state_payload=run_state,
            manifest_units=[
                {
                    "decision_summary": {
                        "merge_readiness_status": "ready",
                        "merge_execution_status": "succeeded",
                        "pr_execution_status": "succeeded",
                        "push_execution_status": "succeeded",
                        "commit_execution_status": "succeeded",
                    }
                }
            ],
            run_status="completed",
        )

        self.assertEqual(augmented["loop_state"], "replan_required")
        self.assertEqual(augmented["next_safe_action"], "require_replanning")
        self.assertTrue(augmented["loop_replan_required"])
        self.assertFalse(augmented["terminal"])

    def test_closed_loop_next_action_terminal_success_only_after_delivery_completion(self) -> None:
        run_state = {
            "continue_allowed": False,
            "run_paused": False,
            "manual_intervention_required": False,
            "rollback_evaluation_pending": False,
            "global_stop_recommended": False,
            "global_stop": False,
            "merge_execution_succeeded": True,
            "rollback_execution_succeeded": False,
            "rollback_execution_failed": False,
            "rollback_replan_required": False,
            "rollback_automatic_continuation_blocked": False,
            "units_pending": 0,
        }

        augmented = _augment_run_state_with_closed_loop(
            run_state_payload=run_state,
            manifest_units=[
                {
                    "decision_summary": {
                        "merge_readiness_status": "ready",
                        "merge_execution_status": "succeeded",
                        "pr_execution_status": "succeeded",
                        "push_execution_status": "succeeded",
                        "commit_execution_status": "succeeded",
                    }
                }
            ],
            run_status="completed",
        )

        self.assertEqual(augmented["loop_state"], "terminal_success")
        self.assertEqual(augmented["next_safe_action"], "stop_terminal_success")
        self.assertTrue(augmented["terminal"])
        self.assertFalse(augmented["resumable"])

    def test_closed_loop_next_action_blocks_ambiguous_lifecycle_evidence(self) -> None:
        run_state = {
            "continue_allowed": True,
            "run_paused": False,
            "manual_intervention_required": False,
            "rollback_evaluation_pending": True,
            "next_run_action": "evaluate_rollback",
            "global_stop_recommended": False,
            "global_stop": False,
            "merge_execution_succeeded": False,
            "rollback_execution_succeeded": False,
            "rollback_execution_failed": False,
            "rollback_replan_required": False,
            "rollback_automatic_continuation_blocked": False,
            "units_pending": 0,
        }
        manifest_units = [
            {
                "decision_summary": {
                    "rollback_readiness_status": "awaiting_prerequisites",
                    "rollback_execution_status": "blocked",
                },
                "rollback_execution_summary": {"status": "blocked"},
            }
        ]

        augmented = _augment_run_state_with_closed_loop(
            run_state_payload=run_state,
            manifest_units=manifest_units,
            run_status="completed",
        )

        self.assertEqual(augmented["loop_state"], "runnable_blocked")
        self.assertEqual(augmented["next_safe_action"], "pause")
        self.assertEqual(augmented["loop_blocked_reason"], "rollback_pending_without_ready_unit")
        self.assertTrue(augmented["loop_manual_intervention_required"])

    def test_commit_execution_succeeds_when_readiness_and_run_state_allow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            changed_file = self._shrink_to_single_pr_slice(artifacts_dir)
            out_dir = root / "artifacts" / "executions"
            repo_dir = root / "execution_repo"
            repo_dir.mkdir(parents=True, exist_ok=True)
            head_before = self._init_git_repo_with_dirty_file(repo_dir, changed_file=changed_file)

            transport = _CommitReadyLiveTransport(
                changed_files_by_pr_id={"project-planned-exec-pr-01": [changed_file]}
            )
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
                execution_repo_path=repo_dir,
            )
            first = manifest["pr_units"][0]
            commit_execution = json.loads(
                Path(first["commit_execution_path"]).read_text(encoding="utf-8")
            )
            run_state_payload = json.loads(Path(manifest["run_state_path"]).read_text(encoding="utf-8"))
            progression = json.loads(Path(first["unit_progression_path"]).read_text(encoding="utf-8"))
            head_after = subprocess.run(
                ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

        self.assertEqual(commit_execution["status"], "succeeded")
        self.assertTrue(commit_execution["attempted"])
        self.assertTrue(commit_execution["commit_sha"])
        self.assertFalse(commit_execution["manual_intervention_required"])
        self.assertTrue(commit_execution["execution_allowed"])
        self.assertEqual(commit_execution["execution_authority_status"], "allowed")
        self.assertEqual(commit_execution["validation_status"], "passed")
        self.assertFalse(commit_execution["manual_approval_required"])
        self.assertNotEqual(head_before, head_after)
        self.assertTrue(run_state_payload["commit_execution_executed"])
        self.assertFalse(run_state_payload["commit_execution_failed"])
        states = [entry["state"] for entry in progression["checkpoints"]]
        self.assertIn("commit_execution_started", states)
        self.assertIn("commit_executed", states)
        self.assertNotIn("commit_execution_failed", states)

    def test_commit_execution_is_blocked_when_repo_path_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            changed_file = self._shrink_to_single_pr_slice(artifacts_dir)
            out_dir = root / "artifacts" / "executions"
            transport = _CommitReadyLiveTransport(
                changed_files_by_pr_id={"project-planned-exec-pr-01": [changed_file]}
            )
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
            )
            first = manifest["pr_units"][0]
            commit_execution = json.loads(
                Path(first["commit_execution_path"]).read_text(encoding="utf-8")
            )
            run_state_payload = json.loads(Path(manifest["run_state_path"]).read_text(encoding="utf-8"))
            progression = json.loads(Path(first["unit_progression_path"]).read_text(encoding="utf-8"))

        self.assertEqual(commit_execution["status"], "blocked")
        self.assertFalse(commit_execution["attempted"])
        self.assertIn("execution_repo_path_missing", commit_execution["blocking_reasons"])
        self.assertFalse(commit_execution["execution_allowed"])
        self.assertEqual(commit_execution["execution_authority_status"], "allowed")
        self.assertEqual(commit_execution["validation_status"], "blocked")
        self.assertTrue(commit_execution["manual_approval_required"])
        self.assertTrue(run_state_payload["commit_execution_pending"])
        self.assertFalse(run_state_payload["commit_execution_executed"])
        states = [entry["state"] for entry in progression["checkpoints"]]
        self.assertNotIn("commit_execution_started", states)

    def test_commit_execution_blocked_when_worktree_has_unscoped_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            changed_file = self._shrink_to_single_pr_slice(artifacts_dir)
            out_dir = root / "artifacts" / "executions"
            repo_dir = root / "execution_repo"
            repo_dir.mkdir(parents=True, exist_ok=True)
            self._init_git_repo_with_dirty_file(repo_dir, changed_file=changed_file)
            unscoped_file = repo_dir / "README.md"
            unscoped_file.write_text("unexpected change\n", encoding="utf-8")

            transport = _CommitReadyLiveTransport(
                changed_files_by_pr_id={"project-planned-exec-pr-01": [changed_file]}
            )
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
                execution_repo_path=repo_dir,
            )
            first = manifest["pr_units"][0]
            commit_execution = json.loads(
                Path(first["commit_execution_path"]).read_text(encoding="utf-8")
            )

        self.assertEqual(commit_execution["status"], "blocked")
        self.assertEqual(
            commit_execution["failure_reason"],
            "working_tree_contains_out_of_scope_changes",
        )
        self.assertIn(
            "working_tree_contains_out_of_scope_changes",
            commit_execution["unsafe_repo_state"],
        )
        self.assertFalse(commit_execution["execution_allowed"])
        self.assertEqual(commit_execution["validation_status"], "blocked")
        self.assertTrue(commit_execution["manual_approval_required"])

    def test_commit_execution_failure_persists_receipt_and_progression(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            changed_file = self._shrink_to_single_pr_slice(artifacts_dir)
            out_dir = root / "artifacts" / "executions"
            repo_dir = root / "execution_repo"
            repo_dir.mkdir(parents=True, exist_ok=True)
            head_before = self._init_git_repo_with_dirty_file(repo_dir, changed_file=changed_file)

            hooks_dir = root / "hooks"
            hooks_dir.mkdir(parents=True, exist_ok=True)
            pre_commit = hooks_dir / "pre-commit"
            pre_commit.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            pre_commit.chmod(0o755)
            subprocess.run(
                ["git", "-C", str(repo_dir), "config", "core.hooksPath", str(hooks_dir)],
                check=True,
                capture_output=True,
                text=True,
            )

            transport = _CommitReadyLiveTransport(
                changed_files_by_pr_id={"project-planned-exec-pr-01": [changed_file]}
            )
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
                execution_repo_path=repo_dir,
            )
            first = manifest["pr_units"][0]
            commit_execution = json.loads(
                Path(first["commit_execution_path"]).read_text(encoding="utf-8")
            )
            run_state_payload = json.loads(Path(manifest["run_state_path"]).read_text(encoding="utf-8"))
            progression = json.loads(Path(first["unit_progression_path"]).read_text(encoding="utf-8"))
            head_after = subprocess.run(
                ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

        self.assertEqual(commit_execution["status"], "failed")
        self.assertTrue(commit_execution["attempted"])
        self.assertEqual(commit_execution["failure_reason"], "git_commit_failed")
        self.assertTrue(commit_execution["manual_intervention_required"])
        self.assertTrue(commit_execution["execution_allowed"])
        self.assertEqual(commit_execution["execution_authority_status"], "allowed")
        self.assertEqual(commit_execution["validation_status"], "passed")
        self.assertEqual(head_before, head_after)
        self.assertTrue(run_state_payload["commit_execution_failed"])
        self.assertTrue(run_state_payload["commit_execution_manual_intervention_required"])
        states = [entry["state"] for entry in progression["checkpoints"]]
        self.assertIn("commit_execution_started", states)
        self.assertIn("commit_execution_failed", states)

    def test_push_pr_merge_execute_when_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            changed_file = self._shrink_to_single_pr_slice(artifacts_dir)
            out_dir = root / "artifacts" / "executions"
            repo_dir = root / "execution_repo"
            repo_dir.mkdir(parents=True, exist_ok=True)
            self._init_git_repo_with_dirty_file(repo_dir, changed_file=changed_file)
            self._attach_origin_remote_and_push_initial(repo_dir)

            transport = _CommitReadyLiveTransport(
                changed_files_by_pr_id={"project-planned-exec-pr-01": [changed_file]}
            )
            read_backend = _FakeGitHubReadBackend(lookup_status="success", matched=False)
            write_backend = _FakeGitHubWriteBackend(create_status="success", merge_status="success")
            runner = PlannedExecutionRunner(
                adapter=CodexExecutorAdapter(transport=transport),
                github_read_backend=read_backend,
                github_write_backend=write_backend,
            )
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
                execution_repo_path=repo_dir,
            )
            first = manifest["pr_units"][0]
            push_execution = json.loads(Path(first["push_execution_path"]).read_text(encoding="utf-8"))
            pr_execution = json.loads(Path(first["pr_execution_path"]).read_text(encoding="utf-8"))
            merge_execution = json.loads(Path(first["merge_execution_path"]).read_text(encoding="utf-8"))
            run_state_payload = json.loads(
                Path(manifest["run_state_path"]).read_text(encoding="utf-8")
            )
            run_state_payload = json.loads(
                Path(manifest["run_state_path"]).read_text(encoding="utf-8")
            )
            run_state_payload = json.loads(
                Path(manifest["run_state_path"]).read_text(encoding="utf-8")
            )
            run_state_payload = json.loads(Path(manifest["run_state_path"]).read_text(encoding="utf-8"))
            merge_decision = json.loads(Path(first["merge_decision_path"]).read_text(encoding="utf-8"))
            progression = json.loads(Path(first["unit_progression_path"]).read_text(encoding="utf-8"))
            run_state_payload = json.loads(Path(manifest["run_state_path"]).read_text(encoding="utf-8"))

        self.assertEqual(push_execution["status"], "succeeded")
        self.assertEqual(pr_execution["status"], "succeeded")
        self.assertEqual(merge_execution["status"], "succeeded")
        self.assertEqual(push_execution["remote_state_status"], "ready")
        self.assertEqual(pr_execution["pr_creation_state_status"], "created")
        self.assertEqual(merge_execution["mergeability_status"], "clean")
        self.assertEqual(merge_execution["merge_requirements_status"], "satisfied")
        self.assertTrue(push_execution["execution_allowed"])
        self.assertTrue(pr_execution["execution_allowed"])
        self.assertTrue(merge_execution["execution_allowed"])
        self.assertEqual(push_execution["execution_authority_status"], "allowed")
        self.assertEqual(pr_execution["execution_authority_status"], "allowed")
        self.assertEqual(merge_execution["execution_authority_status"], "allowed")
        self.assertEqual(merge_decision["decision"], "allowed")
        self.assertEqual(merge_decision["readiness_status"], "ready")
        self.assertEqual(merge_decision["readiness_next_action"], "prepare_merge")
        self.assertTrue(merge_decision["automation_eligible"])
        self.assertTrue(run_state_payload["push_execution_succeeded"])
        self.assertTrue(run_state_payload["pr_execution_succeeded"])
        self.assertTrue(run_state_payload["merge_execution_succeeded"])
        self.assertFalse(run_state_payload["push_execution_failed"])
        self.assertFalse(run_state_payload["pr_execution_failed"])
        self.assertFalse(run_state_payload["merge_execution_failed"])
        states = [entry["state"] for entry in progression["checkpoints"]]
        self.assertIn("push_execution_started", states)
        self.assertIn("push_executed", states)
        self.assertIn("pr_creation_started", states)
        self.assertIn("pr_created", states)
        self.assertIn("merge_execution_started", states)
        self.assertIn("merge_executed", states)
        self.assertEqual(len(write_backend.create_calls), 1)
        self.assertEqual(len(write_backend.merge_calls), 1)

    def test_push_is_blocked_when_commit_execution_not_succeeded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            changed_file = self._shrink_to_single_pr_slice(artifacts_dir)
            out_dir = root / "artifacts" / "executions"
            transport = _CommitReadyLiveTransport(
                changed_files_by_pr_id={"project-planned-exec-pr-01": [changed_file]}
            )
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
            )
            first = manifest["pr_units"][0]
            commit_execution = json.loads(Path(first["commit_execution_path"]).read_text(encoding="utf-8"))
            push_execution = json.loads(Path(first["push_execution_path"]).read_text(encoding="utf-8"))
            pr_execution = json.loads(Path(first["pr_execution_path"]).read_text(encoding="utf-8"))
            merge_execution = json.loads(Path(first["merge_execution_path"]).read_text(encoding="utf-8"))

        self.assertEqual(commit_execution["status"], "blocked")
        self.assertEqual(push_execution["status"], "blocked")
        self.assertIn("commit_execution_not_succeeded", push_execution["blocking_reasons"])
        self.assertFalse(push_execution["execution_allowed"])
        self.assertEqual(push_execution["validation_status"], "blocked")
        self.assertEqual(pr_execution["status"], "blocked")
        self.assertEqual(merge_execution["status"], "blocked")

    def test_pr_creation_blocks_when_github_truth_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            changed_file = self._shrink_to_single_pr_slice(artifacts_dir)
            out_dir = root / "artifacts" / "executions"
            repo_dir = root / "execution_repo"
            repo_dir.mkdir(parents=True, exist_ok=True)
            self._init_git_repo_with_dirty_file(repo_dir, changed_file=changed_file)
            self._attach_origin_remote_and_push_initial(repo_dir)

            transport = _CommitReadyLiveTransport(
                changed_files_by_pr_id={"project-planned-exec-pr-01": [changed_file]}
            )
            read_backend = _FakeGitHubReadBackend(lookup_status="api_failure", matched=False)
            write_backend = _FakeGitHubWriteBackend(create_status="success", merge_status="success")
            runner = PlannedExecutionRunner(
                adapter=CodexExecutorAdapter(transport=transport),
                github_read_backend=read_backend,
                github_write_backend=write_backend,
            )
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
                execution_repo_path=repo_dir,
            )
            first = manifest["pr_units"][0]
            push_execution = json.loads(Path(first["push_execution_path"]).read_text(encoding="utf-8"))
            pr_execution = json.loads(Path(first["pr_execution_path"]).read_text(encoding="utf-8"))
            merge_execution = json.loads(Path(first["merge_execution_path"]).read_text(encoding="utf-8"))
            run_state_payload = json.loads(
                Path(manifest["run_state_path"]).read_text(encoding="utf-8")
            )

        self.assertEqual(push_execution["status"], "succeeded")
        self.assertEqual(pr_execution["status"], "blocked")
        self.assertEqual(pr_execution["failure_reason"], "open_pr_lookup_api_failure")
        self.assertTrue(pr_execution["manual_intervention_required"])
        self.assertFalse(pr_execution["execution_allowed"])
        self.assertEqual(pr_execution["validation_status"], "passed")
        self.assertTrue(pr_execution["remote_state_missing_or_ambiguous"])
        self.assertIn("open_pr_lookup_api_failure", pr_execution["remote_pr_ambiguity"])
        self.assertTrue(pr_execution["remote_github_blocked"])
        self.assertEqual(merge_execution["status"], "blocked")
        self.assertTrue(run_state_payload["remote_github_blocked"])
        self.assertTrue(run_state_payload["remote_github_manual_required"])
        self.assertTrue(run_state_payload["remote_github_missing_or_ambiguous"])
        self.assertIn("open_pr_lookup_api_failure", run_state_payload["remote_github_blocked_reasons"])
        self.assertEqual(len(write_backend.create_calls), 0)
        self.assertEqual(len(write_backend.merge_calls), 0)

    def test_push_blocked_when_remote_state_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_dir = Path(tmp_dir) / "repo"
            repo_dir.mkdir(parents=True, exist_ok=True)
            changed_file = "automation/planning/prompt_compiler.py"
            self._init_git_repo_with_dirty_file(repo_dir, changed_file=changed_file)
            subprocess.run(
                ["git", "-C", str(repo_dir), "add", "--", changed_file],
                check=True,
                capture_output=True,
                text=True,
            )
            commit_sha = self._git_commit(repo_dir, "bounded commit")
            payload = _execute_bounded_push(
                unit_id="pr-push-no-remote",
                repo_path=str(repo_dir),
                remote_name="origin",
                configured_head_branch="feature/test",
                base_branch="main",
                run_state_payload={
                    "continue_allowed": True,
                    "run_paused": False,
                    "manual_intervention_required": False,
                    "global_stop_recommended": False,
                    "global_stop": False,
                    "rollback_evaluation_pending": False,
                },
                commit_execution_payload={"status": "succeeded", "commit_sha": commit_sha},
                dry_run=False,
                now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
            )

        self.assertEqual(payload["status"], "blocked")
        self.assertIn("git_remote_missing", payload["blocking_reasons"])
        self.assertFalse(payload["execution_allowed"])
        self.assertEqual(payload["validation_status"], "passed")
        self.assertIn("git_remote_missing", payload["missing_required_refs"])
        self.assertTrue(payload["remote_state_blocked"])
        self.assertTrue(payload["remote_github_blocked"])

    def test_push_blocked_due_remote_divergence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_dir = Path(tmp_dir) / "repo"
            repo_dir.mkdir(parents=True, exist_ok=True)
            changed_file = "automation/planning/prompt_compiler.py"
            self._init_git_repo_with_dirty_file(repo_dir, changed_file=changed_file)
            remote_dir = self._attach_origin_remote_and_push_initial(repo_dir)
            branch_name = subprocess.run(
                ["git", "-C", str(repo_dir), "rev-parse", "--abbrev-ref", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

            peer_dir = Path(tmp_dir) / "peer"
            subprocess.run(["git", "clone", str(remote_dir), str(peer_dir)], check=True, capture_output=True, text=True)
            subprocess.run(
                ["git", "-C", str(peer_dir), "config", "user.name", "Peer Runner"],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "-C", str(peer_dir), "config", "user.email", "peer@example.com"],
                check=True,
                capture_output=True,
                text=True,
            )
            peer_target = peer_dir / changed_file
            peer_target.parent.mkdir(parents=True, exist_ok=True)
            peer_target.write_text("baseline\npeer\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(peer_dir), "add", "--", changed_file], check=True, capture_output=True, text=True)
            self._git_commit(peer_dir, "peer update")
            subprocess.run(
                ["git", "-C", str(peer_dir), "push", "origin", f"HEAD:{branch_name}"],
                check=True,
                capture_output=True,
                text=True,
            )

            commit_sha = subprocess.run(
                ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            payload = _execute_bounded_push(
                unit_id="pr-push-diverged",
                repo_path=str(repo_dir),
                remote_name="origin",
                configured_head_branch=branch_name,
                base_branch="main",
                run_state_payload={
                    "continue_allowed": True,
                    "run_paused": False,
                    "manual_intervention_required": False,
                    "global_stop_recommended": False,
                    "global_stop": False,
                    "rollback_evaluation_pending": False,
                },
                commit_execution_payload={"status": "succeeded", "commit_sha": commit_sha},
                dry_run=False,
                now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
            )

        self.assertEqual(payload["status"], "blocked")
        self.assertIn("remote_non_fast_forward_risk", payload["blocking_reasons"])
        self.assertFalse(payload["execution_allowed"])
        self.assertEqual(payload["validation_status"], "passed")
        self.assertEqual(payload["remote_state_status"], "non_fast_forward_risk")
        self.assertEqual(payload["upstream_tracking_status"], "tracked")
        self.assertEqual(payload["remote_divergence_status"], "non_fast_forward_risk")
        self.assertTrue(payload["remote_state_blocked"])

    def test_push_blocked_when_upstream_tracking_is_ambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_dir = Path(tmp_dir) / "repo"
            repo_dir.mkdir(parents=True, exist_ok=True)
            changed_file = "automation/planning/prompt_compiler.py"
            self._init_git_repo_with_dirty_file(repo_dir, changed_file=changed_file)
            remote_dir = Path(tmp_dir) / "origin.git"
            subprocess.run(["git", "init", "--bare", str(remote_dir)], check=True, capture_output=True, text=True)
            subprocess.run(
                ["git", "-C", str(repo_dir), "remote", "add", "origin", str(remote_dir)],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "-C", str(repo_dir), "push", "origin", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            )
            commit_sha = subprocess.run(
                ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            payload = _execute_bounded_push(
                unit_id="pr-push-upstream-ambiguous",
                repo_path=str(repo_dir),
                remote_name="origin",
                configured_head_branch="feature/test",
                base_branch="main",
                run_state_payload={
                    "continue_allowed": True,
                    "run_paused": False,
                    "manual_intervention_required": False,
                    "global_stop_recommended": False,
                    "global_stop": False,
                    "rollback_evaluation_pending": False,
                },
                commit_execution_payload={"status": "succeeded", "commit_sha": commit_sha},
                dry_run=False,
                now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
            )

        self.assertEqual(payload["status"], "blocked")
        self.assertIn("upstream_tracking_unresolved", payload["blocking_reasons"])
        self.assertEqual(payload["remote_state_status"], "ambiguous")
        self.assertTrue(payload["remote_state_missing_or_ambiguous"])
        self.assertEqual(payload["validation_status"], "passed")

    def test_pr_creation_blocked_when_existing_matching_pr_exists(self) -> None:
        payload = _execute_bounded_pr_creation(
            unit_id="pr-create-existing",
            job_id="job-1",
            repository="owner/repo",
            base_branch="main",
            run_state_payload={
                "continue_allowed": True,
                "run_paused": False,
                "manual_intervention_required": False,
                "global_stop_recommended": False,
                "global_stop": False,
                "rollback_evaluation_pending": False,
            },
            merge_decision_payload={
                "manual_intervention_required": False,
                "unresolved_blockers": [],
            },
            commit_execution_payload={"status": "succeeded", "commit_sha": "a" * 40},
            push_execution_payload={
                "status": "succeeded",
                "branch_name": "feature/test",
                "remote_name": "origin",
                "head_branch": "feature/test",
            },
            read_backend=_FakeGitHubReadBackend(
                lookup_status="success",
                matched=True,
                match_count=1,
                pr_number=77,
                pr_url="https://example.local/pr/77",
            ),
            write_backend=_FakeGitHubWriteBackend(),
            now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
        )
        payload = dict(payload)

        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["failure_reason"], "existing_open_pr_detected")
        self.assertEqual(payload["existing_pr_status"], "existing_open")
        self.assertEqual(payload["pr_creation_state_status"], "blocked_existing_pr")
        self.assertEqual(payload["pr_duplication_risk"], "detected")
        self.assertTrue(payload["remote_state_blocked"])
        self.assertEqual(payload["validation_status"], "passed")

    def test_pr_creation_blocked_when_existing_pr_lookup_is_ambiguous(self) -> None:
        payload = _execute_bounded_pr_creation(
            unit_id="pr-create-existing-ambiguous",
            job_id="job-1",
            repository="owner/repo",
            base_branch="main",
            run_state_payload={
                "continue_allowed": True,
                "run_paused": False,
                "manual_intervention_required": False,
                "global_stop_recommended": False,
                "global_stop": False,
                "rollback_evaluation_pending": False,
            },
            merge_decision_payload={
                "manual_intervention_required": False,
                "unresolved_blockers": [],
            },
            commit_execution_payload={"status": "succeeded", "commit_sha": "a" * 40},
            push_execution_payload={
                "status": "succeeded",
                "branch_name": "feature/test",
                "remote_name": "origin",
                "head_branch": "feature/test",
            },
            read_backend=_FakeGitHubReadBackend(
                lookup_status="success",
                matched=True,
                match_count=2,
                pr_number=88,
                pr_url="https://example.local/pr/88",
            ),
            write_backend=_FakeGitHubWriteBackend(),
            now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
        )
        payload = dict(payload)

        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["failure_reason"], "existing_pr_lookup_ambiguous")
        self.assertTrue(payload["remote_state_missing_or_ambiguous"])
        self.assertEqual(payload["validation_status"], "passed")

    def test_pr_creation_blocked_when_base_or_head_is_missing(self) -> None:
        payload = _execute_bounded_pr_creation(
            unit_id="pr-create-missing-refs",
            job_id="job-1",
            repository="owner/repo",
            base_branch="",
            run_state_payload={
                "continue_allowed": True,
                "run_paused": False,
                "manual_intervention_required": False,
                "global_stop_recommended": False,
                "global_stop": False,
                "rollback_evaluation_pending": False,
            },
            merge_decision_payload={
                "manual_intervention_required": False,
                "unresolved_blockers": [],
            },
            commit_execution_payload={"status": "succeeded", "commit_sha": "a" * 40},
            push_execution_payload={
                "status": "succeeded",
                "branch_name": "",
                "remote_name": "origin",
                "head_branch": "",
            },
            read_backend=_FakeGitHubReadBackend(),
            write_backend=_FakeGitHubWriteBackend(),
            now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
        )
        payload = dict(payload)

        self.assertEqual(payload["status"], "blocked")
        self.assertIn("base_branch_missing", payload["blocking_reasons"])
        self.assertIn("head_branch_missing", payload["blocking_reasons"])
        self.assertFalse(payload["execution_allowed"])
        self.assertEqual(payload["validation_status"], "blocked")
        self.assertIn("base_branch_missing", payload["missing_required_refs"])
        self.assertIn("head_branch_missing", payload["missing_required_refs"])
        self.assertFalse(payload["remote_state_blocked"])

    def test_merge_blocked_when_pr_identity_missing(self) -> None:
        payload = _execute_bounded_merge(
            unit_id="pr-merge-missing-id",
            repository="owner/repo",
            run_state_payload={
                "continue_allowed": True,
                "run_paused": False,
                "manual_intervention_required": False,
                "global_stop_recommended": False,
                "global_stop": False,
                "rollback_evaluation_pending": False,
            },
            merge_decision_payload={
                "readiness_status": "ready",
                "automation_eligible": True,
                "manual_intervention_required": False,
                "unresolved_blockers": [],
                "prerequisites_satisfied": True,
            },
            commit_execution_payload={"status": "succeeded", "commit_sha": "a" * 40},
            push_execution_payload={"status": "succeeded", "branch_name": "feature/test", "remote_name": "origin"},
            pr_execution_payload={
                "status": "succeeded",
                "base_branch": "main",
                "head_branch": "feature/test",
                "pr_number": None,
            },
            read_backend=_FakeGitHubReadBackend(),
            write_backend=_FakeGitHubWriteBackend(),
            now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
        )
        payload = dict(payload)

        self.assertEqual(payload["status"], "blocked")
        self.assertIn("pr_number_missing_or_invalid", payload["blocking_reasons"])
        self.assertFalse(payload["execution_allowed"])
        self.assertEqual(payload["validation_status"], "passed")
        self.assertIn("pr_number_missing_or_invalid", payload["remote_pr_ambiguity"])
        self.assertEqual(payload["mergeability_status"], "unknown")

    def test_merge_blocked_when_mergeability_is_unknown(self) -> None:
        payload = _execute_bounded_merge(
            unit_id="pr-merge-unknown-mergeability",
            repository="owner/repo",
            run_state_payload={
                "continue_allowed": True,
                "run_paused": False,
                "manual_intervention_required": False,
                "global_stop_recommended": False,
                "global_stop": False,
                "rollback_evaluation_pending": False,
            },
            merge_decision_payload={
                "readiness_status": "ready",
                "automation_eligible": True,
                "manual_intervention_required": False,
                "unresolved_blockers": [],
                "prerequisites_satisfied": True,
            },
            commit_execution_payload={"status": "succeeded", "commit_sha": "a" * 40},
            push_execution_payload={"status": "succeeded", "branch_name": "feature/test", "remote_name": "origin"},
            pr_execution_payload={
                "status": "succeeded",
                "base_branch": "main",
                "head_branch": "feature/test",
                "pr_number": 10,
            },
            read_backend=_FakeGitHubReadBackend(
                pr_status_status="success",
                pr_state="open",
                mergeable_state="",
                checks_state="passing",
            ),
            write_backend=_FakeGitHubWriteBackend(),
            now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
        )
        payload = dict(payload)

        self.assertEqual(payload["status"], "blocked")
        self.assertIn("mergeability_unknown", payload["blocking_reasons"])
        self.assertEqual(payload["validation_status"], "passed")
        self.assertEqual(payload["mergeability_status"], "unknown")
        self.assertTrue(payload["remote_github_blocked"])

    def test_merge_blocked_when_required_checks_are_unsatisfied(self) -> None:
        payload = _execute_bounded_merge(
            unit_id="pr-merge-checks-unsatisfied",
            repository="owner/repo",
            run_state_payload={
                "continue_allowed": True,
                "run_paused": False,
                "manual_intervention_required": False,
                "global_stop_recommended": False,
                "global_stop": False,
                "rollback_evaluation_pending": False,
            },
            merge_decision_payload={
                "readiness_status": "ready",
                "automation_eligible": True,
                "manual_intervention_required": False,
                "unresolved_blockers": [],
                "prerequisites_satisfied": True,
            },
            commit_execution_payload={"status": "succeeded", "commit_sha": "a" * 40},
            push_execution_payload={"status": "succeeded", "branch_name": "feature/test", "remote_name": "origin"},
            pr_execution_payload={
                "status": "succeeded",
                "base_branch": "main",
                "head_branch": "feature/test",
                "pr_number": 11,
            },
            read_backend=_FakeGitHubReadBackend(
                pr_status_status="success",
                pr_state="open",
                mergeable_state="clean",
                checks_state="failing",
            ),
            write_backend=_FakeGitHubWriteBackend(),
            now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
        )
        payload = dict(payload)

        self.assertEqual(payload["status"], "blocked")
        self.assertIn("required_checks_unsatisfied", payload["blocking_reasons"])
        self.assertEqual(payload["required_checks_status"], "unsatisfied")
        self.assertEqual(payload["merge_requirements_status"], "unsatisfied")
        self.assertTrue(payload["remote_state_blocked"])

    def test_merge_blocked_when_review_or_protection_requirements_are_unsatisfied(self) -> None:
        payload = _execute_bounded_merge(
            unit_id="pr-merge-review-protection-unsatisfied",
            repository="owner/repo",
            run_state_payload={
                "continue_allowed": True,
                "run_paused": False,
                "manual_intervention_required": False,
                "global_stop_recommended": False,
                "global_stop": False,
                "rollback_evaluation_pending": False,
            },
            merge_decision_payload={
                "readiness_status": "ready",
                "automation_eligible": True,
                "manual_intervention_required": False,
                "unresolved_blockers": [],
                "prerequisites_satisfied": True,
            },
            commit_execution_payload={"status": "succeeded", "commit_sha": "a" * 40},
            push_execution_payload={"status": "succeeded", "branch_name": "feature/test", "remote_name": "origin"},
            pr_execution_payload={
                "status": "succeeded",
                "base_branch": "main",
                "head_branch": "feature/test",
                "pr_number": 12,
            },
            read_backend=_FakeGitHubReadBackend(
                pr_status_status="success",
                pr_state="open",
                mergeable_state="clean",
                checks_state="passing",
                review_state_status="unsatisfied",
                branch_protection_status="unsatisfied",
            ),
            write_backend=_FakeGitHubWriteBackend(),
            now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
        )
        payload = dict(payload)

        self.assertEqual(payload["status"], "blocked")
        self.assertIn("review_requirements_unsatisfied", payload["blocking_reasons"])
        self.assertIn("branch_protection_unsatisfied", payload["blocking_reasons"])
        self.assertEqual(payload["review_state_status"], "unsatisfied")
        self.assertEqual(payload["branch_protection_status"], "unsatisfied")
        self.assertEqual(payload["merge_requirements_status"], "unsatisfied")

    def test_merge_execution_failure_persists_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            changed_file = self._shrink_to_single_pr_slice(artifacts_dir)
            out_dir = root / "artifacts" / "executions"
            repo_dir = root / "execution_repo"
            repo_dir.mkdir(parents=True, exist_ok=True)
            self._init_git_repo_with_dirty_file(repo_dir, changed_file=changed_file)
            self._attach_origin_remote_and_push_initial(repo_dir)

            transport = _CommitReadyLiveTransport(
                changed_files_by_pr_id={"project-planned-exec-pr-01": [changed_file]}
            )
            read_backend = _FakeGitHubReadBackend(lookup_status="success", matched=False)
            write_backend = _FakeGitHubWriteBackend(create_status="success", merge_status="api_failure")
            runner = PlannedExecutionRunner(
                adapter=CodexExecutorAdapter(transport=transport),
                github_read_backend=read_backend,
                github_write_backend=write_backend,
            )
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
                execution_repo_path=repo_dir,
            )
            first = manifest["pr_units"][0]
            merge_execution = json.loads(Path(first["merge_execution_path"]).read_text(encoding="utf-8"))
            progression = json.loads(Path(first["unit_progression_path"]).read_text(encoding="utf-8"))
            run_state_payload = json.loads(Path(manifest["run_state_path"]).read_text(encoding="utf-8"))

        self.assertEqual(merge_execution["status"], "failed")
        self.assertTrue(merge_execution["attempted"])
        self.assertEqual(merge_execution["failure_reason"], "merge_execution_failed:api_failure")
        self.assertTrue(merge_execution["manual_intervention_required"])
        self.assertTrue(merge_execution["execution_allowed"])
        self.assertEqual(merge_execution["execution_authority_status"], "allowed")
        self.assertEqual(merge_execution["validation_status"], "passed")
        self.assertTrue(run_state_payload["merge_execution_failed"])
        self.assertTrue(run_state_payload["delivery_execution_manual_intervention_required"])
        states = [entry["state"] for entry in progression["checkpoints"]]
        self.assertIn("merge_execution_started", states)
        self.assertIn("merge_execution_failed", states)

    def test_execute_bounded_rollback_local_commit_only_succeeds_when_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_dir = Path(tmp_dir) / "repo"
            repo_dir.mkdir(parents=True, exist_ok=True)
            changed_file = "automation/planning/prompt_compiler.py"
            self._init_git_repo_with_dirty_file(repo_dir, changed_file=changed_file)
            subprocess.run(
                ["git", "-C", str(repo_dir), "add", "--", changed_file],
                check=True,
                capture_output=True,
                text=True,
            )
            commit_sha = self._git_commit(repo_dir, "bounded commit")

            payload = _execute_bounded_rollback(
                unit_id="pr-rollback-local",
                repo_path=str(repo_dir),
                run_state_payload={
                    "next_run_action": "evaluate_rollback",
                    "rollback_evaluation_pending": True,
                    "continue_allowed": False,
                    "manual_intervention_required": False,
                },
                rollback_decision_payload={
                    "decision": "required",
                    "readiness_status": "awaiting_prerequisites",
                    "automation_eligible": False,
                    "manual_intervention_required": False,
                    "unresolved_blockers": [
                        "run_global_stop_recommended",
                        "run_paused",
                        "run_rollback_evaluation_pending",
                    ],
                    "prerequisites_satisfied": True,
                    "recommended_next_action": "rollback_required",
                },
                commit_execution_payload={"status": "succeeded", "commit_sha": commit_sha},
                push_execution_payload={"status": "blocked"},
                pr_execution_payload={"status": "blocked"},
                merge_execution_payload={"status": "blocked"},
                dry_run=False,
                now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
            )
            head_after = subprocess.run(
                ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

        self.assertEqual(payload["status"], "succeeded")
        self.assertTrue(payload["attempted"])
        self.assertEqual(payload["rollback_mode"], "local_commit_only")
        self.assertTrue(payload["replan_required"])
        self.assertFalse(payload["manual_intervention_required"])
        self.assertNotEqual(commit_sha, head_after)

    def test_execute_bounded_rollback_pushed_or_pr_open_blocks_conservatively(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_dir = Path(tmp_dir) / "repo"
            repo_dir.mkdir(parents=True, exist_ok=True)
            changed_file = "automation/planning/prompt_compiler.py"
            self._init_git_repo_with_dirty_file(repo_dir, changed_file=changed_file)
            subprocess.run(
                ["git", "-C", str(repo_dir), "add", "--", changed_file],
                check=True,
                capture_output=True,
                text=True,
            )
            commit_sha = self._git_commit(repo_dir, "bounded commit")

            payload = _execute_bounded_rollback(
                unit_id="pr-rollback-pushed",
                repo_path=str(repo_dir),
                run_state_payload={
                    "next_run_action": "evaluate_rollback",
                    "rollback_evaluation_pending": True,
                    "continue_allowed": False,
                    "manual_intervention_required": False,
                },
                rollback_decision_payload={
                    "decision": "required",
                    "readiness_status": "awaiting_prerequisites",
                    "automation_eligible": False,
                    "manual_intervention_required": False,
                    "unresolved_blockers": [
                        "run_global_stop_recommended",
                        "run_rollback_evaluation_pending",
                    ],
                    "prerequisites_satisfied": True,
                    "recommended_next_action": "rollback_required",
                },
                commit_execution_payload={"status": "succeeded", "commit_sha": commit_sha},
                push_execution_payload={"status": "succeeded"},
                pr_execution_payload={"status": "blocked"},
                merge_execution_payload={"status": "blocked"},
                dry_run=False,
                now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
            )

        self.assertEqual(payload["status"], "blocked")
        self.assertFalse(payload["attempted"])
        self.assertEqual(payload["rollback_mode"], "pushed_or_pr_open")
        self.assertEqual(
            payload["failure_reason"],
            "rollback_mode_pushed_or_pr_open_requires_manual_path",
        )
        self.assertTrue(payload["manual_intervention_required"])

    def test_execute_bounded_rollback_merged_mode_succeeds_when_head_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_dir = Path(tmp_dir) / "repo"
            repo_dir.mkdir(parents=True, exist_ok=True)
            merged = self._init_merged_repo(repo_dir)
            merge_sha = merged["merge_sha"]
            payload = _execute_bounded_rollback(
                unit_id="pr-rollback-merged",
                repo_path=str(repo_dir),
                run_state_payload={
                    "next_run_action": "evaluate_rollback",
                    "rollback_evaluation_pending": True,
                    "continue_allowed": False,
                    "manual_intervention_required": False,
                },
                rollback_decision_payload={
                    "decision": "required",
                    "readiness_status": "awaiting_prerequisites",
                    "automation_eligible": False,
                    "manual_intervention_required": False,
                    "unresolved_blockers": [
                        "run_global_stop_recommended",
                        "run_rollback_evaluation_pending",
                    ],
                    "prerequisites_satisfied": True,
                    "recommended_next_action": "rollback_required",
                },
                commit_execution_payload={"status": "succeeded", "commit_sha": "a" * 40},
                push_execution_payload={"status": "succeeded", "base_branch": merged["target_branch"]},
                pr_execution_payload={"status": "succeeded", "base_branch": merged["target_branch"]},
                merge_execution_payload={
                    "status": "succeeded",
                    "base_branch": merged["target_branch"],
                    "merge_commit_sha": merge_sha,
                },
                dry_run=False,
                now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
            )
            head_after = subprocess.run(
                ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

        self.assertEqual(payload["status"], "succeeded")
        self.assertTrue(payload["attempted"])
        self.assertEqual(payload["rollback_mode"], "merged")
        self.assertTrue(payload["resulting_commit_sha"])
        self.assertNotEqual(head_after, merge_sha)

    def test_execute_bounded_rollback_blocks_on_ambiguous_lifecycle_evidence(self) -> None:
        payload = _execute_bounded_rollback(
            unit_id="pr-rollback-ambiguous",
            repo_path="",
            run_state_payload={
                "next_run_action": "evaluate_rollback",
                "rollback_evaluation_pending": True,
                "continue_allowed": False,
                "manual_intervention_required": False,
            },
            rollback_decision_payload={
                "decision": "required",
                "readiness_status": "awaiting_prerequisites",
                "automation_eligible": False,
                "manual_intervention_required": False,
                "unresolved_blockers": [
                    "run_global_stop_recommended",
                    "run_rollback_evaluation_pending",
                ],
                "prerequisites_satisfied": True,
                "recommended_next_action": "rollback_required",
            },
            commit_execution_payload={"status": "blocked"},
            push_execution_payload={"status": "blocked"},
            pr_execution_payload={"status": "blocked"},
            merge_execution_payload={"status": "blocked"},
            dry_run=False,
            now=lambda: datetime.fromisoformat("2026-04-18T00:00:00"),
        )

        self.assertEqual(payload["status"], "blocked")
        self.assertIn("rollback_mode_ambiguous", payload["blocking_reasons"])
        self.assertTrue(payload["manual_intervention_required"])
        self.assertFalse(payload["execution_allowed"])
        self.assertEqual(payload["validation_status"], "blocked")

    def test_rollback_aftermath_validation_failed_is_classified_conservatively(self) -> None:
        payload = _with_rollback_aftermath_surface(
            {
                "status": "succeeded",
                "rollback_mode": "local_commit_only",
                "resulting_commit_sha": "a" * 40,
                "manual_intervention_required": False,
                "replan_required": False,
                "automatic_continuation_blocked": False,
                "rollback_validation_status": "failed",
                "blocking_reasons": [],
            }
        )
        self.assertEqual(payload["rollback_aftermath_status"], "validation_failed")
        self.assertTrue(payload["rollback_aftermath_blocked"])
        self.assertEqual(payload["rollback_validation_status"], "failed")
        self.assertTrue(payload["rollback_manual_followup_required"])

    def test_rollback_aftermath_merged_without_post_validation_is_not_safe(self) -> None:
        payload = _with_rollback_aftermath_surface(
            {
                "status": "succeeded",
                "rollback_mode": "merged",
                "resulting_commit_sha": "b" * 40,
                "manual_intervention_required": False,
                "replan_required": False,
                "automatic_continuation_blocked": False,
                "blocking_reasons": [],
            }
        )
        self.assertNotEqual(payload["rollback_aftermath_status"], "completed_safe")
        self.assertTrue(payload["rollback_aftermath_blocked"])
        self.assertEqual(payload["rollback_validation_status"], "unavailable")
        self.assertTrue(payload["rollback_remote_followup_required"])
        self.assertTrue(payload["rollback_aftermath_missing_or_ambiguous"])

    def test_rollback_aftermath_completed_safe_can_be_classified_explicitly(self) -> None:
        payload = _with_rollback_aftermath_surface(
            {
                "status": "succeeded",
                "rollback_mode": "local_commit_only",
                "resulting_commit_sha": "c" * 40,
                "manual_intervention_required": False,
                "replan_required": False,
                "automatic_continuation_blocked": False,
                "rollback_validation_status": "satisfied",
                "rollback_post_validation_status": "satisfied",
                "rollback_manual_followup_required": False,
                "rollback_remote_followup_required": False,
                "blocking_reasons": [],
            }
        )
        self.assertEqual(payload["rollback_aftermath_status"], "completed_safe")
        self.assertFalse(payload["rollback_aftermath_blocked"])
        self.assertEqual(payload["rollback_validation_status"], "satisfied")

    def test_run_state_rollback_aftermath_summary_is_aggregated(self) -> None:
        run_state = _augment_run_state_with_rollback_aftermath(
            run_state_payload={},
            manifest_units=[
                {
                    "rollback_execution_summary": {
                        "rollback_aftermath_status": "remote_followup_required",
                        "rollback_aftermath_blocked": True,
                        "rollback_aftermath_blocked_reasons": ["rollback_remote_followup_required"],
                        "rollback_validation_status": "unavailable",
                        "rollback_remote_followup_required": True,
                        "rollback_manual_followup_required": False,
                        "rollback_aftermath_missing_or_ambiguous": True,
                    }
                }
            ],
        )
        self.assertTrue(run_state["rollback_aftermath_blocked"])
        self.assertTrue(run_state["rollback_remote_followup_required"])
        self.assertFalse(run_state["rollback_manual_followup_required"])
        self.assertFalse(run_state["rollback_validation_failed"])
        self.assertTrue(run_state["rollback_aftermath_missing_or_ambiguous"])
        self.assertIn(
            "rollback_remote_followup_required",
            run_state["rollback_aftermath_blocked_reasons"],
        )

    def test_closed_loop_blocks_when_authority_validation_state_is_blocked(self) -> None:
        run_state = {
            "continue_allowed": True,
            "run_paused": False,
            "manual_intervention_required": False,
            "rollback_evaluation_pending": False,
            "next_run_action": "continue_run",
            "global_stop_recommended": False,
            "global_stop": False,
            "merge_execution_succeeded": False,
            "rollback_execution_succeeded": False,
            "rollback_execution_failed": False,
            "rollback_replan_required": False,
            "rollback_automatic_continuation_blocked": False,
            "units_pending": 0,
            "authority_validation_blocked": True,
            "execution_authority_blocked": False,
            "validation_blocked": True,
            "authority_validation_blocked_reasons": ["working_tree_contains_out_of_scope_changes"],
        }
        manifest_units = [
            {
                "decision_summary": {
                    "commit_readiness_status": "ready",
                    "commit_execution_status": "blocked",
                },
                "commit_execution_summary": {
                    "status": "blocked",
                    "execution_allowed": False,
                    "execution_authority_status": "allowed",
                    "validation_status": "blocked",
                },
            }
        ]

        augmented = _augment_run_state_with_closed_loop(
            run_state_payload=run_state,
            manifest_units=manifest_units,
            run_status="completed",
        )

        self.assertEqual(augmented["loop_state"], "manual_intervention_required")
        self.assertEqual(augmented["next_safe_action"], "require_manual_intervention")
        self.assertEqual(
            augmented["loop_blocked_reason"],
            "working_tree_contains_out_of_scope_changes",
        )
        self.assertTrue(augmented["loop_manual_intervention_required"])

    def test_closed_loop_blocks_when_remote_github_state_is_blocked(self) -> None:
        run_state = {
            "continue_allowed": True,
            "run_paused": False,
            "manual_intervention_required": False,
            "rollback_evaluation_pending": False,
            "next_run_action": "continue_run",
            "global_stop_recommended": False,
            "global_stop": False,
            "merge_execution_succeeded": False,
            "rollback_execution_succeeded": False,
            "rollback_execution_failed": False,
            "rollback_replan_required": False,
            "rollback_automatic_continuation_blocked": False,
            "units_pending": 0,
            "authority_validation_blocked": False,
            "execution_authority_blocked": False,
            "validation_blocked": False,
            "remote_github_blocked": True,
            "remote_github_manual_required": True,
            "remote_github_missing_or_ambiguous": True,
            "remote_github_blocked_reasons": ["existing_open_pr_detected"],
        }
        manifest_units = [
            {
                "decision_summary": {
                    "commit_readiness_status": "ready",
                    "commit_execution_status": "blocked",
                },
                "pr_execution_summary": {
                    "status": "blocked",
                    "remote_github_blocked": True,
                    "remote_state_blocked": True,
                },
            }
        ]

        augmented = _augment_run_state_with_closed_loop(
            run_state_payload=run_state,
            manifest_units=manifest_units,
            run_status="completed",
        )

        self.assertEqual(augmented["loop_state"], "manual_intervention_required")
        self.assertEqual(augmented["next_safe_action"], "require_manual_intervention")
        self.assertEqual(augmented["loop_blocked_reason"], "existing_open_pr_detected")
        self.assertTrue(augmented["loop_manual_intervention_required"])

    def test_closed_loop_blocks_when_rollback_aftermath_is_unresolved(self) -> None:
        run_state = {
            "continue_allowed": False,
            "run_paused": False,
            "manual_intervention_required": False,
            "rollback_evaluation_pending": False,
            "next_run_action": "pause_run",
            "global_stop_recommended": False,
            "global_stop": False,
            "merge_execution_succeeded": False,
            "rollback_execution_succeeded": True,
            "rollback_execution_failed": False,
            "rollback_replan_required": False,
            "rollback_automatic_continuation_blocked": False,
            "rollback_aftermath_status": "validation_failed",
            "rollback_aftermath_blocked": True,
            "rollback_aftermath_manual_required": True,
            "rollback_aftermath_missing_or_ambiguous": True,
            "rollback_aftermath_blocked_reasons": ["rollback_validation_failed"],
            "rollback_remote_followup_required": False,
            "rollback_manual_followup_required": True,
            "rollback_validation_failed": True,
            "units_pending": 0,
            "authority_validation_blocked": False,
            "execution_authority_blocked": False,
            "validation_blocked": False,
            "remote_github_blocked": False,
            "remote_github_manual_required": False,
            "remote_github_missing_or_ambiguous": False,
        }
        manifest_units = [{"decision_summary": {"rollback_execution_status": "succeeded"}}]

        augmented = _augment_run_state_with_closed_loop(
            run_state_payload=run_state,
            manifest_units=manifest_units,
            run_status="completed",
        )

        self.assertEqual(augmented["loop_state"], "rollback_completed_blocked")
        self.assertEqual(augmented["next_safe_action"], "require_manual_intervention")
        self.assertEqual(augmented["loop_blocked_reason"], "rollback_validation_failed")
        self.assertTrue(augmented["loop_manual_intervention_required"])

    def test_policy_overlay_duplicate_pr_blocks_pr_action_without_terminalizing_run(self) -> None:
        run_state = _augment_run_state_with_policy_overlay(
            run_state_payload={
                "loop_state": "manual_intervention_required",
                "next_safe_action": "pause",
                "terminal": False,
                "resumable": True,
                "continue_allowed": False,
                "manual_intervention_required": True,
                "remote_github_blocked": True,
                "remote_github_missing_or_ambiguous": False,
                "remote_github_blocked_reasons": ["existing_open_pr_detected"],
                "remote_github_blocked_reason": "existing_open_pr_detected",
            }
        )
        self.assertEqual(run_state["policy_status"], "blocked")
        self.assertTrue(run_state["policy_blocked"])
        self.assertFalse(run_state["policy_terminal"])
        self.assertTrue(run_state["policy_resume_allowed"])
        self.assertEqual(run_state["policy_primary_blocker_class"], "remote_github")
        self.assertIn("proceed_to_pr", run_state["policy_disallowed_actions"])
        self.assertIn("inspect", run_state["policy_allowed_actions"])

    def test_policy_overlay_rollback_validation_failed_maps_to_replan_required(self) -> None:
        run_state = _augment_run_state_with_policy_overlay(
            run_state_payload={
                "loop_state": "rollback_completed_blocked",
                "next_safe_action": "require_replanning",
                "terminal": False,
                "resumable": False,
                "continue_allowed": False,
                "rollback_replan_required": True,
                "loop_replan_required": True,
                "rollback_validation_failed": True,
                "rollback_aftermath_blocked": True,
                "rollback_aftermath_blocked_reasons": ["rollback_validation_failed"],
                "rollback_aftermath_blocked_reason": "rollback_validation_failed",
            }
        )
        self.assertEqual(run_state["policy_status"], "replan_required")
        self.assertTrue(run_state["policy_replan_required"])
        self.assertFalse(run_state["policy_resume_allowed"])
        self.assertEqual(run_state["policy_primary_blocker_class"], "replan_required")
        self.assertIn("rollback_validation_failed", run_state["policy_blocked_reasons"])

    def test_policy_overlay_ambiguous_truth_maps_to_manual_only(self) -> None:
        run_state = _augment_run_state_with_policy_overlay(
            run_state_payload={
                "loop_state": "manual_intervention_required",
                "next_safe_action": "pause",
                "terminal": False,
                "resumable": True,
                "continue_allowed": False,
                "authority_validation_missing_or_ambiguous": True,
                "manual_intervention_required": True,
            }
        )
        self.assertEqual(run_state["policy_status"], "manual_only")
        self.assertTrue(run_state["policy_manual_required"])
        self.assertTrue(run_state["policy_resume_allowed"])
        self.assertTrue(run_state["policy_blocked"])
        self.assertIn("proceed_to_merge", run_state["policy_disallowed_actions"])

    def test_policy_overlay_terminal_success_is_explicitly_terminal(self) -> None:
        run_state = _augment_run_state_with_policy_overlay(
            run_state_payload={
                "loop_state": "terminal_success",
                "next_safe_action": "stop_terminal_success",
                "terminal": True,
                "resumable": False,
                "continue_allowed": False,
            }
        )
        self.assertEqual(run_state["policy_status"], "terminally_stopped")
        self.assertTrue(run_state["policy_terminal"])
        self.assertFalse(run_state["policy_blocked"])
        self.assertFalse(run_state["policy_resume_allowed"])

    def test_lifecycle_terminal_contract_distinguishes_safely_closed(self) -> None:
        run_state = _augment_run_state_with_lifecycle_terminal_contract(
            run_state_payload={
                "state": "completed",
                "orchestration_state": "completed",
                "loop_state": "terminal_success",
                "terminal": True,
                "resumable": False,
                "policy_status": "terminally_stopped",
                "policy_blocked": False,
                "policy_manual_required": False,
                "policy_replan_required": False,
                "policy_terminal": True,
                "policy_resume_allowed": False,
                "delivery_completed": True,
                "merge_execution_succeeded": True,
            }
        )
        self.assertEqual(run_state["lifecycle_closure_status"], "safely_closed")
        self.assertTrue(run_state["lifecycle_safely_closed"])
        self.assertTrue(run_state["lifecycle_terminal"])
        self.assertFalse(run_state["lifecycle_execution_complete_not_closed"])
        self.assertFalse(run_state["lifecycle_rollback_complete_not_closed"])
        self.assertEqual(run_state["lifecycle_primary_closure_issue"], "")

    def test_lifecycle_terminal_contract_distinguishes_execution_complete_and_rollback_not_closed(self) -> None:
        run_state = _augment_run_state_with_lifecycle_terminal_contract(
            run_state_payload={
                "state": "paused",
                "loop_state": "rollback_completed_blocked",
                "terminal": False,
                "resumable": True,
                "policy_status": "manual_only",
                "policy_blocked": True,
                "policy_manual_required": True,
                "policy_replan_required": False,
                "policy_terminal": False,
                "policy_resume_allowed": True,
                "delivery_completed": True,
                "merge_execution_succeeded": True,
                "rollback_execution_succeeded": True,
                "rollback_aftermath_status": "remote_followup_required",
                "rollback_aftermath_blocked": True,
                "rollback_aftermath_blocked_reason": "rollback_remote_followup_required",
                "rollback_remote_followup_required": True,
            }
        )
        self.assertEqual(run_state["lifecycle_closure_status"], "rollback_complete_not_closed")
        self.assertFalse(run_state["lifecycle_safely_closed"])
        self.assertTrue(run_state["lifecycle_execution_complete_not_closed"])
        self.assertTrue(run_state["lifecycle_rollback_complete_not_closed"])
        self.assertEqual(
            run_state["lifecycle_primary_closure_issue"],
            "rollback_remote_followup_required",
        )

    def test_lifecycle_terminal_contract_distinguishes_replan_manual_and_resumable(self) -> None:
        replan_state = _augment_run_state_with_lifecycle_terminal_contract(
            run_state_payload={
                "loop_state": "replan_required",
                "terminal": False,
                "resumable": False,
                "policy_status": "replan_required",
                "policy_blocked": True,
                "policy_replan_required": True,
                "policy_resume_allowed": False,
            }
        )
        self.assertEqual(replan_state["lifecycle_closure_status"], "stopped_replan_required")
        self.assertFalse(replan_state["lifecycle_terminal"])
        self.assertTrue(replan_state["lifecycle_replan_required"])

        manual_state = _augment_run_state_with_lifecycle_terminal_contract(
            run_state_payload={
                "loop_state": "manual_intervention_required",
                "terminal": False,
                "resumable": False,
                "policy_status": "manual_only",
                "policy_blocked": True,
                "policy_manual_required": True,
                "policy_resume_allowed": False,
            }
        )
        self.assertEqual(manual_state["lifecycle_closure_status"], "stopped_manual_only")
        self.assertTrue(manual_state["lifecycle_manual_required"])
        self.assertFalse(manual_state["lifecycle_resumable"])

        resumable_state = _augment_run_state_with_lifecycle_terminal_contract(
            run_state_payload={
                "loop_state": "manual_intervention_required",
                "terminal": False,
                "resumable": True,
                "policy_status": "blocked",
                "policy_blocked": True,
                "policy_manual_required": False,
                "policy_replan_required": False,
                "policy_resume_allowed": True,
                "policy_blocked_reason": "existing_open_pr_detected",
            }
        )
        self.assertEqual(resumable_state["lifecycle_closure_status"], "stopped_resumable")
        self.assertTrue(resumable_state["lifecycle_resumable"])
        self.assertFalse(resumable_state["lifecycle_terminal"])

    def test_objective_contract_is_deterministic_and_uses_priority_one_sources(self) -> None:
        artifacts = {
            "project_brief": {
                "project_id": "proj-1",
                "objective": "Priority1 objective",
                "success_definition": "Priority1 outcome",
                "target_repo": "repo-from-brief",
                "target_branch": "main",
                "allowed_risk_level": "conservative",
                "non_goals": ["no-refactor"],
            },
            "repo_facts": {
                "repo": "repo-from-facts",
                "default_branch": "develop",
            },
            "pr_plan": {
                "plan_id": "proj-1-plan-v1",
                "prs": [
                    {
                        "pr_id": "proj-1-pr-01",
                        "exact_scope": "priority1 exact scope",
                        "touched_files": ["src/a.py"],
                        "forbidden_files": ["src/unsafe.py"],
                        "acceptance_criteria": ["planned acceptance"],
                    }
                ],
            },
            "roadmap": {"estimated_risk": "high"},
        }
        units = [
            {
                "bounded_step_contract": {
                    "purpose": "Priority2 bounded purpose",
                    "scope_in": ["src/alt.py"],
                    "scope_out": ["src/alt_unsafe.py"],
                    "invariants_to_preserve": ["bounded invariant"],
                },
                "pr_implementation_prompt_contract": {
                    "task_scope": {"purpose": "Priority2 prompt purpose"},
                    "definition_of_done": ["prompt done"],
                },
                "codex_task_prompt_md": "- Priority4 fallback summary",
            }
        ]
        artifact_ownership = {
            "run_state": "run_state.json",
            "next_action": "next_action.json",
            "objective_contract": "objective_contract.json",
        }

        payload_a = build_objective_contract_surface(
            run_id="job-objective-1",
            artifacts=artifacts,
            units=units,
            artifact_ownership=artifact_ownership,
        )
        payload_b = build_objective_contract_surface(
            run_id="job-objective-1",
            artifacts=artifacts,
            units=units,
            artifact_ownership=artifact_ownership,
        )

        self.assertEqual(payload_a, payload_b)
        self.assertEqual(payload_a["objective_summary"], "Priority1 objective")
        self.assertEqual(payload_a["requested_outcome"], "Priority1 outcome")
        self.assertEqual(payload_a["target_repo"], "repo-from-brief")
        self.assertEqual(payload_a["target_branch"], "main")
        self.assertEqual(payload_a["source_priority_used"], "priority_1")
        self.assertEqual(payload_a["objective_source_status"], "structured_complete")
        self.assertIn(payload_a["objective_status"], {"complete", "incomplete", "underspecified", "blocked"})
        self.assertIn(payload_a["acceptance_status"], {"defined", "partially_defined", "undefined", "blocked"})
        self.assertIn(payload_a["scope_status"], {"clear", "partial", "unclear", "blocked"})
        self.assertIn(
            payload_a["required_artifacts_status"],
            {"defined", "partially_defined", "undefined", "blocked"},
        )

    def test_objective_contract_is_conservative_when_inputs_are_missing(self) -> None:
        payload = build_objective_contract_surface(
            run_id="job-objective-missing",
            artifacts={},
            units=[],
            artifact_ownership={},
        )

        self.assertEqual(payload["schema_version"], "v1")
        self.assertEqual(payload["run_id"], "job-objective-missing")
        self.assertEqual(payload["objective_source_status"], "missing")
        self.assertEqual(payload["objective_status"], "blocked")
        self.assertEqual(payload["acceptance_status"], "blocked")
        self.assertEqual(payload["scope_status"], "blocked")
        self.assertEqual(payload["required_artifacts_status"], "blocked")
        self.assertTrue(payload["objective_blocked_reasons"])

    def test_objective_contract_keeps_unknown_acceptance_undefined(self) -> None:
        payload = build_objective_contract_surface(
            run_id="job-objective-acceptance",
            artifacts={
                "project_brief": {
                    "project_id": "proj-acceptance",
                    "objective": "Objective without acceptance",
                    "success_definition": "",
                },
                "pr_plan": {
                    "plan_id": "proj-acceptance-plan-v1",
                    "prs": [
                        {
                            "pr_id": "proj-acceptance-pr-01",
                            "touched_files": ["src/a.py"],
                            "forbidden_files": ["src/b.py"],
                            "acceptance_criteria": [],
                        }
                    ],
                },
            },
            units=[],
            artifact_ownership={"run_state": "run_state.json"},
        )

        self.assertIn(payload["acceptance_status"], {"undefined", "blocked", "partially_defined"})
        self.assertNotEqual(payload["acceptance_status"], "defined")
        self.assertEqual(payload["acceptance_criteria"][0]["status"], "undefined")

    def test_objective_run_state_summary_surface_is_compact(self) -> None:
        compact = build_objective_run_state_summary_surface(
            {
                "objective_id": "objective-123",
                "objective_summary": "Summary",
                "objective_type": "implementation",
                "requested_outcome": "Outcome",
                "objective_status": "underspecified",
                "acceptance_status": "partially_defined",
                "scope_status": "partial",
                "required_artifacts_status": "defined",
                "objective_blocked_reason": "acceptance_partially_defined",
            }
        )

        self.assertEqual(set(compact.keys()), set(OBJECTIVE_RUN_STATE_SUMMARY_SAFE_FIELDS))
        self.assertEqual(compact["objective_contract_status"], "underspecified")
        self.assertEqual(compact["objective_acceptance_status"], "partially_defined")
        self.assertEqual(compact["objective_scope_status"], "partial")
        self.assertEqual(compact["objective_required_artifacts_status"], "defined")

    def test_completion_contract_is_deterministic_when_truth_is_aligned(self) -> None:
        objective_payload = {
            "objective_id": "objective-123",
            "objective_summary": "Implement narrow completion contract",
            "requested_outcome": "done and safely closed",
            "objective_status": "complete",
            "acceptance_status": "defined",
            "acceptance_criteria": [
                {"criterion_id": "criterion_001", "status": "defined", "text": "all checks pass"}
            ],
            "required_artifacts": ["next_action.json", "run_state.json"],
        }
        run_state_payload = {
            "lifecycle_closure_status": "safely_closed",
            "lifecycle_safely_closed": True,
            "lifecycle_manual_required": False,
            "lifecycle_replan_required": False,
            "policy_manual_required": False,
            "policy_replan_required": False,
            "delivery_completed": True,
        }
        artifact_presence = {
            "next_action.json": True,
            "run_state.json": True,
        }

        payload_a = build_completion_contract_surface(
            run_id="job-completion-1",
            objective_contract_payload=objective_payload,
            run_state_payload=run_state_payload,
            artifact_presence=artifact_presence,
        )
        payload_b = build_completion_contract_surface(
            run_id="job-completion-1",
            objective_contract_payload=objective_payload,
            run_state_payload=run_state_payload,
            artifact_presence=artifact_presence,
        )

        self.assertEqual(payload_a, payload_b)
        self.assertEqual(payload_a["completion_status"], "done_and_safely_closed")
        self.assertEqual(payload_a["done_status"], "done")
        self.assertEqual(payload_a["safe_closure_status"], "safely_closed")
        self.assertEqual(payload_a["closure_decision"], "close")
        self.assertEqual(payload_a["lifecycle_alignment_status"], "aligned")
        self.assertEqual(payload_a["completion_blocked_reason"], "")
        self.assertEqual(payload_a["completion_blocked_reasons"], [])
        self.assertIn(payload_a["completion_evidence_status"], {"sufficient", "partial", "missing"})

    def test_completion_contract_degrades_conservatively_when_objective_truth_missing(self) -> None:
        payload = build_completion_contract_surface(
            run_id="job-completion-missing",
            objective_contract_payload={},
            run_state_payload={},
            artifact_presence={},
        )

        self.assertEqual(payload["schema_version"], "v1")
        self.assertEqual(payload["run_id"], "job-completion-missing")
        self.assertIn(payload["completion_status"], COMPLETION_STATUSES)
        self.assertIn(payload["done_status"], DONE_STATUSES)
        self.assertIn(payload["safe_closure_status"], SAFE_CLOSURE_STATUSES)
        self.assertIn(payload["closure_decision"], CLOSURE_DECISIONS)
        self.assertIn(payload["lifecycle_alignment_status"], LIFECYCLE_ALIGNMENT_STATUSES)
        self.assertIn(payload["completion_evidence_status"], COMPLETION_EVIDENCE_STATUSES)
        self.assertNotEqual(payload["completion_status"], "done_and_safely_closed")
        self.assertNotEqual(payload["done_status"], "done")
        self.assertTrue(payload["missing_evidence"])
        self.assertTrue(payload["completion_blocked_reasons"])

    def test_completion_contract_distinguishes_execution_complete_not_accepted(self) -> None:
        payload = build_completion_contract_surface(
            run_id="job-completion-execution-only",
            objective_contract_payload={
                "objective_id": "objective-456",
                "objective_status": "underspecified",
                "acceptance_status": "partially_defined",
                "acceptance_criteria": [{"criterion_id": "criterion_001", "status": "undefined"}],
                "required_artifacts": [],
            },
            run_state_payload={
                "delivery_completed": True,
                "lifecycle_closure_status": "execution_complete_not_closed",
                "lifecycle_safely_closed": False,
                "lifecycle_manual_required": False,
                "lifecycle_replan_required": False,
                "policy_manual_required": False,
                "policy_replan_required": False,
            },
            artifact_presence={},
        )

        self.assertEqual(payload["done_status"], "not_done")
        self.assertEqual(payload["safe_closure_status"], "not_safely_closed")
        self.assertEqual(payload["completion_status"], "execution_complete_not_accepted")
        self.assertTrue(payload["execution_complete_not_accepted"])

    def test_completion_contract_distinguishes_done_from_safe_closure(self) -> None:
        payload = build_completion_contract_surface(
            run_id="job-completion-manual-close",
            objective_contract_payload={
                "objective_id": "objective-789",
                "objective_status": "complete",
                "acceptance_status": "defined",
                "acceptance_criteria": [{"criterion_id": "criterion_001", "status": "defined"}],
                "required_artifacts": [],
            },
            run_state_payload={
                "lifecycle_closure_status": "stopped_manual_only",
                "lifecycle_safely_closed": False,
                "lifecycle_manual_required": True,
                "lifecycle_replan_required": False,
                "policy_manual_required": True,
                "policy_replan_required": False,
            },
            artifact_presence={},
        )

        self.assertEqual(payload["done_status"], "done")
        self.assertEqual(payload["safe_closure_status"], "not_safely_closed")
        self.assertEqual(payload["completion_status"], "manual_closure_required")
        self.assertTrue(payload["completion_manual_required"])

    def test_completion_run_state_summary_surface_is_compact(self) -> None:
        compact = build_completion_run_state_summary_surface(
            {
                "completion_status": "delivery_complete_waiting_external_truth",
                "done_status": "done",
                "safe_closure_status": "not_safely_closed",
                "completion_evidence_status": "partial",
                "completion_blocked_reason": "delivery_complete_waiting_external_truth",
                "completion_manual_required": True,
                "completion_replan_required": False,
                "lifecycle_alignment_status": "partially_aligned",
            }
        )

        self.assertEqual(set(compact.keys()), set(COMPLETION_RUN_STATE_SUMMARY_SAFE_FIELDS))
        self.assertEqual(compact["completion_status"], "delivery_complete_waiting_external_truth")
        self.assertEqual(compact["done_status"], "done")
        self.assertEqual(compact["safe_closure_status"], "not_safely_closed")
        self.assertEqual(compact["completion_evidence_status"], "partial")
        self.assertEqual(compact["completion_lifecycle_alignment_status"], "partially_aligned")

    def test_approval_transport_is_deterministic_when_truth_and_input_are_stable(self) -> None:
        objective_payload = {
            "objective_id": "objective-approval-1",
            "objective_status": "complete",
            "objective_summary": "Safely close completed run",
            "requested_outcome": "close run safely",
        }
        completion_payload = {
            "completion_status": "done_and_safely_closed",
            "done_status": "done",
            "safe_closure_status": "safely_closed",
            "closure_decision": "close",
            "completion_manual_required": False,
            "completion_replan_required": False,
        }
        run_state_payload = {
            "lifecycle_closure_status": "safely_closed",
            "lifecycle_primary_closure_issue": "",
            "lifecycle_manual_required": False,
            "lifecycle_replan_required": False,
            "next_safe_action": "stop_terminal_success",
            "policy_primary_action": "proceed_to_merge",
            "policy_status": "allowed",
            "policy_manual_required": False,
            "policy_replan_required": False,
            "manual_intervention_required": False,
        }
        approval_input = {
            "approval_decision": "approve",
            "approval_scope": "current_run",
            "approved_action": "close_run",
            "approval_actor": "operator",
            "approval_reason": "all truth aligned",
            "approval_recorded_at": "2026-04-19T10:00:00+00:00",
        }

        payload_a = build_approval_transport_surface(
            run_id="job-approval-1",
            objective_contract_payload=objective_payload,
            completion_contract_payload=completion_payload,
            run_state_payload=run_state_payload,
            approval_input_payload=approval_input,
            evaluated_at="2026-04-19T10:05:00+00:00",
        )
        payload_b = build_approval_transport_surface(
            run_id="job-approval-1",
            objective_contract_payload=objective_payload,
            completion_contract_payload=completion_payload,
            run_state_payload=run_state_payload,
            approval_input_payload=approval_input,
            evaluated_at="2026-04-19T10:05:00+00:00",
        )

        self.assertEqual(payload_a, payload_b)
        self.assertIn(payload_a["approval_status"], APPROVAL_STATUSES)
        self.assertIn(payload_a["approval_decision"], APPROVAL_DECISIONS)
        self.assertIn(payload_a["approval_scope"], APPROVAL_SCOPES)
        self.assertIn(payload_a["approved_action"], APPROVED_ACTIONS)
        self.assertIn(payload_a["approval_compatibility_status"], APPROVAL_COMPATIBILITY_STATUSES)
        self.assertIn(payload_a["approval_transport_status"], APPROVAL_TRANSPORT_STATUSES)
        self.assertEqual(payload_a["approval_status"], "approved")
        self.assertEqual(payload_a["approval_transport_status"], "actionable")
        self.assertEqual(payload_a["approval_compatibility_status"], "compatible")
        self.assertEqual(payload_a["approval_blocked_reason"], "")
        self.assertEqual(payload_a["approval_blocked_reasons"], [])

    def test_approval_transport_emits_absent_when_input_is_missing(self) -> None:
        payload = build_approval_transport_surface(
            run_id="job-approval-absent",
            objective_contract_payload={
                "objective_id": "objective-approval-absent",
                "objective_status": "incomplete",
            },
            completion_contract_payload={
                "completion_status": "manual_closure_required",
                "done_status": "not_done",
                "safe_closure_status": "not_safely_closed",
                "completion_manual_required": True,
                "completion_replan_required": False,
            },
            run_state_payload={
                "lifecycle_closure_status": "stopped_manual_only",
                "lifecycle_manual_required": True,
                "lifecycle_replan_required": False,
                "policy_status": "manual_only",
                "policy_manual_required": True,
                "policy_replan_required": False,
                "manual_intervention_required": True,
            },
            approval_input_payload=None,
            evaluated_at="2026-04-19T10:05:00+00:00",
        )

        self.assertEqual(payload["approval_status"], "absent")
        self.assertEqual(payload["approval_decision"], "none")
        self.assertFalse(payload["approval_present"])
        self.assertEqual(payload["approval_transport_status"], "missing")
        self.assertEqual(payload["approval_compatibility_status"], "insufficient_truth")
        self.assertEqual(payload["approval_actor"], "")
        self.assertEqual(payload["approval_reason"], "")
        self.assertEqual(payload["approval_notes"], "")
        self.assertTrue(payload["approval_blocked_reasons"])

    def test_approval_transport_marks_closure_approval_incompatible_when_not_done(self) -> None:
        payload = build_approval_transport_surface(
            run_id="job-approval-incompatible",
            objective_contract_payload={
                "objective_id": "objective-approval-2",
                "objective_status": "underspecified",
            },
            completion_contract_payload={
                "completion_status": "execution_complete_not_accepted",
                "done_status": "not_done",
                "safe_closure_status": "not_safely_closed",
                "closure_decision": "hold",
                "completion_manual_required": False,
                "completion_replan_required": False,
            },
            run_state_payload={
                "lifecycle_closure_status": "execution_complete_not_closed",
                "lifecycle_manual_required": False,
                "lifecycle_replan_required": False,
                "policy_status": "blocked",
                "policy_manual_required": False,
                "policy_replan_required": False,
            },
            approval_input_payload={
                "approval_decision": "approve",
                "approval_scope": "current_run",
                "approved_action": "close_run",
            },
            evaluated_at="2026-04-19T10:05:00+00:00",
        )

        self.assertEqual(payload["approval_status"], "approved")
        self.assertEqual(payload["approval_compatibility_status"], "incompatible")
        self.assertEqual(payload["approval_transport_status"], "blocked")
        self.assertIn("completion_not_done_for_closure", payload["approval_blocked_reasons"])

    def test_approval_transport_degrades_for_stale_and_superseded_inputs(self) -> None:
        base_objective = {"objective_id": "objective-approval-3", "objective_status": "complete"}
        base_completion = {
            "completion_status": "done_and_safely_closed",
            "done_status": "done",
            "safe_closure_status": "safely_closed",
            "completion_manual_required": False,
            "completion_replan_required": False,
        }
        base_run_state = {
            "lifecycle_closure_status": "safely_closed",
            "lifecycle_manual_required": False,
            "lifecycle_replan_required": False,
            "policy_status": "allowed",
            "policy_manual_required": False,
            "policy_replan_required": False,
        }

        stale_payload = build_approval_transport_surface(
            run_id="job-approval-3",
            objective_contract_payload=base_objective,
            completion_contract_payload=base_completion,
            run_state_payload=base_run_state,
            approval_input_payload={
                "approval_decision": "approve",
                "approval_scope": "current_run",
                "approval_expires_at": "2026-04-19T09:59:59+00:00",
            },
            evaluated_at="2026-04-19T10:05:00+00:00",
        )
        superseded_payload = build_approval_transport_surface(
            run_id="job-approval-3",
            objective_contract_payload=base_objective,
            completion_contract_payload=base_completion,
            run_state_payload=base_run_state,
            approval_input_payload={
                "approval_decision": "approve",
                "approval_scope": "current_run",
                "target_completion_status": "replan_before_closure",
            },
            evaluated_at="2026-04-19T10:05:00+00:00",
        )

        self.assertTrue(stale_payload["approval_stale"])
        self.assertEqual(stale_payload["approval_transport_status"], "expired")
        self.assertTrue(superseded_payload["approval_superseded"])
        self.assertEqual(superseded_payload["approval_transport_status"], "superseded")

    def test_approval_run_state_summary_surface_is_compact(self) -> None:
        compact = build_approval_run_state_summary_surface(
            {
                "approval_status": "deferred",
                "approval_decision": "defer",
                "approval_scope": "next_safe_action_only",
                "approved_action": "hold_for_manual_review",
                "approval_required": True,
                "approval_transport_status": "non_actionable",
                "approval_compatibility_status": "partially_compatible",
                "approval_blocked_reason": "approval_scope_partial",
                "approval_notes": "not summary safe",
            }
        )

        self.assertEqual(set(compact.keys()), set(APPROVAL_RUN_STATE_SUMMARY_SAFE_FIELDS))
        self.assertEqual(compact["approval_status"], "deferred")
        self.assertEqual(compact["approval_decision"], "defer")
        self.assertEqual(compact["approval_scope"], "next_safe_action_only")
        self.assertEqual(compact["approved_action"], "hold_for_manual_review")
        self.assertEqual(compact["approval_transport_status"], "non_actionable")
        self.assertEqual(compact["approval_compatibility_status"], "partially_compatible")

    def test_reconcile_contract_is_deterministic_when_truth_surfaces_align(self) -> None:
        payload_a = build_reconcile_contract_surface(
            run_id="job-reconcile-1",
            objective_contract_payload={
                "objective_id": "objective-reconcile-1",
                "objective_summary": "close run",
                "requested_outcome": "aligned close",
                "objective_status": "complete",
            },
            completion_contract_payload={
                "objective_id": "objective-reconcile-1",
                "completion_status": "done_and_safely_closed",
                "done_status": "done",
                "safe_closure_status": "safely_closed",
                "closure_decision": "close",
                "completion_manual_required": False,
                "completion_replan_required": False,
            },
            approval_transport_payload={
                "objective_id": "objective-reconcile-1",
                "approval_status": "approved",
                "approval_decision": "approve",
                "approval_transport_status": "actionable",
                "approval_required": False,
                "approval_present": True,
            },
            run_state_payload={
                "objective_contract_present": True,
                "completion_contract_present": True,
                "approval_transport_present": True,
                "objective_contract_status": "complete",
                "completion_status": "done_and_safely_closed",
                "approval_status": "approved",
                "lifecycle_closure_status": "safely_closed",
                "lifecycle_safely_closed": True,
                "lifecycle_manual_required": False,
                "lifecycle_replan_required": False,
                "manual_intervention_required": False,
                "policy_replan_required": False,
                "rollback_replan_required": False,
            },
            artifact_presence={
                "objective_contract.json": True,
                "completion_contract.json": True,
                "approval_transport.json": True,
                "run_state.json": True,
            },
        )
        payload_b = build_reconcile_contract_surface(
            run_id="job-reconcile-1",
            objective_contract_payload={
                "objective_id": "objective-reconcile-1",
                "objective_summary": "close run",
                "requested_outcome": "aligned close",
                "objective_status": "complete",
            },
            completion_contract_payload={
                "objective_id": "objective-reconcile-1",
                "completion_status": "done_and_safely_closed",
                "done_status": "done",
                "safe_closure_status": "safely_closed",
                "closure_decision": "close",
                "completion_manual_required": False,
                "completion_replan_required": False,
            },
            approval_transport_payload={
                "objective_id": "objective-reconcile-1",
                "approval_status": "approved",
                "approval_decision": "approve",
                "approval_transport_status": "actionable",
                "approval_required": False,
                "approval_present": True,
            },
            run_state_payload={
                "objective_contract_present": True,
                "completion_contract_present": True,
                "approval_transport_present": True,
                "objective_contract_status": "complete",
                "completion_status": "done_and_safely_closed",
                "approval_status": "approved",
                "lifecycle_closure_status": "safely_closed",
                "lifecycle_safely_closed": True,
                "lifecycle_manual_required": False,
                "lifecycle_replan_required": False,
                "manual_intervention_required": False,
                "policy_replan_required": False,
                "rollback_replan_required": False,
            },
            artifact_presence={
                "objective_contract.json": True,
                "completion_contract.json": True,
                "approval_transport.json": True,
                "run_state.json": True,
            },
        )

        self.assertEqual(payload_a, payload_b)
        self.assertEqual(payload_a["reconcile_status"], "aligned")
        self.assertEqual(payload_a["reconcile_decision"], "aligned_no_action")
        self.assertEqual(payload_a["reconcile_primary_mismatch"], "")
        self.assertEqual(payload_a["reconcile_blocked_reason"], "")
        self.assertEqual(payload_a["reconcile_blocked_reasons"], [])
        self.assertIn(payload_a["reconcile_status"], RECONCILE_STATUSES)
        self.assertIn(payload_a["reconcile_decision"], RECONCILE_DECISIONS)
        self.assertIn(payload_a["reconcile_alignment_status"], RECONCILE_ALIGNMENT_STATUSES)
        self.assertIn(payload_a["reconcile_transport_status"], RECONCILE_TRANSPORT_STATUSES)

    def test_reconcile_contract_degrades_to_waiting_for_truth_when_sources_missing(self) -> None:
        payload = build_reconcile_contract_surface(
            run_id="job-reconcile-missing",
            objective_contract_payload={},
            completion_contract_payload={},
            approval_transport_payload={},
            run_state_payload={},
            artifact_presence={},
        )

        self.assertEqual(payload["reconcile_status"], "waiting_for_truth")
        self.assertEqual(payload["reconcile_decision"], "wait_for_truth")
        self.assertEqual(payload["reconcile_alignment_status"], "insufficient_truth")
        self.assertNotEqual(payload["reconcile_status"], "inconsistent")
        self.assertTrue(payload["reconcile_waiting_on_truth"])
        self.assertTrue(payload["reconcile_blocked_reasons"])

    def test_reconcile_contract_detects_objective_completion_mismatch(self) -> None:
        payload = build_reconcile_contract_surface(
            run_id="job-reconcile-objective-mismatch",
            objective_contract_payload={"objective_status": "underspecified"},
            completion_contract_payload={
                "completion_status": "done_and_safely_closed",
                "done_status": "done",
                "safe_closure_status": "safely_closed",
            },
            approval_transport_payload={
                "approval_status": "approved",
                "approval_transport_status": "actionable",
                "approval_present": True,
            },
            run_state_payload={
                "objective_contract_status": "underspecified",
                "completion_status": "done_and_safely_closed",
                "approval_status": "approved",
                "lifecycle_closure_status": "safely_closed",
                "lifecycle_safely_closed": True,
            },
            artifact_presence={
                "objective_contract.json": True,
                "completion_contract.json": True,
                "approval_transport.json": True,
                "run_state.json": True,
            },
        )

        self.assertEqual(payload["reconcile_status"], "inconsistent")
        self.assertEqual(payload["reconcile_primary_mismatch"], "objective_completion_conflict")

    def test_reconcile_contract_detects_completion_lifecycle_mismatch(self) -> None:
        payload = build_reconcile_contract_surface(
            run_id="job-reconcile-lifecycle-mismatch",
            objective_contract_payload={"objective_status": "complete"},
            completion_contract_payload={
                "completion_status": "done_and_safely_closed",
                "done_status": "done",
                "safe_closure_status": "safely_closed",
            },
            approval_transport_payload={
                "approval_status": "approved",
                "approval_transport_status": "actionable",
                "approval_present": True,
            },
            run_state_payload={
                "objective_contract_status": "complete",
                "completion_status": "done_and_safely_closed",
                "approval_status": "approved",
                "lifecycle_closure_status": "stopped_manual_only",
                "lifecycle_safely_closed": False,
                "lifecycle_manual_required": True,
            },
            artifact_presence={
                "objective_contract.json": True,
                "completion_contract.json": True,
                "approval_transport.json": True,
                "run_state.json": True,
            },
        )

        self.assertEqual(payload["reconcile_status"], "inconsistent")
        self.assertEqual(payload["reconcile_primary_mismatch"], "completion_lifecycle_conflict")

    def test_reconcile_contract_detects_approval_completion_mismatch(self) -> None:
        payload = build_reconcile_contract_surface(
            run_id="job-reconcile-approval-mismatch",
            objective_contract_payload={"objective_status": "complete"},
            completion_contract_payload={
                "completion_status": "execution_complete_not_accepted",
                "done_status": "not_done",
                "safe_closure_status": "not_safely_closed",
            },
            approval_transport_payload={
                "approval_status": "approved",
                "approval_decision": "approve",
                "approval_transport_status": "actionable",
                "approval_present": True,
            },
            run_state_payload={
                "objective_contract_status": "complete",
                "completion_status": "execution_complete_not_accepted",
                "approval_status": "approved",
                "lifecycle_closure_status": "execution_complete_not_closed",
                "lifecycle_safely_closed": False,
            },
            artifact_presence={
                "objective_contract.json": True,
                "completion_contract.json": True,
                "approval_transport.json": True,
                "run_state.json": True,
            },
        )

        self.assertEqual(payload["reconcile_status"], "inconsistent")
        self.assertEqual(payload["reconcile_primary_mismatch"], "approval_completion_conflict")

    def test_reconcile_waiting_state_is_distinct_from_inconsistent_state(self) -> None:
        waiting = build_reconcile_contract_surface(
            run_id="job-reconcile-waiting",
            objective_contract_payload={},
            completion_contract_payload={},
            approval_transport_payload={},
            run_state_payload={},
            artifact_presence={},
        )
        inconsistent = build_reconcile_contract_surface(
            run_id="job-reconcile-inconsistent",
            objective_contract_payload={"objective_status": "underspecified"},
            completion_contract_payload={
                "completion_status": "done_and_safely_closed",
                "done_status": "done",
                "safe_closure_status": "safely_closed",
            },
            approval_transport_payload={
                "approval_status": "approved",
                "approval_transport_status": "actionable",
                "approval_present": True,
            },
            run_state_payload={
                "objective_contract_status": "underspecified",
                "completion_status": "done_and_safely_closed",
                "approval_status": "approved",
                "lifecycle_closure_status": "safely_closed",
                "lifecycle_safely_closed": True,
            },
            artifact_presence={
                "objective_contract.json": True,
                "completion_contract.json": True,
                "approval_transport.json": True,
                "run_state.json": True,
            },
        )

        self.assertEqual(waiting["reconcile_status"], "waiting_for_truth")
        self.assertEqual(inconsistent["reconcile_status"], "inconsistent")

    def test_reconcile_run_state_summary_surface_is_compact_and_enum_safe(self) -> None:
        compact = build_reconcile_run_state_summary_surface(
            {
                "reconcile_status": "bad_status",
                "reconcile_decision": "bad_decision",
                "reconcile_alignment_status": "bad_alignment",
                "reconcile_primary_mismatch": "truth_pending",
                "reconcile_waiting_on_truth": True,
                "reconcile_manual_required": True,
                "reconcile_replan_required": False,
                "reconcile_blocked_reasons": ["not_summary_safe"],
            }
        )

        self.assertEqual(set(compact.keys()), set(RECONCILE_RUN_STATE_SUMMARY_SAFE_FIELDS))
        self.assertIn(compact["reconcile_status"], RECONCILE_STATUSES)
        self.assertIn(compact["reconcile_decision"], RECONCILE_DECISIONS)
        self.assertIn(compact["reconcile_alignment_status"], RECONCILE_ALIGNMENT_STATUSES)

    def test_repair_suggestion_contract_is_deterministic_when_truth_is_aligned(self) -> None:
        payload_a = build_repair_suggestion_contract_surface(
            run_id="job-repair-1",
            objective_contract_payload={
                "objective_id": "objective-repair-1",
                "objective_status": "complete",
            },
            completion_contract_payload={
                "objective_id": "objective-repair-1",
                "completion_status": "done_and_safely_closed",
                "done_status": "done",
                "safe_closure_status": "safely_closed",
                "closure_decision": "close",
            },
            approval_transport_payload={
                "objective_id": "objective-repair-1",
                "approval_status": "approved",
                "approval_transport_status": "actionable",
                "approval_required": False,
            },
            reconcile_contract_payload={
                "objective_id": "objective-repair-1",
                "reconcile_status": "aligned",
                "reconcile_decision": "aligned_no_action",
            },
            run_state_payload={
                "objective_contract_present": True,
                "completion_contract_present": True,
                "approval_transport_present": True,
                "reconcile_contract_present": True,
                "lifecycle_closure_status": "safely_closed",
                "lifecycle_safely_closed": True,
                "lifecycle_manual_required": False,
                "lifecycle_replan_required": False,
                "manual_intervention_required": False,
            },
            artifact_presence={
                "objective_contract.json": True,
                "completion_contract.json": True,
                "approval_transport.json": True,
                "reconcile_contract.json": True,
                "run_state.json": True,
            },
        )
        payload_b = build_repair_suggestion_contract_surface(
            run_id="job-repair-1",
            objective_contract_payload={
                "objective_id": "objective-repair-1",
                "objective_status": "complete",
            },
            completion_contract_payload={
                "objective_id": "objective-repair-1",
                "completion_status": "done_and_safely_closed",
                "done_status": "done",
                "safe_closure_status": "safely_closed",
                "closure_decision": "close",
            },
            approval_transport_payload={
                "objective_id": "objective-repair-1",
                "approval_status": "approved",
                "approval_transport_status": "actionable",
                "approval_required": False,
            },
            reconcile_contract_payload={
                "objective_id": "objective-repair-1",
                "reconcile_status": "aligned",
                "reconcile_decision": "aligned_no_action",
            },
            run_state_payload={
                "objective_contract_present": True,
                "completion_contract_present": True,
                "approval_transport_present": True,
                "reconcile_contract_present": True,
                "lifecycle_closure_status": "safely_closed",
                "lifecycle_safely_closed": True,
                "lifecycle_manual_required": False,
                "lifecycle_replan_required": False,
                "manual_intervention_required": False,
            },
            artifact_presence={
                "objective_contract.json": True,
                "completion_contract.json": True,
                "approval_transport.json": True,
                "reconcile_contract.json": True,
                "run_state.json": True,
            },
        )

        self.assertEqual(payload_a, payload_b)
        self.assertEqual(payload_a["repair_suggestion_status"], "no_repair_needed")
        self.assertEqual(payload_a["repair_suggestion_decision"], "no_action")
        self.assertEqual(payload_a["repair_suggestion_class"], "no_gap")
        self.assertEqual(payload_a["repair_primary_reason"], "no_reason")
        self.assertEqual(payload_a["repair_reason_codes"], ["no_reason"])
        self.assertFalse(payload_a["repair_execution_recommended"])
        self.assertIn(payload_a["repair_suggestion_status"], REPAIR_SUGGESTION_STATUSES)
        self.assertIn(payload_a["repair_suggestion_decision"], REPAIR_SUGGESTION_DECISIONS)
        self.assertIn(payload_a["repair_suggestion_class"], REPAIR_SUGGESTION_CLASSES)
        self.assertIn(payload_a["repair_suggestion_priority"], REPAIR_SUGGESTION_PRIORITIES)
        self.assertIn(payload_a["repair_suggestion_confidence"], REPAIR_SUGGESTION_CONFIDENCE_LEVELS)
        self.assertIn(payload_a["repair_target_surface"], REPAIR_TARGET_SURFACES)
        self.assertIn(payload_a["repair_precondition_status"], REPAIR_PRECONDITION_STATUSES)

    def test_repair_suggestion_waiting_truth_prefers_gather_truth(self) -> None:
        payload = build_repair_suggestion_contract_surface(
            run_id="job-repair-wait",
            objective_contract_payload={},
            completion_contract_payload={},
            approval_transport_payload={},
            reconcile_contract_payload={"reconcile_status": "waiting_for_truth"},
            run_state_payload={},
            artifact_presence={},
        )

        self.assertEqual(payload["repair_suggestion_decision"], "gather_truth")
        self.assertTrue(payload["repair_truth_gathering_required"])
        self.assertIn("missing_upstream_truth", payload["repair_reason_codes"])
        self.assertFalse(payload["repair_execution_recommended"])

    def test_repair_suggestion_blocked_manual_required_prefers_manual_review(self) -> None:
        payload = build_repair_suggestion_contract_surface(
            run_id="job-repair-manual",
            objective_contract_payload={"objective_status": "underspecified"},
            completion_contract_payload={"completion_status": "replan_before_closure", "done_status": "not_done"},
            approval_transport_payload={"approval_status": "deferred", "approval_transport_status": "non_actionable"},
            reconcile_contract_payload={
                "reconcile_status": "blocked",
                "reconcile_manual_required": True,
                "reconcile_replan_required": False,
            },
            run_state_payload={
                "lifecycle_closure_status": "stopped_manual_only",
                "lifecycle_safely_closed": False,
                "manual_intervention_required": True,
                "lifecycle_manual_required": True,
            },
            artifact_presence={
                "objective_contract.json": True,
                "completion_contract.json": True,
                "approval_transport.json": True,
                "reconcile_contract.json": True,
                "run_state.json": True,
            },
        )

        self.assertEqual(payload["repair_suggestion_decision"], "manual_review")
        self.assertEqual(payload["repair_suggestion_status"], "blocked")
        self.assertTrue(payload["repair_manual_required"])
        self.assertIn("manual_intervention_required", payload["repair_reason_codes"])

    def test_repair_suggestion_replan_required_prefers_request_replan(self) -> None:
        payload = build_repair_suggestion_contract_surface(
            run_id="job-repair-replan",
            objective_contract_payload={"objective_status": "complete"},
            completion_contract_payload={
                "completion_status": "replan_before_closure",
                "done_status": "not_done",
                "completion_replan_required": True,
            },
            approval_transport_payload={"approval_status": "deferred", "approval_transport_status": "non_actionable"},
            reconcile_contract_payload={"reconcile_status": "blocked", "reconcile_replan_required": True},
            run_state_payload={
                "lifecycle_closure_status": "stopped_replan_required",
                "lifecycle_safely_closed": False,
                "lifecycle_replan_required": True,
            },
            artifact_presence={
                "objective_contract.json": True,
                "completion_contract.json": True,
                "approval_transport.json": True,
                "reconcile_contract.json": True,
                "run_state.json": True,
            },
        )

        self.assertEqual(payload["repair_suggestion_decision"], "request_replan")
        self.assertTrue(payload["repair_replan_required"])
        self.assertIn("replan_required", payload["repair_reason_codes"])

    def test_repair_suggestion_done_but_not_closed_prefers_closure_followup(self) -> None:
        payload = build_repair_suggestion_contract_surface(
            run_id="job-repair-closure",
            objective_contract_payload={"objective_status": "complete"},
            completion_contract_payload={
                "completion_status": "done_and_safely_closed",
                "done_status": "done",
                "safe_closure_status": "safely_closed",
            },
            approval_transport_payload={"approval_status": "deferred", "approval_transport_status": "non_actionable"},
            reconcile_contract_payload={"reconcile_status": "partially_aligned"},
            run_state_payload={
                "lifecycle_closure_status": "execution_complete_not_closed",
                "lifecycle_safely_closed": False,
                "lifecycle_manual_required": False,
                "lifecycle_replan_required": False,
            },
            artifact_presence={
                "objective_contract.json": True,
                "completion_contract.json": True,
                "approval_transport.json": True,
                "reconcile_contract.json": True,
                "run_state.json": True,
            },
        )

        self.assertEqual(payload["repair_suggestion_decision"], "closure_followup")
        self.assertTrue(payload["repair_closure_followup_required"])
        self.assertIn("closure_followup_required", payload["repair_reason_codes"])

    def test_repair_suggestion_approval_conflict_prefers_manual_review(self) -> None:
        payload = build_repair_suggestion_contract_surface(
            run_id="job-repair-approval-conflict",
            objective_contract_payload={"objective_status": "complete"},
            completion_contract_payload={
                "completion_status": "execution_complete_not_accepted",
                "done_status": "not_done",
                "safe_closure_status": "not_safely_closed",
            },
            approval_transport_payload={"approval_status": "approved", "approval_transport_status": "actionable"},
            reconcile_contract_payload={"reconcile_status": "inconsistent"},
            run_state_payload={
                "lifecycle_closure_status": "execution_complete_not_closed",
                "lifecycle_safely_closed": False,
                "manual_intervention_required": True,
            },
            artifact_presence={
                "objective_contract.json": True,
                "completion_contract.json": True,
                "approval_transport.json": True,
                "reconcile_contract.json": True,
                "run_state.json": True,
            },
        )

        self.assertEqual(payload["repair_suggestion_decision"], "manual_review")
        self.assertEqual(payload["repair_suggestion_class"], "approval_conflict")
        self.assertIn("approval_conflict", payload["repair_reason_codes"])

    def test_repair_suggestion_run_state_summary_surface_is_compact_and_enum_safe(self) -> None:
        compact = build_repair_suggestion_run_state_summary_surface(
            {
                "repair_suggestion_status": "bad_status",
                "repair_suggestion_decision": "bad_decision",
                "repair_suggestion_class": "bad_class",
                "repair_suggestion_priority": "bad_priority",
                "repair_suggestion_confidence": "bad_confidence",
                "repair_primary_reason": "bad_reason",
                "repair_manual_required": True,
                "repair_replan_required": False,
                "repair_truth_gathering_required": True,
                "repair_reason_codes": ["not_summary_safe"],
            }
        )

        self.assertEqual(set(compact.keys()), set(REPAIR_SUGGESTION_RUN_STATE_SUMMARY_SAFE_FIELDS))
        self.assertIn(compact["repair_suggestion_status"], REPAIR_SUGGESTION_STATUSES)
        self.assertIn(compact["repair_suggestion_decision"], REPAIR_SUGGESTION_DECISIONS)
        self.assertIn(compact["repair_suggestion_class"], REPAIR_SUGGESTION_CLASSES)
        self.assertIn(compact["repair_suggestion_priority"], REPAIR_SUGGESTION_PRIORITIES)
        self.assertIn(compact["repair_suggestion_confidence"], REPAIR_SUGGESTION_CONFIDENCE_LEVELS)
        self.assertIn(compact["repair_primary_reason"], REPAIR_REASON_CODES)

    def test_repair_plan_transport_is_deterministic_when_no_repair_is_needed(self) -> None:
        payload_a = build_repair_plan_transport_surface(
            run_id="job-repair-plan-1",
            objective_contract_payload={
                "objective_id": "objective-repair-plan-1",
                "objective_status": "complete",
            },
            completion_contract_payload={
                "objective_id": "objective-repair-plan-1",
                "completion_status": "done_and_safely_closed",
                "done_status": "done",
                "safe_closure_status": "safely_closed",
                "closure_decision": "close",
            },
            approval_transport_payload={
                "objective_id": "objective-repair-plan-1",
                "approval_status": "approved",
                "approval_transport_status": "actionable",
                "approval_required": False,
            },
            reconcile_contract_payload={
                "objective_id": "objective-repair-plan-1",
                "reconcile_status": "aligned",
                "reconcile_decision": "aligned_no_action",
            },
            repair_suggestion_contract_payload={
                "objective_id": "objective-repair-plan-1",
                "repair_suggestion_status": "no_repair_needed",
                "repair_suggestion_decision": "no_action",
                "repair_suggestion_class": "no_gap",
                "repair_primary_reason": "no_reason",
                "repair_reason_codes": ["no_reason"],
                "repair_target_surface": "none",
            },
            run_state_payload={
                "objective_contract_present": True,
                "completion_contract_present": True,
                "approval_transport_present": True,
                "reconcile_contract_present": True,
                "repair_suggestion_contract_present": True,
                "lifecycle_closure_status": "safely_closed",
                "lifecycle_safely_closed": True,
            },
            artifact_presence={
                "objective_contract.json": True,
                "completion_contract.json": True,
                "approval_transport.json": True,
                "reconcile_contract.json": True,
                "repair_suggestion_contract.json": True,
                "run_state.json": True,
            },
        )
        payload_b = build_repair_plan_transport_surface(
            run_id="job-repair-plan-1",
            objective_contract_payload={
                "objective_id": "objective-repair-plan-1",
                "objective_status": "complete",
            },
            completion_contract_payload={
                "objective_id": "objective-repair-plan-1",
                "completion_status": "done_and_safely_closed",
                "done_status": "done",
                "safe_closure_status": "safely_closed",
                "closure_decision": "close",
            },
            approval_transport_payload={
                "objective_id": "objective-repair-plan-1",
                "approval_status": "approved",
                "approval_transport_status": "actionable",
                "approval_required": False,
            },
            reconcile_contract_payload={
                "objective_id": "objective-repair-plan-1",
                "reconcile_status": "aligned",
                "reconcile_decision": "aligned_no_action",
            },
            repair_suggestion_contract_payload={
                "objective_id": "objective-repair-plan-1",
                "repair_suggestion_status": "no_repair_needed",
                "repair_suggestion_decision": "no_action",
                "repair_suggestion_class": "no_gap",
                "repair_primary_reason": "no_reason",
                "repair_reason_codes": ["no_reason"],
                "repair_target_surface": "none",
            },
            run_state_payload={
                "objective_contract_present": True,
                "completion_contract_present": True,
                "approval_transport_present": True,
                "reconcile_contract_present": True,
                "repair_suggestion_contract_present": True,
                "lifecycle_closure_status": "safely_closed",
                "lifecycle_safely_closed": True,
            },
            artifact_presence={
                "objective_contract.json": True,
                "completion_contract.json": True,
                "approval_transport.json": True,
                "reconcile_contract.json": True,
                "repair_suggestion_contract.json": True,
                "run_state.json": True,
            },
        )

        self.assertEqual(payload_a, payload_b)
        self.assertEqual(payload_a["repair_plan_status"], "not_needed")
        self.assertEqual(payload_a["repair_plan_decision"], "no_plan")
        self.assertEqual(payload_a["repair_plan_class"], "no_plan")
        self.assertEqual(payload_a["repair_plan_candidate_action"], "no_action")
        self.assertEqual(payload_a["repair_plan_reason_codes"], ["no_reason"])
        self.assertEqual(payload_a["repair_plan_primary_reason"], "no_reason")
        self.assertFalse(payload_a["repair_plan_execution_ready"])
        self.assertIn(payload_a["repair_plan_status"], REPAIR_PLAN_STATUSES)
        self.assertIn(payload_a["repair_plan_decision"], REPAIR_PLAN_DECISIONS)
        self.assertIn(payload_a["repair_plan_class"], REPAIR_PLAN_CLASSES)
        self.assertIn(payload_a["repair_plan_priority"], REPAIR_PLAN_PRIORITIES)
        self.assertIn(payload_a["repair_plan_confidence"], REPAIR_PLAN_CONFIDENCE_LEVELS)
        self.assertIn(payload_a["repair_plan_target_surface"], REPAIR_PLAN_TARGET_SURFACES)
        self.assertIn(payload_a["repair_plan_candidate_action"], REPAIR_PLAN_CANDIDATE_ACTIONS)
        self.assertIn(payload_a["repair_plan_precondition_status"], REPAIR_PLAN_PRECONDITION_STATUSES)
        self.assertIn(payload_a["repair_plan_source_status"], REPAIR_PLAN_SOURCE_STATUSES)

    def test_repair_plan_waiting_truth_suggestion_yields_truth_gathering_plan(self) -> None:
        payload = build_repair_plan_transport_surface(
            run_id="job-repair-plan-wait",
            objective_contract_payload={"objective_status": "underspecified"},
            completion_contract_payload={"completion_status": "not_done", "done_status": "not_done"},
            approval_transport_payload={"approval_status": "deferred", "approval_transport_status": "non_actionable"},
            reconcile_contract_payload={"reconcile_status": "waiting_for_truth", "reconcile_decision": "wait_for_truth"},
            repair_suggestion_contract_payload={
                "repair_suggestion_status": "suggested",
                "repair_suggestion_decision": "gather_truth",
                "repair_suggestion_class": "truth_gap",
                "repair_primary_reason": "reconcile_waiting_for_truth",
                "repair_reason_codes": ["reconcile_waiting_for_truth"],
                "repair_truth_gathering_required": True,
                "repair_target_surface": "cross_surface",
            },
            run_state_payload={"repair_suggestion_contract_present": True, "lifecycle_closure_status": "stopped_resumable"},
            artifact_presence={
                "objective_contract.json": True,
                "completion_contract.json": True,
                "approval_transport.json": True,
                "reconcile_contract.json": True,
                "repair_suggestion_contract.json": True,
                "run_state.json": True,
            },
        )

        self.assertEqual(payload["repair_plan_status"], "available")
        self.assertEqual(payload["repair_plan_decision"], "prepare_truth_gathering_plan")
        self.assertEqual(payload["repair_plan_class"], "truth_gathering_plan")
        self.assertEqual(payload["repair_plan_candidate_action"], "gather_missing_truth")
        self.assertTrue(payload["repair_plan_truth_gathering_required"])
        self.assertFalse(payload["repair_plan_execution_ready"])

    def test_repair_plan_manual_review_suggestion_yields_manual_review_plan(self) -> None:
        payload = build_repair_plan_transport_surface(
            run_id="job-repair-plan-manual",
            objective_contract_payload={"objective_status": "complete"},
            completion_contract_payload={"completion_status": "replan_before_closure", "done_status": "not_done"},
            approval_transport_payload={"approval_status": "deferred", "approval_transport_status": "non_actionable"},
            reconcile_contract_payload={"reconcile_status": "blocked", "reconcile_decision": "manual_review"},
            repair_suggestion_contract_payload={
                "repair_suggestion_status": "suggested",
                "repair_suggestion_decision": "manual_review",
                "repair_suggestion_class": "approval_conflict",
                "repair_primary_reason": "manual_intervention_required",
                "repair_reason_codes": ["manual_intervention_required"],
                "repair_manual_required": True,
                "repair_target_surface": "approval",
            },
            run_state_payload={"repair_suggestion_contract_present": True, "manual_intervention_required": True},
            artifact_presence={
                "objective_contract.json": True,
                "completion_contract.json": True,
                "approval_transport.json": True,
                "reconcile_contract.json": True,
                "repair_suggestion_contract.json": True,
                "run_state.json": True,
            },
        )

        self.assertEqual(payload["repair_plan_status"], "available")
        self.assertEqual(payload["repair_plan_decision"], "prepare_manual_review_plan")
        self.assertEqual(payload["repair_plan_class"], "manual_review_plan")
        self.assertEqual(payload["repair_plan_candidate_action"], "request_manual_review")
        self.assertEqual(payload["repair_plan_priority"], "high")
        self.assertTrue(payload["repair_plan_manual_required"])

    def test_repair_plan_replan_suggestion_yields_replan_plan(self) -> None:
        payload = build_repair_plan_transport_surface(
            run_id="job-repair-plan-replan",
            objective_contract_payload={"objective_status": "underspecified"},
            completion_contract_payload={"completion_status": "replan_before_closure", "done_status": "not_done"},
            approval_transport_payload={"approval_status": "deferred", "approval_transport_status": "non_actionable"},
            reconcile_contract_payload={"reconcile_status": "blocked", "reconcile_decision": "request_replan"},
            repair_suggestion_contract_payload={
                "repair_suggestion_status": "suggested",
                "repair_suggestion_decision": "request_replan",
                "repair_suggestion_class": "objective_gap",
                "repair_primary_reason": "replan_required",
                "repair_reason_codes": ["replan_required"],
                "repair_replan_required": True,
                "repair_target_surface": "objective",
            },
            run_state_payload={"repair_suggestion_contract_present": True, "policy_replan_required": True},
            artifact_presence={
                "objective_contract.json": True,
                "completion_contract.json": True,
                "approval_transport.json": True,
                "reconcile_contract.json": True,
                "repair_suggestion_contract.json": True,
                "run_state.json": True,
            },
        )

        self.assertEqual(payload["repair_plan_status"], "available")
        self.assertEqual(payload["repair_plan_decision"], "prepare_replan_plan")
        self.assertEqual(payload["repair_plan_class"], "replan_plan")
        self.assertEqual(payload["repair_plan_candidate_action"], "request_replan")
        self.assertEqual(payload["repair_plan_priority"], "high")
        self.assertTrue(payload["repair_plan_replan_required"])

    def test_repair_plan_closure_followup_suggestion_yields_closure_followup_plan(self) -> None:
        payload = build_repair_plan_transport_surface(
            run_id="job-repair-plan-closure",
            objective_contract_payload={"objective_status": "complete"},
            completion_contract_payload={
                "completion_status": "done_and_safely_closed",
                "done_status": "done",
                "safe_closure_status": "safely_closed",
            },
            approval_transport_payload={"approval_status": "deferred", "approval_transport_status": "non_actionable"},
            reconcile_contract_payload={"reconcile_status": "blocked", "reconcile_decision": "hold"},
            repair_suggestion_contract_payload={
                "repair_suggestion_status": "suggested",
                "repair_suggestion_decision": "closure_followup",
                "repair_suggestion_class": "completion_closure_gap",
                "repair_primary_reason": "closure_followup_required",
                "repair_reason_codes": ["closure_followup_required"],
                "repair_closure_followup_required": True,
                "repair_target_surface": "lifecycle",
            },
            run_state_payload={
                "repair_suggestion_contract_present": True,
                "lifecycle_closure_status": "execution_complete_not_closed",
                "lifecycle_safely_closed": False,
            },
            artifact_presence={
                "objective_contract.json": True,
                "completion_contract.json": True,
                "approval_transport.json": True,
                "reconcile_contract.json": True,
                "repair_suggestion_contract.json": True,
                "run_state.json": True,
            },
        )

        self.assertEqual(payload["repair_plan_status"], "available")
        self.assertEqual(payload["repair_plan_decision"], "prepare_closure_followup_plan")
        self.assertEqual(payload["repair_plan_class"], "closure_followup_plan")
        self.assertEqual(payload["repair_plan_candidate_action"], "request_closure_followup")
        self.assertEqual(payload["repair_plan_priority"], "high")
        self.assertTrue(payload["repair_plan_closure_followup_required"])

    def test_repair_plan_priority_rules_cover_high_medium_and_low(self) -> None:
        high = build_repair_plan_transport_surface(
            run_id="job-repair-plan-priority-high",
            objective_contract_payload={"objective_status": "complete"},
            completion_contract_payload={"completion_status": "replan_before_closure", "done_status": "not_done"},
            approval_transport_payload={"approval_status": "deferred", "approval_transport_status": "non_actionable"},
            reconcile_contract_payload={"reconcile_status": "blocked", "reconcile_decision": "request_replan"},
            repair_suggestion_contract_payload={
                "repair_suggestion_status": "suggested",
                "repair_suggestion_decision": "request_replan",
                "repair_suggestion_class": "objective_gap",
                "repair_primary_reason": "replan_required",
                "repair_reason_codes": ["replan_required"],
                "repair_replan_required": True,
            },
            run_state_payload={"repair_suggestion_contract_present": True},
            artifact_presence={
                "objective_contract.json": True,
                "completion_contract.json": True,
                "approval_transport.json": True,
                "reconcile_contract.json": True,
                "repair_suggestion_contract.json": True,
                "run_state.json": True,
            },
        )
        medium = build_repair_plan_transport_surface(
            run_id="job-repair-plan-priority-medium",
            objective_contract_payload={"objective_status": "underspecified"},
            completion_contract_payload={"completion_status": "not_done", "done_status": "not_done"},
            approval_transport_payload={"approval_status": "deferred", "approval_transport_status": "non_actionable"},
            reconcile_contract_payload={"reconcile_status": "waiting_for_truth", "reconcile_decision": "wait_for_truth"},
            repair_suggestion_contract_payload={
                "repair_suggestion_status": "suggested",
                "repair_suggestion_decision": "gather_truth",
                "repair_suggestion_class": "truth_gap",
                "repair_primary_reason": "reconcile_waiting_for_truth",
                "repair_reason_codes": ["reconcile_waiting_for_truth"],
                "repair_truth_gathering_required": True,
            },
            run_state_payload={"repair_suggestion_contract_present": True},
            artifact_presence={
                "objective_contract.json": True,
                "completion_contract.json": True,
                "approval_transport.json": True,
                "reconcile_contract.json": True,
                "repair_suggestion_contract.json": True,
                "run_state.json": True,
            },
        )
        low = build_repair_plan_transport_surface(
            run_id="job-repair-plan-priority-low",
            objective_contract_payload={"objective_status": "complete"},
            completion_contract_payload={
                "completion_status": "done_and_safely_closed",
                "done_status": "done",
                "safe_closure_status": "safely_closed",
            },
            approval_transport_payload={"approval_status": "approved", "approval_transport_status": "actionable"},
            reconcile_contract_payload={"reconcile_status": "aligned", "reconcile_decision": "aligned_no_action"},
            repair_suggestion_contract_payload={
                "repair_suggestion_status": "no_repair_needed",
                "repair_suggestion_decision": "no_action",
                "repair_primary_reason": "no_reason",
                "repair_reason_codes": ["no_reason"],
            },
            run_state_payload={"repair_suggestion_contract_present": True, "lifecycle_closure_status": "safely_closed"},
            artifact_presence={
                "objective_contract.json": True,
                "completion_contract.json": True,
                "approval_transport.json": True,
                "reconcile_contract.json": True,
                "repair_suggestion_contract.json": True,
                "run_state.json": True,
            },
        )

        self.assertEqual(high["repair_plan_priority"], "high")
        self.assertEqual(medium["repair_plan_priority"], "medium")
        self.assertEqual(low["repair_plan_priority"], "low")

    def test_repair_plan_run_state_summary_surface_is_compact_and_enum_safe(self) -> None:
        compact = build_repair_plan_transport_run_state_summary_surface(
            {
                "repair_plan_status": "bad_status",
                "repair_plan_decision": "bad_decision",
                "repair_plan_class": "bad_class",
                "repair_plan_priority": "bad_priority",
                "repair_plan_confidence": "bad_confidence",
                "repair_plan_target_surface": "bad_surface",
                "repair_plan_candidate_action": "bad_action",
                "repair_plan_primary_reason": "bad_reason",
                "repair_plan_manual_required": True,
                "repair_plan_replan_required": False,
                "repair_plan_truth_gathering_required": True,
                "repair_plan_reason_codes": ["not_summary_safe"],
            }
        )

        self.assertEqual(set(compact.keys()), set(REPAIR_PLAN_TRANSPORT_RUN_STATE_SUMMARY_SAFE_FIELDS))
        self.assertIn(compact["repair_plan_status"], REPAIR_PLAN_STATUSES)
        self.assertIn(compact["repair_plan_decision"], REPAIR_PLAN_DECISIONS)
        self.assertIn(compact["repair_plan_class"], REPAIR_PLAN_CLASSES)
        self.assertIn(compact["repair_plan_priority"], REPAIR_PLAN_PRIORITIES)
        self.assertIn(compact["repair_plan_confidence"], REPAIR_PLAN_CONFIDENCE_LEVELS)
        self.assertIn(compact["repair_plan_target_surface"], REPAIR_PLAN_TARGET_SURFACES)
        self.assertIn(compact["repair_plan_candidate_action"], REPAIR_PLAN_CANDIDATE_ACTIONS)
        self.assertIn(compact["repair_plan_primary_reason"], REPAIR_PLAN_REASON_CODES)

    def test_repair_approval_binding_is_deterministic_when_plan_not_needed(self) -> None:
        kwargs = {
            "run_id": "job-repair-binding-not-needed",
            "objective_contract_payload": {
                "objective_id": "objective-repair-binding-not-needed",
                "objective_status": "complete",
            },
            "completion_contract_payload": {
                "objective_id": "objective-repair-binding-not-needed",
                "completion_status": "done_and_safely_closed",
                "closure_decision": "close",
            },
            "approval_transport_payload": {
                "objective_id": "objective-repair-binding-not-needed",
                "approval_status": "absent",
                "approval_decision": "none",
                "approval_transport_status": "missing",
            },
            "reconcile_contract_payload": {"reconcile_status": "aligned"},
            "repair_suggestion_contract_payload": {"repair_suggestion_status": "no_repair_needed"},
            "repair_plan_transport_payload": {
                "repair_plan_status": "not_needed",
                "repair_plan_decision": "no_plan",
                "repair_plan_candidate_action": "no_action",
                "repair_plan_primary_reason": "no_reason",
            },
            "run_state_payload": {
                "repair_plan_transport_present": True,
                "approval_transport_present": True,
            },
            "artifact_presence": {
                "repair_plan_transport.json": True,
                "approval_transport.json": True,
                "run_state.json": True,
            },
        }
        payload_a = build_repair_approval_binding_surface(**kwargs)
        payload_b = build_repair_approval_binding_surface(**kwargs)

        self.assertEqual(payload_a, payload_b)
        self.assertEqual(payload_a["repair_approval_binding_status"], "not_applicable")
        self.assertEqual(payload_a["repair_approval_binding_decision"], "no_binding")
        self.assertEqual(payload_a["repair_approval_binding_scope"], "none")
        self.assertEqual(payload_a["repair_approval_binding_reason_codes"], ["no_reason"])
        self.assertEqual(payload_a["repair_approval_binding_primary_reason"], "no_reason")
        self.assertFalse(payload_a["repair_approval_binding_execution_authorized"])
        self.assertIn(payload_a["repair_approval_binding_status"], REPAIR_APPROVAL_BINDING_STATUSES)
        self.assertIn(payload_a["repair_approval_binding_decision"], REPAIR_APPROVAL_BINDING_DECISIONS)
        self.assertIn(payload_a["repair_approval_binding_scope"], REPAIR_APPROVAL_BINDING_SCOPES)
        self.assertIn(payload_a["repair_approval_binding_validity"], REPAIR_APPROVAL_BINDING_VALIDITIES)
        self.assertIn(
            payload_a["repair_approval_binding_compatibility_status"],
            REPAIR_APPROVAL_BINDING_COMPATIBILITY_STATUSES,
        )
        self.assertIn(
            payload_a["repair_approval_binding_source_status"],
            REPAIR_APPROVAL_BINDING_SOURCE_STATUSES,
        )

    def test_repair_approval_binding_available_plan_without_approval_is_missing_unbound(self) -> None:
        payload = build_repair_approval_binding_surface(
            run_id="job-repair-binding-missing-approval",
            objective_contract_payload={"objective_status": "underspecified"},
            completion_contract_payload={"completion_status": "replan_before_closure"},
            approval_transport_payload={"approval_status": "absent", "approval_decision": "none"},
            reconcile_contract_payload={"reconcile_status": "blocked"},
            repair_suggestion_contract_payload={"repair_suggestion_status": "suggested"},
            repair_plan_transport_payload={
                "repair_plan_status": "available",
                "repair_plan_decision": "prepare_replan_plan",
                "repair_plan_candidate_action": "request_replan",
                "repair_plan_primary_reason": "replan_required",
                "repair_plan_replan_required": True,
            },
            run_state_payload={
                "repair_plan_transport_present": True,
                "approval_transport_present": True,
            },
            artifact_presence={
                "repair_plan_transport.json": True,
                "approval_transport.json": True,
                "run_state.json": True,
            },
        )

        self.assertEqual(payload["repair_approval_binding_status"], "missing")
        self.assertEqual(payload["repair_approval_binding_decision"], "hold_unbound")
        self.assertEqual(payload["repair_approval_binding_primary_reason"], "missing_approval")
        self.assertFalse(payload["repair_approval_binding_execution_authorized"])

    def test_repair_approval_binding_denied_or_deferred_prevents_bound(self) -> None:
        denied = build_repair_approval_binding_surface(
            run_id="job-repair-binding-denied",
            objective_contract_payload={"objective_status": "complete"},
            completion_contract_payload={"completion_status": "replan_before_closure"},
            approval_transport_payload={
                "approval_status": "denied",
                "approval_decision": "deny",
                "approval_scope": "current_completion_state",
                "approved_action": "hold_for_manual_review",
                "approval_transport_status": "blocked",
            },
            reconcile_contract_payload={"reconcile_status": "blocked"},
            repair_suggestion_contract_payload={"repair_suggestion_status": "suggested"},
            repair_plan_transport_payload={
                "repair_plan_status": "available",
                "repair_plan_decision": "prepare_manual_review_plan",
                "repair_plan_candidate_action": "request_manual_review",
                "repair_plan_primary_reason": "manual_intervention_required",
                "repair_plan_manual_required": True,
            },
            run_state_payload={"repair_plan_transport_present": True, "approval_transport_present": True},
            artifact_presence={
                "repair_plan_transport.json": True,
                "approval_transport.json": True,
                "run_state.json": True,
            },
        )
        deferred = build_repair_approval_binding_surface(
            run_id="job-repair-binding-deferred",
            objective_contract_payload={"objective_status": "complete"},
            completion_contract_payload={"completion_status": "replan_before_closure"},
            approval_transport_payload={
                "approval_status": "deferred",
                "approval_decision": "defer",
                "approval_scope": "current_completion_state",
                "approved_action": "hold_for_manual_review",
                "approval_transport_status": "non_actionable",
            },
            reconcile_contract_payload={"reconcile_status": "blocked"},
            repair_suggestion_contract_payload={"repair_suggestion_status": "suggested"},
            repair_plan_transport_payload={
                "repair_plan_status": "available",
                "repair_plan_decision": "prepare_manual_review_plan",
                "repair_plan_candidate_action": "request_manual_review",
                "repair_plan_primary_reason": "manual_intervention_required",
                "repair_plan_manual_required": True,
            },
            run_state_payload={"repair_plan_transport_present": True, "approval_transport_present": True},
            artifact_presence={
                "repair_plan_transport.json": True,
                "approval_transport.json": True,
                "run_state.json": True,
            },
        )

        self.assertNotEqual(denied["repair_approval_binding_status"], "bound")
        self.assertNotEqual(deferred["repair_approval_binding_status"], "bound")
        self.assertIn("approval_denied", denied["repair_approval_binding_reason_codes"])
        self.assertIn("approval_deferred", deferred["repair_approval_binding_reason_codes"])

    def test_repair_approval_binding_compatible_explicit_approval_can_bind(self) -> None:
        payload = build_repair_approval_binding_surface(
            run_id="job-repair-binding-bound",
            objective_contract_payload={"objective_status": "underspecified"},
            completion_contract_payload={"completion_status": "replan_before_closure"},
            approval_transport_payload={
                "approval_status": "replan_requested",
                "approval_decision": "request_replan",
                "approval_scope": "replan_only",
                "approved_action": "request_replan",
                "approval_transport_status": "actionable",
                "approval_compatibility_status": "compatible",
            },
            reconcile_contract_payload={"reconcile_status": "blocked"},
            repair_suggestion_contract_payload={"repair_suggestion_status": "suggested"},
            repair_plan_transport_payload={
                "repair_plan_status": "available",
                "repair_plan_decision": "prepare_replan_plan",
                "repair_plan_candidate_action": "request_replan",
                "repair_plan_primary_reason": "replan_required",
                "repair_plan_replan_required": True,
            },
            run_state_payload={"repair_plan_transport_present": True, "approval_transport_present": True},
            artifact_presence={
                "repair_plan_transport.json": True,
                "approval_transport.json": True,
                "run_state.json": True,
            },
        )

        self.assertEqual(payload["repair_approval_binding_status"], "bound")
        self.assertEqual(payload["repair_approval_binding_decision"], "bind_for_future_execution")
        self.assertEqual(payload["repair_approval_binding_validity"], "valid")
        self.assertEqual(payload["repair_approval_binding_compatibility_status"], "compatible")
        self.assertFalse(payload["repair_approval_binding_execution_authorized"])

    def test_repair_approval_binding_stale_or_superseded_degrades_validity(self) -> None:
        stale = build_repair_approval_binding_surface(
            run_id="job-repair-binding-stale",
            objective_contract_payload={"objective_status": "complete"},
            completion_contract_payload={"completion_status": "replan_before_closure"},
            approval_transport_payload={
                "approval_status": "approved",
                "approval_decision": "approve",
                "approval_scope": "current_completion_state",
                "approved_action": "hold_for_manual_review",
                "approval_transport_status": "expired",
                "approval_stale": True,
            },
            reconcile_contract_payload={"reconcile_status": "blocked"},
            repair_suggestion_contract_payload={"repair_suggestion_status": "suggested"},
            repair_plan_transport_payload={
                "repair_plan_status": "available",
                "repair_plan_candidate_action": "request_manual_review",
                "repair_plan_manual_required": True,
            },
            run_state_payload={"repair_plan_transport_present": True, "approval_transport_present": True},
            artifact_presence={
                "repair_plan_transport.json": True,
                "approval_transport.json": True,
                "run_state.json": True,
            },
        )
        superseded = build_repair_approval_binding_surface(
            run_id="job-repair-binding-superseded",
            objective_contract_payload={"objective_status": "complete"},
            completion_contract_payload={"completion_status": "replan_before_closure"},
            approval_transport_payload={
                "approval_status": "approved",
                "approval_decision": "approve",
                "approval_scope": "current_completion_state",
                "approved_action": "hold_for_manual_review",
                "approval_transport_status": "superseded",
                "approval_superseded": True,
            },
            reconcile_contract_payload={"reconcile_status": "blocked"},
            repair_suggestion_contract_payload={"repair_suggestion_status": "suggested"},
            repair_plan_transport_payload={
                "repair_plan_status": "available",
                "repair_plan_candidate_action": "request_manual_review",
                "repair_plan_manual_required": True,
            },
            run_state_payload={"repair_plan_transport_present": True, "approval_transport_present": True},
            artifact_presence={
                "repair_plan_transport.json": True,
                "approval_transport.json": True,
                "run_state.json": True,
            },
        )

        self.assertEqual(stale["repair_approval_binding_validity"], "stale")
        self.assertNotEqual(stale["repair_approval_binding_status"], "bound")
        self.assertEqual(superseded["repair_approval_binding_validity"], "superseded")
        self.assertNotEqual(superseded["repair_approval_binding_status"], "bound")

    def test_repair_approval_binding_run_state_summary_surface_is_compact_and_enum_safe(self) -> None:
        compact = build_repair_approval_binding_run_state_summary_surface(
            {
                "repair_approval_binding_status": "bad_status",
                "repair_approval_binding_decision": "bad_decision",
                "repair_approval_binding_scope": "bad_scope",
                "repair_approval_binding_validity": "bad_validity",
                "repair_approval_binding_compatibility_status": "bad_compatibility",
                "repair_approval_binding_primary_reason": "bad_reason",
                "repair_approval_binding_manual_required": True,
                "repair_approval_binding_replan_required": False,
                "repair_approval_binding_truth_gathering_required": True,
                "repair_approval_binding_reason_codes": ["not_summary_safe"],
            }
        )

        self.assertEqual(
            set(compact.keys()),
            set(REPAIR_APPROVAL_BINDING_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertIn(compact["repair_approval_binding_status"], REPAIR_APPROVAL_BINDING_STATUSES)
        self.assertIn(compact["repair_approval_binding_decision"], REPAIR_APPROVAL_BINDING_DECISIONS)
        self.assertIn(compact["repair_approval_binding_scope"], REPAIR_APPROVAL_BINDING_SCOPES)
        self.assertIn(compact["repair_approval_binding_validity"], REPAIR_APPROVAL_BINDING_VALIDITIES)
        self.assertIn(
            compact["repair_approval_binding_compatibility_status"],
            REPAIR_APPROVAL_BINDING_COMPATIBILITY_STATUSES,
        )
        self.assertIn(
            compact["repair_approval_binding_primary_reason"],
            REPAIR_APPROVAL_BINDING_REASON_CODES,
        )

    def test_execution_authorization_gate_is_deterministic_for_eligible_posture(self) -> None:
        kwargs = {
            "run_id": "job-exec-auth-eligible",
            "objective_contract_payload": {
                "objective_id": "objective-exec-auth-eligible",
                "objective_status": "complete",
            },
            "completion_contract_payload": {
                "objective_id": "objective-exec-auth-eligible",
                "completion_status": "done_and_safely_closed",
                "closure_decision": "close",
            },
            "approval_transport_payload": {
                "objective_id": "objective-exec-auth-eligible",
                "approval_status": "approved",
                "approval_decision": "approve",
                "approval_transport_status": "actionable",
            },
            "reconcile_contract_payload": {
                "objective_id": "objective-exec-auth-eligible",
                "reconcile_status": "aligned",
                "reconcile_decision": "aligned_no_action",
            },
            "repair_suggestion_contract_payload": {
                "repair_suggestion_status": "suggested",
            },
            "repair_plan_transport_payload": {
                "repair_plan_status": "available",
                "repair_plan_candidate_action": "request_manual_review",
            },
            "repair_approval_binding_payload": {
                "repair_approval_binding_status": "bound",
                "repair_approval_binding_scope": "current_plan_candidate",
                "repair_approval_binding_validity": "valid",
                "repair_approval_binding_compatibility_status": "compatible",
                "repair_approval_binding_primary_reason": "no_reason",
                "repair_approval_binding_manual_required": False,
                "repair_approval_binding_replan_required": False,
                "repair_approval_binding_truth_gathering_required": False,
            },
            "run_state_payload": {
                "repair_approval_binding_present": True,
                "repair_plan_transport_present": True,
                "approval_transport_present": True,
                "manual_intervention_required": False,
                "policy_manual_required": False,
                "policy_replan_required": False,
                "repair_truth_gathering_required": False,
            },
            "artifact_presence": {
                "objective_contract.json": True,
                "completion_contract.json": True,
                "approval_transport.json": True,
                "reconcile_contract.json": True,
                "repair_suggestion_contract.json": True,
                "repair_plan_transport.json": True,
                "repair_approval_binding.json": True,
                "run_state.json": True,
            },
        }
        payload_a = build_execution_authorization_gate_surface(**kwargs)
        payload_b = build_execution_authorization_gate_surface(**kwargs)

        self.assertEqual(payload_a, payload_b)
        self.assertEqual(payload_a["execution_authorization_status"], "eligible")
        self.assertEqual(payload_a["execution_authorization_decision"], "authorize_future_execution")
        self.assertEqual(payload_a["execution_authorization_primary_reason"], "authorization_ready")
        self.assertFalse(payload_a["execution_authorization_denied"])
        self.assertTrue(payload_a["execution_authorization_eligible"])
        self.assertIn(payload_a["execution_authorization_status"], EXECUTION_AUTHORIZATION_STATUSES)
        self.assertIn(payload_a["execution_authorization_decision"], EXECUTION_AUTHORIZATION_DECISIONS)
        self.assertIn(payload_a["execution_authorization_scope"], EXECUTION_AUTHORIZATION_SCOPES)
        self.assertIn(payload_a["execution_authorization_validity"], EXECUTION_AUTHORIZATION_VALIDITIES)
        self.assertIn(
            payload_a["execution_authorization_confidence"],
            EXECUTION_AUTHORIZATION_CONFIDENCE_LEVELS,
        )
        self.assertIn(
            payload_a["execution_authorization_source_status"],
            EXECUTION_AUTHORIZATION_SOURCE_STATUSES,
        )
        self.assertIn(
            payload_a["execution_authorization_primary_reason"],
            EXECUTION_AUTHORIZATION_REASON_CODES,
        )

    def test_execution_authorization_missing_binding_prevents_eligibility(self) -> None:
        payload = build_execution_authorization_gate_surface(
            run_id="job-exec-auth-missing-binding",
            objective_contract_payload={"objective_status": "underspecified"},
            completion_contract_payload={"completion_status": "replan_before_closure"},
            approval_transport_payload={
                "approval_status": "approved",
                "approval_decision": "approve",
                "approval_transport_status": "actionable",
            },
            reconcile_contract_payload={"reconcile_status": "blocked", "reconcile_decision": "hold"},
            repair_suggestion_contract_payload={"repair_suggestion_status": "suggested"},
            repair_plan_transport_payload={"repair_plan_status": "available"},
            repair_approval_binding_payload=None,
            run_state_payload={"repair_plan_transport_present": True, "approval_transport_present": True},
            artifact_presence={
                "repair_plan_transport.json": True,
                "approval_transport.json": True,
                "run_state.json": True,
            },
        )

        self.assertNotEqual(payload["execution_authorization_status"], "eligible")
        self.assertIn("missing_binding", payload["execution_authorization_reason_codes"])
        self.assertFalse(payload["execution_authorization_eligible"])

    def test_execution_authorization_denied_approval_sets_denied_status(self) -> None:
        payload = build_execution_authorization_gate_surface(
            run_id="job-exec-auth-denied",
            objective_contract_payload={"objective_status": "complete"},
            completion_contract_payload={"completion_status": "replan_before_closure"},
            approval_transport_payload={
                "approval_status": "denied",
                "approval_decision": "deny",
                "approval_transport_status": "blocked",
            },
            reconcile_contract_payload={"reconcile_status": "blocked"},
            repair_suggestion_contract_payload={"repair_suggestion_status": "suggested"},
            repair_plan_transport_payload={"repair_plan_status": "available"},
            repair_approval_binding_payload={
                "repair_approval_binding_status": "blocked",
                "repair_approval_binding_validity": "invalid",
                "repair_approval_binding_compatibility_status": "incompatible",
            },
            run_state_payload={"repair_approval_binding_present": True},
            artifact_presence={"repair_approval_binding.json": True, "run_state.json": True},
        )

        self.assertEqual(payload["execution_authorization_status"], "denied")
        self.assertEqual(payload["execution_authorization_decision"], "deny_execution")
        self.assertTrue(payload["execution_authorization_denied"])
        self.assertFalse(payload["execution_authorization_eligible"])
        self.assertIn("approval_denied", payload["execution_authorization_reason_codes"])

    def test_execution_authorization_stale_superseded_or_invalid_binding_prevents_eligibility(self) -> None:
        stale = build_execution_authorization_gate_surface(
            run_id="job-exec-auth-stale",
            objective_contract_payload={"objective_status": "complete"},
            completion_contract_payload={"completion_status": "replan_before_closure"},
            approval_transport_payload={
                "approval_status": "approved",
                "approval_decision": "approve",
                "approval_transport_status": "actionable",
            },
            reconcile_contract_payload={"reconcile_status": "blocked"},
            repair_suggestion_contract_payload={"repair_suggestion_status": "suggested"},
            repair_plan_transport_payload={"repair_plan_status": "available"},
            repair_approval_binding_payload={
                "repair_approval_binding_status": "bound",
                "repair_approval_binding_validity": "stale",
                "repair_approval_binding_compatibility_status": "compatible",
            },
            run_state_payload={"repair_approval_binding_present": True},
            artifact_presence={"repair_approval_binding.json": True, "run_state.json": True},
        )
        superseded = build_execution_authorization_gate_surface(
            run_id="job-exec-auth-superseded",
            objective_contract_payload={"objective_status": "complete"},
            completion_contract_payload={"completion_status": "replan_before_closure"},
            approval_transport_payload={
                "approval_status": "approved",
                "approval_decision": "approve",
                "approval_transport_status": "actionable",
            },
            reconcile_contract_payload={"reconcile_status": "blocked"},
            repair_suggestion_contract_payload={"repair_suggestion_status": "suggested"},
            repair_plan_transport_payload={"repair_plan_status": "available"},
            repair_approval_binding_payload={
                "repair_approval_binding_status": "bound",
                "repair_approval_binding_validity": "superseded",
                "repair_approval_binding_compatibility_status": "compatible",
            },
            run_state_payload={"repair_approval_binding_present": True},
            artifact_presence={"repair_approval_binding.json": True, "run_state.json": True},
        )
        invalid = build_execution_authorization_gate_surface(
            run_id="job-exec-auth-invalid",
            objective_contract_payload={"objective_status": "complete"},
            completion_contract_payload={"completion_status": "replan_before_closure"},
            approval_transport_payload={
                "approval_status": "approved",
                "approval_decision": "approve",
                "approval_transport_status": "actionable",
            },
            reconcile_contract_payload={"reconcile_status": "blocked"},
            repair_suggestion_contract_payload={"repair_suggestion_status": "suggested"},
            repair_plan_transport_payload={"repair_plan_status": "available"},
            repair_approval_binding_payload={
                "repair_approval_binding_status": "blocked",
                "repair_approval_binding_validity": "invalid",
                "repair_approval_binding_compatibility_status": "incompatible",
            },
            run_state_payload={"repair_approval_binding_present": True},
            artifact_presence={"repair_approval_binding.json": True, "run_state.json": True},
        )

        self.assertNotEqual(stale["execution_authorization_status"], "eligible")
        self.assertEqual(stale["execution_authorization_validity"], "stale")
        self.assertNotEqual(superseded["execution_authorization_status"], "eligible")
        self.assertEqual(superseded["execution_authorization_validity"], "superseded")
        self.assertNotEqual(invalid["execution_authorization_status"], "eligible")
        self.assertEqual(invalid["execution_authorization_validity"], "invalid")

    def test_execution_authorization_replan_manual_and_truth_gathering_prevent_eligibility(self) -> None:
        replan = build_execution_authorization_gate_surface(
            run_id="job-exec-auth-replan",
            objective_contract_payload={"objective_status": "underspecified"},
            completion_contract_payload={"completion_status": "replan_before_closure"},
            approval_transport_payload={"approval_status": "approved", "approval_transport_status": "actionable"},
            reconcile_contract_payload={"reconcile_status": "blocked", "reconcile_decision": "request_replan"},
            repair_suggestion_contract_payload={"repair_suggestion_status": "suggested"},
            repair_plan_transport_payload={
                "repair_plan_status": "available",
                "repair_plan_replan_required": True,
            },
            repair_approval_binding_payload={
                "repair_approval_binding_status": "partially_bound",
                "repair_approval_binding_validity": "valid",
                "repair_approval_binding_compatibility_status": "partially_compatible",
                "repair_approval_binding_replan_required": True,
            },
            run_state_payload={"repair_approval_binding_present": True, "policy_replan_required": True},
            artifact_presence={"repair_approval_binding.json": True, "run_state.json": True},
        )
        manual = build_execution_authorization_gate_surface(
            run_id="job-exec-auth-manual",
            objective_contract_payload={"objective_status": "complete"},
            completion_contract_payload={"completion_status": "execution_complete_not_accepted"},
            approval_transport_payload={"approval_status": "approved", "approval_transport_status": "actionable"},
            reconcile_contract_payload={"reconcile_status": "blocked"},
            repair_suggestion_contract_payload={"repair_suggestion_status": "suggested"},
            repair_plan_transport_payload={"repair_plan_status": "available", "repair_plan_manual_required": True},
            repair_approval_binding_payload={
                "repair_approval_binding_status": "partially_bound",
                "repair_approval_binding_validity": "valid",
                "repair_approval_binding_compatibility_status": "partially_compatible",
                "repair_approval_binding_manual_required": True,
            },
            run_state_payload={"repair_approval_binding_present": True, "manual_intervention_required": True},
            artifact_presence={"repair_approval_binding.json": True, "run_state.json": True},
        )
        truth_gap = build_execution_authorization_gate_surface(
            run_id="job-exec-auth-truth-gap",
            objective_contract_payload={"objective_status": "incomplete"},
            completion_contract_payload={"completion_status": "not_done"},
            approval_transport_payload={"approval_status": "absent", "approval_transport_status": "missing"},
            reconcile_contract_payload={"reconcile_status": "waiting_for_truth"},
            repair_suggestion_contract_payload={
                "repair_suggestion_status": "suggested",
                "repair_truth_gathering_required": True,
            },
            repair_plan_transport_payload={
                "repair_plan_status": "available",
                "repair_plan_truth_gathering_required": True,
            },
            repair_approval_binding_payload={
                "repair_approval_binding_status": "missing",
                "repair_approval_binding_validity": "insufficient_truth",
                "repair_approval_binding_compatibility_status": "insufficient_truth",
                "repair_approval_binding_truth_gathering_required": True,
            },
            run_state_payload={"repair_approval_binding_present": True},
            artifact_presence={"repair_approval_binding.json": True, "run_state.json": True},
        )

        self.assertEqual(replan["execution_authorization_decision"], "request_replan")
        self.assertFalse(replan["execution_authorization_eligible"])
        self.assertNotEqual(manual["execution_authorization_status"], "eligible")
        self.assertIn(
            manual["execution_authorization_primary_reason"],
            EXECUTION_AUTHORIZATION_REASON_CODES,
        )
        self.assertEqual(truth_gap["execution_authorization_status"], "pending")
        self.assertIn("truth_gathering_required", truth_gap["execution_authorization_reason_codes"])
        self.assertFalse(truth_gap["execution_authorization_eligible"])

    def test_execution_authorization_run_state_summary_surface_is_compact_and_enum_safe(self) -> None:
        compact = build_execution_authorization_gate_run_state_summary_surface(
            {
                "execution_authorization_status": "bad_status",
                "execution_authorization_decision": "bad_decision",
                "execution_authorization_scope": "bad_scope",
                "execution_authorization_validity": "bad_validity",
                "execution_authorization_confidence": "bad_confidence",
                "execution_authorization_primary_reason": "bad_reason",
                "execution_authorization_manual_required": True,
                "execution_authorization_replan_required": False,
                "execution_authorization_truth_gathering_required": True,
                "execution_authorization_reason_codes": ["not_summary_safe"],
            }
        )

        self.assertEqual(
            set(compact.keys()),
            set(EXECUTION_AUTHORIZATION_GATE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertIn(compact["execution_authorization_status"], EXECUTION_AUTHORIZATION_STATUSES)
        self.assertIn(compact["execution_authorization_decision"], EXECUTION_AUTHORIZATION_DECISIONS)
        self.assertIn(compact["execution_authorization_scope"], EXECUTION_AUTHORIZATION_SCOPES)
        self.assertIn(compact["execution_authorization_validity"], EXECUTION_AUTHORIZATION_VALIDITIES)
        self.assertIn(
            compact["execution_authorization_confidence"],
            EXECUTION_AUTHORIZATION_CONFIDENCE_LEVELS,
        )
        self.assertIn(
            compact["execution_authorization_primary_reason"],
            EXECUTION_AUTHORIZATION_REASON_CODES,
        )

    def test_bounded_execution_bridge_is_deterministic_for_ready_posture(self) -> None:
        kwargs = {
            "run_id": "job-bounded-ready",
            "objective_contract_payload": {"objective_id": "objective-bounded", "objective_status": "complete"},
            "completion_contract_payload": {
                "objective_id": "objective-bounded",
                "completion_status": "done_and_safely_closed",
                "closure_decision": "close",
            },
            "approval_transport_payload": {
                "objective_id": "objective-bounded",
                "approval_status": "approved",
                "approval_transport_status": "actionable",
            },
            "reconcile_contract_payload": {"reconcile_status": "aligned", "reconcile_decision": "aligned_no_action"},
            "repair_suggestion_contract_payload": {"repair_suggestion_status": "suggested"},
            "repair_plan_transport_payload": {
                "repair_plan_status": "available",
                "repair_plan_candidate_action": "request_manual_review",
            },
            "repair_approval_binding_payload": {
                "repair_approval_binding_status": "bound",
                "repair_approval_binding_scope": "current_plan_candidate",
                "repair_approval_binding_validity": "valid",
            },
            "execution_authorization_gate_payload": {
                "execution_authorization_status": "eligible",
                "execution_authorization_scope": "current_repair_plan_candidate",
                "execution_authorization_validity": "valid",
                "execution_authorization_primary_reason": "authorization_ready",
                "execution_authorization_eligible": True,
                "execution_authorization_denied": False,
            },
            "run_state_payload": {
                "repair_plan_transport_present": True,
                "repair_approval_binding_present": True,
                "execution_authorization_gate_present": True,
                "manual_intervention_required": False,
                "policy_manual_required": False,
                "policy_replan_required": False,
                "repair_truth_gathering_required": False,
            },
            "artifact_presence": {
                "repair_plan_transport.json": True,
                "repair_approval_binding.json": True,
                "execution_authorization_gate.json": True,
                "run_state.json": True,
            },
        }
        payload_a = build_bounded_execution_bridge_surface(**kwargs)
        payload_b = build_bounded_execution_bridge_surface(**kwargs)

        self.assertEqual(payload_a, payload_b)
        self.assertEqual(payload_a["bounded_execution_status"], "ready")
        self.assertEqual(payload_a["bounded_execution_decision"], "attempt_bounded_execution")
        self.assertTrue(payload_a["bounded_execution_ready"])
        self.assertFalse(payload_a["bounded_execution_deferred"])
        self.assertFalse(payload_a["bounded_execution_denied"])
        self.assertIn(payload_a["bounded_execution_status"], BOUNDED_EXECUTION_STATUSES)
        self.assertIn(payload_a["bounded_execution_decision"], BOUNDED_EXECUTION_DECISIONS)
        self.assertIn(payload_a["bounded_execution_scope"], BOUNDED_EXECUTION_SCOPES)
        self.assertIn(
            payload_a["bounded_execution_candidate_action"],
            BOUNDED_EXECUTION_CANDIDATE_ACTIONS,
        )
        self.assertIn(payload_a["bounded_execution_validity"], BOUNDED_EXECUTION_VALIDITIES)
        self.assertIn(
            payload_a["bounded_execution_confidence"],
            BOUNDED_EXECUTION_CONFIDENCE_LEVELS,
        )
        self.assertIn(
            payload_a["bounded_execution_source_status"],
            BOUNDED_EXECUTION_SOURCE_STATUSES,
        )
        self.assertIn(
            payload_a["bounded_execution_primary_reason"],
            BOUNDED_EXECUTION_REASON_CODES,
        )

    def test_bounded_execution_bridge_authorization_not_eligible_prevents_ready(self) -> None:
        payload = build_bounded_execution_bridge_surface(
            run_id="job-bounded-not-eligible",
            objective_contract_payload={"objective_status": "underspecified"},
            completion_contract_payload={"completion_status": "replan_before_closure"},
            approval_transport_payload={"approval_status": "deferred", "approval_transport_status": "non_actionable"},
            reconcile_contract_payload={"reconcile_status": "blocked"},
            repair_suggestion_contract_payload={"repair_suggestion_status": "suggested"},
            repair_plan_transport_payload={"repair_plan_status": "available", "repair_plan_candidate_action": "request_replan"},
            repair_approval_binding_payload={"repair_approval_binding_status": "missing"},
            execution_authorization_gate_payload={
                "execution_authorization_status": "blocked",
                "execution_authorization_validity": "invalid",
                "execution_authorization_eligible": False,
            },
            run_state_payload={"execution_authorization_gate_present": True},
            artifact_presence={"execution_authorization_gate.json": True, "run_state.json": True},
        )

        self.assertNotEqual(payload["bounded_execution_status"], "ready")
        self.assertFalse(payload["bounded_execution_ready"])
        self.assertIn("authorization_not_eligible", payload["bounded_execution_reason_codes"])

    def test_bounded_execution_bridge_denied_authorization_prevents_ready(self) -> None:
        payload = build_bounded_execution_bridge_surface(
            run_id="job-bounded-denied",
            objective_contract_payload={"objective_status": "complete"},
            completion_contract_payload={"completion_status": "replan_before_closure"},
            approval_transport_payload={
                "approval_status": "denied",
                "approval_decision": "deny",
                "approval_transport_status": "blocked",
            },
            reconcile_contract_payload={"reconcile_status": "blocked"},
            repair_suggestion_contract_payload={"repair_suggestion_status": "suggested"},
            repair_plan_transport_payload={"repair_plan_status": "available", "repair_plan_candidate_action": "request_manual_review"},
            repair_approval_binding_payload={
                "repair_approval_binding_status": "blocked",
                "repair_approval_binding_validity": "invalid",
            },
            execution_authorization_gate_payload={
                "execution_authorization_status": "denied",
                "execution_authorization_denied": True,
            },
            run_state_payload={"execution_authorization_gate_present": True},
            artifact_presence={"execution_authorization_gate.json": True, "run_state.json": True},
        )

        self.assertNotEqual(payload["bounded_execution_status"], "ready")
        self.assertFalse(payload["bounded_execution_ready"])
        self.assertTrue(payload["bounded_execution_denied"])
        self.assertIn("authorization_denied", payload["bounded_execution_reason_codes"])

    def test_bounded_execution_bridge_replan_manual_and_truth_gathering_prevent_ready(self) -> None:
        replan = build_bounded_execution_bridge_surface(
            run_id="job-bounded-replan",
            objective_contract_payload={"objective_status": "underspecified"},
            completion_contract_payload={"completion_status": "replan_before_closure"},
            approval_transport_payload={"approval_status": "approved", "approval_transport_status": "actionable"},
            reconcile_contract_payload={"reconcile_status": "blocked", "reconcile_decision": "request_replan"},
            repair_suggestion_contract_payload={"repair_suggestion_status": "suggested"},
            repair_plan_transport_payload={
                "repair_plan_status": "available",
                "repair_plan_candidate_action": "request_replan",
                "repair_plan_replan_required": True,
            },
            repair_approval_binding_payload={"repair_approval_binding_status": "partially_bound"},
            execution_authorization_gate_payload={
                "execution_authorization_status": "blocked",
                "execution_authorization_decision": "request_replan",
                "execution_authorization_replan_required": True,
            },
            run_state_payload={"execution_authorization_gate_present": True},
            artifact_presence={"execution_authorization_gate.json": True, "run_state.json": True},
        )
        manual = build_bounded_execution_bridge_surface(
            run_id="job-bounded-manual",
            objective_contract_payload={"objective_status": "complete"},
            completion_contract_payload={"completion_status": "execution_complete_not_accepted"},
            approval_transport_payload={"approval_status": "approved", "approval_transport_status": "actionable"},
            reconcile_contract_payload={"reconcile_status": "blocked"},
            repair_suggestion_contract_payload={"repair_suggestion_status": "suggested"},
            repair_plan_transport_payload={
                "repair_plan_status": "available",
                "repair_plan_candidate_action": "request_manual_review",
                "repair_plan_manual_required": True,
            },
            repair_approval_binding_payload={"repair_approval_binding_status": "partially_bound"},
            execution_authorization_gate_payload={
                "execution_authorization_status": "blocked",
                "execution_authorization_manual_required": True,
            },
            run_state_payload={"execution_authorization_gate_present": True, "manual_intervention_required": True},
            artifact_presence={"execution_authorization_gate.json": True, "run_state.json": True},
        )
        truth_gap = build_bounded_execution_bridge_surface(
            run_id="job-bounded-truth-gap",
            objective_contract_payload={"objective_status": "incomplete"},
            completion_contract_payload={"completion_status": "not_done"},
            approval_transport_payload={"approval_status": "absent", "approval_transport_status": "missing"},
            reconcile_contract_payload={"reconcile_status": "waiting_for_truth"},
            repair_suggestion_contract_payload={"repair_suggestion_status": "suggested", "repair_suggestion_decision": "gather_truth"},
            repair_plan_transport_payload={
                "repair_plan_status": "available",
                "repair_plan_candidate_action": "gather_missing_truth",
                "repair_plan_truth_gathering_required": True,
            },
            repair_approval_binding_payload={"repair_approval_binding_status": "missing"},
            execution_authorization_gate_payload={
                "execution_authorization_status": "pending",
                "execution_authorization_truth_gathering_required": True,
            },
            run_state_payload={"execution_authorization_gate_present": True},
            artifact_presence={"execution_authorization_gate.json": True, "run_state.json": True},
        )

        self.assertFalse(replan["bounded_execution_ready"])
        self.assertEqual(replan["bounded_execution_decision"], "request_replan")
        self.assertFalse(manual["bounded_execution_ready"])
        self.assertEqual(manual["bounded_execution_decision"], "manual_review_required")
        self.assertFalse(truth_gap["bounded_execution_ready"])
        self.assertEqual(truth_gap["bounded_execution_status"], "deferred")
        self.assertTrue(truth_gap["bounded_execution_deferred"])
        self.assertIn("truth_gathering_required", truth_gap["bounded_execution_reason_codes"])

    def test_bounded_execution_bridge_deferred_vs_insufficient_truth(self) -> None:
        deferred = build_bounded_execution_bridge_surface(
            run_id="job-bounded-deferred",
            objective_contract_payload={"objective_status": "incomplete"},
            completion_contract_payload={"completion_status": "not_done"},
            approval_transport_payload={"approval_status": "absent", "approval_transport_status": "missing"},
            reconcile_contract_payload={"reconcile_status": "waiting_for_truth"},
            repair_suggestion_contract_payload={"repair_suggestion_status": "suggested"},
            repair_plan_transport_payload={
                "repair_plan_status": "available",
                "repair_plan_candidate_action": "gather_missing_truth",
                "repair_plan_truth_gathering_required": True,
            },
            repair_approval_binding_payload={"repair_approval_binding_status": "missing"},
            execution_authorization_gate_payload={"execution_authorization_status": "pending"},
            run_state_payload={"execution_authorization_gate_present": True},
            artifact_presence={"execution_authorization_gate.json": True, "run_state.json": True},
        )
        insufficient = build_bounded_execution_bridge_surface(
            run_id="job-bounded-insufficient",
            objective_contract_payload={},
            completion_contract_payload={},
            approval_transport_payload={},
            reconcile_contract_payload={},
            repair_suggestion_contract_payload={},
            repair_plan_transport_payload={},
            repair_approval_binding_payload={},
            execution_authorization_gate_payload={},
            run_state_payload={},
            artifact_presence={},
        )

        self.assertEqual(deferred["bounded_execution_status"], "deferred")
        self.assertEqual(deferred["bounded_execution_decision"], "hold_deferred")
        self.assertEqual(insufficient["bounded_execution_status"], "insufficient_truth")
        self.assertNotEqual(insufficient["bounded_execution_status"], "ready")

    def test_bounded_execution_bridge_run_state_summary_surface_is_compact_and_enum_safe(self) -> None:
        compact = build_bounded_execution_bridge_run_state_summary_surface(
            {
                "bounded_execution_status": "bad_status",
                "bounded_execution_decision": "bad_decision",
                "bounded_execution_scope": "bad_scope",
                "bounded_execution_validity": "bad_validity",
                "bounded_execution_confidence": "bad_confidence",
                "bounded_execution_primary_reason": "bad_reason",
                "bounded_execution_manual_required": True,
                "bounded_execution_replan_required": False,
                "bounded_execution_truth_gathering_required": True,
                "bounded_execution_reason_codes": ["not_summary_safe"],
            }
        )

        self.assertEqual(
            set(compact.keys()),
            set(BOUNDED_EXECUTION_BRIDGE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertIn(compact["bounded_execution_status"], BOUNDED_EXECUTION_STATUSES)
        self.assertIn(compact["bounded_execution_decision"], BOUNDED_EXECUTION_DECISIONS)
        self.assertIn(compact["bounded_execution_scope"], BOUNDED_EXECUTION_SCOPES)
        self.assertIn(compact["bounded_execution_validity"], BOUNDED_EXECUTION_VALIDITIES)
        self.assertIn(
            compact["bounded_execution_confidence"],
            BOUNDED_EXECUTION_CONFIDENCE_LEVELS,
        )
        self.assertIn(
            compact["bounded_execution_primary_reason"],
            BOUNDED_EXECUTION_REASON_CODES,
        )

    def test_execution_result_contract_is_deterministic_for_narrow_success(self) -> None:
        execution_records = [
            {
                "pr_id": "pr-01",
                "result_path": "/tmp/pr-01/result.json",
                "result_exists": True,
                "result_malformed": False,
                "result_payload": {
                    "execution": {
                        "status": "completed",
                        "attempt_count": 1,
                        "verify": {
                            "status": "passed",
                            "commands": ["uv run python -m unittest tests.test_planned_execution_runner -v"],
                        },
                    },
                    "changed_files": ["automation/orchestration/execution_result_contract.py"],
                    "additions": 10,
                    "deletions": 0,
                    "generated_patch_summary": "narrow additive patch",
                    "failure_type": None,
                    "raw_execution": {
                        "result": {
                            "verify": {
                                "status": "passed",
                                "command_results": [
                                    {"command": "uv run python -m unittest", "status": "passed"}
                                ],
                            }
                        }
                    },
                },
                "receipt_path": "/tmp/pr-01/execution_receipt.json",
                "receipt_exists": True,
                "receipt_malformed": False,
                "receipt_payload": {"status": "recorded"},
            }
        ]
        kwargs = {
            "run_id": "job-execution-result-ready",
            "objective_contract_payload": {"objective_id": "objective-ready", "objective_status": "complete"},
            "completion_contract_payload": {"objective_id": "objective-ready", "completion_status": "done_and_safely_closed"},
            "approval_transport_payload": {"approval_status": "approved"},
            "reconcile_contract_payload": {"reconcile_status": "aligned"},
            "repair_plan_transport_payload": {"repair_plan_status": "available"},
            "repair_approval_binding_payload": {"repair_approval_binding_status": "bound"},
            "execution_authorization_gate_payload": {"execution_authorization_status": "eligible"},
            "bounded_execution_bridge_payload": {
                "bounded_execution_status": "ready",
                "bounded_execution_decision": "attempt_bounded_execution",
                "bounded_execution_denied": False,
            },
            "run_state_payload": {},
            "execution_records": execution_records,
            "artifact_presence": {"bounded_execution_bridge.json": True, "run_state.json": True},
        }
        payload_a = build_execution_result_contract_surface(**kwargs)
        payload_b = build_execution_result_contract_surface(**kwargs)

        self.assertEqual(payload_a, payload_b)
        self.assertEqual(payload_a["execution_result_status"], "succeeded")
        self.assertEqual(payload_a["execution_result_outcome"], "changes_applied")
        self.assertTrue(payload_a["execution_result_attempted"])
        self.assertTrue(payload_a["execution_result_succeeded"])
        self.assertIn(payload_a["execution_result_status"], EXECUTION_RESULT_STATUSES)
        self.assertIn(payload_a["execution_result_outcome"], EXECUTION_RESULT_OUTCOMES)
        self.assertIn(payload_a["execution_result_validity"], EXECUTION_RESULT_VALIDITIES)
        self.assertIn(payload_a["execution_result_confidence"], EXECUTION_RESULT_CONFIDENCE_LEVELS)
        self.assertIn(payload_a["execution_result_primary_reason"], EXECUTION_RESULT_REASON_CODES)
        self.assertIn(payload_a["execution_result_source_posture"], EXECUTION_RESULT_SOURCE_POSTURES)

    def test_execution_result_contract_separates_blocked_not_executed_and_unknown(self) -> None:
        blocked = build_execution_result_contract_surface(
            run_id="job-execution-result-blocked",
            objective_contract_payload={},
            completion_contract_payload={},
            approval_transport_payload={},
            reconcile_contract_payload={},
            repair_plan_transport_payload={},
            repair_approval_binding_payload={},
            execution_authorization_gate_payload={"execution_authorization_status": "denied"},
            bounded_execution_bridge_payload={
                "bounded_execution_status": "blocked",
                "bounded_execution_decision": "hold_blocked",
                "bounded_execution_denied": True,
            },
            run_state_payload={},
            execution_records=[],
            artifact_presence={},
        )
        not_executed = build_execution_result_contract_surface(
            run_id="job-execution-result-not-executed",
            objective_contract_payload={},
            completion_contract_payload={},
            approval_transport_payload={},
            reconcile_contract_payload={},
            repair_plan_transport_payload={},
            repair_approval_binding_payload={},
            execution_authorization_gate_payload={"execution_authorization_status": "pending"},
            bounded_execution_bridge_payload={
                "bounded_execution_status": "deferred",
                "bounded_execution_decision": "hold_deferred",
            },
            run_state_payload={},
            execution_records=[],
            artifact_presence={},
        )
        unknown = build_execution_result_contract_surface(
            run_id="job-execution-result-unknown",
            objective_contract_payload={},
            completion_contract_payload={},
            approval_transport_payload={},
            reconcile_contract_payload={},
            repair_plan_transport_payload={},
            repair_approval_binding_payload={},
            execution_authorization_gate_payload={},
            bounded_execution_bridge_payload={"bounded_execution_status": "insufficient_truth"},
            run_state_payload={},
            execution_records=[],
            artifact_presence={},
        )

        self.assertEqual(blocked["execution_result_status"], "blocked")
        self.assertEqual(blocked["execution_result_outcome"], "blocked")
        self.assertFalse(blocked["execution_result_attempted"])
        self.assertEqual(not_executed["execution_result_status"], "not_executed")
        self.assertEqual(not_executed["execution_result_outcome"], "skipped")
        self.assertFalse(not_executed["execution_result_attempted"])
        self.assertEqual(unknown["execution_result_status"], "unknown")
        self.assertEqual(unknown["execution_result_outcome"], "unknown")

    def test_execution_result_contract_attempted_malformed_evidence_degrades_conservatively(self) -> None:
        payload = build_execution_result_contract_surface(
            run_id="job-execution-result-malformed",
            objective_contract_payload={},
            completion_contract_payload={},
            approval_transport_payload={},
            reconcile_contract_payload={},
            repair_plan_transport_payload={},
            repair_approval_binding_payload={},
            execution_authorization_gate_payload={"execution_authorization_status": "eligible"},
            bounded_execution_bridge_payload={"bounded_execution_status": "ready"},
            run_state_payload={},
            execution_records=[
                {
                    "result_path": "/tmp/pr-01/result.json",
                    "result_exists": True,
                    "result_malformed": True,
                    "result_payload": None,
                    "receipt_path": "/tmp/pr-01/execution_receipt.json",
                    "receipt_exists": True,
                    "receipt_malformed": False,
                    "receipt_payload": {"status": "recorded"},
                }
            ],
            artifact_presence={},
        )

        self.assertIn(payload["execution_result_status"], {"partial", "unknown"})
        self.assertTrue(payload["execution_result_unknown"] or payload["execution_result_partial"])
        self.assertIn(payload["execution_result_validity"], {"malformed", "partial", "unknown"})
        self.assertIn("malformed_evidence", payload["execution_result_reason_codes"])

    def test_execution_result_contract_reason_order_is_deterministic(self) -> None:
        payload = build_execution_result_contract_surface(
            run_id="job-execution-result-reason-order",
            objective_contract_payload={},
            completion_contract_payload={},
            approval_transport_payload={},
            reconcile_contract_payload={},
            repair_plan_transport_payload={},
            repair_approval_binding_payload={},
            execution_authorization_gate_payload={"execution_authorization_status": "pending"},
            bounded_execution_bridge_payload={"bounded_execution_status": "deferred"},
            run_state_payload={},
            execution_records=[],
            artifact_presence={},
        )
        self.assertEqual(
            payload["execution_result_primary_reason"],
            payload["execution_result_reason_codes"][0],
        )

    def test_execution_result_contract_run_state_summary_surface_is_compact_and_enum_safe(self) -> None:
        compact = build_execution_result_contract_run_state_summary_surface(
            {
                "execution_result_status": "bad_status",
                "execution_result_outcome": "bad_outcome",
                "execution_result_validity": "bad_validity",
                "execution_result_confidence": "bad_confidence",
                "execution_result_primary_reason": "bad_reason",
                "execution_result_attempted": True,
                "execution_result_receipt_present": False,
                "execution_result_output_present": True,
                "execution_result_manual_followup_required": True,
                "execution_result_reason_codes": ["not_summary_safe"],
            }
        )

        self.assertEqual(
            set(compact.keys()),
            set(EXECUTION_RESULT_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertIn(compact["execution_result_status"], EXECUTION_RESULT_STATUSES)
        self.assertIn(compact["execution_result_outcome"], EXECUTION_RESULT_OUTCOMES)
        self.assertIn(compact["execution_result_validity"], EXECUTION_RESULT_VALIDITIES)
        self.assertIn(compact["execution_result_confidence"], EXECUTION_RESULT_CONFIDENCE_LEVELS)
        self.assertIn(compact["execution_result_primary_reason"], EXECUTION_RESULT_REASON_CODES)
        self.assertIsInstance(compact["execution_result_attempted"], bool)
        self.assertIsInstance(compact["execution_result_receipt_present"], bool)
        self.assertIsInstance(compact["execution_result_output_present"], bool)
        self.assertIsInstance(compact["execution_result_manual_followup_required"], bool)

    def test_verification_closure_contract_is_deterministic(self) -> None:
        kwargs = {
            "run_id": "job-verification-deterministic",
            "objective_contract_payload": {
                "objective_id": "objective-verification",
                "objective_status": "complete",
            },
            "completion_contract_payload": {
                "objective_id": "objective-verification",
                "completion_status": "done_and_safely_closed",
                "safe_closure_status": "safely_closed",
                "closure_decision": "close",
            },
            "approval_transport_payload": {
                "approval_status": "approved",
                "approval_transport_status": "actionable",
            },
            "reconcile_contract_payload": {
                "reconcile_status": "aligned",
                "reconcile_primary_mismatch": "",
            },
            "execution_authorization_gate_payload": {
                "execution_authorization_status": "eligible",
            },
            "bounded_execution_bridge_payload": {
                "bounded_execution_status": "ready",
                "bounded_execution_decision": "attempt_bounded_execution",
            },
            "execution_result_contract_payload": {
                "objective_id": "objective-verification",
                "execution_result_status": "succeeded",
                "execution_result_outcome": "changes_applied",
                "execution_result_validity": "valid",
                "execution_result_attempted": True,
            },
            "run_state_payload": {
                "lifecycle_safely_closed": True,
                "lifecycle_closure_status": "safely_closed",
            },
            "artifact_presence": {"execution_result_contract.json": True, "run_state.json": True},
        }
        payload_a = build_verification_closure_contract_surface(**kwargs)
        payload_b = build_verification_closure_contract_surface(**kwargs)
        self.assertEqual(payload_a, payload_b)
        self.assertEqual(payload_a["verification_status"], "verified_success")
        self.assertEqual(payload_a["closure_decision"], "close_ready")

    def test_verification_closure_execution_success_does_not_imply_objective_satisfied(self) -> None:
        payload = build_verification_closure_contract_surface(
            run_id="job-verification-objective-gap",
            objective_contract_payload={"objective_status": "underspecified"},
            completion_contract_payload={
                "completion_status": "done_and_safely_closed",
                "safe_closure_status": "safely_closed",
            },
            approval_transport_payload={"approval_status": "approved", "approval_transport_status": "actionable"},
            reconcile_contract_payload={"reconcile_status": "aligned"},
            execution_authorization_gate_payload={"execution_authorization_status": "eligible"},
            bounded_execution_bridge_payload={"bounded_execution_status": "ready"},
            execution_result_contract_payload={
                "execution_result_status": "succeeded",
                "execution_result_outcome": "changes_applied",
                "execution_result_validity": "valid",
                "execution_result_attempted": True,
            },
            run_state_payload={"lifecycle_safely_closed": True, "lifecycle_closure_status": "safely_closed"},
            artifact_presence={"execution_result_contract.json": True},
        )
        self.assertEqual(payload["verification_outcome"], "objective_gap")
        self.assertEqual(payload["objective_satisfaction_status"], "not_satisfied")
        self.assertNotEqual(payload["verification_status"], "verified_success")
        self.assertNotEqual(payload["closure_decision"], "close_ready")

    def test_verification_closure_objective_satisfied_does_not_imply_close_ready(self) -> None:
        payload = build_verification_closure_contract_surface(
            run_id="job-verification-approval-blocked",
            objective_contract_payload={"objective_status": "complete"},
            completion_contract_payload={
                "completion_status": "done_and_safely_closed",
                "safe_closure_status": "safely_closed",
            },
            approval_transport_payload={
                "approval_status": "deferred",
                "approval_transport_status": "non_actionable",
                "approval_blocked_reason": "approval_scope_partial",
            },
            reconcile_contract_payload={"reconcile_status": "aligned"},
            execution_authorization_gate_payload={"execution_authorization_status": "eligible"},
            bounded_execution_bridge_payload={"bounded_execution_status": "ready"},
            execution_result_contract_payload={
                "execution_result_status": "succeeded",
                "execution_result_outcome": "changes_applied",
                "execution_result_validity": "valid",
                "execution_result_attempted": True,
            },
            run_state_payload={"lifecycle_safely_closed": True, "lifecycle_closure_status": "safely_closed"},
            artifact_presence={"execution_result_contract.json": True},
        )
        self.assertEqual(payload["objective_satisfaction_status"], "satisfied")
        self.assertNotEqual(payload["closure_decision"], "close_ready")
        self.assertIn(payload["verification_outcome"], {"closure_followup", "manual_closure_only"})

    def test_verification_closure_handles_malformed_execution_result_evidence(self) -> None:
        payload = build_verification_closure_contract_surface(
            run_id="job-verification-malformed",
            objective_contract_payload={"objective_status": "complete"},
            completion_contract_payload={"completion_status": "done_and_safely_closed"},
            approval_transport_payload={},
            reconcile_contract_payload={},
            execution_authorization_gate_payload={},
            bounded_execution_bridge_payload={"bounded_execution_status": "ready"},
            execution_result_contract_payload={
                "execution_result_status": "unknown",
                "execution_result_outcome": "unknown",
                "execution_result_validity": "malformed",
            },
            run_state_payload={},
            artifact_presence={"execution_result_contract.json": True},
        )
        self.assertEqual(payload["verification_validity"], "malformed")
        self.assertEqual(payload["verification_status"], "not_verifiable")
        self.assertNotEqual(payload["closure_decision"], "close_ready")

    def test_verification_closure_handles_insufficient_truth(self) -> None:
        payload = build_verification_closure_contract_surface(
            run_id="job-verification-insufficient",
            objective_contract_payload={},
            completion_contract_payload={},
            approval_transport_payload={},
            reconcile_contract_payload={},
            execution_authorization_gate_payload={},
            bounded_execution_bridge_payload={"bounded_execution_status": "insufficient_truth"},
            execution_result_contract_payload={},
            run_state_payload={},
            artifact_presence={},
        )
        self.assertEqual(payload["verification_status"], "not_verifiable")
        self.assertEqual(payload["verification_validity"], "insufficient_truth")
        self.assertEqual(payload["objective_satisfaction_status"], "unknown")
        self.assertIn(payload["closure_decision"], {"cannot_determine", "await_external_truth"})

    def test_verification_closure_handles_external_truth_pending(self) -> None:
        payload = build_verification_closure_contract_surface(
            run_id="job-verification-external",
            objective_contract_payload={"objective_status": "complete"},
            completion_contract_payload={
                "completion_status": "delivery_complete_waiting_external_truth",
                "safe_closure_status": "not_safely_closed",
                "delivery_complete_waiting_external_truth": True,
            },
            approval_transport_payload={"approval_status": "approved", "approval_transport_status": "actionable"},
            reconcile_contract_payload={"reconcile_status": "waiting_for_truth"},
            execution_authorization_gate_payload={"execution_authorization_status": "pending"},
            bounded_execution_bridge_payload={"bounded_execution_status": "deferred"},
            execution_result_contract_payload={
                "execution_result_status": "not_executed",
                "execution_result_outcome": "skipped",
                "execution_result_validity": "valid",
                "execution_result_attempted": False,
            },
            run_state_payload={},
            artifact_presence={"execution_result_contract.json": True},
        )
        self.assertEqual(payload["verification_outcome"], "external_truth_pending")
        self.assertEqual(payload["closure_decision"], "await_external_truth")
        self.assertTrue(payload["external_truth_required"])

    def test_verification_closure_approval_blocker_causes_hold(self) -> None:
        payload = build_verification_closure_contract_surface(
            run_id="job-verification-approval-hold",
            objective_contract_payload={"objective_status": "complete"},
            completion_contract_payload={
                "completion_status": "done_and_safely_closed",
                "safe_closure_status": "safely_closed",
            },
            approval_transport_payload={
                "approval_status": "denied",
                "approval_transport_status": "blocked",
                "approval_blocked_reason": "approval_denied",
            },
            reconcile_contract_payload={"reconcile_status": "aligned"},
            execution_authorization_gate_payload={"execution_authorization_status": "denied"},
            bounded_execution_bridge_payload={"bounded_execution_status": "blocked"},
            execution_result_contract_payload={
                "execution_result_status": "blocked",
                "execution_result_outcome": "blocked",
                "execution_result_validity": "valid",
            },
            run_state_payload={},
            artifact_presence={"execution_result_contract.json": True},
        )
        self.assertIn(payload["closure_decision"], {"hold_for_followup", "manual_close"})
        self.assertNotEqual(payload["closure_decision"], "close_ready")

    def test_verification_closure_reconcile_mismatch_causes_hold(self) -> None:
        payload = build_verification_closure_contract_surface(
            run_id="job-verification-reconcile-hold",
            objective_contract_payload={"objective_status": "complete"},
            completion_contract_payload={"completion_status": "done_and_safely_closed", "safe_closure_status": "safely_closed"},
            approval_transport_payload={"approval_status": "approved", "approval_transport_status": "actionable"},
            reconcile_contract_payload={
                "reconcile_status": "blocked",
                "reconcile_primary_mismatch": "completion_lifecycle_mismatch",
            },
            execution_authorization_gate_payload={"execution_authorization_status": "eligible"},
            bounded_execution_bridge_payload={"bounded_execution_status": "ready"},
            execution_result_contract_payload={
                "execution_result_status": "succeeded",
                "execution_result_outcome": "changes_applied",
                "execution_result_validity": "valid",
                "execution_result_attempted": True,
            },
            run_state_payload={"lifecycle_safely_closed": False},
            artifact_presence={"execution_result_contract.json": True},
        )
        self.assertEqual(payload["verification_outcome"], "closure_followup")
        self.assertEqual(payload["closure_decision"], "hold_for_followup")

    def test_verification_closure_flags_rollback_consideration_without_execution(self) -> None:
        payload = build_verification_closure_contract_surface(
            run_id="job-verification-rollback-consideration",
            objective_contract_payload={"objective_status": "complete"},
            completion_contract_payload={
                "completion_status": "done_and_safely_closed",
                "safe_closure_status": "safely_closed",
            },
            approval_transport_payload={"approval_status": "approved", "approval_transport_status": "actionable"},
            reconcile_contract_payload={"reconcile_status": "aligned"},
            execution_authorization_gate_payload={"execution_authorization_status": "eligible"},
            bounded_execution_bridge_payload={"bounded_execution_status": "ready"},
            execution_result_contract_payload={
                "execution_result_status": "failed",
                "execution_result_outcome": "tests_failed",
                "execution_result_validity": "valid",
                "execution_result_attempted": True,
            },
            run_state_payload={"lifecycle_safely_closed": True, "lifecycle_closure_status": "safely_closed"},
            artifact_presence={"execution_result_contract.json": True},
        )
        self.assertTrue(payload["rollback_consideration_required"])
        self.assertEqual(payload["closure_decision"], "consider_rollback")

    def test_verification_closure_reason_order_is_deterministic(self) -> None:
        payload = build_verification_closure_contract_surface(
            run_id="job-verification-reason-order",
            objective_contract_payload={"objective_status": "incomplete"},
            completion_contract_payload={"completion_status": "not_done"},
            approval_transport_payload={"approval_status": "deferred", "approval_transport_status": "non_actionable"},
            reconcile_contract_payload={"reconcile_status": "blocked", "reconcile_primary_mismatch": "x"},
            execution_authorization_gate_payload={"execution_authorization_status": "pending"},
            bounded_execution_bridge_payload={"bounded_execution_status": "blocked"},
            execution_result_contract_payload={
                "execution_result_status": "unknown",
                "execution_result_outcome": "unknown",
                "execution_result_validity": "partial",
            },
            run_state_payload={},
            artifact_presence={"execution_result_contract.json": True},
        )
        self.assertEqual(
            payload["verification_primary_reason"],
            payload["verification_reason_codes"][0],
        )

    def test_verification_closure_run_state_summary_surface_is_compact_and_enum_safe(self) -> None:
        compact = build_verification_closure_run_state_summary_surface(
            {
                "verification_status": "bad_status",
                "verification_outcome": "bad_outcome",
                "verification_validity": "bad_validity",
                "verification_confidence": "bad_confidence",
                "verification_primary_reason": "bad_reason",
                "objective_satisfaction_status": "bad_objective",
                "completion_satisfaction_status": "bad_completion",
                "closure_status": "bad_closure",
                "closure_decision": "bad_decision",
                "objective_satisfied": True,
                "completion_satisfied": False,
                "safely_closable": False,
                "manual_closure_required": True,
                "closure_followup_required": True,
                "external_truth_required": False,
            }
        )
        self.assertEqual(
            set(compact.keys()),
            set(VERIFICATION_CLOSURE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertIn(compact["verification_status"], VERIFICATION_STATUSES)
        self.assertIn(compact["verification_outcome"], VERIFICATION_OUTCOMES)
        self.assertIn(compact["verification_validity"], VERIFICATION_VALIDITIES)
        self.assertIn(compact["verification_confidence"], VERIFICATION_CONFIDENCE_LEVELS)
        self.assertIn(compact["verification_primary_reason"], VERIFICATION_REASON_CODES)
        self.assertIn(compact["objective_satisfaction_status"], OBJECTIVE_SATISFACTION_STATUSES)
        self.assertIn(compact["completion_satisfaction_status"], COMPLETION_SATISFACTION_STATUSES)
        self.assertIn(compact["closure_status"], VERIFICATION_CLOSURE_STATUSES)
        self.assertIn(compact["closure_decision"], VERIFICATION_CLOSURE_DECISIONS)

    def test_retry_reentry_loop_contract_is_deterministic(self) -> None:
        kwargs = {
            "verification": {
                "verification_status": "verified_failure",
                "verification_outcome": "closure_followup",
                "verification_validity": "valid",
                "closure_status": "closure_pending",
                "closure_decision": "hold_for_followup",
                "closure_followup_required": True,
            },
            "execution_result": {
                "execution_result_status": "failed",
                "execution_result_outcome": "tests_failed",
                "execution_result_validity": "valid",
                "execution_result_attempted": True,
            },
        }
        payload_a = self._build_retry_loop_payload(**kwargs)
        payload_b = self._build_retry_loop_payload(**kwargs)

        self.assertEqual(payload_a, payload_b)
        self.assertIn(payload_a["retry_loop_status"], RETRY_LOOP_STATUSES)
        self.assertIn(payload_a["retry_loop_decision"], RETRY_LOOP_DECISIONS)
        self.assertIn(payload_a["retry_loop_validity"], RETRY_LOOP_VALIDITIES)
        self.assertIn(payload_a["retry_loop_confidence"], RETRY_LOOP_CONFIDENCE_LEVELS)
        self.assertIn(payload_a["retry_class"], RETRY_CLASSES)
        self.assertIn(payload_a["reentry_class"], REENTRY_CLASSES)
        self.assertIn(payload_a["loop_stop_reason"], LOOP_STOP_REASONS)
        self.assertIn(payload_a["retry_loop_source_posture"], RETRY_LOOP_SOURCE_POSTURES)
        self.assertEqual(payload_a["loop_primary_reason"], payload_a["loop_reason_codes"][0])

    def test_retry_loop_closure_ready_is_not_applicable(self) -> None:
        payload = self._build_retry_loop_payload(
            verification={
                "verification_status": "verified_success",
                "verification_outcome": "objective_satisfied",
                "verification_validity": "valid",
                "closure_status": "safely_closable",
                "closure_decision": "close_ready",
            },
            execution_result={
                "execution_result_status": "succeeded",
                "execution_result_outcome": "changes_applied",
                "execution_result_validity": "valid",
                "execution_result_attempted": True,
            },
        )
        self.assertEqual(payload["retry_loop_status"], "not_applicable")
        self.assertEqual(payload["retry_loop_decision"], "not_applicable")
        self.assertFalse(payload["retry_allowed"])
        self.assertFalse(payload["reentry_allowed"])

    def test_retry_loop_manual_only_requires_terminal_stop(self) -> None:
        payload = self._build_retry_loop_payload(
            verification={
                "verification_status": "verified_failure",
                "verification_outcome": "manual_closure_only",
                "verification_validity": "valid",
                "closure_status": "manual_closure_only",
                "closure_decision": "manual_close",
                "manual_closure_required": True,
            },
            execution_result={
                "execution_result_status": "failed",
                "execution_result_outcome": "command_failed",
                "execution_result_validity": "valid",
                "execution_result_attempted": True,
            },
        )
        self.assertEqual(payload["retry_loop_status"], "stop_required")
        self.assertEqual(payload["retry_loop_decision"], "escalate_manual")
        self.assertTrue(payload["terminal_stop_required"])
        self.assertFalse(payload["retry_allowed"])
        self.assertFalse(payload["reentry_allowed"])

    def test_retry_loop_classifies_same_lane_retry(self) -> None:
        payload = self._build_retry_loop_payload(
            verification={
                "verification_status": "verified_failure",
                "verification_outcome": "completion_gap",
                "verification_validity": "valid",
                "closure_status": "not_closable",
                "closure_decision": "hold_for_followup",
            },
            execution_result={
                "execution_result_status": "failed",
                "execution_result_outcome": "tests_failed",
                "execution_result_validity": "valid",
                "execution_result_attempted": True,
            },
        )
        self.assertEqual(payload["retry_loop_status"], "retry_ready")
        self.assertEqual(payload["retry_loop_decision"], "same_lane_retry")
        self.assertEqual(payload["retry_class"], "same_lane")
        self.assertTrue(payload["retry_allowed"])
        self.assertTrue(payload["same_lane_retry_allowed"])

    def test_retry_loop_classifies_repair_retry(self) -> None:
        payload = self._build_retry_loop_payload(
            verification={
                "verification_status": "verified_failure",
                "verification_outcome": "closure_followup",
                "verification_validity": "valid",
                "closure_status": "closure_pending",
                "closure_decision": "hold_for_followup",
                "closure_followup_required": True,
            },
            execution_result={
                "execution_result_status": "failed",
                "execution_result_outcome": "tests_failed",
                "execution_result_validity": "valid",
                "execution_result_attempted": True,
            },
        )
        self.assertEqual(payload["retry_loop_status"], "retry_ready")
        self.assertEqual(payload["retry_loop_decision"], "repair_retry")
        self.assertEqual(payload["retry_class"], "repair")
        self.assertTrue(payload["repair_retry_allowed"])

    def test_retry_loop_classifies_recollect_reentry(self) -> None:
        payload = self._build_retry_loop_payload(
            verification={
                "verification_status": "inconclusive",
                "verification_outcome": "external_truth_pending",
                "verification_validity": "partial",
                "closure_status": "closure_pending",
                "closure_decision": "await_external_truth",
                "external_truth_required": True,
            },
            execution_result={
                "execution_result_status": "not_executed",
                "execution_result_outcome": "skipped",
                "execution_result_validity": "valid",
                "execution_result_attempted": False,
            },
        )
        self.assertEqual(payload["retry_loop_status"], "reentry_ready")
        self.assertEqual(payload["retry_loop_decision"], "recollect")
        self.assertEqual(payload["reentry_class"], "recollect")
        self.assertTrue(payload["reentry_allowed"])
        self.assertTrue(payload["recollect_required"])

    def test_retry_loop_classifies_replan_reentry(self) -> None:
        payload = self._build_retry_loop_payload(
            verification={
                "verification_status": "verified_failure",
                "verification_outcome": "completion_gap",
                "verification_validity": "valid",
                "closure_status": "not_closable",
                "closure_decision": "hold_for_followup",
            },
            execution_result={
                "execution_result_status": "failed",
                "execution_result_outcome": "tests_failed",
                "execution_result_validity": "valid",
                "execution_result_attempted": True,
            },
            repair_suggestion={"repair_suggestion_decision": "request_replan"},
        )
        self.assertEqual(payload["retry_loop_status"], "reentry_ready")
        self.assertEqual(payload["retry_loop_decision"], "replan")
        self.assertEqual(payload["reentry_class"], "replan")
        self.assertTrue(payload["reentry_allowed"])
        self.assertTrue(payload["replan_required"])

    def test_retry_loop_handles_insufficient_truth_conservatively(self) -> None:
        payload = self._build_retry_loop_payload(
            verification={},
            execution_result={},
            artifacts={},
        )
        self.assertEqual(payload["retry_loop_status"], "insufficient_truth")
        self.assertEqual(payload["retry_loop_validity"], "insufficient_truth")
        self.assertFalse(payload["retry_allowed"])
        self.assertFalse(payload["reentry_allowed"])

    def test_retry_loop_marks_exhausted_when_retry_budget_consumed(self) -> None:
        payload = self._build_retry_loop_payload(
            verification={
                "verification_status": "verified_failure",
                "verification_outcome": "completion_gap",
                "verification_validity": "valid",
                "closure_status": "not_closable",
                "closure_decision": "hold_for_followup",
            },
            execution_result={
                "execution_result_status": "failed",
                "execution_result_outcome": "tests_failed",
                "execution_result_validity": "valid",
                "execution_result_attempted": True,
            },
            run_state={"attempt_count": 2, "max_attempt_count": 2},
        )
        self.assertEqual(payload["retry_loop_status"], "exhausted")
        self.assertTrue(payload["retry_exhausted"])
        self.assertFalse(payload["retry_allowed"])

    def test_retry_loop_marks_exhausted_when_reentry_budget_consumed(self) -> None:
        payload = self._build_retry_loop_payload(
            verification={
                "verification_status": "verified_failure",
                "verification_outcome": "completion_gap",
                "verification_validity": "valid",
                "closure_status": "not_closable",
                "closure_decision": "hold_for_followup",
            },
            execution_result={
                "execution_result_status": "failed",
                "execution_result_outcome": "tests_failed",
                "execution_result_validity": "valid",
                "execution_result_attempted": True,
            },
            run_state={"reentry_count": 2, "max_reentry_count": 2},
        )
        self.assertEqual(payload["retry_loop_status"], "exhausted")
        self.assertTrue(payload["reentry_exhausted"])
        self.assertFalse(payload["reentry_allowed"])

    def test_retry_loop_detects_same_failure_or_no_progress_stop(self) -> None:
        payload = self._build_retry_loop_payload(
            verification={
                "verification_status": "verified_failure",
                "verification_outcome": "completion_gap",
                "verification_validity": "valid",
                "closure_status": "not_closable",
                "closure_decision": "hold_for_followup",
            },
            execution_result={
                "execution_result_status": "failed",
                "execution_result_outcome": "tests_failed",
                "execution_result_validity": "valid",
                "execution_result_attempted": True,
            },
            run_state={
                "same_failure_count": 2,
                "max_same_failure_count": 3,
                "no_progress_stop_required": True,
            },
        )
        self.assertEqual(payload["retry_loop_status"], "stop_required")
        self.assertEqual(payload["retry_loop_decision"], "stop_terminal")
        self.assertTrue(payload["no_progress_stop_required"])
        self.assertTrue(payload["terminal_stop_required"])
        self.assertFalse(payload["retry_allowed"])

    def test_retry_loop_reason_codes_are_deterministic(self) -> None:
        payload = self._build_retry_loop_payload(
            verification={
                "verification_status": "verified_failure",
                "verification_outcome": "completion_gap",
                "verification_validity": "valid",
                "closure_status": "not_closable",
                "closure_decision": "hold_for_followup",
            },
            execution_result={
                "execution_result_status": "failed",
                "execution_result_outcome": "tests_failed",
                "execution_result_validity": "valid",
                "execution_result_attempted": True,
            },
            repair_suggestion={"repair_suggestion_decision": "request_replan"},
            run_state={"attempt_count": 2, "max_attempt_count": 2},
        )
        self.assertEqual(payload["loop_primary_reason"], payload["loop_reason_codes"][0])
        self.assertEqual(payload["loop_reason_codes"][0], "retry_exhausted")
        self.assertIn("verification_terminal_failure", payload["loop_reason_codes"])
        self.assertLess(
            payload["loop_reason_codes"].index("retry_exhausted"),
            payload["loop_reason_codes"].index("verification_terminal_failure"),
        )

    def test_retry_loop_run_state_summary_surface_is_compact_and_enum_safe(self) -> None:
        compact = build_retry_reentry_loop_run_state_summary_surface(
            {
                "retry_loop_status": "bad_status",
                "retry_loop_decision": "bad_decision",
                "retry_loop_validity": "bad_validity",
                "retry_loop_confidence": "bad_confidence",
                "loop_primary_reason": "bad_reason",
                "attempt_count": 3,
                "max_attempt_count": 2,
                "reentry_count": 1,
                "max_reentry_count": 2,
                "same_failure_count": 1,
                "max_same_failure_count": 2,
                "retry_allowed": True,
                "reentry_allowed": True,
                "retry_exhausted": False,
                "reentry_exhausted": False,
                "same_failure_exhausted": False,
                "terminal_stop_required": True,
                "manual_escalation_required": False,
                "replan_required": False,
                "recollect_required": False,
                "same_lane_retry_allowed": False,
                "repair_retry_allowed": False,
                "no_progress_stop_required": True,
            }
        )
        self.assertEqual(
            set(compact.keys()),
            set(RETRY_REENTRY_LOOP_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertIn(compact["retry_loop_status"], RETRY_LOOP_STATUSES)
        self.assertIn(compact["retry_loop_decision"], RETRY_LOOP_DECISIONS)
        self.assertIn(compact["retry_loop_validity"], RETRY_LOOP_VALIDITIES)
        self.assertIn(compact["retry_loop_confidence"], RETRY_LOOP_CONFIDENCE_LEVELS)
        self.assertIn(compact["loop_primary_reason"], RETRY_LOOP_REASON_CODES)
        self.assertIsInstance(compact["retry_allowed"], bool)
        self.assertIsInstance(compact["reentry_allowed"], bool)
        self.assertIsInstance(compact["terminal_stop_required"], bool)

    def test_endgame_closure_contract_is_deterministic(self) -> None:
        kwargs = {
            "verification": {
                "verification_status": "verified_failure",
                "verification_outcome": "closure_followup",
                "verification_validity": "valid",
                "closure_status": "closure_pending",
                "closure_decision": "hold_for_followup",
                "objective_satisfied": True,
                "completion_satisfied": True,
                "closure_followup_required": True,
            },
            "retry_loop": {
                "retry_loop_status": "stop_required",
                "retry_loop_decision": "stop_terminal",
                "retry_allowed": False,
                "reentry_allowed": False,
                "terminal_stop_required": True,
            },
            "execution_result": {
                "execution_result_status": "succeeded",
                "execution_result_outcome": "changes_applied",
                "execution_result_validity": "valid",
            },
        }
        payload_a = self._build_endgame_payload(**kwargs)
        payload_b = self._build_endgame_payload(**kwargs)
        self.assertEqual(payload_a, payload_b)
        self.assertIn(payload_a["endgame_closure_status"], ENDGAME_CLOSURE_STATUSES)
        self.assertIn(payload_a["endgame_closure_outcome"], ENDGAME_CLOSURE_OUTCOMES)
        self.assertIn(payload_a["endgame_closure_validity"], ENDGAME_CLOSURE_VALIDITIES)
        self.assertIn(payload_a["endgame_closure_confidence"], ENDGAME_CLOSURE_CONFIDENCE_LEVELS)
        self.assertIn(payload_a["final_closure_class"], FINAL_CLOSURE_CLASSES)
        self.assertIn(payload_a["terminal_stop_class"], TERMINAL_STOP_CLASSES)
        self.assertIn(payload_a["closure_resolution_status"], CLOSURE_RESOLUTION_STATUSES)
        self.assertIn(payload_a["endgame_source_posture"], ENDGAME_SOURCE_POSTURES)
        self.assertEqual(payload_a["endgame_primary_reason"], payload_a["endgame_reason_codes"][0])

    def test_endgame_closure_classifies_safely_closed(self) -> None:
        payload = self._build_endgame_payload(
            verification={
                "verification_status": "verified_success",
                "verification_outcome": "objective_satisfied",
                "verification_validity": "valid",
                "closure_status": "safely_closable",
                "closure_decision": "close_ready",
                "objective_satisfied": True,
                "completion_satisfied": True,
            },
            retry_loop={
                "retry_loop_status": "not_applicable",
                "retry_loop_decision": "not_applicable",
                "retry_allowed": False,
                "reentry_allowed": False,
                "terminal_stop_required": False,
            },
            execution_result={
                "execution_result_status": "succeeded",
                "execution_result_outcome": "changes_applied",
                "execution_result_validity": "valid",
            },
            run_state={"lifecycle_closure_status": "safely_closed"},
        )
        self.assertEqual(payload["endgame_closure_status"], "safely_closed")
        self.assertEqual(payload["endgame_closure_outcome"], "terminal_success_closed")
        self.assertEqual(payload["final_closure_class"], "safely_closed")
        self.assertEqual(payload["terminal_stop_class"], "terminal_success")
        self.assertTrue(payload["safely_closed"])
        self.assertFalse(payload["further_retry_allowed"])
        self.assertFalse(payload["further_reentry_allowed"])

    def test_endgame_closure_classifies_completed_but_not_closed(self) -> None:
        payload = self._build_endgame_payload(
            verification={
                "verification_status": "verified_success",
                "verification_outcome": "closure_followup",
                "verification_validity": "partial",
                "closure_status": "closure_pending",
                "closure_decision": "hold_for_followup",
                "objective_satisfied": True,
                "completion_satisfied": True,
                "closure_followup_required": True,
            },
            retry_loop={
                "retry_loop_status": "stop_required",
                "retry_loop_decision": "hold",
                "retry_allowed": False,
                "reentry_allowed": False,
                "terminal_stop_required": True,
            },
            execution_result={
                "execution_result_status": "succeeded",
                "execution_result_outcome": "changes_applied",
                "execution_result_validity": "valid",
            },
            run_state={"lifecycle_execution_complete_not_closed": True},
        )
        self.assertEqual(payload["endgame_closure_status"], "not_closed")
        self.assertEqual(payload["final_closure_class"], "completed_but_not_closed")
        self.assertTrue(payload["completed_but_not_closed"])
        self.assertFalse(payload["safely_closed"])

    def test_endgame_closure_classifies_rollback_complete_not_closed(self) -> None:
        payload = self._build_endgame_payload(
            verification={
                "verification_status": "verified_failure",
                "verification_outcome": "rollback_consideration",
                "verification_validity": "valid",
                "closure_status": "not_closable",
                "closure_decision": "consider_rollback",
            },
            retry_loop={
                "retry_loop_status": "stop_required",
                "retry_loop_decision": "stop_terminal",
                "retry_allowed": False,
                "reentry_allowed": False,
                "terminal_stop_required": True,
            },
            execution_result={
                "execution_result_status": "failed",
                "execution_result_outcome": "tests_failed",
                "execution_result_validity": "valid",
            },
            run_state={"lifecycle_rollback_complete_not_closed": True},
        )
        self.assertEqual(payload["final_closure_class"], "rollback_complete_but_not_closed")
        self.assertTrue(payload["rollback_complete_but_not_closed"])
        self.assertFalse(payload["safely_closed"])

    def test_endgame_closure_classifies_manual_and_external_pending(self) -> None:
        manual_payload = self._build_endgame_payload(
            verification={
                "verification_status": "verified_failure",
                "verification_outcome": "manual_closure_only",
                "verification_validity": "valid",
                "closure_status": "manual_closure_only",
                "closure_decision": "manual_close",
                "manual_closure_required": True,
            },
            retry_loop={
                "retry_loop_status": "stop_required",
                "retry_loop_decision": "escalate_manual",
                "retry_allowed": False,
                "reentry_allowed": False,
                "manual_escalation_required": True,
                "terminal_stop_required": True,
            },
        )
        self.assertEqual(manual_payload["endgame_closure_status"], "manual_only")
        self.assertEqual(manual_payload["final_closure_class"], "manual_closure_only")
        self.assertEqual(manual_payload["terminal_stop_class"], "manual_terminal")

        external_payload = self._build_endgame_payload(
            verification={
                "verification_status": "inconclusive",
                "verification_outcome": "external_truth_pending",
                "verification_validity": "partial",
                "closure_status": "closure_pending",
                "closure_decision": "await_external_truth",
                "external_truth_required": True,
            },
            retry_loop={
                "retry_loop_status": "not_applicable",
                "retry_loop_decision": "hold",
                "retry_allowed": False,
                "reentry_allowed": False,
                "terminal_stop_required": True,
            },
        )
        self.assertEqual(external_payload["endgame_closure_status"], "closure_pending")
        self.assertEqual(external_payload["final_closure_class"], "external_truth_pending")
        self.assertEqual(external_payload["terminal_stop_class"], "external_wait_terminal")

    def test_endgame_closure_handles_insufficient_and_reason_order(self) -> None:
        insufficient = self._build_endgame_payload(
            verification={},
            retry_loop={},
            execution_result={},
            artifacts={},
        )
        self.assertEqual(insufficient["endgame_closure_status"], "insufficient_truth")
        self.assertEqual(insufficient["endgame_closure_validity"], "insufficient_truth")
        self.assertEqual(insufficient["endgame_primary_reason"], "insufficient_endgame_truth")

        ordered = self._build_endgame_payload(
            verification={
                "verification_status": "inconclusive",
                "verification_outcome": "unknown",
                "verification_validity": "partial",
                "closure_status": "unknown",
                "closure_decision": "cannot_determine",
            },
            retry_loop={
                "retry_loop_status": "exhausted",
                "retry_loop_decision": "stop_terminal",
                "retry_allowed": False,
                "reentry_allowed": False,
                "retry_exhausted": True,
                "reentry_exhausted": True,
                "same_failure_exhausted": True,
                "terminal_stop_required": True,
            },
        )
        self.assertEqual(ordered["endgame_primary_reason"], ordered["endgame_reason_codes"][0])
        self.assertIn(ordered["endgame_primary_reason"], ENDGAME_REASON_CODES)

    def test_endgame_closure_run_state_summary_surface_is_compact_and_enum_safe(self) -> None:
        compact = build_endgame_closure_run_state_summary_surface(
            {
                "endgame_closure_status": "bad_status",
                "endgame_closure_outcome": "bad_outcome",
                "endgame_closure_validity": "bad_validity",
                "endgame_closure_confidence": "bad_confidence",
                "final_closure_class": "bad_class",
                "terminal_stop_class": "bad_terminal",
                "closure_resolution_status": "bad_resolution",
                "endgame_primary_reason": "bad_reason",
                "retry_allowed": True,
                "reentry_allowed": True,
                "further_retry_allowed": True,
                "further_reentry_allowed": True,
            }
        )
        self.assertEqual(
            set(compact.keys()),
            set(ENDGAME_CLOSURE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertIn(compact["endgame_closure_status"], ENDGAME_CLOSURE_STATUSES)
        self.assertIn(compact["endgame_closure_outcome"], ENDGAME_CLOSURE_OUTCOMES)
        self.assertIn(compact["endgame_closure_validity"], ENDGAME_CLOSURE_VALIDITIES)
        self.assertIn(compact["endgame_closure_confidence"], ENDGAME_CLOSURE_CONFIDENCE_LEVELS)
        self.assertIn(compact["final_closure_class"], FINAL_CLOSURE_CLASSES)
        self.assertIn(compact["terminal_stop_class"], TERMINAL_STOP_CLASSES)
        self.assertIn(compact["closure_resolution_status"], CLOSURE_RESOLUTION_STATUSES)
        self.assertIn(compact["endgame_primary_reason"], ENDGAME_REASON_CODES)

    def test_loop_hardening_contract_is_deterministic(self) -> None:
        kwargs = {
            "execution_result": {
                "execution_result_status": "failed",
                "execution_result_outcome": "tests_failed",
                "execution_result_validity": "valid",
            },
            "verification": {
                "verification_status": "verified_failure",
                "verification_outcome": "completion_gap",
                "verification_validity": "valid",
                "closure_status": "not_closable",
                "closure_decision": "hold_for_followup",
            },
            "retry_loop": {
                "retry_loop_status": "retry_ready",
                "retry_loop_decision": "same_lane_retry",
                "retry_loop_validity": "valid",
                "same_failure_count": 1,
                "max_same_failure_count": 3,
            },
            "endgame": {
                "endgame_closure_status": "not_closed",
                "endgame_closure_validity": "valid",
                "final_closure_class": "terminal_non_success",
                "closure_resolution_status": "pending",
            },
        }
        payload_a = self._build_loop_hardening_payload(**kwargs)
        payload_b = self._build_loop_hardening_payload(**kwargs)
        self.assertEqual(payload_a, payload_b)
        self.assertIn(payload_a["loop_hardening_status"], LOOP_HARDENING_STATUSES)
        self.assertIn(payload_a["loop_hardening_decision"], LOOP_HARDENING_DECISIONS)
        self.assertIn(payload_a["loop_hardening_validity"], LOOP_HARDENING_VALIDITIES)
        self.assertIn(payload_a["loop_hardening_confidence"], LOOP_HARDENING_CONFIDENCE_LEVELS)
        self.assertIn(payload_a["same_failure_bucket"], SAME_FAILURE_BUCKETS)
        self.assertIn(payload_a["same_failure_persistence"], SAME_FAILURE_PERSISTENCE_STATUSES)
        self.assertIn(payload_a["no_progress_status"], NO_PROGRESS_STATUSES)
        self.assertIn(payload_a["oscillation_status"], OSCILLATION_STATUSES)
        self.assertIn(payload_a["retry_freeze_status"], RETRY_FREEZE_STATUSES)
        self.assertIn(payload_a["loop_hardening_source_posture"], LOOP_HARDENING_SOURCE_POSTURES)
        self.assertEqual(
            payload_a["loop_hardening_primary_reason"],
            payload_a["loop_hardening_reason_codes"][0],
        )

    def test_loop_hardening_detects_same_failure_and_stop(self) -> None:
        payload = self._build_loop_hardening_payload(
            execution_result={
                "execution_result_status": "failed",
                "execution_result_outcome": "tests_failed",
                "execution_result_validity": "valid",
            },
            verification={
                "verification_status": "verified_failure",
                "verification_outcome": "completion_gap",
                "verification_validity": "valid",
            },
            retry_loop={
                "retry_loop_status": "retry_ready",
                "retry_loop_decision": "same_lane_retry",
                "same_failure_count": 2,
                "max_same_failure_count": 2,
                "same_failure_exhausted": True,
            },
            endgame={
                "endgame_closure_status": "not_closed",
                "final_closure_class": "terminal_non_success",
            },
        )
        self.assertTrue(payload["same_failure_detected"])
        self.assertTrue(payload["same_failure_stop_required"])
        self.assertEqual(payload["loop_hardening_status"], "stop_required")
        self.assertTrue(payload["hardening_stop_required"])

    def test_loop_hardening_detects_no_progress_and_oscillation(self) -> None:
        payload = self._build_loop_hardening_payload(
            execution_result={
                "execution_result_status": "failed",
                "execution_result_outcome": "tests_failed",
                "execution_result_validity": "valid",
            },
            verification={
                "verification_status": "verified_failure",
                "verification_outcome": "completion_gap",
                "verification_validity": "valid",
            },
            retry_loop={
                "retry_loop_status": "retry_ready",
                "retry_loop_decision": "same_lane_retry",
                "attempt_count": 3,
                "same_failure_count": 2,
                "max_same_failure_count": 4,
                "no_progress_stop_required": True,
                "unstable_loop_suspected": True,
            },
            run_state={"prior_retry_class": "repair"},
        )
        self.assertTrue(payload["no_progress_detected"])
        self.assertTrue(payload["no_progress_stop_required"])
        self.assertTrue(payload["oscillation_detected"])
        self.assertTrue(payload["unstable_loop_detected"])

    def test_loop_hardening_safely_closed_is_not_applicable(self) -> None:
        payload = self._build_loop_hardening_payload(
            retry_loop={
                "retry_loop_status": "not_applicable",
                "retry_loop_decision": "not_applicable",
            },
            endgame={
                "endgame_closure_status": "safely_closed",
                "final_closure_class": "safely_closed",
                "safely_closed": True,
            },
        )
        self.assertEqual(payload["loop_hardening_status"], "not_applicable")
        self.assertEqual(payload["loop_hardening_decision"], "not_applicable")
        self.assertFalse(payload["hardening_stop_required"])

    def test_loop_hardening_handles_insufficient_truth(self) -> None:
        payload = self._build_loop_hardening_payload(
            completion={},
            approval={},
            reconcile={},
            execution_result={},
            verification={},
            retry_loop={},
            endgame={},
            artifacts={},
        )
        self.assertEqual(payload["loop_hardening_status"], "insufficient_truth")
        self.assertEqual(payload["loop_hardening_validity"], "insufficient_truth")
        self.assertTrue(payload["hardening_stop_required"])

    def test_loop_hardening_reason_codes_are_deterministic(self) -> None:
        payload = self._build_loop_hardening_payload(
            execution_result={
                "execution_result_status": "failed",
                "execution_result_outcome": "tests_failed",
                "execution_result_validity": "valid",
            },
            verification={
                "verification_status": "verified_failure",
                "verification_outcome": "completion_gap",
                "verification_validity": "valid",
            },
            retry_loop={
                "retry_loop_status": "retry_ready",
                "retry_loop_decision": "same_lane_retry",
                "same_failure_count": 2,
                "max_same_failure_count": 2,
                "same_failure_exhausted": True,
            },
        )
        self.assertEqual(
            payload["loop_hardening_primary_reason"],
            payload["loop_hardening_reason_codes"][0],
        )
        self.assertIn("same_failure_exhausted", payload["loop_hardening_reason_codes"])

    def test_loop_hardening_run_state_summary_surface_is_compact_and_enum_safe(self) -> None:
        compact = build_loop_hardening_run_state_summary_surface(
            {
                "loop_hardening_status": "bad_status",
                "loop_hardening_decision": "bad_decision",
                "loop_hardening_validity": "bad_validity",
                "loop_hardening_confidence": "bad_confidence",
                "loop_hardening_primary_reason": "bad_reason",
                "same_failure_bucket": "bad_bucket",
                "same_failure_persistence": "bad_persistence",
                "no_progress_status": "bad_progress",
                "oscillation_status": "bad_oscillation",
                "retry_freeze_status": "bad_freeze",
            }
        )
        self.assertEqual(
            set(compact.keys()),
            set(LOOP_HARDENING_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertIn(compact["loop_hardening_status"], LOOP_HARDENING_STATUSES)
        self.assertIn(compact["loop_hardening_decision"], LOOP_HARDENING_DECISIONS)
        self.assertIn(compact["loop_hardening_validity"], LOOP_HARDENING_VALIDITIES)
        self.assertIn(compact["loop_hardening_confidence"], LOOP_HARDENING_CONFIDENCE_LEVELS)
        self.assertIn(compact["loop_hardening_primary_reason"], LOOP_HARDENING_REASON_CODES)
        self.assertIn(compact["same_failure_bucket"], SAME_FAILURE_BUCKETS)
        self.assertIn(compact["same_failure_persistence"], SAME_FAILURE_PERSISTENCE_STATUSES)
        self.assertIn(compact["no_progress_status"], NO_PROGRESS_STATUSES)
        self.assertIn(compact["oscillation_status"], OSCILLATION_STATUSES)
        self.assertIn(compact["retry_freeze_status"], RETRY_FREEZE_STATUSES)

    def test_lane_stabilization_contract_is_deterministic(self) -> None:
        kwargs = {
            "execution_authorization": {"execution_authorization_status": "eligible"},
            "bounded_execution": {"bounded_execution_status": "ready"},
            "retry_loop": {
                "retry_loop_status": "retry_ready",
                "retry_loop_decision": "same_lane_retry",
                "max_attempt_count": 2,
                "max_reentry_count": 2,
            },
            "endgame": {
                "final_closure_class": "terminal_non_success",
                "closure_resolution_status": "pending",
            },
            "loop_hardening": {"loop_hardening_status": "stable", "loop_hardening_decision": "continue_bounded"},
            "run_state": {"next_safe_action": "proceed_to_pr", "policy_primary_action": "proceed_to_pr"},
        }
        payload_a = self._build_lane_stabilization_payload(**kwargs)
        payload_b = self._build_lane_stabilization_payload(**kwargs)
        self.assertEqual(payload_a, payload_b)
        self.assertIn(payload_a["lane_status"], LANE_STATUSES)
        self.assertIn(payload_a["lane_decision"], LANE_DECISIONS)
        self.assertIn(payload_a["lane_validity"], LANE_VALIDITIES)
        self.assertIn(payload_a["lane_confidence"], LANE_CONFIDENCE_LEVELS)
        self.assertIn(payload_a["current_lane"], LANE_VOCABULARY)
        self.assertIn(payload_a["target_lane"], LANE_VOCABULARY)
        self.assertIn(payload_a["lane_source_posture"], LANE_SOURCE_POSTURES)
        self.assertEqual(payload_a["lane_primary_reason"], payload_a["lane_reason_codes"][0])

    def test_lane_truth_gathering_inference(self) -> None:
        payload = self._build_lane_stabilization_payload(
            retry_loop={"retry_loop_status": "insufficient_truth", "retry_loop_decision": "recollect"},
            loop_hardening={"loop_hardening_status": "watch"},
        )
        self.assertEqual(payload["target_lane"], "truth_gathering")
        self.assertEqual(payload["lane_retry_policy_class"], "recollect_only")
        self.assertEqual(payload["lane_verification_policy_class"], "truth_check")
        self.assertFalse(payload["lane_execution_allowed"])

    def test_lane_replan_and_manual_and_closure_lane_inference(self) -> None:
        replan = self._build_lane_stabilization_payload(
            retry_loop={"retry_loop_decision": "replan", "replan_required": True},
            loop_hardening={"loop_hardening_status": "watch"},
        )
        self.assertEqual(replan["target_lane"], "replan_preparation")
        self.assertEqual(replan["lane_retry_policy_class"], "replan_only")

        manual = self._build_lane_stabilization_payload(
            retry_loop={"retry_loop_decision": "escalate_manual", "manual_escalation_required": True},
            loop_hardening={"loop_hardening_status": "watch"},
        )
        self.assertEqual(manual["target_lane"], "manual_review_preparation")
        self.assertEqual(manual["lane_retry_policy_class"], "manual_only")

        closure = self._build_lane_stabilization_payload(
            verification={"verification_outcome": "closure_followup"},
            endgame={"final_closure_class": "completed_but_not_closed", "closure_resolution_status": "pending"},
            loop_hardening={"loop_hardening_status": "watch"},
        )
        self.assertEqual(closure["target_lane"], "closure_followup")
        self.assertEqual(closure["lane_verification_policy_class"], "closure_check")

    def test_lane_bounded_execution_lane_and_hardening_block(self) -> None:
        ready = self._build_lane_stabilization_payload(
            execution_authorization={"execution_authorization_status": "eligible"},
            bounded_execution={"bounded_execution_status": "ready"},
            retry_loop={"retry_loop_status": "retry_ready", "retry_loop_decision": "same_lane_retry"},
            loop_hardening={"loop_hardening_status": "stable"},
            run_state={"next_safe_action": "proceed_to_pr", "policy_primary_action": "proceed_to_pr"},
        )
        self.assertEqual(ready["target_lane"], "bounded_github_update")
        self.assertTrue(ready["lane_execution_allowed"])

        blocked = self._build_lane_stabilization_payload(
            execution_authorization={"execution_authorization_status": "eligible"},
            bounded_execution={"bounded_execution_status": "ready"},
            retry_loop={"retry_loop_status": "retry_ready", "retry_loop_decision": "same_lane_retry"},
            loop_hardening={"loop_hardening_status": "freeze", "retry_freeze_required": True},
            run_state={"next_safe_action": "proceed_to_pr", "policy_primary_action": "proceed_to_pr"},
        )
        self.assertFalse(blocked["lane_execution_allowed"])
        self.assertIn(blocked["lane_status"], {"lane_valid", "lane_stop_required"})

    def test_lane_mismatch_and_transition_blocked(self) -> None:
        mismatch = self._build_lane_stabilization_payload(
            retry_loop={"retry_loop_decision": "replan", "replan_required": True},
            run_state={"current_lane": "bounded_local_patch", "lane_transition_count": 0},
            loop_hardening={"loop_hardening_status": "watch"},
        )
        self.assertEqual(mismatch["lane_status"], "lane_mismatch")
        self.assertTrue(mismatch["lane_mismatch_detected"])
        self.assertTrue(mismatch["lane_transition_required"])

        blocked = self._build_lane_stabilization_payload(
            retry_loop={"retry_loop_decision": "replan", "replan_required": True},
            run_state={
                "current_lane": "bounded_local_patch",
                "lane_transition_count": 2,
                "max_lane_transition_count": 2,
            },
            loop_hardening={"loop_hardening_status": "watch"},
        )
        self.assertIn(blocked["lane_status"], {"lane_mismatch", "lane_transition_blocked"})
        self.assertIn("transition_budget_exhausted", blocked["lane_reason_codes"])

    def test_lane_reason_codes_and_alias_non_duplication_are_deterministic(self) -> None:
        payload = self._build_lane_stabilization_payload(
            retry_loop={"retry_loop_decision": "recollect", "retry_loop_status": "insufficient_truth"},
            run_state={"lane_transition_count": 1, "lane_transition_count_compat": 1},
            loop_hardening={"loop_hardening_status": "watch"},
        )
        self.assertEqual(payload["lane_primary_reason"], payload["lane_reason_codes"][0])
        self.assertIn(payload["lane_primary_reason"], LANE_REASON_CODES)
        self.assertEqual(payload["lane_transition_count"], 1)

    def test_lane_run_state_summary_surface_is_compact_and_enum_safe(self) -> None:
        compact = build_lane_stabilization_run_state_summary_surface(
            {
                "lane_status": "bad_status",
                "lane_decision": "bad_decision",
                "lane_validity": "bad_validity",
                "lane_confidence": "bad_confidence",
                "current_lane": "bad_lane",
                "target_lane": "bad_lane",
                "lane_transition_status": "bad_transition_status",
                "lane_transition_decision": "bad_transition_decision",
                "lane_preconditions_status": "bad_preconditions",
                "lane_retry_policy_class": "bad_retry_policy",
                "lane_verification_policy_class": "bad_verification_policy",
                "lane_escalation_policy_class": "bad_escalation_policy",
                "lane_primary_reason": "bad_reason",
            }
        )
        self.assertEqual(set(compact.keys()), set(LANE_STABILIZATION_RUN_STATE_SUMMARY_SAFE_FIELDS))
        self.assertIn(compact["lane_status"], LANE_STATUSES)
        self.assertIn(compact["lane_decision"], LANE_DECISIONS)
        self.assertIn(compact["lane_validity"], LANE_VALIDITIES)
        self.assertIn(compact["lane_confidence"], LANE_CONFIDENCE_LEVELS)
        self.assertIn(compact["current_lane"], LANE_VOCABULARY)
        self.assertIn(compact["target_lane"], LANE_VOCABULARY)
        self.assertIn(compact["lane_transition_status"], LANE_TRANSITION_STATUSES)
        self.assertIn(compact["lane_transition_decision"], LANE_TRANSITION_DECISIONS)
        self.assertIn(compact["lane_preconditions_status"], LANE_PRECONDITIONS_STATUSES)
        self.assertIn(compact["lane_retry_policy_class"], LANE_RETRY_POLICY_CLASSES)
        self.assertIn(compact["lane_verification_policy_class"], LANE_VERIFICATION_POLICY_CLASSES)
        self.assertIn(compact["lane_escalation_policy_class"], LANE_ESCALATION_POLICY_CLASSES)
        self.assertIn(compact["lane_primary_reason"], LANE_REASON_CODES)

    def test_observability_rollup_contract_is_deterministic(self) -> None:
        payload_a = self._build_observability_payload(
            execution_result={"execution_result_status": "succeeded"},
            verification={"verification_outcome": "objective_satisfied"},
            retry_loop={"retry_loop_status": "not_applicable", "attempt_count": 1},
            endgame={
                "final_closure_class": "safely_closed",
                "terminal_stop_class": "terminal_success",
            },
            loop_hardening={"loop_hardening_status": "not_applicable"},
            lane={
                "lane_status": "not_applicable",
                "current_lane": "closure_followup",
                "lane_valid": True,
                "lane_execution_allowed": False,
            },
            run_state={"state": "completed"},
        )
        payload_b = self._build_observability_payload(
            execution_result={"execution_result_status": "succeeded"},
            verification={"verification_outcome": "objective_satisfied"},
            retry_loop={"retry_loop_status": "not_applicable", "attempt_count": 1},
            endgame={
                "final_closure_class": "safely_closed",
                "terminal_stop_class": "terminal_success",
            },
            loop_hardening={"loop_hardening_status": "not_applicable"},
            lane={
                "lane_status": "not_applicable",
                "current_lane": "closure_followup",
                "lane_valid": True,
                "lane_execution_allowed": False,
            },
            run_state={"state": "completed"},
        )
        self.assertEqual(payload_a, payload_b)
        self.assertEqual(payload_a["run_terminal_class"], "safely_closed")
        self.assertTrue(payload_a["run_safely_closed"])
        self.assertEqual(payload_a["observability_primary_reason"], "safely_closed_terminal")
        self.assertIn(payload_a["observability_status"], OBSERVABILITY_STATUSES)
        self.assertIn(payload_a["observability_validity"], OBSERVABILITY_VALIDITIES)
        self.assertIn(payload_a["observability_confidence"], OBSERVABILITY_CONFIDENCE_LEVELS)
        self.assertIn(payload_a["run_terminal_class"], RUN_TERMINAL_CLASSES)
        self.assertEqual(
            payload_a["observability_primary_reason"],
            payload_a["observability_reason_codes"][0],
        )
        self.assertIn(payload_a["observability_primary_reason"], OBSERVABILITY_REASON_CODES)

    def test_observability_rollup_distinguishes_missing_vs_malformed(self) -> None:
        missing = self._build_observability_payload(
            artifact_presence={"run_state.json": True},
            execution_result={"execution_result_status": "unknown"},
        )
        malformed = self._build_observability_payload(
            verification=["malformed"],
            execution_result={"execution_result_status": "unknown"},
        )
        self.assertTrue(missing["artifact_missing_detected"])
        self.assertFalse(missing["artifact_malformed_detected"])
        self.assertEqual(missing["observability_status"], "partial")
        self.assertEqual(missing["observability_primary_reason"], "missing_required_artifact")
        self.assertTrue(malformed["artifact_malformed_detected"])
        self.assertEqual(malformed["observability_status"], "degraded")
        self.assertEqual(malformed["observability_validity"], "malformed")
        self.assertEqual(
            malformed["observability_primary_reason"],
            "malformed_observability_inputs",
        )

    def test_failure_bucket_rollup_precedence_and_reason_order_are_deterministic(self) -> None:
        observability = self._build_observability_payload(
            execution_result={"execution_result_status": "partial"},
            verification={"verification_status": "not_verifiable"},
            artifact_presence={"run_state.json": True},
        )
        payload = build_failure_bucket_rollup_surface(
            run_id="job-failure-bucket",
            objective_contract_payload={"objective_id": "objective-failure-bucket"},
            execution_result_contract_payload={"execution_result_status": "failed"},
            verification_closure_contract_payload={
                "verification_status": "not_verifiable",
                "verification_validity": "insufficient_truth",
                "verification_outcome": "objective_gap",
            },
            retry_reentry_loop_contract_payload={"retry_loop_status": "stop_required"},
            endgame_closure_contract_payload={"final_closure_class": "closure_unresolved"},
            loop_hardening_contract_payload={"same_failure_bucket": "bad_bucket"},
            lane_stabilization_contract_payload={"lane_status": "lane_mismatch"},
            observability_rollup_payload=observability,
            run_state_payload={},
        )
        self.assertEqual(payload["primary_failure_bucket"], "truth_missing")
        self.assertEqual(payload["failure_bucket_status"], "insufficient_truth")
        self.assertEqual(payload["same_failure_bucket"], "truth_missing")
        self.assertEqual(
            payload["failure_bucket_primary_reason"],
            payload["failure_bucket_reason_codes"][0],
        )
        self.assertIn(payload["failure_bucket_status"], FAILURE_BUCKET_STATUSES)
        self.assertIn(payload["failure_bucket_validity"], FAILURE_BUCKET_VALIDITIES)
        self.assertIn(payload["failure_bucket_confidence"], FAILURE_BUCKET_CONFIDENCE_LEVELS)
        self.assertIn(payload["failure_bucket_primary_reason"], FAILURE_BUCKET_REASON_CODES)
        self.assertIn(payload["primary_failure_bucket"], FAILURE_BUCKET_VOCABULARY)
        emitted = [payload["primary_failure_bucket"], *payload["secondary_failure_buckets"]]
        self.assertEqual(payload["bucket_count"], len(set(emitted)))

    def test_fleet_run_rollup_maps_increments_deterministically(self) -> None:
        observability = self._build_observability_payload(
            execution_result={"execution_result_status": "failed"},
            verification={"verification_outcome": "closure_followup"},
            retry_loop={
                "retry_loop_status": "exhausted",
                "retry_exhausted": True,
                "no_progress_stop_required": True,
            },
            endgame={"final_closure_class": "terminal_non_success"},
            loop_hardening={"loop_hardening_status": "stop_required"},
            lane={"lane_status": "lane_mismatch", "current_lane": "replan_preparation"},
            run_state={"state": "paused"},
        )
        failure_bucket = build_failure_bucket_rollup_surface(
            run_id="job-fleet-rollup",
            objective_contract_payload={"objective_id": "objective-fleet-rollup"},
            execution_result_contract_payload={"execution_result_status": "failed"},
            verification_closure_contract_payload={"verification_outcome": "closure_followup"},
            retry_reentry_loop_contract_payload={
                "retry_loop_status": "exhausted",
                "no_progress_stop_required": True,
            },
            endgame_closure_contract_payload={"final_closure_class": "terminal_non_success"},
            loop_hardening_contract_payload={"loop_hardening_status": "stop_required"},
            lane_stabilization_contract_payload={"lane_status": "lane_mismatch"},
            observability_rollup_payload=observability,
            run_state_payload={},
        )
        fleet = build_fleet_run_rollup_surface(
            run_id="job-fleet-rollup",
            objective_contract_payload={"objective_id": "objective-fleet-rollup"},
            observability_rollup_payload=observability,
            failure_bucket_rollup_payload=failure_bucket,
            verification_closure_contract_payload={"verification_outcome": "closure_followup"},
            retry_reentry_loop_contract_payload={"retry_loop_status": "exhausted"},
            endgame_closure_contract_payload={"final_closure_class": "terminal_non_success"},
            loop_hardening_contract_payload={"loop_hardening_status": "stop_required"},
            lane_stabilization_contract_payload={"lane_status": "lane_mismatch"},
            execution_result_contract_payload={"execution_result_status": "failed"},
        )
        self.assertEqual(fleet["fleet_started_increment"], 1)
        self.assertEqual(fleet["fleet_safely_closed_increment"], 0)
        self.assertEqual(fleet["fleet_retry_exhausted_increment"], 1)
        self.assertEqual(fleet["fleet_no_progress_stop_increment"], 1)
        self.assertIn(fleet["fleet_primary_failure_bucket"], FAILURE_BUCKET_VOCABULARY)
        for key in (
            "fleet_started_increment",
            "fleet_completed_increment",
            "fleet_safely_closed_increment",
            "fleet_manual_escalation_increment",
            "fleet_replan_increment",
            "fleet_no_progress_stop_increment",
            "fleet_retry_exhausted_increment",
            "fleet_artifact_missing_increment",
            "fleet_artifact_malformed_increment",
        ):
            self.assertIn(fleet[key], {0, 1})

    def test_observability_rollup_summary_surfaces_are_compact(self) -> None:
        compact = build_observability_rollup_run_state_summary_surface(
            {
                "observability_status": "ready",
                "run_terminal_class": "safely_closed",
                "observability_primary_reason": "safely_closed_terminal",
                "lane": "closure_followup",
            }
        )
        self.assertEqual(
            set(compact.keys()),
            set(OBSERVABILITY_ROLLUP_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(compact["observability_rollup_present"])

        summary = build_observability_rollup_contract_summary_surface(
            {"observability_status": "bad", "run_terminal_class": "bad"}
        )
        self.assertEqual(
            set(summary.keys()),
            set(OBSERVABILITY_ROLLUP_SUMMARY_SAFE_FIELDS),
        )
        self.assertIn(summary["observability_status"], OBSERVABILITY_STATUSES)
        self.assertIn(summary["run_terminal_class"], RUN_TERMINAL_CLASSES)

        bucket_summary = build_failure_bucket_rollup_summary_surface(
            {"failure_bucket_status": "bad", "primary_failure_bucket": "bad"}
        )
        self.assertEqual(
            set(bucket_summary.keys()),
            set(FAILURE_BUCKET_ROLLUP_SUMMARY_SAFE_FIELDS),
        )
        self.assertIn(bucket_summary["failure_bucket_status"], FAILURE_BUCKET_STATUSES)
        self.assertIn(bucket_summary["primary_failure_bucket"], FAILURE_BUCKET_VOCABULARY)

        fleet_summary = build_fleet_run_rollup_summary_surface(
            {"fleet_primary_failure_bucket": "bad", "fleet_observability_status": "bad"}
        )
        self.assertEqual(
            set(fleet_summary.keys()),
            set(FLEET_RUN_ROLLUP_SUMMARY_SAFE_FIELDS),
        )
        self.assertIn(fleet_summary["fleet_primary_failure_bucket"], FAILURE_BUCKET_VOCABULARY)
        self.assertIn(fleet_summary["fleet_observability_status"], OBSERVABILITY_STATUSES)

    def test_failure_bucketing_hardening_is_deterministic_and_precedence_ordered(self) -> None:
        payload_a = self._build_failure_bucketing_hardening_payload(
            verification={
                "verification_status": "not_verifiable",
                "verification_validity": "insufficient_truth",
            },
            loop_hardening={
                "same_failure_bucket": "truth_missing",
                "same_failure_signature": "truth_missing|verification_status:not_verifiable",
            },
            failure_bucket_rollup={"primary_failure_bucket": "truth_missing"},
            observability={"observability_status": "partial"},
        )
        payload_b = self._build_failure_bucketing_hardening_payload(
            verification={
                "verification_status": "not_verifiable",
                "verification_validity": "insufficient_truth",
            },
            loop_hardening={
                "same_failure_bucket": "truth_missing",
                "same_failure_signature": "truth_missing|verification_status:not_verifiable",
            },
            failure_bucket_rollup={"primary_failure_bucket": "truth_missing"},
            observability={"observability_status": "partial"},
        )
        self.assertEqual(payload_a, payload_b)
        self.assertEqual(payload_a["primary_failure_bucket"], "truth_missing")
        self.assertEqual(payload_a["failure_bucketing_status"], "insufficient_truth")
        self.assertTrue(payload_a["bucket_alias_deduplicated"])
        self.assertEqual(payload_a["bucket_count"], 1)
        self.assertEqual(
            payload_a["failure_bucketing_primary_reason"],
            payload_a["failure_bucketing_reason_codes"][0],
        )
        self.assertIn(payload_a["failure_bucketing_status"], FAILURE_BUCKETING_STATUSES)
        self.assertIn(payload_a["failure_bucketing_validity"], FAILURE_BUCKETING_VALIDITIES)
        self.assertIn(
            payload_a["failure_bucketing_confidence"],
            FAILURE_BUCKETING_CONFIDENCE_LEVELS,
        )
        self.assertIn(
            payload_a["failure_bucketing_primary_reason"],
            FAILURE_BUCKETING_REASON_CODES,
        )
        self.assertIn(payload_a["primary_failure_bucket"], HARDENED_FAILURE_BUCKET_VOCABULARY)

    def test_failure_bucketing_hardening_truth_conflict_vs_truth_missing(self) -> None:
        missing = self._build_failure_bucketing_hardening_payload(
            verification={
                "verification_status": "not_verifiable",
                "verification_validity": "insufficient_truth",
            },
            observability={"observability_status": "partial"},
            failure_bucket_rollup={"primary_failure_bucket": "unknown"},
        )
        conflict = self._build_failure_bucketing_hardening_payload(
            endgame={"final_closure_class": "safely_closed"},
            execution_authorization={"execution_authorization_status": "denied"},
            bounded_execution={"bounded_execution_status": "ready"},
            observability={"observability_status": "ready"},
            failure_bucket_rollup={"primary_failure_bucket": "execution_failure"},
        )
        self.assertEqual(missing["primary_failure_bucket"], "truth_missing")
        self.assertEqual(conflict["primary_failure_bucket"], "truth_conflict")
        self.assertIn(conflict["bucket_stability_class"], BUCKET_STABILITY_CLASSES)

    def test_failure_bucketing_hardening_distinctions_and_mappings(self) -> None:
        execution_failure = self._build_failure_bucketing_hardening_payload(
            execution_result={"execution_result_status": "failed"},
            verification={"verification_status": "verified_failure"},
            observability={"observability_status": "ready"},
            failure_bucket_rollup={"primary_failure_bucket": "execution_failure"},
        )
        verification_failure = self._build_failure_bucketing_hardening_payload(
            execution_result={"execution_result_status": "succeeded"},
            verification={
                "verification_status": "verified_failure",
                "verification_outcome": "closure_followup",
            },
            observability={"observability_status": "ready"},
            failure_bucket_rollup={"primary_failure_bucket": "verification_failure"},
        )
        retry_exhausted = self._build_failure_bucketing_hardening_payload(
            retry_loop={"retry_loop_status": "exhausted", "retry_exhausted": True},
            loop_hardening={"same_failure_stop_required": True, "same_failure_persistence": "high"},
            observability={"observability_status": "ready"},
            failure_bucket_rollup={"primary_failure_bucket": "same_failure_exhausted"},
        )
        no_progress = self._build_failure_bucketing_hardening_payload(
            loop_hardening={
                "no_progress_stop_required": True,
                "no_progress_status": "confirmed",
                "oscillation_status": "confirmed",
            },
            observability={"observability_status": "ready"},
            failure_bucket_rollup={"primary_failure_bucket": "oscillation"},
        )
        manual_only = self._build_failure_bucketing_hardening_payload(
            endgame={"final_closure_class": "manual_closure_only"},
            observability={"observability_status": "ready"},
            failure_bucket_rollup={"primary_failure_bucket": "closure_unresolved"},
        )
        self.assertEqual(execution_failure["primary_failure_bucket"], "execution_failure")
        self.assertEqual(verification_failure["primary_failure_bucket"], "verification_failure")
        self.assertEqual(retry_exhausted["primary_failure_bucket"], "retry_exhausted")
        self.assertEqual(no_progress["primary_failure_bucket"], "no_progress")
        self.assertEqual(manual_only["primary_failure_bucket"], "manual_only")
        self.assertEqual(manual_only["bucket_terminality_class"], "manual_only")
        self.assertIn(manual_only["bucket_severity"], BUCKET_SEVERITIES)
        self.assertIn(manual_only["bucket_terminality_class"], BUCKET_TERMINALITY_CLASSES)

    def test_failure_bucketing_hardening_summary_surfaces_are_compact(self) -> None:
        compact = build_failure_bucketing_hardening_run_state_summary_surface(
            {"failure_bucketing_status": "classified"}
        )
        self.assertEqual(
            set(compact.keys()),
            set(FAILURE_BUCKETING_HARDENING_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(compact["failure_bucketing_hardening_present"])

        summary = build_failure_bucketing_hardening_summary_surface(
            {
                "failure_bucketing_status": "bad",
                "failure_bucketing_validity": "bad",
                "failure_bucketing_confidence": "bad",
                "primary_failure_bucket": "bad",
                "bucket_family": "bad",
                "bucket_severity": "bad",
                "bucket_stability_class": "bad",
                "bucket_terminality_class": "bad",
                "failure_bucketing_primary_reason": "bad",
            }
        )
        self.assertEqual(
            set(summary.keys()),
            set(FAILURE_BUCKETING_HARDENING_SUMMARY_SAFE_FIELDS),
        )
        self.assertIn(summary["failure_bucketing_status"], FAILURE_BUCKETING_STATUSES)
        self.assertIn(summary["failure_bucketing_validity"], FAILURE_BUCKETING_VALIDITIES)
        self.assertIn(
            summary["failure_bucketing_confidence"],
            FAILURE_BUCKETING_CONFIDENCE_LEVELS,
        )
        self.assertIn(summary["primary_failure_bucket"], HARDENED_FAILURE_BUCKET_VOCABULARY)
        self.assertIn(summary["failure_bucketing_primary_reason"], FAILURE_BUCKETING_REASON_CODES)

    def test_retention_manifest_and_contract_are_deterministic(self) -> None:
        manifest_a = self._build_retention_manifest_payload()
        manifest_b = self._build_retention_manifest_payload()
        self.assertEqual(manifest_a, manifest_b)
        retention_a = self._build_artifact_retention_payload(retention_manifest=manifest_a)
        retention_b = self._build_artifact_retention_payload(retention_manifest=manifest_b)
        self.assertEqual(retention_a, retention_b)
        self.assertIn(retention_a["artifact_retention_status"], ARTIFACT_RETENTION_STATUSES)
        self.assertIn(retention_a["artifact_retention_validity"], ARTIFACT_RETENTION_VALIDITIES)
        self.assertIn(
            retention_a["artifact_retention_confidence"],
            ARTIFACT_RETENTION_CONFIDENCE_LEVELS,
        )
        self.assertEqual(retention_a["retention_primary_reason"], retention_a["retention_reason_codes"][0])
        self.assertIn(retention_a["retention_primary_reason"], ARTIFACT_RETENTION_REASON_CODES)

    def test_retention_distinguishes_canonical_summary_superseded_and_prunable(self) -> None:
        retention_manifest = self._build_retention_manifest_payload()
        self.assertGreater(retention_manifest["canonical_artifact_count"], 0)
        self.assertIn("objective_contract", retention_manifest["summary_safe_refs"])
        self.assertIn("objective_contract", retention_manifest["path_refs"])
        self.assertGreaterEqual(retention_manifest["superseded_artifact_count"], 1)
        self.assertGreaterEqual(retention_manifest["prunable_artifact_count"], 1)
        self.assertTrue(retention_manifest["alias_deduplicated"])

        retention = self._build_artifact_retention_payload(retention_manifest=retention_manifest)
        self.assertGreater(retention["canonical_artifact_count"], 0)
        self.assertGreater(retention["summary_ref_count"], 0)
        self.assertGreater(retention["path_ref_count"], 0)
        self.assertGreaterEqual(retention["superseded_artifact_count"], 1)
        self.assertGreaterEqual(retention["prunable_artifact_count"], 1)
        self.assertIn(retention["retention_policy_class"], RETENTION_POLICY_CLASSES)
        self.assertIn(retention["retention_compaction_class"], RETENTION_COMPACTION_CLASSES)

    def test_retention_alias_non_dup_and_reference_consistency(self) -> None:
        retention_manifest = self._build_retention_manifest_payload()
        retention = self._build_artifact_retention_payload(retention_manifest=retention_manifest)
        self.assertTrue(retention["retention_alias_deduplicated"])
        self.assertTrue(retention["retention_reference_consistent"])
        self.assertGreaterEqual(retention["artifact_count"], retention["canonical_artifact_count"])
        self.assertGreater(retention["alias_ref_count"], 0)

    def test_retention_detects_malformed_reference_layout(self) -> None:
        malformed_manifest = build_retention_manifest_surface(
            run_id="job-retention-malformed",
            objective_contract_payload={"objective_id": "objective-retention"},
            paths_by_role=[],
            summaries_by_role={},
            contract_artifact_index_payload={},
            manifest_payload={},
        )
        self.assertEqual(malformed_manifest["retention_manifest_primary_reason"], "malformed_reference_layout")

        malformed_retention = build_artifact_retention_contract_surface(
            run_id="job-retention-malformed",
            objective_contract_payload={"objective_id": "objective-retention"},
            retention_manifest_payload=[],
            contract_artifact_index_payload={},
            observability_rollup_payload={},
            failure_bucketing_hardening_payload={},
            endgame_closure_contract_payload={},
        )
        self.assertEqual(malformed_retention["artifact_retention_status"], "degraded")
        self.assertEqual(malformed_retention["artifact_retention_validity"], "malformed")

    def test_retention_summary_surfaces_are_compact(self) -> None:
        compact = build_artifact_retention_run_state_summary_surface(
            {"artifact_retention_status": "ready"}
        )
        self.assertEqual(
            set(compact.keys()),
            set(ARTIFACT_RETENTION_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(compact["artifact_retention_present"])

        retention_summary = build_artifact_retention_summary_surface(
            {
                "artifact_retention_status": "bad",
                "artifact_retention_validity": "bad",
                "artifact_retention_confidence": "bad",
                "retention_policy_class": "bad",
                "retention_compaction_class": "bad",
                "retention_primary_reason": "bad",
            }
        )
        self.assertEqual(
            set(retention_summary.keys()),
            set(ARTIFACT_RETENTION_SUMMARY_SAFE_FIELDS),
        )
        self.assertIn(retention_summary["artifact_retention_status"], ARTIFACT_RETENTION_STATUSES)
        self.assertIn(retention_summary["artifact_retention_validity"], ARTIFACT_RETENTION_VALIDITIES)
        self.assertIn(
            retention_summary["artifact_retention_confidence"],
            ARTIFACT_RETENTION_CONFIDENCE_LEVELS,
        )
        self.assertIn(retention_summary["retention_policy_class"], RETENTION_POLICY_CLASSES)
        self.assertIn(retention_summary["retention_compaction_class"], RETENTION_COMPACTION_CLASSES)
        self.assertIn(retention_summary["retention_primary_reason"], ARTIFACT_RETENTION_REASON_CODES)

        manifest_summary = build_retention_manifest_summary_surface(
            {
                "reference_layout_version": "v1",
                "reference_order_stable": True,
                "alias_deduplicated": True,
                "manifest_compact": True,
                "canonical_artifact_count": 3,
                "superseded_artifact_count": 1,
                "prunable_artifact_count": 1,
                "retention_manifest_primary_reason": "canonical_reference_layout_ready",
            }
        )
        self.assertEqual(
            set(manifest_summary.keys()),
            set(RETENTION_MANIFEST_SUMMARY_SAFE_FIELDS),
        )

    def test_fleet_safety_control_is_deterministic_and_manual_only_mapped(self) -> None:
        payload_a = self._build_fleet_safety_payload(
            endgame={"final_closure_class": "manual_closure_only"},
            hard_bucket={
                "primary_failure_bucket": "manual_only",
                "bucket_severity": "high",
                "bucket_stability_class": "stable",
                "bucket_terminality_class": "manual_only",
            },
            retry_loop={"retry_loop_status": "stop_required", "manual_escalation_required": True},
            lane={
                "lane_status": "lane_valid",
                "current_lane": "manual_review_preparation",
                "lane_execution_allowed": False,
            },
        )
        payload_b = self._build_fleet_safety_payload(
            endgame={"final_closure_class": "manual_closure_only"},
            hard_bucket={
                "primary_failure_bucket": "manual_only",
                "bucket_severity": "high",
                "bucket_stability_class": "stable",
                "bucket_terminality_class": "manual_only",
            },
            retry_loop={"retry_loop_status": "stop_required", "manual_escalation_required": True},
            lane={
                "lane_status": "lane_valid",
                "current_lane": "manual_review_preparation",
                "lane_execution_allowed": False,
            },
        )
        self.assertEqual(payload_a, payload_b)
        self.assertEqual(payload_a["fleet_safety_status"], "stop")
        self.assertEqual(payload_a["fleet_safety_decision"], "escalate_manual")
        self.assertEqual(payload_a["fleet_restart_decision"], "manual_only")
        self.assertTrue(payload_a["fleet_manual_review_required"])
        self.assertIn(payload_a["fleet_safety_status"], FLEET_SAFETY_STATUSES)
        self.assertIn(payload_a["fleet_safety_validity"], FLEET_SAFETY_VALIDITIES)
        self.assertIn(payload_a["fleet_safety_confidence"], FLEET_SAFETY_CONFIDENCE_LEVELS)
        self.assertIn(payload_a["fleet_safety_decision"], FLEET_SAFETY_DECISIONS)
        self.assertIn(payload_a["fleet_restart_decision"], FLEET_RESTART_DECISIONS)
        self.assertIn(payload_a["fleet_safety_scope"], FLEET_SAFETY_SCOPES)
        self.assertIn(payload_a["fleet_safety_primary_reason"], FLEET_SAFETY_REASON_CODES)
        self.assertEqual(
            payload_a["fleet_safety_primary_reason"],
            payload_a["fleet_safety_reason_codes"][0],
        )

    def test_fleet_safety_control_distinguishes_hold_and_freeze(self) -> None:
        hold_payload = self._build_fleet_safety_payload(
            observability={"observability_status": "partial"},
            endgame={"final_closure_class": "completed_but_not_closed"},
            lane={
                "lane_status": "lane_transition_blocked",
                "current_lane": "truth_gathering",
                "lane_execution_allowed": False,
                "lane_transition_blocked": True,
            },
            hard_bucket={
                "primary_failure_bucket": "execution_failure",
                "bucket_severity": "medium",
                "bucket_stability_class": "ambiguous",
                "bucket_terminality_class": "non_terminal",
            },
        )
        freeze_payload = self._build_fleet_safety_payload(
            observability={"observability_status": "ready"},
            endgame={"final_closure_class": "completed_but_not_closed"},
            lane={
                "lane_status": "lane_mismatch",
                "current_lane": "bounded_local_patch",
                "lane_execution_allowed": False,
                "lane_mismatch_detected": True,
            },
            hard_bucket={
                "primary_failure_bucket": "lane_mismatch",
                "bucket_severity": "high",
                "bucket_stability_class": "stable",
                "bucket_terminality_class": "non_terminal",
            },
        )
        self.assertEqual(hold_payload["fleet_safety_status"], "hold")
        self.assertEqual(hold_payload["fleet_safety_decision"], "hold_for_review")
        self.assertEqual(freeze_payload["fleet_safety_status"], "freeze")
        self.assertEqual(freeze_payload["fleet_safety_decision"], "freeze_run")

    def test_fleet_safety_control_distinguishes_freeze_and_stop(self) -> None:
        freeze_payload = self._build_fleet_safety_payload(
            loop_hardening={"loop_hardening_status": "stop_required", "no_progress_stop_required": True},
            retry_loop={"retry_loop_status": "exhausted", "same_failure_exhausted": True, "same_failure_count": 3},
            hard_bucket={
                "primary_failure_bucket": "same_failure_exhausted",
                "bucket_severity": "high",
                "bucket_stability_class": "stable",
                "bucket_terminality_class": "non_terminal",
            },
        )
        stop_payload = self._build_fleet_safety_payload(
            endgame={"final_closure_class": "terminal_non_success"},
            hard_bucket={
                "primary_failure_bucket": "terminal_non_success",
                "bucket_severity": "high",
                "bucket_stability_class": "stable",
                "bucket_terminality_class": "terminal",
            },
            lane={"lane_status": "lane_valid", "current_lane": "closure_followup", "lane_execution_allowed": False},
        )
        self.assertEqual(freeze_payload["fleet_safety_status"], "freeze")
        self.assertEqual(stop_payload["fleet_safety_status"], "stop")
        self.assertTrue(stop_payload["fleet_run_stop_required"])
        self.assertFalse(stop_payload["fleet_run_allowed"])

    def test_fleet_safety_control_restart_allowed_vs_blocked(self) -> None:
        allowed_payload = self._build_fleet_safety_payload(
            observability={"observability_status": "ready"},
            endgame={"final_closure_class": "safely_closed"},
            hard_bucket={
                "primary_failure_bucket": "execution_failure",
                "bucket_severity": "low",
                "bucket_stability_class": "stable",
                "bucket_terminality_class": "non_terminal",
            },
            lane={"lane_status": "lane_valid", "current_lane": "closure_followup", "lane_execution_allowed": True},
        )
        blocked_payload = self._build_fleet_safety_payload(
            endgame={"final_closure_class": "terminal_non_success"},
            hard_bucket={
                "primary_failure_bucket": "terminal_non_success",
                "bucket_severity": "high",
                "bucket_stability_class": "stable",
                "bucket_terminality_class": "terminal",
            },
        )
        self.assertEqual(allowed_payload["fleet_safety_status"], "allow")
        self.assertEqual(allowed_payload["fleet_restart_decision"], "restart_allowed")
        self.assertTrue(allowed_payload["fleet_restart_allowed"])
        self.assertFalse(allowed_payload["fleet_restart_blocked"])
        self.assertEqual(blocked_payload["fleet_restart_decision"], "restart_blocked")
        self.assertFalse(blocked_payload["fleet_restart_allowed"])
        self.assertTrue(blocked_payload["fleet_restart_blocked"])

    def test_fleet_safety_control_risk_class_mappings(self) -> None:
        lane_sensitive = self._build_fleet_safety_payload(
            lane={
                "lane_status": "lane_mismatch",
                "current_lane": "bounded_github_update",
                "lane_execution_allowed": False,
                "lane_mismatch_detected": True,
            },
            hard_bucket={
                "primary_failure_bucket": "lane_mismatch",
                "bucket_severity": "high",
                "bucket_stability_class": "stable",
                "bucket_terminality_class": "non_terminal",
            },
        )
        bucket_sensitive = self._build_fleet_safety_payload(
            hard_bucket={
                "primary_failure_bucket": "execution_failure",
                "bucket_severity": "critical",
                "bucket_stability_class": "stable",
                "bucket_terminality_class": "terminal",
            },
            lane={"lane_status": "lane_valid", "current_lane": "closure_followup", "lane_execution_allowed": True},
        )
        repeat_risky = self._build_fleet_safety_payload(
            retry_loop={"retry_loop_status": "exhausted", "same_failure_count": 3, "same_failure_exhausted": True},
            loop_hardening={"loop_hardening_status": "stop_required", "no_progress_stop_required": True},
            hard_bucket={
                "primary_failure_bucket": "same_failure_exhausted",
                "bucket_severity": "high",
                "bucket_stability_class": "stable",
                "bucket_terminality_class": "non_terminal",
            },
        )
        self.assertEqual(lane_sensitive["fleet_safety_scope"], "lane_sensitive")
        self.assertIn(lane_sensitive["fleet_lane_risk_class"], FLEET_LANE_RISK_CLASSES)
        self.assertEqual(bucket_sensitive["fleet_safety_scope"], "bucket_sensitive")
        self.assertIn(bucket_sensitive["fleet_bucket_risk_class"], FLEET_BUCKET_RISK_CLASSES)
        self.assertIn(repeat_risky["fleet_repeat_risk_class"], FLEET_REPEAT_RISK_CLASSES)
        self.assertEqual(repeat_risky["fleet_repeat_risk_class"], "repeat_blocked")

    def test_fleet_safety_control_degraded_vs_insufficient_truth(self) -> None:
        degraded = self._build_fleet_safety_payload(
            observability={"observability_status": "ready"},
            retention={
                "artifact_retention_status": "ready",
                "artifact_retention_validity": "malformed",
                "retention_reference_consistent": False,
                "retention_manifest_compact": True,
            },
        )
        insufficient = self._build_fleet_safety_payload(
            observability={"observability_status": "insufficient_truth"},
            hard_bucket={
                "primary_failure_bucket": "truth_missing",
                "bucket_severity": "unknown",
                "bucket_stability_class": "unknown",
                "bucket_terminality_class": "unknown",
            },
            retention={
                "artifact_retention_status": "insufficient_truth",
                "artifact_retention_validity": "insufficient_truth",
                "retention_reference_consistent": True,
                "retention_manifest_compact": True,
            },
        )
        self.assertEqual(degraded["fleet_safety_status"], "degraded")
        self.assertEqual(degraded["fleet_safety_validity"], "partial")
        self.assertEqual(insufficient["fleet_safety_status"], "insufficient_truth")
        self.assertEqual(insufficient["fleet_safety_validity"], "insufficient_truth")

    def test_fleet_safety_control_alias_non_dup_and_compact_surfaces(self) -> None:
        payload = self._build_fleet_safety_payload(
            retention={
                "artifact_retention_status": "ready",
                "artifact_retention_validity": "valid",
                "retention_reference_consistent": True,
                "retention_manifest_compact": True,
                "retention_alias_deduplicated": True,
            },
            retention_manifest={"alias_deduplicated": True},
            hard_bucket={
                "primary_failure_bucket": "execution_failure",
                "bucket_severity": "low",
                "bucket_stability_class": "stable",
                "bucket_terminality_class": "non_terminal",
                "bucket_alias_deduplicated": True,
            },
        )
        self.assertIn("alias_deduplicated", payload["fleet_safety_reason_codes"])
        compact = build_fleet_safety_control_run_state_summary_surface(payload)
        self.assertEqual(
            set(compact.keys()),
            set(FLEET_SAFETY_CONTROL_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(compact["fleet_safety_control_present"])
        summary = build_fleet_safety_control_summary_surface(payload)
        self.assertEqual(
            set(summary.keys()),
            set(FLEET_SAFETY_CONTROL_SUMMARY_SAFE_FIELDS),
        )
        self.assertIn(summary["fleet_safety_status"], FLEET_SAFETY_STATUSES)
        self.assertIn(summary["fleet_safety_validity"], FLEET_SAFETY_VALIDITIES)
        self.assertIn(summary["fleet_safety_confidence"], FLEET_SAFETY_CONFIDENCE_LEVELS)
        self.assertIn(summary["fleet_safety_decision"], FLEET_SAFETY_DECISIONS)
        self.assertIn(summary["fleet_restart_decision"], FLEET_RESTART_DECISIONS)
        self.assertIn(summary["fleet_safety_scope"], FLEET_SAFETY_SCOPES)
        self.assertIn(summary["fleet_safety_primary_reason"], FLEET_SAFETY_REASON_CODES)

    def test_approval_email_delivery_is_deterministic_and_manual_only_mapped(self) -> None:
        payload_a = self._build_approval_email_payload(
            fleet_safety={
                "fleet_safety_status": "stop",
                "fleet_safety_decision": "escalate_manual",
                "fleet_restart_decision": "manual_only",
            },
            hard_bucket={
                "primary_failure_bucket": "manual_only",
                "bucket_severity": "high",
                "bucket_terminality_class": "manual_only",
            },
            endgame={"final_closure_class": "manual_closure_only"},
        )
        payload_b = self._build_approval_email_payload(
            fleet_safety={
                "fleet_safety_status": "stop",
                "fleet_safety_decision": "escalate_manual",
                "fleet_restart_decision": "manual_only",
            },
            hard_bucket={
                "primary_failure_bucket": "manual_only",
                "bucket_severity": "high",
                "bucket_terminality_class": "manual_only",
            },
            endgame={"final_closure_class": "manual_closure_only"},
        )
        self.assertEqual(payload_a, payload_b)
        self.assertEqual(payload_a["approval_email_status"], "delivery_blocked")
        self.assertTrue(payload_a["approval_required"])
        self.assertEqual(payload_a["approval_reason_class"], "manual_only")
        self.assertEqual(payload_a["proposed_next_direction"], "manual_review_preparation")
        self.assertEqual(payload_a["proposed_restart_mode"], "approval_required_then_manual")
        self.assertTrue(payload_a["delivery_outcome"] in {"blocked", "failed"})
        self.assertIn(payload_a["approval_email_status"], APPROVAL_EMAIL_STATUSES)
        self.assertIn(payload_a["approval_email_validity"], APPROVAL_EMAIL_VALIDITIES)
        self.assertIn(
            payload_a["approval_email_confidence"],
            APPROVAL_EMAIL_CONFIDENCE_LEVELS,
        )
        self.assertIn(payload_a["approval_priority"], APPROVAL_PRIORITIES)
        self.assertIn(payload_a["approval_reason_class"], APPROVAL_REASON_CLASSES)
        self.assertIn(payload_a["approval_decision_scope"], APPROVAL_DECISION_SCOPES)
        self.assertIn(payload_a["proposed_next_direction"], PROPOSED_NEXT_DIRECTIONS)
        self.assertIn(payload_a["proposed_restart_mode"], PROPOSED_RESTART_MODES)
        self.assertIn(payload_a["proposed_action_class"], PROPOSED_ACTION_CLASSES)
        self.assertIn(payload_a["recipient_class"], RECIPIENT_CLASSES)
        self.assertIn(payload_a["delivery_mode"], DELIVERY_MODES)
        self.assertIn(payload_a["delivery_outcome"], DELIVERY_OUTCOMES)
        self.assertIn(payload_a["approval_option_set"], APPROVAL_OPTION_SETS)
        self.assertIn(payload_a["approval_email_primary_reason"], APPROVAL_EMAIL_REASON_CODES)
        self.assertEqual(
            payload_a["approval_email_primary_reason"],
            payload_a["approval_email_reason_codes"][0],
        )

    def test_approval_email_delivery_required_delivered_and_blocked_distinctions(self) -> None:
        delivered = build_approval_email_delivery_contract_surface(
            run_id="job-approval-email",
            objective_contract_payload={"objective_id": "objective-approval-email"},
            fleet_safety_control_payload={
                "fleet_safety_status": "hold",
                "fleet_safety_decision": "hold_for_review",
                "fleet_restart_decision": "restart_hold",
            },
            failure_bucketing_hardening_payload={
                "primary_failure_bucket": "verification_failure",
                "bucket_severity": "high",
                "bucket_terminality_class": "terminal",
            },
            lane_stabilization_contract_payload={"lane_status": "lane_transition_blocked", "current_lane": "bounded_local_patch"},
            loop_hardening_contract_payload={"loop_hardening_status": "watch"},
            endgame_closure_contract_payload={"final_closure_class": "completed_but_not_closed"},
            retry_reentry_loop_contract_payload={"retry_loop_decision": "replan"},
            artifact_retention_contract_payload={
                "artifact_retention_status": "ready",
                "artifact_retention_validity": "valid",
                "retention_reference_consistent": True,
            },
            run_state_payload={"approval_email_delivery_mode": "gmail_send"},
            contract_artifact_index_payload={},
            delivery_adapter=lambda payload: {
                "delivery_attempted": True,
                "delivery_outcome": "sent",
                "status": "ok",
            },
        )
        required = self._build_approval_email_payload(
            run_state={"approval_email_delivery_mode": "review_queue_only"}
        )
        blocked = self._build_approval_email_payload(
            run_state={"approval_email_delivery_mode": "gmail_send"}
        )
        self.assertEqual(delivered["approval_email_status"], "delivered_for_review")
        self.assertEqual(delivered["delivery_outcome"], "sent")
        self.assertEqual(required["approval_email_status"], "required")
        self.assertEqual(required["delivery_outcome"], "skipped")
        self.assertEqual(blocked["approval_email_status"], "delivery_blocked")
        self.assertIn(blocked["delivery_outcome"], {"blocked", "failed"})

    def test_approval_email_delivery_direction_and_restart_consistency(self) -> None:
        replan_payload = self._build_approval_email_payload(
            hard_bucket={
                "primary_failure_bucket": "same_failure_exhausted",
                "bucket_severity": "critical",
                "bucket_terminality_class": "terminal",
            },
            retry_loop={"retry_loop_decision": "replan"},
            fleet_safety={
                "fleet_safety_status": "freeze",
                "fleet_safety_decision": "freeze_run",
                "fleet_restart_decision": "restart_blocked",
            },
        )
        closure_payload = self._build_approval_email_payload(
            fleet_safety={
                "fleet_safety_status": "hold",
                "fleet_safety_decision": "hold_for_review",
                "fleet_restart_decision": "restart_hold",
            },
            hard_bucket={
                "primary_failure_bucket": "external_truth_pending",
                "bucket_severity": "medium",
                "bucket_terminality_class": "external_wait",
            },
            endgame={"final_closure_class": "external_truth_pending"},
            retry_loop={"retry_loop_decision": "hold"},
        )
        self.assertEqual(replan_payload["proposed_next_direction"], "replan_preparation")
        self.assertEqual(replan_payload["proposed_action_class"], "review_and_replan")
        self.assertEqual(replan_payload["proposed_restart_mode"], "blocked")
        self.assertFalse(replan_payload["approval_can_clear_restart_block"])
        self.assertEqual(closure_payload["proposed_next_direction"], "closure_followup")
        self.assertEqual(closure_payload["proposed_action_class"], "review_and_close_followup")
        self.assertEqual(closure_payload["proposed_restart_mode"], "held")
        self.assertTrue(closure_payload["restart_held_pending_approval"])
        self.assertTrue(closure_payload["approval_can_clear_restart_block"])

    def test_approval_email_delivery_mode_selection_and_compact_surfaces(self) -> None:
        draft_payload = self._build_approval_email_payload(
            run_state={"approval_email_delivery_mode": "gmail_draft"}
        )
        send_payload = self._build_approval_email_payload(
            run_state={"approval_email_delivery_mode": "gmail_send"}
        )
        self.assertEqual(draft_payload["delivery_mode"], "gmail_draft")
        self.assertTrue(draft_payload["draft_required"])
        self.assertFalse(draft_payload["send_allowed"])
        self.assertEqual(send_payload["delivery_mode"], "gmail_send")
        self.assertTrue(send_payload["send_allowed"])
        self.assertFalse(send_payload["draft_required"])
        self.assertLessEqual(len(draft_payload["approval_body_compact"].splitlines()), 8)
        self.assertTrue(draft_payload["approval_subject"].startswith("[Approval Needed]"))
        compact = build_approval_email_delivery_run_state_summary_surface(draft_payload)
        self.assertEqual(
            set(compact.keys()),
            set(APPROVAL_EMAIL_DELIVERY_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(compact["approval_email_delivery_present"])
        summary = build_approval_email_delivery_summary_surface(draft_payload)
        self.assertEqual(
            set(summary.keys()),
            set(APPROVAL_EMAIL_DELIVERY_SUMMARY_SAFE_FIELDS),
        )
        self.assertIn(summary["approval_email_status"], APPROVAL_EMAIL_STATUSES)
        self.assertIn(summary["approval_email_validity"], APPROVAL_EMAIL_VALIDITIES)
        self.assertIn(summary["approval_email_confidence"], APPROVAL_EMAIL_CONFIDENCE_LEVELS)
        self.assertIn(summary["approval_priority"], APPROVAL_PRIORITIES)
        self.assertIn(summary["proposed_next_direction"], PROPOSED_NEXT_DIRECTIONS)
        self.assertIn(summary["delivery_mode"], DELIVERY_MODES)
        self.assertIn(summary["delivery_outcome"], DELIVERY_OUTCOMES)
        self.assertIn(summary["approval_email_primary_reason"], APPROVAL_EMAIL_REASON_CODES)

    def test_approval_direction_rules_are_deterministic(self) -> None:
        replan = derive_direction_posture(
            lead_reason="high_repeat_or_freeze_posture",
            primary_failure_bucket="same_failure_exhausted",
            final_closure_class="terminal_non_success",
            retry_loop_decision="replan",
            current_lane="bounded_local_patch",
            approval_required=True,
            manual_only_terminal=False,
            restart_blocked=True,
            restart_hold=False,
            bucket_severity="critical",
            fleet_safety_status="freeze",
        )
        replan_again = derive_direction_posture(
            lead_reason="high_repeat_or_freeze_posture",
            primary_failure_bucket="same_failure_exhausted",
            final_closure_class="terminal_non_success",
            retry_loop_decision="replan",
            current_lane="bounded_local_patch",
            approval_required=True,
            manual_only_terminal=False,
            restart_blocked=True,
            restart_hold=False,
            bucket_severity="critical",
            fleet_safety_status="freeze",
        )
        truth = derive_direction_posture(
            lead_reason="closure_decision_requires_review",
            primary_failure_bucket="truth_missing",
            final_closure_class="closure_unresolved",
            retry_loop_decision="recollect",
            current_lane="bounded_local_patch",
            approval_required=True,
            manual_only_terminal=False,
            restart_blocked=False,
            restart_hold=True,
            bucket_severity="medium",
            fleet_safety_status="hold",
        )
        self.assertEqual(replan, replan_again)
        self.assertEqual(replan["proposed_next_direction"], "replan_preparation")
        self.assertEqual(replan["proposed_target_lane"], "replan_preparation")
        self.assertEqual(replan["proposed_restart_mode"], "blocked")
        self.assertEqual(truth["proposed_next_direction"], "truth_gathering")
        self.assertEqual(truth["proposed_target_lane"], "truth_gathering")

    def test_approval_reply_command_normalization_and_mapping(self) -> None:
        self.assertEqual(normalize_reply_command("  ok   replan "), "OK REPLAN")
        self.assertTrue(is_supported_reply_command("ok truth"))
        self.assertFalse(is_supported_reply_command("ok start"))
        mapped_close = map_approved_reply_command("OK CLOSE")
        mapped_reject = map_approved_reply_command("reject")
        mapped_unknown = map_approved_reply_command("approve now")
        self.assertTrue(mapped_close["supported"])
        self.assertEqual(mapped_close["proposed_next_direction"], "closure_followup")
        self.assertEqual(mapped_close["proposed_action_class"], "review_and_close_followup")
        self.assertEqual(mapped_reject["proposed_next_direction"], "stop_no_restart")
        self.assertFalse(mapped_reject["restart_allowed"])
        self.assertFalse(mapped_unknown["supported"])
        self.assertEqual(mapped_unknown["proposed_restart_mode"], "unknown")

    def test_approval_email_templates_are_compact_and_stable(self) -> None:
        subject = render_approval_subject(
            priority="critical",
            run_id="job-" + ("x" * 80),
            primary_failure_bucket="same_failure_exhausted",
            proposed_next_direction="replan_preparation",
        )
        body = render_approval_body_compact(
            run_id="job-template",
            fleet_safety_status="freeze",
            primary_reason="high_repeat_or_freeze_posture",
            proposed_direction="replan_preparation",
            restart_mode="blocked",
            allowed_reply_commands=("OK REPLAN", "HOLD", "REJECT"),
            hints={"next_safe_hint": "collect minimal truth and replan"},
        )
        body_again = render_approval_body_compact(
            run_id="job-template",
            fleet_safety_status="freeze",
            primary_reason="high_repeat_or_freeze_posture",
            proposed_direction="replan_preparation",
            restart_mode="blocked",
            allowed_reply_commands=("OK REPLAN", "HOLD", "REJECT"),
            hints={"next_safe_hint": "collect minimal truth and replan"},
        )
        self.assertLessEqual(len(subject), 140)
        self.assertTrue(subject.startswith("[Approval Needed]"))
        self.assertLessEqual(len(body), 480)
        self.assertLessEqual(len(body.splitlines()), 7)
        self.assertEqual(body, body_again)
        self.assertIn("Reply: OK REPLAN | HOLD | REJECT", body)

    def test_approval_runtime_rules_contract_is_compact_and_deterministic(self) -> None:
        payload_a = build_approval_runtime_rules_contract_surface(
            run_id="job-runtime-rules",
            objective_contract_payload={"objective_id": "objective-runtime-rules"},
            approval_email_delivery_payload={
                "approval_email_status": "required",
                "proposed_next_direction": "replan_preparation",
                "retention_reference_consistent": True,
            },
            contract_artifact_index_payload={"approval_email_delivery_contract": {"path": "x.json"}},
        )
        payload_b = build_approval_runtime_rules_contract_surface(
            run_id="job-runtime-rules",
            objective_contract_payload={"objective_id": "objective-runtime-rules"},
            approval_email_delivery_payload={
                "approval_email_status": "required",
                "proposed_next_direction": "replan_preparation",
                "retention_reference_consistent": True,
            },
            contract_artifact_index_payload={"approval_email_delivery_contract": {"path": "x.json"}},
        )
        self.assertEqual(payload_a, payload_b)
        self.assertEqual(payload_a["allowed_reply_commands"], list(ALLOWED_REPLY_COMMANDS))
        self.assertEqual(
            len(payload_a["supporting_compact_truth_refs"]),
            len(set(payload_a["supporting_compact_truth_refs"])),
        )
        summary = build_approval_runtime_rules_summary_surface(payload_a)
        self.assertEqual(
            set(summary.keys()),
            set(APPROVAL_RUNTIME_RULES_SUMMARY_SAFE_FIELDS),
        )
        compact = build_approval_runtime_rules_run_state_summary_surface(payload_a)
        self.assertEqual(
            set(compact.keys()),
            set(APPROVAL_RUNTIME_RULES_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(compact["approval_runtime_rules_present"])

    def test_approval_delivery_handoff_mode_specific_outcomes_are_deterministic(self) -> None:
        def _adapter(payload: Mapping[str, Any]) -> Mapping[str, Any]:
            mode = str(payload.get("delivery_mode", "")).strip()
            if mode == "gmail_send":
                return {
                    "delivery_attempted": True,
                    "delivery_outcome": "sent",
                    "downstream_delivery_id": "d-send",
                    "downstream_thread_id": "t-send",
                    "downstream_message_id": "m-send",
                    "downstream_delivery_timestamp": "2026-04-22T00:00:00Z",
                }
            if mode == "gmail_draft":
                return {
                    "delivery_attempted": True,
                    "delivery_outcome": "draft_created",
                    "downstream_delivery_id": "d-draft",
                    "downstream_thread_id": "t-draft",
                    "downstream_message_id": "m-draft",
                    "downstream_delivery_timestamp": "2026-04-22T00:01:00Z",
                }
            return {
                "delivery_attempted": False,
                "delivery_outcome": "blocked",
            }

        common_email_payload = {
            "approval_email_status": "required",
            "approval_required": True,
            "approval_priority": "high",
            "proposed_next_direction": "replan_preparation",
            "proposed_target_lane": "replan_preparation",
            "proposed_restart_mode": "blocked",
            "recipient_target": "self:default",
            "approval_subject": "[Approval Needed][high] run job: retry_exhausted -> replan_preparation",
            "approval_body_compact": "Run: job\nSafety: freeze",
            "approval_option_set": "approve_replan_or_reject",
            "approval_summary_compact": "reason=retry_exhausted",
        }

        sent_a = build_approval_delivery_handoff_contract_surface(
            run_id="job-handoff",
            objective_contract_payload={"objective_id": "obj-handoff"},
            approval_email_delivery_payload={
                **common_email_payload,
                "delivery_mode": "gmail_send",
            },
            approval_runtime_rules_payload={"runtime_rules_version": "v1"},
            fleet_safety_control_payload={"fleet_safety_status": "freeze"},
            failure_bucketing_hardening_payload={
                "primary_failure_bucket": "retry_exhausted",
                "bucket_severity": "high",
            },
            lane_stabilization_contract_payload={"current_lane": "replan_preparation"},
            run_state_payload={"approval_runtime_rules_present": True},
            handoff_adapter=_adapter,
        )
        sent_b = build_approval_delivery_handoff_contract_surface(
            run_id="job-handoff",
            objective_contract_payload={"objective_id": "obj-handoff"},
            approval_email_delivery_payload={
                **common_email_payload,
                "delivery_mode": "gmail_send",
            },
            approval_runtime_rules_payload={"runtime_rules_version": "v1"},
            fleet_safety_control_payload={"fleet_safety_status": "freeze"},
            failure_bucketing_hardening_payload={
                "primary_failure_bucket": "retry_exhausted",
                "bucket_severity": "high",
            },
            lane_stabilization_contract_payload={"current_lane": "replan_preparation"},
            run_state_payload={"approval_runtime_rules_present": True},
            handoff_adapter=_adapter,
        )
        draft = build_approval_delivery_handoff_contract_surface(
            run_id="job-handoff",
            objective_contract_payload={"objective_id": "obj-handoff"},
            approval_email_delivery_payload={
                **common_email_payload,
                "delivery_mode": "gmail_draft",
            },
            approval_runtime_rules_payload={"runtime_rules_version": "v1"},
            fleet_safety_control_payload={"fleet_safety_status": "freeze"},
            failure_bucketing_hardening_payload={
                "primary_failure_bucket": "retry_exhausted",
                "bucket_severity": "high",
            },
            lane_stabilization_contract_payload={"current_lane": "replan_preparation"},
            run_state_payload={"approval_runtime_rules_present": True},
            handoff_adapter=_adapter,
        )
        queue = build_approval_delivery_handoff_contract_surface(
            run_id="job-handoff",
            objective_contract_payload={"objective_id": "obj-handoff"},
            approval_email_delivery_payload={
                **common_email_payload,
                "delivery_mode": "review_queue_only",
            },
            approval_runtime_rules_payload={"runtime_rules_version": "v1"},
            fleet_safety_control_payload={"fleet_safety_status": "freeze"},
            failure_bucketing_hardening_payload={
                "primary_failure_bucket": "retry_exhausted",
                "bucket_severity": "high",
            },
            lane_stabilization_contract_payload={"current_lane": "replan_preparation"},
            run_state_payload={"approval_runtime_rules_present": True},
            handoff_adapter=_adapter,
        )

        self.assertEqual(sent_a, sent_b)
        self.assertEqual(sent_a["approval_delivery_handoff_status"], "delivered_for_review")
        self.assertEqual(sent_a["delivery_outcome"], "sent")
        self.assertTrue(sent_a["delivery_attempted"])
        self.assertTrue(sent_a["delivery_succeeded"])
        self.assertEqual(sent_a["downstream_delivery_id"], "d-send")
        self.assertEqual(draft["delivery_outcome"], "draft_created")
        self.assertEqual(queue["delivery_outcome"], "queued_for_review")
        self.assertTrue(queue["approval_pending_human_response"])
        self.assertIn(
            queue["approval_delivery_handoff_primary_reason"],
            APPROVAL_DELIVERY_HANDOFF_REASON_CODES,
        )
        self.assertIn(
            queue["approval_delivery_handoff_status"],
            APPROVAL_DELIVERY_HANDOFF_STATUSES,
        )
        self.assertIn(
            queue["approval_delivery_handoff_validity"],
            APPROVAL_DELIVERY_HANDOFF_VALIDITIES,
        )
        self.assertIn(
            queue["approval_delivery_handoff_confidence"],
            APPROVAL_DELIVERY_HANDOFF_CONFIDENCE_LEVELS,
        )
        self.assertIn(queue["downstream_adapter"], DOWNSTREAM_ADAPTERS)

    def test_approval_delivery_handoff_blocked_failed_and_not_required(self) -> None:
        blocked = build_approval_delivery_handoff_contract_surface(
            run_id="job-handoff-blocked",
            objective_contract_payload={"objective_id": "obj-handoff"},
            approval_email_delivery_payload={
                "approval_email_status": "required",
                "approval_required": True,
                "delivery_mode": "gmail_send",
                "recipient_target": "self:default",
                "approval_subject": "subject",
                "approval_body_compact": "body",
                "approval_option_set": "approve_or_reject",
                "approval_summary_compact": "summary",
                "proposed_next_direction": "same_lane_retry",
                "proposed_target_lane": "bounded_local_patch",
                "proposed_restart_mode": "approval_required_then_restart",
            },
            approval_runtime_rules_payload={"runtime_rules_version": "v1"},
            fleet_safety_control_payload={},
            failure_bucketing_hardening_payload={},
            lane_stabilization_contract_payload={},
            run_state_payload={},
            handoff_adapter=lambda _: {"delivery_outcome": "blocked"},
        )

        def _failing_adapter(_: Mapping[str, Any]) -> Mapping[str, Any]:
            raise RuntimeError("adapter boom")

        failed = build_approval_delivery_handoff_contract_surface(
            run_id="job-handoff-failed",
            objective_contract_payload={"objective_id": "obj-handoff"},
            approval_email_delivery_payload={
                "approval_email_status": "required",
                "approval_required": True,
                "delivery_mode": "gmail_send",
                "recipient_target": "self:default",
                "approval_subject": "subject",
                "approval_body_compact": "body",
                "approval_option_set": "approve_or_reject",
                "approval_summary_compact": "summary",
                "proposed_next_direction": "same_lane_retry",
                "proposed_target_lane": "bounded_local_patch",
                "proposed_restart_mode": "approval_required_then_restart",
            },
            approval_runtime_rules_payload={"runtime_rules_version": "v1"},
            fleet_safety_control_payload={},
            failure_bucketing_hardening_payload={},
            lane_stabilization_contract_payload={},
            run_state_payload={},
            handoff_adapter=_failing_adapter,
        )
        not_required = build_approval_delivery_handoff_contract_surface(
            run_id="job-handoff-skip",
            objective_contract_payload={"objective_id": "obj-handoff"},
            approval_email_delivery_payload={
                "approval_email_status": "not_required",
                "approval_required": False,
                "delivery_mode": "not_applicable",
            },
            approval_runtime_rules_payload={"runtime_rules_version": "v1"},
            fleet_safety_control_payload={},
            failure_bucketing_hardening_payload={},
            lane_stabilization_contract_payload={},
            run_state_payload={},
            handoff_adapter=_failing_adapter,
        )
        self.assertEqual(blocked["approval_delivery_handoff_status"], "handoff_blocked")
        self.assertEqual(blocked["delivery_outcome"], "blocked")
        self.assertTrue(blocked["delivery_blocked"])
        self.assertFalse(blocked["delivery_attempted"])
        self.assertEqual(failed["approval_delivery_handoff_status"], "handoff_failed")
        self.assertEqual(failed["delivery_outcome"], "failed")
        self.assertTrue(failed["delivery_failed"])
        self.assertTrue(failed["delivery_attempted"])
        self.assertEqual(not_required["approval_delivery_handoff_status"], "not_required")
        self.assertEqual(not_required["delivery_outcome"], "skipped")
        self.assertFalse(not_required["delivery_attempted"])
        summary = build_approval_delivery_handoff_summary_surface(blocked)
        compact = build_approval_delivery_handoff_run_state_summary_surface(blocked)
        self.assertEqual(
            set(summary.keys()),
            set(APPROVAL_DELIVERY_HANDOFF_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(compact.keys()),
            set(APPROVAL_DELIVERY_HANDOFF_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(compact["approval_delivery_handoff_present"])

    def test_approval_response_ingest_normalization_and_supported_vs_unsupported(self) -> None:
        common_handoff = {
            "approval_delivery_handoff_status": "delivered_for_review",
            "delivery_mode": "gmail_send",
            "delivery_outcome": "sent",
            "approval_pending_human_response": True,
            "downstream_adapter": "internal_automation",
            "downstream_delivery_id": "d-1",
            "downstream_thread_id": "t-1",
            "downstream_message_id": "m-1",
        }
        approval_email = {
            "approval_required": True,
            "approval_priority": "high",
            "proposed_next_direction": "replan_preparation",
            "proposed_target_lane": "replan_preparation",
            "proposed_restart_mode": "approval_required_then_restart",
            "recipient_class": "operator",
        }
        supported = build_approval_response_contract_surface(
            run_id="job-response",
            objective_contract_payload={"objective_id": "obj-response"},
            approval_delivery_handoff_payload=common_handoff,
            approval_email_delivery_payload=approval_email,
            approval_runtime_rules_payload={"runtime_rules_version": "v1"},
            fleet_safety_control_payload={"fleet_restart_decision": "restart_hold"},
            run_state_payload={},
            response_payload={
                "response_received": True,
                "response_command_raw": "  ok   replan ",
                "response_actor_class": "operator",
                "response_message_id": "mail-1",
                "response_received_timestamp": "2026-04-22T12:00:00Z",
            },
        )
        unsupported = build_approval_response_contract_surface(
            run_id="job-response",
            objective_contract_payload={"objective_id": "obj-response"},
            approval_delivery_handoff_payload=common_handoff,
            approval_email_delivery_payload=approval_email,
            approval_runtime_rules_payload={"runtime_rules_version": "v1"},
            fleet_safety_control_payload={"fleet_restart_decision": "restart_hold"},
            run_state_payload={},
            response_payload={
                "response_received": True,
                "response_command_raw": "please retry quickly",
                "response_actor_class": "operator",
            },
        )
        held = build_approval_response_contract_surface(
            run_id="job-response",
            objective_contract_payload={"objective_id": "obj-response"},
            approval_delivery_handoff_payload=common_handoff,
            approval_email_delivery_payload=approval_email,
            approval_runtime_rules_payload={"runtime_rules_version": "v1"},
            fleet_safety_control_payload={"fleet_restart_decision": "restart_hold"},
            run_state_payload={},
            response_payload={
                "response_received": True,
                "response_command_raw": " hold ",
                "response_actor_class": "operator",
            },
        )
        rejected = build_approval_response_contract_surface(
            run_id="job-response",
            objective_contract_payload={"objective_id": "obj-response"},
            approval_delivery_handoff_payload=common_handoff,
            approval_email_delivery_payload=approval_email,
            approval_runtime_rules_payload={"runtime_rules_version": "v1"},
            fleet_safety_control_payload={"fleet_restart_decision": "restart_hold"},
            run_state_payload={},
            response_payload={
                "response_received": True,
                "response_command_raw": " reject ",
                "response_actor_class": "operator",
            },
        )

        self.assertEqual(supported["response_command_normalized"], "OK REPLAN")
        self.assertTrue(supported["response_supported"])
        self.assertEqual(supported["approval_response_status"], "response_accepted")
        self.assertEqual(supported["response_decision_class"], "approved")
        self.assertTrue(supported["response_allows_restart"])
        self.assertIn(supported["approval_response_status"], APPROVAL_RESPONSE_STATUSES)
        self.assertIn(supported["approval_response_validity"], APPROVAL_RESPONSE_VALIDITIES)
        self.assertIn(
            supported["approval_response_confidence"],
            APPROVAL_RESPONSE_CONFIDENCE_LEVELS,
        )
        self.assertIn(
            supported["approval_response_primary_reason"],
            APPROVAL_RESPONSE_REASON_CODES,
        )
        self.assertEqual(unsupported["approval_response_status"], "response_unsupported")
        self.assertFalse(unsupported["response_supported"])
        self.assertTrue(unsupported["response_blocks_restart"])
        self.assertEqual(held["approval_response_status"], "response_held")
        self.assertTrue(held["response_holds_restart"])
        self.assertEqual(rejected["approval_response_status"], "response_rejected")
        self.assertTrue(rejected["response_blocks_restart"])
        summary = build_approval_response_summary_surface(supported)
        compact = build_approval_response_run_state_summary_surface(supported)
        self.assertEqual(set(summary.keys()), set(APPROVAL_RESPONSE_SUMMARY_SAFE_FIELDS))
        self.assertEqual(
            set(compact.keys()),
            set(APPROVAL_RESPONSE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(compact["approval_response_present"])

    def test_approved_restart_decision_mapping_and_retry_compatibility(self) -> None:
        approval_email = {
            "approval_required": True,
            "proposed_next_direction": "replan_preparation",
            "proposed_target_lane": "replan_preparation",
            "proposed_restart_mode": "approval_required_then_restart",
        }
        handoff = {
            "approval_can_clear_restart_block": True,
            "restart_blocked_pending_approval": True,
            "restart_held_pending_approval": False,
        }
        base_response = {
            "approval_response_status": "response_accepted",
            "response_received": True,
            "response_decision_class": "approved",
            "approval_can_clear_restart_block": True,
        }
        fleet = {"fleet_restart_decision": "restart_blocked"}
        hardened_bucket = {
            "primary_failure_bucket": "retry_exhausted",
            "bucket_severity": "high",
        }
        lane = {"current_lane": "replan_preparation"}

        replan_response = dict(base_response, response_command_normalized="OK REPLAN")
        truth_response = dict(base_response, response_command_normalized="OK TRUTH")
        close_response = dict(base_response, response_command_normalized="OK CLOSE")
        retry_incompatible_response = dict(base_response, response_command_normalized="OK RETRY")
        hold_response = {
            "approval_response_status": "response_held",
            "response_received": True,
            "response_decision_class": "held",
            "response_command_normalized": "HOLD",
            "response_holds_restart": True,
        }
        reject_response = {
            "approval_response_status": "response_rejected",
            "response_received": True,
            "response_decision_class": "rejected",
            "response_command_normalized": "REJECT",
            "response_blocks_restart": True,
        }
        unsupported_response = {
            "approval_response_status": "response_unsupported",
            "response_received": True,
            "response_decision_class": "unsupported",
            "response_command_normalized": "PLEASE RETRY",
            "response_blocks_restart": True,
        }

        replan = build_approved_restart_contract_surface(
            run_id="job-restart",
            objective_contract_payload={"objective_id": "obj-restart"},
            approval_response_payload=replan_response,
            approval_delivery_handoff_payload=handoff,
            approval_email_delivery_payload=approval_email,
            fleet_safety_control_payload=fleet,
            failure_bucketing_hardening_payload=hardened_bucket,
            lane_stabilization_contract_payload=lane,
            run_state_payload={},
        )
        truth = build_approved_restart_contract_surface(
            run_id="job-restart",
            objective_contract_payload={"objective_id": "obj-restart"},
            approval_response_payload=truth_response,
            approval_delivery_handoff_payload=handoff,
            approval_email_delivery_payload=approval_email,
            fleet_safety_control_payload=fleet,
            failure_bucketing_hardening_payload=hardened_bucket,
            lane_stabilization_contract_payload=lane,
            run_state_payload={},
        )
        close = build_approved_restart_contract_surface(
            run_id="job-restart",
            objective_contract_payload={"objective_id": "obj-restart"},
            approval_response_payload=close_response,
            approval_delivery_handoff_payload=handoff,
            approval_email_delivery_payload=approval_email,
            fleet_safety_control_payload=fleet,
            failure_bucketing_hardening_payload=hardened_bucket,
            lane_stabilization_contract_payload=lane,
            run_state_payload={},
        )
        retry_incompatible = build_approved_restart_contract_surface(
            run_id="job-restart",
            objective_contract_payload={"objective_id": "obj-restart"},
            approval_response_payload=retry_incompatible_response,
            approval_delivery_handoff_payload=handoff,
            approval_email_delivery_payload=approval_email,
            fleet_safety_control_payload=fleet,
            failure_bucketing_hardening_payload=hardened_bucket,
            lane_stabilization_contract_payload=lane,
            run_state_payload={},
        )
        held = build_approved_restart_contract_surface(
            run_id="job-restart",
            objective_contract_payload={"objective_id": "obj-restart"},
            approval_response_payload=hold_response,
            approval_delivery_handoff_payload=handoff,
            approval_email_delivery_payload=approval_email,
            fleet_safety_control_payload=fleet,
            failure_bucketing_hardening_payload=hardened_bucket,
            lane_stabilization_contract_payload=lane,
            run_state_payload={},
        )
        rejected = build_approved_restart_contract_surface(
            run_id="job-restart",
            objective_contract_payload={"objective_id": "obj-restart"},
            approval_response_payload=reject_response,
            approval_delivery_handoff_payload=handoff,
            approval_email_delivery_payload=approval_email,
            fleet_safety_control_payload=fleet,
            failure_bucketing_hardening_payload=hardened_bucket,
            lane_stabilization_contract_payload=lane,
            run_state_payload={},
        )
        unsupported = build_approved_restart_contract_surface(
            run_id="job-restart",
            objective_contract_payload={"objective_id": "obj-restart"},
            approval_response_payload=unsupported_response,
            approval_delivery_handoff_payload=handoff,
            approval_email_delivery_payload=approval_email,
            fleet_safety_control_payload=fleet,
            failure_bucketing_hardening_payload=hardened_bucket,
            lane_stabilization_contract_payload=lane,
            run_state_payload={},
        )

        self.assertEqual(replan["approved_restart_status"], "restart_allowed")
        self.assertEqual(replan["restart_decision"], "allow_replan_preparation")
        self.assertEqual(truth["restart_decision"], "allow_truth_gathering")
        self.assertEqual(close["restart_decision"], "allow_closure_followup")
        self.assertEqual(retry_incompatible["approved_restart_status"], "restart_blocked")
        self.assertEqual(retry_incompatible["restart_decision"], "block_restart")
        self.assertEqual(held["approved_restart_status"], "restart_held")
        self.assertEqual(held["restart_decision"], "hold_restart")
        self.assertEqual(rejected["approved_restart_status"], "manual_followup_required")
        self.assertEqual(rejected["restart_decision"], "manual_followup_only")
        self.assertEqual(unsupported["approved_restart_status"], "restart_blocked")
        self.assertEqual(unsupported["restart_decision"], "block_restart")
        self.assertIn(replan["approved_restart_status"], APPROVED_RESTART_STATUSES)
        self.assertIn(replan["approved_restart_validity"], APPROVED_RESTART_VALIDITIES)
        self.assertIn(
            replan["approved_restart_confidence"],
            APPROVED_RESTART_CONFIDENCE_LEVELS,
        )
        self.assertIn(replan["restart_decision"], RESTART_DECISIONS)
        self.assertIn(
            replan["approved_restart_primary_reason"],
            APPROVED_RESTART_REASON_CODES,
        )
        summary = build_approved_restart_summary_surface(replan)
        compact = build_approved_restart_run_state_summary_surface(replan)
        self.assertEqual(set(summary.keys()), set(APPROVED_RESTART_SUMMARY_SAFE_FIELDS))
        self.assertEqual(
            set(compact.keys()),
            set(APPROVED_RESTART_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(compact["approved_restart_present"])

    def test_approval_safety_duplicate_cooldown_loop_and_not_applicable(self) -> None:
        objective = {"objective_id": "obj-safety"}
        approval_email_required = {
            "approval_email_status": "required",
            "approval_required": True,
            "approval_priority": "high",
            "proposed_next_direction": "replan_preparation",
            "proposed_target_lane": "replan_preparation",
            "proposed_restart_mode": "approval_required_then_restart",
            "recipient_target": "self:default",
            "recipient_class": "self",
        }
        lane = {"current_lane": "replan_preparation"}
        hard_bucket = {"primary_failure_bucket": "retry_exhausted", "bucket_severity": "high"}

        duplicate = build_approval_safety_contract_surface(
            run_id="job-safety",
            objective_contract_payload=objective,
            approval_email_delivery_payload=approval_email_required,
            approval_delivery_handoff_payload={
                "approval_delivery_handoff_status": "delivered_for_review",
                "delivery_outcome": "sent",
                "approval_pending_human_response": True,
            },
            approval_response_payload={"approval_response_status": "awaiting_response"},
            approved_restart_payload={"approved_restart_status": "not_ready"},
            lane_stabilization_contract_payload=lane,
            failure_bucketing_hardening_payload=hard_bucket,
            approval_runtime_rules_payload={},
            run_state_payload={},
        )
        cooldown = build_approval_safety_contract_surface(
            run_id="job-safety",
            objective_contract_payload=objective,
            approval_email_delivery_payload=approval_email_required,
            approval_delivery_handoff_payload={
                "approval_delivery_handoff_status": "handoff_attempted",
                "delivery_outcome": "sent",
                "approval_pending_human_response": False,
            },
            approval_response_payload={"approval_response_status": "awaiting_response"},
            approved_restart_payload={"approved_restart_status": "not_ready"},
            lane_stabilization_contract_payload=lane,
            failure_bucketing_hardening_payload=hard_bucket,
            approval_runtime_rules_payload={},
            run_state_payload={
                "approval_prior_recent_delivery_count": 1,
                "approval_cooldown_seconds": 120,
            },
        )
        loop = build_approval_safety_contract_surface(
            run_id="job-safety",
            objective_contract_payload=objective,
            approval_email_delivery_payload=approval_email_required,
            approval_delivery_handoff_payload={
                "approval_delivery_handoff_status": "handoff_attempted",
                "delivery_outcome": "blocked",
                "approval_pending_human_response": False,
            },
            approval_response_payload={"approval_response_status": "awaiting_response"},
            approved_restart_payload={"approved_restart_status": "not_ready"},
            lane_stabilization_contract_payload=lane,
            failure_bucketing_hardening_payload=hard_bucket,
            approval_runtime_rules_payload={},
            run_state_payload={
                "approval_same_request_class_count": 4,
                "approval_prior_recent_delivery_count": 1,
            },
        )
        not_required = build_approval_safety_contract_surface(
            run_id="job-safety",
            objective_contract_payload=objective,
            approval_email_delivery_payload={
                "approval_email_status": "not_required",
                "approval_required": False,
            },
            approval_delivery_handoff_payload={},
            approval_response_payload={},
            approved_restart_payload={},
            lane_stabilization_contract_payload=lane,
            failure_bucketing_hardening_payload=hard_bucket,
            approval_runtime_rules_payload={},
            run_state_payload={},
        )

        self.assertEqual(duplicate["approval_safety_status"], "duplicate_pending")
        self.assertEqual(duplicate["approval_safety_decision"], "block_until_response_or_clear")
        self.assertTrue(duplicate["approval_duplicate_detected"])
        self.assertTrue(duplicate["approval_pending_duplicate"])
        self.assertTrue(duplicate["approval_delivery_blocked_by_safety"])
        self.assertFalse(duplicate["approval_redelivery_allowed"])

        self.assertEqual(cooldown["approval_safety_status"], "cooldown_active")
        self.assertEqual(cooldown["approval_safety_decision"], "defer_until_cooldown_expires")
        self.assertTrue(cooldown["approval_cooldown_active"])
        self.assertTrue(cooldown["approval_delivery_deferred_by_safety"])
        self.assertFalse(cooldown["approval_redelivery_allowed"])

        self.assertEqual(loop["approval_safety_status"], "loop_suspected")
        self.assertEqual(loop["approval_safety_decision"], "block_loop_suspected")
        self.assertTrue(loop["approval_loop_suspected"])
        self.assertTrue(loop["approval_delivery_blocked_by_safety"])
        self.assertFalse(loop["approval_redelivery_allowed"])

        self.assertEqual(not_required["approval_safety_status"], "not_applicable")
        self.assertFalse(not_required["approval_redelivery_allowed"])
        self.assertFalse(not_required["approval_delivery_allowed_by_safety"])
        self.assertFalse(not_required["approval_delivery_blocked_by_safety"])

    def test_approval_safety_dedup_key_and_response_clearing_are_deterministic(self) -> None:
        objective = {"objective_id": "obj-safety-clear"}
        approval_email = {
            "approval_email_status": "required",
            "approval_required": True,
            "approval_priority": "medium",
            "proposed_next_direction": "truth_gathering",
            "proposed_target_lane": "truth_gathering",
            "proposed_restart_mode": "approval_required_then_restart",
            "recipient_target": "operator:default",
            "recipient_class": "operator",
        }
        lane = {"current_lane": "truth_gathering"}
        hard_bucket = {"primary_failure_bucket": "truth_missing", "bucket_severity": "medium"}

        first = build_approval_safety_contract_surface(
            run_id="job-safety-clear",
            objective_contract_payload=objective,
            approval_email_delivery_payload=approval_email,
            approval_delivery_handoff_payload={
                "approval_delivery_handoff_status": "delivered_for_review",
                "delivery_outcome": "sent",
                "approval_pending_human_response": True,
                "downstream_delivery_timestamp": "2026-04-22T00:00:00Z",
            },
            approval_response_payload={
                "approval_response_status": "response_accepted",
                "approval_response_validity": "valid",
                "response_received": True,
                "response_received_timestamp": "2026-04-22T00:05:00Z",
            },
            approved_restart_payload={"approved_restart_status": "restart_allowed"},
            lane_stabilization_contract_payload=lane,
            failure_bucketing_hardening_payload=hard_bucket,
            approval_runtime_rules_payload={},
            run_state_payload={},
        )
        second = build_approval_safety_contract_surface(
            run_id="job-safety-clear",
            objective_contract_payload=objective,
            approval_email_delivery_payload=approval_email,
            approval_delivery_handoff_payload={
                "approval_delivery_handoff_status": "delivered_for_review",
                "delivery_outcome": "sent",
                "approval_pending_human_response": True,
                "downstream_delivery_timestamp": "2026-04-22T00:00:00Z",
            },
            approval_response_payload={
                "approval_response_status": "response_accepted",
                "approval_response_validity": "valid",
                "response_received": True,
                "response_received_timestamp": "2026-04-22T00:05:00Z",
            },
            approved_restart_payload={"approved_restart_status": "restart_allowed"},
            lane_stabilization_contract_payload=lane,
            failure_bucketing_hardening_payload=hard_bucket,
            approval_runtime_rules_payload={},
            run_state_payload={},
        )
        cleared_duplicate = build_approval_safety_contract_surface(
            run_id="job-safety-clear",
            objective_contract_payload=objective,
            approval_email_delivery_payload=approval_email,
            approval_delivery_handoff_payload={
                "approval_delivery_handoff_status": "delivered_for_review",
                "delivery_outcome": "sent",
                "approval_pending_human_response": True,
                "downstream_delivery_timestamp": "2026-04-22T00:00:00Z",
            },
            approval_response_payload={
                "approval_response_status": "response_accepted",
                "approval_response_validity": "valid",
                "response_received": True,
                "response_received_timestamp": "2026-04-22T00:05:00Z",
            },
            approved_restart_payload={"approved_restart_status": "restart_allowed"},
            lane_stabilization_contract_payload=lane,
            failure_bucketing_hardening_payload=hard_bucket,
            approval_runtime_rules_payload={},
            run_state_payload={
                "approval_last_dedup_key": first["approval_dedup_key"],
                "approval_prior_pending_count": 2,
            },
        )

        self.assertEqual(first["approval_dedup_key"], second["approval_dedup_key"])
        self.assertEqual(cleared_duplicate["approval_safety_status"], "safe_to_deliver")
        self.assertEqual(cleared_duplicate["approval_safety_decision"], "allow_delivery")
        self.assertTrue(cleared_duplicate["approval_duplicate_detected"])
        self.assertFalse(cleared_duplicate["approval_pending_duplicate"])
        self.assertTrue(cleared_duplicate["approval_delivery_allowed_by_safety"])
        self.assertTrue(cleared_duplicate["approval_redelivery_allowed"])
        self.assertEqual(
            cleared_duplicate["approval_safety_primary_reason"],
            "delivery_safe_to_send",
        )
        self.assertIn(
            "response_cleared_pending_duplicate",
            cleared_duplicate["approval_safety_reason_codes"],
        )
        self.assertIn(cleared_duplicate["approval_safety_status"], APPROVAL_SAFETY_STATUSES)
        self.assertIn(cleared_duplicate["approval_safety_validity"], APPROVAL_SAFETY_VALIDITIES)
        self.assertIn(
            cleared_duplicate["approval_safety_confidence"],
            APPROVAL_SAFETY_CONFIDENCE_LEVELS,
        )
        self.assertIn(cleared_duplicate["approval_safety_decision"], APPROVAL_SAFETY_DECISIONS)
        self.assertIn(
            cleared_duplicate["approval_safety_primary_reason"],
            APPROVAL_SAFETY_REASON_CODES,
        )
        summary = build_approval_safety_summary_surface(cleared_duplicate)
        compact = build_approval_safety_run_state_summary_surface(cleared_duplicate)
        self.assertEqual(set(summary.keys()), set(APPROVAL_SAFETY_SUMMARY_SAFE_FIELDS))
        self.assertEqual(
            set(compact.keys()),
            set(APPROVAL_SAFETY_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertTrue(compact["approval_safety_present"])

    def test_runner_executes_one_automatic_restart_when_approved_and_safety_clear(self) -> None:
        response_payload = {
            "schema_version": "v1",
            "run_id": "job-approved-restart",
            "objective_id": "objective-approved-restart",
            "approval_response_status": "response_accepted",
            "approval_response_validity": "valid",
            "approval_response_confidence": "high",
            "response_received": True,
            "response_command_raw": "OK REPLAN",
            "response_command_normalized": "OK REPLAN",
            "response_supported": True,
            "response_from_expected_actor": True,
            "response_decision_class": "approved",
            "response_decision_scope": "restart_and_direction",
            "response_blocks_restart": False,
            "response_holds_restart": False,
            "response_allows_restart": True,
            "approval_response_primary_reason": "response_approved_accepted",
            "approval_response_reason_codes": ["response_approved_accepted"],
        }
        approved_restart_payload = {
            "schema_version": "v1",
            "run_id": "job-approved-restart",
            "objective_id": "objective-approved-restart",
            "approved_restart_status": "restart_allowed",
            "approved_restart_validity": "valid",
            "approved_restart_confidence": "high",
            "restart_decision": "allow_replan_preparation",
            "restart_allowed": True,
            "restart_blocked": False,
            "restart_held": False,
            "restart_requires_manual_followup": False,
            "approved_next_direction": "replan_preparation",
            "approved_target_lane": "replan_preparation",
            "approved_restart_mode": "approval_required_then_restart",
            "approved_action_class": "review_and_replan",
            "response_command_normalized": "OK REPLAN",
            "response_decision_class": "approved",
            "approved_restart_primary_reason": "restart_approved_and_allowed",
            "approved_restart_reason_codes": ["restart_approved_and_allowed"],
        }
        approval_safety_payload = {
            "schema_version": "v1",
            "run_id": "job-approved-restart",
            "objective_id": "objective-approved-restart",
            "approval_safety_status": "safe_to_deliver",
            "approval_safety_validity": "valid",
            "approval_safety_confidence": "high",
            "approval_safety_decision": "allow_delivery",
            "approval_duplicate_detected": False,
            "approval_pending_duplicate": False,
            "approval_cooldown_active": False,
            "approval_loop_suspected": False,
            "approval_delivery_blocked_by_safety": False,
            "approval_delivery_deferred_by_safety": False,
            "approval_delivery_allowed_by_safety": True,
            "approval_safety_primary_reason": "delivery_safe_to_send",
            "approval_safety_reason_codes": ["delivery_safe_to_send"],
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"
            status_map = {
                "project-planned-exec-pr-01__approved_restart_once": "completed",
            }
            transport = _RecordingDryRunTransport(status_by_pr_id=status_map)
            runner = PlannedExecutionRunner(
                adapter=CodexExecutorAdapter(transport=transport)
            )
            with (
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_response_contract_surface",
                    return_value=response_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approved_restart_contract_surface",
                    return_value=approved_restart_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_safety_contract_surface",
                    return_value=approval_safety_payload,
                ),
            ):
                manifest = runner.run(
                    artifacts_input_dir=artifacts_dir,
                    output_dir=out_dir,
                    dry_run=True,
                    stop_on_failure=True,
                )
            run_root = out_dir / manifest["job_id"]
            execution_payload = json.loads(
                (run_root / "approved_restart_execution_contract.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(
            execution_payload["automatic_restart_execution_status"], "executed"
        )
        self.assertTrue(execution_payload["automatic_restart_executed"])
        self.assertTrue(execution_payload["automatic_restart_attempted"])
        self.assertEqual(execution_payload["automatic_restart_count"], 1)
        self.assertTrue(
            execution_payload["automatic_restart_additional_execution_blocked"]
        )
        self.assertFalse(execution_payload["automatic_restart_chained"])
        self.assertEqual(execution_payload["automatic_restart_result_status"], "completed")
        self.assertTrue(
            execution_payload["automatic_restart_launch_pr_id"].endswith(
                "__approved_restart_once"
            )
        )
        self.assertEqual(
            execution_payload["automatic_restart_execution_reason"],
            "restart_executed_once",
        )
        self.assertEqual(len(transport.launch_order), 4)
        self.assertEqual(
            len([item for item in transport.launch_order if item.endswith("__approved_restart_once")]),
            1,
        )
        self.assertIn("approved_restart_execution_contract_summary", manifest)
        self.assertIn("approved_restart_execution_contract_path", manifest)
        self.assertTrue(
            str(manifest["approved_restart_execution_contract_path"]).endswith(
                "approved_restart_execution_contract.json"
            )
        )

    def test_runner_auto_restart_is_blocked_for_safety_statuses(self) -> None:
        response_payload = {
            "approval_response_status": "response_accepted",
            "approval_response_validity": "valid",
            "response_received": True,
            "response_command_normalized": "OK REPLAN",
            "response_decision_class": "approved",
            "response_allows_restart": True,
        }
        approved_restart_payload = {
            "approved_restart_status": "restart_allowed",
            "approved_restart_validity": "valid",
            "restart_decision": "allow_replan_preparation",
            "restart_allowed": True,
            "restart_blocked": False,
            "restart_held": False,
            "restart_requires_manual_followup": False,
            "approved_next_direction": "replan_preparation",
            "approved_target_lane": "replan_preparation",
            "approved_action_class": "review_and_replan",
            "response_decision_class": "approved",
            "response_command_normalized": "OK REPLAN",
        }
        blocked_cases = (
            (
                "duplicate_pending",
                {
                    "approval_safety_status": "duplicate_pending",
                    "approval_safety_decision": "block_until_response_or_clear",
                    "approval_pending_duplicate": True,
                    "approval_delivery_blocked_by_safety": True,
                },
                "safety_duplicate_pending",
            ),
            (
                "cooldown_active",
                {
                    "approval_safety_status": "cooldown_active",
                    "approval_safety_decision": "defer_until_cooldown_expires",
                    "approval_cooldown_active": True,
                    "approval_delivery_deferred_by_safety": True,
                },
                "safety_cooldown_active",
            ),
            (
                "loop_suspected",
                {
                    "approval_safety_status": "loop_suspected",
                    "approval_safety_decision": "block_loop_suspected",
                    "approval_loop_suspected": True,
                    "approval_delivery_blocked_by_safety": True,
                },
                "safety_loop_suspected",
            ),
            (
                "delivery_blocked",
                {
                    "approval_safety_status": "delivery_blocked",
                    "approval_safety_decision": "block_until_response_or_clear",
                    "approval_delivery_blocked_by_safety": True,
                },
                "safety_delivery_blocked",
            ),
            (
                "delivery_deferred",
                {
                    "approval_safety_status": "delivery_deferred",
                    "approval_safety_decision": "defer_until_cooldown_expires",
                    "approval_delivery_deferred_by_safety": True,
                },
                "safety_delivery_deferred",
            ),
        )
        for status, safety_patch, expected_reason in blocked_cases:
            with self.subTest(status=status):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    root = Path(tmp_dir)
                    artifacts_dir = self._write_planning_artifacts(root)
                    out_dir = root / "artifacts" / "executions"
                    transport = _RecordingDryRunTransport()
                    runner = PlannedExecutionRunner(
                        adapter=CodexExecutorAdapter(transport=transport)
                    )
                    merged_safety_payload = {
                        "approval_safety_status": status,
                        "approval_safety_validity": "valid",
                        "approval_safety_confidence": "high",
                        "approval_duplicate_detected": False,
                        "approval_pending_duplicate": False,
                        "approval_cooldown_active": False,
                        "approval_loop_suspected": False,
                        "approval_delivery_blocked_by_safety": False,
                        "approval_delivery_deferred_by_safety": False,
                        "approval_delivery_allowed_by_safety": False,
                        "approval_safety_primary_reason": "unknown_safety_posture",
                        "approval_safety_reason_codes": ["unknown_safety_posture"],
                    }
                    merged_safety_payload.update(safety_patch)
                    with (
                        patch(
                            "automation.orchestration.planned_execution_runner.build_approval_response_contract_surface",
                            return_value=response_payload,
                        ),
                        patch(
                            "automation.orchestration.planned_execution_runner.build_approved_restart_contract_surface",
                            return_value=approved_restart_payload,
                        ),
                        patch(
                            "automation.orchestration.planned_execution_runner.build_approval_safety_contract_surface",
                            return_value=merged_safety_payload,
                        ),
                    ):
                        manifest = runner.run(
                            artifacts_input_dir=artifacts_dir,
                            output_dir=out_dir,
                            dry_run=True,
                            stop_on_failure=True,
                        )
                    run_root = out_dir / manifest["job_id"]
                    execution_payload = json.loads(
                        (run_root / "approved_restart_execution_contract.json").read_text(
                            encoding="utf-8"
                        )
                    )

                self.assertEqual(
                    execution_payload["automatic_restart_execution_status"],
                    "not_executed",
                )
                self.assertFalse(execution_payload["automatic_restart_executed"])
                self.assertFalse(execution_payload["automatic_restart_attempted"])
                self.assertEqual(
                    execution_payload["automatic_restart_execution_reason"],
                    expected_reason,
                )
                self.assertEqual(len(transport.launch_order), 3)
                self.assertEqual(execution_payload["automatic_restart_count"], 0)

    def test_runner_auto_restart_not_executed_for_invalid_restart_posture(self) -> None:
        safety_payload = {
            "approval_safety_status": "safe_to_deliver",
            "approval_safety_validity": "valid",
            "approval_safety_confidence": "high",
            "approval_safety_decision": "allow_delivery",
            "approval_duplicate_detected": False,
            "approval_pending_duplicate": False,
            "approval_cooldown_active": False,
            "approval_loop_suspected": False,
            "approval_delivery_blocked_by_safety": False,
            "approval_delivery_deferred_by_safety": False,
            "approval_delivery_allowed_by_safety": True,
        }
        invalid_cases = (
            (
                "partial_validity",
                {
                    "approval_response_status": "response_accepted",
                    "response_decision_class": "approved",
                    "response_command_normalized": "OK REPLAN",
                },
                {
                    "approved_restart_status": "restart_allowed",
                    "approved_restart_validity": "partial",
                    "restart_decision": "allow_replan_preparation",
                    "restart_allowed": True,
                    "response_decision_class": "approved",
                    "response_command_normalized": "OK REPLAN",
                },
                "invalid_approved_restart_posture",
            ),
            (
                "hold_command",
                {
                    "approval_response_status": "response_held",
                    "response_decision_class": "held",
                    "response_command_normalized": "HOLD",
                },
                {
                    "approved_restart_status": "restart_held",
                    "approved_restart_validity": "valid",
                    "restart_decision": "hold_restart",
                    "restart_allowed": False,
                    "restart_held": True,
                    "response_decision_class": "held",
                    "response_command_normalized": "HOLD",
                },
                "invalid_approved_restart_posture",
            ),
            (
                "reject_manual_only",
                {
                    "approval_response_status": "response_rejected",
                    "response_decision_class": "rejected",
                    "response_command_normalized": "REJECT",
                },
                {
                    "approved_restart_status": "manual_followup_required",
                    "approved_restart_validity": "valid",
                    "restart_decision": "manual_followup_only",
                    "restart_allowed": False,
                    "restart_requires_manual_followup": True,
                    "response_decision_class": "rejected",
                    "response_command_normalized": "REJECT",
                },
                "invalid_approved_restart_posture",
            ),
        )

        for case_id, response_payload, approved_restart_payload, expected_reason in invalid_cases:
            with self.subTest(case=case_id):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    root = Path(tmp_dir)
                    artifacts_dir = self._write_planning_artifacts(root)
                    out_dir = root / "artifacts" / "executions"
                    transport = _RecordingDryRunTransport()
                    runner = PlannedExecutionRunner(
                        adapter=CodexExecutorAdapter(transport=transport)
                    )
                    with (
                        patch(
                            "automation.orchestration.planned_execution_runner.build_approval_response_contract_surface",
                            return_value=response_payload,
                        ),
                        patch(
                            "automation.orchestration.planned_execution_runner.build_approved_restart_contract_surface",
                            return_value=approved_restart_payload,
                        ),
                        patch(
                            "automation.orchestration.planned_execution_runner.build_approval_safety_contract_surface",
                            return_value=safety_payload,
                        ),
                    ):
                        manifest = runner.run(
                            artifacts_input_dir=artifacts_dir,
                            output_dir=out_dir,
                            dry_run=True,
                            stop_on_failure=True,
                        )
                    run_root = out_dir / manifest["job_id"]
                    execution_payload = json.loads(
                        (run_root / "approved_restart_execution_contract.json").read_text(
                            encoding="utf-8"
                        )
                    )

                self.assertEqual(
                    execution_payload["automatic_restart_execution_status"],
                    "not_executed",
                )
                self.assertEqual(
                    execution_payload["automatic_restart_execution_reason"],
                    expected_reason,
                )
                self.assertFalse(execution_payload["automatic_restart_executed"])
                self.assertFalse(execution_payload["automatic_restart_attempted"])
                self.assertEqual(execution_payload["automatic_restart_count"], 0)
                self.assertEqual(len(transport.launch_order), 3)

    def test_runner_allows_one_low_risk_approval_skip_and_executes_once(self) -> None:
        approval_email_payload = {
            "approval_email_status": "required",
            "approval_email_validity": "valid",
            "approval_required": True,
            "approval_priority": "low",
            "approval_reason_class": "restart_hold",
            "proposed_next_direction": "replan_preparation",
            "proposed_target_lane": "replan_preparation",
            "proposed_restart_mode": "approval_required_then_restart",
            "proposed_action_class": "review_and_replan",
        }
        response_payload = {
            "approval_response_status": "awaiting_response",
            "approval_response_validity": "valid",
            "response_received": False,
            "response_command_normalized": "",
            "response_supported": False,
            "response_decision_class": "unknown",
        }
        approved_restart_payload = {
            "approved_restart_status": "not_ready",
            "approved_restart_validity": "valid",
            "restart_decision": "unknown",
            "restart_allowed": False,
            "restart_blocked": True,
            "restart_held": False,
            "restart_requires_manual_followup": False,
            "approved_next_direction": "unknown",
            "approved_target_lane": "unknown",
            "approved_action_class": "unknown",
            "response_decision_class": "unknown",
            "response_command_normalized": "",
        }
        approval_safety_payload = {
            "approval_safety_status": "safe_to_deliver",
            "approval_safety_validity": "valid",
            "approval_safety_confidence": "high",
            "approval_safety_decision": "allow_delivery",
            "approval_pending_duplicate": False,
            "approval_cooldown_active": False,
            "approval_loop_suspected": False,
            "approval_delivery_blocked_by_safety": False,
            "approval_delivery_deferred_by_safety": False,
            "approval_delivery_allowed_by_safety": True,
        }
        fleet_safety_payload = {
            "fleet_safety_status": "allow",
            "fleet_safety_validity": "valid",
            "fleet_safety_decision": "proceed",
            "fleet_restart_decision": "restart_allowed",
            "fleet_manual_review_required": False,
            "bucket_severity": "low",
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"
            status_map = {
                "project-planned-exec-pr-01__approved_restart_once": "completed",
            }
            transport = _RecordingDryRunTransport(status_by_pr_id=status_map)
            runner = PlannedExecutionRunner(
                adapter=CodexExecutorAdapter(transport=transport)
            )
            with (
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_email_delivery_contract_surface",
                    return_value=approval_email_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_response_contract_surface",
                    return_value=response_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approved_restart_contract_surface",
                    return_value=approved_restart_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_safety_contract_surface",
                    return_value=approval_safety_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_fleet_safety_control_contract_surface",
                    return_value=fleet_safety_payload,
                ),
            ):
                manifest = runner.run(
                    artifacts_input_dir=artifacts_dir,
                    output_dir=out_dir,
                    dry_run=True,
                    stop_on_failure=True,
                )
            run_root = out_dir / manifest["job_id"]
            execution_payload = json.loads(
                (run_root / "approved_restart_execution_contract.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(
            execution_payload["automatic_restart_execution_status"], "executed"
        )
        self.assertTrue(execution_payload["automatic_restart_executed"])
        self.assertEqual(execution_payload["automatic_restart_count"], 1)
        self.assertTrue(execution_payload["approval_skip_allowed"])
        self.assertTrue(execution_payload["approval_skip_applied"])
        self.assertEqual(execution_payload["approval_skip_gate_status"], "skip_allowed")
        self.assertEqual(execution_payload["approval_skip_gate_decision"], "skip_and_continue_once")
        self.assertEqual(execution_payload["approval_skip_reason"], "skip_allowed_low_risk")
        self.assertFalse(execution_payload["approval_skip_human_gate_preserved"])
        self.assertEqual(
            execution_payload["approval_skip_effective_response_command"],
            "OK REPLAN",
        )
        self.assertEqual(
            execution_payload["approval_skip_effective_restart_decision"],
            "allow_replan_preparation",
        )
        self.assertEqual(execution_payload["response_command_normalized"], "OK REPLAN")
        self.assertEqual(
            execution_payload["restart_decision"], "allow_replan_preparation"
        )
        self.assertEqual(execution_payload["final_human_review_gate_status"], "not_required")
        self.assertFalse(execution_payload["final_human_review_required"])
        self.assertEqual(
            execution_payload["final_human_review_reason"],
            "final_review_not_required",
        )
        self.assertFalse(execution_payload["final_human_gate_preserved"])
        self.assertEqual(
            execution_payload["project_planning_summary_status"],
            "available",
        )
        self.assertTrue(execution_payload["project_planning_summary_available"])
        self.assertEqual(
            execution_payload["project_planning_summary_reason"],
            "planning_summary_compiled",
        )
        self.assertEqual(
            execution_payload["project_planning_control_posture"],
            "automation_executed",
        )
        self.assertEqual(
            execution_payload["project_autonomy_budget_status"],
            "available",
        )
        self.assertEqual(execution_payload["project_priority_posture"], "active")
        self.assertFalse(execution_payload["project_priority_deferred"])
        self.assertEqual(
            execution_payload["project_high_risk_defer_posture"],
            "clear",
        )
        self.assertEqual(execution_payload["project_run_budget_posture"], "available")
        self.assertEqual(
            execution_payload["project_objective_budget_posture"],
            "available",
        )
        self.assertEqual(
            execution_payload["project_pr_retry_budget_posture"],
            "not_applicable",
        )
        self.assertEqual(
            execution_payload["project_quality_gate_status"],
            "available",
        )
        self.assertEqual(
            execution_payload["project_quality_gate_posture"],
            "retry_needed",
        )
        self.assertFalse(execution_payload["project_quality_gate_merge_ready"])
        self.assertFalse(execution_payload["project_quality_gate_review_ready"])
        self.assertTrue(execution_payload["project_quality_gate_retry_needed"])
        self.assertEqual(
            execution_payload["project_quality_gate_changed_area_class"],
            "runner_and_tests",
        )
        self.assertEqual(
            execution_payload["project_quality_gate_risk_level"],
            "moderate",
        )
        self.assertIn(
            "targeted_regression",
            execution_payload["project_quality_gate_recommended"],
        )
        self.assertEqual(
            execution_payload["project_merge_branch_lifecycle_status"],
            "available",
        )
        self.assertEqual(
            execution_payload["project_merge_ready_posture"],
            "not_merge_ready",
        )
        self.assertFalse(execution_payload["project_merge_ready"])
        self.assertEqual(
            execution_payload["project_branch_cleanup_candidate_posture"],
            "not_candidate",
        )
        self.assertFalse(execution_payload["project_branch_cleanup_candidate"])
        self.assertEqual(
            execution_payload["project_branch_quarantine_candidate_posture"],
            "not_candidate",
        )
        self.assertFalse(execution_payload["project_branch_quarantine_candidate"])
        self.assertEqual(
            execution_payload["project_local_main_sync_posture"],
            "sync_not_required",
        )
        self.assertFalse(execution_payload["project_local_main_sync_required"])
        self.assertEqual(execution_payload["project_roadmap_status"], "available")
        self.assertTrue(execution_payload["project_roadmap_available"])
        self.assertEqual(
            execution_payload["project_roadmap_reason"],
            "roadmap_compiled",
        )
        self.assertEqual(execution_payload["project_roadmap_item_count"], 6)
        self.assertEqual(
            execution_payload["project_roadmap_items"][0]["roadmap_item_id"],
            "roadmap_continuation_budget",
        )
        self.assertEqual(execution_payload["project_pr_slicing_status"], "available")
        self.assertTrue(execution_payload["project_pr_slicing_available"])
        self.assertEqual(
            execution_payload["project_pr_slicing_reason"],
            "pr_slices_compiled",
        )
        self.assertEqual(execution_payload["project_pr_slice_count"], 6)
        self.assertEqual(
            execution_payload["project_pr_one_pr_size_decision"],
            "single_theme_single_pr",
        )
        self.assertEqual(
            execution_payload["project_pr_prioritization_mode"],
            "blocked_last_narrow_first_prereq_first",
        )
        self.assertEqual(
            execution_payload["project_pr_slices"][0]["roadmap_item_id"],
            "roadmap_continuation_budget",
        )
        self.assertEqual(
            execution_payload["implementation_prompt_status"],
            "available",
        )
        self.assertTrue(execution_payload["implementation_prompt_available"])
        self.assertEqual(
            execution_payload["implementation_prompt_reason"],
            "prompt_compiled",
        )
        self.assertEqual(
            execution_payload["implementation_prompt_slice_id"],
            "slice_01_continuation_budget",
        )
        self.assertEqual(
            execution_payload["implementation_prompt_roadmap_item_id"],
            "roadmap_continuation_budget",
        )
        self.assertEqual(
            execution_payload["implementation_prompt_payload"]["prompt_status"],
            "available",
        )
        self.assertEqual(
            execution_payload["implementation_prompt_payload"]["slice_id"],
            "slice_01_continuation_budget",
        )
        self.assertEqual(
            execution_payload["implementation_prompt_payload"]["roadmap_item_id"],
            "roadmap_continuation_budget",
        )
        self.assertIn(
            "automation/orchestration/planned_execution_runner.py",
            execution_payload["implementation_prompt_payload"]["preferred_files"],
        )
        self.assertIn(
            "/home/rai/codex-local-runner/prompts/base_codex_return_format.md",
            execution_payload["implementation_prompt_payload"]["preserved_constraints_ref"],
        )
        self.assertEqual(execution_payload["project_pr_queue_status"], "prepared")
        self.assertEqual(execution_payload["project_pr_queue_reason"], "queue_item_prepared")
        self.assertEqual(execution_payload["project_pr_queue_item_count"], 6)
        self.assertEqual(execution_payload["project_pr_queue_runnable_count"], 6)
        self.assertEqual(execution_payload["project_pr_queue_blocked_count"], 0)
        self.assertEqual(
            execution_payload["project_pr_queue_selected_slice_id"],
            "slice_01_continuation_budget",
        )
        self.assertEqual(
            execution_payload["project_pr_queue_selected_roadmap_item_id"],
            "roadmap_continuation_budget",
        )
        self.assertTrue(execution_payload["project_pr_queue_handoff_prepared"])
        self.assertEqual(
            execution_payload["project_pr_queue_handoff_payload"]["slice_id"],
            "slice_01_continuation_budget",
        )
        self.assertEqual(
            execution_payload["project_pr_queue_outcome"],
            "queue_item_prepared",
        )
        self.assertEqual(
            execution_payload["review_assimilation_status"],
            "assimilated",
        )
        self.assertEqual(
            execution_payload["review_assimilation_action"],
            "accept",
        )
        self.assertEqual(
            execution_payload["review_assimilation_reason"],
            "assimilation_accept_succeeded",
        )
        self.assertTrue(execution_payload["review_assimilation_available"])
        self.assertEqual(
            execution_payload["self_healing_status"],
            "not_applicable",
        )
        self.assertFalse(execution_payload["self_healing_transition_selected"])
        self.assertEqual(
            execution_payload["self_healing_transition_target"],
            "none",
        )
        self.assertFalse(execution_payload["self_healing_transition_executed"])
        self.assertEqual(
            execution_payload["self_healing_reason"],
            "self_healing_not_applicable_assimilation_accept",
        )
        self.assertTrue(execution_payload["self_healing_human_fallback_preserved"])
        self.assertEqual(execution_payload["self_healing_transition_count"], 0)
        self.assertEqual(
            execution_payload["long_running_stability_status"],
            "safe_stop",
        )
        self.assertEqual(
            execution_payload["long_running_reason"],
            "long_running_safe_stop_human_fallback",
        )
        self.assertTrue(execution_payload["long_running_pause_required"])
        self.assertFalse(execution_payload["long_running_resume_allowed"])
        self.assertTrue(execution_payload["long_running_safe_stop_required"])
        self.assertEqual(
            execution_payload["project_pr_queue_processed_slice_ids_before"],
            [],
        )
        self.assertEqual(
            execution_payload["project_pr_queue_processed_slice_ids_after"],
            ["slice_01_continuation_budget"],
        )
        self.assertEqual(len(transport.launch_order), 4)
        self.assertEqual(
            len([item for item in transport.launch_order if item.endswith("__approved_restart_once")]),
            1,
        )

    def test_runner_pr_queue_blocks_when_prompt_is_unavailable_for_selected_slice(self) -> None:
        approval_email_payload = {
            "approval_email_status": "required",
            "approval_email_validity": "valid",
            "approval_required": True,
            "approval_priority": "low",
            "approval_reason_class": "restart_hold",
            "proposed_next_direction": "replan_preparation",
            "proposed_target_lane": "replan_preparation",
            "proposed_restart_mode": "approval_required_then_restart",
            "proposed_action_class": "review_and_replan",
        }
        response_payload = {
            "approval_response_status": "awaiting_response",
            "approval_response_validity": "valid",
            "response_received": False,
            "response_command_normalized": "",
            "response_supported": False,
            "response_decision_class": "unknown",
        }
        approved_restart_payload = {
            "approved_restart_status": "not_ready",
            "approved_restart_validity": "valid",
            "restart_decision": "unknown",
            "restart_allowed": False,
            "restart_blocked": True,
            "restart_held": False,
            "restart_requires_manual_followup": False,
            "approved_next_direction": "unknown",
            "approved_target_lane": "unknown",
            "approved_action_class": "unknown",
            "response_decision_class": "unknown",
            "response_command_normalized": "",
        }
        approval_safety_payload = {
            "approval_safety_status": "safe_to_deliver",
            "approval_safety_validity": "valid",
            "approval_safety_confidence": "high",
            "approval_safety_decision": "allow_delivery",
            "approval_pending_duplicate": False,
            "approval_cooldown_active": False,
            "approval_loop_suspected": False,
            "approval_delivery_blocked_by_safety": False,
            "approval_delivery_deferred_by_safety": False,
            "approval_delivery_allowed_by_safety": True,
        }
        fleet_safety_payload = {
            "fleet_safety_status": "allow",
            "fleet_safety_validity": "valid",
            "fleet_safety_decision": "proceed",
            "fleet_restart_decision": "restart_allowed",
            "fleet_manual_review_required": False,
            "bucket_severity": "low",
        }

        payloads: list[dict[str, object]] = []
        launch_counts: list[int] = []
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"
            status_map = {
                "project-planned-exec-pr-01__approved_restart_once": "completed",
            }
            for _ in range(2):
                transport = _RecordingDryRunTransport(status_by_pr_id=status_map)
                runner = PlannedExecutionRunner(
                    adapter=CodexExecutorAdapter(transport=transport)
                )
                with (
                    patch(
                        "automation.orchestration.planned_execution_runner.build_approval_email_delivery_contract_surface",
                        return_value=approval_email_payload,
                    ),
                    patch(
                        "automation.orchestration.planned_execution_runner.build_approval_response_contract_surface",
                        return_value=response_payload,
                    ),
                    patch(
                        "automation.orchestration.planned_execution_runner.build_approved_restart_contract_surface",
                        return_value=approved_restart_payload,
                    ),
                    patch(
                        "automation.orchestration.planned_execution_runner.build_approval_safety_contract_surface",
                        return_value=approval_safety_payload,
                    ),
                    patch(
                        "automation.orchestration.planned_execution_runner.build_fleet_safety_control_contract_surface",
                        return_value=fleet_safety_payload,
                    ),
                ):
                    manifest = runner.run(
                        artifacts_input_dir=artifacts_dir,
                        output_dir=out_dir,
                        dry_run=True,
                        stop_on_failure=True,
                    )
                run_root = out_dir / manifest["job_id"]
                payloads.append(
                    json.loads(
                        (run_root / "approved_restart_execution_contract.json").read_text(
                            encoding="utf-8"
                        )
                    )
                )
                launch_counts.append(len(transport.launch_order))

        first, second = payloads
        self.assertEqual(first["project_pr_queue_status"], "prepared")
        self.assertEqual(second["project_pr_queue_status"], "blocked")
        self.assertEqual(
            second["project_pr_queue_reason"],
            "prompt_unavailable_for_selected_slice",
        )
        self.assertEqual(
            second["project_pr_queue_selected_slice_id"],
            "slice_02_branch_ceiling",
        )
        self.assertEqual(
            second["implementation_prompt_slice_id"],
            "slice_01_continuation_budget",
        )
        self.assertFalse(second["project_pr_queue_handoff_prepared"])
        self.assertEqual(second["project_pr_queue_handoff_payload"], {})
        self.assertEqual(
            second["project_pr_queue_processed_slice_ids_before"],
            ["slice_01_continuation_budget"],
        )
        self.assertEqual(
            second["project_pr_queue_processed_slice_ids_after"],
            ["slice_01_continuation_budget"],
        )
        self.assertEqual(
            second["project_pr_queue_outcome"],
            "prompt_unavailable_for_selected_slice",
        )
        self.assertEqual(second["review_assimilation_status"], "no_action")
        self.assertEqual(second["review_assimilation_action"], "none")
        self.assertEqual(
            second["review_assimilation_reason"],
            "assimilation_prompt_unavailable",
        )
        self.assertFalse(second["review_assimilation_available"])
        self.assertEqual(second["self_healing_status"], "not_applicable")
        self.assertEqual(
            second["self_healing_reason"],
            "self_healing_not_applicable_assimilation_no_action",
        )
        self.assertFalse(second["self_healing_transition_selected"])
        self.assertFalse(second["self_healing_transition_executed"])
        self.assertTrue(second["self_healing_human_fallback_preserved"])
        self.assertEqual(second["long_running_stability_status"], "safe_stop")
        self.assertEqual(
            second["long_running_reason"],
            "long_running_safe_stop_queue_blocked",
        )
        self.assertTrue(second["long_running_pause_required"])
        self.assertEqual(launch_counts, [4, 4])

    def test_runner_pr_queue_reports_empty_when_all_slices_are_already_processed(self) -> None:
        approval_email_payload = {
            "approval_email_status": "required",
            "approval_email_validity": "valid",
            "approval_required": True,
            "approval_priority": "low",
            "approval_reason_class": "restart_hold",
            "proposed_next_direction": "replan_preparation",
            "proposed_target_lane": "replan_preparation",
            "proposed_restart_mode": "approval_required_then_restart",
            "proposed_action_class": "review_and_replan",
        }
        response_payload = {
            "approval_response_status": "awaiting_response",
            "approval_response_validity": "valid",
            "response_received": False,
            "response_command_normalized": "",
            "response_supported": False,
            "response_decision_class": "unknown",
        }
        approved_restart_payload = {
            "approved_restart_status": "not_ready",
            "approved_restart_validity": "valid",
            "restart_decision": "unknown",
            "restart_allowed": False,
            "restart_blocked": True,
            "restart_held": False,
            "restart_requires_manual_followup": False,
            "approved_next_direction": "unknown",
            "approved_target_lane": "unknown",
            "approved_action_class": "unknown",
            "response_decision_class": "unknown",
            "response_command_normalized": "",
        }
        approval_safety_payload = {
            "approval_safety_status": "safe_to_deliver",
            "approval_safety_validity": "valid",
            "approval_safety_confidence": "high",
            "approval_safety_decision": "allow_delivery",
            "approval_pending_duplicate": False,
            "approval_cooldown_active": False,
            "approval_loop_suspected": False,
            "approval_delivery_blocked_by_safety": False,
            "approval_delivery_deferred_by_safety": False,
            "approval_delivery_allowed_by_safety": True,
        }
        fleet_safety_payload = {
            "fleet_safety_status": "allow",
            "fleet_safety_validity": "valid",
            "fleet_safety_decision": "proceed",
            "fleet_restart_decision": "restart_allowed",
            "fleet_manual_review_required": False,
            "bucket_severity": "low",
        }
        all_processed_slice_ids = [
            "slice_01_continuation_budget",
            "slice_02_branch_ceiling",
            "slice_03_failure_bucket_gate",
            "slice_04_next_step_selection",
            "slice_05_supported_repair_posture",
            "slice_06_human_review_gate",
        ]

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"
            status_map = {
                "project-planned-exec-pr-01__approved_restart_once": "completed",
            }

            transport_first = _RecordingDryRunTransport(status_by_pr_id=status_map)
            runner_first = PlannedExecutionRunner(
                adapter=CodexExecutorAdapter(transport=transport_first)
            )
            with (
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_email_delivery_contract_surface",
                    return_value=approval_email_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_response_contract_surface",
                    return_value=response_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approved_restart_contract_surface",
                    return_value=approved_restart_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_safety_contract_surface",
                    return_value=approval_safety_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_fleet_safety_control_contract_surface",
                    return_value=fleet_safety_payload,
                ),
            ):
                first_manifest = runner_first.run(
                    artifacts_input_dir=artifacts_dir,
                    output_dir=out_dir,
                    dry_run=True,
                    stop_on_failure=True,
                )

            run_root = out_dir / first_manifest["job_id"]
            prior_payload = json.loads(
                (run_root / "approved_restart_execution_contract.json").read_text(
                    encoding="utf-8"
                )
            )
            prior_payload["project_pr_queue_processed_slice_ids"] = all_processed_slice_ids
            (run_root / "approved_restart_execution_contract.json").write_text(
                json.dumps(prior_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            transport_second = _RecordingDryRunTransport(status_by_pr_id=status_map)
            runner_second = PlannedExecutionRunner(
                adapter=CodexExecutorAdapter(transport=transport_second)
            )
            with (
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_email_delivery_contract_surface",
                    return_value=approval_email_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_response_contract_surface",
                    return_value=response_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approved_restart_contract_surface",
                    return_value=approved_restart_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_safety_contract_surface",
                    return_value=approval_safety_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_fleet_safety_control_contract_surface",
                    return_value=fleet_safety_payload,
                ),
            ):
                second_manifest = runner_second.run(
                    artifacts_input_dir=artifacts_dir,
                    output_dir=out_dir,
                    dry_run=True,
                    stop_on_failure=True,
                )

            second_payload = json.loads(
                (out_dir / second_manifest["job_id"] / "approved_restart_execution_contract.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(second_payload["project_pr_queue_status"], "empty")
        self.assertEqual(second_payload["project_pr_queue_reason"], "queue_empty")
        self.assertEqual(second_payload["project_pr_queue_runnable_count"], 0)
        self.assertEqual(second_payload["project_pr_queue_item_count"], 6)
        self.assertFalse(second_payload["project_pr_queue_handoff_prepared"])
        self.assertEqual(second_payload["project_pr_queue_handoff_payload"], {})
        self.assertEqual(
            second_payload["project_pr_queue_processed_slice_ids_before"],
            all_processed_slice_ids,
        )
        self.assertEqual(
            second_payload["project_pr_queue_processed_slice_ids_after"],
            all_processed_slice_ids,
        )
        self.assertEqual(second_payload["project_pr_queue_outcome"], "queue_empty")
        self.assertEqual(second_payload["review_assimilation_status"], "no_action")
        self.assertEqual(second_payload["review_assimilation_action"], "none")
        self.assertEqual(
            second_payload["review_assimilation_reason"],
            "assimilation_queue_empty",
        )
        self.assertFalse(second_payload["review_assimilation_available"])
        self.assertEqual(second_payload["self_healing_status"], "not_applicable")
        self.assertEqual(
            second_payload["self_healing_reason"],
            "self_healing_not_applicable_assimilation_no_action",
        )
        self.assertFalse(second_payload["self_healing_transition_selected"])
        self.assertFalse(second_payload["self_healing_transition_executed"])
        self.assertTrue(second_payload["self_healing_human_fallback_preserved"])
        self.assertEqual(second_payload["long_running_stability_status"], "safe_stop")
        self.assertEqual(
            second_payload["long_running_reason"],
            "long_running_safe_stop_queue_empty",
        )
        self.assertTrue(second_payload["long_running_pause_required"])

    def test_review_assimilation_maps_failed_results_to_bounded_next_actions(self) -> None:
        cases = (
            (
                "retry",
                {
                    "restart_result_status": "failed",
                    "continuation_next_step_target": "retry",
                    "continuation_next_step_reason": "next_step_selected_retry",
                    "continuation_next_step_truth_insufficiency_explicit": False,
                    "final_human_review_required": False,
                    "final_human_review_reason": "final_review_not_required",
                },
                ("assimilated", "retry", "assimilation_retry_retryable_failure"),
            ),
            (
                "replan",
                {
                    "restart_result_status": "failed",
                    "continuation_next_step_target": "replan",
                    "continuation_next_step_reason": "next_step_selected_replan",
                    "continuation_next_step_truth_insufficiency_explicit": False,
                    "final_human_review_required": False,
                    "final_human_review_reason": "final_review_not_required",
                },
                ("assimilated", "replan", "assimilation_replan_design_invalid"),
            ),
            (
                "split",
                {
                    "restart_result_status": "failed",
                    "continuation_next_step_target": "truth_gather",
                    "continuation_next_step_reason": "next_step_selected_truth_gather",
                    "continuation_next_step_truth_insufficiency_explicit": True,
                    "final_human_review_required": False,
                    "final_human_review_reason": "final_review_not_required",
                },
                ("assimilated", "split", "assimilation_split_scope_signal"),
            ),
            (
                "escalate",
                {
                    "restart_result_status": "failed",
                    "continuation_next_step_target": "none",
                    "continuation_next_step_reason": "next_step_not_selected",
                    "continuation_next_step_truth_insufficiency_explicit": False,
                    "final_human_review_required": True,
                    "final_human_review_reason": "final_review_supported_repair_verification_failed",
                },
                ("assimilated", "escalate", "assimilation_escalate_manual_followup"),
            ),
        )

        for case_id, case_input, expected in cases:
            with self.subTest(case=case_id):
                payload = _build_review_assimilation_state(
                    queue_status="prepared",
                    queue_reason="queue_item_prepared",
                    queue_handoff_prepared=True,
                    queue_handoff_payload={
                        "slice_id": "slice_01_continuation_budget",
                        "roadmap_item_id": "roadmap_continuation_budget",
                    },
                    restart_result_status=str(case_input["restart_result_status"]),
                    continuation_next_step_target=str(
                        case_input["continuation_next_step_target"]
                    ),
                    continuation_next_step_reason=str(
                        case_input["continuation_next_step_reason"]
                    ),
                    continuation_next_step_truth_insufficiency_explicit=bool(
                        case_input["continuation_next_step_truth_insufficiency_explicit"]
                    ),
                    final_human_review_required=bool(
                        case_input["final_human_review_required"]
                    ),
                    final_human_review_reason=str(case_input["final_human_review_reason"]),
                )
                self.assertEqual(payload["review_assimilation_status"], expected[0])
                self.assertEqual(payload["review_assimilation_action"], expected[1])
                self.assertEqual(payload["review_assimilation_reason"], expected[2])
                self.assertTrue(payload["review_assimilation_available"])

    def test_bounded_self_healing_selects_single_transition_from_assimilation(self) -> None:
        cases = (
            ("retry", "retry", "self_healing_executed_retry"),
            ("replan", "replan", "self_healing_executed_replan"),
            ("split", "truth_gather", "self_healing_executed_truth_gather"),
            (
                "escalate",
                "alternative_supported_repair",
                "self_healing_executed_alternative_supported_repair",
            ),
        )
        for action, expected_target, expected_reason in cases:
            with self.subTest(action=action):
                payload = _build_bounded_self_healing_state(
                    review_assimilation_status="assimilated",
                    review_assimilation_action=action,
                    review_assimilation_available=True,
                    review_assimilation_reviewable=True,
                    review_assimilation_queue_status="prepared",
                    continuation_next_step_truth_insufficiency_explicit=(action == "split"),
                    supported_repair_execution_status="executed_verification_failed",
                    continuation_repair_playbook_selected=True,
                    continuation_repair_playbook_class="replan_plan",
                    continuation_repair_playbook_candidate_action="request_replan",
                    final_human_review_required=(action == "escalate"),
                    final_human_review_reason=(
                        "final_review_supported_repair_verification_failed"
                        if action == "escalate"
                        else "final_review_not_required"
                    ),
                    continuation_budget_status="available",
                    continuation_branch_budget_status="available",
                    continuation_no_progress_stop_required=False,
                    continuation_failure_bucket_denied=False,
                    safety_duplicate_pending=False,
                    safety_cooldown_active=False,
                    safety_loop_suspected=False,
                    safety_delivery_blocked=False,
                    safety_delivery_deferred=False,
                    prior_self_healing_transition_count=0,
                    self_healing_chain_limit=1,
                    prior_continuation_retry_count=0,
                    prior_continuation_replan_count=0,
                    prior_continuation_truth_gather_count=0,
                    continuation_retry_limit=2,
                    continuation_replan_limit=2,
                    continuation_truth_gather_limit=2,
                )
                self.assertEqual(payload["self_healing_status"], "executed")
                self.assertEqual(payload["self_healing_transition_target"], expected_target)
                self.assertTrue(payload["self_healing_transition_selected"])
                self.assertTrue(payload["self_healing_transition_executed"])
                self.assertEqual(payload["self_healing_reason"], expected_reason)
                self.assertEqual(payload["self_healing_transition_count_before"], 0)
                self.assertEqual(payload["self_healing_transition_count_after"], 1)
                self.assertEqual(payload["self_healing_chain_budget_remaining_after"], 0)
                self.assertFalse(payload["self_healing_human_fallback_preserved"])

    def test_bounded_self_healing_blocks_on_budget_and_non_action_assimilation(self) -> None:
        budget_exhausted = _build_bounded_self_healing_state(
            review_assimilation_status="assimilated",
            review_assimilation_action="retry",
            review_assimilation_available=True,
            review_assimilation_reviewable=True,
            review_assimilation_queue_status="prepared",
            continuation_next_step_truth_insufficiency_explicit=False,
            supported_repair_execution_status="executed_verification_failed",
            continuation_repair_playbook_selected=True,
            continuation_repair_playbook_class="replan_plan",
            continuation_repair_playbook_candidate_action="request_replan",
            final_human_review_required=False,
            final_human_review_reason="final_review_not_required",
            continuation_budget_status="available",
            continuation_branch_budget_status="available",
            continuation_no_progress_stop_required=False,
            continuation_failure_bucket_denied=False,
            safety_duplicate_pending=False,
            safety_cooldown_active=False,
            safety_loop_suspected=False,
            safety_delivery_blocked=False,
            safety_delivery_deferred=False,
            prior_self_healing_transition_count=1,
            self_healing_chain_limit=1,
            prior_continuation_retry_count=0,
            prior_continuation_replan_count=0,
            prior_continuation_truth_gather_count=0,
            continuation_retry_limit=2,
            continuation_replan_limit=2,
            continuation_truth_gather_limit=2,
        )
        self.assertEqual(budget_exhausted["self_healing_status"], "blocked")
        self.assertEqual(
            budget_exhausted["self_healing_reason"],
            "self_healing_blocked_budget_exhausted",
        )
        self.assertFalse(budget_exhausted["self_healing_transition_executed"])
        self.assertTrue(budget_exhausted["self_healing_human_fallback_preserved"])

        no_action = _build_bounded_self_healing_state(
            review_assimilation_status="no_action",
            review_assimilation_action="none",
            review_assimilation_available=False,
            review_assimilation_reviewable=False,
            review_assimilation_queue_status="empty",
            continuation_next_step_truth_insufficiency_explicit=False,
            supported_repair_execution_status="not_selected",
            continuation_repair_playbook_selected=False,
            continuation_repair_playbook_class="no_plan",
            continuation_repair_playbook_candidate_action="no_action",
            final_human_review_required=False,
            final_human_review_reason="final_review_not_required",
            continuation_budget_status="available",
            continuation_branch_budget_status="not_applicable",
            continuation_no_progress_stop_required=False,
            continuation_failure_bucket_denied=False,
            safety_duplicate_pending=False,
            safety_cooldown_active=False,
            safety_loop_suspected=False,
            safety_delivery_blocked=False,
            safety_delivery_deferred=False,
            prior_self_healing_transition_count=0,
            self_healing_chain_limit=1,
            prior_continuation_retry_count=0,
            prior_continuation_replan_count=0,
            prior_continuation_truth_gather_count=0,
            continuation_retry_limit=2,
            continuation_replan_limit=2,
            continuation_truth_gather_limit=2,
        )
        self.assertEqual(no_action["self_healing_status"], "not_applicable")
        self.assertEqual(
            no_action["self_healing_reason"],
            "self_healing_not_applicable_assimilation_no_action",
        )
        self.assertEqual(no_action["self_healing_transition_target"], "none")
        self.assertFalse(no_action["self_healing_transition_executed"])
        self.assertTrue(no_action["self_healing_human_fallback_preserved"])

    def test_long_running_stability_detects_stale_and_stuck(self) -> None:
        now_fn = lambda: datetime.fromisoformat("2026-04-23T12:30:00+00:00")
        stale_payload = _build_long_running_stability_state(
            objective_id="obj-1",
            queue_status="prepared",
            queue_selected_slice_id="slice_01",
            queue_handoff_prepared=True,
            queue_processed_count=1,
            review_assimilation_status="assimilated",
            review_assimilation_action="retry",
            review_assimilation_available=True,
            self_healing_status="selected",
            self_healing_transition_target="retry",
            self_healing_transition_executed=False,
            self_healing_human_fallback_preserved=False,
            self_healing_chain_budget_remaining_after=1,
            self_healing_transition_count_after=0,
            final_human_review_required=False,
            automatic_restart_executed=False,
            automatic_continuation_run_count=1,
            prior_long_running_replay_key="obj-1|slice_01|assimilated|retry|selected|retry",
            prior_long_running_progress_signature="1|1|0|restart_not_executed|self_healing_not_executed",
            prior_long_running_stale_cycle_count=0,
            prior_long_running_stuck_cycle_count=0,
            prior_long_running_watchdog_heartbeat_at="2026-04-23T12:00:00+00:00",
            now=now_fn,
        )
        self.assertEqual(stale_payload["long_running_stability_status"], "paused")
        self.assertEqual(
            stale_payload["long_running_reason"],
            "long_running_paused_stale_watchdog",
        )
        self.assertTrue(stale_payload["long_running_stale_detected"])
        self.assertFalse(stale_payload["long_running_stuck_detected"])
        self.assertTrue(stale_payload["long_running_pause_required"])
        self.assertTrue(stale_payload["long_running_resume_allowed"])
        self.assertTrue(stale_payload["long_running_replay_safe"])
        self.assertEqual(stale_payload["long_running_stuck_cycle_count"], 1)

        stuck_payload = _build_long_running_stability_state(
            objective_id="obj-1",
            queue_status="prepared",
            queue_selected_slice_id="slice_01",
            queue_handoff_prepared=True,
            queue_processed_count=1,
            review_assimilation_status="assimilated",
            review_assimilation_action="retry",
            review_assimilation_available=True,
            self_healing_status="selected",
            self_healing_transition_target="retry",
            self_healing_transition_executed=False,
            self_healing_human_fallback_preserved=False,
            self_healing_chain_budget_remaining_after=1,
            self_healing_transition_count_after=0,
            final_human_review_required=False,
            automatic_restart_executed=False,
            automatic_continuation_run_count=1,
            prior_long_running_replay_key="obj-1|slice_01|assimilated|retry|selected|retry",
            prior_long_running_progress_signature="1|1|0|restart_not_executed|self_healing_not_executed",
            prior_long_running_stale_cycle_count=1,
            prior_long_running_stuck_cycle_count=1,
            prior_long_running_watchdog_heartbeat_at="2026-04-23T12:20:00+00:00",
            now=now_fn,
        )
        self.assertEqual(stuck_payload["long_running_stability_status"], "escalated")
        self.assertEqual(
            stuck_payload["long_running_reason"],
            "long_running_escalated_stuck_detection",
        )
        self.assertTrue(stuck_payload["long_running_stuck_detected"])
        self.assertTrue(stuck_payload["long_running_escalation_required"])
        self.assertTrue(stuck_payload["long_running_pause_required"])
        self.assertFalse(stuck_payload["long_running_resume_allowed"])

    def test_long_running_stability_resume_ready_and_safe_stop_postures(self) -> None:
        now_fn = lambda: datetime.fromisoformat("2026-04-23T13:00:00+00:00")
        resume_payload = _build_long_running_stability_state(
            objective_id="obj-2",
            queue_status="prepared",
            queue_selected_slice_id="slice_02",
            queue_handoff_prepared=True,
            queue_processed_count=2,
            review_assimilation_status="assimilated",
            review_assimilation_action="retry",
            review_assimilation_available=False,
            self_healing_status="selected",
            self_healing_transition_target="retry",
            self_healing_transition_executed=False,
            self_healing_human_fallback_preserved=False,
            self_healing_chain_budget_remaining_after=1,
            self_healing_transition_count_after=0,
            final_human_review_required=False,
            automatic_restart_executed=False,
            automatic_continuation_run_count=2,
            prior_long_running_replay_key="",
            prior_long_running_progress_signature="",
            prior_long_running_stale_cycle_count=0,
            prior_long_running_stuck_cycle_count=0,
            prior_long_running_watchdog_heartbeat_at="",
            now=now_fn,
        )
        self.assertEqual(resume_payload["long_running_stability_status"], "resume_ready")
        self.assertEqual(
            resume_payload["long_running_reason"],
            "long_running_resume_ready_replay_safe",
        )
        self.assertTrue(resume_payload["long_running_resume_allowed"])
        self.assertTrue(resume_payload["long_running_replay_safe"])
        self.assertTrue(resume_payload["long_running_resume_token"])

        safe_stop_payload = _build_long_running_stability_state(
            objective_id="obj-2",
            queue_status="blocked",
            queue_selected_slice_id="slice_02",
            queue_handoff_prepared=False,
            queue_processed_count=2,
            review_assimilation_status="no_action",
            review_assimilation_action="none",
            review_assimilation_available=False,
            self_healing_status="not_applicable",
            self_healing_transition_target="none",
            self_healing_transition_executed=False,
            self_healing_human_fallback_preserved=True,
            self_healing_chain_budget_remaining_after=1,
            self_healing_transition_count_after=0,
            final_human_review_required=False,
            automatic_restart_executed=False,
            automatic_continuation_run_count=2,
            prior_long_running_replay_key="",
            prior_long_running_progress_signature="",
            prior_long_running_stale_cycle_count=0,
            prior_long_running_stuck_cycle_count=0,
            prior_long_running_watchdog_heartbeat_at="",
            now=now_fn,
        )
        self.assertEqual(safe_stop_payload["long_running_stability_status"], "safe_stop")
        self.assertEqual(
            safe_stop_payload["long_running_reason"],
            "long_running_safe_stop_queue_blocked",
        )
        self.assertTrue(safe_stop_payload["long_running_pause_required"])
        self.assertTrue(safe_stop_payload["long_running_safe_stop_required"])

        budget_exhausted_payload = _build_long_running_stability_state(
            objective_id="obj-2",
            queue_status="prepared",
            queue_selected_slice_id="slice_02",
            queue_handoff_prepared=True,
            queue_processed_count=2,
            review_assimilation_status="assimilated",
            review_assimilation_action="retry",
            review_assimilation_available=True,
            self_healing_status="selected",
            self_healing_transition_target="retry",
            self_healing_transition_executed=False,
            self_healing_human_fallback_preserved=False,
            self_healing_chain_budget_remaining_after=0,
            self_healing_transition_count_after=1,
            final_human_review_required=False,
            automatic_restart_executed=False,
            automatic_continuation_run_count=2,
            prior_long_running_replay_key="",
            prior_long_running_progress_signature="",
            prior_long_running_stale_cycle_count=0,
            prior_long_running_stuck_cycle_count=0,
            prior_long_running_watchdog_heartbeat_at="",
            now=now_fn,
        )
        self.assertEqual(
            budget_exhausted_payload["long_running_stability_status"],
            "safe_stop",
        )
        self.assertEqual(
            budget_exhausted_payload["long_running_reason"],
            "long_running_safe_stop_chain_budget_exhausted",
        )
        self.assertTrue(budget_exhausted_payload["long_running_pause_required"])

        escalated_payload = _build_long_running_stability_state(
            objective_id="obj-2",
            queue_status="prepared",
            queue_selected_slice_id="slice_02",
            queue_handoff_prepared=True,
            queue_processed_count=2,
            review_assimilation_status="assimilated",
            review_assimilation_action="replan",
            review_assimilation_available=True,
            self_healing_status="selected",
            self_healing_transition_target="replan",
            self_healing_transition_executed=False,
            self_healing_human_fallback_preserved=False,
            self_healing_chain_budget_remaining_after=1,
            self_healing_transition_count_after=0,
            final_human_review_required=True,
            automatic_restart_executed=False,
            automatic_continuation_run_count=2,
            prior_long_running_replay_key="",
            prior_long_running_progress_signature="",
            prior_long_running_stale_cycle_count=0,
            prior_long_running_stuck_cycle_count=0,
            prior_long_running_watchdog_heartbeat_at="",
            now=now_fn,
        )
        self.assertEqual(escalated_payload["long_running_stability_status"], "escalated")
        self.assertEqual(
            escalated_payload["long_running_reason"],
            "long_running_escalated_final_human_review_required",
        )
        self.assertTrue(escalated_payload["long_running_escalation_required"])
        self.assertTrue(escalated_payload["long_running_pause_required"])

    def test_objective_done_compiler_active_posture_when_work_remains(self) -> None:
        payload = _build_objective_done_compiler_state(
            objective_id="objective-active",
            project_planning_summary_status="available",
            project_pr_slicing_status="available",
            project_pr_slice_count=3,
            project_pr_queue_status="prepared",
            project_pr_queue_reason="queue_item_prepared",
            project_pr_queue_processed_slice_ids_after=["slice_01"],
            review_assimilation_reason="assimilation_accept_success",
            self_healing_human_fallback_preserved=False,
            long_running_stability_status="monitoring",
            final_human_review_required=False,
        )

        self.assertEqual(payload["objective_compiler_status"], "available")
        self.assertTrue(payload["current_objective_available"])
        self.assertEqual(payload["objective_done_criteria_status"], "not_met")
        self.assertFalse(payload["objective_done_criteria_met"])
        self.assertEqual(payload["objective_done_remaining_slice_count"], 2)
        self.assertEqual(payload["objective_stop_criteria_status"], "continue")
        self.assertFalse(payload["objective_stop_criteria_met"])
        self.assertEqual(payload["objective_completion_posture"], "objective_active")
        self.assertEqual(payload["objective_scope_drift_status"], "clear")
        self.assertFalse(payload["objective_scope_drift_detected"])

    def test_objective_done_compiler_completed_posture_when_done_criteria_met(self) -> None:
        payload = _build_objective_done_compiler_state(
            objective_id="objective-complete",
            project_planning_summary_status="available",
            project_pr_slicing_status="available",
            project_pr_slice_count=2,
            project_pr_queue_status="empty",
            project_pr_queue_reason="queue_empty",
            project_pr_queue_processed_slice_ids_after=["slice_01", "slice_02"],
            review_assimilation_reason="assimilation_accept_success",
            self_healing_human_fallback_preserved=False,
            long_running_stability_status="monitoring",
            final_human_review_required=False,
        )

        self.assertEqual(payload["objective_compiler_status"], "available")
        self.assertEqual(payload["objective_done_criteria_status"], "met")
        self.assertTrue(payload["objective_done_criteria_met"])
        self.assertEqual(payload["objective_done_remaining_slice_count"], 0)
        self.assertEqual(payload["objective_completion_posture"], "objective_completed")
        self.assertEqual(payload["objective_scope_drift_status"], "clear")
        self.assertFalse(payload["objective_scope_drift_detected"])

    def test_objective_done_compiler_blocked_posture_for_explicit_review_gate(self) -> None:
        payload = _build_objective_done_compiler_state(
            objective_id="objective-blocked",
            project_planning_summary_status="available",
            project_pr_slicing_status="available",
            project_pr_slice_count=4,
            project_pr_queue_status="blocked",
            project_pr_queue_reason="queue_selected_blocked",
            project_pr_queue_processed_slice_ids_after=["slice_01"],
            review_assimilation_reason="assimilation_escalate_signal",
            self_healing_human_fallback_preserved=True,
            long_running_stability_status="escalated",
            final_human_review_required=True,
        )

        self.assertEqual(payload["objective_compiler_status"], "available")
        self.assertEqual(payload["objective_stop_criteria_status"], "stop")
        self.assertTrue(payload["objective_stop_criteria_met"])
        self.assertEqual(payload["objective_completion_posture"], "objective_blocked")
        self.assertIn(
            "stop_criteria_human_review_required",
            payload["objective_compiler_reason_codes"],
        )

    def test_objective_done_compiler_insufficient_posture_when_objective_truth_missing(self) -> None:
        payload = _build_objective_done_compiler_state(
            objective_id="",
            project_planning_summary_status="insufficient_truth",
            project_pr_slicing_status="insufficient_truth",
            project_pr_slice_count=0,
            project_pr_queue_status="insufficient_truth",
            project_pr_queue_reason="queue_state_insufficient_truth",
            project_pr_queue_processed_slice_ids_after=[],
            review_assimilation_reason="assimilation_insufficient_truth",
            self_healing_human_fallback_preserved=True,
            long_running_stability_status="insufficient_truth",
            final_human_review_required=False,
        )

        self.assertEqual(payload["objective_compiler_status"], "insufficient_truth")
        self.assertFalse(payload["current_objective_available"])
        self.assertEqual(payload["objective_done_criteria_status"], "insufficient_truth")
        self.assertEqual(payload["objective_stop_criteria_status"], "insufficient_truth")
        self.assertEqual(
            payload["objective_completion_posture"],
            "objective_insufficient_truth",
        )
        self.assertEqual(payload["objective_scope_drift_status"], "insufficient_truth")

    def test_objective_done_compiler_detects_scope_drift_from_queue_prompt_mismatch(self) -> None:
        payload = _build_objective_done_compiler_state(
            objective_id="objective-scope-drift",
            project_planning_summary_status="available",
            project_pr_slicing_status="available",
            project_pr_slice_count=3,
            project_pr_queue_status="blocked",
            project_pr_queue_reason="prompt_unavailable_for_selected_slice",
            project_pr_queue_processed_slice_ids_after=["slice_01"],
            review_assimilation_reason="assimilation_accept_success",
            self_healing_human_fallback_preserved=False,
            long_running_stability_status="monitoring",
            final_human_review_required=False,
        )

        self.assertEqual(payload["objective_compiler_status"], "available")
        self.assertEqual(payload["objective_scope_drift_status"], "detected")
        self.assertTrue(payload["objective_scope_drift_detected"])
        self.assertEqual(
            payload["objective_scope_drift_reason"],
            "scope_drift_detected_queue_prompt_mismatch",
        )

    def test_project_autonomy_budget_compiler_compiles_active_posture(self) -> None:
        payload = _build_project_autonomy_budget_state(
            project_planning_summary_status="available",
            objective_compiler_status="available",
            objective_completion_posture="objective_active",
            final_human_review_required=False,
            high_risk_posture=False,
            continuation_budget_truth_sufficient=True,
            continuation_budget_status="available",
            continuation_budget_run_exhausted=False,
            continuation_budget_objective_exhausted=False,
            continuation_budget_run_limit=2,
            continuation_budget_objective_limit=2,
            continuation_budget_run_remaining=1,
            continuation_budget_objective_remaining=1,
            continuation_budget_branch_type="retry",
            continuation_budget_branch_status="available",
            continuation_budget_branch_exhausted=False,
            continuation_budget_branch_limit=2,
            continuation_budget_branch_remaining=1,
        )

        self.assertEqual(payload["project_autonomy_budget_status"], "available")
        self.assertEqual(payload["project_priority_posture"], "active")
        self.assertFalse(payload["project_priority_deferred"])
        self.assertEqual(payload["project_high_risk_defer_posture"], "clear")
        self.assertFalse(payload["project_high_risk_defer_active"])
        self.assertEqual(payload["project_run_budget_posture"], "available")
        self.assertEqual(payload["project_objective_budget_posture"], "available")
        self.assertEqual(payload["project_pr_retry_budget_posture"], "available")
        self.assertTrue(payload["project_pr_retry_budget_applicable"])
        self.assertFalse(payload["project_pr_retry_budget_exhausted"])

    def test_project_autonomy_budget_compiler_defers_for_high_risk_or_blocked(self) -> None:
        payload = _build_project_autonomy_budget_state(
            project_planning_summary_status="available",
            objective_compiler_status="available",
            objective_completion_posture="objective_blocked",
            final_human_review_required=True,
            high_risk_posture=True,
            continuation_budget_truth_sufficient=True,
            continuation_budget_status="available",
            continuation_budget_run_exhausted=False,
            continuation_budget_objective_exhausted=False,
            continuation_budget_run_limit=2,
            continuation_budget_objective_limit=2,
            continuation_budget_run_remaining=2,
            continuation_budget_objective_remaining=2,
            continuation_budget_branch_type="replan",
            continuation_budget_branch_status="available",
            continuation_budget_branch_exhausted=False,
            continuation_budget_branch_limit=2,
            continuation_budget_branch_remaining=2,
        )

        self.assertEqual(payload["project_autonomy_budget_status"], "available")
        self.assertEqual(payload["project_priority_posture"], "deferred")
        self.assertTrue(payload["project_priority_deferred"])
        self.assertEqual(payload["project_high_risk_defer_posture"], "defer")
        self.assertTrue(payload["project_high_risk_defer_active"])
        self.assertEqual(payload["project_pr_retry_budget_posture"], "not_applicable")
        self.assertFalse(payload["project_pr_retry_budget_applicable"])

    def test_project_autonomy_budget_compiler_marks_exhausted_run_and_retry_budget(self) -> None:
        payload = _build_project_autonomy_budget_state(
            project_planning_summary_status="available",
            objective_compiler_status="available",
            objective_completion_posture="objective_active",
            final_human_review_required=False,
            high_risk_posture=False,
            continuation_budget_truth_sufficient=True,
            continuation_budget_status="exhausted",
            continuation_budget_run_exhausted=True,
            continuation_budget_objective_exhausted=False,
            continuation_budget_run_limit=2,
            continuation_budget_objective_limit=2,
            continuation_budget_run_remaining=0,
            continuation_budget_objective_remaining=1,
            continuation_budget_branch_type="retry",
            continuation_budget_branch_status="exhausted",
            continuation_budget_branch_exhausted=True,
            continuation_budget_branch_limit=2,
            continuation_budget_branch_remaining=0,
        )

        self.assertEqual(payload["project_autonomy_budget_status"], "available")
        self.assertEqual(payload["project_priority_posture"], "lower_priority")
        self.assertEqual(payload["project_run_budget_posture"], "exhausted")
        self.assertTrue(payload["project_run_budget_exhausted"])
        self.assertEqual(payload["project_pr_retry_budget_posture"], "exhausted")
        self.assertTrue(payload["project_pr_retry_budget_exhausted"])

    def test_project_autonomy_budget_compiler_emits_insufficient_posture(self) -> None:
        payload = _build_project_autonomy_budget_state(
            project_planning_summary_status="insufficient_truth",
            objective_compiler_status="insufficient_truth",
            objective_completion_posture="objective_insufficient_truth",
            final_human_review_required=False,
            high_risk_posture=False,
            continuation_budget_truth_sufficient=False,
            continuation_budget_status="insufficient_truth",
            continuation_budget_run_exhausted=False,
            continuation_budget_objective_exhausted=False,
            continuation_budget_run_limit=2,
            continuation_budget_objective_limit=2,
            continuation_budget_run_remaining=0,
            continuation_budget_objective_remaining=0,
            continuation_budget_branch_type="unknown",
            continuation_budget_branch_status="not_applicable",
            continuation_budget_branch_exhausted=False,
            continuation_budget_branch_limit=0,
            continuation_budget_branch_remaining=0,
        )

        self.assertEqual(payload["project_autonomy_budget_status"], "insufficient_truth")
        self.assertEqual(payload["project_priority_posture"], "insufficient_truth")
        self.assertEqual(payload["project_run_budget_posture"], "insufficient_truth")
        self.assertEqual(payload["project_objective_budget_posture"], "insufficient_truth")
        self.assertEqual(payload["project_pr_retry_budget_posture"], "insufficient_truth")
        self.assertEqual(payload["project_high_risk_defer_posture"], "insufficient_truth")

    def test_project_quality_gate_compiler_emits_merge_ready_posture(self) -> None:
        payload = _build_project_quality_gate_state(
            project_planning_summary_status="available",
            project_pr_slicing_status="available",
            implementation_prompt_status="available",
            implementation_prompt_payload={
                "preferred_files": [
                    "automation/orchestration/planned_execution_runner.py",
                    "tests/test_planned_execution_runner.py",
                ],
                "bounded_scope_class": "runner_and_tests",
            },
            project_pr_queue_status="empty",
            review_assimilation_status="assimilated",
            review_assimilation_action="accept",
            self_healing_status="not_applicable",
            long_running_stability_status="monitoring",
            objective_compiler_status="available",
            objective_completion_posture="objective_completed",
            objective_scope_drift_detected=False,
            project_autonomy_budget_status="available",
            project_priority_posture="active",
            project_run_budget_posture="available",
            project_objective_budget_posture="available",
            project_pr_retry_budget_posture="available",
            project_high_risk_defer_posture="clear",
            continuation_failure_bucket_denied=False,
            continuation_no_progress_stop_required=False,
            continuation_next_step_selection_status="not_selected",
            continuation_next_step_target="none",
            supported_repair_execution_status="executed_verification_passed",
            final_human_review_required=False,
        )

        self.assertEqual(payload["project_quality_gate_status"], "available")
        self.assertEqual(payload["project_quality_gate_posture"], "merge_ready")
        self.assertTrue(payload["project_quality_gate_merge_ready"])
        self.assertFalse(payload["project_quality_gate_review_ready"])
        self.assertFalse(payload["project_quality_gate_retry_needed"])
        self.assertEqual(payload["project_quality_gate_changed_area_class"], "runner_and_tests")
        self.assertEqual(payload["project_quality_gate_risk_level"], "low")
        self.assertEqual(
            payload["project_quality_gate_recommended"],
            ["unit", "targeted_regression", "lint", "typecheck"],
        )

    def test_project_quality_gate_compiler_emits_retry_needed_posture(self) -> None:
        payload = _build_project_quality_gate_state(
            project_planning_summary_status="available",
            project_pr_slicing_status="available",
            implementation_prompt_status="available",
            implementation_prompt_payload={
                "preferred_files": ["automation/orchestration/planned_execution_runner.py"],
                "bounded_scope_class": "runner_only",
            },
            project_pr_queue_status="prepared",
            review_assimilation_status="assimilated",
            review_assimilation_action="retry",
            self_healing_status="selected",
            long_running_stability_status="monitoring",
            objective_compiler_status="available",
            objective_completion_posture="objective_active",
            objective_scope_drift_detected=False,
            project_autonomy_budget_status="available",
            project_priority_posture="active",
            project_run_budget_posture="available",
            project_objective_budget_posture="available",
            project_pr_retry_budget_posture="available",
            project_high_risk_defer_posture="clear",
            continuation_failure_bucket_denied=False,
            continuation_no_progress_stop_required=False,
            continuation_next_step_selection_status="selected",
            continuation_next_step_target="retry",
            supported_repair_execution_status="not_selected",
            final_human_review_required=False,
        )

        self.assertEqual(payload["project_quality_gate_status"], "available")
        self.assertEqual(payload["project_quality_gate_posture"], "retry_needed")
        self.assertFalse(payload["project_quality_gate_merge_ready"])
        self.assertFalse(payload["project_quality_gate_review_ready"])
        self.assertTrue(payload["project_quality_gate_retry_needed"])
        self.assertEqual(payload["project_quality_gate_changed_area_class"], "runner_only")
        self.assertEqual(payload["project_quality_gate_risk_level"], "moderate")
        self.assertIn("targeted_regression", payload["project_quality_gate_recommended"])

    def test_project_quality_gate_compiler_emits_review_ready_for_high_risk_defer(self) -> None:
        payload = _build_project_quality_gate_state(
            project_planning_summary_status="available",
            project_pr_slicing_status="available",
            implementation_prompt_status="available",
            implementation_prompt_payload={
                "preferred_files": ["automation/orchestration/planned_execution_runner.py"],
                "bounded_scope_class": "runner_only",
            },
            project_pr_queue_status="blocked",
            review_assimilation_status="no_action",
            review_assimilation_action="none",
            self_healing_status="not_applicable",
            long_running_stability_status="safe_stop",
            objective_compiler_status="available",
            objective_completion_posture="objective_blocked",
            objective_scope_drift_detected=True,
            project_autonomy_budget_status="available",
            project_priority_posture="deferred",
            project_run_budget_posture="available",
            project_objective_budget_posture="available",
            project_pr_retry_budget_posture="not_applicable",
            project_high_risk_defer_posture="defer",
            continuation_failure_bucket_denied=True,
            continuation_no_progress_stop_required=True,
            continuation_next_step_selection_status="not_selected",
            continuation_next_step_target="none",
            supported_repair_execution_status="not_executed_precheck_blocked",
            final_human_review_required=True,
        )

        self.assertEqual(payload["project_quality_gate_status"], "available")
        self.assertIn(
            payload["project_quality_gate_posture"],
            {"review_ready", "retry_needed"},
        )
        self.assertFalse(payload["project_quality_gate_merge_ready"])
        self.assertEqual(payload["project_quality_gate_risk_level"], "high")
        self.assertTrue(payload["project_quality_gate_high_risk"])
        self.assertIn("targeted_regression", payload["project_quality_gate_recommended"])

    def test_project_quality_gate_compiler_emits_insufficient_posture(self) -> None:
        payload = _build_project_quality_gate_state(
            project_planning_summary_status="insufficient_truth",
            project_pr_slicing_status="insufficient_truth",
            implementation_prompt_status="insufficient_truth",
            implementation_prompt_payload={},
            project_pr_queue_status="insufficient_truth",
            review_assimilation_status="insufficient_truth",
            review_assimilation_action="none",
            self_healing_status="insufficient_truth",
            long_running_stability_status="insufficient_truth",
            objective_compiler_status="insufficient_truth",
            objective_completion_posture="objective_insufficient_truth",
            objective_scope_drift_detected=False,
            project_autonomy_budget_status="insufficient_truth",
            project_priority_posture="insufficient_truth",
            project_run_budget_posture="insufficient_truth",
            project_objective_budget_posture="insufficient_truth",
            project_pr_retry_budget_posture="insufficient_truth",
            project_high_risk_defer_posture="insufficient_truth",
            continuation_failure_bucket_denied=False,
            continuation_no_progress_stop_required=False,
            continuation_next_step_selection_status="insufficient_truth",
            continuation_next_step_target="none",
            supported_repair_execution_status="not_selected",
            final_human_review_required=False,
        )

        self.assertEqual(payload["project_quality_gate_status"], "insufficient_truth")
        self.assertEqual(payload["project_quality_gate_posture"], "insufficient_truth")
        self.assertTrue(payload["project_quality_gate_unavailable"])
        self.assertEqual(payload["project_quality_gate_recommended"], [])
        self.assertEqual(payload["project_quality_gate_recommended_count"], 0)

    def test_project_merge_branch_lifecycle_compiler_emits_merge_ready_cleanup_and_sync(self) -> None:
        payload = _build_project_merge_branch_lifecycle_state(
            project_quality_gate_status="available",
            project_quality_gate_posture="merge_ready",
            project_quality_gate_merge_ready=True,
            project_quality_gate_retry_needed=False,
            project_quality_gate_high_risk=False,
            objective_compiler_status="available",
            objective_completion_posture="objective_completed",
            project_autonomy_budget_status="available",
            project_priority_posture="active",
            project_high_risk_defer_posture="clear",
            project_pr_queue_status="empty",
            project_pr_queue_processed_count=2,
            review_assimilation_status="assimilated",
            review_assimilation_action="accept",
            self_healing_status="not_applicable",
            long_running_stability_status="monitoring",
            final_human_review_required=False,
            final_human_review_gate_status="not_required",
            continuation_failure_bucket_denied=False,
            continuation_no_progress_stop_required=False,
            supported_repair_execution_status="executed_verification_passed",
        )

        self.assertEqual(payload["project_merge_branch_lifecycle_status"], "available")
        self.assertEqual(payload["project_merge_ready_posture"], "merge_ready")
        self.assertTrue(payload["project_merge_ready"])
        self.assertEqual(payload["project_branch_cleanup_candidate_posture"], "candidate")
        self.assertTrue(payload["project_branch_cleanup_candidate"])
        self.assertEqual(payload["project_branch_quarantine_candidate_posture"], "not_candidate")
        self.assertFalse(payload["project_branch_quarantine_candidate"])
        self.assertEqual(payload["project_local_main_sync_posture"], "sync_required")
        self.assertTrue(payload["project_local_main_sync_required"])
        self.assertFalse(payload["project_merge_branch_lifecycle_unavailable"])

    def test_project_merge_branch_lifecycle_compiler_emits_quarantine_candidate(self) -> None:
        payload = _build_project_merge_branch_lifecycle_state(
            project_quality_gate_status="available",
            project_quality_gate_posture="review_ready",
            project_quality_gate_merge_ready=False,
            project_quality_gate_retry_needed=True,
            project_quality_gate_high_risk=True,
            objective_compiler_status="available",
            objective_completion_posture="objective_blocked",
            project_autonomy_budget_status="available",
            project_priority_posture="deferred",
            project_high_risk_defer_posture="defer",
            project_pr_queue_status="blocked",
            project_pr_queue_processed_count=1,
            review_assimilation_status="no_action",
            review_assimilation_action="none",
            self_healing_status="selected",
            long_running_stability_status="safe_stop",
            final_human_review_required=True,
            final_human_review_gate_status="required",
            continuation_failure_bucket_denied=True,
            continuation_no_progress_stop_required=True,
            supported_repair_execution_status="executed_verification_failed",
        )

        self.assertEqual(payload["project_merge_branch_lifecycle_status"], "available")
        self.assertEqual(payload["project_merge_ready_posture"], "not_merge_ready")
        self.assertFalse(payload["project_merge_ready"])
        self.assertEqual(payload["project_branch_cleanup_candidate_posture"], "not_candidate")
        self.assertFalse(payload["project_branch_cleanup_candidate"])
        self.assertEqual(payload["project_branch_quarantine_candidate_posture"], "candidate")
        self.assertTrue(payload["project_branch_quarantine_candidate"])
        self.assertEqual(payload["project_local_main_sync_posture"], "sync_required")
        self.assertTrue(payload["project_local_main_sync_required"])

    def test_project_merge_branch_lifecycle_compiler_emits_insufficient_posture(self) -> None:
        payload = _build_project_merge_branch_lifecycle_state(
            project_quality_gate_status="insufficient_truth",
            project_quality_gate_posture="insufficient_truth",
            project_quality_gate_merge_ready=False,
            project_quality_gate_retry_needed=False,
            project_quality_gate_high_risk=False,
            objective_compiler_status="insufficient_truth",
            objective_completion_posture="objective_insufficient_truth",
            project_autonomy_budget_status="insufficient_truth",
            project_priority_posture="insufficient_truth",
            project_high_risk_defer_posture="insufficient_truth",
            project_pr_queue_status="insufficient_truth",
            project_pr_queue_processed_count=0,
            review_assimilation_status="insufficient_truth",
            review_assimilation_action="none",
            self_healing_status="insufficient_truth",
            long_running_stability_status="insufficient_truth",
            final_human_review_required=False,
            final_human_review_gate_status="not_required",
            continuation_failure_bucket_denied=False,
            continuation_no_progress_stop_required=False,
            supported_repair_execution_status="not_selected",
        )

        self.assertEqual(payload["project_merge_branch_lifecycle_status"], "insufficient_truth")
        self.assertEqual(payload["project_merge_ready_posture"], "insufficient_truth")
        self.assertEqual(payload["project_branch_cleanup_candidate_posture"], "insufficient_truth")
        self.assertEqual(
            payload["project_branch_quarantine_candidate_posture"],
            "insufficient_truth",
        )
        self.assertEqual(payload["project_local_main_sync_posture"], "insufficient_truth")
        self.assertTrue(payload["project_merge_branch_lifecycle_unavailable"])

    def test_project_failure_memory_compiler_emits_retry_suppression(self) -> None:
        payload = _build_project_failure_memory_state(
            project_merge_branch_lifecycle_status="available",
            project_branch_quarantine_candidate=True,
            failure_bucketing_status="classified",
            failure_bucketing_validity="valid",
            failure_bucketing_primary_bucket="same_failure_exhausted",
            continuation_next_step_selection_status="selected",
            continuation_next_step_target="retry",
            continuation_no_progress_stop_required=True,
            continuation_failure_bucket_denied=False,
            review_assimilation_status="assimilated",
            review_assimilation_action="retry",
            self_healing_status="executed",
            supported_repair_execution_status="not_selected",
            execution_status="not_executed",
            execution_reason="continuation_no_progress_stop",
            restart_result_status="not_attempted",
            final_human_review_required=True,
            prior_retry_failure_count=1,
            prior_repair_failure_count=0,
            prior_review_issue_count=0,
            prior_failure_bucket_recurrence_count=0,
            prior_failure_bucket_value="other_bucket",
        )

        self.assertEqual(payload["project_failure_memory_status"], "available")
        self.assertTrue(payload["project_failure_memory_ineffective_retry"])
        self.assertEqual(payload["project_failure_memory_retry_failure_count"], 2)
        self.assertEqual(
            payload["project_failure_memory_suppression_posture"],
            "suppress_retry",
        )
        self.assertTrue(payload["project_failure_memory_suppression_active"])
        self.assertFalse(payload["project_failure_memory_unavailable"])

    def test_project_failure_memory_compiler_emits_failed_repair_and_bucket_recurrence(self) -> None:
        payload = _build_project_failure_memory_state(
            project_merge_branch_lifecycle_status="available",
            project_branch_quarantine_candidate=True,
            failure_bucketing_status="classified",
            failure_bucketing_validity="valid",
            failure_bucketing_primary_bucket="verification_failure",
            continuation_next_step_selection_status="selected",
            continuation_next_step_target="supported_repair",
            continuation_no_progress_stop_required=False,
            continuation_failure_bucket_denied=True,
            review_assimilation_status="assimilated",
            review_assimilation_action="replan",
            self_healing_status="selected",
            supported_repair_execution_status="executed_verification_failed",
            execution_status="not_executed",
            execution_reason="supported_repair_verification_failed",
            restart_result_status="failed",
            final_human_review_required=True,
            prior_retry_failure_count=0,
            prior_repair_failure_count=1,
            prior_review_issue_count=0,
            prior_failure_bucket_recurrence_count=1,
            prior_failure_bucket_value="verification_failure",
        )

        self.assertEqual(payload["project_failure_memory_status"], "available")
        self.assertTrue(payload["project_failure_memory_failed_repair"])
        self.assertTrue(payload["project_failure_memory_recurring_failure_bucket"])
        self.assertEqual(payload["project_failure_memory_repair_failure_count"], 2)
        self.assertEqual(
            payload["project_failure_memory_failure_bucket_recurrence_count"],
            2,
        )
        self.assertEqual(
            payload["project_failure_memory_suppression_posture"],
            "suppress_failure_bucket",
        )
        self.assertTrue(payload["project_failure_memory_suppression_active"])

    def test_project_failure_memory_compiler_emits_insufficient_posture(self) -> None:
        payload = _build_project_failure_memory_state(
            project_merge_branch_lifecycle_status="insufficient_truth",
            project_branch_quarantine_candidate=False,
            failure_bucketing_status="insufficient_truth",
            failure_bucketing_validity="insufficient_truth",
            failure_bucketing_primary_bucket="unknown",
            continuation_next_step_selection_status="insufficient_truth",
            continuation_next_step_target="none",
            continuation_no_progress_stop_required=False,
            continuation_failure_bucket_denied=False,
            review_assimilation_status="insufficient_truth",
            review_assimilation_action="none",
            self_healing_status="insufficient_truth",
            supported_repair_execution_status="not_selected",
            execution_status="not_executed",
            execution_reason="restart_not_executed",
            restart_result_status="not_attempted",
            final_human_review_required=False,
            prior_retry_failure_count=0,
            prior_repair_failure_count=0,
            prior_review_issue_count=0,
            prior_failure_bucket_recurrence_count=0,
            prior_failure_bucket_value="unknown",
        )

        self.assertEqual(payload["project_failure_memory_status"], "insufficient_truth")
        self.assertEqual(
            payload["project_failure_memory_suppression_posture"],
            "insufficient_truth",
        )
        self.assertTrue(payload["project_failure_memory_unavailable"])

    def test_project_external_boundary_compiler_emits_dependency_available_posture(self) -> None:
        payload = _build_project_external_boundary_state(
            project_failure_memory_status="available",
            project_failure_memory_suppression_posture="none",
            project_failure_memory_suppression_active=False,
            project_merge_branch_lifecycle_status="available",
            project_merge_ready_posture="merge_ready",
            project_branch_quarantine_candidate_posture="not_candidate",
            project_local_main_sync_posture="sync_not_required",
            project_quality_gate_status="available",
            project_quality_gate_posture="merge_ready",
            project_quality_gate_risk_level="low",
            project_pr_queue_status="empty",
            project_autonomy_budget_status="available",
            project_priority_posture="active",
            long_running_stability_status="monitoring",
            supported_repair_execution_status="executed_verification_passed",
            execution_reason="restart_executed_once",
            final_human_review_required=False,
            final_human_review_gate_status="not_required",
            manual_only_posture_active=False,
            fleet_manual_review_required=False,
            approval_reason_class="restart_hold",
        )

        self.assertEqual(payload["project_external_boundary_status"], "available")
        self.assertEqual(
            payload["project_external_dependency_posture"],
            "dependency_available",
        )
        self.assertTrue(payload["project_external_dependency_available"])
        self.assertFalse(payload["project_external_dependency_blocked"])
        self.assertEqual(payload["project_external_manual_only_posture"], "clear")
        self.assertFalse(payload["project_external_manual_only_required"])
        self.assertEqual(payload["project_external_network_boundary_posture"], "clear")
        self.assertEqual(payload["project_external_ci_boundary_posture"], "clear")
        self.assertEqual(payload["project_external_secrets_boundary_posture"], "clear")
        self.assertEqual(payload["project_external_github_boundary_posture"], "clear")
        self.assertEqual(payload["project_external_api_boundary_posture"], "clear")
        self.assertFalse(payload["project_external_boundary_unavailable"])

    def test_project_external_boundary_compiler_emits_manual_only_posture(self) -> None:
        payload = _build_project_external_boundary_state(
            project_failure_memory_status="available",
            project_failure_memory_suppression_posture="suppress_failure_bucket",
            project_failure_memory_suppression_active=True,
            project_merge_branch_lifecycle_status="available",
            project_merge_ready_posture="not_merge_ready",
            project_branch_quarantine_candidate_posture="candidate",
            project_local_main_sync_posture="sync_required",
            project_quality_gate_status="available",
            project_quality_gate_posture="review_ready",
            project_quality_gate_risk_level="high",
            project_pr_queue_status="blocked",
            project_autonomy_budget_status="available",
            project_priority_posture="deferred",
            long_running_stability_status="safe_stop",
            supported_repair_execution_status="executed_verification_failed",
            execution_reason="supported_repair_verification_failed",
            final_human_review_required=True,
            final_human_review_gate_status="required",
            manual_only_posture_active=True,
            fleet_manual_review_required=True,
            approval_reason_class="manual_only",
        )

        self.assertEqual(payload["project_external_boundary_status"], "available")
        self.assertEqual(payload["project_external_dependency_posture"], "manual_only")
        self.assertFalse(payload["project_external_dependency_available"])
        self.assertFalse(payload["project_external_dependency_blocked"])
        self.assertEqual(payload["project_external_manual_only_posture"], "manual_only")
        self.assertTrue(payload["project_external_manual_only_required"])
        self.assertEqual(payload["project_external_network_boundary_posture"], "manual_only")
        self.assertEqual(payload["project_external_ci_boundary_posture"], "manual_only")
        self.assertEqual(payload["project_external_secrets_boundary_posture"], "manual_only")
        self.assertEqual(payload["project_external_github_boundary_posture"], "manual_only")
        self.assertEqual(payload["project_external_api_boundary_posture"], "manual_only")

    def test_project_external_boundary_compiler_emits_insufficient_posture(self) -> None:
        payload = _build_project_external_boundary_state(
            project_failure_memory_status="insufficient_truth",
            project_failure_memory_suppression_posture="insufficient_truth",
            project_failure_memory_suppression_active=False,
            project_merge_branch_lifecycle_status="insufficient_truth",
            project_merge_ready_posture="insufficient_truth",
            project_branch_quarantine_candidate_posture="insufficient_truth",
            project_local_main_sync_posture="insufficient_truth",
            project_quality_gate_status="insufficient_truth",
            project_quality_gate_posture="insufficient_truth",
            project_quality_gate_risk_level="insufficient_truth",
            project_pr_queue_status="insufficient_truth",
            project_autonomy_budget_status="insufficient_truth",
            project_priority_posture="insufficient_truth",
            long_running_stability_status="insufficient_truth",
            supported_repair_execution_status="not_selected",
            execution_reason="restart_not_executed",
            final_human_review_required=False,
            final_human_review_gate_status="not_required",
            manual_only_posture_active=False,
            fleet_manual_review_required=False,
            approval_reason_class="unknown",
        )

        self.assertEqual(payload["project_external_boundary_status"], "insufficient_truth")
        self.assertEqual(
            payload["project_external_dependency_posture"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["project_external_manual_only_posture"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["project_external_network_boundary_posture"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["project_external_github_boundary_posture"],
            "insufficient_truth",
        )
        self.assertTrue(payload["project_external_boundary_unavailable"])

    def test_project_human_escalation_compiler_emits_escalation_required(self) -> None:
        payload = _build_project_human_escalation_state(
            final_human_review_gate_status="required",
            final_human_review_required=True,
            final_human_review_reason="final_review_high_risk_posture",
            objective_compiler_status="available",
            objective_completion_posture="objective_blocked",
            objective_scope_drift_status="detected",
            project_autonomy_budget_status="available",
            project_priority_posture="deferred",
            project_high_risk_defer_posture="defer",
            project_run_budget_posture="exhausted",
            project_objective_budget_posture="available",
            project_pr_retry_budget_posture="exhausted",
            project_quality_gate_status="available",
            project_quality_gate_risk_level="high",
            project_quality_gate_high_risk=True,
            project_merge_branch_lifecycle_status="available",
            project_branch_quarantine_candidate_posture="candidate",
            project_failure_memory_status="available",
            project_failure_memory_suppression_posture="suppress_failure_bucket",
            project_failure_memory_suppression_active=True,
            project_failure_memory_retry_failure_count=2,
            project_failure_memory_repair_failure_count=1,
            project_failure_memory_review_issue_count=2,
            project_failure_memory_failure_bucket_recurrence_count=1,
            project_external_boundary_status="available",
            project_external_dependency_posture="dependency_blocked",
            project_external_manual_only_posture="clear",
            project_external_manual_only_required=False,
            long_running_stability_status="escalated",
            supported_repair_execution_status="executed_verification_failed",
            manual_only_posture_active=False,
            fleet_manual_review_required=False,
        )

        self.assertEqual(payload["project_human_escalation_status"], "available")
        self.assertEqual(
            payload["project_human_escalation_posture"],
            "escalation_required",
        )
        self.assertTrue(payload["project_human_escalation_required"])
        self.assertEqual(payload["project_architecture_risk_posture"], "elevated")
        self.assertEqual(payload["project_scope_risk_posture"], "elevated")
        self.assertEqual(payload["project_external_risk_posture"], "elevated")
        self.assertEqual(payload["project_budget_risk_posture"], "elevated")
        self.assertEqual(
            payload["project_repeated_failure_risk_posture"],
            "elevated",
        )
        self.assertEqual(payload["project_manual_only_risk_posture"], "clear")
        self.assertFalse(payload["project_human_escalation_unavailable"])

    def test_project_human_escalation_compiler_emits_not_required(self) -> None:
        payload = _build_project_human_escalation_state(
            final_human_review_gate_status="not_required",
            final_human_review_required=False,
            final_human_review_reason="final_review_not_required",
            objective_compiler_status="available",
            objective_completion_posture="objective_active",
            objective_scope_drift_status="clear",
            project_autonomy_budget_status="available",
            project_priority_posture="active",
            project_high_risk_defer_posture="clear",
            project_run_budget_posture="available",
            project_objective_budget_posture="available",
            project_pr_retry_budget_posture="not_applicable",
            project_quality_gate_status="available",
            project_quality_gate_risk_level="low",
            project_quality_gate_high_risk=False,
            project_merge_branch_lifecycle_status="available",
            project_branch_quarantine_candidate_posture="not_candidate",
            project_failure_memory_status="available",
            project_failure_memory_suppression_posture="none",
            project_failure_memory_suppression_active=False,
            project_failure_memory_retry_failure_count=0,
            project_failure_memory_repair_failure_count=0,
            project_failure_memory_review_issue_count=0,
            project_failure_memory_failure_bucket_recurrence_count=0,
            project_external_boundary_status="available",
            project_external_dependency_posture="dependency_available",
            project_external_manual_only_posture="clear",
            project_external_manual_only_required=False,
            long_running_stability_status="monitoring",
            supported_repair_execution_status="executed_verification_passed",
            manual_only_posture_active=False,
            fleet_manual_review_required=False,
        )

        self.assertEqual(payload["project_human_escalation_status"], "available")
        self.assertEqual(
            payload["project_human_escalation_posture"],
            "not_required",
        )
        self.assertFalse(payload["project_human_escalation_required"])
        self.assertEqual(payload["project_architecture_risk_posture"], "clear")
        self.assertEqual(payload["project_scope_risk_posture"], "clear")
        self.assertEqual(payload["project_external_risk_posture"], "clear")
        self.assertEqual(payload["project_budget_risk_posture"], "clear")
        self.assertEqual(payload["project_repeated_failure_risk_posture"], "clear")
        self.assertEqual(payload["project_manual_only_risk_posture"], "clear")
        self.assertFalse(payload["project_human_escalation_unavailable"])

    def test_project_human_escalation_compiler_emits_insufficient(self) -> None:
        payload = _build_project_human_escalation_state(
            final_human_review_gate_status="not_required",
            final_human_review_required=False,
            final_human_review_reason="final_review_not_required",
            objective_compiler_status="insufficient_truth",
            objective_completion_posture="objective_insufficient_truth",
            objective_scope_drift_status="insufficient_truth",
            project_autonomy_budget_status="insufficient_truth",
            project_priority_posture="insufficient_truth",
            project_high_risk_defer_posture="insufficient_truth",
            project_run_budget_posture="insufficient_truth",
            project_objective_budget_posture="insufficient_truth",
            project_pr_retry_budget_posture="insufficient_truth",
            project_quality_gate_status="insufficient_truth",
            project_quality_gate_risk_level="insufficient_truth",
            project_quality_gate_high_risk=False,
            project_merge_branch_lifecycle_status="insufficient_truth",
            project_branch_quarantine_candidate_posture="insufficient_truth",
            project_failure_memory_status="insufficient_truth",
            project_failure_memory_suppression_posture="insufficient_truth",
            project_failure_memory_suppression_active=False,
            project_failure_memory_retry_failure_count=0,
            project_failure_memory_repair_failure_count=0,
            project_failure_memory_review_issue_count=0,
            project_failure_memory_failure_bucket_recurrence_count=0,
            project_external_boundary_status="insufficient_truth",
            project_external_dependency_posture="insufficient_truth",
            project_external_manual_only_posture="insufficient_truth",
            project_external_manual_only_required=False,
            long_running_stability_status="insufficient_truth",
            supported_repair_execution_status="not_selected",
            manual_only_posture_active=False,
            fleet_manual_review_required=False,
        )

        self.assertEqual(
            payload["project_human_escalation_status"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["project_human_escalation_posture"],
            "insufficient_truth",
        )
        self.assertFalse(payload["project_human_escalation_required"])
        self.assertEqual(
            payload["project_architecture_risk_posture"],
            "insufficient_truth",
        )
        self.assertEqual(payload["project_scope_risk_posture"], "insufficient_truth")
        self.assertEqual(payload["project_external_risk_posture"], "insufficient_truth")
        self.assertEqual(payload["project_budget_risk_posture"], "insufficient_truth")
        self.assertEqual(
            payload["project_repeated_failure_risk_posture"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["project_manual_only_risk_posture"],
            "insufficient_truth",
        )
        self.assertTrue(payload["project_human_escalation_unavailable"])

    def test_project_approval_notification_compiler_emits_ready_reply_required(self) -> None:
        payload = _build_project_approval_notification_state(
            approval_required=True,
            approval_email_status="required",
            approval_email_validity="valid",
            approval_priority="high",
            approval_reason_class="manual_only",
            proposed_next_direction="replan_preparation",
            delivery_mode="gmail_draft",
            delivery_outcome="draft_created",
            approval_response_status="awaiting_response",
            approval_response_validity="valid",
            response_received=False,
            response_decision_class="unknown",
            project_human_escalation_status="available",
            project_human_escalation_posture="escalation_required",
            project_human_escalation_required=True,
            project_human_escalation_reason="escalation_manual_only_risk_elevated",
            project_architecture_risk_posture="clear",
            project_scope_risk_posture="clear",
            project_external_risk_posture="elevated",
            project_budget_risk_posture="elevated",
            project_repeated_failure_risk_posture="clear",
            project_manual_only_risk_posture="elevated",
            project_external_manual_only_posture="manual_only",
        )

        self.assertEqual(payload["project_approval_notification_status"], "available")
        self.assertEqual(payload["project_approval_notification_ready_posture"], "ready")
        self.assertTrue(payload["project_approval_notification_ready"])
        self.assertEqual(payload["project_approval_reply_required_posture"], "reply_required")
        self.assertTrue(payload["project_approval_reply_required"])
        self.assertEqual(payload["project_approval_channel_posture"], "manual_only")
        self.assertEqual(payload["project_approval_mobile_summary_posture"], "available")
        self.assertTrue(payload["project_approval_mobile_summary_compact"])
        self.assertIn("escalate", payload["project_approval_mobile_summary_tokens"])
        self.assertFalse(payload["project_approval_notification_unavailable"])

    def test_project_approval_notification_compiler_emits_not_required(self) -> None:
        payload = _build_project_approval_notification_state(
            approval_required=True,
            approval_email_status="not_required",
            approval_email_validity="valid",
            approval_priority="low",
            approval_reason_class="restart_hold",
            proposed_next_direction="same_lane_retry",
            delivery_mode="not_applicable",
            delivery_outcome="skipped",
            approval_response_status="response_accepted",
            approval_response_validity="valid",
            response_received=True,
            response_decision_class="approved",
            project_human_escalation_status="available",
            project_human_escalation_posture="not_required",
            project_human_escalation_required=False,
            project_human_escalation_reason="escalation_not_required",
            project_architecture_risk_posture="clear",
            project_scope_risk_posture="clear",
            project_external_risk_posture="clear",
            project_budget_risk_posture="clear",
            project_repeated_failure_risk_posture="clear",
            project_manual_only_risk_posture="clear",
            project_external_manual_only_posture="clear",
        )

        self.assertEqual(payload["project_approval_notification_status"], "available")
        self.assertEqual(
            payload["project_approval_notification_ready_posture"],
            "not_required",
        )
        self.assertFalse(payload["project_approval_notification_ready"])
        self.assertEqual(
            payload["project_approval_reply_required_posture"],
            "reply_not_required",
        )
        self.assertFalse(payload["project_approval_reply_required"])
        self.assertEqual(payload["project_approval_channel_posture"], "not_required")
        self.assertEqual(
            payload["project_approval_mobile_summary_posture"],
            "not_required",
        )
        self.assertEqual(payload["project_approval_mobile_summary_compact"], "")
        self.assertFalse(payload["project_approval_notification_unavailable"])

    def test_project_approval_notification_compiler_emits_insufficient(self) -> None:
        payload = _build_project_approval_notification_state(
            approval_required=True,
            approval_email_status="insufficient_truth",
            approval_email_validity="insufficient_truth",
            approval_priority="unknown",
            approval_reason_class="unknown",
            proposed_next_direction="unknown",
            delivery_mode="unknown",
            delivery_outcome="unknown",
            approval_response_status="insufficient_truth",
            approval_response_validity="insufficient_truth",
            response_received=False,
            response_decision_class="unknown",
            project_human_escalation_status="insufficient_truth",
            project_human_escalation_posture="insufficient_truth",
            project_human_escalation_required=False,
            project_human_escalation_reason="escalation_insufficient_truth",
            project_architecture_risk_posture="insufficient_truth",
            project_scope_risk_posture="insufficient_truth",
            project_external_risk_posture="insufficient_truth",
            project_budget_risk_posture="insufficient_truth",
            project_repeated_failure_risk_posture="insufficient_truth",
            project_manual_only_risk_posture="insufficient_truth",
            project_external_manual_only_posture="insufficient_truth",
        )

        self.assertEqual(
            payload["project_approval_notification_status"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["project_approval_notification_ready_posture"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["project_approval_reply_required_posture"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["project_approval_channel_posture"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["project_approval_mobile_summary_posture"],
            "insufficient_truth",
        )
        self.assertTrue(payload["project_approval_notification_unavailable"])

    def test_project_multi_objective_compiler_emits_selected_resumable_posture(self) -> None:
        payload = _build_project_multi_objective_state(
            objective_id="obj-1",
            objective_compiler_status="available",
            objective_completion_posture="objective_active",
            project_priority_posture="active",
            project_high_risk_defer_posture="clear",
            project_run_budget_posture="available",
            project_objective_budget_posture="available",
            project_pr_retry_budget_posture="not_applicable",
            project_merge_branch_lifecycle_status="available",
            project_merge_ready_posture="not_merge_ready",
            project_branch_quarantine_candidate_posture="not_candidate",
            project_human_escalation_status="available",
            project_human_escalation_required=False,
            project_approval_notification_status="available",
            project_approval_notification_ready_posture="not_required",
            project_approval_reply_required_posture="reply_not_required",
            project_pr_queue_status="prepared",
            project_pr_queue_selected_slice_id="slice_01",
            project_pr_queue_processed_slice_ids_after=[],
            project_pr_queue_item_count=3,
            project_pr_queue_runnable_count=1,
            project_pr_queue_blocked_count=0,
            project_pr_queue_handoff_prepared=True,
        )

        self.assertEqual(payload["project_multi_objective_status"], "available")
        self.assertEqual(
            payload["project_active_objective_selection_posture"],
            "selected",
        )
        self.assertEqual(payload["project_active_objective_id"], "obj-1")
        self.assertEqual(
            payload["project_blocked_objective_deferral_posture"],
            "not_deferred",
        )
        self.assertFalse(payload["project_blocked_objective_deferred"])
        self.assertEqual(
            payload["project_resumable_queue_ordering_posture"],
            "resume_selected_first",
        )
        self.assertEqual(payload["project_resumable_queue_next_slice_id"], "slice_01")
        self.assertTrue(payload["project_resumable_queue_has_pending"])
        self.assertFalse(payload["project_multi_objective_unavailable"])

    def test_project_multi_objective_compiler_emits_deferred_posture(self) -> None:
        payload = _build_project_multi_objective_state(
            objective_id="obj-2",
            objective_compiler_status="available",
            objective_completion_posture="objective_blocked",
            project_priority_posture="deferred",
            project_high_risk_defer_posture="defer",
            project_run_budget_posture="available",
            project_objective_budget_posture="available",
            project_pr_retry_budget_posture="available",
            project_merge_branch_lifecycle_status="available",
            project_merge_ready_posture="not_merge_ready",
            project_branch_quarantine_candidate_posture="candidate",
            project_human_escalation_status="available",
            project_human_escalation_required=True,
            project_approval_notification_status="available",
            project_approval_notification_ready_posture="ready",
            project_approval_reply_required_posture="reply_required",
            project_pr_queue_status="prepared",
            project_pr_queue_selected_slice_id="slice_02",
            project_pr_queue_processed_slice_ids_after=["slice_01"],
            project_pr_queue_item_count=4,
            project_pr_queue_runnable_count=1,
            project_pr_queue_blocked_count=2,
            project_pr_queue_handoff_prepared=False,
        )

        self.assertEqual(payload["project_multi_objective_status"], "available")
        self.assertEqual(
            payload["project_active_objective_selection_posture"],
            "deferred",
        )
        self.assertEqual(
            payload["project_blocked_objective_deferral_posture"],
            "deferred",
        )
        self.assertTrue(payload["project_blocked_objective_deferred"])
        self.assertEqual(
            payload["project_resumable_queue_ordering_posture"],
            "deferred_non_runnable",
        )
        self.assertFalse(payload["project_resumable_queue_has_pending"])
        self.assertFalse(payload["project_multi_objective_unavailable"])

    def test_project_multi_objective_compiler_emits_insufficient(self) -> None:
        payload = _build_project_multi_objective_state(
            objective_id="",
            objective_compiler_status="insufficient_truth",
            objective_completion_posture="objective_insufficient_truth",
            project_priority_posture="insufficient_truth",
            project_high_risk_defer_posture="insufficient_truth",
            project_run_budget_posture="insufficient_truth",
            project_objective_budget_posture="insufficient_truth",
            project_pr_retry_budget_posture="insufficient_truth",
            project_merge_branch_lifecycle_status="insufficient_truth",
            project_merge_ready_posture="insufficient_truth",
            project_branch_quarantine_candidate_posture="insufficient_truth",
            project_human_escalation_status="insufficient_truth",
            project_human_escalation_required=False,
            project_approval_notification_status="insufficient_truth",
            project_approval_notification_ready_posture="insufficient_truth",
            project_approval_reply_required_posture="insufficient_truth",
            project_pr_queue_status="insufficient_truth",
            project_pr_queue_selected_slice_id="",
            project_pr_queue_processed_slice_ids_after=[],
            project_pr_queue_item_count=0,
            project_pr_queue_runnable_count=0,
            project_pr_queue_blocked_count=0,
            project_pr_queue_handoff_prepared=False,
        )

        self.assertEqual(payload["project_multi_objective_status"], "insufficient_truth")
        self.assertEqual(
            payload["project_active_objective_selection_posture"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["project_blocked_objective_deferral_posture"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["project_resumable_queue_ordering_posture"],
            "insufficient_truth",
        )
        self.assertFalse(payload["project_resumable_queue_has_pending"])
        self.assertTrue(payload["project_multi_objective_unavailable"])

    def test_runner_preserves_approval_gate_when_skip_is_not_allowed(self) -> None:
        base_email_payload = {
            "approval_email_status": "required",
            "approval_email_validity": "valid",
            "approval_required": True,
            "approval_priority": "low",
            "approval_reason_class": "restart_hold",
            "proposed_next_direction": "replan_preparation",
            "proposed_target_lane": "replan_preparation",
            "proposed_restart_mode": "approval_required_then_restart",
            "proposed_action_class": "review_and_replan",
        }
        response_payload = {
            "approval_response_status": "awaiting_response",
            "approval_response_validity": "valid",
            "response_received": False,
            "response_command_normalized": "",
            "response_supported": False,
            "response_decision_class": "unknown",
        }
        approved_restart_payload = {
            "approved_restart_status": "not_ready",
            "approved_restart_validity": "valid",
            "restart_decision": "unknown",
            "restart_allowed": False,
            "restart_blocked": True,
            "restart_held": False,
            "restart_requires_manual_followup": False,
            "approved_next_direction": "unknown",
            "approved_target_lane": "unknown",
            "approved_action_class": "unknown",
            "response_decision_class": "unknown",
            "response_command_normalized": "",
        }
        fleet_safety_payload = {
            "fleet_safety_status": "allow",
            "fleet_safety_validity": "valid",
            "fleet_safety_decision": "proceed",
            "fleet_restart_decision": "restart_allowed",
            "fleet_manual_review_required": False,
            "bucket_severity": "low",
        }
        blocked_cases = (
            (
                "cooldown_active",
                base_email_payload,
                {
                    "approval_safety_status": "cooldown_active",
                    "approval_safety_validity": "valid",
                    "approval_safety_decision": "defer_until_cooldown_expires",
                    "approval_pending_duplicate": False,
                    "approval_cooldown_active": True,
                    "approval_loop_suspected": False,
                    "approval_delivery_blocked_by_safety": False,
                    "approval_delivery_deferred_by_safety": True,
                    "approval_delivery_allowed_by_safety": False,
                },
                "skip_safety_cooldown_active",
            ),
            (
                "insufficient_truth",
                {
                    **base_email_payload,
                    "approval_email_validity": "insufficient_truth",
                    "proposed_next_direction": "unknown",
                    "proposed_action_class": "unknown",
                },
                {
                    "approval_safety_status": "safe_to_deliver",
                    "approval_safety_validity": "valid",
                    "approval_safety_decision": "allow_delivery",
                    "approval_pending_duplicate": False,
                    "approval_cooldown_active": False,
                    "approval_loop_suspected": False,
                    "approval_delivery_blocked_by_safety": False,
                    "approval_delivery_deferred_by_safety": False,
                    "approval_delivery_allowed_by_safety": True,
                },
                "skip_invalid_or_insufficient_truth",
            ),
            (
                "unsupported_direction",
                {
                    **base_email_payload,
                    "proposed_next_direction": "stop_no_restart",
                    "proposed_action_class": "stop_only",
                },
                {
                    "approval_safety_status": "safe_to_deliver",
                    "approval_safety_validity": "valid",
                    "approval_safety_decision": "allow_delivery",
                    "approval_pending_duplicate": False,
                    "approval_cooldown_active": False,
                    "approval_loop_suspected": False,
                    "approval_delivery_blocked_by_safety": False,
                    "approval_delivery_deferred_by_safety": False,
                    "approval_delivery_allowed_by_safety": True,
                },
                "skip_unsupported_direction",
            ),
        )

        for case_id, email_payload, safety_payload, expected_skip_reason in blocked_cases:
            with self.subTest(case=case_id):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    root = Path(tmp_dir)
                    artifacts_dir = self._write_planning_artifacts(root)
                    out_dir = root / "artifacts" / "executions"
                    transport = _RecordingDryRunTransport()
                    runner = PlannedExecutionRunner(
                        adapter=CodexExecutorAdapter(transport=transport)
                    )
                    with (
                        patch(
                            "automation.orchestration.planned_execution_runner.build_approval_email_delivery_contract_surface",
                            return_value=email_payload,
                        ),
                        patch(
                            "automation.orchestration.planned_execution_runner.build_approval_response_contract_surface",
                            return_value=response_payload,
                        ),
                        patch(
                            "automation.orchestration.planned_execution_runner.build_approved_restart_contract_surface",
                            return_value=approved_restart_payload,
                        ),
                        patch(
                            "automation.orchestration.planned_execution_runner.build_approval_safety_contract_surface",
                            return_value=safety_payload,
                        ),
                        patch(
                            "automation.orchestration.planned_execution_runner.build_fleet_safety_control_contract_surface",
                            return_value=fleet_safety_payload,
                        ),
                    ):
                        manifest = runner.run(
                            artifacts_input_dir=artifacts_dir,
                            output_dir=out_dir,
                            dry_run=True,
                            stop_on_failure=True,
                        )
                    run_root = out_dir / manifest["job_id"]
                    execution_payload = json.loads(
                        (run_root / "approved_restart_execution_contract.json").read_text(
                            encoding="utf-8"
                        )
                    )

                self.assertEqual(
                    execution_payload["automatic_restart_execution_status"],
                    "not_executed",
                )
                self.assertFalse(execution_payload["automatic_restart_executed"])
                self.assertFalse(execution_payload["automatic_restart_attempted"])
                self.assertEqual(execution_payload["automatic_restart_count"], 0)
                self.assertFalse(execution_payload["approval_skip_allowed"])
                self.assertFalse(execution_payload["approval_skip_applied"])
                self.assertEqual(
                    execution_payload["approval_skip_gate_decision"],
                    "require_human_approval",
                )
                self.assertTrue(execution_payload["approval_skip_human_gate_preserved"])
                self.assertEqual(
                    execution_payload["approval_skip_reason"],
                    expected_skip_reason,
                )
                self.assertEqual(len(transport.launch_order), 3)

    def test_runner_continuation_budget_exhausts_after_repeated_auto_continuations(self) -> None:
        approval_email_payload = {
            "approval_email_status": "required",
            "approval_email_validity": "valid",
            "approval_required": True,
            "approval_priority": "low",
            "approval_reason_class": "restart_hold",
            "proposed_next_direction": "replan_preparation",
            "proposed_target_lane": "replan_preparation",
            "proposed_restart_mode": "approval_required_then_restart",
            "proposed_action_class": "review_and_replan",
        }
        response_payload = {
            "approval_response_status": "awaiting_response",
            "approval_response_validity": "valid",
            "response_received": False,
            "response_command_normalized": "",
            "response_supported": False,
            "response_decision_class": "unknown",
        }
        approved_restart_payload = {
            "approved_restart_status": "not_ready",
            "approved_restart_validity": "valid",
            "restart_decision": "unknown",
            "restart_allowed": False,
            "restart_blocked": True,
            "restart_held": False,
            "restart_requires_manual_followup": False,
            "approved_next_direction": "unknown",
            "approved_target_lane": "unknown",
            "approved_action_class": "unknown",
            "response_decision_class": "unknown",
            "response_command_normalized": "",
        }
        approval_safety_payload = {
            "approval_safety_status": "safe_to_deliver",
            "approval_safety_validity": "valid",
            "approval_safety_confidence": "high",
            "approval_safety_decision": "allow_delivery",
            "approval_pending_duplicate": False,
            "approval_cooldown_active": False,
            "approval_loop_suspected": False,
            "approval_delivery_blocked_by_safety": False,
            "approval_delivery_deferred_by_safety": False,
            "approval_delivery_allowed_by_safety": True,
        }
        fleet_safety_payload = {
            "fleet_safety_status": "allow",
            "fleet_safety_validity": "valid",
            "fleet_safety_decision": "proceed",
            "fleet_restart_decision": "restart_allowed",
            "fleet_manual_review_required": False,
            "bucket_severity": "low",
        }

        payloads: list[dict[str, object]] = []
        launch_counts: list[int] = []
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"
            status_map = {
                "project-planned-exec-pr-01__approved_restart_once": "completed",
            }
            for _ in range(3):
                transport = _RecordingDryRunTransport(status_by_pr_id=status_map)
                runner = PlannedExecutionRunner(
                    adapter=CodexExecutorAdapter(transport=transport)
                )
                with (
                    patch(
                        "automation.orchestration.planned_execution_runner.build_approval_email_delivery_contract_surface",
                        return_value=approval_email_payload,
                    ),
                    patch(
                        "automation.orchestration.planned_execution_runner.build_approval_response_contract_surface",
                        return_value=response_payload,
                    ),
                    patch(
                        "automation.orchestration.planned_execution_runner.build_approved_restart_contract_surface",
                        return_value=approved_restart_payload,
                    ),
                    patch(
                        "automation.orchestration.planned_execution_runner.build_approval_safety_contract_surface",
                        return_value=approval_safety_payload,
                    ),
                    patch(
                        "automation.orchestration.planned_execution_runner.build_fleet_safety_control_contract_surface",
                        return_value=fleet_safety_payload,
                    ),
                ):
                    manifest = runner.run(
                        artifacts_input_dir=artifacts_dir,
                        output_dir=out_dir,
                        dry_run=True,
                        stop_on_failure=True,
                    )
                run_root = out_dir / manifest["job_id"]
                payload = json.loads(
                    (run_root / "approved_restart_execution_contract.json").read_text(
                        encoding="utf-8"
                    )
                )
                payloads.append(payload)
                launch_counts.append(len(transport.launch_order))

        first, second, third = payloads
        self.assertEqual(first["automatic_restart_execution_status"], "executed")
        self.assertEqual(second["automatic_restart_execution_status"], "executed")
        self.assertEqual(third["automatic_restart_execution_status"], "not_executed")
        self.assertEqual(first["automatic_continuation_run_count"], 1)
        self.assertEqual(second["automatic_continuation_run_count"], 2)
        self.assertEqual(third["automatic_continuation_run_count"], 2)
        self.assertEqual(first["continuation_budget_status"], "available")
        self.assertEqual(second["continuation_budget_status"], "available")
        self.assertEqual(third["continuation_budget_status"], "exhausted")
        self.assertEqual(
            third["automatic_restart_execution_reason"],
            "continuation_budget_exhausted",
        )
        self.assertEqual(third["continuation_budget_decision"], "deny_budget_exhausted")
        self.assertTrue(third["continuation_budget_exhausted"])
        self.assertEqual(third["project_autonomy_budget_status"], "available")
        self.assertEqual(third["project_priority_posture"], "lower_priority")
        self.assertEqual(third["project_run_budget_posture"], "exhausted")
        self.assertTrue(third["project_run_budget_exhausted"])
        self.assertEqual(third["project_pr_retry_budget_posture"], "not_applicable")
        self.assertEqual(third["project_quality_gate_status"], "available")
        self.assertEqual(third["project_quality_gate_posture"], "retry_needed")
        self.assertTrue(third["project_quality_gate_retry_needed"])
        self.assertFalse(third["project_quality_gate_merge_ready"])
        self.assertEqual(third["project_merge_branch_lifecycle_status"], "available")
        self.assertEqual(third["project_merge_ready_posture"], "not_merge_ready")
        self.assertFalse(third["project_merge_ready"])
        self.assertEqual(
            third["project_branch_cleanup_candidate_posture"],
            "not_candidate",
        )
        self.assertEqual(
            third["project_branch_quarantine_candidate_posture"],
            "not_candidate",
        )
        self.assertTrue(third["approval_skip_human_gate_preserved"])
        self.assertFalse(third["approval_skip_applied"])
        self.assertEqual(launch_counts, [4, 4, 3])

    def test_runner_continuation_budget_precedence_is_deterministic(self) -> None:
        approval_email_payload = {
            "approval_email_status": "required",
            "approval_email_validity": "valid",
            "approval_required": True,
            "approval_priority": "low",
            "approval_reason_class": "restart_hold",
            "proposed_next_direction": "replan_preparation",
            "proposed_target_lane": "replan_preparation",
            "proposed_restart_mode": "approval_required_then_restart",
            "proposed_action_class": "review_and_replan",
        }
        response_payload = {
            "approval_response_status": "awaiting_response",
            "approval_response_validity": "valid",
            "response_received": False,
            "response_command_normalized": "",
            "response_supported": False,
            "response_decision_class": "unknown",
        }
        approved_restart_payload = {
            "approved_restart_status": "not_ready",
            "approved_restart_validity": "valid",
            "restart_decision": "unknown",
            "restart_allowed": False,
            "restart_blocked": True,
            "restart_held": False,
            "restart_requires_manual_followup": False,
            "approved_next_direction": "unknown",
            "approved_target_lane": "unknown",
            "approved_action_class": "unknown",
            "response_decision_class": "unknown",
            "response_command_normalized": "",
        }
        approval_safety_payload = {
            "approval_safety_status": "safe_to_deliver",
            "approval_safety_validity": "valid",
            "approval_safety_confidence": "high",
            "approval_safety_decision": "allow_delivery",
            "approval_pending_duplicate": False,
            "approval_cooldown_active": False,
            "approval_loop_suspected": False,
            "approval_delivery_blocked_by_safety": False,
            "approval_delivery_deferred_by_safety": False,
            "approval_delivery_allowed_by_safety": True,
        }
        fleet_safety_payload = {
            "fleet_safety_status": "allow",
            "fleet_safety_validity": "valid",
            "fleet_safety_decision": "proceed",
            "fleet_restart_decision": "restart_allowed",
            "fleet_manual_review_required": False,
            "bucket_severity": "low",
        }
        cases = (
            (
                "lane_precedence",
                {"run": 1, "objective": 1, "lane": 2},
                "budget_lane_exhausted",
            ),
            (
                "objective_precedence",
                {"run": 1, "objective": 2, "lane": 1},
                "budget_objective_exhausted",
            ),
            (
                "run_precedence",
                {"run": 2, "objective": 1, "lane": 1},
                "budget_run_exhausted",
            ),
        )

        for case_id, seeded_counts, expected_budget_reason in cases:
            with self.subTest(case=case_id):
                with tempfile.TemporaryDirectory() as tmp_dir:
                    root = Path(tmp_dir)
                    artifacts_dir = self._write_planning_artifacts(root)
                    out_dir = root / "artifacts" / "executions"
                    status_map = {
                        "project-planned-exec-pr-01__approved_restart_once": "completed",
                    }
                    transport = _RecordingDryRunTransport(status_by_pr_id=status_map)
                    runner = PlannedExecutionRunner(
                        adapter=CodexExecutorAdapter(transport=transport)
                    )
                    with (
                        patch(
                            "automation.orchestration.planned_execution_runner.build_approval_email_delivery_contract_surface",
                            return_value=approval_email_payload,
                        ),
                        patch(
                            "automation.orchestration.planned_execution_runner.build_approval_response_contract_surface",
                            return_value=response_payload,
                        ),
                        patch(
                            "automation.orchestration.planned_execution_runner.build_approved_restart_contract_surface",
                            return_value=approved_restart_payload,
                        ),
                        patch(
                            "automation.orchestration.planned_execution_runner.build_approval_safety_contract_surface",
                            return_value=approval_safety_payload,
                        ),
                        patch(
                            "automation.orchestration.planned_execution_runner.build_fleet_safety_control_contract_surface",
                            return_value=fleet_safety_payload,
                        ),
                    ):
                        manifest = runner.run(
                            artifacts_input_dir=artifacts_dir,
                            output_dir=out_dir,
                            dry_run=True,
                            stop_on_failure=True,
                        )
                    run_root = out_dir / manifest["job_id"]
                    baseline_payload = json.loads(
                        (run_root / "approved_restart_execution_contract.json").read_text(
                            encoding="utf-8"
                        )
                    )
                    seeded_payload = {
                        "automatic_continuation_run_count": seeded_counts["run"],
                        "automatic_continuation_objective_count": seeded_counts["objective"],
                        "automatic_continuation_lane_count": seeded_counts["lane"],
                        "automatic_continuation_objective_key": baseline_payload[
                            "automatic_continuation_objective_key"
                        ],
                        "automatic_continuation_lane_key": baseline_payload[
                            "automatic_continuation_lane_key"
                        ],
                    }
                    (run_root / "approved_restart_execution_contract.json").write_text(
                        json.dumps(seeded_payload, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )

                    transport_second = _RecordingDryRunTransport(status_by_pr_id=status_map)
                    runner_second = PlannedExecutionRunner(
                        adapter=CodexExecutorAdapter(transport=transport_second)
                    )
                    with (
                        patch(
                            "automation.orchestration.planned_execution_runner.build_approval_email_delivery_contract_surface",
                            return_value=approval_email_payload,
                        ),
                        patch(
                            "automation.orchestration.planned_execution_runner.build_approval_response_contract_surface",
                            return_value=response_payload,
                        ),
                        patch(
                            "automation.orchestration.planned_execution_runner.build_approved_restart_contract_surface",
                            return_value=approved_restart_payload,
                        ),
                        patch(
                            "automation.orchestration.planned_execution_runner.build_approval_safety_contract_surface",
                            return_value=approval_safety_payload,
                        ),
                        patch(
                            "automation.orchestration.planned_execution_runner.build_fleet_safety_control_contract_surface",
                            return_value=fleet_safety_payload,
                        ),
                    ):
                        manifest_second = runner_second.run(
                            artifacts_input_dir=artifacts_dir,
                            output_dir=out_dir,
                            dry_run=True,
                            stop_on_failure=True,
                        )
                    run_root_second = out_dir / manifest_second["job_id"]
                    payload = json.loads(
                        (run_root_second / "approved_restart_execution_contract.json").read_text(
                            encoding="utf-8"
                        )
                    )

                self.assertEqual(
                    payload["automatic_restart_execution_status"],
                    "not_executed",
                )
                self.assertEqual(
                    payload["automatic_restart_execution_reason"],
                    "continuation_budget_exhausted",
                )
                self.assertEqual(payload["continuation_budget_status"], "exhausted")
                self.assertEqual(payload["continuation_budget_reason"], expected_budget_reason)
                self.assertEqual(payload["continuation_budget_branch_status"], "available")
                self.assertFalse(payload["continuation_budget_branch_exhausted"])
                self.assertEqual(len(transport_second.launch_order), 3)

    def test_runner_continuation_branch_ceiling_is_enforced(self) -> None:
        response_payload = {
            "approval_response_status": "awaiting_response",
            "approval_response_validity": "valid",
            "response_received": False,
            "response_command_normalized": "",
            "response_supported": False,
            "response_decision_class": "unknown",
        }
        approved_restart_payload = {
            "approved_restart_status": "not_ready",
            "approved_restart_validity": "valid",
            "restart_decision": "unknown",
            "restart_allowed": False,
            "restart_blocked": True,
            "restart_held": False,
            "restart_requires_manual_followup": False,
            "approved_next_direction": "unknown",
            "approved_target_lane": "unknown",
            "approved_action_class": "unknown",
            "response_decision_class": "unknown",
            "response_command_normalized": "",
        }
        approval_safety_payload = {
            "approval_safety_status": "safe_to_deliver",
            "approval_safety_validity": "valid",
            "approval_safety_confidence": "high",
            "approval_safety_decision": "allow_delivery",
            "approval_pending_duplicate": False,
            "approval_cooldown_active": False,
            "approval_loop_suspected": False,
            "approval_delivery_blocked_by_safety": False,
            "approval_delivery_deferred_by_safety": False,
            "approval_delivery_allowed_by_safety": True,
        }
        fleet_safety_payload = {
            "fleet_safety_status": "allow",
            "fleet_safety_validity": "valid",
            "fleet_safety_decision": "proceed",
            "fleet_restart_decision": "restart_allowed",
            "fleet_manual_review_required": False,
            "bucket_severity": "low",
        }
        cases = (
            ("retry", "same_lane_retry", "review_and_restart", "retry"),
            ("replan", "replan_preparation", "review_and_replan", "replan"),
            ("truth_gather", "truth_gathering", "review_and_recollect", "truth_gather"),
        )

        for case_id, direction, action_class, expected_branch in cases:
            with self.subTest(case=case_id):
                approval_email_payload = {
                    "approval_email_status": "required",
                    "approval_email_validity": "valid",
                    "approval_required": True,
                    "approval_priority": "low",
                    "approval_reason_class": "restart_hold",
                    "proposed_next_direction": direction,
                    "proposed_target_lane": direction,
                    "proposed_restart_mode": "approval_required_then_restart",
                    "proposed_action_class": action_class,
                }
                failure_bucketing_payload = {
                    "failure_bucketing_status": "classified",
                    "failure_bucketing_validity": "valid",
                    "primary_failure_bucket": "unknown",
                }
                if expected_branch == "truth_gather":
                    failure_bucketing_payload = {
                        "failure_bucketing_status": "insufficient_truth",
                        "failure_bucketing_validity": "insufficient_truth",
                        "primary_failure_bucket": "truth_missing",
                    }
                with tempfile.TemporaryDirectory() as tmp_dir:
                    root = Path(tmp_dir)
                    artifacts_dir = self._write_planning_artifacts(root)
                    out_dir = root / "artifacts" / "executions"
                    status_map = {
                        "project-planned-exec-pr-01__approved_restart_once": "completed",
                    }
                    transport = _RecordingDryRunTransport(status_by_pr_id=status_map)
                    runner = PlannedExecutionRunner(
                        adapter=CodexExecutorAdapter(transport=transport)
                    )
                    with (
                        patch(
                            "automation.orchestration.planned_execution_runner.build_approval_email_delivery_contract_surface",
                            return_value=approval_email_payload,
                        ),
                        patch(
                            "automation.orchestration.planned_execution_runner.build_approval_response_contract_surface",
                            return_value=response_payload,
                        ),
                        patch(
                            "automation.orchestration.planned_execution_runner.build_approved_restart_contract_surface",
                            return_value=approved_restart_payload,
                        ),
                        patch(
                            "automation.orchestration.planned_execution_runner.build_approval_safety_contract_surface",
                            return_value=approval_safety_payload,
                        ),
                        patch(
                            "automation.orchestration.planned_execution_runner.build_fleet_safety_control_contract_surface",
                            return_value=fleet_safety_payload,
                        ),
                        patch(
                            "automation.orchestration.planned_execution_runner.build_failure_bucketing_hardening_contract_surface",
                            return_value=failure_bucketing_payload,
                        ),
                    ):
                        manifest = runner.run(
                            artifacts_input_dir=artifacts_dir,
                            output_dir=out_dir,
                            dry_run=True,
                            stop_on_failure=True,
                        )
                    run_root = out_dir / manifest["job_id"]
                    baseline_payload = json.loads(
                        (run_root / "approved_restart_execution_contract.json").read_text(
                            encoding="utf-8"
                        )
                    )
                    self.assertEqual(
                        baseline_payload["automatic_restart_execution_status"],
                        "executed",
                    )
                    self.assertEqual(
                        baseline_payload["continuation_budget_branch_type"],
                        expected_branch,
                    )
                    self.assertEqual(
                        baseline_payload["continuation_budget_branch_status"],
                        "available",
                    )
                    self.assertEqual(
                        baseline_payload["continuation_budget_branch_reason"],
                        "branch_budget_available",
                    )
                    self.assertEqual(
                        baseline_payload["automatic_continuation_branch_count"],
                        1,
                    )

                    seeded_payload = {
                        "automatic_continuation_run_count": 0,
                        "automatic_continuation_objective_count": 0,
                        "automatic_continuation_lane_count": 0,
                        "automatic_continuation_objective_key": baseline_payload[
                            "automatic_continuation_objective_key"
                        ],
                        "automatic_continuation_lane_key": baseline_payload[
                            "automatic_continuation_lane_key"
                        ],
                        "automatic_continuation_retry_count": (
                            2 if expected_branch == "retry" else 0
                        ),
                        "automatic_continuation_replan_count": (
                            2 if expected_branch == "replan" else 0
                        ),
                        "automatic_continuation_truth_gather_count": (
                            2 if expected_branch == "truth_gather" else 0
                        ),
                    }
                    (run_root / "approved_restart_execution_contract.json").write_text(
                        json.dumps(seeded_payload, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )

                    transport_second = _RecordingDryRunTransport(status_by_pr_id=status_map)
                    runner_second = PlannedExecutionRunner(
                        adapter=CodexExecutorAdapter(transport=transport_second)
                    )
                    with (
                        patch(
                            "automation.orchestration.planned_execution_runner.build_approval_email_delivery_contract_surface",
                            return_value=approval_email_payload,
                        ),
                        patch(
                            "automation.orchestration.planned_execution_runner.build_approval_response_contract_surface",
                            return_value=response_payload,
                        ),
                        patch(
                            "automation.orchestration.planned_execution_runner.build_approved_restart_contract_surface",
                            return_value=approved_restart_payload,
                        ),
                        patch(
                            "automation.orchestration.planned_execution_runner.build_approval_safety_contract_surface",
                            return_value=approval_safety_payload,
                        ),
                        patch(
                            "automation.orchestration.planned_execution_runner.build_fleet_safety_control_contract_surface",
                            return_value=fleet_safety_payload,
                        ),
                        patch(
                            "automation.orchestration.planned_execution_runner.build_failure_bucketing_hardening_contract_surface",
                            return_value=failure_bucketing_payload,
                        ),
                    ):
                        manifest_second = runner_second.run(
                            artifacts_input_dir=artifacts_dir,
                            output_dir=out_dir,
                            dry_run=True,
                            stop_on_failure=True,
                        )
                    run_root_second = out_dir / manifest_second["job_id"]
                    payload = json.loads(
                        (run_root_second / "approved_restart_execution_contract.json").read_text(
                            encoding="utf-8"
                        )
                    )

                self.assertEqual(
                    payload["automatic_restart_execution_status"],
                    "not_executed",
                )
                self.assertEqual(
                    payload["automatic_restart_execution_reason"],
                    "continuation_budget_exhausted",
                )
                self.assertEqual(payload["continuation_budget_status"], "exhausted")
                self.assertEqual(payload["continuation_budget_reason"], "budget_branch_exhausted")
                self.assertEqual(payload["continuation_budget_branch_type"], expected_branch)
                self.assertEqual(payload["continuation_budget_branch_status"], "exhausted")
                self.assertEqual(
                    payload["continuation_budget_branch_decision"],
                    "deny_branch_ceiling_exhausted",
                )
                self.assertEqual(
                    payload["continuation_budget_branch_reason"],
                    "branch_budget_exhausted",
                )
                self.assertTrue(payload["continuation_budget_branch_exhausted"])
                self.assertFalse(payload["continuation_budget_run_exhausted"])
                self.assertFalse(payload["continuation_budget_objective_exhausted"])
                self.assertFalse(payload["continuation_budget_lane_exhausted"])
                self.assertTrue(payload["approval_skip_human_gate_preserved"])
                self.assertFalse(payload["approval_skip_applied"])
                self.assertEqual(payload["automatic_continuation_branch_count"], 2)
                self.assertEqual(len(transport_second.launch_order), 3)

    def test_runner_denies_repeated_continuation_on_no_progress(self) -> None:
        approval_email_payload = {
            "approval_email_status": "required",
            "approval_email_validity": "valid",
            "approval_required": True,
            "approval_priority": "low",
            "approval_reason_class": "restart_hold",
            "proposed_next_direction": "replan_preparation",
            "proposed_target_lane": "replan_preparation",
            "proposed_restart_mode": "approval_required_then_restart",
            "proposed_action_class": "review_and_replan",
        }
        response_payload = {
            "approval_response_status": "awaiting_response",
            "approval_response_validity": "valid",
            "response_received": False,
            "response_command_normalized": "",
            "response_supported": False,
            "response_decision_class": "unknown",
        }
        approved_restart_payload = {
            "approved_restart_status": "not_ready",
            "approved_restart_validity": "valid",
            "restart_decision": "unknown",
            "restart_allowed": False,
            "restart_blocked": True,
            "restart_held": False,
            "restart_requires_manual_followup": False,
            "approved_next_direction": "unknown",
            "approved_target_lane": "unknown",
            "approved_action_class": "unknown",
            "response_decision_class": "unknown",
            "response_command_normalized": "",
        }
        approval_safety_payload = {
            "approval_safety_status": "safe_to_deliver",
            "approval_safety_validity": "valid",
            "approval_safety_confidence": "high",
            "approval_safety_decision": "allow_delivery",
            "approval_pending_duplicate": False,
            "approval_cooldown_active": False,
            "approval_loop_suspected": False,
            "approval_delivery_blocked_by_safety": False,
            "approval_delivery_deferred_by_safety": False,
            "approval_delivery_allowed_by_safety": True,
        }
        fleet_safety_payload = {
            "fleet_safety_status": "allow",
            "fleet_safety_validity": "valid",
            "fleet_safety_decision": "proceed",
            "fleet_restart_decision": "restart_allowed",
            "fleet_manual_review_required": False,
            "bucket_severity": "low",
        }
        loop_hardening_payload = {
            "loop_hardening_status": "stop_required",
            "loop_hardening_validity": "valid",
            "no_progress_status": "confirmed",
            "no_progress_detected": True,
            "no_progress_stop_required": True,
        }
        failure_bucketing_payload = {
            "failure_bucketing_status": "classified",
            "failure_bucketing_validity": "valid",
            "primary_failure_bucket": "objective_gap",
        }

        payloads: list[dict[str, object]] = []
        launch_counts: list[int] = []
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"
            status_map = {
                "project-planned-exec-pr-01__approved_restart_once": "completed",
            }
            for _ in range(2):
                transport = _RecordingDryRunTransport(status_by_pr_id=status_map)
                runner = PlannedExecutionRunner(
                    adapter=CodexExecutorAdapter(transport=transport)
                )
                with (
                    patch(
                        "automation.orchestration.planned_execution_runner.build_approval_email_delivery_contract_surface",
                        return_value=approval_email_payload,
                    ),
                    patch(
                        "automation.orchestration.planned_execution_runner.build_approval_response_contract_surface",
                        return_value=response_payload,
                    ),
                    patch(
                        "automation.orchestration.planned_execution_runner.build_approved_restart_contract_surface",
                        return_value=approved_restart_payload,
                    ),
                    patch(
                        "automation.orchestration.planned_execution_runner.build_approval_safety_contract_surface",
                        return_value=approval_safety_payload,
                    ),
                    patch(
                        "automation.orchestration.planned_execution_runner.build_fleet_safety_control_contract_surface",
                        return_value=fleet_safety_payload,
                    ),
                    patch(
                        "automation.orchestration.planned_execution_runner.build_loop_hardening_contract_surface",
                        return_value=loop_hardening_payload,
                    ),
                    patch(
                        "automation.orchestration.planned_execution_runner.build_failure_bucketing_hardening_contract_surface",
                        return_value=failure_bucketing_payload,
                    ),
                ):
                    manifest = runner.run(
                        artifacts_input_dir=artifacts_dir,
                        output_dir=out_dir,
                        dry_run=True,
                        stop_on_failure=True,
                    )
                run_root = out_dir / manifest["job_id"]
                payload = json.loads(
                    (run_root / "approved_restart_execution_contract.json").read_text(
                        encoding="utf-8"
                    )
                )
                payloads.append(payload)
                launch_counts.append(len(transport.launch_order))

        first, second = payloads
        self.assertEqual(first["automatic_restart_execution_status"], "executed")
        self.assertEqual(second["automatic_restart_execution_status"], "not_executed")
        self.assertEqual(
            second["automatic_restart_execution_reason"],
            "continuation_no_progress_stop",
        )
        self.assertEqual(second["continuation_budget_status"], "available")
        self.assertEqual(second["continuation_budget_branch_status"], "available")
        self.assertTrue(second["continuation_no_progress_repeated"])
        self.assertTrue(second["continuation_no_progress_signal_detected"])
        self.assertTrue(second["continuation_no_progress_stop_required"])
        self.assertFalse(second["continuation_failure_bucket_denied"])
        self.assertTrue(second["approval_skip_human_gate_preserved"])
        self.assertFalse(second["approval_skip_applied"])
        self.assertEqual(launch_counts, [4, 3])

    def test_runner_denies_continuation_for_unsafe_failure_bucket(self) -> None:
        approval_email_payload = {
            "approval_email_status": "required",
            "approval_email_validity": "valid",
            "approval_required": True,
            "approval_priority": "low",
            "approval_reason_class": "restart_hold",
            "proposed_next_direction": "truth_gathering",
            "proposed_target_lane": "truth_gathering",
            "proposed_restart_mode": "approval_required_then_restart",
            "proposed_action_class": "review_and_recollect",
        }
        response_payload = {
            "approval_response_status": "awaiting_response",
            "approval_response_validity": "valid",
            "response_received": False,
            "response_command_normalized": "",
            "response_supported": False,
            "response_decision_class": "unknown",
        }
        approved_restart_payload = {
            "approved_restart_status": "not_ready",
            "approved_restart_validity": "valid",
            "restart_decision": "unknown",
            "restart_allowed": False,
            "restart_blocked": True,
            "restart_held": False,
            "restart_requires_manual_followup": False,
            "approved_next_direction": "unknown",
            "approved_target_lane": "unknown",
            "approved_action_class": "unknown",
            "response_decision_class": "unknown",
            "response_command_normalized": "",
        }
        approval_safety_payload = {
            "approval_safety_status": "safe_to_deliver",
            "approval_safety_validity": "valid",
            "approval_safety_confidence": "high",
            "approval_safety_decision": "allow_delivery",
            "approval_pending_duplicate": False,
            "approval_cooldown_active": False,
            "approval_loop_suspected": False,
            "approval_delivery_blocked_by_safety": False,
            "approval_delivery_deferred_by_safety": False,
            "approval_delivery_allowed_by_safety": True,
        }
        fleet_safety_payload = {
            "fleet_safety_status": "allow",
            "fleet_safety_validity": "valid",
            "fleet_safety_decision": "proceed",
            "fleet_restart_decision": "restart_allowed",
            "fleet_manual_review_required": False,
            "bucket_severity": "low",
        }
        loop_hardening_payload = {
            "loop_hardening_status": "stable",
            "loop_hardening_validity": "valid",
            "no_progress_status": "none",
            "no_progress_detected": False,
            "no_progress_stop_required": False,
        }
        failure_bucketing_payload = {
            "failure_bucketing_status": "classified",
            "failure_bucketing_validity": "valid",
            "primary_failure_bucket": "manual_only",
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"
            transport = _RecordingDryRunTransport()
            runner = PlannedExecutionRunner(
                adapter=CodexExecutorAdapter(transport=transport)
            )
            with (
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_email_delivery_contract_surface",
                    return_value=approval_email_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_response_contract_surface",
                    return_value=response_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approved_restart_contract_surface",
                    return_value=approved_restart_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_safety_contract_surface",
                    return_value=approval_safety_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_fleet_safety_control_contract_surface",
                    return_value=fleet_safety_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_loop_hardening_contract_surface",
                    return_value=loop_hardening_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_failure_bucketing_hardening_contract_surface",
                    return_value=failure_bucketing_payload,
                ),
            ):
                manifest = runner.run(
                    artifacts_input_dir=artifacts_dir,
                    output_dir=out_dir,
                    dry_run=True,
                    stop_on_failure=True,
                )
            run_root = out_dir / manifest["job_id"]
            payload = json.loads(
                (run_root / "approved_restart_execution_contract.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(payload["automatic_restart_execution_status"], "not_executed")
        self.assertEqual(
            payload["automatic_restart_execution_reason"],
            "failure_bucket_continuation_denied",
        )
        self.assertEqual(payload["continuation_budget_status"], "available")
        self.assertEqual(payload["continuation_budget_branch_status"], "available")
        self.assertFalse(payload["continuation_no_progress_stop_required"])
        self.assertTrue(payload["continuation_failure_bucket_unsafe"])
        self.assertTrue(payload["continuation_failure_bucket_denied"])
        self.assertEqual(payload["continuation_failure_bucket"], "manual_only")
        self.assertEqual(
            payload["continuation_repair_playbook_selection_status"],
            "not_selected",
        )
        self.assertFalse(payload["continuation_repair_playbook_selected"])
        self.assertFalse(payload["continuation_repair_playbook_supported_bucket"])
        self.assertEqual(payload["continuation_repair_playbook_class"], "no_plan")
        self.assertEqual(payload["continuation_repair_playbook_candidate_action"], "no_action")
        self.assertEqual(
            payload["continuation_repair_playbook_reason"],
            "playbook_bucket_unsupported",
        )
        self.assertEqual(
            payload["continuation_next_step_selection_status"],
            "not_selected",
        )
        self.assertFalse(payload["continuation_next_step_selected"])
        self.assertEqual(payload["continuation_next_step_target"], "none")
        self.assertEqual(payload["supported_repair_execution_status"], "not_selected")
        self.assertEqual(payload["supported_repair_execution_reason"], "repair_not_selected")
        self.assertFalse(payload["supported_repair_execution_attempted"])
        self.assertFalse(payload["supported_repair_executed"])
        self.assertFalse(payload["supported_repair_verification_passed"])
        self.assertFalse(payload["supported_repair_verification_failed"])
        self.assertEqual(payload["final_human_review_gate_status"], "required")
        self.assertTrue(payload["final_human_review_required"])
        self.assertEqual(
            payload["final_human_review_reason"],
            "final_review_manual_only_posture",
        )
        self.assertTrue(payload["final_human_gate_preserved"])
        self.assertEqual(payload["project_planning_summary_status"], "available")
        self.assertTrue(payload["project_planning_summary_available"])
        self.assertEqual(
            payload["project_planning_summary_reason"],
            "planning_summary_compiled",
        )
        self.assertEqual(
            payload["project_planning_control_posture"],
            "human_review_required",
        )
        self.assertTrue(payload["approval_skip_human_gate_preserved"])
        self.assertFalse(payload["approval_skip_applied"])
        self.assertEqual(len(transport.launch_order), 3)

    def test_runner_final_human_review_required_for_high_risk_posture(self) -> None:
        approval_email_payload = {
            "approval_email_status": "required",
            "approval_email_validity": "valid",
            "approval_required": True,
            "approval_priority": "critical",
            "approval_reason_class": "restart_hold",
            "proposed_next_direction": "replan_preparation",
            "proposed_target_lane": "replan_preparation",
            "proposed_restart_mode": "approval_required_then_restart",
            "proposed_action_class": "review_and_replan",
        }
        response_payload = {
            "approval_response_status": "awaiting_response",
            "approval_response_validity": "valid",
            "response_received": False,
            "response_command_normalized": "",
            "response_supported": False,
            "response_decision_class": "unknown",
        }
        approved_restart_payload = {
            "approved_restart_status": "not_ready",
            "approved_restart_validity": "valid",
            "restart_decision": "unknown",
            "restart_allowed": False,
            "restart_blocked": True,
            "restart_held": False,
            "restart_requires_manual_followup": False,
            "approved_next_direction": "unknown",
            "approved_target_lane": "unknown",
            "approved_action_class": "unknown",
            "response_decision_class": "unknown",
            "response_command_normalized": "",
        }
        approval_safety_payload = {
            "approval_safety_status": "safe_to_deliver",
            "approval_safety_validity": "valid",
            "approval_safety_confidence": "high",
            "approval_safety_decision": "allow_delivery",
            "approval_pending_duplicate": False,
            "approval_cooldown_active": False,
            "approval_loop_suspected": False,
            "approval_delivery_blocked_by_safety": False,
            "approval_delivery_deferred_by_safety": False,
            "approval_delivery_allowed_by_safety": True,
        }
        fleet_safety_payload = {
            "fleet_safety_status": "allow",
            "fleet_safety_validity": "valid",
            "fleet_safety_decision": "proceed",
            "fleet_restart_decision": "restart_allowed",
            "fleet_manual_review_required": False,
            "bucket_severity": "critical",
        }
        loop_hardening_payload = {
            "loop_hardening_status": "stable",
            "loop_hardening_validity": "valid",
            "no_progress_status": "none",
            "no_progress_detected": False,
            "no_progress_stop_required": False,
        }
        failure_bucketing_payload = {
            "failure_bucketing_status": "classified",
            "failure_bucketing_validity": "valid",
            "primary_failure_bucket": "retry_exhausted",
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"
            transport = _RecordingDryRunTransport()
            runner = PlannedExecutionRunner(
                adapter=CodexExecutorAdapter(transport=transport)
            )
            with (
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_email_delivery_contract_surface",
                    return_value=approval_email_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_response_contract_surface",
                    return_value=response_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approved_restart_contract_surface",
                    return_value=approved_restart_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_safety_contract_surface",
                    return_value=approval_safety_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_fleet_safety_control_contract_surface",
                    return_value=fleet_safety_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_loop_hardening_contract_surface",
                    return_value=loop_hardening_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_failure_bucketing_hardening_contract_surface",
                    return_value=failure_bucketing_payload,
                ),
            ):
                manifest = runner.run(
                    artifacts_input_dir=artifacts_dir,
                    output_dir=out_dir,
                    dry_run=True,
                    stop_on_failure=True,
                )
            run_root = out_dir / manifest["job_id"]
            payload = json.loads(
                (run_root / "approved_restart_execution_contract.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(payload["automatic_restart_execution_status"], "not_executed")
        self.assertEqual(payload["final_human_review_gate_status"], "required")
        self.assertTrue(payload["final_human_review_required"])
        self.assertEqual(
            payload["final_human_review_reason"],
            "final_review_high_risk_posture",
        )
        self.assertTrue(payload["final_human_gate_preserved"])
        self.assertEqual(payload["project_planning_summary_status"], "available")
        self.assertTrue(payload["project_planning_summary_available"])
        self.assertEqual(
            payload["project_planning_summary_reason"],
            "planning_summary_compiled",
        )
        self.assertEqual(
            payload["project_planning_control_posture"],
            "human_review_required",
        )
        self.assertEqual(payload["objective_compiler_status"], "available")
        self.assertTrue(payload["current_objective_available"])
        self.assertEqual(payload["objective_done_criteria_status"], "not_met")
        self.assertEqual(payload["objective_stop_criteria_status"], "stop")
        self.assertEqual(payload["objective_completion_posture"], "objective_blocked")
        self.assertFalse(payload["objective_scope_drift_detected"])
        self.assertEqual(payload["objective_scope_drift_status"], "clear")
        self.assertEqual(payload["project_autonomy_budget_status"], "available")
        self.assertEqual(payload["project_priority_posture"], "deferred")
        self.assertTrue(payload["project_priority_deferred"])
        self.assertEqual(payload["project_high_risk_defer_posture"], "defer")
        self.assertTrue(payload["project_high_risk_defer_active"])
        self.assertEqual(payload["project_run_budget_posture"], "available")
        self.assertEqual(payload["project_objective_budget_posture"], "available")
        self.assertEqual(payload["project_pr_retry_budget_posture"], "not_applicable")
        self.assertEqual(payload["project_quality_gate_status"], "available")
        self.assertEqual(payload["project_quality_gate_posture"], "review_ready")
        self.assertFalse(payload["project_quality_gate_merge_ready"])
        self.assertTrue(payload["project_quality_gate_review_ready"])
        self.assertFalse(payload["project_quality_gate_retry_needed"])
        self.assertEqual(payload["project_quality_gate_risk_level"], "high")
        self.assertTrue(payload["project_quality_gate_high_risk"])
        self.assertIn("targeted_regression", payload["project_quality_gate_recommended"])
        self.assertEqual(payload["project_merge_branch_lifecycle_status"], "available")
        self.assertEqual(payload["project_merge_ready_posture"], "not_merge_ready")
        self.assertFalse(payload["project_merge_ready"])
        self.assertEqual(payload["project_branch_cleanup_candidate_posture"], "not_candidate")
        self.assertFalse(payload["project_branch_cleanup_candidate"])
        self.assertEqual(
            payload["project_branch_quarantine_candidate_posture"],
            "candidate",
        )
        self.assertTrue(payload["project_branch_quarantine_candidate"])
        self.assertEqual(payload["project_local_main_sync_posture"], "sync_required")
        self.assertTrue(payload["project_local_main_sync_required"])
        self.assertEqual(payload["project_failure_memory_status"], "available")
        self.assertIn(
            payload["project_failure_memory_suppression_posture"],
            {
                "none",
                "suppress_retry",
                "suppress_repair",
                "suppress_review_issue",
                "suppress_failure_bucket",
            },
        )
        self.assertIn(
            payload["project_failure_memory_last_failure_bucket"],
            {"retry_exhausted", "unknown"},
        )
        self.assertGreaterEqual(payload["project_failure_memory_retry_failure_count"], 0)
        self.assertGreaterEqual(payload["project_failure_memory_repair_failure_count"], 0)
        self.assertEqual(
            payload["project_failure_memory_suppression_active"],
            payload["project_failure_memory_suppression_posture"] != "none",
        )
        self.assertEqual(payload["project_external_boundary_status"], "available")
        self.assertEqual(payload["project_external_dependency_posture"], "manual_only")
        self.assertFalse(payload["project_external_dependency_available"])
        self.assertFalse(payload["project_external_dependency_blocked"])
        self.assertEqual(payload["project_external_manual_only_posture"], "manual_only")
        self.assertTrue(payload["project_external_manual_only_required"])
        self.assertEqual(
            payload["project_external_github_boundary_posture"],
            "manual_only",
        )
        self.assertEqual(payload["project_human_escalation_status"], "available")
        self.assertEqual(
            payload["project_human_escalation_posture"],
            "escalation_required",
        )
        self.assertTrue(payload["project_human_escalation_required"])
        self.assertEqual(payload["project_manual_only_risk_posture"], "elevated")
        self.assertEqual(payload["project_external_risk_posture"], "elevated")
        self.assertEqual(payload["project_budget_risk_posture"], "elevated")
        self.assertFalse(payload["project_human_escalation_unavailable"])
        self.assertEqual(
            payload["project_approval_notification_status"],
            "available",
        )
        self.assertEqual(
            payload["project_approval_notification_ready_posture"],
            "ready",
        )
        self.assertTrue(payload["project_approval_notification_ready"])
        self.assertEqual(
            payload["project_approval_reply_required_posture"],
            "reply_required",
        )
        self.assertTrue(payload["project_approval_reply_required"])
        self.assertEqual(
            payload["project_approval_channel_posture"],
            "manual_only",
        )
        self.assertEqual(
            payload["project_approval_mobile_summary_posture"],
            "available",
        )
        self.assertTrue(payload["project_approval_mobile_summary_compact"])
        self.assertFalse(payload["project_approval_notification_unavailable"])
        self.assertEqual(payload["project_multi_objective_status"], "available")
        self.assertEqual(
            payload["project_active_objective_selection_posture"],
            "deferred",
        )
        self.assertEqual(
            payload["project_blocked_objective_deferral_posture"],
            "deferred",
        )
        self.assertTrue(payload["project_blocked_objective_deferred"])
        self.assertEqual(
            payload["project_resumable_queue_ordering_posture"],
            "deferred_non_runnable",
        )
        self.assertFalse(payload["project_resumable_queue_has_pending"])
        self.assertFalse(payload["project_multi_objective_unavailable"])
        self.assertEqual(payload["project_roadmap_status"], "available")
        self.assertTrue(payload["project_roadmap_available"])
        self.assertEqual(payload["project_roadmap_reason"], "roadmap_compiled")
        self.assertEqual(payload["project_roadmap_item_count"], 6)
        human_review_items = [
            item
            for item in payload["project_roadmap_items"]
            if item.get("roadmap_item_id") == "roadmap_human_review_gate"
        ]
        self.assertEqual(len(human_review_items), 1)
        self.assertTrue(human_review_items[0]["blocked"])
        self.assertEqual(payload["project_pr_slicing_status"], "available")
        self.assertTrue(payload["project_pr_slicing_available"])
        self.assertEqual(payload["project_pr_slicing_reason"], "pr_slices_compiled")
        self.assertEqual(payload["project_pr_slice_count"], 6)
        self.assertEqual(
            payload["project_pr_one_pr_size_decision"],
            "single_theme_single_pr",
        )
        self.assertEqual(payload["implementation_prompt_status"], "available")
        self.assertTrue(payload["implementation_prompt_available"])
        self.assertEqual(payload["implementation_prompt_reason"], "prompt_compiled")
        self.assertEqual(
            payload["implementation_prompt_slice_id"],
            "slice_01_continuation_budget",
        )
        self.assertEqual(
            payload["implementation_prompt_roadmap_item_id"],
            "roadmap_continuation_budget",
        )
        self.assertEqual(
            payload["implementation_prompt_payload"]["prompt_status"],
            "available",
        )
        self.assertTrue(
            payload["implementation_prompt_payload"]["out_of_scope"]
        )
        self.assertEqual(payload["project_pr_queue_status"], "prepared")
        self.assertEqual(payload["project_pr_queue_reason"], "queue_item_prepared")
        self.assertEqual(payload["project_pr_queue_item_count"], 6)
        self.assertEqual(payload["project_pr_queue_selected_slice_id"], "slice_01_continuation_budget")
        self.assertTrue(payload["project_pr_queue_handoff_prepared"])
        self.assertEqual(payload["project_pr_queue_outcome"], "queue_item_prepared")
        self.assertEqual(len(transport.launch_order), 3)

    def test_runner_selects_repair_playbook_for_supported_failure_bucket(self) -> None:
        approval_email_payload = {
            "approval_email_status": "required",
            "approval_email_validity": "valid",
            "approval_required": True,
            "approval_priority": "low",
            "approval_reason_class": "restart_hold",
            "proposed_next_direction": "replan_preparation",
            "proposed_target_lane": "replan_preparation",
            "proposed_restart_mode": "approval_required_then_restart",
            "proposed_action_class": "review_and_replan",
        }
        response_payload = {
            "approval_response_status": "awaiting_response",
            "approval_response_validity": "valid",
            "response_received": False,
            "response_command_normalized": "",
            "response_supported": False,
            "response_decision_class": "unknown",
        }
        approved_restart_payload = {
            "approved_restart_status": "not_ready",
            "approved_restart_validity": "valid",
            "restart_decision": "unknown",
            "restart_allowed": False,
            "restart_blocked": True,
            "restart_held": False,
            "restart_requires_manual_followup": False,
            "approved_next_direction": "unknown",
            "approved_target_lane": "unknown",
            "approved_action_class": "unknown",
            "response_decision_class": "unknown",
            "response_command_normalized": "",
        }
        approval_safety_payload = {
            "approval_safety_status": "safe_to_deliver",
            "approval_safety_validity": "valid",
            "approval_safety_confidence": "high",
            "approval_safety_decision": "allow_delivery",
            "approval_pending_duplicate": False,
            "approval_cooldown_active": False,
            "approval_loop_suspected": False,
            "approval_delivery_blocked_by_safety": False,
            "approval_delivery_deferred_by_safety": False,
            "approval_delivery_allowed_by_safety": True,
        }
        fleet_safety_payload = {
            "fleet_safety_status": "allow",
            "fleet_safety_validity": "valid",
            "fleet_safety_decision": "proceed",
            "fleet_restart_decision": "restart_allowed",
            "fleet_manual_review_required": False,
            "bucket_severity": "low",
        }
        loop_hardening_payload = {
            "loop_hardening_status": "stable",
            "loop_hardening_validity": "valid",
            "no_progress_status": "none",
            "no_progress_detected": False,
            "no_progress_stop_required": False,
        }
        failure_bucketing_payload = {
            "failure_bucketing_status": "classified",
            "failure_bucketing_validity": "valid",
            "primary_failure_bucket": "retry_exhausted",
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"
            status_map = {
                "project-planned-exec-pr-01__approved_restart_once": "completed",
            }
            transport = _RecordingDryRunTransport(status_by_pr_id=status_map)
            runner = PlannedExecutionRunner(
                adapter=CodexExecutorAdapter(transport=transport)
            )
            with (
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_email_delivery_contract_surface",
                    return_value=approval_email_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_response_contract_surface",
                    return_value=response_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approved_restart_contract_surface",
                    return_value=approved_restart_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_safety_contract_surface",
                    return_value=approval_safety_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_fleet_safety_control_contract_surface",
                    return_value=fleet_safety_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_loop_hardening_contract_surface",
                    return_value=loop_hardening_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_failure_bucketing_hardening_contract_surface",
                    return_value=failure_bucketing_payload,
                ),
            ):
                manifest = runner.run(
                    artifacts_input_dir=artifacts_dir,
                    output_dir=out_dir,
                    dry_run=True,
                    stop_on_failure=True,
                )
            run_root = out_dir / manifest["job_id"]
            payload = json.loads(
                (run_root / "approved_restart_execution_contract.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(payload["automatic_restart_execution_status"], "executed")
        self.assertEqual(
            payload["continuation_repair_playbook_selection_status"],
            "selected",
        )
        self.assertTrue(payload["continuation_repair_playbook_selected"])
        self.assertTrue(payload["continuation_repair_playbook_truth_sufficient"])
        self.assertTrue(payload["continuation_repair_playbook_supported_bucket"])
        self.assertEqual(payload["continuation_repair_playbook_bucket"], "retry_exhausted")
        self.assertEqual(payload["continuation_repair_playbook_class"], "replan_plan")
        self.assertEqual(
            payload["continuation_repair_playbook_candidate_action"],
            "request_replan",
        )
        self.assertEqual(
            payload["continuation_repair_playbook_reason"],
            "playbook_selected",
        )
        self.assertEqual(
            payload["continuation_next_step_selection_status"],
            "selected",
        )
        self.assertTrue(payload["continuation_next_step_selected"])
        self.assertEqual(payload["continuation_next_step_target"], "supported_repair")
        self.assertEqual(
            payload["continuation_next_step_reason"],
            "next_step_selected_supported_repair",
        )
        self.assertEqual(
            payload["supported_repair_execution_status"],
            "executed_verification_passed",
        )
        self.assertEqual(
            payload["supported_repair_execution_reason"],
            "repair_verification_passed",
        )
        self.assertTrue(payload["supported_repair_execution_attempted"])
        self.assertTrue(payload["supported_repair_execution_qualified"])
        self.assertTrue(payload["supported_repair_executed"])
        self.assertTrue(payload["supported_repair_verification_passed"])
        self.assertFalse(payload["supported_repair_verification_failed"])
        self.assertEqual(payload["final_human_review_gate_status"], "not_required")
        self.assertFalse(payload["final_human_review_required"])
        self.assertEqual(
            payload["final_human_review_reason"],
            "final_review_not_required",
        )
        self.assertFalse(payload["final_human_gate_preserved"])
        self.assertEqual(len(transport.launch_order), 4)

    def test_runner_supported_repair_execution_verification_failure_preserves_human_gate(self) -> None:
        approval_email_payload = {
            "approval_email_status": "required",
            "approval_email_validity": "valid",
            "approval_required": True,
            "approval_priority": "low",
            "approval_reason_class": "restart_hold",
            "proposed_next_direction": "replan_preparation",
            "proposed_target_lane": "replan_preparation",
            "proposed_restart_mode": "approval_required_then_restart",
            "proposed_action_class": "review_and_replan",
        }
        response_payload = {
            "approval_response_status": "awaiting_response",
            "approval_response_validity": "valid",
            "response_received": False,
            "response_command_normalized": "",
            "response_supported": False,
            "response_decision_class": "unknown",
        }
        approved_restart_payload = {
            "approved_restart_status": "not_ready",
            "approved_restart_validity": "valid",
            "restart_decision": "unknown",
            "restart_allowed": False,
            "restart_blocked": True,
            "restart_held": False,
            "restart_requires_manual_followup": False,
            "approved_next_direction": "unknown",
            "approved_target_lane": "unknown",
            "approved_action_class": "unknown",
            "response_decision_class": "unknown",
            "response_command_normalized": "",
        }
        approval_safety_payload = {
            "approval_safety_status": "safe_to_deliver",
            "approval_safety_validity": "valid",
            "approval_safety_confidence": "high",
            "approval_safety_decision": "allow_delivery",
            "approval_pending_duplicate": False,
            "approval_cooldown_active": False,
            "approval_loop_suspected": False,
            "approval_delivery_blocked_by_safety": False,
            "approval_delivery_deferred_by_safety": False,
            "approval_delivery_allowed_by_safety": True,
        }
        fleet_safety_payload = {
            "fleet_safety_status": "allow",
            "fleet_safety_validity": "valid",
            "fleet_safety_decision": "proceed",
            "fleet_restart_decision": "restart_allowed",
            "fleet_manual_review_required": False,
            "bucket_severity": "low",
        }
        loop_hardening_payload = {
            "loop_hardening_status": "stable",
            "loop_hardening_validity": "valid",
            "no_progress_status": "none",
            "no_progress_detected": False,
            "no_progress_stop_required": False,
        }
        failure_bucketing_payload = {
            "failure_bucketing_status": "classified",
            "failure_bucketing_validity": "valid",
            "primary_failure_bucket": "retry_exhausted",
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"
            status_map = {
                "project-planned-exec-pr-01__approved_restart_once": "failed",
            }
            transport = _RecordingDryRunTransport(status_by_pr_id=status_map)
            runner = PlannedExecutionRunner(
                adapter=CodexExecutorAdapter(transport=transport)
            )
            with (
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_email_delivery_contract_surface",
                    return_value=approval_email_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_response_contract_surface",
                    return_value=response_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approved_restart_contract_surface",
                    return_value=approved_restart_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_safety_contract_surface",
                    return_value=approval_safety_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_fleet_safety_control_contract_surface",
                    return_value=fleet_safety_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_loop_hardening_contract_surface",
                    return_value=loop_hardening_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_failure_bucketing_hardening_contract_surface",
                    return_value=failure_bucketing_payload,
                ),
            ):
                manifest = runner.run(
                    artifacts_input_dir=artifacts_dir,
                    output_dir=out_dir,
                    dry_run=True,
                    stop_on_failure=True,
                )
            run_root = out_dir / manifest["job_id"]
            payload = json.loads(
                (run_root / "approved_restart_execution_contract.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(payload["automatic_restart_execution_status"], "executed")
        self.assertEqual(
            payload["automatic_restart_execution_reason"],
            "supported_repair_verification_failed",
        )
        self.assertEqual(
            payload["supported_repair_execution_status"],
            "executed_verification_failed",
        )
        self.assertEqual(
            payload["supported_repair_execution_reason"],
            "repair_verification_failed",
        )
        self.assertTrue(payload["supported_repair_execution_attempted"])
        self.assertTrue(payload["supported_repair_execution_qualified"])
        self.assertTrue(payload["supported_repair_executed"])
        self.assertFalse(payload["supported_repair_verification_passed"])
        self.assertTrue(payload["supported_repair_verification_failed"])
        self.assertEqual(payload["final_human_review_gate_status"], "required")
        self.assertTrue(payload["final_human_review_required"])
        self.assertEqual(
            payload["final_human_review_reason"],
            "final_review_supported_repair_verification_failed",
        )
        self.assertTrue(payload["final_human_gate_preserved"])
        self.assertEqual(len(transport.launch_order), 4)

    def test_runner_supported_repair_not_executed_when_launch_fails(self) -> None:
        approval_email_payload = {
            "approval_email_status": "required",
            "approval_email_validity": "valid",
            "approval_required": True,
            "approval_priority": "low",
            "approval_reason_class": "restart_hold",
            "proposed_next_direction": "replan_preparation",
            "proposed_target_lane": "replan_preparation",
            "proposed_restart_mode": "approval_required_then_restart",
            "proposed_action_class": "review_and_replan",
        }
        response_payload = {
            "approval_response_status": "awaiting_response",
            "approval_response_validity": "valid",
            "response_received": False,
            "response_command_normalized": "",
            "response_supported": False,
            "response_decision_class": "unknown",
        }
        approved_restart_payload = {
            "approved_restart_status": "not_ready",
            "approved_restart_validity": "valid",
            "restart_decision": "unknown",
            "restart_allowed": False,
            "restart_blocked": True,
            "restart_held": False,
            "restart_requires_manual_followup": False,
            "approved_next_direction": "unknown",
            "approved_target_lane": "unknown",
            "approved_action_class": "unknown",
            "response_decision_class": "unknown",
            "response_command_normalized": "",
        }
        approval_safety_payload = {
            "approval_safety_status": "safe_to_deliver",
            "approval_safety_validity": "valid",
            "approval_safety_confidence": "high",
            "approval_safety_decision": "allow_delivery",
            "approval_pending_duplicate": False,
            "approval_cooldown_active": False,
            "approval_loop_suspected": False,
            "approval_delivery_blocked_by_safety": False,
            "approval_delivery_deferred_by_safety": False,
            "approval_delivery_allowed_by_safety": True,
        }
        fleet_safety_payload = {
            "fleet_safety_status": "allow",
            "fleet_safety_validity": "valid",
            "fleet_safety_decision": "proceed",
            "fleet_restart_decision": "restart_allowed",
            "fleet_manual_review_required": False,
            "bucket_severity": "low",
        }
        loop_hardening_payload = {
            "loop_hardening_status": "stable",
            "loop_hardening_validity": "valid",
            "no_progress_status": "none",
            "no_progress_detected": False,
            "no_progress_stop_required": False,
        }
        failure_bucketing_payload = {
            "failure_bucketing_status": "classified",
            "failure_bucketing_validity": "valid",
            "primary_failure_bucket": "retry_exhausted",
        }

        class _SupportedRepairLaunchFailureTransport(_RecordingDryRunTransport):
            def launch_job(self, **kwargs):  # type: ignore[override]
                pr_id = str(kwargs.get("pr_id", ""))
                self.launch_order.append(pr_id)
                if pr_id.endswith("__approved_restart_once"):
                    raise RuntimeError("mocked supported repair launch failure")
                return super(_RecordingDryRunTransport, self).launch_job(**kwargs)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"
            transport = _SupportedRepairLaunchFailureTransport()
            runner = PlannedExecutionRunner(
                adapter=CodexExecutorAdapter(transport=transport)
            )
            with (
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_email_delivery_contract_surface",
                    return_value=approval_email_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_response_contract_surface",
                    return_value=response_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approved_restart_contract_surface",
                    return_value=approved_restart_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_safety_contract_surface",
                    return_value=approval_safety_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_fleet_safety_control_contract_surface",
                    return_value=fleet_safety_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_loop_hardening_contract_surface",
                    return_value=loop_hardening_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_failure_bucketing_hardening_contract_surface",
                    return_value=failure_bucketing_payload,
                ),
            ):
                manifest = runner.run(
                    artifacts_input_dir=artifacts_dir,
                    output_dir=out_dir,
                    dry_run=True,
                    stop_on_failure=True,
                )
            run_root = out_dir / manifest["job_id"]
            payload = json.loads(
                (run_root / "approved_restart_execution_contract.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(payload["automatic_restart_execution_status"], "not_executed")
        self.assertEqual(
            payload["automatic_restart_execution_reason"],
            "restart_launch_failed",
        )
        self.assertEqual(
            payload["supported_repair_execution_status"],
            "not_executed_launch_failed",
        )
        self.assertEqual(
            payload["supported_repair_execution_reason"],
            "repair_launch_failed",
        )
        self.assertTrue(payload["supported_repair_execution_attempted"])
        self.assertTrue(payload["supported_repair_execution_qualified"])
        self.assertFalse(payload["supported_repair_executed"])
        self.assertFalse(payload["supported_repair_verification_passed"])
        self.assertFalse(payload["supported_repair_verification_failed"])
        self.assertEqual(len(transport.launch_order), 4)

    def test_runner_supported_repair_not_executed_when_playbook_is_not_executable(self) -> None:
        approval_email_payload = {
            "approval_email_status": "required",
            "approval_email_validity": "valid",
            "approval_required": True,
            "approval_priority": "low",
            "approval_reason_class": "restart_hold",
            "proposed_next_direction": "replan_preparation",
            "proposed_target_lane": "replan_preparation",
            "proposed_restart_mode": "approval_required_then_restart",
            "proposed_action_class": "review_and_replan",
        }
        response_payload = {
            "approval_response_status": "awaiting_response",
            "approval_response_validity": "valid",
            "response_received": False,
            "response_command_normalized": "",
            "response_supported": False,
            "response_decision_class": "unknown",
        }
        approved_restart_payload = {
            "approved_restart_status": "not_ready",
            "approved_restart_validity": "valid",
            "restart_decision": "unknown",
            "restart_allowed": False,
            "restart_blocked": True,
            "restart_held": False,
            "restart_requires_manual_followup": False,
            "approved_next_direction": "unknown",
            "approved_target_lane": "unknown",
            "approved_action_class": "unknown",
            "response_decision_class": "unknown",
            "response_command_normalized": "",
        }
        approval_safety_payload = {
            "approval_safety_status": "safe_to_deliver",
            "approval_safety_validity": "valid",
            "approval_safety_confidence": "high",
            "approval_safety_decision": "allow_delivery",
            "approval_pending_duplicate": False,
            "approval_cooldown_active": False,
            "approval_loop_suspected": False,
            "approval_delivery_blocked_by_safety": False,
            "approval_delivery_deferred_by_safety": False,
            "approval_delivery_allowed_by_safety": True,
        }
        fleet_safety_payload = {
            "fleet_safety_status": "allow",
            "fleet_safety_validity": "valid",
            "fleet_safety_decision": "proceed",
            "fleet_restart_decision": "restart_allowed",
            "fleet_manual_review_required": False,
            "bucket_severity": "low",
        }
        loop_hardening_payload = {
            "loop_hardening_status": "stable",
            "loop_hardening_validity": "valid",
            "no_progress_status": "none",
            "no_progress_detected": False,
            "no_progress_stop_required": False,
        }
        failure_bucketing_payload = {
            "failure_bucketing_status": "classified",
            "failure_bucketing_validity": "valid",
            "primary_failure_bucket": "no_progress",
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"
            transport = _RecordingDryRunTransport()
            runner = PlannedExecutionRunner(
                adapter=CodexExecutorAdapter(transport=transport)
            )
            with (
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_email_delivery_contract_surface",
                    return_value=approval_email_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_response_contract_surface",
                    return_value=response_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approved_restart_contract_surface",
                    return_value=approved_restart_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_safety_contract_surface",
                    return_value=approval_safety_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_fleet_safety_control_contract_surface",
                    return_value=fleet_safety_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_loop_hardening_contract_surface",
                    return_value=loop_hardening_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_failure_bucketing_hardening_contract_surface",
                    return_value=failure_bucketing_payload,
                ),
            ):
                manifest = runner.run(
                    artifacts_input_dir=artifacts_dir,
                    output_dir=out_dir,
                    dry_run=True,
                    stop_on_failure=True,
                )
            run_root = out_dir / manifest["job_id"]
            payload = json.loads(
                (run_root / "approved_restart_execution_contract.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(payload["automatic_restart_execution_status"], "not_executed")
        self.assertEqual(
            payload["automatic_restart_execution_reason"],
            "supported_repair_qualification_failed",
        )
        self.assertEqual(
            payload["supported_repair_execution_status"],
            "not_executed_qualification_failed",
        )
        self.assertEqual(
            payload["supported_repair_execution_reason"],
            "repair_qualification_failed",
        )
        self.assertFalse(payload["supported_repair_execution_attempted"])
        self.assertFalse(payload["supported_repair_execution_qualified"])
        self.assertFalse(payload["supported_repair_executed"])
        self.assertFalse(payload["supported_repair_verification_passed"])
        self.assertFalse(payload["supported_repair_verification_failed"])
        self.assertTrue(payload["approval_skip_human_gate_preserved"])
        self.assertFalse(payload["approval_skip_applied"])
        self.assertEqual(len(transport.launch_order), 3)

    def test_runner_does_not_select_repair_playbook_when_bucket_truth_is_insufficient(self) -> None:
        approval_email_payload = {
            "approval_email_status": "required",
            "approval_email_validity": "valid",
            "approval_required": True,
            "approval_priority": "low",
            "approval_reason_class": "restart_hold",
            "proposed_next_direction": "replan_preparation",
            "proposed_target_lane": "replan_preparation",
            "proposed_restart_mode": "approval_required_then_restart",
            "proposed_action_class": "review_and_replan",
        }
        response_payload = {
            "approval_response_status": "awaiting_response",
            "approval_response_validity": "valid",
            "response_received": False,
            "response_command_normalized": "",
            "response_supported": False,
            "response_decision_class": "unknown",
        }
        approved_restart_payload = {
            "approved_restart_status": "not_ready",
            "approved_restart_validity": "valid",
            "restart_decision": "unknown",
            "restart_allowed": False,
            "restart_blocked": True,
            "restart_held": False,
            "restart_requires_manual_followup": False,
            "approved_next_direction": "unknown",
            "approved_target_lane": "unknown",
            "approved_action_class": "unknown",
            "response_decision_class": "unknown",
            "response_command_normalized": "",
        }
        approval_safety_payload = {
            "approval_safety_status": "safe_to_deliver",
            "approval_safety_validity": "valid",
            "approval_safety_confidence": "high",
            "approval_safety_decision": "allow_delivery",
            "approval_pending_duplicate": False,
            "approval_cooldown_active": False,
            "approval_loop_suspected": False,
            "approval_delivery_blocked_by_safety": False,
            "approval_delivery_deferred_by_safety": False,
            "approval_delivery_allowed_by_safety": True,
        }
        fleet_safety_payload = {
            "fleet_safety_status": "allow",
            "fleet_safety_validity": "valid",
            "fleet_safety_decision": "proceed",
            "fleet_restart_decision": "restart_allowed",
            "fleet_manual_review_required": False,
            "bucket_severity": "low",
        }
        loop_hardening_payload = {
            "loop_hardening_status": "stable",
            "loop_hardening_validity": "valid",
            "no_progress_status": "none",
            "no_progress_detected": False,
            "no_progress_stop_required": False,
        }
        failure_bucketing_payload = {
            "failure_bucketing_status": "classified",
            "failure_bucketing_validity": "partial",
            "primary_failure_bucket": "retry_exhausted",
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"
            status_map = {
                "project-planned-exec-pr-01__approved_restart_once": "completed",
            }
            transport = _RecordingDryRunTransport(status_by_pr_id=status_map)
            runner = PlannedExecutionRunner(
                adapter=CodexExecutorAdapter(transport=transport)
            )
            with (
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_email_delivery_contract_surface",
                    return_value=approval_email_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_response_contract_surface",
                    return_value=response_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approved_restart_contract_surface",
                    return_value=approved_restart_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_safety_contract_surface",
                    return_value=approval_safety_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_fleet_safety_control_contract_surface",
                    return_value=fleet_safety_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_loop_hardening_contract_surface",
                    return_value=loop_hardening_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_failure_bucketing_hardening_contract_surface",
                    return_value=failure_bucketing_payload,
                ),
            ):
                manifest = runner.run(
                    artifacts_input_dir=artifacts_dir,
                    output_dir=out_dir,
                    dry_run=True,
                    stop_on_failure=True,
                )
            run_root = out_dir / manifest["job_id"]
            payload = json.loads(
                (run_root / "approved_restart_execution_contract.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(payload["automatic_restart_execution_status"], "executed")
        self.assertEqual(
            payload["continuation_repair_playbook_selection_status"],
            "insufficient_truth",
        )
        self.assertFalse(payload["continuation_repair_playbook_selected"])
        self.assertFalse(payload["continuation_repair_playbook_truth_sufficient"])
        self.assertTrue(payload["continuation_repair_playbook_supported_bucket"])
        self.assertEqual(payload["continuation_repair_playbook_class"], "no_plan")
        self.assertEqual(payload["continuation_repair_playbook_candidate_action"], "no_action")
        self.assertEqual(
            payload["continuation_repair_playbook_reason"],
            "playbook_insufficient_truth",
        )
        self.assertEqual(
            payload["continuation_next_step_selection_status"],
            "selected",
        )
        self.assertTrue(payload["continuation_next_step_selected"])
        self.assertEqual(payload["continuation_next_step_target"], "replan")
        self.assertEqual(
            payload["continuation_next_step_reason"],
            "next_step_selected_replan",
        )
        self.assertEqual(payload["supported_repair_execution_status"], "not_selected")
        self.assertEqual(payload["supported_repair_execution_reason"], "repair_not_selected")
        self.assertFalse(payload["supported_repair_execution_attempted"])
        self.assertFalse(payload["supported_repair_executed"])
        self.assertFalse(payload["supported_repair_verification_passed"])
        self.assertFalse(payload["supported_repair_verification_failed"])
        self.assertEqual(
            payload["project_planning_summary_status"],
            "available",
        )
        self.assertTrue(payload["project_planning_summary_available"])
        self.assertEqual(
            payload["project_planning_summary_reason"],
            "planning_summary_compiled",
        )
        self.assertEqual(len(transport.launch_order), 4)

    def test_runner_selects_truth_gather_next_step_when_truth_insufficiency_is_explicit(self) -> None:
        approval_email_payload = {
            "approval_email_status": "required",
            "approval_email_validity": "valid",
            "approval_required": True,
            "approval_priority": "low",
            "approval_reason_class": "restart_hold",
            "proposed_next_direction": "same_lane_retry",
            "proposed_target_lane": "same_lane_retry",
            "proposed_restart_mode": "approval_required_then_restart",
            "proposed_action_class": "review_and_restart",
        }
        response_payload = {
            "approval_response_status": "awaiting_response",
            "approval_response_validity": "valid",
            "response_received": False,
            "response_command_normalized": "",
            "response_supported": False,
            "response_decision_class": "unknown",
        }
        approved_restart_payload = {
            "approved_restart_status": "not_ready",
            "approved_restart_validity": "valid",
            "restart_decision": "unknown",
            "restart_allowed": False,
            "restart_blocked": True,
            "restart_held": False,
            "restart_requires_manual_followup": False,
            "approved_next_direction": "unknown",
            "approved_target_lane": "unknown",
            "approved_action_class": "unknown",
            "response_decision_class": "unknown",
            "response_command_normalized": "",
        }
        approval_safety_payload = {
            "approval_safety_status": "safe_to_deliver",
            "approval_safety_validity": "valid",
            "approval_safety_confidence": "high",
            "approval_safety_decision": "allow_delivery",
            "approval_pending_duplicate": False,
            "approval_cooldown_active": False,
            "approval_loop_suspected": False,
            "approval_delivery_blocked_by_safety": False,
            "approval_delivery_deferred_by_safety": False,
            "approval_delivery_allowed_by_safety": True,
        }
        fleet_safety_payload = {
            "fleet_safety_status": "allow",
            "fleet_safety_validity": "valid",
            "fleet_safety_decision": "proceed",
            "fleet_restart_decision": "restart_allowed",
            "fleet_manual_review_required": False,
            "bucket_severity": "low",
        }
        loop_hardening_payload = {
            "loop_hardening_status": "stable",
            "loop_hardening_validity": "valid",
            "no_progress_status": "none",
            "no_progress_detected": False,
            "no_progress_stop_required": False,
        }
        failure_bucketing_payload = {
            "failure_bucketing_status": "insufficient_truth",
            "failure_bucketing_validity": "insufficient_truth",
            "primary_failure_bucket": "unknown",
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"
            status_map = {
                "project-planned-exec-pr-01__approved_restart_once": "completed",
            }
            transport = _RecordingDryRunTransport(status_by_pr_id=status_map)
            runner = PlannedExecutionRunner(
                adapter=CodexExecutorAdapter(transport=transport)
            )
            with (
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_email_delivery_contract_surface",
                    return_value=approval_email_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_response_contract_surface",
                    return_value=response_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approved_restart_contract_surface",
                    return_value=approved_restart_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_safety_contract_surface",
                    return_value=approval_safety_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_fleet_safety_control_contract_surface",
                    return_value=fleet_safety_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_loop_hardening_contract_surface",
                    return_value=loop_hardening_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_failure_bucketing_hardening_contract_surface",
                    return_value=failure_bucketing_payload,
                ),
            ):
                manifest = runner.run(
                    artifacts_input_dir=artifacts_dir,
                    output_dir=out_dir,
                    dry_run=True,
                    stop_on_failure=True,
                )
            run_root = out_dir / manifest["job_id"]
            payload = json.loads(
                (run_root / "approved_restart_execution_contract.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(payload["automatic_restart_execution_status"], "executed")
        self.assertEqual(
            payload["continuation_next_step_selection_status"],
            "selected",
        )
        self.assertTrue(payload["continuation_next_step_selected"])
        self.assertEqual(payload["continuation_next_step_target"], "truth_gather")
        self.assertTrue(payload["continuation_next_step_truth_insufficiency_explicit"])
        self.assertEqual(
            payload["continuation_next_step_reason"],
            "next_step_selected_truth_gather",
        )
        self.assertEqual(payload["supported_repair_execution_status"], "not_selected")
        self.assertEqual(payload["supported_repair_execution_reason"], "repair_not_selected")
        self.assertFalse(payload["supported_repair_execution_attempted"])
        self.assertFalse(payload["supported_repair_executed"])
        self.assertFalse(payload["supported_repair_verification_passed"])
        self.assertFalse(payload["supported_repair_verification_failed"])
        self.assertEqual(
            payload["project_planning_summary_status"],
            "insufficient_truth",
        )
        self.assertFalse(payload["project_planning_summary_available"])
        self.assertEqual(
            payload["project_planning_summary_reason"],
            "planning_summary_insufficient_truth",
        )
        self.assertEqual(payload["project_autonomy_budget_status"], "insufficient_truth")
        self.assertEqual(payload["project_priority_posture"], "insufficient_truth")
        self.assertEqual(payload["project_run_budget_posture"], "insufficient_truth")
        self.assertEqual(
            payload["project_objective_budget_posture"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["project_pr_retry_budget_posture"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["project_high_risk_defer_posture"],
            "insufficient_truth",
        )
        self.assertEqual(payload["project_quality_gate_status"], "insufficient_truth")
        self.assertEqual(payload["project_quality_gate_posture"], "insufficient_truth")
        self.assertTrue(payload["project_quality_gate_unavailable"])
        self.assertEqual(payload["project_quality_gate_recommended"], [])
        self.assertEqual(
            payload["project_merge_branch_lifecycle_status"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["project_merge_ready_posture"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["project_branch_cleanup_candidate_posture"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["project_branch_quarantine_candidate_posture"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["project_local_main_sync_posture"],
            "insufficient_truth",
        )
        self.assertTrue(payload["project_merge_branch_lifecycle_unavailable"])
        self.assertEqual(
            payload["project_failure_memory_status"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["project_failure_memory_suppression_posture"],
            "insufficient_truth",
        )
        self.assertFalse(payload["project_failure_memory_suppression_active"])
        self.assertTrue(payload["project_failure_memory_unavailable"])
        self.assertEqual(
            payload["project_external_boundary_status"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["project_external_dependency_posture"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["project_external_manual_only_posture"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["project_external_network_boundary_posture"],
            "insufficient_truth",
        )
        self.assertTrue(payload["project_external_boundary_unavailable"])
        self.assertEqual(
            payload["project_human_escalation_status"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["project_human_escalation_posture"],
            "insufficient_truth",
        )
        self.assertFalse(payload["project_human_escalation_required"])
        self.assertTrue(payload["project_human_escalation_unavailable"])
        self.assertEqual(
            payload["project_approval_notification_status"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["project_approval_notification_ready_posture"],
            "insufficient_truth",
        )
        self.assertFalse(payload["project_approval_notification_ready"])
        self.assertEqual(
            payload["project_approval_reply_required_posture"],
            "insufficient_truth",
        )
        self.assertFalse(payload["project_approval_reply_required"])
        self.assertEqual(
            payload["project_approval_channel_posture"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["project_approval_mobile_summary_posture"],
            "insufficient_truth",
        )
        self.assertEqual(payload["project_approval_mobile_summary_compact"], "")
        self.assertTrue(payload["project_approval_notification_unavailable"])
        self.assertEqual(
            payload["project_multi_objective_status"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["project_active_objective_selection_posture"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["project_blocked_objective_deferral_posture"],
            "insufficient_truth",
        )
        self.assertFalse(payload["project_blocked_objective_deferred"])
        self.assertEqual(
            payload["project_resumable_queue_ordering_posture"],
            "insufficient_truth",
        )
        self.assertFalse(payload["project_resumable_queue_has_pending"])
        self.assertTrue(payload["project_multi_objective_unavailable"])
        self.assertEqual(payload["objective_compiler_status"], "insufficient_truth")
        self.assertFalse(payload["current_objective_available"])
        self.assertEqual(
            payload["objective_done_criteria_status"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["objective_stop_criteria_status"],
            "insufficient_truth",
        )
        self.assertEqual(
            payload["objective_completion_posture"],
            "objective_insufficient_truth",
        )
        self.assertEqual(
            payload["objective_scope_drift_status"],
            "insufficient_truth",
        )
        self.assertEqual(payload["project_roadmap_status"], "insufficient_truth")
        self.assertFalse(payload["project_roadmap_available"])
        self.assertEqual(
            payload["project_roadmap_reason"],
            "roadmap_insufficient_truth",
        )
        self.assertEqual(payload["project_roadmap_item_count"], 0)
        self.assertEqual(payload["project_roadmap_items"], [])
        self.assertEqual(payload["project_pr_slicing_status"], "insufficient_truth")
        self.assertFalse(payload["project_pr_slicing_available"])
        self.assertEqual(
            payload["project_pr_slicing_reason"],
            "pr_slices_insufficient_truth",
        )
        self.assertEqual(payload["project_pr_slice_count"], 0)
        self.assertEqual(payload["project_pr_slices"], [])
        self.assertEqual(payload["project_pr_one_pr_size_decision"], "not_available")
        self.assertEqual(payload["implementation_prompt_status"], "insufficient_truth")
        self.assertFalse(payload["implementation_prompt_available"])
        self.assertEqual(
            payload["implementation_prompt_reason"],
            "prompt_planning_insufficient_truth",
        )
        self.assertEqual(payload["implementation_prompt_slice_id"], "")
        self.assertEqual(payload["implementation_prompt_roadmap_item_id"], "")
        self.assertEqual(
            payload["implementation_prompt_payload"]["prompt_status"],
            "insufficient_truth",
        )
        self.assertFalse(
            payload["implementation_prompt_payload"]["prompt_available"]
        )
        self.assertEqual(
            payload["implementation_prompt_payload"]["prompt_reason"],
            "prompt_planning_insufficient_truth",
        )
        self.assertEqual(payload["implementation_prompt_payload"]["preferred_files"], [])
        self.assertEqual(payload["project_pr_queue_status"], "insufficient_truth")
        self.assertEqual(
            payload["project_pr_queue_reason"],
            "queue_state_insufficient_truth",
        )
        self.assertEqual(payload["project_pr_queue_item_count"], 0)
        self.assertEqual(payload["project_pr_queue_runnable_count"], 0)
        self.assertEqual(payload["project_pr_queue_blocked_count"], 0)
        self.assertEqual(payload["project_pr_queue_selected_slice_id"], "")
        self.assertFalse(payload["project_pr_queue_handoff_prepared"])
        self.assertEqual(payload["project_pr_queue_handoff_payload"], {})
        self.assertEqual(payload["project_pr_queue_outcome"], "queue_state_insufficient_truth")
        self.assertEqual(payload["review_assimilation_status"], "insufficient_truth")
        self.assertEqual(payload["review_assimilation_action"], "none")
        self.assertEqual(
            payload["review_assimilation_reason"],
            "assimilation_queue_state_insufficient_truth",
        )
        self.assertFalse(payload["review_assimilation_available"])
        self.assertEqual(payload["long_running_stability_status"], "insufficient_truth")
        self.assertEqual(
            payload["long_running_reason"],
            "long_running_insufficient_truth_queue_state",
        )
        self.assertTrue(payload["long_running_pause_required"])
        self.assertEqual(len(transport.launch_order), 4)

    def test_runner_selects_retry_next_step_when_retry_is_supported(self) -> None:
        approval_email_payload = {
            "approval_email_status": "required",
            "approval_email_validity": "valid",
            "approval_required": True,
            "approval_priority": "low",
            "approval_reason_class": "restart_hold",
            "proposed_next_direction": "same_lane_retry",
            "proposed_target_lane": "same_lane_retry",
            "proposed_restart_mode": "approval_required_then_restart",
            "proposed_action_class": "review_and_restart",
        }
        response_payload = {
            "approval_response_status": "awaiting_response",
            "approval_response_validity": "valid",
            "response_received": False,
            "response_command_normalized": "",
            "response_supported": False,
            "response_decision_class": "unknown",
        }
        approved_restart_payload = {
            "approved_restart_status": "not_ready",
            "approved_restart_validity": "valid",
            "restart_decision": "unknown",
            "restart_allowed": False,
            "restart_blocked": True,
            "restart_held": False,
            "restart_requires_manual_followup": False,
            "approved_next_direction": "unknown",
            "approved_target_lane": "unknown",
            "approved_action_class": "unknown",
            "response_decision_class": "unknown",
            "response_command_normalized": "",
        }
        approval_safety_payload = {
            "approval_safety_status": "safe_to_deliver",
            "approval_safety_validity": "valid",
            "approval_safety_confidence": "high",
            "approval_safety_decision": "allow_delivery",
            "approval_pending_duplicate": False,
            "approval_cooldown_active": False,
            "approval_loop_suspected": False,
            "approval_delivery_blocked_by_safety": False,
            "approval_delivery_deferred_by_safety": False,
            "approval_delivery_allowed_by_safety": True,
        }
        fleet_safety_payload = {
            "fleet_safety_status": "allow",
            "fleet_safety_validity": "valid",
            "fleet_safety_decision": "proceed",
            "fleet_restart_decision": "restart_allowed",
            "fleet_manual_review_required": False,
            "bucket_severity": "low",
        }
        loop_hardening_payload = {
            "loop_hardening_status": "stable",
            "loop_hardening_validity": "valid",
            "no_progress_status": "none",
            "no_progress_detected": False,
            "no_progress_stop_required": False,
        }
        failure_bucketing_payload = {
            "failure_bucketing_status": "classified",
            "failure_bucketing_validity": "valid",
            "primary_failure_bucket": "unknown",
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"
            status_map = {
                "project-planned-exec-pr-01__approved_restart_once": "completed",
            }
            transport = _RecordingDryRunTransport(status_by_pr_id=status_map)
            runner = PlannedExecutionRunner(
                adapter=CodexExecutorAdapter(transport=transport)
            )
            with (
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_email_delivery_contract_surface",
                    return_value=approval_email_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_response_contract_surface",
                    return_value=response_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approved_restart_contract_surface",
                    return_value=approved_restart_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_safety_contract_surface",
                    return_value=approval_safety_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_fleet_safety_control_contract_surface",
                    return_value=fleet_safety_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_loop_hardening_contract_surface",
                    return_value=loop_hardening_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_failure_bucketing_hardening_contract_surface",
                    return_value=failure_bucketing_payload,
                ),
            ):
                manifest = runner.run(
                    artifacts_input_dir=artifacts_dir,
                    output_dir=out_dir,
                    dry_run=True,
                    stop_on_failure=True,
                )
            run_root = out_dir / manifest["job_id"]
            payload = json.loads(
                (run_root / "approved_restart_execution_contract.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(payload["automatic_restart_execution_status"], "executed")
        self.assertEqual(
            payload["continuation_next_step_selection_status"],
            "selected",
        )
        self.assertTrue(payload["continuation_next_step_selected"])
        self.assertEqual(payload["continuation_next_step_target"], "retry")
        self.assertEqual(
            payload["continuation_next_step_reason"],
            "next_step_selected_retry",
        )
        self.assertEqual(payload["supported_repair_execution_status"], "not_selected")
        self.assertEqual(payload["supported_repair_execution_reason"], "repair_not_selected")
        self.assertFalse(payload["supported_repair_execution_attempted"])
        self.assertFalse(payload["supported_repair_executed"])
        self.assertFalse(payload["supported_repair_verification_passed"])
        self.assertFalse(payload["supported_repair_verification_failed"])
        self.assertEqual(len(transport.launch_order), 4)

    def test_runner_blocks_execution_when_no_supported_next_step_is_selected(self) -> None:
        approval_email_payload = {
            "approval_email_status": "required",
            "approval_email_validity": "valid",
            "approval_required": True,
            "approval_priority": "low",
            "approval_reason_class": "closure_decision_required",
            "proposed_next_direction": "closure_followup",
            "proposed_target_lane": "closure_followup",
            "proposed_restart_mode": "approval_required_then_restart",
            "proposed_action_class": "review_and_close_followup",
        }
        response_payload = {
            "approval_response_status": "awaiting_response",
            "approval_response_validity": "valid",
            "response_received": False,
            "response_command_normalized": "",
            "response_supported": False,
            "response_decision_class": "unknown",
        }
        approved_restart_payload = {
            "approved_restart_status": "not_ready",
            "approved_restart_validity": "valid",
            "restart_decision": "unknown",
            "restart_allowed": False,
            "restart_blocked": True,
            "restart_held": False,
            "restart_requires_manual_followup": False,
            "approved_next_direction": "unknown",
            "approved_target_lane": "unknown",
            "approved_action_class": "unknown",
            "response_decision_class": "unknown",
            "response_command_normalized": "",
        }
        approval_safety_payload = {
            "approval_safety_status": "safe_to_deliver",
            "approval_safety_validity": "valid",
            "approval_safety_confidence": "high",
            "approval_safety_decision": "allow_delivery",
            "approval_pending_duplicate": False,
            "approval_cooldown_active": False,
            "approval_loop_suspected": False,
            "approval_delivery_blocked_by_safety": False,
            "approval_delivery_deferred_by_safety": False,
            "approval_delivery_allowed_by_safety": True,
        }
        fleet_safety_payload = {
            "fleet_safety_status": "allow",
            "fleet_safety_validity": "valid",
            "fleet_safety_decision": "proceed",
            "fleet_restart_decision": "restart_allowed",
            "fleet_manual_review_required": False,
            "bucket_severity": "low",
        }
        loop_hardening_payload = {
            "loop_hardening_status": "stable",
            "loop_hardening_validity": "valid",
            "no_progress_status": "none",
            "no_progress_detected": False,
            "no_progress_stop_required": False,
        }
        failure_bucketing_payload = {
            "failure_bucketing_status": "classified",
            "failure_bucketing_validity": "valid",
            "primary_failure_bucket": "unknown",
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"
            transport = _RecordingDryRunTransport()
            runner = PlannedExecutionRunner(
                adapter=CodexExecutorAdapter(transport=transport)
            )
            with (
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_email_delivery_contract_surface",
                    return_value=approval_email_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_response_contract_surface",
                    return_value=response_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approved_restart_contract_surface",
                    return_value=approved_restart_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_approval_safety_contract_surface",
                    return_value=approval_safety_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_fleet_safety_control_contract_surface",
                    return_value=fleet_safety_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_loop_hardening_contract_surface",
                    return_value=loop_hardening_payload,
                ),
                patch(
                    "automation.orchestration.planned_execution_runner.build_failure_bucketing_hardening_contract_surface",
                    return_value=failure_bucketing_payload,
                ),
            ):
                manifest = runner.run(
                    artifacts_input_dir=artifacts_dir,
                    output_dir=out_dir,
                    dry_run=True,
                    stop_on_failure=True,
                )
            run_root = out_dir / manifest["job_id"]
            payload = json.loads(
                (run_root / "approved_restart_execution_contract.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(payload["automatic_restart_execution_status"], "not_executed")
        self.assertEqual(
            payload["automatic_restart_execution_reason"],
            "continuation_next_step_not_selected",
        )
        self.assertEqual(
            payload["continuation_next_step_selection_status"],
            "not_selected",
        )
        self.assertFalse(payload["continuation_next_step_selected"])
        self.assertEqual(payload["continuation_next_step_target"], "none")
        self.assertEqual(
            payload["continuation_next_step_reason"],
            "next_step_not_selected",
        )
        self.assertTrue(payload["approval_skip_human_gate_preserved"])
        self.assertFalse(payload["approval_skip_applied"])
        self.assertEqual(len(transport.launch_order), 3)

    def test_operator_explainability_distinguishes_action_specific_denial(self) -> None:
        run_state = _augment_run_state_with_operator_explainability(
            run_state_payload={
                "state": "paused",
                "loop_state": "manual_intervention_required",
                "next_safe_action": "pause",
                "policy_status": "blocked",
                "policy_blocked": True,
                "policy_manual_required": False,
                "policy_replan_required": False,
                "policy_resume_allowed": True,
                "policy_terminal": False,
                "policy_primary_blocker_class": "remote_github",
                "policy_primary_action": "proceed_to_pr",
                "policy_blocked_reason": "existing_open_pr_detected",
                "policy_blocked_reasons": ["existing_open_pr_detected"],
                "policy_allowed_actions": ["inspect", "signal_recollect"],
                "policy_disallowed_actions": ["proceed_to_pr"],
                "resumable": True,
                "terminal": False,
            }
        )
        self.assertEqual(run_state["operator_posture_summary"], "action_specific_denial_non_terminal")
        self.assertEqual(run_state["operator_action_scope"], "action_specific")
        self.assertEqual(run_state["operator_resume_status"], "resumable")
        self.assertEqual(run_state["operator_primary_blocker_class"], "remote_github")
        self.assertEqual(run_state["operator_primary_action"], "proceed_to_pr")

    def test_operator_explainability_distinguishes_run_wide_replan_manual_followup(self) -> None:
        run_state = _augment_run_state_with_operator_explainability(
            run_state_payload={
                "state": "paused",
                "loop_state": "rollback_completed_blocked",
                "next_safe_action": "require_replanning",
                "policy_status": "replan_required",
                "policy_blocked": True,
                "policy_manual_required": True,
                "policy_replan_required": True,
                "policy_resume_allowed": False,
                "policy_terminal": False,
                "policy_primary_blocker_class": "replan_required",
                "policy_primary_action": "rollback_required",
                "policy_blocked_reason": "rollback_validation_failed",
                "policy_blocked_reasons": ["rollback_validation_failed"],
                "rollback_aftermath_blocked": True,
                "rollback_replan_required": True,
                "loop_replan_required": True,
                "resumable": False,
                "terminal": False,
            }
        )
        self.assertEqual(run_state["operator_posture_summary"], "execution_blocked_replan_required")
        self.assertEqual(run_state["operator_action_scope"], "run_wide")
        self.assertEqual(run_state["operator_resume_status"], "replan_required")
        self.assertEqual(run_state["operator_next_safe_posture"], "replan_required_before_execution")

    def test_operator_explainability_distinguishes_terminal_stop(self) -> None:
        run_state = _augment_run_state_with_operator_explainability(
            run_state_payload={
                "state": "completed",
                "loop_state": "terminal_success",
                "next_safe_action": "stop_terminal_success",
                "policy_status": "terminally_stopped",
                "policy_blocked": False,
                "policy_manual_required": False,
                "policy_replan_required": False,
                "policy_resume_allowed": False,
                "policy_terminal": True,
                "policy_primary_blocker_class": "terminal",
                "policy_primary_action": "",
                "resumable": False,
                "terminal": True,
            }
        )
        self.assertEqual(run_state["operator_posture_summary"], "terminal_stop")
        self.assertEqual(run_state["operator_resume_status"], "terminal")
        self.assertEqual(run_state["operator_next_safe_posture"], "stop_terminal")

    def test_manifest_summary_selector_is_compact_and_excludes_rendering_only_fields(self) -> None:
        compact = select_manifest_run_state_summary_compact(
            {
                "state": "paused",
                "orchestration_state": "paused_for_manual_review",
                "units_total": 2,
                "units_completed": 1,
                "units_blocked": 1,
                "units_failed": 0,
                "units_pending": 0,
                "global_stop": True,
                "continue_allowed": False,
                "run_paused": True,
                "manual_intervention_required": True,
                "rollback_evaluation_pending": False,
                "global_stop_recommended": True,
                "next_run_action": "hold_for_global_stop",
                "loop_state": "manual_intervention_required",
                "next_safe_action": "pause",
                "loop_blocked_reason": "existing_open_pr_detected",
                "resumable": True,
                "terminal": False,
                "policy_status": "blocked",
                "policy_blocked": True,
                "policy_manual_required": True,
                "policy_replan_required": False,
                "policy_resume_allowed": True,
                "policy_terminal": False,
                "policy_primary_blocker_class": "remote_github",
                "policy_primary_action": "proceed_to_pr",
                "policy_allowed_actions": ["inspect", "signal_recollect"],
                "policy_disallowed_actions": ["proceed_to_pr"],
            }
        )
        self.assertIn("operator_posture_summary", compact)
        self.assertIn("operator_primary_blocker_class", compact)
        self.assertIn("operator_primary_action", compact)
        self.assertIn("operator_resume_status", compact)
        self.assertIn("operator_next_safe_posture", compact)
        self.assertIn("objective_contract_present", compact)
        self.assertIn("objective_contract_status", compact)
        self.assertIn("objective_acceptance_status", compact)
        self.assertIn("objective_scope_status", compact)
        self.assertIn("objective_required_artifacts_status", compact)
        self.assertIn("completion_contract_present", compact)
        self.assertIn("completion_status", compact)
        self.assertIn("done_status", compact)
        self.assertIn("safe_closure_status", compact)
        self.assertIn("completion_evidence_status", compact)
        self.assertIn("completion_blocked_reason", compact)
        self.assertIn("completion_manual_required", compact)
        self.assertIn("completion_replan_required", compact)
        self.assertIn("completion_lifecycle_alignment_status", compact)
        self.assertIn("approval_transport_present", compact)
        self.assertIn("approval_status", compact)
        self.assertIn("approval_decision", compact)
        self.assertIn("approval_scope", compact)
        self.assertIn("approved_action", compact)
        self.assertIn("approval_required", compact)
        self.assertIn("approval_transport_status", compact)
        self.assertIn("approval_compatibility_status", compact)
        self.assertIn("approval_blocked_reason", compact)
        self.assertIn("reconcile_contract_present", compact)
        self.assertIn("reconcile_status", compact)
        self.assertIn("reconcile_decision", compact)
        self.assertIn("reconcile_alignment_status", compact)
        self.assertIn("reconcile_primary_mismatch", compact)
        self.assertIn("reconcile_blocked_reason", compact)
        self.assertIn("reconcile_waiting_on_truth", compact)
        self.assertIn("reconcile_manual_required", compact)
        self.assertIn("reconcile_replan_required", compact)
        self.assertIn("repair_suggestion_contract_present", compact)
        self.assertIn("repair_suggestion_status", compact)
        self.assertIn("repair_suggestion_decision", compact)
        self.assertIn("repair_suggestion_class", compact)
        self.assertIn("repair_suggestion_priority", compact)
        self.assertIn("repair_suggestion_confidence", compact)
        self.assertIn("repair_primary_reason", compact)
        self.assertIn("repair_manual_required", compact)
        self.assertIn("repair_replan_required", compact)
        self.assertIn("repair_truth_gathering_required", compact)
        self.assertIn("repair_plan_transport_present", compact)
        self.assertIn("repair_plan_status", compact)
        self.assertIn("repair_plan_decision", compact)
        self.assertIn("repair_plan_class", compact)
        self.assertIn("repair_plan_priority", compact)
        self.assertIn("repair_plan_confidence", compact)
        self.assertIn("repair_plan_target_surface", compact)
        self.assertIn("repair_plan_candidate_action", compact)
        self.assertIn("repair_plan_primary_reason", compact)
        self.assertIn("repair_plan_manual_required", compact)
        self.assertIn("repair_plan_replan_required", compact)
        self.assertIn("repair_plan_truth_gathering_required", compact)
        self.assertIn("repair_approval_binding_present", compact)
        self.assertIn("repair_approval_binding_status", compact)
        self.assertIn("repair_approval_binding_decision", compact)
        self.assertIn("repair_approval_binding_scope", compact)
        self.assertIn("repair_approval_binding_validity", compact)
        self.assertIn("repair_approval_binding_compatibility_status", compact)
        self.assertIn("repair_approval_binding_primary_reason", compact)
        self.assertIn("repair_approval_binding_manual_required", compact)
        self.assertIn("repair_approval_binding_replan_required", compact)
        self.assertIn("repair_approval_binding_truth_gathering_required", compact)
        self.assertIn("execution_authorization_gate_present", compact)
        self.assertIn("execution_authorization_status", compact)
        self.assertIn("execution_authorization_decision", compact)
        self.assertIn("execution_authorization_scope", compact)
        self.assertIn("execution_authorization_validity", compact)
        self.assertIn("execution_authorization_confidence", compact)
        self.assertIn("execution_authorization_primary_reason", compact)
        self.assertIn("execution_authorization_manual_required", compact)
        self.assertIn("execution_authorization_replan_required", compact)
        self.assertIn("execution_authorization_truth_gathering_required", compact)
        self.assertIn("bounded_execution_bridge_present", compact)
        self.assertIn("bounded_execution_status", compact)
        self.assertIn("bounded_execution_decision", compact)
        self.assertIn("bounded_execution_scope", compact)
        self.assertIn("bounded_execution_validity", compact)
        self.assertIn("bounded_execution_confidence", compact)
        self.assertIn("bounded_execution_primary_reason", compact)
        self.assertIn("bounded_execution_manual_required", compact)
        self.assertIn("bounded_execution_replan_required", compact)
        self.assertIn("bounded_execution_truth_gathering_required", compact)
        self.assertIn("verification_closure_contract_present", compact)
        self.assertIn("verification_status", compact)
        self.assertIn("verification_outcome", compact)
        self.assertIn("verification_validity", compact)
        self.assertIn("verification_confidence", compact)
        self.assertIn("verification_primary_reason", compact)
        self.assertIn("objective_satisfaction_status", compact)
        self.assertIn("completion_satisfaction_status", compact)
        self.assertIn("closure_status", compact)
        self.assertIn("closure_decision", compact)
        self.assertIn("objective_satisfied", compact)
        self.assertIn("completion_satisfied", compact)
        self.assertIn("safely_closable", compact)
        self.assertIn("manual_closure_required", compact)
        self.assertIn("closure_followup_required", compact)
        self.assertIn("external_truth_required", compact)
        self.assertIn("lifecycle_closure_status", compact)
        self.assertIn("lifecycle_safely_closed", compact)
        self.assertIn("lifecycle_terminal", compact)
        self.assertIn("lifecycle_resumable", compact)
        self.assertIn("lifecycle_manual_required", compact)
        self.assertIn("lifecycle_replan_required", compact)
        self.assertIn("lifecycle_execution_complete_not_closed", compact)
        self.assertIn("lifecycle_rollback_complete_not_closed", compact)
        self.assertIn("lifecycle_primary_closure_issue", compact)
        self.assertIn("lifecycle_stop_class", compact)
        self.assertNotIn("lifecycle_blocked_reasons", compact)
        self.assertNotIn("reconcile_blocked_reasons", compact)
        self.assertNotIn("repair_reason_codes", compact)
        self.assertNotIn("repair_plan_reason_codes", compact)
        self.assertNotIn("repair_plan_blocked_reasons", compact)
        self.assertNotIn("repair_approval_binding_reason_codes", compact)
        self.assertNotIn("repair_approval_binding_blocked_reasons", compact)
        self.assertNotIn("execution_authorization_reason_codes", compact)
        self.assertNotIn("execution_authorization_blocked_reasons", compact)
        self.assertNotIn("bounded_execution_reason_codes", compact)
        self.assertNotIn("bounded_execution_blocked_reasons", compact)
        self.assertNotIn("verification_reason_codes", compact)
        self.assertNotIn("operator_guidance_summary", compact)
        self.assertNotIn("operator_safe_actions_summary", compact)
        self.assertNotIn("operator_unsafe_actions_summary", compact)
        self.assertNotIn("objective_source_status", compact)
        self.assertFalse(is_manifest_summary_safe_field("operator_guidance_summary"))
        contract = build_manifest_run_state_summary_contract_surface()
        self.assertEqual(contract["compact_summary_field"], "run_state_summary_compact")
        self.assertEqual(contract["compatibility_summary_field"], "run_state_summary")
        self.assertEqual(
            contract["compatibility_summary_mode"],
            "alias_to_compact_deprecated_verbose",
        )
        self.assertIn("operator_guidance_summary", contract["rendering_only_operator_fields"])
        self.assertIn("lifecycle_closure_status", contract["lifecycle_summary_safe_fields"])
        self.assertEqual(
            set(contract["completion_summary_safe_fields"]),
            set(COMPLETION_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(contract["approval_summary_safe_fields"]),
            set(APPROVAL_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(contract["reconcile_summary_safe_fields"]),
            set(RECONCILE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(contract["repair_suggestion_summary_safe_fields"]),
            set(REPAIR_SUGGESTION_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(contract["repair_plan_transport_summary_safe_fields"]),
            set(REPAIR_PLAN_TRANSPORT_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(contract["repair_approval_binding_summary_safe_fields"]),
            set(REPAIR_APPROVAL_BINDING_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(contract["execution_authorization_summary_safe_fields"]),
            set(EXECUTION_AUTHORIZATION_GATE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(contract["bounded_execution_summary_safe_fields"]),
            set(BOUNDED_EXECUTION_BRIDGE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(contract["execution_result_summary_safe_fields"]),
            set(EXECUTION_RESULT_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(contract["verification_closure_summary_safe_fields"]),
            set(VERIFICATION_CLOSURE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(contract["retry_reentry_loop_summary_safe_fields"]),
            set(RETRY_REENTRY_LOOP_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(contract["endgame_closure_summary_safe_fields"]),
            set(ENDGAME_CLOSURE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(contract["loop_hardening_summary_safe_fields"]),
            set(LOOP_HARDENING_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(contract["lane_stabilization_summary_safe_fields"]),
            set(LANE_STABILIZATION_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(contract["observability_summary_safe_fields"]),
            set(OBSERVABILITY_ROLLUP_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(contract["failure_bucketing_hardening_summary_safe_fields"]),
            set(FAILURE_BUCKETING_HARDENING_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(contract["artifact_retention_summary_safe_fields"]),
            set(ARTIFACT_RETENTION_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(contract["fleet_safety_control_summary_safe_fields"]),
            set(FLEET_SAFETY_CONTROL_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )
        self.assertEqual(
            set(contract["approval_email_delivery_summary_safe_fields"]),
            set(APPROVAL_EMAIL_DELIVERY_RUN_STATE_SUMMARY_SAFE_FIELDS),
        )

    def test_contract_artifact_index_is_deterministic_and_compact(self) -> None:
        paths = {
            "objective_contract": "/tmp/objective_contract.json",
            "completion_contract": "/tmp/completion_contract.json",
            "approval_transport": "/tmp/approval_transport.json",
        }
        summaries = {
            "objective_contract": {"objective_contract_present": True},
            "completion_contract": {"completion_contract_present": True},
            "approval_transport": {"approval_transport_present": True},
        }
        payload_a = build_contract_artifact_index(paths_by_role=paths, summaries_by_role=summaries)
        payload_b = build_contract_artifact_index(paths_by_role=paths, summaries_by_role=summaries)
        self.assertEqual(payload_a, payload_b)
        self.assertEqual(
            list(payload_a.keys()),
            ["objective_contract", "completion_contract", "approval_transport"],
        )
        self.assertEqual(payload_a["objective_contract"]["path"], "/tmp/objective_contract.json")
        self.assertEqual(
            payload_a["completion_contract"]["summary"],
            {"completion_contract_present": True},
        )
        self.assertNotIn("reconcile_contract", payload_a)
        self.assertEqual(list(CONTRACT_ARTIFACT_ROLES)[0], "objective_contract")

    def test_manifest_summary_selector_is_stable_when_optional_operator_fields_are_absent(self) -> None:
        compact = select_manifest_run_state_summary_compact(
            {
                "state": "decision_in_progress",
                "loop_state": "runnable_waiting",
                "next_safe_action": "continue_waiting",
                "policy_status": "allowed",
                "policy_resume_allowed": True,
                "policy_terminal": False,
            }
        )
        self.assertEqual(compact["operator_primary_blocker_class"], "none")
        self.assertEqual(compact["operator_primary_action"], "")
        self.assertEqual(compact["operator_resume_status"], "resumable")
        self.assertEqual(compact["operator_posture_summary"], "safe_to_continue")
        self.assertEqual(compact["lifecycle_closure_status"], "stopped_resumable")
        self.assertFalse(compact["lifecycle_safely_closed"])
        self.assertTrue(compact["lifecycle_resumable"])
        self.assertIn(compact["completion_status"], COMPLETION_STATUSES)
        self.assertIn(compact["done_status"], DONE_STATUSES)
        self.assertIn(compact["safe_closure_status"], SAFE_CLOSURE_STATUSES)

    def test_runner_persists_rollback_progression_checkpoints_when_execution_attempted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            self._shrink_to_single_pr_slice(artifacts_dir)
            out_dir = root / "artifacts" / "executions"
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=_RecordingDryRunTransport()))
            mocked_payload = {
                "schema_version": "v1",
                "unit_id": "project-planned-exec-pr-01",
                "execution_type": "rollback_execution",
                "rollback_mode": "local_commit_only",
                "status": "succeeded",
                "summary": "mocked rollback success",
                "started_at": "2026-04-18T00:00:00",
                "finished_at": "2026-04-18T00:00:01",
                "trigger_reason": "rollback_required",
                "source_execution_state_summary": {},
                "resulting_commit_sha": "f" * 40,
                "resulting_pr_state": "unchanged",
                "resulting_branch_state": {},
                "command_summary": {},
                "failure_reason": "",
                "manual_intervention_required": False,
                "replan_required": True,
                "automatic_continuation_blocked": True,
                "blocking_reasons": [],
                "attempted": True,
            }
            with patch(
                "automation.orchestration.planned_execution_runner._execute_bounded_rollback",
                return_value=mocked_payload,
            ):
                manifest = runner.run(
                    artifacts_input_dir=artifacts_dir,
                    output_dir=out_dir,
                    dry_run=True,
                    stop_on_failure=True,
                )
            first = manifest["pr_units"][0]
            progression = json.loads(Path(first["unit_progression_path"]).read_text(encoding="utf-8"))
            run_state_payload = json.loads(Path(manifest["run_state_path"]).read_text(encoding="utf-8"))

        states = [entry["state"] for entry in progression["checkpoints"]]
        self.assertIn("rollback_execution_started", states)
        self.assertIn("rollback_executed", states)
        self.assertEqual(first["rollback_execution_summary"]["status"], "succeeded")
        self.assertEqual(first["decision_summary"]["rollback_execution_status"], "succeeded")
        self.assertTrue(run_state_payload["rollback_execution_succeeded"])
        self.assertTrue(run_state_payload["rollback_replan_required"])

    def test_invalid_cli_input_handling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = root / "missing_artifacts"
            out_dir = root / "out"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(self._script_path()),
                    "--artifacts-dir",
                    str(artifacts_dir),
                    "--out-dir",
                    str(out_dir),
                    "--json",
                ],
                capture_output=True,
                text=True,
                cwd=self._repo_root(),
            )

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("artifacts directory does not exist", proc.stderr)

    def test_invalid_live_transport_gate_fails_non_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "out"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(self._script_path()),
                    "--artifacts-dir",
                    str(artifacts_dir),
                    "--out-dir",
                    str(out_dir),
                    "--transport-mode",
                    "live",
                    "--repo-path",
                    str(self._repo_root()),
                    "--json",
                ],
                capture_output=True,
                text=True,
                cwd=self._repo_root(),
            )

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("--enable-live-transport", proc.stderr)

    def test_manifest_paths_and_status_fields_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=_RecordingDryRunTransport()))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )

            for entry in manifest["pr_units"]:
                self.assertIn("compiled_prompt_path", entry)
                self.assertIn("bounded_step_contract_path", entry)
                self.assertIn("pr_implementation_prompt_contract_path", entry)
                self.assertIn("result_path", entry)
                self.assertIn("receipt_path", entry)
                self.assertIn("unit_progression_path", entry)
                self.assertIn("unit_progression_state", entry)
                self.assertIn("checkpoint_decision_path", entry)
                self.assertIn("commit_decision_path", entry)
                self.assertIn("merge_decision_path", entry)
                self.assertIn("rollback_decision_path", entry)
                self.assertIn("commit_execution_path", entry)
                self.assertIn("push_execution_path", entry)
                self.assertIn("pr_execution_path", entry)
                self.assertIn("merge_execution_path", entry)
                self.assertIn("rollback_execution_path", entry)
                self.assertIn("checkpoint_summary", entry)
                self.assertIn("commit_execution_summary", entry)
                self.assertIn("push_execution_summary", entry)
                self.assertIn("pr_execution_summary", entry)
                self.assertIn("merge_execution_summary", entry)
                self.assertIn("rollback_execution_summary", entry)
                self.assertIn("decision_summary", entry)
                self.assertIn("status", entry)
                self.assertIn("commit_readiness_status", entry["decision_summary"])
                self.assertIn("merge_readiness_status", entry["decision_summary"])
                self.assertIn("rollback_readiness_status", entry["decision_summary"])
                self.assertIn("commit_readiness_next_action", entry["decision_summary"])
                self.assertIn("merge_readiness_next_action", entry["decision_summary"])
                self.assertIn("rollback_readiness_next_action", entry["decision_summary"])
                self.assertIn("commit_execution_status", entry["decision_summary"])
                self.assertIn("push_execution_status", entry["decision_summary"])
                self.assertIn("pr_execution_status", entry["decision_summary"])
                self.assertIn("merge_execution_status", entry["decision_summary"])
                self.assertIn("rollback_execution_status", entry["decision_summary"])
                self.assertIn(
                    "commit_execution_manual_intervention_required",
                    entry["decision_summary"],
                )
                self.assertIn(
                    "push_execution_manual_intervention_required",
                    entry["decision_summary"],
                )
                self.assertIn(
                    "pr_execution_manual_intervention_required",
                    entry["decision_summary"],
                )
                self.assertIn(
                    "merge_execution_manual_intervention_required",
                    entry["decision_summary"],
                )
                self.assertIn(
                    "rollback_execution_manual_intervention_required",
                    entry["decision_summary"],
                )
                self.assertTrue(Path(entry["compiled_prompt_path"]).exists())
                self.assertTrue(Path(entry["bounded_step_contract_path"]).exists())
                self.assertTrue(Path(entry["pr_implementation_prompt_contract_path"]).exists())
                self.assertTrue(Path(entry["result_path"]).exists())
                self.assertTrue(Path(entry["receipt_path"]).exists())
                self.assertTrue(Path(entry["unit_progression_path"]).exists())
                self.assertTrue(Path(entry["checkpoint_decision_path"]).exists())
                self.assertTrue(Path(entry["commit_decision_path"]).exists())
                self.assertTrue(Path(entry["merge_decision_path"]).exists())
                self.assertTrue(Path(entry["rollback_decision_path"]).exists())
                self.assertTrue(Path(entry["commit_execution_path"]).exists())
                self.assertTrue(Path(entry["push_execution_path"]).exists())
                self.assertTrue(Path(entry["pr_execution_path"]).exists())
                self.assertTrue(Path(entry["merge_execution_path"]).exists())
                self.assertTrue(Path(entry["rollback_execution_path"]).exists())
            self.assertTrue(Path(manifest["action_handoff_path"]).exists())
            self.assertTrue(Path(manifest["run_state_path"]).exists())

    def test_unit_progression_checkpoint_surface_is_explicit_and_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            transport = _RecordingLiveTransport()
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=transport))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=False,
                stop_on_failure=True,
            )
            first = manifest["pr_units"][0]
            progression = json.loads(Path(first["unit_progression_path"]).read_text(encoding="utf-8"))
            checkpoints = progression["checkpoints"]
            states = [entry["state"] for entry in checkpoints]

        self.assertEqual(progression["schema_version"], "v1")
        self.assertEqual(states[:4], ["planned", "prompt_ready", "execution_ready", "execution_completed"])
        self.assertIn("decision_ready", states)
        self.assertIn("checkpoint_evaluated", states)
        self.assertIn("commit_evaluated", states)
        self.assertIn("merge_evaluated", states)
        self.assertIn("rollback_evaluated", states)
        self.assertIn("reviewed", states)
        self.assertEqual(progression["current_state"], "advanced")

    def test_result_shape_compatibility_with_current_expectations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"
            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=_RecordingDryRunTransport()))
            manifest = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )
            first = manifest["pr_units"][0]
            payload = json.loads(Path(first["result_path"]).read_text(encoding="utf-8"))

        self.assertIn("job_id", payload)
        self.assertIn("pr_id", payload)
        self.assertIn("changed_files", payload)
        self.assertIn("execution", payload)
        self.assertIn("additions", payload)
        self.assertIn("deletions", payload)
        self.assertIn("generated_patch_summary", payload)
        self.assertIn("failure_type", payload)
        self.assertIn("failure_message", payload)
        self.assertIn("cost", payload)
        self.assertIn("verify", payload["execution"])

    def test_one_run_one_decision_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            runner = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=_RecordingDryRunTransport()))
            manifest_a = runner.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
                retry_context={
                    "prior_attempt_count": 0,
                    "prior_retry_class": None,
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 1,
                },
            )
            decision_a = json.loads(Path(manifest_a["next_action_path"]).read_text(encoding="utf-8"))
            handoff_a = json.loads(Path(manifest_a["action_handoff_path"]).read_text(encoding="utf-8"))

            runner_b = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=_RecordingDryRunTransport()))
            manifest_b = runner_b.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
                retry_context={
                    "prior_attempt_count": 0,
                    "prior_retry_class": None,
                    "missing_signal_count": 0,
                    "retry_budget_remaining": 1,
                },
            )
            decision_b = json.loads(Path(manifest_b["next_action_path"]).read_text(encoding="utf-8"))
            handoff_b = json.loads(Path(manifest_b["action_handoff_path"]).read_text(encoding="utf-8"))

        self.assertEqual(decision_a["next_action"], decision_b["next_action"])
        self.assertEqual(decision_a["reason"], decision_b["reason"])
        self.assertEqual(decision_a["updated_retry_context"], decision_b["updated_retry_context"])
        self.assertEqual(handoff_a["next_action"], handoff_b["next_action"])
        self.assertEqual(handoff_a["updated_retry_context"], handoff_b["updated_retry_context"])
        self.assertEqual(handoff_a["action_consumable"], handoff_b["action_consumable"])

    def test_retry_context_continuity_across_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_dir = self._write_planning_artifacts(root)
            out_dir = root / "artifacts" / "executions"

            failing_transport_a = _RecordingDryRunTransport(
                status_by_pr_id={"project-planned-exec-pr-01": "failed"}
            )
            runner_a = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=failing_transport_a))
            manifest_a = runner_a.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )
            handoff_a = json.loads(Path(manifest_a["action_handoff_path"]).read_text(encoding="utf-8"))

            failing_transport_b = _RecordingDryRunTransport(
                status_by_pr_id={"project-planned-exec-pr-01": "failed"}
            )
            runner_b = PlannedExecutionRunner(adapter=CodexExecutorAdapter(transport=failing_transport_b))
            manifest_b = runner_b.run(
                artifacts_input_dir=artifacts_dir,
                output_dir=out_dir,
                dry_run=True,
                stop_on_failure=True,
            )
            handoff_b = json.loads(Path(manifest_b["action_handoff_path"]).read_text(encoding="utf-8"))
            run_root = out_dir / manifest_b["job_id"]
            handoff_files = sorted(run_root.glob("action_handoff*.json"))

        self.assertEqual(handoff_a["next_action"], "same_prompt_retry")
        self.assertEqual(handoff_b["next_action"], "escalate_to_human")
        self.assertEqual(len(handoff_files), 1)


if __name__ == "__main__":
    unittest.main()

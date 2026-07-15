from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import shutil
import subprocess
import sys
import time
from typing import Any
from typing import Callable
from typing import Mapping
from typing import Sequence
from urllib import error as urllib_error
from urllib import request as urllib_request

from automation.control.action_handoff import build_action_handoff_payload
from automation.control.next_action_controller import evaluate_next_action_from_run_dir
from automation.control.retry_context_store import FileRetryContextStore
from automation.execution.codex_executor_adapter import CodexExecutorAdapter
from automation.orchestration.approval_transport import build_approval_run_state_summary_surface
from automation.orchestration.approval_transport import build_approval_transport_surface
from automation.orchestration.artifact_index import build_contract_artifact_index
from automation.orchestration.completion_contract import build_completion_contract_surface
from automation.orchestration.completion_contract import build_completion_run_state_summary_surface
from automation.orchestration.execution_authorization_gate import build_execution_authorization_gate_run_state_summary_surface
from automation.orchestration.execution_authorization_gate import build_execution_authorization_gate_surface
from automation.orchestration.execution_result_contract import build_execution_result_contract_run_state_summary_surface
from automation.orchestration.execution_result_contract import build_execution_result_contract_surface
from automation.orchestration.verification_closure_contract import build_verification_closure_contract_surface
from automation.orchestration.verification_closure_contract import build_verification_closure_run_state_summary_surface
from automation.orchestration.retry_reentry_loop_contract import build_retry_reentry_loop_contract_surface
from automation.orchestration.retry_reentry_loop_contract import build_retry_reentry_loop_run_state_summary_surface
from automation.orchestration.endgame_closure_contract import build_endgame_closure_contract_surface
from automation.orchestration.endgame_closure_contract import build_endgame_closure_run_state_summary_surface
from automation.orchestration.loop_hardening_contract import build_loop_hardening_contract_surface
from automation.orchestration.loop_hardening_contract import build_loop_hardening_run_state_summary_surface
from automation.orchestration.lane_stabilization_contract import build_lane_stabilization_contract_surface
from automation.orchestration.lane_stabilization_contract import build_lane_stabilization_run_state_summary_surface
from automation.orchestration.observability_rollup import build_failure_bucket_rollup_summary_surface
from automation.orchestration.observability_rollup import build_failure_bucket_rollup_surface
from automation.orchestration.observability_rollup import build_fleet_run_rollup_summary_surface
from automation.orchestration.observability_rollup import build_fleet_run_rollup_surface
from automation.orchestration.observability_rollup import build_observability_rollup_contract_summary_surface
from automation.orchestration.observability_rollup import build_observability_rollup_contract_surface
from automation.orchestration.observability_rollup import build_observability_rollup_run_state_summary_surface
from automation.orchestration.failure_bucketing_hardening import build_failure_bucketing_hardening_run_state_summary_surface
from automation.orchestration.failure_bucketing_hardening import build_failure_bucketing_hardening_summary_surface
from automation.orchestration.failure_bucketing_hardening import build_failure_bucketing_hardening_contract_surface
from automation.orchestration.artifact_retention import build_artifact_retention_contract_surface
from automation.orchestration.artifact_retention import build_artifact_retention_run_state_summary_surface
from automation.orchestration.artifact_retention import build_artifact_retention_summary_surface
from automation.orchestration.artifact_retention import build_retention_manifest_summary_surface
from automation.orchestration.artifact_retention import build_retention_manifest_surface
from automation.orchestration.fleet_safety_control import build_fleet_safety_control_contract_surface
from automation.orchestration.fleet_safety_control import build_fleet_safety_control_run_state_summary_surface
from automation.orchestration.fleet_safety_control import build_fleet_safety_control_summary_surface
from automation.orchestration.approval_email_delivery import build_approval_email_delivery_contract_surface
from automation.orchestration.approval_email_delivery import build_approval_email_delivery_run_state_summary_surface
from automation.orchestration.approval_email_delivery import build_approval_email_delivery_summary_surface
from automation.orchestration.approval_runtime_policy import build_approval_runtime_rules_contract_surface
from automation.orchestration.approval_runtime_policy import build_approval_runtime_rules_run_state_summary_surface
from automation.orchestration.approval_runtime_policy import build_approval_runtime_rules_summary_surface
from automation.orchestration.approval_delivery_adapter import build_approval_delivery_handoff_contract_surface
from automation.orchestration.approval_delivery_adapter import build_approval_delivery_handoff_run_state_summary_surface
from automation.orchestration.approval_delivery_adapter import build_approval_delivery_handoff_summary_surface
from automation.orchestration.approval_response_ingest import build_approved_restart_contract_surface
from automation.orchestration.approval_response_ingest import build_approved_restart_run_state_summary_surface
from automation.orchestration.approval_response_ingest import build_approved_restart_summary_surface
from automation.orchestration.approval_response_ingest import build_approval_response_contract_surface
from automation.orchestration.approval_response_ingest import build_approval_response_run_state_summary_surface
from automation.orchestration.approval_response_ingest import build_approval_response_summary_surface
from automation.orchestration.approval_safety import build_approval_safety_contract_surface
from automation.orchestration.approval_safety import build_approval_safety_run_state_summary_surface
from automation.orchestration.approval_safety import build_approval_safety_summary_surface
from automation.orchestration.bounded_execution_bridge import build_bounded_execution_bridge_run_state_summary_surface
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

from automation.orchestration.planned_runner.project_browser.constants import (
    _PROJECT_BROWSER_ASSIMILATED_DECISIONS,
    _PROJECT_BROWSER_ASSIMILATED_RISK_LEVELS,
    _PROJECT_BROWSER_AUTONOMOUS_ACTION_DUPLICATE_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_ACTION_FINGERPRINT_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_ACTION_IDENTITY_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_ACTION_KINDS,
    _PROJECT_BROWSER_AUTONOMOUS_ACTION_RECEIPT_KINDS,
    _PROJECT_BROWSER_AUTONOMOUS_ACTION_RECEIPT_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_CONTINUATION_BLOCK_REASONS,
    _PROJECT_BROWSER_AUTONOMOUS_CONTINUATION_GATE_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_CONTINUATION_NEXT_ACTIONS,
    _PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_ACTIONS,
    _PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_ACTION_SOURCES,
    _PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_RECEIPT_KINDS,
    _PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_RECEIPT_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_RUNTIME_POSTURES,
    _PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_STOP_REASONS,
    _PROJECT_BROWSER_AUTONOMOUS_DEV_ASSIMILATION_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_DEV_NEXT_ACTIONS,
    _PROJECT_BROWSER_AUTONOMOUS_DEV_OUTCOMES,
    _PROJECT_BROWSER_AUTONOMOUS_DEV_RUNTIME_POSTURES,
    _PROJECT_BROWSER_AUTONOMOUS_DEV_STOP_REASONS,
    _PROJECT_BROWSER_AUTONOMOUS_DRAFT_RUNTIME_POSTURES,
    _PROJECT_BROWSER_AUTONOMOUS_DUPLICATE_POLICY_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_DUPLICATE_REASONS,
    _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_BRIDGE_REASONS,
    _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_BRIDGE_RUNTIME_POSTURES,
    _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_BRIDGE_SOURCE_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_BRIDGE_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS,
    _PROJECT_BROWSER_AUTONOMOUS_GATE_RUNTIME_POSTURES,
    _PROJECT_BROWSER_AUTONOMOUS_LEDGER_RUNTIME_POSTURES,
    _PROJECT_BROWSER_AUTONOMOUS_MANUAL_OVERRIDE_REASONS,
    _PROJECT_BROWSER_AUTONOMOUS_MANUAL_OVERRIDE_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_MD_UPDATE_BLOCK_REASONS,
    _PROJECT_BROWSER_AUTONOMOUS_MD_UPDATE_COMMAND_DRAFT_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_MD_UPDATE_DRAFT_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_MD_UPDATE_KINDS,
    _PROJECT_BROWSER_AUTONOMOUS_NEXT_PROMPT_BLOCK_REASONS,
    _PROJECT_BROWSER_AUTONOMOUS_NEXT_PROMPT_DRAFT_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_NEXT_PROMPT_KINDS,
    _PROJECT_BROWSER_AUTONOMOUS_NEXT_PROMPT_SCOPES,
    _PROJECT_BROWSER_AUTONOMOUS_NEXT_PROMPT_SOURCES,
    _PROJECT_BROWSER_AUTONOMOUS_RETRY_BUDGET_POSTURES,
    _PROJECT_BROWSER_AUTONOMOUS_RUN_LEDGER_ENTRY_KINDS,
    _PROJECT_BROWSER_AUTONOMOUS_RUN_LEDGER_ENTRY_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_RUN_LEDGER_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_SAFETY_RUNTIME_POSTURES,
    _PROJECT_BROWSER_AUTONOMOUS_SAFETY_SWITCH_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_SAFE_STOP_REASONS,
    _PROJECT_BROWSER_AUTONOMOUS_SAFE_STOP_STATUSES,
    _PROJECT_BROWSER_CHATGPT_PAGE_STATUSES,
    _PROJECT_BROWSER_CHAT_ROTATION_NEAR_THRESHOLD,
    _PROJECT_BROWSER_CHAT_ROTATION_TARGET,
    _PROJECT_BROWSER_CHAT_TURN_POSTURES,
    _PROJECT_BROWSER_COMMAND_BLOCK_REASONS,
    _PROJECT_BROWSER_COMMAND_PRECONDITION_VALUES,
    _PROJECT_BROWSER_COMMAND_QUEUE_MODES,
    _PROJECT_BROWSER_COMMAND_QUEUE_STATUSES,
    _PROJECT_BROWSER_COMMAND_RECEIPT_KINDS,
    _PROJECT_BROWSER_COMMAND_RECEIPT_RESULTS,
    _PROJECT_BROWSER_COMMAND_RECEIPT_STATUSES,
    _PROJECT_BROWSER_COMMAND_RUNTIME_POSTURES,
    _PROJECT_BROWSER_COMMAND_SOURCES,
    _PROJECT_BROWSER_COMMAND_TYPES,
    _PROJECT_BROWSER_CONTEXT_STATUSES,
    _PROJECT_BROWSER_CONTINUATION_THRESHOLD,
    _PROJECT_BROWSER_DECISIONS,
    _PROJECT_BROWSER_DOM_PROBE_BLOCK_REASONS,
    _PROJECT_BROWSER_DOM_READINESS_STATUSES,
    _PROJECT_BROWSER_EXECUTION_BLOCK_REASONS,
    _PROJECT_BROWSER_EXECUTION_HANDOFF_KINDS,
    _PROJECT_BROWSER_EXECUTION_HANDOFF_STATUSES,
    _PROJECT_BROWSER_EXECUTION_PREREQUISITE_VALUES,
    _PROJECT_BROWSER_EXECUTION_RECEIPT_PARSE_KINDS,
    _PROJECT_BROWSER_EXECUTION_RECEIPT_PARSE_STATUSES,
    _PROJECT_BROWSER_EXECUTION_RESULT_STATUSES,
    _PROJECT_BROWSER_EXECUTOR_BLOCK_REASONS,
    _PROJECT_BROWSER_EXECUTOR_CAPABILITY_POSTURES,
    _PROJECT_BROWSER_EXECUTOR_CONTRACT_VERSION,
    _PROJECT_BROWSER_EXECUTOR_INTERFACE_CONTRACT_VERSION,
    _PROJECT_BROWSER_EXECUTOR_INTERFACE_STATUSES,
    _PROJECT_BROWSER_EXECUTOR_MODES,
    _PROJECT_BROWSER_EXECUTOR_RECEIPT_KINDS,
    _PROJECT_BROWSER_EXECUTOR_RECEIPT_STATUSES,
    _PROJECT_BROWSER_HANDOFF_COMPILE_STATUSES,
    _PROJECT_BROWSER_HANDOFF_PAYLOAD_POSTURES,
    _PROJECT_BROWSER_HANDOFF_SECTION_NAMES,
    _PROJECT_BROWSER_HANDOFF_SUMMARY_POSTURES,
    _PROJECT_BROWSER_HANDOFF_TRIGGERS,
    _PROJECT_BROWSER_JSON_REQUIRED_FIELDS,
    _PROJECT_BROWSER_LAUNCH_BLOCK_REASONS,
    _PROJECT_BROWSER_LAUNCH_PREFLIGHT_MODES,
    _PROJECT_BROWSER_LAUNCH_PREFLIGHT_STATUSES,
    _PROJECT_BROWSER_LAUNCH_RECEIPT_KINDS,
    _PROJECT_BROWSER_LAUNCH_RECEIPT_KINDS_RUNTIME,
    _PROJECT_BROWSER_LAUNCH_RECEIPT_STATUSES,
    _PROJECT_BROWSER_LAUNCH_RECEIPT_STATUSES_RUNTIME,
    _PROJECT_BROWSER_LAUNCH_RUNTIME_POSTURES,
    _PROJECT_BROWSER_LAUNCH_STATUSES,
    _PROJECT_BROWSER_LOGIN_INTERRUPTION_STATUSES,
    _PROJECT_BROWSER_LOGIN_PREFLIGHT_POSTURES,
    _PROJECT_BROWSER_NEXT_ACTION_POSTURES,
    _PROJECT_BROWSER_ONE_COMMAND_EXECUTOR_RESULTS,
    _PROJECT_BROWSER_ONE_COMMAND_EXECUTOR_STATUSES,
    _PROJECT_BROWSER_ONE_COMMAND_RECEIPT_KINDS,
    _PROJECT_BROWSER_ONE_COMMAND_RECEIPT_STATUSES,
    _PROJECT_BROWSER_ONE_COMMAND_RUNTIME_POSTURES,
    _PROJECT_BROWSER_ONE_COMMAND_STOP_REASONS,
    _PROJECT_BROWSER_PAGE_OPEN_STATUSES,
    _PROJECT_BROWSER_PLAYWRIGHT_BOUNDARY_STATUSES,
    _PROJECT_BROWSER_PLAYWRIGHT_IMPORT_POSTURES,
    _PROJECT_BROWSER_PROMPT_CONTEXT_LEVELS,
    _PROJECT_BROWSER_PROMPT_FILL_BLOCK_REASONS,
    _PROJECT_BROWSER_PROMPT_FILL_RECEIPT_KINDS,
    _PROJECT_BROWSER_PROMPT_FILL_RECEIPT_STATUSES,
    _PROJECT_BROWSER_PROMPT_FILL_RUNTIME_POSTURES,
    _PROJECT_BROWSER_PROMPT_FILL_SOURCE_STATUSES,
    _PROJECT_BROWSER_PROMPT_FILL_STATUSES,
    _PROJECT_BROWSER_PROMPT_FILL_TARGET_STATUSES,
    _PROJECT_BROWSER_PROMPT_PAYLOAD_STATUSES,
    _PROJECT_BROWSER_PROMPT_SECTION_NAMES,
    _PROJECT_BROWSER_PROMPT_SEND_BLOCK_REASONS,
    _PROJECT_BROWSER_PROMPT_SEND_RECEIPT_KINDS,
    _PROJECT_BROWSER_PROMPT_SEND_RECEIPT_STATUSES,
    _PROJECT_BROWSER_PROMPT_SEND_RUNTIME_POSTURES,
    _PROJECT_BROWSER_PROMPT_SEND_STATUSES,
    _PROJECT_BROWSER_PROMPT_SEND_TARGET_STATUSES,
    _PROJECT_BROWSER_PROMPT_TOKEN_POSTURES,
    _PROJECT_BROWSER_PROOF_POSTURES,
    _PROJECT_BROWSER_RECOVERY_ACTIONS,
    _PROJECT_BROWSER_RECOVERY_BLOCK_REASONS,
    _PROJECT_BROWSER_RECOVERY_REASONS,
    _PROJECT_BROWSER_RECOVERY_RECEIPT_KINDS,
    _PROJECT_BROWSER_RECOVERY_RECEIPT_STATUSES,
    _PROJECT_BROWSER_RECOVERY_RUNTIME_POSTURES,
    _PROJECT_BROWSER_RECOVERY_STATUSES,
    _PROJECT_BROWSER_RESPONSE_ASSIMILATION_STATUSES,
    _PROJECT_BROWSER_RESPONSE_JSON_DECISION_STATUSES,
    _PROJECT_BROWSER_RESPONSE_JSON_PARSE_STATUSES,
    _PROJECT_BROWSER_RESPONSE_JSON_SCHEMA_STATUSES,
    _PROJECT_BROWSER_RESPONSE_PARSE_BLOCK_REASONS,
    _PROJECT_BROWSER_RESPONSE_PARSE_RUNTIME_POSTURES,
    _PROJECT_BROWSER_RESPONSE_READ_RECEIPT_KINDS,
    _PROJECT_BROWSER_RESPONSE_READ_RECEIPT_STATUSES,
    _PROJECT_BROWSER_RESPONSE_READ_STATUSES,
    _PROJECT_BROWSER_RESPONSE_RUNTIME_POSTURES,
    _PROJECT_BROWSER_RESPONSE_STATUSES,
    _PROJECT_BROWSER_RESPONSE_TEXT_STATUSES,
    _PROJECT_BROWSER_RESPONSE_WAIT_BLOCK_REASONS,
    _PROJECT_BROWSER_RESPONSE_WAIT_STATUSES,
    _PROJECT_BROWSER_RETRY_LIMIT,
    _PROJECT_BROWSER_RISK_LEVELS,
    _PROJECT_BROWSER_RUNTIME_BLOCK_REASONS,
    _PROJECT_BROWSER_SAME_PROMPT_RETRY_POLICIES,
    _PROJECT_BROWSER_SAME_PROMPT_RETRY_REASONS,
    _PROJECT_BROWSER_SCORE_POSTURES,
    _PROJECT_BROWSER_SELECTOR_PROBE_RECEIPT_KINDS,
    _PROJECT_BROWSER_SELECTOR_PROBE_RECEIPT_STATUSES,
    _PROJECT_BROWSER_SELECTOR_PROBE_STATUSES,
    _PROJECT_BROWSER_SELECTOR_REQUIRED_PROBE_TARGETS,
    _PROJECT_BROWSER_SELECTOR_RESOLVER_STATUSES,
    _PROJECT_BROWSER_SELECTOR_RUNTIME_POSTURES,
    _PROJECT_BROWSER_SELECTOR_TARGETS,
    _PROJECT_BROWSER_SELECTOR_TARGET_STATUSES,
    _PROJECT_BROWSER_SESSION_CONFIG_STATUSES,
    _PROJECT_BROWSER_SESSION_MODES,
    _PROJECT_BROWSER_TASK_ENVELOPE_STATUSES,
    _PROJECT_BROWSER_TASK_SCHEMA_REF,
    _PROJECT_BROWSER_TASK_STATUSES,
    _PROJECT_BROWSER_TASK_TYPES,
    _PROJECT_BROWSER_UI_FAILURE_STATUSES,
    _PROJECT_BROWSER_UI_HANDOFF_DEPENDENCY_POSTURES,
    _PROJECT_BROWSER_UI_READINESS_STATUSES,
    _PROJECT_BROWSER_UI_RECOVERY_ACTIONS,
    _PROJECT_BROWSER_UI_RECOVERY_CANDIDATES,
    _PROJECT_BROWSER_UI_RECOVERY_DECISION_STATUSES,
    _PROJECT_BROWSER_UI_RECOVERY_REASONS,
    _PROJECT_BROWSER_UI_RETRY_COUNT_POSTURES,
)
from automation.orchestration.planned_runner.utils import (
    _APPROVAL_SKIP_GATE_STATUSES,
    _APPROVE_COMMIT_TAG_ARTIFACT_RECONCILIATION_RECEIPT_PATH,
    _APPROVE_COMMIT_TAG_EXECUTION_COMMIT_MESSAGE,
    _APPROVE_COMMIT_TAG_EXECUTION_REPO_PATH,
    _APPROVE_COMMIT_TAG_EXECUTION_TAG_NAME,
    _AUTONOMY_BROWSER_ORCHESTRATOR_SPEC_REF,
    _BOUNDED_LOCAL_AUTONOMOUS_LOOP_DEFAULT_CURRENT_CYCLE_COUNT,
    _BOUNDED_LOCAL_AUTONOMOUS_LOOP_DEFAULT_MAX_CYCLE_COUNT,
    _BOUNDED_LOCAL_AUTONOMOUS_LOOP_EXPECTED_HEAD_TAG,
    _BOUNDED_LOCAL_LOOP_CONTROL_KEYS,
    _IMPLEMENTATION_PROMPT_STATUSES,
    _LOCAL_AUTONOMOUS_CONTINUATION_DECISION_PATH,
    _LOCAL_AUTONOMOUS_CONTINUATION_RECEIPT_PATH,
    _LOCAL_AUTONOMOUS_CONTINUATION_STATE_PATH,
    _LOCAL_AUTONOMOUS_CYCLE_V2_CURRENT_CYCLE,
    _LOCAL_AUTONOMOUS_CYCLE_V2_DECISION_PATH,
    _LOCAL_AUTONOMOUS_CYCLE_V2_MAX_CYCLES,
    _LOCAL_AUTONOMOUS_CYCLE_V2_RECEIPT_PATH,
    _LOCAL_AUTONOMOUS_CYCLE_V2_STATE_PATH,
    _LOCAL_AUTONOMOUS_LOOP_COMPLETION_SUMMARY_PATH,
    _LOCAL_AUTONOMOUS_NEXT_CYCLE_SELECTION_PATH,
    _LOCAL_BOUNDED_APPROVE_COMMIT_TAG_EXECUTION_RECEIPT_PATH,
    _LOCAL_BOUNDED_APPROVE_COMMIT_TAG_EXECUTION_RESULT_PATH,
    _LOCAL_BOUNDED_APPROVE_COMMIT_TAG_GATE_STATE_PATH,
    _LOCAL_BOUNDED_APPROVE_COMMIT_TAG_PLAN_PATH,
    _LOCAL_BOUNDED_APPROVE_COMMIT_TAG_TAG_NAME,
    _LOCAL_CODEX_EXEC_PLAN_COMMAND,
    _LOCAL_CODEX_ONE_SHOT_EXECUTION_HANDOFF_PATH,
    _LOCAL_CODEX_ONE_SHOT_EXECUTION_RECEIPT_PATH,
    _LOCAL_CODEX_ONE_SHOT_EXECUTION_RECEIPT_V2_PATH,
    _LOCAL_CODEX_ONE_SHOT_EXECUTION_RESULT_PATH,
    _LOCAL_CODEX_ONE_SHOT_EXECUTION_STDERR_PATH,
    _LOCAL_CODEX_ONE_SHOT_EXECUTION_STDOUT_PATH,
    _LOCAL_CODEX_ONE_SHOT_PROMPT_PATH,
    _LOCAL_CONTRACT_FIX_CYCLE_COORDINATION_DECISION_PATH,
    _LOCAL_CONTRACT_FIX_CYCLE_COORDINATION_RECEIPT_PATH,
    _LOCAL_CONTRACT_FIX_CYCLE_COORDINATION_STATE_PATH,
    _LOCAL_CONTRACT_FIX_CYCLE_EXECUTION_HANDOFF_PATH,
    _LOCAL_DAEMON_LITE_WRAPPER_DECISION_PATH,
    _LOCAL_DAEMON_LITE_WRAPPER_PLAN_PATH,
    _LOCAL_DAEMON_LITE_WRAPPER_RECEIPT_PATH,
    _LOCAL_DAEMON_LITE_WRAPPER_STATE_PATH,
    _LOCAL_END_TO_END_ONE_SHOT_EXPECTED_HEAD_TAG,
    _LOCAL_END_TO_END_ONE_SHOT_STEP_SELECTION_PATH,
    _LOCAL_NEXT_CYCLE_REENTRY_DECISION_PATH,
    _LOCAL_ONLY_AUTONOMOUS_LOOP_CLOSURE_DECISION_PATH,
    _LOCAL_ONLY_AUTONOMOUS_LOOP_CLOSURE_RECEIPT_PATH,
    _LOCAL_ONLY_AUTONOMOUS_LOOP_CLOSURE_STATE_PATH,
    _LOCAL_POST_CODEX_DIFF_CAPTURE_PATH,
    _LOCAL_POST_CODEX_DIFF_CAPTURE_RECEIPT_PATH,
    _LOCAL_POST_CODEX_EXECUTION_OUTCOME_PATH,
    _LOCAL_POST_CODEX_ROUTE_DECISION_PATH,
    _LOCAL_POST_COMMIT_CYCLE_CLOSURE_DECISION_PATH,
    _LOCAL_POST_COMMIT_CYCLE_CLOSURE_RECEIPT_PATH,
    _LOCAL_POST_COMMIT_CYCLE_CLOSURE_STATE_PATH,
    _LOCAL_POST_TARGETED_CONTRACT_FIX_DIFF_CAPTURE_PATH,
    _LOCAL_POST_TARGETED_CONTRACT_FIX_EXECUTION_OUTCOME_PATH,
    _LOCAL_POST_TARGETED_CONTRACT_FIX_REVIEW_RECEIPT_PATH,
    _LOCAL_POST_TARGETED_CONTRACT_FIX_ROUTE_DECISION_PATH,
    _LOCAL_TARGETED_CONTRACT_FIX_EXECUTION_RECEIPT_PATH,
    _LOCAL_TARGETED_CONTRACT_FIX_EXECUTION_RESULT_PATH,
    _LOCAL_TARGETED_CONTRACT_FIX_EXECUTION_STATE_PATH,
    _LOCAL_TARGETED_CONTRACT_FIX_EXECUTION_STDERR_PATH,
    _LOCAL_TARGETED_CONTRACT_FIX_EXECUTION_STDOUT_PATH,
    _LOCAL_TARGETED_CONTRACT_FIX_PROMPT_PATH,
    _LOCAL_TARGETED_CONTRACT_FIX_PROMPT_PLAN_PATH,
    _LOCAL_TARGETED_CONTRACT_FIX_PROMPT_RECEIPT_PATH,
    _LOCAL_TARGETED_CONTRACT_FIX_ROUTE_INTAKE_PATH,
    _LONG_RUNNING_STABILITY_STATUSES,
    _PROJECT_APPROVAL_REPLY_REQUIRED_POSTURES,
    _PROJECT_EXTERNAL_BOUNDARY_POSTURES,
    _PROJECT_EXTERNAL_BOUNDARY_STATUSES,
    _PROJECT_EXTERNAL_DEPENDENCY_POSTURES,
    _PROJECT_PR_QUEUE_STATUSES,
    _PROMPT365_DRY_RUN_BLOCKED_NEXT_ACTION,
    _PROMPT365_DRY_RUN_BLOCKED_REASON,
    _PROMPT365_DRY_RUN_MUTATION_DETECTED_NEXT_ACTION,
    _PROMPT365_DRY_RUN_MUTATION_DETECTED_REASON,
    _SELECTED_STEP_EXECUTION_ADAPTER_EXPECTED_HEAD_TAG,
    _SELECTED_STEP_EXECUTION_RESULT_ROUTE_CAPTURE_PATH,
    _SELECTED_STEP_EXECUTION_RESULT_ROUTE_DECISION_PATH,
    _SELECTED_STEP_EXECUTION_RESULT_ROUTE_RECEIPT_PATH,
    _SELECTED_STEP_LIVE_EXECUTION_EXPECTED_HEAD_TAG,
    _SELECTED_STEP_LIVE_EXECUTION_GATE_PATH,
    _SELECTED_STEP_LIVE_EXECUTION_RECEIPT_PATH,
    _SELECTED_STEP_LIVE_EXECUTION_RESULT_PATH,
    _TARGETED_FIX_POST_REENTRY_BOUNDED_CYCLE_DEFAULT_CURRENT_CYCLE_COUNT,
    _TARGETED_FIX_POST_REENTRY_BOUNDED_CYCLE_DEFAULT_MAX_CYCLE_COUNT,
    _as_int,
    _as_non_negative_int,
    _as_optional_int,
    _build_bounded_local_autonomous_loop_decision_state,
    _build_bounded_local_autonomous_loop_receipt_state,
    _build_bounded_local_autonomous_loop_state,
    _build_concrete_prompt298_goal_from_next_dev_slice,
    _build_dry_run_local_codex_one_shot_execution_result_state,
    _build_dry_run_selected_step_live_execution_gate_state,
    _build_dry_run_selected_step_live_execution_operation_state,
    _build_local_autonomous_continuation_artifacts,
    _build_local_autonomous_cycle_v2_decision,
    _build_local_autonomous_cycle_v2_receipt,
    _build_local_autonomous_cycle_v2_state,
    _build_local_bounded_approve_commit_tag_execution_artifacts,
    _build_local_codex_one_shot_execution_handoff_state,
    _build_local_codex_one_shot_execution_receipt,
    _build_local_codex_one_shot_execution_receipt_v2,
    _build_local_codex_one_shot_execution_result_state,
    _build_local_codex_one_shot_prompt_markdown,
    _build_local_contract_fix_cycle_coordination_artifacts,
    _build_local_daemon_lite_wrapper_artifacts,
    _build_local_end_to_end_controller_component_matrix_state,
    _build_local_end_to_end_controller_gap_report_state,
    _build_local_end_to_end_controller_readiness_boundary_state,
    _build_local_end_to_end_dry_run_plan_state,
    _build_local_end_to_end_dry_run_receipt_state,
    _build_local_end_to_end_dry_run_step_matrix_state,
    _build_local_end_to_end_one_shot_execution_gate_state,
    _build_local_end_to_end_one_shot_execution_receipt_state,
    _build_local_end_to_end_one_shot_step_selection_state,
    _build_local_only_autonomous_loop_closure_decision,
    _build_local_only_autonomous_loop_closure_receipt,
    _build_local_only_autonomous_loop_closure_state,
    _build_local_post_commit_cycle_closure_artifacts,
    _build_local_post_targeted_contract_fix_review_artifacts,
    _build_local_targeted_contract_fix_execution_artifacts,
    _build_local_targeted_contract_fix_prompt_artifacts,
    _build_one_cycle_post_execution_handoff,
    _build_one_cycle_review_handoff_decision_state,
    _build_remote_readiness_boundary_state,
    _build_remote_readiness_plan_state,
    _build_review_response_assimilation_state,
    _build_review_route_decision_state,
    _build_selected_step_execution_adapter_state,
    _build_selected_step_execution_plan_state,
    _build_selected_step_execution_receipt_state,
    _build_selected_step_execution_result_route_capture_state,
    _build_selected_step_execution_result_route_decision_state,
    _build_selected_step_execution_result_route_receipt_state,
    _build_selected_step_live_execution_gate_state,
    _build_selected_step_live_execution_receipt_state,
    _build_selected_step_live_execution_result_state,
    _build_targeted_fix_post_reentry_bounded_cycle_decision_state,
    _build_targeted_fix_post_reentry_bounded_cycle_receipt_state,
    _build_targeted_fix_post_reentry_bounded_cycle_state,
    _build_targeted_fix_post_reentry_cycle_closure_result_state,
    _build_targeted_fix_post_reentry_next_step_handoff_state,
    _build_targeted_fix_post_reentry_prompt_emission_state,
    _build_targeted_fix_post_reentry_review_assimilation_state,
    _build_targeted_fix_post_reentry_review_handoff_state,
    _build_targeted_fix_post_reentry_route_decision_state,
    _build_targeted_fix_post_reentry_route_executor_boundary_state,
    _build_targeted_fix_post_reentry_terminal_summary_state,
    _build_targeted_fix_prompt_boundary_state,
    _capture_targeted_fix_post_reentry_diff_state,
    _classify_project_browser_autonomous_duplicate_status,
    _collect_changed_tracked_files,
    _collect_local_codex_execution_readiness_banned_prompt_fragments,
    _collect_project_browser_selector_candidates_for_target,
    _derive_bounded_n2_reason_taxonomy,
    _evaluate_one_cycle_controller_exec_plan_safety,
    _first_true_reason,
    _is_project_browser_login_interruption_url,
    _iso_now,
    _maybe_reconcile_stale_prompt334_post_codex_artifacts,
    _normalize_contract_payload,
    _normalize_project_browser_reason_codes,
    _normalize_selector_candidates,
    _normalize_string_list,
    _normalize_text,
    _overlay_bounded_local_loop_local_loop_state_for_coordinator,
    _parse_git_status_path,
    _parse_project_browser_structured_response,
    _probe_playwright_import_posture,
    _read_json_object_if_exists,
    _read_multi_cycle_history,
    _reconcile_approve_commit_tag_artifacts,
    _record_one_cycle_result_into_multi_cycle_history,
    _refresh_one_cycle_controller_runtime_planning_artifacts,
    _resolve_project_browser_chatgpt_url,
    _resolve_project_browser_prepared_prompt_text,
    _run_git,
    _run_selected_step_read_current_state_if_allowed,
    _run_targeted_fix_post_reentry_codex_reentry_execution_if_enabled,
    _run_targeted_fix_reentry_execution_if_enabled,
    _serialize_required_signals,
    _write_json,
    _write_multi_cycle_history,
    _write_targeted_fix_post_reentry_prompt_if_allowed,
)
from automation.orchestration.planned_runner.project_browser.codex_bridge import (
    _build_project_browser_autonomous_codex_execution_state,
    _build_project_browser_autonomous_codex_result_assimilation_state,
)
from automation.orchestration.planned_runner.project_browser.local_loop import (
    _build_project_browser_autonomous_browser_execution_state,
    _build_project_browser_autonomous_md_apply_state,
    _build_project_browser_autonomous_run_ledger_persistence_state,
)
from automation.orchestration.planned_runner.project_browser.prompt_fill import (
    _build_project_browser_prompt_fill_state,
)
from automation.orchestration.planned_runner.project_browser.prompt_send import (
    _build_project_browser_prompt_send_state,
)
from automation.orchestration.planned_runner.project_browser.recovery import (
    _build_project_browser_recovery_runtime_state,
)
from automation.orchestration.planned_runner.project_browser.response_parse import (
    _build_project_browser_response_parse_state,
)
from automation.orchestration.planned_runner.project_browser.response_wait_read import (
    _build_project_browser_response_wait_read_state,
)
from automation.orchestration.planned_runner.project_browser.selector_probe import (
    _build_project_browser_selector_probe_state,
)

def _build_project_browser_launch_preflight_state(
    *,
    browser_command_queue_status: str,
    browser_command_type: str,
    browser_command_block_reason: str,
    browser_command_precondition_posture: Mapping[str, Any] | None,
    prior_browser_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    prior = dict(prior_browser_state or {})
    queue_status = _normalize_text(
        browser_command_queue_status,
        default="insufficient_truth",
    )
    command_type = _normalize_text(browser_command_type, default="none")
    command_block_reason = _normalize_text(
        browser_command_block_reason,
        default="insufficient_truth",
    )
    preconditions = (
        dict(browser_command_precondition_posture)
        if isinstance(browser_command_precondition_posture, Mapping)
        else {}
    )
    payload_contract = _normalize_text(
        preconditions.get("payload_contract"),
        default="insufficient_truth",
    )
    selector_contract = _normalize_text(
        preconditions.get("selector_contract"),
        default="insufficient_truth",
    )
    handoff_contract = _normalize_text(
        preconditions.get("handoff_contract"),
        default="insufficient_truth",
    )

    supported_command_types = _PROJECT_BROWSER_COMMAND_TYPES - {"none"}
    session_mode = _normalize_text(
        prior.get("project_browser_session_mode"),
        default="none",
    )
    if session_mode not in _PROJECT_BROWSER_SESSION_MODES:
        session_mode = "none"
    if session_mode == "none":
        if _normalize_text(prior.get("project_browser_session_user_data_dir"), default=""):
            session_mode = "explicit_user_data_dir"
        elif bool(prior.get("project_browser_session_persistent_context", False)):
            session_mode = "persistent_context"
        elif bool(prior.get("project_browser_session_existing_profile", False)) or (
            _normalize_text(prior.get("project_browser_ui_session_posture"), default="")
            in {"ready", "available", "known"}
        ):
            session_mode = "existing_profile"

    import_posture = _normalize_text(
        prior.get("project_browser_playwright_import_posture"),
        default="not_checked",
    )
    probe_enabled = bool(prior.get("project_browser_playwright_import_probe_enabled", False))
    if queue_status == "inactive":
        import_posture = "import_not_required"
    elif queue_status in {"blocked", "unavailable"}:
        if import_posture not in {"import_available", "import_unavailable"}:
            import_posture = "not_checked"
    elif queue_status == "insufficient_truth":
        import_posture = "insufficient_truth"
    elif queue_status == "prepared":
        if import_posture not in {"import_available", "import_unavailable"}:
            import_posture = _probe_playwright_import_posture() if probe_enabled else "not_checked"
    if import_posture not in _PROJECT_BROWSER_PLAYWRIGHT_IMPORT_POSTURES:
        import_posture = "insufficient_truth"

    session_status = "insufficient_truth"
    if queue_status == "inactive":
        session_status = "inactive"
        session_mode = "none"
    elif queue_status == "blocked":
        session_status = "blocked"
    elif queue_status == "unavailable":
        session_status = "unavailable"
    elif queue_status == "insufficient_truth":
        session_status = "insufficient_truth"
    elif session_mode in _PROJECT_BROWSER_SESSION_MODES - {"none", "insufficient_truth"}:
        session_status = "configured"
    elif session_mode == "insufficient_truth":
        session_status = "insufficient_truth"
    else:
        session_status = "unavailable"
    if session_status not in _PROJECT_BROWSER_SESSION_CONFIG_STATUSES:
        session_status = "insufficient_truth"
    if session_mode not in _PROJECT_BROWSER_SESSION_MODES:
        session_mode = "insufficient_truth"

    login_preflight_posture = "not_checked"
    runtime_block_reason = "insufficient_truth"
    launch_status = "insufficient_truth"
    launch_mode = "blocked"

    if queue_status == "inactive":
        launch_status = "inactive"
        launch_mode = "none"
        runtime_block_reason = "command_queue_inactive"
    elif queue_status == "blocked":
        launch_status = "blocked"
        launch_mode = "blocked"
        runtime_block_reason = "command_queue_blocked"
        login_preflight_posture = (
            "blocked"
            if command_block_reason in {"login_interruption", "retry_limit_reached"}
            else "not_checked"
        )
    elif queue_status == "unavailable":
        launch_status = "unavailable"
        launch_mode = "metadata_only"
        runtime_block_reason = "command_queue_unavailable"
    elif queue_status == "insufficient_truth":
        launch_status = "insufficient_truth"
        launch_mode = "blocked"
        runtime_block_reason = "insufficient_truth"
        login_preflight_posture = "insufficient_truth"
    elif queue_status != "prepared":
        launch_status = "blocked"
        launch_mode = "blocked"
        runtime_block_reason = "command_not_prepared"
    elif command_type not in supported_command_types:
        launch_status = "blocked"
        launch_mode = "blocked"
        runtime_block_reason = "unsupported_command_type"
    elif command_type == "pause_for_login":
        launch_status = "blocked"
        launch_mode = "blocked"
        runtime_block_reason = "login_truth_missing"
        login_preflight_posture = "login_pause_required_if_detected_later"
    elif command_type == "escalate":
        launch_status = "blocked"
        launch_mode = "blocked"
        runtime_block_reason = "launch_not_allowed"
    elif import_posture == "import_unavailable":
        launch_status = "blocked"
        launch_mode = "blocked"
        runtime_block_reason = "playwright_import_unavailable"
    elif payload_contract in {"unavailable", "blocked", "insufficient_truth"}:
        launch_status = (
            "insufficient_truth"
            if payload_contract == "insufficient_truth"
            else "unavailable"
        )
        launch_mode = "metadata_only" if launch_status == "unavailable" else "blocked"
        runtime_block_reason = (
            "insufficient_truth"
            if payload_contract == "insufficient_truth"
            else "session_config_missing"
        )
    elif selector_contract in {"unavailable", "blocked", "insufficient_truth"}:
        launch_status = (
            "insufficient_truth"
            if selector_contract == "insufficient_truth"
            else "unavailable"
        )
        launch_mode = "metadata_only" if launch_status == "unavailable" else "blocked"
        runtime_block_reason = (
            "insufficient_truth"
            if selector_contract == "insufficient_truth"
            else "session_config_missing"
        )
    elif handoff_contract in {"unavailable", "blocked", "insufficient_truth"}:
        launch_status = (
            "insufficient_truth"
            if handoff_contract == "insufficient_truth"
            else "unavailable"
        )
        launch_mode = "metadata_only" if launch_status == "unavailable" else "blocked"
        runtime_block_reason = (
            "insufficient_truth"
            if handoff_contract == "insufficient_truth"
            else "session_config_missing"
        )
    elif session_status == "configured":
        launch_status = "ready"
        launch_mode = "launch_allowed_later"
        runtime_block_reason = "none"
        login_preflight_posture = "assumed_existing_session"
    elif session_status == "unavailable":
        launch_status = "unavailable"
        launch_mode = "metadata_only"
        runtime_block_reason = "session_config_missing"
    elif session_status == "blocked":
        launch_status = "blocked"
        launch_mode = "blocked"
        runtime_block_reason = "session_config_missing"
    else:
        launch_status = "insufficient_truth"
        launch_mode = "blocked"
        runtime_block_reason = "insufficient_truth"
        login_preflight_posture = "insufficient_truth"

    if launch_status not in _PROJECT_BROWSER_LAUNCH_PREFLIGHT_STATUSES:
        launch_status = "insufficient_truth"
    if launch_mode not in _PROJECT_BROWSER_LAUNCH_PREFLIGHT_MODES:
        launch_mode = "blocked"
    if login_preflight_posture not in _PROJECT_BROWSER_LOGIN_PREFLIGHT_POSTURES:
        login_preflight_posture = "insufficient_truth"
    if runtime_block_reason not in _PROJECT_BROWSER_RUNTIME_BLOCK_REASONS:
        runtime_block_reason = "insufficient_truth"

    boundary_status = "insufficient_truth"
    if queue_status == "inactive":
        boundary_status = "inactive"
    elif queue_status == "blocked":
        boundary_status = "blocked"
    elif queue_status == "unavailable":
        boundary_status = "unavailable"
    elif queue_status == "insufficient_truth":
        boundary_status = "insufficient_truth"
    elif launch_status == "ready" and import_posture in {"import_available", "not_checked"}:
        boundary_status = "available"
    elif import_posture == "import_unavailable":
        boundary_status = "unavailable"
    elif launch_status == "blocked":
        boundary_status = "blocked"
    elif launch_status == "unavailable":
        boundary_status = "unavailable"
    else:
        boundary_status = "insufficient_truth"
    if boundary_status not in _PROJECT_BROWSER_PLAYWRIGHT_BOUNDARY_STATUSES:
        boundary_status = "insufficient_truth"

    launch_receipt_status = "insufficient_truth"
    launch_receipt_kind = "none"
    if launch_status == "inactive":
        launch_receipt_status = "not_created"
    elif launch_status == "ready":
        launch_receipt_status = "preflight_ready"
        launch_receipt_kind = "launch_preflight_receipt"
    elif launch_status == "blocked":
        launch_receipt_status = "blocked"
        launch_receipt_kind = "non_execution_launch_receipt"
    elif launch_status == "unavailable":
        launch_receipt_status = "unavailable"
        launch_receipt_kind = "non_execution_launch_receipt"
    else:
        launch_receipt_status = "insufficient_truth"
        launch_receipt_kind = "none"
    if launch_receipt_status not in _PROJECT_BROWSER_LAUNCH_RECEIPT_STATUSES:
        launch_receipt_status = "insufficient_truth"
    if launch_receipt_kind not in _PROJECT_BROWSER_LAUNCH_RECEIPT_KINDS:
        launch_receipt_kind = "none"

    return {
        "project_browser_playwright_boundary_status": boundary_status,
        "project_browser_playwright_import_posture": import_posture,
        "project_browser_session_config_status": session_status,
        "project_browser_session_mode": session_mode,
        "project_browser_launch_preflight_status": launch_status,
        "project_browser_launch_preflight_mode": launch_mode,
        "project_browser_login_preflight_posture": login_preflight_posture,
        "project_browser_runtime_block_reason": runtime_block_reason,
        "project_browser_launch_receipt_status": launch_receipt_status,
        "project_browser_launch_receipt_kind": launch_receipt_kind,
    }

def _build_project_browser_autonomous_rolling_continuation_launcher_state(
    *,
    autonomous_rolling_controller_status: str,
    autonomous_rolling_controller_permission: str,
    autonomous_rolling_controller_source_status: str,
    autonomous_rolling_controller_block_reason: str,
    autonomous_rolling_controller_receipt_status: str,
    autonomous_rolling_controller_next_action: str,
    autonomous_resume_permission: str,
    autonomous_resume_next_allowed_action: str,
    autonomous_watchdog_status: str,
    autonomous_short_batch_stop_reason: str,
    autonomous_short_batch_steps_attempted: int,
    autonomous_run_ledger_persistence_status: str,
    autonomous_run_ledger_counter_posture: str,
    autonomous_run_ledger_persistence_target_status: str,
) -> dict[str, Any]:
    rolling_controller_status = _normalize_text(
        autonomous_rolling_controller_status,
        default="insufficient_truth",
    )
    rolling_controller_permission = _normalize_text(
        autonomous_rolling_controller_permission,
        default="insufficient_truth",
    )
    rolling_controller_source_status = _normalize_text(
        autonomous_rolling_controller_source_status,
        default="insufficient_truth",
    )
    rolling_controller_block_reason = _normalize_text(
        autonomous_rolling_controller_block_reason,
        default="insufficient_truth",
    )
    rolling_controller_receipt_status = _normalize_text(
        autonomous_rolling_controller_receipt_status,
        default="insufficient_truth",
    )
    rolling_controller_next_action = _normalize_text(
        autonomous_rolling_controller_next_action,
        default="none",
    )
    resume_permission = _normalize_text(
        autonomous_resume_permission,
        default="insufficient_truth",
    )
    resume_next_allowed_action = _normalize_text(
        autonomous_resume_next_allowed_action,
        default="none",
    )
    watchdog_status = _normalize_text(
        autonomous_watchdog_status,
        default="insufficient_truth",
    )
    short_batch_stop_reason = _normalize_text(
        autonomous_short_batch_stop_reason,
        default="insufficient_truth",
    )
    short_batch_steps_attempted = _as_non_negative_int(
        autonomous_short_batch_steps_attempted,
        default=0,
    )
    run_ledger_status = _normalize_text(
        autonomous_run_ledger_persistence_status,
        default="insufficient_truth",
    )
    run_ledger_counter_posture = _normalize_text(
        autonomous_run_ledger_counter_posture,
        default="insufficient_truth",
    )
    run_ledger_persistence_target_status = _normalize_text(
        autonomous_run_ledger_persistence_target_status,
        default="insufficient_truth",
    )

    runtime_posture = [
        "metadata_only_launcher_candidate",
        "bounded_one_short_batch_only",
        "no_next_batch_start",
        "no_rolling_execution",
        "no_daemon",
        "no_background_scheduler",
        "no_sleep_loop",
        "no_queue_drain",
        "no_retry_execution",
        "no_repair_execution",
        "no_restart_execution",
        "no_approval_execution",
        "no_continuation_execution",
        "no_prompt_send",
        "no_md_write",
        "no_shell_execution",
        "no_browser_action",
        "no_playwright",
        "no_dom_interaction",
        "no_git_mutation",
    ]

    def _base_state(
        *,
        status: str,
        kind: str,
        permission: str,
        source_status: str,
        block_reason: str,
        receipt_status: str,
        receipt_kind: str,
        next_action: str,
        launch_mode: str,
        max_next_batch_steps: int,
    ) -> dict[str, Any]:
        return {
            "project_browser_autonomous_rolling_continuation_status": status,
            "project_browser_autonomous_rolling_continuation_kind": kind,
            "project_browser_autonomous_rolling_continuation_permission": permission,
            "project_browser_autonomous_rolling_continuation_source_status": source_status,
            "project_browser_autonomous_rolling_continuation_block_reason": block_reason,
            "project_browser_autonomous_rolling_continuation_receipt_status": receipt_status,
            "project_browser_autonomous_rolling_continuation_receipt_kind": receipt_kind,
            "project_browser_autonomous_rolling_continuation_next_action": next_action,
            "project_browser_autonomous_rolling_continuation_launch_mode": launch_mode,
            "project_browser_autonomous_rolling_continuation_max_next_batch_steps": (
                max_next_batch_steps
            ),
            "project_browser_autonomous_rolling_continuation_runtime_posture": runtime_posture,
        }

    def _insufficient_truth_state(*, block_reason: str) -> dict[str, Any]:
        normalized_block_reason = (
            block_reason
            if block_reason in {"source_inconsistent", "insufficient_truth"}
            else "insufficient_truth"
        )
        return _base_state(
            status="insufficient_truth",
            kind="insufficient_truth_rolling_continuation_launcher",
            permission="insufficient_truth",
            source_status="insufficient_truth",
            block_reason=normalized_block_reason,
            receipt_status="insufficient_truth",
            receipt_kind="insufficient_truth_rolling_continuation_launcher_receipt",
            next_action="hold_insufficient_truth",
            launch_mode="none",
            max_next_batch_steps=0,
        )

    if rolling_controller_status not in {
        "prepared",
        "blocked",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if rolling_controller_permission not in _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if rolling_controller_source_status not in {"valid", "inconsistent", "insufficient_truth"}:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if rolling_controller_block_reason not in {
        "none",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
        "source_inconsistent",
        "resume_inactive",
        "resume_not_allowed",
        "resume_receipt_not_ready",
        "watchdog_not_allowed",
        "watchdog_receipt_not_ready",
        "next_action_not_allowed",
        "manual_stop",
        "stale_receipt",
        "missing_receipt",
        "duplicate_receipt",
        "short_batch_not_terminal_for_rolling",
        "ledger_not_persisted",
        "cooldown_required",
        "loop_suspected",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if rolling_controller_receipt_status not in {
        "ready",
        "blocked",
        "failed",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if rolling_controller_next_action not in {
        "none",
        "prepare_next_short_batch_later",
        "hold_pause",
        "hold_human_review",
        "hold_insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if resume_permission not in _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if resume_next_allowed_action not in {
        "none",
        "resume_from_checkpoint",
        "resume_next_short_batch_later",
        "hold_pause",
        "hold_human_review",
        "hold_insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if watchdog_status not in {
        "clear",
        "stale",
        "missing_receipt",
        "duplicate_receipt",
        "manual_stop",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if short_batch_stop_reason not in {
        "none",
        "max_steps_reached",
        "budget_exhausted",
        "failure_budget_exhausted",
        "retry_budget_exhausted",
        "cooldown_required",
        "loop_suspected",
        "duplicate_detected",
        "ledger_not_persisted",
        "source_inconsistent",
        "step_failed",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if run_ledger_status not in {
        "inactive",
        "persisted",
        "prepared",
        "skipped",
        "blocked",
        "failed",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if run_ledger_counter_posture not in {
        "no_change",
        "would_increment_step",
        "would_increment_failure",
        "would_increment_retry",
        "persisted",
        "blocked",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if run_ledger_persistence_target_status not in {
        "unavailable",
        "existing_path_available",
        "metadata_only",
        "blocked",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")

    if short_batch_steps_attempted > 3:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if rolling_controller_source_status in {"inconsistent", "insufficient_truth"}:
        return _insufficient_truth_state(
            block_reason=(
                "source_inconsistent"
                if rolling_controller_source_status == "inconsistent"
                else "insufficient_truth"
            )
        )

    if (
        rolling_controller_status == "insufficient_truth"
        or rolling_controller_permission == "insufficient_truth"
        or rolling_controller_receipt_status == "insufficient_truth"
    ):
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if (
        rolling_controller_status == "pause_required"
        or rolling_controller_permission == "pause_required"
        or rolling_controller_receipt_status == "pause_required"
    ):
        return _base_state(
            status="pause_required",
            kind="pause_rolling_continuation_launcher",
            permission="pause_required",
            source_status="valid",
            block_reason="pause_required",
            receipt_status="pause_required",
            receipt_kind="pause_rolling_continuation_launcher_receipt",
            next_action="hold_pause",
            launch_mode="none",
            max_next_batch_steps=0,
        )
    if (
        rolling_controller_status == "human_review_required"
        or rolling_controller_permission == "human_review_required"
        or rolling_controller_receipt_status == "human_review_required"
    ):
        return _base_state(
            status="human_review_required",
            kind="human_review_rolling_continuation_launcher",
            permission="human_review_required",
            source_status="valid",
            block_reason="human_review_required",
            receipt_status="human_review_required",
            receipt_kind="human_review_rolling_continuation_launcher_receipt",
            next_action="hold_human_review",
            launch_mode="none",
            max_next_batch_steps=0,
        )
    if (
        rolling_controller_status == "blocked"
        or rolling_controller_permission == "blocked"
        or rolling_controller_receipt_status in {"blocked", "failed"}
    ):
        return _base_state(
            status="blocked",
            kind="blocked_rolling_continuation_launcher",
            permission="blocked",
            source_status="valid",
            block_reason=(
                rolling_controller_block_reason
                if rolling_controller_block_reason
                in {
                    "pause_required",
                    "human_review_required",
                    "insufficient_truth",
                    "source_inconsistent",
                    "resume_inactive",
                    "resume_not_allowed",
                    "resume_receipt_not_ready",
                    "watchdog_not_allowed",
                    "watchdog_receipt_not_ready",
                    "next_action_not_allowed",
                    "manual_stop",
                    "stale_receipt",
                    "missing_receipt",
                    "duplicate_receipt",
                    "short_batch_not_terminal_for_rolling",
                    "ledger_not_persisted",
                    "cooldown_required",
                    "loop_suspected",
                }
                else "rolling_controller_blocked"
            ),
            receipt_status="blocked",
            receipt_kind="blocked_rolling_continuation_launcher_receipt",
            next_action="none",
            launch_mode="none",
            max_next_batch_steps=0,
        )

    if rolling_controller_status != "prepared":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_continuation_launcher",
            permission="blocked",
            source_status="valid",
            block_reason="rolling_controller_not_prepared",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_continuation_launcher_receipt",
            next_action="none",
            launch_mode="none",
            max_next_batch_steps=0,
        )
    if rolling_controller_permission != "allowed_candidate":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_continuation_launcher",
            permission="blocked",
            source_status="valid",
            block_reason="rolling_controller_not_allowed",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_continuation_launcher_receipt",
            next_action="none",
            launch_mode="none",
            max_next_batch_steps=0,
        )
    if rolling_controller_receipt_status != "ready":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_continuation_launcher",
            permission="blocked",
            source_status="valid",
            block_reason="rolling_controller_receipt_not_ready",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_continuation_launcher_receipt",
            next_action="none",
            launch_mode="none",
            max_next_batch_steps=0,
        )
    if rolling_controller_next_action != "prepare_next_short_batch_later":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_continuation_launcher",
            permission="blocked",
            source_status="valid",
            block_reason="next_action_not_allowed",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_continuation_launcher_receipt",
            next_action="none",
            launch_mode="none",
            max_next_batch_steps=0,
        )

    if (
        resume_permission == "insufficient_truth"
        or resume_next_allowed_action == "hold_insufficient_truth"
        or watchdog_status == "insufficient_truth"
        or short_batch_stop_reason == "insufficient_truth"
        or run_ledger_status == "insufficient_truth"
        or run_ledger_counter_posture == "insufficient_truth"
        or run_ledger_persistence_target_status == "insufficient_truth"
    ):
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if resume_permission == "pause_required":
        return _base_state(
            status="pause_required",
            kind="pause_rolling_continuation_launcher",
            permission="pause_required",
            source_status="valid",
            block_reason="pause_required",
            receipt_status="pause_required",
            receipt_kind="pause_rolling_continuation_launcher_receipt",
            next_action="hold_pause",
            launch_mode="none",
            max_next_batch_steps=0,
        )
    if resume_permission == "human_review_required":
        return _base_state(
            status="human_review_required",
            kind="human_review_rolling_continuation_launcher",
            permission="human_review_required",
            source_status="valid",
            block_reason="human_review_required",
            receipt_status="human_review_required",
            receipt_kind="human_review_rolling_continuation_launcher_receipt",
            next_action="hold_human_review",
            launch_mode="none",
            max_next_batch_steps=0,
        )
    if resume_permission != "allowed_candidate":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_continuation_launcher",
            permission="blocked",
            source_status="valid",
            block_reason="resume_not_allowed",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_continuation_launcher_receipt",
            next_action="none",
            launch_mode="none",
            max_next_batch_steps=0,
        )
    if resume_next_allowed_action != "resume_next_short_batch_later":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_continuation_launcher",
            permission="blocked",
            source_status="valid",
            block_reason="next_action_not_allowed",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_continuation_launcher_receipt",
            next_action="none",
            launch_mode="none",
            max_next_batch_steps=0,
        )

    if watchdog_status == "stale":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_continuation_launcher",
            permission="blocked",
            source_status="valid",
            block_reason="stale_receipt",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_continuation_launcher_receipt",
            next_action="none",
            launch_mode="none",
            max_next_batch_steps=0,
        )
    if watchdog_status == "missing_receipt":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_continuation_launcher",
            permission="blocked",
            source_status="valid",
            block_reason="missing_receipt",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_continuation_launcher_receipt",
            next_action="none",
            launch_mode="none",
            max_next_batch_steps=0,
        )
    if watchdog_status == "duplicate_receipt":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_continuation_launcher",
            permission="blocked",
            source_status="valid",
            block_reason="duplicate_receipt",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_continuation_launcher_receipt",
            next_action="none",
            launch_mode="none",
            max_next_batch_steps=0,
        )
    if watchdog_status == "manual_stop":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_continuation_launcher",
            permission="blocked",
            source_status="valid",
            block_reason="manual_stop",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_continuation_launcher_receipt",
            next_action="none",
            launch_mode="none",
            max_next_batch_steps=0,
        )
    if watchdog_status != "clear":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_continuation_launcher",
            permission="blocked",
            source_status="valid",
            block_reason="watchdog_not_clear",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_continuation_launcher_receipt",
            next_action="none",
            launch_mode="none",
            max_next_batch_steps=0,
        )

    if short_batch_stop_reason != "max_steps_reached":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_continuation_launcher",
            permission="blocked",
            source_status="valid",
            block_reason="short_batch_not_terminal_for_rolling",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_continuation_launcher_receipt",
            next_action="none",
            launch_mode="none",
            max_next_batch_steps=0,
        )
    if run_ledger_status == "prepared" or run_ledger_persistence_target_status == "metadata_only":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_continuation_launcher",
            permission="blocked",
            source_status="valid",
            block_reason="ledger_not_persisted",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_continuation_launcher_receipt",
            next_action="none",
            launch_mode="none",
            max_next_batch_steps=0,
        )
    if run_ledger_status != "persisted" or run_ledger_counter_posture != "persisted":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_continuation_launcher",
            permission="blocked",
            source_status="valid",
            block_reason="ledger_not_persisted",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_continuation_launcher_receipt",
            next_action="none",
            launch_mode="none",
            max_next_batch_steps=0,
        )

    return _base_state(
        status="prepared",
        kind="one_short_batch_continuation_launcher",
        permission="allowed_candidate",
        source_status="valid",
        block_reason="none",
        receipt_status="ready",
        receipt_kind="one_rolling_continuation_launcher_receipt",
        next_action="launch_one_short_batch_later",
        launch_mode="bounded_one_short_batch",
        max_next_batch_steps=3,
    )

def _build_project_browser_autonomous_rolling_multi_launch_state(
    *,
    autonomous_rolling_continuation_status: str,
    autonomous_rolling_continuation_permission: str,
    autonomous_rolling_continuation_source_status: str,
    autonomous_rolling_continuation_block_reason: str,
    autonomous_rolling_continuation_receipt_status: str,
    autonomous_rolling_continuation_next_action: str,
    autonomous_rolling_continuation_launch_mode: str,
    autonomous_rolling_continuation_max_next_batch_steps: int,
    autonomous_short_batch_stop_reason: str,
    autonomous_run_ledger_persistence_status: str,
    autonomous_run_ledger_counter_posture: str,
    autonomous_run_ledger_persistence_target_status: str,
    autonomous_run_ledger_duplicate_status: str,
    autonomous_cooldown_status: str,
    autonomous_loop_risk_status: str,
    autonomous_watchdog_status: str,
    autonomous_short_batch_invocation_path_status: str,
) -> dict[str, Any]:
    rolling_continuation_status = _normalize_text(
        autonomous_rolling_continuation_status,
        default="insufficient_truth",
    )
    rolling_continuation_permission = _normalize_text(
        autonomous_rolling_continuation_permission,
        default="insufficient_truth",
    )
    rolling_continuation_source_status = _normalize_text(
        autonomous_rolling_continuation_source_status,
        default="insufficient_truth",
    )
    rolling_continuation_block_reason = _normalize_text(
        autonomous_rolling_continuation_block_reason,
        default="insufficient_truth",
    )
    rolling_continuation_receipt_status = _normalize_text(
        autonomous_rolling_continuation_receipt_status,
        default="insufficient_truth",
    )
    rolling_continuation_next_action = _normalize_text(
        autonomous_rolling_continuation_next_action,
        default="none",
    )
    rolling_continuation_launch_mode = _normalize_text(
        autonomous_rolling_continuation_launch_mode,
        default="none",
    )
    rolling_continuation_max_next_batch_steps = _as_non_negative_int(
        autonomous_rolling_continuation_max_next_batch_steps,
        default=0,
    )
    short_batch_stop_reason = _normalize_text(
        autonomous_short_batch_stop_reason,
        default="insufficient_truth",
    )
    run_ledger_status = _normalize_text(
        autonomous_run_ledger_persistence_status,
        default="insufficient_truth",
    )
    run_ledger_counter_posture = _normalize_text(
        autonomous_run_ledger_counter_posture,
        default="insufficient_truth",
    )
    run_ledger_persistence_target_status = _normalize_text(
        autonomous_run_ledger_persistence_target_status,
        default="insufficient_truth",
    )
    run_ledger_duplicate_status = _normalize_text(
        autonomous_run_ledger_duplicate_status,
        default="insufficient_truth",
    )
    cooldown_status = _normalize_text(
        autonomous_cooldown_status,
        default="insufficient_truth",
    )
    loop_risk_status = _normalize_text(
        autonomous_loop_risk_status,
        default="insufficient_truth",
    )
    watchdog_status = _normalize_text(
        autonomous_watchdog_status,
        default="insufficient_truth",
    )
    short_batch_invocation_path_status = _normalize_text(
        autonomous_short_batch_invocation_path_status,
        default="unavailable",
    )

    max_launches = 2
    per_launch_max_steps = 3
    total_step_budget = 6
    failure_budget = 1

    runtime_posture = [
        "bounded_multi_launch_runner",
        "max_2_launches_per_invocation",
        "max_3_steps_per_launch",
        "total_step_budget_6",
        "failure_budget_1",
        "recheck_gates_before_each_launch",
        "require_receipt_and_ledger_each_launch",
        "stop_immediately_on_stop_condition",
        "no_unbounded_loop",
        "no_daemon",
        "no_background_scheduler",
        "no_sleep_loop",
        "no_queue_drain",
        "no_direct_browser_execution",
        "no_direct_codex_execution",
        "no_shell_execution",
        "no_git_mutation",
    ]

    def _base_state(
        *,
        status: str,
        kind: str,
        permission: str,
        source_status: str,
        block_reason: str,
        receipt_status: str,
        receipt_kind: str,
        launches_allowed: int,
        launches_attempted: int,
        next_action: str,
    ) -> dict[str, Any]:
        return {
            "project_browser_autonomous_rolling_multi_launch_status": status,
            "project_browser_autonomous_rolling_multi_launch_kind": kind,
            "project_browser_autonomous_rolling_multi_launch_permission": permission,
            "project_browser_autonomous_rolling_multi_launch_source_status": source_status,
            "project_browser_autonomous_rolling_multi_launch_block_reason": block_reason,
            "project_browser_autonomous_rolling_multi_launch_receipt_status": receipt_status,
            "project_browser_autonomous_rolling_multi_launch_receipt_kind": receipt_kind,
            "project_browser_autonomous_rolling_multi_launch_launches_allowed": launches_allowed,
            "project_browser_autonomous_rolling_multi_launch_launches_attempted": launches_attempted,
            "project_browser_autonomous_rolling_multi_launch_max_launches": max_launches,
            "project_browser_autonomous_rolling_multi_launch_per_launch_max_steps": (
                per_launch_max_steps
            ),
            "project_browser_autonomous_rolling_multi_launch_total_step_budget": (
                total_step_budget
            ),
            "project_browser_autonomous_rolling_multi_launch_failure_budget": failure_budget,
            "project_browser_autonomous_rolling_multi_launch_next_action": next_action,
            "project_browser_autonomous_rolling_multi_launch_runtime_posture": runtime_posture,
        }

    def _insufficient_truth_state(*, block_reason: str) -> dict[str, Any]:
        normalized_block_reason = (
            block_reason
            if block_reason in {"source_inconsistent", "insufficient_truth"}
            else "insufficient_truth"
        )
        return _base_state(
            status="insufficient_truth",
            kind="insufficient_truth_bounded_multi_launch_runner",
            permission="insufficient_truth",
            source_status="insufficient_truth",
            block_reason=normalized_block_reason,
            receipt_status="insufficient_truth",
            receipt_kind="insufficient_truth_rolling_multi_launch_receipt",
            launches_allowed=0,
            launches_attempted=0,
            next_action="hold_insufficient_truth",
        )

    if rolling_continuation_status not in {
        "prepared",
        "blocked",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if rolling_continuation_permission not in _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if rolling_continuation_source_status not in {"valid", "inconsistent", "insufficient_truth"}:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if rolling_continuation_block_reason not in {
        "none",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
        "source_inconsistent",
        "rolling_controller_not_prepared",
        "rolling_controller_not_allowed",
        "rolling_controller_receipt_not_ready",
        "rolling_controller_blocked",
        "resume_inactive",
        "resume_not_allowed",
        "resume_receipt_not_ready",
        "watchdog_not_allowed",
        "watchdog_receipt_not_ready",
        "watchdog_not_clear",
        "next_action_not_allowed",
        "manual_stop",
        "stale_receipt",
        "missing_receipt",
        "duplicate_receipt",
        "short_batch_not_terminal_for_rolling",
        "ledger_not_persisted",
        "cooldown_required",
        "loop_suspected",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if rolling_continuation_receipt_status not in {
        "ready",
        "blocked",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if rolling_continuation_next_action not in {
        "none",
        "launch_one_short_batch_later",
        "hold_pause",
        "hold_human_review",
        "hold_insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if rolling_continuation_launch_mode not in {"none", "bounded_one_short_batch"}:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if short_batch_stop_reason not in {
        "none",
        "max_steps_reached",
        "budget_exhausted",
        "failure_budget_exhausted",
        "retry_budget_exhausted",
        "cooldown_required",
        "loop_suspected",
        "duplicate_detected",
        "ledger_not_persisted",
        "source_inconsistent",
        "step_failed",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if run_ledger_status not in {
        "inactive",
        "persisted",
        "prepared",
        "skipped",
        "blocked",
        "failed",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if run_ledger_counter_posture not in {
        "no_change",
        "would_increment_step",
        "would_increment_failure",
        "would_increment_retry",
        "persisted",
        "blocked",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if run_ledger_persistence_target_status not in {
        "unavailable",
        "existing_path_available",
        "metadata_only",
        "blocked",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if run_ledger_duplicate_status not in {
        "clear",
        "duplicate_detected",
        "blocked",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if cooldown_status not in {"not_required", "required", "blocked", "insufficient_truth"}:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if loop_risk_status not in {"clear", "suspected", "blocked", "insufficient_truth"}:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if watchdog_status not in {
        "clear",
        "stale",
        "missing_receipt",
        "duplicate_receipt",
        "manual_stop",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if short_batch_invocation_path_status not in {"available", "unavailable", "insufficient_truth"}:
        return _insufficient_truth_state(block_reason="source_inconsistent")

    if rolling_continuation_max_next_batch_steps > per_launch_max_steps:
        return _base_state(
            status="blocked",
            kind="blocked_bounded_multi_launch_runner",
            permission="blocked",
            source_status="valid",
            block_reason="max_next_batch_steps_exceeded",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_multi_launch_receipt",
            launches_allowed=max_launches,
            launches_attempted=0,
            next_action="none",
        )
    if rolling_continuation_source_status in {"inconsistent", "insufficient_truth"}:
        return _insufficient_truth_state(
            block_reason=(
                "source_inconsistent"
                if rolling_continuation_source_status == "inconsistent"
                else "insufficient_truth"
            )
        )

    if (
        rolling_continuation_status == "insufficient_truth"
        or rolling_continuation_permission == "insufficient_truth"
        or rolling_continuation_receipt_status == "insufficient_truth"
        or run_ledger_status == "insufficient_truth"
        or run_ledger_counter_posture == "insufficient_truth"
        or run_ledger_persistence_target_status == "insufficient_truth"
        or run_ledger_duplicate_status == "insufficient_truth"
        or cooldown_status == "insufficient_truth"
        or loop_risk_status == "insufficient_truth"
        or watchdog_status == "insufficient_truth"
        or short_batch_stop_reason == "insufficient_truth"
        or short_batch_invocation_path_status == "insufficient_truth"
    ):
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if short_batch_stop_reason == "source_inconsistent":
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if (
        rolling_continuation_status == "pause_required"
        or rolling_continuation_permission == "pause_required"
        or rolling_continuation_receipt_status == "pause_required"
        or short_batch_stop_reason == "pause_required"
    ):
        return _base_state(
            status="pause_required",
            kind="pause_bounded_multi_launch_runner",
            permission="pause_required",
            source_status="valid",
            block_reason="pause_required",
            receipt_status="pause_required",
            receipt_kind="pause_rolling_multi_launch_receipt",
            launches_allowed=max_launches,
            launches_attempted=0,
            next_action="hold_pause",
        )
    if (
        rolling_continuation_status == "human_review_required"
        or rolling_continuation_permission == "human_review_required"
        or rolling_continuation_receipt_status == "human_review_required"
        or short_batch_stop_reason == "human_review_required"
    ):
        return _base_state(
            status="human_review_required",
            kind="human_review_bounded_multi_launch_runner",
            permission="human_review_required",
            source_status="valid",
            block_reason="human_review_required",
            receipt_status="human_review_required",
            receipt_kind="human_review_rolling_multi_launch_receipt",
            launches_allowed=max_launches,
            launches_attempted=0,
            next_action="hold_human_review",
        )

    if watchdog_status == "manual_stop":
        return _base_state(
            status="blocked",
            kind="blocked_bounded_multi_launch_runner",
            permission="blocked",
            source_status="valid",
            block_reason="manual_stop",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_multi_launch_receipt",
            launches_allowed=max_launches,
            launches_attempted=0,
            next_action="none",
        )
    if watchdog_status in {"stale", "missing_receipt"}:
        return _base_state(
            status="blocked",
            kind="blocked_bounded_multi_launch_runner",
            permission="blocked",
            source_status="valid",
            block_reason="source_inconsistent",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_multi_launch_receipt",
            launches_allowed=max_launches,
            launches_attempted=0,
            next_action="none",
        )
    if watchdog_status == "duplicate_receipt" or run_ledger_duplicate_status == "duplicate_detected":
        return _base_state(
            status="blocked",
            kind="blocked_bounded_multi_launch_runner",
            permission="blocked",
            source_status="valid",
            block_reason="duplicate_detected",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_multi_launch_receipt",
            launches_allowed=max_launches,
            launches_attempted=0,
            next_action="none",
        )

    if short_batch_stop_reason == "failure_budget_exhausted":
        return _base_state(
            status="blocked",
            kind="blocked_bounded_multi_launch_runner",
            permission="blocked",
            source_status="valid",
            block_reason="failure_budget_exhausted",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_multi_launch_receipt",
            launches_allowed=max_launches,
            launches_attempted=0,
            next_action="none",
        )
    if short_batch_stop_reason in {"budget_exhausted", "retry_budget_exhausted"}:
        return _base_state(
            status="blocked",
            kind="blocked_bounded_multi_launch_runner",
            permission="blocked",
            source_status="valid",
            block_reason="step_budget_exhausted",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_multi_launch_receipt",
            launches_allowed=max_launches,
            launches_attempted=0,
            next_action="none",
        )
    if short_batch_stop_reason == "step_failed":
        return _base_state(
            status="failed",
            kind="failed_bounded_multi_launch_runner",
            permission="blocked",
            source_status="valid",
            block_reason="step_failed",
            receipt_status="failed",
            receipt_kind="failed_rolling_multi_launch_receipt",
            launches_allowed=max_launches,
            launches_attempted=0,
            next_action="none",
        )
    if short_batch_stop_reason == "ledger_not_persisted":
        return _base_state(
            status="blocked",
            kind="blocked_bounded_multi_launch_runner",
            permission="blocked",
            source_status="valid",
            block_reason="ledger_not_persisted",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_multi_launch_receipt",
            launches_allowed=max_launches,
            launches_attempted=0,
            next_action="none",
        )
    if short_batch_stop_reason == "cooldown_required":
        return _base_state(
            status="blocked",
            kind="blocked_bounded_multi_launch_runner",
            permission="blocked",
            source_status="valid",
            block_reason="cooldown_required",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_multi_launch_receipt",
            launches_allowed=max_launches,
            launches_attempted=0,
            next_action="none",
        )
    if short_batch_stop_reason == "loop_suspected":
        return _base_state(
            status="blocked",
            kind="blocked_bounded_multi_launch_runner",
            permission="blocked",
            source_status="valid",
            block_reason="loop_suspected",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_multi_launch_receipt",
            launches_allowed=max_launches,
            launches_attempted=0,
            next_action="none",
        )

    if rolling_continuation_status != "prepared":
        return _base_state(
            status="blocked",
            kind="blocked_bounded_multi_launch_runner",
            permission="blocked",
            source_status="valid",
            block_reason="launcher_not_prepared",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_multi_launch_receipt",
            launches_allowed=max_launches,
            launches_attempted=0,
            next_action="none",
        )
    if rolling_continuation_permission != "allowed_candidate":
        return _base_state(
            status="blocked",
            kind="blocked_bounded_multi_launch_runner",
            permission="blocked",
            source_status="valid",
            block_reason="launcher_not_allowed",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_multi_launch_receipt",
            launches_allowed=max_launches,
            launches_attempted=0,
            next_action="none",
        )
    if rolling_continuation_receipt_status != "ready":
        return _base_state(
            status="blocked",
            kind="blocked_bounded_multi_launch_runner",
            permission="blocked",
            source_status="valid",
            block_reason="launcher_receipt_not_ready",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_multi_launch_receipt",
            launches_allowed=max_launches,
            launches_attempted=0,
            next_action="none",
        )
    if rolling_continuation_next_action != "launch_one_short_batch_later":
        return _base_state(
            status="blocked",
            kind="blocked_bounded_multi_launch_runner",
            permission="blocked",
            source_status="valid",
            block_reason="next_action_not_allowed",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_multi_launch_receipt",
            launches_allowed=max_launches,
            launches_attempted=0,
            next_action="none",
        )
    if rolling_continuation_launch_mode != "bounded_one_short_batch":
        return _base_state(
            status="blocked",
            kind="blocked_bounded_multi_launch_runner",
            permission="blocked",
            source_status="valid",
            block_reason="launch_mode_not_bounded",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_multi_launch_receipt",
            launches_allowed=max_launches,
            launches_attempted=0,
            next_action="none",
        )
    if rolling_continuation_max_next_batch_steps < 1:
        return _base_state(
            status="blocked",
            kind="blocked_bounded_multi_launch_runner",
            permission="blocked",
            source_status="valid",
            block_reason="max_next_batch_steps_exceeded",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_multi_launch_receipt",
            launches_allowed=max_launches,
            launches_attempted=0,
            next_action="none",
        )

    if run_ledger_status == "prepared" or run_ledger_persistence_target_status == "metadata_only":
        return _base_state(
            status="blocked",
            kind="blocked_bounded_multi_launch_runner",
            permission="blocked",
            source_status="valid",
            block_reason="ledger_not_persisted",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_multi_launch_receipt",
            launches_allowed=max_launches,
            launches_attempted=0,
            next_action="none",
        )
    if run_ledger_status != "persisted" or run_ledger_counter_posture != "persisted":
        return _base_state(
            status="blocked",
            kind="blocked_bounded_multi_launch_runner",
            permission="blocked",
            source_status="valid",
            block_reason="ledger_not_persisted",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_multi_launch_receipt",
            launches_allowed=max_launches,
            launches_attempted=0,
            next_action="none",
        )
    if cooldown_status != "not_required":
        return _base_state(
            status="blocked",
            kind="blocked_bounded_multi_launch_runner",
            permission="blocked",
            source_status="valid",
            block_reason="cooldown_required",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_multi_launch_receipt",
            launches_allowed=max_launches,
            launches_attempted=0,
            next_action="none",
        )
    if loop_risk_status != "clear":
        return _base_state(
            status="blocked",
            kind="blocked_bounded_multi_launch_runner",
            permission="blocked",
            source_status="valid",
            block_reason="loop_suspected",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_multi_launch_receipt",
            launches_allowed=max_launches,
            launches_attempted=0,
            next_action="none",
        )

    if short_batch_invocation_path_status != "available":
        return _base_state(
            status="blocked",
            kind="blocked_bounded_multi_launch_runner",
            permission="blocked",
            source_status="valid",
            block_reason="short_batch_invocation_path_unavailable",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_multi_launch_receipt",
            launches_allowed=max_launches,
            launches_attempted=0,
            next_action="none",
        )

    return _base_state(
        status="prepared",
        kind="bounded_multi_launch_runner",
        permission="allowed_candidate",
        source_status="valid",
        block_reason="none",
        receipt_status="ready",
        receipt_kind="one_rolling_multi_launch_receipt",
        launches_allowed=max_launches,
        launches_attempted=0,
        next_action="launch_up_to_two_short_batches",
    )

def _build_project_browser_autonomous_one_bounded_launch_state(
    *,
    autonomous_rolling_execution_status: str,
    autonomous_rolling_execution_permission: str,
    autonomous_rolling_execution_source_status: str,
    autonomous_rolling_execution_receipt_status: str,
    autonomous_rolling_execution_runtime_capability: str,
    autonomous_rolling_execution_launches_allowed: int,
    autonomous_rolling_execution_launches_attempted: int,
    autonomous_rolling_execution_launches_completed: int,
    autonomous_rolling_multi_launch_status: str,
    autonomous_rolling_multi_launch_permission: str,
    autonomous_rolling_multi_launch_source_status: str,
    autonomous_rolling_multi_launch_receipt_status: str,
    autonomous_rolling_multi_launch_next_action: str,
    autonomous_short_batch_invocation_path_status: str,
    autonomous_short_batch_invocation_runtime_capability: str,
    autonomous_short_batch_invocation_receipt_status: str,
    autonomous_short_batch_invocation_delegation_mode: str,
    autonomous_short_batch_invocation_call_path_ref: str,
    autonomous_short_batch_invocation_missing_inputs: list[str] | None,
    autonomous_short_batch_invocation_next_action: str,
    autonomous_one_bounded_launch_callsite_available_vars: list[str] | None,
    autonomous_one_bounded_launch_callsite_values: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    rolling_execution_status = _normalize_text(
        autonomous_rolling_execution_status,
        default="insufficient_truth",
    )
    rolling_execution_permission = _normalize_text(
        autonomous_rolling_execution_permission,
        default="insufficient_truth",
    )
    rolling_execution_source_status = _normalize_text(
        autonomous_rolling_execution_source_status,
        default="insufficient_truth",
    )
    rolling_execution_receipt_status = _normalize_text(
        autonomous_rolling_execution_receipt_status,
        default="insufficient_truth",
    )
    rolling_execution_runtime_capability = _normalize_text(
        autonomous_rolling_execution_runtime_capability,
        default="insufficient_truth",
    )
    rolling_execution_launches_allowed = _as_non_negative_int(
        autonomous_rolling_execution_launches_allowed,
        default=0,
    )
    rolling_execution_launches_attempted = _as_non_negative_int(
        autonomous_rolling_execution_launches_attempted,
        default=0,
    )
    rolling_execution_launches_completed = _as_non_negative_int(
        autonomous_rolling_execution_launches_completed,
        default=0,
    )
    rolling_multi_launch_status = _normalize_text(
        autonomous_rolling_multi_launch_status,
        default="insufficient_truth",
    )
    rolling_multi_launch_permission = _normalize_text(
        autonomous_rolling_multi_launch_permission,
        default="insufficient_truth",
    )
    rolling_multi_launch_source_status = _normalize_text(
        autonomous_rolling_multi_launch_source_status,
        default="insufficient_truth",
    )
    rolling_multi_launch_receipt_status = _normalize_text(
        autonomous_rolling_multi_launch_receipt_status,
        default="insufficient_truth",
    )
    rolling_multi_launch_next_action = _normalize_text(
        autonomous_rolling_multi_launch_next_action,
        default="none",
    )
    short_batch_invocation_path_status = _normalize_text(
        autonomous_short_batch_invocation_path_status,
        default="insufficient_truth",
    )
    short_batch_invocation_runtime_capability = _normalize_text(
        autonomous_short_batch_invocation_runtime_capability,
        default="insufficient_truth",
    )
    short_batch_invocation_receipt_status = _normalize_text(
        autonomous_short_batch_invocation_receipt_status,
        default="insufficient_truth",
    )
    short_batch_invocation_delegation_mode = _normalize_text(
        autonomous_short_batch_invocation_delegation_mode,
        default="insufficient_truth",
    )
    short_batch_invocation_call_path_ref = _normalize_text(
        autonomous_short_batch_invocation_call_path_ref,
        default="none",
    )
    short_batch_invocation_missing_inputs = _normalize_string_list(
        autonomous_short_batch_invocation_missing_inputs or []
    )
    short_batch_invocation_next_action = _normalize_text(
        autonomous_short_batch_invocation_next_action,
        default="none",
    )
    one_bounded_launch_callsite_values = (
        dict(autonomous_one_bounded_launch_callsite_values)
        if isinstance(autonomous_one_bounded_launch_callsite_values, Mapping)
        else {}
    )
    one_bounded_launch_callsite_available_vars = set(
        _normalize_string_list(autonomous_one_bounded_launch_callsite_available_vars or [])
    )
    for candidate_name in one_bounded_launch_callsite_values:
        normalized_candidate_name = _normalize_text(candidate_name, default="")
        if normalized_candidate_name:
            one_bounded_launch_callsite_available_vars.add(normalized_candidate_name)

    max_steps = 3
    failure_budget = 1
    hard_risk_flags = {
        "unsafe_to_reinvoke",
        "duplicate_execution_risk",
        "github_mutation_risk",
        "new_executor_required",
        "queue_drain_risk",
        "unbounded_loop_risk",
        "builder_mapping_mismatch",
        "action_state_ref_missing",
        "insufficient_truth",
    }
    invocation_action_bridge_config = {
        "run_one_md_apply": {
            "builder_ref": "_build_project_browser_autonomous_md_apply_state",
            "state_ref": "project_browser_autonomous_md_apply_state",
            "required_inputs": [
                "autonomous_execution_adapter_status",
                "autonomous_execution_adapter_kind",
                "autonomous_execution_adapter_permission",
                "autonomous_execution_adapter_action",
                "autonomous_execution_adapter_source_status",
                "autonomous_execution_adapter_risk_status",
                "autonomous_execution_adapter_block_reason",
                "autonomous_execution_adapter_receipt_status",
                "autonomous_executor_readiness_status",
                "autonomous_executor_risk_status",
                "autonomous_dispatch_status",
                "autonomous_dispatch_risk_status",
                "autonomous_invocation_status",
                "autonomous_operation_contract_status",
                "autonomous_cooldown_status",
                "autonomous_loop_risk_status",
                "autonomous_multistep_budget_status",
                "autonomous_multistep_permission",
                "autonomous_multistep_state",
                "autonomous_safety_switch_status",
                "autonomous_manual_override_status",
                "autonomous_safe_stop_status",
                "autonomous_execution_permission",
                "autonomous_execution_bridge_status",
                "autonomous_execution_bridge_permission",
                "autonomous_md_update_draft_status",
                "autonomous_md_update_kind",
                "autonomous_md_update_command_draft_status",
                "autonomous_md_update_draft_compact",
                "autonomous_md_update_command_draft",
            ],
            "source_var_by_required_input": {
                "autonomous_md_update_draft_compact": "project_browser_autonomous_draft_state",
                "autonomous_md_update_command_draft": "project_browser_autonomous_draft_state",
            },
            "receipt_evidence_inputs": [
                "project_browser_autonomous_md_apply_receipt_status",
                "project_browser_autonomous_md_apply_receipt_kind",
            ],
            "completion_evidence_inputs": [
                "project_browser_autonomous_md_apply_write_status",
                "project_browser_autonomous_md_apply_change_status",
            ],
        },
        "run_one_browser_command": {
            "builder_ref": "_build_project_browser_autonomous_browser_execution_state",
            "state_ref": "project_browser_autonomous_browser_execution_state",
            "required_inputs": [
                "autonomous_browser_enqueue_status",
                "autonomous_browser_enqueue_permission",
                "autonomous_browser_enqueue_command_type",
                "autonomous_browser_enqueue_source_status",
                "autonomous_browser_enqueue_prompt_source_status",
                "autonomous_browser_enqueue_prompt_fingerprint_status",
                "autonomous_browser_enqueue_duplicate_status",
                "autonomous_browser_enqueue_retry_budget_status",
                "autonomous_browser_enqueue_block_reason",
                "autonomous_browser_enqueue_receipt_status",
                "autonomous_browser_enqueue_prompt_fingerprint",
                "autonomous_execution_adapter_status",
                "autonomous_execution_adapter_action",
                "autonomous_execution_adapter_risk_status",
                "autonomous_executor_readiness_status",
                "autonomous_dispatch_status",
                "autonomous_invocation_status",
                "autonomous_operation_contract_status",
                "autonomous_cooldown_status",
                "autonomous_loop_risk_status",
                "autonomous_multistep_budget_status",
                "autonomous_multistep_permission",
                "autonomous_multistep_state",
                "autonomous_safety_switch_status",
                "autonomous_manual_override_status",
                "autonomous_safe_stop_status",
                "autonomous_execution_permission",
                "autonomous_execution_bridge_status",
                "autonomous_execution_bridge_permission",
                "browser_launch_preflight_status",
                "browser_launch_preflight_mode",
                "browser_playwright_import_posture",
                "browser_session_config_status",
                "browser_session_mode",
                "browser_selector_contract_status",
                "browser_prompt_payload_status",
                "browser_prompt_payload",
                "browser_queue_handoff_payload",
                "prior_browser_state",
            ],
            "source_var_by_required_input": {
                "browser_prompt_payload": "project_browser_prompt_payload_state",
                "browser_queue_handoff_payload": "project_pr_queue_state",
                "prior_browser_state": "prior_approved_restart_execution",
            },
            "receipt_evidence_inputs": [
                "project_browser_autonomous_browser_execution_receipt_status",
                "project_browser_autonomous_browser_execution_receipt_kind",
            ],
            "completion_evidence_inputs": [
                "project_browser_autonomous_browser_execution_send_status",
                "project_browser_autonomous_browser_execution_response_read_status",
            ],
        },
        "run_one_codex_attempt": {
            "builder_ref": "_build_project_browser_autonomous_codex_execution_state",
            "state_ref": "project_browser_autonomous_codex_execution_state",
            "required_inputs": [
                "run_id",
                "adapter",
                "manifest_units",
                "autonomous_result_assimilation_status",
                "autonomous_result_assimilation_block_reason",
                "autonomous_result_assimilation_receipt_status",
                "autonomous_response_usability_status",
                "autonomous_response_handoff_status",
                "autonomous_codex_invocation_candidate_status",
                "autonomous_codex_invocation_candidate_kind",
                "autonomous_codex_invocation_permission",
                "autonomous_codex_invocation_prompt_source_status",
                "autonomous_codex_invocation_scope_status",
                "autonomous_codex_invocation_no_tests_policy",
                "autonomous_codex_invocation_token_posture",
                "autonomous_codex_invocation_candidate_compact",
                "autonomous_browser_execution_status",
                "autonomous_browser_execution_receipt_status",
                "autonomous_browser_enqueue_status",
                "autonomous_execution_adapter_status",
                "autonomous_executor_readiness_status",
                "autonomous_dispatch_status",
                "autonomous_invocation_status",
                "autonomous_operation_contract_status",
                "autonomous_cooldown_status",
                "autonomous_loop_risk_status",
                "autonomous_multistep_budget_status",
                "autonomous_multistep_permission",
                "autonomous_multistep_state",
                "autonomous_safety_switch_status",
                "autonomous_manual_override_status",
                "autonomous_safe_stop_status",
                "autonomous_execution_permission",
                "autonomous_execution_bridge_status",
                "autonomous_execution_bridge_permission",
                "project_pr_queue_handoff_payload",
                "project_pr_queue_selected_slice_id",
            ],
            "source_var_by_required_input": {
                "autonomous_codex_invocation_candidate_compact": (
                    "project_browser_autonomous_codex_invocation_candidate_compact"
                ),
                "project_pr_queue_handoff_payload": "project_pr_queue_state",
                "project_pr_queue_selected_slice_id": "project_pr_queue_state",
            },
            "receipt_evidence_inputs": [
                "project_browser_autonomous_codex_execution_receipt_status",
                "project_browser_autonomous_codex_execution_receipt_kind",
            ],
            "completion_evidence_inputs": [
                "project_browser_autonomous_codex_execution_attempt_count",
                "project_browser_autonomous_codex_execution_result_status",
            ],
        },
        "assimilate_result": {
            "builder_ref": "_build_project_browser_autonomous_codex_result_assimilation_state",
            "state_ref": "project_browser_autonomous_codex_result_assimilation_state",
            "required_inputs": [
                "autonomous_codex_execution_status",
                "autonomous_codex_execution_source_status",
                "autonomous_codex_execution_receipt_status",
                "autonomous_codex_execution_result_status",
                "autonomous_codex_execution_files_changed_status",
                "autonomous_codex_execution_tests_status",
                "autonomous_codex_execution_block_reason",
                "autonomous_codex_execution_attempt_count",
                "autonomous_codex_execution_max_attempts",
                "autonomous_codex_execution_repair_loop_status",
                "autonomous_codex_execution_suggested_validation_targets",
                "autonomous_codex_invocation_candidate_status",
                "autonomous_cooldown_status",
                "autonomous_loop_risk_status",
                "autonomous_multistep_budget_status",
                "autonomous_multistep_permission",
                "autonomous_multistep_state",
                "autonomous_safety_switch_status",
                "autonomous_manual_override_status",
                "autonomous_safe_stop_status",
                "autonomous_execution_permission",
                "autonomous_execution_bridge_status",
                "autonomous_execution_bridge_permission",
            ],
            "source_var_by_required_input": {
                "autonomous_codex_execution_suggested_validation_targets": (
                    "project_browser_autonomous_codex_execution_suggested_validation_targets"
                ),
            },
            "receipt_evidence_inputs": [
                "project_browser_autonomous_codex_result_receipt_status",
                "project_browser_autonomous_codex_result_receipt_kind",
            ],
            "completion_evidence_inputs": [
                "project_browser_autonomous_codex_result_outcome",
                "project_browser_autonomous_codex_result_next_posture",
            ],
        },
        "persist_ledger": {
            "builder_ref": "_build_project_browser_autonomous_run_ledger_persistence_state",
            "state_ref": "project_browser_autonomous_run_ledger_persistence_state",
            "required_inputs": [
                "autonomous_codex_result_assimilation_status",
                "autonomous_codex_result_outcome",
                "autonomous_codex_result_files_changed_status",
                "autonomous_codex_result_tests_status",
                "autonomous_codex_result_next_posture",
                "autonomous_codex_result_source_status",
                "autonomous_codex_result_block_reason",
                "autonomous_codex_result_receipt_status",
                "autonomous_codex_execution_attempt_count",
                "autonomous_codex_execution_max_attempts",
                "autonomous_codex_execution_repair_loop_status",
                "autonomous_cooldown_status",
                "autonomous_loop_risk_status",
                "autonomous_multistep_budget_status",
                "autonomous_multistep_permission",
                "autonomous_multistep_state",
                "autonomous_safety_switch_status",
                "autonomous_manual_override_status",
                "autonomous_safe_stop_status",
                "autonomous_execution_permission",
                "autonomous_execution_bridge_status",
                "autonomous_execution_bridge_permission",
                "prior_compact_state",
            ],
            "source_var_by_required_input": {
                "prior_compact_state": "prior_approved_restart_execution",
            },
            "receipt_evidence_inputs": [
                "project_browser_autonomous_run_ledger_receipt_status",
                "project_browser_autonomous_run_ledger_receipt_kind",
            ],
            "completion_evidence_inputs": [
                "project_browser_autonomous_run_ledger_event_kind",
                "project_browser_autonomous_run_ledger_counter_posture",
            ],
        },
    }
    invocation_builder_by_ref = {
        "_build_project_browser_autonomous_md_apply_state": (
            _build_project_browser_autonomous_md_apply_state
        ),
        "_build_project_browser_autonomous_browser_execution_state": (
            _build_project_browser_autonomous_browser_execution_state
        ),
        "_build_project_browser_autonomous_codex_execution_state": (
            _build_project_browser_autonomous_codex_execution_state
        ),
        "_build_project_browser_autonomous_codex_result_assimilation_state": (
            _build_project_browser_autonomous_codex_result_assimilation_state
        ),
        "_build_project_browser_autonomous_run_ledger_persistence_state": (
            _build_project_browser_autonomous_run_ledger_persistence_state
        ),
    }
    runtime_posture = [
        "one_actual_invocation_bridge_prompt145",
        "single_launch_path_only",
        "action_specific_callability_classification",
        "candidate_safety_validation_consumed",
        "callable_candidate_inputs_ready_handoff_consumed",
        "attempted_only_after_real_invocation",
        "completion_evidence_gated_prompt146",
        "completed_only_with_explicit_evidence",
        "no_attempt_from_state_reuse_only",
        "no_attempt_from_readiness_observation_only",
        "max_steps_3_contract",
        "failure_budget_1_contract",
        "no_multi_launch",
        "no_second_launch",
        "no_third_launch",
        "no_loop",
        "no_retry_loop",
        "no_new_executor",
        "no_daemon",
        "no_scheduler",
        "no_sleep_loop",
        "no_queue_drain",
        "no_github_mutation",
    ]
    generic_completion_evidence_refs = {
        "state_exists",
        "ready_receipt",
        "receipt_ready",
    }
    completion_evidence_ref_catalog = {
        "run_one_md_apply": [
            "project_browser_autonomous_md_apply_write_status",
            "project_browser_autonomous_md_apply_change_status",
            "project_browser_autonomous_md_apply_receipt_kind",
        ],
        "run_one_browser_command": [
            "project_browser_autonomous_browser_execution_send_status",
            "project_browser_autonomous_browser_execution_response_wait_status",
            "project_browser_autonomous_browser_execution_response_read_status",
        ],
        "run_one_codex_attempt": [
            "project_browser_autonomous_codex_execution_attempt_count",
            "project_browser_autonomous_codex_execution_result_status",
        ],
        "assimilate_result": [
            "project_browser_autonomous_codex_result_outcome",
            "project_browser_autonomous_codex_result_next_posture",
        ],
        "persist_ledger": [
            "project_browser_autonomous_run_ledger_event_kind",
            "project_browser_autonomous_run_ledger_counter_posture",
        ],
    }

    def _surface_scalar_value(
        surface_state: Mapping[str, Any],
        field_name: str,
    ) -> str:
        if field_name not in surface_state:
            return ""
        raw_value = surface_state.get(field_name)
        if raw_value is None:
            return ""
        if isinstance(raw_value, (str, int, float, bool)):
            return _normalize_text(str(raw_value), default="")
        return ""

    def _derive_missing_completion_surfaces(
        surface_state: Mapping[str, Any],
        candidate_surfaces: list[str],
    ) -> list[str]:
        normalized_surfaces = _normalize_string_list(candidate_surfaces)
        missing_surfaces = [
            surface_name
            for surface_name in normalized_surfaces
            if _surface_scalar_value(surface_state, surface_name) in {"", "insufficient_truth"}
        ]
        return missing_surfaces or normalized_surfaces

    def _evaluate_action_completion_evidence(
        *,
        action_name: str,
        invoked_state: Mapping[str, Any],
    ) -> dict[str, Any]:
        normalized_action_name = _normalize_text(action_name, default="none")
        completion_surfaces = _normalize_string_list(
            completion_evidence_ref_catalog.get(normalized_action_name, [])
        )
        invoked_mapping = dict(invoked_state) if isinstance(invoked_state, Mapping) else {}
        if not invoked_mapping or not completion_surfaces:
            return {
                "completion_evidence_status": "unavailable",
                "completion_evidence_reason": "explicit_completion_evidence_missing",
                "completion_evidence_refs": [],
                "completion_result_status": "not_completed",
                "completion_result_reason": "completion_evidence_unavailable",
                "missing_completion_evidence_surfaces": (
                    completion_surfaces or ["completion_evidence_truth"]
                ),
                "completion_allowed_refs": completion_surfaces,
            }

        surface_values = {
            surface_name: _surface_scalar_value(invoked_mapping, surface_name)
            for surface_name in completion_surfaces
        }

        def _refs(*surface_names: str) -> list[str]:
            return [
                surface_name
                for surface_name in _normalize_string_list(surface_names)
                if surface_values.get(surface_name, "") not in {"", "insufficient_truth"}
            ]

        def _completion_payload(
            *,
            evidence_status: str,
            evidence_reason: str,
            evidence_refs: list[str],
            result_status: str,
            result_reason: str,
            missing_surfaces: list[str] | None = None,
        ) -> dict[str, Any]:
            return {
                "completion_evidence_status": evidence_status,
                "completion_evidence_reason": evidence_reason,
                "completion_evidence_refs": _normalize_string_list(evidence_refs),
                "completion_result_status": result_status,
                "completion_result_reason": result_reason,
                "missing_completion_evidence_surfaces": _normalize_string_list(
                    missing_surfaces or []
                ),
                "completion_allowed_refs": completion_surfaces,
            }

        missing_completion_surfaces = _derive_missing_completion_surfaces(
            invoked_mapping,
            completion_surfaces,
        )

        if normalized_action_name == "run_one_md_apply":
            write_status = surface_values.get(
                "project_browser_autonomous_md_apply_write_status",
                "",
            )
            change_status = surface_values.get(
                "project_browser_autonomous_md_apply_change_status",
                "",
            )
            receipt_kind = surface_values.get(
                "project_browser_autonomous_md_apply_receipt_kind",
                "",
            )
            if write_status == "written" and change_status == "ready":
                return _completion_payload(
                    evidence_status="confirmed",
                    evidence_reason="explicit_completion_evidence_confirmed",
                    evidence_refs=_refs(
                        "project_browser_autonomous_md_apply_write_status",
                        "project_browser_autonomous_md_apply_change_status",
                    ),
                    result_status="completed",
                    result_reason="explicit_completion_evidence_confirmed",
                )
            if (
                write_status == "skipped"
                and change_status == "duplicate_noop"
                and receipt_kind == "duplicate_noop_receipt"
            ):
                return _completion_payload(
                    evidence_status="confirmed",
                    evidence_reason="explicit_completion_evidence_confirmed",
                    evidence_refs=_refs(
                        "project_browser_autonomous_md_apply_write_status",
                        "project_browser_autonomous_md_apply_change_status",
                        "project_browser_autonomous_md_apply_receipt_kind",
                    ),
                    result_status="completed",
                    result_reason="explicit_completion_evidence_confirmed",
                )
            if write_status in {"blocked", "failed"} or change_status in {
                "blocked",
                "too_large",
                "anchor_missing",
            }:
                return _completion_payload(
                    evidence_status="failed",
                    evidence_reason="completion_evidence_failed",
                    evidence_refs=_refs(
                        "project_browser_autonomous_md_apply_write_status",
                        "project_browser_autonomous_md_apply_change_status",
                    ),
                    result_status="failed",
                    result_reason="completion_evidence_failed",
                )
            if any(
                surface_values.get(surface_name, "")
                for surface_name in completion_surfaces
            ):
                return _completion_payload(
                    evidence_status="ambiguous",
                    evidence_reason="completion_evidence_ambiguous",
                    evidence_refs=_refs(*completion_surfaces),
                    result_status="not_completed",
                    result_reason="completion_evidence_ambiguous",
                )
            return _completion_payload(
                evidence_status="unavailable",
                evidence_reason="explicit_completion_evidence_missing",
                evidence_refs=[],
                result_status="not_completed",
                result_reason="completion_evidence_unavailable",
                missing_surfaces=missing_completion_surfaces,
            )

        if normalized_action_name == "run_one_browser_command":
            send_status = surface_values.get(
                "project_browser_autonomous_browser_execution_send_status",
                "",
            )
            response_wait_status = surface_values.get(
                "project_browser_autonomous_browser_execution_response_wait_status",
                "",
            )
            response_read_status = surface_values.get(
                "project_browser_autonomous_browser_execution_response_read_status",
                "",
            )
            if send_status == "sent" and response_read_status == "read":
                return _completion_payload(
                    evidence_status="confirmed",
                    evidence_reason="explicit_completion_evidence_confirmed",
                    evidence_refs=_refs(
                        "project_browser_autonomous_browser_execution_send_status",
                        "project_browser_autonomous_browser_execution_response_wait_status",
                        "project_browser_autonomous_browser_execution_response_read_status",
                    ),
                    result_status="completed",
                    result_reason="explicit_completion_evidence_confirmed",
                )
            if (
                send_status in {"blocked", "failed"}
                or response_wait_status in {"blocked", "failed", "timeout"}
                or response_read_status in {"blocked", "failed", "empty"}
            ):
                return _completion_payload(
                    evidence_status="failed",
                    evidence_reason="completion_evidence_failed",
                    evidence_refs=_refs(
                        "project_browser_autonomous_browser_execution_send_status",
                        "project_browser_autonomous_browser_execution_response_wait_status",
                        "project_browser_autonomous_browser_execution_response_read_status",
                    ),
                    result_status="failed",
                    result_reason="completion_evidence_failed",
                )
            if any(
                surface_values.get(surface_name, "")
                for surface_name in completion_surfaces
            ):
                return _completion_payload(
                    evidence_status="ambiguous",
                    evidence_reason="completion_evidence_ambiguous",
                    evidence_refs=_refs(*completion_surfaces),
                    result_status="not_completed",
                    result_reason="completion_evidence_ambiguous",
                )
            return _completion_payload(
                evidence_status="unavailable",
                evidence_reason="explicit_completion_evidence_missing",
                evidence_refs=[],
                result_status="not_completed",
                result_reason="completion_evidence_unavailable",
                missing_surfaces=missing_completion_surfaces,
            )

        if normalized_action_name == "run_one_codex_attempt":
            attempt_count = surface_values.get(
                "project_browser_autonomous_codex_execution_attempt_count",
                "",
            )
            result_status = surface_values.get(
                "project_browser_autonomous_codex_execution_result_status",
                "",
            )
            if attempt_count == "1" and result_status == "succeeded":
                return _completion_payload(
                    evidence_status="confirmed",
                    evidence_reason="explicit_completion_evidence_confirmed",
                    evidence_refs=_refs(
                        "project_browser_autonomous_codex_execution_attempt_count",
                        "project_browser_autonomous_codex_execution_result_status",
                    ),
                    result_status="completed",
                    result_reason="explicit_completion_evidence_confirmed",
                )
            if result_status in {"failed", "timeout", "blocked", "not_executed"}:
                return _completion_payload(
                    evidence_status="failed",
                    evidence_reason="completion_evidence_failed",
                    evidence_refs=_refs(
                        "project_browser_autonomous_codex_execution_attempt_count",
                        "project_browser_autonomous_codex_execution_result_status",
                    ),
                    result_status="failed",
                    result_reason="completion_evidence_failed",
                )
            if any(
                surface_values.get(surface_name, "")
                for surface_name in completion_surfaces
            ):
                return _completion_payload(
                    evidence_status="ambiguous",
                    evidence_reason="completion_evidence_ambiguous",
                    evidence_refs=_refs(*completion_surfaces),
                    result_status="not_completed",
                    result_reason="completion_evidence_ambiguous",
                )
            return _completion_payload(
                evidence_status="unavailable",
                evidence_reason="explicit_completion_evidence_missing",
                evidence_refs=[],
                result_status="not_completed",
                result_reason="completion_evidence_unavailable",
                missing_surfaces=missing_completion_surfaces,
            )

        if normalized_action_name == "assimilate_result":
            outcome = surface_values.get(
                "project_browser_autonomous_codex_result_outcome",
                "",
            )
            next_posture = surface_values.get(
                "project_browser_autonomous_codex_result_next_posture",
                "",
            )
            if outcome in {
                "codex_succeeded",
                "codex_failed",
                "codex_timeout",
                "codex_blocked",
                "codex_not_executed",
            } and next_posture in {
                "ready_for_ledger_update",
                "ready_for_validation_planning",
                "retry_candidate",
                "repair_candidate",
                "human_review_required",
                "pause_required",
                "blocked",
            }:
                return _completion_payload(
                    evidence_status="confirmed",
                    evidence_reason="explicit_completion_evidence_confirmed",
                    evidence_refs=_refs(
                        "project_browser_autonomous_codex_result_outcome",
                        "project_browser_autonomous_codex_result_next_posture",
                    ),
                    result_status="completed",
                    result_reason="explicit_completion_evidence_confirmed",
                )
            if any(
                surface_values.get(surface_name, "")
                for surface_name in completion_surfaces
            ):
                return _completion_payload(
                    evidence_status="ambiguous",
                    evidence_reason="completion_evidence_ambiguous",
                    evidence_refs=_refs(*completion_surfaces),
                    result_status="not_completed",
                    result_reason="completion_evidence_ambiguous",
                )
            return _completion_payload(
                evidence_status="unavailable",
                evidence_reason="explicit_completion_evidence_missing",
                evidence_refs=[],
                result_status="not_completed",
                result_reason="completion_evidence_unavailable",
                missing_surfaces=missing_completion_surfaces,
            )

        if normalized_action_name == "persist_ledger":
            event_kind = surface_values.get(
                "project_browser_autonomous_run_ledger_event_kind",
                "",
            )
            counter_posture = surface_values.get(
                "project_browser_autonomous_run_ledger_counter_posture",
                "",
            )
            if counter_posture == "persisted" and event_kind in {
                "codex_success_changed",
                "codex_success_no_change",
                "codex_failed",
                "codex_timeout",
                "codex_blocked",
                "human_review_required",
                "pause_required",
            }:
                return _completion_payload(
                    evidence_status="confirmed",
                    evidence_reason="explicit_completion_evidence_confirmed",
                    evidence_refs=_refs(
                        "project_browser_autonomous_run_ledger_event_kind",
                        "project_browser_autonomous_run_ledger_counter_posture",
                    ),
                    result_status="completed",
                    result_reason="explicit_completion_evidence_confirmed",
                )
            if counter_posture == "blocked":
                return _completion_payload(
                    evidence_status="failed",
                    evidence_reason="completion_evidence_failed",
                    evidence_refs=_refs(
                        "project_browser_autonomous_run_ledger_event_kind",
                        "project_browser_autonomous_run_ledger_counter_posture",
                    ),
                    result_status="failed",
                    result_reason="completion_evidence_failed",
                )
            if any(
                surface_values.get(surface_name, "")
                for surface_name in completion_surfaces
            ):
                return _completion_payload(
                    evidence_status="ambiguous",
                    evidence_reason="completion_evidence_ambiguous",
                    evidence_refs=_refs(*completion_surfaces),
                    result_status="not_completed",
                    result_reason="completion_evidence_ambiguous",
                )
            return _completion_payload(
                evidence_status="unavailable",
                evidence_reason="explicit_completion_evidence_missing",
                evidence_refs=[],
                result_status="not_completed",
                result_reason="completion_evidence_unavailable",
                missing_surfaces=missing_completion_surfaces,
            )

        return _completion_payload(
            evidence_status="unavailable",
            evidence_reason="explicit_completion_evidence_missing",
            evidence_refs=[],
            result_status="not_completed",
            result_reason="completion_evidence_unavailable",
            missing_surfaces=completion_surfaces or ["completion_evidence_truth"],
        )

    def _base_state(
        *,
        status: str,
        kind: str,
        permission: str,
        source_status: str,
        block_reason: str,
        receipt_status: str,
        receipt_kind: str,
        next_action: str,
        runtime_capability: str,
        attempted: int,
        completed: int,
        stop_reason: str,
        execution_mode: str,
        execution_ref: str,
        execution_receipt_status: str,
        execution_receipt_kind: str,
        execution_missing_inputs: list[str] | None = None,
        action_callability: str,
        action_callability_reason: str,
        action_required_inputs: list[str] | None = None,
        action_available_inputs: list[str] | None = None,
        action_missing_inputs: list[str] | None = None,
        action_builder_ref: str = "none",
        action_state_ref: str = "none",
        action_input_wiring_status: str = "insufficient_truth",
        action_input_wiring_reason: str = "insufficient_truth",
        candidate_safety_status: str = "insufficient_truth",
        candidate_safety_reason: str = "insufficient_truth",
        candidate_safety_evidence: list[str] | None = None,
        candidate_risk_flags: list[str] | None = None,
        candidate_receipt_evidence_status: str = "insufficient_truth",
        candidate_completion_evidence_status: str = "insufficient_truth",
        invocation_attempt_status: str = "insufficient_truth",
        invocation_attempt_reason: str = "insufficient_truth",
        invocation_result_status: str = "insufficient_truth",
        invocation_result_evidence: list[str] | None = None,
        completion_evidence_status: str = "insufficient_truth",
        completion_evidence_reason: str = "insufficient_truth_for_completion_evidence",
        completion_evidence_refs: list[str] | None = None,
        completion_result_status: str = "insufficient_truth",
        completion_result_reason: str = "insufficient_truth_for_completion_evidence",
        missing_completion_evidence_surfaces: list[str] | None = None,
        completion_allowed_refs: list[str] | None = None,
        actual_invocation_called: bool = False,
    ) -> dict[str, Any]:
        normalized_attempted = _as_non_negative_int(attempted, default=0)
        normalized_completed = _as_non_negative_int(completed, default=0)
        normalized_execution_ref = _normalize_text(execution_ref, default="none")
        normalized_execution_receipt_status = _normalize_text(
            execution_receipt_status,
            default="insufficient_truth",
        )
        normalized_execution_missing_inputs = _normalize_string_list(
            execution_missing_inputs or []
        )
        normalized_execution_mode = _normalize_text(
            execution_mode,
            default="insufficient_truth",
        )
        normalized_action_callability = _normalize_text(
            action_callability,
            default="insufficient_truth",
        )
        normalized_action_callability_reason = _normalize_text(
            action_callability_reason,
            default="insufficient_truth",
        )
        normalized_action_required_inputs = _normalize_string_list(
            action_required_inputs or []
        )
        normalized_action_available_inputs = _normalize_string_list(
            action_available_inputs or []
        )
        normalized_action_missing_inputs = _normalize_string_list(
            action_missing_inputs or []
        )
        normalized_action_builder_ref = _normalize_text(action_builder_ref, default="none")
        normalized_action_state_ref = _normalize_text(action_state_ref, default="none")
        normalized_action_input_wiring_status = _normalize_text(
            action_input_wiring_status,
            default="insufficient_truth",
        )
        normalized_action_input_wiring_reason = _normalize_text(
            action_input_wiring_reason,
            default="insufficient_truth",
        )
        normalized_candidate_safety_status = _normalize_text(
            candidate_safety_status,
            default="insufficient_truth",
        )
        normalized_candidate_safety_reason = _normalize_text(
            candidate_safety_reason,
            default="insufficient_truth",
        )
        normalized_candidate_safety_evidence = _normalize_string_list(
            candidate_safety_evidence or []
        )
        normalized_candidate_risk_flags = _normalize_string_list(
            candidate_risk_flags or []
        )
        normalized_candidate_receipt_evidence_status = _normalize_text(
            candidate_receipt_evidence_status,
            default="insufficient_truth",
        )
        normalized_candidate_completion_evidence_status = _normalize_text(
            candidate_completion_evidence_status,
            default="insufficient_truth",
        )
        normalized_invocation_attempt_status = _normalize_text(
            invocation_attempt_status,
            default="insufficient_truth",
        )
        normalized_invocation_attempt_reason = _normalize_text(
            invocation_attempt_reason,
            default="insufficient_truth",
        )
        normalized_invocation_result_status = _normalize_text(
            invocation_result_status,
            default="insufficient_truth",
        )
        normalized_invocation_result_evidence = _normalize_string_list(
            invocation_result_evidence or []
        )
        normalized_completion_evidence_status = _normalize_text(
            completion_evidence_status,
            default="insufficient_truth",
        )
        normalized_completion_evidence_reason = _normalize_text(
            completion_evidence_reason,
            default="insufficient_truth_for_completion_evidence",
        )
        normalized_completion_evidence_refs = _normalize_string_list(
            completion_evidence_refs or []
        )
        normalized_completion_result_status = _normalize_text(
            completion_result_status,
            default="insufficient_truth",
        )
        normalized_completion_result_reason = _normalize_text(
            completion_result_reason,
            default="insufficient_truth_for_completion_evidence",
        )
        normalized_missing_completion_evidence_surfaces = _normalize_string_list(
            missing_completion_evidence_surfaces or []
        )
        normalized_completion_allowed_refs = _normalize_string_list(
            completion_allowed_refs or []
        )
        allowed_action_callability_values = {
            "callable_candidate_inputs_ready",
            "state_only",
            "missing_inputs",
            "unsafe_to_reinvoke",
            "terminal_stop",
            "insufficient_truth",
        }
        if normalized_action_callability not in allowed_action_callability_values:
            normalized_action_callability = "insufficient_truth"
        available_required_inputs = set(normalized_action_required_inputs)
        normalized_action_available_inputs = [
            name
            for name in normalized_action_available_inputs
            if name in available_required_inputs
        ]
        derived_action_missing_inputs = [
            name
            for name in normalized_action_required_inputs
            if name not in set(normalized_action_available_inputs)
        ]
        if normalized_action_callability in {"terminal_stop", "insufficient_truth"}:
            normalized_action_required_inputs = []
            normalized_action_available_inputs = []
            normalized_action_missing_inputs = []
            normalized_action_builder_ref = "none"
            normalized_action_state_ref = "none"
        else:
            normalized_action_missing_inputs = derived_action_missing_inputs
        if normalized_action_input_wiring_status not in {
            "ready",
            "partial",
            "missing",
            "unsafe",
            "terminal_stop",
            "insufficient_truth",
        }:
            normalized_action_input_wiring_status = "insufficient_truth"
        if normalized_candidate_safety_status not in {
            "callable_candidate_safe",
            "unsafe_to_reinvoke",
            "state_only",
            "missing_inputs",
            "terminal_stop",
            "insufficient_truth",
        }:
            normalized_candidate_safety_status = "insufficient_truth"
        allowed_candidate_risk_flags = {
            "missing_inputs",
            "state_only",
            "unsafe_to_reinvoke",
            "duplicate_execution_risk",
            "github_mutation_risk",
            "new_executor_required",
            "queue_drain_risk",
            "unbounded_loop_risk",
            "receipt_evidence_missing",
            "completion_evidence_missing",
            "builder_mapping_mismatch",
            "action_state_ref_missing",
            "insufficient_truth",
        }
        normalized_candidate_risk_flags = [
            flag
            for flag in normalized_candidate_risk_flags
            if flag in allowed_candidate_risk_flags
        ]
        if normalized_candidate_receipt_evidence_status not in {
            "available",
            "unavailable",
            "unsafe",
            "terminal_stop",
            "insufficient_truth",
        }:
            normalized_candidate_receipt_evidence_status = "insufficient_truth"
        if normalized_candidate_completion_evidence_status not in {
            "available",
            "unavailable",
            "unsafe",
            "terminal_stop",
            "insufficient_truth",
        }:
            normalized_candidate_completion_evidence_status = "insufficient_truth"
        if normalized_invocation_attempt_status not in {
            "invoked_once",
            "not_invoked_candidate_not_safe",
            "not_invoked_missing_inputs",
            "not_invoked_hard_risk",
            "not_invoked_not_callable",
            "terminal_stop",
            "insufficient_truth",
        }:
            normalized_invocation_attempt_status = "insufficient_truth"
        if normalized_invocation_result_status not in {
            "receipt_ready",
            "receipt_unavailable",
            "receipt_failed",
            "not_invoked",
            "terminal_stop",
            "insufficient_truth",
        }:
            normalized_invocation_result_status = "insufficient_truth"
        if normalized_execution_mode not in {
            "existing_invocation_call_path_invoked",
            "prepared_only_invocation_not_callable",
            "terminal_stop",
            "insufficient_truth",
        }:
            normalized_execution_mode = "prepared_only_invocation_not_callable"
        if normalized_execution_mode != "prepared_only_invocation_not_callable":
            normalized_execution_missing_inputs = []
        if normalized_execution_mode in {"terminal_stop", "insufficient_truth"}:
            normalized_execution_ref = "none"
            normalized_execution_missing_inputs = []
        if normalized_candidate_safety_status == "terminal_stop":
            normalized_execution_mode = "terminal_stop"
            normalized_execution_ref = "none"
            normalized_execution_receipt_status = "ready"
            normalized_candidate_receipt_evidence_status = "terminal_stop"
            normalized_candidate_completion_evidence_status = "terminal_stop"
            normalized_invocation_attempt_status = "terminal_stop"
            normalized_invocation_result_status = "terminal_stop"
        elif normalized_candidate_safety_status == "insufficient_truth":
            normalized_execution_mode = "insufficient_truth"
            normalized_execution_ref = "none"
            normalized_execution_receipt_status = "insufficient_truth"
            normalized_candidate_receipt_evidence_status = "insufficient_truth"
            normalized_candidate_completion_evidence_status = "insufficient_truth"
            normalized_invocation_attempt_status = "insufficient_truth"
            normalized_invocation_result_status = "insufficient_truth"
        else:
            hard_risk_present = bool(
                set(normalized_candidate_risk_flags) & hard_risk_flags
            )
            actual_invocation_performed = (
                bool(actual_invocation_called)
                and normalized_execution_mode == "existing_invocation_call_path_invoked"
                and normalized_invocation_attempt_status == "invoked_once"
                and normalized_execution_ref != "none"
            )
            if not actual_invocation_performed:
                normalized_execution_mode = "prepared_only_invocation_not_callable"
                normalized_execution_ref = "none"
                normalized_execution_receipt_status = "unavailable"
            if normalized_execution_mode == "prepared_only_invocation_not_callable":
                normalized_execution_missing_inputs = [
                    input_name
                    for input_name in normalized_execution_missing_inputs
                    if input_name == "existing_invocation_call_path"
                ]
            normalized_attempted = 0
            if (
                actual_invocation_performed
                and normalized_candidate_safety_status == "callable_candidate_safe"
                and not hard_risk_present
                and normalized_action_input_wiring_status == "ready"
                and not normalized_action_missing_inputs
                and normalized_execution_receipt_status == "ready"
            ):
                normalized_attempted = 1
        if normalized_attempted > 1:
            normalized_attempted = 1
        if normalized_completion_evidence_status not in {
            "confirmed",
            "unavailable",
            "ambiguous",
            "failed",
            "not_attempted",
            "terminal_stop",
            "insufficient_truth",
        }:
            normalized_completion_evidence_status = "insufficient_truth"
        if normalized_completion_result_status not in {
            "completed",
            "not_completed",
            "failed",
            "not_attempted",
            "terminal_stop",
            "insufficient_truth",
        }:
            normalized_completion_result_status = "insufficient_truth"
        normalized_completion_evidence_refs = [
            ref_name
            for ref_name in normalized_completion_evidence_refs
            if ref_name not in generic_completion_evidence_refs
        ]
        normalized_missing_completion_evidence_surfaces = [
            surface_name
            for surface_name in normalized_missing_completion_evidence_surfaces
            if surface_name not in generic_completion_evidence_refs
        ]

        if normalized_candidate_safety_status == "terminal_stop":
            normalized_completion_evidence_status = "terminal_stop"
            normalized_completion_evidence_reason = "terminal_stop_no_completion_evaluation"
            normalized_completion_evidence_refs = []
            normalized_completion_result_status = "terminal_stop"
            normalized_completion_result_reason = "terminal_stop_no_completion_evaluation"
            normalized_missing_completion_evidence_surfaces = []
            normalized_completed = 0
        elif normalized_candidate_safety_status == "insufficient_truth":
            normalized_completion_evidence_status = "insufficient_truth"
            normalized_completion_evidence_reason = (
                "insufficient_truth_for_completion_evidence"
            )
            normalized_completion_evidence_refs = []
            normalized_completion_result_status = "insufficient_truth"
            normalized_completion_result_reason = (
                "insufficient_truth_for_completion_evidence"
            )
            normalized_missing_completion_evidence_surfaces = [
                "completion_evidence_truth"
            ]
            normalized_completed = 0
        elif normalized_attempted == 0:
            normalized_completion_evidence_status = "not_attempted"
            normalized_completion_evidence_reason = "no_invocation_attempted"
            normalized_completion_evidence_refs = []
            normalized_completion_result_status = "not_attempted"
            normalized_completion_result_reason = "no_invocation_attempted"
            normalized_missing_completion_evidence_surfaces = []
            normalized_completed = 0
        else:
            valid_completion_refs = [
                ref_name
                for ref_name in normalized_completion_evidence_refs
                if ref_name in normalized_completion_allowed_refs
            ]
            completion_refs_invalid = bool(
                normalized_completion_evidence_refs
                and len(valid_completion_refs) != len(normalized_completion_evidence_refs)
            )
            completion_refs_generic_only = not valid_completion_refs
            if normalized_completion_evidence_status == "confirmed":
                completion_guards_satisfied = bool(
                    normalized_attempted == 1
                    and normalized_completion_result_status == "completed"
                    and not completion_refs_invalid
                    and not completion_refs_generic_only
                    and normalized_execution_mode
                    != "prepared_only_invocation_not_callable"
                    and normalized_invocation_attempt_status == "invoked_once"
                    and normalized_invocation_result_status != "not_invoked"
                )
                if completion_guards_satisfied:
                    normalized_completion_evidence_reason = (
                        "explicit_completion_evidence_confirmed"
                    )
                    normalized_completion_result_reason = (
                        "explicit_completion_evidence_confirmed"
                    )
                    normalized_completion_evidence_refs = valid_completion_refs
                    normalized_missing_completion_evidence_surfaces = []
                    normalized_completed = 1
                else:
                    normalized_completion_result_status = "not_completed"
                    if completion_refs_invalid or completion_refs_generic_only:
                        normalized_completion_evidence_status = "unavailable"
                        normalized_completion_evidence_reason = (
                            "explicit_completion_evidence_missing"
                        )
                        normalized_completion_result_reason = (
                            "completion_evidence_unavailable"
                        )
                        normalized_missing_completion_evidence_surfaces = (
                            normalized_completion_allowed_refs
                        )
                    else:
                        normalized_completion_evidence_status = "ambiguous"
                        normalized_completion_evidence_reason = (
                            "completion_evidence_ambiguous"
                        )
                        normalized_completion_result_reason = (
                            "completion_evidence_ambiguous"
                        )
                        normalized_missing_completion_evidence_surfaces = []
                    normalized_completion_evidence_refs = valid_completion_refs
                    normalized_completed = 0
            elif normalized_completion_evidence_status == "failed":
                normalized_completion_evidence_reason = "completion_evidence_failed"
                normalized_completion_result_status = "failed"
                normalized_completion_result_reason = "completion_evidence_failed"
                normalized_completion_evidence_refs = valid_completion_refs
                normalized_missing_completion_evidence_surfaces = []
                normalized_completed = 0
            elif normalized_completion_evidence_status == "ambiguous":
                normalized_completion_evidence_reason = "completion_evidence_ambiguous"
                normalized_completion_result_status = "not_completed"
                normalized_completion_result_reason = "completion_evidence_ambiguous"
                normalized_completion_evidence_refs = valid_completion_refs
                normalized_missing_completion_evidence_surfaces = []
                normalized_completed = 0
            elif normalized_completion_evidence_status == "unavailable":
                normalized_completion_evidence_reason = "explicit_completion_evidence_missing"
                normalized_completion_evidence_refs = []
                normalized_completion_result_status = "not_completed"
                normalized_completion_result_reason = "completion_evidence_unavailable"
                normalized_missing_completion_evidence_surfaces = (
                    normalized_missing_completion_evidence_surfaces
                    or normalized_completion_allowed_refs
                )
                normalized_completed = 0
            elif normalized_completion_evidence_status == "insufficient_truth":
                normalized_completion_evidence_reason = (
                    "insufficient_truth_for_completion_evidence"
                )
                normalized_completion_evidence_refs = []
                normalized_completion_result_status = "insufficient_truth"
                normalized_completion_result_reason = (
                    "insufficient_truth_for_completion_evidence"
                )
                normalized_missing_completion_evidence_surfaces = [
                    "completion_evidence_truth"
                ]
                normalized_completed = 0
            else:
                normalized_completion_evidence_status = "unavailable"
                normalized_completion_evidence_reason = "explicit_completion_evidence_missing"
                normalized_completion_evidence_refs = []
                normalized_completion_result_status = "not_completed"
                normalized_completion_result_reason = "completion_evidence_unavailable"
                normalized_missing_completion_evidence_surfaces = (
                    normalized_completion_allowed_refs
                )
                normalized_completed = 0

        if normalized_completed > normalized_attempted:
            normalized_completed = normalized_attempted
        if normalized_completed > 1:
            normalized_completed = 1
        if normalized_attempted == 0:
            normalized_completed = 0

        return {
            "project_browser_autonomous_one_bounded_launch_status": status,
            "project_browser_autonomous_one_bounded_launch_kind": kind,
            "project_browser_autonomous_one_bounded_launch_permission": permission,
            "project_browser_autonomous_one_bounded_launch_source_status": source_status,
            "project_browser_autonomous_one_bounded_launch_block_reason": block_reason,
            "project_browser_autonomous_one_bounded_launch_receipt_status": receipt_status,
            "project_browser_autonomous_one_bounded_launch_receipt_kind": receipt_kind,
            "project_browser_autonomous_one_bounded_launch_next_action": next_action,
            "project_browser_autonomous_one_bounded_launch_runtime_capability": (
                runtime_capability
            ),
            "project_browser_autonomous_one_bounded_launch_invocation_next_action": (
                short_batch_invocation_next_action
            ),
            "project_browser_autonomous_one_bounded_launch_invocation_delegation_mode": (
                short_batch_invocation_delegation_mode
            ),
            "project_browser_autonomous_one_bounded_launch_invocation_call_path_ref": (
                short_batch_invocation_call_path_ref
            ),
            "project_browser_autonomous_one_bounded_launch_invocation_receipt_status": (
                short_batch_invocation_receipt_status
            ),
            "project_browser_autonomous_one_bounded_launch_execution_mode": (
                normalized_execution_mode
            ),
            "project_browser_autonomous_one_bounded_launch_execution_ref": (
                normalized_execution_ref
            ),
            "project_browser_autonomous_one_bounded_launch_execution_receipt_status": (
                normalized_execution_receipt_status
            ),
            "project_browser_autonomous_one_bounded_launch_execution_receipt_kind": (
                execution_receipt_kind
            ),
            "project_browser_autonomous_one_bounded_launch_execution_missing_inputs": (
                normalized_execution_missing_inputs
            ),
            "project_browser_autonomous_one_bounded_launch_action_callability": (
                normalized_action_callability
            ),
            "project_browser_autonomous_one_bounded_launch_action_callability_reason": (
                normalized_action_callability_reason
            ),
            "project_browser_autonomous_one_bounded_launch_action_required_inputs": (
                normalized_action_required_inputs
            ),
            "project_browser_autonomous_one_bounded_launch_action_available_inputs": (
                normalized_action_available_inputs
            ),
            "project_browser_autonomous_one_bounded_launch_action_missing_inputs": (
                normalized_action_missing_inputs
            ),
            "project_browser_autonomous_one_bounded_launch_action_builder_ref": (
                normalized_action_builder_ref
            ),
            "project_browser_autonomous_one_bounded_launch_action_state_ref": (
                normalized_action_state_ref
            ),
            "project_browser_autonomous_one_bounded_launch_action_input_wiring_status": (
                normalized_action_input_wiring_status
            ),
            "project_browser_autonomous_one_bounded_launch_action_input_wiring_reason": (
                normalized_action_input_wiring_reason
            ),
            "project_browser_autonomous_one_bounded_launch_candidate_safety_status": (
                normalized_candidate_safety_status
            ),
            "project_browser_autonomous_one_bounded_launch_candidate_safety_reason": (
                normalized_candidate_safety_reason
            ),
            "project_browser_autonomous_one_bounded_launch_candidate_safety_evidence": (
                normalized_candidate_safety_evidence
            ),
            "project_browser_autonomous_one_bounded_launch_candidate_risk_flags": (
                normalized_candidate_risk_flags
            ),
            "project_browser_autonomous_one_bounded_launch_candidate_receipt_evidence_status": (
                normalized_candidate_receipt_evidence_status
            ),
            "project_browser_autonomous_one_bounded_launch_candidate_completion_evidence_status": (
                normalized_candidate_completion_evidence_status
            ),
            "project_browser_autonomous_one_bounded_launch_invocation_attempt_status": (
                normalized_invocation_attempt_status
            ),
            "project_browser_autonomous_one_bounded_launch_invocation_attempt_reason": (
                normalized_invocation_attempt_reason
            ),
            "project_browser_autonomous_one_bounded_launch_invocation_result_status": (
                normalized_invocation_result_status
            ),
            "project_browser_autonomous_one_bounded_launch_invocation_result_evidence": (
                normalized_invocation_result_evidence
            ),
            "project_browser_autonomous_one_bounded_launch_completion_evidence_status": (
                normalized_completion_evidence_status
            ),
            "project_browser_autonomous_one_bounded_launch_completion_evidence_reason": (
                normalized_completion_evidence_reason
            ),
            "project_browser_autonomous_one_bounded_launch_completion_evidence_refs": (
                normalized_completion_evidence_refs
            ),
            "project_browser_autonomous_one_bounded_launch_completion_result_status": (
                normalized_completion_result_status
            ),
            "project_browser_autonomous_one_bounded_launch_completion_result_reason": (
                normalized_completion_result_reason
            ),
            "project_browser_autonomous_one_bounded_launch_missing_completion_evidence_surfaces": (
                normalized_missing_completion_evidence_surfaces
            ),
            "project_browser_autonomous_one_bounded_launch_attempted": normalized_attempted,
            "project_browser_autonomous_one_bounded_launch_completed": normalized_completed,
            "project_browser_autonomous_one_bounded_launch_max_steps": max_steps,
            "project_browser_autonomous_one_bounded_launch_failure_budget": failure_budget,
            "project_browser_autonomous_one_bounded_launch_stop_reason": stop_reason,
            "project_browser_autonomous_one_bounded_launch_runtime_posture": runtime_posture,
        }

    def _insufficient_truth_state() -> dict[str, Any]:
        return _base_state(
            status="insufficient_truth",
            kind="insufficient_truth_one_bounded_launch",
            permission="insufficient_truth",
            source_status="insufficient_truth",
            block_reason="insufficient_truth",
            receipt_status="insufficient_truth",
            receipt_kind="insufficient_truth_one_bounded_launch_receipt",
            next_action="none",
            runtime_capability="insufficient_truth",
            attempted=0,
            completed=0,
            stop_reason="insufficient_truth",
            execution_mode="insufficient_truth",
            execution_ref="none",
            execution_receipt_status="insufficient_truth",
            execution_receipt_kind="insufficient_truth_one_bounded_launch_invocation_receipt",
            execution_missing_inputs=[],
            action_callability="insufficient_truth",
            action_callability_reason="insufficient_truth",
            action_required_inputs=[],
            action_available_inputs=[],
            action_missing_inputs=[],
            candidate_safety_status="insufficient_truth",
            candidate_safety_reason="insufficient_truth",
            candidate_safety_evidence=["candidate_safety_insufficient_truth"],
            candidate_risk_flags=["insufficient_truth"],
            candidate_receipt_evidence_status="insufficient_truth",
            candidate_completion_evidence_status="insufficient_truth",
            invocation_attempt_status="insufficient_truth",
            invocation_attempt_reason="insufficient_truth",
            invocation_result_status="insufficient_truth",
            invocation_result_evidence=["invocation_bridge_insufficient_truth"],
            completion_evidence_status="insufficient_truth",
            completion_evidence_reason="insufficient_truth_for_completion_evidence",
            completion_evidence_refs=[],
            completion_result_status="insufficient_truth",
            completion_result_reason="insufficient_truth_for_completion_evidence",
            missing_completion_evidence_surfaces=["completion_evidence_truth"],
            completion_allowed_refs=[],
        )

    def _blocked_state(
        *,
        block_reason: str,
        action_callability: str = "state_only",
        action_callability_reason: str = "one_bounded_launch_gates_not_ready",
        action_required_inputs: list[str] | None = None,
        action_available_inputs: list[str] | None = None,
        action_missing_inputs: list[str] | None = None,
        action_builder_ref: str = "none",
        action_state_ref: str = "none",
        action_input_wiring_status: str = "insufficient_truth",
        action_input_wiring_reason: str = "insufficient_truth",
        candidate_safety_status: str = "state_only",
        candidate_safety_reason: str = "one_bounded_launch_gates_not_ready",
        candidate_safety_evidence: list[str] | None = None,
        candidate_risk_flags: list[str] | None = None,
        candidate_receipt_evidence_status: str = "unavailable",
        candidate_completion_evidence_status: str = "unavailable",
        invocation_attempt_status: str = "not_invoked_not_callable",
        invocation_attempt_reason: str = "one_bounded_launch_gates_not_ready",
        invocation_result_status: str = "not_invoked",
        invocation_result_evidence: list[str] | None = None,
    ) -> dict[str, Any]:
        return _base_state(
            status="blocked",
            kind="blocked_one_bounded_launch",
            permission="blocked",
            source_status="valid",
            block_reason=block_reason,
            receipt_status="blocked",
            receipt_kind="blocked_one_bounded_launch_receipt",
            next_action="none",
            runtime_capability="helper_missing_inputs",
            attempted=0,
            completed=0,
            stop_reason=block_reason,
            execution_mode="prepared_only_invocation_not_callable",
            execution_ref="none",
            execution_receipt_status="unavailable",
            execution_receipt_kind="one_bounded_launch_invocation_unavailable_receipt",
            execution_missing_inputs=[],
            action_callability=action_callability,
            action_callability_reason=action_callability_reason,
            action_required_inputs=action_required_inputs or [],
            action_available_inputs=action_available_inputs or [],
            action_missing_inputs=action_missing_inputs or [],
            action_builder_ref=action_builder_ref,
            action_state_ref=action_state_ref,
            action_input_wiring_status=action_input_wiring_status,
            action_input_wiring_reason=action_input_wiring_reason,
            candidate_safety_status=candidate_safety_status,
            candidate_safety_reason=candidate_safety_reason,
            candidate_safety_evidence=(
                candidate_safety_evidence
                if candidate_safety_evidence is not None
                else [
                    "one_bounded_launch_candidate_not_ready",
                    "actual_invocation_deferred",
                ]
            ),
            candidate_risk_flags=(
                candidate_risk_flags if candidate_risk_flags is not None else ["state_only"]
            ),
            candidate_receipt_evidence_status=candidate_receipt_evidence_status,
            candidate_completion_evidence_status=candidate_completion_evidence_status,
            invocation_attempt_status=invocation_attempt_status,
            invocation_attempt_reason=invocation_attempt_reason,
            invocation_result_status=invocation_result_status,
            invocation_result_evidence=(
                invocation_result_evidence
                if invocation_result_evidence is not None
                else ["no_actual_invocation_performed"]
            ),
            completion_evidence_status="not_attempted",
            completion_evidence_reason="no_invocation_attempted",
            completion_evidence_refs=[],
            completion_result_status="not_attempted",
            completion_result_reason="no_invocation_attempted",
            missing_completion_evidence_surfaces=[],
            completion_allowed_refs=[],
        )

    def _prepared_non_invoked_state(
        *,
        action_callability: str,
        action_callability_reason: str,
        action_required_inputs: list[str],
        action_available_inputs: list[str],
        action_missing_inputs: list[str],
        action_builder_ref: str,
        action_state_ref: str,
        action_input_wiring_status: str,
        action_input_wiring_reason: str,
        candidate_safety_status: str,
        candidate_safety_reason: str,
        candidate_safety_evidence: list[str],
        candidate_risk_flags: list[str],
        candidate_receipt_evidence_status: str,
        candidate_completion_evidence_status: str,
        invocation_attempt_status: str,
        invocation_attempt_reason: str,
        invocation_result_evidence: list[str],
    ) -> dict[str, Any]:
        return _base_state(
            status="prepared",
            kind="one_bounded_launch_prepared",
            permission="allowed_candidate",
            source_status="valid",
            block_reason="one_bounded_launch_invocation_not_callable",
            receipt_status="ready",
            receipt_kind="one_bounded_launch_prepared_receipt",
            next_action="invoke_existing_short_batch_call_path_once",
            runtime_capability="prepared_one_launch",
            attempted=0,
            completed=0,
            stop_reason="one_bounded_launch_invocation_not_callable",
            execution_mode="prepared_only_invocation_not_callable",
            execution_ref="none",
            execution_receipt_status="unavailable",
            execution_receipt_kind="one_bounded_launch_invocation_unavailable_receipt",
            execution_missing_inputs=[],
            action_callability=action_callability,
            action_callability_reason=action_callability_reason,
            action_required_inputs=action_required_inputs,
            action_available_inputs=action_available_inputs,
            action_missing_inputs=action_missing_inputs,
            action_builder_ref=action_builder_ref,
            action_state_ref=action_state_ref,
            action_input_wiring_status=action_input_wiring_status,
            action_input_wiring_reason=action_input_wiring_reason,
            candidate_safety_status=candidate_safety_status,
            candidate_safety_reason=candidate_safety_reason,
            candidate_safety_evidence=candidate_safety_evidence,
            candidate_risk_flags=candidate_risk_flags,
            candidate_receipt_evidence_status=candidate_receipt_evidence_status,
            candidate_completion_evidence_status=(
                candidate_completion_evidence_status
            ),
            invocation_attempt_status=invocation_attempt_status,
            invocation_attempt_reason=invocation_attempt_reason,
            invocation_result_status="not_invoked",
            invocation_result_evidence=invocation_result_evidence,
            completion_evidence_status="not_attempted",
            completion_evidence_reason="no_invocation_attempted",
            completion_evidence_refs=[],
            completion_result_status="not_attempted",
            completion_result_reason="no_invocation_attempted",
            missing_completion_evidence_surfaces=[],
            completion_allowed_refs=completion_evidence_ref_catalog.get(
                short_batch_invocation_next_action,
                [],
            ),
        )

    if rolling_execution_status not in {
        "prepared",
        "completed",
        "blocked",
        "insufficient_truth",
    }:
        return _insufficient_truth_state()
    if rolling_execution_permission not in _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS:
        return _insufficient_truth_state()
    if rolling_execution_source_status not in {"valid", "inconsistent", "insufficient_truth"}:
        return _insufficient_truth_state()
    if rolling_execution_receipt_status not in {"ready", "blocked", "insufficient_truth"}:
        return _insufficient_truth_state()
    if rolling_execution_runtime_capability not in {
        "prepared_only",
        "terminal_stop",
        "unavailable",
        "insufficient_truth",
    }:
        return _insufficient_truth_state()
    if rolling_multi_launch_status not in {
        "prepared",
        "blocked",
        "failed",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state()
    if rolling_multi_launch_permission not in _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS:
        return _insufficient_truth_state()
    if rolling_multi_launch_source_status not in {"valid", "inconsistent", "insufficient_truth"}:
        return _insufficient_truth_state()
    if rolling_multi_launch_receipt_status not in {
        "ready",
        "blocked",
        "failed",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state()
    if rolling_multi_launch_next_action not in {
        "none",
        "launch_up_to_two_short_batches",
        "hold_pause",
        "hold_human_review",
        "hold_insufficient_truth",
    }:
        return _insufficient_truth_state()
    if short_batch_invocation_path_status not in {"available", "unavailable", "insufficient_truth"}:
        return _insufficient_truth_state()
    if short_batch_invocation_runtime_capability not in {
        "actual_bounded_invocation",
        "partial_runtime_parts_available",
        "metadata_only",
        "unavailable",
        "insufficient_truth",
    }:
        return _insufficient_truth_state()
    if short_batch_invocation_receipt_status not in {
        "ready",
        "blocked",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state()
    if short_batch_invocation_delegation_mode not in {
        "invoked_existing_builder",
        "reused_existing_state_call_path",
        "not_callable_missing_inputs",
        "no_runtime_invocation_stop",
        "insufficient_truth",
    }:
        return _insufficient_truth_state()
    if short_batch_invocation_next_action not in {
        "none",
        "run_one_md_apply",
        "run_one_browser_command",
        "run_one_codex_attempt",
        "assimilate_result",
        "persist_ledger",
        "stop",
    }:
        return _insufficient_truth_state()

    if (
        rolling_execution_status == "insufficient_truth"
        or rolling_execution_permission == "insufficient_truth"
        or rolling_execution_source_status in {"inconsistent", "insufficient_truth"}
        or rolling_execution_receipt_status == "insufficient_truth"
        or rolling_execution_runtime_capability == "insufficient_truth"
        or rolling_multi_launch_status == "insufficient_truth"
        or rolling_multi_launch_permission == "insufficient_truth"
        or rolling_multi_launch_source_status in {"inconsistent", "insufficient_truth"}
        or rolling_multi_launch_receipt_status == "insufficient_truth"
        or short_batch_invocation_path_status == "insufficient_truth"
        or short_batch_invocation_runtime_capability == "insufficient_truth"
        or short_batch_invocation_receipt_status == "insufficient_truth"
        or short_batch_invocation_delegation_mode == "insufficient_truth"
    ):
        return _insufficient_truth_state()

    if short_batch_invocation_next_action == "stop":
        return _base_state(
            status="completed",
            kind="one_bounded_launch_terminal_stop",
            permission="blocked",
            source_status="valid",
            block_reason="stop_next_action",
            receipt_status="ready",
            receipt_kind="one_bounded_launch_terminal_stop_receipt",
            next_action="none",
            runtime_capability="terminal_stop",
            attempted=0,
            completed=0,
            stop_reason="stop_next_action",
            execution_mode="terminal_stop",
            execution_ref="none",
            execution_receipt_status="ready",
            execution_receipt_kind="one_bounded_launch_terminal_stop_receipt",
            execution_missing_inputs=[],
            action_callability="terminal_stop",
            action_callability_reason="stop_next_action",
            action_required_inputs=[],
            action_available_inputs=[],
            action_missing_inputs=[],
            action_builder_ref="none",
            action_state_ref="none",
            action_input_wiring_status="terminal_stop",
            action_input_wiring_reason="stop_next_action",
            candidate_safety_status="terminal_stop",
            candidate_safety_reason="stop_next_action",
            candidate_safety_evidence=["terminal_stop_no_runtime_invocation"],
            candidate_risk_flags=[],
            candidate_receipt_evidence_status="terminal_stop",
            candidate_completion_evidence_status="terminal_stop",
            invocation_attempt_status="terminal_stop",
            invocation_attempt_reason="stop_next_action",
            invocation_result_status="terminal_stop",
            invocation_result_evidence=["terminal_stop_no_runtime_invocation"],
            completion_evidence_status="terminal_stop",
            completion_evidence_reason="terminal_stop_no_completion_evaluation",
            completion_evidence_refs=[],
            completion_result_status="terminal_stop",
            completion_result_reason="terminal_stop_no_completion_evaluation",
            missing_completion_evidence_surfaces=[],
            completion_allowed_refs=[],
        )

    if (
        rolling_execution_status != "prepared"
        or rolling_execution_permission != "allowed_candidate"
        or rolling_execution_receipt_status != "ready"
        or rolling_execution_runtime_capability != "prepared_only"
        or rolling_execution_launches_allowed != 2
        or rolling_execution_launches_attempted != 0
        or rolling_execution_launches_completed != 0
    ):
        return _blocked_state(
            block_reason="rolling_execution_not_ready",
            invocation_attempt_reason="rolling_execution_not_ready",
        )
    if rolling_multi_launch_next_action != "launch_up_to_two_short_batches":
        return _blocked_state(
            block_reason="rolling_multi_launch_action_not_launch",
            invocation_attempt_reason="rolling_multi_launch_action_not_launch",
        )
    if (
        rolling_multi_launch_status != "prepared"
        or rolling_multi_launch_permission != "allowed_candidate"
        or rolling_multi_launch_receipt_status != "ready"
    ):
        return _blocked_state(
            block_reason="rolling_multi_launch_not_ready",
            invocation_attempt_reason="rolling_multi_launch_not_ready",
        )
    if short_batch_invocation_path_status != "available":
        return _blocked_state(
            block_reason="short_batch_invocation_path_unavailable",
            invocation_attempt_reason="short_batch_invocation_path_unavailable",
        )
    if short_batch_invocation_runtime_capability != "actual_bounded_invocation":
        return _blocked_state(
            block_reason="short_batch_invocation_not_actual",
            invocation_attempt_reason="short_batch_invocation_not_actual",
        )
    if short_batch_invocation_receipt_status != "ready":
        return _blocked_state(
            block_reason="short_batch_invocation_receipt_not_ready",
            invocation_attempt_reason="short_batch_invocation_receipt_not_ready",
        )
    if short_batch_invocation_delegation_mode not in {
        "reused_existing_state_call_path",
        "invoked_existing_builder",
    }:
        return _blocked_state(
            block_reason="short_batch_invocation_delegation_not_allowed",
            invocation_attempt_reason="short_batch_invocation_delegation_not_allowed",
        )
    if short_batch_invocation_next_action not in invocation_action_bridge_config:
        return _blocked_state(
            block_reason="short_batch_invocation_not_actual",
            invocation_attempt_reason="short_batch_invocation_not_actual",
        )
    action_bridge_config = invocation_action_bridge_config.get(
        short_batch_invocation_next_action,
        {},
    )
    selected_action_builder_ref = _normalize_text(
        action_bridge_config.get("builder_ref"),
        default="none",
    )
    expected_invocation_call_path_ref = _normalize_text(
        action_bridge_config.get("state_ref"),
        default="none",
    )
    action_required_inputs = _normalize_string_list(
        action_bridge_config.get("required_inputs")
    )
    action_receipt_evidence_inputs = _normalize_string_list(
        action_bridge_config.get("receipt_evidence_inputs")
    )
    action_completion_evidence_inputs = _normalize_string_list(
        action_bridge_config.get("completion_evidence_inputs")
    )
    action_source_var_by_required_input = (
        dict(action_bridge_config.get("source_var_by_required_input", {}))
        if isinstance(action_bridge_config.get("source_var_by_required_input"), Mapping)
        else {}
    )

    def _default_source_var_for_required_input(required_input: str) -> str:
        if required_input.startswith("autonomous_"):
            return f"project_browser_{required_input}"
        return required_input

    def _mapped_source_var_for_required_input(required_input: str) -> str:
        override_var = _normalize_text(
            action_source_var_by_required_input.get(required_input),
            default="",
        )
        if override_var:
            return override_var
        return _default_source_var_for_required_input(required_input)

    action_available_inputs = [
        input_name
        for input_name in action_required_inputs
        if _mapped_source_var_for_required_input(input_name)
        in one_bounded_launch_callsite_available_vars
    ]
    action_missing_inputs = [
        input_name
        for input_name in action_required_inputs
        if input_name not in set(action_available_inputs)
    ]

    def _all_scope_fields_available(field_names: list[str]) -> bool:
        return bool(field_names) and all(
            _normalize_text(field_name, default="") in one_bounded_launch_callsite_available_vars
            for field_name in field_names
        )

    def _collect_invocation_kwargs(
        required_inputs: list[str],
    ) -> tuple[dict[str, Any], list[str]]:
        invocation_kwargs: dict[str, Any] = {}
        missing_callsite_inputs: list[str] = []
        for required_input in required_inputs:
            source_var = _mapped_source_var_for_required_input(required_input)
            if source_var not in one_bounded_launch_callsite_values:
                missing_callsite_inputs.append(required_input)
                continue
            invocation_kwargs[required_input] = one_bounded_launch_callsite_values[source_var]
        return invocation_kwargs, missing_callsite_inputs

    def _map_invocation_receipt_status(
        raw_receipt_status: str,
    ) -> tuple[str, str, str]:
        normalized_raw_receipt_status = _normalize_text(
            raw_receipt_status,
            default="unavailable",
        )
        if normalized_raw_receipt_status == "ready":
            return (
                "ready",
                "one_bounded_launch_invocation_receipt",
                "receipt_ready",
            )
        if normalized_raw_receipt_status == "failed":
            return (
                "failed",
                "failed_one_bounded_launch_invocation_receipt",
                "receipt_failed",
            )
        if normalized_raw_receipt_status == "timeout":
            return (
                "timeout",
                "timeout_one_bounded_launch_invocation_receipt",
                "receipt_failed",
            )
        if normalized_raw_receipt_status == "blocked":
            return (
                "blocked",
                "blocked_one_bounded_launch_invocation_receipt",
                "receipt_unavailable",
            )
        return (
            "unavailable",
            "one_bounded_launch_invocation_unavailable_receipt",
            "receipt_unavailable",
        )

    def _collect_invocation_result_evidence(invoked_state: Mapping[str, Any]) -> list[str]:
        evidence: list[str] = []
        for field_name in (
            action_receipt_evidence_inputs + action_completion_evidence_inputs
        ):
            normalized_field_name = _normalize_text(field_name, default="")
            if not normalized_field_name:
                continue
            raw_value = invoked_state.get(normalized_field_name)
            if raw_value is None:
                continue
            if isinstance(raw_value, (str, int, float, bool)):
                normalized_value = _normalize_text(str(raw_value), default="")
            else:
                normalized_value = ""
            if normalized_value:
                evidence.append(f"{normalized_field_name}={normalized_value}")
            if len(evidence) >= 8:
                break
        return evidence

    if expected_invocation_call_path_ref == "none":
        return _insufficient_truth_state()
    if short_batch_invocation_call_path_ref != expected_invocation_call_path_ref:
        return _prepared_non_invoked_state(
            action_callability="unsafe_to_reinvoke",
            action_callability_reason="selected_action_unsafe_to_reinvoke",
            action_required_inputs=action_required_inputs,
            action_available_inputs=action_available_inputs,
            action_missing_inputs=[],
            action_builder_ref=selected_action_builder_ref,
            action_state_ref=expected_invocation_call_path_ref,
            action_input_wiring_status="unsafe",
            action_input_wiring_reason="selected_action_unsafe_to_reinvoke",
            candidate_safety_status="unsafe_to_reinvoke",
            candidate_safety_reason="selected_action_candidate_has_hard_risk",
            candidate_safety_evidence=[
                "selected_action_mapping_unverified",
                "actual_invocation_deferred",
            ],
            candidate_risk_flags=[
                "unsafe_to_reinvoke",
                "builder_mapping_mismatch",
                "action_state_ref_missing",
            ],
            candidate_receipt_evidence_status="unsafe",
            candidate_completion_evidence_status="unsafe",
            invocation_attempt_status="not_invoked_hard_risk",
            invocation_attempt_reason="selected_action_mapping_unverified",
            invocation_result_evidence=["selected_action_mapping_unverified"],
        )
    if short_batch_invocation_call_path_ref in {"", "none"}:
        return _prepared_non_invoked_state(
            action_callability="unsafe_to_reinvoke",
            action_callability_reason="selected_action_unsafe_to_reinvoke",
            action_required_inputs=action_required_inputs,
            action_available_inputs=action_available_inputs,
            action_missing_inputs=[],
            action_builder_ref=selected_action_builder_ref,
            action_state_ref=expected_invocation_call_path_ref,
            action_input_wiring_status="unsafe",
            action_input_wiring_reason="selected_action_unsafe_to_reinvoke",
            candidate_safety_status="unsafe_to_reinvoke",
            candidate_safety_reason="selected_action_candidate_has_hard_risk",
            candidate_safety_evidence=[
                "selected_action_mapping_unverified",
                "actual_invocation_deferred",
            ],
            candidate_risk_flags=["unsafe_to_reinvoke", "action_state_ref_missing"],
            candidate_receipt_evidence_status="unsafe",
            candidate_completion_evidence_status="unsafe",
            invocation_attempt_status="not_invoked_hard_risk",
            invocation_attempt_reason="selected_action_call_path_missing",
            invocation_result_evidence=["selected_action_call_path_missing"],
        )
    if short_batch_invocation_missing_inputs:
        action_input_wiring_status = (
            "partial" if action_available_inputs else "missing"
        )
        action_input_wiring_reason = (
            "selected_action_partial_inputs"
            if action_input_wiring_status == "partial"
            else "selected_action_missing_inputs"
        )
        return _prepared_non_invoked_state(
            action_callability="missing_inputs",
            action_callability_reason=action_input_wiring_reason,
            action_required_inputs=action_required_inputs,
            action_available_inputs=action_available_inputs,
            action_missing_inputs=action_missing_inputs,
            action_builder_ref=selected_action_builder_ref,
            action_state_ref=expected_invocation_call_path_ref,
            action_input_wiring_status=action_input_wiring_status,
            action_input_wiring_reason=action_input_wiring_reason,
            candidate_safety_status="missing_inputs",
            candidate_safety_reason="selected_action_missing_inputs",
            candidate_safety_evidence=[
                "required_inputs_not_fully_available",
                "actual_invocation_deferred",
            ],
            candidate_risk_flags=[],
            candidate_receipt_evidence_status="unavailable",
            candidate_completion_evidence_status="unavailable",
            invocation_attempt_status="not_invoked_missing_inputs",
            invocation_attempt_reason=action_input_wiring_reason,
            invocation_result_evidence=["selected_action_missing_inputs"],
        )
    if action_missing_inputs:
        action_input_wiring_status = (
            "partial" if action_available_inputs else "missing"
        )
        action_input_wiring_reason = (
            "selected_action_partial_inputs"
            if action_input_wiring_status == "partial"
            else "selected_action_missing_inputs"
        )
        return _prepared_non_invoked_state(
            action_callability="missing_inputs",
            action_callability_reason=action_input_wiring_reason,
            action_required_inputs=action_required_inputs,
            action_available_inputs=action_available_inputs,
            action_missing_inputs=action_missing_inputs,
            action_builder_ref=selected_action_builder_ref,
            action_state_ref=expected_invocation_call_path_ref,
            action_input_wiring_status=action_input_wiring_status,
            action_input_wiring_reason=action_input_wiring_reason,
            candidate_safety_status="missing_inputs",
            candidate_safety_reason="selected_action_missing_inputs",
            candidate_safety_evidence=[
                "required_inputs_not_fully_available",
                "actual_invocation_deferred",
            ],
            candidate_risk_flags=[],
            candidate_receipt_evidence_status="unavailable",
            candidate_completion_evidence_status="unavailable",
            invocation_attempt_status="not_invoked_missing_inputs",
            invocation_attempt_reason=action_input_wiring_reason,
            invocation_result_evidence=["required_inputs_not_fully_available"],
        )

    candidate_risk_flags: list[str] = []
    candidate_safety_evidence = [
        "required_inputs_available",
        "selected_action_mapping_verified",
        "one_invocation_only",
        "no_new_executor_required",
        "no_max_two_launch_in_prompt144",
        "no_actual_invocation_in_prompt144",
    ]
    if selected_action_builder_ref == "none":
        candidate_risk_flags.append("builder_mapping_mismatch")
    if expected_invocation_call_path_ref == "none":
        candidate_risk_flags.append("action_state_ref_missing")
    if not action_required_inputs:
        candidate_risk_flags.append("insufficient_truth")
    receipt_evidence_available = _all_scope_fields_available(action_receipt_evidence_inputs)
    completion_evidence_available = _all_scope_fields_available(
        action_completion_evidence_inputs
    )
    if not receipt_evidence_available:
        candidate_risk_flags.append("receipt_evidence_missing")
    if receipt_evidence_available and not completion_evidence_available:
        candidate_risk_flags.append("completion_evidence_missing")
    if set(candidate_risk_flags) & hard_risk_flags:
        return _prepared_non_invoked_state(
            action_callability="unsafe_to_reinvoke",
            action_callability_reason="selected_action_unsafe_to_reinvoke",
            action_required_inputs=action_required_inputs,
            action_available_inputs=action_available_inputs,
            action_missing_inputs=[],
            action_builder_ref=selected_action_builder_ref,
            action_state_ref=expected_invocation_call_path_ref,
            action_input_wiring_status="unsafe",
            action_input_wiring_reason="selected_action_unsafe_to_reinvoke",
            candidate_safety_status="unsafe_to_reinvoke",
            candidate_safety_reason="selected_action_candidate_has_hard_risk",
            candidate_safety_evidence=[
                "selected_action_mapping_verified",
                "actual_invocation_deferred",
            ],
            candidate_risk_flags=["unsafe_to_reinvoke", *candidate_risk_flags],
            candidate_receipt_evidence_status="unsafe",
            candidate_completion_evidence_status="unsafe",
            invocation_attempt_status="not_invoked_hard_risk",
            invocation_attempt_reason="selected_action_candidate_has_hard_risk",
            invocation_result_evidence=["hard_risk_flags_present"],
        )
    if not receipt_evidence_available:
        return _prepared_non_invoked_state(
            action_callability="state_only",
            action_callability_reason="selected_action_state_only",
            action_required_inputs=action_required_inputs,
            action_available_inputs=action_available_inputs,
            action_missing_inputs=[],
            action_builder_ref=selected_action_builder_ref,
            action_state_ref=expected_invocation_call_path_ref,
            action_input_wiring_status="ready",
            action_input_wiring_reason="selected_action_inputs_ready",
            candidate_safety_status="state_only",
            candidate_safety_reason="selected_action_state_only",
            candidate_safety_evidence=[
                "receipt_evidence_unavailable",
                "actual_invocation_deferred",
            ],
            candidate_risk_flags=["state_only", "receipt_evidence_missing"],
            candidate_receipt_evidence_status="unavailable",
            candidate_completion_evidence_status="unavailable",
            invocation_attempt_status="not_invoked_candidate_not_safe",
            invocation_attempt_reason="selected_action_state_only",
            invocation_result_evidence=["receipt_evidence_unavailable"],
        )
    selected_action_builder = invocation_builder_by_ref.get(selected_action_builder_ref)
    if selected_action_builder is None:
        return _prepared_non_invoked_state(
            action_callability="callable_candidate_inputs_ready",
            action_callability_reason="selected_action_inputs_ready",
            action_required_inputs=action_required_inputs,
            action_available_inputs=action_available_inputs,
            action_missing_inputs=[],
            action_builder_ref=selected_action_builder_ref,
            action_state_ref=expected_invocation_call_path_ref,
            action_input_wiring_status="ready",
            action_input_wiring_reason="selected_action_inputs_ready",
            candidate_safety_status="callable_candidate_safe",
            candidate_safety_reason="selected_action_candidate_safe_for_one_invocation",
            candidate_safety_evidence=candidate_safety_evidence,
            candidate_risk_flags=candidate_risk_flags,
            candidate_receipt_evidence_status="available",
            candidate_completion_evidence_status=(
                "available" if completion_evidence_available else "unavailable"
            ),
            invocation_attempt_status="not_invoked_not_callable",
            invocation_attempt_reason=(
                "existing_invocation_call_path_not_callable_from_this_location"
            ),
            invocation_result_evidence=["builder_callable_missing_at_callsite"],
        )
    invocation_kwargs, missing_callsite_inputs = _collect_invocation_kwargs(
        action_required_inputs
    )
    if missing_callsite_inputs:
        return _prepared_non_invoked_state(
            action_callability="callable_candidate_inputs_ready",
            action_callability_reason="selected_action_inputs_ready",
            action_required_inputs=action_required_inputs,
            action_available_inputs=action_available_inputs,
            action_missing_inputs=[],
            action_builder_ref=selected_action_builder_ref,
            action_state_ref=expected_invocation_call_path_ref,
            action_input_wiring_status="ready",
            action_input_wiring_reason="selected_action_inputs_ready",
            candidate_safety_status="callable_candidate_safe",
            candidate_safety_reason="selected_action_candidate_safe_for_one_invocation",
            candidate_safety_evidence=candidate_safety_evidence,
            candidate_risk_flags=candidate_risk_flags,
            candidate_receipt_evidence_status="available",
            candidate_completion_evidence_status=(
                "available" if completion_evidence_available else "unavailable"
            ),
            invocation_attempt_status="not_invoked_not_callable",
            invocation_attempt_reason=(
                "existing_invocation_call_path_not_callable_from_this_location"
            ),
            invocation_result_evidence=[
                "existing_invocation_call_path_not_callable_from_this_location",
                *missing_callsite_inputs,
            ],
        )
    invoked_state = selected_action_builder(**invocation_kwargs)
    if not isinstance(invoked_state, Mapping):
        return _prepared_non_invoked_state(
            action_callability="callable_candidate_inputs_ready",
            action_callability_reason="selected_action_inputs_ready",
            action_required_inputs=action_required_inputs,
            action_available_inputs=action_available_inputs,
            action_missing_inputs=[],
            action_builder_ref=selected_action_builder_ref,
            action_state_ref=expected_invocation_call_path_ref,
            action_input_wiring_status="ready",
            action_input_wiring_reason="selected_action_inputs_ready",
            candidate_safety_status="callable_candidate_safe",
            candidate_safety_reason="selected_action_candidate_safe_for_one_invocation",
            candidate_safety_evidence=candidate_safety_evidence,
            candidate_risk_flags=candidate_risk_flags,
            candidate_receipt_evidence_status="available",
            candidate_completion_evidence_status=(
                "available" if completion_evidence_available else "unavailable"
            ),
            invocation_attempt_status="not_invoked_not_callable",
            invocation_attempt_reason=(
                "existing_invocation_call_path_not_callable_from_this_location"
            ),
            invocation_result_evidence=["existing_invocation_call_path_return_invalid"],
        )
    invoked_receipt_status_field = (
        action_receipt_evidence_inputs[0] if action_receipt_evidence_inputs else ""
    )
    invoked_receipt_status_raw = _normalize_text(
        invoked_state.get(invoked_receipt_status_field),
        default="unavailable",
    )
    (
        execution_receipt_status,
        execution_receipt_kind,
        invocation_result_status,
    ) = _map_invocation_receipt_status(invoked_receipt_status_raw)
    invocation_result_evidence = _collect_invocation_result_evidence(invoked_state)
    if not invocation_result_evidence:
        invocation_result_evidence = [
            "existing_invocation_call_path_invoked",
            f"receipt_status={invoked_receipt_status_raw}",
        ]
    completion_evidence_state = _evaluate_action_completion_evidence(
        action_name=short_batch_invocation_next_action,
        invoked_state=invoked_state,
    )

    return _base_state(
        status="prepared",
        kind="one_bounded_launch_prepared",
        permission="allowed_candidate",
        source_status="valid",
        block_reason="none",
        receipt_status="ready",
        receipt_kind="one_bounded_launch_prepared_receipt",
        next_action="invoke_existing_short_batch_call_path_once",
        runtime_capability="prepared_one_launch",
        attempted=1,
        completed=0,
        stop_reason="none",
        execution_mode="existing_invocation_call_path_invoked",
        execution_ref=selected_action_builder_ref,
        execution_receipt_status=execution_receipt_status,
        execution_receipt_kind=execution_receipt_kind,
        execution_missing_inputs=[],
        action_callability="callable_candidate_inputs_ready",
        action_callability_reason="selected_action_inputs_ready",
        action_required_inputs=action_required_inputs,
        action_available_inputs=action_available_inputs,
        action_missing_inputs=[],
        action_builder_ref=selected_action_builder_ref,
        action_state_ref=expected_invocation_call_path_ref,
        action_input_wiring_status="ready",
        action_input_wiring_reason="selected_action_inputs_ready",
        candidate_safety_status="callable_candidate_safe",
        candidate_safety_reason="selected_action_candidate_safe_for_one_invocation",
        candidate_safety_evidence=candidate_safety_evidence,
        candidate_risk_flags=candidate_risk_flags,
        candidate_receipt_evidence_status="available",
        candidate_completion_evidence_status=(
            "available" if completion_evidence_available else "unavailable"
        ),
        invocation_attempt_status="invoked_once",
        invocation_attempt_reason="existing_invocation_call_path_invoked_once",
        invocation_result_status=invocation_result_status,
        invocation_result_evidence=invocation_result_evidence,
        completion_evidence_status=_normalize_text(
            completion_evidence_state.get("completion_evidence_status"),
            default="unavailable",
        ),
        completion_evidence_reason=_normalize_text(
            completion_evidence_state.get("completion_evidence_reason"),
            default="explicit_completion_evidence_missing",
        ),
        completion_evidence_refs=_normalize_string_list(
            completion_evidence_state.get("completion_evidence_refs")
        ),
        completion_result_status=_normalize_text(
            completion_evidence_state.get("completion_result_status"),
            default="not_completed",
        ),
        completion_result_reason=_normalize_text(
            completion_evidence_state.get("completion_result_reason"),
            default="completion_evidence_unavailable",
        ),
        missing_completion_evidence_surfaces=_normalize_string_list(
            completion_evidence_state.get("missing_completion_evidence_surfaces")
        ),
        completion_allowed_refs=_normalize_string_list(
            completion_evidence_state.get("completion_allowed_refs")
        ),
        actual_invocation_called=True,
    )

def _build_project_browser_autonomous_two_launch_preparation_state(
    *,
    autonomous_one_bounded_launch_attempted: int,
    autonomous_one_bounded_launch_completed: int,
    autonomous_one_bounded_launch_completion_evidence_status: str,
    autonomous_one_bounded_launch_completion_result_status: str,
    autonomous_one_bounded_launch_stop_reason: str,
    autonomous_short_batch_invocation_path_status: str,
    autonomous_short_batch_invocation_runtime_capability: str,
    autonomous_short_batch_invocation_receipt_status: str,
    autonomous_short_batch_invocation_missing_inputs: list[str] | None,
    autonomous_cooldown_status: str,
    autonomous_loop_risk_status: str,
    autonomous_run_ledger_duplicate_status: str,
    autonomous_watchdog_duplicate_receipt_posture: str,
    autonomous_short_batch_failures: int,
    autonomous_rolling_multi_launch_failure_budget: int,
    autonomous_two_launch_callsite_available_vars: list[str] | None,
) -> dict[str, Any]:
    launch_1_attempted = _as_non_negative_int(
        autonomous_one_bounded_launch_attempted,
        default=0,
    )
    if launch_1_attempted > 1:
        launch_1_attempted = 1
    launch_1_completed = _as_non_negative_int(
        autonomous_one_bounded_launch_completed,
        default=0,
    )
    if launch_1_completed > 1:
        launch_1_completed = 1
    completion_evidence_status = _normalize_text(
        autonomous_one_bounded_launch_completion_evidence_status,
        default="insufficient_truth",
    )
    if completion_evidence_status not in {
        "confirmed",
        "unavailable",
        "ambiguous",
        "failed",
        "not_attempted",
        "terminal_stop",
        "insufficient_truth",
    }:
        completion_evidence_status = "insufficient_truth"
    completion_result_status = _normalize_text(
        autonomous_one_bounded_launch_completion_result_status,
        default="insufficient_truth",
    )
    if completion_result_status not in {
        "completed",
        "not_completed",
        "failed",
        "not_attempted",
        "terminal_stop",
        "insufficient_truth",
    }:
        completion_result_status = "insufficient_truth"
    launch_1_stop_reason = _normalize_text(
        autonomous_one_bounded_launch_stop_reason,
        default="insufficient_truth",
    )
    short_batch_invocation_path_status = _normalize_text(
        autonomous_short_batch_invocation_path_status,
        default="insufficient_truth",
    )
    if short_batch_invocation_path_status not in {
        "available",
        "unavailable",
        "insufficient_truth",
    }:
        short_batch_invocation_path_status = "insufficient_truth"
    short_batch_invocation_runtime_capability = _normalize_text(
        autonomous_short_batch_invocation_runtime_capability,
        default="insufficient_truth",
    )
    if short_batch_invocation_runtime_capability not in {
        "actual_bounded_invocation",
        "partial_runtime_parts_available",
        "metadata_only",
        "unavailable",
        "insufficient_truth",
    }:
        short_batch_invocation_runtime_capability = "insufficient_truth"
    short_batch_invocation_receipt_status = _normalize_text(
        autonomous_short_batch_invocation_receipt_status,
        default="insufficient_truth",
    )
    if short_batch_invocation_receipt_status not in {
        "ready",
        "blocked",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        short_batch_invocation_receipt_status = "insufficient_truth"
    short_batch_invocation_missing_inputs = _normalize_string_list(
        autonomous_short_batch_invocation_missing_inputs or []
    )
    cooldown_status = _normalize_text(
        autonomous_cooldown_status,
        default="insufficient_truth",
    )
    if cooldown_status not in {
        "not_required",
        "required",
        "blocked",
        "insufficient_truth",
    }:
        cooldown_status = "insufficient_truth"
    loop_risk_status = _normalize_text(
        autonomous_loop_risk_status,
        default="insufficient_truth",
    )
    if loop_risk_status not in {"clear", "suspected", "blocked", "insufficient_truth"}:
        loop_risk_status = "insufficient_truth"
    run_ledger_duplicate_status = _normalize_text(
        autonomous_run_ledger_duplicate_status,
        default="insufficient_truth",
    )
    if run_ledger_duplicate_status not in {
        "clear",
        "duplicate_detected",
        "insufficient_truth",
    }:
        run_ledger_duplicate_status = "insufficient_truth"
    watchdog_duplicate_receipt_posture = _normalize_text(
        autonomous_watchdog_duplicate_receipt_posture,
        default="insufficient_truth",
    )
    if watchdog_duplicate_receipt_posture not in {
        "clear",
        "duplicate_detected",
        "insufficient_truth",
    }:
        watchdog_duplicate_receipt_posture = "insufficient_truth"
    short_batch_failures = _as_non_negative_int(
        autonomous_short_batch_failures,
        default=0,
    )
    rolling_multi_launch_failure_budget = _as_non_negative_int(
        autonomous_rolling_multi_launch_failure_budget,
        default=0,
    )

    callsite_available_vars = set(
        _normalize_string_list(autonomous_two_launch_callsite_available_vars or [])
    )
    launch_2_required_inputs = [
        "project_browser_autonomous_one_bounded_launch_attempted",
        "project_browser_autonomous_one_bounded_launch_completed",
        "project_browser_autonomous_one_bounded_launch_completion_evidence_status",
        "project_browser_autonomous_one_bounded_launch_completion_result_status",
        "project_browser_autonomous_one_bounded_launch_stop_reason",
        "project_browser_autonomous_short_batch_invocation_path_status",
        "project_browser_autonomous_short_batch_invocation_runtime_capability",
        "project_browser_autonomous_short_batch_invocation_receipt_status",
        "project_browser_autonomous_short_batch_invocation_missing_inputs",
        "project_browser_autonomous_cooldown_status",
        "project_browser_autonomous_loop_risk_status",
        "project_browser_autonomous_run_ledger_duplicate_status",
        "project_browser_autonomous_watchdog_duplicate_receipt_posture",
        "project_browser_autonomous_short_batch_failures",
        "project_browser_autonomous_rolling_multi_launch_failure_budget",
    ]
    launch_2_available_inputs = [
        input_name
        for input_name in launch_2_required_inputs
        if input_name in callsite_available_vars
    ]

    def _base_state(
        *,
        preparation_status: str,
        preparation_permission: str,
        preparation_reason: str,
        preparation_receipt_status: str,
        launch_1_status: str,
        launch_1_result_status: str,
        launch_2_candidate_status: str,
        launch_2_permission: str,
        launch_2_block_reason: str,
        launch_2_allowed: int,
        launch_2_next_action: str,
    ) -> dict[str, Any]:
        normalized_preparation_status = _normalize_text(
            preparation_status,
            default="insufficient_truth",
        )
        if normalized_preparation_status not in {
            "prepared",
            "blocked",
            "terminal_stop",
            "insufficient_truth",
        }:
            normalized_preparation_status = "insufficient_truth"
        normalized_preparation_permission = _normalize_text(
            preparation_permission,
            default="insufficient_truth",
        )
        if normalized_preparation_permission not in {
            "allowed_candidate",
            "blocked",
            "not_applicable",
            "insufficient_truth",
        }:
            normalized_preparation_permission = "insufficient_truth"
        normalized_preparation_reason = _normalize_text(
            preparation_reason,
            default="insufficient_truth",
        )
        normalized_preparation_receipt_status = _normalize_text(
            preparation_receipt_status,
            default="insufficient_truth",
        )
        if normalized_preparation_receipt_status not in {
            "ready",
            "blocked",
            "insufficient_truth",
        }:
            normalized_preparation_receipt_status = "insufficient_truth"
        normalized_launch_1_status = _normalize_text(
            launch_1_status,
            default="insufficient_truth",
        )
        if normalized_launch_1_status not in {
            "completed",
            "attempted_not_completed",
            "not_attempted",
            "blocked",
            "terminal_stop",
            "insufficient_truth",
        }:
            normalized_launch_1_status = "insufficient_truth"
        normalized_launch_1_result_status = _normalize_text(
            launch_1_result_status,
            default="insufficient_truth",
        )
        if normalized_launch_1_result_status not in {
            "completed",
            "not_completed",
            "failed",
            "blocked",
            "not_attempted",
            "terminal_stop",
            "insufficient_truth",
        }:
            normalized_launch_1_result_status = "insufficient_truth"
        normalized_launch_2_candidate_status = _normalize_text(
            launch_2_candidate_status,
            default="blocked_insufficient_truth",
        )
        if normalized_launch_2_candidate_status not in {
            "prepared_candidate",
            "blocked_launch_1_not_completed",
            "blocked_missing_inputs",
            "blocked_failure_budget",
            "blocked_loop_or_duplicate_risk",
            "blocked_terminal_stop",
            "blocked_human_review",
            "blocked_insufficient_truth",
            "not_applicable",
        }:
            normalized_launch_2_candidate_status = "blocked_insufficient_truth"
        normalized_launch_2_permission = _normalize_text(
            launch_2_permission,
            default="insufficient_truth",
        )
        if normalized_launch_2_permission not in {
            "allowed_candidate",
            "blocked",
            "not_applicable",
            "insufficient_truth",
        }:
            normalized_launch_2_permission = "insufficient_truth"
        normalized_launch_2_block_reason = _normalize_text(
            launch_2_block_reason,
            default="insufficient_truth",
        )
        normalized_launch_2_required_inputs = _normalize_string_list(
            launch_2_required_inputs
        )
        normalized_launch_2_available_inputs = [
            input_name
            for input_name in _normalize_string_list(launch_2_available_inputs)
            if input_name in set(normalized_launch_2_required_inputs)
        ]
        normalized_launch_2_missing_inputs = [
            input_name
            for input_name in normalized_launch_2_required_inputs
            if input_name not in set(normalized_launch_2_available_inputs)
        ]
        normalized_launch_2_allowed = _as_non_negative_int(
            launch_2_allowed,
            default=0,
        )
        if normalized_launch_2_allowed > 1:
            normalized_launch_2_allowed = 1
        normalized_launch_2_next_action = _normalize_text(
            launch_2_next_action,
            default="do_not_launch",
        )
        if normalized_launch_2_next_action not in {
            "prepare_second_bounded_launch_later",
            "do_not_launch",
            "human_review_required",
            "insufficient_truth",
        }:
            normalized_launch_2_next_action = "do_not_launch"

        if (
            launch_1_completed != 1
            or normalized_launch_2_permission != "allowed_candidate"
            or normalized_launch_2_candidate_status != "prepared_candidate"
            or normalized_launch_2_missing_inputs
        ):
            normalized_launch_2_allowed = 0
        else:
            normalized_launch_2_allowed = 1
        if normalized_launch_2_allowed != 1:
            normalized_launch_2_next_action = "do_not_launch"
        else:
            normalized_launch_2_next_action = "prepare_second_bounded_launch_later"

        return {
            "project_browser_autonomous_two_launch_preparation_status": (
                normalized_preparation_status
            ),
            "project_browser_autonomous_two_launch_preparation_permission": (
                normalized_preparation_permission
            ),
            "project_browser_autonomous_two_launch_preparation_reason": (
                normalized_preparation_reason
            ),
            "project_browser_autonomous_two_launch_preparation_receipt_status": (
                normalized_preparation_receipt_status
            ),
            "project_browser_autonomous_launch_1_status": normalized_launch_1_status,
            "project_browser_autonomous_launch_1_attempted": launch_1_attempted,
            "project_browser_autonomous_launch_1_completed": launch_1_completed,
            "project_browser_autonomous_launch_1_result_status": (
                normalized_launch_1_result_status
            ),
            "project_browser_autonomous_launch_1_stop_reason": launch_1_stop_reason,
            "project_browser_autonomous_launch_1_completion_evidence_status": (
                completion_evidence_status
            ),
            "project_browser_autonomous_launch_1_completion_result_status": (
                completion_result_status
            ),
            "project_browser_autonomous_launch_2_candidate_status": (
                normalized_launch_2_candidate_status
            ),
            "project_browser_autonomous_launch_2_permission": (
                normalized_launch_2_permission
            ),
            "project_browser_autonomous_launch_2_allowed": normalized_launch_2_allowed,
            "project_browser_autonomous_launch_2_block_reason": (
                normalized_launch_2_block_reason
            ),
            "project_browser_autonomous_launch_2_required_inputs": (
                normalized_launch_2_required_inputs
            ),
            "project_browser_autonomous_launch_2_available_inputs": (
                normalized_launch_2_available_inputs
            ),
            "project_browser_autonomous_launch_2_missing_inputs": (
                normalized_launch_2_missing_inputs
            ),
            "project_browser_autonomous_launch_2_next_action": (
                normalized_launch_2_next_action
            ),
        }

    launch_1_terminal_stop = (
        launch_1_stop_reason == "stop_next_action"
        or completion_evidence_status == "terminal_stop"
        or completion_result_status == "terminal_stop"
    )
    launch_1_insufficient_truth = False
    if launch_1_terminal_stop:
        launch_1_status = "terminal_stop"
        launch_1_result_status = "terminal_stop"
    elif launch_1_attempted == 0:
        launch_1_status = "not_attempted"
        launch_1_result_status = "not_attempted"
    elif launch_1_completed == 0:
        launch_1_status = "attempted_not_completed"
        if completion_evidence_status == "insufficient_truth" or completion_result_status == (
            "insufficient_truth"
        ):
            launch_1_result_status = "insufficient_truth"
            launch_1_insufficient_truth = True
        elif completion_result_status == "failed":
            launch_1_result_status = "failed"
        elif completion_result_status in {"not_completed", "not_attempted", "completed"}:
            if completion_result_status == "completed":
                launch_1_result_status = "insufficient_truth"
                launch_1_insufficient_truth = True
            else:
                launch_1_result_status = "not_completed"
        else:
            launch_1_result_status = "not_completed"
    else:
        if (
            completion_evidence_status == "confirmed"
            and completion_result_status == "completed"
        ):
            launch_1_status = "completed"
            launch_1_result_status = "completed"
        else:
            launch_1_status = "insufficient_truth"
            launch_1_result_status = "insufficient_truth"
            launch_1_insufficient_truth = True

    if launch_1_terminal_stop:
        return _base_state(
            preparation_status="terminal_stop",
            preparation_permission="blocked",
            preparation_reason=launch_1_stop_reason or "launch_1_terminal_stop",
            preparation_receipt_status="ready",
            launch_1_status=launch_1_status,
            launch_1_result_status=launch_1_result_status,
            launch_2_candidate_status="blocked_terminal_stop",
            launch_2_permission="blocked",
            launch_2_block_reason=launch_1_stop_reason or "launch_1_terminal_stop",
            launch_2_allowed=0,
            launch_2_next_action="do_not_launch",
        )

    if launch_1_insufficient_truth:
        return _base_state(
            preparation_status="insufficient_truth",
            preparation_permission="insufficient_truth",
            preparation_reason="launch_1_insufficient_truth",
            preparation_receipt_status="insufficient_truth",
            launch_1_status=launch_1_status,
            launch_1_result_status=launch_1_result_status,
            launch_2_candidate_status="blocked_insufficient_truth",
            launch_2_permission="insufficient_truth",
            launch_2_block_reason="launch_1_insufficient_truth",
            launch_2_allowed=0,
            launch_2_next_action="do_not_launch",
        )

    launch_2_missing_inputs = [
        input_name
        for input_name in launch_2_required_inputs
        if input_name not in set(launch_2_available_inputs)
    ]
    if launch_2_missing_inputs:
        return _base_state(
            preparation_status="blocked",
            preparation_permission="blocked",
            preparation_reason="launch_2_required_inputs_missing",
            preparation_receipt_status="blocked",
            launch_1_status=launch_1_status,
            launch_1_result_status=launch_1_result_status,
            launch_2_candidate_status="blocked_missing_inputs",
            launch_2_permission="blocked",
            launch_2_block_reason="launch_2_required_inputs_missing",
            launch_2_allowed=0,
            launch_2_next_action="do_not_launch",
        )

    if launch_1_completed != 1:
        return _base_state(
            preparation_status="blocked",
            preparation_permission="blocked",
            preparation_reason="launch_1_not_completed",
            preparation_receipt_status="blocked",
            launch_1_status=launch_1_status,
            launch_1_result_status=launch_1_result_status,
            launch_2_candidate_status="blocked_launch_1_not_completed",
            launch_2_permission="blocked",
            launch_2_block_reason="launch_1_not_completed",
            launch_2_allowed=0,
            launch_2_next_action="do_not_launch",
        )

    if short_batch_invocation_receipt_status == "human_review_required":
        return _base_state(
            preparation_status="blocked",
            preparation_permission="blocked",
            preparation_reason="short_batch_invocation_human_review_required",
            preparation_receipt_status="blocked",
            launch_1_status=launch_1_status,
            launch_1_result_status=launch_1_result_status,
            launch_2_candidate_status="blocked_human_review",
            launch_2_permission="blocked",
            launch_2_block_reason="short_batch_invocation_human_review_required",
            launch_2_allowed=0,
            launch_2_next_action="do_not_launch",
        )

    if (
        short_batch_invocation_path_status == "insufficient_truth"
        or short_batch_invocation_runtime_capability == "insufficient_truth"
        or short_batch_invocation_receipt_status in {"pause_required", "insufficient_truth"}
        or cooldown_status == "insufficient_truth"
        or loop_risk_status == "insufficient_truth"
        or run_ledger_duplicate_status == "insufficient_truth"
        or watchdog_duplicate_receipt_posture == "insufficient_truth"
    ):
        return _base_state(
            preparation_status="insufficient_truth",
            preparation_permission="insufficient_truth",
            preparation_reason="launch_2_gate_insufficient_truth",
            preparation_receipt_status="insufficient_truth",
            launch_1_status=launch_1_status,
            launch_1_result_status=launch_1_result_status,
            launch_2_candidate_status="blocked_insufficient_truth",
            launch_2_permission="insufficient_truth",
            launch_2_block_reason="launch_2_gate_insufficient_truth",
            launch_2_allowed=0,
            launch_2_next_action="do_not_launch",
        )

    if (
        short_batch_invocation_missing_inputs
        or short_batch_invocation_path_status != "available"
        or short_batch_invocation_runtime_capability != "actual_bounded_invocation"
    ):
        return _base_state(
            preparation_status="blocked",
            preparation_permission="blocked",
            preparation_reason="short_batch_invocation_missing_inputs_present",
            preparation_receipt_status="blocked",
            launch_1_status=launch_1_status,
            launch_1_result_status=launch_1_result_status,
            launch_2_candidate_status="blocked_missing_inputs",
            launch_2_permission="blocked",
            launch_2_block_reason="short_batch_invocation_missing_inputs_present",
            launch_2_allowed=0,
            launch_2_next_action="do_not_launch",
        )

    if short_batch_invocation_receipt_status != "ready":
        return _base_state(
            preparation_status="insufficient_truth",
            preparation_permission="insufficient_truth",
            preparation_reason="short_batch_invocation_receipt_not_ready",
            preparation_receipt_status="insufficient_truth",
            launch_1_status=launch_1_status,
            launch_1_result_status=launch_1_result_status,
            launch_2_candidate_status="blocked_insufficient_truth",
            launch_2_permission="insufficient_truth",
            launch_2_block_reason="short_batch_invocation_receipt_not_ready",
            launch_2_allowed=0,
            launch_2_next_action="do_not_launch",
        )

    if (
        cooldown_status in {"required", "blocked"}
        or rolling_multi_launch_failure_budget <= 0
        or short_batch_failures >= rolling_multi_launch_failure_budget
    ):
        return _base_state(
            preparation_status="blocked",
            preparation_permission="blocked",
            preparation_reason="failure_budget_or_cooldown_blocked",
            preparation_receipt_status="blocked",
            launch_1_status=launch_1_status,
            launch_1_result_status=launch_1_result_status,
            launch_2_candidate_status="blocked_failure_budget",
            launch_2_permission="blocked",
            launch_2_block_reason="failure_budget_or_cooldown_blocked",
            launch_2_allowed=0,
            launch_2_next_action="do_not_launch",
        )

    if (
        loop_risk_status in {"suspected", "blocked"}
        or run_ledger_duplicate_status == "duplicate_detected"
        or watchdog_duplicate_receipt_posture == "duplicate_detected"
    ):
        return _base_state(
            preparation_status="blocked",
            preparation_permission="blocked",
            preparation_reason="loop_or_duplicate_risk_detected",
            preparation_receipt_status="blocked",
            launch_1_status=launch_1_status,
            launch_1_result_status=launch_1_result_status,
            launch_2_candidate_status="blocked_loop_or_duplicate_risk",
            launch_2_permission="blocked",
            launch_2_block_reason="loop_or_duplicate_risk_detected",
            launch_2_allowed=0,
            launch_2_next_action="do_not_launch",
        )

    return _base_state(
        preparation_status="prepared",
        preparation_permission="allowed_candidate",
        preparation_reason="launch_2_candidate_prepared",
        preparation_receipt_status="ready",
        launch_1_status=launch_1_status,
        launch_1_result_status=launch_1_result_status,
        launch_2_candidate_status="prepared_candidate",
        launch_2_permission="allowed_candidate",
        launch_2_block_reason="none",
        launch_2_allowed=1,
        launch_2_next_action="prepare_second_bounded_launch_later",
    )

def _build_project_browser_autonomous_max_two_launch_execution_state(
    *,
    autonomous_two_launch_preparation_status: str,
    autonomous_two_launch_preparation_permission: str,
    autonomous_two_launch_preparation_reason: str,
    autonomous_two_launch_preparation_receipt_status: str,
    autonomous_launch_1_status: str,
    autonomous_launch_1_attempted: int,
    autonomous_launch_1_completed: int,
    autonomous_launch_1_result_status: str,
    autonomous_launch_2_candidate_status: str,
    autonomous_launch_2_permission: str,
    autonomous_launch_2_allowed: int,
    autonomous_launch_2_block_reason: str,
    autonomous_launch_2_missing_inputs: list[str] | None,
    autonomous_launch_2_next_action: str,
    autonomous_short_batch_invocation_path_status: str,
    autonomous_short_batch_invocation_runtime_capability: str,
    autonomous_short_batch_invocation_receipt_status: str,
    autonomous_short_batch_invocation_delegation_mode: str,
    autonomous_short_batch_invocation_call_path_ref: str,
    autonomous_short_batch_invocation_missing_inputs: list[str] | None,
    autonomous_short_batch_invocation_next_action: str,
    autonomous_cooldown_status: str,
    autonomous_loop_risk_status: str,
    autonomous_run_ledger_duplicate_status: str,
    autonomous_watchdog_duplicate_receipt_posture: str,
    autonomous_short_batch_failures: int,
    autonomous_rolling_multi_launch_failure_budget: int,
    autonomous_rolling_execution_launch_helper_status: str,
    autonomous_rolling_execution_launch_helper_ref: str,
    autonomous_rolling_execution_launch_helper_missing_inputs: list[str] | None,
    autonomous_rolling_execution_launch_execution_mode: str,
    autonomous_rolling_execution_launch_receipt_status: str,
    autonomous_rolling_execution_status: str,
    autonomous_rolling_execution_permission: str,
    autonomous_rolling_execution_source_status: str,
    autonomous_rolling_execution_receipt_status: str,
    autonomous_rolling_execution_runtime_capability: str,
    autonomous_rolling_execution_launches_allowed: int,
    autonomous_rolling_execution_launches_attempted: int,
    autonomous_rolling_execution_launches_completed: int,
    autonomous_rolling_multi_launch_status: str,
    autonomous_rolling_multi_launch_permission: str,
    autonomous_rolling_multi_launch_source_status: str,
    autonomous_rolling_multi_launch_receipt_status: str,
    autonomous_rolling_multi_launch_next_action: str,
    autonomous_one_bounded_launch_callsite_available_vars: list[str] | None,
    autonomous_one_bounded_launch_callsite_values: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    two_launch_preparation_status = _normalize_text(
        autonomous_two_launch_preparation_status,
        default="insufficient_truth",
    )
    if two_launch_preparation_status not in {
        "prepared",
        "blocked",
        "terminal_stop",
        "insufficient_truth",
    }:
        two_launch_preparation_status = "insufficient_truth"
    two_launch_preparation_permission = _normalize_text(
        autonomous_two_launch_preparation_permission,
        default="insufficient_truth",
    )
    if two_launch_preparation_permission not in {
        "allowed_candidate",
        "blocked",
        "not_applicable",
        "insufficient_truth",
    }:
        two_launch_preparation_permission = "insufficient_truth"
    two_launch_preparation_reason = _normalize_text(
        autonomous_two_launch_preparation_reason,
        default="insufficient_truth",
    )
    two_launch_preparation_receipt_status = _normalize_text(
        autonomous_two_launch_preparation_receipt_status,
        default="insufficient_truth",
    )
    if two_launch_preparation_receipt_status not in {
        "ready",
        "blocked",
        "insufficient_truth",
    }:
        two_launch_preparation_receipt_status = "insufficient_truth"
    launch_1_status = _normalize_text(
        autonomous_launch_1_status,
        default="insufficient_truth",
    )
    if launch_1_status not in {
        "completed",
        "attempted_not_completed",
        "not_attempted",
        "blocked",
        "terminal_stop",
        "insufficient_truth",
    }:
        launch_1_status = "insufficient_truth"
    launch_1_attempted = _as_non_negative_int(
        autonomous_launch_1_attempted,
        default=0,
    )
    if launch_1_attempted > 1:
        launch_1_attempted = 1
    launch_1_completed = _as_non_negative_int(
        autonomous_launch_1_completed,
        default=0,
    )
    if launch_1_completed > 1:
        launch_1_completed = 1
    if launch_1_completed > launch_1_attempted:
        launch_1_completed = launch_1_attempted
    launch_1_result_status = _normalize_text(
        autonomous_launch_1_result_status,
        default="insufficient_truth",
    )
    if launch_1_result_status not in {
        "completed",
        "not_completed",
        "failed",
        "blocked",
        "not_attempted",
        "terminal_stop",
        "insufficient_truth",
    }:
        launch_1_result_status = "insufficient_truth"
    launch_2_candidate_status = _normalize_text(
        autonomous_launch_2_candidate_status,
        default="blocked_insufficient_truth",
    )
    if launch_2_candidate_status not in {
        "prepared_candidate",
        "blocked_launch_1_not_completed",
        "blocked_missing_inputs",
        "blocked_failure_budget",
        "blocked_loop_or_duplicate_risk",
        "blocked_terminal_stop",
        "blocked_human_review",
        "blocked_insufficient_truth",
        "not_applicable",
    }:
        launch_2_candidate_status = "blocked_insufficient_truth"
    launch_2_permission = _normalize_text(
        autonomous_launch_2_permission,
        default="insufficient_truth",
    )
    if launch_2_permission not in {
        "allowed_candidate",
        "blocked",
        "not_applicable",
        "insufficient_truth",
    }:
        launch_2_permission = "insufficient_truth"
    launch_2_allowed = _as_non_negative_int(
        autonomous_launch_2_allowed,
        default=0,
    )
    if launch_2_allowed > 1:
        launch_2_allowed = 1
    launch_2_block_reason = _normalize_text(
        autonomous_launch_2_block_reason,
        default="insufficient_truth",
    )
    launch_2_missing_inputs = _normalize_string_list(
        autonomous_launch_2_missing_inputs or []
    )
    launch_2_next_action = _normalize_text(
        autonomous_launch_2_next_action,
        default="do_not_launch",
    )
    if launch_2_next_action not in {
        "prepare_second_bounded_launch_later",
        "do_not_launch",
        "human_review_required",
        "insufficient_truth",
    }:
        launch_2_next_action = "do_not_launch"
    short_batch_invocation_path_status = _normalize_text(
        autonomous_short_batch_invocation_path_status,
        default="insufficient_truth",
    )
    if short_batch_invocation_path_status not in {
        "available",
        "unavailable",
        "insufficient_truth",
    }:
        short_batch_invocation_path_status = "insufficient_truth"
    short_batch_invocation_runtime_capability = _normalize_text(
        autonomous_short_batch_invocation_runtime_capability,
        default="insufficient_truth",
    )
    if short_batch_invocation_runtime_capability not in {
        "actual_bounded_invocation",
        "partial_runtime_parts_available",
        "metadata_only",
        "unavailable",
        "insufficient_truth",
    }:
        short_batch_invocation_runtime_capability = "insufficient_truth"
    short_batch_invocation_receipt_status = _normalize_text(
        autonomous_short_batch_invocation_receipt_status,
        default="insufficient_truth",
    )
    if short_batch_invocation_receipt_status not in {
        "ready",
        "blocked",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        short_batch_invocation_receipt_status = "insufficient_truth"
    short_batch_invocation_delegation_mode = _normalize_text(
        autonomous_short_batch_invocation_delegation_mode,
        default="insufficient_truth",
    )
    if short_batch_invocation_delegation_mode not in {
        "invoked_existing_builder",
        "reused_existing_state_call_path",
        "not_callable_missing_inputs",
        "no_runtime_invocation_stop",
        "insufficient_truth",
    }:
        short_batch_invocation_delegation_mode = "insufficient_truth"
    short_batch_invocation_call_path_ref = _normalize_text(
        autonomous_short_batch_invocation_call_path_ref,
        default="none",
    )
    short_batch_invocation_missing_inputs = _normalize_string_list(
        autonomous_short_batch_invocation_missing_inputs or []
    )
    short_batch_invocation_next_action = _normalize_text(
        autonomous_short_batch_invocation_next_action,
        default="none",
    )
    cooldown_status = _normalize_text(
        autonomous_cooldown_status,
        default="insufficient_truth",
    )
    if cooldown_status not in {
        "not_required",
        "required",
        "blocked",
        "insufficient_truth",
    }:
        cooldown_status = "insufficient_truth"
    loop_risk_status = _normalize_text(
        autonomous_loop_risk_status,
        default="insufficient_truth",
    )
    if loop_risk_status not in {"clear", "suspected", "blocked", "insufficient_truth"}:
        loop_risk_status = "insufficient_truth"
    run_ledger_duplicate_status = _normalize_text(
        autonomous_run_ledger_duplicate_status,
        default="insufficient_truth",
    )
    if run_ledger_duplicate_status not in {
        "clear",
        "duplicate_detected",
        "blocked",
        "insufficient_truth",
    }:
        run_ledger_duplicate_status = "insufficient_truth"
    watchdog_duplicate_receipt_posture = _normalize_text(
        autonomous_watchdog_duplicate_receipt_posture,
        default="insufficient_truth",
    )
    if watchdog_duplicate_receipt_posture not in {
        "clear",
        "duplicate_detected",
        "insufficient_truth",
    }:
        watchdog_duplicate_receipt_posture = "insufficient_truth"
    short_batch_failures = _as_non_negative_int(
        autonomous_short_batch_failures,
        default=0,
    )
    rolling_multi_launch_failure_budget = _as_non_negative_int(
        autonomous_rolling_multi_launch_failure_budget,
        default=0,
    )
    rolling_execution_launch_helper_status = _normalize_text(
        autonomous_rolling_execution_launch_helper_status,
        default="unavailable",
    )
    if rolling_execution_launch_helper_status not in {
        "available",
        "unavailable",
        "insufficient_truth",
    }:
        rolling_execution_launch_helper_status = "insufficient_truth"
    rolling_execution_launch_helper_ref = _normalize_text(
        autonomous_rolling_execution_launch_helper_ref,
        default="none",
    )
    rolling_execution_launch_helper_missing_inputs = _normalize_string_list(
        autonomous_rolling_execution_launch_helper_missing_inputs or []
    )
    rolling_execution_launch_execution_mode = _normalize_text(
        autonomous_rolling_execution_launch_execution_mode,
        default="prepared_only_helper_missing",
    )
    if rolling_execution_launch_execution_mode not in {
        "existing_call_path_reused",
        "prepared_only_helper_missing",
        "insufficient_truth",
    }:
        rolling_execution_launch_execution_mode = "insufficient_truth"
    rolling_execution_launch_receipt_status = _normalize_text(
        autonomous_rolling_execution_launch_receipt_status,
        default="insufficient_truth",
    )
    if rolling_execution_launch_receipt_status not in {
        "ready",
        "unavailable",
        "insufficient_truth",
    }:
        rolling_execution_launch_receipt_status = "insufficient_truth"
    one_bounded_launch_callsite_values = (
        dict(autonomous_one_bounded_launch_callsite_values)
        if isinstance(autonomous_one_bounded_launch_callsite_values, Mapping)
        else {}
    )
    one_bounded_launch_callsite_available_vars = set(
        _normalize_string_list(autonomous_one_bounded_launch_callsite_available_vars or [])
    )
    for candidate_name in one_bounded_launch_callsite_values:
        normalized_candidate_name = _normalize_text(candidate_name, default="")
        if normalized_candidate_name:
            one_bounded_launch_callsite_available_vars.add(normalized_candidate_name)

    max_launches_allowed = 2
    total_step_budget = 6
    failure_budget = 1
    reusable_surface_name = "existing_one_bounded_launch_invocation_helper"

    def _finalize_counts(
        *,
        launch_2_attempt_status: str,
        launch_2_execution_mode: str,
        launch_2_execution_ref: str,
        launch_2_execution_receipt_status: str,
        launch_2_attempted: int,
        launch_2_completed: int,
        next_action: str,
    ) -> tuple[int, int, int, str]:
        normalized_launch_2_attempted = _as_non_negative_int(
            launch_2_attempted,
            default=0,
        )
        if normalized_launch_2_attempted > 1:
            normalized_launch_2_attempted = 1
        normalized_launch_2_completed = _as_non_negative_int(
            launch_2_completed,
            default=0,
        )
        if normalized_launch_2_completed > 1:
            normalized_launch_2_completed = 1
        if (
            launch_2_attempt_status != "invoked_once"
            or launch_2_execution_mode != "second_existing_invocation_call_path_invoked"
            or _normalize_text(launch_2_execution_ref, default="none") in {"", "none"}
            or launch_2_execution_receipt_status != "ready"
        ):
            normalized_launch_2_attempted = 0
        if normalized_launch_2_completed > normalized_launch_2_attempted:
            normalized_launch_2_completed = normalized_launch_2_attempted
        max_two_launches_attempted = launch_1_attempted + normalized_launch_2_attempted
        max_two_launches_completed = launch_1_completed + normalized_launch_2_completed
        if max_two_launches_attempted > max_launches_allowed:
            max_two_launches_attempted = max_launches_allowed
        if max_two_launches_completed > max_launches_allowed:
            max_two_launches_completed = max_launches_allowed
        if max_two_launches_completed > max_two_launches_attempted:
            max_two_launches_completed = max_two_launches_attempted
        max_two_launches_remaining = max_launches_allowed - max_two_launches_attempted
        if max_two_launches_remaining < 0:
            max_two_launches_remaining = 0
        normalized_next_action = next_action
        if max_two_launches_attempted >= max_launches_allowed:
            max_two_launches_remaining = 0
            if normalized_next_action not in {
                "stop_after_second_launch_attempt",
                "stop_max_two_launch_complete",
            }:
                normalized_next_action = "stop_max_two_launch_complete"
        return (
            normalized_launch_2_attempted,
            normalized_launch_2_completed,
            max_two_launches_attempted,
            max_two_launches_completed,
            max_two_launches_remaining,
            normalized_next_action,
        )

    def _state(
        *,
        max_two_status: str,
        max_two_permission: str,
        max_two_reason: str,
        max_two_receipt_status: str,
        max_two_mode: str,
        max_two_block_reason: str,
        launch_2_attempt_status: str,
        launch_2_attempt_reason: str,
        launch_2_execution_mode: str,
        launch_2_execution_ref: str,
        launch_2_execution_receipt_status: str,
        launch_2_execution_receipt_kind: str,
        launch_2_result_status: str,
        launch_2_result_reason: str,
        launch_2_attempted: int,
        launch_2_completed: int,
        max_two_next_action: str,
        launch_2_pause_status: str,
        launch_2_pause_reason: str,
        launch_2_missing_reusable_invocation_surface: list[str] | None = None,
    ) -> dict[str, Any]:
        (
            normalized_launch_2_attempted,
            normalized_launch_2_completed,
            max_two_launches_attempted,
            max_two_launches_completed,
            max_two_launches_remaining,
            normalized_next_action,
        ) = _finalize_counts(
            launch_2_attempt_status=launch_2_attempt_status,
            launch_2_execution_mode=launch_2_execution_mode,
            launch_2_execution_ref=launch_2_execution_ref,
            launch_2_execution_receipt_status=launch_2_execution_receipt_status,
            launch_2_attempted=launch_2_attempted,
            launch_2_completed=launch_2_completed,
            next_action=max_two_next_action,
        )
        return {
            "project_browser_autonomous_max_two_launch_execution_status": (
                max_two_status
            ),
            "project_browser_autonomous_max_two_launch_execution_permission": (
                max_two_permission
            ),
            "project_browser_autonomous_max_two_launch_execution_reason": (
                max_two_reason
            ),
            "project_browser_autonomous_max_two_launch_execution_receipt_status": (
                max_two_receipt_status
            ),
            "project_browser_autonomous_max_two_launch_execution_mode": (
                max_two_mode
            ),
            "project_browser_autonomous_max_two_launch_execution_block_reason": (
                max_two_block_reason
            ),
            "project_browser_autonomous_launch_2_attempt_status": (
                launch_2_attempt_status
            ),
            "project_browser_autonomous_launch_2_attempt_reason": (
                launch_2_attempt_reason
            ),
            "project_browser_autonomous_launch_2_execution_mode": (
                launch_2_execution_mode
            ),
            "project_browser_autonomous_launch_2_execution_ref": (
                _normalize_text(launch_2_execution_ref, default="none")
            ),
            "project_browser_autonomous_launch_2_execution_receipt_status": (
                launch_2_execution_receipt_status
            ),
            "project_browser_autonomous_launch_2_execution_receipt_kind": (
                _normalize_text(launch_2_execution_receipt_kind, default="none")
            ),
            "project_browser_autonomous_launch_2_result_status": (
                launch_2_result_status
            ),
            "project_browser_autonomous_launch_2_result_reason": (
                launch_2_result_reason
            ),
            "project_browser_autonomous_launch_2_attempted": (
                normalized_launch_2_attempted
            ),
            "project_browser_autonomous_launch_2_completed": (
                normalized_launch_2_completed
            ),
            "project_browser_autonomous_max_two_launches_allowed": (
                max_launches_allowed
            ),
            "project_browser_autonomous_max_two_launches_attempted": (
                max_two_launches_attempted
            ),
            "project_browser_autonomous_max_two_launches_completed": (
                max_two_launches_completed
            ),
            "project_browser_autonomous_max_two_launches_remaining": (
                max_two_launches_remaining
            ),
            "project_browser_autonomous_max_two_launch_total_step_budget": (
                total_step_budget
            ),
            "project_browser_autonomous_max_two_launch_failure_budget": (
                failure_budget
            ),
            "project_browser_autonomous_max_two_launch_next_action": (
                normalized_next_action
            ),
            "project_browser_autonomous_launch_2_pause_status": (
                launch_2_pause_status
            ),
            "project_browser_autonomous_launch_2_pause_reason": (
                launch_2_pause_reason
            ),
            "project_browser_autonomous_launch_2_missing_reusable_invocation_surface": (
                _normalize_string_list(
                    launch_2_missing_reusable_invocation_surface or []
                )
            ),
        }

    helper_surface_available = bool(
        rolling_execution_launch_helper_status == "available"
        and rolling_execution_launch_helper_ref
        == "project_browser_autonomous_one_bounded_launch_state"
        and not rolling_execution_launch_helper_missing_inputs
        and rolling_execution_launch_execution_mode == "existing_call_path_reused"
        and rolling_execution_launch_receipt_status == "ready"
    )
    if not helper_surface_available:
        return _state(
            max_two_status="blocked",
            max_two_permission="blocked",
            max_two_reason="reusable_second_launch_invocation_surface_missing",
            max_two_receipt_status="blocked",
            max_two_mode="insufficient_truth",
            max_two_block_reason="reusable_second_launch_invocation_surface_missing",
            launch_2_attempt_status="insufficient_truth",
            launch_2_attempt_reason="reusable_second_launch_invocation_surface_missing",
            launch_2_execution_mode="insufficient_truth",
            launch_2_execution_ref="none",
            launch_2_execution_receipt_status="insufficient_truth",
            launch_2_execution_receipt_kind="insufficient_truth_second_launch_receipt",
            launch_2_result_status="insufficient_truth",
            launch_2_result_reason="reusable_second_launch_invocation_surface_missing",
            launch_2_attempted=0,
            launch_2_completed=0,
            max_two_next_action="insufficient_truth",
            launch_2_pause_status="not_applicable",
            launch_2_pause_reason="not_applicable",
            launch_2_missing_reusable_invocation_surface=[reusable_surface_name],
        )
    if not callable(_build_project_browser_autonomous_one_bounded_launch_state):
        return _state(
            max_two_status="blocked",
            max_two_permission="blocked",
            max_two_reason="reusable_second_launch_invocation_surface_missing",
            max_two_receipt_status="blocked",
            max_two_mode="insufficient_truth",
            max_two_block_reason="reusable_second_launch_invocation_surface_missing",
            launch_2_attempt_status="insufficient_truth",
            launch_2_attempt_reason="reusable_second_launch_invocation_surface_missing",
            launch_2_execution_mode="insufficient_truth",
            launch_2_execution_ref="none",
            launch_2_execution_receipt_status="insufficient_truth",
            launch_2_execution_receipt_kind="insufficient_truth_second_launch_receipt",
            launch_2_result_status="insufficient_truth",
            launch_2_result_reason="reusable_second_launch_invocation_surface_missing",
            launch_2_attempted=0,
            launch_2_completed=0,
            max_two_next_action="insufficient_truth",
            launch_2_pause_status="not_applicable",
            launch_2_pause_reason="not_applicable",
            launch_2_missing_reusable_invocation_surface=[reusable_surface_name],
        )

    if (
        two_launch_preparation_status == "terminal_stop"
        or launch_1_status == "terminal_stop"
        or launch_1_result_status == "terminal_stop"
        or launch_2_candidate_status == "blocked_terminal_stop"
    ):
        return _state(
            max_two_status="terminal_stop",
            max_two_permission="not_applicable",
            max_two_reason=launch_2_block_reason or two_launch_preparation_reason or "terminal_stop",
            max_two_receipt_status="ready",
            max_two_mode="blocked_terminal_stop",
            max_two_block_reason=launch_2_block_reason or "terminal_stop",
            launch_2_attempt_status="terminal_stop",
            launch_2_attempt_reason=launch_2_block_reason or "terminal_stop",
            launch_2_execution_mode="blocked_terminal_stop",
            launch_2_execution_ref="none",
            launch_2_execution_receipt_status="not_applicable",
            launch_2_execution_receipt_kind="none",
            launch_2_result_status="terminal_stop",
            launch_2_result_reason=launch_2_block_reason or "terminal_stop",
            launch_2_attempted=0,
            launch_2_completed=0,
            max_two_next_action="stop_max_two_launch_complete",
            launch_2_pause_status="not_applicable",
            launch_2_pause_reason="not_applicable",
        )

    if (
        two_launch_preparation_status == "insufficient_truth"
        or two_launch_preparation_permission == "insufficient_truth"
        or two_launch_preparation_receipt_status == "insufficient_truth"
        or launch_1_status == "insufficient_truth"
        or launch_1_result_status == "insufficient_truth"
        or launch_2_candidate_status == "blocked_insufficient_truth"
        or launch_2_permission == "insufficient_truth"
        or launch_2_next_action == "insufficient_truth"
        or short_batch_invocation_path_status == "insufficient_truth"
        or short_batch_invocation_runtime_capability == "insufficient_truth"
        or short_batch_invocation_receipt_status == "insufficient_truth"
        or short_batch_invocation_delegation_mode == "insufficient_truth"
        or cooldown_status == "insufficient_truth"
        or loop_risk_status == "insufficient_truth"
        or run_ledger_duplicate_status == "insufficient_truth"
        or watchdog_duplicate_receipt_posture == "insufficient_truth"
        or rolling_execution_launch_helper_status == "insufficient_truth"
        or rolling_execution_launch_execution_mode == "insufficient_truth"
        or rolling_execution_launch_receipt_status == "insufficient_truth"
    ):
        return _state(
            max_two_status="insufficient_truth",
            max_two_permission="insufficient_truth",
            max_two_reason=two_launch_preparation_reason or "insufficient_truth",
            max_two_receipt_status="insufficient_truth",
            max_two_mode="insufficient_truth",
            max_two_block_reason=launch_2_block_reason or "insufficient_truth",
            launch_2_attempt_status="insufficient_truth",
            launch_2_attempt_reason=launch_2_block_reason or "insufficient_truth",
            launch_2_execution_mode="insufficient_truth",
            launch_2_execution_ref="none",
            launch_2_execution_receipt_status="insufficient_truth",
            launch_2_execution_receipt_kind="insufficient_truth_second_launch_receipt",
            launch_2_result_status="insufficient_truth",
            launch_2_result_reason=launch_2_block_reason or "insufficient_truth",
            launch_2_attempted=0,
            launch_2_completed=0,
            max_two_next_action="insufficient_truth",
            launch_2_pause_status="not_applicable",
            launch_2_pause_reason="not_applicable",
        )

    if short_batch_invocation_receipt_status == "pause_required":
        return _state(
            max_two_status="paused",
            max_two_permission="paused",
            max_two_reason="pause_required",
            max_two_receipt_status="pause_required",
            max_two_mode="blocked_pause_required",
            max_two_block_reason="pause_required",
            launch_2_attempt_status="not_invoked_pause_required",
            launch_2_attempt_reason="pause_required",
            launch_2_execution_mode="blocked_pause_required",
            launch_2_execution_ref="none",
            launch_2_execution_receipt_status="pause_required",
            launch_2_execution_receipt_kind="pause_required_second_launch_receipt",
            launch_2_result_status="paused",
            launch_2_result_reason="pause_required",
            launch_2_attempted=0,
            launch_2_completed=0,
            max_two_next_action="pause_required",
            launch_2_pause_status="pause_required",
            launch_2_pause_reason="short_batch_invocation_pause_required",
        )

    if (
        short_batch_invocation_receipt_status == "human_review_required"
        or launch_2_candidate_status == "blocked_human_review"
        or launch_2_next_action == "human_review_required"
    ):
        return _state(
            max_two_status="blocked",
            max_two_permission="blocked",
            max_two_reason="human_review_required",
            max_two_receipt_status="blocked",
            max_two_mode="blocked_human_review",
            max_two_block_reason="human_review_required",
            launch_2_attempt_status="not_invoked_hard_risk",
            launch_2_attempt_reason="human_review_required",
            launch_2_execution_mode="blocked_human_review",
            launch_2_execution_ref="none",
            launch_2_execution_receipt_status="blocked",
            launch_2_execution_receipt_kind="blocked_second_launch_receipt",
            launch_2_result_status="blocked",
            launch_2_result_reason="human_review_required",
            launch_2_attempted=0,
            launch_2_completed=0,
            max_two_next_action="human_review_required",
            launch_2_pause_status="not_applicable",
            launch_2_pause_reason="not_applicable",
        )

    if (
        launch_2_allowed != 1
        or launch_2_permission != "allowed_candidate"
        or launch_2_candidate_status != "prepared_candidate"
        or launch_2_next_action != "prepare_second_bounded_launch_later"
        or two_launch_preparation_status != "prepared"
        or two_launch_preparation_permission != "allowed_candidate"
        or two_launch_preparation_receipt_status != "ready"
        or launch_1_attempted != 1
        or launch_1_completed != 1
        or launch_1_result_status != "completed"
    ):
        return _state(
            max_two_status="blocked",
            max_two_permission="blocked",
            max_two_reason="launch_2_candidate_not_allowed",
            max_two_receipt_status="blocked",
            max_two_mode="blocked_candidate_not_allowed",
            max_two_block_reason=launch_2_block_reason or "launch_2_candidate_not_allowed",
            launch_2_attempt_status="not_invoked_candidate_not_allowed",
            launch_2_attempt_reason=launch_2_block_reason or "launch_2_candidate_not_allowed",
            launch_2_execution_mode="blocked_candidate_not_allowed",
            launch_2_execution_ref="none",
            launch_2_execution_receipt_status="not_applicable",
            launch_2_execution_receipt_kind="none",
            launch_2_result_status="blocked",
            launch_2_result_reason=launch_2_block_reason or "launch_2_candidate_not_allowed",
            launch_2_attempted=0,
            launch_2_completed=0,
            max_two_next_action="stop_second_launch_not_allowed",
            launch_2_pause_status="not_applicable",
            launch_2_pause_reason="not_applicable",
        )

    if (
        launch_2_missing_inputs
        or short_batch_invocation_missing_inputs
        or short_batch_invocation_path_status != "available"
        or short_batch_invocation_runtime_capability != "actual_bounded_invocation"
        or short_batch_invocation_receipt_status != "ready"
        or short_batch_invocation_call_path_ref in {"", "none"}
    ):
        return _state(
            max_two_status="blocked",
            max_two_permission="blocked",
            max_two_reason="launch_2_missing_inputs",
            max_two_receipt_status="blocked",
            max_two_mode="blocked_missing_inputs",
            max_two_block_reason=(
                launch_2_block_reason
                or (
                    "short_batch_invocation_call_path_missing"
                    if short_batch_invocation_call_path_ref in {"", "none"}
                    else "launch_2_missing_inputs"
                )
            ),
            launch_2_attempt_status="not_invoked_missing_inputs",
            launch_2_attempt_reason=(
                launch_2_block_reason
                or (
                    "short_batch_invocation_call_path_missing"
                    if short_batch_invocation_call_path_ref in {"", "none"}
                    else "launch_2_missing_inputs"
                )
            ),
            launch_2_execution_mode="blocked_missing_inputs",
            launch_2_execution_ref="none",
            launch_2_execution_receipt_status="blocked",
            launch_2_execution_receipt_kind="blocked_second_launch_receipt",
            launch_2_result_status="blocked",
            launch_2_result_reason=(
                launch_2_block_reason
                or (
                    "short_batch_invocation_call_path_missing"
                    if short_batch_invocation_call_path_ref in {"", "none"}
                    else "launch_2_missing_inputs"
                )
            ),
            launch_2_attempted=0,
            launch_2_completed=0,
            max_two_next_action="stop_second_launch_not_allowed",
            launch_2_pause_status="none",
            launch_2_pause_reason="none",
        )

    if (
        cooldown_status in {"required", "blocked"}
        or rolling_multi_launch_failure_budget <= 0
        or short_batch_failures >= failure_budget
    ):
        return _state(
            max_two_status="blocked",
            max_two_permission="blocked",
            max_two_reason="failure_budget_exhausted",
            max_two_receipt_status="blocked",
            max_two_mode="blocked_failure_budget",
            max_two_block_reason="failure_budget_exhausted",
            launch_2_attempt_status="not_invoked_failure_budget",
            launch_2_attempt_reason="failure_budget_exhausted",
            launch_2_execution_mode="blocked_failure_budget",
            launch_2_execution_ref="none",
            launch_2_execution_receipt_status="blocked",
            launch_2_execution_receipt_kind="blocked_second_launch_receipt",
            launch_2_result_status="blocked",
            launch_2_result_reason="failure_budget_exhausted",
            launch_2_attempted=0,
            launch_2_completed=0,
            max_two_next_action="stop_second_launch_not_allowed",
            launch_2_pause_status="none",
            launch_2_pause_reason="none",
        )

    if (
        loop_risk_status in {"suspected", "blocked"}
        or run_ledger_duplicate_status in {"duplicate_detected", "blocked"}
        or watchdog_duplicate_receipt_posture == "duplicate_detected"
    ):
        return _state(
            max_two_status="blocked",
            max_two_permission="blocked",
            max_two_reason="loop_or_duplicate_risk_detected",
            max_two_receipt_status="blocked",
            max_two_mode="blocked_loop_or_duplicate_risk",
            max_two_block_reason="loop_or_duplicate_risk_detected",
            launch_2_attempt_status="not_invoked_loop_or_duplicate_risk",
            launch_2_attempt_reason="loop_or_duplicate_risk_detected",
            launch_2_execution_mode="blocked_loop_or_duplicate_risk",
            launch_2_execution_ref="none",
            launch_2_execution_receipt_status="blocked",
            launch_2_execution_receipt_kind="blocked_second_launch_receipt",
            launch_2_result_status="blocked",
            launch_2_result_reason="loop_or_duplicate_risk_detected",
            launch_2_attempted=0,
            launch_2_completed=0,
            max_two_next_action="stop_second_launch_not_allowed",
            launch_2_pause_status="none",
            launch_2_pause_reason="none",
        )

    second_launch_state = _build_project_browser_autonomous_one_bounded_launch_state(
        autonomous_rolling_execution_status=autonomous_rolling_execution_status,
        autonomous_rolling_execution_permission=autonomous_rolling_execution_permission,
        autonomous_rolling_execution_source_status=autonomous_rolling_execution_source_status,
        autonomous_rolling_execution_receipt_status=autonomous_rolling_execution_receipt_status,
        autonomous_rolling_execution_runtime_capability=(
            autonomous_rolling_execution_runtime_capability
        ),
        autonomous_rolling_execution_launches_allowed=(
            autonomous_rolling_execution_launches_allowed
        ),
        autonomous_rolling_execution_launches_attempted=(
            autonomous_rolling_execution_launches_attempted
        ),
        autonomous_rolling_execution_launches_completed=(
            autonomous_rolling_execution_launches_completed
        ),
        autonomous_rolling_multi_launch_status=autonomous_rolling_multi_launch_status,
        autonomous_rolling_multi_launch_permission=(
            autonomous_rolling_multi_launch_permission
        ),
        autonomous_rolling_multi_launch_source_status=(
            autonomous_rolling_multi_launch_source_status
        ),
        autonomous_rolling_multi_launch_receipt_status=(
            autonomous_rolling_multi_launch_receipt_status
        ),
        autonomous_rolling_multi_launch_next_action=(
            autonomous_rolling_multi_launch_next_action
        ),
        autonomous_short_batch_invocation_path_status=(
            autonomous_short_batch_invocation_path_status
        ),
        autonomous_short_batch_invocation_runtime_capability=(
            autonomous_short_batch_invocation_runtime_capability
        ),
        autonomous_short_batch_invocation_receipt_status=(
            autonomous_short_batch_invocation_receipt_status
        ),
        autonomous_short_batch_invocation_delegation_mode=(
            autonomous_short_batch_invocation_delegation_mode
        ),
        autonomous_short_batch_invocation_call_path_ref=(
            autonomous_short_batch_invocation_call_path_ref
        ),
        autonomous_short_batch_invocation_missing_inputs=(
            autonomous_short_batch_invocation_missing_inputs
        ),
        autonomous_short_batch_invocation_next_action=(
            autonomous_short_batch_invocation_next_action
        ),
        autonomous_one_bounded_launch_callsite_available_vars=(
            list(one_bounded_launch_callsite_available_vars)
        ),
        autonomous_one_bounded_launch_callsite_values=one_bounded_launch_callsite_values,
    )
    second_launch_attempted = _as_non_negative_int(
        second_launch_state.get("project_browser_autonomous_one_bounded_launch_attempted"),
        default=0,
    )
    second_launch_completed = _as_non_negative_int(
        second_launch_state.get("project_browser_autonomous_one_bounded_launch_completed"),
        default=0,
    )
    second_launch_execution_ref = _normalize_text(
        second_launch_state.get("project_browser_autonomous_one_bounded_launch_execution_ref"),
        default="none",
    )
    second_launch_execution_receipt_status = _normalize_text(
        second_launch_state.get(
            "project_browser_autonomous_one_bounded_launch_execution_receipt_status"
        ),
        default="insufficient_truth",
    )
    second_launch_execution_receipt_kind = _normalize_text(
        second_launch_state.get(
            "project_browser_autonomous_one_bounded_launch_execution_receipt_kind"
        ),
        default="insufficient_truth_second_launch_receipt",
    )
    second_launch_invocation_attempt_status = _normalize_text(
        second_launch_state.get(
            "project_browser_autonomous_one_bounded_launch_invocation_attempt_status"
        ),
        default="insufficient_truth",
    )
    second_launch_completion_result_status = _normalize_text(
        second_launch_state.get(
            "project_browser_autonomous_one_bounded_launch_completion_result_status"
        ),
        default="insufficient_truth",
    )
    second_launch_completion_result_reason = _normalize_text(
        second_launch_state.get(
            "project_browser_autonomous_one_bounded_launch_completion_result_reason"
        ),
        default="insufficient_truth_for_completion_evidence",
    )
    second_launch_completion_evidence_status = _normalize_text(
        second_launch_state.get(
            "project_browser_autonomous_one_bounded_launch_completion_evidence_status"
        ),
        default="insufficient_truth",
    )
    second_launch_attempt_confirmed = bool(
        second_launch_attempted == 1
        and second_launch_invocation_attempt_status == "invoked_once"
        and second_launch_execution_ref not in {"", "none"}
        and second_launch_execution_receipt_status == "ready"
    )
    if not second_launch_attempt_confirmed:
        return _state(
            max_two_status="insufficient_truth",
            max_two_permission="insufficient_truth",
            max_two_reason="second_launch_invocation_not_confirmed",
            max_two_receipt_status="insufficient_truth",
            max_two_mode="insufficient_truth",
            max_two_block_reason="second_launch_invocation_not_confirmed",
            launch_2_attempt_status="insufficient_truth",
            launch_2_attempt_reason="second_launch_invocation_not_confirmed",
            launch_2_execution_mode="insufficient_truth",
            launch_2_execution_ref="none",
            launch_2_execution_receipt_status="insufficient_truth",
            launch_2_execution_receipt_kind=second_launch_execution_receipt_kind,
            launch_2_result_status="insufficient_truth",
            launch_2_result_reason="second_launch_invocation_not_confirmed",
            launch_2_attempted=0,
            launch_2_completed=0,
            max_two_next_action="insufficient_truth",
            launch_2_pause_status="not_applicable",
            launch_2_pause_reason="not_applicable",
        )

    second_launch_result_status = "attempted_not_completed"
    if second_launch_completed == 1 and second_launch_completion_result_status == "completed":
        second_launch_result_status = "completed"
    elif second_launch_completion_result_status == "failed":
        second_launch_result_status = "failed"
    elif second_launch_completion_result_status == "insufficient_truth":
        second_launch_result_status = "insufficient_truth"

    return _state(
        max_two_status=(
            "completed" if second_launch_result_status == "completed" else "attempted"
        ),
        max_two_permission="allowed",
        max_two_reason=(
            "second_launch_completed"
            if second_launch_result_status == "completed"
            else "second_launch_attempted"
        ),
        max_two_receipt_status="ready",
        max_two_mode="second_existing_invocation_call_path_invoked",
        max_two_block_reason="none",
        launch_2_attempt_status="invoked_once",
        launch_2_attempt_reason="second_existing_invocation_call_path_invoked_once",
        launch_2_execution_mode="second_existing_invocation_call_path_invoked",
        launch_2_execution_ref=second_launch_execution_ref,
        launch_2_execution_receipt_status=second_launch_execution_receipt_status,
        launch_2_execution_receipt_kind=second_launch_execution_receipt_kind,
        launch_2_result_status=second_launch_result_status,
        launch_2_result_reason=(
            second_launch_completion_result_reason
            if second_launch_result_status != "completed"
            else "explicit_completion_evidence_confirmed"
        ),
        launch_2_attempted=1,
        launch_2_completed=(
            1
            if (
                second_launch_completed == 1
                and second_launch_completion_evidence_status == "confirmed"
                and second_launch_completion_result_status == "completed"
            )
            else 0
        ),
        max_two_next_action="stop_after_second_launch_attempt",
        launch_2_pause_status="none",
        launch_2_pause_reason="none",
    )

def _build_project_browser_autonomous_next_step_launch_contract_state(
    *,
    bounded_local_loop_contract_status: str,
    contract_available: bool,
    contract_allowed: bool,
    contract_block_reason: str,
    contract_source: str,
    contract_kind: str,
    contract_action: str,
    contract_payload: Any,
    feedback_selected: bool,
    feedback_kind: str,
    feedback_payload_valid: bool,
    next_step_kind: str,
    next_step_action: str,
    next_step_payload: Any,
    generated_prompt_reentry_contract_ready: bool,
    codex_reentry_contract_ready: bool,
    rollback_execution_contract_ready: bool,
    commit_execution_contract_ready: bool,
    next_controller_decision_contract_ready: bool,
    manual_stop_contract_ready: bool,
    budget_contract_checked: bool,
    cycle_budget_remaining: int,
    codex_budget_remaining: int,
    rollback_budget_remaining: int,
    commit_budget_remaining: int,
    unsafe_state_detected: bool,
    dirty_state_requires_stop: bool,
    conflict_requires_stop: bool,
    should_prepare_generated_prompt_reentry: bool,
    should_prepare_codex_reentry: bool,
    should_prepare_rollback_execution: bool,
    should_prepare_commit_execution: bool,
    should_prepare_next_controller_decision: bool,
    should_invoke_codex: bool,
    should_execute_rollback: bool,
    should_execute_commit: bool,
    should_push: bool,
    manual_review_required: bool,
    should_stop: bool,
    stop_reason: str,
    next_action: str,
    selected_lane_result_assimilation_status: str,
    selected_lane_execution_status: str,
    multi_cycle_controller_status: str,
    generated_prompt_reentry_readiness_status: str,
    generated_prompt_reentry_routing_status: str,
    codex_reentry_invocation_status: str,
    rollback_readiness_status: str,
    rollback_execution_status: str,
    commit_tag_readiness_status: str,
    commit_tag_execution_status: str,
) -> dict[str, Any]:
    allowed_statuses = {
        "next_step_launch_contract_generated_prompt_reentry_ready",
        "next_step_launch_contract_rollback_execution_ready",
        "next_step_launch_contract_commit_execution_ready",
        "next_step_launch_contract_manual_stop",
        "next_step_launch_contract_blocked_conflict",
        "next_step_launch_contract_blocked_insufficient_truth",
        "next_step_launch_contract_blocked_unsafe",
        "next_step_launch_contract_blocked_budget",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "launch_generated_prompt_reentry",
        "launch_rollback_execution",
        "launch_commit_execution",
        "manual_review_required",
        "insufficient_truth",
    }
    runtime_posture = [
        "prompt204_next_step_launch_contract",
        "metadata_only",
        "single_bounded_launch_contract",
        "no_execution",
        "no_codex_invocation",
        "no_validation_execution",
        "no_rollback_execution",
        "no_commit_execution",
        "no_push",
    ]

    normalized_loop_status = _normalize_text(
        bounded_local_loop_contract_status, default="insufficient_truth"
    )
    normalized_contract_block_reason = _normalize_text(contract_block_reason, default="")
    normalized_contract_source = _normalize_text(contract_source, default="")
    normalized_contract_kind = _normalize_text(contract_kind, default="")
    normalized_contract_action = _normalize_text(contract_action, default="")
    normalized_feedback_kind = _normalize_text(feedback_kind, default="none")
    normalized_next_step_kind = _normalize_text(next_step_kind, default="none")
    normalized_next_step_action = _normalize_text(next_step_action, default="manual_review_required")
    normalized_stop_reason = _normalize_text(stop_reason, default="")
    normalized_next_action = _normalize_text(next_action, default="manual_review_required")
    normalized_selected_lane_result_assimilation_status = _normalize_text(
        selected_lane_result_assimilation_status, default="insufficient_truth"
    )
    normalized_selected_lane_execution_status = _normalize_text(
        selected_lane_execution_status, default="insufficient_truth"
    )
    normalized_multi_cycle_controller_status = _normalize_text(
        multi_cycle_controller_status, default="insufficient_truth"
    )
    normalized_generated_prompt_reentry_readiness_status = _normalize_text(
        generated_prompt_reentry_readiness_status, default="insufficient_truth"
    )
    normalized_generated_prompt_reentry_routing_status = _normalize_text(
        generated_prompt_reentry_routing_status, default="insufficient_truth"
    )
    normalized_codex_reentry_invocation_status = _normalize_text(
        codex_reentry_invocation_status, default="insufficient_truth"
    )
    normalized_rollback_readiness_status = _normalize_text(
        rollback_readiness_status, default="insufficient_truth"
    )
    normalized_rollback_execution_status = _normalize_text(
        rollback_execution_status, default="insufficient_truth"
    )
    normalized_commit_tag_readiness_status = _normalize_text(
        commit_tag_readiness_status, default="insufficient_truth"
    )
    normalized_commit_tag_execution_status = _normalize_text(
        commit_tag_execution_status, default="insufficient_truth"
    )

    normalized_contract_payload = (
        dict(contract_payload) if isinstance(contract_payload, Mapping) else {}
    )
    normalized_next_step_payload = (
        dict(next_step_payload) if isinstance(next_step_payload, Mapping) else {}
    )

    authoritative_source_selected = bool(
        (
            bool(contract_available)
            or normalized_loop_status
            in {
                "bounded_local_loop_contract_manual_stop",
                "bounded_local_loop_contract_blocked",
                "bounded_local_loop_contract_blocked_insufficient_truth",
            }
        )
        and bool(normalized_contract_kind)
        and bool(normalized_contract_action)
        and bool(normalized_loop_status)
        and (
            not bool(contract_allowed)
            or normalized_contract_kind == "manual_stop"
            or bool(normalized_contract_payload)
        )
    )

    codex_budget_remaining_normalized = _as_non_negative_int(codex_budget_remaining, default=0)
    rollback_budget_remaining_normalized = _as_non_negative_int(
        rollback_budget_remaining, default=0
    )
    commit_budget_remaining_normalized = _as_non_negative_int(commit_budget_remaining, default=0)
    cycle_budget_remaining_normalized = _as_non_negative_int(cycle_budget_remaining, default=0)
    launch_budget_checked = bool(budget_contract_checked)

    generated_payload_kind = _normalize_text(normalized_contract_payload.get("prompt_kind"), default="")
    generated_payload_path = _normalize_text(normalized_contract_payload.get("prompt_path"), default="")
    generated_prompt_reentry_launch_candidate = bool(
        bool(contract_allowed)
        and normalized_contract_kind == "generated_prompt_reentry"
        and bool(generated_prompt_reentry_contract_ready)
        and bool(should_prepare_generated_prompt_reentry)
        and codex_budget_remaining_normalized > 0
        and not bool(manual_review_required)
        and not bool(should_stop)
    )
    rollback_execution_launch_candidate = bool(
        bool(contract_allowed)
        and normalized_contract_kind == "rollback_execution"
        and bool(rollback_execution_contract_ready)
        and bool(should_prepare_rollback_execution)
        and rollback_budget_remaining_normalized > 0
        and not bool(manual_review_required)
        and not bool(should_stop)
    )
    commit_execution_launch_candidate = bool(
        bool(contract_allowed)
        and normalized_contract_kind == "commit_execution"
        and bool(commit_execution_contract_ready)
        and bool(should_prepare_commit_execution)
        and commit_budget_remaining_normalized > 0
        and not bool(manual_review_required)
        and not bool(should_stop)
    )
    manual_stop_launch_candidate = bool(
        normalized_contract_kind == "manual_stop"
        or bool(manual_stop_contract_ready)
        or bool(manual_review_required)
        or bool(should_stop)
        or normalized_loop_status
        in {
            "bounded_local_loop_contract_blocked",
            "bounded_local_loop_contract_blocked_insufficient_truth",
        }
    )

    non_stop_candidates: list[str] = []
    if generated_prompt_reentry_launch_candidate:
        non_stop_candidates.append("generated_prompt_reentry_launch")
    if rollback_execution_launch_candidate:
        non_stop_candidates.append("rollback_execution_launch")
    if commit_execution_launch_candidate:
        non_stop_candidates.append("commit_execution_launch")
    non_stop_candidates = sorted(non_stop_candidates)

    launch_contract_available = False
    launch_contract_allowed = False
    launch_contract_block_reason = ""
    launch_contract_source = "prompt203_bounded_local_loop_contract"
    launch_contract_kind = "manual_stop"
    launch_contract_action = "manual_review_required"
    launch_contract_payload: dict[str, Any] = {}
    launch_contract_ready_for_executor = False
    selected_launch_kind = "manual_stop"
    selected_launch_action = "manual_review_required"
    selected_launch_payload: dict[str, Any] = {}
    exactly_one_launch_contract = False
    launch_conflict_detected = False
    conflicting_launch_contracts: list[str] = []
    generated_prompt_reentry_launch_ready = False
    rollback_execution_launch_ready = False
    commit_execution_launch_ready = False
    manual_stop_launch_ready = False
    launch_safety_checked = bool(authoritative_source_selected)
    launch_requires_existing_executor = False
    out_should_invoke_codex = False
    out_should_execute_rollback = False
    out_should_execute_commit = False
    out_should_push = False
    out_manual_review_required = True
    out_should_stop = True
    out_stop_reason = normalized_stop_reason or "insufficient_next_step_launch_contract_truth"
    out_next_action = "manual_review_required"
    status = "next_step_launch_contract_blocked_insufficient_truth"

    safety_policy_block = bool(
        not launch_budget_checked
        or bool(unsafe_state_detected)
        or bool(dirty_state_requires_stop)
        or bool(conflict_requires_stop)
        or bool(should_invoke_codex)
        or bool(should_execute_rollback)
        or bool(should_execute_commit)
        or bool(should_push)
        or bool(manual_review_required)
        or bool(should_stop)
    )
    budget_policy_block = bool(not launch_budget_checked)

    if len(non_stop_candidates) > 1:
        status = "next_step_launch_contract_blocked_conflict"
        launch_contract_available = True
        launch_contract_allowed = False
        launch_contract_ready_for_executor = False
        launch_conflict_detected = True
        conflicting_launch_contracts = list(non_stop_candidates)
        launch_contract_block_reason = "conflicting_next_step_launch_contracts"
        launch_safety_checked = True
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "conflicting_next_step_launch_contracts"
        out_next_action = "manual_review_required"
    elif manual_stop_launch_candidate and not (
        len(non_stop_candidates) == 1 and bool(contract_allowed)
    ):
        status = "next_step_launch_contract_manual_stop"
        launch_contract_available = True
        launch_contract_allowed = False
        launch_contract_kind = "manual_stop"
        launch_contract_action = "manual_review_required"
        launch_contract_payload = {
            "source": "prompt203_bounded_local_loop_contract",
            "stop_reason": normalized_stop_reason or "manual_stop",
            "next_action": "manual_review_required",
        }
        selected_launch_kind = "manual_stop"
        selected_launch_action = "manual_review_required"
        selected_launch_payload = dict(launch_contract_payload)
        exactly_one_launch_contract = True
        launch_conflict_detected = False
        conflicting_launch_contracts = []
        generated_prompt_reentry_launch_ready = False
        rollback_execution_launch_ready = False
        commit_execution_launch_ready = False
        manual_stop_launch_ready = True
        launch_contract_ready_for_executor = False
        launch_safety_checked = True
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = normalized_stop_reason or "manual_stop"
        out_next_action = "manual_review_required"
    elif not authoritative_source_selected:
        status = "next_step_launch_contract_blocked_insufficient_truth"
        launch_contract_available = False
        launch_contract_allowed = False
        launch_contract_block_reason = "insufficient_next_step_launch_contract_truth"
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_next_step_launch_contract_truth"
        out_next_action = "manual_review_required"
    elif len(non_stop_candidates) == 0:
        status = "next_step_launch_contract_blocked_insufficient_truth"
        launch_contract_available = False
        launch_contract_allowed = False
        launch_contract_block_reason = "insufficient_next_step_launch_contract_truth"
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_next_step_launch_contract_truth"
        out_next_action = "manual_review_required"
    elif safety_policy_block:
        status = (
            "next_step_launch_contract_blocked_budget"
            if budget_policy_block
            else "next_step_launch_contract_blocked_unsafe"
        )
        launch_contract_available = True
        launch_contract_allowed = False
        launch_contract_ready_for_executor = False
        launch_contract_block_reason = (
            "blocked_budget"
            if budget_policy_block
            else (
                "blocked_unsafe"
                if not bool(conflict_requires_stop)
                else "conflicting_next_step_launch_contracts"
            )
        )
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = normalized_stop_reason or launch_contract_block_reason
        out_next_action = "manual_review_required"
    else:
        chosen = non_stop_candidates[0]
        exactly_one_launch_contract = True
        launch_contract_available = True
        launch_contract_allowed = True
        launch_contract_source = "prompt203_bounded_local_loop_contract"
        launch_contract_ready_for_executor = True
        launch_requires_existing_executor = True
        launch_conflict_detected = False
        conflicting_launch_contracts = []
        out_manual_review_required = False
        out_should_stop = False
        out_stop_reason = ""
        if chosen == "generated_prompt_reentry_launch":
            status = "next_step_launch_contract_generated_prompt_reentry_ready"
            launch_contract_kind = "generated_prompt_reentry_launch"
            launch_contract_action = "launch_generated_prompt_reentry"
            launch_contract_payload = {
                "prompt_kind": generated_payload_kind,
                "prompt_path": generated_payload_path,
                "source": "prompt203_bounded_local_loop_contract",
                "max_invocations": 1,
                "next_action": "launch_generated_prompt_reentry",
            }
            generated_prompt_reentry_launch_ready = True
            selected_launch_kind = launch_contract_kind
            selected_launch_action = launch_contract_action
            selected_launch_payload = dict(launch_contract_payload)
            out_next_action = "launch_generated_prompt_reentry"
        elif chosen == "rollback_execution_launch":
            status = "next_step_launch_contract_rollback_execution_ready"
            launch_contract_kind = "rollback_execution_launch"
            launch_contract_action = "launch_rollback_execution"
            launch_contract_payload = {
                "source": "prompt203_bounded_local_loop_contract",
                "max_rollback_attempts": 1,
                "next_action": "launch_rollback_execution",
            }
            rollback_execution_launch_ready = True
            selected_launch_kind = launch_contract_kind
            selected_launch_action = launch_contract_action
            selected_launch_payload = dict(launch_contract_payload)
            out_next_action = "launch_rollback_execution"
        else:
            status = "next_step_launch_contract_commit_execution_ready"
            launch_contract_kind = "commit_execution_launch"
            launch_contract_action = "launch_commit_execution"
            launch_contract_payload = {
                "source": "prompt203_bounded_local_loop_contract",
                "max_commit_attempts": 1,
                "next_action": "launch_commit_execution",
            }
            commit_execution_launch_ready = True
            selected_launch_kind = launch_contract_kind
            selected_launch_action = launch_contract_action
            selected_launch_payload = dict(launch_contract_payload)
            out_next_action = "launch_commit_execution"

    if not launch_contract_payload:
        launch_contract_payload = {
            "source": "prompt203_bounded_local_loop_contract",
            "stop_reason": out_stop_reason or normalized_contract_block_reason,
            "next_action": out_next_action,
        }
    if not selected_launch_payload:
        selected_launch_payload = dict(launch_contract_payload)

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if out_next_action not in allowed_next_actions:
        out_next_action = "insufficient_truth"
    if status == "insufficient_truth":
        status = "next_step_launch_contract_blocked_insufficient_truth"
        launch_contract_available = False
        launch_contract_allowed = False
        launch_contract_block_reason = "insufficient_next_step_launch_contract_truth"
        launch_contract_source = "prompt203_bounded_local_loop_contract"
        launch_contract_kind = "manual_stop"
        launch_contract_action = "manual_review_required"
        launch_contract_payload = {
            "source": "prompt203_bounded_local_loop_contract",
            "stop_reason": "insufficient_next_step_launch_contract_truth",
            "next_action": "manual_review_required",
        }
        launch_contract_ready_for_executor = False
        selected_launch_kind = "manual_stop"
        selected_launch_action = "manual_review_required"
        selected_launch_payload = dict(launch_contract_payload)
        exactly_one_launch_contract = False
        launch_conflict_detected = False
        conflicting_launch_contracts = []
        generated_prompt_reentry_launch_ready = False
        rollback_execution_launch_ready = False
        commit_execution_launch_ready = False
        manual_stop_launch_ready = False
        launch_budget_checked = bool(launch_budget_checked)
        launch_safety_checked = False
        launch_requires_existing_executor = False
        out_should_invoke_codex = False
        out_should_execute_rollback = False
        out_should_execute_commit = False
        out_should_push = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_next_step_launch_contract_truth"
        out_next_action = "manual_review_required"

    return {
        "project_browser_autonomous_next_step_launch_contract_status": status,
        "project_browser_autonomous_next_step_launch_contract_launch_contract_available": bool(
            launch_contract_available
        ),
        "project_browser_autonomous_next_step_launch_contract_launch_contract_allowed": bool(
            launch_contract_allowed
        ),
        "project_browser_autonomous_next_step_launch_contract_launch_contract_block_reason": (
            launch_contract_block_reason
        ),
        "project_browser_autonomous_next_step_launch_contract_launch_contract_source": (
            launch_contract_source
        ),
        "project_browser_autonomous_next_step_launch_contract_launch_contract_kind": (
            launch_contract_kind
        ),
        "project_browser_autonomous_next_step_launch_contract_launch_contract_action": (
            launch_contract_action
        ),
        "project_browser_autonomous_next_step_launch_contract_launch_contract_payload": (
            launch_contract_payload
        ),
        "project_browser_autonomous_next_step_launch_contract_launch_contract_ready_for_executor": bool(
            launch_contract_ready_for_executor
        ),
        "project_browser_autonomous_next_step_launch_contract_selected_launch_kind": (
            selected_launch_kind
        ),
        "project_browser_autonomous_next_step_launch_contract_selected_launch_action": (
            selected_launch_action
        ),
        "project_browser_autonomous_next_step_launch_contract_selected_launch_payload": (
            selected_launch_payload
        ),
        "project_browser_autonomous_next_step_launch_contract_exactly_one_launch_contract": bool(
            exactly_one_launch_contract
        ),
        "project_browser_autonomous_next_step_launch_contract_launch_conflict_detected": bool(
            launch_conflict_detected
        ),
        "project_browser_autonomous_next_step_launch_contract_conflicting_launch_contracts": (
            conflicting_launch_contracts
        ),
        "project_browser_autonomous_next_step_launch_contract_generated_prompt_reentry_launch_ready": bool(
            generated_prompt_reentry_launch_ready
        ),
        "project_browser_autonomous_next_step_launch_contract_rollback_execution_launch_ready": bool(
            rollback_execution_launch_ready
        ),
        "project_browser_autonomous_next_step_launch_contract_commit_execution_launch_ready": bool(
            commit_execution_launch_ready
        ),
        "project_browser_autonomous_next_step_launch_contract_manual_stop_launch_ready": bool(
            manual_stop_launch_ready
        ),
        "project_browser_autonomous_next_step_launch_contract_codex_budget_remaining": int(
            codex_budget_remaining_normalized
        ),
        "project_browser_autonomous_next_step_launch_contract_rollback_budget_remaining": int(
            rollback_budget_remaining_normalized
        ),
        "project_browser_autonomous_next_step_launch_contract_commit_budget_remaining": int(
            commit_budget_remaining_normalized
        ),
        "project_browser_autonomous_next_step_launch_contract_launch_budget_checked": bool(
            launch_budget_checked
        ),
        "project_browser_autonomous_next_step_launch_contract_launch_safety_checked": bool(
            launch_safety_checked
        ),
        "project_browser_autonomous_next_step_launch_contract_launch_requires_existing_executor": bool(
            launch_requires_existing_executor
        ),
        "project_browser_autonomous_next_step_launch_contract_should_invoke_codex": bool(
            out_should_invoke_codex
        ),
        "project_browser_autonomous_next_step_launch_contract_should_execute_rollback": bool(
            out_should_execute_rollback
        ),
        "project_browser_autonomous_next_step_launch_contract_should_execute_commit": bool(
            out_should_execute_commit
        ),
        "project_browser_autonomous_next_step_launch_contract_should_push": bool(out_should_push),
        "project_browser_autonomous_next_step_launch_contract_manual_review_required": bool(
            out_manual_review_required
        ),
        "project_browser_autonomous_next_step_launch_contract_should_stop": bool(
            out_should_stop
        ),
        "project_browser_autonomous_next_step_launch_contract_stop_reason": out_stop_reason,
        "project_browser_autonomous_next_step_launch_contract_next_action": out_next_action,
        "project_browser_autonomous_next_step_launch_contract_runtime_posture": runtime_posture,
        "project_browser_autonomous_next_step_launch_contract_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_loop_status,
                    normalized_contract_block_reason,
                    normalized_contract_source,
                    normalized_contract_kind,
                    normalized_contract_action,
                    normalized_feedback_kind,
                    normalized_next_step_kind,
                    normalized_next_step_action,
                    normalized_stop_reason,
                    normalized_next_action,
                    normalized_selected_lane_result_assimilation_status,
                    normalized_selected_lane_execution_status,
                    normalized_multi_cycle_controller_status,
                    normalized_generated_prompt_reentry_readiness_status,
                    normalized_generated_prompt_reentry_routing_status,
                    normalized_codex_reentry_invocation_status,
                    normalized_rollback_readiness_status,
                    normalized_rollback_execution_status,
                    normalized_commit_tag_readiness_status,
                    normalized_commit_tag_execution_status,
                    "authoritative_source_not_selected" if not authoritative_source_selected else "",
                    "launch_budget_not_checked" if not launch_budget_checked else "",
                    "feedback_payload_invalid"
                    if bool(feedback_selected) and not bool(feedback_payload_valid)
                    else "",
                    "non_stop_candidate_count_gt_one" if len(non_stop_candidates) > 1 else "",
                ]
            )
        ),
    }

def _build_project_browser_autonomous_next_step_launch_execution_state(
    *,
    launch_contract_status: str,
    launch_contract_available: bool,
    launch_contract_allowed: bool,
    launch_contract_block_reason: str,
    launch_contract_source: str,
    launch_contract_kind: str,
    launch_contract_action: str,
    launch_contract_payload: Any,
    launch_contract_ready_for_executor: bool,
    selected_launch_kind: str,
    selected_launch_action: str,
    selected_launch_payload: Any,
    exactly_one_launch_contract: bool,
    launch_conflict_detected: bool,
    conflicting_launch_contracts: list[str] | None,
    generated_prompt_reentry_launch_ready: bool,
    rollback_execution_launch_ready: bool,
    commit_execution_launch_ready: bool,
    manual_stop_launch_ready: bool,
    codex_budget_remaining: int,
    rollback_budget_remaining: int,
    commit_budget_remaining: int,
    launch_budget_checked: bool,
    launch_safety_checked: bool,
    launch_requires_existing_executor: bool,
    launch_should_invoke_codex: bool,
    launch_should_execute_rollback: bool,
    launch_should_execute_commit: bool,
    launch_should_push: bool,
    launch_manual_review_required: bool,
    launch_should_stop: bool,
    launch_stop_reason: str,
    launch_next_action: str,
    bounded_local_loop_contract_status: str,
    selected_lane_result_assimilation_status: str,
    generated_prompt_reentry_readiness_status: str,
    generated_prompt_reentry_routing_status: str,
    codex_reentry_invocation_status: str,
    codex_reentry_invocation_next_action: str,
    codex_reentry_result_class: str,
    codex_reentry_result_ready_for_assimilation: bool,
    codex_reentry_invocation_attempted: bool,
    codex_reentry_human_review_required: bool,
    rollback_readiness_status: str,
    rollback_execution_status: str,
    rollback_execution_next_action: str,
    rollback_execution_human_review_required: bool,
    commit_tag_readiness_status: str,
    commit_tag_execution_status: str,
    commit_tag_execution_next_action: str,
    commit_tag_execution_human_review_required: bool,
) -> dict[str, Any]:
    allowed_statuses = {
        "next_step_launch_execution_generated_prompt_reentry_completed",
        "next_step_launch_execution_rollback_completed",
        "next_step_launch_execution_commit_completed",
        "next_step_launch_execution_manual_stop",
        "next_step_launch_execution_blocked_not_allowed",
        "next_step_launch_execution_blocked_multiple_launches",
        "next_step_launch_execution_blocked_unknown_launch",
        "next_step_launch_execution_blocked_existing_path",
        "next_step_launch_execution_blocked_insufficient_truth",
        "next_step_launch_execution_failed",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "assimilate_next_step_launch_result",
        "manual_review_required",
        "insufficient_truth",
    }
    runtime_posture = [
        "prompt205_next_step_launch_execution",
        "single_bounded_launch_only",
        "delegated_existing_paths_only",
        "no_new_executor",
        "no_retry",
        "no_loop",
        "no_push",
        "no_github_mutation",
    ]

    normalized_launch_contract_status = _normalize_text(
        launch_contract_status,
        default="insufficient_truth",
    )
    normalized_launch_contract_block_reason = _normalize_text(
        launch_contract_block_reason,
        default="",
    )
    normalized_launch_contract_source = _normalize_text(
        launch_contract_source,
        default="prompt204_next_step_launch_contract",
    )
    normalized_launch_contract_kind = _normalize_text(launch_contract_kind, default="")
    normalized_launch_contract_action = _normalize_text(
        launch_contract_action,
        default="manual_review_required",
    )
    normalized_selected_launch_kind = _normalize_text(selected_launch_kind, default="")
    normalized_selected_launch_action = _normalize_text(
        selected_launch_action,
        default="manual_review_required",
    )
    normalized_launch_stop_reason = _normalize_text(launch_stop_reason, default="")
    normalized_launch_next_action = _normalize_text(
        launch_next_action,
        default="manual_review_required",
    )
    normalized_bounded_local_loop_contract_status = _normalize_text(
        bounded_local_loop_contract_status,
        default="insufficient_truth",
    )
    normalized_selected_lane_result_assimilation_status = _normalize_text(
        selected_lane_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_generated_prompt_reentry_readiness_status = _normalize_text(
        generated_prompt_reentry_readiness_status,
        default="insufficient_truth",
    )
    normalized_generated_prompt_reentry_routing_status = _normalize_text(
        generated_prompt_reentry_routing_status,
        default="insufficient_truth",
    )
    normalized_codex_reentry_invocation_status = _normalize_text(
        codex_reentry_invocation_status,
        default="insufficient_truth",
    )
    normalized_codex_reentry_invocation_next_action = _normalize_text(
        codex_reentry_invocation_next_action,
        default="manual_review_required",
    )
    normalized_codex_reentry_result_class = _normalize_text(
        codex_reentry_result_class,
        default="blocked",
    )
    normalized_rollback_readiness_status = _normalize_text(
        rollback_readiness_status,
        default="insufficient_truth",
    )
    normalized_rollback_execution_status = _normalize_text(
        rollback_execution_status,
        default="insufficient_truth",
    )
    normalized_rollback_execution_next_action = _normalize_text(
        rollback_execution_next_action,
        default="manual_review_required",
    )
    normalized_commit_tag_readiness_status = _normalize_text(
        commit_tag_readiness_status,
        default="insufficient_truth",
    )
    normalized_commit_tag_execution_status = _normalize_text(
        commit_tag_execution_status,
        default="insufficient_truth",
    )
    normalized_commit_tag_execution_next_action = _normalize_text(
        commit_tag_execution_next_action,
        default="manual_review_required",
    )

    normalized_launch_contract_payload = (
        dict(launch_contract_payload) if isinstance(launch_contract_payload, Mapping) else {}
    )
    normalized_selected_launch_payload = (
        dict(selected_launch_payload) if isinstance(selected_launch_payload, Mapping) else {}
    )
    normalized_conflicting_launch_contracts = _normalize_string_list(
        conflicting_launch_contracts
    )

    normalized_codex_budget_remaining = _as_non_negative_int(codex_budget_remaining, default=0)
    normalized_rollback_budget_remaining = _as_non_negative_int(
        rollback_budget_remaining,
        default=0,
    )
    normalized_commit_budget_remaining = _as_non_negative_int(commit_budget_remaining, default=0)

    effective_selected_kind = (
        normalized_selected_launch_kind or normalized_launch_contract_kind
    )
    effective_selected_action = (
        normalized_selected_launch_action or normalized_launch_contract_action
    )
    effective_selected_payload = (
        normalized_selected_launch_payload
        if normalized_selected_launch_payload
        else normalized_launch_contract_payload
    )

    non_selected_candidates_true: list[str] = []
    if effective_selected_kind != "generated_prompt_reentry_launch" and bool(
        generated_prompt_reentry_launch_ready
    ):
        non_selected_candidates_true.append("generated_prompt_reentry_launch")
    if effective_selected_kind != "rollback_execution_launch" and bool(
        rollback_execution_launch_ready
    ):
        non_selected_candidates_true.append("rollback_execution_launch")
    if effective_selected_kind != "commit_execution_launch" and bool(
        commit_execution_launch_ready
    ):
        non_selected_candidates_true.append("commit_execution_launch")
    if effective_selected_kind != "manual_stop" and bool(manual_stop_launch_ready):
        non_selected_candidates_true.append("manual_stop")
    non_selected_candidates_true = sorted(non_selected_candidates_true)

    manual_stop_rule = bool(
        effective_selected_kind == "manual_stop"
        or bool(manual_stop_launch_ready)
        or bool(launch_manual_review_required)
        or bool(launch_should_stop)
    )

    selected_kind_is_supported = effective_selected_kind in {
        "generated_prompt_reentry_launch",
        "rollback_execution_launch",
        "commit_execution_launch",
    }
    selected_budget_ok = bool(
        (
            effective_selected_kind == "generated_prompt_reentry_launch"
            and normalized_codex_budget_remaining > 0
        )
        or (
            effective_selected_kind == "rollback_execution_launch"
            and normalized_rollback_budget_remaining > 0
        )
        or (
            effective_selected_kind == "commit_execution_launch"
            and normalized_commit_budget_remaining > 0
        )
    )
    allow_base = bool(
        bool(launch_contract_available)
        and bool(launch_contract_allowed)
        and bool(launch_contract_ready_for_executor)
        and bool(exactly_one_launch_contract)
        and not bool(launch_conflict_detected)
        and bool(launch_budget_checked)
        and bool(launch_safety_checked)
        and bool(launch_requires_existing_executor)
        and selected_kind_is_supported
        and not bool(launch_manual_review_required)
        and not bool(launch_should_stop)
        and not bool(launch_should_push)
        and not bool(non_selected_candidates_true)
        and selected_budget_ok
    )

    block_reason = _first_true_reason(
        [
            (not bool(launch_contract_allowed), "blocked_launch_contract_not_allowed"),
            (not bool(launch_contract_ready_for_executor), "blocked_launch_contract_not_ready"),
            (
                not bool(exactly_one_launch_contract),
                "blocked_not_exactly_one_launch_contract",
            ),
            (bool(launch_conflict_detected), "blocked_launch_conflict_detected"),
            (not bool(launch_budget_checked), "blocked_launch_budget_not_checked"),
            (not bool(launch_safety_checked), "blocked_launch_safety_not_checked"),
            (
                not bool(launch_requires_existing_executor),
                "blocked_existing_executor_not_required_or_missing",
            ),
            (bool(launch_manual_review_required), "blocked_manual_review_required"),
            (bool(launch_should_stop), "blocked_should_stop"),
            (bool(launch_should_push), "blocked_unexpected_push_flag"),
            (
                effective_selected_kind == "generated_prompt_reentry_launch"
                and normalized_codex_budget_remaining <= 0,
                "blocked_codex_budget_exhausted",
            ),
            (
                effective_selected_kind == "rollback_execution_launch"
                and normalized_rollback_budget_remaining <= 0,
                "blocked_rollback_budget_exhausted",
            ),
            (
                effective_selected_kind == "commit_execution_launch"
                and normalized_commit_budget_remaining <= 0,
                "blocked_commit_budget_exhausted",
            ),
            (len(non_selected_candidates_true) > 0, "blocked_multiple_launch_executions"),
            (
                not manual_stop_rule and not selected_kind_is_supported,
                "blocked_unknown_selected_launch_kind",
            ),
        ],
        default="blocked_insufficient_next_step_launch_execution_truth",
    )

    status = "next_step_launch_execution_blocked_insufficient_truth"
    launch_execution_allowed = False
    launch_execution_attempted = False
    launch_execution_completed = False
    launch_execution_failed = False
    launch_execution_block_reason = block_reason
    launch_execution_source = "prompt204_next_step_launch_contract"
    non_selected_launches_noop = True
    generated_prompt_reentry_launch_executed = False
    rollback_execution_launch_executed = False
    commit_execution_launch_executed = False
    manual_stop_launch_executed = False
    delegated_existing_path = False
    delegated_existing_path_kind = "none"
    delegated_existing_status = "insufficient_truth"
    delegated_existing_next_action = "manual_review_required"
    generated_prompt_reentry_result_status = ""
    rollback_execution_result_status = ""
    commit_execution_result_status = ""
    result_class = "blocked"
    out_should_invoke_codex = False
    out_should_execute_rollback = False
    out_should_execute_commit = False
    out_should_push = False
    out_manual_review_required = True
    out_should_stop = True
    out_stop_reason = normalized_launch_stop_reason or block_reason
    out_next_action = "manual_review_required"

    if manual_stop_rule:
        status = "next_step_launch_execution_manual_stop"
        launch_execution_allowed = False
        launch_execution_attempted = False
        launch_execution_completed = False
        launch_execution_failed = False
        launch_execution_block_reason = ""
        non_selected_launches_noop = True
        manual_stop_launch_executed = True
        result_class = "manual_stop"
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = normalized_launch_stop_reason or "manual_stop"
        out_next_action = "manual_review_required"
    elif not allow_base:
        status = (
            "next_step_launch_execution_blocked_unknown_launch"
            if block_reason == "blocked_unknown_selected_launch_kind"
            else (
                "next_step_launch_execution_blocked_multiple_launches"
                if block_reason == "blocked_multiple_launch_executions"
                else "next_step_launch_execution_blocked_not_allowed"
            )
        )
        launch_execution_allowed = False
        launch_execution_attempted = False
        launch_execution_completed = False
        launch_execution_failed = False
        launch_execution_block_reason = block_reason
        non_selected_launches_noop = True
        result_class = "blocked"
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = normalized_launch_stop_reason or block_reason
        out_next_action = "manual_review_required"
    else:
        launch_execution_allowed = True
        launch_execution_attempted = True
        non_selected_launches_noop = True
        delegated_existing_path = True
        launch_execution_source = "prompt204_next_step_launch_contract"

        if effective_selected_kind == "generated_prompt_reentry_launch":
            generated_prompt_reentry_launch_executed = True
            delegated_existing_path_kind = "generated_prompt_reentry"
            delegated_existing_status = normalized_codex_reentry_invocation_status
            delegated_existing_next_action = normalized_codex_reentry_invocation_next_action
            generated_prompt_reentry_result_status = normalized_codex_reentry_invocation_status
            launch_execution_attempted = bool(codex_reentry_invocation_attempted)
            if normalized_codex_reentry_invocation_status in {
                "reentry_invocation_completed_with_changes",
                "reentry_invocation_completed_no_changes",
                "reentry_invocation_completed_failure",
                "reentry_invocation_completed_timeout",
            } and bool(codex_reentry_result_ready_for_assimilation):
                status = "next_step_launch_execution_generated_prompt_reentry_completed"
                launch_execution_completed = True
                launch_execution_failed = bool(
                    normalized_codex_reentry_result_class
                    in {"completed_failure", "completed_timeout"}
                    or bool(codex_reentry_human_review_required)
                )
                launch_execution_block_reason = ""
                result_class = (
                    normalized_codex_reentry_result_class
                    if normalized_codex_reentry_result_class
                    else "generated_prompt_reentry_completed"
                )
                out_manual_review_required = bool(codex_reentry_human_review_required)
                out_should_stop = bool(codex_reentry_human_review_required)
                out_stop_reason = (
                    "generated_prompt_reentry_requires_manual_review"
                    if out_manual_review_required
                    else ""
                )
                out_next_action = "assimilate_next_step_launch_result"
            elif normalized_codex_reentry_invocation_status.startswith("blocked_"):
                status = "next_step_launch_execution_blocked_existing_path"
                launch_execution_completed = False
                launch_execution_failed = False
                launch_execution_block_reason = "blocked_existing_delegated_path"
                result_class = "blocked"
                out_manual_review_required = True
                out_should_stop = True
                out_stop_reason = "blocked_existing_delegated_path"
                out_next_action = "manual_review_required"
            else:
                status = "next_step_launch_execution_blocked_insufficient_truth"
                launch_execution_completed = False
                launch_execution_failed = False
                launch_execution_block_reason = (
                    "blocked_insufficient_next_step_launch_execution_truth"
                )
                result_class = "insufficient_truth"
                out_manual_review_required = True
                out_should_stop = True
                out_stop_reason = "blocked_insufficient_next_step_launch_execution_truth"
                out_next_action = "manual_review_required"
        elif effective_selected_kind == "rollback_execution_launch":
            rollback_execution_launch_executed = True
            delegated_existing_path_kind = "rollback_execution"
            delegated_existing_status = normalized_rollback_execution_status
            delegated_existing_next_action = normalized_rollback_execution_next_action
            rollback_execution_result_status = normalized_rollback_execution_status
            if normalized_rollback_execution_status in {
                "rollback_execution_completed",
                "rollback_execution_partial_failure",
                "rollback_execution_failed",
                "rollback_execution_timeout",
            }:
                status = "next_step_launch_execution_rollback_completed"
                launch_execution_completed = True
                launch_execution_failed = bool(
                    normalized_rollback_execution_status
                    in {
                        "rollback_execution_partial_failure",
                        "rollback_execution_failed",
                        "rollback_execution_timeout",
                    }
                )
                launch_execution_block_reason = ""
                result_class = normalized_rollback_execution_status
                out_manual_review_required = bool(
                    rollback_execution_human_review_required or launch_execution_failed
                )
                out_should_stop = bool(out_manual_review_required)
                out_stop_reason = (
                    "rollback_execution_requires_manual_review"
                    if out_manual_review_required
                    else ""
                )
                out_next_action = "assimilate_next_step_launch_result"
            elif normalized_rollback_execution_status.startswith("rollback_execution_blocked"):
                status = "next_step_launch_execution_blocked_existing_path"
                launch_execution_completed = False
                launch_execution_failed = False
                launch_execution_block_reason = "blocked_existing_delegated_path"
                result_class = "blocked"
                out_manual_review_required = True
                out_should_stop = True
                out_stop_reason = "blocked_existing_delegated_path"
                out_next_action = "manual_review_required"
            else:
                status = "next_step_launch_execution_blocked_insufficient_truth"
                launch_execution_block_reason = (
                    "blocked_insufficient_next_step_launch_execution_truth"
                )
                result_class = "insufficient_truth"
                out_manual_review_required = True
                out_should_stop = True
                out_stop_reason = "blocked_insufficient_next_step_launch_execution_truth"
                out_next_action = "manual_review_required"
        elif effective_selected_kind == "commit_execution_launch":
            commit_execution_launch_executed = True
            delegated_existing_path_kind = "commit_execution"
            delegated_existing_status = normalized_commit_tag_execution_status
            delegated_existing_next_action = normalized_commit_tag_execution_next_action
            commit_execution_result_status = normalized_commit_tag_execution_status
            if normalized_commit_tag_execution_status in {
                "commit_tag_execution_completed",
                "commit_tag_execution_failed_git_add",
                "commit_tag_execution_failed_git_commit",
                "commit_tag_execution_failed_git_tag",
                "commit_tag_execution_partial_commit_tag_failed",
                "commit_tag_execution_timeout",
            }:
                status = "next_step_launch_execution_commit_completed"
                launch_execution_completed = True
                launch_execution_failed = bool(
                    normalized_commit_tag_execution_status
                    != "commit_tag_execution_completed"
                )
                launch_execution_block_reason = ""
                result_class = normalized_commit_tag_execution_status
                out_manual_review_required = bool(
                    commit_tag_execution_human_review_required or launch_execution_failed
                )
                out_should_stop = bool(out_manual_review_required)
                out_stop_reason = (
                    "commit_execution_requires_manual_review"
                    if out_manual_review_required
                    else ""
                )
                out_next_action = "assimilate_next_step_launch_result"
            elif normalized_commit_tag_execution_status.startswith("commit_tag_execution_blocked"):
                status = "next_step_launch_execution_blocked_existing_path"
                launch_execution_completed = False
                launch_execution_failed = False
                launch_execution_block_reason = "blocked_existing_delegated_path"
                result_class = "blocked"
                out_manual_review_required = True
                out_should_stop = True
                out_stop_reason = "blocked_existing_delegated_path"
                out_next_action = "manual_review_required"
            else:
                status = "next_step_launch_execution_blocked_insufficient_truth"
                launch_execution_block_reason = (
                    "blocked_insufficient_next_step_launch_execution_truth"
                )
                result_class = "insufficient_truth"
                out_manual_review_required = True
                out_should_stop = True
                out_stop_reason = "blocked_insufficient_next_step_launch_execution_truth"
                out_next_action = "manual_review_required"
        else:
            status = "next_step_launch_execution_blocked_unknown_launch"
            launch_execution_allowed = False
            launch_execution_attempted = False
            launch_execution_completed = False
            launch_execution_failed = False
            launch_execution_block_reason = "blocked_unknown_selected_launch_kind"
            delegated_existing_path = False
            delegated_existing_path_kind = "none"
            delegated_existing_status = "insufficient_truth"
            delegated_existing_next_action = "manual_review_required"
            result_class = "blocked"
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = "blocked_unknown_selected_launch_kind"
            out_next_action = "manual_review_required"

    total_launch_executed = sum(
        [
            1 if generated_prompt_reentry_launch_executed else 0,
            1 if rollback_execution_launch_executed else 0,
            1 if commit_execution_launch_executed else 0,
            1 if manual_stop_launch_executed else 0,
        ]
    )
    if total_launch_executed > 1:
        status = "next_step_launch_execution_blocked_multiple_launches"
        launch_execution_allowed = False
        launch_execution_attempted = False
        launch_execution_completed = False
        launch_execution_failed = False
        launch_execution_block_reason = "blocked_multiple_launch_executions"
        non_selected_launches_noop = False
        generated_prompt_reentry_launch_executed = False
        rollback_execution_launch_executed = False
        commit_execution_launch_executed = False
        manual_stop_launch_executed = False
        delegated_existing_path = False
        delegated_existing_path_kind = "none"
        delegated_existing_status = "insufficient_truth"
        delegated_existing_next_action = "manual_review_required"
        generated_prompt_reentry_result_status = ""
        rollback_execution_result_status = ""
        commit_execution_result_status = ""
        result_class = "blocked"
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "blocked_multiple_launch_executions"
        out_next_action = "manual_review_required"

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if out_next_action not in allowed_next_actions:
        out_next_action = "insufficient_truth"
    if status == "insufficient_truth":
        status = "next_step_launch_execution_blocked_insufficient_truth"
        launch_execution_allowed = False
        launch_execution_attempted = False
        launch_execution_completed = False
        launch_execution_failed = False
        launch_execution_block_reason = "blocked_insufficient_next_step_launch_execution_truth"
        launch_execution_source = "prompt204_next_step_launch_contract"
        non_selected_launches_noop = True
        generated_prompt_reentry_launch_executed = False
        rollback_execution_launch_executed = False
        commit_execution_launch_executed = False
        manual_stop_launch_executed = False
        delegated_existing_path = False
        delegated_existing_path_kind = "none"
        delegated_existing_status = "insufficient_truth"
        delegated_existing_next_action = "manual_review_required"
        generated_prompt_reentry_result_status = ""
        rollback_execution_result_status = ""
        commit_execution_result_status = ""
        result_class = "insufficient_truth"
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "blocked_insufficient_next_step_launch_execution_truth"
        out_next_action = "manual_review_required"

    return {
        "project_browser_autonomous_next_step_launch_execution_status": status,
        "project_browser_autonomous_next_step_launch_execution_launch_execution_allowed": bool(
            launch_execution_allowed
        ),
        "project_browser_autonomous_next_step_launch_execution_launch_execution_attempted": bool(
            launch_execution_attempted
        ),
        "project_browser_autonomous_next_step_launch_execution_launch_execution_completed": bool(
            launch_execution_completed
        ),
        "project_browser_autonomous_next_step_launch_execution_launch_execution_failed": bool(
            launch_execution_failed
        ),
        "project_browser_autonomous_next_step_launch_execution_launch_execution_block_reason": (
            launch_execution_block_reason
        ),
        "project_browser_autonomous_next_step_launch_execution_launch_execution_source": (
            launch_execution_source
        ),
        "project_browser_autonomous_next_step_launch_execution_selected_launch_kind": (
            effective_selected_kind
        ),
        "project_browser_autonomous_next_step_launch_execution_selected_launch_action": (
            effective_selected_action
        ),
        "project_browser_autonomous_next_step_launch_execution_selected_launch_payload": (
            effective_selected_payload
        ),
        "project_browser_autonomous_next_step_launch_execution_non_selected_launches_noop": bool(
            non_selected_launches_noop
        ),
        "project_browser_autonomous_next_step_launch_execution_generated_prompt_reentry_launch_executed": bool(
            generated_prompt_reentry_launch_executed
        ),
        "project_browser_autonomous_next_step_launch_execution_rollback_execution_launch_executed": bool(
            rollback_execution_launch_executed
        ),
        "project_browser_autonomous_next_step_launch_execution_commit_execution_launch_executed": bool(
            commit_execution_launch_executed
        ),
        "project_browser_autonomous_next_step_launch_execution_manual_stop_launch_executed": bool(
            manual_stop_launch_executed
        ),
        "project_browser_autonomous_next_step_launch_execution_delegated_existing_path": bool(
            delegated_existing_path
        ),
        "project_browser_autonomous_next_step_launch_execution_delegated_existing_path_kind": (
            delegated_existing_path_kind
        ),
        "project_browser_autonomous_next_step_launch_execution_delegated_existing_status": (
            delegated_existing_status
        ),
        "project_browser_autonomous_next_step_launch_execution_delegated_existing_next_action": (
            delegated_existing_next_action
        ),
        "project_browser_autonomous_next_step_launch_execution_generated_prompt_reentry_result_status": (
            generated_prompt_reentry_result_status
        ),
        "project_browser_autonomous_next_step_launch_execution_rollback_execution_result_status": (
            rollback_execution_result_status
        ),
        "project_browser_autonomous_next_step_launch_execution_commit_execution_result_status": (
            commit_execution_result_status
        ),
        "project_browser_autonomous_next_step_launch_execution_result_class": result_class,
        "project_browser_autonomous_next_step_launch_execution_next_step_launch_result_ready_for_assimilation": True,
        "project_browser_autonomous_next_step_launch_execution_next_step_launch_result_assimilation_source": (
            "prompt205_next_step_launch_execution"
        ),
        "project_browser_autonomous_next_step_launch_execution_next_step_launch_result_next_stage": (
            "next_step_launch_result_assimilation"
        ),
        "project_browser_autonomous_next_step_launch_execution_should_invoke_codex": bool(
            out_should_invoke_codex
        ),
        "project_browser_autonomous_next_step_launch_execution_should_execute_rollback": bool(
            out_should_execute_rollback
        ),
        "project_browser_autonomous_next_step_launch_execution_should_execute_commit": bool(
            out_should_execute_commit
        ),
        "project_browser_autonomous_next_step_launch_execution_should_push": bool(
            out_should_push
        ),
        "project_browser_autonomous_next_step_launch_execution_manual_review_required": bool(
            out_manual_review_required
        ),
        "project_browser_autonomous_next_step_launch_execution_should_stop": bool(
            out_should_stop
        ),
        "project_browser_autonomous_next_step_launch_execution_stop_reason": out_stop_reason,
        "project_browser_autonomous_next_step_launch_execution_next_action": out_next_action,
        "project_browser_autonomous_next_step_launch_execution_runtime_posture": runtime_posture,
        "project_browser_autonomous_next_step_launch_execution_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_launch_contract_status,
                    normalized_launch_contract_block_reason,
                    normalized_launch_contract_source,
                    normalized_launch_contract_kind,
                    normalized_launch_contract_action,
                    normalized_selected_launch_kind,
                    normalized_selected_launch_action,
                    normalized_launch_stop_reason,
                    normalized_launch_next_action,
                    normalized_bounded_local_loop_contract_status,
                    normalized_selected_lane_result_assimilation_status,
                    normalized_generated_prompt_reentry_readiness_status,
                    normalized_generated_prompt_reentry_routing_status,
                    normalized_codex_reentry_invocation_status,
                    normalized_codex_reentry_invocation_next_action,
                    normalized_rollback_readiness_status,
                    normalized_rollback_execution_status,
                    normalized_rollback_execution_next_action,
                    normalized_commit_tag_readiness_status,
                    normalized_commit_tag_execution_status,
                    normalized_commit_tag_execution_next_action,
                    "launch_contract_not_available" if not bool(launch_contract_available) else "",
                    "selected_payload_missing"
                    if selected_kind_is_supported and not bool(effective_selected_payload)
                    else "",
                ]
            )
        ),
    }

def _build_project_browser_autonomous_chatgpt_browser_runtime_enablement_state(
    *,
    dry_run: bool,
    existing_send_path_available: bool,
    browser_queue_status: str,
    browser_queue_mode: str,
    browser_queue_block_reason: str,
    browser_executor_interface_status: str,
    browser_executor_mode: str,
    browser_executor_block_reason: str,
    browser_execution_handoff_status: str,
    browser_execution_block_reason: str,
    browser_launch_preflight_mode: str,
    browser_runtime_block_reason: str,
    browser_playwright_import_posture: str,
    browser_session_config_status: str,
    browser_session_mode: str,
    browser_selector_contract_status: str,
    browser_selector_contract_targets: Any,
) -> dict[str, Any]:
    current_transport_mode = "dry-run" if dry_run else "live"
    required_transport_mode = "live"
    normalized_queue_status = _normalize_text(browser_queue_status, default="")
    normalized_queue_mode = _normalize_text(browser_queue_mode, default="")
    normalized_queue_block_reason = _normalize_text(browser_queue_block_reason, default="")
    normalized_executor_interface_status = _normalize_text(
        browser_executor_interface_status,
        default="",
    )
    normalized_executor_mode = _normalize_text(browser_executor_mode, default="")
    normalized_executor_block_reason = _normalize_text(
        browser_executor_block_reason,
        default="",
    )
    normalized_execution_handoff_status = _normalize_text(
        browser_execution_handoff_status,
        default="",
    )
    normalized_execution_block_reason = _normalize_text(
        browser_execution_block_reason,
        default="",
    )
    normalized_preflight_mode = _normalize_text(browser_launch_preflight_mode, default="")
    normalized_runtime_block_reason = _normalize_text(
        browser_runtime_block_reason,
        default="",
    )
    normalized_playwright_import_posture = _normalize_text(
        browser_playwright_import_posture,
        default="",
    )
    normalized_session_config_status = _normalize_text(
        browser_session_config_status,
        default="",
    )
    normalized_session_mode = _normalize_text(browser_session_mode, default="")
    normalized_selector_contract_status = _normalize_text(
        browser_selector_contract_status,
        default="",
    )
    selector_contract_targets = (
        list(browser_selector_contract_targets)
        if isinstance(browser_selector_contract_targets, list)
        else []
    )
    required_selector_keys = [
        "chat_input",
        "send_trigger",
        "latest_assistant_response",
        "message_ready",
        "loading_state",
    ]
    selector_key_availability: dict[str, bool] = {
        key: False for key in required_selector_keys
    }
    for entry in selector_contract_targets:
        if not isinstance(entry, Mapping):
            continue
        target = _normalize_text(entry.get("selector_target"), default="")
        if target not in selector_key_availability:
            continue
        selector_key_availability[target] = bool(
            bool(entry.get("primary_selector_available", False))
            or bool(entry.get("secondary_selector_available", False))
            or bool(entry.get("fallback_selector_available", False))
        )
    missing_selector_keys = [
        key for key in required_selector_keys if not selector_key_availability.get(key, False)
    ]
    selector_contract_keys_available = bool(
        not missing_selector_keys and bool(selector_key_availability)
    )

    environment_prerequisites: list[str] = [
        "playwright_runtime_available",
        "browser_session_user_data_dir_configured",
        "chatgpt_login_session_active",
        "selector_contract_ready",
    ]
    browser_session_required = True
    browser_runtime_available = bool(
        not dry_run
        and normalized_queue_mode != "dry_run_contract_only"
        and normalized_executor_mode != "dry_run_contract_only"
        and normalized_preflight_mode == "launch_allowed_later"
    )

    operator_command_suggestion = (
        "python scripts/run_planned_execution.py "
        "--artifacts-dir /tmp/prompt248_artifacts "
        "--out-dir /tmp/prompt262b_out/prompt262b-live-run "
        "--job-id prompt262b-live-run "
        "--retry-context /tmp/prompt258_out/retry_context_store.json "
        "--transport-mode live "
        "--enable-live-transport "
        "--repo-path /home/rai/codex-local-runner"
    )

    selector_contract_missing = bool(
        bool(missing_selector_keys)
        or (
            normalized_execution_block_reason == "selector_contract_missing"
            and not selector_contract_keys_available
        )
        or (
            normalized_selector_contract_status == "unavailable"
            and not selector_contract_keys_available
        )
    )
    browser_execution_handoff_missing = bool(
        normalized_execution_handoff_status in {"inactive", "unavailable"}
    )
    browser_executor_not_callable = bool(
        normalized_executor_mode == "none"
        or normalized_executor_interface_status in {"blocked", "unavailable"}
        or normalized_executor_block_reason in {"prerequisite_not_ready", "handoff_unavailable"}
    )
    session_config_missing = bool(
        normalized_session_config_status in {"blocked", "unavailable"}
    )
    browser_user_data_dir_missing = bool(
        normalized_session_mode == "none"
    )
    chatgpt_login_session_missing = bool(
        session_config_missing
        and normalized_session_mode in {"existing_profile", "persistent_context", "explicit_user_data_dir"}
    )
    launch_preflight_blocked = bool(normalized_preflight_mode == "blocked")
    live_transport_not_propagated_to_queue = bool(
        not dry_run
        and normalized_queue_mode == "none"
        and normalized_queue_status in {"blocked", "unavailable"}
        and browser_executor_not_callable
    )
    queue_blocked_generic = bool(
        normalized_queue_status == "blocked" or normalized_runtime_block_reason == "command_queue_blocked"
    )

    detected_blockers: list[str] = []
    if selector_contract_missing:
        detected_blockers.append("selector_contract_not_ready")
    if browser_user_data_dir_missing:
        detected_blockers.append("browser_user_data_dir_missing")
    if chatgpt_login_session_missing:
        detected_blockers.append("chatgpt_login_session_missing")
    if browser_executor_not_callable:
        detected_blockers.append("browser_executor_mode_none")
    if launch_preflight_blocked:
        detected_blockers.append("launch_preflight_blocked")
    if normalized_playwright_import_posture == "import_unavailable":
        detected_blockers.append("playwright_runtime_missing")
    if browser_execution_handoff_missing or not existing_send_path_available:
        detected_blockers.append("missing_existing_invocation_inputs")
    if live_transport_not_propagated_to_queue:
        detected_blockers.append("missing_existing_invocation_inputs")
    # Keep generic queue blocker only as fallback when no deeper prerequisite is discoverable.
    if queue_blocked_generic and not detected_blockers:
        detected_blockers.append("command_queue_blocked")

    blocker_priority = [
        "transport_mode_live_not_supported",
        "live_transport_flag_missing",
        "selector_contract_not_ready",
        "browser_user_data_dir_missing",
        "chatgpt_login_session_missing",
        "browser_executor_mode_none",
        "launch_preflight_blocked",
        "playwright_runtime_missing",
        "missing_existing_invocation_inputs",
        "codex_environment_cannot_execute_browser_runtime",
        "command_queue_blocked",
    ]
    highest_priority_blocker = "none"
    for candidate in blocker_priority:
        if candidate in detected_blockers:
            highest_priority_blocker = candidate
            break
    secondary_blockers = [item for item in detected_blockers if item != highest_priority_blocker]

    operator_action_map = {
        "command_queue_blocked": (
            "Unblock browser command queue by restoring selector contract + session prerequisites, then run: "
            f"{operator_command_suggestion}"
        ),
        "browser_executor_mode_none": (
            "Restore browser execution handoff prerequisites so executor mode is callable, then run: "
            f"{operator_command_suggestion}"
        ),
        "launch_preflight_blocked": (
            "Resolve launch preflight prerequisites (Playwright import, session config, selector contract), then run: "
            f"{operator_command_suggestion}"
        ),
        "playwright_runtime_missing": (
            "Install/enable Playwright runtime in this environment, then run: "
            f"{operator_command_suggestion}"
        ),
        "browser_user_data_dir_missing": (
            "Set project_browser_session_user_data_dir to a valid persistent browser profile with ChatGPT access, then run: "
            f"{operator_command_suggestion}"
        ),
        "chatgpt_login_session_missing": (
            "Log in to ChatGPT using the configured persistent browser profile, then run: "
            f"{operator_command_suggestion}"
        ),
        "selector_contract_not_ready": (
            "Configure existing selector contract path (project_browser_selector_contract or project_browser_selector_<target>_* fields) with required keys "
            f"{','.join(missing_selector_keys if missing_selector_keys else required_selector_keys)}, then run: "
            f"{operator_command_suggestion}"
        ),
        "missing_existing_invocation_inputs": (
            "Populate missing browser invocation inputs for run_one_browser_command, then run: "
            f"{operator_command_suggestion}"
        ),
        "codex_environment_cannot_execute_browser_runtime": (
            "Run the live command in an environment that can launch Playwright with the configured profile: "
            f"{operator_command_suggestion}"
        ),
        "transport_mode_live_not_supported": (
            "Use a runner build that supports --transport-mode live and rerun: "
            f"{operator_command_suggestion}"
        ),
        "live_transport_flag_missing": (
            "Run with --enable-live-transport explicitly set: "
            f"{operator_command_suggestion}"
        ),
    }
    operator_action = operator_action_map.get(
        highest_priority_blocker,
        (
            "Run the stored live operator command after satisfying runtime prerequisites: "
            f"{operator_command_suggestion}"
        ),
    )

    if dry_run:
        status = "chatgpt_browser_runtime_enablement_blocked_dry_run"
        next_action = "rerun_with_browser_runtime_enabled"
    elif existing_send_path_available and browser_runtime_available:
        status = "chatgpt_browser_runtime_enablement_ready"
        next_action = "invoke_one_bounded_browser_send"
    else:
        status = "chatgpt_browser_runtime_enablement_blocked_missing_prerequisite"
        next_action = "resolve_browser_runtime_prerequisites"

    return {
        "project_browser_autonomous_chatgpt_browser_runtime_enablement_status": status,
        "project_browser_autonomous_chatgpt_browser_runtime_enablement_source": (
            "prompt262b_chatgpt_browser_runtime_enablement"
        ),
        "project_browser_autonomous_chatgpt_browser_runtime_enablement_current_transport_mode": (
            current_transport_mode
        ),
        "project_browser_autonomous_chatgpt_browser_runtime_enablement_required_transport_mode": (
            required_transport_mode
        ),
        "project_browser_autonomous_chatgpt_browser_runtime_enablement_browser_runtime_available": bool(
            browser_runtime_available
        ),
        "project_browser_autonomous_chatgpt_browser_runtime_enablement_browser_session_required": bool(
            browser_session_required
        ),
        "project_browser_autonomous_chatgpt_browser_runtime_enablement_existing_send_path_available": bool(
            existing_send_path_available
        ),
        "project_browser_autonomous_chatgpt_browser_runtime_enablement_operator_command_suggestion": (
            operator_command_suggestion
        ),
        "project_browser_autonomous_chatgpt_browser_runtime_enablement_environment_prerequisites": (
            environment_prerequisites
        ),
        "project_browser_autonomous_chatgpt_browser_runtime_enablement_next_action": (
            next_action
        ),
        "project_browser_autonomous_chatgpt_browser_runtime_enablement_runtime_block_reason": (
            normalized_runtime_block_reason
        ),
        "project_browser_autonomous_chatgpt_browser_runtime_enablement_queue_mode": (
            normalized_queue_mode
        ),
        "project_browser_autonomous_chatgpt_browser_runtime_enablement_executor_mode": (
            normalized_executor_mode
        ),
        "project_browser_autonomous_chatgpt_browser_runtime_enablement_launch_preflight_mode": (
            normalized_preflight_mode
        ),
        "project_browser_autonomous_chatgpt_browser_runtime_enablement_highest_priority_blocker": (
            highest_priority_blocker
        ),
        "project_browser_autonomous_chatgpt_browser_runtime_enablement_secondary_blockers": (
            _normalize_string_list(secondary_blockers)
        ),
        "project_browser_autonomous_chatgpt_browser_runtime_enablement_operator_action": (
            operator_action
        ),
        "project_browser_autonomous_chatgpt_browser_runtime_enablement_selector_contract_required_keys": (
            _normalize_string_list(required_selector_keys)
        ),
        "project_browser_autonomous_chatgpt_browser_runtime_enablement_selector_contract_missing_keys": (
            _normalize_string_list(missing_selector_keys)
        ),
        "project_browser_autonomous_chatgpt_browser_runtime_enablement_selector_contract_keys_available": bool(
            selector_contract_keys_available
        ),
    }

def _build_project_browser_launch_runtime_state(
    *,
    browser_task_status: str,
    browser_command_queue_status: str,
    browser_command_type: str,
    browser_prompt_payload_status: str,
    browser_prompt_payload: Mapping[str, Any] | None,
    browser_queue_handoff_payload: Mapping[str, Any] | None,
    browser_launch_preflight_status: str,
    browser_launch_preflight_mode: str,
    browser_playwright_import_posture: str,
    browser_session_config_status: str,
    browser_session_mode: str,
    browser_selector_contract_status: str,
    browser_ui_recovery_decision_status: str,
    browser_recovery_candidate: str,
    browser_recovery_reason: str,
    browser_retry_count_posture: str,
    browser_handoff_dependency_posture: str,
    browser_handoff_compile_status: str,
    browser_handoff_payload_posture: str,
    dry_run: bool,
    prior_browser_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    task_status = _normalize_text(browser_task_status, default="inactive")
    queue_status = _normalize_text(browser_command_queue_status, default="insufficient_truth")
    command_type = _normalize_text(browser_command_type, default="none")
    prompt_payload_status = _normalize_text(
        browser_prompt_payload_status,
        default="insufficient_truth",
    )
    prompt_payload = (
        dict(browser_prompt_payload)
        if isinstance(browser_prompt_payload, Mapping)
        else {}
    )
    queue_handoff_payload = (
        dict(browser_queue_handoff_payload)
        if isinstance(browser_queue_handoff_payload, Mapping)
        else {}
    )
    preflight_status = _normalize_text(
        browser_launch_preflight_status,
        default="insufficient_truth",
    )
    preflight_mode = _normalize_text(
        browser_launch_preflight_mode,
        default="blocked",
    )
    import_posture = _normalize_text(
        browser_playwright_import_posture,
        default="insufficient_truth",
    )
    session_config_status = _normalize_text(
        browser_session_config_status,
        default="insufficient_truth",
    )
    session_mode = _normalize_text(browser_session_mode, default="insufficient_truth")
    selector_contract_status = _normalize_text(
        browser_selector_contract_status,
        default="insufficient_truth",
    )
    ui_recovery_decision_status = _normalize_text(
        browser_ui_recovery_decision_status,
        default="insufficient_truth",
    )
    recovery_candidate = _normalize_text(browser_recovery_candidate, default="none")
    recovery_reason = _normalize_text(
        browser_recovery_reason,
        default="insufficient_truth",
    )
    retry_count_posture = _normalize_text(
        browser_retry_count_posture,
        default="insufficient_truth",
    )
    handoff_dependency_posture = _normalize_text(
        browser_handoff_dependency_posture,
        default="insufficient_truth",
    )
    handoff_compile_status = _normalize_text(
        browser_handoff_compile_status,
        default="insufficient_truth",
    )
    handoff_payload_posture = _normalize_text(
        browser_handoff_payload_posture,
        default="insufficient_truth",
    )
    prior = dict(prior_browser_state or {})

    runtime_posture_tokens = [
        "no_prompt_send",
        "no_send_click",
        "no_response_wait",
        "no_response_read",
        "no_dom_deep_read",
        "no_retry_execution",
        "no_reload_execution",
        "no_new_chat_execution",
        "no_login_recovery",
        "no_executor_loop",
    ]

    launch_status = "insufficient_truth"
    context_status = "insufficient_truth"
    page_open_status = "insufficient_truth"
    chatgpt_page_status = "insufficient_truth"
    login_interruption_status = "insufficient_truth"
    launch_block_reason = "insufficient_truth"
    launch_receipt_status = "insufficient_truth"
    launch_receipt_kind = "none"
    attempted = False
    selector_probe_state: dict[str, Any] | None = None
    prompt_fill_state: dict[str, Any] | None = None
    prompt_send_state: dict[str, Any] | None = None
    response_wait_read_state: dict[str, Any] | None = None
    response_parse_state: dict[str, Any] | None = None
    recovery_state: dict[str, Any] | None = None

    if queue_status == "inactive" or preflight_status == "inactive":
        launch_status = "inactive"
        context_status = "inactive"
        page_open_status = "inactive"
        chatgpt_page_status = "inactive"
        login_interruption_status = "not_checked"
        launch_block_reason = "preflight_inactive"
        launch_receipt_status = "not_created"
        launch_receipt_kind = "none"
    elif queue_status == "blocked" or preflight_status == "blocked":
        launch_status = "blocked"
        context_status = "blocked"
        page_open_status = "blocked"
        chatgpt_page_status = "blocked"
        login_interruption_status = "not_checked"
        launch_block_reason = "preflight_blocked"
        launch_receipt_status = "blocked"
        launch_receipt_kind = "blocked_launch_receipt"
    elif queue_status == "unavailable" or preflight_status == "unavailable":
        launch_status = "blocked"
        context_status = "blocked"
        page_open_status = "blocked"
        chatgpt_page_status = "unavailable"
        login_interruption_status = "not_checked"
        launch_block_reason = "preflight_unavailable"
        launch_receipt_status = "unavailable"
        launch_receipt_kind = "blocked_launch_receipt"
    elif queue_status == "insufficient_truth" or preflight_status == "insufficient_truth":
        launch_status = "insufficient_truth"
        context_status = "insufficient_truth"
        page_open_status = "insufficient_truth"
        chatgpt_page_status = "insufficient_truth"
        login_interruption_status = "insufficient_truth"
        launch_block_reason = "insufficient_truth"
        launch_receipt_status = "insufficient_truth"
        launch_receipt_kind = "none"
    elif preflight_status != "ready":
        launch_status = "blocked"
        context_status = "blocked"
        page_open_status = "blocked"
        chatgpt_page_status = "blocked"
        login_interruption_status = "not_checked"
        launch_block_reason = "preflight_not_ready"
        launch_receipt_status = "blocked"
        launch_receipt_kind = "blocked_launch_receipt"
    elif command_type not in _PROJECT_BROWSER_COMMAND_TYPES - {"none"}:
        launch_status = "blocked"
        context_status = "blocked"
        page_open_status = "blocked"
        chatgpt_page_status = "blocked"
        login_interruption_status = "not_checked"
        launch_block_reason = "unsupported_command_type"
        launch_receipt_status = "blocked"
        launch_receipt_kind = "blocked_launch_receipt"
    elif preflight_mode == "blocked":
        launch_status = "blocked"
        context_status = "blocked"
        page_open_status = "blocked"
        chatgpt_page_status = "blocked"
        login_interruption_status = "not_checked"
        launch_block_reason = "preflight_blocked"
        launch_receipt_status = "blocked"
        launch_receipt_kind = "blocked_launch_receipt"
    elif session_config_status != "configured" or session_mode not in {
        "existing_profile",
        "persistent_context",
        "explicit_user_data_dir",
    }:
        launch_status = "blocked"
        context_status = "blocked"
        page_open_status = "blocked"
        chatgpt_page_status = "blocked"
        login_interruption_status = "not_checked"
        launch_block_reason = (
            "insufficient_truth"
            if session_config_status == "insufficient_truth"
            or session_mode == "insufficient_truth"
            else "session_config_missing"
        )
        launch_receipt_status = (
            "insufficient_truth"
            if launch_block_reason == "insufficient_truth"
            else "blocked"
        )
        launch_receipt_kind = (
            "none" if launch_receipt_status == "insufficient_truth" else "blocked_launch_receipt"
        )
    elif dry_run:
        launch_status = "not_attempted"
        context_status = "not_attempted"
        page_open_status = "not_attempted"
        chatgpt_page_status = "not_attempted"
        login_interruption_status = "not_checked"
        launch_block_reason = "none"
        launch_receipt_status = "not_created"
        launch_receipt_kind = "none"
    else:
        user_data_dir = _normalize_text(
            prior.get("project_browser_session_user_data_dir"),
            default="",
        )
        if not user_data_dir:
            launch_status = "blocked"
            context_status = "blocked"
            page_open_status = "blocked"
            chatgpt_page_status = "blocked"
            login_interruption_status = "not_checked"
            launch_block_reason = "session_config_missing"
            launch_receipt_status = "blocked"
            launch_receipt_kind = "blocked_launch_receipt"
        elif import_posture == "import_unavailable":
            launch_status = "blocked"
            context_status = "blocked"
            page_open_status = "blocked"
            chatgpt_page_status = "blocked"
            login_interruption_status = "not_checked"
            launch_block_reason = "playwright_unavailable"
            launch_receipt_status = "blocked"
            launch_receipt_kind = "blocked_launch_receipt"
        elif import_posture == "insufficient_truth":
            launch_status = "insufficient_truth"
            context_status = "insufficient_truth"
            page_open_status = "insufficient_truth"
            chatgpt_page_status = "insufficient_truth"
            login_interruption_status = "insufficient_truth"
            launch_block_reason = "insufficient_truth"
            launch_receipt_status = "insufficient_truth"
            launch_receipt_kind = "none"
        else:
            attempted = True
            runtime_posture_tokens.append("launch_attempted")
            target_url = _resolve_project_browser_chatgpt_url(prior)
            timeout_ms = _as_non_negative_int(
                prior.get("project_browser_launch_timeout_ms"),
                default=20000,
            )
            if timeout_ms <= 0:
                timeout_ms = 20000
            headless = bool(prior.get("project_browser_launch_headless", True))

            browser = None
            context = None
            try:
                from playwright.sync_api import sync_playwright  # type: ignore
            except Exception:
                launch_status = "blocked"
                context_status = "blocked"
                page_open_status = "blocked"
                chatgpt_page_status = "blocked"
                login_interruption_status = "not_checked"
                launch_block_reason = "playwright_unavailable"
                launch_receipt_status = "blocked"
                launch_receipt_kind = "blocked_launch_receipt"
            else:
                try:
                    with sync_playwright() as p:
                        context = p.chromium.launch_persistent_context(
                            user_data_dir=user_data_dir,
                            headless=headless,
                        )
                        launch_status = "launched"
                        context_status = "opened"
                        runtime_posture_tokens.append("page_open_attempted")
                        page = context.new_page()
                        page.goto(
                            target_url,
                            wait_until="domcontentloaded",
                            timeout=timeout_ms,
                        )
                        page_open_status = "opened"
                        page_url = _normalize_text(getattr(page, "url", ""), default="")
                        if _is_project_browser_login_interruption_url(page_url):
                            chatgpt_page_status = "login_interruption"
                            login_interruption_status = "detected"
                            launch_block_reason = "login_interruption"
                            launch_receipt_status = "login_pause_required"
                            launch_receipt_kind = "login_interruption_receipt"
                        elif page_url.startswith("https://chatgpt.com") or page_url.startswith(
                            "https://chat.openai.com"
                        ):
                            chatgpt_page_status = "opened"
                            login_interruption_status = "not_detected"
                            launch_block_reason = "none"
                            launch_receipt_status = "launch_opened"
                            launch_receipt_kind = "browser_launch_page_open_receipt"
                        else:
                            chatgpt_page_status = "unavailable"
                            login_interruption_status = "insufficient_truth"
                            launch_block_reason = "page_open_failed"
                            launch_receipt_status = "failed"
                            launch_receipt_kind = "failed_launch_receipt"
                        selector_probe_state = _build_project_browser_selector_probe_state(
                            browser_launch_status=launch_status,
                            browser_chatgpt_page_status=chatgpt_page_status,
                            browser_login_interruption_status=login_interruption_status,
                            browser_launch_receipt_status=launch_receipt_status,
                            browser_launch_block_reason=launch_block_reason,
                            browser_command_type=command_type,
                            browser_selector_contract_status=selector_contract_status,
                            prior_browser_state=prior,
                            page=page if chatgpt_page_status == "opened" else None,
                        )
                        prompt_fill_state = _build_project_browser_prompt_fill_state(
                            browser_task_status=task_status,
                            browser_command_type=command_type,
                            browser_prompt_payload_status=prompt_payload_status,
                            browser_launch_status=launch_status,
                            browser_chatgpt_page_status=chatgpt_page_status,
                            browser_login_interruption_status=login_interruption_status,
                            browser_dom_readiness_status=_normalize_text(
                                selector_probe_state.get("project_browser_dom_readiness_status"),
                                default="insufficient_truth",
                            ),
                            browser_chat_input_target_status=_normalize_text(
                                dict(
                                    selector_probe_state.get(
                                        "project_browser_selector_target_status",
                                        {},
                                    )
                                ).get("chat_input"),
                                default="insufficient_truth",
                            ),
                            prior_browser_state=prior,
                            browser_prompt_payload=prompt_payload,
                            browser_queue_handoff_payload=queue_handoff_payload,
                            page=page if chatgpt_page_status == "opened" else None,
                        )
                        prompt_send_state = _build_project_browser_prompt_send_state(
                            browser_command_type=command_type,
                            browser_launch_status=launch_status,
                            browser_chatgpt_page_status=chatgpt_page_status,
                            browser_login_interruption_status=login_interruption_status,
                            browser_dom_readiness_status=_normalize_text(
                                selector_probe_state.get("project_browser_dom_readiness_status"),
                                default="insufficient_truth",
                            ),
                            browser_prompt_fill_status=_normalize_text(
                                prompt_fill_state.get("project_browser_prompt_fill_status"),
                                default="insufficient_truth",
                            ),
                            browser_send_trigger_target_status=_normalize_text(
                                dict(
                                    selector_probe_state.get(
                                        "project_browser_selector_target_status",
                                        {},
                                    )
                                ).get("send_trigger"),
                                default="insufficient_truth",
                            ),
                            prior_browser_state=prior,
                            page=page if chatgpt_page_status == "opened" else None,
                        )
                        response_wait_read_state = _build_project_browser_response_wait_read_state(
                            browser_command_type=command_type,
                            browser_launch_status=launch_status,
                            browser_chatgpt_page_status=chatgpt_page_status,
                            browser_login_interruption_status=login_interruption_status,
                            browser_prompt_send_status=_normalize_text(
                                prompt_send_state.get("project_browser_prompt_send_status"),
                                default="insufficient_truth",
                            ),
                            browser_latest_assistant_response_target_status=_normalize_text(
                                dict(
                                    selector_probe_state.get(
                                        "project_browser_selector_target_status",
                                        {},
                                    )
                                ).get("latest_assistant_response"),
                                default="insufficient_truth",
                            ),
                            browser_message_ready_target_status=_normalize_text(
                                dict(
                                    selector_probe_state.get(
                                        "project_browser_selector_target_status",
                                        {},
                                    )
                                ).get("message_ready"),
                                default="insufficient_truth",
                            ),
                            browser_loading_state_target_status=_normalize_text(
                                dict(
                                    selector_probe_state.get(
                                        "project_browser_selector_target_status",
                                        {},
                                    )
                                ).get("loading_state"),
                                default="insufficient_truth",
                            ),
                            prior_browser_state=prior,
                            page=page if chatgpt_page_status == "opened" else None,
                        )
                        response_parse_state = _build_project_browser_response_parse_state(
                            browser_command_type=command_type,
                            browser_chatgpt_page_status=chatgpt_page_status,
                            browser_login_interruption_status=login_interruption_status,
                            browser_response_wait_status=_normalize_text(
                                response_wait_read_state.get(
                                    "project_browser_response_wait_status"
                                ),
                                default="insufficient_truth",
                            ),
                            browser_response_read_status=_normalize_text(
                                response_wait_read_state.get(
                                    "project_browser_response_read_status"
                                ),
                                default="insufficient_truth",
                            ),
                            browser_response_text_status=_normalize_text(
                                response_wait_read_state.get(
                                    "project_browser_response_text_status"
                                ),
                                default="insufficient_truth",
                            ),
                            browser_response_text=_normalize_text(
                                response_wait_read_state.get("project_browser_response_text"),
                                default="",
                            ),
                            browser_response_text_truncated=bool(
                                response_wait_read_state.get(
                                    "project_browser_response_text_truncated",
                                    False,
                                )
                            ),
                            browser_prompt_schema_required_json_ref=_normalize_text(
                                prompt_payload.get("project_browser_prompt_schema_required_json_ref"),
                                default=_PROJECT_BROWSER_TASK_SCHEMA_REF,
                            ),
                        )
                        recovery_state = _build_project_browser_recovery_runtime_state(
                            browser_command_type=command_type,
                            browser_chatgpt_page_status=chatgpt_page_status,
                            browser_login_interruption_status=login_interruption_status,
                            browser_response_wait_status=_normalize_text(
                                response_wait_read_state.get(
                                    "project_browser_response_wait_status"
                                ),
                                default="insufficient_truth",
                            ),
                            browser_response_wait_block_reason=_normalize_text(
                                response_wait_read_state.get(
                                    "project_browser_response_wait_block_reason"
                                ),
                                default="insufficient_truth",
                            ),
                            browser_response_json_parse_status=_normalize_text(
                                response_parse_state.get(
                                    "project_browser_response_json_parse_status"
                                ),
                                default="insufficient_truth",
                            ),
                            browser_execution_receipt_status=_normalize_text(
                                response_parse_state.get(
                                    "project_browser_execution_receipt_status"
                                ),
                                default="insufficient_truth",
                            ),
                            browser_response_parse_block_reason=_normalize_text(
                                response_parse_state.get(
                                    "project_browser_response_parse_block_reason"
                                ),
                                default="insufficient_truth",
                            ),
                            browser_ui_recovery_decision_status=ui_recovery_decision_status,
                            browser_recovery_candidate=recovery_candidate,
                            browser_recovery_reason=recovery_reason,
                            browser_retry_count_posture=retry_count_posture,
                            browser_handoff_dependency_posture=handoff_dependency_posture,
                            browser_handoff_compile_status=handoff_compile_status,
                            browser_handoff_payload_posture=handoff_payload_posture,
                            prior_browser_state=prior,
                            page=page if chatgpt_page_status == "opened" else None,
                        )
                except Exception:
                    launch_status = "failed" if launch_status == "launched" else "failed"
                    context_status = (
                        "failed"
                        if context_status in {"opened", "not_attempted"}
                        else context_status
                    )
                    page_open_status = "failed"
                    chatgpt_page_status = "failed"
                    login_interruption_status = "not_checked"
                    launch_block_reason = (
                        "page_open_failed" if context_status == "failed" else "launch_failed"
                    )
                    launch_receipt_status = "failed"
                    launch_receipt_kind = "failed_launch_receipt"
                finally:
                    try:
                        if context is not None:
                            context.close()
                    except Exception:
                        pass
                    try:
                        if browser is not None:
                            browser.close()
                    except Exception:
                        pass

    if selector_probe_state is None:
        selector_probe_state = _build_project_browser_selector_probe_state(
            browser_launch_status=launch_status,
            browser_chatgpt_page_status=chatgpt_page_status,
            browser_login_interruption_status=login_interruption_status,
            browser_launch_receipt_status=launch_receipt_status,
            browser_launch_block_reason=launch_block_reason,
            browser_command_type=command_type,
            browser_selector_contract_status=selector_contract_status,
            prior_browser_state=prior,
            page=None,
        )
    if prompt_fill_state is None:
        prompt_fill_state = _build_project_browser_prompt_fill_state(
            browser_task_status=task_status,
            browser_command_type=command_type,
            browser_prompt_payload_status=prompt_payload_status,
            browser_launch_status=launch_status,
            browser_chatgpt_page_status=chatgpt_page_status,
            browser_login_interruption_status=login_interruption_status,
            browser_dom_readiness_status=_normalize_text(
                selector_probe_state.get("project_browser_dom_readiness_status"),
                default="insufficient_truth",
            ),
            browser_chat_input_target_status=_normalize_text(
                dict(
                    selector_probe_state.get(
                        "project_browser_selector_target_status",
                        {},
                    )
                ).get("chat_input"),
                default="insufficient_truth",
            ),
            prior_browser_state=prior,
            browser_prompt_payload=prompt_payload,
            browser_queue_handoff_payload=queue_handoff_payload,
            page=None,
        )
    if prompt_send_state is None:
        prompt_send_state = _build_project_browser_prompt_send_state(
            browser_command_type=command_type,
            browser_launch_status=launch_status,
            browser_chatgpt_page_status=chatgpt_page_status,
            browser_login_interruption_status=login_interruption_status,
            browser_dom_readiness_status=_normalize_text(
                selector_probe_state.get("project_browser_dom_readiness_status"),
                default="insufficient_truth",
            ),
            browser_prompt_fill_status=_normalize_text(
                prompt_fill_state.get("project_browser_prompt_fill_status"),
                default="insufficient_truth",
            ),
            browser_send_trigger_target_status=_normalize_text(
                dict(
                    selector_probe_state.get(
                        "project_browser_selector_target_status",
                        {},
                    )
                ).get("send_trigger"),
                default="insufficient_truth",
            ),
            prior_browser_state=prior,
            page=None,
        )
    if response_wait_read_state is None:
        response_wait_read_state = _build_project_browser_response_wait_read_state(
            browser_command_type=command_type,
            browser_launch_status=launch_status,
            browser_chatgpt_page_status=chatgpt_page_status,
            browser_login_interruption_status=login_interruption_status,
            browser_prompt_send_status=_normalize_text(
                prompt_send_state.get("project_browser_prompt_send_status"),
                default="insufficient_truth",
            ),
            browser_latest_assistant_response_target_status=_normalize_text(
                dict(
                    selector_probe_state.get(
                        "project_browser_selector_target_status",
                        {},
                    )
                ).get("latest_assistant_response"),
                default="insufficient_truth",
            ),
            browser_message_ready_target_status=_normalize_text(
                dict(
                    selector_probe_state.get(
                        "project_browser_selector_target_status",
                        {},
                    )
                ).get("message_ready"),
                default="insufficient_truth",
            ),
            browser_loading_state_target_status=_normalize_text(
                dict(
                    selector_probe_state.get(
                        "project_browser_selector_target_status",
                        {},
                    )
                ).get("loading_state"),
                default="insufficient_truth",
            ),
            prior_browser_state=prior,
            page=None,
        )
    if response_parse_state is None:
        response_parse_state = _build_project_browser_response_parse_state(
            browser_command_type=command_type,
            browser_chatgpt_page_status=chatgpt_page_status,
            browser_login_interruption_status=login_interruption_status,
            browser_response_wait_status=_normalize_text(
                response_wait_read_state.get("project_browser_response_wait_status"),
                default="insufficient_truth",
            ),
            browser_response_read_status=_normalize_text(
                response_wait_read_state.get("project_browser_response_read_status"),
                default="insufficient_truth",
            ),
            browser_response_text_status=_normalize_text(
                response_wait_read_state.get("project_browser_response_text_status"),
                default="insufficient_truth",
            ),
            browser_response_text=_normalize_text(
                response_wait_read_state.get("project_browser_response_text"),
                default="",
            ),
            browser_response_text_truncated=bool(
                response_wait_read_state.get("project_browser_response_text_truncated", False)
            ),
            browser_prompt_schema_required_json_ref=_normalize_text(
                prompt_payload.get("project_browser_prompt_schema_required_json_ref"),
                default=_PROJECT_BROWSER_TASK_SCHEMA_REF,
            ),
        )
    if recovery_state is None:
        recovery_state = _build_project_browser_recovery_runtime_state(
            browser_command_type=command_type,
            browser_chatgpt_page_status=chatgpt_page_status,
            browser_login_interruption_status=login_interruption_status,
            browser_response_wait_status=_normalize_text(
                response_wait_read_state.get("project_browser_response_wait_status"),
                default="insufficient_truth",
            ),
            browser_response_wait_block_reason=_normalize_text(
                response_wait_read_state.get("project_browser_response_wait_block_reason"),
                default="insufficient_truth",
            ),
            browser_response_json_parse_status=_normalize_text(
                response_parse_state.get("project_browser_response_json_parse_status"),
                default="insufficient_truth",
            ),
            browser_execution_receipt_status=_normalize_text(
                response_parse_state.get("project_browser_execution_receipt_status"),
                default="insufficient_truth",
            ),
            browser_response_parse_block_reason=_normalize_text(
                response_parse_state.get("project_browser_response_parse_block_reason"),
                default="insufficient_truth",
            ),
            browser_ui_recovery_decision_status=ui_recovery_decision_status,
            browser_recovery_candidate=recovery_candidate,
            browser_recovery_reason=recovery_reason,
            browser_retry_count_posture=retry_count_posture,
            browser_handoff_dependency_posture=handoff_dependency_posture,
            browser_handoff_compile_status=handoff_compile_status,
            browser_handoff_payload_posture=handoff_payload_posture,
            prior_browser_state=prior,
            page=None,
        )

    if launch_status not in _PROJECT_BROWSER_LAUNCH_STATUSES:
        launch_status = "insufficient_truth"
    if context_status not in _PROJECT_BROWSER_CONTEXT_STATUSES:
        context_status = "insufficient_truth"
    if page_open_status not in _PROJECT_BROWSER_PAGE_OPEN_STATUSES:
        page_open_status = "insufficient_truth"
    if chatgpt_page_status not in _PROJECT_BROWSER_CHATGPT_PAGE_STATUSES:
        chatgpt_page_status = "insufficient_truth"
    if login_interruption_status not in _PROJECT_BROWSER_LOGIN_INTERRUPTION_STATUSES:
        login_interruption_status = "insufficient_truth"
    if launch_block_reason not in _PROJECT_BROWSER_LAUNCH_BLOCK_REASONS:
        launch_block_reason = "insufficient_truth"
    if launch_receipt_status not in _PROJECT_BROWSER_LAUNCH_RECEIPT_STATUSES_RUNTIME:
        launch_receipt_status = "insufficient_truth"
    if launch_receipt_kind not in _PROJECT_BROWSER_LAUNCH_RECEIPT_KINDS_RUNTIME:
        launch_receipt_kind = "none"
    selector_resolver_status = _normalize_text(
        selector_probe_state.get("project_browser_selector_resolver_status"),
        default="insufficient_truth",
    )
    if selector_resolver_status not in _PROJECT_BROWSER_SELECTOR_RESOLVER_STATUSES:
        selector_resolver_status = "insufficient_truth"
    selector_probe_status = _normalize_text(
        selector_probe_state.get("project_browser_selector_probe_status"),
        default="insufficient_truth",
    )
    if selector_probe_status not in _PROJECT_BROWSER_SELECTOR_PROBE_STATUSES:
        selector_probe_status = "insufficient_truth"
    dom_readiness_status = _normalize_text(
        selector_probe_state.get("project_browser_dom_readiness_status"),
        default="insufficient_truth",
    )
    if dom_readiness_status not in _PROJECT_BROWSER_DOM_READINESS_STATUSES:
        dom_readiness_status = "insufficient_truth"
    dom_probe_block_reason = _normalize_text(
        selector_probe_state.get("project_browser_dom_probe_block_reason"),
        default="insufficient_truth",
    )
    if dom_probe_block_reason not in _PROJECT_BROWSER_DOM_PROBE_BLOCK_REASONS:
        dom_probe_block_reason = "insufficient_truth"
    selector_probe_receipt_status = _normalize_text(
        selector_probe_state.get("project_browser_selector_probe_receipt_status"),
        default="insufficient_truth",
    )
    if (
        selector_probe_receipt_status
        not in _PROJECT_BROWSER_SELECTOR_PROBE_RECEIPT_STATUSES
    ):
        selector_probe_receipt_status = "insufficient_truth"
    selector_probe_receipt_kind = _normalize_text(
        selector_probe_state.get("project_browser_selector_probe_receipt_kind"),
        default="none",
    )
    if selector_probe_receipt_kind not in _PROJECT_BROWSER_SELECTOR_PROBE_RECEIPT_KINDS:
        selector_probe_receipt_kind = "none"
    target_status_map = (
        dict(selector_probe_state.get("project_browser_selector_target_status", {}))
        if isinstance(
            selector_probe_state.get("project_browser_selector_target_status"),
            Mapping,
        )
        else {}
    )
    normalized_target_status_map: dict[str, str] = {}
    for target in _PROJECT_BROWSER_SELECTOR_REQUIRED_PROBE_TARGETS:
        target_status = _normalize_text(
            target_status_map.get(target),
            default="insufficient_truth",
        )
        if target_status not in _PROJECT_BROWSER_SELECTOR_TARGET_STATUSES:
            target_status = "insufficient_truth"
        normalized_target_status_map[target] = target_status

    runtime_posture = [
        token
        for token in runtime_posture_tokens
        if token in _PROJECT_BROWSER_LAUNCH_RUNTIME_POSTURES
    ]
    if not attempted and "launch_attempted" in runtime_posture:
        runtime_posture = [token for token in runtime_posture if token != "launch_attempted"]
    if page_open_status == "not_attempted" and "page_open_attempted" in runtime_posture:
        runtime_posture = [token for token in runtime_posture if token != "page_open_attempted"]
    selector_runtime_posture = _normalize_string_list(
        selector_probe_state.get("project_browser_selector_runtime_posture")
    )
    selector_runtime_posture = [
        token
        for token in selector_runtime_posture
        if token in _PROJECT_BROWSER_SELECTOR_RUNTIME_POSTURES
    ]
    prompt_fill_status = _normalize_text(
        prompt_fill_state.get("project_browser_prompt_fill_status"),
        default="insufficient_truth",
    )
    if prompt_fill_status not in _PROJECT_BROWSER_PROMPT_FILL_STATUSES:
        prompt_fill_status = "insufficient_truth"
    prompt_fill_source_status = _normalize_text(
        prompt_fill_state.get("project_browser_prompt_fill_source_status"),
        default="insufficient_truth",
    )
    if prompt_fill_source_status not in _PROJECT_BROWSER_PROMPT_FILL_SOURCE_STATUSES:
        prompt_fill_source_status = "insufficient_truth"
    prompt_fill_target_status = _normalize_text(
        prompt_fill_state.get("project_browser_prompt_fill_target_status"),
        default="insufficient_truth",
    )
    if prompt_fill_target_status not in _PROJECT_BROWSER_PROMPT_FILL_TARGET_STATUSES:
        prompt_fill_target_status = "insufficient_truth"
    prompt_fill_block_reason = _normalize_text(
        prompt_fill_state.get("project_browser_prompt_fill_block_reason"),
        default="insufficient_truth",
    )
    if prompt_fill_block_reason not in _PROJECT_BROWSER_PROMPT_FILL_BLOCK_REASONS:
        prompt_fill_block_reason = "insufficient_truth"
    prompt_fill_receipt_status = _normalize_text(
        prompt_fill_state.get("project_browser_prompt_fill_receipt_status"),
        default="insufficient_truth",
    )
    if prompt_fill_receipt_status not in _PROJECT_BROWSER_PROMPT_FILL_RECEIPT_STATUSES:
        prompt_fill_receipt_status = "insufficient_truth"
    prompt_fill_receipt_kind = _normalize_text(
        prompt_fill_state.get("project_browser_prompt_fill_receipt_kind"),
        default="none",
    )
    if prompt_fill_receipt_kind not in _PROJECT_BROWSER_PROMPT_FILL_RECEIPT_KINDS:
        prompt_fill_receipt_kind = "none"
    prompt_fill_runtime_posture = _normalize_string_list(
        prompt_fill_state.get("project_browser_prompt_fill_runtime_posture")
    )
    prompt_fill_runtime_posture = [
        token
        for token in prompt_fill_runtime_posture
        if token in _PROJECT_BROWSER_PROMPT_FILL_RUNTIME_POSTURES
    ]
    prompt_send_status = _normalize_text(
        prompt_send_state.get("project_browser_prompt_send_status"),
        default="insufficient_truth",
    )
    if prompt_send_status not in _PROJECT_BROWSER_PROMPT_SEND_STATUSES:
        prompt_send_status = "insufficient_truth"
    prompt_send_target_status = _normalize_text(
        prompt_send_state.get("project_browser_prompt_send_target_status"),
        default="insufficient_truth",
    )
    if prompt_send_target_status not in _PROJECT_BROWSER_PROMPT_SEND_TARGET_STATUSES:
        prompt_send_target_status = "insufficient_truth"
    prompt_send_block_reason = _normalize_text(
        prompt_send_state.get("project_browser_prompt_send_block_reason"),
        default="insufficient_truth",
    )
    if prompt_send_block_reason not in _PROJECT_BROWSER_PROMPT_SEND_BLOCK_REASONS:
        prompt_send_block_reason = "insufficient_truth"
    prompt_send_receipt_status = _normalize_text(
        prompt_send_state.get("project_browser_prompt_send_receipt_status"),
        default="insufficient_truth",
    )
    if prompt_send_receipt_status not in _PROJECT_BROWSER_PROMPT_SEND_RECEIPT_STATUSES:
        prompt_send_receipt_status = "insufficient_truth"
    prompt_send_receipt_kind = _normalize_text(
        prompt_send_state.get("project_browser_prompt_send_receipt_kind"),
        default="none",
    )
    if prompt_send_receipt_kind not in _PROJECT_BROWSER_PROMPT_SEND_RECEIPT_KINDS:
        prompt_send_receipt_kind = "none"
    prompt_send_runtime_posture = _normalize_string_list(
        prompt_send_state.get("project_browser_prompt_send_runtime_posture")
    )
    prompt_send_runtime_posture = [
        token
        for token in prompt_send_runtime_posture
        if token in _PROJECT_BROWSER_PROMPT_SEND_RUNTIME_POSTURES
    ]
    response_wait_status = _normalize_text(
        response_wait_read_state.get("project_browser_response_wait_status"),
        default="insufficient_truth",
    )
    if response_wait_status not in _PROJECT_BROWSER_RESPONSE_WAIT_STATUSES:
        response_wait_status = "insufficient_truth"
    response_read_status = _normalize_text(
        response_wait_read_state.get("project_browser_response_read_status"),
        default="insufficient_truth",
    )
    if response_read_status not in _PROJECT_BROWSER_RESPONSE_READ_STATUSES:
        response_read_status = "insufficient_truth"
    response_text_status = _normalize_text(
        response_wait_read_state.get("project_browser_response_text_status"),
        default="insufficient_truth",
    )
    if response_text_status not in _PROJECT_BROWSER_RESPONSE_TEXT_STATUSES:
        response_text_status = "insufficient_truth"
    response_wait_block_reason = _normalize_text(
        response_wait_read_state.get("project_browser_response_wait_block_reason"),
        default="insufficient_truth",
    )
    if response_wait_block_reason not in _PROJECT_BROWSER_RESPONSE_WAIT_BLOCK_REASONS:
        response_wait_block_reason = "insufficient_truth"
    response_read_receipt_status = _normalize_text(
        response_wait_read_state.get("project_browser_response_read_receipt_status"),
        default="insufficient_truth",
    )
    if response_read_receipt_status not in _PROJECT_BROWSER_RESPONSE_READ_RECEIPT_STATUSES:
        response_read_receipt_status = "insufficient_truth"
    response_read_receipt_kind = _normalize_text(
        response_wait_read_state.get("project_browser_response_read_receipt_kind"),
        default="none",
    )
    if response_read_receipt_kind not in _PROJECT_BROWSER_RESPONSE_READ_RECEIPT_KINDS:
        response_read_receipt_kind = "none"
    response_runtime_posture = _normalize_string_list(
        response_wait_read_state.get("project_browser_response_runtime_posture")
    )
    response_runtime_posture = [
        token
        for token in response_runtime_posture
        if token in _PROJECT_BROWSER_RESPONSE_RUNTIME_POSTURES
    ]
    response_json_parse_status = _normalize_text(
        response_parse_state.get("project_browser_response_json_parse_status"),
        default="insufficient_truth",
    )
    if response_json_parse_status not in _PROJECT_BROWSER_RESPONSE_JSON_PARSE_STATUSES:
        response_json_parse_status = "insufficient_truth"
    response_json_schema_status = _normalize_text(
        response_parse_state.get("project_browser_response_json_schema_status"),
        default="insufficient_truth",
    )
    if response_json_schema_status not in _PROJECT_BROWSER_RESPONSE_JSON_SCHEMA_STATUSES:
        response_json_schema_status = "insufficient_truth"
    response_json_decision_status = _normalize_text(
        response_parse_state.get("project_browser_response_json_decision_status"),
        default="insufficient_truth",
    )
    if response_json_decision_status not in _PROJECT_BROWSER_RESPONSE_JSON_DECISION_STATUSES:
        response_json_decision_status = "insufficient_truth"
    browser_execution_receipt_status = _normalize_text(
        response_parse_state.get("project_browser_execution_receipt_status"),
        default="insufficient_truth",
    )
    if browser_execution_receipt_status not in _PROJECT_BROWSER_EXECUTION_RECEIPT_PARSE_STATUSES:
        browser_execution_receipt_status = "insufficient_truth"
    browser_execution_receipt_kind = _normalize_text(
        response_parse_state.get("project_browser_execution_receipt_kind"),
        default="none",
    )
    if browser_execution_receipt_kind not in _PROJECT_BROWSER_EXECUTION_RECEIPT_PARSE_KINDS:
        browser_execution_receipt_kind = "none"
    browser_execution_result_status = _normalize_text(
        response_parse_state.get("project_browser_execution_result_status"),
        default="insufficient_truth",
    )
    if browser_execution_result_status not in _PROJECT_BROWSER_EXECUTION_RESULT_STATUSES:
        browser_execution_result_status = "insufficient_truth"
    response_parse_block_reason = _normalize_text(
        response_parse_state.get("project_browser_response_parse_block_reason"),
        default="insufficient_truth",
    )
    if response_parse_block_reason not in _PROJECT_BROWSER_RESPONSE_PARSE_BLOCK_REASONS:
        response_parse_block_reason = "insufficient_truth"
    response_parse_runtime_posture = _normalize_string_list(
        response_parse_state.get("project_browser_response_parse_runtime_posture")
    )
    response_parse_runtime_posture = [
        token
        for token in response_parse_runtime_posture
        if token in _PROJECT_BROWSER_RESPONSE_PARSE_RUNTIME_POSTURES
    ]
    recovery_status = _normalize_text(
        recovery_state.get("project_browser_recovery_status"),
        default="insufficient_truth",
    )
    if recovery_status not in _PROJECT_BROWSER_RECOVERY_STATUSES:
        recovery_status = "insufficient_truth"
    recovery_action = _normalize_text(
        recovery_state.get("project_browser_recovery_action"),
        default="none",
    )
    if recovery_action not in _PROJECT_BROWSER_RECOVERY_ACTIONS:
        recovery_action = "none"
    recovery_reason_compact = _normalize_text(
        recovery_state.get("project_browser_recovery_reason"),
        default="insufficient_truth",
    )
    if recovery_reason_compact not in _PROJECT_BROWSER_RECOVERY_REASONS:
        recovery_reason_compact = "insufficient_truth"
    recovery_block_reason = _normalize_text(
        recovery_state.get("project_browser_recovery_block_reason"),
        default="insufficient_truth",
    )
    if recovery_block_reason not in _PROJECT_BROWSER_RECOVERY_BLOCK_REASONS:
        recovery_block_reason = "insufficient_truth"
    recovery_receipt_status = _normalize_text(
        recovery_state.get("project_browser_recovery_receipt_status"),
        default="insufficient_truth",
    )
    if recovery_receipt_status not in _PROJECT_BROWSER_RECOVERY_RECEIPT_STATUSES:
        recovery_receipt_status = "insufficient_truth"
    recovery_receipt_kind = _normalize_text(
        recovery_state.get("project_browser_recovery_receipt_kind"),
        default="none",
    )
    if recovery_receipt_kind not in _PROJECT_BROWSER_RECOVERY_RECEIPT_KINDS:
        recovery_receipt_kind = "none"
    recovery_runtime_posture = _normalize_string_list(
        recovery_state.get("project_browser_recovery_runtime_posture")
    )
    recovery_runtime_posture = [
        token
        for token in recovery_runtime_posture
        if token in _PROJECT_BROWSER_RECOVERY_RUNTIME_POSTURES
    ]

    return {
        "project_browser_launch_status": launch_status,
        "project_browser_context_status": context_status,
        "project_browser_page_open_status": page_open_status,
        "project_browser_chatgpt_page_status": chatgpt_page_status,
        "project_browser_login_interruption_status": login_interruption_status,
        "project_browser_launch_block_reason": launch_block_reason,
        "project_browser_launch_runtime_posture": runtime_posture,
        "project_browser_launch_receipt_status": launch_receipt_status,
        "project_browser_launch_receipt_kind": launch_receipt_kind,
        "project_browser_launch_runtime_launch_attempted": bool(
            "launch_attempted" in runtime_posture
        ),
        "project_browser_launch_runtime_page_open_attempted": bool(
            "page_open_attempted" in runtime_posture
        ),
        "project_browser_launch_runtime_no_prompt_send": True,
        "project_browser_launch_runtime_no_send_click": True,
        "project_browser_launch_runtime_no_response_wait": True,
        "project_browser_launch_runtime_no_response_read": True,
        "project_browser_launch_runtime_no_dom_deep_read": True,
        "project_browser_launch_runtime_no_retry_execution": True,
        "project_browser_launch_runtime_no_reload_execution": True,
        "project_browser_launch_runtime_no_new_chat_execution": True,
        "project_browser_launch_runtime_no_login_recovery": True,
        "project_browser_launch_runtime_no_executor_loop": True,
        "project_browser_selector_resolver_status": selector_resolver_status,
        "project_browser_selector_probe_status": selector_probe_status,
        "project_browser_selector_target_status": normalized_target_status_map,
        "project_browser_dom_readiness_status": dom_readiness_status,
        "project_browser_dom_probe_block_reason": dom_probe_block_reason,
        "project_browser_selector_runtime_posture": selector_runtime_posture,
        "project_browser_selector_probe_receipt_status": selector_probe_receipt_status,
        "project_browser_selector_probe_receipt_kind": selector_probe_receipt_kind,
        "project_browser_selector_runtime_read_only_probe": bool(
            selector_probe_state.get("project_browser_selector_runtime_read_only_probe", False)
        ),
        "project_browser_selector_runtime_no_prompt_fill": bool(
            selector_probe_state.get("project_browser_selector_runtime_no_prompt_fill", True)
        ),
        "project_browser_selector_runtime_no_send_click": bool(
            selector_probe_state.get("project_browser_selector_runtime_no_send_click", True)
        ),
        "project_browser_selector_runtime_no_response_wait": bool(
            selector_probe_state.get("project_browser_selector_runtime_no_response_wait", True)
        ),
        "project_browser_selector_runtime_no_response_read": bool(
            selector_probe_state.get("project_browser_selector_runtime_no_response_read", True)
        ),
        "project_browser_selector_runtime_no_json_parse": bool(
            selector_probe_state.get("project_browser_selector_runtime_no_json_parse", True)
        ),
        "project_browser_selector_runtime_no_retry_execution": bool(
            selector_probe_state.get("project_browser_selector_runtime_no_retry_execution", True)
        ),
        "project_browser_selector_runtime_no_reload_execution": bool(
            selector_probe_state.get("project_browser_selector_runtime_no_reload_execution", True)
        ),
        "project_browser_selector_runtime_no_new_chat_execution": bool(
            selector_probe_state.get("project_browser_selector_runtime_no_new_chat_execution", True)
        ),
        "project_browser_selector_runtime_no_login_recovery": bool(
            selector_probe_state.get("project_browser_selector_runtime_no_login_recovery", True)
        ),
        "project_browser_selector_runtime_no_executor_loop": bool(
            selector_probe_state.get("project_browser_selector_runtime_no_executor_loop", True)
        ),
        "project_browser_selector_target_chat_input_status": normalized_target_status_map.get(
            "chat_input",
            "insufficient_truth",
        ),
        "project_browser_selector_target_send_trigger_status": normalized_target_status_map.get(
            "send_trigger",
            "insufficient_truth",
        ),
        "project_browser_selector_target_latest_assistant_response_status": (
            normalized_target_status_map.get(
                "latest_assistant_response",
                "insufficient_truth",
            )
        ),
        "project_browser_selector_target_message_ready_status": normalized_target_status_map.get(
            "message_ready",
            "insufficient_truth",
        ),
        "project_browser_selector_target_loading_state_status": normalized_target_status_map.get(
            "loading_state",
            "insufficient_truth",
        ),
        "project_browser_selector_target_retryable_ui_failure_status": (
            normalized_target_status_map.get(
                "retryable_ui_failure",
                "insufficient_truth",
            )
        ),
        "project_browser_selector_target_login_interruption_status": (
            normalized_target_status_map.get(
                "login_interruption",
                "insufficient_truth",
            )
        ),
        "project_browser_prompt_fill_status": prompt_fill_status,
        "project_browser_prompt_fill_source_status": prompt_fill_source_status,
        "project_browser_prompt_fill_target_status": prompt_fill_target_status,
        "project_browser_prompt_fill_block_reason": prompt_fill_block_reason,
        "project_browser_prompt_fill_runtime_posture": prompt_fill_runtime_posture,
        "project_browser_prompt_fill_receipt_status": prompt_fill_receipt_status,
        "project_browser_prompt_fill_receipt_kind": prompt_fill_receipt_kind,
        "project_browser_prompt_fill_runtime_fill_attempted": bool(
            prompt_fill_state.get("project_browser_prompt_fill_runtime_fill_attempted", False)
        ),
        "project_browser_prompt_fill_runtime_no_send_click": bool(
            prompt_fill_state.get("project_browser_prompt_fill_runtime_no_send_click", True)
        ),
        "project_browser_prompt_fill_runtime_no_enter_submit": bool(
            prompt_fill_state.get("project_browser_prompt_fill_runtime_no_enter_submit", True)
        ),
        "project_browser_prompt_fill_runtime_no_response_wait": bool(
            prompt_fill_state.get("project_browser_prompt_fill_runtime_no_response_wait", True)
        ),
        "project_browser_prompt_fill_runtime_no_response_read": bool(
            prompt_fill_state.get("project_browser_prompt_fill_runtime_no_response_read", True)
        ),
        "project_browser_prompt_fill_runtime_no_json_parse": bool(
            prompt_fill_state.get("project_browser_prompt_fill_runtime_no_json_parse", True)
        ),
        "project_browser_prompt_fill_runtime_no_retry_execution": bool(
            prompt_fill_state.get("project_browser_prompt_fill_runtime_no_retry_execution", True)
        ),
        "project_browser_prompt_fill_runtime_no_reload_execution": bool(
            prompt_fill_state.get("project_browser_prompt_fill_runtime_no_reload_execution", True)
        ),
        "project_browser_prompt_fill_runtime_no_new_chat_execution": bool(
            prompt_fill_state.get("project_browser_prompt_fill_runtime_no_new_chat_execution", True)
        ),
        "project_browser_prompt_fill_runtime_no_login_recovery": bool(
            prompt_fill_state.get("project_browser_prompt_fill_runtime_no_login_recovery", True)
        ),
        "project_browser_prompt_fill_runtime_no_executor_loop": bool(
            prompt_fill_state.get("project_browser_prompt_fill_runtime_no_executor_loop", True)
        ),
        "project_browser_prompt_send_status": prompt_send_status,
        "project_browser_prompt_send_target_status": prompt_send_target_status,
        "project_browser_prompt_send_block_reason": prompt_send_block_reason,
        "project_browser_prompt_send_runtime_posture": prompt_send_runtime_posture,
        "project_browser_prompt_send_receipt_status": prompt_send_receipt_status,
        "project_browser_prompt_send_receipt_kind": prompt_send_receipt_kind,
        "project_browser_prompt_send_runtime_send_click_attempted": bool(
            prompt_send_state.get(
                "project_browser_prompt_send_runtime_send_click_attempted",
                False,
            )
        ),
        "project_browser_prompt_send_runtime_no_response_wait": bool(
            prompt_send_state.get("project_browser_prompt_send_runtime_no_response_wait", True)
        ),
        "project_browser_prompt_send_runtime_no_response_read": bool(
            prompt_send_state.get("project_browser_prompt_send_runtime_no_response_read", True)
        ),
        "project_browser_prompt_send_runtime_no_json_parse": bool(
            prompt_send_state.get("project_browser_prompt_send_runtime_no_json_parse", True)
        ),
        "project_browser_prompt_send_runtime_no_retry_execution": bool(
            prompt_send_state.get("project_browser_prompt_send_runtime_no_retry_execution", True)
        ),
        "project_browser_prompt_send_runtime_no_reload_execution": bool(
            prompt_send_state.get("project_browser_prompt_send_runtime_no_reload_execution", True)
        ),
        "project_browser_prompt_send_runtime_no_new_chat_execution": bool(
            prompt_send_state.get(
                "project_browser_prompt_send_runtime_no_new_chat_execution",
                True,
            )
        ),
        "project_browser_prompt_send_runtime_no_login_recovery": bool(
            prompt_send_state.get("project_browser_prompt_send_runtime_no_login_recovery", True)
        ),
        "project_browser_prompt_send_runtime_no_executor_loop": bool(
            prompt_send_state.get("project_browser_prompt_send_runtime_no_executor_loop", True)
        ),
        "project_browser_response_wait_status": response_wait_status,
        "project_browser_response_read_status": response_read_status,
        "project_browser_response_text_status": response_text_status,
        "project_browser_response_wait_block_reason": response_wait_block_reason,
        "project_browser_response_runtime_posture": response_runtime_posture,
        "project_browser_response_read_receipt_status": response_read_receipt_status,
        "project_browser_response_read_receipt_kind": response_read_receipt_kind,
        "project_browser_response_text": _normalize_text(
            response_wait_read_state.get("project_browser_response_text"),
            default="",
        ),
        "project_browser_response_text_length": _as_non_negative_int(
            response_wait_read_state.get("project_browser_response_text_length"),
            default=0,
        ),
        "project_browser_response_text_truncated": bool(
            response_wait_read_state.get("project_browser_response_text_truncated", False)
        ),
        "project_browser_response_runtime_response_wait_attempted": bool(
            response_wait_read_state.get(
                "project_browser_response_runtime_response_wait_attempted",
                False,
            )
        ),
        "project_browser_response_runtime_response_read_attempted": bool(
            response_wait_read_state.get(
                "project_browser_response_runtime_response_read_attempted",
                False,
            )
        ),
        "project_browser_response_runtime_no_json_parse": bool(
            response_wait_read_state.get("project_browser_response_runtime_no_json_parse", True)
        ),
        "project_browser_response_runtime_no_decision_execution": bool(
            response_wait_read_state.get(
                "project_browser_response_runtime_no_decision_execution",
                True,
            )
        ),
        "project_browser_response_runtime_no_retry_execution": bool(
            response_wait_read_state.get(
                "project_browser_response_runtime_no_retry_execution",
                True,
            )
        ),
        "project_browser_response_runtime_no_reload_execution": bool(
            response_wait_read_state.get(
                "project_browser_response_runtime_no_reload_execution",
                True,
            )
        ),
        "project_browser_response_runtime_no_new_chat_execution": bool(
            response_wait_read_state.get(
                "project_browser_response_runtime_no_new_chat_execution",
                True,
            )
        ),
        "project_browser_response_runtime_no_login_recovery": bool(
            response_wait_read_state.get(
                "project_browser_response_runtime_no_login_recovery",
                True,
            )
        ),
        "project_browser_response_runtime_no_executor_loop": bool(
            response_wait_read_state.get(
                "project_browser_response_runtime_no_executor_loop",
                True,
            )
        ),
        "project_browser_response_json_parse_status": response_json_parse_status,
        "project_browser_response_json_schema_status": response_json_schema_status,
        "project_browser_response_json_decision_status": response_json_decision_status,
        "project_browser_execution_receipt_status": browser_execution_receipt_status,
        "project_browser_execution_receipt_kind": browser_execution_receipt_kind,
        "project_browser_execution_result_status": browser_execution_result_status,
        "project_browser_response_parse_block_reason": response_parse_block_reason,
        "project_browser_response_parse_runtime_posture": response_parse_runtime_posture,
        "project_browser_response_json_parse_compact": (
            dict(
                response_parse_state.get(
                    "project_browser_response_json_parse_compact",
                    {},
                )
            )
            if isinstance(
                response_parse_state.get("project_browser_response_json_parse_compact"),
                Mapping,
            )
            else {}
        ),
        "project_browser_response_parse_runtime_json_parse_attempted": bool(
            response_parse_state.get(
                "project_browser_response_parse_runtime_json_parse_attempted",
                False,
            )
        ),
        "project_browser_response_parse_runtime_no_decision_execution": bool(
            response_parse_state.get(
                "project_browser_response_parse_runtime_no_decision_execution",
                True,
            )
        ),
        "project_browser_response_parse_runtime_no_queue_mutation": bool(
            response_parse_state.get(
                "project_browser_response_parse_runtime_no_queue_mutation",
                True,
            )
        ),
        "project_browser_response_parse_runtime_no_retry_execution": bool(
            response_parse_state.get(
                "project_browser_response_parse_runtime_no_retry_execution",
                True,
            )
        ),
        "project_browser_response_parse_runtime_no_repair_execution": bool(
            response_parse_state.get(
                "project_browser_response_parse_runtime_no_repair_execution",
                True,
            )
        ),
        "project_browser_response_parse_runtime_no_restart_execution": bool(
            response_parse_state.get(
                "project_browser_response_parse_runtime_no_restart_execution",
                True,
            )
        ),
        "project_browser_response_parse_runtime_no_reload_execution": bool(
            response_parse_state.get(
                "project_browser_response_parse_runtime_no_reload_execution",
                True,
            )
        ),
        "project_browser_response_parse_runtime_no_new_chat_execution": bool(
            response_parse_state.get(
                "project_browser_response_parse_runtime_no_new_chat_execution",
                True,
            )
        ),
        "project_browser_response_parse_runtime_no_login_recovery": bool(
            response_parse_state.get(
                "project_browser_response_parse_runtime_no_login_recovery",
                True,
            )
        ),
        "project_browser_response_parse_runtime_no_executor_loop": bool(
            response_parse_state.get(
                "project_browser_response_parse_runtime_no_executor_loop",
                True,
            )
        ),
        "project_browser_recovery_status": recovery_status,
        "project_browser_recovery_action": recovery_action,
        "project_browser_recovery_reason": recovery_reason_compact,
        "project_browser_recovery_block_reason": recovery_block_reason,
        "project_browser_recovery_runtime_posture": recovery_runtime_posture,
        "project_browser_recovery_receipt_status": recovery_receipt_status,
        "project_browser_recovery_receipt_kind": recovery_receipt_kind,
        "project_browser_recovery_runtime_recovery_attempted": bool(
            recovery_state.get("project_browser_recovery_runtime_recovery_attempted", False)
        ),
        "project_browser_recovery_runtime_no_prompt_refill": bool(
            recovery_state.get("project_browser_recovery_runtime_no_prompt_refill", True)
        ),
        "project_browser_recovery_runtime_no_resend": bool(
            recovery_state.get("project_browser_recovery_runtime_no_resend", True)
        ),
        "project_browser_recovery_runtime_no_response_wait": bool(
            recovery_state.get("project_browser_recovery_runtime_no_response_wait", True)
        ),
        "project_browser_recovery_runtime_no_response_read": bool(
            recovery_state.get("project_browser_recovery_runtime_no_response_read", True)
        ),
        "project_browser_recovery_runtime_no_json_parse": bool(
            recovery_state.get("project_browser_recovery_runtime_no_json_parse", True)
        ),
        "project_browser_recovery_runtime_no_decision_execution": bool(
            recovery_state.get(
                "project_browser_recovery_runtime_no_decision_execution",
                True,
            )
        ),
        "project_browser_recovery_runtime_no_queue_mutation": bool(
            recovery_state.get("project_browser_recovery_runtime_no_queue_mutation", True)
        ),
        "project_browser_recovery_runtime_no_retry_loop": bool(
            recovery_state.get("project_browser_recovery_runtime_no_retry_loop", True)
        ),
        "project_browser_recovery_runtime_no_login_recovery": bool(
            recovery_state.get("project_browser_recovery_runtime_no_login_recovery", True)
        ),
        "project_browser_recovery_runtime_no_executor_loop": bool(
            recovery_state.get("project_browser_recovery_runtime_no_executor_loop", True)
        ),
    }

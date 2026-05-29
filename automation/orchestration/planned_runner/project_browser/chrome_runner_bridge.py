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
def _build_project_browser_autonomous_chrome_runner_bridge_one_shot_state(
    *,
    project_analysis_request_text: str,
    browser_prompt_payload: Mapping[str, Any] | None,
    browser_queue_handoff_payload: Mapping[str, Any] | None,
    prior_browser_state: Mapping[str, Any] | None,
    one_shot_execution_enabled: Any = None,
    one_shot_wait_enabled: Any = None,
    max_wait_seconds: int = 600,
    poll_interval_seconds: int = 10,
) -> dict[str, Any]:
    base_dir_path = Path("/tmp/codex-local-runner-chatgpt-bridge")
    request_path = base_dir_path / "request.md"
    response_path = base_dir_path / "response.md"
    status_path = base_dir_path / "status.json"
    response_read_limit_bytes = 8192
    status_json_read_limit_bytes = 8192
    preview_chars = 500

    def _normalize_preview_text(text: str, *, max_chars: int = 500) -> str:
        if not text:
            return ""
        normalized = " ".join(text.split())
        if len(normalized) <= max_chars:
            return normalized
        return normalized[:max_chars]

    def _read_status_json_snapshot(path_obj: Path) -> dict[str, Any]:
        snapshot: dict[str, Any] = {
            "exists": False,
            "size_bytes": 0,
            "preview": "",
            "parse_completed": False,
            "parse_error": "",
            "last_status": "",
            "last_reason": "",
            "last_step": "",
        }
        if not path_obj.exists():
            return snapshot
        snapshot["exists"] = True
        if not path_obj.is_file():
            snapshot["parse_error"] = "status_json_not_regular_file"
            return snapshot
        try:
            size_bytes = _as_non_negative_int(path_obj.stat().st_size, default=0)
            with path_obj.open("rb") as file_obj:
                raw_bytes = file_obj.read(status_json_read_limit_bytes)
        except OSError as exc:
            snapshot["parse_error"] = f"{exc.__class__.__name__}:{exc}"
            return snapshot
        snapshot["size_bytes"] = size_bytes
        preview_bytes = raw_bytes[:status_json_read_limit_bytes]
        preview_text = preview_bytes.decode("utf-8", errors="replace")
        snapshot["preview"] = _normalize_preview_text(preview_text, max_chars=preview_chars)
        try:
            parsed = json.loads(raw_bytes.decode("utf-8", errors="replace"))
        except Exception as exc:  # pragma: no cover - defensive parse boundary
            snapshot["parse_error"] = f"{exc.__class__.__name__}:{exc}"
            return snapshot
        if not isinstance(parsed, Mapping):
            snapshot["parse_error"] = "status_json_not_mapping"
            return snapshot
        parsed_obj = dict(parsed)
        snapshot["parse_completed"] = True
        snapshot["last_status"] = _normalize_text(parsed_obj.get("status"), default="")
        snapshot["last_reason"] = _normalize_text(parsed_obj.get("reason"), default="")
        snapshot["last_step"] = _normalize_text(
            parsed_obj.get("step"),
            default=_normalize_text(parsed_obj.get("status_step"), default=""),
        )
        return snapshot

    def _is_transient_response(normalized_text: str, text_length: int) -> bool:
        lower = normalized_text.lower()
        if not normalized_text:
            return True
        exact_transients = {
            "思考中",
            "考え中",
            "thinking",
            "thinking...",
            "generating",
            "generating...",
            "応答を生成しています",
            "応答を生成しています...",
            "...",
        }
        if lower in exact_transients or normalized_text in exact_transients:
            return True
        contains_tokens = [
            "thinking",
            "generating",
            "思考中",
            "考え中",
            "生成しています",
            "応答を生成",
        ]
        if text_length <= 40 and any(token in lower or token in normalized_text for token in contains_tokens):
            return True
        return False

    def _read_response_snapshot(path_obj: Path) -> dict[str, Any]:
        snapshot: dict[str, Any] = {
            "exists": False,
            "is_file": False,
            "size_bytes": 0,
            "read_attempted": False,
            "read_completed": False,
            "read_error": "",
            "preview": "",
            "fingerprint": "",
            "transient_detected": False,
            "status": "chrome_runner_bridge_response_missing",
        }
        if not path_obj.exists():
            return snapshot
        snapshot["exists"] = True
        if not path_obj.is_file():
            snapshot["status"] = "chrome_runner_bridge_response_not_file"
            return snapshot
        snapshot["is_file"] = True
        snapshot["read_attempted"] = True
        try:
            file_size = _as_non_negative_int(path_obj.stat().st_size, default=0)
            with path_obj.open("rb") as file_obj:
                raw_bytes = file_obj.read(response_read_limit_bytes)
        except OSError as exc:
            snapshot["size_bytes"] = 0
            snapshot["read_error"] = f"{exc.__class__.__name__}:{exc}"
            snapshot["status"] = "chrome_runner_bridge_response_read_error"
            return snapshot
        snapshot["size_bytes"] = file_size
        text = raw_bytes[:response_read_limit_bytes].decode("utf-8", errors="replace")
        normalized_text = text.strip()
        snapshot["read_completed"] = True
        snapshot["preview"] = _normalize_preview_text(normalized_text, max_chars=preview_chars)
        if normalized_text:
            snapshot["fingerprint"] = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
        else:
            snapshot["fingerprint"] = ""
        text_length = len(normalized_text)
        transient_detected = _is_transient_response(normalized_text, text_length)
        snapshot["transient_detected"] = transient_detected
        if not normalized_text:
            snapshot["status"] = "chrome_runner_bridge_response_empty"
        elif transient_detected:
            snapshot["status"] = "chrome_runner_bridge_response_transient"
        else:
            snapshot["status"] = "chrome_runner_bridge_response_ready"
        return snapshot

    prepared_prompt_text, prepared_prompt_source_status, prepared_prompt_source_reason = (
        _resolve_project_browser_prepared_prompt_text(
            browser_prompt_payload=browser_prompt_payload,
            browser_queue_handoff_payload=browser_queue_handoff_payload,
            prior_browser_state=prior_browser_state,
        )
    )
    request_text_from_analysis_request = _normalize_text(project_analysis_request_text, default="")

    def _read_bool_flag(value: Any, *, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        text = _normalize_text(value, default="").lower()
        if text in {"1", "true", "yes", "on", "enabled"}:
            return True
        if text in {"0", "false", "no", "off", "disabled"}:
            return False
        return default

    selected_request_text = ""
    request_source = ""
    if prepared_prompt_source_status == "available" and prepared_prompt_text:
        selected_request_text = prepared_prompt_text
        request_source = "project_browser_prepared_prompt_text"
    elif request_text_from_analysis_request:
        selected_request_text = request_text_from_analysis_request
        request_source = "project_browser_autonomous_project_analysis_request_text"

    operator_action = (
        "Open a logged-in normal Chrome ChatGPT tab, ensure the composer is empty and no "
        "Verify/CAPTCHA is visible, then click ChatGPT Runner Bridge once."
    )
    wait_timeout_seconds = _as_non_negative_int(max_wait_seconds, default=600)
    wait_poll_seconds = _as_non_negative_int(poll_interval_seconds, default=10)
    if wait_poll_seconds <= 0:
        wait_poll_seconds = 10
    if wait_timeout_seconds <= 0:
        wait_timeout_seconds = 600
    execution_enabled = _read_bool_flag(one_shot_execution_enabled, default=False)
    wait_enabled = _read_bool_flag(one_shot_wait_enabled, default=False)

    state: dict[str, Any] = {
        "project_browser_autonomous_chrome_runner_bridge_one_shot_status": (
            "chrome_runner_bridge_one_shot_not_requested"
        ),
        "project_browser_autonomous_chrome_runner_bridge_one_shot_next_action": (
            "enable_chrome_runner_bridge_one_shot"
        ),
        "project_browser_autonomous_chrome_runner_bridge_base_dir": str(base_dir_path),
        "project_browser_autonomous_chrome_runner_bridge_request_path": str(request_path),
        "project_browser_autonomous_chrome_runner_bridge_response_path": str(response_path),
        "project_browser_autonomous_chrome_runner_bridge_status_path": str(status_path),
        "project_browser_autonomous_chrome_runner_bridge_one_shot_execution_enabled": bool(
            execution_enabled
        ),
        "project_browser_autonomous_chrome_runner_bridge_one_shot_wait_enabled": bool(
            wait_enabled
        ),
        "project_browser_autonomous_chrome_runner_bridge_request_written": False,
        "project_browser_autonomous_chrome_runner_bridge_request_size_bytes": 0,
        "project_browser_autonomous_chrome_runner_bridge_request_fingerprint": "",
        "project_browser_autonomous_chrome_runner_bridge_request_source": request_source,
        "project_browser_autonomous_chrome_runner_bridge_request_write_error": "",
        "project_browser_autonomous_chrome_runner_bridge_operator_action_required": False,
        "project_browser_autonomous_chrome_runner_bridge_operator_action_kind": "",
        "project_browser_autonomous_chrome_runner_bridge_operator_action": "",
        "project_browser_autonomous_chrome_runner_bridge_wait_attempted": False,
        "project_browser_autonomous_chrome_runner_bridge_wait_timeout_seconds": wait_timeout_seconds,
        "project_browser_autonomous_chrome_runner_bridge_wait_poll_interval_seconds": wait_poll_seconds,
        "project_browser_autonomous_chrome_runner_bridge_wait_elapsed_seconds": 0,
        "project_browser_autonomous_chrome_runner_bridge_wait_exit_reason": "wait_not_enabled",
        "project_browser_autonomous_chrome_runner_bridge_response_exists": False,
        "project_browser_autonomous_chrome_runner_bridge_response_is_file": False,
        "project_browser_autonomous_chrome_runner_bridge_response_size_bytes": 0,
        "project_browser_autonomous_chrome_runner_bridge_response_read_attempted": False,
        "project_browser_autonomous_chrome_runner_bridge_response_read_completed": False,
        "project_browser_autonomous_chrome_runner_bridge_response_read_error": "",
        "project_browser_autonomous_chrome_runner_bridge_response_preview": "",
        "project_browser_autonomous_chrome_runner_bridge_response_fingerprint": "",
        "project_browser_autonomous_chrome_runner_bridge_response_transient_detected": False,
        "project_browser_autonomous_chrome_runner_bridge_response_status": (
            "chrome_runner_bridge_response_missing"
        ),
        "project_browser_autonomous_chrome_runner_bridge_status_json_exists": False,
        "project_browser_autonomous_chrome_runner_bridge_status_json_size_bytes": 0,
        "project_browser_autonomous_chrome_runner_bridge_status_json_preview": "",
        "project_browser_autonomous_chrome_runner_bridge_status_json_parse_completed": False,
        "project_browser_autonomous_chrome_runner_bridge_status_json_parse_error": "",
        "project_browser_autonomous_chrome_runner_bridge_status_json_last_status": "",
        "project_browser_autonomous_chrome_runner_bridge_status_json_last_reason": "",
        "project_browser_autonomous_chrome_runner_bridge_status_json_last_step": "",
        "project_browser_autonomous_chrome_runner_bridge_cleanup_error": "",
        "project_browser_autonomous_chrome_runner_bridge_prompt_source_status": (
            prepared_prompt_source_status
        ),
        "project_browser_autonomous_chrome_runner_bridge_prompt_source_reason": (
            prepared_prompt_source_reason
        ),
    }

    if not execution_enabled:
        return state

    if not selected_request_text:
        state["project_browser_autonomous_chrome_runner_bridge_one_shot_status"] = (
            "chrome_runner_bridge_one_shot_blocked_missing_prompt"
        )
        state["project_browser_autonomous_chrome_runner_bridge_one_shot_next_action"] = (
            "provide_bridge_request_prompt"
        )
        return state

    try:
        base_dir_path.mkdir(parents=True, exist_ok=True)
        for stale_path in (response_path, status_path):
            if not stale_path.exists():
                continue
            if not stale_path.is_file() and not stale_path.is_symlink():
                raise OSError(f"stale_path_not_file:{stale_path}")
            stale_path.unlink()
    except OSError as exc:
        state["project_browser_autonomous_chrome_runner_bridge_one_shot_status"] = (
            "chrome_runner_bridge_one_shot_blocked_cleanup_failed"
        )
        state["project_browser_autonomous_chrome_runner_bridge_one_shot_next_action"] = (
            "inspect_bridge_cleanup_error"
        )
        state["project_browser_autonomous_chrome_runner_bridge_cleanup_error"] = (
            f"{exc.__class__.__name__}:{exc}"
        )
        return state

    try:
        temp_path = request_path.with_name(f"{request_path.name}.tmp")
        temp_path.write_text(selected_request_text, encoding="utf-8")
        os.replace(temp_path, request_path)
    except OSError as exc:
        state["project_browser_autonomous_chrome_runner_bridge_one_shot_status"] = (
            "chrome_runner_bridge_one_shot_blocked_cleanup_failed"
        )
        state["project_browser_autonomous_chrome_runner_bridge_one_shot_next_action"] = (
            "inspect_bridge_cleanup_error"
        )
        state["project_browser_autonomous_chrome_runner_bridge_request_write_error"] = (
            f"request_write_failed:{exc.__class__.__name__}:{exc}"
        )
        state["project_browser_autonomous_chrome_runner_bridge_cleanup_error"] = (
            state["project_browser_autonomous_chrome_runner_bridge_request_write_error"]
        )
        return state

    request_size_bytes = _as_non_negative_int(len(selected_request_text.encode("utf-8")), default=0)
    request_fingerprint = hashlib.sha256(selected_request_text.encode("utf-8")).hexdigest()
    state["project_browser_autonomous_chrome_runner_bridge_request_written"] = True
    state["project_browser_autonomous_chrome_runner_bridge_request_size_bytes"] = request_size_bytes
    state["project_browser_autonomous_chrome_runner_bridge_request_fingerprint"] = request_fingerprint
    state["project_browser_autonomous_chrome_runner_bridge_operator_action_required"] = True
    state["project_browser_autonomous_chrome_runner_bridge_operator_action_kind"] = (
        "click_chrome_extension_once"
    )
    state["project_browser_autonomous_chrome_runner_bridge_operator_action"] = operator_action
    state["project_browser_autonomous_chrome_runner_bridge_one_shot_status"] = (
        "chrome_runner_bridge_one_shot_request_written_waiting_for_operator"
    )
    state["project_browser_autonomous_chrome_runner_bridge_one_shot_next_action"] = (
        "click_chrome_runner_bridge_once"
    )
    state["project_browser_autonomous_chrome_runner_bridge_wait_exit_reason"] = (
        "wait_not_enabled"
    )

    if not wait_enabled:
        return state

    terminal_blocked_reasons = {
        "human_verification_required",
        "submit_not_confirmed",
        "bridge_error",
        "response_timeout",
        "composer_not_found",
        "prompt_insert_failed",
        "run_in_progress",
    }

    state["project_browser_autonomous_chrome_runner_bridge_wait_attempted"] = True
    state["project_browser_autonomous_chrome_runner_bridge_wait_exit_reason"] = ""
    state["project_browser_autonomous_chrome_runner_bridge_one_shot_status"] = (
        "chrome_runner_bridge_one_shot_waiting_for_response"
    )
    state["project_browser_autonomous_chrome_runner_bridge_one_shot_next_action"] = (
        "wait_for_chrome_runner_bridge_response"
    )
    start = time.monotonic()
    deadline = start + wait_timeout_seconds

    while True:
        now_ts = time.monotonic()
        elapsed_seconds = _as_non_negative_int(int(now_ts - start), default=0)
        state["project_browser_autonomous_chrome_runner_bridge_wait_elapsed_seconds"] = elapsed_seconds

        status_snapshot = _read_status_json_snapshot(status_path)
        state["project_browser_autonomous_chrome_runner_bridge_status_json_exists"] = bool(
            status_snapshot["exists"]
        )
        state["project_browser_autonomous_chrome_runner_bridge_status_json_size_bytes"] = _as_non_negative_int(
            status_snapshot["size_bytes"],
            default=0,
        )
        state["project_browser_autonomous_chrome_runner_bridge_status_json_preview"] = _normalize_text(
            status_snapshot["preview"],
            default="",
        )
        state["project_browser_autonomous_chrome_runner_bridge_status_json_parse_completed"] = bool(
            status_snapshot["parse_completed"]
        )
        state["project_browser_autonomous_chrome_runner_bridge_status_json_parse_error"] = _normalize_text(
            status_snapshot["parse_error"],
            default="",
        )
        state["project_browser_autonomous_chrome_runner_bridge_status_json_last_status"] = _normalize_text(
            status_snapshot["last_status"],
            default="",
        )
        state["project_browser_autonomous_chrome_runner_bridge_status_json_last_reason"] = _normalize_text(
            status_snapshot["last_reason"],
            default="",
        )
        state["project_browser_autonomous_chrome_runner_bridge_status_json_last_step"] = _normalize_text(
            status_snapshot["last_step"],
            default="",
        )

        response_snapshot = _read_response_snapshot(response_path)
        state["project_browser_autonomous_chrome_runner_bridge_response_exists"] = bool(
            response_snapshot["exists"]
        )
        state["project_browser_autonomous_chrome_runner_bridge_response_is_file"] = bool(
            response_snapshot["is_file"]
        )
        state["project_browser_autonomous_chrome_runner_bridge_response_size_bytes"] = _as_non_negative_int(
            response_snapshot["size_bytes"],
            default=0,
        )
        state["project_browser_autonomous_chrome_runner_bridge_response_read_attempted"] = bool(
            response_snapshot["read_attempted"]
        )
        state["project_browser_autonomous_chrome_runner_bridge_response_read_completed"] = bool(
            response_snapshot["read_completed"]
        )
        state["project_browser_autonomous_chrome_runner_bridge_response_read_error"] = _normalize_text(
            response_snapshot["read_error"],
            default="",
        )
        state["project_browser_autonomous_chrome_runner_bridge_response_preview"] = _normalize_text(
            response_snapshot["preview"],
            default="",
        )
        state["project_browser_autonomous_chrome_runner_bridge_response_fingerprint"] = _normalize_text(
            response_snapshot["fingerprint"],
            default="",
        )
        state["project_browser_autonomous_chrome_runner_bridge_response_transient_detected"] = bool(
            response_snapshot["transient_detected"]
        )
        response_status = _normalize_text(
            response_snapshot["status"],
            default="chrome_runner_bridge_response_missing",
        )
        state["project_browser_autonomous_chrome_runner_bridge_response_status"] = response_status

        last_status = _normalize_text(status_snapshot.get("last_status"), default="")
        last_reason = _normalize_text(status_snapshot.get("last_reason"), default="")
        reason_is_terminal_blocked = (
            last_reason in terminal_blocked_reasons
            or (last_status == "blocked" and last_reason in terminal_blocked_reasons)
        )
        status_reports_result_saved = bool(
            last_status in {"response_saved", "result_saved"}
            or last_reason in {"response_saved", "result_saved"}
        )

        if response_status == "chrome_runner_bridge_response_ready":
            state["project_browser_autonomous_chrome_runner_bridge_one_shot_status"] = (
                "chrome_runner_bridge_one_shot_response_ready"
            )
            state["project_browser_autonomous_chrome_runner_bridge_one_shot_next_action"] = (
                "assimilate_bridge_response"
            )
            state["project_browser_autonomous_chrome_runner_bridge_wait_exit_reason"] = (
                "response_ready"
            )
            break

        if reason_is_terminal_blocked:
            state["project_browser_autonomous_chrome_runner_bridge_one_shot_status"] = (
                "chrome_runner_bridge_one_shot_blocked_by_extension_status"
            )
            state["project_browser_autonomous_chrome_runner_bridge_one_shot_next_action"] = (
                "inspect_bridge_status_json"
            )
            state["project_browser_autonomous_chrome_runner_bridge_wait_exit_reason"] = (
                "extension_terminal_blocked"
            )
            break

        if status_reports_result_saved:
            if response_status == "chrome_runner_bridge_response_transient":
                state["project_browser_autonomous_chrome_runner_bridge_one_shot_status"] = (
                    "chrome_runner_bridge_one_shot_response_transient"
                )
                state["project_browser_autonomous_chrome_runner_bridge_one_shot_next_action"] = (
                    "wait_or_rerun_after_final_response"
                )
                state["project_browser_autonomous_chrome_runner_bridge_wait_exit_reason"] = (
                    "response_transient"
                )
                break
            if response_status == "chrome_runner_bridge_response_empty":
                state["project_browser_autonomous_chrome_runner_bridge_one_shot_status"] = (
                    "chrome_runner_bridge_one_shot_response_empty"
                )
                state["project_browser_autonomous_chrome_runner_bridge_one_shot_next_action"] = (
                    "rerun_chrome_runner_bridge_once"
                )
                state["project_browser_autonomous_chrome_runner_bridge_wait_exit_reason"] = (
                    "response_empty"
                )
                break
            if response_status == "chrome_runner_bridge_response_read_error":
                state["project_browser_autonomous_chrome_runner_bridge_one_shot_status"] = (
                    "chrome_runner_bridge_one_shot_response_read_error"
                )
                state["project_browser_autonomous_chrome_runner_bridge_one_shot_next_action"] = (
                    "inspect_bridge_response_read_error"
                )
                state["project_browser_autonomous_chrome_runner_bridge_wait_exit_reason"] = (
                    "response_read_error"
                )
                break

        if now_ts >= deadline:
            if response_status == "chrome_runner_bridge_response_transient":
                state["project_browser_autonomous_chrome_runner_bridge_one_shot_status"] = (
                    "chrome_runner_bridge_one_shot_response_transient"
                )
                state["project_browser_autonomous_chrome_runner_bridge_one_shot_next_action"] = (
                    "wait_or_rerun_after_final_response"
                )
                state["project_browser_autonomous_chrome_runner_bridge_wait_exit_reason"] = (
                    "timeout_response_transient"
                )
            elif response_status == "chrome_runner_bridge_response_empty":
                state["project_browser_autonomous_chrome_runner_bridge_one_shot_status"] = (
                    "chrome_runner_bridge_one_shot_response_empty"
                )
                state["project_browser_autonomous_chrome_runner_bridge_one_shot_next_action"] = (
                    "rerun_chrome_runner_bridge_once"
                )
                state["project_browser_autonomous_chrome_runner_bridge_wait_exit_reason"] = (
                    "timeout_response_empty"
                )
            elif response_status == "chrome_runner_bridge_response_read_error":
                state["project_browser_autonomous_chrome_runner_bridge_one_shot_status"] = (
                    "chrome_runner_bridge_one_shot_response_read_error"
                )
                state["project_browser_autonomous_chrome_runner_bridge_one_shot_next_action"] = (
                    "inspect_bridge_response_read_error"
                )
                state["project_browser_autonomous_chrome_runner_bridge_wait_exit_reason"] = (
                    "timeout_response_read_error"
                )
            else:
                state["project_browser_autonomous_chrome_runner_bridge_one_shot_status"] = (
                    "chrome_runner_bridge_one_shot_timeout"
                )
                state["project_browser_autonomous_chrome_runner_bridge_one_shot_next_action"] = (
                    "inspect_bridge_status_or_rerun_once"
                )
                state["project_browser_autonomous_chrome_runner_bridge_wait_exit_reason"] = (
                    "timeout"
                )
            break

        remaining = max(0.0, deadline - now_ts)
        sleep_seconds = min(float(wait_poll_seconds), remaining)
        if sleep_seconds <= 0:
            continue
        time.sleep(sleep_seconds)

    state["project_browser_autonomous_chrome_runner_bridge_wait_elapsed_seconds"] = (
        _as_non_negative_int(int(time.monotonic() - start), default=0)
    )
    return state

def _build_project_browser_autonomous_chrome_runner_bridge_response_assimilation_state(
    *,
    bridge_one_shot_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    default_base_dir = "/tmp/codex-local-runner-chatgpt-bridge"
    one_shot_state = dict(bridge_one_shot_state) if isinstance(bridge_one_shot_state, Mapping) else {}
    base_dir_text = _normalize_text(
        one_shot_state.get("project_browser_autonomous_chrome_runner_bridge_base_dir"),
        default=default_base_dir,
    )
    base_dir_path = Path(base_dir_text or default_base_dir)
    response_path = Path(
        _normalize_text(
            one_shot_state.get("project_browser_autonomous_chrome_runner_bridge_response_path"),
            default=str(base_dir_path / "response.md"),
        )
    )
    status_path = Path(
        _normalize_text(
            one_shot_state.get("project_browser_autonomous_chrome_runner_bridge_status_path"),
            default=str(base_dir_path / "status.json"),
        )
    )
    status_read_limit_bytes = 8192
    response_read_limit_bytes = 32768
    summary_max_chars = 240
    prompt_max_chars = 6000

    def _normalize_preview_text(text: str, *, max_chars: int = 500) -> str:
        if not text:
            return ""
        normalized = " ".join(text.split())
        if len(normalized) <= max_chars:
            return normalized
        return normalized[:max_chars]

    def _looks_transient(text: str) -> bool:
        normalized_text = _normalize_text(text, default="")
        if not normalized_text:
            return True
        lower = normalized_text.lower()
        exact_transients = {
            "thinking",
            "thinking...",
            "generating",
            "generating...",
            "思考中",
            "考え中",
            "応答を生成しています",
            "応答を生成しています...",
            "...",
        }
        if lower in exact_transients or normalized_text in exact_transients:
            return True
        if len(normalized_text) <= 40:
            tokens = ("thinking", "generating", "思考中", "考え中", "生成しています", "応答を生成")
            if any(token in lower or token in normalized_text for token in tokens):
                return True
        return False

    def _map_runtime_to_task_status(status: str, reason: str) -> str:
        normalized_status = _normalize_text(status, default="").lower()
        normalized_reason = _normalize_text(reason, default="").lower()
        if normalized_status in {"response_saved", "result_saved"} or normalized_reason in {
            "result_saved",
            "response_saved",
        }:
            return "response_saved"
        if normalized_status == "blocked":
            return "blocked"
        if normalized_status in {"running", "sent", "in_progress"}:
            return "in_progress"
        if normalized_status == "consumed":
            return "consumed"
        return "ready"

    def _classify_assimilation(payload_text: str) -> tuple[str, str, str, str]:
        normalized_text = _normalize_text(payload_text, default="")
        lower = normalized_text.lower()

        def _contains_any(tokens: tuple[str, ...]) -> bool:
            return any(token in lower for token in tokens)

        has_blocker_signal = _contains_any(
            (
                "manual review",
                "blocked",
                "unclear",
                "insufficient",
                "cannot determine",
                "cannot proceed",
                "captcha",
                "verify",
            )
        )
        has_completion_signal = _contains_any(
            (
                "ready to commit",
                "ready for commit",
                "ready to open pr",
                "pr-ready",
                "pull request ready",
                "ready for pr",
                "looks complete",
                "task complete",
                "implementation complete",
            )
        )
        has_fix_signal = _contains_any(("fix", "corrective", "repair", "patch", "resolve", "address"))
        has_failure_signal = _contains_any(("bug", "issue", "error", "failing", "regression", "failed test"))
        has_review_signal = _contains_any(("review", "diff", "result", "validation", "test results"))
        has_prompt_contract_signal = (
            "goal" in lower
            and "allowed files" in lower
            and "forbidden files" in lower
            and "expected artifact" in lower
        ) or ("files to modify" in lower and "validation" in lower)

        if has_blocker_signal:
            return (
                "blocked_or_manual_review",
                "manual_review_required",
                "bridge response indicates manual review or blocked state",
                "response_content_blocked_or_unclear",
            )
        if has_completion_signal:
            return (
                "completion_decision",
                "prepare_commit_or_pr_gate",
                "bridge response indicates completion or PR readiness",
                "",
            )
        if has_fix_signal and has_failure_signal:
            return (
                "fix_prompt",
                "run_codex_fix_prompt",
                "bridge response provides corrective implementation guidance",
                "",
            )
        if has_review_signal and not has_prompt_contract_signal:
            return (
                "review_result",
                "decide_fix_or_complete",
                "bridge response appears to be a review/result assessment",
                "",
            )
        if has_prompt_contract_signal or _contains_any(("implementation prompt", "implement", "apply patch")):
            return (
                "implementation_prompt",
                "run_codex_with_assimilated_prompt",
                "bridge response provides implementation instructions",
                "",
            )
        return (
            "blocked_or_manual_review",
            "manual_review_required",
            "bridge response was saved but could not be conservatively classified",
            "response_unclassified",
        )

    state: dict[str, Any] = {
        "project_browser_autonomous_chrome_runner_bridge_response_assimilation_status": "not_assimilated",
        "project_browser_autonomous_chrome_runner_bridge_response_assimilation_kind": (
            "blocked_or_manual_review"
        ),
        "project_browser_autonomous_chrome_runner_bridge_response_assimilation_next_action": (
            "manual_review_required"
        ),
        "project_browser_autonomous_chrome_runner_bridge_response_assimilation_summary": "",
        "project_browser_autonomous_chrome_runner_bridge_response_assimilation_prompt": "",
        "project_browser_autonomous_chrome_runner_bridge_response_assimilation_blocked_reason": (
            "status_not_response_saved"
        ),
        "project_browser_autonomous_chrome_runner_bridge_response_assimilation_source_task_status": "",
        "project_browser_autonomous_chrome_runner_bridge_response_assimilation_source_runtime_status": "",
        "project_browser_autonomous_chrome_runner_bridge_response_assimilation_source_runtime_reason": "",
        "project_browser_autonomous_chrome_runner_bridge_response_assimilation_source_response_status": "",
        "project_browser_autonomous_chrome_runner_bridge_response_assimilation_consume_status": (
            "not_attempted"
        ),
        "project_browser_autonomous_chrome_runner_bridge_response_assimilation_consume_error": "",
    }

    status_payload: dict[str, Any] = {}
    if not status_path.exists():
        state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_blocked_reason"] = (
            "status_json_missing"
        )
        return state
    if not status_path.is_file():
        state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_blocked_reason"] = (
            "status_json_not_file"
        )
        return state
    try:
        with status_path.open("rb") as file_obj:
            raw_status = file_obj.read(status_read_limit_bytes)
    except OSError as exc:
        state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_blocked_reason"] = (
            f"status_json_read_error:{exc.__class__.__name__}"
        )
        return state

    try:
        parsed_status = json.loads(raw_status.decode("utf-8", errors="replace"))
    except Exception as exc:  # pragma: no cover - defensive parse boundary
        state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_blocked_reason"] = (
            f"status_json_parse_error:{exc.__class__.__name__}"
        )
        return state
    if not isinstance(parsed_status, Mapping):
        state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_blocked_reason"] = (
            "status_json_not_mapping"
        )
        return state
    status_payload = dict(parsed_status)
    runtime_status = _normalize_text(status_payload.get("status"), default="").lower()
    runtime_reason = _normalize_text(status_payload.get("reason"), default="").lower()
    task_status = _normalize_text(status_payload.get("task_status"), default="").lower()
    if not task_status:
        task_status = _map_runtime_to_task_status(runtime_status, runtime_reason)
    state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_source_task_status"] = (
        task_status
    )
    state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_source_runtime_status"] = (
        runtime_status
    )
    state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_source_runtime_reason"] = (
        runtime_reason
    )

    if task_status != "response_saved":
        if task_status == "in_progress":
            blocked_reason = "task_in_progress"
        elif task_status == "blocked":
            blocked_reason = "task_blocked"
        elif task_status == "consumed":
            blocked_reason = "task_already_consumed"
        elif task_status == "ready":
            blocked_reason = "task_not_completed"
        else:
            blocked_reason = "status_not_response_saved"
        state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_blocked_reason"] = (
            blocked_reason
        )
        return state

    response_status = _normalize_text(
        one_shot_state.get("project_browser_autonomous_chrome_runner_bridge_response_status"),
        default="",
    )
    if not response_status:
        response_status = "chrome_runner_bridge_response_missing"
        if response_path.exists():
            if not response_path.is_file():
                response_status = "chrome_runner_bridge_response_not_file"
            else:
                try:
                    with response_path.open("rb") as file_obj:
                        raw_probe = file_obj.read(1024)
                except OSError:
                    response_status = "chrome_runner_bridge_response_read_error"
                else:
                    probe_text = raw_probe.decode("utf-8", errors="replace").strip()
                    if not probe_text:
                        response_status = "chrome_runner_bridge_response_empty"
                    elif _looks_transient(probe_text):
                        response_status = "chrome_runner_bridge_response_transient"
                    else:
                        response_status = "chrome_runner_bridge_response_ready"
    state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_source_response_status"] = (
        response_status
    )
    if response_status != "chrome_runner_bridge_response_ready":
        response_status_to_reason = {
            "chrome_runner_bridge_response_missing": "response_missing",
            "chrome_runner_bridge_response_not_file": "response_not_file",
            "chrome_runner_bridge_response_empty": "response_empty",
            "chrome_runner_bridge_response_transient": "response_transient",
            "chrome_runner_bridge_response_read_error": "response_read_error",
        }
        state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_blocked_reason"] = (
            response_status_to_reason.get(response_status, "response_not_ready")
        )
        return state

    try:
        with response_path.open("rb") as file_obj:
            raw_response = file_obj.read(response_read_limit_bytes)
    except OSError as exc:
        state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_blocked_reason"] = (
            f"response_read_error:{exc.__class__.__name__}"
        )
        return state
    response_text = raw_response.decode("utf-8", errors="replace").strip()
    if not response_text:
        state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_blocked_reason"] = (
            "response_empty"
        )
        return state
    if _looks_transient(response_text):
        state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_blocked_reason"] = (
            "response_transient"
        )
        return state

    kind, next_action, summary, blocked_reason = _classify_assimilation(response_text)
    state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_kind"] = kind
    state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_next_action"] = (
        next_action
    )
    state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_summary"] = (
        _normalize_preview_text(summary or response_text, max_chars=summary_max_chars)
    )
    state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_prompt"] = (
        _normalize_preview_text(response_text, max_chars=prompt_max_chars)
    )
    state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_blocked_reason"] = (
        blocked_reason
    )

    assimilated_kinds = {
        "implementation_prompt",
        "review_result",
        "fix_prompt",
        "completion_decision",
    }
    if kind in assimilated_kinds:
        state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_status"] = (
            "assimilated"
        )
        consume_payload: dict[str, Any] = {}
        for key in ("task_id", "request_fingerprint", "created_at"):
            value = _normalize_text(status_payload.get(key), default="")
            if value:
                consume_payload[key] = value
        consume_body = json.dumps(consume_payload).encode("utf-8")
        request = urllib_request.Request(
            "http://127.0.0.1:8765/consume-result",
            data=consume_body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib_request.urlopen(request, timeout=2.0) as response_obj:  # noqa: S310
                response_bytes = response_obj.read(8192)
        except urllib_error.URLError as exc:
            state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_consume_status"] = (
                "consume_post_failed"
            )
            state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_consume_error"] = (
                f"{exc.__class__.__name__}:{exc}"
            )
        except OSError as exc:
            state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_consume_status"] = (
                "consume_post_failed"
            )
            state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_consume_error"] = (
                f"{exc.__class__.__name__}:{exc}"
            )
        else:
            parsed_response: dict[str, Any] = {}
            try:
                decoded = json.loads(response_bytes.decode("utf-8", errors="replace"))
            except Exception:
                decoded = {}
            if isinstance(decoded, Mapping):
                parsed_response = dict(decoded)
            consume_ok = bool(parsed_response.get("ok", False))
            if consume_ok:
                state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_consume_status"] = (
                    "consume_succeeded"
                )
            else:
                state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_consume_status"] = (
                    "consume_post_failed"
                )
                state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_consume_error"] = (
                    "consume_response_not_ok"
                )
    else:
        state["project_browser_autonomous_chrome_runner_bridge_response_assimilation_status"] = (
            "blocked"
        )
    return state

def _build_project_browser_autonomous_chrome_runner_bridge_bounded_loop_state(
    *,
    response_assimilation_state: Mapping[str, Any] | None,
    approved_restart_payload: Mapping[str, Any] | None,
    prior_approved_restart_execution_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    assimilation_state = (
        dict(response_assimilation_state) if isinstance(response_assimilation_state, Mapping) else {}
    )
    approved_restart = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    prior_payload = (
        dict(prior_approved_restart_execution_payload)
        if isinstance(prior_approved_restart_execution_payload, Mapping)
        else {}
    )

    def _read_flag(
        key: str,
        *,
        default: bool = False,
    ) -> bool:
        if key in prior_payload:
            value = prior_payload.get(key)
        else:
            value = approved_restart.get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        text = _normalize_text(value, default="").lower()
        if text in {"1", "true", "yes", "on", "enabled"}:
            return True
        if text in {"0", "false", "no", "off", "disabled"}:
            return False
        return default

    def _read_int(key: str, *, default: int) -> int:
        if key in prior_payload:
            value = prior_payload.get(key)
        else:
            value = approved_restart.get(key)
        return _as_non_negative_int(value, default=default)

    loop_enabled = _read_flag(
        "project_browser_autonomous_chrome_runner_bridge_bounded_loop_enabled",
        default=False,
    )
    loop_execute_enabled = _read_flag(
        "project_browser_autonomous_chrome_runner_bridge_bounded_loop_execute_enabled",
        default=False,
    )
    loop_max_iterations = _read_int(
        "project_browser_autonomous_chrome_runner_bridge_bounded_loop_max_iterations",
        default=1,
    )
    if loop_max_iterations <= 0:
        loop_max_iterations = 1
    loop_iteration = _read_int(
        "project_browser_autonomous_chrome_runner_bridge_bounded_loop_iteration",
        default=_read_int(
            "project_browser_autonomous_chrome_runner_bridge_bounded_loop_current_iteration",
            default=0,
        ),
    )
    max_consecutive_failures = 1
    failure_count = _as_non_negative_int(
        prior_payload.get(
            "project_browser_autonomous_chrome_runner_bridge_bounded_loop_failure_count",
            0,
        ),
        default=0,
    )

    assimilation_status = _normalize_text(
        assimilation_state.get(
            "project_browser_autonomous_chrome_runner_bridge_response_assimilation_status"
        ),
        default="not_assimilated",
    )
    assimilation_next_action = _normalize_text(
        assimilation_state.get(
            "project_browser_autonomous_chrome_runner_bridge_response_assimilation_next_action"
        ),
        default="manual_review_required",
    )
    assimilation_prompt = _normalize_text(
        assimilation_state.get(
            "project_browser_autonomous_chrome_runner_bridge_response_assimilation_prompt"
        ),
        default="",
    )
    assimilation_summary = _normalize_text(
        assimilation_state.get(
            "project_browser_autonomous_chrome_runner_bridge_response_assimilation_summary"
        ),
        default="",
    )
    allowed_assimilation_next_actions = {
        "run_codex_with_assimilated_prompt",
        "run_codex_fix_prompt",
        "decide_fix_or_complete",
        "prepare_commit_or_pr_gate",
        "manual_review_required",
    }
    route_for_codex = assimilation_next_action in {
        "run_codex_with_assimilated_prompt",
        "run_codex_fix_prompt",
    }
    selected_prompt = assimilation_prompt if route_for_codex else ""
    selected_prompt_fingerprint = (
        hashlib.sha256(selected_prompt.encode("utf-8")).hexdigest() if selected_prompt else ""
    )
    prior_selected_prompt_fingerprint = _normalize_text(
        prior_payload.get(
            "project_browser_autonomous_chrome_runner_bridge_bounded_loop_selected_prompt_fingerprint"
        ),
        default="",
    )
    duplicate_prompt_detected = bool(
        selected_prompt_fingerprint
        and prior_selected_prompt_fingerprint
        and selected_prompt_fingerprint == prior_selected_prompt_fingerprint
    )

    blocked_unsafe_tokens = (
        "playwright",
        "chatgpt api",
        "openai api",
        "captcha bypass",
        "verify bypass",
        "store cookie",
        "store cookies",
        "store token",
        "store tokens",
        "store session",
        "store sessions",
        "daemon",
        "scheduler",
        "background queue",
        "queue drain",
        "unbounded loop",
        "infinite loop",
        "new shell execution",
        "new codex execution",
        "auto commit",
        "automatic commit",
        "auto tag",
        "automatic tag",
        "auto pr",
        "automatic pr",
        "auto merge",
        "automatic merge",
        "rm -rf /",
        "delete /",
        "outside repo",
    )
    lower_prompt = selected_prompt.lower()
    unsafe_prompt_detected = bool(
        selected_prompt and any(token in lower_prompt for token in blocked_unsafe_tokens)
    )

    loop_status = "loop_not_requested"
    loop_next_action = "enable_bounded_loop"
    loop_stop_reason = "loop_disabled"
    decision_summary = "bounded loop disabled by default"
    loop_routed = False

    if loop_enabled:
        loop_status = "loop_decision_only"
        loop_next_action = assimilation_next_action
        loop_stop_reason = "decision_only_execution_disabled"
        decision_summary = f"selected assimilation next action: {assimilation_next_action or 'none'}"

        if failure_count >= max_consecutive_failures:
            loop_status = "loop_iteration_limit_reached"
            loop_next_action = "manual_review_required"
            loop_stop_reason = "max_consecutive_failures_reached"
            decision_summary = "bounded loop stopped after consecutive failure limit"
        elif loop_iteration >= loop_max_iterations:
            loop_status = "loop_iteration_limit_reached"
            loop_next_action = "manual_review_required"
            loop_stop_reason = "max_iterations_reached"
            decision_summary = "bounded loop stopped at max iteration limit"
        elif assimilation_status != "assimilated":
            loop_status = "loop_blocked_missing_assimilation"
            loop_next_action = "manual_review_required"
            loop_stop_reason = f"assimilation_status:{assimilation_status or 'unknown'}"
            decision_summary = "bounded loop blocked because no assimilated bridge response was available"
        elif assimilation_next_action not in allowed_assimilation_next_actions:
            loop_status = "loop_blocked_invalid_next_action"
            loop_next_action = "manual_review_required"
            loop_stop_reason = "invalid_assimilation_next_action"
            decision_summary = "bounded loop blocked due to unsupported assimilation next action"
        elif assimilation_next_action == "manual_review_required":
            loop_status = "loop_blocked_manual_review"
            loop_next_action = "manual_review_required"
            loop_stop_reason = "manual_review_required"
            decision_summary = "bounded loop stopped because manual review is required"
        elif route_for_codex and not selected_prompt:
            loop_status = "loop_blocked_missing_assimilation"
            loop_next_action = "manual_review_required"
            loop_stop_reason = "selected_prompt_missing"
            decision_summary = "bounded loop blocked because routed prompt text was unavailable"
        elif route_for_codex and unsafe_prompt_detected:
            loop_status = "loop_blocked_unsafe_prompt"
            loop_next_action = "manual_review_required"
            loop_stop_reason = "unsafe_prompt_detected"
            decision_summary = "bounded loop blocked by unsafe assimilated prompt content"
        elif route_for_codex and duplicate_prompt_detected:
            loop_status = "loop_blocked_duplicate_prompt"
            loop_next_action = "manual_review_required"
            loop_stop_reason = "duplicate_prompt_fingerprint"
            decision_summary = "bounded loop blocked because the assimilated prompt fingerprint is duplicated"
        elif not loop_execute_enabled:
            loop_status = "loop_decision_only"
            loop_next_action = assimilation_next_action
            loop_stop_reason = "execution_not_enabled"
            decision_summary = "bounded loop decision exposed without execution routing"
        elif assimilation_next_action == "run_codex_with_assimilated_prompt":
            route_path = Path("/tmp/codex-local-runner-decision/generated_next_prompt.txt")
            if route_path.is_symlink() or not route_path.parent.exists():
                loop_status = "loop_blocked_no_existing_runner_route"
                loop_next_action = "manual_review_required"
                loop_stop_reason = "existing_next_prompt_route_unavailable"
                decision_summary = "bounded loop could not route to existing next-prompt surface"
            else:
                try:
                    tmp_path = route_path.with_name(f"{route_path.name}.tmp")
                    tmp_path.write_text(selected_prompt, encoding="utf-8")
                    os.replace(tmp_path, route_path)
                except OSError:
                    loop_status = "loop_blocked_no_existing_runner_route"
                    loop_next_action = "manual_review_required"
                    loop_stop_reason = "existing_next_prompt_route_write_failed"
                    decision_summary = "bounded loop failed to write existing next-prompt surface"
                else:
                    loop_status = "loop_ready_or_routed_to_codex"
                    loop_next_action = "run_existing_codex_implementation_step"
                    loop_stop_reason = "routed_to_existing_next_prompt_surface"
                    decision_summary = "bounded loop routed assimilated prompt to existing implementation surface"
                    loop_routed = True
                    loop_iteration = min(loop_max_iterations, loop_iteration + 1)
        elif assimilation_next_action == "run_codex_fix_prompt":
            route_path = Path("/tmp/codex-local-runner-decision/generated_fix_prompt.txt")
            if route_path.is_symlink() or not route_path.parent.exists():
                loop_status = "loop_blocked_no_existing_runner_route"
                loop_next_action = "manual_review_required"
                loop_stop_reason = "existing_fix_prompt_route_unavailable"
                decision_summary = "bounded loop could not route to existing fix-prompt surface"
            else:
                try:
                    tmp_path = route_path.with_name(f"{route_path.name}.tmp")
                    tmp_path.write_text(selected_prompt, encoding="utf-8")
                    os.replace(tmp_path, route_path)
                except OSError:
                    loop_status = "loop_blocked_no_existing_runner_route"
                    loop_next_action = "manual_review_required"
                    loop_stop_reason = "existing_fix_prompt_route_write_failed"
                    decision_summary = "bounded loop failed to write existing fix-prompt surface"
                else:
                    loop_status = "loop_ready_or_routed_to_codex_fix"
                    loop_next_action = "run_existing_codex_fix_step"
                    loop_stop_reason = "routed_to_existing_fix_prompt_surface"
                    decision_summary = "bounded loop routed assimilated prompt to existing fix surface"
                    loop_routed = True
                    loop_iteration = min(loop_max_iterations, loop_iteration + 1)
        elif assimilation_next_action == "decide_fix_or_complete":
            loop_status = "loop_ready_to_decide_fix_or_complete"
            loop_next_action = "decide_fix_or_complete"
            loop_stop_reason = "review_decision_ready"
            decision_summary = "bounded loop prepared review decision handoff"
        elif assimilation_next_action == "prepare_commit_or_pr_gate":
            loop_status = "loop_ready_for_commit_or_pr_gate"
            loop_next_action = "prepare_commit_or_pr_gate"
            loop_stop_reason = "commit_or_pr_gate_ready"
            decision_summary = "bounded loop prepared commit/PR gate readiness"
        else:
            loop_status = "loop_blocked_invalid_next_action"
            loop_next_action = "manual_review_required"
            loop_stop_reason = "invalid_assimilation_next_action"
            decision_summary = "bounded loop blocked due to unsupported assimilation next action"

    return {
        "project_browser_autonomous_chrome_runner_bridge_bounded_loop_status": loop_status,
        "project_browser_autonomous_chrome_runner_bridge_bounded_loop_next_action": loop_next_action,
        "project_browser_autonomous_chrome_runner_bridge_bounded_loop_enabled": bool(loop_enabled),
        "project_browser_autonomous_chrome_runner_bridge_bounded_loop_execute_enabled": bool(
            loop_execute_enabled
        ),
        "project_browser_autonomous_chrome_runner_bridge_bounded_loop_iteration": _as_non_negative_int(
            loop_iteration,
            default=0,
        ),
        "project_browser_autonomous_chrome_runner_bridge_bounded_loop_current_iteration": _as_non_negative_int(
            loop_iteration,
            default=0,
        ),
        "project_browser_autonomous_chrome_runner_bridge_bounded_loop_max_iterations": _as_non_negative_int(
            loop_max_iterations,
            default=1,
        ),
        "project_browser_autonomous_chrome_runner_bridge_bounded_loop_stop_reason": (
            _normalize_text(loop_stop_reason, default="")
        ),
        "project_browser_autonomous_chrome_runner_bridge_bounded_loop_selected_prompt": (
            _normalize_text(selected_prompt, default="")
        ),
        "project_browser_autonomous_chrome_runner_bridge_bounded_loop_selected_prompt_fingerprint": (
            _normalize_text(selected_prompt_fingerprint, default="")
        ),
        "project_browser_autonomous_chrome_runner_bridge_bounded_loop_decision_summary": (
            _normalize_text(decision_summary or assimilation_summary, default="")
        ),
        "project_browser_autonomous_chrome_runner_bridge_bounded_loop_routed": bool(loop_routed),
        "project_browser_autonomous_chrome_runner_bridge_bounded_loop_failure_count": _as_non_negative_int(
            failure_count + (1 if str(loop_status).startswith("loop_blocked_") else 0),
            default=0,
        ),
        "project_browser_autonomous_chrome_runner_bridge_bounded_loop_max_consecutive_failures": (
            max_consecutive_failures
        ),
        "project_browser_autonomous_chrome_runner_bridge_bounded_loop_runtime_posture": [
            "bounded_loop_single_step",
            "default_off",
            "no_unbounded_loop",
            "no_new_executor_path",
            "no_commit_pr_merge_automation",
        ],
    }

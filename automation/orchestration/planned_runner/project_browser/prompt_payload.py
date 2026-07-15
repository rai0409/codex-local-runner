from __future__ import annotations
from automation.orchestration.planned_runner.constants import *

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
def _build_project_browser_prompt_payload_state(
    *,
    browser_task_status: str,
    browser_task_type: str,
    browser_task_envelope_status: str,
    browser_task_envelope: Mapping[str, Any] | None,
    browser_response_schema_ref: str,
    browser_selector_contract_status: str,
    browser_ui_readiness_status: str,
    browser_ui_failure_status: str,
    browser_selector_targets: list[str],
    project_planning_summary_status: str,
    objective_compiler_status: str,
    implementation_prompt_status: str,
    project_pr_queue_status: str,
    project_failure_memory_status: str,
    project_autonomy_budget_status: str,
    project_external_boundary_status: str,
    project_external_dependency_posture: str,
    project_human_escalation_status: str,
    project_human_escalation_required: bool,
    project_failure_memory_suppression_active: bool,
) -> dict[str, Any]:
    normalized_task_status = _normalize_text(browser_task_status, default="inactive")
    normalized_task_type = _normalize_text(browser_task_type, default="none")
    normalized_envelope_status = _normalize_text(
        browser_task_envelope_status,
        default="inactive",
    )
    envelope = (
        dict(browser_task_envelope)
        if isinstance(browser_task_envelope, Mapping)
        else {}
    )
    task_type = _normalize_text(
        envelope.get("task_type"),
        default=normalized_task_type,
    )
    objective_id = _normalize_text(envelope.get("objective_id"), default="")
    step_id = _normalize_text(envelope.get("step_id"), default="")
    schema_ref = _normalize_text(
        envelope.get("required_json_schema_ref"),
        default=_normalize_text(
            browser_response_schema_ref,
            default="",
        ),
    )
    active = normalized_task_status != "inactive" and task_type != "none"
    missing_required_fields = _serialize_required_signals(
        [
            "task_type_missing"
            if task_type in {"", "none"}
            else "",
            "objective_id_missing" if not objective_id else "",
            "step_id_missing" if not step_id else "",
            "required_json_schema_missing" if not schema_ref else "",
        ]
    )

    payload_status = "inactive"
    if not active:
        payload_status = "inactive"
    elif missing_required_fields or normalized_envelope_status != "ready":
        payload_status = "insufficient_truth"
    elif _normalize_text(browser_ui_failure_status, default="") in {
        "login_interruption",
        "loading_timeout",
    }:
        payload_status = "unavailable"
    elif normalized_task_status in {"available", "invalid_response"}:
        payload_status = "ready"
    elif normalized_task_status == "insufficient_truth":
        payload_status = "insufficient_truth"
    else:
        payload_status = "unavailable"
    if payload_status not in _PROJECT_BROWSER_PROMPT_PAYLOAD_STATUSES:
        payload_status = "insufficient_truth"

    section_availability: dict[str, bool] = {
        "project_brief_summary": bool(project_planning_summary_status == "available"),
        "active_objective_summary": bool(objective_compiler_status == "available"),
        "current_constraints_summary": bool(
            project_external_boundary_status == "available"
            and project_human_escalation_status == "available"
        ),
        "current_state_summary": bool(active),
        "latest_diff_summary": bool(
            implementation_prompt_status == "available"
            or project_pr_queue_status in {"prepared", "blocked", "empty"}
        ),
        "failure_memory_summary": bool(project_failure_memory_status == "available"),
        "budget_boundary_summary": bool(
            project_autonomy_budget_status == "available"
            and project_external_boundary_status == "available"
        ),
        "requested_task_type": bool(task_type and task_type != "none"),
        "required_json_schema": bool(schema_ref),
    }
    section_statuses: list[dict[str, Any]] = []
    for section_name in _PROJECT_BROWSER_PROMPT_SECTION_NAMES:
        available = bool(section_availability.get(section_name, False))
        section_statuses.append(
            {
                "section": section_name,
                "available": available,
                "status": "available" if available else "insufficient_truth",
            }
        )
    sections_available_count = sum(
        1 for section in section_statuses if bool(section.get("available", False))
    )

    context_level = "minimal"
    if payload_status == "insufficient_truth":
        context_level = "insufficient_truth"
    else:
        expanded_required = bool(
            task_type in {"planner", "repair", "scoring"}
            or project_human_escalation_required
            or project_failure_memory_suppression_active
            or project_external_dependency_posture in {"dependency_blocked", "manual_only"}
            or _normalize_text(browser_ui_readiness_status, default="")
            in {"insufficient_truth", "unavailable"}
            or _normalize_text(browser_selector_contract_status, default="")
            in {"insufficient_truth", "unavailable"}
        )
        context_level = "expanded" if expanded_required else "minimal"
    if context_level not in _PROJECT_BROWSER_PROMPT_CONTEXT_LEVELS:
        context_level = "insufficient_truth"

    token_posture = "compact"
    if payload_status == "insufficient_truth":
        token_posture = "blocked_insufficient_truth"
    elif context_level == "expanded":
        token_posture = "expanded_required"
    if token_posture not in _PROJECT_BROWSER_PROMPT_TOKEN_POSTURES:
        token_posture = "blocked_insufficient_truth"

    runtime_posture = [
        "metadata_only",
        "no_browser_send",
        "no_dom_read",
        "no_session_check",
    ]

    return {
        "project_browser_prompt_payload_status": payload_status,
        "project_browser_prompt_payload_style": "summary_first",
        "project_browser_prompt_payload_sections": section_statuses,
        "project_browser_prompt_payload_section_count": len(section_statuses),
        "project_browser_prompt_payload_sections_available_count": sections_available_count,
        "project_browser_prompt_payload_missing_required_fields": missing_required_fields,
        "project_browser_prompt_context_level": context_level,
        "project_browser_prompt_payload_context_level": context_level,
        "project_browser_prompt_token_posture": token_posture,
        "project_browser_prompt_payload_token_posture": token_posture,
        "project_browser_prompt_context_task_type": task_type,
        "project_browser_prompt_context_objective_id": objective_id,
        "project_browser_prompt_context_step_id": step_id,
        "project_browser_prompt_context_selector_contract_status": _normalize_text(
            browser_selector_contract_status,
            default="insufficient_truth",
        ),
        "project_browser_prompt_context_selector_targets": _normalize_string_list(
            browser_selector_targets
        ),
        "project_browser_prompt_schema_required_json_ref": schema_ref,
        "project_browser_prompt_schema_required_json_available": bool(schema_ref),
        "project_browser_prompt_runtime_posture": runtime_posture,
        "project_browser_prompt_payload_runtime_posture": runtime_posture,
        "project_browser_prompt_runtime_metadata_only": True,
        "project_browser_prompt_runtime_no_browser_send": True,
        "project_browser_prompt_runtime_no_dom_read": True,
        "project_browser_prompt_runtime_no_session_check": True,
        "project_browser_prompt_runtime_dom_checked": False,
        "project_browser_prompt_runtime_session_checked": False,
        "project_browser_prompt_runtime_recovery_attempted": False,
    }

def _build_project_browser_autonomous_chatgpt_implementation_packet_state(
    *,
    decision_consumption_status: str,
    decision_consumption_ready: bool,
    decision_consumption_block_reason: str,
    source_decision: str,
    objective_summary: str,
    implementation_actor: str,
    implementation_mode: str,
    implementation_output_kind: str,
    implementation_allowed: bool,
    rollback_required: bool,
    human_review_required: bool,
    same_actor_requires_human_review: bool,
    actor_separation_status: str,
    allowed_files: list[str] | None,
    forbidden_files: list[str] | None,
    required_constraints: list[str] | None,
    forbidden_actions: list[str] | None,
) -> dict[str, Any]:
    allowed_output_kinds = {
        "patch_plan",
        "unified_diff",
        "full_file_replacement",
        "manual_steps",
        "instructions_only",
        "none",
    }
    normalized_consumption_status = _normalize_text(
        decision_consumption_status,
        default="insufficient_truth",
    )
    normalized_consumption_block_reason = _normalize_text(
        decision_consumption_block_reason,
        default="insufficient_truth",
    )
    normalized_source_decision = _normalize_text(source_decision, default="none")
    normalized_objective_summary = _normalize_text(objective_summary, default="")
    normalized_implementation_actor = _normalize_text(implementation_actor, default="none")
    normalized_implementation_mode = _normalize_text(implementation_mode, default="none")
    normalized_implementation_output_kind = _normalize_text(
        implementation_output_kind,
        default="none",
    )
    if normalized_implementation_output_kind not in allowed_output_kinds:
        normalized_implementation_output_kind = "none"

    normalized_allowed_files = _normalize_string_list(allowed_files or [])
    normalized_forbidden_files = _normalize_string_list(forbidden_files or [])
    normalized_required_constraints = _normalize_string_list(required_constraints or [])
    normalized_forbidden_actions = _normalize_string_list(forbidden_actions or [])
    normalized_actor_separation_status = _normalize_text(
        actor_separation_status,
        default="insufficient_truth",
    )

    mandatory_constraints = [
        "ChatGPT-Implementer must not approve its own output.",
        "ChatGPT-Judge or human_operator must review before commit.",
        "No ChatGPT API call.",
        "No browser UI automation.",
        "No patch generation or patch application.",
    ]
    mandatory_forbidden_actions = [
        "Do not approve own output.",
        "Do not commit without ChatGPT-Judge or human_operator review.",
        "Do not call ChatGPT API.",
        "Do not automate browser UI.",
        "Do not apply patches.",
    ]
    normalized_required_constraints = _serialize_required_signals(
        normalized_required_constraints + mandatory_constraints
    )
    normalized_forbidden_actions = _serialize_required_signals(
        normalized_forbidden_actions + mandatory_forbidden_actions
    )

    expected_packet_path = "/tmp/codex-local-runner-decision/chatgpt_implementation_packet.md"
    expected_response_path = "/tmp/codex-local-runner-decision/chatgpt_implementation_response.md"
    expected_patch_path = "/tmp/codex-local-runner-decision/chatgpt_implementation_patch.diff"

    decision_requests_implementation = bool(
        implementation_allowed
        or normalized_source_decision
        in {
            "implementation_required",
            "fix_required",
        }
    )

    required_inputs = [
        "objective_summary",
        "source_decision_status",
        "source_decision",
        "implementation_actor",
        "implementation_mode",
        "implementation_output_kind",
        "allowed_files",
        "forbidden_files",
        "required_constraints",
        "forbidden_actions",
        "expected_response_path",
        "expected_patch_path",
    ]
    available_inputs: list[str] = [
        "source_decision_status",
        "source_decision",
        "implementation_actor",
        "implementation_mode",
        "implementation_output_kind",
        "required_constraints",
        "forbidden_actions",
        "expected_response_path",
        "expected_patch_path",
    ]
    if normalized_objective_summary:
        available_inputs.append("objective_summary")
    if normalized_allowed_files:
        available_inputs.append("allowed_files")
    if normalized_forbidden_files:
        available_inputs.append("forbidden_files")
    missing_inputs = [
        input_name for input_name in required_inputs if input_name not in set(available_inputs)
    ]

    packet_status = "blocked_waiting_for_valid_decision"
    packet_next_action = "wait_for_valid_chatgpt_decision_json"
    packet_block_reason = "decision_not_ready"
    handoff_status = "blocked_waiting_for_valid_decision"
    handoff_transport = "local_file_handoff"
    handoff_next_action = "wait_for_valid_chatgpt_decision_json"
    handoff_target = "local_decision_json"

    if rollback_required:
        packet_status = "blocked_rollback_required"
        packet_block_reason = "rollback_required"
        packet_next_action = "rollback_required"
        handoff_status = "blocked_rollback_required"
        handoff_transport = "unavailable"
        handoff_next_action = "rollback_required"
        handoff_target = "unavailable"
    elif human_review_required:
        packet_status = "blocked_human_review_required"
        packet_block_reason = "human_review_required"
        packet_next_action = "human_review_required"
        handoff_status = "blocked_human_review_required"
        handoff_transport = "local_file_handoff"
        handoff_next_action = "human_review_required"
        handoff_target = "human_operator"
    elif same_actor_requires_human_review or normalized_actor_separation_status == "same_actor_human_review_required":
        packet_status = "blocked_same_actor_review_required"
        packet_block_reason = "same_actor_requires_human_review"
        packet_next_action = "human_review_required"
        handoff_status = "blocked_same_actor_review_required"
        handoff_transport = "local_file_handoff"
        handoff_next_action = "human_review_required"
        handoff_target = "human_operator"
    elif not decision_consumption_ready:
        if normalized_consumption_status in {"waiting_for_manual_chatgpt_json", "blocked"}:
            if normalized_consumption_block_reason == "insufficient_truth":
                packet_status = "insufficient_truth"
                packet_block_reason = "insufficient_truth"
                packet_next_action = "insufficient_truth"
                handoff_status = "insufficient_truth"
                handoff_transport = "unavailable"
                handoff_next_action = "insufficient_truth"
                handoff_target = "unavailable"
            else:
                packet_status = "blocked_waiting_for_valid_decision"
                packet_block_reason = "waiting_for_valid_decision"
                packet_next_action = "wait_for_valid_chatgpt_decision_json"
                handoff_status = "blocked_waiting_for_valid_decision"
                handoff_transport = "local_file_handoff"
                handoff_next_action = "wait_for_valid_chatgpt_decision_json"
                handoff_target = "local_decision_json"
        else:
            packet_status = "insufficient_truth"
            packet_block_reason = "insufficient_truth"
            packet_next_action = "insufficient_truth"
            handoff_status = "insufficient_truth"
            handoff_transport = "unavailable"
            handoff_next_action = "insufficient_truth"
            handoff_target = "unavailable"
    elif normalized_implementation_actor == "none":
        packet_status = "blocked_no_implementation_actor"
        packet_block_reason = "implementation_actor_missing"
        packet_next_action = "manual_set_implementation_actor"
        handoff_status = "blocked_no_implementation_actor"
        handoff_transport = "unavailable"
        handoff_next_action = "manual_set_implementation_actor"
        handoff_target = "unavailable"
    elif normalized_implementation_actor != "chatgpt_5_5_implementer":
        packet_status = "blocked_actor_not_chatgpt_implementer"
        packet_block_reason = "implementation_actor_not_chatgpt_implementer"
        packet_next_action = "route_to_selected_implementation_actor"
        handoff_status = "blocked_actor_not_chatgpt_implementer"
        handoff_transport = "unavailable"
        handoff_next_action = "route_to_selected_implementation_actor"
        handoff_target = "unavailable"
    elif not decision_requests_implementation:
        packet_status = "blocked_missing_inputs"
        packet_block_reason = "implementation_not_requested"
        packet_next_action = "manual_fix_required"
        handoff_status = "blocked_missing_inputs"
        handoff_transport = "local_file_handoff"
        handoff_next_action = "manual_fix_required"
        handoff_target = "local_decision_json"
    elif missing_inputs:
        packet_status = "blocked_missing_inputs"
        packet_block_reason = "packet_missing_inputs"
        packet_next_action = "manual_fix_required"
        handoff_status = "blocked_missing_inputs"
        handoff_transport = "local_file_handoff"
        handoff_next_action = "manual_fix_required"
        handoff_target = "local_decision_json"
    else:
        packet_status = "prepared_for_manual_handoff"
        packet_block_reason = "none"
        packet_next_action = "prepare_manual_handoff_packet"
        handoff_status = "prepared_for_manual_handoff"
        handoff_transport = "subscription_ui_manual_paste"
        handoff_next_action = "manual_paste_packet_into_chatgpt_implementer_ui"
        handoff_target = "chatgpt_subscription_ui"

    return {
        "project_browser_autonomous_chatgpt_implementation_packet_status": packet_status,
        "project_browser_autonomous_chatgpt_implementation_packet_block_reason": (
            packet_block_reason
        ),
        "project_browser_autonomous_chatgpt_implementation_packet_objective_summary": (
            normalized_objective_summary
        ),
        "project_browser_autonomous_chatgpt_implementation_packet_source_decision_status": (
            normalized_consumption_status
        ),
        "project_browser_autonomous_chatgpt_implementation_packet_source_decision": (
            normalized_source_decision
        ),
        "project_browser_autonomous_chatgpt_implementation_packet_implementation_actor": (
            normalized_implementation_actor
        ),
        "project_browser_autonomous_chatgpt_implementation_packet_implementation_mode": (
            normalized_implementation_mode
        ),
        "project_browser_autonomous_chatgpt_implementation_packet_implementation_output_kind": (
            normalized_implementation_output_kind
        ),
        "project_browser_autonomous_chatgpt_implementation_packet_allowed_files": (
            normalized_allowed_files
        ),
        "project_browser_autonomous_chatgpt_implementation_packet_forbidden_files": (
            normalized_forbidden_files
        ),
        "project_browser_autonomous_chatgpt_implementation_packet_required_constraints": (
            normalized_required_constraints
        ),
        "project_browser_autonomous_chatgpt_implementation_packet_forbidden_actions": (
            normalized_forbidden_actions
        ),
        "project_browser_autonomous_chatgpt_implementation_packet_expected_path": (
            expected_packet_path
        ),
        "project_browser_autonomous_chatgpt_implementation_packet_expected_response_path": (
            expected_response_path
        ),
        "project_browser_autonomous_chatgpt_implementation_packet_expected_patch_path": (
            expected_patch_path
        ),
        "project_browser_autonomous_chatgpt_implementation_packet_required_inputs": (
            required_inputs
        ),
        "project_browser_autonomous_chatgpt_implementation_packet_available_inputs": (
            _serialize_required_signals(available_inputs)
        ),
        "project_browser_autonomous_chatgpt_implementation_packet_missing_inputs": (
            missing_inputs
        ),
        "project_browser_autonomous_chatgpt_implementation_packet_next_action": (
            packet_next_action
        ),
        "project_browser_autonomous_chatgpt_implementation_packet_self_approval_policy": (
            "implementer_must_not_approve_own_output"
        ),
        "project_browser_autonomous_chatgpt_implementation_packet_review_before_commit_policy": (
            "chatgpt_judge_or_human_operator_must_review"
        ),
        "project_browser_autonomous_chatgpt_implementation_handoff_status": handoff_status,
        "project_browser_autonomous_chatgpt_implementation_handoff_transport": (
            handoff_transport
        ),
        "project_browser_autonomous_chatgpt_implementation_handoff_target": handoff_target,
        "project_browser_autonomous_chatgpt_implementation_handoff_output_kind": (
            normalized_implementation_output_kind
        ),
        "project_browser_autonomous_chatgpt_implementation_handoff_expected_packet_path": (
            expected_packet_path
        ),
        "project_browser_autonomous_chatgpt_implementation_handoff_expected_response_path": (
            expected_response_path
        ),
        "project_browser_autonomous_chatgpt_implementation_handoff_expected_patch_path": (
            expected_patch_path
        ),
        "project_browser_autonomous_chatgpt_implementation_handoff_requires_review_before_commit": (
            True
        ),
        "project_browser_autonomous_chatgpt_implementation_handoff_next_action": (
            handoff_next_action
        ),
        "project_browser_autonomous_chatgpt_implementation_handoff_runtime_posture": (
            [
                "metadata_only_packet_planning",
                "manual_handoff_only",
                "no_chatgpt_api_call",
                "no_browser_automation",
                "no_response_validation",
                "no_patch_generation_or_apply",
            ]
        ),
    }

def _build_project_browser_autonomous_chatgpt_implementation_response_state(
    *,
    implementation_packet_status: str,
    implementation_handoff_status: str,
    expected_output_kind: str,
    expected_response_path: str,
    expected_patch_path: str,
    allowed_files: list[str] | None,
    forbidden_files: list[str] | None,
    human_review_required: bool,
    rollback_required: bool,
) -> dict[str, Any]:
    patch_like_response_types = {
        "patch_plan",
        "unified_diff",
        "full_file_replacement",
        "mixed",
    }
    allowed_output_kinds = {
        "patch_plan",
        "unified_diff",
        "full_file_replacement",
        "manual_steps",
        "instructions_only",
        "none",
    }
    runtime_posture = [
        "metadata_only_response_validation",
        "local_file_read_only",
        "no_chatgpt_api_call",
        "no_browser_automation",
        "no_patch_write",
        "no_patch_apply",
        "no_repo_file_modification_from_response",
    ]

    normalized_packet_status = _normalize_text(
        implementation_packet_status,
        default="insufficient_truth",
    )
    normalized_handoff_status = _normalize_text(
        implementation_handoff_status,
        default="insufficient_truth",
    )
    normalized_expected_output_kind = _normalize_text(
        expected_output_kind,
        default="none",
    )
    if normalized_expected_output_kind not in allowed_output_kinds:
        normalized_expected_output_kind = "none"
    normalized_expected_response_path = _normalize_text(
        expected_response_path,
        default="/tmp/codex-local-runner-decision/chatgpt_implementation_response.md",
    )
    normalized_expected_patch_path = _normalize_text(
        expected_patch_path,
        default="/tmp/codex-local-runner-decision/chatgpt_implementation_patch.diff",
    )
    normalized_allowed_files = _normalize_string_list(allowed_files or [])
    normalized_forbidden_files = _normalize_string_list(forbidden_files or [])

    required_inputs = [
        "implementation_packet_status",
        "implementation_handoff_status",
        "expected_response_path",
        "expected_patch_path",
        "expected_output_kind",
    ]
    available_inputs: list[str] = []
    if normalized_packet_status:
        available_inputs.append("implementation_packet_status")
    if normalized_handoff_status:
        available_inputs.append("implementation_handoff_status")
    if normalized_expected_response_path:
        available_inputs.append("expected_response_path")
    if normalized_expected_patch_path:
        available_inputs.append("expected_patch_path")
    if normalized_expected_output_kind and normalized_expected_output_kind != "none":
        available_inputs.append("expected_output_kind")
    base_missing_inputs = [
        input_name for input_name in required_inputs if input_name not in set(available_inputs)
    ]

    def _normalize_repo_path(path_text: str) -> str:
        value = _normalize_text(path_text, default="")
        if not value:
            return ""
        value = value.replace("\\", "/")
        if value.startswith("a/") or value.startswith("b/"):
            value = value[2:]
        value = value.strip().strip("`").strip("\"")
        if value == "/dev/null":
            return ""
        return value

    def _path_matches_scope(candidate: str, scope_items: list[str]) -> bool:
        normalized_candidate = _normalize_repo_path(candidate)
        if not normalized_candidate:
            return False
        for scope_item in scope_items:
            normalized_scope = _normalize_repo_path(scope_item)
            if not normalized_scope:
                continue
            if normalized_candidate == normalized_scope:
                return True
            if normalized_candidate.startswith(normalized_scope.rstrip("/") + "/"):
                return True
        return False

    def _extract_touched_files(text: str) -> list[str]:
        touched: list[str] = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            normalized_path = ""
            if line.startswith("diff --git "):
                parts = line.split()
                if len(parts) >= 4:
                    normalized_path = _normalize_repo_path(parts[3])
            elif line.startswith("+++ "):
                normalized_path = _normalize_repo_path(line[4:].strip())
            elif line.startswith("*** Update File: "):
                normalized_path = _normalize_repo_path(
                    line[len("*** Update File: ") :]
                )
            elif line.startswith("*** Add File: "):
                normalized_path = _normalize_repo_path(line[len("*** Add File: ") :])
            elif line.startswith("*** Delete File: "):
                normalized_path = _normalize_repo_path(
                    line[len("*** Delete File: ") :]
                )
            if normalized_path:
                touched.append(normalized_path)
        return _serialize_required_signals(touched)

    status = "insufficient_truth"
    source_status = "insufficient_truth"
    block_reason = "insufficient_truth"
    next_action = "insufficient_truth"
    response_present = False
    patch_present = False
    response_type = "unknown"
    output_kind = "none"
    touched_files: list[str] = []
    forbidden_touched_files: list[str] = []
    unsafe_operation_flags: list[str] = []
    missing_inputs = _serialize_required_signals(base_missing_inputs)
    invalid_reasons: list[str] = []
    response_text = ""
    patch_text = ""

    if rollback_required:
        status = "blocked_rollback_required"
        source_status = "rollback_required"
        block_reason = "rollback_required"
        next_action = "rollback_required"
    elif human_review_required:
        status = "blocked_human_review_required"
        source_status = "human_review_required"
        block_reason = "human_review_required"
        next_action = "human_review_required"
    elif normalized_packet_status == "insufficient_truth" or normalized_handoff_status == "insufficient_truth":
        status = "insufficient_truth"
        source_status = "insufficient_truth"
        block_reason = "insufficient_truth"
        next_action = "insufficient_truth"
    elif (
        normalized_packet_status != "prepared_for_manual_handoff"
        or normalized_handoff_status != "prepared_for_manual_handoff"
    ):
        status = "blocked_missing_inputs"
        source_status = "prompt152_packet_handoff_not_prepared"
        block_reason = "prompt152_packet_handoff_not_prepared"
        next_action = "manual_fix_implementation_response"
        missing_inputs = _serialize_required_signals(
            [*missing_inputs, "prepared_prompt152_packet_handoff"]
        )
    elif missing_inputs:
        status = "blocked_missing_inputs"
        source_status = "missing_required_source_fields"
        block_reason = "missing_required_source_fields"
        next_action = "manual_fix_implementation_response"
    else:
        response_path = Path(normalized_expected_response_path)
        patch_path = Path(normalized_expected_patch_path)
        response_present = bool(response_path.exists())
        patch_present = bool(patch_path.exists())

        if not response_present and not patch_present:
            status = "waiting_for_manual_response"
            source_status = "response_missing"
            block_reason = "waiting_for_manual_response"
            next_action = "wait_for_chatgpt_implementation_response"
            response_type = "missing"
        else:
            unreadable_response = False
            unreadable_patch = False
            if response_present:
                try:
                    response_text = response_path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    unreadable_response = True
            if patch_present:
                try:
                    patch_text = patch_path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    unreadable_patch = True

            if unreadable_response or unreadable_patch:
                status = "blocked_unreadable_response"
                source_status = "response_unreadable"
                block_reason = (
                    "response_unreadable"
                    if unreadable_response
                    else "patch_unreadable"
                )
                next_action = "manual_fix_implementation_response"
                response_type = "unreadable"
            else:
                combined_text = "\n".join(
                    [text for text in [response_text, patch_text] if text]
                )
                combined_lower = combined_text.lower()
                response_text_lower = response_text.lower()
                patch_text_lower = patch_text.lower()

                has_unified_diff = bool(
                    "```diff" in response_text_lower
                    or "diff --git " in combined_lower
                    or "\n--- a/" in combined_text
                    or "\n+++ b/" in combined_text
                    or "*** update file: " in combined_lower
                    or "*** add file: " in combined_lower
                    or "*** delete file: " in combined_lower
                    or "@@" in combined_text
                )
                has_full_file_replacement = bool(
                    "full_file_replacement" in combined_lower
                    or "full file replacement" in combined_lower
                )
                has_patch_plan = bool(
                    "patch_plan" in combined_lower or "patch plan" in combined_lower
                )
                has_manual_steps = bool(
                    "manual_steps" in combined_lower or "manual steps" in combined_lower
                )
                has_instructions_only = bool(
                    "instructions_only" in combined_lower
                    or "instructions only" in combined_lower
                )

                if has_unified_diff and has_full_file_replacement:
                    response_type = "mixed"
                elif has_unified_diff:
                    response_type = "unified_diff"
                elif has_full_file_replacement:
                    response_type = "full_file_replacement"
                elif has_patch_plan:
                    response_type = "patch_plan"
                elif has_manual_steps:
                    response_type = "manual_steps"
                elif has_instructions_only:
                    response_type = "instructions_only"
                elif combined_text.strip():
                    response_type = "unknown"
                else:
                    response_type = "invalid"

                output_kind = (
                    response_type
                    if response_type in allowed_output_kinds
                    else "none"
                )
                touched_files = _extract_touched_files(combined_text)
                forbidden_touched_files = _serialize_required_signals(
                    [
                        path
                        for path in touched_files
                        if _path_matches_scope(path, normalized_forbidden_files)
                    ]
                )

                if "rm -rf" in combined_lower:
                    unsafe_operation_flags.append("dangerous_rm_rf")
                if "sudo " in combined_lower or "\nsudo\n" in combined_lower:
                    unsafe_operation_flags.append("dangerous_sudo")
                if "chmod 777" in combined_lower:
                    unsafe_operation_flags.append("dangerous_chmod_777")
                if "curl | sh" in combined_lower:
                    unsafe_operation_flags.append("dangerous_curl_pipe_sh")
                if "wget | sh" in combined_lower:
                    unsafe_operation_flags.append("dangerous_wget_pipe_sh")
                if "git push" in combined_lower:
                    unsafe_operation_flags.append("dangerous_git_push")
                if "git reset --hard" in combined_lower:
                    unsafe_operation_flags.append("dangerous_git_reset_hard")
                if "git clean -fd" in combined_lower:
                    unsafe_operation_flags.append("dangerous_git_clean_fd")
                if "gh pr merge" in combined_lower:
                    unsafe_operation_flags.append("dangerous_gh_pr_merge")
                if "merge_pull_request" in combined_lower:
                    unsafe_operation_flags.append("dangerous_merge_pull_request")
                if "create_pull_request" in combined_lower:
                    unsafe_operation_flags.append("dangerous_create_pull_request")
                sensitive_terms = ["secret", "token", "cookie", "credential"]
                mutation_terms = [
                    "set ",
                    "update ",
                    "replace ",
                    "change ",
                    "write ",
                    "export ",
                    "password",
                ]
                if any(term in combined_lower for term in sensitive_terms) and any(
                    term in combined_lower for term in mutation_terms
                ):
                    unsafe_operation_flags.append("credential_change_detected")
                unsafe_operation_flags = _serialize_required_signals(
                    unsafe_operation_flags
                )

                outside_allowed_files = _serialize_required_signals(
                    [
                        path
                        for path in touched_files
                        if normalized_allowed_files
                        and not _path_matches_scope(path, normalized_allowed_files)
                    ]
                )

                if response_type in {"invalid", "unknown", "mixed"}:
                    status = "blocked_invalid_response"
                    source_status = "response_readable"
                    block_reason = (
                        "response_type_unknown"
                        if response_type == "unknown"
                        else "response_invalid"
                    )
                    next_action = "manual_fix_implementation_response"
                    invalid_reasons.append(f"response_type:{response_type}")
                elif (
                    normalized_expected_output_kind != "none"
                    and output_kind != normalized_expected_output_kind
                ):
                    status = "blocked_output_kind_mismatch"
                    source_status = "response_readable"
                    block_reason = "output_kind_mismatch"
                    next_action = "manual_fix_implementation_response"
                    invalid_reasons.append(
                        f"expected_output_kind:{normalized_expected_output_kind}"
                    )
                    invalid_reasons.append(f"actual_output_kind:{output_kind}")
                elif response_type in patch_like_response_types and not touched_files:
                    status = "insufficient_truth"
                    source_status = "response_readable"
                    block_reason = "patch_like_response_missing_touched_files"
                    next_action = "insufficient_truth"
                    missing_inputs = _serialize_required_signals(
                        [*missing_inputs, "touched_files"]
                    )
                elif response_type in patch_like_response_types and not normalized_allowed_files:
                    status = "insufficient_truth"
                    source_status = "response_readable"
                    block_reason = "allowed_files_missing_for_patch_like_response"
                    next_action = "insufficient_truth"
                    missing_inputs = _serialize_required_signals(
                        [*missing_inputs, "allowed_files"]
                    )
                elif forbidden_touched_files or outside_allowed_files:
                    status = "blocked_forbidden_files"
                    source_status = "response_readable"
                    block_reason = "forbidden_or_out_of_scope_files_touched"
                    next_action = "manual_fix_implementation_response"
                    if forbidden_touched_files:
                        invalid_reasons.append("forbidden_files_touched")
                    if outside_allowed_files:
                        invalid_reasons.append("outside_allowed_files_touched")
                elif unsafe_operation_flags:
                    status = "blocked_unsafe_operations"
                    source_status = "response_readable"
                    block_reason = "unsafe_operations_detected"
                    next_action = "manual_fix_implementation_response"
                    invalid_reasons.append("unsafe_operations_detected")
                else:
                    status = "valid_metadata_only"
                    source_status = "response_readable"
                    block_reason = "none"
                    next_action = "prepare_safe_patch_apply_gate_later"

                invalid_reasons = _serialize_required_signals(invalid_reasons)

    patch_candidate_status = "waiting"
    patch_candidate_source_status = source_status
    patch_candidate_block_reason = block_reason
    patch_candidate_next_action = next_action
    if status == "insufficient_truth":
        patch_candidate_status = "insufficient_truth"
        patch_candidate_next_action = "insufficient_truth"
    elif status == "waiting_for_manual_response":
        patch_candidate_status = "waiting"
        patch_candidate_next_action = "wait_for_chatgpt_implementation_response"
    elif status == "valid_metadata_only":
        if response_type in {"unified_diff", "full_file_replacement"}:
            patch_candidate_status = "candidate_ready_for_later_gate"
            patch_candidate_block_reason = "none"
            patch_candidate_next_action = "prepare_safe_patch_apply_gate_later"
        elif response_type in {"patch_plan", "manual_steps", "instructions_only"}:
            patch_candidate_status = "waiting"
            patch_candidate_block_reason = "response_not_patch_ready"
            patch_candidate_next_action = "wait_for_chatgpt_implementation_response"
        else:
            patch_candidate_status = "blocked"
            patch_candidate_block_reason = "response_not_patch_ready"
            patch_candidate_next_action = "manual_fix_implementation_response"
    else:
        patch_candidate_status = "blocked"

    return {
        "project_browser_autonomous_chatgpt_implementation_response_status": status,
        "project_browser_autonomous_chatgpt_implementation_response_source_status": (
            source_status
        ),
        "project_browser_autonomous_chatgpt_implementation_response_block_reason": (
            block_reason
        ),
        "project_browser_autonomous_chatgpt_implementation_response_expected_response_path": (
            normalized_expected_response_path
        ),
        "project_browser_autonomous_chatgpt_implementation_response_expected_patch_path": (
            normalized_expected_patch_path
        ),
        "project_browser_autonomous_chatgpt_implementation_response_response_present": (
            bool(response_present)
        ),
        "project_browser_autonomous_chatgpt_implementation_response_patch_present": (
            bool(patch_present)
        ),
        "project_browser_autonomous_chatgpt_implementation_response_response_type": (
            response_type
        ),
        "project_browser_autonomous_chatgpt_implementation_response_output_kind": (
            output_kind
        ),
        "project_browser_autonomous_chatgpt_implementation_response_allowed_files": (
            normalized_allowed_files
        ),
        "project_browser_autonomous_chatgpt_implementation_response_forbidden_files": (
            normalized_forbidden_files
        ),
        "project_browser_autonomous_chatgpt_implementation_response_touched_files": (
            touched_files
        ),
        "project_browser_autonomous_chatgpt_implementation_response_forbidden_touched_files": (
            forbidden_touched_files
        ),
        "project_browser_autonomous_chatgpt_implementation_response_unsafe_operation_flags": (
            unsafe_operation_flags
        ),
        "project_browser_autonomous_chatgpt_implementation_response_missing_inputs": (
            missing_inputs
        ),
        "project_browser_autonomous_chatgpt_implementation_response_invalid_reasons": (
            invalid_reasons
        ),
        "project_browser_autonomous_chatgpt_implementation_response_next_action": (
            next_action
        ),
        "project_browser_autonomous_chatgpt_implementation_response_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_chatgpt_implementation_response_validation_status": (
            status
        ),
        "project_browser_autonomous_chatgpt_implementation_response_validation_source_status": (
            source_status
        ),
        "project_browser_autonomous_chatgpt_implementation_response_validation_block_reason": (
            block_reason
        ),
        "project_browser_autonomous_chatgpt_implementation_response_validation_missing_inputs": (
            missing_inputs
        ),
        "project_browser_autonomous_chatgpt_implementation_response_validation_invalid_reasons": (
            invalid_reasons
        ),
        "project_browser_autonomous_chatgpt_implementation_response_validation_next_action": (
            next_action
        ),
        "project_browser_autonomous_chatgpt_implementation_response_validation_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_chatgpt_patch_candidate_status": (
            patch_candidate_status
        ),
        "project_browser_autonomous_chatgpt_patch_candidate_source_status": (
            patch_candidate_source_status
        ),
        "project_browser_autonomous_chatgpt_patch_candidate_block_reason": (
            patch_candidate_block_reason
        ),
        "project_browser_autonomous_chatgpt_patch_candidate_expected_patch_path": (
            normalized_expected_patch_path
        ),
        "project_browser_autonomous_chatgpt_patch_candidate_response_type": (
            response_type
        ),
        "project_browser_autonomous_chatgpt_patch_candidate_output_kind": output_kind,
        "project_browser_autonomous_chatgpt_patch_candidate_touched_files": (
            touched_files
        ),
        "project_browser_autonomous_chatgpt_patch_candidate_forbidden_touched_files": (
            forbidden_touched_files
        ),
        "project_browser_autonomous_chatgpt_patch_candidate_unsafe_operation_flags": (
            unsafe_operation_flags
        ),
        "project_browser_autonomous_chatgpt_patch_candidate_missing_inputs": (
            missing_inputs
        ),
        "project_browser_autonomous_chatgpt_patch_candidate_invalid_reasons": (
            invalid_reasons
        ),
        "project_browser_autonomous_chatgpt_patch_candidate_next_action": (
            patch_candidate_next_action
        ),
        "project_browser_autonomous_chatgpt_patch_candidate_runtime_posture": (
            [
                "metadata_only_patch_candidate",
                "no_patch_write",
                "no_patch_apply",
                "no_git_apply",
            ]
        ),
    }

def _build_project_browser_autonomous_fix_prompt_readiness_state(
    *,
    expected_patch_path: str,
    dry_run_status: str,
    dry_run_passed: bool,
    dry_run_failed: bool,
    dry_run_stderr_excerpt: str,
    apply_status: str,
    apply_passed: bool,
    apply_failed: bool,
    apply_stderr_excerpt: str,
    validation_status: str,
    validation_passed: bool,
    validation_failed: bool,
    validation_missing_inputs: list[str] | None,
    py_compile_exit_code: int,
    py_compile_stderr_excerpt: str,
    touched_files: list[str] | None,
    changed_files_after_apply: list[str] | None,
    unexpected_changed_files_after_apply: list[str] | None,
    forbidden_changed_files_after_apply: list[str] | None,
    metadata_consistency_passed: bool,
    metadata_consistency_failed: bool,
    human_review_required: bool,
    rollback_required: bool,
    cycle_handoff_available: bool = False,
    cycle_handoff_prompt_kind: str = "none",
    cycle_handoff_reason: str = "",
) -> dict[str, Any]:
    allowed_statuses = {
        "ready_to_generate_fix_prompt",
        "cycle_handoff_fix_ready",
        "blocked_validation_passed",
        "blocked_insufficient_truth",
        "blocked_human_review_required",
        "blocked_rollback_required",
        "blocked_missing_failure_truth",
        "blocked_no_actionable_failure",
        "blocked_forbidden_changes",
        "blocked_unexpected_changes",
        "blocked_metadata_inconsistency",
        "ready_for_manual_fix",
        "insufficient_truth",
    }
    allowed_failure_kinds = {
        "validation_failed",
        "py_compile_failed",
        "dry_run_failed",
        "apply_failed",
        "changed_file_mismatch",
        "forbidden_changes",
        "unexpected_changes",
        "metadata_inconsistency",
        "missing_truth",
        "human_review_required",
        "rollback_required",
        "no_actionable_failure",
        "none",
    }
    allowed_next_actions = {
        "generate_fix_prompt_later",
        "generate_fix_prompt",
        "wait_for_validation_failure",
        "wait_for_more_truth",
        "manual_review_required",
        "rollback_required",
        "manual_fix_required",
        "no_fix_needed",
        "insufficient_truth",
    }
    runtime_posture = [
        "metadata_only_fix_prompt_readiness",
        "no_fix_prompt_generation",
        "no_prompt_file_write",
        "no_model_invocation",
        "no_browser_automation",
        "no_rollback_execution",
        "no_git_mutation",
    ]

    normalized_expected_patch_path = _normalize_text(expected_patch_path, default="")
    normalized_dry_run_status = _normalize_text(dry_run_status, default="insufficient_truth")
    normalized_apply_status = _normalize_text(apply_status, default="insufficient_truth")
    normalized_validation_status = _normalize_text(
        validation_status,
        default="insufficient_truth",
    )
    normalized_validation_missing_inputs = _normalize_string_list(validation_missing_inputs or [])
    normalized_py_compile_stderr = _normalize_text(py_compile_stderr_excerpt, default="")
    normalized_dry_run_stderr = _normalize_text(dry_run_stderr_excerpt, default="")
    normalized_apply_stderr = _normalize_text(apply_stderr_excerpt, default="")
    normalized_touched_files = _normalize_string_list(touched_files or [])
    normalized_changed_files = _normalize_string_list(changed_files_after_apply or [])
    normalized_unexpected_changed_files = _normalize_string_list(
        unexpected_changed_files_after_apply or []
    )
    normalized_forbidden_changed_files = _normalize_string_list(
        forbidden_changed_files_after_apply or []
    )
    normalized_py_compile_exit_code = int(_as_int(py_compile_exit_code, default=-1))
    metadata_passed = bool(metadata_consistency_passed)
    metadata_failed = bool(metadata_consistency_failed)
    normalized_cycle_handoff_prompt_kind = _normalize_text(
        cycle_handoff_prompt_kind,
        default="none",
    )
    normalized_cycle_handoff_reason = _normalize_text(cycle_handoff_reason, default="")
    cycle_handoff_consumed = bool(cycle_handoff_available)
    cycle_handoff_acknowledged = bool(
        cycle_handoff_consumed
        and normalized_cycle_handoff_prompt_kind == "fix"
        and normalized_cycle_handoff_reason == "validation_failed"
    )
    cycle_handoff_readiness_source = (
        "cycle_failed_validation" if cycle_handoff_acknowledged else ""
    )
    cycle_handoff_block_reason = ""
    if cycle_handoff_consumed and not cycle_handoff_acknowledged:
        if normalized_cycle_handoff_prompt_kind != "fix":
            cycle_handoff_block_reason = "mismatched_cycle_handoff_prompt_kind"
        elif normalized_cycle_handoff_reason != "validation_failed":
            cycle_handoff_block_reason = "mismatched_cycle_handoff_reason"
    cycle_handoff_re_evaluation_attempted = False
    cycle_handoff_re_evaluation_allowed = False
    cycle_handoff_re_evaluation_block_reason = ""
    cycle_handoff_re_evaluated_status = ""
    cycle_handoff_re_evaluated_ready_to_generate = False
    cycle_handoff_re_evaluated_generation_allowed = False
    cycle_handoff_re_evaluation_safety_gates_passed = False
    cycle_handoff_re_evaluation_source = ""

    target_file_candidates: list[str] = []
    for file_path in [*normalized_changed_files, *normalized_touched_files]:
        if file_path and file_path not in target_file_candidates:
            target_file_candidates.append(file_path)
    fix_target_files = [
        file_path
        for file_path in target_file_candidates
        if file_path not in normalized_forbidden_changed_files
        and file_path not in normalized_unexpected_changed_files
    ]

    status = "insufficient_truth"
    source_status = "insufficient_truth"
    block_reason = "insufficient_truth"
    failure_kind = "missing_truth"
    failure_source = "unknown"
    actionable_failure = False
    ready_to_generate = False
    generation_allowed = False
    generation_blocked = True
    next_action = "insufficient_truth"
    prompt_generation_attempted = False
    prompt_generated = False
    prompt_path = ""
    missing_inputs = list(normalized_validation_missing_inputs)

    if rollback_required:
        status = "blocked_rollback_required"
        source_status = "rollback_posture_required"
        block_reason = "rollback_required"
        failure_kind = "rollback_required"
        failure_source = "prompt157_post_apply_validation"
        next_action = "rollback_required"
    elif human_review_required:
        status = "blocked_human_review_required"
        source_status = "human_review_posture_required"
        block_reason = "human_review_required"
        failure_kind = "human_review_required"
        failure_source = "prompt157_post_apply_validation"
        next_action = "manual_review_required"
    elif normalized_forbidden_changed_files:
        status = "blocked_forbidden_changes"
        source_status = "forbidden_changes_detected"
        block_reason = "forbidden_changes_detected"
        failure_kind = "forbidden_changes"
        failure_source = "prompt157_changed_file_consistency"
        next_action = "manual_review_required"
    elif normalized_unexpected_changed_files:
        status = "blocked_unexpected_changes"
        source_status = "unexpected_changes_detected"
        block_reason = "unexpected_changes_detected"
        failure_kind = "unexpected_changes"
        failure_source = "prompt157_changed_file_consistency"
        next_action = "manual_review_required"
    elif metadata_failed:
        status = "blocked_metadata_inconsistency"
        source_status = "metadata_inconsistency_detected"
        block_reason = "metadata_consistency_failed"
        failure_kind = "metadata_inconsistency"
        failure_source = "prompt157_metadata_consistency"
        next_action = "wait_for_more_truth"
    elif validation_passed:
        status = "blocked_validation_passed"
        source_status = "validation_passed"
        block_reason = "validation_passed"
        failure_kind = "none"
        failure_source = "prompt157_post_apply_validation"
        next_action = "no_fix_needed"
    elif (
        normalized_validation_status == "insufficient_truth"
        or (not validation_failed and not validation_passed)
    ):
        status = "blocked_insufficient_truth"
        source_status = "validation_truth_unavailable"
        block_reason = "insufficient_truth"
        failure_kind = "missing_truth"
        failure_source = "prompt157_post_apply_validation"
        next_action = "wait_for_more_truth"
        if not missing_inputs:
            missing_inputs.append("post_apply_validation_result")
    elif validation_failed:
        source_status = "validation_failed"
        block_reason = "validation_failed"
        failure_kind = "validation_failed"
        failure_source = "prompt157_post_apply_validation"

        actionable_details_available = False
        if normalized_py_compile_exit_code not in {-1, 0}:
            failure_kind = "py_compile_failed"
            failure_source = "prompt157_py_compile"
            actionable_details_available = bool(normalized_py_compile_stderr)
        elif normalized_validation_status == "blocked_changed_file_mismatch":
            failure_kind = "changed_file_mismatch"
            failure_source = "prompt157_changed_file_consistency"
            actionable_details_available = bool(
                normalized_changed_files or normalized_touched_files
            )
        elif apply_failed or normalized_apply_status in {
            "apply_failed",
            "blocked_post_apply_mutation_mismatch",
            "blocked_no_dry_run_pass",
        }:
            failure_kind = "apply_failed"
            failure_source = "prompt156_real_apply"
            actionable_details_available = bool(normalized_apply_stderr)
        elif dry_run_failed or normalized_dry_run_status == "dry_run_failed":
            failure_kind = "dry_run_failed"
            failure_source = "prompt155_dry_run"
            actionable_details_available = bool(normalized_dry_run_stderr)

        actionable_failure = bool(
            actionable_details_available or bool(fix_target_files)
        )
        if actionable_failure and fix_target_files:
            status = "ready_to_generate_fix_prompt"
            ready_to_generate = True
            generation_allowed = True
            generation_blocked = False
            next_action = "generate_fix_prompt_later"
        elif actionable_failure and not fix_target_files:
            status = "blocked_missing_failure_truth"
            source_status = "fix_target_files_unavailable"
            block_reason = "fix_target_files_unavailable"
            failure_kind = "missing_truth"
            failure_source = "prompt157_changed_file_consistency"
            actionable_failure = False
            next_action = "wait_for_more_truth"
            missing_inputs.append("fix_target_files")
        else:
            status = "blocked_no_actionable_failure"
            source_status = "failure_not_actionable"
            block_reason = "no_actionable_failure"
            failure_kind = "no_actionable_failure"
            next_action = "manual_fix_required"
    else:
        status = "insufficient_truth"
        source_status = "readiness_unresolved"
        block_reason = "insufficient_truth"
        failure_kind = "missing_truth"
        failure_source = "unknown"
        next_action = "insufficient_truth"
        if not missing_inputs:
            missing_inputs.append("validation_failure_classification")

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if failure_kind not in allowed_failure_kinds:
        failure_kind = "missing_truth"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"

    if status != "ready_to_generate_fix_prompt":
        actionable_failure = False
        ready_to_generate = False
        generation_allowed = False
        generation_blocked = True
    if cycle_handoff_acknowledged:
        cycle_handoff_re_evaluation_attempted = True
        cycle_handoff_re_evaluation_source = "cycle_failed_validation"
        cycle_handoff_re_evaluation_safety_gates_passed = bool(
            status == "ready_to_generate_fix_prompt"
            and ready_to_generate
            and generation_allowed
            and validation_failed
            and not validation_passed
            and not rollback_required
            and not human_review_required
            and not metadata_failed
            and not normalized_forbidden_changed_files
            and not normalized_unexpected_changed_files
            and bool(fix_target_files)
        )
        if cycle_handoff_re_evaluation_safety_gates_passed:
            cycle_handoff_re_evaluation_allowed = True
            status = "cycle_handoff_fix_ready"
            next_action = "generate_fix_prompt"
            ready_to_generate = True
            generation_allowed = True
            generation_blocked = False
            cycle_handoff_re_evaluated_status = status
            cycle_handoff_re_evaluated_ready_to_generate = True
            cycle_handoff_re_evaluated_generation_allowed = True
        elif human_review_required:
            cycle_handoff_re_evaluation_block_reason = "blocked_human_review_required"
        elif normalized_validation_status == "insufficient_truth" or (
            not validation_failed and not validation_passed
        ):
            cycle_handoff_re_evaluation_block_reason = "blocked_missing_truth"
        elif status in {
            "blocked_rollback_required",
            "blocked_forbidden_changes",
            "blocked_unexpected_changes",
            "blocked_metadata_inconsistency",
            "blocked_validation_passed",
            "blocked_missing_failure_truth",
            "blocked_no_actionable_failure",
            "insufficient_truth",
            "blocked_insufficient_truth",
        }:
            cycle_handoff_re_evaluation_block_reason = (
                "blocked_existing_readiness_safety_gate"
            )
        else:
            cycle_handoff_re_evaluation_block_reason = (
                "blocked_insufficient_re_evaluation_truth"
            )
    else:
        if cycle_handoff_consumed:
            cycle_handoff_re_evaluation_attempted = True
        if cycle_handoff_consumed and normalized_cycle_handoff_prompt_kind != "fix":
            cycle_handoff_re_evaluation_block_reason = (
                "blocked_mismatched_cycle_handoff_prompt_kind"
            )
        elif cycle_handoff_consumed and normalized_cycle_handoff_reason != "validation_failed":
            cycle_handoff_re_evaluation_block_reason = (
                "blocked_mismatched_cycle_handoff_reason"
            )
        elif cycle_handoff_consumed or not cycle_handoff_acknowledged:
            cycle_handoff_re_evaluation_block_reason = "blocked_handoff_not_acknowledged"

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if failure_kind not in allowed_failure_kinds:
        failure_kind = "missing_truth"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"

    return {
        "project_browser_autonomous_fix_prompt_readiness_status": status,
        "project_browser_autonomous_fix_prompt_readiness_source_status": source_status,
        "project_browser_autonomous_fix_prompt_readiness_block_reason": block_reason,
        "project_browser_autonomous_fix_prompt_readiness_failure_kind": failure_kind,
        "project_browser_autonomous_fix_prompt_readiness_failure_source": failure_source,
        "project_browser_autonomous_fix_prompt_readiness_actionable_failure": bool(
            actionable_failure
        ),
        "project_browser_autonomous_fix_prompt_readiness_ready_to_generate": bool(
            ready_to_generate
        ),
        "project_browser_autonomous_fix_prompt_readiness_generation_allowed": bool(
            generation_allowed
        ),
        "project_browser_autonomous_fix_prompt_readiness_generation_blocked": bool(
            generation_blocked
        ),
        "project_browser_autonomous_fix_prompt_readiness_prompt_generation_attempted": bool(
            prompt_generation_attempted
        ),
        "project_browser_autonomous_fix_prompt_readiness_prompt_generated": bool(
            prompt_generated
        ),
        "project_browser_autonomous_fix_prompt_readiness_prompt_path": prompt_path,
        "project_browser_autonomous_fix_prompt_readiness_fix_target_files": fix_target_files,
        "project_browser_autonomous_fix_prompt_readiness_changed_files_after_apply": (
            normalized_changed_files
        ),
        "project_browser_autonomous_fix_prompt_readiness_unexpected_changed_files_after_apply": (
            normalized_unexpected_changed_files
        ),
        "project_browser_autonomous_fix_prompt_readiness_forbidden_changed_files_after_apply": (
            normalized_forbidden_changed_files
        ),
        "project_browser_autonomous_fix_prompt_readiness_validation_status": (
            normalized_validation_status
        ),
        "project_browser_autonomous_fix_prompt_readiness_validation_passed": bool(
            validation_passed
        ),
        "project_browser_autonomous_fix_prompt_readiness_validation_failed": bool(
            validation_failed
        ),
        "project_browser_autonomous_fix_prompt_readiness_validation_missing_inputs": (
            normalized_validation_missing_inputs
        ),
        "project_browser_autonomous_fix_prompt_readiness_py_compile_exit_code": int(
            normalized_py_compile_exit_code
        ),
        "project_browser_autonomous_fix_prompt_readiness_py_compile_stderr_excerpt": (
            normalized_py_compile_stderr
        ),
        "project_browser_autonomous_fix_prompt_readiness_apply_status": (
            normalized_apply_status
        ),
        "project_browser_autonomous_fix_prompt_readiness_apply_passed": bool(apply_passed),
        "project_browser_autonomous_fix_prompt_readiness_apply_failed": bool(apply_failed),
        "project_browser_autonomous_fix_prompt_readiness_dry_run_status": (
            normalized_dry_run_status
        ),
        "project_browser_autonomous_fix_prompt_readiness_dry_run_passed": bool(dry_run_passed),
        "project_browser_autonomous_fix_prompt_readiness_dry_run_failed": bool(dry_run_failed),
        "project_browser_autonomous_fix_prompt_readiness_metadata_consistency_passed": bool(
            metadata_passed
        ),
        "project_browser_autonomous_fix_prompt_readiness_metadata_consistency_failed": bool(
            metadata_failed
        ),
        "project_browser_autonomous_fix_prompt_readiness_human_review_required": bool(
            human_review_required
        ),
        "project_browser_autonomous_fix_prompt_readiness_rollback_required": bool(
            rollback_required
        ),
        "project_browser_autonomous_fix_prompt_readiness_next_action": next_action,
        "project_browser_autonomous_fix_prompt_readiness_runtime_posture": runtime_posture,
        "project_browser_autonomous_fix_prompt_readiness_missing_inputs": (
            _serialize_required_signals(missing_inputs)
        ),
        "project_browser_autonomous_fix_prompt_readiness_expected_patch_path": (
            normalized_expected_patch_path
        ),
        "project_browser_autonomous_fix_prompt_readiness_cycle_handoff_consumed": bool(
            cycle_handoff_consumed
        ),
        "project_browser_autonomous_fix_prompt_readiness_cycle_handoff_acknowledged": bool(
            cycle_handoff_acknowledged
        ),
        "project_browser_autonomous_fix_prompt_readiness_cycle_handoff_prompt_kind": (
            normalized_cycle_handoff_prompt_kind
        ),
        "project_browser_autonomous_fix_prompt_readiness_cycle_handoff_reason": (
            normalized_cycle_handoff_reason
        ),
        "project_browser_autonomous_fix_prompt_readiness_cycle_handoff_block_reason": (
            cycle_handoff_block_reason
        ),
        "project_browser_autonomous_fix_prompt_readiness_cycle_handoff_readiness_source": (
            cycle_handoff_readiness_source
        ),
        "project_browser_autonomous_fix_prompt_readiness_cycle_handoff_re_evaluation_attempted": bool(
            cycle_handoff_re_evaluation_attempted
        ),
        "project_browser_autonomous_fix_prompt_readiness_cycle_handoff_re_evaluation_allowed": bool(
            cycle_handoff_re_evaluation_allowed
        ),
        "project_browser_autonomous_fix_prompt_readiness_cycle_handoff_re_evaluation_block_reason": (
            cycle_handoff_re_evaluation_block_reason
        ),
        "project_browser_autonomous_fix_prompt_readiness_cycle_handoff_re_evaluated_status": (
            cycle_handoff_re_evaluated_status
        ),
        "project_browser_autonomous_fix_prompt_readiness_cycle_handoff_re_evaluated_ready_to_generate": bool(
            cycle_handoff_re_evaluated_ready_to_generate
        ),
        "project_browser_autonomous_fix_prompt_readiness_cycle_handoff_re_evaluated_generation_allowed": bool(
            cycle_handoff_re_evaluated_generation_allowed
        ),
        "project_browser_autonomous_fix_prompt_readiness_cycle_handoff_re_evaluation_safety_gates_passed": bool(
            cycle_handoff_re_evaluation_safety_gates_passed
        ),
        "project_browser_autonomous_fix_prompt_readiness_cycle_handoff_re_evaluation_source": (
            cycle_handoff_re_evaluation_source
        ),
    }

def _build_project_browser_autonomous_fix_prompt_generation_state(
    *,
    repository_path: str,
    readiness_status: str,
    readiness_generation_allowed: bool,
    readiness_ready_to_generate: bool,
    actionable_failure: bool,
    failure_kind: str,
    failure_source: str,
    target_files: list[str] | None,
    changed_files_after_apply: list[str] | None,
    unexpected_changed_files_after_apply: list[str] | None,
    forbidden_changed_files_after_apply: list[str] | None,
    validation_status: str,
    validation_passed: bool,
    validation_failed: bool,
    validation_missing_inputs: list[str] | None,
    py_compile_stderr_excerpt: str,
    apply_stderr_excerpt: str,
    dry_run_stderr_excerpt: str,
    rollback_required: bool,
    human_review_required: bool,
    validation_commands: list[str] | None,
    cycle_handoff_generation_input_available: bool = False,
    cycle_handoff_generation_input_consumed: bool = False,
    cycle_handoff_generation_input_kind: str = "none",
    cycle_handoff_generation_input_status: str = "",
    cycle_handoff_generation_input_source: str = "",
    cycle_handoff_generation_input_block_reason: str = "",
) -> dict[str, Any]:
    allowed_statuses = {
        "prompt_generated",
        "blocked_not_ready",
        "blocked_generation_not_allowed",
        "blocked_insufficient_truth",
        "blocked_human_review_required",
        "blocked_rollback_required",
        "blocked_missing_target_files",
        "blocked_missing_failure_detail",
        "blocked_handoff_path_invalid",
        "blocked_handoff_write_failed",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "run_codex_with_generated_fix_prompt_later",
        "generate_fix_prompt",
        "wait_for_more_truth",
        "manual_review_required",
        "rollback_required",
        "manual_fix_required",
        "no_fix_needed",
        "insufficient_truth",
    }
    handoff_path = "/tmp/codex-local-runner-decision/generated_fix_prompt.txt"
    runtime_posture = [
        "bounded_fix_prompt_generation",
        "metadata_and_prompt_text_only",
        "no_prompt_execution",
        "no_external_model_invocation",
        "no_patch_generation",
        "no_patch_apply",
        "no_git_mutation",
    ]
    non_goals = [
        "Do not invoke Codex/ChatGPT/browser automation/external models.",
        "Do not generate or apply patches.",
        "Do not execute rollback, commit, push, PR, CI, merge, or loops.",
        "Do not change unrelated Prompt154-Prompt161 semantics.",
    ]
    safety_constraints = [
        "Keep changes minimal and scoped to target files.",
        "Preserve Prompt154-Prompt161 contract fields and safety gates.",
        "Use only bounded local validation commands.",
        "Do not mutate git or remote state.",
    ]

    normalized_repository_path = _normalize_text(repository_path, default="")
    normalized_readiness_status = _normalize_text(
        readiness_status,
        default="insufficient_truth",
    )
    normalized_failure_kind = _normalize_text(failure_kind, default="none")
    normalized_failure_source = _normalize_text(failure_source, default="unknown")
    normalized_target_files = _normalize_string_list(target_files or [])
    normalized_changed_files = _normalize_string_list(changed_files_after_apply or [])
    normalized_unexpected_files = _normalize_string_list(
        unexpected_changed_files_after_apply or []
    )
    normalized_forbidden_files = _normalize_string_list(
        forbidden_changed_files_after_apply or []
    )
    normalized_validation_status = _normalize_text(
        validation_status,
        default="insufficient_truth",
    )
    normalized_validation_missing_inputs = _normalize_string_list(validation_missing_inputs or [])
    normalized_validation_commands = _normalize_string_list(validation_commands or [])
    normalized_cycle_handoff_generation_input_kind = _normalize_text(
        cycle_handoff_generation_input_kind,
        default="none",
    )
    normalized_cycle_handoff_generation_input_status = _normalize_text(
        cycle_handoff_generation_input_status,
        default="",
    )
    normalized_cycle_handoff_generation_input_source = _normalize_text(
        cycle_handoff_generation_input_source,
        default="",
    )
    normalized_cycle_handoff_generation_input_block_reason = _normalize_text(
        cycle_handoff_generation_input_block_reason,
        default="",
    )
    computed_cycle_handoff_generation_input_available = bool(
        cycle_handoff_generation_input_available
    )
    computed_cycle_handoff_generation_input_consumed = bool(
        cycle_handoff_generation_input_consumed
    )

    stderr_excerpt_candidates = _normalize_string_list(
        [
            _normalize_text(py_compile_stderr_excerpt, default=""),
            _normalize_text(apply_stderr_excerpt, default=""),
            _normalize_text(dry_run_stderr_excerpt, default=""),
        ]
    )
    failure_detail_excerpt = ""
    if stderr_excerpt_candidates:
        excerpt_text = stderr_excerpt_candidates[0]
        failure_detail_excerpt = excerpt_text[:600]

    status = "insufficient_truth"
    source_status = "insufficient_truth"
    block_reason = "insufficient_truth"
    generation_allowed = False
    generation_attempted = False
    generation_completed = False
    prompt_generated = False
    prompt_kind = "none"
    prompt_body = ""
    prompt_summary = ""
    prompt_handoff_write_attempted = False
    prompt_handoff_write_completed = False
    prompt_handoff_write_failed = False
    next_action = "insufficient_truth"
    missing_inputs = list(normalized_validation_missing_inputs)

    prompt_handoff_path = handoff_path
    handoff_path_obj = Path(prompt_handoff_path)
    prompt_handoff_path_is_exact = prompt_handoff_path == handoff_path
    prompt_handoff_path_parent_exists = handoff_path_obj.parent.exists()
    prompt_handoff_path_is_symlink = handoff_path_obj.is_symlink()

    if rollback_required:
        status = "blocked_rollback_required"
        source_status = "rollback_posture_required"
        block_reason = "rollback_required"
        next_action = "rollback_required"
    elif human_review_required:
        status = "blocked_human_review_required"
        source_status = "human_review_required"
        block_reason = "human_review_required"
        next_action = "manual_review_required"
    elif normalized_forbidden_files or normalized_unexpected_files:
        status = "blocked_generation_not_allowed"
        source_status = "unsafe_changed_files_detected"
        block_reason = (
            "forbidden_changed_files_detected"
            if normalized_forbidden_files
            else "unexpected_changed_files_detected"
        )
        next_action = "manual_review_required"
    elif normalized_readiness_status in {"blocked_validation_passed"}:
        status = "blocked_not_ready"
        source_status = "readiness_no_fix_needed"
        block_reason = "validation_passed"
        next_action = "no_fix_needed"
    elif normalized_readiness_status in {"insufficient_truth", "blocked_insufficient_truth"}:
        status = "blocked_insufficient_truth"
        source_status = "readiness_insufficient_truth"
        block_reason = "insufficient_truth"
        next_action = "wait_for_more_truth"
        if not missing_inputs:
            missing_inputs.append("fix_prompt_readiness_truth")
    elif normalized_readiness_status not in {
        "ready_to_generate_fix_prompt",
        "cycle_handoff_fix_ready",
    }:
        status = "blocked_not_ready"
        source_status = "readiness_not_ready"
        block_reason = f"readiness_status:{normalized_readiness_status or 'unknown'}"
        next_action = "wait_for_more_truth"
    elif not readiness_generation_allowed or not readiness_ready_to_generate:
        status = "blocked_generation_not_allowed"
        source_status = "readiness_generation_not_allowed"
        block_reason = "readiness_generation_not_allowed"
        next_action = "wait_for_more_truth"
    elif not actionable_failure:
        status = "blocked_generation_not_allowed"
        source_status = "failure_not_actionable"
        block_reason = "actionable_failure_false"
        next_action = "manual_fix_required"
    elif normalized_failure_kind in {"none", "", "missing_truth"}:
        status = "blocked_missing_failure_detail"
        source_status = "failure_kind_missing"
        block_reason = "failure_kind_missing"
        next_action = "wait_for_more_truth"
        if not missing_inputs:
            missing_inputs.append("failure_kind")
    elif not normalized_target_files:
        status = "blocked_missing_target_files"
        source_status = "target_files_missing"
        block_reason = "safe_target_files_missing"
        next_action = "manual_fix_required"
        if "target_files" not in missing_inputs:
            missing_inputs.append("target_files")
    elif not validation_failed:
        status = "blocked_not_ready"
        source_status = "validation_not_failed"
        block_reason = "validation_not_failed"
        next_action = "wait_for_more_truth"
    elif not failure_detail_excerpt and normalized_failure_kind not in {
        "changed_file_mismatch",
        "metadata_inconsistency",
    }:
        status = "blocked_missing_failure_detail"
        source_status = "failure_detail_missing"
        block_reason = "missing_failure_detail_excerpt"
        next_action = "manual_fix_required"
        if "failure_detail_excerpt" not in missing_inputs:
            missing_inputs.append("failure_detail_excerpt")
    else:
        generation_allowed = True
        generation_attempted = True
        generation_completed = True
        prompt_generated = True
        prompt_kind = "bounded_fix_prompt_v1"
        prompt_summary = (
            f"Repair {normalized_failure_kind} from {normalized_failure_source} "
            f"in {len(normalized_target_files)} target file(s)."
        )

        prompt_lines = [
            "Prompt161 Generated Fix Prompt (Bounded, Execution Prohibited)",
            f"Repository: {normalized_repository_path}",
            "",
            "Goal:",
            "Apply the smallest safe code fix that resolves the observed failure state.",
            "",
            "Failure Context:",
            f"- failure_kind: {normalized_failure_kind}",
            f"- failure_source: {normalized_failure_source}",
            f"- validation_status: {normalized_validation_status}",
        ]
        if failure_detail_excerpt:
            prompt_lines.extend(
                [
                    "",
                    "Observed Failure Excerpt (bounded):",
                    failure_detail_excerpt,
                ]
            )
        prompt_lines.extend(
            [
                "",
                "Allowed Target Files (only these):",
            ]
        )
        prompt_lines.extend([f"- {file_path}" for file_path in normalized_target_files])
        prompt_lines.extend(
            [
                "",
                "Exact Repair Requirements:",
                "- Implement the minimum safe fix for the failure.",
                "- Keep Prompt154-Prompt161 semantics unchanged except the targeted fix.",
                "- Do not modify unrelated logic or broad posture precedence behavior.",
                "",
                "Strict Non-Goals:",
            ]
        )
        prompt_lines.extend([f"- {item}" for item in non_goals])
        prompt_lines.extend(
            [
                "",
                "Safety Constraints:",
            ]
        )
        prompt_lines.extend([f"- {item}" for item in safety_constraints])
        prompt_lines.extend(
            [
                "",
                "Validation Commands (run after edits):",
            ]
        )
        prompt_lines.extend([f"- {cmd}" for cmd in normalized_validation_commands])
        prompt_lines.extend(
            [
                "",
                "Expected Report Format:",
                "1. Files changed.",
                "2. Root cause.",
                "3. Exact fix applied.",
                "4. Validation commands run and results.",
                "5. Remaining risks.",
            ]
        )
        prompt_body = "\n".join(prompt_lines).strip()
        status = "prompt_generated"
        source_status = "generation_succeeded"
        block_reason = "none"
        next_action = "run_codex_with_generated_fix_prompt_later"

        if not prompt_handoff_path_is_exact:
            prompt_handoff_write_failed = True
            block_reason = "handoff_path_not_exact"
            next_action = "manual_fix_required"
        elif not prompt_handoff_path_parent_exists:
            prompt_handoff_write_failed = True
            block_reason = "handoff_parent_missing"
            next_action = "manual_fix_required"
        elif prompt_handoff_path_is_symlink:
            prompt_handoff_write_failed = True
            block_reason = "handoff_path_symlink"
            next_action = "manual_fix_required"
        else:
            prompt_handoff_write_attempted = True
            try:
                handoff_path_obj.write_text(prompt_body, encoding="utf-8")
            except OSError:
                prompt_handoff_write_failed = True
                next_action = "manual_fix_required"
                block_reason = "handoff_write_failed"
            else:
                prompt_handoff_write_completed = True

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"

    if human_review_required:
        normalized_cycle_handoff_generation_input_block_reason = (
            "blocked_human_review_required"
        )
    elif not readiness_generation_allowed or not readiness_ready_to_generate:
        normalized_cycle_handoff_generation_input_block_reason = (
            normalized_cycle_handoff_generation_input_block_reason
            or "blocked_generation_not_allowed"
        )
    elif normalized_readiness_status not in {
        "ready_to_generate_fix_prompt",
        "cycle_handoff_fix_ready",
    }:
        normalized_cycle_handoff_generation_input_block_reason = (
            normalized_cycle_handoff_generation_input_block_reason
            or "blocked_readiness_not_ready"
        )
    elif (
        computed_cycle_handoff_generation_input_available
        and not computed_cycle_handoff_generation_input_consumed
    ):
        normalized_cycle_handoff_generation_input_block_reason = (
            normalized_cycle_handoff_generation_input_block_reason
            or "blocked_re_evaluation_not_allowed"
        )
    elif (
        computed_cycle_handoff_generation_input_available
        and normalized_cycle_handoff_generation_input_kind not in {"fix", "none"}
    ):
        normalized_cycle_handoff_generation_input_block_reason = (
            "blocked_mismatched_cycle_handoff_generation_kind"
        )
    elif not computed_cycle_handoff_generation_input_available:
        normalized_cycle_handoff_generation_input_block_reason = (
            normalized_cycle_handoff_generation_input_block_reason
            or "blocked_missing_generation_input_truth"
        )
    elif status != "prompt_generated":
        normalized_cycle_handoff_generation_input_block_reason = (
            normalized_cycle_handoff_generation_input_block_reason
            or "blocked_existing_generation_safety_gate"
        )

    return {
        "project_browser_autonomous_fix_prompt_generation_status": status,
        "project_browser_autonomous_fix_prompt_generation_source_status": source_status,
        "project_browser_autonomous_fix_prompt_generation_block_reason": block_reason,
        "project_browser_autonomous_fix_prompt_generation_readiness_status": (
            normalized_readiness_status
        ),
        "project_browser_autonomous_fix_prompt_generation_readiness_generation_allowed": bool(
            readiness_generation_allowed
        ),
        "project_browser_autonomous_fix_prompt_generation_generation_allowed": bool(
            generation_allowed
        ),
        "project_browser_autonomous_fix_prompt_generation_generation_attempted": bool(
            generation_attempted
        ),
        "project_browser_autonomous_fix_prompt_generation_generation_completed": bool(
            generation_completed
        ),
        "project_browser_autonomous_fix_prompt_generation_prompt_generated": bool(
            prompt_generated
        ),
        "project_browser_autonomous_fix_prompt_generation_prompt_kind": prompt_kind,
        "project_browser_autonomous_fix_prompt_generation_prompt_body": prompt_body,
        "project_browser_autonomous_fix_prompt_generation_prompt_summary": prompt_summary,
        "project_browser_autonomous_fix_prompt_generation_prompt_handoff_path": (
            prompt_handoff_path
        ),
        "project_browser_autonomous_fix_prompt_generation_prompt_handoff_write_attempted": bool(
            prompt_handoff_write_attempted
        ),
        "project_browser_autonomous_fix_prompt_generation_prompt_handoff_write_completed": bool(
            prompt_handoff_write_completed
        ),
        "project_browser_autonomous_fix_prompt_generation_prompt_handoff_write_failed": bool(
            prompt_handoff_write_failed
        ),
        "project_browser_autonomous_fix_prompt_generation_prompt_handoff_path_is_exact": bool(
            prompt_handoff_path_is_exact
        ),
        "project_browser_autonomous_fix_prompt_generation_prompt_handoff_path_parent_exists": bool(
            prompt_handoff_path_parent_exists
        ),
        "project_browser_autonomous_fix_prompt_generation_prompt_handoff_path_is_symlink": bool(
            prompt_handoff_path_is_symlink
        ),
        "project_browser_autonomous_fix_prompt_generation_failure_kind": (
            normalized_failure_kind
        ),
        "project_browser_autonomous_fix_prompt_generation_failure_source": (
            normalized_failure_source
        ),
        "project_browser_autonomous_fix_prompt_generation_target_files": (
            normalized_target_files
        ),
        "project_browser_autonomous_fix_prompt_generation_changed_files_after_apply": (
            normalized_changed_files
        ),
        "project_browser_autonomous_fix_prompt_generation_unexpected_changed_files_after_apply": (
            normalized_unexpected_files
        ),
        "project_browser_autonomous_fix_prompt_generation_forbidden_changed_files_after_apply": (
            normalized_forbidden_files
        ),
        "project_browser_autonomous_fix_prompt_generation_validation_commands": (
            normalized_validation_commands
        ),
        "project_browser_autonomous_fix_prompt_generation_non_goals": non_goals,
        "project_browser_autonomous_fix_prompt_generation_safety_constraints": (
            safety_constraints
        ),
        "project_browser_autonomous_fix_prompt_generation_next_action": next_action,
        "project_browser_autonomous_fix_prompt_generation_human_review_required": bool(
            human_review_required
        ),
        "project_browser_autonomous_fix_prompt_generation_runtime_posture": runtime_posture,
        "project_browser_autonomous_fix_prompt_generation_missing_inputs": (
            _serialize_required_signals(missing_inputs)
        ),
        "project_browser_autonomous_fix_prompt_generation_cycle_handoff_generation_input_available": bool(
            computed_cycle_handoff_generation_input_available
        ),
        "project_browser_autonomous_fix_prompt_generation_cycle_handoff_generation_input_consumed": bool(
            computed_cycle_handoff_generation_input_consumed
        ),
        "project_browser_autonomous_fix_prompt_generation_cycle_handoff_generation_input_kind": (
            normalized_cycle_handoff_generation_input_kind
        ),
        "project_browser_autonomous_fix_prompt_generation_cycle_handoff_generation_input_status": (
            normalized_cycle_handoff_generation_input_status
        ),
        "project_browser_autonomous_fix_prompt_generation_cycle_handoff_generation_input_source": (
            normalized_cycle_handoff_generation_input_source
        ),
        "project_browser_autonomous_fix_prompt_generation_cycle_handoff_generation_input_block_reason": (
            normalized_cycle_handoff_generation_input_block_reason
        ),
    }

def _build_project_browser_autonomous_next_prompt_readiness_state(
    *,
    validation_status: str,
    validation_passed: bool,
    validation_failed: bool,
    post_apply_validation_status: str,
    rollback_required: bool,
    human_review_required: bool,
    fix_prompt_readiness_status: str,
    fix_prompt_generation_status: str,
    prior_next_prompt_generation_attempted: bool,
    implementation_prompt_status: str,
    implementation_prompt_available: bool,
    implementation_prompt_slice_id: str,
    implementation_prompt_bounded_scope_class: str,
    implementation_prompt_preferred_files: list[str] | None,
    project_pr_queue_status: str,
    project_pr_queue_selected_slice_id: str,
    objective_completion_posture: str,
    validation_missing_inputs: list[str] | None,
    fix_readiness_missing_inputs: list[str] | None,
    fix_generation_missing_inputs: list[str] | None,
    cycle_handoff_available: bool = False,
    cycle_handoff_prompt_kind: str = "none",
    cycle_handoff_reason: str = "",
) -> dict[str, Any]:
    allowed_statuses = {
        "ready_to_generate_next_prompt",
        "cycle_handoff_next_ready",
        "blocked_validation_not_passed",
        "blocked_validation_failed",
        "blocked_fix_required",
        "blocked_insufficient_truth",
        "blocked_human_review_required",
        "blocked_rollback_required",
        "blocked_missing_next_work",
        "blocked_no_remaining_work",
        "blocked_prompt_generation_already_attempted",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "generate_next_prompt_later",
        "generate_next_prompt",
        "wait_for_validation_pass",
        "run_fix_prompt_flow",
        "wait_for_more_truth",
        "manual_review_required",
        "rollback_required",
        "no_remaining_work",
        "insufficient_truth",
    }
    runtime_posture = [
        "metadata_only_next_prompt_readiness",
        "no_next_prompt_generation",
        "no_handoff_write",
        "no_external_model_invocation",
        "no_patch_apply",
        "no_git_mutation",
        "no_autonomous_loop",
    ]

    normalized_validation_status = _normalize_text(
        validation_status,
        default="insufficient_truth",
    )
    normalized_post_apply_validation_status = _normalize_text(
        post_apply_validation_status,
        default="insufficient_truth",
    )
    normalized_fix_readiness_status = _normalize_text(
        fix_prompt_readiness_status,
        default="insufficient_truth",
    )
    normalized_fix_generation_status = _normalize_text(
        fix_prompt_generation_status,
        default="insufficient_truth",
    )
    normalized_implementation_prompt_status = _normalize_text(
        implementation_prompt_status,
        default="insufficient_truth",
    )
    normalized_implementation_slice_id = _normalize_text(
        implementation_prompt_slice_id,
        default="",
    )
    normalized_scope_class = _normalize_text(
        implementation_prompt_bounded_scope_class,
        default="unknown",
    )
    normalized_queue_status = _normalize_text(
        project_pr_queue_status,
        default="insufficient_truth",
    )
    normalized_queue_slice_id = _normalize_text(
        project_pr_queue_selected_slice_id,
        default="",
    )
    normalized_objective_completion_posture = _normalize_text(
        objective_completion_posture,
        default="objective_insufficient_truth",
    )
    normalized_target_files = _normalize_string_list(
        implementation_prompt_preferred_files or []
    )
    normalized_cycle_handoff_prompt_kind = _normalize_text(
        cycle_handoff_prompt_kind,
        default="none",
    )
    normalized_cycle_handoff_reason = _normalize_text(cycle_handoff_reason, default="")
    cycle_handoff_consumed = bool(cycle_handoff_available)
    cycle_handoff_acknowledged = bool(
        cycle_handoff_consumed
        and normalized_cycle_handoff_prompt_kind == "next"
        and normalized_cycle_handoff_reason == "cycle_passed"
    )
    cycle_handoff_readiness_source = "cycle_passed" if cycle_handoff_acknowledged else ""
    cycle_handoff_block_reason = ""
    if cycle_handoff_consumed and not cycle_handoff_acknowledged:
        if normalized_cycle_handoff_prompt_kind != "next":
            cycle_handoff_block_reason = "mismatched_cycle_handoff_prompt_kind"
        elif normalized_cycle_handoff_reason != "cycle_passed":
            cycle_handoff_block_reason = "mismatched_cycle_handoff_reason"
    cycle_handoff_re_evaluation_attempted = False
    cycle_handoff_re_evaluation_allowed = False
    cycle_handoff_re_evaluation_block_reason = ""
    cycle_handoff_re_evaluated_status = ""
    cycle_handoff_re_evaluated_ready_to_generate = False
    cycle_handoff_re_evaluated_generation_allowed = False
    cycle_handoff_re_evaluation_safety_gates_passed = False
    cycle_handoff_re_evaluation_source = ""
    validation_missing = _normalize_string_list(validation_missing_inputs or [])
    fix_readiness_missing = _normalize_string_list(fix_readiness_missing_inputs or [])
    fix_generation_missing = _normalize_string_list(fix_generation_missing_inputs or [])
    missing_inputs = _serialize_required_signals(
        [*validation_missing, *fix_readiness_missing, *fix_generation_missing]
    )

    status = "insufficient_truth"
    source_status = "insufficient_truth"
    block_reason = "insufficient_truth"
    next_work_available = False
    next_work_kind = "none"
    next_scope = "none"
    next_action = "insufficient_truth"
    ready_to_generate = False
    generation_allowed = False
    prompt_generation_attempted = False
    prompt_generated = False
    prompt_path = ""
    insufficient_truth = False

    fix_required_active = bool(
        normalized_fix_readiness_status
        in {
            "ready_to_generate_fix_prompt",
            "blocked_missing_failure_truth",
            "blocked_no_actionable_failure",
            "blocked_forbidden_changes",
            "blocked_unexpected_changes",
            "blocked_metadata_inconsistency",
        }
        or normalized_fix_generation_status
        in {
            "prompt_generated",
            "blocked_missing_target_files",
            "blocked_missing_failure_detail",
            "blocked_handoff_path_invalid",
            "blocked_handoff_write_failed",
        }
    )

    if rollback_required:
        status = "blocked_rollback_required"
        source_status = "rollback_required"
        block_reason = "rollback_required"
        next_action = "rollback_required"
    elif human_review_required:
        status = "blocked_human_review_required"
        source_status = "human_review_required"
        block_reason = "human_review_required"
        next_action = "manual_review_required"
    elif normalized_validation_status == "insufficient_truth" or normalized_post_apply_validation_status == "insufficient_truth":
        status = "blocked_insufficient_truth"
        source_status = "validation_truth_unavailable"
        block_reason = "insufficient_truth"
        next_action = "wait_for_more_truth"
        insufficient_truth = True
        if not missing_inputs:
            missing_inputs = ["post_apply_validation_truth"]
    elif fix_required_active:
        status = "blocked_fix_required"
        source_status = "fix_prompt_flow_required"
        block_reason = "fix_required"
        next_action = "run_fix_prompt_flow"
    elif validation_failed:
        status = "blocked_validation_failed"
        source_status = "validation_failed"
        block_reason = "validation_failed"
        next_action = "run_fix_prompt_flow"
    elif not validation_passed:
        status = "blocked_validation_not_passed"
        source_status = "validation_not_passed"
        block_reason = "validation_not_passed"
        next_action = "wait_for_validation_pass"
    elif prior_next_prompt_generation_attempted:
        status = "blocked_prompt_generation_already_attempted"
        source_status = "prior_generation_attempt_detected"
        block_reason = "prompt_generation_already_attempted"
        next_action = "wait_for_more_truth"
    else:
        if (
            normalized_objective_completion_posture == "objective_completed"
            or normalized_queue_status == "empty"
        ):
            status = "blocked_no_remaining_work"
            source_status = "no_remaining_work_detected"
            block_reason = "no_remaining_work"
            next_action = "no_remaining_work"
        elif (
            normalized_implementation_prompt_status == "available"
            and bool(implementation_prompt_available)
            and normalized_queue_status == "prepared"
        ):
            next_work_available = True
            next_work_kind = "queued_slice_next_prompt"
            next_scope = (
                normalized_scope_class
                if normalized_scope_class not in {"", "unknown", "insufficient_truth"}
                else "single_slice"
            )
        else:
            status = "blocked_missing_next_work"
            source_status = "next_work_not_determinable"
            block_reason = "next_work_missing"
            next_action = "wait_for_more_truth"
            if not missing_inputs:
                missing_inputs = ["next_work_truth"]

        scope_bounded = bool(next_scope and next_scope not in {"none", "unknown", "unbounded"})
        if next_work_available and not normalized_target_files:
            status = "blocked_missing_next_work"
            source_status = "next_target_files_missing"
            block_reason = "next_target_files_missing"
            next_action = "wait_for_more_truth"
            if "next_target_files" not in missing_inputs:
                missing_inputs = _serialize_required_signals([*missing_inputs, "next_target_files"])
        elif next_work_available and not scope_bounded:
            status = "blocked_missing_next_work"
            source_status = "next_scope_unbounded"
            block_reason = "next_scope_unbounded"
            next_action = "wait_for_more_truth"
            if "next_scope" not in missing_inputs:
                missing_inputs = _serialize_required_signals([*missing_inputs, "next_scope"])
        elif next_work_available:
            status = "ready_to_generate_next_prompt"
            source_status = "validation_and_scope_ready"
            block_reason = "none"
            next_action = "generate_next_prompt_later"
            ready_to_generate = True
            generation_allowed = True

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"
    if cycle_handoff_acknowledged:
        cycle_handoff_re_evaluation_attempted = True
        cycle_handoff_re_evaluation_source = "cycle_passed"
        cycle_handoff_re_evaluation_safety_gates_passed = bool(
            status == "ready_to_generate_next_prompt"
            and ready_to_generate
            and generation_allowed
            and validation_passed
            and not validation_failed
            and not rollback_required
            and not human_review_required
            and not insufficient_truth
            and next_work_available
            and bool(normalized_target_files)
            and bool(next_scope and next_scope not in {"none", "unknown", "unbounded"})
        )
        if cycle_handoff_re_evaluation_safety_gates_passed:
            cycle_handoff_re_evaluation_allowed = True
            status = "cycle_handoff_next_ready"
            next_action = "generate_next_prompt"
            ready_to_generate = True
            generation_allowed = True
            cycle_handoff_re_evaluated_status = status
            cycle_handoff_re_evaluated_ready_to_generate = True
            cycle_handoff_re_evaluated_generation_allowed = True
        elif human_review_required:
            cycle_handoff_re_evaluation_block_reason = "blocked_human_review_required"
        elif normalized_validation_status == "insufficient_truth" or normalized_post_apply_validation_status == "insufficient_truth":
            cycle_handoff_re_evaluation_block_reason = "blocked_missing_truth"
        elif status in {
            "blocked_rollback_required",
            "blocked_human_review_required",
            "blocked_validation_not_passed",
            "blocked_validation_failed",
            "blocked_fix_required",
            "blocked_insufficient_truth",
            "blocked_missing_next_work",
            "blocked_no_remaining_work",
            "blocked_prompt_generation_already_attempted",
            "insufficient_truth",
        }:
            cycle_handoff_re_evaluation_block_reason = (
                "blocked_existing_readiness_safety_gate"
            )
        else:
            cycle_handoff_re_evaluation_block_reason = (
                "blocked_insufficient_re_evaluation_truth"
            )
    else:
        if cycle_handoff_consumed:
            cycle_handoff_re_evaluation_attempted = True
        if cycle_handoff_consumed and normalized_cycle_handoff_prompt_kind != "next":
            cycle_handoff_re_evaluation_block_reason = (
                "blocked_mismatched_cycle_handoff_prompt_kind"
            )
        elif cycle_handoff_consumed and normalized_cycle_handoff_reason != "cycle_passed":
            cycle_handoff_re_evaluation_block_reason = (
                "blocked_mismatched_cycle_handoff_reason"
            )
        elif cycle_handoff_consumed or not cycle_handoff_acknowledged:
            cycle_handoff_re_evaluation_block_reason = "blocked_handoff_not_acknowledged"

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"

    return {
        "project_browser_autonomous_next_prompt_readiness_status": status,
        "project_browser_autonomous_next_prompt_readiness_source_status": source_status,
        "project_browser_autonomous_next_prompt_readiness_block_reason": block_reason,
        "project_browser_autonomous_next_prompt_readiness_validation_status": (
            normalized_validation_status
        ),
        "project_browser_autonomous_next_prompt_readiness_validation_passed": bool(
            validation_passed
        ),
        "project_browser_autonomous_next_prompt_readiness_validation_failed": bool(
            validation_failed
        ),
        "project_browser_autonomous_next_prompt_readiness_post_apply_validation_status": (
            normalized_post_apply_validation_status
        ),
        "project_browser_autonomous_next_prompt_readiness_rollback_required": bool(
            rollback_required
        ),
        "project_browser_autonomous_next_prompt_readiness_human_review_required": bool(
            human_review_required
        ),
        "project_browser_autonomous_next_prompt_readiness_insufficient_truth": bool(
            insufficient_truth
        ),
        "project_browser_autonomous_next_prompt_readiness_fix_prompt_readiness_status": (
            normalized_fix_readiness_status
        ),
        "project_browser_autonomous_next_prompt_readiness_fix_prompt_generation_status": (
            normalized_fix_generation_status
        ),
        "project_browser_autonomous_next_prompt_readiness_next_work_available": bool(
            next_work_available
        ),
        "project_browser_autonomous_next_prompt_readiness_next_work_kind": next_work_kind,
        "project_browser_autonomous_next_prompt_readiness_next_scope": next_scope,
        "project_browser_autonomous_next_prompt_readiness_next_target_files": (
            normalized_target_files
        ),
        "project_browser_autonomous_next_prompt_readiness_ready_to_generate": bool(
            ready_to_generate
        ),
        "project_browser_autonomous_next_prompt_readiness_generation_allowed": bool(
            generation_allowed
        ),
        "project_browser_autonomous_next_prompt_readiness_generation_blocked": bool(
            not generation_allowed
        ),
        "project_browser_autonomous_next_prompt_readiness_prompt_generation_attempted": bool(
            prompt_generation_attempted
        ),
        "project_browser_autonomous_next_prompt_readiness_prompt_generated": bool(
            prompt_generated
        ),
        "project_browser_autonomous_next_prompt_readiness_prompt_path": prompt_path,
        "project_browser_autonomous_next_prompt_readiness_next_action": next_action,
        "project_browser_autonomous_next_prompt_readiness_runtime_posture": runtime_posture,
        "project_browser_autonomous_next_prompt_readiness_missing_inputs": (
            _serialize_required_signals(missing_inputs)
        ),
        "project_browser_autonomous_next_prompt_readiness_cycle_handoff_consumed": bool(
            cycle_handoff_consumed
        ),
        "project_browser_autonomous_next_prompt_readiness_cycle_handoff_acknowledged": bool(
            cycle_handoff_acknowledged
        ),
        "project_browser_autonomous_next_prompt_readiness_cycle_handoff_prompt_kind": (
            normalized_cycle_handoff_prompt_kind
        ),
        "project_browser_autonomous_next_prompt_readiness_cycle_handoff_reason": (
            normalized_cycle_handoff_reason
        ),
        "project_browser_autonomous_next_prompt_readiness_cycle_handoff_block_reason": (
            cycle_handoff_block_reason
        ),
        "project_browser_autonomous_next_prompt_readiness_cycle_handoff_readiness_source": (
            cycle_handoff_readiness_source
        ),
        "project_browser_autonomous_next_prompt_readiness_cycle_handoff_re_evaluation_attempted": bool(
            cycle_handoff_re_evaluation_attempted
        ),
        "project_browser_autonomous_next_prompt_readiness_cycle_handoff_re_evaluation_allowed": bool(
            cycle_handoff_re_evaluation_allowed
        ),
        "project_browser_autonomous_next_prompt_readiness_cycle_handoff_re_evaluation_block_reason": (
            cycle_handoff_re_evaluation_block_reason
        ),
        "project_browser_autonomous_next_prompt_readiness_cycle_handoff_re_evaluated_status": (
            cycle_handoff_re_evaluated_status
        ),
        "project_browser_autonomous_next_prompt_readiness_cycle_handoff_re_evaluated_ready_to_generate": bool(
            cycle_handoff_re_evaluated_ready_to_generate
        ),
        "project_browser_autonomous_next_prompt_readiness_cycle_handoff_re_evaluated_generation_allowed": bool(
            cycle_handoff_re_evaluated_generation_allowed
        ),
        "project_browser_autonomous_next_prompt_readiness_cycle_handoff_re_evaluation_safety_gates_passed": bool(
            cycle_handoff_re_evaluation_safety_gates_passed
        ),
        "project_browser_autonomous_next_prompt_readiness_cycle_handoff_re_evaluation_source": (
            cycle_handoff_re_evaluation_source
        ),
    }

def _build_project_browser_autonomous_next_prompt_generation_state(
    *,
    repository_path: str,
    current_checkpoint: str,
    readiness_status: str,
    readiness_generation_allowed: bool,
    readiness_ready_to_generate: bool,
    validation_passed: bool,
    validation_failed: bool,
    rollback_required: bool,
    human_review_required: bool,
    insufficient_truth: bool,
    next_work_available: bool,
    next_work_kind: str,
    next_scope: str,
    next_target_files: list[str] | None,
    next_validation_commands: list[str] | None,
    readiness_next_action: str,
    readiness_missing_inputs: list[str] | None,
    cycle_handoff_generation_input_available: bool = False,
    cycle_handoff_generation_input_consumed: bool = False,
    cycle_handoff_generation_input_kind: str = "none",
    cycle_handoff_generation_input_status: str = "",
    cycle_handoff_generation_input_source: str = "",
    cycle_handoff_generation_input_block_reason: str = "",
) -> dict[str, Any]:
    allowed_statuses = {
        "prompt_generated",
        "blocked_not_ready",
        "blocked_generation_not_allowed",
        "blocked_insufficient_truth",
        "blocked_human_review_required",
        "blocked_rollback_required",
        "blocked_missing_next_work",
        "blocked_missing_target_files",
        "blocked_missing_scope",
        "blocked_handoff_path_invalid",
        "blocked_handoff_write_failed",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "select_generated_next_prompt_later",
        "generate_next_prompt",
        "wait_for_more_truth",
        "run_fix_prompt_flow",
        "manual_review_required",
        "rollback_required",
        "manual_next_prompt_required",
        "no_remaining_work",
        "insufficient_truth",
    }
    runtime_posture = [
        "bounded_next_prompt_generation",
        "metadata_and_prompt_text_only",
        "no_prompt_execution",
        "no_external_model_invocation",
        "no_patch_apply",
        "no_git_mutation",
        "no_autonomous_loop",
    ]
    non_goals = [
        "Do not invoke Codex/ChatGPT/browser/external models.",
        "Do not generate or apply implementation patches.",
        "Do not execute rollback, commit, push, GitHub, CI, merge, or loops.",
        "Do not change unrelated Prompt154-Prompt163 semantics.",
    ]
    safety_constraints = [
        "Make the smallest safe additive change for the selected bounded scope.",
        "Keep changes strictly within target files unless absolutely necessary.",
        "Preserve existing Prompt154-Prompt163 safety gates and metadata contracts.",
        "Avoid unrelated refactors and side effects.",
    ]

    handoff_path = "/tmp/codex-local-runner-decision/generated_next_prompt.txt"
    normalized_repository_path = _normalize_text(repository_path, default="")
    normalized_checkpoint = _normalize_text(current_checkpoint, default="")
    normalized_readiness_status = _normalize_text(readiness_status, default="insufficient_truth")
    normalized_next_work_kind = _normalize_text(next_work_kind, default="none")
    normalized_next_scope = _normalize_text(next_scope, default="none")
    normalized_next_target_files = _normalize_string_list(next_target_files or [])
    normalized_next_validation_commands = _normalize_string_list(next_validation_commands or [])
    normalized_readiness_next_action = _normalize_text(
        readiness_next_action,
        default="insufficient_truth",
    )
    normalized_cycle_handoff_generation_input_kind = _normalize_text(
        cycle_handoff_generation_input_kind,
        default="none",
    )
    normalized_cycle_handoff_generation_input_status = _normalize_text(
        cycle_handoff_generation_input_status,
        default="",
    )
    normalized_cycle_handoff_generation_input_source = _normalize_text(
        cycle_handoff_generation_input_source,
        default="",
    )
    normalized_cycle_handoff_generation_input_block_reason = _normalize_text(
        cycle_handoff_generation_input_block_reason,
        default="",
    )
    computed_cycle_handoff_generation_input_available = bool(
        cycle_handoff_generation_input_available
    )
    computed_cycle_handoff_generation_input_consumed = bool(
        cycle_handoff_generation_input_consumed
    )
    missing_inputs = _normalize_string_list(readiness_missing_inputs or [])

    scope_bounded = normalized_next_scope not in {
        "",
        "none",
        "unknown",
        "unbounded",
        "insufficient_truth",
    }
    handoff_path_obj = Path(handoff_path)
    prompt_handoff_path_is_exact = handoff_path == "/tmp/codex-local-runner-decision/generated_next_prompt.txt"
    prompt_handoff_path_parent_exists = handoff_path_obj.parent.exists()
    prompt_handoff_path_is_symlink = handoff_path_obj.is_symlink()

    status = "insufficient_truth"
    source_status = "insufficient_truth"
    block_reason = "insufficient_truth"
    generation_allowed = False
    generation_attempted = False
    generation_completed = False
    prompt_generated = False
    prompt_kind = "none"
    prompt_body = ""
    prompt_summary = ""
    prompt_path = ""
    prompt_handoff_write_attempted = False
    prompt_handoff_write_completed = False
    prompt_handoff_write_failed = False
    next_action = "insufficient_truth"

    if rollback_required:
        status = "blocked_rollback_required"
        source_status = "rollback_required"
        block_reason = "rollback_required"
        next_action = "rollback_required"
    elif human_review_required:
        status = "blocked_human_review_required"
        source_status = "human_review_required"
        block_reason = "human_review_required"
        next_action = "manual_review_required"
    elif insufficient_truth or normalized_readiness_status in {
        "blocked_insufficient_truth",
        "insufficient_truth",
    }:
        status = "blocked_insufficient_truth"
        source_status = "insufficient_truth_active"
        block_reason = "insufficient_truth"
        next_action = "wait_for_more_truth"
        if not missing_inputs:
            missing_inputs = ["next_prompt_readiness_truth"]
    elif normalized_readiness_status in {
        "blocked_fix_required",
        "blocked_validation_failed",
    } or normalized_readiness_next_action == "run_fix_prompt_flow":
        status = "blocked_not_ready"
        source_status = "fix_flow_required"
        block_reason = "fix_required"
        next_action = "run_fix_prompt_flow"
    elif normalized_readiness_status not in {
        "ready_to_generate_next_prompt",
        "cycle_handoff_next_ready",
    }:
        status = "blocked_not_ready"
        source_status = "readiness_not_ready"
        block_reason = f"readiness_status:{normalized_readiness_status or 'unknown'}"
        next_action = (
            "no_remaining_work"
            if normalized_readiness_status == "blocked_no_remaining_work"
            else "wait_for_more_truth"
        )
    elif not readiness_generation_allowed or not readiness_ready_to_generate:
        status = "blocked_generation_not_allowed"
        source_status = "readiness_generation_not_allowed"
        block_reason = "generation_not_allowed"
        next_action = "wait_for_more_truth"
    elif not validation_passed or validation_failed:
        status = "blocked_generation_not_allowed"
        source_status = "validation_gate_not_satisfied"
        block_reason = "validation_not_passed"
        next_action = "run_fix_prompt_flow"
    elif not next_work_available:
        status = "blocked_missing_next_work"
        source_status = "next_work_unavailable"
        block_reason = "next_work_unavailable"
        next_action = "wait_for_more_truth"
        if "next_work" not in missing_inputs:
            missing_inputs = _serialize_required_signals([*missing_inputs, "next_work"])
    elif not scope_bounded:
        status = "blocked_missing_scope"
        source_status = "next_scope_unbounded"
        block_reason = "next_scope_unbounded"
        next_action = "wait_for_more_truth"
        if "next_scope" not in missing_inputs:
            missing_inputs = _serialize_required_signals([*missing_inputs, "next_scope"])
    elif not normalized_next_target_files:
        status = "blocked_missing_target_files"
        source_status = "next_target_files_missing"
        block_reason = "next_target_files_missing"
        next_action = "manual_next_prompt_required"
        if "next_target_files" not in missing_inputs:
            missing_inputs = _serialize_required_signals([*missing_inputs, "next_target_files"])
    else:
        generation_allowed = True
        generation_attempted = True
        generation_completed = True
        prompt_generated = True
        prompt_kind = "bounded_next_prompt_v1"
        prompt_path = handoff_path
        prompt_summary = (
            f"Next prompt prepared for {normalized_next_work_kind} with "
            f"{len(normalized_next_target_files)} target file(s)."
        )

        prompt_lines = [
            "Prompt163 Generated Next Prompt (Bounded, Execution Prohibited)",
            f"Repository: {normalized_repository_path}",
            f"Current checkpoint: {normalized_checkpoint}",
            "",
            "Goal:",
            "Implement the next bounded development step as the smallest safe additive change.",
            "",
            "Next Work:",
            f"- next_work_kind: {normalized_next_work_kind}",
            f"- next_scope: {normalized_next_scope}",
            "",
            "Target Files (only these):",
        ]
        prompt_lines.extend([f"- {path}" for path in normalized_next_target_files])
        prompt_lines.extend(
            [
                "",
                "Exact Implementation Requirements:",
                "- Apply only the minimum additive change required for this next step.",
                "- Preserve existing Prompt154-Prompt163 semantics unless the scoped change requires otherwise.",
                "- Avoid unrelated refactors and broad behavior changes.",
                "",
                "Strict Non-Goals:",
            ]
        )
        prompt_lines.extend([f"- {item}" for item in non_goals])
        prompt_lines.extend(
            [
                "",
                "Safety Constraints:",
            ]
        )
        prompt_lines.extend([f"- {item}" for item in safety_constraints])
        prompt_lines.extend(
            [
                "",
                "Validation Commands:",
            ]
        )
        prompt_lines.extend([f"- {cmd}" for cmd in normalized_next_validation_commands])
        prompt_lines.extend(
            [
                "",
                "Expected Report Format:",
                "1. Files changed.",
                "2. Exact behavior implemented.",
                "3. Validation commands run and results.",
                "4. Confirmation of non-goals preserved.",
                "5. Remaining risk.",
            ]
        )
        prompt_body = "\n".join(prompt_lines).strip()
        status = "prompt_generated"
        source_status = "generation_succeeded"
        block_reason = "none"
        next_action = "select_generated_next_prompt_later"

        if not prompt_handoff_path_is_exact:
            prompt_handoff_write_failed = True
            block_reason = "handoff_path_not_exact"
            next_action = "manual_next_prompt_required"
        elif not prompt_handoff_path_parent_exists:
            prompt_handoff_write_failed = True
            block_reason = "handoff_parent_missing"
            next_action = "manual_next_prompt_required"
        elif prompt_handoff_path_is_symlink:
            prompt_handoff_write_failed = True
            block_reason = "handoff_path_symlink"
            next_action = "manual_next_prompt_required"
        else:
            prompt_handoff_write_attempted = True
            try:
                handoff_path_obj.write_text(prompt_body, encoding="utf-8")
            except OSError:
                prompt_handoff_write_failed = True
                block_reason = "handoff_write_failed"
                next_action = "manual_next_prompt_required"
            else:
                prompt_handoff_write_completed = True

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"

    if human_review_required:
        normalized_cycle_handoff_generation_input_block_reason = (
            "blocked_human_review_required"
        )
    elif not readiness_generation_allowed or not readiness_ready_to_generate:
        normalized_cycle_handoff_generation_input_block_reason = (
            normalized_cycle_handoff_generation_input_block_reason
            or "blocked_generation_not_allowed"
        )
    elif normalized_readiness_status not in {
        "ready_to_generate_next_prompt",
        "cycle_handoff_next_ready",
    }:
        normalized_cycle_handoff_generation_input_block_reason = (
            normalized_cycle_handoff_generation_input_block_reason
            or "blocked_readiness_not_ready"
        )
    elif (
        computed_cycle_handoff_generation_input_available
        and not computed_cycle_handoff_generation_input_consumed
    ):
        normalized_cycle_handoff_generation_input_block_reason = (
            normalized_cycle_handoff_generation_input_block_reason
            or "blocked_re_evaluation_not_allowed"
        )
    elif (
        computed_cycle_handoff_generation_input_available
        and normalized_cycle_handoff_generation_input_kind not in {"next", "none"}
    ):
        normalized_cycle_handoff_generation_input_block_reason = (
            "blocked_mismatched_cycle_handoff_generation_kind"
        )
    elif not computed_cycle_handoff_generation_input_available:
        normalized_cycle_handoff_generation_input_block_reason = (
            normalized_cycle_handoff_generation_input_block_reason
            or "blocked_missing_generation_input_truth"
        )
    elif status != "prompt_generated":
        normalized_cycle_handoff_generation_input_block_reason = (
            normalized_cycle_handoff_generation_input_block_reason
            or "blocked_existing_generation_safety_gate"
        )

    return {
        "project_browser_autonomous_next_prompt_generation_status": status,
        "project_browser_autonomous_next_prompt_generation_source_status": source_status,
        "project_browser_autonomous_next_prompt_generation_block_reason": block_reason,
        "project_browser_autonomous_next_prompt_generation_readiness_status": (
            normalized_readiness_status
        ),
        "project_browser_autonomous_next_prompt_generation_readiness_generation_allowed": bool(
            readiness_generation_allowed
        ),
        "project_browser_autonomous_next_prompt_generation_generation_allowed": bool(
            generation_allowed
        ),
        "project_browser_autonomous_next_prompt_generation_generation_attempted": bool(
            generation_attempted
        ),
        "project_browser_autonomous_next_prompt_generation_generation_completed": bool(
            generation_completed
        ),
        "project_browser_autonomous_next_prompt_generation_prompt_generated": bool(
            prompt_generated
        ),
        "project_browser_autonomous_next_prompt_generation_prompt_kind": prompt_kind,
        "project_browser_autonomous_next_prompt_generation_prompt_body": prompt_body,
        "project_browser_autonomous_next_prompt_generation_prompt_summary": prompt_summary,
        "project_browser_autonomous_next_prompt_generation_prompt_handoff_path": handoff_path,
        "project_browser_autonomous_next_prompt_generation_prompt_handoff_write_attempted": bool(
            prompt_handoff_write_attempted
        ),
        "project_browser_autonomous_next_prompt_generation_prompt_handoff_write_completed": bool(
            prompt_handoff_write_completed
        ),
        "project_browser_autonomous_next_prompt_generation_prompt_handoff_write_failed": bool(
            prompt_handoff_write_failed
        ),
        "project_browser_autonomous_next_prompt_generation_prompt_handoff_path_is_exact": bool(
            prompt_handoff_path_is_exact
        ),
        "project_browser_autonomous_next_prompt_generation_prompt_handoff_path_parent_exists": bool(
            prompt_handoff_path_parent_exists
        ),
        "project_browser_autonomous_next_prompt_generation_prompt_handoff_path_is_symlink": bool(
            prompt_handoff_path_is_symlink
        ),
        "project_browser_autonomous_next_prompt_generation_next_work_kind": (
            normalized_next_work_kind
        ),
        "project_browser_autonomous_next_prompt_generation_next_scope": (
            normalized_next_scope
        ),
        "project_browser_autonomous_next_prompt_generation_next_target_files": (
            normalized_next_target_files
        ),
        "project_browser_autonomous_next_prompt_generation_next_validation_commands": (
            normalized_next_validation_commands
        ),
        "project_browser_autonomous_next_prompt_generation_non_goals": non_goals,
        "project_browser_autonomous_next_prompt_generation_safety_constraints": (
            safety_constraints
        ),
        "project_browser_autonomous_next_prompt_generation_next_action": next_action,
        "project_browser_autonomous_next_prompt_generation_human_review_required": bool(
            human_review_required
        ),
        "project_browser_autonomous_next_prompt_generation_runtime_posture": runtime_posture,
        "project_browser_autonomous_next_prompt_generation_missing_inputs": (
            _serialize_required_signals(missing_inputs)
        ),
        "project_browser_autonomous_next_prompt_generation_prompt_path": prompt_path,
        "project_browser_autonomous_next_prompt_generation_cycle_handoff_generation_input_available": bool(
            computed_cycle_handoff_generation_input_available
        ),
        "project_browser_autonomous_next_prompt_generation_cycle_handoff_generation_input_consumed": bool(
            computed_cycle_handoff_generation_input_consumed
        ),
        "project_browser_autonomous_next_prompt_generation_cycle_handoff_generation_input_kind": (
            normalized_cycle_handoff_generation_input_kind
        ),
        "project_browser_autonomous_next_prompt_generation_cycle_handoff_generation_input_status": (
            normalized_cycle_handoff_generation_input_status
        ),
        "project_browser_autonomous_next_prompt_generation_cycle_handoff_generation_input_source": (
            normalized_cycle_handoff_generation_input_source
        ),
        "project_browser_autonomous_next_prompt_generation_cycle_handoff_generation_input_block_reason": (
            normalized_cycle_handoff_generation_input_block_reason
        ),
    }

def _build_project_browser_autonomous_generated_prompt_reentry_readiness_state(
    *,
    fix_generation_status: str,
    fix_prompt_generated: bool,
    fix_prompt_handoff_path: str,
    fix_prompt_handoff_write_completed: bool,
    fix_prompt_handoff_write_failed: bool,
    fix_human_review_required: bool,
    fix_next_action: str,
    fix_cycle_handoff_generation_input_available: bool = False,
    fix_cycle_handoff_generation_input_consumed: bool = False,
    fix_cycle_handoff_generation_input_kind: str = "none",
    fix_cycle_handoff_generation_input_block_reason: str = "",
    next_generation_status: str = "",
    next_prompt_generated: bool = False,
    next_prompt_handoff_path: str = "",
    next_prompt_handoff_write_completed: bool = False,
    next_prompt_handoff_write_failed: bool = False,
    next_human_review_required: bool = False,
    next_next_action: str = "",
    next_cycle_handoff_generation_input_available: bool = False,
    next_cycle_handoff_generation_input_consumed: bool = False,
    next_cycle_handoff_generation_input_kind: str = "none",
    next_cycle_handoff_generation_input_block_reason: str = "",
) -> dict[str, Any]:
    allowed_statuses = {
        "reentry_fix_prompt_ready",
        "reentry_next_prompt_ready",
        "reentry_blocked_human_review_required",
        "reentry_blocked_insufficient_truth",
        "reentry_blocked_ambiguous_prompt_kind",
        "insufficient_truth",
    }
    allowed_prompt_kinds = {"fix", "next", "none"}
    allowed_targets = {
        "prompt_selection_and_codex_invocation_readiness",
        "manual_review",
        "none",
    }
    allowed_next_actions = {
        "prepare_fix_prompt_reentry",
        "prepare_next_prompt_reentry",
        "manual_review_required",
        "insufficient_truth",
    }
    runtime_posture = [
        "metadata_only_generated_prompt_reentry_readiness",
        "no_prompt_generation",
        "no_prompt_execution",
        "no_codex_invocation",
        "no_autonomous_loop",
        "no_git_mutation",
    ]
    fix_allowed_path = "/tmp/codex-local-runner-decision/generated_fix_prompt.txt"
    next_allowed_path = "/tmp/codex-local-runner-decision/generated_next_prompt.txt"
    max_prompt_size_bytes = 20000

    normalized_fix_generation_status = _normalize_text(
        fix_generation_status,
        default="insufficient_truth",
    )
    normalized_next_generation_status = _normalize_text(
        next_generation_status,
        default="insufficient_truth",
    )
    normalized_fix_prompt_handoff_path = _normalize_text(fix_prompt_handoff_path, default="")
    normalized_next_prompt_handoff_path = _normalize_text(next_prompt_handoff_path, default="")
    normalized_fix_cycle_kind = _normalize_text(
        fix_cycle_handoff_generation_input_kind,
        default="none",
    )
    normalized_next_cycle_kind = _normalize_text(
        next_cycle_handoff_generation_input_kind,
        default="none",
    )
    normalized_fix_cycle_block_reason = _normalize_text(
        fix_cycle_handoff_generation_input_block_reason,
        default="",
    )
    normalized_next_cycle_block_reason = _normalize_text(
        next_cycle_handoff_generation_input_block_reason,
        default="",
    )

    def _safe_prompt_path(path_text: str, expected_path: str) -> tuple[bool, str]:
        normalized_path = _normalize_text(path_text, default="")
        if not normalized_path:
            return False, "blocked_insufficient_reentry_truth"
        if normalized_path != expected_path:
            return False, "blocked_unexpected_prompt_path"
        prompt_path_obj = Path(normalized_path)
        if prompt_path_obj.is_symlink():
            return False, "blocked_prompt_path_symlink"
        if not prompt_path_obj.exists():
            return False, "blocked_prompt_path_missing"
        if not prompt_path_obj.is_file():
            return False, "blocked_prompt_path_not_file"
        try:
            size_bytes = prompt_path_obj.stat().st_size
        except OSError:
            return False, "blocked_prompt_path_unreadable"
        if size_bytes <= 0:
            return False, "blocked_prompt_path_empty"
        if size_bytes > max_prompt_size_bytes:
            return False, "blocked_prompt_path_too_large"
        return True, ""

    fix_path_safe, fix_path_block_reason = _safe_prompt_path(
        normalized_fix_prompt_handoff_path,
        fix_allowed_path,
    )
    next_path_safe, next_path_block_reason = _safe_prompt_path(
        normalized_next_prompt_handoff_path,
        next_allowed_path,
    )

    fix_cycle_ok = True
    if bool(fix_cycle_handoff_generation_input_available):
        fix_cycle_ok = bool(fix_cycle_handoff_generation_input_consumed) and bool(
            normalized_fix_cycle_kind in {"fix", "none"}
        )
    next_cycle_ok = True
    if bool(next_cycle_handoff_generation_input_available):
        next_cycle_ok = bool(next_cycle_handoff_generation_input_consumed) and bool(
            normalized_next_cycle_kind in {"next", "none"}
        )

    fix_ready = bool(
        normalized_fix_generation_status == "prompt_generated"
        and bool(fix_prompt_generated)
        and bool(fix_prompt_handoff_write_completed)
        and not bool(fix_prompt_handoff_write_failed)
        and not bool(fix_human_review_required)
        and fix_path_safe
        and fix_cycle_ok
    )
    next_ready = bool(
        normalized_next_generation_status == "prompt_generated"
        and bool(next_prompt_generated)
        and bool(next_prompt_handoff_write_completed)
        and not bool(next_prompt_handoff_write_failed)
        and not bool(next_human_review_required)
        and next_path_safe
        and next_cycle_ok
    )

    status = "insufficient_truth"
    reentry_allowed = False
    reentry_block_reason = "blocked_insufficient_reentry_truth"
    reentry_prompt_kind = "none"
    reentry_prompt_path = ""
    reentry_target = "none"
    should_update_prompt_selection = False
    should_update_invocation_readiness = False
    should_invoke_codex = False
    should_start_next_cycle = False
    should_rollback = False
    human_review_required = False
    next_action = "insufficient_truth"
    missing_inputs: list[str] = []

    if bool(fix_human_review_required) or bool(next_human_review_required):
        status = "reentry_blocked_human_review_required"
        reentry_block_reason = "blocked_human_review_required"
        reentry_target = "manual_review"
        human_review_required = True
        next_action = "manual_review_required"
    elif fix_ready and next_ready:
        status = "reentry_blocked_ambiguous_prompt_kind"
        reentry_block_reason = "blocked_ambiguous_fix_and_next_reentry"
        reentry_target = "manual_review"
        human_review_required = True
        next_action = "manual_review_required"
    elif fix_ready:
        status = "reentry_fix_prompt_ready"
        reentry_allowed = True
        reentry_block_reason = ""
        reentry_prompt_kind = "fix"
        reentry_prompt_path = normalized_fix_prompt_handoff_path
        reentry_target = "prompt_selection_and_codex_invocation_readiness"
        should_update_prompt_selection = True
        should_update_invocation_readiness = True
        human_review_required = False
        next_action = "prepare_fix_prompt_reentry"
    elif next_ready:
        status = "reentry_next_prompt_ready"
        reentry_allowed = True
        reentry_block_reason = ""
        reentry_prompt_kind = "next"
        reentry_prompt_path = normalized_next_prompt_handoff_path
        reentry_target = "prompt_selection_and_codex_invocation_readiness"
        should_update_prompt_selection = True
        should_update_invocation_readiness = True
        human_review_required = False
        next_action = "prepare_next_prompt_reentry"
    else:
        status = "reentry_blocked_insufficient_truth"
        reentry_block_reason = "blocked_insufficient_reentry_truth"
        reentry_target = "manual_review"
        human_review_required = True
        next_action = "manual_review_required"
        if normalized_fix_generation_status != "prompt_generated":
            missing_inputs.append("fix_generation_prompt_not_generated")
        if normalized_next_generation_status != "prompt_generated":
            missing_inputs.append("next_generation_prompt_not_generated")
        if not fix_path_safe and fix_path_block_reason:
            missing_inputs.append(f"fix:{fix_path_block_reason}")
        if not next_path_safe and next_path_block_reason:
            missing_inputs.append(f"next:{next_path_block_reason}")
        if (
            bool(fix_cycle_handoff_generation_input_available)
            and not fix_cycle_ok
            and normalized_fix_cycle_block_reason
        ):
            missing_inputs.append(f"fix:{normalized_fix_cycle_block_reason}")
        if (
            bool(next_cycle_handoff_generation_input_available)
            and not next_cycle_ok
            and normalized_next_cycle_block_reason
        ):
            missing_inputs.append(f"next:{normalized_next_cycle_block_reason}")

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if reentry_prompt_kind not in allowed_prompt_kinds:
        reentry_prompt_kind = "none"
    if reentry_target not in allowed_targets:
        reentry_target = "none"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"

    return {
        "project_browser_autonomous_generated_prompt_reentry_readiness_status": status,
        "project_browser_autonomous_generated_prompt_reentry_readiness_reentry_allowed": bool(
            reentry_allowed
        ),
        "project_browser_autonomous_generated_prompt_reentry_readiness_reentry_block_reason": (
            reentry_block_reason
        ),
        "project_browser_autonomous_generated_prompt_reentry_readiness_reentry_prompt_kind": (
            reentry_prompt_kind
        ),
        "project_browser_autonomous_generated_prompt_reentry_readiness_reentry_prompt_path": (
            reentry_prompt_path
        ),
        "project_browser_autonomous_generated_prompt_reentry_readiness_reentry_target": (
            reentry_target
        ),
        "project_browser_autonomous_generated_prompt_reentry_readiness_should_update_prompt_selection": bool(
            should_update_prompt_selection
        ),
        "project_browser_autonomous_generated_prompt_reentry_readiness_should_update_invocation_readiness": bool(
            should_update_invocation_readiness
        ),
        "project_browser_autonomous_generated_prompt_reentry_readiness_should_invoke_codex": bool(
            should_invoke_codex
        ),
        "project_browser_autonomous_generated_prompt_reentry_readiness_should_start_next_cycle": bool(
            should_start_next_cycle
        ),
        "project_browser_autonomous_generated_prompt_reentry_readiness_should_rollback": bool(
            should_rollback
        ),
        "project_browser_autonomous_generated_prompt_reentry_readiness_source_fix_generation_status": (
            normalized_fix_generation_status
        ),
        "project_browser_autonomous_generated_prompt_reentry_readiness_source_fix_prompt_generated": bool(
            fix_prompt_generated
        ),
        "project_browser_autonomous_generated_prompt_reentry_readiness_source_fix_prompt_handoff_write_completed": bool(
            fix_prompt_handoff_write_completed
        ),
        "project_browser_autonomous_generated_prompt_reentry_readiness_source_next_generation_status": (
            normalized_next_generation_status
        ),
        "project_browser_autonomous_generated_prompt_reentry_readiness_source_next_prompt_generated": bool(
            next_prompt_generated
        ),
        "project_browser_autonomous_generated_prompt_reentry_readiness_source_next_prompt_handoff_write_completed": bool(
            next_prompt_handoff_write_completed
        ),
        "project_browser_autonomous_generated_prompt_reentry_readiness_human_review_required": bool(
            human_review_required
        ),
        "project_browser_autonomous_generated_prompt_reentry_readiness_next_action": (
            next_action
        ),
        "project_browser_autonomous_generated_prompt_reentry_readiness_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_generated_prompt_reentry_readiness_missing_inputs": (
            _serialize_required_signals(missing_inputs)
        ),
        "project_browser_autonomous_generated_prompt_reentry_readiness_source_fix_next_action": (
            _normalize_text(fix_next_action, default="")
        ),
        "project_browser_autonomous_generated_prompt_reentry_readiness_source_next_next_action": (
            _normalize_text(next_next_action, default="")
        ),
    }

def _build_project_browser_autonomous_generated_prompt_reentry_routing_state(
    *,
    reentry_status: str,
    reentry_allowed: bool,
    reentry_prompt_kind: str,
    reentry_prompt_path: str,
    reentry_target: str,
    should_update_prompt_selection: bool,
    should_update_invocation_readiness: bool,
    should_invoke_codex: bool,
    should_start_next_cycle: bool,
    should_rollback: bool,
    human_review_required: bool,
    next_action: str,
    reentry_block_reason: str,
) -> dict[str, Any]:
    allowed_statuses = {
        "reentry_routing_fix_ready",
        "reentry_routing_next_ready",
        "reentry_routing_blocked",
        "reentry_routing_blocked_ambiguous",
        "reentry_routing_blocked_unsafe_path",
        "reentry_routing_blocked_insufficient_truth",
    }
    allowed_prompt_kinds = {"fix", "next", "none"}
    allowed_next_actions = {
        "prepare_bounded_reentry_codex_invocation",
        "manual_review_required",
        "insufficient_truth",
    }
    allowed_prompt_paths = {
        "/tmp/codex-local-runner-decision/generated_fix_prompt.txt",
        "/tmp/codex-local-runner-decision/generated_next_prompt.txt",
    }
    max_prompt_size_bytes = 20000
    runtime_posture = [
        "metadata_only_generated_prompt_reentry_routing",
        "no_codex_invocation",
        "no_prompt_generation",
        "no_prompt_execution",
        "no_git_mutation",
        "no_autonomous_loop",
    ]

    source_status = _normalize_text(reentry_status, default="insufficient_truth")
    normalized_prompt_kind = _normalize_text(reentry_prompt_kind, default="none")
    normalized_prompt_path = _normalize_text(reentry_prompt_path, default="")
    normalized_reentry_target = _normalize_text(reentry_target, default="")
    normalized_source_next_action = _normalize_text(next_action, default="")
    normalized_source_block_reason = _normalize_text(reentry_block_reason, default="")

    path_is_exact = normalized_prompt_path in allowed_prompt_paths
    prompt_path_obj = Path(normalized_prompt_path) if normalized_prompt_path else None
    path_exists = bool(prompt_path_obj and prompt_path_obj.exists())
    path_is_file = bool(prompt_path_obj and prompt_path_obj.is_file())
    path_is_symlink = bool(prompt_path_obj and prompt_path_obj.is_symlink())
    size_bytes = 0
    if prompt_path_obj and path_exists and path_is_file and not path_is_symlink:
        try:
            size_bytes = _as_non_negative_int(prompt_path_obj.stat().st_size, default=0)
        except OSError:
            size_bytes = 0
    file_non_empty = size_bytes > 0
    file_too_large = size_bytes > max_prompt_size_bytes
    path_safe = bool(
        path_is_exact
        and path_exists
        and path_is_file
        and not path_is_symlink
        and file_non_empty
        and not file_too_large
    )

    status = "reentry_routing_blocked_insufficient_truth"
    reentry_routing_allowed = False
    reentry_routing_block_reason = "blocked_insufficient_reentry_truth"
    selection_refresh_allowed = False
    selection_refresh_kind = "none"
    selection_refresh_path = ""
    invocation_readiness_refresh_allowed = False
    write_invocation_reentry_prepared = False
    next_action_out = "manual_review_required"
    missing_inputs: list[str] = []

    if bool(human_review_required):
        status = "reentry_routing_blocked"
        reentry_routing_block_reason = "blocked_human_review_required"
        next_action_out = "manual_review_required"
    elif source_status == "reentry_blocked_ambiguous_prompt_kind" or (
        normalized_source_block_reason == "blocked_ambiguous_fix_and_next_reentry"
    ):
        status = "reentry_routing_blocked_ambiguous"
        reentry_routing_block_reason = "blocked_ambiguous_fix_and_next_reentry"
        next_action_out = "manual_review_required"
    elif bool(reentry_allowed) and not path_safe:
        status = "reentry_routing_blocked_unsafe_path"
        if not normalized_prompt_path:
            reentry_routing_block_reason = "blocked_prompt_path_missing"
            missing_inputs.append("reentry_prompt_path")
        elif not path_is_exact:
            reentry_routing_block_reason = "blocked_prompt_path_unexpected"
        elif path_is_symlink:
            reentry_routing_block_reason = "blocked_prompt_path_symlink"
        elif not path_exists:
            reentry_routing_block_reason = "blocked_prompt_path_missing"
        elif not path_is_file:
            reentry_routing_block_reason = "blocked_prompt_path_not_file"
        elif not file_non_empty:
            reentry_routing_block_reason = "blocked_prompt_empty"
        elif file_too_large:
            reentry_routing_block_reason = "blocked_prompt_too_large"
        else:
            reentry_routing_block_reason = "blocked_prompt_path_unexpected"
        next_action_out = "manual_review_required"
    elif (
        bool(reentry_allowed)
        and not bool(human_review_required)
        and normalized_prompt_kind == "fix"
        and path_safe
    ):
        status = "reentry_routing_fix_ready"
        reentry_routing_allowed = True
        reentry_routing_block_reason = ""
        selection_refresh_allowed = bool(should_update_prompt_selection)
        selection_refresh_kind = "fix"
        selection_refresh_path = normalized_prompt_path
        invocation_readiness_refresh_allowed = bool(
            selection_refresh_allowed and should_update_invocation_readiness
        )
        write_invocation_reentry_prepared = bool(invocation_readiness_refresh_allowed)
        next_action_out = "prepare_bounded_reentry_codex_invocation"
    elif (
        bool(reentry_allowed)
        and not bool(human_review_required)
        and normalized_prompt_kind == "next"
        and path_safe
    ):
        status = "reentry_routing_next_ready"
        reentry_routing_allowed = True
        reentry_routing_block_reason = ""
        selection_refresh_allowed = bool(should_update_prompt_selection)
        selection_refresh_kind = "next"
        selection_refresh_path = normalized_prompt_path
        invocation_readiness_refresh_allowed = bool(
            selection_refresh_allowed and should_update_invocation_readiness
        )
        write_invocation_reentry_prepared = bool(invocation_readiness_refresh_allowed)
        next_action_out = "prepare_bounded_reentry_codex_invocation"
    else:
        status = "reentry_routing_blocked_insufficient_truth"
        reentry_routing_block_reason = "blocked_insufficient_reentry_truth"
        next_action_out = "manual_review_required"
        if normalized_source_block_reason:
            missing_inputs.append(normalized_source_block_reason)
        if not normalized_prompt_kind or normalized_prompt_kind == "none":
            missing_inputs.append("reentry_prompt_kind")
        if not normalized_prompt_path:
            missing_inputs.append("reentry_prompt_path")
        if not normalized_reentry_target:
            missing_inputs.append("reentry_target")

    if status not in allowed_statuses:
        status = "reentry_routing_blocked_insufficient_truth"
    if selection_refresh_kind not in allowed_prompt_kinds:
        selection_refresh_kind = "none"
    if normalized_prompt_kind not in allowed_prompt_kinds:
        normalized_prompt_kind = "none"
    if next_action_out not in allowed_next_actions:
        next_action_out = "insufficient_truth"

    return {
        "project_browser_autonomous_generated_prompt_reentry_routing_status": status,
        "project_browser_autonomous_generated_prompt_reentry_routing_reentry_routing_allowed": bool(
            reentry_routing_allowed
        ),
        "project_browser_autonomous_generated_prompt_reentry_routing_reentry_routing_block_reason": (
            reentry_routing_block_reason
        ),
        "project_browser_autonomous_generated_prompt_reentry_routing_reentry_prompt_kind": (
            normalized_prompt_kind
        ),
        "project_browser_autonomous_generated_prompt_reentry_routing_reentry_prompt_path": (
            normalized_prompt_path
        ),
        "project_browser_autonomous_generated_prompt_reentry_routing_selection_refresh_allowed": bool(
            selection_refresh_allowed
        ),
        "project_browser_autonomous_generated_prompt_reentry_routing_selection_refresh_kind": (
            selection_refresh_kind
        ),
        "project_browser_autonomous_generated_prompt_reentry_routing_selection_refresh_path": (
            selection_refresh_path
        ),
        "project_browser_autonomous_generated_prompt_reentry_routing_invocation_readiness_refresh_allowed": bool(
            invocation_readiness_refresh_allowed
        ),
        "project_browser_autonomous_generated_prompt_reentry_routing_write_invocation_reentry_prepared": bool(
            write_invocation_reentry_prepared
        ),
        "project_browser_autonomous_generated_prompt_reentry_routing_max_reentry_invocations": 1,
        "project_browser_autonomous_generated_prompt_reentry_routing_should_invoke_codex": bool(
            False
        ),
        "project_browser_autonomous_generated_prompt_reentry_routing_should_start_next_cycle": bool(
            False
        ),
        "project_browser_autonomous_generated_prompt_reentry_routing_should_rollback": bool(
            False
        ),
        "project_browser_autonomous_generated_prompt_reentry_routing_human_review_required": bool(
            bool(human_review_required) or not bool(reentry_routing_allowed)
        ),
        "project_browser_autonomous_generated_prompt_reentry_routing_next_action": (
            next_action_out
        ),
        "project_browser_autonomous_generated_prompt_reentry_routing_runtime_posture": runtime_posture,
        "project_browser_autonomous_generated_prompt_reentry_routing_missing_inputs": (
            _serialize_required_signals(missing_inputs)
        ),
        "project_browser_autonomous_generated_prompt_reentry_routing_source_status": (
            source_status
        ),
        "project_browser_autonomous_generated_prompt_reentry_routing_source_next_action": (
            normalized_source_next_action
        ),
        "project_browser_autonomous_generated_prompt_reentry_routing_source_block_reason": (
            normalized_source_block_reason
        ),
        "project_browser_autonomous_generated_prompt_reentry_routing_source_target": (
            normalized_reentry_target
        ),
        "project_browser_autonomous_generated_prompt_reentry_routing_source_should_invoke_codex": bool(
            should_invoke_codex
        ),
        "project_browser_autonomous_generated_prompt_reentry_routing_source_should_start_next_cycle": bool(
            should_start_next_cycle
        ),
        "project_browser_autonomous_generated_prompt_reentry_routing_source_should_rollback": bool(
            should_rollback
        ),
        "project_browser_autonomous_generated_prompt_reentry_routing_reentry_prompt_path_is_exact": bool(
            path_is_exact
        ),
        "project_browser_autonomous_generated_prompt_reentry_routing_reentry_prompt_path_exists": bool(
            path_exists
        ),
        "project_browser_autonomous_generated_prompt_reentry_routing_reentry_prompt_path_is_symlink": bool(
            path_is_symlink
        ),
        "project_browser_autonomous_generated_prompt_reentry_routing_reentry_prompt_file_non_empty": bool(
            file_non_empty
        ),
        "project_browser_autonomous_generated_prompt_reentry_routing_reentry_prompt_file_too_large": bool(
            file_too_large
        ),
    }

def _build_project_browser_autonomous_pr_prompt_generation_state(
    *,
    repo_path: str,
    project_request_text: str,
    roadmap_pr_split_queue_state: Mapping[str, Any],
) -> dict[str, Any]:
    normalized_project_request_text = _normalize_text(project_request_text, default="")
    roadmap_ready = bool(
        roadmap_pr_split_queue_state.get(
            "project_browser_autonomous_roadmap_pr_split_queue_roadmap_available",
            False,
        )
    )
    active_pr_index = _as_non_negative_int(
        roadmap_pr_split_queue_state.get(
            "project_browser_autonomous_roadmap_pr_split_queue_active_pr_index"
        ),
        default=0,
    )
    active_pr = roadmap_pr_split_queue_state.get(
        "project_browser_autonomous_roadmap_pr_split_queue_active_pr"
    )
    active_pr_payload = dict(active_pr) if isinstance(active_pr, Mapping) else {}

    status = "pr_prompt_generation_waiting_for_roadmap_or_pr_metadata"
    ready = False
    active_pr_title = ""
    generated_prompt = ""
    prompt_ready = False
    next_action = "run_chatgpt_project_analysis_and_roadmap_split"

    if not normalized_project_request_text:
        status = "pr_prompt_generation_blocked_project_request_missing"
        next_action = "provide_project_request"
    elif roadmap_ready and active_pr_payload:
        ready = True
        prompt_ready = True
        status = "pr_prompt_generation_ready"
        next_action = "handoff_prompt_to_codex"
        active_pr_title = _normalize_text(
            active_pr_payload.get("title", active_pr_payload.get("pr_title")),
            default="",
        )
        active_pr_goal = _normalize_text(
            active_pr_payload.get(
                "goal",
                active_pr_payload.get(
                    "scope",
                    active_pr_payload.get("summary", active_pr_title),
                ),
            ),
            default="",
        )
        target_files = _normalize_string_list(active_pr_payload.get("target_files"))
        validation_commands = _normalize_string_list(
            active_pr_payload.get("validation_commands")
        ) or [
            "python -m py_compile automation/orchestration/planned_execution_runner.py",
            "python -m py_compile scripts/run_planned_execution.py",
        ]
        forbidden_actions = [
            "no tests",
            "no docs",
            "no new files",
            "no new external executors",
            "no network calls",
            "no shell command execution paths",
            "no git mutation paths",
        ]
        generated_prompt_lines = [
            "Implement one PR slice for autonomous development MVP control spine.",
            f"Repo: {repo_path}",
            f"PR Goal/Scope: {active_pr_goal}",
            "Target files:",
        ]
        if target_files:
            generated_prompt_lines.extend([f"- {path}" for path in target_files])
        else:
            generated_prompt_lines.append("- automation/orchestration/planned_execution_runner.py")
        generated_prompt_lines.extend(
            [
                "forbidden_actions:",
                *[f"- {action}" for action in forbidden_actions],
                "Validation:",
                *[f"- {command}" for command in validation_commands],
                "expected_return_format:",
                "- files changed",
                "- builders added",
                "- exposure locations",
                "- validation results",
                "- key status/next_action values",
            ]
        )
        generated_prompt = "\n".join(generated_prompt_lines)

    return {
        "project_browser_autonomous_pr_prompt_generation_status": status,
        "project_browser_autonomous_pr_prompt_generation_source": (
            "prompt252_pr_prompt_generation"
        ),
        "project_browser_autonomous_pr_prompt_generation_ready": bool(ready),
        "project_browser_autonomous_pr_prompt_generation_active_pr_index": active_pr_index,
        "project_browser_autonomous_pr_prompt_generation_active_pr_title": active_pr_title,
        "project_browser_autonomous_pr_prompt_generation_generated_prompt": generated_prompt,
        "project_browser_autonomous_pr_prompt_generation_prompt_ready": bool(prompt_ready),
        "project_browser_autonomous_pr_prompt_generation_next_action": next_action,
    }

def _build_project_browser_autonomous_dev_loop_pr_prompt_readiness_state(
    *,
    project_intake_state: Mapping[str, Any],
    project_analysis_request_state: Mapping[str, Any],
    roadmap_pr_split_queue_state: Mapping[str, Any],
    pr_prompt_generation_state: Mapping[str, Any],
    codex_handoff_state: Mapping[str, Any],
) -> dict[str, Any]:
    project_request_detected = bool(
        project_intake_state.get(
            "project_browser_autonomous_project_intake_project_request_detected",
            False,
        )
    )
    analysis_ready = bool(
        project_analysis_request_state.get(
            "project_browser_autonomous_project_analysis_request_result_available",
            False,
        )
    )
    roadmap_ready = bool(
        roadmap_pr_split_queue_state.get(
            "project_browser_autonomous_roadmap_pr_split_queue_roadmap_available",
            False,
        )
    )
    active_pr_index = _as_non_negative_int(
        roadmap_pr_split_queue_state.get(
            "project_browser_autonomous_roadmap_pr_split_queue_active_pr_index"
        ),
        default=0,
    )
    active_pr_title = _normalize_text(
        pr_prompt_generation_state.get(
            "project_browser_autonomous_pr_prompt_generation_active_pr_title"
        ),
        default="",
    )
    pr_prompt_ready = bool(
        pr_prompt_generation_state.get(
            "project_browser_autonomous_pr_prompt_generation_prompt_ready",
            False,
        )
    )
    codex_handoff_ready = bool(
        codex_handoff_state.get("project_browser_autonomous_codex_handoff_ready", False)
    )
    generated_prompt = _normalize_text(
        pr_prompt_generation_state.get(
            "project_browser_autonomous_pr_prompt_generation_generated_prompt"
        ),
        default="",
    )
    generated_prompt_excerpt = generated_prompt[:280] if generated_prompt else ""
    if generated_prompt:
        prompt_lines = generated_prompt.splitlines()
        repo_line = next(
            (
                line
                for line in prompt_lines
                if _normalize_text(line, default="").startswith("Repo:")
            ),
            "",
        )
        validation_line = next(
            (
                line
                for line in prompt_lines
                if _normalize_text(line, default="").startswith("Validation:")
            ),
            "",
        )
        if repo_line and validation_line:
            generated_prompt_excerpt = f"{repo_line} | {validation_line}"
    generated_prompt_length = len(generated_prompt)

    status = "pr_prompt_readiness_waiting_for_pr_prompt"
    next_action = "generate_next_pr_prompt"
    if pr_prompt_ready and codex_handoff_ready:
        status = "pr_prompt_readiness_ready_for_codex_handoff"
        next_action = "await_codex_result"
    elif not project_request_detected:
        status = "pr_prompt_readiness_waiting_for_project_request"
        next_action = "provide_project_request"
    elif not analysis_ready:
        status = "pr_prompt_readiness_waiting_for_project_analysis"
        next_action = "run_chatgpt_project_analysis"
    elif not roadmap_ready:
        status = "pr_prompt_readiness_waiting_for_roadmap_pr_split"
        next_action = "run_chatgpt_roadmap_pr_split"

    return {
        "project_browser_autonomous_dev_loop_pr_prompt_readiness_status": status,
        "project_browser_autonomous_dev_loop_pr_prompt_readiness_source": (
            "prompt253_dev_loop_pr_prompt_readiness"
        ),
        "project_browser_autonomous_dev_loop_pr_prompt_readiness_project_request_detected": bool(
            project_request_detected
        ),
        "project_browser_autonomous_dev_loop_pr_prompt_readiness_analysis_ready": bool(
            analysis_ready
        ),
        "project_browser_autonomous_dev_loop_pr_prompt_readiness_roadmap_ready": bool(
            roadmap_ready
        ),
        "project_browser_autonomous_dev_loop_pr_prompt_readiness_active_pr_index": active_pr_index,
        "project_browser_autonomous_dev_loop_pr_prompt_readiness_active_pr_title": active_pr_title,
        "project_browser_autonomous_dev_loop_pr_prompt_readiness_pr_prompt_ready": bool(
            pr_prompt_ready
        ),
        "project_browser_autonomous_dev_loop_pr_prompt_readiness_codex_handoff_ready": bool(
            codex_handoff_ready
        ),
        "project_browser_autonomous_dev_loop_pr_prompt_readiness_generated_prompt_excerpt": (
            generated_prompt_excerpt
        ),
        "project_browser_autonomous_dev_loop_pr_prompt_readiness_generated_prompt_length": (
            generated_prompt_length
        ),
        "project_browser_autonomous_dev_loop_pr_prompt_readiness_next_action": next_action,
    }

def _build_project_browser_autonomous_prompt_selection_state(
    *,
    validation_passed: bool,
    validation_failed: bool,
    rollback_required: bool,
    human_review_required: bool,
    insufficient_truth: bool,
    fix_required_path_active: bool,
    fix_prompt_status: str,
    fix_prompt_generated: bool,
    fix_prompt_body: str,
    fix_prompt_handoff_path: str,
    fix_prompt_handoff_write_completed: bool,
    fix_prompt_handoff_write_failed: bool,
    next_prompt_status: str,
    next_prompt_generated: bool,
    next_prompt_body: str,
    next_prompt_handoff_path: str,
    next_prompt_handoff_write_completed: bool,
    next_prompt_handoff_write_failed: bool,
) -> dict[str, Any]:
    allowed_statuses = {
        "selected_fix_prompt",
        "selected_next_prompt",
        "blocked_no_ready_prompt",
        "blocked_conflicting_prompts",
        "blocked_handoff_write_failed",
        "blocked_prompt_path_missing",
        "blocked_prompt_path_unexpected",
        "blocked_prompt_path_symlink",
        "blocked_prompt_body_missing",
        "blocked_insufficient_truth",
        "blocked_human_review_required",
        "blocked_rollback_required",
        "insufficient_truth",
    }
    allowed_prompt_kinds = {"fix", "next", "none"}
    allowed_next_actions = {
        "check_codex_invocation_readiness_later",
        "wait_for_fix_prompt_generation",
        "wait_for_next_prompt_generation",
        "wait_for_more_truth",
        "manual_review_required",
        "rollback_required",
        "manual_prompt_selection_required",
        "insufficient_truth",
    }
    fix_allowed_path = "/tmp/codex-local-runner-decision/generated_fix_prompt.txt"
    next_allowed_path = "/tmp/codex-local-runner-decision/generated_next_prompt.txt"
    runtime_posture = [
        "prompt_selection_controller",
        "metadata_only_selection",
        "no_prompt_generation",
        "no_prompt_execution",
        "no_external_model_invocation",
        "no_patch_apply",
        "no_git_mutation",
        "no_autonomous_loop",
    ]

    normalized_fix_prompt_status = _normalize_text(
        fix_prompt_status,
        default="insufficient_truth",
    )
    normalized_next_prompt_status = _normalize_text(
        next_prompt_status,
        default="insufficient_truth",
    )
    normalized_fix_path = _normalize_text(fix_prompt_handoff_path, default="")
    normalized_next_path = _normalize_text(next_prompt_handoff_path, default="")
    normalized_fix_body = _normalize_text(fix_prompt_body, default="")
    normalized_next_body = _normalize_text(next_prompt_body, default="")

    fix_path_obj = Path(normalized_fix_path) if normalized_fix_path else None
    next_path_obj = Path(normalized_next_path) if normalized_next_path else None
    fix_path_is_exact = normalized_fix_path == fix_allowed_path
    next_path_is_exact = normalized_next_path == next_allowed_path
    fix_path_exists = bool(fix_path_obj and fix_path_obj.exists())
    next_path_exists = bool(next_path_obj and next_path_obj.exists())
    fix_path_is_symlink = bool(fix_path_obj and fix_path_obj.is_symlink())
    next_path_is_symlink = bool(next_path_obj and next_path_obj.is_symlink())
    fix_body_available = bool(normalized_fix_body)
    next_body_available = bool(normalized_next_body)

    fix_candidate_valid = (
        (bool(validation_failed) or bool(fix_required_path_active))
        and normalized_fix_prompt_status == "prompt_generated"
        and bool(fix_prompt_generated)
        and fix_path_is_exact
        and bool(fix_prompt_handoff_write_completed)
        and not bool(fix_prompt_handoff_write_failed)
        and fix_body_available
        and fix_path_exists
        and not fix_path_is_symlink
    )
    next_candidate_valid = (
        bool(validation_passed)
        and not bool(validation_failed)
        and normalized_next_prompt_status == "prompt_generated"
        and bool(next_prompt_generated)
        and next_path_is_exact
        and bool(next_prompt_handoff_write_completed)
        and not bool(next_prompt_handoff_write_failed)
        and next_body_available
        and next_path_exists
        and not next_path_is_symlink
    )

    status = "insufficient_truth"
    source_status = "insufficient_truth"
    block_reason = "insufficient_truth"
    selected_prompt_kind = "none"
    selected_prompt_path = ""
    selected_prompt_source = ""
    selected_prompt_ready = False
    selected_prompt_body_available = False
    selected_prompt_handoff_write_completed = False
    selected_prompt_handoff_write_failed = False
    selected_prompt_path_is_exact = False
    selected_prompt_path_exists = False
    selected_prompt_path_is_symlink = False
    next_action = "insufficient_truth"
    missing_inputs: list[str] = []

    if rollback_required:
        status = "blocked_rollback_required"
        source_status = "rollback_required"
        block_reason = "rollback_required"
        next_action = "rollback_required"
    elif human_review_required:
        status = "blocked_human_review_required"
        source_status = "human_review_required"
        block_reason = "human_review_required"
        next_action = "manual_review_required"
    elif insufficient_truth:
        status = "blocked_insufficient_truth"
        source_status = "insufficient_truth_active"
        block_reason = "insufficient_truth"
        next_action = "wait_for_more_truth"
        missing_inputs.append("prompt_selection_truth")
    elif fix_candidate_valid and next_candidate_valid:
        status = "blocked_conflicting_prompts"
        source_status = "multiple_candidates_ready"
        block_reason = "conflicting_ready_prompts"
        next_action = "manual_prompt_selection_required"
    elif fix_candidate_valid:
        status = "selected_fix_prompt"
        source_status = "fix_prompt_selected"
        block_reason = "none"
        selected_prompt_kind = "fix"
        selected_prompt_path = normalized_fix_path
        selected_prompt_source = "project_browser_autonomous_fix_prompt_generation"
        selected_prompt_ready = True
        selected_prompt_body_available = fix_body_available
        selected_prompt_handoff_write_completed = bool(fix_prompt_handoff_write_completed)
        selected_prompt_handoff_write_failed = bool(fix_prompt_handoff_write_failed)
        selected_prompt_path_is_exact = fix_path_is_exact
        selected_prompt_path_exists = fix_path_exists
        selected_prompt_path_is_symlink = fix_path_is_symlink
        next_action = "check_codex_invocation_readiness_later"
    elif next_candidate_valid:
        status = "selected_next_prompt"
        source_status = "next_prompt_selected"
        block_reason = "none"
        selected_prompt_kind = "next"
        selected_prompt_path = normalized_next_path
        selected_prompt_source = "project_browser_autonomous_next_prompt_generation"
        selected_prompt_ready = True
        selected_prompt_body_available = next_body_available
        selected_prompt_handoff_write_completed = bool(next_prompt_handoff_write_completed)
        selected_prompt_handoff_write_failed = bool(next_prompt_handoff_write_failed)
        selected_prompt_path_is_exact = next_path_is_exact
        selected_prompt_path_exists = next_path_exists
        selected_prompt_path_is_symlink = next_path_is_symlink
        next_action = "check_codex_invocation_readiness_later"
    else:
        status = "blocked_no_ready_prompt"
        source_status = "no_valid_prompt_candidate"
        block_reason = "no_ready_prompt_candidate"
        if validation_failed or fix_required_path_active:
            next_action = "wait_for_fix_prompt_generation"
        elif validation_passed and not validation_failed:
            next_action = "wait_for_next_prompt_generation"
        else:
            next_action = "wait_for_more_truth"

        if validation_failed or fix_required_path_active:
            if normalized_fix_prompt_status != "prompt_generated":
                missing_inputs.append("fix_prompt_status_prompt_generated")
            if not fix_path_is_exact:
                status = "blocked_prompt_path_unexpected"
                source_status = "fix_prompt_path_not_exact"
                block_reason = "selected_prompt_path_unexpected"
            elif bool(fix_prompt_handoff_write_failed):
                status = "blocked_handoff_write_failed"
                source_status = "fix_handoff_write_failed"
                block_reason = "selected_handoff_write_failed"
            elif not bool(fix_prompt_handoff_write_completed):
                missing_inputs.append("fix_handoff_write_completed")
            elif fix_path_is_symlink:
                status = "blocked_prompt_path_symlink"
                source_status = "fix_prompt_path_symlink"
                block_reason = "selected_prompt_path_symlink"
            elif not fix_path_exists:
                status = "blocked_prompt_path_missing"
                source_status = "fix_prompt_path_missing"
                block_reason = "selected_prompt_path_missing"
            elif not fix_body_available:
                status = "blocked_prompt_body_missing"
                source_status = "fix_prompt_body_missing"
                block_reason = "selected_prompt_body_missing"
        elif validation_passed and not validation_failed:
            if normalized_next_prompt_status != "prompt_generated":
                missing_inputs.append("next_prompt_status_prompt_generated")
            if not next_path_is_exact:
                status = "blocked_prompt_path_unexpected"
                source_status = "next_prompt_path_not_exact"
                block_reason = "selected_prompt_path_unexpected"
            elif bool(next_prompt_handoff_write_failed):
                status = "blocked_handoff_write_failed"
                source_status = "next_handoff_write_failed"
                block_reason = "selected_handoff_write_failed"
            elif not bool(next_prompt_handoff_write_completed):
                missing_inputs.append("next_handoff_write_completed")
            elif next_path_is_symlink:
                status = "blocked_prompt_path_symlink"
                source_status = "next_prompt_path_symlink"
                block_reason = "selected_prompt_path_symlink"
            elif not next_path_exists:
                status = "blocked_prompt_path_missing"
                source_status = "next_prompt_path_missing"
                block_reason = "selected_prompt_path_missing"
            elif not next_body_available:
                status = "blocked_prompt_body_missing"
                source_status = "next_prompt_body_missing"
                block_reason = "selected_prompt_body_missing"

    if selected_prompt_kind not in allowed_prompt_kinds:
        selected_prompt_kind = "none"
    if status not in allowed_statuses:
        status = "insufficient_truth"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"

    return {
        "project_browser_autonomous_prompt_selection_status": status,
        "project_browser_autonomous_prompt_selection_source_status": source_status,
        "project_browser_autonomous_prompt_selection_block_reason": block_reason,
        "project_browser_autonomous_prompt_selection_selected_prompt_kind": (
            selected_prompt_kind
        ),
        "project_browser_autonomous_prompt_selection_selected_prompt_path": (
            selected_prompt_path
        ),
        "project_browser_autonomous_prompt_selection_selected_prompt_source": (
            selected_prompt_source
        ),
        "project_browser_autonomous_prompt_selection_selected_prompt_ready": bool(
            selected_prompt_ready
        ),
        "project_browser_autonomous_prompt_selection_selected_prompt_body_available": bool(
            selected_prompt_body_available
        ),
        "project_browser_autonomous_prompt_selection_selected_prompt_handoff_write_completed": bool(
            selected_prompt_handoff_write_completed
        ),
        "project_browser_autonomous_prompt_selection_selected_prompt_handoff_write_failed": bool(
            selected_prompt_handoff_write_failed
        ),
        "project_browser_autonomous_prompt_selection_selected_prompt_path_is_exact": bool(
            selected_prompt_path_is_exact
        ),
        "project_browser_autonomous_prompt_selection_selected_prompt_path_exists": bool(
            selected_prompt_path_exists
        ),
        "project_browser_autonomous_prompt_selection_selected_prompt_path_is_symlink": bool(
            selected_prompt_path_is_symlink
        ),
        "project_browser_autonomous_prompt_selection_fix_prompt_status": (
            normalized_fix_prompt_status
        ),
        "project_browser_autonomous_prompt_selection_fix_prompt_generated": bool(
            fix_prompt_generated
        ),
        "project_browser_autonomous_prompt_selection_fix_prompt_handoff_path": (
            normalized_fix_path
        ),
        "project_browser_autonomous_prompt_selection_fix_prompt_handoff_write_completed": bool(
            fix_prompt_handoff_write_completed
        ),
        "project_browser_autonomous_prompt_selection_fix_prompt_handoff_write_failed": bool(
            fix_prompt_handoff_write_failed
        ),
        "project_browser_autonomous_prompt_selection_next_prompt_status": (
            normalized_next_prompt_status
        ),
        "project_browser_autonomous_prompt_selection_next_prompt_generated": bool(
            next_prompt_generated
        ),
        "project_browser_autonomous_prompt_selection_next_prompt_handoff_path": (
            normalized_next_path
        ),
        "project_browser_autonomous_prompt_selection_next_prompt_handoff_write_completed": bool(
            next_prompt_handoff_write_completed
        ),
        "project_browser_autonomous_prompt_selection_next_prompt_handoff_write_failed": bool(
            next_prompt_handoff_write_failed
        ),
        "project_browser_autonomous_prompt_selection_validation_passed": bool(
            validation_passed
        ),
        "project_browser_autonomous_prompt_selection_validation_failed": bool(
            validation_failed
        ),
        "project_browser_autonomous_prompt_selection_rollback_required": bool(
            rollback_required
        ),
        "project_browser_autonomous_prompt_selection_human_review_required": bool(
            human_review_required
        ),
        "project_browser_autonomous_prompt_selection_insufficient_truth": bool(
            insufficient_truth
        ),
        "project_browser_autonomous_prompt_selection_next_action": next_action,
        "project_browser_autonomous_prompt_selection_runtime_posture": runtime_posture,
        "project_browser_autonomous_prompt_selection_missing_inputs": (
            _serialize_required_signals(missing_inputs)
        ),
    }

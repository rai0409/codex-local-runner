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
def _build_project_browser_autonomous_next_local_codex_prompt_state() -> dict[str, Any]:
    next_dev_slice_dir = Path("/tmp/codex-local-runner-decision/next_dev_slice")
    next_codex_prompt_dir = Path("/tmp/codex-local-runner-decision/next_codex_prompt")

    input_next_dev_slice_json = next_dev_slice_dir / "next_dev_slice.json"
    input_next_dev_slice_summary = next_dev_slice_dir / "next_dev_slice_summary.md"
    output_prompt_path = next_codex_prompt_dir / "codex_implementation_prompt.md"
    output_request_path = next_codex_prompt_dir / "codex_implementation_request.json"
    output_summary_path = next_codex_prompt_dir / "codex_implementation_summary.md"

    runtime_posture = [
        "metadata_only_prompt_generation",
        "no_codex_invocation",
        "no_prompt_execution",
        "no_commit_tag_push_pr_merge",
        "no_daemon_loop_no_unbounded_retry",
    ]

    status = "next_local_codex_prompt_blocked_missing_next_dev_slice"
    next_action = "manual_review_required"
    blocked_reason = "next_dev_slice_missing"
    source_slice_id = ""
    execution_status = "not_started"
    codex_invocation_status = "not_started"
    review_status = "not_started"
    commit_tag_status = "not_started"
    push_status = "not_started"
    selected_slice_goal = ""
    selected_slice_scope = ""
    concrete_prompt298_goal = ""

    request_payload: dict[str, Any] = {
        "status": status,
        "next_action": next_action,
        "blocked_reason": blocked_reason,
        "source_slice_id": source_slice_id,
        "execution_status": execution_status,
        "codex_invocation_status": codex_invocation_status,
        "review_status": review_status,
        "commit_tag_status": commit_tag_status,
        "push_status": push_status,
        "input_artifacts": {
            "next_dev_slice_json": str(input_next_dev_slice_json),
            "next_dev_slice_summary_md": str(input_next_dev_slice_summary),
        },
        "output_artifacts": {
            "codex_implementation_prompt_md": str(output_prompt_path),
            "codex_implementation_request_json": str(output_request_path),
            "codex_implementation_summary_md": str(output_summary_path),
        },
        "runtime_posture": runtime_posture,
    }

    prompt_lines: list[str] = [
        "# Local Codex Implement Prompt (Bounded Metadata-Only)",
        "",
        "- Mode: `Implement`",
        "- Goal: blocked because `next_dev_slice` input is missing or invalid.",
    ]

    if not input_next_dev_slice_json.exists():
        blocked_reason = "next_dev_slice_missing"
        status = "next_local_codex_prompt_blocked_missing_next_dev_slice"
    elif not input_next_dev_slice_summary.exists():
        blocked_reason = "next_dev_slice_summary_missing"
        status = "next_local_codex_prompt_blocked_missing_next_dev_slice_summary"
    else:
        try:
            next_dev_slice_payload = json.loads(input_next_dev_slice_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            blocked_reason = "next_dev_slice_invalid_json"
            status = "next_local_codex_prompt_blocked_invalid_next_dev_slice"
        else:
            if not isinstance(next_dev_slice_payload, Mapping):
                blocked_reason = "next_dev_slice_not_object"
                status = "next_local_codex_prompt_blocked_invalid_next_dev_slice"
            else:
                slice_status = _normalize_text(next_dev_slice_payload.get("status"), default="")
                slice_next_action = _normalize_text(next_dev_slice_payload.get("next_action"), default="")
                selected_slice_count = _as_non_negative_int(
                    next_dev_slice_payload.get("selected_slice_count"),
                    default=0,
                )
                selected_slices = (
                    list(next_dev_slice_payload.get("selected_slices", []))
                    if isinstance(next_dev_slice_payload.get("selected_slices"), list)
                    else []
                )
                selected_slice = selected_slices[0] if selected_slices else {}
                if not isinstance(selected_slice, Mapping):
                    selected_slice = {}
                source_slice_id = _normalize_text(selected_slice.get("slice_id"), default="")
                selected_slice_goal = _normalize_text(selected_slice.get("goal"), default="")
                selected_slice_scope = _normalize_text(selected_slice.get("scope"), default="")
                concrete_prompt298_goal = _build_concrete_prompt298_goal_from_next_dev_slice(
                    selected_slice_goal
                )

                if slice_status != "next_dev_slice_generated":
                    blocked_reason = "next_dev_slice_status_not_generated"
                    status = "next_local_codex_prompt_blocked_invalid_next_dev_slice"
                elif slice_next_action != "prepare_next_local_codex_prompt":
                    blocked_reason = "next_dev_slice_next_action_not_prepare_next_local_codex_prompt"
                    status = "next_local_codex_prompt_blocked_invalid_next_dev_slice"
                elif selected_slice_count != 1:
                    blocked_reason = "next_dev_slice_selected_count_not_one"
                    status = "next_local_codex_prompt_blocked_invalid_next_dev_slice"
                elif source_slice_id != "next-local-codex-prompt-from-next-dev-slice":
                    blocked_reason = "next_dev_slice_id_mismatch"
                    status = "next_local_codex_prompt_blocked_invalid_next_dev_slice"
                else:
                    blocked_reason = "none"
                    status = "next_local_codex_prompt_generated"
                    next_action = "ready_for_bounded_local_codex_implementation"
                    prompt_lines = [
                        "# Prompt298: Implement Local Codex Execution Readiness (Metadata-Only)",
                        "",
                        "- Mode: `Implement`",
                        "",
                        "## Goal",
                        concrete_prompt298_goal,
                        "",
                        "## Allowed Files",
                        "- `automation/orchestration/planned_execution_runner.py`",
                        "- If absolutely necessary, only files required to keep this path syntactically valid.",
                        "",
                        "## Forbidden Files",
                        "- Any file outside the allowed scope unless absolutely necessary for imports or strict runtime safety.",
                        "",
                        "## Required Input",
                        f"- `{output_prompt_path}`",
                        f"- `{output_request_path}`",
                        f"- `{output_summary_path}`",
                        "",
                        "## Expected Artifacts",
                        "- `/tmp/codex-local-runner-decision/local_codex_execution_readiness/local_codex_execution_readiness.json`",
                        "- `/tmp/codex-local-runner-decision/local_codex_execution_readiness/local_codex_execution_summary.md`",
                        "- `/tmp/codex-local-runner-decision/local_codex_execution_readiness/local_codex_exec_plan.sh`",
                        "",
                        "## Required Behavior",
                        "- Read the three `next_codex_prompt` artifacts and verify:",
                        "  - request `status=next_local_codex_prompt_generated`",
                        "  - request `next_action=ready_for_bounded_local_codex_implementation`",
                        "  - request `blocked_reason=none`",
                        "- Confirm `codex_implementation_prompt.md` exists and is non-empty.",
                        "- Confirm the prompt is intended for a later local codex exec run only.",
                        "- Confirm the prompt does not request: git commit, git tag, git push, PR creation, merge, daemon, polling loop, sleep loop, queue drain, or unbounded retry.",
                        f"- Write `local_codex_exec_plan.sh` with this exact bounded command: `{_LOCAL_CODEX_EXEC_PLAN_COMMAND}`",
                        "- Do not execute `local_codex_exec_plan.sh`.",
                        "- Do not invoke Codex from inside the runner.",
                        "- Do not execute `codex_implementation_prompt.md`.",
                        "- Do not commit, tag, push, open PR, or merge.",
                        "",
                        "## Required Contract Fields",
                        "- `project_browser_autonomous_local_codex_execution_readiness_status`",
                        "- `project_browser_autonomous_local_codex_execution_readiness_next_action`",
                        "- `project_browser_autonomous_local_codex_execution_readiness_prompt_path`",
                        "- `project_browser_autonomous_local_codex_execution_readiness_exec_plan_path`",
                        "- `project_browser_autonomous_local_codex_execution_readiness_blocked_reason`",
                        "- `project_browser_autonomous_local_codex_execution_readiness_runtime_posture`",
                        "",
                        "## Next Action Mapping",
                        "- Readiness artifacts written -> `ready_for_local_codex_exec_command`",
                        "- `next_codex_prompt` missing/invalid -> `manual_review_required`",
                        "- Unsafe/self-referential prompt -> `manual_review_required`",
                        "",
                        "## Validation Commands",
                        "- `python -m py_compile automation/orchestration/planned_execution_runner.py`",
                        "- `python scripts/run_planned_execution.py --artifacts-dir /tmp/codex-local-runner-decision/artifacts --out-dir /tmp/codex-local-runner-decision/out --job-id planned-execution --transport-mode dry-run --json`",
                        "- Run one dry-run verification command only (no repeated retries).",
                        "",
                        "## Out Of Scope",
                        "- Running Codex from inside the runner.",
                        "- Executing local Codex commands inside this Prompt298 run.",
                        "- Executing `local_codex_exec_plan.sh`.",
                        "- Executing the generated implementation prompt.",
                        "- Tests beyond the requested syntax check.",
                        "- Commit/tag/push/PR/merge operations.",
                        "- Deleting existing runtime artifacts.",
                    ]

    request_payload.update(
        {
            "status": status,
            "next_action": next_action,
            "blocked_reason": blocked_reason,
            "source_slice_id": source_slice_id,
            "source_slice_goal": selected_slice_goal,
            "source_slice_scope": selected_slice_scope,
            "execution_status": execution_status,
            "codex_invocation_status": codex_invocation_status,
            "review_status": review_status,
            "commit_tag_status": commit_tag_status,
            "push_status": push_status,
            "do_not_invoke_codex_from_runner": True,
            "do_not_execute_generated_implementation_prompt": True,
            "do_not_commit_tag_push_pr_merge": True,
        }
    )

    summary_lines = [
        "# Next Local Codex Prompt Generation",
        "",
        f"- Status: `{status}`",
        f"- Next action: `{next_action}`",
        f"- Source slice id: `{source_slice_id or 'none'}`",
        f"- Blocked reason: `{blocked_reason}`",
        "- execution_status: `not_started`",
        "- codex_invocation_status: `not_started`",
        "- review_status: `not_started`",
        "- commit_tag_status: `not_started`",
        "- push_status: `not_started`",
        "",
        "## Input Artifacts",
        f"- next_dev_slice.json: `{input_next_dev_slice_json}`",
        f"- next_dev_slice_summary.md: `{input_next_dev_slice_summary}`",
        "",
        "## Output Artifacts",
        f"- codex_implementation_prompt.md: `{output_prompt_path}`",
        f"- codex_implementation_request.json: `{output_request_path}`",
        f"- codex_implementation_summary.md: `{output_summary_path}`",
    ]

    try:
        next_codex_prompt_dir.mkdir(parents=True, exist_ok=True)
        output_prompt_path.write_text("\n".join(prompt_lines).rstrip() + "\n", encoding="utf-8")
        output_request_path.write_text(
            json.dumps(request_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        output_summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    except OSError:
        status = "next_local_codex_prompt_blocked_write_failed"
        next_action = "manual_review_required"
        blocked_reason = "next_local_codex_prompt_artifact_write_failed"

    return {
        "project_browser_autonomous_next_local_codex_prompt_status": status,
        "project_browser_autonomous_next_local_codex_prompt_next_action": next_action,
        "project_browser_autonomous_next_local_codex_prompt_source_slice_id": source_slice_id,
        "project_browser_autonomous_next_local_codex_prompt_path": str(output_prompt_path),
        "project_browser_autonomous_next_local_codex_prompt_request_path": str(output_request_path),
        "project_browser_autonomous_next_local_codex_prompt_summary_path": str(output_summary_path),
        "project_browser_autonomous_next_local_codex_prompt_blocked_reason": blocked_reason,
        "project_browser_autonomous_next_local_codex_prompt_runtime_posture": runtime_posture,
        "project_browser_autonomous_next_local_codex_prompt_execution_status": execution_status,
        "project_browser_autonomous_next_local_codex_prompt_codex_invocation_status": (
            codex_invocation_status
        ),
        "project_browser_autonomous_next_local_codex_prompt_review_status": review_status,
        "project_browser_autonomous_next_local_codex_prompt_commit_tag_status": commit_tag_status,
        "project_browser_autonomous_next_local_codex_prompt_push_status": push_status,
    }

def _build_project_browser_autonomous_local_codex_execution_readiness_state() -> dict[str, Any]:
    next_codex_prompt_dir = Path("/tmp/codex-local-runner-decision/next_codex_prompt")
    readiness_dir = Path("/tmp/codex-local-runner-decision/local_codex_execution_readiness")

    input_prompt_path = next_codex_prompt_dir / "codex_implementation_prompt.md"
    input_request_path = next_codex_prompt_dir / "codex_implementation_request.json"
    input_summary_path = next_codex_prompt_dir / "codex_implementation_summary.md"

    output_json_path = readiness_dir / "local_codex_execution_readiness.json"
    output_summary_path = readiness_dir / "local_codex_execution_summary.md"
    output_exec_plan_path = readiness_dir / "local_codex_exec_plan.sh"

    runtime_posture = [
        "metadata_only_readiness",
        "no_codex_invocation",
        "no_prompt_execution",
        "no_exec_plan_execution",
        "no_commit_tag_push_pr_merge",
        "no_daemon_loop_no_unbounded_retry",
    ]

    status = "local_codex_execution_readiness_blocked_missing_next_codex_prompt"
    next_action = "manual_review_required"
    blocked_reason = "next_codex_prompt_missing"
    prompt_exists = False
    prompt_non_empty = False
    prompt_intended_for_later_exec_only = False
    prompt_safe = False
    prompt_self_referential = False
    banned_requests_detected: list[str] = []

    request_payload: Mapping[str, Any] | None = None
    prompt_text = ""
    summary_text = ""

    input_artifacts = {
        "codex_implementation_prompt_md": str(input_prompt_path),
        "codex_implementation_request_json": str(input_request_path),
        "codex_implementation_summary_md": str(input_summary_path),
    }
    output_artifacts = {
        "local_codex_execution_readiness_json": str(output_json_path),
        "local_codex_execution_summary_md": str(output_summary_path),
        "local_codex_exec_plan_sh": str(output_exec_plan_path),
    }

    if not input_prompt_path.exists():
        blocked_reason = "next_codex_prompt_prompt_missing"
        status = "local_codex_execution_readiness_blocked_missing_next_codex_prompt"
    elif not input_request_path.exists():
        blocked_reason = "next_codex_prompt_request_missing"
        status = "local_codex_execution_readiness_blocked_missing_next_codex_prompt"
    elif not input_summary_path.exists():
        blocked_reason = "next_codex_prompt_summary_missing"
        status = "local_codex_execution_readiness_blocked_missing_next_codex_prompt"
    else:
        try:
            loaded_request_payload = json.loads(input_request_path.read_text(encoding="utf-8"))
            prompt_text = input_prompt_path.read_text(encoding="utf-8")
            summary_text = input_summary_path.read_text(encoding="utf-8")
        except (OSError, json.JSONDecodeError):
            blocked_reason = "next_codex_prompt_invalid"
            status = "local_codex_execution_readiness_blocked_invalid_next_codex_prompt"
        else:
            if not isinstance(loaded_request_payload, Mapping):
                blocked_reason = "next_codex_prompt_request_not_object"
                status = "local_codex_execution_readiness_blocked_invalid_next_codex_prompt"
            else:
                request_payload = loaded_request_payload
                request_status = _normalize_text(request_payload.get("status"), default="")
                request_next_action = _normalize_text(request_payload.get("next_action"), default="")
                request_blocked_reason = _normalize_text(
                    request_payload.get("blocked_reason"),
                    default="",
                )
                summary_readable = bool(summary_text.strip())

                prompt_exists = input_prompt_path.is_file()
                prompt_non_empty = bool(prompt_text.strip())
                prompt_text_lower = prompt_text.lower()
                prompt_intended_for_later_exec_only = (
                    "later local codex exec run only" in prompt_text_lower
                    or (
                        "local codex execution readiness" in prompt_text_lower
                        and "do not execute `local_codex_exec_plan.sh`" in prompt_text_lower
                    )
                )
                prompt_self_referential = (
                    "generate next local codex implementation request from next_dev_slice"
                    in prompt_text_lower
                    or "bounded metadata-only local prompt generation from `next_dev_slice`"
                    in prompt_text_lower
                )
                banned_requests_detected = (
                    _collect_local_codex_execution_readiness_banned_prompt_fragments(
                        prompt_text_lower
                    )
                )
                prompt_safe = not prompt_self_referential and not banned_requests_detected

                if request_status != "next_local_codex_prompt_generated":
                    blocked_reason = "next_codex_prompt_status_not_generated"
                    status = "local_codex_execution_readiness_blocked_invalid_next_codex_prompt"
                elif request_next_action != "ready_for_bounded_local_codex_implementation":
                    blocked_reason = (
                        "next_codex_prompt_next_action_not_ready_for_bounded_local_codex_implementation"
                    )
                    status = "local_codex_execution_readiness_blocked_invalid_next_codex_prompt"
                elif request_blocked_reason != "none":
                    blocked_reason = "next_codex_prompt_blocked_reason_not_none"
                    status = "local_codex_execution_readiness_blocked_invalid_next_codex_prompt"
                elif not summary_readable:
                    blocked_reason = "next_codex_prompt_summary_empty"
                    status = "local_codex_execution_readiness_blocked_invalid_next_codex_prompt"
                elif not prompt_exists:
                    blocked_reason = "next_codex_prompt_prompt_not_file"
                    status = "local_codex_execution_readiness_blocked_invalid_next_codex_prompt"
                elif not prompt_non_empty:
                    blocked_reason = "next_codex_prompt_prompt_empty"
                    status = "local_codex_execution_readiness_blocked_invalid_next_codex_prompt"
                elif not prompt_intended_for_later_exec_only:
                    blocked_reason = "prompt_not_intended_for_later_local_codex_exec_run_only"
                    status = "local_codex_execution_readiness_blocked_prompt_unsafe_or_self_referential"
                elif prompt_self_referential:
                    blocked_reason = "prompt_self_referential"
                    status = "local_codex_execution_readiness_blocked_prompt_unsafe_or_self_referential"
                elif banned_requests_detected:
                    blocked_reason = "prompt_requests_disallowed_operations"
                    status = "local_codex_execution_readiness_blocked_prompt_unsafe_or_self_referential"
                else:
                    blocked_reason = "none"
                    status = "local_codex_execution_readiness_generated"
                    next_action = "ready_for_local_codex_exec_command"

    readiness_payload: dict[str, Any] = {
        "status": status,
        "next_action": next_action,
        "blocked_reason": blocked_reason,
        "prompt_path": str(input_prompt_path),
        "prompt_exists": prompt_exists,
        "prompt_non_empty": prompt_non_empty,
        "prompt_intended_for_later_local_codex_exec_run_only": prompt_intended_for_later_exec_only,
        "prompt_safe": prompt_safe,
        "prompt_self_referential": prompt_self_referential,
        "prompt_banned_requests_detected": banned_requests_detected,
        "exact_bounded_exec_command": _LOCAL_CODEX_EXEC_PLAN_COMMAND,
        "do_not_execute_local_codex_exec_plan": True,
        "do_not_invoke_codex_from_runner": True,
        "do_not_execute_generated_implementation_prompt": True,
        "do_not_commit_tag_push_pr_merge": True,
        "input_artifacts": input_artifacts,
        "output_artifacts": output_artifacts,
        "runtime_posture": runtime_posture,
    }

    summary_lines = [
        "# Local Codex Execution Readiness",
        "",
        f"- Status: `{status}`",
        f"- Next action: `{next_action}`",
        f"- Blocked reason: `{blocked_reason}`",
        f"- Prompt exists: `{str(prompt_exists).lower()}`",
        f"- Prompt non-empty: `{str(prompt_non_empty).lower()}`",
        (
            "- Prompt intended for later local codex exec run only: "
            f"`{str(prompt_intended_for_later_exec_only).lower()}`"
        ),
        f"- Prompt safe: `{str(prompt_safe).lower()}`",
        f"- Prompt self-referential: `{str(prompt_self_referential).lower()}`",
        f"- Banned requests detected: `{', '.join(banned_requests_detected) if banned_requests_detected else 'none'}`",
        "",
        "## Input Artifacts",
        f"- codex_implementation_prompt.md: `{input_prompt_path}`",
        f"- codex_implementation_request.json: `{input_request_path}`",
        f"- codex_implementation_summary.md: `{input_summary_path}`",
        "",
        "## Output Artifacts",
        f"- local_codex_execution_readiness.json: `{output_json_path}`",
        f"- local_codex_execution_summary.md: `{output_summary_path}`",
        f"- local_codex_exec_plan.sh: `{output_exec_plan_path}`",
        "",
        "## Bounded Exec Command",
        f"- `{_LOCAL_CODEX_EXEC_PLAN_COMMAND}`",
    ]

    try:
        readiness_dir.mkdir(parents=True, exist_ok=True)
        output_json_path.write_text(
            json.dumps(readiness_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        output_summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
        output_exec_plan_path.write_text(
            (
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "\n"
                f"{_LOCAL_CODEX_EXEC_PLAN_COMMAND}\n"
            ),
            encoding="utf-8",
        )
        try:
            current_mode = output_exec_plan_path.stat().st_mode
            output_exec_plan_path.chmod(current_mode | 0o111)
        except OSError:
            pass
    except OSError:
        status = "local_codex_execution_readiness_blocked_write_failed"
        next_action = "manual_review_required"
        blocked_reason = "local_codex_execution_readiness_artifact_write_failed"

    return {
        "project_browser_autonomous_local_codex_execution_readiness_status": status,
        "project_browser_autonomous_local_codex_execution_readiness_next_action": next_action,
        "project_browser_autonomous_local_codex_execution_readiness_prompt_path": str(
            input_prompt_path
        ),
        "project_browser_autonomous_local_codex_execution_readiness_json_path": str(
            output_json_path
        ),
        "project_browser_autonomous_local_codex_execution_readiness_summary_path": str(
            output_summary_path
        ),
        "project_browser_autonomous_local_codex_execution_readiness_exec_plan_path": str(
            output_exec_plan_path
        ),
        "project_browser_autonomous_local_codex_execution_readiness_blocked_reason": blocked_reason,
        "project_browser_autonomous_local_codex_execution_readiness_runtime_posture": runtime_posture,
    }

def _build_project_browser_autonomous_codex_execution_state(
    *,
    run_id: str,
    adapter: CodexExecutorAdapter,
    manifest_units: list[Mapping[str, Any]],
    autonomous_result_assimilation_status: str,
    autonomous_result_assimilation_block_reason: str,
    autonomous_result_assimilation_receipt_status: str,
    autonomous_response_usability_status: str,
    autonomous_response_handoff_status: str,
    autonomous_codex_invocation_candidate_status: str,
    autonomous_codex_invocation_candidate_kind: str,
    autonomous_codex_invocation_permission: str,
    autonomous_codex_invocation_prompt_source_status: str,
    autonomous_codex_invocation_scope_status: str,
    autonomous_codex_invocation_no_tests_policy: str,
    autonomous_codex_invocation_token_posture: str,
    autonomous_codex_invocation_candidate_compact: Mapping[str, Any] | None,
    autonomous_browser_execution_status: str,
    autonomous_browser_execution_receipt_status: str,
    autonomous_browser_enqueue_status: str,
    autonomous_execution_adapter_status: str,
    autonomous_executor_readiness_status: str,
    autonomous_dispatch_status: str,
    autonomous_invocation_status: str,
    autonomous_operation_contract_status: str,
    autonomous_cooldown_status: str,
    autonomous_loop_risk_status: str,
    autonomous_multistep_budget_status: str,
    autonomous_multistep_permission: str,
    autonomous_multistep_state: Mapping[str, Any] | None,
    autonomous_safety_switch_status: str,
    autonomous_manual_override_status: str,
    autonomous_safe_stop_status: str,
    autonomous_execution_permission: str,
    autonomous_execution_bridge_status: str,
    autonomous_execution_bridge_permission: str,
    project_pr_queue_handoff_payload: Mapping[str, Any] | None,
    project_pr_queue_selected_slice_id: str,
) -> dict[str, Any]:
    assimilation_status = _normalize_text(
        autonomous_result_assimilation_status,
        default="insufficient_truth",
    )
    assimilation_block_reason = _normalize_text(
        autonomous_result_assimilation_block_reason,
        default="insufficient_truth",
    )
    assimilation_receipt_status = _normalize_text(
        autonomous_result_assimilation_receipt_status,
        default="insufficient_truth",
    )
    response_usability_status = _normalize_text(
        autonomous_response_usability_status,
        default="insufficient_truth",
    )
    response_handoff_status = _normalize_text(
        autonomous_response_handoff_status,
        default="insufficient_truth",
    )
    codex_candidate_status = _normalize_text(
        autonomous_codex_invocation_candidate_status,
        default="insufficient_truth",
    )
    codex_candidate_kind = _normalize_text(
        autonomous_codex_invocation_candidate_kind,
        default="insufficient_truth_candidate",
    )
    codex_permission = _normalize_text(
        autonomous_codex_invocation_permission,
        default="insufficient_truth",
    )
    codex_prompt_source_status = _normalize_text(
        autonomous_codex_invocation_prompt_source_status,
        default="insufficient_truth",
    )
    codex_scope_status = _normalize_text(
        autonomous_codex_invocation_scope_status,
        default="insufficient_truth",
    )
    codex_no_tests_policy = _normalize_text(
        autonomous_codex_invocation_no_tests_policy,
        default="insufficient_truth",
    )
    codex_token_posture = _normalize_text(
        autonomous_codex_invocation_token_posture,
        default="insufficient_truth",
    )
    codex_candidate_compact = (
        dict(autonomous_codex_invocation_candidate_compact)
        if isinstance(autonomous_codex_invocation_candidate_compact, Mapping)
        else {}
    )
    browser_execution_status = _normalize_text(
        autonomous_browser_execution_status,
        default="insufficient_truth",
    )
    browser_execution_receipt_status = _normalize_text(
        autonomous_browser_execution_receipt_status,
        default="insufficient_truth",
    )
    browser_enqueue_status = _normalize_text(
        autonomous_browser_enqueue_status,
        default="insufficient_truth",
    )
    execution_adapter_status = _normalize_text(
        autonomous_execution_adapter_status,
        default="insufficient_truth",
    )
    executor_readiness_status = _normalize_text(
        autonomous_executor_readiness_status,
        default="insufficient_truth",
    )
    dispatch_status = _normalize_text(
        autonomous_dispatch_status,
        default="insufficient_truth",
    )
    invocation_status = _normalize_text(
        autonomous_invocation_status,
        default="insufficient_truth",
    )
    operation_contract_status = _normalize_text(
        autonomous_operation_contract_status,
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
    multistep_budget_status = _normalize_text(
        autonomous_multistep_budget_status,
        default="insufficient_truth",
    )
    multistep_permission = _normalize_text(
        autonomous_multistep_permission,
        default="insufficient_truth",
    )
    multistep_state = dict(autonomous_multistep_state or {})
    safety_switch_status = _normalize_text(
        autonomous_safety_switch_status,
        default="insufficient_truth",
    )
    manual_override_status = _normalize_text(
        autonomous_manual_override_status,
        default="insufficient_truth",
    )
    safe_stop_status = _normalize_text(
        autonomous_safe_stop_status,
        default="insufficient_truth",
    )
    execution_permission = _normalize_text(
        autonomous_execution_permission,
        default="insufficient_truth",
    )
    execution_bridge_status = _normalize_text(
        autonomous_execution_bridge_status,
        default="insufficient_truth",
    )
    execution_bridge_permission = _normalize_text(
        autonomous_execution_bridge_permission,
        default="insufficient_truth",
    )
    queue_handoff_payload = (
        dict(project_pr_queue_handoff_payload)
        if isinstance(project_pr_queue_handoff_payload, Mapping)
        else {}
    )
    queue_selected_slice_id = _normalize_text(project_pr_queue_selected_slice_id, default="")

    runtime_posture = [
        "one_attempt_only",
        "no_repair_loop",
        "no_tests",
        "no_validation_commands",
        "no_sanity_checks",
        "no_second_codex_attempt",
        "no_browser_action",
        "no_prompt_send",
        "no_browser_enqueue",
        "no_md_write",
        "no_arbitrary_shell_execution",
        "no_queue_drain",
        "no_retry_execution",
        "no_repair_execution",
        "no_restart_execution",
        "no_approval_execution",
        "no_continuation_execution",
        "no_counter_mutation",
        "no_git_commit",
        "no_git_push",
        "no_pr_create",
        "no_auto_merge",
        "no_github_mutation",
        "no_loop_execution",
        "no_background_runtime",
    ]

    def _read_required_non_negative_int(value: Any) -> tuple[int, bool]:
        if isinstance(value, bool):
            return 0, True
        if isinstance(value, int):
            return (value if value >= 0 else 0), value < 0
        if isinstance(value, str):
            text = value.strip()
            if text.isdigit():
                return int(text), False
        return 0, True

    def _base_state(
        *,
        status: str,
        kind: str,
        permission: str,
        source_status: str,
        candidate_status: str,
        prompt_status: str,
        scope_status: str,
        token_posture: str,
        no_tests_policy: str,
        attempt_count: int,
        repair_loop_status: str,
        result_status: str,
        files_changed_status: str,
        tests_status: str,
        block_reason: str,
        receipt_status: str,
        receipt_kind: str,
        suggested_validation_targets: list[str],
    ) -> dict[str, Any]:
        return {
            "project_browser_autonomous_codex_execution_status": status,
            "project_browser_autonomous_codex_execution_kind": kind,
            "project_browser_autonomous_codex_execution_permission": permission,
            "project_browser_autonomous_codex_execution_source_status": source_status,
            "project_browser_autonomous_codex_execution_candidate_status": candidate_status,
            "project_browser_autonomous_codex_execution_prompt_status": prompt_status,
            "project_browser_autonomous_codex_execution_scope_status": scope_status,
            "project_browser_autonomous_codex_execution_token_posture": token_posture,
            "project_browser_autonomous_codex_execution_no_tests_policy": no_tests_policy,
            "project_browser_autonomous_codex_execution_attempt_count": attempt_count,
            "project_browser_autonomous_codex_execution_max_attempts": 1,
            "project_browser_autonomous_codex_execution_repair_loop_status": (
                repair_loop_status
            ),
            "project_browser_autonomous_codex_execution_result_status": result_status,
            "project_browser_autonomous_codex_execution_files_changed_status": (
                files_changed_status
            ),
            "project_browser_autonomous_codex_execution_tests_status": tests_status,
            "project_browser_autonomous_codex_execution_block_reason": block_reason,
            "project_browser_autonomous_codex_execution_receipt_status": receipt_status,
            "project_browser_autonomous_codex_execution_receipt_kind": receipt_kind,
            "project_browser_autonomous_codex_execution_runtime_posture": runtime_posture,
            "project_browser_autonomous_codex_execution_suggested_validation_targets": (
                suggested_validation_targets
            ),
        }

    def _insufficient_truth_state(*, block_reason: str) -> dict[str, Any]:
        normalized_block_reason = (
            block_reason
            if block_reason in {"source_inconsistent", "insufficient_truth"}
            else "insufficient_truth"
        )
        return _base_state(
            status="insufficient_truth",
            kind="insufficient_truth_codex_execution",
            permission="insufficient_truth",
            source_status="insufficient_truth",
            candidate_status="insufficient_truth",
            prompt_status="insufficient_truth",
            scope_status="insufficient_truth",
            token_posture="insufficient_truth",
            no_tests_policy="insufficient_truth",
            attempt_count=0,
            repair_loop_status="insufficient_truth",
            result_status="insufficient_truth",
            files_changed_status="insufficient_truth",
            tests_status="insufficient_truth",
            block_reason=normalized_block_reason,
            receipt_status="insufficient_truth",
            receipt_kind="insufficient_truth_codex_execution_receipt",
            suggested_validation_targets=[],
        )

    def _map_assimilation_block_reason(value: str) -> str:
        mapping = {
            "none": "candidate_not_ready",
            "browser_receipt_not_ready": "candidate_not_ready",
            "browser_execution_blocked": "candidate_not_ready",
            "browser_execution_failed": "codex_failed",
            "browser_timeout": "timeout",
            "response_empty": "prompt_empty",
            "response_too_large": "prompt_too_large",
            "response_unusable": "candidate_not_ready",
            "codex_scope_too_broad": "scope_too_broad",
            "codex_prompt_missing": "prompt_missing",
            "codex_prompt_empty": "prompt_empty",
            "codex_prompt_too_large": "prompt_too_large",
            "high_risk_action": "high_risk_action",
            "source_inconsistent": "source_inconsistent",
            "cooldown_required": "cooldown_required",
            "loop_suspected": "loop_suspected",
            "pause_required": "pause_required",
            "human_review_required": "human_review_required",
            "insufficient_truth": "insufficient_truth",
        }
        return mapping.get(value, "insufficient_truth")

    def _normalize_candidate_status(value: str) -> str:
        if value in {"ready", "blocked", "failed", "timeout", "pause_required", "human_review_required", "insufficient_truth"}:
            return value
        if value in {"none", "not_created"}:
            return "unavailable"
        return "unavailable"

    def _normalize_prompt_status(value: str) -> str:
        if value in {"available", "empty", "too_large", "invalid_response", "insufficient_truth"}:
            return value
        if value in {"none", "not_created", "unavailable"}:
            return "unavailable"
        return "unavailable"

    def _extract_structured_prompt_text() -> tuple[str, str]:
        implementation_payload = (
            dict(queue_handoff_payload.get("implementation_prompt_payload"))
            if isinstance(queue_handoff_payload.get("implementation_prompt_payload"), Mapping)
            else {}
        )
        prompt_candidates: list[Any] = [
            implementation_payload.get("project_browser_prepared_prompt_text"),
            implementation_payload.get("project_browser_prompt_text"),
            implementation_payload.get("prompt_text"),
            implementation_payload.get("prepared_prompt_text"),
            queue_handoff_payload.get("project_browser_prepared_prompt_text"),
            queue_handoff_payload.get("project_browser_prompt_text"),
            queue_handoff_payload.get("prompt_text"),
        ]
        saw_present = False
        saw_empty = False
        for entry in prompt_candidates:
            if entry is None:
                continue
            saw_present = True
            if not isinstance(entry, str):
                continue
            normalized = _normalize_text(entry, default="")
            if normalized:
                return normalized, "available"
            saw_empty = True
        if saw_empty:
            return "", "empty"
        if saw_present:
            return "", "insufficient_truth"
        return "", "unavailable"

    def _extract_suggested_validation_targets(
        status_payload: Mapping[str, Any],
        artifact_payload: Mapping[str, Any],
    ) -> list[str]:
        for source in (status_payload, artifact_payload):
            raw = source.get("suggested_validation_targets")
            if isinstance(raw, list):
                out: list[str] = []
                for entry in raw:
                    text = _normalize_text(entry, default="")
                    if text and text not in out:
                        out.append(text[:240])
                    if len(out) >= 12:
                        break
                if out:
                    return out
        return []

    def _select_candidate_unit(
        units: list[Mapping[str, Any]],
        *,
        compact: Mapping[str, Any],
        selected_slice_id: str,
    ) -> tuple[Mapping[str, Any] | None, str]:
        if not units:
            return None, "candidate_not_ready"
        slice_id = _normalize_text(compact.get("slice_id"), default=selected_slice_id)
        source_step_id = _normalize_text(compact.get("source_step_id"), default="")
        planned_step_id = _normalize_text(compact.get("planned_step_id"), default="")
        candidate_ids = _normalize_string_list(compact.get("candidate_ids"))
        if len(candidate_ids) > 1:
            return None, "candidate_not_ready"
        if len(candidate_ids) == 1 and not slice_id:
            slice_id = candidate_ids[0]

        matches: list[Mapping[str, Any]] = []
        if slice_id:
            for unit in units:
                unit_pr_id = _normalize_text(unit.get("pr_id"), default="")
                contract_summary = (
                    dict(unit.get("contract_handoff_summary"))
                    if isinstance(unit.get("contract_handoff_summary"), Mapping)
                    else {}
                )
                if slice_id in {
                    unit_pr_id,
                    _normalize_text(contract_summary.get("planned_step_id"), default=""),
                    _normalize_text(contract_summary.get("source_step_id"), default=""),
                }:
                    matches.append(unit)
        if not matches and source_step_id:
            for unit in units:
                contract_summary = (
                    dict(unit.get("contract_handoff_summary"))
                    if isinstance(unit.get("contract_handoff_summary"), Mapping)
                    else {}
                )
                if source_step_id == _normalize_text(
                    contract_summary.get("source_step_id"),
                    default="",
                ):
                    matches.append(unit)
        if not matches and planned_step_id:
            for unit in units:
                contract_summary = (
                    dict(unit.get("contract_handoff_summary"))
                    if isinstance(unit.get("contract_handoff_summary"), Mapping)
                    else {}
                )
                if planned_step_id == _normalize_text(
                    contract_summary.get("planned_step_id"),
                    default="",
                ):
                    matches.append(unit)
        if not matches and len(units) == 1:
            return units[0], "none"
        deduped_matches: list[Mapping[str, Any]] = []
        seen_pr_ids: set[str] = set()
        for unit in matches:
            pr_id = _normalize_text(unit.get("pr_id"), default="")
            if pr_id and pr_id not in seen_pr_ids:
                seen_pr_ids.add(pr_id)
                deduped_matches.append(unit)
        if len(deduped_matches) != 1:
            return None, "candidate_not_ready"
        return deduped_matches[0], "none"

    if assimilation_status not in {
        "inactive",
        "assimilated",
        "blocked",
        "failed",
        "timeout",
        "cooldown_required",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if assimilation_block_reason not in {
        "none",
        "browser_receipt_not_ready",
        "browser_execution_blocked",
        "browser_execution_failed",
        "browser_timeout",
        "response_empty",
        "response_too_large",
        "response_unusable",
        "codex_scope_too_broad",
        "codex_prompt_missing",
        "codex_prompt_empty",
        "codex_prompt_too_large",
        "high_risk_action",
        "source_inconsistent",
        "cooldown_required",
        "loop_suspected",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if assimilation_receipt_status not in {
        "not_created",
        "ready",
        "blocked",
        "failed",
        "timeout",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if response_usability_status not in {
        "unavailable",
        "usable",
        "empty",
        "too_large",
        "invalid_response",
        "blocked",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if response_handoff_status not in {
        "not_created",
        "ready",
        "blocked",
        "failed",
        "timeout",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if codex_candidate_status not in {
        "not_created",
        "ready",
        "blocked",
        "failed",
        "timeout",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if codex_candidate_kind not in {
        "none",
        "one_codex_invocation_candidate",
        "retry_browser_prompt_candidate",
        "blocked_candidate",
        "timeout_candidate",
        "pause_candidate",
        "human_review_candidate",
        "insufficient_truth_candidate",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if codex_permission not in {
        "allowed_candidate",
        "blocked",
        "timeout",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if codex_prompt_source_status not in {
        "unavailable",
        "available",
        "empty",
        "too_large",
        "invalid_response",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if codex_scope_status not in {
        "unavailable",
        "bounded",
        "too_broad",
        "high_risk",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if codex_no_tests_policy not in {"enforced", "unavailable", "insufficient_truth"}:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if codex_token_posture not in {"compact", "too_large", "insufficient_truth"}:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if browser_execution_status not in {
        "inactive",
        "executed",
        "blocked",
        "failed",
        "timeout",
        "cooldown_required",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if browser_execution_receipt_status not in {
        "not_created",
        "ready",
        "blocked",
        "failed",
        "timeout",
        "cooldown_required",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if browser_enqueue_status not in {
        "inactive",
        "prepared",
        "skipped",
        "blocked",
        "cooldown_required",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if execution_adapter_status not in {
        "inactive",
        "executable_candidate",
        "execution_ready_candidate",
        "blocked",
        "cooldown_required",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if executor_readiness_status not in {
        "inactive",
        "ready",
        "blocked",
        "cooldown_required",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if dispatch_status not in {
        "inactive",
        "prepared",
        "blocked",
        "cooldown_required",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if invocation_status not in {
        "inactive",
        "prepared",
        "blocked",
        "cooldown_required",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if operation_contract_status not in {
        "inactive",
        "ready",
        "blocked",
        "cooldown_required",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if cooldown_status not in {"not_required", "required", "blocked", "insufficient_truth"}:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if loop_risk_status not in {"clear", "suspected", "blocked", "insufficient_truth"}:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if multistep_budget_status not in {
        "inactive",
        "ready",
        "blocked",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if multistep_permission not in _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if safety_switch_status not in _PROJECT_BROWSER_AUTONOMOUS_SAFETY_SWITCH_STATUSES:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if manual_override_status not in _PROJECT_BROWSER_AUTONOMOUS_MANUAL_OVERRIDE_STATUSES:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if safe_stop_status not in _PROJECT_BROWSER_AUTONOMOUS_SAFE_STOP_STATUSES:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if execution_permission not in _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if execution_bridge_status not in _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_BRIDGE_STATUSES:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if execution_bridge_permission not in _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS:
        return _insufficient_truth_state(block_reason="insufficient_truth")

    remaining_steps, remaining_steps_invalid = _read_required_non_negative_int(
        multistep_state.get("project_browser_autonomous_multistep_remaining_steps")
    )
    remaining_failures, remaining_failures_invalid = _read_required_non_negative_int(
        multistep_state.get("project_browser_autonomous_multistep_remaining_failures")
    )
    if remaining_steps_invalid or remaining_failures_invalid:
        return _insufficient_truth_state(block_reason="insufficient_truth")

    candidate_status_out = _normalize_candidate_status(codex_candidate_status)
    prompt_status_out = _normalize_prompt_status(codex_prompt_source_status)
    scope_status_out = codex_scope_status
    token_posture_out = codex_token_posture
    no_tests_policy_out = codex_no_tests_policy

    if assimilation_status == "inactive":
        return _base_state(
            status="inactive",
            kind="none",
            permission="blocked",
            source_status="valid",
            candidate_status=candidate_status_out,
            prompt_status=prompt_status_out,
            scope_status=scope_status_out,
            token_posture=token_posture_out,
            no_tests_policy=no_tests_policy_out,
            attempt_count=0,
            repair_loop_status="not_started",
            result_status="not_executed",
            files_changed_status="unavailable",
            tests_status="not_run_by_instruction",
            block_reason="none",
            receipt_status="not_created",
            receipt_kind="none",
            suggested_validation_targets=[],
        )
    if assimilation_status == "blocked":
        return _base_state(
            status="blocked",
            kind="blocked_codex_execution",
            permission="blocked",
            source_status="valid",
            candidate_status=candidate_status_out,
            prompt_status=prompt_status_out,
            scope_status=scope_status_out,
            token_posture=token_posture_out,
            no_tests_policy=no_tests_policy_out,
            attempt_count=0,
            repair_loop_status="blocked",
            result_status="blocked",
            files_changed_status="unavailable",
            tests_status="not_run_by_instruction",
            block_reason=_map_assimilation_block_reason(assimilation_block_reason),
            receipt_status="blocked",
            receipt_kind="blocked_codex_execution_receipt",
            suggested_validation_targets=[],
        )
    if assimilation_status == "failed":
        return _base_state(
            status="failed",
            kind="failed_codex_execution",
            permission="blocked",
            source_status="valid",
            candidate_status=candidate_status_out,
            prompt_status=prompt_status_out,
            scope_status=scope_status_out,
            token_posture=token_posture_out,
            no_tests_policy=no_tests_policy_out,
            attempt_count=0,
            repair_loop_status="not_started",
            result_status="failed",
            files_changed_status="unavailable",
            tests_status="not_run_by_instruction",
            block_reason=_map_assimilation_block_reason(assimilation_block_reason),
            receipt_status="failed",
            receipt_kind="failed_codex_execution_receipt",
            suggested_validation_targets=[],
        )
    if assimilation_status == "timeout":
        return _base_state(
            status="timeout",
            kind="timeout_codex_execution",
            permission="blocked",
            source_status="valid",
            candidate_status=candidate_status_out,
            prompt_status=prompt_status_out,
            scope_status=scope_status_out,
            token_posture=token_posture_out,
            no_tests_policy=no_tests_policy_out,
            attempt_count=0,
            repair_loop_status="not_started",
            result_status="timeout",
            files_changed_status="unavailable",
            tests_status="not_run_by_instruction",
            block_reason="timeout",
            receipt_status="timeout",
            receipt_kind="timeout_codex_execution_receipt",
            suggested_validation_targets=[],
        )
    if assimilation_status == "cooldown_required":
        return _base_state(
            status="cooldown_required",
            kind="cooldown_codex_execution",
            permission="cooldown_required",
            source_status="valid",
            candidate_status=candidate_status_out,
            prompt_status=prompt_status_out,
            scope_status=scope_status_out,
            token_posture=token_posture_out,
            no_tests_policy=no_tests_policy_out,
            attempt_count=0,
            repair_loop_status="blocked",
            result_status="blocked",
            files_changed_status="unavailable",
            tests_status="not_run_by_instruction",
            block_reason="cooldown_required",
            receipt_status="cooldown_required",
            receipt_kind="cooldown_codex_execution_receipt",
            suggested_validation_targets=[],
        )
    if assimilation_status == "pause_required":
        return _base_state(
            status="pause_required",
            kind="pause_codex_execution",
            permission="pause_required",
            source_status="valid",
            candidate_status=candidate_status_out,
            prompt_status=prompt_status_out,
            scope_status=scope_status_out,
            token_posture=token_posture_out,
            no_tests_policy=no_tests_policy_out,
            attempt_count=0,
            repair_loop_status="blocked",
            result_status="blocked",
            files_changed_status="unavailable",
            tests_status="not_run_by_instruction",
            block_reason="pause_required",
            receipt_status="pause_required",
            receipt_kind="pause_codex_execution_receipt",
            suggested_validation_targets=[],
        )
    if assimilation_status == "human_review_required":
        return _base_state(
            status="human_review_required",
            kind="human_review_codex_execution",
            permission="human_review_required",
            source_status="valid",
            candidate_status=candidate_status_out,
            prompt_status=prompt_status_out,
            scope_status=scope_status_out,
            token_posture=token_posture_out,
            no_tests_policy=no_tests_policy_out,
            attempt_count=0,
            repair_loop_status="blocked",
            result_status="blocked",
            files_changed_status="unavailable",
            tests_status="not_run_by_instruction",
            block_reason="human_review_required",
            receipt_status="human_review_required",
            receipt_kind="human_review_codex_execution_receipt",
            suggested_validation_targets=[],
        )
    if assimilation_status == "insufficient_truth":
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if assimilation_status != "assimilated":
        return _insufficient_truth_state(block_reason="source_inconsistent")

    source_conflict = False
    if assimilation_receipt_status != "ready":
        source_conflict = True
    if response_usability_status != "usable":
        source_conflict = True
    if response_handoff_status != "ready":
        source_conflict = True
    if browser_execution_status != "executed":
        source_conflict = True
    if browser_execution_receipt_status != "ready":
        source_conflict = True
    if browser_enqueue_status != "prepared":
        source_conflict = True
    if execution_adapter_status != "execution_ready_candidate":
        source_conflict = True
    if executor_readiness_status != "ready":
        source_conflict = True
    if dispatch_status != "prepared":
        source_conflict = True
    if invocation_status != "prepared":
        source_conflict = True
    if operation_contract_status != "ready":
        source_conflict = True
    if cooldown_status != "not_required":
        source_conflict = True
    if loop_risk_status != "clear":
        source_conflict = True
    if multistep_budget_status != "ready":
        source_conflict = True
    if multistep_permission != "allowed_candidate":
        source_conflict = True
    if remaining_steps <= 0 or remaining_failures <= 0:
        source_conflict = True
    if safety_switch_status in {
        "disabled",
        "stop_all",
        "pause_after_current_step",
        "manual_review_required",
        "pause_required",
        "insufficient_truth",
    }:
        source_conflict = True
    if manual_override_status in {"requested", "required", "blocked", "insufficient_truth"}:
        source_conflict = True
    if safe_stop_status != "not_required":
        source_conflict = True
    if execution_permission != "allowed_candidate":
        source_conflict = True
    if execution_bridge_status != "ready":
        source_conflict = True
    if execution_bridge_permission != "allowed_candidate":
        source_conflict = True
    if source_conflict:
        return _base_state(
            status="insufficient_truth",
            kind="insufficient_truth_codex_execution",
            permission="insufficient_truth",
            source_status="inconsistent",
            candidate_status="insufficient_truth",
            prompt_status="insufficient_truth",
            scope_status="insufficient_truth",
            token_posture="insufficient_truth",
            no_tests_policy="insufficient_truth",
            attempt_count=0,
            repair_loop_status="insufficient_truth",
            result_status="insufficient_truth",
            files_changed_status="insufficient_truth",
            tests_status="insufficient_truth",
            block_reason="source_inconsistent",
            receipt_status="insufficient_truth",
            receipt_kind="insufficient_truth_codex_execution_receipt",
            suggested_validation_targets=[],
        )

    if codex_candidate_status != "ready" or codex_permission != "allowed_candidate":
        return _base_state(
            status="blocked",
            kind="blocked_codex_execution",
            permission="blocked",
            source_status="valid",
            candidate_status=candidate_status_out,
            prompt_status=prompt_status_out,
            scope_status=scope_status_out,
            token_posture=token_posture_out,
            no_tests_policy=no_tests_policy_out,
            attempt_count=0,
            repair_loop_status="blocked",
            result_status="blocked",
            files_changed_status="unavailable",
            tests_status="not_run_by_instruction",
            block_reason="candidate_not_ready",
            receipt_status="blocked",
            receipt_kind="blocked_codex_execution_receipt",
            suggested_validation_targets=[],
        )
    if codex_candidate_kind != "one_codex_invocation_candidate":
        return _base_state(
            status="blocked",
            kind="blocked_codex_execution",
            permission="blocked",
            source_status="valid",
            candidate_status=candidate_status_out,
            prompt_status=prompt_status_out,
            scope_status=scope_status_out,
            token_posture=token_posture_out,
            no_tests_policy=no_tests_policy_out,
            attempt_count=0,
            repair_loop_status="blocked",
            result_status="blocked",
            files_changed_status="unavailable",
            tests_status="not_run_by_instruction",
            block_reason="candidate_not_ready",
            receipt_status="blocked",
            receipt_kind="blocked_codex_execution_receipt",
            suggested_validation_targets=[],
        )

    candidate_ids = _normalize_string_list(codex_candidate_compact.get("candidate_ids"))
    codex_candidates = codex_candidate_compact.get("codex_candidates")
    if (candidate_ids and len(candidate_ids) != 1) or (
        isinstance(codex_candidates, list) and len(codex_candidates) != 1
    ):
        return _base_state(
            status="blocked",
            kind="blocked_codex_execution",
            permission="blocked",
            source_status="inconsistent",
            candidate_status="blocked",
            prompt_status=prompt_status_out,
            scope_status=scope_status_out,
            token_posture=token_posture_out,
            no_tests_policy=no_tests_policy_out,
            attempt_count=0,
            repair_loop_status="blocked",
            result_status="blocked",
            files_changed_status="unavailable",
            tests_status="not_run_by_instruction",
            block_reason="candidate_not_ready",
            receipt_status="blocked",
            receipt_kind="blocked_codex_execution_receipt",
            suggested_validation_targets=[],
        )

    prompt_text, structured_prompt_status = _extract_structured_prompt_text()
    prompt_status_out = _normalize_prompt_status(codex_prompt_source_status)
    if prompt_status_out == "available" and structured_prompt_status != "available":
        prompt_status_out = structured_prompt_status

    prompt_max_chars = 12000
    if prompt_status_out == "unavailable":
        return _base_state(
            status="blocked",
            kind="blocked_codex_execution",
            permission="blocked",
            source_status="valid",
            candidate_status="ready",
            prompt_status="unavailable",
            scope_status=scope_status_out,
            token_posture=token_posture_out,
            no_tests_policy=no_tests_policy_out,
            attempt_count=0,
            repair_loop_status="blocked",
            result_status="blocked",
            files_changed_status="unavailable",
            tests_status="not_run_by_instruction",
            block_reason="prompt_missing",
            receipt_status="blocked",
            receipt_kind="blocked_codex_execution_receipt",
            suggested_validation_targets=[],
        )
    if prompt_status_out == "empty" or not prompt_text:
        return _base_state(
            status="blocked",
            kind="blocked_codex_execution",
            permission="blocked",
            source_status="valid",
            candidate_status="ready",
            prompt_status="empty",
            scope_status=scope_status_out,
            token_posture=token_posture_out,
            no_tests_policy=no_tests_policy_out,
            attempt_count=0,
            repair_loop_status="blocked",
            result_status="blocked",
            files_changed_status="unavailable",
            tests_status="not_run_by_instruction",
            block_reason="prompt_empty",
            receipt_status="blocked",
            receipt_kind="blocked_codex_execution_receipt",
            suggested_validation_targets=[],
        )
    if len(prompt_text) > prompt_max_chars or prompt_status_out == "too_large":
        return _base_state(
            status="blocked",
            kind="blocked_codex_execution",
            permission="blocked",
            source_status="valid",
            candidate_status="ready",
            prompt_status="too_large",
            scope_status=scope_status_out,
            token_posture="too_large",
            no_tests_policy=no_tests_policy_out,
            attempt_count=0,
            repair_loop_status="blocked",
            result_status="blocked",
            files_changed_status="unavailable",
            tests_status="not_run_by_instruction",
            block_reason="prompt_too_large",
            receipt_status="blocked",
            receipt_kind="blocked_codex_execution_receipt",
            suggested_validation_targets=[],
        )
    if scope_status_out == "high_risk":
        return _base_state(
            status="human_review_required",
            kind="human_review_codex_execution",
            permission="human_review_required",
            source_status="valid",
            candidate_status="ready",
            prompt_status=prompt_status_out,
            scope_status="high_risk",
            token_posture=token_posture_out,
            no_tests_policy=no_tests_policy_out,
            attempt_count=0,
            repair_loop_status="blocked",
            result_status="blocked",
            files_changed_status="unavailable",
            tests_status="not_run_by_instruction",
            block_reason="high_risk_action",
            receipt_status="human_review_required",
            receipt_kind="human_review_codex_execution_receipt",
            suggested_validation_targets=[],
        )
    if scope_status_out != "bounded":
        return _base_state(
            status="blocked",
            kind="blocked_codex_execution",
            permission="blocked",
            source_status="valid",
            candidate_status="ready",
            prompt_status=prompt_status_out,
            scope_status=scope_status_out,
            token_posture=token_posture_out,
            no_tests_policy=no_tests_policy_out,
            attempt_count=0,
            repair_loop_status="blocked",
            result_status="blocked",
            files_changed_status="unavailable",
            tests_status="not_run_by_instruction",
            block_reason="scope_too_broad",
            receipt_status="blocked",
            receipt_kind="blocked_codex_execution_receipt",
            suggested_validation_targets=[],
        )
    if token_posture_out != "compact":
        return _base_state(
            status="blocked",
            kind="blocked_codex_execution",
            permission="blocked",
            source_status="valid",
            candidate_status="ready",
            prompt_status=prompt_status_out,
            scope_status=scope_status_out,
            token_posture="too_large",
            no_tests_policy=no_tests_policy_out,
            attempt_count=0,
            repair_loop_status="blocked",
            result_status="blocked",
            files_changed_status="unavailable",
            tests_status="not_run_by_instruction",
            block_reason="token_too_large",
            receipt_status="blocked",
            receipt_kind="blocked_codex_execution_receipt",
            suggested_validation_targets=[],
        )
    if no_tests_policy_out != "enforced":
        return _base_state(
            status="blocked",
            kind="blocked_codex_execution",
            permission="blocked",
            source_status="valid",
            candidate_status="ready",
            prompt_status=prompt_status_out,
            scope_status=scope_status_out,
            token_posture=token_posture_out,
            no_tests_policy=no_tests_policy_out,
            attempt_count=0,
            repair_loop_status="blocked",
            result_status="blocked",
            files_changed_status="unavailable",
            tests_status="not_run_by_instruction",
            block_reason="no_tests_policy_violation",
            receipt_status="blocked",
            receipt_kind="blocked_codex_execution_receipt",
            suggested_validation_targets=[],
        )

    preferred_files = [
        _normalize_text(path, default="")
        for path in codex_candidate_compact.get("preferred_files", [])
        if isinstance(path, str)
    ]
    if any(path.endswith(".md") for path in preferred_files):
        return _base_state(
            status="blocked",
            kind="blocked_codex_execution",
            permission="blocked",
            source_status="valid",
            candidate_status="ready",
            prompt_status=prompt_status_out,
            scope_status="too_broad",
            token_posture=token_posture_out,
            no_tests_policy=no_tests_policy_out,
            attempt_count=0,
            repair_loop_status="blocked",
            result_status="blocked",
            files_changed_status="unavailable",
            tests_status="not_run_by_instruction",
            block_reason="scope_too_broad",
            receipt_status="blocked",
            receipt_kind="blocked_codex_execution_receipt",
            suggested_validation_targets=[],
        )

    selected_unit, unit_select_error = _select_candidate_unit(
        manifest_units,
        compact=codex_candidate_compact,
        selected_slice_id=queue_selected_slice_id,
    )
    if selected_unit is None:
        return _base_state(
            status="blocked",
            kind="blocked_codex_execution",
            permission="blocked",
            source_status="inconsistent",
            candidate_status="blocked",
            prompt_status=prompt_status_out,
            scope_status=scope_status_out,
            token_posture=token_posture_out,
            no_tests_policy=no_tests_policy_out,
            attempt_count=0,
            repair_loop_status="blocked",
            result_status="blocked",
            files_changed_status="unavailable",
            tests_status="not_run_by_instruction",
            block_reason=(
                "candidate_not_ready"
                if unit_select_error == "candidate_not_ready"
                else "insufficient_truth"
            ),
            receipt_status="blocked",
            receipt_kind="blocked_codex_execution_receipt",
            suggested_validation_targets=[],
        )

    selected_pr_id = _normalize_text(selected_unit.get("pr_id"), default="")
    prompt_path_text = _normalize_text(selected_unit.get("compiled_prompt_path"), default="")
    prompt_path = Path(prompt_path_text) if prompt_path_text else None
    work_dir = prompt_path.parent if prompt_path is not None else Path("")
    if (
        not selected_pr_id
        or prompt_path is None
        or not prompt_path.exists()
        or not work_dir.exists()
    ):
        return _base_state(
            status="blocked",
            kind="blocked_codex_execution",
            permission="blocked",
            source_status="inconsistent",
            candidate_status="blocked",
            prompt_status="unavailable",
            scope_status=scope_status_out,
            token_posture=token_posture_out,
            no_tests_policy=no_tests_policy_out,
            attempt_count=0,
            repair_loop_status="blocked",
            result_status="blocked",
            files_changed_status="unavailable",
            tests_status="not_run_by_instruction",
            block_reason="prompt_missing",
            receipt_status="blocked",
            receipt_kind="blocked_codex_execution_receipt",
            suggested_validation_targets=[],
        )

    codex_run_id = ""
    status_response: dict[str, Any] = {}
    artifact_response: dict[str, Any] = {}
    attempt_count = 0
    try:
        attempt_count = 1
        launch_response = dict(
            adapter.launch_job(
                job_id=_normalize_text(run_id, default=""),
                pr_id=f"{selected_pr_id}__autonomous_codex_once",
                prompt_path=str(prompt_path),
                work_dir=str(work_dir),
                metadata={
                    "autonomous_codex_execution": True,
                    "autonomous_codex_execution_max_attempts": 1,
                    "autonomous_codex_candidate_only": True,
                    "autonomous_codex_no_tests": True,
                    "autonomous_codex_no_validation_commands": True,
                    "autonomous_codex_no_sanity_checks": True,
                    "autonomous_codex_no_repair_loop": True,
                    "autonomous_codex_no_git_mutation": True,
                    "validation_commands": [],
                    "requires_explicit_validation": False,
                    "slice_id": _normalize_text(
                        codex_candidate_compact.get("slice_id"),
                        default=queue_selected_slice_id,
                    ),
                    "source_step_id": _normalize_text(
                        codex_candidate_compact.get("source_step_id"),
                        default="",
                    ),
                    "planned_step_id": _normalize_text(
                        codex_candidate_compact.get("planned_step_id"),
                        default="",
                    ),
                    "strict_scope_files": preferred_files,
                },
            )
        )
        codex_run_id = _normalize_text(launch_response.get("run_id"), default="")
        if not codex_run_id:
            return _base_state(
                status="failed",
                kind="failed_codex_execution",
                permission="allowed",
                source_status="valid",
                candidate_status="ready",
                prompt_status=prompt_status_out,
                scope_status=scope_status_out,
                token_posture=token_posture_out,
                no_tests_policy=no_tests_policy_out,
                attempt_count=attempt_count,
                repair_loop_status="not_started",
                result_status="failed",
                files_changed_status="unavailable",
                tests_status="not_run_by_instruction",
                block_reason="codex_failed",
                receipt_status="failed",
                receipt_kind="failed_codex_execution_receipt",
                suggested_validation_targets=[],
            )
        status_response = dict(adapter.poll_status(run_id=codex_run_id))
        artifact_response = dict(adapter.collect_artifacts(run_id=codex_run_id))
    except Exception:
        return _base_state(
            status="failed",
            kind="failed_codex_execution",
            permission="allowed",
            source_status="valid",
            candidate_status="ready",
            prompt_status=prompt_status_out,
            scope_status=scope_status_out,
            token_posture=token_posture_out,
            no_tests_policy=no_tests_policy_out,
            attempt_count=attempt_count,
            repair_loop_status="not_started",
            result_status="failed",
            files_changed_status="unavailable",
            tests_status="not_run_by_instruction",
            block_reason="codex_failed",
            receipt_status="failed",
            receipt_kind="failed_codex_execution_receipt",
            suggested_validation_targets=[],
        )

    execution_status = _normalize_text(
        status_response.get("status"),
        default="failed",
    ).lower()
    if execution_status not in {"completed", "failed", "timed_out", "not_started", "running"}:
        execution_status = "failed"

    changed_files = _normalize_string_list(
        status_response.get("changed_files")
        if isinstance(status_response.get("changed_files"), list)
        else artifact_response.get("changed_files"),
        sort_items=True,
    )
    if not changed_files:
        files_changed_status = "none"
    elif len(changed_files) > 25:
        files_changed_status = "too_many"
    else:
        files_changed_status = "changed"

    verify_payload = (
        dict(status_response.get("verify"))
        if isinstance(status_response.get("verify"), Mapping)
        else (
            dict(artifact_response.get("verify"))
            if isinstance(artifact_response.get("verify"), Mapping)
            else {}
        )
    )
    verify_status = _normalize_text(verify_payload.get("status"), default="not_run").lower()
    verify_commands = _normalize_string_list(verify_payload.get("commands"))
    tests_status = (
        "attempted_violation"
        if verify_status in {"passed", "failed"} or bool(verify_commands)
        else "not_run_by_instruction"
    )
    suggested_validation_targets = _extract_suggested_validation_targets(
        status_payload=status_response,
        artifact_payload=artifact_response,
    )

    if execution_status == "timed_out":
        return _base_state(
            status="timeout",
            kind="timeout_codex_execution",
            permission="allowed",
            source_status="valid",
            candidate_status="ready",
            prompt_status=prompt_status_out,
            scope_status=scope_status_out,
            token_posture=token_posture_out,
            no_tests_policy=no_tests_policy_out,
            attempt_count=attempt_count,
            repair_loop_status="not_started",
            result_status="timeout",
            files_changed_status=files_changed_status,
            tests_status=tests_status,
            block_reason="timeout",
            receipt_status="timeout",
            receipt_kind="timeout_codex_execution_receipt",
            suggested_validation_targets=suggested_validation_targets,
        )
    if tests_status == "attempted_violation":
        return _base_state(
            status="blocked",
            kind="blocked_codex_execution",
            permission="blocked",
            source_status="valid",
            candidate_status="ready",
            prompt_status=prompt_status_out,
            scope_status=scope_status_out,
            token_posture=token_posture_out,
            no_tests_policy="violated",
            attempt_count=attempt_count,
            repair_loop_status="blocked",
            result_status="blocked",
            files_changed_status=files_changed_status,
            tests_status="attempted_violation",
            block_reason="no_tests_policy_violation",
            receipt_status="blocked",
            receipt_kind="blocked_codex_execution_receipt",
            suggested_validation_targets=suggested_validation_targets,
        )
    if execution_status != "completed":
        return _base_state(
            status="failed",
            kind="failed_codex_execution",
            permission="allowed",
            source_status="valid",
            candidate_status="ready",
            prompt_status=prompt_status_out,
            scope_status=scope_status_out,
            token_posture=token_posture_out,
            no_tests_policy=no_tests_policy_out,
            attempt_count=attempt_count,
            repair_loop_status="not_started",
            result_status="failed",
            files_changed_status=files_changed_status,
            tests_status=tests_status,
            block_reason="codex_failed",
            receipt_status="failed",
            receipt_kind="failed_codex_execution_receipt",
            suggested_validation_targets=suggested_validation_targets,
        )

    return _base_state(
        status="executed",
        kind="one_codex_execution",
        permission="allowed",
        source_status="valid",
        candidate_status="ready",
        prompt_status=prompt_status_out,
        scope_status=scope_status_out,
        token_posture=token_posture_out,
        no_tests_policy=no_tests_policy_out,
        attempt_count=attempt_count,
        repair_loop_status="not_started",
        result_status="succeeded",
        files_changed_status=files_changed_status,
        tests_status="not_run_by_instruction",
        block_reason="none",
        receipt_status="ready",
        receipt_kind="one_codex_execution_receipt",
        suggested_validation_targets=suggested_validation_targets,
    )

def _build_project_browser_autonomous_codex_result_assimilation_state(
    *,
    autonomous_codex_execution_status: str,
    autonomous_codex_execution_source_status: str,
    autonomous_codex_execution_receipt_status: str,
    autonomous_codex_execution_result_status: str,
    autonomous_codex_execution_files_changed_status: str,
    autonomous_codex_execution_tests_status: str,
    autonomous_codex_execution_block_reason: str,
    autonomous_codex_execution_attempt_count: int,
    autonomous_codex_execution_max_attempts: int,
    autonomous_codex_execution_repair_loop_status: str,
    autonomous_codex_execution_suggested_validation_targets: list[str] | None,
    autonomous_codex_invocation_candidate_status: str,
    autonomous_cooldown_status: str,
    autonomous_loop_risk_status: str,
    autonomous_multistep_budget_status: str,
    autonomous_multistep_permission: str,
    autonomous_multistep_state: Mapping[str, Any] | None,
    autonomous_safety_switch_status: str,
    autonomous_manual_override_status: str,
    autonomous_safe_stop_status: str,
    autonomous_execution_permission: str,
    autonomous_execution_bridge_status: str,
    autonomous_execution_bridge_permission: str,
) -> dict[str, Any]:
    codex_execution_status = _normalize_text(
        autonomous_codex_execution_status,
        default="insufficient_truth",
    )
    codex_execution_source_status = _normalize_text(
        autonomous_codex_execution_source_status,
        default="insufficient_truth",
    )
    codex_execution_receipt_status = _normalize_text(
        autonomous_codex_execution_receipt_status,
        default="insufficient_truth",
    )
    codex_execution_result_status = _normalize_text(
        autonomous_codex_execution_result_status,
        default="insufficient_truth",
    )
    codex_execution_files_changed_status = _normalize_text(
        autonomous_codex_execution_files_changed_status,
        default="insufficient_truth",
    )
    codex_execution_tests_status = _normalize_text(
        autonomous_codex_execution_tests_status,
        default="insufficient_truth",
    )
    codex_execution_block_reason = _normalize_text(
        autonomous_codex_execution_block_reason,
        default="insufficient_truth",
    )
    codex_execution_attempt_count = _as_non_negative_int(
        autonomous_codex_execution_attempt_count,
        default=0,
    )
    codex_execution_max_attempts = _as_non_negative_int(
        autonomous_codex_execution_max_attempts,
        default=1,
    )
    codex_execution_repair_loop_status = _normalize_text(
        autonomous_codex_execution_repair_loop_status,
        default="insufficient_truth",
    )
    codex_execution_suggested_validation_targets = _normalize_string_list(
        autonomous_codex_execution_suggested_validation_targets,
    )
    codex_invocation_candidate_status = _normalize_text(
        autonomous_codex_invocation_candidate_status,
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
    multistep_budget_status = _normalize_text(
        autonomous_multistep_budget_status,
        default="insufficient_truth",
    )
    multistep_permission = _normalize_text(
        autonomous_multistep_permission,
        default="insufficient_truth",
    )
    multistep_state = dict(autonomous_multistep_state or {})
    safety_switch_status = _normalize_text(
        autonomous_safety_switch_status,
        default="insufficient_truth",
    )
    manual_override_status = _normalize_text(
        autonomous_manual_override_status,
        default="insufficient_truth",
    )
    safe_stop_status = _normalize_text(
        autonomous_safe_stop_status,
        default="insufficient_truth",
    )
    execution_permission = _normalize_text(
        autonomous_execution_permission,
        default="insufficient_truth",
    )
    execution_bridge_status = _normalize_text(
        autonomous_execution_bridge_status,
        default="insufficient_truth",
    )
    execution_bridge_permission = _normalize_text(
        autonomous_execution_bridge_permission,
        default="insufficient_truth",
    )

    runtime_posture = [
        "metadata_only",
        "no_new_codex_execution",
        "no_tests",
        "no_validation_commands",
        "no_sanity_checks",
        "no_shell_execution",
        "no_browser_action",
        "no_prompt_send",
        "no_browser_enqueue",
        "no_md_write",
        "no_queue_drain",
        "no_retry_execution",
        "no_repair_execution",
        "no_restart_execution",
        "no_approval_execution",
        "no_continuation_execution",
        "no_counter_mutation",
        "no_git_commit",
        "no_git_push",
        "no_pr_create",
        "no_auto_merge",
        "no_github_mutation",
        "no_loop_execution",
        "no_background_runtime",
    ]

    def _read_required_non_negative_int(value: Any) -> tuple[int, bool]:
        if isinstance(value, bool):
            return 0, True
        if isinstance(value, int):
            return (value if value >= 0 else 0), value < 0
        if isinstance(value, str):
            text = value.strip()
            if text.isdigit():
                return int(text), False
        return 0, True

    def _validation_targets_status(targets: list[str]) -> str:
        if not targets:
            return "unavailable"
        if len(targets) > 12:
            return "too_many"
        return "available"

    def _map_codex_block_reason(value: str) -> tuple[str, str]:
        if value == "no_tests_policy_violation":
            return "tests_policy_violation", "tests_policy_violation"
        if value == "source_inconsistent":
            return "source_inconsistent", "insufficient_truth"
        if value in {"cooldown_required", "loop_suspected"}:
            return value, "insufficient_truth"
        if value == "high_risk_action":
            return "high_risk_action", "scope_violation"
        if value == "scope_too_broad":
            return "high_risk_action", "scope_violation"
        if value == "timeout":
            return "codex_timeout", "codex_timeout"
        if value == "codex_failed":
            return "codex_failed", "codex_failed"
        if value == "pause_required":
            return "pause_required", "insufficient_truth"
        if value == "human_review_required":
            return "human_review_required", "insufficient_truth"
        if value == "insufficient_truth":
            return "insufficient_truth", "insufficient_truth"
        if value == "none":
            return "codex_not_executed", "none"
        return "codex_not_executed", "none"

    def _base_state(
        *,
        status: str,
        kind: str,
        outcome: str,
        files_changed_status: str,
        tests_status: str,
        validation_targets_status: str,
        quality_posture: str,
        next_posture: str,
        failure_class: str,
        source_status: str,
        block_reason: str,
        receipt_status: str,
        receipt_kind: str,
    ) -> dict[str, Any]:
        return {
            "project_browser_autonomous_codex_result_assimilation_status": status,
            "project_browser_autonomous_codex_result_assimilation_kind": kind,
            "project_browser_autonomous_codex_result_outcome": outcome,
            "project_browser_autonomous_codex_result_files_changed_status": (
                files_changed_status
            ),
            "project_browser_autonomous_codex_result_tests_status": tests_status,
            "project_browser_autonomous_codex_result_validation_targets_status": (
                validation_targets_status
            ),
            "project_browser_autonomous_codex_result_quality_posture": quality_posture,
            "project_browser_autonomous_codex_result_next_posture": next_posture,
            "project_browser_autonomous_codex_result_failure_class": failure_class,
            "project_browser_autonomous_codex_result_source_status": source_status,
            "project_browser_autonomous_codex_result_block_reason": block_reason,
            "project_browser_autonomous_codex_result_receipt_status": receipt_status,
            "project_browser_autonomous_codex_result_receipt_kind": receipt_kind,
            "project_browser_autonomous_codex_result_runtime_posture": runtime_posture,
        }

    def _insufficient_truth_state(*, block_reason: str) -> dict[str, Any]:
        normalized_block_reason = (
            block_reason
            if block_reason in {"source_inconsistent", "insufficient_truth"}
            else "insufficient_truth"
        )
        return _base_state(
            status="insufficient_truth",
            kind="insufficient_truth_codex_result_assimilation",
            outcome="insufficient_truth",
            files_changed_status="insufficient_truth",
            tests_status="insufficient_truth",
            validation_targets_status="insufficient_truth",
            quality_posture="insufficient_truth",
            next_posture="insufficient_truth",
            failure_class="insufficient_truth",
            source_status="insufficient_truth",
            block_reason=normalized_block_reason,
            receipt_status="insufficient_truth",
            receipt_kind="insufficient_truth_codex_result_receipt",
        )

    if codex_execution_status not in {
        "inactive",
        "executed",
        "blocked",
        "failed",
        "timeout",
        "cooldown_required",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if codex_execution_source_status not in {"valid", "inconsistent", "insufficient_truth"}:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if codex_execution_receipt_status not in {
        "not_created",
        "ready",
        "blocked",
        "failed",
        "timeout",
        "cooldown_required",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if codex_execution_result_status not in {
        "not_executed",
        "succeeded",
        "failed",
        "timeout",
        "blocked",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if codex_execution_files_changed_status not in {
        "unavailable",
        "none",
        "changed",
        "too_many",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if codex_execution_tests_status not in {
        "not_run_by_instruction",
        "attempted_violation",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if codex_execution_block_reason not in {
        "none",
        "candidate_not_ready",
        "prompt_missing",
        "prompt_empty",
        "prompt_too_large",
        "scope_too_broad",
        "high_risk_action",
        "token_too_large",
        "no_tests_policy_violation",
        "source_inconsistent",
        "cooldown_required",
        "loop_suspected",
        "timeout",
        "codex_failed",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if codex_execution_repair_loop_status not in {"not_started", "blocked", "insufficient_truth"}:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if codex_invocation_candidate_status not in {
        "not_created",
        "ready",
        "blocked",
        "failed",
        "timeout",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if cooldown_status not in {"not_required", "required", "blocked", "insufficient_truth"}:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if loop_risk_status not in {"clear", "suspected", "blocked", "insufficient_truth"}:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if multistep_budget_status not in {
        "inactive",
        "ready",
        "blocked",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if multistep_permission not in _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if safety_switch_status not in _PROJECT_BROWSER_AUTONOMOUS_SAFETY_SWITCH_STATUSES:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if manual_override_status not in _PROJECT_BROWSER_AUTONOMOUS_MANUAL_OVERRIDE_STATUSES:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if safe_stop_status not in _PROJECT_BROWSER_AUTONOMOUS_SAFE_STOP_STATUSES:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if execution_permission not in _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if execution_bridge_status not in _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_BRIDGE_STATUSES:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if execution_bridge_permission not in _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS:
        return _insufficient_truth_state(block_reason="insufficient_truth")

    remaining_steps, remaining_steps_invalid = _read_required_non_negative_int(
        multistep_state.get("project_browser_autonomous_multistep_remaining_steps")
    )
    remaining_failures, remaining_failures_invalid = _read_required_non_negative_int(
        multistep_state.get("project_browser_autonomous_multistep_remaining_failures")
    )
    if remaining_steps_invalid or remaining_failures_invalid:
        return _insufficient_truth_state(block_reason="insufficient_truth")

    validation_targets_status = _validation_targets_status(
        codex_execution_suggested_validation_targets
    )

    if codex_execution_source_status == "inconsistent":
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if codex_execution_source_status == "insufficient_truth":
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if codex_execution_status == "insufficient_truth":
        return _insufficient_truth_state(block_reason="insufficient_truth")

    if codex_execution_status == "inactive":
        return _base_state(
            status="inactive",
            kind="none",
            outcome="none",
            files_changed_status="unavailable",
            tests_status="unavailable",
            validation_targets_status="unavailable",
            quality_posture="unknown",
            next_posture="none",
            failure_class="none",
            source_status="valid",
            block_reason="none",
            receipt_status="not_created",
            receipt_kind="none",
        )

    if codex_execution_status == "cooldown_required":
        return _base_state(
            status="cooldown_required",
            kind="cooldown_codex_result_assimilation",
            outcome="codex_blocked",
            files_changed_status="unavailable",
            tests_status="unavailable",
            validation_targets_status="unavailable",
            quality_posture="unknown",
            next_posture="blocked",
            failure_class="none",
            source_status="valid",
            block_reason="cooldown_required",
            receipt_status="blocked",
            receipt_kind="blocked_codex_result_receipt",
        )
    if codex_execution_status == "pause_required":
        return _base_state(
            status="pause_required",
            kind="pause_codex_result_assimilation",
            outcome="codex_blocked",
            files_changed_status="unavailable",
            tests_status="unavailable",
            validation_targets_status="unavailable",
            quality_posture="unknown",
            next_posture="pause_required",
            failure_class="none",
            source_status="valid",
            block_reason="pause_required",
            receipt_status="pause_required",
            receipt_kind="pause_codex_result_receipt",
        )
    if codex_execution_status == "human_review_required":
        return _base_state(
            status="human_review_required",
            kind="human_review_codex_result_assimilation",
            outcome="codex_blocked",
            files_changed_status="unavailable",
            tests_status="unavailable",
            validation_targets_status="unavailable",
            quality_posture="needs_review",
            next_posture="human_review_required",
            failure_class="none",
            source_status="valid",
            block_reason="human_review_required",
            receipt_status="human_review_required",
            receipt_kind="human_review_codex_result_receipt",
        )

    if codex_execution_status == "blocked":
        mapped_block_reason, mapped_failure_class = _map_codex_block_reason(
            codex_execution_block_reason
        )
        return _base_state(
            status="blocked",
            kind="blocked_codex_result_assimilation",
            outcome="codex_blocked",
            files_changed_status=(
                codex_execution_files_changed_status
                if codex_execution_files_changed_status
                in {"unavailable", "none", "changed", "too_many"}
                else "insufficient_truth"
            ),
            tests_status=(
                codex_execution_tests_status
                if codex_execution_tests_status
                in {"not_run_by_instruction", "attempted_violation"}
                else "unavailable"
            ),
            validation_targets_status=validation_targets_status,
            quality_posture="needs_review",
            next_posture="blocked",
            failure_class=(
                "tests_policy_violation"
                if mapped_block_reason == "tests_policy_violation"
                else mapped_failure_class
            ),
            source_status="valid",
            block_reason=mapped_block_reason,
            receipt_status="blocked",
            receipt_kind="blocked_codex_result_receipt",
        )

    if codex_execution_status == "failed":
        return _base_state(
            status="failed",
            kind="failed_codex_result_assimilation",
            outcome="codex_failed",
            files_changed_status=(
                codex_execution_files_changed_status
                if codex_execution_files_changed_status
                in {"unavailable", "none", "changed", "too_many"}
                else "unavailable"
            ),
            tests_status=(
                codex_execution_tests_status
                if codex_execution_tests_status
                in {"not_run_by_instruction", "attempted_violation"}
                else "unavailable"
            ),
            validation_targets_status=validation_targets_status,
            quality_posture="failed",
            next_posture="repair_candidate",
            failure_class="codex_failed",
            source_status="valid",
            block_reason="codex_failed",
            receipt_status="failed",
            receipt_kind="failed_codex_result_receipt",
        )
    if codex_execution_status == "timeout":
        return _base_state(
            status="timeout",
            kind="timeout_codex_result_assimilation",
            outcome="codex_timeout",
            files_changed_status=(
                codex_execution_files_changed_status
                if codex_execution_files_changed_status
                in {"unavailable", "none", "changed", "too_many"}
                else "unavailable"
            ),
            tests_status=(
                codex_execution_tests_status
                if codex_execution_tests_status
                in {"not_run_by_instruction", "attempted_violation"}
                else "unavailable"
            ),
            validation_targets_status=validation_targets_status,
            quality_posture="failed",
            next_posture="retry_candidate",
            failure_class="codex_timeout",
            source_status="valid",
            block_reason="codex_timeout",
            receipt_status="timeout",
            receipt_kind="timeout_codex_result_receipt",
        )

    if codex_execution_status != "executed":
        return _insufficient_truth_state(block_reason="source_inconsistent")

    if codex_execution_receipt_status != "ready":
        return _base_state(
            status="blocked",
            kind="blocked_codex_result_assimilation",
            outcome="codex_blocked",
            files_changed_status="unavailable",
            tests_status="unavailable",
            validation_targets_status="unavailable",
            quality_posture="needs_review",
            next_posture="blocked",
            failure_class="none",
            source_status="valid",
            block_reason="codex_receipt_not_ready",
            receipt_status="blocked",
            receipt_kind="blocked_codex_result_receipt",
        )

    if codex_execution_result_status == "failed":
        return _base_state(
            status="failed",
            kind="failed_codex_result_assimilation",
            outcome="codex_failed",
            files_changed_status=(
                codex_execution_files_changed_status
                if codex_execution_files_changed_status
                in {"unavailable", "none", "changed", "too_many"}
                else "unavailable"
            ),
            tests_status=(
                codex_execution_tests_status
                if codex_execution_tests_status
                in {"not_run_by_instruction", "attempted_violation"}
                else "unavailable"
            ),
            validation_targets_status=validation_targets_status,
            quality_posture="failed",
            next_posture="repair_candidate",
            failure_class="codex_failed",
            source_status="valid",
            block_reason="codex_failed",
            receipt_status="failed",
            receipt_kind="failed_codex_result_receipt",
        )
    if codex_execution_result_status == "timeout":
        return _base_state(
            status="timeout",
            kind="timeout_codex_result_assimilation",
            outcome="codex_timeout",
            files_changed_status=(
                codex_execution_files_changed_status
                if codex_execution_files_changed_status
                in {"unavailable", "none", "changed", "too_many"}
                else "unavailable"
            ),
            tests_status=(
                codex_execution_tests_status
                if codex_execution_tests_status
                in {"not_run_by_instruction", "attempted_violation"}
                else "unavailable"
            ),
            validation_targets_status=validation_targets_status,
            quality_posture="failed",
            next_posture="retry_candidate",
            failure_class="codex_timeout",
            source_status="valid",
            block_reason="codex_timeout",
            receipt_status="timeout",
            receipt_kind="timeout_codex_result_receipt",
        )
    if codex_execution_result_status in {"blocked", "not_executed"}:
        return _base_state(
            status="blocked",
            kind="blocked_codex_result_assimilation",
            outcome="codex_not_executed",
            files_changed_status="unavailable",
            tests_status="unavailable",
            validation_targets_status="unavailable",
            quality_posture="needs_review",
            next_posture="blocked",
            failure_class="none",
            source_status="valid",
            block_reason="codex_not_executed",
            receipt_status="blocked",
            receipt_kind="blocked_codex_result_receipt",
        )
    if codex_execution_result_status == "insufficient_truth":
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if codex_execution_result_status != "succeeded":
        return _insufficient_truth_state(block_reason="source_inconsistent")

    source_conflict = False
    if codex_execution_max_attempts != 1:
        source_conflict = True
    if codex_execution_attempt_count > 1:
        source_conflict = True
    if codex_execution_repair_loop_status not in {"not_started", "blocked"}:
        source_conflict = True
    if codex_invocation_candidate_status != "ready":
        source_conflict = True
    if codex_execution_block_reason != "none":
        source_conflict = True
    if cooldown_status != "not_required":
        source_conflict = True
    if loop_risk_status != "clear":
        source_conflict = True
    if multistep_budget_status != "ready":
        source_conflict = True
    if multistep_permission != "allowed_candidate":
        source_conflict = True
    if remaining_steps <= 0 or remaining_failures <= 0:
        source_conflict = True
    if safety_switch_status in {
        "disabled",
        "stop_all",
        "pause_after_current_step",
        "manual_review_required",
        "pause_required",
        "insufficient_truth",
    }:
        source_conflict = True
    if manual_override_status in {"requested", "required", "blocked", "insufficient_truth"}:
        source_conflict = True
    if safe_stop_status != "not_required":
        source_conflict = True
    if execution_permission != "allowed_candidate":
        source_conflict = True
    if execution_bridge_status != "ready":
        source_conflict = True
    if execution_bridge_permission != "allowed_candidate":
        source_conflict = True
    if source_conflict:
        return _insufficient_truth_state(block_reason="source_inconsistent")

    if codex_execution_tests_status == "attempted_violation":
        return _base_state(
            status="blocked",
            kind="blocked_codex_result_assimilation",
            outcome="codex_blocked",
            files_changed_status=(
                codex_execution_files_changed_status
                if codex_execution_files_changed_status
                in {"unavailable", "none", "changed", "too_many"}
                else "unavailable"
            ),
            tests_status="attempted_violation",
            validation_targets_status=validation_targets_status,
            quality_posture="needs_review",
            next_posture="blocked",
            failure_class="tests_policy_violation",
            source_status="valid",
            block_reason="tests_policy_violation",
            receipt_status="blocked",
            receipt_kind="blocked_codex_result_receipt",
        )
    if codex_execution_tests_status != "not_run_by_instruction":
        return _insufficient_truth_state(block_reason="insufficient_truth")

    if codex_execution_files_changed_status == "too_many":
        return _base_state(
            status="blocked",
            kind="blocked_codex_result_assimilation",
            outcome="codex_blocked",
            files_changed_status="too_many",
            tests_status="not_run_by_instruction",
            validation_targets_status=validation_targets_status,
            quality_posture="needs_review",
            next_posture="blocked",
            failure_class="too_many_files_changed",
            source_status="valid",
            block_reason="files_changed_too_many",
            receipt_status="blocked",
            receipt_kind="blocked_codex_result_receipt",
        )
    if codex_execution_files_changed_status == "insufficient_truth":
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if codex_execution_files_changed_status == "unavailable":
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if validation_targets_status == "too_many":
        return _base_state(
            status="blocked",
            kind="blocked_codex_result_assimilation",
            outcome="codex_blocked",
            files_changed_status=codex_execution_files_changed_status,
            tests_status="not_run_by_instruction",
            validation_targets_status="too_many",
            quality_posture="needs_review",
            next_posture="blocked",
            failure_class="none",
            source_status="valid",
            block_reason="insufficient_truth",
            receipt_status="blocked",
            receipt_kind="blocked_codex_result_receipt",
        )

    if codex_execution_files_changed_status == "none":
        return _base_state(
            status="assimilated",
            kind="codex_result_assimilation",
            outcome="codex_succeeded",
            files_changed_status="none",
            tests_status="not_run_by_instruction",
            validation_targets_status=validation_targets_status,
            quality_posture="needs_review",
            next_posture="ready_for_validation_planning",
            failure_class="no_files_changed",
            source_status="valid",
            block_reason="none",
            receipt_status="ready",
            receipt_kind="one_codex_result_assimilation_receipt",
        )

    quality_posture = (
        "needs_validation"
        if validation_targets_status == "available"
        else "likely_good"
    )
    return _base_state(
        status="assimilated",
        kind="codex_result_assimilation",
        outcome="codex_succeeded",
        files_changed_status="changed",
        tests_status="not_run_by_instruction",
        validation_targets_status=validation_targets_status,
        quality_posture=quality_posture,
        next_posture="ready_for_ledger_update",
        failure_class="none",
        source_status="valid",
        block_reason="none",
        receipt_status="ready",
        receipt_kind="one_codex_result_assimilation_receipt",
    )

def _build_project_browser_autonomous_codex_reentry_invocation_state(
    *,
    repository_path: str,
    reentry_routing_status: str,
    reentry_routing_allowed: bool,
    reentry_prompt_kind: str,
    reentry_prompt_path: str,
    selection_refresh_allowed: bool,
    invocation_readiness_refresh_allowed: bool,
    write_invocation_reentry_prepared: bool,
    reentry_selected_prompt_kind: str,
    reentry_selected_prompt_path: str,
    reentry_selected_prompt_ready: bool,
    reentry_prompt_path_is_exact: bool,
    reentry_prompt_path_exists: bool,
    reentry_prompt_path_is_symlink: bool,
    reentry_prompt_file_non_empty: bool,
    reentry_prompt_file_too_large: bool,
    reentry_max_invocations: int,
    reentry_should_start_next_cycle: bool,
    reentry_should_rollback: bool,
    human_review_required: bool,
    reentry_routing_block_reason: str,
    prior_write_invocation_attempted: bool,
    prior_write_invocation_completed: bool,
) -> dict[str, Any]:
    allowed_statuses = {
        "reentry_invocation_completed_with_changes",
        "reentry_invocation_completed_no_changes",
        "reentry_invocation_completed_failure",
        "reentry_invocation_completed_timeout",
        "blocked_human_review_required",
        "blocked_reentry_routing_not_allowed",
        "blocked_selection_refresh_not_allowed",
        "blocked_invocation_readiness_not_allowed",
        "blocked_write_reentry_not_prepared",
        "blocked_prompt_not_ready",
        "blocked_prompt_path_unsafe",
        "blocked_ambiguous_reentry_prompt_kind",
        "blocked_max_reentry_invocations_not_one",
        "blocked_rollback_required",
        "blocked_insufficient_reentry_invocation_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "prepare_bounded_reentry_codex_invocation",
        "reentry_result_assimilation",
        "manual_review_required",
        "wait_for_more_truth",
        "insufficient_truth",
    }
    allowed_prompt_paths = {
        "/tmp/codex-local-runner-decision/generated_fix_prompt.txt",
        "/tmp/codex-local-runner-decision/generated_next_prompt.txt",
    }
    max_prompt_size_bytes = 20000
    runtime_posture = [
        "prompt180_single_bounded_reentry_invocation",
        "reuses_prompt167_workspace_write_executor",
        "no_retry",
        "no_loop",
        "no_rollback",
        "no_git_stage_commit_push",
        "no_github_mutation",
    ]

    normalized_repository_path = _normalize_text(repository_path, default="")
    normalized_routing_status = _normalize_text(
        reentry_routing_status,
        default="insufficient_truth",
    )
    normalized_reentry_prompt_kind = _normalize_text(reentry_prompt_kind, default="none")
    normalized_reentry_prompt_path = _normalize_text(reentry_prompt_path, default="")
    normalized_selected_prompt_kind = _normalize_text(
        reentry_selected_prompt_kind,
        default="none",
    )
    normalized_selected_prompt_path = _normalize_text(
        reentry_selected_prompt_path,
        default="",
    )
    normalized_block_reason = _normalize_text(reentry_routing_block_reason, default="")

    effective_prompt_kind = (
        normalized_selected_prompt_kind
        if normalized_selected_prompt_kind in {"fix", "next"}
        else normalized_reentry_prompt_kind
    )
    effective_prompt_path = (
        normalized_selected_prompt_path or normalized_reentry_prompt_path
    )

    prompt_path_obj = Path(effective_prompt_path) if effective_prompt_path else None
    prompt_path_is_exact_now = effective_prompt_path in allowed_prompt_paths
    prompt_path_exists_now = bool(prompt_path_obj and prompt_path_obj.exists())
    prompt_path_is_symlink_now = bool(prompt_path_obj and prompt_path_obj.is_symlink())
    prompt_path_is_file_now = bool(prompt_path_obj and prompt_path_obj.is_file())
    prompt_size_bytes_now = 0
    if prompt_path_obj and prompt_path_exists_now and prompt_path_is_file_now and not prompt_path_is_symlink_now:
        try:
            prompt_size_bytes_now = _as_non_negative_int(
                prompt_path_obj.stat().st_size,
                default=0,
            )
        except OSError:
            prompt_size_bytes_now = 0
    prompt_file_non_empty_now = prompt_size_bytes_now > 0
    prompt_file_too_large_now = prompt_size_bytes_now > max_prompt_size_bytes
    prompt_path_safe = bool(
        prompt_path_is_exact_now
        and prompt_path_exists_now
        and prompt_path_is_file_now
        and not prompt_path_is_symlink_now
        and prompt_file_non_empty_now
        and not prompt_file_too_large_now
    )

    normalized_max_invocations = _as_non_negative_int(reentry_max_invocations, default=0)
    ambiguity_detected = bool(
        normalized_reentry_prompt_kind in {"fix", "next"}
        and normalized_selected_prompt_kind in {"fix", "next"}
        and normalized_reentry_prompt_kind != normalized_selected_prompt_kind
    )
    allowed_for_execution = False
    status = "insufficient_truth"
    block_reason = "blocked_insufficient_reentry_invocation_truth"
    next_action = "wait_for_more_truth"
    missing_inputs: list[str] = []
    local_human_review_required = bool(human_review_required)

    if local_human_review_required:
        status = "blocked_human_review_required"
        block_reason = "blocked_human_review_required"
        next_action = "manual_review_required"
    elif bool(reentry_should_rollback):
        status = "blocked_rollback_required"
        block_reason = "blocked_rollback_required"
        next_action = "manual_review_required"
        local_human_review_required = True
    elif not bool(reentry_routing_allowed):
        status = "blocked_reentry_routing_not_allowed"
        block_reason = (
            normalized_block_reason
            if normalized_block_reason
            else "blocked_reentry_routing_not_allowed"
        )
        next_action = "manual_review_required"
        local_human_review_required = True
    elif not bool(selection_refresh_allowed):
        status = "blocked_selection_refresh_not_allowed"
        block_reason = "blocked_selection_refresh_not_allowed"
        next_action = "manual_review_required"
        local_human_review_required = True
    elif not bool(invocation_readiness_refresh_allowed):
        status = "blocked_invocation_readiness_not_allowed"
        block_reason = "blocked_invocation_readiness_not_allowed"
        next_action = "manual_review_required"
        local_human_review_required = True
    elif not bool(write_invocation_reentry_prepared):
        status = "blocked_write_reentry_not_prepared"
        block_reason = "blocked_write_reentry_not_prepared"
        next_action = "manual_review_required"
        local_human_review_required = True
    elif bool(prior_write_invocation_attempted) or bool(prior_write_invocation_completed):
        status = "blocked_invocation_readiness_not_allowed"
        block_reason = "prior_write_invocation_already_attempted"
        next_action = "manual_review_required"
        local_human_review_required = True
    elif ambiguity_detected or effective_prompt_kind not in {"fix", "next"}:
        status = "blocked_ambiguous_reentry_prompt_kind"
        block_reason = "blocked_ambiguous_reentry_prompt_kind"
        next_action = "manual_review_required"
        local_human_review_required = True
    elif not bool(reentry_selected_prompt_ready):
        status = "blocked_prompt_not_ready"
        block_reason = "blocked_prompt_not_ready"
        next_action = "manual_review_required"
        local_human_review_required = True
    elif normalized_max_invocations != 1:
        status = "blocked_max_reentry_invocations_not_one"
        block_reason = "blocked_max_reentry_invocations_not_one"
        next_action = "manual_review_required"
        local_human_review_required = True
    elif not prompt_path_safe:
        status = "blocked_prompt_path_unsafe"
        if not effective_prompt_path:
            block_reason = "blocked_prompt_path_missing"
            missing_inputs.append("reentry_prompt_path")
        elif not prompt_path_is_exact_now:
            block_reason = "blocked_prompt_path_unexpected"
        elif prompt_path_is_symlink_now:
            block_reason = "blocked_prompt_path_symlink"
        elif not prompt_path_exists_now:
            block_reason = "blocked_prompt_path_missing"
        elif not prompt_path_is_file_now:
            block_reason = "blocked_prompt_path_not_file"
        elif not prompt_file_non_empty_now:
            block_reason = "blocked_prompt_empty"
        elif prompt_file_too_large_now:
            block_reason = "blocked_prompt_too_large"
        else:
            block_reason = "blocked_prompt_path_unsafe"
        next_action = "manual_review_required"
        local_human_review_required = True
    elif not normalized_repository_path:
        status = "blocked_insufficient_reentry_invocation_truth"
        block_reason = "blocked_insufficient_reentry_invocation_truth"
        next_action = "wait_for_more_truth"
        missing_inputs.append("repository_path")
        local_human_review_required = True
    elif bool(reentry_should_start_next_cycle):
        status = "blocked_insufficient_reentry_invocation_truth"
        block_reason = "blocked_insufficient_reentry_invocation_truth"
        next_action = "manual_review_required"
        local_human_review_required = True
        missing_inputs.append("reentry_should_start_next_cycle")
    else:
        allowed_for_execution = True
        status = "insufficient_truth"
        block_reason = ""
        next_action = "prepare_bounded_reentry_codex_invocation"
        local_human_review_required = False

    write_state: dict[str, Any] = {}
    reentry_invocation_attempted = False
    reentry_invocation_completed = False
    reentry_invocations_attempted = 0
    reentry_invocations_completed = 0
    result_class = "blocked"
    exit_code = -1
    timed_out = False
    changed_files_after: list[str] = []
    changed_files_count_after = 0
    command: list[str] = []
    stdout_path = "/tmp/codex-local-runner-decision/codex_write_invocation_stdout.txt"
    stderr_path = "/tmp/codex-local-runner-decision/codex_write_invocation_stderr.txt"
    result_path = "/tmp/codex-local-runner-decision/codex_write_invocation_result.json"
    git_diff_name_only_path = "/tmp/codex-local-runner-decision/codex_write_git_diff_name_only.txt"
    git_diff_numstat_path = "/tmp/codex-local-runner-decision/codex_write_git_diff_numstat.txt"
    reentry_result_ready_for_assimilation = False
    reentry_result_assimilation_source = ""
    reentry_result_next_stage = "manual_review_or_blocked_reentry"

    if allowed_for_execution:
        write_state = _build_project_browser_autonomous_codex_write_invocation_state(
            repository_path=normalized_repository_path,
            codex_invocation_readiness_status="ready_to_invoke_codex",
            codex_invocation_readiness_allowed=True,
            selected_prompt_kind=effective_prompt_kind,
            selected_prompt_path=effective_prompt_path,
            selected_prompt_source="project_browser_autonomous_generated_prompt_reentry_routing",
            selected_prompt_ready=True,
            selected_prompt_path_is_exact=True,
            selected_prompt_path_exists=True,
            selected_prompt_path_is_symlink=False,
            selected_prompt_file_non_empty=True,
            selected_prompt_file_too_large=False,
            rollback_required=False,
            human_review_required=False,
            insufficient_truth=False,
            max_invocations=1,
            prior_write_invocation_attempted=bool(prior_write_invocation_attempted),
            prior_write_invocation_completed=bool(prior_write_invocation_completed),
        )
        write_exec_status = _normalize_text(
            write_state.get(
                "project_browser_autonomous_codex_write_invocation_execution_status"
            ),
            default="insufficient_truth",
        )
        write_result_status = _normalize_text(
            write_state.get("project_browser_autonomous_codex_write_invocation_result_status"),
            default="insufficient_truth",
        )
        write_exec_block_reason = _normalize_text(
            write_state.get(
                "project_browser_autonomous_codex_write_invocation_execution_block_reason"
            ),
            default="",
        )
        command = _normalize_string_list(
            write_state.get(
                "project_browser_autonomous_codex_write_invocation_execution_invocation_command"
            )
        )
        stdout_path = _normalize_text(
            write_state.get(
                "project_browser_autonomous_codex_write_invocation_execution_invocation_stdout_path"
            ),
            default=stdout_path,
        )
        stderr_path = _normalize_text(
            write_state.get(
                "project_browser_autonomous_codex_write_invocation_execution_invocation_stderr_path"
            ),
            default=stderr_path,
        )
        result_path = _normalize_text(
            write_state.get("project_browser_autonomous_codex_write_invocation_result_result_json_path"),
            default=result_path,
        )
        git_diff_name_only_path = _normalize_text(
            write_state.get(
                "project_browser_autonomous_codex_write_invocation_result_git_diff_name_only_path"
            ),
            default=git_diff_name_only_path,
        )
        git_diff_numstat_path = _normalize_text(
            write_state.get(
                "project_browser_autonomous_codex_write_invocation_result_git_diff_numstat_path"
            ),
            default=git_diff_numstat_path,
        )
        changed_files_after = _normalize_string_list(
            write_state.get(
                "project_browser_autonomous_codex_write_invocation_result_changed_files_after"
            )
        )
        changed_files_count_after = _as_non_negative_int(
            write_state.get(
                "project_browser_autonomous_codex_write_invocation_result_changed_files_count_after"
            ),
            default=len(changed_files_after),
        )
        exit_code = int(
            _as_int(
                write_state.get(
                    "project_browser_autonomous_codex_write_invocation_result_exit_code"
                ),
                default=-1,
            )
        )
        timed_out = bool(
            write_state.get("project_browser_autonomous_codex_write_invocation_result_timeout", False)
        )
        reentry_invocation_attempted = bool(
            write_state.get(
                "project_browser_autonomous_codex_write_invocation_execution_invocation_attempted",
                False,
            )
        )
        reentry_invocation_completed = bool(
            write_state.get(
                "project_browser_autonomous_codex_write_invocation_execution_invocation_completed",
                False,
            )
        )
        reentry_invocations_attempted = 1 if reentry_invocation_attempted else 0
        reentry_invocations_completed = (
            1 if (reentry_invocation_completed and not timed_out) else 0
        )

        if write_result_status == "completed_with_changes":
            status = "reentry_invocation_completed_with_changes"
            result_class = "completed_with_changes"
            next_action = "reentry_result_assimilation"
            reentry_result_ready_for_assimilation = True
        elif write_result_status == "completed_no_changes":
            status = "reentry_invocation_completed_no_changes"
            result_class = "completed_no_changes"
            next_action = "reentry_result_assimilation"
            reentry_result_ready_for_assimilation = True
        elif write_result_status == "completed_failure":
            status = "reentry_invocation_completed_failure"
            result_class = "completed_failure"
            next_action = "reentry_result_assimilation"
            reentry_result_ready_for_assimilation = True
            local_human_review_required = True
        elif write_result_status == "completed_timeout":
            status = "reentry_invocation_completed_timeout"
            result_class = "completed_timeout"
            next_action = "reentry_result_assimilation"
            reentry_result_ready_for_assimilation = True
            local_human_review_required = True
        else:
            status = "blocked_insufficient_reentry_invocation_truth"
            result_class = "blocked"
            block_reason = (
                write_exec_block_reason
                if write_exec_block_reason
                else (
                    write_exec_status
                    if write_exec_status != "insufficient_truth"
                    else "blocked_insufficient_reentry_invocation_truth"
                )
            )
            next_action = "manual_review_required"
            local_human_review_required = True
            reentry_result_ready_for_assimilation = False

        if reentry_result_ready_for_assimilation:
            reentry_result_assimilation_source = "prompt180_reentry_invocation"
            reentry_result_next_stage = "reentry_result_assimilation"
        else:
            reentry_result_assimilation_source = ""
            reentry_result_next_stage = "manual_review_or_blocked_reentry"

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"

    return {
        "project_browser_autonomous_codex_reentry_invocation_status": status,
        "project_browser_autonomous_codex_reentry_invocation_reentry_invocation_allowed": bool(
            allowed_for_execution
        ),
        "project_browser_autonomous_codex_reentry_invocation_reentry_invocation_attempted": bool(
            reentry_invocation_attempted
        ),
        "project_browser_autonomous_codex_reentry_invocation_reentry_invocation_completed": bool(
            reentry_invocation_completed
        ),
        "project_browser_autonomous_codex_reentry_invocation_reentry_invocation_block_reason": (
            block_reason
        ),
        "project_browser_autonomous_codex_reentry_invocation_reentry_prompt_kind": (
            effective_prompt_kind if effective_prompt_kind in {"fix", "next"} else "none"
        ),
        "project_browser_autonomous_codex_reentry_invocation_reentry_prompt_path": (
            effective_prompt_path
        ),
        "project_browser_autonomous_codex_reentry_invocation_max_reentry_invocations": int(
            normalized_max_invocations
        ),
        "project_browser_autonomous_codex_reentry_invocation_reentry_invocations_attempted": int(
            reentry_invocations_attempted
        ),
        "project_browser_autonomous_codex_reentry_invocation_reentry_invocations_completed": int(
            reentry_invocations_completed
        ),
        "project_browser_autonomous_codex_reentry_invocation_reused_write_invocation_path": True,
        "project_browser_autonomous_codex_reentry_invocation_execution_sandbox": "workspace-write",
        "project_browser_autonomous_codex_reentry_invocation_command": command,
        "project_browser_autonomous_codex_reentry_invocation_stdout_path": stdout_path,
        "project_browser_autonomous_codex_reentry_invocation_stderr_path": stderr_path,
        "project_browser_autonomous_codex_reentry_invocation_result_path": result_path,
        "project_browser_autonomous_codex_reentry_invocation_git_diff_name_only_path": (
            git_diff_name_only_path
        ),
        "project_browser_autonomous_codex_reentry_invocation_git_diff_numstat_path": (
            git_diff_numstat_path
        ),
        "project_browser_autonomous_codex_reentry_invocation_changed_files_after": (
            changed_files_after
        ),
        "project_browser_autonomous_codex_reentry_invocation_changed_files_count_after": int(
            changed_files_count_after
        ),
        "project_browser_autonomous_codex_reentry_invocation_result_class": result_class,
        "project_browser_autonomous_codex_reentry_invocation_exit_code": int(exit_code),
        "project_browser_autonomous_codex_reentry_invocation_timed_out": bool(timed_out),
        "project_browser_autonomous_codex_reentry_invocation_reentry_result_ready_for_assimilation": bool(
            reentry_result_ready_for_assimilation
        ),
        "project_browser_autonomous_codex_reentry_invocation_reentry_result_assimilation_source": (
            reentry_result_assimilation_source
        ),
        "project_browser_autonomous_codex_reentry_invocation_reentry_result_next_stage": (
            reentry_result_next_stage
        ),
        "project_browser_autonomous_codex_reentry_invocation_human_review_required": bool(
            local_human_review_required
        ),
        "project_browser_autonomous_codex_reentry_invocation_next_action": next_action,
        "project_browser_autonomous_codex_reentry_invocation_runtime_posture": runtime_posture,
        "project_browser_autonomous_codex_reentry_invocation_missing_inputs": (
            _serialize_required_signals(missing_inputs)
        ),
    }

def _build_project_browser_autonomous_codex_handoff_state(
    *,
    generated_pr_prompt: str,
) -> dict[str, Any]:
    normalized_prompt = _normalize_text(generated_pr_prompt, default="")
    prompt_present = bool(normalized_prompt)
    status = "codex_handoff_blocked_missing_pr_prompt"
    ready = False
    next_action = "generate_next_pr_prompt"
    if prompt_present:
        status = "codex_handoff_ready"
        ready = True
        next_action = "await_codex_result"
    return {
        "project_browser_autonomous_codex_handoff_status": status,
        "project_browser_autonomous_codex_handoff_source": "prompt252_codex_handoff",
        "project_browser_autonomous_codex_handoff_ready": bool(ready),
        "project_browser_autonomous_codex_handoff_prompt": normalized_prompt if ready else "",
        "project_browser_autonomous_codex_handoff_transport_mode": "manual_or_external",
        "project_browser_autonomous_codex_handoff_codex_execution_requested": False,
        "project_browser_autonomous_codex_handoff_next_action": next_action,
    }

def _build_project_browser_autonomous_codex_result_review_decision_state(
    *,
    explicit_codex_result_summary: str,
    explicit_codex_validation_passed: bool,
) -> dict[str, Any]:
    result_summary = _normalize_text(explicit_codex_result_summary, default="")
    validation_passed = bool(explicit_codex_validation_passed)

    status = "codex_result_review_waiting_for_result"
    result_detected = False
    review_decision = "waiting"
    fix_prompt = ""
    next_action = "await_codex_result"

    if result_summary:
        result_detected = True
        if validation_passed:
            status = "codex_result_review_approved"
            review_decision = "approve"
            next_action = "commit_externally_or_generate_next_pr"
        else:
            status = "codex_result_review_needs_fix"
            review_decision = "fix"
            fix_prompt = (
                "Revise the PR implementation to address validation failure. "
                f"Focus on: {result_summary}"
            )
            next_action = "revise_pr_prompt_or_retry_codex"

    return {
        "project_browser_autonomous_codex_result_review_decision_status": status,
        "project_browser_autonomous_codex_result_review_decision_source": (
            "prompt252_codex_result_review_decision"
        ),
        "project_browser_autonomous_codex_result_review_decision_result_detected": bool(
            result_detected
        ),
        "project_browser_autonomous_codex_result_review_decision_result_summary": (
            result_summary if result_detected else ""
        ),
        "project_browser_autonomous_codex_result_review_decision_validation_passed": bool(
            validation_passed if result_detected else False
        ),
        "project_browser_autonomous_codex_result_review_decision_review_decision": (
            review_decision
        ),
        "project_browser_autonomous_codex_result_review_decision_fix_prompt": (
            fix_prompt if review_decision == "fix" else ""
        ),
        "project_browser_autonomous_codex_result_review_decision_commit_allowed": False,
        "project_browser_autonomous_codex_result_review_decision_next_action": next_action,
    }

def _build_project_browser_autonomous_codex_result_synthetic_seed_state(
    *,
    dry_run: bool,
    scenario_mode_selected: str,
    pr_prompt_ready: bool,
    codex_handoff_ready: bool,
    explicit_codex_result_present: bool,
) -> dict[str, Any]:
    enabled = bool(
        dry_run and pr_prompt_ready and codex_handoff_ready and not explicit_codex_result_present
    )
    if enabled:
        status = "codex_result_synthetic_seed_ready"
        enabled_reason = "normal_dry_run_without_explicit_codex_result"
        next_action = "ingest_codex_result_metadata"
    elif explicit_codex_result_present:
        status = "codex_result_synthetic_seed_skipped_explicit_result_present"
        enabled_reason = "explicit_codex_result_present"
        next_action = "use_explicit_codex_result"
    else:
        status = "codex_result_synthetic_seed_not_applicable"
        enabled_reason = "codex_handoff_not_ready_for_synthetic_result"
        next_action = "await_codex_result"

    changed_files = ["automation/orchestration/planned_execution_runner.py"] if enabled else []
    normalized_scenario_mode = _normalize_text(
        scenario_mode_selected,
        default="approve_single_pr_project_complete",
    )
    validation_passed = bool(enabled)
    result_summary = ""
    if enabled and normalized_scenario_mode == "failed_result_fix_route":
        validation_passed = False
        result_summary = (
            "Synthetic Codex result: validation failed for MVP scenario route; "
            "fix prompt required before continuation."
        )
    elif enabled:
        result_summary = (
            "Synthetic Codex result: implemented the generated PR prompt successfully for MVP verification."
        )

    return {
        "project_browser_autonomous_codex_result_synthetic_seed_status": status,
        "project_browser_autonomous_codex_result_synthetic_seed_source": (
            "prompt254_codex_result_synthetic_seed"
        ),
        "project_browser_autonomous_codex_result_synthetic_seed_enabled": bool(enabled),
        "project_browser_autonomous_codex_result_synthetic_seed_enabled_reason": (
            enabled_reason
        ),
        "project_browser_autonomous_codex_result_synthetic_seed_result_summary": (
            result_summary
        ),
        "project_browser_autonomous_codex_result_synthetic_seed_validation_passed": bool(
            validation_passed if enabled else False
        ),
        "project_browser_autonomous_codex_result_synthetic_seed_changed_files": changed_files,
        "project_browser_autonomous_codex_result_synthetic_seed_ready": bool(enabled),
        "project_browser_autonomous_codex_result_synthetic_seed_next_action": next_action,
    }

def _build_project_browser_autonomous_codex_result_ingestion_state(
    *,
    payload_from_final_override: Mapping[str, Any] | None,
    payload_from_normalized_state: Mapping[str, Any] | None,
    payload_from_explicit_dev_loop_input: Mapping[str, Any] | None,
    payload_from_explicit_codex_result_injection: Mapping[str, Any] | None,
    payload_from_synthetic_seed: Mapping[str, Any] | None,
) -> dict[str, Any]:
    def _normalize_changed_files(value: Any) -> list[str]:
        return _normalize_string_list(value)

    def _has_materialized_result(payload: Mapping[str, Any]) -> bool:
        result_summary = _normalize_text(payload.get("result_summary"), default="")
        changed_files = _normalize_changed_files(payload.get("changed_files"))
        return bool(result_summary or changed_files)

    candidate_payloads: list[tuple[str, dict[str, Any]]] = []
    for source_name, payload in (
        ("final_approved_restart_execution_explicit_codex_result", payload_from_final_override),
        ("existing_normalized_runner_state_explicit_codex_result", payload_from_normalized_state),
        ("explicit_dev_loop_input_codex_result", payload_from_explicit_dev_loop_input),
        (
            "prompt259_explicit_codex_result_injection",
            payload_from_explicit_codex_result_injection,
        ),
        ("prompt254_synthetic_codex_result_seed", payload_from_synthetic_seed),
    ):
        candidate_payloads.append(
            (source_name, dict(payload) if isinstance(payload, Mapping) else {})
        )

    selected_payload: dict[str, Any] = {}
    selected_source = ""
    for source_name, payload in candidate_payloads:
        if not payload:
            continue
        if _has_materialized_result(payload):
            selected_payload = payload
            selected_source = source_name
            break

    result_detected = bool(selected_source)
    result_summary = _normalize_text(selected_payload.get("result_summary"), default="")
    changed_files = _normalize_changed_files(selected_payload.get("changed_files"))
    validation_passed = False
    validation_raw = selected_payload.get("validation_passed")
    if isinstance(validation_raw, bool):
        validation_passed = validation_raw
    elif validation_raw is not None:
        validation_passed = (
            _normalize_text(validation_raw, default="").lower()
            in {"true", "1", "yes", "passed"}
        )

    status = "codex_result_ingestion_waiting_for_result"
    ready = False
    next_action = "await_codex_result"
    if result_detected:
        status = "codex_result_ingestion_ready"
        ready = True
        next_action = "review_codex_result"

    return {
        "project_browser_autonomous_codex_result_ingestion_status": status,
        "project_browser_autonomous_codex_result_ingestion_source": (
            "prompt254_codex_result_ingestion"
        ),
        "project_browser_autonomous_codex_result_ingestion_result_detected": bool(
            result_detected
        ),
        "project_browser_autonomous_codex_result_ingestion_result_source": _normalize_text(
            selected_source,
            default="",
        ),
        "project_browser_autonomous_codex_result_ingestion_result_summary": (
            result_summary if result_detected else ""
        ),
        "project_browser_autonomous_codex_result_ingestion_validation_passed": bool(
            validation_passed if result_detected else False
        ),
        "project_browser_autonomous_codex_result_ingestion_changed_files": (
            changed_files if result_detected else []
        ),
        "project_browser_autonomous_codex_result_ingestion_ready": bool(ready),
        "project_browser_autonomous_codex_result_ingestion_next_action": next_action,
    }

def _build_project_browser_autonomous_codex_execution_gate_state(
    *,
    bounded_loop_state: Mapping[str, Any] | None,
    approved_restart_payload: Mapping[str, Any] | None,
    prior_approved_restart_execution_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    bounded_loop = dict(bounded_loop_state) if isinstance(bounded_loop_state, Mapping) else {}
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
        value = prior_payload.get(key) if key in prior_payload else approved_restart.get(key)
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

    def _read_prompt_snapshot(path_text: str) -> dict[str, Any]:
        path_obj = Path(path_text)
        snapshot = {
            "path": path_text,
            "exists": False,
            "is_file": False,
            "size_bytes": 0,
            "read_error": "",
            "preview": "",
            "fingerprint": "",
            "text": "",
            "non_empty": False,
        }
        if not path_obj.exists():
            return snapshot
        snapshot["exists"] = True
        if not path_obj.is_file():
            return snapshot
        snapshot["is_file"] = True
        try:
            file_size = _as_non_negative_int(path_obj.stat().st_size, default=0)
            with path_obj.open("rb") as file_obj:
                raw = file_obj.read(32768)
        except OSError as exc:
            snapshot["read_error"] = f"{exc.__class__.__name__}:{exc}"
            return snapshot
        text = raw.decode("utf-8", errors="replace").strip()
        snapshot["size_bytes"] = file_size
        snapshot["text"] = text
        snapshot["non_empty"] = bool(text)
        snapshot["preview"] = (" ".join(text.split()))[:500] if text else ""
        snapshot["fingerprint"] = (
            hashlib.sha256(text.encode("utf-8")).hexdigest() if text else ""
        )
        return snapshot

    gate_enabled = _read_flag(
        "project_browser_autonomous_codex_execution_gate_enabled",
        default=False,
    )
    gate_execute_enabled = _read_flag(
        "project_browser_autonomous_codex_execution_gate_execute_enabled",
        default=False,
    )
    bounded_loop_status = _normalize_text(
        bounded_loop.get("project_browser_autonomous_chrome_runner_bridge_bounded_loop_status"),
        default="",
    )
    bounded_loop_next_action = _normalize_text(
        bounded_loop.get("project_browser_autonomous_chrome_runner_bridge_bounded_loop_next_action"),
        default="",
    )
    next_prompt_path = "/tmp/codex-local-runner-decision/generated_next_prompt.txt"
    fix_prompt_path = "/tmp/codex-local-runner-decision/generated_fix_prompt.txt"
    next_prompt_snapshot = _read_prompt_snapshot(next_prompt_path)
    fix_prompt_snapshot = _read_prompt_snapshot(fix_prompt_path)
    local_loop_overlay_state = (
        _overlay_bounded_local_loop_local_loop_state_for_coordinator(
            local_loop_state={},
            approved_restart_payload=approved_restart,
        )
    )
    local_loop_status = _normalize_text(
        local_loop_overlay_state.get("project_browser_autonomous_local_loop_status"),
        default="",
    )
    local_loop_next_action = _normalize_text(
        local_loop_overlay_state.get("project_browser_autonomous_local_loop_next_action"),
        default="",
    )
    local_loop_threshold_ready = bool(
        (
            local_loop_status == "local_loop_ready_run_codex_implementation"
            and local_loop_next_action == "run_codex_implementation"
        )
        or (
            local_loop_status == "local_loop_ready_run_codex_fix"
            and local_loop_next_action == "run_codex_fix"
        )
    )

    prompt_kind = "none"
    prompt_path = ""
    selected_snapshot = {
        "size_bytes": 0,
        "preview": "",
        "fingerprint": "",
        "text": "",
        "exists": False,
        "is_file": False,
        "non_empty": False,
        "read_error": "",
    }
    if bounded_loop_status == "loop_ready_or_routed_to_codex":
        prompt_kind = "implementation"
        prompt_path = next_prompt_path
        selected_snapshot = dict(next_prompt_snapshot)
    elif bounded_loop_status == "loop_ready_or_routed_to_codex_fix":
        prompt_kind = "fix"
        prompt_path = fix_prompt_path
        selected_snapshot = dict(fix_prompt_snapshot)
    elif local_loop_threshold_ready and local_loop_next_action == "run_codex_implementation":
        prompt_kind = "implementation"
        prompt_path = next_prompt_path
        selected_snapshot = dict(next_prompt_snapshot)
    elif local_loop_threshold_ready and local_loop_next_action == "run_codex_fix":
        prompt_kind = "fix"
        prompt_path = fix_prompt_path
        selected_snapshot = dict(fix_prompt_snapshot)

    prompt_fingerprint = _normalize_text(selected_snapshot.get("fingerprint"), default="")
    prompt_preview = _normalize_text(selected_snapshot.get("preview"), default="")
    prompt_text = _normalize_text(selected_snapshot.get("text"), default="")
    prompt_size_bytes = _as_non_negative_int(selected_snapshot.get("size_bytes"), default=0)

    prior_fingerprints = {
        _normalize_text(
            prior_payload.get("project_browser_autonomous_codex_execution_gate_prompt_fingerprint"),
            default="",
        ),
        _normalize_text(
            prior_payload.get(
                "project_browser_autonomous_chrome_runner_bridge_bounded_loop_selected_prompt_fingerprint"
            ),
            default="",
        ),
    }
    prior_fingerprints.discard("")
    duplicate_prompt = bool(prompt_fingerprint and prompt_fingerprint in prior_fingerprints)

    unsafe_tokens = (
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
        "unbounded loop",
        "infinite loop",
        "daemon",
        "scheduler",
        "background queue",
        "queue drain",
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
    lower_prompt = prompt_text.lower()
    unsafe_prompt = bool(prompt_text and any(token in lower_prompt for token in unsafe_tokens))

    bounded_loop_threshold_ready = bounded_loop_status in {
        "loop_ready_or_routed_to_codex",
        "loop_ready_or_routed_to_codex_fix",
    }
    execution_route_threshold_ready = bool(
        bounded_loop_threshold_ready or local_loop_threshold_ready
    )
    prompt_exists = bool(selected_snapshot.get("exists", False))
    prompt_is_file = bool(selected_snapshot.get("is_file", False))
    prompt_non_empty = bool(selected_snapshot.get("non_empty", False))
    prompt_read_error = _normalize_text(selected_snapshot.get("read_error"), default="")
    existing_safe_route = (
        (prompt_kind == "implementation" and bounded_loop_next_action == "run_existing_codex_implementation_step")
        or (prompt_kind == "fix" and bounded_loop_next_action == "run_existing_codex_fix_step")
        or (prompt_kind == "implementation" and local_loop_next_action == "run_codex_implementation")
        or (prompt_kind == "fix" and local_loop_next_action == "run_codex_fix")
    )
    threshold_passed = bool(
        execution_route_threshold_ready
        and prompt_exists
        and prompt_is_file
        and prompt_non_empty
        and not prompt_read_error
        and not unsafe_prompt
        and not duplicate_prompt
    )

    status = "codex_execution_gate_not_requested"
    next_action = "enable_codex_execution_gate"
    blocked_reason = "gate_disabled"
    approved_for_execution = False

    if gate_enabled:
        status = "codex_execution_gate_decision_only"
        next_action = "manual_review_required"
        blocked_reason = "decision_only_execution_disabled"
        if not execution_route_threshold_ready:
            status = "codex_execution_gate_blocked_threshold"
            next_action = "manual_review_required"
            blocked_reason = "execution_route_not_ready_for_codex_gate"
        elif not prompt_exists or not prompt_is_file or not prompt_non_empty or prompt_read_error:
            status = "codex_execution_gate_blocked_missing_routed_prompt"
            next_action = "manual_review_required"
            if prompt_read_error:
                blocked_reason = "routed_prompt_read_error"
            elif not prompt_exists:
                blocked_reason = "routed_prompt_missing"
            elif not prompt_is_file:
                blocked_reason = "routed_prompt_not_file"
            else:
                blocked_reason = "routed_prompt_empty"
        elif duplicate_prompt:
            status = "codex_execution_gate_blocked_duplicate_prompt"
            next_action = "manual_review_required"
            blocked_reason = "duplicate_prompt_fingerprint"
        elif unsafe_prompt:
            status = "codex_execution_gate_blocked_unsafe_prompt"
            next_action = "manual_review_required"
            blocked_reason = "unsafe_prompt_detected"
        elif not threshold_passed:
            status = "codex_execution_gate_blocked_threshold"
            next_action = "manual_review_required"
            blocked_reason = "threshold_not_passed"
        elif not existing_safe_route:
            status = "codex_execution_gate_blocked_no_existing_codex_route"
            next_action = "manual_review_required"
            blocked_reason = "existing_safe_codex_route_not_detected"
        elif not gate_execute_enabled:
            status = "codex_execution_gate_decision_only"
            next_action = (
                "run_existing_codex_implementation_step"
                if prompt_kind == "implementation"
                else "run_existing_codex_fix_step"
            )
            blocked_reason = "execution_not_enabled"
        else:
            status = "codex_execution_gate_ready"
            next_action = (
                "run_existing_codex_implementation_step"
                if prompt_kind == "implementation"
                else "run_existing_codex_fix_step"
            )
            blocked_reason = "none"
            approved_for_execution = True

    return {
        "project_browser_autonomous_codex_execution_gate_status": status,
        "project_browser_autonomous_codex_execution_gate_next_action": next_action,
        "project_browser_autonomous_codex_execution_gate_enabled": bool(gate_enabled),
        "project_browser_autonomous_codex_execution_gate_execute_enabled": bool(
            gate_execute_enabled
        ),
        "project_browser_autonomous_codex_execution_gate_prompt_kind": prompt_kind,
        "project_browser_autonomous_codex_execution_gate_prompt_path": prompt_path,
        "project_browser_autonomous_codex_execution_gate_prompt_size_bytes": prompt_size_bytes,
        "project_browser_autonomous_codex_execution_gate_prompt_fingerprint": prompt_fingerprint,
        "project_browser_autonomous_codex_execution_gate_prompt_preview": prompt_preview,
        "project_browser_autonomous_codex_execution_gate_threshold_passed": bool(threshold_passed),
        "project_browser_autonomous_codex_execution_gate_approved_for_execution": bool(
            approved_for_execution
        ),
        "project_browser_autonomous_codex_execution_gate_blocked_reason": blocked_reason,
    }

def _build_project_browser_autonomous_codex_capture_gate_state(
    *,
    codex_execution_gate_state: Mapping[str, Any] | None,
    approved_restart_payload: Mapping[str, Any] | None,
    prior_approved_restart_execution_payload: Mapping[str, Any] | None,
    execution_repo_path: str,
) -> dict[str, Any]:
    codex_gate = dict(codex_execution_gate_state) if isinstance(codex_execution_gate_state, Mapping) else {}
    approved_restart = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    prior_payload = (
        dict(prior_approved_restart_execution_payload)
        if isinstance(prior_approved_restart_execution_payload, Mapping)
        else {}
    )

    def _read_flag(key: str, *, default: bool = False) -> bool:
        value = approved_restart.get(key) if key in approved_restart else prior_payload.get(key)
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

    def _read_text_bounded(path_text: str, *, read_limit_bytes: int = 32768) -> str:
        path_obj = Path(path_text)
        if not path_obj.exists() or not path_obj.is_file():
            return ""
        try:
            with path_obj.open("rb") as file_obj:
                raw = file_obj.read(read_limit_bytes)
        except OSError:
            return ""
        return raw.decode("utf-8", errors="replace")

    def _parse_capture_stdout(stdout_text: str) -> tuple[str, str]:
        report = ""
        patch = ""
        for raw_line in stdout_text.splitlines():
            line = _normalize_text(raw_line, default="")
            if line.startswith("REPORT="):
                report = line.partition("=")[2].strip()
            elif line.startswith("PATCH="):
                patch = line.partition("=")[2].strip()
        return report, patch

    def _extract_changed_files(report_text: str) -> list[str]:
        changed: list[str] = []
        if not report_text:
            return changed
        capture = False
        for raw_line in report_text.splitlines():
            line = raw_line.rstrip("\n")
            normalized = line.strip()
            if normalized.startswith("## Diff name-status - unstaged tracked") or normalized.startswith(
                "## Diff name-status - staged"
            ):
                capture = True
                continue
            if capture and normalized.startswith("## "):
                capture = False
            if not capture or not normalized:
                continue
            parts = normalized.split(None, 1)
            if len(parts) != 2:
                continue
            status_code = parts[0]
            file_path = parts[1].strip()
            if status_code and status_code[0] in {"A", "C", "D", "M", "R", "T", "U"} and file_path:
                changed.append(file_path)
        return _normalize_string_list(changed, sort_items=True)

    capture_enabled = _read_flag(
        "project_browser_autonomous_codex_capture_gate_enabled",
        default=False,
    )
    capture_execute_enabled = _read_flag(
        "project_browser_autonomous_codex_capture_gate_execute_enabled",
        default=False,
    )
    gate_status = _normalize_text(
        codex_gate.get("project_browser_autonomous_codex_execution_gate_status"),
        default="",
    )
    gate_approved = bool(
        codex_gate.get("project_browser_autonomous_codex_execution_gate_approved_for_execution", False)
    )
    prompt_kind = _normalize_text(
        codex_gate.get("project_browser_autonomous_codex_execution_gate_prompt_kind"),
        default="none",
    )
    prompt_path = _normalize_text(
        codex_gate.get("project_browser_autonomous_codex_execution_gate_prompt_path"),
        default="",
    )
    prompt_fingerprint = _normalize_text(
        codex_gate.get("project_browser_autonomous_codex_execution_gate_prompt_fingerprint"),
        default="",
    )
    codex_route_next_action = _normalize_text(
        codex_gate.get("project_browser_autonomous_codex_execution_gate_next_action"),
        default="",
    )
    has_existing_codex_execution_route = codex_route_next_action in {
        "run_existing_codex_implementation_step",
        "run_existing_codex_fix_step",
    }

    script_path = "scripts/capture_prompt_diff.sh"
    script_path_obj = Path(script_path)
    script_exists = script_path_obj.exists() and script_path_obj.is_file() and not script_path_obj.is_symlink()
    known_output_dir = Path("/tmp/codex-local-runner-diff-logs")

    status = "codex_capture_gate_not_requested"
    next_action = "enable_codex_capture_gate"
    blocked_reason = "capture_gate_disabled"
    changed_files: list[str] = []
    diff_summary = ""
    validation_summary = ""
    codex_output_summary = ""
    capture_output_path = ""
    capture_artifact_paths: list[str] = []
    capture_failure_count = 0

    if capture_enabled:
        if gate_status != "codex_execution_gate_ready" or not gate_approved:
            status = "codex_capture_gate_blocked_missing_execution_gate"
            next_action = "manual_review_required"
            blocked_reason = "codex_execution_gate_not_ready_or_not_approved"
        elif not has_existing_codex_execution_route:
            status = "codex_capture_gate_blocked_no_existing_codex_execution_route"
            next_action = "manual_review_required"
            blocked_reason = "no_existing_codex_execution_route"
        elif not script_exists:
            status = "codex_capture_gate_blocked_missing_capture_script"
            next_action = "manual_review_required"
            blocked_reason = "capture_script_missing_or_unsafe_path"
        elif not capture_execute_enabled:
            status = "codex_capture_gate_decision_only"
            next_action = "enable_codex_capture_execute"
            blocked_reason = "execution_not_enabled"
        else:
            status = "codex_capture_gate_ready"
            next_action = "capture_with_existing_script"
            blocked_reason = "none"

            repo_path_text = _normalize_text(execution_repo_path, default="")
            repo_path_obj = Path(repo_path_text) if repo_path_text else Path.cwd()
            if not repo_path_obj.exists() or not repo_path_obj.is_dir():
                status = "codex_capture_gate_blocked_execution_or_capture_failed"
                next_action = "manual_review_required"
                blocked_reason = "execution_repo_path_unavailable"
            else:
                try:
                    capture_run = subprocess.run(
                        [script_path],
                        cwd=str(repo_path_obj),
                        capture_output=True,
                        text=True,
                        timeout=120,
                        check=False,
                    )
                except (OSError, subprocess.SubprocessError):
                    status = "codex_capture_gate_blocked_execution_or_capture_failed"
                    next_action = "manual_review_required"
                    blocked_reason = "capture_script_execution_failed"
                else:
                    if int(capture_run.returncode) != 0:
                        status = "codex_capture_gate_blocked_execution_or_capture_failed"
                        next_action = "manual_review_required"
                        blocked_reason = "capture_script_nonzero_exit"
                    report_path_text, patch_path_text = _parse_capture_stdout(
                        _normalize_text(capture_run.stdout, default="")
                    )
                    candidate_artifacts: list[str] = []
                    for path_text in (report_path_text, patch_path_text):
                        if path_text:
                            candidate_artifacts.append(path_text)
                    if not candidate_artifacts and known_output_dir.exists() and known_output_dir.is_dir():
                        report_candidates = sorted(
                            known_output_dir.glob("*_diff_report.txt"),
                            key=lambda path: path.stat().st_mtime if path.exists() else 0,
                            reverse=True,
                        )
                        patch_candidates = sorted(
                            known_output_dir.glob("*_full.patch"),
                            key=lambda path: path.stat().st_mtime if path.exists() else 0,
                            reverse=True,
                        )
                        if report_candidates:
                            candidate_artifacts.append(str(report_candidates[0]))
                        if patch_candidates:
                            candidate_artifacts.append(str(patch_candidates[0]))
                    capture_artifact_paths = _normalize_string_list(candidate_artifacts, sort_items=False)
                    report_text = ""
                    patch_text = ""
                    if capture_artifact_paths:
                        for artifact_path in capture_artifact_paths:
                            if artifact_path.endswith("_diff_report.txt"):
                                report_text = _read_text_bounded(artifact_path, read_limit_bytes=32768)
                                if report_text and not capture_output_path:
                                    capture_output_path = artifact_path
                            elif artifact_path.endswith("_full.patch"):
                                patch_text = _read_text_bounded(artifact_path, read_limit_bytes=32768)
                    changed_files = _extract_changed_files(report_text)
                    if report_text:
                        diff_summary = (
                            f"capture report available; changed_files={len(changed_files)}; "
                            f"report_chars={len(report_text)}"
                        )
                    elif patch_text:
                        diff_summary = (
                            f"capture patch available; changed_files={len(changed_files)}; "
                            f"patch_chars={len(patch_text)}"
                        )
                    else:
                        diff_summary = "capture output unavailable"
                    if "Diff check" in report_text:
                        if "error:" in report_text.lower():
                            validation_summary = "diff_check_has_errors"
                        else:
                            validation_summary = "diff_check_present"
                    else:
                        validation_summary = "validation_not_available"
                    codex_output_summary = (
                        f"prompt_kind={prompt_kind}; prompt_fingerprint={prompt_fingerprint[:16]}; "
                        f"capture_exit_code={int(capture_run.returncode)}"
                    )
                    if (
                        status == "codex_capture_gate_ready"
                        and not report_text
                        and not patch_text
                    ):
                        status = "codex_capture_gate_blocked_capture_unavailable"
                        next_action = "manual_review_required"
                        blocked_reason = "capture_output_unavailable"
                    elif status == "codex_capture_gate_ready":
                        status = "codex_capture_gate_captured"
                        next_action = "prepare_chatgpt_diff_review_request"
                        blocked_reason = "none"

    if status.startswith("codex_capture_gate_blocked_"):
        capture_failure_count = 1

    return {
        "project_browser_autonomous_codex_capture_gate_status": status,
        "project_browser_autonomous_codex_capture_gate_next_action": next_action,
        "project_browser_autonomous_codex_capture_gate_enabled": bool(capture_enabled),
        "project_browser_autonomous_codex_capture_gate_execute_enabled": bool(
            capture_execute_enabled
        ),
        "project_browser_autonomous_codex_capture_gate_prompt_kind": prompt_kind,
        "project_browser_autonomous_codex_capture_gate_prompt_path": prompt_path,
        "project_browser_autonomous_codex_capture_gate_prompt_fingerprint": prompt_fingerprint,
        "project_browser_autonomous_codex_capture_gate_script_path": script_path,
        "project_browser_autonomous_codex_capture_gate_changed_files": _normalize_string_list(
            changed_files
        ),
        "project_browser_autonomous_codex_capture_gate_diff_summary": _normalize_text(
            diff_summary,
            default="",
        ),
        "project_browser_autonomous_codex_capture_gate_validation_summary": _normalize_text(
            validation_summary,
            default="",
        ),
        "project_browser_autonomous_codex_capture_gate_codex_output_summary": _normalize_text(
            codex_output_summary,
            default="",
        ),
        "project_browser_autonomous_codex_capture_gate_capture_output_path": _normalize_text(
            capture_output_path,
            default="",
        ),
        "project_browser_autonomous_codex_capture_gate_capture_artifact_paths": (
            _normalize_string_list(capture_artifact_paths)
        ),
        "project_browser_autonomous_codex_capture_gate_blocked_reason": _normalize_text(
            blocked_reason,
            default="",
        ),
        "project_browser_autonomous_codex_capture_gate_capture_failure_count": _as_non_negative_int(
            capture_failure_count,
            default=0,
        ),
    }

def _build_project_browser_autonomous_codex_fix_prompt_generation_state() -> dict[str, Any]:
    route_dir = Path("/tmp/codex-local-runner-decision/chatgpt_diff_review_route")
    response_dir = Path("/tmp/codex-local-runner-decision/chatgpt_diff_review_response")
    capture_dir = Path("/tmp/codex-local-runner-decision/local_git_diff_capture")
    output_dir = Path("/tmp/codex-local-runner-decision/codex_fix_prompt")

    route_decision_path = route_dir / "review_route_decision.json"
    review_decision_path = response_dir / "review_decision.json"
    changed_files_path = capture_dir / "changed_files.json"
    fix_prompt_path = output_dir / "codex_fix_prompt.md"
    fix_request_path = output_dir / "codex_fix_request.json"
    fix_summary_path = output_dir / "codex_fix_summary.md"

    status = "codex_fix_prompt_generation_blocked_missing_review_route"
    next_action = "blocked_missing_review_route"
    selected_route = "none"
    blocked_reason = "missing_review_route_decision"
    runtime_posture = [
        "metadata_only_fix_prompt_generation",
        "no_codex_invocation",
        "no_fix_execution",
        "no_commit_or_tag_execution",
        "no_push_or_pr_or_merge",
        "probe_file_disposable_guard_required",
    ]

    artifact_paths = {
        "input_review_route_decision_json": str(route_decision_path),
        "input_review_decision_json": str(review_decision_path),
        "input_changed_files_json": str(changed_files_path),
        "codex_fix_prompt_md": str(fix_prompt_path),
        "codex_fix_request_json": str(fix_request_path),
        "codex_fix_summary_md": str(fix_summary_path),
    }

    decision = "manual_review"
    confidence = "low"
    route_blocked_reason = "missing_review_route_decision"
    probe_file_present = False
    probe_file_classification = "unknown"
    reviewable_changed_files: list[str] = []
    blocking_issues: list[str] = []

    route_payload: Mapping[str, Any] | None = None
    if route_decision_path.exists():
        try:
            loaded = json.loads(route_decision_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            blocked_reason = "invalid_review_route_decision_json"
        else:
            if isinstance(loaded, Mapping):
                route_payload = loaded
            else:
                blocked_reason = "review_route_decision_not_object"
    else:
        blocked_reason = "missing_review_route_decision"

    if isinstance(route_payload, Mapping):
        selected_route = _normalize_text(route_payload.get("selected_route"), default="none")
        if selected_route not in {"approve", "fix", "revert", "manual_review", "none"}:
            selected_route = "none"
        decision = _normalize_text(route_payload.get("decision"), default="manual_review")
        if decision not in {"approve", "fix", "revert", "manual_review"}:
            decision = "manual_review"
        confidence = _normalize_text(route_payload.get("confidence"), default="low").lower()
        if confidence not in {"high", "medium", "low"}:
            confidence = "low"
        route_blocked_reason = _normalize_text(
            route_payload.get("blocked_reason"),
            default="none",
        )
        probe_file_present = bool(route_payload.get("probe_file_present", False))
        probe_file_classification = _normalize_text(
            route_payload.get("probe_file_classification"),
            default="unknown",
        )

    if selected_route != "fix":
        status = "codex_fix_prompt_generation_blocked_route_not_fix"
        next_action = "blocked_route_not_fix"
        blocked_reason = (
            f"selected_route_not_fix:{selected_route}" if selected_route else "selected_route_not_fix:none"
        )
    elif not isinstance(route_payload, Mapping):
        status = "codex_fix_prompt_generation_blocked_missing_review_route"
        next_action = "blocked_missing_review_route"
    else:
        if changed_files_path.exists():
            try:
                changed_files_payload = json.loads(changed_files_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                changed_files_payload = None
            if isinstance(changed_files_payload, Mapping):
                entries = changed_files_payload.get("changed_files")
                if isinstance(entries, list):
                    for entry in entries:
                        if not isinstance(entry, Mapping):
                            continue
                        path_text = _normalize_text(entry.get("path"), default="")
                        if not path_text:
                            continue
                        if bool(entry.get("reviewable", False)):
                            reviewable_changed_files.append(path_text)
                        if path_text == "tmp_runner_live_write_probe.txt":
                            probe_file_present = True
                            if _normalize_text(
                                probe_file_classification,
                                default="",
                            ).lower() in {"", "unknown", "present_unclassified"}:
                                if bool(entry.get("runtime_only", False)):
                                    probe_file_classification = "runtime_only"
                                elif bool(entry.get("reviewable", False)):
                                    probe_file_classification = "probe_disposable_local_change"
                                else:
                                    probe_file_classification = "present_unclassified"

        if review_decision_path.exists():
            try:
                review_decision_payload = json.loads(
                    review_decision_path.read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError):
                review_decision_payload = None
            if isinstance(review_decision_payload, Mapping):
                blocking_issues = _normalize_string_list(
                    review_decision_payload.get("blocking_issues")
                )

        fix_request_payload: dict[str, Any] = {
            "status": "ready_for_bounded_codex_fix_invocation",
            "selected_route": "fix",
            "objective": (
                "Apply the minimum metadata-only fix so tmp_runner_live_write_probe.txt is always "
                "treated as disposable probe evidence and cannot enter product-code commit/readiness."
            ),
            "source_artifacts": artifact_paths,
            "review_route_decision": {
                "decision": decision,
                "confidence": confidence,
                "blocked_reason": route_blocked_reason,
            },
            "probe_file": {
                "path": "tmp_runner_live_write_probe.txt",
                "present": bool(probe_file_present),
                "classification": _normalize_text(
                    probe_file_classification,
                    default="unknown",
                ),
            },
            "reviewable_changed_files": sorted(set(reviewable_changed_files)),
            "blocking_issues": _normalize_string_list(blocking_issues),
            "constraints": {
                "preserve_existing_behaviors": [
                    "Prompt285-B",
                    "Prompt286",
                    "Prompt287",
                    "Prompt288",
                    "Prompt288-fix",
                ],
                "forbidden_actions": [
                    "invoke_codex",
                    "execute_fix_prompt",
                    "commit_or_tag",
                    "push_or_pr_or_merge",
                    "daemon_or_scheduler",
                    "unbounded_retry_or_polling_loop",
                    "delete_runtime_artifacts",
                ],
                "tmp_runner_live_write_probe_handling": [
                    "treat_as_disposable_probe_artifact",
                    "prepare_exclusion_from_product_commit_readiness",
                    "do_not_delete_in_this_step",
                ],
                "scope": ["automation/orchestration/planned_execution_runner.py"],
            },
            "next_action": "ready_for_bounded_codex_fix_invocation",
            "runtime_posture": runtime_posture,
        }
        prompt_lines = [
            "# Bounded Codex Fix Prompt",
            "",
            "Mode: Implement",
            "",
            "Goal:",
            "- Apply the minimum metadata-only fix for the selected `fix` route.",
            "- Ensure `tmp_runner_live_write_probe.txt` is always treated as disposable probe-only evidence and cannot be included in product-code commit/readiness.",
            "",
            "Allowed files:",
            "- `automation/orchestration/planned_execution_runner.py`",
            "",
            "Forbidden actions:",
            "- Do not invoke Codex from this step.",
            "- Do not execute the generated fix.",
            "- Do not commit/tag/push/create PR/merge/delete branches.",
            "- Do not add daemon/scheduler/polling loops/unbounded retries.",
            "- Do not rewrite unrelated review/capture surfaces.",
            "- Do not delete runtime artifacts.",
            "- Do not delete `tmp_runner_live_write_probe.txt` in this step.",
            "",
            "Required behavior:",
            "- Keep Prompt285-B / Prompt286 / Prompt287 / Prompt288 / Prompt288-fix behavior intact.",
            "- Address only the selected fix-route blocker with a bounded change.",
            "- Prepare `tmp_runner_live_write_probe.txt` for exclusion from product-code commit/readiness while preserving it as disposable probe evidence.",
            "",
            "Validation allowed:",
            "- `python -m py_compile automation/orchestration/planned_execution_runner.py`",
            "",
            "Expected output:",
            "- Metadata-only fix readiness for the next bounded Codex fix invocation step.",
        ]
        if blocking_issues:
            prompt_lines.extend(["", "Review blocking issues context:"])
            for issue in blocking_issues:
                prompt_lines.append(f"- {issue}")
        prompt_body = "\n".join(prompt_lines) + "\n"

        summary_lines = [
            "# Codex Fix Prompt Generation",
            "",
            "- Status: `codex_fix_prompt_generation_completed`",
            "- Next action: `ready_for_bounded_codex_fix_invocation`",
            "- Selected route: `fix`",
            f"- Source review route decision: `{str(route_decision_path)}`",
            f"- Probe file present: `{str(bool(probe_file_present)).lower()}`",
            f"- Probe file classification: `{_normalize_text(probe_file_classification, default='unknown')}`",
            "- Codex execution invoked: `false`",
        ]

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            fix_prompt_path.write_text(prompt_body, encoding="utf-8")
            fix_request_path.write_text(
                json.dumps(fix_request_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            fix_summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
            status = "codex_fix_prompt_generation_completed"
            next_action = "ready_for_bounded_codex_fix_invocation"
            blocked_reason = "none"
        except OSError:
            status = "codex_fix_prompt_generation_blocked_write_failed"
            next_action = "blocked_missing_review_route"
            blocked_reason = "fix_prompt_artifact_write_failed"

    return {
        "project_browser_autonomous_codex_fix_prompt_generation_status": status,
        "project_browser_autonomous_codex_fix_prompt_generation_next_action": next_action,
        "project_browser_autonomous_codex_fix_prompt_generation_selected_route": selected_route,
        "project_browser_autonomous_codex_fix_prompt_generation_fix_prompt_path": str(
            fix_prompt_path
        ),
        "project_browser_autonomous_codex_fix_prompt_generation_fix_request_path": str(
            fix_request_path
        ),
        "project_browser_autonomous_codex_fix_prompt_generation_fix_summary_path": str(
            fix_summary_path
        ),
        "project_browser_autonomous_codex_fix_prompt_generation_blocked_reason": blocked_reason,
        "project_browser_autonomous_codex_fix_prompt_generation_runtime_posture": runtime_posture,
        "project_browser_autonomous_codex_fix_prompt_generation_artifact_paths": artifact_paths,
    }

def _build_project_browser_autonomous_codex_execution_connector_state(
    *,
    local_loop_state: Mapping[str, Any] | None,
    codex_execution_gate_state: Mapping[str, Any] | None,
    codex_capture_gate_state: Mapping[str, Any] | None,
    chrome_runner_bridge_bounded_loop_state: Mapping[str, Any] | None,
    approved_restart_payload: Mapping[str, Any] | None,
    prior_approved_restart_execution_payload: Mapping[str, Any] | None,
    execution_repo_path: str,
) -> dict[str, Any]:
    local_loop = dict(local_loop_state) if isinstance(local_loop_state, Mapping) else {}
    codex_gate = (
        dict(codex_execution_gate_state)
        if isinstance(codex_execution_gate_state, Mapping)
        else {}
    )
    codex_capture = dict(codex_capture_gate_state) if isinstance(codex_capture_gate_state, Mapping) else {}
    bounded_loop = (
        dict(chrome_runner_bridge_bounded_loop_state)
        if isinstance(chrome_runner_bridge_bounded_loop_state, Mapping)
        else {}
    )
    approved_restart = dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    prior_payload = (
        dict(prior_approved_restart_execution_payload)
        if isinstance(prior_approved_restart_execution_payload, Mapping)
        else {}
    )

    def _read_flag(key: str, *, default: bool = False) -> bool:
        value = prior_payload.get(key) if key in prior_payload else approved_restart.get(key)
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

    def _read_text_bounded(path_text: str, *, limit_bytes: int = 32768) -> tuple[str, str]:
        path_obj = Path(path_text)
        if not path_obj.exists():
            return ("", "missing")
        if not path_obj.is_file():
            return ("", "not_file")
        try:
            with path_obj.open("rb") as file_obj:
                raw = file_obj.read(limit_bytes)
        except OSError as exc:
            return ("", f"read_error:{exc.__class__.__name__}")
        text = raw.decode("utf-8", errors="replace").strip()
        if not text:
            return ("", "empty")
        return (text, "ready")

    connector_enabled = _read_flag(
        "project_browser_autonomous_codex_execution_connector_enabled",
        default=False,
    )
    connector_execute_enabled = _read_flag(
        "project_browser_autonomous_codex_execution_connector_execute_enabled",
        default=False,
    )

    local_loop_status = _normalize_text(
        local_loop.get("project_browser_autonomous_local_loop_status"),
        default="",
    )
    local_loop_next_action = _normalize_text(
        local_loop.get("project_browser_autonomous_local_loop_next_action"),
        default="",
    )
    local_loop_prompt = _normalize_text(
        local_loop.get("project_browser_autonomous_local_loop_selected_prompt"),
        default="",
    )
    local_loop_prompt_fingerprint = _normalize_text(
        local_loop.get("project_browser_autonomous_local_loop_selected_prompt_fingerprint"),
        default="",
    )

    codex_gate_status = _normalize_text(
        codex_gate.get("project_browser_autonomous_codex_execution_gate_status"),
        default="",
    )
    codex_gate_approved = bool(
        codex_gate.get("project_browser_autonomous_codex_execution_gate_approved_for_execution", False)
    )
    codex_gate_prompt_kind = _normalize_text(
        codex_gate.get("project_browser_autonomous_codex_execution_gate_prompt_kind"),
        default="",
    )
    codex_gate_prompt_path = _normalize_text(
        codex_gate.get("project_browser_autonomous_codex_execution_gate_prompt_path"),
        default="",
    )
    codex_gate_prompt_fingerprint = _normalize_text(
        codex_gate.get("project_browser_autonomous_codex_execution_gate_prompt_fingerprint"),
        default="",
    )
    codex_gate_next_action = _normalize_text(
        codex_gate.get("project_browser_autonomous_codex_execution_gate_next_action"),
        default="",
    )

    _ = _normalize_text(
        codex_capture.get("project_browser_autonomous_codex_capture_gate_status"),
        default="",
    )
    _ = _normalize_text(
        bounded_loop.get("project_browser_autonomous_chrome_runner_bridge_bounded_loop_status"),
        default="",
    )

    status = "codex_execution_connector_not_requested"
    next_action = "enable_codex_execution_connector"
    executed = False
    prompt_kind = ""
    prompt_path = ""
    prompt_fingerprint = ""
    route_name = ""
    output_preview = ""
    blocked_reason = "connector_disabled"

    if not connector_enabled:
        return {
            "project_browser_autonomous_codex_execution_connector_status": status,
            "project_browser_autonomous_codex_execution_connector_next_action": next_action,
            "project_browser_autonomous_codex_execution_connector_enabled": bool(
                connector_enabled
            ),
            "project_browser_autonomous_codex_execution_connector_execute_enabled": bool(
                connector_execute_enabled
            ),
            "project_browser_autonomous_codex_execution_connector_executed": bool(executed),
            "project_browser_autonomous_codex_execution_connector_prompt_kind": prompt_kind,
            "project_browser_autonomous_codex_execution_connector_prompt_path": prompt_path,
            "project_browser_autonomous_codex_execution_connector_prompt_fingerprint": (
                prompt_fingerprint
            ),
            "project_browser_autonomous_codex_execution_connector_route_name": route_name,
            "project_browser_autonomous_codex_execution_connector_output_preview": output_preview,
            "project_browser_autonomous_codex_execution_connector_blocked_reason": blocked_reason,
        }

    if not connector_execute_enabled:
        prompt_kind = (
            "next"
            if local_loop_next_action == "run_codex_implementation"
            else ("fix" if local_loop_next_action == "run_codex_fix" else "")
        )
        prompt_path = _normalize_text(codex_gate_prompt_path, default="")
        prompt_fingerprint = _normalize_text(codex_gate_prompt_fingerprint, default="")
        if not prompt_fingerprint:
            prompt_fingerprint = local_loop_prompt_fingerprint
        status = "codex_execution_connector_decision_only"
        next_action = "set_execute_enabled_for_single_codex_step"
        blocked_reason = "execute_not_enabled"
        return {
            "project_browser_autonomous_codex_execution_connector_status": status,
            "project_browser_autonomous_codex_execution_connector_next_action": next_action,
            "project_browser_autonomous_codex_execution_connector_enabled": bool(
                connector_enabled
            ),
            "project_browser_autonomous_codex_execution_connector_execute_enabled": bool(
                connector_execute_enabled
            ),
            "project_browser_autonomous_codex_execution_connector_executed": bool(executed),
            "project_browser_autonomous_codex_execution_connector_prompt_kind": prompt_kind,
            "project_browser_autonomous_codex_execution_connector_prompt_path": prompt_path,
            "project_browser_autonomous_codex_execution_connector_prompt_fingerprint": (
                prompt_fingerprint
            ),
            "project_browser_autonomous_codex_execution_connector_route_name": route_name,
            "project_browser_autonomous_codex_execution_connector_output_preview": output_preview,
            "project_browser_autonomous_codex_execution_connector_blocked_reason": blocked_reason,
        }

    ready_local_loop = bool(
        (
            local_loop_status == "local_loop_ready_run_codex_implementation"
            and local_loop_next_action == "run_codex_implementation"
        )
        or (
            local_loop_status == "local_loop_ready_run_codex_fix"
            and local_loop_next_action == "run_codex_fix"
        )
    )
    if not ready_local_loop:
        status = "codex_execution_connector_blocked_missing_local_loop"
        next_action = "manual_review_required"
        blocked_reason = "local_loop_not_ready_for_codex_execution"
        return {
            "project_browser_autonomous_codex_execution_connector_status": status,
            "project_browser_autonomous_codex_execution_connector_next_action": next_action,
            "project_browser_autonomous_codex_execution_connector_enabled": bool(
                connector_enabled
            ),
            "project_browser_autonomous_codex_execution_connector_execute_enabled": bool(
                connector_execute_enabled
            ),
            "project_browser_autonomous_codex_execution_connector_executed": bool(executed),
            "project_browser_autonomous_codex_execution_connector_prompt_kind": prompt_kind,
            "project_browser_autonomous_codex_execution_connector_prompt_path": prompt_path,
            "project_browser_autonomous_codex_execution_connector_prompt_fingerprint": (
                prompt_fingerprint
            ),
            "project_browser_autonomous_codex_execution_connector_route_name": route_name,
            "project_browser_autonomous_codex_execution_connector_output_preview": output_preview,
            "project_browser_autonomous_codex_execution_connector_blocked_reason": blocked_reason,
        }

    if not (codex_gate_status == "codex_execution_gate_ready" and codex_gate_approved):
        status = "codex_execution_connector_blocked_missing_codex_gate"
        next_action = "manual_review_required"
        blocked_reason = "codex_execution_gate_not_ready_or_not_approved"
        return {
            "project_browser_autonomous_codex_execution_connector_status": status,
            "project_browser_autonomous_codex_execution_connector_next_action": next_action,
            "project_browser_autonomous_codex_execution_connector_enabled": bool(
                connector_enabled
            ),
            "project_browser_autonomous_codex_execution_connector_execute_enabled": bool(
                connector_execute_enabled
            ),
            "project_browser_autonomous_codex_execution_connector_executed": bool(executed),
            "project_browser_autonomous_codex_execution_connector_prompt_kind": prompt_kind,
            "project_browser_autonomous_codex_execution_connector_prompt_path": prompt_path,
            "project_browser_autonomous_codex_execution_connector_prompt_fingerprint": (
                prompt_fingerprint
            ),
            "project_browser_autonomous_codex_execution_connector_route_name": route_name,
            "project_browser_autonomous_codex_execution_connector_output_preview": output_preview,
            "project_browser_autonomous_codex_execution_connector_blocked_reason": blocked_reason,
        }

    expected_prompt_kind = (
        "implementation" if local_loop_next_action == "run_codex_implementation" else "fix"
    )
    expected_gate_next_action = (
        "run_existing_codex_implementation_step"
        if expected_prompt_kind == "implementation"
        else "run_existing_codex_fix_step"
    )
    route_available = bool(
        expected_prompt_kind in {"implementation", "fix"}
        and codex_gate_prompt_kind == expected_prompt_kind
        and codex_gate_next_action == expected_gate_next_action
        and codex_gate_prompt_path
        and codex_gate_prompt_path
        in {
            "/tmp/codex-local-runner-decision/generated_next_prompt.txt",
            "/tmp/codex-local-runner-decision/generated_fix_prompt.txt",
        }
    )
    if not route_available:
        status = "codex_execution_connector_blocked_no_existing_route"
        next_action = "manual_review_required"
        blocked_reason = "existing_safe_codex_invocation_route_not_available"
        return {
            "project_browser_autonomous_codex_execution_connector_status": status,
            "project_browser_autonomous_codex_execution_connector_next_action": next_action,
            "project_browser_autonomous_codex_execution_connector_enabled": bool(
                connector_enabled
            ),
            "project_browser_autonomous_codex_execution_connector_execute_enabled": bool(
                connector_execute_enabled
            ),
            "project_browser_autonomous_codex_execution_connector_executed": bool(executed),
            "project_browser_autonomous_codex_execution_connector_prompt_kind": prompt_kind,
            "project_browser_autonomous_codex_execution_connector_prompt_path": prompt_path,
            "project_browser_autonomous_codex_execution_connector_prompt_fingerprint": (
                prompt_fingerprint
            ),
            "project_browser_autonomous_codex_execution_connector_route_name": route_name,
            "project_browser_autonomous_codex_execution_connector_output_preview": output_preview,
            "project_browser_autonomous_codex_execution_connector_blocked_reason": blocked_reason,
        }

    prompt_path = codex_gate_prompt_path
    prompt_text, prompt_read_status = _read_text_bounded(prompt_path, limit_bytes=32768)
    if prompt_read_status != "ready":
        status = "codex_execution_connector_blocked_missing_codex_gate"
        next_action = "manual_review_required"
        blocked_reason = f"prompt_read_status:{prompt_read_status}"
        return {
            "project_browser_autonomous_codex_execution_connector_status": status,
            "project_browser_autonomous_codex_execution_connector_next_action": next_action,
            "project_browser_autonomous_codex_execution_connector_enabled": bool(
                connector_enabled
            ),
            "project_browser_autonomous_codex_execution_connector_execute_enabled": bool(
                connector_execute_enabled
            ),
            "project_browser_autonomous_codex_execution_connector_executed": bool(executed),
            "project_browser_autonomous_codex_execution_connector_prompt_kind": prompt_kind,
            "project_browser_autonomous_codex_execution_connector_prompt_path": prompt_path,
            "project_browser_autonomous_codex_execution_connector_prompt_fingerprint": (
                prompt_fingerprint
            ),
            "project_browser_autonomous_codex_execution_connector_route_name": route_name,
            "project_browser_autonomous_codex_execution_connector_output_preview": output_preview,
            "project_browser_autonomous_codex_execution_connector_blocked_reason": blocked_reason,
        }

    prompt_kind = "next" if expected_prompt_kind == "implementation" else "fix"
    prompt_fingerprint = (
        codex_gate_prompt_fingerprint
        if codex_gate_prompt_fingerprint
        else hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
    )
    if not prompt_fingerprint and local_loop_prompt_fingerprint:
        prompt_fingerprint = local_loop_prompt_fingerprint
    if not prompt_fingerprint and local_loop_prompt:
        prompt_fingerprint = hashlib.sha256(local_loop_prompt.encode("utf-8")).hexdigest()

    prior_dispatched_or_executed_fingerprints = {
        _normalize_text(
            prior_payload.get("project_browser_autonomous_codex_execution_connector_prompt_fingerprint"),
            default="",
        ),
        _normalize_text(
            prior_payload.get("project_browser_autonomous_codex_execution_gate_prompt_fingerprint"),
            default="",
        ),
        _normalize_text(
            prior_payload.get("project_browser_autonomous_local_loop_selected_prompt_fingerprint"),
            default="",
        ),
    }
    prior_dispatched_or_executed_fingerprints.discard("")
    if prompt_fingerprint and prompt_fingerprint in prior_dispatched_or_executed_fingerprints:
        status = "codex_execution_connector_blocked_duplicate_prompt"
        next_action = "manual_review_required"
        blocked_reason = "duplicate_prompt_fingerprint_against_prior_dispatch_or_execution"
        return {
            "project_browser_autonomous_codex_execution_connector_status": status,
            "project_browser_autonomous_codex_execution_connector_next_action": next_action,
            "project_browser_autonomous_codex_execution_connector_enabled": bool(
                connector_enabled
            ),
            "project_browser_autonomous_codex_execution_connector_execute_enabled": bool(
                connector_execute_enabled
            ),
            "project_browser_autonomous_codex_execution_connector_executed": bool(executed),
            "project_browser_autonomous_codex_execution_connector_prompt_kind": prompt_kind,
            "project_browser_autonomous_codex_execution_connector_prompt_path": prompt_path,
            "project_browser_autonomous_codex_execution_connector_prompt_fingerprint": (
                prompt_fingerprint
            ),
            "project_browser_autonomous_codex_execution_connector_route_name": route_name,
            "project_browser_autonomous_codex_execution_connector_output_preview": output_preview,
            "project_browser_autonomous_codex_execution_connector_blocked_reason": blocked_reason,
        }

    unsafe_tokens = (
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
        "unbounded loop",
        "infinite loop",
        "daemon",
        "scheduler",
        "background queue",
        "queue drain",
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
    lower_prompt = prompt_text.lower()
    if any(token in lower_prompt for token in unsafe_tokens):
        status = "codex_execution_connector_blocked_unsafe_prompt"
        next_action = "manual_review_required"
        blocked_reason = "unsafe_prompt_detected"
        return {
            "project_browser_autonomous_codex_execution_connector_status": status,
            "project_browser_autonomous_codex_execution_connector_next_action": next_action,
            "project_browser_autonomous_codex_execution_connector_enabled": bool(
                connector_enabled
            ),
            "project_browser_autonomous_codex_execution_connector_execute_enabled": bool(
                connector_execute_enabled
            ),
            "project_browser_autonomous_codex_execution_connector_executed": bool(executed),
            "project_browser_autonomous_codex_execution_connector_prompt_kind": prompt_kind,
            "project_browser_autonomous_codex_execution_connector_prompt_path": prompt_path,
            "project_browser_autonomous_codex_execution_connector_prompt_fingerprint": (
                prompt_fingerprint
            ),
            "project_browser_autonomous_codex_execution_connector_route_name": route_name,
            "project_browser_autonomous_codex_execution_connector_output_preview": output_preview,
            "project_browser_autonomous_codex_execution_connector_blocked_reason": blocked_reason,
        }

    route_name = "existing_codex_invocation_execution_state"
    invocation_state = _build_project_browser_autonomous_codex_invocation_execution_state(
        repository_path=str(execution_repo_path),
        readiness_status="ready_to_invoke_codex",
        invocation_allowed=True,
        selected_prompt_kind=prompt_kind,
        selected_prompt_path=prompt_path,
        selected_prompt_source="project_browser_autonomous_codex_execution_connector",
        selected_prompt_ready=True,
        selected_prompt_path_is_exact=True,
        selected_prompt_path_exists=True,
        selected_prompt_path_is_symlink=False,
        selected_prompt_file_non_empty=True,
        selected_prompt_file_too_large=False,
        rollback_required=False,
        human_review_required=False,
        insufficient_truth=False,
        max_invocations=1,
        prior_invocation_attempted=bool(
            prior_payload.get(
                "project_browser_autonomous_codex_invocation_execution_invocation_attempted",
                False,
            )
        ),
        prior_invocation_completed=bool(
            prior_payload.get(
                "project_browser_autonomous_codex_invocation_execution_invocation_completed",
                False,
            )
        ),
    )
    invocation_status = _normalize_text(
        invocation_state.get("project_browser_autonomous_codex_invocation_execution_status"),
        default="",
    )
    invocation_completed = bool(
        invocation_state.get("project_browser_autonomous_codex_invocation_execution_invocation_completed", False)
    )
    invocation_exit_code = _as_int(
        invocation_state.get("project_browser_autonomous_codex_invocation_execution_invocation_exit_code"),
        default=-1,
    )
    stdout_excerpt = _normalize_text(
        invocation_state.get("project_browser_autonomous_codex_invocation_execution_invocation_stdout_excerpt"),
        default="",
    )
    stderr_excerpt = _normalize_text(
        invocation_state.get("project_browser_autonomous_codex_invocation_execution_invocation_stderr_excerpt"),
        default="",
    )
    invocation_blocker_class = _normalize_text(
        invocation_state.get(
            "project_browser_autonomous_codex_invocation_execution_blocker_class"
        ),
        default="none",
    )
    invocation_blocked_reason = _normalize_text(
        invocation_state.get(
            "project_browser_autonomous_codex_invocation_execution_blocked_reason"
        ),
        default="",
    )
    invocation_retry_likely_repeats = bool(
        invocation_state.get(
            "project_browser_autonomous_codex_invocation_execution_retry_likely_repeats",
            False,
        )
    )
    output_preview = _normalize_text(
        "\n".join(
            _serialize_required_signals(
                [
                    f"execution_status={invocation_status}",
                    f"exit_code={invocation_exit_code}",
                    f"stdout={stdout_excerpt[:300]}" if stdout_excerpt else "",
                    f"stderr={stderr_excerpt[:300]}" if stderr_excerpt else "",
                ]
            )
        ),
        default="",
    )

    if invocation_status == "codex_invocation_completed" and invocation_completed and invocation_exit_code == 0:
        status = "codex_execution_connector_executed"
        next_action = "run_codex_capture_gate"
        executed = True
        blocked_reason = "none"
    else:
        status = "codex_execution_connector_blocked_execution_failed"
        next_action = "manual_review_required"
        blocked_reason = (
            invocation_blocked_reason
            if invocation_blocked_reason and invocation_blocked_reason != "none"
            else f"invocation_status:{invocation_status or 'unknown'}"
        )

    return {
        "project_browser_autonomous_codex_execution_connector_status": status,
        "project_browser_autonomous_codex_execution_connector_next_action": next_action,
        "project_browser_autonomous_codex_execution_connector_enabled": bool(connector_enabled),
        "project_browser_autonomous_codex_execution_connector_execute_enabled": bool(
            connector_execute_enabled
        ),
        "project_browser_autonomous_codex_execution_connector_executed": bool(executed),
        "project_browser_autonomous_codex_execution_connector_prompt_kind": prompt_kind,
        "project_browser_autonomous_codex_execution_connector_prompt_path": prompt_path,
        "project_browser_autonomous_codex_execution_connector_prompt_fingerprint": (
            prompt_fingerprint
        ),
        "project_browser_autonomous_codex_execution_connector_route_name": route_name,
        "project_browser_autonomous_codex_execution_connector_output_preview": output_preview[:800],
        "project_browser_autonomous_codex_execution_connector_blocked_reason": blocked_reason,
        "project_browser_autonomous_codex_execution_connector_invocation_blocker_class": (
            invocation_blocker_class
        ),
        "project_browser_autonomous_codex_execution_connector_invocation_blocked_reason": (
            invocation_blocked_reason
        ),
        "project_browser_autonomous_codex_execution_connector_invocation_retry_likely_repeats": bool(
            invocation_retry_likely_repeats
        ),
    }

def _build_project_browser_autonomous_codex_live_network_state(
    *,
    codex_execution_connector_state: Mapping[str, Any] | None,
    codex_invocation_execution_state: Mapping[str, Any] | None,
    codex_invocation_result_state: Mapping[str, Any] | None,
    approved_restart_payload: Mapping[str, Any] | None = None,
    prior_approved_restart_execution_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    connector = (
        dict(codex_execution_connector_state)
        if isinstance(codex_execution_connector_state, Mapping)
        else {}
    )
    invocation_execution = (
        dict(codex_invocation_execution_state)
        if isinstance(codex_invocation_execution_state, Mapping)
        else {}
    )
    invocation_result = (
        dict(codex_invocation_result_state)
        if isinstance(codex_invocation_result_state, Mapping)
        else {}
    )
    approved_restart = (
        dict(approved_restart_payload)
        if isinstance(approved_restart_payload, Mapping)
        else {}
    )
    prior_payload = (
        dict(prior_approved_restart_execution_payload)
        if isinstance(prior_approved_restart_execution_payload, Mapping)
        else {}
    )

    def _read_persisted_value(key: str) -> Any:
        if key in approved_restart and approved_restart.get(key) is not None:
            return approved_restart.get(key)
        if key in prior_payload:
            return prior_payload.get(key)
        return None

    persisted_blocker_class = _normalize_text(
        _read_persisted_value(
            "project_browser_autonomous_codex_live_network_blocker_class"
        ),
        default="",
    )
    persisted_blocked_reason = _normalize_text(
        _read_persisted_value(
            "project_browser_autonomous_codex_live_network_blocked_reason"
        ),
        default="",
    )
    persisted_retry_allowed = _read_persisted_value(
        "project_browser_autonomous_codex_live_retry_allowed"
    )
    persisted_next_action = _normalize_text(
        _read_persisted_value("project_browser_autonomous_codex_live_next_action"),
        default="",
    )
    persisted_retry_likely_repeats = bool(
        _read_persisted_value(
            "project_browser_autonomous_codex_live_retry_likely_repeats"
        )
    )
    persisted_non_retryable_network_denied = bool(
        persisted_blocker_class == "network_denied"
        and persisted_blocked_reason == "codex_invocation_blocked_network_denied"
        and persisted_next_action == "stop_live_network_unavailable"
        and not bool(persisted_retry_allowed)
    )

    if persisted_non_retryable_network_denied:
        return {
            "project_browser_autonomous_codex_live_network_status": "blocked",
            "project_browser_autonomous_codex_live_network_blocker_class": (
                "network_denied"
            ),
            "project_browser_autonomous_codex_live_network_blocked_reason": (
                "codex_invocation_blocked_network_denied"
            ),
            "project_browser_autonomous_codex_live_retry_allowed": False,
            "project_browser_autonomous_codex_live_retry_likely_repeats": True,
            "project_browser_autonomous_codex_live_next_action": (
                "stop_live_network_unavailable"
            ),
            "project_browser_autonomous_codex_live_manual_action_required": True,
        }

    blocker_class = _normalize_text(
        connector.get(
            "project_browser_autonomous_codex_execution_connector_invocation_blocker_class"
        ),
        default=_normalize_text(
            invocation_result.get(
                "project_browser_autonomous_codex_invocation_result_blocker_class"
            ),
            default=_normalize_text(
                invocation_execution.get(
                    "project_browser_autonomous_codex_invocation_execution_blocker_class"
                ),
                default="none",
            ),
        ),
    )
    blocked_reason = _normalize_text(
        connector.get(
            "project_browser_autonomous_codex_execution_connector_invocation_blocked_reason"
        ),
        default=_normalize_text(
            invocation_result.get(
                "project_browser_autonomous_codex_invocation_result_blocked_reason"
            ),
            default=_normalize_text(
                invocation_execution.get(
                    "project_browser_autonomous_codex_invocation_execution_blocked_reason"
                ),
                default="none",
            ),
        ),
    )
    retry_likely_repeats = bool(
        connector.get(
            "project_browser_autonomous_codex_execution_connector_invocation_retry_likely_repeats",
            invocation_result.get(
                "project_browser_autonomous_codex_invocation_result_retry_likely_repeats",
                invocation_execution.get(
                    "project_browser_autonomous_codex_invocation_execution_retry_likely_repeats",
                    False,
                ),
            ),
        )
    )

    status = "available"
    next_action = "continue_codex_flow"
    retry_allowed = True
    manual_action_required = False

    if (
        blocker_class == "network_denied"
        or blocked_reason == "codex_invocation_blocked_network_denied"
    ):
        status = "blocked"
        blocker_class = "network_denied"
        blocked_reason = "codex_invocation_blocked_network_denied"
        retry_allowed = False
        retry_likely_repeats = True
        next_action = "stop_live_network_unavailable"
        manual_action_required = True
    elif blocker_class and blocker_class != "none":
        status = "blocked"
        retry_allowed = not retry_likely_repeats
        next_action = "manual_review_required"
        manual_action_required = True
    elif blocked_reason and blocked_reason != "none":
        status = "blocked"
        blocker_class = "unknown"
        retry_allowed = not retry_likely_repeats
        next_action = "manual_review_required"
        manual_action_required = True

    return {
        "project_browser_autonomous_codex_live_network_status": status,
        "project_browser_autonomous_codex_live_network_blocker_class": blocker_class,
        "project_browser_autonomous_codex_live_network_blocked_reason": blocked_reason,
        "project_browser_autonomous_codex_live_retry_allowed": bool(retry_allowed),
        "project_browser_autonomous_codex_live_retry_likely_repeats": bool(
            retry_likely_repeats
        ),
        "project_browser_autonomous_codex_live_next_action": next_action,
        "project_browser_autonomous_codex_live_manual_action_required": bool(
            manual_action_required
        ),
    }

def _build_project_browser_autonomous_codex_live_continuation_guard_state(
    *,
    codex_live_network_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    live_network = (
        dict(codex_live_network_state)
        if isinstance(codex_live_network_state, Mapping)
        else {}
    )
    live_status = _normalize_text(
        live_network.get("project_browser_autonomous_codex_live_network_status"),
        default="insufficient_truth",
    )
    live_next_action = _normalize_text(
        live_network.get("project_browser_autonomous_codex_live_next_action"),
        default="insufficient_truth",
    )
    live_retry_allowed = bool(
        live_network.get("project_browser_autonomous_codex_live_retry_allowed", True)
    )

    guard_status = "allow"
    guard_reason = "none"
    guard_retry_allowed = bool(live_retry_allowed)
    guard_next_action = "continue_codex_flow"
    if (
        live_status == "blocked"
        and live_next_action == "stop_live_network_unavailable"
        and not live_retry_allowed
    ):
        guard_status = "blocked"
        guard_reason = "codex_live_network_unavailable"
        guard_retry_allowed = False
        guard_next_action = "manual_network_setup_required"

    return {
        "project_browser_autonomous_codex_live_continuation_guard_status": guard_status,
        "project_browser_autonomous_codex_live_continuation_guard_reason": guard_reason,
        "project_browser_autonomous_codex_live_continuation_retry_allowed": bool(
            guard_retry_allowed
        ),
        "project_browser_autonomous_codex_live_continuation_next_action": (
            guard_next_action
        ),
    }

def _build_project_browser_autonomous_explicit_codex_result_injection_state(
    *,
    dry_run: bool,
    explicit_codex_result_present: bool,
    codex_handoff_status: str,
    current_mvp_status: str,
    prompt258_explicit_real_input_injection_enabled: bool,
    explicit_real_input_path_ready_for_codex_handoff: bool,
    explicit_result_scenario_mode_selected: str,
) -> dict[str, Any]:
    normalized_codex_handoff_status = _normalize_text(codex_handoff_status, default="")
    normalized_current_mvp_status = _normalize_text(current_mvp_status, default="")

    codex_handoff_or_waiting_result = bool(
        normalized_codex_handoff_status == "codex_handoff_ready"
        or normalized_current_mvp_status == "waiting_for_codex_result"
    )
    explicit_real_input_route_ready = bool(
        prompt258_explicit_real_input_injection_enabled
        or explicit_real_input_path_ready_for_codex_handoff
    )
    enabled = bool(
        dry_run
        and codex_handoff_or_waiting_result
        and not explicit_codex_result_present
        and explicit_real_input_route_ready
    )

    review_mode = ""
    normalized_explicit_result_mode = _normalize_text(
        explicit_result_scenario_mode_selected,
        default="explicit_result_approve_project_complete",
    )
    result_summary = ""
    validation_passed = False
    if enabled:
        status = "explicit_codex_result_injection_ready"
        enabled_reason = "normal_dry_run_after_explicit_real_input_handoff"
        review_mode = "approve"
        next_action = "apply_explicit_codex_result"
        result_summary = (
            "Explicit Codex result injection: implementation completed for explicit real-input MVP verification."
        )
        validation_passed = True
        if normalized_explicit_result_mode == "explicit_result_fail_fix_route":
            review_mode = "fix"
            result_summary = (
                "Explicit Codex result injection: synthetic explicit validation failure for real-input MVP fix-route verification."
            )
            validation_passed = False
        elif normalized_explicit_result_mode == "explicit_result_multi_pr_approve_next_pr":
            result_summary = (
                "Explicit Codex result injection: implementation completed for explicit real-input multi-PR continuation verification."
            )
    elif explicit_codex_result_present:
        status = "explicit_codex_result_injection_skipped_explicit_result_present"
        enabled_reason = "explicit_codex_result_present"
        next_action = "use_existing_explicit_codex_result"
    else:
        status = "explicit_codex_result_injection_not_applicable"
        enabled_reason = "explicit_codex_result_injection_not_required"
        next_action = "await_codex_result"

    return {
        "project_browser_autonomous_explicit_codex_result_injection_status": status,
        "project_browser_autonomous_explicit_codex_result_injection_source": (
            "prompt259_explicit_codex_result_injection"
        ),
        "project_browser_autonomous_explicit_codex_result_injection_enabled": bool(enabled),
        "project_browser_autonomous_explicit_codex_result_injection_enabled_reason": (
            enabled_reason
        ),
        "project_browser_autonomous_explicit_codex_result_injection_result_summary": (
            result_summary
        ),
        "project_browser_autonomous_explicit_codex_result_injection_validation_passed": bool(
            validation_passed
        ),
        "project_browser_autonomous_explicit_codex_result_injection_changed_files": (
            ["automation/orchestration/planned_execution_runner.py"] if enabled else []
        ),
        "project_browser_autonomous_explicit_codex_result_injection_review_mode": (
            review_mode
        ),
        "project_browser_autonomous_explicit_codex_result_injection_ready": bool(enabled),
        "project_browser_autonomous_explicit_codex_result_injection_next_action": (
            next_action
        ),
    }

def _build_project_browser_autonomous_explicit_codex_result_review_validation_state(
    *,
    injection_state: Mapping[str, Any],
    codex_result_ingestion_state: Mapping[str, Any],
    review_fix_decision_state: Mapping[str, Any],
    commit_next_pr_metadata_state: Mapping[str, Any],
    dev_loop_completion_state: Mapping[str, Any],
    mvp_state: Mapping[str, Any],
) -> dict[str, Any]:
    injection_enabled = bool(
        injection_state.get(
            "project_browser_autonomous_explicit_codex_result_injection_enabled",
            False,
        )
    )
    result_detected = bool(
        codex_result_ingestion_state.get(
            "project_browser_autonomous_codex_result_ingestion_result_detected",
            False,
        )
    )
    validation_passed = bool(
        codex_result_ingestion_state.get(
            "project_browser_autonomous_codex_result_ingestion_validation_passed",
            False,
        )
    )
    review_decision = _normalize_text(
        review_fix_decision_state.get(
            "project_browser_autonomous_review_fix_decision_review_decision"
        ),
        default="waiting",
    )
    ingestion_status = _normalize_text(
        codex_result_ingestion_state.get(
            "project_browser_autonomous_codex_result_ingestion_status"
        ),
        default="",
    )
    review_fix_status = _normalize_text(
        review_fix_decision_state.get(
            "project_browser_autonomous_review_fix_decision_status"
        ),
        default="",
    )
    commit_metadata_status = _normalize_text(
        commit_next_pr_metadata_state.get(
            "project_browser_autonomous_commit_next_pr_metadata_status"
        ),
        default="",
    )
    completion_status = _normalize_text(
        dev_loop_completion_state.get(
            "project_browser_autonomous_dev_loop_completion_status"
        ),
        default="",
    )
    observed_mvp_status = _normalize_text(
        mvp_state.get("project_browser_autonomous_dev_loop_mvp_status"),
        default="",
    )
    observed_mvp_next_action = _normalize_text(
        mvp_state.get("project_browser_autonomous_dev_loop_mvp_next_action"),
        default="",
    )

    passed = bool(
        injection_enabled
        and result_detected
        and validation_passed
        and review_decision == "approve"
        and ingestion_status == "codex_result_ingestion_ready"
        and review_fix_status == "review_fix_decision_approved"
        and commit_metadata_status == "commit_next_pr_metadata_ready"
        and completion_status == "dev_loop_completion_project_complete"
        and observed_mvp_status == "project_complete"
        and observed_mvp_next_action == "complete_project"
    )
    if passed:
        status = "explicit_codex_result_review_validation_passed"
        next_action = "complete_project"
    elif injection_enabled:
        status = "explicit_codex_result_review_validation_failed"
        next_action = "inspect_explicit_codex_result_review_validation_mismatch"
    else:
        status = "explicit_codex_result_review_validation_not_applicable"
        next_action = "use_existing_explicit_codex_result"

    return {
        "project_browser_autonomous_explicit_codex_result_review_validation_status": (
            status
        ),
        "project_browser_autonomous_explicit_codex_result_review_validation_source": (
            "prompt259_explicit_codex_result_review_validation"
        ),
        "project_browser_autonomous_explicit_codex_result_review_validation_injection_enabled": bool(
            injection_enabled
        ),
        "project_browser_autonomous_explicit_codex_result_review_validation_result_detected": bool(
            result_detected
        ),
        "project_browser_autonomous_explicit_codex_result_review_validation_validation_passed": bool(
            validation_passed if result_detected else False
        ),
        "project_browser_autonomous_explicit_codex_result_review_validation_review_decision": (
            review_decision
        ),
        "project_browser_autonomous_explicit_codex_result_review_validation_ingestion_status": (
            ingestion_status
        ),
        "project_browser_autonomous_explicit_codex_result_review_validation_review_fix_status": (
            review_fix_status
        ),
        "project_browser_autonomous_explicit_codex_result_review_validation_commit_metadata_status": (
            commit_metadata_status
        ),
        "project_browser_autonomous_explicit_codex_result_review_validation_completion_status": (
            completion_status
        ),
        "project_browser_autonomous_explicit_codex_result_review_validation_observed_mvp_status": (
            observed_mvp_status
        ),
        "project_browser_autonomous_explicit_codex_result_review_validation_observed_mvp_next_action": (
            observed_mvp_next_action
        ),
        "project_browser_autonomous_explicit_codex_result_review_validation_passed": bool(
            passed
        ),
        "project_browser_autonomous_explicit_codex_result_review_validation_next_action": (
            next_action
        ),
    }

def _build_project_browser_autonomous_codex_invocation_readiness_state(
    *,
    prompt_selection_status: str,
    selected_prompt_kind: str,
    selected_prompt_path: str,
    selected_prompt_source: str,
    selected_prompt_ready: bool,
    selected_prompt_body_available: bool,
    rollback_required: bool,
    human_review_required: bool,
    insufficient_truth: bool,
) -> dict[str, Any]:
    allowed_statuses = {
        "ready_to_invoke_codex",
        "blocked_no_selected_prompt",
        "blocked_invalid_prompt_kind",
        "blocked_selected_prompt_not_ready",
        "blocked_prompt_path_missing",
        "blocked_prompt_path_unexpected",
        "blocked_prompt_path_symlink",
        "blocked_prompt_empty",
        "blocked_prompt_too_large",
        "blocked_rollback_required",
        "blocked_human_review_required",
        "blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "invoke_codex_later",
        "wait_for_prompt_selection",
        "wait_for_prompt_generation",
        "wait_for_more_truth",
        "manual_review_required",
        "rollback_required",
        "manual_codex_invocation_required",
        "insufficient_truth",
    }
    allowed_paths = {
        "/tmp/codex-local-runner-decision/generated_fix_prompt.txt",
        "/tmp/codex-local-runner-decision/generated_next_prompt.txt",
    }
    runtime_posture = [
        "codex_invocation_readiness_only",
        "metadata_only_gate",
        "no_codex_invocation",
        "no_external_model_invocation",
        "no_prompt_generation",
        "no_patch_apply",
        "no_git_mutation",
        "no_autonomous_loop",
    ]
    max_prompt_size_bytes = 20000
    max_invocations = 1

    normalized_selection_status = _normalize_text(
        prompt_selection_status,
        default="insufficient_truth",
    )
    normalized_prompt_kind = _normalize_text(selected_prompt_kind, default="none")
    normalized_prompt_path = _normalize_text(selected_prompt_path, default="")
    normalized_prompt_source = _normalize_text(selected_prompt_source, default="")

    selected_prompt_path_is_exact = normalized_prompt_path in allowed_paths
    path_obj = Path(normalized_prompt_path) if normalized_prompt_path else None
    selected_prompt_path_exists = bool(path_obj and path_obj.exists())
    selected_prompt_path_is_symlink = bool(path_obj and path_obj.is_symlink())

    selected_prompt_file_size_bytes = 0
    if selected_prompt_path_exists and path_obj and not selected_prompt_path_is_symlink:
        try:
            selected_prompt_file_size_bytes = max(0, int(path_obj.stat().st_size))
        except OSError:
            selected_prompt_file_size_bytes = 0

    selected_prompt_file_non_empty = selected_prompt_file_size_bytes > 0
    selected_prompt_file_too_large = selected_prompt_file_size_bytes > max_prompt_size_bytes

    status = "insufficient_truth"
    source_status = "insufficient_truth"
    block_reason = "insufficient_truth"
    invocation_allowed = False
    invocation_blocked = True
    invocation_attempted = False
    invocation_completed = False
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
        missing_inputs.append("codex_invocation_readiness_truth")
    elif normalized_selection_status not in {"selected_fix_prompt", "selected_next_prompt"}:
        status = "blocked_no_selected_prompt"
        source_status = "prompt_selection_not_ready"
        block_reason = "no_selected_prompt"
        next_action = (
            "wait_for_prompt_generation"
            if normalized_selection_status
            in {
                "blocked_handoff_write_failed",
                "blocked_prompt_path_missing",
                "blocked_prompt_path_unexpected",
                "blocked_prompt_path_symlink",
                "blocked_prompt_body_missing",
                "blocked_no_ready_prompt",
            }
            else "wait_for_prompt_selection"
        )
    elif normalized_prompt_kind not in {"fix", "next"}:
        status = "blocked_invalid_prompt_kind"
        source_status = "invalid_selected_prompt_kind"
        block_reason = "invalid_selected_prompt_kind"
        next_action = "wait_for_prompt_selection"
    elif not selected_prompt_ready:
        status = "blocked_selected_prompt_not_ready"
        source_status = "selected_prompt_not_ready"
        block_reason = "selected_prompt_not_ready"
        next_action = "wait_for_prompt_generation"
    elif not selected_prompt_path_is_exact:
        status = "blocked_prompt_path_unexpected"
        source_status = "selected_prompt_path_not_allowed"
        block_reason = "selected_prompt_path_unexpected"
        next_action = "manual_codex_invocation_required"
    elif selected_prompt_path_is_symlink:
        status = "blocked_prompt_path_symlink"
        source_status = "selected_prompt_path_symlink"
        block_reason = "selected_prompt_path_symlink"
        next_action = "manual_codex_invocation_required"
    elif not selected_prompt_path_exists:
        status = "blocked_prompt_path_missing"
        source_status = "selected_prompt_path_missing"
        block_reason = "selected_prompt_path_missing"
        next_action = "wait_for_prompt_generation"
    elif not selected_prompt_file_non_empty:
        status = "blocked_prompt_empty"
        source_status = "selected_prompt_file_empty"
        block_reason = "selected_prompt_empty"
        next_action = "wait_for_prompt_generation"
    elif selected_prompt_file_too_large:
        status = "blocked_prompt_too_large"
        source_status = "selected_prompt_file_too_large"
        block_reason = "selected_prompt_too_large"
        next_action = "manual_codex_invocation_required"
    elif not selected_prompt_body_available:
        status = "blocked_selected_prompt_not_ready"
        source_status = "selected_prompt_body_unavailable"
        block_reason = "selected_prompt_body_unavailable"
        next_action = "wait_for_prompt_generation"
    else:
        status = "ready_to_invoke_codex"
        source_status = "selected_prompt_ready_for_bounded_invocation"
        block_reason = "none"
        invocation_allowed = True
        invocation_blocked = False
        next_action = "invoke_codex_later"

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"

    return {
        "project_browser_autonomous_codex_invocation_readiness_status": status,
        "project_browser_autonomous_codex_invocation_readiness_source_status": (
            source_status
        ),
        "project_browser_autonomous_codex_invocation_readiness_block_reason": (
            block_reason
        ),
        "project_browser_autonomous_codex_invocation_readiness_selected_prompt_kind": (
            normalized_prompt_kind
        ),
        "project_browser_autonomous_codex_invocation_readiness_selected_prompt_path": (
            normalized_prompt_path
        ),
        "project_browser_autonomous_codex_invocation_readiness_selected_prompt_source": (
            normalized_prompt_source
        ),
        "project_browser_autonomous_codex_invocation_readiness_selected_prompt_ready": bool(
            selected_prompt_ready
        ),
        "project_browser_autonomous_codex_invocation_readiness_selected_prompt_path_is_exact": bool(
            selected_prompt_path_is_exact
        ),
        "project_browser_autonomous_codex_invocation_readiness_selected_prompt_path_exists": bool(
            selected_prompt_path_exists
        ),
        "project_browser_autonomous_codex_invocation_readiness_selected_prompt_path_is_symlink": bool(
            selected_prompt_path_is_symlink
        ),
        "project_browser_autonomous_codex_invocation_readiness_selected_prompt_file_size_bytes": int(
            selected_prompt_file_size_bytes
        ),
        "project_browser_autonomous_codex_invocation_readiness_selected_prompt_file_non_empty": bool(
            selected_prompt_file_non_empty
        ),
        "project_browser_autonomous_codex_invocation_readiness_selected_prompt_file_too_large": bool(
            selected_prompt_file_too_large
        ),
        "project_browser_autonomous_codex_invocation_readiness_selected_prompt_body_available": bool(
            selected_prompt_body_available
        ),
        "project_browser_autonomous_codex_invocation_readiness_invocation_allowed": bool(
            invocation_allowed
        ),
        "project_browser_autonomous_codex_invocation_readiness_invocation_blocked": bool(
            invocation_blocked
        ),
        "project_browser_autonomous_codex_invocation_readiness_invocation_attempted": bool(
            invocation_attempted
        ),
        "project_browser_autonomous_codex_invocation_readiness_invocation_completed": bool(
            invocation_completed
        ),
        "project_browser_autonomous_codex_invocation_readiness_max_invocations": int(
            max_invocations
        ),
        "project_browser_autonomous_codex_invocation_readiness_rollback_required": bool(
            rollback_required
        ),
        "project_browser_autonomous_codex_invocation_readiness_human_review_required": bool(
            human_review_required
        ),
        "project_browser_autonomous_codex_invocation_readiness_insufficient_truth": bool(
            insufficient_truth
        ),
        "project_browser_autonomous_codex_invocation_readiness_next_action": next_action,
        "project_browser_autonomous_codex_invocation_readiness_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_codex_invocation_readiness_missing_inputs": (
            _serialize_required_signals(missing_inputs)
        ),
    }

def _build_project_browser_autonomous_codex_invocation_execution_state(
    *,
    repository_path: str,
    readiness_status: str,
    invocation_allowed: bool,
    selected_prompt_kind: str,
    selected_prompt_path: str,
    selected_prompt_source: str,
    selected_prompt_ready: bool,
    selected_prompt_path_is_exact: bool,
    selected_prompt_path_exists: bool,
    selected_prompt_path_is_symlink: bool,
    selected_prompt_file_non_empty: bool,
    selected_prompt_file_too_large: bool,
    rollback_required: bool,
    human_review_required: bool,
    insufficient_truth: bool,
    max_invocations: int,
    prior_invocation_attempted: bool,
    prior_invocation_completed: bool,
) -> dict[str, Any]:
    allowed_execution_statuses = {
        "codex_invocation_completed",
        "blocked_not_ready",
        "blocked_invocation_not_allowed",
        "blocked_missing_prompt",
        "blocked_prompt_path_unexpected",
        "blocked_prompt_path_symlink",
        "blocked_prompt_empty",
        "blocked_prompt_too_large",
        "blocked_rollback_required",
        "blocked_human_review_required",
        "blocked_insufficient_truth",
        "blocked_codex_command_unavailable",
        "blocked_timeout",
        "failed_execution_error",
        "insufficient_truth",
    }
    allowed_result_statuses = {
        "completed_success",
        "completed_failure",
        "completed_timeout",
        "blocked",
        "failed_execution_error",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "invoke_codex_later",
        "wait_for_prompt_selection",
        "wait_for_prompt_generation",
        "wait_for_more_truth",
        "manual_review_required",
        "rollback_required",
        "manual_codex_invocation_required",
        "insufficient_truth",
    }
    runtime_posture = [
        "one_bounded_codex_invocation",
        "at_most_one_invocation",
        "no_retry",
        "no_loop",
        "no_patch_candidate_classification",
        "no_patch_generation",
        "no_patch_apply",
        "no_git_mutation",
        "stdout_stderr_compact_excerpts_only",
    ]
    allowed_paths = {
        "/tmp/codex-local-runner-decision/generated_fix_prompt.txt",
        "/tmp/codex-local-runner-decision/generated_next_prompt.txt",
    }
    stdout_path = "/tmp/codex-local-runner-decision/codex_invocation_stdout.txt"
    stderr_path = "/tmp/codex-local-runner-decision/codex_invocation_stderr.txt"
    result_path = "/tmp/codex-local-runner-decision/codex_invocation_result.json"
    timeout_seconds = 120.0
    excerpt_limit = 800

    normalized_repository_path = _normalize_text(repository_path, default="")
    normalized_readiness_status = _normalize_text(readiness_status, default="insufficient_truth")
    normalized_prompt_kind = _normalize_text(selected_prompt_kind, default="none")
    normalized_prompt_path = _normalize_text(selected_prompt_path, default="")
    normalized_prompt_source = _normalize_text(selected_prompt_source, default="")
    explicit_one_shot_live_probe_prompt_path = (
        "/tmp/codex-local-runner-decision/generated_next_prompt.txt"
    )
    explicit_one_shot_live_probe_selected = bool(
        normalized_prompt_source == "explicit_one_shot_live_probe"
        and normalized_prompt_kind == "next"
        and normalized_prompt_path == explicit_one_shot_live_probe_prompt_path
    )
    normalized_max_invocations = (
        1 if _as_non_negative_int(max_invocations, default=1) != 1 else 1
    )

    invocation_command: list[str] = []
    invocation_environment_overrides: dict[str, str] = {}
    invocation_attempted = bool(prior_invocation_attempted)
    invocation_completed = bool(prior_invocation_completed)
    invocation_exit_code = -1
    invocation_timeout = False
    invocation_stdout_excerpt = ""
    invocation_stderr_excerpt = ""
    status = "insufficient_truth"
    source_status = "insufficient_truth"
    block_reason = "insufficient_truth"
    next_action = "insufficient_truth"
    missing_inputs: list[str] = []

    result_status = "insufficient_truth"
    result_source_status = "insufficient_truth"
    result_kind = "none"
    result_completed = False
    result_failed = False
    result_timeout = False
    result_next_action = "insufficient_truth"
    blocker_class = "none"
    blocked_reason_classified = "none"
    retry_likely_repeats = False
    stderr_summary = ""

    def _write_text_file(path_text: str, content: str) -> None:
        path_obj = Path(path_text)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        path_obj.write_text(content, encoding="utf-8")

    def _write_result_payload() -> None:
        payload = {
            "status": result_status,
            "source_status": result_source_status,
            "result_kind": result_kind,
            "result_path": result_path,
            "stdout_path": stdout_path,
            "stderr_path": stderr_path,
            "exit_code": invocation_exit_code,
            "completed": bool(result_completed),
            "failed": bool(result_failed),
            "timeout": bool(result_timeout),
            "next_action": result_next_action,
            "missing_inputs": _serialize_required_signals(missing_inputs),
            "blocker_class": blocker_class,
            "blocked_reason": blocked_reason_classified,
            "retry_likely_repeats": bool(retry_likely_repeats),
            "stderr_summary": _normalize_text(stderr_summary, default=""),
        }
        try:
            result_obj = Path(result_path)
            result_obj.parent.mkdir(parents=True, exist_ok=True)
            result_obj.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass

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
        missing_inputs.append("codex_invocation_readiness_truth")
    elif normalized_readiness_status != "ready_to_invoke_codex":
        status = "blocked_not_ready"
        source_status = "readiness_not_ready"
        block_reason = f"readiness_status:{normalized_readiness_status or 'unknown'}"
        next_action = "wait_for_prompt_selection"
    elif not invocation_allowed:
        status = "blocked_invocation_not_allowed"
        source_status = "readiness_invocation_not_allowed"
        block_reason = "invocation_allowed_false"
        next_action = "wait_for_prompt_generation"
    elif invocation_attempted or invocation_completed:
        status = "blocked_invocation_not_allowed"
        source_status = "max_invocations_reached"
        block_reason = "prior_invocation_already_attempted"
        next_action = "wait_for_more_truth"
    elif normalized_max_invocations != 1:
        status = "blocked_invocation_not_allowed"
        source_status = "max_invocations_invalid"
        block_reason = "max_invocations_not_one"
        next_action = "wait_for_more_truth"
    elif normalized_prompt_kind not in {"fix", "next"}:
        status = "blocked_not_ready"
        source_status = "selected_prompt_kind_invalid"
        block_reason = "selected_prompt_kind_invalid"
        next_action = "wait_for_prompt_selection"
    elif not selected_prompt_ready:
        status = "blocked_not_ready"
        source_status = "selected_prompt_not_ready"
        block_reason = "selected_prompt_not_ready"
        next_action = "wait_for_prompt_generation"
    elif normalized_prompt_path not in allowed_paths or not selected_prompt_path_is_exact:
        status = "blocked_prompt_path_unexpected"
        source_status = "selected_prompt_path_unexpected"
        block_reason = "selected_prompt_path_unexpected"
        next_action = "manual_codex_invocation_required"
    elif selected_prompt_path_is_symlink:
        status = "blocked_prompt_path_symlink"
        source_status = "selected_prompt_path_symlink"
        block_reason = "selected_prompt_path_symlink"
        next_action = "manual_codex_invocation_required"
    elif not selected_prompt_path_exists:
        status = "blocked_missing_prompt"
        source_status = "selected_prompt_path_missing"
        block_reason = "selected_prompt_path_missing"
        next_action = "wait_for_prompt_generation"
    elif not selected_prompt_file_non_empty:
        status = "blocked_prompt_empty"
        source_status = "selected_prompt_empty"
        block_reason = "selected_prompt_empty"
        next_action = "wait_for_prompt_generation"
    elif selected_prompt_file_too_large:
        status = "blocked_prompt_too_large"
        source_status = "selected_prompt_too_large"
        block_reason = "selected_prompt_too_large"
        next_action = "manual_codex_invocation_required"
    else:
        codex_command = shutil.which("codex")
        if not codex_command:
            status = "blocked_codex_command_unavailable"
            source_status = "codex_command_unavailable"
            block_reason = "codex_command_unavailable"
            next_action = "manual_codex_invocation_required"
        else:
            invocation_environment = os.environ.copy()
            if explicit_one_shot_live_probe_selected:
                runtime_posture.append(
                    "explicit_one_shot_live_probe_inherit_user_codex_environment"
                )
                invocation_environment_overrides = {}
            else:
                runtime_root = Path("/tmp/codex-local-runner-decision/codex_runtime")
                runtime_home = runtime_root / "home"
                runtime_tmp = runtime_root / "tmp"
                runtime_config = runtime_root / "config"
                runtime_cache = runtime_root / "cache"
                runtime_state = runtime_root / "state"
                runtime_data = runtime_root / "data"
                runtime_codex_home = runtime_root / "codex_home"
                runtime_dirs = (
                    runtime_root,
                    runtime_home,
                    runtime_tmp,
                    runtime_config,
                    runtime_cache,
                    runtime_state,
                    runtime_data,
                    runtime_codex_home,
                )
                try:
                    for runtime_dir in runtime_dirs:
                        runtime_dir.mkdir(parents=True, exist_ok=True)
                except OSError as exc:
                    status = "failed_execution_error"
                    source_status = "runtime_environment_prepare_failed"
                    block_reason = f"runtime_environment_prepare_failed:{type(exc).__name__}"
                    next_action = "manual_codex_invocation_required"
                    result_status = "failed_execution_error"
                    result_source_status = source_status
                    result_kind = "execution_error"
                    result_failed = True
                    result_timeout = False
                    result_next_action = "manual_codex_invocation_required"
                    missing_inputs.append("runtime_environment_writable_path")
                    _write_result_payload()
                    return {
                        "project_browser_autonomous_codex_invocation_execution_status": status,
                        "project_browser_autonomous_codex_invocation_execution_source_status": (
                            source_status
                        ),
                        "project_browser_autonomous_codex_invocation_execution_block_reason": (
                            block_reason
                        ),
                        "project_browser_autonomous_codex_invocation_execution_selected_prompt_kind": (
                            normalized_prompt_kind
                        ),
                        "project_browser_autonomous_codex_invocation_execution_selected_prompt_path": (
                            normalized_prompt_path
                        ),
                        "project_browser_autonomous_codex_invocation_execution_selected_prompt_source": (
                            normalized_prompt_source
                        ),
                        "project_browser_autonomous_codex_invocation_execution_invocation_allowed": bool(
                            invocation_allowed
                        ),
                        "project_browser_autonomous_codex_invocation_execution_invocation_attempted": bool(
                            invocation_attempted
                        ),
                        "project_browser_autonomous_codex_invocation_execution_invocation_completed": bool(
                            invocation_completed
                        ),
                        "project_browser_autonomous_codex_invocation_execution_invocation_exit_code": int(
                            invocation_exit_code
                        ),
                        "project_browser_autonomous_codex_invocation_execution_invocation_timeout": bool(
                            invocation_timeout
                        ),
                        "project_browser_autonomous_codex_invocation_execution_invocation_command": (
                            invocation_command
                        ),
                        "project_browser_autonomous_codex_invocation_execution_invocation_stdout_path": (
                            stdout_path
                        ),
                        "project_browser_autonomous_codex_invocation_execution_invocation_stderr_path": (
                            stderr_path
                        ),
                        "project_browser_autonomous_codex_invocation_execution_invocation_stdout_excerpt": (
                            invocation_stdout_excerpt
                        ),
                        "project_browser_autonomous_codex_invocation_execution_invocation_stderr_excerpt": (
                            invocation_stderr_excerpt
                        ),
                        "project_browser_autonomous_codex_invocation_execution_max_invocations": int(
                            normalized_max_invocations
                        ),
                        "project_browser_autonomous_codex_invocation_execution_next_action": next_action,
                        "project_browser_autonomous_codex_invocation_execution_runtime_posture": (
                            runtime_posture
                        ),
                        "project_browser_autonomous_codex_invocation_execution_missing_inputs": (
                            _serialize_required_signals(missing_inputs)
                        ),
                        "project_browser_autonomous_codex_invocation_result_status": result_status,
                        "project_browser_autonomous_codex_invocation_result_source_status": (
                            result_source_status
                        ),
                        "project_browser_autonomous_codex_invocation_result_result_kind": result_kind,
                        "project_browser_autonomous_codex_invocation_result_result_path": result_path,
                        "project_browser_autonomous_codex_invocation_result_stdout_path": stdout_path,
                        "project_browser_autonomous_codex_invocation_result_stderr_path": stderr_path,
                        "project_browser_autonomous_codex_invocation_result_exit_code": int(
                            invocation_exit_code
                        ),
                        "project_browser_autonomous_codex_invocation_result_completed": bool(
                            result_completed
                        ),
                        "project_browser_autonomous_codex_invocation_result_failed": bool(
                            result_failed
                        ),
                        "project_browser_autonomous_codex_invocation_result_timeout": bool(
                            result_timeout
                        ),
                        "project_browser_autonomous_codex_invocation_result_next_action": (
                            result_next_action
                        ),
                        "project_browser_autonomous_codex_invocation_result_runtime_posture": (
                            runtime_posture
                        ),
                        "project_browser_autonomous_codex_invocation_result_missing_inputs": (
                            _serialize_required_signals(missing_inputs)
                        ),
                    }
                invocation_environment_overrides = {
                    "HOME": str(runtime_home),
                    "TMPDIR": str(runtime_tmp),
                    "XDG_CONFIG_HOME": str(runtime_config),
                    "XDG_CACHE_HOME": str(runtime_cache),
                    "XDG_STATE_HOME": str(runtime_state),
                    "XDG_DATA_HOME": str(runtime_data),
                    "CODEX_HOME": str(runtime_codex_home),
                }
            invocation_environment.update(invocation_environment_overrides)
            invocation_command = [
                codex_command,
                "exec",
                "-",
                "--cd",
                normalized_repository_path,
                "--sandbox",
                "workspace-write",
                "-m",
                "gpt-5.3-codex",
                "-c",
                'model_reasoning_effort="high"',
                "-c",
                'approval_policy="never"',
            ]
            prompt_text = ""
            try:
                prompt_text = Path(normalized_prompt_path).read_text(encoding="utf-8")
            except OSError as exc:
                status = "failed_execution_error"
                source_status = "prompt_read_error"
                block_reason = f"prompt_read_error:{type(exc).__name__}"
                next_action = "manual_codex_invocation_required"
                result_status = "failed_execution_error"
                result_source_status = source_status
                result_kind = "execution_error"
                result_failed = True
            else:
                invocation_attempted = True
                try:
                    completed = subprocess.run(
                        invocation_command,
                        input=prompt_text,
                        text=True,
                        capture_output=True,
                        timeout=timeout_seconds,
                        check=False,
                        env=invocation_environment,
                    )
                    invocation_completed = True
                    invocation_exit_code = int(completed.returncode)
                    stdout_text = _normalize_text(completed.stdout, default="")
                    stderr_text = _normalize_text(completed.stderr, default="")
                    invocation_stdout_excerpt = stdout_text[:excerpt_limit]
                    invocation_stderr_excerpt = stderr_text[:excerpt_limit]
                    try:
                        _write_text_file(stdout_path, stdout_text)
                        _write_text_file(stderr_path, stderr_text)
                    except OSError:
                        pass
                    status = "codex_invocation_completed"
                    source_status = "codex_exec_completed"
                    block_reason = "none" if invocation_exit_code == 0 else "codex_exit_nonzero"
                    next_action = "wait_for_more_truth"
                    result_kind = "codex_exec"
                    result_completed = True
                    result_timeout = False
                    if invocation_exit_code == 0:
                        result_status = "completed_success"
                        result_source_status = "codex_exec_completed_success"
                        result_failed = False
                        result_next_action = "wait_for_more_truth"
                    else:
                        result_status = "completed_failure"
                        result_source_status = "codex_exec_completed_failure"
                        result_failed = True
                        result_next_action = "manual_codex_invocation_required"
                except subprocess.TimeoutExpired as exc:
                    invocation_completed = True
                    invocation_timeout = True
                    invocation_exit_code = -1
                    timeout_stdout = _normalize_text(exc.stdout, default="")
                    timeout_stderr = _normalize_text(exc.stderr, default="")
                    invocation_stdout_excerpt = timeout_stdout[:excerpt_limit]
                    invocation_stderr_excerpt = timeout_stderr[:excerpt_limit]
                    try:
                        _write_text_file(stdout_path, timeout_stdout)
                        _write_text_file(stderr_path, timeout_stderr)
                    except OSError:
                        pass
                    status = "blocked_timeout"
                    source_status = "codex_exec_timeout"
                    block_reason = "codex_invocation_timeout"
                    next_action = "manual_codex_invocation_required"
                    result_status = "completed_timeout"
                    result_source_status = "codex_exec_timeout"
                    result_kind = "codex_exec_timeout"
                    result_completed = True
                    result_failed = True
                    result_timeout = True
                    result_next_action = "manual_codex_invocation_required"
                except OSError as exc:
                    invocation_completed = True
                    invocation_exit_code = -1
                    status = "failed_execution_error"
                    source_status = "codex_exec_os_error"
                    block_reason = f"execution_error:{type(exc).__name__}"
                    next_action = "manual_codex_invocation_required"
                    result_status = "failed_execution_error"
                    result_source_status = "codex_exec_os_error"
                    result_kind = "execution_error"
                    result_completed = True
                    result_failed = True
                    result_timeout = False
                    result_next_action = "manual_codex_invocation_required"

    if result_status == "insufficient_truth":
        if status in {
            "codex_invocation_completed",
            "blocked_timeout",
            "failed_execution_error",
        }:
            result_status = "failed_execution_error"
            result_source_status = source_status
            result_kind = "execution_error"
            result_failed = True
            result_next_action = "manual_codex_invocation_required"
        elif status.startswith("blocked_"):
            result_status = "blocked"
            result_source_status = source_status
            result_kind = "blocked"
            result_failed = False
            result_timeout = False
            result_next_action = next_action

    lower_stderr = _normalize_text(invocation_stderr_excerpt, default="").lower()
    lower_stdout = _normalize_text(invocation_stdout_excerpt, default="").lower()
    combined_output = f"{lower_stderr}\n{lower_stdout}"
    stderr_summary = _normalize_text(
        invocation_stderr_excerpt or invocation_stdout_excerpt,
        default="",
    )[:400]
    if status == "codex_invocation_completed" and invocation_exit_code == 0:
        blocker_class = "none"
        blocked_reason_classified = "none"
        retry_likely_repeats = False
    elif status == "blocked_codex_command_unavailable":
        blocker_class = "command_unavailable"
        blocked_reason_classified = "codex_invocation_blocked_command_unavailable"
        retry_likely_repeats = True
    elif status in {
        "blocked_missing_prompt",
        "blocked_prompt_path_unexpected",
        "blocked_prompt_path_symlink",
        "blocked_prompt_empty",
        "blocked_prompt_too_large",
    }:
        blocker_class = "prompt_path_or_content"
        blocked_reason_classified = "codex_invocation_blocked_prompt_path_or_content"
        retry_likely_repeats = False
    elif status == "blocked_timeout" or result_status == "completed_timeout":
        blocker_class = "timeout"
        blocked_reason_classified = "codex_invocation_blocked_timeout"
        retry_likely_repeats = True
    elif (
        "failed to connect to websocket" in combined_output
        or "wss://api.openai.com" in combined_output
        or ("operation not permitted" in combined_output and "websocket" in combined_output)
    ):
        blocker_class = "network_denied"
        blocked_reason_classified = "codex_invocation_blocked_network_denied"
        retry_likely_repeats = True
    elif (
        "read-only file system" in combined_output
        and (
            "thread/start" in combined_output
            or "failed to create session" in combined_output
            or "initialize session" in combined_output
        )
    ):
        blocker_class = "runtime_filesystem_readonly"
        blocked_reason_classified = "codex_invocation_blocked_readonly_session_init"
        retry_likely_repeats = True
    elif (
        "api key" in combined_output
        or "not logged in" in combined_output
        or "authentication" in combined_output
        or "unauthorized" in combined_output
        or "forbidden" in combined_output
        or "credentials" in combined_output
    ):
        blocker_class = "auth_or_config_missing"
        blocked_reason_classified = "codex_invocation_blocked_auth_or_config_missing"
        retry_likely_repeats = False
    elif "sandbox" in combined_output and (
        "denied" in combined_output or "not permitted" in combined_output
    ):
        blocker_class = "sandbox_restriction"
        blocked_reason_classified = "codex_invocation_blocked_sandbox_restriction"
        retry_likely_repeats = True
    elif status == "blocked_human_review_required":
        blocker_class = "safety_gate"
        blocked_reason_classified = "codex_invocation_blocked_human_review_required"
        retry_likely_repeats = True
    elif status == "blocked_insufficient_truth":
        blocker_class = "safety_gate"
        blocked_reason_classified = "codex_invocation_blocked_insufficient_truth"
        retry_likely_repeats = True
    elif status == "blocked_invocation_not_allowed":
        blocker_class = "safety_gate"
        blocked_reason_classified = "codex_invocation_blocked_invocation_not_allowed"
        retry_likely_repeats = True
    elif status == "failed_execution_error":
        blocker_class = "command_or_runtime_error"
        blocked_reason_classified = "codex_invocation_failed_execution_error"
        retry_likely_repeats = True
    else:
        blocker_class = "none" if block_reason == "none" else "execution_failed_unknown"
        blocked_reason_classified = (
            "none"
            if block_reason == "none"
            else "codex_invocation_blocked_unknown_execution_error"
        )
        retry_likely_repeats = bool(status == "codex_invocation_completed" and invocation_exit_code != 0)

    if status not in allowed_execution_statuses:
        status = "insufficient_truth"
    if result_status not in allowed_result_statuses:
        result_status = "insufficient_truth"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"
    if result_next_action not in allowed_next_actions:
        result_next_action = "insufficient_truth"

    _write_result_payload()

    return {
        "project_browser_autonomous_codex_invocation_execution_status": status,
        "project_browser_autonomous_codex_invocation_execution_source_status": (
            source_status
        ),
        "project_browser_autonomous_codex_invocation_execution_block_reason": (
            block_reason
        ),
        "project_browser_autonomous_codex_invocation_execution_blocker_class": blocker_class,
        "project_browser_autonomous_codex_invocation_execution_blocked_reason": (
            blocked_reason_classified
        ),
        "project_browser_autonomous_codex_invocation_execution_retry_likely_repeats": bool(
            retry_likely_repeats
        ),
        "project_browser_autonomous_codex_invocation_execution_stderr_summary": (
            _normalize_text(stderr_summary, default="")
        ),
        "project_browser_autonomous_codex_invocation_execution_selected_prompt_kind": (
            normalized_prompt_kind
        ),
        "project_browser_autonomous_codex_invocation_execution_selected_prompt_path": (
            normalized_prompt_path
        ),
        "project_browser_autonomous_codex_invocation_execution_selected_prompt_source": (
            normalized_prompt_source
        ),
        "project_browser_autonomous_codex_invocation_execution_invocation_allowed": bool(
            invocation_allowed
        ),
        "project_browser_autonomous_codex_invocation_execution_invocation_attempted": bool(
            invocation_attempted
        ),
        "project_browser_autonomous_codex_invocation_execution_invocation_completed": bool(
            invocation_completed
        ),
        "project_browser_autonomous_codex_invocation_execution_invocation_exit_code": int(
            invocation_exit_code
        ),
        "project_browser_autonomous_codex_invocation_execution_invocation_timeout": bool(
            invocation_timeout
        ),
        "project_browser_autonomous_codex_invocation_execution_invocation_command": (
            invocation_command
        ),
        "project_browser_autonomous_codex_invocation_execution_invocation_stdout_path": (
            stdout_path
        ),
        "project_browser_autonomous_codex_invocation_execution_invocation_stderr_path": (
            stderr_path
        ),
        "project_browser_autonomous_codex_invocation_execution_invocation_stdout_excerpt": (
            invocation_stdout_excerpt
        ),
        "project_browser_autonomous_codex_invocation_execution_invocation_stderr_excerpt": (
            invocation_stderr_excerpt
        ),
        "project_browser_autonomous_codex_invocation_execution_max_invocations": int(
            normalized_max_invocations
        ),
        "project_browser_autonomous_codex_invocation_execution_next_action": next_action,
        "project_browser_autonomous_codex_invocation_execution_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_codex_invocation_execution_missing_inputs": (
            _serialize_required_signals(missing_inputs)
        ),
        "project_browser_autonomous_codex_invocation_result_status": result_status,
        "project_browser_autonomous_codex_invocation_result_source_status": (
            result_source_status
        ),
        "project_browser_autonomous_codex_invocation_result_result_kind": result_kind,
        "project_browser_autonomous_codex_invocation_result_blocker_class": blocker_class,
        "project_browser_autonomous_codex_invocation_result_blocked_reason": (
            blocked_reason_classified
        ),
        "project_browser_autonomous_codex_invocation_result_result_path": result_path,
        "project_browser_autonomous_codex_invocation_result_stdout_path": stdout_path,
        "project_browser_autonomous_codex_invocation_result_stderr_path": stderr_path,
        "project_browser_autonomous_codex_invocation_result_exit_code": int(
            invocation_exit_code
        ),
        "project_browser_autonomous_codex_invocation_result_completed": bool(
            result_completed
        ),
        "project_browser_autonomous_codex_invocation_result_failed": bool(
            result_failed
        ),
        "project_browser_autonomous_codex_invocation_result_timeout": bool(
            result_timeout
        ),
        "project_browser_autonomous_codex_invocation_result_next_action": (
            result_next_action
        ),
        "project_browser_autonomous_codex_invocation_result_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_codex_invocation_result_missing_inputs": (
            _serialize_required_signals(missing_inputs)
        ),
    }

def _build_project_browser_autonomous_codex_write_invocation_state(
    *,
    repository_path: str,
    codex_invocation_readiness_status: str,
    codex_invocation_readiness_allowed: bool,
    selected_prompt_kind: str,
    selected_prompt_path: str,
    selected_prompt_source: str,
    selected_prompt_ready: bool,
    selected_prompt_path_is_exact: bool,
    selected_prompt_path_exists: bool,
    selected_prompt_path_is_symlink: bool,
    selected_prompt_file_non_empty: bool,
    selected_prompt_file_too_large: bool,
    rollback_required: bool,
    human_review_required: bool,
    insufficient_truth: bool,
    max_invocations: int,
    prior_write_invocation_attempted: bool,
    prior_write_invocation_completed: bool,
) -> dict[str, Any]:
    allowed_readiness_statuses = {
        "ready_for_write_codex_invocation",
        "blocked_not_ready",
        "blocked_invocation_not_allowed",
        "blocked_missing_prompt",
        "blocked_prompt_path_unexpected",
        "blocked_prompt_path_symlink",
        "blocked_prompt_empty",
        "blocked_prompt_too_large",
        "blocked_dirty_worktree_before",
        "blocked_rollback_required",
        "blocked_human_review_required",
        "blocked_insufficient_truth",
        "blocked_codex_command_unavailable",
        "insufficient_truth",
    }
    allowed_execution_statuses = {
        "codex_write_invocation_completed",
        "blocked_not_ready",
        "blocked_invocation_not_allowed",
        "blocked_missing_prompt",
        "blocked_prompt_path_unexpected",
        "blocked_prompt_path_symlink",
        "blocked_prompt_empty",
        "blocked_prompt_too_large",
        "blocked_dirty_worktree_before",
        "blocked_rollback_required",
        "blocked_human_review_required",
        "blocked_insufficient_truth",
        "blocked_codex_command_unavailable",
        "blocked_timeout",
        "failed_execution_error",
        "insufficient_truth",
    }
    allowed_result_statuses = {
        "completed_with_changes",
        "completed_no_changes",
        "completed_failure",
        "completed_timeout",
        "blocked",
        "failed_execution_error",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "assimilate_codex_git_diff_later",
        "wait_for_prompt_selection",
        "wait_for_codex_invocation_readiness",
        "wait_for_more_truth",
        "manual_review_required",
        "rollback_required",
        "insufficient_truth",
    }
    allowed_prompt_paths = {
        "/tmp/codex-local-runner-decision/generated_fix_prompt.txt",
        "/tmp/codex-local-runner-decision/generated_next_prompt.txt",
    }
    stdout_path = "/tmp/codex-local-runner-decision/codex_write_invocation_stdout.txt"
    stderr_path = "/tmp/codex-local-runner-decision/codex_write_invocation_stderr.txt"
    result_json_path = "/tmp/codex-local-runner-decision/codex_write_invocation_result.json"
    git_diff_name_only_path = "/tmp/codex-local-runner-decision/codex_write_git_diff_name_only.txt"
    git_diff_numstat_path = "/tmp/codex-local-runner-decision/codex_write_git_diff_numstat.txt"
    timeout_seconds = 300.0
    excerpt_limit = 800
    runtime_posture = [
        "bounded_write_codex_invocation",
        "one_invocation_only",
        "workspace_write_mode",
        "no_retry",
        "no_autonomous_loop",
        "no_patch_candidate_classification",
        "no_patch_apply",
        "no_git_commit",
        "no_git_push",
        "no_github_mutation",
        "post_invocation_git_accounting_only",
    ]
    normalized_repository_path = _normalize_text(repository_path, default="")
    normalized_readiness_status = _normalize_text(
        codex_invocation_readiness_status,
        default="insufficient_truth",
    )
    normalized_prompt_kind = _normalize_text(selected_prompt_kind, default="none")
    normalized_prompt_path = _normalize_text(selected_prompt_path, default="")
    normalized_prompt_source = _normalize_text(selected_prompt_source, default="")
    normalized_max_invocations = (
        1 if _as_non_negative_int(max_invocations, default=1) != 1 else 1
    )

    readiness_status = "insufficient_truth"
    readiness_source_status = "insufficient_truth"
    readiness_block_reason = "insufficient_truth"
    worktree_clean_before = False
    worktree_status_before = ""
    readiness_invocation_allowed = False
    readiness_invocation_blocked = True
    readiness_next_action = "insufficient_truth"
    readiness_missing_inputs: list[str] = []

    execution_status = "insufficient_truth"
    execution_source_status = "insufficient_truth"
    execution_block_reason = "insufficient_truth"
    execution_invocation_allowed = False
    execution_invocation_attempted = bool(prior_write_invocation_attempted)
    execution_invocation_completed = bool(prior_write_invocation_completed)
    execution_invocation_exit_code = -1
    execution_invocation_timeout = False
    execution_invocation_command: list[str] = []
    execution_sandbox_mode = "workspace-write"
    execution_write_enabled = True
    execution_invocation_stdout_excerpt = ""
    execution_invocation_stderr_excerpt = ""
    execution_next_action = "insufficient_truth"
    execution_missing_inputs: list[str] = []

    result_status = "insufficient_truth"
    result_source_status = "insufficient_truth"
    result_kind = "none"
    result_exit_code = -1
    result_completed = False
    result_failed = False
    result_timeout = False
    worktree_dirty_after = False
    worktree_status_after = ""
    changed_files_after: list[str] = []
    changed_files_count_after = 0
    result_next_action = "insufficient_truth"
    result_missing_inputs: list[str] = []

    output_paths = [
        stdout_path,
        stderr_path,
        result_json_path,
        git_diff_name_only_path,
        git_diff_numstat_path,
    ]

    def _output_paths_safe() -> bool:
        for path_text in output_paths:
            path_obj = Path(path_text)
            parent = path_obj.parent
            if not parent.exists():
                readiness_missing_inputs.append(f"output_parent_missing:{parent}")
                return False
            if path_obj.exists() and path_obj.is_symlink():
                readiness_missing_inputs.append(f"output_path_symlink:{path_text}")
                return False
        return True

    def _write_text(path_text: str, content: str) -> None:
        path_obj = Path(path_text)
        if path_obj.exists() and path_obj.is_symlink():
            return
        path_obj.write_text(content, encoding="utf-8")

    def _capture_git_accounting() -> tuple[str, bool, list[str], str, str]:
        status_text = ""
        name_only_text = ""
        numstat_text = ""
        changed_files_local: list[str] = []
        dirty_local = False
        try:
            status_cp = _run_git(
                normalized_repository_path,
                ["status", "--short"],
                timeout_seconds=10.0,
            )
            status_text = _normalize_text(status_cp.stdout, default="")
            dirty_local = bool(status_text)
        except (subprocess.TimeoutExpired, OSError):
            return "", False, [], "", ""

        try:
            name_cp = _run_git(
                normalized_repository_path,
                ["diff", "--name-only"],
                timeout_seconds=10.0,
            )
            name_only_text = _normalize_text(name_cp.stdout, default="")
            changed_files_local = _serialize_required_signals(name_only_text.splitlines())
        except (subprocess.TimeoutExpired, OSError):
            name_only_text = ""
            changed_files_local = []

        try:
            numstat_cp = _run_git(
                normalized_repository_path,
                ["diff", "--numstat"],
                timeout_seconds=10.0,
            )
            numstat_text = _normalize_text(numstat_cp.stdout, default="")
        except (subprocess.TimeoutExpired, OSError):
            numstat_text = ""

        return (
            status_text,
            dirty_local,
            changed_files_local,
            name_only_text,
            numstat_text,
        )

    def _write_result_json_payload() -> None:
        payload = {
            "readiness_status": readiness_status,
            "execution_status": execution_status,
            "result_status": result_status,
            "exit_code": result_exit_code,
            "completed": bool(result_completed),
            "failed": bool(result_failed),
            "timeout": bool(result_timeout),
            "worktree_dirty_after": bool(worktree_dirty_after),
            "worktree_status_after": worktree_status_after,
            "changed_files_after": changed_files_after,
            "changed_files_count_after": int(changed_files_count_after),
            "stdout_path": stdout_path,
            "stderr_path": stderr_path,
            "git_diff_name_only_path": git_diff_name_only_path,
            "git_diff_numstat_path": git_diff_numstat_path,
            "next_action": result_next_action,
            "missing_inputs": _serialize_required_signals(
                [*readiness_missing_inputs, *execution_missing_inputs, *result_missing_inputs]
            ),
        }
        try:
            _write_text(
                result_json_path,
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            )
        except OSError:
            pass

    if rollback_required:
        readiness_status = "blocked_rollback_required"
        readiness_source_status = "rollback_required"
        readiness_block_reason = "rollback_required"
        readiness_next_action = "rollback_required"
    elif human_review_required:
        readiness_status = "blocked_human_review_required"
        readiness_source_status = "human_review_required"
        readiness_block_reason = "human_review_required"
        readiness_next_action = "manual_review_required"
    elif insufficient_truth:
        readiness_status = "blocked_insufficient_truth"
        readiness_source_status = "insufficient_truth_active"
        readiness_block_reason = "insufficient_truth"
        readiness_next_action = "wait_for_more_truth"
        readiness_missing_inputs.append("codex_invocation_readiness_truth")
    elif normalized_readiness_status != "ready_to_invoke_codex":
        readiness_status = "blocked_not_ready"
        readiness_source_status = "readiness_not_ready"
        readiness_block_reason = (
            f"readiness_status:{normalized_readiness_status or 'unknown'}"
        )
        readiness_next_action = "wait_for_codex_invocation_readiness"
    elif not codex_invocation_readiness_allowed:
        readiness_status = "blocked_invocation_not_allowed"
        readiness_source_status = "readiness_invocation_not_allowed"
        readiness_block_reason = "invocation_allowed_false"
        readiness_next_action = "wait_for_codex_invocation_readiness"
    elif normalized_max_invocations != 1:
        readiness_status = "blocked_invocation_not_allowed"
        readiness_source_status = "max_invocations_invalid"
        readiness_block_reason = "max_invocations_not_one"
        readiness_next_action = "wait_for_codex_invocation_readiness"
    elif execution_invocation_attempted or execution_invocation_completed:
        readiness_status = "blocked_invocation_not_allowed"
        readiness_source_status = "prior_write_invocation_exists"
        readiness_block_reason = "prior_write_invocation_already_attempted"
        readiness_next_action = "wait_for_more_truth"
    elif normalized_prompt_kind not in {"fix", "next"}:
        readiness_status = "blocked_not_ready"
        readiness_source_status = "selected_prompt_kind_invalid"
        readiness_block_reason = "selected_prompt_kind_invalid"
        readiness_next_action = "wait_for_prompt_selection"
    elif not selected_prompt_ready:
        readiness_status = "blocked_not_ready"
        readiness_source_status = "selected_prompt_not_ready"
        readiness_block_reason = "selected_prompt_not_ready"
        readiness_next_action = "wait_for_prompt_selection"
    elif normalized_prompt_path not in allowed_prompt_paths or not selected_prompt_path_is_exact:
        readiness_status = "blocked_prompt_path_unexpected"
        readiness_source_status = "selected_prompt_path_unexpected"
        readiness_block_reason = "selected_prompt_path_unexpected"
        readiness_next_action = "wait_for_prompt_selection"
    elif selected_prompt_path_is_symlink:
        readiness_status = "blocked_prompt_path_symlink"
        readiness_source_status = "selected_prompt_path_symlink"
        readiness_block_reason = "selected_prompt_path_symlink"
        readiness_next_action = "wait_for_prompt_selection"
    elif not selected_prompt_path_exists:
        readiness_status = "blocked_missing_prompt"
        readiness_source_status = "selected_prompt_missing"
        readiness_block_reason = "selected_prompt_path_missing"
        readiness_next_action = "wait_for_prompt_selection"
    elif not selected_prompt_file_non_empty:
        readiness_status = "blocked_prompt_empty"
        readiness_source_status = "selected_prompt_empty"
        readiness_block_reason = "selected_prompt_empty"
        readiness_next_action = "wait_for_prompt_selection"
    elif selected_prompt_file_too_large:
        readiness_status = "blocked_prompt_too_large"
        readiness_source_status = "selected_prompt_too_large"
        readiness_block_reason = "selected_prompt_too_large"
        readiness_next_action = "wait_for_prompt_selection"
    elif not _output_paths_safe():
        readiness_status = "blocked_invocation_not_allowed"
        readiness_source_status = "output_path_constraints_failed"
        readiness_block_reason = "output_path_constraints_failed"
        readiness_next_action = "wait_for_more_truth"
    else:
        codex_command = shutil.which("codex")
        if not codex_command:
            readiness_status = "blocked_codex_command_unavailable"
            readiness_source_status = "codex_command_unavailable"
            readiness_block_reason = "codex_command_unavailable"
            readiness_next_action = "wait_for_more_truth"
        else:
            supports_workspace_write = False
            try:
                help_cp = subprocess.run(
                    [codex_command, "exec", "--help"],
                    text=True,
                    capture_output=True,
                    timeout=10.0,
                    check=False,
                )
                help_text = (
                    _normalize_text(help_cp.stdout, default="")
                    + "\n"
                    + _normalize_text(help_cp.stderr, default="")
                )
                supports_workspace_write = "workspace-write" in help_text
            except (subprocess.TimeoutExpired, OSError):
                supports_workspace_write = False
            if not supports_workspace_write:
                readiness_status = "blocked_codex_command_unavailable"
                readiness_source_status = "workspace_write_mode_unavailable"
                readiness_block_reason = "workspace_write_mode_unavailable"
                readiness_next_action = "wait_for_more_truth"
            else:
                try:
                    status_before_cp = _run_git(
                        normalized_repository_path,
                        ["status", "--short"],
                        timeout_seconds=10.0,
                    )
                    worktree_status_before = _normalize_text(
                        status_before_cp.stdout,
                        default="",
                    )
                    worktree_clean_before = bool(
                        status_before_cp.returncode == 0 and not worktree_status_before
                    )
                except (subprocess.TimeoutExpired, OSError):
                    worktree_status_before = ""
                    worktree_clean_before = False
                    readiness_missing_inputs.append("worktree_status_before")
                if not worktree_clean_before:
                    readiness_status = "blocked_dirty_worktree_before"
                    readiness_source_status = "worktree_not_clean_before"
                    readiness_block_reason = "dirty_worktree_before"
                    readiness_next_action = "manual_review_required"
                else:
                    readiness_status = "ready_for_write_codex_invocation"
                    readiness_source_status = "all_write_invocation_gates_satisfied"
                    readiness_block_reason = "none"
                    readiness_invocation_allowed = True
                    readiness_invocation_blocked = False
                    readiness_next_action = "wait_for_codex_invocation_readiness"

    execution_status = (
        readiness_status if readiness_status != "ready_for_write_codex_invocation" else "insufficient_truth"
    )
    execution_source_status = readiness_source_status
    execution_block_reason = readiness_block_reason
    execution_invocation_allowed = readiness_invocation_allowed
    execution_next_action = readiness_next_action
    execution_missing_inputs = list(readiness_missing_inputs)

    if readiness_status == "ready_for_write_codex_invocation":
        codex_command = shutil.which("codex")
        if not codex_command:
            execution_status = "blocked_codex_command_unavailable"
            execution_source_status = "codex_command_unavailable"
            execution_block_reason = "codex_command_unavailable"
            execution_next_action = "wait_for_more_truth"
            result_status = "blocked"
            result_source_status = execution_source_status
            result_kind = "blocked"
            result_next_action = execution_next_action
        else:
            execution_invocation_command = [
                codex_command,
                "exec",
                "-",
                "--cd",
                normalized_repository_path,
                "--sandbox",
                "workspace-write",
            ]
            execution_invocation_command = _serialize_required_signals(
                execution_invocation_command
            )
            execution_invocation_command = execution_invocation_command
            execution_invocation_attempted = True
            execution_invocation_completed = False
            prompt_text = ""
            try:
                prompt_text = Path(normalized_prompt_path).read_text(encoding="utf-8")
            except OSError as exc:
                execution_status = "failed_execution_error"
                execution_source_status = "prompt_read_error"
                execution_block_reason = f"prompt_read_error:{type(exc).__name__}"
                execution_next_action = "wait_for_more_truth"
                result_status = "failed_execution_error"
                result_source_status = execution_source_status
                result_kind = "execution_error"
                result_failed = True
                result_next_action = "wait_for_more_truth"
            else:
                execution_invocation_command = [
                    codex_command,
                    "exec",
                    "-",
                    "--cd",
                    normalized_repository_path,
                    "--sandbox",
                    "workspace-write",
                ]
                try:
                    completed = subprocess.run(
                        execution_invocation_command,
                        input=prompt_text,
                        text=True,
                        capture_output=True,
                        timeout=timeout_seconds,
                        check=False,
                    )
                    execution_invocation_completed = True
                    execution_invocation_exit_code = int(completed.returncode)
                    stdout_text = _normalize_text(completed.stdout, default="")
                    stderr_text = _normalize_text(completed.stderr, default="")
                    execution_invocation_stdout_excerpt = stdout_text[:excerpt_limit]
                    execution_invocation_stderr_excerpt = stderr_text[:excerpt_limit]
                    try:
                        _write_text(stdout_path, stdout_text)
                        _write_text(stderr_path, stderr_text)
                    except OSError:
                        pass
                    execution_status = "codex_write_invocation_completed"
                    execution_source_status = "codex_write_exec_completed"
                    execution_block_reason = (
                        "none"
                        if execution_invocation_exit_code == 0
                        else "codex_exit_nonzero"
                    )
                    execution_next_action = "wait_for_more_truth"
                    result_source_status = execution_source_status
                    result_kind = "codex_write_exec"
                    result_exit_code = execution_invocation_exit_code
                    result_completed = True
                    result_timeout = False
                    if execution_invocation_exit_code == 0:
                        result_failed = False
                    else:
                        result_failed = True
                except subprocess.TimeoutExpired as exc:
                    execution_invocation_completed = True
                    execution_invocation_timeout = True
                    execution_invocation_exit_code = -1
                    timeout_stdout = _normalize_text(exc.stdout, default="")
                    timeout_stderr = _normalize_text(exc.stderr, default="")
                    execution_invocation_stdout_excerpt = timeout_stdout[:excerpt_limit]
                    execution_invocation_stderr_excerpt = timeout_stderr[:excerpt_limit]
                    try:
                        _write_text(stdout_path, timeout_stdout)
                        _write_text(stderr_path, timeout_stderr)
                    except OSError:
                        pass
                    execution_status = "blocked_timeout"
                    execution_source_status = "codex_write_exec_timeout"
                    execution_block_reason = "codex_write_invocation_timeout"
                    execution_next_action = "wait_for_more_truth"
                    result_status = "completed_timeout"
                    result_source_status = execution_source_status
                    result_kind = "codex_write_exec_timeout"
                    result_exit_code = -1
                    result_completed = True
                    result_failed = True
                    result_timeout = True
                    result_next_action = "wait_for_more_truth"
                except OSError as exc:
                    execution_invocation_completed = True
                    execution_invocation_exit_code = -1
                    execution_status = "failed_execution_error"
                    execution_source_status = "codex_write_exec_os_error"
                    execution_block_reason = f"execution_error:{type(exc).__name__}"
                    execution_next_action = "wait_for_more_truth"
                    result_status = "failed_execution_error"
                    result_source_status = execution_source_status
                    result_kind = "execution_error"
                    result_exit_code = -1
                    result_completed = True
                    result_failed = True
                    result_timeout = False
                    result_next_action = "wait_for_more_truth"

            execution_invocation_command = _serialize_required_signals(
                execution_invocation_command
            )
            status_after, dirty_after, files_after, diff_name, diff_num = _capture_git_accounting()
            worktree_status_after = status_after[:excerpt_limit]
            worktree_dirty_after = bool(dirty_after)
            changed_files_after = files_after
            changed_files_count_after = len(changed_files_after)
            try:
                _write_text(git_diff_name_only_path, diff_name)
                _write_text(git_diff_numstat_path, diff_num)
            except OSError:
                pass

            if result_status == "insufficient_truth":
                if execution_status == "codex_write_invocation_completed":
                    if result_exit_code == 0:
                        if changed_files_count_after > 0:
                            result_status = "completed_with_changes"
                            result_next_action = "assimilate_codex_git_diff_later"
                        else:
                            result_status = "completed_no_changes"
                            result_next_action = "manual_review_required"
                    else:
                        result_status = "completed_failure"
                        result_next_action = "wait_for_more_truth"
                elif execution_status.startswith("blocked_"):
                    result_status = "blocked"
                    result_kind = "blocked"
                    result_next_action = execution_next_action
                elif execution_status == "failed_execution_error":
                    result_status = "failed_execution_error"
                    result_next_action = "wait_for_more_truth"

    if result_status == "insufficient_truth":
        if execution_status.startswith("blocked_"):
            result_status = "blocked"
            result_source_status = execution_source_status
            result_kind = "blocked"
            result_failed = False
            result_timeout = False
            result_next_action = execution_next_action
        elif execution_status == "failed_execution_error":
            result_status = "failed_execution_error"
            result_source_status = execution_source_status
            result_kind = "execution_error"
            result_failed = True
            result_timeout = False
            result_next_action = "wait_for_more_truth"

    if readiness_status not in allowed_readiness_statuses:
        readiness_status = "insufficient_truth"
    if readiness_next_action not in allowed_next_actions:
        readiness_next_action = "insufficient_truth"
    if execution_status not in allowed_execution_statuses:
        execution_status = "insufficient_truth"
    if execution_next_action not in allowed_next_actions:
        execution_next_action = "insufficient_truth"
    if result_status not in allowed_result_statuses:
        result_status = "insufficient_truth"
    if result_next_action not in allowed_next_actions:
        result_next_action = "insufficient_truth"

    _write_result_json_payload()

    merged_missing_inputs = _serialize_required_signals(
        [
            *readiness_missing_inputs,
            *execution_missing_inputs,
            *result_missing_inputs,
        ]
    )

    return {
        "project_browser_autonomous_codex_write_invocation_readiness_status": readiness_status,
        "project_browser_autonomous_codex_write_invocation_readiness_source_status": (
            readiness_source_status
        ),
        "project_browser_autonomous_codex_write_invocation_readiness_block_reason": (
            readiness_block_reason
        ),
        "project_browser_autonomous_codex_write_invocation_readiness_selected_prompt_kind": (
            normalized_prompt_kind
        ),
        "project_browser_autonomous_codex_write_invocation_readiness_selected_prompt_path": (
            normalized_prompt_path
        ),
        "project_browser_autonomous_codex_write_invocation_readiness_selected_prompt_ready": bool(
            selected_prompt_ready
        ),
        "project_browser_autonomous_codex_write_invocation_readiness_selected_prompt_path_is_exact": bool(
            selected_prompt_path_is_exact
        ),
        "project_browser_autonomous_codex_write_invocation_readiness_selected_prompt_path_exists": bool(
            selected_prompt_path_exists
        ),
        "project_browser_autonomous_codex_write_invocation_readiness_selected_prompt_path_is_symlink": bool(
            selected_prompt_path_is_symlink
        ),
        "project_browser_autonomous_codex_write_invocation_readiness_selected_prompt_file_non_empty": bool(
            selected_prompt_file_non_empty
        ),
        "project_browser_autonomous_codex_write_invocation_readiness_selected_prompt_file_too_large": bool(
            selected_prompt_file_too_large
        ),
        "project_browser_autonomous_codex_write_invocation_readiness_worktree_clean_before": bool(
            worktree_clean_before
        ),
        "project_browser_autonomous_codex_write_invocation_readiness_worktree_status_before": (
            worktree_status_before
        ),
        "project_browser_autonomous_codex_write_invocation_readiness_invocation_allowed": bool(
            readiness_invocation_allowed
        ),
        "project_browser_autonomous_codex_write_invocation_readiness_invocation_blocked": bool(
            readiness_invocation_blocked
        ),
        "project_browser_autonomous_codex_write_invocation_readiness_max_invocations": int(
            normalized_max_invocations
        ),
        "project_browser_autonomous_codex_write_invocation_readiness_rollback_required": bool(
            rollback_required
        ),
        "project_browser_autonomous_codex_write_invocation_readiness_human_review_required": bool(
            human_review_required
        ),
        "project_browser_autonomous_codex_write_invocation_readiness_insufficient_truth": bool(
            insufficient_truth
        ),
        "project_browser_autonomous_codex_write_invocation_readiness_next_action": (
            readiness_next_action
        ),
        "project_browser_autonomous_codex_write_invocation_readiness_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_codex_write_invocation_readiness_missing_inputs": (
            _serialize_required_signals(readiness_missing_inputs)
        ),
        "project_browser_autonomous_codex_write_invocation_execution_status": execution_status,
        "project_browser_autonomous_codex_write_invocation_execution_source_status": (
            execution_source_status
        ),
        "project_browser_autonomous_codex_write_invocation_execution_block_reason": (
            execution_block_reason
        ),
        "project_browser_autonomous_codex_write_invocation_execution_selected_prompt_kind": (
            normalized_prompt_kind
        ),
        "project_browser_autonomous_codex_write_invocation_execution_selected_prompt_path": (
            normalized_prompt_path
        ),
        "project_browser_autonomous_codex_write_invocation_execution_invocation_allowed": bool(
            execution_invocation_allowed
        ),
        "project_browser_autonomous_codex_write_invocation_execution_invocation_attempted": bool(
            execution_invocation_attempted
        ),
        "project_browser_autonomous_codex_write_invocation_execution_invocation_completed": bool(
            execution_invocation_completed
        ),
        "project_browser_autonomous_codex_write_invocation_execution_invocation_exit_code": int(
            execution_invocation_exit_code
        ),
        "project_browser_autonomous_codex_write_invocation_execution_invocation_timeout": bool(
            execution_invocation_timeout
        ),
        "project_browser_autonomous_codex_write_invocation_execution_invocation_command": (
            execution_invocation_command
        ),
        "project_browser_autonomous_codex_write_invocation_execution_sandbox_mode": (
            execution_sandbox_mode
        ),
        "project_browser_autonomous_codex_write_invocation_execution_write_enabled": bool(
            execution_write_enabled
        ),
        "project_browser_autonomous_codex_write_invocation_execution_invocation_stdout_path": (
            stdout_path
        ),
        "project_browser_autonomous_codex_write_invocation_execution_invocation_stderr_path": (
            stderr_path
        ),
        "project_browser_autonomous_codex_write_invocation_execution_invocation_stdout_excerpt": (
            execution_invocation_stdout_excerpt
        ),
        "project_browser_autonomous_codex_write_invocation_execution_invocation_stderr_excerpt": (
            execution_invocation_stderr_excerpt
        ),
        "project_browser_autonomous_codex_write_invocation_execution_max_invocations": int(
            normalized_max_invocations
        ),
        "project_browser_autonomous_codex_write_invocation_execution_next_action": (
            execution_next_action
        ),
        "project_browser_autonomous_codex_write_invocation_execution_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_codex_write_invocation_execution_missing_inputs": (
            _serialize_required_signals(execution_missing_inputs)
        ),
        "project_browser_autonomous_codex_write_invocation_result_status": result_status,
        "project_browser_autonomous_codex_write_invocation_result_source_status": (
            result_source_status
        ),
        "project_browser_autonomous_codex_write_invocation_result_result_kind": result_kind,
        "project_browser_autonomous_codex_write_invocation_result_exit_code": int(
            result_exit_code
        ),
        "project_browser_autonomous_codex_write_invocation_result_completed": bool(
            result_completed
        ),
        "project_browser_autonomous_codex_write_invocation_result_failed": bool(
            result_failed
        ),
        "project_browser_autonomous_codex_write_invocation_result_timeout": bool(
            result_timeout
        ),
        "project_browser_autonomous_codex_write_invocation_result_worktree_dirty_after": bool(
            worktree_dirty_after
        ),
        "project_browser_autonomous_codex_write_invocation_result_worktree_status_after": (
            worktree_status_after
        ),
        "project_browser_autonomous_codex_write_invocation_result_changed_files_after": (
            changed_files_after
        ),
        "project_browser_autonomous_codex_write_invocation_result_changed_files_count_after": int(
            changed_files_count_after
        ),
        "project_browser_autonomous_codex_write_invocation_result_git_diff_name_only_path": (
            git_diff_name_only_path
        ),
        "project_browser_autonomous_codex_write_invocation_result_git_diff_numstat_path": (
            git_diff_numstat_path
        ),
        "project_browser_autonomous_codex_write_invocation_result_stdout_path": (
            stdout_path
        ),
        "project_browser_autonomous_codex_write_invocation_result_stderr_path": (
            stderr_path
        ),
        "project_browser_autonomous_codex_write_invocation_result_result_json_path": (
            result_json_path
        ),
        "project_browser_autonomous_codex_write_invocation_result_next_action": (
            result_next_action
        ),
        "project_browser_autonomous_codex_write_invocation_result_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_codex_write_invocation_result_missing_inputs": (
            merged_missing_inputs
        ),
    }

def _build_project_browser_autonomous_codex_write_result_assimilation_state(
    *,
    write_invocation_status: str,
    write_invocation_result_status: str,
    smoke_override_status: str,
    smoke_override_used: bool,
    selected_prompt_kind: str,
    selected_prompt_path: str,
    exit_code: int,
    timeout: bool,
    completed: bool,
    failed: bool,
    worktree_dirty_after: bool,
    changed_files_after: list[str] | None,
    changed_files_count_after: int,
    diff_name_only_path: str,
    diff_numstat_path: str,
    fix_target_files: list[str] | None,
    next_target_files: list[str] | None,
) -> dict[str, Any]:
    allowed_statuses = {
        "assimilated_with_expected_changes",
        "assimilated_with_no_changes",
        "assimilated_with_unexpected_changes",
        "assimilated_with_forbidden_changes",
        "assimilated_too_many_changes",
        "assimilated_completed_failure",
        "assimilated_completed_timeout",
        "blocked_no_write_invocation_result",
        "blocked_write_invocation_not_completed",
        "blocked_insufficient_truth",
        "manual_review_required",
        "insufficient_truth",
    }
    allowed_result_classes = {
        "expected_changes",
        "no_changes",
        "unexpected_changes",
        "forbidden_changes",
        "too_many_changes",
        "invocation_failure",
        "invocation_timeout",
        "blocked",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "route_to_safe_validation_later",
        "manual_review_required",
        "wait_for_write_invocation",
        "wait_for_more_truth",
        "rollback_required",
        "insufficient_truth",
    }
    fixed_name_only_path = (
        "/tmp/codex-local-runner-decision/codex_write_git_diff_name_only.txt"
    )
    fixed_numstat_path = "/tmp/codex-local-runner-decision/codex_write_git_diff_numstat.txt"
    allowed_diff_paths = {fixed_name_only_path, fixed_numstat_path}
    smoke_marker_path = "prompt167_workspace_write_smoke.txt"
    max_changed_files_threshold = 8
    runtime_posture = [
        "metadata_only_codex_write_result_assimilation",
        "bounded_changed_file_classification",
        "fixed_diff_path_inputs_only",
        "no_patch_apply",
        "no_rollback_execution",
        "no_git_stage_commit_push",
        "no_github_mutation",
        "no_autonomous_loop",
    ]

    normalized_write_invocation_status = _normalize_text(
        write_invocation_status,
        default="insufficient_truth",
    )
    normalized_write_invocation_result_status = _normalize_text(
        write_invocation_result_status,
        default="insufficient_truth",
    )
    normalized_smoke_override_status = _normalize_text(
        smoke_override_status,
        default="insufficient_truth",
    )
    normalized_selected_prompt_kind = _normalize_text(selected_prompt_kind, default="none")
    if normalized_selected_prompt_kind not in {"fix", "next", "none"}:
        normalized_selected_prompt_kind = "none"
    normalized_selected_prompt_path = _normalize_text(selected_prompt_path, default="")
    normalized_changed_files = _normalize_string_list(changed_files_after or [])
    normalized_changed_files_count = _as_non_negative_int(changed_files_count_after, default=0)
    normalized_fix_targets = _normalize_string_list(fix_target_files or [])
    normalized_next_targets = _normalize_string_list(next_target_files or [])
    normalized_diff_name_only_path = _normalize_text(diff_name_only_path, default="")
    normalized_diff_numstat_path = _normalize_text(diff_numstat_path, default="")

    status = "insufficient_truth"
    source_status = "insufficient_truth"
    block_reason = "insufficient_truth"
    result_class = "insufficient_truth"
    safe_for_validation_routing = False
    manual_review_required = False
    rollback_required = False
    next_action = "insufficient_truth"
    missing_inputs: list[str] = []

    expected_changed_files: list[str] = []
    if normalized_selected_prompt_kind == "fix":
        expected_changed_files = list(normalized_fix_targets)
    elif normalized_selected_prompt_kind == "next":
        expected_changed_files = list(normalized_next_targets)
    else:
        expected_changed_files = _serialize_required_signals(
            [*normalized_fix_targets, *normalized_next_targets]
        )
    if bool(smoke_override_used):
        expected_changed_files = _serialize_required_signals(
            [*expected_changed_files, smoke_marker_path]
        )
    expected_changed_files = _serialize_required_signals(expected_changed_files)
    allowed_changed_files = list(expected_changed_files)
    allowed_changed_set = set(allowed_changed_files)

    def _load_changed_files_from_diff_path(path_text: str) -> list[str]:
        normalized_path = _normalize_text(path_text, default="")
        if not normalized_path or normalized_path not in allowed_diff_paths:
            return []
        diff_path_obj = Path(normalized_path)
        if not diff_path_obj.exists() or diff_path_obj.is_symlink():
            return []
        try:
            content = diff_path_obj.read_text(encoding="utf-8")
        except OSError:
            return []
        return _serialize_required_signals(content.splitlines())

    if not normalized_changed_files:
        changed_from_name_only = _load_changed_files_from_diff_path(
            normalized_diff_name_only_path
        )
        changed_from_numstat = _load_changed_files_from_diff_path(
            normalized_diff_numstat_path
        )
        if changed_from_name_only:
            normalized_changed_files = changed_from_name_only
        elif changed_from_numstat:
            # numstat lines are `<add>\t<del>\t<path>`; keep only terminal path token.
            parsed_from_numstat: list[str] = []
            for line in changed_from_numstat:
                parts = line.split("\t")
                if len(parts) >= 3:
                    parsed_from_numstat.append(parts[-1].strip())
            normalized_changed_files = _serialize_required_signals(parsed_from_numstat)

    if normalized_changed_files_count < len(normalized_changed_files):
        normalized_changed_files_count = len(normalized_changed_files)

    def _is_forbidden_changed_file(path_text: str) -> bool:
        normalized_path = _normalize_text(path_text, default="").replace("\\", "/")
        if not normalized_path:
            return False
        lowered = normalized_path.lower()
        if normalized_path.startswith("/") or normalized_path.startswith("../"):
            return True
        if normalized_path.startswith(".git/"):
            return True
        if (
            normalized_path.startswith("prompts/context/")
            and normalized_path not in allowed_changed_set
        ):
            return True
        if normalized_path.startswith("__pycache__/") or "/__pycache__/" in normalized_path:
            return True
        if lowered.endswith(".pyc"):
            return True
        if lowered == ".env" or lowered.startswith(".env.") or "/.env" in lowered:
            return True
        if lowered.endswith(".pem") or lowered.endswith(".key"):
            return True
        if normalized_path.startswith("tmp/") or normalized_path.startswith(".cache/"):
            return True
        return False

    forbidden_changed_files = _serialize_required_signals(
        [path for path in normalized_changed_files if _is_forbidden_changed_file(path)]
    )
    unexpected_changed_files = _serialize_required_signals(
        [
            path
            for path in normalized_changed_files
            if path not in allowed_changed_set and path not in set(forbidden_changed_files)
        ]
    )
    too_many_changed_files = bool(
        normalized_changed_files_count > max_changed_files_threshold
    )

    if normalized_write_invocation_result_status in {"", "insufficient_truth"}:
        status = "blocked_insufficient_truth"
        source_status = "write_result_insufficient_truth"
        block_reason = "write_result_insufficient_truth"
        result_class = "insufficient_truth"
        next_action = "wait_for_more_truth"
        missing_inputs.append("project_browser_autonomous_codex_write_invocation_result_status")
    elif normalized_write_invocation_result_status == "blocked":
        status = "blocked_no_write_invocation_result"
        source_status = "write_result_blocked"
        block_reason = "write_invocation_blocked"
        result_class = "blocked"
        next_action = "wait_for_write_invocation"
    elif not bool(completed):
        status = "blocked_write_invocation_not_completed"
        source_status = "write_invocation_not_completed"
        block_reason = "write_invocation_not_completed"
        result_class = "blocked"
        next_action = "wait_for_write_invocation"
    elif normalized_write_invocation_result_status == "completed_timeout" or bool(timeout):
        status = "assimilated_completed_timeout"
        source_status = "write_invocation_timeout"
        block_reason = "write_invocation_timeout"
        result_class = "invocation_timeout"
        manual_review_required = True
        next_action = "manual_review_required"
    elif normalized_write_invocation_result_status == "completed_failure" or bool(failed):
        status = "assimilated_completed_failure"
        source_status = "write_invocation_failed"
        block_reason = "write_invocation_failed"
        result_class = "invocation_failure"
        manual_review_required = True
        next_action = "manual_review_required"
    elif normalized_write_invocation_result_status == "completed_no_changes":
        status = "assimilated_with_no_changes"
        source_status = "write_invocation_completed_no_changes"
        block_reason = "no_repo_changes_detected"
        result_class = "no_changes"
        manual_review_required = True
        next_action = "manual_review_required"
    elif normalized_write_invocation_result_status == "completed_with_changes":
        if not normalized_changed_files:
            status = "blocked_insufficient_truth"
            source_status = "changed_files_missing"
            block_reason = "changed_files_missing"
            result_class = "insufficient_truth"
            next_action = "wait_for_more_truth"
            missing_inputs.append("changed_files_after")
        elif forbidden_changed_files:
            status = "assimilated_with_forbidden_changes"
            source_status = "forbidden_changed_files_detected"
            block_reason = "forbidden_changed_files_detected"
            result_class = "forbidden_changes"
            manual_review_required = True
            rollback_required = True
            next_action = "manual_review_required"
        elif too_many_changed_files:
            status = "assimilated_too_many_changes"
            source_status = "too_many_changed_files"
            block_reason = "too_many_changed_files"
            result_class = "too_many_changes"
            manual_review_required = True
            next_action = "manual_review_required"
        elif unexpected_changed_files:
            status = "assimilated_with_unexpected_changes"
            source_status = "unexpected_changed_files_detected"
            block_reason = "unexpected_changed_files_detected"
            result_class = "unexpected_changes"
            manual_review_required = True
            next_action = "manual_review_required"
        else:
            status = "assimilated_with_expected_changes"
            source_status = "expected_changed_files_detected"
            block_reason = "none"
            result_class = "expected_changes"
            safe_for_validation_routing = True
            next_action = "route_to_safe_validation_later"
    else:
        status = "blocked_no_write_invocation_result"
        source_status = "write_result_status_unhandled"
        block_reason = (
            f"write_result_status_unhandled:{normalized_write_invocation_result_status}"
        )
        result_class = "blocked"
        next_action = "wait_for_write_invocation"

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if result_class not in allowed_result_classes:
        result_class = "insufficient_truth"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"

    return {
        "project_browser_autonomous_codex_write_result_assimilation_status": status,
        "project_browser_autonomous_codex_write_result_assimilation_source_status": (
            source_status
        ),
        "project_browser_autonomous_codex_write_result_assimilation_block_reason": (
            block_reason
        ),
        "project_browser_autonomous_codex_write_result_assimilation_write_invocation_status": (
            normalized_write_invocation_status
        ),
        "project_browser_autonomous_codex_write_result_assimilation_write_invocation_result_status": (
            normalized_write_invocation_result_status
        ),
        "project_browser_autonomous_codex_write_result_assimilation_smoke_override_status": (
            normalized_smoke_override_status
        ),
        "project_browser_autonomous_codex_write_result_assimilation_smoke_override_used": bool(
            smoke_override_used
        ),
        "project_browser_autonomous_codex_write_result_assimilation_selected_prompt_kind": (
            normalized_selected_prompt_kind
        ),
        "project_browser_autonomous_codex_write_result_assimilation_selected_prompt_path": (
            normalized_selected_prompt_path
        ),
        "project_browser_autonomous_codex_write_result_assimilation_exit_code": int(
            _as_int(exit_code, default=-1)
        ),
        "project_browser_autonomous_codex_write_result_assimilation_timeout": bool(timeout),
        "project_browser_autonomous_codex_write_result_assimilation_completed": bool(
            completed
        ),
        "project_browser_autonomous_codex_write_result_assimilation_failed": bool(failed),
        "project_browser_autonomous_codex_write_result_assimilation_worktree_dirty_after": bool(
            worktree_dirty_after
        ),
        "project_browser_autonomous_codex_write_result_assimilation_changed_files_after": (
            normalized_changed_files
        ),
        "project_browser_autonomous_codex_write_result_assimilation_changed_files_count_after": int(
            normalized_changed_files_count
        ),
        "project_browser_autonomous_codex_write_result_assimilation_expected_changed_files": (
            expected_changed_files
        ),
        "project_browser_autonomous_codex_write_result_assimilation_unexpected_changed_files": (
            unexpected_changed_files
        ),
        "project_browser_autonomous_codex_write_result_assimilation_forbidden_changed_files": (
            forbidden_changed_files
        ),
        "project_browser_autonomous_codex_write_result_assimilation_allowed_changed_files": (
            allowed_changed_files
        ),
        "project_browser_autonomous_codex_write_result_assimilation_too_many_changed_files": bool(
            too_many_changed_files
        ),
        "project_browser_autonomous_codex_write_result_assimilation_result_class": (
            result_class
        ),
        "project_browser_autonomous_codex_write_result_assimilation_safe_for_validation_routing": bool(
            safe_for_validation_routing
        ),
        "project_browser_autonomous_codex_write_result_assimilation_manual_review_required": bool(
            manual_review_required
        ),
        "project_browser_autonomous_codex_write_result_assimilation_rollback_required": bool(
            rollback_required
        ),
        "project_browser_autonomous_codex_write_result_assimilation_next_action": next_action,
        "project_browser_autonomous_codex_write_result_assimilation_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_codex_write_result_assimilation_missing_inputs": (
            _serialize_required_signals(missing_inputs)
        ),
    }

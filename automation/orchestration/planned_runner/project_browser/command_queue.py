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
def _build_project_browser_command_queue_state(
    *,
    browser_executor_interface_status: str,
    browser_executor_mode: str,
    browser_executor_block_reason: str,
    browser_execution_handoff_status: str,
    browser_execution_handoff_kind: str,
    browser_execution_block_reason: str,
    browser_execution_prerequisite_posture: Mapping[str, Any] | None,
    browser_execution_prerequisite_task_envelope: str,
    browser_execution_prerequisite_prompt_payload: str,
    browser_execution_prerequisite_ui_readiness: str,
    browser_execution_prerequisite_selector_contract: str,
    browser_execution_prerequisite_recovery_decision: str,
    browser_execution_prerequisite_handoff_summary: str,
) -> dict[str, Any]:
    interface_status = _normalize_text(
        browser_executor_interface_status,
        default="insufficient_truth",
    )
    interface_mode = _normalize_text(browser_executor_mode, default="none")
    interface_block_reason = _normalize_text(
        browser_executor_block_reason,
        default="insufficient_truth",
    )
    handoff_status = _normalize_text(
        browser_execution_handoff_status,
        default="insufficient_truth",
    )
    handoff_kind = _normalize_text(
        browser_execution_handoff_kind,
        default="none",
    )
    handoff_block_reason = _normalize_text(
        browser_execution_block_reason,
        default="insufficient_truth",
    )
    raw_prerequisites = (
        dict(browser_execution_prerequisite_posture)
        if isinstance(browser_execution_prerequisite_posture, Mapping)
        else {}
    )

    preconditions = {
        "executor_interface": (
            "ready"
            if interface_status == "contract_ready"
            else (
                "inactive"
                if interface_status == "inactive"
                else (
                    "blocked"
                    if interface_status == "blocked"
                    else (
                        "unavailable"
                        if interface_status == "unavailable"
                        else "insufficient_truth"
                    )
                )
            )
        ),
        "source_contract": (
            "ready"
            if handoff_status == "ready"
            else (
                "inactive"
                if handoff_status == "inactive"
                else (
                    "blocked"
                    if handoff_status == "blocked"
                    else (
                        "unavailable"
                        if handoff_status == "unavailable"
                        else "insufficient_truth"
                    )
                )
            )
        ),
        "payload_contract": _normalize_text(
            browser_execution_prerequisite_prompt_payload
            or raw_prerequisites.get("prompt_payload"),
            default="insufficient_truth",
        ),
        "ui_contract": _normalize_text(
            browser_execution_prerequisite_ui_readiness
            or raw_prerequisites.get("ui_readiness"),
            default="insufficient_truth",
        ),
        "selector_contract": _normalize_text(
            browser_execution_prerequisite_selector_contract
            or raw_prerequisites.get("selector_contract"),
            default="insufficient_truth",
        ),
        "recovery_contract": _normalize_text(
            browser_execution_prerequisite_recovery_decision
            or raw_prerequisites.get("recovery_decision"),
            default="insufficient_truth",
        ),
        "handoff_contract": _normalize_text(
            browser_execution_prerequisite_handoff_summary
            or raw_prerequisites.get("handoff_summary"),
            default="insufficient_truth",
        ),
    }
    preconditions["payload_contract"] = (
        preconditions["payload_contract"]
        if preconditions["payload_contract"] in _PROJECT_BROWSER_COMMAND_PRECONDITION_VALUES
        else "insufficient_truth"
    )
    preconditions["ui_contract"] = (
        preconditions["ui_contract"]
        if preconditions["ui_contract"] in _PROJECT_BROWSER_COMMAND_PRECONDITION_VALUES
        else "insufficient_truth"
    )
    preconditions["selector_contract"] = (
        preconditions["selector_contract"]
        if preconditions["selector_contract"] in _PROJECT_BROWSER_COMMAND_PRECONDITION_VALUES
        else "insufficient_truth"
    )
    preconditions["recovery_contract"] = (
        preconditions["recovery_contract"]
        if preconditions["recovery_contract"] in _PROJECT_BROWSER_COMMAND_PRECONDITION_VALUES
        else "insufficient_truth"
    )
    preconditions["handoff_contract"] = (
        preconditions["handoff_contract"]
        if preconditions["handoff_contract"] in _PROJECT_BROWSER_COMMAND_PRECONDITION_VALUES
        else "insufficient_truth"
    )

    queue_status = "insufficient_truth"
    queue_mode = "none"
    command_type = "none"
    command_source = "none"
    block_reason = "insufficient_truth"

    if interface_status not in _PROJECT_BROWSER_EXECUTOR_INTERFACE_STATUSES:
        queue_status = "insufficient_truth"
        block_reason = "insufficient_truth"
    elif interface_status == "inactive":
        queue_status = "inactive"
        queue_mode = "none"
        command_type = "none"
        command_source = "none"
        block_reason = "executor_interface_inactive"
    elif interface_status == "blocked":
        queue_status = "blocked"
        queue_mode = "none"
        command_type = "none"
        command_source = "pr98_executor_interface"
        block_reason = "executor_interface_blocked"
    elif interface_status == "unavailable":
        queue_status = "unavailable"
        queue_mode = "none"
        command_type = "none"
        command_source = "pr98_executor_interface"
        block_reason = "executor_interface_unavailable"
    elif interface_status == "insufficient_truth":
        queue_status = "insufficient_truth"
        queue_mode = "none"
        command_type = "none"
        command_source = "insufficient_truth"
        block_reason = "insufficient_truth"
    elif handoff_status != "ready":
        queue_status = (
            "blocked"
            if handoff_status == "blocked"
            else (
                "unavailable" if handoff_status == "unavailable" else "insufficient_truth"
            )
        )
        queue_mode = "none"
        command_type = "none"
        command_source = "pr97_execution_handoff"
        if handoff_status == "blocked":
            block_reason = (
                "payload_unavailable"
                if handoff_block_reason == "payload_unavailable"
                else (
                    "selector_contract_missing"
                    if handoff_block_reason == "selector_contract_missing"
                    else (
                        "handoff_missing"
                        if handoff_block_reason == "handoff_missing"
                        else (
                            "login_interruption"
                            if handoff_block_reason == "login_interruption"
                            else (
                                "retry_limit_reached"
                                if handoff_block_reason == "retry_limit_reached"
                                else "precondition_missing"
                            )
                        )
                    )
                )
            )
        elif handoff_status == "unavailable":
            block_reason = "precondition_missing"
        else:
            block_reason = "insufficient_truth"
    elif handoff_kind not in _PROJECT_BROWSER_COMMAND_TYPES or handoff_kind == "none":
        queue_status = "blocked"
        queue_mode = "none"
        command_type = "none"
        command_source = "pr97_execution_handoff"
        block_reason = (
            "insufficient_truth"
            if handoff_kind == "none"
            else "unsupported_command_type"
        )
    elif (
        preconditions["payload_contract"] in {"unavailable", "blocked"}
        or preconditions["ui_contract"] in {"unavailable", "blocked"}
        or preconditions["selector_contract"] in {"unavailable", "blocked"}
        or preconditions["recovery_contract"] in {"unavailable", "blocked"}
        or preconditions["handoff_contract"] in {"unavailable", "blocked"}
        or preconditions["payload_contract"] == "insufficient_truth"
        or preconditions["ui_contract"] == "insufficient_truth"
        or preconditions["selector_contract"] == "insufficient_truth"
        or preconditions["recovery_contract"] == "insufficient_truth"
        or preconditions["handoff_contract"] == "insufficient_truth"
    ):
        queue_status = (
            "blocked"
            if (
                preconditions["payload_contract"] in {"unavailable", "blocked"}
                or preconditions["ui_contract"] in {"unavailable", "blocked"}
                or preconditions["selector_contract"] in {"unavailable", "blocked"}
                or preconditions["recovery_contract"] in {"unavailable", "blocked"}
                or preconditions["handoff_contract"] in {"unavailable", "blocked"}
            )
            else "insufficient_truth"
        )
        queue_mode = "none"
        command_type = "none"
        command_source = "pr97_execution_handoff"
        if preconditions["payload_contract"] in {"unavailable", "blocked"}:
            block_reason = "payload_unavailable"
        elif preconditions["selector_contract"] in {"unavailable", "blocked"}:
            block_reason = "selector_contract_missing"
        elif preconditions["handoff_contract"] in {"unavailable", "blocked"}:
            block_reason = "handoff_missing"
        elif preconditions["recovery_contract"] in {"unavailable", "blocked"}:
            block_reason = "precondition_missing"
        elif preconditions["ui_contract"] in {"unavailable", "blocked"}:
            block_reason = "precondition_missing"
        else:
            block_reason = "insufficient_truth"
    else:
        queue_status = "prepared"
        queue_mode = (
            "dry_run_contract_only"
            if interface_mode == "dry_run_contract_only"
            else "single_command"
        )
        command_type = handoff_kind
        command_source = (
            "handoff_contract"
            if handoff_kind == "new_chat_handoff"
            else (
                "recovery_candidate"
                if handoff_kind
                in {
                    "same_chat_retry",
                    "resend_same_prompt",
                    "page_reload",
                    "pause_for_login",
                    "escalate",
                }
                else "pr97_execution_handoff"
            )
        )
        block_reason = "none"

    if queue_status not in _PROJECT_BROWSER_COMMAND_QUEUE_STATUSES:
        queue_status = "insufficient_truth"
    if queue_mode not in _PROJECT_BROWSER_COMMAND_QUEUE_MODES:
        queue_mode = "none"
    if command_type not in _PROJECT_BROWSER_COMMAND_TYPES:
        command_type = "none"
    if command_source not in _PROJECT_BROWSER_COMMAND_SOURCES:
        command_source = "insufficient_truth"
    if block_reason not in _PROJECT_BROWSER_COMMAND_BLOCK_REASONS:
        block_reason = "insufficient_truth"

    receipt_status = "insufficient_truth"
    receipt_kind = "none"
    receipt_result = "insufficient_truth"
    if queue_status == "prepared":
        receipt_status = "dry_run_ready"
        receipt_kind = (
            "dry_run_command_receipt"
            if queue_mode == "dry_run_contract_only"
            else "non_execution_command_receipt"
        )
        receipt_result = "not_executed"
    elif queue_status in {"inactive", "empty"}:
        receipt_status = "not_created"
        receipt_kind = "none"
        receipt_result = "not_executed"
    elif queue_status == "blocked":
        receipt_status = "blocked"
        receipt_kind = "none"
        receipt_result = "blocked"
    elif queue_status == "unavailable":
        receipt_status = "unavailable"
        receipt_kind = "none"
        receipt_result = "unavailable"
    else:
        receipt_status = "insufficient_truth"
        receipt_kind = "none"
        receipt_result = "insufficient_truth"

    if receipt_status not in _PROJECT_BROWSER_COMMAND_RECEIPT_STATUSES:
        receipt_status = "insufficient_truth"
    if receipt_kind not in _PROJECT_BROWSER_COMMAND_RECEIPT_KINDS:
        receipt_kind = "none"
    if receipt_result not in _PROJECT_BROWSER_COMMAND_RECEIPT_RESULTS:
        receipt_result = "insufficient_truth"

    runtime_posture = [
        "metadata_only",
        "no_playwright_execution",
        "no_browser_open",
        "no_dom_interaction",
        "no_browser_send",
        "no_response_wait",
        "no_retry_execution",
        "no_reload_execution",
        "no_new_chat_execution",
        "no_login_recovery",
        "no_external_operation",
    ]
    runtime_posture = [
        token
        for token in runtime_posture
        if token in _PROJECT_BROWSER_COMMAND_RUNTIME_POSTURES
    ]

    return {
        "project_browser_command_queue_status": queue_status,
        "project_browser_command_queue_mode": queue_mode,
        "project_browser_command_type": command_type,
        "project_browser_command_source": command_source,
        "project_browser_command_precondition_posture": preconditions,
        "project_browser_command_precondition_executor_interface": preconditions.get(
            "executor_interface",
            "insufficient_truth",
        ),
        "project_browser_command_precondition_source_contract": preconditions.get(
            "source_contract",
            "insufficient_truth",
        ),
        "project_browser_command_precondition_payload_contract": preconditions.get(
            "payload_contract",
            "insufficient_truth",
        ),
        "project_browser_command_precondition_ui_contract": preconditions.get(
            "ui_contract",
            "insufficient_truth",
        ),
        "project_browser_command_precondition_selector_contract": preconditions.get(
            "selector_contract",
            "insufficient_truth",
        ),
        "project_browser_command_precondition_recovery_contract": preconditions.get(
            "recovery_contract",
            "insufficient_truth",
        ),
        "project_browser_command_precondition_handoff_contract": preconditions.get(
            "handoff_contract",
            "insufficient_truth",
        ),
        "project_browser_command_block_reason": block_reason,
        "project_browser_command_receipt_status": receipt_status,
        "project_browser_command_receipt_kind": receipt_kind,
        "project_browser_command_receipt_result": receipt_result,
        "project_browser_command_receipt_runtime_posture": runtime_posture,
        "project_browser_command_runtime_metadata_only": True,
        "project_browser_command_runtime_no_playwright_execution": True,
        "project_browser_command_runtime_no_browser_open": True,
        "project_browser_command_runtime_no_dom_interaction": True,
        "project_browser_command_runtime_no_browser_send": True,
        "project_browser_command_runtime_no_response_wait": True,
        "project_browser_command_runtime_no_retry_execution": True,
        "project_browser_command_runtime_no_reload_execution": True,
        "project_browser_command_runtime_no_new_chat_execution": True,
        "project_browser_command_runtime_no_login_recovery": True,
        "project_browser_command_runtime_no_external_operation": True,
    }

def _build_project_browser_one_command_finalizer_state(
    *,
    browser_task_status: str,
    browser_command_queue_status: str,
    browser_command_type: str,
    browser_command_receipt_status: str,
    browser_launch_status: str,
    browser_prompt_send_status: str,
    browser_response_wait_status: str,
    browser_response_wait_block_reason: str,
    browser_response_json_parse_status: str,
    browser_execution_receipt_status: str,
    browser_execution_result_status: str,
    browser_recovery_status: str,
    browser_recovery_action: str,
    browser_recovery_receipt_status: str,
) -> dict[str, Any]:
    task_status = _normalize_text(browser_task_status, default="inactive")
    queue_status = _normalize_text(browser_command_queue_status, default="insufficient_truth")
    command_type = _normalize_text(browser_command_type, default="none")
    command_receipt_status = _normalize_text(
        browser_command_receipt_status,
        default="insufficient_truth",
    )
    launch_status = _normalize_text(browser_launch_status, default="insufficient_truth")
    prompt_send_status = _normalize_text(browser_prompt_send_status, default="insufficient_truth")
    response_wait_status = _normalize_text(
        browser_response_wait_status,
        default="insufficient_truth",
    )
    response_wait_block_reason = _normalize_text(
        browser_response_wait_block_reason,
        default="insufficient_truth",
    )
    parse_status = _normalize_text(
        browser_response_json_parse_status,
        default="insufficient_truth",
    )
    execution_receipt_status = _normalize_text(
        browser_execution_receipt_status,
        default="insufficient_truth",
    )
    execution_result_status = _normalize_text(
        browser_execution_result_status,
        default="insufficient_truth",
    )
    recovery_status = _normalize_text(browser_recovery_status, default="insufficient_truth")
    recovery_action = _normalize_text(browser_recovery_action, default="none")
    recovery_receipt_status = _normalize_text(
        browser_recovery_receipt_status,
        default="insufficient_truth",
    )

    status = "insufficient_truth"
    result = "insufficient_truth"
    stop_reason = "insufficient_truth"
    receipt_status = "insufficient_truth"
    receipt_kind = "none"

    if (
        queue_status == "inactive"
        or task_status == "inactive"
        or command_type == "none"
        or queue_status == "empty"
    ):
        status = "inactive"
        result = "none"
        stop_reason = "none"
        receipt_status = "not_created"
    elif queue_status in {"insufficient_truth", "unavailable"}:
        status = "insufficient_truth"
        result = "insufficient_truth"
        stop_reason = "insufficient_truth"
        receipt_status = "insufficient_truth"
    elif queue_status == "blocked":
        status = "blocked"
        result = "blocked"
        stop_reason = "blocked_by_precondition"
        receipt_status = "blocked"
        receipt_kind = "one_command_blocked_receipt"
    elif recovery_status == "pause_required" or recovery_action == "pause_for_login":
        status = "pause_required"
        result = "pause_for_login"
        stop_reason = "pause_for_login"
        receipt_status = "pause_required"
        receipt_kind = "one_command_pause_for_login_receipt"
    elif recovery_status == "recovered" and recovery_receipt_status == "recovered":
        status = "completed_with_recovery"
        result = "recovered"
        stop_reason = "recovery_completed"
        receipt_status = "final_ready"
        receipt_kind = "one_command_recovery_receipt"
    elif parse_status == "valid" and execution_receipt_status == "parsed":
        status = "completed"
        result = "success"
        stop_reason = "command_completed"
        receipt_status = "final_ready"
        receipt_kind = "one_command_success_receipt"
    elif (
        parse_status == "invalid_response"
        or execution_receipt_status == "invalid_response"
        or execution_result_status == "invalid_response"
    ):
        status = "completed"
        result = "invalid_response"
        stop_reason = "invalid_response"
        receipt_status = "final_ready"
        receipt_kind = "one_command_invalid_response_receipt"
    elif (
        response_wait_status == "timeout"
        or response_wait_block_reason == "response_timeout"
    ):
        status = "completed"
        result = "timeout"
        stop_reason = "timeout"
        receipt_status = "final_ready"
        receipt_kind = "one_command_failed_receipt"
    elif recovery_status == "failed" or parse_status in {"failed"} or execution_receipt_status in {"failed"}:
        status = "failed"
        result = "failed"
        stop_reason = "runtime_failed"
        receipt_status = "failed"
        receipt_kind = "one_command_failed_receipt"
    elif (
        recovery_status == "blocked"
        or parse_status in {"blocked", "unavailable", "not_attempted", "inactive"}
        or execution_receipt_status in {"blocked", "unavailable", "not_created"}
        or prompt_send_status in {"blocked", "failed", "not_attempted"}
        or launch_status in {"blocked", "failed"}
        or command_receipt_status in {"blocked", "unavailable"}
    ):
        status = "blocked"
        result = "blocked"
        stop_reason = "blocked_by_precondition"
        receipt_status = "blocked"
        receipt_kind = "one_command_blocked_receipt"
    elif (
        recovery_status == "insufficient_truth"
        or parse_status == "insufficient_truth"
        or execution_receipt_status == "insufficient_truth"
        or prompt_send_status == "insufficient_truth"
        or launch_status == "insufficient_truth"
        or command_receipt_status == "insufficient_truth"
    ):
        status = "insufficient_truth"
        result = "insufficient_truth"
        stop_reason = "insufficient_truth"
        receipt_status = "insufficient_truth"
    else:
        status = "insufficient_truth"
        result = "insufficient_truth"
        stop_reason = "insufficient_truth"
        receipt_status = "insufficient_truth"

    if status not in _PROJECT_BROWSER_ONE_COMMAND_EXECUTOR_STATUSES:
        status = "insufficient_truth"
    if result not in _PROJECT_BROWSER_ONE_COMMAND_EXECUTOR_RESULTS:
        result = "insufficient_truth"
    if stop_reason not in _PROJECT_BROWSER_ONE_COMMAND_STOP_REASONS:
        stop_reason = "insufficient_truth"
    if receipt_status not in _PROJECT_BROWSER_ONE_COMMAND_RECEIPT_STATUSES:
        receipt_status = "insufficient_truth"
    if receipt_kind not in _PROJECT_BROWSER_ONE_COMMAND_RECEIPT_KINDS:
        receipt_kind = "none"

    runtime_posture = [
        "no_additional_browser_action",
        "no_second_command",
        "no_queue_drain",
        "no_prompt_generation",
        "no_refill",
        "no_resend",
        "no_response_rewait",
        "no_json_reparse",
        "no_decision_execution",
        "no_retry_loop",
        "no_repair_execution",
        "no_restart_execution",
        "no_approval_execution",
        "no_background_loop",
    ]
    runtime_posture = [
        token
        for token in runtime_posture
        if token in _PROJECT_BROWSER_ONE_COMMAND_RUNTIME_POSTURES
    ]
    return {
        "project_browser_one_command_executor_status": status,
        "project_browser_one_command_executor_result": result,
        "project_browser_one_command_executor_stop_reason": stop_reason,
        "project_browser_one_command_executor_receipt_status": receipt_status,
        "project_browser_one_command_executor_receipt_kind": receipt_kind,
        "project_browser_one_command_executor_runtime_posture": runtime_posture,
        "project_browser_one_command_executor_runtime_no_additional_browser_action": True,
        "project_browser_one_command_executor_runtime_no_second_command": True,
        "project_browser_one_command_executor_runtime_no_queue_drain": True,
        "project_browser_one_command_executor_runtime_no_prompt_generation": True,
        "project_browser_one_command_executor_runtime_no_refill": True,
        "project_browser_one_command_executor_runtime_no_resend": True,
        "project_browser_one_command_executor_runtime_no_response_rewait": True,
        "project_browser_one_command_executor_runtime_no_json_reparse": True,
        "project_browser_one_command_executor_runtime_no_decision_execution": True,
        "project_browser_one_command_executor_runtime_no_retry_loop": True,
        "project_browser_one_command_executor_runtime_no_repair_execution": True,
        "project_browser_one_command_executor_runtime_no_restart_execution": True,
        "project_browser_one_command_executor_runtime_no_approval_execution": True,
        "project_browser_one_command_executor_runtime_no_background_loop": True,
    }

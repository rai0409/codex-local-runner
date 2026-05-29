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
def _build_project_browser_handoff_compile_state(
    *,
    browser_task_status: str,
    browser_chat_rotation_due: bool,
    browser_handoff_summary_required: bool,
    browser_handoff_summary_available: bool,
    browser_prompt_payload_status: str,
    browser_prompt_payload_sections: list[Mapping[str, Any]] | None,
    browser_response_assimilation_status: str,
    browser_next_action_posture: str,
    browser_recovery_decision_status: str,
    browser_recovery_candidate: str,
    browser_handoff_dependency_posture: str,
    project_planning_summary_status: str,
    objective_completion_posture: str,
    project_failure_memory_status: str,
    project_autonomy_budget_status: str,
    project_external_boundary_status: str,
    project_blocked_objective_deferral_posture: str,
    project_human_escalation_required: bool,
) -> dict[str, Any]:
    task_status = _normalize_text(browser_task_status, default="inactive")
    prompt_payload_status = _normalize_text(
        browser_prompt_payload_status,
        default="insufficient_truth",
    )
    assimilation_status = _normalize_text(
        browser_response_assimilation_status,
        default="insufficient_truth",
    )
    next_action_posture = _normalize_text(
        browser_next_action_posture,
        default="no_action",
    )
    recovery_decision_status = _normalize_text(
        browser_recovery_decision_status,
        default="insufficient_truth",
    )
    recovery_candidate = _normalize_text(
        browser_recovery_candidate,
        default="none",
    )
    handoff_dependency_posture = _normalize_text(
        browser_handoff_dependency_posture,
        default="insufficient_truth",
    )
    completion_posture = _normalize_text(
        objective_completion_posture,
        default="objective_insufficient_truth",
    )
    planning_summary_status = _normalize_text(
        project_planning_summary_status,
        default="insufficient_truth",
    )
    failure_memory_status = _normalize_text(
        project_failure_memory_status,
        default="insufficient_truth",
    )
    autonomy_budget_status = _normalize_text(
        project_autonomy_budget_status,
        default="insufficient_truth",
    )
    external_boundary_status = _normalize_text(
        project_external_boundary_status,
        default="insufficient_truth",
    )
    blocked_objective_deferral_posture = _normalize_text(
        project_blocked_objective_deferral_posture,
        default="insufficient_truth",
    )

    prompt_sections = [
        dict(entry)
        for entry in (browser_prompt_payload_sections or [])
        if isinstance(entry, Mapping)
    ]
    prompt_section_available: dict[str, bool] = {}
    for entry in prompt_sections:
        section_name = _normalize_text(entry.get("section"), default="")
        if not section_name:
            continue
        prompt_section_available[section_name] = bool(entry.get("available", False))

    section_availability = {
        "project_summary": bool(
            prompt_section_available.get("project_brief_summary", False)
            and planning_summary_status == "available"
        ),
        "active_objective_summary": bool(
            prompt_section_available.get("active_objective_summary", False)
            and completion_posture == "objective_active"
        ),
        "completed_objective_summary": bool(completion_posture == "objective_completed"),
        "blocked_items": bool(
            blocked_objective_deferral_posture == "deferred"
            or bool(project_human_escalation_required)
            or completion_posture == "objective_blocked"
        ),
        "failure_memory_summary": bool(
            prompt_section_available.get("failure_memory_summary", False)
            and failure_memory_status == "available"
        ),
        "current_budgets_limits": bool(
            prompt_section_available.get("budget_boundary_summary", False)
            and autonomy_budget_status == "available"
        ),
        "current_repo_constraints": bool(
            prompt_section_available.get("current_constraints_summary", False)
            and external_boundary_status == "available"
        ),
        "next_intended_action": bool(
            next_action_posture in _PROJECT_BROWSER_NEXT_ACTION_POSTURES - {"no_action"}
            or prompt_section_available.get("requested_task_type", False)
        ),
    }
    sections_status: list[dict[str, Any]] = []
    for section_name in _PROJECT_BROWSER_HANDOFF_SECTION_NAMES:
        available = bool(section_availability.get(section_name, False))
        sections_status.append(
            {
                "section": section_name,
                "available": available,
                "status": "available" if available else "insufficient_truth",
            }
        )
    sections_available_count = sum(
        1 for section in sections_status if bool(section.get("available", False))
    )

    objective_summary_available = bool(
        section_availability.get("active_objective_summary", False)
        or section_availability.get("completed_objective_summary", False)
    )
    missing_required_sections = _serialize_required_signals(
        [
            "project_summary"
            if not section_availability.get("project_summary", False)
            else "",
            "objective_summary" if not objective_summary_available else "",
            "current_budgets_limits"
            if not section_availability.get("current_budgets_limits", False)
            else "",
            "current_repo_constraints"
            if not section_availability.get("current_repo_constraints", False)
            else "",
            "next_intended_action"
            if not section_availability.get("next_intended_action", False)
            else "",
        ]
    )

    compile_status = "inactive"
    handoff_trigger = "none"
    payload_posture = "unavailable"
    handoff_required = bool(
        browser_chat_rotation_due or recovery_candidate == "new_chat_handoff"
    )

    if (
        task_status not in _PROJECT_BROWSER_TASK_STATUSES
        or prompt_payload_status not in _PROJECT_BROWSER_PROMPT_PAYLOAD_STATUSES
        or assimilation_status not in _PROJECT_BROWSER_RESPONSE_ASSIMILATION_STATUSES
        or next_action_posture not in _PROJECT_BROWSER_NEXT_ACTION_POSTURES
        or recovery_decision_status not in _PROJECT_BROWSER_UI_RECOVERY_DECISION_STATUSES
        or recovery_candidate not in _PROJECT_BROWSER_UI_RECOVERY_CANDIDATES
        or handoff_dependency_posture not in _PROJECT_BROWSER_UI_HANDOFF_DEPENDENCY_POSTURES
    ):
        compile_status = "insufficient_truth"
        handoff_trigger = "insufficient_truth"
        payload_posture = "insufficient_truth"
    elif task_status == "inactive" or recovery_decision_status == "inactive":
        compile_status = "inactive"
        handoff_trigger = "none"
        payload_posture = "unavailable"
    elif not handoff_required:
        compile_status = "not_required"
        handoff_trigger = "none"
        payload_posture = "unavailable"
    else:
        if (
            handoff_dependency_posture == "required_missing"
            or (
                browser_handoff_summary_required
                and not browser_handoff_summary_available
                and recovery_candidate != "new_chat_handoff"
            )
        ):
            compile_status = "unavailable"
            handoff_trigger = "manual_required"
            payload_posture = "unavailable"
        elif (
            prompt_payload_status == "insufficient_truth"
            or assimilation_status == "insufficient_truth"
            or handoff_dependency_posture == "insufficient_truth"
        ):
            compile_status = "insufficient_truth"
            handoff_trigger = "insufficient_truth"
            payload_posture = "insufficient_truth"
        elif missing_required_sections:
            compile_status = "unavailable"
            handoff_trigger = (
                "new_chat_handoff_recovery"
                if recovery_candidate == "new_chat_handoff"
                else "rotation_due"
            )
            payload_posture = "missing_required_sections"
        else:
            compile_status = "ready"
            handoff_trigger = (
                "new_chat_handoff_recovery"
                if recovery_candidate == "new_chat_handoff"
                else "rotation_due"
            )
            payload_posture = "compact_ready"

    if compile_status not in _PROJECT_BROWSER_HANDOFF_COMPILE_STATUSES:
        compile_status = "insufficient_truth"
    if handoff_trigger not in _PROJECT_BROWSER_HANDOFF_TRIGGERS:
        handoff_trigger = "insufficient_truth"
    if payload_posture not in _PROJECT_BROWSER_HANDOFF_PAYLOAD_POSTURES:
        payload_posture = "insufficient_truth"

    runtime_posture = [
        "metadata_only",
        "no_new_chat_execution",
        "no_browser_send",
        "no_dom_read",
        "no_session_check",
        "no_handoff_delivery",
    ]
    return {
        "project_browser_handoff_compile_status": compile_status,
        "project_browser_handoff_trigger": handoff_trigger,
        "project_browser_handoff_sections_status": sections_status,
        "project_browser_handoff_sections_available_count": sections_available_count,
        "project_browser_handoff_missing_required_sections": missing_required_sections,
        "project_browser_handoff_payload_posture": payload_posture,
        "project_browser_handoff_runtime_posture": runtime_posture,
        "project_browser_handoff_runtime_metadata_only": True,
        "project_browser_handoff_runtime_no_new_chat_execution": True,
        "project_browser_handoff_runtime_no_browser_send": True,
        "project_browser_handoff_runtime_no_dom_read": True,
        "project_browser_handoff_runtime_no_session_check": True,
        "project_browser_handoff_runtime_no_handoff_delivery": True,
    }

def _build_project_browser_autonomous_bounded_multistep_handoff_guard_state(
    *,
    direct_retrigger_followup_guard_status: str,
    followup_guard_available: bool,
    followup_guard_allowed: bool,
    followup_guard_block_reason: str,
    followup_guard_source: str,
    selected_followup_kind: str,
    selected_followup_action: str,
    selected_followup_payload: Any,
    exactly_one_followup_target: bool,
    followup_conflict_detected: bool,
    conflicting_followup_targets: Sequence[Any],
    continue_to_result_assimilation_chain: bool,
    continue_to_bounded_multi_step_coordinator: bool,
    manual_stop_followup: bool,
    blocked_followup: bool,
    fresh_attempt_followup_allowed: bool,
    existing_truth_followup_allowed: bool,
    stale_truth_followup_blocked: bool,
    not_callable_followup_blocked: bool,
    source_result_class: str,
    source_selected_retrigger_kind: str,
    source_retrigger_status: str,
    terminal_result_detected: bool,
    terminal_result_source: str,
    cycle_budget_remaining: int,
    codex_budget_remaining: int,
    rollback_budget_remaining: int,
    commit_budget_remaining: int,
    budget_checked: bool,
    prompt217_multistep_ready: bool,
    prompt217_multistep_source: str,
    prompt217_multistep_contract: Any,
    should_continue_local_loop: bool,
    should_start_unbounded_loop: bool,
    should_prepare_result_assimilation_chain: bool,
    should_prepare_next_controller_decision: bool,
    should_invoke_codex: bool,
    should_execute_rollback: bool,
    should_execute_commit: bool,
    should_push: bool,
    manual_review_required: bool,
    should_stop: bool,
    stop_reason: str,
    next_action: str,
    direct_retrigger_result_assimilation_status: str,
    direct_retrigger_coordinator_status: str,
    stale_fresh_ordering_gate_status: str,
    one_bounded_continuation_coordinator_status: str,
    final_runtime_continuation_guard_status: str,
    multi_cycle_controller_status: str,
    codex_reentry_invocation_status: str,
    rollback_execution_status: str,
    rollback_result_assimilation_status: str,
    commit_tag_execution_status: str,
    commit_tag_result_assimilation_status: str,
    fix_prompt_generation_status: str,
    next_prompt_generation_status: str,
) -> dict[str, Any]:
    allowed_statuses = {
        "bounded_multistep_handoff_guard_ready",
        "bounded_multistep_handoff_guard_result_assimilation_ready",
        "bounded_multistep_handoff_guard_manual_stop",
        "bounded_multistep_handoff_guard_blocked",
        "bounded_multistep_handoff_guard_blocked_conflict",
        "bounded_multistep_handoff_guard_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "prepare_bounded_multi_step_execution",
        "prepare_result_assimilation_chain",
        "manual_review_required",
        "insufficient_truth",
    }
    runtime_posture = [
        "prompt217_bounded_multistep_handoff_guard",
        "metadata_only",
        "multistep_handoff_guard_only",
        "contract_revalidation",
        "no_execution",
        "no_retry",
        "no_loop",
        "no_push",
        "no_github_mutation",
    ]

    normalized_status = _normalize_text(
        direct_retrigger_followup_guard_status,
        default="insufficient_truth",
    )
    normalized_followup_block_reason = _normalize_text(followup_guard_block_reason, default="")
    normalized_followup_source = _normalize_text(followup_guard_source, default="")
    normalized_selected_followup_kind = _normalize_text(selected_followup_kind, default="")
    normalized_selected_followup_action = _normalize_text(
        selected_followup_action,
        default="manual_review_required",
    )
    normalized_source_result_class = _normalize_text(source_result_class, default="")
    normalized_source_selected_retrigger_kind = _normalize_text(
        source_selected_retrigger_kind,
        default="",
    )
    normalized_source_retrigger_status = _normalize_text(source_retrigger_status, default="")
    normalized_terminal_result_source = _normalize_text(terminal_result_source, default="")
    normalized_stop_reason = _normalize_text(stop_reason, default="")
    normalized_next_action = _normalize_text(next_action, default="manual_review_required")
    normalized_result_assimilation_status = _normalize_text(
        direct_retrigger_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_direct_coordinator_status = _normalize_text(
        direct_retrigger_coordinator_status,
        default="insufficient_truth",
    )
    normalized_stale_gate_status = _normalize_text(
        stale_fresh_ordering_gate_status,
        default="insufficient_truth",
    )
    normalized_one_bounded_status = _normalize_text(
        one_bounded_continuation_coordinator_status,
        default="insufficient_truth",
    )
    normalized_final_guard_status = _normalize_text(
        final_runtime_continuation_guard_status,
        default="insufficient_truth",
    )
    normalized_multi_cycle_status = _normalize_text(
        multi_cycle_controller_status,
        default="insufficient_truth",
    )
    normalized_codex_reentry_status = _normalize_text(
        codex_reentry_invocation_status,
        default="insufficient_truth",
    )
    normalized_rollback_execution_status = _normalize_text(
        rollback_execution_status,
        default="insufficient_truth",
    )
    normalized_rollback_result_assimilation_status = _normalize_text(
        rollback_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_commit_execution_status = _normalize_text(
        commit_tag_execution_status,
        default="insufficient_truth",
    )
    normalized_commit_result_assimilation_status = _normalize_text(
        commit_tag_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_fix_generation_status = _normalize_text(
        fix_prompt_generation_status,
        default="insufficient_truth",
    )
    normalized_next_generation_status = _normalize_text(
        next_prompt_generation_status,
        default="insufficient_truth",
    )

    normalized_selected_followup_payload = (
        dict(selected_followup_payload)
        if isinstance(selected_followup_payload, Mapping)
        else {}
    )
    normalized_prompt217_contract = (
        dict(prompt217_multistep_contract)
        if isinstance(prompt217_multistep_contract, Mapping)
        else {}
    )
    normalized_conflicting_followup_targets = _normalize_string_list(
        conflicting_followup_targets
    )

    out_cycle_budget_remaining = _as_non_negative_int(cycle_budget_remaining, default=0)
    out_codex_budget_remaining = _as_non_negative_int(codex_budget_remaining, default=0)
    out_rollback_budget_remaining = _as_non_negative_int(rollback_budget_remaining, default=0)
    out_commit_budget_remaining = _as_non_negative_int(commit_budget_remaining, default=0)
    out_budget_checked = bool(budget_checked)

    source_status_indicates_manual = (
        normalized_status == "direct_retrigger_followup_guard_manual_stop"
    )
    source_status_indicates_blocked = "blocked" in normalized_status
    source_status_indicates_result_assimilation = (
        normalized_status == "direct_retrigger_followup_guard_result_assimilation_ready"
    )
    source_status_indicates_multistep_ready = (
        normalized_status == "direct_retrigger_followup_guard_multistep_ready"
    )

    authoritative_selected = bool(
        bool(normalized_status)
        and (
            bool(followup_guard_available)
            or source_status_indicates_manual
            or source_status_indicates_blocked
        )
        and (
            bool(normalized_selected_followup_kind)
            or source_status_indicates_manual
            or source_status_indicates_blocked
        )
        and (
            source_status_indicates_multistep_ready
            or source_status_indicates_result_assimilation
            or source_status_indicates_manual
            or source_status_indicates_blocked
            or normalized_status in {"insufficient_truth"}
        )
    )

    contract_kind = _normalize_text(
        normalized_prompt217_contract.get("contract_kind"),
        default="",
    )
    contract_source = _normalize_text(
        normalized_prompt217_contract.get("source"),
        default="",
    )
    contract_selected_followup_kind = _normalize_text(
        normalized_prompt217_contract.get("selected_followup_kind"),
        default="",
    )
    max_next_steps = _as_non_negative_int(
        normalized_prompt217_contract.get("max_next_steps"),
        default=0,
    )
    allow_unbounded_loop = bool(
        normalized_prompt217_contract.get("allow_unbounded_loop", True)
    )
    allow_retry = bool(normalized_prompt217_contract.get("allow_retry", False))
    requires_stop_policy_guard = bool(
        normalized_prompt217_contract.get("requires_stop_policy_guard", False)
    )
    requires_budget_guard = bool(
        normalized_prompt217_contract.get("requires_budget_guard", False)
    )
    requires_result_assimilation = bool(
        normalized_prompt217_contract.get("requires_result_assimilation", False)
    )
    contract_next_action = _normalize_text(
        normalized_prompt217_contract.get("next_action"),
        default="",
    )

    prompt217_contract_valid = bool(
        bool(prompt217_multistep_ready)
        and _normalize_text(
            prompt217_multistep_source,
            default="",
        )
        == "prompt216_direct_retrigger_followup_guard"
        and isinstance(prompt217_multistep_contract, Mapping)
        and contract_kind == "bounded_multi_step_preflight"
        and contract_source == "prompt216_direct_retrigger_followup_guard"
        and contract_selected_followup_kind == "bounded_multi_step_coordinator"
        and not allow_unbounded_loop
        and max_next_steps == 1
        and bool(requires_stop_policy_guard)
        and bool(requires_budget_guard)
        and bool(requires_result_assimilation)
        and contract_next_action == "prepare_bounded_multi_step_coordinator"
    )

    fresh_attempt_detected = bool(fresh_attempt_followup_allowed)
    existing_truth_surface_detected = bool(existing_truth_followup_allowed)

    multistep_guard_allowed = bool(
        prompt217_contract_valid
        and bool(followup_guard_allowed)
        and bool(continue_to_bounded_multi_step_coordinator)
        and bool(exactly_one_followup_target)
        and not bool(followup_conflict_detected)
        and bool(out_budget_checked)
        and out_cycle_budget_remaining > 0
        and not bool(manual_review_required)
        and not bool(should_stop)
        and not bool(should_start_unbounded_loop)
        and not bool(should_continue_local_loop)
        and not bool(should_invoke_codex)
        and not bool(should_execute_rollback)
        and not bool(should_execute_commit)
        and not bool(should_push)
        and not bool(stale_truth_followup_blocked)
        and not bool(not_callable_followup_blocked)
        and not bool(blocked_followup)
        and not bool(manual_stop_followup)
        and bool(terminal_result_detected)
        and normalized_source_result_class
        in {"completed_fresh_attempt", "completed_existing_truth_surface"}
    )

    status = "bounded_multistep_handoff_guard_blocked_insufficient_truth"
    multistep_guard_available = False
    out_multistep_guard_allowed = False
    multistep_guard_block_reason = "blocked_insufficient_multistep_handoff_truth"
    multistep_guard_source = "prompt216_direct_retrigger_followup_guard"
    selected_handoff_kind = "blocked"
    selected_handoff_action = "manual_review_required"
    selected_handoff_payload: dict[str, Any] = {}
    exactly_one_handoff_target = False
    handoff_conflict_detected = False
    conflicting_handoff_targets: list[str] = []
    bounded_multistep_handoff_ready = False
    result_assimilation_handoff_ready = False
    manual_stop_handoff_ready = False
    blocked_handoff_ready = True
    prompt218_multistep_execution_ready = False
    prompt218_multistep_execution_source = ""
    prompt218_multistep_execution_contract: dict[str, Any] = {}
    out_should_continue_local_loop = False
    out_should_start_unbounded_loop = False
    out_should_invoke_codex = False
    out_should_execute_rollback = False
    out_should_execute_commit = False
    out_should_push = False
    out_manual_review_required = True
    out_should_stop = True
    out_stop_reason = normalized_stop_reason or "insufficient_multistep_handoff_truth"
    out_next_action = "manual_review_required"

    manual_stop_candidate = bool(
        bool(manual_stop_followup) or bool(manual_review_required) or bool(should_stop)
    )
    blocked_candidate = bool(
        bool(blocked_followup)
        or bool(stale_truth_followup_blocked)
        or bool(not_callable_followup_blocked)
        or normalized_source_result_class
        in {
            "blocked_stale_truth_only",
            "blocked_existing_path_not_callable",
            "blocked_non_selected_retrigger_activity",
            "failed",
            "blocked",
            "insufficient_truth",
        }
        or source_status_indicates_blocked
    )

    if not authoritative_selected:
        status = "bounded_multistep_handoff_guard_blocked_insufficient_truth"
        multistep_guard_available = False
        out_multistep_guard_allowed = False
        multistep_guard_block_reason = "blocked_prompt216_not_authoritative"
        blocked_handoff_ready = True
    elif manual_stop_candidate:
        status = "bounded_multistep_handoff_guard_manual_stop"
        multistep_guard_available = True
        out_multistep_guard_allowed = False
        multistep_guard_block_reason = "blocked_manual_review_required"
        selected_handoff_kind = "manual_stop"
        selected_handoff_action = "manual_review_required"
        selected_handoff_payload = {
            "handoff_kind": "manual_stop",
            "source": "prompt217_bounded_multistep_handoff_guard",
            "stop_reason": normalized_stop_reason or "manual_stop",
            "next_action": "manual_review_required",
        }
        exactly_one_handoff_target = True
        manual_stop_handoff_ready = True
        blocked_handoff_ready = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = normalized_stop_reason or "manual_stop"
        out_next_action = "manual_review_required"
    else:
        non_stop_candidates: list[str] = []
        if multistep_guard_allowed:
            non_stop_candidates.append("bounded_multi_step_execution")
        if bool(continue_to_result_assimilation_chain) and not multistep_guard_allowed:
            non_stop_candidates.append("result_assimilation_chain")

        if len(non_stop_candidates) > 1:
            status = "bounded_multistep_handoff_guard_blocked_conflict"
            multistep_guard_available = True
            out_multistep_guard_allowed = False
            multistep_guard_block_reason = "blocked_followup_conflict"
            selected_handoff_kind = "blocked"
            selected_handoff_action = "manual_review_required"
            selected_handoff_payload = {
                "handoff_kind": "blocked",
                "source": "prompt217_bounded_multistep_handoff_guard",
                "stop_reason": "conflicting_handoff_targets",
                "next_action": "manual_review_required",
            }
            handoff_conflict_detected = True
            conflicting_handoff_targets = sorted(non_stop_candidates)
            blocked_handoff_ready = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = "conflicting_handoff_targets"
            out_next_action = "manual_review_required"
        elif len(non_stop_candidates) == 1 and non_stop_candidates[0] == "bounded_multi_step_execution":
            status = "bounded_multistep_handoff_guard_ready"
            multistep_guard_available = True
            out_multistep_guard_allowed = True
            multistep_guard_block_reason = ""
            selected_handoff_kind = "bounded_multi_step_execution"
            selected_handoff_action = "prepare_bounded_multi_step_execution"
            selected_handoff_payload = {
                "handoff_kind": "bounded_multi_step_execution",
                "source": "prompt217_bounded_multistep_handoff_guard",
                "source_result_class": normalized_source_result_class,
                "source_selected_retrigger_kind": normalized_source_selected_retrigger_kind,
                "fresh_attempt_detected": bool(fresh_attempt_detected),
                "existing_truth_surface_detected": bool(
                    existing_truth_surface_detected
                ),
                "next_action": "prepare_bounded_multi_step_execution",
            }
            exactly_one_handoff_target = True
            bounded_multistep_handoff_ready = True
            blocked_handoff_ready = False
            out_manual_review_required = False
            out_should_stop = False
            out_stop_reason = ""
            out_next_action = "prepare_bounded_multi_step_execution"
            prompt218_multistep_execution_ready = True
            prompt218_multistep_execution_source = (
                "prompt217_bounded_multistep_handoff_guard"
            )
            prompt218_multistep_execution_contract = {
                "contract_kind": "bounded_multi_step_execution_preflight",
                "source": "prompt217_bounded_multistep_handoff_guard",
                "selected_handoff_kind": "bounded_multi_step_execution",
                "source_result_class": normalized_source_result_class,
                "source_selected_retrigger_kind": normalized_source_selected_retrigger_kind,
                "fresh_attempt_detected": (
                    bool(fresh_attempt_detected)
                    if normalized_source_result_class == "completed_fresh_attempt"
                    else False
                ),
                "existing_truth_surface_detected": (
                    True
                    if normalized_source_result_class
                    == "completed_existing_truth_surface"
                    else bool(existing_truth_surface_detected)
                ),
                "existing_truth_requires_revalidation": (
                    normalized_source_result_class
                    == "completed_existing_truth_surface"
                ),
                "allow_unbounded_loop": False,
                "allow_retry": False,
                "max_next_steps": 1,
                "requires_stop_policy_guard": True,
                "requires_budget_guard": True,
                "requires_result_assimilation": True,
                "cycle_budget_remaining": out_cycle_budget_remaining,
                "codex_budget_remaining": out_codex_budget_remaining,
                "rollback_budget_remaining": out_rollback_budget_remaining,
                "commit_budget_remaining": out_commit_budget_remaining,
                "next_action": "prepare_bounded_multi_step_execution",
            }
        elif len(non_stop_candidates) == 1 and non_stop_candidates[0] == "result_assimilation_chain":
            status = "bounded_multistep_handoff_guard_result_assimilation_ready"
            multistep_guard_available = True
            out_multistep_guard_allowed = False
            multistep_guard_block_reason = (
                "blocked_prompt217_contract_invalid"
                if not prompt217_contract_valid
                else "blocked_followup_guard_not_allowed"
            )
            selected_handoff_kind = "result_assimilation_chain"
            selected_handoff_action = "prepare_result_assimilation_chain"
            selected_handoff_payload = {
                "handoff_kind": "result_assimilation_chain",
                "source": "prompt217_bounded_multistep_handoff_guard",
                "source_result_class": normalized_source_result_class,
                "source_selected_retrigger_kind": normalized_source_selected_retrigger_kind,
                "next_action": "prepare_result_assimilation_chain",
            }
            exactly_one_handoff_target = True
            result_assimilation_handoff_ready = True
            blocked_handoff_ready = False
            out_manual_review_required = False
            out_should_stop = False
            out_stop_reason = ""
            out_next_action = "prepare_result_assimilation_chain"
        elif blocked_candidate:
            status = "bounded_multistep_handoff_guard_blocked"
            multistep_guard_available = True
            out_multistep_guard_allowed = False
            if not prompt217_contract_valid:
                multistep_guard_block_reason = "blocked_prompt217_contract_invalid"
            elif not bool(followup_guard_allowed):
                multistep_guard_block_reason = "blocked_followup_guard_not_allowed"
            elif not bool(exactly_one_followup_target):
                multistep_guard_block_reason = "blocked_not_exactly_one_followup_target"
            elif bool(followup_conflict_detected):
                multistep_guard_block_reason = "blocked_followup_conflict"
            elif not out_budget_checked:
                multistep_guard_block_reason = "blocked_budget_not_checked"
            elif out_cycle_budget_remaining <= 0:
                multistep_guard_block_reason = "blocked_cycle_budget_exhausted"
            elif bool(manual_review_required):
                multistep_guard_block_reason = "blocked_manual_review_required"
            elif bool(should_stop):
                multistep_guard_block_reason = "blocked_should_stop"
            elif bool(should_start_unbounded_loop):
                multistep_guard_block_reason = "blocked_unbounded_loop_requested"
            elif bool(should_continue_local_loop):
                multistep_guard_block_reason = "blocked_unexpected_continue_flag"
            elif bool(should_invoke_codex):
                multistep_guard_block_reason = "blocked_unexpected_codex_invocation_flag"
            elif bool(should_execute_rollback):
                multistep_guard_block_reason = "blocked_unexpected_rollback_execution_flag"
            elif bool(should_execute_commit):
                multistep_guard_block_reason = "blocked_unexpected_commit_execution_flag"
            elif bool(should_push):
                multistep_guard_block_reason = "blocked_unexpected_push_flag"
            elif bool(stale_truth_followup_blocked):
                multistep_guard_block_reason = "blocked_stale_truth_followup"
            elif bool(not_callable_followup_blocked):
                multistep_guard_block_reason = "blocked_not_callable_followup"
            elif not bool(terminal_result_detected):
                multistep_guard_block_reason = "blocked_terminal_result_missing"
            elif normalized_source_result_class not in {
                "completed_fresh_attempt",
                "completed_existing_truth_surface",
            }:
                multistep_guard_block_reason = "blocked_unsupported_source_result_class"
            else:
                multistep_guard_block_reason = "blocked_insufficient_multistep_handoff_truth"
            selected_handoff_kind = "blocked"
            selected_handoff_action = "manual_review_required"
            selected_handoff_payload = {
                "handoff_kind": "blocked",
                "source": "prompt217_bounded_multistep_handoff_guard",
                "stop_reason": multistep_guard_block_reason,
                "next_action": "manual_review_required",
            }
            exactly_one_handoff_target = True
            blocked_handoff_ready = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = multistep_guard_block_reason
            out_next_action = "manual_review_required"
        else:
            status = "bounded_multistep_handoff_guard_blocked_insufficient_truth"
            multistep_guard_available = False
            out_multistep_guard_allowed = False
            multistep_guard_block_reason = "blocked_insufficient_multistep_handoff_truth"
            selected_handoff_kind = "blocked"
            selected_handoff_action = "manual_review_required"
            selected_handoff_payload = {}
            blocked_handoff_ready = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = "insufficient_multistep_handoff_truth"
            out_next_action = "manual_review_required"

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if out_next_action not in allowed_next_actions:
        out_next_action = "insufficient_truth"
    if status == "insufficient_truth":
        status = "bounded_multistep_handoff_guard_blocked_insufficient_truth"
        multistep_guard_available = False
        out_multistep_guard_allowed = False
        multistep_guard_block_reason = "blocked_insufficient_multistep_handoff_truth"
        multistep_guard_source = "prompt216_direct_retrigger_followup_guard"
        prompt217_contract_valid = False
        selected_handoff_kind = "blocked"
        selected_handoff_action = "manual_review_required"
        selected_handoff_payload = {}
        exactly_one_handoff_target = False
        handoff_conflict_detected = False
        conflicting_handoff_targets = []
        bounded_multistep_handoff_ready = False
        result_assimilation_handoff_ready = False
        manual_stop_handoff_ready = False
        blocked_handoff_ready = True
        prompt218_multistep_execution_ready = False
        prompt218_multistep_execution_source = ""
        prompt218_multistep_execution_contract = {}
        out_should_continue_local_loop = False
        out_should_start_unbounded_loop = False
        out_should_invoke_codex = False
        out_should_execute_rollback = False
        out_should_execute_commit = False
        out_should_push = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_multistep_handoff_truth"
        out_next_action = "manual_review_required"
        max_next_steps = 0
        allow_unbounded_loop = False
        allow_retry = False
        requires_stop_policy_guard = False
        requires_budget_guard = False
        requires_result_assimilation = False

    return {
        "project_browser_autonomous_bounded_multistep_handoff_guard_status": status,
        "project_browser_autonomous_bounded_multistep_handoff_guard_multistep_guard_available": bool(
            multistep_guard_available
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_multistep_guard_allowed": bool(
            out_multistep_guard_allowed
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_multistep_guard_block_reason": (
            multistep_guard_block_reason
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_multistep_guard_source": (
            multistep_guard_source
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_prompt217_contract_valid": bool(
            prompt217_contract_valid
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_selected_handoff_kind": (
            selected_handoff_kind
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_selected_handoff_action": (
            selected_handoff_action
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_selected_handoff_payload": (
            selected_handoff_payload if isinstance(selected_handoff_payload, Mapping) else {}
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_exactly_one_handoff_target": bool(
            exactly_one_handoff_target
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_handoff_conflict_detected": bool(
            handoff_conflict_detected
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_conflicting_handoff_targets": (
            _normalize_string_list(conflicting_handoff_targets)
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_bounded_multistep_handoff_ready": bool(
            bounded_multistep_handoff_ready
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_result_assimilation_handoff_ready": bool(
            result_assimilation_handoff_ready
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_manual_stop_handoff_ready": bool(
            manual_stop_handoff_ready
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_blocked_handoff_ready": bool(
            blocked_handoff_ready
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_source_result_class": (
            normalized_source_result_class
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_source_selected_retrigger_kind": (
            normalized_source_selected_retrigger_kind
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_fresh_attempt_detected": bool(
            fresh_attempt_detected
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_existing_truth_surface_detected": bool(
            existing_truth_surface_detected
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_terminal_result_detected": bool(
            terminal_result_detected
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_terminal_result_source": (
            normalized_terminal_result_source
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_max_next_steps": int(
            _as_non_negative_int(max_next_steps, default=0)
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_allow_unbounded_loop": bool(
            allow_unbounded_loop
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_allow_retry": bool(
            allow_retry
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_requires_stop_policy_guard": bool(
            requires_stop_policy_guard
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_requires_budget_guard": bool(
            requires_budget_guard
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_requires_result_assimilation": bool(
            requires_result_assimilation
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_cycle_budget_remaining": int(
            out_cycle_budget_remaining
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_codex_budget_remaining": int(
            out_codex_budget_remaining
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_rollback_budget_remaining": int(
            out_rollback_budget_remaining
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_commit_budget_remaining": int(
            out_commit_budget_remaining
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_budget_checked": bool(
            out_budget_checked
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_prompt218_multistep_execution_ready": bool(
            prompt218_multistep_execution_ready
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_prompt218_multistep_execution_source": (
            prompt218_multistep_execution_source
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_prompt218_multistep_execution_contract": (
            prompt218_multistep_execution_contract
            if isinstance(prompt218_multistep_execution_contract, Mapping)
            else {}
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_should_continue_local_loop": bool(
            out_should_continue_local_loop
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_should_start_unbounded_loop": bool(
            out_should_start_unbounded_loop
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_should_invoke_codex": bool(
            out_should_invoke_codex
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_should_execute_rollback": bool(
            out_should_execute_rollback
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_should_execute_commit": bool(
            out_should_execute_commit
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_should_push": bool(
            out_should_push
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_manual_review_required": bool(
            out_manual_review_required
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_should_stop": bool(
            out_should_stop
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_stop_reason": (
            out_stop_reason
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_next_action": (
            out_next_action
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_bounded_multistep_handoff_guard_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_status,
                    normalized_followup_block_reason,
                    normalized_followup_source,
                    normalized_selected_followup_kind,
                    normalized_selected_followup_action,
                    normalized_source_result_class,
                    normalized_source_selected_retrigger_kind,
                    normalized_source_retrigger_status,
                    normalized_terminal_result_source,
                    normalized_stop_reason,
                    normalized_next_action,
                    normalized_result_assimilation_status,
                    normalized_direct_coordinator_status,
                    normalized_stale_gate_status,
                    normalized_one_bounded_status,
                    normalized_final_guard_status,
                    normalized_multi_cycle_status,
                    normalized_codex_reentry_status,
                    normalized_rollback_execution_status,
                    normalized_rollback_result_assimilation_status,
                    normalized_commit_execution_status,
                    normalized_commit_result_assimilation_status,
                    normalized_fix_generation_status,
                    normalized_next_generation_status,
                    "authoritative_prompt216_missing" if not authoritative_selected else "",
                    "followup_payload_missing"
                    if not normalized_selected_followup_payload
                    else "",
                    "prompt217_contract_invalid" if not prompt217_contract_valid else "",
                    "budget_not_checked" if not out_budget_checked else "",
                    "unexpected_continue_local_loop_flag"
                    if bool(should_continue_local_loop)
                    else "",
                    "unexpected_unbounded_loop_flag"
                    if bool(should_start_unbounded_loop)
                    else "",
                    "unexpected_codex_invocation_flag"
                    if bool(should_invoke_codex)
                    else "",
                    "unexpected_rollback_execution_flag"
                    if bool(should_execute_rollback)
                    else "",
                    "unexpected_commit_execution_flag"
                    if bool(should_execute_commit)
                    else "",
                    "unexpected_push_flag" if bool(should_push) else "",
                ]
            )
        ),
    }

def _build_project_browser_autonomous_bounded_n2_prompt229_handoff_packet_state(
    *,
    conformance_status: str,
    conformance_next_action: str,
    conformance_passed: bool,
    policy_surface_authoritative: bool,
    conformance_should_prepare_prompt229: bool,
    conformance_should_prepare_manual_review: bool,
    conformance_should_stop: bool,
    conformance_block_reason: str,
    conformance_compatibility_warnings: Any,
    selected_reason_family: str,
    root_cause_reason_family: str,
    prompt229_allowed_by_policy: bool,
    prompt229_ready_from_prompt228_booleans: bool,
    selected_primary_reason: str,
    root_cause_primary_reason: str,
    root_cause_upstream_reason_source: str,
    prompt228_e2e_flow_check_ready: bool,
    prompt228_fresh_runtime_evidence_ready: bool,
) -> dict[str, Any]:
    allowed_statuses = {
        "bounded_n2_prompt229_handoff_ready",
        "bounded_n2_prompt229_handoff_manual_stop",
        "bounded_n2_prompt229_handoff_blocked",
        "bounded_n2_prompt229_handoff_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "prepare_prompt229_preflight",
        "manual_review_required",
        "insufficient_truth",
    }
    allowed_paths = {"e2e_flow_check", "fresh_runtime_evidence", "none", "conflict"}

    normalized_selected_reason_family = _normalize_text(selected_reason_family, default="unknown")
    normalized_root_cause_reason_family = _normalize_text(
        root_cause_reason_family,
        default="unknown",
    )
    normalized_selected_primary_reason = _normalize_text(selected_primary_reason, default="")
    normalized_root_cause_primary_reason = _normalize_text(root_cause_primary_reason, default="")
    normalized_root_cause_upstream_reason_source = _normalize_text(
        root_cause_upstream_reason_source,
        default="",
    )
    normalized_conformance_status = _normalize_text(conformance_status, default="")
    normalized_conformance_next_action = _normalize_text(conformance_next_action, default="")
    normalized_conformance_block_reason = _normalize_text(conformance_block_reason, default="")

    prompt229_e2e_ready = bool(prompt228_e2e_flow_check_ready)
    prompt229_fresh_ready = bool(prompt228_fresh_runtime_evidence_ready)
    prompt229_ready_count = (1 if prompt229_e2e_ready else 0) + (
        1 if prompt229_fresh_ready else 0
    )

    selected_prompt229_path = "none"
    if prompt229_ready_count == 2:
        selected_prompt229_path = "conflict"
    elif prompt229_e2e_ready:
        selected_prompt229_path = "e2e_flow_check"
    elif prompt229_fresh_ready:
        selected_prompt229_path = "fresh_runtime_evidence"

    handoff_ready_rule = bool(
        bool(conformance_passed)
        and bool(policy_surface_authoritative)
        and bool(prompt229_allowed_by_policy)
        and prompt229_ready_count == 1
    )
    manual_stop_selected = bool(
        normalized_selected_reason_family == "manual_stop"
        or normalized_selected_primary_reason == "blocked_manual_review_required"
    )
    explicit_prompt228_ready = bool(prompt229_ready_count > 0)

    prompt229_handoff_block_reason = _first_true_reason(
        [
            (prompt229_ready_count == 2, "prompt229_readiness_conflict"),
            (not explicit_prompt228_ready, "prompt228_not_ready"),
            (
                manual_stop_selected and not explicit_prompt228_ready,
                "selected_manual_stop_or_prompt228_not_ready",
            ),
            (not bool(conformance_passed), "n2_policy_conformance_not_passed"),
            (not bool(policy_surface_authoritative), "n2_policy_surface_not_authoritative"),
            (not bool(prompt229_allowed_by_policy), "prompt229_not_allowed_by_policy"),
        ],
        default="",
    )

    status = "bounded_n2_prompt229_handoff_insufficient_truth"
    next_action = "manual_review_required"
    handoff_ready = False
    handoff_source = "prompt228_fix12_bounded_n2_prompt229_handoff_packet"
    handoff_stage = "prompt229_preflight_handoff"
    should_prepare_prompt229 = False
    should_prepare_manual_review = True
    should_stop = True

    if bool(conformance_passed) and bool(policy_surface_authoritative):
        if handoff_ready_rule:
            status = "bounded_n2_prompt229_handoff_ready"
            next_action = "prepare_prompt229_preflight"
            handoff_ready = True
            should_prepare_prompt229 = True
            should_prepare_manual_review = False
            should_stop = False
        elif manual_stop_selected:
            status = "bounded_n2_prompt229_handoff_manual_stop"
            next_action = "manual_review_required"
            handoff_ready = False
            should_prepare_prompt229 = False
            should_prepare_manual_review = True
            should_stop = True
        else:
            status = "bounded_n2_prompt229_handoff_blocked"
            next_action = "manual_review_required"
            handoff_ready = False
            should_prepare_prompt229 = False
            should_prepare_manual_review = True
            should_stop = True
    elif normalized_conformance_status:
        status = "bounded_n2_prompt229_handoff_blocked"
        next_action = "manual_review_required"
        handoff_ready = False
        should_prepare_prompt229 = False
        should_prepare_manual_review = True
        should_stop = True

    if not handoff_ready:
        selected_prompt229_path = (
            selected_prompt229_path if selected_prompt229_path in {"none", "conflict"} else "none"
        )

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"
    if selected_prompt229_path not in allowed_paths:
        selected_prompt229_path = "none"
    if status == "insufficient_truth":
        status = "bounded_n2_prompt229_handoff_insufficient_truth"
        next_action = "manual_review_required"
        handoff_ready = False
        selected_prompt229_path = "none"
        prompt229_handoff_block_reason = "insufficient_prompt229_handoff_truth"
        should_prepare_prompt229 = False
        should_prepare_manual_review = True
        should_stop = True

    compatibility_warnings = _normalize_string_list(conformance_compatibility_warnings)
    if not bool(conformance_passed):
        compatibility_warnings.append("n2_policy_conformance_not_passed")
    if not bool(policy_surface_authoritative):
        compatibility_warnings.append("n2_policy_surface_not_authoritative")
    if manual_stop_selected and not explicit_prompt228_ready:
        compatibility_warnings.append("manual_stop_selected_prompt228_not_ready")
    compatibility_warnings = _normalize_string_list(compatibility_warnings)

    handoff_payload = {
        "contract_kind": "prompt229_n2_canonical_handoff_packet",
        "source": "prompt228_fix12_bounded_n2_prompt229_handoff_packet",
        "handoff_stage": "prompt229_preflight_handoff",
        "conformance_passed": bool(conformance_passed),
        "policy_surface_authoritative": bool(policy_surface_authoritative),
        "selected_reason_family": normalized_selected_reason_family,
        "root_cause_reason_family": normalized_root_cause_reason_family,
        "prompt229_allowed_by_policy": bool(prompt229_allowed_by_policy),
        "prompt229_ready_from_prompt228_booleans": bool(prompt229_ready_from_prompt228_booleans),
        "prompt229_e2e_flow_check_ready": bool(prompt229_e2e_ready),
        "prompt229_fresh_runtime_evidence_ready": bool(prompt229_fresh_ready),
        "selected_prompt229_path": selected_prompt229_path,
        "prompt229_handoff_block_reason": prompt229_handoff_block_reason,
        "next_action": next_action,
    }

    return {
        "project_browser_autonomous_bounded_n2_prompt229_handoff_packet_status": status,
        "project_browser_autonomous_bounded_n2_prompt229_handoff_packet_next_action": next_action,
        "project_browser_autonomous_bounded_n2_prompt229_handoff_packet_handoff_ready": bool(
            handoff_ready
        ),
        "project_browser_autonomous_bounded_n2_prompt229_handoff_packet_handoff_source": (
            handoff_source
        ),
        "project_browser_autonomous_bounded_n2_prompt229_handoff_packet_handoff_stage": (
            handoff_stage
        ),
        "project_browser_autonomous_bounded_n2_prompt229_handoff_packet_conformance_passed": bool(
            conformance_passed
        ),
        "project_browser_autonomous_bounded_n2_prompt229_handoff_packet_policy_surface_authoritative": bool(
            policy_surface_authoritative
        ),
        "project_browser_autonomous_bounded_n2_prompt229_handoff_packet_selected_reason_family": (
            normalized_selected_reason_family
        ),
        "project_browser_autonomous_bounded_n2_prompt229_handoff_packet_selected_primary_reason": (
            normalized_selected_primary_reason
        ),
        "project_browser_autonomous_bounded_n2_prompt229_handoff_packet_root_cause_reason_family": (
            normalized_root_cause_reason_family
        ),
        "project_browser_autonomous_bounded_n2_prompt229_handoff_packet_root_cause_primary_reason": (
            normalized_root_cause_primary_reason
        ),
        "project_browser_autonomous_bounded_n2_prompt229_handoff_packet_root_cause_upstream_reason_source": (
            normalized_root_cause_upstream_reason_source
        ),
        "project_browser_autonomous_bounded_n2_prompt229_handoff_packet_prompt229_allowed_by_policy": bool(
            prompt229_allowed_by_policy
        ),
        "project_browser_autonomous_bounded_n2_prompt229_handoff_packet_prompt229_ready_from_prompt228_booleans": bool(
            prompt229_ready_from_prompt228_booleans
        ),
        "project_browser_autonomous_bounded_n2_prompt229_handoff_packet_prompt229_e2e_flow_check_ready": bool(
            prompt229_e2e_ready
        ),
        "project_browser_autonomous_bounded_n2_prompt229_handoff_packet_prompt229_fresh_runtime_evidence_ready": bool(
            prompt229_fresh_ready
        ),
        "project_browser_autonomous_bounded_n2_prompt229_handoff_packet_selected_prompt229_path": (
            selected_prompt229_path
        ),
        "project_browser_autonomous_bounded_n2_prompt229_handoff_packet_prompt229_handoff_block_reason": (
            prompt229_handoff_block_reason
        ),
        "project_browser_autonomous_bounded_n2_prompt229_handoff_packet_should_prepare_prompt229": bool(
            should_prepare_prompt229
        ),
        "project_browser_autonomous_bounded_n2_prompt229_handoff_packet_should_prepare_manual_review": bool(
            should_prepare_manual_review
        ),
        "project_browser_autonomous_bounded_n2_prompt229_handoff_packet_should_stop": bool(
            should_stop
        ),
        "project_browser_autonomous_bounded_n2_prompt229_handoff_packet_compatibility_warnings": (
            compatibility_warnings
        ),
        "project_browser_autonomous_bounded_n2_prompt229_handoff_packet_handoff_payload": (
            handoff_payload
        ),
    }

def _build_project_browser_autonomous_explicit_real_input_handoff_validation_state(
    *,
    injection_state: Mapping[str, Any],
    explicit_readiness_state: Mapping[str, Any],
    real_input_path_readiness_state: Mapping[str, Any],
    pr_prompt_generation_state: Mapping[str, Any],
    codex_handoff_state: Mapping[str, Any],
    mvp_state: Mapping[str, Any],
) -> dict[str, Any]:
    injection_enabled = bool(
        injection_state.get(
            "project_browser_autonomous_explicit_real_input_injection_enabled",
            False,
        )
    )
    project_request_detected = bool(
        explicit_readiness_state.get(
            "project_browser_autonomous_explicit_dev_loop_input_readiness_project_request_detected",
            False,
        )
    )
    analysis_ready = bool(
        explicit_readiness_state.get(
            "project_browser_autonomous_explicit_dev_loop_input_readiness_analysis_summary_detected",
            False,
        )
    )
    roadmap_ready = bool(
        explicit_readiness_state.get(
            "project_browser_autonomous_explicit_dev_loop_input_readiness_roadmap_pr_queue_detected",
            False,
        )
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
    real_input_path_kind = _normalize_text(
        real_input_path_readiness_state.get(
            "project_browser_autonomous_real_input_mvp_path_readiness_path_kind"
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
        and project_request_detected
        and analysis_ready
        and roadmap_ready
        and pr_prompt_ready
        and codex_handoff_ready
        and real_input_path_kind == "explicit_real_pr_prompt_to_handoff_path"
        and observed_mvp_status == "waiting_for_codex_result"
        and observed_mvp_next_action == "await_codex_result"
    )
    if passed:
        status = "explicit_real_input_handoff_validation_passed"
        next_action = "await_codex_result"
    elif injection_enabled:
        status = "explicit_real_input_handoff_validation_failed"
        next_action = "inspect_explicit_real_input_handoff_mismatch"
    else:
        status = "explicit_real_input_handoff_validation_not_applicable"
        next_action = "use_existing_explicit_real_input"

    return {
        "project_browser_autonomous_explicit_real_input_handoff_validation_status": status,
        "project_browser_autonomous_explicit_real_input_handoff_validation_source": (
            "prompt258_explicit_real_input_handoff_validation"
        ),
        "project_browser_autonomous_explicit_real_input_handoff_validation_injection_enabled": bool(
            injection_enabled
        ),
        "project_browser_autonomous_explicit_real_input_handoff_validation_project_request_detected": bool(
            project_request_detected
        ),
        "project_browser_autonomous_explicit_real_input_handoff_validation_analysis_ready": bool(
            analysis_ready
        ),
        "project_browser_autonomous_explicit_real_input_handoff_validation_roadmap_ready": bool(
            roadmap_ready
        ),
        "project_browser_autonomous_explicit_real_input_handoff_validation_pr_prompt_ready": bool(
            pr_prompt_ready
        ),
        "project_browser_autonomous_explicit_real_input_handoff_validation_codex_handoff_ready": bool(
            codex_handoff_ready
        ),
        "project_browser_autonomous_explicit_real_input_handoff_validation_real_input_path_kind": (
            real_input_path_kind
        ),
        "project_browser_autonomous_explicit_real_input_handoff_validation_observed_mvp_status": (
            observed_mvp_status
        ),
        "project_browser_autonomous_explicit_real_input_handoff_validation_observed_mvp_next_action": (
            observed_mvp_next_action
        ),
        "project_browser_autonomous_explicit_real_input_handoff_validation_passed": bool(
            passed
        ),
        "project_browser_autonomous_explicit_real_input_handoff_validation_next_action": (
            next_action
        ),
    }

def _build_project_browser_autonomous_cycle_handoff_controller_state(
    *,
    source_cycle_status: str,
    source_next_safe_action: str,
    source_next_prompt_kind: str,
    source_cycle_passed: bool,
    source_cycle_failed: bool,
    source_cycle_blocked: bool,
    source_cycle_block_reason: str,
    human_review_required: bool,
    downstream_validation_definitive: bool,
    source_validation_execution_status: str,
) -> dict[str, Any]:
    normalized_source_cycle_status = _normalize_text(
        source_cycle_status,
        default="blocked_insufficient_cycle_truth",
    )
    normalized_source_next_safe_action = _normalize_text(
        source_next_safe_action,
        default="manual_review_required",
    )
    normalized_source_next_prompt_kind = _normalize_text(
        source_next_prompt_kind,
        default="none",
    )
    if normalized_source_next_prompt_kind not in {"fix", "next", "none"}:
        normalized_source_next_prompt_kind = "none"
    normalized_source_cycle_block_reason = _normalize_text(
        source_cycle_block_reason,
        default="",
    )
    normalized_source_validation_execution_status = _normalize_text(
        source_validation_execution_status,
        default="insufficient_truth",
    )

    status = "handoff_blocked_insufficient_truth"
    handoff_allowed = False
    handoff_block_reason = "blocked_insufficient_handoff_truth"
    handoff_target = "none"
    handoff_prompt_kind = "none"
    should_generate_next_prompt = False
    should_generate_fix_prompt = False
    should_prepare_next_cycle = False
    should_start_next_cycle = False
    should_invoke_codex = False
    should_rollback = False
    readiness_handoff_available = False
    readiness_handoff_prompt_kind = "none"
    readiness_handoff_reason = "blocked_insufficient_handoff_truth"
    effective_human_review_required = True
    next_action = "manual_review_required"

    if (
        normalized_source_next_safe_action == "continue_one_step_cycle"
        and normalized_source_next_prompt_kind == "next"
        and bool(source_cycle_passed)
        and not bool(human_review_required)
    ):
        status = "handoff_to_next_prompt_flow"
        handoff_allowed = True
        handoff_block_reason = ""
        handoff_target = "next_prompt_flow"
        handoff_prompt_kind = "next"
        should_generate_next_prompt = True
        should_generate_fix_prompt = False
        should_prepare_next_cycle = True
        should_start_next_cycle = False
        should_invoke_codex = False
        should_rollback = False
        readiness_handoff_available = True
        readiness_handoff_prompt_kind = "next"
        readiness_handoff_reason = "cycle_passed"
        effective_human_review_required = False
        next_action = "generate_next_prompt"
    elif (
        normalized_source_next_safe_action == "generate_fix_prompt"
        and normalized_source_next_prompt_kind == "fix"
        and bool(source_cycle_failed)
        and not bool(human_review_required)
    ):
        status = "handoff_to_fix_prompt_flow"
        handoff_allowed = True
        handoff_block_reason = ""
        handoff_target = "fix_prompt_flow"
        handoff_prompt_kind = "fix"
        should_generate_next_prompt = False
        should_generate_fix_prompt = True
        should_prepare_next_cycle = False
        should_start_next_cycle = False
        should_invoke_codex = False
        should_rollback = False
        readiness_handoff_available = True
        readiness_handoff_prompt_kind = "fix"
        readiness_handoff_reason = "validation_failed"
        effective_human_review_required = False
        next_action = "generate_fix_prompt"
    elif (
        normalized_source_next_safe_action == "manual_review_required"
        or bool(human_review_required)
        or bool(source_cycle_blocked)
    ):
        status = "handoff_blocked_manual_review"
        handoff_allowed = False
        handoff_target = "manual_review"
        handoff_prompt_kind = "none"
        should_generate_next_prompt = False
        should_generate_fix_prompt = False
        should_prepare_next_cycle = False
        should_start_next_cycle = False
        should_invoke_codex = False
        should_rollback = False
        readiness_handoff_available = False
        readiness_handoff_prompt_kind = "none"
        readiness_handoff_reason = "manual_review_required"
        handoff_block_reason = (
            normalized_source_cycle_block_reason or "manual_review_required"
        )
        effective_human_review_required = True
        next_action = "manual_review_required"

    return {
        "project_browser_autonomous_cycle_handoff_controller_status": status,
        "project_browser_autonomous_cycle_handoff_controller_handoff_allowed": bool(
            handoff_allowed
        ),
        "project_browser_autonomous_cycle_handoff_controller_handoff_block_reason": (
            handoff_block_reason
        ),
        "project_browser_autonomous_cycle_handoff_controller_handoff_target": (
            handoff_target
        ),
        "project_browser_autonomous_cycle_handoff_controller_handoff_prompt_kind": (
            handoff_prompt_kind
        ),
        "project_browser_autonomous_cycle_handoff_controller_should_generate_next_prompt": bool(
            should_generate_next_prompt
        ),
        "project_browser_autonomous_cycle_handoff_controller_should_generate_fix_prompt": bool(
            should_generate_fix_prompt
        ),
        "project_browser_autonomous_cycle_handoff_controller_should_prepare_next_cycle": bool(
            should_prepare_next_cycle
        ),
        "project_browser_autonomous_cycle_handoff_controller_should_start_next_cycle": bool(
            should_start_next_cycle
        ),
        "project_browser_autonomous_cycle_handoff_controller_should_invoke_codex": bool(
            should_invoke_codex
        ),
        "project_browser_autonomous_cycle_handoff_controller_should_rollback": bool(
            should_rollback
        ),
        "project_browser_autonomous_cycle_handoff_controller_readiness_handoff_available": bool(
            readiness_handoff_available
        ),
        "project_browser_autonomous_cycle_handoff_controller_readiness_handoff_prompt_kind": (
            readiness_handoff_prompt_kind
        ),
        "project_browser_autonomous_cycle_handoff_controller_readiness_handoff_reason": (
            readiness_handoff_reason
        ),
        "project_browser_autonomous_cycle_handoff_controller_source_cycle_status": (
            normalized_source_cycle_status
        ),
        "project_browser_autonomous_cycle_handoff_controller_source_next_safe_action": (
            normalized_source_next_safe_action
        ),
        "project_browser_autonomous_cycle_handoff_controller_source_next_prompt_kind": (
            normalized_source_next_prompt_kind
        ),
        "project_browser_autonomous_cycle_handoff_controller_source_cycle_passed": bool(
            source_cycle_passed
        ),
        "project_browser_autonomous_cycle_handoff_controller_source_cycle_failed": bool(
            source_cycle_failed
        ),
        "project_browser_autonomous_cycle_handoff_controller_source_cycle_blocked": bool(
            source_cycle_blocked
        ),
        "project_browser_autonomous_cycle_handoff_controller_source_cycle_block_reason": (
            normalized_source_cycle_block_reason
        ),
        "project_browser_autonomous_cycle_handoff_controller_human_review_required": bool(
            effective_human_review_required
        ),
        "project_browser_autonomous_cycle_handoff_controller_next_action": next_action,
        "project_browser_autonomous_cycle_handoff_controller_downstream_validation_definitive": bool(
            downstream_validation_definitive
        ),
        "project_browser_autonomous_cycle_handoff_controller_source_validation_execution_status": (
            normalized_source_validation_execution_status
        ),
    }

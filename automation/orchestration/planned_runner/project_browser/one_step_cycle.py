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
def _build_project_browser_autonomous_one_cycle_controller_state(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prior_approved_restart_execution_payload: Mapping[str, Any] | None,
    execution_repo_path: str,
    dry_run: bool,
) -> dict[str, Any]:
    approved_restart = (
        dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    )
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

    def _read_text_value(key: str, *, default: str = "") -> str:
        value = prior_payload.get(key) if key in prior_payload else approved_restart.get(key)
        return _normalize_text(value, default=default)

    def _resolve_prompt365_runtime_transport_mode() -> str:
        for candidate in (
            _read_text_value("prompt360_transport_mode"),
            _read_text_value("transport_mode"),
        ):
            normalized_candidate = _normalize_text(candidate, default="").lower()
            if normalized_candidate == "dry-run":
                return "dry-run"
            if normalized_candidate == "live":
                return "live"
        return "dry-run" if bool(dry_run) or _read_flag("dry_run", default=False) else "live"

    def _resolve_prompt365_effective_dry_run() -> bool:
        if bool(dry_run):
            return True
        if _resolve_prompt365_runtime_transport_mode() == "dry-run":
            return True
        if _read_flag("dry_run", default=False):
            return True
        if _read_text_value("prompt360_transport_mode", default="").lower() == "dry-run":
            return True
        for key in ("manifest_dry_run", "run_dry_run"):
            if _read_flag(key, default=False):
                return True
        return False

    def _read_non_negative_int_flag(key: str, *, default: int) -> int:
        value = prior_payload.get(key) if key in prior_payload else approved_restart.get(key)
        return _as_non_negative_int(value, default=default)

    one_cycle_controller_dir = Path("/tmp/codex-local-runner-decision/one_cycle_controller")
    output_json_path = one_cycle_controller_dir / "one_cycle_controller_result.json"
    output_summary_path = one_cycle_controller_dir / "one_cycle_controller_summary.md"
    execution_stdout_path = one_cycle_controller_dir / "one_cycle_controller_exec_stdout.log"
    execution_stderr_path = one_cycle_controller_dir / "one_cycle_controller_exec_stderr.log"
    execution_runlog_path = one_cycle_controller_dir / "one_cycle_controller_runlog.md"
    diff_stat_path = one_cycle_controller_dir / "one_cycle_controller_diff_stat.txt"
    diff_name_status_path = one_cycle_controller_dir / "one_cycle_controller_diff_name_status.txt"
    diff_patch_path = one_cycle_controller_dir / "one_cycle_controller_diff.patch"
    review_request_path = one_cycle_controller_dir / "one_cycle_controller_review_request.md"
    review_handoff_path = one_cycle_controller_dir / "one_cycle_controller_review_handoff.json"
    review_response_path = one_cycle_controller_dir / "review_response.json"
    targeted_fix_prompt_path = one_cycle_controller_dir / "targeted_fix_prompt.md"
    targeted_fix_codex_prompt_path = one_cycle_controller_dir / "targeted_fix_codex_prompt.md"
    targeted_fix_reentry_execution_receipt_path = (
        one_cycle_controller_dir / "targeted_fix_reentry_execution_receipt.json"
    )
    targeted_fix_post_reentry_diff_capture_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_diff_capture.json"
    )
    targeted_fix_post_reentry_diff_patch_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_diff.patch"
    )
    targeted_fix_post_reentry_diff_stat_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_diff_stat.txt"
    )
    targeted_fix_post_reentry_diff_name_status_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_diff_name_status.txt"
    )
    targeted_fix_post_reentry_review_handoff_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_review_handoff.json"
    )
    targeted_fix_post_reentry_review_response_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_review_response.json"
    )
    targeted_fix_post_reentry_review_assimilation_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_review_assimilation.json"
    )
    targeted_fix_post_reentry_route_decision_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_route_decision.json"
    )
    targeted_fix_post_reentry_route_executor_boundary_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_route_executor_boundary.json"
    )
    targeted_fix_post_reentry_next_step_handoff_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_next_step_handoff.json"
    )
    targeted_fix_post_reentry_cycle_closure_result_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_cycle_closure_result.json"
    )
    targeted_fix_post_reentry_terminal_summary_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_terminal_summary.json"
    )
    targeted_fix_post_reentry_prompt_emission_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_prompt_emission.json"
    )
    targeted_fix_post_reentry_prompt_emission_receipt_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_prompt_emission_receipt.json"
    )
    targeted_fix_post_reentry_codex_reentry_execution_receipt_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_codex_reentry_execution_receipt.json"
    )
    targeted_fix_post_reentry_codex_reentry_execution_stdout_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_codex_reentry_execution_stdout.txt"
    )
    targeted_fix_post_reentry_codex_reentry_execution_stderr_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_codex_reentry_execution_stderr.txt"
    )
    targeted_fix_post_reentry_bounded_cycle_state_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_bounded_cycle_state.json"
    )
    targeted_fix_post_reentry_bounded_cycle_decision_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_bounded_cycle_decision.json"
    )
    targeted_fix_post_reentry_bounded_cycle_receipt_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_bounded_cycle_receipt.json"
    )
    approve_commit_tag_boundary_metadata_path = (
        one_cycle_controller_dir / "approve_commit_tag_boundary.json"
    )
    approve_commit_tag_boundary_commands_path = (
        one_cycle_controller_dir / "approve_commit_tag_commands.sh"
    )
    approve_commit_tag_plan_metadata_path = (
        one_cycle_controller_dir / "approve_commit_tag_plan.json"
    )
    approve_commit_tag_artifact_reconciliation_receipt_file_path = (
        one_cycle_controller_dir / "approve_commit_tag_artifact_reconciliation_receipt.json"
    )
    approve_commit_tag_execution_receipt_path = (
        one_cycle_controller_dir / "approve_commit_tag_execution_receipt.json"
    )
    remote_readiness_boundary_metadata_path = (
        one_cycle_controller_dir / "remote_readiness_boundary.json"
    )
    remote_readiness_plan_metadata_path = (
        one_cycle_controller_dir / "remote_readiness_plan.json"
    )
    local_end_to_end_controller_readiness_boundary_path = (
        one_cycle_controller_dir / "local_end_to_end_controller_readiness_boundary.json"
    )
    local_end_to_end_controller_component_matrix_path = (
        one_cycle_controller_dir / "local_end_to_end_controller_component_matrix.json"
    )
    local_end_to_end_controller_gap_report_path = (
        one_cycle_controller_dir / "local_end_to_end_controller_gap_report.json"
    )
    local_end_to_end_dry_run_plan_path = (
        one_cycle_controller_dir / "local_end_to_end_dry_run_plan.json"
    )
    local_end_to_end_dry_run_step_matrix_path = (
        one_cycle_controller_dir / "local_end_to_end_dry_run_step_matrix.json"
    )
    local_end_to_end_dry_run_receipt_path = (
        one_cycle_controller_dir / "local_end_to_end_dry_run_receipt.json"
    )
    local_end_to_end_one_shot_execution_gate_path = (
        one_cycle_controller_dir / "local_end_to_end_one_shot_execution_gate.json"
    )
    local_end_to_end_one_shot_step_selection_path = (
        one_cycle_controller_dir / "local_end_to_end_one_shot_step_selection.json"
    )
    local_end_to_end_one_shot_execution_receipt_path = (
        one_cycle_controller_dir / "local_end_to_end_one_shot_execution_receipt.json"
    )
    bounded_local_autonomous_loop_state_path = (
        one_cycle_controller_dir / "bounded_local_autonomous_loop_state.json"
    )
    bounded_local_autonomous_loop_decision_path = (
        one_cycle_controller_dir / "bounded_local_autonomous_loop_decision.json"
    )
    bounded_local_autonomous_loop_receipt_path = (
        one_cycle_controller_dir / "bounded_local_autonomous_loop_receipt.json"
    )
    selected_step_execution_adapter_state_path = (
        one_cycle_controller_dir / "selected_step_execution_adapter_state.json"
    )
    selected_step_execution_plan_path = (
        one_cycle_controller_dir / "selected_step_execution_plan.json"
    )
    selected_step_execution_receipt_path = (
        one_cycle_controller_dir / "selected_step_execution_receipt.json"
    )
    selected_step_live_execution_gate_path = Path(
        _SELECTED_STEP_LIVE_EXECUTION_GATE_PATH
    )
    selected_step_live_execution_result_path = Path(
        _SELECTED_STEP_LIVE_EXECUTION_RESULT_PATH
    )
    selected_step_live_execution_receipt_path = Path(
        _SELECTED_STEP_LIVE_EXECUTION_RECEIPT_PATH
    )
    selected_step_execution_result_route_capture_path = Path(
        _SELECTED_STEP_EXECUTION_RESULT_ROUTE_CAPTURE_PATH
    )
    selected_step_execution_result_route_decision_path = Path(
        _SELECTED_STEP_EXECUTION_RESULT_ROUTE_DECISION_PATH
    )
    selected_step_execution_result_route_receipt_path = Path(
        _SELECTED_STEP_EXECUTION_RESULT_ROUTE_RECEIPT_PATH
    )
    local_only_autonomous_loop_closure_state_path = Path(
        _LOCAL_ONLY_AUTONOMOUS_LOOP_CLOSURE_STATE_PATH
    )
    local_only_autonomous_loop_closure_decision_path = Path(
        _LOCAL_ONLY_AUTONOMOUS_LOOP_CLOSURE_DECISION_PATH
    )
    local_only_autonomous_loop_closure_receipt_path = Path(
        _LOCAL_ONLY_AUTONOMOUS_LOOP_CLOSURE_RECEIPT_PATH
    )
    local_autonomous_cycle_v2_state_path = Path(_LOCAL_AUTONOMOUS_CYCLE_V2_STATE_PATH)
    local_autonomous_cycle_v2_decision_path = Path(_LOCAL_AUTONOMOUS_CYCLE_V2_DECISION_PATH)
    local_autonomous_cycle_v2_receipt_path = Path(_LOCAL_AUTONOMOUS_CYCLE_V2_RECEIPT_PATH)
    local_codex_one_shot_prompt_path = Path(_LOCAL_CODEX_ONE_SHOT_PROMPT_PATH)
    local_codex_one_shot_execution_handoff_path = Path(
        _LOCAL_CODEX_ONE_SHOT_EXECUTION_HANDOFF_PATH
    )
    local_codex_one_shot_execution_receipt_path = Path(
        _LOCAL_CODEX_ONE_SHOT_EXECUTION_RECEIPT_PATH
    )
    local_codex_one_shot_execution_result_path = Path(
        _LOCAL_CODEX_ONE_SHOT_EXECUTION_RESULT_PATH
    )
    local_codex_one_shot_execution_receipt_v2_path = Path(
        _LOCAL_CODEX_ONE_SHOT_EXECUTION_RECEIPT_V2_PATH
    )
    local_codex_one_shot_execution_stdout_path = Path(
        _LOCAL_CODEX_ONE_SHOT_EXECUTION_STDOUT_PATH
    )
    local_codex_one_shot_execution_stderr_path = Path(
        _LOCAL_CODEX_ONE_SHOT_EXECUTION_STDERR_PATH
    )
    local_post_codex_diff_capture_path = Path(_LOCAL_POST_CODEX_DIFF_CAPTURE_PATH)
    local_post_codex_execution_outcome_path = Path(_LOCAL_POST_CODEX_EXECUTION_OUTCOME_PATH)
    local_post_codex_route_decision_path = Path(_LOCAL_POST_CODEX_ROUTE_DECISION_PATH)
    local_post_codex_diff_capture_receipt_path = Path(_LOCAL_POST_CODEX_DIFF_CAPTURE_RECEIPT_PATH)
    local_targeted_contract_fix_prompt_path = Path(_LOCAL_TARGETED_CONTRACT_FIX_PROMPT_PATH)
    local_targeted_contract_fix_prompt_plan_path = Path(
        _LOCAL_TARGETED_CONTRACT_FIX_PROMPT_PLAN_PATH
    )
    local_targeted_contract_fix_prompt_receipt_path = Path(
        _LOCAL_TARGETED_CONTRACT_FIX_PROMPT_RECEIPT_PATH
    )
    local_targeted_contract_fix_route_intake_path = Path(
        _LOCAL_TARGETED_CONTRACT_FIX_ROUTE_INTAKE_PATH
    )
    local_contract_fix_cycle_coordination_state_path = Path(
        _LOCAL_CONTRACT_FIX_CYCLE_COORDINATION_STATE_PATH
    )
    local_contract_fix_cycle_coordination_decision_path = Path(
        _LOCAL_CONTRACT_FIX_CYCLE_COORDINATION_DECISION_PATH
    )
    local_contract_fix_cycle_coordination_receipt_path = Path(
        _LOCAL_CONTRACT_FIX_CYCLE_COORDINATION_RECEIPT_PATH
    )
    local_contract_fix_cycle_execution_handoff_path = Path(
        _LOCAL_CONTRACT_FIX_CYCLE_EXECUTION_HANDOFF_PATH
    )
    local_daemon_lite_wrapper_state_path = Path(_LOCAL_DAEMON_LITE_WRAPPER_STATE_PATH)
    local_daemon_lite_wrapper_plan_path = Path(_LOCAL_DAEMON_LITE_WRAPPER_PLAN_PATH)
    local_daemon_lite_wrapper_decision_path = Path(_LOCAL_DAEMON_LITE_WRAPPER_DECISION_PATH)
    local_daemon_lite_wrapper_receipt_path = Path(_LOCAL_DAEMON_LITE_WRAPPER_RECEIPT_PATH)
    local_targeted_contract_fix_execution_state_path = Path(
        _LOCAL_TARGETED_CONTRACT_FIX_EXECUTION_STATE_PATH
    )
    local_targeted_contract_fix_execution_result_path = Path(
        _LOCAL_TARGETED_CONTRACT_FIX_EXECUTION_RESULT_PATH
    )
    local_targeted_contract_fix_execution_receipt_path = Path(
        _LOCAL_TARGETED_CONTRACT_FIX_EXECUTION_RECEIPT_PATH
    )
    local_targeted_contract_fix_execution_stdout_path = Path(
        _LOCAL_TARGETED_CONTRACT_FIX_EXECUTION_STDOUT_PATH
    )
    local_targeted_contract_fix_execution_stderr_path = Path(
        _LOCAL_TARGETED_CONTRACT_FIX_EXECUTION_STDERR_PATH
    )
    local_post_targeted_contract_fix_diff_capture_path = Path(
        _LOCAL_POST_TARGETED_CONTRACT_FIX_DIFF_CAPTURE_PATH
    )
    local_post_targeted_contract_fix_execution_outcome_path = Path(
        _LOCAL_POST_TARGETED_CONTRACT_FIX_EXECUTION_OUTCOME_PATH
    )
    local_post_targeted_contract_fix_route_decision_path = Path(
        _LOCAL_POST_TARGETED_CONTRACT_FIX_ROUTE_DECISION_PATH
    )
    local_post_targeted_contract_fix_review_receipt_path = Path(
        _LOCAL_POST_TARGETED_CONTRACT_FIX_REVIEW_RECEIPT_PATH
    )
    local_bounded_approve_commit_tag_gate_state_path = Path(
        _LOCAL_BOUNDED_APPROVE_COMMIT_TAG_GATE_STATE_PATH
    )
    local_bounded_approve_commit_tag_execution_result_path = Path(
        _LOCAL_BOUNDED_APPROVE_COMMIT_TAG_EXECUTION_RESULT_PATH
    )
    local_bounded_approve_commit_tag_execution_receipt_path = Path(
        _LOCAL_BOUNDED_APPROVE_COMMIT_TAG_EXECUTION_RECEIPT_PATH
    )
    local_bounded_approve_commit_tag_plan_path = Path(
        _LOCAL_BOUNDED_APPROVE_COMMIT_TAG_PLAN_PATH
    )
    local_post_commit_cycle_closure_state_path = Path(
        _LOCAL_POST_COMMIT_CYCLE_CLOSURE_STATE_PATH
    )
    local_post_commit_cycle_closure_decision_path = Path(
        _LOCAL_POST_COMMIT_CYCLE_CLOSURE_DECISION_PATH
    )
    local_post_commit_cycle_closure_receipt_path = Path(
        _LOCAL_POST_COMMIT_CYCLE_CLOSURE_RECEIPT_PATH
    )
    local_next_cycle_reentry_decision_path = Path(
        _LOCAL_NEXT_CYCLE_REENTRY_DECISION_PATH
    )
    local_autonomous_continuation_state_path = Path(
        _LOCAL_AUTONOMOUS_CONTINUATION_STATE_PATH
    )
    local_autonomous_continuation_decision_path = Path(
        _LOCAL_AUTONOMOUS_CONTINUATION_DECISION_PATH
    )
    local_autonomous_continuation_receipt_path = Path(
        _LOCAL_AUTONOMOUS_CONTINUATION_RECEIPT_PATH
    )
    local_autonomous_next_cycle_selection_path = Path(
        _LOCAL_AUTONOMOUS_NEXT_CYCLE_SELECTION_PATH
    )
    local_autonomous_loop_completion_summary_path = Path(
        _LOCAL_AUTONOMOUS_LOOP_COMPLETION_SUMMARY_PATH
    )
    completed_result_source_path = output_json_path
    exec_plan_path = Path(
        "/tmp/codex-local-runner-decision/local_codex_execution_readiness/local_codex_exec_plan.sh"
    )
    _refresh_one_cycle_controller_runtime_planning_artifacts(
        one_cycle_controller_dir=one_cycle_controller_dir,
        execution_repo_path=execution_repo_path,
    )

    status = "one_cycle_controller_ready"
    next_action = "enable_one_cycle_controller_execution"
    cycle_count = 0
    max_cycles = 1
    codex_execution_status = "not_executed"
    diff_capture_status = "not_started"
    diff_capture_blocked_reason = "one_cycle_not_completed"
    review_request_status = "not_started"
    review_request_blocked_reason = "one_cycle_not_completed"
    review_handoff_decision_status = "manual_review_required"
    tracked_diff_status = "unknown"
    no_diff_review_status = "blocked"
    no_diff_reason = "review_handoff_missing_or_invalid"
    review_handoff_decision_source_path = str(review_handoff_path)
    review_handoff_decision_next_action = "manual_review_required"
    review_response_status = "missing"
    review_response_decision = "none"
    review_response_reason = ""
    review_response_next_action = "wait_for_chatgpt_diff_review_response"
    local_post_codex_diff_capture_status = "not_started"
    local_post_codex_diff_capture_blocked_reason = "prompt334_not_started"
    local_post_codex_diff_capture_next_action = "prepare_prompt333_execution_result_artifacts"
    local_post_codex_diff_capture_worktree_clean_for_tracked_files = False
    local_post_codex_diff_capture_changed_tracked_file_count = 0
    local_post_codex_outcome_status = "not_started"
    local_post_codex_outcome_classification = "prompt333_execution_not_ready"
    local_post_codex_stdout_contains_blocked = False
    local_post_codex_stdout_blocked_reason = ""
    local_post_codex_route_status = "not_started"
    local_post_codex_route_decision = "manual_review_prompt333_execution_artifacts"
    local_post_codex_route_next_action = "manual_review_prompt333_execution_artifacts"
    local_post_codex_route_targeted_contract_fix_recommended = False
    local_post_codex_route_approve_commit_tag_allowed = False
    prompt334_stale_post_codex_artifact_detected = False
    prompt334_stale_post_codex_artifact_regeneration_attempted = False
    prompt334_stale_post_codex_artifact_regeneration_reason = (
        "prompt333_completed_artifacts_not_ready_for_reconciliation"
    )
    prompt334_stale_post_codex_artifact_regeneration_status = "not_applicable"
    local_targeted_contract_fix_route_intake_status = "not_started"
    local_targeted_contract_fix_route_intake_blocked_reason = "prompt335_not_started"
    local_targeted_contract_fix_route_intake_signal_source = "none"
    local_targeted_contract_fix_prompt_plan_status = "not_started"
    local_targeted_contract_fix_prompt_plan_blocked_reason = "prompt335_not_started"
    local_targeted_contract_fix_prompt_path_text = str(local_targeted_contract_fix_prompt_path)
    local_targeted_contract_fix_prompt_ready = False
    local_targeted_contract_fix_prompt_next_action = "manual_review_contract_fix_route_intake"
    local_targeted_contract_fix_prompt_normalized_reason = ""
    local_targeted_contract_fix_prompt_lifecycle_issue_detected = False
    local_targeted_contract_fix_prompt_state: dict[str, Any] = {}
    local_contract_fix_cycle_coordination_status = "not_started"
    local_contract_fix_cycle_coordination_blocked_reason = "prompt336_not_started"
    local_contract_fix_cycle_coordination_ready = False
    local_contract_fix_cycle_coordination_next_action = (
        "manual_review_targeted_contract_fix_prompt"
    )
    local_contract_fix_cycle_prompt_path = str(local_targeted_contract_fix_prompt_path)
    local_contract_fix_cycle_prompt_ready = False
    local_contract_fix_cycle_normalized_reason = ""
    local_contract_fix_cycle_selected_step_name = "none"
    local_contract_fix_cycle_handoff_status = "not_started"
    local_contract_fix_cycle_handoff_next_action = "manual_review_targeted_contract_fix_prompt"
    local_daemon_lite_wrapper_status = "not_started"
    local_daemon_lite_wrapper_blocked_reason = "prompt337_not_started"
    local_daemon_lite_wrapper_ready = False
    local_daemon_lite_wrapper_decision = "manual_review_contract_fix_cycle_handoff"
    local_daemon_lite_wrapper_next_action = "manual_review_contract_fix_cycle_handoff"
    local_daemon_lite_wrapper_selected_step_name = "none"
    local_daemon_lite_wrapper_prompt_path = str(local_targeted_contract_fix_prompt_path)
    local_daemon_lite_wrapper_bounded_execution = True
    local_daemon_lite_wrapper_total_codex_invocation_budget = 1
    local_targeted_contract_fix_execution_status = "blocked"
    local_targeted_contract_fix_execution_blocked_reason = (
        "prompt338_targeted_contract_fix_execution_not_started"
    )
    local_targeted_contract_fix_execution_next_action = (
        "manual_review_targeted_contract_fix_execution_readiness"
    )
    local_targeted_contract_fix_execution_codex_invoked = False
    local_targeted_contract_fix_execution_exit_code: int | None = None
    local_targeted_contract_fix_execution_changed_tracked_file_count = 0
    local_targeted_contract_fix_execution_stdout_path_text = str(
        local_targeted_contract_fix_execution_stdout_path
    )
    local_targeted_contract_fix_execution_stderr_path_text = str(
        local_targeted_contract_fix_execution_stderr_path
    )
    local_post_targeted_contract_fix_status = "blocked"
    local_post_targeted_contract_fix_blocked_reason = "prompt339_not_started"
    local_post_targeted_contract_fix_classification = (
        "targeted_contract_fix_execution_not_ready"
    )
    local_post_targeted_contract_fix_route_decision = (
        "manual_review_prompt338_execution_artifacts"
    )
    local_post_targeted_contract_fix_next_action = (
        "manual_review_prompt338_execution_artifacts"
    )
    local_post_targeted_contract_fix_approve_commit_tag_ready = False
    local_post_targeted_contract_fix_changed_tracked_file_count = 0
    local_post_targeted_contract_fix_unexpected_tracked_file_count = 0
    local_bounded_approve_commit_tag_status = "blocked"
    local_bounded_approve_commit_tag_execution_status = "blocked"
    local_bounded_approve_commit_tag_blocked_reason = "prompt340_not_started"
    local_bounded_approve_commit_tag_next_action = (
        "manual_review_prompt339_approve_route_not_ready"
    )
    local_bounded_approve_commit_tag_commit_performed = False
    local_bounded_approve_commit_tag_tag_performed = False
    local_bounded_approve_commit_tag_commit_hash = ""
    local_bounded_approve_commit_tag_tag_name = _LOCAL_BOUNDED_APPROVE_COMMIT_TAG_TAG_NAME
    local_bounded_approve_commit_tag_worktree_clean = False
    local_post_commit_cycle_closure_status = "blocked"
    local_post_commit_cycle_closure_blocked_reason = "prompt340_commit_tag_artifacts_not_ready"
    local_post_commit_cycle_closure_cycle_closed = False
    local_post_commit_cycle_closure_reentry_allowed = False
    local_post_commit_cycle_closure_should_continue = False
    local_post_commit_cycle_closure_cycle_decision = "manual_review_post_commit_cycle_closure"
    local_post_commit_cycle_closure_next_action = "manual_review_prompt340_commit_tag_artifacts"
    local_post_commit_cycle_closure_commit_hash = ""
    local_post_commit_cycle_closure_tag_name = _LOCAL_BOUNDED_APPROVE_COMMIT_TAG_TAG_NAME
    local_post_commit_cycle_closure_no_change_cycle_closure = False
    local_post_commit_cycle_closure_commit_required = True
    local_post_commit_cycle_closure_tag_required = True
    local_post_commit_cycle_closure_local_commit_tag_complete = False
    local_next_cycle_reentry_status = "blocked"
    local_next_cycle_reentry_next_action = "manual_review_prompt340_commit_tag_artifacts"
    local_next_cycle_reentry_selected_step_name = ""
    local_autonomous_continuation_status = "blocked"
    local_autonomous_continuation_blocked_reason = (
        "prompt341_cycle_closure_reentry_not_ready"
    )
    local_autonomous_continuation_next_action = (
        "manual_review_prompt341_cycle_closure_reentry"
    )
    local_autonomous_continuation_reentry_connected = False
    local_autonomous_continuation_next_cycle_ready = False
    local_autonomous_continuation_selected_step_name = ""
    local_autonomous_loop_completion_status = "blocked"
    local_autonomous_loop_completion_final_decision = (
        "manual_review_prompt341_cycle_closure_reentry"
    )
    local_only_complete_autonomous_loop_ready = False
    local_autonomous_loop_complete = False
    local_autonomous_continuation_no_change_cycle_closure = False
    local_autonomous_continuation_commit_required = True
    local_autonomous_continuation_tag_required = True
    targeted_fix_prompt_status = "not_applicable"
    targeted_fix_prompt_text = ""
    targeted_fix_prompt_resolved_path = ""
    review_route_status = "waiting_for_review_response"
    review_route_decision = "none"
    review_route_reason = "review_response_missing"
    review_route_next_action = "wait_for_chatgpt_diff_review_response"
    review_route_blocked_reason = "review_response_missing"
    review_route_source = ""
    review_route_targeted_fix_prompt_path = ""
    review_route_should_prepare_commit = False
    review_route_should_prepare_targeted_fix = False
    review_route_should_prepare_reject = False
    targeted_fix_boundary_status = "not_applicable"
    targeted_fix_boundary_decision = "none"
    targeted_fix_boundary_reason = "route_not_targeted_fix"
    targeted_fix_boundary_next_action = "none"
    targeted_fix_boundary_blocked_reason = "route_not_targeted_fix"
    targeted_fix_boundary_source_prompt_path = ""
    targeted_fix_boundary_codex_prompt_path = ""
    targeted_fix_boundary_prompt_ready = False
    targeted_fix_boundary_should_execute_codex = False
    targeted_fix_reentry_execution_enabled = _read_flag(
        "project_browser_autonomous_targeted_fix_reentry_execution_enabled",
        default=False,
    )
    targeted_fix_reentry_execution_confirmed = _read_flag(
        "project_browser_autonomous_targeted_fix_reentry_execution_confirmed",
        default=False,
    )
    targeted_fix_post_reentry_codex_reentry_execution_enabled = _read_flag(
        "project_browser_autonomous_targeted_fix_post_reentry_codex_reentry_execution_enabled",
        default=False,
    )
    targeted_fix_post_reentry_codex_reentry_execution_confirmed = _read_flag(
        "project_browser_autonomous_targeted_fix_post_reentry_codex_reentry_execution_confirmed",
        default=False,
    )
    targeted_fix_post_reentry_current_cycle_count = _read_non_negative_int_flag(
        "project_browser_autonomous_targeted_fix_post_reentry_current_cycle_count",
        default=_TARGETED_FIX_POST_REENTRY_BOUNDED_CYCLE_DEFAULT_CURRENT_CYCLE_COUNT,
    )
    targeted_fix_post_reentry_max_cycle_count = _read_non_negative_int_flag(
        "project_browser_autonomous_targeted_fix_post_reentry_max_cycle_count",
        default=_TARGETED_FIX_POST_REENTRY_BOUNDED_CYCLE_DEFAULT_MAX_CYCLE_COUNT,
    )
    targeted_fix_reentry_execution_gate_status = "not_applicable"
    targeted_fix_reentry_execution_status = "not_executed"
    targeted_fix_reentry_execution_attempted = False
    targeted_fix_reentry_execution_exit_code = 0
    targeted_fix_reentry_execution_blocked_reason = "route_not_targeted_fix"
    targeted_fix_reentry_execution_prompt_path = str(targeted_fix_codex_prompt_path)
    targeted_fix_reentry_execution_should_execute_codex = False
    targeted_fix_post_reentry_diff_capture_status = "not_applicable"
    targeted_fix_post_reentry_diff_capture_attempted = False
    targeted_fix_post_reentry_diff_capture_blocked_reason = "reentry_not_completed"
    targeted_fix_post_reentry_diff_has_diff = False
    targeted_fix_post_reentry_diff_changed_file_count = 0
    targeted_fix_post_reentry_review_handoff_status = "not_applicable"
    targeted_fix_post_reentry_review_required = False
    targeted_fix_post_reentry_review_assimilation_status = "not_applicable"
    targeted_fix_post_reentry_review_assimilation_blocked_reason = "review_handoff_not_ready"
    targeted_fix_post_reentry_review_decision = "none"
    targeted_fix_post_reentry_route_status = "blocked"
    targeted_fix_post_reentry_route_decision = "manual_review_required"
    targeted_fix_post_reentry_next_action = "manual_review_required"
    targeted_fix_post_reentry_manual_review_required = True
    targeted_fix_post_reentry_targeted_fix_required = False
    targeted_fix_post_reentry_route_executor_boundary_status = "blocked"
    targeted_fix_post_reentry_route_executor_kind = "manual_review"
    targeted_fix_post_reentry_route_executor_next_action = "manual_review_required"
    targeted_fix_post_reentry_route_executor_execution_allowed = False
    targeted_fix_post_reentry_route_executor_manual_review_required = True
    targeted_fix_post_reentry_cycle_closure_allowed = False
    targeted_fix_post_reentry_approval_boundary_allowed = False
    targeted_fix_post_reentry_reject_boundary_allowed = False
    targeted_fix_post_reentry_targeted_fix_prompt_emission_allowed = False
    targeted_fix_post_reentry_codex_reentry_allowed = False
    targeted_fix_post_reentry_next_step_handoff_status = "blocked"
    targeted_fix_post_reentry_cycle_closure_status = "blocked"
    targeted_fix_post_reentry_terminal_state = "blocked"
    targeted_fix_post_reentry_cycle_closed = False
    targeted_fix_post_reentry_safe_to_stop = False
    targeted_fix_post_reentry_safe_to_commit_prompt_changes = False
    targeted_fix_post_reentry_requires_codex_reentry = False
    targeted_fix_post_reentry_requires_manual_review = True
    targeted_fix_post_reentry_prompt_emission_status = "not_applicable"
    targeted_fix_post_reentry_prompt_emission_blocked_reason = "route_not_targeted_fix"
    targeted_fix_post_reentry_prompt_written = False
    targeted_fix_post_reentry_prompt_ready_for_codex_reentry = False
    targeted_fix_post_reentry_prompt_emission_next_action = "none"
    targeted_fix_post_reentry_emitted_prompt_path = str(targeted_fix_codex_prompt_path)
    targeted_fix_post_reentry_codex_reentry_execution_status = "not_applicable"
    targeted_fix_post_reentry_codex_reentry_gate_status = "not_applicable"
    targeted_fix_post_reentry_codex_reentry_blocked_reason = "prompt_emission_not_ready"
    targeted_fix_post_reentry_codex_reentry_attempted = False
    targeted_fix_post_reentry_codex_reentry_executed = False
    targeted_fix_post_reentry_codex_reentry_exit_code: int | None = None
    targeted_fix_post_reentry_codex_reentry_next_action = "none"
    targeted_fix_post_reentry_bounded_cycle_status = "blocked"
    targeted_fix_post_reentry_bounded_cycle_decision = "blocked"
    targeted_fix_post_reentry_bounded_cycle_blocked_reason = (
        "post_reentry_bounded_cycle_inputs_incomplete"
    )
    targeted_fix_post_reentry_bounded_cycle_complete = False
    targeted_fix_post_reentry_bounded_cycle_should_continue = False
    targeted_fix_post_reentry_bounded_cycle_should_emit_prompt = False
    targeted_fix_post_reentry_bounded_cycle_should_execute_codex = False
    targeted_fix_post_reentry_bounded_cycle_should_capture_diff = False
    targeted_fix_post_reentry_bounded_cycle_next_action = "manual_review_required"
    approve_commit_tag_boundary_status = "not_applicable"
    approve_commit_tag_boundary_decision = "none"
    approve_commit_tag_boundary_reason = "route_not_approve"
    approve_commit_tag_boundary_next_action = "none"
    approve_commit_tag_boundary_blocked_reason = "route_not_approve"
    approve_commit_tag_boundary_commit_message = ""
    approve_commit_tag_boundary_tag_name = ""
    approve_commit_tag_boundary_commands_resolved_path = ""
    approve_commit_tag_boundary_metadata_resolved_path = ""
    approve_commit_tag_boundary_should_execute_commit = False
    approve_commit_tag_boundary_should_execute_tag = False
    approve_commit_tag_boundary_ready = False
    approve_commit_tag_plan_ready = False
    approve_commit_tag_tracked_files_allowed = False
    approve_commit_tag_changed_tracked_files: list[str] = []
    approve_commit_tag_unexpected_tracked_files: list[str] = []
    approve_commit_tag_explicit_add_paths: list[str] = []
    approve_commit_tag_proposed_commit_message = ""
    approve_commit_tag_proposed_tag = ""
    approve_commit_tag_command_file_path = str(approve_commit_tag_boundary_commands_path)
    approve_commit_tag_execution_allowed = False
    approve_commit_tag_boundary_path = str(approve_commit_tag_boundary_metadata_path)
    approve_commit_tag_plan_path = str(approve_commit_tag_plan_metadata_path)
    approve_commit_tag_execution_enabled = False
    approve_commit_tag_execution_confirmed = False
    approve_commit_tag_execution_gate_status = "execution_not_enabled"
    approve_commit_tag_execution_status = "not_executed"
    approve_commit_tag_execution_attempted = False
    approve_commit_tag_execution_exit_code = 0
    approve_commit_tag_execution_blocked_reason = "execution_not_enabled"
    approve_commit_tag_execution_commit_message = ""
    approve_commit_tag_execution_tag_name = ""
    approve_commit_tag_execution_should_commit = False
    approve_commit_tag_execution_should_tag = False
    approve_commit_tag_artifact_reconciliation_status = "not_started"
    approve_commit_tag_artifact_reconciliation_blocked_reason = "none"
    approve_commit_tag_artifact_reconciliation_stale_artifacts_detected = False
    approve_commit_tag_artifact_reconciliation_already_committed = False
    approve_commit_tag_artifact_reconciliation_already_tagged = False
    approve_commit_tag_artifact_reconciliation_next_action = "manual_review_required"
    approve_commit_tag_artifact_reconciliation_receipt_path = str(
        approve_commit_tag_artifact_reconciliation_receipt_file_path
    )
    remote_readiness_boundary_status = "blocked"
    remote_readiness_blocked_reason = "approve_commit_tag_reconciliation_not_completed"
    remote_readiness_remote_ready = False
    remote_readiness_push_ready = False
    remote_readiness_pr_ready = False
    remote_readiness_merge_ready = False
    remote_readiness_worktree_clean = False
    remote_readiness_expected_head_tag_present = False
    remote_readiness_remote_configured = False
    remote_readiness_upstream_configured = False
    remote_readiness_next_action = "complete_approve_commit_tag_reconciliation"
    remote_readiness_boundary_path = str(remote_readiness_boundary_metadata_path)
    remote_readiness_plan_path = str(remote_readiness_plan_metadata_path)
    local_end_to_end_readiness_status = "blocked"
    local_end_to_end_readiness_blocked_reason = "approve_commit_tag_reconciliation_not_completed"
    local_end_to_end_ready = False
    local_components_ready = False
    integrated_local_runner_ready = False
    implementation_prompt_generation_status = "mostly_ready"
    github_deferred = True
    remote_required = False
    local_end_to_end_next_action = "complete_approve_commit_tag_reconciliation"
    local_end_to_end_component_matrix_surface_path = str(
        local_end_to_end_controller_component_matrix_path
    )
    local_end_to_end_readiness_boundary_surface_path = str(
        local_end_to_end_controller_readiness_boundary_path
    )
    local_end_to_end_gap_report_surface_path = str(local_end_to_end_controller_gap_report_path)
    local_end_to_end_dry_run_plan_status = "blocked"
    local_end_to_end_dry_run_blocked_reason = "local_end_to_end_readiness_not_available"
    local_end_to_end_dry_run_plan_ready = False
    local_end_to_end_dry_run_step_count = 16
    local_end_to_end_dry_run_execution_allowed = False
    local_end_to_end_dry_run_next_action = "complete_local_end_to_end_readiness_boundary"
    local_end_to_end_dry_run_plan_surface_path = str(local_end_to_end_dry_run_plan_path)
    local_end_to_end_dry_run_step_matrix_surface_path = str(
        local_end_to_end_dry_run_step_matrix_path
    )
    local_end_to_end_dry_run_receipt_surface_path = str(local_end_to_end_dry_run_receipt_path)
    local_one_shot_gate_status = "blocked"
    local_one_shot_blocked_reason = "local_end_to_end_dry_run_plan_not_ready"
    local_one_shot_gate_ready = False
    local_one_shot_selected_step_id = 1
    local_one_shot_selected_step_name = "read_current_state"
    local_one_shot_execution_allowed = False
    local_one_shot_next_action = "complete_local_end_to_end_dry_run_plan_builder"
    local_one_shot_gate_surface_path = str(local_end_to_end_one_shot_execution_gate_path)
    local_one_shot_step_selection_surface_path = str(
        local_end_to_end_one_shot_step_selection_path
    )
    local_one_shot_receipt_surface_path = str(local_end_to_end_one_shot_execution_receipt_path)
    bounded_local_loop_status = "blocked"
    bounded_local_loop_blocked_reason = "local_one_shot_or_dry_run_artifacts_missing"
    bounded_local_loop_ready = False
    bounded_local_loop_complete = False
    bounded_local_loop_should_continue = False
    bounded_local_loop_selected_step_id: int | None = 1
    bounded_local_loop_selected_step_name = "read_current_state"
    bounded_local_loop_execution_allowed = False
    bounded_local_loop_next_action = "complete_local_one_shot_gate_before_bounded_loop"
    bounded_local_loop_state_surface_path = str(bounded_local_autonomous_loop_state_path)
    bounded_local_loop_decision_surface_path = str(
        bounded_local_autonomous_loop_decision_path
    )
    bounded_local_loop_receipt_surface_path = str(bounded_local_autonomous_loop_receipt_path)
    selected_step_execution_adapter_status = "blocked"
    selected_step_execution_blocked_reason = "bounded_local_loop_artifacts_missing"
    selected_step_execution_ready = False
    selected_step_execution_selected_step_id = 1
    selected_step_execution_selected_step_name = "read_current_state"
    selected_step_execution_operation = "read_current_state"
    selected_step_execution_allowed = False
    selected_step_execution_performed = False
    selected_step_execution_next_action = (
        "complete_bounded_local_loop_before_selected_step_execution_adapter"
    )
    selected_step_execution_adapter_state_surface_path = str(
        selected_step_execution_adapter_state_path
    )
    selected_step_execution_plan_surface_path = str(selected_step_execution_plan_path)
    selected_step_execution_receipt_surface_path = str(
        selected_step_execution_receipt_path
    )
    selected_step_live_execution_gate_status = "blocked"
    selected_step_live_execution_blocked_reason = "selected_step_execution_adapter_artifacts_missing"
    selected_step_live_execution_ready = False
    selected_step_live_execution_allowed = False
    selected_step_live_execution_performed = False
    selected_step_live_execution_selected_step_id = 1
    selected_step_live_execution_selected_step_name = "read_current_state"
    selected_step_live_execution_operation = "read_current_state"
    selected_step_live_execution_result_status = "not_run"
    selected_step_live_execution_next_action = (
        "complete_selected_step_execution_adapter_before_live_gate"
    )
    selected_step_live_execution_gate_surface_path = str(selected_step_live_execution_gate_path)
    selected_step_live_execution_result_surface_path = str(selected_step_live_execution_result_path)
    selected_step_live_execution_receipt_surface_path = str(
        selected_step_live_execution_receipt_path
    )
    selected_step_live_execution_read_current_state_completed = False
    selected_step_execution_result_route_status = "blocked"
    selected_step_execution_result_route_blocked_reason = (
        "selected_step_live_execution_artifacts_missing_or_invalid"
    )
    selected_step_execution_result_route_decision = "blocked"
    selected_step_execution_result_route_next_action = (
        "prepare_selected_step_execution_result_route"
    )
    selected_step_execution_result_route_should_continue = False
    selected_step_execution_result_route_capture_surface_path = str(
        selected_step_execution_result_route_capture_path
    )
    selected_step_execution_result_route_decision_surface_path = str(
        selected_step_execution_result_route_decision_path
    )
    selected_step_execution_result_route_receipt_surface_path = str(
        selected_step_execution_result_route_receipt_path
    )
    local_only_autonomous_loop_closure_status = "blocked"
    local_only_autonomous_loop_closure_blocked_reason = (
        "selected_step_result_route_artifacts_missing_or_invalid"
    )
    local_only_autonomous_loop_closure_decision = "blocked"
    local_only_autonomous_loop_closure_next_action = (
        "complete_selected_step_result_route_before_loop_closure"
    )
    local_only_autonomous_loop_v1_complete = False
    local_only_autonomous_loop_closed = False
    local_only_autonomous_loop_closure_should_continue = False
    local_only_autonomous_loop_closure_state_surface_path = str(
        local_only_autonomous_loop_closure_state_path
    )
    local_only_autonomous_loop_closure_decision_surface_path = str(
        local_only_autonomous_loop_closure_decision_path
    )
    local_only_autonomous_loop_closure_receipt_surface_path = str(
        local_only_autonomous_loop_closure_receipt_path
    )
    local_autonomous_cycle_v2_status = "blocked"
    local_autonomous_cycle_v2_cycle_status = "blocked"
    local_autonomous_cycle_v2_next_action = "manual_review_prompt330_closure_before_v2_cycle"
    local_autonomous_cycle_v2_selected_step_id: int | None = None
    local_autonomous_cycle_v2_selected_step_name: str | None = None
    local_autonomous_cycle_v2_selected_step_operation: str | None = None
    local_autonomous_cycle_v2_decision = "blocked"
    local_autonomous_cycle_v2_ready = False
    local_autonomous_cycle_v2_blocked_reason = "prompt330_closure_status_not_completed"
    local_autonomous_cycle_v2_readiness_reason = (
        "prompt330_closure_not_valid_for_local_autonomous_cycle_v2"
    )
    local_autonomous_cycle_v2_run_id = "local-autonomous-v2"
    local_autonomous_cycle_v2_cycle_id = "local-autonomous-v2-cycle-1"
    local_autonomous_cycle_v2_current_cycle = _LOCAL_AUTONOMOUS_CYCLE_V2_CURRENT_CYCLE
    local_autonomous_cycle_v2_max_cycles = _LOCAL_AUTONOMOUS_CYCLE_V2_MAX_CYCLES
    local_autonomous_cycle_v2_state_surface_path = str(local_autonomous_cycle_v2_state_path)
    local_autonomous_cycle_v2_decision_surface_path = str(
        local_autonomous_cycle_v2_decision_path
    )
    local_autonomous_cycle_v2_receipt_surface_path = str(local_autonomous_cycle_v2_receipt_path)
    local_codex_one_shot_handoff_status = "blocked"
    local_codex_one_shot_handoff_handoff_status = "blocked"
    local_codex_one_shot_handoff_next_action = (
        "manual_review_local_autonomous_cycle_v2_before_codex_handoff"
    )
    local_codex_one_shot_handoff_blocked_reason = (
        "local_autonomous_cycle_v2_not_valid_for_codex_one_shot_handoff"
    )
    local_codex_one_shot_handoff_readiness_reason = (
        "local_autonomous_cycle_v2_not_valid_for_codex_one_shot_handoff"
    )
    local_codex_one_shot_handoff_prompt_ready = False
    local_codex_one_shot_handoff_command_ready = False
    local_codex_one_shot_handoff_codex_invocation_allowed = False
    local_codex_one_shot_handoff_execution_allowed = False
    local_codex_one_shot_handoff_max_codex_invocations = 1
    local_codex_one_shot_handoff_codex_invocation_count = 0
    local_codex_one_shot_handoff_selected_step_id: int | None = None
    local_codex_one_shot_handoff_selected_step_name: str | None = None
    local_codex_one_shot_handoff_selected_step_operation: str | None = None
    local_codex_one_shot_handoff_prompt_path: str | None = None
    local_codex_one_shot_handoff_command_display = ""
    local_codex_one_shot_handoff_run_id = "local-autonomous-v2"
    local_codex_one_shot_handoff_cycle_id = "local-autonomous-v2-cycle-1"
    local_codex_one_shot_handoff_current_cycle = _LOCAL_AUTONOMOUS_CYCLE_V2_CURRENT_CYCLE
    local_codex_one_shot_handoff_max_cycles = _LOCAL_AUTONOMOUS_CYCLE_V2_MAX_CYCLES
    local_codex_one_shot_execution_status = "blocked"
    local_codex_one_shot_execution_execution_status = "blocked"
    local_codex_one_shot_execution_next_action = (
        "manual_review_local_codex_one_shot_handoff_before_execution"
    )
    local_codex_one_shot_execution_blocked_reason = (
        "local_codex_one_shot_handoff_not_valid_for_execution"
    )
    local_codex_one_shot_execution_readiness_reason = (
        "local_codex_one_shot_handoff_not_valid_for_execution"
    )
    local_codex_one_shot_execution_codex_invoked = False
    local_codex_one_shot_execution_codex_invocation_allowed = False
    local_codex_one_shot_execution_execution_allowed = False
    local_codex_one_shot_execution_execution_attempted = False
    local_codex_one_shot_execution_execution_completed = False
    local_codex_one_shot_execution_execution_exit_code: int | None = None
    local_codex_one_shot_execution_max_codex_invocations = 1
    local_codex_one_shot_execution_codex_invocation_count = 0
    local_codex_one_shot_execution_selected_step_id: int | None = None
    local_codex_one_shot_execution_selected_step_name: str | None = None
    local_codex_one_shot_execution_selected_step_operation: str | None = None
    local_codex_one_shot_execution_prompt_path: str | None = None
    local_codex_one_shot_execution_stdout_path_text: str | None = None
    local_codex_one_shot_execution_stderr_path_text: str | None = None
    local_codex_one_shot_execution_result_path_text: str | None = None
    local_codex_one_shot_execution_run_id = "local-autonomous-v2"
    local_codex_one_shot_execution_cycle_id = "local-autonomous-v2-cycle-1"
    local_codex_one_shot_execution_current_cycle = _LOCAL_AUTONOMOUS_CYCLE_V2_CURRENT_CYCLE
    local_codex_one_shot_execution_max_cycles = _LOCAL_AUTONOMOUS_CYCLE_V2_MAX_CYCLES
    prompt365_effective_dry_run = _resolve_prompt365_effective_dry_run()
    prompt365_runtime_source_mutation_guard_status = (
        "clean" if prompt365_effective_dry_run else "not_applicable"
    )
    prompt365_dry_run_source_mutation_detected = False
    prompt365_mutation_capable_path_blocked = False
    prompt365_before_changed_tracked_files: list[str] = []
    prompt365_after_changed_tracked_files: list[str] = []
    prompt365_new_changed_tracked_files: list[str] = []
    prompt365_blocked_reason = ""
    prompt365_next_action = "continue"
    prompt365_manual_required = False
    prompt365_summary = (
        "Prompt365 dry-run source mutation guard applies only to dry-run transport mode."
    )
    prompt365_git_state_available = True
    prompt365_mutation_capable_dry_run_attempted = False
    normalized_execution_repo_path = _normalize_text(
        execution_repo_path,
        default=_APPROVE_COMMIT_TAG_EXECUTION_REPO_PATH,
    )
    if prompt365_effective_dry_run:
        (
            prompt365_git_state_available,
            prompt365_before_changed_tracked_files,
        ) = _collect_changed_tracked_files(normalized_execution_repo_path)
        if not prompt365_git_state_available:
            prompt365_runtime_source_mutation_guard_status = "blocked"
            prompt365_blocked_reason = (
                "dry_run_source_mutation_guard_git_state_unavailable"
            )
            prompt365_next_action = "review_dry_run_source_mutation_guard_git_state"
            prompt365_manual_required = True
            prompt365_summary = (
                "Prompt365 blocked dry-run source mutation verification because tracked git state could not be collected before the guarded runtime segment."
            )
    completed_result_source_status = "not_completed"
    stop_reason = "execution_not_enabled"
    enabled = _read_flag(
        "project_browser_autonomous_one_cycle_controller_enabled",
        default=False,
    )
    execute_enabled = _read_flag(
        "project_browser_autonomous_one_cycle_controller_execute_enabled",
        default=False,
    )
    exec_plan_execution_status = "not_executed"
    execution_attempted = False
    execution_blocked_reason = "execution_not_enabled"
    execution_gate_status = "execution_not_enabled"
    execution_exit_code = -1
    execution_started_at = ""
    execution_finished_at = ""
    if enabled and execute_enabled:
        if dry_run:
            stop_reason = "dry_run_execution_suppressed"
            execution_blocked_reason = "dry_run_execution_suppressed"
            execution_gate_status = "dry_run_suppressed"
        else:
            stop_reason = "none"
            execution_blocked_reason = "none"
            execution_gate_status = "ready_for_single_execution"
    exec_plan_safety = _evaluate_one_cycle_controller_exec_plan_safety(
        exec_plan_path=exec_plan_path
    )
    exec_plan_safety_status = _normalize_text(
        exec_plan_safety.get("exec_plan_safety_status"),
        default="blocked",
    )
    exec_plan_blocked_reason = _normalize_text(
        exec_plan_safety.get("exec_plan_blocked_reason"),
        default="exec_plan_read_error",
    )
    exec_plan_required_fragments_present = _normalize_string_list(
        exec_plan_safety.get("exec_plan_required_fragments_present")
    )
    exec_plan_banned_fragments_present = _normalize_string_list(
        exec_plan_safety.get("exec_plan_banned_fragments_present")
    )
    runtime_posture = [
        "single_execution_path_available",
        "single_cycle_only",
        "execution_explicitly_gated",
        "post_execution_handoff_local_tracked_diff_only",
        "post_execution_handoff_review_request_artifact_only",
        "no_commit_tag_push_pr_merge",
        "no_daemon_no_polling_no_unbounded_retry",
    ]

    artifact_paths = {
        "one_cycle_controller_result_json": str(output_json_path),
        "one_cycle_controller_summary_md": str(output_summary_path),
        "local_codex_exec_plan_sh": str(exec_plan_path),
        "one_cycle_controller_exec_stdout_log": str(execution_stdout_path),
        "one_cycle_controller_exec_stderr_log": str(execution_stderr_path),
        "one_cycle_controller_runlog_md": str(execution_runlog_path),
        "one_cycle_controller_diff_stat_txt": str(diff_stat_path),
        "one_cycle_controller_diff_name_status_txt": str(diff_name_status_path),
        "one_cycle_controller_diff_patch": str(diff_patch_path),
        "one_cycle_controller_review_request_md": str(review_request_path),
        "one_cycle_controller_review_handoff_json": str(review_handoff_path),
        "one_cycle_controller_review_response_json": str(review_response_path),
        "one_cycle_controller_targeted_fix_prompt_md": str(targeted_fix_prompt_path),
        "one_cycle_controller_targeted_fix_codex_prompt_md": str(targeted_fix_codex_prompt_path),
        "one_cycle_controller_targeted_fix_reentry_execution_receipt_json": str(
            targeted_fix_reentry_execution_receipt_path
        ),
        "one_cycle_controller_targeted_fix_post_reentry_diff_capture_json": str(
            targeted_fix_post_reentry_diff_capture_path
        ),
        "one_cycle_controller_targeted_fix_post_reentry_diff_patch": str(
            targeted_fix_post_reentry_diff_patch_path
        ),
        "one_cycle_controller_targeted_fix_post_reentry_diff_stat_txt": str(
            targeted_fix_post_reentry_diff_stat_path
        ),
        "one_cycle_controller_targeted_fix_post_reentry_diff_name_status_txt": str(
            targeted_fix_post_reentry_diff_name_status_path
        ),
        "one_cycle_controller_targeted_fix_post_reentry_review_handoff_json": str(
            targeted_fix_post_reentry_review_handoff_path
        ),
        "one_cycle_controller_targeted_fix_post_reentry_review_response_json": str(
            targeted_fix_post_reentry_review_response_path
        ),
        "one_cycle_controller_targeted_fix_post_reentry_review_assimilation_json": str(
            targeted_fix_post_reentry_review_assimilation_path
        ),
        "one_cycle_controller_targeted_fix_post_reentry_route_decision_json": str(
            targeted_fix_post_reentry_route_decision_path
        ),
        "one_cycle_controller_targeted_fix_post_reentry_route_executor_boundary_json": str(
            targeted_fix_post_reentry_route_executor_boundary_path
        ),
        "one_cycle_controller_targeted_fix_post_reentry_next_step_handoff_json": str(
            targeted_fix_post_reentry_next_step_handoff_path
        ),
        "one_cycle_controller_targeted_fix_post_reentry_cycle_closure_result_json": str(
            targeted_fix_post_reentry_cycle_closure_result_path
        ),
        "one_cycle_controller_targeted_fix_post_reentry_terminal_summary_json": str(
            targeted_fix_post_reentry_terminal_summary_path
        ),
        "one_cycle_controller_targeted_fix_post_reentry_prompt_emission_json": str(
            targeted_fix_post_reentry_prompt_emission_path
        ),
        "one_cycle_controller_targeted_fix_post_reentry_prompt_emission_receipt_json": str(
            targeted_fix_post_reentry_prompt_emission_receipt_path
        ),
        "one_cycle_controller_targeted_fix_post_reentry_codex_reentry_execution_receipt_json": str(
            targeted_fix_post_reentry_codex_reentry_execution_receipt_path
        ),
        "one_cycle_controller_targeted_fix_post_reentry_codex_reentry_execution_stdout_txt": str(
            targeted_fix_post_reentry_codex_reentry_execution_stdout_path
        ),
        "one_cycle_controller_targeted_fix_post_reentry_codex_reentry_execution_stderr_txt": str(
            targeted_fix_post_reentry_codex_reentry_execution_stderr_path
        ),
        "one_cycle_controller_targeted_fix_post_reentry_bounded_cycle_state_json": str(
            targeted_fix_post_reentry_bounded_cycle_state_path
        ),
        "one_cycle_controller_targeted_fix_post_reentry_bounded_cycle_decision_json": str(
            targeted_fix_post_reentry_bounded_cycle_decision_path
        ),
        "one_cycle_controller_targeted_fix_post_reentry_bounded_cycle_receipt_json": str(
            targeted_fix_post_reentry_bounded_cycle_receipt_path
        ),
        "one_cycle_controller_approve_commit_tag_boundary_json": str(
            approve_commit_tag_boundary_metadata_path
        ),
        "one_cycle_controller_approve_commit_tag_plan_json": str(
            approve_commit_tag_plan_metadata_path
        ),
        "one_cycle_controller_approve_commit_tag_artifact_reconciliation_receipt_json": str(
            approve_commit_tag_artifact_reconciliation_receipt_file_path
        ),
        "one_cycle_controller_approve_commit_tag_commands_sh": str(
            approve_commit_tag_boundary_commands_path
        ),
        "one_cycle_controller_approve_commit_tag_execution_receipt_json": str(
            approve_commit_tag_execution_receipt_path
        ),
        "one_cycle_controller_remote_readiness_boundary_json": str(
            remote_readiness_boundary_metadata_path
        ),
        "one_cycle_controller_remote_readiness_plan_json": str(
            remote_readiness_plan_metadata_path
        ),
        "one_cycle_controller_local_end_to_end_controller_component_matrix_json": str(
            local_end_to_end_controller_component_matrix_path
        ),
        "one_cycle_controller_local_end_to_end_controller_readiness_boundary_json": str(
            local_end_to_end_controller_readiness_boundary_path
        ),
        "one_cycle_controller_local_end_to_end_controller_gap_report_json": str(
            local_end_to_end_controller_gap_report_path
        ),
        "one_cycle_controller_local_end_to_end_dry_run_plan_json": str(
            local_end_to_end_dry_run_plan_path
        ),
        "one_cycle_controller_local_end_to_end_dry_run_step_matrix_json": str(
            local_end_to_end_dry_run_step_matrix_path
        ),
        "one_cycle_controller_local_end_to_end_dry_run_receipt_json": str(
            local_end_to_end_dry_run_receipt_path
        ),
        "one_cycle_controller_local_end_to_end_one_shot_execution_gate_json": str(
            local_end_to_end_one_shot_execution_gate_path
        ),
        "one_cycle_controller_local_end_to_end_one_shot_step_selection_json": str(
            local_end_to_end_one_shot_step_selection_path
        ),
        "one_cycle_controller_local_end_to_end_one_shot_execution_receipt_json": str(
            local_end_to_end_one_shot_execution_receipt_path
        ),
        "one_cycle_controller_bounded_local_autonomous_loop_state_json": str(
            bounded_local_autonomous_loop_state_path
        ),
        "one_cycle_controller_bounded_local_autonomous_loop_decision_json": str(
            bounded_local_autonomous_loop_decision_path
        ),
        "one_cycle_controller_bounded_local_autonomous_loop_receipt_json": str(
            bounded_local_autonomous_loop_receipt_path
        ),
        "one_cycle_controller_selected_step_execution_adapter_state_json": str(
            selected_step_execution_adapter_state_path
        ),
        "one_cycle_controller_selected_step_execution_plan_json": str(
            selected_step_execution_plan_path
        ),
        "one_cycle_controller_selected_step_execution_receipt_json": str(
            selected_step_execution_receipt_path
        ),
        "one_cycle_controller_selected_step_live_execution_gate_json": str(
            selected_step_live_execution_gate_path
        ),
        "one_cycle_controller_selected_step_live_execution_result_json": str(
            selected_step_live_execution_result_path
        ),
        "one_cycle_controller_selected_step_live_execution_receipt_json": str(
            selected_step_live_execution_receipt_path
        ),
        "one_cycle_controller_selected_step_execution_result_route_capture_json": str(
            selected_step_execution_result_route_capture_path
        ),
        "one_cycle_controller_selected_step_execution_result_route_decision_json": str(
            selected_step_execution_result_route_decision_path
        ),
        "one_cycle_controller_selected_step_execution_result_route_receipt_json": str(
            selected_step_execution_result_route_receipt_path
        ),
        "one_cycle_controller_local_only_autonomous_loop_closure_state_json": str(
            local_only_autonomous_loop_closure_state_path
        ),
        "one_cycle_controller_local_only_autonomous_loop_closure_decision_json": str(
            local_only_autonomous_loop_closure_decision_path
        ),
        "one_cycle_controller_local_only_autonomous_loop_closure_receipt_json": str(
            local_only_autonomous_loop_closure_receipt_path
        ),
        "one_cycle_controller_local_autonomous_cycle_v2_state_json": str(
            local_autonomous_cycle_v2_state_path
        ),
        "one_cycle_controller_local_autonomous_cycle_v2_decision_json": str(
            local_autonomous_cycle_v2_decision_path
        ),
        "one_cycle_controller_local_autonomous_cycle_v2_receipt_json": str(
            local_autonomous_cycle_v2_receipt_path
        ),
        "one_cycle_controller_local_codex_one_shot_prompt_md": str(
            local_codex_one_shot_prompt_path
        ),
        "one_cycle_controller_local_codex_one_shot_execution_handoff_json": str(
            local_codex_one_shot_execution_handoff_path
        ),
        "one_cycle_controller_local_codex_one_shot_execution_receipt_json": str(
            local_codex_one_shot_execution_receipt_path
        ),
        "one_cycle_controller_local_codex_one_shot_execution_result_json": str(
            local_codex_one_shot_execution_result_path
        ),
        "one_cycle_controller_local_codex_one_shot_execution_receipt_v2_json": str(
            local_codex_one_shot_execution_receipt_v2_path
        ),
        "one_cycle_controller_local_codex_one_shot_execution_stdout_txt": str(
            local_codex_one_shot_execution_stdout_path
        ),
        "one_cycle_controller_local_codex_one_shot_execution_stderr_txt": str(
            local_codex_one_shot_execution_stderr_path
        ),
        "one_cycle_controller_local_post_codex_diff_capture_json": str(
            local_post_codex_diff_capture_path
        ),
        "one_cycle_controller_local_post_codex_execution_outcome_json": str(
            local_post_codex_execution_outcome_path
        ),
        "one_cycle_controller_local_post_codex_route_decision_json": str(
            local_post_codex_route_decision_path
        ),
        "one_cycle_controller_local_post_codex_diff_capture_receipt_json": str(
            local_post_codex_diff_capture_receipt_path
        ),
        "one_cycle_controller_local_targeted_contract_fix_prompt_md": str(
            local_targeted_contract_fix_prompt_path
        ),
        "one_cycle_controller_local_targeted_contract_fix_prompt_plan_json": str(
            local_targeted_contract_fix_prompt_plan_path
        ),
        "one_cycle_controller_local_targeted_contract_fix_prompt_receipt_json": str(
            local_targeted_contract_fix_prompt_receipt_path
        ),
        "one_cycle_controller_local_targeted_contract_fix_route_intake_json": str(
            local_targeted_contract_fix_route_intake_path
        ),
        "one_cycle_controller_local_contract_fix_cycle_coordination_state_json": str(
            local_contract_fix_cycle_coordination_state_path
        ),
        "one_cycle_controller_local_contract_fix_cycle_coordination_decision_json": str(
            local_contract_fix_cycle_coordination_decision_path
        ),
        "one_cycle_controller_local_contract_fix_cycle_coordination_receipt_json": str(
            local_contract_fix_cycle_coordination_receipt_path
        ),
        "one_cycle_controller_local_contract_fix_cycle_execution_handoff_json": str(
            local_contract_fix_cycle_execution_handoff_path
        ),
        "one_cycle_controller_local_daemon_lite_wrapper_state_json": str(
            local_daemon_lite_wrapper_state_path
        ),
        "one_cycle_controller_local_daemon_lite_wrapper_plan_json": str(
            local_daemon_lite_wrapper_plan_path
        ),
        "one_cycle_controller_local_daemon_lite_wrapper_decision_json": str(
            local_daemon_lite_wrapper_decision_path
        ),
        "one_cycle_controller_local_daemon_lite_wrapper_receipt_json": str(
            local_daemon_lite_wrapper_receipt_path
        ),
        "one_cycle_controller_local_targeted_contract_fix_execution_state_json": str(
            local_targeted_contract_fix_execution_state_path
        ),
        "one_cycle_controller_local_targeted_contract_fix_execution_result_json": str(
            local_targeted_contract_fix_execution_result_path
        ),
        "one_cycle_controller_local_targeted_contract_fix_execution_receipt_json": str(
            local_targeted_contract_fix_execution_receipt_path
        ),
        "one_cycle_controller_local_targeted_contract_fix_execution_stdout_txt": str(
            local_targeted_contract_fix_execution_stdout_path
        ),
        "one_cycle_controller_local_targeted_contract_fix_execution_stderr_txt": str(
            local_targeted_contract_fix_execution_stderr_path
        ),
        "one_cycle_controller_local_post_targeted_contract_fix_diff_capture_json": str(
            local_post_targeted_contract_fix_diff_capture_path
        ),
        "one_cycle_controller_local_post_targeted_contract_fix_execution_outcome_json": str(
            local_post_targeted_contract_fix_execution_outcome_path
        ),
        "one_cycle_controller_local_post_targeted_contract_fix_route_decision_json": str(
            local_post_targeted_contract_fix_route_decision_path
        ),
        "one_cycle_controller_local_post_targeted_contract_fix_review_receipt_json": str(
            local_post_targeted_contract_fix_review_receipt_path
        ),
        "one_cycle_controller_local_bounded_approve_commit_tag_gate_state_json": str(
            local_bounded_approve_commit_tag_gate_state_path
        ),
        "one_cycle_controller_local_bounded_approve_commit_tag_execution_result_json": str(
            local_bounded_approve_commit_tag_execution_result_path
        ),
        "one_cycle_controller_local_bounded_approve_commit_tag_execution_receipt_json": str(
            local_bounded_approve_commit_tag_execution_receipt_path
        ),
        "one_cycle_controller_local_bounded_approve_commit_tag_plan_json": str(
            local_bounded_approve_commit_tag_plan_path
        ),
        "one_cycle_controller_local_post_commit_cycle_closure_state_json": str(
            local_post_commit_cycle_closure_state_path
        ),
        "one_cycle_controller_local_post_commit_cycle_closure_decision_json": str(
            local_post_commit_cycle_closure_decision_path
        ),
        "one_cycle_controller_local_post_commit_cycle_closure_receipt_json": str(
            local_post_commit_cycle_closure_receipt_path
        ),
        "one_cycle_controller_local_next_cycle_reentry_decision_json": str(
            local_next_cycle_reentry_decision_path
        ),
        "one_cycle_controller_local_autonomous_continuation_state_json": str(
            local_autonomous_continuation_state_path
        ),
        "one_cycle_controller_local_autonomous_continuation_decision_json": str(
            local_autonomous_continuation_decision_path
        ),
        "one_cycle_controller_local_autonomous_continuation_receipt_json": str(
            local_autonomous_continuation_receipt_path
        ),
        "one_cycle_controller_local_autonomous_next_cycle_selection_json": str(
            local_autonomous_next_cycle_selection_path
        ),
        "one_cycle_controller_local_autonomous_loop_completion_summary_json": str(
            local_autonomous_loop_completion_summary_path
        ),
    }

    requested_execution = enabled and execute_enabled and (not dry_run)
    if requested_execution:
        if max_cycles != 1:
            status = "one_cycle_controller_blocked"
            next_action = "manual_review_required"
            stop_reason = "manual_review_required"
            execution_blocked_reason = "manual_review_required"
            execution_gate_status = "ready_for_single_execution"
        elif cycle_count != 0:
            status = "one_cycle_controller_blocked"
            next_action = "manual_review_required"
            stop_reason = "manual_review_required"
            execution_blocked_reason = "manual_review_required"
            execution_gate_status = "ready_for_single_execution"
        elif exec_plan_safety_status != "safe" or exec_plan_blocked_reason != "none":
            status = "one_cycle_controller_blocked"
            next_action = "manual_review_required"
            stop_reason = (
                "exec_plan_missing"
                if exec_plan_blocked_reason == "exec_plan_missing"
                else "exec_plan_not_safe"
            )
            execution_blocked_reason = stop_reason
            execution_gate_status = "ready_for_single_execution"
        else:
            staged_check = _run_git(
                execution_repo_path,
                ["diff", "--cached", "--quiet"],
                timeout_seconds=10,
            )
            if staged_check.returncode == 1:
                status = "one_cycle_controller_blocked"
                next_action = "manual_review_required"
                stop_reason = "staged_changes_present"
                execution_blocked_reason = "staged_changes_present"
                execution_gate_status = "ready_for_single_execution"
            elif staged_check.returncode != 0:
                status = "one_cycle_controller_blocked"
                next_action = "manual_review_required"
                stop_reason = "manual_review_required"
                execution_blocked_reason = "manual_review_required"
                execution_gate_status = "ready_for_single_execution"
            else:
                unstaged_check = _run_git(
                    execution_repo_path,
                    ["diff", "--quiet"],
                    timeout_seconds=10,
                )
                if unstaged_check.returncode == 1:
                    status = "one_cycle_controller_blocked"
                    next_action = "manual_review_required"
                    stop_reason = "unstaged_changes_present"
                    execution_blocked_reason = "unstaged_changes_present"
                    execution_gate_status = "ready_for_single_execution"
                elif unstaged_check.returncode != 0:
                    status = "one_cycle_controller_blocked"
                    next_action = "manual_review_required"
                    stop_reason = "manual_review_required"
                    execution_blocked_reason = "manual_review_required"
                    execution_gate_status = "ready_for_single_execution"
                else:
                    execution_attempted = True
                    execution_started_at = _iso_now(datetime.now)
                    try:
                        completed = subprocess.run(
                            [str(exec_plan_path)],
                            text=True,
                            capture_output=True,
                            timeout=1800,
                            check=False,
                            cwd=execution_repo_path,
                        )
                        execution_exit_code = int(completed.returncode)
                        stdout_text = completed.stdout or ""
                        stderr_text = completed.stderr or ""
                    except subprocess.TimeoutExpired as exc:
                        execution_exit_code = 124
                        stdout_text = (
                            exc.stdout
                            if isinstance(exc.stdout, str)
                            else (
                                exc.stdout.decode("utf-8", errors="replace")
                                if isinstance(exc.stdout, bytes)
                                else ""
                            )
                        )
                        stderr_text = (
                            exc.stderr
                            if isinstance(exc.stderr, str)
                            else (
                                exc.stderr.decode("utf-8", errors="replace")
                                if isinstance(exc.stderr, bytes)
                                else ""
                            )
                        )
                    except OSError as exc:
                        execution_exit_code = 126
                        stdout_text = ""
                        stderr_text = str(exc).strip()
                    execution_finished_at = _iso_now(datetime.now)
                    try:
                        one_cycle_controller_dir.mkdir(parents=True, exist_ok=True)
                        execution_stdout_path.write_text(stdout_text, encoding="utf-8")
                        execution_stderr_path.write_text(stderr_text, encoding="utf-8")
                        execution_runlog_path.write_text(
                            "\n".join(
                                [
                                    "# One Cycle Controller Runlog",
                                    "",
                                    f"- Exec plan path: `{exec_plan_path}`",
                                    f"- Started at: `{execution_started_at}`",
                                    f"- Finished at: `{execution_finished_at}`",
                                    f"- Exit code: `{execution_exit_code}`",
                                    f"- Stdout path: `{execution_stdout_path}`",
                                    f"- Stderr path: `{execution_stderr_path}`",
                                ]
                            )
                            + "\n",
                            encoding="utf-8",
                        )
                    except OSError:
                        pass
                    if execution_exit_code == 0:
                        status = "one_cycle_controller_completed"
                        next_action = "wait_for_chatgpt_diff_review_response"
                        cycle_count = 1
                        codex_execution_status = "completed"
                        exec_plan_execution_status = "completed"
                        stop_reason = "review_response_required"
                        execution_blocked_reason = "none"
                        execution_gate_status = "ready_for_single_execution"
                    else:
                        status = "one_cycle_controller_blocked"
                        next_action = "manual_review_required"
                        cycle_count = 1
                        codex_execution_status = "failed"
                        exec_plan_execution_status = "failed"
                        stop_reason = "exec_plan_execution_failed"
                        execution_blocked_reason = "exec_plan_execution_failed"
                        execution_gate_status = "ready_for_single_execution"

    (
        post_execution_handoff,
        prompt334_stale_post_codex_reconciliation_state,
    ) = _maybe_reconcile_stale_prompt334_post_codex_artifacts(
        execution_repo_path=execution_repo_path,
        status=status,
        stop_reason=stop_reason,
        next_action=next_action,
        execution_attempted=execution_attempted,
        execution_exit_code=execution_exit_code,
        exec_plan_execution_status=exec_plan_execution_status,
        one_cycle_controller_dir=one_cycle_controller_dir,
        completed_result_source_path=completed_result_source_path,
    )
    if post_execution_handoff is None:
        post_execution_handoff = _build_one_cycle_post_execution_handoff(
            execution_repo_path=execution_repo_path,
            status=status,
            stop_reason=stop_reason,
            next_action=next_action,
            execution_attempted=execution_attempted,
            execution_exit_code=execution_exit_code,
            exec_plan_execution_status=exec_plan_execution_status,
            one_cycle_controller_dir=one_cycle_controller_dir,
            completed_result_source_path=completed_result_source_path,
        )
    prompt334_stale_post_codex_artifact_detected = bool(
        prompt334_stale_post_codex_reconciliation_state.get(
            "prompt334_stale_post_codex_artifact_detected",
            prompt334_stale_post_codex_artifact_detected,
        )
    )
    prompt334_stale_post_codex_artifact_regeneration_attempted = bool(
        prompt334_stale_post_codex_reconciliation_state.get(
            "prompt334_stale_post_codex_artifact_regeneration_attempted",
            prompt334_stale_post_codex_artifact_regeneration_attempted,
        )
    )
    prompt334_stale_post_codex_artifact_regeneration_reason = _normalize_text(
        prompt334_stale_post_codex_reconciliation_state.get(
            "prompt334_stale_post_codex_artifact_regeneration_reason"
        ),
        default=prompt334_stale_post_codex_artifact_regeneration_reason,
    )
    prompt334_stale_post_codex_artifact_regeneration_status = _normalize_text(
        prompt334_stale_post_codex_reconciliation_state.get(
            "prompt334_stale_post_codex_artifact_regeneration_status"
        ),
        default=prompt334_stale_post_codex_artifact_regeneration_status,
    )
    next_action = _normalize_text(post_execution_handoff.get("next_action"), default=next_action)
    diff_capture_status = _normalize_text(
        post_execution_handoff.get("diff_capture_status"),
        default=diff_capture_status,
    )
    diff_capture_blocked_reason = _normalize_text(
        post_execution_handoff.get("diff_capture_blocked_reason"),
        default=diff_capture_blocked_reason,
    )
    review_request_status = _normalize_text(
        post_execution_handoff.get("review_request_status"),
        default=review_request_status,
    )
    review_request_blocked_reason = _normalize_text(
        post_execution_handoff.get("review_request_blocked_reason"),
        default=review_request_blocked_reason,
    )
    completed_result_source_status = _normalize_text(
        post_execution_handoff.get("completed_result_source_status"),
        default=completed_result_source_status,
    )
    local_post_codex_diff_capture_status = _normalize_text(
        post_execution_handoff.get("local_post_codex_diff_capture_status"),
        default=local_post_codex_diff_capture_status,
    )
    local_post_codex_diff_capture_blocked_reason = _normalize_text(
        post_execution_handoff.get("local_post_codex_diff_capture_blocked_reason"),
        default=local_post_codex_diff_capture_blocked_reason,
    )
    local_post_codex_diff_capture_next_action = _normalize_text(
        post_execution_handoff.get("local_post_codex_diff_capture_next_action"),
        default=local_post_codex_diff_capture_next_action,
    )
    local_post_codex_diff_capture_worktree_clean_for_tracked_files = bool(
        post_execution_handoff.get(
            "local_post_codex_diff_capture_worktree_clean_for_tracked_files",
            local_post_codex_diff_capture_worktree_clean_for_tracked_files,
        )
    )
    local_post_codex_diff_capture_changed_tracked_file_count = _as_non_negative_int(
        post_execution_handoff.get("local_post_codex_diff_capture_changed_tracked_file_count"),
        default=local_post_codex_diff_capture_changed_tracked_file_count,
    )
    local_post_codex_outcome_status = _normalize_text(
        post_execution_handoff.get("local_post_codex_outcome_status"),
        default=local_post_codex_outcome_status,
    )
    local_post_codex_outcome_classification = _normalize_text(
        post_execution_handoff.get("local_post_codex_outcome_classification"),
        default=local_post_codex_outcome_classification,
    )
    local_post_codex_stdout_contains_blocked = bool(
        post_execution_handoff.get(
            "local_post_codex_stdout_contains_blocked",
            local_post_codex_stdout_contains_blocked,
        )
    )
    local_post_codex_stdout_blocked_reason = _normalize_text(
        post_execution_handoff.get("local_post_codex_stdout_blocked_reason"),
        default=local_post_codex_stdout_blocked_reason,
    )
    local_post_codex_route_status = _normalize_text(
        post_execution_handoff.get("local_post_codex_route_status"),
        default=local_post_codex_route_status,
    )
    local_post_codex_route_decision = _normalize_text(
        post_execution_handoff.get("local_post_codex_route_decision"),
        default=local_post_codex_route_decision,
    )
    local_post_codex_route_next_action = _normalize_text(
        post_execution_handoff.get("local_post_codex_route_next_action"),
        default=local_post_codex_route_next_action,
    )
    local_post_codex_route_targeted_contract_fix_recommended = bool(
        post_execution_handoff.get(
            "local_post_codex_route_targeted_contract_fix_recommended",
            local_post_codex_route_targeted_contract_fix_recommended,
        )
    )
    local_post_codex_route_approve_commit_tag_allowed = bool(
        post_execution_handoff.get(
            "local_post_codex_route_approve_commit_tag_allowed",
            local_post_codex_route_approve_commit_tag_allowed,
        )
    )
    review_handoff_decision_state = _build_one_cycle_review_handoff_decision_state(
        review_handoff_path=review_handoff_path
    )
    review_handoff_decision_status = _normalize_text(
        review_handoff_decision_state.get("review_handoff_decision_status"),
        default=review_handoff_decision_status,
    )
    tracked_diff_status = _normalize_text(
        review_handoff_decision_state.get("tracked_diff_status"),
        default=tracked_diff_status,
    )
    no_diff_review_status = _normalize_text(
        review_handoff_decision_state.get("no_diff_review_status"),
        default=no_diff_review_status,
    )
    no_diff_reason = _normalize_text(
        review_handoff_decision_state.get("no_diff_reason"),
        default=no_diff_reason,
    )
    review_handoff_decision_source_path = _normalize_text(
        review_handoff_decision_state.get("review_handoff_decision_source_path"),
        default=review_handoff_decision_source_path,
    )
    review_handoff_decision_next_action = _normalize_text(
        review_handoff_decision_state.get("review_handoff_decision_next_action"),
        default=review_handoff_decision_next_action,
    )
    review_response_assimilation_state = _build_review_response_assimilation_state(
        review_response_path=review_response_path,
        targeted_fix_prompt_path=targeted_fix_prompt_path,
    )
    review_response_status = _normalize_text(
        review_response_assimilation_state.get("review_response_status"),
        default=review_response_status,
    )
    review_response_decision = _normalize_text(
        review_response_assimilation_state.get("review_response_decision"),
        default=review_response_decision,
    )
    review_response_reason = _normalize_text(
        review_response_assimilation_state.get("review_response_reason"),
        default=review_response_reason,
    )
    review_response_next_action = _normalize_text(
        review_response_assimilation_state.get("review_response_next_action"),
        default=review_response_next_action,
    )
    targeted_fix_prompt_status = _normalize_text(
        review_response_assimilation_state.get("targeted_fix_prompt_status"),
        default=targeted_fix_prompt_status,
    )
    targeted_fix_prompt_text = _normalize_text(
        review_response_assimilation_state.get("targeted_fix_prompt_text"),
        default=targeted_fix_prompt_text,
    )
    targeted_fix_prompt_resolved_path = _normalize_text(
        review_response_assimilation_state.get("targeted_fix_prompt_path"),
        default=targeted_fix_prompt_resolved_path,
    )
    review_route_decision_state = _build_review_route_decision_state(
        review_response_status=review_response_status,
        review_response_decision=review_response_decision,
        review_response_next_action=review_response_next_action,
        targeted_fix_prompt_status=targeted_fix_prompt_status,
        targeted_fix_prompt_path=targeted_fix_prompt_resolved_path,
        review_handoff_decision_status=review_handoff_decision_status,
        tracked_diff_status=tracked_diff_status,
        review_handoff_decision_next_action=review_handoff_decision_next_action,
    )
    review_route_status = _normalize_text(
        review_route_decision_state.get("review_route_status"),
        default=review_route_status,
    )
    review_route_decision = _normalize_text(
        review_route_decision_state.get("review_route_decision"),
        default=review_route_decision,
    )
    review_route_reason = _normalize_text(
        review_route_decision_state.get("review_route_reason"),
        default=review_route_reason,
    )
    review_route_next_action = _normalize_text(
        review_route_decision_state.get("review_route_next_action"),
        default=review_route_next_action,
    )
    review_route_blocked_reason = _normalize_text(
        review_route_decision_state.get("review_route_blocked_reason"),
        default=review_route_blocked_reason,
    )
    review_route_source = _normalize_text(
        review_route_decision_state.get("review_route_source"),
        default=review_route_source,
    )
    review_route_targeted_fix_prompt_path = _normalize_text(
        review_route_decision_state.get("review_route_targeted_fix_prompt_path"),
        default=review_route_targeted_fix_prompt_path,
    )
    review_route_should_prepare_commit = bool(
        review_route_decision_state.get("review_route_should_prepare_commit", False)
    )
    review_route_should_prepare_targeted_fix = bool(
        review_route_decision_state.get("review_route_should_prepare_targeted_fix", False)
    )
    review_route_should_prepare_reject = bool(
        review_route_decision_state.get("review_route_should_prepare_reject", False)
    )
    targeted_fix_prompt_boundary_state = _build_targeted_fix_prompt_boundary_state(
        review_route_status=review_route_status,
        review_route_decision=review_route_decision,
        review_route_should_prepare_targeted_fix=review_route_should_prepare_targeted_fix,
        review_route_targeted_fix_prompt_path=review_route_targeted_fix_prompt_path,
        targeted_fix_prompt_path=targeted_fix_prompt_resolved_path,
        targeted_fix_codex_prompt_path=targeted_fix_codex_prompt_path,
    )
    targeted_fix_boundary_status = _normalize_text(
        targeted_fix_prompt_boundary_state.get("targeted_fix_boundary_status"),
        default=targeted_fix_boundary_status,
    )
    targeted_fix_boundary_decision = _normalize_text(
        targeted_fix_prompt_boundary_state.get("targeted_fix_boundary_decision"),
        default=targeted_fix_boundary_decision,
    )
    targeted_fix_boundary_reason = _normalize_text(
        targeted_fix_prompt_boundary_state.get("targeted_fix_boundary_reason"),
        default=targeted_fix_boundary_reason,
    )
    targeted_fix_boundary_next_action = _normalize_text(
        targeted_fix_prompt_boundary_state.get("targeted_fix_boundary_next_action"),
        default=targeted_fix_boundary_next_action,
    )
    targeted_fix_boundary_blocked_reason = _normalize_text(
        targeted_fix_prompt_boundary_state.get("targeted_fix_boundary_blocked_reason"),
        default=targeted_fix_boundary_blocked_reason,
    )
    targeted_fix_boundary_source_prompt_path = _normalize_text(
        targeted_fix_prompt_boundary_state.get("targeted_fix_boundary_source_prompt_path"),
        default=targeted_fix_boundary_source_prompt_path,
    )
    targeted_fix_boundary_codex_prompt_path = _normalize_text(
        targeted_fix_prompt_boundary_state.get("targeted_fix_boundary_codex_prompt_path"),
        default=targeted_fix_boundary_codex_prompt_path,
    )
    targeted_fix_boundary_prompt_ready = bool(
        targeted_fix_prompt_boundary_state.get(
            "targeted_fix_boundary_prompt_ready",
            targeted_fix_boundary_prompt_ready,
        )
    )
    targeted_fix_boundary_should_execute_codex = False
    targeted_fix_reentry_execution_state = _run_targeted_fix_reentry_execution_if_enabled(
        dry_run=bool(dry_run),
        review_route_status=review_route_status,
        review_route_decision=review_route_decision,
        review_route_should_prepare_targeted_fix=review_route_should_prepare_targeted_fix,
        targeted_fix_boundary_status=targeted_fix_boundary_status,
        targeted_fix_boundary_decision=targeted_fix_boundary_decision,
        targeted_fix_boundary_prompt_ready=targeted_fix_boundary_prompt_ready,
        targeted_fix_boundary_codex_prompt_path=targeted_fix_boundary_codex_prompt_path,
        execution_enabled=targeted_fix_reentry_execution_enabled,
        execution_confirmed=targeted_fix_reentry_execution_confirmed,
        execution_receipt_path=targeted_fix_reentry_execution_receipt_path,
    )
    targeted_fix_post_reentry_diff_capture_state = (
        _capture_targeted_fix_post_reentry_diff_state(
            targeted_fix_reentry_execution_state=targeted_fix_reentry_execution_state
        )
    )
    targeted_fix_post_reentry_review_handoff_state = (
        _build_targeted_fix_post_reentry_review_handoff_state(
            diff_capture_state=targeted_fix_post_reentry_diff_capture_state
        )
    )
    targeted_fix_reentry_execution_enabled = bool(
        targeted_fix_reentry_execution_state.get(
            "execution_enabled",
            targeted_fix_reentry_execution_enabled,
        )
    )
    targeted_fix_reentry_execution_confirmed = bool(
        targeted_fix_reentry_execution_state.get(
            "execution_confirmed",
            targeted_fix_reentry_execution_confirmed,
        )
    )
    targeted_fix_reentry_execution_gate_status = _normalize_text(
        targeted_fix_reentry_execution_state.get("execution_gate_status"),
        default=targeted_fix_reentry_execution_gate_status,
    )
    targeted_fix_reentry_execution_status = _normalize_text(
        targeted_fix_reentry_execution_state.get("execution_status"),
        default=targeted_fix_reentry_execution_status,
    )
    targeted_fix_reentry_execution_attempted = bool(
        targeted_fix_reentry_execution_state.get(
            "execution_attempted",
            targeted_fix_reentry_execution_attempted,
        )
    )
    targeted_fix_reentry_execution_exit_code = _as_int(
        targeted_fix_reentry_execution_state.get("execution_exit_code"),
        default=targeted_fix_reentry_execution_exit_code,
    )
    targeted_fix_reentry_execution_blocked_reason = _normalize_text(
        targeted_fix_reentry_execution_state.get("execution_blocked_reason"),
        default=targeted_fix_reentry_execution_blocked_reason,
    )
    targeted_fix_reentry_execution_prompt_path = _normalize_text(
        targeted_fix_reentry_execution_state.get("execution_prompt_path"),
        default=targeted_fix_reentry_execution_prompt_path,
    )
    targeted_fix_reentry_execution_should_execute_codex = bool(
        targeted_fix_reentry_execution_state.get(
            "execution_should_execute_codex",
            targeted_fix_reentry_execution_should_execute_codex,
        )
    )
    targeted_fix_post_reentry_diff_capture_status = _normalize_text(
        targeted_fix_post_reentry_diff_capture_state.get("capture_status"),
        default=targeted_fix_post_reentry_diff_capture_status,
    )
    targeted_fix_post_reentry_diff_capture_attempted = bool(
        targeted_fix_post_reentry_diff_capture_state.get(
            "attempted",
            targeted_fix_post_reentry_diff_capture_attempted,
        )
    )
    targeted_fix_post_reentry_diff_capture_blocked_reason = _normalize_text(
        targeted_fix_post_reentry_diff_capture_state.get("blocked_reason"),
        default=targeted_fix_post_reentry_diff_capture_blocked_reason,
    )
    targeted_fix_post_reentry_diff_has_diff = bool(
        targeted_fix_post_reentry_diff_capture_state.get(
            "has_diff",
            targeted_fix_post_reentry_diff_has_diff,
        )
    )
    targeted_fix_post_reentry_diff_changed_file_count = _as_non_negative_int(
        targeted_fix_post_reentry_diff_capture_state.get("changed_file_count"),
        default=targeted_fix_post_reentry_diff_changed_file_count,
    )
    targeted_fix_post_reentry_review_handoff_status = _normalize_text(
        targeted_fix_post_reentry_review_handoff_state.get("handoff_status"),
        default=targeted_fix_post_reentry_review_handoff_status,
    )
    targeted_fix_post_reentry_review_required = bool(
        targeted_fix_post_reentry_review_handoff_state.get(
            "review_required",
            targeted_fix_post_reentry_review_required,
        )
    )
    targeted_fix_post_reentry_review_assimilation_state = (
        _build_targeted_fix_post_reentry_review_assimilation_state(
            review_handoff_state=targeted_fix_post_reentry_review_handoff_state
        )
    )
    targeted_fix_post_reentry_route_decision_state = (
        _build_targeted_fix_post_reentry_route_decision_state(
            review_assimilation_state=targeted_fix_post_reentry_review_assimilation_state
        )
    )
    targeted_fix_post_reentry_route_executor_boundary_state = (
        _build_targeted_fix_post_reentry_route_executor_boundary_state(
            route_decision_path=targeted_fix_post_reentry_route_decision_path
        )
    )
    targeted_fix_post_reentry_prompt_emission_state = (
        _write_targeted_fix_post_reentry_prompt_if_allowed(
            prompt_emission_state=_build_targeted_fix_post_reentry_prompt_emission_state(
                route_decision_path=targeted_fix_post_reentry_route_decision_path,
                review_assimilation_path=targeted_fix_post_reentry_review_assimilation_path,
                review_response_path=targeted_fix_post_reentry_review_response_path,
                route_executor_boundary_path=targeted_fix_post_reentry_route_executor_boundary_path,
                next_step_handoff_path=targeted_fix_post_reentry_next_step_handoff_path,
                emitted_prompt_path=targeted_fix_codex_prompt_path,
            )
        )
    )
    targeted_fix_post_reentry_prompt_emission_receipt_state = {
        "status": _normalize_text(
            targeted_fix_post_reentry_prompt_emission_state.get("status"),
            default="not_applicable",
        ),
        "receipt_status": "not_applicable",
        "blocked_reason": _normalize_text(
            targeted_fix_post_reentry_prompt_emission_state.get("blocked_reason"),
            default="route_not_targeted_fix",
        ),
        "source": _normalize_text(
            targeted_fix_post_reentry_prompt_emission_state.get("source"),
            default="targeted_fix_post_reentry_prompt_emission",
        ),
        "prompt_emission_path": str(targeted_fix_post_reentry_prompt_emission_path),
        "emitted_prompt_path": _normalize_text(
            targeted_fix_post_reentry_prompt_emission_state.get("emitted_prompt_path"),
            default=str(targeted_fix_codex_prompt_path),
        ),
        "prompt_written": bool(
            targeted_fix_post_reentry_prompt_emission_state.get("prompt_written", False)
        ),
        "ready_for_codex_reentry": False,
        "codex_reentry_executed": False,
        "execution_performed": False,
        "next_action": _normalize_text(
            targeted_fix_post_reentry_prompt_emission_state.get("next_action"),
            default="none",
        ),
        "summary": "",
    }
    emission_status = _normalize_text(
        targeted_fix_post_reentry_prompt_emission_state.get("emission_status"),
        default="not_applicable",
    )
    if emission_status == "ready" and bool(
        targeted_fix_post_reentry_prompt_emission_state.get("prompt_written", False)
    ):
        targeted_fix_post_reentry_prompt_emission_receipt_state.update(
            {
                "receipt_status": "ready",
                "blocked_reason": "none",
                "ready_for_codex_reentry": True,
                "next_action": "run_prompt318_post_reentry_targeted_fix_codex_reentry",
                "summary": (
                    "Post-reentry targeted-fix prompt emitted; ready for deterministic Codex reentry."
                ),
            }
        )
    elif emission_status == "blocked":
        targeted_fix_post_reentry_prompt_emission_receipt_state.update(
            {
                "receipt_status": "blocked",
                "ready_for_codex_reentry": False,
                "next_action": _normalize_text(
                    targeted_fix_post_reentry_prompt_emission_state.get("next_action"),
                    default="manual_review_required",
                ),
                "summary": "Post-reentry targeted-fix prompt emission is blocked.",
            }
        )
    else:
        targeted_fix_post_reentry_prompt_emission_receipt_state.update(
            {
                "receipt_status": "not_applicable",
                "ready_for_codex_reentry": False,
                "next_action": _normalize_text(
                    targeted_fix_post_reentry_prompt_emission_state.get("next_action"),
                    default="none",
                ),
                "summary": "Post-reentry targeted-fix prompt emission is not applicable.",
            }
        )
    try:
        targeted_fix_post_reentry_prompt_emission_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(
            targeted_fix_post_reentry_prompt_emission_path,
            targeted_fix_post_reentry_prompt_emission_state,
        )
    except OSError:
        pass
    try:
        targeted_fix_post_reentry_prompt_emission_receipt_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        _write_json(
            targeted_fix_post_reentry_prompt_emission_receipt_path,
            targeted_fix_post_reentry_prompt_emission_receipt_state,
        )
    except OSError:
        pass
    targeted_fix_post_reentry_codex_reentry_execution_state = (
        _run_targeted_fix_post_reentry_codex_reentry_execution_if_enabled(
            prompt_emission_path=targeted_fix_post_reentry_prompt_emission_path,
            prompt_emission_receipt_path=targeted_fix_post_reentry_prompt_emission_receipt_path,
            expected_emitted_prompt_path=targeted_fix_codex_prompt_path,
            execution_enabled=targeted_fix_post_reentry_codex_reentry_execution_enabled,
            execution_confirmed=targeted_fix_post_reentry_codex_reentry_execution_confirmed,
            execution_receipt_path=(
                targeted_fix_post_reentry_codex_reentry_execution_receipt_path
            ),
            execution_stdout_path=(
                targeted_fix_post_reentry_codex_reentry_execution_stdout_path
            ),
            execution_stderr_path=(
                targeted_fix_post_reentry_codex_reentry_execution_stderr_path
            ),
        )
    )
    targeted_fix_post_reentry_next_step_handoff_state = (
        _build_targeted_fix_post_reentry_next_step_handoff_state(
            route_executor_boundary_state=targeted_fix_post_reentry_route_executor_boundary_state,
            route_decision_path=targeted_fix_post_reentry_route_decision_path,
            route_executor_boundary_path=targeted_fix_post_reentry_route_executor_boundary_path,
        )
    )
    targeted_fix_post_reentry_codex_reentry_execution_status = _normalize_text(
        targeted_fix_post_reentry_codex_reentry_execution_state.get("execution_status"),
        default=targeted_fix_post_reentry_codex_reentry_execution_status,
    )
    targeted_fix_post_reentry_codex_reentry_gate_status = _normalize_text(
        targeted_fix_post_reentry_codex_reentry_execution_state.get("gate_status"),
        default=targeted_fix_post_reentry_codex_reentry_gate_status,
    )
    targeted_fix_post_reentry_codex_reentry_blocked_reason = _normalize_text(
        targeted_fix_post_reentry_codex_reentry_execution_state.get("blocked_reason"),
        default=targeted_fix_post_reentry_codex_reentry_blocked_reason,
    )
    targeted_fix_post_reentry_codex_reentry_attempted = bool(
        targeted_fix_post_reentry_codex_reentry_execution_state.get(
            "attempted",
            targeted_fix_post_reentry_codex_reentry_attempted,
        )
    )
    targeted_fix_post_reentry_codex_reentry_executed = bool(
        targeted_fix_post_reentry_codex_reentry_execution_state.get(
            "codex_reentry_executed",
            targeted_fix_post_reentry_codex_reentry_executed,
        )
    )
    targeted_fix_post_reentry_codex_reentry_exit_code = _as_optional_int(
        targeted_fix_post_reentry_codex_reentry_execution_state.get("exit_code")
    )
    targeted_fix_post_reentry_codex_reentry_next_action = _normalize_text(
        targeted_fix_post_reentry_codex_reentry_execution_state.get("next_action"),
        default=targeted_fix_post_reentry_codex_reentry_next_action,
    )
    targeted_fix_post_reentry_review_assimilation_status = _normalize_text(
        targeted_fix_post_reentry_review_assimilation_state.get("assimilation_status"),
        default=targeted_fix_post_reentry_review_assimilation_status,
    )
    targeted_fix_post_reentry_review_assimilation_blocked_reason = _normalize_text(
        targeted_fix_post_reentry_review_assimilation_state.get("blocked_reason"),
        default=targeted_fix_post_reentry_review_assimilation_blocked_reason,
    )
    targeted_fix_post_reentry_review_decision = _normalize_text(
        targeted_fix_post_reentry_review_assimilation_state.get("normalized_decision"),
        default=targeted_fix_post_reentry_review_decision,
    )
    targeted_fix_post_reentry_route_status = _normalize_text(
        targeted_fix_post_reentry_route_decision_state.get("route_status"),
        default=targeted_fix_post_reentry_route_status,
    )
    targeted_fix_post_reentry_route_decision = _normalize_text(
        targeted_fix_post_reentry_route_decision_state.get("route_decision"),
        default=targeted_fix_post_reentry_route_decision,
    )
    targeted_fix_post_reentry_next_action = _normalize_text(
        targeted_fix_post_reentry_route_decision_state.get("next_action"),
        default=targeted_fix_post_reentry_next_action,
    )
    targeted_fix_post_reentry_manual_review_required = bool(
        targeted_fix_post_reentry_route_decision_state.get(
            "manual_review_required",
            targeted_fix_post_reentry_manual_review_required,
        )
    )
    targeted_fix_post_reentry_targeted_fix_required = bool(
        targeted_fix_post_reentry_route_decision_state.get(
            "targeted_fix_required",
            targeted_fix_post_reentry_targeted_fix_required,
        )
    )
    targeted_fix_post_reentry_route_executor_boundary_status = _normalize_text(
        targeted_fix_post_reentry_route_executor_boundary_state.get("boundary_status"),
        default=targeted_fix_post_reentry_route_executor_boundary_status,
    )
    targeted_fix_post_reentry_route_executor_kind = _normalize_text(
        targeted_fix_post_reentry_route_executor_boundary_state.get("executor_kind"),
        default=targeted_fix_post_reentry_route_executor_kind,
    )
    targeted_fix_post_reentry_route_executor_next_action = _normalize_text(
        targeted_fix_post_reentry_route_executor_boundary_state.get("next_action"),
        default=targeted_fix_post_reentry_route_executor_next_action,
    )
    targeted_fix_post_reentry_route_executor_execution_allowed = bool(
        targeted_fix_post_reentry_route_executor_boundary_state.get(
            "execution_allowed",
            targeted_fix_post_reentry_route_executor_execution_allowed,
        )
    )
    targeted_fix_post_reentry_route_executor_manual_review_required = bool(
        targeted_fix_post_reentry_route_executor_boundary_state.get(
            "manual_review_required",
            targeted_fix_post_reentry_route_executor_manual_review_required,
        )
    )
    targeted_fix_post_reentry_cycle_closure_allowed = bool(
        targeted_fix_post_reentry_route_executor_boundary_state.get(
            "cycle_closure_allowed",
            targeted_fix_post_reentry_cycle_closure_allowed,
        )
    )
    targeted_fix_post_reentry_approval_boundary_allowed = bool(
        targeted_fix_post_reentry_route_executor_boundary_state.get(
            "approval_boundary_allowed",
            targeted_fix_post_reentry_approval_boundary_allowed,
        )
    )
    targeted_fix_post_reentry_reject_boundary_allowed = bool(
        targeted_fix_post_reentry_route_executor_boundary_state.get(
            "reject_boundary_allowed",
            targeted_fix_post_reentry_reject_boundary_allowed,
        )
    )
    targeted_fix_post_reentry_targeted_fix_prompt_emission_allowed = bool(
        targeted_fix_post_reentry_route_executor_boundary_state.get(
            "targeted_fix_prompt_emission_allowed",
            targeted_fix_post_reentry_targeted_fix_prompt_emission_allowed,
        )
    )
    targeted_fix_post_reentry_codex_reentry_allowed = bool(
        targeted_fix_post_reentry_route_executor_boundary_state.get(
            "codex_reentry_allowed",
            targeted_fix_post_reentry_codex_reentry_allowed,
        )
    )
    targeted_fix_post_reentry_next_step_handoff_status = _normalize_text(
        targeted_fix_post_reentry_next_step_handoff_state.get("handoff_status"),
        default=targeted_fix_post_reentry_next_step_handoff_status,
    )
    targeted_fix_post_reentry_prompt_emission_status = _normalize_text(
        targeted_fix_post_reentry_prompt_emission_state.get("emission_status"),
        default=targeted_fix_post_reentry_prompt_emission_status,
    )
    targeted_fix_post_reentry_prompt_emission_blocked_reason = _normalize_text(
        targeted_fix_post_reentry_prompt_emission_state.get("blocked_reason"),
        default=targeted_fix_post_reentry_prompt_emission_blocked_reason,
    )
    targeted_fix_post_reentry_prompt_written = bool(
        targeted_fix_post_reentry_prompt_emission_state.get(
            "prompt_written",
            targeted_fix_post_reentry_prompt_written,
        )
    )
    targeted_fix_post_reentry_prompt_ready_for_codex_reentry = bool(
        targeted_fix_post_reentry_prompt_emission_receipt_state.get(
            "ready_for_codex_reentry",
            targeted_fix_post_reentry_prompt_ready_for_codex_reentry,
        )
    )
    targeted_fix_post_reentry_prompt_emission_next_action = _normalize_text(
        targeted_fix_post_reentry_prompt_emission_state.get("next_action"),
        default=targeted_fix_post_reentry_prompt_emission_next_action,
    )
    targeted_fix_post_reentry_emitted_prompt_path = _normalize_text(
        targeted_fix_post_reentry_prompt_emission_state.get("emitted_prompt_path"),
        default=targeted_fix_post_reentry_emitted_prompt_path,
    )
    targeted_fix_post_reentry_cycle_closure_result_state = (
        _build_targeted_fix_post_reentry_cycle_closure_result_state(
            next_step_handoff_path=targeted_fix_post_reentry_next_step_handoff_path,
            route_executor_boundary_path=targeted_fix_post_reentry_route_executor_boundary_path,
            route_decision_path=targeted_fix_post_reentry_route_decision_path,
            diff_capture_path=targeted_fix_post_reentry_diff_capture_path,
            review_handoff_path=targeted_fix_post_reentry_review_handoff_path,
        )
    )
    targeted_fix_post_reentry_terminal_summary_state = (
        _build_targeted_fix_post_reentry_terminal_summary_state(
            cycle_closure_result_state=targeted_fix_post_reentry_cycle_closure_result_state,
            cycle_closure_result_path=targeted_fix_post_reentry_cycle_closure_result_path,
        )
    )
    targeted_fix_post_reentry_cycle_closure_status = _normalize_text(
        targeted_fix_post_reentry_cycle_closure_result_state.get("closure_status"),
        default=targeted_fix_post_reentry_cycle_closure_status,
    )
    targeted_fix_post_reentry_terminal_state = _normalize_text(
        targeted_fix_post_reentry_terminal_summary_state.get("terminal_state"),
        default=targeted_fix_post_reentry_terminal_state,
    )
    targeted_fix_post_reentry_cycle_closed = bool(
        targeted_fix_post_reentry_terminal_summary_state.get(
            "cycle_closed",
            targeted_fix_post_reentry_cycle_closed,
        )
    )
    targeted_fix_post_reentry_safe_to_stop = bool(
        targeted_fix_post_reentry_terminal_summary_state.get(
            "safe_to_stop",
            targeted_fix_post_reentry_safe_to_stop,
        )
    )
    targeted_fix_post_reentry_safe_to_commit_prompt_changes = bool(
        targeted_fix_post_reentry_terminal_summary_state.get(
            "safe_to_commit_prompt_changes",
            targeted_fix_post_reentry_safe_to_commit_prompt_changes,
        )
    )
    targeted_fix_post_reentry_requires_codex_reentry = bool(
        targeted_fix_post_reentry_terminal_summary_state.get(
            "requires_codex_reentry",
            targeted_fix_post_reentry_requires_codex_reentry,
        )
    )
    targeted_fix_post_reentry_requires_manual_review = bool(
        targeted_fix_post_reentry_terminal_summary_state.get(
            "requires_manual_review",
            targeted_fix_post_reentry_requires_manual_review,
        )
    )
    targeted_fix_post_reentry_bounded_cycle_state = (
        _build_targeted_fix_post_reentry_bounded_cycle_state(
            prompt_emission_path=targeted_fix_post_reentry_prompt_emission_path,
            prompt_emission_receipt_path=targeted_fix_post_reentry_prompt_emission_receipt_path,
            codex_reentry_execution_receipt_path=(
                targeted_fix_post_reentry_codex_reentry_execution_receipt_path
            ),
            diff_capture_path=targeted_fix_post_reentry_diff_capture_path,
            review_handoff_path=targeted_fix_post_reentry_review_handoff_path,
            review_assimilation_path=targeted_fix_post_reentry_review_assimilation_path,
            route_decision_path=targeted_fix_post_reentry_route_decision_path,
            route_executor_boundary_path=targeted_fix_post_reentry_route_executor_boundary_path,
            next_step_handoff_path=targeted_fix_post_reentry_next_step_handoff_path,
            cycle_closure_result_path=targeted_fix_post_reentry_cycle_closure_result_path,
            terminal_summary_path=targeted_fix_post_reentry_terminal_summary_path,
            current_cycle_count=targeted_fix_post_reentry_current_cycle_count,
            max_cycle_count=targeted_fix_post_reentry_max_cycle_count,
            bounded_cycle_state_path=targeted_fix_post_reentry_bounded_cycle_state_path,
            bounded_cycle_decision_path=targeted_fix_post_reentry_bounded_cycle_decision_path,
            bounded_cycle_receipt_path=targeted_fix_post_reentry_bounded_cycle_receipt_path,
        )
    )
    targeted_fix_post_reentry_bounded_cycle_decision_state = (
        _build_targeted_fix_post_reentry_bounded_cycle_decision_state(
            bounded_cycle_state=targeted_fix_post_reentry_bounded_cycle_state
        )
    )
    targeted_fix_post_reentry_bounded_cycle_receipt_state = (
        _build_targeted_fix_post_reentry_bounded_cycle_receipt_state(
            bounded_cycle_state=targeted_fix_post_reentry_bounded_cycle_state,
            bounded_cycle_decision_state=targeted_fix_post_reentry_bounded_cycle_decision_state,
        )
    )
    try:
        targeted_fix_post_reentry_bounded_cycle_state_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        _write_json(
            targeted_fix_post_reentry_bounded_cycle_state_path,
            targeted_fix_post_reentry_bounded_cycle_state,
        )
        _write_json(
            targeted_fix_post_reentry_bounded_cycle_decision_path,
            targeted_fix_post_reentry_bounded_cycle_decision_state,
        )
        _write_json(
            targeted_fix_post_reentry_bounded_cycle_receipt_path,
            targeted_fix_post_reentry_bounded_cycle_receipt_state,
        )
    except OSError:
        pass
    targeted_fix_post_reentry_bounded_cycle_status = _normalize_text(
        targeted_fix_post_reentry_bounded_cycle_state.get("status"),
        default=targeted_fix_post_reentry_bounded_cycle_status,
    )
    targeted_fix_post_reentry_bounded_cycle_decision = _normalize_text(
        targeted_fix_post_reentry_bounded_cycle_decision_state.get("decision"),
        default=targeted_fix_post_reentry_bounded_cycle_decision,
    )
    targeted_fix_post_reentry_bounded_cycle_blocked_reason = _normalize_text(
        targeted_fix_post_reentry_bounded_cycle_state.get("blocked_reason"),
        default=targeted_fix_post_reentry_bounded_cycle_blocked_reason,
    )
    targeted_fix_post_reentry_bounded_cycle_complete = bool(
        targeted_fix_post_reentry_bounded_cycle_state.get(
            "bounded_cycle_complete",
            targeted_fix_post_reentry_bounded_cycle_complete,
        )
    )
    targeted_fix_post_reentry_bounded_cycle_should_continue = bool(
        targeted_fix_post_reentry_bounded_cycle_state.get(
            "should_continue",
            targeted_fix_post_reentry_bounded_cycle_should_continue,
        )
    )
    targeted_fix_post_reentry_bounded_cycle_should_emit_prompt = bool(
        targeted_fix_post_reentry_bounded_cycle_state.get(
            "should_emit_targeted_fix_prompt",
            targeted_fix_post_reentry_bounded_cycle_should_emit_prompt,
        )
    )
    targeted_fix_post_reentry_bounded_cycle_should_execute_codex = bool(
        targeted_fix_post_reentry_bounded_cycle_state.get(
            "should_execute_codex_reentry",
            targeted_fix_post_reentry_bounded_cycle_should_execute_codex,
        )
    )
    targeted_fix_post_reentry_bounded_cycle_should_capture_diff = bool(
        targeted_fix_post_reentry_bounded_cycle_state.get(
            "should_capture_diff",
            targeted_fix_post_reentry_bounded_cycle_should_capture_diff,
        )
    )
    targeted_fix_post_reentry_bounded_cycle_next_action = _normalize_text(
        targeted_fix_post_reentry_bounded_cycle_state.get("next_action"),
        default=targeted_fix_post_reentry_bounded_cycle_next_action,
    )
    targeted_fix_post_reentry_current_cycle_count = _as_non_negative_int(
        targeted_fix_post_reentry_bounded_cycle_state.get("current_cycle_count"),
        default=targeted_fix_post_reentry_current_cycle_count,
    )
    targeted_fix_post_reentry_max_cycle_count = _as_non_negative_int(
        targeted_fix_post_reentry_bounded_cycle_state.get("max_cycle_count"),
        default=targeted_fix_post_reentry_max_cycle_count,
    )
    approve_commit_tag_artifact_reconciliation = _reconcile_approve_commit_tag_artifacts(
        execution_repo_path=execution_repo_path,
        boundary_path=approve_commit_tag_boundary_metadata_path,
        plan_path=approve_commit_tag_plan_metadata_path,
        command_file_path=approve_commit_tag_boundary_commands_path,
        receipt_path=approve_commit_tag_artifact_reconciliation_receipt_file_path,
    )
    approve_commit_tag_artifact_reconciliation_status = _normalize_text(
        approve_commit_tag_artifact_reconciliation.get("status"),
        default="blocked",
    )
    approve_commit_tag_artifact_reconciliation_blocked_reason = _normalize_text(
        approve_commit_tag_artifact_reconciliation.get("blocked_reason"),
        default="manual_review_required",
    )
    approve_commit_tag_artifact_reconciliation_stale_artifacts_detected = bool(
        approve_commit_tag_artifact_reconciliation.get("stale_artifacts_detected", False)
    )
    approve_commit_tag_artifact_reconciliation_already_committed = bool(
        approve_commit_tag_artifact_reconciliation.get("already_committed", False)
    )
    approve_commit_tag_artifact_reconciliation_already_tagged = bool(
        approve_commit_tag_artifact_reconciliation.get("already_tagged", False)
    )
    approve_commit_tag_artifact_reconciliation_next_action = _normalize_text(
        approve_commit_tag_artifact_reconciliation.get("next_action"),
        default="manual_review_required",
    )
    approve_commit_tag_artifact_reconciliation_receipt_path = _normalize_text(
        approve_commit_tag_artifact_reconciliation.get("receipt_path"),
        default=_APPROVE_COMMIT_TAG_ARTIFACT_RECONCILIATION_RECEIPT_PATH,
    )

    approve_commit_tag_boundary_state = _read_json_object_if_exists(
        approve_commit_tag_boundary_metadata_path
    ) or {}
    approve_commit_tag_plan_state = _read_json_object_if_exists(
        approve_commit_tag_plan_metadata_path
    ) or {}
    if approve_commit_tag_artifact_reconciliation_status != "completed":
        changed_tracked_files_from_reconciliation = _normalize_string_list(
            approve_commit_tag_artifact_reconciliation.get("changed_tracked_files")
        )
        approve_commit_tag_boundary_state = {
            "status": "blocked",
            "boundary_status": "blocked",
            "blocked_reason": approve_commit_tag_artifact_reconciliation_blocked_reason,
            "source": "approve_commit_tag_artifact_reconciliation",
            "activation_condition_met": False,
            "plan_ready": False,
            "tracked_files_allowed": False,
            "changed_tracked_files": changed_tracked_files_from_reconciliation,
            "unexpected_tracked_files": changed_tracked_files_from_reconciliation,
            "explicit_add_paths": [],
            "proposed_commit_message": _APPROVE_COMMIT_TAG_EXECUTION_COMMIT_MESSAGE,
            "proposed_tag": _APPROVE_COMMIT_TAG_EXECUTION_TAG_NAME,
            "command_file_path": str(approve_commit_tag_boundary_commands_path),
            "commit_allowed": False,
            "tag_allowed": False,
            "execution_allowed": False,
            "execution_performed": False,
            "already_committed": False,
            "already_tagged": False,
            "stale_artifacts_detected": (
                approve_commit_tag_artifact_reconciliation_stale_artifacts_detected
            ),
            "next_action": approve_commit_tag_artifact_reconciliation_next_action,
            "summary": "Approve commit/tag artifacts reconciliation is blocked.",
        }
        approve_commit_tag_plan_state = {
            "status": "blocked",
            "plan_status": "blocked",
            "blocked_reason": approve_commit_tag_artifact_reconciliation_blocked_reason,
            "source": "approve_commit_tag_artifact_reconciliation",
            "commit_message": _APPROVE_COMMIT_TAG_EXECUTION_COMMIT_MESSAGE,
            "tag_name": _APPROVE_COMMIT_TAG_EXECUTION_TAG_NAME,
            "explicit_add_paths": [],
            "command_file_path": str(approve_commit_tag_boundary_commands_path),
            "execution_required_by": "none",
            "execution_performed": False,
            "already_committed": False,
            "already_tagged": False,
            "stale_artifacts_detected": (
                approve_commit_tag_artifact_reconciliation_stale_artifacts_detected
            ),
            "next_action": approve_commit_tag_artifact_reconciliation_next_action,
            "summary": "Approve commit/tag plan reconciliation is blocked.",
        }

    approve_commit_tag_boundary_status = _normalize_text(
        approve_commit_tag_boundary_state.get("boundary_status"),
        default=approve_commit_tag_boundary_status,
    )
    if approve_commit_tag_boundary_status == "completed":
        approve_commit_tag_boundary_decision = "approve"
        approve_commit_tag_boundary_reason = "approve_commit_tag_artifact_reconciled"
    elif approve_commit_tag_boundary_status == "ready":
        approve_commit_tag_boundary_decision = "approve"
        approve_commit_tag_boundary_reason = "approve_commit_tag_boundary_ready"
    else:
        approve_commit_tag_boundary_decision = "none"
        approve_commit_tag_boundary_reason = _normalize_text(
            approve_commit_tag_boundary_state.get("blocked_reason"),
            default="blocked",
        )
    approve_commit_tag_boundary_next_action = _normalize_text(
        approve_commit_tag_boundary_state.get("next_action"),
        default=approve_commit_tag_boundary_next_action,
    )
    approve_commit_tag_boundary_blocked_reason = _normalize_text(
        approve_commit_tag_boundary_state.get("blocked_reason"),
        default=approve_commit_tag_boundary_blocked_reason,
    )
    approve_commit_tag_boundary_commit_message = _normalize_text(
        approve_commit_tag_boundary_state.get("proposed_commit_message"),
        default=approve_commit_tag_boundary_commit_message,
    )
    approve_commit_tag_boundary_tag_name = _normalize_text(
        approve_commit_tag_boundary_state.get("proposed_tag"),
        default=approve_commit_tag_boundary_tag_name,
    )
    approve_commit_tag_boundary_commands_resolved_path = (
        str(approve_commit_tag_boundary_commands_path)
        if bool(approve_commit_tag_artifact_reconciliation.get("command_file_rewritten", False))
        else ""
    )
    approve_commit_tag_boundary_metadata_resolved_path = str(approve_commit_tag_boundary_metadata_path)
    approve_commit_tag_boundary_should_execute_commit = False
    approve_commit_tag_boundary_should_execute_tag = False
    approve_commit_tag_boundary_ready = approve_commit_tag_boundary_status == "ready"

    approve_commit_tag_plan_ready = bool(approve_commit_tag_boundary_state.get("plan_ready", False))
    approve_commit_tag_tracked_files_allowed = bool(
        approve_commit_tag_boundary_state.get("tracked_files_allowed", False)
    )
    approve_commit_tag_changed_tracked_files = _normalize_string_list(
        approve_commit_tag_boundary_state.get("changed_tracked_files")
    )
    approve_commit_tag_unexpected_tracked_files = _normalize_string_list(
        approve_commit_tag_boundary_state.get("unexpected_tracked_files")
    )
    approve_commit_tag_explicit_add_paths = _normalize_string_list(
        approve_commit_tag_boundary_state.get("explicit_add_paths")
    )
    approve_commit_tag_proposed_commit_message = _normalize_text(
        approve_commit_tag_boundary_state.get("proposed_commit_message"),
        default=approve_commit_tag_proposed_commit_message,
    )
    approve_commit_tag_proposed_tag = _normalize_text(
        approve_commit_tag_boundary_state.get("proposed_tag"),
        default=approve_commit_tag_proposed_tag,
    )
    approve_commit_tag_command_file_path = _normalize_text(
        approve_commit_tag_boundary_state.get("command_file_path"),
        default=approve_commit_tag_command_file_path,
    )
    approve_commit_tag_execution_allowed = bool(
        approve_commit_tag_boundary_state.get("execution_allowed", False)
    )
    approve_commit_tag_boundary_path = str(approve_commit_tag_boundary_metadata_path)
    approve_commit_tag_plan_path = str(approve_commit_tag_plan_metadata_path)

    approve_commit_tag_execution_enabled = False
    approve_commit_tag_execution_confirmed = False
    approve_commit_tag_execution_gate_status = "execution_not_enabled"
    approve_commit_tag_execution_status = "not_executed"
    approve_commit_tag_execution_attempted = False
    approve_commit_tag_execution_exit_code = 0
    approve_commit_tag_execution_blocked_reason = "execution_not_enabled"
    approve_commit_tag_execution_commit_message = _normalize_text(
        approve_commit_tag_plan_state.get("commit_message"),
        default=approve_commit_tag_execution_commit_message,
    )
    approve_commit_tag_execution_tag_name = _normalize_text(
        approve_commit_tag_plan_state.get("tag_name"),
        default=approve_commit_tag_execution_tag_name,
    )
    approve_commit_tag_execution_should_commit = False
    approve_commit_tag_execution_should_tag = False
    remote_readiness_boundary_state = _build_remote_readiness_boundary_state(
        execution_repo_path=execution_repo_path,
        reconciliation_receipt_path=approve_commit_tag_artifact_reconciliation_receipt_file_path,
    )
    remote_readiness_plan_state = _build_remote_readiness_plan_state(
        boundary_state=remote_readiness_boundary_state
    )
    try:
        remote_readiness_boundary_metadata_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(
            remote_readiness_boundary_metadata_path,
            remote_readiness_boundary_state,
        )
        _write_json(
            remote_readiness_plan_metadata_path,
            remote_readiness_plan_state,
        )
    except OSError:
        pass

    remote_readiness_boundary_status = _normalize_text(
        remote_readiness_boundary_state.get("boundary_status"),
        default=remote_readiness_boundary_status,
    )
    remote_readiness_blocked_reason = _normalize_text(
        remote_readiness_boundary_state.get("blocked_reason"),
        default=remote_readiness_blocked_reason,
    )
    remote_readiness_remote_ready = bool(
        remote_readiness_boundary_state.get("remote_ready", remote_readiness_remote_ready)
    )
    remote_readiness_push_ready = bool(
        remote_readiness_boundary_state.get("push_ready", remote_readiness_push_ready)
    )
    remote_readiness_pr_ready = bool(
        remote_readiness_boundary_state.get("pr_ready", remote_readiness_pr_ready)
    )
    remote_readiness_merge_ready = bool(
        remote_readiness_boundary_state.get("merge_ready", remote_readiness_merge_ready)
    )
    remote_readiness_worktree_clean = bool(
        remote_readiness_boundary_state.get(
            "worktree_clean",
            remote_readiness_worktree_clean,
        )
    )
    remote_readiness_expected_head_tag_present = bool(
        remote_readiness_boundary_state.get(
            "expected_head_tag_present",
            remote_readiness_expected_head_tag_present,
        )
    )
    remote_readiness_remote_configured = bool(
        remote_readiness_boundary_state.get(
            "remote_configured",
            remote_readiness_remote_configured,
        )
    )
    remote_readiness_upstream_configured = bool(
        remote_readiness_boundary_state.get(
            "upstream_configured",
            remote_readiness_upstream_configured,
        )
    )
    remote_readiness_next_action = _normalize_text(
        remote_readiness_boundary_state.get("next_action"),
        default=remote_readiness_next_action,
    )
    remote_readiness_boundary_path = str(remote_readiness_boundary_metadata_path)
    remote_readiness_plan_path = str(remote_readiness_plan_metadata_path)
    local_end_to_end_controller_component_matrix_state = (
        _build_local_end_to_end_controller_component_matrix_state(
            execution_repo_path=execution_repo_path,
        )
    )
    local_end_to_end_controller_readiness_boundary_state = (
        _build_local_end_to_end_controller_readiness_boundary_state(
            component_matrix_state=local_end_to_end_controller_component_matrix_state,
            reconciliation_receipt_path=approve_commit_tag_artifact_reconciliation_receipt_file_path,
            remote_readiness_boundary_path=remote_readiness_boundary_metadata_path,
        )
    )
    local_end_to_end_controller_gap_report_state = _build_local_end_to_end_controller_gap_report_state(
        component_matrix_state=local_end_to_end_controller_component_matrix_state,
        readiness_boundary_state=local_end_to_end_controller_readiness_boundary_state,
    )
    try:
        local_end_to_end_controller_component_matrix_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        _write_json(
            local_end_to_end_controller_component_matrix_path,
            local_end_to_end_controller_component_matrix_state,
        )
        _write_json(
            local_end_to_end_controller_readiness_boundary_path,
            local_end_to_end_controller_readiness_boundary_state,
        )
        _write_json(
            local_end_to_end_controller_gap_report_path,
            local_end_to_end_controller_gap_report_state,
        )
    except OSError:
        pass
    local_end_to_end_readiness_status = _normalize_text(
        local_end_to_end_controller_readiness_boundary_state.get("boundary_status"),
        default=local_end_to_end_readiness_status,
    )
    local_end_to_end_readiness_blocked_reason = _normalize_text(
        local_end_to_end_controller_readiness_boundary_state.get("blocked_reason"),
        default=local_end_to_end_readiness_blocked_reason,
    )
    local_end_to_end_ready = bool(
        local_end_to_end_controller_readiness_boundary_state.get(
            "local_end_to_end_ready",
            local_end_to_end_ready,
        )
    )
    local_components_ready = bool(
        local_end_to_end_controller_readiness_boundary_state.get(
            "local_components_ready",
            local_components_ready,
        )
    )
    integrated_local_runner_ready = bool(
        local_end_to_end_controller_readiness_boundary_state.get(
            "integrated_runner_ready",
            integrated_local_runner_ready,
        )
    )
    implementation_prompt_generation_status = _normalize_text(
        local_end_to_end_controller_readiness_boundary_state.get(
            "implementation_prompt_generation_status"
        ),
        default=implementation_prompt_generation_status,
    )
    github_deferred = bool(
        local_end_to_end_controller_readiness_boundary_state.get(
            "github_deferred",
            github_deferred,
        )
    )
    remote_required = bool(
        local_end_to_end_controller_readiness_boundary_state.get(
            "remote_required",
            remote_required,
        )
    )
    local_end_to_end_next_action = _normalize_text(
        local_end_to_end_controller_readiness_boundary_state.get("next_action"),
        default=local_end_to_end_next_action,
    )
    local_end_to_end_component_matrix_surface_path = str(
        local_end_to_end_controller_component_matrix_path
    )
    local_end_to_end_readiness_boundary_surface_path = str(
        local_end_to_end_controller_readiness_boundary_path
    )
    local_end_to_end_gap_report_surface_path = str(local_end_to_end_controller_gap_report_path)
    local_end_to_end_dry_run_plan_state = _build_local_end_to_end_dry_run_plan_state(
        execution_repo_path=execution_repo_path,
        one_cycle_controller_dir=one_cycle_controller_dir,
    )
    local_end_to_end_dry_run_step_matrix_state = _build_local_end_to_end_dry_run_step_matrix_state(
        plan_state=local_end_to_end_dry_run_plan_state,
        one_cycle_controller_dir=one_cycle_controller_dir,
    )
    local_end_to_end_dry_run_receipt_state = _build_local_end_to_end_dry_run_receipt_state(
        plan_state=local_end_to_end_dry_run_plan_state,
        step_matrix_state=local_end_to_end_dry_run_step_matrix_state,
        plan_path=local_end_to_end_dry_run_plan_path,
        step_matrix_path=local_end_to_end_dry_run_step_matrix_path,
    )
    try:
        local_end_to_end_dry_run_plan_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(
            local_end_to_end_dry_run_plan_path,
            local_end_to_end_dry_run_plan_state,
        )
        _write_json(
            local_end_to_end_dry_run_step_matrix_path,
            local_end_to_end_dry_run_step_matrix_state,
        )
        _write_json(
            local_end_to_end_dry_run_receipt_path,
            local_end_to_end_dry_run_receipt_state,
        )
    except OSError:
        pass
    local_end_to_end_dry_run_plan_status = _normalize_text(
        local_end_to_end_dry_run_plan_state.get("plan_status"),
        default=local_end_to_end_dry_run_plan_status,
    )
    local_end_to_end_dry_run_blocked_reason = _normalize_text(
        local_end_to_end_dry_run_plan_state.get("blocked_reason"),
        default=local_end_to_end_dry_run_blocked_reason,
    )
    local_end_to_end_dry_run_plan_ready = bool(
        local_end_to_end_dry_run_plan_state.get(
            "dry_run_plan_ready",
            local_end_to_end_dry_run_plan_ready,
        )
    )
    local_end_to_end_dry_run_step_count = _as_non_negative_int(
        local_end_to_end_dry_run_step_matrix_state.get("step_count"),
        default=local_end_to_end_dry_run_step_count,
    )
    local_end_to_end_dry_run_execution_allowed = bool(
        local_end_to_end_dry_run_plan_state.get(
            "execution_allowed",
            local_end_to_end_dry_run_execution_allowed,
        )
    )
    local_end_to_end_dry_run_next_action = _normalize_text(
        local_end_to_end_dry_run_plan_state.get("next_action"),
        default=local_end_to_end_dry_run_next_action,
    )
    local_end_to_end_dry_run_plan_surface_path = str(local_end_to_end_dry_run_plan_path)
    local_end_to_end_dry_run_step_matrix_surface_path = str(
        local_end_to_end_dry_run_step_matrix_path
    )
    local_end_to_end_dry_run_receipt_surface_path = str(local_end_to_end_dry_run_receipt_path)
    prior_one_shot_execution_receipt_state = (
        _read_json_object_if_exists(local_end_to_end_one_shot_execution_receipt_path) or {}
    )
    local_end_to_end_one_shot_step_selection_state = (
        _build_local_end_to_end_one_shot_step_selection_state(
            plan_state=local_end_to_end_dry_run_plan_state,
            step_matrix_state=local_end_to_end_dry_run_step_matrix_state,
            prior_receipt_state=prior_one_shot_execution_receipt_state,
            plan_path=local_end_to_end_dry_run_plan_path,
            step_matrix_path=local_end_to_end_dry_run_step_matrix_path,
            prior_receipt_path=local_end_to_end_one_shot_execution_receipt_path,
        )
    )
    local_end_to_end_one_shot_execution_gate_state = (
        _build_local_end_to_end_one_shot_execution_gate_state(
            execution_repo_path=execution_repo_path,
            plan_state=local_end_to_end_dry_run_plan_state,
            step_matrix_state=local_end_to_end_dry_run_step_matrix_state,
            step_selection_state=local_end_to_end_one_shot_step_selection_state,
            expected_head_tag=_LOCAL_END_TO_END_ONE_SHOT_EXPECTED_HEAD_TAG,
        )
    )
    local_end_to_end_one_shot_execution_receipt_state = (
        _build_local_end_to_end_one_shot_execution_receipt_state(
            gate_state=local_end_to_end_one_shot_execution_gate_state,
            step_selection_state=local_end_to_end_one_shot_step_selection_state,
            gate_path=local_end_to_end_one_shot_execution_gate_path,
            step_selection_path=local_end_to_end_one_shot_step_selection_path,
        )
    )
    try:
        local_end_to_end_one_shot_execution_gate_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        _write_json(
            local_end_to_end_one_shot_execution_gate_path,
            local_end_to_end_one_shot_execution_gate_state,
        )
        _write_json(
            local_end_to_end_one_shot_step_selection_path,
            local_end_to_end_one_shot_step_selection_state,
        )
        _write_json(
            local_end_to_end_one_shot_execution_receipt_path,
            local_end_to_end_one_shot_execution_receipt_state,
        )
    except OSError:
        pass
    local_one_shot_gate_status = _normalize_text(
        local_end_to_end_one_shot_execution_gate_state.get("gate_status"),
        default=local_one_shot_gate_status,
    )
    local_one_shot_blocked_reason = _normalize_text(
        local_end_to_end_one_shot_execution_gate_state.get("blocked_reason"),
        default=local_one_shot_blocked_reason,
    )
    local_one_shot_gate_ready = bool(
        local_end_to_end_one_shot_execution_gate_state.get(
            "one_shot_gate_ready",
            local_one_shot_gate_ready,
        )
    )
    local_one_shot_selected_step_id = _as_non_negative_int(
        local_end_to_end_one_shot_execution_gate_state.get("selected_step_id"),
        default=local_one_shot_selected_step_id,
    )
    local_one_shot_selected_step_name = _normalize_text(
        local_end_to_end_one_shot_execution_gate_state.get("selected_step_name"),
        default=local_one_shot_selected_step_name,
    )
    local_one_shot_execution_allowed = bool(
        local_end_to_end_one_shot_execution_gate_state.get(
            "execution_allowed",
            local_one_shot_execution_allowed,
        )
    )
    local_one_shot_next_action = _normalize_text(
        local_end_to_end_one_shot_execution_gate_state.get("next_action"),
        default=local_one_shot_next_action,
    )
    local_one_shot_gate_surface_path = str(local_end_to_end_one_shot_execution_gate_path)
    local_one_shot_step_selection_surface_path = str(
        local_end_to_end_one_shot_step_selection_path
    )
    local_one_shot_receipt_surface_path = str(local_end_to_end_one_shot_execution_receipt_path)
    bounded_local_autonomous_loop_state = _build_bounded_local_autonomous_loop_state(
        execution_repo_path=execution_repo_path,
        one_cycle_controller_dir=one_cycle_controller_dir,
        expected_head_tag=_BOUNDED_LOCAL_AUTONOMOUS_LOOP_EXPECTED_HEAD_TAG,
        current_cycle_count=_read_non_negative_int_flag(
            "project_browser_autonomous_bounded_local_loop_current_cycle_count",
            default=_BOUNDED_LOCAL_AUTONOMOUS_LOOP_DEFAULT_CURRENT_CYCLE_COUNT,
        ),
        max_cycle_count=_read_non_negative_int_flag(
            "project_browser_autonomous_bounded_local_loop_max_cycle_count",
            default=_BOUNDED_LOCAL_AUTONOMOUS_LOOP_DEFAULT_MAX_CYCLE_COUNT,
        ),
    )
    bounded_local_autonomous_loop_decision = (
        _build_bounded_local_autonomous_loop_decision_state(
            loop_state=bounded_local_autonomous_loop_state,
        )
    )
    bounded_local_autonomous_loop_receipt = _build_bounded_local_autonomous_loop_receipt_state(
        loop_state=bounded_local_autonomous_loop_state,
        decision_state=bounded_local_autonomous_loop_decision,
        state_path=bounded_local_autonomous_loop_state_path,
        decision_path=bounded_local_autonomous_loop_decision_path,
    )
    bounded_local_loop_artifacts_written = False
    try:
        bounded_local_autonomous_loop_state_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(
            bounded_local_autonomous_loop_state_path,
            bounded_local_autonomous_loop_state,
        )
        _write_json(
            bounded_local_autonomous_loop_decision_path,
            bounded_local_autonomous_loop_decision,
        )
        _write_json(
            bounded_local_autonomous_loop_receipt_path,
            bounded_local_autonomous_loop_receipt,
        )
        bounded_local_loop_artifacts_written = True
    except OSError:
        bounded_local_loop_artifacts_written = False
    if (
        not bounded_local_loop_artifacts_written
        or not bounded_local_autonomous_loop_state_path.exists()
        or not bounded_local_autonomous_loop_decision_path.exists()
        or not bounded_local_autonomous_loop_receipt_path.exists()
    ):
        fallback_selected_step_id = _as_non_negative_int(
            local_end_to_end_one_shot_step_selection_state.get("selected_step_id"),
            default=_as_non_negative_int(
                local_end_to_end_one_shot_execution_gate_state.get("selected_step_id"),
                default=1,
            ),
        )
        fallback_selected_step_name = _normalize_text(
            local_end_to_end_one_shot_step_selection_state.get("selected_step_name"),
            default=_normalize_text(
                local_end_to_end_one_shot_execution_gate_state.get("selected_step_name"),
                default="read_current_state",
            ),
        )
        fallback_loop_state = dict(bounded_local_autonomous_loop_state)
        fallback_loop_state["selected_step_id"] = (
            _as_non_negative_int(
                fallback_loop_state.get("selected_step_id"),
                default=fallback_selected_step_id,
            )
            if _as_optional_int(fallback_loop_state.get("selected_step_id")) is not None
            else fallback_selected_step_id
        )
        fallback_loop_state["selected_step_name"] = _normalize_text(
            fallback_loop_state.get("selected_step_name"),
            default=fallback_selected_step_name,
        )
        fallback_decision_state = _build_bounded_local_autonomous_loop_decision_state(
            loop_state=fallback_loop_state
        )
        fallback_receipt_state = _build_bounded_local_autonomous_loop_receipt_state(
            loop_state=fallback_loop_state,
            decision_state=fallback_decision_state,
            state_path=bounded_local_autonomous_loop_state_path,
            decision_path=bounded_local_autonomous_loop_decision_path,
        )
        try:
            bounded_local_autonomous_loop_state_path.parent.mkdir(parents=True, exist_ok=True)
            _write_json(
                bounded_local_autonomous_loop_state_path,
                fallback_loop_state,
            )
            _write_json(
                bounded_local_autonomous_loop_decision_path,
                fallback_decision_state,
            )
            _write_json(
                bounded_local_autonomous_loop_receipt_path,
                fallback_receipt_state,
            )
            bounded_local_autonomous_loop_state = fallback_loop_state
            bounded_local_autonomous_loop_decision = fallback_decision_state
            bounded_local_autonomous_loop_receipt = fallback_receipt_state
        except Exception:
            pass
    bounded_local_loop_status = _normalize_text(
        bounded_local_autonomous_loop_state.get("loop_status"),
        default=bounded_local_loop_status,
    )
    bounded_local_loop_blocked_reason = _normalize_text(
        bounded_local_autonomous_loop_state.get("blocked_reason"),
        default=bounded_local_loop_blocked_reason,
    )
    bounded_local_loop_ready = bool(
        bounded_local_autonomous_loop_state.get(
            "bounded_loop_ready",
            bounded_local_loop_ready,
        )
    )
    bounded_local_loop_complete = bool(
        bounded_local_autonomous_loop_state.get(
            "bounded_loop_complete",
            bounded_local_loop_complete,
        )
    )
    bounded_local_loop_should_continue = bool(
        bounded_local_autonomous_loop_state.get(
            "should_continue",
            bounded_local_loop_should_continue,
        )
    )
    bounded_local_loop_selected_step_id = _as_optional_int(
        bounded_local_autonomous_loop_state.get("selected_step_id")
    )
    if bounded_local_loop_selected_step_id is not None and bounded_local_loop_selected_step_id <= 0:
        bounded_local_loop_selected_step_id = None
    bounded_local_loop_selected_step_name = _normalize_text(
        bounded_local_autonomous_loop_state.get("selected_step_name"),
        default=bounded_local_loop_selected_step_name,
    )
    bounded_local_loop_execution_allowed = bool(
        bounded_local_autonomous_loop_state.get(
            "execution_allowed",
            bounded_local_loop_execution_allowed,
        )
    )
    bounded_local_loop_next_action = _normalize_text(
        bounded_local_autonomous_loop_state.get("next_action"),
        default=bounded_local_loop_next_action,
    )
    bounded_local_loop_state_surface_path = str(bounded_local_autonomous_loop_state_path)
    bounded_local_loop_decision_surface_path = str(bounded_local_autonomous_loop_decision_path)
    bounded_local_loop_receipt_surface_path = str(bounded_local_autonomous_loop_receipt_path)
    selected_step_execution_adapter_state = _build_selected_step_execution_adapter_state(
        execution_repo_path=execution_repo_path,
        one_cycle_controller_dir=one_cycle_controller_dir,
        expected_head_tag=_SELECTED_STEP_EXECUTION_ADAPTER_EXPECTED_HEAD_TAG,
    )
    selected_step_execution_plan_state = _build_selected_step_execution_plan_state(
        adapter_state=selected_step_execution_adapter_state,
    )
    selected_step_execution_receipt_state = _build_selected_step_execution_receipt_state(
        adapter_state=selected_step_execution_adapter_state,
        plan_state=selected_step_execution_plan_state,
        adapter_state_path=selected_step_execution_adapter_state_path,
        execution_plan_path=selected_step_execution_plan_path,
    )
    selected_step_execution_artifacts_written = False
    try:
        selected_step_execution_adapter_state_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(
            selected_step_execution_adapter_state_path,
            selected_step_execution_adapter_state,
        )
        _write_json(
            selected_step_execution_plan_path,
            selected_step_execution_plan_state,
        )
        _write_json(
            selected_step_execution_receipt_path,
            selected_step_execution_receipt_state,
        )
        selected_step_execution_artifacts_written = True
    except OSError:
        selected_step_execution_artifacts_written = False
    if (
        not selected_step_execution_artifacts_written
        or not selected_step_execution_adapter_state_path.exists()
        or not selected_step_execution_plan_path.exists()
        or not selected_step_execution_receipt_path.exists()
    ):
        try:
            selected_step_execution_adapter_state_path.parent.mkdir(parents=True, exist_ok=True)
            _write_json(
                selected_step_execution_adapter_state_path,
                selected_step_execution_adapter_state,
            )
            _write_json(
                selected_step_execution_plan_path,
                selected_step_execution_plan_state,
            )
            _write_json(
                selected_step_execution_receipt_path,
                selected_step_execution_receipt_state,
            )
        except OSError:
            pass

    selected_step_execution_adapter_status = _normalize_text(
        selected_step_execution_adapter_state.get("adapter_status"),
        default=selected_step_execution_adapter_status,
    )
    selected_step_execution_blocked_reason = _normalize_text(
        selected_step_execution_adapter_state.get("blocked_reason"),
        default=selected_step_execution_blocked_reason,
    )
    selected_step_execution_ready = bool(
        selected_step_execution_adapter_state.get(
            "selected_step_execution_ready",
            selected_step_execution_ready,
        )
    )
    selected_step_execution_selected_step_id = _as_non_negative_int(
        selected_step_execution_adapter_state.get("selected_step_id"),
        default=selected_step_execution_selected_step_id,
    )
    if selected_step_execution_selected_step_id <= 0:
        selected_step_execution_selected_step_id = 1
    selected_step_execution_selected_step_name = _normalize_text(
        selected_step_execution_adapter_state.get("selected_step_name"),
        default=selected_step_execution_selected_step_name,
    )
    selected_step_execution_operation = _normalize_text(
        selected_step_execution_adapter_state.get("selected_step_operation"),
        default=selected_step_execution_operation,
    )
    selected_step_execution_allowed = bool(
        selected_step_execution_adapter_state.get(
            "execution_allowed",
            selected_step_execution_allowed,
        )
    )
    selected_step_execution_performed = bool(
        selected_step_execution_adapter_state.get(
            "execution_performed",
            selected_step_execution_performed,
        )
    )
    selected_step_execution_next_action = _normalize_text(
        selected_step_execution_adapter_state.get("next_action"),
        default=selected_step_execution_next_action,
    )
    selected_step_execution_adapter_state_surface_path = str(
        selected_step_execution_adapter_state_path
    )
    selected_step_execution_plan_surface_path = str(selected_step_execution_plan_path)
    selected_step_execution_receipt_surface_path = str(
        selected_step_execution_receipt_path
    )
    selected_step_live_execution_gate_state = _build_selected_step_live_execution_gate_state(
        execution_repo_path=execution_repo_path,
        one_cycle_controller_dir=one_cycle_controller_dir,
        expected_head_tag=_SELECTED_STEP_LIVE_EXECUTION_EXPECTED_HEAD_TAG,
    )
    if dry_run:
        selected_step_live_execution_gate_state = (
            _build_dry_run_selected_step_live_execution_gate_state(
                gate_state=selected_step_live_execution_gate_state,
            )
        )
        selected_step_live_execution_operation_state = (
            _build_dry_run_selected_step_live_execution_operation_state(
                gate_state=selected_step_live_execution_gate_state,
            )
        )
    else:
        selected_step_live_execution_operation_state = (
            _run_selected_step_read_current_state_if_allowed(
                gate_state=selected_step_live_execution_gate_state,
                one_cycle_controller_dir=one_cycle_controller_dir,
            )
        )
    selected_step_live_execution_result_state = _build_selected_step_live_execution_result_state(
        gate_state=selected_step_live_execution_gate_state,
        execution_state=selected_step_live_execution_operation_state,
    )
    selected_step_live_execution_receipt_state = (
        _build_selected_step_live_execution_receipt_state(
            gate_state=selected_step_live_execution_gate_state,
            result_state=selected_step_live_execution_result_state,
            gate_path=selected_step_live_execution_gate_path,
            result_path=selected_step_live_execution_result_path,
        )
    )
    selected_step_live_execution_artifacts_written = False
    try:
        selected_step_live_execution_gate_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(
            selected_step_live_execution_gate_path,
            selected_step_live_execution_gate_state,
        )
        _write_json(
            selected_step_live_execution_result_path,
            selected_step_live_execution_result_state,
        )
        _write_json(
            selected_step_live_execution_receipt_path,
            selected_step_live_execution_receipt_state,
        )
        selected_step_live_execution_artifacts_written = True
    except OSError:
        selected_step_live_execution_artifacts_written = False
    if (
        not selected_step_live_execution_artifacts_written
        or not selected_step_live_execution_gate_path.exists()
        or not selected_step_live_execution_result_path.exists()
        or not selected_step_live_execution_receipt_path.exists()
    ):
        try:
            selected_step_live_execution_gate_path.parent.mkdir(parents=True, exist_ok=True)
            _write_json(
                selected_step_live_execution_gate_path,
                selected_step_live_execution_gate_state,
            )
            _write_json(
                selected_step_live_execution_result_path,
                selected_step_live_execution_result_state,
            )
            _write_json(
                selected_step_live_execution_receipt_path,
                selected_step_live_execution_receipt_state,
            )
        except OSError:
            pass
    selected_step_live_execution_gate_status = _normalize_text(
        selected_step_live_execution_gate_state.get("gate_status"),
        default=selected_step_live_execution_gate_status,
    )
    selected_step_live_execution_blocked_reason = _normalize_text(
        selected_step_live_execution_gate_state.get("blocked_reason"),
        default=selected_step_live_execution_blocked_reason,
    )
    selected_step_live_execution_ready = bool(
        selected_step_live_execution_gate_state.get(
            "live_execution_ready",
            selected_step_live_execution_ready,
        )
    )
    selected_step_live_execution_allowed = bool(
        selected_step_live_execution_gate_state.get(
            "live_execution_allowed",
            selected_step_live_execution_allowed,
        )
    )
    selected_step_live_execution_performed = bool(
        selected_step_live_execution_result_state.get(
            "live_execution_performed",
            selected_step_live_execution_performed,
        )
    )
    selected_step_live_execution_selected_step_id = _as_non_negative_int(
        selected_step_live_execution_gate_state.get("selected_step_id"),
        default=selected_step_live_execution_selected_step_id,
    )
    if selected_step_live_execution_selected_step_id <= 0:
        selected_step_live_execution_selected_step_id = 1
    selected_step_live_execution_selected_step_name = _normalize_text(
        selected_step_live_execution_gate_state.get("selected_step_name"),
        default=selected_step_live_execution_selected_step_name,
    )
    selected_step_live_execution_operation = _normalize_text(
        selected_step_live_execution_gate_state.get("selected_step_operation"),
        default=selected_step_live_execution_operation,
    )
    selected_step_live_execution_result_status = _normalize_text(
        selected_step_live_execution_result_state.get("result_status"),
        default=selected_step_live_execution_result_status,
    )
    selected_step_live_execution_next_action = _normalize_text(
        selected_step_live_execution_result_state.get("next_action"),
        default=selected_step_live_execution_next_action,
    )
    selected_step_live_execution_gate_surface_path = str(selected_step_live_execution_gate_path)
    selected_step_live_execution_result_surface_path = str(selected_step_live_execution_result_path)
    selected_step_live_execution_receipt_surface_path = str(
        selected_step_live_execution_receipt_path
    )
    selected_step_live_execution_read_current_state_completed = bool(
        selected_step_live_execution_result_state.get(
            "read_current_state_completed",
            selected_step_live_execution_read_current_state_completed,
        )
    )
    selected_step_execution_result_route_capture_state = (
        _build_selected_step_execution_result_route_capture_state(
            gate_path=selected_step_live_execution_gate_path,
            result_path=selected_step_live_execution_result_path,
            receipt_path=selected_step_live_execution_receipt_path,
        )
    )
    selected_step_execution_result_route_decision_state = (
        _build_selected_step_execution_result_route_decision_state(
            capture_state=selected_step_execution_result_route_capture_state,
        )
    )
    selected_step_execution_result_route_receipt_state = (
        _build_selected_step_execution_result_route_receipt_state(
            capture_state=selected_step_execution_result_route_capture_state,
            decision_state=selected_step_execution_result_route_decision_state,
            capture_path=selected_step_execution_result_route_capture_path,
            decision_path=selected_step_execution_result_route_decision_path,
        )
    )
    selected_step_execution_result_route_artifacts_written = False
    try:
        selected_step_execution_result_route_capture_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        _write_json(
            selected_step_execution_result_route_capture_path,
            selected_step_execution_result_route_capture_state,
        )
        _write_json(
            selected_step_execution_result_route_decision_path,
            selected_step_execution_result_route_decision_state,
        )
        _write_json(
            selected_step_execution_result_route_receipt_path,
            selected_step_execution_result_route_receipt_state,
        )
        selected_step_execution_result_route_artifacts_written = True
    except OSError:
        selected_step_execution_result_route_artifacts_written = False
    if (
        not selected_step_execution_result_route_artifacts_written
        or not selected_step_execution_result_route_capture_path.exists()
        or not selected_step_execution_result_route_decision_path.exists()
        or not selected_step_execution_result_route_receipt_path.exists()
    ):
        try:
            selected_step_execution_result_route_capture_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            _write_json(
                selected_step_execution_result_route_capture_path,
                selected_step_execution_result_route_capture_state,
            )
            _write_json(
                selected_step_execution_result_route_decision_path,
                selected_step_execution_result_route_decision_state,
            )
            _write_json(
                selected_step_execution_result_route_receipt_path,
                selected_step_execution_result_route_receipt_state,
            )
        except OSError:
            pass
    selected_step_execution_result_route_status = _normalize_text(
        selected_step_execution_result_route_decision_state.get("route_status"),
        default=selected_step_execution_result_route_status,
    )
    selected_step_execution_result_route_blocked_reason = _normalize_text(
        selected_step_execution_result_route_decision_state.get("blocked_reason"),
        default=selected_step_execution_result_route_blocked_reason,
    )
    selected_step_execution_result_route_decision = _normalize_text(
        selected_step_execution_result_route_decision_state.get("route_decision"),
        default=selected_step_execution_result_route_decision,
    )
    selected_step_execution_result_route_next_action = _normalize_text(
        selected_step_execution_result_route_decision_state.get("next_action"),
        default=selected_step_execution_result_route_next_action,
    )
    selected_step_execution_result_route_should_continue = bool(
        selected_step_execution_result_route_decision_state.get(
            "should_continue",
            selected_step_execution_result_route_should_continue,
        )
    )
    selected_step_execution_result_route_capture_surface_path = str(
        selected_step_execution_result_route_capture_path
    )
    selected_step_execution_result_route_decision_surface_path = str(
        selected_step_execution_result_route_decision_path
    )
    selected_step_execution_result_route_receipt_surface_path = str(
        selected_step_execution_result_route_receipt_path
    )
    local_only_autonomous_loop_closure_state = (
        _build_local_only_autonomous_loop_closure_state(
            route_capture_path=selected_step_execution_result_route_capture_path,
            route_decision_path=selected_step_execution_result_route_decision_path,
            route_receipt_path=selected_step_execution_result_route_receipt_path,
            live_gate_path=selected_step_live_execution_gate_path,
            live_result_path=selected_step_live_execution_result_path,
            live_receipt_path=selected_step_live_execution_receipt_path,
        )
    )
    local_only_autonomous_loop_closure_decision_state = (
        _build_local_only_autonomous_loop_closure_decision(
            closure_state=local_only_autonomous_loop_closure_state,
        )
    )
    local_only_autonomous_loop_closure_receipt_state = (
        _build_local_only_autonomous_loop_closure_receipt(
            closure_state=local_only_autonomous_loop_closure_state,
            closure_decision=local_only_autonomous_loop_closure_decision_state,
            closure_state_path=local_only_autonomous_loop_closure_state_path,
            closure_decision_path=local_only_autonomous_loop_closure_decision_path,
        )
    )
    local_only_autonomous_loop_closure_artifacts_written = False
    try:
        local_only_autonomous_loop_closure_state_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        _write_json(
            local_only_autonomous_loop_closure_state_path,
            local_only_autonomous_loop_closure_state,
        )
        _write_json(
            local_only_autonomous_loop_closure_decision_path,
            local_only_autonomous_loop_closure_decision_state,
        )
        _write_json(
            local_only_autonomous_loop_closure_receipt_path,
            local_only_autonomous_loop_closure_receipt_state,
        )
        local_only_autonomous_loop_closure_artifacts_written = True
    except OSError:
        local_only_autonomous_loop_closure_artifacts_written = False
    if (
        not local_only_autonomous_loop_closure_artifacts_written
        or not local_only_autonomous_loop_closure_state_path.exists()
        or not local_only_autonomous_loop_closure_decision_path.exists()
        or not local_only_autonomous_loop_closure_receipt_path.exists()
    ):
        try:
            local_only_autonomous_loop_closure_state_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            _write_json(
                local_only_autonomous_loop_closure_state_path,
                local_only_autonomous_loop_closure_state,
            )
            _write_json(
                local_only_autonomous_loop_closure_decision_path,
                local_only_autonomous_loop_closure_decision_state,
            )
            _write_json(
                local_only_autonomous_loop_closure_receipt_path,
                local_only_autonomous_loop_closure_receipt_state,
            )
        except OSError:
            pass
    local_only_autonomous_loop_closure_status = _normalize_text(
        local_only_autonomous_loop_closure_decision_state.get("closure_status"),
        default=local_only_autonomous_loop_closure_status,
    )
    local_only_autonomous_loop_closure_blocked_reason = _normalize_text(
        local_only_autonomous_loop_closure_decision_state.get("blocked_reason"),
        default=local_only_autonomous_loop_closure_blocked_reason,
    )
    local_only_autonomous_loop_closure_decision = _normalize_text(
        local_only_autonomous_loop_closure_decision_state.get("closure_decision"),
        default=local_only_autonomous_loop_closure_decision,
    )
    local_only_autonomous_loop_closure_next_action = _normalize_text(
        local_only_autonomous_loop_closure_decision_state.get("next_action"),
        default=local_only_autonomous_loop_closure_next_action,
    )
    local_only_autonomous_loop_v1_complete = bool(
        local_only_autonomous_loop_closure_decision_state.get(
            "local_only_v1_complete",
            local_only_autonomous_loop_v1_complete,
        )
    )
    local_only_autonomous_loop_closed = bool(
        local_only_autonomous_loop_closure_decision_state.get(
            "local_only_loop_closed",
            local_only_autonomous_loop_closed,
        )
    )
    local_only_autonomous_loop_closure_should_continue = bool(
        local_only_autonomous_loop_closure_decision_state.get(
            "should_continue",
            local_only_autonomous_loop_closure_should_continue,
        )
    )
    local_only_autonomous_loop_closure_state_surface_path = str(
        local_only_autonomous_loop_closure_state_path
    )
    local_only_autonomous_loop_closure_decision_surface_path = str(
        local_only_autonomous_loop_closure_decision_path
    )
    local_only_autonomous_loop_closure_receipt_surface_path = str(
        local_only_autonomous_loop_closure_receipt_path
    )
    local_autonomous_cycle_v2_state = _build_local_autonomous_cycle_v2_state(
        prompt330_closure_state_path=local_only_autonomous_loop_closure_state_path,
        prompt330_closure_decision_path=local_only_autonomous_loop_closure_decision_path,
        prompt330_closure_receipt_path=local_only_autonomous_loop_closure_receipt_path,
        execution_repo_path=str(execution_repo_path),
        controller_run_id=_normalize_text(
            prior_payload.get("run_id", approved_restart.get("run_id")),
            default="",
        ),
        controller_job_id=_normalize_text(
            prior_payload.get("job_id", approved_restart.get("job_id")),
            default="",
        ),
    )
    local_autonomous_cycle_v2_decision_state = _build_local_autonomous_cycle_v2_decision(
        cycle_state=local_autonomous_cycle_v2_state,
    )
    local_autonomous_cycle_v2_receipt_state = _build_local_autonomous_cycle_v2_receipt(
        cycle_state=local_autonomous_cycle_v2_state,
        cycle_decision=local_autonomous_cycle_v2_decision_state,
        cycle_state_path=local_autonomous_cycle_v2_state_path,
        cycle_decision_path=local_autonomous_cycle_v2_decision_path,
    )
    local_autonomous_cycle_v2_artifacts_written = False
    try:
        local_autonomous_cycle_v2_state_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(local_autonomous_cycle_v2_state_path, local_autonomous_cycle_v2_state)
        _write_json(local_autonomous_cycle_v2_decision_path, local_autonomous_cycle_v2_decision_state)
        _write_json(local_autonomous_cycle_v2_receipt_path, local_autonomous_cycle_v2_receipt_state)
        local_autonomous_cycle_v2_artifacts_written = True
    except OSError:
        local_autonomous_cycle_v2_artifacts_written = False
    if (
        not local_autonomous_cycle_v2_artifacts_written
        or not local_autonomous_cycle_v2_state_path.exists()
        or not local_autonomous_cycle_v2_decision_path.exists()
        or not local_autonomous_cycle_v2_receipt_path.exists()
    ):
        try:
            local_autonomous_cycle_v2_state_path.parent.mkdir(parents=True, exist_ok=True)
            _write_json(local_autonomous_cycle_v2_state_path, local_autonomous_cycle_v2_state)
            _write_json(
                local_autonomous_cycle_v2_decision_path,
                local_autonomous_cycle_v2_decision_state,
            )
            _write_json(
                local_autonomous_cycle_v2_receipt_path,
                local_autonomous_cycle_v2_receipt_state,
            )
        except OSError:
            pass
    local_autonomous_cycle_v2_status = _normalize_text(
        local_autonomous_cycle_v2_decision_state.get("status"),
        default=local_autonomous_cycle_v2_status,
    )
    local_autonomous_cycle_v2_cycle_status = _normalize_text(
        local_autonomous_cycle_v2_decision_state.get("cycle_status"),
        default=local_autonomous_cycle_v2_cycle_status,
    )
    local_autonomous_cycle_v2_next_action = _normalize_text(
        local_autonomous_cycle_v2_decision_state.get("next_action"),
        default=local_autonomous_cycle_v2_next_action,
    )
    local_autonomous_cycle_v2_selected_step_id = _as_optional_int(
        local_autonomous_cycle_v2_decision_state.get("selected_step_id")
    )
    local_autonomous_cycle_v2_selected_step_name = (
        _normalize_text(
            local_autonomous_cycle_v2_decision_state.get("selected_step_name"),
            default="",
        )
        or None
    )
    local_autonomous_cycle_v2_selected_step_operation = (
        _normalize_text(
            local_autonomous_cycle_v2_decision_state.get("selected_step_operation"),
            default="",
        )
        or None
    )
    local_autonomous_cycle_v2_decision = _normalize_text(
        local_autonomous_cycle_v2_decision_state.get("cycle_decision"),
        default=local_autonomous_cycle_v2_decision,
    )
    local_autonomous_cycle_v2_ready = bool(
        local_autonomous_cycle_v2_decision_state.get(
            "v2_cycle_ready",
            local_autonomous_cycle_v2_ready,
        )
    )
    local_autonomous_cycle_v2_blocked_reason = _normalize_text(
        local_autonomous_cycle_v2_decision_state.get("blocked_reason"),
        default=local_autonomous_cycle_v2_blocked_reason,
    )
    local_autonomous_cycle_v2_readiness_reason = _normalize_text(
        local_autonomous_cycle_v2_decision_state.get("readiness_reason"),
        default=local_autonomous_cycle_v2_readiness_reason,
    )
    local_autonomous_cycle_v2_run_id = _normalize_text(
        local_autonomous_cycle_v2_decision_state.get("run_id"),
        default=local_autonomous_cycle_v2_run_id,
    )
    local_autonomous_cycle_v2_cycle_id = _normalize_text(
        local_autonomous_cycle_v2_decision_state.get("cycle_id"),
        default=local_autonomous_cycle_v2_cycle_id,
    )
    local_autonomous_cycle_v2_current_cycle = _as_non_negative_int(
        local_autonomous_cycle_v2_decision_state.get("current_cycle"),
        default=local_autonomous_cycle_v2_current_cycle,
    )
    local_autonomous_cycle_v2_max_cycles = _as_non_negative_int(
        local_autonomous_cycle_v2_decision_state.get("max_cycles"),
        default=local_autonomous_cycle_v2_max_cycles,
    )
    local_autonomous_cycle_v2_state_surface_path = str(local_autonomous_cycle_v2_state_path)
    local_autonomous_cycle_v2_decision_surface_path = str(
        local_autonomous_cycle_v2_decision_path
    )
    local_autonomous_cycle_v2_receipt_surface_path = str(local_autonomous_cycle_v2_receipt_path)
    local_codex_one_shot_handoff_state = _build_local_codex_one_shot_execution_handoff_state(
        prompt331_state_path=local_autonomous_cycle_v2_state_path,
        prompt331_decision_path=local_autonomous_cycle_v2_decision_path,
        prompt331_receipt_path=local_autonomous_cycle_v2_receipt_path,
        execution_repo_path=str(execution_repo_path),
    )
    local_codex_one_shot_prompt_written = False
    local_codex_one_shot_prompt_non_empty = False
    if _normalize_text(local_codex_one_shot_handoff_state.get("status"), default="") == "ready":
        prompt_text = _build_local_codex_one_shot_prompt_markdown(
            run_id=_normalize_text(
                local_codex_one_shot_handoff_state.get("run_id"),
                default=local_autonomous_cycle_v2_run_id,
            ),
            cycle_id=_normalize_text(
                local_codex_one_shot_handoff_state.get("cycle_id"),
                default=local_autonomous_cycle_v2_cycle_id,
            ),
            current_cycle=_as_non_negative_int(
                local_codex_one_shot_handoff_state.get("current_cycle"),
                default=local_autonomous_cycle_v2_current_cycle,
            ),
            max_cycles=_as_non_negative_int(
                local_codex_one_shot_handoff_state.get("max_cycles"),
                default=local_autonomous_cycle_v2_max_cycles,
            ),
            selected_step_id=_as_non_negative_int(
                local_codex_one_shot_handoff_state.get("selected_step_id"),
                default=2,
            ),
            selected_step_name=_normalize_text(
                local_codex_one_shot_handoff_state.get("selected_step_name"),
                default="generate_next_codex_task",
            ),
            selected_step_operation=_normalize_text(
                local_codex_one_shot_handoff_state.get("selected_step_operation"),
                default="generate_next_codex_task",
            ),
            expected_changed_files=_normalize_string_list(
                local_codex_one_shot_handoff_state.get("explicit_allowed_tracked_files")
            ),
            explicit_allowed_tracked_files=_normalize_string_list(
                local_codex_one_shot_handoff_state.get("explicit_allowed_tracked_files")
            ),
            mutation_allowed=bool(local_codex_one_shot_handoff_state.get("mutation_allowed", False)),
            selected_step_authority_source=_normalize_text(
                local_codex_one_shot_handoff_state.get("selected_step_authority_source"),
                default="prompt331_v2_local_autonomous_cycle_v2_decision",
            ),
            selected_step_authority_artifact=_normalize_text(
                local_codex_one_shot_handoff_state.get("selected_step_authority_artifact"),
                default=_LOCAL_AUTONOMOUS_CYCLE_V2_DECISION_PATH,
            ),
            selected_step_authority_status=_normalize_text(
                local_codex_one_shot_handoff_state.get("selected_step_authority_status"),
                default="blocked",
            ),
            stale_step_selection_conflict_detected=bool(
                local_codex_one_shot_handoff_state.get(
                    "stale_step_selection_conflict_detected",
                    False,
                )
            ),
            stale_step_selection_artifact_path=_normalize_text(
                local_codex_one_shot_handoff_state.get("stale_step_selection_artifact_path"),
                default=_LOCAL_END_TO_END_ONE_SHOT_STEP_SELECTION_PATH,
            ),
            stale_step_selection_status=_normalize_text(
                local_codex_one_shot_handoff_state.get("stale_step_selection_status"),
                default="missing",
            ),
            contract_fix_applied=bool(
                local_codex_one_shot_handoff_state.get("contract_fix_applied", False)
            ),
            prompt_path=local_codex_one_shot_prompt_path,
        )
        local_codex_one_shot_prompt_non_empty = bool(prompt_text.strip())
        if local_codex_one_shot_prompt_non_empty:
            try:
                local_codex_one_shot_prompt_path.parent.mkdir(parents=True, exist_ok=True)
                local_codex_one_shot_prompt_path.write_text(prompt_text, encoding="utf-8")
                local_codex_one_shot_prompt_written = True
            except OSError:
                local_codex_one_shot_prompt_written = False
    else:
        try:
            local_codex_one_shot_prompt_path.unlink(missing_ok=True)
        except OSError:
            pass

    if local_codex_one_shot_prompt_written and local_codex_one_shot_prompt_non_empty:
        local_codex_one_shot_handoff_state["prompt_exists"] = True
        local_codex_one_shot_handoff_state["prompt_non_empty"] = True
        local_codex_one_shot_handoff_state["prompt_path"] = str(local_codex_one_shot_prompt_path)
    elif _normalize_text(local_codex_one_shot_handoff_state.get("status"), default="") == "ready":
        local_codex_one_shot_handoff_state.update(
            {
                "status": "blocked",
                "handoff_status": "blocked",
                "blocked_reason": "local_codex_one_shot_prompt_artifact_write_failed",
                "readiness_reason": "local_autonomous_cycle_v2_not_valid_for_codex_one_shot_handoff",
                "validation_errors": [],
                "codex_prompt_ready": False,
                "codex_execution_command_ready": False,
                "codex_invocation_allowed": False,
                "execution_allowed": False,
                "prompt_path": None,
                "prompt_exists": False,
                "prompt_non_empty": False,
                "command_argv": [],
                "command_display": "",
                "selected_step_id": None,
                "selected_step_name": None,
                "selected_step_operation": None,
                "explicit_allowed_tracked_files": [],
                "mutation_allowed": False,
                "selected_step_authority_status": "blocked",
                "should_continue": False,
                "next_action": "manual_review_local_codex_one_shot_prompt_artifact_write_failure",
                "changed_tracked_files": [],
            }
        )

    local_codex_one_shot_handoff_artifacts_written = False
    try:
        local_codex_one_shot_execution_handoff_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(
            local_codex_one_shot_execution_handoff_path,
            local_codex_one_shot_handoff_state,
        )
        local_codex_one_shot_handoff_artifacts_written = True
    except OSError:
        local_codex_one_shot_handoff_artifacts_written = False
    if (
        (not local_codex_one_shot_handoff_artifacts_written)
        or (not local_codex_one_shot_execution_handoff_path.exists())
    ):
        try:
            local_codex_one_shot_execution_handoff_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            _write_json(
                local_codex_one_shot_execution_handoff_path,
                local_codex_one_shot_handoff_state,
            )
        except OSError:
            pass

    local_codex_one_shot_execution_receipt_state = (
        _build_local_codex_one_shot_execution_receipt(
            handoff_state=local_codex_one_shot_handoff_state,
        )
    )
    local_codex_one_shot_receipt_artifacts_written = False
    try:
        local_codex_one_shot_execution_receipt_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(
            local_codex_one_shot_execution_receipt_path,
            local_codex_one_shot_execution_receipt_state,
        )
        local_codex_one_shot_receipt_artifacts_written = True
    except OSError:
        local_codex_one_shot_receipt_artifacts_written = False
    if (
        (not local_codex_one_shot_receipt_artifacts_written)
        or (not local_codex_one_shot_execution_receipt_path.exists())
    ):
        try:
            local_codex_one_shot_execution_receipt_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            _write_json(
                local_codex_one_shot_execution_receipt_path,
                local_codex_one_shot_execution_receipt_state,
            )
        except OSError:
            pass
    if (
        (not local_codex_one_shot_execution_handoff_path.exists())
        or (not local_codex_one_shot_execution_receipt_path.exists())
    ):
        local_codex_one_shot_handoff_state.update(
            {
                "status": "blocked",
                "handoff_status": "blocked",
                "blocked_reason": "local_codex_one_shot_handoff_artifact_write_failed",
                "readiness_reason": "local_autonomous_cycle_v2_not_valid_for_codex_one_shot_handoff",
                "validation_errors": [],
                "codex_prompt_ready": False,
                "codex_execution_command_ready": False,
                "codex_invocation_allowed": False,
                "execution_allowed": False,
                "prompt_path": None,
                "prompt_exists": False,
                "prompt_non_empty": False,
                "command_argv": [],
                "command_display": "",
                "selected_step_id": None,
                "selected_step_name": None,
                "selected_step_operation": None,
                "should_continue": False,
                "next_action": "manual_review_local_codex_one_shot_handoff_artifact_write_failure",
                "changed_tracked_files": [],
            }
        )
        try:
            local_codex_one_shot_execution_handoff_path.parent.mkdir(parents=True, exist_ok=True)
            _write_json(
                local_codex_one_shot_execution_handoff_path,
                local_codex_one_shot_handoff_state,
            )
        except OSError:
            pass
        local_codex_one_shot_execution_receipt_state = (
            _build_local_codex_one_shot_execution_receipt(
                handoff_state=local_codex_one_shot_handoff_state,
            )
        )
        try:
            local_codex_one_shot_execution_receipt_path.parent.mkdir(parents=True, exist_ok=True)
            _write_json(
                local_codex_one_shot_execution_receipt_path,
                local_codex_one_shot_execution_receipt_state,
            )
        except OSError:
            pass

    local_codex_one_shot_handoff_status = _normalize_text(
        local_codex_one_shot_handoff_state.get("status"),
        default=local_codex_one_shot_handoff_status,
    )
    local_codex_one_shot_handoff_handoff_status = _normalize_text(
        local_codex_one_shot_handoff_state.get("handoff_status"),
        default=local_codex_one_shot_handoff_handoff_status,
    )
    local_codex_one_shot_handoff_next_action = _normalize_text(
        local_codex_one_shot_handoff_state.get("next_action"),
        default=local_codex_one_shot_handoff_next_action,
    )
    local_codex_one_shot_handoff_blocked_reason = _normalize_text(
        local_codex_one_shot_handoff_state.get("blocked_reason"),
        default=local_codex_one_shot_handoff_blocked_reason,
    )
    local_codex_one_shot_handoff_readiness_reason = _normalize_text(
        local_codex_one_shot_handoff_state.get("readiness_reason"),
        default=local_codex_one_shot_handoff_readiness_reason,
    )
    local_codex_one_shot_handoff_prompt_ready = bool(
        local_codex_one_shot_handoff_state.get(
            "codex_prompt_ready",
            local_codex_one_shot_handoff_prompt_ready,
        )
    )
    local_codex_one_shot_handoff_command_ready = bool(
        local_codex_one_shot_handoff_state.get(
            "codex_execution_command_ready",
            local_codex_one_shot_handoff_command_ready,
        )
    )
    local_codex_one_shot_handoff_codex_invocation_allowed = bool(
        local_codex_one_shot_handoff_state.get(
            "codex_invocation_allowed",
            local_codex_one_shot_handoff_codex_invocation_allowed,
        )
    )
    local_codex_one_shot_handoff_execution_allowed = bool(
        local_codex_one_shot_handoff_state.get(
            "execution_allowed",
            local_codex_one_shot_handoff_execution_allowed,
        )
    )
    local_codex_one_shot_handoff_max_codex_invocations = _as_non_negative_int(
        local_codex_one_shot_handoff_state.get("max_codex_invocations"),
        default=local_codex_one_shot_handoff_max_codex_invocations,
    )
    local_codex_one_shot_handoff_codex_invocation_count = _as_non_negative_int(
        local_codex_one_shot_handoff_state.get("codex_invocation_count"),
        default=local_codex_one_shot_handoff_codex_invocation_count,
    )
    local_codex_one_shot_handoff_selected_step_id = _as_optional_int(
        local_codex_one_shot_handoff_state.get("selected_step_id")
    )
    local_codex_one_shot_handoff_selected_step_name = (
        _normalize_text(
            local_codex_one_shot_handoff_state.get("selected_step_name"),
            default="",
        )
        or None
    )
    local_codex_one_shot_handoff_selected_step_operation = (
        _normalize_text(
            local_codex_one_shot_handoff_state.get("selected_step_operation"),
            default="",
        )
        or None
    )
    local_codex_one_shot_handoff_prompt_path = (
        _normalize_text(
            local_codex_one_shot_handoff_state.get("prompt_path"),
            default="",
        )
        or None
    )
    local_codex_one_shot_handoff_command_display = _normalize_text(
        local_codex_one_shot_handoff_state.get("command_display"),
        default=local_codex_one_shot_handoff_command_display,
    )
    local_codex_one_shot_handoff_run_id = _normalize_text(
        local_codex_one_shot_handoff_state.get("run_id"),
        default=local_codex_one_shot_handoff_run_id,
    )
    local_codex_one_shot_handoff_cycle_id = _normalize_text(
        local_codex_one_shot_handoff_state.get("cycle_id"),
        default=local_codex_one_shot_handoff_cycle_id,
    )
    local_codex_one_shot_handoff_current_cycle = _as_non_negative_int(
        local_codex_one_shot_handoff_state.get("current_cycle"),
        default=local_codex_one_shot_handoff_current_cycle,
    )
    local_codex_one_shot_handoff_max_cycles = _as_non_negative_int(
        local_codex_one_shot_handoff_state.get("max_cycles"),
        default=local_codex_one_shot_handoff_max_cycles,
    )
    if dry_run:
        local_codex_one_shot_execution_result_state = (
            _build_dry_run_local_codex_one_shot_execution_result_state(
                handoff_state=local_codex_one_shot_handoff_state,
                handoff_receipt_state=local_codex_one_shot_execution_receipt_state,
                prompt_path=local_codex_one_shot_prompt_path,
                stdout_path=local_codex_one_shot_execution_stdout_path,
                stderr_path=local_codex_one_shot_execution_stderr_path,
                result_path=local_codex_one_shot_execution_result_path,
            )
        )
    else:
        local_codex_one_shot_execution_result_state = (
            _build_local_codex_one_shot_execution_result_state(
                execution_repo_path=str(execution_repo_path),
                handoff_path=local_codex_one_shot_execution_handoff_path,
                handoff_receipt_path=local_codex_one_shot_execution_receipt_path,
                prompt_path=local_codex_one_shot_prompt_path,
                stdout_path=local_codex_one_shot_execution_stdout_path,
                stderr_path=local_codex_one_shot_execution_stderr_path,
                result_path=local_codex_one_shot_execution_result_path,
            )
        )
    local_codex_one_shot_execution_receipt_v2_state = (
        _build_local_codex_one_shot_execution_receipt_v2(
            result_state=local_codex_one_shot_execution_result_state,
        )
    )
    local_codex_one_shot_execution_artifacts_written = False
    try:
        local_codex_one_shot_execution_result_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(
            local_codex_one_shot_execution_result_path,
            local_codex_one_shot_execution_result_state,
        )
        _write_json(
            local_codex_one_shot_execution_receipt_v2_path,
            local_codex_one_shot_execution_receipt_v2_state,
        )
        local_codex_one_shot_execution_artifacts_written = True
    except OSError:
        local_codex_one_shot_execution_artifacts_written = False
    if (
        (not local_codex_one_shot_execution_artifacts_written)
        or (not local_codex_one_shot_execution_result_path.exists())
        or (not local_codex_one_shot_execution_receipt_v2_path.exists())
    ):
        try:
            local_codex_one_shot_execution_result_path.parent.mkdir(parents=True, exist_ok=True)
            _write_json(
                local_codex_one_shot_execution_result_path,
                local_codex_one_shot_execution_result_state,
            )
            _write_json(
                local_codex_one_shot_execution_receipt_v2_path,
                local_codex_one_shot_execution_receipt_v2_state,
            )
        except OSError:
            pass
    (
        refreshed_post_execution_handoff,
        prompt334_post_write_reconciliation_state,
    ) = _maybe_reconcile_stale_prompt334_post_codex_artifacts(
        execution_repo_path=execution_repo_path,
        status=status,
        stop_reason=stop_reason,
        next_action=next_action,
        execution_attempted=execution_attempted,
        execution_exit_code=execution_exit_code,
        exec_plan_execution_status=exec_plan_execution_status,
        one_cycle_controller_dir=one_cycle_controller_dir,
        completed_result_source_path=completed_result_source_path,
    )
    post_write_post_execution_handoff = refreshed_post_execution_handoff
    if refreshed_post_execution_handoff is not None:
        prompt334_stale_post_codex_artifact_detected = bool(
            prompt334_post_write_reconciliation_state.get(
                "prompt334_stale_post_codex_artifact_detected",
                prompt334_stale_post_codex_artifact_detected,
            )
        )
        prompt334_stale_post_codex_artifact_regeneration_attempted = bool(
            prompt334_post_write_reconciliation_state.get(
                "prompt334_stale_post_codex_artifact_regeneration_attempted",
                prompt334_stale_post_codex_artifact_regeneration_attempted,
            )
        )
        prompt334_stale_post_codex_artifact_regeneration_reason = _normalize_text(
            prompt334_post_write_reconciliation_state.get(
                "prompt334_stale_post_codex_artifact_regeneration_reason"
            ),
            default=prompt334_stale_post_codex_artifact_regeneration_reason,
        )
        prompt334_stale_post_codex_artifact_regeneration_status = _normalize_text(
            prompt334_post_write_reconciliation_state.get(
                "prompt334_stale_post_codex_artifact_regeneration_status"
            ),
            default=prompt334_stale_post_codex_artifact_regeneration_status,
        )
    if post_write_post_execution_handoff is None:
        post_write_post_execution_handoff = _build_one_cycle_post_execution_handoff(
            execution_repo_path=execution_repo_path,
            status=status,
            stop_reason=stop_reason,
            next_action=next_action,
            execution_attempted=execution_attempted,
            execution_exit_code=execution_exit_code,
            exec_plan_execution_status=exec_plan_execution_status,
            one_cycle_controller_dir=one_cycle_controller_dir,
            completed_result_source_path=completed_result_source_path,
        )
    # Rebuild the Prompt334->Prompt342 chain from the post-write Prompt333 artifacts.
    next_action = _normalize_text(
        post_write_post_execution_handoff.get("next_action"),
        default=next_action,
    )
    diff_capture_status = _normalize_text(
        post_write_post_execution_handoff.get("diff_capture_status"),
        default=diff_capture_status,
    )
    diff_capture_blocked_reason = _normalize_text(
        post_write_post_execution_handoff.get("diff_capture_blocked_reason"),
        default=diff_capture_blocked_reason,
    )
    review_request_status = _normalize_text(
        post_write_post_execution_handoff.get("review_request_status"),
        default=review_request_status,
    )
    review_request_blocked_reason = _normalize_text(
        post_write_post_execution_handoff.get("review_request_blocked_reason"),
        default=review_request_blocked_reason,
    )
    completed_result_source_status = _normalize_text(
        post_write_post_execution_handoff.get("completed_result_source_status"),
        default=completed_result_source_status,
    )
    local_post_codex_diff_capture_status = _normalize_text(
        post_write_post_execution_handoff.get("local_post_codex_diff_capture_status"),
        default=local_post_codex_diff_capture_status,
    )
    local_post_codex_diff_capture_blocked_reason = _normalize_text(
        post_write_post_execution_handoff.get("local_post_codex_diff_capture_blocked_reason"),
        default=local_post_codex_diff_capture_blocked_reason,
    )
    local_post_codex_diff_capture_next_action = _normalize_text(
        post_write_post_execution_handoff.get("local_post_codex_diff_capture_next_action"),
        default=local_post_codex_diff_capture_next_action,
    )
    local_post_codex_diff_capture_worktree_clean_for_tracked_files = bool(
        post_write_post_execution_handoff.get(
            "local_post_codex_diff_capture_worktree_clean_for_tracked_files",
            local_post_codex_diff_capture_worktree_clean_for_tracked_files,
        )
    )
    local_post_codex_diff_capture_changed_tracked_file_count = _as_non_negative_int(
        post_write_post_execution_handoff.get(
            "local_post_codex_diff_capture_changed_tracked_file_count"
        ),
        default=local_post_codex_diff_capture_changed_tracked_file_count,
    )
    local_post_codex_outcome_status = _normalize_text(
        post_write_post_execution_handoff.get("local_post_codex_outcome_status"),
        default=local_post_codex_outcome_status,
    )
    local_post_codex_outcome_classification = _normalize_text(
        post_write_post_execution_handoff.get("local_post_codex_outcome_classification"),
        default=local_post_codex_outcome_classification,
    )
    local_post_codex_stdout_contains_blocked = bool(
        post_write_post_execution_handoff.get(
            "local_post_codex_stdout_contains_blocked",
            local_post_codex_stdout_contains_blocked,
        )
    )
    local_post_codex_stdout_blocked_reason = _normalize_text(
        post_write_post_execution_handoff.get("local_post_codex_stdout_blocked_reason"),
        default=local_post_codex_stdout_blocked_reason,
    )
    local_post_codex_route_status = _normalize_text(
        post_write_post_execution_handoff.get("local_post_codex_route_status"),
        default=local_post_codex_route_status,
    )
    local_post_codex_route_decision = _normalize_text(
        post_write_post_execution_handoff.get("local_post_codex_route_decision"),
        default=local_post_codex_route_decision,
    )
    local_post_codex_route_next_action = _normalize_text(
        post_write_post_execution_handoff.get("local_post_codex_route_next_action"),
        default=local_post_codex_route_next_action,
    )
    local_post_codex_route_targeted_contract_fix_recommended = bool(
        post_write_post_execution_handoff.get(
            "local_post_codex_route_targeted_contract_fix_recommended",
            local_post_codex_route_targeted_contract_fix_recommended,
        )
    )
    local_post_codex_route_approve_commit_tag_allowed = bool(
        post_write_post_execution_handoff.get(
            "local_post_codex_route_approve_commit_tag_allowed",
            local_post_codex_route_approve_commit_tag_allowed,
        )
    )
    local_targeted_contract_fix_prompt_state = (
        _build_local_targeted_contract_fix_prompt_artifacts(
            one_cycle_controller_dir=one_cycle_controller_dir
        )
        or {}
    )
    local_targeted_contract_fix_route_intake_status = _normalize_text(
        local_targeted_contract_fix_prompt_state.get("route_intake_status"),
        default=local_targeted_contract_fix_route_intake_status,
    )
    local_targeted_contract_fix_route_intake_blocked_reason = _normalize_text(
        local_targeted_contract_fix_prompt_state.get("route_intake_blocked_reason"),
        default=local_targeted_contract_fix_route_intake_blocked_reason,
    )
    local_targeted_contract_fix_route_intake_signal_source = _normalize_text(
        local_targeted_contract_fix_prompt_state.get("route_intake_signal_source"),
        default=local_targeted_contract_fix_route_intake_signal_source,
    )
    local_targeted_contract_fix_prompt_plan_status = _normalize_text(
        local_targeted_contract_fix_prompt_state.get("prompt_plan_status"),
        default=local_targeted_contract_fix_prompt_plan_status,
    )
    local_targeted_contract_fix_prompt_plan_blocked_reason = _normalize_text(
        local_targeted_contract_fix_prompt_state.get("prompt_plan_blocked_reason"),
        default=local_targeted_contract_fix_prompt_plan_blocked_reason,
    )
    local_targeted_contract_fix_prompt_path_text = _normalize_text(
        local_targeted_contract_fix_prompt_state.get("prompt_path"),
        default=local_targeted_contract_fix_prompt_path_text,
    )
    local_targeted_contract_fix_prompt_ready = bool(
        local_targeted_contract_fix_prompt_state.get(
            "prompt_ready",
            local_targeted_contract_fix_prompt_ready,
        )
    )
    local_targeted_contract_fix_prompt_next_action = _normalize_text(
        local_targeted_contract_fix_prompt_state.get("prompt_next_action"),
        default=local_targeted_contract_fix_prompt_next_action,
    )
    local_targeted_contract_fix_prompt_normalized_reason = _normalize_text(
        local_targeted_contract_fix_prompt_state.get("prompt_normalized_reason"),
        default=local_targeted_contract_fix_prompt_normalized_reason,
    )
    local_targeted_contract_fix_prompt_lifecycle_issue_detected = bool(
        local_targeted_contract_fix_prompt_state.get(
            "prompt_lifecycle_issue_detected",
            local_targeted_contract_fix_prompt_lifecycle_issue_detected,
        )
    )
    local_contract_fix_cycle_coordination_state = (
        _build_local_contract_fix_cycle_coordination_artifacts(
            one_cycle_controller_dir=one_cycle_controller_dir
        )
    )
    local_contract_fix_cycle_coordination_status = _normalize_text(
        local_contract_fix_cycle_coordination_state.get("coordination_status"),
        default=local_contract_fix_cycle_coordination_status,
    )
    local_contract_fix_cycle_coordination_blocked_reason = _normalize_text(
        local_contract_fix_cycle_coordination_state.get("coordination_blocked_reason"),
        default=local_contract_fix_cycle_coordination_blocked_reason,
    )
    local_contract_fix_cycle_coordination_ready = bool(
        local_contract_fix_cycle_coordination_state.get(
            "coordination_ready",
            local_contract_fix_cycle_coordination_ready,
        )
    )
    local_contract_fix_cycle_coordination_next_action = _normalize_text(
        local_contract_fix_cycle_coordination_state.get("coordination_next_action"),
        default=local_contract_fix_cycle_coordination_next_action,
    )
    local_contract_fix_cycle_prompt_path = _normalize_text(
        local_contract_fix_cycle_coordination_state.get("coordination_prompt_path"),
        default=local_contract_fix_cycle_prompt_path,
    )
    local_contract_fix_cycle_prompt_ready = bool(
        local_contract_fix_cycle_coordination_state.get(
            "coordination_prompt_ready",
            local_contract_fix_cycle_prompt_ready,
        )
    )
    local_contract_fix_cycle_normalized_reason = _normalize_text(
        local_contract_fix_cycle_coordination_state.get("coordination_normalized_reason"),
        default=local_contract_fix_cycle_normalized_reason,
    )
    local_contract_fix_cycle_selected_step_name = _normalize_text(
        local_contract_fix_cycle_coordination_state.get("coordination_selected_step_name"),
        default=local_contract_fix_cycle_selected_step_name,
    )
    local_contract_fix_cycle_handoff_status = _normalize_text(
        local_contract_fix_cycle_coordination_state.get("handoff_status"),
        default=local_contract_fix_cycle_handoff_status,
    )
    local_contract_fix_cycle_handoff_next_action = _normalize_text(
        local_contract_fix_cycle_coordination_state.get("handoff_next_action"),
        default=local_contract_fix_cycle_handoff_next_action,
    )
    local_daemon_lite_wrapper_state = _build_local_daemon_lite_wrapper_artifacts(
        one_cycle_controller_dir=one_cycle_controller_dir
    )
    local_daemon_lite_wrapper_status = _normalize_text(
        local_daemon_lite_wrapper_state.get("local_daemon_lite_wrapper_status"),
        default=local_daemon_lite_wrapper_status,
    )
    local_daemon_lite_wrapper_blocked_reason = _normalize_text(
        local_daemon_lite_wrapper_state.get("local_daemon_lite_wrapper_blocked_reason"),
        default=local_daemon_lite_wrapper_blocked_reason,
    )
    local_daemon_lite_wrapper_ready = bool(
        local_daemon_lite_wrapper_state.get(
            "local_daemon_lite_wrapper_ready",
            local_daemon_lite_wrapper_ready,
        )
    )
    local_daemon_lite_wrapper_decision = _normalize_text(
        local_daemon_lite_wrapper_state.get("local_daemon_lite_wrapper_decision"),
        default=local_daemon_lite_wrapper_decision,
    )
    local_daemon_lite_wrapper_next_action = _normalize_text(
        local_daemon_lite_wrapper_state.get("local_daemon_lite_wrapper_next_action"),
        default=local_daemon_lite_wrapper_next_action,
    )
    local_daemon_lite_wrapper_selected_step_name = _normalize_text(
        local_daemon_lite_wrapper_state.get("local_daemon_lite_wrapper_selected_step_name"),
        default=local_daemon_lite_wrapper_selected_step_name,
    )
    local_daemon_lite_wrapper_prompt_path = _normalize_text(
        local_daemon_lite_wrapper_state.get("local_daemon_lite_wrapper_prompt_path"),
        default=local_daemon_lite_wrapper_prompt_path,
    )
    local_daemon_lite_wrapper_bounded_execution = bool(
        local_daemon_lite_wrapper_state.get(
            "local_daemon_lite_wrapper_bounded_execution",
            local_daemon_lite_wrapper_bounded_execution,
        )
    )
    local_daemon_lite_wrapper_total_codex_invocation_budget = _as_non_negative_int(
        local_daemon_lite_wrapper_state.get(
            "local_daemon_lite_wrapper_total_codex_invocation_budget"
        ),
        default=local_daemon_lite_wrapper_total_codex_invocation_budget,
    )
    local_targeted_contract_fix_execution_state = (
        _build_local_targeted_contract_fix_execution_artifacts(
            execution_repo_path=execution_repo_path,
            one_cycle_controller_dir=one_cycle_controller_dir,
        )
    )
    local_targeted_contract_fix_execution_status = _normalize_text(
        local_targeted_contract_fix_execution_state.get(
            "local_targeted_contract_fix_execution_status"
        ),
        default=local_targeted_contract_fix_execution_status,
    )
    local_targeted_contract_fix_execution_blocked_reason = _normalize_text(
        local_targeted_contract_fix_execution_state.get(
            "local_targeted_contract_fix_execution_blocked_reason"
        ),
        default=local_targeted_contract_fix_execution_blocked_reason,
    )
    local_targeted_contract_fix_execution_next_action = _normalize_text(
        local_targeted_contract_fix_execution_state.get(
            "local_targeted_contract_fix_execution_next_action"
        ),
        default=local_targeted_contract_fix_execution_next_action,
    )
    local_targeted_contract_fix_execution_codex_invoked = bool(
        local_targeted_contract_fix_execution_state.get(
            "local_targeted_contract_fix_execution_codex_invoked",
            local_targeted_contract_fix_execution_codex_invoked,
        )
    )
    local_targeted_contract_fix_execution_exit_code = _as_optional_int(
        local_targeted_contract_fix_execution_state.get(
            "local_targeted_contract_fix_execution_exit_code"
        )
    )
    local_targeted_contract_fix_execution_changed_tracked_file_count = _as_non_negative_int(
        local_targeted_contract_fix_execution_state.get(
            "local_targeted_contract_fix_execution_changed_tracked_file_count"
        ),
        default=local_targeted_contract_fix_execution_changed_tracked_file_count,
    )
    local_targeted_contract_fix_execution_stdout_path_text = _normalize_text(
        local_targeted_contract_fix_execution_state.get(
            "local_targeted_contract_fix_execution_stdout_path"
        ),
        default=local_targeted_contract_fix_execution_stdout_path_text,
    )
    local_targeted_contract_fix_execution_stderr_path_text = _normalize_text(
        local_targeted_contract_fix_execution_state.get(
            "local_targeted_contract_fix_execution_stderr_path"
        ),
        default=local_targeted_contract_fix_execution_stderr_path_text,
    )
    local_post_targeted_contract_fix_review_state = (
        _build_local_post_targeted_contract_fix_review_artifacts(
            execution_repo_path=execution_repo_path,
            one_cycle_controller_dir=one_cycle_controller_dir,
        )
    )
    local_post_targeted_contract_fix_status = _normalize_text(
        local_post_targeted_contract_fix_review_state.get(
            "local_post_targeted_contract_fix_status"
        ),
        default=local_post_targeted_contract_fix_status,
    )
    local_post_targeted_contract_fix_blocked_reason = _normalize_text(
        local_post_targeted_contract_fix_review_state.get(
            "local_post_targeted_contract_fix_blocked_reason"
        ),
        default=local_post_targeted_contract_fix_blocked_reason,
    )
    local_post_targeted_contract_fix_classification = _normalize_text(
        local_post_targeted_contract_fix_review_state.get(
            "local_post_targeted_contract_fix_classification"
        ),
        default=local_post_targeted_contract_fix_classification,
    )
    local_post_targeted_contract_fix_route_decision = _normalize_text(
        local_post_targeted_contract_fix_review_state.get(
            "local_post_targeted_contract_fix_route_decision"
        ),
        default=local_post_targeted_contract_fix_route_decision,
    )
    local_post_targeted_contract_fix_next_action = _normalize_text(
        local_post_targeted_contract_fix_review_state.get(
            "local_post_targeted_contract_fix_next_action"
        ),
        default=local_post_targeted_contract_fix_next_action,
    )
    local_post_targeted_contract_fix_approve_commit_tag_ready = bool(
        local_post_targeted_contract_fix_review_state.get(
            "local_post_targeted_contract_fix_approve_commit_tag_ready",
            local_post_targeted_contract_fix_approve_commit_tag_ready,
        )
    )
    local_post_targeted_contract_fix_changed_tracked_file_count = _as_non_negative_int(
        local_post_targeted_contract_fix_review_state.get(
            "local_post_targeted_contract_fix_changed_tracked_file_count"
        ),
        default=local_post_targeted_contract_fix_changed_tracked_file_count,
    )
    local_post_targeted_contract_fix_unexpected_tracked_file_count = _as_non_negative_int(
        local_post_targeted_contract_fix_review_state.get(
            "local_post_targeted_contract_fix_unexpected_tracked_file_count"
        ),
        default=local_post_targeted_contract_fix_unexpected_tracked_file_count,
    )
    local_bounded_approve_commit_tag_state = (
        _build_local_bounded_approve_commit_tag_execution_artifacts(
            execution_repo_path=execution_repo_path,
            one_cycle_controller_dir=one_cycle_controller_dir,
        )
    )
    local_bounded_approve_commit_tag_status = _normalize_text(
        local_bounded_approve_commit_tag_state.get("local_bounded_approve_commit_tag_status"),
        default=local_bounded_approve_commit_tag_status,
    )
    local_bounded_approve_commit_tag_execution_status = _normalize_text(
        local_bounded_approve_commit_tag_state.get(
            "local_bounded_approve_commit_tag_execution_status"
        ),
        default=local_bounded_approve_commit_tag_execution_status,
    )
    local_bounded_approve_commit_tag_blocked_reason = _normalize_text(
        local_bounded_approve_commit_tag_state.get(
            "local_bounded_approve_commit_tag_blocked_reason"
        ),
        default=local_bounded_approve_commit_tag_blocked_reason,
    )
    local_bounded_approve_commit_tag_next_action = _normalize_text(
        local_bounded_approve_commit_tag_state.get("local_bounded_approve_commit_tag_next_action"),
        default=local_bounded_approve_commit_tag_next_action,
    )
    local_bounded_approve_commit_tag_commit_performed = bool(
        local_bounded_approve_commit_tag_state.get(
            "local_bounded_approve_commit_tag_commit_performed",
            local_bounded_approve_commit_tag_commit_performed,
        )
    )
    local_bounded_approve_commit_tag_tag_performed = bool(
        local_bounded_approve_commit_tag_state.get(
            "local_bounded_approve_commit_tag_tag_performed",
            local_bounded_approve_commit_tag_tag_performed,
        )
    )
    local_bounded_approve_commit_tag_commit_hash = _normalize_text(
        local_bounded_approve_commit_tag_state.get("local_bounded_approve_commit_tag_commit_hash"),
        default=local_bounded_approve_commit_tag_commit_hash,
    )
    local_bounded_approve_commit_tag_tag_name = _normalize_text(
        local_bounded_approve_commit_tag_state.get("local_bounded_approve_commit_tag_tag_name"),
        default=local_bounded_approve_commit_tag_tag_name,
    )
    local_bounded_approve_commit_tag_worktree_clean = bool(
        local_bounded_approve_commit_tag_state.get(
            "local_bounded_approve_commit_tag_worktree_clean",
            local_bounded_approve_commit_tag_worktree_clean,
        )
    )
    local_post_commit_cycle_closure_state = _build_local_post_commit_cycle_closure_artifacts(
        execution_repo_path=execution_repo_path,
        one_cycle_controller_dir=one_cycle_controller_dir,
    )
    local_post_commit_cycle_closure_status = _normalize_text(
        local_post_commit_cycle_closure_state.get("local_post_commit_cycle_closure_status"),
        default=local_post_commit_cycle_closure_status,
    )
    local_post_commit_cycle_closure_blocked_reason = _normalize_text(
        local_post_commit_cycle_closure_state.get(
            "local_post_commit_cycle_closure_blocked_reason"
        ),
        default=local_post_commit_cycle_closure_blocked_reason,
    )
    local_post_commit_cycle_closure_cycle_closed = bool(
        local_post_commit_cycle_closure_state.get(
            "local_post_commit_cycle_closure_cycle_closed",
            local_post_commit_cycle_closure_cycle_closed,
        )
    )
    local_post_commit_cycle_closure_reentry_allowed = bool(
        local_post_commit_cycle_closure_state.get(
            "local_post_commit_cycle_closure_reentry_allowed",
            local_post_commit_cycle_closure_reentry_allowed,
        )
    )
    local_post_commit_cycle_closure_should_continue = bool(
        local_post_commit_cycle_closure_state.get(
            "local_post_commit_cycle_closure_should_continue",
            local_post_commit_cycle_closure_should_continue,
        )
    )
    local_post_commit_cycle_closure_cycle_decision = _normalize_text(
        local_post_commit_cycle_closure_state.get(
            "local_post_commit_cycle_closure_cycle_decision"
        ),
        default=local_post_commit_cycle_closure_cycle_decision,
    )
    local_post_commit_cycle_closure_next_action = _normalize_text(
        local_post_commit_cycle_closure_state.get(
            "local_post_commit_cycle_closure_next_action"
        ),
        default=local_post_commit_cycle_closure_next_action,
    )
    local_post_commit_cycle_closure_commit_hash = _normalize_text(
        local_post_commit_cycle_closure_state.get(
            "local_post_commit_cycle_closure_commit_hash"
        ),
        default=local_post_commit_cycle_closure_commit_hash,
    )
    local_post_commit_cycle_closure_tag_name = _normalize_text(
        local_post_commit_cycle_closure_state.get("local_post_commit_cycle_closure_tag_name"),
        default=local_post_commit_cycle_closure_tag_name,
    )
    local_post_commit_cycle_closure_no_change_cycle_closure = bool(
        local_post_commit_cycle_closure_state.get(
            "local_post_commit_cycle_closure_no_change_cycle_closure",
            local_post_commit_cycle_closure_no_change_cycle_closure,
        )
    )
    local_post_commit_cycle_closure_commit_required = bool(
        local_post_commit_cycle_closure_state.get(
            "local_post_commit_cycle_closure_commit_required",
            local_post_commit_cycle_closure_commit_required,
        )
    )
    local_post_commit_cycle_closure_tag_required = bool(
        local_post_commit_cycle_closure_state.get(
            "local_post_commit_cycle_closure_tag_required",
            local_post_commit_cycle_closure_tag_required,
        )
    )
    local_post_commit_cycle_closure_local_commit_tag_complete = bool(
        local_post_commit_cycle_closure_state.get(
            "local_post_commit_cycle_closure_local_commit_tag_complete",
            local_post_commit_cycle_closure_local_commit_tag_complete,
        )
    )
    local_next_cycle_reentry_status = _normalize_text(
        local_post_commit_cycle_closure_state.get("local_next_cycle_reentry_status"),
        default=local_next_cycle_reentry_status,
    )
    local_next_cycle_reentry_next_action = _normalize_text(
        local_post_commit_cycle_closure_state.get("local_next_cycle_reentry_next_action"),
        default=local_next_cycle_reentry_next_action,
    )
    local_next_cycle_reentry_selected_step_name = _normalize_text(
        local_post_commit_cycle_closure_state.get(
            "local_next_cycle_reentry_selected_step_name"
        ),
        default=local_next_cycle_reentry_selected_step_name,
    )
    local_autonomous_continuation_state = _build_local_autonomous_continuation_artifacts(
        execution_repo_path=execution_repo_path,
        one_cycle_controller_dir=one_cycle_controller_dir,
    )
    local_autonomous_continuation_status = _normalize_text(
        local_autonomous_continuation_state.get("local_autonomous_continuation_status"),
        default=local_autonomous_continuation_status,
    )
    local_autonomous_continuation_blocked_reason = _normalize_text(
        local_autonomous_continuation_state.get(
            "local_autonomous_continuation_blocked_reason"
        ),
        default=local_autonomous_continuation_blocked_reason,
    )
    local_autonomous_continuation_next_action = _normalize_text(
        local_autonomous_continuation_state.get("local_autonomous_continuation_next_action"),
        default=local_autonomous_continuation_next_action,
    )
    local_autonomous_continuation_reentry_connected = bool(
        local_autonomous_continuation_state.get(
            "local_autonomous_continuation_reentry_connected",
            local_autonomous_continuation_reentry_connected,
        )
    )
    local_autonomous_continuation_next_cycle_ready = bool(
        local_autonomous_continuation_state.get(
            "local_autonomous_continuation_next_cycle_ready",
            local_autonomous_continuation_next_cycle_ready,
        )
    )
    local_autonomous_continuation_selected_step_name = _normalize_text(
        local_autonomous_continuation_state.get(
            "local_autonomous_continuation_selected_step_name"
        ),
        default=local_autonomous_continuation_selected_step_name,
    )
    local_autonomous_loop_completion_status = _normalize_text(
        local_autonomous_continuation_state.get("local_autonomous_loop_completion_status"),
        default=local_autonomous_loop_completion_status,
    )
    local_autonomous_loop_completion_final_decision = _normalize_text(
        local_autonomous_continuation_state.get(
            "local_autonomous_loop_completion_final_decision"
        ),
        default=local_autonomous_loop_completion_final_decision,
    )
    local_only_complete_autonomous_loop_ready = bool(
        local_autonomous_continuation_state.get(
            "local_only_complete_autonomous_loop_ready",
            local_only_complete_autonomous_loop_ready,
        )
    )
    local_autonomous_loop_complete = bool(
        local_autonomous_continuation_state.get(
            "local_autonomous_loop_complete",
            local_autonomous_loop_complete,
        )
    )
    local_autonomous_continuation_no_change_cycle_closure = bool(
        local_autonomous_continuation_state.get(
            "local_autonomous_continuation_no_change_cycle_closure",
            local_autonomous_continuation_no_change_cycle_closure,
        )
    )
    local_autonomous_continuation_commit_required = bool(
        local_autonomous_continuation_state.get(
            "local_autonomous_continuation_commit_required",
            local_autonomous_continuation_commit_required,
        )
    )
    local_autonomous_continuation_tag_required = bool(
        local_autonomous_continuation_state.get(
            "local_autonomous_continuation_tag_required",
            local_autonomous_continuation_tag_required,
        )
    )
    local_codex_one_shot_execution_status = _normalize_text(
        local_codex_one_shot_execution_result_state.get("status"),
        default=local_codex_one_shot_execution_status,
    )
    local_codex_one_shot_execution_execution_status = _normalize_text(
        local_codex_one_shot_execution_result_state.get("execution_status"),
        default=local_codex_one_shot_execution_execution_status,
    )
    local_codex_one_shot_execution_next_action = _normalize_text(
        local_codex_one_shot_execution_result_state.get("next_action"),
        default=local_codex_one_shot_execution_next_action,
    )
    local_codex_one_shot_execution_blocked_reason = _normalize_text(
        local_codex_one_shot_execution_result_state.get("blocked_reason"),
        default=local_codex_one_shot_execution_blocked_reason,
    )
    local_codex_one_shot_execution_readiness_reason = _normalize_text(
        local_codex_one_shot_execution_result_state.get("readiness_reason"),
        default=local_codex_one_shot_execution_readiness_reason,
    )
    local_codex_one_shot_execution_codex_invoked = bool(
        local_codex_one_shot_execution_result_state.get(
            "codex_invoked",
            local_codex_one_shot_execution_codex_invoked,
        )
    )
    local_codex_one_shot_execution_codex_invocation_allowed = bool(
        local_codex_one_shot_execution_result_state.get(
            "codex_invocation_allowed",
            local_codex_one_shot_execution_codex_invocation_allowed,
        )
    )
    local_codex_one_shot_execution_execution_allowed = bool(
        local_codex_one_shot_execution_result_state.get(
            "execution_allowed",
            local_codex_one_shot_execution_execution_allowed,
        )
    )
    local_codex_one_shot_execution_execution_attempted = bool(
        local_codex_one_shot_execution_result_state.get(
            "execution_attempted",
            local_codex_one_shot_execution_execution_attempted,
        )
    )
    local_codex_one_shot_execution_execution_completed = bool(
        local_codex_one_shot_execution_result_state.get(
            "execution_completed",
            local_codex_one_shot_execution_execution_completed,
        )
    )
    local_codex_one_shot_execution_execution_exit_code = _as_optional_int(
        local_codex_one_shot_execution_result_state.get("execution_exit_code")
    )
    local_codex_one_shot_execution_max_codex_invocations = _as_non_negative_int(
        local_codex_one_shot_execution_result_state.get("max_codex_invocations"),
        default=local_codex_one_shot_execution_max_codex_invocations,
    )
    local_codex_one_shot_execution_codex_invocation_count = _as_non_negative_int(
        local_codex_one_shot_execution_result_state.get("codex_invocation_count"),
        default=local_codex_one_shot_execution_codex_invocation_count,
    )
    local_codex_one_shot_execution_selected_step_id = _as_optional_int(
        local_codex_one_shot_execution_result_state.get("selected_step_id")
    )
    local_codex_one_shot_execution_selected_step_name = (
        _normalize_text(
            local_codex_one_shot_execution_result_state.get("selected_step_name"),
            default="",
        )
        or None
    )
    local_codex_one_shot_execution_selected_step_operation = (
        _normalize_text(
            local_codex_one_shot_execution_result_state.get("selected_step_operation"),
            default="",
        )
        or None
    )
    local_codex_one_shot_execution_prompt_path = (
        _normalize_text(
            local_codex_one_shot_execution_result_state.get("prompt_path"),
            default="",
        )
        or None
    )
    local_codex_one_shot_execution_stdout_path_text = (
        _normalize_text(
            local_codex_one_shot_execution_result_state.get("stdout_path"),
            default="",
        )
        or None
    )
    local_codex_one_shot_execution_stderr_path_text = (
        _normalize_text(
            local_codex_one_shot_execution_result_state.get("stderr_path"),
            default="",
        )
        or None
    )
    local_codex_one_shot_execution_result_path_text = (
        _normalize_text(
            local_codex_one_shot_execution_result_state.get("result_path"),
            default="",
        )
        or None
    )
    local_codex_one_shot_execution_run_id = _normalize_text(
        local_codex_one_shot_execution_result_state.get("run_id"),
        default=local_codex_one_shot_execution_run_id,
    )
    local_codex_one_shot_execution_cycle_id = _normalize_text(
        local_codex_one_shot_execution_result_state.get("cycle_id"),
        default=local_codex_one_shot_execution_cycle_id,
    )
    local_codex_one_shot_execution_current_cycle = _as_non_negative_int(
        local_codex_one_shot_execution_result_state.get("current_cycle"),
        default=local_codex_one_shot_execution_current_cycle,
    )
    local_codex_one_shot_execution_max_cycles = _as_non_negative_int(
        local_codex_one_shot_execution_result_state.get("max_cycles"),
        default=local_codex_one_shot_execution_max_cycles,
    )
    if prompt365_effective_dry_run:
        prompt365_mutation_capable_dry_run_attempted = bool(
            bool(selected_step_live_execution_operation_state.get("execution_performed", False))
            or bool(
                selected_step_live_execution_operation_state.get(
                    "live_execution_performed",
                    False,
                )
            )
            or bool(selected_step_live_execution_result_state.get("execution_performed", False))
            or bool(
                selected_step_live_execution_result_state.get(
                    "live_execution_performed",
                    False,
                )
            )
            or bool(local_codex_one_shot_execution_result_state.get("execution_attempted", False))
            or bool(local_codex_one_shot_execution_result_state.get("execution_completed", False))
            or bool(local_codex_one_shot_execution_result_state.get("codex_invoked", False))
            or bool(local_codex_one_shot_execution_result_state.get("commit_performed", False))
            or bool(local_codex_one_shot_execution_result_state.get("tag_performed", False))
            or bool(local_codex_one_shot_execution_result_state.get("push_performed", False))
            or bool(local_codex_one_shot_execution_result_state.get("pr_created", False))
            or bool(local_codex_one_shot_execution_result_state.get("merge_performed", False))
            or bool(local_codex_one_shot_execution_result_state.get("rollback_performed", False))
        )
        (
            prompt365_git_state_available_after,
            prompt365_after_changed_tracked_files,
        ) = _collect_changed_tracked_files(normalized_execution_repo_path)
        prompt365_git_state_available = bool(
            prompt365_git_state_available and prompt365_git_state_available_after
        )
        prompt365_new_changed_tracked_files = sorted(
            set(prompt365_after_changed_tracked_files)
            - set(prompt365_before_changed_tracked_files)
        )
        if not prompt365_git_state_available:
            prompt365_runtime_source_mutation_guard_status = "blocked"
            prompt365_blocked_reason = (
                "dry_run_source_mutation_guard_git_state_unavailable"
            )
            prompt365_next_action = "review_dry_run_source_mutation_guard_git_state"
            prompt365_manual_required = True
            prompt365_summary = (
                "Prompt365 blocked dry-run source mutation verification because tracked git state could not be collected across the guarded runtime segment."
            )
        elif prompt365_new_changed_tracked_files:
            prompt365_runtime_source_mutation_guard_status = "blocked"
            prompt365_dry_run_source_mutation_detected = True
            prompt365_blocked_reason = _PROMPT365_DRY_RUN_MUTATION_DETECTED_REASON
            prompt365_next_action = _PROMPT365_DRY_RUN_MUTATION_DETECTED_NEXT_ACTION
            prompt365_manual_required = True
            prompt365_summary = (
                "Prompt365 detected new tracked source mutations during dry-run runtime and blocked continuation."
            )
        elif prompt365_mutation_capable_dry_run_attempted:
            prompt365_runtime_source_mutation_guard_status = "blocked"
            prompt365_mutation_capable_path_blocked = True
            prompt365_blocked_reason = _PROMPT365_DRY_RUN_BLOCKED_REASON
            prompt365_next_action = _PROMPT365_DRY_RUN_BLOCKED_NEXT_ACTION
            prompt365_manual_required = True
            prompt365_summary = (
                "Prompt365 blocked continuation because a mutation-capable dry-run execution path was attempted."
            )
        else:
            prompt365_summary = (
                "Prompt365 confirmed that dry-run runtime did not introduce new tracked source mutations."
            )
    if prompt365_effective_dry_run:
        if not prompt365_git_state_available:
            prompt365_runtime_source_mutation_guard_status = "blocked"
            prompt365_blocked_reason = "dry_run_source_mutation_guard_git_state_unavailable"
            prompt365_next_action = "review_dry_run_source_mutation_guard_git_state"
            prompt365_manual_required = True
            prompt365_summary = (
                "Prompt365 blocked dry-run source mutation verification because tracked git state could not be collected across the guarded runtime segment."
            )
        elif prompt365_dry_run_source_mutation_detected:
            prompt365_runtime_source_mutation_guard_status = "blocked"
            prompt365_blocked_reason = _PROMPT365_DRY_RUN_MUTATION_DETECTED_REASON
            prompt365_next_action = _PROMPT365_DRY_RUN_MUTATION_DETECTED_NEXT_ACTION
            prompt365_manual_required = True
            prompt365_summary = (
                "Prompt365 detected new tracked source mutations during dry-run runtime and blocked continuation."
            )
        elif prompt365_mutation_capable_path_blocked:
            prompt365_runtime_source_mutation_guard_status = "blocked"
            prompt365_blocked_reason = _PROMPT365_DRY_RUN_BLOCKED_REASON
            prompt365_next_action = _PROMPT365_DRY_RUN_BLOCKED_NEXT_ACTION
            prompt365_manual_required = True
            prompt365_summary = (
                "Prompt365 blocked continuation because a mutation-capable dry-run execution path was attempted."
            )
        else:
            prompt365_runtime_source_mutation_guard_status = "clean"
            prompt365_blocked_reason = ""
            prompt365_next_action = "continue"
            prompt365_manual_required = False
            prompt365_summary = (
                "Prompt365 confirmed that dry-run runtime did not introduce new tracked source mutations."
            )

    result_payload = {
        "status": status,
        "next_action": next_action,
        "cycle_count": cycle_count,
        "max_cycles": max_cycles,
        "codex_execution_status": codex_execution_status,
        "diff_capture_status": diff_capture_status,
        "diff_capture_blocked_reason": diff_capture_blocked_reason,
        "diff_stat_path": str(diff_stat_path),
        "diff_name_status_path": str(diff_name_status_path),
        "diff_patch_path": str(diff_patch_path),
        "review_request_status": review_request_status,
        "review_request_blocked_reason": review_request_blocked_reason,
        "review_request_path": str(review_request_path),
        "review_handoff_path": str(review_handoff_path),
        "review_handoff_decision_status": review_handoff_decision_status,
        "tracked_diff_status": tracked_diff_status,
        "no_diff_review_status": no_diff_review_status,
        "no_diff_reason": no_diff_reason,
        "review_handoff_decision_source_path": review_handoff_decision_source_path,
        "review_handoff_decision_next_action": review_handoff_decision_next_action,
        "review_response_status": review_response_status,
        "review_response_decision": review_response_decision,
        "review_response_reason": review_response_reason,
        "review_response_path": str(review_response_path),
        "review_response_next_action": review_response_next_action,
        "targeted_fix_prompt_status": targeted_fix_prompt_status,
        "targeted_fix_prompt_text": targeted_fix_prompt_text,
        "targeted_fix_prompt_path": targeted_fix_prompt_resolved_path,
        "review_route_status": review_route_status,
        "review_route_decision": review_route_decision,
        "review_route_reason": review_route_reason,
        "review_route_next_action": review_route_next_action,
        "review_route_blocked_reason": review_route_blocked_reason,
        "review_route_source": review_route_source,
        "review_route_targeted_fix_prompt_path": review_route_targeted_fix_prompt_path,
        "review_route_should_prepare_commit": review_route_should_prepare_commit,
        "review_route_should_prepare_targeted_fix": review_route_should_prepare_targeted_fix,
        "review_route_should_prepare_reject": review_route_should_prepare_reject,
        "targeted_fix_boundary_status": targeted_fix_boundary_status,
        "targeted_fix_boundary_decision": targeted_fix_boundary_decision,
        "targeted_fix_boundary_reason": targeted_fix_boundary_reason,
        "targeted_fix_boundary_next_action": targeted_fix_boundary_next_action,
        "targeted_fix_boundary_blocked_reason": targeted_fix_boundary_blocked_reason,
        "targeted_fix_boundary_source_prompt_path": targeted_fix_boundary_source_prompt_path,
        "targeted_fix_boundary_codex_prompt_path": targeted_fix_boundary_codex_prompt_path,
        "targeted_fix_boundary_prompt_ready": targeted_fix_boundary_prompt_ready,
        "targeted_fix_boundary_should_execute_codex": targeted_fix_boundary_should_execute_codex,
        "targeted_fix_reentry_execution_enabled": targeted_fix_reentry_execution_enabled,
        "targeted_fix_reentry_execution_confirmed": targeted_fix_reentry_execution_confirmed,
        "targeted_fix_reentry_execution_gate_status": targeted_fix_reentry_execution_gate_status,
        "targeted_fix_reentry_execution_status": targeted_fix_reentry_execution_status,
        "targeted_fix_reentry_execution_attempted": targeted_fix_reentry_execution_attempted,
        "targeted_fix_reentry_execution_exit_code": targeted_fix_reentry_execution_exit_code,
        "targeted_fix_reentry_execution_blocked_reason": (
            targeted_fix_reentry_execution_blocked_reason
        ),
        "targeted_fix_reentry_execution_prompt_path": targeted_fix_reentry_execution_prompt_path,
        "targeted_fix_reentry_execution_receipt_path": str(
            targeted_fix_reentry_execution_receipt_path
        ),
        "targeted_fix_reentry_execution_should_execute_codex": (
            targeted_fix_reentry_execution_should_execute_codex
        ),
        "targeted_fix_post_reentry_diff_capture_status": (
            targeted_fix_post_reentry_diff_capture_status
        ),
        "targeted_fix_post_reentry_diff_capture_attempted": (
            targeted_fix_post_reentry_diff_capture_attempted
        ),
        "targeted_fix_post_reentry_diff_capture_blocked_reason": (
            targeted_fix_post_reentry_diff_capture_blocked_reason
        ),
        "targeted_fix_post_reentry_diff_has_diff": targeted_fix_post_reentry_diff_has_diff,
        "targeted_fix_post_reentry_diff_changed_file_count": (
            targeted_fix_post_reentry_diff_changed_file_count
        ),
        "targeted_fix_post_reentry_review_handoff_status": (
            targeted_fix_post_reentry_review_handoff_status
        ),
        "targeted_fix_post_reentry_review_required": (
            targeted_fix_post_reentry_review_required
        ),
        "targeted_fix_post_reentry_review_assimilation_status": (
            targeted_fix_post_reentry_review_assimilation_status
        ),
        "targeted_fix_post_reentry_review_assimilation_blocked_reason": (
            targeted_fix_post_reentry_review_assimilation_blocked_reason
        ),
        "targeted_fix_post_reentry_review_decision": (
            targeted_fix_post_reentry_review_decision
        ),
        "targeted_fix_post_reentry_route_status": targeted_fix_post_reentry_route_status,
        "targeted_fix_post_reentry_route_decision": (
            targeted_fix_post_reentry_route_decision
        ),
        "targeted_fix_post_reentry_next_action": targeted_fix_post_reentry_next_action,
        "targeted_fix_post_reentry_manual_review_required": (
            targeted_fix_post_reentry_manual_review_required
        ),
        "targeted_fix_post_reentry_targeted_fix_required": (
            targeted_fix_post_reentry_targeted_fix_required
        ),
        "targeted_fix_post_reentry_route_executor_boundary_status": (
            targeted_fix_post_reentry_route_executor_boundary_status
        ),
        "targeted_fix_post_reentry_route_executor_kind": (
            targeted_fix_post_reentry_route_executor_kind
        ),
        "targeted_fix_post_reentry_route_executor_next_action": (
            targeted_fix_post_reentry_route_executor_next_action
        ),
        "targeted_fix_post_reentry_route_executor_execution_allowed": (
            targeted_fix_post_reentry_route_executor_execution_allowed
        ),
        "targeted_fix_post_reentry_route_executor_manual_review_required": (
            targeted_fix_post_reentry_route_executor_manual_review_required
        ),
        "targeted_fix_post_reentry_cycle_closure_allowed": (
            targeted_fix_post_reentry_cycle_closure_allowed
        ),
        "targeted_fix_post_reentry_approval_boundary_allowed": (
            targeted_fix_post_reentry_approval_boundary_allowed
        ),
        "targeted_fix_post_reentry_reject_boundary_allowed": (
            targeted_fix_post_reentry_reject_boundary_allowed
        ),
        "targeted_fix_post_reentry_targeted_fix_prompt_emission_allowed": (
            targeted_fix_post_reentry_targeted_fix_prompt_emission_allowed
        ),
        "targeted_fix_post_reentry_codex_reentry_allowed": (
            targeted_fix_post_reentry_codex_reentry_allowed
        ),
        "targeted_fix_post_reentry_next_step_handoff_status": (
            targeted_fix_post_reentry_next_step_handoff_status
        ),
        "targeted_fix_post_reentry_cycle_closure_status": (
            targeted_fix_post_reentry_cycle_closure_status
        ),
        "targeted_fix_post_reentry_terminal_state": targeted_fix_post_reentry_terminal_state,
        "targeted_fix_post_reentry_cycle_closed": targeted_fix_post_reentry_cycle_closed,
        "targeted_fix_post_reentry_safe_to_stop": targeted_fix_post_reentry_safe_to_stop,
        "targeted_fix_post_reentry_safe_to_commit_prompt_changes": (
            targeted_fix_post_reentry_safe_to_commit_prompt_changes
        ),
        "targeted_fix_post_reentry_requires_codex_reentry": (
            targeted_fix_post_reentry_requires_codex_reentry
        ),
        "targeted_fix_post_reentry_requires_manual_review": (
            targeted_fix_post_reentry_requires_manual_review
        ),
        "targeted_fix_post_reentry_review_response_path": str(
            targeted_fix_post_reentry_review_response_path
        ),
        "targeted_fix_post_reentry_review_assimilation_path": str(
            targeted_fix_post_reentry_review_assimilation_path
        ),
        "targeted_fix_post_reentry_route_decision_path": str(
            targeted_fix_post_reentry_route_decision_path
        ),
        "targeted_fix_post_reentry_route_executor_boundary_path": str(
            targeted_fix_post_reentry_route_executor_boundary_path
        ),
        "targeted_fix_post_reentry_next_step_handoff_path": str(
            targeted_fix_post_reentry_next_step_handoff_path
        ),
        "targeted_fix_post_reentry_cycle_closure_result_path": str(
            targeted_fix_post_reentry_cycle_closure_result_path
        ),
        "targeted_fix_post_reentry_terminal_summary_path": str(
            targeted_fix_post_reentry_terminal_summary_path
        ),
        "targeted_fix_post_reentry_prompt_emission_status": (
            targeted_fix_post_reentry_prompt_emission_status
        ),
        "targeted_fix_post_reentry_prompt_emission_blocked_reason": (
            targeted_fix_post_reentry_prompt_emission_blocked_reason
        ),
        "targeted_fix_post_reentry_prompt_written": targeted_fix_post_reentry_prompt_written,
        "targeted_fix_post_reentry_prompt_ready_for_codex_reentry": (
            targeted_fix_post_reentry_prompt_ready_for_codex_reentry
        ),
        "targeted_fix_post_reentry_prompt_emission_next_action": (
            targeted_fix_post_reentry_prompt_emission_next_action
        ),
        "targeted_fix_post_reentry_prompt_emission_path": str(
            targeted_fix_post_reentry_prompt_emission_path
        ),
        "targeted_fix_post_reentry_prompt_emission_receipt_path": str(
            targeted_fix_post_reentry_prompt_emission_receipt_path
        ),
        "targeted_fix_post_reentry_emitted_prompt_path": (
            targeted_fix_post_reentry_emitted_prompt_path
        ),
        "targeted_fix_post_reentry_codex_reentry_execution_status": (
            targeted_fix_post_reentry_codex_reentry_execution_status
        ),
        "targeted_fix_post_reentry_codex_reentry_gate_status": (
            targeted_fix_post_reentry_codex_reentry_gate_status
        ),
        "targeted_fix_post_reentry_codex_reentry_blocked_reason": (
            targeted_fix_post_reentry_codex_reentry_blocked_reason
        ),
        "targeted_fix_post_reentry_codex_reentry_attempted": (
            targeted_fix_post_reentry_codex_reentry_attempted
        ),
        "targeted_fix_post_reentry_codex_reentry_executed": (
            targeted_fix_post_reentry_codex_reentry_executed
        ),
        "targeted_fix_post_reentry_codex_reentry_exit_code": (
            targeted_fix_post_reentry_codex_reentry_exit_code
        ),
        "targeted_fix_post_reentry_codex_reentry_next_action": (
            targeted_fix_post_reentry_codex_reentry_next_action
        ),
        "targeted_fix_post_reentry_codex_reentry_execution_receipt_path": str(
            targeted_fix_post_reentry_codex_reentry_execution_receipt_path
        ),
        "targeted_fix_post_reentry_codex_reentry_stdout_path": str(
            targeted_fix_post_reentry_codex_reentry_execution_stdout_path
        ),
        "targeted_fix_post_reentry_codex_reentry_stderr_path": str(
            targeted_fix_post_reentry_codex_reentry_execution_stderr_path
        ),
        "targeted_fix_post_reentry_bounded_cycle_status": (
            targeted_fix_post_reentry_bounded_cycle_status
        ),
        "targeted_fix_post_reentry_bounded_cycle_decision": (
            targeted_fix_post_reentry_bounded_cycle_decision
        ),
        "targeted_fix_post_reentry_bounded_cycle_blocked_reason": (
            targeted_fix_post_reentry_bounded_cycle_blocked_reason
        ),
        "targeted_fix_post_reentry_current_cycle_count": (
            targeted_fix_post_reentry_current_cycle_count
        ),
        "targeted_fix_post_reentry_max_cycle_count": (
            targeted_fix_post_reentry_max_cycle_count
        ),
        "targeted_fix_post_reentry_bounded_cycle_complete": (
            targeted_fix_post_reentry_bounded_cycle_complete
        ),
        "targeted_fix_post_reentry_bounded_cycle_should_continue": (
            targeted_fix_post_reentry_bounded_cycle_should_continue
        ),
        "targeted_fix_post_reentry_bounded_cycle_should_emit_prompt": (
            targeted_fix_post_reentry_bounded_cycle_should_emit_prompt
        ),
        "targeted_fix_post_reentry_bounded_cycle_should_execute_codex": (
            targeted_fix_post_reentry_bounded_cycle_should_execute_codex
        ),
        "targeted_fix_post_reentry_bounded_cycle_should_capture_diff": (
            targeted_fix_post_reentry_bounded_cycle_should_capture_diff
        ),
        "targeted_fix_post_reentry_bounded_cycle_next_action": (
            targeted_fix_post_reentry_bounded_cycle_next_action
        ),
        "targeted_fix_post_reentry_bounded_cycle_state_path": str(
            targeted_fix_post_reentry_bounded_cycle_state_path
        ),
        "targeted_fix_post_reentry_bounded_cycle_decision_path": str(
            targeted_fix_post_reentry_bounded_cycle_decision_path
        ),
        "targeted_fix_post_reentry_bounded_cycle_receipt_path": str(
            targeted_fix_post_reentry_bounded_cycle_receipt_path
        ),
        "targeted_fix_post_reentry_diff_capture_path": str(
            targeted_fix_post_reentry_diff_capture_path
        ),
        "targeted_fix_post_reentry_diff_patch_path": str(
            targeted_fix_post_reentry_diff_patch_path
        ),
        "targeted_fix_post_reentry_diff_stat_path": str(
            targeted_fix_post_reentry_diff_stat_path
        ),
        "targeted_fix_post_reentry_diff_name_status_path": str(
            targeted_fix_post_reentry_diff_name_status_path
        ),
        "targeted_fix_post_reentry_review_handoff_path": str(
            targeted_fix_post_reentry_review_handoff_path
        ),
        "approve_commit_tag_boundary_status": approve_commit_tag_boundary_status,
        "approve_commit_tag_boundary_decision": approve_commit_tag_boundary_decision,
        "approve_commit_tag_boundary_reason": approve_commit_tag_boundary_reason,
        "approve_commit_tag_boundary_next_action": approve_commit_tag_boundary_next_action,
        "approve_commit_tag_boundary_blocked_reason": approve_commit_tag_boundary_blocked_reason,
        "approve_commit_tag_boundary_commit_message": approve_commit_tag_boundary_commit_message,
        "approve_commit_tag_boundary_tag_name": approve_commit_tag_boundary_tag_name,
        "approve_commit_tag_boundary_commands_path": (
            approve_commit_tag_boundary_commands_resolved_path
        ),
        "approve_commit_tag_boundary_metadata_path": (
            approve_commit_tag_boundary_metadata_resolved_path
        ),
        "approve_commit_tag_boundary_should_execute_commit": (
            approve_commit_tag_boundary_should_execute_commit
        ),
        "approve_commit_tag_boundary_should_execute_tag": (
            approve_commit_tag_boundary_should_execute_tag
        ),
        "approve_commit_tag_boundary_ready": approve_commit_tag_boundary_ready,
        "approve_commit_tag_plan_ready": approve_commit_tag_plan_ready,
        "approve_commit_tag_tracked_files_allowed": approve_commit_tag_tracked_files_allowed,
        "approve_commit_tag_changed_tracked_files": approve_commit_tag_changed_tracked_files,
        "approve_commit_tag_unexpected_tracked_files": (
            approve_commit_tag_unexpected_tracked_files
        ),
        "approve_commit_tag_explicit_add_paths": approve_commit_tag_explicit_add_paths,
        "approve_commit_tag_proposed_commit_message": (
            approve_commit_tag_proposed_commit_message
        ),
        "approve_commit_tag_proposed_tag": approve_commit_tag_proposed_tag,
        "approve_commit_tag_command_file_path": approve_commit_tag_command_file_path,
        "approve_commit_tag_execution_allowed": approve_commit_tag_execution_allowed,
        "approve_commit_tag_next_action": approve_commit_tag_boundary_next_action,
        "approve_commit_tag_boundary_path": approve_commit_tag_boundary_path,
        "approve_commit_tag_plan_path": approve_commit_tag_plan_path,
        "approve_commit_tag_artifact_reconciliation_status": (
            approve_commit_tag_artifact_reconciliation_status
        ),
        "approve_commit_tag_artifact_reconciliation_blocked_reason": (
            approve_commit_tag_artifact_reconciliation_blocked_reason
        ),
        "approve_commit_tag_artifact_reconciliation_stale_artifacts_detected": (
            approve_commit_tag_artifact_reconciliation_stale_artifacts_detected
        ),
        "approve_commit_tag_artifact_reconciliation_already_committed": (
            approve_commit_tag_artifact_reconciliation_already_committed
        ),
        "approve_commit_tag_artifact_reconciliation_already_tagged": (
            approve_commit_tag_artifact_reconciliation_already_tagged
        ),
        "approve_commit_tag_artifact_reconciliation_next_action": (
            approve_commit_tag_artifact_reconciliation_next_action
        ),
        "approve_commit_tag_artifact_reconciliation_receipt_path": (
            approve_commit_tag_artifact_reconciliation_receipt_path
        ),
        "remote_readiness_boundary_status": remote_readiness_boundary_status,
        "remote_readiness_blocked_reason": remote_readiness_blocked_reason,
        "remote_readiness_remote_ready": remote_readiness_remote_ready,
        "remote_readiness_push_ready": remote_readiness_push_ready,
        "remote_readiness_pr_ready": remote_readiness_pr_ready,
        "remote_readiness_merge_ready": remote_readiness_merge_ready,
        "remote_readiness_worktree_clean": remote_readiness_worktree_clean,
        "remote_readiness_expected_head_tag_present": (
            remote_readiness_expected_head_tag_present
        ),
        "remote_readiness_remote_configured": remote_readiness_remote_configured,
        "remote_readiness_upstream_configured": remote_readiness_upstream_configured,
        "remote_readiness_next_action": remote_readiness_next_action,
        "remote_readiness_boundary_path": remote_readiness_boundary_path,
        "remote_readiness_plan_path": remote_readiness_plan_path,
        "local_end_to_end_readiness_status": local_end_to_end_readiness_status,
        "local_end_to_end_readiness_blocked_reason": local_end_to_end_readiness_blocked_reason,
        "local_end_to_end_ready": local_end_to_end_ready,
        "local_components_ready": local_components_ready,
        "integrated_local_runner_ready": integrated_local_runner_ready,
        "implementation_prompt_generation_status": implementation_prompt_generation_status,
        "github_deferred": github_deferred,
        "remote_required": remote_required,
        "local_end_to_end_next_action": local_end_to_end_next_action,
        "local_end_to_end_component_matrix_path": local_end_to_end_component_matrix_surface_path,
        "local_end_to_end_readiness_boundary_path": (
            local_end_to_end_readiness_boundary_surface_path
        ),
        "local_end_to_end_gap_report_path": local_end_to_end_gap_report_surface_path,
        "local_autonomous_cycle_v2_status": local_autonomous_cycle_v2_status,
        "local_autonomous_cycle_v2_cycle_status": local_autonomous_cycle_v2_cycle_status,
        "local_autonomous_cycle_v2_next_action": local_autonomous_cycle_v2_next_action,
        "local_autonomous_cycle_v2_selected_step_id": local_autonomous_cycle_v2_selected_step_id,
        "local_autonomous_cycle_v2_selected_step_name": (
            local_autonomous_cycle_v2_selected_step_name
        ),
        "local_autonomous_cycle_v2_selected_step_operation": (
            local_autonomous_cycle_v2_selected_step_operation
        ),
        "local_autonomous_cycle_v2_decision": local_autonomous_cycle_v2_decision,
        "local_autonomous_cycle_v2_ready": local_autonomous_cycle_v2_ready,
        "local_autonomous_cycle_v2_blocked_reason": local_autonomous_cycle_v2_blocked_reason,
        "local_autonomous_cycle_v2_readiness_reason": local_autonomous_cycle_v2_readiness_reason,
        "local_autonomous_cycle_v2_run_id": local_autonomous_cycle_v2_run_id,
        "local_autonomous_cycle_v2_cycle_id": local_autonomous_cycle_v2_cycle_id,
        "local_autonomous_cycle_v2_current_cycle": local_autonomous_cycle_v2_current_cycle,
        "local_autonomous_cycle_v2_max_cycles": local_autonomous_cycle_v2_max_cycles,
        "local_autonomous_cycle_v2_state_path": local_autonomous_cycle_v2_state_surface_path,
        "local_autonomous_cycle_v2_decision_path": (
            local_autonomous_cycle_v2_decision_surface_path
        ),
        "local_autonomous_cycle_v2_receipt_path": local_autonomous_cycle_v2_receipt_surface_path,
        "local_codex_one_shot_handoff_status": local_codex_one_shot_handoff_status,
        "local_codex_one_shot_handoff_handoff_status": (
            local_codex_one_shot_handoff_handoff_status
        ),
        "local_codex_one_shot_handoff_next_action": local_codex_one_shot_handoff_next_action,
        "local_codex_one_shot_handoff_blocked_reason": (
            local_codex_one_shot_handoff_blocked_reason
        ),
        "local_codex_one_shot_handoff_readiness_reason": (
            local_codex_one_shot_handoff_readiness_reason
        ),
        "local_codex_one_shot_handoff_prompt_ready": (
            local_codex_one_shot_handoff_prompt_ready
        ),
        "local_codex_one_shot_handoff_command_ready": (
            local_codex_one_shot_handoff_command_ready
        ),
        "local_codex_one_shot_handoff_codex_invocation_allowed": (
            local_codex_one_shot_handoff_codex_invocation_allowed
        ),
        "local_codex_one_shot_handoff_execution_allowed": (
            local_codex_one_shot_handoff_execution_allowed
        ),
        "local_codex_one_shot_handoff_max_codex_invocations": (
            local_codex_one_shot_handoff_max_codex_invocations
        ),
        "local_codex_one_shot_handoff_codex_invocation_count": (
            local_codex_one_shot_handoff_codex_invocation_count
        ),
        "local_codex_one_shot_handoff_selected_step_id": (
            local_codex_one_shot_handoff_selected_step_id
        ),
        "local_codex_one_shot_handoff_selected_step_name": (
            local_codex_one_shot_handoff_selected_step_name
        ),
        "local_codex_one_shot_handoff_selected_step_operation": (
            local_codex_one_shot_handoff_selected_step_operation
        ),
        "local_codex_one_shot_handoff_prompt_path": local_codex_one_shot_handoff_prompt_path,
        "local_codex_one_shot_handoff_command_display": (
            local_codex_one_shot_handoff_command_display
        ),
        "local_codex_one_shot_handoff_run_id": local_codex_one_shot_handoff_run_id,
        "local_codex_one_shot_handoff_cycle_id": local_codex_one_shot_handoff_cycle_id,
        "local_codex_one_shot_handoff_current_cycle": (
            local_codex_one_shot_handoff_current_cycle
        ),
        "local_codex_one_shot_handoff_max_cycles": local_codex_one_shot_handoff_max_cycles,
        "local_codex_one_shot_execution_status": local_codex_one_shot_execution_status,
        "local_codex_one_shot_execution_execution_status": (
            local_codex_one_shot_execution_execution_status
        ),
        "local_codex_one_shot_execution_next_action": local_codex_one_shot_execution_next_action,
        "local_codex_one_shot_execution_blocked_reason": (
            local_codex_one_shot_execution_blocked_reason
        ),
        "local_codex_one_shot_execution_readiness_reason": (
            local_codex_one_shot_execution_readiness_reason
        ),
        "local_codex_one_shot_execution_codex_invoked": (
            local_codex_one_shot_execution_codex_invoked
        ),
        "local_codex_one_shot_execution_codex_invocation_allowed": (
            local_codex_one_shot_execution_codex_invocation_allowed
        ),
        "local_codex_one_shot_execution_execution_allowed": (
            local_codex_one_shot_execution_execution_allowed
        ),
        "local_codex_one_shot_execution_execution_attempted": (
            local_codex_one_shot_execution_execution_attempted
        ),
        "local_codex_one_shot_execution_execution_completed": (
            local_codex_one_shot_execution_execution_completed
        ),
        "local_codex_one_shot_execution_execution_exit_code": (
            local_codex_one_shot_execution_execution_exit_code
        ),
        "local_codex_one_shot_execution_max_codex_invocations": (
            local_codex_one_shot_execution_max_codex_invocations
        ),
        "local_codex_one_shot_execution_codex_invocation_count": (
            local_codex_one_shot_execution_codex_invocation_count
        ),
        "local_codex_one_shot_execution_selected_step_id": (
            local_codex_one_shot_execution_selected_step_id
        ),
        "local_codex_one_shot_execution_selected_step_name": (
            local_codex_one_shot_execution_selected_step_name
        ),
        "local_codex_one_shot_execution_selected_step_operation": (
            local_codex_one_shot_execution_selected_step_operation
        ),
        "local_codex_one_shot_execution_prompt_path": (
            local_codex_one_shot_execution_prompt_path
        ),
        "local_codex_one_shot_execution_stdout_path": (
            local_codex_one_shot_execution_stdout_path_text
        ),
        "local_codex_one_shot_execution_stderr_path": (
            local_codex_one_shot_execution_stderr_path_text
        ),
        "local_codex_one_shot_execution_result_path": (
            local_codex_one_shot_execution_result_path_text
        ),
        "local_codex_one_shot_execution_run_id": local_codex_one_shot_execution_run_id,
        "local_codex_one_shot_execution_cycle_id": local_codex_one_shot_execution_cycle_id,
        "local_codex_one_shot_execution_current_cycle": (
            local_codex_one_shot_execution_current_cycle
        ),
        "local_codex_one_shot_execution_max_cycles": local_codex_one_shot_execution_max_cycles,
        "prompt365_runtime_source_mutation_guard_status": (
            prompt365_runtime_source_mutation_guard_status
        ),
        "prompt365_dry_run_source_mutation_detected": (
            prompt365_dry_run_source_mutation_detected
        ),
        "prompt365_mutation_capable_path_blocked": (
            prompt365_mutation_capable_path_blocked
        ),
        "prompt365_before_changed_tracked_files": (
            prompt365_before_changed_tracked_files
        ),
        "prompt365_after_changed_tracked_files": prompt365_after_changed_tracked_files,
        "prompt365_new_changed_tracked_files": prompt365_new_changed_tracked_files,
        "prompt365_blocked_reason": prompt365_blocked_reason,
        "prompt365_next_action": prompt365_next_action,
        "prompt365_manual_required": prompt365_manual_required,
        "prompt365_summary": prompt365_summary,
        "local_post_codex_diff_capture_status": local_post_codex_diff_capture_status,
        "local_post_codex_diff_capture_blocked_reason": local_post_codex_diff_capture_blocked_reason,
        "local_post_codex_diff_capture_next_action": local_post_codex_diff_capture_next_action,
        "local_post_codex_diff_capture_worktree_clean_for_tracked_files": (
            local_post_codex_diff_capture_worktree_clean_for_tracked_files
        ),
        "local_post_codex_diff_capture_changed_tracked_file_count": (
            local_post_codex_diff_capture_changed_tracked_file_count
        ),
        "local_post_codex_outcome_status": local_post_codex_outcome_status,
        "local_post_codex_outcome_classification": local_post_codex_outcome_classification,
        "local_post_codex_stdout_contains_blocked": local_post_codex_stdout_contains_blocked,
        "local_post_codex_stdout_blocked_reason": local_post_codex_stdout_blocked_reason,
        "local_post_codex_route_status": local_post_codex_route_status,
        "local_post_codex_route_decision": local_post_codex_route_decision,
        "local_post_codex_route_next_action": local_post_codex_route_next_action,
        "local_post_codex_route_targeted_contract_fix_recommended": (
            local_post_codex_route_targeted_contract_fix_recommended
        ),
        "local_post_codex_route_approve_commit_tag_allowed": (
            local_post_codex_route_approve_commit_tag_allowed
        ),
        "prompt334_stale_post_codex_artifact_detected": (
            prompt334_stale_post_codex_artifact_detected
        ),
        "prompt334_stale_post_codex_artifact_regeneration_attempted": (
            prompt334_stale_post_codex_artifact_regeneration_attempted
        ),
        "prompt334_stale_post_codex_artifact_regeneration_reason": (
            prompt334_stale_post_codex_artifact_regeneration_reason
        ),
        "prompt334_stale_post_codex_artifact_regeneration_status": (
            prompt334_stale_post_codex_artifact_regeneration_status
        ),
        "local_post_codex_diff_capture_path": str(local_post_codex_diff_capture_path),
        "local_post_codex_execution_outcome_path": str(local_post_codex_execution_outcome_path),
        "local_post_codex_route_decision_path": str(local_post_codex_route_decision_path),
        "local_post_codex_diff_capture_receipt_path": str(local_post_codex_diff_capture_receipt_path),
        "local_targeted_contract_fix_route_intake_status": (
            local_targeted_contract_fix_route_intake_status
        ),
        "local_targeted_contract_fix_route_intake_blocked_reason": (
            local_targeted_contract_fix_route_intake_blocked_reason
        ),
        "local_targeted_contract_fix_route_intake_signal_source": (
            local_targeted_contract_fix_route_intake_signal_source
        ),
        "local_targeted_contract_fix_prompt_plan_status": (
            local_targeted_contract_fix_prompt_plan_status
        ),
        "local_targeted_contract_fix_prompt_plan_blocked_reason": (
            local_targeted_contract_fix_prompt_plan_blocked_reason
        ),
        "local_targeted_contract_fix_prompt_path": local_targeted_contract_fix_prompt_path_text,
        "local_targeted_contract_fix_prompt_ready": local_targeted_contract_fix_prompt_ready,
        "local_targeted_contract_fix_prompt_next_action": (
            local_targeted_contract_fix_prompt_next_action
        ),
        "local_targeted_contract_fix_prompt_normalized_reason": (
            local_targeted_contract_fix_prompt_normalized_reason
        ),
        "local_targeted_contract_fix_prompt_lifecycle_issue_detected": (
            local_targeted_contract_fix_prompt_lifecycle_issue_detected
        ),
        "local_contract_fix_cycle_coordination_status": (
            local_contract_fix_cycle_coordination_status
        ),
        "local_contract_fix_cycle_coordination_blocked_reason": (
            local_contract_fix_cycle_coordination_blocked_reason
        ),
        "local_contract_fix_cycle_coordination_ready": (
            local_contract_fix_cycle_coordination_ready
        ),
        "local_contract_fix_cycle_coordination_next_action": (
            local_contract_fix_cycle_coordination_next_action
        ),
        "local_contract_fix_cycle_prompt_path": local_contract_fix_cycle_prompt_path,
        "local_contract_fix_cycle_prompt_ready": local_contract_fix_cycle_prompt_ready,
        "local_contract_fix_cycle_normalized_reason": (
            local_contract_fix_cycle_normalized_reason
        ),
        "local_contract_fix_cycle_selected_step_name": (
            local_contract_fix_cycle_selected_step_name
        ),
        "local_contract_fix_cycle_handoff_status": local_contract_fix_cycle_handoff_status,
        "local_contract_fix_cycle_handoff_next_action": (
            local_contract_fix_cycle_handoff_next_action
        ),
        "local_daemon_lite_wrapper_status": local_daemon_lite_wrapper_status,
        "local_daemon_lite_wrapper_blocked_reason": local_daemon_lite_wrapper_blocked_reason,
        "local_daemon_lite_wrapper_ready": local_daemon_lite_wrapper_ready,
        "local_daemon_lite_wrapper_decision": local_daemon_lite_wrapper_decision,
        "local_daemon_lite_wrapper_next_action": local_daemon_lite_wrapper_next_action,
        "local_daemon_lite_wrapper_selected_step_name": (
            local_daemon_lite_wrapper_selected_step_name
        ),
        "local_daemon_lite_wrapper_prompt_path": local_daemon_lite_wrapper_prompt_path,
        "local_daemon_lite_wrapper_bounded_execution": (
            local_daemon_lite_wrapper_bounded_execution
        ),
        "local_daemon_lite_wrapper_total_codex_invocation_budget": (
            local_daemon_lite_wrapper_total_codex_invocation_budget
        ),
        "local_targeted_contract_fix_execution_status": (
            local_targeted_contract_fix_execution_status
        ),
        "local_targeted_contract_fix_execution_blocked_reason": (
            local_targeted_contract_fix_execution_blocked_reason
        ),
        "local_targeted_contract_fix_execution_next_action": (
            local_targeted_contract_fix_execution_next_action
        ),
        "local_targeted_contract_fix_execution_codex_invoked": (
            local_targeted_contract_fix_execution_codex_invoked
        ),
        "local_targeted_contract_fix_execution_exit_code": (
            local_targeted_contract_fix_execution_exit_code
        ),
        "local_targeted_contract_fix_execution_changed_tracked_file_count": (
            local_targeted_contract_fix_execution_changed_tracked_file_count
        ),
        "local_targeted_contract_fix_execution_stdout_path": (
            local_targeted_contract_fix_execution_stdout_path_text
        ),
        "local_targeted_contract_fix_execution_stderr_path": (
            local_targeted_contract_fix_execution_stderr_path_text
        ),
        "local_post_targeted_contract_fix_status": local_post_targeted_contract_fix_status,
        "local_post_targeted_contract_fix_blocked_reason": (
            local_post_targeted_contract_fix_blocked_reason
        ),
        "local_post_targeted_contract_fix_classification": (
            local_post_targeted_contract_fix_classification
        ),
        "local_post_targeted_contract_fix_route_decision": (
            local_post_targeted_contract_fix_route_decision
        ),
        "local_post_targeted_contract_fix_next_action": (
            local_post_targeted_contract_fix_next_action
        ),
        "local_post_targeted_contract_fix_approve_commit_tag_ready": (
            local_post_targeted_contract_fix_approve_commit_tag_ready
        ),
        "local_post_targeted_contract_fix_changed_tracked_file_count": (
            local_post_targeted_contract_fix_changed_tracked_file_count
        ),
        "local_post_targeted_contract_fix_unexpected_tracked_file_count": (
            local_post_targeted_contract_fix_unexpected_tracked_file_count
        ),
        "local_post_targeted_contract_fix_diff_capture_path": str(
            local_post_targeted_contract_fix_diff_capture_path
        ),
        "local_post_targeted_contract_fix_execution_outcome_path": str(
            local_post_targeted_contract_fix_execution_outcome_path
        ),
        "local_post_targeted_contract_fix_route_decision_path": str(
            local_post_targeted_contract_fix_route_decision_path
        ),
        "local_post_targeted_contract_fix_review_receipt_path": str(
            local_post_targeted_contract_fix_review_receipt_path
        ),
        "local_bounded_approve_commit_tag_status": (
            local_bounded_approve_commit_tag_status
        ),
        "local_bounded_approve_commit_tag_execution_status": (
            local_bounded_approve_commit_tag_execution_status
        ),
        "local_bounded_approve_commit_tag_blocked_reason": (
            local_bounded_approve_commit_tag_blocked_reason
        ),
        "local_bounded_approve_commit_tag_next_action": (
            local_bounded_approve_commit_tag_next_action
        ),
        "local_bounded_approve_commit_tag_commit_performed": (
            local_bounded_approve_commit_tag_commit_performed
        ),
        "local_bounded_approve_commit_tag_tag_performed": (
            local_bounded_approve_commit_tag_tag_performed
        ),
        "local_bounded_approve_commit_tag_commit_hash": (
            local_bounded_approve_commit_tag_commit_hash
        ),
        "local_bounded_approve_commit_tag_tag_name": (
            local_bounded_approve_commit_tag_tag_name
        ),
        "local_bounded_approve_commit_tag_worktree_clean": (
            local_bounded_approve_commit_tag_worktree_clean
        ),
        "local_bounded_approve_commit_tag_gate_state_path": str(
            local_bounded_approve_commit_tag_gate_state_path
        ),
        "local_bounded_approve_commit_tag_execution_result_path": str(
            local_bounded_approve_commit_tag_execution_result_path
        ),
        "local_bounded_approve_commit_tag_execution_receipt_path": str(
            local_bounded_approve_commit_tag_execution_receipt_path
        ),
        "local_bounded_approve_commit_tag_plan_path": str(
            local_bounded_approve_commit_tag_plan_path
        ),
        "local_post_commit_cycle_closure_status": (
            local_post_commit_cycle_closure_status
        ),
        "local_post_commit_cycle_closure_blocked_reason": (
            local_post_commit_cycle_closure_blocked_reason
        ),
        "local_post_commit_cycle_closure_cycle_closed": (
            local_post_commit_cycle_closure_cycle_closed
        ),
        "local_post_commit_cycle_closure_reentry_allowed": (
            local_post_commit_cycle_closure_reentry_allowed
        ),
        "local_post_commit_cycle_closure_should_continue": (
            local_post_commit_cycle_closure_should_continue
        ),
        "local_post_commit_cycle_closure_cycle_decision": (
            local_post_commit_cycle_closure_cycle_decision
        ),
        "local_post_commit_cycle_closure_next_action": (
            local_post_commit_cycle_closure_next_action
        ),
        "local_post_commit_cycle_closure_commit_hash": (
            local_post_commit_cycle_closure_commit_hash
        ),
        "local_post_commit_cycle_closure_tag_name": (
            local_post_commit_cycle_closure_tag_name
        ),
        "local_post_commit_cycle_closure_no_change_cycle_closure": (
            local_post_commit_cycle_closure_no_change_cycle_closure
        ),
        "local_post_commit_cycle_closure_commit_required": (
            local_post_commit_cycle_closure_commit_required
        ),
        "local_post_commit_cycle_closure_tag_required": (
            local_post_commit_cycle_closure_tag_required
        ),
        "local_post_commit_cycle_closure_local_commit_tag_complete": (
            local_post_commit_cycle_closure_local_commit_tag_complete
        ),
        "local_next_cycle_reentry_status": local_next_cycle_reentry_status,
        "local_next_cycle_reentry_next_action": local_next_cycle_reentry_next_action,
        "local_next_cycle_reentry_selected_step_name": (
            local_next_cycle_reentry_selected_step_name
        ),
        "local_post_commit_cycle_closure_state_path": str(
            local_post_commit_cycle_closure_state_path
        ),
        "local_post_commit_cycle_closure_decision_path": str(
            local_post_commit_cycle_closure_decision_path
        ),
        "local_post_commit_cycle_closure_receipt_path": str(
            local_post_commit_cycle_closure_receipt_path
        ),
        "local_next_cycle_reentry_decision_path": str(
            local_next_cycle_reentry_decision_path
        ),
        "local_autonomous_continuation_status": local_autonomous_continuation_status,
        "local_autonomous_continuation_blocked_reason": (
            local_autonomous_continuation_blocked_reason
        ),
        "local_autonomous_continuation_next_action": (
            local_autonomous_continuation_next_action
        ),
        "local_autonomous_continuation_reentry_connected": (
            local_autonomous_continuation_reentry_connected
        ),
        "local_autonomous_continuation_next_cycle_ready": (
            local_autonomous_continuation_next_cycle_ready
        ),
        "local_autonomous_continuation_selected_step_name": (
            local_autonomous_continuation_selected_step_name
        ),
        "local_autonomous_loop_completion_status": local_autonomous_loop_completion_status,
        "local_autonomous_loop_completion_final_decision": (
            local_autonomous_loop_completion_final_decision
        ),
        "local_only_complete_autonomous_loop_ready": (
            local_only_complete_autonomous_loop_ready
        ),
        "local_autonomous_loop_complete": local_autonomous_loop_complete,
        "local_autonomous_continuation_no_change_cycle_closure": (
            local_autonomous_continuation_no_change_cycle_closure
        ),
        "local_autonomous_continuation_commit_required": (
            local_autonomous_continuation_commit_required
        ),
        "local_autonomous_continuation_tag_required": (
            local_autonomous_continuation_tag_required
        ),
        "local_autonomous_continuation_state_path": str(
            local_autonomous_continuation_state_path
        ),
        "local_autonomous_continuation_decision_path": str(
            local_autonomous_continuation_decision_path
        ),
        "local_autonomous_continuation_receipt_path": str(
            local_autonomous_continuation_receipt_path
        ),
        "local_autonomous_next_cycle_selection_path": str(
            local_autonomous_next_cycle_selection_path
        ),
        "local_autonomous_loop_completion_summary_path": str(
            local_autonomous_loop_completion_summary_path
        ),
        "approve_commit_tag_execution_enabled": approve_commit_tag_execution_enabled,
        "approve_commit_tag_execution_confirmed": approve_commit_tag_execution_confirmed,
        "approve_commit_tag_execution_gate_status": approve_commit_tag_execution_gate_status,
        "approve_commit_tag_execution_status": approve_commit_tag_execution_status,
        "approve_commit_tag_execution_attempted": approve_commit_tag_execution_attempted,
        "approve_commit_tag_execution_exit_code": approve_commit_tag_execution_exit_code,
        "approve_commit_tag_execution_blocked_reason": (
            approve_commit_tag_execution_blocked_reason
        ),
        "approve_commit_tag_execution_commit_message": (
            approve_commit_tag_execution_commit_message
        ),
        "approve_commit_tag_execution_tag_name": approve_commit_tag_execution_tag_name,
        "approve_commit_tag_execution_receipt_path": str(
            approve_commit_tag_execution_receipt_path
        ),
        "approve_commit_tag_execution_should_commit": (
            approve_commit_tag_execution_should_commit
        ),
        "approve_commit_tag_execution_should_tag": approve_commit_tag_execution_should_tag,
        "completed_result_source_path": str(completed_result_source_path),
        "completed_result_source_status": completed_result_source_status,
        "stop_reason": stop_reason,
        "enabled": enabled,
        "execute_enabled": execute_enabled,
        "exec_plan_path": str(exec_plan_path),
        "exec_plan_safety_status": exec_plan_safety_status,
        "exec_plan_blocked_reason": exec_plan_blocked_reason,
        "exec_plan_required_fragments_present": exec_plan_required_fragments_present,
        "exec_plan_banned_fragments_present": exec_plan_banned_fragments_present,
        "exec_plan_execution_status": exec_plan_execution_status,
        "execution_attempted": execution_attempted,
        "execution_blocked_reason": execution_blocked_reason,
        "execution_gate_status": execution_gate_status,
        "execution_exit_code": execution_exit_code,
        "execution_stdout_path": str(execution_stdout_path),
        "execution_stderr_path": str(execution_stderr_path),
        "execution_runlog_path": str(execution_runlog_path),
        "execution_started_at": execution_started_at,
        "execution_finished_at": execution_finished_at,
        "artifact_paths": artifact_paths,
        "runtime_posture": runtime_posture,
    }
    summary_lines = [
        "# One Cycle Controller Readiness",
        "",
        f"- Status: `{status}`",
        f"- Next action: `{next_action}`",
        f"- Cycle count: `{cycle_count}`",
        f"- Max cycles: `{max_cycles}`",
        f"- Codex execution status: `{codex_execution_status}`",
        f"- Prompt334 diff capture status: `{local_post_codex_diff_capture_status}`",
        f"- Prompt334 outcome class: `{local_post_codex_outcome_classification}`",
        f"- Prompt334 route decision: `{local_post_codex_route_decision}`",
        f"- Prompt334 route next action: `{local_post_codex_route_next_action}`",
        (
            "- Prompt335 route intake status: "
            f"`{local_targeted_contract_fix_route_intake_status}`"
        ),
        (
            "- Prompt335 route intake blocked reason: "
            f"`{local_targeted_contract_fix_route_intake_blocked_reason}`"
        ),
        (
            "- Prompt335 route intake signal source: "
            f"`{local_targeted_contract_fix_route_intake_signal_source}`"
        ),
        f"- Prompt335 prompt plan status: `{local_targeted_contract_fix_prompt_plan_status}`",
        (
            "- Prompt335 prompt plan blocked reason: "
            f"`{local_targeted_contract_fix_prompt_plan_blocked_reason}`"
        ),
        f"- Prompt335 prompt path: `{local_targeted_contract_fix_prompt_path_text}`",
        (
            "- Prompt335 prompt ready: "
            f"`{str(local_targeted_contract_fix_prompt_ready).lower()}`"
        ),
        (
            "- Prompt335 prompt next action: "
            f"`{local_targeted_contract_fix_prompt_next_action}`"
        ),
        (
            "- Prompt335 normalized blocked reason: "
            f"`{local_targeted_contract_fix_prompt_normalized_reason or 'none'}`"
        ),
        (
            "- Prompt335 lifecycle issue detected: "
            f"`{str(local_targeted_contract_fix_prompt_lifecycle_issue_detected).lower()}`"
        ),
        (
            "- Prompt336 coordination status: "
            f"`{local_contract_fix_cycle_coordination_status}`"
        ),
        (
            "- Prompt336 coordination blocked reason: "
            f"`{local_contract_fix_cycle_coordination_blocked_reason}`"
        ),
        (
            "- Prompt336 coordination ready: "
            f"`{str(local_contract_fix_cycle_coordination_ready).lower()}`"
        ),
        (
            "- Prompt336 coordination next action: "
            f"`{local_contract_fix_cycle_coordination_next_action}`"
        ),
        f"- Prompt336 prompt path: `{local_contract_fix_cycle_prompt_path}`",
        (
            "- Prompt336 prompt ready: "
            f"`{str(local_contract_fix_cycle_prompt_ready).lower()}`"
        ),
        (
            "- Prompt336 normalized reason: "
            f"`{local_contract_fix_cycle_normalized_reason or 'none'}`"
        ),
        (
            "- Prompt336 selected step name: "
            f"`{local_contract_fix_cycle_selected_step_name}`"
        ),
        (
            "- Prompt336 handoff status: "
            f"`{local_contract_fix_cycle_handoff_status}`"
        ),
        (
            "- Prompt336 handoff next action: "
            f"`{local_contract_fix_cycle_handoff_next_action}`"
        ),
        f"- Prompt337 daemon-lite wrapper status: `{local_daemon_lite_wrapper_status}`",
        (
            "- Prompt337 daemon-lite wrapper blocked reason: "
            f"`{local_daemon_lite_wrapper_blocked_reason}`"
        ),
        (
            "- Prompt337 daemon-lite wrapper ready: "
            f"`{str(local_daemon_lite_wrapper_ready).lower()}`"
        ),
        f"- Prompt337 daemon-lite wrapper decision: `{local_daemon_lite_wrapper_decision}`",
        (
            "- Prompt337 daemon-lite wrapper next action: "
            f"`{local_daemon_lite_wrapper_next_action}`"
        ),
        (
            "- Prompt337 daemon-lite wrapper selected step name: "
            f"`{local_daemon_lite_wrapper_selected_step_name}`"
        ),
        f"- Prompt337 daemon-lite wrapper prompt path: `{local_daemon_lite_wrapper_prompt_path}`",
        (
            "- Prompt337 daemon-lite wrapper bounded execution: "
            f"`{str(local_daemon_lite_wrapper_bounded_execution).lower()}`"
        ),
        (
            "- Prompt337 daemon-lite wrapper total codex invocation budget: "
            f"`{local_daemon_lite_wrapper_total_codex_invocation_budget}`"
        ),
        f"- Prompt338 targeted contract-fix execution status: `{local_targeted_contract_fix_execution_status}`",
        (
            "- Prompt338 targeted contract-fix execution blocked reason: "
            f"`{local_targeted_contract_fix_execution_blocked_reason}`"
        ),
        (
            "- Prompt338 targeted contract-fix execution next action: "
            f"`{local_targeted_contract_fix_execution_next_action}`"
        ),
        (
            "- Prompt338 targeted contract-fix execution codex invoked: "
            f"`{str(local_targeted_contract_fix_execution_codex_invoked).lower()}`"
        ),
        (
            "- Prompt338 targeted contract-fix execution exit code: "
            f"`{local_targeted_contract_fix_execution_exit_code}`"
        ),
        (
            "- Prompt338 targeted contract-fix changed tracked file count: "
            f"`{local_targeted_contract_fix_execution_changed_tracked_file_count}`"
        ),
        (
            "- Prompt338 targeted contract-fix stdout path: "
            f"`{local_targeted_contract_fix_execution_stdout_path_text}`"
        ),
        (
            "- Prompt338 targeted contract-fix stderr path: "
            f"`{local_targeted_contract_fix_execution_stderr_path_text}`"
        ),
        f"- Prompt339 post-targeted-contract-fix status: `{local_post_targeted_contract_fix_status}`",
        (
            "- Prompt339 post-targeted-contract-fix blocked reason: "
            f"`{local_post_targeted_contract_fix_blocked_reason}`"
        ),
        (
            "- Prompt339 post-targeted-contract-fix classification: "
            f"`{local_post_targeted_contract_fix_classification}`"
        ),
        (
            "- Prompt339 post-targeted-contract-fix route decision: "
            f"`{local_post_targeted_contract_fix_route_decision}`"
        ),
        (
            "- Prompt339 post-targeted-contract-fix next action: "
            f"`{local_post_targeted_contract_fix_next_action}`"
        ),
        (
            "- Prompt339 post-targeted-contract-fix approve ready: "
            f"`{str(local_post_targeted_contract_fix_approve_commit_tag_ready).lower()}`"
        ),
        (
            "- Prompt339 post-targeted-contract-fix changed tracked file count: "
            f"`{local_post_targeted_contract_fix_changed_tracked_file_count}`"
        ),
        (
            "- Prompt339 post-targeted-contract-fix unexpected tracked file count: "
            f"`{local_post_targeted_contract_fix_unexpected_tracked_file_count}`"
        ),
        f"- Prompt340 bounded approve status: `{local_bounded_approve_commit_tag_status}`",
        (
            "- Prompt340 bounded approve execution status: "
            f"`{local_bounded_approve_commit_tag_execution_status}`"
        ),
        (
            "- Prompt340 bounded approve blocked reason: "
            f"`{local_bounded_approve_commit_tag_blocked_reason}`"
        ),
        (
            "- Prompt340 bounded approve next action: "
            f"`{local_bounded_approve_commit_tag_next_action}`"
        ),
        (
            "- Prompt340 bounded approve commit performed: "
            f"`{str(local_bounded_approve_commit_tag_commit_performed).lower()}`"
        ),
        (
            "- Prompt340 bounded approve tag performed: "
            f"`{str(local_bounded_approve_commit_tag_tag_performed).lower()}`"
        ),
        (
            "- Prompt340 bounded approve commit hash: "
            f"`{local_bounded_approve_commit_tag_commit_hash or 'none'}`"
        ),
        (
            "- Prompt340 bounded approve tag name: "
            f"`{local_bounded_approve_commit_tag_tag_name}`"
        ),
        (
            "- Prompt340 bounded approve worktree clean: "
            f"`{str(local_bounded_approve_commit_tag_worktree_clean).lower()}`"
        ),
        (
            "- Prompt341 post-commit cycle closure status: "
            f"`{local_post_commit_cycle_closure_status}`"
        ),
        (
            "- Prompt341 post-commit cycle closure blocked reason: "
            f"`{local_post_commit_cycle_closure_blocked_reason}`"
        ),
        (
            "- Prompt341 post-commit cycle closure cycle closed: "
            f"`{str(local_post_commit_cycle_closure_cycle_closed).lower()}`"
        ),
        (
            "- Prompt341 post-commit cycle closure reentry allowed: "
            f"`{str(local_post_commit_cycle_closure_reentry_allowed).lower()}`"
        ),
        (
            "- Prompt341 post-commit cycle closure should continue: "
            f"`{str(local_post_commit_cycle_closure_should_continue).lower()}`"
        ),
        (
            "- Prompt341 post-commit cycle closure decision: "
            f"`{local_post_commit_cycle_closure_cycle_decision}`"
        ),
        (
            "- Prompt341 post-commit cycle closure next action: "
            f"`{local_post_commit_cycle_closure_next_action}`"
        ),
        (
            "- Prompt341 post-commit cycle closure commit hash: "
            f"`{local_post_commit_cycle_closure_commit_hash or 'none'}`"
        ),
        (
            "- Prompt341 post-commit cycle closure tag name: "
            f"`{local_post_commit_cycle_closure_tag_name}`"
        ),
        (
            "- Prompt341 next-cycle reentry status: "
            f"`{local_next_cycle_reentry_status}`"
        ),
        (
            "- Prompt341 next-cycle reentry next action: "
            f"`{local_next_cycle_reentry_next_action}`"
        ),
        (
            "- Prompt341 next-cycle reentry selected step: "
            f"`{local_next_cycle_reentry_selected_step_name or 'none'}`"
        ),
        (
            "- Prompt342 continuation status: "
            f"`{local_autonomous_continuation_status}`"
        ),
        (
            "- Prompt342 continuation blocked reason: "
            f"`{local_autonomous_continuation_blocked_reason}`"
        ),
        (
            "- Prompt342 continuation next action: "
            f"`{local_autonomous_continuation_next_action}`"
        ),
        (
            "- Prompt342 continuation reentry connected: "
            f"`{str(local_autonomous_continuation_reentry_connected).lower()}`"
        ),
        (
            "- Prompt342 continuation next cycle ready: "
            f"`{str(local_autonomous_continuation_next_cycle_ready).lower()}`"
        ),
        (
            "- Prompt342 continuation selected step: "
            f"`{local_autonomous_continuation_selected_step_name or 'none'}`"
        ),
        (
            "- Prompt342 loop completion status: "
            f"`{local_autonomous_loop_completion_status}`"
        ),
        (
            "- Prompt342 loop completion final decision: "
            f"`{local_autonomous_loop_completion_final_decision}`"
        ),
        (
            "- Prompt342 local-only complete loop ready: "
            f"`{str(local_only_complete_autonomous_loop_ready).lower()}`"
        ),
        (
            "- Prompt342 autonomous loop complete: "
            f"`{str(local_autonomous_loop_complete).lower()}`"
        ),
        f"- Diff capture status: `{diff_capture_status}`",
        f"- Diff capture blocked reason: `{diff_capture_blocked_reason}`",
        f"- Review request status: `{review_request_status}`",
        f"- Review request blocked reason: `{review_request_blocked_reason}`",
        f"- Review handoff decision status: `{review_handoff_decision_status}`",
        f"- Tracked diff status: `{tracked_diff_status}`",
        f"- No-diff review status: `{no_diff_review_status}`",
        f"- No-diff reason: `{no_diff_reason}`",
        f"- Review handoff decision source path: `{review_handoff_decision_source_path}`",
        f"- Review handoff decision next action: `{review_handoff_decision_next_action}`",
        f"- Review response status: `{review_response_status}`",
        f"- Review response decision: `{review_response_decision}`",
        f"- Review response reason: `{review_response_reason or 'none'}`",
        f"- Review response path: `{review_response_path}`",
        f"- Review response next action: `{review_response_next_action}`",
        f"- Targeted fix prompt status: `{targeted_fix_prompt_status}`",
        f"- Targeted fix prompt path: `{targeted_fix_prompt_resolved_path or 'none'}`",
        f"- Review route status: `{review_route_status}`",
        f"- Review route decision: `{review_route_decision}`",
        f"- Review route reason: `{review_route_reason}`",
        f"- Review route next action: `{review_route_next_action}`",
        f"- Review route blocked reason: `{review_route_blocked_reason}`",
        f"- Review route targeted-fix path: `{review_route_targeted_fix_prompt_path or 'none'}`",
        f"- Review route should prepare commit: `{str(review_route_should_prepare_commit).lower()}`",
        (
            "- Review route should prepare targeted fix: "
            f"`{str(review_route_should_prepare_targeted_fix).lower()}`"
        ),
        f"- Review route should prepare reject: `{str(review_route_should_prepare_reject).lower()}`",
        f"- Targeted-fix boundary status: `{targeted_fix_boundary_status}`",
        f"- Targeted-fix boundary decision: `{targeted_fix_boundary_decision}`",
        f"- Targeted-fix boundary reason: `{targeted_fix_boundary_reason}`",
        f"- Targeted-fix boundary next action: `{targeted_fix_boundary_next_action}`",
        f"- Targeted-fix boundary blocked reason: `{targeted_fix_boundary_blocked_reason}`",
        (
            "- Targeted-fix boundary source prompt path: "
            f"`{targeted_fix_boundary_source_prompt_path or 'none'}`"
        ),
        (
            "- Targeted-fix boundary codex prompt path: "
            f"`{targeted_fix_boundary_codex_prompt_path or 'none'}`"
        ),
        f"- Targeted-fix boundary prompt ready: `{str(targeted_fix_boundary_prompt_ready).lower()}`",
        (
            "- Targeted-fix boundary should execute codex: "
            f"`{str(targeted_fix_boundary_should_execute_codex).lower()}`"
        ),
        (
            "- Targeted-fix reentry execution enabled: "
            f"`{str(targeted_fix_reentry_execution_enabled).lower()}`"
        ),
        (
            "- Targeted-fix reentry execution confirmed: "
            f"`{str(targeted_fix_reentry_execution_confirmed).lower()}`"
        ),
        (
            "- Targeted-fix reentry execution gate status: "
            f"`{targeted_fix_reentry_execution_gate_status}`"
        ),
        f"- Targeted-fix reentry execution status: `{targeted_fix_reentry_execution_status}`",
        (
            "- Targeted-fix reentry execution attempted: "
            f"`{str(targeted_fix_reentry_execution_attempted).lower()}`"
        ),
        (
            "- Targeted-fix reentry execution exit code: "
            f"`{targeted_fix_reentry_execution_exit_code}`"
        ),
        (
            "- Targeted-fix reentry execution blocked reason: "
            f"`{targeted_fix_reentry_execution_blocked_reason}`"
        ),
        (
            "- Targeted-fix reentry execution prompt path: "
            f"`{targeted_fix_reentry_execution_prompt_path or 'none'}`"
        ),
        (
            "- Targeted-fix reentry execution receipt path: "
            f"`{targeted_fix_reentry_execution_receipt_path}`"
        ),
        (
            "- Targeted-fix reentry execution should execute codex: "
            f"`{str(targeted_fix_reentry_execution_should_execute_codex).lower()}`"
        ),
        (
            "- Targeted-fix post-reentry diff capture status: "
            f"`{targeted_fix_post_reentry_diff_capture_status}`"
        ),
        (
            "- Targeted-fix post-reentry diff capture attempted: "
            f"`{str(targeted_fix_post_reentry_diff_capture_attempted).lower()}`"
        ),
        (
            "- Targeted-fix post-reentry diff capture blocked reason: "
            f"`{targeted_fix_post_reentry_diff_capture_blocked_reason}`"
        ),
        (
            "- Targeted-fix post-reentry diff has diff: "
            f"`{str(targeted_fix_post_reentry_diff_has_diff).lower()}`"
        ),
        (
            "- Targeted-fix post-reentry changed file count: "
            f"`{targeted_fix_post_reentry_diff_changed_file_count}`"
        ),
        (
            "- Targeted-fix post-reentry review handoff status: "
            f"`{targeted_fix_post_reentry_review_handoff_status}`"
        ),
        (
            "- Targeted-fix post-reentry review required: "
            f"`{str(targeted_fix_post_reentry_review_required).lower()}`"
        ),
        (
            "- Targeted-fix post-reentry review assimilation status: "
            f"`{targeted_fix_post_reentry_review_assimilation_status}`"
        ),
        (
            "- Targeted-fix post-reentry review assimilation blocked reason: "
            f"`{targeted_fix_post_reentry_review_assimilation_blocked_reason}`"
        ),
        (
            "- Targeted-fix post-reentry review decision: "
            f"`{targeted_fix_post_reentry_review_decision}`"
        ),
        (
            "- Targeted-fix post-reentry route status: "
            f"`{targeted_fix_post_reentry_route_status}`"
        ),
        (
            "- Targeted-fix post-reentry route decision: "
            f"`{targeted_fix_post_reentry_route_decision}`"
        ),
        (
            "- Targeted-fix post-reentry next action: "
            f"`{targeted_fix_post_reentry_next_action}`"
        ),
        (
            "- Targeted-fix post-reentry manual review required: "
            f"`{str(targeted_fix_post_reentry_manual_review_required).lower()}`"
        ),
        (
            "- Targeted-fix post-reentry targeted-fix required: "
            f"`{str(targeted_fix_post_reentry_targeted_fix_required).lower()}`"
        ),
        (
            "- Targeted-fix post-reentry cycle closure status: "
            f"`{targeted_fix_post_reentry_cycle_closure_status}`"
        ),
        (
            "- Targeted-fix post-reentry terminal state: "
            f"`{targeted_fix_post_reentry_terminal_state}`"
        ),
        (
            "- Targeted-fix post-reentry cycle closed: "
            f"`{str(targeted_fix_post_reentry_cycle_closed).lower()}`"
        ),
        (
            "- Targeted-fix post-reentry safe to stop: "
            f"`{str(targeted_fix_post_reentry_safe_to_stop).lower()}`"
        ),
        (
            "- Targeted-fix post-reentry safe to commit prompt changes: "
            f"`{str(targeted_fix_post_reentry_safe_to_commit_prompt_changes).lower()}`"
        ),
        (
            "- Targeted-fix post-reentry requires codex reentry: "
            f"`{str(targeted_fix_post_reentry_requires_codex_reentry).lower()}`"
        ),
        (
            "- Targeted-fix post-reentry requires manual review: "
            f"`{str(targeted_fix_post_reentry_requires_manual_review).lower()}`"
        ),
        (
            "- Post-reentry codex reentry execution status: "
            f"`{targeted_fix_post_reentry_codex_reentry_execution_status}`"
        ),
        (
            "- Post-reentry codex reentry gate status: "
            f"`{targeted_fix_post_reentry_codex_reentry_gate_status}`"
        ),
        (
            "- Post-reentry codex reentry blocked reason: "
            f"`{targeted_fix_post_reentry_codex_reentry_blocked_reason}`"
        ),
        (
            "- Post-reentry codex reentry attempted: "
            f"`{str(targeted_fix_post_reentry_codex_reentry_attempted).lower()}`"
        ),
        (
            "- Post-reentry codex reentry executed: "
            f"`{str(targeted_fix_post_reentry_codex_reentry_executed).lower()}`"
        ),
        (
            "- Post-reentry codex reentry exit code: "
            f"`{targeted_fix_post_reentry_codex_reentry_exit_code}`"
        ),
        (
            "- Post-reentry codex reentry next action: "
            f"`{targeted_fix_post_reentry_codex_reentry_next_action}`"
        ),
        f"- Approve boundary status: `{approve_commit_tag_boundary_status}`",
        f"- Approve boundary decision: `{approve_commit_tag_boundary_decision}`",
        f"- Approve boundary reason: `{approve_commit_tag_boundary_reason}`",
        f"- Approve boundary next action: `{approve_commit_tag_boundary_next_action}`",
        f"- Approve boundary blocked reason: `{approve_commit_tag_boundary_blocked_reason}`",
        f"- Approve boundary commit message: `{approve_commit_tag_boundary_commit_message or 'none'}`",
        f"- Approve boundary tag name: `{approve_commit_tag_boundary_tag_name or 'none'}`",
        (
            "- Approve boundary commands path: "
            f"`{approve_commit_tag_boundary_commands_resolved_path or 'none'}`"
        ),
        (
            "- Approve boundary metadata path: "
            f"`{approve_commit_tag_boundary_metadata_resolved_path or 'none'}`"
        ),
        (
            "- Approve boundary should execute commit: "
            f"`{str(approve_commit_tag_boundary_should_execute_commit).lower()}`"
        ),
        (
            "- Approve boundary should execute tag: "
            f"`{str(approve_commit_tag_boundary_should_execute_tag).lower()}`"
        ),
        f"- Approve boundary ready: `{str(approve_commit_tag_boundary_ready).lower()}`",
        f"- Approve plan ready: `{str(approve_commit_tag_plan_ready).lower()}`",
        (
            "- Approve tracked files allowed: "
            f"`{str(approve_commit_tag_tracked_files_allowed).lower()}`"
        ),
        (
            "- Approve changed tracked files: "
            f"`{', '.join(approve_commit_tag_changed_tracked_files) if approve_commit_tag_changed_tracked_files else 'none'}`"
        ),
        (
            "- Approve unexpected tracked files: "
            f"`{', '.join(approve_commit_tag_unexpected_tracked_files) if approve_commit_tag_unexpected_tracked_files else 'none'}`"
        ),
        (
            "- Approve explicit add paths: "
            f"`{', '.join(approve_commit_tag_explicit_add_paths) if approve_commit_tag_explicit_add_paths else 'none'}`"
        ),
        (
            "- Approve command file path: "
            f"`{approve_commit_tag_command_file_path or 'none'}`"
        ),
        (
            "- Approve execution allowed: "
            f"`{str(approve_commit_tag_execution_allowed).lower()}`"
        ),
        (
            "- Approve execution enabled: "
            f"`{str(approve_commit_tag_execution_enabled).lower()}`"
        ),
        (
            "- Approve execution confirmed: "
            f"`{str(approve_commit_tag_execution_confirmed).lower()}`"
        ),
        f"- Approve execution gate status: `{approve_commit_tag_execution_gate_status}`",
        f"- Approve execution status: `{approve_commit_tag_execution_status}`",
        (
            "- Approve execution attempted: "
            f"`{str(approve_commit_tag_execution_attempted).lower()}`"
        ),
        f"- Approve execution exit code: `{approve_commit_tag_execution_exit_code}`",
        (
            "- Approve execution blocked reason: "
            f"`{approve_commit_tag_execution_blocked_reason}`"
        ),
        (
            "- Approve execution commit message: "
            f"`{approve_commit_tag_execution_commit_message or 'none'}`"
        ),
        (
            "- Approve execution tag name: "
            f"`{approve_commit_tag_execution_tag_name or 'none'}`"
        ),
        (
            "- Approve execution should commit: "
            f"`{str(approve_commit_tag_execution_should_commit).lower()}`"
        ),
        (
            "- Approve execution should tag: "
            f"`{str(approve_commit_tag_execution_should_tag).lower()}`"
        ),
        (
            "- Approve execution receipt path: "
            f"`{approve_commit_tag_execution_receipt_path}`"
        ),
        (
            "- Approve artifact reconciliation status: "
            f"`{approve_commit_tag_artifact_reconciliation_status}`"
        ),
        (
            "- Approve artifact reconciliation blocked reason: "
            f"`{approve_commit_tag_artifact_reconciliation_blocked_reason}`"
        ),
        (
            "- Approve artifact reconciliation stale artifacts detected: "
            f"`{str(approve_commit_tag_artifact_reconciliation_stale_artifacts_detected).lower()}`"
        ),
        (
            "- Approve artifact reconciliation already committed: "
            f"`{str(approve_commit_tag_artifact_reconciliation_already_committed).lower()}`"
        ),
        (
            "- Approve artifact reconciliation already tagged: "
            f"`{str(approve_commit_tag_artifact_reconciliation_already_tagged).lower()}`"
        ),
        (
            "- Approve artifact reconciliation next action: "
            f"`{approve_commit_tag_artifact_reconciliation_next_action}`"
        ),
        (
            "- Approve artifact reconciliation receipt path: "
            f"`{approve_commit_tag_artifact_reconciliation_receipt_path}`"
        ),
        f"- Remote readiness boundary status: `{remote_readiness_boundary_status}`",
        f"- Remote readiness blocked reason: `{remote_readiness_blocked_reason}`",
        (
            "- Remote readiness remote ready: "
            f"`{str(remote_readiness_remote_ready).lower()}`"
        ),
        (
            "- Remote readiness push ready: "
            f"`{str(remote_readiness_push_ready).lower()}`"
        ),
        f"- Remote readiness PR ready: `{str(remote_readiness_pr_ready).lower()}`",
        (
            "- Remote readiness merge ready: "
            f"`{str(remote_readiness_merge_ready).lower()}`"
        ),
        (
            "- Remote readiness worktree clean: "
            f"`{str(remote_readiness_worktree_clean).lower()}`"
        ),
        (
            "- Remote readiness expected head tag present: "
            f"`{str(remote_readiness_expected_head_tag_present).lower()}`"
        ),
        (
            "- Remote readiness remote configured: "
            f"`{str(remote_readiness_remote_configured).lower()}`"
        ),
        (
            "- Remote readiness upstream configured: "
            f"`{str(remote_readiness_upstream_configured).lower()}`"
        ),
        f"- Remote readiness next action: `{remote_readiness_next_action}`",
        f"- Remote readiness boundary path: `{remote_readiness_boundary_path}`",
        f"- Remote readiness plan path: `{remote_readiness_plan_path}`",
        f"- Local end-to-end readiness status: `{local_end_to_end_readiness_status}`",
        (
            "- Local end-to-end readiness blocked reason: "
            f"`{local_end_to_end_readiness_blocked_reason}`"
        ),
        f"- Local end-to-end ready: `{str(local_end_to_end_ready).lower()}`",
        f"- Local components ready: `{str(local_components_ready).lower()}`",
        (
            "- Integrated local runner ready: "
            f"`{str(integrated_local_runner_ready).lower()}`"
        ),
        (
            "- Implementation prompt generation status: "
            f"`{implementation_prompt_generation_status}`"
        ),
        f"- GitHub deferred: `{str(github_deferred).lower()}`",
        f"- Remote required: `{str(remote_required).lower()}`",
        f"- Local end-to-end next action: `{local_end_to_end_next_action}`",
        (
            "- Local end-to-end component matrix path: "
            f"`{local_end_to_end_component_matrix_surface_path}`"
        ),
        (
            "- Local end-to-end readiness boundary path: "
            f"`{local_end_to_end_readiness_boundary_surface_path}`"
        ),
        (
            "- Local end-to-end gap report path: "
            f"`{local_end_to_end_gap_report_surface_path}`"
        ),
        (
            "- Local Codex one-shot handoff status: "
            f"`{local_codex_one_shot_handoff_status}`"
        ),
        (
            "- Local Codex one-shot handoff handoff status: "
            f"`{local_codex_one_shot_handoff_handoff_status}`"
        ),
        (
            "- Local Codex one-shot handoff next action: "
            f"`{local_codex_one_shot_handoff_next_action}`"
        ),
        (
            "- Local Codex one-shot handoff blocked reason: "
            f"`{local_codex_one_shot_handoff_blocked_reason}`"
        ),
        (
            "- Local Codex one-shot handoff readiness reason: "
            f"`{local_codex_one_shot_handoff_readiness_reason}`"
        ),
        (
            "- Local Codex one-shot handoff prompt ready: "
            f"`{str(local_codex_one_shot_handoff_prompt_ready).lower()}`"
        ),
        (
            "- Local Codex one-shot handoff command ready: "
            f"`{str(local_codex_one_shot_handoff_command_ready).lower()}`"
        ),
        (
            "- Local Codex one-shot handoff codex invocation allowed: "
            f"`{str(local_codex_one_shot_handoff_codex_invocation_allowed).lower()}`"
        ),
        (
            "- Local Codex one-shot handoff execution allowed: "
            f"`{str(local_codex_one_shot_handoff_execution_allowed).lower()}`"
        ),
        (
            "- Local Codex one-shot handoff max codex invocations: "
            f"`{local_codex_one_shot_handoff_max_codex_invocations}`"
        ),
        (
            "- Local Codex one-shot handoff codex invocation count: "
            f"`{local_codex_one_shot_handoff_codex_invocation_count}`"
        ),
        (
            "- Local Codex one-shot handoff selected step id: "
            f"`{local_codex_one_shot_handoff_selected_step_id}`"
        ),
        (
            "- Local Codex one-shot handoff selected step name: "
            f"`{local_codex_one_shot_handoff_selected_step_name or 'none'}`"
        ),
        (
            "- Local Codex one-shot handoff selected step operation: "
            f"`{local_codex_one_shot_handoff_selected_step_operation or 'none'}`"
        ),
        (
            "- Local Codex one-shot handoff prompt path: "
            f"`{local_codex_one_shot_handoff_prompt_path or 'none'}`"
        ),
        (
            "- Local Codex one-shot handoff command display: "
            f"`{local_codex_one_shot_handoff_command_display or 'none'}`"
        ),
        (
            "- Local Codex one-shot handoff run id: "
            f"`{local_codex_one_shot_handoff_run_id}`"
        ),
        (
            "- Local Codex one-shot handoff cycle id: "
            f"`{local_codex_one_shot_handoff_cycle_id}`"
        ),
        (
            "- Local Codex one-shot handoff current cycle: "
            f"`{local_codex_one_shot_handoff_current_cycle}`"
        ),
        (
            "- Local Codex one-shot handoff max cycles: "
            f"`{local_codex_one_shot_handoff_max_cycles}`"
        ),
        (
            "- Local Codex one-shot execution status: "
            f"`{local_codex_one_shot_execution_status}`"
        ),
        (
            "- Local Codex one-shot execution execution status: "
            f"`{local_codex_one_shot_execution_execution_status}`"
        ),
        (
            "- Local Codex one-shot execution next action: "
            f"`{local_codex_one_shot_execution_next_action}`"
        ),
        (
            "- Local Codex one-shot execution blocked reason: "
            f"`{local_codex_one_shot_execution_blocked_reason}`"
        ),
        (
            "- Local Codex one-shot execution readiness reason: "
            f"`{local_codex_one_shot_execution_readiness_reason}`"
        ),
        (
            "- Local Codex one-shot execution codex invoked: "
            f"`{str(local_codex_one_shot_execution_codex_invoked).lower()}`"
        ),
        (
            "- Local Codex one-shot execution codex invocation allowed: "
            f"`{str(local_codex_one_shot_execution_codex_invocation_allowed).lower()}`"
        ),
        (
            "- Local Codex one-shot execution execution allowed: "
            f"`{str(local_codex_one_shot_execution_execution_allowed).lower()}`"
        ),
        (
            "- Local Codex one-shot execution attempted: "
            f"`{str(local_codex_one_shot_execution_execution_attempted).lower()}`"
        ),
        (
            "- Local Codex one-shot execution completed: "
            f"`{str(local_codex_one_shot_execution_execution_completed).lower()}`"
        ),
        (
            "- Local Codex one-shot execution exit code: "
            f"`{local_codex_one_shot_execution_execution_exit_code}`"
        ),
        (
            "- Local Codex one-shot execution max codex invocations: "
            f"`{local_codex_one_shot_execution_max_codex_invocations}`"
        ),
        (
            "- Local Codex one-shot execution codex invocation count: "
            f"`{local_codex_one_shot_execution_codex_invocation_count}`"
        ),
        (
            "- Local Codex one-shot execution selected step id: "
            f"`{local_codex_one_shot_execution_selected_step_id}`"
        ),
        (
            "- Local Codex one-shot execution selected step name: "
            f"`{local_codex_one_shot_execution_selected_step_name or 'none'}`"
        ),
        (
            "- Local Codex one-shot execution selected step operation: "
            f"`{local_codex_one_shot_execution_selected_step_operation or 'none'}`"
        ),
        (
            "- Local Codex one-shot execution prompt path: "
            f"`{local_codex_one_shot_execution_prompt_path or 'none'}`"
        ),
        (
            "- Local Codex one-shot execution stdout path: "
            f"`{local_codex_one_shot_execution_stdout_path_text or 'none'}`"
        ),
        (
            "- Local Codex one-shot execution stderr path: "
            f"`{local_codex_one_shot_execution_stderr_path_text or 'none'}`"
        ),
        (
            "- Local Codex one-shot execution result path: "
            f"`{local_codex_one_shot_execution_result_path_text or 'none'}`"
        ),
        (
            "- Local Codex one-shot execution run id: "
            f"`{local_codex_one_shot_execution_run_id}`"
        ),
        (
            "- Local Codex one-shot execution cycle id: "
            f"`{local_codex_one_shot_execution_cycle_id}`"
        ),
        (
            "- Local Codex one-shot execution current cycle: "
            f"`{local_codex_one_shot_execution_current_cycle}`"
        ),
        (
            "- Local Codex one-shot execution max cycles: "
            f"`{local_codex_one_shot_execution_max_cycles}`"
        ),
        f"- Completed result source path: `{completed_result_source_path}`",
        f"- Completed result source status: `{completed_result_source_status}`",
        f"- Stop reason: `{stop_reason}`",
        f"- Enabled: `{str(enabled).lower()}`",
        f"- Execute enabled: `{str(execute_enabled).lower()}`",
        f"- Exec plan path: `{exec_plan_path}`",
        f"- Exec plan safety status: `{exec_plan_safety_status}`",
        f"- Exec plan blocked reason: `{exec_plan_blocked_reason}`",
        (
            "- Exec plan required fragments present: "
            f"`{', '.join(exec_plan_required_fragments_present) if exec_plan_required_fragments_present else 'none'}`"
        ),
        (
            "- Exec plan banned fragments present: "
            f"`{', '.join(exec_plan_banned_fragments_present) if exec_plan_banned_fragments_present else 'none'}`"
        ),
        f"- Exec plan execution status: `{exec_plan_execution_status}`",
        f"- Execution attempted: `{str(execution_attempted).lower()}`",
        f"- Execution blocked reason: `{execution_blocked_reason}`",
        f"- Execution gate status: `{execution_gate_status}`",
        f"- Execution exit code: `{execution_exit_code}`",
        f"- Execution started at: `{execution_started_at or 'none'}`",
        f"- Execution finished at: `{execution_finished_at or 'none'}`",
        "",
        "## Output Artifacts",
        f"- one_cycle_controller_result.json: `{output_json_path}`",
        f"- one_cycle_controller_summary.md: `{output_summary_path}`",
        f"- local_codex_exec_plan.sh: `{exec_plan_path}`",
        f"- one_cycle_controller_exec_stdout.log: `{execution_stdout_path}`",
        f"- one_cycle_controller_exec_stderr.log: `{execution_stderr_path}`",
        f"- one_cycle_controller_runlog.md: `{execution_runlog_path}`",
        f"- one_cycle_controller_diff_stat.txt: `{diff_stat_path}`",
        f"- one_cycle_controller_diff_name_status.txt: `{diff_name_status_path}`",
        f"- one_cycle_controller_diff.patch: `{diff_patch_path}`",
        f"- one_cycle_controller_review_request.md: `{review_request_path}`",
        f"- one_cycle_controller_review_handoff.json: `{review_handoff_path}`",
        f"- review_response.json: `{review_response_path}`",
        f"- targeted_fix_prompt.md: `{targeted_fix_prompt_path}`",
        f"- targeted_fix_codex_prompt.md: `{targeted_fix_codex_prompt_path}`",
        (
            "- targeted_fix_reentry_execution_receipt.json: "
            f"`{targeted_fix_reentry_execution_receipt_path}`"
        ),
        (
            "- targeted_fix_post_reentry_diff_capture.json: "
            f"`{targeted_fix_post_reentry_diff_capture_path}`"
        ),
        (
            "- targeted_fix_post_reentry_diff.patch: "
            f"`{targeted_fix_post_reentry_diff_patch_path}`"
        ),
        (
            "- targeted_fix_post_reentry_diff_stat.txt: "
            f"`{targeted_fix_post_reentry_diff_stat_path}`"
        ),
        (
            "- targeted_fix_post_reentry_diff_name_status.txt: "
            f"`{targeted_fix_post_reentry_diff_name_status_path}`"
        ),
        (
            "- targeted_fix_post_reentry_review_handoff.json: "
            f"`{targeted_fix_post_reentry_review_handoff_path}`"
        ),
        (
            "- targeted_fix_post_reentry_review_response.json: "
            f"`{targeted_fix_post_reentry_review_response_path}`"
        ),
        (
            "- targeted_fix_post_reentry_review_assimilation.json: "
            f"`{targeted_fix_post_reentry_review_assimilation_path}`"
        ),
        (
            "- targeted_fix_post_reentry_route_decision.json: "
            f"`{targeted_fix_post_reentry_route_decision_path}`"
        ),
        (
            "- targeted_fix_post_reentry_cycle_closure_result.json: "
            f"`{targeted_fix_post_reentry_cycle_closure_result_path}`"
        ),
        (
            "- targeted_fix_post_reentry_terminal_summary.json: "
            f"`{targeted_fix_post_reentry_terminal_summary_path}`"
        ),
        (
            "- targeted_fix_post_reentry_prompt_emission.json: "
            f"`{targeted_fix_post_reentry_prompt_emission_path}`"
        ),
        (
            "- targeted_fix_post_reentry_prompt_emission_receipt.json: "
            f"`{targeted_fix_post_reentry_prompt_emission_receipt_path}`"
        ),
        (
            "- targeted_fix_post_reentry_codex_reentry_execution_receipt.json: "
            f"`{targeted_fix_post_reentry_codex_reentry_execution_receipt_path}`"
        ),
        (
            "- targeted_fix_post_reentry_codex_reentry_execution_stdout.txt: "
            f"`{targeted_fix_post_reentry_codex_reentry_execution_stdout_path}`"
        ),
        (
            "- targeted_fix_post_reentry_codex_reentry_execution_stderr.txt: "
            f"`{targeted_fix_post_reentry_codex_reentry_execution_stderr_path}`"
        ),
        (
            "- targeted_fix_post_reentry_bounded_cycle_state.json: "
            f"`{targeted_fix_post_reentry_bounded_cycle_state_path}`"
        ),
        (
            "- targeted_fix_post_reentry_bounded_cycle_decision.json: "
            f"`{targeted_fix_post_reentry_bounded_cycle_decision_path}`"
        ),
        (
            "- targeted_fix_post_reentry_bounded_cycle_receipt.json: "
            f"`{targeted_fix_post_reentry_bounded_cycle_receipt_path}`"
        ),
        (
            "- local_codex_one_shot_prompt.md: "
            f"`{local_codex_one_shot_prompt_path}`"
        ),
        (
            "- local_codex_one_shot_execution_handoff.json: "
            f"`{local_codex_one_shot_execution_handoff_path}`"
        ),
        (
            "- local_codex_one_shot_execution_receipt.json: "
            f"`{local_codex_one_shot_execution_receipt_path}`"
        ),
        (
            "- local_codex_one_shot_execution_result.json: "
            f"`{local_codex_one_shot_execution_result_path}`"
        ),
        (
            "- local_codex_one_shot_execution_receipt_v2.json: "
            f"`{local_codex_one_shot_execution_receipt_v2_path}`"
        ),
        (
            "- local_codex_one_shot_execution_stdout.txt: "
            f"`{local_codex_one_shot_execution_stdout_path}`"
        ),
        (
            "- local_codex_one_shot_execution_stderr.txt: "
            f"`{local_codex_one_shot_execution_stderr_path}`"
        ),
        f"- approve_commit_tag_boundary.json: `{approve_commit_tag_boundary_metadata_path}`",
        f"- approve_commit_tag_plan.json: `{approve_commit_tag_plan_metadata_path}`",
        (
            "- approve_commit_tag_artifact_reconciliation_receipt.json: "
            f"`{approve_commit_tag_artifact_reconciliation_receipt_path}`"
        ),
        f"- approve_commit_tag_commands.sh: `{approve_commit_tag_boundary_commands_path}`",
        f"- approve_commit_tag_execution_receipt.json: `{approve_commit_tag_execution_receipt_path}`",
        f"- remote_readiness_boundary.json: `{remote_readiness_boundary_metadata_path}`",
        f"- remote_readiness_plan.json: `{remote_readiness_plan_metadata_path}`",
        (
            "- local_end_to_end_controller_component_matrix.json: "
            f"`{local_end_to_end_controller_component_matrix_path}`"
        ),
        (
            "- local_end_to_end_controller_readiness_boundary.json: "
            f"`{local_end_to_end_controller_readiness_boundary_path}`"
        ),
        (
            "- local_end_to_end_controller_gap_report.json: "
            f"`{local_end_to_end_controller_gap_report_path}`"
        ),
    ]

    try:
        one_cycle_controller_dir.mkdir(parents=True, exist_ok=True)
        output_json_path.write_text(
            json.dumps(result_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        output_summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    except OSError:
        status = "one_cycle_controller_ready"
        next_action = "enable_one_cycle_controller_execution"
        cycle_count = 0
        max_cycles = 1
        codex_execution_status = "not_executed"
        diff_capture_status = "not_started"
        diff_capture_blocked_reason = "one_cycle_not_completed"
        review_request_status = "not_started"
        review_request_blocked_reason = "one_cycle_not_completed"
        review_handoff_decision_status = "manual_review_required"
        tracked_diff_status = "unknown"
        no_diff_review_status = "blocked"
        no_diff_reason = "review_handoff_missing_or_invalid"
        review_handoff_decision_source_path = str(review_handoff_path)
        review_handoff_decision_next_action = "manual_review_required"
        review_response_status = "missing"
        review_response_decision = "none"
        review_response_reason = ""
        review_response_next_action = "wait_for_chatgpt_diff_review_response"
        targeted_fix_prompt_status = "not_applicable"
        targeted_fix_prompt_text = ""
        targeted_fix_prompt_resolved_path = ""
        review_route_status = "waiting_for_review_response"
        review_route_decision = "none"
        review_route_reason = "review_response_missing"
        review_route_next_action = "wait_for_chatgpt_diff_review_response"
        review_route_blocked_reason = "review_response_missing"
        review_route_source = ""
        review_route_targeted_fix_prompt_path = ""
        review_route_should_prepare_commit = False
        review_route_should_prepare_targeted_fix = False
        review_route_should_prepare_reject = False
        targeted_fix_boundary_status = "not_applicable"
        targeted_fix_boundary_decision = "none"
        targeted_fix_boundary_reason = "route_not_targeted_fix"
        targeted_fix_boundary_next_action = "none"
        targeted_fix_boundary_blocked_reason = "route_not_targeted_fix"
        targeted_fix_boundary_source_prompt_path = ""
        targeted_fix_boundary_codex_prompt_path = ""
        targeted_fix_boundary_prompt_ready = False
        targeted_fix_boundary_should_execute_codex = False
        targeted_fix_reentry_execution_enabled = bool(
            targeted_fix_reentry_execution_enabled
        )
        targeted_fix_reentry_execution_confirmed = bool(
            targeted_fix_reentry_execution_confirmed
        )
        if review_route_decision != "targeted_fix":
            targeted_fix_reentry_execution_gate_status = "not_applicable"
            targeted_fix_reentry_execution_status = "not_executed"
            targeted_fix_reentry_execution_attempted = False
            targeted_fix_reentry_execution_exit_code = 0
            targeted_fix_reentry_execution_blocked_reason = "route_not_targeted_fix"
            targeted_fix_reentry_execution_should_execute_codex = False
        elif not (
            targeted_fix_reentry_execution_enabled and targeted_fix_reentry_execution_confirmed
        ):
            targeted_fix_reentry_execution_gate_status = "execution_not_enabled"
            targeted_fix_reentry_execution_status = "not_executed"
            targeted_fix_reentry_execution_attempted = False
            targeted_fix_reentry_execution_exit_code = 0
            targeted_fix_reentry_execution_blocked_reason = "execution_not_enabled"
            targeted_fix_reentry_execution_should_execute_codex = False
        elif dry_run:
            targeted_fix_reentry_execution_gate_status = "dry_run_suppressed"
            targeted_fix_reentry_execution_status = "dry_run_suppressed"
            targeted_fix_reentry_execution_attempted = False
            targeted_fix_reentry_execution_exit_code = 0
            targeted_fix_reentry_execution_blocked_reason = "dry_run_execution_suppressed"
            targeted_fix_reentry_execution_should_execute_codex = False
        else:
            targeted_fix_reentry_execution_gate_status = "blocked"
            targeted_fix_reentry_execution_status = "blocked"
            targeted_fix_reentry_execution_attempted = False
            targeted_fix_reentry_execution_exit_code = 0
            targeted_fix_reentry_execution_blocked_reason = (
                "targeted_fix_prompt_execution_adapter_missing"
            )
            targeted_fix_reentry_execution_should_execute_codex = False
        targeted_fix_reentry_execution_prompt_path = str(targeted_fix_codex_prompt_path)
        targeted_fix_post_reentry_diff_capture_status = "not_applicable"
        targeted_fix_post_reentry_diff_capture_attempted = False
        targeted_fix_post_reentry_diff_capture_blocked_reason = "reentry_not_completed"
        targeted_fix_post_reentry_diff_has_diff = False
        targeted_fix_post_reentry_diff_changed_file_count = 0
        targeted_fix_post_reentry_review_handoff_status = "not_applicable"
        targeted_fix_post_reentry_review_required = False
        targeted_fix_post_reentry_review_assimilation_status = "not_applicable"
        targeted_fix_post_reentry_review_assimilation_blocked_reason = (
            "review_handoff_not_ready"
        )
        targeted_fix_post_reentry_review_decision = "none"
        targeted_fix_post_reentry_route_status = "blocked"
        targeted_fix_post_reentry_route_decision = "manual_review_required"
        targeted_fix_post_reentry_next_action = "manual_review_required"
        targeted_fix_post_reentry_manual_review_required = True
        targeted_fix_post_reentry_targeted_fix_required = False
        targeted_fix_post_reentry_route_executor_boundary_status = "blocked"
        targeted_fix_post_reentry_route_executor_kind = "manual_review"
        targeted_fix_post_reentry_route_executor_next_action = "manual_review_required"
        targeted_fix_post_reentry_route_executor_execution_allowed = False
        targeted_fix_post_reentry_route_executor_manual_review_required = True
        targeted_fix_post_reentry_cycle_closure_allowed = False
        targeted_fix_post_reentry_approval_boundary_allowed = False
        targeted_fix_post_reentry_reject_boundary_allowed = False
        targeted_fix_post_reentry_targeted_fix_prompt_emission_allowed = False
        targeted_fix_post_reentry_codex_reentry_allowed = False
        targeted_fix_post_reentry_next_step_handoff_status = "blocked"
        targeted_fix_post_reentry_cycle_closure_status = "blocked"
        targeted_fix_post_reentry_terminal_state = "blocked"
        targeted_fix_post_reentry_cycle_closed = False
        targeted_fix_post_reentry_safe_to_stop = False
        targeted_fix_post_reentry_safe_to_commit_prompt_changes = False
        targeted_fix_post_reentry_requires_codex_reentry = False
        targeted_fix_post_reentry_requires_manual_review = True
        targeted_fix_post_reentry_prompt_emission_status = "not_applicable"
        targeted_fix_post_reentry_prompt_emission_blocked_reason = "route_not_targeted_fix"
        targeted_fix_post_reentry_prompt_written = False
        targeted_fix_post_reentry_prompt_ready_for_codex_reentry = False
        targeted_fix_post_reentry_prompt_emission_next_action = "none"
        targeted_fix_post_reentry_emitted_prompt_path = str(targeted_fix_codex_prompt_path)
        targeted_fix_post_reentry_codex_reentry_execution_status = "not_applicable"
        targeted_fix_post_reentry_codex_reentry_gate_status = "not_applicable"
        targeted_fix_post_reentry_codex_reentry_blocked_reason = "prompt_emission_not_ready"
        targeted_fix_post_reentry_codex_reentry_attempted = False
        targeted_fix_post_reentry_codex_reentry_executed = False
        targeted_fix_post_reentry_codex_reentry_exit_code = None
        targeted_fix_post_reentry_codex_reentry_next_action = "none"
        targeted_fix_post_reentry_bounded_cycle_status = "blocked"
        targeted_fix_post_reentry_bounded_cycle_decision = "blocked"
        targeted_fix_post_reentry_bounded_cycle_blocked_reason = (
            "post_reentry_bounded_cycle_inputs_incomplete"
        )
        targeted_fix_post_reentry_bounded_cycle_complete = False
        targeted_fix_post_reentry_bounded_cycle_should_continue = False
        targeted_fix_post_reentry_bounded_cycle_should_emit_prompt = False
        targeted_fix_post_reentry_bounded_cycle_should_execute_codex = False
        targeted_fix_post_reentry_bounded_cycle_should_capture_diff = False
        targeted_fix_post_reentry_bounded_cycle_next_action = "manual_review_required"
        approve_commit_tag_boundary_status = "not_applicable"
        approve_commit_tag_boundary_decision = "none"
        approve_commit_tag_boundary_reason = "route_not_approve"
        approve_commit_tag_boundary_next_action = "none"
        approve_commit_tag_boundary_blocked_reason = "route_not_approve"
        approve_commit_tag_boundary_commit_message = ""
        approve_commit_tag_boundary_tag_name = ""
        approve_commit_tag_boundary_commands_resolved_path = ""
        approve_commit_tag_boundary_metadata_resolved_path = ""
        approve_commit_tag_boundary_should_execute_commit = False
        approve_commit_tag_boundary_should_execute_tag = False
        approve_commit_tag_boundary_ready = False
        approve_commit_tag_execution_enabled = bool(approve_commit_tag_execution_enabled)
        approve_commit_tag_execution_confirmed = bool(approve_commit_tag_execution_confirmed)
        if not (
            approve_commit_tag_execution_enabled and approve_commit_tag_execution_confirmed
        ):
            approve_commit_tag_execution_gate_status = "execution_not_enabled"
            approve_commit_tag_execution_status = "not_executed"
            approve_commit_tag_execution_attempted = False
            approve_commit_tag_execution_exit_code = 0
            approve_commit_tag_execution_blocked_reason = "execution_not_enabled"
            approve_commit_tag_execution_should_commit = False
            approve_commit_tag_execution_should_tag = False
        elif dry_run:
            approve_commit_tag_execution_gate_status = "dry_run_suppressed"
            approve_commit_tag_execution_status = "dry_run_suppressed"
            approve_commit_tag_execution_attempted = False
            approve_commit_tag_execution_exit_code = 0
            approve_commit_tag_execution_blocked_reason = "dry_run_execution_suppressed"
            approve_commit_tag_execution_should_commit = False
            approve_commit_tag_execution_should_tag = False
        else:
            approve_commit_tag_execution_gate_status = "boundary_not_ready"
            approve_commit_tag_execution_status = "blocked"
            approve_commit_tag_execution_attempted = False
            approve_commit_tag_execution_exit_code = 0
            approve_commit_tag_execution_blocked_reason = "route_not_approve"
            approve_commit_tag_execution_should_commit = False
            approve_commit_tag_execution_should_tag = False
        approve_commit_tag_execution_commit_message = ""
        approve_commit_tag_execution_tag_name = ""
        approve_commit_tag_artifact_reconciliation_status = "blocked"
        approve_commit_tag_artifact_reconciliation_blocked_reason = "result_write_failed"
        approve_commit_tag_artifact_reconciliation_stale_artifacts_detected = False
        approve_commit_tag_artifact_reconciliation_already_committed = False
        approve_commit_tag_artifact_reconciliation_already_tagged = False
        approve_commit_tag_artifact_reconciliation_next_action = "manual_review_required"
        approve_commit_tag_artifact_reconciliation_receipt_path = str(
            approve_commit_tag_artifact_reconciliation_receipt_file_path
        )
        remote_readiness_boundary_status = "blocked"
        remote_readiness_blocked_reason = "result_write_failed"
        remote_readiness_remote_ready = False
        remote_readiness_push_ready = False
        remote_readiness_pr_ready = False
        remote_readiness_merge_ready = False
        remote_readiness_worktree_clean = False
        remote_readiness_expected_head_tag_present = False
        remote_readiness_remote_configured = False
        remote_readiness_upstream_configured = False
        remote_readiness_next_action = "manual_review_required"
        remote_readiness_boundary_path = str(remote_readiness_boundary_metadata_path)
        remote_readiness_plan_path = str(remote_readiness_plan_metadata_path)
        completed_result_source_status = "not_completed"
        stop_reason = (
            "dry_run_execution_suppressed"
            if enabled and execute_enabled and dry_run
            else ("none" if enabled and execute_enabled and not dry_run else "execution_not_enabled")
        )
        enabled = bool(enabled)
        execute_enabled = bool(execute_enabled)
        exec_plan_execution_status = "not_executed"
        execution_attempted = False
        execution_exit_code = -1
        execution_started_at = ""
        execution_finished_at = ""
        execution_blocked_reason = (
            "dry_run_execution_suppressed"
            if enabled and execute_enabled and dry_run
            else ("none" if enabled and execute_enabled and not dry_run else "execution_not_enabled")
        )
        execution_gate_status = (
            "dry_run_suppressed"
            if enabled and execute_enabled and dry_run
            else (
                "ready_for_single_execution"
                if enabled and execute_enabled and not dry_run
                else "execution_not_enabled"
            )
        )

    return {
        "project_browser_autonomous_one_cycle_controller_status": status,
        "project_browser_autonomous_one_cycle_controller_next_action": next_action,
        "project_browser_autonomous_one_cycle_controller_cycle_count": cycle_count,
        "project_browser_autonomous_one_cycle_controller_max_cycles": max_cycles,
        "project_browser_autonomous_one_cycle_controller_codex_execution_status": (
            codex_execution_status
        ),
        "project_browser_autonomous_one_cycle_controller_diff_capture_status": (
            diff_capture_status
        ),
        "project_browser_autonomous_one_cycle_controller_diff_capture_blocked_reason": (
            diff_capture_blocked_reason
        ),
        "project_browser_autonomous_one_cycle_controller_diff_stat_path": str(diff_stat_path),
        "project_browser_autonomous_one_cycle_controller_diff_name_status_path": str(
            diff_name_status_path
        ),
        "project_browser_autonomous_one_cycle_controller_diff_patch_path": str(diff_patch_path),
        "project_browser_autonomous_one_cycle_controller_review_request_status": (
            review_request_status
        ),
        "project_browser_autonomous_one_cycle_controller_review_request_blocked_reason": (
            review_request_blocked_reason
        ),
        "project_browser_autonomous_one_cycle_controller_review_request_path": str(
            review_request_path
        ),
        "project_browser_autonomous_one_cycle_controller_review_handoff_path": str(
            review_handoff_path
        ),
        "project_browser_autonomous_one_cycle_controller_review_handoff_decision_status": (
            review_handoff_decision_status
        ),
        "project_browser_autonomous_one_cycle_controller_tracked_diff_status": (
            tracked_diff_status
        ),
        "project_browser_autonomous_one_cycle_controller_no_diff_review_status": (
            no_diff_review_status
        ),
        "project_browser_autonomous_one_cycle_controller_no_diff_reason": no_diff_reason,
        "project_browser_autonomous_one_cycle_controller_review_handoff_decision_source_path": (
            review_handoff_decision_source_path
        ),
        "project_browser_autonomous_one_cycle_controller_review_handoff_decision_next_action": (
            review_handoff_decision_next_action
        ),
        "project_browser_autonomous_review_response_status": review_response_status,
        "project_browser_autonomous_review_response_decision": review_response_decision,
        "project_browser_autonomous_review_response_reason": review_response_reason,
        "project_browser_autonomous_review_response_path": str(review_response_path),
        "project_browser_autonomous_review_response_next_action": review_response_next_action,
        "project_browser_autonomous_targeted_fix_prompt_status": targeted_fix_prompt_status,
        "project_browser_autonomous_targeted_fix_prompt_text": targeted_fix_prompt_text,
        "project_browser_autonomous_targeted_fix_prompt_path": targeted_fix_prompt_resolved_path,
        "project_browser_autonomous_review_route_status": review_route_status,
        "project_browser_autonomous_review_route_decision": review_route_decision,
        "project_browser_autonomous_review_route_reason": review_route_reason,
        "project_browser_autonomous_review_route_next_action": review_route_next_action,
        "project_browser_autonomous_review_route_blocked_reason": review_route_blocked_reason,
        "project_browser_autonomous_review_route_source": review_route_source,
        "project_browser_autonomous_review_route_targeted_fix_prompt_path": (
            review_route_targeted_fix_prompt_path
        ),
        "project_browser_autonomous_review_route_should_prepare_commit": (
            review_route_should_prepare_commit
        ),
        "project_browser_autonomous_review_route_should_prepare_targeted_fix": (
            review_route_should_prepare_targeted_fix
        ),
        "project_browser_autonomous_review_route_should_prepare_reject": (
            review_route_should_prepare_reject
        ),
        "project_browser_autonomous_targeted_fix_boundary_status": (
            targeted_fix_boundary_status
        ),
        "project_browser_autonomous_targeted_fix_boundary_decision": (
            targeted_fix_boundary_decision
        ),
        "project_browser_autonomous_targeted_fix_boundary_reason": (
            targeted_fix_boundary_reason
        ),
        "project_browser_autonomous_targeted_fix_boundary_next_action": (
            targeted_fix_boundary_next_action
        ),
        "project_browser_autonomous_targeted_fix_boundary_blocked_reason": (
            targeted_fix_boundary_blocked_reason
        ),
        "project_browser_autonomous_targeted_fix_boundary_source_prompt_path": (
            targeted_fix_boundary_source_prompt_path
        ),
        "project_browser_autonomous_targeted_fix_boundary_codex_prompt_path": (
            targeted_fix_boundary_codex_prompt_path
        ),
        "project_browser_autonomous_targeted_fix_boundary_prompt_ready": (
            targeted_fix_boundary_prompt_ready
        ),
        "project_browser_autonomous_targeted_fix_boundary_should_execute_codex": (
            targeted_fix_boundary_should_execute_codex
        ),
        "project_browser_autonomous_targeted_fix_reentry_execution_enabled": (
            targeted_fix_reentry_execution_enabled
        ),
        "project_browser_autonomous_targeted_fix_reentry_execution_confirmed": (
            targeted_fix_reentry_execution_confirmed
        ),
        "project_browser_autonomous_targeted_fix_reentry_execution_gate_status": (
            targeted_fix_reentry_execution_gate_status
        ),
        "project_browser_autonomous_targeted_fix_reentry_execution_status": (
            targeted_fix_reentry_execution_status
        ),
        "project_browser_autonomous_targeted_fix_reentry_execution_attempted": (
            targeted_fix_reentry_execution_attempted
        ),
        "project_browser_autonomous_targeted_fix_reentry_execution_exit_code": (
            targeted_fix_reentry_execution_exit_code
        ),
        "project_browser_autonomous_targeted_fix_reentry_execution_blocked_reason": (
            targeted_fix_reentry_execution_blocked_reason
        ),
        "project_browser_autonomous_targeted_fix_reentry_execution_prompt_path": (
            targeted_fix_reentry_execution_prompt_path
        ),
        "project_browser_autonomous_targeted_fix_reentry_execution_receipt_path": str(
            targeted_fix_reentry_execution_receipt_path
        ),
        "project_browser_autonomous_targeted_fix_reentry_execution_should_execute_codex": (
            targeted_fix_reentry_execution_should_execute_codex
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_diff_capture_status": (
            targeted_fix_post_reentry_diff_capture_status
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_diff_capture_attempted": (
            targeted_fix_post_reentry_diff_capture_attempted
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_diff_capture_blocked_reason": (
            targeted_fix_post_reentry_diff_capture_blocked_reason
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_diff_has_diff": (
            targeted_fix_post_reentry_diff_has_diff
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_diff_changed_file_count": (
            targeted_fix_post_reentry_diff_changed_file_count
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_review_handoff_status": (
            targeted_fix_post_reentry_review_handoff_status
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_review_required": (
            targeted_fix_post_reentry_review_required
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_review_assimilation_status": (
            targeted_fix_post_reentry_review_assimilation_status
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_review_assimilation_blocked_reason": (
            targeted_fix_post_reentry_review_assimilation_blocked_reason
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_review_decision": (
            targeted_fix_post_reentry_review_decision
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_route_status": (
            targeted_fix_post_reentry_route_status
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_route_decision": (
            targeted_fix_post_reentry_route_decision
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_next_action": (
            targeted_fix_post_reentry_next_action
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_manual_review_required": (
            targeted_fix_post_reentry_manual_review_required
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_targeted_fix_required": (
            targeted_fix_post_reentry_targeted_fix_required
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_route_executor_boundary_status": (
            targeted_fix_post_reentry_route_executor_boundary_status
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_route_executor_kind": (
            targeted_fix_post_reentry_route_executor_kind
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_route_executor_next_action": (
            targeted_fix_post_reentry_route_executor_next_action
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_route_executor_execution_allowed": (
            targeted_fix_post_reentry_route_executor_execution_allowed
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_route_executor_manual_review_required": (
            targeted_fix_post_reentry_route_executor_manual_review_required
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_cycle_closure_allowed": (
            targeted_fix_post_reentry_cycle_closure_allowed
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_approval_boundary_allowed": (
            targeted_fix_post_reentry_approval_boundary_allowed
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_reject_boundary_allowed": (
            targeted_fix_post_reentry_reject_boundary_allowed
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_targeted_fix_prompt_emission_allowed": (
            targeted_fix_post_reentry_targeted_fix_prompt_emission_allowed
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_codex_reentry_allowed": (
            targeted_fix_post_reentry_codex_reentry_allowed
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_next_step_handoff_status": (
            targeted_fix_post_reentry_next_step_handoff_status
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_cycle_closure_status": (
            targeted_fix_post_reentry_cycle_closure_status
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_terminal_state": (
            targeted_fix_post_reentry_terminal_state
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_cycle_closed": (
            targeted_fix_post_reentry_cycle_closed
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_safe_to_stop": (
            targeted_fix_post_reentry_safe_to_stop
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_safe_to_commit_prompt_changes": (
            targeted_fix_post_reentry_safe_to_commit_prompt_changes
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_requires_codex_reentry": (
            targeted_fix_post_reentry_requires_codex_reentry
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_requires_manual_review": (
            targeted_fix_post_reentry_requires_manual_review
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_review_response_path": str(
            targeted_fix_post_reentry_review_response_path
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_review_assimilation_path": str(
            targeted_fix_post_reentry_review_assimilation_path
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_route_decision_path": str(
            targeted_fix_post_reentry_route_decision_path
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_route_executor_boundary_path": str(
            targeted_fix_post_reentry_route_executor_boundary_path
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_next_step_handoff_path": str(
            targeted_fix_post_reentry_next_step_handoff_path
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_cycle_closure_result_path": str(
            targeted_fix_post_reentry_cycle_closure_result_path
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_terminal_summary_path": str(
            targeted_fix_post_reentry_terminal_summary_path
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_prompt_emission_status": (
            targeted_fix_post_reentry_prompt_emission_status
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_prompt_emission_blocked_reason": (
            targeted_fix_post_reentry_prompt_emission_blocked_reason
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_prompt_written": (
            targeted_fix_post_reentry_prompt_written
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_prompt_ready_for_codex_reentry": (
            targeted_fix_post_reentry_prompt_ready_for_codex_reentry
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_prompt_emission_next_action": (
            targeted_fix_post_reentry_prompt_emission_next_action
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_prompt_emission_path": str(
            targeted_fix_post_reentry_prompt_emission_path
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_prompt_emission_receipt_path": str(
            targeted_fix_post_reentry_prompt_emission_receipt_path
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_emitted_prompt_path": (
            targeted_fix_post_reentry_emitted_prompt_path
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_codex_reentry_execution_status": (
            targeted_fix_post_reentry_codex_reentry_execution_status
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_codex_reentry_gate_status": (
            targeted_fix_post_reentry_codex_reentry_gate_status
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_codex_reentry_blocked_reason": (
            targeted_fix_post_reentry_codex_reentry_blocked_reason
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_codex_reentry_attempted": (
            targeted_fix_post_reentry_codex_reentry_attempted
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_codex_reentry_executed": (
            targeted_fix_post_reentry_codex_reentry_executed
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_codex_reentry_exit_code": (
            targeted_fix_post_reentry_codex_reentry_exit_code
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_codex_reentry_next_action": (
            targeted_fix_post_reentry_codex_reentry_next_action
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_codex_reentry_execution_receipt_path": str(
            targeted_fix_post_reentry_codex_reentry_execution_receipt_path
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_codex_reentry_stdout_path": str(
            targeted_fix_post_reentry_codex_reentry_execution_stdout_path
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_codex_reentry_stderr_path": str(
            targeted_fix_post_reentry_codex_reentry_execution_stderr_path
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_bounded_cycle_status": (
            targeted_fix_post_reentry_bounded_cycle_status
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_bounded_cycle_decision": (
            targeted_fix_post_reentry_bounded_cycle_decision
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_bounded_cycle_blocked_reason": (
            targeted_fix_post_reentry_bounded_cycle_blocked_reason
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_current_cycle_count": (
            targeted_fix_post_reentry_current_cycle_count
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_max_cycle_count": (
            targeted_fix_post_reentry_max_cycle_count
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_bounded_cycle_complete": (
            targeted_fix_post_reentry_bounded_cycle_complete
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_bounded_cycle_should_continue": (
            targeted_fix_post_reentry_bounded_cycle_should_continue
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_bounded_cycle_should_emit_prompt": (
            targeted_fix_post_reentry_bounded_cycle_should_emit_prompt
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_bounded_cycle_should_execute_codex": (
            targeted_fix_post_reentry_bounded_cycle_should_execute_codex
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_bounded_cycle_should_capture_diff": (
            targeted_fix_post_reentry_bounded_cycle_should_capture_diff
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_bounded_cycle_next_action": (
            targeted_fix_post_reentry_bounded_cycle_next_action
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_bounded_cycle_state_path": str(
            targeted_fix_post_reentry_bounded_cycle_state_path
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_bounded_cycle_decision_path": str(
            targeted_fix_post_reentry_bounded_cycle_decision_path
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_bounded_cycle_receipt_path": str(
            targeted_fix_post_reentry_bounded_cycle_receipt_path
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_review_handoff_path": str(
            targeted_fix_post_reentry_review_handoff_path
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_diff_capture_path": str(
            targeted_fix_post_reentry_diff_capture_path
        ),
        "project_browser_autonomous_targeted_fix_post_reentry_diff_patch_path": str(
            targeted_fix_post_reentry_diff_patch_path
        ),
        "project_browser_autonomous_approve_commit_tag_boundary_status": (
            approve_commit_tag_boundary_status
        ),
        "project_browser_autonomous_approve_commit_tag_boundary_decision": (
            approve_commit_tag_boundary_decision
        ),
        "project_browser_autonomous_approve_commit_tag_boundary_reason": (
            approve_commit_tag_boundary_reason
        ),
        "project_browser_autonomous_approve_commit_tag_boundary_next_action": (
            approve_commit_tag_boundary_next_action
        ),
        "project_browser_autonomous_approve_commit_tag_boundary_blocked_reason": (
            approve_commit_tag_boundary_blocked_reason
        ),
        "project_browser_autonomous_approve_commit_tag_boundary_commit_message": (
            approve_commit_tag_boundary_commit_message
        ),
        "project_browser_autonomous_approve_commit_tag_boundary_tag_name": (
            approve_commit_tag_boundary_tag_name
        ),
        "project_browser_autonomous_approve_commit_tag_boundary_commands_path": (
            approve_commit_tag_boundary_commands_resolved_path
        ),
        "project_browser_autonomous_approve_commit_tag_boundary_metadata_path": (
            approve_commit_tag_boundary_metadata_resolved_path
        ),
        "project_browser_autonomous_approve_commit_tag_boundary_should_execute_commit": (
            approve_commit_tag_boundary_should_execute_commit
        ),
        "project_browser_autonomous_approve_commit_tag_boundary_should_execute_tag": (
            approve_commit_tag_boundary_should_execute_tag
        ),
        "project_browser_autonomous_approve_commit_tag_boundary_ready": (
            approve_commit_tag_boundary_ready
        ),
        "project_browser_autonomous_approve_commit_tag_plan_ready": (
            approve_commit_tag_plan_ready
        ),
        "project_browser_autonomous_approve_commit_tag_tracked_files_allowed": (
            approve_commit_tag_tracked_files_allowed
        ),
        "project_browser_autonomous_approve_commit_tag_changed_tracked_files": (
            approve_commit_tag_changed_tracked_files
        ),
        "project_browser_autonomous_approve_commit_tag_unexpected_tracked_files": (
            approve_commit_tag_unexpected_tracked_files
        ),
        "project_browser_autonomous_approve_commit_tag_explicit_add_paths": (
            approve_commit_tag_explicit_add_paths
        ),
        "project_browser_autonomous_approve_commit_tag_proposed_commit_message": (
            approve_commit_tag_proposed_commit_message
        ),
        "project_browser_autonomous_approve_commit_tag_proposed_tag": (
            approve_commit_tag_proposed_tag
        ),
        "project_browser_autonomous_approve_commit_tag_command_file_path": (
            approve_commit_tag_command_file_path
        ),
        "project_browser_autonomous_approve_commit_tag_execution_allowed": (
            approve_commit_tag_execution_allowed
        ),
        "project_browser_autonomous_approve_commit_tag_next_action": (
            approve_commit_tag_boundary_next_action
        ),
        "project_browser_autonomous_approve_commit_tag_boundary_path": (
            approve_commit_tag_boundary_path
        ),
        "project_browser_autonomous_approve_commit_tag_plan_path": (
            approve_commit_tag_plan_path
        ),
        "project_browser_autonomous_approve_commit_tag_artifact_reconciliation_status": (
            approve_commit_tag_artifact_reconciliation_status
        ),
        "project_browser_autonomous_approve_commit_tag_artifact_reconciliation_blocked_reason": (
            approve_commit_tag_artifact_reconciliation_blocked_reason
        ),
        "project_browser_autonomous_approve_commit_tag_artifact_reconciliation_stale_artifacts_detected": (
            approve_commit_tag_artifact_reconciliation_stale_artifacts_detected
        ),
        "project_browser_autonomous_approve_commit_tag_artifact_reconciliation_already_committed": (
            approve_commit_tag_artifact_reconciliation_already_committed
        ),
        "project_browser_autonomous_approve_commit_tag_artifact_reconciliation_already_tagged": (
            approve_commit_tag_artifact_reconciliation_already_tagged
        ),
        "project_browser_autonomous_approve_commit_tag_artifact_reconciliation_next_action": (
            approve_commit_tag_artifact_reconciliation_next_action
        ),
        "project_browser_autonomous_approve_commit_tag_artifact_reconciliation_receipt_path": (
            approve_commit_tag_artifact_reconciliation_receipt_path
        ),
        "project_browser_autonomous_remote_readiness_boundary_status": (
            remote_readiness_boundary_status
        ),
        "project_browser_autonomous_remote_readiness_blocked_reason": (
            remote_readiness_blocked_reason
        ),
        "project_browser_autonomous_remote_readiness_remote_ready": (
            remote_readiness_remote_ready
        ),
        "project_browser_autonomous_remote_readiness_push_ready": (
            remote_readiness_push_ready
        ),
        "project_browser_autonomous_remote_readiness_pr_ready": (
            remote_readiness_pr_ready
        ),
        "project_browser_autonomous_remote_readiness_merge_ready": (
            remote_readiness_merge_ready
        ),
        "project_browser_autonomous_remote_readiness_worktree_clean": (
            remote_readiness_worktree_clean
        ),
        "project_browser_autonomous_remote_readiness_expected_head_tag_present": (
            remote_readiness_expected_head_tag_present
        ),
        "project_browser_autonomous_remote_readiness_remote_configured": (
            remote_readiness_remote_configured
        ),
        "project_browser_autonomous_remote_readiness_upstream_configured": (
            remote_readiness_upstream_configured
        ),
        "project_browser_autonomous_remote_readiness_next_action": (
            remote_readiness_next_action
        ),
        "project_browser_autonomous_remote_readiness_boundary_path": (
            remote_readiness_boundary_path
        ),
        "project_browser_autonomous_remote_readiness_plan_path": (
            remote_readiness_plan_path
        ),
        "project_browser_autonomous_local_end_to_end_readiness_status": (
            local_end_to_end_readiness_status
        ),
        "project_browser_autonomous_local_end_to_end_readiness_blocked_reason": (
            local_end_to_end_readiness_blocked_reason
        ),
        "project_browser_autonomous_local_end_to_end_ready": local_end_to_end_ready,
        "project_browser_autonomous_local_components_ready": local_components_ready,
        "project_browser_autonomous_integrated_local_runner_ready": (
            integrated_local_runner_ready
        ),
        "project_browser_autonomous_implementation_prompt_generation_status": (
            implementation_prompt_generation_status
        ),
        "project_browser_autonomous_github_deferred": github_deferred,
        "project_browser_autonomous_remote_required": remote_required,
        "project_browser_autonomous_local_end_to_end_next_action": (
            local_end_to_end_next_action
        ),
        "project_browser_autonomous_local_end_to_end_component_matrix_path": (
            local_end_to_end_component_matrix_surface_path
        ),
        "project_browser_autonomous_local_end_to_end_readiness_boundary_path": (
            local_end_to_end_readiness_boundary_surface_path
        ),
        "project_browser_autonomous_local_end_to_end_gap_report_path": (
            local_end_to_end_gap_report_surface_path
        ),
        "project_browser_autonomous_local_end_to_end_dry_run_plan_status": (
            local_end_to_end_dry_run_plan_status
        ),
        "project_browser_autonomous_local_end_to_end_dry_run_blocked_reason": (
            local_end_to_end_dry_run_blocked_reason
        ),
        "project_browser_autonomous_local_end_to_end_dry_run_plan_ready": (
            local_end_to_end_dry_run_plan_ready
        ),
        "project_browser_autonomous_local_end_to_end_dry_run_step_count": (
            local_end_to_end_dry_run_step_count
        ),
        "project_browser_autonomous_local_end_to_end_dry_run_execution_allowed": (
            local_end_to_end_dry_run_execution_allowed
        ),
        "project_browser_autonomous_local_end_to_end_dry_run_next_action": (
            local_end_to_end_dry_run_next_action
        ),
        "project_browser_autonomous_local_end_to_end_dry_run_plan_path": (
            local_end_to_end_dry_run_plan_surface_path
        ),
        "project_browser_autonomous_local_end_to_end_dry_run_step_matrix_path": (
            local_end_to_end_dry_run_step_matrix_surface_path
        ),
        "project_browser_autonomous_local_end_to_end_dry_run_receipt_path": (
            local_end_to_end_dry_run_receipt_surface_path
        ),
        "project_browser_autonomous_local_one_shot_gate_status": local_one_shot_gate_status,
        "project_browser_autonomous_local_one_shot_blocked_reason": (
            local_one_shot_blocked_reason
        ),
        "project_browser_autonomous_local_one_shot_gate_ready": local_one_shot_gate_ready,
        "project_browser_autonomous_local_one_shot_selected_step_id": (
            local_one_shot_selected_step_id
        ),
        "project_browser_autonomous_local_one_shot_selected_step_name": (
            local_one_shot_selected_step_name
        ),
        "project_browser_autonomous_local_one_shot_execution_allowed": (
            local_one_shot_execution_allowed
        ),
        "project_browser_autonomous_local_one_shot_next_action": (
            local_one_shot_next_action
        ),
        "project_browser_autonomous_local_one_shot_gate_path": (
            local_one_shot_gate_surface_path
        ),
        "project_browser_autonomous_local_one_shot_step_selection_path": (
            local_one_shot_step_selection_surface_path
        ),
        "project_browser_autonomous_local_one_shot_receipt_path": (
            local_one_shot_receipt_surface_path
        ),
        "project_browser_autonomous_bounded_local_loop_status": (
            bounded_local_loop_status
        ),
        "project_browser_autonomous_bounded_local_loop_blocked_reason": (
            bounded_local_loop_blocked_reason
        ),
        "project_browser_autonomous_bounded_local_loop_ready": (
            bounded_local_loop_ready
        ),
        "project_browser_autonomous_bounded_local_loop_complete": (
            bounded_local_loop_complete
        ),
        "project_browser_autonomous_bounded_local_loop_should_continue": (
            bounded_local_loop_should_continue
        ),
        "project_browser_autonomous_bounded_local_loop_selected_step_id": (
            bounded_local_loop_selected_step_id
        ),
        "project_browser_autonomous_bounded_local_loop_selected_step_name": (
            bounded_local_loop_selected_step_name
        ),
        "project_browser_autonomous_bounded_local_loop_execution_allowed": (
            bounded_local_loop_execution_allowed
        ),
        "project_browser_autonomous_bounded_local_loop_next_action": (
            bounded_local_loop_next_action
        ),
        "project_browser_autonomous_bounded_local_loop_state_path": (
            bounded_local_loop_state_surface_path
        ),
        "project_browser_autonomous_bounded_local_loop_decision_path": (
            bounded_local_loop_decision_surface_path
        ),
        "project_browser_autonomous_bounded_local_loop_receipt_path": (
            bounded_local_loop_receipt_surface_path
        ),
        "project_browser_autonomous_selected_step_execution_adapter_status": (
            selected_step_execution_adapter_status
        ),
        "project_browser_autonomous_selected_step_execution_blocked_reason": (
            selected_step_execution_blocked_reason
        ),
        "project_browser_autonomous_selected_step_execution_ready": (
            selected_step_execution_ready
        ),
        "project_browser_autonomous_selected_step_execution_selected_step_id": (
            selected_step_execution_selected_step_id
        ),
        "project_browser_autonomous_selected_step_execution_selected_step_name": (
            selected_step_execution_selected_step_name
        ),
        "project_browser_autonomous_selected_step_execution_operation": (
            selected_step_execution_operation
        ),
        "project_browser_autonomous_selected_step_execution_allowed": (
            selected_step_execution_allowed
        ),
        "project_browser_autonomous_selected_step_execution_performed": (
            selected_step_execution_performed
        ),
        "project_browser_autonomous_selected_step_execution_next_action": (
            selected_step_execution_next_action
        ),
        "project_browser_autonomous_selected_step_execution_adapter_state_path": (
            selected_step_execution_adapter_state_surface_path
        ),
        "project_browser_autonomous_selected_step_execution_plan_path": (
            selected_step_execution_plan_surface_path
        ),
        "project_browser_autonomous_selected_step_execution_receipt_path": (
            selected_step_execution_receipt_surface_path
        ),
        "project_browser_autonomous_selected_step_live_execution_gate_status": (
            selected_step_live_execution_gate_status
        ),
        "project_browser_autonomous_selected_step_live_execution_blocked_reason": (
            selected_step_live_execution_blocked_reason
        ),
        "project_browser_autonomous_selected_step_live_execution_ready": (
            selected_step_live_execution_ready
        ),
        "project_browser_autonomous_selected_step_live_execution_allowed": (
            selected_step_live_execution_allowed
        ),
        "project_browser_autonomous_selected_step_live_execution_performed": (
            selected_step_live_execution_performed
        ),
        "project_browser_autonomous_selected_step_live_execution_selected_step_id": (
            selected_step_live_execution_selected_step_id
        ),
        "project_browser_autonomous_selected_step_live_execution_selected_step_name": (
            selected_step_live_execution_selected_step_name
        ),
        "project_browser_autonomous_selected_step_live_execution_operation": (
            selected_step_live_execution_operation
        ),
        "project_browser_autonomous_selected_step_live_execution_result_status": (
            selected_step_live_execution_result_status
        ),
        "project_browser_autonomous_selected_step_live_execution_next_action": (
            selected_step_live_execution_next_action
        ),
        "project_browser_autonomous_selected_step_live_execution_gate_path": (
            selected_step_live_execution_gate_surface_path
        ),
        "project_browser_autonomous_selected_step_live_execution_result_path": (
            selected_step_live_execution_result_surface_path
        ),
        "project_browser_autonomous_selected_step_live_execution_receipt_path": (
            selected_step_live_execution_receipt_surface_path
        ),
        "project_browser_autonomous_selected_step_execution_result_route_status": (
            selected_step_execution_result_route_status
        ),
        "project_browser_autonomous_selected_step_execution_result_route_blocked_reason": (
            selected_step_execution_result_route_blocked_reason
        ),
        "project_browser_autonomous_selected_step_execution_result_route_decision": (
            selected_step_execution_result_route_decision
        ),
        "project_browser_autonomous_selected_step_execution_result_route_next_action": (
            selected_step_execution_result_route_next_action
        ),
        "project_browser_autonomous_selected_step_execution_result_route_should_continue": (
            selected_step_execution_result_route_should_continue
        ),
        "project_browser_autonomous_selected_step_execution_result_route_capture_path": (
            selected_step_execution_result_route_capture_surface_path
        ),
        "project_browser_autonomous_selected_step_execution_result_route_decision_path": (
            selected_step_execution_result_route_decision_surface_path
        ),
        "project_browser_autonomous_selected_step_execution_result_route_receipt_path": (
            selected_step_execution_result_route_receipt_surface_path
        ),
        "project_browser_autonomous_local_only_autonomous_loop_closure_status": (
            local_only_autonomous_loop_closure_status
        ),
        "project_browser_autonomous_local_only_autonomous_loop_closure_blocked_reason": (
            local_only_autonomous_loop_closure_blocked_reason
        ),
        "project_browser_autonomous_local_only_autonomous_loop_closure_decision": (
            local_only_autonomous_loop_closure_decision
        ),
        "project_browser_autonomous_local_only_autonomous_loop_closure_next_action": (
            local_only_autonomous_loop_closure_next_action
        ),
        "project_browser_autonomous_local_only_autonomous_loop_v1_complete": (
            local_only_autonomous_loop_v1_complete
        ),
        "project_browser_autonomous_local_only_autonomous_loop_closed": (
            local_only_autonomous_loop_closed
        ),
        "project_browser_autonomous_local_only_autonomous_loop_closure_should_continue": (
            local_only_autonomous_loop_closure_should_continue
        ),
        "project_browser_autonomous_local_only_autonomous_loop_closure_state_path": (
            local_only_autonomous_loop_closure_state_surface_path
        ),
        "project_browser_autonomous_local_only_autonomous_loop_closure_decision_path": (
            local_only_autonomous_loop_closure_decision_surface_path
        ),
        "project_browser_autonomous_local_only_autonomous_loop_closure_receipt_path": (
            local_only_autonomous_loop_closure_receipt_surface_path
        ),
        "project_browser_autonomous_local_autonomous_cycle_v2_status": (
            local_autonomous_cycle_v2_status
        ),
        "project_browser_autonomous_local_autonomous_cycle_v2_cycle_status": (
            local_autonomous_cycle_v2_cycle_status
        ),
        "project_browser_autonomous_local_autonomous_cycle_v2_next_action": (
            local_autonomous_cycle_v2_next_action
        ),
        "project_browser_autonomous_local_autonomous_cycle_v2_selected_step_id": (
            local_autonomous_cycle_v2_selected_step_id
        ),
        "project_browser_autonomous_local_autonomous_cycle_v2_selected_step_name": (
            local_autonomous_cycle_v2_selected_step_name or ""
        ),
        "project_browser_autonomous_local_autonomous_cycle_v2_selected_step_operation": (
            local_autonomous_cycle_v2_selected_step_operation or ""
        ),
        "project_browser_autonomous_local_autonomous_cycle_v2_decision": (
            local_autonomous_cycle_v2_decision
        ),
        "project_browser_autonomous_local_autonomous_cycle_v2_ready": (
            local_autonomous_cycle_v2_ready
        ),
        "project_browser_autonomous_local_autonomous_cycle_v2_blocked_reason": (
            local_autonomous_cycle_v2_blocked_reason
        ),
        "project_browser_autonomous_local_autonomous_cycle_v2_readiness_reason": (
            local_autonomous_cycle_v2_readiness_reason
        ),
        "project_browser_autonomous_local_autonomous_cycle_v2_run_id": (
            local_autonomous_cycle_v2_run_id
        ),
        "project_browser_autonomous_local_autonomous_cycle_v2_cycle_id": (
            local_autonomous_cycle_v2_cycle_id
        ),
        "project_browser_autonomous_local_autonomous_cycle_v2_current_cycle": (
            local_autonomous_cycle_v2_current_cycle
        ),
        "project_browser_autonomous_local_autonomous_cycle_v2_max_cycles": (
            local_autonomous_cycle_v2_max_cycles
        ),
        "project_browser_autonomous_local_autonomous_cycle_v2_state_path": (
            local_autonomous_cycle_v2_state_surface_path
        ),
        "project_browser_autonomous_local_autonomous_cycle_v2_decision_path": (
            local_autonomous_cycle_v2_decision_surface_path
        ),
        "project_browser_autonomous_local_autonomous_cycle_v2_receipt_path": (
            local_autonomous_cycle_v2_receipt_surface_path
        ),
        "project_browser_autonomous_local_codex_one_shot_handoff_status": (
            local_codex_one_shot_handoff_status
        ),
        "project_browser_autonomous_local_codex_one_shot_handoff_handoff_status": (
            local_codex_one_shot_handoff_handoff_status
        ),
        "project_browser_autonomous_local_codex_one_shot_handoff_next_action": (
            local_codex_one_shot_handoff_next_action
        ),
        "project_browser_autonomous_local_codex_one_shot_handoff_blocked_reason": (
            local_codex_one_shot_handoff_blocked_reason
        ),
        "project_browser_autonomous_local_codex_one_shot_handoff_readiness_reason": (
            local_codex_one_shot_handoff_readiness_reason
        ),
        "project_browser_autonomous_local_codex_one_shot_handoff_prompt_ready": (
            local_codex_one_shot_handoff_prompt_ready
        ),
        "project_browser_autonomous_local_codex_one_shot_handoff_command_ready": (
            local_codex_one_shot_handoff_command_ready
        ),
        "project_browser_autonomous_local_codex_one_shot_handoff_codex_invocation_allowed": (
            local_codex_one_shot_handoff_codex_invocation_allowed
        ),
        "project_browser_autonomous_local_codex_one_shot_handoff_execution_allowed": (
            local_codex_one_shot_handoff_execution_allowed
        ),
        "project_browser_autonomous_local_codex_one_shot_handoff_max_codex_invocations": (
            local_codex_one_shot_handoff_max_codex_invocations
        ),
        "project_browser_autonomous_local_codex_one_shot_handoff_codex_invocation_count": (
            local_codex_one_shot_handoff_codex_invocation_count
        ),
        "project_browser_autonomous_local_codex_one_shot_handoff_selected_step_id": (
            local_codex_one_shot_handoff_selected_step_id
        ),
        "project_browser_autonomous_local_codex_one_shot_handoff_selected_step_name": (
            local_codex_one_shot_handoff_selected_step_name or ""
        ),
        "project_browser_autonomous_local_codex_one_shot_handoff_selected_step_operation": (
            local_codex_one_shot_handoff_selected_step_operation or ""
        ),
        "project_browser_autonomous_local_codex_one_shot_handoff_prompt_path": (
            local_codex_one_shot_handoff_prompt_path or ""
        ),
        "project_browser_autonomous_local_codex_one_shot_handoff_command_display": (
            local_codex_one_shot_handoff_command_display
        ),
        "project_browser_autonomous_local_codex_one_shot_handoff_run_id": (
            local_codex_one_shot_handoff_run_id
        ),
        "project_browser_autonomous_local_codex_one_shot_handoff_cycle_id": (
            local_codex_one_shot_handoff_cycle_id
        ),
        "project_browser_autonomous_local_codex_one_shot_handoff_current_cycle": (
            local_codex_one_shot_handoff_current_cycle
        ),
        "project_browser_autonomous_local_codex_one_shot_handoff_max_cycles": (
            local_codex_one_shot_handoff_max_cycles
        ),
        "project_browser_autonomous_local_codex_one_shot_execution_status": (
            local_codex_one_shot_execution_status
        ),
        "project_browser_autonomous_local_codex_one_shot_execution_execution_status": (
            local_codex_one_shot_execution_execution_status
        ),
        "project_browser_autonomous_local_codex_one_shot_execution_next_action": (
            local_codex_one_shot_execution_next_action
        ),
        "project_browser_autonomous_local_codex_one_shot_execution_blocked_reason": (
            local_codex_one_shot_execution_blocked_reason
        ),
        "project_browser_autonomous_local_codex_one_shot_execution_readiness_reason": (
            local_codex_one_shot_execution_readiness_reason
        ),
        "project_browser_autonomous_local_codex_one_shot_execution_codex_invoked": (
            local_codex_one_shot_execution_codex_invoked
        ),
        "project_browser_autonomous_local_codex_one_shot_execution_codex_invocation_allowed": (
            local_codex_one_shot_execution_codex_invocation_allowed
        ),
        "project_browser_autonomous_local_codex_one_shot_execution_execution_allowed": (
            local_codex_one_shot_execution_execution_allowed
        ),
        "project_browser_autonomous_local_codex_one_shot_execution_execution_attempted": (
            local_codex_one_shot_execution_execution_attempted
        ),
        "project_browser_autonomous_local_codex_one_shot_execution_execution_completed": (
            local_codex_one_shot_execution_execution_completed
        ),
        "project_browser_autonomous_local_codex_one_shot_execution_execution_exit_code": (
            local_codex_one_shot_execution_execution_exit_code
        ),
        "project_browser_autonomous_local_codex_one_shot_execution_max_codex_invocations": (
            local_codex_one_shot_execution_max_codex_invocations
        ),
        "project_browser_autonomous_local_codex_one_shot_execution_codex_invocation_count": (
            local_codex_one_shot_execution_codex_invocation_count
        ),
        "project_browser_autonomous_local_codex_one_shot_execution_selected_step_id": (
            local_codex_one_shot_execution_selected_step_id
        ),
        "project_browser_autonomous_local_codex_one_shot_execution_selected_step_name": (
            local_codex_one_shot_execution_selected_step_name or ""
        ),
        "project_browser_autonomous_local_codex_one_shot_execution_selected_step_operation": (
            local_codex_one_shot_execution_selected_step_operation or ""
        ),
        "project_browser_autonomous_local_codex_one_shot_execution_prompt_path": (
            local_codex_one_shot_execution_prompt_path or ""
        ),
        "project_browser_autonomous_local_codex_one_shot_execution_stdout_path": (
            local_codex_one_shot_execution_stdout_path_text or ""
        ),
        "project_browser_autonomous_local_codex_one_shot_execution_stderr_path": (
            local_codex_one_shot_execution_stderr_path_text or ""
        ),
        "project_browser_autonomous_local_codex_one_shot_execution_result_path": (
            local_codex_one_shot_execution_result_path_text or ""
        ),
        "project_browser_autonomous_local_codex_one_shot_execution_run_id": (
            local_codex_one_shot_execution_run_id
        ),
        "project_browser_autonomous_local_codex_one_shot_execution_cycle_id": (
            local_codex_one_shot_execution_cycle_id
        ),
        "project_browser_autonomous_local_codex_one_shot_execution_current_cycle": (
            local_codex_one_shot_execution_current_cycle
        ),
        "project_browser_autonomous_local_codex_one_shot_execution_max_cycles": (
            local_codex_one_shot_execution_max_cycles
        ),
        "project_browser_autonomous_local_post_codex_diff_capture_status": (
            local_post_codex_diff_capture_status
        ),
        "project_browser_autonomous_local_post_codex_diff_capture_blocked_reason": (
            local_post_codex_diff_capture_blocked_reason
        ),
        "project_browser_autonomous_local_post_codex_diff_capture_next_action": (
            local_post_codex_diff_capture_next_action
        ),
        "project_browser_autonomous_local_post_codex_diff_capture_worktree_clean_for_tracked_files": (
            local_post_codex_diff_capture_worktree_clean_for_tracked_files
        ),
        "project_browser_autonomous_local_post_codex_diff_capture_changed_tracked_file_count": (
            local_post_codex_diff_capture_changed_tracked_file_count
        ),
        "project_browser_autonomous_local_post_codex_outcome_status": local_post_codex_outcome_status,
        "project_browser_autonomous_local_post_codex_outcome_classification": (
            local_post_codex_outcome_classification
        ),
        "project_browser_autonomous_local_post_codex_stdout_contains_blocked": (
            local_post_codex_stdout_contains_blocked
        ),
        "project_browser_autonomous_local_post_codex_stdout_blocked_reason": (
            local_post_codex_stdout_blocked_reason
        ),
        "project_browser_autonomous_local_post_codex_route_status": local_post_codex_route_status,
        "project_browser_autonomous_local_post_codex_route_decision": (
            local_post_codex_route_decision
        ),
        "project_browser_autonomous_local_post_codex_route_next_action": (
            local_post_codex_route_next_action
        ),
        "project_browser_autonomous_local_post_codex_route_targeted_contract_fix_recommended": (
            local_post_codex_route_targeted_contract_fix_recommended
        ),
        "project_browser_autonomous_local_post_codex_route_approve_commit_tag_allowed": (
            local_post_codex_route_approve_commit_tag_allowed
        ),
        "project_browser_autonomous_prompt334_stale_post_codex_artifact_detected": (
            prompt334_stale_post_codex_artifact_detected
        ),
        "project_browser_autonomous_prompt334_stale_post_codex_artifact_regeneration_attempted": (
            prompt334_stale_post_codex_artifact_regeneration_attempted
        ),
        "project_browser_autonomous_prompt334_stale_post_codex_artifact_regeneration_reason": (
            prompt334_stale_post_codex_artifact_regeneration_reason
        ),
        "project_browser_autonomous_prompt334_stale_post_codex_artifact_regeneration_status": (
            prompt334_stale_post_codex_artifact_regeneration_status
        ),
        "project_browser_autonomous_local_post_codex_diff_capture_path": str(
            local_post_codex_diff_capture_path
        ),
        "project_browser_autonomous_local_post_codex_execution_outcome_path": str(
            local_post_codex_execution_outcome_path
        ),
        "project_browser_autonomous_local_post_codex_route_decision_path": str(
            local_post_codex_route_decision_path
        ),
        "project_browser_autonomous_local_post_codex_diff_capture_receipt_path": str(
            local_post_codex_diff_capture_receipt_path
        ),
        "project_browser_autonomous_local_targeted_contract_fix_route_intake_status": (
            local_targeted_contract_fix_route_intake_status
        ),
        "project_browser_autonomous_local_targeted_contract_fix_route_intake_blocked_reason": (
            local_targeted_contract_fix_route_intake_blocked_reason
        ),
        "project_browser_autonomous_local_targeted_contract_fix_route_intake_signal_source": (
            local_targeted_contract_fix_route_intake_signal_source
        ),
        "project_browser_autonomous_local_targeted_contract_fix_prompt_plan_status": (
            local_targeted_contract_fix_prompt_plan_status
        ),
        "project_browser_autonomous_local_targeted_contract_fix_prompt_plan_blocked_reason": (
            local_targeted_contract_fix_prompt_plan_blocked_reason
        ),
        "project_browser_autonomous_local_targeted_contract_fix_prompt_path": (
            local_targeted_contract_fix_prompt_path_text
        ),
        "project_browser_autonomous_local_targeted_contract_fix_prompt_ready": (
            local_targeted_contract_fix_prompt_ready
        ),
        "project_browser_autonomous_local_targeted_contract_fix_prompt_next_action": (
            local_targeted_contract_fix_prompt_next_action
        ),
        "project_browser_autonomous_local_targeted_contract_fix_prompt_normalized_reason": (
            local_targeted_contract_fix_prompt_normalized_reason
        ),
        "project_browser_autonomous_local_targeted_contract_fix_prompt_lifecycle_issue_detected": (
            local_targeted_contract_fix_prompt_lifecycle_issue_detected
        ),
        "project_browser_autonomous_local_contract_fix_cycle_coordination_status": (
            local_contract_fix_cycle_coordination_status
        ),
        "project_browser_autonomous_local_contract_fix_cycle_coordination_blocked_reason": (
            local_contract_fix_cycle_coordination_blocked_reason
        ),
        "project_browser_autonomous_local_contract_fix_cycle_coordination_ready": (
            local_contract_fix_cycle_coordination_ready
        ),
        "project_browser_autonomous_local_contract_fix_cycle_coordination_next_action": (
            local_contract_fix_cycle_coordination_next_action
        ),
        "project_browser_autonomous_local_contract_fix_cycle_prompt_path": (
            local_contract_fix_cycle_prompt_path
        ),
        "project_browser_autonomous_local_contract_fix_cycle_prompt_ready": (
            local_contract_fix_cycle_prompt_ready
        ),
        "project_browser_autonomous_local_contract_fix_cycle_normalized_reason": (
            local_contract_fix_cycle_normalized_reason
        ),
        "project_browser_autonomous_local_contract_fix_cycle_selected_step_name": (
            local_contract_fix_cycle_selected_step_name
        ),
        "project_browser_autonomous_local_contract_fix_cycle_handoff_status": (
            local_contract_fix_cycle_handoff_status
        ),
        "project_browser_autonomous_local_contract_fix_cycle_handoff_next_action": (
            local_contract_fix_cycle_handoff_next_action
        ),
        "project_browser_autonomous_local_daemon_lite_wrapper_status": (
            local_daemon_lite_wrapper_status
        ),
        "project_browser_autonomous_local_daemon_lite_wrapper_blocked_reason": (
            local_daemon_lite_wrapper_blocked_reason
        ),
        "project_browser_autonomous_local_daemon_lite_wrapper_ready": (
            local_daemon_lite_wrapper_ready
        ),
        "project_browser_autonomous_local_daemon_lite_wrapper_decision": (
            local_daemon_lite_wrapper_decision
        ),
        "project_browser_autonomous_local_daemon_lite_wrapper_next_action": (
            local_daemon_lite_wrapper_next_action
        ),
        "project_browser_autonomous_local_daemon_lite_wrapper_selected_step_name": (
            local_daemon_lite_wrapper_selected_step_name
        ),
        "project_browser_autonomous_local_daemon_lite_wrapper_prompt_path": (
            local_daemon_lite_wrapper_prompt_path
        ),
        "project_browser_autonomous_local_daemon_lite_wrapper_bounded_execution": (
            local_daemon_lite_wrapper_bounded_execution
        ),
        "project_browser_autonomous_local_daemon_lite_wrapper_total_codex_invocation_budget": (
            local_daemon_lite_wrapper_total_codex_invocation_budget
        ),
        "project_browser_autonomous_local_targeted_contract_fix_execution_status": (
            local_targeted_contract_fix_execution_status
        ),
        "project_browser_autonomous_local_targeted_contract_fix_execution_blocked_reason": (
            local_targeted_contract_fix_execution_blocked_reason
        ),
        "project_browser_autonomous_local_targeted_contract_fix_execution_next_action": (
            local_targeted_contract_fix_execution_next_action
        ),
        "project_browser_autonomous_local_targeted_contract_fix_execution_codex_invoked": (
            local_targeted_contract_fix_execution_codex_invoked
        ),
        "project_browser_autonomous_local_targeted_contract_fix_execution_exit_code": (
            local_targeted_contract_fix_execution_exit_code
        ),
        "project_browser_autonomous_local_targeted_contract_fix_execution_changed_tracked_file_count": (
            local_targeted_contract_fix_execution_changed_tracked_file_count
        ),
        "project_browser_autonomous_local_targeted_contract_fix_execution_stdout_path": (
            local_targeted_contract_fix_execution_stdout_path_text
        ),
        "project_browser_autonomous_local_targeted_contract_fix_execution_stderr_path": (
            local_targeted_contract_fix_execution_stderr_path_text
        ),
        "project_browser_autonomous_local_post_targeted_contract_fix_status": (
            local_post_targeted_contract_fix_status
        ),
        "project_browser_autonomous_local_post_targeted_contract_fix_blocked_reason": (
            local_post_targeted_contract_fix_blocked_reason
        ),
        "project_browser_autonomous_local_post_targeted_contract_fix_classification": (
            local_post_targeted_contract_fix_classification
        ),
        "project_browser_autonomous_local_post_targeted_contract_fix_route_decision": (
            local_post_targeted_contract_fix_route_decision
        ),
        "project_browser_autonomous_local_post_targeted_contract_fix_next_action": (
            local_post_targeted_contract_fix_next_action
        ),
        "project_browser_autonomous_local_post_targeted_contract_fix_approve_commit_tag_ready": (
            local_post_targeted_contract_fix_approve_commit_tag_ready
        ),
        "project_browser_autonomous_local_post_targeted_contract_fix_changed_tracked_file_count": (
            local_post_targeted_contract_fix_changed_tracked_file_count
        ),
        "project_browser_autonomous_local_post_targeted_contract_fix_unexpected_tracked_file_count": (
            local_post_targeted_contract_fix_unexpected_tracked_file_count
        ),
        "project_browser_autonomous_local_post_targeted_contract_fix_diff_capture_path": str(
            local_post_targeted_contract_fix_diff_capture_path
        ),
        "project_browser_autonomous_local_post_targeted_contract_fix_execution_outcome_path": str(
            local_post_targeted_contract_fix_execution_outcome_path
        ),
        "project_browser_autonomous_local_post_targeted_contract_fix_route_decision_path": str(
            local_post_targeted_contract_fix_route_decision_path
        ),
        "project_browser_autonomous_local_post_targeted_contract_fix_review_receipt_path": str(
            local_post_targeted_contract_fix_review_receipt_path
        ),
        "project_browser_autonomous_local_bounded_approve_commit_tag_status": (
            local_bounded_approve_commit_tag_status
        ),
        "project_browser_autonomous_local_bounded_approve_commit_tag_execution_status": (
            local_bounded_approve_commit_tag_execution_status
        ),
        "project_browser_autonomous_local_bounded_approve_commit_tag_blocked_reason": (
            local_bounded_approve_commit_tag_blocked_reason
        ),
        "project_browser_autonomous_local_bounded_approve_commit_tag_next_action": (
            local_bounded_approve_commit_tag_next_action
        ),
        "project_browser_autonomous_local_bounded_approve_commit_tag_commit_performed": (
            local_bounded_approve_commit_tag_commit_performed
        ),
        "project_browser_autonomous_local_bounded_approve_commit_tag_tag_performed": (
            local_bounded_approve_commit_tag_tag_performed
        ),
        "project_browser_autonomous_local_bounded_approve_commit_tag_commit_hash": (
            local_bounded_approve_commit_tag_commit_hash
        ),
        "project_browser_autonomous_local_bounded_approve_commit_tag_tag_name": (
            local_bounded_approve_commit_tag_tag_name
        ),
        "project_browser_autonomous_local_bounded_approve_commit_tag_worktree_clean": (
            local_bounded_approve_commit_tag_worktree_clean
        ),
        "project_browser_autonomous_local_bounded_approve_commit_tag_gate_state_path": str(
            local_bounded_approve_commit_tag_gate_state_path
        ),
        "project_browser_autonomous_local_bounded_approve_commit_tag_execution_result_path": str(
            local_bounded_approve_commit_tag_execution_result_path
        ),
        "project_browser_autonomous_local_bounded_approve_commit_tag_execution_receipt_path": str(
            local_bounded_approve_commit_tag_execution_receipt_path
        ),
        "project_browser_autonomous_local_bounded_approve_commit_tag_plan_path": str(
            local_bounded_approve_commit_tag_plan_path
        ),
        "project_browser_autonomous_local_post_commit_cycle_closure_status": (
            local_post_commit_cycle_closure_status
        ),
        "project_browser_autonomous_local_post_commit_cycle_closure_blocked_reason": (
            local_post_commit_cycle_closure_blocked_reason
        ),
        "project_browser_autonomous_local_post_commit_cycle_closure_cycle_closed": (
            local_post_commit_cycle_closure_cycle_closed
        ),
        "project_browser_autonomous_local_post_commit_cycle_closure_reentry_allowed": (
            local_post_commit_cycle_closure_reentry_allowed
        ),
        "project_browser_autonomous_local_post_commit_cycle_closure_should_continue": (
            local_post_commit_cycle_closure_should_continue
        ),
        "project_browser_autonomous_local_post_commit_cycle_closure_cycle_decision": (
            local_post_commit_cycle_closure_cycle_decision
        ),
        "project_browser_autonomous_local_post_commit_cycle_closure_next_action": (
            local_post_commit_cycle_closure_next_action
        ),
        "project_browser_autonomous_local_post_commit_cycle_closure_commit_hash": (
            local_post_commit_cycle_closure_commit_hash
        ),
        "project_browser_autonomous_local_post_commit_cycle_closure_tag_name": (
            local_post_commit_cycle_closure_tag_name
        ),
        "project_browser_autonomous_local_post_commit_cycle_closure_no_change_cycle_closure": (
            local_post_commit_cycle_closure_no_change_cycle_closure
        ),
        "project_browser_autonomous_local_post_commit_cycle_closure_commit_required": (
            local_post_commit_cycle_closure_commit_required
        ),
        "project_browser_autonomous_local_post_commit_cycle_closure_tag_required": (
            local_post_commit_cycle_closure_tag_required
        ),
        "project_browser_autonomous_local_post_commit_cycle_closure_local_commit_tag_complete": (
            local_post_commit_cycle_closure_local_commit_tag_complete
        ),
        "project_browser_autonomous_local_next_cycle_reentry_status": (
            local_next_cycle_reentry_status
        ),
        "project_browser_autonomous_local_next_cycle_reentry_next_action": (
            local_next_cycle_reentry_next_action
        ),
        "project_browser_autonomous_local_next_cycle_reentry_selected_step_name": (
            local_next_cycle_reentry_selected_step_name
        ),
        "project_browser_autonomous_local_post_commit_cycle_closure_state_path": str(
            local_post_commit_cycle_closure_state_path
        ),
        "project_browser_autonomous_local_post_commit_cycle_closure_decision_path": str(
            local_post_commit_cycle_closure_decision_path
        ),
        "project_browser_autonomous_local_post_commit_cycle_closure_receipt_path": str(
            local_post_commit_cycle_closure_receipt_path
        ),
        "project_browser_autonomous_local_next_cycle_reentry_decision_path": str(
            local_next_cycle_reentry_decision_path
        ),
        "project_browser_autonomous_local_autonomous_continuation_status": (
            local_autonomous_continuation_status
        ),
        "project_browser_autonomous_local_autonomous_continuation_blocked_reason": (
            local_autonomous_continuation_blocked_reason
        ),
        "project_browser_autonomous_local_autonomous_continuation_next_action": (
            local_autonomous_continuation_next_action
        ),
        "project_browser_autonomous_local_autonomous_continuation_reentry_connected": (
            local_autonomous_continuation_reentry_connected
        ),
        "project_browser_autonomous_local_autonomous_continuation_next_cycle_ready": (
            local_autonomous_continuation_next_cycle_ready
        ),
        "project_browser_autonomous_local_autonomous_continuation_selected_step_name": (
            local_autonomous_continuation_selected_step_name
        ),
        "project_browser_autonomous_local_autonomous_loop_completion_status": (
            local_autonomous_loop_completion_status
        ),
        "project_browser_autonomous_local_autonomous_loop_completion_final_decision": (
            local_autonomous_loop_completion_final_decision
        ),
        "project_browser_autonomous_local_only_complete_autonomous_loop_ready": (
            local_only_complete_autonomous_loop_ready
        ),
        "project_browser_autonomous_local_autonomous_loop_complete": (
            local_autonomous_loop_complete
        ),
        "project_browser_autonomous_local_autonomous_continuation_no_change_cycle_closure": (
            local_autonomous_continuation_no_change_cycle_closure
        ),
        "project_browser_autonomous_local_autonomous_continuation_commit_required": (
            local_autonomous_continuation_commit_required
        ),
        "project_browser_autonomous_local_autonomous_continuation_tag_required": (
            local_autonomous_continuation_tag_required
        ),
        "project_browser_autonomous_local_autonomous_continuation_state_path": str(
            local_autonomous_continuation_state_path
        ),
        "project_browser_autonomous_local_autonomous_continuation_decision_path": str(
            local_autonomous_continuation_decision_path
        ),
        "project_browser_autonomous_local_autonomous_continuation_receipt_path": str(
            local_autonomous_continuation_receipt_path
        ),
        "project_browser_autonomous_local_autonomous_next_cycle_selection_path": str(
            local_autonomous_next_cycle_selection_path
        ),
        "project_browser_autonomous_local_autonomous_loop_completion_summary_path": str(
            local_autonomous_loop_completion_summary_path
        ),
        "project_browser_autonomous_approve_commit_tag_execution_enabled": (
            approve_commit_tag_execution_enabled
        ),
        "project_browser_autonomous_approve_commit_tag_execution_confirmed": (
            approve_commit_tag_execution_confirmed
        ),
        "project_browser_autonomous_approve_commit_tag_execution_gate_status": (
            approve_commit_tag_execution_gate_status
        ),
        "project_browser_autonomous_approve_commit_tag_execution_status": (
            approve_commit_tag_execution_status
        ),
        "project_browser_autonomous_approve_commit_tag_execution_attempted": (
            approve_commit_tag_execution_attempted
        ),
        "project_browser_autonomous_approve_commit_tag_execution_exit_code": (
            approve_commit_tag_execution_exit_code
        ),
        "project_browser_autonomous_approve_commit_tag_execution_blocked_reason": (
            approve_commit_tag_execution_blocked_reason
        ),
        "project_browser_autonomous_approve_commit_tag_execution_commit_message": (
            approve_commit_tag_execution_commit_message
        ),
        "project_browser_autonomous_approve_commit_tag_execution_tag_name": (
            approve_commit_tag_execution_tag_name
        ),
        "project_browser_autonomous_approve_commit_tag_execution_receipt_path": str(
            approve_commit_tag_execution_receipt_path
        ),
        "project_browser_autonomous_approve_commit_tag_execution_should_commit": (
            approve_commit_tag_execution_should_commit
        ),
        "project_browser_autonomous_approve_commit_tag_execution_should_tag": (
            approve_commit_tag_execution_should_tag
        ),
        "project_browser_autonomous_one_cycle_controller_completed_result_source_path": str(
            completed_result_source_path
        ),
        "project_browser_autonomous_one_cycle_controller_completed_result_source_status": (
            completed_result_source_status
        ),
        "project_browser_autonomous_one_cycle_controller_stop_reason": stop_reason,
        "project_browser_autonomous_one_cycle_controller_artifact_paths": artifact_paths,
        "project_browser_autonomous_one_cycle_controller_runtime_posture": runtime_posture,
        "project_browser_autonomous_one_cycle_controller_enabled": enabled,
        "project_browser_autonomous_one_cycle_controller_execute_enabled": execute_enabled,
        "project_browser_autonomous_one_cycle_controller_exec_plan_path": str(exec_plan_path),
        "project_browser_autonomous_one_cycle_controller_exec_plan_safety_status": (
            exec_plan_safety_status
        ),
        "project_browser_autonomous_one_cycle_controller_exec_plan_blocked_reason": (
            exec_plan_blocked_reason
        ),
        "project_browser_autonomous_one_cycle_controller_exec_plan_required_fragments_present": (
            exec_plan_required_fragments_present
        ),
        "project_browser_autonomous_one_cycle_controller_exec_plan_banned_fragments_present": (
            exec_plan_banned_fragments_present
        ),
        "project_browser_autonomous_one_cycle_controller_exec_plan_execution_status": (
            exec_plan_execution_status
        ),
        "project_browser_autonomous_one_cycle_controller_execution_attempted": (
            execution_attempted
        ),
        "project_browser_autonomous_one_cycle_controller_execution_blocked_reason": (
            execution_blocked_reason
        ),
        "project_browser_autonomous_one_cycle_controller_execution_gate_status": (
            execution_gate_status
        ),
        "project_browser_autonomous_one_cycle_controller_execution_exit_code": (
            execution_exit_code
        ),
        "project_browser_autonomous_one_cycle_controller_execution_stdout_path": str(
            execution_stdout_path
        ),
        "project_browser_autonomous_one_cycle_controller_execution_stderr_path": str(
            execution_stderr_path
        ),
        "project_browser_autonomous_one_cycle_controller_execution_runlog_path": str(
            execution_runlog_path
        ),
        "project_browser_autonomous_one_cycle_controller_execution_started_at": (
            execution_started_at
        ),
        "project_browser_autonomous_one_cycle_controller_execution_finished_at": (
            execution_finished_at
        ),
    }

def _build_project_browser_autonomous_multi_cycle_controller_readiness_state(
    *,
    approved_restart_payload: Mapping[str, Any] | None,
    prior_approved_restart_execution_payload: Mapping[str, Any] | None,
    dry_run: bool,
) -> dict[str, Any]:
    approved_restart = (
        dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    )
    prior_payload = (
        dict(prior_approved_restart_execution_payload)
        if isinstance(prior_approved_restart_execution_payload, Mapping)
        else {}
    )

    def _read_value(key: str) -> Any:
        if key in prior_payload:
            return prior_payload.get(key)
        return approved_restart.get(key)

    def _read_strict_flag(key: str, *, default: bool = False) -> bool:
        value = _read_value(key)
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

    multi_cycle_controller_dir = Path("/tmp/codex-local-runner-decision/multi_cycle_controller")
    cycle_history_path = multi_cycle_controller_dir / "multi_cycle_cycle_history.json"
    readiness_summary_path = (
        multi_cycle_controller_dir / "multi_cycle_controller_readiness_summary.md"
    )

    max_cycles_allowed = 2
    requested_cycles_value = _read_value(
        "project_browser_autonomous_multi_cycle_controller_max_cycles_requested"
    )
    if requested_cycles_value is None:
        requested_cycles_value = _read_value(
            "project_browser_autonomous_multi_cycle_controller_max_cycles"
        )
    max_cycles_requested = _as_optional_int(requested_cycles_value)
    if max_cycles_requested is None:
        max_cycles_requested = 2
    max_cycles_requested = max(0, int(max_cycles_requested))

    enabled = _read_strict_flag(
        "project_browser_autonomous_multi_cycle_controller_enabled",
        default=False,
    )
    execute_enabled = _read_strict_flag(
        "project_browser_autonomous_multi_cycle_controller_execute_enabled",
        default=False,
    )
    one_cycle_status = _normalize_text(
        _read_value("project_browser_autonomous_one_cycle_controller_status"),
        default="",
    )
    one_cycle_next_action = _normalize_text(
        _read_value("project_browser_autonomous_one_cycle_controller_next_action"),
        default="",
    )
    one_cycle_stop_reason = _normalize_text(
        _read_value("project_browser_autonomous_one_cycle_controller_stop_reason"),
        default="",
    )
    one_cycle_execution_gate_status = _normalize_text(
        _read_value("project_browser_autonomous_one_cycle_controller_execution_gate_status"),
        default="",
    )
    one_cycle_execution_blocked_reason = _normalize_text(
        _read_value("project_browser_autonomous_one_cycle_controller_execution_blocked_reason"),
        default="",
    )
    one_cycle_enabled = _read_strict_flag(
        "project_browser_autonomous_one_cycle_controller_enabled",
        default=False,
    )
    one_cycle_execute_enabled = _read_strict_flag(
        "project_browser_autonomous_one_cycle_controller_execute_enabled",
        default=False,
    )

    cycle_history_payload, history_invalid = _read_multi_cycle_history(
        cycle_history_path=cycle_history_path,
        max_cycles_allowed=max_cycles_allowed,
    )
    cycle_history_payload, _history_appended = _record_one_cycle_result_into_multi_cycle_history(
        history_payload=cycle_history_payload,
        one_cycle_state={
            "project_browser_autonomous_one_cycle_controller_status": one_cycle_status,
            "project_browser_autonomous_one_cycle_controller_next_action": one_cycle_next_action,
            "project_browser_autonomous_one_cycle_controller_execution_attempted": bool(
                _read_value("project_browser_autonomous_one_cycle_controller_execution_attempted")
            ),
            "project_browser_autonomous_one_cycle_controller_execution_exit_code": _read_value(
                "project_browser_autonomous_one_cycle_controller_execution_exit_code"
            ),
            "project_browser_autonomous_one_cycle_controller_exec_plan_execution_status": (
                _read_value("project_browser_autonomous_one_cycle_controller_exec_plan_execution_status")
            ),
            "project_browser_autonomous_one_cycle_controller_diff_capture_status": _read_value(
                "project_browser_autonomous_one_cycle_controller_diff_capture_status"
            ),
            "project_browser_autonomous_one_cycle_controller_review_request_status": _read_value(
                "project_browser_autonomous_one_cycle_controller_review_request_status"
            ),
            "project_browser_autonomous_one_cycle_controller_completed_result_source_path": (
                _read_value("project_browser_autonomous_one_cycle_controller_completed_result_source_path")
            ),
            "project_browser_autonomous_one_cycle_controller_review_request_path": _read_value(
                "project_browser_autonomous_one_cycle_controller_review_request_path"
            ),
            "project_browser_autonomous_one_cycle_controller_review_handoff_path": _read_value(
                "project_browser_autonomous_one_cycle_controller_review_handoff_path"
            ),
        },
        max_cycles_allowed=max_cycles_allowed,
    )

    cycles = (
        list(cycle_history_payload.get("cycles", []))
        if isinstance(cycle_history_payload.get("cycles"), list)
        else []
    )
    completed_cycle_count = min(
        _as_non_negative_int(
            cycle_history_payload.get("completed_cycle_count"),
            default=len(cycles),
        ),
        max_cycles_allowed,
    )
    current_cycle_index = min(
        _as_non_negative_int(
            cycle_history_payload.get("current_cycle_index"),
            default=completed_cycle_count,
        ),
        max_cycles_allowed,
    )
    cycle_history_status = _normalize_text(
        cycle_history_payload.get("status"),
        default="not_started",
    )
    if cycle_history_status not in {"not_started", "in_progress", "completed"}:
        cycle_history_status = "not_started"
    if not cycles:
        cycle_history_status = "not_started"

    remaining_cycle_count = max(
        0,
        min(max_cycles_requested, max_cycles_allowed) - completed_cycle_count,
    )
    can_continue = bool(enabled and execute_enabled and remaining_cycle_count > 0)
    next_cycle_allowed = False
    next_cycle_blocked_reason = "none"
    should_invoke_codex = False
    status = "multi_cycle_controller_ready"
    next_action = "enable_multi_cycle_controller"
    blocked_reason = "execution_not_enabled"
    stop_reason = "execution_not_enabled"

    if max_cycles_requested > max_cycles_allowed:
        status = "multi_cycle_controller_blocked"
        next_action = "manual_review_required"
        blocked_reason = "max_cycles_not_allowed"
        stop_reason = "max_cycles_not_allowed"
        can_continue = False
        next_cycle_blocked_reason = "max_cycles_not_allowed"
    elif not enabled:
        status = "multi_cycle_controller_ready"
        next_action = "enable_multi_cycle_controller"
        blocked_reason = "execution_not_enabled"
        stop_reason = "execution_not_enabled"
        can_continue = False
        next_cycle_blocked_reason = "execution_not_enabled"
    elif not execute_enabled:
        status = "multi_cycle_controller_ready"
        next_action = "enable_multi_cycle_controller_execution"
        blocked_reason = "execution_not_enabled"
        stop_reason = "execution_not_enabled"
        can_continue = False
        next_cycle_blocked_reason = "execution_not_enabled"
    elif completed_cycle_count >= max_cycles_allowed or remaining_cycle_count <= 0:
        status = "multi_cycle_controller_completed"
        next_action = "manual_review_required"
        blocked_reason = "cycle_limit_reached"
        stop_reason = "cycle_limit_reached"
        can_continue = False
        next_cycle_blocked_reason = "cycle_limit_reached"
    elif completed_cycle_count > 0:
        status = "multi_cycle_controller_waiting_for_review"
        next_action = "wait_for_chatgpt_diff_review_response"
        blocked_reason = "none"
        stop_reason = "review_required_before_next_cycle"
        can_continue = False
        next_cycle_blocked_reason = "review_required_before_next_cycle"
    elif dry_run:
        status = "multi_cycle_controller_ready"
        next_action = "prepare_bounded_two_cycle_execution"
        blocked_reason = "dry_run_execution_suppressed"
        stop_reason = "dry_run_execution_suppressed"
        can_continue = remaining_cycle_count > 0
        next_cycle_blocked_reason = "dry_run_execution_suppressed"
    elif not one_cycle_status or one_cycle_status == "insufficient_truth":
        status = "multi_cycle_controller_blocked"
        next_action = "manual_review_required"
        blocked_reason = "one_cycle_surface_missing"
        stop_reason = "one_cycle_surface_missing"
        can_continue = False
        next_cycle_blocked_reason = "one_cycle_surface_missing"
    elif one_cycle_status == "one_cycle_controller_blocked":
        status = "multi_cycle_controller_blocked"
        next_action = "manual_review_required"
        blocked_reason = (
            one_cycle_stop_reason
            if one_cycle_stop_reason in {
                "manual_review_required",
                "exec_plan_execution_failed",
                "exec_plan_not_safe",
                "exec_plan_missing",
                "staged_changes_present",
                "unstaged_changes_present",
            }
            else "manual_review_required"
        )
        stop_reason = blocked_reason
        can_continue = False
        next_cycle_blocked_reason = blocked_reason
    elif one_cycle_status == "one_cycle_controller_ready":
        status = "multi_cycle_controller_running"
        next_action = "run_next_bounded_cycle"
        blocked_reason = "none"
        stop_reason = "none"
        can_continue = remaining_cycle_count > 0
        next_cycle_allowed = bool(can_continue)
        next_cycle_blocked_reason = "none" if next_cycle_allowed else "cycle_limit_reached"
        should_invoke_codex = bool(
            can_continue
            and one_cycle_enabled
            and one_cycle_execute_enabled
            and one_cycle_execution_gate_status == "ready_for_single_execution"
            and one_cycle_execution_blocked_reason == "none"
        )
    elif one_cycle_status == "one_cycle_controller_completed":
        status = "multi_cycle_controller_waiting_for_review"
        next_action = "wait_for_chatgpt_diff_review_response"
        blocked_reason = "none"
        stop_reason = "review_required_before_next_cycle"
        can_continue = False
        next_cycle_blocked_reason = "review_required_before_next_cycle"
    else:
        status = "insufficient_truth"
        next_action = "insufficient_truth"
        blocked_reason = "insufficient_truth"
        stop_reason = "insufficient_truth"
        can_continue = False
        next_cycle_blocked_reason = "insufficient_truth"

    if dry_run:
        should_invoke_codex = False

    cycle_history_payload = {
        "status": (
            "completed"
            if completed_cycle_count >= int(max_cycles_allowed)
            else ("in_progress" if completed_cycle_count > 0 else "not_started")
        ),
        "max_cycles_allowed": int(max_cycles_allowed),
        "completed_cycle_count": int(completed_cycle_count),
        "current_cycle_index": int(current_cycle_index),
        "cycles": cycles[: int(max_cycles_allowed)],
    }
    if not cycles:
        cycle_history_payload["status"] = "not_started"
    cycle_history_status = _normalize_text(
        cycle_history_payload.get("status"),
        default=cycle_history_status,
    )

    if history_invalid:
        next_cycle_allowed = False

    history_write_failed = False
    try:
        multi_cycle_controller_dir.mkdir(parents=True, exist_ok=True)
        _write_multi_cycle_history(
            cycle_history_path=cycle_history_path,
            payload=cycle_history_payload,
        )
    except OSError:
        history_write_failed = True
        status = "multi_cycle_controller_blocked"
        next_action = "manual_review_required"
        blocked_reason = "cycle_history_write_failed"
        stop_reason = "cycle_history_write_failed"
        can_continue = False
        next_cycle_allowed = False
        next_cycle_blocked_reason = "cycle_history_write_failed"
        should_invoke_codex = False

    last_cycle = cycles[-1] if cycles else {}
    last_cycle_status = _normalize_text(last_cycle.get("one_cycle_status"), default="")
    last_cycle_next_action = _normalize_text(last_cycle.get("one_cycle_next_action"), default="")
    last_cycle_review_request_status = _normalize_text(
        last_cycle.get("review_request_status"),
        default="",
    )
    last_cycle_diff_capture_status = _normalize_text(
        last_cycle.get("diff_capture_status"),
        default="",
    )

    controller_allowed = bool(
        enabled
        and execute_enabled
        and can_continue
        and status in {"multi_cycle_controller_ready", "multi_cycle_controller_running"}
    )
    should_stop = stop_reason != "none"
    runtime_posture = [
        "prompt301_bounded_two_cycle_controller",
        "single_invocation_single_cycle_execution_cap",
        "bounded_max_cycles_2",
        "no_implicit_second_cycle_execution",
        "review_handoff_required_before_next_cycle",
        "no_codex_direct_execution_path_added",
        "no_exec_plan_direct_execution_path_added",
        "no_commit_tag_push_pr_merge",
    ]
    remaining_cycles = int(remaining_cycle_count)

    summary_lines = [
        "# Multi Cycle Controller Readiness",
        "",
        f"- Status: `{status}`",
        f"- Next action: `{next_action}`",
        f"- Enabled: `{str(enabled).lower()}`",
        f"- Execute enabled: `{str(execute_enabled).lower()}`",
        f"- Current cycle index: `{current_cycle_index}`",
        f"- Completed cycle count: `{completed_cycle_count}`",
        f"- Remaining cycle count: `{remaining_cycle_count}`",
        f"- Max cycles requested: `{max_cycles_requested}`",
        f"- Max cycles allowed: `{max_cycles_allowed}`",
        f"- Can continue: `{str(can_continue).lower()}`",
        f"- Cycle history status: `{cycle_history_status}`",
        f"- Next cycle allowed: `{str(next_cycle_allowed).lower()}`",
        f"- Next cycle blocked reason: `{next_cycle_blocked_reason}`",
        f"- Should invoke codex: `{str(should_invoke_codex).lower()}`",
        f"- Blocked reason: `{blocked_reason}`",
        f"- Stop reason: `{stop_reason}`",
        "",
        "## Output Artifacts",
        f"- multi_cycle_controller_readiness_summary.md: `{readiness_summary_path}`",
        f"- multi_cycle_cycle_history.json: `{cycle_history_path}`",
    ]

    if not history_write_failed:
        try:
            readiness_summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
        except OSError:
            status = "multi_cycle_controller_blocked"
            next_action = "manual_review_required"
            blocked_reason = "cycle_history_write_failed"
            stop_reason = "cycle_history_write_failed"
            can_continue = False
            next_cycle_allowed = False
            next_cycle_blocked_reason = "cycle_history_write_failed"
            should_invoke_codex = False

    return {
        "project_browser_autonomous_multi_cycle_controller_status": status,
        "project_browser_autonomous_multi_cycle_controller_next_action": next_action,
        "project_browser_autonomous_multi_cycle_controller_enabled": enabled,
        "project_browser_autonomous_multi_cycle_controller_execute_enabled": (
            execute_enabled
        ),
        "project_browser_autonomous_multi_cycle_controller_current_cycle_index": int(
            current_cycle_index
        ),
        "project_browser_autonomous_multi_cycle_controller_completed_cycle_count": int(
            completed_cycle_count
        ),
        "project_browser_autonomous_multi_cycle_controller_max_cycles_requested": int(
            max_cycles_requested
        ),
        "project_browser_autonomous_multi_cycle_controller_max_cycles_allowed": int(
            max_cycles_allowed
        ),
        "project_browser_autonomous_multi_cycle_controller_cycle_history_path": str(
            cycle_history_path
        ),
        "project_browser_autonomous_multi_cycle_controller_cycle_history_status": (
            cycle_history_status
        ),
        "project_browser_autonomous_multi_cycle_controller_blocked_reason": blocked_reason,
        "project_browser_autonomous_multi_cycle_controller_stop_reason": stop_reason,
        "project_browser_autonomous_multi_cycle_controller_can_continue": bool(can_continue),
        "project_browser_autonomous_multi_cycle_controller_remaining_cycle_count": int(
            remaining_cycle_count
        ),
        "project_browser_autonomous_multi_cycle_controller_last_cycle_status": (
            last_cycle_status
        ),
        "project_browser_autonomous_multi_cycle_controller_last_cycle_next_action": (
            last_cycle_next_action
        ),
        "project_browser_autonomous_multi_cycle_controller_last_cycle_review_request_status": (
            last_cycle_review_request_status
        ),
        "project_browser_autonomous_multi_cycle_controller_last_cycle_diff_capture_status": (
            last_cycle_diff_capture_status
        ),
        "project_browser_autonomous_multi_cycle_controller_next_cycle_allowed": bool(
            next_cycle_allowed
        ),
        "project_browser_autonomous_multi_cycle_controller_next_cycle_blocked_reason": (
            next_cycle_blocked_reason
        ),
        "project_browser_autonomous_multi_cycle_controller_should_invoke_codex": bool(
            should_invoke_codex
        ),
        "project_browser_autonomous_multi_cycle_controller_readiness_summary_path": str(
            readiness_summary_path
        ),
        "project_browser_autonomous_multi_cycle_controller_controller_allowed": bool(
            controller_allowed
        ),
        "project_browser_autonomous_multi_cycle_controller_controller_block_reason": (
            blocked_reason if blocked_reason != "none" else ""
        ),
        "project_browser_autonomous_multi_cycle_controller_controller_source": (
            "prompt301_bounded_two_cycle_controller"
        ),
        "project_browser_autonomous_multi_cycle_controller_latest_authoritative_stage": (
            "one_cycle_controller_surface"
        ),
        "project_browser_autonomous_multi_cycle_controller_latest_cycle_status": (
            _normalize_text(one_cycle_status, default="insufficient_truth")
        ),
        "project_browser_autonomous_multi_cycle_controller_latest_validation_passed": False,
        "project_browser_autonomous_multi_cycle_controller_latest_commit_tag_status": (
            "insufficient_truth"
        ),
        "project_browser_autonomous_multi_cycle_controller_latest_rollback_status": (
            "insufficient_truth"
        ),
        "project_browser_autonomous_multi_cycle_controller_latest_human_review_required": bool(
            next_action == "manual_review_required"
        ),
        "project_browser_autonomous_multi_cycle_controller_cycle_index": int(
            current_cycle_index
        ),
        "project_browser_autonomous_multi_cycle_controller_max_cycles": int(max_cycles_allowed),
        "project_browser_autonomous_multi_cycle_controller_remaining_cycles": int(
            remaining_cycles
        ),
        "project_browser_autonomous_multi_cycle_controller_fix_attempt_index": 0,
        "project_browser_autonomous_multi_cycle_controller_max_fix_attempts": 1,
        "project_browser_autonomous_multi_cycle_controller_remaining_fix_attempts": 1,
        "project_browser_autonomous_multi_cycle_controller_rollback_attempt_index": 0,
        "project_browser_autonomous_multi_cycle_controller_max_rollback_attempts": 1,
        "project_browser_autonomous_multi_cycle_controller_remaining_rollback_attempts": 1,
        "project_browser_autonomous_multi_cycle_controller_codex_invocation_count": 0,
        "project_browser_autonomous_multi_cycle_controller_max_codex_invocations": 3,
        "project_browser_autonomous_multi_cycle_controller_remaining_codex_invocations": 3,
        "project_browser_autonomous_multi_cycle_controller_commit_count": 0,
        "project_browser_autonomous_multi_cycle_controller_max_commits": 1,
        "project_browser_autonomous_multi_cycle_controller_remaining_commits": 1,
        "project_browser_autonomous_multi_cycle_controller_next_prompt_kind": "none",
        "project_browser_autonomous_multi_cycle_controller_fix_continuation_allowed": False,
        "project_browser_autonomous_multi_cycle_controller_rollback_path_allowed": False,
        "project_browser_autonomous_multi_cycle_controller_github_handoff_allowed": False,
        "project_browser_autonomous_multi_cycle_controller_manual_review_required": bool(
            next_action == "manual_review_required"
        ),
        "project_browser_autonomous_multi_cycle_controller_should_generate_next_prompt": False,
        "project_browser_autonomous_multi_cycle_controller_should_generate_fix_prompt": False,
        "project_browser_autonomous_multi_cycle_controller_should_validate": False,
        "project_browser_autonomous_multi_cycle_controller_should_prepare_rollback": False,
        "project_browser_autonomous_multi_cycle_controller_should_execute_rollback": False,
        "project_browser_autonomous_multi_cycle_controller_should_prepare_commit": False,
        "project_browser_autonomous_multi_cycle_controller_should_execute_commit": False,
        "project_browser_autonomous_multi_cycle_controller_should_prepare_github_handoff": (
            False
        ),
        "project_browser_autonomous_multi_cycle_controller_should_push": False,
        "project_browser_autonomous_multi_cycle_controller_should_stop": bool(should_stop),
        "project_browser_autonomous_multi_cycle_controller_runtime_posture": runtime_posture,
        "project_browser_autonomous_multi_cycle_controller_missing_inputs": [],
    }

def _build_project_browser_autonomous_multi_cycle_controller_state(
    *,
    commit_tag_result_status: str,
    commit_tag_result_class: str,
    commit_tag_result_block_reason: str,
    commit_tag_result_handoff_allowed: bool,
    commit_tag_result_safe_handoff: bool,
    commit_tag_result_post_commit_dirty: bool,
    commit_tag_result_human_review_required: bool,
    commit_tag_result_stop_reason: str,
    commit_tag_result_next_action: str,
    commit_tag_result_should_prepare_next_cycle: bool,
    commit_tag_result_should_prepare_github_handoff: bool,
    commit_tag_result_commit_completed: bool,
    commit_tag_result_tag_completed: bool,
    commit_tag_result_should_stop: bool,
    commit_tag_execution_status: str,
    commit_tag_readiness_status: str,
    post_rollback_fix_reentry_result_status: str,
    post_rollback_fix_reentry_validation_passed: bool,
    post_rollback_fix_reentry_cycle_passed: bool,
    post_rollback_fix_reentry_commit_candidate: bool,
    post_rollback_fix_reentry_cycle_failed: bool,
    post_rollback_fix_reentry_cycle_blocked: bool,
    post_rollback_fix_reentry_rollback_candidate: bool,
    post_rollback_fix_reentry_human_review_required: bool,
    bounded_continuation_status: str,
    bounded_continuation_remaining_cycles: int,
    bounded_continuation_remaining_fix_attempts: int,
    bounded_continuation_human_review_required: bool,
    one_step_cycle_status: str,
    one_step_cycle_passed: bool,
    one_step_cycle_failed: bool,
    one_step_cycle_blocked: bool,
    one_step_cycle_human_review_required: bool,
    rollback_result_status: str,
    rollback_result_human_review_required: bool,
    post_rollback_continuation_status: str,
    post_rollback_continuation_human_review_required: bool,
    post_rollback_fix_reentry_execution_attempted: bool,
    codex_write_invocation_attempted: bool,
    codex_reentry_invocation_attempted: bool,
) -> dict[str, Any]:
    allowed_statuses = {
        "multi_cycle_controller_next_cycle_ready",
        "multi_cycle_controller_completed_cycle_budget_exhausted",
        "multi_cycle_controller_blocked_commit_tag_result",
        "multi_cycle_controller_prepare_commit",
        "multi_cycle_controller_fix_ready",
        "multi_cycle_controller_rollback_ready",
        "multi_cycle_controller_blocked_codex_budget_exhausted",
        "multi_cycle_controller_blocked_fix_budget_exhausted",
        "multi_cycle_controller_blocked_rollback_budget_exhausted",
        "multi_cycle_controller_blocked_manual_review",
        "multi_cycle_controller_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "generate_next_prompt",
        "generate_fix_prompt",
        "prepare_rollback_readiness",
        "prepare_commit_tag_readiness",
        "prepare_github_handoff_readiness",
        "manual_review_required",
        "stop_bounded_autonomous_loop",
        "wait_for_more_truth",
        "insufficient_truth",
    }
    runtime_posture = [
        "prompt197_multi_cycle_controller",
        "metadata_only_controller",
        "no_execution",
        "no_git_mutation",
        "no_codex_invocation",
        "no_rollback_execution",
        "no_loop_start",
    ]

    normalized_commit_tag_result_status = _normalize_text(
        commit_tag_result_status,
        default="insufficient_truth",
    )
    normalized_commit_tag_result_class = _normalize_text(
        commit_tag_result_class,
        default="insufficient_truth",
    )
    normalized_commit_tag_result_block_reason = _normalize_text(
        commit_tag_result_block_reason,
        default="",
    )
    normalized_commit_tag_result_stop_reason = _normalize_text(
        commit_tag_result_stop_reason,
        default="",
    )
    normalized_commit_tag_result_next_action = _normalize_text(
        commit_tag_result_next_action,
        default="",
    )
    normalized_commit_tag_execution_status = _normalize_text(
        commit_tag_execution_status,
        default="insufficient_truth",
    )
    normalized_commit_tag_readiness_status = _normalize_text(
        commit_tag_readiness_status,
        default="insufficient_truth",
    )
    normalized_post_rollback_fix_reentry_result_status = _normalize_text(
        post_rollback_fix_reentry_result_status,
        default="insufficient_truth",
    )
    normalized_bounded_continuation_status = _normalize_text(
        bounded_continuation_status,
        default="insufficient_truth",
    )
    normalized_one_step_cycle_status = _normalize_text(
        one_step_cycle_status,
        default="insufficient_truth",
    )
    normalized_rollback_result_status = _normalize_text(
        rollback_result_status,
        default="insufficient_truth",
    )
    normalized_post_rollback_continuation_status = _normalize_text(
        post_rollback_continuation_status,
        default="insufficient_truth",
    )

    # Budget defaults / derivation
    max_cycles = 2
    cycle_index = max(1, max_cycles - _as_non_negative_int(bounded_continuation_remaining_cycles, default=1))
    remaining_cycles = max(max_cycles - cycle_index, 0)

    max_fix_attempts = 1
    fix_attempt_index = max(
        0,
        max_fix_attempts - _as_non_negative_int(bounded_continuation_remaining_fix_attempts, default=1),
    )
    remaining_fix_attempts = max(max_fix_attempts - fix_attempt_index, 0)

    max_rollback_attempts = 1
    rollback_attempt_index = (
        1
        if (
            normalized_rollback_result_status
            and normalized_rollback_result_status != "insufficient_truth"
        )
        else 0
    )
    remaining_rollback_attempts = max(max_rollback_attempts - rollback_attempt_index, 0)

    max_codex_invocations = 3
    codex_invocation_count = int(bool(codex_write_invocation_attempted)) + int(
        bool(codex_reentry_invocation_attempted)
    ) + int(bool(post_rollback_fix_reentry_execution_attempted))
    remaining_codex_invocations = max(max_codex_invocations - codex_invocation_count, 0)

    max_commits = 1
    commit_count = (
        1
        if (
            normalized_commit_tag_result_class == "completed"
            and bool(commit_tag_result_commit_completed)
            and bool(commit_tag_result_tag_completed)
        )
        else 0
    )
    remaining_commits = max(max_commits - commit_count, 0)

    latest_authoritative_stage = "none"
    latest_cycle_status = "insufficient_truth"
    latest_validation_passed = False
    latest_commit_tag_status = normalized_commit_tag_result_status
    latest_rollback_status = normalized_rollback_result_status
    latest_human_review_required = False
    controller_source = "none"

    if normalized_commit_tag_result_status and normalized_commit_tag_result_status != "insufficient_truth":
        latest_authoritative_stage = "commit_tag_result_assimilation"
        latest_cycle_status = normalized_post_rollback_fix_reentry_result_status
        latest_validation_passed = bool(post_rollback_fix_reentry_validation_passed)
        latest_human_review_required = bool(commit_tag_result_human_review_required)
        controller_source = "prompt196_commit_tag_result_assimilation"
    elif (
        normalized_post_rollback_fix_reentry_result_status
        and normalized_post_rollback_fix_reentry_result_status != "insufficient_truth"
    ):
        latest_authoritative_stage = "post_rollback_fix_reentry_result_assimilation"
        latest_cycle_status = normalized_post_rollback_fix_reentry_result_status
        latest_validation_passed = bool(post_rollback_fix_reentry_validation_passed)
        latest_human_review_required = bool(post_rollback_fix_reentry_human_review_required)
        controller_source = "prompt193_post_rollback_fix_reentry_result_assimilation"
    elif (
        normalized_rollback_result_status and normalized_rollback_result_status != "insufficient_truth"
    ) or (
        normalized_post_rollback_continuation_status
        and normalized_post_rollback_continuation_status != "insufficient_truth"
    ):
        latest_authoritative_stage = "rollback_posture"
        latest_cycle_status = normalized_post_rollback_continuation_status or normalized_rollback_result_status
        latest_validation_passed = False
        latest_human_review_required = bool(
            rollback_result_human_review_required or post_rollback_continuation_human_review_required
        )
        controller_source = "prompt186_187_rollback_path"
    elif normalized_bounded_continuation_status and normalized_bounded_continuation_status != "insufficient_truth":
        latest_authoritative_stage = "bounded_continuation_controller"
        latest_cycle_status = normalized_bounded_continuation_status
        latest_validation_passed = False
        latest_human_review_required = bool(bounded_continuation_human_review_required)
        controller_source = "prompt183_bounded_continuation"
    else:
        latest_authoritative_stage = "one_step_cycle"
        latest_cycle_status = normalized_one_step_cycle_status
        latest_validation_passed = False
        latest_human_review_required = bool(one_step_cycle_human_review_required)
        controller_source = "prompt172_173_one_step_cycle"

    status = "multi_cycle_controller_blocked_insufficient_truth"
    controller_allowed = False
    controller_block_reason = "blocked_insufficient_multi_cycle_truth"
    next_prompt_kind = "none"
    next_cycle_allowed = False
    fix_continuation_allowed = False
    rollback_path_allowed = False
    github_handoff_allowed = False
    manual_review_required = False
    should_generate_next_prompt = False
    should_generate_fix_prompt = False
    should_invoke_codex = False
    should_validate = False
    should_prepare_rollback = False
    should_execute_rollback = False
    should_prepare_commit = False
    should_execute_commit = False
    should_prepare_github_handoff = False
    should_push = False
    should_stop = True
    stop_reason = "insufficient_multi_cycle_truth"
    next_action = "manual_review_required"
    missing_inputs: list[str] = []

    commit_tag_failure_or_unsafe = bool(
        normalized_commit_tag_result_status
        in {
            "commit_tag_result_assimilation_partial_commit_tag_failed",
            "commit_tag_result_assimilation_failed_git_add",
            "commit_tag_result_assimilation_failed_git_commit",
            "commit_tag_result_assimilation_failed_git_tag",
            "commit_tag_result_assimilation_timeout",
            "commit_tag_result_assimilation_blocked_insufficient_truth",
            "commit_tag_result_assimilation_completed_with_unexpected_dirty",
        }
        or normalized_commit_tag_result_class
        in {
            "partial_commit_tag_failed",
            "failed_git_add",
            "failed_git_commit",
            "failed_git_tag",
            "timeout",
            "blocked",
            "insufficient_truth",
            "completed_unexpected_dirty",
        }
    )

    validation_failed_like = bool(
        post_rollback_fix_reentry_cycle_failed
        or one_step_cycle_failed
        or normalized_post_rollback_fix_reentry_result_status
        in {
            "post_rollback_fix_reentry_result_validation_failed",
            "post_rollback_fix_reentry_result_completed_failure",
        }
    )

    rollback_needed = bool(
        post_rollback_fix_reentry_rollback_candidate
        or normalized_post_rollback_fix_reentry_result_status
        in {
            "post_rollback_fix_reentry_result_blocked_unsafe_changes",
            "post_rollback_fix_reentry_result_validation_timeout",
            "post_rollback_fix_reentry_result_completed_timeout",
        }
    )

    # deterministic priority
    if latest_human_review_required:
        status = "multi_cycle_controller_blocked_manual_review"
        controller_allowed = False
        controller_block_reason = "manual_review_required"
        manual_review_required = True
        should_stop = True
        stop_reason = "manual_review_required"
        next_action = "manual_review_required"
    elif commit_tag_failure_or_unsafe:
        status = "multi_cycle_controller_blocked_commit_tag_result"
        controller_allowed = False
        controller_block_reason = (
            normalized_commit_tag_result_stop_reason
            or normalized_commit_tag_result_block_reason
            or "commit_tag_result_not_safe"
        )
        manual_review_required = True
        should_stop = True
        stop_reason = (
            normalized_commit_tag_result_stop_reason
            or normalized_commit_tag_result_block_reason
            or "commit_tag_result_not_safe"
        )
        next_action = "manual_review_required"
    elif remaining_codex_invocations <= 0:
        status = "multi_cycle_controller_blocked_codex_budget_exhausted"
        controller_allowed = False
        controller_block_reason = "codex_invocation_budget_exhausted"
        should_stop = True
        stop_reason = "codex_invocation_budget_exhausted"
        next_action = "stop_bounded_autonomous_loop"
    elif validation_failed_like and remaining_fix_attempts <= 0:
        status = "multi_cycle_controller_blocked_fix_budget_exhausted"
        controller_allowed = False
        controller_block_reason = "fix_budget_exhausted"
        manual_review_required = True
        should_stop = True
        stop_reason = "fix_budget_exhausted"
        next_action = "manual_review_required"
    elif rollback_needed and remaining_rollback_attempts <= 0:
        status = "multi_cycle_controller_blocked_rollback_budget_exhausted"
        controller_allowed = False
        controller_block_reason = "rollback_budget_exhausted"
        manual_review_required = True
        should_stop = True
        stop_reason = "rollback_budget_exhausted"
        next_action = "manual_review_required"
    elif (
        normalized_commit_tag_result_class == "completed"
        and bool(commit_tag_result_safe_handoff)
        and bool(commit_tag_result_handoff_allowed)
        and not bool(commit_tag_result_human_review_required)
        and not bool(commit_tag_result_post_commit_dirty)
    ):
        if remaining_cycles > 0:
            status = "multi_cycle_controller_next_cycle_ready"
            controller_allowed = True
            controller_block_reason = ""
            next_cycle_allowed = True
            next_prompt_kind = "next"
            should_generate_next_prompt = True
            should_generate_fix_prompt = False
            should_invoke_codex = False
            should_validate = False
            should_prepare_rollback = False
            should_execute_rollback = False
            should_prepare_commit = False
            should_execute_commit = False
            should_prepare_github_handoff = False
            should_push = False
            should_stop = False
            stop_reason = ""
            next_action = "generate_next_prompt"
        else:
            status = "multi_cycle_controller_completed_cycle_budget_exhausted"
            controller_allowed = False
            controller_block_reason = "cycle_budget_exhausted_after_commit"
            next_cycle_allowed = False
            should_stop = True
            stop_reason = "cycle_budget_exhausted_after_commit"
            next_action = "stop_bounded_autonomous_loop"
    elif (
        bool(post_rollback_fix_reentry_validation_passed)
        and bool(post_rollback_fix_reentry_commit_candidate)
        and normalized_commit_tag_result_class != "completed"
    ):
        status = "multi_cycle_controller_prepare_commit"
        controller_allowed = True
        controller_block_reason = ""
        should_prepare_commit = True
        should_execute_commit = False
        should_stop = False
        stop_reason = ""
        next_action = "prepare_commit_tag_readiness"
    elif rollback_needed and remaining_rollback_attempts > 0 and not latest_human_review_required:
        status = "multi_cycle_controller_rollback_ready"
        controller_allowed = True
        controller_block_reason = ""
        rollback_path_allowed = True
        should_prepare_rollback = True
        should_execute_rollback = False
        should_stop = False
        stop_reason = ""
        next_action = "prepare_rollback_readiness"
    elif validation_failed_like and remaining_fix_attempts > 0 and not latest_human_review_required:
        status = "multi_cycle_controller_fix_ready"
        controller_allowed = True
        controller_block_reason = ""
        fix_continuation_allowed = True
        next_prompt_kind = "fix"
        should_generate_fix_prompt = True
        should_generate_next_prompt = False
        should_invoke_codex = False
        should_stop = False
        stop_reason = ""
        next_action = "generate_fix_prompt"
    else:
        status = "multi_cycle_controller_blocked_insufficient_truth"
        controller_allowed = False
        controller_block_reason = "blocked_insufficient_multi_cycle_truth"
        should_stop = True
        stop_reason = "insufficient_multi_cycle_truth"
        manual_review_required = True
        next_action = "manual_review_required"

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"
    if status == "insufficient_truth":
        controller_allowed = False
        controller_block_reason = "blocked_insufficient_multi_cycle_truth"
        should_stop = True
        stop_reason = "insufficient_multi_cycle_truth"
        manual_review_required = True
        should_generate_next_prompt = False
        should_generate_fix_prompt = False
        should_invoke_codex = False
        should_validate = False
        should_prepare_rollback = False
        should_execute_rollback = False
        should_prepare_commit = False
        should_execute_commit = False
        should_prepare_github_handoff = False
        should_push = False

    return {
        "project_browser_autonomous_multi_cycle_controller_status": status,
        "project_browser_autonomous_multi_cycle_controller_controller_allowed": bool(
            controller_allowed
        ),
        "project_browser_autonomous_multi_cycle_controller_controller_block_reason": (
            controller_block_reason
        ),
        "project_browser_autonomous_multi_cycle_controller_controller_source": controller_source,
        "project_browser_autonomous_multi_cycle_controller_latest_authoritative_stage": (
            latest_authoritative_stage
        ),
        "project_browser_autonomous_multi_cycle_controller_latest_cycle_status": (
            latest_cycle_status
        ),
        "project_browser_autonomous_multi_cycle_controller_latest_validation_passed": bool(
            latest_validation_passed
        ),
        "project_browser_autonomous_multi_cycle_controller_latest_commit_tag_status": (
            latest_commit_tag_status
        ),
        "project_browser_autonomous_multi_cycle_controller_latest_rollback_status": (
            latest_rollback_status
        ),
        "project_browser_autonomous_multi_cycle_controller_latest_human_review_required": bool(
            latest_human_review_required
        ),
        "project_browser_autonomous_multi_cycle_controller_cycle_index": int(cycle_index),
        "project_browser_autonomous_multi_cycle_controller_max_cycles": int(max_cycles),
        "project_browser_autonomous_multi_cycle_controller_remaining_cycles": int(
            remaining_cycles
        ),
        "project_browser_autonomous_multi_cycle_controller_fix_attempt_index": int(
            fix_attempt_index
        ),
        "project_browser_autonomous_multi_cycle_controller_max_fix_attempts": int(
            max_fix_attempts
        ),
        "project_browser_autonomous_multi_cycle_controller_remaining_fix_attempts": int(
            remaining_fix_attempts
        ),
        "project_browser_autonomous_multi_cycle_controller_rollback_attempt_index": int(
            rollback_attempt_index
        ),
        "project_browser_autonomous_multi_cycle_controller_max_rollback_attempts": int(
            max_rollback_attempts
        ),
        "project_browser_autonomous_multi_cycle_controller_remaining_rollback_attempts": int(
            remaining_rollback_attempts
        ),
        "project_browser_autonomous_multi_cycle_controller_codex_invocation_count": int(
            codex_invocation_count
        ),
        "project_browser_autonomous_multi_cycle_controller_max_codex_invocations": int(
            max_codex_invocations
        ),
        "project_browser_autonomous_multi_cycle_controller_remaining_codex_invocations": int(
            remaining_codex_invocations
        ),
        "project_browser_autonomous_multi_cycle_controller_commit_count": int(commit_count),
        "project_browser_autonomous_multi_cycle_controller_max_commits": int(max_commits),
        "project_browser_autonomous_multi_cycle_controller_remaining_commits": int(
            remaining_commits
        ),
        "project_browser_autonomous_multi_cycle_controller_next_prompt_kind": next_prompt_kind,
        "project_browser_autonomous_multi_cycle_controller_next_cycle_allowed": bool(
            next_cycle_allowed
        ),
        "project_browser_autonomous_multi_cycle_controller_fix_continuation_allowed": bool(
            fix_continuation_allowed
        ),
        "project_browser_autonomous_multi_cycle_controller_rollback_path_allowed": bool(
            rollback_path_allowed
        ),
        "project_browser_autonomous_multi_cycle_controller_github_handoff_allowed": bool(
            github_handoff_allowed
        ),
        "project_browser_autonomous_multi_cycle_controller_manual_review_required": bool(
            manual_review_required
        ),
        "project_browser_autonomous_multi_cycle_controller_should_generate_next_prompt": bool(
            should_generate_next_prompt
        ),
        "project_browser_autonomous_multi_cycle_controller_should_generate_fix_prompt": bool(
            should_generate_fix_prompt
        ),
        "project_browser_autonomous_multi_cycle_controller_should_invoke_codex": bool(
            should_invoke_codex
        ),
        "project_browser_autonomous_multi_cycle_controller_should_validate": bool(
            should_validate
        ),
        "project_browser_autonomous_multi_cycle_controller_should_prepare_rollback": bool(
            should_prepare_rollback
        ),
        "project_browser_autonomous_multi_cycle_controller_should_execute_rollback": bool(
            should_execute_rollback
        ),
        "project_browser_autonomous_multi_cycle_controller_should_prepare_commit": bool(
            should_prepare_commit
        ),
        "project_browser_autonomous_multi_cycle_controller_should_execute_commit": bool(
            should_execute_commit
        ),
        "project_browser_autonomous_multi_cycle_controller_should_prepare_github_handoff": bool(
            should_prepare_github_handoff
        ),
        "project_browser_autonomous_multi_cycle_controller_should_push": bool(should_push),
        "project_browser_autonomous_multi_cycle_controller_should_stop": bool(should_stop),
        "project_browser_autonomous_multi_cycle_controller_stop_reason": stop_reason,
        "project_browser_autonomous_multi_cycle_controller_next_action": next_action,
        "project_browser_autonomous_multi_cycle_controller_runtime_posture": runtime_posture,
        "project_browser_autonomous_multi_cycle_controller_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_commit_tag_result_status,
                    normalized_commit_tag_result_class,
                    normalized_commit_tag_result_block_reason,
                    normalized_commit_tag_result_stop_reason,
                    normalized_commit_tag_result_next_action,
                    normalized_commit_tag_execution_status,
                    normalized_commit_tag_readiness_status,
                    normalized_post_rollback_fix_reentry_result_status,
                    normalized_bounded_continuation_status,
                    normalized_one_step_cycle_status,
                    normalized_rollback_result_status,
                    normalized_post_rollback_continuation_status,
                    "post_commit_dirty_true"
                    if commit_tag_result_post_commit_dirty and normalized_commit_tag_result_class == "completed"
                    else "",
                    "remaining_cycles_zero" if remaining_cycles <= 0 else "",
                    "remaining_fix_attempts_zero" if remaining_fix_attempts <= 0 else "",
                    "remaining_rollback_attempts_zero" if remaining_rollback_attempts <= 0 else "",
                    "remaining_codex_invocations_zero" if remaining_codex_invocations <= 0 else "",
                    *missing_inputs,
                ]
            )
        ),
    }

def _build_project_browser_autonomous_one_step_cycle_state(
    *,
    source_selection_status: str,
    selected_prompt_kind: str,
    selected_prompt_ready: bool,
    source_invocation_readiness_status: str,
    codex_invocation_allowed: bool,
    source_write_invocation_status: str,
    write_invocation_attempted: bool,
    codex_write_completed: bool,
    write_invocation_result_status: str,
    smoke_override_status: str,
    smoke_override_used: bool,
    source_assimilation_status: str,
    assimilation_result_class: str,
    assimilation_safe_for_validation_routing: bool,
    source_validation_routing_status: str,
    validation_allowed: bool,
    source_validation_routing_block_reason: str,
    source_validation_execution_status: str,
    validation_executed: bool,
    validation_passed: bool,
    validation_failed: bool,
    source_validation_execution_block_reason: str,
    selection_human_review_required: bool,
    invocation_human_review_required: bool,
    write_human_review_required: bool,
    assimilation_human_review_required: bool,
    routing_human_review_required: bool,
    validation_execution_human_review_required: bool,
) -> dict[str, Any]:
    normalized_source_selection_status = _normalize_text(
        source_selection_status,
        default="insufficient_truth",
    )
    normalized_selected_prompt_kind = _normalize_text(selected_prompt_kind, default="none")
    if normalized_selected_prompt_kind not in {"fix", "next", "none"}:
        normalized_selected_prompt_kind = "none"
    normalized_source_invocation_readiness_status = _normalize_text(
        source_invocation_readiness_status,
        default="insufficient_truth",
    )
    normalized_source_write_invocation_status = _normalize_text(
        source_write_invocation_status,
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
    normalized_source_assimilation_status = _normalize_text(
        source_assimilation_status,
        default="insufficient_truth",
    )
    normalized_assimilation_result_class = _normalize_text(
        assimilation_result_class,
        default="insufficient_truth",
    )
    normalized_source_validation_routing_status = _normalize_text(
        source_validation_routing_status,
        default="insufficient_truth",
    )
    normalized_source_validation_execution_status = _normalize_text(
        source_validation_execution_status,
        default="insufficient_truth",
    )
    normalized_source_validation_routing_block_reason = _normalize_text(
        source_validation_routing_block_reason,
        default="",
    )
    normalized_source_validation_execution_block_reason = _normalize_text(
        source_validation_execution_block_reason,
        default="",
    )
    prompt167_write_completed_explicit = bool(
        normalized_write_invocation_result_status
        in {"completed_with_changes", "completed_no_changes"}
    )
    prompt169_write_completed_explicit = bool(
        normalized_source_assimilation_status
        in {"assimilated_with_expected_changes", "assimilated_with_no_changes"}
        or normalized_assimilation_result_class in {"expected_changes", "no_changes"}
    )
    write_completed_successfully = bool(
        prompt167_write_completed_explicit or prompt169_write_completed_explicit
    )
    codex_write_completion_source = "none"
    if prompt167_write_completed_explicit:
        codex_write_completion_source = "prompt167_write_result"
    elif prompt169_write_completed_explicit:
        codex_write_completion_source = "prompt169_assimilation"

    downstream_validation_definitive = bool(
        bool(validation_passed)
        or bool(validation_failed)
        or normalized_source_validation_execution_status == "validation_timeout"
    )
    downstream_truth_precedence_applied = bool(downstream_validation_definitive)
    active_path_human_review_required = bool(
        (
            validation_execution_human_review_required
            or normalized_source_validation_execution_status
            in {
                "blocked_routing_not_allowed",
                "blocked_no_py_compile_candidates",
                "blocked_unsafe_py_compile_candidate",
            }
        )
        if downstream_validation_definitive
        else (
            selection_human_review_required
            or invocation_human_review_required
            or write_human_review_required
            or assimilation_human_review_required
            or routing_human_review_required
            or validation_execution_human_review_required
            or normalized_source_selection_status == "blocked_human_review_required"
            or normalized_source_invocation_readiness_status
            == "blocked_human_review_required"
            or normalized_source_write_invocation_status == "blocked_human_review_required"
            or normalized_smoke_override_status == "manual_review_required"
            or normalized_source_assimilation_status == "manual_review_required"
            or normalized_source_validation_routing_status == "blocked_human_review_required"
            or normalized_source_validation_execution_status
            == "blocked_human_review_required"
        )
    )

    blocked_before_write = bool(
        (
            normalized_source_selection_status
            not in {"selected_fix_prompt", "selected_next_prompt"}
            or not bool(selected_prompt_ready)
            or normalized_source_invocation_readiness_status != "ready_to_invoke_codex"
            or not bool(codex_invocation_allowed)
        )
        and not bool(write_invocation_attempted)
        and not bool(validation_executed)
    )

    status = "blocked_insufficient_cycle_truth"
    cycle_attempted = False
    cycle_completed = False
    cycle_passed = False
    cycle_failed = False
    cycle_blocked = True
    cycle_block_reason = "blocked_insufficient_cycle_truth"
    human_review_required = True
    next_safe_action = "manual_review_required"
    next_prompt_kind = "none"

    if normalized_source_validation_execution_status == "validation_timeout":
        status = "blocked_validation_timeout"
        cycle_attempted = True
        cycle_completed = True
        cycle_passed = False
        cycle_failed = True
        cycle_blocked = True
        cycle_block_reason = "blocked_validation_timeout"
        human_review_required = True
        next_safe_action = "manual_review_required"
        next_prompt_kind = "none"
    elif bool(validation_passed):
        status = "cycle_passed"
        cycle_attempted = True
        cycle_completed = True
        cycle_passed = True
        cycle_failed = False
        cycle_blocked = False
        cycle_block_reason = ""
        human_review_required = bool(active_path_human_review_required)
        next_safe_action = "continue_one_step_cycle"
        next_prompt_kind = "next"
    elif bool(validation_failed):
        status = "cycle_failed_validation"
        cycle_attempted = True
        cycle_completed = True
        cycle_passed = False
        cycle_failed = True
        cycle_blocked = False
        cycle_block_reason = "validation_failed"
        human_review_required = bool(
            active_path_human_review_required
            and normalized_source_validation_execution_status
            in {
                "blocked_routing_not_allowed",
                "blocked_no_py_compile_candidates",
                "blocked_unsafe_py_compile_candidate",
                "validation_timeout",
            }
        )
        next_safe_action = (
            "manual_review_required" if human_review_required else "generate_fix_prompt"
        )
        next_prompt_kind = "none" if human_review_required else "fix"
    elif active_path_human_review_required:
        status = "blocked_human_review_required"
        cycle_attempted = bool(write_invocation_attempted or validation_executed)
        cycle_completed = False
        cycle_passed = False
        cycle_failed = False
        cycle_blocked = True
        cycle_block_reason = "blocked_human_review_required"
        human_review_required = True
        next_safe_action = "manual_review_required"
        next_prompt_kind = "none"
    elif blocked_before_write:
        status = "blocked_before_codex_write"
        cycle_attempted = False
        cycle_completed = False
        cycle_passed = False
        cycle_failed = False
        cycle_blocked = True
        cycle_block_reason = "blocked_before_codex_write"
        human_review_required = True
        next_safe_action = "manual_review_required"
        next_prompt_kind = "none"
    elif not write_completed_successfully and not downstream_validation_definitive:
        status = "blocked_codex_write_not_completed"
        cycle_attempted = True
        cycle_completed = False
        cycle_passed = False
        cycle_failed = False
        cycle_blocked = True
        cycle_block_reason = "blocked_codex_write_not_completed"
        human_review_required = True
        next_safe_action = "manual_review_required"
        next_prompt_kind = "none"
    elif (
        not bool(assimilation_safe_for_validation_routing)
        and not downstream_validation_definitive
    ):
        status = "blocked_assimilation_not_safe"
        cycle_attempted = True
        cycle_completed = False
        cycle_passed = False
        cycle_failed = False
        cycle_blocked = True
        cycle_block_reason = "blocked_assimilation_not_safe"
        human_review_required = True
        next_safe_action = "manual_review_required"
        next_prompt_kind = "none"
    elif not bool(validation_allowed) and not downstream_validation_definitive:
        status = "blocked_validation_routing"
        cycle_attempted = True
        cycle_completed = False
        cycle_passed = False
        cycle_failed = False
        cycle_blocked = True
        cycle_block_reason = (
            normalized_source_validation_routing_block_reason
            or "blocked_validation_routing"
        )
        human_review_required = True
        next_safe_action = "manual_review_required"
        next_prompt_kind = "none"
    else:
        status = "blocked_insufficient_cycle_truth"
        cycle_attempted = False
        cycle_completed = False
        cycle_passed = False
        cycle_failed = False
        cycle_blocked = True
        cycle_block_reason = "blocked_insufficient_cycle_truth"
        human_review_required = True
        next_safe_action = "manual_review_required"
        next_prompt_kind = "none"

    return {
        "project_browser_autonomous_one_step_cycle_status": status,
        "project_browser_autonomous_one_step_cycle_cycle_attempted": bool(cycle_attempted),
        "project_browser_autonomous_one_step_cycle_cycle_completed": bool(cycle_completed),
        "project_browser_autonomous_one_step_cycle_cycle_passed": bool(cycle_passed),
        "project_browser_autonomous_one_step_cycle_cycle_failed": bool(cycle_failed),
        "project_browser_autonomous_one_step_cycle_cycle_blocked": bool(cycle_blocked),
        "project_browser_autonomous_one_step_cycle_cycle_block_reason": cycle_block_reason,
        "project_browser_autonomous_one_step_cycle_selected_prompt_kind": (
            normalized_selected_prompt_kind
        ),
        "project_browser_autonomous_one_step_cycle_codex_invocation_allowed": bool(
            codex_invocation_allowed
        ),
        "project_browser_autonomous_one_step_cycle_codex_write_completed": bool(
            write_completed_successfully
        ),
        "project_browser_autonomous_one_step_cycle_assimilation_safe_for_validation_routing": bool(
            assimilation_safe_for_validation_routing
        ),
        "project_browser_autonomous_one_step_cycle_validation_allowed": bool(
            validation_allowed
        ),
        "project_browser_autonomous_one_step_cycle_validation_executed": bool(
            validation_executed
        ),
        "project_browser_autonomous_one_step_cycle_validation_passed": bool(
            validation_passed
        ),
        "project_browser_autonomous_one_step_cycle_validation_failed": bool(
            validation_failed
        ),
        "project_browser_autonomous_one_step_cycle_human_review_required": bool(
            human_review_required
        ),
        "project_browser_autonomous_one_step_cycle_next_safe_action": next_safe_action,
        "project_browser_autonomous_one_step_cycle_next_prompt_kind": next_prompt_kind,
        "project_browser_autonomous_one_step_cycle_source_selection_status": (
            normalized_source_selection_status
        ),
        "project_browser_autonomous_one_step_cycle_source_invocation_readiness_status": (
            normalized_source_invocation_readiness_status
        ),
        "project_browser_autonomous_one_step_cycle_source_write_invocation_status": (
            normalized_source_write_invocation_status
        ),
        "project_browser_autonomous_one_step_cycle_source_assimilation_status": (
            normalized_source_assimilation_status
        ),
        "project_browser_autonomous_one_step_cycle_source_validation_routing_status": (
            normalized_source_validation_routing_status
        ),
        "project_browser_autonomous_one_step_cycle_source_validation_execution_status": (
            normalized_source_validation_execution_status
        ),
        "project_browser_autonomous_one_step_cycle_active_path_human_review_required": bool(
            active_path_human_review_required
        ),
        "project_browser_autonomous_one_step_cycle_downstream_validation_definitive": bool(
            downstream_validation_definitive
        ),
        "project_browser_autonomous_one_step_cycle_downstream_truth_precedence_applied": bool(
            downstream_truth_precedence_applied
        ),
        "project_browser_autonomous_one_step_cycle_codex_write_completion_source": (
            codex_write_completion_source
        ),
    }

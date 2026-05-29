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
    _build_project_browser_autonomous_codex_write_invocation_state,
)

def _build_project_browser_ui_recovery_decision_state(
    *,
    browser_task_status: str,
    browser_response_status: str,
    browser_chat_rotation_due: bool,
    browser_handoff_summary_required: bool,
    browser_handoff_summary_available: bool,
    browser_ui_failure_status: str,
    browser_prompt_payload_status: str,
    browser_prompt_runtime_metadata_only: bool,
    browser_prompt_runtime_no_browser_send: bool,
    browser_prompt_runtime_no_dom_read: bool,
    browser_prompt_runtime_no_session_check: bool,
    browser_response_assimilation_status: str,
    browser_next_action_posture: str,
    browser_assimilation_runtime_no_queue_mutation: bool,
    browser_assimilation_runtime_no_retry_execution: bool,
    browser_assimilation_runtime_no_repair_execution: bool,
    browser_assimilation_runtime_no_restart_execution: bool,
    browser_assimilation_runtime_no_browser_action: bool,
    retry_limit: int,
    prior_retry_count: int,
) -> dict[str, Any]:
    task_status = _normalize_text(browser_task_status, default="inactive")
    response_status = _normalize_text(browser_response_status, default="inactive")
    ui_failure_status = _normalize_text(
        browser_ui_failure_status,
        default="insufficient_truth",
    )
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

    retry_limit_value = _as_non_negative_int(
        retry_limit,
        default=_PROJECT_BROWSER_RETRY_LIMIT,
    )
    retry_count = _as_non_negative_int(prior_retry_count, default=0)
    retry_count_posture = "not_applicable"
    if task_status != "inactive":
        if retry_limit_value <= 0:
            retry_count_posture = "insufficient_truth"
        elif retry_count >= retry_limit_value:
            retry_count_posture = "retry_limit_reached"
        else:
            retry_count_posture = "retry_available"
    if retry_count_posture not in _PROJECT_BROWSER_UI_RETRY_COUNT_POSTURES:
        retry_count_posture = "insufficient_truth"
    retry_remaining = max(0, retry_limit_value - retry_count)

    handoff_dependency_posture = "not_required"
    if browser_chat_rotation_due:
        if browser_handoff_summary_available:
            handoff_dependency_posture = "required_available"
        elif browser_handoff_summary_required:
            handoff_dependency_posture = "required_missing"
        else:
            handoff_dependency_posture = "insufficient_truth"
    if handoff_dependency_posture not in _PROJECT_BROWSER_UI_HANDOFF_DEPENDENCY_POSTURES:
        handoff_dependency_posture = "insufficient_truth"

    runtime_posture = [
        "metadata_only",
        "no_same_chat_retry_execution",
        "no_resend_execution",
        "no_page_reload_execution",
        "no_new_chat_execution",
        "no_login_recovery_execution",
        "no_browser_action",
    ]
    runtime_contract_ok = bool(
        browser_prompt_runtime_metadata_only
        and browser_prompt_runtime_no_browser_send
        and browser_prompt_runtime_no_dom_read
        and browser_prompt_runtime_no_session_check
        and browser_assimilation_runtime_no_queue_mutation
        and browser_assimilation_runtime_no_retry_execution
        and browser_assimilation_runtime_no_repair_execution
        and browser_assimilation_runtime_no_restart_execution
        and browser_assimilation_runtime_no_browser_action
    )

    status = "inactive"
    candidate = "none"
    reason = "no_failure"
    blocked = False
    retry_available = bool(retry_count_posture == "retry_available")
    retry_limit_reached = bool(retry_count_posture == "retry_limit_reached")

    if (
        task_status not in _PROJECT_BROWSER_TASK_STATUSES
        or response_status not in _PROJECT_BROWSER_RESPONSE_STATUSES
        or ui_failure_status not in _PROJECT_BROWSER_UI_FAILURE_STATUSES
        or prompt_payload_status not in _PROJECT_BROWSER_PROMPT_PAYLOAD_STATUSES
        or assimilation_status not in _PROJECT_BROWSER_RESPONSE_ASSIMILATION_STATUSES
        or next_action_posture not in _PROJECT_BROWSER_NEXT_ACTION_POSTURES
    ):
        status = "insufficient_truth"
        reason = "insufficient_truth"
    elif (
        task_status == "inactive"
        or prompt_payload_status == "inactive"
        or assimilation_status == "inactive"
    ):
        status = "inactive"
    elif not runtime_contract_ok:
        status = "insufficient_truth"
        reason = "insufficient_truth"
    elif (
        assimilation_status == "assimilated"
        and response_status in {"invalid_response", "unavailable", "inactive"}
    ):
        status = "insufficient_truth"
        reason = "insufficient_truth"
    elif prompt_payload_status == "unavailable":
        status = "unavailable"
        reason = "insufficient_truth"
    elif (
        prompt_payload_status == "insufficient_truth"
        or assimilation_status == "insufficient_truth"
        or handoff_dependency_posture == "insufficient_truth"
        or retry_count_posture == "insufficient_truth"
    ):
        status = "insufficient_truth"
        reason = "insufficient_truth"
    elif ui_failure_status == "login_interruption":
        status = "selected"
        candidate = "escalate"
        reason = "login_interruption"
    elif browser_chat_rotation_due:
        reason = "rotation_due"
        if handoff_dependency_posture == "required_available":
            status = "selected"
            candidate = "new_chat_handoff"
        elif handoff_dependency_posture == "required_missing":
            status = "blocked"
            blocked = True
        else:
            status = "insufficient_truth"
            reason = "insufficient_truth"
    elif ui_failure_status == "loading_timeout":
        status = "selected"
        candidate = "page_reload"
        reason = "loading_timeout"
    elif ui_failure_status == "retryable_ui_failure":
        reason = "retryable_ui_failure"
        if retry_available:
            status = "selected"
            candidate = "same_chat_retry"
        elif retry_limit_reached:
            status = "blocked"
            blocked = True
            candidate = "escalate"
            reason = "retry_limit_reached"
        else:
            status = "insufficient_truth"
            reason = "insufficient_truth"
    elif ui_failure_status == "response_unavailable":
        reason = "response_unavailable"
        if retry_available:
            status = "selected"
            candidate = "resend_same_prompt"
        elif retry_limit_reached:
            status = "blocked"
            blocked = True
            candidate = "escalate"
            reason = "retry_limit_reached"
        else:
            status = "unavailable"
    elif response_status == "invalid_response" or assimilation_status == "invalid_response":
        reason = "invalid_response"
        if retry_available:
            status = "selected"
            candidate = "resend_same_prompt"
        elif retry_limit_reached:
            status = "blocked"
            blocked = True
            candidate = "escalate"
            reason = "retry_limit_reached"
        else:
            status = "unavailable"
    elif response_status == "unavailable" or assimilation_status == "unavailable":
        reason = "response_unavailable"
        if retry_available:
            status = "selected"
            candidate = "resend_same_prompt"
        elif retry_limit_reached:
            status = "blocked"
            blocked = True
            candidate = "escalate"
            reason = "retry_limit_reached"
        else:
            status = "unavailable"
    elif next_action_posture == "candidate_retry":
        reason = "assimilation_candidate_retry"
        if retry_available:
            status = "selected"
            candidate = "same_chat_retry"
        elif retry_limit_reached:
            status = "blocked"
            blocked = True
            candidate = "escalate"
            reason = "retry_limit_reached"
        else:
            status = "unavailable"
    elif next_action_posture == "candidate_repair":
        status = "blocked"
        blocked = True
        candidate = "escalate"
        reason = "assimilation_candidate_repair"
    elif next_action_posture == "candidate_restart":
        status = "blocked"
        blocked = True
        candidate = "escalate"
        reason = "assimilation_candidate_restart"
    elif ui_failure_status == "no_failure":
        status = "selected"
        candidate = "none"
        reason = "no_failure"
    else:
        status = "unavailable"
        candidate = "none"
        reason = "insufficient_truth"

    if status not in _PROJECT_BROWSER_UI_RECOVERY_DECISION_STATUSES:
        status = "insufficient_truth"
    if candidate not in _PROJECT_BROWSER_UI_RECOVERY_CANDIDATES:
        candidate = "none"
    if reason not in _PROJECT_BROWSER_UI_RECOVERY_REASONS:
        reason = "insufficient_truth"

    return {
        "project_browser_ui_recovery_decision_status": status,
        "project_browser_recovery_candidate": candidate,
        "project_browser_recovery_reason": reason,
        "project_browser_retry_count_posture": retry_count_posture,
        "project_browser_retry_count_current": retry_count,
        "project_browser_retry_count_limit": retry_limit_value,
        "project_browser_retry_count_remaining": retry_remaining,
        "project_browser_handoff_dependency_posture": handoff_dependency_posture,
        "project_browser_ui_recovery_decision_blocked": bool(blocked),
        "project_browser_recovery_runtime_posture": runtime_posture,
        "project_browser_recovery_runtime_metadata_only": True,
        "project_browser_recovery_runtime_no_same_chat_retry_execution": True,
        "project_browser_recovery_runtime_no_resend_execution": True,
        "project_browser_recovery_runtime_no_page_reload_execution": True,
        "project_browser_recovery_runtime_no_new_chat_execution": True,
        "project_browser_recovery_runtime_no_login_recovery_execution": True,
        "project_browser_recovery_runtime_no_browser_action": True,
    }

def _build_project_browser_recovery_runtime_state(
    *,
    browser_command_type: str,
    browser_chatgpt_page_status: str,
    browser_login_interruption_status: str,
    browser_response_wait_status: str,
    browser_response_wait_block_reason: str,
    browser_response_json_parse_status: str,
    browser_execution_receipt_status: str,
    browser_response_parse_block_reason: str,
    browser_ui_recovery_decision_status: str,
    browser_recovery_candidate: str,
    browser_recovery_reason: str,
    browser_retry_count_posture: str,
    browser_handoff_dependency_posture: str,
    browser_handoff_compile_status: str,
    browser_handoff_payload_posture: str,
    prior_browser_state: Mapping[str, Any] | None,
    page: Any | None,
) -> dict[str, Any]:
    command_type = _normalize_text(browser_command_type, default="none")
    page_status = _normalize_text(browser_chatgpt_page_status, default="insufficient_truth")
    login_status = _normalize_text(
        browser_login_interruption_status,
        default="insufficient_truth",
    )
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
    parse_block_reason = _normalize_text(
        browser_response_parse_block_reason,
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

    status = "insufficient_truth"
    action = "none"
    reason = "insufficient_truth"
    block_reason = "insufficient_truth"
    receipt_status = "insufficient_truth"
    receipt_kind = "none"
    recovery_attempted = False
    runtime_tokens = [
        "no_prompt_refill",
        "no_resend",
        "no_response_wait",
        "no_response_read",
        "no_json_parse",
        "no_decision_execution",
        "no_queue_mutation",
        "no_retry_loop",
        "no_login_recovery",
        "no_executor_loop",
    ]

    if parse_status == "inactive" or execution_receipt_status == "not_created":
        status = "inactive"
        reason = "none"
        block_reason = "execution_receipt_missing"
        receipt_status = "not_created"
    elif parse_status == "failed" or execution_receipt_status == "failed":
        status = "failed"
        reason = "unsupported_outcome"
        block_reason = "parse_not_ready"
        receipt_status = "failed"
        receipt_kind = "failed_recovery_receipt"
    elif parse_status == "blocked" or execution_receipt_status == "blocked":
        status = "blocked"
        reason = "unsupported_outcome"
        block_reason = "parse_not_ready"
        receipt_status = "blocked"
        receipt_kind = "blocked_recovery_receipt"
    elif (
        parse_status == "insufficient_truth"
        or execution_receipt_status == "insufficient_truth"
        or ui_recovery_decision_status == "insufficient_truth"
        or retry_count_posture == "insufficient_truth"
    ):
        status = "insufficient_truth"
        reason = "insufficient_truth"
        block_reason = "insufficient_truth"
        receipt_status = "insufficient_truth"
    elif (
        login_status == "detected"
        or page_status == "login_interruption"
        or recovery_reason == "login_interruption"
    ):
        status = "pause_required"
        action = "pause_for_login"
        reason = "login_interruption"
        block_reason = "login_interruption"
        receipt_status = "pause_required"
        receipt_kind = "pause_for_login_receipt"
    elif retry_count_posture == "retry_limit_reached":
        status = "blocked"
        action = "escalate"
        reason = "retry_limit_reached"
        block_reason = "retry_limit_reached"
        receipt_status = "blocked"
        receipt_kind = "blocked_recovery_receipt"
    elif parse_status == "valid" and execution_receipt_status == "parsed":
        status = "not_attempted"
        reason = "none"
        block_reason = "recovery_not_required"
        receipt_status = "not_created"
    else:
        if command_type not in _PROJECT_BROWSER_COMMAND_TYPES - {"none"}:
            status = "blocked"
            reason = "unsupported_outcome"
            block_reason = "recovery_not_allowed"
            receipt_status = "blocked"
            receipt_kind = "blocked_recovery_receipt"
        else:
            handoff_ready = bool(
                handoff_dependency_posture == "required_available"
                and handoff_compile_status == "ready"
                and handoff_payload_posture == "compact_ready"
            )
            handoff_missing = bool(
                handoff_dependency_posture == "required_missing"
                or handoff_compile_status in {"unavailable", "insufficient_truth"}
                or handoff_payload_posture
                in {"missing_required_sections", "unavailable", "insufficient_truth"}
            )
            wants_new_chat = bool(
                recovery_candidate == "new_chat_handoff"
                or recovery_reason == "rotation_due"
            )
            reload_outcome = _normalize_text(recovery_reason, default="")
            if reload_outcome not in {
                "response_timeout",
                "page_unavailable",
                "loading_timeout",
                "response_unavailable",
                "invalid_response",
            }:
                if response_wait_block_reason == "response_timeout":
                    reload_outcome = "response_timeout"
                elif response_wait_block_reason == "page_unavailable":
                    reload_outcome = "page_unavailable"
                elif parse_status == "invalid_response" or parse_block_reason in {
                    "json_parse_failed",
                    "schema_missing",
                    "schema_invalid",
                    "decision_missing",
                }:
                    reload_outcome = "invalid_response"
                elif parse_status in {"unavailable", "not_attempted"}:
                    reload_outcome = "response_unavailable"
            safe_reload_requested = bool(
                recovery_candidate == "page_reload"
                or (
                    reload_outcome in {"response_timeout", "page_unavailable", "loading_timeout"}
                    and recovery_reason == "loading_timeout"
                )
            )
            if wants_new_chat:
                if handoff_missing:
                    status = "blocked"
                    reason = "handoff_missing"
                    block_reason = "handoff_missing"
                    receipt_status = "blocked"
                    receipt_kind = "blocked_recovery_receipt"
                elif not handoff_ready:
                    status = "insufficient_truth"
                    reason = "insufficient_truth"
                    block_reason = "insufficient_truth"
                    receipt_status = "insufficient_truth"
                elif page is None:
                    status = "failed"
                    action = "new_chat"
                    reason = "rotation_due"
                    block_reason = "new_chat_failed"
                    receipt_status = "failed"
                    receipt_kind = "failed_recovery_receipt"
                else:
                    recovery_attempted = True
                    runtime_tokens.append("recovery_attempted")
                    timeout_ms = _as_non_negative_int(
                        dict(prior_browser_state or {}).get(
                            "project_browser_recovery_new_chat_timeout_ms"
                        ),
                        default=2000,
                    )
                    if timeout_ms <= 0 or timeout_ms > 10000:
                        timeout_ms = 2000
                    candidates = _collect_project_browser_selector_candidates_for_target(
                        target="new_chat_trigger",
                        prior_browser_state=prior_browser_state,
                    )
                    clicked = False
                    try:
                        try:
                            page.set_default_timeout(timeout_ms)
                        except Exception:
                            pass
                        for selector in candidates:
                            try:
                                locator = page.locator(selector).first
                                if locator.count() <= 0:
                                    continue
                                locator.click(timeout=timeout_ms)
                                clicked = True
                                break
                            except Exception:
                                continue
                    except Exception:
                        clicked = False
                    if clicked:
                        status = "recovered"
                        action = "new_chat"
                        reason = "rotation_due"
                        block_reason = "none"
                        receipt_status = "recovered"
                        receipt_kind = "new_chat_recovery_receipt"
                    else:
                        status = "failed"
                        action = "new_chat"
                        reason = "rotation_due"
                        block_reason = "new_chat_failed"
                        receipt_status = "failed"
                        receipt_kind = "failed_recovery_receipt"
            elif safe_reload_requested:
                if page is None:
                    status = "failed"
                    action = "page_reload"
                    reason = (
                        reload_outcome
                        if reload_outcome in _PROJECT_BROWSER_RECOVERY_REASONS
                        else "unsupported_outcome"
                    )
                    block_reason = "page_reload_failed"
                    receipt_status = "failed"
                    receipt_kind = "failed_recovery_receipt"
                else:
                    recovery_attempted = True
                    runtime_tokens.append("recovery_attempted")
                    timeout_ms = _as_non_negative_int(
                        dict(prior_browser_state or {}).get(
                            "project_browser_recovery_page_reload_timeout_ms"
                        ),
                        default=2500,
                    )
                    if timeout_ms <= 0 or timeout_ms > 12000:
                        timeout_ms = 2500
                    reloaded = False
                    try:
                        page.reload(
                            wait_until="domcontentloaded",
                            timeout=timeout_ms,
                        )
                        reloaded = True
                    except Exception:
                        reloaded = False
                    if reloaded:
                        status = "recovered"
                        action = "page_reload"
                        reason = (
                            reload_outcome
                            if reload_outcome in _PROJECT_BROWSER_RECOVERY_REASONS
                            else "unsupported_outcome"
                        )
                        block_reason = "none"
                        receipt_status = "recovered"
                        receipt_kind = "page_reload_recovery_receipt"
                    else:
                        status = "failed"
                        action = "page_reload"
                        reason = (
                            reload_outcome
                            if reload_outcome in _PROJECT_BROWSER_RECOVERY_REASONS
                            else "unsupported_outcome"
                        )
                        block_reason = "page_reload_failed"
                        receipt_status = "failed"
                        receipt_kind = "failed_recovery_receipt"
            elif handoff_missing and recovery_reason == "rotation_due":
                status = "blocked"
                reason = "handoff_missing"
                block_reason = "handoff_missing"
                receipt_status = "blocked"
                receipt_kind = "blocked_recovery_receipt"
            elif parse_status in {"invalid_response", "unavailable"}:
                status = "blocked"
                action = "escalate"
                reason = (
                    "invalid_response" if parse_status == "invalid_response" else "response_unavailable"
                )
                block_reason = "recovery_not_allowed"
                receipt_status = "blocked"
                receipt_kind = "blocked_recovery_receipt"
            else:
                status = "blocked"
                action = "escalate"
                reason = "unsupported_outcome"
                block_reason = "recovery_not_allowed"
                receipt_status = "blocked"
                receipt_kind = "blocked_recovery_receipt"

    if status not in _PROJECT_BROWSER_RECOVERY_STATUSES:
        status = "insufficient_truth"
    if action not in _PROJECT_BROWSER_RECOVERY_ACTIONS:
        action = "none"
    if reason not in _PROJECT_BROWSER_RECOVERY_REASONS:
        reason = "insufficient_truth"
    if block_reason not in _PROJECT_BROWSER_RECOVERY_BLOCK_REASONS:
        block_reason = "insufficient_truth"
    if receipt_status not in _PROJECT_BROWSER_RECOVERY_RECEIPT_STATUSES:
        receipt_status = "insufficient_truth"
    if receipt_kind not in _PROJECT_BROWSER_RECOVERY_RECEIPT_KINDS:
        receipt_kind = "none"

    runtime_posture = [
        token
        for token in runtime_tokens
        if token in _PROJECT_BROWSER_RECOVERY_RUNTIME_POSTURES
    ]
    if not recovery_attempted and "recovery_attempted" in runtime_posture:
        runtime_posture = [
            token for token in runtime_posture if token != "recovery_attempted"
        ]

    return {
        "project_browser_recovery_status": status,
        "project_browser_recovery_action": action,
        "project_browser_recovery_reason": reason,
        "project_browser_recovery_block_reason": block_reason,
        "project_browser_recovery_runtime_posture": runtime_posture,
        "project_browser_recovery_receipt_status": receipt_status,
        "project_browser_recovery_receipt_kind": receipt_kind,
        "project_browser_recovery_runtime_recovery_attempted": bool(
            "recovery_attempted" in runtime_posture
        ),
        "project_browser_recovery_runtime_no_prompt_refill": True,
        "project_browser_recovery_runtime_no_resend": True,
        "project_browser_recovery_runtime_no_response_wait": True,
        "project_browser_recovery_runtime_no_response_read": True,
        "project_browser_recovery_runtime_no_json_parse": True,
        "project_browser_recovery_runtime_no_decision_execution": True,
        "project_browser_recovery_runtime_no_queue_mutation": True,
        "project_browser_recovery_runtime_no_retry_loop": True,
        "project_browser_recovery_runtime_no_login_recovery": True,
        "project_browser_recovery_runtime_no_executor_loop": True,
    }

def _build_project_browser_autonomous_rollback_readiness_state(
    *,
    repository_path: str,
    continuation_status: str,
    continuation_rollback_required: bool,
    continuation_rollback_candidate: bool,
    continuation_rollback_reason: str,
    continuation_allowed: bool,
    continuation_block_reason: str,
    continuation_stop_reason: str,
    continuation_human_review_required: bool,
    continuation_manual_review_required: bool,
    continuation_next_action: str,
    post_reentry_cycle_status: str,
    post_reentry_cycle_block_reason: str,
    post_reentry_rollback_candidate: bool,
    post_reentry_rollback_reason: str,
    source_changed_files: list[str] | None,
    source_changed_files_count: int,
    expected_changed_files: list[str] | None,
    allowed_changed_files: list[str] | None,
    unexpected_changed_files: list[str] | None,
    forbidden_changed_files: list[str] | None,
    too_many_changed_files: bool,
    reentry_assimilation_source_changed_files: list[str] | None,
    reentry_assimilation_source_changed_files_count: int,
    reentry_assimilation_authoritative_source_kind: str,
    reentry_assimilation_authoritative_source_selected: bool,
    reentry_invocation_status: str,
    reentry_invocation_attempted: bool,
    reentry_invocation_completed: bool,
    reentry_invocation_changed_files_after: list[str] | None,
    normal_write_result_status: str,
    normal_write_result_changed_files_after: list[str] | None,
) -> dict[str, Any]:
    allowed_statuses = {
        "rollback_readiness_allowed",
        "rollback_readiness_not_required",
        "rollback_readiness_blocked_manual_review",
        "rollback_readiness_blocked_no_targets",
        "rollback_readiness_blocked_forbidden_files",
        "rollback_readiness_blocked_unsafe_files",
        "rollback_readiness_blocked_symlink_files",
        "rollback_readiness_blocked_out_of_repo_files",
        "rollback_readiness_blocked_ambiguous_sources",
        "rollback_readiness_blocked_too_many_files",
        "rollback_readiness_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_strategies = {
        "restore_tracked_only",
        "restore_tracked_and_remove_safe_untracked",
        "blocked_manual_review",
    }
    runtime_posture = [
        "prompt184_rollback_readiness_controller",
        "metadata_only",
        "no_rollback_execution",
        "no_git_reset_clean_checkout_restore",
        "no_file_deletion_execution",
        "no_codex_invocation",
        "no_commit",
    ]
    max_rollback_file_count = 20

    normalized_repo = _normalize_text(repository_path, default="")
    normalized_continuation_status = _normalize_text(
        continuation_status,
        default="insufficient_truth",
    )
    normalized_continuation_next_action = _normalize_text(
        continuation_next_action,
        default="insufficient_truth",
    )
    normalized_continuation_block_reason = _normalize_text(
        continuation_block_reason,
        default="",
    )
    normalized_continuation_stop_reason = _normalize_text(
        continuation_stop_reason,
        default="",
    )
    normalized_continuation_rollback_reason = _normalize_text(
        continuation_rollback_reason,
        default="",
    )
    normalized_post_reentry_cycle_status = _normalize_text(
        post_reentry_cycle_status,
        default="insufficient_truth",
    )
    normalized_post_reentry_cycle_block_reason = _normalize_text(
        post_reentry_cycle_block_reason,
        default="",
    )
    normalized_post_reentry_rollback_reason = _normalize_text(
        post_reentry_rollback_reason,
        default="",
    )
    normalized_expected_changed_files = _normalize_string_list(expected_changed_files or [])
    normalized_allowed_changed_files = _normalize_string_list(allowed_changed_files or [])
    normalized_unexpected_changed_files = _normalize_string_list(
        unexpected_changed_files or []
    )
    normalized_forbidden_changed_files = _normalize_string_list(forbidden_changed_files or [])
    normalized_source_changed_files = _normalize_string_list(source_changed_files or [])
    normalized_source_changed_files_count = _as_non_negative_int(
        source_changed_files_count,
        default=len(normalized_source_changed_files),
    )
    normalized_assimilation_changed_files = _normalize_string_list(
        reentry_assimilation_source_changed_files or []
    )
    normalized_assimilation_changed_files_count = _as_non_negative_int(
        reentry_assimilation_source_changed_files_count,
        default=len(normalized_assimilation_changed_files),
    )
    normalized_reentry_changed_files = _normalize_string_list(
        reentry_invocation_changed_files_after or []
    )
    normalized_normal_write_changed_files = _normalize_string_list(
        normal_write_result_changed_files_after or []
    )
    normalized_reentry_authoritative_kind = _normalize_text(
        reentry_assimilation_authoritative_source_kind,
        default="none",
    )
    normalized_reentry_status = _normalize_text(
        reentry_invocation_status,
        default="insufficient_truth",
    )
    normalized_normal_write_status = _normalize_text(
        normal_write_result_status,
        default="insufficient_truth",
    )

    rollback_requested = bool(
        continuation_rollback_required
        or continuation_rollback_candidate
        or post_reentry_rollback_candidate
    )
    rollback_reason = (
        normalized_continuation_rollback_reason
        or normalized_post_reentry_rollback_reason
        or normalized_post_reentry_cycle_block_reason
        or normalized_continuation_block_reason
        or normalized_continuation_stop_reason
    )
    continuation_path_requires_rollback = bool(
        rollback_requested
        and not bool(continuation_allowed)
        and normalized_continuation_next_action in {"prepare_rollback"}
    )
    if not rollback_reason and rollback_requested:
        rollback_reason = "post_reentry_rollback_required"

    reentry_source_active = bool(
        normalized_reentry_authoritative_kind == "reentry"
        or bool(reentry_assimilation_authoritative_source_selected)
        or bool(reentry_invocation_attempted)
        or bool(reentry_invocation_completed)
        or normalized_reentry_status
        in {
            "reentry_invocation_completed_with_changes",
            "reentry_invocation_completed_no_changes",
            "reentry_invocation_completed_failure",
            "reentry_invocation_completed_timeout",
        }
    )
    source_ambiguous = bool(
        reentry_source_active
        and normalized_reentry_authoritative_kind not in {"reentry", "none"}
    )

    rollback_target_files: list[str] = []
    if normalized_source_changed_files:
        rollback_target_files = list(normalized_source_changed_files)
    elif normalized_assimilation_changed_files:
        rollback_target_files = list(normalized_assimilation_changed_files)
    elif normalized_reentry_changed_files:
        rollback_target_files = list(normalized_reentry_changed_files)
    elif not reentry_source_active and normalized_normal_write_changed_files:
        rollback_target_files = list(normalized_normal_write_changed_files)

    rollback_target_files = sorted(set(_serialize_required_signals(rollback_target_files)))
    allowed_set = set(normalized_allowed_changed_files)
    expected_set = set(normalized_expected_changed_files)
    forbidden_set_from_source = set(normalized_forbidden_changed_files)
    unexpected_set_from_source = set(normalized_unexpected_changed_files)
    too_many_from_source = bool(too_many_changed_files)

    safe_untracked_runtime_paths = {
        "prompt167_workspace_write_smoke.txt",
    }
    sensitive_file_markers = (
        ".env",
        ".pem",
        ".key",
        "secret",
        "token",
        "credential",
    )

    repo_root: Path | None = None
    if normalized_repo:
        try:
            repo_root = Path(normalized_repo).resolve()
        except OSError:
            repo_root = None

    status_by_path: dict[str, str] = {}
    rollback_worktree_dirty = bool(normalized_source_changed_files_count > 0 or rollback_target_files)
    if normalized_repo:
        try:
            status_cp = _run_git(normalized_repo, ["status", "--short"], timeout_seconds=10.0)
            status_output = _normalize_text(status_cp.stdout, default="")
            rollback_worktree_dirty = bool(status_output)
            for line in status_output.splitlines():
                parsed_path = _normalize_text(_parse_git_status_path(line), default="")
                if parsed_path:
                    status_by_path[parsed_path] = line[:2]
        except (subprocess.TimeoutExpired, OSError):
            pass

    rollback_tracked_files: list[str] = []
    rollback_untracked_files: list[str] = []
    rollback_runtime_files: list[str] = []
    rollback_forbidden_files: list[str] = []
    rollback_unexpected_files: list[str] = []
    rollback_unsafe_files: list[str] = []
    rollback_missing_files: list[str] = []
    rollback_symlink_files: list[str] = []
    rollback_out_of_repo_files: list[str] = []
    missing_inputs: list[str] = []

    def _contains_parent_traversal(path_text: str) -> bool:
        return ".." in PurePosixPath(path_text.replace("\\", "/")).parts

    def _is_forbidden(path_text: str) -> bool:
        normalized_path = _normalize_text(path_text, default="").replace("\\", "/")
        lowered = normalized_path.lower()
        if not normalized_path:
            return False
        if normalized_path.startswith(".git/"):
            return True
        if normalized_path.startswith("prompts/context/") and normalized_path not in allowed_set:
            return True
        if normalized_path.startswith("__pycache__/") or "/__pycache__/" in normalized_path:
            return True
        if lowered.endswith(".pyc"):
            return True
        if lowered.startswith(".env") or "/.env" in lowered:
            return True
        if any(marker in lowered for marker in sensitive_file_markers):
            return True
        if normalized_path.startswith(".cache/") or normalized_path.startswith("tmp/"):
            return True
        return False

    for path_text in rollback_target_files:
        normalized_path = _normalize_text(path_text, default="").replace("\\", "/")
        if not normalized_path:
            continue
        if normalized_path.startswith("/") or _contains_parent_traversal(normalized_path):
            rollback_out_of_repo_files.append(normalized_path)
            continue

        candidate_path = Path(normalized_repo, normalized_path) if normalized_repo else Path(normalized_path)
        if candidate_path.exists() and candidate_path.is_symlink():
            rollback_symlink_files.append(normalized_path)
            continue
        if repo_root is not None:
            try:
                resolved_candidate = candidate_path.resolve(strict=False)
                resolved_candidate.relative_to(repo_root)
            except (OSError, ValueError):
                rollback_out_of_repo_files.append(normalized_path)
                continue

        if _is_forbidden(normalized_path) or normalized_path in forbidden_set_from_source:
            rollback_forbidden_files.append(normalized_path)
            continue
        if normalized_path in unexpected_set_from_source:
            rollback_unexpected_files.append(normalized_path)
            continue

        status_code = _normalize_text(status_by_path.get(normalized_path), default="")
        is_untracked = bool(status_code == "??")
        is_runtime = bool(normalized_path in safe_untracked_runtime_paths)
        if is_runtime:
            rollback_runtime_files.append(normalized_path)

        if is_untracked:
            rollback_untracked_files.append(normalized_path)
            if not is_runtime:
                rollback_unsafe_files.append(normalized_path)
            continue

        if candidate_path.exists() and not candidate_path.is_file():
            rollback_unsafe_files.append(normalized_path)
            continue
        if not candidate_path.exists():
            rollback_missing_files.append(normalized_path)
            # Missing tracked file can still be restored from git checkout.
        rollback_tracked_files.append(normalized_path)

        if expected_set and normalized_path not in expected_set and normalized_path not in allowed_set:
            rollback_unexpected_files.append(normalized_path)

    rollback_forbidden_files = sorted(set(_serialize_required_signals(rollback_forbidden_files)))
    rollback_unexpected_files = sorted(set(_serialize_required_signals(rollback_unexpected_files)))
    rollback_unsafe_files = sorted(set(_serialize_required_signals(rollback_unsafe_files)))
    rollback_missing_files = sorted(set(_serialize_required_signals(rollback_missing_files)))
    rollback_symlink_files = sorted(set(_serialize_required_signals(rollback_symlink_files)))
    rollback_out_of_repo_files = sorted(
        set(_serialize_required_signals(rollback_out_of_repo_files))
    )
    rollback_tracked_files = sorted(set(_serialize_required_signals(rollback_tracked_files)))
    rollback_untracked_files = sorted(
        set(_serialize_required_signals(rollback_untracked_files))
    )
    rollback_runtime_files = sorted(set(_serialize_required_signals(rollback_runtime_files)))

    rollback_file_count = len(rollback_target_files)
    rollback_safe_worktree_state = bool(
        rollback_target_files
        and not rollback_forbidden_files
        and not rollback_unexpected_files
        and not rollback_unsafe_files
        and not rollback_symlink_files
        and not rollback_out_of_repo_files
        and not too_many_from_source
        and rollback_file_count <= max_rollback_file_count
    )

    rollback_strategy = "blocked_manual_review"
    rollback_execution_plan: list[str] = []
    rollback_readiness_allowed = False
    rollback_execution_allowed_next = False
    should_execute_rollback = False
    should_invoke_codex = False
    should_commit = False
    status = "rollback_readiness_blocked_insufficient_truth"
    rollback_readiness_block_reason = "blocked_insufficient_truth"
    human_review_required = bool(
        continuation_human_review_required or continuation_manual_review_required
    )
    next_action = "manual_review_required"

    if not rollback_requested:
        status = "rollback_readiness_not_required"
        rollback_readiness_block_reason = "rollback_not_required"
        rollback_reason = ""
        human_review_required = bool(
            continuation_human_review_required or continuation_manual_review_required
        )
        next_action = "no_rollback_required"
    elif not continuation_path_requires_rollback:
        status = "rollback_readiness_blocked_insufficient_truth"
        rollback_readiness_block_reason = "rollback_precondition_not_satisfied"
        human_review_required = True
        next_action = "manual_review_required"
    elif continuation_human_review_required or continuation_manual_review_required:
        status = "rollback_readiness_blocked_manual_review"
        rollback_readiness_block_reason = "manual_review_required"
        human_review_required = True
        next_action = "manual_review_required"
    elif source_ambiguous:
        status = "rollback_readiness_blocked_ambiguous_sources"
        rollback_readiness_block_reason = "ambiguous_file_source_truth"
        human_review_required = True
        next_action = "manual_review_required"
    elif not rollback_target_files:
        status = "rollback_readiness_blocked_no_targets"
        rollback_readiness_block_reason = "rollback_target_files_missing"
        human_review_required = True
        next_action = "manual_review_required"
    elif rollback_out_of_repo_files:
        status = "rollback_readiness_blocked_out_of_repo_files"
        rollback_readiness_block_reason = "out_of_repo_files_detected"
        human_review_required = True
        next_action = "manual_review_required"
    elif rollback_symlink_files:
        status = "rollback_readiness_blocked_symlink_files"
        rollback_readiness_block_reason = "symlink_files_detected"
        human_review_required = True
        next_action = "manual_review_required"
    elif rollback_forbidden_files:
        status = "rollback_readiness_blocked_forbidden_files"
        rollback_readiness_block_reason = "forbidden_files_detected"
        human_review_required = True
        next_action = "manual_review_required"
    elif rollback_unsafe_files or rollback_unexpected_files or too_many_from_source:
        status = (
            "rollback_readiness_blocked_too_many_files"
            if too_many_from_source or rollback_file_count > max_rollback_file_count
            else "rollback_readiness_blocked_unsafe_files"
        )
        rollback_readiness_block_reason = (
            "too_many_files"
            if status == "rollback_readiness_blocked_too_many_files"
            else "unsafe_or_unexpected_files_detected"
        )
        human_review_required = True
        next_action = "manual_review_required"
    elif rollback_file_count > max_rollback_file_count:
        status = "rollback_readiness_blocked_too_many_files"
        rollback_readiness_block_reason = "too_many_files"
        human_review_required = True
        next_action = "manual_review_required"
    else:
        rollback_readiness_allowed = True
        rollback_execution_allowed_next = True
        status = "rollback_readiness_allowed"
        rollback_readiness_block_reason = ""
        human_review_required = False
        next_action = "prepare_rollback_execution"

        if rollback_untracked_files and all(
            path in safe_untracked_runtime_paths for path in rollback_untracked_files
        ):
            rollback_strategy = "restore_tracked_and_remove_safe_untracked"
        else:
            rollback_strategy = "restore_tracked_only"

        for path_text in rollback_tracked_files:
            rollback_execution_plan.append(f"git checkout -- {path_text}")
        if rollback_strategy == "restore_tracked_and_remove_safe_untracked":
            for path_text in rollback_untracked_files:
                rollback_execution_plan.append(f"rm -f -- {path_text}")

    if rollback_strategy not in allowed_strategies:
        rollback_strategy = "blocked_manual_review"
    if status not in allowed_statuses:
        status = "insufficient_truth"
    if status.startswith("rollback_readiness_blocked") and not rollback_readiness_block_reason:
        rollback_readiness_block_reason = "blocked_insufficient_truth"

    missing_inputs = _serialize_required_signals(
        [
            "repository_path_missing" if not normalized_repo else "",
            "continuation_status_missing"
            if not normalized_continuation_status
            else "",
            "post_reentry_cycle_status_missing"
            if not normalized_post_reentry_cycle_status
            else "",
            "source_changed_files_missing"
            if rollback_requested and not rollback_target_files
            else "",
            "expected_changed_files_missing"
            if rollback_requested and not normalized_expected_changed_files
            else "",
            "allowed_changed_files_missing"
            if rollback_requested and not normalized_allowed_changed_files
            else "",
        ]
    )

    return {
        "project_browser_autonomous_rollback_readiness_status": status,
        "project_browser_autonomous_rollback_readiness_rollback_readiness_allowed": bool(
            rollback_readiness_allowed
        ),
        "project_browser_autonomous_rollback_readiness_rollback_readiness_block_reason": (
            rollback_readiness_block_reason
        ),
        "project_browser_autonomous_rollback_readiness_rollback_reason": rollback_reason,
        "project_browser_autonomous_rollback_readiness_rollback_strategy": (
            rollback_strategy
        ),
        "project_browser_autonomous_rollback_readiness_rollback_target_files": (
            rollback_target_files
        ),
        "project_browser_autonomous_rollback_readiness_rollback_tracked_files": (
            rollback_tracked_files
        ),
        "project_browser_autonomous_rollback_readiness_rollback_untracked_files": (
            rollback_untracked_files
        ),
        "project_browser_autonomous_rollback_readiness_rollback_runtime_files": (
            rollback_runtime_files
        ),
        "project_browser_autonomous_rollback_readiness_rollback_forbidden_files": (
            rollback_forbidden_files
        ),
        "project_browser_autonomous_rollback_readiness_rollback_unexpected_files": (
            rollback_unexpected_files
        ),
        "project_browser_autonomous_rollback_readiness_rollback_unsafe_files": (
            rollback_unsafe_files
        ),
        "project_browser_autonomous_rollback_readiness_rollback_missing_files": (
            rollback_missing_files
        ),
        "project_browser_autonomous_rollback_readiness_rollback_symlink_files": (
            rollback_symlink_files
        ),
        "project_browser_autonomous_rollback_readiness_rollback_out_of_repo_files": (
            rollback_out_of_repo_files
        ),
        "project_browser_autonomous_rollback_readiness_rollback_file_count": int(
            rollback_file_count
        ),
        "project_browser_autonomous_rollback_readiness_rollback_worktree_dirty": bool(
            rollback_worktree_dirty
        ),
        "project_browser_autonomous_rollback_readiness_rollback_safe_worktree_state": bool(
            rollback_safe_worktree_state
        ),
        "project_browser_autonomous_rollback_readiness_rollback_execution_plan": (
            rollback_execution_plan
        ),
        "project_browser_autonomous_rollback_readiness_rollback_execution_allowed_next": bool(
            rollback_execution_allowed_next
        ),
        "project_browser_autonomous_rollback_readiness_should_execute_rollback": bool(
            should_execute_rollback
        ),
        "project_browser_autonomous_rollback_readiness_should_invoke_codex": bool(
            should_invoke_codex
        ),
        "project_browser_autonomous_rollback_readiness_should_commit": bool(
            should_commit
        ),
        "project_browser_autonomous_rollback_readiness_human_review_required": bool(
            human_review_required
        ),
        "project_browser_autonomous_rollback_readiness_next_action": next_action,
        "project_browser_autonomous_rollback_readiness_runtime_posture": runtime_posture,
        "project_browser_autonomous_rollback_readiness_missing_inputs": missing_inputs,
    }

def _build_project_browser_autonomous_rollback_execution_state(
    *,
    repository_path: str,
    rollback_readiness_status: str,
    rollback_readiness_allowed: bool,
    rollback_readiness_block_reason: str,
    rollback_reason: str,
    rollback_strategy: str,
    rollback_target_files: list[str] | None,
    rollback_tracked_files: list[str] | None,
    rollback_untracked_files: list[str] | None,
    rollback_runtime_files: list[str] | None,
    rollback_forbidden_files: list[str] | None,
    rollback_unexpected_files: list[str] | None,
    rollback_unsafe_files: list[str] | None,
    rollback_missing_files: list[str] | None,
    rollback_symlink_files: list[str] | None,
    rollback_out_of_repo_files: list[str] | None,
    rollback_file_count: int,
    rollback_worktree_dirty: bool,
    rollback_safe_worktree_state: bool,
    rollback_execution_plan: list[str] | None,
    rollback_execution_allowed_next: bool,
    rollback_human_review_required: bool,
    rollback_readiness_next_action: str,
    continuation_human_review_required: bool,
    post_reentry_human_review_required: bool,
) -> dict[str, Any]:
    allowed_statuses = {
        "rollback_execution_completed",
        "rollback_execution_partial_failure",
        "rollback_execution_failed",
        "rollback_execution_timeout",
        "rollback_execution_blocked_not_allowed",
        "rollback_execution_blocked_manual_review",
        "rollback_execution_blocked_unsafe_plan",
        "rollback_execution_blocked_insufficient_truth",
        "rollback_execution_not_required",
        "insufficient_truth",
    }
    runtime_posture = [
        "prompt185_bounded_rollback_execution",
        "no_git_reset_hard",
        "no_git_clean_fd",
        "no_recursive_delete",
        "no_shell_expansion",
        "no_codex_invocation",
        "no_commit",
    ]
    allowed_safe_untracked_paths = {
        "prompt167_workspace_write_smoke.txt",
    }
    allowed_strategy_values = {
        "restore_tracked_only",
        "restore_tracked_and_remove_safe_untracked",
    }
    command_timeout_seconds = 15.0

    normalized_repo = _normalize_text(repository_path, default="")
    normalized_readiness_status = _normalize_text(
        rollback_readiness_status,
        default="insufficient_truth",
    )
    normalized_readiness_block_reason = _normalize_text(
        rollback_readiness_block_reason,
        default="",
    )
    normalized_rollback_reason = _normalize_text(rollback_reason, default="")
    normalized_strategy = _normalize_text(rollback_strategy, default="blocked_manual_review")
    normalized_target_files = _normalize_string_list(rollback_target_files or [])
    normalized_tracked_files = _normalize_string_list(rollback_tracked_files or [])
    normalized_untracked_files = _normalize_string_list(rollback_untracked_files or [])
    normalized_runtime_files = _normalize_string_list(rollback_runtime_files or [])
    normalized_forbidden_files = _normalize_string_list(rollback_forbidden_files or [])
    normalized_unexpected_files = _normalize_string_list(rollback_unexpected_files or [])
    normalized_unsafe_files = _normalize_string_list(rollback_unsafe_files or [])
    normalized_missing_files = _normalize_string_list(rollback_missing_files or [])
    normalized_symlink_files = _normalize_string_list(rollback_symlink_files or [])
    normalized_out_of_repo_files = _normalize_string_list(rollback_out_of_repo_files or [])
    normalized_execution_plan = _normalize_string_list(rollback_execution_plan or [])
    normalized_rollback_file_count = _as_non_negative_int(
        rollback_file_count,
        default=len(normalized_target_files),
    )
    normalized_readiness_next_action = _normalize_text(
        rollback_readiness_next_action,
        default="manual_review_required",
    )

    status = "rollback_execution_blocked_insufficient_truth"
    rollback_execution_allowed = False
    rollback_execution_attempted = False
    rollback_execution_completed = False
    rollback_execution_failed = False
    rollback_execution_block_reason = "blocked_insufficient_truth"
    rollback_restored_tracked_files: list[str] = []
    rollback_removed_untracked_files: list[str] = []
    rollback_skipped_files: list[str] = []
    rollback_failed_files: list[str] = []
    rollback_command_results: list[dict[str, Any]] = []
    rollback_commands_attempted = 0
    rollback_commands_completed = 0
    rollback_exit_code = 0
    rollback_timed_out = False
    pre_rollback_git_status_short = ""
    post_rollback_git_status_short = ""
    post_rollback_dirty = bool(rollback_worktree_dirty)
    post_rollback_expected_dirty_only = False
    human_review_required = bool(
        rollback_human_review_required
        or continuation_human_review_required
        or post_reentry_human_review_required
    )
    next_action = "manual_review_required"
    missing_inputs: list[str] = []

    def _contains_parent_traversal(path_text: str) -> bool:
        return ".." in PurePosixPath(path_text.replace("\\", "/")).parts

    def _is_sensitive_or_forbidden(path_text: str) -> bool:
        lowered = path_text.lower()
        if path_text.startswith(".git/"):
            return True
        if path_text.startswith("__pycache__/") or "/__pycache__/" in path_text:
            return True
        if lowered.endswith(".pyc"):
            return True
        if lowered.startswith(".env") or "/.env" in lowered:
            return True
        if any(token in lowered for token in ("secret", "token", "credential", ".pem", ".key")):
            return True
        if path_text.startswith(".cache/") or path_text.startswith("tmp/"):
            return True
        return False

    repo_root: Path | None = None
    if normalized_repo:
        try:
            repo_root = Path(normalized_repo).resolve()
        except OSError:
            repo_root = None

    def _validate_repo_file(path_text: str, *, allow_missing: bool) -> tuple[bool, str]:
        normalized_path = _normalize_text(path_text, default="").replace("\\", "/")
        if not normalized_path:
            return False, "path_missing"
        if normalized_path.startswith("/") or _contains_parent_traversal(normalized_path):
            return False, "path_out_of_repo"
        if _is_sensitive_or_forbidden(normalized_path):
            return False, "path_forbidden"
        if repo_root is None:
            return False, "repo_root_missing"
        candidate = (repo_root / normalized_path)
        if candidate.exists() and candidate.is_symlink():
            return False, "path_symlink"
        if candidate.exists() and candidate.is_dir():
            return False, "path_directory"
        try:
            resolved = candidate.resolve(strict=False)
            resolved.relative_to(repo_root)
        except (OSError, ValueError):
            return False, "path_out_of_repo"
        if not allow_missing and not candidate.exists():
            return False, "path_missing"
        return True, ""

    expected_plan: list[str] = []
    for path_text in normalized_tracked_files:
        expected_plan.append(f"git checkout -- {path_text}")
    if normalized_strategy == "restore_tracked_and_remove_safe_untracked":
        for path_text in normalized_untracked_files:
            expected_plan.append(f"rm -f -- {path_text}")

    if (
        normalized_readiness_status == "rollback_readiness_not_required"
        or normalized_readiness_block_reason == "rollback_not_required"
    ):
        status = "rollback_execution_not_required"
        rollback_execution_block_reason = "rollback_not_required"
        human_review_required = bool(
            continuation_human_review_required or post_reentry_human_review_required
        )
        next_action = "no_rollback_required"
    elif human_review_required:
        status = "rollback_execution_blocked_manual_review"
        rollback_execution_block_reason = "blocked_manual_review_required"
        next_action = "manual_review_required"
    elif not bool(rollback_execution_allowed_next) or not bool(rollback_readiness_allowed):
        status = "rollback_execution_blocked_not_allowed"
        rollback_execution_block_reason = (
            normalized_readiness_block_reason or "rollback_execution_not_allowed"
        )
        next_action = "manual_review_required"
    elif normalized_strategy not in allowed_strategy_values:
        status = "rollback_execution_blocked_unsafe_plan"
        rollback_execution_block_reason = "rollback_strategy_invalid"
        human_review_required = True
        next_action = "manual_review_required"
    elif not normalized_target_files:
        status = "rollback_execution_blocked_insufficient_truth"
        rollback_execution_block_reason = "rollback_target_files_missing"
        human_review_required = True
        next_action = "manual_review_required"
    elif normalized_forbidden_files or normalized_unsafe_files or normalized_symlink_files or normalized_out_of_repo_files:
        status = "rollback_execution_blocked_unsafe_plan"
        rollback_execution_block_reason = "unsafe_rollback_file_set"
        human_review_required = True
        next_action = "manual_review_required"
    elif normalized_rollback_file_count > 20:
        status = "rollback_execution_blocked_unsafe_plan"
        rollback_execution_block_reason = "rollback_file_count_exceeded"
        human_review_required = True
        next_action = "manual_review_required"
    elif not normalized_execution_plan or expected_plan != normalized_execution_plan:
        status = "rollback_execution_blocked_unsafe_plan"
        rollback_execution_block_reason = "nondeterministic_rollback_plan"
        human_review_required = True
        next_action = "manual_review_required"
    elif not rollback_safe_worktree_state:
        status = "rollback_execution_blocked_unsafe_plan"
        rollback_execution_block_reason = "rollback_worktree_state_not_safe"
        human_review_required = True
        next_action = "manual_review_required"
    elif not normalized_repo or repo_root is None:
        status = "rollback_execution_blocked_insufficient_truth"
        rollback_execution_block_reason = "repository_path_missing"
        missing_inputs.append("repository_path")
        human_review_required = True
        next_action = "manual_review_required"
    else:
        rollback_execution_allowed = True
        rollback_execution_attempted = True
        human_review_required = False
        next_action = "manual_review_required"
        try:
            pre_status_cp = _run_git(normalized_repo, ["status", "--short"], timeout_seconds=10.0)
            pre_rollback_git_status_short = _normalize_text(pre_status_cp.stdout, default="")
        except (subprocess.TimeoutExpired, OSError):
            pre_rollback_git_status_short = ""

        for tracked_path in normalized_tracked_files:
            valid, reason = _validate_repo_file(tracked_path, allow_missing=True)
            if not valid:
                rollback_failed_files.append(tracked_path)
                rollback_skipped_files.append(tracked_path)
                rollback_command_results.append(
                    {
                        "command": ["git", "checkout", "--", tracked_path],
                        "exit_code": 2,
                        "timed_out": False,
                        "status": "blocked",
                        "block_reason": reason,
                    }
                )
                rollback_exit_code = 1
                continue
            command = ["git", "-C", normalized_repo, "checkout", "--", tracked_path]
            rollback_commands_attempted += 1
            try:
                cp = subprocess.run(
                    command,
                    text=True,
                    capture_output=True,
                    timeout=command_timeout_seconds,
                    check=False,
                )
                command_exit = int(cp.returncode)
                command_ok = command_exit == 0
                if command_ok:
                    rollback_restored_tracked_files.append(tracked_path)
                    rollback_commands_completed += 1
                else:
                    rollback_failed_files.append(tracked_path)
                    rollback_exit_code = 1
                rollback_command_results.append(
                    {
                        "command": command,
                        "exit_code": command_exit,
                        "timed_out": False,
                        "status": "completed" if command_ok else "failed",
                        "stdout_excerpt": _normalize_text(cp.stdout, default="")[:400],
                        "stderr_excerpt": _normalize_text(cp.stderr, default="")[:400],
                    }
                )
            except subprocess.TimeoutExpired as exc:
                rollback_timed_out = True
                rollback_failed_files.append(tracked_path)
                rollback_exit_code = 1
                rollback_command_results.append(
                    {
                        "command": command,
                        "exit_code": -1,
                        "timed_out": True,
                        "status": "timeout",
                        "stdout_excerpt": _normalize_text(exc.stdout, default="")[:400],
                        "stderr_excerpt": _normalize_text(exc.stderr, default="")[:400],
                    }
                )
            except OSError as exc:
                rollback_failed_files.append(tracked_path)
                rollback_exit_code = 1
                rollback_command_results.append(
                    {
                        "command": command,
                        "exit_code": -1,
                        "timed_out": False,
                        "status": "execution_error",
                        "stderr_excerpt": f"{type(exc).__name__}",
                    }
                )

        if normalized_strategy == "restore_tracked_and_remove_safe_untracked":
            for untracked_path in normalized_untracked_files:
                valid, reason = _validate_repo_file(untracked_path, allow_missing=True)
                if not valid:
                    rollback_failed_files.append(untracked_path)
                    rollback_skipped_files.append(untracked_path)
                    rollback_exit_code = 1
                    rollback_command_results.append(
                        {
                            "command": ["unlink", untracked_path],
                            "exit_code": 2,
                            "timed_out": False,
                            "status": "blocked",
                            "block_reason": reason,
                        }
                    )
                    continue
                if untracked_path not in allowed_safe_untracked_paths or untracked_path not in normalized_runtime_files:
                    rollback_failed_files.append(untracked_path)
                    rollback_skipped_files.append(untracked_path)
                    rollback_exit_code = 1
                    rollback_command_results.append(
                        {
                            "command": ["unlink", untracked_path],
                            "exit_code": 2,
                            "timed_out": False,
                            "status": "blocked",
                            "block_reason": "untracked_path_not_safe_runtime",
                        }
                    )
                    continue
                candidate = repo_root / untracked_path
                if candidate.exists():
                    if candidate.is_symlink() or candidate.is_dir():
                        rollback_failed_files.append(untracked_path)
                        rollback_skipped_files.append(untracked_path)
                        rollback_exit_code = 1
                        rollback_command_results.append(
                            {
                                "command": ["unlink", untracked_path],
                                "exit_code": 2,
                                "timed_out": False,
                                "status": "blocked",
                                "block_reason": "unsafe_unlink_target",
                            }
                        )
                        continue
                    rollback_commands_attempted += 1
                    try:
                        candidate.unlink()
                        rollback_removed_untracked_files.append(untracked_path)
                        rollback_commands_completed += 1
                        rollback_command_results.append(
                            {
                                "command": ["unlink", untracked_path],
                                "exit_code": 0,
                                "timed_out": False,
                                "status": "completed",
                            }
                        )
                    except OSError as exc:
                        rollback_failed_files.append(untracked_path)
                        rollback_exit_code = 1
                        rollback_command_results.append(
                            {
                                "command": ["unlink", untracked_path],
                                "exit_code": -1,
                                "timed_out": False,
                                "status": "execution_error",
                                "stderr_excerpt": f"{type(exc).__name__}",
                            }
                        )
                else:
                    rollback_skipped_files.append(untracked_path)
                    rollback_command_results.append(
                        {
                            "command": ["unlink", untracked_path],
                            "exit_code": 0,
                            "timed_out": False,
                            "status": "skipped_missing",
                        }
                    )

        try:
            post_status_cp = _run_git(normalized_repo, ["status", "--short"], timeout_seconds=10.0)
            post_rollback_git_status_short = _normalize_text(post_status_cp.stdout, default="")
        except (subprocess.TimeoutExpired, OSError):
            post_rollback_git_status_short = ""
            rollback_exit_code = 1

        post_rollback_dirty = bool(post_rollback_git_status_short)
        pre_paths = {
            _normalize_text(_parse_git_status_path(line), default="")
            for line in pre_rollback_git_status_short.splitlines()
        }
        pre_paths.discard("")
        post_paths = {
            _normalize_text(_parse_git_status_path(line), default="")
            for line in post_rollback_git_status_short.splitlines()
        }
        post_paths.discard("")
        target_set = set(normalized_target_files)
        post_rollback_expected_dirty_only = bool(
            all((path in pre_paths and path not in target_set) for path in post_paths)
        )
        target_paths_remaining_dirty = bool(any(path in post_paths for path in target_set))

        if rollback_timed_out:
            status = "rollback_execution_timeout"
            rollback_execution_failed = True
            rollback_execution_completed = False
            rollback_execution_block_reason = "rollback_timeout"
            human_review_required = True
            next_action = "manual_review_required"
            rollback_exit_code = 1
        elif rollback_failed_files:
            status = (
                "rollback_execution_partial_failure"
                if rollback_restored_tracked_files or rollback_removed_untracked_files
                else "rollback_execution_failed"
            )
            rollback_execution_failed = True
            rollback_execution_completed = False
            rollback_execution_block_reason = "rollback_command_failed"
            human_review_required = True
            next_action = "manual_review_required"
            rollback_exit_code = 1
        elif target_paths_remaining_dirty or not post_rollback_expected_dirty_only:
            status = "rollback_execution_partial_failure"
            rollback_execution_failed = True
            rollback_execution_completed = False
            rollback_execution_block_reason = "post_rollback_unexpected_dirty"
            human_review_required = True
            next_action = "manual_review_required"
            rollback_exit_code = 1
        else:
            status = "rollback_execution_completed"
            rollback_execution_completed = True
            rollback_execution_failed = False
            rollback_execution_block_reason = ""
            human_review_required = False
            next_action = "rollback_completed"
            rollback_exit_code = 0

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if status.startswith("rollback_execution_blocked") and not rollback_execution_block_reason:
        rollback_execution_block_reason = "blocked_insufficient_truth"

    return {
        "project_browser_autonomous_rollback_execution_status": status,
        "project_browser_autonomous_rollback_execution_rollback_execution_allowed": bool(
            rollback_execution_allowed
        ),
        "project_browser_autonomous_rollback_execution_rollback_execution_attempted": bool(
            rollback_execution_attempted
        ),
        "project_browser_autonomous_rollback_execution_rollback_execution_completed": bool(
            rollback_execution_completed
        ),
        "project_browser_autonomous_rollback_execution_rollback_execution_failed": bool(
            rollback_execution_failed
        ),
        "project_browser_autonomous_rollback_execution_rollback_execution_block_reason": (
            rollback_execution_block_reason
        ),
        "project_browser_autonomous_rollback_execution_rollback_reason": (
            normalized_rollback_reason
        ),
        "project_browser_autonomous_rollback_execution_rollback_strategy": normalized_strategy,
        "project_browser_autonomous_rollback_execution_rollback_target_files": (
            normalized_target_files
        ),
        "project_browser_autonomous_rollback_execution_rollback_tracked_files": (
            normalized_tracked_files
        ),
        "project_browser_autonomous_rollback_execution_rollback_untracked_files": (
            normalized_untracked_files
        ),
        "project_browser_autonomous_rollback_execution_rollback_runtime_files": (
            normalized_runtime_files
        ),
        "project_browser_autonomous_rollback_execution_rollback_restored_tracked_files": (
            _serialize_required_signals(rollback_restored_tracked_files)
        ),
        "project_browser_autonomous_rollback_execution_rollback_removed_untracked_files": (
            _serialize_required_signals(rollback_removed_untracked_files)
        ),
        "project_browser_autonomous_rollback_execution_rollback_skipped_files": (
            _serialize_required_signals(rollback_skipped_files)
        ),
        "project_browser_autonomous_rollback_execution_rollback_failed_files": (
            _serialize_required_signals(rollback_failed_files)
        ),
        "project_browser_autonomous_rollback_execution_rollback_command_results": (
            rollback_command_results
        ),
        "project_browser_autonomous_rollback_execution_rollback_commands_attempted": int(
            rollback_commands_attempted
        ),
        "project_browser_autonomous_rollback_execution_rollback_commands_completed": int(
            rollback_commands_completed
        ),
        "project_browser_autonomous_rollback_execution_rollback_exit_code": int(
            rollback_exit_code
        ),
        "project_browser_autonomous_rollback_execution_rollback_timed_out": bool(
            rollback_timed_out
        ),
        "project_browser_autonomous_rollback_execution_pre_rollback_git_status_short": (
            pre_rollback_git_status_short
        ),
        "project_browser_autonomous_rollback_execution_post_rollback_git_status_short": (
            post_rollback_git_status_short
        ),
        "project_browser_autonomous_rollback_execution_post_rollback_dirty": bool(
            post_rollback_dirty
        ),
        "project_browser_autonomous_rollback_execution_post_rollback_expected_dirty_only": bool(
            post_rollback_expected_dirty_only
        ),
        "project_browser_autonomous_rollback_execution_human_review_required": bool(
            human_review_required
        ),
        "project_browser_autonomous_rollback_execution_next_action": next_action,
        "project_browser_autonomous_rollback_execution_runtime_posture": runtime_posture,
        "project_browser_autonomous_rollback_execution_missing_inputs": (
            _serialize_required_signals(
                [
                    *missing_inputs,
                    normalized_readiness_status,
                    normalized_readiness_next_action,
                    normalized_readiness_block_reason,
                ]
            )
        ),
    }

def _build_project_browser_autonomous_post_rollback_continuation_gate_state(
    *,
    rollback_result_status: str,
    rollback_result_available: bool,
    rollback_result_selected: bool,
    rollback_result_class: str,
    rollback_result_block_reason: str,
    rollback_completed_cleanly: bool,
    rollback_completed_with_expected_dirty: bool,
    rollback_partial_failure: bool,
    rollback_failed: bool,
    rollback_timeout: bool,
    post_rollback_dirty: bool,
    post_rollback_expected_dirty_only: bool,
    rollback_remaining_dirty_files: list[str] | None,
    safe_to_continue_after_rollback: bool,
    safe_to_commit_after_rollback: bool,
    rollback_should_generate_fix_prompt: bool,
    rollback_should_generate_next_prompt: bool,
    rollback_should_invoke_codex: bool,
    rollback_should_execute_rollback: bool,
    rollback_should_commit: bool,
    rollback_should_stop: bool,
    rollback_stop_reason: str,
    rollback_human_review_required: bool,
    rollback_next_action: str,
    remaining_fix_attempts: int,
    remaining_cycles: int,
    failure_budget: int,
    failure_count: int,
    continuation_human_review_required: bool,
    continuation_stop_reason: str,
    rollback_execution_status: str,
    post_reentry_status: str,
) -> dict[str, Any]:
    allowed_statuses = {
        "post_rollback_continuation_allowed_fix",
        "post_rollback_continuation_blocked_manual_review",
        "post_rollback_continuation_blocked_fix_budget_exhausted",
        "post_rollback_continuation_blocked_failure_budget_exhausted",
        "post_rollback_continuation_not_required",
        "post_rollback_continuation_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "generate_fix_prompt_after_rollback",
        "manual_review_required",
        "no_rollback_required",
        "insufficient_truth",
    }
    runtime_posture = [
        "prompt187_post_rollback_continuation_gate",
        "metadata_only_controller",
        "authoritative_prompt186_source",
        "budget_gated_recovery",
        "no_prompt_generation",
        "no_codex_invocation",
        "no_rollback_execution",
        "no_commit",
    ]

    normalized_result_status = _normalize_text(rollback_result_status, default="insufficient_truth")
    normalized_result_class = _normalize_text(rollback_result_class, default="blocked")
    normalized_result_block_reason = _normalize_text(rollback_result_block_reason, default="")
    normalized_stop_reason = _normalize_text(rollback_stop_reason, default="")
    normalized_next_action = _normalize_text(rollback_next_action, default="manual_review_required")
    normalized_continuation_stop_reason = _normalize_text(continuation_stop_reason, default="")
    normalized_rollback_execution_status = _normalize_text(
        rollback_execution_status,
        default="insufficient_truth",
    )
    normalized_post_reentry_status = _normalize_text(
        post_reentry_status,
        default="insufficient_truth",
    )
    normalized_remaining_dirty_files = _normalize_string_list(
        rollback_remaining_dirty_files or []
    )

    normalized_remaining_fix_attempts = _as_non_negative_int(remaining_fix_attempts, default=0)
    normalized_remaining_cycles = _as_non_negative_int(remaining_cycles, default=0)
    normalized_failure_budget = _as_non_negative_int(failure_budget, default=1)
    normalized_failure_count = _as_non_negative_int(failure_count, default=0)

    fix_budget_available = normalized_remaining_fix_attempts > 0
    cycle_budget_available = normalized_remaining_cycles > 0
    failure_budget_available = normalized_failure_count <= normalized_failure_budget

    rollback_success = bool(rollback_completed_cleanly) or bool(
        rollback_completed_with_expected_dirty
    )
    unexpected_dirty_result = bool(
        normalized_result_status == "rollback_result_assimilation_unexpected_dirty"
        or (post_rollback_dirty and not post_rollback_expected_dirty_only)
    )
    hard_stop_unsafe_result = bool(
        rollback_partial_failure
        or rollback_failed
        or rollback_timeout
        or unexpected_dirty_result
        or rollback_human_review_required
        or continuation_human_review_required
    )

    status = "post_rollback_continuation_blocked_insufficient_truth"
    post_rollback_continuation_allowed = False
    post_rollback_continuation_block_reason = "blocked_insufficient_post_rollback_truth"
    post_rollback_continuation_kind = "none"
    post_rollback_next_action = "manual_review_required"
    should_generate_fix_prompt = False
    should_generate_next_prompt = False
    should_invoke_codex = False
    should_execute_rollback = False
    should_commit = False
    should_stop = True
    human_review_required = True
    stop_reason = "insufficient_post_rollback_truth"
    next_action = "manual_review_required"

    # Priority 1: hard-stop unsafe rollback results
    if hard_stop_unsafe_result:
        status = "post_rollback_continuation_blocked_manual_review"
        post_rollback_continuation_allowed = False
        post_rollback_continuation_block_reason = (
            normalized_stop_reason or "rollback_result_not_safe"
        )
        post_rollback_continuation_kind = "none"
        post_rollback_next_action = "manual_review_required"
        should_stop = True
        human_review_required = True
        stop_reason = normalized_stop_reason or "rollback_result_not_safe"
        next_action = "manual_review_required"
    # Priority 2: no rollback required
    elif normalized_result_status == "rollback_result_assimilation_not_required":
        status = "post_rollback_continuation_not_required"
        post_rollback_continuation_allowed = False
        post_rollback_continuation_block_reason = "rollback_not_required"
        post_rollback_continuation_kind = "none"
        post_rollback_next_action = "no_rollback_required"
        should_stop = False
        human_review_required = False
        stop_reason = ""
        next_action = "no_rollback_required"
    # Priority 3: budget exhaustion
    elif rollback_success and not fix_budget_available:
        status = "post_rollback_continuation_blocked_fix_budget_exhausted"
        post_rollback_continuation_allowed = False
        post_rollback_continuation_block_reason = "fix_budget_exhausted_after_rollback"
        post_rollback_continuation_kind = "fix"
        post_rollback_next_action = "manual_review_required"
        should_stop = True
        human_review_required = True
        stop_reason = "fix_budget_exhausted_after_rollback"
        next_action = "manual_review_required"
    elif rollback_success and not failure_budget_available:
        status = "post_rollback_continuation_blocked_failure_budget_exhausted"
        post_rollback_continuation_allowed = False
        post_rollback_continuation_block_reason = (
            "failure_budget_exhausted_after_rollback"
        )
        post_rollback_continuation_kind = "fix"
        post_rollback_next_action = "manual_review_required"
        should_stop = True
        human_review_required = True
        stop_reason = "failure_budget_exhausted_after_rollback"
        next_action = "manual_review_required"
    # Priority 4: post-rollback fix continuation allowed
    elif (
        rollback_success
        and bool(safe_to_continue_after_rollback)
        and bool(rollback_should_generate_fix_prompt)
        and not bool(rollback_human_review_required)
        and fix_budget_available
        and failure_budget_available
    ):
        status = "post_rollback_continuation_allowed_fix"
        post_rollback_continuation_allowed = True
        post_rollback_continuation_block_reason = ""
        post_rollback_continuation_kind = "fix"
        post_rollback_next_action = "generate_fix_prompt_after_rollback"
        should_generate_fix_prompt = True
        should_generate_next_prompt = False
        should_invoke_codex = False
        should_execute_rollback = False
        should_commit = False
        should_stop = False
        human_review_required = False
        stop_reason = ""
        next_action = "generate_fix_prompt_after_rollback"
    # Priority 5: insufficient truth
    else:
        status = "post_rollback_continuation_blocked_insufficient_truth"
        post_rollback_continuation_allowed = False
        post_rollback_continuation_block_reason = (
            "blocked_insufficient_post_rollback_truth"
        )
        post_rollback_continuation_kind = "none"
        post_rollback_next_action = "manual_review_required"
        should_generate_fix_prompt = False
        should_generate_next_prompt = False
        should_invoke_codex = False
        should_execute_rollback = False
        should_commit = False
        should_stop = True
        human_review_required = True
        stop_reason = "insufficient_post_rollback_truth"
        next_action = "manual_review_required"

    # Prompt187 commit-safety invariant.
    should_commit = False
    safe_to_commit_after_rollback = False

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"
    if post_rollback_next_action not in allowed_next_actions:
        post_rollback_next_action = next_action

    return {
        "project_browser_autonomous_post_rollback_continuation_gate_status": status,
        "project_browser_autonomous_post_rollback_continuation_gate_post_rollback_continuation_allowed": bool(
            post_rollback_continuation_allowed
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_post_rollback_continuation_block_reason": (
            post_rollback_continuation_block_reason
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_post_rollback_continuation_kind": (
            post_rollback_continuation_kind
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_post_rollback_next_action": (
            post_rollback_next_action
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_source_rollback_result_status": (
            normalized_result_status
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_source_rollback_result_class": (
            normalized_result_class
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_rollback_completed_cleanly": bool(
            rollback_completed_cleanly
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_rollback_completed_with_expected_dirty": bool(
            rollback_completed_with_expected_dirty
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_rollback_failed": bool(
            rollback_failed
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_rollback_timeout": bool(
            rollback_timeout
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_post_rollback_dirty": bool(
            post_rollback_dirty
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_post_rollback_expected_dirty_only": bool(
            post_rollback_expected_dirty_only
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_remaining_fix_attempts": int(
            normalized_remaining_fix_attempts
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_remaining_cycles": int(
            normalized_remaining_cycles
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_failure_budget": int(
            normalized_failure_budget
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_failure_count": int(
            normalized_failure_count
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_fix_budget_available": bool(
            fix_budget_available
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_cycle_budget_available": bool(
            cycle_budget_available
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_failure_budget_available": bool(
            failure_budget_available
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_should_generate_fix_prompt": bool(
            should_generate_fix_prompt
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_should_generate_next_prompt": bool(
            should_generate_next_prompt
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_should_invoke_codex": bool(
            should_invoke_codex
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_should_execute_rollback": bool(
            should_execute_rollback
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_should_commit": bool(
            should_commit
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_should_stop": bool(
            should_stop
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_safe_to_continue_after_rollback": bool(
            safe_to_continue_after_rollback
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_safe_to_commit_after_rollback": bool(
            safe_to_commit_after_rollback
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_human_review_required": bool(
            human_review_required
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_stop_reason": (
            stop_reason
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_next_action": next_action,
        "project_browser_autonomous_post_rollback_continuation_gate_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_post_rollback_continuation_gate_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_result_status,
                    normalized_result_class,
                    normalized_result_block_reason,
                    normalized_next_action,
                    normalized_stop_reason,
                    normalized_continuation_stop_reason,
                    normalized_rollback_execution_status,
                    normalized_post_reentry_status,
                    "rollback_result_unavailable"
                    if not rollback_result_available
                    else "",
                    "rollback_result_not_selected"
                    if not rollback_result_selected
                    else "",
                    "rollback_should_stop"
                    if rollback_should_stop
                    else "",
                    "rollback_should_generate_next_prompt_true"
                    if rollback_should_generate_next_prompt
                    else "",
                    "rollback_should_invoke_codex_true"
                    if rollback_should_invoke_codex
                    else "",
                    "rollback_should_execute_true"
                    if rollback_should_execute_rollback
                    else "",
                    "rollback_should_commit_true"
                    if rollback_should_commit
                    else "",
                    "rollback_remaining_dirty_files"
                    if normalized_remaining_dirty_files
                    else "",
                ]
            )
        ),
    }

def _build_project_browser_autonomous_post_rollback_fix_handoff_state(
    *,
    post_rollback_status: str,
    post_rollback_continuation_allowed: bool,
    post_rollback_continuation_kind: str,
    post_rollback_next_action: str,
    rollback_completed_cleanly: bool,
    rollback_completed_with_expected_dirty: bool,
    safe_to_continue_after_rollback: bool,
    safe_to_commit_after_rollback: bool,
    remaining_fix_attempts: int,
    fix_budget_available: bool,
    cycle_budget_available: bool,
    failure_budget_available: bool,
    should_generate_fix_prompt: bool,
    should_generate_next_prompt: bool,
    should_invoke_codex: bool,
    should_execute_rollback: bool,
    should_commit: bool,
    should_stop: bool,
    human_review_required: bool,
    stop_reason: str,
    next_action: str,
    source_rollback_result_class: str,
) -> dict[str, Any]:
    allowed_statuses = {
        "post_rollback_fix_handoff_allowed",
        "post_rollback_fix_handoff_blocked",
        "post_rollback_fix_handoff_blocked_manual_review",
        "post_rollback_fix_handoff_blocked_budget_exhausted",
        "post_rollback_fix_handoff_blocked_not_allowed",
        "post_rollback_fix_handoff_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "generate_fix_prompt_after_rollback",
        "manual_review_required",
        "no_rollback_required",
        "insufficient_truth",
    }
    runtime_posture = [
        "prompt188_post_rollback_fix_handoff",
        "metadata_only_handoff",
        "connect_prompt187_to_fix_readiness_generation",
        "no_safety_bypass",
        "no_codex_invocation",
        "no_rollback_execution",
        "no_commit",
    ]

    normalized_post_rollback_status = _normalize_text(
        post_rollback_status,
        default="insufficient_truth",
    )
    normalized_post_rollback_kind = _normalize_text(
        post_rollback_continuation_kind,
        default="none",
    )
    if normalized_post_rollback_kind not in {"fix", "next", "none"}:
        normalized_post_rollback_kind = "none"
    normalized_post_rollback_next_action = _normalize_text(
        post_rollback_next_action,
        default="manual_review_required",
    )
    normalized_stop_reason = _normalize_text(stop_reason, default="")
    normalized_next_action = _normalize_text(next_action, default="manual_review_required")
    normalized_source_rollback_result_class = _normalize_text(
        source_rollback_result_class,
        default="blocked",
    )
    normalized_remaining_fix_attempts = _as_non_negative_int(remaining_fix_attempts, default=0)

    status = "post_rollback_fix_handoff_blocked_insufficient_truth"
    post_rollback_fix_handoff_available = False
    post_rollback_fix_handoff_allowed = False
    post_rollback_fix_handoff_block_reason = "blocked_insufficient_post_rollback_truth"
    post_rollback_fix_prompt_kind = "none"
    post_rollback_fix_prompt_reason = ""
    fix_readiness_refresh_allowed = False
    fix_readiness_refresh_source = ""
    fix_generation_refresh_allowed = False
    fix_generation_refresh_source = ""
    computed_should_generate_fix_prompt = False
    computed_should_generate_next_prompt = False
    computed_should_invoke_codex = False
    computed_should_execute_rollback = False
    computed_should_commit = False
    computed_human_review_required = True
    computed_next_action = "manual_review_required"

    handoff_allow_rule = bool(
        normalized_post_rollback_status == "post_rollback_continuation_allowed_fix"
        and post_rollback_continuation_allowed
        and normalized_post_rollback_kind == "fix"
        and should_generate_fix_prompt
        and not should_generate_next_prompt
        and not should_invoke_codex
        and not should_execute_rollback
        and not should_commit
        and safe_to_continue_after_rollback
        and not safe_to_commit_after_rollback
        and fix_budget_available
        and failure_budget_available
        and not human_review_required
    )
    blocked_budget = bool(
        normalized_post_rollback_status
        in {
            "post_rollback_continuation_blocked_fix_budget_exhausted",
            "post_rollback_continuation_blocked_failure_budget_exhausted",
        }
        or (
            (rollback_completed_cleanly or rollback_completed_with_expected_dirty)
            and (not fix_budget_available or not failure_budget_available)
        )
    )
    blocked_manual_review = bool(
        human_review_required
        or normalized_post_rollback_status
        in {
            "post_rollback_continuation_blocked_manual_review",
            "post_rollback_continuation_blocked_not_allowed",
        }
    )
    blocked_not_allowed = bool(
        normalized_post_rollback_status == "post_rollback_continuation_not_required"
        or (
            not post_rollback_continuation_allowed
            and normalized_post_rollback_status not in {"insufficient_truth"}
            and not blocked_budget
            and not blocked_manual_review
        )
    )

    if handoff_allow_rule:
        status = "post_rollback_fix_handoff_allowed"
        post_rollback_fix_handoff_available = True
        post_rollback_fix_handoff_allowed = True
        post_rollback_fix_handoff_block_reason = ""
        post_rollback_fix_prompt_kind = "fix"
        post_rollback_fix_prompt_reason = "rollback_recovered_unsafe_change"
        fix_readiness_refresh_allowed = True
        fix_readiness_refresh_source = "post_rollback_continuation"
        fix_generation_refresh_allowed = True
        fix_generation_refresh_source = "post_rollback_continuation"
        computed_should_generate_fix_prompt = True
        computed_should_generate_next_prompt = False
        computed_should_invoke_codex = False
        computed_should_execute_rollback = False
        computed_should_commit = False
        computed_human_review_required = False
        computed_next_action = "generate_fix_prompt_after_rollback"
    elif blocked_manual_review:
        status = "post_rollback_fix_handoff_blocked_manual_review"
        post_rollback_fix_handoff_available = False
        post_rollback_fix_handoff_allowed = False
        post_rollback_fix_handoff_block_reason = (
            normalized_stop_reason or "manual_review_required"
        )
        computed_human_review_required = True
        computed_next_action = (
            normalized_next_action
            if normalized_next_action in allowed_next_actions
            else "manual_review_required"
        )
    elif blocked_budget:
        status = "post_rollback_fix_handoff_blocked_budget_exhausted"
        post_rollback_fix_handoff_available = False
        post_rollback_fix_handoff_allowed = False
        post_rollback_fix_handoff_block_reason = (
            "fix_or_failure_budget_exhausted_after_rollback"
        )
        computed_human_review_required = True
        computed_next_action = "manual_review_required"
    elif blocked_not_allowed:
        status = "post_rollback_fix_handoff_blocked_not_allowed"
        post_rollback_fix_handoff_available = False
        post_rollback_fix_handoff_allowed = False
        post_rollback_fix_handoff_block_reason = (
            "post_rollback_fix_continuation_not_allowed"
        )
        computed_human_review_required = bool(human_review_required)
        computed_next_action = (
            normalized_next_action
            if normalized_next_action in allowed_next_actions
            else "manual_review_required"
        )
    elif normalized_post_rollback_status in {"insufficient_truth", ""}:
        status = "post_rollback_fix_handoff_blocked_insufficient_truth"
        post_rollback_fix_handoff_available = False
        post_rollback_fix_handoff_allowed = False
        post_rollback_fix_handoff_block_reason = (
            "blocked_insufficient_post_rollback_truth"
        )
        computed_human_review_required = True
        computed_next_action = "manual_review_required"
    else:
        status = "post_rollback_fix_handoff_blocked"
        post_rollback_fix_handoff_available = False
        post_rollback_fix_handoff_allowed = False
        post_rollback_fix_handoff_block_reason = (
            normalized_stop_reason or "post_rollback_fix_handoff_blocked"
        )
        computed_human_review_required = bool(human_review_required)
        computed_next_action = (
            normalized_next_action
            if normalized_next_action in allowed_next_actions
            else "manual_review_required"
        )

    # Commit boundary invariant for rollback-derived handoff.
    computed_should_commit = False

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if computed_next_action not in allowed_next_actions:
        computed_next_action = "insufficient_truth"

    return {
        "project_browser_autonomous_post_rollback_fix_handoff_status": status,
        "project_browser_autonomous_post_rollback_fix_handoff_post_rollback_fix_handoff_available": bool(
            post_rollback_fix_handoff_available
        ),
        "project_browser_autonomous_post_rollback_fix_handoff_post_rollback_fix_handoff_allowed": bool(
            post_rollback_fix_handoff_allowed
        ),
        "project_browser_autonomous_post_rollback_fix_handoff_post_rollback_fix_handoff_block_reason": (
            post_rollback_fix_handoff_block_reason
        ),
        "project_browser_autonomous_post_rollback_fix_handoff_post_rollback_fix_prompt_kind": (
            post_rollback_fix_prompt_kind
        ),
        "project_browser_autonomous_post_rollback_fix_handoff_post_rollback_fix_prompt_reason": (
            post_rollback_fix_prompt_reason
        ),
        "project_browser_autonomous_post_rollback_fix_handoff_source_post_rollback_status": (
            normalized_post_rollback_status
        ),
        "project_browser_autonomous_post_rollback_fix_handoff_source_rollback_result_class": (
            normalized_source_rollback_result_class
        ),
        "project_browser_autonomous_post_rollback_fix_handoff_fix_readiness_refresh_allowed": bool(
            fix_readiness_refresh_allowed
        ),
        "project_browser_autonomous_post_rollback_fix_handoff_fix_readiness_refresh_source": (
            fix_readiness_refresh_source
        ),
        "project_browser_autonomous_post_rollback_fix_handoff_fix_generation_refresh_allowed": bool(
            fix_generation_refresh_allowed
        ),
        "project_browser_autonomous_post_rollback_fix_handoff_fix_generation_refresh_source": (
            fix_generation_refresh_source
        ),
        "project_browser_autonomous_post_rollback_fix_handoff_should_generate_fix_prompt": bool(
            computed_should_generate_fix_prompt
        ),
        "project_browser_autonomous_post_rollback_fix_handoff_should_generate_next_prompt": bool(
            computed_should_generate_next_prompt
        ),
        "project_browser_autonomous_post_rollback_fix_handoff_should_invoke_codex": bool(
            computed_should_invoke_codex
        ),
        "project_browser_autonomous_post_rollback_fix_handoff_should_execute_rollback": bool(
            computed_should_execute_rollback
        ),
        "project_browser_autonomous_post_rollback_fix_handoff_should_commit": bool(
            computed_should_commit
        ),
        "project_browser_autonomous_post_rollback_fix_handoff_human_review_required": bool(
            computed_human_review_required
        ),
        "project_browser_autonomous_post_rollback_fix_handoff_next_action": (
            computed_next_action
        ),
        "project_browser_autonomous_post_rollback_fix_handoff_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_post_rollback_fix_handoff_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_post_rollback_status,
                    normalized_post_rollback_next_action,
                    normalized_post_rollback_kind,
                    normalized_stop_reason,
                    normalized_next_action,
                    normalized_source_rollback_result_class,
                    "remaining_fix_attempts_zero"
                    if normalized_remaining_fix_attempts <= 0
                    else "",
                    "fix_budget_unavailable" if not fix_budget_available else "",
                    "failure_budget_unavailable" if not failure_budget_available else "",
                    "cycle_budget_unavailable" if not cycle_budget_available else "",
                    "rollback_should_stop_true" if should_stop else "",
                ]
            )
        ),
    }

def _build_project_browser_autonomous_post_rollback_fix_reentry_propagation_state(
    *,
    source_fix_generation_status: str,
    source_fix_prompt_generated: bool,
    source_fix_prompt_path: str,
    source_fix_prompt_handoff_write_completed: bool,
    source_fix_human_review_required: bool,
    source_fix_next_action: str,
    source_post_rollback_input_available: bool,
    source_post_rollback_input_consumed: bool,
    source_post_rollback_input_effective: bool,
    source_post_rollback_input_source: str,
    source_post_rollback_input_reason: str,
    source_post_rollback_refresh_applied: bool,
    post_rollback_handoff_allowed: bool,
    post_rollback_handoff_available: bool,
    post_rollback_handoff_prompt_kind: str,
    post_rollback_handoff_human_review_required: bool,
    post_rollback_handoff_should_generate_fix_prompt: bool,
    post_rollback_handoff_should_generate_next_prompt: bool,
    post_rollback_handoff_should_invoke_codex: bool,
    post_rollback_handoff_should_execute_rollback: bool,
    post_rollback_handoff_should_commit: bool,
    post_rollback_handoff_next_action: str,
    post_rollback_continuation_status: str,
    post_rollback_continuation_next_action: str,
    rollback_result_status: str,
    existing_reentry_readiness_status: str,
    existing_reentry_routing_status: str,
) -> dict[str, Any]:
    allowed_statuses = {
        "post_rollback_fix_reentry_propagation_allowed",
        "post_rollback_fix_reentry_propagation_blocked",
        "post_rollback_fix_reentry_propagation_blocked_manual_review",
        "post_rollback_fix_reentry_propagation_blocked_unsafe_path",
        "post_rollback_fix_reentry_propagation_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "prepare_post_rollback_fix_reentry",
        "manual_review_required",
        "no_rollback_required",
        "insufficient_truth",
    }
    fix_allowed_path = "/tmp/codex-local-runner-decision/generated_fix_prompt.txt"
    max_prompt_size_bytes = 20000
    runtime_posture = [
        "prompt190_post_rollback_fix_reentry_propagation",
        "metadata_only_propagation",
        "reuse_existing_reentry_path",
        "no_codex_invocation",
        "no_rollback_execution",
        "no_commit",
    ]

    normalized_fix_generation_status = _normalize_text(
        source_fix_generation_status,
        default="insufficient_truth",
    )
    normalized_fix_prompt_path = _normalize_text(source_fix_prompt_path, default="")
    normalized_fix_next_action = _normalize_text(source_fix_next_action, default="")
    normalized_post_rollback_input_source = _normalize_text(
        source_post_rollback_input_source,
        default="",
    )
    normalized_post_rollback_input_reason = _normalize_text(
        source_post_rollback_input_reason,
        default="",
    )
    normalized_post_rollback_handoff_prompt_kind = _normalize_text(
        post_rollback_handoff_prompt_kind,
        default="none",
    )
    normalized_post_rollback_handoff_next_action = _normalize_text(
        post_rollback_handoff_next_action,
        default="manual_review_required",
    )
    normalized_post_rollback_continuation_status = _normalize_text(
        post_rollback_continuation_status,
        default="insufficient_truth",
    )
    normalized_post_rollback_continuation_next_action = _normalize_text(
        post_rollback_continuation_next_action,
        default="manual_review_required",
    )
    normalized_rollback_result_status = _normalize_text(
        rollback_result_status,
        default="insufficient_truth",
    )
    normalized_existing_reentry_readiness_status = _normalize_text(
        existing_reentry_readiness_status,
        default="insufficient_truth",
    )
    normalized_existing_reentry_routing_status = _normalize_text(
        existing_reentry_routing_status,
        default="insufficient_truth",
    )

    path_obj = Path(normalized_fix_prompt_path) if normalized_fix_prompt_path else None
    path_is_exact = normalized_fix_prompt_path == fix_allowed_path
    path_exists = bool(path_obj and path_obj.exists())
    path_is_file = bool(path_obj and path_obj.is_file())
    path_is_symlink = bool(path_obj and path_obj.is_symlink())
    file_size_bytes = 0
    if path_obj and path_exists and path_is_file and not path_is_symlink:
        try:
            file_size_bytes = _as_non_negative_int(path_obj.stat().st_size, default=0)
        except OSError:
            file_size_bytes = 0
    file_non_empty = file_size_bytes > 0
    file_too_large = file_size_bytes > max_prompt_size_bytes
    path_safe = bool(
        path_is_exact
        and path_exists
        and path_is_file
        and not path_is_symlink
        and file_non_empty
        and not file_too_large
    )

    manual_review_or_stop = bool(
        normalized_post_rollback_handoff_next_action == "manual_review_required"
        or normalized_post_rollback_continuation_next_action == "manual_review_required"
        or normalized_post_rollback_continuation_status
        in {
            "post_rollback_continuation_blocked_manual_review",
            "post_rollback_continuation_blocked_fix_budget_exhausted",
            "post_rollback_continuation_blocked_failure_budget_exhausted",
            "post_rollback_continuation_blocked_insufficient_truth",
        }
        or normalized_rollback_result_status
        in {
            "rollback_result_assimilation_partial_failure",
            "rollback_result_assimilation_failed",
            "rollback_result_assimilation_timeout",
            "rollback_result_assimilation_unexpected_dirty",
            "rollback_result_assimilation_blocked_insufficient_truth",
        }
    )

    allow_rule = bool(
        source_post_rollback_input_effective
        and source_post_rollback_refresh_applied
        and source_fix_prompt_generated
        and source_fix_prompt_handoff_write_completed
        and normalized_post_rollback_handoff_prompt_kind == "fix"
        and not source_fix_human_review_required
        and post_rollback_handoff_allowed
        and post_rollback_handoff_available
        and post_rollback_handoff_should_generate_fix_prompt
        and not post_rollback_handoff_should_generate_next_prompt
        and not post_rollback_handoff_should_invoke_codex
        and not post_rollback_handoff_should_execute_rollback
        and not post_rollback_handoff_should_commit
        and not post_rollback_handoff_human_review_required
        and path_safe
    )

    propagation_block_reason = ""
    if not source_post_rollback_input_effective:
        propagation_block_reason = "blocked_post_rollback_fix_input_not_effective"
    elif not source_post_rollback_refresh_applied:
        propagation_block_reason = "blocked_fix_generation_refresh_not_applied"
    elif not source_fix_prompt_generated or not source_fix_prompt_handoff_write_completed:
        propagation_block_reason = "blocked_fix_prompt_not_generated"
    elif not path_safe:
        propagation_block_reason = "blocked_generated_fix_prompt_path_unsafe"
    elif normalized_post_rollback_handoff_prompt_kind != "fix":
        propagation_block_reason = "blocked_mismatched_prompt_kind"
    elif source_fix_human_review_required or post_rollback_handoff_human_review_required:
        propagation_block_reason = "blocked_human_review_required"
    elif post_rollback_handoff_should_invoke_codex:
        propagation_block_reason = "blocked_codex_invocation_requested_unexpectedly"
    elif post_rollback_handoff_should_execute_rollback:
        propagation_block_reason = "blocked_rollback_requested_unexpectedly"
    elif post_rollback_handoff_should_commit:
        propagation_block_reason = "blocked_commit_requested_unexpectedly"
    elif not allow_rule:
        propagation_block_reason = "blocked_insufficient_post_rollback_reentry_truth"

    status = "post_rollback_fix_reentry_propagation_blocked"
    propagation_allowed = False
    propagation_applied = False
    generated_prompt_reentry_refresh_allowed = False
    generated_prompt_reentry_prompt_kind = "none"
    generated_prompt_reentry_prompt_path = ""
    generated_prompt_reentry_source = ""
    reentry_routing_refresh_allowed = False
    reentry_routing_refresh_source = ""
    reentry_invocation_preparation_allowed = False
    should_invoke_codex = False
    should_execute_rollback = False
    should_commit = False
    human_review_required = True
    next_action = "manual_review_required"

    if manual_review_or_stop:
        status = "post_rollback_fix_reentry_propagation_blocked_manual_review"
        propagation_allowed = False
        propagation_applied = False
        human_review_required = True
        next_action = (
            normalized_post_rollback_handoff_next_action
            if normalized_post_rollback_handoff_next_action in allowed_next_actions
            else "manual_review_required"
        )
    elif allow_rule:
        status = "post_rollback_fix_reentry_propagation_allowed"
        propagation_allowed = True
        propagation_applied = True
        generated_prompt_reentry_refresh_allowed = True
        generated_prompt_reentry_prompt_kind = "fix"
        generated_prompt_reentry_prompt_path = normalized_fix_prompt_path
        generated_prompt_reentry_source = "post_rollback_fix_generation"
        reentry_routing_refresh_allowed = True
        reentry_routing_refresh_source = "post_rollback_fix_generation"
        reentry_invocation_preparation_allowed = True
        should_invoke_codex = False
        should_execute_rollback = False
        should_commit = False
        human_review_required = False
        propagation_block_reason = ""
        next_action = "prepare_post_rollback_fix_reentry"
    elif not path_safe and normalized_fix_prompt_path:
        status = "post_rollback_fix_reentry_propagation_blocked_unsafe_path"
        propagation_allowed = False
        propagation_applied = False
        human_review_required = True
        next_action = "manual_review_required"
    elif propagation_block_reason == "blocked_insufficient_post_rollback_reentry_truth":
        status = "post_rollback_fix_reentry_propagation_blocked_insufficient_truth"
        propagation_allowed = False
        propagation_applied = False
        human_review_required = True
        next_action = "manual_review_required"
    else:
        status = "post_rollback_fix_reentry_propagation_blocked"
        propagation_allowed = False
        propagation_applied = False
        human_review_required = bool(
            source_fix_human_review_required or post_rollback_handoff_human_review_required
        )
        next_action = (
            normalized_post_rollback_handoff_next_action
            if normalized_post_rollback_handoff_next_action in allowed_next_actions
            else "manual_review_required"
        )

    # Commit/Codex/Rollback execution boundaries for Prompt190.
    should_invoke_codex = False
    should_execute_rollback = False
    should_commit = False

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"

    return {
        "project_browser_autonomous_post_rollback_fix_reentry_propagation_status": status,
        "project_browser_autonomous_post_rollback_fix_reentry_propagation_propagation_allowed": bool(
            propagation_allowed
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_propagation_propagation_applied": bool(
            propagation_applied
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_propagation_propagation_block_reason": (
            propagation_block_reason
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_propagation_source_fix_generation_status": (
            normalized_fix_generation_status
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_propagation_source_fix_prompt_generated": bool(
            source_fix_prompt_generated
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_propagation_source_fix_prompt_path": (
            normalized_fix_prompt_path
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_propagation_source_post_rollback_input_effective": bool(
            source_post_rollback_input_effective
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_propagation_generated_prompt_reentry_refresh_allowed": bool(
            generated_prompt_reentry_refresh_allowed
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_propagation_generated_prompt_reentry_prompt_kind": (
            generated_prompt_reentry_prompt_kind
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_propagation_generated_prompt_reentry_prompt_path": (
            generated_prompt_reentry_prompt_path
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_propagation_generated_prompt_reentry_source": (
            generated_prompt_reentry_source
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_propagation_reentry_routing_refresh_allowed": bool(
            reentry_routing_refresh_allowed
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_propagation_reentry_routing_refresh_source": (
            reentry_routing_refresh_source
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_propagation_reentry_invocation_preparation_allowed": bool(
            reentry_invocation_preparation_allowed
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_propagation_should_invoke_codex": bool(
            should_invoke_codex
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_propagation_should_execute_rollback": bool(
            should_execute_rollback
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_propagation_should_commit": bool(
            should_commit
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_propagation_human_review_required": bool(
            human_review_required
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_propagation_next_action": (
            next_action
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_propagation_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_propagation_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_fix_generation_status,
                    normalized_fix_next_action,
                    normalized_post_rollback_input_source,
                    normalized_post_rollback_input_reason,
                    normalized_post_rollback_handoff_prompt_kind,
                    normalized_post_rollback_handoff_next_action,
                    normalized_post_rollback_continuation_status,
                    normalized_post_rollback_continuation_next_action,
                    normalized_rollback_result_status,
                    normalized_existing_reentry_readiness_status,
                    normalized_existing_reentry_routing_status,
                    "post_rollback_input_unavailable"
                    if not source_post_rollback_input_available
                    else "",
                    "post_rollback_input_not_consumed"
                    if not source_post_rollback_input_consumed
                    else "",
                    "fix_prompt_path_not_exact" if not path_is_exact else "",
                    "fix_prompt_path_missing" if not path_exists else "",
                    "fix_prompt_path_not_file" if path_exists and not path_is_file else "",
                    "fix_prompt_path_symlink" if path_is_symlink else "",
                    "fix_prompt_file_empty" if path_exists and not file_non_empty else "",
                    "fix_prompt_file_too_large" if file_too_large else "",
                    "manual_review_or_stop" if manual_review_or_stop else "",
                ]
            )
        ),
    }

def _build_project_browser_autonomous_post_rollback_fix_reentry_checkpoint_state(
    *,
    prompt190_status: str,
    prompt190_propagation_allowed: bool,
    prompt190_propagation_applied: bool,
    prompt190_propagation_block_reason: str,
    prompt190_generated_prompt_reentry_source: str,
    prompt190_generated_prompt_reentry_prompt_kind: str,
    prompt190_generated_prompt_reentry_prompt_path: str,
    prompt190_reentry_routing_refresh_allowed: bool,
    prompt190_reentry_invocation_preparation_allowed: bool,
    prompt190_human_review_required: bool,
    prompt190_should_invoke_codex: bool,
    prompt190_should_execute_rollback: bool,
    prompt190_should_commit: bool,
    prompt190_next_action: str,
    generated_reentry_readiness_status: str,
    generated_reentry_allowed: bool,
    generated_reentry_prompt_kind: str,
    generated_reentry_prompt_path: str,
    generated_reentry_human_review_required: bool,
    generated_reentry_routing_status: str,
    generated_reentry_routing_allowed: bool,
    generated_reentry_routing_prompt_kind: str,
    generated_reentry_routing_prompt_path: str,
    generated_reentry_routing_human_review_required: bool,
    prompt_selection_reentry_refresh_allowed: bool,
    prompt_selection_reentry_refresh_kind: str,
    prompt_selection_reentry_refresh_path: str,
    codex_invocation_reentry_selected_prompt_ready: bool,
    codex_invocation_reentry_selected_prompt_kind: str,
    codex_invocation_reentry_selected_prompt_path: str,
    codex_write_reentry_prepared: bool,
    codex_write_reentry_selected_prompt_ready: bool,
    codex_write_reentry_max_invocations: int,
    codex_reentry_post_rollback_preparation_allowed: bool,
    codex_reentry_post_rollback_preparation_source: str,
) -> dict[str, Any]:
    allowed_statuses = {
        "post_rollback_fix_reentry_checkpoint_ready",
        "post_rollback_fix_reentry_checkpoint_blocked",
        "post_rollback_fix_reentry_checkpoint_blocked_manual_review",
        "post_rollback_fix_reentry_checkpoint_blocked_unsafe_path",
        "post_rollback_fix_reentry_checkpoint_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "prepare_bounded_post_rollback_fix_codex_reentry",
        "manual_review_required",
        "no_rollback_required",
        "insufficient_truth",
    }
    fixed_prompt_path = "/tmp/codex-local-runner-decision/generated_fix_prompt.txt"
    max_prompt_size_bytes = 20000
    runtime_posture = [
        "prompt191_post_rollback_fix_reentry_checkpoint",
        "metadata_only_final_recompute",
        "no_codex_invocation",
        "no_rollback_execution",
        "no_commit",
    ]

    normalized_prompt190_status = _normalize_text(prompt190_status, default="insufficient_truth")
    normalized_prompt190_block_reason = _normalize_text(
        prompt190_propagation_block_reason,
        default="",
    )
    normalized_prompt190_source = _normalize_text(
        prompt190_generated_prompt_reentry_source,
        default="",
    )
    normalized_prompt190_kind = _normalize_text(
        prompt190_generated_prompt_reentry_prompt_kind,
        default="none",
    )
    normalized_prompt190_path = _normalize_text(
        prompt190_generated_prompt_reentry_prompt_path,
        default="",
    )
    normalized_prompt190_next_action = _normalize_text(prompt190_next_action, default="")

    normalized_readiness_status = _normalize_text(
        generated_reentry_readiness_status,
        default="insufficient_truth",
    )
    normalized_readiness_kind = _normalize_text(generated_reentry_prompt_kind, default="none")
    normalized_readiness_path = _normalize_text(generated_reentry_prompt_path, default="")
    normalized_routing_status = _normalize_text(
        generated_reentry_routing_status,
        default="insufficient_truth",
    )
    normalized_routing_kind = _normalize_text(
        generated_reentry_routing_prompt_kind,
        default="none",
    )
    normalized_routing_path = _normalize_text(
        generated_reentry_routing_prompt_path,
        default="",
    )
    normalized_prompt_selection_kind = _normalize_text(
        prompt_selection_reentry_refresh_kind,
        default="none",
    )
    normalized_prompt_selection_path = _normalize_text(
        prompt_selection_reentry_refresh_path,
        default="",
    )
    normalized_codex_invocation_kind = _normalize_text(
        codex_invocation_reentry_selected_prompt_kind,
        default="none",
    )
    normalized_codex_invocation_path = _normalize_text(
        codex_invocation_reentry_selected_prompt_path,
        default="",
    )
    normalized_codex_reentry_prep_source = _normalize_text(
        codex_reentry_post_rollback_preparation_source,
        default="",
    )
    normalized_max_invocations = _as_non_negative_int(
        codex_write_reentry_max_invocations,
        default=1,
    )

    final_path = normalized_prompt190_path or normalized_readiness_path or normalized_routing_path
    final_path_obj = Path(final_path) if final_path else None
    final_path_is_exact = final_path == fixed_prompt_path
    final_path_exists = bool(final_path_obj and final_path_obj.exists())
    final_path_is_file = bool(final_path_obj and final_path_obj.is_file())
    final_path_is_symlink = bool(final_path_obj and final_path_obj.is_symlink())
    final_file_size = 0
    if final_path_obj and final_path_exists and final_path_is_file and not final_path_is_symlink:
        try:
            final_file_size = _as_non_negative_int(final_path_obj.stat().st_size, default=0)
        except OSError:
            final_file_size = 0
    final_file_non_empty = final_file_size > 0
    final_file_too_large = final_file_size > max_prompt_size_bytes
    final_path_safe = bool(
        final_path_is_exact
        and final_path_exists
        and final_path_is_file
        and not final_path_is_symlink
        and final_file_non_empty
        and not final_file_too_large
    )

    manual_review_or_stop = bool(
        prompt190_human_review_required
        or generated_reentry_human_review_required
        or generated_reentry_routing_human_review_required
        or normalized_prompt190_next_action == "manual_review_required"
        or normalized_prompt190_status
        in {
            "post_rollback_fix_reentry_propagation_blocked_manual_review",
            "post_rollback_fix_reentry_propagation_blocked_insufficient_truth",
        }
    )

    generated_prompt_reentry_ready = bool(
        generated_reentry_allowed
        and normalized_readiness_kind == "fix"
        and bool(normalized_readiness_path)
    )
    generated_prompt_reentry_routed = bool(
        generated_reentry_routing_allowed
        and normalized_routing_kind == "fix"
        and bool(normalized_routing_path)
    )
    prompt_selection_refresh_ready = bool(
        prompt_selection_reentry_refresh_allowed
        and normalized_prompt_selection_kind == "fix"
        and bool(normalized_prompt_selection_path)
    )
    codex_invocation_readiness_ready = bool(
        codex_invocation_reentry_selected_prompt_ready
        and normalized_codex_invocation_kind == "fix"
        and bool(normalized_codex_invocation_path)
    )

    allow_rule = bool(
        prompt190_propagation_allowed
        and prompt190_propagation_applied
        and normalized_prompt190_source == "post_rollback_fix_generation"
        and normalized_prompt190_kind == "fix"
        and prompt190_reentry_routing_refresh_allowed
        and prompt190_reentry_invocation_preparation_allowed
        and generated_prompt_reentry_ready
        and generated_prompt_reentry_routed
        and prompt_selection_refresh_ready
        and codex_invocation_readiness_ready
        and codex_write_reentry_prepared
        and codex_write_reentry_selected_prompt_ready
        and codex_reentry_post_rollback_preparation_allowed
        and final_path_safe
        and normalized_max_invocations == 1
        and not prompt190_human_review_required
        and not prompt190_should_invoke_codex
        and not prompt190_should_execute_rollback
        and not prompt190_should_commit
    )

    block_reason = ""
    if not prompt190_propagation_allowed:
        block_reason = "blocked_prompt190_propagation_not_allowed"
    elif not prompt190_propagation_applied:
        block_reason = "blocked_prompt190_propagation_not_applied"
    elif normalized_prompt190_source != "post_rollback_fix_generation":
        block_reason = "blocked_mismatched_reentry_source"
    elif normalized_prompt190_kind != "fix":
        block_reason = "blocked_mismatched_prompt_kind"
    elif not generated_prompt_reentry_ready:
        block_reason = "blocked_reentry_readiness_not_allowed"
    elif not generated_prompt_reentry_routed:
        block_reason = "blocked_reentry_routing_not_allowed"
    elif not prompt_selection_refresh_ready:
        block_reason = "blocked_prompt_selection_refresh_not_ready"
    elif not codex_invocation_readiness_ready:
        block_reason = "blocked_codex_invocation_readiness_not_ready"
    elif not codex_write_reentry_prepared or not codex_write_reentry_selected_prompt_ready:
        block_reason = "blocked_codex_write_reentry_not_prepared"
    elif not codex_reentry_post_rollback_preparation_allowed:
        block_reason = "blocked_post_rollback_reentry_preparation_not_allowed"
    elif not final_path_safe:
        block_reason = "blocked_final_prompt_path_unsafe"
    elif normalized_max_invocations != 1:
        block_reason = "blocked_max_reentry_invocations_not_one"
    elif prompt190_human_review_required:
        block_reason = "blocked_human_review_required"
    elif prompt190_should_invoke_codex:
        block_reason = "blocked_codex_invocation_requested_unexpectedly"
    elif prompt190_should_execute_rollback:
        block_reason = "blocked_rollback_requested_unexpectedly"
    elif prompt190_should_commit:
        block_reason = "blocked_commit_requested_unexpectedly"
    elif not allow_rule:
        block_reason = "blocked_insufficient_post_rollback_reentry_truth"

    status = "post_rollback_fix_reentry_checkpoint_blocked"
    final_ready = False
    final_source = ""
    final_kind = "none"
    final_path_out = ""
    final_max_invocations = 1
    final_invocation_prepared = False
    human_review_required = True
    next_action = "manual_review_required"

    if manual_review_or_stop:
        status = "post_rollback_fix_reentry_checkpoint_blocked_manual_review"
        final_ready = False
        final_invocation_prepared = False
        human_review_required = True
        next_action = (
            normalized_prompt190_next_action
            if normalized_prompt190_next_action in allowed_next_actions
            else "manual_review_required"
        )
    elif allow_rule:
        status = "post_rollback_fix_reentry_checkpoint_ready"
        final_ready = True
        final_source = "post_rollback_fix_generation"
        final_kind = "fix"
        final_path_out = fixed_prompt_path
        final_max_invocations = 1
        final_invocation_prepared = True
        human_review_required = False
        block_reason = ""
        next_action = "prepare_bounded_post_rollback_fix_codex_reentry"
    elif not final_path_safe and final_path:
        status = "post_rollback_fix_reentry_checkpoint_blocked_unsafe_path"
        final_ready = False
        final_invocation_prepared = False
        human_review_required = True
        next_action = "manual_review_required"
    elif block_reason == "blocked_insufficient_post_rollback_reentry_truth":
        status = "post_rollback_fix_reentry_checkpoint_blocked_insufficient_truth"
        final_ready = False
        final_invocation_prepared = False
        human_review_required = True
        next_action = "manual_review_required"
    else:
        status = "post_rollback_fix_reentry_checkpoint_blocked"
        final_ready = False
        final_invocation_prepared = False
        human_review_required = bool(
            prompt190_human_review_required
            or generated_reentry_human_review_required
            or generated_reentry_routing_human_review_required
        )
        next_action = (
            normalized_prompt190_next_action
            if normalized_prompt190_next_action in allowed_next_actions
            else "manual_review_required"
        )

    # Execution boundary/commit safety invariants for Prompt191.
    should_invoke_codex = False
    should_execute_rollback = False
    should_commit = False

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"

    return {
        "project_browser_autonomous_post_rollback_fix_reentry_checkpoint_status": status,
        "project_browser_autonomous_post_rollback_fix_reentry_checkpoint_final_post_rollback_reentry_ready": bool(
            final_ready
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_checkpoint_final_post_rollback_reentry_block_reason": (
            block_reason
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_checkpoint_final_post_rollback_reentry_source": (
            final_source
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_checkpoint_final_reentry_prompt_kind": (
            final_kind
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_checkpoint_final_reentry_prompt_path": (
            final_path_out
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_checkpoint_final_reentry_max_invocations": int(
            final_max_invocations
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_checkpoint_final_reentry_invocation_prepared": bool(
            final_invocation_prepared
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_checkpoint_prompt190_propagation_allowed": bool(
            prompt190_propagation_allowed
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_checkpoint_prompt190_propagation_applied": bool(
            prompt190_propagation_applied
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_checkpoint_generated_prompt_reentry_ready": bool(
            generated_prompt_reentry_ready
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_checkpoint_generated_prompt_reentry_routed": bool(
            generated_prompt_reentry_routed
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_checkpoint_prompt_selection_refresh_ready": bool(
            prompt_selection_refresh_ready
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_checkpoint_codex_invocation_readiness_ready": bool(
            codex_invocation_readiness_ready
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_checkpoint_codex_write_invocation_reentry_prepared": bool(
            codex_write_reentry_prepared
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_checkpoint_post_rollback_reentry_preparation_allowed": bool(
            codex_reentry_post_rollback_preparation_allowed
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_checkpoint_should_invoke_codex": bool(
            should_invoke_codex
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_checkpoint_should_execute_rollback": bool(
            should_execute_rollback
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_checkpoint_should_commit": bool(
            should_commit
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_checkpoint_human_review_required": bool(
            human_review_required
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_checkpoint_next_action": next_action,
        "project_browser_autonomous_post_rollback_fix_reentry_checkpoint_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_checkpoint_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_prompt190_status,
                    normalized_prompt190_block_reason,
                    normalized_prompt190_source,
                    normalized_prompt190_kind,
                    normalized_prompt190_next_action,
                    normalized_readiness_status,
                    normalized_readiness_kind,
                    normalized_routing_status,
                    normalized_routing_kind,
                    normalized_prompt_selection_kind,
                    normalized_codex_invocation_kind,
                    normalized_codex_reentry_prep_source,
                    "final_path_not_exact" if not final_path_is_exact else "",
                    "final_path_missing" if not final_path_exists else "",
                    "final_path_not_file"
                    if final_path_exists and not final_path_is_file
                    else "",
                    "final_path_symlink" if final_path_is_symlink else "",
                    "final_path_empty" if final_path_exists and not final_file_non_empty else "",
                    "final_path_too_large" if final_file_too_large else "",
                    "manual_review_or_stop" if manual_review_or_stop else "",
                ]
            )
        ),
    }

def _build_project_browser_autonomous_post_rollback_fix_reentry_execution_state(
    *,
    repository_path: str,
    checkpoint_status: str,
    final_post_rollback_reentry_ready: bool,
    final_post_rollback_reentry_block_reason: str,
    final_post_rollback_reentry_source: str,
    final_reentry_prompt_kind: str,
    final_reentry_prompt_path: str,
    final_reentry_max_invocations: int,
    final_reentry_invocation_prepared: bool,
    prompt190_propagation_allowed: bool,
    prompt190_propagation_applied: bool,
    generated_prompt_reentry_ready: bool,
    generated_prompt_reentry_routed: bool,
    prompt_selection_refresh_ready: bool,
    codex_invocation_readiness_ready: bool,
    codex_write_invocation_reentry_prepared: bool,
    post_rollback_reentry_preparation_allowed: bool,
    should_invoke_codex: bool,
    should_execute_rollback: bool,
    should_commit: bool,
    human_review_required: bool,
    checkpoint_next_action: str,
    propagation_status: str,
    codex_reentry_invocation_status: str,
    codex_reentry_invocation_attempted: bool,
    codex_reentry_invocation_completed: bool,
    codex_invocation_reentry_selected_prompt_ready: bool,
    codex_invocation_reentry_selected_prompt_kind: str,
    codex_invocation_reentry_selected_prompt_path: str,
    codex_write_reentry_selected_prompt_ready: bool,
    codex_write_reentry_selected_prompt_kind: str,
    codex_write_reentry_selected_prompt_path: str,
    codex_write_reentry_max_invocations: int,
) -> dict[str, Any]:
    allowed_statuses = {
        "post_rollback_fix_reentry_execution_completed_with_changes",
        "post_rollback_fix_reentry_execution_completed_no_changes",
        "post_rollback_fix_reentry_execution_completed_failure",
        "post_rollback_fix_reentry_execution_completed_timeout",
        "post_rollback_fix_reentry_execution_blocked_not_ready",
        "post_rollback_fix_reentry_execution_blocked_manual_review",
        "post_rollback_fix_reentry_execution_blocked_unsafe_prompt_path",
        "post_rollback_fix_reentry_execution_blocked_max_invocations",
        "post_rollback_fix_reentry_execution_blocked_unexpected_prior_action",
        "post_rollback_fix_reentry_execution_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "post_rollback_fix_reentry_result_assimilation",
        "manual_review_required",
        "wait_for_more_truth",
        "insufficient_truth",
    }
    fixed_prompt_path = "/tmp/codex-local-runner-decision/generated_fix_prompt.txt"
    max_prompt_size_bytes = 20000
    runtime_posture = [
        "prompt192_post_rollback_fix_reentry_execution",
        "single_bounded_invocation",
        "reuses_prompt180_prompt167_workspace_write_path",
        "no_retry",
        "no_loop",
        "no_rollback_execution",
        "no_commit",
    ]

    normalized_repository_path = _normalize_text(repository_path, default="")
    normalized_checkpoint_status = _normalize_text(
        checkpoint_status,
        default="insufficient_truth",
    )
    normalized_checkpoint_block_reason = _normalize_text(
        final_post_rollback_reentry_block_reason,
        default="",
    )
    normalized_checkpoint_source = _normalize_text(
        final_post_rollback_reentry_source,
        default="",
    )
    normalized_prompt_kind = _normalize_text(final_reentry_prompt_kind, default="none")
    normalized_prompt_path = _normalize_text(final_reentry_prompt_path, default="")
    normalized_checkpoint_next_action = _normalize_text(checkpoint_next_action, default="")
    normalized_propagation_status = _normalize_text(propagation_status, default="insufficient_truth")
    normalized_prior_reentry_status = _normalize_text(
        codex_reentry_invocation_status,
        default="insufficient_truth",
    )
    normalized_codex_invocation_reentry_kind = _normalize_text(
        codex_invocation_reentry_selected_prompt_kind,
        default="none",
    )
    normalized_codex_invocation_reentry_path = _normalize_text(
        codex_invocation_reentry_selected_prompt_path,
        default="",
    )
    normalized_codex_write_reentry_kind = _normalize_text(
        codex_write_reentry_selected_prompt_kind,
        default="none",
    )
    normalized_codex_write_reentry_path = _normalize_text(
        codex_write_reentry_selected_prompt_path,
        default="",
    )
    normalized_max_invocations = _as_non_negative_int(final_reentry_max_invocations, default=0)
    normalized_write_reentry_max_invocations = _as_non_negative_int(
        codex_write_reentry_max_invocations,
        default=0,
    )

    prompt_path_obj = Path(normalized_prompt_path) if normalized_prompt_path else None
    prompt_path_is_exact = normalized_prompt_path == fixed_prompt_path
    prompt_path_exists = bool(prompt_path_obj and prompt_path_obj.exists())
    prompt_path_is_file = bool(prompt_path_obj and prompt_path_obj.is_file())
    prompt_path_is_symlink = bool(prompt_path_obj and prompt_path_obj.is_symlink())
    prompt_size_bytes = 0
    if prompt_path_obj and prompt_path_exists and prompt_path_is_file and not prompt_path_is_symlink:
        try:
            prompt_size_bytes = _as_non_negative_int(prompt_path_obj.stat().st_size, default=0)
        except OSError:
            prompt_size_bytes = 0
    prompt_file_non_empty = prompt_size_bytes > 0
    prompt_file_too_large = prompt_size_bytes > max_prompt_size_bytes
    prompt_path_safe = bool(
        prompt_path_is_exact
        and prompt_path_exists
        and prompt_path_is_file
        and not prompt_path_is_symlink
        and prompt_file_non_empty
        and not prompt_file_too_large
    )

    block_reason = ""
    if not final_post_rollback_reentry_ready:
        block_reason = "blocked_checkpoint_not_ready"
    elif normalized_checkpoint_source != "post_rollback_fix_generation":
        block_reason = "blocked_mismatched_source"
    elif normalized_prompt_kind != "fix":
        block_reason = "blocked_mismatched_prompt_kind"
    elif not prompt_path_safe:
        block_reason = "blocked_unsafe_prompt_path"
    elif normalized_max_invocations != 1 or normalized_write_reentry_max_invocations != 1:
        block_reason = "blocked_max_invocations_not_one"
    elif not final_reentry_invocation_prepared:
        block_reason = "blocked_invocation_not_prepared"
    elif not (prompt190_propagation_allowed and prompt190_propagation_applied):
        block_reason = "blocked_prompt190_propagation_not_ready"
    elif not generated_prompt_reentry_ready:
        block_reason = "blocked_generated_prompt_reentry_not_ready"
    elif not generated_prompt_reentry_routed:
        block_reason = "blocked_generated_prompt_reentry_not_routed"
    elif not prompt_selection_refresh_ready:
        block_reason = "blocked_prompt_selection_not_ready"
    elif not codex_invocation_readiness_ready:
        block_reason = "blocked_codex_invocation_readiness_not_ready"
    elif not codex_write_invocation_reentry_prepared:
        block_reason = "blocked_codex_write_reentry_not_prepared"
    elif not post_rollback_reentry_preparation_allowed:
        block_reason = "blocked_post_rollback_preparation_not_allowed"
    elif human_review_required:
        block_reason = "blocked_human_review_required"
    elif should_invoke_codex:
        block_reason = "blocked_codex_invocation_requested_unexpectedly"
    elif should_execute_rollback:
        block_reason = "blocked_rollback_requested_unexpectedly"
    elif should_commit:
        block_reason = "blocked_commit_requested_unexpectedly"
    elif not normalized_repository_path:
        block_reason = "blocked_insufficient_post_rollback_fix_reentry_execution_truth"
    elif (
        normalized_codex_invocation_reentry_kind != "fix"
        or normalized_codex_invocation_reentry_path != fixed_prompt_path
        or not codex_invocation_reentry_selected_prompt_ready
    ):
        block_reason = "blocked_codex_invocation_readiness_not_ready"
    elif (
        normalized_codex_write_reentry_kind != "fix"
        or normalized_codex_write_reentry_path != fixed_prompt_path
        or not codex_write_reentry_selected_prompt_ready
    ):
        block_reason = "blocked_codex_write_reentry_not_prepared"
    elif not (
        normalized_checkpoint_status == "post_rollback_fix_reentry_checkpoint_ready"
        and normalized_propagation_status == "post_rollback_fix_reentry_propagation_allowed"
    ):
        block_reason = "blocked_insufficient_post_rollback_fix_reentry_execution_truth"
    elif not (
        normalized_prior_reentry_status in {"insufficient_truth"}
        or (
            not bool(codex_reentry_invocation_attempted)
            and not bool(codex_reentry_invocation_completed)
        )
    ):
        block_reason = "blocked_insufficient_post_rollback_fix_reentry_execution_truth"

    execution_allowed = not bool(block_reason)
    status = "post_rollback_fix_reentry_execution_blocked_insufficient_truth"
    execution_source = "prompt191_post_rollback_fix_reentry_checkpoint"
    execution_attempted = False
    execution_completed = False
    execution_failed = False
    command: list[str] = []
    stdout_path = "/tmp/codex-local-runner-decision/codex_write_invocation_stdout.txt"
    stderr_path = "/tmp/codex-local-runner-decision/codex_write_invocation_stderr.txt"
    result_path = "/tmp/codex-local-runner-decision/codex_write_invocation_result.json"
    git_diff_name_only_path = "/tmp/codex-local-runner-decision/codex_write_git_diff_name_only.txt"
    git_diff_numstat_path = "/tmp/codex-local-runner-decision/codex_write_git_diff_numstat.txt"
    changed_files_after: list[str] = []
    changed_files_count_after = 0
    result_class = "blocked"
    exit_code = -1
    timed_out = False
    invocations_attempted = 0
    invocations_completed = 0
    local_human_review_required = bool(human_review_required)
    next_action = "manual_review_required"
    assimilation_ready = False
    assimilation_source = ""
    assimilation_next_stage = "manual_review_or_blocked_post_rollback_reentry"
    missing_inputs: list[str] = []

    if execution_allowed:
        write_state = _build_project_browser_autonomous_codex_write_invocation_state(
            repository_path=normalized_repository_path,
            codex_invocation_readiness_status="ready_for_write_codex_invocation",
            codex_invocation_readiness_allowed=True,
            selected_prompt_kind="fix",
            selected_prompt_path=fixed_prompt_path,
            selected_prompt_source="project_browser_autonomous_post_rollback_fix_reentry_checkpoint",
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
            prior_write_invocation_attempted=False,
            prior_write_invocation_completed=False,
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
        execution_attempted = bool(
            write_state.get(
                "project_browser_autonomous_codex_write_invocation_execution_invocation_attempted",
                False,
            )
        )
        execution_completed = bool(
            write_state.get(
                "project_browser_autonomous_codex_write_invocation_execution_invocation_completed",
                False,
            )
        )
        timed_out = bool(
            write_state.get("project_browser_autonomous_codex_write_invocation_result_timeout", False)
        )
        exit_code = int(
            _as_int(
                write_state.get("project_browser_autonomous_codex_write_invocation_result_exit_code"),
                default=-1,
            )
        )
        invocations_attempted = 1 if execution_attempted else 0
        invocations_completed = 1 if (execution_completed and not timed_out) else 0
        write_result_status = _normalize_text(
            write_state.get("project_browser_autonomous_codex_write_invocation_result_status"),
            default="insufficient_truth",
        )
        if write_result_status == "completed_with_changes":
            status = "post_rollback_fix_reentry_execution_completed_with_changes"
            result_class = "completed_with_changes"
            execution_failed = False
            local_human_review_required = False
            next_action = "post_rollback_fix_reentry_result_assimilation"
            assimilation_ready = True
        elif write_result_status == "completed_no_changes":
            status = "post_rollback_fix_reentry_execution_completed_no_changes"
            result_class = "completed_no_changes"
            execution_failed = False
            local_human_review_required = False
            next_action = "post_rollback_fix_reentry_result_assimilation"
            assimilation_ready = True
        elif write_result_status == "completed_failure":
            status = "post_rollback_fix_reentry_execution_completed_failure"
            result_class = "completed_failure"
            execution_failed = True
            local_human_review_required = False
            next_action = "post_rollback_fix_reentry_result_assimilation"
            assimilation_ready = True
        elif write_result_status == "completed_timeout":
            status = "post_rollback_fix_reentry_execution_completed_timeout"
            result_class = "completed_timeout"
            execution_failed = True
            local_human_review_required = True
            next_action = "post_rollback_fix_reentry_result_assimilation"
            assimilation_ready = True
        else:
            status = "post_rollback_fix_reentry_execution_blocked_insufficient_truth"
            result_class = "blocked"
            execution_failed = False
            local_human_review_required = True
            next_action = "manual_review_required"
            block_reason = _normalize_text(
                write_state.get(
                    "project_browser_autonomous_codex_write_invocation_execution_block_reason"
                ),
                default="blocked_insufficient_post_rollback_fix_reentry_execution_truth",
            )
            assimilation_ready = False

        if assimilation_ready:
            assimilation_source = "prompt192_post_rollback_fix_reentry_execution"
            assimilation_next_stage = "post_rollback_fix_reentry_result_assimilation"
        else:
            assimilation_source = ""
            assimilation_next_stage = "manual_review_or_blocked_post_rollback_reentry"
    else:
        if block_reason == "blocked_human_review_required":
            status = "post_rollback_fix_reentry_execution_blocked_manual_review"
            local_human_review_required = True
            next_action = "manual_review_required"
        elif block_reason == "blocked_unsafe_prompt_path":
            status = "post_rollback_fix_reentry_execution_blocked_unsafe_prompt_path"
            local_human_review_required = True
            next_action = "manual_review_required"
        elif block_reason == "blocked_max_invocations_not_one":
            status = "post_rollback_fix_reentry_execution_blocked_max_invocations"
            local_human_review_required = True
            next_action = "manual_review_required"
        elif block_reason in {
            "blocked_codex_invocation_requested_unexpectedly",
            "blocked_rollback_requested_unexpectedly",
            "blocked_commit_requested_unexpectedly",
        }:
            status = "post_rollback_fix_reentry_execution_blocked_unexpected_prior_action"
            local_human_review_required = True
            next_action = "manual_review_required"
        elif block_reason in {
            "blocked_checkpoint_not_ready",
            "blocked_mismatched_source",
            "blocked_mismatched_prompt_kind",
            "blocked_invocation_not_prepared",
            "blocked_prompt190_propagation_not_ready",
            "blocked_generated_prompt_reentry_not_ready",
            "blocked_generated_prompt_reentry_not_routed",
            "blocked_prompt_selection_not_ready",
            "blocked_codex_invocation_readiness_not_ready",
            "blocked_codex_write_reentry_not_prepared",
            "blocked_post_rollback_preparation_not_allowed",
        }:
            status = "post_rollback_fix_reentry_execution_blocked_not_ready"
            local_human_review_required = True
            next_action = (
                "manual_review_required"
                if normalized_checkpoint_next_action != "no_rollback_required"
                else "wait_for_more_truth"
            )
        else:
            status = "post_rollback_fix_reentry_execution_blocked_insufficient_truth"
            local_human_review_required = True
            next_action = "manual_review_required"
        if not normalized_repository_path:
            missing_inputs.append("repository_path")

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"

    return {
        "project_browser_autonomous_post_rollback_fix_reentry_execution_status": status,
        "project_browser_autonomous_post_rollback_fix_reentry_execution_execution_allowed": bool(
            execution_allowed
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_execution_attempted": bool(
            execution_attempted
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_execution_completed": bool(
            execution_completed
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_execution_failed": bool(
            execution_failed
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_execution_block_reason": (
            block_reason
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_execution_source": (
            execution_source
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_prompt_kind": (
            "fix" if normalized_prompt_kind == "fix" else "none"
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_prompt_path": (
            normalized_prompt_path if normalized_prompt_kind == "fix" else ""
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_max_invocations": int(
            normalized_max_invocations
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_invocations_attempted": int(
            invocations_attempted
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_invocations_completed": int(
            invocations_completed
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_reused_invocation_path": True,
        "project_browser_autonomous_post_rollback_fix_reentry_execution_execution_sandbox": (
            "workspace-write"
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_command": command,
        "project_browser_autonomous_post_rollback_fix_reentry_execution_stdout_path": (
            stdout_path
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_stderr_path": (
            stderr_path
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_result_path": (
            result_path
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_git_diff_name_only_path": (
            git_diff_name_only_path
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_git_diff_numstat_path": (
            git_diff_numstat_path
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_changed_files_after": (
            changed_files_after
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_changed_files_count_after": int(
            changed_files_count_after
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_result_class": (
            result_class
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_exit_code": int(
            exit_code
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_timed_out": bool(
            timed_out
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_post_rollback_fix_reentry_result_ready_for_assimilation": bool(
            assimilation_ready
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_post_rollback_fix_reentry_result_assimilation_source": (
            assimilation_source
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_post_rollback_fix_reentry_result_next_stage": (
            assimilation_next_stage
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_human_review_required": bool(
            local_human_review_required
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_next_action": (
            next_action
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_execution_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_checkpoint_status,
                    normalized_checkpoint_block_reason,
                    normalized_checkpoint_source,
                    normalized_prompt_kind,
                    normalized_prompt_path,
                    normalized_propagation_status,
                    normalized_prior_reentry_status,
                    "checkpoint_not_ready" if not final_post_rollback_reentry_ready else "",
                    "prompt_path_not_exact" if not prompt_path_is_exact else "",
                    "prompt_path_missing" if not prompt_path_exists else "",
                    "prompt_path_not_file"
                    if prompt_path_exists and not prompt_path_is_file
                    else "",
                    "prompt_path_symlink" if prompt_path_is_symlink else "",
                    "prompt_path_empty" if prompt_path_exists and not prompt_file_non_empty else "",
                    "prompt_path_too_large" if prompt_file_too_large else "",
                    *missing_inputs,
                ]
            )
        ),
    }

def _build_project_browser_autonomous_review_fix_decision_state(
    *,
    codex_result_ingestion_state: Mapping[str, Any],
) -> dict[str, Any]:
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
    result_summary = _normalize_text(
        codex_result_ingestion_state.get(
            "project_browser_autonomous_codex_result_ingestion_result_summary"
        ),
        default="",
    )

    status = "review_fix_decision_waiting_for_codex_result"
    review_decision = "waiting"
    fix_prompt = ""
    commit_candidate = False
    next_pr_candidate = False
    next_action = "await_codex_result"

    if result_detected and validation_passed:
        status = "review_fix_decision_approved"
        review_decision = "approve"
        commit_candidate = True
        next_pr_candidate = True
        next_action = "prepare_commit_or_next_pr_metadata"
    elif result_detected and not validation_passed:
        status = "review_fix_decision_needs_fix"
        review_decision = "fix"
        fix_prompt = (
            "Revise the implementation to address reported issues. "
            f"Focus on: {result_summary}"
        )
        next_action = "revise_pr_prompt_or_retry_codex"

    return {
        "project_browser_autonomous_review_fix_decision_status": status,
        "project_browser_autonomous_review_fix_decision_source": (
            "prompt254_review_fix_decision"
        ),
        "project_browser_autonomous_review_fix_decision_result_detected": bool(
            result_detected
        ),
        "project_browser_autonomous_review_fix_decision_validation_passed": bool(
            validation_passed if result_detected else False
        ),
        "project_browser_autonomous_review_fix_decision_review_decision": review_decision,
        "project_browser_autonomous_review_fix_decision_fix_prompt": (
            fix_prompt if review_decision == "fix" else ""
        ),
        "project_browser_autonomous_review_fix_decision_commit_candidate": bool(
            commit_candidate
        ),
        "project_browser_autonomous_review_fix_decision_next_pr_candidate": bool(
            next_pr_candidate
        ),
        "project_browser_autonomous_review_fix_decision_next_action": next_action,
    }

def _build_project_browser_autonomous_fix_retry_route_state(
    *,
    review_decision: str,
    fix_prompt: str,
) -> dict[str, Any]:
    normalized_review_decision = _normalize_text(review_decision, default="waiting")
    normalized_fix_prompt = _normalize_text(fix_prompt, default="")

    status = "fix_retry_route_waiting_for_review_decision"
    fix_required = False
    next_action = "await_codex_result"
    effective_fix_prompt = ""

    if normalized_review_decision == "fix":
        status = "fix_retry_route_ready"
        fix_required = True
        effective_fix_prompt = (
            normalized_fix_prompt
            if normalized_fix_prompt
            else "Revise the implementation based on the previous Codex result summary."
        )
        next_action = "revise_pr_prompt_or_retry_codex"
    elif normalized_review_decision == "approve":
        status = "fix_retry_route_not_required"
        next_action = "prepare_commit_or_next_pr_metadata"

    return {
        "project_browser_autonomous_fix_retry_route_status": status,
        "project_browser_autonomous_fix_retry_route_source": (
            "prompt255_fix_retry_route"
        ),
        "project_browser_autonomous_fix_retry_route_review_decision": (
            normalized_review_decision
        ),
        "project_browser_autonomous_fix_retry_route_fix_required": bool(fix_required),
        "project_browser_autonomous_fix_retry_route_fix_prompt": effective_fix_prompt,
        "project_browser_autonomous_fix_retry_route_retry_allowed": False,
        "project_browser_autonomous_fix_retry_route_next_action": next_action,
    }

def _build_project_browser_autonomous_safe_revert_state(
    *,
    chatgpt_diff_review_decision_state: Mapping[str, Any] | None,
    codex_capture_gate_state: Mapping[str, Any] | None,
    local_loop_state: Mapping[str, Any] | None,
    approved_restart_payload: Mapping[str, Any] | None,
    prior_approved_restart_execution_payload: Mapping[str, Any] | None,
    execution_repo_path: str,
) -> dict[str, Any]:
    review_state = (
        dict(chatgpt_diff_review_decision_state)
        if isinstance(chatgpt_diff_review_decision_state, Mapping)
        else {}
    )
    capture_state = dict(codex_capture_gate_state) if isinstance(codex_capture_gate_state, Mapping) else {}
    local_loop = dict(local_loop_state) if isinstance(local_loop_state, Mapping) else {}
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

    def _is_safe_changed_path(path_text: str) -> tuple[bool, str]:
        path = _normalize_text(path_text, default="")
        if not path:
            return (False, "empty_path")
        if Path(path).is_absolute() or path.startswith("/") or path.startswith("\\"):
            return (False, f"absolute_path:{path}")
        normalized = path.replace("\\", "/")
        if normalized.startswith("./"):
            normalized = normalized[2:]
        if not normalized:
            return (False, "malformed_path")
        if ".." in normalized.split("/"):
            return (False, f"parent_traversal:{path}")
        if normalized == ".git" or normalized.startswith(".git/"):
            return (False, f"git_internal:{path}")
        if normalized.startswith("../") or "/../" in normalized:
            return (False, f"outside_repo:{path}")
        if " -> " in normalized:
            return (False, f"ambiguous_path:{path}")
        return (True, normalized)

    def _parse_git_status_short(output: str) -> tuple[dict[str, str], list[str]]:
        parsed: dict[str, str] = {}
        ambiguous: list[str] = []
        for raw_line in output.splitlines():
            line = raw_line.rstrip("\n")
            if not line.strip():
                continue
            if len(line) < 4 or line[2] != " ":
                ambiguous.append(f"malformed_status_line:{line}")
                continue
            code = line[:2]
            x, y = code[0], code[1]
            path_text = line[3:].strip()
            if not path_text or path_text.startswith('"') or " -> " in path_text:
                ambiguous.append(f"ambiguous_path:{line}")
                continue
            if x in {"R", "C", "U"} or y in {"R", "C", "U"}:
                ambiguous.append(f"unsupported_status:{line}")
                continue
            if x not in {" ", "M", "A", "D", "?"} or y not in {" ", "M", "A", "D", "?"}:
                ambiguous.append(f"unsupported_status:{line}")
                continue
            path = path_text.replace("\\", "/")
            if path in parsed:
                ambiguous.append(f"duplicate_status_entry:{path}")
                continue
            parsed[path] = code
        return parsed, ambiguous

    safe_revert_enabled = _read_flag(
        "project_browser_autonomous_safe_revert_enabled",
        default=False,
    )
    safe_revert_execute_enabled = _read_flag(
        "project_browser_autonomous_safe_revert_execute_enabled",
        default=False,
    )

    review_decision = _normalize_text(
        review_state.get("project_browser_autonomous_chatgpt_diff_review_decision"),
        default="",
    )
    review_revert_reason = _normalize_text(
        review_state.get("project_browser_autonomous_chatgpt_diff_review_revert_reason"),
        default="",
    )
    review_revert_plan = _normalize_text(
        review_state.get("project_browser_autonomous_chatgpt_diff_review_revert_plan"),
        default="",
    )
    local_loop_status = _normalize_text(
        local_loop.get("project_browser_autonomous_local_loop_status"),
        default="",
    )
    local_loop_next_action = _normalize_text(
        local_loop.get("project_browser_autonomous_local_loop_next_action"),
        default="",
    )
    local_loop_revert_plan = _normalize_text(
        local_loop.get("project_browser_autonomous_local_loop_revert_plan"),
        default="",
    )
    changed_files = _normalize_string_list(
        capture_state.get("project_browser_autonomous_codex_capture_gate_changed_files")
    )

    status = "safe_revert_not_requested"
    next_action = "enable_safe_revert"
    reverted = False
    pre_git_status_short = ""
    post_git_status_short = ""
    blocked_reason = "safe_revert_disabled"

    revert_reason = review_revert_reason
    revert_plan = review_revert_plan if review_revert_plan else local_loop_revert_plan

    if not safe_revert_enabled:
        return {
            "project_browser_autonomous_safe_revert_status": status,
            "project_browser_autonomous_safe_revert_next_action": next_action,
            "project_browser_autonomous_safe_revert_enabled": bool(safe_revert_enabled),
            "project_browser_autonomous_safe_revert_execute_enabled": bool(
                safe_revert_execute_enabled
            ),
            "project_browser_autonomous_safe_revert_reverted": bool(reverted),
            "project_browser_autonomous_safe_revert_changed_files": _normalize_string_list(
                changed_files
            ),
            "project_browser_autonomous_safe_revert_revert_reason": revert_reason,
            "project_browser_autonomous_safe_revert_revert_plan": revert_plan,
            "project_browser_autonomous_safe_revert_pre_git_status_short": pre_git_status_short,
            "project_browser_autonomous_safe_revert_post_git_status_short": post_git_status_short,
            "project_browser_autonomous_safe_revert_blocked_reason": blocked_reason,
        }

    review_revert_flow = bool(
        review_decision == "revert" and (review_revert_reason or review_revert_plan)
    )
    local_loop_revert_flow = bool(
        local_loop_next_action == "prepare_safe_revert"
        and local_loop_status == "local_loop_ready_prepare_safe_revert"
    )
    if not review_revert_flow and not local_loop_revert_flow:
        status = "safe_revert_blocked_missing_revert_decision"
        next_action = "manual_review_required"
        blocked_reason = "missing_revert_flow_signal"
        return {
            "project_browser_autonomous_safe_revert_status": status,
            "project_browser_autonomous_safe_revert_next_action": next_action,
            "project_browser_autonomous_safe_revert_enabled": bool(safe_revert_enabled),
            "project_browser_autonomous_safe_revert_execute_enabled": bool(
                safe_revert_execute_enabled
            ),
            "project_browser_autonomous_safe_revert_reverted": bool(reverted),
            "project_browser_autonomous_safe_revert_changed_files": _normalize_string_list(
                changed_files
            ),
            "project_browser_autonomous_safe_revert_revert_reason": revert_reason,
            "project_browser_autonomous_safe_revert_revert_plan": revert_plan,
            "project_browser_autonomous_safe_revert_pre_git_status_short": pre_git_status_short,
            "project_browser_autonomous_safe_revert_post_git_status_short": post_git_status_short,
            "project_browser_autonomous_safe_revert_blocked_reason": blocked_reason,
        }

    if not changed_files:
        status = "safe_revert_blocked_missing_changed_files"
        next_action = "manual_review_required"
        blocked_reason = "changed_files_missing"
        return {
            "project_browser_autonomous_safe_revert_status": status,
            "project_browser_autonomous_safe_revert_next_action": next_action,
            "project_browser_autonomous_safe_revert_enabled": bool(safe_revert_enabled),
            "project_browser_autonomous_safe_revert_execute_enabled": bool(
                safe_revert_execute_enabled
            ),
            "project_browser_autonomous_safe_revert_reverted": bool(reverted),
            "project_browser_autonomous_safe_revert_changed_files": _normalize_string_list(
                changed_files
            ),
            "project_browser_autonomous_safe_revert_revert_reason": revert_reason,
            "project_browser_autonomous_safe_revert_revert_plan": revert_plan,
            "project_browser_autonomous_safe_revert_pre_git_status_short": pre_git_status_short,
            "project_browser_autonomous_safe_revert_post_git_status_short": post_git_status_short,
            "project_browser_autonomous_safe_revert_blocked_reason": blocked_reason,
        }

    safe_changed_files: list[str] = []
    for path in changed_files:
        safe, normalized_or_reason = _is_safe_changed_path(path)
        if not safe:
            status = "safe_revert_blocked_unsafe_paths"
            next_action = "manual_review_required"
            blocked_reason = normalized_or_reason
            return {
                "project_browser_autonomous_safe_revert_status": status,
                "project_browser_autonomous_safe_revert_next_action": next_action,
                "project_browser_autonomous_safe_revert_enabled": bool(safe_revert_enabled),
                "project_browser_autonomous_safe_revert_execute_enabled": bool(
                    safe_revert_execute_enabled
                ),
                "project_browser_autonomous_safe_revert_reverted": bool(reverted),
                "project_browser_autonomous_safe_revert_changed_files": _normalize_string_list(
                    changed_files
                ),
                "project_browser_autonomous_safe_revert_revert_reason": revert_reason,
                "project_browser_autonomous_safe_revert_revert_plan": revert_plan,
                "project_browser_autonomous_safe_revert_pre_git_status_short": pre_git_status_short,
                "project_browser_autonomous_safe_revert_post_git_status_short": post_git_status_short,
                "project_browser_autonomous_safe_revert_blocked_reason": blocked_reason,
            }
        safe_changed_files.append(normalized_or_reason)
    safe_changed_files = _normalize_string_list(safe_changed_files)

    max_changed_files = 25
    large_change_approved = False
    for key in (
        "project_browser_autonomous_large_change_approved",
        "project_browser_autonomous_commit_tag_large_change_approved",
    ):
        if key in approved_restart or key in prior_payload:
            large_change_approved = _read_flag(key, default=False)
            break
    if len(safe_changed_files) > max_changed_files and not large_change_approved:
        status = "safe_revert_blocked_large_change"
        next_action = "manual_review_required"
        blocked_reason = "changed_file_count_exceeds_limit"
        return {
            "project_browser_autonomous_safe_revert_status": status,
            "project_browser_autonomous_safe_revert_next_action": next_action,
            "project_browser_autonomous_safe_revert_enabled": bool(safe_revert_enabled),
            "project_browser_autonomous_safe_revert_execute_enabled": bool(
                safe_revert_execute_enabled
            ),
            "project_browser_autonomous_safe_revert_reverted": bool(reverted),
            "project_browser_autonomous_safe_revert_changed_files": _normalize_string_list(
                safe_changed_files
            ),
            "project_browser_autonomous_safe_revert_revert_reason": revert_reason,
            "project_browser_autonomous_safe_revert_revert_plan": revert_plan,
            "project_browser_autonomous_safe_revert_pre_git_status_short": pre_git_status_short,
            "project_browser_autonomous_safe_revert_post_git_status_short": post_git_status_short,
            "project_browser_autonomous_safe_revert_blocked_reason": blocked_reason,
        }

    repo_path = _normalize_text(execution_repo_path, default="")
    repo_obj = Path(repo_path) if repo_path else Path.cwd()
    if not repo_obj.exists() or not repo_obj.is_dir():
        status = "safe_revert_blocked_unsafe_paths"
        next_action = "manual_review_required"
        blocked_reason = "execution_repo_unavailable"
        return {
            "project_browser_autonomous_safe_revert_status": status,
            "project_browser_autonomous_safe_revert_next_action": next_action,
            "project_browser_autonomous_safe_revert_enabled": bool(safe_revert_enabled),
            "project_browser_autonomous_safe_revert_execute_enabled": bool(
                safe_revert_execute_enabled
            ),
            "project_browser_autonomous_safe_revert_reverted": bool(reverted),
            "project_browser_autonomous_safe_revert_changed_files": _normalize_string_list(
                safe_changed_files
            ),
            "project_browser_autonomous_safe_revert_revert_reason": revert_reason,
            "project_browser_autonomous_safe_revert_revert_plan": revert_plan,
            "project_browser_autonomous_safe_revert_pre_git_status_short": pre_git_status_short,
            "project_browser_autonomous_safe_revert_post_git_status_short": post_git_status_short,
            "project_browser_autonomous_safe_revert_blocked_reason": blocked_reason,
        }

    try:
        pre_status_cp = _run_git(str(repo_obj), ["status", "--short"], timeout_seconds=10.0)
    except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
        status = "safe_revert_blocked_git_failed"
        next_action = "manual_review_required"
        blocked_reason = "git_status_failed"
        return {
            "project_browser_autonomous_safe_revert_status": status,
            "project_browser_autonomous_safe_revert_next_action": next_action,
            "project_browser_autonomous_safe_revert_enabled": bool(safe_revert_enabled),
            "project_browser_autonomous_safe_revert_execute_enabled": bool(
                safe_revert_execute_enabled
            ),
            "project_browser_autonomous_safe_revert_reverted": bool(reverted),
            "project_browser_autonomous_safe_revert_changed_files": _normalize_string_list(
                safe_changed_files
            ),
            "project_browser_autonomous_safe_revert_revert_reason": revert_reason,
            "project_browser_autonomous_safe_revert_revert_plan": revert_plan,
            "project_browser_autonomous_safe_revert_pre_git_status_short": pre_git_status_short,
            "project_browser_autonomous_safe_revert_post_git_status_short": post_git_status_short,
            "project_browser_autonomous_safe_revert_blocked_reason": blocked_reason,
        }
    pre_git_status_short = _normalize_text(pre_status_cp.stdout, default="")
    if pre_status_cp.returncode != 0:
        status = "safe_revert_blocked_git_failed"
        next_action = "manual_review_required"
        blocked_reason = "git_status_nonzero"
        return {
            "project_browser_autonomous_safe_revert_status": status,
            "project_browser_autonomous_safe_revert_next_action": next_action,
            "project_browser_autonomous_safe_revert_enabled": bool(safe_revert_enabled),
            "project_browser_autonomous_safe_revert_execute_enabled": bool(
                safe_revert_execute_enabled
            ),
            "project_browser_autonomous_safe_revert_reverted": bool(reverted),
            "project_browser_autonomous_safe_revert_changed_files": _normalize_string_list(
                safe_changed_files
            ),
            "project_browser_autonomous_safe_revert_revert_reason": revert_reason,
            "project_browser_autonomous_safe_revert_revert_plan": revert_plan,
            "project_browser_autonomous_safe_revert_pre_git_status_short": pre_git_status_short,
            "project_browser_autonomous_safe_revert_post_git_status_short": post_git_status_short,
            "project_browser_autonomous_safe_revert_blocked_reason": blocked_reason,
        }

    parsed_status, ambiguous_status = _parse_git_status_short(pre_git_status_short)
    if ambiguous_status:
        status = "safe_revert_blocked_ambiguous_status"
        next_action = "manual_review_required"
        blocked_reason = ambiguous_status[0]
        return {
            "project_browser_autonomous_safe_revert_status": status,
            "project_browser_autonomous_safe_revert_next_action": next_action,
            "project_browser_autonomous_safe_revert_enabled": bool(safe_revert_enabled),
            "project_browser_autonomous_safe_revert_execute_enabled": bool(
                safe_revert_execute_enabled
            ),
            "project_browser_autonomous_safe_revert_reverted": bool(reverted),
            "project_browser_autonomous_safe_revert_changed_files": _normalize_string_list(
                safe_changed_files
            ),
            "project_browser_autonomous_safe_revert_revert_reason": revert_reason,
            "project_browser_autonomous_safe_revert_revert_plan": revert_plan,
            "project_browser_autonomous_safe_revert_pre_git_status_short": pre_git_status_short,
            "project_browser_autonomous_safe_revert_post_git_status_short": post_git_status_short,
            "project_browser_autonomous_safe_revert_blocked_reason": blocked_reason,
        }

    status_paths = set(parsed_status.keys())
    changed_files_set = set(safe_changed_files)
    if status_paths != changed_files_set:
        status = "safe_revert_blocked_unexpected_changes"
        next_action = "manual_review_required"
        blocked_reason = "git_status_paths_mismatch"
        return {
            "project_browser_autonomous_safe_revert_status": status,
            "project_browser_autonomous_safe_revert_next_action": next_action,
            "project_browser_autonomous_safe_revert_enabled": bool(safe_revert_enabled),
            "project_browser_autonomous_safe_revert_execute_enabled": bool(
                safe_revert_execute_enabled
            ),
            "project_browser_autonomous_safe_revert_reverted": bool(reverted),
            "project_browser_autonomous_safe_revert_changed_files": _normalize_string_list(
                safe_changed_files
            ),
            "project_browser_autonomous_safe_revert_revert_reason": revert_reason,
            "project_browser_autonomous_safe_revert_revert_plan": revert_plan,
            "project_browser_autonomous_safe_revert_pre_git_status_short": pre_git_status_short,
            "project_browser_autonomous_safe_revert_post_git_status_short": post_git_status_short,
            "project_browser_autonomous_safe_revert_blocked_reason": blocked_reason,
        }

    untracked_changed_files: list[str] = []
    for path in safe_changed_files:
        code = parsed_status.get(path, "")
        if code == "??":
            untracked_changed_files.append(path)
    if untracked_changed_files:
        status = "safe_revert_blocked_untracked_files"
        next_action = "manual_review_required"
        blocked_reason = f"untracked_files_present:{untracked_changed_files[0]}"
        return {
            "project_browser_autonomous_safe_revert_status": status,
            "project_browser_autonomous_safe_revert_next_action": next_action,
            "project_browser_autonomous_safe_revert_enabled": bool(safe_revert_enabled),
            "project_browser_autonomous_safe_revert_execute_enabled": bool(
                safe_revert_execute_enabled
            ),
            "project_browser_autonomous_safe_revert_reverted": bool(reverted),
            "project_browser_autonomous_safe_revert_changed_files": _normalize_string_list(
                safe_changed_files
            ),
            "project_browser_autonomous_safe_revert_revert_reason": revert_reason,
            "project_browser_autonomous_safe_revert_revert_plan": revert_plan,
            "project_browser_autonomous_safe_revert_pre_git_status_short": pre_git_status_short,
            "project_browser_autonomous_safe_revert_post_git_status_short": post_git_status_short,
            "project_browser_autonomous_safe_revert_blocked_reason": blocked_reason,
        }

    if not safe_revert_execute_enabled:
        status = "safe_revert_decision_only"
        next_action = "set_execute_enabled_for_safe_revert"
        blocked_reason = "execution_not_enabled"
        return {
            "project_browser_autonomous_safe_revert_status": status,
            "project_browser_autonomous_safe_revert_next_action": next_action,
            "project_browser_autonomous_safe_revert_enabled": bool(safe_revert_enabled),
            "project_browser_autonomous_safe_revert_execute_enabled": bool(
                safe_revert_execute_enabled
            ),
            "project_browser_autonomous_safe_revert_reverted": bool(reverted),
            "project_browser_autonomous_safe_revert_changed_files": _normalize_string_list(
                safe_changed_files
            ),
            "project_browser_autonomous_safe_revert_revert_reason": revert_reason,
            "project_browser_autonomous_safe_revert_revert_plan": revert_plan,
            "project_browser_autonomous_safe_revert_pre_git_status_short": pre_git_status_short,
            "project_browser_autonomous_safe_revert_post_git_status_short": post_git_status_short,
            "project_browser_autonomous_safe_revert_blocked_reason": blocked_reason,
        }

    try:
        restore_staged_cp = _run_git(
            str(repo_obj),
            ["restore", "--staged", "--", *safe_changed_files],
            timeout_seconds=30.0,
        )
    except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
        restore_staged_cp = None
    if restore_staged_cp is None or restore_staged_cp.returncode != 0:
        status = "safe_revert_blocked_git_failed"
        next_action = "manual_review_required"
        blocked_reason = "git_restore_staged_failed"
        try:
            post_status_cp = _run_git(str(repo_obj), ["status", "--short"], timeout_seconds=10.0)
            post_git_status_short = _normalize_text(post_status_cp.stdout, default="")
        except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
            post_git_status_short = ""
        return {
            "project_browser_autonomous_safe_revert_status": status,
            "project_browser_autonomous_safe_revert_next_action": next_action,
            "project_browser_autonomous_safe_revert_enabled": bool(safe_revert_enabled),
            "project_browser_autonomous_safe_revert_execute_enabled": bool(
                safe_revert_execute_enabled
            ),
            "project_browser_autonomous_safe_revert_reverted": bool(reverted),
            "project_browser_autonomous_safe_revert_changed_files": _normalize_string_list(
                safe_changed_files
            ),
            "project_browser_autonomous_safe_revert_revert_reason": revert_reason,
            "project_browser_autonomous_safe_revert_revert_plan": revert_plan,
            "project_browser_autonomous_safe_revert_pre_git_status_short": pre_git_status_short,
            "project_browser_autonomous_safe_revert_post_git_status_short": post_git_status_short,
            "project_browser_autonomous_safe_revert_blocked_reason": blocked_reason,
        }

    try:
        restore_cp = _run_git(
            str(repo_obj),
            ["restore", "--", *safe_changed_files],
            timeout_seconds=30.0,
        )
    except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
        restore_cp = None
    if restore_cp is None or restore_cp.returncode != 0:
        status = "safe_revert_blocked_git_failed"
        next_action = "manual_review_required"
        blocked_reason = "git_restore_failed"
        try:
            post_status_cp = _run_git(str(repo_obj), ["status", "--short"], timeout_seconds=10.0)
            post_git_status_short = _normalize_text(post_status_cp.stdout, default="")
        except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
            post_git_status_short = ""
        return {
            "project_browser_autonomous_safe_revert_status": status,
            "project_browser_autonomous_safe_revert_next_action": next_action,
            "project_browser_autonomous_safe_revert_enabled": bool(safe_revert_enabled),
            "project_browser_autonomous_safe_revert_execute_enabled": bool(
                safe_revert_execute_enabled
            ),
            "project_browser_autonomous_safe_revert_reverted": bool(reverted),
            "project_browser_autonomous_safe_revert_changed_files": _normalize_string_list(
                safe_changed_files
            ),
            "project_browser_autonomous_safe_revert_revert_reason": revert_reason,
            "project_browser_autonomous_safe_revert_revert_plan": revert_plan,
            "project_browser_autonomous_safe_revert_pre_git_status_short": pre_git_status_short,
            "project_browser_autonomous_safe_revert_post_git_status_short": post_git_status_short,
            "project_browser_autonomous_safe_revert_blocked_reason": blocked_reason,
        }

    try:
        post_status_cp = _run_git(str(repo_obj), ["status", "--short"], timeout_seconds=10.0)
    except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
        post_status_cp = None
    if post_status_cp is None:
        status = "safe_revert_blocked_git_failed"
        next_action = "manual_review_required"
        blocked_reason = "git_status_post_failed"
        return {
            "project_browser_autonomous_safe_revert_status": status,
            "project_browser_autonomous_safe_revert_next_action": next_action,
            "project_browser_autonomous_safe_revert_enabled": bool(safe_revert_enabled),
            "project_browser_autonomous_safe_revert_execute_enabled": bool(
                safe_revert_execute_enabled
            ),
            "project_browser_autonomous_safe_revert_reverted": bool(reverted),
            "project_browser_autonomous_safe_revert_changed_files": _normalize_string_list(
                safe_changed_files
            ),
            "project_browser_autonomous_safe_revert_revert_reason": revert_reason,
            "project_browser_autonomous_safe_revert_revert_plan": revert_plan,
            "project_browser_autonomous_safe_revert_pre_git_status_short": pre_git_status_short,
            "project_browser_autonomous_safe_revert_post_git_status_short": post_git_status_short,
            "project_browser_autonomous_safe_revert_blocked_reason": blocked_reason,
        }
    post_git_status_short = _normalize_text(post_status_cp.stdout, default="")

    post_parsed_status, post_ambiguous_status = _parse_git_status_short(post_git_status_short)
    if post_ambiguous_status:
        status = "safe_revert_blocked_ambiguous_status"
        next_action = "manual_review_required"
        blocked_reason = post_ambiguous_status[0]
        return {
            "project_browser_autonomous_safe_revert_status": status,
            "project_browser_autonomous_safe_revert_next_action": next_action,
            "project_browser_autonomous_safe_revert_enabled": bool(safe_revert_enabled),
            "project_browser_autonomous_safe_revert_execute_enabled": bool(
                safe_revert_execute_enabled
            ),
            "project_browser_autonomous_safe_revert_reverted": bool(reverted),
            "project_browser_autonomous_safe_revert_changed_files": _normalize_string_list(
                safe_changed_files
            ),
            "project_browser_autonomous_safe_revert_revert_reason": revert_reason,
            "project_browser_autonomous_safe_revert_revert_plan": revert_plan,
            "project_browser_autonomous_safe_revert_pre_git_status_short": pre_git_status_short,
            "project_browser_autonomous_safe_revert_post_git_status_short": post_git_status_short,
            "project_browser_autonomous_safe_revert_blocked_reason": blocked_reason,
        }

    if any(path in post_parsed_status for path in safe_changed_files):
        status = "safe_revert_blocked_post_status_not_clean"
        next_action = "manual_review_required"
        blocked_reason = "changed_files_still_present_after_restore"
        return {
            "project_browser_autonomous_safe_revert_status": status,
            "project_browser_autonomous_safe_revert_next_action": next_action,
            "project_browser_autonomous_safe_revert_enabled": bool(safe_revert_enabled),
            "project_browser_autonomous_safe_revert_execute_enabled": bool(
                safe_revert_execute_enabled
            ),
            "project_browser_autonomous_safe_revert_reverted": bool(reverted),
            "project_browser_autonomous_safe_revert_changed_files": _normalize_string_list(
                safe_changed_files
            ),
            "project_browser_autonomous_safe_revert_revert_reason": revert_reason,
            "project_browser_autonomous_safe_revert_revert_plan": revert_plan,
            "project_browser_autonomous_safe_revert_pre_git_status_short": pre_git_status_short,
            "project_browser_autonomous_safe_revert_post_git_status_short": post_git_status_short,
            "project_browser_autonomous_safe_revert_blocked_reason": blocked_reason,
        }

    status = "safe_revert_reverted"
    next_action = "regenerate_pr_prompt_or_continue_loop"
    blocked_reason = "none"
    reverted = True
    return {
        "project_browser_autonomous_safe_revert_status": status,
        "project_browser_autonomous_safe_revert_next_action": next_action,
        "project_browser_autonomous_safe_revert_enabled": bool(safe_revert_enabled),
        "project_browser_autonomous_safe_revert_execute_enabled": bool(
            safe_revert_execute_enabled
        ),
        "project_browser_autonomous_safe_revert_reverted": bool(reverted),
        "project_browser_autonomous_safe_revert_changed_files": _normalize_string_list(
            safe_changed_files
        ),
        "project_browser_autonomous_safe_revert_revert_reason": revert_reason,
        "project_browser_autonomous_safe_revert_revert_plan": revert_plan,
        "project_browser_autonomous_safe_revert_pre_git_status_short": pre_git_status_short,
        "project_browser_autonomous_safe_revert_post_git_status_short": post_git_status_short,
        "project_browser_autonomous_safe_revert_blocked_reason": blocked_reason,
    }

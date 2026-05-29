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
from automation.orchestration.planned_runner.project_browser.local_loop import (
    _build_project_browser_autonomous_post_write_validation_execution_state,
)

def _build_project_browser_response_assimilation_state(
    *,
    browser_task_status: str,
    browser_response_status: str,
    browser_response_compact: Mapping[str, Any] | None,
    browser_prompt_payload_status: str,
    browser_prompt_context_level: str,
    browser_prompt_token_posture: str,
    browser_prompt_schema_required_json_available: bool,
    browser_ui_failure_status: str,
    hard_gate_blocked: bool,
    continuation_threshold: int,
) -> dict[str, Any]:
    normalized_task_status = _normalize_text(browser_task_status, default="inactive")
    normalized_response_status = _normalize_text(
        browser_response_status,
        default="inactive",
    )
    normalized_prompt_status = _normalize_text(
        browser_prompt_payload_status,
        default="insufficient_truth",
    )
    response = (
        dict(browser_response_compact)
        if isinstance(browser_response_compact, Mapping)
        else {}
    )

    status = "inactive"
    decision = "unavailable"
    risk_level = "unavailable"
    score_posture = "unavailable"
    proof_posture = "unavailable"
    next_action_posture = "no_action"

    if normalized_task_status == "inactive" or normalized_prompt_status == "inactive":
        status = "inactive"
    elif normalized_prompt_status == "unavailable":
        status = "unavailable"
    elif (
        normalized_prompt_status == "insufficient_truth"
        or not browser_prompt_schema_required_json_available
        or _normalize_text(browser_prompt_context_level, default="insufficient_truth")
        == "insufficient_truth"
        or _normalize_text(browser_prompt_token_posture, default="blocked_insufficient_truth")
        == "blocked_insufficient_truth"
    ):
        status = "insufficient_truth"
    elif normalized_response_status == "invalid_response":
        status = "invalid_response"
    elif normalized_response_status == "unavailable":
        status = "unavailable"
        if _normalize_text(browser_ui_failure_status, default="") in {
            "retryable_ui_failure",
            "response_unavailable",
            "loading_timeout",
        }:
            next_action_posture = "candidate_retry"
    elif normalized_response_status != "valid":
        status = "insufficient_truth"
    else:
        parsed_decision = _normalize_text(response.get("decision"), default="")
        parsed_risk = _normalize_text(response.get("risk_level"), default="")
        parsed_task_type = _normalize_text(response.get("task_type"), default="")
        parsed_objective_id = _normalize_text(response.get("objective_id"), default="")
        parsed_step_id = _normalize_text(response.get("step_id"), default="")
        missing_required = any(
            (
                parsed_decision not in _PROJECT_BROWSER_DECISIONS,
                parsed_risk not in _PROJECT_BROWSER_RISK_LEVELS,
                not parsed_task_type,
                not parsed_objective_id,
                not parsed_step_id,
            )
        )
        if missing_required:
            status = "insufficient_truth"
        else:
            status = "assimilated"
            decision = (
                parsed_decision
                if parsed_decision in _PROJECT_BROWSER_ASSIMILATED_DECISIONS
                else "unavailable"
            )
            risk_level = (
                parsed_risk
                if parsed_risk in _PROJECT_BROWSER_ASSIMILATED_RISK_LEVELS
                else "unavailable"
            )
            raw_score = response.get("success_score")
            score_missing = bool(
                raw_score is None
                or isinstance(raw_score, bool)
                or (
                    isinstance(raw_score, str)
                    and not raw_score.strip().isdigit()
                )
            )
            if score_missing:
                score_posture = "insufficient_truth"
                proof_posture = "insufficient_truth"
            else:
                success_score = _as_non_negative_int(raw_score, default=0)
                if success_score >= max(0, continuation_threshold):
                    score_posture = "above_threshold"
                    proof_posture = (
                        "proof_loss" if hard_gate_blocked else "proof_available"
                    )
                else:
                    score_posture = "below_threshold"
                    proof_posture = "proof_missing"
            next_action_posture = {
                "continue": "candidate_continue",
                "retry": "candidate_retry",
                "replan": "candidate_replan",
                "split": "candidate_split",
                "repair": "candidate_repair",
                "restart": "candidate_restart",
                "escalate": "candidate_escalate",
                "stop": "candidate_stop",
            }.get(decision, "no_action")

    if status not in _PROJECT_BROWSER_RESPONSE_ASSIMILATION_STATUSES:
        status = "insufficient_truth"
    if decision not in _PROJECT_BROWSER_ASSIMILATED_DECISIONS:
        decision = "unavailable"
    if risk_level not in _PROJECT_BROWSER_ASSIMILATED_RISK_LEVELS:
        risk_level = "unavailable"
    if score_posture not in _PROJECT_BROWSER_SCORE_POSTURES:
        score_posture = "insufficient_truth"
    if proof_posture not in _PROJECT_BROWSER_PROOF_POSTURES:
        proof_posture = "insufficient_truth"
    if next_action_posture not in _PROJECT_BROWSER_NEXT_ACTION_POSTURES:
        next_action_posture = "no_action"

    runtime_posture = [
        "metadata_only",
        "no_queue_mutation",
        "no_retry_execution",
        "no_repair_execution",
        "no_restart_execution",
        "no_browser_action",
    ]
    return {
        "project_browser_response_assimilation_status": status,
        "project_browser_assimilated_decision": decision,
        "project_browser_assimilated_risk_level": risk_level,
        "project_browser_score_posture": score_posture,
        "project_browser_proof_posture": proof_posture,
        "project_browser_next_action_posture": next_action_posture,
        "project_browser_response_assimilation_hard_gate_blocked": bool(
            hard_gate_blocked
        ),
        "project_browser_response_assimilation_threshold": _as_non_negative_int(
            continuation_threshold,
            default=_PROJECT_BROWSER_CONTINUATION_THRESHOLD,
        ),
        "project_browser_assimilation_runtime_posture": runtime_posture,
        "project_browser_assimilation_runtime_metadata_only": True,
        "project_browser_assimilation_runtime_no_queue_mutation": True,
        "project_browser_assimilation_runtime_no_retry_execution": True,
        "project_browser_assimilation_runtime_no_repair_execution": True,
        "project_browser_assimilation_runtime_no_restart_execution": True,
        "project_browser_assimilation_runtime_no_browser_action": True,
    }

def _build_project_browser_autonomous_dev_assimilation_state(
    *,
    browser_task_status: str,
    one_command_executor_status: str,
    one_command_executor_result: str,
    one_command_executor_receipt_status: str,
    response_wait_block_reason: str,
    response_parse_block_reason: str,
    recovery_status: str,
    recovery_action: str,
    recovery_reason_runtime: str,
    retry_count_posture: str,
    login_interruption_status: str,
) -> dict[str, Any]:
    task_status = _normalize_text(browser_task_status, default="inactive")
    executor_status = _normalize_text(
        one_command_executor_status,
        default="insufficient_truth",
    )
    executor_result = _normalize_text(
        one_command_executor_result,
        default="insufficient_truth",
    )
    executor_receipt_status = _normalize_text(
        one_command_executor_receipt_status,
        default="insufficient_truth",
    )
    response_wait_block_reason = _normalize_text(
        response_wait_block_reason,
        default="insufficient_truth",
    )
    response_parse_block_reason = _normalize_text(
        response_parse_block_reason,
        default="insufficient_truth",
    )
    recovery_status = _normalize_text(recovery_status, default="insufficient_truth")
    recovery_action = _normalize_text(recovery_action, default="none")
    recovery_reason_runtime = _normalize_text(
        recovery_reason_runtime,
        default="insufficient_truth",
    )
    retry_count_posture = _normalize_text(
        retry_count_posture,
        default="insufficient_truth",
    )
    login_interruption_status = _normalize_text(
        login_interruption_status,
        default="insufficient_truth",
    )

    assimilation_status = "insufficient_truth"
    outcome = "insufficient_truth"
    next_action = "stop"
    stop_reason = "insufficient_truth"
    same_prompt_retry_policy = "insufficient_truth"
    same_prompt_retry_reason = "insufficient_truth"

    if task_status == "inactive" or executor_status == "inactive":
        assimilation_status = "inactive"
        outcome = "none"
        next_action = "none"
        stop_reason = "none"
        same_prompt_retry_policy = "not_applicable"
        same_prompt_retry_reason = "none"
    elif executor_receipt_status in {"not_created", "none", ""}:
        assimilation_status = "insufficient_truth"
        outcome = "insufficient_truth"
        next_action = "stop"
        stop_reason = "final_receipt_missing"
    elif executor_status == "pause_required" or executor_result == "pause_for_login":
        assimilation_status = "pause_required"
        outcome = "pause_for_login"
        next_action = "pause_for_login"
        stop_reason = "pause_for_login"
        same_prompt_retry_policy = "human_review_required"
        same_prompt_retry_reason = (
            "login_resumed"
            if login_interruption_status == "not_detected"
            else "insufficient_truth"
        )
    elif executor_status == "completed_with_recovery" or executor_result == "recovered":
        assimilation_status = "assimilated"
        outcome = "recovered"
        stop_reason = "recovery_completed"
        if recovery_action == "page_reload":
            next_action = "retry_same_prompt_candidate"
            same_prompt_retry_policy = (
                "allowed_candidate"
                if retry_count_posture == "retry_available"
                else (
                    "retry_budget_exhausted"
                    if retry_count_posture == "retry_limit_reached"
                    else "insufficient_truth"
                )
            )
            same_prompt_retry_reason = "page_reload_completed"
        elif recovery_action == "new_chat":
            next_action = "retry_same_prompt_candidate"
            same_prompt_retry_policy = (
                "allowed_candidate"
                if retry_count_posture == "retry_available"
                else (
                    "retry_budget_exhausted"
                    if retry_count_posture == "retry_limit_reached"
                    else "insufficient_truth"
                )
            )
            same_prompt_retry_reason = "new_chat_opened"
        elif recovery_action == "pause_for_login":
            assimilation_status = "pause_required"
            outcome = "pause_for_login"
            next_action = "pause_for_login"
            stop_reason = "pause_for_login"
            same_prompt_retry_policy = "human_review_required"
            same_prompt_retry_reason = "insufficient_truth"
        else:
            next_action = "human_review_required"
            same_prompt_retry_policy = "human_review_required"
            same_prompt_retry_reason = (
                "same_failure"
                if recovery_reason_runtime in {"invalid_response", "response_unavailable"}
                else "insufficient_truth"
            )
    elif executor_status == "completed" and executor_result == "success":
        assimilation_status = "assimilated"
        outcome = "success"
        next_action = "draft_md_update"
        stop_reason = "final_success"
        same_prompt_retry_policy = "not_applicable"
        same_prompt_retry_reason = "none"
    elif executor_status == "completed" and executor_result == "invalid_response":
        assimilation_status = "assimilated"
        outcome = "invalid_response"
        stop_reason = "invalid_response"
        if retry_count_posture == "retry_limit_reached":
            next_action = "draft_repair_prompt"
            same_prompt_retry_policy = "retry_budget_exhausted"
            same_prompt_retry_reason = "same_failure"
        elif retry_count_posture == "retry_available":
            if recovery_action in {"page_reload", "new_chat"}:
                next_action = "retry_same_prompt_candidate"
                same_prompt_retry_policy = "allowed_candidate"
                same_prompt_retry_reason = (
                    "page_reload_completed"
                    if recovery_action == "page_reload"
                    else "new_chat_opened"
                )
            elif response_parse_block_reason in {
                "json_parse_failed",
                "schema_missing",
                "schema_invalid",
                "decision_missing",
            }:
                next_action = "retry_same_prompt_candidate"
                same_prompt_retry_policy = "allowed_candidate"
                same_prompt_retry_reason = "invalid_response_retry_candidate"
            else:
                next_action = "draft_repair_prompt"
                same_prompt_retry_policy = "blocked_duplicate"
                same_prompt_retry_reason = "no_context_change"
        elif retry_count_posture == "insufficient_truth":
            next_action = "human_review_required"
            same_prompt_retry_policy = "insufficient_truth"
            same_prompt_retry_reason = "insufficient_truth"
        else:
            next_action = "draft_repair_prompt"
            same_prompt_retry_policy = "human_review_required"
            same_prompt_retry_reason = "same_failure"
    elif executor_status == "completed" and executor_result == "timeout":
        assimilation_status = "assimilated"
        outcome = "timeout"
        stop_reason = "timeout"
        if retry_count_posture == "retry_available":
            next_action = "retry_same_prompt_candidate"
            same_prompt_retry_policy = "allowed_candidate"
            same_prompt_retry_reason = (
                "response_unavailable"
                if response_wait_block_reason == "assistant_response_missing"
                else "transient_timeout"
            )
        elif retry_count_posture == "retry_limit_reached":
            next_action = "human_review_required"
            same_prompt_retry_policy = "retry_budget_exhausted"
            same_prompt_retry_reason = "same_failure"
        elif retry_count_posture == "insufficient_truth":
            next_action = "stop"
            same_prompt_retry_policy = "insufficient_truth"
            same_prompt_retry_reason = "insufficient_truth"
        else:
            next_action = "human_review_required"
            same_prompt_retry_policy = "human_review_required"
            same_prompt_retry_reason = "transient_timeout"
    elif executor_status == "blocked" or executor_result == "blocked":
        assimilation_status = "blocked"
        outcome = "blocked"
        next_action = "human_review_required"
        stop_reason = "blocked"
        if retry_count_posture == "retry_available" and recovery_reason_runtime in {
            "response_unavailable",
            "loading_timeout",
        }:
            same_prompt_retry_policy = "allowed_candidate"
            same_prompt_retry_reason = "response_unavailable"
            next_action = "retry_same_prompt_candidate"
        elif retry_count_posture == "retry_limit_reached":
            same_prompt_retry_policy = "retry_budget_exhausted"
            same_prompt_retry_reason = "same_failure"
        else:
            same_prompt_retry_policy = "human_review_required"
            same_prompt_retry_reason = "same_failure"
    elif executor_status == "failed" or executor_result == "failed":
        assimilation_status = "failed"
        outcome = "failed"
        next_action = "human_review_required"
        stop_reason = "failed"
        if retry_count_posture == "retry_available" and recovery_reason_runtime in {
            "response_unavailable",
            "loading_timeout",
        }:
            same_prompt_retry_policy = "allowed_candidate"
            same_prompt_retry_reason = "response_unavailable"
            next_action = "retry_same_prompt_candidate"
        elif retry_count_posture == "retry_limit_reached":
            same_prompt_retry_policy = "retry_budget_exhausted"
            same_prompt_retry_reason = "same_failure"
        else:
            same_prompt_retry_policy = "human_review_required"
            same_prompt_retry_reason = "same_failure"
    elif executor_status == "insufficient_truth" or executor_result == "insufficient_truth":
        assimilation_status = "insufficient_truth"
        outcome = "insufficient_truth"
        next_action = "stop"
        stop_reason = "insufficient_truth"
        same_prompt_retry_policy = "insufficient_truth"
        same_prompt_retry_reason = "insufficient_truth"
    else:
        assimilation_status = "insufficient_truth"
        outcome = "insufficient_truth"
        next_action = "stop"
        stop_reason = "unsupported_outcome"
        same_prompt_retry_policy = "insufficient_truth"
        same_prompt_retry_reason = "insufficient_truth"

    if assimilation_status not in _PROJECT_BROWSER_AUTONOMOUS_DEV_ASSIMILATION_STATUSES:
        assimilation_status = "insufficient_truth"
    if outcome not in _PROJECT_BROWSER_AUTONOMOUS_DEV_OUTCOMES:
        outcome = "insufficient_truth"
    if next_action not in _PROJECT_BROWSER_AUTONOMOUS_DEV_NEXT_ACTIONS:
        next_action = "stop"
    if stop_reason not in _PROJECT_BROWSER_AUTONOMOUS_DEV_STOP_REASONS:
        stop_reason = "insufficient_truth"
    if same_prompt_retry_policy not in _PROJECT_BROWSER_SAME_PROMPT_RETRY_POLICIES:
        same_prompt_retry_policy = "insufficient_truth"
    if same_prompt_retry_reason not in _PROJECT_BROWSER_SAME_PROMPT_RETRY_REASONS:
        same_prompt_retry_reason = "insufficient_truth"

    runtime_posture = [
        "metadata_only",
        "no_next_prompt_generation",
        "no_md_write",
        "no_browser_action",
        "no_resend",
        "no_reload",
        "no_new_chat",
        "no_queue_mutation",
        "no_decision_execution",
        "no_executor_loop",
    ]
    runtime_posture = [
        token
        for token in runtime_posture
        if token in _PROJECT_BROWSER_AUTONOMOUS_DEV_RUNTIME_POSTURES
    ]

    return {
        "project_browser_autonomous_dev_assimilation_status": assimilation_status,
        "project_browser_autonomous_dev_outcome": outcome,
        "project_browser_autonomous_dev_next_action": next_action,
        "project_browser_autonomous_dev_stop_reason": stop_reason,
        "project_browser_same_prompt_retry_policy": same_prompt_retry_policy,
        "project_browser_same_prompt_retry_reason": same_prompt_retry_reason,
        "project_browser_autonomous_dev_runtime_posture": runtime_posture,
        "project_browser_autonomous_dev_runtime_metadata_only": True,
        "project_browser_autonomous_dev_runtime_no_next_prompt_generation": True,
        "project_browser_autonomous_dev_runtime_no_md_write": True,
        "project_browser_autonomous_dev_runtime_no_browser_action": True,
        "project_browser_autonomous_dev_runtime_no_resend": True,
        "project_browser_autonomous_dev_runtime_no_reload": True,
        "project_browser_autonomous_dev_runtime_no_new_chat": True,
        "project_browser_autonomous_dev_runtime_no_queue_mutation": True,
        "project_browser_autonomous_dev_runtime_no_decision_execution": True,
        "project_browser_autonomous_dev_runtime_no_executor_loop": True,
    }

def _build_project_browser_autonomous_batch_evaluation_state(
    *,
    autonomous_multistep_budget_status: str,
    autonomous_multistep_permission: str,
    autonomous_multistep_next_step_candidate: str,
    autonomous_multistep_stop_reason: str,
    autonomous_multistep_budget_source_status: str,
    autonomous_multistep_state: Mapping[str, Any] | None,
    autonomous_action_duplicate_status: str,
    autonomous_safety_switch_status: str,
    autonomous_manual_override_status: str,
    autonomous_safe_stop_status: str,
    autonomous_execution_permission: str,
    autonomous_execution_bridge_status: str,
    autonomous_execution_bridge_permission: str,
    autonomous_execution_bridge_source_status: str,
    autonomous_step_wrapper_status: str,
    autonomous_step_action: str,
    autonomous_step_score_status: str,
    autonomous_step_score_band: str,
    autonomous_step_auto_approval_posture: str,
    autonomous_step_execution_result: str,
    autonomous_step_receipt_status: str,
    autonomous_step_stop_reason: str,
    autonomous_step_batch_posture: str,
) -> dict[str, Any]:
    budget_status = _normalize_text(
        autonomous_multistep_budget_status,
        default="insufficient_truth",
    )
    multistep_permission = _normalize_text(
        autonomous_multistep_permission,
        default="insufficient_truth",
    )
    next_step_candidate = _normalize_text(
        autonomous_multistep_next_step_candidate,
        default="none",
    )
    multistep_stop_reason = _normalize_text(
        autonomous_multistep_stop_reason,
        default="insufficient_truth",
    )
    budget_source_status = _normalize_text(
        autonomous_multistep_budget_source_status,
        default="insufficient_truth",
    )
    multistep_state = dict(autonomous_multistep_state or {})

    duplicate_status = _normalize_text(
        autonomous_action_duplicate_status,
        default="insufficient_truth",
    )
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
    bridge_status = _normalize_text(
        autonomous_execution_bridge_status,
        default="insufficient_truth",
    )
    bridge_permission = _normalize_text(
        autonomous_execution_bridge_permission,
        default="insufficient_truth",
    )
    bridge_source_status = _normalize_text(
        autonomous_execution_bridge_source_status,
        default="insufficient_truth",
    )

    step_wrapper_status = _normalize_text(
        autonomous_step_wrapper_status,
        default="insufficient_truth",
    )
    step_action = _normalize_text(autonomous_step_action, default="none")
    step_score_status = _normalize_text(
        autonomous_step_score_status,
        default="insufficient_truth",
    )
    step_score_band = _normalize_text(
        autonomous_step_score_band,
        default="insufficient_truth",
    )
    step_auto_approval_posture = _normalize_text(
        autonomous_step_auto_approval_posture,
        default="insufficient_truth",
    )
    step_execution_result = _normalize_text(
        autonomous_step_execution_result,
        default="insufficient_truth",
    )
    step_receipt_status = _normalize_text(
        autonomous_step_receipt_status,
        default="insufficient_truth",
    )
    step_stop_reason = _normalize_text(
        autonomous_step_stop_reason,
        default="insufficient_truth",
    )
    step_batch_posture = _normalize_text(
        autonomous_step_batch_posture,
        default="insufficient_truth",
    )

    runtime_posture = [
        "metadata_only",
        "no_next_step_start",
        "no_prompt_send",
        "no_md_write",
        "no_shell_execution",
        "no_codex_execution",
        "no_browser_action",
        "no_playwright",
        "no_dom_interaction",
        "no_queue_mutation",
        "no_retry_execution",
        "no_repair_execution",
        "no_restart_execution",
        "no_approval_execution",
        "no_continuation_execution",
        "no_loop_execution",
        "no_background_runtime",
    ]

    def _base_state(
        *,
        batch_evaluation_status: str,
        batch_continue_permission: str,
        batch_continue_reason: str,
        batch_next_action: str,
        batch_score_summary_status: str,
        batch_score_summary: str,
        observability_status: str,
        current_phase: str,
        last_action: str,
        last_result: str,
        last_stop_reason: str,
        remaining_budget_status: str,
        operator_summary_status: str,
        operator_summary_kind: str,
    ) -> dict[str, Any]:
        return {
            "project_browser_autonomous_batch_evaluation_status": batch_evaluation_status,
            "project_browser_autonomous_batch_continue_permission": batch_continue_permission,
            "project_browser_autonomous_batch_continue_reason": batch_continue_reason,
            "project_browser_autonomous_batch_next_action": batch_next_action,
            "project_browser_autonomous_batch_score_summary_status": batch_score_summary_status,
            "project_browser_autonomous_batch_score_summary": batch_score_summary,
            "project_browser_autonomous_observability_status": observability_status,
            "project_browser_autonomous_current_phase": current_phase,
            "project_browser_autonomous_last_action": last_action,
            "project_browser_autonomous_last_result": last_result,
            "project_browser_autonomous_last_stop_reason": last_stop_reason,
            "project_browser_autonomous_remaining_budget_status": remaining_budget_status,
            "project_browser_autonomous_operator_summary_status": operator_summary_status,
            "project_browser_autonomous_operator_summary_kind": operator_summary_kind,
            "project_browser_autonomous_observability_runtime_posture": runtime_posture,
            "project_browser_autonomous_observability_runtime_metadata_only": True,
            "project_browser_autonomous_observability_runtime_no_next_step_start": True,
            "project_browser_autonomous_observability_runtime_no_prompt_send": True,
            "project_browser_autonomous_observability_runtime_no_md_write": True,
            "project_browser_autonomous_observability_runtime_no_shell_execution": True,
            "project_browser_autonomous_observability_runtime_no_codex_execution": True,
            "project_browser_autonomous_observability_runtime_no_browser_action": True,
            "project_browser_autonomous_observability_runtime_no_playwright": True,
            "project_browser_autonomous_observability_runtime_no_dom_interaction": True,
            "project_browser_autonomous_observability_runtime_no_queue_mutation": True,
            "project_browser_autonomous_observability_runtime_no_retry_execution": True,
            "project_browser_autonomous_observability_runtime_no_repair_execution": True,
            "project_browser_autonomous_observability_runtime_no_restart_execution": True,
            "project_browser_autonomous_observability_runtime_no_approval_execution": True,
            "project_browser_autonomous_observability_runtime_no_continuation_execution": True,
            "project_browser_autonomous_observability_runtime_no_loop_execution": True,
            "project_browser_autonomous_observability_runtime_no_background_runtime": True,
        }

    def _insufficient_truth_state() -> dict[str, Any]:
        return _base_state(
            batch_evaluation_status="insufficient_truth",
            batch_continue_permission="insufficient_truth",
            batch_continue_reason="insufficient_truth",
            batch_next_action="none",
            batch_score_summary_status="insufficient_truth",
            batch_score_summary="insufficient_truth",
            observability_status="insufficient_truth",
            current_phase="insufficient_truth",
            last_action="none",
            last_result="insufficient_truth",
            last_stop_reason="insufficient_truth",
            remaining_budget_status="insufficient_truth",
            operator_summary_status="insufficient_truth",
            operator_summary_kind="insufficient_truth_summary",
        )

    if budget_status not in {
        "inactive",
        "ready",
        "blocked",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state()
    if multistep_permission not in _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS:
        return _insufficient_truth_state()
    if next_step_candidate not in {
        "none",
        "apply_md_update",
        "send_next_prompt",
        "retry_same_prompt",
        "pause_for_login",
        "human_review",
        "stop",
    }:
        return _insufficient_truth_state()
    if multistep_stop_reason not in {
        "none",
        "bridge_not_ready",
        "blocked_by_bridge",
        "pause_required",
        "human_review_required",
        "duplicate_risk",
        "retry_budget_exhausted",
        "failure_budget_exhausted",
        "step_budget_exhausted",
        "action_receipt_not_ready",
        "insufficient_truth",
    }:
        return _insufficient_truth_state()
    if budget_source_status not in {"valid", "inconsistent", "insufficient_truth"}:
        return _insufficient_truth_state()
    if duplicate_status not in _PROJECT_BROWSER_AUTONOMOUS_ACTION_DUPLICATE_STATUSES:
        return _insufficient_truth_state()
    if safety_switch_status not in _PROJECT_BROWSER_AUTONOMOUS_SAFETY_SWITCH_STATUSES:
        return _insufficient_truth_state()
    if manual_override_status not in _PROJECT_BROWSER_AUTONOMOUS_MANUAL_OVERRIDE_STATUSES:
        return _insufficient_truth_state()
    if safe_stop_status not in _PROJECT_BROWSER_AUTONOMOUS_SAFE_STOP_STATUSES:
        return _insufficient_truth_state()
    if execution_permission not in _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS:
        return _insufficient_truth_state()
    if bridge_status not in _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_BRIDGE_STATUSES:
        return _insufficient_truth_state()
    if bridge_permission not in _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS:
        return _insufficient_truth_state()
    if bridge_source_status not in _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_BRIDGE_SOURCE_STATUSES:
        return _insufficient_truth_state()
    if step_wrapper_status not in {
        "inactive",
        "ready",
        "auto_safe",
        "blocked",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state()
    if step_action not in {
        "none",
        "apply_md_update",
        "send_next_prompt",
        "retry_same_prompt",
        "pause_for_login",
        "human_review",
        "stop",
    }:
        return _insufficient_truth_state()
    if step_score_status not in {"unavailable", "scored", "insufficient_truth"}:
        return _insufficient_truth_state()
    if step_score_band not in {
        "auto_safe_without_approval",
        "auto_candidate",
        "human_review_recommended",
        "blocked",
        "insufficient_truth",
    }:
        return _insufficient_truth_state()
    if step_auto_approval_posture not in {
        "allowed_without_human",
        "blocked_needs_human",
        "pause_required",
        "blocked_by_budget",
        "blocked_by_duplicate",
        "insufficient_truth",
    }:
        return _insufficient_truth_state()
    if step_execution_result not in {
        "not_executed",
        "candidate_recorded",
        "blocked",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state()
    if step_receipt_status not in {
        "not_created",
        "ready",
        "blocked",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state()
    if step_stop_reason not in {
        "none",
        "one_step_recorded",
        "score_below_auto_safe",
        "bridge_or_budget_not_ready",
        "duplicate_risk",
        "retry_budget_exhausted",
        "failure_budget_exhausted",
        "step_budget_exhausted",
        "pause_for_login",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state()
    if step_batch_posture not in {
        "not_started",
        "one_step_recorded",
        "batch_continue_candidate",
        "batch_blocked",
        "batch_pause_required",
        "batch_human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state()

    if (
        budget_source_status in {"inconsistent", "insufficient_truth"}
        or bridge_source_status in {"inconsistent", "insufficient_truth"}
    ):
        return _insufficient_truth_state()

    remaining_steps = _as_non_negative_int(
        multistep_state.get("project_browser_autonomous_multistep_remaining_steps"),
        default=0,
    )
    remaining_failures = _as_non_negative_int(
        multistep_state.get("project_browser_autonomous_multistep_remaining_failures"),
        default=0,
    )
    retry_remaining = _as_non_negative_int(
        multistep_state.get("project_browser_autonomous_multistep_same_prompt_retry_remaining"),
        default=0,
    )

    retry_exhausted = bool(step_action == "retry_same_prompt" and retry_remaining <= 0)
    duplicate_risk_present = duplicate_status not in {"clear", "no_duplicate", "not_duplicate"}
    budget_exhausted = remaining_steps <= 0
    failure_exhausted = remaining_failures <= 0

    def _map_stop_reason(value: str) -> str:
        if value in {"none", "one_step_recorded", "score_below_auto_safe", "duplicate_risk"}:
            return value
        if value in {"step_budget_exhausted", "bridge_or_budget_not_ready"}:
            return "budget_exhausted"
        if value == "failure_budget_exhausted":
            return "failure_budget_exhausted"
        if value == "retry_budget_exhausted":
            return "retry_budget_exhausted"
        if value == "pause_for_login":
            return "pause_for_login"
        if value == "human_review_required":
            return "human_review_required"
        return "insufficient_truth"

    mapped_last_stop_reason = _map_stop_reason(step_stop_reason)
    if mapped_last_stop_reason == "insufficient_truth":
        return _insufficient_truth_state()

    score_summary_status = (
        "available"
        if step_score_status == "scored"
        else ("unavailable" if step_score_status == "unavailable" else "insufficient_truth")
    )
    score_summary = (
        step_score_band
        if score_summary_status == "available"
        else ("insufficient_truth" if score_summary_status == "insufficient_truth" else "insufficient_truth")
    )
    if score_summary_status == "insufficient_truth":
        return _insufficient_truth_state()

    remaining_budget_status = "available"
    if budget_exhausted or failure_exhausted or retry_exhausted:
        remaining_budget_status = "exhausted"
    if step_wrapper_status == "inactive":
        remaining_budget_status = "unavailable"

    if step_wrapper_status == "inactive":
        current_phase = "inactive" if budget_status == "inactive" else "budget_compiled"
        return _base_state(
            batch_evaluation_status="inactive",
            batch_continue_permission="insufficient_truth",
            batch_continue_reason="none",
            batch_next_action="none",
            batch_score_summary_status="unavailable",
            batch_score_summary="insufficient_truth",
            observability_status="unavailable",
            current_phase=current_phase,
            last_action="none",
            last_result="none",
            last_stop_reason="none",
            remaining_budget_status="unavailable",
            operator_summary_status="unavailable",
            operator_summary_kind="none",
        )
    if step_wrapper_status == "insufficient_truth":
        return _insufficient_truth_state()
    if step_wrapper_status == "pause_required":
        return _base_state(
            batch_evaluation_status="pause_required",
            batch_continue_permission="pause_required",
            batch_continue_reason="pause_required",
            batch_next_action="pause_for_login",
            batch_score_summary_status=score_summary_status,
            batch_score_summary=score_summary,
            observability_status="available",
            current_phase="pause_required",
            last_action="pause_for_login",
            last_result="pause_required",
            last_stop_reason="pause_for_login",
            remaining_budget_status=remaining_budget_status,
            operator_summary_status="compact_available",
            operator_summary_kind="pause_summary",
        )
    if step_wrapper_status == "human_review_required":
        return _base_state(
            batch_evaluation_status="human_review_required",
            batch_continue_permission="human_review_required",
            batch_continue_reason="human_review_required",
            batch_next_action="human_review",
            batch_score_summary_status=score_summary_status,
            batch_score_summary=score_summary,
            observability_status="available",
            current_phase="human_review_required",
            last_action="human_review",
            last_result="human_review_required",
            last_stop_reason="human_review_required",
            remaining_budget_status=remaining_budget_status,
            operator_summary_status="compact_available",
            operator_summary_kind="human_review_summary",
        )
    if step_wrapper_status == "blocked":
        blocked_reason = "score_below_auto_safe"
        if mapped_last_stop_reason in {
            "duplicate_risk",
            "retry_budget_exhausted",
            "failure_budget_exhausted",
            "budget_exhausted",
        }:
            blocked_reason = mapped_last_stop_reason
        return _base_state(
            batch_evaluation_status="blocked",
            batch_continue_permission="blocked",
            batch_continue_reason=blocked_reason,
            batch_next_action="stop",
            batch_score_summary_status=score_summary_status,
            batch_score_summary=score_summary,
            observability_status="blocked",
            current_phase="blocked",
            last_action=step_action,
            last_result="blocked",
            last_stop_reason=mapped_last_stop_reason,
            remaining_budget_status=remaining_budget_status,
            operator_summary_status="compact_available",
            operator_summary_kind="blocked_summary",
        )

    if step_wrapper_status not in {"ready", "auto_safe"}:
        return _insufficient_truth_state()

    upstream_clear = bool(
        budget_status == "ready"
        and multistep_permission == "allowed_candidate"
        and execution_permission == "allowed_candidate"
        and bridge_status == "ready"
        and bridge_permission == "allowed_candidate"
        and bridge_source_status == "valid"
        and safety_switch_status in {"enabled", "inactive"}
        and manual_override_status in {"inactive", "clear"}
        and safe_stop_status == "not_required"
    )

    if budget_exhausted:
        return _base_state(
            batch_evaluation_status="stopped",
            batch_continue_permission="blocked",
            batch_continue_reason="budget_exhausted",
            batch_next_action="stop",
            batch_score_summary_status=score_summary_status,
            batch_score_summary=score_summary,
            observability_status="available",
            current_phase="stopped",
            last_action=step_action,
            last_result=step_execution_result if step_execution_result != "insufficient_truth" else "none",
            last_stop_reason="budget_exhausted",
            remaining_budget_status="exhausted",
            operator_summary_status="compact_available",
            operator_summary_kind="stopped_summary",
        )
    if failure_exhausted:
        return _base_state(
            batch_evaluation_status="blocked",
            batch_continue_permission="blocked",
            batch_continue_reason="failure_budget_exhausted",
            batch_next_action="stop",
            batch_score_summary_status=score_summary_status,
            batch_score_summary=score_summary,
            observability_status="blocked",
            current_phase="blocked",
            last_action=step_action,
            last_result="blocked",
            last_stop_reason="failure_budget_exhausted",
            remaining_budget_status="exhausted",
            operator_summary_status="compact_available",
            operator_summary_kind="blocked_summary",
        )
    if retry_exhausted:
        return _base_state(
            batch_evaluation_status="blocked",
            batch_continue_permission="blocked",
            batch_continue_reason="retry_budget_exhausted",
            batch_next_action="stop",
            batch_score_summary_status=score_summary_status,
            batch_score_summary=score_summary,
            observability_status="blocked",
            current_phase="blocked",
            last_action=step_action,
            last_result="blocked",
            last_stop_reason="retry_budget_exhausted",
            remaining_budget_status="exhausted",
            operator_summary_status="compact_available",
            operator_summary_kind="blocked_summary",
        )
    if duplicate_risk_present:
        return _base_state(
            batch_evaluation_status="blocked",
            batch_continue_permission="blocked",
            batch_continue_reason="duplicate_risk",
            batch_next_action="stop",
            batch_score_summary_status=score_summary_status,
            batch_score_summary=score_summary,
            observability_status="blocked",
            current_phase="blocked",
            last_action=step_action,
            last_result="blocked",
            last_stop_reason="duplicate_risk",
            remaining_budget_status=remaining_budget_status,
            operator_summary_status="compact_available",
            operator_summary_kind="blocked_summary",
        )
    if step_receipt_status != "ready":
        return _base_state(
            batch_evaluation_status="stopped",
            batch_continue_permission="blocked",
            batch_continue_reason="step_receipt_missing",
            batch_next_action="stop",
            batch_score_summary_status=score_summary_status,
            batch_score_summary=score_summary,
            observability_status="available",
            current_phase="stopped",
            last_action=step_action,
            last_result=step_execution_result if step_execution_result != "insufficient_truth" else "none",
            last_stop_reason="insufficient_truth",
            remaining_budget_status=remaining_budget_status,
            operator_summary_status="compact_available",
            operator_summary_kind="stopped_summary",
        )
    if not upstream_clear:
        return _base_state(
            batch_evaluation_status="blocked",
            batch_continue_permission="blocked",
            batch_continue_reason="insufficient_truth",
            batch_next_action="stop",
            batch_score_summary_status=score_summary_status,
            batch_score_summary=score_summary,
            observability_status="blocked",
            current_phase="blocked",
            last_action=step_action,
            last_result="blocked",
            last_stop_reason="insufficient_truth",
            remaining_budget_status=remaining_budget_status,
            operator_summary_status="compact_available",
            operator_summary_kind="blocked_summary",
        )

    if step_score_band == "auto_safe_without_approval":
        if (
            step_auto_approval_posture == "allowed_without_human"
            and step_batch_posture == "batch_continue_candidate"
        ):
            return _base_state(
                batch_evaluation_status="continue_candidate",
                batch_continue_permission="allowed_candidate",
                batch_continue_reason="score_auto_safe",
                batch_next_action="continue_later",
                batch_score_summary_status=score_summary_status,
                batch_score_summary=score_summary,
                observability_status="available",
                current_phase="batch_continue_candidate",
                last_action=step_action,
                last_result="candidate_recorded",
                last_stop_reason="one_step_recorded",
                remaining_budget_status="available",
                operator_summary_status="compact_available",
                operator_summary_kind="batch_continue_summary",
            )
        return _base_state(
            batch_evaluation_status="stopped",
            batch_continue_permission="blocked",
            batch_continue_reason="score_below_auto_safe",
            batch_next_action="stop",
            batch_score_summary_status=score_summary_status,
            batch_score_summary=score_summary,
            observability_status="available",
            current_phase="stopped",
            last_action=step_action,
            last_result=step_execution_result if step_execution_result != "insufficient_truth" else "none",
            last_stop_reason="score_below_auto_safe",
            remaining_budget_status=remaining_budget_status,
            operator_summary_status="compact_available",
            operator_summary_kind="stopped_summary",
        )
    if step_score_band == "auto_candidate":
        return _base_state(
            batch_evaluation_status="human_review_required",
            batch_continue_permission="human_review_required",
            batch_continue_reason="score_below_auto_safe",
            batch_next_action="human_review",
            batch_score_summary_status=score_summary_status,
            batch_score_summary=score_summary,
            observability_status="available",
            current_phase="human_review_required",
            last_action=step_action,
            last_result="human_review_required",
            last_stop_reason="score_below_auto_safe",
            remaining_budget_status=remaining_budget_status,
            operator_summary_status="compact_available",
            operator_summary_kind="human_review_summary",
        )
    if step_score_band == "human_review_recommended":
        return _base_state(
            batch_evaluation_status="human_review_required",
            batch_continue_permission="human_review_required",
            batch_continue_reason="human_review_required",
            batch_next_action="human_review",
            batch_score_summary_status=score_summary_status,
            batch_score_summary=score_summary,
            observability_status="available",
            current_phase="human_review_required",
            last_action=step_action,
            last_result="human_review_required",
            last_stop_reason="human_review_required",
            remaining_budget_status=remaining_budget_status,
            operator_summary_status="compact_available",
            operator_summary_kind="human_review_summary",
        )
    if step_score_band == "blocked":
        return _base_state(
            batch_evaluation_status="blocked",
            batch_continue_permission="blocked",
            batch_continue_reason="score_below_auto_safe",
            batch_next_action="stop",
            batch_score_summary_status=score_summary_status,
            batch_score_summary=score_summary,
            observability_status="blocked",
            current_phase="blocked",
            last_action=step_action,
            last_result="blocked",
            last_stop_reason="score_below_auto_safe",
            remaining_budget_status=remaining_budget_status,
            operator_summary_status="compact_available",
            operator_summary_kind="blocked_summary",
        )

    return _insufficient_truth_state()

def _build_project_browser_autonomous_result_assimilation_state(
    *,
    autonomous_browser_execution_status: str,
    autonomous_browser_execution_source_status: str,
    autonomous_browser_execution_command_type: str,
    autonomous_browser_execution_response_wait_status: str,
    autonomous_browser_execution_response_read_status: str,
    autonomous_browser_execution_response_text_status: str,
    autonomous_browser_execution_block_reason: str,
    autonomous_browser_execution_receipt_status: str,
    autonomous_browser_enqueue_status: str,
    autonomous_browser_enqueue_permission: str,
    autonomous_browser_enqueue_retry_budget_status: str,
    autonomous_execution_adapter_status: str,
    autonomous_execution_adapter_action: str,
    autonomous_execution_adapter_risk_status: str,
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
    autonomous_retry_budget_posture: str,
    browser_response_json_parse_status: str,
    project_pr_queue_status: str,
    project_pr_queue_handoff_prepared: bool,
    project_pr_queue_handoff_payload: Mapping[str, Any] | None,
    implementation_prompt_status: str,
    implementation_prompt_available: bool,
) -> dict[str, Any]:
    execution_status = _normalize_text(
        autonomous_browser_execution_status,
        default="insufficient_truth",
    )
    execution_source_status = _normalize_text(
        autonomous_browser_execution_source_status,
        default="insufficient_truth",
    )
    execution_command_type = _normalize_text(
        autonomous_browser_execution_command_type,
        default="insufficient_truth",
    )
    execution_wait_status = _normalize_text(
        autonomous_browser_execution_response_wait_status,
        default="insufficient_truth",
    )
    execution_read_status = _normalize_text(
        autonomous_browser_execution_response_read_status,
        default="insufficient_truth",
    )
    execution_text_status = _normalize_text(
        autonomous_browser_execution_response_text_status,
        default="insufficient_truth",
    )
    execution_block_reason = _normalize_text(
        autonomous_browser_execution_block_reason,
        default="insufficient_truth",
    )
    execution_receipt_status = _normalize_text(
        autonomous_browser_execution_receipt_status,
        default="insufficient_truth",
    )
    enqueue_status = _normalize_text(
        autonomous_browser_enqueue_status,
        default="insufficient_truth",
    )
    enqueue_permission = _normalize_text(
        autonomous_browser_enqueue_permission,
        default="insufficient_truth",
    )
    enqueue_retry_budget_status = _normalize_text(
        autonomous_browser_enqueue_retry_budget_status,
        default="insufficient_truth",
    )
    adapter_status = _normalize_text(
        autonomous_execution_adapter_status,
        default="insufficient_truth",
    )
    adapter_action = _normalize_text(
        autonomous_execution_adapter_action,
        default="none",
    )
    adapter_risk_status = _normalize_text(
        autonomous_execution_adapter_risk_status,
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
    retry_budget_posture = _normalize_text(
        autonomous_retry_budget_posture,
        default="insufficient_truth",
    )
    response_json_parse_status = _normalize_text(
        browser_response_json_parse_status,
        default="insufficient_truth",
    )
    pr_queue_status = _normalize_text(project_pr_queue_status, default="insufficient_truth")
    queue_handoff_prepared = bool(project_pr_queue_handoff_prepared)
    queue_handoff_payload = (
        dict(project_pr_queue_handoff_payload)
        if isinstance(project_pr_queue_handoff_payload, Mapping)
        else {}
    )
    normalized_implementation_prompt_status = _normalize_text(
        implementation_prompt_status,
        default="insufficient_truth",
    )
    normalized_implementation_prompt_available = bool(implementation_prompt_available)

    runtime_posture = [
        "metadata_only",
        "no_codex_execution",
        "no_shell_execution",
        "no_md_write",
        "no_prompt_send",
        "no_browser_enqueue",
        "no_browser_action",
        "no_playwright",
        "no_dom_interaction",
        "no_response_wait",
        "no_response_read",
        "no_json_deep_parse",
        "no_queue_mutation",
        "no_retry_execution",
        "no_repair_execution",
        "no_restart_execution",
        "no_approval_execution",
        "no_continuation_execution",
        "no_counter_mutation",
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
        browser_result_outcome: str,
        response_usability_status: str,
        response_handoff_status: str,
        response_handoff_kind: str,
        codex_candidate_status: str,
        codex_candidate_kind: str,
        codex_permission: str,
        codex_prompt_source_status: str,
        codex_scope_status: str,
        codex_no_tests_policy: str,
        codex_token_posture: str,
        block_reason: str,
        receipt_status: str,
        receipt_kind: str,
        codex_candidate_compact: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        return {
            "project_browser_autonomous_result_assimilation_status": status,
            "project_browser_autonomous_result_assimilation_kind": kind,
            "project_browser_autonomous_browser_result_outcome": browser_result_outcome,
            "project_browser_autonomous_response_usability_status": response_usability_status,
            "project_browser_autonomous_response_handoff_status": response_handoff_status,
            "project_browser_autonomous_response_handoff_kind": response_handoff_kind,
            "project_browser_autonomous_codex_invocation_candidate_status": (
                codex_candidate_status
            ),
            "project_browser_autonomous_codex_invocation_candidate_kind": codex_candidate_kind,
            "project_browser_autonomous_codex_invocation_permission": codex_permission,
            "project_browser_autonomous_codex_invocation_prompt_source_status": (
                codex_prompt_source_status
            ),
            "project_browser_autonomous_codex_invocation_scope_status": codex_scope_status,
            "project_browser_autonomous_codex_invocation_no_tests_policy": (
                codex_no_tests_policy
            ),
            "project_browser_autonomous_codex_invocation_token_posture": (
                codex_token_posture
            ),
            "project_browser_autonomous_result_assimilation_block_reason": block_reason,
            "project_browser_autonomous_result_assimilation_receipt_status": receipt_status,
            "project_browser_autonomous_result_assimilation_receipt_kind": receipt_kind,
            "project_browser_autonomous_result_assimilation_runtime_posture": runtime_posture,
            "project_browser_autonomous_codex_invocation_candidate_compact": dict(
                codex_candidate_compact or {}
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
            kind="insufficient_truth_assimilation",
            browser_result_outcome="insufficient_truth",
            response_usability_status="insufficient_truth",
            response_handoff_status="insufficient_truth",
            response_handoff_kind="insufficient_truth_handoff",
            codex_candidate_status="insufficient_truth",
            codex_candidate_kind="insufficient_truth_candidate",
            codex_permission="insufficient_truth",
            codex_prompt_source_status="insufficient_truth",
            codex_scope_status="insufficient_truth",
            codex_no_tests_policy="insufficient_truth",
            codex_token_posture="insufficient_truth",
            block_reason=normalized_block_reason,
            receipt_status="insufficient_truth",
            receipt_kind="insufficient_truth_assimilation_receipt",
            codex_candidate_compact={},
        )

    def _map_execution_block_reason(value: str) -> str:
        if value in {"cooldown_required", "loop_suspected", "pause_required", "human_review_required"}:
            return value
        if value in {"response_empty", "response_too_large"}:
            return value
        if value in {"response_timeout"}:
            return "browser_timeout"
        if value == "insufficient_truth":
            return "insufficient_truth"
        if value == "source_inconsistent":
            return "source_inconsistent"
        return "browser_execution_blocked"

    if execution_status not in {
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
    if execution_source_status not in {"valid", "inconsistent", "insufficient_truth"}:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if execution_command_type not in {"none", "send_next_prompt", "retry_same_prompt", "insufficient_truth"}:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if execution_wait_status not in {
        "not_attempted",
        "completed",
        "timeout",
        "blocked",
        "failed",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if execution_read_status not in {
        "not_attempted",
        "read",
        "empty",
        "blocked",
        "failed",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if execution_text_status not in {
        "unavailable",
        "available",
        "empty",
        "too_large",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if execution_block_reason not in {
        "none",
        "enqueue_not_ready",
        "command_not_allowed",
        "prompt_source_missing",
        "prompt_empty",
        "prompt_too_large",
        "duplicate_prompt",
        "retry_budget_exhausted",
        "source_inconsistent",
        "cooldown_required",
        "loop_suspected",
        "login_interruption",
        "launch_failed",
        "page_open_failed",
        "selector_not_ready",
        "prompt_fill_failed",
        "send_failed",
        "response_timeout",
        "response_empty",
        "response_too_large",
        "browser_unavailable",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if execution_receipt_status not in {
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
    if enqueue_status not in {
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
    if enqueue_permission not in {
        "allowed_candidate",
        "blocked",
        "cooldown_required",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if enqueue_retry_budget_status not in {
        "not_applicable",
        "available",
        "exhausted",
        "blocked",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if adapter_status not in {
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
    if adapter_action not in {
        "none",
        "md_update_apply_candidate",
        "browser_prompt_enqueue_candidate",
        "browser_retry_enqueue_candidate",
        "codex_invocation_candidate",
        "stop",
        "cooldown",
        "pause_for_login",
        "human_review",
    }:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if adapter_risk_status not in {"low", "standard", "high", "blocked", "insufficient_truth"}:
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
    if retry_budget_posture not in _PROJECT_BROWSER_AUTONOMOUS_RETRY_BUDGET_POSTURES:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if response_json_parse_status not in _PROJECT_BROWSER_RESPONSE_JSON_PARSE_STATUSES:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if pr_queue_status not in _PROJECT_PR_QUEUE_STATUSES:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if normalized_implementation_prompt_status not in _IMPLEMENTATION_PROMPT_STATUSES:
        return _insufficient_truth_state(block_reason="insufficient_truth")

    remaining_steps, remaining_steps_invalid = _read_required_non_negative_int(
        multistep_state.get("project_browser_autonomous_multistep_remaining_steps")
    )
    remaining_failures, remaining_failures_invalid = _read_required_non_negative_int(
        multistep_state.get("project_browser_autonomous_multistep_remaining_failures")
    )
    if remaining_steps_invalid or remaining_failures_invalid:
        return _insufficient_truth_state(block_reason="insufficient_truth")

    if execution_source_status == "insufficient_truth":
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if execution_source_status == "inconsistent":
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if execution_status == "insufficient_truth" or execution_receipt_status == "insufficient_truth":
        return _insufficient_truth_state(block_reason="insufficient_truth")

    if execution_status == "inactive":
        return _base_state(
            status="inactive",
            kind="none",
            browser_result_outcome="none",
            response_usability_status="unavailable",
            response_handoff_status="not_created",
            response_handoff_kind="none",
            codex_candidate_status="not_created",
            codex_candidate_kind="none",
            codex_permission="blocked",
            codex_prompt_source_status="unavailable",
            codex_scope_status="unavailable",
            codex_no_tests_policy="unavailable",
            codex_token_posture="insufficient_truth",
            block_reason="none",
            receipt_status="not_created",
            receipt_kind="none",
            codex_candidate_compact={},
        )
    if execution_status == "blocked":
        mapped_reason = _map_execution_block_reason(execution_block_reason)
        return _base_state(
            status="blocked",
            kind="blocked_assimilation",
            browser_result_outcome="browser_blocked",
            response_usability_status="blocked",
            response_handoff_status="blocked",
            response_handoff_kind="blocked_handoff",
            codex_candidate_status="blocked",
            codex_candidate_kind="blocked_candidate",
            codex_permission="blocked",
            codex_prompt_source_status="unavailable",
            codex_scope_status="unavailable",
            codex_no_tests_policy="unavailable",
            codex_token_posture="insufficient_truth",
            block_reason=mapped_reason,
            receipt_status="blocked",
            receipt_kind="blocked_assimilation_receipt",
            codex_candidate_compact={},
        )
    if execution_status == "failed":
        return _base_state(
            status="failed",
            kind="failed_assimilation",
            browser_result_outcome="browser_failed",
            response_usability_status="blocked",
            response_handoff_status="failed",
            response_handoff_kind="blocked_handoff",
            codex_candidate_status="failed",
            codex_candidate_kind="blocked_candidate",
            codex_permission="blocked",
            codex_prompt_source_status="unavailable",
            codex_scope_status="unavailable",
            codex_no_tests_policy="unavailable",
            codex_token_posture="insufficient_truth",
            block_reason="browser_execution_failed",
            receipt_status="failed",
            receipt_kind="failed_assimilation_receipt",
            codex_candidate_compact={},
        )
    if execution_status == "cooldown_required":
        return _base_state(
            status="cooldown_required",
            kind="cooldown_assimilation",
            browser_result_outcome="browser_blocked",
            response_usability_status="blocked",
            response_handoff_status="blocked",
            response_handoff_kind="blocked_handoff",
            codex_candidate_status="blocked",
            codex_candidate_kind="blocked_candidate",
            codex_permission="blocked",
            codex_prompt_source_status="unavailable",
            codex_scope_status="unavailable",
            codex_no_tests_policy="unavailable",
            codex_token_posture="insufficient_truth",
            block_reason="cooldown_required",
            receipt_status="blocked",
            receipt_kind="blocked_assimilation_receipt",
            codex_candidate_compact={},
        )
    if execution_status == "pause_required":
        return _base_state(
            status="pause_required",
            kind="pause_assimilation",
            browser_result_outcome="login_interruption",
            response_usability_status="blocked",
            response_handoff_status="pause_required",
            response_handoff_kind="pause_handoff",
            codex_candidate_status="pause_required",
            codex_candidate_kind="pause_candidate",
            codex_permission="pause_required",
            codex_prompt_source_status="unavailable",
            codex_scope_status="unavailable",
            codex_no_tests_policy="unavailable",
            codex_token_posture="insufficient_truth",
            block_reason="pause_required",
            receipt_status="pause_required",
            receipt_kind="pause_assimilation_receipt",
            codex_candidate_compact={},
        )
    if execution_status == "human_review_required":
        return _base_state(
            status="human_review_required",
            kind="human_review_assimilation",
            browser_result_outcome="browser_blocked",
            response_usability_status="blocked",
            response_handoff_status="human_review_required",
            response_handoff_kind="human_review_handoff",
            codex_candidate_status="human_review_required",
            codex_candidate_kind="human_review_candidate",
            codex_permission="human_review_required",
            codex_prompt_source_status="unavailable",
            codex_scope_status="unavailable",
            codex_no_tests_policy="unavailable",
            codex_token_posture="insufficient_truth",
            block_reason="human_review_required",
            receipt_status="human_review_required",
            receipt_kind="human_review_assimilation_receipt",
            codex_candidate_compact={},
        )
    if execution_status == "timeout":
        retry_candidate_allowed = bool(
            retry_budget_posture == "available"
            and enqueue_retry_budget_status == "available"
            and cooldown_status == "not_required"
            and loop_risk_status == "clear"
            and adapter_risk_status == "standard"
            and adapter_status == "execution_ready_candidate"
            and adapter_action in {
                "browser_prompt_enqueue_candidate",
                "browser_retry_enqueue_candidate",
            }
        )
        candidate_kind = (
            "retry_browser_prompt_candidate"
            if retry_candidate_allowed
            else "timeout_candidate"
        )
        receipt_kind = (
            "retry_browser_candidate_receipt"
            if retry_candidate_allowed
            else "timeout_assimilation_receipt"
        )
        return _base_state(
            status="timeout",
            kind="timeout_assimilation",
            browser_result_outcome="response_timeout",
            response_usability_status="unavailable",
            response_handoff_status="timeout",
            response_handoff_kind="timeout_handoff",
            codex_candidate_status="timeout",
            codex_candidate_kind=candidate_kind,
            codex_permission="timeout",
            codex_prompt_source_status="unavailable",
            codex_scope_status="unavailable",
            codex_no_tests_policy="enforced",
            codex_token_posture="compact",
            block_reason="browser_timeout",
            receipt_status="timeout",
            receipt_kind=receipt_kind,
            codex_candidate_compact={
                "candidate_kind": candidate_kind,
                "execution_command_type": execution_command_type,
                "retry_budget_posture": retry_budget_posture,
                "candidate_only": True,
                "execution_performed": False,
            },
        )

    if execution_status != "executed":
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if execution_receipt_status != "ready":
        return _base_state(
            status="blocked",
            kind="blocked_assimilation",
            browser_result_outcome="browser_blocked",
            response_usability_status="blocked",
            response_handoff_status="blocked",
            response_handoff_kind="blocked_handoff",
            codex_candidate_status="blocked",
            codex_candidate_kind="blocked_candidate",
            codex_permission="blocked",
            codex_prompt_source_status="unavailable",
            codex_scope_status="unavailable",
            codex_no_tests_policy="unavailable",
            codex_token_posture="insufficient_truth",
            block_reason="browser_receipt_not_ready",
            receipt_status="blocked",
            receipt_kind="blocked_assimilation_receipt",
            codex_candidate_compact={},
        )

    source_conflict = False
    if enqueue_status != "prepared":
        source_conflict = True
    if enqueue_permission != "allowed_candidate":
        source_conflict = True
    if adapter_status != "execution_ready_candidate":
        source_conflict = True
    if adapter_action not in {"browser_prompt_enqueue_candidate", "browser_retry_enqueue_candidate"}:
        source_conflict = True
    if adapter_risk_status != "standard":
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
    if multistep_budget_status != "ready" or multistep_permission != "allowed_candidate":
        source_conflict = True
    if remaining_steps <= 0:
        source_conflict = True
    if remaining_failures <= 0:
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

    browser_result_outcome = "insufficient_truth"
    response_usability_status = "insufficient_truth"
    result_block_reason = "insufficient_truth"
    if execution_wait_status == "timeout":
        browser_result_outcome = "response_timeout"
        response_usability_status = "unavailable"
        result_block_reason = "browser_timeout"
    elif execution_read_status == "empty" or execution_text_status == "empty":
        browser_result_outcome = "response_empty"
        response_usability_status = "empty"
        result_block_reason = "response_empty"
    elif execution_text_status == "too_large":
        browser_result_outcome = "response_too_large"
        if response_json_parse_status == "valid":
            response_usability_status = "usable"
            result_block_reason = "none"
        else:
            response_usability_status = "too_large"
            result_block_reason = "response_too_large"
    elif execution_read_status == "read" and execution_text_status == "available":
        browser_result_outcome = "response_read"
        if response_json_parse_status == "invalid_response":
            response_usability_status = "invalid_response"
            result_block_reason = "response_unusable"
        else:
            response_usability_status = "usable"
            result_block_reason = "none"
    elif execution_read_status == "read" and execution_text_status == "insufficient_truth":
        browser_result_outcome = "insufficient_truth"
        response_usability_status = "insufficient_truth"
        result_block_reason = "insufficient_truth"
    elif execution_read_status in {"blocked", "failed"} or execution_wait_status in {"blocked", "failed"}:
        browser_result_outcome = "browser_failed"
        response_usability_status = "blocked"
        result_block_reason = "browser_execution_failed"
    else:
        browser_result_outcome = "insufficient_truth"
        response_usability_status = "insufficient_truth"
        result_block_reason = "insufficient_truth"

    if response_usability_status == "insufficient_truth":
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if browser_result_outcome == "response_timeout":
        return _base_state(
            status="timeout",
            kind="timeout_assimilation",
            browser_result_outcome=browser_result_outcome,
            response_usability_status=response_usability_status,
            response_handoff_status="timeout",
            response_handoff_kind="timeout_handoff",
            codex_candidate_status="timeout",
            codex_candidate_kind="timeout_candidate",
            codex_permission="timeout",
            codex_prompt_source_status="unavailable",
            codex_scope_status="unavailable",
            codex_no_tests_policy="enforced",
            codex_token_posture="compact",
            block_reason="browser_timeout",
            receipt_status="timeout",
            receipt_kind="timeout_assimilation_receipt",
            codex_candidate_compact={
                "candidate_kind": "timeout_candidate",
                "execution_command_type": execution_command_type,
                "candidate_only": True,
                "execution_performed": False,
            },
        )

    handoff_payload = queue_handoff_payload
    implementation_payload = (
        dict(handoff_payload.get("implementation_prompt_payload"))
        if isinstance(handoff_payload.get("implementation_prompt_payload"), Mapping)
        else {}
    )
    structured_prompt_available = bool(
        pr_queue_status == "prepared"
        and queue_handoff_prepared
        and normalized_implementation_prompt_status == "available"
        and normalized_implementation_prompt_available
        and implementation_payload
        and bool(implementation_payload.get("prompt_available", False))
    )
    prompt_source_status = "available" if structured_prompt_available else "unavailable"
    if not structured_prompt_available and implementation_payload:
        prompt_source_status = (
            "empty" if not bool(implementation_payload.get("prompt_available", False)) else "unavailable"
        )
    if response_usability_status == "invalid_response":
        prompt_source_status = "invalid_response"
    elif response_usability_status == "too_large" and response_json_parse_status != "valid":
        prompt_source_status = "too_large"

    bounded_scope_class = _normalize_text(
        implementation_payload.get("bounded_scope_class"),
        default="unknown",
    )
    preferred_files = [
        _normalize_text(path, default="")
        for path in implementation_payload.get("preferred_files", [])
        if isinstance(path, str)
    ]
    allowed_scope_roots = ("automation/orchestration/", "prompts/context/")
    scope_status = "unavailable"
    if adapter_risk_status in {"high", "blocked"}:
        scope_status = "high_risk"
    elif structured_prompt_available:
        if not preferred_files:
            scope_status = "unavailable"
        elif any(
            path
            and not path.startswith(allowed_scope_roots)
            and not path.startswith("tests/")
            for path in preferred_files
        ):
            scope_status = "too_broad"
        elif len(preferred_files) > 5 or bounded_scope_class in {"unknown", "insufficient_truth"}:
            scope_status = "too_broad"
        else:
            scope_status = "bounded"

    no_tests_policy = (
        "enforced"
        if prompt_source_status in {"available", "empty", "too_large", "invalid_response"}
        else "unavailable"
    )
    token_posture = "insufficient_truth"
    candidate_compact: dict[str, Any] = {}
    if structured_prompt_available:
        candidate_compact = {
            "candidate_only": True,
            "execution_performed": False,
            "slice_id": _normalize_text(handoff_payload.get("slice_id"), default=""),
            "roadmap_item_id": _normalize_text(handoff_payload.get("roadmap_item_id"), default=""),
            "bounded_scope_class": bounded_scope_class,
            "preferred_files": preferred_files[:5],
            "browser_execution_command_type": execution_command_type,
            "browser_result_outcome": browser_result_outcome,
            "no_tests_policy": "enforced",
        }
        serialized_len = len(json.dumps(candidate_compact, ensure_ascii=False))
        token_posture = "compact" if serialized_len <= 4000 else "too_large"
    elif prompt_source_status in {"unavailable", "empty"}:
        token_posture = "insufficient_truth"
    else:
        token_posture = "too_large"

    if response_usability_status == "empty":
        return _base_state(
            status="blocked",
            kind="blocked_assimilation",
            browser_result_outcome="response_empty",
            response_usability_status="empty",
            response_handoff_status="blocked",
            response_handoff_kind="blocked_handoff",
            codex_candidate_status="blocked",
            codex_candidate_kind="blocked_candidate",
            codex_permission="blocked",
            codex_prompt_source_status="empty",
            codex_scope_status="unavailable",
            codex_no_tests_policy=no_tests_policy,
            codex_token_posture=token_posture,
            block_reason="response_empty",
            receipt_status="blocked",
            receipt_kind="blocked_assimilation_receipt",
            codex_candidate_compact={},
        )
    if response_usability_status == "too_large":
        return _base_state(
            status="blocked",
            kind="blocked_assimilation",
            browser_result_outcome="response_too_large",
            response_usability_status="too_large",
            response_handoff_status="blocked",
            response_handoff_kind="blocked_handoff",
            codex_candidate_status="blocked",
            codex_candidate_kind="blocked_candidate",
            codex_permission="blocked",
            codex_prompt_source_status="too_large",
            codex_scope_status=scope_status,
            codex_no_tests_policy=no_tests_policy,
            codex_token_posture=token_posture,
            block_reason="response_too_large",
            receipt_status="blocked",
            receipt_kind="blocked_assimilation_receipt",
            codex_candidate_compact={},
        )
    if response_usability_status == "invalid_response":
        return _base_state(
            status="blocked",
            kind="blocked_assimilation",
            browser_result_outcome=browser_result_outcome,
            response_usability_status="invalid_response",
            response_handoff_status="blocked",
            response_handoff_kind="blocked_handoff",
            codex_candidate_status="blocked",
            codex_candidate_kind="blocked_candidate",
            codex_permission="blocked",
            codex_prompt_source_status="invalid_response",
            codex_scope_status="unavailable",
            codex_no_tests_policy=no_tests_policy,
            codex_token_posture="insufficient_truth",
            block_reason="response_unusable",
            receipt_status="blocked",
            receipt_kind="blocked_assimilation_receipt",
            codex_candidate_compact={},
        )

    if prompt_source_status == "unavailable":
        return _base_state(
            status="blocked",
            kind="blocked_assimilation",
            browser_result_outcome=browser_result_outcome,
            response_usability_status=response_usability_status,
            response_handoff_status="blocked",
            response_handoff_kind="blocked_handoff",
            codex_candidate_status="blocked",
            codex_candidate_kind="blocked_candidate",
            codex_permission="blocked",
            codex_prompt_source_status="unavailable",
            codex_scope_status="unavailable",
            codex_no_tests_policy=no_tests_policy,
            codex_token_posture=token_posture,
            block_reason="codex_prompt_missing",
            receipt_status="blocked",
            receipt_kind="blocked_assimilation_receipt",
            codex_candidate_compact={},
        )
    if prompt_source_status == "empty":
        return _base_state(
            status="blocked",
            kind="blocked_assimilation",
            browser_result_outcome=browser_result_outcome,
            response_usability_status=response_usability_status,
            response_handoff_status="blocked",
            response_handoff_kind="blocked_handoff",
            codex_candidate_status="blocked",
            codex_candidate_kind="blocked_candidate",
            codex_permission="blocked",
            codex_prompt_source_status="empty",
            codex_scope_status=scope_status,
            codex_no_tests_policy=no_tests_policy,
            codex_token_posture=token_posture,
            block_reason="codex_prompt_empty",
            receipt_status="blocked",
            receipt_kind="blocked_assimilation_receipt",
            codex_candidate_compact={},
        )
    if scope_status == "high_risk":
        return _base_state(
            status="human_review_required",
            kind="human_review_assimilation",
            browser_result_outcome=browser_result_outcome,
            response_usability_status=response_usability_status,
            response_handoff_status="human_review_required",
            response_handoff_kind="human_review_handoff",
            codex_candidate_status="human_review_required",
            codex_candidate_kind="human_review_candidate",
            codex_permission="human_review_required",
            codex_prompt_source_status=prompt_source_status,
            codex_scope_status="high_risk",
            codex_no_tests_policy=no_tests_policy,
            codex_token_posture=token_posture,
            block_reason="high_risk_action",
            receipt_status="human_review_required",
            receipt_kind="human_review_assimilation_receipt",
            codex_candidate_compact={},
        )
    if scope_status == "too_broad":
        return _base_state(
            status="blocked",
            kind="blocked_assimilation",
            browser_result_outcome=browser_result_outcome,
            response_usability_status=response_usability_status,
            response_handoff_status="blocked",
            response_handoff_kind="blocked_handoff",
            codex_candidate_status="blocked",
            codex_candidate_kind="blocked_candidate",
            codex_permission="blocked",
            codex_prompt_source_status=prompt_source_status,
            codex_scope_status="too_broad",
            codex_no_tests_policy=no_tests_policy,
            codex_token_posture=token_posture,
            block_reason="codex_scope_too_broad",
            receipt_status="blocked",
            receipt_kind="blocked_assimilation_receipt",
            codex_candidate_compact={},
        )
    if token_posture == "too_large":
        return _base_state(
            status="blocked",
            kind="blocked_assimilation",
            browser_result_outcome=browser_result_outcome,
            response_usability_status=response_usability_status,
            response_handoff_status="blocked",
            response_handoff_kind="blocked_handoff",
            codex_candidate_status="blocked",
            codex_candidate_kind="blocked_candidate",
            codex_permission="blocked",
            codex_prompt_source_status=prompt_source_status,
            codex_scope_status=scope_status,
            codex_no_tests_policy=no_tests_policy,
            codex_token_posture="too_large",
            block_reason="codex_prompt_too_large",
            receipt_status="blocked",
            receipt_kind="blocked_assimilation_receipt",
            codex_candidate_compact={},
        )
    if no_tests_policy != "enforced":
        return _base_state(
            status="blocked",
            kind="blocked_assimilation",
            browser_result_outcome=browser_result_outcome,
            response_usability_status=response_usability_status,
            response_handoff_status="blocked",
            response_handoff_kind="blocked_handoff",
            codex_candidate_status="blocked",
            codex_candidate_kind="blocked_candidate",
            codex_permission="blocked",
            codex_prompt_source_status=prompt_source_status,
            codex_scope_status=scope_status,
            codex_no_tests_policy=no_tests_policy,
            codex_token_posture=token_posture,
            block_reason="source_inconsistent",
            receipt_status="blocked",
            receipt_kind="blocked_assimilation_receipt",
            codex_candidate_compact={},
        )

    return _base_state(
        status="assimilated",
        kind="browser_result_assimilation",
        browser_result_outcome=browser_result_outcome,
        response_usability_status="usable",
        response_handoff_status="ready",
        response_handoff_kind="implementation_prompt_handoff",
        codex_candidate_status="ready",
        codex_candidate_kind="one_codex_invocation_candidate",
        codex_permission="allowed_candidate",
        codex_prompt_source_status="available",
        codex_scope_status="bounded",
        codex_no_tests_policy="enforced",
        codex_token_posture="compact",
        block_reason="none",
        receipt_status="ready",
        receipt_kind="codex_invocation_candidate_receipt",
        codex_candidate_compact=candidate_compact,
    )

def _build_project_browser_autonomous_reentry_result_assimilation_state(
    *,
    reentry_routing_status: str,
    reentry_routing_allowed: bool,
    reentry_routing_block_reason: str,
    reentry_status: str,
    reentry_invocation_allowed: bool,
    reentry_invocation_attempted: bool,
    reentry_invocation_completed: bool,
    reentry_invocation_block_reason: str,
    reentry_prompt_kind: str,
    reentry_prompt_path: str,
    reentry_result_class: str,
    reentry_changed_files: list[str] | None,
    reentry_changed_files_count: int,
    reentry_stdout_path: str,
    reentry_stderr_path: str,
    reentry_result_path: str,
    reentry_git_diff_name_only_path: str,
    reentry_git_diff_numstat_path: str,
    reentry_exit_code: int,
    reentry_timed_out: bool,
    reentry_result_ready_for_assimilation: bool,
    reentry_result_assimilation_source: str,
    reentry_result_next_stage: str,
    reentry_human_review_required: bool,
    reentry_next_action: str,
    normal_write_execution_status: str,
    normal_write_result_status: str,
    normal_write_attempted: bool,
    normal_write_completed: bool,
    normal_write_prompt_kind: str,
    normal_write_prompt_path: str,
    normal_write_changed_files: list[str] | None,
    normal_write_changed_files_count: int,
    normal_write_stdout_path: str,
    normal_write_stderr_path: str,
    normal_write_result_path: str,
    normal_write_git_diff_name_only_path: str,
    normal_write_git_diff_numstat_path: str,
    normal_write_human_review_required: bool,
    fix_target_files: list[str] | None,
    next_target_files: list[str] | None,
    smoke_override_used: bool,
) -> dict[str, Any]:
    allowed_statuses = {
        "reentry_assimilation_completed_with_changes",
        "reentry_assimilation_completed_no_changes",
        "reentry_assimilation_completed_failure",
        "reentry_assimilation_completed_timeout",
        "blocked_reentry_invocation_not_ready",
        "blocked_ambiguous_write_sources",
        "blocked_human_review_required",
        "blocked_insufficient_assimilation_truth",
        "blocked_source_paths_unsafe",
        "blocked_forbidden_changed_files",
        "blocked_unexpected_changed_files",
        "blocked_too_many_changed_files",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "route_reentry_result_to_validation",
        "manual_review_required",
        "generate_fix_prompt",
        "wait_for_more_truth",
        "insufficient_truth",
    }
    allowed_prompt_paths = {
        "/tmp/codex-local-runner-decision/generated_fix_prompt.txt",
        "/tmp/codex-local-runner-decision/generated_next_prompt.txt",
    }
    allowed_artifact_paths = {
        "/tmp/codex-local-runner-decision/codex_write_invocation_stdout.txt",
        "/tmp/codex-local-runner-decision/codex_write_invocation_stderr.txt",
        "/tmp/codex-local-runner-decision/codex_write_invocation_result.json",
        "/tmp/codex-local-runner-decision/codex_write_git_diff_name_only.txt",
        "/tmp/codex-local-runner-decision/codex_write_git_diff_numstat.txt",
    }
    max_changed_files_threshold = 8
    runtime_posture = [
        "prompt181_reentry_result_assimilation",
        "authoritative_source_precedence",
        "no_source_merging",
        "metadata_only_routing",
        "no_codex_invocation",
        "no_validation_execution",
        "no_git_mutation",
    ]

    normalized_reentry_routing_status = _normalize_text(
        reentry_routing_status,
        default="insufficient_truth",
    )
    reentry_routing_active = bool(
        normalized_reentry_routing_status
        and normalized_reentry_routing_status != "insufficient_truth"
    )
    normalized_reentry_status = _normalize_text(reentry_status, default="insufficient_truth")
    normalized_reentry_result_class = _normalize_text(
        reentry_result_class,
        default="blocked",
    )
    normalized_reentry_prompt_kind = _normalize_text(reentry_prompt_kind, default="none")
    normalized_reentry_prompt_path = _normalize_text(reentry_prompt_path, default="")
    normalized_reentry_stdout_path = _normalize_text(reentry_stdout_path, default="")
    normalized_reentry_stderr_path = _normalize_text(reentry_stderr_path, default="")
    normalized_reentry_result_path = _normalize_text(reentry_result_path, default="")
    normalized_reentry_diff_name_only_path = _normalize_text(
        reentry_git_diff_name_only_path,
        default="",
    )
    normalized_reentry_diff_numstat_path = _normalize_text(
        reentry_git_diff_numstat_path,
        default="",
    )
    normalized_normal_write_result_status = _normalize_text(
        normal_write_result_status,
        default="insufficient_truth",
    )
    normalized_normal_write_prompt_kind = _normalize_text(
        normal_write_prompt_kind,
        default="none",
    )
    normalized_normal_write_prompt_path = _normalize_text(normal_write_prompt_path, default="")
    normalized_normal_write_stdout_path = _normalize_text(normal_write_stdout_path, default="")
    normalized_normal_write_stderr_path = _normalize_text(normal_write_stderr_path, default="")
    normalized_normal_write_result_path = _normalize_text(normal_write_result_path, default="")
    normalized_normal_write_diff_name_only_path = _normalize_text(
        normal_write_git_diff_name_only_path,
        default="",
    )
    normalized_normal_write_diff_numstat_path = _normalize_text(
        normal_write_git_diff_numstat_path,
        default="",
    )
    normalized_reentry_changed_files = _normalize_string_list(reentry_changed_files or [])
    normalized_normal_changed_files = _normalize_string_list(normal_write_changed_files or [])
    normalized_reentry_changed_files_count = _as_non_negative_int(
        reentry_changed_files_count,
        default=len(normalized_reentry_changed_files),
    )
    normalized_normal_changed_files_count = _as_non_negative_int(
        normal_write_changed_files_count,
        default=len(normalized_normal_changed_files),
    )
    normalized_reentry_routing_block_reason = _normalize_text(
        reentry_routing_block_reason,
        default="",
    )
    normalized_reentry_invocation_block_reason = _normalize_text(
        reentry_invocation_block_reason,
        default="",
    )

    def _has_parent_traversal(path_text: str) -> bool:
        path_obj = PurePosixPath(path_text.replace("\\", "/"))
        return ".." in path_obj.parts

    def _validate_prompt_path(path_text: str) -> tuple[bool, str]:
        normalized_path = _normalize_text(path_text, default="")
        if not normalized_path:
            return False, "blocked_prompt_path_missing"
        if _has_parent_traversal(normalized_path):
            return False, "blocked_prompt_path_unexpected"
        if normalized_path not in allowed_prompt_paths:
            return False, "blocked_prompt_path_unexpected"
        path_obj = Path(normalized_path)
        if path_obj.is_symlink():
            return False, "blocked_prompt_path_symlink"
        if not path_obj.exists():
            return False, "blocked_prompt_path_missing"
        if not path_obj.is_file():
            return False, "blocked_prompt_path_not_file"
        try:
            size_bytes = _as_non_negative_int(path_obj.stat().st_size, default=0)
        except OSError:
            return False, "blocked_prompt_path_unreadable"
        if size_bytes <= 0:
            return False, "blocked_prompt_empty"
        if size_bytes > 20000:
            return False, "blocked_prompt_too_large"
        return True, ""

    def _validate_artifact_path(path_text: str) -> tuple[bool, str]:
        normalized_path = _normalize_text(path_text, default="")
        if not normalized_path:
            return False, "blocked_required_path_missing"
        if _has_parent_traversal(normalized_path):
            return False, "blocked_required_path_unexpected"
        if normalized_path not in allowed_artifact_paths:
            return False, "blocked_required_path_unexpected"
        path_obj = Path(normalized_path)
        if path_obj.is_symlink():
            return False, "blocked_required_path_symlink"
        if not path_obj.exists():
            return False, "blocked_required_path_missing"
        if not path_obj.is_file():
            return False, "blocked_required_path_not_file"
        return True, ""

    def _read_changed_files_from_diff(
        diff_name_only_path: str,
        diff_numstat_path: str,
    ) -> list[str]:
        normalized_name = _normalize_text(diff_name_only_path, default="")
        normalized_numstat = _normalize_text(diff_numstat_path, default="")
        changed_from_name: list[str] = []
        changed_from_numstat: list[str] = []
        if normalized_name in allowed_artifact_paths:
            name_path = Path(normalized_name)
            if name_path.exists() and not name_path.is_symlink():
                try:
                    changed_from_name = _serialize_required_signals(
                        name_path.read_text(encoding="utf-8").splitlines()
                    )
                except OSError:
                    changed_from_name = []
        if normalized_numstat in allowed_artifact_paths:
            num_path = Path(normalized_numstat)
            if num_path.exists() and not num_path.is_symlink():
                try:
                    for line in num_path.read_text(encoding="utf-8").splitlines():
                        parts = line.split("\t")
                        if len(parts) >= 3:
                            changed_from_numstat.append(parts[-1].strip())
                except OSError:
                    changed_from_numstat = []
        return (
            changed_from_name
            if changed_from_name
            else _serialize_required_signals(changed_from_numstat)
        )

    reentry_source_available = bool(
        reentry_invocation_attempted
        or reentry_invocation_completed
        or reentry_result_ready_for_assimilation
        or normalized_reentry_status
        in {
            "reentry_invocation_completed_with_changes",
            "reentry_invocation_completed_no_changes",
            "reentry_invocation_completed_failure",
            "reentry_invocation_completed_timeout",
        }
    )
    normal_write_source_available = bool(
        normal_write_attempted
        or normal_write_completed
        or normalized_normal_write_result_status
        in {
            "completed_with_changes",
            "completed_no_changes",
            "completed_failure",
            "completed_timeout",
        }
    )
    ambiguous_write_sources = bool(
        reentry_source_available
        and normal_write_source_available
        and not bool(reentry_result_ready_for_assimilation)
    )

    authoritative_source_kind = "none"
    authoritative_source_selected = False
    authoritative_source_block_reason = "blocked_insufficient_assimilation_truth"

    if bool(reentry_result_ready_for_assimilation):
        authoritative_source_kind = "reentry"
        authoritative_source_selected = True
        authoritative_source_block_reason = ""
    elif ambiguous_write_sources:
        authoritative_source_kind = "none"
        authoritative_source_selected = False
        authoritative_source_block_reason = "blocked_ambiguous_write_sources"
    elif reentry_routing_active:
        authoritative_source_kind = "none"
        authoritative_source_selected = False
        authoritative_source_block_reason = "blocked_reentry_invocation_not_ready"
    elif normal_write_source_available:
        authoritative_source_kind = "normal_write"
        authoritative_source_selected = True
        authoritative_source_block_reason = ""

    source_status = ""
    source_result_class = "blocked"
    source_prompt_kind = "none"
    source_prompt_path = ""
    source_stdout_path = ""
    source_stderr_path = ""
    source_result_path = ""
    source_git_diff_name_only_path = ""
    source_git_diff_numstat_path = ""
    source_changed_files: list[str] = []
    source_changed_files_count = 0
    selected_source_human_review_required = False
    selected_source_timed_out = False

    if authoritative_source_kind == "reentry":
        source_status = normalized_reentry_status
        source_result_class = normalized_reentry_result_class
        source_prompt_kind = normalized_reentry_prompt_kind
        source_prompt_path = normalized_reentry_prompt_path
        source_stdout_path = normalized_reentry_stdout_path
        source_stderr_path = normalized_reentry_stderr_path
        source_result_path = normalized_reentry_result_path
        source_git_diff_name_only_path = normalized_reentry_diff_name_only_path
        source_git_diff_numstat_path = normalized_reentry_diff_numstat_path
        source_changed_files = list(normalized_reentry_changed_files)
        source_changed_files_count = normalized_reentry_changed_files_count
        selected_source_human_review_required = bool(reentry_human_review_required)
        selected_source_timed_out = bool(reentry_timed_out)
    elif authoritative_source_kind == "normal_write":
        source_status = normalized_normal_write_result_status
        if normalized_normal_write_result_status == "completed_with_changes":
            source_result_class = "completed_with_changes"
        elif normalized_normal_write_result_status == "completed_no_changes":
            source_result_class = "completed_no_changes"
        elif normalized_normal_write_result_status == "completed_failure":
            source_result_class = "completed_failure"
        elif normalized_normal_write_result_status == "completed_timeout":
            source_result_class = "completed_timeout"
        else:
            source_result_class = "blocked"
        source_prompt_kind = normalized_normal_write_prompt_kind
        source_prompt_path = normalized_normal_write_prompt_path
        source_stdout_path = normalized_normal_write_stdout_path
        source_stderr_path = normalized_normal_write_stderr_path
        source_result_path = normalized_normal_write_result_path
        source_git_diff_name_only_path = normalized_normal_write_diff_name_only_path
        source_git_diff_numstat_path = normalized_normal_write_diff_numstat_path
        source_changed_files = list(normalized_normal_changed_files)
        source_changed_files_count = normalized_normal_changed_files_count
        selected_source_human_review_required = bool(normal_write_human_review_required)
        selected_source_timed_out = bool(
            normalized_normal_write_result_status == "completed_timeout"
        )

    if not source_changed_files and authoritative_source_selected:
        source_changed_files = _read_changed_files_from_diff(
            source_git_diff_name_only_path,
            source_git_diff_numstat_path,
        )
        source_changed_files_count = max(source_changed_files_count, len(source_changed_files))

    expected_changed_files: list[str] = []
    normalized_fix_targets = _normalize_string_list(fix_target_files or [])
    normalized_next_targets = _normalize_string_list(next_target_files or [])
    if source_prompt_kind == "fix":
        expected_changed_files = list(normalized_fix_targets)
    elif source_prompt_kind == "next":
        expected_changed_files = list(normalized_next_targets)
    else:
        expected_changed_files = _serialize_required_signals(
            [*normalized_fix_targets, *normalized_next_targets]
        )
    if bool(smoke_override_used):
        expected_changed_files = _serialize_required_signals(
            [*expected_changed_files, "prompt167_workspace_write_smoke.txt"]
        )
    allowed_changed_files = list(expected_changed_files)
    allowed_changed_set = set(allowed_changed_files)

    def _is_forbidden_changed_file(path_text: str) -> bool:
        normalized_path = _normalize_text(path_text, default="").replace("\\", "/")
        if not normalized_path:
            return False
        lowered = normalized_path.lower()
        if normalized_path.startswith("/") or normalized_path.startswith("../"):
            return True
        if normalized_path.startswith(".git/"):
            return True
        if normalized_path.startswith("prompts/context/") and normalized_path not in allowed_changed_set:
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
        [path for path in source_changed_files if _is_forbidden_changed_file(path)]
    )
    unexpected_changed_files = _serialize_required_signals(
        [
            path
            for path in source_changed_files
            if path not in allowed_changed_set and path not in set(forbidden_changed_files)
        ]
    )
    too_many_changed_files = bool(source_changed_files_count > max_changed_files_threshold)

    safe_for_validation_routing = False
    validation_routing_candidate = False
    validation_routing_block_reason = "blocked_assimilation_not_safe"
    status = "blocked_insufficient_assimilation_truth"
    next_action = "manual_review_required"
    human_review_required = True
    reentry_assimilation_completed = False
    reentry_assimilation_failed = False
    missing_inputs: list[str] = []

    if selected_source_human_review_required:
        status = "blocked_human_review_required"
        human_review_required = True
        next_action = "manual_review_required"
        validation_routing_block_reason = "blocked_human_review_required"
    elif authoritative_source_block_reason == "blocked_ambiguous_write_sources":
        status = "blocked_ambiguous_write_sources"
        human_review_required = True
        next_action = "manual_review_required"
        validation_routing_block_reason = "blocked_not_completed"
    elif authoritative_source_block_reason == "blocked_reentry_invocation_not_ready":
        status = "blocked_reentry_invocation_not_ready"
        human_review_required = True
        next_action = "manual_review_required"
        validation_routing_block_reason = "blocked_not_completed"
    elif not authoritative_source_selected:
        status = "blocked_insufficient_assimilation_truth"
        human_review_required = True
        next_action = "manual_review_required"
        validation_routing_block_reason = "blocked_insufficient_truth"
        missing_inputs.append("authoritative_write_source")
    else:
        prompt_ok, prompt_reason = _validate_prompt_path(source_prompt_path)
        stdout_ok, stdout_reason = _validate_artifact_path(source_stdout_path)
        stderr_ok, stderr_reason = _validate_artifact_path(source_stderr_path)
        result_ok, result_reason = _validate_artifact_path(source_result_path)
        diff_name_ok, diff_name_reason = _validate_artifact_path(
            source_git_diff_name_only_path
        )
        diff_num_ok, diff_num_reason = _validate_artifact_path(
            source_git_diff_numstat_path
        )
        if not (
            prompt_ok
            and stdout_ok
            and stderr_ok
            and result_ok
            and diff_name_ok
            and diff_num_ok
        ):
            status = "blocked_source_paths_unsafe"
            human_review_required = True
            next_action = "manual_review_required"
            validation_routing_block_reason = "blocked_insufficient_truth"
            for reason in [
                prompt_reason,
                stdout_reason,
                stderr_reason,
                result_reason,
                diff_name_reason,
                diff_num_reason,
            ]:
                if reason:
                    missing_inputs.append(reason)
        elif source_result_class == "completed_timeout" or selected_source_timed_out:
            status = "reentry_assimilation_completed_timeout"
            human_review_required = True
            next_action = "manual_review_required"
            reentry_assimilation_completed = True
            reentry_assimilation_failed = True
            validation_routing_block_reason = "blocked_reentry_invocation_timeout"
        elif source_result_class == "completed_failure":
            status = "reentry_assimilation_completed_failure"
            human_review_required = False
            next_action = "generate_fix_prompt"
            reentry_assimilation_completed = True
            reentry_assimilation_failed = True
            validation_routing_block_reason = "blocked_reentry_invocation_failure"
        elif source_result_class == "completed_no_changes":
            status = "reentry_assimilation_completed_no_changes"
            human_review_required = True
            next_action = "manual_review_required"
            reentry_assimilation_completed = True
            reentry_assimilation_failed = False
            validation_routing_block_reason = "blocked_no_changed_files"
        elif source_result_class == "completed_with_changes":
            reentry_assimilation_completed = True
            if forbidden_changed_files:
                status = "blocked_forbidden_changed_files"
                human_review_required = True
                next_action = "manual_review_required"
                reentry_assimilation_failed = True
                validation_routing_block_reason = "blocked_forbidden_changed_files"
            elif unexpected_changed_files:
                status = "blocked_unexpected_changed_files"
                human_review_required = True
                next_action = "manual_review_required"
                reentry_assimilation_failed = True
                validation_routing_block_reason = "blocked_unexpected_changed_files"
            elif too_many_changed_files:
                status = "blocked_too_many_changed_files"
                human_review_required = True
                next_action = "manual_review_required"
                reentry_assimilation_failed = True
                validation_routing_block_reason = "blocked_too_many_changed_files"
            elif not source_changed_files:
                status = "reentry_assimilation_completed_no_changes"
                human_review_required = True
                next_action = "manual_review_required"
                reentry_assimilation_failed = False
                validation_routing_block_reason = "blocked_no_changed_files"
            else:
                status = "reentry_assimilation_completed_with_changes"
                human_review_required = False
                next_action = "route_reentry_result_to_validation"
                reentry_assimilation_failed = False
                safe_for_validation_routing = True
                validation_routing_candidate = True
                validation_routing_block_reason = ""
        else:
            status = "blocked_insufficient_assimilation_truth"
            human_review_required = True
            next_action = "manual_review_required"
            reentry_assimilation_failed = False
            validation_routing_block_reason = "blocked_insufficient_truth"
            missing_inputs.append("source_result_class")

    prompt170_compat_source_status = source_status if source_status else status
    prompt170_compat_result_class = "blocked"
    if safe_for_validation_routing:
        prompt170_compat_result_class = "expected_changes"
    elif status == "reentry_assimilation_completed_no_changes":
        prompt170_compat_result_class = "no_changes"
    elif status == "blocked_unexpected_changed_files":
        prompt170_compat_result_class = "unexpected_changes"
    elif status == "blocked_forbidden_changed_files":
        prompt170_compat_result_class = "forbidden_changes"
    elif status == "blocked_too_many_changed_files":
        prompt170_compat_result_class = "too_many_changes"
    elif status == "reentry_assimilation_completed_failure":
        prompt170_compat_result_class = "invocation_failure"
    elif status == "reentry_assimilation_completed_timeout":
        prompt170_compat_result_class = "invocation_timeout"
    elif status in {
        "blocked_reentry_invocation_not_ready",
        "blocked_ambiguous_write_sources",
        "blocked_human_review_required",
        "blocked_source_paths_unsafe",
    }:
        prompt170_compat_result_class = "blocked"
    elif status == "blocked_insufficient_assimilation_truth":
        prompt170_compat_result_class = "insufficient_truth"

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"

    return {
        "project_browser_autonomous_reentry_result_assimilation_status": status,
        "project_browser_autonomous_reentry_result_assimilation_authoritative_source_kind": (
            authoritative_source_kind
        ),
        "project_browser_autonomous_reentry_result_assimilation_authoritative_source_selected": bool(
            authoritative_source_selected
        ),
        "project_browser_autonomous_reentry_result_assimilation_authoritative_source_block_reason": (
            authoritative_source_block_reason
        ),
        "project_browser_autonomous_reentry_result_assimilation_reentry_source_available": bool(
            reentry_source_available
        ),
        "project_browser_autonomous_reentry_result_assimilation_reentry_source_selected": bool(
            authoritative_source_kind == "reentry" and authoritative_source_selected
        ),
        "project_browser_autonomous_reentry_result_assimilation_normal_write_source_available": bool(
            normal_write_source_available
        ),
        "project_browser_autonomous_reentry_result_assimilation_normal_write_source_selected": bool(
            authoritative_source_kind == "normal_write" and authoritative_source_selected
        ),
        "project_browser_autonomous_reentry_result_assimilation_ambiguous_write_sources": bool(
            ambiguous_write_sources
        ),
        "project_browser_autonomous_reentry_result_assimilation_source_status": source_status,
        "project_browser_autonomous_reentry_result_assimilation_source_result_class": (
            source_result_class
        ),
        "project_browser_autonomous_reentry_result_assimilation_source_prompt_kind": (
            source_prompt_kind
        ),
        "project_browser_autonomous_reentry_result_assimilation_source_prompt_path": (
            source_prompt_path
        ),
        "project_browser_autonomous_reentry_result_assimilation_source_stdout_path": (
            source_stdout_path
        ),
        "project_browser_autonomous_reentry_result_assimilation_source_stderr_path": (
            source_stderr_path
        ),
        "project_browser_autonomous_reentry_result_assimilation_source_result_path": (
            source_result_path
        ),
        "project_browser_autonomous_reentry_result_assimilation_source_git_diff_name_only_path": (
            source_git_diff_name_only_path
        ),
        "project_browser_autonomous_reentry_result_assimilation_source_git_diff_numstat_path": (
            source_git_diff_numstat_path
        ),
        "project_browser_autonomous_reentry_result_assimilation_source_changed_files": (
            source_changed_files
        ),
        "project_browser_autonomous_reentry_result_assimilation_source_changed_files_count": int(
            source_changed_files_count
        ),
        "project_browser_autonomous_reentry_result_assimilation_expected_changed_files": (
            expected_changed_files
        ),
        "project_browser_autonomous_reentry_result_assimilation_allowed_changed_files": (
            allowed_changed_files
        ),
        "project_browser_autonomous_reentry_result_assimilation_unexpected_changed_files": (
            unexpected_changed_files
        ),
        "project_browser_autonomous_reentry_result_assimilation_forbidden_changed_files": (
            forbidden_changed_files
        ),
        "project_browser_autonomous_reentry_result_assimilation_too_many_changed_files": bool(
            too_many_changed_files
        ),
        "project_browser_autonomous_reentry_result_assimilation_safe_for_validation_routing": bool(
            safe_for_validation_routing
        ),
        "project_browser_autonomous_reentry_result_assimilation_validation_routing_candidate": bool(
            validation_routing_candidate
        ),
        "project_browser_autonomous_reentry_result_assimilation_validation_routing_block_reason": (
            validation_routing_block_reason
        ),
        "project_browser_autonomous_reentry_result_assimilation_prompt170_compat_source_status": (
            prompt170_compat_source_status
        ),
        "project_browser_autonomous_reentry_result_assimilation_prompt170_compat_result_class": (
            prompt170_compat_result_class
        ),
        "project_browser_autonomous_reentry_result_assimilation_prompt170_compat_changed_files": (
            source_changed_files
        ),
        "project_browser_autonomous_reentry_result_assimilation_prompt170_compat_safe_for_validation_routing": bool(
            safe_for_validation_routing
        ),
        "project_browser_autonomous_reentry_result_assimilation_prompt170_compat_human_review_required": bool(
            human_review_required
        ),
        "project_browser_autonomous_reentry_result_assimilation_reentry_assimilation_completed": bool(
            reentry_assimilation_completed
        ),
        "project_browser_autonomous_reentry_result_assimilation_reentry_assimilation_failed": bool(
            reentry_assimilation_failed
        ),
        "project_browser_autonomous_reentry_result_assimilation_human_review_required": bool(
            human_review_required
        ),
        "project_browser_autonomous_reentry_result_assimilation_next_action": next_action,
        "project_browser_autonomous_reentry_result_assimilation_runtime_posture": runtime_posture,
        "project_browser_autonomous_reentry_result_assimilation_missing_inputs": (
            _serialize_required_signals(
                [
                    *missing_inputs,
                    _normalize_text(normalized_reentry_routing_block_reason, default=""),
                    _normalize_text(normalized_reentry_invocation_block_reason, default=""),
                    _normalize_text(reentry_result_assimilation_source, default=""),
                    _normalize_text(reentry_result_next_stage, default=""),
                    _normalize_text(reentry_next_action, default=""),
                    _normalize_text(normal_write_execution_status, default=""),
                ]
            )
        ),
    }

def _build_project_browser_autonomous_rollback_result_assimilation_state(
    *,
    rollback_execution_status: str,
    rollback_execution_allowed: bool,
    rollback_execution_attempted: bool,
    rollback_execution_completed: bool,
    rollback_execution_failed: bool,
    rollback_execution_block_reason: str,
    rollback_reason: str,
    rollback_strategy: str,
    rollback_target_files: list[str] | None,
    rollback_restored_tracked_files: list[str] | None,
    rollback_removed_untracked_files: list[str] | None,
    rollback_skipped_files: list[str] | None,
    rollback_failed_files: list[str] | None,
    rollback_command_results: list[dict[str, Any]] | None,
    rollback_commands_attempted: int,
    rollback_commands_completed: int,
    rollback_exit_code: int,
    rollback_timed_out: bool,
    pre_rollback_git_status_short: str,
    post_rollback_git_status_short: str,
    post_rollback_dirty: bool,
    post_rollback_expected_dirty_only: bool,
    rollback_execution_human_review_required: bool,
    rollback_execution_next_action: str,
    rollback_readiness_status: str,
    rollback_readiness_allowed: bool,
    rollback_readiness_block_reason: str,
    rollback_readiness_next_action: str,
    continuation_status: str,
    continuation_next_action: str,
    post_reentry_status: str,
    post_reentry_next_action: str,
) -> dict[str, Any]:
    allowed_statuses = {
        "rollback_result_assimilation_completed_clean",
        "rollback_result_assimilation_completed_expected_dirty",
        "rollback_result_assimilation_partial_failure",
        "rollback_result_assimilation_failed",
        "rollback_result_assimilation_timeout",
        "rollback_result_assimilation_unexpected_dirty",
        "rollback_result_assimilation_not_required",
        "rollback_result_assimilation_blocked_insufficient_truth",
        "insufficient_truth",
    }
    runtime_posture = [
        "prompt186_rollback_result_assimilation",
        "metadata_only",
        "no_rollback_execution",
        "no_codex_invocation",
        "no_prompt_generation",
        "no_commit",
    ]

    normalized_rollback_execution_status = _normalize_text(
        rollback_execution_status,
        default="insufficient_truth",
    )
    normalized_rollback_execution_block_reason = _normalize_text(
        rollback_execution_block_reason,
        default="",
    )
    normalized_rollback_reason = _normalize_text(rollback_reason, default="")
    normalized_rollback_strategy = _normalize_text(
        rollback_strategy,
        default="blocked_manual_review",
    )
    normalized_pre_status_short = _normalize_text(pre_rollback_git_status_short, default="")
    normalized_post_status_short = _normalize_text(post_rollback_git_status_short, default="")
    normalized_rollback_execution_next_action = _normalize_text(
        rollback_execution_next_action,
        default="manual_review_required",
    )
    normalized_rollback_readiness_status = _normalize_text(
        rollback_readiness_status,
        default="insufficient_truth",
    )
    normalized_rollback_readiness_block_reason = _normalize_text(
        rollback_readiness_block_reason,
        default="",
    )
    normalized_rollback_readiness_next_action = _normalize_text(
        rollback_readiness_next_action,
        default="manual_review_required",
    )
    normalized_continuation_status = _normalize_text(
        continuation_status,
        default="insufficient_truth",
    )
    normalized_continuation_next_action = _normalize_text(
        continuation_next_action,
        default="insufficient_truth",
    )
    normalized_post_reentry_status = _normalize_text(
        post_reentry_status,
        default="insufficient_truth",
    )
    normalized_post_reentry_next_action = _normalize_text(
        post_reentry_next_action,
        default="insufficient_truth",
    )

    normalized_rollback_target_files = _normalize_string_list(rollback_target_files or [])
    normalized_restored_tracked_files = _normalize_string_list(
        rollback_restored_tracked_files or []
    )
    normalized_removed_untracked_files = _normalize_string_list(
        rollback_removed_untracked_files or []
    )
    normalized_skipped_files = _normalize_string_list(rollback_skipped_files or [])
    normalized_failed_files = _normalize_string_list(rollback_failed_files or [])
    normalized_command_results = (
        rollback_command_results if isinstance(rollback_command_results, list) else []
    )

    rollback_remaining_dirty_files = _serialize_required_signals(
        [
            _normalize_text(_parse_git_status_path(line), default="")
            for line in normalized_post_status_short.splitlines()
        ]
    )

    status = "rollback_result_assimilation_blocked_insufficient_truth"
    rollback_result_available = False
    rollback_result_selected = False
    rollback_result_class = "blocked"
    rollback_result_block_reason = "blocked_insufficient_rollback_result_truth"
    rollback_completed_cleanly = False
    rollback_completed_with_expected_dirty = False
    rollback_partial_failure = False
    rollback_failed = False
    rollback_timeout = False
    safe_to_continue_after_rollback = False
    safe_to_commit_after_rollback = False
    should_generate_fix_prompt = False
    should_generate_next_prompt = False
    should_invoke_codex = False
    should_execute_rollback = False
    should_commit = False
    should_stop = True
    stop_reason = "insufficient_rollback_result_truth"
    human_review_required = True
    next_action = "manual_review_required"

    if normalized_rollback_execution_status == "rollback_execution_not_required":
        status = "rollback_result_assimilation_not_required"
        rollback_result_available = False
        rollback_result_selected = False
        rollback_result_class = "not_required"
        rollback_result_block_reason = "rollback_not_required"
        should_stop = False
        stop_reason = ""
        human_review_required = False
        next_action = "no_rollback_required"
    elif normalized_rollback_execution_status in {
        "rollback_execution_completed",
        "rollback_execution_partial_failure",
        "rollback_execution_failed",
        "rollback_execution_timeout",
    }:
        rollback_result_available = True
        rollback_result_selected = True
        rollback_result_block_reason = ""

        if bool(rollback_timed_out) or normalized_rollback_execution_status == "rollback_execution_timeout":
            status = "rollback_result_assimilation_timeout"
            rollback_result_class = "timeout"
            rollback_timeout = True
            rollback_failed = True
            should_stop = True
            stop_reason = "rollback_timeout"
            human_review_required = True
            next_action = "manual_review_required"
        elif normalized_rollback_execution_status == "rollback_execution_partial_failure":
            status = "rollback_result_assimilation_partial_failure"
            rollback_result_class = "partial_failure"
            rollback_partial_failure = True
            rollback_failed = True
            should_stop = True
            stop_reason = "rollback_partial_failure"
            human_review_required = True
            next_action = "manual_review_required"
        elif normalized_rollback_execution_status == "rollback_execution_failed" or bool(
            rollback_execution_failed
        ):
            status = "rollback_result_assimilation_failed"
            rollback_result_class = "failed"
            rollback_failed = True
            should_stop = True
            stop_reason = "rollback_failed"
            human_review_required = True
            next_action = "manual_review_required"
        elif bool(post_rollback_dirty) and not bool(post_rollback_expected_dirty_only):
            status = "rollback_result_assimilation_unexpected_dirty"
            rollback_result_class = "unexpected_dirty"
            rollback_failed = True
            should_stop = True
            stop_reason = "unexpected_dirty_after_rollback"
            human_review_required = True
            next_action = "manual_review_required"
        elif not bool(post_rollback_dirty):
            status = "rollback_result_assimilation_completed_clean"
            rollback_result_class = "completed_clean"
            rollback_completed_cleanly = True
            safe_to_continue_after_rollback = True
            safe_to_commit_after_rollback = False
            should_generate_fix_prompt = True
            should_stop = False
            stop_reason = ""
            human_review_required = False
            next_action = "generate_fix_prompt_after_rollback"
        else:
            status = "rollback_result_assimilation_completed_expected_dirty"
            rollback_result_class = "completed_expected_dirty"
            rollback_completed_with_expected_dirty = True
            safe_to_continue_after_rollback = True
            safe_to_commit_after_rollback = False
            should_generate_fix_prompt = True
            should_stop = False
            stop_reason = ""
            human_review_required = False
            next_action = "generate_fix_prompt_after_rollback"
    else:
        status = "rollback_result_assimilation_blocked_insufficient_truth"
        rollback_result_available = False
        rollback_result_selected = False
        rollback_result_class = "blocked"
        rollback_result_block_reason = "blocked_insufficient_rollback_result_truth"
        safe_to_continue_after_rollback = False
        safe_to_commit_after_rollback = False
        should_stop = True
        stop_reason = "insufficient_rollback_result_truth"
        human_review_required = True
        next_action = "manual_review_required"

    if rollback_execution_human_review_required and status not in {
        "rollback_result_assimilation_completed_clean",
        "rollback_result_assimilation_completed_expected_dirty",
        "rollback_result_assimilation_not_required",
    }:
        human_review_required = True

    if status not in allowed_statuses:
        status = "insufficient_truth"

    return {
        "project_browser_autonomous_rollback_result_assimilation_status": status,
        "project_browser_autonomous_rollback_result_assimilation_rollback_result_available": bool(
            rollback_result_available
        ),
        "project_browser_autonomous_rollback_result_assimilation_rollback_result_selected": bool(
            rollback_result_selected
        ),
        "project_browser_autonomous_rollback_result_assimilation_rollback_result_class": (
            rollback_result_class
        ),
        "project_browser_autonomous_rollback_result_assimilation_rollback_result_block_reason": (
            rollback_result_block_reason
        ),
        "project_browser_autonomous_rollback_result_assimilation_rollback_completed_cleanly": bool(
            rollback_completed_cleanly
        ),
        "project_browser_autonomous_rollback_result_assimilation_rollback_completed_with_expected_dirty": bool(
            rollback_completed_with_expected_dirty
        ),
        "project_browser_autonomous_rollback_result_assimilation_rollback_partial_failure": bool(
            rollback_partial_failure
        ),
        "project_browser_autonomous_rollback_result_assimilation_rollback_failed": bool(
            rollback_failed
        ),
        "project_browser_autonomous_rollback_result_assimilation_rollback_timeout": bool(
            rollback_timeout
        ),
        "project_browser_autonomous_rollback_result_assimilation_post_rollback_dirty": bool(
            post_rollback_dirty
        ),
        "project_browser_autonomous_rollback_result_assimilation_post_rollback_expected_dirty_only": bool(
            post_rollback_expected_dirty_only
        ),
        "project_browser_autonomous_rollback_result_assimilation_post_rollback_git_status_short": (
            normalized_post_status_short
        ),
        "project_browser_autonomous_rollback_result_assimilation_restored_tracked_files": (
            normalized_restored_tracked_files
        ),
        "project_browser_autonomous_rollback_result_assimilation_removed_untracked_files": (
            normalized_removed_untracked_files
        ),
        "project_browser_autonomous_rollback_result_assimilation_rollback_failed_files": (
            normalized_failed_files
        ),
        "project_browser_autonomous_rollback_result_assimilation_rollback_remaining_dirty_files": (
            rollback_remaining_dirty_files
        ),
        "project_browser_autonomous_rollback_result_assimilation_safe_to_continue_after_rollback": bool(
            safe_to_continue_after_rollback
        ),
        "project_browser_autonomous_rollback_result_assimilation_safe_to_commit_after_rollback": bool(
            safe_to_commit_after_rollback
        ),
        "project_browser_autonomous_rollback_result_assimilation_should_generate_fix_prompt": bool(
            should_generate_fix_prompt
        ),
        "project_browser_autonomous_rollback_result_assimilation_should_generate_next_prompt": bool(
            should_generate_next_prompt
        ),
        "project_browser_autonomous_rollback_result_assimilation_should_invoke_codex": bool(
            should_invoke_codex
        ),
        "project_browser_autonomous_rollback_result_assimilation_should_execute_rollback": bool(
            should_execute_rollback
        ),
        "project_browser_autonomous_rollback_result_assimilation_should_commit": bool(
            should_commit
        ),
        "project_browser_autonomous_rollback_result_assimilation_should_stop": bool(
            should_stop
        ),
        "project_browser_autonomous_rollback_result_assimilation_stop_reason": stop_reason,
        "project_browser_autonomous_rollback_result_assimilation_human_review_required": bool(
            human_review_required
        ),
        "project_browser_autonomous_rollback_result_assimilation_next_action": next_action,
        "project_browser_autonomous_rollback_result_assimilation_runtime_posture": runtime_posture,
        "project_browser_autonomous_rollback_result_assimilation_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_rollback_execution_status,
                    normalized_rollback_execution_block_reason,
                    normalized_rollback_execution_next_action,
                    normalized_rollback_readiness_status,
                    normalized_rollback_readiness_block_reason,
                    normalized_rollback_readiness_next_action,
                    normalized_continuation_status,
                    normalized_continuation_next_action,
                    normalized_post_reentry_status,
                    normalized_post_reentry_next_action,
                    normalized_rollback_reason,
                    normalized_rollback_strategy,
                    str(_as_non_negative_int(rollback_commands_attempted, default=0)),
                    str(_as_non_negative_int(rollback_commands_completed, default=0)),
                    str(_as_int(rollback_exit_code, default=0)),
                    "rollback_target_files_missing"
                    if rollback_result_available and not normalized_rollback_target_files
                    else "",
                    "rollback_command_results_missing"
                    if rollback_result_available and not normalized_command_results
                    else "",
                    "pre_rollback_status_missing"
                    if rollback_result_available and not normalized_pre_status_short
                    else "",
                    "rollback_skipped_files_present"
                    if normalized_skipped_files
                    else "",
                ]
            )
        ),
    }

def _build_project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_state(
    *,
    repository_path: str,
    execution_status: str,
    execution_allowed: bool,
    execution_attempted: bool,
    execution_completed: bool,
    execution_failed: bool,
    execution_block_reason: str,
    execution_source: str,
    prompt_kind: str,
    prompt_path: str,
    max_invocations: int,
    invocations_attempted: int,
    invocations_completed: int,
    reused_invocation_path: bool,
    execution_sandbox: str,
    command: list[str] | None,
    stdout_path: str,
    stderr_path: str,
    result_path: str,
    git_diff_name_only_path: str,
    git_diff_numstat_path: str,
    changed_files_after: list[str] | None,
    changed_files_count_after: int,
    result_class: str,
    exit_code: int,
    timed_out: bool,
    result_ready_for_assimilation: bool,
    result_assimilation_source: str,
    result_next_stage: str,
    execution_human_review_required: bool,
    execution_next_action: str,
    checkpoint_status: str,
    checkpoint_next_action: str,
    propagation_status: str,
    codex_reentry_invocation_status: str,
    codex_write_execution_status: str,
    codex_write_result_status: str,
    fix_target_files: list[str] | None,
) -> dict[str, Any]:
    allowed_statuses = {
        "post_rollback_fix_reentry_result_completed_with_changes",
        "post_rollback_fix_reentry_result_completed_no_changes",
        "post_rollback_fix_reentry_result_completed_failure",
        "post_rollback_fix_reentry_result_completed_timeout",
        "post_rollback_fix_reentry_result_validation_passed",
        "post_rollback_fix_reentry_result_validation_failed",
        "post_rollback_fix_reentry_result_validation_timeout",
        "post_rollback_fix_reentry_result_blocked_execution_not_ready",
        "post_rollback_fix_reentry_result_blocked_unsafe_changes",
        "post_rollback_fix_reentry_result_blocked_validation_routing",
        "post_rollback_fix_reentry_result_blocked_no_py_compile_candidates",
        "post_rollback_fix_reentry_result_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "prepare_commit_readiness",
        "generate_fix_prompt",
        "manual_review_required",
        "wait_for_more_truth",
        "insufficient_truth",
    }
    fixed_prompt_path = "/tmp/codex-local-runner-decision/generated_fix_prompt.txt"
    fixed_diff_name_only_path = (
        "/tmp/codex-local-runner-decision/codex_write_git_diff_name_only.txt"
    )
    fixed_diff_numstat_path = "/tmp/codex-local-runner-decision/codex_write_git_diff_numstat.txt"
    allowed_diff_paths = {fixed_diff_name_only_path, fixed_diff_numstat_path}
    max_changed_files_threshold = 8
    runtime_posture = [
        "prompt193_post_rollback_fix_reentry_result_assimilation",
        "prompt192_authoritative_source_only",
        "bounded_py_compile_only",
        "no_codex_invocation",
        "no_rollback_execution",
        "no_commit",
        "no_loop",
    ]

    normalized_repository_path = _normalize_text(repository_path, default="")
    normalized_execution_status = _normalize_text(execution_status, default="insufficient_truth")
    normalized_execution_block_reason = _normalize_text(execution_block_reason, default="")
    normalized_execution_source = _normalize_text(execution_source, default="")
    normalized_prompt_kind = _normalize_text(prompt_kind, default="none")
    normalized_prompt_path = _normalize_text(prompt_path, default="")
    normalized_result_class = _normalize_text(result_class, default="blocked")
    normalized_result_assimilation_source = _normalize_text(
        result_assimilation_source,
        default="",
    )
    normalized_result_next_stage = _normalize_text(result_next_stage, default="")
    normalized_execution_next_action = _normalize_text(execution_next_action, default="")
    normalized_checkpoint_status = _normalize_text(checkpoint_status, default="insufficient_truth")
    normalized_checkpoint_next_action = _normalize_text(checkpoint_next_action, default="")
    normalized_propagation_status = _normalize_text(propagation_status, default="insufficient_truth")
    normalized_codex_reentry_invocation_status = _normalize_text(
        codex_reentry_invocation_status,
        default="insufficient_truth",
    )
    normalized_codex_write_execution_status = _normalize_text(
        codex_write_execution_status,
        default="insufficient_truth",
    )
    normalized_codex_write_result_status = _normalize_text(
        codex_write_result_status,
        default="insufficient_truth",
    )
    normalized_command = _normalize_string_list(command or [])
    normalized_stdout_path = _normalize_text(stdout_path, default="")
    normalized_stderr_path = _normalize_text(stderr_path, default="")
    normalized_result_path = _normalize_text(result_path, default="")
    normalized_diff_name_only_path = _normalize_text(git_diff_name_only_path, default="")
    normalized_diff_numstat_path = _normalize_text(git_diff_numstat_path, default="")
    normalized_changed_files = _normalize_string_list(changed_files_after or [])
    normalized_changed_files_count = _as_non_negative_int(
        changed_files_count_after,
        default=len(normalized_changed_files),
    )
    normalized_fix_target_files = _normalize_string_list(fix_target_files or [])
    normalized_max_invocations = _as_non_negative_int(max_invocations, default=0)
    normalized_invocations_attempted = _as_non_negative_int(invocations_attempted, default=0)
    normalized_invocations_completed = _as_non_negative_int(invocations_completed, default=0)

    authoritative_source_kind = "none"
    authoritative_source_selected = False
    authoritative_source_block_reason = "blocked_execution_not_ready"
    if (
        bool(result_ready_for_assimilation)
        and normalized_result_assimilation_source
        == "prompt192_post_rollback_fix_reentry_execution"
        and bool(execution_attempted)
        and normalized_prompt_kind == "fix"
        and normalized_prompt_path == fixed_prompt_path
    ):
        authoritative_source_kind = "post_rollback_fix_reentry"
        authoritative_source_selected = True
        authoritative_source_block_reason = ""

    source_status = normalized_execution_status
    source_result_class = normalized_result_class
    source_prompt_kind = normalized_prompt_kind if normalized_prompt_kind in {"fix", "next"} else "none"
    source_prompt_path = normalized_prompt_path
    source_stdout_path = normalized_stdout_path
    source_stderr_path = normalized_stderr_path
    source_result_path = normalized_result_path
    source_git_diff_name_only_path = normalized_diff_name_only_path
    source_git_diff_numstat_path = normalized_diff_numstat_path
    source_changed_files = list(normalized_changed_files)
    source_changed_files_count = normalized_changed_files_count

    def _read_changed_files_from_diff() -> list[str]:
        changed_from_name: list[str] = []
        changed_from_numstat: list[str] = []
        if source_git_diff_name_only_path in allowed_diff_paths:
            path_obj = Path(source_git_diff_name_only_path)
            if path_obj.exists() and not path_obj.is_symlink():
                try:
                    changed_from_name = _serialize_required_signals(
                        path_obj.read_text(encoding="utf-8").splitlines()
                    )
                except OSError:
                    changed_from_name = []
        if source_git_diff_numstat_path in allowed_diff_paths:
            path_obj = Path(source_git_diff_numstat_path)
            if path_obj.exists() and not path_obj.is_symlink():
                try:
                    for line in path_obj.read_text(encoding="utf-8").splitlines():
                        parts = line.split("\t")
                        if len(parts) >= 3:
                            changed_from_numstat.append(parts[-1].strip())
                except OSError:
                    changed_from_numstat = []
        return (
            changed_from_name
            if changed_from_name
            else _serialize_required_signals(changed_from_numstat)
        )

    if authoritative_source_selected and not source_changed_files:
        source_changed_files = _read_changed_files_from_diff()
        source_changed_files_count = max(source_changed_files_count, len(source_changed_files))

    expected_changed_files = _serialize_required_signals(normalized_fix_target_files)
    allowed_changed_files = list(expected_changed_files)
    allowed_set = set(allowed_changed_files)

    def _is_forbidden_changed_file(path_text: str) -> bool:
        normalized_path = _normalize_text(path_text, default="").replace("\\", "/")
        if not normalized_path:
            return False
        lowered = normalized_path.lower()
        if normalized_path.startswith("/") or normalized_path.startswith("../"):
            return True
        if normalized_path.startswith(".git/"):
            return True
        if normalized_path.startswith("prompts/context/") and normalized_path not in allowed_set:
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
        [path for path in source_changed_files if _is_forbidden_changed_file(path)]
    )
    forbidden_set = set(forbidden_changed_files)
    unexpected_changed_files = _serialize_required_signals(
        [path for path in source_changed_files if path not in allowed_set and path not in forbidden_set]
    )
    too_many_changed_files = bool(source_changed_files_count > max_changed_files_threshold)

    safe_for_validation_routing = False
    validation_routing_candidate = False
    validation_routing_block_reason = "blocked_validation_routing"
    validation_target_files: list[str] = []
    py_compile_candidate_files: list[str] = []
    validation_executed = False
    validation_passed = False
    validation_failed = False
    validation_timeout = False
    py_compile_results: list[dict[str, Any]] = []

    cycle_status = "post_rollback_fix_reentry_cycle_blocked"
    cycle_passed = False
    cycle_failed = False
    cycle_blocked = True
    cycle_block_reason = "blocked_insufficient_truth"
    commit_candidate = False
    fix_candidate = False
    rollback_candidate = False
    rollback_reason = ""
    local_human_review_required = True
    status = "post_rollback_fix_reentry_result_blocked_insufficient_truth"
    next_action = "manual_review_required"
    missing_inputs: list[str] = []

    if not authoritative_source_selected:
        status = "post_rollback_fix_reentry_result_blocked_execution_not_ready"
        cycle_status = "post_rollback_fix_reentry_cycle_blocked_execution_not_ready"
        cycle_blocked = True
        cycle_block_reason = "blocked_execution_not_ready"
        local_human_review_required = bool(execution_human_review_required)
        next_action = (
            "manual_review_required"
            if local_human_review_required
            else "wait_for_more_truth"
        )
        authoritative_source_block_reason = (
            normalized_execution_block_reason or authoritative_source_block_reason
        )
    elif source_result_class == "completed_timeout" or bool(timed_out):
        status = "post_rollback_fix_reentry_result_completed_timeout"
        cycle_status = "cycle_blocked_invocation_timeout"
        cycle_blocked = True
        cycle_block_reason = "post_rollback_fix_reentry_invocation_timeout"
        rollback_candidate = True
        rollback_reason = "post_rollback_fix_reentry_invocation_timeout"
        local_human_review_required = True
        validation_routing_block_reason = "blocked_post_rollback_fix_reentry_timeout"
        next_action = "manual_review_required"
    elif source_result_class == "completed_failure" or bool(execution_failed):
        status = "post_rollback_fix_reentry_result_completed_failure"
        cycle_status = "cycle_failed_invocation"
        cycle_failed = True
        cycle_blocked = False
        cycle_block_reason = "post_rollback_fix_reentry_invocation_failure"
        fix_candidate = True
        rollback_candidate = True
        rollback_reason = "post_rollback_fix_reentry_invocation_failure"
        local_human_review_required = False
        validation_routing_block_reason = "blocked_post_rollback_fix_reentry_failure"
        next_action = "generate_fix_prompt"
    elif source_result_class == "completed_no_changes":
        status = "post_rollback_fix_reentry_result_completed_no_changes"
        cycle_status = "cycle_blocked_no_changes"
        cycle_blocked = True
        cycle_block_reason = "blocked_no_changed_files"
        local_human_review_required = True
        validation_routing_block_reason = "blocked_no_changed_files"
        next_action = "manual_review_required"
    elif source_result_class == "completed_with_changes":
        status = "post_rollback_fix_reentry_result_completed_with_changes"
        if forbidden_changed_files or unexpected_changed_files or too_many_changed_files:
            status = "post_rollback_fix_reentry_result_blocked_unsafe_changes"
            cycle_status = "post_rollback_fix_reentry_cycle_blocked_unsafe_changes"
            cycle_blocked = True
            cycle_block_reason = "unsafe_post_rollback_fix_reentry_changes"
            rollback_candidate = True
            rollback_reason = "unsafe_post_rollback_fix_reentry_changes"
            local_human_review_required = True
            next_action = "manual_review_required"
            validation_routing_block_reason = "blocked_unsafe_post_rollback_fix_reentry_changes"
        elif not source_changed_files:
            status = "post_rollback_fix_reentry_result_blocked_insufficient_truth"
            cycle_status = "post_rollback_fix_reentry_cycle_blocked_missing_changes"
            cycle_blocked = True
            cycle_block_reason = "changed_files_missing"
            local_human_review_required = True
            validation_routing_block_reason = "blocked_insufficient_truth"
            next_action = "wait_for_more_truth"
            missing_inputs.append("source_changed_files")
        else:
            safe_for_validation_routing = True
            validation_routing_candidate = True
            validation_routing_block_reason = ""
            validation_target_files = sorted(
                set(path for path in source_changed_files if path in allowed_set)
            )
            py_compile_candidate_files = sorted(
                [path for path in validation_target_files if path.endswith(".py")]
            )
            if not py_compile_candidate_files:
                status = "post_rollback_fix_reentry_result_blocked_no_py_compile_candidates"
                cycle_status = "post_rollback_fix_reentry_cycle_blocked_no_py_compile_candidates"
                cycle_blocked = True
                cycle_block_reason = "blocked_no_post_reentry_py_compile_candidates"
                local_human_review_required = True
                next_action = "manual_review_required"
            else:
                validation_state = _build_project_browser_autonomous_post_write_validation_execution_state(
                    repository_path=normalized_repository_path,
                    source_routing_status="validation_routing_allowed",
                    source_validation_allowed=True,
                    source_validation_block_reason="",
                    validation_target_files=validation_target_files,
                    py_compile_candidate_files=py_compile_candidate_files,
                    targeted_test_candidate_files=[],
                    human_review_required=False,
                    source_next_action="run_post_write_validation",
                )
                validation_status = _normalize_text(
                    validation_state.get(
                        "project_browser_autonomous_post_write_validation_execution_status"
                    ),
                    default="blocked_routing_not_allowed",
                )
                validation_executed = bool(
                    validation_state.get(
                        "project_browser_autonomous_post_write_validation_execution_validation_executed",
                        False,
                    )
                )
                validation_passed = bool(
                    validation_state.get(
                        "project_browser_autonomous_post_write_validation_execution_validation_passed",
                        False,
                    )
                )
                validation_failed = bool(
                    validation_state.get(
                        "project_browser_autonomous_post_write_validation_execution_validation_failed",
                        False,
                    )
                )
                validation_timeout = bool(validation_status == "validation_timeout")
                py_compile_results = (
                    list(
                        validation_state.get(
                            "project_browser_autonomous_post_write_validation_execution_py_compile_results",
                            [],
                        )
                    )
                    if isinstance(
                        validation_state.get(
                            "project_browser_autonomous_post_write_validation_execution_py_compile_results",
                            [],
                        ),
                        list,
                    )
                    else []
                )
                if validation_passed:
                    status = "post_rollback_fix_reentry_result_validation_passed"
                    cycle_status = "post_rollback_fix_reentry_cycle_passed"
                    cycle_passed = True
                    cycle_failed = False
                    cycle_blocked = False
                    cycle_block_reason = ""
                    commit_candidate = bool(
                        not forbidden_changed_files
                        and not unexpected_changed_files
                        and not too_many_changed_files
                        and bool(source_changed_files)
                    )
                    fix_candidate = False
                    rollback_candidate = False
                    rollback_reason = ""
                    local_human_review_required = False
                    next_action = "prepare_commit_readiness"
                elif validation_timeout:
                    status = "post_rollback_fix_reentry_result_validation_timeout"
                    cycle_status = "post_rollback_fix_reentry_cycle_blocked_validation_timeout"
                    cycle_blocked = True
                    cycle_block_reason = "post_rollback_fix_reentry_validation_timeout"
                    commit_candidate = False
                    fix_candidate = False
                    rollback_candidate = True
                    rollback_reason = "post_rollback_fix_reentry_validation_timeout"
                    local_human_review_required = True
                    next_action = "manual_review_required"
                elif validation_failed:
                    status = "post_rollback_fix_reentry_result_validation_failed"
                    cycle_status = "post_rollback_fix_reentry_cycle_failed_validation"
                    cycle_passed = False
                    cycle_failed = True
                    cycle_blocked = False
                    cycle_block_reason = "post_rollback_fix_reentry_validation_failed"
                    commit_candidate = False
                    fix_candidate = True
                    rollback_candidate = True
                    rollback_reason = "post_rollback_fix_reentry_validation_failed"
                    local_human_review_required = False
                    next_action = "generate_fix_prompt"
                else:
                    status = "post_rollback_fix_reentry_result_blocked_validation_routing"
                    cycle_status = "post_rollback_fix_reentry_cycle_blocked_validation_routing"
                    cycle_blocked = True
                    cycle_block_reason = "blocked_post_rollback_fix_reentry_validation_routing"
                    local_human_review_required = True
                    next_action = "manual_review_required"
                    validation_routing_block_reason = "blocked_post_rollback_fix_reentry_validation_routing"
    else:
        status = "post_rollback_fix_reentry_result_blocked_insufficient_truth"
        cycle_status = "post_rollback_fix_reentry_cycle_blocked_insufficient_truth"
        cycle_blocked = True
        cycle_block_reason = "blocked_insufficient_truth"
        local_human_review_required = True
        next_action = "wait_for_more_truth"
        missing_inputs.append("source_result_class")

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"
    if commit_candidate and (
        not validation_passed
        or not cycle_passed
        or rollback_candidate
        or local_human_review_required
        or forbidden_changed_files
        or unexpected_changed_files
        or too_many_changed_files
    ):
        commit_candidate = False

    return {
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_status": status,
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_authoritative_source_kind": (
            authoritative_source_kind
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_authoritative_source_selected": bool(
            authoritative_source_selected
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_authoritative_source_block_reason": (
            authoritative_source_block_reason
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_source_status": source_status,
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_source_result_class": (
            source_result_class
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_source_prompt_kind": (
            source_prompt_kind
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_source_prompt_path": (
            source_prompt_path
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_source_stdout_path": (
            source_stdout_path
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_source_stderr_path": (
            source_stderr_path
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_source_result_path": (
            source_result_path
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_source_git_diff_name_only_path": (
            source_git_diff_name_only_path
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_source_git_diff_numstat_path": (
            source_git_diff_numstat_path
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_source_changed_files": (
            source_changed_files
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_source_changed_files_count": int(
            source_changed_files_count
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_expected_changed_files": (
            expected_changed_files
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_allowed_changed_files": (
            allowed_changed_files
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_unexpected_changed_files": (
            unexpected_changed_files
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_forbidden_changed_files": (
            forbidden_changed_files
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_too_many_changed_files": bool(
            too_many_changed_files
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_safe_for_validation_routing": bool(
            safe_for_validation_routing
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_validation_routing_candidate": bool(
            validation_routing_candidate
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_validation_routing_block_reason": (
            validation_routing_block_reason
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_validation_target_files": (
            validation_target_files
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_py_compile_candidate_files": (
            py_compile_candidate_files
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_validation_executed": bool(
            validation_executed
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_validation_passed": bool(
            validation_passed
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_validation_failed": bool(
            validation_failed
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_validation_timeout": bool(
            validation_timeout
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_py_compile_results": (
            py_compile_results
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_cycle_status": (
            cycle_status
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_cycle_passed": bool(
            cycle_passed
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_cycle_failed": bool(
            cycle_failed
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_cycle_blocked": bool(
            cycle_blocked
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_cycle_block_reason": (
            cycle_block_reason
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_commit_candidate": bool(
            commit_candidate
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_fix_candidate": bool(
            fix_candidate
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_rollback_candidate": bool(
            rollback_candidate
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_rollback_reason": (
            rollback_reason
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_human_review_required": bool(
            local_human_review_required
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_next_action": (
            next_action
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_post_rollback_fix_reentry_result_assimilation_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_execution_status,
                    normalized_execution_block_reason,
                    normalized_execution_source,
                    normalized_result_assimilation_source,
                    normalized_result_next_stage,
                    normalized_execution_next_action,
                    normalized_checkpoint_status,
                    normalized_checkpoint_next_action,
                    normalized_propagation_status,
                    normalized_codex_reentry_invocation_status,
                    normalized_codex_write_execution_status,
                    normalized_codex_write_result_status,
                    _normalize_text(execution_source, default=""),
                    _normalize_text(execution_sandbox, default=""),
                    str(normalized_max_invocations),
                    str(normalized_invocations_attempted),
                    str(normalized_invocations_completed),
                    "execution_not_allowed" if not execution_allowed else "",
                    "execution_not_completed" if not execution_completed else "",
                    "execution_human_review_required" if execution_human_review_required else "",
                    "result_not_ready_for_assimilation" if not result_ready_for_assimilation else "",
                    "prompt_path_not_fixed" if normalized_prompt_path != fixed_prompt_path else "",
                    "prompt_kind_not_fix" if normalized_prompt_kind != "fix" else "",
                    "reused_invocation_path_false" if not reused_invocation_path else "",
                    "command_missing" if not normalized_command else "",
                    "exit_code_missing" if _as_int(exit_code, default=-1) == -1 else "",
                    *missing_inputs,
                ]
            )
        ),
    }

def _build_project_browser_autonomous_commit_tag_result_assimilation_state(
    *,
    execution_status: str,
    execution_attempted: bool,
    execution_completed: bool,
    execution_failed: bool,
    execution_block_reason: str,
    commit_source: str,
    commit_files: list[str] | None,
    commit_file_count: int,
    tag_name: str,
    post_commit_git_status_short: str,
    git_commit_completed: bool,
    git_tag_completed: bool,
    commit_hash: str,
    timed_out: bool,
    execution_human_review_required: bool,
    execution_next_action: str,
    readiness_status: str,
    readiness_next_action: str,
    source_assimilation_status: str,
    source_next_action: str,
    continuation_status: str,
    continuation_next_action: str,
) -> dict[str, Any]:
    allowed_statuses = {
        "commit_tag_result_assimilation_completed",
        "commit_tag_result_assimilation_completed_with_unexpected_dirty",
        "commit_tag_result_assimilation_partial_commit_tag_failed",
        "commit_tag_result_assimilation_failed_git_add",
        "commit_tag_result_assimilation_failed_git_commit",
        "commit_tag_result_assimilation_failed_git_tag",
        "commit_tag_result_assimilation_timeout",
        "commit_tag_result_assimilation_blocked",
        "commit_tag_result_assimilation_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "prepare_next_cycle_or_github_readiness",
        "manual_review_required",
        "no_commit_tag_execution",
        "wait_for_more_truth",
        "insufficient_truth",
    }
    runtime_posture = [
        "prompt196_commit_tag_result_assimilation",
        "metadata_only",
        "no_git_mutation",
        "no_push",
        "no_codex_invocation",
        "no_rollback_execution",
        "no_loop",
    ]

    normalized_execution_status = _normalize_text(execution_status, default="insufficient_truth")
    normalized_execution_block_reason = _normalize_text(execution_block_reason, default="")
    normalized_commit_source = _normalize_text(commit_source, default="")
    normalized_commit_files = _normalize_string_list(commit_files or [])
    normalized_commit_file_count = _as_non_negative_int(
        commit_file_count,
        default=len(normalized_commit_files),
    )
    normalized_tag_name = _normalize_text(tag_name, default="")
    normalized_post_commit_git_status_short = _normalize_text(
        post_commit_git_status_short,
        default="",
    )
    normalized_commit_hash = _normalize_text(commit_hash, default="")
    normalized_execution_next_action = _normalize_text(execution_next_action, default="")
    normalized_readiness_status = _normalize_text(readiness_status, default="insufficient_truth")
    normalized_readiness_next_action = _normalize_text(readiness_next_action, default="")
    normalized_source_assimilation_status = _normalize_text(
        source_assimilation_status,
        default="insufficient_truth",
    )
    normalized_source_next_action = _normalize_text(source_next_action, default="")
    normalized_continuation_status = _normalize_text(
        continuation_status,
        default="insufficient_truth",
    )
    normalized_continuation_next_action = _normalize_text(continuation_next_action, default="")

    commit_tag_result_available = False
    commit_tag_result_selected = False
    commit_tag_result_class = "insufficient_truth"
    commit_tag_result_block_reason = "blocked_insufficient_commit_tag_result_truth"
    commit_completed = False
    tag_completed = False
    partial_commit_without_tag = False
    commit_failed = False
    tag_failed = False
    commit_tag_timeout = False
    commit_tag_blocked = False
    safe_post_commit_handoff = False
    post_commit_handoff_allowed = False
    post_commit_handoff_kind = "none"
    post_commit_handoff_source = ""
    should_prepare_next_cycle = False
    should_prepare_github_handoff = False
    should_push = False
    should_invoke_codex = False
    should_execute_rollback = False
    should_commit = False
    should_tag = False
    should_stop = True
    stop_reason = "insufficient_commit_tag_result_truth"
    human_review_required = True
    next_action = "manual_review_required"
    status = "commit_tag_result_assimilation_blocked_insufficient_truth"
    missing_inputs: list[str] = []

    post_commit_paths = _serialize_required_signals(
        [
            _normalize_text(_parse_git_status_path(line), default="")
            for line in normalized_post_commit_git_status_short.splitlines()
        ]
    )
    post_commit_dirty = bool(post_commit_paths)
    post_commit_expected_dirty_only = bool(
        post_commit_dirty
        and all(path in set(normalized_commit_files) for path in post_commit_paths)
    )

    authoritative_source_kind = "prompt195_commit_tag_execution"
    authoritative_source_valid = bool(
        normalized_execution_status
        and (
            bool(execution_attempted)
            or normalized_execution_status.startswith("commit_tag_execution_blocked")
        )
        and normalized_commit_source
    )

    if not authoritative_source_valid:
        status = "commit_tag_result_assimilation_blocked_insufficient_truth"
        commit_tag_result_available = False
        commit_tag_result_selected = False
        commit_tag_result_class = "insufficient_truth"
        commit_tag_result_block_reason = "blocked_insufficient_commit_tag_result_truth"
        human_review_required = True
        should_stop = True
        stop_reason = "insufficient_commit_tag_result_truth"
        next_action = "manual_review_required"
    elif (
        normalized_execution_status == "commit_tag_execution_completed"
        and bool(git_commit_completed)
        and bool(git_tag_completed)
        and bool(normalized_commit_hash)
        and bool(normalized_tag_name)
        and not bool(execution_human_review_required)
    ):
        status = "commit_tag_result_assimilation_completed"
        commit_tag_result_available = True
        commit_tag_result_selected = True
        commit_tag_result_class = "completed"
        commit_tag_result_block_reason = ""
        commit_completed = True
        tag_completed = True
        partial_commit_without_tag = False
        commit_failed = False
        tag_failed = False
        commit_tag_timeout = False
        commit_tag_blocked = False
        safe_post_commit_handoff = True
        post_commit_handoff_allowed = True
        post_commit_handoff_kind = "post_commit_success"
        post_commit_handoff_source = authoritative_source_kind
        should_prepare_next_cycle = True
        should_prepare_github_handoff = False
        should_push = False
        should_invoke_codex = False
        should_execute_rollback = False
        should_commit = False
        should_tag = False
        should_stop = False
        stop_reason = ""
        human_review_required = False
        next_action = "prepare_next_cycle_or_github_readiness"

        if post_commit_dirty and not post_commit_expected_dirty_only:
            status = "commit_tag_result_assimilation_completed_with_unexpected_dirty"
            commit_tag_result_class = "completed_unexpected_dirty"
            commit_tag_result_block_reason = "unexpected_dirty_after_commit_tag"
            safe_post_commit_handoff = False
            post_commit_handoff_allowed = False
            post_commit_handoff_kind = "none"
            post_commit_handoff_source = authoritative_source_kind
            should_prepare_next_cycle = False
            should_prepare_github_handoff = False
            should_stop = True
            stop_reason = "unexpected_dirty_after_commit_tag"
            human_review_required = True
            next_action = "manual_review_required"
    elif (
        normalized_execution_status == "commit_tag_execution_partial_commit_tag_failed"
        or (bool(git_commit_completed) and not bool(git_tag_completed))
    ):
        status = "commit_tag_result_assimilation_partial_commit_tag_failed"
        commit_tag_result_available = True
        commit_tag_result_selected = True
        commit_tag_result_class = "partial_commit_tag_failed"
        commit_tag_result_block_reason = "commit_completed_but_tag_failed"
        commit_completed = bool(git_commit_completed)
        tag_completed = False
        partial_commit_without_tag = True
        commit_failed = False
        tag_failed = True
        commit_tag_timeout = False
        commit_tag_blocked = False
        safe_post_commit_handoff = False
        post_commit_handoff_allowed = False
        post_commit_handoff_kind = "none"
        post_commit_handoff_source = authoritative_source_kind
        should_prepare_next_cycle = False
        should_prepare_github_handoff = False
        should_push = False
        should_invoke_codex = False
        should_execute_rollback = False
        should_commit = False
        should_tag = False
        should_stop = True
        stop_reason = "commit_completed_but_tag_failed"
        human_review_required = True
        next_action = "manual_review_required"
    elif normalized_execution_status == "commit_tag_execution_failed_git_add":
        status = "commit_tag_result_assimilation_failed_git_add"
        commit_tag_result_available = True
        commit_tag_result_selected = True
        commit_tag_result_class = "failed_git_add"
        commit_tag_result_block_reason = "git_add_failed"
        commit_completed = False
        tag_completed = False
        partial_commit_without_tag = False
        commit_failed = True
        tag_failed = False
        commit_tag_timeout = False
        commit_tag_blocked = False
        safe_post_commit_handoff = False
        post_commit_handoff_allowed = False
        post_commit_handoff_kind = "none"
        post_commit_handoff_source = authoritative_source_kind
        should_stop = True
        stop_reason = "git_add_failed"
        human_review_required = True
        next_action = "manual_review_required"
    elif normalized_execution_status == "commit_tag_execution_failed_git_commit":
        status = "commit_tag_result_assimilation_failed_git_commit"
        commit_tag_result_available = True
        commit_tag_result_selected = True
        commit_tag_result_class = "failed_git_commit"
        commit_tag_result_block_reason = "git_commit_failed"
        commit_completed = False
        tag_completed = False
        partial_commit_without_tag = False
        commit_failed = True
        tag_failed = False
        commit_tag_timeout = False
        commit_tag_blocked = False
        safe_post_commit_handoff = False
        post_commit_handoff_allowed = False
        post_commit_handoff_kind = "none"
        post_commit_handoff_source = authoritative_source_kind
        should_stop = True
        stop_reason = "git_commit_failed"
        human_review_required = True
        next_action = "manual_review_required"
    elif normalized_execution_status == "commit_tag_execution_failed_git_tag":
        status = "commit_tag_result_assimilation_failed_git_tag"
        commit_tag_result_available = True
        commit_tag_result_selected = True
        commit_tag_result_class = "failed_git_tag"
        commit_tag_result_block_reason = "git_tag_failed"
        commit_completed = bool(git_commit_completed)
        tag_completed = False
        partial_commit_without_tag = bool(git_commit_completed)
        commit_failed = False
        tag_failed = True
        commit_tag_timeout = False
        commit_tag_blocked = False
        safe_post_commit_handoff = False
        post_commit_handoff_allowed = False
        post_commit_handoff_kind = "none"
        post_commit_handoff_source = authoritative_source_kind
        should_stop = True
        stop_reason = "git_tag_failed"
        human_review_required = True
        next_action = "manual_review_required"
    elif normalized_execution_status == "commit_tag_execution_timeout" or bool(timed_out):
        status = "commit_tag_result_assimilation_timeout"
        commit_tag_result_available = True
        commit_tag_result_selected = True
        commit_tag_result_class = "timeout"
        commit_tag_result_block_reason = "commit_tag_timeout"
        commit_completed = bool(git_commit_completed)
        tag_completed = bool(git_tag_completed)
        partial_commit_without_tag = bool(git_commit_completed and not git_tag_completed)
        commit_failed = bool(execution_failed)
        tag_failed = False
        commit_tag_timeout = True
        commit_tag_blocked = False
        safe_post_commit_handoff = False
        post_commit_handoff_allowed = False
        post_commit_handoff_kind = "none"
        post_commit_handoff_source = authoritative_source_kind
        should_stop = True
        stop_reason = "commit_tag_timeout"
        human_review_required = True
        next_action = "manual_review_required"
    elif normalized_execution_status.startswith("commit_tag_execution_blocked"):
        status = "commit_tag_result_assimilation_blocked"
        commit_tag_result_available = True
        commit_tag_result_selected = True
        commit_tag_result_class = "blocked"
        commit_tag_result_block_reason = (
            normalized_execution_block_reason or "commit_tag_execution_blocked"
        )
        commit_completed = bool(git_commit_completed)
        tag_completed = bool(git_tag_completed)
        partial_commit_without_tag = bool(git_commit_completed and not git_tag_completed)
        commit_failed = False
        tag_failed = False
        commit_tag_timeout = False
        commit_tag_blocked = True
        safe_post_commit_handoff = False
        post_commit_handoff_allowed = False
        post_commit_handoff_kind = "none"
        post_commit_handoff_source = authoritative_source_kind
        should_prepare_next_cycle = False
        should_prepare_github_handoff = False
        should_stop = bool(execution_human_review_required)
        stop_reason = normalized_execution_block_reason or "commit_tag_execution_blocked"
        human_review_required = bool(execution_human_review_required)
        next_action = (
            normalized_execution_next_action
            if normalized_execution_next_action
            else "manual_review_required"
        )
    else:
        status = "commit_tag_result_assimilation_blocked_insufficient_truth"
        commit_tag_result_available = False
        commit_tag_result_selected = False
        commit_tag_result_class = "insufficient_truth"
        commit_tag_result_block_reason = "blocked_insufficient_commit_tag_result_truth"
        safe_post_commit_handoff = False
        post_commit_handoff_allowed = False
        should_prepare_next_cycle = False
        should_prepare_github_handoff = False
        should_stop = True
        stop_reason = "insufficient_commit_tag_result_truth"
        human_review_required = True
        next_action = "manual_review_required"

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"
    if status == "insufficient_truth":
        commit_tag_result_available = False
        commit_tag_result_selected = False
        commit_tag_result_class = "insufficient_truth"
        commit_tag_result_block_reason = "blocked_insufficient_commit_tag_result_truth"
        commit_completed = False
        tag_completed = False
        partial_commit_without_tag = False
        commit_failed = False
        tag_failed = False
        commit_tag_timeout = False
        commit_tag_blocked = False
        safe_post_commit_handoff = False
        post_commit_handoff_allowed = False
        post_commit_handoff_kind = "none"
        post_commit_handoff_source = ""
        should_prepare_next_cycle = False
        should_prepare_github_handoff = False
        should_stop = True
        stop_reason = "insufficient_commit_tag_result_truth"
        human_review_required = True
        should_push = False
        should_invoke_codex = False
        should_execute_rollback = False
        should_commit = False
        should_tag = False

    return {
        "project_browser_autonomous_commit_tag_result_assimilation_status": status,
        "project_browser_autonomous_commit_tag_result_assimilation_commit_tag_result_available": bool(
            commit_tag_result_available
        ),
        "project_browser_autonomous_commit_tag_result_assimilation_commit_tag_result_selected": bool(
            commit_tag_result_selected
        ),
        "project_browser_autonomous_commit_tag_result_assimilation_commit_tag_result_class": (
            commit_tag_result_class
        ),
        "project_browser_autonomous_commit_tag_result_assimilation_commit_tag_result_block_reason": (
            commit_tag_result_block_reason
        ),
        "project_browser_autonomous_commit_tag_result_assimilation_commit_completed": bool(
            commit_completed
        ),
        "project_browser_autonomous_commit_tag_result_assimilation_tag_completed": bool(
            tag_completed
        ),
        "project_browser_autonomous_commit_tag_result_assimilation_commit_hash": normalized_commit_hash,
        "project_browser_autonomous_commit_tag_result_assimilation_tag_name": normalized_tag_name,
        "project_browser_autonomous_commit_tag_result_assimilation_commit_files": normalized_commit_files,
        "project_browser_autonomous_commit_tag_result_assimilation_commit_file_count": int(
            normalized_commit_file_count
        ),
        "project_browser_autonomous_commit_tag_result_assimilation_post_commit_git_status_short": (
            normalized_post_commit_git_status_short
        ),
        "project_browser_autonomous_commit_tag_result_assimilation_post_commit_dirty": bool(
            post_commit_dirty
        ),
        "project_browser_autonomous_commit_tag_result_assimilation_post_commit_expected_dirty_only": bool(
            post_commit_expected_dirty_only
        ),
        "project_browser_autonomous_commit_tag_result_assimilation_partial_commit_without_tag": bool(
            partial_commit_without_tag
        ),
        "project_browser_autonomous_commit_tag_result_assimilation_commit_failed": bool(
            commit_failed
        ),
        "project_browser_autonomous_commit_tag_result_assimilation_tag_failed": bool(
            tag_failed
        ),
        "project_browser_autonomous_commit_tag_result_assimilation_commit_tag_timeout": bool(
            commit_tag_timeout
        ),
        "project_browser_autonomous_commit_tag_result_assimilation_commit_tag_blocked": bool(
            commit_tag_blocked
        ),
        "project_browser_autonomous_commit_tag_result_assimilation_safe_post_commit_handoff": bool(
            safe_post_commit_handoff
        ),
        "project_browser_autonomous_commit_tag_result_assimilation_post_commit_handoff_allowed": bool(
            post_commit_handoff_allowed
        ),
        "project_browser_autonomous_commit_tag_result_assimilation_post_commit_handoff_kind": (
            post_commit_handoff_kind
        ),
        "project_browser_autonomous_commit_tag_result_assimilation_post_commit_handoff_source": (
            post_commit_handoff_source
        ),
        "project_browser_autonomous_commit_tag_result_assimilation_should_prepare_next_cycle": bool(
            should_prepare_next_cycle
        ),
        "project_browser_autonomous_commit_tag_result_assimilation_should_prepare_github_handoff": bool(
            should_prepare_github_handoff
        ),
        "project_browser_autonomous_commit_tag_result_assimilation_should_push": bool(should_push),
        "project_browser_autonomous_commit_tag_result_assimilation_should_invoke_codex": bool(
            should_invoke_codex
        ),
        "project_browser_autonomous_commit_tag_result_assimilation_should_execute_rollback": bool(
            should_execute_rollback
        ),
        "project_browser_autonomous_commit_tag_result_assimilation_should_commit": bool(
            should_commit
        ),
        "project_browser_autonomous_commit_tag_result_assimilation_should_tag": bool(should_tag),
        "project_browser_autonomous_commit_tag_result_assimilation_should_stop": bool(should_stop),
        "project_browser_autonomous_commit_tag_result_assimilation_stop_reason": stop_reason,
        "project_browser_autonomous_commit_tag_result_assimilation_human_review_required": bool(
            human_review_required
        ),
        "project_browser_autonomous_commit_tag_result_assimilation_next_action": next_action,
        "project_browser_autonomous_commit_tag_result_assimilation_runtime_posture": runtime_posture,
        "project_browser_autonomous_commit_tag_result_assimilation_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_execution_status,
                    normalized_execution_block_reason,
                    normalized_commit_source,
                    normalized_execution_next_action,
                    normalized_readiness_status,
                    normalized_readiness_next_action,
                    normalized_source_assimilation_status,
                    normalized_source_next_action,
                    normalized_continuation_status,
                    normalized_continuation_next_action,
                    "execution_not_attempted" if not execution_attempted else "",
                    "execution_not_completed" if not execution_completed else "",
                    "execution_failed_true" if execution_failed else "",
                    "tag_collision_detected" if False else "",
                    "commit_hash_missing_on_complete"
                    if (
                        normalized_execution_status == "commit_tag_execution_completed"
                        and not normalized_commit_hash
                    )
                    else "",
                    "tag_name_missing_on_complete"
                    if (
                        normalized_execution_status == "commit_tag_execution_completed"
                        and not normalized_tag_name
                    )
                    else "",
                    *missing_inputs,
                ]
            )
        ),
    }

def _build_project_browser_autonomous_selected_lane_result_assimilation_state(
    *,
    selected_lane_execution_status: str,
    selected_lane: str,
    selected_lane_action: str,
    execution_allowed: bool,
    execution_attempted: bool,
    execution_completed: bool,
    execution_failed: bool,
    execution_block_reason: str,
    execution_source: str,
    non_selected_lanes_noop: bool,
    next_prompt_lane_executed: bool,
    fix_prompt_lane_executed: bool,
    rollback_readiness_lane_executed: bool,
    commit_readiness_lane_executed: bool,
    manual_stop_executed: bool,
    generated_prompt_kind: str,
    generated_prompt_path: str,
    generated_prompt_ready_for_reentry: bool,
    rollback_readiness_ready: bool,
    commit_readiness_ready: bool,
    execution_result_class: str,
    selected_action_result_ready_for_assimilation: bool,
    selected_action_result_assimilation_source: str,
    selected_action_result_next_stage: str,
    execution_manual_review_required: bool,
    execution_should_stop: bool,
    execution_stop_reason: str,
    execution_next_action: str,
    guarded_dispatch_status: str,
    lane_contract_guard_status: str,
    terminal_lane_status: str,
    multi_cycle_controller_status: str,
    generated_prompt_reentry_readiness_status: str,
    generated_prompt_reentry_routing_status: str,
    rollback_readiness_status: str,
    commit_readiness_status: str,
) -> dict[str, Any]:
    allowed_statuses = {
        "selected_lane_result_next_prompt_completed",
        "selected_lane_result_fix_prompt_completed",
        "selected_lane_result_rollback_readiness_completed",
        "selected_lane_result_commit_readiness_completed",
        "selected_lane_result_manual_stop",
        "selected_lane_result_failed",
        "selected_lane_result_blocked",
        "selected_lane_result_blocked_non_selected_lane_activity",
        "selected_lane_result_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_result_classes = {
        "next_prompt_generation_completed",
        "fix_prompt_generation_completed",
        "rollback_readiness_completed",
        "commit_readiness_completed",
        "manual_stop",
        "blocked",
        "failed",
        "insufficient_truth",
        "blocked_non_selected_lane_activity",
    }
    allowed_next_actions = {
        "prepare_generated_prompt_reentry",
        "prepare_rollback_execution",
        "prepare_commit_execution",
        "manual_review_required",
        "insufficient_truth",
    }
    runtime_posture = [
        "prompt202_selected_lane_result_assimilation",
        "metadata_only",
        "controller_feedback_only",
        "no_execution",
        "no_codex_invocation",
        "no_validation_execution",
        "no_rollback_execution",
        "no_git_mutation",
        "no_push",
    ]

    normalized_selected_lane_execution_status = _normalize_text(
        selected_lane_execution_status,
        default="insufficient_truth",
    )
    normalized_selected_lane = _normalize_text(selected_lane, default="")
    normalized_selected_lane_action = _normalize_text(selected_lane_action, default="")
    normalized_execution_block_reason = _normalize_text(execution_block_reason, default="")
    normalized_execution_source = _normalize_text(execution_source, default="")
    normalized_generated_prompt_kind = _normalize_text(generated_prompt_kind, default="none")
    normalized_generated_prompt_path = _normalize_text(generated_prompt_path, default="")
    normalized_execution_result_class = _normalize_text(execution_result_class, default="blocked")
    normalized_assimilation_source = _normalize_text(
        selected_action_result_assimilation_source,
        default="",
    )
    normalized_assimilation_next_stage = _normalize_text(
        selected_action_result_next_stage,
        default="",
    )
    normalized_execution_stop_reason = _normalize_text(execution_stop_reason, default="")
    normalized_execution_next_action = _normalize_text(execution_next_action, default="")
    normalized_guarded_dispatch_status = _normalize_text(
        guarded_dispatch_status, default="insufficient_truth"
    )
    normalized_lane_contract_guard_status = _normalize_text(
        lane_contract_guard_status, default="insufficient_truth"
    )
    normalized_terminal_lane_status = _normalize_text(terminal_lane_status, default="insufficient_truth")
    normalized_multi_cycle_controller_status = _normalize_text(
        multi_cycle_controller_status, default="insufficient_truth"
    )
    normalized_generated_prompt_reentry_readiness_status = _normalize_text(
        generated_prompt_reentry_readiness_status, default="insufficient_truth"
    )
    normalized_generated_prompt_reentry_routing_status = _normalize_text(
        generated_prompt_reentry_routing_status, default="insufficient_truth"
    )
    normalized_rollback_readiness_status = _normalize_text(
        rollback_readiness_status, default="insufficient_truth"
    )
    normalized_commit_readiness_status = _normalize_text(
        commit_readiness_status, default="insufficient_truth"
    )

    authoritative_result_selected = bool(
        bool(selected_action_result_ready_for_assimilation)
        and normalized_assimilation_source == "prompt201_selected_lane_execution"
        and normalized_assimilation_next_stage == "selected_lane_result_assimilation"
        and bool(normalized_selected_lane)
        and (
            bool(normalized_execution_result_class)
            or bool(normalized_selected_lane_execution_status)
        )
    )
    result_available = bool(
        bool(normalized_selected_lane_execution_status) and normalized_selected_lane_execution_status != "insufficient_truth"
    ) or bool(normalized_execution_result_class)
    non_stop_lane = normalized_selected_lane in {
        "next_prompt_lane",
        "fix_prompt_lane",
        "rollback_readiness_lane",
        "commit_readiness_lane",
    }

    status = "selected_lane_result_blocked_insufficient_truth"
    result_selected = False
    result_class = "insufficient_truth"
    result_block_reason = "blocked_insufficient_selected_lane_result_truth"
    source_execution_status = normalized_selected_lane_execution_status
    source_execution_completed = bool(execution_completed)
    source_execution_failed = bool(execution_failed)
    non_selected_lanes_noop_confirmed = bool(non_selected_lanes_noop)
    out_generated_prompt_kind = "none"
    out_generated_prompt_path = ""
    out_generated_prompt_ready_for_reentry = False
    out_rollback_readiness_ready = False
    out_commit_readiness_ready = False
    controller_feedback_ready = False
    controller_feedback_kind = "none"
    controller_feedback_source = ""
    controller_feedback_payload: dict[str, Any] = {}
    next_controller_input_ready = False
    next_controller_input_kind = "none"
    next_controller_input_source = ""
    next_controller_action_hint = "manual_review_required"
    should_prepare_generated_prompt_reentry = False
    should_prepare_codex_reentry = False
    should_prepare_rollback_execution = False
    should_prepare_commit_execution = False
    should_prepare_next_controller_decision = False
    out_should_invoke_codex = False
    out_should_execute_rollback = False
    out_should_execute_commit = False
    out_should_push = False
    out_manual_review_required = True
    out_should_stop = True
    out_stop_reason = normalized_execution_stop_reason or "insufficient_selected_lane_result_truth"
    out_next_action = "manual_review_required"

    if not authoritative_result_selected:
        status = "selected_lane_result_blocked_insufficient_truth"
        result_selected = False
        result_class = "insufficient_truth"
        result_block_reason = "blocked_insufficient_selected_lane_result_truth"
    elif non_stop_lane and not bool(non_selected_lanes_noop):
        status = "selected_lane_result_blocked_non_selected_lane_activity"
        result_selected = True
        result_class = "blocked_non_selected_lane_activity"
        result_block_reason = "blocked_non_selected_lane_activity"
        source_execution_completed = bool(execution_completed)
        source_execution_failed = bool(execution_failed)
        non_selected_lanes_noop_confirmed = False
        controller_feedback_ready = True
        controller_feedback_kind = "selected_lane_blocked"
        controller_feedback_source = "prompt201_selected_lane_execution"
        next_controller_input_ready = True
        next_controller_input_kind = "stop_or_manual_review"
        next_controller_input_source = "prompt202_selected_lane_result_assimilation"
        next_controller_action_hint = "manual_review_required"
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "blocked_non_selected_lane_activity"
        out_next_action = "manual_review_required"
    elif (
        normalized_selected_lane == "next_prompt_lane"
        and bool(next_prompt_lane_executed)
        and bool(execution_completed)
        and normalized_generated_prompt_kind == "next"
        and bool(generated_prompt_ready_for_reentry)
        and bool(normalized_generated_prompt_path)
    ):
        status = "selected_lane_result_next_prompt_completed"
        result_selected = True
        result_class = "next_prompt_generation_completed"
        result_block_reason = ""
        out_generated_prompt_kind = "next"
        out_generated_prompt_path = normalized_generated_prompt_path
        out_generated_prompt_ready_for_reentry = True
        controller_feedback_ready = True
        controller_feedback_kind = "generated_prompt_ready"
        controller_feedback_source = "prompt201_selected_lane_execution"
        controller_feedback_payload = {
            "feedback": "generated_prompt_ready",
            "prompt_kind": "next",
            "prompt_path": normalized_generated_prompt_path,
            "source": "prompt201_selected_lane_execution",
            "next_action": "prepare_generated_prompt_reentry",
        }
        next_controller_input_ready = True
        next_controller_input_kind = "generated_next_prompt_ready_for_reentry"
        next_controller_input_source = "prompt202_selected_lane_result_assimilation"
        next_controller_action_hint = "prepare_generated_prompt_reentry"
        should_prepare_generated_prompt_reentry = True
        should_prepare_codex_reentry = False
        should_prepare_next_controller_decision = False
        out_manual_review_required = False
        out_should_stop = False
        out_stop_reason = ""
        out_next_action = "prepare_generated_prompt_reentry"
    elif (
        normalized_selected_lane == "fix_prompt_lane"
        and bool(fix_prompt_lane_executed)
        and bool(execution_completed)
        and normalized_generated_prompt_kind == "fix"
        and bool(generated_prompt_ready_for_reentry)
        and bool(normalized_generated_prompt_path)
    ):
        status = "selected_lane_result_fix_prompt_completed"
        result_selected = True
        result_class = "fix_prompt_generation_completed"
        result_block_reason = ""
        out_generated_prompt_kind = "fix"
        out_generated_prompt_path = normalized_generated_prompt_path
        out_generated_prompt_ready_for_reentry = True
        controller_feedback_ready = True
        controller_feedback_kind = "generated_prompt_ready"
        controller_feedback_source = "prompt201_selected_lane_execution"
        controller_feedback_payload = {
            "feedback": "generated_prompt_ready",
            "prompt_kind": "fix",
            "prompt_path": normalized_generated_prompt_path,
            "source": "prompt201_selected_lane_execution",
            "next_action": "prepare_generated_prompt_reentry",
        }
        next_controller_input_ready = True
        next_controller_input_kind = "generated_fix_prompt_ready_for_reentry"
        next_controller_input_source = "prompt202_selected_lane_result_assimilation"
        next_controller_action_hint = "prepare_generated_prompt_reentry"
        should_prepare_generated_prompt_reentry = True
        should_prepare_codex_reentry = False
        should_prepare_next_controller_decision = False
        out_manual_review_required = False
        out_should_stop = False
        out_stop_reason = ""
        out_next_action = "prepare_generated_prompt_reentry"
    elif (
        normalized_selected_lane == "rollback_readiness_lane"
        and bool(rollback_readiness_lane_executed)
        and bool(execution_completed)
        and bool(rollback_readiness_ready)
    ):
        status = "selected_lane_result_rollback_readiness_completed"
        result_selected = True
        result_class = "rollback_readiness_completed"
        result_block_reason = ""
        out_rollback_readiness_ready = True
        controller_feedback_ready = True
        controller_feedback_kind = "rollback_readiness_ready"
        controller_feedback_source = "prompt201_selected_lane_execution"
        controller_feedback_payload = {
            "feedback": "rollback_readiness_ready",
            "source": "prompt201_selected_lane_execution",
            "next_action": "prepare_rollback_execution",
        }
        next_controller_input_ready = True
        next_controller_input_kind = "rollback_execution_ready"
        next_controller_input_source = "prompt202_selected_lane_result_assimilation"
        next_controller_action_hint = "prepare_rollback_execution"
        should_prepare_rollback_execution = True
        should_prepare_next_controller_decision = False
        out_manual_review_required = False
        out_should_stop = False
        out_stop_reason = ""
        out_next_action = "prepare_rollback_execution"
    elif (
        normalized_selected_lane == "commit_readiness_lane"
        and bool(commit_readiness_lane_executed)
        and bool(execution_completed)
        and bool(commit_readiness_ready)
    ):
        status = "selected_lane_result_commit_readiness_completed"
        result_selected = True
        result_class = "commit_readiness_completed"
        result_block_reason = ""
        out_commit_readiness_ready = True
        controller_feedback_ready = True
        controller_feedback_kind = "commit_readiness_ready"
        controller_feedback_source = "prompt201_selected_lane_execution"
        controller_feedback_payload = {
            "feedback": "commit_readiness_ready",
            "source": "prompt201_selected_lane_execution",
            "next_action": "prepare_commit_execution",
        }
        next_controller_input_ready = True
        next_controller_input_kind = "commit_execution_ready"
        next_controller_input_source = "prompt202_selected_lane_result_assimilation"
        next_controller_action_hint = "prepare_commit_execution"
        should_prepare_commit_execution = True
        should_prepare_next_controller_decision = False
        out_manual_review_required = False
        out_should_stop = False
        out_stop_reason = ""
        out_next_action = "prepare_commit_execution"
    elif normalized_selected_lane == "manual_stop_lane" or bool(manual_stop_executed):
        status = "selected_lane_result_manual_stop"
        result_selected = True
        result_class = "manual_stop"
        result_block_reason = ""
        controller_feedback_ready = True
        controller_feedback_kind = "manual_stop"
        controller_feedback_source = "prompt201_selected_lane_execution"
        out_stop_reason = normalized_execution_stop_reason or "manual_stop_lane_selected"
        controller_feedback_payload = {
            "feedback": "manual_stop",
            "source": "prompt201_selected_lane_execution",
            "stop_reason": out_stop_reason,
            "next_action": "manual_review_required",
        }
        next_controller_input_ready = True
        next_controller_input_kind = "stop"
        next_controller_input_source = "prompt202_selected_lane_result_assimilation"
        next_controller_action_hint = "manual_review_required"
        should_prepare_next_controller_decision = False
        out_manual_review_required = True
        out_should_stop = True
        out_next_action = "manual_review_required"
    elif bool(execution_failed) or normalized_selected_lane_execution_status == "selected_lane_execution_failed":
        status = "selected_lane_result_failed"
        result_selected = True
        result_class = "failed"
        result_block_reason = normalized_execution_block_reason or "selected_lane_execution_failed"
        controller_feedback_ready = True
        controller_feedback_kind = "selected_lane_failed"
        controller_feedback_source = "prompt201_selected_lane_execution"
        out_stop_reason = normalized_execution_block_reason or "selected_lane_execution_failed"
        controller_feedback_payload = {
            "feedback": "selected_lane_failed",
            "source": "prompt201_selected_lane_execution",
            "stop_reason": out_stop_reason,
            "next_action": "manual_review_required",
        }
        next_controller_input_ready = True
        next_controller_input_kind = "stop_or_manual_review"
        next_controller_input_source = "prompt202_selected_lane_result_assimilation"
        next_controller_action_hint = "manual_review_required"
        out_manual_review_required = True
        out_should_stop = True
        out_next_action = "manual_review_required"
    elif "blocked" in normalized_selected_lane_execution_status:
        status = "selected_lane_result_blocked"
        result_selected = True
        result_class = "blocked"
        result_block_reason = normalized_execution_block_reason or "selected_lane_execution_blocked"
        controller_feedback_ready = True
        controller_feedback_kind = "selected_lane_blocked"
        controller_feedback_source = "prompt201_selected_lane_execution"
        out_stop_reason = normalized_execution_block_reason or "selected_lane_execution_blocked"
        controller_feedback_payload = {
            "feedback": "selected_lane_blocked",
            "source": "prompt201_selected_lane_execution",
            "stop_reason": out_stop_reason,
            "next_action": "manual_review_required",
        }
        next_controller_input_ready = True
        next_controller_input_kind = "stop_or_manual_review"
        next_controller_input_source = "prompt202_selected_lane_result_assimilation"
        next_controller_action_hint = "manual_review_required"
        out_manual_review_required = True
        out_should_stop = True
        out_next_action = "manual_review_required"
    else:
        status = "selected_lane_result_blocked_insufficient_truth"
        result_selected = True
        result_class = "insufficient_truth"
        result_block_reason = "blocked_insufficient_selected_lane_result_truth"
        controller_feedback_ready = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_selected_lane_result_truth"
        out_next_action = "manual_review_required"

    if result_selected and not controller_feedback_source:
        controller_feedback_source = "prompt201_selected_lane_execution"
    if result_selected and not controller_feedback_payload:
        controller_feedback_payload = {
            "feedback": controller_feedback_kind or "selected_lane_blocked",
            "source": "prompt201_selected_lane_execution",
            "stop_reason": out_stop_reason,
            "next_action": "manual_review_required",
        }

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if result_class not in allowed_result_classes:
        result_class = "insufficient_truth"
    if out_next_action not in allowed_next_actions:
        out_next_action = "insufficient_truth"
    if status == "insufficient_truth":
        status = "selected_lane_result_blocked_insufficient_truth"
        result_selected = False
        result_available = False
        result_class = "insufficient_truth"
        result_block_reason = "blocked_insufficient_selected_lane_result_truth"
        source_execution_completed = False
        source_execution_failed = False
        non_selected_lanes_noop_confirmed = False
        out_generated_prompt_kind = "none"
        out_generated_prompt_path = ""
        out_generated_prompt_ready_for_reentry = False
        out_rollback_readiness_ready = False
        out_commit_readiness_ready = False
        controller_feedback_ready = False
        controller_feedback_kind = "none"
        controller_feedback_source = ""
        controller_feedback_payload = {}
        next_controller_input_ready = False
        next_controller_input_kind = "none"
        next_controller_input_source = ""
        next_controller_action_hint = "manual_review_required"
        should_prepare_generated_prompt_reentry = False
        should_prepare_codex_reentry = False
        should_prepare_rollback_execution = False
        should_prepare_commit_execution = False
        should_prepare_next_controller_decision = False
        out_should_invoke_codex = False
        out_should_execute_rollback = False
        out_should_execute_commit = False
        out_should_push = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_selected_lane_result_truth"
        out_next_action = "manual_review_required"

    return {
        "project_browser_autonomous_selected_lane_result_assimilation_status": status,
        "project_browser_autonomous_selected_lane_result_assimilation_result_selected": bool(
            result_selected
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_result_available": bool(
            result_available
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_result_class": result_class,
        "project_browser_autonomous_selected_lane_result_assimilation_result_block_reason": (
            result_block_reason
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_source_selected_lane": (
            normalized_selected_lane
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_source_selected_lane_action": (
            normalized_selected_lane_action
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_source_execution_status": (
            source_execution_status
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_source_execution_completed": bool(
            source_execution_completed
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_source_execution_failed": bool(
            source_execution_failed
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_non_selected_lanes_noop_confirmed": bool(
            non_selected_lanes_noop_confirmed
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_generated_prompt_kind": (
            out_generated_prompt_kind
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_generated_prompt_path": (
            out_generated_prompt_path
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_generated_prompt_ready_for_reentry": bool(
            out_generated_prompt_ready_for_reentry
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_rollback_readiness_ready": bool(
            out_rollback_readiness_ready
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_commit_readiness_ready": bool(
            out_commit_readiness_ready
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_controller_feedback_ready": bool(
            controller_feedback_ready
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_controller_feedback_kind": (
            controller_feedback_kind
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_controller_feedback_source": (
            controller_feedback_source
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_controller_feedback_payload": (
            controller_feedback_payload if isinstance(controller_feedback_payload, Mapping) else {}
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_next_controller_input_ready": bool(
            next_controller_input_ready
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_next_controller_input_kind": (
            next_controller_input_kind
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_next_controller_input_source": (
            next_controller_input_source
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_next_controller_action_hint": (
            next_controller_action_hint
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_should_prepare_generated_prompt_reentry": bool(
            should_prepare_generated_prompt_reentry
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_should_prepare_codex_reentry": bool(
            should_prepare_codex_reentry
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_should_prepare_rollback_execution": bool(
            should_prepare_rollback_execution
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_should_prepare_commit_execution": bool(
            should_prepare_commit_execution
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_should_prepare_next_controller_decision": bool(
            should_prepare_next_controller_decision
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_should_invoke_codex": bool(
            out_should_invoke_codex
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_should_execute_rollback": bool(
            out_should_execute_rollback
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_should_execute_commit": bool(
            out_should_execute_commit
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_should_push": bool(
            out_should_push
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_manual_review_required": bool(
            out_manual_review_required
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_should_stop": bool(
            out_should_stop
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_stop_reason": out_stop_reason,
        "project_browser_autonomous_selected_lane_result_assimilation_next_action": out_next_action,
        "project_browser_autonomous_selected_lane_result_assimilation_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_selected_lane_result_assimilation_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_selected_lane_execution_status,
                    normalized_selected_lane,
                    normalized_selected_lane_action,
                    normalized_execution_block_reason,
                    normalized_execution_source,
                    normalized_generated_prompt_kind,
                    normalized_generated_prompt_path,
                    normalized_execution_result_class,
                    normalized_assimilation_source,
                    normalized_assimilation_next_stage,
                    normalized_execution_stop_reason,
                    normalized_execution_next_action,
                    normalized_guarded_dispatch_status,
                    normalized_lane_contract_guard_status,
                    normalized_terminal_lane_status,
                    normalized_multi_cycle_controller_status,
                    normalized_generated_prompt_reentry_readiness_status,
                    normalized_generated_prompt_reentry_routing_status,
                    normalized_rollback_readiness_status,
                    normalized_commit_readiness_status,
                    "authoritative_result_not_selected"
                    if not authoritative_result_selected
                    else "",
                    "selected_action_result_not_ready"
                    if not bool(selected_action_result_ready_for_assimilation)
                    else "",
                    "non_selected_lanes_noop_false"
                    if non_stop_lane and not bool(non_selected_lanes_noop)
                    else "",
                ]
            )
        ),
    }

def _build_project_browser_autonomous_next_step_launch_result_assimilation_state(
    *,
    next_step_launch_execution_status: str,
    launch_execution_allowed: bool,
    launch_execution_attempted: bool,
    launch_execution_completed: bool,
    launch_execution_failed: bool,
    launch_execution_block_reason: str,
    launch_execution_source: str,
    selected_launch_kind: str,
    selected_launch_action: str,
    selected_launch_payload: Any,
    non_selected_launches_noop: bool,
    generated_prompt_reentry_launch_executed: bool,
    rollback_execution_launch_executed: bool,
    commit_execution_launch_executed: bool,
    manual_stop_launch_executed: bool,
    delegated_existing_path: bool,
    delegated_existing_path_kind: str,
    delegated_existing_status: str,
    delegated_existing_next_action: str,
    generated_prompt_reentry_result_status: str,
    rollback_execution_result_status: str,
    commit_execution_result_status: str,
    launch_execution_result_class: str,
    next_step_launch_result_ready_for_assimilation: bool,
    next_step_launch_result_assimilation_source: str,
    next_step_launch_result_next_stage: str,
    launch_execution_should_invoke_codex: bool,
    launch_execution_should_execute_rollback: bool,
    launch_execution_should_execute_commit: bool,
    launch_execution_should_push: bool,
    launch_execution_manual_review_required: bool,
    launch_execution_should_stop: bool,
    launch_execution_stop_reason: str,
    launch_execution_next_action: str,
    next_step_launch_contract_status: str,
    bounded_local_loop_contract_status: str,
    multi_cycle_controller_status: str,
    reentry_result_assimilation_status: str,
    rollback_result_assimilation_status: str,
    commit_tag_result_assimilation_status: str,
) -> dict[str, Any]:
    allowed_statuses = {
        "next_step_launch_result_generated_prompt_reentry_completed",
        "next_step_launch_result_rollback_execution_completed",
        "next_step_launch_result_commit_execution_completed",
        "next_step_launch_result_manual_stop",
        "next_step_launch_result_failed",
        "next_step_launch_result_blocked",
        "next_step_launch_result_blocked_non_selected_launch_activity",
        "next_step_launch_result_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_result_classes = {
        "generated_prompt_reentry_completed",
        "rollback_execution_completed",
        "commit_execution_completed",
        "manual_stop",
        "blocked",
        "failed",
        "insufficient_truth",
        "blocked_non_selected_launch_activity",
    }
    allowed_next_actions = {
        "prepare_reentry_result_assimilation",
        "prepare_rollback_result_assimilation",
        "prepare_commit_result_assimilation",
        "manual_review_required",
        "insufficient_truth",
    }
    runtime_posture = [
        "prompt206_next_step_launch_result_assimilation",
        "metadata_only",
        "no_additional_launch_execution",
        "no_codex_invocation",
        "no_validation_execution",
        "no_rollback_execution",
        "no_commit_execution",
        "no_push",
    ]

    normalized_execution_status = _normalize_text(
        next_step_launch_execution_status,
        default="insufficient_truth",
    )
    normalized_execution_block_reason = _normalize_text(
        launch_execution_block_reason,
        default="",
    )
    normalized_execution_source = _normalize_text(
        launch_execution_source,
        default="prompt205_next_step_launch_execution",
    )
    normalized_selected_launch_kind = _normalize_text(selected_launch_kind, default="")
    normalized_selected_launch_action = _normalize_text(
        selected_launch_action,
        default="manual_review_required",
    )
    normalized_delegated_existing_path_kind = _normalize_text(
        delegated_existing_path_kind,
        default="none",
    )
    normalized_delegated_existing_status = _normalize_text(
        delegated_existing_status,
        default="insufficient_truth",
    )
    normalized_delegated_existing_next_action = _normalize_text(
        delegated_existing_next_action,
        default="manual_review_required",
    )
    normalized_generated_prompt_reentry_result_status = _normalize_text(
        generated_prompt_reentry_result_status,
        default="",
    )
    normalized_rollback_execution_result_status = _normalize_text(
        rollback_execution_result_status,
        default="",
    )
    normalized_commit_execution_result_status = _normalize_text(
        commit_execution_result_status,
        default="",
    )
    normalized_launch_execution_result_class = _normalize_text(
        launch_execution_result_class,
        default="blocked",
    )
    normalized_assimilation_source = _normalize_text(
        next_step_launch_result_assimilation_source,
        default="",
    )
    normalized_assimilation_next_stage = _normalize_text(
        next_step_launch_result_next_stage,
        default="",
    )
    normalized_stop_reason = _normalize_text(launch_execution_stop_reason, default="")
    normalized_execution_next_action = _normalize_text(
        launch_execution_next_action,
        default="manual_review_required",
    )
    normalized_next_step_launch_contract_status = _normalize_text(
        next_step_launch_contract_status,
        default="insufficient_truth",
    )
    normalized_bounded_local_loop_contract_status = _normalize_text(
        bounded_local_loop_contract_status,
        default="insufficient_truth",
    )
    normalized_multi_cycle_controller_status = _normalize_text(
        multi_cycle_controller_status,
        default="insufficient_truth",
    )
    normalized_reentry_result_assimilation_status = _normalize_text(
        reentry_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_rollback_result_assimilation_status = _normalize_text(
        rollback_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_commit_tag_result_assimilation_status = _normalize_text(
        commit_tag_result_assimilation_status,
        default="insufficient_truth",
    )

    _normalized_selected_launch_payload = (
        dict(selected_launch_payload) if isinstance(selected_launch_payload, Mapping) else {}
    )

    authoritative_selected = bool(
        bool(next_step_launch_result_ready_for_assimilation)
        and normalized_assimilation_source == "prompt205_next_step_launch_execution"
        and normalized_assimilation_next_stage == "next_step_launch_result_assimilation"
        and bool(normalized_selected_launch_kind)
        and bool(
            normalized_execution_status != "insufficient_truth"
            or normalized_launch_execution_result_class != "blocked"
        )
    )

    status = "next_step_launch_result_blocked_insufficient_truth"
    result_selected = False
    result_available = False
    result_class = "insufficient_truth"
    result_block_reason = "blocked_insufficient_next_step_launch_result_truth"
    source_execution_status = normalized_execution_status
    source_execution_completed = bool(launch_execution_completed)
    source_execution_failed = bool(launch_execution_failed)
    non_selected_launches_noop_confirmed = bool(non_selected_launches_noop)
    controller_feedback_ready = False
    controller_feedback_kind = "none"
    controller_feedback_source = ""
    controller_feedback_payload: dict[str, Any] = {}
    next_controller_input_ready = False
    next_controller_input_kind = "none"
    next_controller_input_source = ""
    next_controller_action_hint = "manual_review_required"
    should_continue_local_loop = False
    should_prepare_reentry_result_assimilation = False
    should_prepare_rollback_result_assimilation = False
    should_prepare_commit_result_assimilation = False
    should_prepare_next_controller_decision = False
    out_should_invoke_codex = False
    out_should_execute_rollback = False
    out_should_execute_commit = False
    out_should_push = False
    out_manual_review_required = True
    out_should_stop = True
    out_stop_reason = normalized_stop_reason or "insufficient_next_step_launch_result_truth"
    out_next_action = "manual_review_required"

    non_stop_selected_launch = normalized_selected_launch_kind in {
        "generated_prompt_reentry_launch",
        "rollback_execution_launch",
        "commit_execution_launch",
    }
    if non_stop_selected_launch and not bool(non_selected_launches_noop):
        status = "next_step_launch_result_blocked_non_selected_launch_activity"
        result_selected = True
        result_available = True
        result_class = "blocked_non_selected_launch_activity"
        result_block_reason = "blocked_non_selected_launch_activity"
        controller_feedback_ready = True
        controller_feedback_kind = "next_step_launch_blocked"
        controller_feedback_source = "prompt205_next_step_launch_execution"
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "non_selected_launch_activity_detected"
        out_next_action = "manual_review_required"
    elif not authoritative_selected:
        status = "next_step_launch_result_blocked_insufficient_truth"
        result_selected = False
        result_available = False
        result_class = "insufficient_truth"
        result_block_reason = "blocked_insufficient_next_step_launch_result_truth"
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_next_step_launch_result_truth"
        out_next_action = "manual_review_required"
    elif (
        normalized_selected_launch_kind == "generated_prompt_reentry_launch"
        and bool(generated_prompt_reentry_launch_executed)
        and bool(launch_execution_completed)
        and normalized_delegated_existing_path_kind == "generated_prompt_reentry"
        and bool(normalized_delegated_existing_status)
    ):
        status = "next_step_launch_result_generated_prompt_reentry_completed"
        result_selected = True
        result_available = True
        result_class = "generated_prompt_reentry_completed"
        result_block_reason = ""
        controller_feedback_ready = True
        controller_feedback_kind = "generated_prompt_reentry_result_ready"
        controller_feedback_source = "prompt205_next_step_launch_execution"
        controller_feedback_payload = {
            "feedback": "generated_prompt_reentry_result_ready",
            "source": "prompt205_next_step_launch_execution",
            "delegated_existing_status": normalized_delegated_existing_status,
            "next_action": "prepare_reentry_result_assimilation",
        }
        next_controller_input_ready = True
        next_controller_input_kind = "reentry_result_assimilation_ready"
        next_controller_input_source = "prompt206_next_step_launch_result_assimilation"
        next_controller_action_hint = "prepare_reentry_result_assimilation"
        should_prepare_reentry_result_assimilation = True
        should_prepare_next_controller_decision = False
        out_manual_review_required = False
        out_should_stop = False
        out_stop_reason = ""
        out_next_action = "prepare_reentry_result_assimilation"
    elif (
        normalized_selected_launch_kind == "rollback_execution_launch"
        and bool(rollback_execution_launch_executed)
        and bool(launch_execution_completed)
        and normalized_delegated_existing_path_kind == "rollback_execution"
        and bool(normalized_delegated_existing_status)
    ):
        status = "next_step_launch_result_rollback_execution_completed"
        result_selected = True
        result_available = True
        result_class = "rollback_execution_completed"
        result_block_reason = ""
        controller_feedback_ready = True
        controller_feedback_kind = "rollback_execution_result_ready"
        controller_feedback_source = "prompt205_next_step_launch_execution"
        controller_feedback_payload = {
            "feedback": "rollback_execution_result_ready",
            "source": "prompt205_next_step_launch_execution",
            "delegated_existing_status": normalized_delegated_existing_status,
            "next_action": "prepare_rollback_result_assimilation",
        }
        next_controller_input_ready = True
        next_controller_input_kind = "rollback_result_assimilation_ready"
        next_controller_input_source = "prompt206_next_step_launch_result_assimilation"
        next_controller_action_hint = "prepare_rollback_result_assimilation"
        should_prepare_rollback_result_assimilation = True
        should_prepare_next_controller_decision = False
        out_manual_review_required = False
        out_should_stop = False
        out_stop_reason = ""
        out_next_action = "prepare_rollback_result_assimilation"
    elif (
        normalized_selected_launch_kind == "commit_execution_launch"
        and bool(commit_execution_launch_executed)
        and bool(launch_execution_completed)
        and normalized_delegated_existing_path_kind == "commit_execution"
        and bool(normalized_delegated_existing_status)
    ):
        status = "next_step_launch_result_commit_execution_completed"
        result_selected = True
        result_available = True
        result_class = "commit_execution_completed"
        result_block_reason = ""
        controller_feedback_ready = True
        controller_feedback_kind = "commit_execution_result_ready"
        controller_feedback_source = "prompt205_next_step_launch_execution"
        controller_feedback_payload = {
            "feedback": "commit_execution_result_ready",
            "source": "prompt205_next_step_launch_execution",
            "delegated_existing_status": normalized_delegated_existing_status,
            "next_action": "prepare_commit_result_assimilation",
        }
        next_controller_input_ready = True
        next_controller_input_kind = "commit_result_assimilation_ready"
        next_controller_input_source = "prompt206_next_step_launch_result_assimilation"
        next_controller_action_hint = "prepare_commit_result_assimilation"
        should_prepare_commit_result_assimilation = True
        should_prepare_next_controller_decision = False
        out_manual_review_required = False
        out_should_stop = False
        out_stop_reason = ""
        out_next_action = "prepare_commit_result_assimilation"
    elif (
        normalized_selected_launch_kind == "manual_stop"
        or bool(manual_stop_launch_executed)
    ):
        status = "next_step_launch_result_manual_stop"
        result_selected = True
        result_available = True
        result_class = "manual_stop"
        result_block_reason = ""
        controller_feedback_ready = True
        controller_feedback_kind = "manual_stop"
        controller_feedback_source = "prompt205_next_step_launch_execution"
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = normalized_stop_reason or "manual_stop"
        out_next_action = "manual_review_required"
    elif bool(launch_execution_failed) or (
        normalized_execution_status == "next_step_launch_execution_failed"
    ):
        status = "next_step_launch_result_failed"
        result_selected = True
        result_available = True
        result_class = "failed"
        result_block_reason = normalized_execution_block_reason or "next_step_launch_execution_failed"
        controller_feedback_ready = True
        controller_feedback_kind = "next_step_launch_failed"
        controller_feedback_source = "prompt205_next_step_launch_execution"
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = normalized_execution_block_reason or "next_step_launch_execution_failed"
        out_next_action = "manual_review_required"
    elif "blocked" in normalized_execution_status:
        status = "next_step_launch_result_blocked"
        result_selected = True
        result_available = True
        result_class = "blocked"
        result_block_reason = normalized_execution_block_reason or "next_step_launch_execution_blocked"
        controller_feedback_ready = True
        controller_feedback_kind = "next_step_launch_blocked"
        controller_feedback_source = "prompt205_next_step_launch_execution"
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = normalized_execution_block_reason or "next_step_launch_execution_blocked"
        out_next_action = "manual_review_required"
    else:
        status = "next_step_launch_result_blocked_insufficient_truth"
        result_selected = True
        result_available = True
        result_class = "insufficient_truth"
        result_block_reason = "blocked_insufficient_next_step_launch_result_truth"
        controller_feedback_ready = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_next_step_launch_result_truth"
        out_next_action = "manual_review_required"

    if result_selected and controller_feedback_ready and not controller_feedback_payload:
        if result_class in {
            "generated_prompt_reentry_completed",
            "rollback_execution_completed",
            "commit_execution_completed",
        }:
            _feedback_map = {
                "generated_prompt_reentry_completed": (
                    "generated_prompt_reentry_result_ready",
                    "prepare_reentry_result_assimilation",
                ),
                "rollback_execution_completed": (
                    "rollback_execution_result_ready",
                    "prepare_rollback_result_assimilation",
                ),
                "commit_execution_completed": (
                    "commit_execution_result_ready",
                    "prepare_commit_result_assimilation",
                ),
            }
            feedback_kind, feedback_next_action = _feedback_map[result_class]
            controller_feedback_payload = {
                "feedback": feedback_kind,
                "source": "prompt205_next_step_launch_execution",
                "delegated_existing_status": normalized_delegated_existing_status,
                "next_action": feedback_next_action,
            }
        else:
            controller_feedback_payload = {
                "feedback": controller_feedback_kind or "next_step_launch_blocked",
                "source": "prompt205_next_step_launch_execution",
                "stop_reason": out_stop_reason,
                "next_action": "manual_review_required",
            }
    elif result_selected and not controller_feedback_ready and not controller_feedback_payload:
        controller_feedback_payload = {}

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if result_class not in allowed_result_classes:
        result_class = "insufficient_truth"
    if out_next_action not in allowed_next_actions:
        out_next_action = "insufficient_truth"
    if status == "insufficient_truth":
        status = "next_step_launch_result_blocked_insufficient_truth"
        result_selected = False
        result_available = False
        result_class = "insufficient_truth"
        result_block_reason = "blocked_insufficient_next_step_launch_result_truth"
        source_execution_status = "insufficient_truth"
        source_execution_completed = False
        source_execution_failed = False
        non_selected_launches_noop_confirmed = False
        controller_feedback_ready = False
        controller_feedback_kind = "none"
        controller_feedback_source = ""
        controller_feedback_payload = {}
        next_controller_input_ready = False
        next_controller_input_kind = "none"
        next_controller_input_source = ""
        next_controller_action_hint = "manual_review_required"
        should_continue_local_loop = False
        should_prepare_reentry_result_assimilation = False
        should_prepare_rollback_result_assimilation = False
        should_prepare_commit_result_assimilation = False
        should_prepare_next_controller_decision = False
        out_should_invoke_codex = False
        out_should_execute_rollback = False
        out_should_execute_commit = False
        out_should_push = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_next_step_launch_result_truth"
        out_next_action = "manual_review_required"

    return {
        "project_browser_autonomous_next_step_launch_result_assimilation_status": status,
        "project_browser_autonomous_next_step_launch_result_assimilation_result_selected": bool(
            result_selected
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_result_available": bool(
            result_available
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_result_class": result_class,
        "project_browser_autonomous_next_step_launch_result_assimilation_result_block_reason": (
            result_block_reason
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_source_selected_launch_kind": (
            normalized_selected_launch_kind
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_source_selected_launch_action": (
            normalized_selected_launch_action
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_source_execution_status": (
            source_execution_status
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_source_execution_completed": bool(
            source_execution_completed
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_source_execution_failed": bool(
            source_execution_failed
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_non_selected_launches_noop_confirmed": bool(
            non_selected_launches_noop_confirmed
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_delegated_existing_path_kind": (
            normalized_delegated_existing_path_kind
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_delegated_existing_status": (
            normalized_delegated_existing_status
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_generated_prompt_reentry_result_status": (
            normalized_generated_prompt_reentry_result_status
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_rollback_execution_result_status": (
            normalized_rollback_execution_result_status
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_commit_execution_result_status": (
            normalized_commit_execution_result_status
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_controller_feedback_ready": bool(
            controller_feedback_ready
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_controller_feedback_kind": (
            controller_feedback_kind
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_controller_feedback_source": (
            controller_feedback_source
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_controller_feedback_payload": (
            controller_feedback_payload if isinstance(controller_feedback_payload, Mapping) else {}
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_next_controller_input_ready": bool(
            next_controller_input_ready
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_next_controller_input_kind": (
            next_controller_input_kind
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_next_controller_input_source": (
            next_controller_input_source
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_next_controller_action_hint": (
            next_controller_action_hint
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_should_continue_local_loop": bool(
            should_continue_local_loop
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_should_prepare_reentry_result_assimilation": bool(
            should_prepare_reentry_result_assimilation
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_should_prepare_rollback_result_assimilation": bool(
            should_prepare_rollback_result_assimilation
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_should_prepare_commit_result_assimilation": bool(
            should_prepare_commit_result_assimilation
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_should_prepare_next_controller_decision": bool(
            should_prepare_next_controller_decision
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_should_invoke_codex": bool(
            out_should_invoke_codex
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_should_execute_rollback": bool(
            out_should_execute_rollback
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_should_execute_commit": bool(
            out_should_execute_commit
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_should_push": bool(
            out_should_push
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_manual_review_required": bool(
            out_manual_review_required
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_should_stop": bool(
            out_should_stop
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_stop_reason": out_stop_reason,
        "project_browser_autonomous_next_step_launch_result_assimilation_next_action": out_next_action,
        "project_browser_autonomous_next_step_launch_result_assimilation_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_next_step_launch_result_assimilation_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_execution_status,
                    normalized_execution_block_reason,
                    normalized_execution_source,
                    normalized_selected_launch_kind,
                    normalized_selected_launch_action,
                    normalized_delegated_existing_path_kind,
                    normalized_delegated_existing_status,
                    normalized_delegated_existing_next_action,
                    normalized_generated_prompt_reentry_result_status,
                    normalized_rollback_execution_result_status,
                    normalized_commit_execution_result_status,
                    normalized_launch_execution_result_class,
                    normalized_assimilation_source,
                    normalized_assimilation_next_stage,
                    normalized_stop_reason,
                    normalized_execution_next_action,
                    normalized_next_step_launch_contract_status,
                    normalized_bounded_local_loop_contract_status,
                    normalized_multi_cycle_controller_status,
                    normalized_reentry_result_assimilation_status,
                    normalized_rollback_result_assimilation_status,
                    normalized_commit_tag_result_assimilation_status,
                    "authoritative_result_not_selected" if not authoritative_selected else "",
                    "selected_launch_payload_missing"
                    if non_stop_selected_launch and not _normalized_selected_launch_payload
                    else "",
                ]
            )
        ),
    }

def _build_project_browser_autonomous_control_dispatch_refresh_result_assimilation_state(
    *,
    control_dispatch_refresh_status: str,
    refresh_allowed: bool,
    refresh_attempted: bool,
    refresh_completed: bool,
    refresh_failed: bool,
    refresh_block_reason: str,
    refresh_source: str,
    selected_assimilation_kind: str,
    selected_assimilation_action: str,
    selected_assimilation_payload: Any,
    exactly_one_refresh_path: bool,
    refresh_conflict_detected: bool,
    conflicting_refresh_paths: Sequence[Any],
    non_selected_refresh_paths_noop: bool,
    reentry_result_assimilation_refresh_executed: bool,
    rollback_result_assimilation_refresh_executed: bool,
    commit_result_assimilation_refresh_executed: bool,
    manual_stop_refresh_executed: bool,
    blocked_refresh_executed: bool,
    delegated_assimilation_path_kind: str,
    delegated_assimilation_status: str,
    delegated_assimilation_next_action: str,
    reentry_result_assimilation_status: str,
    rollback_result_assimilation_status: str,
    commit_result_assimilation_status: str,
    result_class: str,
    control_dispatch_refresh_result_ready_for_assimilation: bool,
    control_dispatch_refresh_result_assimilation_source: str,
    control_dispatch_refresh_result_next_stage: str,
    should_continue_local_loop: bool,
    should_prepare_next_controller_decision: bool,
    should_invoke_codex: bool,
    should_execute_rollback: bool,
    should_execute_commit: bool,
    should_push: bool,
    manual_review_required: bool,
    should_stop: bool,
    stop_reason: str,
    next_action: str,
    control_contract_dispatch_status: str,
    bounded_local_control_decision_status: str,
    next_step_launch_result_assimilation_status: str,
    reentry_result_assimilation_next_action: str,
    rollback_result_assimilation_next_action: str,
    commit_tag_result_assimilation_next_action: str,
    multi_cycle_controller_status: str,
) -> dict[str, Any]:
    allowed_statuses = {
        "control_dispatch_refresh_result_reentry_assimilation_completed",
        "control_dispatch_refresh_result_rollback_assimilation_completed",
        "control_dispatch_refresh_result_commit_assimilation_completed",
        "control_dispatch_refresh_result_manual_stop",
        "control_dispatch_refresh_result_failed",
        "control_dispatch_refresh_result_blocked",
        "control_dispatch_refresh_result_blocked_non_selected_refresh_activity",
        "control_dispatch_refresh_result_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "prepare_next_multi_cycle_decision",
        "manual_review_required",
        "insufficient_truth",
    }
    runtime_posture = [
        "prompt210_control_dispatch_refresh_result_assimilation",
        "metadata_only",
        "final_controller_feedback",
        "single_next_control_target",
        "no_execution",
        "no_codex_invocation",
        "no_git_mutation",
        "no_push",
    ]

    normalized_refresh_status = _normalize_text(
        control_dispatch_refresh_status,
        default="insufficient_truth",
    )
    normalized_refresh_block_reason = _normalize_text(refresh_block_reason, default="")
    normalized_refresh_source = _normalize_text(refresh_source, default="")
    normalized_selected_assimilation_kind = _normalize_text(selected_assimilation_kind, default="")
    normalized_selected_assimilation_action = _normalize_text(
        selected_assimilation_action,
        default="",
    )
    normalized_delegated_assimilation_path_kind = _normalize_text(
        delegated_assimilation_path_kind,
        default="none",
    )
    normalized_delegated_assimilation_status = _normalize_text(
        delegated_assimilation_status,
        default="",
    )
    normalized_delegated_assimilation_next_action = _normalize_text(
        delegated_assimilation_next_action,
        default="",
    )
    normalized_reentry_result_assimilation_status = _normalize_text(
        reentry_result_assimilation_status,
        default="",
    )
    normalized_rollback_result_assimilation_status = _normalize_text(
        rollback_result_assimilation_status,
        default="",
    )
    normalized_commit_result_assimilation_status = _normalize_text(
        commit_result_assimilation_status,
        default="",
    )
    normalized_result_class = _normalize_text(result_class, default="")
    normalized_refresh_result_assimilation_source = _normalize_text(
        control_dispatch_refresh_result_assimilation_source,
        default="",
    )
    normalized_refresh_result_next_stage = _normalize_text(
        control_dispatch_refresh_result_next_stage,
        default="",
    )
    normalized_stop_reason = _normalize_text(stop_reason, default="")
    normalized_next_action = _normalize_text(next_action, default="manual_review_required")
    normalized_control_contract_dispatch_status = _normalize_text(
        control_contract_dispatch_status,
        default="insufficient_truth",
    )
    normalized_bounded_local_control_decision_status = _normalize_text(
        bounded_local_control_decision_status,
        default="insufficient_truth",
    )
    normalized_next_step_launch_result_assimilation_status = _normalize_text(
        next_step_launch_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_reentry_result_assimilation_next_action = _normalize_text(
        reentry_result_assimilation_next_action,
        default="",
    )
    normalized_rollback_result_assimilation_next_action = _normalize_text(
        rollback_result_assimilation_next_action,
        default="",
    )
    normalized_commit_result_assimilation_next_action = _normalize_text(
        commit_tag_result_assimilation_next_action,
        default="",
    )
    normalized_multi_cycle_controller_status = _normalize_text(
        multi_cycle_controller_status,
        default="insufficient_truth",
    )
    normalized_selected_assimilation_payload = (
        dict(selected_assimilation_payload)
        if isinstance(selected_assimilation_payload, Mapping)
        else {}
    )
    normalized_conflicting_refresh_paths = _normalize_string_list(conflicting_refresh_paths)

    authoritative_selected = bool(
        bool(control_dispatch_refresh_result_ready_for_assimilation)
        and normalized_refresh_result_assimilation_source
        == "prompt209_control_dispatch_refresh"
        and normalized_refresh_result_next_stage
        == "control_dispatch_refresh_result_assimilation"
        and (bool(normalized_selected_assimilation_kind) or normalized_refresh_status.startswith("control_dispatch_refresh_manual_stop") or "blocked" in normalized_refresh_status)
        and (bool(normalized_refresh_status) or bool(normalized_result_class))
    )

    status = "control_dispatch_refresh_result_blocked_insufficient_truth"
    out_result_selected = False
    out_result_available = False
    out_result_class = "insufficient_truth"
    out_result_block_reason = "blocked_insufficient_control_dispatch_refresh_result_truth"
    source_selected_assimilation_kind = normalized_selected_assimilation_kind
    source_selected_assimilation_action = normalized_selected_assimilation_action
    source_refresh_status = normalized_refresh_status
    source_refresh_completed = bool(refresh_completed)
    source_refresh_failed = bool(refresh_failed)
    non_selected_refresh_paths_noop_confirmed = bool(non_selected_refresh_paths_noop)
    out_controller_feedback_ready = False
    out_controller_feedback_kind = "control_dispatch_refresh_blocked"
    out_controller_feedback_source = "prompt209_control_dispatch_refresh"
    out_controller_feedback_payload: dict[str, Any] = {}
    final_step_result_kind = "insufficient_truth"
    final_step_result_status = ""
    next_bounded_control_target_ready = False
    next_bounded_control_target_kind = "manual_stop"
    next_bounded_control_target_action = "manual_review_required"
    next_bounded_control_target_payload: dict[str, Any] = {}
    continue_to_multi_cycle_controller = False
    continue_to_generated_prompt_reentry_flow = False
    continue_to_rollback_flow = False
    continue_to_commit_result_flow = False
    manual_stop_target = False
    blocked_target = True
    out_should_continue_local_loop = False
    out_should_prepare_next_controller_decision = False
    out_should_invoke_codex = False
    out_should_execute_rollback = False
    out_should_execute_commit = False
    out_should_push = False
    out_manual_review_required = True
    out_should_stop = True
    out_stop_reason = (
        normalized_stop_reason or "insufficient_control_dispatch_refresh_result_truth"
    )
    out_next_action = "manual_review_required"

    if authoritative_selected:
        out_result_selected = True
        out_result_available = True
        out_result_class = normalized_result_class or "blocked"

        non_stop_success = bool(
            normalized_selected_assimilation_kind
            in {
                "reentry_result_assimilation",
                "rollback_result_assimilation",
                "commit_result_assimilation",
            }
            and bool(refresh_completed)
        )
        if non_stop_success and not bool(non_selected_refresh_paths_noop):
            status = "control_dispatch_refresh_result_blocked_non_selected_refresh_activity"
            out_result_class = "blocked_non_selected_refresh_activity"
            out_result_block_reason = "blocked_non_selected_refresh_activity"
            out_controller_feedback_ready = True
            out_controller_feedback_kind = "control_dispatch_refresh_blocked"
            final_step_result_kind = "blocked"
            blocked_target = True
            next_bounded_control_target_ready = True
            next_bounded_control_target_kind = "manual_stop"
            next_bounded_control_target_action = "manual_review_required"
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = "blocked_non_selected_refresh_activity"
            out_next_action = "manual_review_required"
        elif (
            normalized_selected_assimilation_kind == "reentry_result_assimilation"
            and bool(reentry_result_assimilation_refresh_executed)
            and bool(refresh_completed)
            and normalized_delegated_assimilation_path_kind
            == "reentry_result_assimilation"
            and bool(normalized_delegated_assimilation_status)
        ):
            status = "control_dispatch_refresh_result_reentry_assimilation_completed"
            out_result_class = "reentry_result_assimilation_completed"
            out_result_block_reason = ""
            out_controller_feedback_ready = True
            out_controller_feedback_kind = "reentry_result_assimilation_feedback"
            final_step_result_kind = "reentry_result_assimilation"
            final_step_result_status = normalized_delegated_assimilation_status
            next_bounded_control_target_ready = True
            next_bounded_control_target_kind = "multi_cycle_controller"
            next_bounded_control_target_action = "prepare_next_multi_cycle_decision"
            continue_to_multi_cycle_controller = True
            blocked_target = False
            out_should_prepare_next_controller_decision = True
            out_manual_review_required = False
            out_should_stop = False
            out_stop_reason = ""
            out_next_action = "prepare_next_multi_cycle_decision"
        elif (
            normalized_selected_assimilation_kind == "rollback_result_assimilation"
            and bool(rollback_result_assimilation_refresh_executed)
            and bool(refresh_completed)
            and normalized_delegated_assimilation_path_kind
            == "rollback_result_assimilation"
            and bool(normalized_delegated_assimilation_status)
        ):
            status = "control_dispatch_refresh_result_rollback_assimilation_completed"
            out_result_class = "rollback_result_assimilation_completed"
            out_result_block_reason = ""
            out_controller_feedback_ready = True
            out_controller_feedback_kind = "rollback_result_assimilation_feedback"
            final_step_result_kind = "rollback_result_assimilation"
            final_step_result_status = normalized_delegated_assimilation_status
            next_bounded_control_target_ready = True
            next_bounded_control_target_kind = "multi_cycle_controller"
            next_bounded_control_target_action = "prepare_next_multi_cycle_decision"
            continue_to_multi_cycle_controller = True
            blocked_target = False
            out_should_prepare_next_controller_decision = True
            out_manual_review_required = False
            out_should_stop = False
            out_stop_reason = ""
            out_next_action = "prepare_next_multi_cycle_decision"
        elif (
            normalized_selected_assimilation_kind == "commit_result_assimilation"
            and bool(commit_result_assimilation_refresh_executed)
            and bool(refresh_completed)
            and normalized_delegated_assimilation_path_kind
            == "commit_result_assimilation"
            and bool(normalized_delegated_assimilation_status)
        ):
            status = "control_dispatch_refresh_result_commit_assimilation_completed"
            out_result_class = "commit_result_assimilation_completed"
            out_result_block_reason = ""
            out_controller_feedback_ready = True
            out_controller_feedback_kind = "commit_result_assimilation_feedback"
            final_step_result_kind = "commit_result_assimilation"
            final_step_result_status = normalized_delegated_assimilation_status
            next_bounded_control_target_ready = True
            next_bounded_control_target_kind = "multi_cycle_controller"
            next_bounded_control_target_action = "prepare_next_multi_cycle_decision"
            continue_to_multi_cycle_controller = True
            blocked_target = False
            out_should_prepare_next_controller_decision = True
            out_manual_review_required = False
            out_should_stop = False
            out_stop_reason = ""
            out_next_action = "prepare_next_multi_cycle_decision"
        elif (
            normalized_selected_assimilation_kind == "manual_stop"
            or bool(manual_stop_refresh_executed)
        ):
            status = "control_dispatch_refresh_result_manual_stop"
            out_result_class = "manual_stop"
            out_result_block_reason = ""
            out_controller_feedback_ready = True
            out_controller_feedback_kind = "manual_stop"
            final_step_result_kind = "manual_stop"
            next_bounded_control_target_ready = True
            next_bounded_control_target_kind = "manual_stop"
            next_bounded_control_target_action = "manual_review_required"
            manual_stop_target = True
            blocked_target = False
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = normalized_stop_reason or "manual_stop"
            out_next_action = "manual_review_required"
        elif bool(refresh_failed) or normalized_refresh_status.endswith("_failed"):
            status = "control_dispatch_refresh_result_failed"
            out_result_class = "failed"
            out_result_block_reason = normalized_refresh_block_reason or "control_dispatch_refresh_failed"
            out_controller_feedback_ready = True
            out_controller_feedback_kind = "control_dispatch_refresh_failed"
            final_step_result_kind = "failed"
            next_bounded_control_target_ready = True
            next_bounded_control_target_kind = "manual_stop"
            next_bounded_control_target_action = "manual_review_required"
            blocked_target = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = normalized_refresh_block_reason or "control_dispatch_refresh_failed"
            out_next_action = "manual_review_required"
        elif "blocked" in normalized_refresh_status:
            status = "control_dispatch_refresh_result_blocked"
            out_result_class = "blocked"
            out_result_block_reason = normalized_refresh_block_reason or "control_dispatch_refresh_blocked"
            out_controller_feedback_ready = True
            out_controller_feedback_kind = "control_dispatch_refresh_blocked"
            final_step_result_kind = "blocked"
            next_bounded_control_target_ready = True
            next_bounded_control_target_kind = "manual_stop"
            next_bounded_control_target_action = "manual_review_required"
            blocked_target = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = normalized_refresh_block_reason or "control_dispatch_refresh_blocked"
            out_next_action = "manual_review_required"
        else:
            status = "control_dispatch_refresh_result_blocked_insufficient_truth"
            out_result_class = "insufficient_truth"
            out_result_block_reason = "blocked_insufficient_control_dispatch_refresh_result_truth"
            out_controller_feedback_ready = False
            final_step_result_kind = "insufficient_truth"
            next_bounded_control_target_ready = True
            next_bounded_control_target_kind = "manual_stop"
            next_bounded_control_target_action = "manual_review_required"
            blocked_target = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = "insufficient_control_dispatch_refresh_result_truth"
            out_next_action = "manual_review_required"
    else:
        status = "control_dispatch_refresh_result_blocked_insufficient_truth"
        out_result_selected = False
        out_result_available = False
        out_result_class = "insufficient_truth"
        out_result_block_reason = "blocked_insufficient_control_dispatch_refresh_result_truth"
        out_controller_feedback_ready = False
        final_step_result_kind = "insufficient_truth"
        next_bounded_control_target_ready = False
        next_bounded_control_target_kind = "manual_stop"
        next_bounded_control_target_action = "manual_review_required"
        blocked_target = True
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_control_dispatch_refresh_result_truth"
        out_next_action = "manual_review_required"

    if out_result_selected:
        if continue_to_multi_cycle_controller:
            out_controller_feedback_payload = {
                "feedback": out_controller_feedback_kind,
                "source": "prompt209_control_dispatch_refresh",
                "assimilation_kind": normalized_selected_assimilation_kind,
                "assimilation_status": normalized_delegated_assimilation_status,
                "assimilation_next_action": normalized_delegated_assimilation_next_action,
                "next_action": "prepare_next_multi_cycle_decision",
            }
            next_bounded_control_target_payload = {
                "target": "multi_cycle_controller",
                "source": "prompt210_control_dispatch_refresh_result_assimilation",
                "final_step_result_kind": final_step_result_kind,
                "final_step_result_status": final_step_result_status,
                "next_action": "prepare_next_multi_cycle_decision",
            }
        else:
            out_controller_feedback_payload = {
                "feedback": out_controller_feedback_kind,
                "source": "prompt209_control_dispatch_refresh",
                "stop_reason": out_stop_reason,
                "next_action": "manual_review_required",
            }
            next_bounded_control_target_payload = {
                "target": "manual_stop",
                "source": "prompt210_control_dispatch_refresh_result_assimilation",
                "stop_reason": out_stop_reason,
                "next_action": "manual_review_required",
            }
    else:
        out_controller_feedback_payload = {}
        next_bounded_control_target_payload = {}

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if out_next_action not in allowed_next_actions:
        out_next_action = "insufficient_truth"
    if status == "insufficient_truth":
        status = "control_dispatch_refresh_result_blocked_insufficient_truth"
        out_result_selected = False
        out_result_available = False
        out_result_class = "insufficient_truth"
        out_result_block_reason = "blocked_insufficient_control_dispatch_refresh_result_truth"
        out_controller_feedback_ready = False
        out_controller_feedback_kind = "control_dispatch_refresh_blocked"
        out_controller_feedback_payload = {}
        final_step_result_kind = "insufficient_truth"
        final_step_result_status = ""
        next_bounded_control_target_ready = False
        next_bounded_control_target_kind = "manual_stop"
        next_bounded_control_target_action = "manual_review_required"
        next_bounded_control_target_payload = {}
        continue_to_multi_cycle_controller = False
        continue_to_generated_prompt_reentry_flow = False
        continue_to_rollback_flow = False
        continue_to_commit_result_flow = False
        manual_stop_target = False
        blocked_target = True
        out_should_continue_local_loop = False
        out_should_prepare_next_controller_decision = False
        out_should_invoke_codex = False
        out_should_execute_rollback = False
        out_should_execute_commit = False
        out_should_push = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_control_dispatch_refresh_result_truth"
        out_next_action = "manual_review_required"

    return {
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_status": status,
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_result_selected": bool(
            out_result_selected
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_result_available": bool(
            out_result_available
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_result_class": (
            out_result_class
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_result_block_reason": (
            out_result_block_reason
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_source_selected_assimilation_kind": (
            source_selected_assimilation_kind
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_source_selected_assimilation_action": (
            source_selected_assimilation_action
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_source_refresh_status": (
            source_refresh_status
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_source_refresh_completed": bool(
            source_refresh_completed
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_source_refresh_failed": bool(
            source_refresh_failed
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_non_selected_refresh_paths_noop_confirmed": bool(
            non_selected_refresh_paths_noop_confirmed
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_delegated_assimilation_path_kind": (
            normalized_delegated_assimilation_path_kind
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_delegated_assimilation_status": (
            normalized_delegated_assimilation_status
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_delegated_assimilation_next_action": (
            normalized_delegated_assimilation_next_action
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_reentry_result_assimilation_status": (
            normalized_reentry_result_assimilation_status
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_rollback_result_assimilation_status": (
            normalized_rollback_result_assimilation_status
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_commit_result_assimilation_status": (
            normalized_commit_result_assimilation_status
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_controller_feedback_ready": bool(
            out_controller_feedback_ready
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_controller_feedback_kind": (
            out_controller_feedback_kind
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_controller_feedback_source": (
            out_controller_feedback_source
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_controller_feedback_payload": (
            out_controller_feedback_payload
            if isinstance(out_controller_feedback_payload, Mapping)
            else {}
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_final_step_result_kind": (
            final_step_result_kind
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_final_step_result_status": (
            final_step_result_status
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_next_bounded_control_target_ready": bool(
            next_bounded_control_target_ready
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_next_bounded_control_target_kind": (
            next_bounded_control_target_kind
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_next_bounded_control_target_action": (
            next_bounded_control_target_action
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_next_bounded_control_target_payload": (
            next_bounded_control_target_payload
            if isinstance(next_bounded_control_target_payload, Mapping)
            else {}
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_continue_to_multi_cycle_controller": bool(
            continue_to_multi_cycle_controller
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_continue_to_generated_prompt_reentry_flow": bool(
            continue_to_generated_prompt_reentry_flow
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_continue_to_rollback_flow": bool(
            continue_to_rollback_flow
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_continue_to_commit_result_flow": bool(
            continue_to_commit_result_flow
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_manual_stop_target": bool(
            manual_stop_target
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_blocked_target": bool(
            blocked_target
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_should_continue_local_loop": bool(
            out_should_continue_local_loop
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_should_prepare_next_controller_decision": bool(
            out_should_prepare_next_controller_decision
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_should_invoke_codex": bool(
            out_should_invoke_codex
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_should_execute_rollback": bool(
            out_should_execute_rollback
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_should_execute_commit": bool(
            out_should_execute_commit
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_should_push": bool(
            out_should_push
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_manual_review_required": bool(
            out_manual_review_required
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_should_stop": bool(
            out_should_stop
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_stop_reason": (
            out_stop_reason
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_next_action": (
            out_next_action
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_assimilation_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_refresh_status,
                    normalized_refresh_block_reason,
                    normalized_refresh_source,
                    normalized_selected_assimilation_kind,
                    normalized_selected_assimilation_action,
                    normalized_delegated_assimilation_path_kind,
                    normalized_delegated_assimilation_status,
                    normalized_delegated_assimilation_next_action,
                    normalized_reentry_result_assimilation_status,
                    normalized_rollback_result_assimilation_status,
                    normalized_commit_result_assimilation_status,
                    normalized_refresh_result_assimilation_source,
                    normalized_refresh_result_next_stage,
                    normalized_stop_reason,
                    normalized_next_action,
                    normalized_control_contract_dispatch_status,
                    normalized_bounded_local_control_decision_status,
                    normalized_next_step_launch_result_assimilation_status,
                    normalized_reentry_result_assimilation_next_action,
                    normalized_rollback_result_assimilation_next_action,
                    normalized_commit_result_assimilation_next_action,
                    normalized_multi_cycle_controller_status,
                    "authoritative_refresh_result_not_selected"
                    if not authoritative_selected
                    else "",
                    "refresh_conflict_detected" if bool(refresh_conflict_detected) else "",
                    "conflicting_refresh_paths_present"
                    if normalized_conflicting_refresh_paths
                    else "",
                ]
            )
        ),
    }

def _build_project_browser_autonomous_direct_retrigger_result_assimilation_state(
    *,
    direct_retrigger_coordinator_status: str,
    direct_retrigger_available: bool,
    direct_retrigger_allowed: bool,
    direct_retrigger_attempted: bool,
    direct_retrigger_completed: bool,
    direct_retrigger_failed: bool,
    direct_retrigger_block_reason: str,
    direct_retrigger_source: str,
    selected_retrigger_kind: str,
    selected_retrigger_action: str,
    selected_retrigger_payload: Any,
    prompt213_preflight_valid: bool,
    prompt214_contract_valid: bool,
    exactly_one_direct_retrigger: bool,
    direct_retrigger_conflict_detected: bool,
    conflicting_direct_retriggers: Sequence[Any],
    codex_retrigger_executed: bool,
    rollback_retrigger_executed: bool,
    commit_retrigger_executed: bool,
    fix_prompt_retrigger_executed: bool,
    next_prompt_retrigger_executed: bool,
    manual_stop_executed: bool,
    blocked_executed: bool,
    delegated_existing_path: bool,
    delegated_existing_path_kind: str,
    delegated_existing_status: str,
    delegated_existing_next_action: str,
    non_selected_retriggers_noop: bool,
    source_result_class: str,
    prompt215_result_ready_for_assimilation: bool,
    prompt215_result_assimilation_source: str,
    prompt215_result_next_stage: str,
    should_continue_local_loop: bool,
    should_start_unbounded_loop: bool,
    should_invoke_codex: bool,
    should_execute_rollback: bool,
    should_execute_commit: bool,
    should_push: bool,
    manual_review_required: bool,
    should_stop: bool,
    stop_reason: str,
    next_action: str,
    stale_fresh_ordering_gate_status: str,
    stale_fresh_state_detected: bool,
    one_bounded_continuation_coordinator_status: str,
    final_runtime_continuation_guard_status: str,
    multi_cycle_controller_status: str,
    codex_reentry_invocation_status: str,
    codex_reentry_invocation_next_action: str,
    codex_reentry_result_ready_for_assimilation: bool,
    rollback_execution_status: str,
    rollback_execution_next_action: str,
    rollback_result_assimilation_status: str,
    rollback_result_assimilation_next_action: str,
    commit_tag_execution_status: str,
    commit_tag_execution_next_action: str,
    commit_tag_result_assimilation_status: str,
    commit_tag_result_assimilation_next_action: str,
    fix_prompt_generation_status: str,
    fix_prompt_generation_next_action: str,
    next_prompt_generation_status: str,
    next_prompt_generation_next_action: str,
) -> dict[str, Any]:
    allowed_statuses = {
        "direct_retrigger_result_completed_fresh_attempt",
        "direct_retrigger_result_completed_existing_truth",
        "direct_retrigger_result_blocked_stale_truth_only",
        "direct_retrigger_result_blocked_existing_path_not_callable",
        "direct_retrigger_result_manual_stop",
        "direct_retrigger_result_failed",
        "direct_retrigger_result_blocked",
        "direct_retrigger_result_blocked_non_selected_retrigger_activity",
        "direct_retrigger_result_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_result_classes = {
        "completed_fresh_attempt",
        "completed_existing_truth_surface",
        "blocked_stale_truth_only",
        "blocked_existing_path_not_callable",
        "blocked_non_selected_retrigger_activity",
        "manual_stop",
        "blocked",
        "failed",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "prepare_result_followup",
        "manual_review_required",
        "insufficient_truth",
    }
    runtime_posture = [
        "prompt215_direct_retrigger_result_assimilation",
        "metadata_only",
        "result_assimilation_only",
        "no_downstream_execution",
        "no_retry",
        "no_loop",
        "no_push",
        "no_github_mutation",
    ]

    normalized_source_status = _normalize_text(
        direct_retrigger_coordinator_status,
        default="insufficient_truth",
    )
    normalized_source_block_reason = _normalize_text(direct_retrigger_block_reason, default="")
    normalized_source = _normalize_text(
        direct_retrigger_source,
        default="prompt213_stale_fresh_ordering_gate",
    )
    normalized_selected_kind = _normalize_text(selected_retrigger_kind, default="")
    normalized_selected_action = _normalize_text(
        selected_retrigger_action,
        default="manual_review_required",
    )
    normalized_source_result_class = _normalize_text(source_result_class, default="")
    normalized_assimilation_source = _normalize_text(
        prompt215_result_assimilation_source,
        default="",
    )
    normalized_assimilation_next_stage = _normalize_text(
        prompt215_result_next_stage,
        default="",
    )
    normalized_delegated_kind = _normalize_text(delegated_existing_path_kind, default="none")
    normalized_delegated_status = _normalize_text(delegated_existing_status, default="")
    normalized_delegated_next_action = _normalize_text(
        delegated_existing_next_action,
        default="",
    )
    normalized_stop_reason = _normalize_text(stop_reason, default="")
    normalized_source_next_action = _normalize_text(next_action, default="manual_review_required")
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
    normalized_codex_reentry_next_action = _normalize_text(
        codex_reentry_invocation_next_action,
        default="",
    )
    normalized_rollback_execution_status = _normalize_text(
        rollback_execution_status,
        default="insufficient_truth",
    )
    normalized_rollback_execution_next_action = _normalize_text(
        rollback_execution_next_action,
        default="",
    )
    normalized_rollback_result_assimilation_status = _normalize_text(
        rollback_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_rollback_result_assimilation_next_action = _normalize_text(
        rollback_result_assimilation_next_action,
        default="",
    )
    normalized_commit_execution_status = _normalize_text(
        commit_tag_execution_status,
        default="insufficient_truth",
    )
    normalized_commit_execution_next_action = _normalize_text(
        commit_tag_execution_next_action,
        default="",
    )
    normalized_commit_result_assimilation_status = _normalize_text(
        commit_tag_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_commit_result_assimilation_next_action = _normalize_text(
        commit_tag_result_assimilation_next_action,
        default="",
    )
    normalized_fix_generation_status = _normalize_text(
        fix_prompt_generation_status,
        default="insufficient_truth",
    )
    normalized_fix_generation_next_action = _normalize_text(
        fix_prompt_generation_next_action,
        default="",
    )
    normalized_next_generation_status = _normalize_text(
        next_prompt_generation_status,
        default="insufficient_truth",
    )
    normalized_next_generation_next_action = _normalize_text(
        next_prompt_generation_next_action,
        default="",
    )
    normalized_conflicts = _normalize_string_list(conflicting_direct_retriggers)
    normalized_selected_payload = (
        dict(selected_retrigger_payload)
        if isinstance(selected_retrigger_payload, Mapping)
        else {}
    )

    source_status_indicates_manual = normalized_source_status == "direct_retrigger_coordinator_manual_stop"
    source_status_indicates_blocked = "blocked" in normalized_source_status
    source_status_indicates_failed = normalized_source_status == "direct_retrigger_coordinator_failed"

    authoritative_selected = bool(
        bool(prompt215_result_ready_for_assimilation)
        and normalized_assimilation_source == "prompt214_direct_retrigger_coordinator"
        and normalized_assimilation_next_stage == "direct_retrigger_result_assimilation"
        and (
            bool(normalized_selected_kind)
            or source_status_indicates_manual
            or source_status_indicates_blocked
        )
        and (bool(normalized_source_status) or bool(normalized_source_result_class))
    )

    expected_delegated_kind_map = {
        "codex_retrigger": "codex_retrigger",
        "rollback_retrigger": "rollback_retrigger",
        "commit_retrigger": "commit_retrigger",
        "fix_prompt_retrigger": "fix_prompt_retrigger",
        "next_prompt_retrigger": "next_prompt_retrigger",
    }
    non_stop_supported_kinds = set(expected_delegated_kind_map)
    selected_is_non_stop_supported = normalized_selected_kind in non_stop_supported_kinds
    expected_delegated_kind = expected_delegated_kind_map.get(normalized_selected_kind, "")
    selected_exec_flag = bool(
        (normalized_selected_kind == "codex_retrigger" and bool(codex_retrigger_executed))
        or (
            normalized_selected_kind == "rollback_retrigger"
            and bool(rollback_retrigger_executed)
        )
        or (
            normalized_selected_kind == "commit_retrigger"
            and bool(commit_retrigger_executed)
        )
        or (
            normalized_selected_kind == "fix_prompt_retrigger"
            and bool(fix_prompt_retrigger_executed)
        )
        or (
            normalized_selected_kind == "next_prompt_retrigger"
            and bool(next_prompt_retrigger_executed)
        )
    )

    callable_existing_path_detected = bool(
        bool(delegated_existing_path)
        and bool(expected_delegated_kind)
        and normalized_delegated_kind == expected_delegated_kind
    )

    codex_terminal = bool(
        bool(codex_reentry_result_ready_for_assimilation)
        or normalized_codex_reentry_status in {"invocation_result_assimilated"}
        or any(
            token in normalized_codex_reentry_status
            for token in ("completed", "failed", "blocked")
        )
        or normalized_codex_reentry_next_action in {"manual_review_required"}
    )
    rollback_terminal = bool(
        bool(normalized_rollback_result_assimilation_status)
        and normalized_rollback_result_assimilation_status != "insufficient_truth"
    ) or any(
        token in normalized_rollback_execution_status
        for token in ("completed", "failed", "blocked")
    )
    commit_terminal = bool(
        bool(normalized_commit_result_assimilation_status)
        and normalized_commit_result_assimilation_status != "insufficient_truth"
    ) or any(
        token in normalized_commit_execution_status
        for token in ("completed", "failed", "blocked")
    )
    fix_terminal = normalized_fix_generation_status in {"prompt_generated"} or any(
        token in normalized_fix_generation_status for token in ("blocked", "failed")
    )
    next_terminal = normalized_next_generation_status in {"prompt_generated"} or any(
        token in normalized_next_generation_status for token in ("blocked", "failed")
    )

    terminal_result_detected = bool(
        (normalized_selected_kind == "codex_retrigger" and callable_existing_path_detected and codex_terminal)
        or (
            normalized_selected_kind == "rollback_retrigger"
            and callable_existing_path_detected
            and rollback_terminal
        )
        or (
            normalized_selected_kind == "commit_retrigger"
            and callable_existing_path_detected
            and commit_terminal
        )
        or (
            normalized_selected_kind == "fix_prompt_retrigger"
            and callable_existing_path_detected
            and fix_terminal
        )
        or (
            normalized_selected_kind == "next_prompt_retrigger"
            and callable_existing_path_detected
            and next_terminal
        )
        or normalized_source_result_class in {
            "codex_retrigger_completed",
            "rollback_retrigger_completed",
            "commit_retrigger_completed",
            "fix_prompt_retrigger_completed",
            "next_prompt_retrigger_completed",
        }
    )
    terminal_result_source = ""
    if terminal_result_detected:
        if selected_exec_flag and bool(direct_retrigger_attempted):
            terminal_result_source = "fresh_attempt"
        elif normalized_source_result_class.endswith("_completed"):
            terminal_result_source = "source_result_class"
        elif bool(normalized_delegated_status):
            terminal_result_source = "delegated_existing_status"
        else:
            terminal_result_source = "result_handoff_marker"

    fresh_attempt_detected = bool(
        bool(direct_retrigger_attempted)
        and selected_exec_flag
        and callable_existing_path_detected
        and terminal_result_detected
        and (
            bool(normalized_delegated_next_action)
            or bool(prompt215_result_ready_for_assimilation)
        )
    )

    completed_statuses = {
        "direct_retrigger_coordinator_codex_completed",
        "direct_retrigger_coordinator_rollback_completed",
        "direct_retrigger_coordinator_commit_completed",
        "direct_retrigger_coordinator_fix_prompt_completed",
        "direct_retrigger_coordinator_next_prompt_completed",
    }
    existing_truth_surface_detected = bool(
        bool(direct_retrigger_completed)
        and bool(normalized_delegated_status)
        and terminal_result_detected
        and not fresh_attempt_detected
        and normalized_source_status in completed_statuses
    )

    stale_truth_only_detected = bool(
        (
            bool(normalized_delegated_status)
            and not terminal_result_detected
            and normalized_source_status in completed_statuses
        )
        or (
            bool(stale_fresh_state_detected)
            and not fresh_attempt_detected
            and normalized_stale_gate_status
            in {
                "stale_fresh_ordering_gate_blocked_stale_state",
                "stale_fresh_ordering_gate_blocked",
            }
        )
    )

    existing_path_not_callable_detected = bool(
        selected_is_non_stop_supported
        and (
            normalized_source_status
            == "direct_retrigger_coordinator_blocked_existing_bounded_path"
            or normalized_source_block_reason == "blocked_existing_bounded_path"
            or not callable_existing_path_detected
        )
    )

    status = "direct_retrigger_result_blocked_insufficient_truth"
    result_selected = False
    result_available = False
    result_class = "insufficient_truth"
    result_block_reason = "blocked_insufficient_direct_retrigger_result_truth"
    source_retrigger_status = normalized_source_status
    source_retrigger_attempted = bool(direct_retrigger_attempted)
    source_retrigger_completed = bool(direct_retrigger_completed)
    source_retrigger_failed = bool(direct_retrigger_failed)
    non_selected_retriggers_noop_confirmed = bool(non_selected_retriggers_noop)
    controller_feedback_ready = False
    controller_feedback_kind = "none"
    controller_feedback_source = "prompt214_direct_retrigger_coordinator"
    controller_feedback_payload: dict[str, Any] = {}
    next_bounded_control_target_ready = False
    next_bounded_control_target_kind = "manual_stop"
    next_bounded_control_target_action = "manual_review_required"
    next_bounded_control_target_payload: dict[str, Any] = {}
    should_prepare_result_assimilation_chain = False
    out_should_prepare_next_controller_decision = False
    out_should_continue_local_loop = False
    out_should_start_unbounded_loop = False
    out_should_invoke_codex = False
    out_should_execute_rollback = False
    out_should_execute_commit = False
    out_should_push = False
    out_manual_review_required = True
    out_should_stop = True
    out_stop_reason = normalized_stop_reason or "insufficient_direct_retrigger_result_truth"
    out_next_action = "manual_review_required"

    if not authoritative_selected:
        status = "direct_retrigger_result_blocked_insufficient_truth"
        result_selected = False
        result_available = False
    else:
        result_selected = True
        result_available = True

        if (
            selected_is_non_stop_supported
            and (fresh_attempt_detected or existing_truth_surface_detected)
            and not bool(non_selected_retriggers_noop)
        ):
            status = "direct_retrigger_result_blocked_non_selected_retrigger_activity"
            result_class = "blocked_non_selected_retrigger_activity"
            result_block_reason = "blocked_non_selected_retrigger_activity"
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = "blocked_non_selected_retrigger_activity"
            out_next_action = "manual_review_required"
        elif (
            selected_is_non_stop_supported
            and fresh_attempt_detected
        ):
            status = "direct_retrigger_result_completed_fresh_attempt"
            result_class = "completed_fresh_attempt"
            result_block_reason = ""
            controller_feedback_ready = True
            controller_feedback_kind = "direct_retrigger_fresh_attempt_completed"
            controller_feedback_payload = {
                "feedback": "direct_retrigger_fresh_attempt_completed",
                "source": "prompt214_direct_retrigger_coordinator",
                "selected_retrigger_kind": normalized_selected_kind,
                "delegated_existing_status": normalized_delegated_status,
                "next_action": "prepare_result_followup",
            }
            next_bounded_control_target_ready = True
            next_bounded_control_target_kind = "direct_retrigger_result_followup"
            next_bounded_control_target_action = "prepare_result_followup"
            next_bounded_control_target_payload = {
                "target": "direct_retrigger_result_followup",
                "source": "prompt215_direct_retrigger_result_assimilation",
                "selected_retrigger_kind": normalized_selected_kind,
                "next_action": "prepare_result_followup",
            }
            should_prepare_result_assimilation_chain = True
            out_manual_review_required = False
            out_should_stop = False
            out_stop_reason = ""
            out_next_action = "prepare_result_followup"
        elif (
            selected_is_non_stop_supported
            and existing_truth_surface_detected
        ):
            status = "direct_retrigger_result_completed_existing_truth"
            result_class = "completed_existing_truth_surface"
            result_block_reason = ""
            controller_feedback_ready = True
            controller_feedback_kind = "direct_retrigger_existing_truth_completed"
            controller_feedback_payload = {
                "feedback": "direct_retrigger_existing_truth_completed",
                "source": "prompt214_direct_retrigger_coordinator",
                "selected_retrigger_kind": normalized_selected_kind,
                "delegated_existing_status": normalized_delegated_status,
                "next_action": "prepare_result_followup",
            }
            next_bounded_control_target_ready = True
            next_bounded_control_target_kind = "direct_retrigger_result_followup"
            next_bounded_control_target_action = "prepare_result_followup"
            next_bounded_control_target_payload = {
                "target": "direct_retrigger_result_followup",
                "source": "prompt215_direct_retrigger_result_assimilation",
                "selected_retrigger_kind": normalized_selected_kind,
                "next_action": "prepare_result_followup",
            }
            should_prepare_result_assimilation_chain = True
            out_manual_review_required = False
            out_should_stop = False
            out_stop_reason = ""
            out_next_action = "prepare_result_followup"
        elif stale_truth_only_detected:
            status = "direct_retrigger_result_blocked_stale_truth_only"
            result_class = "blocked_stale_truth_only"
            result_block_reason = "blocked_stale_truth_only"
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = "blocked_stale_truth_only"
            out_next_action = "manual_review_required"
        elif existing_path_not_callable_detected:
            status = "direct_retrigger_result_blocked_existing_path_not_callable"
            result_class = "blocked_existing_path_not_callable"
            result_block_reason = "blocked_existing_path_not_callable"
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = "blocked_existing_path_not_callable"
            out_next_action = "manual_review_required"
        elif normalized_selected_kind == "manual_stop" or bool(manual_stop_executed):
            status = "direct_retrigger_result_manual_stop"
            result_class = "manual_stop"
            result_block_reason = ""
            controller_feedback_ready = True
            controller_feedback_kind = "manual_stop"
            controller_feedback_payload = {
                "feedback": "manual_stop",
                "source": "prompt214_direct_retrigger_coordinator",
                "stop_reason": normalized_stop_reason or "manual_stop",
                "next_action": "manual_review_required",
            }
            next_bounded_control_target_ready = True
            next_bounded_control_target_kind = "manual_stop"
            next_bounded_control_target_action = "manual_review_required"
            next_bounded_control_target_payload = {
                "target": "manual_stop",
                "source": "prompt215_direct_retrigger_result_assimilation",
                "stop_reason": normalized_stop_reason or "manual_stop",
                "next_action": "manual_review_required",
            }
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = normalized_stop_reason or "manual_stop"
            out_next_action = "manual_review_required"
        elif bool(direct_retrigger_failed) or source_status_indicates_failed:
            status = "direct_retrigger_result_failed"
            result_class = "failed"
            result_block_reason = normalized_source_block_reason or "direct_retrigger_failed"
            controller_feedback_ready = True
            controller_feedback_kind = "direct_retrigger_failed"
            controller_feedback_payload = {
                "feedback": "direct_retrigger_failed",
                "source": "prompt214_direct_retrigger_coordinator",
                "stop_reason": normalized_source_block_reason or "direct_retrigger_failed",
                "next_action": "manual_review_required",
            }
            next_bounded_control_target_ready = True
            next_bounded_control_target_kind = "manual_stop"
            next_bounded_control_target_action = "manual_review_required"
            next_bounded_control_target_payload = {
                "target": "manual_stop",
                "source": "prompt215_direct_retrigger_result_assimilation",
                "stop_reason": normalized_source_block_reason or "direct_retrigger_failed",
                "next_action": "manual_review_required",
            }
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = normalized_source_block_reason or "direct_retrigger_failed"
            out_next_action = "manual_review_required"
        elif source_status_indicates_blocked or bool(blocked_executed):
            status = "direct_retrigger_result_blocked"
            result_class = "blocked"
            result_block_reason = normalized_source_block_reason or "direct_retrigger_blocked"
            controller_feedback_ready = True
            controller_feedback_kind = "direct_retrigger_blocked"
            controller_feedback_payload = {
                "feedback": "direct_retrigger_blocked",
                "source": "prompt214_direct_retrigger_coordinator",
                "stop_reason": normalized_source_block_reason or "direct_retrigger_blocked",
                "next_action": "manual_review_required",
            }
            next_bounded_control_target_ready = True
            next_bounded_control_target_kind = "manual_stop"
            next_bounded_control_target_action = "manual_review_required"
            next_bounded_control_target_payload = {
                "target": "manual_stop",
                "source": "prompt215_direct_retrigger_result_assimilation",
                "stop_reason": normalized_source_block_reason or "direct_retrigger_blocked",
                "next_action": "manual_review_required",
            }
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = normalized_source_block_reason or "direct_retrigger_blocked"
            out_next_action = "manual_review_required"
        else:
            status = "direct_retrigger_result_blocked_insufficient_truth"
            result_class = "insufficient_truth"
            result_block_reason = "blocked_insufficient_direct_retrigger_result_truth"
            controller_feedback_ready = False
            next_bounded_control_target_ready = True
            next_bounded_control_target_kind = "manual_stop"
            next_bounded_control_target_action = "manual_review_required"
            next_bounded_control_target_payload = {
                "target": "manual_stop",
                "source": "prompt215_direct_retrigger_result_assimilation",
                "stop_reason": "insufficient_direct_retrigger_result_truth",
                "next_action": "manual_review_required",
            }
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = "insufficient_direct_retrigger_result_truth"
            out_next_action = "manual_review_required"

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if result_class not in allowed_result_classes:
        result_class = "insufficient_truth"
    if out_next_action not in allowed_next_actions:
        out_next_action = "insufficient_truth"
    if status == "insufficient_truth":
        status = "direct_retrigger_result_blocked_insufficient_truth"
        result_selected = False
        result_available = False
        result_class = "insufficient_truth"
        result_block_reason = "blocked_insufficient_direct_retrigger_result_truth"
        non_selected_retriggers_noop_confirmed = False
        controller_feedback_ready = False
        controller_feedback_kind = "none"
        controller_feedback_source = "prompt214_direct_retrigger_coordinator"
        controller_feedback_payload = {}
        next_bounded_control_target_ready = False
        next_bounded_control_target_kind = "manual_stop"
        next_bounded_control_target_action = "manual_review_required"
        next_bounded_control_target_payload = {}
        should_prepare_result_assimilation_chain = False
        out_should_prepare_next_controller_decision = False
        out_should_continue_local_loop = False
        out_should_start_unbounded_loop = False
        out_should_invoke_codex = False
        out_should_execute_rollback = False
        out_should_execute_commit = False
        out_should_push = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_direct_retrigger_result_truth"
        out_next_action = "manual_review_required"

    return {
        "project_browser_autonomous_direct_retrigger_result_assimilation_status": status,
        "project_browser_autonomous_direct_retrigger_result_assimilation_result_selected": bool(
            result_selected
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_result_available": bool(
            result_available
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_result_class": result_class,
        "project_browser_autonomous_direct_retrigger_result_assimilation_result_block_reason": (
            result_block_reason
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_source_selected_retrigger_kind": (
            normalized_selected_kind
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_source_selected_retrigger_action": (
            normalized_selected_action
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_source_retrigger_status": (
            source_retrigger_status
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_source_retrigger_attempted": bool(
            source_retrigger_attempted
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_source_retrigger_completed": bool(
            source_retrigger_completed
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_source_retrigger_failed": bool(
            source_retrigger_failed
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_non_selected_retriggers_noop_confirmed": bool(
            non_selected_retriggers_noop_confirmed
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_delegated_existing_path_kind": (
            normalized_delegated_kind
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_delegated_existing_status": (
            normalized_delegated_status
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_delegated_existing_next_action": (
            normalized_delegated_next_action
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_fresh_attempt_detected": bool(
            fresh_attempt_detected
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_existing_truth_surface_detected": bool(
            existing_truth_surface_detected
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_stale_truth_only_detected": bool(
            stale_truth_only_detected
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_callable_existing_path_detected": bool(
            callable_existing_path_detected
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_existing_path_not_callable_detected": bool(
            existing_path_not_callable_detected
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_terminal_result_detected": bool(
            terminal_result_detected
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_terminal_result_source": (
            terminal_result_source
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_controller_feedback_ready": bool(
            controller_feedback_ready
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_controller_feedback_kind": (
            controller_feedback_kind
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_controller_feedback_source": (
            controller_feedback_source
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_controller_feedback_payload": (
            controller_feedback_payload if isinstance(controller_feedback_payload, Mapping) else {}
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_next_bounded_control_target_ready": bool(
            next_bounded_control_target_ready
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_next_bounded_control_target_kind": (
            next_bounded_control_target_kind
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_next_bounded_control_target_action": (
            next_bounded_control_target_action
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_next_bounded_control_target_payload": (
            next_bounded_control_target_payload
            if isinstance(next_bounded_control_target_payload, Mapping)
            else {}
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_should_prepare_result_assimilation_chain": bool(
            should_prepare_result_assimilation_chain
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_should_prepare_next_controller_decision": bool(
            out_should_prepare_next_controller_decision
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_should_continue_local_loop": bool(
            out_should_continue_local_loop
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_should_start_unbounded_loop": bool(
            out_should_start_unbounded_loop
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_should_invoke_codex": bool(
            out_should_invoke_codex
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_should_execute_rollback": bool(
            out_should_execute_rollback
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_should_execute_commit": bool(
            out_should_execute_commit
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_should_push": bool(
            out_should_push
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_manual_review_required": bool(
            out_manual_review_required
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_should_stop": bool(
            out_should_stop
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_stop_reason": (
            out_stop_reason
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_next_action": (
            out_next_action
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_direct_retrigger_result_assimilation_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_source_status,
                    normalized_source_block_reason,
                    normalized_source,
                    normalized_selected_kind,
                    normalized_selected_action,
                    normalized_source_result_class,
                    normalized_assimilation_source,
                    normalized_assimilation_next_stage,
                    normalized_delegated_kind,
                    normalized_delegated_status,
                    normalized_delegated_next_action,
                    normalized_stop_reason,
                    normalized_source_next_action,
                    normalized_stale_gate_status,
                    normalized_one_bounded_status,
                    normalized_final_guard_status,
                    normalized_multi_cycle_status,
                    normalized_codex_reentry_status,
                    normalized_rollback_execution_status,
                    normalized_commit_execution_status,
                    normalized_fix_generation_status,
                    normalized_next_generation_status,
                    normalized_codex_reentry_next_action,
                    normalized_rollback_execution_next_action,
                    normalized_rollback_result_assimilation_next_action,
                    normalized_commit_execution_next_action,
                    normalized_commit_result_assimilation_next_action,
                    normalized_fix_generation_next_action,
                    normalized_next_generation_next_action,
                    "authoritative_prompt214_missing" if not authoritative_selected else "",
                    "existing_path_not_callable" if existing_path_not_callable_detected else "",
                    "stale_truth_only_detected" if stale_truth_only_detected else "",
                    "terminal_result_not_detected" if not terminal_result_detected else "",
                    "direct_retrigger_conflict_detected"
                    if bool(direct_retrigger_conflict_detected)
                    else "",
                    "conflicting_direct_retriggers_present"
                    if normalized_conflicts
                    else "",
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

def _build_project_browser_autonomous_bounded_multistep_execution_result_assimilation_state(
    *,
    bounded_multistep_execution_coordinator_status: str,
    execution_coordinator_available: bool,
    execution_coordinator_allowed: bool,
    execution_coordinator_attempted: bool,
    execution_coordinator_completed: bool,
    execution_coordinator_failed: bool,
    execution_coordinator_block_reason: str,
    execution_coordinator_source: str,
    prompt218_contract_valid: bool,
    selected_action_kind: str,
    selected_action_action: str,
    selected_action_payload: Any,
    exactly_one_bounded_action: bool,
    bounded_action_conflict_detected: bool,
    conflicting_bounded_actions: Sequence[Any],
    generated_prompt_reentry_action_executed: bool,
    rollback_execution_action_executed: bool,
    commit_tag_execution_action_executed: bool,
    fix_prompt_generation_action_executed: bool,
    next_prompt_generation_action_executed: bool,
    result_assimilation_chain_action_executed: bool,
    manual_stop_executed: bool,
    blocked_executed: bool,
    delegated_existing_path_kind: str,
    delegated_existing_status: str,
    delegated_existing_next_action: str,
    delegated_existing_attempted: bool,
    delegated_existing_completed: bool,
    existing_truth_requires_revalidation: bool,
    existing_truth_revalidated: bool,
    non_selected_actions_noop: bool,
    source_result_class: str,
    prompt219_result_ready_for_assimilation: bool,
    prompt219_result_assimilation_source: str,
    prompt219_result_next_stage: str,
    source_should_continue_local_loop: bool,
    source_should_start_unbounded_loop: bool,
    source_should_invoke_codex: bool,
    source_should_execute_rollback: bool,
    source_should_execute_commit: bool,
    source_should_push: bool,
    source_manual_review_required: bool,
    source_should_stop: bool,
    source_stop_reason: str,
    source_next_action: str,
    bounded_multistep_handoff_guard_status: str,
    direct_retrigger_followup_guard_status: str,
    direct_retrigger_result_assimilation_status: str,
    direct_retrigger_coordinator_status: str,
    stale_fresh_ordering_gate_status: str,
    one_bounded_continuation_coordinator_status: str,
    final_runtime_continuation_guard_status: str,
    multi_cycle_controller_status: str,
    generated_prompt_reentry_readiness_status: str,
    generated_prompt_reentry_routing_status: str,
    codex_reentry_invocation_status: str,
    rollback_execution_status: str,
    rollback_result_assimilation_status: str,
    commit_tag_execution_status: str,
    commit_tag_result_assimilation_status: str,
    fix_prompt_readiness_status: str,
    fix_prompt_generation_status: str,
    next_prompt_readiness_status: str,
    next_prompt_generation_status: str,
) -> dict[str, Any]:
    allowed_statuses = {
        "bounded_multistep_execution_result_completed_fresh_action",
        "bounded_multistep_execution_result_completed_existing_truth_revalidated",
        "bounded_multistep_execution_result_blocked_existing_truth_revalidation",
        "bounded_multistep_execution_result_blocked_existing_path",
        "bounded_multistep_execution_result_manual_stop",
        "bounded_multistep_execution_result_failed",
        "bounded_multistep_execution_result_blocked",
        "bounded_multistep_execution_result_blocked_non_selected_action_activity",
        "bounded_multistep_execution_result_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_result_classes = {
        "completed_fresh_action",
        "completed_existing_truth_revalidated",
        "blocked_existing_truth_revalidation",
        "blocked_existing_path",
        "manual_stop",
        "failed",
        "blocked",
        "blocked_non_selected_action_activity",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "prepare_bounded_next_step_decision",
        "manual_review_required",
        "insufficient_truth",
    }
    runtime_posture = [
        "prompt219_bounded_multistep_execution_result_assimilation",
        "metadata_only",
        "result_assimilation_only",
        "no_downstream_execution",
        "no_retry",
        "no_loop",
        "no_codex_invocation",
        "no_rollback_execution",
        "no_commit_execution",
        "no_push",
    ]

    normalized_source_status = _normalize_text(
        bounded_multistep_execution_coordinator_status,
        default="insufficient_truth",
    )
    normalized_source_block_reason = _normalize_text(
        execution_coordinator_block_reason,
        default="",
    )
    normalized_source = _normalize_text(
        execution_coordinator_source,
        default="prompt218_bounded_multistep_execution_coordinator",
    )
    normalized_selected_kind = _normalize_text(selected_action_kind, default="")
    normalized_selected_action = _normalize_text(
        selected_action_action,
        default="manual_review_required",
    )
    normalized_delegated_kind = _normalize_text(delegated_existing_path_kind, default="none")
    normalized_delegated_status = _normalize_text(delegated_existing_status, default="")
    normalized_delegated_next_action = _normalize_text(
        delegated_existing_next_action,
        default="",
    )
    normalized_source_result_class = _normalize_text(source_result_class, default="")
    normalized_assimilation_source = _normalize_text(
        prompt219_result_assimilation_source,
        default="",
    )
    normalized_assimilation_next_stage = _normalize_text(
        prompt219_result_next_stage,
        default="",
    )
    normalized_source_stop_reason = _normalize_text(source_stop_reason, default="")
    normalized_source_next_action = _normalize_text(
        source_next_action,
        default="manual_review_required",
    )
    normalized_handoff_guard_status = _normalize_text(
        bounded_multistep_handoff_guard_status,
        default="insufficient_truth",
    )
    normalized_direct_retrigger_followup_guard_status = _normalize_text(
        direct_retrigger_followup_guard_status,
        default="insufficient_truth",
    )
    normalized_direct_retrigger_result_assimilation_status = _normalize_text(
        direct_retrigger_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_direct_retrigger_coordinator_status = _normalize_text(
        direct_retrigger_coordinator_status,
        default="insufficient_truth",
    )
    normalized_stale_fresh_ordering_gate_status = _normalize_text(
        stale_fresh_ordering_gate_status,
        default="insufficient_truth",
    )
    normalized_one_bounded_continuation_coordinator_status = _normalize_text(
        one_bounded_continuation_coordinator_status,
        default="insufficient_truth",
    )
    normalized_final_runtime_continuation_guard_status = _normalize_text(
        final_runtime_continuation_guard_status,
        default="insufficient_truth",
    )
    normalized_multi_cycle_controller_status = _normalize_text(
        multi_cycle_controller_status,
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
    normalized_rollback_execution_status = _normalize_text(
        rollback_execution_status,
        default="insufficient_truth",
    )
    normalized_rollback_result_assimilation_status = _normalize_text(
        rollback_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_commit_tag_execution_status = _normalize_text(
        commit_tag_execution_status,
        default="insufficient_truth",
    )
    normalized_commit_tag_result_assimilation_status = _normalize_text(
        commit_tag_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_fix_prompt_readiness_status = _normalize_text(
        fix_prompt_readiness_status,
        default="insufficient_truth",
    )
    normalized_fix_prompt_generation_status = _normalize_text(
        fix_prompt_generation_status,
        default="insufficient_truth",
    )
    normalized_next_prompt_readiness_status = _normalize_text(
        next_prompt_readiness_status,
        default="insufficient_truth",
    )
    normalized_next_prompt_generation_status = _normalize_text(
        next_prompt_generation_status,
        default="insufficient_truth",
    )
    normalized_selected_payload = (
        dict(selected_action_payload) if isinstance(selected_action_payload, Mapping) else {}
    )
    normalized_conflicts = _normalize_string_list(conflicting_bounded_actions)

    source_status_indicates_manual = normalized_source_status == "bounded_multistep_execution_manual_stop"
    source_status_indicates_blocked = "blocked" in normalized_source_status
    source_status_indicates_failed = "failed" in normalized_source_status
    source_status_indicates_existing_truth_revalidation_block = (
        normalized_source_status == "bounded_multistep_execution_blocked_existing_truth_revalidation"
        or normalized_source_block_reason == "blocked_existing_truth_revalidation"
    )
    source_status_indicates_existing_path_block = bool(
        normalized_source_status
        in {
            "bounded_multistep_execution_blocked_existing_path",
            "bounded_multistep_execution_blocked_not_allowed",
            "bounded_multistep_execution_blocked_no_action",
            "bounded_multistep_execution_blocked_multiple_actions",
            "bounded_multistep_execution_blocked_insufficient_truth",
        }
        or normalized_source_block_reason
        in {
            "blocked_existing_bounded_path",
            "blocked_no_supported_action",
            "blocked_multiple_actions",
            "blocked_no_action",
            "blocked_not_allowed",
            "blocked_insufficient_bounded_multistep_execution_truth",
            "blocked_prompt217_not_authoritative",
            "blocked_prompt217_contract_invalid",
            "blocked_prompt218_contract_invalid",
        }
    )

    authoritative_selected = bool(
        bool(prompt219_result_ready_for_assimilation)
        and normalized_assimilation_source
        == "prompt218_bounded_multistep_execution_coordinator"
        and normalized_assimilation_next_stage
        == "bounded_multistep_execution_result_assimilation"
        and (
            bool(normalized_selected_kind)
            or source_status_indicates_manual
            or source_status_indicates_blocked
        )
        and (bool(normalized_source_status) or bool(normalized_source_result_class))
    )

    supported_non_stop_kinds = {
        "generated_prompt_reentry_action",
        "rollback_execution_action",
        "commit_tag_execution_action",
        "fix_prompt_generation_action",
        "next_prompt_generation_action",
        "result_assimilation_chain_action",
    }
    selected_is_non_stop_supported = normalized_selected_kind in supported_non_stop_kinds
    selected_exec_flag_for_kind = bool(
        (
            normalized_selected_kind == "generated_prompt_reentry_action"
            and bool(generated_prompt_reentry_action_executed)
        )
        or (
            normalized_selected_kind == "rollback_execution_action"
            and bool(rollback_execution_action_executed)
        )
        or (
            normalized_selected_kind == "commit_tag_execution_action"
            and bool(commit_tag_execution_action_executed)
        )
        or (
            normalized_selected_kind == "fix_prompt_generation_action"
            and bool(fix_prompt_generation_action_executed)
        )
        or (
            normalized_selected_kind == "next_prompt_generation_action"
            and bool(next_prompt_generation_action_executed)
        )
        or (
            normalized_selected_kind == "result_assimilation_chain_action"
            and bool(result_assimilation_chain_action_executed)
        )
    )
    selected_exec_flag_count = sum(
        [
            1 if bool(generated_prompt_reentry_action_executed) else 0,
            1 if bool(rollback_execution_action_executed) else 0,
            1 if bool(commit_tag_execution_action_executed) else 0,
            1 if bool(fix_prompt_generation_action_executed) else 0,
            1 if bool(next_prompt_generation_action_executed) else 0,
            1 if bool(result_assimilation_chain_action_executed) else 0,
        ]
    )
    exactly_one_selected_exec_flag = selected_exec_flag_count == 1

    delegated_status_terminal = bool(
        any(
            token in normalized_delegated_status
            for token in (
                "completed",
                "failed",
                "blocked",
                "manual_stop",
                "succeeded",
                "prompt_generated",
            )
        )
    )
    source_execution_status_terminal = bool(
        any(
            token in normalized_source_status
            for token in ("completed", "failed", "blocked", "manual_stop")
        )
    )
    result_handoff_marker = bool(
        normalized_source_next_action == "assimilate_bounded_multistep_execution_result"
        or bool(prompt219_result_ready_for_assimilation)
    )
    terminal_result_class_marker = normalized_source_result_class in {
        "generated_prompt_reentry_completed",
        "rollback_execution_completed",
        "commit_tag_execution_completed",
        "fix_prompt_generation_completed",
        "next_prompt_generation_completed",
        "result_assimilation_chain_completed",
        "manual_stop",
        "failed",
        "blocked",
    }
    path_specific_attempted_terminal = bool(
        bool(execution_coordinator_attempted)
        and selected_exec_flag_for_kind
        and normalized_delegated_kind == normalized_selected_kind
        and (delegated_status_terminal or source_execution_status_terminal)
    )
    path_specific_completed_classification = normalized_source_status in {
        "bounded_multistep_execution_generated_prompt_reentry_completed",
        "bounded_multistep_execution_rollback_completed",
        "bounded_multistep_execution_commit_tag_completed",
        "bounded_multistep_execution_fix_prompt_completed",
        "bounded_multistep_execution_next_prompt_completed",
        "bounded_multistep_execution_result_assimilation_completed",
    }
    terminal_result_detected = bool(
        path_specific_attempted_terminal
        or bool(delegated_existing_completed)
        or result_handoff_marker
        or terminal_result_class_marker
        or path_specific_completed_classification
    )
    terminal_result_source = ""
    if terminal_result_detected:
        if path_specific_attempted_terminal:
            terminal_result_source = "path_attempted_terminal_status"
        elif bool(delegated_existing_completed):
            terminal_result_source = "delegated_existing_completed"
        elif result_handoff_marker:
            terminal_result_source = "result_handoff_marker"
        elif terminal_result_class_marker:
            terminal_result_source = "terminal_result_class"
        else:
            terminal_result_source = "path_specific_completed_classification"

    fresh_bounded_action_detected = bool(
        bool(execution_coordinator_attempted)
        and selected_is_non_stop_supported
        and selected_exec_flag_for_kind
        and exactly_one_selected_exec_flag
        and normalized_delegated_kind == normalized_selected_kind
        and bool(delegated_existing_attempted)
        and (bool(delegated_existing_completed) or terminal_result_detected)
        and (
            not bool(existing_truth_requires_revalidation)
            or bool(existing_truth_revalidated)
        )
    )
    existing_truth_revalidated_detected = bool(
        bool(existing_truth_requires_revalidation)
        and bool(existing_truth_revalidated)
        and terminal_result_detected
        and (delegated_status_terminal or result_handoff_marker)
        and not fresh_bounded_action_detected
    )
    existing_truth_revalidation_failed_detected = bool(
        (
            bool(existing_truth_requires_revalidation)
            and not bool(existing_truth_revalidated)
        )
        or source_status_indicates_existing_truth_revalidation_block
    )
    existing_path_blocked_detected = bool(
        source_status_indicates_existing_path_block
        or normalized_selected_kind in {"blocked", ""}
        and source_status_indicates_blocked
    )

    status = "bounded_multistep_execution_result_blocked_insufficient_truth"
    result_selected = False
    result_available = False
    result_class = "insufficient_truth"
    result_block_reason = "blocked_insufficient_bounded_multistep_execution_result_truth"
    source_execution_status = normalized_source_status
    source_execution_attempted = bool(execution_coordinator_attempted)
    source_execution_completed = bool(execution_coordinator_completed)
    source_execution_failed = bool(execution_coordinator_failed)
    non_selected_actions_noop_confirmed = bool(non_selected_actions_noop)
    controller_feedback_ready = False
    controller_feedback_kind = "none"
    controller_feedback_source = "prompt218_bounded_multistep_execution_coordinator"
    controller_feedback_payload: dict[str, Any] = {}
    next_bounded_control_target_ready = False
    next_bounded_control_target_kind = "manual_stop"
    next_bounded_control_target_action = "manual_review_required"
    next_bounded_control_target_payload: dict[str, Any] = {}
    should_prepare_next_multistep_decision = False
    should_prepare_result_assimilation_chain = False
    should_prepare_manual_review = True
    out_should_continue_local_loop = False
    out_should_start_unbounded_loop = False
    out_should_invoke_codex = False
    out_should_execute_rollback = False
    out_should_execute_commit = False
    out_should_push = False
    out_manual_review_required = True
    out_should_stop = True
    out_stop_reason = normalized_source_stop_reason or "insufficient_bounded_multistep_execution_result_truth"
    out_next_action = "manual_review_required"

    if not authoritative_selected:
        status = "bounded_multistep_execution_result_blocked_insufficient_truth"
        result_selected = False
        result_available = False
    else:
        result_selected = True
        result_available = True

        if (
            selected_is_non_stop_supported
            and (fresh_bounded_action_detected or existing_truth_revalidated_detected)
            and not bool(non_selected_actions_noop)
        ):
            status = "bounded_multistep_execution_result_blocked_non_selected_action_activity"
            result_class = "blocked_non_selected_action_activity"
            result_block_reason = "blocked_non_selected_action_activity"
            should_prepare_manual_review = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = "blocked_non_selected_action_activity"
            out_next_action = "manual_review_required"
        elif selected_is_non_stop_supported and fresh_bounded_action_detected:
            status = "bounded_multistep_execution_result_completed_fresh_action"
            result_class = "completed_fresh_action"
            result_block_reason = ""
            controller_feedback_ready = True
            controller_feedback_kind = "bounded_multistep_fresh_action_completed"
            controller_feedback_payload = {
                "feedback": "bounded_multistep_fresh_action_completed",
                "source": "prompt218_bounded_multistep_execution_coordinator",
                "selected_action_kind": normalized_selected_kind,
                "delegated_existing_status": normalized_delegated_status,
                "next_action": "prepare_bounded_next_step_decision",
            }
            next_bounded_control_target_ready = True
            next_bounded_control_target_kind = "bounded_next_step_decision"
            next_bounded_control_target_action = "prepare_bounded_next_step_decision"
            next_bounded_control_target_payload = {
                "target": "bounded_next_step_decision",
                "source": "prompt219_bounded_multistep_execution_result_assimilation",
                "selected_action_kind": normalized_selected_kind,
                "next_action": "prepare_bounded_next_step_decision",
            }
            should_prepare_next_multistep_decision = True
            should_prepare_result_assimilation_chain = True
            should_prepare_manual_review = False
            out_manual_review_required = False
            out_should_stop = False
            out_stop_reason = ""
            out_next_action = "prepare_bounded_next_step_decision"
        elif selected_is_non_stop_supported and existing_truth_revalidated_detected:
            status = "bounded_multistep_execution_result_completed_existing_truth_revalidated"
            result_class = "completed_existing_truth_revalidated"
            result_block_reason = ""
            controller_feedback_ready = True
            controller_feedback_kind = "bounded_multistep_existing_truth_revalidated"
            controller_feedback_payload = {
                "feedback": "bounded_multistep_existing_truth_revalidated",
                "source": "prompt218_bounded_multistep_execution_coordinator",
                "selected_action_kind": normalized_selected_kind,
                "delegated_existing_status": normalized_delegated_status,
                "existing_truth_revalidated": True,
                "fresh_bounded_action_detected": False,
                "next_action": "prepare_bounded_next_step_decision",
            }
            next_bounded_control_target_ready = True
            next_bounded_control_target_kind = "bounded_next_step_decision"
            next_bounded_control_target_action = "prepare_bounded_next_step_decision"
            next_bounded_control_target_payload = {
                "target": "bounded_next_step_decision",
                "source": "prompt219_bounded_multistep_execution_result_assimilation",
                "selected_action_kind": normalized_selected_kind,
                "next_action": "prepare_bounded_next_step_decision",
            }
            should_prepare_next_multistep_decision = True
            should_prepare_result_assimilation_chain = True
            should_prepare_manual_review = False
            out_manual_review_required = False
            out_should_stop = False
            out_stop_reason = ""
            out_next_action = "prepare_bounded_next_step_decision"
        elif existing_truth_revalidation_failed_detected:
            status = "bounded_multistep_execution_result_blocked_existing_truth_revalidation"
            result_class = "blocked_existing_truth_revalidation"
            result_block_reason = "blocked_existing_truth_revalidation"
            should_prepare_manual_review = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = "blocked_existing_truth_revalidation"
            out_next_action = "manual_review_required"
        elif existing_path_blocked_detected:
            status = "bounded_multistep_execution_result_blocked_existing_path"
            result_class = "blocked_existing_path"
            result_block_reason = "blocked_existing_path"
            should_prepare_manual_review = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = "blocked_existing_path"
            out_next_action = "manual_review_required"
        elif normalized_selected_kind == "manual_stop" or bool(manual_stop_executed):
            status = "bounded_multistep_execution_result_manual_stop"
            result_class = "manual_stop"
            result_block_reason = ""
            controller_feedback_ready = True
            controller_feedback_kind = "manual_stop"
            controller_feedback_payload = {
                "feedback": "manual_stop",
                "source": "prompt218_bounded_multistep_execution_coordinator",
                "stop_reason": normalized_source_stop_reason or "manual_stop",
                "next_action": "manual_review_required",
            }
            next_bounded_control_target_ready = True
            next_bounded_control_target_kind = "manual_stop"
            next_bounded_control_target_action = "manual_review_required"
            next_bounded_control_target_payload = {
                "target": "manual_stop",
                "source": "prompt219_bounded_multistep_execution_result_assimilation",
                "stop_reason": normalized_source_stop_reason or "manual_stop",
                "next_action": "manual_review_required",
            }
            should_prepare_manual_review = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = normalized_source_stop_reason or "manual_stop"
            out_next_action = "manual_review_required"
        elif bool(execution_coordinator_failed) or source_status_indicates_failed:
            status = "bounded_multistep_execution_result_failed"
            result_class = "failed"
            result_block_reason = "bounded_multistep_execution_failed"
            controller_feedback_ready = True
            controller_feedback_kind = "bounded_multistep_execution_failed"
            controller_feedback_payload = {
                "feedback": "bounded_multistep_execution_failed",
                "source": "prompt218_bounded_multistep_execution_coordinator",
                "stop_reason": normalized_source_block_reason
                or "bounded_multistep_execution_failed",
                "next_action": "manual_review_required",
            }
            next_bounded_control_target_ready = True
            next_bounded_control_target_kind = "manual_stop"
            next_bounded_control_target_action = "manual_review_required"
            next_bounded_control_target_payload = {
                "target": "manual_stop",
                "source": "prompt219_bounded_multistep_execution_result_assimilation",
                "stop_reason": normalized_source_block_reason
                or "bounded_multistep_execution_failed",
                "next_action": "manual_review_required",
            }
            should_prepare_manual_review = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = normalized_source_block_reason or "bounded_multistep_execution_failed"
            out_next_action = "manual_review_required"
        elif source_status_indicates_blocked or bool(blocked_executed):
            status = "bounded_multistep_execution_result_blocked"
            result_class = "blocked"
            result_block_reason = normalized_source_block_reason or "bounded_multistep_execution_blocked"
            controller_feedback_ready = True
            controller_feedback_kind = "bounded_multistep_execution_blocked"
            controller_feedback_payload = {
                "feedback": "bounded_multistep_execution_blocked",
                "source": "prompt218_bounded_multistep_execution_coordinator",
                "stop_reason": normalized_source_block_reason
                or "bounded_multistep_execution_blocked",
                "next_action": "manual_review_required",
            }
            next_bounded_control_target_ready = True
            next_bounded_control_target_kind = "manual_stop"
            next_bounded_control_target_action = "manual_review_required"
            next_bounded_control_target_payload = {
                "target": "manual_stop",
                "source": "prompt219_bounded_multistep_execution_result_assimilation",
                "stop_reason": normalized_source_block_reason
                or "bounded_multistep_execution_blocked",
                "next_action": "manual_review_required",
            }
            should_prepare_manual_review = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = normalized_source_block_reason or "bounded_multistep_execution_blocked"
            out_next_action = "manual_review_required"
        else:
            status = "bounded_multistep_execution_result_blocked_insufficient_truth"
            result_class = "insufficient_truth"
            result_block_reason = "blocked_insufficient_bounded_multistep_execution_result_truth"
            controller_feedback_ready = False
            next_bounded_control_target_ready = True
            next_bounded_control_target_kind = "manual_stop"
            next_bounded_control_target_action = "manual_review_required"
            next_bounded_control_target_payload = {
                "target": "manual_stop",
                "source": "prompt219_bounded_multistep_execution_result_assimilation",
                "stop_reason": "insufficient_bounded_multistep_execution_result_truth",
                "next_action": "manual_review_required",
            }
            should_prepare_manual_review = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = "insufficient_bounded_multistep_execution_result_truth"
            out_next_action = "manual_review_required"

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if result_class not in allowed_result_classes:
        result_class = "insufficient_truth"
    if out_next_action not in allowed_next_actions:
        out_next_action = "insufficient_truth"
    if status == "insufficient_truth":
        status = "bounded_multistep_execution_result_blocked_insufficient_truth"
        result_selected = False
        result_available = False
        result_class = "insufficient_truth"
        result_block_reason = "blocked_insufficient_bounded_multistep_execution_result_truth"
        non_selected_actions_noop_confirmed = False
        terminal_result_detected = False
        terminal_result_source = ""
        controller_feedback_ready = False
        controller_feedback_kind = "none"
        controller_feedback_source = "prompt218_bounded_multistep_execution_coordinator"
        controller_feedback_payload = {}
        next_bounded_control_target_ready = False
        next_bounded_control_target_kind = "manual_stop"
        next_bounded_control_target_action = "manual_review_required"
        next_bounded_control_target_payload = {}
        should_prepare_next_multistep_decision = False
        should_prepare_result_assimilation_chain = False
        should_prepare_manual_review = True
        out_should_continue_local_loop = False
        out_should_start_unbounded_loop = False
        out_should_invoke_codex = False
        out_should_execute_rollback = False
        out_should_execute_commit = False
        out_should_push = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_bounded_multistep_execution_result_truth"
        out_next_action = "manual_review_required"

    return {
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_status": status,
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_result_selected": bool(
            result_selected
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_result_available": bool(
            result_available
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_result_class": result_class,
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_result_block_reason": (
            result_block_reason
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_source_selected_action_kind": (
            normalized_selected_kind
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_source_selected_action_action": (
            normalized_selected_action
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_source_execution_status": (
            source_execution_status
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_source_execution_attempted": bool(
            source_execution_attempted
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_source_execution_completed": bool(
            source_execution_completed
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_source_execution_failed": bool(
            source_execution_failed
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_non_selected_actions_noop_confirmed": bool(
            non_selected_actions_noop_confirmed
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_delegated_existing_path_kind": (
            normalized_delegated_kind
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_delegated_existing_status": (
            normalized_delegated_status
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_delegated_existing_next_action": (
            normalized_delegated_next_action
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_delegated_existing_attempted": bool(
            delegated_existing_attempted
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_delegated_existing_completed": bool(
            delegated_existing_completed
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_fresh_bounded_action_detected": bool(
            fresh_bounded_action_detected
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_existing_truth_revalidated_detected": bool(
            existing_truth_revalidated_detected
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_existing_truth_revalidation_failed_detected": bool(
            existing_truth_revalidation_failed_detected
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_existing_path_blocked_detected": bool(
            existing_path_blocked_detected
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_terminal_result_detected": bool(
            terminal_result_detected
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_terminal_result_source": (
            terminal_result_source
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_controller_feedback_ready": bool(
            controller_feedback_ready
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_controller_feedback_kind": (
            controller_feedback_kind
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_controller_feedback_source": (
            controller_feedback_source
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_controller_feedback_payload": (
            controller_feedback_payload if isinstance(controller_feedback_payload, Mapping) else {}
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_next_bounded_control_target_ready": bool(
            next_bounded_control_target_ready
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_next_bounded_control_target_kind": (
            next_bounded_control_target_kind
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_next_bounded_control_target_action": (
            next_bounded_control_target_action
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_next_bounded_control_target_payload": (
            next_bounded_control_target_payload
            if isinstance(next_bounded_control_target_payload, Mapping)
            else {}
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_should_prepare_next_multistep_decision": bool(
            should_prepare_next_multistep_decision
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_should_prepare_result_assimilation_chain": bool(
            should_prepare_result_assimilation_chain
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_should_prepare_manual_review": bool(
            should_prepare_manual_review
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_should_continue_local_loop": bool(
            out_should_continue_local_loop
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_should_start_unbounded_loop": bool(
            out_should_start_unbounded_loop
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_should_invoke_codex": bool(
            out_should_invoke_codex
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_should_execute_rollback": bool(
            out_should_execute_rollback
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_should_execute_commit": bool(
            out_should_execute_commit
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_should_push": bool(
            out_should_push
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_manual_review_required": bool(
            out_manual_review_required
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_should_stop": bool(
            out_should_stop
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_stop_reason": (
            out_stop_reason
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_next_action": (
            out_next_action
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_bounded_multistep_execution_result_assimilation_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_source_status,
                    normalized_source_block_reason,
                    normalized_source,
                    normalized_selected_kind,
                    normalized_selected_action,
                    normalized_delegated_kind,
                    normalized_delegated_status,
                    normalized_delegated_next_action,
                    normalized_source_result_class,
                    normalized_assimilation_source,
                    normalized_assimilation_next_stage,
                    normalized_source_stop_reason,
                    normalized_source_next_action,
                    normalized_handoff_guard_status,
                    normalized_direct_retrigger_followup_guard_status,
                    normalized_direct_retrigger_result_assimilation_status,
                    normalized_direct_retrigger_coordinator_status,
                    normalized_stale_fresh_ordering_gate_status,
                    normalized_one_bounded_continuation_coordinator_status,
                    normalized_final_runtime_continuation_guard_status,
                    normalized_multi_cycle_controller_status,
                    normalized_generated_prompt_reentry_readiness_status,
                    normalized_generated_prompt_reentry_routing_status,
                    normalized_codex_reentry_invocation_status,
                    normalized_rollback_execution_status,
                    normalized_rollback_result_assimilation_status,
                    normalized_commit_tag_execution_status,
                    normalized_commit_tag_result_assimilation_status,
                    normalized_fix_prompt_readiness_status,
                    normalized_fix_prompt_generation_status,
                    normalized_next_prompt_readiness_status,
                    normalized_next_prompt_generation_status,
                    "prompt218_not_authoritative_for_prompt219"
                    if not authoritative_selected
                    else "",
                    "prompt218_contract_invalid" if not bool(prompt218_contract_valid) else "",
                    "execution_coordinator_unavailable"
                    if not bool(execution_coordinator_available)
                    else "",
                    "execution_coordinator_not_allowed"
                    if not bool(execution_coordinator_allowed)
                    else "",
                    "exactly_one_bounded_action_false"
                    if not bool(exactly_one_bounded_action)
                    else "",
                    "bounded_action_conflict_detected"
                    if bool(bounded_action_conflict_detected)
                    else "",
                    "conflicting_bounded_actions_present" if normalized_conflicts else "",
                    "source_requested_continue_local_loop"
                    if bool(source_should_continue_local_loop)
                    else "",
                    "source_requested_unbounded_loop"
                    if bool(source_should_start_unbounded_loop)
                    else "",
                    "source_requested_codex_invocation"
                    if bool(source_should_invoke_codex)
                    else "",
                    "source_requested_rollback_execution"
                    if bool(source_should_execute_rollback)
                    else "",
                    "source_requested_commit_execution"
                    if bool(source_should_execute_commit)
                    else "",
                    "source_requested_push" if bool(source_should_push) else "",
                    "source_manual_review_required"
                    if bool(source_manual_review_required)
                    else "",
                    "source_should_stop" if bool(source_should_stop) else "",
                ]
            )
        ),
    }

def _build_project_browser_autonomous_bounded_n_step_result_assimilation_state(
    *,
    bounded_n_step_coordinator_status: str,
    n_step_coordinator_available: bool,
    n_step_coordinator_allowed: bool,
    n_step_coordinator_attempted: bool,
    n_step_coordinator_completed: bool,
    n_step_coordinator_failed: bool,
    n_step_coordinator_block_reason: str,
    n_step_coordinator_source: str,
    prompt221_contract_valid: bool,
    selected_step_kind: str,
    selected_step_action: str,
    selected_step_payload: Any,
    max_continuation_steps: int,
    actual_steps_allowed: int,
    actual_steps_attempted: int,
    actual_steps_completed: int,
    allow_unbounded_loop: bool,
    allow_retry: bool,
    exactly_one_step_target: bool,
    step_conflict_detected: bool,
    conflicting_step_targets: Sequence[Any],
    bounded_next_step_decision_executed: bool,
    result_assimilation_chain_executed: bool,
    manual_stop_executed: bool,
    blocked_executed: bool,
    delegated_existing_path_kind: str,
    delegated_existing_status: str,
    delegated_existing_next_action: str,
    delegated_existing_attempted: bool,
    delegated_existing_completed: bool,
    existing_truth_requires_guarded_continuation: bool,
    existing_truth_guarded_revalidation_applied: bool,
    non_selected_steps_noop: bool,
    source_result_class: str,
    prompt222_result_ready_for_assimilation: bool,
    prompt222_result_assimilation_source: str,
    prompt222_result_next_stage: str,
    source_should_continue_local_loop: bool,
    source_should_start_unbounded_loop: bool,
    source_should_invoke_codex: bool,
    source_should_execute_rollback: bool,
    source_should_execute_commit: bool,
    source_should_push: bool,
    source_manual_review_required: bool,
    source_should_stop: bool,
    source_stop_reason: str,
    source_next_action: str,
    bounded_continuation_decision_status: str,
    bounded_multistep_execution_result_assimilation_status: str,
    bounded_multistep_execution_coordinator_status: str,
    bounded_multistep_handoff_guard_status: str,
    direct_retrigger_followup_guard_status: str,
    direct_retrigger_result_assimilation_status: str,
    multi_cycle_controller_status: str,
    terminal_lane_decision_status: str,
    lane_contract_guard_status: str,
    guarded_lane_dispatch_status: str,
    next_step_launch_contract_status: str,
    next_step_launch_execution_status: str,
    next_step_launch_result_assimilation_status: str,
    generated_prompt_reentry_readiness_status: str,
    generated_prompt_reentry_routing_status: str,
    codex_reentry_invocation_status: str,
    rollback_execution_status: str,
    rollback_result_assimilation_status: str,
    commit_tag_execution_status: str,
    commit_tag_result_assimilation_status: str,
    fix_prompt_readiness_status: str,
    fix_prompt_generation_status: str,
    next_prompt_readiness_status: str,
    next_prompt_generation_status: str,
) -> dict[str, Any]:
    allowed_statuses = {
        "bounded_n_step_result_completed_fresh_surface",
        "bounded_n_step_result_completed_existing_truth_guarded",
        "bounded_n_step_result_completed_existing_truth",
        "bounded_n_step_result_blocked_existing_path",
        "bounded_n_step_result_blocked_step_accounting_violation",
        "bounded_n_step_result_blocked_non_selected_step_activity",
        "bounded_n_step_result_manual_stop",
        "bounded_n_step_result_failed",
        "bounded_n_step_result_blocked",
        "bounded_n_step_result_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_result_classes = {
        "completed_fresh_surface",
        "completed_existing_truth_guarded",
        "completed_existing_truth",
        "blocked_existing_path",
        "blocked_step_accounting_violation",
        "blocked_non_selected_step_activity",
        "manual_stop",
        "failed",
        "blocked",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "prepare_bounded_raise_to_2_preflight",
        "prepare_end_to_end_flow_check",
        "manual_review_required",
        "insufficient_truth",
    }
    runtime_posture = [
        "prompt222_bounded_n_step_result_assimilation",
        "metadata_only",
        "result_assimilation_only",
        "no_downstream_execution",
        "max_continuation_steps_one_only",
        "no_raise_of_max_continuation_steps",
        "no_retry",
        "no_loop",
        "no_unbounded_loop",
        "no_push",
    ]

    normalized_source_status = _normalize_text(
        bounded_n_step_coordinator_status,
        default="insufficient_truth",
    )
    normalized_source_block_reason = _normalize_text(
        n_step_coordinator_block_reason,
        default="",
    )
    normalized_source = _normalize_text(
        n_step_coordinator_source,
        default="prompt220_bounded_continuation_decision",
    )
    normalized_selected_step_kind = _normalize_text(selected_step_kind, default="")
    normalized_selected_step_action = _normalize_text(
        selected_step_action,
        default="manual_review_required",
    )
    normalized_delegated_kind = _normalize_text(delegated_existing_path_kind, default="none")
    normalized_delegated_status = _normalize_text(delegated_existing_status, default="")
    normalized_delegated_next_action = _normalize_text(
        delegated_existing_next_action,
        default="",
    )
    normalized_source_result_class = _normalize_text(source_result_class, default="")
    normalized_assimilation_source = _normalize_text(
        prompt222_result_assimilation_source,
        default="",
    )
    normalized_assimilation_next_stage = _normalize_text(
        prompt222_result_next_stage,
        default="",
    )
    normalized_source_stop_reason = _normalize_text(source_stop_reason, default="")
    normalized_source_next_action = _normalize_text(
        source_next_action,
        default="manual_review_required",
    )
    normalized_decision_status = _normalize_text(
        bounded_continuation_decision_status,
        default="insufficient_truth",
    )
    normalized_result_assimilation_status = _normalize_text(
        bounded_multistep_execution_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_execution_coordinator_status = _normalize_text(
        bounded_multistep_execution_coordinator_status,
        default="insufficient_truth",
    )
    normalized_handoff_guard_status = _normalize_text(
        bounded_multistep_handoff_guard_status,
        default="insufficient_truth",
    )
    normalized_direct_retrigger_followup_guard_status = _normalize_text(
        direct_retrigger_followup_guard_status,
        default="insufficient_truth",
    )
    normalized_direct_retrigger_result_assimilation_status = _normalize_text(
        direct_retrigger_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_multi_cycle_controller_status = _normalize_text(
        multi_cycle_controller_status,
        default="insufficient_truth",
    )
    normalized_terminal_lane_decision_status = _normalize_text(
        terminal_lane_decision_status,
        default="insufficient_truth",
    )
    normalized_lane_contract_guard_status = _normalize_text(
        lane_contract_guard_status,
        default="insufficient_truth",
    )
    normalized_guarded_lane_dispatch_status = _normalize_text(
        guarded_lane_dispatch_status,
        default="insufficient_truth",
    )
    normalized_next_step_launch_contract_status = _normalize_text(
        next_step_launch_contract_status,
        default="insufficient_truth",
    )
    normalized_next_step_launch_execution_status = _normalize_text(
        next_step_launch_execution_status,
        default="insufficient_truth",
    )
    normalized_next_step_launch_result_assimilation_status = _normalize_text(
        next_step_launch_result_assimilation_status,
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
    normalized_rollback_execution_status = _normalize_text(
        rollback_execution_status,
        default="insufficient_truth",
    )
    normalized_rollback_result_assimilation_status = _normalize_text(
        rollback_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_commit_tag_execution_status = _normalize_text(
        commit_tag_execution_status,
        default="insufficient_truth",
    )
    normalized_commit_tag_result_assimilation_status = _normalize_text(
        commit_tag_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_fix_prompt_readiness_status = _normalize_text(
        fix_prompt_readiness_status,
        default="insufficient_truth",
    )
    normalized_fix_prompt_generation_status = _normalize_text(
        fix_prompt_generation_status,
        default="insufficient_truth",
    )
    normalized_next_prompt_readiness_status = _normalize_text(
        next_prompt_readiness_status,
        default="insufficient_truth",
    )
    normalized_next_prompt_generation_status = _normalize_text(
        next_prompt_generation_status,
        default="insufficient_truth",
    )
    normalized_selected_payload = (
        dict(selected_step_payload) if isinstance(selected_step_payload, Mapping) else {}
    )
    normalized_conflicts = _normalize_string_list(conflicting_step_targets)

    source_actual_steps_allowed = _as_non_negative_int(actual_steps_allowed, default=0)
    source_actual_steps_attempted = _as_non_negative_int(actual_steps_attempted, default=0)
    source_actual_steps_completed = _as_non_negative_int(actual_steps_completed, default=0)
    source_max_continuation_steps = (
        1 if _as_non_negative_int(max_continuation_steps, default=1) == 1 else 0
    )

    source_status_indicates_manual = normalized_source_status == "bounded_n_step_coordinator_manual_stop"
    source_status_indicates_blocked = "blocked" in normalized_source_status
    source_status_indicates_failed = "failed" in normalized_source_status
    source_status_indicates_insufficient = normalized_source_status in {
        "bounded_n_step_coordinator_blocked_insufficient_truth",
        "insufficient_truth",
    }

    authoritative_selected = bool(
        bool(prompt222_result_ready_for_assimilation)
        and normalized_assimilation_source == "prompt221_bounded_n_step_coordinator"
        and normalized_assimilation_next_stage == "bounded_n_step_result_assimilation"
        and (
            bool(normalized_selected_step_kind)
            or source_status_indicates_manual
            or source_status_indicates_blocked
        )
        and (bool(normalized_source_status) or bool(normalized_source_result_class))
    )

    one_step_accounting_valid = bool(
        source_max_continuation_steps == 1
        and source_actual_steps_allowed in {0, 1}
        and source_actual_steps_attempted <= 1
        and source_actual_steps_completed <= 1
        and source_actual_steps_completed <= source_actual_steps_attempted
        and not bool(allow_unbounded_loop)
        and not bool(allow_retry)
        and not bool(source_should_continue_local_loop)
        and not bool(source_should_start_unbounded_loop)
    )
    non_selected_steps_noop_confirmed = bool(non_selected_steps_noop)

    delegated_status_terminal = bool(
        any(
            token in normalized_delegated_status
            for token in (
                "completed",
                "blocked",
                "failed",
                "manual_stop",
                "result_assimilation",
                "next_step",
            )
        )
    )
    source_status_terminal = bool(
        any(
            token in normalized_source_status
            for token in ("completed", "blocked", "failed", "manual_stop")
        )
    )
    handoff_ready_marker = bool(
        normalized_source_next_action == "assimilate_bounded_n_step_result"
        or (
            bool(prompt222_result_ready_for_assimilation)
            and normalized_assimilation_next_stage == "bounded_n_step_result_assimilation"
        )
    )
    terminal_result_class_marker = normalized_source_result_class in {
        "next_step_completed",
        "result_assimilation_completed",
        "manual_stop",
        "blocked",
        "failed",
    }
    path_specific_completed_classification = normalized_source_status in {
        "bounded_n_step_coordinator_next_step_completed",
        "bounded_n_step_coordinator_result_assimilation_completed",
    }
    terminal_result_detected = bool(
        bool(delegated_existing_completed)
        or bool(delegated_existing_attempted) and delegated_status_terminal
        or handoff_ready_marker
        or terminal_result_class_marker
        or path_specific_completed_classification
    )
    terminal_result_source = ""
    if terminal_result_detected:
        if bool(delegated_existing_completed):
            terminal_result_source = "delegated_existing_completed"
        elif bool(delegated_existing_attempted) and delegated_status_terminal:
            terminal_result_source = "delegated_existing_attempted_terminal_status"
        elif handoff_ready_marker:
            terminal_result_source = "handoff_ready_metadata"
        elif terminal_result_class_marker:
            terminal_result_source = "terminal_result_class"
        else:
            terminal_result_source = "path_specific_completed_classification"

    completed_fresh_surface_detected = bool(
        normalized_selected_step_kind == "bounded_next_step_decision"
        and bool(n_step_coordinator_attempted)
        and bool(bounded_next_step_decision_executed)
        and bool(delegated_existing_attempted)
        and (bool(delegated_existing_completed) or terminal_result_detected)
        and one_step_accounting_valid
    )
    completed_existing_truth_detected = bool(
        normalized_selected_step_kind
        in {"bounded_next_step_decision", "result_assimilation_chain"}
        and terminal_result_detected
        and not completed_fresh_surface_detected
        and one_step_accounting_valid
    )
    guarded_existing_truth_detected = bool(
        bool(existing_truth_requires_guarded_continuation)
        and bool(existing_truth_guarded_revalidation_applied)
        and completed_existing_truth_detected
    )
    existing_path_blocked_detected = bool(
        normalized_source_status
        in {
            "bounded_n_step_coordinator_blocked_existing_path",
            "bounded_n_step_coordinator_blocked_no_step",
            "bounded_n_step_coordinator_blocked_multiple_steps",
            "bounded_n_step_coordinator_blocked_conflict",
            "bounded_n_step_coordinator_blocked_insufficient_truth",
        }
        or normalized_source_block_reason
        in {
            "blocked_existing_bounded_path",
            "blocked_no_supported_step",
            "blocked_multiple_steps",
            "blocked_conflict_state",
            "blocked_insufficient_bounded_n_step_truth",
        }
    )

    status = "bounded_n_step_result_blocked_insufficient_truth"
    result_selected = False
    result_available = False
    result_class = "insufficient_truth"
    result_block_reason = "blocked_insufficient_bounded_n_step_result_truth"
    source_n_step_status = normalized_source_status
    source_n_step_attempted = bool(n_step_coordinator_attempted)
    source_n_step_completed = bool(n_step_coordinator_completed)
    source_n_step_failed = bool(n_step_coordinator_failed)
    stop_policy_passed = False
    stop_policy_block_reason = "blocked_insufficient_bounded_n_step_result_truth"
    n_step_runtime_safety_confidence = "insufficient"
    n_step_raise_to_2_candidate = False
    n_step_raise_block_reason = "insufficient_bounded_n_step_result_truth"
    next_bounded_control_target_ready = False
    next_bounded_control_target_kind = "manual_stop"
    next_bounded_control_target_action = "manual_review_required"
    next_bounded_control_target_payload: dict[str, Any] = {}
    controller_feedback_ready = False
    controller_feedback_kind = "none"
    controller_feedback_source = "prompt221_bounded_n_step_coordinator"
    controller_feedback_payload: dict[str, Any] = {}
    should_prepare_raise_to_2_preflight = False
    should_prepare_end_to_end_flow_check = False
    should_prepare_manual_review = True
    out_should_continue_local_loop = False
    out_should_start_unbounded_loop = False
    out_should_invoke_codex = False
    out_should_execute_rollback = False
    out_should_execute_commit = False
    out_should_push = False
    out_manual_review_required = True
    out_should_stop = True
    out_stop_reason = normalized_source_stop_reason or "insufficient_bounded_n_step_result_truth"
    out_next_action = "manual_review_required"

    successful_non_stop_selected_step = bool(
        normalized_selected_step_kind in {"bounded_next_step_decision", "result_assimilation_chain"}
        and normalized_source_status
        in {
            "bounded_n_step_coordinator_next_step_completed",
            "bounded_n_step_coordinator_result_assimilation_completed",
        }
    )

    if authoritative_selected:
        result_selected = True
        result_available = True

        if not one_step_accounting_valid:
            status = "bounded_n_step_result_blocked_step_accounting_violation"
            result_class = "blocked_step_accounting_violation"
            result_block_reason = "blocked_step_accounting_violation"
            n_step_runtime_safety_confidence = "blocked"
            n_step_raise_to_2_candidate = False
            n_step_raise_block_reason = "step_accounting_violation"
            should_prepare_manual_review = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = "step_accounting_violation"
            out_next_action = "manual_review_required"
        elif successful_non_stop_selected_step and not non_selected_steps_noop_confirmed:
            status = "bounded_n_step_result_blocked_non_selected_step_activity"
            result_class = "blocked_non_selected_step_activity"
            result_block_reason = "blocked_non_selected_step_activity"
            n_step_runtime_safety_confidence = "blocked"
            n_step_raise_to_2_candidate = False
            n_step_raise_block_reason = "non_selected_step_activity"
            should_prepare_manual_review = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = "blocked_non_selected_step_activity"
            out_next_action = "manual_review_required"
        elif completed_fresh_surface_detected:
            status = "bounded_n_step_result_completed_fresh_surface"
            result_class = "completed_fresh_surface"
            result_block_reason = ""
            n_step_runtime_safety_confidence = "high"
            n_step_raise_to_2_candidate = True
            n_step_raise_block_reason = ""
            next_bounded_control_target_ready = True
            next_bounded_control_target_kind = "raise_to_2_preflight"
            next_bounded_control_target_action = "prepare_bounded_raise_to_2_preflight"
            next_bounded_control_target_payload = {
                "target": "raise_to_2_preflight",
                "source": "prompt222_bounded_n_step_result_assimilation",
                "selected_step_kind": normalized_selected_step_kind,
                "runtime_safety_confidence": "high",
                "next_action": "prepare_bounded_raise_to_2_preflight",
            }
            controller_feedback_ready = True
            controller_feedback_kind = "bounded_n_step_completed_fresh_surface"
            controller_feedback_payload = {
                "feedback": "bounded_n_step_completed_fresh_surface",
                "source": "prompt221_bounded_n_step_coordinator",
                "selected_step_kind": normalized_selected_step_kind,
                "runtime_safety_confidence": "high",
                "n_step_raise_to_2_candidate": True,
                "next_action": "prepare_bounded_raise_to_2_preflight",
            }
            should_prepare_raise_to_2_preflight = True
            should_prepare_end_to_end_flow_check = False
            should_prepare_manual_review = False
            out_manual_review_required = False
            out_should_stop = False
            out_stop_reason = ""
            out_next_action = "prepare_bounded_raise_to_2_preflight"
        elif guarded_existing_truth_detected:
            status = "bounded_n_step_result_completed_existing_truth_guarded"
            result_class = "completed_existing_truth_guarded"
            result_block_reason = ""
            n_step_runtime_safety_confidence = "guarded"
            n_step_raise_to_2_candidate = False
            n_step_raise_block_reason = "existing_truth_guarded_requires_more_runtime_validation"
            next_bounded_control_target_ready = True
            next_bounded_control_target_kind = "end_to_end_flow_check"
            next_bounded_control_target_action = "prepare_end_to_end_flow_check"
            next_bounded_control_target_payload = {
                "target": "end_to_end_flow_check",
                "source": "prompt222_bounded_n_step_result_assimilation",
                "selected_step_kind": normalized_selected_step_kind,
                "runtime_safety_confidence": "guarded",
                "next_action": "prepare_end_to_end_flow_check",
            }
            controller_feedback_ready = True
            controller_feedback_kind = "bounded_n_step_completed_existing_truth"
            controller_feedback_payload = {
                "feedback": "bounded_n_step_completed_existing_truth",
                "source": "prompt221_bounded_n_step_coordinator",
                "selected_step_kind": normalized_selected_step_kind,
                "runtime_safety_confidence": "guarded",
                "n_step_raise_to_2_candidate": False,
                "next_action": "prepare_end_to_end_flow_check",
            }
            should_prepare_raise_to_2_preflight = False
            should_prepare_end_to_end_flow_check = True
            should_prepare_manual_review = False
            out_manual_review_required = False
            out_should_stop = False
            out_stop_reason = ""
            out_next_action = "prepare_end_to_end_flow_check"
        elif completed_existing_truth_detected and not guarded_existing_truth_detected:
            status = "bounded_n_step_result_completed_existing_truth"
            result_class = "completed_existing_truth"
            result_block_reason = ""
            n_step_runtime_safety_confidence = "medium"
            n_step_raise_to_2_candidate = False
            n_step_raise_block_reason = "fresh_surface_not_proven"
            next_bounded_control_target_ready = True
            next_bounded_control_target_kind = "end_to_end_flow_check"
            next_bounded_control_target_action = "prepare_end_to_end_flow_check"
            next_bounded_control_target_payload = {
                "target": "end_to_end_flow_check",
                "source": "prompt222_bounded_n_step_result_assimilation",
                "selected_step_kind": normalized_selected_step_kind,
                "runtime_safety_confidence": "medium",
                "next_action": "prepare_end_to_end_flow_check",
            }
            controller_feedback_ready = True
            controller_feedback_kind = "bounded_n_step_completed_existing_truth"
            controller_feedback_payload = {
                "feedback": "bounded_n_step_completed_existing_truth",
                "source": "prompt221_bounded_n_step_coordinator",
                "selected_step_kind": normalized_selected_step_kind,
                "runtime_safety_confidence": "medium",
                "n_step_raise_to_2_candidate": False,
                "next_action": "prepare_end_to_end_flow_check",
            }
            should_prepare_raise_to_2_preflight = False
            should_prepare_end_to_end_flow_check = True
            should_prepare_manual_review = False
            out_manual_review_required = False
            out_should_stop = False
            out_stop_reason = ""
            out_next_action = "prepare_end_to_end_flow_check"
        elif existing_path_blocked_detected:
            status = "bounded_n_step_result_blocked_existing_path"
            result_class = "blocked_existing_path"
            result_block_reason = "blocked_existing_path"
            n_step_runtime_safety_confidence = "blocked"
            n_step_raise_to_2_candidate = False
            n_step_raise_block_reason = "existing_path_blocked"
            controller_feedback_ready = True
            controller_feedback_kind = "blocked_existing_path"
            controller_feedback_payload = {
                "feedback": "blocked_existing_path",
                "source": "prompt221_bounded_n_step_coordinator",
                "stop_reason": "blocked_existing_path",
                "next_action": "manual_review_required",
            }
            should_prepare_manual_review = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = "blocked_existing_path"
            out_next_action = "manual_review_required"
        elif normalized_selected_step_kind == "manual_stop" or bool(manual_stop_executed):
            status = "bounded_n_step_result_manual_stop"
            result_class = "manual_stop"
            result_block_reason = ""
            n_step_runtime_safety_confidence = "stopped"
            n_step_raise_to_2_candidate = False
            n_step_raise_block_reason = "manual_stop"
            controller_feedback_ready = True
            controller_feedback_kind = "manual_stop"
            controller_feedback_payload = {
                "feedback": "manual_stop",
                "source": "prompt221_bounded_n_step_coordinator",
                "stop_reason": normalized_source_stop_reason or "manual_stop",
                "next_action": "manual_review_required",
            }
            should_prepare_manual_review = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = normalized_source_stop_reason or "manual_stop"
            out_next_action = "manual_review_required"
        elif bool(n_step_coordinator_failed) or source_status_indicates_failed:
            status = "bounded_n_step_result_failed"
            result_class = "failed"
            result_block_reason = "bounded_n_step_failed"
            n_step_runtime_safety_confidence = "failed"
            n_step_raise_to_2_candidate = False
            n_step_raise_block_reason = "bounded_n_step_failed"
            controller_feedback_ready = True
            controller_feedback_kind = "failed"
            controller_feedback_payload = {
                "feedback": "failed",
                "source": "prompt221_bounded_n_step_coordinator",
                "stop_reason": normalized_source_block_reason or "bounded_n_step_failed",
                "next_action": "manual_review_required",
            }
            should_prepare_manual_review = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = normalized_source_block_reason or "bounded_n_step_failed"
            out_next_action = "manual_review_required"
        elif source_status_indicates_blocked or bool(blocked_executed):
            status = "bounded_n_step_result_blocked"
            result_class = "blocked"
            result_block_reason = normalized_source_block_reason or "bounded_n_step_blocked"
            n_step_runtime_safety_confidence = "blocked"
            n_step_raise_to_2_candidate = False
            n_step_raise_block_reason = normalized_source_block_reason or "bounded_n_step_blocked"
            controller_feedback_ready = True
            controller_feedback_kind = "blocked"
            controller_feedback_payload = {
                "feedback": "blocked",
                "source": "prompt221_bounded_n_step_coordinator",
                "stop_reason": normalized_source_block_reason or "bounded_n_step_blocked",
                "next_action": "manual_review_required",
            }
            should_prepare_manual_review = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = normalized_source_block_reason or "bounded_n_step_blocked"
            out_next_action = "manual_review_required"
        else:
            status = "bounded_n_step_result_blocked_insufficient_truth"
            result_class = "insufficient_truth"
            result_block_reason = "blocked_insufficient_bounded_n_step_result_truth"
            n_step_runtime_safety_confidence = "insufficient"
            n_step_raise_to_2_candidate = False
            n_step_raise_block_reason = "insufficient_bounded_n_step_result_truth"
            should_prepare_manual_review = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = "insufficient_bounded_n_step_result_truth"
            out_next_action = "manual_review_required"

    stop_policy_block_reason = _first_true_reason(
        [
            (bool(out_manual_review_required), "blocked_manual_review_required"),
            (bool(out_should_stop), "blocked_should_stop"),
            (bool(out_should_continue_local_loop), "blocked_unexpected_continue_flag"),
            (bool(out_should_start_unbounded_loop), "blocked_unbounded_loop_requested"),
            (bool(out_should_invoke_codex), "blocked_unexpected_codex_invocation_flag"),
            (bool(out_should_execute_rollback), "blocked_unexpected_rollback_flag"),
            (bool(out_should_execute_commit), "blocked_unexpected_commit_flag"),
            (bool(out_should_push), "blocked_unexpected_push_flag"),
            (not one_step_accounting_valid, "blocked_step_accounting_violation"),
            (not non_selected_steps_noop_confirmed, "blocked_non_selected_step_activity"),
        ],
        default="",
    )
    stop_policy_passed = bool(
        not bool(out_manual_review_required)
        and not bool(out_should_stop)
        and not bool(out_should_continue_local_loop)
        and not bool(out_should_start_unbounded_loop)
        and not bool(out_should_invoke_codex)
        and not bool(out_should_execute_rollback)
        and not bool(out_should_execute_commit)
        and not bool(out_should_push)
        and one_step_accounting_valid
        and non_selected_steps_noop_confirmed
    )
    if not stop_policy_passed:
        should_prepare_manual_review = True
        out_manual_review_required = True
        out_should_stop = True
        out_next_action = "manual_review_required"
        if not out_stop_reason:
            out_stop_reason = stop_policy_block_reason or "manual_review_required"
        if status in {
            "bounded_n_step_result_completed_fresh_surface",
            "bounded_n_step_result_completed_existing_truth_guarded",
            "bounded_n_step_result_completed_existing_truth",
        }:
            status = "bounded_n_step_result_blocked_insufficient_truth"
            result_class = "insufficient_truth"
            result_block_reason = (
                stop_policy_block_reason
                or "blocked_insufficient_bounded_n_step_result_truth"
            )
            n_step_runtime_safety_confidence = "insufficient"
            n_step_raise_to_2_candidate = False
            n_step_raise_block_reason = stop_policy_block_reason or "stop_policy_violation"
            should_prepare_raise_to_2_preflight = False
            should_prepare_end_to_end_flow_check = False
            next_bounded_control_target_ready = False
            next_bounded_control_target_kind = "manual_stop"
            next_bounded_control_target_action = "manual_review_required"
            next_bounded_control_target_payload = {}
            controller_feedback_ready = False
            controller_feedback_kind = "none"
            controller_feedback_payload = {}

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if result_class not in allowed_result_classes:
        result_class = "insufficient_truth"
    if out_next_action not in allowed_next_actions:
        out_next_action = "insufficient_truth"
    if status == "insufficient_truth":
        status = "bounded_n_step_result_blocked_insufficient_truth"
        result_selected = False
        result_available = False
        result_class = "insufficient_truth"
        result_block_reason = "blocked_insufficient_bounded_n_step_result_truth"
        one_step_accounting_valid = False
        non_selected_steps_noop_confirmed = False
        completed_fresh_surface_detected = False
        completed_existing_truth_detected = False
        guarded_existing_truth_detected = False
        existing_path_blocked_detected = False
        terminal_result_detected = False
        terminal_result_source = ""
        stop_policy_passed = False
        stop_policy_block_reason = "blocked_insufficient_bounded_n_step_result_truth"
        n_step_runtime_safety_confidence = "insufficient"
        n_step_raise_to_2_candidate = False
        n_step_raise_block_reason = "insufficient_bounded_n_step_result_truth"
        next_bounded_control_target_ready = False
        next_bounded_control_target_kind = "manual_stop"
        next_bounded_control_target_action = "manual_review_required"
        next_bounded_control_target_payload = {}
        controller_feedback_ready = False
        controller_feedback_kind = "none"
        controller_feedback_source = "prompt221_bounded_n_step_coordinator"
        controller_feedback_payload = {}
        should_prepare_raise_to_2_preflight = False
        should_prepare_end_to_end_flow_check = False
        should_prepare_manual_review = True
        out_should_continue_local_loop = False
        out_should_start_unbounded_loop = False
        out_should_invoke_codex = False
        out_should_execute_rollback = False
        out_should_execute_commit = False
        out_should_push = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_bounded_n_step_result_truth"
        out_next_action = "manual_review_required"

    return {
        "project_browser_autonomous_bounded_n_step_result_assimilation_status": status,
        "project_browser_autonomous_bounded_n_step_result_assimilation_result_selected": bool(
            result_selected
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_result_available": bool(
            result_available
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_result_class": (
            result_class
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_result_block_reason": (
            result_block_reason
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_source_selected_step_kind": (
            normalized_selected_step_kind
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_source_selected_step_action": (
            normalized_selected_step_action
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_source_n_step_status": (
            source_n_step_status
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_source_n_step_attempted": bool(
            source_n_step_attempted
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_source_n_step_completed": bool(
            source_n_step_completed
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_source_n_step_failed": bool(
            source_n_step_failed
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_source_actual_steps_allowed": int(
            source_actual_steps_allowed
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_source_actual_steps_attempted": int(
            source_actual_steps_attempted
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_source_actual_steps_completed": int(
            source_actual_steps_completed
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_one_step_accounting_valid": bool(
            one_step_accounting_valid
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_non_selected_steps_noop_confirmed": bool(
            non_selected_steps_noop_confirmed
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_delegated_existing_path_kind": (
            normalized_delegated_kind
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_delegated_existing_status": (
            normalized_delegated_status
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_delegated_existing_next_action": (
            normalized_delegated_next_action
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_delegated_existing_attempted": bool(
            delegated_existing_attempted
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_delegated_existing_completed": bool(
            delegated_existing_completed
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_completed_fresh_surface_detected": bool(
            completed_fresh_surface_detected
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_completed_existing_truth_detected": bool(
            completed_existing_truth_detected
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_guarded_existing_truth_detected": bool(
            guarded_existing_truth_detected
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_existing_path_blocked_detected": bool(
            existing_path_blocked_detected
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_terminal_result_detected": bool(
            terminal_result_detected
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_terminal_result_source": (
            terminal_result_source
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_stop_policy_passed": bool(
            stop_policy_passed
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_stop_policy_block_reason": (
            stop_policy_block_reason
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_n_step_runtime_safety_confidence": (
            n_step_runtime_safety_confidence
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_n_step_raise_to_2_candidate": bool(
            n_step_raise_to_2_candidate
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_n_step_raise_block_reason": (
            n_step_raise_block_reason
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_next_bounded_control_target_ready": bool(
            next_bounded_control_target_ready
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_next_bounded_control_target_kind": (
            next_bounded_control_target_kind
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_next_bounded_control_target_action": (
            next_bounded_control_target_action
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_next_bounded_control_target_payload": (
            next_bounded_control_target_payload
            if isinstance(next_bounded_control_target_payload, Mapping)
            else {}
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_controller_feedback_ready": bool(
            controller_feedback_ready
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_controller_feedback_kind": (
            controller_feedback_kind
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_controller_feedback_source": (
            controller_feedback_source
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_controller_feedback_payload": (
            controller_feedback_payload if isinstance(controller_feedback_payload, Mapping) else {}
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_should_prepare_raise_to_2_preflight": bool(
            should_prepare_raise_to_2_preflight
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_should_prepare_end_to_end_flow_check": bool(
            should_prepare_end_to_end_flow_check
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_should_prepare_manual_review": bool(
            should_prepare_manual_review
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_should_continue_local_loop": bool(
            out_should_continue_local_loop
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_should_start_unbounded_loop": bool(
            out_should_start_unbounded_loop
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_should_invoke_codex": bool(
            out_should_invoke_codex
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_should_execute_rollback": bool(
            out_should_execute_rollback
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_should_execute_commit": bool(
            out_should_execute_commit
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_should_push": bool(
            out_should_push
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_manual_review_required": bool(
            out_manual_review_required
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_should_stop": bool(
            out_should_stop
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_stop_reason": (
            out_stop_reason
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_next_action": (
            out_next_action
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_bounded_n_step_result_assimilation_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_source_status,
                    normalized_source_block_reason,
                    normalized_source,
                    normalized_selected_step_kind,
                    normalized_selected_step_action,
                    normalized_delegated_kind,
                    normalized_delegated_status,
                    normalized_delegated_next_action,
                    normalized_source_result_class,
                    normalized_assimilation_source,
                    normalized_assimilation_next_stage,
                    normalized_source_stop_reason,
                    normalized_source_next_action,
                    normalized_decision_status,
                    normalized_result_assimilation_status,
                    normalized_execution_coordinator_status,
                    normalized_handoff_guard_status,
                    normalized_direct_retrigger_followup_guard_status,
                    normalized_direct_retrigger_result_assimilation_status,
                    normalized_multi_cycle_controller_status,
                    normalized_terminal_lane_decision_status,
                    normalized_lane_contract_guard_status,
                    normalized_guarded_lane_dispatch_status,
                    normalized_next_step_launch_contract_status,
                    normalized_next_step_launch_execution_status,
                    normalized_next_step_launch_result_assimilation_status,
                    normalized_generated_prompt_reentry_readiness_status,
                    normalized_generated_prompt_reentry_routing_status,
                    normalized_codex_reentry_invocation_status,
                    normalized_rollback_execution_status,
                    normalized_rollback_result_assimilation_status,
                    normalized_commit_tag_execution_status,
                    normalized_commit_tag_result_assimilation_status,
                    normalized_fix_prompt_readiness_status,
                    normalized_fix_prompt_generation_status,
                    normalized_next_prompt_readiness_status,
                    normalized_next_prompt_generation_status,
                    "prompt221_not_authoritative_for_prompt222"
                    if not authoritative_selected
                    else "",
                    "prompt221_contract_invalid" if not bool(prompt221_contract_valid) else "",
                    "n_step_coordinator_unavailable"
                    if not bool(n_step_coordinator_available)
                    else "",
                    "n_step_coordinator_not_allowed"
                    if not bool(n_step_coordinator_allowed)
                    else "",
                    "exactly_one_step_target_false"
                    if not bool(exactly_one_step_target)
                    else "",
                    "step_conflict_detected" if bool(step_conflict_detected) else "",
                    "conflicting_step_targets_present" if normalized_conflicts else "",
                    "source_requested_continue_local_loop"
                    if bool(source_should_continue_local_loop)
                    else "",
                    "source_requested_unbounded_loop"
                    if bool(source_should_start_unbounded_loop)
                    else "",
                    "source_requested_codex_invocation"
                    if bool(source_should_invoke_codex)
                    else "",
                    "source_requested_rollback_execution"
                    if bool(source_should_execute_rollback)
                    else "",
                    "source_requested_commit_execution"
                    if bool(source_should_execute_commit)
                    else "",
                    "source_requested_push" if bool(source_should_push) else "",
                    "source_manual_review_required"
                    if bool(source_manual_review_required)
                    else "",
                    "source_should_stop" if bool(source_should_stop) else "",
                ]
            )
        ),
    }

def _build_project_browser_autonomous_bounded_n2_execution_result_assimilation_state(
    *,
    bounded_n2_execution_coordinator_status: str,
    n2_execution_available: bool,
    n2_execution_allowed: bool,
    n2_execution_attempted: bool,
    n2_execution_completed: bool,
    n2_execution_failed: bool,
    n2_execution_block_reason: str,
    n2_execution_source: str,
    prompt225_contract_valid: bool,
    max_continuation_steps: int,
    actual_steps_allowed: int,
    actual_steps_attempted: int,
    actual_steps_completed: int,
    allow_unbounded_loop: bool,
    allow_retry: bool,
    step1_available: bool,
    step1_allowed: bool,
    step1_attempted: bool,
    step1_completed: bool,
    step1_failed: bool,
    step1_block_reason: str,
    step1_result_class: str,
    step1_delegated_existing_path_kind: str,
    step1_delegated_existing_status: str,
    step1_delegated_existing_next_action: str,
    step1_fresh_evidence_detected: bool,
    step1_terminal_result_detected: bool,
    step1_result_assimilation_ready: bool,
    post_step1_stop_policy_passed: bool,
    post_step1_budget_guard_passed: bool,
    post_step1_result_assimilation_ready: bool,
    post_step1_fresh_surface_evidence_confirmed: bool,
    step2_available: bool,
    step2_allowed: bool,
    step2_attempted: bool,
    step2_completed: bool,
    step2_failed: bool,
    step2_block_reason: str,
    step2_result_class: str,
    step2_delegated_existing_path_kind: str,
    step2_delegated_existing_status: str,
    step2_delegated_existing_next_action: str,
    step2_fresh_evidence_detected: bool,
    step2_terminal_result_detected: bool,
    step2_result_assimilation_ready: bool,
    per_step_stop_policy_passed: bool,
    per_step_budget_guard_passed: bool,
    per_step_result_assimilation_ready: bool,
    per_step_fresh_surface_guard_passed: bool,
    non_selected_steps_noop: bool,
    result_class: str,
    prompt226_result_ready_for_assimilation: bool,
    prompt226_result_assimilation_source: str,
    prompt226_result_next_stage: str,
    source_should_continue_local_loop: bool,
    source_should_start_unbounded_loop: bool,
    source_should_invoke_codex: bool,
    source_should_execute_rollback: bool,
    source_should_execute_commit: bool,
    source_should_push: bool,
    source_manual_review_required: bool,
    source_should_stop: bool,
    source_stop_reason: str,
    source_next_action: str,
    bounded_n2_execution_preflight_status: str,
    raise_to_2_preflight_decision_status: str,
    bounded_n_step_result_assimilation_status: str,
    bounded_n_step_coordinator_status: str,
    bounded_continuation_decision_status: str,
    bounded_multistep_execution_result_assimilation_status: str,
    multi_cycle_controller_status: str,
    terminal_lane_decision_status: str,
    lane_contract_guard_status: str,
    guarded_lane_dispatch_status: str,
    next_step_launch_contract_status: str,
    next_step_launch_execution_status: str,
    next_step_launch_result_assimilation_status: str,
    generated_prompt_reentry_readiness_status: str,
    generated_prompt_reentry_routing_status: str,
    codex_reentry_invocation_status: str,
    rollback_execution_status: str,
    rollback_result_assimilation_status: str,
    commit_tag_execution_status: str,
    commit_tag_result_assimilation_status: str,
    fix_prompt_readiness_status: str,
    fix_prompt_generation_status: str,
    next_prompt_readiness_status: str,
    next_prompt_generation_status: str,
) -> dict[str, Any]:
    allowed_statuses = {
        "bounded_n2_result_completed_two_fresh_runtime_steps",
        "bounded_n2_result_completed_one_fresh_runtime_step",
        "bounded_n2_result_completed_existing_truth_only",
        "bounded_n2_result_blocked_step1",
        "bounded_n2_result_blocked_step2",
        "bounded_n2_result_blocked_step_accounting_violation",
        "bounded_n2_result_blocked_non_selected_step_activity",
        "bounded_n2_result_manual_stop",
        "bounded_n2_result_failed",
        "bounded_n2_result_blocked",
        "bounded_n2_result_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_result_classes = {
        "completed_two_fresh_runtime_steps",
        "completed_one_fresh_runtime_step",
        "completed_existing_truth_only",
        "blocked_step1",
        "blocked_step2",
        "blocked_step_accounting_violation",
        "blocked_non_selected_step_activity",
        "manual_stop",
        "failed",
        "blocked",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "prepare_end_to_end_flow_check",
        "manual_review_required",
        "insufficient_truth",
    }
    runtime_posture = [
        "prompt226_bounded_n2_execution_result_assimilation",
        "metadata_only",
        "no_execution",
        "no_retry",
        "no_loop_start",
        "no_push",
        "no_github",
    ]

    normalized_source_status = _normalize_text(
        bounded_n2_execution_coordinator_status,
        default="insufficient_truth",
    )
    normalized_source_result_class = _normalize_text(result_class, default="insufficient_truth")
    normalized_source_block_reason = _normalize_text(n2_execution_block_reason, default="")
    normalized_source = _normalize_text(
        n2_execution_source,
        default="prompt224_bounded_n2_execution_preflight",
    )
    normalized_assimilation_source = _normalize_text(
        prompt226_result_assimilation_source,
        default="",
    )
    normalized_assimilation_next_stage = _normalize_text(
        prompt226_result_next_stage,
        default="",
    )
    normalized_source_stop_reason = _normalize_text(source_stop_reason, default="")
    normalized_source_next_action = _normalize_text(source_next_action, default="")

    normalized_step1_result_class = _normalize_text(step1_result_class, default="blocked")
    normalized_step1_block_reason = _normalize_text(step1_block_reason, default="")
    normalized_step1_delegated_kind = _normalize_text(
        step1_delegated_existing_path_kind,
        default="none",
    )
    normalized_step1_delegated_status = _normalize_text(
        step1_delegated_existing_status,
        default="",
    )
    normalized_step1_delegated_next_action = _normalize_text(
        step1_delegated_existing_next_action,
        default="",
    )
    normalized_step2_result_class = _normalize_text(step2_result_class, default="blocked")
    normalized_step2_block_reason = _normalize_text(step2_block_reason, default="")
    normalized_step2_delegated_kind = _normalize_text(
        step2_delegated_existing_path_kind,
        default="none",
    )
    normalized_step2_delegated_status = _normalize_text(
        step2_delegated_existing_status,
        default="",
    )
    normalized_step2_delegated_next_action = _normalize_text(
        step2_delegated_existing_next_action,
        default="",
    )

    normalized_n2_preflight_status = _normalize_text(
        bounded_n2_execution_preflight_status,
        default="insufficient_truth",
    )
    normalized_raise_to_2_status = _normalize_text(
        raise_to_2_preflight_decision_status,
        default="insufficient_truth",
    )
    normalized_n_step_result_assimilation_status = _normalize_text(
        bounded_n_step_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_n_step_coordinator_status = _normalize_text(
        bounded_n_step_coordinator_status,
        default="insufficient_truth",
    )
    normalized_continuation_decision_status = _normalize_text(
        bounded_continuation_decision_status,
        default="insufficient_truth",
    )
    normalized_multistep_result_assimilation_status = _normalize_text(
        bounded_multistep_execution_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_multi_cycle_controller_status = _normalize_text(
        multi_cycle_controller_status,
        default="insufficient_truth",
    )
    normalized_terminal_lane_decision_status = _normalize_text(
        terminal_lane_decision_status,
        default="insufficient_truth",
    )
    normalized_lane_contract_guard_status = _normalize_text(
        lane_contract_guard_status,
        default="insufficient_truth",
    )
    normalized_guarded_lane_dispatch_status = _normalize_text(
        guarded_lane_dispatch_status,
        default="insufficient_truth",
    )
    normalized_next_step_launch_contract_status = _normalize_text(
        next_step_launch_contract_status,
        default="insufficient_truth",
    )
    normalized_next_step_launch_execution_status = _normalize_text(
        next_step_launch_execution_status,
        default="insufficient_truth",
    )
    normalized_next_step_launch_result_assimilation_status = _normalize_text(
        next_step_launch_result_assimilation_status,
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
    normalized_rollback_execution_status = _normalize_text(
        rollback_execution_status,
        default="insufficient_truth",
    )
    normalized_rollback_result_assimilation_status = _normalize_text(
        rollback_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_commit_tag_execution_status = _normalize_text(
        commit_tag_execution_status,
        default="insufficient_truth",
    )
    normalized_commit_tag_result_assimilation_status = _normalize_text(
        commit_tag_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_fix_prompt_readiness_status = _normalize_text(
        fix_prompt_readiness_status,
        default="insufficient_truth",
    )
    normalized_fix_prompt_generation_status = _normalize_text(
        fix_prompt_generation_status,
        default="insufficient_truth",
    )
    normalized_next_prompt_readiness_status = _normalize_text(
        next_prompt_readiness_status,
        default="insufficient_truth",
    )
    normalized_next_prompt_generation_status = _normalize_text(
        next_prompt_generation_status,
        default="insufficient_truth",
    )

    source_status_indicates_manual_stop = (
        normalized_source_status == "bounded_n2_execution_manual_stop"
    ) or (normalized_source_result_class == "manual_stop")
    source_status_indicates_blocked = (
        "blocked" in normalized_source_status
        or normalized_source_result_class in {"blocked", "blocked_step1", "blocked_step2"}
    )
    source_status_indicates_failed = (
        "failed" in normalized_source_status or normalized_source_result_class == "failed"
    )
    source_status_indicates_insufficient = normalized_source_status in {
        "bounded_n2_execution_blocked_insufficient_truth",
        "insufficient_truth",
    } or normalized_source_result_class == "insufficient_truth"

    authoritative_selected = bool(
        bool(prompt226_result_ready_for_assimilation)
        and normalized_assimilation_source == "prompt225_bounded_n2_execution_coordinator"
        and normalized_assimilation_next_stage
        == "bounded_n2_execution_result_assimilation"
        and bool(normalized_source_status)
        and (
            bool(normalized_source_result_class)
            or source_status_indicates_manual_stop
            or source_status_indicates_blocked
            or source_status_indicates_failed
            or source_status_indicates_insufficient
        )
    )

    source_actual_steps_allowed = _as_non_negative_int(actual_steps_allowed, default=0)
    source_actual_steps_attempted = _as_non_negative_int(actual_steps_attempted, default=0)
    source_actual_steps_completed = _as_non_negative_int(actual_steps_completed, default=0)
    out_max_continuation_steps = _as_non_negative_int(max_continuation_steps, default=0)

    out_step1_attempted = bool(step1_attempted)
    out_step1_completed = bool(step1_completed)
    out_step1_failed = bool(step1_failed)
    out_step1_fresh_evidence_detected = bool(step1_fresh_evidence_detected)
    out_step1_terminal_result_detected = bool(step1_terminal_result_detected)
    out_step1_result_assimilation_ready = bool(step1_result_assimilation_ready)
    out_step2_attempted = bool(step2_attempted)
    out_step2_completed = bool(step2_completed)
    out_step2_failed = bool(step2_failed)
    out_step2_fresh_evidence_detected = bool(step2_fresh_evidence_detected)
    out_step2_terminal_result_detected = bool(step2_terminal_result_detected)
    out_step2_result_assimilation_ready = bool(step2_result_assimilation_ready)

    no_attempt_upstream_blocked = bool(
        not bool(n2_execution_attempted)
        and source_actual_steps_allowed == 0
        and source_actual_steps_attempted == 0
        and source_actual_steps_completed == 0
        and out_max_continuation_steps == 0
        and (source_status_indicates_manual_stop or source_status_indicates_blocked)
        and bool(normalized_source_block_reason or normalized_source_stop_reason)
    )
    n2_step_accounting_valid = bool(
        (out_max_continuation_steps == 2 or no_attempt_upstream_blocked)
        and source_actual_steps_allowed in {0, 1, 2}
        and source_actual_steps_attempted <= 2
        and source_actual_steps_completed <= source_actual_steps_attempted
        and (not out_step2_attempted or out_step1_completed)
        and not bool(allow_unbounded_loop)
        and not bool(allow_retry)
        and not bool(source_should_continue_local_loop)
        and not bool(source_should_start_unbounded_loop)
    )
    non_selected_steps_noop_confirmed = bool(non_selected_steps_noop)

    two_step_success_detected = bool(
        out_step1_completed and out_step2_completed and n2_step_accounting_valid
    )
    one_step_success_detected = bool(
        out_step1_completed and not out_step2_completed and n2_step_accounting_valid
    )
    two_fresh_runtime_steps_detected = bool(
        out_step1_completed
        and out_step2_completed
        and out_step1_fresh_evidence_detected
        and out_step2_fresh_evidence_detected
        and out_step1_terminal_result_detected
        and out_step2_terminal_result_detected
        and out_step1_result_assimilation_ready
        and out_step2_result_assimilation_ready
        and n2_step_accounting_valid
    )
    one_fresh_runtime_step_detected = bool(
        out_step1_completed
        and out_step1_fresh_evidence_detected
        and out_step1_terminal_result_detected
        and out_step1_result_assimilation_ready
        and not out_step2_completed
        and n2_step_accounting_valid
    )
    fresh_runtime_execution_confirmed = bool(two_fresh_runtime_steps_detected)

    step1_blocked_detected = bool(
        normalized_source_status == "bounded_n2_execution_blocked_step1"
        or out_step1_failed
        or (out_step2_attempted and not out_step1_completed)
        or (
            out_step1_attempted
            and not out_step1_completed
            and (
                "blocked" in normalized_step1_result_class
                or bool(normalized_step1_block_reason)
            )
        )
    )
    step2_blocked_detected = bool(
        normalized_source_status == "bounded_n2_execution_blocked_step2"
        or out_step2_failed
        or (out_step2_attempted and not out_step2_completed)
    )
    manual_stop_detected = bool(source_status_indicates_manual_stop)
    failed_detected = bool(
        bool(n2_execution_failed) or source_status_indicates_failed
    )

    hard_stop_or_failure_detected = bool(
        step1_blocked_detected
        or step2_blocked_detected
        or manual_stop_detected
        or failed_detected
        or source_status_indicates_blocked
    )
    required_fresh_evidence_missing = bool(
        (out_step1_completed and not one_fresh_runtime_step_detected and not two_fresh_runtime_steps_detected)
        or (
            out_step2_completed
            and not two_fresh_runtime_steps_detected
        )
    )
    existing_truth_only_detected = bool(
        (out_step1_completed or out_step2_completed)
        and required_fresh_evidence_missing
        and not hard_stop_or_failure_detected
        and n2_step_accounting_valid
    )

    insufficient_truth_detected = False
    result_block_reason = ""
    n2_runtime_safety_confidence = "insufficient"
    e2e_flow_check_candidate = False
    further_raise_candidate = False
    further_raise_block_reason = ""
    controller_feedback_ready = False
    controller_feedback_kind = "none"
    controller_feedback_source = "prompt225_bounded_n2_execution_coordinator"
    controller_feedback_payload: dict[str, Any] = {}
    next_bounded_control_target_ready = False
    next_bounded_control_target_kind = "manual_stop"
    next_bounded_control_target_action = "manual_review_required"
    next_bounded_control_target_payload: dict[str, Any] = {}
    should_prepare_e2e_flow_check = False
    should_prepare_fresh_runtime_evidence_gate = False
    should_prepare_operational_hardening = False
    should_prepare_manual_review = False

    out_should_continue_local_loop = False
    out_should_start_unbounded_loop = False
    out_should_invoke_codex = False
    out_should_execute_rollback = False
    out_should_execute_commit = False
    out_should_push = False
    out_manual_review_required = True
    out_should_stop = True
    out_stop_reason = normalized_source_stop_reason or "insufficient_bounded_n2_result_truth"
    out_next_action = "manual_review_required"

    status = "bounded_n2_result_blocked_insufficient_truth"
    out_result_class = "insufficient_truth"
    result_selected = bool(authoritative_selected)
    result_available = bool(authoritative_selected and normalized_source_status)

    if not authoritative_selected:
        insufficient_truth_detected = True
        out_stop_reason = "insufficient_bounded_n2_result_truth"
    elif not n2_step_accounting_valid:
        status = "bounded_n2_result_blocked_step_accounting_violation"
        out_result_class = "blocked_step_accounting_violation"
        result_block_reason = "blocked_step_accounting_violation"
        should_prepare_manual_review = True
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "blocked_step_accounting_violation"
        out_next_action = "manual_review_required"
    else:
        successful_non_stop_candidate = bool(
            normalized_source_status
            in {
                "bounded_n2_execution_completed_two_steps",
                "bounded_n2_execution_completed_one_step",
            }
            or two_step_success_detected
            or one_step_success_detected
            or existing_truth_only_detected
        )
        if successful_non_stop_candidate and not non_selected_steps_noop_confirmed:
            status = "bounded_n2_result_blocked_non_selected_step_activity"
            out_result_class = "blocked_non_selected_step_activity"
            result_block_reason = "blocked_non_selected_step_activity"
            should_prepare_manual_review = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = "blocked_non_selected_step_activity"
            out_next_action = "manual_review_required"
        elif two_fresh_runtime_steps_detected:
            status = "bounded_n2_result_completed_two_fresh_runtime_steps"
            out_result_class = "completed_two_fresh_runtime_steps"
            fresh_runtime_execution_confirmed = True
            n2_runtime_safety_confidence = "high"
            e2e_flow_check_candidate = True
            further_raise_candidate = False
            further_raise_block_reason = "complete_e2e_flow_check_before_further_raise"
            next_bounded_control_target_ready = True
            next_bounded_control_target_kind = "end_to_end_flow_check"
            next_bounded_control_target_action = "prepare_end_to_end_flow_check"
            next_bounded_control_target_payload = {
                "target": "end_to_end_flow_check",
                "source": "prompt226_bounded_n2_execution_result_assimilation",
                "result_class": out_result_class,
                "next_action": "prepare_end_to_end_flow_check",
            }
            controller_feedback_ready = True
            controller_feedback_kind = "bounded_n2_completed_two_fresh_runtime_steps"
            controller_feedback_payload = {
                "feedback": "bounded_n2_completed_two_fresh_runtime_steps",
                "source": "prompt225_bounded_n2_execution_coordinator",
                "fresh_runtime_execution_confirmed": True,
                "next_action": "prepare_end_to_end_flow_check",
            }
            should_prepare_e2e_flow_check = True
            should_prepare_fresh_runtime_evidence_gate = True
            should_prepare_operational_hardening = True
            out_manual_review_required = False
            out_should_stop = False
            out_stop_reason = ""
            out_next_action = "prepare_end_to_end_flow_check"
        elif one_fresh_runtime_step_detected:
            status = "bounded_n2_result_completed_one_fresh_runtime_step"
            out_result_class = "completed_one_fresh_runtime_step"
            fresh_runtime_execution_confirmed = False
            n2_runtime_safety_confidence = "medium"
            e2e_flow_check_candidate = True
            further_raise_candidate = False
            further_raise_block_reason = "only_one_fresh_runtime_step_completed"
            next_bounded_control_target_ready = True
            next_bounded_control_target_kind = "end_to_end_flow_check"
            next_bounded_control_target_action = "prepare_end_to_end_flow_check"
            next_bounded_control_target_payload = {
                "target": "end_to_end_flow_check",
                "source": "prompt226_bounded_n2_execution_result_assimilation",
                "result_class": out_result_class,
                "next_action": "prepare_end_to_end_flow_check",
            }
            controller_feedback_ready = True
            controller_feedback_kind = "bounded_n2_completed_one_fresh_runtime_step"
            controller_feedback_payload = {
                "feedback": "bounded_n2_completed_one_fresh_runtime_step",
                "source": "prompt225_bounded_n2_execution_coordinator",
                "fresh_runtime_execution_confirmed": False,
                "next_action": "prepare_end_to_end_flow_check",
            }
            should_prepare_e2e_flow_check = True
            should_prepare_fresh_runtime_evidence_gate = True
            out_manual_review_required = False
            out_should_stop = False
            out_stop_reason = ""
            out_next_action = "prepare_end_to_end_flow_check"
        elif existing_truth_only_detected:
            status = "bounded_n2_result_completed_existing_truth_only"
            out_result_class = "completed_existing_truth_only"
            fresh_runtime_execution_confirmed = False
            n2_runtime_safety_confidence = "guarded"
            e2e_flow_check_candidate = True
            further_raise_candidate = False
            further_raise_block_reason = "fresh_runtime_execution_not_confirmed"
            next_bounded_control_target_ready = True
            next_bounded_control_target_kind = "end_to_end_flow_check"
            next_bounded_control_target_action = "prepare_end_to_end_flow_check"
            next_bounded_control_target_payload = {
                "target": "end_to_end_flow_check",
                "source": "prompt226_bounded_n2_execution_result_assimilation",
                "result_class": out_result_class,
                "next_action": "prepare_end_to_end_flow_check",
            }
            controller_feedback_ready = True
            controller_feedback_kind = "bounded_n2_completed_existing_truth_only"
            controller_feedback_payload = {
                "feedback": "bounded_n2_completed_existing_truth_only",
                "source": "prompt225_bounded_n2_execution_coordinator",
                "fresh_runtime_execution_confirmed": False,
                "next_action": "prepare_end_to_end_flow_check",
            }
            should_prepare_e2e_flow_check = True
            should_prepare_fresh_runtime_evidence_gate = True
            out_manual_review_required = False
            out_should_stop = False
            out_stop_reason = ""
            out_next_action = "prepare_end_to_end_flow_check"
        elif step1_blocked_detected:
            status = "bounded_n2_result_blocked_step1"
            out_result_class = "blocked_step1"
            result_block_reason = normalized_step1_block_reason or "bounded_n2_step1_blocked"
            n2_runtime_safety_confidence = "blocked"
            e2e_flow_check_candidate = False
            further_raise_candidate = False
            further_raise_block_reason = "step1_blocked"
            controller_feedback_ready = True
            controller_feedback_kind = "blocked_step1"
            controller_feedback_payload = {
                "feedback": "blocked_step1",
                "source": "prompt225_bounded_n2_execution_coordinator",
                "stop_reason": result_block_reason,
                "next_action": "manual_review_required",
            }
            should_prepare_manual_review = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = normalized_step1_block_reason or "bounded_n2_step1_blocked"
            out_next_action = "manual_review_required"
        elif step2_blocked_detected:
            status = "bounded_n2_result_blocked_step2"
            out_result_class = "blocked_step2"
            result_block_reason = normalized_step2_block_reason or "bounded_n2_step2_blocked"
            n2_runtime_safety_confidence = "partial"
            e2e_flow_check_candidate = True
            further_raise_candidate = False
            further_raise_block_reason = "step2_blocked"
            next_bounded_control_target_ready = True
            next_bounded_control_target_kind = "end_to_end_flow_check"
            next_bounded_control_target_action = "prepare_end_to_end_flow_check"
            next_bounded_control_target_payload = {
                "target": "end_to_end_flow_check",
                "source": "prompt226_bounded_n2_execution_result_assimilation",
                "result_class": out_result_class,
                "next_action": "prepare_end_to_end_flow_check",
            }
            controller_feedback_ready = True
            controller_feedback_kind = "blocked_step2"
            controller_feedback_payload = {
                "feedback": "blocked_step2",
                "source": "prompt225_bounded_n2_execution_coordinator",
                "next_action": "prepare_end_to_end_flow_check",
            }
            should_prepare_e2e_flow_check = True
            out_manual_review_required = False
            out_should_stop = False
            out_stop_reason = ""
            out_next_action = "prepare_end_to_end_flow_check"
        elif manual_stop_detected:
            status = "bounded_n2_result_manual_stop"
            out_result_class = "manual_stop"
            result_block_reason = (
                normalized_source_block_reason
                or normalized_source_stop_reason
                or "manual_stop"
            )
            n2_runtime_safety_confidence = "stopped"
            further_raise_candidate = False
            further_raise_block_reason = "manual_stop"
            controller_feedback_ready = True
            controller_feedback_kind = "manual_stop"
            controller_feedback_payload = {
                "feedback": "manual_stop",
                "source": "prompt225_bounded_n2_execution_coordinator",
                "stop_reason": result_block_reason,
                "next_action": "manual_review_required",
            }
            should_prepare_manual_review = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = result_block_reason
            out_next_action = "manual_review_required"
        elif failed_detected:
            status = "bounded_n2_result_failed"
            out_result_class = "failed"
            result_block_reason = normalized_source_block_reason or "bounded_n2_failed"
            n2_runtime_safety_confidence = "failed"
            further_raise_candidate = False
            further_raise_block_reason = "bounded_n2_failed"
            controller_feedback_ready = True
            controller_feedback_kind = "failed"
            controller_feedback_payload = {
                "feedback": "failed",
                "source": "prompt225_bounded_n2_execution_coordinator",
                "stop_reason": result_block_reason,
                "next_action": "manual_review_required",
            }
            should_prepare_manual_review = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = result_block_reason
            out_next_action = "manual_review_required"
        elif source_status_indicates_blocked:
            status = "bounded_n2_result_blocked"
            out_result_class = "blocked"
            result_block_reason = normalized_source_block_reason or "bounded_n2_blocked"
            n2_runtime_safety_confidence = "blocked"
            further_raise_candidate = False
            further_raise_block_reason = normalized_source_block_reason or "bounded_n2_blocked"
            controller_feedback_ready = True
            controller_feedback_kind = "blocked"
            controller_feedback_payload = {
                "feedback": "blocked",
                "source": "prompt225_bounded_n2_execution_coordinator",
                "stop_reason": normalized_source_block_reason or "bounded_n2_blocked",
                "next_action": "manual_review_required",
            }
            should_prepare_manual_review = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = normalized_source_block_reason or "bounded_n2_blocked"
            out_next_action = "manual_review_required"
        else:
            status = "bounded_n2_result_blocked_insufficient_truth"
            out_result_class = "insufficient_truth"
            insufficient_truth_detected = True
            result_block_reason = "blocked_insufficient_bounded_n2_result_truth"
            n2_runtime_safety_confidence = "insufficient"
            further_raise_candidate = False
            further_raise_block_reason = "insufficient_bounded_n2_result_truth"
            should_prepare_manual_review = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = "insufficient_bounded_n2_result_truth"
            out_next_action = "manual_review_required"

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if out_result_class not in allowed_result_classes:
        out_result_class = "insufficient_truth"
    if out_next_action not in allowed_next_actions:
        out_next_action = "insufficient_truth"
    if status == "insufficient_truth":
        status = "bounded_n2_result_blocked_insufficient_truth"
        result_selected = False
        result_available = False
        out_result_class = "insufficient_truth"
        result_block_reason = "blocked_insufficient_bounded_n2_result_truth"
        n2_step_accounting_valid = False
        non_selected_steps_noop_confirmed = False
        two_step_success_detected = False
        one_step_success_detected = False
        two_fresh_runtime_steps_detected = False
        one_fresh_runtime_step_detected = False
        fresh_runtime_execution_confirmed = False
        existing_truth_only_detected = False
        step1_blocked_detected = False
        step2_blocked_detected = False
        manual_stop_detected = False
        failed_detected = False
        insufficient_truth_detected = True
        n2_runtime_safety_confidence = "insufficient"
        e2e_flow_check_candidate = False
        further_raise_candidate = False
        further_raise_block_reason = "insufficient_bounded_n2_result_truth"
        controller_feedback_ready = False
        controller_feedback_kind = "none"
        controller_feedback_source = "prompt225_bounded_n2_execution_coordinator"
        controller_feedback_payload = {}
        next_bounded_control_target_ready = False
        next_bounded_control_target_kind = "manual_stop"
        next_bounded_control_target_action = "manual_review_required"
        next_bounded_control_target_payload = {}
        should_prepare_e2e_flow_check = False
        should_prepare_fresh_runtime_evidence_gate = False
        should_prepare_operational_hardening = False
        should_prepare_manual_review = True
        out_should_continue_local_loop = False
        out_should_start_unbounded_loop = False
        out_should_invoke_codex = False
        out_should_execute_rollback = False
        out_should_execute_commit = False
        out_should_push = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_bounded_n2_result_truth"
        out_next_action = "manual_review_required"

    result_primary_reason, result_reason_family, result_upstream_reason_source = (
        _derive_bounded_n2_reason_taxonomy(
            primary_reason=result_block_reason,
            status=status,
            fallback_reason=normalized_source_block_reason or out_stop_reason,
            preferred_upstream_source=normalized_source,
            local_stage="prompt226_bounded_n2_execution_result_assimilation",
        )
    )

    return {
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_status": status,
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_result_selected": bool(
            result_selected
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_result_available": bool(
            result_available
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_result_class": (
            out_result_class
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_result_block_reason": (
            result_block_reason
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_primary_reason": (
            result_primary_reason
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_reason_family": (
            result_reason_family
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_upstream_reason_source": (
            result_upstream_reason_source
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_source_n2_status": (
            normalized_source_status
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_source_n2_result_class": (
            normalized_source_result_class
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_source_n2_attempted": bool(
            n2_execution_attempted
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_source_n2_completed": bool(
            n2_execution_completed
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_source_n2_failed": bool(
            n2_execution_failed
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_source_actual_steps_allowed": int(
            source_actual_steps_allowed
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_source_actual_steps_attempted": int(
            source_actual_steps_attempted
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_source_actual_steps_completed": int(
            source_actual_steps_completed
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_n2_step_accounting_valid": bool(
            n2_step_accounting_valid
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_non_selected_steps_noop_confirmed": bool(
            non_selected_steps_noop_confirmed
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_step1_result_class": (
            normalized_step1_result_class
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_step1_attempted": bool(
            out_step1_attempted
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_step1_completed": bool(
            out_step1_completed
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_step1_failed": bool(
            out_step1_failed
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_step1_fresh_evidence_detected": bool(
            out_step1_fresh_evidence_detected
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_step1_terminal_result_detected": bool(
            out_step1_terminal_result_detected
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_step1_result_assimilation_ready": bool(
            out_step1_result_assimilation_ready
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_step2_result_class": (
            normalized_step2_result_class
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_step2_attempted": bool(
            out_step2_attempted
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_step2_completed": bool(
            out_step2_completed
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_step2_failed": bool(
            out_step2_failed
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_step2_fresh_evidence_detected": bool(
            out_step2_fresh_evidence_detected
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_step2_terminal_result_detected": bool(
            out_step2_terminal_result_detected
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_step2_result_assimilation_ready": bool(
            out_step2_result_assimilation_ready
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_two_step_success_detected": bool(
            two_step_success_detected
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_one_step_success_detected": bool(
            one_step_success_detected
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_two_fresh_runtime_steps_detected": bool(
            two_fresh_runtime_steps_detected
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_one_fresh_runtime_step_detected": bool(
            one_fresh_runtime_step_detected
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_fresh_runtime_execution_confirmed": bool(
            fresh_runtime_execution_confirmed
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_existing_truth_only_detected": bool(
            existing_truth_only_detected
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_step1_blocked_detected": bool(
            step1_blocked_detected
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_step2_blocked_detected": bool(
            step2_blocked_detected
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_manual_stop_detected": bool(
            manual_stop_detected
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_failed_detected": bool(
            failed_detected
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_insufficient_truth_detected": bool(
            insufficient_truth_detected
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_n2_runtime_safety_confidence": (
            n2_runtime_safety_confidence
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_e2e_flow_check_candidate": bool(
            e2e_flow_check_candidate
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_further_raise_candidate": bool(
            further_raise_candidate
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_further_raise_block_reason": (
            further_raise_block_reason
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_controller_feedback_ready": bool(
            controller_feedback_ready
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_controller_feedback_kind": (
            controller_feedback_kind
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_controller_feedback_source": (
            controller_feedback_source
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_controller_feedback_payload": (
            controller_feedback_payload if isinstance(controller_feedback_payload, Mapping) else {}
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_next_bounded_control_target_ready": bool(
            next_bounded_control_target_ready
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_next_bounded_control_target_kind": (
            next_bounded_control_target_kind
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_next_bounded_control_target_action": (
            next_bounded_control_target_action
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_next_bounded_control_target_payload": (
            next_bounded_control_target_payload
            if isinstance(next_bounded_control_target_payload, Mapping)
            else {}
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_should_prepare_e2e_flow_check": bool(
            should_prepare_e2e_flow_check
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_should_prepare_fresh_runtime_evidence_gate": bool(
            should_prepare_fresh_runtime_evidence_gate
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_should_prepare_operational_hardening": bool(
            should_prepare_operational_hardening
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_should_prepare_manual_review": bool(
            should_prepare_manual_review
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_should_continue_local_loop": bool(
            out_should_continue_local_loop
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_should_start_unbounded_loop": bool(
            out_should_start_unbounded_loop
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_should_invoke_codex": bool(
            out_should_invoke_codex
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_should_execute_rollback": bool(
            out_should_execute_rollback
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_should_execute_commit": bool(
            out_should_execute_commit
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_should_push": bool(
            out_should_push
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_manual_review_required": bool(
            out_manual_review_required
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_should_stop": bool(
            out_should_stop
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_stop_reason": (
            out_stop_reason
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_next_action": (
            out_next_action
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_bounded_n2_execution_result_assimilation_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_source_status,
                    normalized_source_result_class,
                    normalized_source_block_reason,
                    normalized_source,
                    normalized_assimilation_source,
                    normalized_assimilation_next_stage,
                    normalized_source_stop_reason,
                    normalized_source_next_action,
                    normalized_step1_result_class,
                    normalized_step1_block_reason,
                    normalized_step1_delegated_kind,
                    normalized_step1_delegated_status,
                    normalized_step1_delegated_next_action,
                    normalized_step2_result_class,
                    normalized_step2_block_reason,
                    normalized_step2_delegated_kind,
                    normalized_step2_delegated_status,
                    normalized_step2_delegated_next_action,
                    normalized_n2_preflight_status,
                    normalized_raise_to_2_status,
                    normalized_n_step_result_assimilation_status,
                    normalized_n_step_coordinator_status,
                    normalized_continuation_decision_status,
                    normalized_multistep_result_assimilation_status,
                    normalized_multi_cycle_controller_status,
                    normalized_terminal_lane_decision_status,
                    normalized_lane_contract_guard_status,
                    normalized_guarded_lane_dispatch_status,
                    normalized_next_step_launch_contract_status,
                    normalized_next_step_launch_execution_status,
                    normalized_next_step_launch_result_assimilation_status,
                    normalized_generated_prompt_reentry_readiness_status,
                    normalized_generated_prompt_reentry_routing_status,
                    normalized_codex_reentry_invocation_status,
                    normalized_rollback_execution_status,
                    normalized_rollback_result_assimilation_status,
                    normalized_commit_tag_execution_status,
                    normalized_commit_tag_result_assimilation_status,
                    normalized_fix_prompt_readiness_status,
                    normalized_fix_prompt_generation_status,
                    normalized_next_prompt_readiness_status,
                    normalized_next_prompt_generation_status,
                    "prompt225_not_authoritative_for_prompt226"
                    if not authoritative_selected
                    else "",
                    "prompt225_contract_invalid" if not bool(prompt225_contract_valid) else "",
                    "n2_execution_unavailable" if not bool(n2_execution_available) else "",
                    "n2_execution_not_allowed" if not bool(n2_execution_allowed) else "",
                    "source_requested_continue_local_loop"
                    if bool(source_should_continue_local_loop)
                    else "",
                    "source_requested_unbounded_loop"
                    if bool(source_should_start_unbounded_loop)
                    else "",
                    "source_requested_codex_invocation"
                    if bool(source_should_invoke_codex)
                    else "",
                    "source_requested_rollback_execution"
                    if bool(source_should_execute_rollback)
                    else "",
                    "source_requested_commit_execution"
                    if bool(source_should_execute_commit)
                    else "",
                    "source_requested_push" if bool(source_should_push) else "",
                    "source_manual_review_required"
                    if bool(source_manual_review_required)
                    else "",
                    "source_should_stop" if bool(source_should_stop) else "",
                    "step1_not_available" if not bool(step1_available) else "",
                    "step1_not_allowed" if not bool(step1_allowed) else "",
                    "step2_not_available" if not bool(step2_available) else "",
                    "step2_not_allowed" if not bool(step2_allowed) else "",
                    "post_step1_stop_policy_failed"
                    if not bool(post_step1_stop_policy_passed)
                    else "",
                    "post_step1_budget_guard_failed"
                    if not bool(post_step1_budget_guard_passed)
                    else "",
                    "post_step1_result_assimilation_missing"
                    if not bool(post_step1_result_assimilation_ready)
                    else "",
                    "post_step1_fresh_evidence_missing"
                    if not bool(post_step1_fresh_surface_evidence_confirmed)
                    else "",
                    "per_step_stop_policy_failed"
                    if not bool(per_step_stop_policy_passed)
                    else "",
                    "per_step_budget_guard_failed"
                    if not bool(per_step_budget_guard_passed)
                    else "",
                    "per_step_result_assimilation_missing"
                    if not bool(per_step_result_assimilation_ready)
                    else "",
                    "per_step_fresh_surface_guard_failed"
                    if not bool(per_step_fresh_surface_guard_passed)
                    else "",
                ]
            )
        ),
    }

def _build_project_browser_autonomous_fresh_runtime_evidence_validity_decision_state(
    *,
    prompt239_status: str,
    prompt239_surface_available: bool,
    prompt239_surface_authoritative: bool,
    selected_check_kind: str,
    prompt240_ready: bool,
    should_prepare_prompt240: bool,
    required_artifacts: Any,
    supplied_artifact_paths: Any,
    missing_supplied_artifact_paths: Any,
    artifact_consistency_status: str,
    consistency_block_reason: str,
    consistency_findings: Any,
    prompt240_preconditions_ready: bool,
    content_review_ready: bool,
    json_review_ready: bool,
    evidence_validation_ready: bool,
) -> dict[str, Any]:
    allowed_statuses = {
        "fresh_runtime_evidence_validity_decision_ready",
        "fresh_runtime_evidence_validity_decision_blocked_artifact_consistency_not_reviewable",
        "fresh_runtime_evidence_validity_decision_blocked_prompt239_not_ready",
        "fresh_runtime_evidence_validity_decision_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "prepare_prompt241_fresh_runtime_evidence_truth_bridge",
        "manual_review_required",
        "insufficient_truth",
    }

    normalized_prompt239_status = _normalize_text(prompt239_status, default="")
    normalized_selected_check_kind = _normalize_text(selected_check_kind, default="")
    normalized_required_artifacts = _normalize_string_list(required_artifacts)
    normalized_supplied_artifact_paths = _normalize_string_list(supplied_artifact_paths)
    normalized_missing_supplied_artifact_paths = _normalize_string_list(
        missing_supplied_artifact_paths
    )
    normalized_artifact_consistency_status = _normalize_text(
        artifact_consistency_status, default=""
    )
    normalized_consistency_block_reason = _normalize_text(
        consistency_block_reason, default=""
    )
    normalized_consistency_findings = _normalize_string_list(consistency_findings)

    required_artifact_set = {
        "approved_restart_execution_contract.json",
        "run_state.json",
        "manifest.json",
    }
    required_artifacts_present = required_artifact_set.issubset(
        set(normalized_required_artifacts)
    )

    prompt241_bridge_preconditions = {
        "prompt239_authoritative_required": bool(
            prompt239_surface_available and prompt239_surface_authoritative
        ),
        "selected_check_kind_fresh_runtime_evidence_check": (
            normalized_selected_check_kind == "fresh_runtime_evidence_check"
        ),
        "required_artifacts_known": bool(required_artifacts_present),
        "prompt240_preconditions_ready": bool(prompt240_preconditions_ready),
        "artifact_consistency_reviewed": bool(normalized_artifact_consistency_status),
    }
    forbidden_actions = [
        "read_files",
        "parse_json",
        "filesystem_scan",
        "validate_file_existence",
        "command_execution",
        "codex_invocation",
        "git_mutation",
        "commit",
        "tag",
        "push",
        "rollback",
        "retry",
        "github_mutation",
        "unbounded_loop",
        "prompt222_update",
        "n2_reevaluation",
    ]

    authoritative_ready = bool(
        prompt239_surface_available
        and prompt239_surface_authoritative
        and prompt240_ready
        and should_prepare_prompt240
        and normalized_selected_check_kind == "fresh_runtime_evidence_check"
        and required_artifacts_present
    )

    status = "fresh_runtime_evidence_validity_decision_blocked_prompt239_not_ready"
    next_action = "manual_review_required"
    validity_decision_ready = False
    validity_status = "blocked_prompt239_not_ready"
    validity_block_reason = "prompt239_not_ready"
    validity_findings: list[str] = ["prompt239_not_ready"]
    prompt241_bridge_ready = False
    should_prepare_prompt241 = False

    if authoritative_ready:
        prompt241_bridge_ready = True
        should_prepare_prompt241 = True
        next_action = "prepare_prompt241_fresh_runtime_evidence_truth_bridge"
        if bool(prompt240_preconditions_ready):
            status = "fresh_runtime_evidence_validity_decision_ready"
            validity_decision_ready = True
            validity_status = "ready_for_validity_evaluation_from_observed_outputs"
            validity_block_reason = ""
            validity_findings = [
                "artifact_consistency_reviewable",
                "supplied_artifact_paths_present",
                "content_review_ready",
                "json_review_ready",
                "evidence_validation_ready",
            ]
        else:
            status = "fresh_runtime_evidence_validity_decision_blocked_artifact_consistency_not_reviewable"
            validity_decision_ready = False
            validity_status = "blocked_artifact_consistency_not_reviewable"
            validity_block_reason = (
                normalized_consistency_block_reason
                or "missing_supplied_artifact_paths"
            )
            validity_findings = [
                "artifact_consistency_not_reviewable",
                "supplied_artifact_paths_missing",
                "content_review_not_ready",
                "json_review_not_ready",
                "evidence_validation_not_ready",
            ]
    elif normalized_prompt239_status:
        status = "fresh_runtime_evidence_validity_decision_blocked_prompt239_not_ready"
        validity_decision_ready = False
        validity_status = "blocked_prompt239_not_ready"
        validity_block_reason = "prompt239_not_ready"
        validity_findings = ["prompt239_not_ready"]
    else:
        status = "fresh_runtime_evidence_validity_decision_blocked_insufficient_truth"
        validity_decision_ready = False
        validity_status = "blocked_insufficient_truth"
        validity_block_reason = "insufficient_truth"
        validity_findings = ["insufficient_truth"]

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"
    if status == "insufficient_truth":
        status = "fresh_runtime_evidence_validity_decision_blocked_insufficient_truth"
        next_action = "manual_review_required"
        validity_decision_ready = False
        validity_status = "blocked_insufficient_truth"
        validity_block_reason = "insufficient_truth"
        validity_findings = ["insufficient_truth"]
        prompt241_bridge_ready = False
        should_prepare_prompt241 = False
        normalized_required_artifacts = []
        normalized_supplied_artifact_paths = []
        normalized_missing_supplied_artifact_paths = []
        normalized_artifact_consistency_status = ""
        normalized_consistency_block_reason = "insufficient_truth"
        normalized_consistency_findings = []
        prompt241_bridge_preconditions = {}
        forbidden_actions = []

    return {
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_status": (
            status
        ),
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_source": (
            "prompt240_fresh_runtime_evidence_validity_decision"
        ),
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_prompt239_surface_available": bool(
            prompt239_surface_available
        ),
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_prompt239_surface_authoritative": bool(
            prompt239_surface_authoritative
        ),
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_selected_check_kind": (
            normalized_selected_check_kind
        ),
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_required_artifacts": (
            normalized_required_artifacts
        ),
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_supplied_artifact_paths": (
            normalized_supplied_artifact_paths
        ),
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_missing_supplied_artifact_paths": (
            normalized_missing_supplied_artifact_paths
        ),
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_artifact_consistency_status": (
            normalized_artifact_consistency_status
        ),
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_consistency_block_reason": (
            normalized_consistency_block_reason
        ),
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_consistency_findings": (
            normalized_consistency_findings
        ),
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_prompt240_preconditions_ready": bool(
            prompt240_preconditions_ready
        ),
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_validity_decision_ready": bool(
            validity_decision_ready
        ),
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_validity_status": (
            _normalize_text(validity_status, default="")
        ),
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_validity_block_reason": (
            _normalize_text(validity_block_reason, default="")
        ),
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_validity_findings": (
            _normalize_string_list(validity_findings)
        ),
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_prompt241_bridge_preconditions": (
            prompt241_bridge_preconditions
        ),
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_prompt241_bridge_ready": bool(
            prompt241_bridge_ready
        ),
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_forbidden_actions": (
            forbidden_actions
        ),
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_observed_outputs_available": False,
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_fresh_runtime_evidence_detected": False,
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_fresh_runtime_evidence_valid": False,
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_completed_fresh_surface_detected": False,
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_one_step_accounting_valid": False,
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_stop_policy_passed": False,
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_should_prepare_prompt241": bool(
            should_prepare_prompt241
        ),
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_should_read_files": False,
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_should_parse_json": False,
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_should_validate_file_existence": False,
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_should_scan_filesystem": False,
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_should_execute_manual_command": False,
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_should_execute_runbook": False,
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_should_execute_check_command": False,
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_should_invoke_codex": False,
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_should_execute_commit": False,
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_should_execute_rollback": False,
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_should_push": False,
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_should_start_unbounded_loop": False,
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_should_stop": True,
        "project_browser_autonomous_fresh_runtime_evidence_validity_decision_next_action": (
            next_action
        ),
    }

def _build_project_browser_autonomous_chatgpt_diff_review_decision_state(
    *,
    chatgpt_diff_review_request_state: Mapping[str, Any] | None,
    codex_capture_gate_state: Mapping[str, Any] | None,
    prior_approved_restart_execution_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    request_state = (
        dict(chatgpt_diff_review_request_state)
        if isinstance(chatgpt_diff_review_request_state, Mapping)
        else {}
    )
    capture_state = dict(codex_capture_gate_state) if isinstance(codex_capture_gate_state, Mapping) else {}
    prior_payload = (
        dict(prior_approved_restart_execution_payload)
        if isinstance(prior_approved_restart_execution_payload, Mapping)
        else {}
    )

    def _clip_preview(text: str, *, max_chars: int = 500) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= max_chars:
            return normalized
        return normalized[:max_chars]

    def _looks_transient(text: str) -> bool:
        normalized = _normalize_text(text, default="")
        if not normalized:
            return True
        lower = normalized.lower()
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
        if lower in exact_transients or normalized in exact_transients:
            return True
        if len(normalized) <= 40:
            tokens = ("thinking", "generating", "思考中", "考え中", "生成しています", "応答を生成")
            if any(token in lower or token in normalized for token in tokens):
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

    def _attempt_json_object_parse(text: str) -> dict[str, Any] | None:
        bounded = _normalize_text(text, default="")
        if not bounded:
            return None
        try:
            parsed = json.loads(bounded)
        except Exception:
            parsed = None
        if isinstance(parsed, Mapping):
            return dict(parsed)
        if "```" in bounded:
            fence_markers = ("```json", "```JSON", "```")
            for marker in fence_markers:
                start = bounded.find(marker)
                if start < 0:
                    continue
                payload_start = bounded.find("\n", start)
                if payload_start < 0:
                    continue
                end = bounded.find("```", payload_start + 1)
                if end < 0:
                    continue
                candidate = bounded[payload_start + 1 : end].strip()
                if not candidate:
                    continue
                try:
                    parsed = json.loads(candidate)
                except Exception:
                    continue
                if isinstance(parsed, Mapping):
                    return dict(parsed)
        first_brace = bounded.find("{")
        if first_brace < 0:
            return None
        max_scan = min(len(bounded), 12000)
        start = first_brace
        while start >= 0 and start < max_scan:
            depth = 0
            in_string = False
            escaped = False
            for index in range(start, max_scan):
                char = bounded[index]
                if in_string:
                    if escaped:
                        escaped = False
                    elif char == "\\":
                        escaped = True
                    elif char == '"':
                        in_string = False
                    continue
                if char == '"':
                    in_string = True
                    continue
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = bounded[start : index + 1]
                        try:
                            parsed = json.loads(candidate)
                        except Exception:
                            break
                        if isinstance(parsed, Mapping):
                            return dict(parsed)
                        break
            start = bounded.find("{", start + 1, max_scan)
        return None

    def _extract_scalar_line_value(response_text: str, key: str) -> str:
        key_patterns = (f'"{key}"', key)
        for raw_line in response_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            lower_line = line.lower()
            if not any(pattern.lower() in lower_line for pattern in key_patterns):
                continue
            if ":" not in line:
                continue
            _, raw_value = line.split(":", 1)
            value = raw_value.strip().rstrip(",")
            if value.startswith('"') and value.endswith('"') and len(value) >= 2:
                return value[1:-1].strip()
            if value.startswith("'") and value.endswith("'") and len(value) >= 2:
                return value[1:-1].strip()
            return value.strip()
        return ""

    def _parse_blocking_issues_fallback(response_text: str) -> list[str]:
        extracted: list[str] = []
        for raw_line in response_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            lower_line = line.lower()
            if "blocking_issues" in lower_line and "[" in line and "]" in line:
                start = line.find("[")
                end = line.rfind("]")
                if start >= 0 and end > start:
                    candidate = line[start : end + 1]
                    try:
                        parsed = json.loads(candidate)
                    except Exception:
                        continue
                    if isinstance(parsed, list):
                        extracted = _normalize_string_list(parsed)
                        break
            if line.startswith("- ") and extracted:
                extracted.append(line[2:].strip())
        return _normalize_string_list(extracted)

    def _parse_review_fields(
        response_text: str,
    ) -> tuple[dict[str, Any], bool, str]:
        bounded = response_text[:12000]
        parsed_json = _attempt_json_object_parse(bounded)
        if parsed_json is not None:
            return (parsed_json, True, "json")

        decision = _normalize_text(_extract_scalar_line_value(bounded, "decision"), default="").lower()
        confidence_raw = _normalize_text(_extract_scalar_line_value(bounded, "confidence"), default="")
        risk = _normalize_text(_extract_scalar_line_value(bounded, "risk"), default="").lower()
        fix_prompt = _normalize_text(_extract_scalar_line_value(bounded, "fix_prompt"), default="")
        revert_reason = _normalize_text(_extract_scalar_line_value(bounded, "revert_reason"), default="")
        commit_recommendation_raw = _normalize_text(
            _extract_scalar_line_value(bounded, "commit_recommendation"),
            default="",
        ).lower()
        summary = _normalize_text(_extract_scalar_line_value(bounded, "summary"), default="")
        blocking_issues = _parse_blocking_issues_fallback(bounded)

        extracted: dict[str, Any] = {}
        if decision:
            extracted["decision"] = decision
        if confidence_raw:
            extracted["confidence"] = confidence_raw
        if risk:
            extracted["risk"] = risk
        if blocking_issues:
            extracted["blocking_issues"] = blocking_issues
        if fix_prompt:
            extracted["fix_prompt"] = fix_prompt
        if revert_reason:
            extracted["revert_reason"] = revert_reason
        if commit_recommendation_raw:
            extracted["commit_recommendation"] = commit_recommendation_raw
        if summary:
            extracted["summary"] = summary

        if not extracted:
            return ({}, False, "parse_failed")
        return (extracted, False, "fallback_extracted")

    def _normalize_decision(value: Any) -> str:
        decision = _normalize_text(value, default="").lower()
        if decision in {"approve", "fix", "revert", "manual_review"}:
            return decision
        return "manual_review"

    def _normalize_confidence(value: Any) -> float:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return max(0.0, min(1.0, float(value)))
        text = _normalize_text(value, default="")
        if not text:
            return 0.0
        try:
            parsed = float(text)
        except ValueError:
            return 0.0
        return max(0.0, min(1.0, parsed))

    def _normalize_risk(value: Any) -> str:
        risk = _normalize_text(value, default="").lower()
        if risk in {"low", "medium", "high"}:
            return risk
        return "high"

    def _normalize_blocking_issues(value: Any) -> list[str]:
        if isinstance(value, list):
            return _normalize_string_list(value)
        text = _normalize_text(value, default="")
        if not text:
            return []
        return [text]

    def _normalize_commit_recommendation(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        text = _normalize_text(value, default="").lower()
        return text in {"1", "true", "yes", "on"}

    request_status = _normalize_text(
        request_state.get("project_browser_autonomous_chatgpt_diff_review_request_status"),
        default="",
    )
    request_applicable = request_status in {
        "chatgpt_diff_review_request_ready",
        "chatgpt_diff_review_request_written",
        "chatgpt_diff_review_request_decision_only",
    }

    changed_files = _normalize_string_list(
        capture_state.get("project_browser_autonomous_codex_capture_gate_changed_files")
    )
    base_dir_path = Path("/tmp/codex-local-runner-chatgpt-bridge")
    response_path = base_dir_path / "response.md"
    status_path = base_dir_path / "status.json"
    routed_fix_prompt_path = Path("/tmp/codex-local-runner-decision/generated_fix_prompt.txt")

    status = "chatgpt_diff_review_decision_not_applicable"
    next_action = "wait_for_chatgpt_diff_review_response"
    decision = "manual_review"
    confidence = 0.0
    risk = "high"
    blocking_issues: list[str] = []
    fix_prompt = ""
    fix_prompt_fingerprint = ""
    revert_reason = ""
    revert_plan = ""
    commit_recommendation = False
    summary = ""
    blocked_reason = "not_applicable"
    routed = False
    response_status = "missing"
    response_size_bytes = 0
    response_preview = ""

    if not request_applicable:
        return {
            "project_browser_autonomous_chatgpt_diff_review_decision_status": status,
            "project_browser_autonomous_chatgpt_diff_review_decision_next_action": next_action,
            "project_browser_autonomous_chatgpt_diff_review_decision": decision,
            "project_browser_autonomous_chatgpt_diff_review_confidence": confidence,
            "project_browser_autonomous_chatgpt_diff_review_risk": risk,
            "project_browser_autonomous_chatgpt_diff_review_blocking_issues": blocking_issues,
            "project_browser_autonomous_chatgpt_diff_review_fix_prompt": fix_prompt,
            "project_browser_autonomous_chatgpt_diff_review_fix_prompt_fingerprint": (
                fix_prompt_fingerprint
            ),
            "project_browser_autonomous_chatgpt_diff_review_revert_reason": revert_reason,
            "project_browser_autonomous_chatgpt_diff_review_revert_plan": revert_plan,
            "project_browser_autonomous_chatgpt_diff_review_commit_recommendation": bool(
                commit_recommendation
            ),
            "project_browser_autonomous_chatgpt_diff_review_summary": summary,
            "project_browser_autonomous_chatgpt_diff_review_blocked_reason": blocked_reason,
            "project_browser_autonomous_chatgpt_diff_review_routed": bool(routed),
            "project_browser_autonomous_chatgpt_diff_review_response_status": response_status,
            "project_browser_autonomous_chatgpt_diff_review_response_size_bytes": (
                _as_non_negative_int(response_size_bytes, default=0)
            ),
            "project_browser_autonomous_chatgpt_diff_review_response_preview": response_preview,
        }

    status = "chatgpt_diff_review_decision_blocked_missing_response"
    next_action = "wait_for_chatgpt_diff_review_response"
    blocked_reason = "status_json_missing"

    if not status_path.exists() or not status_path.is_file():
        return {
            "project_browser_autonomous_chatgpt_diff_review_decision_status": status,
            "project_browser_autonomous_chatgpt_diff_review_decision_next_action": next_action,
            "project_browser_autonomous_chatgpt_diff_review_decision": decision,
            "project_browser_autonomous_chatgpt_diff_review_confidence": confidence,
            "project_browser_autonomous_chatgpt_diff_review_risk": risk,
            "project_browser_autonomous_chatgpt_diff_review_blocking_issues": blocking_issues,
            "project_browser_autonomous_chatgpt_diff_review_fix_prompt": fix_prompt,
            "project_browser_autonomous_chatgpt_diff_review_fix_prompt_fingerprint": (
                fix_prompt_fingerprint
            ),
            "project_browser_autonomous_chatgpt_diff_review_revert_reason": revert_reason,
            "project_browser_autonomous_chatgpt_diff_review_revert_plan": revert_plan,
            "project_browser_autonomous_chatgpt_diff_review_commit_recommendation": bool(
                commit_recommendation
            ),
            "project_browser_autonomous_chatgpt_diff_review_summary": summary,
            "project_browser_autonomous_chatgpt_diff_review_blocked_reason": blocked_reason,
            "project_browser_autonomous_chatgpt_diff_review_routed": bool(routed),
            "project_browser_autonomous_chatgpt_diff_review_response_status": response_status,
            "project_browser_autonomous_chatgpt_diff_review_response_size_bytes": (
                _as_non_negative_int(response_size_bytes, default=0)
            ),
            "project_browser_autonomous_chatgpt_diff_review_response_preview": response_preview,
        }

    try:
        with status_path.open("rb") as file_obj:
            raw_status = file_obj.read(8192)
    except OSError as exc:
        blocked_reason = f"status_json_read_error:{exc.__class__.__name__}"
        return {
            "project_browser_autonomous_chatgpt_diff_review_decision_status": status,
            "project_browser_autonomous_chatgpt_diff_review_decision_next_action": next_action,
            "project_browser_autonomous_chatgpt_diff_review_decision": decision,
            "project_browser_autonomous_chatgpt_diff_review_confidence": confidence,
            "project_browser_autonomous_chatgpt_diff_review_risk": risk,
            "project_browser_autonomous_chatgpt_diff_review_blocking_issues": blocking_issues,
            "project_browser_autonomous_chatgpt_diff_review_fix_prompt": fix_prompt,
            "project_browser_autonomous_chatgpt_diff_review_fix_prompt_fingerprint": (
                fix_prompt_fingerprint
            ),
            "project_browser_autonomous_chatgpt_diff_review_revert_reason": revert_reason,
            "project_browser_autonomous_chatgpt_diff_review_revert_plan": revert_plan,
            "project_browser_autonomous_chatgpt_diff_review_commit_recommendation": bool(
                commit_recommendation
            ),
            "project_browser_autonomous_chatgpt_diff_review_summary": summary,
            "project_browser_autonomous_chatgpt_diff_review_blocked_reason": blocked_reason,
            "project_browser_autonomous_chatgpt_diff_review_routed": bool(routed),
            "project_browser_autonomous_chatgpt_diff_review_response_status": response_status,
            "project_browser_autonomous_chatgpt_diff_review_response_size_bytes": (
                _as_non_negative_int(response_size_bytes, default=0)
            ),
            "project_browser_autonomous_chatgpt_diff_review_response_preview": response_preview,
        }

    try:
        parsed_status = json.loads(raw_status.decode("utf-8", errors="replace"))
    except Exception as exc:  # pragma: no cover - defensive parse boundary
        blocked_reason = f"status_json_parse_error:{exc.__class__.__name__}"
        return {
            "project_browser_autonomous_chatgpt_diff_review_decision_status": status,
            "project_browser_autonomous_chatgpt_diff_review_decision_next_action": next_action,
            "project_browser_autonomous_chatgpt_diff_review_decision": decision,
            "project_browser_autonomous_chatgpt_diff_review_confidence": confidence,
            "project_browser_autonomous_chatgpt_diff_review_risk": risk,
            "project_browser_autonomous_chatgpt_diff_review_blocking_issues": blocking_issues,
            "project_browser_autonomous_chatgpt_diff_review_fix_prompt": fix_prompt,
            "project_browser_autonomous_chatgpt_diff_review_fix_prompt_fingerprint": (
                fix_prompt_fingerprint
            ),
            "project_browser_autonomous_chatgpt_diff_review_revert_reason": revert_reason,
            "project_browser_autonomous_chatgpt_diff_review_revert_plan": revert_plan,
            "project_browser_autonomous_chatgpt_diff_review_commit_recommendation": bool(
                commit_recommendation
            ),
            "project_browser_autonomous_chatgpt_diff_review_summary": summary,
            "project_browser_autonomous_chatgpt_diff_review_blocked_reason": blocked_reason,
            "project_browser_autonomous_chatgpt_diff_review_routed": bool(routed),
            "project_browser_autonomous_chatgpt_diff_review_response_status": response_status,
            "project_browser_autonomous_chatgpt_diff_review_response_size_bytes": (
                _as_non_negative_int(response_size_bytes, default=0)
            ),
            "project_browser_autonomous_chatgpt_diff_review_response_preview": response_preview,
        }
    if not isinstance(parsed_status, Mapping):
        blocked_reason = "status_json_not_mapping"
        return {
            "project_browser_autonomous_chatgpt_diff_review_decision_status": status,
            "project_browser_autonomous_chatgpt_diff_review_decision_next_action": next_action,
            "project_browser_autonomous_chatgpt_diff_review_decision": decision,
            "project_browser_autonomous_chatgpt_diff_review_confidence": confidence,
            "project_browser_autonomous_chatgpt_diff_review_risk": risk,
            "project_browser_autonomous_chatgpt_diff_review_blocking_issues": blocking_issues,
            "project_browser_autonomous_chatgpt_diff_review_fix_prompt": fix_prompt,
            "project_browser_autonomous_chatgpt_diff_review_fix_prompt_fingerprint": (
                fix_prompt_fingerprint
            ),
            "project_browser_autonomous_chatgpt_diff_review_revert_reason": revert_reason,
            "project_browser_autonomous_chatgpt_diff_review_revert_plan": revert_plan,
            "project_browser_autonomous_chatgpt_diff_review_commit_recommendation": bool(
                commit_recommendation
            ),
            "project_browser_autonomous_chatgpt_diff_review_summary": summary,
            "project_browser_autonomous_chatgpt_diff_review_blocked_reason": blocked_reason,
            "project_browser_autonomous_chatgpt_diff_review_routed": bool(routed),
            "project_browser_autonomous_chatgpt_diff_review_response_status": response_status,
            "project_browser_autonomous_chatgpt_diff_review_response_size_bytes": (
                _as_non_negative_int(response_size_bytes, default=0)
            ),
            "project_browser_autonomous_chatgpt_diff_review_response_preview": response_preview,
        }
    status_payload = dict(parsed_status)
    runtime_status = _normalize_text(status_payload.get("status"), default="").lower()
    runtime_reason = _normalize_text(status_payload.get("reason"), default="").lower()
    task_status = _normalize_text(status_payload.get("task_status"), default="").lower()
    if not task_status:
        task_status = _map_runtime_to_task_status(runtime_status, runtime_reason)
    if task_status != "response_saved":
        blocked_reason = (
            "response_not_saved"
            if task_status == "ready"
            else (
                "response_in_progress"
                if task_status == "in_progress"
                else (
                    "response_blocked"
                    if task_status == "blocked"
                    else (
                        "response_already_consumed"
                        if task_status == "consumed"
                        else "response_not_available"
                    )
                )
            )
        )
        return {
            "project_browser_autonomous_chatgpt_diff_review_decision_status": status,
            "project_browser_autonomous_chatgpt_diff_review_decision_next_action": next_action,
            "project_browser_autonomous_chatgpt_diff_review_decision": decision,
            "project_browser_autonomous_chatgpt_diff_review_confidence": confidence,
            "project_browser_autonomous_chatgpt_diff_review_risk": risk,
            "project_browser_autonomous_chatgpt_diff_review_blocking_issues": blocking_issues,
            "project_browser_autonomous_chatgpt_diff_review_fix_prompt": fix_prompt,
            "project_browser_autonomous_chatgpt_diff_review_fix_prompt_fingerprint": (
                fix_prompt_fingerprint
            ),
            "project_browser_autonomous_chatgpt_diff_review_revert_reason": revert_reason,
            "project_browser_autonomous_chatgpt_diff_review_revert_plan": revert_plan,
            "project_browser_autonomous_chatgpt_diff_review_commit_recommendation": bool(
                commit_recommendation
            ),
            "project_browser_autonomous_chatgpt_diff_review_summary": summary,
            "project_browser_autonomous_chatgpt_diff_review_blocked_reason": blocked_reason,
            "project_browser_autonomous_chatgpt_diff_review_routed": bool(routed),
            "project_browser_autonomous_chatgpt_diff_review_response_status": response_status,
            "project_browser_autonomous_chatgpt_diff_review_response_size_bytes": (
                _as_non_negative_int(response_size_bytes, default=0)
            ),
            "project_browser_autonomous_chatgpt_diff_review_response_preview": response_preview,
        }

    if not response_path.exists() or not response_path.is_file():
        blocked_reason = "response_missing"
        return {
            "project_browser_autonomous_chatgpt_diff_review_decision_status": status,
            "project_browser_autonomous_chatgpt_diff_review_decision_next_action": next_action,
            "project_browser_autonomous_chatgpt_diff_review_decision": decision,
            "project_browser_autonomous_chatgpt_diff_review_confidence": confidence,
            "project_browser_autonomous_chatgpt_diff_review_risk": risk,
            "project_browser_autonomous_chatgpt_diff_review_blocking_issues": blocking_issues,
            "project_browser_autonomous_chatgpt_diff_review_fix_prompt": fix_prompt,
            "project_browser_autonomous_chatgpt_diff_review_fix_prompt_fingerprint": (
                fix_prompt_fingerprint
            ),
            "project_browser_autonomous_chatgpt_diff_review_revert_reason": revert_reason,
            "project_browser_autonomous_chatgpt_diff_review_revert_plan": revert_plan,
            "project_browser_autonomous_chatgpt_diff_review_commit_recommendation": bool(
                commit_recommendation
            ),
            "project_browser_autonomous_chatgpt_diff_review_summary": summary,
            "project_browser_autonomous_chatgpt_diff_review_blocked_reason": blocked_reason,
            "project_browser_autonomous_chatgpt_diff_review_routed": bool(routed),
            "project_browser_autonomous_chatgpt_diff_review_response_status": response_status,
            "project_browser_autonomous_chatgpt_diff_review_response_size_bytes": (
                _as_non_negative_int(response_size_bytes, default=0)
            ),
            "project_browser_autonomous_chatgpt_diff_review_response_preview": response_preview,
        }

    response_status = "read_attempted"
    try:
        response_size_bytes = _as_non_negative_int(response_path.stat().st_size, default=0)
        with response_path.open("rb") as file_obj:
            raw_response = file_obj.read(32768)
    except OSError as exc:
        blocked_reason = f"response_read_error:{exc.__class__.__name__}"
        return {
            "project_browser_autonomous_chatgpt_diff_review_decision_status": status,
            "project_browser_autonomous_chatgpt_diff_review_decision_next_action": next_action,
            "project_browser_autonomous_chatgpt_diff_review_decision": decision,
            "project_browser_autonomous_chatgpt_diff_review_confidence": confidence,
            "project_browser_autonomous_chatgpt_diff_review_risk": risk,
            "project_browser_autonomous_chatgpt_diff_review_blocking_issues": blocking_issues,
            "project_browser_autonomous_chatgpt_diff_review_fix_prompt": fix_prompt,
            "project_browser_autonomous_chatgpt_diff_review_fix_prompt_fingerprint": (
                fix_prompt_fingerprint
            ),
            "project_browser_autonomous_chatgpt_diff_review_revert_reason": revert_reason,
            "project_browser_autonomous_chatgpt_diff_review_revert_plan": revert_plan,
            "project_browser_autonomous_chatgpt_diff_review_commit_recommendation": bool(
                commit_recommendation
            ),
            "project_browser_autonomous_chatgpt_diff_review_summary": summary,
            "project_browser_autonomous_chatgpt_diff_review_blocked_reason": blocked_reason,
            "project_browser_autonomous_chatgpt_diff_review_routed": bool(routed),
            "project_browser_autonomous_chatgpt_diff_review_response_status": response_status,
            "project_browser_autonomous_chatgpt_diff_review_response_size_bytes": (
                _as_non_negative_int(response_size_bytes, default=0)
            ),
            "project_browser_autonomous_chatgpt_diff_review_response_preview": response_preview,
        }
    response_text = raw_response.decode("utf-8", errors="replace").strip()
    response_preview = _clip_preview(response_text, max_chars=500)
    if not response_text:
        blocked_reason = "response_empty"
        response_status = "empty"
        return {
            "project_browser_autonomous_chatgpt_diff_review_decision_status": status,
            "project_browser_autonomous_chatgpt_diff_review_decision_next_action": next_action,
            "project_browser_autonomous_chatgpt_diff_review_decision": decision,
            "project_browser_autonomous_chatgpt_diff_review_confidence": confidence,
            "project_browser_autonomous_chatgpt_diff_review_risk": risk,
            "project_browser_autonomous_chatgpt_diff_review_blocking_issues": blocking_issues,
            "project_browser_autonomous_chatgpt_diff_review_fix_prompt": fix_prompt,
            "project_browser_autonomous_chatgpt_diff_review_fix_prompt_fingerprint": (
                fix_prompt_fingerprint
            ),
            "project_browser_autonomous_chatgpt_diff_review_revert_reason": revert_reason,
            "project_browser_autonomous_chatgpt_diff_review_revert_plan": revert_plan,
            "project_browser_autonomous_chatgpt_diff_review_commit_recommendation": bool(
                commit_recommendation
            ),
            "project_browser_autonomous_chatgpt_diff_review_summary": summary,
            "project_browser_autonomous_chatgpt_diff_review_blocked_reason": blocked_reason,
            "project_browser_autonomous_chatgpt_diff_review_routed": bool(routed),
            "project_browser_autonomous_chatgpt_diff_review_response_status": response_status,
            "project_browser_autonomous_chatgpt_diff_review_response_size_bytes": (
                _as_non_negative_int(response_size_bytes, default=0)
            ),
            "project_browser_autonomous_chatgpt_diff_review_response_preview": response_preview,
        }
    if _looks_transient(response_text):
        blocked_reason = "response_transient"
        response_status = "transient"
        return {
            "project_browser_autonomous_chatgpt_diff_review_decision_status": status,
            "project_browser_autonomous_chatgpt_diff_review_decision_next_action": next_action,
            "project_browser_autonomous_chatgpt_diff_review_decision": decision,
            "project_browser_autonomous_chatgpt_diff_review_confidence": confidence,
            "project_browser_autonomous_chatgpt_diff_review_risk": risk,
            "project_browser_autonomous_chatgpt_diff_review_blocking_issues": blocking_issues,
            "project_browser_autonomous_chatgpt_diff_review_fix_prompt": fix_prompt,
            "project_browser_autonomous_chatgpt_diff_review_fix_prompt_fingerprint": (
                fix_prompt_fingerprint
            ),
            "project_browser_autonomous_chatgpt_diff_review_revert_reason": revert_reason,
            "project_browser_autonomous_chatgpt_diff_review_revert_plan": revert_plan,
            "project_browser_autonomous_chatgpt_diff_review_commit_recommendation": bool(
                commit_recommendation
            ),
            "project_browser_autonomous_chatgpt_diff_review_summary": summary,
            "project_browser_autonomous_chatgpt_diff_review_blocked_reason": blocked_reason,
            "project_browser_autonomous_chatgpt_diff_review_routed": bool(routed),
            "project_browser_autonomous_chatgpt_diff_review_response_status": response_status,
            "project_browser_autonomous_chatgpt_diff_review_response_size_bytes": (
                _as_non_negative_int(response_size_bytes, default=0)
            ),
            "project_browser_autonomous_chatgpt_diff_review_response_preview": response_preview,
        }
    response_status = "ready"

    parsed_fields, parsed_as_json, parse_mode = _parse_review_fields(response_text)
    if not parsed_fields:
        status = "chatgpt_diff_review_decision_blocked_parse_failed"
        next_action = "manual_review_required"
        blocked_reason = "review_response_parse_failed"
        return {
            "project_browser_autonomous_chatgpt_diff_review_decision_status": status,
            "project_browser_autonomous_chatgpt_diff_review_decision_next_action": next_action,
            "project_browser_autonomous_chatgpt_diff_review_decision": decision,
            "project_browser_autonomous_chatgpt_diff_review_confidence": confidence,
            "project_browser_autonomous_chatgpt_diff_review_risk": risk,
            "project_browser_autonomous_chatgpt_diff_review_blocking_issues": blocking_issues,
            "project_browser_autonomous_chatgpt_diff_review_fix_prompt": fix_prompt,
            "project_browser_autonomous_chatgpt_diff_review_fix_prompt_fingerprint": (
                fix_prompt_fingerprint
            ),
            "project_browser_autonomous_chatgpt_diff_review_revert_reason": revert_reason,
            "project_browser_autonomous_chatgpt_diff_review_revert_plan": revert_plan,
            "project_browser_autonomous_chatgpt_diff_review_commit_recommendation": bool(
                commit_recommendation
            ),
            "project_browser_autonomous_chatgpt_diff_review_summary": summary,
            "project_browser_autonomous_chatgpt_diff_review_blocked_reason": blocked_reason,
            "project_browser_autonomous_chatgpt_diff_review_routed": bool(routed),
            "project_browser_autonomous_chatgpt_diff_review_response_status": response_status,
            "project_browser_autonomous_chatgpt_diff_review_response_size_bytes": (
                _as_non_negative_int(response_size_bytes, default=0)
            ),
            "project_browser_autonomous_chatgpt_diff_review_response_preview": response_preview,
        }

    decision = _normalize_decision(parsed_fields.get("decision"))
    confidence = _normalize_confidence(parsed_fields.get("confidence"))
    risk = _normalize_risk(parsed_fields.get("risk"))
    blocking_issues = _normalize_blocking_issues(parsed_fields.get("blocking_issues"))
    fix_prompt = _normalize_text(parsed_fields.get("fix_prompt"), default="")
    fix_prompt = fix_prompt[:6000] if fix_prompt else ""
    fix_prompt_fingerprint = (
        hashlib.sha256(fix_prompt.encode("utf-8")).hexdigest() if fix_prompt else ""
    )
    revert_reason = _normalize_text(parsed_fields.get("revert_reason"), default="")
    commit_recommendation = _normalize_commit_recommendation(
        parsed_fields.get("commit_recommendation")
    )
    summary = _normalize_text(parsed_fields.get("summary"), default="")
    if not summary:
        summary = (
            "chatgpt diff review response parsed"
            if parsed_as_json
            else f"chatgpt diff review response parsed via {parse_mode}"
        )
    summary = summary[:600]

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
    unsafe_fix_prompt = bool(
        fix_prompt and any(token in fix_prompt.lower() for token in unsafe_tokens)
    )

    if decision == "approve":
        approve_valid = bool(
            confidence >= 0.80
            and risk in {"low", "medium"}
            and not blocking_issues
            and commit_recommendation
        )
        if approve_valid:
            status = "chatgpt_diff_review_decision_approved_for_commit_gate"
            next_action = "prepare_commit_or_pr_gate"
            blocked_reason = "none"
            routed = True
        else:
            status = "chatgpt_diff_review_decision_manual_review"
            next_action = "manual_review_required"
            blocked_reason = "approve_policy_not_satisfied"
    elif decision == "fix":
        if unsafe_fix_prompt:
            status = "chatgpt_diff_review_decision_blocked_unsafe_fix_prompt"
            next_action = "manual_review_required"
            blocked_reason = "unsafe_fix_prompt"
        elif not fix_prompt:
            status = "chatgpt_diff_review_decision_manual_review"
            next_action = "manual_review_required"
            blocked_reason = "missing_fix_prompt"
        elif risk == "high" or blocking_issues or confidence < 0.80:
            status = "chatgpt_diff_review_decision_manual_review"
            next_action = "manual_review_required"
            blocked_reason = "fix_requires_manual_review"
        else:
            prior_fix_fingerprints = {
                _normalize_text(
                    prior_payload.get("project_browser_autonomous_chatgpt_diff_review_fix_prompt_fingerprint"),
                    default="",
                ),
                _normalize_text(
                    prior_payload.get("project_browser_autonomous_codex_execution_gate_prompt_fingerprint"),
                    default="",
                ),
            }
            prior_fix_fingerprints.discard("")
            existing_fix_fp = ""
            if routed_fix_prompt_path.exists() and routed_fix_prompt_path.is_file():
                try:
                    with routed_fix_prompt_path.open("rb") as file_obj:
                        existing_text = file_obj.read(32768).decode("utf-8", errors="replace").strip()
                except OSError:
                    existing_text = ""
                if existing_text:
                    existing_fix_fp = hashlib.sha256(existing_text.encode("utf-8")).hexdigest()
            duplicate_fix_prompt = bool(
                fix_prompt_fingerprint
                and (
                    fix_prompt_fingerprint in prior_fix_fingerprints
                    or fix_prompt_fingerprint == existing_fix_fp
                )
            )
            if duplicate_fix_prompt:
                status = "chatgpt_diff_review_decision_blocked_duplicate_fix_prompt"
                next_action = "manual_review_required"
                blocked_reason = "duplicate_fix_prompt_fingerprint"
            else:
                try:
                    routed_fix_prompt_path.parent.mkdir(parents=True, exist_ok=True)
                    temp_path = routed_fix_prompt_path.with_name(
                        f"{routed_fix_prompt_path.name}.tmp"
                    )
                    temp_path.write_text(fix_prompt, encoding="utf-8")
                    os.replace(temp_path, routed_fix_prompt_path)
                except OSError as exc:
                    status = "chatgpt_diff_review_decision_manual_review"
                    next_action = "manual_review_required"
                    blocked_reason = f"fix_prompt_write_failed:{exc.__class__.__name__}"
                else:
                    status = "chatgpt_diff_review_decision_fix_routed"
                    next_action = "run_existing_codex_fix_step"
                    blocked_reason = "none"
                    routed = True
    elif decision == "revert":
        if not revert_reason:
            status = "chatgpt_diff_review_decision_manual_review"
            next_action = "manual_review_required"
            blocked_reason = "missing_revert_reason"
        else:
            status = "chatgpt_diff_review_decision_revert_plan_ready"
            next_action = "manual_revert_plan_review"
            blocked_reason = "none"
            routed = True
            changed_files_text = ", ".join(changed_files[:20]) if changed_files else "(none)"
            revert_plan = (
                "Revert plan only (no file mutation): "
                f"{revert_reason}. Review captured changed files [{changed_files_text}], "
                "identify exact hunks to revert, and apply safe/manual bounded rollback in a later step."
            )[:1200]
    else:
        status = "chatgpt_diff_review_decision_manual_review"
        next_action = "manual_review_required"
        blocked_reason = "decision_manual_review_or_unrecognized"

    if blocking_issues and status in {
        "chatgpt_diff_review_decision_approved_for_commit_gate",
        "chatgpt_diff_review_decision_fix_routed",
    }:
        status = "chatgpt_diff_review_decision_manual_review"
        next_action = "manual_review_required"
        blocked_reason = "blocking_issues_present"
        routed = False
    if risk == "high" and status in {
        "chatgpt_diff_review_decision_approved_for_commit_gate",
        "chatgpt_diff_review_decision_fix_routed",
    }:
        status = "chatgpt_diff_review_decision_manual_review"
        next_action = "manual_review_required"
        blocked_reason = "high_risk_requires_manual_review"
        routed = False

    return {
        "project_browser_autonomous_chatgpt_diff_review_decision_status": status,
        "project_browser_autonomous_chatgpt_diff_review_decision_next_action": next_action,
        "project_browser_autonomous_chatgpt_diff_review_decision": decision,
        "project_browser_autonomous_chatgpt_diff_review_confidence": confidence,
        "project_browser_autonomous_chatgpt_diff_review_risk": risk,
        "project_browser_autonomous_chatgpt_diff_review_blocking_issues": (
            _normalize_string_list(blocking_issues)
        ),
        "project_browser_autonomous_chatgpt_diff_review_fix_prompt": fix_prompt,
        "project_browser_autonomous_chatgpt_diff_review_fix_prompt_fingerprint": (
            fix_prompt_fingerprint
        ),
        "project_browser_autonomous_chatgpt_diff_review_revert_reason": revert_reason,
        "project_browser_autonomous_chatgpt_diff_review_revert_plan": revert_plan,
        "project_browser_autonomous_chatgpt_diff_review_commit_recommendation": bool(
            commit_recommendation
        ),
        "project_browser_autonomous_chatgpt_diff_review_summary": summary,
        "project_browser_autonomous_chatgpt_diff_review_blocked_reason": blocked_reason,
        "project_browser_autonomous_chatgpt_diff_review_routed": bool(routed),
        "project_browser_autonomous_chatgpt_diff_review_response_status": response_status,
        "project_browser_autonomous_chatgpt_diff_review_response_size_bytes": _as_non_negative_int(
            response_size_bytes,
            default=0,
        ),
        "project_browser_autonomous_chatgpt_diff_review_response_preview": response_preview,
    }

def _build_project_browser_autonomous_chatgpt_diff_review_response_assimilation_state() -> dict[str, Any]:
    response_dir = Path("/tmp/codex-local-runner-decision/chatgpt_diff_review_response")
    expected_response_path = response_dir / "chatgpt_review_response.json"
    decision_path = response_dir / "review_decision.json"
    summary_path = response_dir / "review_decision_summary.md"
    artifact_paths = {
        "expected_response_json": str(expected_response_path),
        "review_decision_json": str(decision_path),
        "review_decision_summary_md": str(summary_path),
    }
    runtime_posture = [
        "metadata_only_response_assimilation",
        "no_codex_invocation",
        "no_git_mutation",
        "no_approve_fix_revert_execution",
    ]

    status = "chatgpt_diff_review_response_assimilation_blocked_missing_response"
    next_action = "wait_for_chatgpt_diff_review_response"
    decision = "manual_review"
    confidence = "low"
    safe_to_commit = False
    requires_fix = False
    requires_revert = False
    summary = ""
    blocking_issues: list[str] = []
    non_blocking_notes: list[str] = []
    recommended_next_action = ""
    blocked_reason = "missing_response_artifact"
    safety_downgrades: list[str] = []

    def _coerce_bool(value: Any, *, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        text = _normalize_text(value, default="").lower()
        if text in {"1", "true", "yes", "on"}:
            return True
        if text in {"0", "false", "no", "off"}:
            return False
        return default

    def _normalize_confidence(value: Any) -> str:
        normalized = _normalize_text(value, default="").lower()
        if normalized in {"high", "medium", "low"}:
            return normalized
        return "low"

    def _normalize_decision(value: Any) -> str:
        normalized = _normalize_text(value, default="").lower()
        if normalized in {"approve", "fix", "revert", "manual_review"}:
            return normalized
        return "manual_review"

    parsed_payload: Mapping[str, Any] | None = None
    raw_response_text = ""
    if expected_response_path.exists():
        try:
            raw_response_text = expected_response_path.read_text(encoding="utf-8")
        except OSError as exc:
            blocked_reason = f"response_read_failed:{exc.__class__.__name__}"
            safety_downgrades.append("response_read_failed_downgraded_to_manual_review")
        else:
            try:
                loaded = json.loads(raw_response_text)
            except json.JSONDecodeError:
                blocked_reason = "invalid_response_json"
                safety_downgrades.append("invalid_response_json_downgraded_to_manual_review")
            else:
                if not isinstance(loaded, Mapping):
                    blocked_reason = "response_not_object"
                    safety_downgrades.append("response_not_object_downgraded_to_manual_review")
                else:
                    parsed_payload = loaded
    else:
        blocked_reason = "missing_response_artifact"

    if isinstance(parsed_payload, Mapping):
        decision = _normalize_decision(parsed_payload.get("decision"))
        confidence = _normalize_confidence(parsed_payload.get("confidence"))
        safe_to_commit = _coerce_bool(parsed_payload.get("safe_to_commit"), default=False)
        requires_fix = _coerce_bool(parsed_payload.get("requires_fix"), default=False)
        requires_revert = _coerce_bool(parsed_payload.get("requires_revert"), default=False)
        summary = _normalize_text(parsed_payload.get("summary"), default="")
        blocking_issues = _normalize_string_list(parsed_payload.get("blocking_issues"))
        non_blocking_notes = _normalize_string_list(parsed_payload.get("non_blocking_notes"))
        recommended_next_action = _normalize_text(
            parsed_payload.get("recommended_next_action"),
            default="",
        )

        contradictory = False
        if requires_fix and requires_revert:
            contradictory = True
            safety_downgrades.append("requires_fix_and_requires_revert_contradiction")
        if decision == "approve" and requires_fix:
            contradictory = True
            safety_downgrades.append("approve_with_requires_fix_contradiction")
        if decision == "approve" and requires_revert:
            contradictory = True
            safety_downgrades.append("approve_with_requires_revert_contradiction")
        if decision == "approve" and not safe_to_commit:
            contradictory = True
            safety_downgrades.append("approve_with_safe_to_commit_false")

        if confidence == "low":
            decision = "manual_review"
            safety_downgrades.append("low_confidence_downgraded_to_manual_review")
        elif contradictory:
            decision = "manual_review"
            safe_to_commit = False
            safety_downgrades.append("contradictory_fields_downgraded_to_manual_review")

        if decision == "approve":
            if (
                not safe_to_commit
                or requires_fix
                or requires_revert
                or confidence not in {"high", "medium"}
            ):
                decision = "manual_review"
                safe_to_commit = False
                safety_downgrades.append("unsafe_approve_downgraded_to_manual_review")

        if decision == "revert" and safe_to_commit:
            safe_to_commit = False
            safety_downgrades.append("revert_forces_safe_to_commit_false")
        if requires_revert:
            safe_to_commit = False

        if requires_revert and decision != "manual_review" and decision != "revert":
            decision = "manual_review"
            safety_downgrades.append("requires_revert_conflict_downgraded_to_manual_review")

        if decision == "approve":
            status = "chatgpt_diff_review_response_assimilation_completed"
            next_action = "prepare_approve_route"
            blocked_reason = "none"
        elif decision == "fix":
            status = "chatgpt_diff_review_response_assimilation_completed"
            next_action = "prepare_fix_route"
            blocked_reason = "none"
        elif decision == "revert" or requires_revert:
            status = "chatgpt_diff_review_response_assimilation_completed"
            next_action = "prepare_revert_route"
            blocked_reason = "none"
        else:
            status = (
                "chatgpt_diff_review_response_assimilation_completed_with_downgrade"
                if safety_downgrades
                else "chatgpt_diff_review_response_assimilation_completed"
            )
            next_action = "manual_review_required"
            blocked_reason = (
                "manual_review_decision_or_safety_downgrade"
                if safety_downgrades
                else "manual_review_decision"
            )

    if not summary:
        summary = _normalize_text(
            recommended_next_action,
            default="ChatGPT review response assimilation completed with safety normalization.",
        )

    decision_payload = {
        "status": status,
        "next_action": next_action,
        "decision": decision,
        "confidence": confidence,
        "safe_to_commit": bool(safe_to_commit),
        "requires_fix": bool(requires_fix),
        "requires_revert": bool(requires_revert),
        "summary": summary,
        "blocking_issues": _normalize_string_list(blocking_issues),
        "non_blocking_notes": _normalize_string_list(non_blocking_notes),
        "recommended_next_action": recommended_next_action,
        "blocked_reason": blocked_reason,
        "safety_downgrades": _normalize_string_list(safety_downgrades),
        "artifact_paths": artifact_paths,
        "runtime_posture": runtime_posture,
    }

    summary_lines = [
        "# ChatGPT Review Response Assimilation",
        "",
        f"- Status: `{status}`",
        f"- Next action: `{next_action}`",
        f"- Decision: `{decision}`",
        f"- Confidence: `{confidence}`",
        f"- Safe to commit: `{str(bool(safe_to_commit)).lower()}`",
        f"- Requires fix: `{str(bool(requires_fix)).lower()}`",
        f"- Requires revert: `{str(bool(requires_revert)).lower()}`",
        f"- Blocked reason: `{blocked_reason}`",
        "",
        "## Safety Downgrades",
    ]
    if safety_downgrades:
        for item in _normalize_string_list(safety_downgrades):
            summary_lines.append(f"- {item}")
    else:
        summary_lines.append("- none")

    try:
        response_dir.mkdir(parents=True, exist_ok=True)
        decision_path.write_text(
            json.dumps(decision_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    except OSError:
        status = "chatgpt_diff_review_response_assimilation_blocked_write_failed"
        next_action = "manual_review_required"
        blocked_reason = "decision_artifact_write_failed"

    return {
        "project_browser_autonomous_chatgpt_diff_review_response_assimilation_status": status,
        "project_browser_autonomous_chatgpt_diff_review_response_assimilation_next_action": next_action,
        "project_browser_autonomous_chatgpt_diff_review_response_assimilation_decision": decision,
        "project_browser_autonomous_chatgpt_diff_review_response_assimilation_confidence": confidence,
        "project_browser_autonomous_chatgpt_diff_review_response_assimilation_safe_to_commit": bool(
            safe_to_commit
        ),
        "project_browser_autonomous_chatgpt_diff_review_response_assimilation_requires_fix": bool(
            requires_fix
        ),
        "project_browser_autonomous_chatgpt_diff_review_response_assimilation_requires_revert": bool(
            requires_revert
        ),
        "project_browser_autonomous_chatgpt_diff_review_response_assimilation_artifact_paths": artifact_paths,
        "project_browser_autonomous_chatgpt_diff_review_response_assimilation_blocked_reason": blocked_reason,
        "project_browser_autonomous_chatgpt_diff_review_response_assimilation_safety_downgrades": (
            _normalize_string_list(safety_downgrades)
        ),
        "project_browser_autonomous_chatgpt_diff_review_response_assimilation_runtime_posture": (
            runtime_posture
        ),
    }

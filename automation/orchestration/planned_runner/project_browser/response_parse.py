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
def _build_project_browser_response_parse_state(
    *,
    browser_command_type: str,
    browser_chatgpt_page_status: str,
    browser_login_interruption_status: str,
    browser_response_wait_status: str,
    browser_response_read_status: str,
    browser_response_text_status: str,
    browser_response_text: str,
    browser_response_text_truncated: bool,
    browser_prompt_schema_required_json_ref: str,
) -> dict[str, Any]:
    command_type = _normalize_text(browser_command_type, default="none")
    page_status = _normalize_text(browser_chatgpt_page_status, default="insufficient_truth")
    login_status = _normalize_text(
        browser_login_interruption_status,
        default="insufficient_truth",
    )
    wait_status = _normalize_text(browser_response_wait_status, default="insufficient_truth")
    read_status = _normalize_text(browser_response_read_status, default="insufficient_truth")
    text_status = _normalize_text(browser_response_text_status, default="insufficient_truth")
    response_text = _normalize_text(browser_response_text, default="")
    schema_ref = _normalize_text(browser_prompt_schema_required_json_ref, default="")

    parse_status = "insufficient_truth"
    schema_status = "insufficient_truth"
    decision_status = "insufficient_truth"
    execution_receipt_status = "insufficient_truth"
    execution_receipt_kind = "none"
    execution_result_status = "insufficient_truth"
    block_reason = "insufficient_truth"
    parse_attempted = False
    parsed_compact: dict[str, Any] = {}

    runtime_tokens = [
        "no_decision_execution",
        "no_queue_mutation",
        "no_retry_execution",
        "no_repair_execution",
        "no_restart_execution",
        "no_reload_execution",
        "no_new_chat_execution",
        "no_login_recovery",
        "no_executor_loop",
    ]

    if wait_status == "inactive" or read_status == "inactive":
        parse_status = "inactive"
        schema_status = "not_checked"
        decision_status = "unavailable"
        execution_receipt_status = "not_created"
        execution_result_status = "not_executed"
        block_reason = "response_not_read"
    elif wait_status == "not_attempted" or read_status == "not_attempted":
        parse_status = "not_attempted"
        schema_status = "not_checked"
        decision_status = "unavailable"
        execution_receipt_status = "not_created"
        execution_result_status = "not_executed"
        block_reason = "response_not_read"
    elif wait_status in {"blocked"} or read_status in {"blocked"}:
        parse_status = "blocked"
        schema_status = "not_checked"
        decision_status = "unavailable"
        execution_receipt_status = "blocked"
        execution_receipt_kind = "blocked_parse_receipt"
        execution_result_status = "blocked"
        block_reason = "response_not_read"
    elif wait_status in {"failed"} or read_status in {"failed"}:
        parse_status = "failed"
        schema_status = "not_checked"
        decision_status = "unavailable"
        execution_receipt_status = "failed"
        execution_receipt_kind = "failed_parse_receipt"
        execution_result_status = "failed"
        block_reason = "response_not_read"
    elif wait_status in {"insufficient_truth"} or read_status in {"insufficient_truth"}:
        parse_status = "insufficient_truth"
        schema_status = "insufficient_truth"
        decision_status = "insufficient_truth"
        execution_receipt_status = "insufficient_truth"
        execution_result_status = "insufficient_truth"
        block_reason = "insufficient_truth"
    elif login_status == "detected" or page_status == "login_interruption":
        parse_status = "blocked"
        schema_status = "not_checked"
        decision_status = "unavailable"
        execution_receipt_status = "blocked"
        execution_receipt_kind = "blocked_parse_receipt"
        execution_result_status = "blocked"
        block_reason = "login_interruption"
    elif command_type not in _PROJECT_BROWSER_COMMAND_TYPES - {"none"}:
        parse_status = "blocked"
        schema_status = "not_checked"
        decision_status = "unavailable"
        execution_receipt_status = "blocked"
        execution_receipt_kind = "blocked_parse_receipt"
        execution_result_status = "blocked"
        block_reason = "unsupported_command_type"
    elif text_status == "unavailable":
        parse_status = "blocked"
        schema_status = "not_checked"
        decision_status = "unavailable"
        execution_receipt_status = "blocked"
        execution_receipt_kind = "blocked_parse_receipt"
        execution_result_status = "blocked"
        block_reason = "response_text_missing"
    elif text_status == "empty":
        parse_status = "blocked"
        schema_status = "not_checked"
        decision_status = "unavailable"
        execution_receipt_status = "blocked"
        execution_receipt_kind = "blocked_parse_receipt"
        execution_result_status = "blocked"
        block_reason = "response_text_empty"
    elif text_status == "too_large" or bool(browser_response_text_truncated):
        parse_status = "blocked"
        schema_status = "not_checked"
        decision_status = "unavailable"
        execution_receipt_status = "blocked"
        execution_receipt_kind = "blocked_parse_receipt"
        execution_result_status = "blocked"
        block_reason = "response_text_too_large"
    elif text_status == "insufficient_truth":
        parse_status = "insufficient_truth"
        schema_status = "insufficient_truth"
        decision_status = "insufficient_truth"
        execution_receipt_status = "insufficient_truth"
        execution_result_status = "insufficient_truth"
        block_reason = "insufficient_truth"
    elif read_status != "read":
        parse_status = "unavailable"
        schema_status = "not_checked"
        decision_status = "unavailable"
        execution_receipt_status = "blocked"
        execution_receipt_kind = "blocked_parse_receipt"
        execution_result_status = "blocked"
        block_reason = "response_not_read"
    elif not response_text:
        parse_status = "blocked"
        schema_status = "not_checked"
        decision_status = "unavailable"
        execution_receipt_status = "blocked"
        execution_receipt_kind = "blocked_parse_receipt"
        execution_result_status = "blocked"
        block_reason = "response_text_empty"
    elif not schema_ref:
        parse_status = "blocked"
        schema_status = "missing"
        decision_status = "unavailable"
        execution_receipt_status = "blocked"
        execution_receipt_kind = "blocked_parse_receipt"
        execution_result_status = "blocked"
        block_reason = "schema_missing"
    else:
        parse_attempted = True
        runtime_tokens.append("json_parse_attempted")
        try:
            parsed_raw = json.loads(response_text)
        except Exception:
            parse_status = "invalid_response"
            schema_status = "not_checked"
            decision_status = "invalid"
            execution_receipt_status = "invalid_response"
            execution_receipt_kind = "invalid_response_receipt"
            execution_result_status = "invalid_response"
            block_reason = "json_parse_failed"
        else:
            if not isinstance(parsed_raw, Mapping):
                parse_status = "invalid_response"
                schema_status = "invalid"
                decision_status = "invalid"
                execution_receipt_status = "invalid_response"
                execution_receipt_kind = "invalid_response_receipt"
                execution_result_status = "invalid_response"
                block_reason = "schema_invalid"
            else:
                parsed = dict(parsed_raw)
                missing_fields = [
                    field
                    for field in _PROJECT_BROWSER_JSON_REQUIRED_FIELDS
                    if field not in parsed
                ]
                if missing_fields:
                    parse_status = "invalid_response"
                    schema_status = "missing"
                    decision_status = (
                        "missing" if "decision" in missing_fields else "invalid"
                    )
                    execution_receipt_status = "invalid_response"
                    execution_receipt_kind = "invalid_response_receipt"
                    execution_result_status = "invalid_response"
                    block_reason = (
                        "decision_missing" if "decision" in missing_fields else "schema_missing"
                    )
                else:
                    task_type = _normalize_text(parsed.get("task_type"), default="none")
                    decision = _normalize_text(parsed.get("decision"), default="")
                    risk_level = _normalize_text(parsed.get("risk_level"), default="")
                    success_score = _as_non_negative_int(parsed.get("success_score"), default=-1)
                    confidence_score = _as_non_negative_int(
                        parsed.get("confidence_score"),
                        default=-1,
                    )
                    schema_invalid = any(
                        (
                            task_type not in _PROJECT_BROWSER_TASK_TYPES
                            or task_type == "none",
                            decision not in _PROJECT_BROWSER_DECISIONS,
                            risk_level not in _PROJECT_BROWSER_RISK_LEVELS,
                            success_score < 0
                            or confidence_score < 0
                            or success_score > 100
                            or confidence_score > 100,
                            not _normalize_text(parsed.get("objective_id"), default=""),
                            not _normalize_text(parsed.get("step_id"), default=""),
                        )
                    )
                    if schema_invalid:
                        parse_status = "invalid_response"
                        schema_status = "invalid"
                        decision_status = (
                            "missing"
                            if not decision
                            else ("invalid" if decision not in _PROJECT_BROWSER_DECISIONS else "invalid")
                        )
                        execution_receipt_status = "invalid_response"
                        execution_receipt_kind = "invalid_response_receipt"
                        execution_result_status = "invalid_response"
                        block_reason = (
                            "decision_missing"
                            if not decision
                            else "schema_invalid"
                        )
                    else:
                        parse_status = "valid"
                        schema_status = "valid"
                        decision_status = "parsed"
                        execution_receipt_status = "parsed"
                        execution_receipt_kind = "browser_response_parse_receipt"
                        execution_result_status = "response_parsed"
                        block_reason = "none"
                        parsed_compact = {
                            "task_type": task_type,
                            "objective_id": _normalize_text(parsed.get("objective_id"), default=""),
                            "step_id": _normalize_text(parsed.get("step_id"), default=""),
                            "decision": decision,
                            "risk_level": risk_level,
                            "success_score": success_score,
                            "confidence_score": confidence_score,
                        }

    if parse_status not in _PROJECT_BROWSER_RESPONSE_JSON_PARSE_STATUSES:
        parse_status = "insufficient_truth"
    if schema_status not in _PROJECT_BROWSER_RESPONSE_JSON_SCHEMA_STATUSES:
        schema_status = "insufficient_truth"
    if decision_status not in _PROJECT_BROWSER_RESPONSE_JSON_DECISION_STATUSES:
        decision_status = "insufficient_truth"
    if execution_receipt_status not in _PROJECT_BROWSER_EXECUTION_RECEIPT_PARSE_STATUSES:
        execution_receipt_status = "insufficient_truth"
    if execution_receipt_kind not in _PROJECT_BROWSER_EXECUTION_RECEIPT_PARSE_KINDS:
        execution_receipt_kind = "none"
    if execution_result_status not in _PROJECT_BROWSER_EXECUTION_RESULT_STATUSES:
        execution_result_status = "insufficient_truth"
    if block_reason not in _PROJECT_BROWSER_RESPONSE_PARSE_BLOCK_REASONS:
        block_reason = "insufficient_truth"

    runtime_posture = [
        token
        for token in runtime_tokens
        if token in _PROJECT_BROWSER_RESPONSE_PARSE_RUNTIME_POSTURES
    ]
    if not parse_attempted and "json_parse_attempted" in runtime_posture:
        runtime_posture = [
            token for token in runtime_posture if token != "json_parse_attempted"
        ]

    return {
        "project_browser_response_json_parse_status": parse_status,
        "project_browser_response_json_schema_status": schema_status,
        "project_browser_response_json_decision_status": decision_status,
        "project_browser_execution_receipt_status": execution_receipt_status,
        "project_browser_execution_receipt_kind": execution_receipt_kind,
        "project_browser_execution_result_status": execution_result_status,
        "project_browser_response_parse_block_reason": block_reason,
        "project_browser_response_parse_runtime_posture": runtime_posture,
        "project_browser_response_json_parse_compact": parsed_compact,
        "project_browser_response_parse_runtime_json_parse_attempted": bool(
            "json_parse_attempted" in runtime_posture
        ),
        "project_browser_response_parse_runtime_no_decision_execution": True,
        "project_browser_response_parse_runtime_no_queue_mutation": True,
        "project_browser_response_parse_runtime_no_retry_execution": True,
        "project_browser_response_parse_runtime_no_repair_execution": True,
        "project_browser_response_parse_runtime_no_restart_execution": True,
        "project_browser_response_parse_runtime_no_reload_execution": True,
        "project_browser_response_parse_runtime_no_new_chat_execution": True,
        "project_browser_response_parse_runtime_no_login_recovery": True,
        "project_browser_response_parse_runtime_no_executor_loop": True,
    }

def _build_project_browser_autonomous_chatgpt_decision_validation_state(
    *,
    decision_json_expected_path: str,
    decision_schema_required_fields: list[str] | None,
    decision_schema_allowed_decisions: list[str] | None,
    actor_separation_required: bool,
    same_actor_requires_human_review: bool,
    final_human_review_required: bool,
) -> dict[str, Any]:
    required_fields = _normalize_string_list(decision_schema_required_fields or [])
    if not required_fields:
        required_fields = [
            "schema_version",
            "decision",
            "confidence",
            "summary",
            "reasons",
            "commit_allowed",
            "rollback_required",
            "human_review_required",
            "next_prompt_required",
            "fix_prompt_required",
            "stop_required",
            "next_action",
            "decision_actor",
            "decision_actor_role",
            "implementation_actor",
            "implementation_actor_role",
            "actor_separation_required",
            "same_actor_requires_human_review",
            "implementation_mode",
            "implementation_output_kind",
            "implementation_allowed",
            "implementation_requires_human_apply",
            "required_checks",
            "changed_files_reviewed",
            "risk_flags",
            "missing_evidence",
            "implementation_constraints",
            "implementation_forbidden_actions",
            "validation_summary",
            "accounting_summary",
            "prompt_summary",
            "safety_summary",
            "actor_summary",
            "implementation_summary",
        ]
    allowed_decisions = _normalize_string_list(decision_schema_allowed_decisions or [])
    if not allowed_decisions:
        allowed_decisions = [
            "proceed",
            "fix_required",
            "stop",
            "human_review_required",
            "rollback_required",
            "commit_allowed",
            "commit_blocked",
            "implementation_required",
            "implementation_blocked",
        ]
    allowed_decision_actors = {
        "chatgpt_5_5_judge",
        "human_operator",
        "local_policy",
        "none",
    }
    allowed_decision_actor_roles = {
        "judge",
        "reviewer",
        "policy_checker",
        "human_supervisor",
        "none",
    }
    allowed_implementation_actors = {
        "codex",
        "chatgpt_5_5_implementer",
        "local_model",
        "human_operator",
        "none",
    }
    allowed_implementation_actor_roles = {
        "implementer",
        "patch_author",
        "codex_executor",
        "human_editor",
        "none",
    }
    allowed_implementation_modes = {
        "codex_live_transport",
        "chatgpt_subscription_ui_manual_patch",
        "chatgpt_subscription_ui_unified_diff",
        "local_model_patch",
        "human_manual_edit",
        "none",
    }
    allowed_implementation_output_kinds = {
        "none",
        "instructions_only",
        "unified_diff",
        "full_file_replacement",
        "patch_plan",
        "manual_steps",
    }
    allowed_confidence_values = {"high", "medium", "low"}

    bool_required_fields = {
        "commit_allowed",
        "rollback_required",
        "human_review_required",
        "next_prompt_required",
        "fix_prompt_required",
        "stop_required",
        "actor_separation_required",
        "same_actor_requires_human_review",
        "implementation_allowed",
        "implementation_requires_human_apply",
    }
    list_required_fields = {
        "reasons",
        "required_checks",
        "changed_files_reviewed",
        "risk_flags",
        "missing_evidence",
        "implementation_constraints",
        "implementation_forbidden_actions",
    }
    object_required_fields = {
        "validation_summary",
        "accounting_summary",
        "prompt_summary",
        "safety_summary",
        "actor_summary",
        "implementation_summary",
    }

    expected_path = _normalize_text(
        decision_json_expected_path,
        default="/tmp/codex-local-runner-decision/chatgpt_decision.json",
    )
    decision_json_path = Path(expected_path)

    decision_json_status = "missing_file"
    validator_status = "waiting_for_manual_file"
    validator_source_status = "valid"
    validator_block_reason = "none"
    validator_next_action = "wait_for_chatgpt_decision_json"
    validator_runtime_posture = [
        "decision_json_intake_local_file_only",
        "validator_metadata_only",
        "no_chatgpt_api_call",
        "no_browser_automation",
    ]
    consumption_status = "waiting_for_manual_chatgpt_json"
    consumption_block_reason = "none"
    consumption_next_action = "wait_for_chatgpt_decision_json"
    consumption_ready = False

    decision_payload: dict[str, Any] | None = None
    decision_schema_version = "none"
    decision_value = "none"
    decision_confidence = "none"
    decision_actor = "none"
    decision_actor_role = "none"
    implementation_actor = "none"
    implementation_actor_role = "none"
    implementation_mode = "none"
    implementation_output_kind = "none"
    decision_commit_allowed = False
    decision_rollback_required = False
    decision_human_review_required = False
    decision_same_actor_requires_human_review = bool(same_actor_requires_human_review)
    decision_actor_separation_required = bool(actor_separation_required)
    required_checks_count = 0
    changed_files_reviewed_count = 0
    risk_flags_count = 0
    missing_evidence_count = 0
    validation_summary_status = "insufficient_truth"
    accounting_summary_status = "insufficient_truth"
    safety_summary_status = "insufficient_truth"
    actor_summary_status = "insufficient_truth"
    implementation_summary_status = "insufficient_truth"
    decision_summary = ""
    implementation_allowed = False
    implementation_requires_human_apply = True
    implementation_constraints: list[str] = []
    implementation_forbidden_actions: list[str] = []
    implementation_allowed_files: list[str] = []
    implementation_forbidden_files: list[str] = []

    missing_required_fields: list[str] = []
    invalid_allowed_value_fields: list[str] = []
    actor_separation_status = "insufficient_truth"
    commit_gate_status = "blocked"
    effective_commit_allowed = False

    if not decision_json_path.exists():
        decision_json_status = "missing_file"
        validator_status = "waiting_for_manual_file"
        validator_source_status = "valid"
        validator_block_reason = "manual_decision_json_missing"
        validator_next_action = "wait_for_chatgpt_decision_json"
        consumption_status = "waiting_for_manual_chatgpt_json"
        consumption_block_reason = "manual_decision_json_missing"
        consumption_next_action = "wait_for_chatgpt_decision_json"
    else:
        raw_text = ""
        try:
            raw_text = decision_json_path.read_text(encoding="utf-8")
        except OSError:
            decision_json_status = "unreadable_file"
            validator_status = "unreadable_file"
            validator_block_reason = "decision_json_unreadable"
            validator_next_action = "fix_decision_json_file_permissions"
            consumption_status = "blocked"
            consumption_block_reason = "decision_json_unreadable"
            consumption_next_action = "manual_fix_required"
        if not validator_status == "unreadable_file":
            try:
                parsed = json.loads(raw_text)
            except json.JSONDecodeError:
                decision_json_status = "invalid_json"
                validator_status = "invalid_json"
                validator_block_reason = "decision_json_parse_failed"
                validator_next_action = "manual_fix_invalid_json"
                consumption_status = "blocked"
                consumption_block_reason = "invalid_json"
                consumption_next_action = "manual_fix_required"
            else:
                if not isinstance(parsed, Mapping):
                    decision_json_status = "invalid_json"
                    validator_status = "invalid_json"
                    validator_block_reason = "decision_json_not_object"
                    validator_next_action = "manual_fix_invalid_json"
                    consumption_status = "blocked"
                    consumption_block_reason = "invalid_json"
                    consumption_next_action = "manual_fix_required"
                else:
                    decision_payload = dict(parsed)
                    decision_json_status = "valid"

    if isinstance(decision_payload, Mapping):
        missing_required_fields = [
            field_name
            for field_name in required_fields
            if field_name not in decision_payload
        ]

        def _is_list_field(name: str) -> bool:
            return isinstance(decision_payload.get(name), list)

        def _is_mapping_field(name: str) -> bool:
            return isinstance(decision_payload.get(name), Mapping)

        if not missing_required_fields:
            if (
                _normalize_text(decision_payload.get("schema_version"), default="none")
                != "chatgpt_runner_decision_v1"
            ):
                invalid_allowed_value_fields.append("schema_version")
            if (
                _normalize_text(decision_payload.get("decision"), default="none")
                not in set(allowed_decisions)
            ):
                invalid_allowed_value_fields.append("decision")
            if (
                _normalize_text(decision_payload.get("confidence"), default="none")
                not in allowed_confidence_values
            ):
                invalid_allowed_value_fields.append("confidence")
            if (
                _normalize_text(decision_payload.get("decision_actor"), default="none")
                not in allowed_decision_actors
            ):
                invalid_allowed_value_fields.append("decision_actor")
            if (
                _normalize_text(decision_payload.get("decision_actor_role"), default="none")
                not in allowed_decision_actor_roles
            ):
                invalid_allowed_value_fields.append("decision_actor_role")
            if (
                _normalize_text(decision_payload.get("implementation_actor"), default="none")
                not in allowed_implementation_actors
            ):
                invalid_allowed_value_fields.append("implementation_actor")
            if (
                _normalize_text(decision_payload.get("implementation_actor_role"), default="none")
                not in allowed_implementation_actor_roles
            ):
                invalid_allowed_value_fields.append("implementation_actor_role")
            if (
                _normalize_text(decision_payload.get("implementation_mode"), default="none")
                not in allowed_implementation_modes
            ):
                invalid_allowed_value_fields.append("implementation_mode")
            if (
                _normalize_text(
                    decision_payload.get("implementation_output_kind"),
                    default="none",
                )
                not in allowed_implementation_output_kinds
            ):
                invalid_allowed_value_fields.append("implementation_output_kind")
            for field_name in bool_required_fields:
                if not isinstance(decision_payload.get(field_name), bool):
                    invalid_allowed_value_fields.append(field_name)
            for field_name in list_required_fields:
                if not _is_list_field(field_name):
                    invalid_allowed_value_fields.append(field_name)
            for field_name in object_required_fields:
                if not _is_mapping_field(field_name):
                    invalid_allowed_value_fields.append(field_name)
            invalid_allowed_value_fields = _serialize_required_signals(
                invalid_allowed_value_fields
            )

        decision_schema_version = _normalize_text(
            decision_payload.get("schema_version"),
            default="none",
        )
        decision_value = _normalize_text(decision_payload.get("decision"), default="none")
        decision_confidence = _normalize_text(
            decision_payload.get("confidence"),
            default="none",
        )
        decision_actor = _normalize_text(decision_payload.get("decision_actor"), default="none")
        decision_actor_role = _normalize_text(
            decision_payload.get("decision_actor_role"),
            default="none",
        )
        implementation_actor = _normalize_text(
            decision_payload.get("implementation_actor"),
            default="none",
        )
        implementation_actor_role = _normalize_text(
            decision_payload.get("implementation_actor_role"),
            default="none",
        )
        implementation_mode = _normalize_text(
            decision_payload.get("implementation_mode"),
            default="none",
        )
        implementation_output_kind = _normalize_text(
            decision_payload.get("implementation_output_kind"),
            default="none",
        )
        decision_summary = _normalize_text(decision_payload.get("summary"), default="")
        decision_commit_allowed = bool(decision_payload.get("commit_allowed", False))
        decision_rollback_required = bool(
            decision_payload.get("rollback_required", False)
        )
        decision_human_review_required = bool(
            decision_payload.get("human_review_required", False)
        )
        decision_same_actor_requires_human_review = bool(
            decision_payload.get(
                "same_actor_requires_human_review",
                same_actor_requires_human_review,
            )
        )
        decision_actor_separation_required = bool(
            decision_payload.get(
                "actor_separation_required",
                actor_separation_required,
            )
        )
        implementation_allowed = bool(decision_payload.get("implementation_allowed", False))
        implementation_requires_human_apply = bool(
            decision_payload.get("implementation_requires_human_apply", True)
        )
        implementation_constraints = _normalize_string_list(
            decision_payload.get("implementation_constraints")
        )
        implementation_forbidden_actions = _normalize_string_list(
            decision_payload.get("implementation_forbidden_actions")
        )
        required_checks_count = len(
            _normalize_string_list(decision_payload.get("required_checks"))
        )
        changed_files_reviewed_count = len(
            _normalize_string_list(decision_payload.get("changed_files_reviewed"))
        )
        risk_flags_count = len(
            _normalize_string_list(decision_payload.get("risk_flags"))
        )
        missing_evidence_count = len(
            _normalize_string_list(decision_payload.get("missing_evidence"))
        )
        validation_summary_status = _normalize_text(
            dict(decision_payload.get("validation_summary") or {}).get("status"),
            default="insufficient_truth",
        )
        accounting_summary_status = _normalize_text(
            dict(decision_payload.get("accounting_summary") or {}).get("status"),
            default="insufficient_truth",
        )
        safety_summary_payload = dict(decision_payload.get("safety_summary") or {})
        safety_summary_status = _normalize_text(
            safety_summary_payload.get("safety_status"),
            default="insufficient_truth",
        )
        safety_forbidden_detected = bool(
            safety_summary_payload.get("forbidden_behavior_detected", False)
        )
        actor_summary_status = _normalize_text(
            dict(decision_payload.get("actor_summary") or {}).get("status"),
            default="insufficient_truth",
        )
        implementation_summary_payload = dict(
            decision_payload.get("implementation_summary") or {}
        )
        implementation_allowed_files = _normalize_string_list(
            implementation_summary_payload.get("allowed_files")
            or decision_payload.get("allowed_files")
        )
        implementation_forbidden_files = _normalize_string_list(
            implementation_summary_payload.get("forbidden_files")
            or decision_payload.get("forbidden_files")
        )
        implementation_summary_status = _normalize_text(
            implementation_summary_payload.get("status"),
            default="insufficient_truth",
        )

        if decision_actor == "none":
            actor_separation_status = "insufficient_truth"
        elif implementation_actor == "none":
            actor_separation_status = "separated"
        elif decision_actor == implementation_actor:
            actor_separation_status = "same_actor_human_review_required"
            if (
                not decision_same_actor_requires_human_review
                or not decision_human_review_required
                or decision_commit_allowed
            ):
                actor_separation_status = "failed"
        else:
            actor_separation_status = "separated"

        actor_separation_failed = False
        actor_separation_insufficient_truth = False
        if decision_actor_separation_required:
            if actor_separation_status == "failed":
                actor_separation_failed = True
            if actor_separation_status == "insufficient_truth":
                actor_separation_failed = True
                actor_separation_insufficient_truth = True

        validation_gate_ok = validation_summary_status in {"passed", "partial"}
        accounting_gate_ok = accounting_summary_status in {
            "accurate",
            "corrected",
            "inconsistent_but_corrected",
            "acceptable",
        }
        safety_gate_ok = (
            safety_summary_status in {"clear", "passed", "acceptable"}
            and not safety_forbidden_detected
        )
        actor_gate_ok = actor_summary_status in {
            "separated",
            "human_approved_same_actor",
        }
        commit_gate_ok = bool(
            validation_gate_ok
            and accounting_gate_ok
            and safety_gate_ok
            and actor_gate_ok
            and not decision_rollback_required
            and not decision_human_review_required
            and not decision_same_actor_requires_human_review
            and not actor_separation_failed
            and not final_human_review_required
        )
        commit_gate_status = "allowed" if commit_gate_ok else "blocked"
        commit_requested = bool(
            decision_commit_allowed or decision_value == "commit_allowed"
        )
        effective_commit_allowed = bool(commit_requested and commit_gate_ok)

        if missing_required_fields:
            validator_status = "missing_required_fields"
            validator_block_reason = "decision_json_missing_required_fields"
            validator_next_action = "manual_fix_missing_required_fields"
            consumption_status = "blocked"
            consumption_block_reason = "missing_required_fields"
            consumption_next_action = "manual_fix_required"
        elif invalid_allowed_value_fields:
            validator_status = "invalid_allowed_values"
            validator_block_reason = "decision_json_invalid_allowed_values"
            validator_next_action = "manual_fix_invalid_allowed_values"
            consumption_status = "blocked"
            consumption_block_reason = "invalid_allowed_values"
            consumption_next_action = "manual_fix_required"
        elif actor_separation_failed:
            validator_status = "actor_separation_failed"
            validator_block_reason = (
                "insufficient_truth"
                if actor_separation_insufficient_truth
                else "actor_separation_failed"
            )
            validator_source_status = (
                "insufficient_truth"
                if actor_separation_insufficient_truth
                else "valid"
            )
            validator_next_action = "human_review_required"
            consumption_status = "blocked"
            consumption_block_reason = (
                "insufficient_truth"
                if actor_separation_insufficient_truth
                else "actor_separation_failed"
            )
            consumption_next_action = "human_review_required"
        elif decision_rollback_required:
            validator_status = "rollback_required"
            validator_block_reason = "rollback_required"
            validator_next_action = "rollback_required"
            consumption_status = "blocked"
            consumption_block_reason = "rollback_required"
            consumption_next_action = "rollback_required"
        elif decision_human_review_required:
            validator_status = "human_review_required"
            validator_block_reason = "human_review_required"
            validator_next_action = "human_review_required"
            consumption_status = "blocked"
            consumption_block_reason = "human_review_required"
            consumption_next_action = "human_review_required"
        elif commit_requested and not effective_commit_allowed:
            validator_status = "commit_blocked"
            validator_block_reason = "commit_gate_blocked"
            validator_next_action = "human_review_required"
            consumption_status = "blocked"
            consumption_block_reason = "commit_blocked"
            consumption_next_action = "human_review_required"
        else:
            validator_status = "valid"
            validator_block_reason = "none"
            validator_next_action = "consume_valid_chatgpt_decision_json"
            consumption_status = "ready"
            consumption_block_reason = "none"
            consumption_next_action = "consume_valid_chatgpt_decision_json"
            consumption_ready = True

    return {
        "project_browser_autonomous_chatgpt_decision_validator_status": validator_status,
        "project_browser_autonomous_chatgpt_decision_validator_source_status": (
            validator_source_status
        ),
        "project_browser_autonomous_chatgpt_decision_validator_block_reason": (
            validator_block_reason
        ),
        "project_browser_autonomous_chatgpt_decision_validator_missing_required_fields": (
            _serialize_required_signals(missing_required_fields)
        ),
        "project_browser_autonomous_chatgpt_decision_validator_invalid_allowed_value_fields": (
            _serialize_required_signals(invalid_allowed_value_fields)
        ),
        "project_browser_autonomous_chatgpt_decision_validator_actor_separation_status": (
            actor_separation_status
        ),
        "project_browser_autonomous_chatgpt_decision_validator_commit_gate_status": (
            commit_gate_status
        ),
        "project_browser_autonomous_chatgpt_decision_validator_next_action": (
            validator_next_action
        ),
        "project_browser_autonomous_chatgpt_decision_validator_runtime_posture": (
            validator_runtime_posture
        ),
        "project_browser_autonomous_chatgpt_decision_json_status": decision_json_status,
        "project_browser_autonomous_chatgpt_decision_json_path": str(decision_json_path),
        "project_browser_autonomous_chatgpt_decision_json_schema_version": (
            decision_schema_version
        ),
        "project_browser_autonomous_chatgpt_decision_json_decision": decision_value,
        "project_browser_autonomous_chatgpt_decision_json_confidence": (
            decision_confidence
        ),
        "project_browser_autonomous_chatgpt_decision_json_decision_actor": decision_actor,
        "project_browser_autonomous_chatgpt_decision_json_decision_actor_role": (
            decision_actor_role
        ),
        "project_browser_autonomous_chatgpt_decision_json_implementation_actor": (
            implementation_actor
        ),
        "project_browser_autonomous_chatgpt_decision_json_implementation_actor_role": (
            implementation_actor_role
        ),
        "project_browser_autonomous_chatgpt_decision_json_implementation_mode": (
            implementation_mode
        ),
        "project_browser_autonomous_chatgpt_decision_json_implementation_output_kind": (
            implementation_output_kind
        ),
        "project_browser_autonomous_chatgpt_decision_json_commit_allowed": (
            decision_commit_allowed
        ),
        "project_browser_autonomous_chatgpt_decision_json_rollback_required": (
            decision_rollback_required
        ),
        "project_browser_autonomous_chatgpt_decision_json_human_review_required": (
            decision_human_review_required
        ),
        "project_browser_autonomous_chatgpt_decision_json_same_actor_requires_human_review": (
            decision_same_actor_requires_human_review
        ),
        "project_browser_autonomous_chatgpt_decision_json_actor_separation_required": (
            decision_actor_separation_required
        ),
        "project_browser_autonomous_chatgpt_decision_json_required_checks_count": (
            required_checks_count
        ),
        "project_browser_autonomous_chatgpt_decision_json_changed_files_reviewed_count": (
            changed_files_reviewed_count
        ),
        "project_browser_autonomous_chatgpt_decision_json_risk_flags_count": (
            risk_flags_count
        ),
        "project_browser_autonomous_chatgpt_decision_json_missing_evidence_count": (
            missing_evidence_count
        ),
        "project_browser_autonomous_chatgpt_decision_json_validation_summary_status": (
            validation_summary_status
        ),
        "project_browser_autonomous_chatgpt_decision_json_accounting_summary_status": (
            accounting_summary_status
        ),
        "project_browser_autonomous_chatgpt_decision_json_safety_summary_status": (
            safety_summary_status
        ),
        "project_browser_autonomous_chatgpt_decision_json_actor_summary_status": (
            actor_summary_status
        ),
        "project_browser_autonomous_chatgpt_decision_json_implementation_summary_status": (
            implementation_summary_status
        ),
        "project_browser_autonomous_chatgpt_decision_json_summary": decision_summary,
        "project_browser_autonomous_chatgpt_decision_json_implementation_allowed": (
            implementation_allowed
        ),
        "project_browser_autonomous_chatgpt_decision_json_implementation_requires_human_apply": (
            implementation_requires_human_apply
        ),
        "project_browser_autonomous_chatgpt_decision_json_implementation_constraints": (
            implementation_constraints
        ),
        "project_browser_autonomous_chatgpt_decision_json_implementation_forbidden_actions": (
            implementation_forbidden_actions
        ),
        "project_browser_autonomous_chatgpt_decision_json_implementation_allowed_files": (
            implementation_allowed_files
        ),
        "project_browser_autonomous_chatgpt_decision_json_implementation_forbidden_files": (
            implementation_forbidden_files
        ),
        "project_browser_autonomous_chatgpt_decision_consumption_status": (
            consumption_status
        ),
        "project_browser_autonomous_chatgpt_decision_consumption_ready": (
            bool(consumption_ready)
        ),
        "project_browser_autonomous_chatgpt_decision_consumption_block_reason": (
            consumption_block_reason
        ),
        "project_browser_autonomous_chatgpt_decision_consumption_next_action": (
            consumption_next_action
        ),
        "project_browser_autonomous_chatgpt_decision_consumption_commit_allowed_effective": (
            bool(effective_commit_allowed)
        ),
        "project_browser_autonomous_chatgpt_decision_consumption_rollback_required": (
            bool(decision_rollback_required)
        ),
        "project_browser_autonomous_chatgpt_decision_consumption_human_review_required": (
            bool(decision_human_review_required)
        ),
        "project_browser_autonomous_chatgpt_decision_consumption_runtime_posture": (
            [
                "local_file_intake_only",
                "validator_classification_only",
                "no_chatgpt_runtime_invocation",
                "no_patch_generation_or_apply",
            ]
        ),
    }

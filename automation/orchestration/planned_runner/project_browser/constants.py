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

_AUTONOMY_BROWSER_ORCHESTRATOR_SPEC_REF = (
    "docs/autonomy_browser_orchestrator.md#autonomy-browser-orchestrator"
)
_PROJECT_BROWSER_TASK_SCHEMA_REF = (
    f"{_AUTONOMY_BROWSER_ORCHESTRATOR_SPEC_REF}#structured-output-policy-base-schema"
)

_PROJECT_BROWSER_CHAT_ROTATION_TARGET = 80

_PROJECT_BROWSER_CHAT_ROTATION_NEAR_THRESHOLD = 75

_PROJECT_BROWSER_CONTINUATION_THRESHOLD = 90

_PROJECT_BROWSER_RETRY_LIMIT = 2

_PROJECT_BROWSER_TASK_TYPES = {
    "planner",
    "review",
    "repair",
    "scoring",
    "prompt_generator",
    "test_spec",
    "none",
}

_PROJECT_BROWSER_TASK_STATUSES = {
    "inactive",
    "available",
    "invalid_response",
    "insufficient_truth",
}

_PROJECT_BROWSER_TASK_ENVELOPE_STATUSES = {"ready", "inactive", "insufficient_truth"}

_PROJECT_BROWSER_RESPONSE_STATUSES = {
    "valid",
    "invalid_response",
    "unavailable",
    "inactive",
}

_PROJECT_BROWSER_CHAT_TURN_POSTURES = {
    "inactive",
    "under_target",
    "near_rotation",
    "rotation_due",
    "insufficient_truth",
}

_PROJECT_BROWSER_HANDOFF_SUMMARY_POSTURES = {
    "not_required",
    "required",
    "available",
    "insufficient_truth",
}

_PROJECT_BROWSER_UI_READINESS_STATUSES = {
    "inactive",
    "unavailable",
    "ready",
    "insufficient_truth",
}

_PROJECT_BROWSER_UI_FAILURE_STATUSES = {
    "no_failure",
    "retryable_ui_failure",
    "loading_timeout",
    "login_interruption",
    "response_unavailable",
    "insufficient_truth",
}

_PROJECT_BROWSER_UI_RECOVERY_ACTIONS = {
    "same_chat_retry",
    "resend_same_prompt",
    "page_reload",
    "new_chat_handoff",
    "escalate",
}

_PROJECT_BROWSER_SELECTOR_TARGETS = (
    "chat_input",
    "send_trigger",
    "latest_assistant_response",
    "new_chat_trigger",
    "message_ready",
    "loading_state",
    "retryable_ui_failure",
    "login_interruption",
)

_PROJECT_BROWSER_SELECTOR_REQUIRED_PROBE_TARGETS = (
    "chat_input",
    "send_trigger",
    "latest_assistant_response",
    "message_ready",
    "loading_state",
    "retryable_ui_failure",
    "login_interruption",
)

_PROJECT_BROWSER_PROMPT_PAYLOAD_STATUSES = {
    "inactive",
    "unavailable",
    "ready",
    "insufficient_truth",
}

_PROJECT_BROWSER_PROMPT_PAYLOAD_STYLES = {"summary_first"}

_PROJECT_BROWSER_PROMPT_CONTEXT_LEVELS = {
    "minimal",
    "expanded",
    "insufficient_truth",
}

_PROJECT_BROWSER_PROMPT_TOKEN_POSTURES = {
    "compact",
    "expanded_required",
    "blocked_insufficient_truth",
}

_PROJECT_BROWSER_PROMPT_RUNTIME_POSTURES = {
    "metadata_only",
    "no_browser_send",
    "no_dom_read",
    "no_session_check",
}

_PROJECT_BROWSER_RESPONSE_ASSIMILATION_STATUSES = {
    "inactive",
    "unavailable",
    "assimilated",
    "invalid_response",
    "insufficient_truth",
}

_PROJECT_BROWSER_ASSIMILATED_DECISIONS = {
    "continue",
    "retry",
    "replan",
    "split",
    "repair",
    "restart",
    "escalate",
    "stop",
    "unavailable",
}

_PROJECT_BROWSER_ASSIMILATED_RISK_LEVELS = {
    "low",
    "medium",
    "high",
    "critical",
    "unavailable",
}

_PROJECT_BROWSER_SCORE_POSTURES = {
    "above_threshold",
    "below_threshold",
    "unavailable",
    "insufficient_truth",
}

_PROJECT_BROWSER_PROOF_POSTURES = {
    "proof_available",
    "proof_missing",
    "proof_loss",
    "unavailable",
    "insufficient_truth",
}

_PROJECT_BROWSER_NEXT_ACTION_POSTURES = {
    "no_action",
    "candidate_continue",
    "candidate_retry",
    "candidate_replan",
    "candidate_split",
    "candidate_repair",
    "candidate_restart",
    "candidate_escalate",
    "candidate_stop",
}

_PROJECT_BROWSER_ASSIMILATION_RUNTIME_POSTURES = {
    "metadata_only",
    "no_queue_mutation",
    "no_retry_execution",
    "no_repair_execution",
    "no_restart_execution",
    "no_browser_action",
}

_PROJECT_BROWSER_UI_RECOVERY_DECISION_STATUSES = {
    "inactive",
    "unavailable",
    "selected",
    "blocked",
    "insufficient_truth",
}

_PROJECT_BROWSER_UI_RECOVERY_CANDIDATES = {
    "none",
    "same_chat_retry",
    "resend_same_prompt",
    "page_reload",
    "new_chat_handoff",
    "escalate",
}

_PROJECT_BROWSER_UI_RECOVERY_REASONS = {
    "no_failure",
    "retryable_ui_failure",
    "loading_timeout",
    "login_interruption",
    "response_unavailable",
    "invalid_response",
    "assimilation_candidate_retry",
    "assimilation_candidate_repair",
    "assimilation_candidate_restart",
    "rotation_due",
    "retry_limit_reached",
    "insufficient_truth",
}

_PROJECT_BROWSER_UI_RETRY_COUNT_POSTURES = {
    "not_applicable",
    "retry_available",
    "retry_limit_reached",
    "insufficient_truth",
}

_PROJECT_BROWSER_UI_HANDOFF_DEPENDENCY_POSTURES = {
    "not_required",
    "required_available",
    "required_missing",
    "insufficient_truth",
}

_PROJECT_BROWSER_UI_RECOVERY_RUNTIME_POSTURES = {
    "metadata_only",
    "no_same_chat_retry_execution",
    "no_resend_execution",
    "no_page_reload_execution",
    "no_new_chat_execution",
    "no_login_recovery_execution",
    "no_browser_action",
}

_PROJECT_BROWSER_HANDOFF_COMPILE_STATUSES = {
    "inactive",
    "not_required",
    "ready",
    "unavailable",
    "insufficient_truth",
}

_PROJECT_BROWSER_HANDOFF_TRIGGERS = {
    "none",
    "rotation_due",
    "new_chat_handoff_recovery",
    "manual_required",
    "insufficient_truth",
}

_PROJECT_BROWSER_HANDOFF_SECTION_NAMES = (
    "project_summary",
    "active_objective_summary",
    "completed_objective_summary",
    "blocked_items",
    "failure_memory_summary",
    "current_budgets_limits",
    "current_repo_constraints",
    "next_intended_action",
)

_PROJECT_BROWSER_HANDOFF_PAYLOAD_POSTURES = {
    "compact_ready",
    "missing_required_sections",
    "unavailable",
    "insufficient_truth",
}

_PROJECT_BROWSER_HANDOFF_RUNTIME_POSTURES = {
    "metadata_only",
    "no_new_chat_execution",
    "no_browser_send",
    "no_dom_read",
    "no_session_check",
    "no_handoff_delivery",
}

_PROJECT_BROWSER_EXECUTION_HANDOFF_STATUSES = {
    "inactive",
    "blocked",
    "ready",
    "unavailable",
    "insufficient_truth",
}

_PROJECT_BROWSER_EXECUTION_HANDOFF_KINDS = {
    "none",
    "send_prompt",
    "wait_for_response",
    "same_chat_retry",
    "resend_same_prompt",
    "page_reload",
    "new_chat_handoff",
    "pause_for_login",
    "escalate",
}

_PROJECT_BROWSER_EXECUTION_BLOCK_REASONS = {
    "none",
    "browser_task_inactive",
    "payload_unavailable",
    "ui_not_ready",
    "selector_contract_missing",
    "response_unavailable",
    "recovery_blocked",
    "handoff_missing",
    "login_interruption",
    "retry_limit_reached",
    "insufficient_truth",
}

_PROJECT_BROWSER_EXECUTION_PREREQUISITE_VALUES = {
    "inactive",
    "not_required",
    "ready",
    "unavailable",
    "blocked",
    "insufficient_truth",
}

_PROJECT_BROWSER_EXECUTION_RUNTIME_POSTURES = {
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
}

_PROJECT_BROWSER_EXECUTOR_CONTRACT_VERSION = "browser_execution_handoff_v1"

_PROJECT_BROWSER_EXECUTOR_INTERFACE_STATUSES = {
    "inactive",
    "unavailable",
    "contract_ready",
    "blocked",
    "insufficient_truth",
}

_PROJECT_BROWSER_EXECUTOR_MODES = {
    "none",
    "stub_only",
    "dry_run_contract_only",
    "future_playwright",
}

_PROJECT_BROWSER_EXECUTOR_CAPABILITY_POSTURES = {
    "accepts_handoff_contract",
    "validates_contract_shape",
    "returns_non_execution_receipt",
    "does_not_open_browser",
    "does_not_call_playwright",
    "does_not_touch_dom",
    "does_not_send_prompt",
    "does_not_wait_response",
}

_PROJECT_BROWSER_EXECUTOR_RECEIPT_STATUSES = {
    "not_created",
    "receipt_ready",
    "blocked",
    "insufficient_truth",
}

_PROJECT_BROWSER_EXECUTOR_RECEIPT_KINDS = {
    "none",
    "non_execution_stub_receipt",
    "dry_run_contract_receipt",
}

_PROJECT_BROWSER_EXECUTOR_BLOCK_REASONS = {
    "none",
    "handoff_inactive",
    "handoff_blocked",
    "handoff_unavailable",
    "contract_version_unsupported",
    "prerequisite_not_ready",
    "insufficient_truth",
}

_PROJECT_BROWSER_EXECUTOR_INTERFACE_CONTRACT_VERSION = "browser_executor_interface_v1"

_PROJECT_BROWSER_COMMAND_QUEUE_STATUSES = {
    "inactive",
    "empty",
    "prepared",
    "blocked",
    "unavailable",
    "insufficient_truth",
}

_PROJECT_BROWSER_COMMAND_QUEUE_MODES = {
    "none",
    "single_command",
    "dry_run_contract_only",
}

_PROJECT_BROWSER_COMMAND_TYPES = {
    "none",
    "send_prompt",
    "wait_for_response",
    "same_chat_retry",
    "resend_same_prompt",
    "page_reload",
    "new_chat_handoff",
    "pause_for_login",
    "escalate",
}

_PROJECT_BROWSER_COMMAND_SOURCES = {
    "none",
    "pr97_execution_handoff",
    "pr98_executor_interface",
    "recovery_candidate",
    "handoff_contract",
    "insufficient_truth",
}

_PROJECT_BROWSER_COMMAND_PRECONDITION_VALUES = {
    "inactive",
    "not_required",
    "ready",
    "unavailable",
    "blocked",
    "insufficient_truth",
}

_PROJECT_BROWSER_COMMAND_BLOCK_REASONS = {
    "none",
    "executor_interface_inactive",
    "executor_interface_blocked",
    "executor_interface_unavailable",
    "unsupported_command_type",
    "precondition_missing",
    "payload_unavailable",
    "selector_contract_missing",
    "handoff_missing",
    "login_interruption",
    "retry_limit_reached",
    "insufficient_truth",
}

_PROJECT_BROWSER_COMMAND_RECEIPT_STATUSES = {
    "not_created",
    "dry_run_ready",
    "blocked",
    "unavailable",
    "insufficient_truth",
}

_PROJECT_BROWSER_COMMAND_RECEIPT_KINDS = {
    "none",
    "dry_run_command_receipt",
    "non_execution_command_receipt",
}

_PROJECT_BROWSER_COMMAND_RECEIPT_RESULTS = {
    "not_executed",
    "blocked",
    "unavailable",
    "insufficient_truth",
}

_PROJECT_BROWSER_COMMAND_RUNTIME_POSTURES = {
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
}

_PROJECT_BROWSER_PLAYWRIGHT_BOUNDARY_STATUSES = {
    "inactive",
    "unavailable",
    "available",
    "blocked",
    "insufficient_truth",
}

_PROJECT_BROWSER_PLAYWRIGHT_IMPORT_POSTURES = {
    "not_checked",
    "import_available",
    "import_unavailable",
    "import_not_required",
    "insufficient_truth",
}

_PROJECT_BROWSER_SESSION_CONFIG_STATUSES = {
    "inactive",
    "unavailable",
    "configured",
    "blocked",
    "insufficient_truth",
}

_PROJECT_BROWSER_SESSION_MODES = {
    "none",
    "existing_profile",
    "persistent_context",
    "explicit_user_data_dir",
    "insufficient_truth",
}

_PROJECT_BROWSER_LAUNCH_PREFLIGHT_STATUSES = {
    "inactive",
    "unavailable",
    "ready",
    "blocked",
    "insufficient_truth",
}

_PROJECT_BROWSER_LAUNCH_PREFLIGHT_MODES = {
    "none",
    "metadata_only",
    "launch_allowed_later",
    "blocked",
}

_PROJECT_BROWSER_LOGIN_PREFLIGHT_POSTURES = {
    "not_checked",
    "assumed_existing_session",
    "login_pause_required_if_detected_later",
    "blocked",
    "insufficient_truth",
}

_PROJECT_BROWSER_RUNTIME_BLOCK_REASONS = {
    "none",
    "command_queue_inactive",
    "command_queue_blocked",
    "command_queue_unavailable",
    "command_not_prepared",
    "playwright_import_unavailable",
    "session_config_missing",
    "launch_not_allowed",
    "unsupported_command_type",
    "login_truth_missing",
    "insufficient_truth",
}

_PROJECT_BROWSER_LAUNCH_RECEIPT_STATUSES = {
    "not_created",
    "preflight_ready",
    "blocked",
    "unavailable",
    "insufficient_truth",
}

_PROJECT_BROWSER_LAUNCH_RECEIPT_KINDS = {
    "none",
    "launch_preflight_receipt",
    "non_execution_launch_receipt",
}

_PROJECT_BROWSER_LAUNCH_STATUSES = {
    "inactive",
    "not_attempted",
    "launched",
    "blocked",
    "failed",
    "insufficient_truth",
}

_PROJECT_BROWSER_CONTEXT_STATUSES = {
    "inactive",
    "not_attempted",
    "opened",
    "blocked",
    "failed",
    "insufficient_truth",
}

_PROJECT_BROWSER_PAGE_OPEN_STATUSES = {
    "inactive",
    "not_attempted",
    "opened",
    "blocked",
    "failed",
    "insufficient_truth",
}

_PROJECT_BROWSER_CHATGPT_PAGE_STATUSES = {
    "inactive",
    "not_attempted",
    "opened",
    "login_interruption",
    "unavailable",
    "blocked",
    "failed",
    "insufficient_truth",
}

_PROJECT_BROWSER_LOGIN_INTERRUPTION_STATUSES = {
    "not_checked",
    "detected",
    "not_detected",
    "insufficient_truth",
}

_PROJECT_BROWSER_LAUNCH_BLOCK_REASONS = {
    "none",
    "preflight_inactive",
    "preflight_blocked",
    "preflight_unavailable",
    "preflight_not_ready",
    "playwright_unavailable",
    "session_config_missing",
    "launch_failed",
    "page_open_failed",
    "login_interruption",
    "unsupported_command_type",
    "insufficient_truth",
}

_PROJECT_BROWSER_LAUNCH_RUNTIME_POSTURES = {
    "launch_attempted",
    "page_open_attempted",
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
}

_PROJECT_BROWSER_LAUNCH_RECEIPT_STATUSES_RUNTIME = {
    "not_created",
    "launch_opened",
    "login_pause_required",
    "blocked",
    "failed",
    "insufficient_truth",
}

_PROJECT_BROWSER_LAUNCH_RECEIPT_KINDS_RUNTIME = {
    "none",
    "browser_launch_page_open_receipt",
    "login_interruption_receipt",
    "blocked_launch_receipt",
    "failed_launch_receipt",
}

_PROJECT_BROWSER_SELECTOR_RESOLVER_STATUSES = {
    "inactive",
    "not_attempted",
    "resolved",
    "partially_resolved",
    "blocked",
    "failed",
    "insufficient_truth",
}

_PROJECT_BROWSER_SELECTOR_PROBE_STATUSES = {
    "inactive",
    "not_attempted",
    "ready",
    "not_ready",
    "blocked",
    "failed",
    "insufficient_truth",
}

_PROJECT_BROWSER_SELECTOR_TARGET_STATUSES = {
    "missing",
    "found",
    "not_checked",
    "blocked",
    "insufficient_truth",
}

_PROJECT_BROWSER_DOM_READINESS_STATUSES = {
    "inactive",
    "not_attempted",
    "ready",
    "not_ready",
    "login_interruption",
    "blocked",
    "failed",
    "insufficient_truth",
}

_PROJECT_BROWSER_DOM_PROBE_BLOCK_REASONS = {
    "none",
    "launch_inactive",
    "page_not_opened",
    "login_interruption",
    "selector_contract_missing",
    "selector_not_found",
    "playwright_unavailable",
    "page_unavailable",
    "probe_failed",
    "unsupported_command_type",
    "insufficient_truth",
}

_PROJECT_BROWSER_SELECTOR_RUNTIME_POSTURES = {
    "read_only_probe",
    "no_prompt_fill",
    "no_send_click",
    "no_response_wait",
    "no_response_read",
    "no_json_parse",
    "no_retry_execution",
    "no_reload_execution",
    "no_new_chat_execution",
    "no_login_recovery",
    "no_executor_loop",
}

_PROJECT_BROWSER_SELECTOR_PROBE_RECEIPT_STATUSES = {
    "not_created",
    "ready",
    "not_ready",
    "login_pause_required",
    "blocked",
    "failed",
    "insufficient_truth",
}

_PROJECT_BROWSER_SELECTOR_PROBE_RECEIPT_KINDS = {
    "none",
    "read_only_dom_probe_receipt",
    "login_interruption_receipt",
    "blocked_probe_receipt",
    "failed_probe_receipt",
}

_PROJECT_BROWSER_PROMPT_FILL_STATUSES = {
    "inactive",
    "not_attempted",
    "filled",
    "blocked",
    "failed",
    "insufficient_truth",
}

_PROJECT_BROWSER_PROMPT_FILL_SOURCE_STATUSES = {
    "unavailable",
    "available",
    "insufficient_truth",
}

_PROJECT_BROWSER_PROMPT_FILL_TARGET_STATUSES = {
    "missing",
    "available",
    "blocked",
    "insufficient_truth",
}

_PROJECT_BROWSER_PROMPT_FILL_BLOCK_REASONS = {
    "none",
    "dom_not_ready",
    "chat_input_missing",
    "prompt_text_missing",
    "prompt_text_empty",
    "fill_failed",
    "login_interruption",
    "unsupported_command_type",
    "insufficient_truth",
}

_PROJECT_BROWSER_PROMPT_FILL_RUNTIME_POSTURES = {
    "fill_attempted",
    "no_send_click",
    "no_enter_submit",
    "no_response_wait",
    "no_response_read",
    "no_json_parse",
    "no_retry_execution",
    "no_reload_execution",
    "no_new_chat_execution",
    "no_login_recovery",
    "no_executor_loop",
}

_PROJECT_BROWSER_PROMPT_FILL_RECEIPT_STATUSES = {
    "not_created",
    "filled",
    "blocked",
    "failed",
    "insufficient_truth",
}

_PROJECT_BROWSER_PROMPT_FILL_RECEIPT_KINDS = {
    "none",
    "prompt_fill_receipt",
    "blocked_fill_receipt",
    "failed_fill_receipt",
}

_PROJECT_BROWSER_PROMPT_SEND_STATUSES = {
    "inactive",
    "not_attempted",
    "sent",
    "blocked",
    "failed",
    "insufficient_truth",
}

_PROJECT_BROWSER_PROMPT_SEND_TARGET_STATUSES = {
    "missing",
    "available",
    "blocked",
    "insufficient_truth",
}

_PROJECT_BROWSER_PROMPT_SEND_BLOCK_REASONS = {
    "none",
    "fill_not_ready",
    "send_trigger_missing",
    "send_failed",
    "login_interruption",
    "unsupported_command_type",
    "insufficient_truth",
}

_PROJECT_BROWSER_PROMPT_SEND_RUNTIME_POSTURES = {
    "send_click_attempted",
    "no_response_wait",
    "no_response_read",
    "no_json_parse",
    "no_retry_execution",
    "no_reload_execution",
    "no_new_chat_execution",
    "no_login_recovery",
    "no_executor_loop",
}

_PROJECT_BROWSER_PROMPT_SEND_RECEIPT_STATUSES = {
    "not_created",
    "sent",
    "blocked",
    "failed",
    "insufficient_truth",
}

_PROJECT_BROWSER_PROMPT_SEND_RECEIPT_KINDS = {
    "none",
    "prompt_send_receipt",
    "blocked_send_receipt",
    "failed_send_receipt",
}

_PROJECT_BROWSER_RESPONSE_WAIT_STATUSES = {
    "inactive",
    "not_attempted",
    "completed",
    "timeout",
    "blocked",
    "failed",
    "insufficient_truth",
}

_PROJECT_BROWSER_RESPONSE_READ_STATUSES = {
    "inactive",
    "not_attempted",
    "read",
    "empty",
    "blocked",
    "failed",
    "insufficient_truth",
}

_PROJECT_BROWSER_RESPONSE_TEXT_STATUSES = {
    "unavailable",
    "available",
    "empty",
    "too_large",
    "insufficient_truth",
}

_PROJECT_BROWSER_RESPONSE_WAIT_BLOCK_REASONS = {
    "none",
    "send_not_ready",
    "assistant_response_missing",
    "response_timeout",
    "response_empty",
    "login_interruption",
    "page_unavailable",
    "unsupported_command_type",
    "insufficient_truth",
}

_PROJECT_BROWSER_RESPONSE_RUNTIME_POSTURES = {
    "response_wait_attempted",
    "response_read_attempted",
    "no_json_parse",
    "no_decision_execution",
    "no_retry_execution",
    "no_reload_execution",
    "no_new_chat_execution",
    "no_login_recovery",
    "no_executor_loop",
}

_PROJECT_BROWSER_RESPONSE_READ_RECEIPT_STATUSES = {
    "not_created",
    "response_read",
    "timeout",
    "blocked",
    "failed",
    "insufficient_truth",
}

_PROJECT_BROWSER_RESPONSE_READ_RECEIPT_KINDS = {
    "none",
    "response_wait_read_receipt",
    "timeout_receipt",
    "blocked_response_receipt",
    "failed_response_receipt",
}

_PROJECT_BROWSER_RESPONSE_JSON_PARSE_STATUSES = {
    "inactive",
    "not_attempted",
    "valid",
    "invalid_response",
    "unavailable",
    "blocked",
    "failed",
    "insufficient_truth",
}

_PROJECT_BROWSER_RESPONSE_JSON_SCHEMA_STATUSES = {
    "not_checked",
    "valid",
    "invalid",
    "missing",
    "insufficient_truth",
}

_PROJECT_BROWSER_RESPONSE_JSON_DECISION_STATUSES = {
    "unavailable",
    "parsed",
    "missing",
    "invalid",
    "insufficient_truth",
}

_PROJECT_BROWSER_EXECUTION_RECEIPT_PARSE_STATUSES = {
    "not_created",
    "parsed",
    "invalid_response",
    "blocked",
    "failed",
    "insufficient_truth",
}

_PROJECT_BROWSER_EXECUTION_RECEIPT_PARSE_KINDS = {
    "none",
    "browser_response_parse_receipt",
    "invalid_response_receipt",
    "blocked_parse_receipt",
    "failed_parse_receipt",
}

_PROJECT_BROWSER_EXECUTION_RESULT_STATUSES = {
    "not_executed",
    "response_parsed",
    "invalid_response",
    "blocked",
    "failed",
    "insufficient_truth",
}

_PROJECT_BROWSER_RESPONSE_PARSE_BLOCK_REASONS = {
    "none",
    "response_not_read",
    "response_text_missing",
    "response_text_empty",
    "response_text_too_large",
    "json_parse_failed",
    "schema_missing",
    "schema_invalid",
    "decision_missing",
    "login_interruption",
    "unsupported_command_type",
    "insufficient_truth",
}

_PROJECT_BROWSER_RESPONSE_PARSE_RUNTIME_POSTURES = {
    "json_parse_attempted",
    "no_decision_execution",
    "no_queue_mutation",
    "no_retry_execution",
    "no_repair_execution",
    "no_restart_execution",
    "no_reload_execution",
    "no_new_chat_execution",
    "no_login_recovery",
    "no_executor_loop",
}

_PROJECT_BROWSER_RECOVERY_STATUSES = {
    "inactive",
    "not_attempted",
    "recovered",
    "pause_required",
    "blocked",
    "failed",
    "insufficient_truth",
}

_PROJECT_BROWSER_RECOVERY_ACTIONS = {
    "none",
    "page_reload",
    "new_chat",
    "pause_for_login",
    "escalate",
}

_PROJECT_BROWSER_RECOVERY_REASONS = {
    "none",
    "response_timeout",
    "invalid_response",
    "response_unavailable",
    "page_unavailable",
    "loading_timeout",
    "login_interruption",
    "rotation_due",
    "handoff_missing",
    "retry_limit_reached",
    "unsupported_outcome",
    "insufficient_truth",
}

_PROJECT_BROWSER_RECOVERY_BLOCK_REASONS = {
    "none",
    "execution_receipt_missing",
    "parse_not_ready",
    "recovery_not_required",
    "recovery_not_allowed",
    "handoff_missing",
    "login_interruption",
    "retry_limit_reached",
    "page_reload_failed",
    "new_chat_failed",
    "insufficient_truth",
}

_PROJECT_BROWSER_RECOVERY_RUNTIME_POSTURES = {
    "recovery_attempted",
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
}

_PROJECT_BROWSER_RECOVERY_RECEIPT_STATUSES = {
    "not_created",
    "recovered",
    "pause_required",
    "blocked",
    "failed",
    "insufficient_truth",
}

_PROJECT_BROWSER_RECOVERY_RECEIPT_KINDS = {
    "none",
    "page_reload_recovery_receipt",
    "new_chat_recovery_receipt",
    "pause_for_login_receipt",
    "blocked_recovery_receipt",
    "failed_recovery_receipt",
}

_PROJECT_BROWSER_ONE_COMMAND_EXECUTOR_STATUSES = {
    "inactive",
    "completed",
    "completed_with_recovery",
    "blocked",
    "failed",
    "pause_required",
    "insufficient_truth",
}

_PROJECT_BROWSER_ONE_COMMAND_EXECUTOR_RESULTS = {
    "none",
    "success",
    "invalid_response",
    "timeout",
    "recovered",
    "blocked",
    "failed",
    "pause_for_login",
    "insufficient_truth",
}

_PROJECT_BROWSER_ONE_COMMAND_STOP_REASONS = {
    "none",
    "command_completed",
    "recovery_completed",
    "recovery_not_required",
    "pause_for_login",
    "blocked_by_precondition",
    "runtime_failed",
    "invalid_response",
    "timeout",
    "insufficient_truth",
}

_PROJECT_BROWSER_ONE_COMMAND_RECEIPT_STATUSES = {
    "not_created",
    "final_ready",
    "blocked",
    "failed",
    "pause_required",
    "insufficient_truth",
}

_PROJECT_BROWSER_ONE_COMMAND_RECEIPT_KINDS = {
    "none",
    "one_command_success_receipt",
    "one_command_invalid_response_receipt",
    "one_command_recovery_receipt",
    "one_command_blocked_receipt",
    "one_command_failed_receipt",
    "one_command_pause_for_login_receipt",
}

_PROJECT_BROWSER_ONE_COMMAND_RUNTIME_POSTURES = {
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
}

_PROJECT_BROWSER_AUTONOMOUS_DEV_ASSIMILATION_STATUSES = {
    "inactive",
    "assimilated",
    "blocked",
    "failed",
    "pause_required",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_DEV_OUTCOMES = {
    "none",
    "success",
    "invalid_response",
    "timeout",
    "recovered",
    "blocked",
    "failed",
    "pause_for_login",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_DEV_NEXT_ACTIONS = {
    "none",
    "draft_next_prompt",
    "draft_repair_prompt",
    "draft_md_update",
    "retry_same_prompt_candidate",
    "human_review_required",
    "pause_for_login",
    "stop",
}

_PROJECT_BROWSER_AUTONOMOUS_DEV_STOP_REASONS = {
    "none",
    "final_receipt_missing",
    "final_success",
    "invalid_response",
    "timeout",
    "recovery_completed",
    "blocked",
    "failed",
    "pause_for_login",
    "insufficient_truth",
    "unsupported_outcome",
}

_PROJECT_BROWSER_SAME_PROMPT_RETRY_POLICIES = {
    "not_applicable",
    "allowed_candidate",
    "blocked_duplicate",
    "cooldown_required",
    "retry_budget_exhausted",
    "human_review_required",
    "insufficient_truth",
}

_PROJECT_BROWSER_SAME_PROMPT_RETRY_REASONS = {
    "none",
    "rate_limit",
    "transient_timeout",
    "response_unavailable",
    "page_reload_completed",
    "new_chat_opened",
    "login_resumed",
    "invalid_response_retry_candidate",
    "no_context_change",
    "same_failure",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_DEV_RUNTIME_POSTURES = {
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
}

_PROJECT_BROWSER_AUTONOMOUS_NEXT_PROMPT_DRAFT_STATUSES = {
    "not_required",
    "ready",
    "blocked",
    "human_review_required",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_NEXT_PROMPT_KINDS = {
    "none",
    "next_pr_prompt",
    "repair_prompt",
    "retry_same_prompt",
    "stop_prompt",
    "human_review_prompt",
}

_PROJECT_BROWSER_AUTONOMOUS_NEXT_PROMPT_SCOPES = {
    "none",
    "next_pr_only",
    "repair_only",
    "retry_same_prompt_only",
    "md_update_only",
    "human_review_only",
}

_PROJECT_BROWSER_AUTONOMOUS_NEXT_PROMPT_SOURCES = {
    "none",
    "pr109_success",
    "pr109_invalid_response",
    "pr109_timeout",
    "pr109_recovered",
    "pr109_pause_for_login",
    "pr109_blocked",
    "pr109_failed",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_NEXT_PROMPT_BLOCK_REASONS = {
    "none",
    "assimilation_missing",
    "next_action_not_supported",
    "retry_policy_blocked",
    "human_review_required",
    "pause_for_login",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_MD_UPDATE_DRAFT_STATUSES = {
    "not_required",
    "ready",
    "blocked",
    "human_review_required",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_MD_UPDATE_KINDS = {
    "none",
    "pr_history_and_constraints_append",
    "constraints_only",
    "history_only",
    "human_review_only",
}

_PROJECT_BROWSER_AUTONOMOUS_MD_UPDATE_COMMAND_DRAFT_STATUSES = {
    "not_required",
    "ready",
    "blocked",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_MD_UPDATE_BLOCK_REASONS = {
    "none",
    "assimilation_missing",
    "prior_pr_summary_missing",
    "md_anchor_missing",
    "human_review_required",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_DRAFT_RUNTIME_POSTURES = {
    "metadata_only",
    "no_prompt_send",
    "no_browser_action",
    "no_md_write",
    "no_shell_execution",
    "no_queue_mutation",
    "no_continuation_execution",
    "no_retry_execution",
    "no_executor_loop",
}

_PROJECT_BROWSER_AUTONOMOUS_CONTINUATION_GATE_STATUSES = {
    "inactive",
    "allowed",
    "blocked",
    "human_review_required",
    "pause_required",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_CONTINUATION_NEXT_ACTIONS = {
    "none",
    "use_next_prompt_draft",
    "use_md_update_draft",
    "retry_same_prompt",
    "stop",
    "pause_for_login",
    "human_review",
}

_PROJECT_BROWSER_AUTONOMOUS_CONTINUATION_BLOCK_REASONS = {
    "none",
    "draft_missing",
    "md_update_missing",
    "duplicate_blocked",
    "retry_policy_blocked",
    "retry_budget_exhausted",
    "loop_suspected",
    "cooldown_required",
    "pause_for_login",
    "human_review_required",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_DUPLICATE_POLICY_STATUSES = {
    "clear",
    "duplicate_blocked",
    "retry_same_prompt_allowed",
    "cooldown_required",
    "loop_suspected",
    "human_review_required",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_DUPLICATE_REASONS = {
    "none",
    "same_prompt",
    "same_failure",
    "no_context_change",
    "allowed_after_timeout",
    "allowed_after_response_unavailable",
    "allowed_after_page_reload",
    "allowed_after_new_chat",
    "allowed_after_login_resume",
    "retry_budget_exhausted",
    "cooldown_required",
    "loop_suspected",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_RETRY_BUDGET_POSTURES = {
    "not_applicable",
    "available",
    "exhausted",
    "cooldown_required",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_GATE_RUNTIME_POSTURES = {
    "metadata_only",
    "no_prompt_send",
    "no_md_write",
    "no_shell_execution",
    "no_browser_action",
    "no_queue_mutation",
    "no_retry_execution",
    "no_continuation_execution",
    "no_controller_loop",
}

_PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_STATUSES = {
    "inactive",
    "ready",
    "selected_one_action",
    "blocked",
    "human_review_required",
    "pause_required",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_ACTIONS = {
    "none",
    "use_md_update_draft",
    "use_next_prompt_draft",
    "retry_same_prompt",
    "pause_for_login",
    "human_review",
    "stop",
}

_PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_ACTION_SOURCES = {
    "none",
    "pr111_gate",
    "pr110_draft",
    "pr109_assimilation",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_STOP_REASONS = {
    "none",
    "one_action_selected",
    "gate_inactive",
    "gate_blocked",
    "duplicate_blocked",
    "retry_budget_exhausted",
    "cooldown_required",
    "pause_for_login",
    "human_review_required",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_RECEIPT_STATUSES = {
    "not_created",
    "ready",
    "blocked",
    "human_review_required",
    "pause_required",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_RECEIPT_KINDS = {
    "none",
    "one_pr_controller_receipt",
    "blocked_controller_receipt",
    "human_review_controller_receipt",
    "pause_for_login_controller_receipt",
}

_PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_RUNTIME_POSTURES = {
    "metadata_only",
    "no_prompt_send",
    "no_md_write",
    "no_shell_execution",
    "no_browser_action",
    "no_queue_mutation",
    "no_retry_execution",
    "no_continuation_execution",
    "no_multi_action",
    "no_controller_loop",
    "no_background_runtime",
}

_PROJECT_BROWSER_AUTONOMOUS_RUN_LEDGER_STATUSES = {
    "inactive",
    "ready",
    "blocked",
    "duplicate_risk",
    "human_review_required",
    "pause_required",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_RUN_LEDGER_ENTRY_STATUSES = {
    "not_created",
    "created",
    "blocked",
    "duplicate_risk",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_RUN_LEDGER_ENTRY_KINDS = {
    "none",
    "selected_action_entry",
    "blocked_action_entry",
    "pause_action_entry",
    "human_review_action_entry",
}

_PROJECT_BROWSER_AUTONOMOUS_ACTION_IDENTITY_STATUSES = {
    "unavailable",
    "available",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_ACTION_KINDS = {
    "none",
    "use_md_update_draft",
    "use_next_prompt_draft",
    "retry_same_prompt",
    "pause_for_login",
    "human_review",
    "stop",
}

_PROJECT_BROWSER_AUTONOMOUS_ACTION_FINGERPRINT_STATUSES = {
    "unavailable",
    "available",
    "duplicate",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_ACTION_DUPLICATE_STATUSES = {
    "clear",
    "duplicate_action",
    "duplicate_prompt",
    "duplicate_md_update",
    "duplicate_pause",
    "duplicate_human_review",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_ACTION_RECEIPT_STATUSES = {
    "not_created",
    "ready",
    "blocked",
    "duplicate_risk",
    "human_review_required",
    "pause_required",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_ACTION_RECEIPT_KINDS = {
    "none",
    "selected_action_receipt",
    "blocked_action_receipt",
    "duplicate_action_receipt",
    "pause_action_receipt",
    "human_review_action_receipt",
}

_PROJECT_BROWSER_AUTONOMOUS_LEDGER_RUNTIME_POSTURES = {
    "metadata_only",
    "no_selected_action_execution",
    "no_prompt_send",
    "no_md_write",
    "no_shell_execution",
    "no_browser_action",
    "no_queue_mutation",
    "no_retry_execution",
    "no_continuation_execution",
    "no_multi_action",
    "no_controller_loop",
    "no_background_runtime",
}

_PROJECT_BROWSER_AUTONOMOUS_SAFETY_SWITCH_STATUSES = {
    "inactive",
    "enabled",
    "disabled",
    "stop_all",
    "pause_after_current_step",
    "manual_review_required",
    "pause_required",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_MANUAL_OVERRIDE_STATUSES = {
    "inactive",
    "clear",
    "requested",
    "required",
    "blocked",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_MANUAL_OVERRIDE_REASONS = {
    "none",
    "user_requested_pause",
    "user_requested_stop",
    "login_required",
    "human_review_required",
    "duplicate_risk",
    "unsafe_state",
    "approval_required",
    "external_boundary",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_SAFE_STOP_STATUSES = {
    "not_required",
    "required",
    "stop_now",
    "pause_after_current_step",
    "human_review_required",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_SAFE_STOP_REASONS = {
    "none",
    "kill_switch_disabled",
    "stop_all_requested",
    "manual_override_requested",
    "pause_for_login",
    "human_review_required",
    "duplicate_risk",
    "action_receipt_blocked",
    "ledger_insufficient_truth",
    "unsafe_state",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS = {
    "allowed_candidate",
    "blocked",
    "pause_required",
    "human_review_required",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_SAFETY_RUNTIME_POSTURES = {
    "metadata_only",
    "no_selected_action_execution",
    "no_prompt_send",
    "no_md_write",
    "no_shell_execution",
    "no_browser_action",
    "no_queue_mutation",
    "no_retry_execution",
    "no_continuation_execution",
    "no_multi_step_execution",
    "no_background_runtime",
}

_PROJECT_BROWSER_AUTONOMOUS_EXECUTION_BRIDGE_STATUSES = {
    "inactive",
    "ready",
    "blocked",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_EXECUTION_BRIDGE_REASONS = {
    "none",
    "blocked_by_pr114",
    "pause_required",
    "human_review_required",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_EXECUTION_BRIDGE_SOURCE_STATUSES = {
    "valid",
    "inconsistent",
    "insufficient_truth",
}

_PROJECT_BROWSER_AUTONOMOUS_EXECUTION_BRIDGE_RUNTIME_POSTURES = {
    "metadata_only",
    "no_execution",
    "no_browser",
    "no_prompt_send",
    "no_md_write",
    "no_shell_execution",
    "no_queue_mutation",
    "no_retry_execution",
    "no_continuation_execution",
    "no_multi_step_execution",
    "no_background_runtime",
}

_PROJECT_BROWSER_PROMPT_SECTION_NAMES = (
    "project_brief_summary",
    "active_objective_summary",
    "current_constraints_summary",
    "current_state_summary",
    "latest_diff_summary",
    "failure_memory_summary",
    "budget_boundary_summary",
    "requested_task_type",
    "required_json_schema",
)

_PROJECT_BROWSER_DECISIONS = {
    "continue",
    "retry",
    "replan",
    "split",
    "repair",
    "restart",
    "escalate",
    "stop",
}

_PROJECT_BROWSER_RISK_LEVELS = {"low", "medium", "high", "critical"}

_PROJECT_BROWSER_JSON_REQUIRED_FIELDS = (
    "status",
    "task_type",
    "objective_id",
    "step_id",
    "success_score",
    "confidence_score",
    "decision",
    "decision_reason",
    "risk_level",
    "risks",
    "proofs",
    "required_actions",
    "blocked_by",
    "suggested_next_prompt",
    "summary",
    "token_list",
)

_PROJECT_BROWSER_REASON_CODES = {
    "browser_task_compiled",
    "browser_task_inactive",
    "browser_task_insufficient_truth",
    "browser_task_invalid_response",
    "browser_task_available",
    "browser_task_recover_first",
    "browser_task_type_planner",
    "browser_task_type_review",
    "browser_task_type_repair",
    "browser_task_type_scoring",
    "browser_task_type_prompt_generator",
    "browser_task_type_test_spec",
    "browser_response_valid",
    "browser_response_invalid",
    "browser_response_unavailable",
    "browser_rotation_due",
    "browser_rotation_not_due",
    "browser_handoff_required",
    "browser_handoff_available",
    "browser_handoff_not_required",
    "browser_ui_readiness_inactive",
    "browser_ui_readiness_ready",
    "browser_ui_readiness_unavailable",
    "browser_ui_readiness_insufficient_truth",
    "browser_ui_failure_no_failure",
    "browser_ui_failure_retryable",
    "browser_ui_failure_loading_timeout",
    "browser_ui_failure_login_interruption",
    "browser_ui_failure_response_unavailable",
    "browser_ui_failure_insufficient_truth",
    "browser_ui_recovery_same_chat_retry",
    "browser_ui_recovery_resend_same_prompt",
    "browser_ui_recovery_page_reload",
    "browser_ui_recovery_new_chat_handoff",
    "browser_ui_recovery_escalate",
}

_PROJECT_BROWSER_REASON_ORDER = (
    "browser_task_insufficient_truth",
    "browser_task_invalid_response",
    "browser_task_inactive",
    "browser_task_compiled",
    "browser_task_available",
    "browser_task_recover_first",
    "browser_task_type_repair",
    "browser_task_type_review",
    "browser_task_type_scoring",
    "browser_task_type_prompt_generator",
    "browser_task_type_planner",
    "browser_task_type_test_spec",
    "browser_response_invalid",
    "browser_response_unavailable",
    "browser_response_valid",
    "browser_rotation_due",
    "browser_rotation_not_due",
    "browser_handoff_required",
    "browser_handoff_available",
    "browser_handoff_not_required",
    "browser_ui_readiness_inactive",
    "browser_ui_readiness_ready",
    "browser_ui_readiness_unavailable",
    "browser_ui_readiness_insufficient_truth",
    "browser_ui_failure_no_failure",
    "browser_ui_failure_retryable",
    "browser_ui_failure_loading_timeout",
    "browser_ui_failure_login_interruption",
    "browser_ui_failure_response_unavailable",
    "browser_ui_failure_insufficient_truth",
    "browser_ui_recovery_same_chat_retry",
    "browser_ui_recovery_resend_same_prompt",
    "browser_ui_recovery_page_reload",
    "browser_ui_recovery_new_chat_handoff",
    "browser_ui_recovery_escalate",
)


__all__ = [
    "_AUTONOMY_BROWSER_ORCHESTRATOR_SPEC_REF",
    "_PROJECT_BROWSER_ASSIMILATED_DECISIONS",
    "_PROJECT_BROWSER_ASSIMILATED_RISK_LEVELS",
    "_PROJECT_BROWSER_ASSIMILATION_RUNTIME_POSTURES",
    "_PROJECT_BROWSER_AUTONOMOUS_ACTION_DUPLICATE_STATUSES",
    "_PROJECT_BROWSER_AUTONOMOUS_ACTION_FINGERPRINT_STATUSES",
    "_PROJECT_BROWSER_AUTONOMOUS_ACTION_IDENTITY_STATUSES",
    "_PROJECT_BROWSER_AUTONOMOUS_ACTION_KINDS",
    "_PROJECT_BROWSER_AUTONOMOUS_ACTION_RECEIPT_KINDS",
    "_PROJECT_BROWSER_AUTONOMOUS_ACTION_RECEIPT_STATUSES",
    "_PROJECT_BROWSER_AUTONOMOUS_CONTINUATION_BLOCK_REASONS",
    "_PROJECT_BROWSER_AUTONOMOUS_CONTINUATION_GATE_STATUSES",
    "_PROJECT_BROWSER_AUTONOMOUS_CONTINUATION_NEXT_ACTIONS",
    "_PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_ACTIONS",
    "_PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_ACTION_SOURCES",
    "_PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_RECEIPT_KINDS",
    "_PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_RECEIPT_STATUSES",
    "_PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_RUNTIME_POSTURES",
    "_PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_STATUSES",
    "_PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_STOP_REASONS",
    "_PROJECT_BROWSER_AUTONOMOUS_DEV_ASSIMILATION_STATUSES",
    "_PROJECT_BROWSER_AUTONOMOUS_DEV_NEXT_ACTIONS",
    "_PROJECT_BROWSER_AUTONOMOUS_DEV_OUTCOMES",
    "_PROJECT_BROWSER_AUTONOMOUS_DEV_RUNTIME_POSTURES",
    "_PROJECT_BROWSER_AUTONOMOUS_DEV_STOP_REASONS",
    "_PROJECT_BROWSER_AUTONOMOUS_DRAFT_RUNTIME_POSTURES",
    "_PROJECT_BROWSER_AUTONOMOUS_DUPLICATE_POLICY_STATUSES",
    "_PROJECT_BROWSER_AUTONOMOUS_DUPLICATE_REASONS",
    "_PROJECT_BROWSER_AUTONOMOUS_EXECUTION_BRIDGE_REASONS",
    "_PROJECT_BROWSER_AUTONOMOUS_EXECUTION_BRIDGE_RUNTIME_POSTURES",
    "_PROJECT_BROWSER_AUTONOMOUS_EXECUTION_BRIDGE_SOURCE_STATUSES",
    "_PROJECT_BROWSER_AUTONOMOUS_EXECUTION_BRIDGE_STATUSES",
    "_PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS",
    "_PROJECT_BROWSER_AUTONOMOUS_GATE_RUNTIME_POSTURES",
    "_PROJECT_BROWSER_AUTONOMOUS_LEDGER_RUNTIME_POSTURES",
    "_PROJECT_BROWSER_AUTONOMOUS_MANUAL_OVERRIDE_REASONS",
    "_PROJECT_BROWSER_AUTONOMOUS_MANUAL_OVERRIDE_STATUSES",
    "_PROJECT_BROWSER_AUTONOMOUS_MD_UPDATE_BLOCK_REASONS",
    "_PROJECT_BROWSER_AUTONOMOUS_MD_UPDATE_COMMAND_DRAFT_STATUSES",
    "_PROJECT_BROWSER_AUTONOMOUS_MD_UPDATE_DRAFT_STATUSES",
    "_PROJECT_BROWSER_AUTONOMOUS_MD_UPDATE_KINDS",
    "_PROJECT_BROWSER_AUTONOMOUS_NEXT_PROMPT_BLOCK_REASONS",
    "_PROJECT_BROWSER_AUTONOMOUS_NEXT_PROMPT_DRAFT_STATUSES",
    "_PROJECT_BROWSER_AUTONOMOUS_NEXT_PROMPT_KINDS",
    "_PROJECT_BROWSER_AUTONOMOUS_NEXT_PROMPT_SCOPES",
    "_PROJECT_BROWSER_AUTONOMOUS_NEXT_PROMPT_SOURCES",
    "_PROJECT_BROWSER_AUTONOMOUS_RETRY_BUDGET_POSTURES",
    "_PROJECT_BROWSER_AUTONOMOUS_RUN_LEDGER_ENTRY_KINDS",
    "_PROJECT_BROWSER_AUTONOMOUS_RUN_LEDGER_ENTRY_STATUSES",
    "_PROJECT_BROWSER_AUTONOMOUS_RUN_LEDGER_STATUSES",
    "_PROJECT_BROWSER_AUTONOMOUS_SAFETY_RUNTIME_POSTURES",
    "_PROJECT_BROWSER_AUTONOMOUS_SAFETY_SWITCH_STATUSES",
    "_PROJECT_BROWSER_AUTONOMOUS_SAFE_STOP_REASONS",
    "_PROJECT_BROWSER_AUTONOMOUS_SAFE_STOP_STATUSES",
    "_PROJECT_BROWSER_CHATGPT_PAGE_STATUSES",
    "_PROJECT_BROWSER_CHAT_ROTATION_NEAR_THRESHOLD",
    "_PROJECT_BROWSER_CHAT_ROTATION_TARGET",
    "_PROJECT_BROWSER_CHAT_TURN_POSTURES",
    "_PROJECT_BROWSER_COMMAND_BLOCK_REASONS",
    "_PROJECT_BROWSER_COMMAND_PRECONDITION_VALUES",
    "_PROJECT_BROWSER_COMMAND_QUEUE_MODES",
    "_PROJECT_BROWSER_COMMAND_QUEUE_STATUSES",
    "_PROJECT_BROWSER_COMMAND_RECEIPT_KINDS",
    "_PROJECT_BROWSER_COMMAND_RECEIPT_RESULTS",
    "_PROJECT_BROWSER_COMMAND_RECEIPT_STATUSES",
    "_PROJECT_BROWSER_COMMAND_RUNTIME_POSTURES",
    "_PROJECT_BROWSER_COMMAND_SOURCES",
    "_PROJECT_BROWSER_COMMAND_TYPES",
    "_PROJECT_BROWSER_CONTEXT_STATUSES",
    "_PROJECT_BROWSER_CONTINUATION_THRESHOLD",
    "_PROJECT_BROWSER_DECISIONS",
    "_PROJECT_BROWSER_DOM_PROBE_BLOCK_REASONS",
    "_PROJECT_BROWSER_DOM_READINESS_STATUSES",
    "_PROJECT_BROWSER_EXECUTION_BLOCK_REASONS",
    "_PROJECT_BROWSER_EXECUTION_HANDOFF_KINDS",
    "_PROJECT_BROWSER_EXECUTION_HANDOFF_STATUSES",
    "_PROJECT_BROWSER_EXECUTION_PREREQUISITE_VALUES",
    "_PROJECT_BROWSER_EXECUTION_RECEIPT_PARSE_KINDS",
    "_PROJECT_BROWSER_EXECUTION_RECEIPT_PARSE_STATUSES",
    "_PROJECT_BROWSER_EXECUTION_RESULT_STATUSES",
    "_PROJECT_BROWSER_EXECUTION_RUNTIME_POSTURES",
    "_PROJECT_BROWSER_EXECUTOR_BLOCK_REASONS",
    "_PROJECT_BROWSER_EXECUTOR_CAPABILITY_POSTURES",
    "_PROJECT_BROWSER_EXECUTOR_CONTRACT_VERSION",
    "_PROJECT_BROWSER_EXECUTOR_INTERFACE_CONTRACT_VERSION",
    "_PROJECT_BROWSER_EXECUTOR_INTERFACE_STATUSES",
    "_PROJECT_BROWSER_EXECUTOR_MODES",
    "_PROJECT_BROWSER_EXECUTOR_RECEIPT_KINDS",
    "_PROJECT_BROWSER_EXECUTOR_RECEIPT_STATUSES",
    "_PROJECT_BROWSER_HANDOFF_COMPILE_STATUSES",
    "_PROJECT_BROWSER_HANDOFF_PAYLOAD_POSTURES",
    "_PROJECT_BROWSER_HANDOFF_RUNTIME_POSTURES",
    "_PROJECT_BROWSER_HANDOFF_SECTION_NAMES",
    "_PROJECT_BROWSER_HANDOFF_SUMMARY_POSTURES",
    "_PROJECT_BROWSER_HANDOFF_TRIGGERS",
    "_PROJECT_BROWSER_JSON_REQUIRED_FIELDS",
    "_PROJECT_BROWSER_LAUNCH_BLOCK_REASONS",
    "_PROJECT_BROWSER_LAUNCH_PREFLIGHT_MODES",
    "_PROJECT_BROWSER_LAUNCH_PREFLIGHT_STATUSES",
    "_PROJECT_BROWSER_LAUNCH_RECEIPT_KINDS",
    "_PROJECT_BROWSER_LAUNCH_RECEIPT_KINDS_RUNTIME",
    "_PROJECT_BROWSER_LAUNCH_RECEIPT_STATUSES",
    "_PROJECT_BROWSER_LAUNCH_RECEIPT_STATUSES_RUNTIME",
    "_PROJECT_BROWSER_LAUNCH_RUNTIME_POSTURES",
    "_PROJECT_BROWSER_LAUNCH_STATUSES",
    "_PROJECT_BROWSER_LOGIN_INTERRUPTION_STATUSES",
    "_PROJECT_BROWSER_LOGIN_PREFLIGHT_POSTURES",
    "_PROJECT_BROWSER_NEXT_ACTION_POSTURES",
    "_PROJECT_BROWSER_ONE_COMMAND_EXECUTOR_RESULTS",
    "_PROJECT_BROWSER_ONE_COMMAND_EXECUTOR_STATUSES",
    "_PROJECT_BROWSER_ONE_COMMAND_RECEIPT_KINDS",
    "_PROJECT_BROWSER_ONE_COMMAND_RECEIPT_STATUSES",
    "_PROJECT_BROWSER_ONE_COMMAND_RUNTIME_POSTURES",
    "_PROJECT_BROWSER_ONE_COMMAND_STOP_REASONS",
    "_PROJECT_BROWSER_PAGE_OPEN_STATUSES",
    "_PROJECT_BROWSER_PLAYWRIGHT_BOUNDARY_STATUSES",
    "_PROJECT_BROWSER_PLAYWRIGHT_IMPORT_POSTURES",
    "_PROJECT_BROWSER_PROMPT_CONTEXT_LEVELS",
    "_PROJECT_BROWSER_PROMPT_FILL_BLOCK_REASONS",
    "_PROJECT_BROWSER_PROMPT_FILL_RECEIPT_KINDS",
    "_PROJECT_BROWSER_PROMPT_FILL_RECEIPT_STATUSES",
    "_PROJECT_BROWSER_PROMPT_FILL_RUNTIME_POSTURES",
    "_PROJECT_BROWSER_PROMPT_FILL_SOURCE_STATUSES",
    "_PROJECT_BROWSER_PROMPT_FILL_STATUSES",
    "_PROJECT_BROWSER_PROMPT_FILL_TARGET_STATUSES",
    "_PROJECT_BROWSER_PROMPT_PAYLOAD_STATUSES",
    "_PROJECT_BROWSER_PROMPT_PAYLOAD_STYLES",
    "_PROJECT_BROWSER_PROMPT_RUNTIME_POSTURES",
    "_PROJECT_BROWSER_PROMPT_SECTION_NAMES",
    "_PROJECT_BROWSER_PROMPT_SEND_BLOCK_REASONS",
    "_PROJECT_BROWSER_PROMPT_SEND_RECEIPT_KINDS",
    "_PROJECT_BROWSER_PROMPT_SEND_RECEIPT_STATUSES",
    "_PROJECT_BROWSER_PROMPT_SEND_RUNTIME_POSTURES",
    "_PROJECT_BROWSER_PROMPT_SEND_STATUSES",
    "_PROJECT_BROWSER_PROMPT_SEND_TARGET_STATUSES",
    "_PROJECT_BROWSER_PROMPT_TOKEN_POSTURES",
    "_PROJECT_BROWSER_PROOF_POSTURES",
    "_PROJECT_BROWSER_REASON_CODES",
    "_PROJECT_BROWSER_REASON_ORDER",
    "_PROJECT_BROWSER_RECOVERY_ACTIONS",
    "_PROJECT_BROWSER_RECOVERY_BLOCK_REASONS",
    "_PROJECT_BROWSER_RECOVERY_REASONS",
    "_PROJECT_BROWSER_RECOVERY_RECEIPT_KINDS",
    "_PROJECT_BROWSER_RECOVERY_RECEIPT_STATUSES",
    "_PROJECT_BROWSER_RECOVERY_RUNTIME_POSTURES",
    "_PROJECT_BROWSER_RECOVERY_STATUSES",
    "_PROJECT_BROWSER_RESPONSE_ASSIMILATION_STATUSES",
    "_PROJECT_BROWSER_RESPONSE_JSON_DECISION_STATUSES",
    "_PROJECT_BROWSER_RESPONSE_JSON_PARSE_STATUSES",
    "_PROJECT_BROWSER_RESPONSE_JSON_SCHEMA_STATUSES",
    "_PROJECT_BROWSER_RESPONSE_PARSE_BLOCK_REASONS",
    "_PROJECT_BROWSER_RESPONSE_PARSE_RUNTIME_POSTURES",
    "_PROJECT_BROWSER_RESPONSE_READ_RECEIPT_KINDS",
    "_PROJECT_BROWSER_RESPONSE_READ_RECEIPT_STATUSES",
    "_PROJECT_BROWSER_RESPONSE_READ_STATUSES",
    "_PROJECT_BROWSER_RESPONSE_RUNTIME_POSTURES",
    "_PROJECT_BROWSER_RESPONSE_STATUSES",
    "_PROJECT_BROWSER_RESPONSE_TEXT_STATUSES",
    "_PROJECT_BROWSER_RESPONSE_WAIT_BLOCK_REASONS",
    "_PROJECT_BROWSER_RESPONSE_WAIT_STATUSES",
    "_PROJECT_BROWSER_RETRY_LIMIT",
    "_PROJECT_BROWSER_RISK_LEVELS",
    "_PROJECT_BROWSER_RUNTIME_BLOCK_REASONS",
    "_PROJECT_BROWSER_SAME_PROMPT_RETRY_POLICIES",
    "_PROJECT_BROWSER_SAME_PROMPT_RETRY_REASONS",
    "_PROJECT_BROWSER_SCORE_POSTURES",
    "_PROJECT_BROWSER_SELECTOR_PROBE_RECEIPT_KINDS",
    "_PROJECT_BROWSER_SELECTOR_PROBE_RECEIPT_STATUSES",
    "_PROJECT_BROWSER_SELECTOR_PROBE_STATUSES",
    "_PROJECT_BROWSER_SELECTOR_REQUIRED_PROBE_TARGETS",
    "_PROJECT_BROWSER_SELECTOR_RESOLVER_STATUSES",
    "_PROJECT_BROWSER_SELECTOR_RUNTIME_POSTURES",
    "_PROJECT_BROWSER_SELECTOR_TARGETS",
    "_PROJECT_BROWSER_SELECTOR_TARGET_STATUSES",
    "_PROJECT_BROWSER_SESSION_CONFIG_STATUSES",
    "_PROJECT_BROWSER_SESSION_MODES",
    "_PROJECT_BROWSER_TASK_ENVELOPE_STATUSES",
    "_PROJECT_BROWSER_TASK_SCHEMA_REF",
    "_PROJECT_BROWSER_TASK_STATUSES",
    "_PROJECT_BROWSER_TASK_TYPES",
    "_PROJECT_BROWSER_UI_FAILURE_STATUSES",
    "_PROJECT_BROWSER_UI_HANDOFF_DEPENDENCY_POSTURES",
    "_PROJECT_BROWSER_UI_READINESS_STATUSES",
    "_PROJECT_BROWSER_UI_RECOVERY_ACTIONS",
    "_PROJECT_BROWSER_UI_RECOVERY_CANDIDATES",
    "_PROJECT_BROWSER_UI_RECOVERY_DECISION_STATUSES",
    "_PROJECT_BROWSER_UI_RECOVERY_REASONS",
    "_PROJECT_BROWSER_UI_RECOVERY_RUNTIME_POSTURES",
    "_PROJECT_BROWSER_UI_RETRY_COUNT_POSTURES",
]

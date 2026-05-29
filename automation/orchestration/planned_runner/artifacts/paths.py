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
    _PROJECT_BROWSER_ASSIMILATION_RUNTIME_POSTURES,
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
    _PROJECT_BROWSER_EXECUTION_RUNTIME_POSTURES,
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
    _PROJECT_BROWSER_HANDOFF_RUNTIME_POSTURES,
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
    _PROJECT_BROWSER_PROMPT_PAYLOAD_STYLES,
    _PROJECT_BROWSER_PROMPT_RUNTIME_POSTURES,
    _PROJECT_BROWSER_PROMPT_SECTION_NAMES,
    _PROJECT_BROWSER_PROMPT_SEND_BLOCK_REASONS,
    _PROJECT_BROWSER_PROMPT_SEND_RECEIPT_KINDS,
    _PROJECT_BROWSER_PROMPT_SEND_RECEIPT_STATUSES,
    _PROJECT_BROWSER_PROMPT_SEND_RUNTIME_POSTURES,
    _PROJECT_BROWSER_PROMPT_SEND_STATUSES,
    _PROJECT_BROWSER_PROMPT_SEND_TARGET_STATUSES,
    _PROJECT_BROWSER_PROMPT_TOKEN_POSTURES,
    _PROJECT_BROWSER_PROOF_POSTURES,
    _PROJECT_BROWSER_REASON_CODES,
    _PROJECT_BROWSER_REASON_ORDER,
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
    _PROJECT_BROWSER_UI_RECOVERY_RUNTIME_POSTURES,
    _PROJECT_BROWSER_UI_RETRY_COUNT_POSTURES,
)
from automation.orchestration.planned_runner.utils import (
    _as_int,
    _as_non_negative_int,
    _as_optional_int,
    _normalize_string_list,
    _normalize_text,
    _read_json_object_if_exists,
    _write_json,
)
from automation.orchestration.planned_runner.git_ops.local_status import (
    _collect_changed_tracked_files,
    _parse_git_status_path,
    _run_git,
)

def _build_local_contract_fix_cycle_coordination_artifacts(
    *,
    one_cycle_controller_dir: Path,
) -> dict[str, Any]:
    def _prompt336_safety_fields() -> dict[str, Any]:
        return {
            "commit_allowed": False,
            "tag_allowed": False,
            "push_pr_merge_enabled": False,
            "targeted_fix_execution_allowed": False,
            "rollback_allowed": False,
            "commit_performed": False,
            "tag_performed": False,
            "push_performed": False,
            "pr_created": False,
            "merge_performed": False,
            "rollback_performed": False,
            "codex_invoked": False,
            "codex_invocation_allowed": False,
        }

    def _as_boolish(value: Any, *, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        text = _normalize_text(value, default="").strip().lower()
        if text in {"1", "true", "yes", "on", "enabled"}:
            return True
        if text in {"0", "false", "no", "off", "disabled"}:
            return False
        return default

    def _read_json_mapping(path: Path) -> tuple[bool, dict[str, Any]]:
        if not path.exists():
            return False, {}
        payload = _read_json_object_if_exists(path)
        if not isinstance(payload, Mapping):
            return True, {}
        return True, dict(payload)

    one_cycle_controller_dir = Path(one_cycle_controller_dir)
    route_intake_path = one_cycle_controller_dir / "local_targeted_contract_fix_route_intake.json"
    prompt_plan_path = one_cycle_controller_dir / "local_targeted_contract_fix_prompt_plan.json"
    prompt_receipt_path = one_cycle_controller_dir / "local_targeted_contract_fix_prompt_receipt.json"
    prompt_path = one_cycle_controller_dir / "local_targeted_contract_fix_prompt.md"
    coordination_state_path = (
        one_cycle_controller_dir / "local_contract_fix_cycle_coordination_state.json"
    )
    coordination_decision_path = (
        one_cycle_controller_dir / "local_contract_fix_cycle_coordination_decision.json"
    )
    coordination_receipt_path = (
        one_cycle_controller_dir / "local_contract_fix_cycle_coordination_receipt.json"
    )
    execution_handoff_path = (
        one_cycle_controller_dir / "local_contract_fix_cycle_execution_handoff.json"
    )

    required_reason = "missing_explicit_allowed_tracked_files_and_conflicting_step_authority"
    allowed_tracked_file = "automation/orchestration/planned_execution_runner.py"

    route_intake_exists, route_intake_payload = _read_json_mapping(route_intake_path)
    prompt_plan_exists, prompt_plan_payload = _read_json_mapping(prompt_plan_path)
    prompt_receipt_exists, prompt_receipt_payload = _read_json_mapping(prompt_receipt_path)

    route_intake_status = _normalize_text(route_intake_payload.get("status"), default="missing")
    contract_fix_signal_source = _normalize_text(
        prompt_plan_payload.get("contract_fix_signal_source"),
        default=_normalize_text(
            route_intake_payload.get("contract_fix_signal_source"),
            default="none",
        ),
    )
    prompt335_plan_status = _normalize_text(prompt_plan_payload.get("status"), default="missing")
    prompt335_plan_blocked_reason = _normalize_text(
        prompt_plan_payload.get("blocked_reason"),
        default="missing_prompt335_prompt_plan_artifact",
    )
    prompt335_receipt_status = _normalize_text(
        prompt_receipt_payload.get("status"),
        default="missing",
    )
    prompt335_receipt_blocked_reason = _normalize_text(
        prompt_receipt_payload.get("blocked_reason"),
        default="missing_prompt335_prompt_receipt_artifact",
    )
    contract_fix_signal_detected = _as_boolish(
        prompt_plan_payload.get("contract_fix_signal_detected"),
        default=False,
    )
    normalized_contract_fix_reason = _normalize_text(
        prompt_plan_payload.get("normalized_contract_fix_reason"),
        default="",
    )

    plan_prompt_path = _normalize_text(
        prompt_plan_payload.get("prompt_path"),
        default=str(prompt_path),
    )
    plan_prompt_exists = _as_boolish(prompt_plan_payload.get("prompt_exists"), default=False)
    plan_prompt_non_empty = _as_boolish(
        prompt_plan_payload.get("prompt_non_empty"),
        default=False,
    )
    plan_next_action = _normalize_text(prompt_plan_payload.get("next_action"), default="")

    receipt_prompt_exists = _as_boolish(prompt_receipt_payload.get("prompt_exists"), default=False)
    receipt_prompt_non_empty = _as_boolish(
        prompt_receipt_payload.get("prompt_non_empty"),
        default=False,
    )
    generated_prompt_sha256 = _normalize_text(
        prompt_receipt_payload.get("generated_prompt_sha256"),
        default="",
    )
    generated_prompt_size_bytes = _as_non_negative_int(
        prompt_receipt_payload.get("generated_prompt_size_bytes"),
        default=0,
    )
    generated_prompt_line_count = _as_non_negative_int(
        prompt_receipt_payload.get("generated_prompt_line_count"),
        default=0,
    )

    prompt_exists = prompt_path.exists()
    prompt_text = ""
    if prompt_exists:
        try:
            prompt_text = prompt_path.read_text(encoding="utf-8")
        except OSError:
            prompt_text = ""
    prompt_non_empty = bool(prompt_text.strip())
    prompt_size_bytes = len(prompt_text.encode("utf-8"))
    prompt_line_count = len(prompt_text.splitlines())
    prompt_sha256 = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest() if prompt_text else ""
    prompt_lines = prompt_text.splitlines()
    prompt_first_80_lines_text = "\n".join(prompt_lines[:80])

    blocked_reason = "none"
    prompt_content_validation_errors: list[str] = []
    prompt_content_validation_status = "not_checked"

    if not route_intake_exists:
        blocked_reason = "missing_prompt335_route_intake_artifact"
    elif not prompt_plan_exists:
        blocked_reason = "missing_prompt335_prompt_plan_artifact"
    elif prompt335_plan_status != "ready":
        blocked_reason = (
            prompt335_plan_blocked_reason
            if prompt335_plan_blocked_reason and prompt335_plan_blocked_reason != "none"
            else "prompt335_plan_status_not_ready"
        )
    elif prompt335_plan_blocked_reason != "none":
        blocked_reason = "prompt335_plan_blocked_reason_not_none"
    elif not contract_fix_signal_detected:
        blocked_reason = "prompt335_contract_fix_signal_not_detected"
    elif not normalized_contract_fix_reason:
        blocked_reason = "prompt335_normalized_contract_fix_reason_missing"
    elif plan_prompt_path != str(prompt_path):
        blocked_reason = "prompt335_prompt_path_mismatch"
    elif not plan_prompt_exists:
        blocked_reason = "prompt335_prompt_exists_false"
    elif not plan_prompt_non_empty:
        blocked_reason = "prompt335_prompt_non_empty_false"
    elif plan_next_action != "execute_targeted_contract_fix_prompt_adapter":
        blocked_reason = "prompt335_plan_next_action_not_execute_targeted_contract_fix_prompt_adapter"
    elif not prompt_receipt_exists:
        blocked_reason = "missing_prompt335_prompt_receipt_artifact"
    elif prompt335_receipt_status != "ready":
        blocked_reason = (
            prompt335_receipt_blocked_reason
            if prompt335_receipt_blocked_reason and prompt335_receipt_blocked_reason != "none"
            else "prompt335_receipt_status_not_ready"
        )
    elif prompt335_receipt_blocked_reason != "none":
        blocked_reason = "prompt335_receipt_blocked_reason_not_none"
    elif not receipt_prompt_exists:
        blocked_reason = "prompt335_receipt_prompt_exists_false"
    elif not receipt_prompt_non_empty:
        blocked_reason = "prompt335_receipt_prompt_non_empty_false"
    elif not generated_prompt_sha256:
        blocked_reason = "prompt335_receipt_generated_prompt_sha256_missing"
    elif generated_prompt_size_bytes <= 0:
        blocked_reason = "prompt335_receipt_generated_prompt_size_bytes_not_positive"
    elif generated_prompt_line_count <= 0:
        blocked_reason = "prompt335_receipt_generated_prompt_line_count_not_positive"
    else:
        prompt_content_validation_status = "passed"
        if not prompt_exists:
            prompt_content_validation_status = "failed"
            prompt_content_validation_errors = ["prompt_file_missing"]
        elif not prompt_non_empty:
            prompt_content_validation_status = "failed"
            prompt_content_validation_errors = ["prompt_file_empty"]
        elif "DO NOT EXECUTE" in prompt_first_80_lines_text.upper():
            prompt_content_validation_status = "failed"
            prompt_content_validation_errors = ["prompt_contains_do_not_execute_in_first_80_lines"]
        elif "Modify only automation/orchestration/planned_execution_runner.py" not in prompt_text:
            prompt_content_validation_status = "failed"
            prompt_content_validation_errors = ["prompt_missing_modify_only_allowed_file_instruction"]
        elif "Do not run tests" not in prompt_text:
            prompt_content_validation_status = "failed"
            prompt_content_validation_errors = ["prompt_missing_do_not_run_tests_instruction"]
        elif "Do not invoke Codex" not in prompt_text:
            prompt_content_validation_status = "failed"
            prompt_content_validation_errors = ["prompt_missing_do_not_invoke_codex_instruction"]
        elif required_reason not in prompt_text:
            prompt_content_validation_status = "failed"
            prompt_content_validation_errors = ["prompt_missing_normalized_contract_fix_reason"]
        elif allowed_tracked_file not in prompt_text:
            prompt_content_validation_status = "failed"
            prompt_content_validation_errors = ["prompt_missing_explicit_allowed_tracked_file_scope"]
        if prompt_content_validation_errors:
            blocked_reason = prompt_content_validation_errors[0]

    status = "ready" if blocked_reason == "none" else "blocked"
    coordination_status = status
    contract_fix_cycle_ready = status == "ready"
    readiness_reason = (
        "targeted_contract_fix_prompt_ready_for_bounded_execution_handoff"
        if status == "ready"
        else "targeted_contract_fix_prompt_not_ready"
    )
    selected_step_id = 3 if status == "ready" else 0
    selected_step_name = "execute_targeted_contract_fix_prompt" if status == "ready" else "none"
    selected_step_operation = (
        "execute_targeted_contract_fix_prompt" if status == "ready" else "none"
    )
    selected_step_authority_source = (
        "prompt335_targeted_contract_fix_prompt_plan" if status == "ready" else "none"
    )
    selected_step_authority_artifact = str(prompt_plan_path)
    explicit_allowed_tracked_files = [allowed_tracked_file]
    mutation_allowed = status == "ready"
    execution_allowed = False
    next_action = (
        "prepare_prompt337_local_daemon_lite_wrapper"
        if status == "ready"
        else "manual_review_targeted_contract_fix_prompt"
    )
    validation_errors = [] if status == "ready" else [blocked_reason]

    handoff_status = "ready" if status == "ready" else "blocked"
    handoff_readiness_reason = (
        "bounded_contract_fix_cycle_ready_for_prompt337"
        if handoff_status == "ready"
        else "bounded_contract_fix_cycle_not_ready"
    )
    handoff_next_action = (
        "prompt337_may_execute_targeted_contract_fix_once"
        if handoff_status == "ready"
        else "manual_review_targeted_contract_fix_prompt"
    )

    safety_fields = _prompt336_safety_fields()
    coordination_payload_base: dict[str, Any] = {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "status": status,
        "coordination_status": coordination_status,
        "blocked_reason": blocked_reason,
        "readiness_reason": readiness_reason,
        "contract_fix_cycle_ready": contract_fix_cycle_ready,
        "prompt335_plan_status": prompt335_plan_status,
        "prompt335_plan_blocked_reason": prompt335_plan_blocked_reason,
        "prompt335_receipt_status": prompt335_receipt_status,
        "prompt335_receipt_blocked_reason": prompt335_receipt_blocked_reason,
        "route_intake_status": route_intake_status,
        "contract_fix_signal_detected": contract_fix_signal_detected,
        "contract_fix_signal_source": contract_fix_signal_source,
        "normalized_contract_fix_reason": normalized_contract_fix_reason,
        "prompt_path": str(prompt_path),
        "prompt_exists": prompt_exists,
        "prompt_non_empty": prompt_non_empty,
        "prompt_sha256": prompt_sha256,
        "prompt_size_bytes": prompt_size_bytes,
        "prompt_line_count": prompt_line_count,
        "prompt_content_validation_status": prompt_content_validation_status,
        "prompt_content_validation_errors": prompt_content_validation_errors,
        "current_cycle": _LOCAL_AUTONOMOUS_CYCLE_V2_CURRENT_CYCLE,
        "max_cycles": _LOCAL_AUTONOMOUS_CYCLE_V2_MAX_CYCLES,
        "selected_step_id": selected_step_id,
        "selected_step_name": selected_step_name,
        "selected_step_operation": selected_step_operation,
        "selected_step_authority_source": selected_step_authority_source,
        "selected_step_authority_artifact": selected_step_authority_artifact,
        "explicit_allowed_tracked_files": explicit_allowed_tracked_files,
        "mutation_allowed": mutation_allowed,
        "execution_allowed": execution_allowed,
        "execution_handoff_status": handoff_status,
        "max_codex_invocations": 1,
        "codex_invocation_count": 0,
        "next_action": next_action,
        "validation_errors": validation_errors,
        **safety_fields,
    }

    coordination_state_payload = {
        **coordination_payload_base,
        "coordination_state_schema_version": (
            _LOCAL_CONTRACT_FIX_CYCLE_COORDINATION_STATE_SCHEMA_VERSION
        ),
    }
    coordination_decision_payload = {
        **coordination_payload_base,
        "coordination_decision_schema_version": (
            _LOCAL_CONTRACT_FIX_CYCLE_COORDINATION_DECISION_SCHEMA_VERSION
        ),
    }
    coordination_receipt_payload = {
        **coordination_payload_base,
        "coordination_receipt_schema_version": (
            _LOCAL_CONTRACT_FIX_CYCLE_COORDINATION_RECEIPT_SCHEMA_VERSION
        ),
    }

    execution_handoff_payload: dict[str, Any] = {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "execution_handoff_schema_version": (
            _LOCAL_CONTRACT_FIX_CYCLE_EXECUTION_HANDOFF_SCHEMA_VERSION
        ),
        "status": handoff_status,
        "handoff_status": handoff_status,
        "blocked_reason": blocked_reason,
        "readiness_reason": handoff_readiness_reason,
        "execution_allowed": False,
        "codex_invocation_allowed": False,
        "prompt_path": str(prompt_path),
        "prompt_exists": prompt_exists,
        "prompt_non_empty": prompt_non_empty,
        "command_argv": [],
        "command_display": "",
        "max_codex_invocations": 1,
        "codex_invocation_count": 0,
        "selected_step_id": selected_step_id,
        "selected_step_name": selected_step_name,
        "selected_step_operation": selected_step_operation,
        "explicit_allowed_tracked_files": explicit_allowed_tracked_files,
        "mutation_allowed": mutation_allowed,
        "next_action": handoff_next_action,
        "validation_errors": [] if handoff_status == "ready" else [blocked_reason],
        **safety_fields,
    }

    try:
        one_cycle_controller_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    try:
        _write_json(coordination_state_path, coordination_state_payload)
    except OSError:
        pass
    try:
        _write_json(coordination_decision_path, coordination_decision_payload)
    except OSError:
        pass
    try:
        _write_json(coordination_receipt_path, coordination_receipt_payload)
    except OSError:
        pass
    try:
        _write_json(execution_handoff_path, execution_handoff_payload)
    except OSError:
        pass

    return {
        "coordination_status": coordination_status,
        "coordination_blocked_reason": blocked_reason,
        "coordination_ready": contract_fix_cycle_ready,
        "coordination_next_action": next_action,
        "coordination_prompt_path": str(prompt_path),
        "coordination_prompt_ready": prompt_exists and prompt_non_empty and status == "ready",
        "coordination_normalized_reason": normalized_contract_fix_reason,
        "coordination_selected_step_name": selected_step_name,
        "handoff_status": handoff_status,
        "handoff_next_action": handoff_next_action,
        "coordination_state_path": str(coordination_state_path),
        "coordination_decision_path": str(coordination_decision_path),
        "coordination_receipt_path": str(coordination_receipt_path),
        "execution_handoff_path": str(execution_handoff_path),
    }

def _build_local_daemon_lite_wrapper_artifacts(
    *,
    one_cycle_controller_dir: Path,
) -> dict[str, Any]:
    def _prompt337_safety_fields() -> dict[str, Any]:
        return {
            "commit_allowed": False,
            "tag_allowed": False,
            "push_pr_merge_enabled": False,
            "targeted_fix_execution_allowed": False,
            "rollback_allowed": False,
            "commit_performed": False,
            "tag_performed": False,
            "push_performed": False,
            "pr_created": False,
            "merge_performed": False,
            "rollback_performed": False,
            "codex_invoked": False,
            "codex_invocation_allowed": False,
            "execution_allowed": False,
        }

    def _as_boolish(value: Any, *, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        text = _normalize_text(value, default="").strip().lower()
        if text in {"1", "true", "yes", "on", "enabled"}:
            return True
        if text in {"0", "false", "no", "off", "disabled"}:
            return False
        return default

    def _read_json_mapping(path: Path) -> tuple[bool, dict[str, Any]]:
        if not path.exists():
            return False, {}
        payload = _read_json_object_if_exists(path)
        if not isinstance(payload, Mapping):
            return True, {}
        return True, dict(payload)

    one_cycle_controller_dir = Path(one_cycle_controller_dir)
    prompt336_coordination_state_path = (
        one_cycle_controller_dir / "local_contract_fix_cycle_coordination_state.json"
    )
    prompt336_coordination_decision_path = (
        one_cycle_controller_dir / "local_contract_fix_cycle_coordination_decision.json"
    )
    prompt336_coordination_receipt_path = (
        one_cycle_controller_dir / "local_contract_fix_cycle_coordination_receipt.json"
    )
    prompt336_handoff_path = (
        one_cycle_controller_dir / "local_contract_fix_cycle_execution_handoff.json"
    )
    prompt_path = one_cycle_controller_dir / "local_targeted_contract_fix_prompt.md"

    daemon_lite_state_path = one_cycle_controller_dir / "local_daemon_lite_wrapper_state.json"
    daemon_lite_plan_path = one_cycle_controller_dir / "local_daemon_lite_wrapper_plan.json"
    daemon_lite_decision_path = one_cycle_controller_dir / "local_daemon_lite_wrapper_decision.json"
    daemon_lite_receipt_path = one_cycle_controller_dir / "local_daemon_lite_wrapper_receipt.json"

    prompt336_handoff_exists, prompt336_handoff_payload = _read_json_mapping(prompt336_handoff_path)
    (
        prompt336_coordination_state_exists,
        prompt336_coordination_state_payload,
    ) = _read_json_mapping(prompt336_coordination_state_path)
    (
        prompt336_coordination_decision_exists,
        prompt336_coordination_decision_payload,
    ) = _read_json_mapping(prompt336_coordination_decision_path)
    (
        prompt336_coordination_receipt_exists,
        prompt336_coordination_receipt_payload,
    ) = _read_json_mapping(prompt336_coordination_receipt_path)

    prompt336_handoff_status = _normalize_text(
        prompt336_handoff_payload.get("status"),
        default="missing",
    )
    prompt336_handoff_handoff_status = _normalize_text(
        prompt336_handoff_payload.get("handoff_status"),
        default=prompt336_handoff_status,
    )
    prompt336_handoff_blocked_reason = _normalize_text(
        prompt336_handoff_payload.get("blocked_reason"),
        default=(
            "missing_local_contract_fix_cycle_execution_handoff"
            if not prompt336_handoff_exists
            else "prompt336_handoff_blocked_or_invalid"
        ),
    )
    prompt336_handoff_readiness_reason = _normalize_text(
        prompt336_handoff_payload.get("readiness_reason"),
        default="",
    )
    prompt336_handoff_next_action = _normalize_text(
        prompt336_handoff_payload.get("next_action"),
        default="manual_review_contract_fix_cycle_handoff",
    )
    prompt336_selected_step_id = _as_int(
        prompt336_handoff_payload.get("selected_step_id"),
        default=0,
    )
    prompt336_selected_step_name = _normalize_text(
        prompt336_handoff_payload.get("selected_step_name"),
        default="none",
    )
    prompt336_selected_step_operation = _normalize_text(
        prompt336_handoff_payload.get("selected_step_operation"),
        default="none",
    )
    prompt336_prompt_path = _normalize_text(
        prompt336_handoff_payload.get("prompt_path"),
        default=str(prompt_path),
    )
    prompt336_prompt_exists = _as_boolish(
        prompt336_handoff_payload.get("prompt_exists"),
        default=False,
    )
    prompt336_prompt_non_empty = _as_boolish(
        prompt336_handoff_payload.get("prompt_non_empty"),
        default=False,
    )
    prompt336_explicit_allowed_tracked_files = _normalize_string_list(
        prompt336_handoff_payload.get("explicit_allowed_tracked_files")
    )
    prompt336_mutation_allowed = _as_boolish(
        prompt336_handoff_payload.get("mutation_allowed"),
        default=False,
    )
    prompt336_execution_allowed = _as_boolish(
        prompt336_handoff_payload.get("execution_allowed"),
        default=False,
    )
    prompt336_codex_invocation_allowed = _as_boolish(
        prompt336_handoff_payload.get("codex_invocation_allowed"),
        default=False,
    )
    prompt336_command_argv_raw = prompt336_handoff_payload.get("command_argv")
    prompt336_command_argv: list[str] = []
    if isinstance(prompt336_command_argv_raw, list):
        prompt336_command_argv = [
            _normalize_text(item, default="") for item in prompt336_command_argv_raw
        ]
    prompt336_command_display = _normalize_text(
        prompt336_handoff_payload.get("command_display"),
        default="",
    )
    prompt336_max_codex_invocations = _as_non_negative_int(
        prompt336_handoff_payload.get("max_codex_invocations"),
        default=0,
    )
    prompt336_codex_invocation_count = _as_non_negative_int(
        prompt336_handoff_payload.get("codex_invocation_count"),
        default=0,
    )

    prompt336_coordination_status = _normalize_text(
        prompt336_coordination_state_payload.get("coordination_status"),
        default=_normalize_text(
            prompt336_coordination_decision_payload.get("coordination_status"),
            default=_normalize_text(
                prompt336_coordination_receipt_payload.get("coordination_status"),
                default="missing",
            ),
        ),
    )
    prompt336_coordination_blocked_reason = _normalize_text(
        prompt336_coordination_state_payload.get("blocked_reason"),
        default=_normalize_text(
            prompt336_coordination_decision_payload.get("blocked_reason"),
            default=_normalize_text(
                prompt336_coordination_receipt_payload.get("blocked_reason"),
                default=(
                    "missing_local_contract_fix_cycle_coordination_state"
                    if not prompt336_coordination_state_exists
                    else "none"
                ),
            ),
        ),
    )
    prompt336_contract_fix_cycle_ready = _as_boolish(
        prompt336_coordination_state_payload.get("contract_fix_cycle_ready"),
        default=_as_boolish(
            prompt336_coordination_decision_payload.get("contract_fix_cycle_ready"),
            default=_as_boolish(
                prompt336_coordination_receipt_payload.get("contract_fix_cycle_ready"),
                default=False,
            ),
        ),
    )

    blocked_reason = "none"
    expected_prompt_path = str(prompt_path)
    expected_allowed_tracked_files = ["automation/orchestration/planned_execution_runner.py"]

    if not prompt336_handoff_exists:
        blocked_reason = "missing_prompt336_execution_handoff_artifact"
    elif prompt336_handoff_status != "ready":
        blocked_reason = "prompt336_handoff_status_not_ready"
    elif prompt336_handoff_handoff_status != "ready":
        blocked_reason = "prompt336_handoff_handoff_status_not_ready"
    elif prompt336_handoff_blocked_reason != "none":
        blocked_reason = "prompt336_handoff_blocked_reason_not_none"
    elif prompt336_handoff_readiness_reason != "bounded_contract_fix_cycle_ready_for_prompt337":
        blocked_reason = "prompt336_handoff_readiness_reason_not_ready_for_prompt337"
    elif prompt336_handoff_next_action != "prompt337_may_execute_targeted_contract_fix_once":
        blocked_reason = "prompt336_handoff_next_action_not_prompt337_single_execution"
    elif prompt336_selected_step_id != 3:
        blocked_reason = "prompt336_handoff_selected_step_id_not_3"
    elif prompt336_selected_step_name != "execute_targeted_contract_fix_prompt":
        blocked_reason = "prompt336_handoff_selected_step_name_not_execute_targeted_contract_fix_prompt"
    elif prompt336_selected_step_operation != "execute_targeted_contract_fix_prompt":
        blocked_reason = (
            "prompt336_handoff_selected_step_operation_not_execute_targeted_contract_fix_prompt"
        )
    elif prompt336_prompt_path != expected_prompt_path:
        blocked_reason = "prompt336_handoff_prompt_path_mismatch"
    elif not prompt336_prompt_exists:
        blocked_reason = "prompt336_handoff_prompt_exists_false"
    elif not prompt336_prompt_non_empty:
        blocked_reason = "prompt336_handoff_prompt_non_empty_false"
    elif prompt336_explicit_allowed_tracked_files != expected_allowed_tracked_files:
        blocked_reason = "prompt336_handoff_explicit_allowed_tracked_files_mismatch"
    elif not prompt336_mutation_allowed:
        blocked_reason = "prompt336_handoff_mutation_allowed_false"
    elif prompt336_execution_allowed:
        blocked_reason = "prompt336_handoff_execution_allowed_true"
    elif prompt336_codex_invocation_allowed:
        blocked_reason = "prompt336_handoff_codex_invocation_allowed_true"
    elif prompt336_command_argv:
        blocked_reason = "prompt336_handoff_command_argv_not_empty"
    elif prompt336_command_display:
        blocked_reason = "prompt336_handoff_command_display_not_empty"
    elif prompt336_max_codex_invocations != 1:
        blocked_reason = "prompt336_handoff_max_codex_invocations_not_1"
    elif prompt336_codex_invocation_count != 0:
        blocked_reason = "prompt336_handoff_codex_invocation_count_not_0"

    supporting_expectations: tuple[tuple[str, Any, str], ...] = (
        ("status", "ready", "status_not_ready"),
        ("coordination_status", "ready", "coordination_status_not_ready"),
        ("contract_fix_cycle_ready", True, "contract_fix_cycle_ready_not_true"),
        (
            "selected_step_operation",
            "execute_targeted_contract_fix_prompt",
            "selected_step_operation_not_execute_targeted_contract_fix_prompt",
        ),
        ("prompt_exists", True, "prompt_exists_not_true"),
        ("prompt_non_empty", True, "prompt_non_empty_not_true"),
        ("execution_allowed", False, "execution_allowed_not_false"),
        ("codex_invocation_allowed", False, "codex_invocation_allowed_not_false"),
    )
    supporting_artifacts: tuple[tuple[str, bool, dict[str, Any]], ...] = (
        ("coordination_state", prompt336_coordination_state_exists, prompt336_coordination_state_payload),
        (
            "coordination_decision",
            prompt336_coordination_decision_exists,
            prompt336_coordination_decision_payload,
        ),
        (
            "coordination_receipt",
            prompt336_coordination_receipt_exists,
            prompt336_coordination_receipt_payload,
        ),
    )
    if blocked_reason == "none":
        for artifact_name, artifact_exists, artifact_payload in supporting_artifacts:
            if not artifact_exists:
                continue
            for key, expected_value, error_suffix in supporting_expectations:
                if key not in artifact_payload:
                    continue
                actual_value = artifact_payload.get(key)
                if isinstance(expected_value, bool):
                    if _as_boolish(actual_value, default=not expected_value) != expected_value:
                        blocked_reason = f"prompt336_{artifact_name}_{error_suffix}"
                        break
                else:
                    if _normalize_text(actual_value, default="") != expected_value:
                        blocked_reason = f"prompt336_{artifact_name}_{error_suffix}"
                        break
            if blocked_reason != "none":
                break

    status = "ready" if blocked_reason == "none" else "blocked"
    daemon_lite_status = status
    wrapper_plan_status = status
    daemon_lite_ready = status == "ready"
    readiness_reason = (
        "prompt336_handoff_ready_for_bounded_daemon_lite_wrapper"
        if daemon_lite_ready
        else "prompt336_handoff_not_ready_for_bounded_daemon_lite_wrapper"
    )

    selected_step_id = 3 if daemon_lite_ready else prompt336_selected_step_id
    selected_step_name = (
        "execute_targeted_contract_fix_prompt"
        if daemon_lite_ready
        else (
            prompt336_selected_step_name
            if prompt336_selected_step_name
            else "none"
        )
    )
    selected_step_operation = (
        "execute_targeted_contract_fix_prompt"
        if daemon_lite_ready
        else (
            prompt336_selected_step_operation
            if prompt336_selected_step_operation
            else "none"
        )
    )
    mutation_allowed = prompt336_mutation_allowed
    wrapper_next_action = (
        "manual_execute_bounded_targeted_contract_fix_adapter"
        if daemon_lite_ready
        else "manual_review_contract_fix_cycle_handoff"
    )
    next_action = wrapper_next_action
    decision = (
        "prepare_manual_bounded_targeted_contract_fix_execution"
        if daemon_lite_ready
        else "manual_review_contract_fix_cycle_handoff"
    )
    decision_reason = (
        "prompt336_handoff_ready_and_daemon_lite_wrapper_bounded"
        if daemon_lite_ready
        else blocked_reason
    )
    validation_errors = [] if daemon_lite_ready else [blocked_reason]

    safety_fields = _prompt337_safety_fields()
    state_payload: dict[str, Any] = {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "daemon_lite_state_schema_version": _LOCAL_DAEMON_LITE_WRAPPER_STATE_SCHEMA_VERSION,
        "status": status,
        "daemon_lite_status": daemon_lite_status,
        "wrapper_plan_status": wrapper_plan_status,
        "blocked_reason": blocked_reason,
        "readiness_reason": readiness_reason,
        "daemon_lite_ready": daemon_lite_ready,
        "prompt336_handoff_status": prompt336_handoff_handoff_status,
        "prompt336_handoff_blocked_reason": prompt336_handoff_blocked_reason,
        "prompt336_handoff_next_action": prompt336_handoff_next_action,
        "prompt336_coordination_status": prompt336_coordination_status,
        "prompt336_coordination_blocked_reason": prompt336_coordination_blocked_reason,
        "prompt336_contract_fix_cycle_ready": prompt336_contract_fix_cycle_ready,
        "selected_step_id": selected_step_id,
        "selected_step_name": selected_step_name,
        "selected_step_operation": selected_step_operation,
        "prompt_path": prompt336_prompt_path or expected_prompt_path,
        "prompt_exists": prompt336_prompt_exists,
        "prompt_non_empty": prompt336_prompt_non_empty,
        "explicit_allowed_tracked_files": prompt336_explicit_allowed_tracked_files,
        "mutation_allowed": mutation_allowed,
        "execution_allowed": False,
        "codex_invocation_allowed": False,
        "max_wrapper_cycles": 1,
        "current_wrapper_cycle": 0,
        "max_codex_invocations_per_cycle": 1,
        "total_codex_invocation_budget": 1,
        "bounded_execution": True,
        "unbounded_loop_allowed": False,
        "retry_allowed": False,
        "sleep_poll_allowed": False,
        "next_action": next_action,
        "validation_errors": validation_errors,
        **safety_fields,
    }

    plan_payload: dict[str, Any] = {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "daemon_lite_plan_schema_version": _LOCAL_DAEMON_LITE_WRAPPER_PLAN_SCHEMA_VERSION,
        "status": status,
        "daemon_lite_status": daemon_lite_status,
        "wrapper_plan_status": wrapper_plan_status,
        "blocked_reason": blocked_reason,
        "readiness_reason": readiness_reason,
        "daemon_lite_ready": daemon_lite_ready,
        "daemon_mode": "daemon_lite",
        "daemon_is_real_background_process": False,
        "background_execution_enabled": False,
        "scheduler_enabled": False,
        "watcher_enabled": False,
        "max_wrapper_cycles": 1,
        "current_wrapper_cycle": 0,
        "max_codex_invocations_per_cycle": 1,
        "total_codex_invocation_budget": 1,
        "bounded_execution": True,
        "unbounded_loop_allowed": False,
        "retry_allowed": False,
        "sleep_poll_allowed": False,
        "selected_step_id": selected_step_id,
        "selected_step_name": selected_step_name,
        "selected_step_operation": selected_step_operation,
        "selected_step_authority_source": "prompt336_contract_fix_cycle_execution_handoff",
        "selected_step_authority_artifact": str(prompt336_handoff_path),
        "prompt_path": prompt336_prompt_path or expected_prompt_path,
        "prompt_exists": prompt336_prompt_exists,
        "prompt_non_empty": prompt336_prompt_non_empty,
        "explicit_allowed_tracked_files": prompt336_explicit_allowed_tracked_files,
        "mutation_allowed": mutation_allowed,
        "execution_allowed": False,
        "codex_invocation_allowed": False,
        "command_argv": [],
        "command_display": "",
        "wrapper_next_action": wrapper_next_action,
        "next_action": next_action,
        "validation_errors": validation_errors,
        **safety_fields,
    }

    decision_payload: dict[str, Any] = {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "daemon_lite_decision_schema_version": _LOCAL_DAEMON_LITE_WRAPPER_DECISION_SCHEMA_VERSION,
        "status": status,
        "daemon_lite_status": daemon_lite_status,
        "wrapper_plan_status": wrapper_plan_status,
        "blocked_reason": blocked_reason,
        "daemon_lite_ready": daemon_lite_ready,
        "decision": decision,
        "decision_reason": decision_reason,
        "selected_step_id": selected_step_id,
        "selected_step_name": selected_step_name,
        "selected_step_operation": selected_step_operation,
        "wrapper_next_action": wrapper_next_action,
        "next_action": next_action,
        "execution_allowed": False,
        "codex_invocation_allowed": False,
        "max_wrapper_cycles": 1,
        "total_codex_invocation_budget": 1,
        "validation_errors": validation_errors,
        **safety_fields,
    }

    receipt_payload: dict[str, Any] = {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "daemon_lite_receipt_schema_version": _LOCAL_DAEMON_LITE_WRAPPER_RECEIPT_SCHEMA_VERSION,
        "status": status,
        "daemon_lite_status": daemon_lite_status,
        "wrapper_plan_status": wrapper_plan_status,
        "blocked_reason": blocked_reason,
        "readiness_reason": readiness_reason,
        "daemon_lite_ready": daemon_lite_ready,
        "state_path": str(daemon_lite_state_path),
        "plan_path": str(daemon_lite_plan_path),
        "decision_path": str(daemon_lite_decision_path),
        "prompt336_handoff_path": str(prompt336_handoff_path),
        "selected_step_id": selected_step_id,
        "selected_step_name": selected_step_name,
        "selected_step_operation": selected_step_operation,
        "prompt_path": prompt336_prompt_path or expected_prompt_path,
        "prompt_exists": prompt336_prompt_exists,
        "prompt_non_empty": prompt336_prompt_non_empty,
        "wrapper_next_action": wrapper_next_action,
        "next_action": next_action,
        "validation_errors": validation_errors,
        **safety_fields,
    }

    try:
        one_cycle_controller_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    try:
        _write_json(daemon_lite_state_path, state_payload)
    except OSError:
        pass
    try:
        _write_json(daemon_lite_plan_path, plan_payload)
    except OSError:
        pass
    try:
        _write_json(daemon_lite_decision_path, decision_payload)
    except OSError:
        pass
    try:
        _write_json(daemon_lite_receipt_path, receipt_payload)
    except OSError:
        pass

    return {
        "local_daemon_lite_wrapper_status": status,
        "local_daemon_lite_wrapper_blocked_reason": blocked_reason,
        "local_daemon_lite_wrapper_ready": daemon_lite_ready,
        "local_daemon_lite_wrapper_decision": decision,
        "local_daemon_lite_wrapper_next_action": next_action,
        "local_daemon_lite_wrapper_selected_step_name": selected_step_name,
        "local_daemon_lite_wrapper_prompt_path": prompt336_prompt_path or expected_prompt_path,
        "local_daemon_lite_wrapper_bounded_execution": True,
        "local_daemon_lite_wrapper_total_codex_invocation_budget": 1,
        "local_daemon_lite_wrapper_state_path": str(daemon_lite_state_path),
        "local_daemon_lite_wrapper_plan_path": str(daemon_lite_plan_path),
        "local_daemon_lite_wrapper_decision_path": str(daemon_lite_decision_path),
        "local_daemon_lite_wrapper_receipt_path": str(daemon_lite_receipt_path),
    }

def _build_local_targeted_contract_fix_execution_artifacts(
    *,
    execution_repo_path: str,
    one_cycle_controller_dir: Path,
) -> dict[str, Any]:
    def _as_boolish(value: Any, *, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        text = _normalize_text(value, default="").strip().lower()
        if text in {"1", "true", "yes", "on", "enabled"}:
            return True
        if text in {"0", "false", "no", "off", "disabled"}:
            return False
        return default

    def _read_json_mapping(path: Path) -> tuple[bool, bool, dict[str, Any]]:
        if not path.exists():
            return False, False, {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return True, False, {}
        if not isinstance(payload, Mapping):
            return True, False, {}
        return True, True, dict(payload)

    def _collect_changed_tracked_files(repo_path: str) -> tuple[bool, list[str]]:
        try:
            status_short_cmd = _run_git(
                repo_path,
                ["status", "--short", "--untracked-files=no"],
                timeout_seconds=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False, []
        if status_short_cmd.returncode != 0:
            return False, []
        changed = sorted(
            {
                _parse_git_status_path(line)
                for line in (status_short_cmd.stdout or "").splitlines()
                if line.strip() and _parse_git_status_path(line)
            }
        )
        return True, changed

    def _contains_blocked(text: str) -> bool:
        return "BLOCKED" in _normalize_text(text, default="").upper()

    def _get_file_size(path: Path) -> int:
        try:
            return _as_non_negative_int(path.stat().st_size, default=0)
        except OSError:
            return 0

    one_cycle_controller_dir = Path(one_cycle_controller_dir)
    prompt337_plan_path = one_cycle_controller_dir / "local_daemon_lite_wrapper_plan.json"
    prompt337_decision_path = one_cycle_controller_dir / "local_daemon_lite_wrapper_decision.json"
    prompt337_receipt_path = one_cycle_controller_dir / "local_daemon_lite_wrapper_receipt.json"
    prompt336_handoff_path = one_cycle_controller_dir / "local_contract_fix_cycle_execution_handoff.json"
    prompt335_prompt_path = one_cycle_controller_dir / "local_targeted_contract_fix_prompt.md"
    prompt335_plan_path = one_cycle_controller_dir / "local_targeted_contract_fix_prompt_plan.json"
    prompt335_receipt_path = one_cycle_controller_dir / "local_targeted_contract_fix_prompt_receipt.json"

    execution_state_path = one_cycle_controller_dir / "local_targeted_contract_fix_execution_state.json"
    execution_result_path = one_cycle_controller_dir / "local_targeted_contract_fix_execution_result.json"
    execution_receipt_path = (
        one_cycle_controller_dir / "local_targeted_contract_fix_execution_receipt.json"
    )
    stdout_path = one_cycle_controller_dir / "local_targeted_contract_fix_execution_stdout.txt"
    stderr_path = one_cycle_controller_dir / "local_targeted_contract_fix_execution_stderr.txt"

    expected_prompt_path = str(prompt335_prompt_path)
    expected_allowed_tracked_files = ["automation/orchestration/planned_execution_runner.py"]
    expected_command_argv = list(_LOCAL_TARGETED_CONTRACT_FIX_EXECUTION_COMMAND)
    command_display = " ".join(expected_command_argv)

    (
        prompt337_plan_exists,
        prompt337_plan_valid,
        prompt337_plan_payload,
    ) = _read_json_mapping(prompt337_plan_path)
    (
        prompt337_decision_exists,
        prompt337_decision_valid,
        prompt337_decision_payload,
    ) = _read_json_mapping(prompt337_decision_path)
    (
        prompt337_receipt_exists,
        prompt337_receipt_valid,
        prompt337_receipt_payload,
    ) = _read_json_mapping(prompt337_receipt_path)
    (
        prompt336_handoff_exists,
        prompt336_handoff_valid,
        prompt336_handoff_payload,
    ) = _read_json_mapping(prompt336_handoff_path)
    (
        prompt335_plan_exists,
        prompt335_plan_valid,
        prompt335_plan_payload,
    ) = _read_json_mapping(prompt335_plan_path)
    (
        prompt335_receipt_exists,
        prompt335_receipt_valid,
        prompt335_receipt_payload,
    ) = _read_json_mapping(prompt335_receipt_path)

    prompt_exists = prompt335_prompt_path.exists()
    prompt_text = ""
    if prompt_exists:
        try:
            prompt_text = prompt335_prompt_path.read_text(encoding="utf-8")
        except OSError:
            prompt_text = ""
    prompt_non_empty = bool(prompt_text.strip())
    prompt_sha256 = (
        hashlib.sha256(prompt_text.encode("utf-8")).hexdigest() if prompt_text else ""
    )
    prompt_size_bytes = len(prompt_text.encode("utf-8")) if prompt_text else 0
    prompt_line_count = len(prompt_text.splitlines()) if prompt_text else 0
    prompt_first_80_lines = "\n".join(prompt_text.splitlines()[:80])

    selected_step_id = _as_int(prompt337_plan_payload.get("selected_step_id"), default=0)
    selected_step_name = _normalize_text(
        prompt337_plan_payload.get("selected_step_name"),
        default="none",
    )
    selected_step_operation = _normalize_text(
        prompt337_plan_payload.get("selected_step_operation"),
        default="none",
    )
    selected_step_authority_source = _normalize_text(
        prompt337_plan_payload.get("selected_step_authority_source"),
        default="none",
    )
    explicit_allowed_tracked_files = _normalize_string_list(
        prompt337_plan_payload.get("explicit_allowed_tracked_files")
    )
    mutation_allowed = _as_boolish(prompt337_plan_payload.get("mutation_allowed"), default=False)

    readiness_errors: list[str] = []
    blocked_reason = "none"

    if not prompt337_plan_exists:
        readiness_errors.append("missing_prompt337_wrapper_plan_artifact")
    elif not prompt337_plan_valid:
        readiness_errors.append("invalid_prompt337_wrapper_plan_artifact")
    if not prompt337_decision_exists:
        readiness_errors.append("missing_prompt337_wrapper_decision_artifact")
    elif not prompt337_decision_valid:
        readiness_errors.append("invalid_prompt337_wrapper_decision_artifact")
    if not prompt337_receipt_exists:
        readiness_errors.append("missing_prompt337_wrapper_receipt_artifact")
    elif not prompt337_receipt_valid:
        readiness_errors.append("invalid_prompt337_wrapper_receipt_artifact")
    if not prompt336_handoff_exists:
        readiness_errors.append("missing_prompt336_execution_handoff_artifact")
    elif not prompt336_handoff_valid:
        readiness_errors.append("invalid_prompt336_execution_handoff_artifact")
    if not prompt335_plan_exists:
        readiness_errors.append("missing_prompt335_prompt_plan_artifact")
    elif not prompt335_plan_valid:
        readiness_errors.append("invalid_prompt335_prompt_plan_artifact")
    if not prompt335_receipt_exists:
        readiness_errors.append("missing_prompt335_prompt_receipt_artifact")
    elif not prompt335_receipt_valid:
        readiness_errors.append("invalid_prompt335_prompt_receipt_artifact")
    if not prompt_exists:
        readiness_errors.append("missing_prompt335_prompt_artifact")

    prompt337_plan_status = _normalize_text(prompt337_plan_payload.get("status"), default="")
    prompt337_plan_daemon_lite_status = _normalize_text(
        prompt337_plan_payload.get("daemon_lite_status"),
        default="",
    )
    prompt337_plan_blocked_reason = _normalize_text(
        prompt337_plan_payload.get("blocked_reason"),
        default="",
    )
    prompt337_plan_daemon_lite_ready = _as_boolish(
        prompt337_plan_payload.get("daemon_lite_ready"),
        default=False,
    )
    prompt337_plan_daemon_mode = _normalize_text(
        prompt337_plan_payload.get("daemon_mode"),
        default="",
    )
    prompt337_plan_daemon_is_background = _as_boolish(
        prompt337_plan_payload.get("daemon_is_real_background_process"),
        default=True,
    )
    prompt337_plan_background_execution_enabled = _as_boolish(
        prompt337_plan_payload.get("background_execution_enabled"),
        default=True,
    )
    prompt337_plan_scheduler_enabled = _as_boolish(
        prompt337_plan_payload.get("scheduler_enabled"),
        default=True,
    )
    prompt337_plan_watcher_enabled = _as_boolish(
        prompt337_plan_payload.get("watcher_enabled"),
        default=True,
    )
    prompt337_plan_max_wrapper_cycles = _as_non_negative_int(
        prompt337_plan_payload.get("max_wrapper_cycles"),
        default=0,
    )
    prompt337_plan_total_codex_invocation_budget = _as_non_negative_int(
        prompt337_plan_payload.get("total_codex_invocation_budget"),
        default=0,
    )
    prompt337_plan_bounded_execution = _as_boolish(
        prompt337_plan_payload.get("bounded_execution"),
        default=False,
    )
    prompt337_plan_unbounded_loop_allowed = _as_boolish(
        prompt337_plan_payload.get("unbounded_loop_allowed"),
        default=True,
    )
    prompt337_plan_retry_allowed = _as_boolish(
        prompt337_plan_payload.get("retry_allowed"),
        default=True,
    )
    prompt337_plan_sleep_poll_allowed = _as_boolish(
        prompt337_plan_payload.get("sleep_poll_allowed"),
        default=True,
    )
    prompt337_plan_selected_step_id = _as_int(
        prompt337_plan_payload.get("selected_step_id"),
        default=0,
    )
    prompt337_plan_selected_step_name = _normalize_text(
        prompt337_plan_payload.get("selected_step_name"),
        default="",
    )
    prompt337_plan_selected_step_operation = _normalize_text(
        prompt337_plan_payload.get("selected_step_operation"),
        default="",
    )
    prompt337_plan_selected_step_authority_source = _normalize_text(
        prompt337_plan_payload.get("selected_step_authority_source"),
        default="",
    )
    prompt337_plan_prompt_path = _normalize_text(
        prompt337_plan_payload.get("prompt_path"),
        default="",
    )
    prompt337_plan_prompt_exists = _as_boolish(
        prompt337_plan_payload.get("prompt_exists"),
        default=False,
    )
    prompt337_plan_prompt_non_empty = _as_boolish(
        prompt337_plan_payload.get("prompt_non_empty"),
        default=False,
    )
    prompt337_plan_execution_allowed = _as_boolish(
        prompt337_plan_payload.get("execution_allowed"),
        default=True,
    )
    prompt337_plan_codex_invocation_allowed = _as_boolish(
        prompt337_plan_payload.get("codex_invocation_allowed"),
        default=True,
    )
    prompt337_plan_command_argv = _normalize_string_list(
        prompt337_plan_payload.get("command_argv"),
        sort_items=False,
    )
    prompt337_plan_command_display = _normalize_text(
        prompt337_plan_payload.get("command_display"),
        default="",
    )
    prompt337_plan_next_action = _normalize_text(
        prompt337_plan_payload.get("next_action"),
        default="",
    )
    prompt337_plan_wrapper_next_action = _normalize_text(
        prompt337_plan_payload.get("wrapper_next_action"),
        default="",
    )

    prompt337_decision_status = _normalize_text(
        prompt337_decision_payload.get("status"),
        default="",
    )
    prompt337_decision_blocked_reason = _normalize_text(
        prompt337_decision_payload.get("blocked_reason"),
        default="",
    )
    prompt337_decision_decision = _normalize_text(
        prompt337_decision_payload.get("decision"),
        default="",
    )
    prompt337_decision_daemon_lite_ready = _as_boolish(
        prompt337_decision_payload.get("daemon_lite_ready"),
        default=False,
    )
    prompt337_decision_selected_step_operation = _normalize_text(
        prompt337_decision_payload.get("selected_step_operation"),
        default="",
    )
    prompt337_decision_execution_allowed = _as_boolish(
        prompt337_decision_payload.get("execution_allowed"),
        default=True,
    )
    prompt337_decision_codex_invocation_allowed = _as_boolish(
        prompt337_decision_payload.get("codex_invocation_allowed"),
        default=True,
    )

    prompt337_receipt_status = _normalize_text(
        prompt337_receipt_payload.get("status"),
        default="",
    )
    prompt337_receipt_blocked_reason = _normalize_text(
        prompt337_receipt_payload.get("blocked_reason"),
        default="",
    )
    prompt337_receipt_daemon_lite_ready = _as_boolish(
        prompt337_receipt_payload.get("daemon_lite_ready"),
        default=False,
    )
    prompt337_receipt_selected_step_operation = _normalize_text(
        prompt337_receipt_payload.get("selected_step_operation"),
        default="",
    )
    prompt337_receipt_prompt_exists = _as_boolish(
        prompt337_receipt_payload.get("prompt_exists"),
        default=False,
    )
    prompt337_receipt_prompt_non_empty = _as_boolish(
        prompt337_receipt_payload.get("prompt_non_empty"),
        default=False,
    )

    prompt336_handoff_status = _normalize_text(
        prompt336_handoff_payload.get("status"),
        default="",
    )
    prompt336_handoff_handoff_status = _normalize_text(
        prompt336_handoff_payload.get("handoff_status"),
        default=prompt336_handoff_status,
    )
    prompt336_handoff_blocked_reason = _normalize_text(
        prompt336_handoff_payload.get("blocked_reason"),
        default="",
    )
    prompt336_handoff_next_action = _normalize_text(
        prompt336_handoff_payload.get("next_action"),
        default="",
    )
    prompt336_handoff_selected_step_operation = _normalize_text(
        prompt336_handoff_payload.get("selected_step_operation"),
        default="",
    )
    prompt336_handoff_explicit_allowed_tracked_files = _normalize_string_list(
        prompt336_handoff_payload.get("explicit_allowed_tracked_files")
    )
    prompt336_handoff_mutation_allowed = _as_boolish(
        prompt336_handoff_payload.get("mutation_allowed"),
        default=False,
    )
    prompt336_handoff_execution_allowed = _as_boolish(
        prompt336_handoff_payload.get("execution_allowed"),
        default=True,
    )
    prompt336_handoff_codex_invocation_allowed = _as_boolish(
        prompt336_handoff_payload.get("codex_invocation_allowed"),
        default=True,
    )
    prompt336_handoff_command_argv = _normalize_string_list(
        prompt336_handoff_payload.get("command_argv"),
        sort_items=False,
    )
    prompt336_handoff_command_display = _normalize_text(
        prompt336_handoff_payload.get("command_display"),
        default="",
    )
    prompt336_handoff_max_codex_invocations = _as_non_negative_int(
        prompt336_handoff_payload.get("max_codex_invocations"),
        default=0,
    )
    prompt336_handoff_codex_invocation_count = _as_non_negative_int(
        prompt336_handoff_payload.get("codex_invocation_count"),
        default=0,
    )

    prompt335_plan_status = _normalize_text(prompt335_plan_payload.get("status"), default="")
    prompt335_plan_blocked_reason = _normalize_text(
        prompt335_plan_payload.get("blocked_reason"),
        default="",
    )
    prompt335_receipt_status = _normalize_text(
        prompt335_receipt_payload.get("status"),
        default="",
    )
    prompt335_receipt_blocked_reason = _normalize_text(
        prompt335_receipt_payload.get("blocked_reason"),
        default="",
    )
    prompt335_receipt_sha = _normalize_text(
        prompt335_receipt_payload.get("generated_prompt_sha256"),
        default="",
    )
    prompt335_receipt_size = _as_non_negative_int(
        prompt335_receipt_payload.get("generated_prompt_size_bytes"),
        default=0,
    )
    prompt335_receipt_lines = _as_non_negative_int(
        prompt335_receipt_payload.get("generated_prompt_line_count"),
        default=0,
    )

    if not readiness_errors:
        if prompt337_plan_status != "ready":
            blocked_reason = (
                prompt337_plan_blocked_reason
                if prompt337_plan_blocked_reason and prompt337_plan_blocked_reason != "none"
                else "prompt337_plan_status_not_ready"
            )
        elif prompt337_plan_daemon_lite_status != "ready":
            blocked_reason = (
                prompt337_plan_blocked_reason
                if prompt337_plan_blocked_reason and prompt337_plan_blocked_reason != "none"
                else "prompt337_plan_daemon_lite_status_not_ready"
            )
        elif prompt337_plan_blocked_reason != "none":
            blocked_reason = "prompt337_plan_blocked_reason_not_none"
        elif not prompt337_plan_daemon_lite_ready:
            blocked_reason = "prompt337_plan_daemon_lite_ready_false"
        elif prompt337_plan_daemon_mode != "daemon_lite":
            blocked_reason = "prompt337_plan_daemon_mode_not_daemon_lite"
        elif prompt337_plan_daemon_is_background:
            blocked_reason = "prompt337_plan_daemon_is_real_background_process_true"
        elif prompt337_plan_background_execution_enabled:
            blocked_reason = "prompt337_plan_background_execution_enabled_true"
        elif prompt337_plan_scheduler_enabled:
            blocked_reason = "prompt337_plan_scheduler_enabled_true"
        elif prompt337_plan_watcher_enabled:
            blocked_reason = "prompt337_plan_watcher_enabled_true"
        elif prompt337_plan_max_wrapper_cycles != 1:
            blocked_reason = "prompt337_plan_max_wrapper_cycles_not_1"
        elif prompt337_plan_total_codex_invocation_budget != 1:
            blocked_reason = "prompt337_plan_total_codex_invocation_budget_not_1"
        elif not prompt337_plan_bounded_execution:
            blocked_reason = "prompt337_plan_bounded_execution_false"
        elif prompt337_plan_unbounded_loop_allowed:
            blocked_reason = "prompt337_plan_unbounded_loop_allowed_true"
        elif prompt337_plan_retry_allowed:
            blocked_reason = "prompt337_plan_retry_allowed_true"
        elif prompt337_plan_sleep_poll_allowed:
            blocked_reason = "prompt337_plan_sleep_poll_allowed_true"
        elif prompt337_plan_selected_step_id != 3:
            blocked_reason = "prompt337_plan_selected_step_id_not_3"
        elif prompt337_plan_selected_step_name != "execute_targeted_contract_fix_prompt":
            blocked_reason = "prompt337_plan_selected_step_name_not_execute_targeted_contract_fix_prompt"
        elif prompt337_plan_selected_step_operation != "execute_targeted_contract_fix_prompt":
            blocked_reason = "prompt337_plan_selected_step_operation_not_execute_targeted_contract_fix_prompt"
        elif (
            prompt337_plan_selected_step_authority_source
            != "prompt336_contract_fix_cycle_execution_handoff"
        ):
            blocked_reason = "prompt337_plan_selected_step_authority_source_not_prompt336_handoff"
        elif prompt337_plan_prompt_path != expected_prompt_path:
            blocked_reason = "prompt337_plan_prompt_path_mismatch"
        elif not prompt337_plan_prompt_exists:
            blocked_reason = "prompt337_plan_prompt_exists_false"
        elif not prompt337_plan_prompt_non_empty:
            blocked_reason = "prompt337_plan_prompt_non_empty_false"
        elif explicit_allowed_tracked_files != expected_allowed_tracked_files:
            blocked_reason = "prompt337_plan_explicit_allowed_tracked_files_mismatch"
        elif not mutation_allowed:
            blocked_reason = "prompt337_plan_mutation_allowed_false"
        elif prompt337_plan_execution_allowed:
            blocked_reason = "prompt337_plan_execution_allowed_true"
        elif prompt337_plan_codex_invocation_allowed:
            blocked_reason = "prompt337_plan_codex_invocation_allowed_true"
        elif prompt337_plan_command_argv:
            blocked_reason = "prompt337_plan_command_argv_not_empty"
        elif prompt337_plan_command_display:
            blocked_reason = "prompt337_plan_command_display_not_empty"
        elif (
            prompt337_plan_next_action != "manual_execute_bounded_targeted_contract_fix_adapter"
            and prompt337_plan_wrapper_next_action
            != "manual_execute_bounded_targeted_contract_fix_adapter"
        ):
            blocked_reason = "prompt337_plan_next_action_not_manual_execute_bounded_targeted_contract_fix_adapter"
        elif prompt337_decision_status != "ready":
            blocked_reason = (
                prompt337_decision_blocked_reason
                if prompt337_decision_blocked_reason and prompt337_decision_blocked_reason != "none"
                else "prompt337_decision_status_not_ready"
            )
        elif prompt337_decision_decision != "prepare_manual_bounded_targeted_contract_fix_execution":
            blocked_reason = "prompt337_decision_not_prepare_manual_bounded_targeted_contract_fix_execution"
        elif not prompt337_decision_daemon_lite_ready:
            blocked_reason = "prompt337_decision_daemon_lite_ready_false"
        elif prompt337_decision_selected_step_operation != "execute_targeted_contract_fix_prompt":
            blocked_reason = "prompt337_decision_selected_step_operation_not_execute_targeted_contract_fix_prompt"
        elif prompt337_decision_execution_allowed:
            blocked_reason = "prompt337_decision_execution_allowed_true"
        elif prompt337_decision_codex_invocation_allowed:
            blocked_reason = "prompt337_decision_codex_invocation_allowed_true"
        elif prompt337_receipt_status != "ready":
            blocked_reason = (
                prompt337_receipt_blocked_reason
                if prompt337_receipt_blocked_reason and prompt337_receipt_blocked_reason != "none"
                else "prompt337_receipt_status_not_ready"
            )
        elif not prompt337_receipt_daemon_lite_ready:
            blocked_reason = "prompt337_receipt_daemon_lite_ready_false"
        elif prompt337_receipt_selected_step_operation != "execute_targeted_contract_fix_prompt":
            blocked_reason = "prompt337_receipt_selected_step_operation_not_execute_targeted_contract_fix_prompt"
        elif not prompt337_receipt_prompt_exists:
            blocked_reason = "prompt337_receipt_prompt_exists_false"
        elif not prompt337_receipt_prompt_non_empty:
            blocked_reason = "prompt337_receipt_prompt_non_empty_false"
        elif prompt336_handoff_status != "ready":
            blocked_reason = (
                prompt336_handoff_blocked_reason
                if prompt336_handoff_blocked_reason and prompt336_handoff_blocked_reason != "none"
                else "prompt336_handoff_status_not_ready"
            )
        elif prompt336_handoff_handoff_status != "ready":
            blocked_reason = (
                prompt336_handoff_blocked_reason
                if prompt336_handoff_blocked_reason and prompt336_handoff_blocked_reason != "none"
                else "prompt336_handoff_handoff_status_not_ready"
            )
        elif prompt336_handoff_blocked_reason != "none":
            blocked_reason = "prompt336_handoff_blocked_reason_not_none"
        elif prompt336_handoff_next_action != "prompt337_may_execute_targeted_contract_fix_once":
            blocked_reason = "prompt336_handoff_next_action_not_prompt337_single_execution"
        elif prompt336_handoff_selected_step_operation != "execute_targeted_contract_fix_prompt":
            blocked_reason = "prompt336_handoff_selected_step_operation_not_execute_targeted_contract_fix_prompt"
        elif prompt336_handoff_explicit_allowed_tracked_files != expected_allowed_tracked_files:
            blocked_reason = "prompt336_handoff_explicit_allowed_tracked_files_mismatch"
        elif not prompt336_handoff_mutation_allowed:
            blocked_reason = "prompt336_handoff_mutation_allowed_false"
        elif prompt336_handoff_execution_allowed:
            blocked_reason = "prompt336_handoff_execution_allowed_true"
        elif prompt336_handoff_codex_invocation_allowed:
            blocked_reason = "prompt336_handoff_codex_invocation_allowed_true"
        elif prompt336_handoff_command_argv:
            blocked_reason = "prompt336_handoff_command_argv_not_empty"
        elif prompt336_handoff_command_display:
            blocked_reason = "prompt336_handoff_command_display_not_empty"
        elif prompt336_handoff_max_codex_invocations != 1:
            blocked_reason = "prompt336_handoff_max_codex_invocations_not_1"
        elif prompt336_handoff_codex_invocation_count != 0:
            blocked_reason = "prompt336_handoff_codex_invocation_count_not_0"
        elif prompt335_plan_status != "ready":
            blocked_reason = (
                prompt335_plan_blocked_reason
                if prompt335_plan_blocked_reason and prompt335_plan_blocked_reason != "none"
                else "prompt335_plan_status_not_ready"
            )
        elif prompt335_receipt_status != "ready":
            blocked_reason = (
                prompt335_receipt_blocked_reason
                if prompt335_receipt_blocked_reason and prompt335_receipt_blocked_reason != "none"
                else "prompt335_receipt_status_not_ready"
            )
        elif not prompt_non_empty:
            blocked_reason = "prompt335_prompt_non_empty_false"
        elif "DO NOT EXECUTE" in prompt_first_80_lines.upper():
            blocked_reason = "prompt335_prompt_contains_do_not_execute_in_first_80_lines"
        elif "Modify only automation/orchestration/planned_execution_runner.py" not in prompt_text:
            blocked_reason = "prompt335_prompt_missing_modify_only_instruction"
        elif "Do not run tests" not in prompt_text:
            blocked_reason = "prompt335_prompt_missing_do_not_run_tests_instruction"
        elif "Do not invoke Codex" not in prompt_text:
            blocked_reason = "prompt335_prompt_missing_do_not_invoke_codex_instruction"
        elif "missing_explicit_allowed_tracked_files_and_conflicting_step_authority" not in prompt_text:
            blocked_reason = "prompt335_prompt_missing_required_contract_fix_reason"
        elif (
            "generated_prompt_sha256" in prompt335_receipt_payload
            and prompt335_receipt_sha != prompt_sha256
        ):
            blocked_reason = "prompt335_receipt_generated_prompt_sha256_mismatch"
        elif (
            "generated_prompt_size_bytes" in prompt335_receipt_payload
            and prompt335_receipt_size != prompt_size_bytes
        ):
            blocked_reason = "prompt335_receipt_generated_prompt_size_bytes_mismatch"
        elif (
            "generated_prompt_line_count" in prompt335_receipt_payload
            and prompt335_receipt_lines != prompt_line_count
        ):
            blocked_reason = "prompt335_receipt_generated_prompt_line_count_mismatch"

    if blocked_reason != "none":
        readiness_errors.append(blocked_reason)
    validation_errors = _normalize_string_list(readiness_errors)
    readiness_failed = bool(validation_errors)
    if readiness_failed and blocked_reason == "none":
        blocked_reason = validation_errors[0]

    git_ok_before, changed_tracked_files_before_execution = _collect_changed_tracked_files(
        _normalize_text(execution_repo_path, default=_APPROVE_COMMIT_TAG_EXECUTION_REPO_PATH)
    )
    tracked_worktree_clean_before_execution = bool(
        git_ok_before and not changed_tracked_files_before_execution
    )
    if not git_ok_before and not readiness_failed:
        readiness_failed = True
        blocked_reason = "git_metadata_collection_failed_before_targeted_contract_fix_execution"
        validation_errors = _normalize_string_list(
            [*validation_errors, blocked_reason]
        )

    status = "blocked"
    execution_status = "blocked"
    readiness_reason = "targeted_contract_fix_execution_readiness_failed"
    next_action = "manual_review_targeted_contract_fix_execution_readiness"
    execution_allowed = False
    codex_invocation_allowed = False
    codex_invoked = False
    execution_attempted = False
    execution_completed = False
    execution_exit_code: int | None = None
    execution_timed_out = False
    codex_invocation_count = 0
    stdout_text = ""
    stderr_text = ""
    tracked_worktree_clean_after_execution = tracked_worktree_clean_before_execution
    changed_tracked_files_after_execution = list(changed_tracked_files_before_execution)

    if not readiness_failed and not tracked_worktree_clean_before_execution:
        blocked_reason = "tracked_changes_present_before_targeted_contract_fix_execution"
        status = "blocked"
        execution_status = "blocked"
        readiness_reason = "targeted_contract_fix_execution_worktree_not_clean"
        next_action = "manual_review_tracked_changes_before_targeted_contract_fix_execution"
        validation_errors = _normalize_string_list(validation_errors)
    elif not readiness_failed and tracked_worktree_clean_before_execution:
        readiness_reason = "targeted_contract_fix_execution_ready"
        execution_allowed = True
        codex_invocation_allowed = True
        codex_invoked = True
        execution_attempted = True
        codex_invocation_count = 1
        try:
            completed = subprocess.run(
                expected_command_argv,
                input=prompt_text,
                shell=False,
                cwd=_normalize_text(
                    execution_repo_path,
                    default=_APPROVE_COMMIT_TAG_EXECUTION_REPO_PATH,
                ),
                capture_output=True,
                text=True,
                check=False,
                timeout=_LOCAL_TARGETED_CONTRACT_FIX_EXECUTION_TIMEOUT_SECONDS,
            )
            execution_exit_code = _as_int(completed.returncode, default=126)
            stdout_text = _normalize_text(completed.stdout, default="")
            stderr_text = _normalize_text(completed.stderr, default="")
            execution_completed = True
        except subprocess.TimeoutExpired as exc:
            execution_timed_out = True
            execution_exit_code = 124
            if isinstance(exc.stdout, bytes):
                stdout_text = exc.stdout.decode("utf-8", errors="replace")
            else:
                stdout_text = _normalize_text(exc.stdout, default="")
            if isinstance(exc.stderr, bytes):
                stderr_text = exc.stderr.decode("utf-8", errors="replace")
            else:
                stderr_text = _normalize_text(exc.stderr, default="")
            execution_completed = False
        except OSError as exc:
            execution_exit_code = 126
            stdout_text = ""
            stderr_text = _normalize_text(str(exc), default="")
            execution_completed = True

        git_ok_after, changed_tracked_files_after_execution = _collect_changed_tracked_files(
            _normalize_text(execution_repo_path, default=_APPROVE_COMMIT_TAG_EXECUTION_REPO_PATH)
        )
        tracked_worktree_clean_after_execution = bool(
            git_ok_after and not changed_tracked_files_after_execution
        )

        if execution_timed_out:
            status = "completed"
            execution_status = "timeout"
            blocked_reason = "targeted_contract_fix_execution_timed_out"
            next_action = "manual_review_targeted_contract_fix_execution_timeout"
        elif execution_exit_code == 0:
            status = "completed"
            execution_status = "completed"
            blocked_reason = "none"
            next_action = (
                "prepare_post_targeted_contract_fix_diff_capture"
                if changed_tracked_files_after_execution
                else "manual_review_targeted_contract_fix_no_tracked_changes"
            )
        else:
            status = "completed"
            execution_status = "failed"
            blocked_reason = "targeted_contract_fix_execution_failed"
            next_action = "manual_review_targeted_contract_fix_execution_failure"

    try:
        one_cycle_controller_dir.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(stdout_text, encoding="utf-8")
        stderr_path.write_text(stderr_text, encoding="utf-8")
    except OSError:
        pass

    stdout_exists = stdout_path.exists()
    stderr_exists = stderr_path.exists()
    stdout_size_bytes = _get_file_size(stdout_path)
    stderr_size_bytes = _get_file_size(stderr_path)
    stdout_contains_blocked = _contains_blocked(stdout_text)
    stderr_contains_blocked = _contains_blocked(stderr_text)
    changed_tracked_file_count_after_execution = len(changed_tracked_files_after_execution)

    common_payload: dict[str, Any] = {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "prompt_id": "prompt338",
        "status": status,
        "execution_status": execution_status,
        "blocked_reason": blocked_reason,
        "readiness_reason": readiness_reason,
        "selected_step_id": selected_step_id,
        "selected_step_name": selected_step_name,
        "selected_step_operation": selected_step_operation,
        "selected_step_authority_source": selected_step_authority_source,
        "prompt337_plan_path": str(prompt337_plan_path),
        "prompt337_decision_path": str(prompt337_decision_path),
        "prompt337_receipt_path": str(prompt337_receipt_path),
        "prompt336_handoff_path": str(prompt336_handoff_path),
        "prompt335_prompt_path": str(prompt335_prompt_path),
        "prompt_exists": prompt_exists,
        "prompt_non_empty": prompt_non_empty,
        "prompt_sha256": prompt_sha256,
        "prompt_size_bytes": prompt_size_bytes,
        "prompt_line_count": prompt_line_count,
        "explicit_allowed_tracked_files": explicit_allowed_tracked_files,
        "mutation_allowed": mutation_allowed,
        "tracked_worktree_clean_before_execution": tracked_worktree_clean_before_execution,
        "changed_tracked_files_before_execution": changed_tracked_files_before_execution,
        "execution_allowed": execution_allowed,
        "codex_invocation_allowed": codex_invocation_allowed,
        "codex_invoked": codex_invoked,
        "execution_attempted": execution_attempted,
        "execution_completed": execution_completed,
        "execution_exit_code": execution_exit_code,
        "execution_timed_out": execution_timed_out,
        "max_codex_invocations": 1,
        "codex_invocation_count": codex_invocation_count,
        "command_argv": expected_command_argv,
        "command_display": command_display,
        "shell_used": False,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "stdout_exists": stdout_exists,
        "stderr_exists": stderr_exists,
        "stdout_size_bytes": stdout_size_bytes,
        "stderr_size_bytes": stderr_size_bytes,
        "stdout_contains_blocked": stdout_contains_blocked,
        "stderr_contains_blocked": stderr_contains_blocked,
        "tracked_worktree_clean_after_execution": tracked_worktree_clean_after_execution,
        "changed_tracked_files_after_execution": changed_tracked_files_after_execution,
        "changed_tracked_file_count_after_execution": changed_tracked_file_count_after_execution,
        "next_action": next_action,
        "validation_errors": validation_errors,
        "commit_allowed": False,
        "tag_allowed": False,
        "push_pr_merge_enabled": False,
        "rollback_allowed": False,
        "commit_performed": False,
        "tag_performed": False,
        "push_performed": False,
        "pr_created": False,
        "merge_performed": False,
        "rollback_performed": False,
    }

    state_payload = {
        **common_payload,
        "targeted_contract_fix_execution_state_schema_version": (
            _LOCAL_TARGETED_CONTRACT_FIX_EXECUTION_STATE_SCHEMA_VERSION
        ),
    }
    result_payload = {
        **common_payload,
        "targeted_contract_fix_execution_result_schema_version": (
            _LOCAL_TARGETED_CONTRACT_FIX_EXECUTION_RESULT_SCHEMA_VERSION
        ),
    }
    receipt_payload = {
        **common_payload,
        "targeted_contract_fix_execution_receipt_schema_version": (
            _LOCAL_TARGETED_CONTRACT_FIX_EXECUTION_RECEIPT_SCHEMA_VERSION
        ),
    }

    try:
        _write_json(execution_state_path, state_payload)
    except OSError:
        pass
    try:
        _write_json(execution_result_path, result_payload)
    except OSError:
        pass
    try:
        _write_json(execution_receipt_path, receipt_payload)
    except OSError:
        pass

    return {
        "local_targeted_contract_fix_execution_status": execution_status,
        "local_targeted_contract_fix_execution_blocked_reason": blocked_reason,
        "local_targeted_contract_fix_execution_next_action": next_action,
        "local_targeted_contract_fix_execution_codex_invoked": codex_invoked,
        "local_targeted_contract_fix_execution_exit_code": execution_exit_code,
        "local_targeted_contract_fix_execution_changed_tracked_file_count": (
            changed_tracked_file_count_after_execution
        ),
        "local_targeted_contract_fix_execution_stdout_path": str(stdout_path),
        "local_targeted_contract_fix_execution_stderr_path": str(stderr_path),
        "local_targeted_contract_fix_execution_state_path": str(execution_state_path),
        "local_targeted_contract_fix_execution_result_path": str(execution_result_path),
        "local_targeted_contract_fix_execution_receipt_path": str(execution_receipt_path),
    }

def _build_local_post_targeted_contract_fix_review_artifacts(
    *,
    execution_repo_path: str,
    one_cycle_controller_dir: Path,
) -> dict[str, Any]:
    def _as_boolish(value: Any, *, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        text = _normalize_text(value, default="").strip().lower()
        if text in {"1", "true", "yes", "on", "enabled"}:
            return True
        if text in {"0", "false", "no", "off", "disabled"}:
            return False
        return default

    def _read_json_mapping(path: Path) -> tuple[bool, bool, dict[str, Any]]:
        if not path.exists():
            return False, False, {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return True, False, {}
        if not isinstance(payload, Mapping):
            return True, False, {}
        return True, True, dict(payload)

    def _read_bounded_text(path: Path, *, max_chars: int) -> tuple[bool, int, str]:
        if not path.exists():
            return False, 0, ""
        size_bytes = 0
        try:
            size_bytes = _as_non_negative_int(path.stat().st_size, default=0)
        except OSError:
            size_bytes = 0
        try:
            raw_text = path.read_text(encoding="utf-8")
        except OSError:
            return True, size_bytes, ""
        if len(raw_text) <= max_chars:
            return True, size_bytes, raw_text
        head = max_chars // 2
        tail = max_chars - head
        bounded_text = raw_text[:head] + "\n...\n" + raw_text[-tail:]
        return True, size_bytes, bounded_text

    def _contains_blocked(text: str) -> bool:
        return "BLOCKED" in _normalize_text(text, default="").upper()

    def _contains_error_hint(text: str) -> bool:
        normalized = _normalize_text(text, default="").lower()
        return any(
            token in normalized
            for token in (
                "error",
                "exception",
                "traceback",
                "failed",
                "failure",
                "timeout",
            )
        )

    def _extract_blocked_reason(text: str) -> str:
        for line in text.splitlines():
            normalized_line = _normalize_text(line, default="").strip()
            upper_line = normalized_line.upper()
            if "BLOCKED" not in upper_line:
                continue
            if ":" in normalized_line:
                maybe = normalized_line.split(":", 1)[1].strip()
                if maybe:
                    return maybe
            return normalized_line
        return ""

    def _collect_tracked_diff_state(
        repo_path: str,
    ) -> tuple[bool, bool, list[str], list[str], list[str]]:
        try:
            status_short = _run_git(
                repo_path,
                ["status", "--short", "--untracked-files=no"],
                timeout_seconds=10,
            )
            unstaged_names = _run_git(
                repo_path,
                ["diff", "--name-only"],
                timeout_seconds=10,
            )
            staged_names = _run_git(
                repo_path,
                ["diff", "--cached", "--name-only"],
                timeout_seconds=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False, False, [], [], []

        if status_short.returncode != 0 or unstaged_names.returncode != 0 or staged_names.returncode != 0:
            return False, False, [], [], []

        status_paths = sorted(
            {
                _parse_git_status_path(line)
                for line in (status_short.stdout or "").splitlines()
                if line.strip() and _parse_git_status_path(line)
            }
        )
        unstaged = sorted(
            {
                _normalize_text(line, default="").strip()
                for line in (unstaged_names.stdout or "").splitlines()
                if _normalize_text(line, default="").strip()
            }
        )
        staged = sorted(
            {
                _normalize_text(line, default="").strip()
                for line in (staged_names.stdout or "").splitlines()
                if _normalize_text(line, default="").strip()
            }
        )
        changed = sorted(set(status_paths) | set(unstaged) | set(staged))
        tracked_worktree_clean = bool(not status_paths and not changed)
        return True, tracked_worktree_clean, changed, staged, unstaged

    def _safety_fields() -> dict[str, Any]:
        return {
            "codex_invoked": False,
            "codex_invocation_allowed": False,
            "execution_allowed": False,
            "commit_allowed": False,
            "tag_allowed": False,
            "push_pr_merge_enabled": False,
            "targeted_fix_execution_allowed": False,
            "rollback_allowed": False,
            "commit_performed": False,
            "tag_performed": False,
            "push_performed": False,
            "pr_created": False,
            "merge_performed": False,
            "rollback_performed": False,
        }

    one_cycle_controller_dir = Path(one_cycle_controller_dir)
    prompt338_state_path = one_cycle_controller_dir / "local_targeted_contract_fix_execution_state.json"
    prompt338_result_path = one_cycle_controller_dir / "local_targeted_contract_fix_execution_result.json"
    prompt338_receipt_path = (
        one_cycle_controller_dir / "local_targeted_contract_fix_execution_receipt.json"
    )
    prompt338_stdout_path = one_cycle_controller_dir / "local_targeted_contract_fix_execution_stdout.txt"
    prompt338_stderr_path = one_cycle_controller_dir / "local_targeted_contract_fix_execution_stderr.txt"

    prompt337_plan_path = one_cycle_controller_dir / "local_daemon_lite_wrapper_plan.json"
    prompt337_decision_path = one_cycle_controller_dir / "local_daemon_lite_wrapper_decision.json"
    prompt336_handoff_path = one_cycle_controller_dir / "local_contract_fix_cycle_execution_handoff.json"
    prompt335_plan_path = one_cycle_controller_dir / "local_targeted_contract_fix_prompt_plan.json"
    prompt335_receipt_path = one_cycle_controller_dir / "local_targeted_contract_fix_prompt_receipt.json"

    diff_capture_path = one_cycle_controller_dir / "local_post_targeted_contract_fix_diff_capture.json"
    execution_outcome_path = (
        one_cycle_controller_dir / "local_post_targeted_contract_fix_execution_outcome.json"
    )
    route_decision_path = one_cycle_controller_dir / "local_post_targeted_contract_fix_route_decision.json"
    review_receipt_path = one_cycle_controller_dir / "local_post_targeted_contract_fix_review_receipt.json"

    _, _, _ = _read_json_mapping(prompt338_state_path)
    _, _, _ = _read_json_mapping(prompt337_plan_path)
    _, _, _ = _read_json_mapping(prompt337_decision_path)
    _, _, _ = _read_json_mapping(prompt336_handoff_path)
    _, _, _ = _read_json_mapping(prompt335_plan_path)
    _, _, _ = _read_json_mapping(prompt335_receipt_path)

    prompt338_result_exists, prompt338_result_valid, prompt338_result_payload = _read_json_mapping(
        prompt338_result_path
    )
    (
        prompt338_receipt_exists,
        prompt338_receipt_valid,
        prompt338_receipt_payload,
    ) = _read_json_mapping(prompt338_receipt_path)

    stdout_exists, stdout_size_bytes, stdout_text = _read_bounded_text(
        prompt338_stdout_path,
        max_chars=_LOCAL_POST_TARGETED_CONTRACT_FIX_STDIO_MAX_CHARS,
    )
    stderr_exists, stderr_size_bytes, stderr_text = _read_bounded_text(
        prompt338_stderr_path,
        max_chars=_LOCAL_POST_TARGETED_CONTRACT_FIX_STDIO_MAX_CHARS,
    )

    stdout_contains_blocked = _contains_blocked(stdout_text)
    stderr_contains_blocked = _contains_blocked(stderr_text)
    stdout_contains_error_hint = _contains_error_hint(stdout_text)
    stderr_contains_error_hint = _contains_error_hint(stderr_text)
    stdout_blocked_reason = _extract_blocked_reason(stdout_text)
    stderr_blocked_reason = _extract_blocked_reason(stderr_text)

    validation_errors: list[str] = []
    blocked_reason = "none"
    readiness_reason = "prompt338_execution_artifacts_ready"
    prompt338_artifacts_ready = True

    if not prompt338_result_exists:
        prompt338_artifacts_ready = False
        blocked_reason = "prompt338_execution_artifacts_not_ready"
        validation_errors.append("missing_prompt338_execution_result_artifact")
    elif not prompt338_result_valid:
        prompt338_artifacts_ready = False
        blocked_reason = "prompt338_execution_artifacts_not_ready"
        validation_errors.append("invalid_prompt338_execution_result_artifact")

    if not prompt338_receipt_exists:
        prompt338_artifacts_ready = False
        blocked_reason = "prompt338_execution_artifacts_not_ready"
        validation_errors.append("missing_prompt338_execution_receipt_artifact")
    elif not prompt338_receipt_valid:
        prompt338_artifacts_ready = False
        blocked_reason = "prompt338_execution_artifacts_not_ready"
        validation_errors.append("invalid_prompt338_execution_receipt_artifact")

    prompt338_status = _normalize_text(prompt338_result_payload.get("status"), default="missing")
    prompt338_execution_status = _normalize_text(
        prompt338_result_payload.get("execution_status"),
        default="missing",
    )
    prompt338_execution_exit_code = _as_optional_int(
        prompt338_result_payload.get("execution_exit_code")
    )
    prompt338_codex_invoked = _as_boolish(
        prompt338_result_payload.get("codex_invoked"),
        default=False,
    )
    prompt338_execution_attempted = _as_boolish(
        prompt338_result_payload.get("execution_attempted"),
        default=False,
    )
    prompt338_execution_completed = _as_boolish(
        prompt338_result_payload.get("execution_completed"),
        default=False,
    )
    prompt338_execution_timed_out = _as_boolish(
        prompt338_result_payload.get("execution_timed_out"),
        default=False,
    )
    prompt338_codex_invocation_count = _as_non_negative_int(
        prompt338_result_payload.get("codex_invocation_count"),
        default=0,
    )

    prompt338_commit_allowed = _as_boolish(
        prompt338_result_payload.get("commit_allowed"),
        default=True,
    )
    prompt338_tag_allowed = _as_boolish(
        prompt338_result_payload.get("tag_allowed"),
        default=True,
    )
    prompt338_push_pr_merge_enabled = _as_boolish(
        prompt338_result_payload.get("push_pr_merge_enabled"),
        default=True,
    )
    prompt338_rollback_allowed = _as_boolish(
        prompt338_result_payload.get("rollback_allowed"),
        default=True,
    )

    if prompt338_artifacts_ready:
        if _normalize_text(
            prompt338_result_payload.get("schema_version"),
            default="",
        ) != _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION:
            prompt338_artifacts_ready = False
            blocked_reason = "prompt338_execution_artifacts_not_ready"
            validation_errors.append("prompt338_result_schema_version_mismatch")
        if _normalize_text(
            prompt338_receipt_payload.get("schema_version"),
            default="",
        ) != _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION:
            prompt338_artifacts_ready = False
            blocked_reason = "prompt338_execution_artifacts_not_ready"
            validation_errors.append("prompt338_receipt_schema_version_mismatch")

    prompt338_completed_reviewable = bool(
        prompt338_artifacts_ready
        and prompt338_status == "completed"
        and prompt338_execution_status in {"completed", "failed", "timeout"}
        and prompt338_codex_invoked
        and prompt338_codex_invocation_count == 1
        and not prompt338_commit_allowed
        and not prompt338_tag_allowed
        and not prompt338_push_pr_merge_enabled
        and not prompt338_rollback_allowed
    )
    prompt338_blocked_reviewable = bool(
        prompt338_artifacts_ready
        and (prompt338_status == "blocked" or prompt338_execution_status == "blocked")
        and _normalize_text(prompt338_result_payload.get("blocked_reason"), default="") != ""
        and not prompt338_codex_invoked
        and not prompt338_execution_attempted
        and not prompt338_execution_completed
    )

    if prompt338_artifacts_ready and not (prompt338_completed_reviewable or prompt338_blocked_reviewable):
        prompt338_artifacts_ready = False
        blocked_reason = "prompt338_execution_artifacts_not_ready"
        validation_errors.append("prompt338_execution_result_internally_inconsistent")

    git_ok, tracked_worktree_clean, changed_tracked_files, staged_tracked_files, unstaged_tracked_files = (
        _collect_tracked_diff_state(
            _normalize_text(execution_repo_path, default=_APPROVE_COMMIT_TAG_EXECUTION_REPO_PATH)
        )
    )
    if not git_ok:
        tracked_worktree_clean = False
        changed_tracked_files = []
        staged_tracked_files = []
        unstaged_tracked_files = []
        prompt338_artifacts_ready = False
        blocked_reason = "prompt338_execution_artifacts_not_ready"
        validation_errors.append("prompt339_tracked_diff_capture_failed")

    allowed_tracked_files = _normalize_string_list(
        prompt338_result_payload.get("explicit_allowed_tracked_files")
    )
    if not allowed_tracked_files:
        allowed_tracked_files = ["automation/orchestration/planned_execution_runner.py"]

    unexpected_tracked_files_changed = sorted(
        path for path in changed_tracked_files if path not in set(allowed_tracked_files)
    )
    only_allowed_tracked_files_changed = bool(
        (not changed_tracked_files) or (not unexpected_tracked_files_changed)
    )
    changed_tracked_file_count = len(changed_tracked_files)
    staged_tracked_file_count = len(staged_tracked_files)
    unstaged_tracked_file_count = len(unstaged_tracked_files)
    unexpected_tracked_file_count = len(unexpected_tracked_files_changed)
    local_diff_present = changed_tracked_file_count > 0

    codex_outcome_classification = "targeted_contract_fix_execution_not_ready"
    if prompt338_artifacts_ready:
        exit_code_nonzero = (
            prompt338_execution_exit_code is not None and prompt338_execution_exit_code != 0
        )
        if prompt338_status == "blocked" or (
            prompt338_execution_status == "blocked" and not prompt338_codex_invoked
        ):
            codex_outcome_classification = "targeted_contract_fix_execution_blocked_before_run"
        elif prompt338_execution_status == "timeout" or prompt338_execution_timed_out:
            codex_outcome_classification = "targeted_contract_fix_execution_timeout"
        elif prompt338_execution_status == "failed" or exit_code_nonzero:
            codex_outcome_classification = "targeted_contract_fix_execution_failed"
        elif (
            prompt338_execution_status == "completed"
            and (prompt338_execution_exit_code or 0) == 0
            and (stdout_contains_blocked or stderr_contains_blocked)
        ):
            codex_outcome_classification = "targeted_contract_fix_codex_blocked"
        elif (
            prompt338_execution_status == "completed"
            and (prompt338_execution_exit_code or 0) == 0
            and changed_tracked_file_count > 0
            and not only_allowed_tracked_files_changed
        ):
            codex_outcome_classification = "targeted_contract_fix_completed_with_unexpected_changes"
        elif (
            prompt338_execution_status == "completed"
            and (prompt338_execution_exit_code or 0) == 0
            and changed_tracked_file_count > 0
            and only_allowed_tracked_files_changed
            and not stdout_contains_blocked
            and not stderr_contains_blocked
        ):
            codex_outcome_classification = "targeted_contract_fix_completed_with_allowed_changes"
        elif (
            prompt338_execution_status == "completed"
            and (prompt338_execution_exit_code or 0) == 0
            and changed_tracked_file_count == 0
        ):
            codex_outcome_classification = "targeted_contract_fix_completed_no_changes"
        else:
            codex_outcome_classification = "targeted_contract_fix_execution_not_ready"
            blocked_reason = "prompt338_execution_artifacts_not_ready"
            validation_errors.append("prompt339_classification_preconditions_not_met")

    status = "completed"
    route_decision = "manual_review_prompt338_execution_artifacts"
    next_action = "manual_review_prompt338_execution_artifacts"
    approve_commit_tag_ready = False
    targeted_fix_recommended = False
    decision_reason = "prompt338_execution_artifacts_not_ready_for_prompt339"
    additional_targeted_fix_reason = ""
    if codex_outcome_classification == "targeted_contract_fix_completed_with_allowed_changes":
        route_decision = "prepare_approve_commit_tag"
        next_action = "prepare_bounded_approve_commit_tag_execution"
        approve_commit_tag_ready = True
        decision_reason = "prompt338_completed_with_allowed_tracked_changes"
        blocked_reason = "none"
    elif codex_outcome_classification == "targeted_contract_fix_completed_no_changes":
        route_decision = "manual_review_no_changes_after_targeted_fix"
        next_action = "manual_review_targeted_contract_fix_no_changes"
        decision_reason = "prompt338_completed_without_tracked_changes"
        blocked_reason = "none"
    elif codex_outcome_classification == "targeted_contract_fix_completed_with_unexpected_changes":
        route_decision = "manual_review_unexpected_tracked_changes"
        next_action = "manual_review_unexpected_tracked_changes"
        decision_reason = "unexpected_tracked_files_changed_after_prompt338"
        blocked_reason = "none"
    elif codex_outcome_classification == "targeted_contract_fix_codex_blocked":
        route_decision = "prepare_additional_targeted_fix_prompt"
        next_action = "prepare_additional_targeted_contract_fix_prompt"
        targeted_fix_recommended = True
        additional_targeted_fix_reason = stdout_blocked_reason or stderr_blocked_reason
        decision_reason = "prompt338_completed_with_blocked_output_signal"
        blocked_reason = "none"
    elif codex_outcome_classification == "targeted_contract_fix_execution_failed":
        route_decision = "manual_review_targeted_fix_execution_failure"
        next_action = "manual_review_targeted_fix_execution_failure"
        decision_reason = "prompt338_execution_failed"
        blocked_reason = "none"
    elif codex_outcome_classification == "targeted_contract_fix_execution_timeout":
        route_decision = "manual_review_targeted_fix_execution_timeout"
        next_action = "manual_review_targeted_fix_execution_timeout"
        decision_reason = "prompt338_execution_timeout"
        blocked_reason = "none"
    elif codex_outcome_classification == "targeted_contract_fix_execution_blocked_before_run":
        route_decision = "manual_review_targeted_fix_execution_blocked"
        next_action = "manual_review_targeted_fix_execution_blocked"
        decision_reason = "prompt338_blocked_before_execution"
        blocked_reason = "none"
    else:
        status = "blocked"
        route_decision = "manual_review_prompt338_execution_artifacts"
        next_action = "manual_review_prompt338_execution_artifacts"
        approve_commit_tag_ready = False
        targeted_fix_recommended = False
        decision_reason = "prompt338_execution_artifacts_not_ready_for_prompt339"
        blocked_reason = "prompt338_execution_artifacts_not_ready"
        readiness_reason = "prompt338_execution_artifacts_not_ready"

    if status == "completed":
        readiness_reason = "prompt339_post_targeted_contract_fix_review_completed"

    safety_fields = _safety_fields()

    diff_capture_payload: dict[str, Any] = {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "post_targeted_contract_fix_diff_capture_schema_version": (
            _LOCAL_POST_TARGETED_CONTRACT_FIX_DIFF_CAPTURE_SCHEMA_VERSION
        ),
        "prompt_id": "prompt339",
        "status": status,
        "blocked_reason": blocked_reason,
        "readiness_reason": readiness_reason,
        "prompt338_result_path": str(prompt338_result_path),
        "prompt338_receipt_path": str(prompt338_receipt_path),
        "prompt338_stdout_path": str(prompt338_stdout_path),
        "prompt338_stderr_path": str(prompt338_stderr_path),
        "prompt338_status": prompt338_status,
        "prompt338_execution_status": prompt338_execution_status,
        "prompt338_execution_exit_code": prompt338_execution_exit_code,
        "prompt338_codex_invoked": prompt338_codex_invoked,
        "tracked_worktree_clean": tracked_worktree_clean,
        "local_diff_present": local_diff_present,
        "changed_tracked_files": changed_tracked_files,
        "changed_tracked_file_count": changed_tracked_file_count,
        "staged_tracked_files": staged_tracked_files,
        "unstaged_tracked_files": unstaged_tracked_files,
        "staged_tracked_file_count": staged_tracked_file_count,
        "unstaged_tracked_file_count": unstaged_tracked_file_count,
        "allowed_tracked_files": allowed_tracked_files,
        "only_allowed_tracked_files_changed": only_allowed_tracked_files_changed,
        "unexpected_tracked_files_changed": unexpected_tracked_files_changed,
        "unexpected_tracked_file_count": unexpected_tracked_file_count,
        "stdout_exists": stdout_exists,
        "stderr_exists": stderr_exists,
        "stdout_size_bytes": stdout_size_bytes,
        "stderr_size_bytes": stderr_size_bytes,
        "stdout_contains_blocked": stdout_contains_blocked,
        "stderr_contains_blocked": stderr_contains_blocked,
        "stdout_contains_error_hint": stdout_contains_error_hint,
        "stderr_contains_error_hint": stderr_contains_error_hint,
        "stdout_blocked_reason": stdout_blocked_reason,
        "stderr_blocked_reason": stderr_blocked_reason,
        "codex_invocation_allowed": False,
        "execution_allowed": False,
        "commit_allowed": False,
        "tag_allowed": False,
        "push_pr_merge_enabled": False,
        "rollback_allowed": False,
        "next_action": next_action,
        "validation_errors": _normalize_string_list(validation_errors),
        **safety_fields,
    }

    execution_outcome_payload: dict[str, Any] = {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "post_targeted_contract_fix_execution_outcome_schema_version": (
            _LOCAL_POST_TARGETED_CONTRACT_FIX_EXECUTION_OUTCOME_SCHEMA_VERSION
        ),
        "prompt_id": "prompt339",
        "status": status,
        "blocked_reason": blocked_reason,
        "readiness_reason": readiness_reason,
        "codex_outcome_classification": codex_outcome_classification,
        "prompt338_status": prompt338_status,
        "prompt338_execution_status": prompt338_execution_status,
        "prompt338_execution_exit_code": prompt338_execution_exit_code,
        "prompt338_codex_invoked": prompt338_codex_invoked,
        "prompt338_execution_attempted": prompt338_execution_attempted,
        "prompt338_execution_completed": prompt338_execution_completed,
        "prompt338_execution_timed_out": prompt338_execution_timed_out,
        "stdout_contains_blocked": stdout_contains_blocked,
        "stderr_contains_blocked": stderr_contains_blocked,
        "stdout_blocked_reason": stdout_blocked_reason,
        "stderr_blocked_reason": stderr_blocked_reason,
        "changed_tracked_files": changed_tracked_files,
        "changed_tracked_file_count": changed_tracked_file_count,
        "only_allowed_tracked_files_changed": only_allowed_tracked_files_changed,
        "unexpected_tracked_files_changed": unexpected_tracked_files_changed,
        "next_action": next_action,
        "validation_errors": _normalize_string_list(validation_errors),
        **safety_fields,
    }

    route_decision_payload: dict[str, Any] = {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "post_targeted_contract_fix_route_decision_schema_version": (
            _LOCAL_POST_TARGETED_CONTRACT_FIX_ROUTE_DECISION_SCHEMA_VERSION
        ),
        "prompt_id": "prompt339",
        "status": status,
        "blocked_reason": blocked_reason,
        "readiness_reason": readiness_reason,
        "codex_outcome_classification": codex_outcome_classification,
        "route_decision": route_decision,
        "decision_reason": decision_reason,
        "approve_commit_tag_ready": approve_commit_tag_ready,
        "approve_commit_tag_allowed": False,
        "targeted_fix_recommended": targeted_fix_recommended,
        "additional_targeted_fix_reason": additional_targeted_fix_reason,
        "allowed_tracked_files": allowed_tracked_files,
        "changed_tracked_files": changed_tracked_files,
        "unexpected_tracked_files_changed": unexpected_tracked_files_changed,
        "next_action": next_action,
        "validation_errors": _normalize_string_list(validation_errors),
        **safety_fields,
    }

    review_receipt_payload: dict[str, Any] = {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "post_targeted_contract_fix_review_receipt_schema_version": (
            _LOCAL_POST_TARGETED_CONTRACT_FIX_REVIEW_RECEIPT_SCHEMA_VERSION
        ),
        "prompt_id": "prompt339",
        "status": status,
        "blocked_reason": blocked_reason,
        "readiness_reason": readiness_reason,
        "diff_capture_path": str(diff_capture_path),
        "execution_outcome_path": str(execution_outcome_path),
        "route_decision_path": str(route_decision_path),
        "prompt338_result_path": str(prompt338_result_path),
        "prompt338_receipt_path": str(prompt338_receipt_path),
        "codex_outcome_classification": codex_outcome_classification,
        "route_decision": route_decision,
        "approve_commit_tag_ready": approve_commit_tag_ready,
        "targeted_fix_recommended": targeted_fix_recommended,
        "changed_tracked_file_count": changed_tracked_file_count,
        "unexpected_tracked_file_count": unexpected_tracked_file_count,
        "next_action": next_action,
        "validation_errors": _normalize_string_list(validation_errors),
        **safety_fields,
    }

    try:
        one_cycle_controller_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    try:
        _write_json(diff_capture_path, diff_capture_payload)
    except OSError:
        pass
    try:
        _write_json(execution_outcome_path, execution_outcome_payload)
    except OSError:
        pass
    try:
        _write_json(route_decision_path, route_decision_payload)
    except OSError:
        pass
    try:
        _write_json(review_receipt_path, review_receipt_payload)
    except OSError:
        pass

    return {
        "local_post_targeted_contract_fix_status": status,
        "local_post_targeted_contract_fix_blocked_reason": blocked_reason,
        "local_post_targeted_contract_fix_classification": codex_outcome_classification,
        "local_post_targeted_contract_fix_route_decision": route_decision,
        "local_post_targeted_contract_fix_next_action": next_action,
        "local_post_targeted_contract_fix_approve_commit_tag_ready": approve_commit_tag_ready,
        "local_post_targeted_contract_fix_changed_tracked_file_count": changed_tracked_file_count,
        "local_post_targeted_contract_fix_unexpected_tracked_file_count": (
            unexpected_tracked_file_count
        ),
        "local_post_targeted_contract_fix_diff_capture_path": str(diff_capture_path),
        "local_post_targeted_contract_fix_execution_outcome_path": str(execution_outcome_path),
        "local_post_targeted_contract_fix_route_decision_path": str(route_decision_path),
        "local_post_targeted_contract_fix_review_receipt_path": str(review_receipt_path),
    }

def _build_local_post_commit_cycle_closure_artifacts(
    *,
    execution_repo_path: str,
    one_cycle_controller_dir: Path,
) -> dict[str, Any]:
    def _as_boolish(value: Any, *, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        text = _normalize_text(value, default="").strip().lower()
        if text in {"1", "true", "yes", "on", "enabled"}:
            return True
        if text in {"0", "false", "no", "off", "disabled"}:
            return False
        return default

    def _read_json_mapping(path: Path) -> tuple[bool, bool, dict[str, Any]]:
        if not path.exists():
            return False, False, {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return True, False, {}
        if not isinstance(payload, Mapping):
            return True, False, {}
        return True, True, dict(payload)

    def _run_local_git(
        repo_path: str,
        args: list[str],
        *,
        timeout_seconds: float,
    ) -> tuple[bool, subprocess.CompletedProcess[str] | None]:
        try:
            completed = subprocess.run(
                ["git", "-C", repo_path, *args],
                text=True,
                capture_output=True,
                check=False,
                timeout=timeout_seconds,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False, None
        return True, completed

    def _collect_tracked_diff_state(
        repo_path: str,
    ) -> tuple[bool, bool, list[str], list[str], list[str]]:
        status_ok, status_short = _run_local_git(
            repo_path,
            ["status", "--short", "--untracked-files=no"],
            timeout_seconds=10,
        )
        unstaged_ok, unstaged_names = _run_local_git(
            repo_path,
            ["diff", "--name-only"],
            timeout_seconds=10,
        )
        staged_ok, staged_names = _run_local_git(
            repo_path,
            ["diff", "--cached", "--name-only"],
            timeout_seconds=10,
        )
        if (
            not status_ok
            or not unstaged_ok
            or not staged_ok
            or status_short is None
            or unstaged_names is None
            or staged_names is None
        ):
            return False, False, [], [], []
        if (
            status_short.returncode != 0
            or unstaged_names.returncode != 0
            or staged_names.returncode != 0
        ):
            return False, False, [], [], []

        status_paths = sorted(
            {
                _parse_git_status_path(line)
                for line in (status_short.stdout or "").splitlines()
                if line.strip() and _parse_git_status_path(line)
            }
        )
        unstaged = sorted(
            {
                _normalize_text(line, default="").strip()
                for line in (unstaged_names.stdout or "").splitlines()
                if _normalize_text(line, default="").strip()
            }
        )
        staged = sorted(
            {
                _normalize_text(line, default="").strip()
                for line in (staged_names.stdout or "").splitlines()
                if _normalize_text(line, default="").strip()
            }
        )
        changed = sorted(set(status_paths) | set(unstaged) | set(staged))
        tracked_worktree_clean = bool(not changed and not staged and not unstaged)
        return True, tracked_worktree_clean, changed, staged, unstaged

    def _safety_fields() -> dict[str, Any]:
        return {
            "codex_invoked": False,
            "codex_invocation_allowed": False,
            "execution_allowed": False,
            "targeted_fix_execution_allowed": False,
            "commit_allowed": False,
            "tag_allowed": False,
            "push_pr_merge_enabled": False,
            "rollback_allowed": False,
            "commit_performed": False,
            "tag_performed": False,
            "push_performed": False,
            "pr_created": False,
            "merge_performed": False,
            "rollback_performed": False,
        }

    one_cycle_controller_dir = Path(one_cycle_controller_dir)
    prompt340_gate_state_path = one_cycle_controller_dir / "local_bounded_approve_commit_tag_gate_state.json"
    prompt340_result_path = (
        one_cycle_controller_dir / "local_bounded_approve_commit_tag_execution_result.json"
    )
    prompt340_receipt_path = (
        one_cycle_controller_dir / "local_bounded_approve_commit_tag_execution_receipt.json"
    )
    prompt340_plan_path = one_cycle_controller_dir / "local_bounded_approve_commit_tag_plan.json"
    prompt339_route_decision_path = (
        one_cycle_controller_dir / "local_post_targeted_contract_fix_route_decision.json"
    )
    prompt339_review_receipt_path = (
        one_cycle_controller_dir / "local_post_targeted_contract_fix_review_receipt.json"
    )
    prompt338_result_path = one_cycle_controller_dir / "local_targeted_contract_fix_execution_result.json"
    prompt337_plan_path = one_cycle_controller_dir / "local_daemon_lite_wrapper_plan.json"
    prompt334_route_path = one_cycle_controller_dir / "local_post_codex_route_decision.json"
    prompt334_outcome_path = one_cycle_controller_dir / "local_post_codex_execution_outcome.json"
    prompt334_diff_capture_path = one_cycle_controller_dir / "local_post_codex_diff_capture.json"
    cycle_state_path = one_cycle_controller_dir / "local_autonomous_cycle_v2_state.json"
    cycle_decision_path = one_cycle_controller_dir / "local_autonomous_cycle_v2_decision.json"
    cycle_receipt_path = one_cycle_controller_dir / "local_autonomous_cycle_v2_receipt.json"

    closure_state_path = one_cycle_controller_dir / "local_post_commit_cycle_closure_state.json"
    closure_decision_path = one_cycle_controller_dir / "local_post_commit_cycle_closure_decision.json"
    closure_receipt_path = one_cycle_controller_dir / "local_post_commit_cycle_closure_receipt.json"
    reentry_decision_path = one_cycle_controller_dir / "local_next_cycle_reentry_decision.json"

    prompt340_result_exists, prompt340_result_valid, prompt340_result_payload = _read_json_mapping(
        prompt340_result_path
    )
    prompt340_receipt_exists, prompt340_receipt_valid, prompt340_receipt_payload = _read_json_mapping(
        prompt340_receipt_path
    )
    prompt340_plan_exists, prompt340_plan_valid, prompt340_plan_payload = _read_json_mapping(
        prompt340_plan_path
    )
    prompt340_gate_exists, prompt340_gate_valid, prompt340_gate_payload = _read_json_mapping(
        prompt340_gate_state_path
    )
    cycle_state_exists, cycle_state_valid, cycle_state_payload = _read_json_mapping(cycle_state_path)
    cycle_decision_exists, cycle_decision_valid, cycle_decision_payload = _read_json_mapping(
        cycle_decision_path
    )
    cycle_receipt_exists, cycle_receipt_valid, cycle_receipt_payload = _read_json_mapping(
        cycle_receipt_path
    )
    _ = _read_json_mapping(prompt339_route_decision_path)
    _ = _read_json_mapping(prompt339_review_receipt_path)
    _ = _read_json_mapping(prompt338_result_path)
    _ = _read_json_mapping(prompt337_plan_path)
    prompt334_route_exists, prompt334_route_valid, prompt334_route_payload = _read_json_mapping(
        prompt334_route_path
    )
    prompt334_outcome_exists, prompt334_outcome_valid, prompt334_outcome_payload = _read_json_mapping(
        prompt334_outcome_path
    )
    _, _, prompt334_diff_payload = _read_json_mapping(
        prompt334_diff_capture_path
    )

    current_cycle = _LOCAL_AUTONOMOUS_CYCLE_V2_CURRENT_CYCLE
    max_cycles = _LOCAL_AUTONOMOUS_CYCLE_V2_MAX_CYCLES
    run_id = "local-autonomous-v2"
    cycle_id = f"{run_id}-cycle-{current_cycle}"
    for exists, valid, payload in (
        (cycle_state_exists, cycle_state_valid, cycle_state_payload),
        (cycle_decision_exists, cycle_decision_valid, cycle_decision_payload),
        (cycle_receipt_exists, cycle_receipt_valid, cycle_receipt_payload),
    ):
        if not exists or not valid:
            continue
        run_id = _normalize_text(payload.get("run_id"), default=run_id) or run_id
        cycle_id = _normalize_text(payload.get("cycle_id"), default=cycle_id) or cycle_id
        parsed_current_cycle = _as_non_negative_int(payload.get("current_cycle"), default=current_cycle)
        parsed_max_cycles = _as_non_negative_int(payload.get("max_cycles"), default=max_cycles)
        current_cycle = parsed_current_cycle if parsed_current_cycle > 0 else current_cycle
        max_cycles = parsed_max_cycles if parsed_max_cycles > 0 else max_cycles
        break
    completed_cycle = current_cycle
    next_cycle = current_cycle + 1

    validation_errors: list[str] = []

    prompt334_route_decision = _normalize_text(prompt334_route_payload.get("route_decision"), default="")
    prompt334_route_status = _normalize_text(prompt334_route_payload.get("status"), default="")
    prompt334_codex_outcome_classification = _normalize_text(
        prompt334_route_payload.get("codex_outcome_classification"),
        default=_normalize_text(
            prompt334_outcome_payload.get("codex_outcome_classification"),
            default="",
        ),
    )
    prompt334_blocked_reason = _normalize_text(
        prompt334_route_payload.get("blocked_reason"),
        default=_normalize_text(prompt334_outcome_payload.get("blocked_reason"), default=""),
    )
    prompt334_blocked_reason_clear = (
        _normalize_text(prompt334_blocked_reason, default="").strip().lower() in {"", "none"}
    )
    prompt334_changed_tracked_file_count = _as_non_negative_int(
        prompt334_outcome_payload.get("changed_tracked_file_count"),
        default=_as_non_negative_int(
            prompt334_diff_payload.get("changed_tracked_file_count"),
            default=1,
        ),
    )
    prompt334_no_change_route_match = (
        prompt334_route_decision == "prepare_no_change_review"
        and prompt334_codex_outcome_classification == "codex_task_success_no_tracked_changes"
        and prompt334_changed_tracked_file_count == 0
        and prompt334_blocked_reason_clear
    )
    prompt334_no_change_success_route = bool(
        prompt334_route_exists
        and prompt334_route_valid
        and prompt334_outcome_exists
        and prompt334_outcome_valid
        and prompt334_route_status == "completed"
        and prompt334_no_change_route_match
    )

    prompt340_artifacts_required = not prompt334_no_change_success_route
    prompt340_artifacts_ready = not prompt340_artifacts_required

    prompt340_status = _normalize_text(prompt340_result_payload.get("status"), default="")
    prompt340_execution_status = _normalize_text(
        prompt340_result_payload.get("execution_status"),
        default="",
    )
    prompt340_commit_performed = _as_boolish(
        prompt340_result_payload.get("commit_performed"),
        default=False,
    )
    prompt340_tag_performed = _as_boolish(
        prompt340_result_payload.get("tag_performed"),
        default=False,
    )
    prompt340_commit_hash = _normalize_text(prompt340_result_payload.get("commit_hash"), default="")
    prompt340_tag_name = _normalize_text(prompt340_result_payload.get("tag_name"), default="")
    prompt340_tag_points_at_commit = _as_boolish(
        prompt340_result_payload.get("tag_points_at_commit"),
        default=False,
    )

    if prompt340_artifacts_required:
        if not prompt340_result_exists:
            prompt340_artifacts_ready = False
            validation_errors.append("missing_prompt340_execution_result_artifact")
        elif not prompt340_result_valid:
            prompt340_artifacts_ready = False
            validation_errors.append("invalid_prompt340_execution_result_artifact")
        else:
            result_expectations: tuple[tuple[str, Any], ...] = (
                ("schema_version", _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION),
                ("status", "completed"),
                ("execution_status", "completed"),
                ("commit_performed", True),
                ("tag_performed", True),
                ("tag_points_at_commit", True),
                ("post_execution_tracked_worktree_clean", True),
                ("next_action", "prepare_post_commit_cycle_closure"),
                ("codex_invoked", False),
                ("push_pr_merge_enabled", False),
                ("rollback_allowed", False),
                ("push_performed", False),
                ("pr_created", False),
                ("merge_performed", False),
                ("rollback_performed", False),
            )
            for key, expected in result_expectations:
                value = prompt340_result_payload.get(key)
                if isinstance(expected, bool):
                    if _as_boolish(value, default=not expected) != expected:
                        prompt340_artifacts_ready = False
                        validation_errors.append(f"prompt340_result_{key}_mismatch")
                else:
                    if _normalize_text(value, default="") != expected:
                        prompt340_artifacts_ready = False
                        validation_errors.append(f"prompt340_result_{key}_mismatch")
            if not prompt340_commit_hash:
                prompt340_artifacts_ready = False
                validation_errors.append("prompt340_result_commit_hash_missing")
            if not prompt340_tag_name:
                prompt340_artifacts_ready = False
                validation_errors.append("prompt340_result_tag_name_missing")

        if not prompt340_receipt_exists:
            prompt340_artifacts_ready = False
            validation_errors.append("missing_prompt340_execution_receipt_artifact")
        elif not prompt340_receipt_valid:
            prompt340_artifacts_ready = False
            validation_errors.append("invalid_prompt340_execution_receipt_artifact")
        else:
            receipt_expectations: tuple[tuple[str, Any], ...] = (
                ("status", "completed"),
                ("execution_status", "completed"),
                ("commit_performed", True),
                ("tag_performed", True),
                ("tag_points_at_commit", True),
                ("post_execution_tracked_worktree_clean", True),
                ("next_action", "prepare_post_commit_cycle_closure"),
            )
            for key, expected in receipt_expectations:
                value = prompt340_receipt_payload.get(key)
                if isinstance(expected, bool):
                    if _as_boolish(value, default=not expected) != expected:
                        prompt340_artifacts_ready = False
                        validation_errors.append(f"prompt340_receipt_{key}_mismatch")
                else:
                    if _normalize_text(value, default="") != expected:
                        prompt340_artifacts_ready = False
                        validation_errors.append(f"prompt340_receipt_{key}_mismatch")
            receipt_commit_hash = _normalize_text(
                prompt340_receipt_payload.get("commit_hash"),
                default="",
            )
            receipt_tag_name = _normalize_text(prompt340_receipt_payload.get("tag_name"), default="")
            if receipt_commit_hash != prompt340_commit_hash:
                prompt340_artifacts_ready = False
                validation_errors.append("prompt340_receipt_commit_hash_mismatch")
            if receipt_tag_name != prompt340_tag_name:
                prompt340_artifacts_ready = False
                validation_errors.append("prompt340_receipt_tag_name_mismatch")

        for label, exists, valid, payload in (
            ("prompt340_plan", prompt340_plan_exists, prompt340_plan_valid, prompt340_plan_payload),
            ("prompt340_gate", prompt340_gate_exists, prompt340_gate_valid, prompt340_gate_payload),
        ):
            if not exists:
                continue
            if not valid:
                prompt340_artifacts_ready = False
                validation_errors.append(f"invalid_{label}_artifact")
                continue
            if not _as_boolish(payload.get("approve_commit_tag_ready"), default=False):
                prompt340_artifacts_ready = False
                validation_errors.append(f"{label}_approve_commit_tag_ready_mismatch")
            if _normalize_text(payload.get("route_decision"), default="") != "prepare_approve_commit_tag":
                prompt340_artifacts_ready = False
                validation_errors.append(f"{label}_route_decision_mismatch")
            if _as_boolish(payload.get("push_pr_merge_enabled"), default=True):
                prompt340_artifacts_ready = False
                validation_errors.append(f"{label}_push_pr_merge_enabled_mismatch")
            if _as_boolish(payload.get("rollback_allowed"), default=True):
                prompt340_artifacts_ready = False
                validation_errors.append(f"{label}_rollback_allowed_mismatch")
            status_value = _normalize_text(payload.get("status"), default="")
            execution_status_value = _normalize_text(payload.get("execution_status"), default="")
            for permission_key in ("commit_allowed", "tag_allowed"):
                if not _as_boolish(payload.get(permission_key), default=False):
                    continue
                in_ready_path = status_value in {"ready", "completed"} or execution_status_value in {
                    "ready",
                    "completed",
                }
                if not in_ready_path:
                    prompt340_artifacts_ready = False
                    validation_errors.append(f"{label}_{permission_key}_outside_ready_completed_path")

    current_head_hash = ""
    current_head_matches_prompt340_commit = False
    prompt340_tag_resolves_to_commit = False
    prompt340_tag_points_at_head = False
    tracked_worktree_clean = False
    staged_tracked_files: list[str] = []
    unstaged_tracked_files: list[str] = []
    changed_tracked_files: list[str] = []
    git_verification_ok = False

    normalized_repo_path = _normalize_text(
        execution_repo_path,
        default=_APPROVE_COMMIT_TAG_EXECUTION_REPO_PATH,
    )
    if prompt340_artifacts_ready and prompt340_artifacts_required:
        head_ok, head_completed = _run_local_git(
            normalized_repo_path,
            ["rev-parse", "HEAD"],
            timeout_seconds=10,
        )
        tag_ok, tag_completed = _run_local_git(
            normalized_repo_path,
            ["rev-list", "-n", "1", prompt340_tag_name],
            timeout_seconds=10,
        )
        diff_ok, tracked_worktree_clean, changed_tracked_files, staged_tracked_files, unstaged_tracked_files = (
            _collect_tracked_diff_state(normalized_repo_path)
        )
        if head_ok and isinstance(head_completed, subprocess.CompletedProcess) and head_completed.returncode == 0:
            current_head_hash = _normalize_text(head_completed.stdout, default="")
        else:
            validation_errors.append("prompt341_head_lookup_failed")
        tag_target_hash = ""
        if (
            tag_ok
            and isinstance(tag_completed, subprocess.CompletedProcess)
            and tag_completed.returncode == 0
        ):
            tag_target_hash = _normalize_text(tag_completed.stdout, default="")
        else:
            validation_errors.append("prompt341_tag_resolution_failed")
        if not diff_ok:
            validation_errors.append("prompt341_tracked_worktree_state_lookup_failed")

        current_head_matches_prompt340_commit = bool(
            current_head_hash and prompt340_commit_hash and current_head_hash == prompt340_commit_hash
        )
        prompt340_tag_resolves_to_commit = bool(
            tag_target_hash and prompt340_commit_hash and tag_target_hash == prompt340_commit_hash
        )
        prompt340_tag_points_at_head = bool(
            tag_target_hash and current_head_hash and tag_target_hash == current_head_hash
        )
        git_verification_ok = bool(
            current_head_matches_prompt340_commit
            and prompt340_tag_resolves_to_commit
            and prompt340_tag_points_at_head
            and tracked_worktree_clean
            and not staged_tracked_files
            and not unstaged_tracked_files
        )
        if not git_verification_ok:
            validation_errors.append("prompt341_post_commit_git_state_verification_failed")
    elif prompt334_no_change_success_route:
        head_ok, head_completed = _run_local_git(
            normalized_repo_path,
            ["rev-parse", "HEAD"],
            timeout_seconds=10,
        )
        diff_ok, tracked_worktree_clean, changed_tracked_files, staged_tracked_files, unstaged_tracked_files = (
            _collect_tracked_diff_state(normalized_repo_path)
        )
        if head_ok and isinstance(head_completed, subprocess.CompletedProcess) and head_completed.returncode == 0:
            current_head_hash = _normalize_text(head_completed.stdout, default="")
        else:
            validation_errors.append("prompt341_no_change_head_lookup_failed")
        if not diff_ok:
            validation_errors.append("prompt341_no_change_tracked_worktree_state_lookup_failed")
        git_verification_ok = bool(
            diff_ok
            and tracked_worktree_clean
            and not staged_tracked_files
            and not unstaged_tracked_files
        )
        if not git_verification_ok:
            validation_errors.append("prompt341_post_no_change_git_state_verification_failed")

    status = "blocked"
    closure_status = "blocked"
    blocked_reason = "prompt340_commit_tag_artifacts_not_ready"
    readiness_reason = "prompt341_prompt340_artifacts_not_ready"
    no_change_cycle_closure = False
    commit_required = True
    tag_required = True
    local_commit_tag_complete = False
    cycle_closed = False
    cycle_decision = "manual_review_post_commit_cycle_closure"
    decision_reason = "post_commit_cycle_closure_not_ready"
    reentry_allowed = False
    should_continue = False
    next_action = "manual_review_prompt340_commit_tag_artifacts"
    reentry_status = "blocked"

    if prompt334_no_change_success_route:
        no_change_cycle_closure = True
        commit_required = False
        tag_required = False
        if not git_verification_ok:
            blocked_reason = "post_no_change_git_state_verification_failed"
            readiness_reason = "prompt341_post_no_change_git_state_verification_failed"
            decision_reason = "post_no_change_git_state_verification_failed"
            next_action = "manual_review_post_no_change_git_state"
        else:
            status = "completed"
            closure_status = "completed"
            blocked_reason = "none"
            readiness_reason = "prompt341_no_change_cycle_closure_verified"
            local_commit_tag_complete = True
            cycle_closed = True
            if next_cycle <= max_cycles:
                cycle_decision = "continue_next_local_autonomous_cycle"
                decision_reason = "no_change_cycle_closed_and_within_max_cycles"
                reentry_allowed = True
                should_continue = True
                next_action = "select_next_local_autonomous_step"
                reentry_status = "ready_for_reentry"
            else:
                cycle_decision = "bounded_cycle_limit_reached"
                decision_reason = "no_change_cycle_closed_and_bounded_cycle_limit_reached"
                reentry_allowed = False
                should_continue = False
                next_action = "local_autonomous_loop_complete"
                reentry_status = "bounded_cycle_limit_reached"
    elif prompt340_artifacts_ready and not git_verification_ok:
        blocked_reason = "post_commit_git_state_verification_failed"
        readiness_reason = "prompt341_post_commit_git_state_verification_failed"
        decision_reason = "post_commit_git_state_verification_failed"
        next_action = "manual_review_post_commit_git_state"
    elif prompt340_artifacts_ready and git_verification_ok:
        status = "completed"
        closure_status = "completed"
        blocked_reason = "none"
        readiness_reason = "prompt341_post_commit_cycle_closure_verified"
        local_commit_tag_complete = True
        cycle_closed = True
        if next_cycle <= max_cycles:
            cycle_decision = "continue_next_local_autonomous_cycle"
            decision_reason = "cycle_closed_and_within_max_cycles"
            reentry_allowed = True
            should_continue = True
            next_action = "select_next_local_autonomous_step"
            reentry_status = "ready_for_reentry"
        else:
            cycle_decision = "bounded_cycle_limit_reached"
            decision_reason = "cycle_closed_and_bounded_cycle_limit_reached"
            reentry_allowed = False
            should_continue = False
            next_action = "local_autonomous_loop_complete"
            reentry_status = "bounded_cycle_limit_reached"

    cycle_commit_hash = prompt340_commit_hash if commit_required else ""
    cycle_tag_name = prompt340_tag_name if tag_required else ""

    next_selected_step_id: int | None = None
    next_selected_step_name = ""
    next_selected_step_operation = ""
    next_selected_step_authority_source = ""
    if reentry_allowed:
        next_selected_step_id = 1
        next_selected_step_name = "read_current_state"
        next_selected_step_operation = "read_current_state"
        next_selected_step_authority_source = "prompt341_post_commit_cycle_closure"

    safety_fields = _safety_fields()
    state_payload: dict[str, Any] = {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "post_commit_cycle_closure_state_schema_version": (
            _LOCAL_POST_COMMIT_CYCLE_CLOSURE_STATE_SCHEMA_VERSION
        ),
        "prompt_id": "prompt341",
        "status": status,
        "closure_status": closure_status,
        "blocked_reason": blocked_reason,
        "readiness_reason": readiness_reason,
        "prompt340_result_path": str(prompt340_result_path),
        "prompt340_receipt_path": str(prompt340_receipt_path),
        "prompt340_plan_path": str(prompt340_plan_path),
        "prompt340_gate_state_path": str(prompt340_gate_state_path),
        "prompt340_status": prompt340_status,
        "prompt340_execution_status": prompt340_execution_status,
        "prompt340_commit_performed": prompt340_commit_performed,
        "prompt340_tag_performed": prompt340_tag_performed,
        "prompt340_commit_hash": prompt340_commit_hash,
        "prompt340_tag_name": prompt340_tag_name,
        "prompt340_tag_points_at_commit": prompt340_tag_points_at_commit,
        "current_head_hash": current_head_hash,
        "current_head_matches_prompt340_commit": current_head_matches_prompt340_commit,
        "prompt340_tag_resolves_to_commit": prompt340_tag_resolves_to_commit,
        "prompt340_tag_points_at_head": prompt340_tag_points_at_head,
        "prompt334_route_path": str(prompt334_route_path),
        "prompt334_outcome_path": str(prompt334_outcome_path),
        "prompt334_diff_capture_path": str(prompt334_diff_capture_path),
        "prompt334_no_change_route_match": prompt334_no_change_route_match,
        "prompt334_no_change_success_route": prompt334_no_change_success_route,
        "tracked_worktree_clean": tracked_worktree_clean,
        "staged_tracked_files": staged_tracked_files,
        "unstaged_tracked_files": unstaged_tracked_files,
        "changed_tracked_files": changed_tracked_files,
        "no_change_cycle_closure": no_change_cycle_closure,
        "commit_required": commit_required,
        "tag_required": tag_required,
        "local_commit_tag_complete": local_commit_tag_complete,
        "cycle_closed": cycle_closed,
        "completed_cycle": completed_cycle,
        "current_cycle": current_cycle,
        "next_cycle": next_cycle,
        "max_cycles": max_cycles,
        "next_action": next_action,
        "validation_errors": _normalize_string_list(validation_errors),
        **safety_fields,
    }
    decision_payload: dict[str, Any] = {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "post_commit_cycle_closure_decision_schema_version": (
            _LOCAL_POST_COMMIT_CYCLE_CLOSURE_DECISION_SCHEMA_VERSION
        ),
        "prompt_id": "prompt341",
        "status": status,
        "closure_status": closure_status,
        "blocked_reason": blocked_reason,
        "cycle_closed": cycle_closed,
        "no_change_cycle_closure": no_change_cycle_closure,
        "commit_required": commit_required,
        "tag_required": tag_required,
        "local_commit_tag_complete": local_commit_tag_complete,
        "cycle_decision": cycle_decision,
        "decision_reason": decision_reason,
        "reentry_allowed": reentry_allowed,
        "should_continue": should_continue,
        "completed_cycle": completed_cycle,
        "current_cycle": current_cycle,
        "next_cycle": next_cycle,
        "max_cycles": max_cycles,
        "cycle_commit_hash": cycle_commit_hash,
        "cycle_tag_name": cycle_tag_name,
        "next_action": next_action,
        "validation_errors": _normalize_string_list(validation_errors),
        **safety_fields,
    }
    receipt_payload: dict[str, Any] = {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "post_commit_cycle_closure_receipt_schema_version": (
            _LOCAL_POST_COMMIT_CYCLE_CLOSURE_RECEIPT_SCHEMA_VERSION
        ),
        "prompt_id": "prompt341",
        "status": status,
        "closure_status": closure_status,
        "blocked_reason": blocked_reason,
        "readiness_reason": readiness_reason,
        "closure_state_path": str(closure_state_path),
        "closure_decision_path": str(closure_decision_path),
        "reentry_decision_path": str(reentry_decision_path),
        "prompt340_result_path": str(prompt340_result_path),
        "prompt340_receipt_path": str(prompt340_receipt_path),
        "prompt334_route_path": str(prompt334_route_path),
        "prompt334_outcome_path": str(prompt334_outcome_path),
        "prompt334_diff_capture_path": str(prompt334_diff_capture_path),
        "no_change_cycle_closure": no_change_cycle_closure,
        "commit_required": commit_required,
        "tag_required": tag_required,
        "local_commit_tag_complete": local_commit_tag_complete,
        "cycle_closed": cycle_closed,
        "cycle_decision": cycle_decision,
        "reentry_allowed": reentry_allowed,
        "should_continue": should_continue,
        "completed_cycle": completed_cycle,
        "next_cycle": next_cycle,
        "max_cycles": max_cycles,
        "cycle_commit_hash": cycle_commit_hash,
        "cycle_tag_name": cycle_tag_name,
        "tracked_worktree_clean": tracked_worktree_clean,
        "next_action": next_action,
        "validation_errors": _normalize_string_list(validation_errors),
        **safety_fields,
    }
    reentry_payload: dict[str, Any] = {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "next_cycle_reentry_decision_schema_version": (
            _LOCAL_NEXT_CYCLE_REENTRY_DECISION_SCHEMA_VERSION
        ),
        "prompt_id": "prompt341",
        "status": status,
        "blocked_reason": blocked_reason,
        "reentry_status": reentry_status,
        "cycle_decision": cycle_decision,
        "decision_reason": decision_reason,
        "no_change_cycle_closure": no_change_cycle_closure,
        "commit_required": commit_required,
        "tag_required": tag_required,
        "reentry_allowed": reentry_allowed,
        "should_continue": should_continue,
        "completed_cycle": completed_cycle,
        "current_cycle": current_cycle,
        "next_cycle": next_cycle,
        "max_cycles": max_cycles,
        "previous_cycle_commit_hash": cycle_commit_hash,
        "previous_cycle_tag_name": cycle_tag_name,
        "next_selected_step_id": next_selected_step_id,
        "next_selected_step_name": next_selected_step_name,
        "next_selected_step_operation": next_selected_step_operation,
        "next_selected_step_authority_source": next_selected_step_authority_source,
        "next_action": next_action,
        "validation_errors": _normalize_string_list(validation_errors),
        **safety_fields,
    }

    try:
        one_cycle_controller_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    try:
        _write_json(closure_state_path, state_payload)
    except OSError:
        pass
    try:
        _write_json(closure_decision_path, decision_payload)
    except OSError:
        pass
    try:
        _write_json(closure_receipt_path, receipt_payload)
    except OSError:
        pass
    try:
        _write_json(reentry_decision_path, reentry_payload)
    except OSError:
        pass

    return {
        "local_post_commit_cycle_closure_status": status,
        "local_post_commit_cycle_closure_blocked_reason": blocked_reason,
        "local_post_commit_cycle_closure_cycle_closed": cycle_closed,
        "local_post_commit_cycle_closure_reentry_allowed": reentry_allowed,
        "local_post_commit_cycle_closure_should_continue": should_continue,
        "local_post_commit_cycle_closure_cycle_decision": cycle_decision,
        "local_post_commit_cycle_closure_next_action": next_action,
        "local_post_commit_cycle_closure_commit_hash": cycle_commit_hash,
        "local_post_commit_cycle_closure_tag_name": cycle_tag_name,
        "local_post_commit_cycle_closure_no_change_cycle_closure": no_change_cycle_closure,
        "local_post_commit_cycle_closure_commit_required": commit_required,
        "local_post_commit_cycle_closure_tag_required": tag_required,
        "local_post_commit_cycle_closure_local_commit_tag_complete": local_commit_tag_complete,
        "local_next_cycle_reentry_status": reentry_status,
        "local_next_cycle_reentry_next_action": next_action,
        "local_next_cycle_reentry_selected_step_name": next_selected_step_name,
        "local_post_commit_cycle_closure_state_path": str(closure_state_path),
        "local_post_commit_cycle_closure_decision_path": str(closure_decision_path),
        "local_post_commit_cycle_closure_receipt_path": str(closure_receipt_path),
        "local_next_cycle_reentry_decision_path": str(reentry_decision_path),
    }

def _build_local_autonomous_continuation_artifacts(
    *,
    execution_repo_path: str,
    one_cycle_controller_dir: Path,
) -> dict[str, Any]:
    def _as_boolish(value: Any, *, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        text = _normalize_text(value, default="").strip().lower()
        if text in {"1", "true", "yes", "on", "enabled"}:
            return True
        if text in {"0", "false", "no", "off", "disabled"}:
            return False
        return default

    def _read_json_mapping(path: Path) -> tuple[bool, bool, dict[str, Any]]:
        if not path.exists():
            return False, False, {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return True, False, {}
        if not isinstance(payload, Mapping):
            return True, False, {}
        return True, True, dict(payload)

    def _run_local_git(
        repo_path: str,
        args: list[str],
        *,
        timeout_seconds: float,
    ) -> tuple[bool, subprocess.CompletedProcess[str] | None]:
        try:
            completed = subprocess.run(
                ["git", "-C", repo_path, *args],
                text=True,
                capture_output=True,
                check=False,
                timeout=timeout_seconds,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False, None
        return True, completed

    def _collect_tracked_diff_state(
        repo_path: str,
    ) -> tuple[bool, bool, list[str], list[str], list[str]]:
        status_ok, status_short = _run_local_git(
            repo_path,
            ["status", "--short", "--untracked-files=no"],
            timeout_seconds=10,
        )
        unstaged_ok, unstaged_names = _run_local_git(
            repo_path,
            ["diff", "--name-only"],
            timeout_seconds=10,
        )
        staged_ok, staged_names = _run_local_git(
            repo_path,
            ["diff", "--cached", "--name-only"],
            timeout_seconds=10,
        )
        if (
            not status_ok
            or not unstaged_ok
            or not staged_ok
            or status_short is None
            or unstaged_names is None
            or staged_names is None
        ):
            return False, False, [], [], []
        if (
            status_short.returncode != 0
            or unstaged_names.returncode != 0
            or staged_names.returncode != 0
        ):
            return False, False, [], [], []

        status_paths = sorted(
            {
                _parse_git_status_path(line)
                for line in (status_short.stdout or "").splitlines()
                if line.strip() and _parse_git_status_path(line)
            }
        )
        unstaged = sorted(
            {
                _normalize_text(line, default="").strip()
                for line in (unstaged_names.stdout or "").splitlines()
                if _normalize_text(line, default="").strip()
            }
        )
        staged = sorted(
            {
                _normalize_text(line, default="").strip()
                for line in (staged_names.stdout or "").splitlines()
                if _normalize_text(line, default="").strip()
            }
        )
        changed = sorted(set(status_paths) | set(unstaged) | set(staged))
        tracked_worktree_clean = bool(not changed and not staged and not unstaged)
        return True, tracked_worktree_clean, changed, staged, unstaged

    def _safety_fields() -> dict[str, Any]:
        return {
            "codex_invoked": False,
            "codex_invocation_allowed": False,
            "execution_allowed": False,
            "targeted_fix_execution_allowed": False,
            "commit_allowed": False,
            "tag_allowed": False,
            "push_pr_merge_enabled": False,
            "rollback_allowed": False,
            "commit_performed": False,
            "tag_performed": False,
            "push_performed": False,
            "pr_created": False,
            "merge_performed": False,
            "rollback_performed": False,
        }

    one_cycle_controller_dir = Path(one_cycle_controller_dir)
    prompt341_closure_state_path = one_cycle_controller_dir / "local_post_commit_cycle_closure_state.json"
    prompt341_closure_decision_path = (
        one_cycle_controller_dir / "local_post_commit_cycle_closure_decision.json"
    )
    prompt341_closure_receipt_path = (
        one_cycle_controller_dir / "local_post_commit_cycle_closure_receipt.json"
    )
    prompt341_reentry_decision_path = one_cycle_controller_dir / "local_next_cycle_reentry_decision.json"
    prompt340_execution_receipt_path = (
        one_cycle_controller_dir / "local_bounded_approve_commit_tag_execution_receipt.json"
    )
    prompt340_execution_result_path = (
        one_cycle_controller_dir / "local_bounded_approve_commit_tag_execution_result.json"
    )
    prompt339_route_decision_path = (
        one_cycle_controller_dir / "local_post_targeted_contract_fix_route_decision.json"
    )
    prompt338_execution_result_path = (
        one_cycle_controller_dir / "local_targeted_contract_fix_execution_result.json"
    )
    cycle_v2_state_path = one_cycle_controller_dir / "local_autonomous_cycle_v2_state.json"
    cycle_v2_decision_path = one_cycle_controller_dir / "local_autonomous_cycle_v2_decision.json"
    cycle_v2_receipt_path = one_cycle_controller_dir / "local_autonomous_cycle_v2_receipt.json"

    continuation_state_path = one_cycle_controller_dir / "local_autonomous_continuation_state.json"
    continuation_decision_path = one_cycle_controller_dir / "local_autonomous_continuation_decision.json"
    continuation_receipt_path = one_cycle_controller_dir / "local_autonomous_continuation_receipt.json"
    next_cycle_selection_path = one_cycle_controller_dir / "local_autonomous_next_cycle_selection.json"
    loop_completion_summary_path = one_cycle_controller_dir / "local_autonomous_loop_completion_summary.json"

    prompt341_closure_state_exists, prompt341_closure_state_valid, prompt341_closure_state_payload = (
        _read_json_mapping(prompt341_closure_state_path)
    )
    (
        prompt341_closure_decision_exists,
        prompt341_closure_decision_valid,
        prompt341_closure_decision_payload,
    ) = _read_json_mapping(prompt341_closure_decision_path)
    (
        prompt341_closure_receipt_exists,
        prompt341_closure_receipt_valid,
        prompt341_closure_receipt_payload,
    ) = _read_json_mapping(prompt341_closure_receipt_path)
    (
        prompt341_reentry_decision_exists,
        prompt341_reentry_decision_valid,
        prompt341_reentry_decision_payload,
    ) = _read_json_mapping(prompt341_reentry_decision_path)
    _ = _read_json_mapping(prompt340_execution_receipt_path)
    _ = _read_json_mapping(prompt340_execution_result_path)
    _ = _read_json_mapping(prompt339_route_decision_path)
    _ = _read_json_mapping(prompt338_execution_result_path)
    cycle_v2_state_exists, cycle_v2_state_valid, cycle_v2_state_payload = _read_json_mapping(
        cycle_v2_state_path
    )
    cycle_v2_decision_exists, cycle_v2_decision_valid, cycle_v2_decision_payload = _read_json_mapping(
        cycle_v2_decision_path
    )
    cycle_v2_receipt_exists, cycle_v2_receipt_valid, cycle_v2_receipt_payload = _read_json_mapping(
        cycle_v2_receipt_path
    )

    prompt341_status = _normalize_text(prompt341_closure_decision_payload.get("status"), default="")
    prompt341_closure_status = _normalize_text(
        prompt341_closure_decision_payload.get("closure_status"),
        default="",
    )
    prompt341_cycle_closed = _as_boolish(
        prompt341_closure_decision_payload.get("cycle_closed"),
        default=False,
    )
    prompt341_reentry_allowed = _as_boolish(
        prompt341_reentry_decision_payload.get("reentry_allowed"),
        default=False,
    )
    prompt341_should_continue = _as_boolish(
        prompt341_reentry_decision_payload.get("should_continue"),
        default=False,
    )
    prompt341_cycle_decision = _normalize_text(
        prompt341_reentry_decision_payload.get("cycle_decision"),
        default="",
    )
    prompt341_no_change_cycle_closure = _as_boolish(
        prompt341_closure_decision_payload.get("no_change_cycle_closure"),
        default=False,
    )
    prompt341_commit_required = _as_boolish(
        prompt341_closure_decision_payload.get("commit_required"),
        default=True,
    )
    prompt341_tag_required = _as_boolish(
        prompt341_closure_decision_payload.get("tag_required"),
        default=True,
    )

    completed_cycle = _LOCAL_AUTONOMOUS_CYCLE_V2_CURRENT_CYCLE
    current_cycle = _LOCAL_AUTONOMOUS_CYCLE_V2_CURRENT_CYCLE
    max_cycles = _LOCAL_AUTONOMOUS_CYCLE_V2_MAX_CYCLES
    next_cycle = _LOCAL_AUTONOMOUS_CYCLE_V2_CURRENT_CYCLE + 1
    for exists, valid, payload in (
        (prompt341_closure_decision_exists, prompt341_closure_decision_valid, prompt341_closure_decision_payload),
        (prompt341_reentry_decision_exists, prompt341_reentry_decision_valid, prompt341_reentry_decision_payload),
        (cycle_v2_state_exists, cycle_v2_state_valid, cycle_v2_state_payload),
        (cycle_v2_decision_exists, cycle_v2_decision_valid, cycle_v2_decision_payload),
        (cycle_v2_receipt_exists, cycle_v2_receipt_valid, cycle_v2_receipt_payload),
    ):
        if not exists or not valid:
            continue
        completed_cycle = _as_non_negative_int(
            payload.get("completed_cycle"),
            default=completed_cycle,
        )
        current_cycle = _as_non_negative_int(
            payload.get("current_cycle"),
            default=current_cycle,
        )
        max_cycles = _as_non_negative_int(payload.get("max_cycles"), default=max_cycles)
        next_cycle = _as_non_negative_int(payload.get("next_cycle"), default=next_cycle)
        if current_cycle <= 0:
            current_cycle = _LOCAL_AUTONOMOUS_CYCLE_V2_CURRENT_CYCLE
        if completed_cycle <= 0:
            completed_cycle = current_cycle
        if max_cycles <= 0:
            max_cycles = _LOCAL_AUTONOMOUS_CYCLE_V2_MAX_CYCLES
        if next_cycle <= 0:
            next_cycle = current_cycle + 1
        break

    validation_errors: list[str] = []
    prompt341_closure_reentry_ready = True

    if not prompt341_closure_state_exists:
        prompt341_closure_reentry_ready = False
        validation_errors.append("missing_prompt341_closure_state_artifact")
    elif not prompt341_closure_state_valid:
        prompt341_closure_reentry_ready = False
        validation_errors.append("invalid_prompt341_closure_state_artifact")

    if not prompt341_closure_decision_exists:
        prompt341_closure_reentry_ready = False
        validation_errors.append("missing_prompt341_closure_decision_artifact")
    elif not prompt341_closure_decision_valid:
        prompt341_closure_reentry_ready = False
        validation_errors.append("invalid_prompt341_closure_decision_artifact")
    else:
        closure_decision_expectations: tuple[tuple[str, Any], ...] = (
            ("schema_version", _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION),
            ("status", "completed"),
            ("closure_status", "completed"),
            ("blocked_reason", "none"),
            ("cycle_closed", True),
            ("local_commit_tag_complete", True),
        )
        for key, expected in closure_decision_expectations:
            value = prompt341_closure_decision_payload.get(key)
            if isinstance(expected, bool):
                if _as_boolish(value, default=not expected) != expected:
                    prompt341_closure_reentry_ready = False
                    validation_errors.append(f"prompt341_closure_decision_{key}_mismatch")
            else:
                if _normalize_text(value, default="") != expected:
                    prompt341_closure_reentry_ready = False
                    validation_errors.append(f"prompt341_closure_decision_{key}_mismatch")
        closure_decision_commit_hash = _normalize_text(
            prompt341_closure_decision_payload.get("cycle_commit_hash"),
            default="",
        )
        closure_decision_tag_name = _normalize_text(
            prompt341_closure_decision_payload.get("cycle_tag_name"),
            default="",
        )
        if prompt341_commit_required and not closure_decision_commit_hash:
            prompt341_closure_reentry_ready = False
            validation_errors.append("prompt341_closure_decision_cycle_commit_hash_missing")
        if prompt341_tag_required and not closure_decision_tag_name:
            prompt341_closure_reentry_ready = False
            validation_errors.append("prompt341_closure_decision_cycle_tag_name_missing")
        if prompt341_no_change_cycle_closure:
            if prompt341_commit_required or prompt341_tag_required:
                prompt341_closure_reentry_ready = False
                validation_errors.append(
                    "prompt341_closure_decision_no_change_commit_tag_requirement_mismatch"
                )
        else:
            if (not prompt341_commit_required) or (not prompt341_tag_required):
                prompt341_closure_reentry_ready = False
                validation_errors.append(
                    "prompt341_closure_decision_commit_tag_requirement_mismatch"
                )
        if _normalize_string_list(prompt341_closure_decision_payload.get("validation_errors")):
            prompt341_closure_reentry_ready = False
            validation_errors.append("prompt341_closure_decision_validation_errors_present")

    cycle_commit_hash = _normalize_text(prompt341_closure_decision_payload.get("cycle_commit_hash"), default="")
    cycle_tag_name = _normalize_text(prompt341_closure_decision_payload.get("cycle_tag_name"), default="")
    local_commit_tag_complete = _as_boolish(
        prompt341_closure_decision_payload.get("local_commit_tag_complete"),
        default=False,
    )

    if not prompt341_closure_receipt_exists:
        prompt341_closure_reentry_ready = False
        validation_errors.append("missing_prompt341_closure_receipt_artifact")
    elif not prompt341_closure_receipt_valid:
        prompt341_closure_reentry_ready = False
        validation_errors.append("invalid_prompt341_closure_receipt_artifact")
    else:
        closure_receipt_expectations: tuple[tuple[str, Any], ...] = (
            ("status", "completed"),
            ("closure_status", "completed"),
            ("blocked_reason", "none"),
            ("local_commit_tag_complete", True),
            ("cycle_closed", True),
            ("tracked_worktree_clean", True),
        )
        for key, expected in closure_receipt_expectations:
            value = prompt341_closure_receipt_payload.get(key)
            if isinstance(expected, bool):
                if _as_boolish(value, default=not expected) != expected:
                    prompt341_closure_reentry_ready = False
                    validation_errors.append(f"prompt341_closure_receipt_{key}_mismatch")
            else:
                if _normalize_text(value, default="") != expected:
                    prompt341_closure_reentry_ready = False
                    validation_errors.append(f"prompt341_closure_receipt_{key}_mismatch")
        receipt_cycle_commit_hash = _normalize_text(
            prompt341_closure_receipt_payload.get("cycle_commit_hash"),
            default="",
        )
        receipt_cycle_tag_name = _normalize_text(
            prompt341_closure_receipt_payload.get("cycle_tag_name"),
            default="",
        )
        receipt_no_change_cycle_closure = _as_boolish(
            prompt341_closure_receipt_payload.get("no_change_cycle_closure"),
            default=False,
        )
        receipt_commit_required = _as_boolish(
            prompt341_closure_receipt_payload.get("commit_required"),
            default=True,
        )
        receipt_tag_required = _as_boolish(
            prompt341_closure_receipt_payload.get("tag_required"),
            default=True,
        )
        if receipt_no_change_cycle_closure != prompt341_no_change_cycle_closure:
            prompt341_closure_reentry_ready = False
            validation_errors.append("prompt341_closure_receipt_no_change_cycle_closure_mismatch")
        if receipt_commit_required != prompt341_commit_required:
            prompt341_closure_reentry_ready = False
            validation_errors.append("prompt341_closure_receipt_commit_required_mismatch")
        if receipt_tag_required != prompt341_tag_required:
            prompt341_closure_reentry_ready = False
            validation_errors.append("prompt341_closure_receipt_tag_required_mismatch")
        if prompt341_commit_required and receipt_cycle_commit_hash != cycle_commit_hash:
            prompt341_closure_reentry_ready = False
            validation_errors.append("prompt341_closure_receipt_cycle_commit_hash_mismatch")
        if prompt341_tag_required and receipt_cycle_tag_name != cycle_tag_name:
            prompt341_closure_reentry_ready = False
            validation_errors.append("prompt341_closure_receipt_cycle_tag_name_mismatch")
        if (not prompt341_commit_required) and _normalize_text(receipt_cycle_commit_hash, default=""):
            prompt341_closure_reentry_ready = False
            validation_errors.append("prompt341_closure_receipt_cycle_commit_hash_unexpected")
        if (not prompt341_tag_required) and _normalize_text(receipt_cycle_tag_name, default=""):
            prompt341_closure_reentry_ready = False
            validation_errors.append("prompt341_closure_receipt_cycle_tag_name_unexpected")
        if _normalize_string_list(prompt341_closure_receipt_payload.get("validation_errors")):
            prompt341_closure_reentry_ready = False
            validation_errors.append("prompt341_closure_receipt_validation_errors_present")

    if not prompt341_reentry_decision_exists:
        prompt341_closure_reentry_ready = False
        validation_errors.append("missing_prompt341_reentry_decision_artifact")
    elif not prompt341_reentry_decision_valid:
        prompt341_closure_reentry_ready = False
        validation_errors.append("invalid_prompt341_reentry_decision_artifact")
    else:
        reentry_expectations: tuple[tuple[str, Any], ...] = (
            ("schema_version", _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION),
            ("status", "completed"),
            ("blocked_reason", "none"),
        )
        for key, expected in reentry_expectations:
            value = prompt341_reentry_decision_payload.get(key)
            if isinstance(expected, bool):
                if _as_boolish(value, default=not expected) != expected:
                    prompt341_closure_reentry_ready = False
                    validation_errors.append(f"prompt341_reentry_decision_{key}_mismatch")
            else:
                if _normalize_text(value, default="") != expected:
                    prompt341_closure_reentry_ready = False
                    validation_errors.append(f"prompt341_reentry_decision_{key}_mismatch")
        reentry_status_value = _normalize_text(
            prompt341_reentry_decision_payload.get("reentry_status"),
            default="",
        )
        if reentry_status_value not in {"completed", "ready", "ready_for_reentry", "bounded_cycle_limit_reached"}:
            prompt341_closure_reentry_ready = False
            validation_errors.append("prompt341_reentry_decision_reentry_status_mismatch")
        if _normalize_string_list(prompt341_reentry_decision_payload.get("validation_errors")):
            prompt341_closure_reentry_ready = False
            validation_errors.append("prompt341_reentry_decision_validation_errors_present")

    normalized_repo_path = _normalize_text(
        execution_repo_path,
        default=_APPROVE_COMMIT_TAG_EXECUTION_REPO_PATH,
    )
    current_head_hash = ""
    tracked_worktree_clean = False
    staged_tracked_files: list[str] = []
    unstaged_tracked_files: list[str] = []
    changed_tracked_files: list[str] = []
    git_verification_ok = False

    head_ok, head_completed = _run_local_git(
        normalized_repo_path,
        ["rev-parse", "HEAD"],
        timeout_seconds=10,
    )
    diff_ok, tracked_worktree_clean, changed_tracked_files, staged_tracked_files, unstaged_tracked_files = (
        _collect_tracked_diff_state(normalized_repo_path)
    )
    if head_ok and isinstance(head_completed, subprocess.CompletedProcess) and head_completed.returncode == 0:
        current_head_hash = _normalize_text(head_completed.stdout, default="")
    else:
        validation_errors.append("prompt342_head_lookup_failed")
    if not diff_ok:
        validation_errors.append("prompt342_tracked_worktree_state_lookup_failed")
    git_verification_ok = bool(
        current_head_hash
        and diff_ok
        and tracked_worktree_clean
        and not staged_tracked_files
        and not unstaged_tracked_files
    )

    status = "blocked"
    continuation_status = "blocked"
    blocked_reason = "prompt341_cycle_closure_reentry_not_ready"
    readiness_reason = "prompt341_cycle_closure_reentry_not_ready"
    reentry_connected = False
    next_cycle_ready = False
    local_autonomous_loop_complete = False
    local_only_complete_autonomous_loop_ready = False
    selected_next_cycle: int | None = None
    selected_step_id: int | None = None
    selected_step_name = ""
    selected_step_operation = ""
    selected_step_authority_source = ""
    next_action = "manual_review_prompt341_cycle_closure_reentry"
    decision_reason = "prompt341_cycle_closure_reentry_not_ready"
    selection_status = "blocked"
    selection_reason = "prompt341_cycle_closure_reentry_not_ready"
    final_decision = "manual_review_prompt341_cycle_closure_reentry"

    reentry_allowed = _as_boolish(prompt341_reentry_decision_payload.get("reentry_allowed"), default=False)
    should_continue = _as_boolish(prompt341_reentry_decision_payload.get("should_continue"), default=False)
    cycle_decision = _normalize_text(prompt341_reentry_decision_payload.get("cycle_decision"), default="")
    reentry_next_action = _normalize_text(prompt341_reentry_decision_payload.get("next_action"), default="")
    selected_next_cycle_value = _as_non_negative_int(
        prompt341_reentry_decision_payload.get("next_cycle"),
        default=next_cycle,
    )

    if prompt341_closure_reentry_ready:
        if prompt341_closure_status == "completed" and not tracked_worktree_clean:
            blocked_reason = "post_closure_tracked_worktree_not_clean"
            readiness_reason = "post_closure_tracked_worktree_not_clean"
            next_action = "manual_review_post_closure_worktree_state"
            decision_reason = "post_closure_tracked_worktree_not_clean"
            selection_status = "blocked"
            selection_reason = "post_closure_tracked_worktree_not_clean"
            final_decision = "post_closure_tracked_worktree_not_clean"
            validation_errors.append("prompt342_post_closure_tracked_worktree_not_clean")
        elif (
            reentry_allowed
            and should_continue
            and cycle_decision == "continue_next_local_autonomous_cycle"
            and reentry_next_action == "select_next_local_autonomous_step"
            and git_verification_ok
        ):
            status = "completed"
            continuation_status = "ready"
            blocked_reason = "none"
            readiness_reason = "prompt342_reentry_connected_to_next_cycle_selection"
            reentry_connected = True
            next_cycle_ready = True
            local_autonomous_loop_complete = False
            local_only_complete_autonomous_loop_ready = True
            selected_next_cycle = selected_next_cycle_value if selected_next_cycle_value > 0 else next_cycle
            selected_step_id = 1
            selected_step_name = "read_current_state"
            selected_step_operation = "read_current_state"
            selected_step_authority_source = "prompt342_autonomous_continuation_connector"
            next_action = "run_next_local_autonomous_cycle_step"
            decision_reason = "prompt341_reentry_continue_validated"
            selection_status = "completed"
            selection_reason = "deterministic_next_step_selected"
            final_decision = "continue_next_local_autonomous_cycle"
        elif (
            (not reentry_allowed)
            and (not should_continue)
            and cycle_decision == "bounded_cycle_limit_reached"
            and reentry_next_action == "local_autonomous_loop_complete"
        ):
            status = "completed"
            continuation_status = "complete"
            blocked_reason = "none"
            readiness_reason = "prompt342_bounded_cycle_limit_completion_validated"
            reentry_connected = False
            next_cycle_ready = False
            local_autonomous_loop_complete = True
            local_only_complete_autonomous_loop_ready = True
            selected_next_cycle = None
            selected_step_id = None
            selected_step_name = ""
            selected_step_operation = ""
            selected_step_authority_source = ""
            next_action = "local_only_autonomous_loop_complete"
            decision_reason = "prompt341_bounded_cycle_limit_reached"
            selection_status = "not_applicable"
            selection_reason = "bounded_cycle_limit_reached"
            final_decision = "bounded_cycle_limit_reached"
        else:
            validation_errors.append("prompt342_prompt341_reentry_contract_mismatch")
            decision_reason = "prompt341_reentry_contract_mismatch"
            selection_reason = "prompt341_reentry_contract_mismatch"
            final_decision = "prompt341_reentry_contract_mismatch"

    if not prompt341_closure_reentry_ready:
        validation_errors.append("prompt342_prompt341_closure_reentry_not_ready")

    if status == "completed" and continuation_status == "ready":
        selected_next_cycle = selected_next_cycle if isinstance(selected_next_cycle, int) else next_cycle

    included_local_only_capabilities = [
        "next_prompt_or_step_selection",
        "prompt_generation_or_handoff",
        "codex_execution",
        "post_execution_review_route",
        "targeted_fix_prompt_generation",
        "targeted_fix_execution",
        "post_targeted_fix_review_route",
        "approve_commit_tag_execution",
        "post_commit_cycle_closure",
        "next_cycle_reentry",
    ]
    excluded_remote_capabilities = [
        "remote_push",
        "pr_create",
        "pr_merge",
        "remote_rollback",
        "real_background_daemon",
        "external_scheduler",
    ]
    safety_fields = _safety_fields()

    state_payload: dict[str, Any] = {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "autonomous_continuation_state_schema_version": (
            _LOCAL_AUTONOMOUS_CONTINUATION_STATE_SCHEMA_VERSION
        ),
        "prompt_id": "prompt342",
        "status": status,
        "continuation_status": continuation_status,
        "blocked_reason": blocked_reason,
        "readiness_reason": readiness_reason,
        "prompt341_closure_state_path": str(prompt341_closure_state_path),
        "prompt341_closure_decision_path": str(prompt341_closure_decision_path),
        "prompt341_closure_receipt_path": str(prompt341_closure_receipt_path),
        "prompt341_reentry_decision_path": str(prompt341_reentry_decision_path),
        "prompt341_status": prompt341_status,
        "prompt341_closure_status": prompt341_closure_status,
        "prompt341_cycle_closed": prompt341_cycle_closed,
        "prompt341_reentry_allowed": prompt341_reentry_allowed,
        "prompt341_should_continue": prompt341_should_continue,
        "prompt341_cycle_decision": prompt341_cycle_decision,
        "prompt341_no_change_cycle_closure": prompt341_no_change_cycle_closure,
        "prompt341_commit_required": prompt341_commit_required,
        "prompt341_tag_required": prompt341_tag_required,
        "completed_cycle": completed_cycle,
        "current_cycle": current_cycle,
        "next_cycle": next_cycle,
        "max_cycles": max_cycles,
        "selected_next_cycle": selected_next_cycle,
        "current_head_hash": current_head_hash,
        "tracked_worktree_clean": tracked_worktree_clean,
        "staged_tracked_files": staged_tracked_files,
        "unstaged_tracked_files": unstaged_tracked_files,
        "changed_tracked_files": changed_tracked_files,
        "no_change_cycle_closure": prompt341_no_change_cycle_closure,
        "commit_required": prompt341_commit_required,
        "tag_required": prompt341_tag_required,
        "local_commit_tag_complete": local_commit_tag_complete,
        "cycle_commit_hash": cycle_commit_hash,
        "cycle_tag_name": cycle_tag_name,
        "reentry_connected": reentry_connected,
        "next_cycle_ready": next_cycle_ready,
        "local_autonomous_loop_complete": local_autonomous_loop_complete,
        "local_only_complete_autonomous_loop_ready": (
            local_only_complete_autonomous_loop_ready
        ),
        "selected_step_id": selected_step_id,
        "selected_step_name": selected_step_name,
        "selected_step_operation": selected_step_operation,
        "selected_step_authority_source": selected_step_authority_source,
        "next_action": next_action,
        "validation_errors": _normalize_string_list(validation_errors),
        **safety_fields,
    }
    decision_payload: dict[str, Any] = {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "autonomous_continuation_decision_schema_version": (
            _LOCAL_AUTONOMOUS_CONTINUATION_DECISION_SCHEMA_VERSION
        ),
        "prompt_id": "prompt342",
        "status": status,
        "continuation_status": continuation_status,
        "blocked_reason": blocked_reason,
        "decision_reason": decision_reason,
        "no_change_cycle_closure": prompt341_no_change_cycle_closure,
        "commit_required": prompt341_commit_required,
        "tag_required": prompt341_tag_required,
        "local_only_complete_autonomous_loop_ready": (
            local_only_complete_autonomous_loop_ready
        ),
        "local_autonomous_loop_complete": local_autonomous_loop_complete,
        "reentry_connected": reentry_connected,
        "next_cycle_ready": next_cycle_ready,
        "selected_next_cycle": selected_next_cycle,
        "completed_cycle": completed_cycle,
        "current_cycle": current_cycle,
        "next_cycle": next_cycle,
        "max_cycles": max_cycles,
        "cycle_decision": cycle_decision,
        "selected_step_id": selected_step_id,
        "selected_step_name": selected_step_name,
        "selected_step_operation": selected_step_operation,
        "selected_step_authority_source": selected_step_authority_source,
        "next_action": next_action,
        "validation_errors": _normalize_string_list(validation_errors),
        **safety_fields,
    }
    receipt_payload: dict[str, Any] = {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "autonomous_continuation_receipt_schema_version": (
            _LOCAL_AUTONOMOUS_CONTINUATION_RECEIPT_SCHEMA_VERSION
        ),
        "prompt_id": "prompt342",
        "status": status,
        "continuation_status": continuation_status,
        "blocked_reason": blocked_reason,
        "readiness_reason": readiness_reason,
        "continuation_state_path": str(continuation_state_path),
        "continuation_decision_path": str(continuation_decision_path),
        "next_cycle_selection_path": str(next_cycle_selection_path),
        "loop_completion_summary_path": str(loop_completion_summary_path),
        "prompt341_closure_decision_path": str(prompt341_closure_decision_path),
        "prompt341_reentry_decision_path": str(prompt341_reentry_decision_path),
        "no_change_cycle_closure": prompt341_no_change_cycle_closure,
        "commit_required": prompt341_commit_required,
        "tag_required": prompt341_tag_required,
        "local_only_complete_autonomous_loop_ready": (
            local_only_complete_autonomous_loop_ready
        ),
        "local_autonomous_loop_complete": local_autonomous_loop_complete,
        "reentry_connected": reentry_connected,
        "next_cycle_ready": next_cycle_ready,
        "selected_next_cycle": selected_next_cycle,
        "selected_step_name": selected_step_name,
        "selected_step_operation": selected_step_operation,
        "cycle_commit_hash": cycle_commit_hash,
        "cycle_tag_name": cycle_tag_name,
        "next_action": next_action,
        "validation_errors": _normalize_string_list(validation_errors),
        **safety_fields,
    }
    next_cycle_selection_payload: dict[str, Any] = {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "autonomous_next_cycle_selection_schema_version": (
            _LOCAL_AUTONOMOUS_NEXT_CYCLE_SELECTION_SCHEMA_VERSION
        ),
        "prompt_id": "prompt342",
        "status": status,
        "blocked_reason": blocked_reason,
        "selection_status": selection_status,
        "selected_next_cycle": selected_next_cycle,
        "selected_step_id": selected_step_id,
        "selected_step_name": selected_step_name,
        "selected_step_operation": selected_step_operation,
        "selected_step_authority_source": selected_step_authority_source,
        "selection_reason": selection_reason,
        "next_action": next_action,
        "validation_errors": _normalize_string_list(validation_errors),
        **safety_fields,
    }
    loop_completion_summary_payload: dict[str, Any] = {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "autonomous_loop_completion_summary_schema_version": (
            _LOCAL_AUTONOMOUS_LOOP_COMPLETION_SUMMARY_SCHEMA_VERSION
        ),
        "prompt_id": "prompt342",
        "status": status,
        "continuation_status": continuation_status,
        "blocked_reason": blocked_reason,
        "no_change_cycle_closure": prompt341_no_change_cycle_closure,
        "commit_required": prompt341_commit_required,
        "tag_required": prompt341_tag_required,
        "local_only_complete_autonomous_loop_ready": (
            local_only_complete_autonomous_loop_ready
        ),
        "local_autonomous_loop_complete": local_autonomous_loop_complete,
        "completed_cycle": completed_cycle,
        "next_cycle": next_cycle,
        "max_cycles": max_cycles,
        "cycle_commit_hash": cycle_commit_hash,
        "cycle_tag_name": cycle_tag_name,
        "final_decision": final_decision,
        "next_action": next_action,
        "included_local_only_capabilities": included_local_only_capabilities,
        "excluded_remote_capabilities": excluded_remote_capabilities,
        "validation_errors": _normalize_string_list(validation_errors),
        **safety_fields,
    }

    try:
        one_cycle_controller_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    try:
        _write_json(continuation_state_path, state_payload)
    except OSError:
        pass
    try:
        _write_json(continuation_decision_path, decision_payload)
    except OSError:
        pass
    try:
        _write_json(continuation_receipt_path, receipt_payload)
    except OSError:
        pass
    try:
        _write_json(next_cycle_selection_path, next_cycle_selection_payload)
    except OSError:
        pass
    try:
        _write_json(loop_completion_summary_path, loop_completion_summary_payload)
    except OSError:
        pass

    return {
        "local_autonomous_continuation_status": status,
        "local_autonomous_continuation_blocked_reason": blocked_reason,
        "local_autonomous_continuation_next_action": next_action,
        "local_autonomous_continuation_reentry_connected": reentry_connected,
        "local_autonomous_continuation_next_cycle_ready": next_cycle_ready,
        "local_autonomous_continuation_selected_step_name": selected_step_name,
        "local_autonomous_loop_completion_status": continuation_status,
        "local_autonomous_loop_completion_final_decision": final_decision,
        "local_only_complete_autonomous_loop_ready": (
            local_only_complete_autonomous_loop_ready
        ),
        "local_autonomous_loop_complete": local_autonomous_loop_complete,
        "local_autonomous_continuation_no_change_cycle_closure": (
            prompt341_no_change_cycle_closure
        ),
        "local_autonomous_continuation_commit_required": prompt341_commit_required,
        "local_autonomous_continuation_tag_required": prompt341_tag_required,
        "local_autonomous_continuation_state_path": str(continuation_state_path),
        "local_autonomous_continuation_decision_path": str(continuation_decision_path),
        "local_autonomous_continuation_receipt_path": str(continuation_receipt_path),
        "local_autonomous_next_cycle_selection_path": str(next_cycle_selection_path),
        "local_autonomous_loop_completion_summary_path": str(loop_completion_summary_path),
    }

def _planning_artifact_bundle_has_complete_objective(
    bundle: Mapping[str, Any] | None,
) -> bool:
    payload = dict(bundle or {})
    project_brief = (
        dict(payload.get("project_brief"))
        if isinstance(payload.get("project_brief"), Mapping)
        else {}
    )
    pr_plan = (
        dict(payload.get("pr_plan"))
        if isinstance(payload.get("pr_plan"), Mapping)
        else {}
    )
    roadmap = (
        dict(payload.get("roadmap"))
        if isinstance(payload.get("roadmap"), Mapping)
        else {}
    )
    prs = pr_plan.get("prs") if isinstance(pr_plan.get("prs"), list) else []
    first_pr = prs[0] if prs and isinstance(prs[0], Mapping) else {}
    roadmap_items = roadmap.get("items") if isinstance(roadmap.get("items"), list) else []

    return all(
        [
            bool(_normalize_text(project_brief.get("objective"), default="")),
            bool(_normalize_text(project_brief.get("success_definition"), default="")),
            bool(_normalize_text(project_brief.get("target_repo"), default="")),
            bool(_normalize_text(project_brief.get("target_branch"), default="")),
            bool(_normalize_text(first_pr.get("pr_id"), default="")),
            bool(_normalize_text(first_pr.get("exact_scope"), default="")),
            bool(_normalize_string_list(first_pr.get("touched_files"), sort_items=False)),
            bool(_normalize_string_list(first_pr.get("forbidden_files"), sort_items=False)),
            bool(_normalize_string_list(first_pr.get("acceptance_criteria"), sort_items=False)),
            bool(_normalize_string_list(first_pr.get("validation_commands"), sort_items=False)),
            bool(roadmap_items),
        ]
    )

def _is_one_cycle_controller_local_artifacts_dir(artifacts_dir: Path) -> bool:
    try:
        resolved = artifacts_dir.resolve()
    except OSError:
        resolved = artifacts_dir
    return resolved in {
        Path("/tmp/codex-local-runner-decision/one_cycle_controller").resolve(),
        Path("/tmp/codex-local-runner-decision/artifacts").resolve(),
    }

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
    _normalize_string_list,
    _normalize_text,
    _write_json,
)

def _build_selected_step_execution_result_route_capture_state(
    *,
    gate_path: Path,
    result_path: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    normalized_repo_path = _APPROVE_COMMIT_TAG_EXECUTION_REPO_PATH
    status_short_cmd = subprocess.run(
        ["git", "status", "--short", "--untracked-files=no"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    metadata_collection_ok = status_short_cmd.returncode == 0
    changed_tracked_files = (
        [
            line.rstrip()
            for line in (status_short_cmd.stdout or "").splitlines()
            if line.strip()
        ]
        if metadata_collection_ok
        else []
    )
    worktree_clean = bool(metadata_collection_ok and (not changed_tracked_files))

    def _read_artifact_payload(path: Path) -> tuple[bool, bool, dict[str, Any]]:
        exists = path.exists()
        if not exists:
            return False, False, {}
        try:
            raw_payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            return True, False, {}
        if not isinstance(raw_payload, Mapping):
            return True, False, {}
        return True, True, dict(raw_payload)

    gate_present, gate_valid, gate = _read_artifact_payload(gate_path)
    result_present, result_valid, result = _read_artifact_payload(result_path)
    receipt_present, receipt_valid, receipt = _read_artifact_payload(receipt_path)

    required_artifacts_present = bool(gate_present and result_present and receipt_present)
    required_artifacts_valid = bool(gate_valid and result_valid and receipt_valid)

    selected_step_id = _as_non_negative_int(
        result.get("selected_step_id"),
        default=_as_non_negative_int(
            receipt.get("selected_step_id"),
            default=_as_non_negative_int(gate.get("selected_step_id"), default=1),
        ),
    )
    if selected_step_id <= 0:
        selected_step_id = 1
    selected_step_name = _normalize_text(
        result.get("selected_step_name"),
        default=_normalize_text(
            receipt.get("selected_step_name"),
            default=_normalize_text(gate.get("selected_step_name"), default="read_current_state"),
        ),
    )
    selected_step_operation = _normalize_text(
        result.get("selected_step_operation"),
        default=_normalize_text(
            receipt.get("selected_step_operation"),
            default=_normalize_text(gate.get("selected_step_operation"), default="read_current_state"),
        ),
    )
    if not selected_step_name:
        selected_step_name = "read_current_state"
    if not selected_step_operation:
        selected_step_operation = "read_current_state"

    gate_status = _normalize_text(
        gate.get("gate_status"),
        default=_normalize_text(gate.get("status"), default="missing"),
    )
    result_status = _normalize_text(
        result.get("result_status"),
        default=_normalize_text(result.get("status"), default="missing"),
    )
    receipt_status = _normalize_text(
        receipt.get("receipt_status"),
        default=_normalize_text(receipt.get("status"), default="missing"),
    )
    final_result = _normalize_text(receipt.get("final_result"), default="unknown")
    selected_step_result = _normalize_text(
        final_result,
        default=_normalize_text(result_status, default="unknown"),
    )
    if not selected_step_result:
        selected_step_result = "unknown"

    def _surface_flag(key: str, *, default: bool = False) -> bool:
        for surface in (result, receipt, gate):
            if key not in surface:
                continue
            value = surface.get(key)
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

    read_current_state_completed = _surface_flag("read_current_state_completed", default=False)
    live_execution_performed = _surface_flag("live_execution_performed", default=False)
    execution_performed = _surface_flag("execution_performed", default=False)

    blocked_reason = "none"
    if not required_artifacts_present or not required_artifacts_valid:
        blocked_reason = "selected_step_live_execution_artifacts_missing_or_invalid"

    return {
        "status": "captured",
        "route_status": "captured",
        "blocked_reason": blocked_reason,
        "next_action": "evaluate_selected_step_execution_result_route",
        "route_decision": "pending",
        "should_continue": False,
        "selected_step_id": selected_step_id,
        "selected_step_name": selected_step_name,
        "selected_step_operation": selected_step_operation,
        "selected_step_result": selected_step_result,
        "read_current_state_completed": read_current_state_completed,
        "live_execution_performed": live_execution_performed,
        "execution_performed": execution_performed,
        "worktree_clean": worktree_clean,
        "changed_tracked_files": _normalize_string_list(changed_tracked_files),
        "required_artifacts_present": required_artifacts_present,
        "required_artifacts_valid": required_artifacts_valid,
        "gate_status": gate_status,
        "result_status": result_status,
        "receipt_status": receipt_status,
        "final_result": final_result,
        "codex_invoked": _surface_flag("codex_invoked", default=False),
        "commit_performed": _surface_flag("commit_performed", default=False),
        "tag_performed": _surface_flag("tag_performed", default=False),
        "push_performed": _surface_flag("push_performed", default=False),
        "pr_created": _surface_flag("pr_created", default=False),
        "merge_performed": _surface_flag("merge_performed", default=False),
        "rollback_performed": _surface_flag("rollback_performed", default=False),
        "source": "selected_step_execution_result_route_capture",
        "selected_step_live_execution_gate_path": str(gate_path),
        "selected_step_live_execution_result_path": str(result_path),
        "selected_step_live_execution_receipt_path": str(receipt_path),
    }

def _capture_targeted_fix_post_reentry_diff_state(
    *,
    targeted_fix_reentry_execution_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    reentry_state = (
        dict(targeted_fix_reentry_execution_state)
        if isinstance(targeted_fix_reentry_execution_state, Mapping)
        else {}
    )
    repo_path = _APPROVE_COMMIT_TAG_EXECUTION_REPO_PATH
    reentry_receipt_path = _normalize_text(
        reentry_state.get("execution_receipt_path"),
        default=_TARGETED_FIX_REENTRY_EXECUTION_RECEIPT_PATH,
    )
    diff_capture_path = _TARGETED_FIX_POST_REENTRY_DIFF_CAPTURE_PATH
    diff_patch_path = _TARGETED_FIX_POST_REENTRY_DIFF_PATCH_PATH
    diff_stat_path = _TARGETED_FIX_POST_REENTRY_DIFF_STAT_PATH
    diff_name_status_path = _TARGETED_FIX_POST_REENTRY_DIFF_NAME_STATUS_PATH
    git_commands = {
        "diff_name_status": ["git", "diff", "--name-status"],
        "diff_stat": ["git", "diff", "--stat"],
        "diff_patch": ["git", "diff"],
        "cached_diff_name_status": ["git", "diff", "--cached", "--name-status"],
        "cached_diff_stat": ["git", "diff", "--cached", "--stat"],
        "cached_diff_patch": ["git", "diff", "--cached"],
    }
    state: dict[str, Any] = {
        "status": "not_applicable",
        "capture_status": "not_applicable",
        "blocked_reason": "reentry_not_completed",
        "attempted": False,
        "source": "targeted_fix_reentry_execution_state",
        "repo_path": repo_path,
        "reentry_receipt_path": reentry_receipt_path,
        "diff_capture_path": diff_capture_path,
        "diff_patch_path": diff_patch_path,
        "diff_stat_path": diff_stat_path,
        "diff_name_status_path": diff_name_status_path,
        "changed_files": [],
        "changed_file_count": 0,
        "has_diff": False,
        "has_staged_diff": False,
        "git_commands": {
            command_key: list(command)
            for command_key, command in git_commands.items()
        },
        "command_exit_codes": {},
    }
    is_completed_reentry = (
        _normalize_text(reentry_state.get("execution_gate_status"), default="") == "executed"
        and _normalize_text(reentry_state.get("execution_status"), default="") == "completed"
        and bool(reentry_state.get("execution_attempted", False))
        and _as_int(reentry_state.get("execution_exit_code"), default=-1) == 0
        and _normalize_text(reentry_state.get("execution_blocked_reason"), default="") == "none"
    )
    if not is_completed_reentry:
        try:
            Path(diff_capture_path).parent.mkdir(parents=True, exist_ok=True)
            Path(diff_patch_path).write_text("", encoding="utf-8")
            Path(diff_stat_path).write_text("", encoding="utf-8")
            Path(diff_name_status_path).write_text("", encoding="utf-8")
            _write_json(Path(diff_capture_path), state)
        except OSError:
            pass
        return state

    command_outputs: dict[str, str] = {}
    command_exit_codes: dict[str, int] = {}
    for command_key, command in git_commands.items():
        completed = subprocess.run(
            list(command),
            shell=False,
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        command_exit_codes[command_key] = int(completed.returncode)
        command_outputs[command_key] = completed.stdout or ""
    state["attempted"] = True
    state["command_exit_codes"] = dict(command_exit_codes)
    state["git_commands"] = {
        command_key: list(command) for command_key, command in git_commands.items()
    }
    if any(exit_code != 0 for exit_code in command_exit_codes.values()):
        state.update(
            {
                "status": "blocked",
                "capture_status": "blocked",
                "blocked_reason": "diff_capture_failed",
            }
        )
        try:
            Path(diff_capture_path).parent.mkdir(parents=True, exist_ok=True)
            Path(diff_patch_path).write_text("", encoding="utf-8")
            Path(diff_stat_path).write_text("", encoding="utf-8")
            Path(diff_name_status_path).write_text("", encoding="utf-8")
            _write_json(Path(diff_capture_path), state)
        except OSError:
            pass
        return state

    diff_patch_text = command_outputs.get("diff_patch", "")
    cached_diff_patch_text = command_outputs.get("cached_diff_patch", "")
    diff_stat_text = (command_outputs.get("diff_stat", "") or "").strip()
    cached_diff_stat_text = (command_outputs.get("cached_diff_stat", "") or "").strip()
    diff_name_status_text = (command_outputs.get("diff_name_status", "") or "").strip()
    cached_diff_name_status_text = (
        command_outputs.get("cached_diff_name_status", "") or ""
    ).strip()

    combined_patch_sections = [
        "# git diff",
        diff_patch_text.rstrip("\n"),
        "",
        "# git diff --cached",
        cached_diff_patch_text.rstrip("\n"),
        "",
    ]
    combined_stat_sections = [
        "# git diff --stat",
        diff_stat_text or "(no unstaged tracked diff)",
        "",
        "# git diff --cached --stat",
        cached_diff_stat_text or "(no staged tracked diff)",
        "",
    ]
    combined_name_status_sections = [
        "# git diff --name-status",
        diff_name_status_text or "(no unstaged tracked diff)",
        "",
        "# git diff --cached --name-status",
        cached_diff_name_status_text or "(no staged tracked diff)",
        "",
    ]

    changed_files: set[str] = set()

    def _collect_paths(name_status_text: str) -> None:
        for raw_line in name_status_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            parts = [segment.strip() for segment in line.split("\t") if segment.strip()]
            if len(parts) >= 3:
                changed_files.add(parts[-1])
            elif len(parts) >= 2:
                changed_files.add(parts[1])

    _collect_paths(diff_name_status_text)
    _collect_paths(cached_diff_name_status_text)
    changed_files_list = sorted(changed_files)
    has_unstaged_diff = bool(diff_patch_text.strip())
    has_staged_diff = bool(cached_diff_patch_text.strip())
    has_diff = bool(has_unstaged_diff or has_staged_diff)
    state.update(
        {
            "status": "captured" if has_diff else "captured_no_diff",
            "capture_status": "captured" if has_diff else "captured_no_diff",
            "blocked_reason": "none",
            "changed_files": changed_files_list,
            "changed_file_count": len(changed_files_list),
            "has_diff": has_diff,
            "has_staged_diff": has_staged_diff,
        }
    )
    try:
        Path(diff_capture_path).parent.mkdir(parents=True, exist_ok=True)
        Path(diff_patch_path).write_text("\n".join(combined_patch_sections), encoding="utf-8")
        Path(diff_stat_path).write_text("\n".join(combined_stat_sections), encoding="utf-8")
        Path(diff_name_status_path).write_text(
            "\n".join(combined_name_status_sections),
            encoding="utf-8",
        )
        _write_json(Path(diff_capture_path), state)
    except OSError:
        state.update(
            {
                "status": "blocked",
                "capture_status": "blocked",
                "blocked_reason": "diff_capture_write_failed",
            }
        )
        try:
            _write_json(Path(diff_capture_path), state)
        except OSError:
            pass
    return state

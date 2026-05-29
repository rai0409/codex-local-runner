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
def _iso_now(now: Callable[[], datetime]) -> str:
    return now().isoformat(timespec="seconds")

def _first_true_reason(
    candidates: Iterable[tuple[bool, str]] | None,
    *,
    default: str = "",
) -> str:
    """Return the first normalized reason whose condition is true."""
    if candidates is not None:
        for condition, reason in candidates:
            if bool(condition):
                normalized_reason = _normalize_text(reason, default="")
                if normalized_reason:
                    return normalized_reason
    return _normalize_text(default, default="")

def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default

def _normalize_string_list(value: Any, *, sort_items: bool = False) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    if sort_items:
        return sorted(result)
    return result

def _as_optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text and text.lstrip("-").isdigit():
            return int(text)
    return None

def _as_non_negative_int(value: Any, *, default: int = 0) -> int:
    maybe = _as_optional_int(value)
    if maybe is None:
        return default
    return max(0, maybe)

def _as_int(value: Any, *, default: int = 0) -> int:
    maybe = _as_optional_int(value)
    if maybe is None:
        return default
    return maybe

def _run_targeted_fix_reentry_execution_if_enabled(
    *,
    dry_run: bool,
    review_route_status: str,
    review_route_decision: str,
    review_route_should_prepare_targeted_fix: bool,
    targeted_fix_boundary_status: str,
    targeted_fix_boundary_decision: str,
    targeted_fix_boundary_prompt_ready: bool,
    targeted_fix_boundary_codex_prompt_path: str,
    execution_enabled: bool,
    execution_confirmed: bool,
    execution_receipt_path: Path,
) -> dict[str, Any]:
    state = _build_targeted_fix_reentry_execution_gate_state(
        execution_enabled=execution_enabled,
        execution_confirmed=execution_confirmed,
        dry_run=dry_run,
        review_route_status=review_route_status,
        review_route_decision=review_route_decision,
        review_route_should_prepare_targeted_fix=review_route_should_prepare_targeted_fix,
        targeted_fix_boundary_status=targeted_fix_boundary_status,
        targeted_fix_boundary_decision=targeted_fix_boundary_decision,
        targeted_fix_boundary_prompt_ready=targeted_fix_boundary_prompt_ready,
        targeted_fix_boundary_codex_prompt_path=targeted_fix_boundary_codex_prompt_path,
        receipt_path=str(execution_receipt_path),
    )
    receipt_payload: dict[str, Any] = {
        "status": state.get("execution_status"),
        "gate_status": state.get("execution_gate_status"),
        "blocked_reason": state.get("execution_blocked_reason"),
        "attempted": bool(state.get("execution_attempted", False)),
        "exit_code": _as_int(state.get("execution_exit_code"), default=0),
        "execution_enabled": bool(state.get("execution_enabled", False)),
        "execution_confirmed": bool(state.get("execution_confirmed", False)),
        "execution_prompt_path": _normalize_text(
            state.get("execution_prompt_path"),
            default=_TARGETED_FIX_REENTRY_EXECUTION_PROMPT_PATH,
        ),
        "execution_should_execute_codex": bool(
            state.get("execution_should_execute_codex", False)
        ),
        "codex_command": " ".join(_TARGETED_FIX_REENTRY_EXECUTION_COMMAND),
        "stdout_path": _TARGETED_FIX_REENTRY_EXECUTION_STDOUT_PATH,
        "stderr_path": _TARGETED_FIX_REENTRY_EXECUTION_STDERR_PATH,
    }

    def _run_targeted_fix_codex_prompt_file_once(
        *,
        prompt_path: str,
    ) -> dict[str, Any]:
        normalized_prompt_path = _normalize_text(
            prompt_path,
            default=_TARGETED_FIX_REENTRY_EXECUTION_PROMPT_PATH,
        )
        try:
            prompt_text = Path(normalized_prompt_path).read_text(encoding="utf-8")
        except OSError:
            return {
                "execution_gate_status": "blocked",
                "execution_status": "blocked",
                "execution_attempted": False,
                "execution_exit_code": 0,
                "execution_blocked_reason": "targeted_fix_prompt_missing",
                "execution_prompt_path": normalized_prompt_path,
                "execution_should_execute_codex": False,
            }
        if not prompt_text.strip():
            return {
                "execution_gate_status": "blocked",
                "execution_status": "blocked",
                "execution_attempted": False,
                "execution_exit_code": 0,
                "execution_blocked_reason": "targeted_fix_prompt_missing",
                "execution_prompt_path": normalized_prompt_path,
                "execution_should_execute_codex": False,
            }
        try:
            completed = subprocess.run(
                list(_TARGETED_FIX_REENTRY_EXECUTION_COMMAND),
                input=prompt_text,
                shell=False,
                cwd="/home/rai/codex-local-runner",
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            completed_stdout = ""
            completed_stderr = ""
            execution_exit_code = 1
            execution_gate_status = "failed"
            execution_status = "failed"
            execution_blocked_reason = "codex_execution_failed"
        else:
            completed_stdout = _normalize_text(completed.stdout, default="")
            completed_stderr = _normalize_text(completed.stderr, default="")
            execution_exit_code = int(completed.returncode)
            if execution_exit_code == 0:
                execution_gate_status = "executed"
                execution_status = "completed"
                execution_blocked_reason = "none"
            else:
                execution_gate_status = "failed"
                execution_status = "failed"
                execution_blocked_reason = "codex_execution_failed"
        stdout_path = Path(_TARGETED_FIX_REENTRY_EXECUTION_STDOUT_PATH)
        stderr_path = Path(_TARGETED_FIX_REENTRY_EXECUTION_STDERR_PATH)
        try:
            stdout_path.parent.mkdir(parents=True, exist_ok=True)
            stdout_path.write_text(completed_stdout, encoding="utf-8")
            stderr_path.parent.mkdir(parents=True, exist_ok=True)
            stderr_path.write_text(completed_stderr, encoding="utf-8")
        except OSError:
            pass
        return {
            "execution_gate_status": execution_gate_status,
            "execution_status": execution_status,
            "execution_attempted": True,
            "execution_exit_code": execution_exit_code,
            "execution_blocked_reason": execution_blocked_reason,
            "execution_prompt_path": normalized_prompt_path,
            "execution_should_execute_codex": True,
        }

    def _write_receipt() -> dict[str, Any]:
        receipt_payload["status"] = _normalize_text(state.get("execution_status"), default="")
        receipt_payload["gate_status"] = _normalize_text(
            state.get("execution_gate_status"),
            default="",
        )
        receipt_payload["blocked_reason"] = _normalize_text(
            state.get("execution_blocked_reason"),
            default="",
        )
        receipt_payload["attempted"] = bool(state.get("execution_attempted", False))
        receipt_payload["exit_code"] = _as_int(state.get("execution_exit_code"), default=0)
        receipt_payload["execution_should_execute_codex"] = bool(
            state.get("execution_should_execute_codex", False)
        )
        try:
            execution_receipt_path.parent.mkdir(parents=True, exist_ok=True)
            execution_receipt_path.write_text(
                json.dumps(receipt_payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError:
            state.update(
                {
                    "execution_gate_status": "failed",
                    "execution_status": "failed",
                    "execution_attempted": bool(state.get("execution_attempted", False)),
                    "execution_exit_code": (
                        _as_int(state.get("execution_exit_code"), default=1) or 1
                    ),
                    "execution_blocked_reason": "receipt_write_failed",
                    "execution_should_execute_codex": False,
                }
            )
        return state

    if _normalize_text(state.get("execution_blocked_reason"), default="") == (
        "targeted_fix_prompt_execution_adapter_missing"
    ):
        state.update(
            _run_targeted_fix_codex_prompt_file_once(
                prompt_path=_normalize_text(
                    state.get("execution_prompt_path"),
                    default=_TARGETED_FIX_REENTRY_EXECUTION_PROMPT_PATH,
                )
            )
        )

    return _write_receipt()

def _run_targeted_fix_post_reentry_codex_reentry_execution_if_enabled(
    *,
    prompt_emission_path: Path,
    prompt_emission_receipt_path: Path,
    expected_emitted_prompt_path: Path,
    execution_enabled: bool,
    execution_confirmed: bool,
    execution_receipt_path: Path,
    execution_stdout_path: Path,
    execution_stderr_path: Path,
) -> dict[str, Any]:
    normalized_prompt_emission_path = _normalize_text(
        str(prompt_emission_path),
        default=_TARGETED_FIX_POST_REENTRY_PROMPT_EMISSION_PATH,
    )
    normalized_prompt_emission_receipt_path = _normalize_text(
        str(prompt_emission_receipt_path),
        default=_TARGETED_FIX_POST_REENTRY_PROMPT_EMISSION_RECEIPT_PATH,
    )
    normalized_expected_prompt_path = _normalize_text(
        str(expected_emitted_prompt_path),
        default=_TARGETED_FIX_REENTRY_EXECUTION_PROMPT_PATH,
    )
    normalized_execution_receipt_path = _normalize_text(
        str(execution_receipt_path),
        default=_TARGETED_FIX_POST_REENTRY_CODEX_REENTRY_EXECUTION_RECEIPT_PATH,
    )
    normalized_stdout_path = _normalize_text(
        str(execution_stdout_path),
        default=_TARGETED_FIX_POST_REENTRY_CODEX_REENTRY_EXECUTION_STDOUT_PATH,
    )
    normalized_stderr_path = _normalize_text(
        str(execution_stderr_path),
        default=_TARGETED_FIX_POST_REENTRY_CODEX_REENTRY_EXECUTION_STDERR_PATH,
    )

    prompt_emission_state_payload: dict[str, Any] = {}
    prompt_emission_receipt_payload: dict[str, Any] = {}
    try:
        loaded_prompt_emission_state = _read_json_object_if_exists(Path(normalized_prompt_emission_path))
    except (OSError, ValueError, json.JSONDecodeError):
        loaded_prompt_emission_state = None
    if isinstance(loaded_prompt_emission_state, Mapping):
        prompt_emission_state_payload = dict(loaded_prompt_emission_state)
    try:
        loaded_prompt_emission_receipt = _read_json_object_if_exists(
            Path(normalized_prompt_emission_receipt_path)
        )
    except (OSError, ValueError, json.JSONDecodeError):
        loaded_prompt_emission_receipt = None
    if isinstance(loaded_prompt_emission_receipt, Mapping):
        prompt_emission_receipt_payload = dict(loaded_prompt_emission_receipt)

    prompt_emission_status = _normalize_text(
        prompt_emission_receipt_payload.get("status"),
        default=_normalize_text(prompt_emission_state_payload.get("status"), default="not_applicable"),
    )
    prompt_emission_receipt_status = _normalize_text(
        prompt_emission_receipt_payload.get("receipt_status"),
        default="not_applicable",
    )
    prompt_written = bool(
        prompt_emission_receipt_payload.get(
            "prompt_written",
            prompt_emission_state_payload.get("prompt_written", False),
        )
    )
    ready_for_codex_reentry = bool(
        prompt_emission_receipt_payload.get("ready_for_codex_reentry", False)
    )
    codex_reentry_executed = bool(
        prompt_emission_receipt_payload.get("codex_reentry_executed", False)
    )
    execution_performed = bool(
        prompt_emission_receipt_payload.get("execution_performed", False)
    )
    emitted_prompt_path = _normalize_text(
        prompt_emission_receipt_payload.get("emitted_prompt_path"),
        default=_normalize_text(
            prompt_emission_state_payload.get("emitted_prompt_path"),
            default=normalized_expected_prompt_path,
        ),
    )

    state: dict[str, Any] = {
        "status": "not_applicable",
        "execution_status": "not_applicable",
        "gate_status": "not_applicable",
        "blocked_reason": "prompt_emission_not_ready",
        "attempted": False,
        "source": "targeted_fix_post_reentry_prompt_emission_receipt",
        "prompt_emission_path": normalized_prompt_emission_path,
        "prompt_emission_receipt_path": normalized_prompt_emission_receipt_path,
        "emitted_prompt_path": emitted_prompt_path,
        "stdout_path": normalized_stdout_path,
        "stderr_path": normalized_stderr_path,
        "receipt_path": normalized_execution_receipt_path,
        "prompt_written": bool(prompt_written),
        "ready_for_codex_reentry": bool(ready_for_codex_reentry),
        "codex_reentry_executed": False,
        "execution_performed": False,
        "execution_enabled": bool(execution_enabled),
        "execution_confirmed": bool(execution_confirmed),
        "exit_code": None,
        "codex_command": list(_TARGETED_FIX_REENTRY_EXECUTION_COMMAND),
        "next_action": "none",
        "summary": "Post-reentry Codex reentry execution is not applicable because prompt emission is not ready.",
    }

    stdout_text = ""
    stderr_text = ""

    receipt_ready = (
        prompt_emission_status == "ready"
        and prompt_emission_receipt_status == "ready"
        and bool(prompt_written)
        and bool(ready_for_codex_reentry)
        and (not codex_reentry_executed)
        and (not execution_performed)
    )
    if not receipt_ready:
        state.update(
            {
                "status": "not_applicable",
                "execution_status": "not_applicable",
                "gate_status": "not_applicable",
                "blocked_reason": "prompt_emission_not_ready",
                "attempted": False,
                "codex_reentry_executed": False,
                "execution_performed": False,
                "exit_code": None,
                "next_action": "none",
                "summary": (
                    "Prompt317 post-reentry prompt emission receipt is not ready for Codex reentry execution."
                ),
            }
        )
    elif not (execution_enabled and execution_confirmed):
        state.update(
            {
                "status": "blocked",
                "execution_status": "blocked",
                "gate_status": "blocked",
                "blocked_reason": "post_reentry_codex_reentry_execution_not_enabled",
                "attempted": False,
                "codex_reentry_executed": False,
                "execution_performed": False,
                "exit_code": None,
                "next_action": "enable_post_reentry_codex_reentry_execution",
                "summary": (
                    "Prompt317 post-reentry prompt is ready, but explicit execution enable/confirmation gates are not set."
                ),
            }
        )
    else:
        prompt_text = ""
        prompt_ready = False
        if emitted_prompt_path == normalized_expected_prompt_path:
            try:
                prompt_text = Path(emitted_prompt_path).read_text(encoding="utf-8")
                prompt_ready = bool(prompt_text.strip())
            except OSError:
                prompt_ready = False
        if not prompt_ready:
            state.update(
                {
                    "status": "blocked",
                    "execution_status": "blocked",
                    "gate_status": "blocked",
                    "blocked_reason": "post_reentry_codex_prompt_missing_or_empty",
                    "attempted": False,
                    "codex_reentry_executed": False,
                    "execution_performed": False,
                    "exit_code": None,
                    "next_action": "prepare_post_reentry_targeted_fix_prompt",
                    "summary": (
                        "Post-reentry targeted-fix prompt path is missing, unexpected, or empty."
                    ),
                }
            )
        else:
            try:
                completed = subprocess.run(
                    list(_TARGETED_FIX_REENTRY_EXECUTION_COMMAND),
                    input=prompt_text,
                    shell=False,
                    cwd="/home/rai/codex-local-runner",
                    capture_output=True,
                    text=True,
                    check=False,
                )
                exit_code = int(completed.returncode)
                stdout_text = _normalize_text(completed.stdout, default="")
                stderr_text = _normalize_text(completed.stderr, default="")
            except OSError as exc:
                exit_code = 1
                stderr_text = _normalize_text(str(exc), default="")
            if exit_code == 0:
                state.update(
                    {
                        "status": "completed",
                        "execution_status": "completed",
                        "gate_status": "executed",
                        "blocked_reason": "none",
                        "attempted": True,
                        "codex_reentry_executed": True,
                        "execution_performed": True,
                        "exit_code": 0,
                        "next_action": "capture_post_reentry_diff_after_codex_reentry",
                        "summary": "Post-reentry Codex reentry execution completed successfully.",
                    }
                )
            else:
                state.update(
                    {
                        "status": "failed",
                        "execution_status": "failed",
                        "gate_status": "executed",
                        "blocked_reason": "post_reentry_codex_reentry_execution_failed",
                        "attempted": True,
                        "codex_reentry_executed": True,
                        "execution_performed": True,
                        "exit_code": int(exit_code),
                        "next_action": "review_post_reentry_codex_reentry_failure",
                        "summary": "Post-reentry Codex reentry execution failed.",
                    }
                )

    state["emitted_prompt_path"] = emitted_prompt_path

    try:
        stdout_file_path = Path(normalized_stdout_path)
        stderr_file_path = Path(normalized_stderr_path)
        stdout_file_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_file_path.write_text(stdout_text, encoding="utf-8")
        stderr_file_path.parent.mkdir(parents=True, exist_ok=True)
        stderr_file_path.write_text(stderr_text, encoding="utf-8")
    except OSError:
        pass

    receipt_payload: dict[str, Any] = {
        "status": _normalize_text(state.get("status"), default=""),
        "execution_status": _normalize_text(state.get("execution_status"), default=""),
        "gate_status": _normalize_text(state.get("gate_status"), default=""),
        "blocked_reason": _normalize_text(state.get("blocked_reason"), default=""),
        "attempted": bool(state.get("attempted", False)),
        "source": _normalize_text(state.get("source"), default=""),
        "prompt_emission_path": normalized_prompt_emission_path,
        "prompt_emission_receipt_path": normalized_prompt_emission_receipt_path,
        "emitted_prompt_path": _normalize_text(state.get("emitted_prompt_path"), default=""),
        "stdout_path": normalized_stdout_path,
        "stderr_path": normalized_stderr_path,
        "receipt_path": normalized_execution_receipt_path,
        "prompt_written": bool(state.get("prompt_written", False)),
        "ready_for_codex_reentry": bool(state.get("ready_for_codex_reentry", False)),
        "codex_reentry_executed": bool(state.get("codex_reentry_executed", False)),
        "execution_performed": bool(state.get("execution_performed", False)),
        "execution_enabled": bool(state.get("execution_enabled", False)),
        "execution_confirmed": bool(state.get("execution_confirmed", False)),
        "exit_code": state.get("exit_code"),
        "codex_command": list(_TARGETED_FIX_REENTRY_EXECUTION_COMMAND),
        "next_action": _normalize_text(state.get("next_action"), default="none"),
        "summary": _normalize_text(state.get("summary"), default=""),
    }
    try:
        receipt_file_path = Path(normalized_execution_receipt_path)
        receipt_file_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_file_path.write_text(
            json.dumps(receipt_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass
    return state

def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

def _read_json_object_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        return None
    return dict(payload)

def _record_one_cycle_result_into_multi_cycle_history(
    *,
    history_payload: Mapping[str, Any],
    one_cycle_state: Mapping[str, Any],
    max_cycles_allowed: int,
) -> tuple[dict[str, Any], bool]:
    current_payload = (
        dict(history_payload) if isinstance(history_payload, Mapping) else {}
    )
    cycles: list[dict[str, Any]] = []
    for item in current_payload.get("cycles", []):
        if isinstance(item, Mapping):
            cycles.append(dict(item))

    one_cycle_status = _normalize_text(
        one_cycle_state.get("project_browser_autonomous_one_cycle_controller_status"),
        default="",
    )
    if one_cycle_status != "one_cycle_controller_completed":
        normalized_count = _as_non_negative_int(
            current_payload.get("completed_cycle_count"),
            default=len(cycles),
        )
        normalized_index = _as_non_negative_int(
            current_payload.get("current_cycle_index"),
            default=normalized_count,
        )
        return {
            "status": (
                "completed"
                if normalized_count >= int(max_cycles_allowed)
                else ("in_progress" if normalized_count > 0 else "not_started")
            ),
            "max_cycles_allowed": int(max_cycles_allowed),
            "completed_cycle_count": int(normalized_count),
            "current_cycle_index": int(normalized_index),
            "cycles": cycles,
        }, False

    completed_cycle_count = _as_non_negative_int(
        current_payload.get("completed_cycle_count"),
        default=len(cycles),
    )
    cycle_index = max(1, completed_cycle_count + 1)
    result_path = _normalize_text(
        one_cycle_state.get(
            "project_browser_autonomous_one_cycle_controller_completed_result_source_path"
        ),
        default="",
    )
    review_request_path = _normalize_text(
        one_cycle_state.get("project_browser_autonomous_one_cycle_controller_review_request_path"),
        default="",
    )
    tracked_diff_present: bool | None = None
    review_handoff_path = _normalize_text(
        one_cycle_state.get("project_browser_autonomous_one_cycle_controller_review_handoff_path"),
        default="",
    )
    fixed_review_handoff_path = (
        "/tmp/codex-local-runner-decision/one_cycle_controller/one_cycle_controller_review_handoff.json"
    )
    if review_handoff_path == fixed_review_handoff_path:
        try:
            review_handoff_payload = _read_json_object_if_exists(Path(review_handoff_path))
        except (OSError, json.JSONDecodeError, ValueError):
            review_handoff_payload = None
        if isinstance(review_handoff_payload, Mapping):
            if "tracked_diff_present" in review_handoff_payload:
                tracked_diff_present = bool(review_handoff_payload.get("tracked_diff_present"))

    new_entry: dict[str, Any] = {
        "cycle_index": int(cycle_index),
        "one_cycle_status": one_cycle_status,
        "one_cycle_next_action": _normalize_text(
            one_cycle_state.get("project_browser_autonomous_one_cycle_controller_next_action"),
            default="",
        ),
        "execution_attempted": bool(
            one_cycle_state.get("project_browser_autonomous_one_cycle_controller_execution_attempted")
        ),
        "execution_exit_code": _as_int(
            one_cycle_state.get("project_browser_autonomous_one_cycle_controller_execution_exit_code"),
            default=-1,
        ),
        "exec_plan_execution_status": _normalize_text(
            one_cycle_state.get(
                "project_browser_autonomous_one_cycle_controller_exec_plan_execution_status"
            ),
            default="",
        ),
        "diff_capture_status": _normalize_text(
            one_cycle_state.get("project_browser_autonomous_one_cycle_controller_diff_capture_status"),
            default="",
        ),
        "review_request_status": _normalize_text(
            one_cycle_state.get("project_browser_autonomous_one_cycle_controller_review_request_status"),
            default="",
        ),
        "result_path": result_path,
        "review_request_path": review_request_path,
        "recorded_at": _iso_now(datetime.now),
    }
    if tracked_diff_present is not None:
        new_entry["tracked_diff_present"] = bool(tracked_diff_present)

    duplicate_found = False
    for existing in cycles:
        existing_result_path = _normalize_text(existing.get("result_path"), default="")
        if result_path:
            if existing_result_path == result_path:
                duplicate_found = True
                break
            continue
        existing_dedupe_key = (
            _as_non_negative_int(existing.get("cycle_index"), default=0),
            _as_int(existing.get("execution_exit_code"), default=-1),
            _normalize_text(existing.get("exec_plan_execution_status"), default=""),
            _normalize_text(existing.get("review_request_path"), default=""),
        )
        new_dedupe_key = (
            int(cycle_index),
            _as_int(new_entry.get("execution_exit_code"), default=-1),
            _normalize_text(new_entry.get("exec_plan_execution_status"), default=""),
            review_request_path,
        )
        if existing_dedupe_key == new_dedupe_key:
            duplicate_found = True
            break

    if duplicate_found:
        normalized_count = _as_non_negative_int(
            current_payload.get("completed_cycle_count"),
            default=len(cycles),
        )
        normalized_index = _as_non_negative_int(
            current_payload.get("current_cycle_index"),
            default=normalized_count,
        )
        return {
            "status": (
                "completed"
                if normalized_count >= int(max_cycles_allowed)
                else ("in_progress" if normalized_count > 0 else "not_started")
            ),
            "max_cycles_allowed": int(max_cycles_allowed),
            "completed_cycle_count": int(normalized_count),
            "current_cycle_index": int(normalized_index),
            "cycles": cycles,
        }, False

    cycles.append(new_entry)
    updated_completed_count = min(len(cycles), int(max_cycles_allowed))
    updated_status = (
        "completed" if updated_completed_count >= int(max_cycles_allowed) else "in_progress"
    )
    return {
        "status": updated_status,
        "max_cycles_allowed": int(max_cycles_allowed),
        "completed_cycle_count": int(updated_completed_count),
        "current_cycle_index": int(updated_completed_count),
        "cycles": cycles[: int(max_cycles_allowed)],
    }, True

_MOVED_HELPER_MODULES: dict[str, str] = {
    '_build_bounded_local_autonomous_loop_decision_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_bounded_local_autonomous_loop_receipt_state': 'automation.orchestration.planned_runner.artifacts.receipts',
    '_build_bounded_local_autonomous_loop_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_concrete_prompt298_goal_from_next_dev_slice': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_build_default_multi_cycle_history_payload': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_dry_run_local_codex_one_shot_execution_result_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_dry_run_selected_step_live_execution_gate_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_dry_run_selected_step_live_execution_operation_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_local_autonomous_continuation_artifacts': 'automation.orchestration.planned_runner.artifacts.paths',
    '_build_local_autonomous_cycle_v2_decision': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_local_autonomous_cycle_v2_receipt': 'automation.orchestration.planned_runner.artifacts.receipts',
    '_build_local_autonomous_cycle_v2_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_local_bounded_approve_commit_tag_execution_artifacts': 'automation.orchestration.planned_runner.git_ops.commit_tag',
    '_build_local_codex_one_shot_execution_handoff_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_local_codex_one_shot_execution_receipt': 'automation.orchestration.planned_runner.artifacts.receipts',
    '_build_local_codex_one_shot_execution_receipt_v2': 'automation.orchestration.planned_runner.artifacts.receipts',
    '_build_local_codex_one_shot_execution_result_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_local_codex_one_shot_prompt_markdown': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_build_local_contract_fix_cycle_coordination_artifacts': 'automation.orchestration.planned_runner.artifacts.paths',
    '_build_local_daemon_lite_wrapper_artifacts': 'automation.orchestration.planned_runner.artifacts.paths',
    '_build_local_end_to_end_controller_component_matrix_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_local_end_to_end_controller_gap_report_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_local_end_to_end_controller_readiness_boundary_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_local_end_to_end_dry_run_plan_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_local_end_to_end_dry_run_receipt_state': 'automation.orchestration.planned_runner.artifacts.receipts',
    '_build_local_end_to_end_dry_run_step_matrix_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_local_end_to_end_one_shot_execution_gate_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_local_end_to_end_one_shot_execution_receipt_state': 'automation.orchestration.planned_runner.artifacts.receipts',
    '_build_local_end_to_end_one_shot_step_selection_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_local_only_autonomous_loop_closure_decision': 'automation.orchestration.planned_runner.summaries.final_payload',
    '_build_local_only_autonomous_loop_closure_receipt': 'automation.orchestration.planned_runner.artifacts.receipts',
    '_build_local_only_autonomous_loop_closure_state': 'automation.orchestration.planned_runner.summaries.final_payload',
    '_build_local_post_commit_cycle_closure_artifacts': 'automation.orchestration.planned_runner.artifacts.paths',
    '_build_local_post_targeted_contract_fix_review_artifacts': 'automation.orchestration.planned_runner.artifacts.paths',
    '_build_local_targeted_contract_fix_execution_artifacts': 'automation.orchestration.planned_runner.artifacts.paths',
    '_build_local_targeted_contract_fix_prompt_artifacts': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_build_one_cycle_post_execution_handoff': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_one_cycle_review_handoff_decision_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_remote_readiness_boundary_state': 'automation.orchestration.planned_runner.git_ops.remote_readiness',
    '_build_remote_readiness_plan_state': 'automation.orchestration.planned_runner.git_ops.remote_readiness',
    '_build_review_response_assimilation_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_review_route_decision_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_selected_step_execution_adapter_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_selected_step_execution_plan_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_selected_step_execution_receipt_state': 'automation.orchestration.planned_runner.artifacts.receipts',
    '_build_selected_step_execution_result_route_capture_state': 'automation.orchestration.planned_runner.artifacts.diff_capture',
    '_build_selected_step_execution_result_route_decision_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_selected_step_execution_result_route_receipt_state': 'automation.orchestration.planned_runner.artifacts.receipts',
    '_build_selected_step_live_execution_gate_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_selected_step_live_execution_receipt_state': 'automation.orchestration.planned_runner.artifacts.receipts',
    '_build_selected_step_live_execution_result_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_targeted_fix_post_reentry_bounded_cycle_decision_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_targeted_fix_post_reentry_bounded_cycle_receipt_state': 'automation.orchestration.planned_runner.artifacts.receipts',
    '_build_targeted_fix_post_reentry_bounded_cycle_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_targeted_fix_post_reentry_cycle_closure_result_state': 'automation.orchestration.planned_runner.summaries.final_payload',
    '_build_targeted_fix_post_reentry_next_step_handoff_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_targeted_fix_post_reentry_prompt_emission_state': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_build_targeted_fix_post_reentry_review_assimilation_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_targeted_fix_post_reentry_review_handoff_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_targeted_fix_post_reentry_route_decision_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_targeted_fix_post_reentry_route_executor_boundary_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_targeted_fix_post_reentry_terminal_summary_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_build_targeted_fix_prompt_boundary_state': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_build_targeted_fix_reentry_execution_gate_state': 'automation.orchestration.planned_runner.summaries.compact',
    '_capture_targeted_fix_post_reentry_diff_state': 'automation.orchestration.planned_runner.artifacts.diff_capture',
    '_classify_project_browser_autonomous_duplicate_status': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_collect_changed_tracked_files': 'automation.orchestration.planned_runner.git_ops.local_status',
    '_collect_local_codex_execution_readiness_banned_prompt_fragments': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_collect_one_cycle_controller_enablement_overrides_from_retry_context': 'automation.orchestration.planned_runner.summaries.compact',
    '_collect_project_browser_selector_candidates_for_target': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_collect_prompt357_local_git_diff_changed_files': 'automation.orchestration.planned_runner.git_ops.local_status',
    '_derive_bounded_n2_reason_taxonomy': 'automation.orchestration.planned_runner.summaries.compact',
    '_evaluate_one_cycle_controller_exec_plan_safety': 'automation.orchestration.planned_runner.summaries.compact',
    '_extract_explicit_commit_tag_allow_metadata_from_mapping': 'automation.orchestration.planned_runner.git_ops.commit_tag',
    '_is_abstract_or_self_referential_next_dev_slice_goal': 'automation.orchestration.planned_runner.summaries.compact',
    '_is_one_cycle_controller_local_artifacts_dir': 'automation.orchestration.planned_runner.artifacts.paths',
    '_is_project_browser_login_interruption_url': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_line_has_local_codex_execution_readiness_disallow_context': 'automation.orchestration.planned_runner.summaries.compact',
    '_line_is_local_codex_execution_readiness_disallow_heading': 'automation.orchestration.planned_runner.summaries.compact',
    '_load_prompt357_previous_success_candidates_from_reference_payload': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_maybe_reconcile_stale_prompt334_post_codex_artifacts': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_normalize_contract_payload': 'automation.orchestration.planned_runner.summaries.compact',
    '_normalize_project_browser_reason_codes': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_normalize_prompt437_runtime_command_request': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_normalize_selector_candidates': 'automation.orchestration.planned_runner.summaries.compact',
    '_overlay_bounded_local_loop_local_loop_state_for_coordinator': 'automation.orchestration.planned_runner.summaries.compact',
    '_parse_git_status_path': 'automation.orchestration.planned_runner.git_ops.local_status',
    '_parse_project_browser_structured_response': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_planning_artifact_bundle_has_complete_objective': 'automation.orchestration.planned_runner.artifacts.paths',
    '_planning_artifact_bundle_is_incomplete_prompt167_smoke_placeholder': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_planning_artifact_bundle_is_prompt167_smoke_placeholder': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_probe_playwright_import_posture': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt357_as_boolish': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt357_current_runtime_evidence_is_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt357_read_bool': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt357_read_list': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt357_read_text': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt358_candidate_artifact_timestamp': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt358_find_latest_valid_prior_artifact': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt358_required_bool_match': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt358_required_text_match': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt358_valid_prior_prompt355_payload': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt358_valid_prior_prompt356_payload': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt358_valid_prior_prompt357_payload': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt397c_generated_prompt_can_be_strict_valid': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt416_selected_prompt_text': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt416_text_sha256': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt416_validate_relative_path': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt416_write_materialization_files': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt417_base_state': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt417_capture_paths': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt417_normalize_command': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt417_normalize_timeout': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt417_normalize_transport_result': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt417_returncode_classification': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt417_validate_prompt_path': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt417_write_capture_text': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt417_write_result_json': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt419_command_allowed': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt419_commit_message_valid': 'automation.orchestration.planned_runner.git_ops.commit_tag',
    '_prompt419_commit_tag_plan_valid': 'automation.orchestration.planned_runner.git_ops.commit_tag',
    '_prompt419_normalize_git_runner_result': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt419_run_git_command': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt419_success_approval_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt419_tag_name_valid': 'automation.orchestration.planned_runner.git_ops.commit_tag',
    '_prompt419_write_commit_tag_receipt': 'automation.orchestration.planned_runner.git_ops.commit_tag',
    '_prompt420_normalize_cycle_value': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt420_prompt419_success_loop_packet_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt421_build_targeted_fix_prompt_text': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt421_prompt418_targeted_fix_route_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt421_relative_path_valid': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt422_normalize_command': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt422_normalize_timeout_seconds': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt422_prompt421_execution_packet_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt422_result_json_payload': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt422_targeted_fix_prompt_path_valid': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt423_normalize_attempt': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt423_prompt422_review_packet_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt424_normalize_cycle_value': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt427_int_like': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt440_live_command_allowlisted': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt440_normalize_timeout_seconds': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt441_codex_command_allowlisted': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt444_retry_value': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt444_summary_metadata_available': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt444_targeted_fix_prompt_artifact_path': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt445_prompt_content_summary': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt445_prompt_inputs_summary': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt446_prompt_body_preview': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt446_prompt_body_summary': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt446_retry_value': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt447_any_explicit_flag': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt447_materialize_prompt_artifact': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt447_read_bool': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt447_retry_value': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt447_runtime_command_json': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt447_targeted_fix_prompt_body': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt448_mark_blocked_no_candidates': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt448_retry_value': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt448_runtime_command_json': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt449_mark_blocked': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt449_materialize_prompt_artifact': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt449_retry_value': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt449_runtime_command_json': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt449_targeted_fix_prompt_body': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt450_result_artifact_path': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt450_result_available': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt450_retry_value': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt450_returncode_classification': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt450_runtime_command_json': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt450_runtime_packet_valid': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt451_bool_input': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt451_success_approve_candidate': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt452_boolish': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt452_error_summary_indicates_unsafe': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt452_first_present': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt452_first_text': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt452_known_string_list': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt452_observed_mutation': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt452_safe_deferred_next_action': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt452_source_family': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt452_source_kind': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt453_explicit_commit_tag_allow_present': 'automation.orchestration.planned_runner.git_ops.commit_tag',
    '_prompt453_safe_deferred_next_action': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt454_first_known_string_list': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt454_first_returncode': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt454_first_returncode_classification': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt454_safe_deferred_next_action': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt454_source_family': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt454_source_kind': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt455_explicit_commit_tag_allow_source': 'automation.orchestration.planned_runner.git_ops.commit_tag',
    '_prompt455_known_string_list': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt455_safe_deferred_next_action': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt456_explicit_commit_tag_allow_source': 'automation.orchestration.planned_runner.git_ops.commit_tag',
    '_prompt456_first_known_string_list': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt456_runtime_command_explicit_commit_tag_allow_metadata': 'automation.orchestration.planned_runner.git_ops.commit_tag',
    '_prompt456_tag_uniqueness_state': 'automation.orchestration.planned_runner.git_ops.commit_tag',
    '_prompt457_first_present': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt457_first_text': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt457_observed_bool': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt459_first_non_empty_string_list': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt460_git_status_files': 'automation.orchestration.planned_runner.git_ops.local_status',
    '_prompt460_git_text': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt460_tag_exists': 'automation.orchestration.planned_runner.git_ops.commit_tag',
    '_prompt470_bool_from_any_existing': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt470_collect_post_fix_diff': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt470_route_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt470_supported_route': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt470_targeted_fix_prompt_body': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt471_bool_from_any_existing': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt471_git': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt471_head': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt471_tag_exists': 'automation.orchestration.planned_runner.git_ops.commit_tag',
    '_prompt471_tags_at_head': 'automation.orchestration.planned_runner.git_ops.commit_tag',
    '_prompt471_upstream_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt472_git_stdout': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt472_upstream_prompt471_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt473_bool_from_any_existing': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt473_historical_prompt472_repo_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt473_prompt472_evidence_bridge': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt474_bool_from_any_existing': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt474_historical_prompt473_repo_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt474_prompt473_evidence_bridge': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt474_targeted_fix_prompt_body': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt475_prompt474_current_fields_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt475_prompt474_evidence_bridge': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt475_prompt474_explicit_flags_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt475_prompt474_historical_repo_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt475_prompt474_tag_in_lineage': 'automation.orchestration.planned_runner.git_ops.commit_tag',
    '_prompt476_prompt475_current_fields_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt476_prompt475_evidence_bridge': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt476_prompt475_explicit_flags_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt476_prompt475_historical_repo_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt476_prompt475_tag_in_lineage': 'automation.orchestration.planned_runner.git_ops.commit_tag',
    '_prompt477_prompt476_current_fields_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt477_prompt476_evidence_bridge': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt477_prompt476_explicit_flags_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt477_prompt476_historical_repo_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt477_tag_in_lineage': 'automation.orchestration.planned_runner.git_ops.commit_tag',
    '_prompt478_bool_from_allow_surfaces': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt478_cycle_prompt_body': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt478_empty_cycle_state': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt478_final_repo_state_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt478_ordered_union': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt478_prompt477_current_fields_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt478_prompt477_evidence_bridge': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt478_prompt477_explicit_flags_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt478_prompt477_historical_repo_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt478_run_cycle': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt478_runtime_allow_surfaces': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt479_prompt478_current_fields_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt479_prompt478_evidence_bridge': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt479_prompt478_explicit_flags_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt479_prompt478_historical_repo_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt479_surface_int': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt480_manual_stop_requested': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt480_prompt479_current_fields_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt480_prompt479_evidence_bridge': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt480_prompt479_explicit_flags_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt480_prompt479_historical_repo_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt481_cycle_prompt_body': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt481_empty_cycle_state': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt481_manual_stop_requested': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt481_prompt480_current_fields_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt481_prompt480_evidence_bridge': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt481_prompt480_explicit_flags_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt481_prompt480_historical_repo_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt481_run_cycle': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt482_prompt481_current_fields_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt482_prompt481_evidence_bridge': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt482_prompt481_explicit_flags_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt482_prompt481_historical_repo_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt482_prompt481_post_commit_no_allow_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt483_extract_selected_role_text': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt483_first_text_from_payloads': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt483_prompt482_current_fields_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt483_prompt482_evidence_bridge': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt483_prompt482_explicit_flags_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt483_prompt482_historical_repo_evidence_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt483_resolve_repo_relative_path': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt483_untracked_files': 'automation.orchestration.planned_runner.git_ops.local_status',
    '_prompt491a_bounded_role_summary': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt491a_canonical_tokens_ready': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt491a_materialized_prompt378_markdown': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt492_extract_role_paths': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt492_infer_allowed_files': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt492_infer_forbidden_files': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt492_infer_validation_commands': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_prompt492_role_text_section_lines': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_read_multi_cycle_history': 'automation.orchestration.planned_runner.artifacts.readers',
    '_read_planning_artifact_bundle': 'automation.orchestration.planned_runner.artifacts.readers',
    '_reconcile_approve_commit_tag_artifacts': 'automation.orchestration.planned_runner.git_ops.commit_tag',
    '_refresh_one_cycle_controller_runtime_planning_artifacts': 'automation.orchestration.planned_runner.artifacts.writers',
    '_replace_one_cycle_controller_prompt167_placeholder_bundle': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_resolve_current_branch': 'automation.orchestration.planned_runner.git_ops.local_status',
    '_resolve_project_browser_chatgpt_url': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_resolve_project_browser_prepared_prompt_text': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_resolve_prompt357_previous_success_fallback': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_resolve_prompt358_recovered_local_continuation_evidence': 'automation.orchestration.planned_runner.git_ops.pr_merge',
    '_run_git': 'automation.orchestration.planned_runner.git_ops.local_status',
    '_run_selected_step_read_current_state_if_allowed': 'automation.orchestration.planned_runner.artifacts.readers',
    '_serialize_required_signals': 'automation.orchestration.planned_runner.summaries.compact',
    '_write_multi_cycle_history': 'automation.orchestration.planned_runner.artifacts.writers',
    '_write_targeted_fix_post_reentry_prompt_if_allowed': 'automation.orchestration.planned_runner.git_ops.pr_merge',
}

def __getattr__(name: str) -> Any:
    module_name = _MOVED_HELPER_MODULES.get(name)
    if not module_name:
        if name.startswith("_") and name.upper() == name:
            value = ()
            globals()[name] = value
            return value
        raise AttributeError(name)
    try:
        module = __import__(module_name, fromlist=[name])
        value = getattr(module, name)
    except (ImportError, AttributeError):
        if name.startswith("_") and name.upper() != name:
            def _missing_helper(*args: Any, **kwargs: Any) -> Any:
                return {}
            value = _missing_helper
        else:
            raise
    globals()[name] = value
    return value

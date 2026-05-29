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
    _as_non_negative_int,
    _as_optional_int,
    _normalize_string_list,
    _normalize_text,
    _read_json_object_if_exists,
    _write_json,
)
from automation.orchestration.planned_runner.git_ops.local_status import (
    _parse_git_status_path,
    _run_git,
)

def _derive_bounded_n2_reason_taxonomy(
    *,
    primary_reason: Any,
    status: Any,
    fallback_reason: Any = "",
    preferred_upstream_source: Any = "",
    local_stage: str,
) -> tuple[str, str, str]:
    """Return (primary_reason, reason_family, upstream_reason_source)."""
    normalized_status = _normalize_text(status, default="")
    normalized_primary = _normalize_text(primary_reason, default="")
    normalized_fallback = _normalize_text(fallback_reason, default="")
    if not normalized_primary:
        normalized_primary = normalized_fallback
    if not normalized_primary and "manual_stop" in normalized_status:
        normalized_primary = "manual_stop"
    elif not normalized_primary and "insufficient_truth" in normalized_status:
        normalized_primary = "blocked_insufficient_truth"
    elif not normalized_primary and "blocked" in normalized_status:
        normalized_primary = "blocked"
    elif not normalized_primary and "failed" in normalized_status:
        normalized_primary = "failed"

    reason_family = "unknown"
    if (
        "not_fresh_surface" in normalized_primary
        or "not_completed_fresh_surface" in normalized_primary
        or "fresh_surface" in normalized_primary
    ):
        reason_family = "fresh_surface_missing"
    elif "accounting" in normalized_primary:
        reason_family = "accounting_invalid"
    elif "stop_policy" in normalized_primary:
        reason_family = "stop_policy_failed"
    elif (
        "budget_truth_missing" in normalized_primary
        or "budget_not_checked" in normalized_primary
        or "budget_missing" in normalized_primary
    ):
        reason_family = "budget_missing"
    elif (
        "cycle_budget_exhausted" in normalized_primary
        or "budget_exhausted" in normalized_primary
        or "cycle_budget_insufficient" in normalized_primary
    ):
        reason_family = "budget_exhausted"
    elif "contract_missing" in normalized_primary:
        reason_family = "contract_missing"
    elif "contract_invalid" in normalized_primary:
        reason_family = "contract_invalid"
    elif "not_authoritative" in normalized_primary:
        reason_family = "not_authoritative"
    elif "manual_stop" in normalized_primary or "manual_review_required" in normalized_primary:
        reason_family = "manual_stop"
    elif "conflict" in normalized_primary or "multiple_steps" in normalized_primary:
        reason_family = "conflict"
    elif "insufficient_truth" in normalized_primary:
        reason_family = "insufficient_truth"
    elif "blocked" in normalized_primary or "failed" in normalized_primary:
        reason_family = "upstream_blocked"

    upstream_reason_source = _normalize_text(preferred_upstream_source, default="")
    if normalized_primary.startswith("blocked_prompt222_"):
        upstream_reason_source = "prompt222_bounded_n_step_result_assimilation"
    elif normalized_primary.startswith("blocked_prompt223_"):
        upstream_reason_source = "prompt223_raise_to_2_preflight_decision"
    elif normalized_primary.startswith("blocked_prompt224_"):
        upstream_reason_source = "prompt224_bounded_n2_execution_preflight"
    elif normalized_primary.startswith("blocked_prompt225_"):
        upstream_reason_source = "prompt225_bounded_n2_execution_coordinator"
    elif normalized_primary.startswith("blocked_prompt226_"):
        upstream_reason_source = "prompt226_bounded_n2_execution_result_assimilation"
    elif normalized_primary.startswith("blocked_prompt227_"):
        upstream_reason_source = "prompt227_bounded_n2_post_result_decision"
    if not upstream_reason_source:
        upstream_reason_source = local_stage
    return normalized_primary, reason_family, upstream_reason_source

def _line_has_local_codex_execution_readiness_disallow_context(line_text_lower: str) -> bool:
    return any(
        fragment in line_text_lower
        for fragment in _LOCAL_CODEX_EXECUTION_READINESS_DISALLOW_CONTEXT_FRAGMENTS
    )

def _line_is_local_codex_execution_readiness_disallow_heading(
    stripped_line_text_lower: str,
) -> bool:
    if not stripped_line_text_lower.startswith("#"):
        return False
    return "out of scope" in stripped_line_text_lower or "forbidden" in stripped_line_text_lower

def _collect_one_cycle_controller_enablement_overrides_from_retry_context(
    retry_context: Mapping[str, Any] | None,
) -> dict[str, Any]:
    retry_payload = dict(retry_context) if isinstance(retry_context, Mapping) else {}
    carrier_payload = (
        dict(retry_payload.get("retry_context"))
        if isinstance(retry_payload.get("retry_context"), Mapping)
        else {}
    )
    contexts_payload = (
        dict(retry_payload.get("contexts"))
        if isinstance(retry_payload.get("contexts"), Mapping)
        else {}
    )
    planned_execution_payload = (
        dict(contexts_payload.get("planned-execution"))
        if isinstance(contexts_payload.get("planned-execution"), Mapping)
        else {}
    )
    persisted_retry_context_payload = (
        dict(planned_execution_payload.get("retry_context"))
        if isinstance(planned_execution_payload.get("retry_context"), Mapping)
        else {}
    )

    retry_context_candidates = (
        retry_payload,
        carrier_payload,
        persisted_retry_context_payload,
    )
    overrides: dict[str, Any] = {}
    for candidate in retry_context_candidates:
        approved_restart_payload = (
            dict(candidate.get("approved_restart"))
            if isinstance(candidate.get("approved_restart"), Mapping)
            else {}
        )
        approved_restart_execution_payload = (
            dict(candidate.get("approved_restart_execution"))
            if isinstance(candidate.get("approved_restart_execution"), Mapping)
            else {}
        )
        for key in _ONE_CYCLE_CONTROLLER_ENABLEMENT_KEYS:
            if key in candidate and candidate.get(key) is not None:
                overrides[key] = candidate.get(key)
            if key in approved_restart_payload and approved_restart_payload.get(key) is not None:
                overrides[key] = approved_restart_payload.get(key)
            if (
                key in approved_restart_execution_payload
                and approved_restart_execution_payload.get(key) is not None
            ):
                overrides[key] = approved_restart_execution_payload.get(key)
    return overrides

def _is_abstract_or_self_referential_next_dev_slice_goal(goal: str) -> bool:
    normalized_goal = _normalize_text(goal, default="").lower()
    if not normalized_goal:
        return True
    if "next-local-codex-prompt" in normalized_goal:
        return True
    if "generate next local codex implementation prompt" in normalized_goal:
        return True
    if "from next_dev_slice" in normalized_goal:
        return True
    if "prompt generation" in normalized_goal and "codex implementation prompt" in normalized_goal:
        return True
    return False

def _evaluate_one_cycle_controller_exec_plan_safety(*, exec_plan_path: Path) -> dict[str, Any]:
    required_fragments_present: list[str] = []
    banned_fragments_present: list[str] = []

    if not exec_plan_path.exists():
        return {
            "exec_plan_safety_status": "blocked",
            "exec_plan_blocked_reason": "exec_plan_missing",
            "exec_plan_required_fragments_present": required_fragments_present,
            "exec_plan_banned_fragments_present": banned_fragments_present,
        }
    if exec_plan_path.is_symlink():
        return {
            "exec_plan_safety_status": "blocked",
            "exec_plan_blocked_reason": "exec_plan_symlink",
            "exec_plan_required_fragments_present": required_fragments_present,
            "exec_plan_banned_fragments_present": banned_fragments_present,
        }

    try:
        exec_plan_text = exec_plan_path.read_text(encoding="utf-8")
    except OSError:
        return {
            "exec_plan_safety_status": "blocked",
            "exec_plan_blocked_reason": "exec_plan_read_error",
            "exec_plan_required_fragments_present": required_fragments_present,
            "exec_plan_banned_fragments_present": banned_fragments_present,
        }

    if not exec_plan_text:
        return {
            "exec_plan_safety_status": "blocked",
            "exec_plan_blocked_reason": "exec_plan_empty",
            "exec_plan_required_fragments_present": required_fragments_present,
            "exec_plan_banned_fragments_present": banned_fragments_present,
        }

    exec_plan_lines = exec_plan_text.splitlines()
    if len(exec_plan_lines) < 2 or exec_plan_lines[0] != "#!/usr/bin/env bash" or exec_plan_lines[1] != "set -euo pipefail":
        return {
            "exec_plan_safety_status": "blocked",
            "exec_plan_blocked_reason": "exec_plan_invalid_strict_header",
            "exec_plan_required_fragments_present": required_fragments_present,
            "exec_plan_banned_fragments_present": banned_fragments_present,
        }

    for fragment in _ONE_CYCLE_CONTROLLER_EXEC_PLAN_REQUIRED_FRAGMENTS:
        if fragment in exec_plan_text:
            required_fragments_present.append(fragment)
    approval_policy_fragment_present = ""
    for fragment in _ONE_CYCLE_CONTROLLER_EXEC_PLAN_APPROVAL_POLICY_ALLOWED_FRAGMENTS:
        if fragment in exec_plan_text:
            approval_policy_fragment_present = fragment
            break
    if approval_policy_fragment_present:
        required_fragments_present.append(approval_policy_fragment_present)
    required_fragments_ok = (
        len(required_fragments_present)
        == len(_ONE_CYCLE_CONTROLLER_EXEC_PLAN_REQUIRED_FRAGMENTS) + 1
    )
    if not required_fragments_ok:
        return {
            "exec_plan_safety_status": "blocked",
            "exec_plan_blocked_reason": "exec_plan_required_fragment_missing",
            "exec_plan_required_fragments_present": required_fragments_present,
            "exec_plan_banned_fragments_present": banned_fragments_present,
        }

    for fragment in _ONE_CYCLE_CONTROLLER_EXEC_PLAN_BANNED_FRAGMENTS:
        if fragment in exec_plan_text:
            banned_fragments_present.append(fragment)
    if banned_fragments_present:
        return {
            "exec_plan_safety_status": "blocked",
            "exec_plan_blocked_reason": "exec_plan_banned_fragment_present",
            "exec_plan_required_fragments_present": required_fragments_present,
            "exec_plan_banned_fragments_present": banned_fragments_present,
        }

    return {
        "exec_plan_safety_status": "safe",
        "exec_plan_blocked_reason": "none",
        "exec_plan_required_fragments_present": required_fragments_present,
        "exec_plan_banned_fragments_present": banned_fragments_present,
    }

def _build_one_cycle_post_execution_handoff(
    *,
    execution_repo_path: str,
    status: str,
    stop_reason: str,
    next_action: str,
    execution_attempted: bool,
    execution_exit_code: int,
    exec_plan_execution_status: str,
    one_cycle_controller_dir: Path,
    completed_result_source_path: Path,
) -> dict[str, Any]:
    _ = (
        status,
        stop_reason,
        next_action,
        execution_attempted,
        execution_exit_code,
        exec_plan_execution_status,
        completed_result_source_path,
    )

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

    def _read_bounded_text(path: Path, *, max_lines: int) -> tuple[bool, int, list[str], str]:
        if not path.exists():
            return False, 0, [], ""
        size_bytes = 0
        try:
            size_bytes = max(0, int(path.stat().st_size))
        except OSError:
            size_bytes = 0
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return True, size_bytes, [], ""
        lines = text.splitlines()
        return True, size_bytes, lines[:max_lines], text

    def _extract_stdout_blocked_reason(stdout_text: str) -> tuple[bool, str]:
        lines = stdout_text.splitlines()
        contains_blocked = any(
            _normalize_text(line, default="").strip().upper().startswith("BLOCKED")
            for line in lines
        )
        blocked_reason = ""
        marker_index = -1
        for idx, raw_line in enumerate(lines):
            normalized = _normalize_text(raw_line, default="").strip().lower()
            if normalized.startswith("specific blocked reason"):
                marker_index = idx
                suffix = _normalize_text(raw_line, default="")
                if ":" in suffix:
                    maybe_reason = suffix.split(":", 1)[1].strip()
                    if maybe_reason:
                        blocked_reason = maybe_reason
                break
        if marker_index >= 0 and not blocked_reason:
            for follow_line in lines[marker_index + 1 :]:
                maybe_reason = _normalize_text(follow_line, default="").strip()
                if maybe_reason:
                    blocked_reason = maybe_reason
                    break
        return contains_blocked, blocked_reason

    def _prompt334_safety_fields() -> dict[str, Any]:
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

    one_cycle_controller_dir = Path(one_cycle_controller_dir)
    diff_stat_path = one_cycle_controller_dir / "one_cycle_controller_diff_stat.txt"
    diff_name_status_path = one_cycle_controller_dir / "one_cycle_controller_diff_name_status.txt"
    diff_patch_path = one_cycle_controller_dir / "one_cycle_controller_diff.patch"
    review_request_path = one_cycle_controller_dir / "one_cycle_controller_review_request.md"
    review_handoff_path = one_cycle_controller_dir / "one_cycle_controller_review_handoff.json"

    prompt333_result_path = one_cycle_controller_dir / "local_codex_one_shot_execution_result.json"
    prompt333_receipt_v2_path = (
        one_cycle_controller_dir / "local_codex_one_shot_execution_receipt_v2.json"
    )
    prompt333_stdout_path = one_cycle_controller_dir / "local_codex_one_shot_execution_stdout.txt"
    prompt333_stderr_path = one_cycle_controller_dir / "local_codex_one_shot_execution_stderr.txt"
    prompt334_diff_capture_path = one_cycle_controller_dir / "local_post_codex_diff_capture.json"
    prompt334_outcome_path = one_cycle_controller_dir / "local_post_codex_execution_outcome.json"
    prompt334_route_path = one_cycle_controller_dir / "local_post_codex_route_decision.json"
    prompt334_receipt_path = one_cycle_controller_dir / "local_post_codex_diff_capture_receipt.json"

    prompt333_result_exists, prompt333_result_valid, prompt333_result_payload = _read_json_mapping(
        prompt333_result_path
    )
    prompt333_receipt_v2_exists, prompt333_receipt_v2_valid, prompt333_receipt_v2_payload = (
        _read_json_mapping(prompt333_receipt_v2_path)
    )
    prompt333_validation_errors: list[str] = []
    prompt333_blocked_reason = "none"
    prompt333_ready = True

    def _invalidate(reason: str, detail: str) -> None:
        nonlocal prompt333_ready, prompt333_blocked_reason
        prompt333_ready = False
        if prompt333_blocked_reason == "none":
            prompt333_blocked_reason = reason
        prompt333_validation_errors.append(detail)

    if not prompt333_result_exists:
        _invalidate(
            "missing_prompt333_execution_result_artifact",
            "missing_prompt333_execution_result_artifact",
        )
    elif not prompt333_result_valid:
        _invalidate(
            "invalid_prompt333_execution_result_artifact",
            "invalid_prompt333_execution_result_artifact",
        )

    if not prompt333_receipt_v2_exists:
        _invalidate(
            "missing_prompt333_execution_receipt_v2_artifact",
            "missing_prompt333_execution_receipt_v2_artifact",
        )
    elif not prompt333_receipt_v2_valid:
        _invalidate(
            "invalid_prompt333_execution_receipt_v2_artifact",
            "invalid_prompt333_execution_receipt_v2_artifact",
        )

    if prompt333_result_valid:
        expected_fields: tuple[tuple[str, Any], ...] = (
            ("schema_version", _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION),
            ("execution_schema_version", _LOCAL_CODEX_ONE_SHOT_EXECUTION_SCHEMA_VERSION),
            ("status", "completed"),
            ("execution_status", "completed"),
            ("blocked_reason", "none"),
            (
                "readiness_reason",
                "local_codex_one_shot_handoff_valid_and_tracked_worktree_clean",
            ),
            ("codex_invoked", True),
            ("execution_attempted", True),
            ("execution_completed", True),
            ("max_codex_invocations", 1),
            ("codex_invocation_count", 1),
        )
        field_failure_reasons = {
            "schema_version": "prompt333_execution_result_schema_version_mismatch",
            "execution_schema_version": "prompt333_execution_result_execution_schema_version_mismatch",
            "status": "prompt333_execution_result_status_not_completed",
            "execution_status": "prompt333_execution_result_execution_status_not_completed",
            "blocked_reason": "prompt333_execution_result_blocked_reason_not_none",
            "readiness_reason": "prompt333_execution_result_readiness_reason_mismatch",
            "codex_invoked": "prompt333_execution_result_codex_not_invoked",
            "execution_attempted": "prompt333_execution_result_execution_not_attempted",
            "execution_completed": "prompt333_execution_result_execution_not_completed",
            "max_codex_invocations": "prompt333_execution_result_max_codex_invocations_not_one",
            "codex_invocation_count": "prompt333_execution_result_codex_invocation_count_not_one",
        }
        for field_name, expected_value in expected_fields:
            actual_value = prompt333_result_payload.get(field_name)
            if actual_value != expected_value:
                _invalidate(
                    field_failure_reasons[field_name],
                    f"{field_name}_mismatch",
                )
                break
        raw_execution_exit_code = prompt333_result_payload.get("execution_exit_code")
        parsed_execution_exit_code = _as_optional_int(raw_execution_exit_code)
        if parsed_execution_exit_code is None:
            _invalidate(
                "prompt333_execution_result_execution_exit_code_not_integer",
                "execution_exit_code_not_integer",
            )
        execution_result = _normalize_text(
            prompt333_result_payload.get("execution_result"),
            default="",
        )
        if execution_result not in {"codex_one_shot_completed", "codex_one_shot_failed"}:
            _invalidate(
                "prompt333_execution_result_execution_result_invalid",
                "execution_result_invalid",
            )
        result_next_action = _normalize_text(
            prompt333_result_payload.get("next_action"),
            default="",
        )
        if result_next_action not in {
            "prepare_local_git_diff_capture",
            "manual_review_local_codex_one_shot_execution_failure",
        }:
            _invalidate(
                "prompt333_execution_result_next_action_invalid",
                "next_action_invalid",
            )
        validation_errors_field = prompt333_result_payload.get("validation_errors")
        if _normalize_string_list(validation_errors_field):
            _invalidate(
                "prompt333_execution_result_validation_errors_not_empty",
                "validation_errors_not_empty",
            )
        if "command_argv_mismatch_source" in prompt333_result_payload:
            if (
                _normalize_text(
                    prompt333_result_payload.get("command_argv_mismatch_source"),
                    default="",
                )
                != "none"
            ):
                _invalidate(
                    "prompt333_execution_result_command_argv_mismatch_source_not_none",
                    "command_argv_mismatch_source_invalid",
                )
        if "authoritative_handoff_command_argv_equal_expected" in prompt333_result_payload:
            if not bool(
                prompt333_result_payload.get("authoritative_handoff_command_argv_equal_expected")
            ):
                _invalidate(
                    "prompt333_execution_result_authoritative_handoff_command_argv_not_equal_expected",
                    "authoritative_handoff_command_argv_equal_expected_invalid",
                )
        if "supporting_receipt_command_argv_equal_expected" in prompt333_result_payload:
            supporting_value = prompt333_result_payload.get(
                "supporting_receipt_command_argv_equal_expected"
            )
            if supporting_value is not None and bool(supporting_value) is not True:
                _invalidate(
                    "prompt333_execution_result_supporting_receipt_command_argv_not_equal_expected",
                    "supporting_receipt_command_argv_equal_expected_invalid",
                )

    prompt333_execution_exit_code_value = _as_optional_int(
        prompt333_result_payload.get("execution_exit_code")
    )
    prompt333_execution_exit_code = (
        int(prompt333_execution_exit_code_value)
        if prompt333_execution_exit_code_value is not None
        else -1
    )
    prompt333_execution_attempted = bool(
        prompt333_result_payload.get("execution_attempted", False)
    )
    prompt333_codex_invoked = bool(prompt333_result_payload.get("codex_invoked", False))
    prompt333_prompt_exists = bool(prompt333_result_payload.get("prompt_exists", False))
    prompt333_current_run_blocked_reason = (
        "none" if prompt333_ready else "current_prompt333_execution_artifacts_not_completed"
    )
    prompt333_current_run_blocked_detail = (
        "none"
        if prompt333_ready
        else (
            prompt333_blocked_reason
            if prompt333_blocked_reason != "none"
            else (
                prompt333_validation_errors[0]
                if prompt333_validation_errors
                else "prompt333_execution_artifacts_not_ready"
            )
        )
    )

    stdout_exists, stdout_size_bytes, stdout_head_lines, stdout_text = _read_bounded_text(
        prompt333_stdout_path,
        max_lines=40,
    )
    stderr_exists, stderr_size_bytes, stderr_head_lines, stderr_text = _read_bounded_text(
        prompt333_stderr_path,
        max_lines=40,
    )
    stdout_contains_blocked, stdout_blocked_reason = _extract_stdout_blocked_reason(stdout_text)
    prompt333_stdout_artifact_stale = bool(
        stdout_exists and not (prompt333_execution_attempted and prompt333_codex_invoked)
    )
    if prompt333_stdout_artifact_stale:
        stdout_contains_blocked = False
        stdout_blocked_reason = ""

    git_commands: dict[str, list[str]] = {
        "status_short": ["status", "--short", "--untracked-files=no"],
        "diff_stat": ["diff", "--stat"],
        "diff_name_status": ["diff", "--name-status"],
        "diff_numstat": ["diff", "--numstat"],
        "diff_name_only": ["diff", "--name-only"],
        "cached_diff_stat": ["diff", "--cached", "--stat"],
        "cached_diff_name_status": ["diff", "--cached", "--name-status"],
        "cached_diff_name_only": ["diff", "--cached", "--name-only"],
    }
    git_command_exit_codes: dict[str, int] = {}
    git_command_stdout: dict[str, str] = {}
    git_capture_failed = False
    if prompt333_ready:
        for key, args in git_commands.items():
            try:
                cp = _run_git(execution_repo_path, args, timeout_seconds=20.0)
            except (OSError, subprocess.TimeoutExpired):
                git_command_exit_codes[key] = 124
                git_command_stdout[key] = ""
                git_capture_failed = True
                continue
            git_command_exit_codes[key] = int(cp.returncode)
            git_command_stdout[key] = _normalize_text(cp.stdout, default="")
            if cp.returncode != 0:
                git_capture_failed = True

    status_short_lines = (
        [
            _normalize_text(line, default="")
            for line in git_command_stdout.get("status_short", "").splitlines()
            if _normalize_text(line, default="").strip()
        ]
        if prompt333_ready
        else []
    )
    unstaged_tracked_files = (
        sorted(
            {
                _normalize_text(line, default="").strip()
                for line in git_command_stdout.get("diff_name_only", "").splitlines()
                if _normalize_text(line, default="").strip()
            }
        )
        if prompt333_ready
        else []
    )
    staged_tracked_files = (
        sorted(
            {
                _normalize_text(line, default="").strip()
                for line in git_command_stdout.get("cached_diff_name_only", "").splitlines()
                if _normalize_text(line, default="").strip()
            }
        )
        if prompt333_ready
        else []
    )
    changed_tracked_files = sorted(set(unstaged_tracked_files) | set(staged_tracked_files))
    changed_tracked_file_count = len(changed_tracked_files)
    staged_tracked_file_count = len(staged_tracked_files)
    unstaged_tracked_file_count = len(unstaged_tracked_files)
    worktree_clean_for_tracked_files = changed_tracked_file_count == 0 and not status_short_lines
    staged_changes_present = staged_tracked_file_count > 0
    unstaged_changes_present = unstaged_tracked_file_count > 0
    local_diff_present = changed_tracked_file_count > 0
    local_diff_stat_text = _normalize_text(git_command_stdout.get("diff_stat"), default="").strip()
    local_diff_name_status_lines = [
        _normalize_text(line, default="").strip()
        for line in git_command_stdout.get("diff_name_status", "").splitlines()
        if _normalize_text(line, default="").strip()
    ]
    local_diff_numstat_lines = [
        _normalize_text(line, default="").strip()
        for line in git_command_stdout.get("diff_numstat", "").splitlines()
        if _normalize_text(line, default="").strip()
    ]
    local_diff_name_only_lines = [
        _normalize_text(line, default="").strip()
        for line in git_command_stdout.get("diff_name_only", "").splitlines()
        if _normalize_text(line, default="").strip()
    ]

    if not prompt333_ready:
        codex_outcome_classification = "prompt333_execution_not_ready"
    elif prompt333_execution_exit_code == 0 and not stdout_contains_blocked and changed_tracked_file_count > 0:
        codex_outcome_classification = "codex_task_success_with_tracked_changes"
    elif prompt333_execution_exit_code == 0 and not stdout_contains_blocked and changed_tracked_file_count == 0:
        codex_outcome_classification = "codex_task_success_no_tracked_changes"
    elif prompt333_execution_exit_code == 0 and stdout_contains_blocked and changed_tracked_file_count == 0:
        codex_outcome_classification = "codex_task_blocked_no_tracked_changes"
    elif prompt333_execution_exit_code == 0 and stdout_contains_blocked and changed_tracked_file_count > 0:
        codex_outcome_classification = "codex_task_blocked_with_tracked_changes"
    elif prompt333_execution_exit_code != 0 and changed_tracked_file_count == 0:
        codex_outcome_classification = "codex_task_failed_no_tracked_changes"
    else:
        codex_outcome_classification = "codex_task_failed_with_tracked_changes"

    route_decision = "manual_review_prompt333_execution_artifacts"
    route_next_action = "manual_review_prompt333_execution_artifacts"
    approve_commit_tag_allowed = False
    targeted_contract_fix_recommended = False
    contract_fix_reason = ""
    if codex_outcome_classification == "codex_task_success_with_tracked_changes":
        route_decision = "prepare_review_for_tracked_changes"
        route_next_action = "prepare_local_review_handoff"
    elif codex_outcome_classification == "codex_task_success_no_tracked_changes":
        route_decision = "prepare_no_change_review"
        route_next_action = "manual_review_no_tracked_changes_after_codex_success"
    elif codex_outcome_classification == "codex_task_blocked_no_tracked_changes":
        route_decision = "prepare_contract_handoff_fix"
        route_next_action = "prepare_targeted_contract_fix_prompt"
        targeted_contract_fix_recommended = True
        contract_fix_reason = stdout_blocked_reason
    elif codex_outcome_classification == "codex_task_blocked_with_tracked_changes":
        route_decision = "prepare_blocked_with_changes_review"
        route_next_action = "manual_review_blocked_codex_with_tracked_changes"
        targeted_contract_fix_recommended = True
        contract_fix_reason = stdout_blocked_reason
    elif codex_outcome_classification == "codex_task_failed_no_tracked_changes":
        route_decision = "manual_review_codex_failure"
        route_next_action = "manual_review_local_codex_one_shot_execution_failure"
    elif codex_outcome_classification == "codex_task_failed_with_tracked_changes":
        route_decision = "manual_review_codex_failure_with_changes"
        route_next_action = "manual_review_failed_codex_with_tracked_changes"

    local_post_codex_diff_capture_status = "completed"
    local_post_codex_diff_capture_blocked_reason = "none"
    if not prompt333_ready:
        local_post_codex_diff_capture_status = "blocked"
        local_post_codex_diff_capture_blocked_reason = prompt333_current_run_blocked_reason
    elif git_capture_failed:
        local_post_codex_diff_capture_status = "blocked"
        local_post_codex_diff_capture_blocked_reason = "local_post_codex_git_diff_capture_failed"

    local_post_codex_outcome_status = "completed" if prompt333_ready else "blocked"
    local_post_codex_route_status = "completed" if prompt333_ready else "blocked"

    safety_fields = _prompt334_safety_fields()
    prompt333_validation_errors_normalized = _normalize_string_list(prompt333_validation_errors)
    diff_capture_payload: dict[str, Any] = {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "diff_capture_schema_version": _LOCAL_POST_CODEX_DIFF_CAPTURE_SCHEMA_VERSION,
        "source_prompt": "prompt334",
        "status": local_post_codex_diff_capture_status,
        "blocked_reason": local_post_codex_diff_capture_blocked_reason,
        "next_action": route_next_action,
        "execution_repo_path": _normalize_text(execution_repo_path, default=""),
        "prompt333_result_path": str(prompt333_result_path),
        "prompt333_receipt_v2_path": str(prompt333_receipt_v2_path),
        "prompt333_stdout_path": str(prompt333_stdout_path),
        "prompt333_stderr_path": str(prompt333_stderr_path),
        "prompt333_result_exists": prompt333_result_exists,
        "prompt333_result_valid": prompt333_result_valid,
        "prompt333_receipt_v2_exists": prompt333_receipt_v2_exists,
        "prompt333_receipt_v2_valid": prompt333_receipt_v2_valid,
        "prompt333_validation_errors": prompt333_validation_errors_normalized,
        "prompt333_execution_attempted": prompt333_execution_attempted,
        "prompt333_codex_invoked": prompt333_codex_invoked,
        "prompt333_prompt_exists": prompt333_prompt_exists,
        "prompt333_current_run_blocked_reason": prompt333_current_run_blocked_reason,
        "prompt333_current_run_blocked_detail": prompt333_current_run_blocked_detail,
        "prompt333_stdout_artifact_stale": prompt333_stdout_artifact_stale,
        "changed_tracked_files": changed_tracked_files,
        "staged_tracked_files": staged_tracked_files,
        "unstaged_tracked_files": unstaged_tracked_files,
        "changed_tracked_file_count": changed_tracked_file_count,
        "staged_tracked_file_count": staged_tracked_file_count,
        "unstaged_tracked_file_count": unstaged_tracked_file_count,
        "worktree_clean_for_tracked_files": worktree_clean_for_tracked_files,
        "staged_changes_present": staged_changes_present,
        "unstaged_changes_present": unstaged_changes_present,
        "local_diff_present": local_diff_present,
        "local_diff_stat_text": local_diff_stat_text,
        "local_diff_name_status_lines": local_diff_name_status_lines,
        "local_diff_numstat_lines": local_diff_numstat_lines,
        "local_diff_name_only_lines": local_diff_name_only_lines,
        "status_short_lines": status_short_lines,
        "cached_diff_stat_text": _normalize_text(
            git_command_stdout.get("cached_diff_stat"),
            default="",
        ).strip(),
        "cached_diff_name_status_lines": [
            _normalize_text(line, default="").strip()
            for line in git_command_stdout.get("cached_diff_name_status", "").splitlines()
            if _normalize_text(line, default="").strip()
        ],
        "cached_diff_name_only_lines": staged_tracked_files,
        "git_diff_commands": {key: list(value) for key, value in git_commands.items()},
        "git_diff_command_exit_codes": dict(git_command_exit_codes),
        "stdout_exists": stdout_exists,
        "stderr_exists": stderr_exists,
        "stdout_size_bytes": stdout_size_bytes,
        "stderr_size_bytes": stderr_size_bytes,
        "stdout_head_lines": stdout_head_lines,
        "stderr_head_lines": stderr_head_lines,
        "stdout_contains_blocked": stdout_contains_blocked,
        "stdout_blocked_reason": stdout_blocked_reason,
        "local_post_codex_diff_capture_status": local_post_codex_diff_capture_status,
        "local_post_codex_diff_capture_blocked_reason": local_post_codex_diff_capture_blocked_reason,
        "local_post_codex_diff_capture_next_action": route_next_action,
        "local_post_codex_diff_capture_worktree_clean_for_tracked_files": (
            worktree_clean_for_tracked_files
        ),
        "local_post_codex_diff_capture_changed_tracked_file_count": changed_tracked_file_count,
        **safety_fields,
    }

    outcome_payload: dict[str, Any] = {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "outcome_schema_version": _LOCAL_POST_CODEX_EXECUTION_OUTCOME_SCHEMA_VERSION,
        "source_prompt": "prompt334",
        "status": local_post_codex_outcome_status,
        "blocked_reason": prompt333_current_run_blocked_reason if not prompt333_ready else "none",
        "prompt333_current_run_blocked_detail": prompt333_current_run_blocked_detail,
        "next_action": route_next_action,
        "prompt333_result_path": str(prompt333_result_path),
        "prompt333_receipt_v2_path": str(prompt333_receipt_v2_path),
        "prompt333_execution_attempted": prompt333_execution_attempted,
        "prompt333_codex_invoked": prompt333_codex_invoked,
        "prompt333_prompt_exists": prompt333_prompt_exists,
        "prompt333_stdout_artifact_stale": prompt333_stdout_artifact_stale,
        "execution_exit_code": prompt333_execution_exit_code,
        "stdout_contains_blocked": stdout_contains_blocked,
        "stdout_blocked_reason": stdout_blocked_reason,
        "changed_tracked_file_count": changed_tracked_file_count,
        "changed_tracked_files": changed_tracked_files,
        "codex_outcome_classification": codex_outcome_classification,
        "local_post_codex_outcome_status": local_post_codex_outcome_status,
        "local_post_codex_outcome_classification": codex_outcome_classification,
        "local_post_codex_stdout_contains_blocked": stdout_contains_blocked,
        "local_post_codex_stdout_blocked_reason": stdout_blocked_reason,
        **safety_fields,
    }

    route_payload: dict[str, Any] = {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "route_decision_schema_version": _LOCAL_POST_CODEX_ROUTE_DECISION_SCHEMA_VERSION,
        "source_prompt": "prompt334",
        "status": local_post_codex_route_status,
        "blocked_reason": prompt333_current_run_blocked_reason if not prompt333_ready else "none",
        "prompt333_current_run_blocked_detail": prompt333_current_run_blocked_detail,
        "prompt333_execution_attempted": prompt333_execution_attempted,
        "prompt333_codex_invoked": prompt333_codex_invoked,
        "prompt333_prompt_exists": prompt333_prompt_exists,
        "prompt333_stdout_artifact_stale": prompt333_stdout_artifact_stale,
        "codex_outcome_classification": codex_outcome_classification,
        "route_decision": route_decision,
        "next_action": route_next_action,
        "approve_commit_tag_allowed": approve_commit_tag_allowed,
        "targeted_contract_fix_recommended": targeted_contract_fix_recommended,
        "contract_fix_reason": contract_fix_reason,
        "local_post_codex_route_status": local_post_codex_route_status,
        "local_post_codex_route_decision": route_decision,
        "local_post_codex_route_next_action": route_next_action,
        "local_post_codex_route_targeted_contract_fix_recommended": (
            targeted_contract_fix_recommended
        ),
        "local_post_codex_route_approve_commit_tag_allowed": approve_commit_tag_allowed,
        **safety_fields,
    }

    artifact_write_status = {
        "local_post_codex_diff_capture_written": False,
        "local_post_codex_execution_outcome_written": False,
        "local_post_codex_route_decision_written": False,
    }
    artifact_write_errors: list[str] = []
    try:
        one_cycle_controller_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        artifact_write_errors.append("local_post_codex_artifact_directory_create_failed")
    else:
        try:
            _write_json(prompt334_diff_capture_path, diff_capture_payload)
            artifact_write_status["local_post_codex_diff_capture_written"] = True
        except OSError:
            artifact_write_errors.append("local_post_codex_diff_capture_write_failed")
        try:
            _write_json(prompt334_outcome_path, outcome_payload)
            artifact_write_status["local_post_codex_execution_outcome_written"] = True
        except OSError:
            artifact_write_errors.append("local_post_codex_execution_outcome_write_failed")
        try:
            _write_json(prompt334_route_path, route_payload)
            artifact_write_status["local_post_codex_route_decision_written"] = True
        except OSError:
            artifact_write_errors.append("local_post_codex_route_decision_write_failed")
        try:
            diff_stat_path.write_text(
                (local_diff_stat_text + "\n") if local_diff_stat_text else "",
                encoding="utf-8",
            )
            diff_name_status_path.write_text(
                ("\n".join(local_diff_name_status_lines) + "\n")
                if local_diff_name_status_lines
                else "",
                encoding="utf-8",
            )
            diff_patch_path.write_text("", encoding="utf-8")
        except OSError:
            pass

    receipt_payload: dict[str, Any] = {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "diff_capture_schema_version": _LOCAL_POST_CODEX_DIFF_CAPTURE_SCHEMA_VERSION,
        "receipt_schema_version": "local_post_codex_diff_capture_receipt_v1",
        "source_prompt": "prompt334",
        "status": "completed" if not artifact_write_errors else "blocked",
        "blocked_reason": "none"
        if not artifact_write_errors
        else artifact_write_errors[0],
        "next_action": route_next_action,
        "artifact_paths": {
            "local_post_codex_diff_capture_path": str(prompt334_diff_capture_path),
            "local_post_codex_execution_outcome_path": str(prompt334_outcome_path),
            "local_post_codex_route_decision_path": str(prompt334_route_path),
            "local_post_codex_diff_capture_receipt_path": str(prompt334_receipt_path),
        },
        "artifact_write_status": artifact_write_status,
        "artifact_write_errors": artifact_write_errors,
        "codex_outcome_classification": codex_outcome_classification,
        "route_decision": route_decision,
        "route_next_action": route_next_action,
        "approve_commit_tag_allowed": approve_commit_tag_allowed,
        "targeted_contract_fix_recommended": targeted_contract_fix_recommended,
        "contract_fix_reason": contract_fix_reason,
        "prompt333_current_run_blocked_reason": prompt333_current_run_blocked_reason,
        "prompt333_current_run_blocked_detail": prompt333_current_run_blocked_detail,
        "prompt333_execution_attempted": prompt333_execution_attempted,
        "prompt333_codex_invoked": prompt333_codex_invoked,
        "prompt333_prompt_exists": prompt333_prompt_exists,
        "prompt333_stdout_artifact_stale": prompt333_stdout_artifact_stale,
        "local_post_codex_diff_capture_status": local_post_codex_diff_capture_status,
        "local_post_codex_diff_capture_blocked_reason": local_post_codex_diff_capture_blocked_reason,
        "local_post_codex_outcome_status": local_post_codex_outcome_status,
        "local_post_codex_outcome_classification": codex_outcome_classification,
        "local_post_codex_stdout_contains_blocked": stdout_contains_blocked,
        "local_post_codex_stdout_blocked_reason": stdout_blocked_reason,
        "local_post_codex_route_status": local_post_codex_route_status,
        "local_post_codex_route_decision": route_decision,
        "local_post_codex_route_next_action": route_next_action,
        "local_post_codex_route_targeted_contract_fix_recommended": (
            targeted_contract_fix_recommended
        ),
        "local_post_codex_route_approve_commit_tag_allowed": approve_commit_tag_allowed,
        **safety_fields,
    }
    try:
        _write_json(prompt334_receipt_path, receipt_payload)
    except OSError:
        pass

    completed_result_source_status = "available" if prompt333_ready else "not_completed"
    review_request_status = "not_started"
    review_request_blocked_reason = "prompt334_route_decision_boundary_only"

    return {
        "next_action": route_next_action,
        "diff_capture_status": local_post_codex_diff_capture_status,
        "diff_capture_blocked_reason": local_post_codex_diff_capture_blocked_reason,
        "diff_stat_path": str(diff_stat_path),
        "diff_name_status_path": str(diff_name_status_path),
        "diff_patch_path": str(diff_patch_path),
        "review_request_status": review_request_status,
        "review_request_blocked_reason": review_request_blocked_reason,
        "review_request_path": str(review_request_path),
        "review_handoff_path": str(review_handoff_path),
        "completed_result_source_path": str(completed_result_source_path),
        "completed_result_source_status": completed_result_source_status,
        "local_post_codex_diff_capture_status": local_post_codex_diff_capture_status,
        "local_post_codex_diff_capture_blocked_reason": local_post_codex_diff_capture_blocked_reason,
        "local_post_codex_diff_capture_next_action": route_next_action,
        "local_post_codex_diff_capture_worktree_clean_for_tracked_files": (
            worktree_clean_for_tracked_files
        ),
        "local_post_codex_diff_capture_changed_tracked_file_count": changed_tracked_file_count,
        "local_post_codex_outcome_status": local_post_codex_outcome_status,
        "local_post_codex_outcome_classification": codex_outcome_classification,
        "local_post_codex_stdout_contains_blocked": stdout_contains_blocked,
        "local_post_codex_stdout_blocked_reason": stdout_blocked_reason,
        "local_post_codex_route_status": local_post_codex_route_status,
        "local_post_codex_route_decision": route_decision,
        "local_post_codex_route_next_action": route_next_action,
        "local_post_codex_route_targeted_contract_fix_recommended": (
            targeted_contract_fix_recommended
        ),
        "local_post_codex_route_approve_commit_tag_allowed": approve_commit_tag_allowed,
        "prompt333_current_run_blocked_reason": prompt333_current_run_blocked_reason,
        "prompt333_current_run_blocked_detail": prompt333_current_run_blocked_detail,
        "prompt333_execution_attempted": prompt333_execution_attempted,
        "prompt333_codex_invoked": prompt333_codex_invoked,
        "prompt333_prompt_exists": prompt333_prompt_exists,
        "prompt333_stdout_artifact_stale": prompt333_stdout_artifact_stale,
        "local_post_codex_diff_capture_path": str(prompt334_diff_capture_path),
        "local_post_codex_execution_outcome_path": str(prompt334_outcome_path),
        "local_post_codex_route_decision_path": str(prompt334_route_path),
        "local_post_codex_diff_capture_receipt_path": str(prompt334_receipt_path),
    }

def _build_one_cycle_review_handoff_decision_state(
    *,
    review_handoff_path: Path,
) -> dict[str, str]:
    default_state = {
        "review_handoff_decision_status": "manual_review_required",
        "tracked_diff_status": "unknown",
        "no_diff_review_status": "blocked",
        "no_diff_reason": "review_handoff_missing_or_invalid",
        "review_handoff_decision_source_path": str(review_handoff_path),
        "review_handoff_decision_next_action": "manual_review_required",
    }
    if not review_handoff_path.exists():
        return default_state
    try:
        payload = json.loads(review_handoff_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return default_state
    if not isinstance(payload, Mapping):
        return default_state
    status = _normalize_text(payload.get("status"), default="")
    review_request_status = _normalize_text(payload.get("review_request_status"), default="")
    diff_capture_status = _normalize_text(payload.get("diff_capture_status"), default="")
    if status != "ready" or review_request_status != "ready" or diff_capture_status != "completed":
        return default_state
    tracked_diff_present = payload.get("tracked_diff_present")
    if tracked_diff_present is True:
        return {
            "review_handoff_decision_status": "awaiting_diff_review_response",
            "tracked_diff_status": "present",
            "no_diff_review_status": "not_applicable",
            "no_diff_reason": "tracked_diff_present",
            "review_handoff_decision_source_path": str(review_handoff_path),
            "review_handoff_decision_next_action": "wait_for_chatgpt_diff_review_response",
        }
    if tracked_diff_present is False:
        return {
            "review_handoff_decision_status": "no_diff_pending_decision",
            "tracked_diff_status": "absent",
            "no_diff_review_status": "ready",
            "no_diff_reason": "no_tracked_diff_present",
            "review_handoff_decision_source_path": str(review_handoff_path),
            "review_handoff_decision_next_action": "prepare_next_codex_prompt_or_manual_decision",
        }
    return default_state

def _build_review_response_assimilation_state(
    *,
    review_response_path: Path,
    targeted_fix_prompt_path: Path,
) -> dict[str, str]:
    default_state = {
        "review_response_status": "missing",
        "review_response_decision": "none",
        "review_response_reason": "",
        "review_response_path": str(review_response_path),
        "review_response_next_action": "wait_for_chatgpt_diff_review_response",
        "targeted_fix_prompt_status": "not_applicable",
        "targeted_fix_prompt_text": "",
        "targeted_fix_prompt_path": "",
    }
    if not review_response_path.exists():
        return default_state

    try:
        payload = json.loads(review_response_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return {
            "review_response_status": "invalid",
            "review_response_decision": "none",
            "review_response_reason": "",
            "review_response_path": str(review_response_path),
            "review_response_next_action": "manual_review_required",
            "targeted_fix_prompt_status": "blocked",
            "targeted_fix_prompt_text": "",
            "targeted_fix_prompt_path": "",
        }
    if not isinstance(payload, Mapping):
        return {
            "review_response_status": "invalid",
            "review_response_decision": "none",
            "review_response_reason": "",
            "review_response_path": str(review_response_path),
            "review_response_next_action": "manual_review_required",
            "targeted_fix_prompt_status": "blocked",
            "targeted_fix_prompt_text": "",
            "targeted_fix_prompt_path": "",
        }

    decision = _normalize_text(payload.get("decision"), default="").lower()
    reason = _normalize_text(payload.get("reason"), default="")
    if decision not in {"approve", "reject", "targeted_fix"}:
        return {
            "review_response_status": "unsupported",
            "review_response_decision": "none",
            "review_response_reason": "",
            "review_response_path": str(review_response_path),
            "review_response_next_action": "manual_review_required",
            "targeted_fix_prompt_status": "blocked",
            "targeted_fix_prompt_text": "",
            "targeted_fix_prompt_path": "",
        }
    if decision == "approve":
        return {
            "review_response_status": "available",
            "review_response_decision": "approve",
            "review_response_reason": reason,
            "review_response_path": str(review_response_path),
            "review_response_next_action": "prepare_approve_route_decision",
            "targeted_fix_prompt_status": "not_applicable",
            "targeted_fix_prompt_text": "",
            "targeted_fix_prompt_path": "",
        }
    if decision == "reject":
        return {
            "review_response_status": "available",
            "review_response_decision": "reject",
            "review_response_reason": reason,
            "review_response_path": str(review_response_path),
            "review_response_next_action": "prepare_reject_route_decision",
            "targeted_fix_prompt_status": "not_applicable",
            "targeted_fix_prompt_text": "",
            "targeted_fix_prompt_path": "",
        }

    targeted_fix_prompt_text = _normalize_text(payload.get("targeted_fix_prompt"), default="")
    if not targeted_fix_prompt_text:
        return {
            "review_response_status": "invalid",
            "review_response_decision": "targeted_fix",
            "review_response_reason": reason,
            "review_response_path": str(review_response_path),
            "review_response_next_action": "manual_review_required",
            "targeted_fix_prompt_status": "blocked",
            "targeted_fix_prompt_text": "",
            "targeted_fix_prompt_path": "",
        }
    deterministic_prompt_text = targeted_fix_prompt_text.replace("\r\n", "\n").replace("\r", "\n")
    try:
        targeted_fix_prompt_path.parent.mkdir(parents=True, exist_ok=True)
        targeted_fix_prompt_path.write_text(deterministic_prompt_text + "\n", encoding="utf-8")
    except OSError:
        return {
            "review_response_status": "insufficient_truth",
            "review_response_decision": "insufficient_truth",
            "review_response_reason": "",
            "review_response_path": str(review_response_path),
            "review_response_next_action": "insufficient_truth",
            "targeted_fix_prompt_status": "insufficient_truth",
            "targeted_fix_prompt_text": "",
            "targeted_fix_prompt_path": "",
        }
    return {
        "review_response_status": "available",
        "review_response_decision": "targeted_fix",
        "review_response_reason": reason,
        "review_response_path": str(review_response_path),
        "review_response_next_action": "prepare_targeted_fix_route_decision",
        "targeted_fix_prompt_status": "ready",
        "targeted_fix_prompt_text": deterministic_prompt_text,
        "targeted_fix_prompt_path": str(targeted_fix_prompt_path),
    }

def _build_review_route_decision_state(
    *,
    review_response_status: str,
    review_response_decision: str,
    review_response_next_action: str,
    targeted_fix_prompt_status: str,
    targeted_fix_prompt_path: str,
    review_handoff_decision_status: str,
    tracked_diff_status: str,
    review_handoff_decision_next_action: str,
) -> dict[str, Any]:
    source = (
        "review_response_status="
        f"{review_response_status};"
        "review_response_decision="
        f"{review_response_decision};"
        "review_response_next_action="
        f"{review_response_next_action};"
        "targeted_fix_prompt_status="
        f"{targeted_fix_prompt_status};"
        "targeted_fix_prompt_path="
        f"{targeted_fix_prompt_path};"
        "review_handoff_decision_status="
        f"{review_handoff_decision_status};"
        "tracked_diff_status="
        f"{tracked_diff_status};"
        "review_handoff_decision_next_action="
        f"{review_handoff_decision_next_action}"
    )
    default_state: dict[str, Any] = {
        "review_route_status": "insufficient_truth",
        "review_route_decision": "insufficient_truth",
        "review_route_reason": "insufficient_truth",
        "review_route_next_action": "insufficient_truth",
        "review_route_blocked_reason": "insufficient_truth",
        "review_route_source": source,
        "review_route_targeted_fix_prompt_path": "",
        "review_route_should_prepare_commit": False,
        "review_route_should_prepare_targeted_fix": False,
        "review_route_should_prepare_reject": False,
    }

    if review_response_status == "missing":
        return {
            "review_route_status": "waiting_for_review_response",
            "review_route_decision": "none",
            "review_route_reason": "review_response_missing",
            "review_route_next_action": "wait_for_chatgpt_diff_review_response",
            "review_route_blocked_reason": "review_response_missing",
            "review_route_source": source,
            "review_route_targeted_fix_prompt_path": "",
            "review_route_should_prepare_commit": False,
            "review_route_should_prepare_targeted_fix": False,
            "review_route_should_prepare_reject": False,
        }
    if review_response_status == "invalid":
        return {
            "review_route_status": "blocked",
            "review_route_decision": (
                "targeted_fix" if review_response_decision == "targeted_fix" else "none"
            ),
            "review_route_reason": "review_response_invalid",
            "review_route_next_action": "manual_review_required",
            "review_route_blocked_reason": "review_response_invalid",
            "review_route_source": source,
            "review_route_targeted_fix_prompt_path": "",
            "review_route_should_prepare_commit": False,
            "review_route_should_prepare_targeted_fix": False,
            "review_route_should_prepare_reject": False,
        }
    if review_response_status == "unsupported":
        return {
            "review_route_status": "blocked",
            "review_route_decision": "none",
            "review_route_reason": "review_response_unsupported",
            "review_route_next_action": "manual_review_required",
            "review_route_blocked_reason": "review_response_unsupported",
            "review_route_source": source,
            "review_route_targeted_fix_prompt_path": "",
            "review_route_should_prepare_commit": False,
            "review_route_should_prepare_targeted_fix": False,
            "review_route_should_prepare_reject": False,
        }
    if review_response_status != "available":
        return default_state
    if review_response_decision == "approve":
        return {
            "review_route_status": "route_ready",
            "review_route_decision": "approve",
            "review_route_reason": "approve_review_response_available",
            "review_route_next_action": "prepare_approve_commit_tag_boundary",
            "review_route_blocked_reason": "none",
            "review_route_source": source,
            "review_route_targeted_fix_prompt_path": "",
            "review_route_should_prepare_commit": True,
            "review_route_should_prepare_targeted_fix": False,
            "review_route_should_prepare_reject": False,
        }
    if review_response_decision == "reject":
        return {
            "review_route_status": "route_ready",
            "review_route_decision": "reject",
            "review_route_reason": "reject_review_response_available",
            "review_route_next_action": "prepare_reject_boundary",
            "review_route_blocked_reason": "none",
            "review_route_source": source,
            "review_route_targeted_fix_prompt_path": "",
            "review_route_should_prepare_commit": False,
            "review_route_should_prepare_targeted_fix": False,
            "review_route_should_prepare_reject": True,
        }
    if review_response_decision == "targeted_fix":
        normalized_path = _normalize_text(targeted_fix_prompt_path, default="")
        if targeted_fix_prompt_status == "ready" and normalized_path:
            return {
                "review_route_status": "route_ready",
                "review_route_decision": "targeted_fix",
                "review_route_reason": "targeted_fix_review_response_available",
                "review_route_next_action": "prepare_targeted_fix_prompt_boundary",
                "review_route_blocked_reason": "none",
                "review_route_source": source,
                "review_route_targeted_fix_prompt_path": normalized_path,
                "review_route_should_prepare_commit": False,
                "review_route_should_prepare_targeted_fix": True,
                "review_route_should_prepare_reject": False,
            }
        return {
            "review_route_status": "blocked",
            "review_route_decision": "targeted_fix",
            "review_route_reason": "targeted_fix_prompt_not_ready",
            "review_route_next_action": "manual_review_required",
            "review_route_blocked_reason": "targeted_fix_prompt_not_ready",
            "review_route_source": source,
            "review_route_targeted_fix_prompt_path": "",
            "review_route_should_prepare_commit": False,
            "review_route_should_prepare_targeted_fix": False,
            "review_route_should_prepare_reject": False,
        }
    return default_state

def _build_local_end_to_end_controller_component_matrix_state(
    *,
    execution_repo_path: str,
) -> dict[str, Any]:
    _ = execution_repo_path
    normalized_repo_path = _APPROVE_COMMIT_TAG_EXECUTION_REPO_PATH
    expected_branch = _LOCAL_END_TO_END_CONTROLLER_EXPECTED_BRANCH
    expected_head_tag = _LOCAL_END_TO_END_CONTROLLER_EXPECTED_HEAD_TAG
    one_cycle_controller_dir = Path("/tmp/codex-local-runner-decision/one_cycle_controller")
    targeted_fix_post_reentry_prompt_emission_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_prompt_emission.json"
    )
    targeted_fix_post_reentry_prompt_emission_receipt_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_prompt_emission_receipt.json"
    )
    targeted_fix_post_reentry_codex_reentry_execution_receipt_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_codex_reentry_execution_receipt.json"
    )
    targeted_fix_post_reentry_diff_capture_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_diff_capture.json"
    )
    targeted_fix_post_reentry_review_handoff_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_review_handoff.json"
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
    targeted_fix_post_reentry_bounded_cycle_state_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_bounded_cycle_state.json"
    )
    targeted_fix_post_reentry_bounded_cycle_decision_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_bounded_cycle_decision.json"
    )
    targeted_fix_post_reentry_bounded_cycle_receipt_path = (
        one_cycle_controller_dir / "targeted_fix_post_reentry_bounded_cycle_receipt.json"
    )
    approve_commit_tag_artifact_reconciliation_receipt_path = (
        one_cycle_controller_dir / "approve_commit_tag_artifact_reconciliation_receipt.json"
    )
    approve_commit_tag_boundary_path = one_cycle_controller_dir / "approve_commit_tag_boundary.json"
    approve_commit_tag_plan_path = one_cycle_controller_dir / "approve_commit_tag_plan.json"
    remote_readiness_boundary_path = one_cycle_controller_dir / "remote_readiness_boundary.json"
    remote_readiness_plan_path = one_cycle_controller_dir / "remote_readiness_plan.json"
    approve_commit_tag_command_path = one_cycle_controller_dir / "approve_commit_tag_commands.sh"

    status_short_cmd = subprocess.run(
        ["git", "status", "--short", "--untracked-files=no"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    current_branch_cmd = subprocess.run(
        ["git", "branch", "--show-current"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    head_short_cmd = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    head_tags_cmd = subprocess.run(
        ["git", "tag", "--points-at", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    expected_head_tag_exists_cmd = subprocess.run(
        ["git", "tag", "--list", expected_head_tag],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    expected_head_tag_exists = False
    expected_head_tag_ancestor_of_head = False
    expected_tag_ancestor_cmd: subprocess.CompletedProcess[str] | None = None
    if expected_head_tag_exists_cmd.returncode == 0:
        expected_head_tag_exists = expected_head_tag in {
            line.strip()
            for line in (expected_head_tag_exists_cmd.stdout or "").splitlines()
            if line.strip()
        }
        if expected_head_tag_exists:
            expected_tag_ancestor_cmd = subprocess.run(
                ["git", "merge-base", "--is-ancestor", expected_head_tag, "HEAD"],
                text=True,
                capture_output=True,
                check=False,
                cwd=normalized_repo_path,
                shell=False,
            )
            expected_head_tag_ancestor_of_head = expected_tag_ancestor_cmd.returncode == 0

    metadata_collection_ok = (
        status_short_cmd.returncode == 0
        and current_branch_cmd.returncode == 0
        and head_short_cmd.returncode == 0
        and head_tags_cmd.returncode == 0
        and expected_head_tag_exists_cmd.returncode == 0
        and (
            expected_tag_ancestor_cmd is None
            or expected_tag_ancestor_cmd.returncode in {0, 1}
        )
    )
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
    current_branch = (
        _normalize_text(current_branch_cmd.stdout, default="") if metadata_collection_ok else ""
    )
    head_short = _normalize_text(head_short_cmd.stdout, default="") if metadata_collection_ok else ""
    head_tags = (
        sorted(
            {
                line.strip()
                for line in (head_tags_cmd.stdout or "").splitlines()
                if line.strip()
            }
        )
        if metadata_collection_ok
        else []
    )
    expected_head_tag_present = bool(
        expected_head_tag_exists and expected_head_tag_ancestor_of_head
    )

    approve_reconciliation_receipt = _read_json_object_if_exists(
        approve_commit_tag_artifact_reconciliation_receipt_path
    ) or {}
    approve_reconciliation_completed = (
        _normalize_text(approve_reconciliation_receipt.get("status"), default="") == "completed"
        and _normalize_text(
            approve_reconciliation_receipt.get("reconciliation_status"), default=""
        )
        == "completed"
        and _normalize_text(approve_reconciliation_receipt.get("blocked_reason"), default="")
        == "none"
        and bool(approve_reconciliation_receipt.get("already_committed", False))
        and bool(approve_reconciliation_receipt.get("already_tagged", False))
    )
    command_file_has_noop_text = False
    command_file_has_dangerous_commands = False
    if approve_commit_tag_command_path.exists():
        try:
            command_file_text = approve_commit_tag_command_path.read_text(encoding="utf-8")
            command_file_has_noop_text = (
                "No approve commit/tag execution is required." in command_file_text
            )
            command_file_has_dangerous_commands = (
                ("git commit" in command_file_text) or ("git tag" in command_file_text)
            )
        except OSError:
            command_file_has_noop_text = False
            command_file_has_dangerous_commands = True
    approve_command_safe = command_file_has_noop_text and (not command_file_has_dangerous_commands)

    component_entries: list[dict[str, Any]] = []

    def _append_component(
        *,
        component: str,
        status: str,
        required_for_local_end_to_end: bool,
        artifact_paths: list[Path],
        reason: str,
        next_action: str,
    ) -> None:
        present_artifacts = [str(path) for path in artifact_paths if path.exists()]
        missing_artifacts = [str(path) for path in artifact_paths if not path.exists()]
        component_entries.append(
            {
                "component": component,
                "status": status,
                "required_for_local_end_to_end": required_for_local_end_to_end,
                "artifact_paths": [str(path) for path in artifact_paths],
                "present_artifacts": present_artifacts,
                "missing_artifacts": missing_artifacts,
                "reason": reason,
                "next_action": next_action,
            }
        )

    prompt_generation_artifact_paths = [
        targeted_fix_post_reentry_prompt_emission_path,
        targeted_fix_post_reentry_prompt_emission_receipt_path,
        targeted_fix_post_reentry_next_step_handoff_path,
    ]
    prompt_generation_present_count = sum(1 for path in prompt_generation_artifact_paths if path.exists())
    implementation_prompt_generation_status = (
        "mostly_ready" if prompt_generation_present_count > 0 else "missing"
    )
    implementation_prompt_generation_reason = (
        "Prompt generation is substantially implemented, but not fully complete because a single "
        "integrated runner does not yet choose, generate, execute, review, and continue without human intervention."
    )
    _append_component(
        component="implementation_prompt_generation",
        status=implementation_prompt_generation_status,
        required_for_local_end_to_end=True,
        artifact_paths=prompt_generation_artifact_paths,
        reason=implementation_prompt_generation_reason,
        next_action=(
            "prepare_local_end_to_end_dry_run_plan"
            if implementation_prompt_generation_status == "mostly_ready"
            else "restore_prompt_generation_artifacts"
        ),
    )

    codex_execution_gate_artifact_paths = [
        targeted_fix_post_reentry_codex_reentry_execution_receipt_path
    ]
    codex_execution_gate_ready = all(path.exists() for path in codex_execution_gate_artifact_paths)
    _append_component(
        component="codex_execution_gate",
        status="ready" if codex_execution_gate_ready else "missing",
        required_for_local_end_to_end=True,
        artifact_paths=codex_execution_gate_artifact_paths,
        reason=(
            "Codex reentry execution receipts confirm bounded gate surfaces are present."
            if codex_execution_gate_ready
            else "Codex reentry execution receipt is missing."
        ),
        next_action=(
            "confirm_prompt323_metadata_only_no_codex_invocation"
            if codex_execution_gate_ready
            else "restore_codex_execution_gate_artifact"
        ),
    )

    diff_capture_artifact_paths = [targeted_fix_post_reentry_diff_capture_path]
    diff_capture_ready = all(path.exists() for path in diff_capture_artifact_paths)
    _append_component(
        component="diff_capture",
        status="ready" if diff_capture_ready else "missing",
        required_for_local_end_to_end=True,
        artifact_paths=diff_capture_artifact_paths,
        reason=(
            "Post-reentry diff capture artifact is present."
            if diff_capture_ready
            else "Post-reentry diff capture artifact is missing."
        ),
        next_action=(
            "retain_metadata_only_readiness_flow"
            if diff_capture_ready
            else "restore_post_reentry_diff_capture_artifact"
        ),
    )

    review_handoff_artifact_paths = [targeted_fix_post_reentry_review_handoff_path]
    review_handoff_ready = all(path.exists() for path in review_handoff_artifact_paths)
    _append_component(
        component="review_handoff",
        status="ready" if review_handoff_ready else "missing",
        required_for_local_end_to_end=True,
        artifact_paths=review_handoff_artifact_paths,
        reason=(
            "Review handoff artifact is present."
            if review_handoff_ready
            else "Review handoff artifact is missing."
        ),
        next_action=(
            "retain_review_handoff_metadata_path"
            if review_handoff_ready
            else "restore_review_handoff_artifact"
        ),
    )

    review_assimilation_artifact_paths = [targeted_fix_post_reentry_review_assimilation_path]
    review_assimilation_ready = all(path.exists() for path in review_assimilation_artifact_paths)
    _append_component(
        component="review_assimilation",
        status="ready" if review_assimilation_ready else "missing",
        required_for_local_end_to_end=True,
        artifact_paths=review_assimilation_artifact_paths,
        reason=(
            "Review assimilation artifact is present."
            if review_assimilation_ready
            else "Review assimilation artifact is missing."
        ),
        next_action=(
            "retain_review_assimilation_metadata_path"
            if review_assimilation_ready
            else "restore_review_assimilation_artifact"
        ),
    )

    route_decision_artifact_paths = [
        targeted_fix_post_reentry_route_decision_path,
        targeted_fix_post_reentry_route_executor_boundary_path,
    ]
    route_decision_present_count = sum(1 for path in route_decision_artifact_paths if path.exists())
    if route_decision_present_count == len(route_decision_artifact_paths):
        route_decision_status = "ready"
    elif route_decision_present_count > 0:
        route_decision_status = "mostly_ready"
    else:
        route_decision_status = "missing"
    _append_component(
        component="route_decision",
        status=route_decision_status,
        required_for_local_end_to_end=True,
        artifact_paths=route_decision_artifact_paths,
        reason=(
            "Route decision and executor boundary artifacts are present."
            if route_decision_status == "ready"
            else (
                "Route decision artifacts are partially present."
                if route_decision_status == "mostly_ready"
                else "Route decision artifacts are missing."
            )
        ),
        next_action=(
            "retain_route_decision_metadata_path"
            if route_decision_status in {"ready", "mostly_ready"}
            else "restore_route_decision_artifacts"
        ),
    )

    targeted_fix_loop_artifact_paths = [
        targeted_fix_post_reentry_prompt_emission_path,
        targeted_fix_post_reentry_prompt_emission_receipt_path,
        targeted_fix_post_reentry_codex_reentry_execution_receipt_path,
        targeted_fix_post_reentry_diff_capture_path,
        targeted_fix_post_reentry_route_decision_path,
    ]
    targeted_fix_loop_core_ready = (
        targeted_fix_post_reentry_prompt_emission_path.exists()
        and targeted_fix_post_reentry_prompt_emission_receipt_path.exists()
        and targeted_fix_post_reentry_codex_reentry_execution_receipt_path.exists()
    )
    targeted_fix_loop_present_count = sum(1 for path in targeted_fix_loop_artifact_paths if path.exists())
    if targeted_fix_loop_core_ready:
        targeted_fix_loop_status = "ready"
    elif targeted_fix_loop_present_count > 0:
        targeted_fix_loop_status = "mostly_ready"
    else:
        targeted_fix_loop_status = "missing"
    _append_component(
        component="targeted_fix_loop",
        status=targeted_fix_loop_status,
        required_for_local_end_to_end=True,
        artifact_paths=targeted_fix_loop_artifact_paths,
        reason=(
            "Targeted-fix loop artifacts for emission, reentry gate, and reroute are present."
            if targeted_fix_loop_status == "ready"
            else (
                "Targeted-fix loop artifacts are partially present."
                if targeted_fix_loop_status == "mostly_ready"
                else "Targeted-fix loop artifacts are missing."
            )
        ),
        next_action=(
            "retain_targeted_fix_loop_metadata_path"
            if targeted_fix_loop_status in {"ready", "mostly_ready"}
            else "restore_targeted_fix_loop_artifacts"
        ),
    )

    bounded_cycle_artifact_paths = [
        targeted_fix_post_reentry_bounded_cycle_state_path,
        targeted_fix_post_reentry_bounded_cycle_decision_path,
        targeted_fix_post_reentry_bounded_cycle_receipt_path,
    ]
    bounded_cycle_present_count = sum(1 for path in bounded_cycle_artifact_paths if path.exists())
    if bounded_cycle_present_count == len(bounded_cycle_artifact_paths):
        bounded_cycle_status = "ready"
    elif bounded_cycle_present_count > 0:
        bounded_cycle_status = "mostly_ready"
    else:
        bounded_cycle_status = "missing"
    _append_component(
        component="bounded_cycle_control",
        status=bounded_cycle_status,
        required_for_local_end_to_end=True,
        artifact_paths=bounded_cycle_artifact_paths,
        reason=(
            "Bounded cycle state, decision, and receipt artifacts are present."
            if bounded_cycle_status == "ready"
            else (
                "Bounded cycle artifacts are partially present."
                if bounded_cycle_status == "mostly_ready"
                else "Bounded cycle artifacts are missing."
            )
        ),
        next_action=(
            "retain_bounded_cycle_control_metadata_path"
            if bounded_cycle_status in {"ready", "mostly_ready"}
            else "restore_bounded_cycle_control_artifacts"
        ),
    )

    local_commit_tag_control_artifact_paths = [
        approve_commit_tag_artifact_reconciliation_receipt_path,
        approve_commit_tag_boundary_path,
        approve_commit_tag_plan_path,
    ]
    local_commit_tag_control_ready = (
        approve_reconciliation_completed
        and approve_commit_tag_boundary_path.exists()
        and approve_commit_tag_plan_path.exists()
        and approve_command_safe
    )
    if local_commit_tag_control_ready:
        local_commit_tag_control_status = "ready"
    elif any(path.exists() for path in local_commit_tag_control_artifact_paths):
        local_commit_tag_control_status = "mostly_ready"
    else:
        local_commit_tag_control_status = "missing"
    _append_component(
        component="local_commit_tag_control",
        status=local_commit_tag_control_status,
        required_for_local_end_to_end=True,
        artifact_paths=local_commit_tag_control_artifact_paths,
        reason=(
            "Approve commit/tag reconciliation is completed and stale executable commands are removed."
            if local_commit_tag_control_status == "ready"
            else (
                "Approve commit/tag control artifacts are present but reconciliation is not fully confirmed."
                if local_commit_tag_control_status == "mostly_ready"
                else "Approve commit/tag control artifacts are missing."
            )
        ),
        next_action=(
            "retain_local_commit_tag_control_metadata_path"
            if local_commit_tag_control_status == "ready"
            else "complete_approve_commit_tag_reconciliation"
        ),
    )

    remote_operations_artifact_paths = [remote_readiness_boundary_path, remote_readiness_plan_path]
    _append_component(
        component="remote_operations",
        status="deferred",
        required_for_local_end_to_end=False,
        artifact_paths=remote_operations_artifact_paths,
        reason="Remote push/PR/merge remains intentionally deferred for local-only readiness.",
        next_action="defer_remote_operations",
    )

    _append_component(
        component="integrated_local_runner",
        status="not_ready",
        required_for_local_end_to_end=False,
        artifact_paths=[],
        reason=(
            "A single integrated local runner does not yet choose the next prompt, execute Codex, "
            "review results, route decisions, and continue without human intervention."
        ),
        next_action="prepare_local_end_to_end_dry_run_plan",
    )

    ready_components = sorted(
        [entry["component"] for entry in component_entries if entry.get("status") == "ready"]
    )
    mostly_ready_components = sorted(
        [entry["component"] for entry in component_entries if entry.get("status") == "mostly_ready"]
    )
    partial_components = sorted(
        [entry["component"] for entry in component_entries if entry.get("status") == "partial"]
    )
    missing_components = sorted(
        [entry["component"] for entry in component_entries if entry.get("status") == "missing"]
    )
    deferred_components = sorted(
        [entry["component"] for entry in component_entries if entry.get("status") == "deferred"]
    )
    required_component_entries = [
        entry
        for entry in component_entries
        if bool(entry.get("required_for_local_end_to_end", False))
    ]
    local_components_ready = bool(required_component_entries) and all(
        _normalize_text(entry.get("status"), default="missing") in {"ready", "mostly_ready"}
        for entry in required_component_entries
    )
    integrated_runner_ready = any(
        entry.get("component") == "integrated_local_runner"
        and _normalize_text(entry.get("status"), default="not_ready") == "ready"
        for entry in component_entries
    )

    status = "ready" if (metadata_collection_ok and local_components_ready) else "blocked"
    summary = (
        "Local-only controller components are sufficiently ready for dry-run planning; integrated runner remains the next local gap."
        if status == "ready"
        else (
            "Local-only controller component readiness is blocked by missing metadata."
            if not metadata_collection_ok
            else "Local-only controller component readiness is blocked by missing required components."
        )
    )

    return {
        "status": status,
        "source": "local_end_to_end_controller_component_matrix",
        "current_branch": current_branch,
        "head_short": head_short,
        "head_tags": head_tags,
        "expected_head_tag": expected_head_tag,
        "expected_head_tag_exists": expected_head_tag_exists,
        "expected_head_tag_ancestor_of_head": expected_head_tag_ancestor_of_head,
        "expected_head_tag_present": expected_head_tag_present,
        "worktree_clean": worktree_clean,
        "changed_tracked_files": changed_tracked_files,
        "expected_branch": expected_branch,
        "components": component_entries,
        "ready_components": ready_components,
        "mostly_ready_components": mostly_ready_components,
        "partial_components": partial_components,
        "missing_components": missing_components,
        "deferred_components": deferred_components,
        "local_components_ready": local_components_ready,
        "integrated_runner_ready": integrated_runner_ready,
        "remote_required": False,
        "github_deferred": True,
        "summary": summary,
    }

def _build_local_end_to_end_controller_readiness_boundary_state(
    *,
    component_matrix_state: Mapping[str, Any] | None,
    reconciliation_receipt_path: Path,
    remote_readiness_boundary_path: Path,
) -> dict[str, Any]:
    component_matrix = (
        dict(component_matrix_state) if isinstance(component_matrix_state, Mapping) else {}
    )
    components_raw = component_matrix.get("components")
    components: list[dict[str, Any]] = []
    if isinstance(components_raw, list):
        for item in components_raw:
            if isinstance(item, Mapping):
                components.append(dict(item))
    implementation_prompt_generation_status = "mostly_ready"
    implementation_prompt_generation_reason = (
        "Prompt generation is substantially implemented, but not fully complete because a single integrated runner does not yet choose, generate, execute, review, and continue without human intervention."
    )
    for entry in components:
        if _normalize_text(entry.get("component"), default="") != "implementation_prompt_generation":
            continue
        implementation_prompt_generation_status = _normalize_text(
            entry.get("status"),
            default=implementation_prompt_generation_status,
        )
        implementation_prompt_generation_reason = _normalize_text(
            entry.get("reason"),
            default=implementation_prompt_generation_reason,
        )
        break

    remote_readiness_artifact = _read_json_object_if_exists(remote_readiness_boundary_path) or {}
    remote_readiness_artifact_status = _normalize_text(
        remote_readiness_artifact.get("boundary_status"),
        default=_normalize_text(remote_readiness_artifact.get("status"), default="missing"),
    )

    reconciliation_receipt = _read_json_object_if_exists(reconciliation_receipt_path) or {}
    reconciliation_completed = (
        _normalize_text(reconciliation_receipt.get("status"), default="") == "completed"
        and _normalize_text(reconciliation_receipt.get("reconciliation_status"), default="")
        == "completed"
        and _normalize_text(reconciliation_receipt.get("blocked_reason"), default="")
        == "none"
        and bool(reconciliation_receipt.get("already_committed", False))
        and bool(reconciliation_receipt.get("already_tagged", False))
    )

    current_branch = _normalize_text(component_matrix.get("current_branch"), default="")
    head_short = _normalize_text(component_matrix.get("head_short"), default="")
    head_tags = _normalize_string_list(component_matrix.get("head_tags"))
    expected_branch = _LOCAL_END_TO_END_CONTROLLER_EXPECTED_BRANCH
    expected_head_tag = _LOCAL_END_TO_END_CONTROLLER_EXPECTED_HEAD_TAG
    expected_head_tag_exists = bool(component_matrix.get("expected_head_tag_exists", False))
    expected_head_tag_ancestor_of_head = bool(
        component_matrix.get("expected_head_tag_ancestor_of_head", False)
    )
    expected_head_tag_present = bool(component_matrix.get("expected_head_tag_present", False))
    changed_tracked_files = _normalize_string_list(component_matrix.get("changed_tracked_files"))
    worktree_clean = bool(component_matrix.get("worktree_clean", False))
    local_components_ready = bool(component_matrix.get("local_components_ready", False))
    integrated_runner_ready = bool(component_matrix.get("integrated_runner_ready", False))
    missing_components = _normalize_string_list(component_matrix.get("missing_components"))

    status = "blocked"
    boundary_status = "blocked"
    blocked_reason = "none"
    next_action = "manual_review_required"
    local_end_to_end_ready = False

    if not worktree_clean:
        blocked_reason = "tracked_changes_present_before_local_end_to_end_readiness"
        next_action = "commit_or_reconcile_tracked_changes_before_local_readiness"
    elif not expected_head_tag_exists:
        blocked_reason = "expected_prompt322_tag_missing"
        next_action = "commit_and_tag_prompt322_before_local_readiness"
    elif not expected_head_tag_ancestor_of_head:
        blocked_reason = "expected_prompt322_tag_not_ancestor_of_head"
        next_action = "checkout_or_merge_history_where_prompt322_tag_is_ancestor_of_head"
    elif not reconciliation_completed:
        blocked_reason = "approve_commit_tag_reconciliation_not_completed"
        next_action = "complete_approve_commit_tag_reconciliation"
    elif not local_components_ready:
        blocked_reason = "local_controller_required_components_missing"
        next_action = "implement_missing_local_controller_components"
    else:
        status = "ready"
        boundary_status = "ready"
        blocked_reason = "none"
        next_action = "prepare_local_end_to_end_dry_run_plan"
        local_end_to_end_ready = True

    readiness_state = {
        "status": status,
        "boundary_status": boundary_status,
        "blocked_reason": blocked_reason,
        "source": "local_end_to_end_controller_readiness_boundary",
        "current_branch": current_branch,
        "expected_branch": expected_branch,
        "head_short": head_short,
        "head_tags": head_tags,
        "expected_head_tag": expected_head_tag,
        "expected_head_tag_exists": expected_head_tag_exists,
        "expected_head_tag_ancestor_of_head": expected_head_tag_ancestor_of_head,
        "expected_head_tag_present": expected_head_tag_present,
        "worktree_clean": worktree_clean,
        "changed_tracked_files": changed_tracked_files,
        "local_end_to_end_ready": local_end_to_end_ready,
        "local_components_ready": local_components_ready,
        "integrated_runner_ready": integrated_runner_ready,
        "implementation_prompt_generation_status": implementation_prompt_generation_status,
        "implementation_prompt_generation_reason": implementation_prompt_generation_reason,
        "remote_required": False,
        "github_deferred": True,
        "remote_readiness_artifact_status": remote_readiness_artifact_status,
        "execution_allowed": False,
        "execution_performed": False,
        "codex_invoked": False,
        "commit_performed": False,
        "tag_performed": False,
        "push_performed": False,
        "pr_created": False,
        "merge_performed": False,
        "next_action": next_action,
        "summary": (
            "Local-only end-to-end controller readiness is ready for dry-run planning; integrated runner implementation remains the next local gap."
            if local_end_to_end_ready
            else (
                "Local-only end-to-end controller readiness is blocked by tracked changes in the worktree."
                if blocked_reason == "tracked_changes_present_before_local_end_to_end_readiness"
                else (
                    "Local-only end-to-end controller readiness is blocked because expected Prompt322 tag is missing."
                    if blocked_reason == "expected_prompt322_tag_missing"
                    else (
                        "Local-only end-to-end controller readiness is blocked because expected Prompt322 tag is not an ancestor of HEAD."
                        if blocked_reason == "expected_prompt322_tag_not_ancestor_of_head"
                        else (
                            "Local-only end-to-end controller readiness is blocked because approve commit/tag reconciliation is not completed."
                            if blocked_reason == "approve_commit_tag_reconciliation_not_completed"
                            else "Local-only end-to-end controller readiness is blocked because required local controller components are missing."
                        )
                    )
                )
            )
        ),
    }
    if blocked_reason == "local_controller_required_components_missing":
        readiness_state["missing_components"] = missing_components
    return readiness_state

def _build_local_end_to_end_controller_gap_report_state(
    *,
    component_matrix_state: Mapping[str, Any] | None,
    readiness_boundary_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    component_matrix = (
        dict(component_matrix_state) if isinstance(component_matrix_state, Mapping) else {}
    )
    readiness_boundary = (
        dict(readiness_boundary_state) if isinstance(readiness_boundary_state, Mapping) else {}
    )
    readiness_status = _normalize_text(readiness_boundary.get("boundary_status"), default="blocked")
    next_action = "prepare_local_end_to_end_dry_run_plan"
    return {
        "status": "ready" if readiness_status == "ready" else "blocked",
        "source": "local_end_to_end_controller_gap_report",
        "primary_gap": "integrated_local_runner_missing",
        "secondary_gaps": [
            "next_prompt_selection_not_fully_automated",
            "prompt_generation_not_fully_auto_adopted",
            "end_to_end_execution_sequence_not_yet_unified",
        ],
        "completed_capabilities": [
            "codex_execution_gate",
            "diff_capture",
            "review_handoff",
            "review_assimilation",
            "route_decision",
            "targeted_fix_loop",
            "bounded_cycle_control",
            "local_commit_tag_control",
            "approve_artifact_reconciliation",
            "remote_readiness_boundary_metadata_only",
        ],
        "deferred_capabilities": [
            "remote_push",
            "pr_create",
            "pr_merge",
            "remote_rollback",
        ],
        "next_prompt_id_recommendation": "Prompt324-local",
        "next_prompt_title_recommendation": "local-only end-to-end dry-run plan builder",
        "next_action": next_action,
        "summary": (
            "Integrated local runner remains the primary local-only gap; existing controller components are ready for dry-run planning."
            if readiness_status == "ready"
            else "Integrated local runner remains the primary local-only gap; readiness boundary is blocked pending prerequisite conditions."
        ),
        "local_components_ready": bool(component_matrix.get("local_components_ready", False)),
        "integrated_runner_ready": bool(component_matrix.get("integrated_runner_ready", False)),
    }

def _build_local_end_to_end_dry_run_step_matrix_state(
    *,
    plan_state: Mapping[str, Any] | None,
    one_cycle_controller_dir: Path,
) -> dict[str, Any]:
    plan = dict(plan_state) if isinstance(plan_state, Mapping) else {}
    status = _normalize_text(plan.get("status"), default="blocked")
    blocked_reason = _normalize_text(
        plan.get("blocked_reason"),
        default="local_end_to_end_readiness_not_available",
    )
    plan_ready = bool(plan.get("dry_run_plan_ready", False))
    next_action = _normalize_text(plan.get("next_action"), default="manual_review_required")
    step_sequence = [
        "read_current_state",
        "choose_next_local_action",
        "prepare_or_select_codex_prompt",
        "codex_execution_gate",
        "post_execution_diff_capture",
        "review_handoff",
        "review_response_assimilation",
        "route_decision",
        "targeted_fix_prompt_emission_if_needed",
        "targeted_fix_codex_reentry_if_needed",
        "post_reentry_diff_capture_if_needed",
        "bounded_cycle_decision",
        "approve_commit_tag_boundary_if_approved",
        "approve_artifact_reconciliation_if_needed",
        "terminal_summary",
        "next_cycle_decision",
    ]
    artifact_paths: dict[str, Path] = {
        "local_end_to_end_controller_readiness_boundary": (
            one_cycle_controller_dir / "local_end_to_end_controller_readiness_boundary.json"
        ),
        "local_end_to_end_controller_component_matrix": (
            one_cycle_controller_dir / "local_end_to_end_controller_component_matrix.json"
        ),
        "local_end_to_end_controller_gap_report": (
            one_cycle_controller_dir / "local_end_to_end_controller_gap_report.json"
        ),
        "targeted_fix_post_reentry_prompt_emission": (
            one_cycle_controller_dir / "targeted_fix_post_reentry_prompt_emission.json"
        ),
        "targeted_fix_post_reentry_codex_reentry_execution_receipt": (
            one_cycle_controller_dir / "targeted_fix_post_reentry_codex_reentry_execution_receipt.json"
        ),
        "targeted_fix_post_reentry_diff_capture": (
            one_cycle_controller_dir / "targeted_fix_post_reentry_diff_capture.json"
        ),
        "targeted_fix_post_reentry_review_handoff": (
            one_cycle_controller_dir / "targeted_fix_post_reentry_review_handoff.json"
        ),
        "targeted_fix_post_reentry_review_assimilation": (
            one_cycle_controller_dir / "targeted_fix_post_reentry_review_assimilation.json"
        ),
        "targeted_fix_post_reentry_route_decision": (
            one_cycle_controller_dir / "targeted_fix_post_reentry_route_decision.json"
        ),
        "targeted_fix_post_reentry_route_executor_boundary": (
            one_cycle_controller_dir / "targeted_fix_post_reentry_route_executor_boundary.json"
        ),
        "targeted_fix_post_reentry_bounded_cycle_state": (
            one_cycle_controller_dir / "targeted_fix_post_reentry_bounded_cycle_state.json"
        ),
        "targeted_fix_post_reentry_bounded_cycle_decision": (
            one_cycle_controller_dir / "targeted_fix_post_reentry_bounded_cycle_decision.json"
        ),
        "targeted_fix_post_reentry_bounded_cycle_receipt": (
            one_cycle_controller_dir / "targeted_fix_post_reentry_bounded_cycle_receipt.json"
        ),
        "approve_commit_tag_boundary": one_cycle_controller_dir / "approve_commit_tag_boundary.json",
        "approve_commit_tag_artifact_reconciliation_receipt": (
            one_cycle_controller_dir / "approve_commit_tag_artifact_reconciliation_receipt.json"
        ),
        "remote_readiness_boundary": one_cycle_controller_dir / "remote_readiness_boundary.json",
        "local_end_to_end_dry_run_plan": (
            one_cycle_controller_dir / "local_end_to_end_dry_run_plan.json"
        ),
        "local_end_to_end_dry_run_step_matrix": (
            one_cycle_controller_dir / "local_end_to_end_dry_run_step_matrix.json"
        ),
        "local_end_to_end_dry_run_receipt": (
            one_cycle_controller_dir / "local_end_to_end_dry_run_receipt.json"
        ),
    }

    def _artifact_str_list(keys: list[str]) -> list[str]:
        return [str(artifact_paths[key]) for key in keys if key in artifact_paths]

    def _inputs_available(keys: list[str]) -> bool:
        return all(artifact_paths[key].exists() for key in keys if key in artifact_paths)

    step_definitions: list[dict[str, Any]] = [
        {
            "step_name": "read_current_state",
            "input_keys": [
                "local_end_to_end_controller_component_matrix",
                "local_end_to_end_controller_readiness_boundary",
                "local_end_to_end_controller_gap_report",
                "remote_readiness_boundary",
            ],
            "output_keys": [],
            "summary": "Read current local readiness and boundary artifacts.",
        },
        {
            "step_name": "choose_next_local_action",
            "input_keys": [
                "local_end_to_end_controller_component_matrix",
                "local_end_to_end_controller_readiness_boundary",
            ],
            "output_keys": ["targeted_fix_post_reentry_route_decision"],
            "summary": "Choose the next local action based on bounded route metadata.",
        },
        {
            "step_name": "prepare_or_select_codex_prompt",
            "input_keys": [
                "targeted_fix_post_reentry_route_decision",
                "targeted_fix_post_reentry_prompt_emission",
            ],
            "output_keys": ["targeted_fix_post_reentry_prompt_emission"],
            "summary": "Prepare or select the next Codex prompt artifact when routing requires it.",
        },
        {
            "step_name": "codex_execution_gate",
            "input_keys": ["targeted_fix_post_reentry_codex_reentry_execution_receipt"],
            "output_keys": ["targeted_fix_post_reentry_codex_reentry_execution_receipt"],
            "summary": "Gate Codex execution through metadata-only readiness checks.",
        },
        {
            "step_name": "post_execution_diff_capture",
            "input_keys": ["targeted_fix_post_reentry_diff_capture"],
            "output_keys": ["targeted_fix_post_reentry_diff_capture"],
            "summary": "Capture post-execution diff metadata for review handoff.",
        },
        {
            "step_name": "review_handoff",
            "input_keys": ["targeted_fix_post_reentry_review_handoff"],
            "output_keys": ["targeted_fix_post_reentry_review_handoff"],
            "summary": "Emit review handoff metadata for external review response.",
        },
        {
            "step_name": "review_response_assimilation",
            "input_keys": ["targeted_fix_post_reentry_review_assimilation"],
            "output_keys": ["targeted_fix_post_reentry_review_assimilation"],
            "summary": "Assimilate review response into deterministic local metadata.",
        },
        {
            "step_name": "route_decision",
            "input_keys": [
                "targeted_fix_post_reentry_route_decision",
                "targeted_fix_post_reentry_route_executor_boundary",
            ],
            "output_keys": [
                "targeted_fix_post_reentry_route_decision",
                "targeted_fix_post_reentry_route_executor_boundary",
            ],
            "summary": "Produce a route decision for approve, reject, or targeted-fix continuation.",
        },
        {
            "step_name": "targeted_fix_prompt_emission_if_needed",
            "input_keys": ["targeted_fix_post_reentry_prompt_emission"],
            "output_keys": ["targeted_fix_post_reentry_prompt_emission"],
            "summary": "Emit targeted-fix prompt metadata when route decision requires it.",
        },
        {
            "step_name": "targeted_fix_codex_reentry_if_needed",
            "input_keys": ["targeted_fix_post_reentry_codex_reentry_execution_receipt"],
            "output_keys": ["targeted_fix_post_reentry_codex_reentry_execution_receipt"],
            "summary": "Perform targeted-fix Codex reentry only if route policy allows.",
        },
        {
            "step_name": "post_reentry_diff_capture_if_needed",
            "input_keys": ["targeted_fix_post_reentry_diff_capture"],
            "output_keys": ["targeted_fix_post_reentry_diff_capture"],
            "summary": "Capture post-reentry diff metadata when targeted-fix reentry runs.",
        },
        {
            "step_name": "bounded_cycle_decision",
            "input_keys": [
                "targeted_fix_post_reentry_bounded_cycle_state",
                "targeted_fix_post_reentry_bounded_cycle_decision",
                "targeted_fix_post_reentry_bounded_cycle_receipt",
            ],
            "output_keys": [
                "targeted_fix_post_reentry_bounded_cycle_decision",
                "targeted_fix_post_reentry_bounded_cycle_receipt",
            ],
            "summary": "Enforce bounded cycle continuation rules for local deterministic looping.",
        },
        {
            "step_name": "approve_commit_tag_boundary_if_approved",
            "input_keys": ["approve_commit_tag_boundary"],
            "output_keys": ["approve_commit_tag_boundary"],
            "summary": "Apply local approve/commit/tag boundary only after explicit approval route.",
        },
        {
            "step_name": "approve_artifact_reconciliation_if_needed",
            "input_keys": ["approve_commit_tag_artifact_reconciliation_receipt"],
            "output_keys": ["approve_commit_tag_artifact_reconciliation_receipt"],
            "summary": "Reconcile local approve artifacts to preserve deterministic state continuity.",
        },
        {
            "step_name": "terminal_summary",
            "input_keys": [
                "targeted_fix_post_reentry_route_decision",
                "targeted_fix_post_reentry_bounded_cycle_receipt",
            ],
            "output_keys": ["local_end_to_end_dry_run_plan"],
            "summary": "Compile terminal cycle summary metadata for local-only orchestration.",
        },
        {
            "step_name": "next_cycle_decision",
            "input_keys": [
                "local_end_to_end_dry_run_plan",
                "local_end_to_end_dry_run_step_matrix",
            ],
            "output_keys": ["local_end_to_end_dry_run_receipt"],
            "summary": "Decide whether to continue locally into the next bounded cycle prompt.",
        },
    ]

    steps: list[dict[str, Any]] = []
    for index, step in enumerate(step_definitions, start=1):
        step_name = _normalize_text(step.get("step_name"), default="")
        input_keys = [
            _normalize_text(item, default="")
            for item in step.get("input_keys", [])
            if _normalize_text(item, default="")
        ]
        output_keys = [
            _normalize_text(item, default="")
            for item in step.get("output_keys", [])
            if _normalize_text(item, default="")
        ]
        next_on_success = (
            step_sequence[index] if index < len(step_sequence) else "completed"
        )
        steps.append(
            {
                "step_id": index,
                "step_name": step_name,
                "required": True,
                "execution_kind": "metadata_only",
                "input_artifacts": _artifact_str_list(input_keys),
                "output_artifacts": _artifact_str_list(output_keys),
                "existing_surface_available": _inputs_available(input_keys),
                "execution_allowed_now": False,
                "codex_invocation_allowed_now": False,
                "git_mutation_allowed_now": False,
                "remote_operation_allowed_now": False,
                "next_on_success": next_on_success,
                "next_on_blocked": "terminal_summary",
                "next_on_failed": "terminal_summary",
                "summary": _normalize_text(step.get("summary"), default=""),
            }
        )

    all_steps_metadata_only = all(
        _normalize_text(step.get("execution_kind"), default="") == "metadata_only"
        for step in steps
    )
    return {
        "status": "ready" if plan_ready and status == "ready" else "blocked",
        "source": "local_end_to_end_dry_run_plan_builder",
        "step_count": len(steps),
        "steps": steps,
        "all_steps_metadata_only": all_steps_metadata_only,
        "any_codex_invocation_allowed_now": any(
            bool(step.get("codex_invocation_allowed_now", False)) for step in steps
        ),
        "any_git_mutation_allowed_now": any(
            bool(step.get("git_mutation_allowed_now", False)) for step in steps
        ),
        "any_remote_operation_allowed_now": any(
            bool(step.get("remote_operation_allowed_now", False)) for step in steps
        ),
        "next_action": next_action,
        "summary": (
            "Metadata-only local end-to-end dry-run step matrix is ready; execution remains disabled."
            if plan_ready and status == "ready"
            else (
                "Metadata-only local end-to-end dry-run step matrix is blocked by tracked changes."
                if blocked_reason == "tracked_changes_present_before_dry_run_plan"
                else (
                    "Metadata-only local end-to-end dry-run step matrix is blocked because expected Prompt323 tag is missing."
                    if blocked_reason == "expected_prompt323_tag_missing"
                    else (
                        "Metadata-only local end-to-end dry-run step matrix is blocked because expected Prompt323 tag is not an ancestor of HEAD."
                        if blocked_reason == "expected_prompt323_tag_not_ancestor_of_head"
                        else "Metadata-only local end-to-end dry-run step matrix is blocked because local readiness artifacts are missing or incompatible."
                    )
                )
            )
        ),
    }

def _build_local_end_to_end_dry_run_plan_state(
    *,
    execution_repo_path: str,
    one_cycle_controller_dir: Path,
) -> dict[str, Any]:
    _ = execution_repo_path
    normalized_repo_path = _APPROVE_COMMIT_TAG_EXECUTION_REPO_PATH
    expected_head_tag = _LOCAL_END_TO_END_DRY_RUN_EXPECTED_HEAD_TAG
    component_matrix_path = one_cycle_controller_dir / "local_end_to_end_controller_component_matrix.json"
    readiness_boundary_path = (
        one_cycle_controller_dir / "local_end_to_end_controller_readiness_boundary.json"
    )
    gap_report_path = one_cycle_controller_dir / "local_end_to_end_controller_gap_report.json"
    remote_readiness_boundary_path = one_cycle_controller_dir / "remote_readiness_boundary.json"

    status_short_cmd = subprocess.run(
        ["git", "status", "--short", "--untracked-files=no"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    current_branch_cmd = subprocess.run(
        ["git", "branch", "--show-current"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    head_short_cmd = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    head_tags_cmd = subprocess.run(
        ["git", "tag", "--points-at", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    expected_head_tag_exists_cmd = subprocess.run(
        ["git", "tag", "--list", expected_head_tag],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    expected_head_tag_exists = False
    expected_head_tag_ancestor_of_head = False
    expected_tag_ancestor_cmd: subprocess.CompletedProcess[str] | None = None
    if expected_head_tag_exists_cmd.returncode == 0:
        expected_head_tag_exists = expected_head_tag in {
            line.strip()
            for line in (expected_head_tag_exists_cmd.stdout or "").splitlines()
            if line.strip()
        }
        if expected_head_tag_exists:
            expected_tag_ancestor_cmd = subprocess.run(
                ["git", "merge-base", "--is-ancestor", expected_head_tag, "HEAD"],
                text=True,
                capture_output=True,
                check=False,
                cwd=normalized_repo_path,
                shell=False,
            )
            expected_head_tag_ancestor_of_head = expected_tag_ancestor_cmd.returncode == 0

    metadata_collection_ok = (
        status_short_cmd.returncode == 0
        and current_branch_cmd.returncode == 0
        and head_short_cmd.returncode == 0
        and head_tags_cmd.returncode == 0
        and expected_head_tag_exists_cmd.returncode == 0
        and (
            expected_tag_ancestor_cmd is None
            or expected_tag_ancestor_cmd.returncode in {0, 1}
        )
    )
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
    current_branch = (
        _normalize_text(current_branch_cmd.stdout, default="") if metadata_collection_ok else ""
    )
    head_short = _normalize_text(head_short_cmd.stdout, default="") if metadata_collection_ok else ""
    head_tags = (
        sorted(
            {
                line.strip()
                for line in (head_tags_cmd.stdout or "").splitlines()
                if line.strip()
            }
        )
        if metadata_collection_ok
        else []
    )
    expected_head_tag_present = bool(
        expected_head_tag_exists and expected_head_tag_ancestor_of_head
    )

    component_matrix_state = _read_json_object_if_exists(component_matrix_path) or {}
    readiness_boundary_state = _read_json_object_if_exists(readiness_boundary_path) or {}
    gap_report_state = _read_json_object_if_exists(gap_report_path) or {}
    _ = _read_json_object_if_exists(remote_readiness_boundary_path) or {}
    _ = _read_json_object_if_exists(one_cycle_controller_dir / "targeted_fix_post_reentry_prompt_emission.json")
    _ = _read_json_object_if_exists(
        one_cycle_controller_dir / "targeted_fix_post_reentry_codex_reentry_execution_receipt.json"
    )
    _ = _read_json_object_if_exists(one_cycle_controller_dir / "targeted_fix_post_reentry_diff_capture.json")
    _ = _read_json_object_if_exists(one_cycle_controller_dir / "targeted_fix_post_reentry_review_handoff.json")
    _ = _read_json_object_if_exists(
        one_cycle_controller_dir / "targeted_fix_post_reentry_review_assimilation.json"
    )
    _ = _read_json_object_if_exists(one_cycle_controller_dir / "targeted_fix_post_reentry_route_decision.json")
    _ = _read_json_object_if_exists(
        one_cycle_controller_dir / "targeted_fix_post_reentry_route_executor_boundary.json"
    )
    _ = _read_json_object_if_exists(one_cycle_controller_dir / "targeted_fix_post_reentry_bounded_cycle_state.json")
    _ = _read_json_object_if_exists(
        one_cycle_controller_dir / "targeted_fix_post_reentry_bounded_cycle_decision.json"
    )
    _ = _read_json_object_if_exists(one_cycle_controller_dir / "targeted_fix_post_reentry_bounded_cycle_receipt.json")
    _ = _read_json_object_if_exists(
        one_cycle_controller_dir / "approve_commit_tag_artifact_reconciliation_receipt.json"
    )

    local_components_ready = bool(component_matrix_state.get("local_components_ready", False))
    integrated_runner_ready = bool(component_matrix_state.get("integrated_runner_ready", False))
    github_deferred = bool(
        readiness_boundary_state.get(
            "github_deferred",
            component_matrix_state.get("github_deferred", True),
        )
    )
    remote_required = bool(
        readiness_boundary_state.get(
            "remote_required",
            component_matrix_state.get("remote_required", False),
        )
    )
    implementation_prompt_generation_status = _normalize_text(
        readiness_boundary_state.get("implementation_prompt_generation_status"),
        default="mostly_ready",
    )
    if not implementation_prompt_generation_status:
        implementation_prompt_generation_status = "mostly_ready"
    components_raw = component_matrix_state.get("components")
    if isinstance(components_raw, list):
        for item in components_raw:
            if not isinstance(item, Mapping):
                continue
            if _normalize_text(item.get("component"), default="") == "implementation_prompt_generation":
                implementation_prompt_generation_status = _normalize_text(
                    item.get("status"),
                    default=implementation_prompt_generation_status,
                )
                break

    prompt323_local_artifacts_available = (
        component_matrix_path.exists()
        and readiness_boundary_path.exists()
        and gap_report_path.exists()
    )
    prompt323_local_artifacts_compatible = (
        prompt323_local_artifacts_available
        and local_components_ready
        and (not integrated_runner_ready)
        and github_deferred
        and (not remote_required)
    )

    status = "blocked"
    plan_status = "blocked"
    blocked_reason = "local_end_to_end_readiness_not_available"
    dry_run_plan_ready = False
    next_action = "complete_local_end_to_end_readiness_boundary"
    summary = (
        "Local-only end-to-end dry-run plan is blocked because local readiness artifacts are missing or incompatible."
    )

    if not worktree_clean:
        blocked_reason = "tracked_changes_present_before_dry_run_plan"
        next_action = "commit_or_reconcile_tracked_changes_before_dry_run_plan"
        summary = "Local-only end-to-end dry-run plan is blocked by tracked changes in the worktree."
    elif not expected_head_tag_exists:
        blocked_reason = "expected_prompt323_tag_missing"
        next_action = "commit_and_tag_prompt323_before_dry_run_plan"
        summary = (
            "Local-only end-to-end dry-run plan is blocked because expected Prompt323 tag is missing."
        )
    elif not expected_head_tag_ancestor_of_head:
        blocked_reason = "expected_prompt323_tag_not_ancestor_of_head"
        next_action = "checkout_or_merge_history_where_prompt323_tag_is_ancestor_of_head"
        summary = (
            "Local-only end-to-end dry-run plan is blocked because expected Prompt323 tag is not an ancestor of HEAD."
        )
    elif not prompt323_local_artifacts_compatible:
        blocked_reason = "local_end_to_end_readiness_not_available"
        next_action = "complete_local_end_to_end_readiness_boundary"
        summary = (
            "Local-only end-to-end dry-run plan is blocked because local readiness artifacts are missing or incompatible."
        )
    else:
        status = "ready"
        plan_status = "ready"
        blocked_reason = "none"
        dry_run_plan_ready = True
        next_action = "prepare_local_end_to_end_one_shot_execution_gate"
        summary = (
            "Local-only end-to-end dry-run plan is ready; execution remains disabled until Prompt325."
        )

    return {
        "status": status,
        "plan_status": plan_status,
        "blocked_reason": blocked_reason,
        "source": "local_end_to_end_dry_run_plan_builder",
        "current_branch": current_branch,
        "head_short": head_short,
        "head_tags": head_tags,
        "expected_head_tag": expected_head_tag,
        "expected_head_tag_exists": expected_head_tag_exists,
        "expected_head_tag_ancestor_of_head": expected_head_tag_ancestor_of_head,
        "expected_head_tag_present": expected_head_tag_present,
        "worktree_clean": worktree_clean,
        "changed_tracked_files": changed_tracked_files,
        "dry_run_plan_ready": dry_run_plan_ready,
        "local_only": True,
        "github_deferred": github_deferred,
        "remote_required": remote_required,
        "local_components_ready": local_components_ready,
        "integrated_runner_ready": integrated_runner_ready,
        "implementation_prompt_generation_status": implementation_prompt_generation_status,
        "step_count": 16,
        "first_step": "read_current_state",
        "final_step": "next_cycle_decision",
        "execution_allowed": False,
        "execution_performed": False,
        "codex_invoked": False,
        "commit_performed": False,
        "tag_performed": False,
        "push_performed": False,
        "pr_created": False,
        "merge_performed": False,
        "next_prompt_id_recommendation": "Prompt325-local",
        "next_prompt_title_recommendation": "local-only one-shot execution gate",
        "next_action": next_action,
        "summary": summary,
    }

def _build_local_end_to_end_one_shot_step_selection_state(
    *,
    plan_state: Mapping[str, Any] | None,
    step_matrix_state: Mapping[str, Any] | None,
    prior_receipt_state: Mapping[str, Any] | None,
    plan_path: Path,
    step_matrix_path: Path,
    prior_receipt_path: Path,
) -> dict[str, Any]:
    plan = dict(plan_state) if isinstance(plan_state, Mapping) else {}
    step_matrix = dict(step_matrix_state) if isinstance(step_matrix_state, Mapping) else {}
    prior_receipt = (
        dict(prior_receipt_state) if isinstance(prior_receipt_state, Mapping) else {}
    )
    step_count = _as_non_negative_int(
        step_matrix.get("step_count"),
        default=_as_non_negative_int(plan.get("step_count"), default=16),
    )
    if step_count <= 0:
        step_count = 16

    steps_raw = step_matrix.get("steps")
    step_name_by_id: dict[int, str] = {}
    if isinstance(steps_raw, list):
        for entry in steps_raw:
            if not isinstance(entry, Mapping):
                continue
            step_id = _as_non_negative_int(entry.get("step_id"), default=0)
            step_name = _normalize_text(entry.get("step_name"), default="")
            if step_id > 0 and step_name:
                step_name_by_id[step_id] = step_name

    def _resolve_step_name(step_id: int) -> str:
        if step_id <= 0:
            return "none"
        if step_id in step_name_by_id:
            return step_name_by_id[step_id]
        if step_id == 1:
            return "read_current_state"
        return "unknown_step"

    plan_status = _normalize_text(plan.get("status"), default="blocked")
    plan_ready = bool(plan.get("dry_run_plan_ready", False))
    plan_local_only = bool(plan.get("local_only", False))
    plan_github_deferred = bool(plan.get("github_deferred", False))
    plan_remote_required = bool(plan.get("remote_required", True))
    plan_execution_allowed = bool(plan.get("execution_allowed", True))
    matrix_all_steps_metadata_only = bool(step_matrix.get("all_steps_metadata_only", False))
    matrix_any_codex = bool(step_matrix.get("any_codex_invocation_allowed_now", True))
    matrix_any_git_mutation = bool(step_matrix.get("any_git_mutation_allowed_now", True))
    matrix_any_remote = bool(step_matrix.get("any_remote_operation_allowed_now", True))
    matrix_status = _normalize_text(step_matrix.get("status"), default="blocked")

    plan_compatible = (
        plan_status == "ready"
        and plan_ready
        and step_count == 16
        and plan_local_only
        and plan_github_deferred
        and (not plan_remote_required)
        and (not plan_execution_allowed)
    )
    step_matrix_compatible = (
        matrix_status == "ready"
        and step_count == 16
        and matrix_all_steps_metadata_only
        and (not matrix_any_codex)
        and (not matrix_any_git_mutation)
        and (not matrix_any_remote)
    )
    dry_run_plan_ready = plan_compatible and step_matrix_compatible

    status = "blocked"
    selection_status = "blocked"
    blocked_reason = "local_end_to_end_dry_run_plan_not_ready"
    selected_step_id = 1
    selected_step_name = _resolve_step_name(selected_step_id)
    one_shot_sequence_complete = False
    next_action = "complete_local_end_to_end_dry_run_plan_builder"
    summary = (
        "Local-only one-shot step selection is blocked because Prompt324 dry-run metadata is missing or incompatible."
    )

    if dry_run_plan_ready:
        status = "ready"
        selection_status = "ready"
        blocked_reason = "none"
        next_action = "prepare_local_one_shot_step_execution_adapter"
        summary = (
            "Local-only one-shot step selection is ready; execution remains disabled until an explicit adapter enables the selected step."
        )
        if prior_receipt:
            prior_status = _normalize_text(prior_receipt.get("status"), default="unknown")
            prior_receipt_status = _normalize_text(
                prior_receipt.get("receipt_status"),
                default=prior_status,
            )
            if prior_status == "blocked" or prior_receipt_status == "blocked":
                status = "blocked"
                selection_status = "blocked"
                blocked_reason = _normalize_text(
                    prior_receipt.get("blocked_reason"),
                    default="prior_one_shot_step_blocked",
                )
                selected_step_id = _as_non_negative_int(
                    prior_receipt.get("selected_step_id"),
                    default=1,
                )
                if selected_step_id <= 0:
                    selected_step_id = 1
                selected_step_name = _normalize_text(
                    prior_receipt.get("selected_step_name"),
                    default=_resolve_step_name(selected_step_id),
                )
                next_action = _normalize_text(
                    prior_receipt.get("next_action"),
                    default="resolve_blocked_local_one_shot_step_before_retry",
                )
                summary = (
                    "Local-only one-shot step selection remains blocked at the previously blocked step."
                )
            elif prior_status == "completed" or prior_receipt_status == "completed":
                last_step_id = _as_non_negative_int(
                    prior_receipt.get("last_step_id"),
                    default=_as_non_negative_int(
                        prior_receipt.get("selected_step_id"),
                        default=0,
                    ),
                )
                if last_step_id >= step_count:
                    selected_step_id = 0
                    selected_step_name = "none"
                    one_shot_sequence_complete = True
                    summary = (
                        "Local-only one-shot step sequence is complete; no additional step is selected."
                    )
                else:
                    selected_step_id = last_step_id + 1
                    if selected_step_id <= 0:
                        selected_step_id = 1
                    selected_step_name = _resolve_step_name(selected_step_id)
            else:
                selected_step_id = 1
                selected_step_name = _resolve_step_name(selected_step_id)

    return {
        "status": status,
        "selection_status": selection_status,
        "blocked_reason": blocked_reason,
        "source": "local_end_to_end_one_shot_step_selection",
        "plan_path": str(plan_path),
        "step_matrix_path": str(step_matrix_path),
        "prior_receipt_path": str(prior_receipt_path),
        "step_count": step_count,
        "selected_step_id": selected_step_id,
        "selected_step_name": selected_step_name,
        "one_shot_sequence_complete": one_shot_sequence_complete,
        "execution_allowed_now": False,
        "codex_invocation_allowed_now": False,
        "git_mutation_allowed_now": False,
        "remote_operation_allowed_now": False,
        "next_action": next_action,
        "summary": summary,
    }

def _build_local_end_to_end_one_shot_execution_gate_state(
    *,
    execution_repo_path: str,
    plan_state: Mapping[str, Any] | None,
    step_matrix_state: Mapping[str, Any] | None,
    step_selection_state: Mapping[str, Any] | None,
    expected_head_tag: str,
) -> dict[str, Any]:
    _ = execution_repo_path
    normalized_repo_path = _APPROVE_COMMIT_TAG_EXECUTION_REPO_PATH
    plan = dict(plan_state) if isinstance(plan_state, Mapping) else {}
    step_matrix = dict(step_matrix_state) if isinstance(step_matrix_state, Mapping) else {}
    step_selection = (
        dict(step_selection_state) if isinstance(step_selection_state, Mapping) else {}
    )
    step_count = _as_non_negative_int(
        step_matrix.get("step_count"),
        default=_as_non_negative_int(plan.get("step_count"), default=16),
    )
    if step_count <= 0:
        step_count = 16

    status_short_cmd = subprocess.run(
        ["git", "status", "--short", "--untracked-files=no"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    current_branch_cmd = subprocess.run(
        ["git", "branch", "--show-current"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    head_short_cmd = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    head_tags_cmd = subprocess.run(
        ["git", "tag", "--points-at", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    expected_head_tag_exists_cmd = subprocess.run(
        ["git", "tag", "--list", expected_head_tag],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    expected_head_tag_exists = False
    expected_head_tag_ancestor_of_head = False
    expected_tag_ancestor_cmd: subprocess.CompletedProcess[str] | None = None
    if expected_head_tag_exists_cmd.returncode == 0:
        expected_head_tag_exists = expected_head_tag in {
            line.strip()
            for line in (expected_head_tag_exists_cmd.stdout or "").splitlines()
            if line.strip()
        }
        if expected_head_tag_exists:
            expected_tag_ancestor_cmd = subprocess.run(
                ["git", "merge-base", "--is-ancestor", expected_head_tag, "HEAD"],
                text=True,
                capture_output=True,
                check=False,
                cwd=normalized_repo_path,
                shell=False,
            )
            expected_head_tag_ancestor_of_head = expected_tag_ancestor_cmd.returncode == 0
    metadata_collection_ok = (
        status_short_cmd.returncode == 0
        and current_branch_cmd.returncode == 0
        and head_short_cmd.returncode == 0
        and head_tags_cmd.returncode == 0
        and expected_head_tag_exists_cmd.returncode == 0
        and (
            expected_tag_ancestor_cmd is None
            or expected_tag_ancestor_cmd.returncode in {0, 1}
        )
    )
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
    current_branch = (
        _normalize_text(current_branch_cmd.stdout, default="")
        if metadata_collection_ok
        else ""
    )
    head_short = (
        _normalize_text(head_short_cmd.stdout, default="")
        if metadata_collection_ok
        else ""
    )
    head_tags = (
        sorted(
            {
                line.strip()
                for line in (head_tags_cmd.stdout or "").splitlines()
                if line.strip()
            }
        )
        if metadata_collection_ok
        else []
    )
    expected_head_tag_present = bool(
        expected_head_tag_exists and expected_head_tag_ancestor_of_head
    )

    plan_status = _normalize_text(plan.get("status"), default="blocked")
    plan_ready = bool(plan.get("dry_run_plan_ready", False))
    plan_local_only = bool(plan.get("local_only", False))
    plan_github_deferred = bool(plan.get("github_deferred", False))
    plan_remote_required = bool(plan.get("remote_required", True))
    plan_execution_allowed = bool(plan.get("execution_allowed", True))
    matrix_status = _normalize_text(step_matrix.get("status"), default="blocked")
    matrix_all_steps_metadata_only = bool(step_matrix.get("all_steps_metadata_only", False))
    matrix_any_codex = bool(step_matrix.get("any_codex_invocation_allowed_now", True))
    matrix_any_git_mutation = bool(step_matrix.get("any_git_mutation_allowed_now", True))
    matrix_any_remote = bool(step_matrix.get("any_remote_operation_allowed_now", True))
    dry_run_plan_ready = (
        plan_status == "ready"
        and plan_ready
        and step_count == 16
        and plan_local_only
        and plan_github_deferred
        and (not plan_remote_required)
        and (not plan_execution_allowed)
        and matrix_status == "ready"
        and matrix_all_steps_metadata_only
        and (not matrix_any_codex)
        and (not matrix_any_git_mutation)
        and (not matrix_any_remote)
    )

    selected_step_id = _as_non_negative_int(step_selection.get("selected_step_id"), default=1)
    selected_step_name = _normalize_text(
        step_selection.get("selected_step_name"),
        default="read_current_state",
    )
    status = "blocked"
    gate_status = "blocked"
    blocked_reason = "local_end_to_end_dry_run_plan_not_ready"
    one_shot_gate_ready = False
    next_action = "complete_local_end_to_end_dry_run_plan_builder"
    summary = (
        "Local-only one-shot execution gate is blocked because Prompt324 dry-run metadata is missing or incompatible."
    )
    if not worktree_clean:
        blocked_reason = "tracked_changes_present_before_one_shot_execution_gate"
        next_action = "commit_or_reconcile_tracked_changes_before_one_shot_gate"
        summary = "Local-only one-shot execution gate is blocked by tracked changes in the worktree."
    elif not expected_head_tag_exists:
        blocked_reason = "expected_prompt324_tag_missing"
        next_action = "commit_and_tag_prompt324_before_one_shot_gate"
        summary = (
            "Local-only one-shot execution gate is blocked because expected Prompt324 tag is missing."
        )
    elif not expected_head_tag_ancestor_of_head:
        blocked_reason = "expected_prompt324_tag_not_ancestor_of_head"
        next_action = "checkout_or_merge_history_where_prompt324_tag_is_ancestor_of_head"
        summary = (
            "Local-only one-shot execution gate is blocked because expected Prompt324 tag is not an ancestor of HEAD."
        )
    elif not dry_run_plan_ready:
        blocked_reason = "local_end_to_end_dry_run_plan_not_ready"
        next_action = "complete_local_end_to_end_dry_run_plan_builder"
        summary = (
            "Local-only one-shot execution gate is blocked because Prompt324 dry-run metadata is missing or incompatible."
        )
    else:
        status = "ready"
        gate_status = "ready"
        blocked_reason = "none"
        one_shot_gate_ready = True
        next_action = "prepare_bounded_local_autonomous_loop_controller"
        summary = (
            "Local-only one-shot execution gate is ready; execution remains disabled until an explicit adapter/gate enables a selected step."
        )

    return {
        "status": status,
        "gate_status": gate_status,
        "blocked_reason": blocked_reason,
        "source": "local_end_to_end_one_shot_execution_gate",
        "current_branch": current_branch,
        "head_short": head_short,
        "head_tags": head_tags,
        "expected_head_tag": expected_head_tag,
        "expected_head_tag_exists": expected_head_tag_exists,
        "expected_head_tag_ancestor_of_head": expected_head_tag_ancestor_of_head,
        "expected_head_tag_present": expected_head_tag_present,
        "worktree_clean": worktree_clean,
        "changed_tracked_files": changed_tracked_files,
        "one_shot_gate_ready": one_shot_gate_ready,
        "local_only": True,
        "github_deferred": plan_github_deferred,
        "remote_required": plan_remote_required,
        "dry_run_plan_ready": dry_run_plan_ready,
        "selected_step_id": selected_step_id,
        "selected_step_name": selected_step_name,
        "step_count": step_count,
        "execution_allowed": False,
        "execution_performed": False,
        "codex_invoked": False,
        "commit_performed": False,
        "tag_performed": False,
        "push_performed": False,
        "pr_created": False,
        "merge_performed": False,
        "rollback_performed": False,
        "next_prompt_id_recommendation": "Prompt326-local",
        "next_prompt_title_recommendation": "bounded local autonomous loop controller",
        "next_action": next_action,
        "summary": summary,
    }

def _build_bounded_local_autonomous_loop_state(
    *,
    execution_repo_path: str,
    one_cycle_controller_dir: Path,
    expected_head_tag: str,
    current_cycle_count: int,
    max_cycle_count: int,
) -> dict[str, Any]:
    _ = execution_repo_path
    normalized_repo_path = _APPROVE_COMMIT_TAG_EXECUTION_REPO_PATH
    dry_run_plan_path = one_cycle_controller_dir / "local_end_to_end_dry_run_plan.json"
    dry_run_step_matrix_path = (
        one_cycle_controller_dir / "local_end_to_end_dry_run_step_matrix.json"
    )
    dry_run_receipt_path = one_cycle_controller_dir / "local_end_to_end_dry_run_receipt.json"
    one_shot_step_selection_path = (
        one_cycle_controller_dir / "local_end_to_end_one_shot_step_selection.json"
    )
    one_shot_execution_gate_path = (
        one_cycle_controller_dir / "local_end_to_end_one_shot_execution_gate.json"
    )
    one_shot_execution_receipt_path = (
        one_cycle_controller_dir / "local_end_to_end_one_shot_execution_receipt.json"
    )
    controller_readiness_boundary_path = (
        one_cycle_controller_dir / "local_end_to_end_controller_readiness_boundary.json"
    )
    controller_component_matrix_path = (
        one_cycle_controller_dir / "local_end_to_end_controller_component_matrix.json"
    )
    controller_gap_report_path = (
        one_cycle_controller_dir / "local_end_to_end_controller_gap_report.json"
    )

    status_short_cmd = subprocess.run(
        ["git", "status", "--short", "--untracked-files=no"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    current_branch_cmd = subprocess.run(
        ["git", "branch", "--show-current"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    head_short_cmd = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    head_tags_cmd = subprocess.run(
        ["git", "tag", "--points-at", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    expected_head_tag_exists_cmd = subprocess.run(
        ["git", "tag", "--list", expected_head_tag],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    expected_head_tag_exists = False
    expected_head_tag_ancestor_of_head = False
    expected_tag_ancestor_cmd: subprocess.CompletedProcess[str] | None = None
    if expected_head_tag_exists_cmd.returncode == 0:
        expected_head_tag_exists = expected_head_tag in {
            line.strip()
            for line in (expected_head_tag_exists_cmd.stdout or "").splitlines()
            if line.strip()
        }
        if expected_head_tag_exists:
            expected_tag_ancestor_cmd = subprocess.run(
                ["git", "merge-base", "--is-ancestor", expected_head_tag, "HEAD"],
                text=True,
                capture_output=True,
                check=False,
                cwd=normalized_repo_path,
                shell=False,
            )
            expected_head_tag_ancestor_of_head = expected_tag_ancestor_cmd.returncode == 0

    metadata_collection_ok = (
        status_short_cmd.returncode == 0
        and current_branch_cmd.returncode == 0
        and head_short_cmd.returncode == 0
        and head_tags_cmd.returncode == 0
        and expected_head_tag_exists_cmd.returncode == 0
        and (
            expected_tag_ancestor_cmd is None
            or expected_tag_ancestor_cmd.returncode in {0, 1}
        )
    )
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
    current_branch = (
        _normalize_text(current_branch_cmd.stdout, default="")
        if metadata_collection_ok
        else ""
    )
    head_short = (
        _normalize_text(head_short_cmd.stdout, default="")
        if metadata_collection_ok
        else ""
    )
    head_tags = (
        sorted(
            {
                line.strip()
                for line in (head_tags_cmd.stdout or "").splitlines()
                if line.strip()
            }
        )
        if metadata_collection_ok
        else []
    )
    expected_head_tag_present = bool(
        expected_head_tag_exists and expected_head_tag_ancestor_of_head
    )

    dry_run_plan_state = _read_json_object_if_exists(dry_run_plan_path) or {}
    dry_run_step_matrix_state = _read_json_object_if_exists(dry_run_step_matrix_path) or {}
    dry_run_receipt_state = _read_json_object_if_exists(dry_run_receipt_path) or {}
    one_shot_step_selection_state = (
        _read_json_object_if_exists(one_shot_step_selection_path) or {}
    )
    one_shot_execution_gate_state = (
        _read_json_object_if_exists(one_shot_execution_gate_path) or {}
    )
    one_shot_execution_receipt_state = (
        _read_json_object_if_exists(one_shot_execution_receipt_path) or {}
    )
    _ = _read_json_object_if_exists(controller_readiness_boundary_path) or {}
    _ = _read_json_object_if_exists(controller_component_matrix_path) or {}
    _ = _read_json_object_if_exists(controller_gap_report_path) or {}

    step_count = _as_non_negative_int(
        dry_run_step_matrix_state.get("step_count"),
        default=_as_non_negative_int(dry_run_plan_state.get("step_count"), default=16),
    )
    if step_count <= 0:
        step_count = 16

    selected_step_id = _as_non_negative_int(
        one_shot_step_selection_state.get("selected_step_id"),
        default=_as_non_negative_int(
            one_shot_execution_gate_state.get("selected_step_id"),
            default=_as_non_negative_int(
                one_shot_execution_receipt_state.get("selected_step_id"),
                default=1,
            ),
        ),
    )
    selected_step_name = _normalize_text(
        one_shot_step_selection_state.get("selected_step_name"),
        default=_normalize_text(
            one_shot_execution_gate_state.get("selected_step_name"),
            default=_normalize_text(
                one_shot_execution_receipt_state.get("selected_step_name"),
                default="read_current_state",
            ),
        ),
    )
    one_shot_sequence_complete = bool(
        one_shot_step_selection_state.get("one_shot_sequence_complete", False)
    )

    def _read_surface_flag(
        key: str,
        *,
        default: bool,
    ) -> bool:
        for surface in (
            one_shot_execution_gate_state,
            one_shot_execution_receipt_state,
            dry_run_plan_state,
            dry_run_receipt_state,
        ):
            if not isinstance(surface, Mapping) or key not in surface:
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

    execution_flags = {
        "execution_performed": _read_surface_flag(
            "execution_performed",
            default=False,
        ),
        "codex_invoked": _read_surface_flag("codex_invoked", default=False),
        "commit_performed": _read_surface_flag("commit_performed", default=False),
        "tag_performed": _read_surface_flag("tag_performed", default=False),
        "push_performed": _read_surface_flag("push_performed", default=False),
        "pr_created": _read_surface_flag("pr_created", default=False),
        "merge_performed": _read_surface_flag("merge_performed", default=False),
        "rollback_performed": _read_surface_flag("rollback_performed", default=False),
    }
    flags_clear = not any(bool(value) for value in execution_flags.values())

    github_deferred = bool(
        dry_run_plan_state.get(
            "github_deferred",
            one_shot_execution_gate_state.get("github_deferred", True),
        )
    )
    remote_required = bool(
        dry_run_plan_state.get(
            "remote_required",
            one_shot_execution_gate_state.get("remote_required", False),
        )
    )
    dry_run_artifacts_exist = dry_run_plan_path.exists() and dry_run_step_matrix_path.exists()
    one_shot_artifacts_exist = (
        one_shot_step_selection_path.exists()
        and one_shot_execution_gate_path.exists()
        and one_shot_execution_receipt_path.exists()
    )
    activation_compatible = bool(
        dry_run_artifacts_exist
        and one_shot_artifacts_exist
        and step_count == 16
        and github_deferred
        and (not remote_required)
        and flags_clear
    )

    current_cycle = max(0, int(current_cycle_count))
    max_cycle = max(0, int(max_cycle_count))
    if max_cycle <= 0:
        max_cycle = _BOUNDED_LOCAL_AUTONOMOUS_LOOP_DEFAULT_MAX_CYCLE_COUNT

    status = "blocked"
    loop_status = "blocked"
    blocked_reason = "local_one_shot_or_dry_run_artifacts_missing"
    bounded_loop_ready = False
    bounded_loop_complete = False
    should_continue = False
    execution_allowed = False
    next_action = "complete_local_one_shot_gate_before_bounded_loop"
    stale_one_shot_artifact_block_ignored = False
    summary = (
        "Bounded local autonomous loop is blocked because required Prompt324/Prompt325 metadata artifacts are missing or incompatible."
    )

    if not worktree_clean:
        blocked_reason = "tracked_changes_present_before_bounded_local_loop"
        next_action = "commit_or_reconcile_tracked_changes_before_bounded_local_loop"
        summary = "Bounded local autonomous loop is blocked by tracked changes in the worktree."
    elif not expected_head_tag_exists:
        blocked_reason = "expected_prompt325_tag_missing"
        next_action = "commit_and_tag_prompt325_before_bounded_local_loop"
        summary = (
            "Bounded local autonomous loop is blocked because expected Prompt325 tag is missing."
        )
    elif not expected_head_tag_ancestor_of_head:
        blocked_reason = "expected_prompt325_tag_not_ancestor_of_head"
        next_action = "checkout_or_merge_history_where_prompt325_tag_is_ancestor_of_head"
        summary = (
            "Bounded local autonomous loop is blocked because expected Prompt325 tag is not an ancestor of HEAD."
        )
    elif not activation_compatible:
        blocked_reason = "local_one_shot_or_dry_run_artifacts_missing"
        next_action = "complete_local_one_shot_gate_before_bounded_loop"
        summary = (
            "Bounded local autonomous loop is blocked because required Prompt324/Prompt325 metadata artifacts are missing or incompatible."
        )
    else:
        gate_status = _normalize_text(
            one_shot_execution_gate_state.get("status"),
            default=_normalize_text(
                one_shot_execution_gate_state.get("gate_status"),
                default="",
            ),
        )
        gate_blocked_reason = _normalize_text(
            one_shot_execution_gate_state.get("blocked_reason"),
            default="",
        )
        selected_step_present = selected_step_id > 0 and bool(selected_step_name)
        stale_one_shot_artifact_block_ignored = bool(
            gate_status == "blocked"
            and gate_blocked_reason == "tracked_changes_present_before_one_shot_execution_gate"
            and selected_step_present
        )
        status = "ready"
        loop_status = "ready"
        blocked_reason = "none"
        bounded_loop_ready = True
        if current_cycle >= max_cycle:
            bounded_loop_complete = True
            should_continue = False
            next_action = "prepare_local_failure_terminal_decision_boundary"
            summary = (
                "Bounded local autonomous loop reached the configured max cycle count and should stop safely."
            )
        elif one_shot_sequence_complete or selected_step_id <= 0:
            bounded_loop_complete = True
            should_continue = False
            next_action = "prepare_local_terminal_summary"
            selected_step_id = 0
            selected_step_name = "none"
            summary = (
                "Bounded local autonomous loop reached one-shot sequence completion and should stop safely."
            )
        else:
            bounded_loop_complete = False
            should_continue = True
            next_action = "prepare_selected_step_execution_adapter"
            summary = (
                "Bounded local autonomous loop is ready to continue to the selected one-shot step."
            )

    if selected_step_id <= 0 and not one_shot_sequence_complete:
        selected_step_name = "none"

    return {
        "status": status,
        "loop_status": loop_status,
        "blocked_reason": blocked_reason,
        "source": "bounded_local_autonomous_loop_controller",
        "current_branch": current_branch,
        "head_short": head_short,
        "head_tags": head_tags,
        "expected_head_tag": expected_head_tag,
        "expected_head_tag_exists": expected_head_tag_exists,
        "expected_head_tag_ancestor_of_head": expected_head_tag_ancestor_of_head,
        "expected_head_tag_present": expected_head_tag_present,
        "worktree_clean": worktree_clean,
        "changed_tracked_files": changed_tracked_files,
        "bounded_loop_ready": bounded_loop_ready,
        "bounded_loop_complete": bounded_loop_complete,
        "current_cycle_count": current_cycle,
        "max_cycle_count": max_cycle,
        "should_continue": should_continue,
        "selected_step_id": selected_step_id if selected_step_id > 0 else None,
        "selected_step_name": selected_step_name,
        "step_count": step_count,
        "one_shot_sequence_complete": one_shot_sequence_complete,
        "stale_one_shot_artifact_block_ignored": stale_one_shot_artifact_block_ignored,
        "github_deferred": github_deferred,
        "remote_required": remote_required,
        "execution_allowed": execution_allowed,
        "execution_performed": False,
        "codex_invoked": False,
        "commit_performed": False,
        "tag_performed": False,
        "push_performed": False,
        "pr_created": False,
        "merge_performed": False,
        "rollback_performed": False,
        "next_action": next_action,
        "summary": summary,
    }

def _build_bounded_local_autonomous_loop_decision_state(
    *,
    loop_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    state = dict(loop_state) if isinstance(loop_state, Mapping) else {}
    status = _normalize_text(state.get("status"), default="blocked")
    blocked_reason = _normalize_text(
        state.get("blocked_reason"),
        default="local_one_shot_or_dry_run_artifacts_missing",
    )
    bounded_loop_ready = bool(state.get("bounded_loop_ready", False))
    bounded_loop_complete = bool(state.get("bounded_loop_complete", False))
    should_continue = bool(state.get("should_continue", False))
    current_cycle_count = _as_non_negative_int(
        state.get("current_cycle_count"),
        default=_BOUNDED_LOCAL_AUTONOMOUS_LOOP_DEFAULT_CURRENT_CYCLE_COUNT,
    )
    max_cycle_count = _as_non_negative_int(
        state.get("max_cycle_count"),
        default=_BOUNDED_LOCAL_AUTONOMOUS_LOOP_DEFAULT_MAX_CYCLE_COUNT,
    )
    selected_step_id = _as_optional_int(state.get("selected_step_id"))
    if selected_step_id is not None and selected_step_id <= 0:
        selected_step_id = None
    selected_step_name = _normalize_text(state.get("selected_step_name"), default="none")
    one_shot_sequence_complete = bool(state.get("one_shot_sequence_complete", False))

    decision_status = "blocked"
    decision = "stop_blocked"
    safe_to_stop = True
    next_action = _normalize_text(
        state.get("next_action"),
        default="complete_local_one_shot_gate_before_bounded_loop",
    )
    summary = _normalize_text(
        state.get("summary"),
        default="Bounded local autonomous loop is blocked.",
    )

    if status == "ready" and bounded_loop_ready:
        decision_status = "ready"
        if current_cycle_count >= max_cycle_count:
            decision = "stop_max_cycle_reached"
            safe_to_stop = True
            should_continue = False
            bounded_loop_complete = True
            next_action = "prepare_local_failure_terminal_decision_boundary"
            summary = "Max cycle count reached; bounded local autonomous loop should stop."
        elif one_shot_sequence_complete or selected_step_id is None:
            decision = "stop_completed"
            safe_to_stop = True
            should_continue = False
            bounded_loop_complete = True
            next_action = "prepare_local_terminal_summary"
            summary = "One-shot sequence is complete; bounded local autonomous loop should stop."
        elif should_continue:
            decision = "continue_to_selected_step"
            safe_to_stop = False
            bounded_loop_complete = False
            next_action = "prepare_selected_step_execution_adapter"
            summary = (
                "Bounded local autonomous loop should continue to the selected one-shot step; execution remains disabled."
            )
        else:
            decision = "stop_blocked"
            safe_to_stop = False
            summary = (
                "Bounded local autonomous loop is ready but cannot continue because step selection is incomplete."
            )

    return {
        "status": status,
        "decision_status": decision_status,
        "decision": decision,
        "blocked_reason": blocked_reason,
        "source": "bounded_local_autonomous_loop_controller",
        "bounded_loop_ready": bounded_loop_ready,
        "bounded_loop_complete": bounded_loop_complete,
        "should_continue": should_continue,
        "safe_to_stop": safe_to_stop,
        "current_cycle_count": current_cycle_count,
        "max_cycle_count": max_cycle_count,
        "selected_step_id": selected_step_id,
        "selected_step_name": selected_step_name,
        "next_prompt_id_recommendation": "Prompt327-local",
        "next_prompt_title_recommendation": (
            "local selected-step execution adapter and terminal/failure decision boundary"
        ),
        "next_action": next_action,
        "summary": summary,
    }

def _build_selected_step_execution_adapter_state(
    *,
    execution_repo_path: str,
    one_cycle_controller_dir: Path,
    expected_head_tag: str,
) -> dict[str, Any]:
    _ = execution_repo_path
    normalized_repo_path = _APPROVE_COMMIT_TAG_EXECUTION_REPO_PATH
    bounded_loop_state_path = one_cycle_controller_dir / "bounded_local_autonomous_loop_state.json"
    bounded_loop_decision_path = (
        one_cycle_controller_dir / "bounded_local_autonomous_loop_decision.json"
    )
    bounded_loop_receipt_path = (
        one_cycle_controller_dir / "bounded_local_autonomous_loop_receipt.json"
    )
    one_shot_step_selection_path = (
        one_cycle_controller_dir / "local_end_to_end_one_shot_step_selection.json"
    )
    one_shot_execution_gate_path = (
        one_cycle_controller_dir / "local_end_to_end_one_shot_execution_gate.json"
    )
    one_shot_execution_receipt_path = (
        one_cycle_controller_dir / "local_end_to_end_one_shot_execution_receipt.json"
    )
    dry_run_plan_path = one_cycle_controller_dir / "local_end_to_end_dry_run_plan.json"
    dry_run_step_matrix_path = (
        one_cycle_controller_dir / "local_end_to_end_dry_run_step_matrix.json"
    )
    dry_run_receipt_path = one_cycle_controller_dir / "local_end_to_end_dry_run_receipt.json"

    status_short_cmd = subprocess.run(
        ["git", "status", "--short", "--untracked-files=no"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    current_branch_cmd = subprocess.run(
        ["git", "branch", "--show-current"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    head_short_cmd = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    head_tags_cmd = subprocess.run(
        ["git", "tag", "--points-at", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    expected_head_tag_exists_cmd = subprocess.run(
        ["git", "tag", "--list", expected_head_tag],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    expected_head_tag_exists = False
    expected_head_tag_ancestor_of_head = False
    expected_tag_ancestor_cmd: subprocess.CompletedProcess[str] | None = None
    if expected_head_tag_exists_cmd.returncode == 0:
        expected_head_tag_exists = expected_head_tag in {
            line.strip()
            for line in (expected_head_tag_exists_cmd.stdout or "").splitlines()
            if line.strip()
        }
        if expected_head_tag_exists:
            expected_tag_ancestor_cmd = subprocess.run(
                ["git", "merge-base", "--is-ancestor", expected_head_tag, "HEAD"],
                text=True,
                capture_output=True,
                check=False,
                cwd=normalized_repo_path,
                shell=False,
            )
            expected_head_tag_ancestor_of_head = expected_tag_ancestor_cmd.returncode == 0
    metadata_collection_ok = (
        status_short_cmd.returncode == 0
        and current_branch_cmd.returncode == 0
        and head_short_cmd.returncode == 0
        and head_tags_cmd.returncode == 0
        and expected_head_tag_exists_cmd.returncode == 0
        and (
            expected_tag_ancestor_cmd is None
            or expected_tag_ancestor_cmd.returncode in {0, 1}
        )
    )
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
    current_branch = (
        _normalize_text(current_branch_cmd.stdout, default="")
        if metadata_collection_ok
        else ""
    )
    head_short = (
        _normalize_text(head_short_cmd.stdout, default="")
        if metadata_collection_ok
        else ""
    )
    head_tags = (
        sorted(
            {
                line.strip()
                for line in (head_tags_cmd.stdout or "").splitlines()
                if line.strip()
            }
        )
        if metadata_collection_ok
        else []
    )
    expected_head_tag_present = bool(
        expected_head_tag_exists and expected_head_tag_ancestor_of_head
    )

    bounded_loop_state = _read_json_object_if_exists(bounded_loop_state_path) or {}
    bounded_loop_decision = _read_json_object_if_exists(bounded_loop_decision_path) or {}
    bounded_loop_receipt = _read_json_object_if_exists(bounded_loop_receipt_path) or {}
    one_shot_step_selection = _read_json_object_if_exists(one_shot_step_selection_path) or {}
    one_shot_execution_gate = _read_json_object_if_exists(one_shot_execution_gate_path) or {}
    one_shot_execution_receipt = _read_json_object_if_exists(one_shot_execution_receipt_path) or {}
    dry_run_plan = _read_json_object_if_exists(dry_run_plan_path) or {}
    _ = _read_json_object_if_exists(dry_run_step_matrix_path) or {}
    dry_run_receipt = _read_json_object_if_exists(dry_run_receipt_path) or {}

    bounded_artifacts_exist = (
        bounded_loop_state_path.exists()
        and bounded_loop_decision_path.exists()
        and bounded_loop_receipt_path.exists()
    )

    selected_step_id = _as_non_negative_int(
        bounded_loop_state.get("selected_step_id"),
        default=_as_non_negative_int(
            one_shot_step_selection.get("selected_step_id"),
            default=_as_non_negative_int(
                one_shot_execution_gate.get("selected_step_id"),
                default=_as_non_negative_int(
                    one_shot_execution_receipt.get("selected_step_id"),
                    default=1,
                ),
            ),
        ),
    )
    if selected_step_id <= 0:
        selected_step_id = 1
    selected_step_name = _normalize_text(
        bounded_loop_state.get("selected_step_name"),
        default=_normalize_text(
            one_shot_step_selection.get("selected_step_name"),
            default=_normalize_text(
                one_shot_execution_gate.get("selected_step_name"),
                default=_normalize_text(
                    one_shot_execution_receipt.get("selected_step_name"),
                    default="read_current_state",
                ),
            ),
        ),
    )
    if not selected_step_name or selected_step_name == "none":
        selected_step_name = "read_current_state" if selected_step_id == 1 else selected_step_name
    selected_step_operation = _normalize_text(selected_step_name, default="read_current_state")
    if not selected_step_operation or selected_step_operation == "none":
        selected_step_operation = "read_current_state"

    def _read_surface_flag(key: str, *, default: bool) -> bool:
        for surface in (
            bounded_loop_state,
            bounded_loop_decision,
            bounded_loop_receipt,
            one_shot_execution_gate,
            one_shot_execution_receipt,
            dry_run_plan,
            dry_run_receipt,
        ):
            if not isinstance(surface, Mapping) or key not in surface:
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

    execution_performed = _read_surface_flag("execution_performed", default=False)
    codex_invoked = _read_surface_flag("codex_invoked", default=False)
    commit_performed = _read_surface_flag("commit_performed", default=False)
    tag_performed = _read_surface_flag("tag_performed", default=False)
    push_performed = _read_surface_flag("push_performed", default=False)
    pr_created = _read_surface_flag("pr_created", default=False)
    merge_performed = _read_surface_flag("merge_performed", default=False)
    rollback_performed = _read_surface_flag("rollback_performed", default=False)
    execution_flags_clear = not any(
        (
            execution_performed,
            codex_invoked,
            commit_performed,
            tag_performed,
            push_performed,
            pr_created,
            merge_performed,
            rollback_performed,
        )
    )

    github_deferred = bool(
        bounded_loop_state.get(
            "github_deferred",
            dry_run_plan.get("github_deferred", True),
        )
    )
    remote_required = bool(
        bounded_loop_state.get(
            "remote_required",
            dry_run_plan.get("remote_required", False),
        )
    )
    bounded_loop_ready = bool(bounded_loop_state.get("bounded_loop_ready", False))
    bounded_loop_decision_value = _normalize_text(
        bounded_loop_decision.get("decision"),
        default="stop_blocked",
    )
    bounded_loop_should_continue = bool(
        bounded_loop_state.get(
            "should_continue",
            bounded_loop_decision.get("should_continue", False),
        )
    )
    bounded_blocked_reason = _normalize_text(
        bounded_loop_state.get("blocked_reason"),
        default=_normalize_text(
            bounded_loop_decision.get("blocked_reason"),
            default=_normalize_text(
                bounded_loop_receipt.get("blocked_reason"),
                default="bounded_local_loop_not_ready_for_selected_step_execution_adapter",
            ),
        ),
    )
    stale_bounded_loop_artifact_block_ignored = bool(
        bounded_blocked_reason == "tracked_changes_present_before_bounded_local_loop"
        and worktree_clean
        and expected_head_tag_present
    )

    status = "blocked"
    adapter_status = "blocked"
    blocked_reason = "bounded_local_loop_artifacts_missing"
    selected_step_execution_ready = False
    execution_allowed = False
    next_action = "complete_bounded_local_loop_before_selected_step_execution_adapter"
    summary = (
        "Selected-step execution adapter is blocked because required bounded local loop artifacts are missing."
    )

    if not worktree_clean:
        blocked_reason = "tracked_changes_present_before_selected_step_execution_adapter"
        next_action = "commit_or_reconcile_tracked_changes_before_selected_step_execution_adapter"
        summary = "Selected-step execution adapter is blocked by tracked changes in the worktree."
    elif not expected_head_tag_exists:
        blocked_reason = "expected_prompt326_tag_missing"
        next_action = "commit_and_tag_prompt326_before_selected_step_execution_adapter"
        summary = (
            "Selected-step execution adapter is blocked because expected Prompt326 tag is missing."
        )
    elif not expected_head_tag_ancestor_of_head:
        blocked_reason = "expected_prompt326_tag_not_ancestor_of_head"
        next_action = "checkout_or_merge_history_where_prompt326_tag_is_ancestor_of_head"
        summary = (
            "Selected-step execution adapter is blocked because the expected Prompt326 tag is not an ancestor of HEAD."
        )
    elif not bounded_artifacts_exist:
        blocked_reason = "bounded_local_loop_artifacts_missing"
        next_action = "complete_bounded_local_loop_before_selected_step_execution_adapter"
        summary = (
            "Selected-step execution adapter is blocked because required bounded local loop artifacts are missing."
        )
    elif not execution_flags_clear:
        blocked_reason = "execution_flags_not_clear_before_selected_step_execution_adapter"
        next_action = "reconcile_execution_flags_before_selected_step_execution_adapter"
        summary = (
            "Selected-step execution adapter is blocked because prior execution flags are not clear."
        )
    elif (not github_deferred) or remote_required:
        blocked_reason = "selected_step_execution_adapter_local_only_posture_required"
        next_action = "restore_local_only_posture_before_selected_step_execution_adapter"
        summary = (
            "Selected-step execution adapter is blocked because local-only posture requirements are not satisfied."
        )
    elif bounded_loop_decision_value == "continue_to_selected_step" or (
        stale_bounded_loop_artifact_block_ignored and worktree_clean and expected_head_tag_present
    ):
        status = "ready"
        adapter_status = "ready"
        blocked_reason = "none"
        selected_step_execution_ready = True
        execution_allowed = False
        next_action = "prepare_selected_step_execution_live_gate"
        summary = (
            "Selected-step execution adapter is ready and prepared as a metadata-only boundary; live step execution remains disabled."
        )
    else:
        blocked_reason = _normalize_text(
            bounded_blocked_reason,
            default="bounded_local_loop_not_ready_for_selected_step_execution_adapter",
        )
        next_action = _normalize_text(
            bounded_loop_decision.get("next_action"),
            default=_normalize_text(
                bounded_loop_state.get("next_action"),
                default="complete_bounded_local_loop_before_selected_step_execution_adapter",
            ),
        )
        summary = (
            "Selected-step execution adapter is blocked because bounded local loop is not ready to continue to a selected step."
        )

    return {
        "status": status,
        "adapter_status": adapter_status,
        "blocked_reason": blocked_reason,
        "source": "selected_step_execution_adapter_boundary",
        "current_branch": current_branch,
        "head_short": head_short,
        "head_tags": head_tags,
        "expected_head_tag": expected_head_tag,
        "expected_head_tag_exists": expected_head_tag_exists,
        "expected_head_tag_ancestor_of_head": expected_head_tag_ancestor_of_head,
        "expected_head_tag_present": expected_head_tag_present,
        "worktree_clean": worktree_clean,
        "changed_tracked_files": changed_tracked_files,
        "selected_step_execution_ready": selected_step_execution_ready,
        "selected_step_id": selected_step_id,
        "selected_step_name": selected_step_name,
        "selected_step_operation": selected_step_operation,
        "bounded_loop_ready": bounded_loop_ready,
        "bounded_loop_decision": bounded_loop_decision_value,
        "bounded_loop_should_continue": bounded_loop_should_continue,
        "stale_bounded_loop_artifact_block_ignored": stale_bounded_loop_artifact_block_ignored,
        "github_deferred": github_deferred,
        "remote_required": remote_required,
        "execution_allowed": execution_allowed,
        "execution_performed": False,
        "codex_invoked": False,
        "commit_performed": False,
        "tag_performed": False,
        "push_performed": False,
        "pr_created": False,
        "merge_performed": False,
        "rollback_performed": False,
        "next_action": next_action,
        "summary": summary,
    }

def _build_selected_step_execution_plan_state(
    *,
    adapter_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    adapter = dict(adapter_state) if isinstance(adapter_state, Mapping) else {}
    status = _normalize_text(adapter.get("status"), default="blocked")
    adapter_status = _normalize_text(adapter.get("adapter_status"), default=status)
    blocked_reason = _normalize_text(
        adapter.get("blocked_reason"),
        default="bounded_local_loop_artifacts_missing",
    )
    selected_step_id = _as_non_negative_int(adapter.get("selected_step_id"), default=1)
    if selected_step_id <= 0:
        selected_step_id = 1
    selected_step_name = _normalize_text(
        adapter.get("selected_step_name"),
        default="read_current_state",
    )
    selected_step_operation = _normalize_text(
        adapter.get("selected_step_operation"),
        default=selected_step_name,
    )
    if not selected_step_operation:
        selected_step_operation = "read_current_state"
    execution_performed = False
    codex_invoked = False
    commit_performed = False
    tag_performed = False
    push_performed = False
    pr_created = False
    merge_performed = False
    rollback_performed = False
    execution_allowed = False
    selected_step_execution_ready = bool(adapter.get("selected_step_execution_ready", False))

    plan_status = "blocked"
    next_action = _normalize_text(
        adapter.get("next_action"),
        default="complete_bounded_local_loop_before_selected_step_execution_adapter",
    )
    if status == "ready" and adapter_status == "ready" and selected_step_execution_ready:
        plan_status = "ready"
        next_action = "prepare_selected_step_execution_live_gate"

    return {
        "status": "ready" if plan_status == "ready" else "blocked",
        "plan_status": plan_status,
        "blocked_reason": "none" if plan_status == "ready" else blocked_reason,
        "source": "selected_step_execution_adapter_boundary",
        "adapter_kind": "metadata_only_selected_step_boundary",
        "selected_step_id": selected_step_id,
        "selected_step_name": selected_step_name,
        "selected_step_operation": selected_step_operation,
        "operation_intent": "collect_current_repo_and_controller_metadata",
        "live_execution_required": True,
        "live_execution_enabled": False,
        "execution_allowed": execution_allowed,
        "execution_performed": execution_performed,
        "codex_invoked": codex_invoked,
        "commit_performed": commit_performed,
        "tag_performed": tag_performed,
        "push_performed": push_performed,
        "pr_created": pr_created,
        "merge_performed": merge_performed,
        "rollback_performed": rollback_performed,
        "next_action": next_action,
        "summary": (
            "Selected-step execution plan is ready as a metadata-only boundary; live step execution remains disabled."
            if plan_status == "ready"
            else "Selected-step execution plan is blocked because adapter prerequisites are not satisfied."
        ),
    }

def _build_selected_step_live_execution_gate_state(
    *,
    execution_repo_path: str,
    one_cycle_controller_dir: Path,
    expected_head_tag: str,
) -> dict[str, Any]:
    _ = execution_repo_path
    normalized_repo_path = _APPROVE_COMMIT_TAG_EXECUTION_REPO_PATH
    selected_step_execution_adapter_state_path = (
        one_cycle_controller_dir / "selected_step_execution_adapter_state.json"
    )
    selected_step_execution_plan_path = one_cycle_controller_dir / "selected_step_execution_plan.json"
    selected_step_execution_receipt_path = (
        one_cycle_controller_dir / "selected_step_execution_receipt.json"
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
    local_end_to_end_one_shot_step_selection_path = (
        one_cycle_controller_dir / "local_end_to_end_one_shot_step_selection.json"
    )
    local_end_to_end_one_shot_execution_gate_path = (
        one_cycle_controller_dir / "local_end_to_end_one_shot_execution_gate.json"
    )
    local_end_to_end_one_shot_execution_receipt_path = (
        one_cycle_controller_dir / "local_end_to_end_one_shot_execution_receipt.json"
    )
    local_end_to_end_dry_run_plan_path = one_cycle_controller_dir / "local_end_to_end_dry_run_plan.json"
    local_end_to_end_dry_run_step_matrix_path = (
        one_cycle_controller_dir / "local_end_to_end_dry_run_step_matrix.json"
    )
    local_end_to_end_dry_run_receipt_path = (
        one_cycle_controller_dir / "local_end_to_end_dry_run_receipt.json"
    )

    status_short_cmd = subprocess.run(
        ["git", "status", "--short", "--untracked-files=no"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    current_branch_cmd = subprocess.run(
        ["git", "branch", "--show-current"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    head_short_cmd = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    head_tags_cmd = subprocess.run(
        ["git", "tag", "--points-at", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    expected_tag_list_cmd = subprocess.run(
        ["git", "tag", "--list", expected_head_tag],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    expected_head_tag_exists = False
    expected_head_tag_ancestor_of_head = False
    expected_tag_ancestor_cmd: subprocess.CompletedProcess[str] | None = None
    if expected_tag_list_cmd.returncode == 0:
        expected_head_tag_exists = expected_head_tag in {
            line.strip()
            for line in (expected_tag_list_cmd.stdout or "").splitlines()
            if line.strip()
        }
        if expected_head_tag_exists:
            expected_tag_ancestor_cmd = subprocess.run(
                ["git", "merge-base", "--is-ancestor", expected_head_tag, "HEAD"],
                text=True,
                capture_output=True,
                check=False,
                cwd=normalized_repo_path,
                shell=False,
            )
            expected_head_tag_ancestor_of_head = expected_tag_ancestor_cmd.returncode == 0
    metadata_collection_ok = (
        status_short_cmd.returncode == 0
        and current_branch_cmd.returncode == 0
        and head_short_cmd.returncode == 0
        and head_tags_cmd.returncode == 0
        and expected_tag_list_cmd.returncode == 0
        and (
            expected_tag_ancestor_cmd is None
            or expected_tag_ancestor_cmd.returncode in {0, 1}
        )
    )
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
    current_branch = (
        _normalize_text(current_branch_cmd.stdout, default="")
        if metadata_collection_ok
        else ""
    )
    head_short = (
        _normalize_text(head_short_cmd.stdout, default="")
        if metadata_collection_ok
        else ""
    )
    head_tags = (
        sorted(
            {
                line.strip()
                for line in (head_tags_cmd.stdout or "").splitlines()
                if line.strip()
            }
        )
        if metadata_collection_ok
        else []
    )
    expected_head_tag_present = bool(
        expected_head_tag_exists and expected_head_tag_ancestor_of_head
    )

    selected_step_execution_adapter_state = (
        _read_json_object_if_exists(selected_step_execution_adapter_state_path) or {}
    )
    selected_step_execution_plan_state = (
        _read_json_object_if_exists(selected_step_execution_plan_path) or {}
    )
    selected_step_execution_receipt_state = (
        _read_json_object_if_exists(selected_step_execution_receipt_path) or {}
    )
    bounded_local_autonomous_loop_state = (
        _read_json_object_if_exists(bounded_local_autonomous_loop_state_path) or {}
    )
    bounded_local_autonomous_loop_decision = (
        _read_json_object_if_exists(bounded_local_autonomous_loop_decision_path) or {}
    )
    bounded_local_autonomous_loop_receipt = (
        _read_json_object_if_exists(bounded_local_autonomous_loop_receipt_path) or {}
    )
    local_end_to_end_one_shot_step_selection = (
        _read_json_object_if_exists(local_end_to_end_one_shot_step_selection_path) or {}
    )
    local_end_to_end_one_shot_execution_gate = (
        _read_json_object_if_exists(local_end_to_end_one_shot_execution_gate_path) or {}
    )
    local_end_to_end_one_shot_execution_receipt = (
        _read_json_object_if_exists(local_end_to_end_one_shot_execution_receipt_path) or {}
    )
    local_end_to_end_dry_run_plan = _read_json_object_if_exists(local_end_to_end_dry_run_plan_path) or {}
    local_end_to_end_dry_run_step_matrix = (
        _read_json_object_if_exists(local_end_to_end_dry_run_step_matrix_path) or {}
    )
    local_end_to_end_dry_run_receipt = (
        _read_json_object_if_exists(local_end_to_end_dry_run_receipt_path) or {}
    )

    selected_step_adapter_artifacts_exist = (
        selected_step_execution_adapter_state_path.exists()
        and selected_step_execution_plan_path.exists()
        and selected_step_execution_receipt_path.exists()
    )
    selected_step_id = _as_non_negative_int(
        selected_step_execution_plan_state.get("selected_step_id"),
        default=_as_non_negative_int(
            selected_step_execution_adapter_state.get("selected_step_id"),
            default=_as_non_negative_int(
                selected_step_execution_receipt_state.get("selected_step_id"),
                default=1,
            ),
        ),
    )
    if selected_step_id <= 0:
        selected_step_id = 1
    selected_step_name = _normalize_text(
        selected_step_execution_plan_state.get("selected_step_name"),
        default=_normalize_text(
            selected_step_execution_adapter_state.get("selected_step_name"),
            default=_normalize_text(
                selected_step_execution_receipt_state.get("selected_step_name"),
                default="read_current_state",
            ),
        ),
    )
    selected_step_operation = _normalize_text(
        selected_step_execution_plan_state.get("selected_step_operation"),
        default=_normalize_text(
            selected_step_execution_adapter_state.get("selected_step_operation"),
            default=_normalize_text(
                selected_step_execution_receipt_state.get("selected_step_operation"),
                default=selected_step_name,
            ),
        ),
    )
    if selected_step_name.lower() == "read_current_state":
        selected_step_name = "read_current_state"
    if selected_step_operation.lower() == "read_current_state":
        selected_step_operation = "read_current_state"
    if not selected_step_name:
        selected_step_name = "read_current_state"
    if not selected_step_operation:
        selected_step_operation = "read_current_state"

    surfaces: tuple[Mapping[str, Any], ...] = (
        selected_step_execution_adapter_state,
        selected_step_execution_plan_state,
        selected_step_execution_receipt_state,
        bounded_local_autonomous_loop_state,
        bounded_local_autonomous_loop_decision,
        bounded_local_autonomous_loop_receipt,
        local_end_to_end_one_shot_step_selection,
        local_end_to_end_one_shot_execution_gate,
        local_end_to_end_one_shot_execution_receipt,
        local_end_to_end_dry_run_plan,
        local_end_to_end_dry_run_step_matrix,
        local_end_to_end_dry_run_receipt,
    )

    def _read_surface_flag(key: str, *, default: bool) -> bool:
        for surface in surfaces:
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

    def _read_surface_text(key: str, *, default: str = "") -> str:
        for surface in surfaces:
            if key not in surface:
                continue
            return _normalize_text(surface.get(key), default=default)
        return default

    live_execution_required = _read_surface_flag("live_execution_required", default=True)
    live_execution_enabled = _read_surface_flag("live_execution_enabled", default=False)
    github_deferred = _read_surface_flag("github_deferred", default=True)
    remote_required = _read_surface_flag("remote_required", default=False)
    execution_flags_clear = not any(
        (
            _read_surface_flag("execution_performed", default=False),
            _read_surface_flag("codex_invoked", default=False),
            _read_surface_flag("commit_performed", default=False),
            _read_surface_flag("tag_performed", default=False),
            _read_surface_flag("push_performed", default=False),
            _read_surface_flag("pr_created", default=False),
            _read_surface_flag("merge_performed", default=False),
            _read_surface_flag("rollback_performed", default=False),
        )
    )
    adapter_status = _normalize_text(
        selected_step_execution_adapter_state.get("adapter_status"),
        default=_normalize_text(selected_step_execution_adapter_state.get("status"), default="blocked"),
    )
    adapter_ready = bool(
        _normalize_text(selected_step_execution_adapter_state.get("status"), default="blocked") == "ready"
        and adapter_status == "ready"
        and bool(selected_step_execution_adapter_state.get("selected_step_execution_ready", False))
    )
    plan_ready = bool(
        _normalize_text(selected_step_execution_plan_state.get("status"), default="blocked") == "ready"
        and _normalize_text(selected_step_execution_plan_state.get("plan_status"), default="blocked")
        == "ready"
    )
    selected_step_adapter_ready = bool(selected_step_adapter_artifacts_exist and adapter_ready and plan_ready)
    adapter_blocked_reason = _normalize_text(
        selected_step_execution_adapter_state.get("blocked_reason"),
        default=_normalize_text(
            selected_step_execution_plan_state.get("blocked_reason"),
            default=_normalize_text(
                selected_step_execution_receipt_state.get("blocked_reason"),
                default="selected_step_execution_adapter_artifacts_missing",
            ),
        ),
    )
    stale_selected_step_adapter_block_ignored = bool(
        selected_step_adapter_artifacts_exist
        and adapter_blocked_reason
        == "tracked_changes_present_before_selected_step_execution_adapter"
        and worktree_clean
        and expected_head_tag_present
    )
    if stale_selected_step_adapter_block_ignored:
        selected_step_id = 1
        selected_step_name = "read_current_state"
        selected_step_operation = "read_current_state"

    selected_step_supported = bool(
        selected_step_id == 1
        and selected_step_name == "read_current_state"
        and selected_step_operation == "read_current_state"
    )

    status = "blocked"
    gate_status = "blocked"
    blocked_reason = "selected_step_execution_adapter_artifacts_missing"
    live_execution_ready = False
    live_execution_allowed = False
    next_action = "complete_selected_step_execution_adapter_before_live_gate"
    summary = (
        "Selected-step live execution gate is blocked because selected-step execution adapter artifacts are missing."
    )
    if not worktree_clean:
        blocked_reason = "tracked_changes_present_before_selected_step_live_execution_gate"
        next_action = "commit_or_reconcile_tracked_changes_before_selected_step_live_execution_gate"
        summary = (
            "Selected-step live execution gate is blocked because tracked changes are present in the worktree."
        )
    elif not expected_head_tag_exists:
        blocked_reason = "expected_prompt327_tag_missing"
        next_action = "commit_and_tag_prompt327_before_selected_step_live_execution_gate"
        summary = (
            "Selected-step live execution gate is blocked because the expected Prompt327 tag is missing."
        )
    elif not expected_head_tag_ancestor_of_head:
        blocked_reason = "expected_prompt327_tag_not_ancestor_of_head"
        next_action = "checkout_or_merge_history_where_prompt327_tag_is_ancestor_of_head"
        summary = (
            "Selected-step live execution gate is blocked because the expected Prompt327 tag is not an ancestor of HEAD."
        )
    elif not selected_step_adapter_artifacts_exist:
        blocked_reason = "selected_step_execution_adapter_artifacts_missing"
        next_action = "complete_selected_step_execution_adapter_before_live_gate"
        summary = (
            "Selected-step live execution gate is blocked because selected-step execution adapter artifacts are missing."
        )
    elif not selected_step_supported:
        blocked_reason = "unsupported_selected_step_operation"
        next_action = "add_selected_step_operation_adapter"
        summary = (
            "Selected-step live execution gate is blocked because the selected step operation is unsupported."
        )
    elif not live_execution_required:
        blocked_reason = "selected_step_live_execution_not_required"
        next_action = "prepare_selected_step_execution_result_route"
        summary = (
            "Selected-step live execution gate is blocked because live execution is not required by selected-step artifacts."
        )
    elif not execution_flags_clear:
        blocked_reason = "execution_flags_not_clear_before_selected_step_live_execution_gate"
        next_action = "reconcile_execution_flags_before_selected_step_live_execution_gate"
        summary = (
            "Selected-step live execution gate is blocked because prior execution flags are not clear."
        )
    elif (not github_deferred) or remote_required:
        blocked_reason = "selected_step_live_execution_gate_local_only_posture_required"
        next_action = "restore_local_only_posture_before_selected_step_live_execution_gate"
        summary = (
            "Selected-step live execution gate is blocked because local-only posture requirements are not satisfied."
        )
    elif selected_step_adapter_ready or stale_selected_step_adapter_block_ignored:
        status = "ready"
        gate_status = "ready"
        blocked_reason = "none"
        live_execution_ready = True
        live_execution_allowed = True
        next_action = "capture_selected_step_live_execution_result"
        summary = (
            "Selected-step live execution gate is ready for one metadata-only read_current_state execution."
        )
    else:
        blocked_reason = _read_surface_text(
            "blocked_reason",
            default="selected_step_execution_adapter_not_ready_for_live_execution_gate",
        )
        next_action = _read_surface_text(
            "next_action",
            default="complete_selected_step_execution_adapter_before_live_gate",
        )
        summary = (
            "Selected-step live execution gate is blocked because selected-step adapter readiness is incomplete."
        )

    return {
        "status": status,
        "gate_status": gate_status,
        "blocked_reason": blocked_reason,
        "source": "selected_step_live_execution_gate",
        "current_branch": current_branch,
        "head_short": head_short,
        "head_tags": head_tags,
        "expected_head_tag": expected_head_tag,
        "expected_head_tag_exists": expected_head_tag_exists,
        "expected_head_tag_ancestor_of_head": expected_head_tag_ancestor_of_head,
        "expected_head_tag_present": expected_head_tag_present,
        "worktree_clean": worktree_clean,
        "changed_tracked_files": changed_tracked_files,
        "selected_step_id": selected_step_id,
        "selected_step_name": selected_step_name,
        "selected_step_operation": selected_step_operation,
        "stale_selected_step_adapter_block_ignored": stale_selected_step_adapter_block_ignored,
        "live_execution_required": live_execution_required,
        "live_execution_enabled": live_execution_enabled,
        "live_execution_ready": live_execution_ready,
        "live_execution_allowed": live_execution_allowed,
        "live_execution_mode": "metadata_only_read_current_state",
        "github_deferred": github_deferred,
        "remote_required": remote_required,
        "execution_performed": False,
        "codex_invoked": False,
        "commit_performed": False,
        "tag_performed": False,
        "push_performed": False,
        "pr_created": False,
        "merge_performed": False,
        "rollback_performed": False,
        "next_action": next_action,
        "summary": summary,
    }

def _build_selected_step_live_execution_result_state(
    *,
    gate_state: Mapping[str, Any] | None,
    execution_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    gate = dict(gate_state) if isinstance(gate_state, Mapping) else {}
    execution = dict(execution_state) if isinstance(execution_state, Mapping) else {}
    selected_step_id = _as_non_negative_int(gate.get("selected_step_id"), default=1)
    if selected_step_id <= 0:
        selected_step_id = 1
    selected_step_name = _normalize_text(gate.get("selected_step_name"), default="read_current_state")
    selected_step_operation = _normalize_text(
        gate.get("selected_step_operation"),
        default=selected_step_name,
    )
    if not selected_step_operation:
        selected_step_operation = "read_current_state"
    read_current_state_completed = bool(execution.get("read_current_state_completed", False))
    live_execution_performed = bool(execution.get("live_execution_performed", False))
    blocked_reason = _normalize_text(
        execution.get("blocked_reason"),
        default=_normalize_text(gate.get("blocked_reason"), default="selected_step_live_execution_gate_not_ready"),
    )
    next_action = _normalize_text(
        execution.get("next_action"),
        default=_normalize_text(
            gate.get("next_action"),
            default="capture_selected_step_live_execution_result",
        ),
    )
    status = "blocked"
    result_status = "not_run"
    if read_current_state_completed and live_execution_performed:
        status = "completed"
        result_status = "completed"
        blocked_reason = "none"
        next_action = "prepare_selected_step_execution_result_route"

    return {
        "status": status,
        "result_status": result_status,
        "blocked_reason": blocked_reason,
        "source": "selected_step_live_execution_gate",
        "selected_step_id": selected_step_id,
        "selected_step_name": selected_step_name,
        "selected_step_operation": selected_step_operation,
        "live_execution_performed": live_execution_performed,
        "execution_performed": bool(execution.get("execution_performed", False)),
        "read_current_state_completed": read_current_state_completed,
        "current_branch": _normalize_text(
            execution.get("current_branch"),
            default=_normalize_text(gate.get("current_branch"), default=""),
        ),
        "head_short": _normalize_text(
            execution.get("head_short"),
            default=_normalize_text(gate.get("head_short"), default=""),
        ),
        "head_tags": _normalize_string_list(
            execution.get("head_tags")
            if isinstance(execution.get("head_tags"), (list, tuple))
            else gate.get("head_tags")
        ),
        "worktree_clean": bool(
            execution.get("worktree_clean", gate.get("worktree_clean", False))
        ),
        "changed_tracked_files": _normalize_string_list(
            execution.get("changed_tracked_files")
            if isinstance(execution.get("changed_tracked_files"), (list, tuple))
            else gate.get("changed_tracked_files")
        ),
        "artifact_status_summary": (
            dict(execution.get("artifact_status_summary"))
            if isinstance(execution.get("artifact_status_summary"), Mapping)
            else {}
        ),
        "codex_invoked": False,
        "commit_performed": False,
        "tag_performed": False,
        "push_performed": False,
        "pr_created": False,
        "merge_performed": False,
        "rollback_performed": False,
        "next_action": next_action,
        "summary": (
            "Selected-step live execution completed read_current_state metadata collection."
            if status == "completed"
            else "Selected-step live execution did not run."
        ),
    }

def _build_dry_run_selected_step_live_execution_gate_state(
    *,
    gate_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    state = dict(gate_state) if isinstance(gate_state, Mapping) else {}
    prior_ready = bool(
        _normalize_text(state.get("status"), default="blocked") == "ready"
        and _normalize_text(state.get("gate_status"), default="blocked") == "ready"
        and bool(state.get("live_execution_allowed", False))
    )
    if prior_ready:
        state.update(
            {
                "status": "blocked",
                "gate_status": "blocked",
                "blocked_reason": "selected_step_live_execution_dry_run_bypassed",
                "live_execution_ready": False,
                "live_execution_allowed": False,
                "execution_performed": False,
                "codex_invoked": False,
                "next_action": "prepare_selected_step_execution_result_route",
                "summary": (
                    "Selected-step live execution is bypassed in dry-run so downstream mutation-capable execution remains disabled."
                ),
            }
        )
    else:
        state.update(
            {
                "live_execution_ready": False,
                "live_execution_allowed": False,
                "execution_performed": False,
                "codex_invoked": False,
            }
        )
    return state

def _build_dry_run_selected_step_live_execution_operation_state(
    *,
    gate_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    gate = dict(gate_state) if isinstance(gate_state, Mapping) else {}
    selected_step_id = _as_non_negative_int(gate.get("selected_step_id"), default=1)
    if selected_step_id <= 0:
        selected_step_id = 1
    selected_step_name = _normalize_text(
        gate.get("selected_step_name"),
        default="read_current_state",
    )
    selected_step_operation = _normalize_text(
        gate.get("selected_step_operation"),
        default=selected_step_name or "read_current_state",
    )
    return {
        "status": "blocked",
        "blocked_reason": _normalize_text(
            gate.get("blocked_reason"),
            default="selected_step_live_execution_dry_run_bypassed",
        ),
        "live_execution_performed": False,
        "execution_performed": False,
        "read_current_state_completed": False,
        "selected_step_id": selected_step_id,
        "selected_step_name": selected_step_name or "read_current_state",
        "selected_step_operation": selected_step_operation or "read_current_state",
        "current_branch": _normalize_text(gate.get("current_branch"), default=""),
        "head_short": _normalize_text(gate.get("head_short"), default=""),
        "head_tags": _normalize_string_list(gate.get("head_tags")),
        "worktree_clean": bool(gate.get("worktree_clean", False)),
        "changed_tracked_files": _normalize_string_list(
            gate.get("changed_tracked_files")
        ),
        "artifact_status_summary": {},
        "next_action": _normalize_text(
            gate.get("next_action"),
            default="prepare_selected_step_execution_result_route",
        ),
    }

def _build_selected_step_execution_result_route_decision_state(
    *,
    capture_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    capture = dict(capture_state) if isinstance(capture_state, Mapping) else {}
    state = dict(capture)

    changed_tracked_files = _normalize_string_list(capture.get("changed_tracked_files"))
    required_artifacts_present = bool(capture.get("required_artifacts_present", False))
    required_artifacts_valid = bool(capture.get("required_artifacts_valid", False))
    result_status = _normalize_text(capture.get("result_status"), default="missing")
    final_result = _normalize_text(capture.get("final_result"), default="unknown")

    status = "blocked"
    route_status = "blocked"
    blocked_reason = "selected_step_result_not_routable"
    route_decision = "blocked"
    should_continue = False
    next_action = "manual_review_selected_step_result"
    selected_step_result = _normalize_text(
        capture.get("selected_step_result"),
        default=final_result or "unknown",
    )
    if not selected_step_result:
        selected_step_result = "unknown"

    if changed_tracked_files:
        blocked_reason = "tracked_changes_present_before_selected_step_result_route"
        next_action = "commit_or_reconcile_tracked_changes_before_selected_step_result_route"
    elif (not required_artifacts_present) or (not required_artifacts_valid):
        blocked_reason = "selected_step_live_execution_artifacts_missing_or_invalid"
        next_action = "rerun_prompt328_live_execution_clean_verify"
    elif result_status != "completed":
        blocked_reason = "selected_step_live_execution_not_completed"
        next_action = "complete_selected_step_live_execution_before_route"
    elif final_result == "read_current_state_completed":
        status = "ready"
        route_status = "ready"
        blocked_reason = "none"
        route_decision = "continue_to_next_selected_step"
        should_continue = True
        next_action = "prepare_next_selected_step_or_prompt330_loop_closure"
        selected_step_result = "read_current_state_completed"
    elif final_result in {"blocked", "not_run", "unknown", ""}:
        blocked_reason = "selected_step_result_not_routable"
        next_action = "manual_review_selected_step_result"
    else:
        blocked_reason = "selected_step_result_not_routable"
        next_action = "manual_review_selected_step_result"

    state.update(
        {
            "status": status,
            "route_status": route_status,
            "blocked_reason": blocked_reason,
            "next_action": next_action,
            "route_decision": route_decision,
            "should_continue": should_continue,
            "selected_step_result": selected_step_result,
            "source": "selected_step_execution_result_route_decision",
        }
    )
    return state

def _build_local_autonomous_cycle_v2_state(
    *,
    prompt330_closure_state_path: Path,
    prompt330_closure_decision_path: Path,
    prompt330_closure_receipt_path: Path,
    execution_repo_path: str,
    controller_run_id: str,
    controller_job_id: str,
) -> dict[str, Any]:
    current_cycle = _LOCAL_AUTONOMOUS_CYCLE_V2_CURRENT_CYCLE
    max_cycles = _LOCAL_AUTONOMOUS_CYCLE_V2_MAX_CYCLES

    def _read_artifact(path: Path) -> tuple[bool, bool, dict[str, Any]]:
        if not path.exists():
            return False, False, {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            return True, False, {}
        if not isinstance(payload, Mapping):
            return True, False, {}
        return True, True, dict(payload)

    def _extract_bool(value: Any) -> tuple[bool, bool]:
        if isinstance(value, bool):
            return value, True
        if isinstance(value, int):
            return value != 0, True
        text = _normalize_text(value, default="").strip().lower()
        if text in {"1", "true", "yes", "on", "enabled"}:
            return True, True
        if text in {"0", "false", "no", "off", "disabled"}:
            return False, True
        return False, False

    prompt330_state_exists, prompt330_state_valid, prompt330_state = _read_artifact(
        prompt330_closure_state_path
    )
    prompt330_decision_exists, prompt330_decision_valid, prompt330_decision = _read_artifact(
        prompt330_closure_decision_path
    )
    prompt330_receipt_exists, prompt330_receipt_valid, prompt330_receipt = _read_artifact(
        prompt330_closure_receipt_path
    )

    run_id_candidates = [
        controller_run_id,
        _normalize_text(prompt330_decision.get("run_id"), default=""),
        _normalize_text(prompt330_state.get("run_id"), default=""),
        _normalize_text(prompt330_receipt.get("run_id"), default=""),
    ]
    job_id_candidates = [
        controller_job_id,
        _normalize_text(prompt330_decision.get("job_id"), default=""),
        _normalize_text(prompt330_state.get("job_id"), default=""),
        _normalize_text(prompt330_receipt.get("job_id"), default=""),
    ]
    resolved_run_id = next((value for value in run_id_candidates if value), "")
    if not resolved_run_id:
        resolved_job_id = next((value for value in job_id_candidates if value), "")
        if resolved_job_id:
            resolved_run_id = resolved_job_id
    if not resolved_run_id:
        resolved_run_id = "local-autonomous-v2"
    cycle_id = f"{resolved_run_id}-cycle-{current_cycle}"

    safety_fields: dict[str, Any] = {
        "codex_invoked": False,
        "codex_invocation_allowed": False,
        "commit_allowed": False,
        "tag_allowed": False,
        "commit_performed": False,
        "tag_performed": False,
        "push_pr_merge_enabled": False,
        "push_performed": False,
        "pr_created": False,
        "merge_performed": False,
        "targeted_fix_allowed": False,
        "rollback_allowed": False,
        "rollback_performed": False,
    }

    validation_errors: list[str] = []
    blocked_reason = "prompt330_closure_status_not_completed"
    readiness_reason = "prompt330_closure_not_valid_for_local_autonomous_cycle_v2"
    changed_tracked_files: list[str] = []

    status = "blocked"
    cycle_status = "blocked"
    v2_cycle_ready = False
    selected_step_id: int | None = None
    selected_step_name: str | None = None
    selected_step_operation: str | None = None
    cycle_decision = "blocked"
    cycle_reason = ""
    should_continue = False
    next_action = "manual_review_prompt330_closure_before_v2_cycle"

    if not prompt330_state_exists:
        blocked_reason = "missing_prompt330_closure_state_artifact"
        validation_errors.append("missing_prompt330_closure_state_artifact")
    elif not prompt330_state_valid:
        blocked_reason = "invalid_prompt330_closure_state_artifact"
        validation_errors.append("invalid_prompt330_closure_state_artifact")
    elif not prompt330_decision_exists:
        blocked_reason = "missing_prompt330_closure_decision_artifact"
        validation_errors.append("missing_prompt330_closure_decision_artifact")
    elif not prompt330_decision_valid:
        blocked_reason = "invalid_prompt330_closure_decision_artifact"
        validation_errors.append("invalid_prompt330_closure_decision_artifact")
    elif not prompt330_receipt_exists:
        blocked_reason = "missing_prompt330_closure_receipt_artifact"
        validation_errors.append("missing_prompt330_closure_receipt_artifact")
    elif not prompt330_receipt_valid:
        blocked_reason = "invalid_prompt330_closure_receipt_artifact"
        validation_errors.append("invalid_prompt330_closure_receipt_artifact")
    else:
        authoritative = prompt330_decision
        supporting_surfaces: tuple[Mapping[str, Any], ...] = (prompt330_state, prompt330_receipt)
        required_fields: tuple[tuple[str, Any], ...] = (
            ("status", "completed"),
            ("closure_status", "completed"),
            ("blocked_reason", "none"),
            ("local_only_v1_complete", True),
            ("local_only_loop_closed", True),
            ("closure_decision", "local_only_v1_closed"),
            ("completed_step_id", 1),
            ("completed_step_name", "read_current_state"),
            ("completed_step_operation", "read_current_state"),
            (
                "next_action",
                "prepare_prompt331_or_enable_next_local_loop_increment",
            ),
        )
        field_to_blocked_reason = {
            "status": "prompt330_closure_status_not_completed",
            "closure_status": "prompt330_closure_status_not_completed",
            "blocked_reason": "prompt330_blocked_reason_not_none",
            "local_only_v1_complete": "prompt330_local_only_v1_not_complete",
            "local_only_loop_closed": "prompt330_local_only_loop_not_closed",
            "closure_decision": "prompt330_closure_decision_mismatch",
            "completed_step_id": "prompt330_completed_step_mismatch",
            "completed_step_name": "prompt330_completed_step_mismatch",
            "completed_step_operation": "prompt330_completed_step_mismatch",
            "next_action": "prompt330_next_action_mismatch",
        }
        first_failure_reason = ""

        for field_name, expected in required_fields:
            if field_name not in authoritative:
                present_in_supporting = any(field_name in surface for surface in supporting_surfaces)
                if present_in_supporting:
                    validation_errors.append(
                        f"prompt330_{field_name}_present_only_in_non_authoritative_artifact"
                    )
                else:
                    validation_errors.append(
                        f"prompt330_{field_name}_missing_in_authoritative_artifact"
                    )
                if not first_failure_reason:
                    first_failure_reason = field_to_blocked_reason.get(
                        field_name,
                        "prompt330_closure_status_not_completed",
                    )
                continue

            raw_value = authoritative.get(field_name)
            if isinstance(expected, bool):
                parsed_value, valid_bool = _extract_bool(raw_value)
                if (not valid_bool) or parsed_value != expected:
                    validation_errors.append(
                        f"prompt330_{field_name}_mismatch_expected_{str(expected).lower()}"
                    )
                    if not first_failure_reason:
                        first_failure_reason = field_to_blocked_reason.get(
                            field_name,
                            "prompt330_closure_status_not_completed",
                        )
            elif isinstance(expected, int):
                parsed_int = _as_optional_int(raw_value)
                if parsed_int != expected:
                    validation_errors.append(
                        f"prompt330_{field_name}_mismatch_expected_{expected}"
                    )
                    if not first_failure_reason:
                        first_failure_reason = field_to_blocked_reason.get(
                            field_name,
                            "prompt330_closure_status_not_completed",
                        )
            else:
                parsed_text = _normalize_text(raw_value, default="")
                if parsed_text != expected:
                    validation_errors.append(
                        f"prompt330_{field_name}_mismatch_expected_{expected}"
                    )
                    if not first_failure_reason:
                        first_failure_reason = field_to_blocked_reason.get(
                            field_name,
                            "prompt330_closure_status_not_completed",
                        )

        if validation_errors:
            blocked_reason = first_failure_reason or "prompt330_closure_status_not_completed"
        else:
            status_short_cmd = subprocess.run(
                ["git", "status", "--short", "--untracked-files=no"],
                text=True,
                capture_output=True,
                check=False,
                cwd=_normalize_text(execution_repo_path, default=_APPROVE_COMMIT_TAG_EXECUTION_REPO_PATH),
                shell=False,
            )
            if status_short_cmd.returncode == 0:
                changed_tracked_files = sorted(
                    {
                        _parse_git_status_path(line)
                        for line in (status_short_cmd.stdout or "").splitlines()
                        if line.strip() and _parse_git_status_path(line)
                    }
                )
            else:
                changed_tracked_files = []

            if status_short_cmd.returncode != 0:
                blocked_reason = "git_metadata_collection_failed_before_local_autonomous_cycle_v2"
                readiness_reason = "worktree_not_clean_before_local_autonomous_cycle_v2"
                validation_errors = []
                next_action = "review_git_metadata_failure_before_local_autonomous_cycle_v2"
            elif changed_tracked_files:
                blocked_reason = "tracked_changes_present_before_local_autonomous_cycle_v2"
                readiness_reason = "worktree_not_clean_before_local_autonomous_cycle_v2"
                validation_errors = []
                next_action = (
                    "commit_or_reconcile_tracked_changes_before_local_autonomous_cycle_v2"
                )
            else:
                status = "ready"
                cycle_status = "ready"
                blocked_reason = "none"
                readiness_reason = (
                    "prompt330_closure_valid_and_tracked_worktree_clean"
                )
                v2_cycle_ready = True
                selected_step_id = 2
                selected_step_name = "generate_next_codex_task"
                selected_step_operation = "generate_next_codex_task"
                cycle_decision = "continue_local_multi_step"
                cycle_reason = (
                    "local_only_v1_closed_and_next_v2_step_is_codex_task_generation"
                )
                should_continue = True
                next_action = "prepare_local_codex_one_shot_execution_handoff"
                changed_tracked_files = []
                validation_errors = []

    return {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "run_id": resolved_run_id,
        "cycle_id": cycle_id,
        "current_cycle": current_cycle,
        "max_cycles": max_cycles,
        "status": status,
        "cycle_status": cycle_status,
        "blocked_reason": blocked_reason,
        "readiness_reason": readiness_reason,
        "validation_errors": _normalize_string_list(validation_errors),
        "v2_cycle_ready": v2_cycle_ready,
        "selected_step_id": selected_step_id,
        "selected_step_name": selected_step_name,
        "selected_step_operation": selected_step_operation,
        "cycle_decision": cycle_decision,
        "cycle_reason": cycle_reason,
        "should_continue": should_continue,
        "next_action": next_action,
        "changed_tracked_files": _normalize_string_list(changed_tracked_files),
        "prompt330_closure_state_path": str(prompt330_closure_state_path),
        "prompt330_closure_decision_path": str(prompt330_closure_decision_path),
        "prompt330_closure_receipt_path": str(prompt330_closure_receipt_path),
        "source": "local_autonomous_cycle_v2_state",
        **safety_fields,
    }

def _build_local_autonomous_cycle_v2_decision(
    *,
    cycle_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    state = dict(cycle_state) if isinstance(cycle_state, Mapping) else {}
    decision = dict(state)
    decision["source"] = "local_autonomous_cycle_v2_decision"
    return decision

def _build_local_codex_one_shot_execution_handoff_state(
    *,
    prompt331_state_path: Path,
    prompt331_decision_path: Path,
    prompt331_receipt_path: Path,
    execution_repo_path: str,
) -> dict[str, Any]:
    def _read_artifact(path: Path) -> tuple[bool, bool, dict[str, Any]]:
        if not path.exists():
            return False, False, {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            return True, False, {}
        if not isinstance(payload, Mapping):
            return True, False, {}
        return True, True, dict(payload)

    def _extract_bool(value: Any) -> tuple[bool, bool]:
        if isinstance(value, bool):
            return value, True
        if isinstance(value, int):
            return value != 0, True
        text = _normalize_text(value, default="").strip().lower()
        if text in {"1", "true", "yes", "on", "enabled"}:
            return True, True
        if text in {"0", "false", "no", "off", "disabled"}:
            return False, True
        return False, False

    def _as_field_int(value: Any) -> int | None:
        return _as_optional_int(value)

    prompt331_state_exists, prompt331_state_valid, prompt331_state = _read_artifact(
        prompt331_state_path
    )
    prompt331_decision_exists, prompt331_decision_valid, prompt331_decision = _read_artifact(
        prompt331_decision_path
    )
    prompt331_receipt_exists, prompt331_receipt_valid, prompt331_receipt = _read_artifact(
        prompt331_receipt_path
    )

    run_id = _normalize_text(
        prompt331_decision.get("run_id"),
        default=_normalize_text(
            prompt331_state.get("run_id"),
            default=_normalize_text(
                prompt331_receipt.get("run_id"),
                default="local-autonomous-v2",
            ),
        ),
    )
    cycle_id = _normalize_text(
        prompt331_decision.get("cycle_id"),
        default=_normalize_text(
            prompt331_state.get("cycle_id"),
            default=_normalize_text(
                prompt331_receipt.get("cycle_id"),
                default=f"{run_id}-cycle-{_LOCAL_AUTONOMOUS_CYCLE_V2_CURRENT_CYCLE}",
            ),
        ),
    )
    current_cycle = _as_non_negative_int(
        prompt331_decision.get("current_cycle"),
        default=_as_non_negative_int(
            prompt331_state.get("current_cycle"),
            default=_as_non_negative_int(
                prompt331_receipt.get("current_cycle"),
                default=_LOCAL_AUTONOMOUS_CYCLE_V2_CURRENT_CYCLE,
            ),
        ),
    )
    max_cycles = _as_non_negative_int(
        prompt331_decision.get("max_cycles"),
        default=_as_non_negative_int(
            prompt331_state.get("max_cycles"),
            default=_as_non_negative_int(
                prompt331_receipt.get("max_cycles"),
                default=_LOCAL_AUTONOMOUS_CYCLE_V2_MAX_CYCLES,
            ),
        ),
    )
    if current_cycle <= 0:
        current_cycle = _LOCAL_AUTONOMOUS_CYCLE_V2_CURRENT_CYCLE
    if max_cycles <= 0:
        max_cycles = _LOCAL_AUTONOMOUS_CYCLE_V2_MAX_CYCLES
    allowed_tracked_file = "automation/orchestration/planned_execution_runner.py"
    explicit_allowed_tracked_files: list[str] = []
    mutation_allowed = False
    selected_step_authority_source = "prompt331_v2_local_autonomous_cycle_v2_decision"
    selected_step_authority_artifact = str(prompt331_decision_path)
    selected_step_authority_status = "blocked"
    stale_step_selection_artifact_path = _LOCAL_END_TO_END_ONE_SHOT_STEP_SELECTION_PATH
    stale_step_selection_status = "missing"
    stale_step_selection_conflict_detected = False
    contract_fix_applied = True

    stale_step_selection_exists, stale_step_selection_valid, stale_step_selection_payload = (
        _read_artifact(Path(stale_step_selection_artifact_path))
    )
    if stale_step_selection_exists and stale_step_selection_valid:
        stale_step_selection_status = _normalize_text(
            stale_step_selection_payload.get("status"),
            default="invalid",
        )
    elif stale_step_selection_exists:
        stale_step_selection_status = "invalid"

    safety_fields: dict[str, Any] = {
        "codex_invoked": False,
        "codex_invocation_allowed": False,
        "codex_invocation_count": 0,
        "commit_allowed": False,
        "tag_allowed": False,
        "commit_performed": False,
        "tag_performed": False,
        "push_pr_merge_enabled": False,
        "push_performed": False,
        "pr_created": False,
        "merge_performed": False,
        "targeted_fix_allowed": False,
        "rollback_allowed": False,
        "rollback_performed": False,
    }
    required_bool_false_fields = (
        "commit_allowed",
        "tag_allowed",
        "push_pr_merge_enabled",
        "targeted_fix_allowed",
        "rollback_allowed",
    )
    required_fields: tuple[tuple[str, Any], ...] = (
        ("schema_version", _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION),
        ("status", "ready"),
        ("cycle_status", "ready"),
        ("blocked_reason", "none"),
        ("readiness_reason", "prompt330_closure_valid_and_tracked_worktree_clean"),
        ("v2_cycle_ready", True),
        ("current_cycle", _LOCAL_AUTONOMOUS_CYCLE_V2_CURRENT_CYCLE),
        ("max_cycles", _LOCAL_AUTONOMOUS_CYCLE_V2_MAX_CYCLES),
        ("selected_step_id", 2),
        ("selected_step_name", "generate_next_codex_task"),
        ("selected_step_operation", "generate_next_codex_task"),
        ("cycle_decision", "continue_local_multi_step"),
        ("should_continue", True),
        ("next_action", "prepare_local_codex_one_shot_execution_handoff"),
        ("codex_invocation_allowed", False),
        ("commit_allowed", False),
        ("tag_allowed", False),
        ("push_pr_merge_enabled", False),
        ("targeted_fix_allowed", False),
        ("rollback_allowed", False),
        ("changed_tracked_files", []),
        ("validation_errors", []),
    )
    field_to_blocked_reason: dict[str, str] = {
        "schema_version": "local_autonomous_cycle_v2_schema_version_mismatch",
        "status": "local_autonomous_cycle_v2_status_not_ready",
        "cycle_status": "local_autonomous_cycle_v2_cycle_status_not_ready",
        "blocked_reason": "local_autonomous_cycle_v2_blocked_reason_not_none",
        "readiness_reason": "local_autonomous_cycle_v2_readiness_reason_mismatch",
        "v2_cycle_ready": "local_autonomous_cycle_v2_ready_not_true",
        "current_cycle": "local_autonomous_cycle_v2_cycle_index_mismatch",
        "max_cycles": "local_autonomous_cycle_v2_cycle_index_mismatch",
        "selected_step_id": "local_autonomous_cycle_v2_selected_step_mismatch",
        "selected_step_name": "local_autonomous_cycle_v2_selected_step_mismatch",
        "selected_step_operation": "local_autonomous_cycle_v2_selected_step_mismatch",
        "cycle_decision": "local_autonomous_cycle_v2_cycle_decision_mismatch",
        "should_continue": "local_autonomous_cycle_v2_should_continue_not_true",
        "next_action": "local_autonomous_cycle_v2_next_action_mismatch",
        "codex_invocation_allowed": "local_autonomous_cycle_v2_safety_flag_mismatch",
        "commit_allowed": "local_autonomous_cycle_v2_safety_flag_mismatch",
        "tag_allowed": "local_autonomous_cycle_v2_safety_flag_mismatch",
        "push_pr_merge_enabled": "local_autonomous_cycle_v2_safety_flag_mismatch",
        "targeted_fix_allowed": "local_autonomous_cycle_v2_safety_flag_mismatch",
        "rollback_allowed": "local_autonomous_cycle_v2_safety_flag_mismatch",
        "changed_tracked_files": "local_autonomous_cycle_v2_changed_tracked_files_not_empty",
        "validation_errors": "local_autonomous_cycle_v2_validation_errors_not_empty",
    }

    validation_errors: list[str] = []
    status = "blocked"
    handoff_status = "blocked"
    blocked_reason = "missing_local_autonomous_cycle_v2_state_artifact"
    readiness_reason = "local_autonomous_cycle_v2_not_valid_for_codex_one_shot_handoff"
    codex_prompt_ready = False
    codex_execution_command_ready = False
    codex_invocation_allowed = False
    execution_allowed = False
    max_codex_invocations = 1
    codex_invocation_count = 0
    selected_step_id: int | None = None
    selected_step_name: str | None = None
    selected_step_operation: str | None = None
    next_action = "manual_review_local_autonomous_cycle_v2_before_codex_handoff"
    should_continue = False
    changed_tracked_files: list[str] = []
    prompt_path: str | None = None
    command_argv: list[str] = []
    command_display = ""
    prompt_exists = False
    prompt_non_empty = False

    if not prompt331_state_exists:
        blocked_reason = "missing_local_autonomous_cycle_v2_state_artifact"
        validation_errors.append("missing_local_autonomous_cycle_v2_state_artifact")
    elif not prompt331_state_valid:
        blocked_reason = "invalid_local_autonomous_cycle_v2_state_artifact"
        validation_errors.append("invalid_local_autonomous_cycle_v2_state_artifact")
    elif not prompt331_decision_exists:
        blocked_reason = "missing_local_autonomous_cycle_v2_decision_artifact"
        validation_errors.append("missing_local_autonomous_cycle_v2_decision_artifact")
    elif not prompt331_decision_valid:
        blocked_reason = "invalid_local_autonomous_cycle_v2_decision_artifact"
        validation_errors.append("invalid_local_autonomous_cycle_v2_decision_artifact")
    elif not prompt331_receipt_exists:
        blocked_reason = "missing_local_autonomous_cycle_v2_receipt_artifact"
        validation_errors.append("missing_local_autonomous_cycle_v2_receipt_artifact")
    elif not prompt331_receipt_valid:
        blocked_reason = "invalid_local_autonomous_cycle_v2_receipt_artifact"
        validation_errors.append("invalid_local_autonomous_cycle_v2_receipt_artifact")
    else:
        authoritative = prompt331_decision
        supporting_surfaces: tuple[tuple[str, Mapping[str, Any]], ...] = (
            ("state", prompt331_state),
            ("receipt", prompt331_receipt),
        )
        first_failure_reason = ""
        for field_name, expected in required_fields:
            if field_name not in authoritative:
                present_in_supporting = any(
                    field_name in surface for _, surface in supporting_surfaces
                )
                if present_in_supporting:
                    validation_errors.append(
                        f"local_autonomous_cycle_v2_{field_name}_present_only_in_non_authoritative_artifact"
                    )
                else:
                    validation_errors.append(
                        f"local_autonomous_cycle_v2_{field_name}_missing_in_authoritative_artifact"
                    )
                if not first_failure_reason:
                    first_failure_reason = field_to_blocked_reason.get(
                        field_name,
                        "local_autonomous_cycle_v2_not_valid_for_codex_one_shot_handoff",
                    )
                continue

            decision_value = authoritative.get(field_name)
            mismatch = False
            if isinstance(expected, bool):
                parsed, valid = _extract_bool(decision_value)
                mismatch = (not valid) or (parsed != expected)
            elif isinstance(expected, int):
                mismatch = _as_field_int(decision_value) != expected
            elif isinstance(expected, list):
                mismatch = _normalize_string_list(decision_value) != expected
            else:
                mismatch = _normalize_text(decision_value, default="") != expected
            if mismatch:
                validation_errors.append(
                    f"local_autonomous_cycle_v2_{field_name}_mismatch_expected_{expected}"
                )
                if not first_failure_reason:
                    first_failure_reason = field_to_blocked_reason.get(
                        field_name,
                        "local_autonomous_cycle_v2_not_valid_for_codex_one_shot_handoff",
                    )

            for surface_name, surface in supporting_surfaces:
                if field_name not in surface:
                    continue
                support_value = surface.get(field_name)
                support_mismatch = False
                if isinstance(expected, bool):
                    parsed, valid = _extract_bool(support_value)
                    support_mismatch = (not valid) or (parsed != expected)
                elif isinstance(expected, int):
                    support_mismatch = _as_field_int(support_value) != expected
                elif isinstance(expected, list):
                    support_mismatch = _normalize_string_list(support_value) != expected
                else:
                    support_mismatch = _normalize_text(support_value, default="") != expected
                if support_mismatch:
                    validation_errors.append(
                        "local_autonomous_cycle_v2_"
                        f"{field_name}_mismatch_in_supporting_{surface_name}_artifact"
                    )
                    if not first_failure_reason:
                        first_failure_reason = field_to_blocked_reason.get(
                            field_name,
                            "local_autonomous_cycle_v2_not_valid_for_codex_one_shot_handoff",
                        )

        if validation_errors:
            blocked_reason = (
                first_failure_reason
                or "local_autonomous_cycle_v2_not_valid_for_codex_one_shot_handoff"
            )
        else:
            try:
                status_short_cmd = _run_git(
                    _normalize_text(
                        execution_repo_path,
                        default=_APPROVE_COMMIT_TAG_EXECUTION_REPO_PATH,
                    ),
                    ["status", "--short", "--untracked-files=no"],
                    timeout_seconds=10,
                )
            except (OSError, subprocess.TimeoutExpired):
                status_short_cmd = subprocess.CompletedProcess(
                    args=["git", "status", "--short", "--untracked-files=no"],
                    returncode=1,
                    stdout="",
                    stderr="",
                )
            if status_short_cmd.returncode != 0:
                blocked_reason = (
                    "git_metadata_collection_failed_before_local_codex_one_shot_handoff"
                )
                readiness_reason = "worktree_not_clean_before_local_codex_one_shot_handoff"
                validation_errors = []
                next_action = (
                    "review_git_metadata_failure_before_local_codex_one_shot_handoff"
                )
            else:
                changed_tracked_files = sorted(
                    {
                        _parse_git_status_path(line)
                        for line in (status_short_cmd.stdout or "").splitlines()
                        if line.strip() and _parse_git_status_path(line)
                    }
                )
                if changed_tracked_files:
                    blocked_reason = (
                        "tracked_changes_present_before_local_codex_one_shot_handoff"
                    )
                    readiness_reason = "worktree_not_clean_before_local_codex_one_shot_handoff"
                    validation_errors = []
                    next_action = (
                        "commit_or_reconcile_tracked_changes_before_local_codex_one_shot_handoff"
                    )
                else:
                    status = "ready"
                    handoff_status = "ready"
                    blocked_reason = "none"
                    readiness_reason = (
                        "local_autonomous_cycle_v2_ready_and_tracked_worktree_clean"
                    )
                    codex_prompt_ready = True
                    codex_execution_command_ready = True
                    codex_invocation_allowed = True
                    execution_allowed = True
                    selected_step_id = 2
                    selected_step_name = "generate_next_codex_task"
                    selected_step_operation = "generate_next_codex_task"
                    selected_step_authority_status = "ready"
                    next_action = "execute_local_codex_one_shot_adapter"
                    should_continue = True
                    changed_tracked_files = []
                    validation_errors = []
                    explicit_allowed_tracked_files = [allowed_tracked_file]
                    mutation_allowed = True
                    stale_selected_step_id = _as_optional_int(
                        stale_step_selection_payload.get("selected_step_id")
                    )
                    stale_selected_step_name = _normalize_text(
                        stale_step_selection_payload.get("selected_step_name"),
                        default="",
                    )
                    stale_selected_step_operation = _normalize_text(
                        stale_step_selection_payload.get("selected_step_operation"),
                        default="",
                    )
                    stale_step_selection_conflict_detected = bool(
                        stale_step_selection_status == "blocked"
                        and (
                            stale_selected_step_id not in {None, 2}
                            or (
                                stale_selected_step_name
                                and stale_selected_step_name != "generate_next_codex_task"
                            )
                            or (
                                stale_selected_step_operation
                                and stale_selected_step_operation != "generate_next_codex_task"
                            )
                        )
                    )
                    prompt_path = _LOCAL_CODEX_ONE_SHOT_PROMPT_PATH
                    command_argv = list(_LOCAL_CODEX_ONE_SHOT_EXECUTION_COMMAND)
                    command_display = " ".join(_LOCAL_CODEX_ONE_SHOT_EXECUTION_COMMAND)
                    prompt_exists = False
                    prompt_non_empty = False

    state_payload: dict[str, Any] = {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "handoff_schema_version": _LOCAL_CODEX_ONE_SHOT_HANDOFF_SCHEMA_VERSION,
        "run_id": run_id,
        "cycle_id": cycle_id,
        "current_cycle": current_cycle,
        "max_cycles": max_cycles,
        "source_prompt": "prompt332",
        "source_step_id": 2,
        "source_step_name": "generate_next_codex_task",
        "source_step_operation": "generate_next_codex_task",
        "status": status,
        "handoff_status": handoff_status,
        "blocked_reason": blocked_reason,
        "readiness_reason": readiness_reason,
        "validation_errors": _normalize_string_list(validation_errors),
        "selected_step_id": selected_step_id,
        "selected_step_name": selected_step_name,
        "selected_step_operation": selected_step_operation,
        "selected_step_authority_source": selected_step_authority_source,
        "selected_step_authority_artifact": selected_step_authority_artifact,
        "selected_step_authority_status": selected_step_authority_status,
        "explicit_allowed_tracked_files": _normalize_string_list(explicit_allowed_tracked_files),
        "mutation_allowed": mutation_allowed,
        "stale_step_selection_conflict_detected": stale_step_selection_conflict_detected,
        "stale_step_selection_artifact_path": stale_step_selection_artifact_path,
        "stale_step_selection_status": stale_step_selection_status,
        "contract_fix_applied": contract_fix_applied,
        "prompt_path": prompt_path,
        "prompt_exists": prompt_exists,
        "prompt_non_empty": prompt_non_empty,
        "command_argv": list(command_argv),
        "command_display": command_display,
        "cwd": "/home/rai/codex-local-runner",
        "sandbox": "workspace-write",
        "approval_policy": "never",
        "model": "gpt-5.3-codex",
        "model_reasoning_effort": "high",
        "max_codex_invocations": max_codex_invocations,
        "codex_invocation_count": codex_invocation_count,
        "codex_prompt_ready": codex_prompt_ready,
        "codex_execution_command_ready": codex_execution_command_ready,
        "execution_allowed": execution_allowed,
        "next_action": next_action,
        "should_continue": should_continue,
        "changed_tracked_files": _normalize_string_list(changed_tracked_files),
        "prompt331_state_path": str(prompt331_state_path),
        "prompt331_decision_path": str(prompt331_decision_path),
        "prompt331_receipt_path": str(prompt331_receipt_path),
        **safety_fields,
    }
    if not bool(state_payload.get("codex_prompt_ready", False)):
        state_payload["prompt_path"] = None
        state_payload["command_argv"] = []
        state_payload["command_display"] = ""
        state_payload["selected_step_id"] = None
        state_payload["selected_step_name"] = None
        state_payload["selected_step_operation"] = None
        state_payload["should_continue"] = False
        state_payload["codex_invocation_allowed"] = False
        state_payload["execution_allowed"] = False
        state_payload["codex_execution_command_ready"] = False
        state_payload["prompt_exists"] = False
        state_payload["prompt_non_empty"] = False

    for safety_field_name in required_bool_false_fields:
        if bool(state_payload.get(safety_field_name, False)):
            state_payload[safety_field_name] = False

    if bool(state_payload.get("status") == "ready"):
        state_payload["codex_invocation_allowed"] = bool(codex_invocation_allowed)
    else:
        state_payload["codex_invocation_allowed"] = False
    return state_payload

def _build_dry_run_local_codex_one_shot_execution_result_state(
    *,
    handoff_state: Mapping[str, Any] | None,
    handoff_receipt_state: Mapping[str, Any] | None,
    prompt_path: Path,
    stdout_path: Path,
    stderr_path: Path,
    result_path: Path,
) -> dict[str, Any]:
    handoff = dict(handoff_state) if isinstance(handoff_state, Mapping) else {}
    receipt = (
        dict(handoff_receipt_state)
        if isinstance(handoff_receipt_state, Mapping)
        else {}
    )
    run_id = _normalize_text(
        handoff.get("run_id"),
        default=_normalize_text(receipt.get("run_id"), default="local-autonomous-v2"),
    )
    cycle_id = _normalize_text(
        handoff.get("cycle_id"),
        default=_normalize_text(
            receipt.get("cycle_id"),
            default="local-autonomous-v2-cycle-1",
        ),
    )
    current_cycle = _as_non_negative_int(
        handoff.get("current_cycle"),
        default=_as_non_negative_int(
            receipt.get("current_cycle"),
            default=_LOCAL_AUTONOMOUS_CYCLE_V2_CURRENT_CYCLE,
        ),
    )
    max_cycles = _as_non_negative_int(
        handoff.get("max_cycles"),
        default=_as_non_negative_int(
            receipt.get("max_cycles"),
            default=_LOCAL_AUTONOMOUS_CYCLE_V2_MAX_CYCLES,
        ),
    )
    selected_step_id = _as_optional_int(
        handoff.get("selected_step_id")
        if "selected_step_id" in handoff
        else receipt.get("selected_step_id")
    )
    selected_step_name = (
        _normalize_text(
            handoff.get("selected_step_name"),
            default=_normalize_text(receipt.get("selected_step_name"), default=""),
        )
        or None
    )
    selected_step_operation = (
        _normalize_text(
            handoff.get("selected_step_operation"),
            default=_normalize_text(
                receipt.get("selected_step_operation"),
                default="",
            ),
        )
        or None
    )
    handoff_ready = bool(
        _normalize_text(handoff.get("status"), default="blocked") == "ready"
        and _normalize_text(handoff.get("handoff_status"), default="blocked") == "ready"
        and bool(handoff.get("codex_prompt_ready", False))
        and bool(handoff.get("codex_execution_command_ready", False))
        and bool(handoff.get("codex_invocation_allowed", False))
        and bool(handoff.get("execution_allowed", False))
    )
    blocked_reason = _normalize_text(
        handoff.get("blocked_reason"),
        default=_normalize_text(
            receipt.get("blocked_reason"),
            default="local_codex_one_shot_handoff_not_valid_for_execution",
        ),
    )
    readiness_reason = _normalize_text(
        handoff.get("readiness_reason"),
        default=_normalize_text(
            receipt.get("readiness_reason"),
            default="local_codex_one_shot_handoff_not_valid_for_execution",
        ),
    )
    next_action = _normalize_text(
        handoff.get("next_action"),
        default=_normalize_text(
            receipt.get("next_action"),
            default="manual_review_local_codex_one_shot_handoff_before_execution",
        ),
    )
    if handoff_ready:
        blocked_reason = _PROMPT365_DRY_RUN_BLOCKED_REASON
        readiness_reason = "dry_run_local_codex_one_shot_execution_bypassed"
        next_action = _PROMPT365_DRY_RUN_BLOCKED_NEXT_ACTION
    prompt_path_text = _normalize_text(
        handoff.get("prompt_path"),
        default=str(prompt_path),
    )
    if not prompt_path_text:
        prompt_path_text = str(prompt_path)
    return {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "execution_schema_version": _LOCAL_CODEX_ONE_SHOT_EXECUTION_SCHEMA_VERSION,
        "source_prompt": "prompt333",
        "source_handoff_schema_version": _LOCAL_CODEX_ONE_SHOT_HANDOFF_SCHEMA_VERSION,
        "run_id": run_id,
        "cycle_id": cycle_id,
        "current_cycle": current_cycle,
        "max_cycles": max_cycles,
        "source_step_id": 2,
        "source_step_name": "generate_next_codex_task",
        "source_step_operation": "generate_next_codex_task",
        "status": "blocked",
        "execution_status": "blocked",
        "blocked_reason": blocked_reason,
        "readiness_reason": readiness_reason,
        "execution_result": "not_run",
        "codex_invoked": False,
        "codex_invocation_allowed": False,
        "execution_allowed": False,
        "execution_attempted": False,
        "execution_completed": False,
        "execution_exit_code": None,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "result_path": str(result_path),
        "selected_step_id": selected_step_id,
        "selected_step_name": selected_step_name,
        "selected_step_operation": selected_step_operation,
        "command_argv": [],
        "prompt_path": prompt_path_text,
        "prompt_exists": prompt_path.exists(),
        "prompt_non_empty": False,
        "max_codex_invocations": 1,
        "codex_invocation_count": 0,
        "changed_tracked_files": [],
        "changed_tracked_files_after_execution": [],
        "validation_errors": _normalize_string_list(
            handoff.get("validation_errors")
            if isinstance(handoff.get("validation_errors"), list)
            else receipt.get("validation_errors")
        ),
        "should_continue": False,
        "next_action": next_action,
        "stdout_chars_total": 0,
        "stderr_chars_total": 0,
        "stdout_chars_written": 0,
        "stderr_chars_written": 0,
        "stdout_truncated": False,
        "stderr_truncated": False,
        "output_max_chars": _LOCAL_CODEX_ONE_SHOT_EXECUTION_OUTPUT_MAX_CHARS,
        "commit_allowed": False,
        "tag_allowed": False,
        "commit_performed": False,
        "tag_performed": False,
        "push_pr_merge_enabled": False,
        "push_performed": False,
        "pr_created": False,
        "merge_performed": False,
        "targeted_fix_allowed": False,
        "rollback_allowed": False,
        "rollback_performed": False,
    }

def _build_local_codex_one_shot_execution_result_state(
    *,
    execution_repo_path: str,
    handoff_path: Path,
    handoff_receipt_path: Path,
    prompt_path: Path,
    stdout_path: Path,
    stderr_path: Path,
    result_path: Path,
) -> dict[str, Any]:
    def _read_artifact(path: Path) -> tuple[bool, bool, dict[str, Any]]:
        if not path.exists():
            return False, False, {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return True, False, {}
        if not isinstance(payload, Mapping):
            return True, False, {}
        return True, True, dict(payload)

    def _extract_bool(value: Any) -> tuple[bool, bool]:
        if isinstance(value, bool):
            return value, True
        if isinstance(value, int):
            return value != 0, True
        text = _normalize_text(value, default="").strip().lower()
        if text in {"1", "true", "yes", "on", "enabled"}:
            return True, True
        if text in {"0", "false", "no", "off", "disabled"}:
            return False, True
        return False, False

    def _as_field_int(value: Any) -> int | None:
        return _as_optional_int(value)

    def _bounded_output(text: str, *, max_chars: int) -> tuple[str, bool, int]:
        normalized = _normalize_text(text, default="")
        total_chars = len(normalized)
        if total_chars <= max_chars:
            return normalized, False, total_chars
        return normalized[:max_chars], True, total_chars

    def _command_argv_length(value: Any) -> int | None:
        if isinstance(value, (list, tuple)):
            return len(value)
        return None

    handoff_exists, handoff_valid, handoff_payload = _read_artifact(handoff_path)
    receipt_exists, receipt_valid, receipt_payload = _read_artifact(handoff_receipt_path)
    prompt_artifact_exists = prompt_path.exists()
    expected_command_argv = list(_LOCAL_CODEX_ONE_SHOT_EXECUTION_COMMAND)
    authoritative_handoff_command_argv = (
        handoff_payload.get("command_argv") if handoff_valid else None
    )
    supporting_receipt_command_argv = (
        receipt_payload.get("command_argv") if receipt_valid else None
    )
    authoritative_handoff_command_argv_equal_expected = (
        isinstance(authoritative_handoff_command_argv, (list, tuple))
        and list(authoritative_handoff_command_argv) == expected_command_argv
    )
    supporting_receipt_command_argv_equal_expected: bool | None = None
    if isinstance(supporting_receipt_command_argv, (list, tuple)):
        if supporting_receipt_command_argv:
            supporting_receipt_command_argv_equal_expected = (
                list(supporting_receipt_command_argv) == expected_command_argv
            )

    command_argv_validation_mode = (
        "authoritative_handoff_strict_supporting_receipt_optional"
    )
    command_argv_mismatch_source = "none"
    command_argv_diagnostics: dict[str, Any] = {
        "expected_command_argv": list(expected_command_argv),
        "expected_command_argv_type": type(expected_command_argv).__name__,
        "expected_command_argv_length": _command_argv_length(expected_command_argv),
        "authoritative_handoff_command_argv": authoritative_handoff_command_argv,
        "authoritative_handoff_command_argv_type": type(
            authoritative_handoff_command_argv
        ).__name__,
        "authoritative_handoff_command_argv_length": _command_argv_length(
            authoritative_handoff_command_argv
        ),
        "supporting_receipt_command_argv": supporting_receipt_command_argv,
        "supporting_receipt_command_argv_type": type(
            supporting_receipt_command_argv
        ).__name__,
        "supporting_receipt_command_argv_length": _command_argv_length(
            supporting_receipt_command_argv
        ),
        "authoritative_handoff_command_argv_equal_expected": (
            authoritative_handoff_command_argv_equal_expected
        ),
        "supporting_receipt_command_argv_equal_expected": (
            supporting_receipt_command_argv_equal_expected
        ),
        "command_argv_mismatch_source": command_argv_mismatch_source,
        "command_argv_validation_mode": command_argv_validation_mode,
    }

    run_id = _normalize_text(
        handoff_payload.get("run_id"),
        default=_normalize_text(receipt_payload.get("run_id"), default="local-autonomous-v2"),
    )
    cycle_id = _normalize_text(
        handoff_payload.get("cycle_id"),
        default=_normalize_text(receipt_payload.get("cycle_id"), default="local-autonomous-v2-cycle-1"),
    )
    current_cycle = _as_non_negative_int(
        handoff_payload.get("current_cycle"),
        default=_as_non_negative_int(
            receipt_payload.get("current_cycle"),
            default=_LOCAL_AUTONOMOUS_CYCLE_V2_CURRENT_CYCLE,
        ),
    )
    max_cycles = _as_non_negative_int(
        handoff_payload.get("max_cycles"),
        default=_as_non_negative_int(
            receipt_payload.get("max_cycles"),
            default=_LOCAL_AUTONOMOUS_CYCLE_V2_MAX_CYCLES,
        ),
    )
    if current_cycle <= 0:
        current_cycle = _LOCAL_AUTONOMOUS_CYCLE_V2_CURRENT_CYCLE
    if max_cycles <= 0:
        max_cycles = _LOCAL_AUTONOMOUS_CYCLE_V2_MAX_CYCLES

    default_blocked_state: dict[str, Any] = {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "execution_schema_version": _LOCAL_CODEX_ONE_SHOT_EXECUTION_SCHEMA_VERSION,
        "source_prompt": "prompt333",
        "source_handoff_schema_version": _LOCAL_CODEX_ONE_SHOT_HANDOFF_SCHEMA_VERSION,
        "run_id": run_id,
        "cycle_id": cycle_id,
        "current_cycle": _LOCAL_AUTONOMOUS_CYCLE_V2_CURRENT_CYCLE,
        "max_cycles": _LOCAL_AUTONOMOUS_CYCLE_V2_MAX_CYCLES,
        "source_step_id": 2,
        "source_step_name": "generate_next_codex_task",
        "source_step_operation": "generate_next_codex_task",
        "status": "blocked",
        "execution_status": "blocked",
        "blocked_reason": "local_codex_one_shot_handoff_not_valid_for_execution",
        "readiness_reason": "local_codex_one_shot_handoff_not_valid_for_execution",
        "execution_result": "codex_one_shot_not_executed",
        "codex_invoked": False,
        "codex_invocation_allowed": False,
        "execution_allowed": False,
        "execution_attempted": False,
        "execution_completed": False,
        "execution_exit_code": None,
        "stdout_path": None,
        "stderr_path": None,
        "result_path": None,
        "selected_step_id": None,
        "selected_step_name": None,
        "selected_step_operation": None,
        "command_argv": [],
        "prompt_path": None,
        "prompt_exists": False,
        "prompt_non_empty": False,
        "max_codex_invocations": 1,
        "codex_invocation_count": 0,
        "changed_tracked_files": [],
        "changed_tracked_files_after_execution": [],
        "validation_errors": [],
        "should_continue": False,
        "next_action": "manual_review_local_codex_one_shot_handoff_before_execution",
        "stdout_chars_total": 0,
        "stderr_chars_total": 0,
        "stdout_chars_written": 0,
        "stderr_chars_written": 0,
        "stdout_truncated": False,
        "stderr_truncated": False,
        "output_max_chars": _LOCAL_CODEX_ONE_SHOT_EXECUTION_OUTPUT_MAX_CHARS,
        "commit_allowed": False,
        "tag_allowed": False,
        "commit_performed": False,
        "tag_performed": False,
        "push_pr_merge_enabled": False,
        "push_performed": False,
        "pr_created": False,
        "merge_performed": False,
        "targeted_fix_allowed": False,
        "rollback_allowed": False,
        "rollback_performed": False,
        **command_argv_diagnostics,
    }

    def _blocked_state(
        *,
        blocked_reason: str,
        validation_errors: list[str],
        changed_tracked_files: list[str] | None = None,
        readiness_reason: str = "local_codex_one_shot_handoff_not_valid_for_execution",
        next_action: str = "manual_review_local_codex_one_shot_handoff_before_execution",
    ) -> dict[str, Any]:
        state = dict(default_blocked_state)
        state.update(command_argv_diagnostics)
        state["blocked_reason"] = blocked_reason
        state["readiness_reason"] = readiness_reason
        state["validation_errors"] = _normalize_string_list(validation_errors)
        state["changed_tracked_files"] = _normalize_string_list(changed_tracked_files)
        state["next_action"] = next_action
        return state

    if not handoff_exists:
        return _blocked_state(
            blocked_reason="missing_local_codex_one_shot_execution_handoff_artifact",
            validation_errors=["missing_local_codex_one_shot_execution_handoff_artifact"],
        )
    if not handoff_valid:
        return _blocked_state(
            blocked_reason="invalid_local_codex_one_shot_execution_handoff_artifact",
            validation_errors=["invalid_local_codex_one_shot_execution_handoff_artifact"],
        )
    if not receipt_exists:
        return _blocked_state(
            blocked_reason="missing_local_codex_one_shot_execution_receipt_artifact",
            validation_errors=["missing_local_codex_one_shot_execution_receipt_artifact"],
        )
    if not receipt_valid:
        return _blocked_state(
            blocked_reason="invalid_local_codex_one_shot_execution_receipt_artifact",
            validation_errors=["invalid_local_codex_one_shot_execution_receipt_artifact"],
        )
    if not prompt_artifact_exists:
        return _blocked_state(
            blocked_reason="missing_local_codex_one_shot_prompt_artifact",
            validation_errors=["missing_local_codex_one_shot_prompt_artifact"],
        )

    required_fields: tuple[tuple[str, Any], ...] = (
        ("schema_version", _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION),
        ("handoff_schema_version", _LOCAL_CODEX_ONE_SHOT_HANDOFF_SCHEMA_VERSION),
        ("status", "ready"),
        ("handoff_status", "ready"),
        ("blocked_reason", "none"),
        ("readiness_reason", "local_autonomous_cycle_v2_ready_and_tracked_worktree_clean"),
        ("codex_prompt_ready", True),
        ("codex_execution_command_ready", True),
        ("codex_invocation_allowed", True),
        ("execution_allowed", True),
        ("max_codex_invocations", 1),
        ("codex_invocation_count", 0),
        ("selected_step_id", 2),
        ("selected_step_name", "generate_next_codex_task"),
        ("selected_step_operation", "generate_next_codex_task"),
        ("prompt_exists", True),
        ("prompt_non_empty", True),
        ("next_action", "execute_local_codex_one_shot_adapter"),
        ("commit_allowed", False),
        ("tag_allowed", False),
        ("push_pr_merge_enabled", False),
        ("targeted_fix_allowed", False),
        ("rollback_allowed", False),
        ("changed_tracked_files", []),
        ("validation_errors", []),
    )
    field_to_blocked_reason: dict[str, str] = {
        "schema_version": "local_codex_one_shot_handoff_schema_version_mismatch",
        "handoff_schema_version": "local_codex_one_shot_handoff_schema_version_mismatch",
        "status": "local_codex_one_shot_handoff_status_not_ready",
        "handoff_status": "local_codex_one_shot_handoff_handoff_status_not_ready",
        "blocked_reason": "local_codex_one_shot_handoff_blocked_reason_not_none",
        "readiness_reason": "local_codex_one_shot_handoff_readiness_reason_mismatch",
        "codex_prompt_ready": "local_codex_one_shot_handoff_prompt_not_ready",
        "codex_execution_command_ready": "local_codex_one_shot_handoff_command_not_ready",
        "codex_invocation_allowed": "local_codex_one_shot_handoff_invocation_not_allowed",
        "execution_allowed": "local_codex_one_shot_handoff_execution_not_allowed",
        "max_codex_invocations": "local_codex_one_shot_handoff_max_codex_invocations_not_one",
        "codex_invocation_count": "local_codex_one_shot_handoff_invocation_count_not_zero",
        "selected_step_id": "local_codex_one_shot_handoff_selected_step_mismatch",
        "selected_step_name": "local_codex_one_shot_handoff_selected_step_mismatch",
        "selected_step_operation": "local_codex_one_shot_handoff_selected_step_mismatch",
        "prompt_exists": "local_codex_one_shot_handoff_prompt_not_ready",
        "prompt_non_empty": "local_codex_one_shot_handoff_prompt_not_ready",
        "command_argv": "local_codex_one_shot_handoff_command_argv_mismatch",
        "next_action": "local_codex_one_shot_handoff_next_action_mismatch",
        "commit_allowed": "local_codex_one_shot_handoff_safety_flag_mismatch",
        "tag_allowed": "local_codex_one_shot_handoff_safety_flag_mismatch",
        "push_pr_merge_enabled": "local_codex_one_shot_handoff_safety_flag_mismatch",
        "targeted_fix_allowed": "local_codex_one_shot_handoff_safety_flag_mismatch",
        "rollback_allowed": "local_codex_one_shot_handoff_safety_flag_mismatch",
        "changed_tracked_files": "local_codex_one_shot_handoff_changed_tracked_files_not_empty",
        "validation_errors": "local_codex_one_shot_handoff_validation_errors_not_empty",
        "prompt_path": "local_codex_one_shot_handoff_prompt_not_ready",
    }

    validation_errors: list[str] = []
    first_failure_reason = ""
    authoritative = handoff_payload
    supporting_surfaces: tuple[tuple[str, Mapping[str, Any]], ...] = (
        ("receipt", receipt_payload),
    )

    if "prompt_path" not in authoritative:
        if any("prompt_path" in surface for _, surface in supporting_surfaces):
            validation_errors.append(
                "local_codex_one_shot_handoff_prompt_path_present_only_in_non_authoritative_artifact"
            )
        else:
            validation_errors.append(
                "local_codex_one_shot_handoff_prompt_path_missing_in_authoritative_artifact"
            )
        first_failure_reason = "local_codex_one_shot_handoff_prompt_not_ready"
    elif not _normalize_text(authoritative.get("prompt_path"), default=""):
        validation_errors.append("local_codex_one_shot_handoff_prompt_path_empty")
        first_failure_reason = "local_codex_one_shot_handoff_prompt_not_ready"
    else:
        authoritative_prompt_path = _normalize_text(
            authoritative.get("prompt_path"),
            default="",
        )
        for surface_name, surface in supporting_surfaces:
            if "prompt_path" not in surface:
                continue
            supporting_prompt_path = _normalize_text(surface.get("prompt_path"), default="")
            if (not supporting_prompt_path) or (supporting_prompt_path != authoritative_prompt_path):
                validation_errors.append(
                    "local_codex_one_shot_handoff_prompt_path_"
                    f"mismatch_in_supporting_{surface_name}_artifact"
                )
                if not first_failure_reason:
                    first_failure_reason = "local_codex_one_shot_handoff_prompt_not_ready"

    for field_name, expected in required_fields:
        if field_name not in authoritative:
            present_in_supporting = any(
                field_name in surface for _, surface in supporting_surfaces
            )
            if present_in_supporting:
                validation_errors.append(
                    f"local_codex_one_shot_handoff_{field_name}_present_only_in_non_authoritative_artifact"
                )
            else:
                validation_errors.append(
                    f"local_codex_one_shot_handoff_{field_name}_missing_in_authoritative_artifact"
                )
            if not first_failure_reason:
                first_failure_reason = field_to_blocked_reason.get(
                    field_name,
                    "local_codex_one_shot_handoff_not_valid_for_execution",
                )
            continue

        authoritative_value = authoritative.get(field_name)
        mismatch = False
        if isinstance(expected, bool):
            parsed, valid = _extract_bool(authoritative_value)
            mismatch = (not valid) or (parsed != expected)
        elif isinstance(expected, int):
            mismatch = _as_field_int(authoritative_value) != expected
        elif isinstance(expected, list):
            if field_name == "command_argv":
                mismatch = _normalize_string_list(authoritative_value, sort_items=False) != expected
            else:
                mismatch = _normalize_string_list(authoritative_value) != expected
        else:
            mismatch = _normalize_text(authoritative_value, default="") != expected

        if mismatch:
            validation_errors.append(
                f"local_codex_one_shot_handoff_{field_name}_mismatch_expected_{expected}"
            )
            if not first_failure_reason:
                first_failure_reason = field_to_blocked_reason.get(
                    field_name,
                    "local_codex_one_shot_handoff_not_valid_for_execution",
                )

        for surface_name, surface in supporting_surfaces:
            if field_name not in surface:
                continue
            support_value = surface.get(field_name)
            support_mismatch = False
            if isinstance(expected, bool):
                parsed, valid = _extract_bool(support_value)
                support_mismatch = (not valid) or (parsed != expected)
            elif isinstance(expected, int):
                support_mismatch = _as_field_int(support_value) != expected
            elif isinstance(expected, list):
                if field_name == "command_argv":
                    if support_value is None:
                        continue
                    if isinstance(support_value, (list, tuple)):
                        normalized_support_argv = _normalize_string_list(
                            support_value,
                            sort_items=False,
                        )
                        if not normalized_support_argv:
                            continue
                        support_mismatch = normalized_support_argv != expected
                    else:
                        # Receipt command_argv is optional, but if present as a non-empty
                        # non-sequence value it is treated as an invalid/mismatched command.
                        support_mismatch = bool(
                            _normalize_text(support_value, default="")
                        )
                else:
                    support_mismatch = _normalize_string_list(support_value) != expected
            else:
                support_mismatch = _normalize_text(support_value, default="") != expected

            if support_mismatch:
                validation_errors.append(
                    "local_codex_one_shot_handoff_"
                    f"{field_name}_mismatch_in_supporting_{surface_name}_artifact"
                )
                if not first_failure_reason:
                    first_failure_reason = field_to_blocked_reason.get(
                        field_name,
                        "local_codex_one_shot_handoff_not_valid_for_execution",
                    )

    authoritative_command_argv = authoritative.get("command_argv")
    authoritative_command_argv_matches_expected = (
        isinstance(authoritative_command_argv, (list, tuple))
        and list(authoritative_command_argv) == expected_command_argv
    )
    if not authoritative_command_argv_matches_expected:
        validation_errors.append(
            "local_codex_one_shot_handoff_command_argv_mismatch_expected_"
            f"{expected_command_argv}"
        )
        if not first_failure_reason:
            first_failure_reason = "local_codex_one_shot_handoff_command_argv_mismatch"
        command_argv_mismatch_source = "authoritative_handoff"

    support_command_argv = receipt_payload.get("command_argv")
    support_command_argv_is_optional_missing = False
    if support_command_argv is None:
        support_command_argv_is_optional_missing = True
    elif isinstance(support_command_argv, str) and not support_command_argv.strip():
        support_command_argv_is_optional_missing = True
    elif isinstance(support_command_argv, (list, tuple)) and not support_command_argv:
        support_command_argv_is_optional_missing = True

    if not support_command_argv_is_optional_missing:
        if isinstance(support_command_argv, (list, tuple)):
            if list(support_command_argv) != expected_command_argv:
                validation_errors.append(
                    "local_codex_one_shot_handoff_command_argv_"
                    "mismatch_in_supporting_receipt_artifact"
                )
                if not first_failure_reason:
                    first_failure_reason = (
                        "local_codex_one_shot_handoff_command_argv_mismatch"
                    )
                if command_argv_mismatch_source == "none":
                    command_argv_mismatch_source = "supporting_receipt"
        else:
            validation_errors.append(
                "local_codex_one_shot_handoff_command_argv_"
                "invalid_shape_in_supporting_receipt_artifact"
            )
            if not first_failure_reason:
                first_failure_reason = "local_codex_one_shot_handoff_command_argv_mismatch"
            if command_argv_mismatch_source == "none":
                command_argv_mismatch_source = "supporting_receipt_shape"

    command_argv_diagnostics["command_argv_mismatch_source"] = command_argv_mismatch_source

    resolved_prompt_path_text = _normalize_text(
        authoritative.get("prompt_path"),
        default=str(prompt_path),
    )
    resolved_prompt_path = Path(resolved_prompt_path_text)

    prompt_text = ""
    try:
        prompt_text = resolved_prompt_path.read_text(encoding="utf-8")
    except OSError:
        prompt_text = ""
    if not prompt_text:
        if not validation_errors:
            validation_errors.append("local_codex_one_shot_prompt_missing")
        return _blocked_state(
            blocked_reason="local_codex_one_shot_prompt_missing",
            validation_errors=validation_errors,
        )
    if not prompt_text.strip():
        validation_errors.append("local_codex_one_shot_prompt_empty")
        return _blocked_state(
            blocked_reason="local_codex_one_shot_prompt_empty",
            validation_errors=validation_errors,
        )

    if validation_errors:
        return _blocked_state(
            blocked_reason=(
                first_failure_reason or "local_codex_one_shot_handoff_not_valid_for_execution"
            ),
            validation_errors=validation_errors,
        )

    try:
        status_short_cmd = _run_git(
            _normalize_text(execution_repo_path, default=_APPROVE_COMMIT_TAG_EXECUTION_REPO_PATH),
            ["status", "--short", "--untracked-files=no"],
            timeout_seconds=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        status_short_cmd = subprocess.CompletedProcess(
            args=["git", "status", "--short", "--untracked-files=no"],
            returncode=1,
            stdout="",
            stderr="",
        )

    if status_short_cmd.returncode != 0:
        return _blocked_state(
            blocked_reason="git_metadata_collection_failed_before_local_codex_one_shot_execution",
            validation_errors=[],
            readiness_reason="worktree_not_clean_before_local_codex_one_shot_execution",
            next_action="review_git_metadata_failure_before_local_codex_one_shot_execution",
        )

    changed_tracked_files = sorted(
        {
            _parse_git_status_path(line)
            for line in (status_short_cmd.stdout or "").splitlines()
            if line.strip() and _parse_git_status_path(line)
        }
    )
    if changed_tracked_files:
        return _blocked_state(
            blocked_reason="tracked_changes_present_before_local_codex_one_shot_execution",
            validation_errors=[],
            changed_tracked_files=changed_tracked_files,
            readiness_reason="worktree_not_clean_before_local_codex_one_shot_execution",
            next_action=(
                "commit_or_reconcile_tracked_changes_before_local_codex_one_shot_execution"
            ),
        )

    command_argv = list(authoritative.get("command_argv", []))
    try:
        completed = subprocess.run(
            command_argv,
            input=prompt_text,
            shell=False,
            cwd=_normalize_text(
                execution_repo_path,
                default=_APPROVE_COMMIT_TAG_EXECUTION_REPO_PATH,
            ),
            capture_output=True,
            text=True,
            check=False,
        )
        execution_exit_code = int(completed.returncode)
        raw_stdout = _normalize_text(completed.stdout, default="")
        raw_stderr = _normalize_text(completed.stderr, default="")
    except subprocess.TimeoutExpired as exc:
        execution_exit_code = 124
        raw_stdout = _normalize_text(exc.stdout, default="")
        raw_stderr = _normalize_text(exc.stderr, default="")
    except OSError as exc:
        execution_exit_code = 126
        raw_stdout = ""
        raw_stderr = _normalize_text(str(exc), default="")

    stdout_text, stdout_truncated, stdout_chars_total = _bounded_output(
        raw_stdout,
        max_chars=_LOCAL_CODEX_ONE_SHOT_EXECUTION_OUTPUT_MAX_CHARS,
    )
    stderr_text, stderr_truncated, stderr_chars_total = _bounded_output(
        raw_stderr,
        max_chars=_LOCAL_CODEX_ONE_SHOT_EXECUTION_OUTPUT_MAX_CHARS,
    )
    try:
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(stdout_text, encoding="utf-8")
        stderr_path.parent.mkdir(parents=True, exist_ok=True)
        stderr_path.write_text(stderr_text, encoding="utf-8")
    except OSError:
        pass

    try:
        post_status_cmd = _run_git(
            _normalize_text(execution_repo_path, default=_APPROVE_COMMIT_TAG_EXECUTION_REPO_PATH),
            ["status", "--short", "--untracked-files=no"],
            timeout_seconds=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        post_status_cmd = subprocess.CompletedProcess(
            args=["git", "status", "--short", "--untracked-files=no"],
            returncode=1,
            stdout="",
            stderr="",
        )
    changed_tracked_files_after_execution = (
        sorted(
            {
                _parse_git_status_path(line)
                for line in (post_status_cmd.stdout or "").splitlines()
                if line.strip() and _parse_git_status_path(line)
            }
        )
        if post_status_cmd.returncode == 0
        else []
    )

    should_continue = execution_exit_code == 0
    return {
        "schema_version": _LOCAL_AUTONOMOUS_CYCLE_V2_SCHEMA_VERSION,
        "execution_schema_version": _LOCAL_CODEX_ONE_SHOT_EXECUTION_SCHEMA_VERSION,
        "source_prompt": "prompt333",
        "source_handoff_schema_version": _LOCAL_CODEX_ONE_SHOT_HANDOFF_SCHEMA_VERSION,
        "run_id": run_id,
        "cycle_id": cycle_id,
        "current_cycle": _LOCAL_AUTONOMOUS_CYCLE_V2_CURRENT_CYCLE,
        "max_cycles": _LOCAL_AUTONOMOUS_CYCLE_V2_MAX_CYCLES,
        "source_step_id": 2,
        "source_step_name": "generate_next_codex_task",
        "source_step_operation": "generate_next_codex_task",
        "status": "completed",
        "execution_status": "completed",
        "blocked_reason": "none",
        "readiness_reason": "local_codex_one_shot_handoff_valid_and_tracked_worktree_clean",
        "execution_result": (
            "codex_one_shot_completed" if should_continue else "codex_one_shot_failed"
        ),
        "codex_invoked": True,
        "codex_invocation_allowed": True,
        "execution_allowed": True,
        "execution_attempted": True,
        "execution_completed": True,
        "execution_exit_code": int(execution_exit_code),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "result_path": str(result_path),
        "selected_step_id": 2,
        "selected_step_name": "generate_next_codex_task",
        "selected_step_operation": "generate_next_codex_task",
        "command_argv": list(command_argv),
        "prompt_path": str(resolved_prompt_path),
        "prompt_exists": True,
        "prompt_non_empty": True,
        "max_codex_invocations": 1,
        "codex_invocation_count": 1,
        "changed_tracked_files": [],
        "changed_tracked_files_after_execution": changed_tracked_files_after_execution,
        "validation_errors": [],
        "should_continue": should_continue,
        "next_action": (
            "prepare_local_git_diff_capture"
            if should_continue
            else "manual_review_local_codex_one_shot_execution_failure"
        ),
        "stdout_chars_total": stdout_chars_total,
        "stderr_chars_total": stderr_chars_total,
        "stdout_chars_written": len(stdout_text),
        "stderr_chars_written": len(stderr_text),
        "stdout_truncated": stdout_truncated,
        "stderr_truncated": stderr_truncated,
        "output_max_chars": _LOCAL_CODEX_ONE_SHOT_EXECUTION_OUTPUT_MAX_CHARS,
        "commit_allowed": False,
        "tag_allowed": False,
        "commit_performed": False,
        "tag_performed": False,
        "push_pr_merge_enabled": False,
        "push_performed": False,
        "pr_created": False,
        "merge_performed": False,
        "targeted_fix_allowed": False,
        "rollback_allowed": False,
        "rollback_performed": False,
        **command_argv_diagnostics,
    }

def _build_targeted_fix_reentry_execution_gate_state(
    *,
    execution_enabled: bool,
    execution_confirmed: bool,
    dry_run: bool,
    review_route_status: str,
    review_route_decision: str,
    review_route_should_prepare_targeted_fix: bool,
    targeted_fix_boundary_status: str,
    targeted_fix_boundary_decision: str,
    targeted_fix_boundary_prompt_ready: bool,
    targeted_fix_boundary_codex_prompt_path: str,
    receipt_path: str,
) -> dict[str, Any]:
    normalized_prompt_path = _normalize_text(
        targeted_fix_boundary_codex_prompt_path,
        default=_TARGETED_FIX_REENTRY_EXECUTION_PROMPT_PATH,
    )
    state: dict[str, Any] = {
        "execution_enabled": bool(execution_enabled),
        "execution_confirmed": bool(execution_confirmed),
        "execution_gate_status": "not_applicable",
        "execution_status": "not_executed",
        "execution_attempted": False,
        "execution_exit_code": 0,
        "execution_blocked_reason": "route_not_targeted_fix",
        "execution_prompt_path": normalized_prompt_path,
        "execution_receipt_path": _normalize_text(
            receipt_path,
            default=_TARGETED_FIX_REENTRY_EXECUTION_RECEIPT_PATH,
        ),
        "execution_should_execute_codex": False,
    }
    if review_route_decision != "targeted_fix":
        return state
    state.update(
        {
            "execution_gate_status": "execution_not_enabled",
            "execution_status": "not_executed",
            "execution_attempted": False,
            "execution_exit_code": 0,
            "execution_blocked_reason": "execution_not_enabled",
            "execution_should_execute_codex": False,
        }
    )
    if not execution_enabled or not execution_confirmed:
        return state
    if dry_run:
        state.update(
            {
                "execution_gate_status": "dry_run_suppressed",
                "execution_status": "dry_run_suppressed",
                "execution_attempted": False,
                "execution_exit_code": 0,
                "execution_blocked_reason": "dry_run_execution_suppressed",
                "execution_should_execute_codex": False,
            }
        )
        return state
    boundary_ready = (
        review_route_status == "route_ready"
        and bool(review_route_should_prepare_targeted_fix)
        and targeted_fix_boundary_status == "boundary_ready"
        and targeted_fix_boundary_decision == "targeted_fix"
        and bool(targeted_fix_boundary_prompt_ready)
        and normalized_prompt_path == _TARGETED_FIX_REENTRY_EXECUTION_PROMPT_PATH
    )
    if not boundary_ready:
        state.update(
            {
                "execution_gate_status": "boundary_not_ready",
                "execution_status": "blocked",
                "execution_attempted": False,
                "execution_exit_code": 0,
                "execution_blocked_reason": "boundary_not_ready",
                "execution_should_execute_codex": False,
            }
        )
        return state
    state.update(
        {
            "execution_gate_status": "blocked",
            "execution_status": "blocked",
            "execution_attempted": False,
            "execution_exit_code": 0,
            "execution_blocked_reason": "targeted_fix_prompt_execution_adapter_missing",
            "execution_should_execute_codex": False,
        }
    )
    return state

def _build_targeted_fix_post_reentry_review_handoff_state(
    *,
    diff_capture_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    capture_state = dict(diff_capture_state) if isinstance(diff_capture_state, Mapping) else {}
    review_handoff_path = _TARGETED_FIX_POST_REENTRY_REVIEW_HANDOFF_PATH
    state: dict[str, Any] = {
        "status": "not_applicable",
        "handoff_status": "not_applicable",
        "blocked_reason": "reentry_not_completed",
        "review_required": False,
        "review_kind": "not_applicable",
        "source": "targeted_fix_post_reentry_diff_capture",
        "reentry_receipt_path": _normalize_text(
            capture_state.get("reentry_receipt_path"),
            default=_TARGETED_FIX_REENTRY_EXECUTION_RECEIPT_PATH,
        ),
        "diff_capture_path": _normalize_text(
            capture_state.get("diff_capture_path"),
            default=_TARGETED_FIX_POST_REENTRY_DIFF_CAPTURE_PATH,
        ),
        "diff_patch_path": _normalize_text(
            capture_state.get("diff_patch_path"),
            default=_TARGETED_FIX_POST_REENTRY_DIFF_PATCH_PATH,
        ),
        "diff_stat_path": _normalize_text(
            capture_state.get("diff_stat_path"),
            default=_TARGETED_FIX_POST_REENTRY_DIFF_STAT_PATH,
        ),
        "diff_name_status_path": _normalize_text(
            capture_state.get("diff_name_status_path"),
            default=_TARGETED_FIX_POST_REENTRY_DIFF_NAME_STATUS_PATH,
        ),
        "review_handoff_path": review_handoff_path,
        "changed_files": [],
        "changed_file_count": 0,
        "has_diff": False,
        "summary": "Post-reentry review handoff not applicable because reentry did not complete.",
    }
    capture_status = _normalize_text(capture_state.get("capture_status"), default="not_applicable")
    capture_blocked_reason = _normalize_text(
        capture_state.get("blocked_reason"),
        default="reentry_not_completed",
    )
    if capture_status == "captured":
        state.update(
            {
                "status": "ready",
                "handoff_status": "ready",
                "blocked_reason": "none",
                "review_required": True,
                "review_kind": "targeted_fix_post_reentry_review",
                "changed_files": _normalize_string_list(capture_state.get("changed_files")),
                "changed_file_count": _as_non_negative_int(
                    capture_state.get("changed_file_count"),
                    default=0,
                ),
                "has_diff": bool(capture_state.get("has_diff", False)),
                "summary": "Post-reentry diff captured; targeted fix review is required.",
            }
        )
    elif capture_status == "captured_no_diff":
        state.update(
            {
                "status": "ready_no_diff",
                "handoff_status": "ready_no_diff",
                "blocked_reason": "none",
                "review_required": False,
                "review_kind": "targeted_fix_post_reentry_no_diff_review",
                "changed_files": [],
                "changed_file_count": 0,
                "has_diff": False,
                "summary": "Post-reentry completed with no tracked/staged diff.",
            }
        )
    elif capture_status == "blocked":
        state.update(
            {
                "status": "blocked",
                "handoff_status": "blocked",
                "blocked_reason": capture_blocked_reason or "diff_capture_failed",
                "review_required": False,
                "review_kind": "targeted_fix_post_reentry_review_blocked",
                "summary": "Post-reentry diff capture was blocked.",
            }
        )

    try:
        Path(review_handoff_path).parent.mkdir(parents=True, exist_ok=True)
        _write_json(Path(review_handoff_path), state)
    except OSError:
        pass
    return state

def _build_targeted_fix_post_reentry_review_assimilation_state(
    *,
    review_handoff_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    handoff_state = (
        dict(review_handoff_state) if isinstance(review_handoff_state, Mapping) else {}
    )
    review_response_path = _TARGETED_FIX_POST_REENTRY_REVIEW_RESPONSE_PATH
    review_handoff_path = _TARGETED_FIX_POST_REENTRY_REVIEW_HANDOFF_PATH
    review_assimilation_path = _TARGETED_FIX_POST_REENTRY_REVIEW_ASSIMILATION_PATH
    handoff_status = _normalize_text(handoff_state.get("handoff_status"), default="not_applicable")
    review_required = bool(handoff_state.get("review_required", False))
    state: dict[str, Any] = {
        "status": "not_applicable",
        "assimilation_status": "not_applicable",
        "blocked_reason": "review_handoff_not_ready",
        "attempted": False,
        "source": "targeted_fix_post_reentry_review_handoff",
        "review_response_path": review_response_path,
        "review_handoff_path": review_handoff_path,
        "handoff_status": handoff_status,
        "review_required": review_required,
        "decision": "none",
        "normalized_decision": "none",
        "reason": "",
        "summary": "",
        "targeted_fix_prompt_present": False,
        "targeted_fix_prompt_length": 0,
    }
    if handoff_status == "ready_no_diff" and not review_required:
        state.update(
            {
                "status": "ready",
                "assimilation_status": "no_review_required",
                "blocked_reason": "none",
                "attempted": True,
                "decision": "no_action",
                "normalized_decision": "no_action",
                "reason": "no_review_required",
                "summary": _normalize_text(
                    handoff_state.get("summary"),
                    default="Post-reentry no-diff handoff does not require review response.",
                ),
                "targeted_fix_prompt_present": False,
                "targeted_fix_prompt_length": 0,
            }
        )
    elif handoff_status == "ready" and review_required:
        state["attempted"] = True
        response_path = Path(review_response_path)
        if not response_path.exists():
            state.update(
                {
                    "status": "blocked",
                    "assimilation_status": "blocked",
                    "blocked_reason": "post_reentry_review_response_missing",
                }
            )
        else:
            try:
                payload = json.loads(response_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, ValueError):
                state.update(
                    {
                        "status": "blocked",
                        "assimilation_status": "blocked",
                        "blocked_reason": "post_reentry_review_response_invalid_json",
                    }
                )
            else:
                if not isinstance(payload, Mapping):
                    state.update(
                        {
                            "status": "blocked",
                            "assimilation_status": "blocked",
                            "blocked_reason": "post_reentry_review_response_invalid_json",
                        }
                    )
                else:
                    decision = _normalize_text(payload.get("decision"), default="")
                    normalized_decision = decision.lower()
                    reason = _normalize_text(payload.get("reason"), default="")
                    summary = _normalize_text(payload.get("summary"), default="")
                    targeted_fix_prompt = _normalize_text(
                        payload.get("targeted_fix_prompt"),
                        default="",
                    )
                    targeted_fix_prompt_present = bool(targeted_fix_prompt)
                    targeted_fix_prompt_length = len(targeted_fix_prompt)
                    state.update(
                        {
                            "decision": decision or "none",
                            "normalized_decision": normalized_decision or "none",
                            "reason": reason,
                            "summary": summary,
                            "targeted_fix_prompt_present": targeted_fix_prompt_present,
                            "targeted_fix_prompt_length": targeted_fix_prompt_length,
                        }
                    )
                    if normalized_decision not in {
                        "approve",
                        "reject",
                        "targeted_fix",
                        "no_action",
                    }:
                        state.update(
                            {
                                "status": "blocked",
                                "assimilation_status": "blocked",
                                "blocked_reason": "unsupported_post_reentry_review_decision",
                            }
                        )
                    elif normalized_decision == "targeted_fix" and not targeted_fix_prompt_present:
                        state.update(
                            {
                                "status": "blocked",
                                "assimilation_status": "blocked",
                                "blocked_reason": "post_reentry_targeted_fix_prompt_missing",
                            }
                        )
                    else:
                        state.update(
                            {
                                "status": "ready",
                                "assimilation_status": "assimilated",
                                "blocked_reason": "none",
                            }
                        )
    try:
        Path(review_assimilation_path).parent.mkdir(parents=True, exist_ok=True)
        _write_json(Path(review_assimilation_path), state)
    except OSError:
        pass
    return state

def _build_targeted_fix_post_reentry_route_decision_state(
    *,
    review_assimilation_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    assimilation_state = (
        dict(review_assimilation_state)
        if isinstance(review_assimilation_state, Mapping)
        else {}
    )
    review_response_path = _TARGETED_FIX_POST_REENTRY_REVIEW_RESPONSE_PATH
    review_handoff_path = _TARGETED_FIX_POST_REENTRY_REVIEW_HANDOFF_PATH
    review_assimilation_path = _TARGETED_FIX_POST_REENTRY_REVIEW_ASSIMILATION_PATH
    route_decision_path = _TARGETED_FIX_POST_REENTRY_ROUTE_DECISION_PATH
    normalized_decision = _normalize_text(
        assimilation_state.get("normalized_decision"),
        default="none",
    )
    assimilation_status = _normalize_text(
        assimilation_state.get("assimilation_status"),
        default="not_applicable",
    )
    blocked_reason = _normalize_text(
        assimilation_state.get("blocked_reason"),
        default="review_handoff_not_ready",
    )
    targeted_fix_prompt_present = bool(
        assimilation_state.get("targeted_fix_prompt_present", False)
    )
    summary = _normalize_text(assimilation_state.get("summary"), default="")
    state: dict[str, Any] = {
        "status": "blocked",
        "route_status": "blocked",
        "blocked_reason": "manual_review_required",
        "source": "targeted_fix_post_reentry_review_assimilation",
        "review_response_path": review_response_path,
        "review_assimilation_path": review_assimilation_path,
        "review_handoff_path": review_handoff_path,
        "route_decision": "manual_review_required",
        "next_action": "manual_review_required",
        "manual_review_required": True,
        "targeted_fix_required": False,
        "approve_allowed": False,
        "reject_allowed": False,
        "no_action_allowed": False,
        "targeted_fix_prompt_present": targeted_fix_prompt_present,
        "summary": summary,
    }
    if assimilation_status == "no_review_required" and normalized_decision == "no_action":
        state.update(
            {
                "status": "ready",
                "route_status": "ready",
                "blocked_reason": "none",
                "route_decision": "completed_no_diff",
                "next_action": "complete_post_reentry_no_diff",
                "manual_review_required": False,
                "targeted_fix_required": False,
                "approve_allowed": False,
                "reject_allowed": False,
                "no_action_allowed": True,
                "targeted_fix_prompt_present": False,
                "summary": summary or "No post-reentry diff; no review response required.",
            }
        )
    elif assimilation_status == "blocked":
        if blocked_reason == "post_reentry_review_response_missing":
            state.update(
                {
                    "status": "blocked",
                    "route_status": "blocked",
                    "blocked_reason": "post_reentry_review_response_missing",
                    "route_decision": "await_review_response",
                    "next_action": "provide_post_reentry_review_response",
                    "manual_review_required": False,
                    "summary": summary or "Post-reentry review response file is missing.",
                }
            )
        elif blocked_reason == "post_reentry_review_response_invalid_json":
            state.update(
                {
                    "status": "blocked",
                    "route_status": "blocked",
                    "blocked_reason": "post_reentry_review_response_invalid_json",
                    "route_decision": "await_valid_review_response",
                    "next_action": "provide_valid_post_reentry_review_response",
                    "manual_review_required": False,
                    "summary": summary or "Post-reentry review response JSON is invalid.",
                }
            )
        elif blocked_reason == "unsupported_post_reentry_review_decision":
            state.update(
                {
                    "status": "blocked",
                    "route_status": "blocked",
                    "blocked_reason": "unsupported_post_reentry_review_decision",
                    "route_decision": "manual_review_required",
                    "next_action": "manual_review_required",
                    "manual_review_required": True,
                    "summary": summary or "Post-reentry review decision is unsupported.",
                }
            )
        elif blocked_reason == "post_reentry_targeted_fix_prompt_missing":
            state.update(
                {
                    "status": "blocked",
                    "route_status": "blocked",
                    "blocked_reason": "post_reentry_targeted_fix_prompt_missing",
                    "route_decision": "targeted_fix_blocked",
                    "next_action": "provide_post_reentry_targeted_fix_prompt",
                    "manual_review_required": False,
                    "targeted_fix_required": True,
                    "summary": summary or "Targeted-fix decision requires non-empty prompt.",
                }
            )
    elif assimilation_status == "assimilated":
        if normalized_decision == "approve":
            state.update(
                {
                    "status": "ready",
                    "route_status": "ready",
                    "blocked_reason": "none",
                    "route_decision": "approve",
                    "next_action": "prepare_post_reentry_approve_boundary",
                    "manual_review_required": False,
                    "targeted_fix_required": False,
                    "approve_allowed": True,
                    "reject_allowed": False,
                    "no_action_allowed": False,
                    "targeted_fix_prompt_present": False,
                    "summary": summary or "Post-reentry review approved.",
                }
            )
        elif normalized_decision == "reject":
            state.update(
                {
                    "status": "ready",
                    "route_status": "ready",
                    "blocked_reason": "none",
                    "route_decision": "reject",
                    "next_action": "prepare_post_reentry_reject_boundary",
                    "manual_review_required": False,
                    "targeted_fix_required": False,
                    "approve_allowed": False,
                    "reject_allowed": True,
                    "no_action_allowed": False,
                    "targeted_fix_prompt_present": False,
                    "summary": summary or "Post-reentry review rejected.",
                }
            )
        elif normalized_decision == "targeted_fix":
            state.update(
                {
                    "status": "ready",
                    "route_status": "ready",
                    "blocked_reason": "none",
                    "route_decision": "targeted_fix",
                    "next_action": "prepare_post_reentry_targeted_fix_prompt",
                    "manual_review_required": False,
                    "targeted_fix_required": True,
                    "approve_allowed": False,
                    "reject_allowed": False,
                    "no_action_allowed": False,
                    "targeted_fix_prompt_present": targeted_fix_prompt_present,
                    "summary": summary or "Post-reentry follow-up targeted fix requested.",
                }
            )
        elif normalized_decision == "no_action":
            state.update(
                {
                    "status": "ready",
                    "route_status": "ready",
                    "blocked_reason": "none",
                    "route_decision": "no_action",
                    "next_action": "complete_post_reentry_no_action",
                    "manual_review_required": False,
                    "targeted_fix_required": False,
                    "approve_allowed": False,
                    "reject_allowed": False,
                    "no_action_allowed": True,
                    "targeted_fix_prompt_present": False,
                    "summary": summary or "Post-reentry review indicates no action.",
                }
            )
    try:
        Path(route_decision_path).parent.mkdir(parents=True, exist_ok=True)
        _write_json(Path(route_decision_path), state)
    except OSError:
        pass
    return state

def _build_targeted_fix_post_reentry_route_executor_boundary_state(
    *,
    route_decision_path: Path,
) -> dict[str, Any]:
    normalized_route_decision_path = _normalize_text(
        str(route_decision_path),
        default=_TARGETED_FIX_POST_REENTRY_ROUTE_DECISION_PATH,
    )
    boundary_path = _TARGETED_FIX_POST_REENTRY_ROUTE_EXECUTOR_BOUNDARY_PATH
    route_payload: dict[str, Any] = {}
    try:
        loaded_payload = _read_json_object_if_exists(Path(normalized_route_decision_path))
    except (OSError, ValueError, json.JSONDecodeError):
        loaded_payload = None
    if isinstance(loaded_payload, Mapping):
        route_payload = dict(loaded_payload)
    route_decision = _normalize_text(route_payload.get("route_decision"), default="")
    route_status = _normalize_text(route_payload.get("route_status"), default="blocked")
    state: dict[str, Any] = {
        "status": "blocked",
        "boundary_status": "blocked",
        "blocked_reason": "unsupported_or_missing_post_reentry_route_decision",
        "source": "targeted_fix_post_reentry_route_decision",
        "route_decision_path": normalized_route_decision_path,
        "route_decision": route_decision,
        "route_status": route_status,
        "next_action": "manual_review_required",
        "executor_kind": "manual_review",
        "execution_allowed": False,
        "cycle_closure_allowed": False,
        "approval_boundary_allowed": False,
        "reject_boundary_allowed": False,
        "targeted_fix_prompt_emission_allowed": False,
        "codex_reentry_allowed": False,
        "commit_allowed": False,
        "rollback_allowed": False,
        "manual_review_required": True,
        "summary": "Post-reentry route decision missing or unsupported; manual review required.",
    }
    if route_decision == "completed_no_diff":
        state.update(
            {
                "status": "ready",
                "boundary_status": "ready",
                "blocked_reason": "none",
                "next_action": "complete_post_reentry_no_diff",
                "executor_kind": "cycle_closure",
                "execution_allowed": False,
                "cycle_closure_allowed": True,
                "approval_boundary_allowed": False,
                "reject_boundary_allowed": False,
                "targeted_fix_prompt_emission_allowed": False,
                "codex_reentry_allowed": False,
                "commit_allowed": False,
                "rollback_allowed": False,
                "manual_review_required": False,
                "summary": "Post-reentry route is completed_no_diff; cycle closure is ready.",
            }
        )
    elif route_decision == "no_action":
        state.update(
            {
                "status": "ready",
                "boundary_status": "ready",
                "blocked_reason": "none",
                "next_action": "complete_post_reentry_no_action",
                "executor_kind": "cycle_closure",
                "execution_allowed": False,
                "cycle_closure_allowed": True,
                "approval_boundary_allowed": False,
                "reject_boundary_allowed": False,
                "targeted_fix_prompt_emission_allowed": False,
                "codex_reentry_allowed": False,
                "commit_allowed": False,
                "rollback_allowed": False,
                "manual_review_required": False,
                "summary": "Post-reentry route is no_action; cycle closure is ready.",
            }
        )
    elif route_decision == "approve":
        state.update(
            {
                "status": "ready",
                "boundary_status": "ready",
                "blocked_reason": "none",
                "next_action": "prepare_post_reentry_approve_boundary",
                "executor_kind": "approve_boundary",
                "execution_allowed": False,
                "cycle_closure_allowed": False,
                "approval_boundary_allowed": True,
                "reject_boundary_allowed": False,
                "targeted_fix_prompt_emission_allowed": False,
                "codex_reentry_allowed": False,
                "commit_allowed": False,
                "rollback_allowed": False,
                "manual_review_required": False,
                "summary": "Post-reentry route is approve; only approval boundary preparation is ready.",
            }
        )
    elif route_decision == "reject":
        state.update(
            {
                "status": "ready",
                "boundary_status": "ready",
                "blocked_reason": "none",
                "next_action": "prepare_post_reentry_reject_boundary",
                "executor_kind": "reject_boundary",
                "execution_allowed": False,
                "cycle_closure_allowed": False,
                "approval_boundary_allowed": False,
                "reject_boundary_allowed": True,
                "targeted_fix_prompt_emission_allowed": False,
                "codex_reentry_allowed": False,
                "commit_allowed": False,
                "rollback_allowed": False,
                "manual_review_required": False,
                "summary": "Post-reentry route is reject; only reject boundary preparation is ready.",
            }
        )
    elif route_decision == "targeted_fix":
        state.update(
            {
                "status": "ready",
                "boundary_status": "ready",
                "blocked_reason": "none",
                "next_action": "prepare_post_reentry_targeted_fix_prompt",
                "executor_kind": "targeted_fix_prompt_emission",
                "execution_allowed": False,
                "cycle_closure_allowed": False,
                "approval_boundary_allowed": False,
                "reject_boundary_allowed": False,
                "targeted_fix_prompt_emission_allowed": True,
                "codex_reentry_allowed": False,
                "commit_allowed": False,
                "rollback_allowed": False,
                "manual_review_required": False,
                "summary": (
                    "Post-reentry route is targeted_fix; targeted-fix prompt emission preparation is ready."
                ),
            }
        )
    elif route_decision in {"await_review_response", "await_valid_review_response"}:
        state.update(
            {
                "status": "blocked",
                "boundary_status": "blocked",
                "blocked_reason": "post_reentry_review_response_required",
                "next_action": "provide_post_reentry_review_response",
                "executor_kind": "manual_review_input",
                "execution_allowed": False,
                "cycle_closure_allowed": False,
                "approval_boundary_allowed": False,
                "reject_boundary_allowed": False,
                "targeted_fix_prompt_emission_allowed": False,
                "codex_reentry_allowed": False,
                "commit_allowed": False,
                "rollback_allowed": False,
                "manual_review_required": True,
                "summary": "Post-reentry review response is required before any route preparation.",
            }
        )
    elif route_decision == "targeted_fix_blocked":
        state.update(
            {
                "status": "blocked",
                "boundary_status": "blocked",
                "blocked_reason": "post_reentry_targeted_fix_prompt_missing",
                "next_action": "provide_post_reentry_targeted_fix_prompt",
                "executor_kind": "manual_targeted_fix_prompt_input",
                "execution_allowed": False,
                "cycle_closure_allowed": False,
                "approval_boundary_allowed": False,
                "reject_boundary_allowed": False,
                "targeted_fix_prompt_emission_allowed": False,
                "codex_reentry_allowed": False,
                "commit_allowed": False,
                "rollback_allowed": False,
                "manual_review_required": True,
                "summary": "Targeted-fix prompt is missing; manual prompt input is required.",
            }
        )
    elif route_decision in {"manual_review_required", "blocked"}:
        state.update(
            {
                "status": "blocked",
                "boundary_status": "blocked",
                "blocked_reason": "unsupported_or_missing_post_reentry_route_decision",
                "next_action": "manual_review_required",
                "executor_kind": "manual_review",
                "execution_allowed": False,
                "cycle_closure_allowed": False,
                "approval_boundary_allowed": False,
                "reject_boundary_allowed": False,
                "targeted_fix_prompt_emission_allowed": False,
                "codex_reentry_allowed": False,
                "commit_allowed": False,
                "rollback_allowed": False,
                "manual_review_required": True,
                "summary": "Post-reentry route remains blocked; manual review is required.",
            }
        )
    try:
        Path(boundary_path).parent.mkdir(parents=True, exist_ok=True)
        _write_json(Path(boundary_path), state)
    except OSError:
        pass
    return state

def _build_targeted_fix_post_reentry_next_step_handoff_state(
    *,
    route_executor_boundary_state: Mapping[str, Any] | None,
    route_decision_path: Path,
    route_executor_boundary_path: Path,
) -> dict[str, Any]:
    boundary_state = (
        dict(route_executor_boundary_state)
        if isinstance(route_executor_boundary_state, Mapping)
        else {}
    )
    handoff_path = _TARGETED_FIX_POST_REENTRY_NEXT_STEP_HANDOFF_PATH
    route_decision = _normalize_text(boundary_state.get("route_decision"), default="")
    boundary_status = _normalize_text(boundary_state.get("boundary_status"), default="blocked")
    blocked_reason = _normalize_text(
        boundary_state.get("blocked_reason"),
        default="unsupported_or_missing_post_reentry_route_decision",
    )
    executor_kind = _normalize_text(boundary_state.get("executor_kind"), default="manual_review")
    next_action = _normalize_text(boundary_state.get("next_action"), default="manual_review_required")
    state: dict[str, Any] = {
        "status": "blocked",
        "handoff_status": "blocked",
        "blocked_reason": blocked_reason,
        "source": "targeted_fix_post_reentry_route_executor_boundary",
        "route_decision_path": _normalize_text(
            str(route_decision_path),
            default=_TARGETED_FIX_POST_REENTRY_ROUTE_DECISION_PATH,
        ),
        "route_executor_boundary_path": _normalize_text(
            str(route_executor_boundary_path),
            default=_TARGETED_FIX_POST_REENTRY_ROUTE_EXECUTOR_BOUNDARY_PATH,
        ),
        "route_decision": route_decision,
        "handoff_kind": "manual_review",
        "next_action": next_action,
        "action_consumable": False,
        "manual_review_required": True,
        "execution_allowed": False,
        "summary": "Post-reentry route handoff is blocked pending manual review.",
    }
    if boundary_status == "ready":
        if executor_kind == "cycle_closure":
            state.update(
                {
                    "status": "ready",
                    "handoff_status": "ready",
                    "blocked_reason": "none",
                    "handoff_kind": "cycle_closure",
                    "action_consumable": True,
                    "manual_review_required": False,
                    "execution_allowed": False,
                    "summary": "Cycle closure next-step handoff is ready.",
                }
            )
        elif executor_kind == "approve_boundary":
            state.update(
                {
                    "status": "ready",
                    "handoff_status": "ready",
                    "blocked_reason": "none",
                    "handoff_kind": "approve_boundary",
                    "action_consumable": True,
                    "manual_review_required": False,
                    "execution_allowed": False,
                    "summary": "Approve boundary preparation handoff is ready.",
                }
            )
        elif executor_kind == "reject_boundary":
            state.update(
                {
                    "status": "ready",
                    "handoff_status": "ready",
                    "blocked_reason": "none",
                    "handoff_kind": "reject_boundary",
                    "action_consumable": True,
                    "manual_review_required": False,
                    "execution_allowed": False,
                    "summary": "Reject boundary preparation handoff is ready.",
                }
            )
        elif executor_kind == "targeted_fix_prompt_emission":
            state.update(
                {
                    "status": "ready",
                    "handoff_status": "ready",
                    "blocked_reason": "none",
                    "handoff_kind": "targeted_fix_prompt_emission",
                    "action_consumable": True,
                    "manual_review_required": False,
                    "execution_allowed": False,
                    "summary": "Targeted-fix prompt emission preparation handoff is ready.",
                }
            )
    try:
        Path(handoff_path).parent.mkdir(parents=True, exist_ok=True)
        _write_json(Path(handoff_path), state)
    except OSError:
        pass
    return state

def _build_targeted_fix_post_reentry_terminal_summary_state(
    *,
    cycle_closure_result_state: Mapping[str, Any] | None,
    cycle_closure_result_path: Path,
) -> dict[str, Any]:
    result_state = (
        dict(cycle_closure_result_state)
        if isinstance(cycle_closure_result_state, Mapping)
        else {}
    )
    terminal_summary_path = _TARGETED_FIX_POST_REENTRY_TERMINAL_SUMMARY_PATH
    cycle_closure_status = _normalize_text(result_state.get("closure_status"), default="blocked")
    terminal_state = _normalize_text(result_state.get("terminal_state"), default="blocked")
    blocked_reason = _normalize_text(
        result_state.get("blocked_reason"),
        default="post_reentry_next_step_handoff_not_ready",
    )
    route_decision = _normalize_text(result_state.get("route_decision"), default="")
    final_next_action = _normalize_text(result_state.get("next_action"), default="manual_review_required")
    cycle_closed = bool(result_state.get("cycle_closed", False))
    requires_codex_reentry = bool(result_state.get("codex_reentry_required", False))
    requires_manual_review = bool(result_state.get("manual_review_required", True))
    state: dict[str, Any] = {
        "status": "blocked",
        "terminal_status": "blocked",
        "blocked_reason": blocked_reason,
        "source": "targeted_fix_post_reentry_cycle_closure_result",
        "cycle_closure_result_path": _normalize_text(
            str(cycle_closure_result_path),
            default=_TARGETED_FIX_POST_REENTRY_CYCLE_CLOSURE_RESULT_PATH,
        ),
        "terminal_summary_path": terminal_summary_path,
        "terminal_state": terminal_state,
        "cycle_closed": cycle_closed,
        "route_decision": route_decision,
        "final_next_action": final_next_action,
        "safe_to_stop": False,
        "safe_to_commit_prompt_changes": False,
        "requires_codex_reentry": requires_codex_reentry,
        "requires_manual_review": requires_manual_review,
        "summary": "Post-reentry terminal summary is blocked pending manual review.",
    }
    if cycle_closure_status == "completed" and terminal_state in {
        "completed_no_diff",
        "completed_no_action",
    }:
        state.update(
            {
                "status": "completed",
                "terminal_status": "completed",
                "blocked_reason": "none",
                "cycle_closed": True,
                "final_next_action": "none",
                "safe_to_stop": True,
                "safe_to_commit_prompt_changes": True,
                "requires_codex_reentry": False,
                "requires_manual_review": False,
                "summary": (
                    "Post-reentry cycle closure reached terminal completion with no further execution."
                ),
            }
        )
    elif cycle_closure_status == "not_applicable":
        state.update(
            {
                "status": "not_applicable",
                "terminal_status": "not_applicable",
                "safe_to_stop": False,
                "safe_to_commit_prompt_changes": False,
                "requires_codex_reentry": False,
                "requires_manual_review": False,
                "summary": "Post-reentry terminal summary is not applicable for non-cycle handoff.",
            }
        )
    try:
        Path(terminal_summary_path).parent.mkdir(parents=True, exist_ok=True)
        _write_json(Path(terminal_summary_path), state)
    except OSError:
        pass
    return state

def _build_targeted_fix_post_reentry_bounded_cycle_state(
    *,
    prompt_emission_path: Path,
    prompt_emission_receipt_path: Path,
    codex_reentry_execution_receipt_path: Path,
    diff_capture_path: Path,
    review_handoff_path: Path,
    review_assimilation_path: Path,
    route_decision_path: Path,
    route_executor_boundary_path: Path,
    next_step_handoff_path: Path,
    cycle_closure_result_path: Path,
    terminal_summary_path: Path,
    current_cycle_count: int,
    max_cycle_count: int,
    bounded_cycle_state_path: Path,
    bounded_cycle_decision_path: Path,
    bounded_cycle_receipt_path: Path,
) -> dict[str, Any]:
    def _load_payload(path: Path) -> dict[str, Any]:
        try:
            loaded = _read_json_object_if_exists(path)
        except (OSError, ValueError, json.JSONDecodeError):
            loaded = None
        return dict(loaded) if isinstance(loaded, Mapping) else {}

    prompt_emission_payload = _load_payload(prompt_emission_path)
    prompt_emission_receipt_payload = _load_payload(prompt_emission_receipt_path)
    codex_reentry_execution_payload = _load_payload(codex_reentry_execution_receipt_path)
    diff_capture_payload = _load_payload(diff_capture_path)
    review_handoff_payload = _load_payload(review_handoff_path)
    _ = _load_payload(review_assimilation_path)
    route_decision_payload = _load_payload(route_decision_path)
    route_executor_boundary_payload = _load_payload(route_executor_boundary_path)
    _ = _load_payload(next_step_handoff_path)
    _ = _load_payload(cycle_closure_result_path)
    terminal_summary_payload = _load_payload(terminal_summary_path)

    route_decision = _normalize_text(route_decision_payload.get("route_decision"), default="")
    route_status = _normalize_text(route_decision_payload.get("route_status"), default="blocked")
    targeted_fix_required = bool(route_decision_payload.get("targeted_fix_required", False))
    boundary_status = _normalize_text(
        route_executor_boundary_payload.get("boundary_status"),
        default="blocked",
    )
    executor_kind = _normalize_text(
        route_executor_boundary_payload.get("executor_kind"),
        default="manual_review",
    )
    targeted_fix_prompt_emission_allowed = bool(
        route_executor_boundary_payload.get("targeted_fix_prompt_emission_allowed", False)
    )

    prompt_emission_status = _normalize_text(
        prompt_emission_payload.get("emission_status"),
        default=_normalize_text(prompt_emission_payload.get("status"), default="not_applicable"),
    )
    prompt_emission_receipt_status = _normalize_text(
        prompt_emission_receipt_payload.get("receipt_status"),
        default="not_applicable",
    )
    prompt_emission_receipt_state_status = _normalize_text(
        prompt_emission_receipt_payload.get("status"),
        default="not_applicable",
    )
    prompt_written = bool(prompt_emission_receipt_payload.get("prompt_written", False))
    prompt_ready_for_codex_reentry = bool(
        prompt_emission_receipt_payload.get("ready_for_codex_reentry", False)
    )
    prompt_receipt_codex_reentry_executed = bool(
        prompt_emission_receipt_payload.get("codex_reentry_executed", False)
    )
    prompt_receipt_execution_performed = bool(
        prompt_emission_receipt_payload.get("execution_performed", False)
    )

    codex_reentry_execution_status = _normalize_text(
        codex_reentry_execution_payload.get("execution_status"),
        default="not_applicable",
    )
    codex_reentry_gate_status = _normalize_text(
        codex_reentry_execution_payload.get("gate_status"),
        default="not_applicable",
    )
    codex_reentry_executed = bool(codex_reentry_execution_payload.get("codex_reentry_executed", False))
    codex_reentry_execution_performed = bool(
        codex_reentry_execution_payload.get("execution_performed", False)
    )
    codex_reentry_exit_code = _as_optional_int(codex_reentry_execution_payload.get("exit_code"))

    diff_capture_status = _normalize_text(
        diff_capture_payload.get("capture_status"),
        default="not_applicable",
    )
    diff_has_diff = bool(diff_capture_payload.get("has_diff", False))
    review_handoff_status = _normalize_text(
        review_handoff_payload.get("handoff_status"),
        default="not_applicable",
    )
    review_required = bool(review_handoff_payload.get("review_required", False))

    terminal_status = _normalize_text(
        terminal_summary_payload.get("terminal_status"),
        default="not_applicable",
    )
    terminal_summary_state_status = _normalize_text(
        terminal_summary_payload.get("status"),
        default="not_applicable",
    )
    terminal_state = _normalize_text(
        terminal_summary_payload.get("terminal_state"),
        default="blocked",
    )
    terminal_cycle_closed = bool(terminal_summary_payload.get("cycle_closed", False))
    terminal_final_next_action = _normalize_text(
        terminal_summary_payload.get("final_next_action"),
        default="manual_review_required",
    )

    state: dict[str, Any] = {
        "status": "blocked",
        "cycle_status": "blocked",
        "blocked_reason": "post_reentry_bounded_cycle_inputs_incomplete",
        "source": "targeted_fix_post_reentry_bounded_cycle_controller",
        "current_cycle_count": int(current_cycle_count),
        "max_cycle_count": int(max_cycle_count),
        "cycle_closed": False,
        "bounded_cycle_complete": False,
        "should_continue": False,
        "should_emit_targeted_fix_prompt": False,
        "should_execute_codex_reentry": False,
        "should_capture_diff": False,
        "should_request_review": False,
        "should_block": True,
        "route_decision": route_decision,
        "route_status": route_status,
        "prompt_emission_status": prompt_emission_status,
        "prompt_emission_receipt_status": prompt_emission_receipt_status,
        "codex_reentry_execution_status": codex_reentry_execution_status,
        "codex_reentry_gate_status": codex_reentry_gate_status,
        "diff_capture_status": diff_capture_status,
        "review_handoff_status": review_handoff_status,
        "terminal_state": terminal_state,
        "safe_to_stop": False,
        "next_action": "manual_review_required",
        "summary": "Post-reentry bounded cycle inputs are incomplete; manual review required.",
        "targeted_fix_post_reentry_bounded_cycle_state_path": _normalize_text(
            str(bounded_cycle_state_path),
            default=_TARGETED_FIX_POST_REENTRY_BOUNDED_CYCLE_STATE_PATH,
        ),
        "targeted_fix_post_reentry_bounded_cycle_decision_path": _normalize_text(
            str(bounded_cycle_decision_path),
            default=_TARGETED_FIX_POST_REENTRY_BOUNDED_CYCLE_DECISION_PATH,
        ),
        "targeted_fix_post_reentry_bounded_cycle_receipt_path": _normalize_text(
            str(bounded_cycle_receipt_path),
            default=_TARGETED_FIX_POST_REENTRY_BOUNDED_CYCLE_RECEIPT_PATH,
        ),
    }

    terminal_completed = (
        terminal_summary_state_status == "completed"
        and terminal_status == "completed"
        and terminal_cycle_closed
        and terminal_final_next_action == "none"
    )
    diff_captured_no_diff_completed = (
        diff_capture_status == "captured_no_diff"
        and (not diff_has_diff)
        and (route_decision == "completed_no_diff" or terminal_completed)
    )
    if terminal_completed or diff_captured_no_diff_completed:
        state.update(
            {
                "status": "completed",
                "cycle_status": "completed",
                "blocked_reason": "none",
                "cycle_closed": True,
                "bounded_cycle_complete": True,
                "should_continue": False,
                "should_emit_targeted_fix_prompt": False,
                "should_execute_codex_reentry": False,
                "should_capture_diff": False,
                "should_request_review": False,
                "should_block": False,
                "safe_to_stop": True,
                "next_action": "none",
                "summary": "Post-reentry bounded cycle already terminal completed.",
            }
        )
        return state

    requires_targeted_fix_or_codex = (
        route_decision == "targeted_fix"
        or targeted_fix_required
        or (
            prompt_emission_receipt_state_status == "ready"
            and prompt_emission_receipt_status == "ready"
            and prompt_written
            and prompt_ready_for_codex_reentry
            and (not prompt_receipt_codex_reentry_executed)
            and (not prompt_receipt_execution_performed)
        )
        or (
            codex_reentry_execution_status == "completed"
            and codex_reentry_gate_status == "executed"
            and codex_reentry_executed
            and codex_reentry_execution_performed
            and codex_reentry_exit_code == 0
        )
    )
    if int(current_cycle_count) >= int(max_cycle_count) and requires_targeted_fix_or_codex:
        state.update(
            {
                "status": "blocked",
                "cycle_status": "max_cycle_count_reached",
                "blocked_reason": "max_post_reentry_targeted_fix_cycle_count_reached",
                "bounded_cycle_complete": False,
                "should_continue": False,
                "should_emit_targeted_fix_prompt": False,
                "should_execute_codex_reentry": False,
                "should_capture_diff": False,
                "should_request_review": False,
                "should_block": True,
                "safe_to_stop": False,
                "next_action": "manual_review_required_after_max_cycle_count",
                "summary": "Post-reentry targeted-fix bounded cycle reached max cycle count.",
            }
        )
        return state

    prompt_receipt_missing_or_not_ready = (
        (not prompt_emission_receipt_payload)
        or prompt_emission_receipt_status in {"not_applicable", "blocked", ""}
    )
    if (
        route_status == "ready"
        and route_decision == "targeted_fix"
        and targeted_fix_required
        and boundary_status == "ready"
        and executor_kind == "targeted_fix_prompt_emission"
        and targeted_fix_prompt_emission_allowed
        and prompt_receipt_missing_or_not_ready
    ):
        state.update(
            {
                "status": "ready",
                "cycle_status": "awaiting_prompt_emission",
                "blocked_reason": "none",
                "cycle_closed": False,
                "bounded_cycle_complete": False,
                "should_continue": True,
                "should_emit_targeted_fix_prompt": True,
                "should_execute_codex_reentry": False,
                "should_capture_diff": False,
                "should_request_review": False,
                "should_block": False,
                "safe_to_stop": False,
                "next_action": "run_prompt317_post_reentry_targeted_fix_prompt_emission",
                "summary": "Post-reentry targeted-fix route is waiting for prompt emission.",
            }
        )
        return state

    if (
        prompt_emission_receipt_state_status == "ready"
        and prompt_emission_receipt_status == "ready"
        and prompt_written
        and prompt_ready_for_codex_reentry
        and (not prompt_receipt_codex_reentry_executed)
        and (not prompt_receipt_execution_performed)
    ):
        state.update(
            {
                "status": "ready",
                "cycle_status": "awaiting_codex_reentry",
                "blocked_reason": "none",
                "cycle_closed": False,
                "bounded_cycle_complete": False,
                "should_continue": True,
                "should_emit_targeted_fix_prompt": False,
                "should_execute_codex_reentry": True,
                "should_capture_diff": False,
                "should_request_review": False,
                "should_block": False,
                "safe_to_stop": False,
                "next_action": "run_prompt318_post_reentry_targeted_fix_codex_reentry",
                "summary": "Post-reentry targeted-fix prompt is emitted and waiting for Codex reentry.",
            }
        )
        return state

    if codex_reentry_execution_status == "failed":
        state.update(
            {
                "status": "blocked",
                "cycle_status": "blocked",
                "blocked_reason": "post_reentry_codex_reentry_execution_failed",
                "cycle_closed": False,
                "bounded_cycle_complete": False,
                "should_continue": False,
                "should_emit_targeted_fix_prompt": False,
                "should_execute_codex_reentry": False,
                "should_capture_diff": False,
                "should_request_review": False,
                "should_block": True,
                "safe_to_stop": False,
                "next_action": "review_post_reentry_codex_reentry_failure",
                "summary": "Post-reentry Codex reentry execution failed and requires manual review.",
            }
        )
        return state

    if (
        codex_reentry_execution_status == "completed"
        and codex_reentry_gate_status == "executed"
        and codex_reentry_executed
        and codex_reentry_execution_performed
        and codex_reentry_exit_code == 0
    ):
        state.update(
            {
                "status": "ready",
                "cycle_status": "awaiting_post_reentry_diff_capture",
                "blocked_reason": "none",
                "cycle_closed": False,
                "bounded_cycle_complete": False,
                "should_continue": True,
                "should_emit_targeted_fix_prompt": False,
                "should_execute_codex_reentry": False,
                "should_capture_diff": True,
                "should_request_review": False,
                "should_block": False,
                "safe_to_stop": False,
                "next_action": "capture_post_reentry_diff_after_codex_reentry",
                "summary": "Post-reentry Codex reentry completed; waiting for diff capture.",
            }
        )
        return state

    if (
        diff_capture_status == "captured"
        and diff_has_diff
        and review_handoff_status == "ready"
        and review_required
    ):
        state.update(
            {
                "status": "ready",
                "cycle_status": "awaiting_post_reentry_review",
                "blocked_reason": "none",
                "cycle_closed": False,
                "bounded_cycle_complete": False,
                "should_continue": True,
                "should_emit_targeted_fix_prompt": False,
                "should_execute_codex_reentry": False,
                "should_capture_diff": False,
                "should_request_review": True,
                "should_block": False,
                "safe_to_stop": False,
                "next_action": "provide_post_reentry_review_response",
                "summary": "Post-reentry diff capture is ready and requires review response.",
            }
        )
        return state

    return state

def _build_targeted_fix_post_reentry_bounded_cycle_decision_state(
    *,
    bounded_cycle_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    state = dict(bounded_cycle_state) if isinstance(bounded_cycle_state, Mapping) else {}
    cycle_status = _normalize_text(state.get("cycle_status"), default="blocked")
    status = _normalize_text(state.get("status"), default="blocked")
    blocked_reason = _normalize_text(
        state.get("blocked_reason"),
        default="post_reentry_bounded_cycle_inputs_incomplete",
    )
    next_action = _normalize_text(state.get("next_action"), default="manual_review_required")
    decision = "blocked"
    if status == "completed" and cycle_status == "completed":
        decision = "stop_completed"
    elif status == "ready" and cycle_status == "awaiting_prompt_emission":
        decision = "emit_targeted_fix_prompt"
    elif status == "ready" and cycle_status == "awaiting_codex_reentry":
        decision = "execute_codex_reentry"
    elif status == "ready" and cycle_status == "awaiting_post_reentry_diff_capture":
        decision = "capture_post_reentry_diff"
    elif status == "ready" and cycle_status == "awaiting_post_reentry_review":
        decision = "request_review"
    elif status == "blocked" and cycle_status == "max_cycle_count_reached":
        decision = "max_cycle_count_reached"

    return {
        "status": status,
        "decision": decision,
        "blocked_reason": blocked_reason,
        "source": _normalize_text(
            state.get("source"),
            default="targeted_fix_post_reentry_bounded_cycle_state",
        ),
        "current_cycle_count": _as_non_negative_int(
            state.get("current_cycle_count"),
            default=_TARGETED_FIX_POST_REENTRY_BOUNDED_CYCLE_DEFAULT_CURRENT_CYCLE_COUNT,
        ),
        "max_cycle_count": _as_non_negative_int(
            state.get("max_cycle_count"),
            default=_TARGETED_FIX_POST_REENTRY_BOUNDED_CYCLE_DEFAULT_MAX_CYCLE_COUNT,
        ),
        "bounded_cycle_complete": bool(state.get("bounded_cycle_complete", False)),
        "safe_to_stop": bool(state.get("safe_to_stop", False)),
        "requires_manual_review": bool(state.get("should_block", False)),
        "requires_codex_reentry": bool(state.get("should_execute_codex_reentry", False)),
        "requires_prompt_emission": bool(state.get("should_emit_targeted_fix_prompt", False)),
        "requires_diff_capture": bool(state.get("should_capture_diff", False)),
        "requires_review_response": bool(state.get("should_request_review", False)),
        "next_action": next_action,
        "summary": _normalize_text(state.get("summary"), default=""),
    }

def _overlay_bounded_local_loop_local_loop_state_for_coordinator(
    *,
    local_loop_state: Mapping[str, Any] | None,
    approved_restart_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(local_loop_state) if isinstance(local_loop_state, Mapping) else {}
    approved_restart = (
        dict(approved_restart_payload) if isinstance(approved_restart_payload, Mapping) else {}
    )
    for key in _BOUNDED_LOCAL_LOOP_LOCAL_LOOP_STATE_KEYS:
        if key in approved_restart and approved_restart.get(key) is not None:
            merged[key] = approved_restart.get(key)
    return merged

def _build_default_multi_cycle_history_payload(*, max_cycles_allowed: int) -> dict[str, Any]:
    return {
        "status": "not_started",
        "max_cycles_allowed": int(max_cycles_allowed),
        "completed_cycle_count": 0,
        "current_cycle_index": 0,
        "cycles": [],
    }

def _normalize_contract_payload(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}

def _serialize_required_signals(signal_names: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in signal_names:
        text = _normalize_text(item, default="")
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized

def _normalize_selector_candidates(value: Any) -> list[str]:
    if isinstance(value, str):
        candidate = _normalize_text(value, default="")
        return [candidate] if candidate else []
    if isinstance(value, list):
        normalized: list[str] = []
        for entry in value:
            candidate = _normalize_text(entry, default="")
            if candidate:
                normalized.append(candidate)
        return normalized
    return []

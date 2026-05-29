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
    _as_optional_int,
    _normalize_string_list,
    _normalize_text,
    _read_json_object_if_exists,
)

def _build_remote_readiness_boundary_state(
    *,
    execution_repo_path: str,
    reconciliation_receipt_path: Path,
) -> dict[str, Any]:
    expected_branch = _REMOTE_READINESS_EXPECTED_BRANCH
    expected_head_tag = _REMOTE_READINESS_EXPECTED_HEAD_TAG
    normalized_repo_path = _normalize_text(
        execution_repo_path,
        default=_APPROVE_COMMIT_TAG_EXECUTION_REPO_PATH,
    )
    try:
        receipt_payload = _read_json_object_if_exists(reconciliation_receipt_path) or {}
    except (OSError, json.JSONDecodeError, ValueError):
        receipt_payload = {}

    receipt_completed = (
        _normalize_text(receipt_payload.get("status"), default="") == "completed"
        and _normalize_text(receipt_payload.get("reconciliation_status"), default="") == "completed"
        and _normalize_text(receipt_payload.get("blocked_reason"), default="") == "none"
        and bool(receipt_payload.get("already_committed", False))
        and bool(receipt_payload.get("already_tagged", False))
        and (not bool(receipt_payload.get("execution_performed", True)))
        and (not bool(receipt_payload.get("commit_performed", True)))
        and (not bool(receipt_payload.get("tag_performed", True)))
        and _normalize_text(receipt_payload.get("next_action"), default="") == "prepare_remote_readiness_boundary"
    )

    base_state: dict[str, Any] = {
        "status": "blocked",
        "boundary_status": "blocked",
        "blocked_reason": "approve_commit_tag_reconciliation_not_completed",
        "source": "remote_readiness_boundary",
        "reconciliation_receipt_path": str(reconciliation_receipt_path),
        "reconciliation_completed": bool(receipt_completed),
        "current_branch": "",
        "expected_branch": expected_branch,
        "head_short": "",
        "head_tags": [],
        "expected_head_tag": expected_head_tag,
        "expected_head_tag_present": False,
        "worktree_clean": False,
        "changed_tracked_files": [],
        "remote_configured": False,
        "remotes": [],
        "remote_verbose": [],
        "upstream_configured": False,
        "upstream_name": "none",
        "ahead_count": None,
        "behind_count": None,
        "remote_ready": False,
        "push_ready": False,
        "pr_ready": False,
        "merge_ready": False,
        "execution_allowed": False,
        "execution_performed": False,
        "push_performed": False,
        "pr_created": False,
        "merge_performed": False,
        "next_action": "complete_approve_commit_tag_reconciliation",
        "summary": "Remote readiness boundary is blocked until approve commit/tag reconciliation is completed.",
    }
    if not receipt_completed:
        return base_state

    status_short = subprocess.run(
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
    remotes_cmd = subprocess.run(
        ["git", "remote"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    remotes_verbose_cmd = subprocess.run(
        ["git", "remote", "-v"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )

    command_return_codes = (
        status_short.returncode,
        current_branch_cmd.returncode,
        head_short_cmd.returncode,
        head_tags_cmd.returncode,
        expected_head_tag_exists_cmd.returncode,
        remotes_cmd.returncode,
        remotes_verbose_cmd.returncode,
    )
    if any(code != 0 for code in command_return_codes) or (
        expected_tag_ancestor_cmd is not None and expected_tag_ancestor_cmd.returncode not in {0, 1}
    ):
        return {
            **base_state,
            "blocked_reason": "git_metadata_collection_failed",
            "next_action": "review_git_metadata_failure",
            "summary": "Remote readiness boundary is blocked because git metadata collection failed.",
        }

    changed_tracked_files = [
        line.rstrip()
        for line in (status_short.stdout or "").splitlines()
        if line.strip()
    ]
    worktree_clean = not changed_tracked_files
    current_branch = _normalize_text(current_branch_cmd.stdout, default="")
    head_short = _normalize_text(head_short_cmd.stdout, default="")
    head_tags = sorted(
        {
            line.strip()
            for line in (head_tags_cmd.stdout or "").splitlines()
            if line.strip()
        }
    )
    expected_head_tag_present = bool(
        expected_head_tag_exists and expected_head_tag_ancestor_of_head
    )
    remotes = [
        line.strip() for line in (remotes_cmd.stdout or "").splitlines() if line.strip()
    ]
    remote_verbose = [
        line.rstrip()
        for line in (remotes_verbose_cmd.stdout or "").splitlines()
        if line.strip()
    ]
    remote_configured = bool(remotes)

    upstream_name = "none"
    upstream_configured = False
    ahead_count: int | None = None
    behind_count: int | None = None
    upstream_cmd = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        text=True,
        capture_output=True,
        check=False,
        cwd=normalized_repo_path,
        shell=False,
    )
    if upstream_cmd.returncode == 0:
        upstream_name = _normalize_text(upstream_cmd.stdout, default="")
        upstream_configured = bool(upstream_name)
        if upstream_configured:
            ahead_behind_cmd = subprocess.run(
                ["git", "rev-list", "--left-right", "--count", "@{u}...HEAD"],
                text=True,
                capture_output=True,
                check=False,
                cwd=normalized_repo_path,
                shell=False,
            )
            if ahead_behind_cmd.returncode == 0:
                tokens = (ahead_behind_cmd.stdout or "").strip().split()
                if len(tokens) >= 2:
                    behind_count = _as_optional_int(tokens[0])
                    ahead_count = _as_optional_int(tokens[1])

    state = {
        **base_state,
        "reconciliation_completed": True,
        "current_branch": current_branch,
        "head_short": head_short,
        "head_tags": head_tags,
        "expected_head_tag_exists": expected_head_tag_exists,
        "expected_head_tag_ancestor_of_head": expected_head_tag_ancestor_of_head,
        "expected_head_tag_present": expected_head_tag_present,
        "worktree_clean": worktree_clean,
        "changed_tracked_files": changed_tracked_files,
        "remote_configured": remote_configured,
        "remotes": remotes,
        "remote_verbose": remote_verbose,
        "upstream_configured": upstream_configured,
        "upstream_name": upstream_name or "none",
        "ahead_count": ahead_count,
        "behind_count": behind_count,
    }

    if not worktree_clean:
        return {
            **state,
            "blocked_reason": "tracked_changes_present_before_remote_boundary",
            "next_action": "commit_or_reconcile_tracked_changes_before_remote",
            "summary": "Remote readiness boundary is blocked by tracked changes in the worktree.",
        }
    if not expected_head_tag_exists:
        return {
            **state,
            "blocked_reason": "expected_prompt321_tag_missing",
            "next_action": "tag_prompt321_before_remote_boundary",
            "summary": "Remote readiness boundary is blocked because expected Prompt321 tag is missing.",
        }
    if not expected_head_tag_ancestor_of_head:
        return {
            **state,
            "blocked_reason": "expected_prompt321_tag_not_ancestor_of_head",
            "next_action": "checkout_or_merge_history_where_prompt321_tag_is_ancestor_of_head",
            "summary": "Remote readiness boundary is blocked because expected Prompt321 tag is not an ancestor of HEAD.",
        }
    if current_branch != expected_branch:
        return {
            **state,
            "blocked_reason": "unexpected_branch_for_remote_boundary",
            "next_action": "review_branch_before_remote",
            "summary": "Remote readiness boundary is blocked because current branch differs from expected branch.",
        }
    if not remote_configured:
        return {
            **state,
            "blocked_reason": "no_git_remote_configured",
            "next_action": "configure_remote_before_push",
            "summary": "Remote readiness boundary is blocked because no git remote is configured.",
        }

    return {
        **state,
        "status": "ready",
        "boundary_status": "ready",
        "blocked_reason": "none",
        "remote_ready": True,
        "push_ready": True,
        "pr_ready": False,
        "merge_ready": False,
        "execution_allowed": False,
        "execution_performed": False,
        "push_performed": False,
        "pr_created": False,
        "merge_performed": False,
        "next_action": "prepare_remote_push_boundary",
        "summary": "Remote readiness boundary is ready; push/PR/merge execution remains disabled.",
    }

def _build_remote_readiness_plan_state(
    *,
    boundary_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    boundary = dict(boundary_state) if isinstance(boundary_state, Mapping) else {}
    remote_ready = bool(boundary.get("remote_ready", False))
    remote_configured = bool(boundary.get("remote_configured", False))
    upstream_configured = bool(boundary.get("upstream_configured", False))
    current_branch = _normalize_text(boundary.get("current_branch"), default="")
    remotes = _normalize_string_list(boundary.get("remotes"))
    upstream_name = _normalize_text(boundary.get("upstream_name"), default="")
    blocked_reason = _normalize_text(boundary.get("blocked_reason"), default="manual_review_required")
    next_action = _normalize_text(boundary.get("next_action"), default="manual_review_required")

    status = "blocked"
    plan_status = "blocked"
    push_plan_kind = "none"
    suggested_remote = "none"
    suggested_branch = "none"
    suggested_push_command = "none"
    summary = "Remote readiness plan is blocked."

    if remote_ready:
        status = "ready"
        plan_status = "ready"
        blocked_reason = "none"
        if upstream_configured:
            push_plan_kind = "push_existing_upstream"
            suggested_push_command = "git push"
            if "/" in upstream_name:
                suggested_remote = upstream_name.split("/", 1)[0].strip() or "none"
            elif remotes:
                suggested_remote = remotes[0]
            suggested_branch = current_branch or "none"
            summary = "Remote readiness plan is ready with existing upstream push."
        elif remote_configured:
            push_plan_kind = "push_set_upstream"
            suggested_remote = remotes[0] if remotes else "origin"
            suggested_branch = current_branch or "none"
            suggested_push_command = (
                f"git push -u {suggested_remote} {suggested_branch}"
                if suggested_branch != "none"
                else "none"
            )
            summary = "Remote readiness plan is ready for first push with upstream setup."
        next_action = "prepare_remote_push_boundary"

    return {
        "status": status,
        "plan_status": plan_status,
        "blocked_reason": blocked_reason,
        "source": "remote_readiness_boundary",
        "remote_ready": remote_ready,
        "push_plan_kind": push_plan_kind,
        "suggested_remote": suggested_remote,
        "suggested_branch": suggested_branch,
        "suggested_push_command": suggested_push_command,
        "pr_ready": bool(boundary.get("pr_ready", False)),
        "merge_ready": bool(boundary.get("merge_ready", False)),
        "execution_required_by": "Prompt323",
        "execution_performed": False,
        "next_action": next_action,
        "summary": summary,
    }

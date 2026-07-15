from __future__ import annotations
import json
from pathlib import Path
import subprocess
from typing import Any
from typing import Mapping
from automation.orchestration.planned_runner.project_browser.constants import (
    _PROJECT_BROWSER_AUTONOMOUS_ACTION_DUPLICATE_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_BRIDGE_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS,
    _PROJECT_BROWSER_AUTONOMOUS_MANUAL_OVERRIDE_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_SAFETY_SWITCH_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_SAFE_STOP_STATUSES,
)
from automation.orchestration.planned_runner.utils import (
    _normalize_string_list,
    _normalize_text,
    _run_git,
    _serialize_required_signals,
)

def _build_project_browser_autonomous_dispatch_state(
    *,
    autonomous_invocation_status: str,
    autonomous_invocation_permission: str,
    autonomous_invocation_action: str,
    autonomous_invocation_source_status: str,
    autonomous_invocation_block_reason: str,
    autonomous_invocation_receipt_status: str,
    autonomous_invocation_threshold_used: str,
    autonomous_invocation_task_size_status: str,
    autonomous_invocation_simple_task_status: str,
    autonomous_invocation_simple_task_gate_status: str,
    autonomous_operation_contract_status: str,
    autonomous_operation_permission: str,
    autonomous_rolling_continue_permission: str,
    autonomous_cooldown_status: str,
    autonomous_loop_risk_status: str,
    autonomous_batch_continue_permission: str,
    autonomous_multistep_budget_status: str,
    autonomous_multistep_permission: str,
    autonomous_multistep_next_step_candidate: str,
    autonomous_multistep_state: Mapping[str, Any] | None,
    autonomous_action_duplicate_status: str,
    autonomous_safety_switch_status: str,
    autonomous_manual_override_status: str,
    autonomous_safe_stop_status: str,
    autonomous_execution_permission: str,
    autonomous_execution_bridge_status: str,
    autonomous_execution_bridge_permission: str,
) -> dict[str, Any]:
    invocation_status = _normalize_text(
        autonomous_invocation_status,
        default="insufficient_truth",
    )
    invocation_permission = _normalize_text(
        autonomous_invocation_permission,
        default="insufficient_truth",
    )
    invocation_action = _normalize_text(
        autonomous_invocation_action,
        default="none",
    )
    invocation_source_status = _normalize_text(
        autonomous_invocation_source_status,
        default="insufficient_truth",
    )
    invocation_block_reason = _normalize_text(
        autonomous_invocation_block_reason,
        default="insufficient_truth",
    )
    invocation_receipt_status = _normalize_text(
        autonomous_invocation_receipt_status,
        default="insufficient_truth",
    )
    invocation_threshold_used = _normalize_text(
        autonomous_invocation_threshold_used,
        default="insufficient_truth",
    )
    invocation_task_size_status = _normalize_text(
        autonomous_invocation_task_size_status,
        default="insufficient_truth",
    )
    invocation_simple_task_status = _normalize_text(
        autonomous_invocation_simple_task_status,
        default="insufficient_truth",
    )
    invocation_simple_task_gate_status = _normalize_text(
        autonomous_invocation_simple_task_gate_status,
        default="insufficient_truth",
    )

    operation_contract_status = _normalize_text(
        autonomous_operation_contract_status,
        default="insufficient_truth",
    )
    operation_permission = _normalize_text(
        autonomous_operation_permission,
        default="insufficient_truth",
    )
    rolling_continue_permission = _normalize_text(
        autonomous_rolling_continue_permission,
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
    batch_continue_permission = _normalize_text(
        autonomous_batch_continue_permission,
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
    multistep_next_step_candidate = _normalize_text(
        autonomous_multistep_next_step_candidate,
        default="none",
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
    execution_bridge_status = _normalize_text(
        autonomous_execution_bridge_status,
        default="insufficient_truth",
    )
    execution_bridge_permission = _normalize_text(
        autonomous_execution_bridge_permission,
        default="insufficient_truth",
    )

    runtime_posture = [
        "metadata_only",
        "no_actual_next_step_start",
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
        dispatch_status: str,
        dispatch_kind: str,
        dispatch_permission: str,
        dispatch_action: str,
        source_status: str,
        risk_status: str,
        task_size_status: str,
        block_reason: str,
        receipt_status: str,
        receipt_kind: str,
    ) -> dict[str, Any]:
        return {
            "project_browser_autonomous_dispatch_status": dispatch_status,
            "project_browser_autonomous_dispatch_kind": dispatch_kind,
            "project_browser_autonomous_dispatch_permission": dispatch_permission,
            "project_browser_autonomous_dispatch_action": dispatch_action,
            "project_browser_autonomous_dispatch_source_status": source_status,
            "project_browser_autonomous_dispatch_risk_status": risk_status,
            "project_browser_autonomous_dispatch_task_size_status": task_size_status,
            "project_browser_autonomous_dispatch_block_reason": block_reason,
            "project_browser_autonomous_dispatch_receipt_status": receipt_status,
            "project_browser_autonomous_dispatch_receipt_kind": receipt_kind,
            "project_browser_autonomous_dispatch_runtime_posture": runtime_posture,
        }

    def _insufficient_truth_state(
        *,
        source_status: str,
        block_reason: str = "insufficient_truth",
    ) -> dict[str, Any]:
        normalized_source_status = (
            source_status
            if source_status in {"valid", "inconsistent", "insufficient_truth"}
            else "insufficient_truth"
        )
        normalized_block_reason = (
            block_reason
            if block_reason in {"source_inconsistent", "insufficient_truth"}
            else "insufficient_truth"
        )
        return _base_state(
            dispatch_status="insufficient_truth",
            dispatch_kind="insufficient_truth_dispatch",
            dispatch_permission="insufficient_truth",
            dispatch_action="none",
            source_status=normalized_source_status,
            risk_status="insufficient_truth",
            task_size_status="insufficient_truth",
            block_reason=normalized_block_reason,
            receipt_status="insufficient_truth",
            receipt_kind="insufficient_truth_dispatch_receipt",
        )

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

    def _map_invocation_block_reason(value: str) -> str:
        mapping = {
            "none": "none",
            "contract_not_ready": "invocation_not_ready",
            "permission_not_allowed": "permission_not_allowed",
            "score_below_no_approval_threshold": "permission_not_allowed",
            "extra_hard_gate_blocked": "permission_not_allowed",
            "simple_task_gate_blocked": "high_risk_action",
            "budget_exhausted": "budget_exhausted",
            "failure_budget_exhausted": "failure_budget_exhausted",
            "retry_budget_exhausted": "retry_budget_exhausted",
            "cooldown_required": "cooldown_required",
            "duplicate_risk": "duplicate_risk",
            "loop_suspected": "loop_suspected",
            "same_failure_repeated": "loop_suspected",
            "pause_required": "pause_required",
            "human_review_required": "human_review_required",
            "insufficient_truth": "insufficient_truth",
        }
        return mapping.get(value, "insufficient_truth")

    def _map_invocation_action(value: str) -> str:
        mapping = {
            "none": "none",
            "continue_short_batch_later": "none",
            "stop": "stop",
            "cooldown": "cooldown",
            "pause_for_login": "pause_for_login",
            "human_review": "human_review",
        }
        return mapping.get(value, "none")

    def _map_continue_candidate_to_dispatch_action(value: str) -> str:
        mapping = {
            "apply_md_update": "prepare_md_update_handoff",
            "send_next_prompt": "prepare_next_prompt_handoff",
            "retry_same_prompt": "prepare_retry_same_prompt_handoff",
            "stop": "stop",
            "pause_for_login": "pause_for_login",
            "human_review": "human_review",
            "none": "none",
        }
        return mapping.get(value, "none")

    if invocation_status not in {
        "inactive",
        "prepared",
        "blocked",
        "cooldown_required",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(source_status="insufficient_truth")
    if invocation_permission not in {
        "allowed_candidate",
        "blocked",
        "cooldown_required",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(source_status="insufficient_truth")
    if invocation_action not in {
        "none",
        "continue_short_batch_later",
        "stop",
        "cooldown",
        "pause_for_login",
        "human_review",
    }:
        return _insufficient_truth_state(source_status="insufficient_truth")
    if invocation_source_status not in {"valid", "inconsistent", "insufficient_truth"}:
        return _insufficient_truth_state(source_status="insufficient_truth")
    if invocation_block_reason not in {
        "none",
        "contract_not_ready",
        "permission_not_allowed",
        "score_below_no_approval_threshold",
        "extra_hard_gate_blocked",
        "simple_task_gate_blocked",
        "budget_exhausted",
        "failure_budget_exhausted",
        "retry_budget_exhausted",
        "cooldown_required",
        "duplicate_risk",
        "loop_suspected",
        "same_failure_repeated",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(source_status="insufficient_truth")
    if invocation_receipt_status not in {
        "not_created",
        "ready",
        "blocked",
        "cooldown_required",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(source_status="insufficient_truth")
    if invocation_threshold_used not in {
        "none",
        "standard_92",
        "simple_task_90",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(source_status="insufficient_truth")
    if invocation_task_size_status not in {
        "unknown",
        "simple_low_risk",
        "standard",
        "high_risk",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(source_status="insufficient_truth")
    if invocation_simple_task_status not in {"true", "false", "insufficient_truth"}:
        return _insufficient_truth_state(source_status="insufficient_truth")
    if invocation_simple_task_gate_status not in {"clear", "blocked", "insufficient_truth"}:
        return _insufficient_truth_state(source_status="insufficient_truth")
    if operation_contract_status not in {
        "inactive",
        "ready",
        "blocked",
        "cooldown_required",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(source_status="insufficient_truth")
    if operation_permission not in {
        "allowed_candidate",
        "blocked",
        "cooldown_required",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(source_status="insufficient_truth")
    if rolling_continue_permission not in {
        "allowed_candidate",
        "blocked",
        "cooldown_required",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(source_status="insufficient_truth")
    if cooldown_status not in {"not_required", "required", "blocked", "insufficient_truth"}:
        return _insufficient_truth_state(source_status="insufficient_truth")
    if loop_risk_status not in {"clear", "suspected", "blocked", "insufficient_truth"}:
        return _insufficient_truth_state(source_status="insufficient_truth")
    if batch_continue_permission not in {
        "allowed_candidate",
        "blocked",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(source_status="insufficient_truth")
    if multistep_budget_status not in {
        "inactive",
        "ready",
        "blocked",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(source_status="insufficient_truth")
    if multistep_permission not in _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS:
        return _insufficient_truth_state(source_status="insufficient_truth")
    if multistep_next_step_candidate not in {
        "none",
        "apply_md_update",
        "send_next_prompt",
        "retry_same_prompt",
        "pause_for_login",
        "human_review",
        "stop",
    }:
        return _insufficient_truth_state(source_status="insufficient_truth")
    if duplicate_status not in _PROJECT_BROWSER_AUTONOMOUS_ACTION_DUPLICATE_STATUSES:
        return _insufficient_truth_state(source_status="insufficient_truth")
    if safety_switch_status not in _PROJECT_BROWSER_AUTONOMOUS_SAFETY_SWITCH_STATUSES:
        return _insufficient_truth_state(source_status="insufficient_truth")
    if manual_override_status not in _PROJECT_BROWSER_AUTONOMOUS_MANUAL_OVERRIDE_STATUSES:
        return _insufficient_truth_state(source_status="insufficient_truth")
    if safe_stop_status not in _PROJECT_BROWSER_AUTONOMOUS_SAFE_STOP_STATUSES:
        return _insufficient_truth_state(source_status="insufficient_truth")
    if execution_permission not in _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS:
        return _insufficient_truth_state(source_status="insufficient_truth")
    if execution_bridge_status not in _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_BRIDGE_STATUSES:
        return _insufficient_truth_state(source_status="insufficient_truth")
    if execution_bridge_permission not in _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS:
        return _insufficient_truth_state(source_status="insufficient_truth")

    remaining_steps, remaining_steps_invalid = _read_required_non_negative_int(
        multistep_state.get("project_browser_autonomous_multistep_remaining_steps")
    )
    remaining_failures, remaining_failures_invalid = _read_required_non_negative_int(
        multistep_state.get("project_browser_autonomous_multistep_remaining_failures")
    )
    same_prompt_retry_remaining, same_prompt_retry_remaining_invalid = _read_required_non_negative_int(
        multistep_state.get("project_browser_autonomous_multistep_same_prompt_retry_remaining")
    )
    if remaining_steps_invalid or remaining_failures_invalid or same_prompt_retry_remaining_invalid:
        return _insufficient_truth_state(source_status="insufficient_truth")

    if invocation_source_status == "insufficient_truth":
        return _insufficient_truth_state(source_status="insufficient_truth")
    if invocation_source_status == "inconsistent":
        return _insufficient_truth_state(
            source_status="inconsistent",
            block_reason="source_inconsistent",
        )

    if invocation_status == "insufficient_truth":
        return _insufficient_truth_state(source_status="insufficient_truth")
    if invocation_status == "inactive":
        return _base_state(
            dispatch_status="inactive",
            dispatch_kind="none",
            dispatch_permission="blocked",
            dispatch_action="none",
            source_status="valid",
            risk_status="blocked",
            task_size_status="insufficient_truth",
            block_reason="invocation_not_ready",
            receipt_status="not_created",
            receipt_kind="none",
        )
    if invocation_status == "blocked":
        return _base_state(
            dispatch_status="blocked",
            dispatch_kind="blocked_dispatch",
            dispatch_permission="blocked",
            dispatch_action=_map_invocation_action(invocation_action),
            source_status="valid",
            risk_status="blocked",
            task_size_status=(
                invocation_task_size_status
                if invocation_task_size_status in {"simple_low_risk", "standard", "high_risk"}
                else "standard"
            ),
            block_reason=_map_invocation_block_reason(invocation_block_reason),
            receipt_status="blocked",
            receipt_kind="blocked_dispatch_receipt",
        )
    if invocation_status == "cooldown_required":
        return _base_state(
            dispatch_status="cooldown_required",
            dispatch_kind="cooldown_dispatch",
            dispatch_permission="cooldown_required",
            dispatch_action="cooldown",
            source_status="valid",
            risk_status="high",
            task_size_status="high_risk",
            block_reason="cooldown_required",
            receipt_status="cooldown_required",
            receipt_kind="cooldown_dispatch_receipt",
        )
    if invocation_status == "pause_required":
        return _base_state(
            dispatch_status="pause_required",
            dispatch_kind="pause_dispatch",
            dispatch_permission="pause_required",
            dispatch_action="pause_for_login",
            source_status="valid",
            risk_status="high",
            task_size_status="high_risk",
            block_reason="pause_required",
            receipt_status="pause_required",
            receipt_kind="pause_dispatch_receipt",
        )
    if invocation_status == "human_review_required":
        return _base_state(
            dispatch_status="human_review_required",
            dispatch_kind="human_review_dispatch",
            dispatch_permission="human_review_required",
            dispatch_action="human_review",
            source_status="valid",
            risk_status="high",
            task_size_status="high_risk",
            block_reason="human_review_required",
            receipt_status="human_review_required",
            receipt_kind="human_review_dispatch_receipt",
        )

    if invocation_status != "prepared":
        return _insufficient_truth_state(
            source_status="inconsistent",
            block_reason="source_inconsistent",
        )

    source_conflict = False
    if invocation_permission != "allowed_candidate":
        source_conflict = True
    if invocation_receipt_status != "ready":
        source_conflict = True
    if invocation_action != "continue_short_batch_later":
        source_conflict = True
    if operation_contract_status != "ready":
        source_conflict = True
    if operation_permission != "allowed_candidate":
        source_conflict = True
    if rolling_continue_permission != "allowed_candidate":
        source_conflict = True
    if batch_continue_permission != "allowed_candidate":
        source_conflict = True
    if multistep_budget_status != "ready" or multistep_permission != "allowed_candidate":
        source_conflict = True
    if remaining_steps <= 0 or remaining_failures <= 0:
        source_conflict = True
    if cooldown_status != "not_required":
        source_conflict = True
    if loop_risk_status != "clear":
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
    if any(
        token == "insufficient_truth"
        for token in (
            invocation_threshold_used,
            invocation_task_size_status,
            invocation_simple_task_status,
            invocation_simple_task_gate_status,
            duplicate_status,
            rolling_continue_permission,
            batch_continue_permission,
        )
    ):
        source_conflict = True
    if source_conflict:
        return _insufficient_truth_state(
            source_status="inconsistent",
            block_reason="source_inconsistent",
        )

    dispatch_action = _map_continue_candidate_to_dispatch_action(multistep_next_step_candidate)
    if dispatch_action == "none":
        return _base_state(
            dispatch_status="blocked",
            dispatch_kind="blocked_dispatch",
            dispatch_permission="blocked",
            dispatch_action="none",
            source_status="valid",
            risk_status="blocked",
            task_size_status="standard",
            block_reason="invocation_not_ready",
            receipt_status="blocked",
            receipt_kind="blocked_dispatch_receipt",
        )

    if duplicate_status in {
        "duplicate_action",
        "duplicate_prompt",
        "duplicate_md_update",
        "duplicate_pause",
        "duplicate_human_review",
    }:
        return _base_state(
            dispatch_status="blocked",
            dispatch_kind="blocked_dispatch",
            dispatch_permission="blocked",
            dispatch_action=dispatch_action,
            source_status="valid",
            risk_status="blocked",
            task_size_status="high_risk",
            block_reason="duplicate_risk",
            receipt_status="blocked",
            receipt_kind="blocked_dispatch_receipt",
        )

    if dispatch_action == "prepare_retry_same_prompt_handoff" and same_prompt_retry_remaining <= 0:
        return _base_state(
            dispatch_status="blocked",
            dispatch_kind="blocked_dispatch",
            dispatch_permission="blocked",
            dispatch_action=dispatch_action,
            source_status="valid",
            risk_status="blocked",
            task_size_status="high_risk",
            block_reason="retry_budget_exhausted",
            receipt_status="blocked",
            receipt_kind="blocked_dispatch_receipt",
        )

    if dispatch_action in {"stop", "cooldown", "pause_for_login", "human_review"}:
        return _base_state(
            dispatch_status="blocked",
            dispatch_kind="blocked_dispatch",
            dispatch_permission="blocked",
            dispatch_action=dispatch_action,
            source_status="valid",
            risk_status="high",
            task_size_status="high_risk",
            block_reason="high_risk_action",
            receipt_status="blocked",
            receipt_kind="blocked_dispatch_receipt",
        )

    task_size_status = "standard"
    risk_status = "standard"
    if (
        invocation_threshold_used == "simple_task_90"
        and invocation_simple_task_status == "true"
        and invocation_simple_task_gate_status == "clear"
    ):
        task_size_status = "simple_low_risk"
        risk_status = "low"
    elif invocation_task_size_status == "high_risk":
        task_size_status = "high_risk"
        risk_status = "high"
    elif invocation_task_size_status in {"simple_low_risk", "standard"}:
        task_size_status = invocation_task_size_status
        risk_status = "low" if task_size_status == "simple_low_risk" else "standard"

    if task_size_status == "high_risk" or risk_status == "high":
        return _base_state(
            dispatch_status="blocked",
            dispatch_kind="blocked_dispatch",
            dispatch_permission="blocked",
            dispatch_action=dispatch_action,
            source_status="valid",
            risk_status="high",
            task_size_status="high_risk",
            block_reason="high_risk_action",
            receipt_status="blocked",
            receipt_kind="blocked_dispatch_receipt",
        )

    return _base_state(
        dispatch_status="prepared",
        dispatch_kind="one_dispatch_candidate",
        dispatch_permission="allowed_candidate",
        dispatch_action=dispatch_action,
        source_status="valid",
        risk_status=risk_status,
        task_size_status=task_size_status,
        block_reason="none",
        receipt_status="ready",
        receipt_kind="one_dispatch_candidate_receipt",
    )

def _build_project_browser_autonomous_prompt222_n2_bridge_readiness_phase_state(
    *,
    prompt246_status: str,
    prompt246_surface_available: bool,
    prompt246_surface_authoritative: bool,
    should_prepare_prompt247: bool,
    prompt247_bridge_ready: bool,
    required_artifacts: Any,
    fresh_evidence_validity_status: str,
    fresh_evidence_validity_block_reason: str,
    fresh_evidence_validity_findings: Any,
    prompt247_bridge_block_reason: str,
    observed_outputs_available: bool,
    fresh_runtime_evidence_detected: bool,
    fresh_runtime_evidence_valid: bool,
    completed_fresh_surface_detected: bool,
    one_step_accounting_valid: bool,
    stop_policy_passed: bool,
    truth_update_allowed: bool,
    prompt222_reflection_allowed: bool,
    n2_readiness_allowed: bool,
    n2_readiness_summary_ready: bool,
) -> dict[str, Any]:
    allowed_statuses = {
        "prompt222_n2_bridge_readiness_phase_ready",
        "prompt222_n2_bridge_readiness_phase_blocked_fresh_evidence_not_valid",
        "prompt222_n2_bridge_readiness_phase_blocked_prompt246_not_ready",
        "prompt222_n2_bridge_readiness_phase_blocked_metadata_preconditions",
        "prompt222_n2_bridge_readiness_phase_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "prepare_prompt248_manual_artifact_supply_or_supplied_path_ingestion_phase",
        "manual_review_required",
        "insufficient_truth",
    }
    required_artifact_set = {
        "approved_restart_execution_contract.json",
        "run_state.json",
        "manifest.json",
    }
    forbidden_actions = [
        "prompt222_update",
        "n2_reevaluation",
        "bounded_continuation_execution",
        "read_files",
        "parse_json",
        "validate_file_existence",
        "filesystem_scan",
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
    ]

    normalized_prompt246_status = _normalize_text(prompt246_status, default="")
    normalized_required_artifacts = _normalize_string_list(required_artifacts)
    normalized_required_artifact_set = set(normalized_required_artifacts)
    required_artifacts_present = required_artifact_set.issubset(
        normalized_required_artifact_set
    )
    normalized_fresh_evidence_validity_status = _normalize_text(
        fresh_evidence_validity_status, default=""
    )
    normalized_fresh_evidence_validity_block_reason = _normalize_text(
        fresh_evidence_validity_block_reason, default=""
    )
    normalized_fresh_evidence_validity_findings = _normalize_string_list(
        fresh_evidence_validity_findings
    )
    normalized_prompt247_bridge_block_reason = _normalize_text(
        prompt247_bridge_block_reason, default=""
    )

    status = "prompt222_n2_bridge_readiness_phase_blocked_prompt246_not_ready"
    next_action = "manual_review_required"
    prompt222_bridge_ready = False
    prompt222_update_allowed_final = False
    prompt222_update_status = "blocked_prompt246_not_ready"
    prompt222_update_block_reason = "prompt246_not_ready"
    completed_fresh_surface_bridge_ready = False
    completed_fresh_surface_update_allowed = False
    completed_fresh_surface_update_status = "blocked_prompt246_not_ready"
    one_step_accounting_bridge_ready = False
    one_step_accounting_update_allowed = False
    one_step_accounting_update_status = "blocked_prompt246_not_ready"
    stop_policy_bridge_ready = False
    stop_policy_update_allowed = False
    stop_policy_update_status = "blocked_prompt246_not_ready"
    n2_readiness_summary_ready_final = False
    n2_readiness_allowed_final = False
    n2_readiness_status = "blocked_prompt246_not_ready"
    bounded_continuation_readiness_ready = False
    bounded_continuation_allowed = False
    bounded_continuation_status = "blocked_prompt246_not_ready"
    manual_artifact_supply_still_required = False
    next_manual_action = ""
    should_prepare_prompt248 = False

    authoritative_ready = bool(
        prompt246_surface_available
        and prompt246_surface_authoritative
        and should_prepare_prompt247
        and prompt247_bridge_ready
        and required_artifacts_present
        and normalized_prompt246_status
    )

    if authoritative_ready:
        prompt222_bridge_ready = True
        completed_fresh_surface_bridge_ready = True
        one_step_accounting_bridge_ready = True
        stop_policy_bridge_ready = True
        n2_readiness_summary_ready_final = bool(n2_readiness_summary_ready)
        bounded_continuation_readiness_ready = True
        manual_artifact_supply_still_required = True
        next_manual_action = "supply_explicit_fresh_runtime_artifact_paths"
        should_prepare_prompt248 = True
        next_action = "prepare_prompt248_manual_artifact_supply_or_supplied_path_ingestion_phase"

        fresh_valid = bool(fresh_runtime_evidence_valid)
        if fresh_valid:
            status = "prompt222_n2_bridge_readiness_phase_ready"
            prompt222_update_allowed_final = bool(truth_update_allowed)
            prompt222_update_status = (
                "ready_for_prompt222_update" if prompt222_update_allowed_final else "blocked_truth_update_not_allowed"
            )
            prompt222_update_block_reason = (
                "" if prompt222_update_allowed_final else "truth_update_not_allowed"
            )
            completed_fresh_surface_update_allowed = bool(completed_fresh_surface_detected)
            completed_fresh_surface_update_status = (
                "ready_for_completed_fresh_surface_update"
                if completed_fresh_surface_update_allowed
                else "blocked_completed_fresh_surface_not_detected"
            )
            one_step_accounting_update_allowed = bool(one_step_accounting_valid)
            one_step_accounting_update_status = (
                "ready_for_one_step_accounting_update"
                if one_step_accounting_update_allowed
                else "blocked_one_step_accounting_not_valid"
            )
            stop_policy_update_allowed = bool(stop_policy_passed)
            stop_policy_update_status = (
                "ready_for_stop_policy_update"
                if stop_policy_update_allowed
                else "blocked_stop_policy_not_passed"
            )
            n2_readiness_allowed_final = bool(n2_readiness_allowed)
            n2_readiness_status = (
                "ready_for_n2_readiness"
                if n2_readiness_allowed_final
                else "blocked_n2_not_allowed"
            )
            bounded_continuation_allowed = bool(n2_readiness_allowed_final)
            bounded_continuation_status = (
                "ready_for_bounded_continuation"
                if bounded_continuation_allowed
                else "blocked_n2_readiness_not_allowed"
            )
        else:
            status = "prompt222_n2_bridge_readiness_phase_blocked_fresh_evidence_not_valid"
            prompt222_update_allowed_final = False
            prompt222_update_status = "blocked_fresh_runtime_evidence_not_valid"
            prompt222_update_block_reason = (
                normalized_prompt247_bridge_block_reason
                or normalized_fresh_evidence_validity_block_reason
                or "fresh_runtime_evidence_not_valid"
            )
            completed_fresh_surface_update_allowed = False
            completed_fresh_surface_update_status = (
                "blocked_fresh_runtime_evidence_not_valid"
            )
            one_step_accounting_update_allowed = False
            one_step_accounting_update_status = (
                "blocked_fresh_runtime_evidence_not_valid"
            )
            stop_policy_update_allowed = False
            stop_policy_update_status = "blocked_fresh_runtime_evidence_not_valid"
            n2_readiness_allowed_final = False
            n2_readiness_status = "blocked_fresh_runtime_evidence_not_valid"
            bounded_continuation_allowed = False
            bounded_continuation_status = "blocked_n2_readiness_not_allowed"
    elif not normalized_prompt246_status:
        status = "prompt222_n2_bridge_readiness_phase_blocked_insufficient_truth"
        prompt222_update_status = "blocked_insufficient_truth"
        prompt222_update_block_reason = "insufficient_truth"
        completed_fresh_surface_update_status = "blocked_insufficient_truth"
        one_step_accounting_update_status = "blocked_insufficient_truth"
        stop_policy_update_status = "blocked_insufficient_truth"
        n2_readiness_status = "blocked_insufficient_truth"
        bounded_continuation_status = "blocked_insufficient_truth"

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"
    if status == "insufficient_truth":
        status = "prompt222_n2_bridge_readiness_phase_blocked_insufficient_truth"
        next_action = "manual_review_required"
        normalized_fresh_evidence_validity_status = "blocked_insufficient_truth"
        normalized_fresh_evidence_validity_block_reason = "insufficient_truth"
        normalized_fresh_evidence_validity_findings = []
        normalized_prompt247_bridge_block_reason = "insufficient_truth"
        prompt222_bridge_ready = False
        prompt222_update_allowed_final = False
        prompt222_update_status = "blocked_insufficient_truth"
        prompt222_update_block_reason = "insufficient_truth"
        completed_fresh_surface_bridge_ready = False
        completed_fresh_surface_update_allowed = False
        completed_fresh_surface_update_status = "blocked_insufficient_truth"
        one_step_accounting_bridge_ready = False
        one_step_accounting_update_allowed = False
        one_step_accounting_update_status = "blocked_insufficient_truth"
        stop_policy_bridge_ready = False
        stop_policy_update_allowed = False
        stop_policy_update_status = "blocked_insufficient_truth"
        n2_readiness_summary_ready_final = False
        n2_readiness_allowed_final = False
        n2_readiness_status = "blocked_insufficient_truth"
        bounded_continuation_readiness_ready = False
        bounded_continuation_allowed = False
        bounded_continuation_status = "blocked_insufficient_truth"
        manual_artifact_supply_still_required = False
        next_manual_action = ""
        should_prepare_prompt248 = False
        forbidden_actions = []

    return {
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_status": status,
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_source": (
            "prompt247_prompt222_n2_bridge_readiness_phase"
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_prompt246_surface_available": bool(
            prompt246_surface_available
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_prompt246_surface_authoritative": bool(
            prompt246_surface_authoritative
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_fresh_evidence_validity_status": (
            normalized_fresh_evidence_validity_status
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_fresh_evidence_validity_block_reason": (
            normalized_fresh_evidence_validity_block_reason
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_fresh_evidence_validity_findings": (
            normalized_fresh_evidence_validity_findings
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_prompt247_bridge_block_reason": (
            normalized_prompt247_bridge_block_reason
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_prompt222_bridge_ready": bool(
            prompt222_bridge_ready
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_prompt222_update_allowed": bool(
            prompt222_update_allowed_final
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_prompt222_update_status": (
            _normalize_text(prompt222_update_status, default="")
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_prompt222_update_block_reason": (
            _normalize_text(prompt222_update_block_reason, default="")
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_completed_fresh_surface_bridge_ready": bool(
            completed_fresh_surface_bridge_ready
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_completed_fresh_surface_update_allowed": bool(
            completed_fresh_surface_update_allowed
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_completed_fresh_surface_update_status": (
            _normalize_text(completed_fresh_surface_update_status, default="")
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_one_step_accounting_bridge_ready": bool(
            one_step_accounting_bridge_ready
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_one_step_accounting_update_allowed": bool(
            one_step_accounting_update_allowed
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_one_step_accounting_update_status": (
            _normalize_text(one_step_accounting_update_status, default="")
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_stop_policy_bridge_ready": bool(
            stop_policy_bridge_ready
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_stop_policy_update_allowed": bool(
            stop_policy_update_allowed
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_stop_policy_update_status": (
            _normalize_text(stop_policy_update_status, default="")
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_n2_readiness_summary_ready": bool(
            n2_readiness_summary_ready_final
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_n2_readiness_allowed": bool(
            n2_readiness_allowed_final
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_n2_readiness_status": (
            _normalize_text(n2_readiness_status, default="")
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_bounded_continuation_readiness_ready": bool(
            bounded_continuation_readiness_ready
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_bounded_continuation_allowed": bool(
            bounded_continuation_allowed
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_bounded_continuation_status": (
            _normalize_text(bounded_continuation_status, default="")
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_manual_artifact_supply_still_required": bool(
            manual_artifact_supply_still_required
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_next_manual_action": (
            _normalize_text(next_manual_action, default="")
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_forbidden_actions": (
            forbidden_actions
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_observed_outputs_available": bool(
            observed_outputs_available
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_fresh_runtime_evidence_detected": bool(
            fresh_runtime_evidence_detected
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_fresh_runtime_evidence_valid": bool(
            fresh_runtime_evidence_valid
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_completed_fresh_surface_detected": bool(
            completed_fresh_surface_detected
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_one_step_accounting_valid": bool(
            one_step_accounting_valid
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_stop_policy_passed": bool(
            stop_policy_passed
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_should_prepare_prompt248": bool(
            should_prepare_prompt248
        ),
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_should_update_prompt222": False,
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_should_re_evaluate_n2": False,
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_should_start_bounded_continuation": False,
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_should_read_files": False,
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_should_parse_json": False,
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_should_validate_file_existence": False,
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_should_scan_filesystem": False,
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_should_execute_manual_command": False,
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_should_execute_runbook": False,
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_should_execute_check_command": False,
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_should_invoke_codex": False,
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_should_execute_commit": False,
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_should_execute_rollback": False,
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_should_push": False,
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_should_start_unbounded_loop": False,
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_should_stop": True,
        "project_browser_autonomous_prompt222_n2_bridge_readiness_phase_next_action": (
            next_action
        ),
    }

def _build_project_browser_autonomous_commit_tag_execution_state_prompt276(
    *,
    commit_tag_gate_state: Mapping[str, Any] | None,
    approved_restart_payload: Mapping[str, Any] | None,
    prior_approved_restart_execution_payload: Mapping[str, Any] | None,
    execution_repo_path: str,
) -> dict[str, Any]:
    gate_state = dict(commit_tag_gate_state) if isinstance(commit_tag_gate_state, Mapping) else {}
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

    def _compact(text: Any, *, max_chars: int = 200) -> str:
        value = _normalize_text(text, default="")
        if not value:
            return ""
        normalized = " ".join(value.split())
        if len(normalized) <= max_chars:
            return normalized
        return normalized[:max_chars]

    def _is_safe_tag_name(value: str) -> bool:
        if not value:
            return False
        return all(ch.isalnum() or ch in {"-", "_", "."} for ch in value)

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

    gate_status = _normalize_text(
        gate_state.get("project_browser_autonomous_commit_tag_gate_status"),
        default="",
    )
    gate_next_action = _normalize_text(
        gate_state.get("project_browser_autonomous_commit_tag_gate_next_action"),
        default="",
    )
    gate_ready = bool(gate_state.get("project_browser_autonomous_commit_tag_gate_ready", False))
    commit_message = _compact(
        gate_state.get("project_browser_autonomous_commit_tag_gate_commit_message"),
        max_chars=200,
    )
    tag_name = _normalize_text(
        gate_state.get("project_browser_autonomous_commit_tag_gate_tag_name"),
        default="",
    )
    changed_files = _normalize_string_list(
        gate_state.get("project_browser_autonomous_commit_tag_gate_changed_files")
    )
    validation_summary = _compact(
        gate_state.get("project_browser_autonomous_commit_tag_gate_validation_summary"),
        max_chars=200,
    ).lower()
    review_summary = _compact(
        gate_state.get("project_browser_autonomous_commit_tag_gate_review_summary"),
        max_chars=200,
    )

    execution_enabled = _read_flag(
        "project_browser_autonomous_commit_tag_execution_enabled",
        default=False,
    )
    execute_enabled = _read_flag(
        "project_browser_autonomous_commit_tag_execution_execute_enabled",
        default=False,
    )

    max_changed_files = 25
    large_change_approved = False
    for key in (
        "project_browser_autonomous_commit_tag_large_change_approved",
        "project_browser_autonomous_large_change_approved",
    ):
        if key in approved_restart or key in prior_payload:
            large_change_approved = _read_flag(key, default=False)
            break

    status = "commit_tag_execution_not_requested"
    next_action = "enable_commit_tag_execution"
    blocked_reason = "execution_disabled"
    commit_sha = ""
    tag_created = False
    git_status_short = ""
    post_git_status_short = ""

    gate_ready_for_execution = bool(
        gate_status == "commit_tag_gate_ready"
        and gate_ready
        and gate_next_action == "prepare_explicit_commit_tag_execution_step"
    )

    if not execution_enabled:
        return {
            "project_browser_autonomous_commit_tag_execution_status": status,
            "project_browser_autonomous_commit_tag_execution_next_action": next_action,
            "project_browser_autonomous_commit_tag_execution_enabled": bool(execution_enabled),
            "project_browser_autonomous_commit_tag_execution_execute_enabled": bool(
                execute_enabled
            ),
            "project_browser_autonomous_commit_tag_execution_commit_message": commit_message,
            "project_browser_autonomous_commit_tag_execution_tag_name": tag_name,
            "project_browser_autonomous_commit_tag_execution_changed_files": changed_files,
            "project_browser_autonomous_commit_tag_execution_commit_sha": commit_sha,
            "project_browser_autonomous_commit_tag_execution_tag_created": bool(tag_created),
            "project_browser_autonomous_commit_tag_execution_git_status_short": git_status_short,
            "project_browser_autonomous_commit_tag_execution_post_git_status_short": (
                post_git_status_short
            ),
            "project_browser_autonomous_commit_tag_execution_blocked_reason": blocked_reason,
        }

    status = "commit_tag_execution_decision_only"
    next_action = "run_commit_tag_execution_when_explicitly_enabled"
    blocked_reason = "execute_disabled"

    if not gate_ready_for_execution:
        status = "commit_tag_execution_blocked_missing_gate"
        next_action = "manual_review_required"
        blocked_reason = "commit_tag_gate_not_ready"
        return {
            "project_browser_autonomous_commit_tag_execution_status": status,
            "project_browser_autonomous_commit_tag_execution_next_action": next_action,
            "project_browser_autonomous_commit_tag_execution_enabled": bool(execution_enabled),
            "project_browser_autonomous_commit_tag_execution_execute_enabled": bool(
                execute_enabled
            ),
            "project_browser_autonomous_commit_tag_execution_commit_message": commit_message,
            "project_browser_autonomous_commit_tag_execution_tag_name": tag_name,
            "project_browser_autonomous_commit_tag_execution_changed_files": changed_files,
            "project_browser_autonomous_commit_tag_execution_commit_sha": commit_sha,
            "project_browser_autonomous_commit_tag_execution_tag_created": bool(tag_created),
            "project_browser_autonomous_commit_tag_execution_git_status_short": git_status_short,
            "project_browser_autonomous_commit_tag_execution_post_git_status_short": (
                post_git_status_short
            ),
            "project_browser_autonomous_commit_tag_execution_blocked_reason": blocked_reason,
        }

    safe_changed_files: list[str] = []
    for path in changed_files:
        safe, normalized_or_reason = _is_safe_changed_path(path)
        if not safe:
            status = "commit_tag_execution_blocked_preflight"
            next_action = "manual_review_required"
            blocked_reason = normalized_or_reason
            return {
                "project_browser_autonomous_commit_tag_execution_status": status,
                "project_browser_autonomous_commit_tag_execution_next_action": next_action,
                "project_browser_autonomous_commit_tag_execution_enabled": bool(execution_enabled),
                "project_browser_autonomous_commit_tag_execution_execute_enabled": bool(
                    execute_enabled
                ),
                "project_browser_autonomous_commit_tag_execution_commit_message": commit_message,
                "project_browser_autonomous_commit_tag_execution_tag_name": tag_name,
                "project_browser_autonomous_commit_tag_execution_changed_files": changed_files,
                "project_browser_autonomous_commit_tag_execution_commit_sha": commit_sha,
                "project_browser_autonomous_commit_tag_execution_tag_created": bool(tag_created),
                "project_browser_autonomous_commit_tag_execution_git_status_short": git_status_short,
                "project_browser_autonomous_commit_tag_execution_post_git_status_short": (
                    post_git_status_short
                ),
                "project_browser_autonomous_commit_tag_execution_blocked_reason": blocked_reason,
            }
        safe_changed_files.append(normalized_or_reason)
    safe_changed_files = _normalize_string_list(safe_changed_files)

    if len(safe_changed_files) > max_changed_files and not large_change_approved:
        status = "commit_tag_execution_blocked_large_change"
        next_action = "manual_review_required"
        blocked_reason = "changed_file_count_exceeds_limit"
        return {
            "project_browser_autonomous_commit_tag_execution_status": status,
            "project_browser_autonomous_commit_tag_execution_next_action": next_action,
            "project_browser_autonomous_commit_tag_execution_enabled": bool(execution_enabled),
            "project_browser_autonomous_commit_tag_execution_execute_enabled": bool(
                execute_enabled
            ),
            "project_browser_autonomous_commit_tag_execution_commit_message": commit_message,
            "project_browser_autonomous_commit_tag_execution_tag_name": tag_name,
            "project_browser_autonomous_commit_tag_execution_changed_files": safe_changed_files,
            "project_browser_autonomous_commit_tag_execution_commit_sha": commit_sha,
            "project_browser_autonomous_commit_tag_execution_tag_created": bool(tag_created),
            "project_browser_autonomous_commit_tag_execution_git_status_short": git_status_short,
            "project_browser_autonomous_commit_tag_execution_post_git_status_short": (
                post_git_status_short
            ),
            "project_browser_autonomous_commit_tag_execution_blocked_reason": blocked_reason,
        }

    validation_missing_or_failing = (
        not validation_summary
        or "not_available" in validation_summary
        or "unavailable" in validation_summary
        or "missing" in validation_summary
        or "error" in validation_summary
        or "failed" in validation_summary
        or "failure" in validation_summary
        or "diff_check_has_errors" in validation_summary
    )
    if validation_missing_or_failing:
        status = "commit_tag_execution_blocked_preflight"
        next_action = "manual_review_required"
        blocked_reason = "validation_missing_or_failing"
        return {
            "project_browser_autonomous_commit_tag_execution_status": status,
            "project_browser_autonomous_commit_tag_execution_next_action": next_action,
            "project_browser_autonomous_commit_tag_execution_enabled": bool(execution_enabled),
            "project_browser_autonomous_commit_tag_execution_execute_enabled": bool(
                execute_enabled
            ),
            "project_browser_autonomous_commit_tag_execution_commit_message": commit_message,
            "project_browser_autonomous_commit_tag_execution_tag_name": tag_name,
            "project_browser_autonomous_commit_tag_execution_changed_files": safe_changed_files,
            "project_browser_autonomous_commit_tag_execution_commit_sha": commit_sha,
            "project_browser_autonomous_commit_tag_execution_tag_created": bool(tag_created),
            "project_browser_autonomous_commit_tag_execution_git_status_short": git_status_short,
            "project_browser_autonomous_commit_tag_execution_post_git_status_short": (
                post_git_status_short
            ),
            "project_browser_autonomous_commit_tag_execution_blocked_reason": blocked_reason,
        }

    if not commit_message or len(commit_message) > 200 or "\n" in commit_message:
        status = "commit_tag_execution_blocked_preflight"
        next_action = "manual_review_required"
        blocked_reason = "invalid_commit_message"
        return {
            "project_browser_autonomous_commit_tag_execution_status": status,
            "project_browser_autonomous_commit_tag_execution_next_action": next_action,
            "project_browser_autonomous_commit_tag_execution_enabled": bool(execution_enabled),
            "project_browser_autonomous_commit_tag_execution_execute_enabled": bool(
                execute_enabled
            ),
            "project_browser_autonomous_commit_tag_execution_commit_message": commit_message,
            "project_browser_autonomous_commit_tag_execution_tag_name": tag_name,
            "project_browser_autonomous_commit_tag_execution_changed_files": safe_changed_files,
            "project_browser_autonomous_commit_tag_execution_commit_sha": commit_sha,
            "project_browser_autonomous_commit_tag_execution_tag_created": bool(tag_created),
            "project_browser_autonomous_commit_tag_execution_git_status_short": git_status_short,
            "project_browser_autonomous_commit_tag_execution_post_git_status_short": (
                post_git_status_short
            ),
            "project_browser_autonomous_commit_tag_execution_blocked_reason": blocked_reason,
        }
    if not _is_safe_tag_name(tag_name):
        status = "commit_tag_execution_blocked_preflight"
        next_action = "manual_review_required"
        blocked_reason = "invalid_tag_name"
        return {
            "project_browser_autonomous_commit_tag_execution_status": status,
            "project_browser_autonomous_commit_tag_execution_next_action": next_action,
            "project_browser_autonomous_commit_tag_execution_enabled": bool(execution_enabled),
            "project_browser_autonomous_commit_tag_execution_execute_enabled": bool(
                execute_enabled
            ),
            "project_browser_autonomous_commit_tag_execution_commit_message": commit_message,
            "project_browser_autonomous_commit_tag_execution_tag_name": tag_name,
            "project_browser_autonomous_commit_tag_execution_changed_files": safe_changed_files,
            "project_browser_autonomous_commit_tag_execution_commit_sha": commit_sha,
            "project_browser_autonomous_commit_tag_execution_tag_created": bool(tag_created),
            "project_browser_autonomous_commit_tag_execution_git_status_short": git_status_short,
            "project_browser_autonomous_commit_tag_execution_post_git_status_short": (
                post_git_status_short
            ),
            "project_browser_autonomous_commit_tag_execution_blocked_reason": blocked_reason,
        }
    if not safe_changed_files:
        status = "commit_tag_execution_blocked_preflight"
        next_action = "manual_review_required"
        blocked_reason = "missing_changed_files"
        return {
            "project_browser_autonomous_commit_tag_execution_status": status,
            "project_browser_autonomous_commit_tag_execution_next_action": next_action,
            "project_browser_autonomous_commit_tag_execution_enabled": bool(execution_enabled),
            "project_browser_autonomous_commit_tag_execution_execute_enabled": bool(
                execute_enabled
            ),
            "project_browser_autonomous_commit_tag_execution_commit_message": commit_message,
            "project_browser_autonomous_commit_tag_execution_tag_name": tag_name,
            "project_browser_autonomous_commit_tag_execution_changed_files": safe_changed_files,
            "project_browser_autonomous_commit_tag_execution_commit_sha": commit_sha,
            "project_browser_autonomous_commit_tag_execution_tag_created": bool(tag_created),
            "project_browser_autonomous_commit_tag_execution_git_status_short": git_status_short,
            "project_browser_autonomous_commit_tag_execution_post_git_status_short": (
                post_git_status_short
            ),
            "project_browser_autonomous_commit_tag_execution_blocked_reason": blocked_reason,
        }

    if not execute_enabled:
        status = "commit_tag_execution_decision_only"
        next_action = "set_execute_enabled_to_run_local_commit_tag"
        blocked_reason = "execution_not_enabled"
        return {
            "project_browser_autonomous_commit_tag_execution_status": status,
            "project_browser_autonomous_commit_tag_execution_next_action": next_action,
            "project_browser_autonomous_commit_tag_execution_enabled": bool(execution_enabled),
            "project_browser_autonomous_commit_tag_execution_execute_enabled": bool(
                execute_enabled
            ),
            "project_browser_autonomous_commit_tag_execution_commit_message": commit_message,
            "project_browser_autonomous_commit_tag_execution_tag_name": tag_name,
            "project_browser_autonomous_commit_tag_execution_changed_files": safe_changed_files,
            "project_browser_autonomous_commit_tag_execution_commit_sha": commit_sha,
            "project_browser_autonomous_commit_tag_execution_tag_created": bool(tag_created),
            "project_browser_autonomous_commit_tag_execution_git_status_short": git_status_short,
            "project_browser_autonomous_commit_tag_execution_post_git_status_short": (
                post_git_status_short
            ),
            "project_browser_autonomous_commit_tag_execution_blocked_reason": blocked_reason,
        }

    repo_path_text = _normalize_text(execution_repo_path, default="")
    repo_path_obj = Path(repo_path_text) if repo_path_text else Path.cwd()
    if not repo_path_obj.exists() or not repo_path_obj.is_dir():
        status = "commit_tag_execution_blocked_preflight"
        next_action = "manual_review_required"
        blocked_reason = "execution_repo_unavailable"
        return {
            "project_browser_autonomous_commit_tag_execution_status": status,
            "project_browser_autonomous_commit_tag_execution_next_action": next_action,
            "project_browser_autonomous_commit_tag_execution_enabled": bool(execution_enabled),
            "project_browser_autonomous_commit_tag_execution_execute_enabled": bool(
                execute_enabled
            ),
            "project_browser_autonomous_commit_tag_execution_commit_message": commit_message,
            "project_browser_autonomous_commit_tag_execution_tag_name": tag_name,
            "project_browser_autonomous_commit_tag_execution_changed_files": safe_changed_files,
            "project_browser_autonomous_commit_tag_execution_commit_sha": commit_sha,
            "project_browser_autonomous_commit_tag_execution_tag_created": bool(tag_created),
            "project_browser_autonomous_commit_tag_execution_git_status_short": git_status_short,
            "project_browser_autonomous_commit_tag_execution_post_git_status_short": (
                post_git_status_short
            ),
            "project_browser_autonomous_commit_tag_execution_blocked_reason": blocked_reason,
        }

    try:
        pre_status_run = subprocess.run(
            ["git", "status", "--short"],
            cwd=str(repo_path_obj),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        status = "commit_tag_execution_blocked_git_failed"
        next_action = "manual_review_required"
        blocked_reason = "git_status_failed"
        return {
            "project_browser_autonomous_commit_tag_execution_status": status,
            "project_browser_autonomous_commit_tag_execution_next_action": next_action,
            "project_browser_autonomous_commit_tag_execution_enabled": bool(execution_enabled),
            "project_browser_autonomous_commit_tag_execution_execute_enabled": bool(
                execute_enabled
            ),
            "project_browser_autonomous_commit_tag_execution_commit_message": commit_message,
            "project_browser_autonomous_commit_tag_execution_tag_name": tag_name,
            "project_browser_autonomous_commit_tag_execution_changed_files": safe_changed_files,
            "project_browser_autonomous_commit_tag_execution_commit_sha": commit_sha,
            "project_browser_autonomous_commit_tag_execution_tag_created": bool(tag_created),
            "project_browser_autonomous_commit_tag_execution_git_status_short": git_status_short,
            "project_browser_autonomous_commit_tag_execution_post_git_status_short": (
                post_git_status_short
            ),
            "project_browser_autonomous_commit_tag_execution_blocked_reason": blocked_reason,
        }
    git_status_short = _compact(pre_status_run.stdout, max_chars=4000)
    if int(pre_status_run.returncode) != 0:
        status = "commit_tag_execution_blocked_git_failed"
        next_action = "manual_review_required"
        blocked_reason = "git_status_nonzero_exit"
        return {
            "project_browser_autonomous_commit_tag_execution_status": status,
            "project_browser_autonomous_commit_tag_execution_next_action": next_action,
            "project_browser_autonomous_commit_tag_execution_enabled": bool(execution_enabled),
            "project_browser_autonomous_commit_tag_execution_execute_enabled": bool(
                execute_enabled
            ),
            "project_browser_autonomous_commit_tag_execution_commit_message": commit_message,
            "project_browser_autonomous_commit_tag_execution_tag_name": tag_name,
            "project_browser_autonomous_commit_tag_execution_changed_files": safe_changed_files,
            "project_browser_autonomous_commit_tag_execution_commit_sha": commit_sha,
            "project_browser_autonomous_commit_tag_execution_tag_created": bool(tag_created),
            "project_browser_autonomous_commit_tag_execution_git_status_short": git_status_short,
            "project_browser_autonomous_commit_tag_execution_post_git_status_short": (
                post_git_status_short
            ),
            "project_browser_autonomous_commit_tag_execution_blocked_reason": blocked_reason,
        }

    parsed_status, ambiguous_status = _parse_git_status_short(pre_status_run.stdout)
    if ambiguous_status:
        status = "commit_tag_execution_blocked_preflight"
        next_action = "manual_review_required"
        blocked_reason = ambiguous_status[0]
        return {
            "project_browser_autonomous_commit_tag_execution_status": status,
            "project_browser_autonomous_commit_tag_execution_next_action": next_action,
            "project_browser_autonomous_commit_tag_execution_enabled": bool(execution_enabled),
            "project_browser_autonomous_commit_tag_execution_execute_enabled": bool(
                execute_enabled
            ),
            "project_browser_autonomous_commit_tag_execution_commit_message": commit_message,
            "project_browser_autonomous_commit_tag_execution_tag_name": tag_name,
            "project_browser_autonomous_commit_tag_execution_changed_files": safe_changed_files,
            "project_browser_autonomous_commit_tag_execution_commit_sha": commit_sha,
            "project_browser_autonomous_commit_tag_execution_tag_created": bool(tag_created),
            "project_browser_autonomous_commit_tag_execution_git_status_short": git_status_short,
            "project_browser_autonomous_commit_tag_execution_post_git_status_short": (
                post_git_status_short
            ),
            "project_browser_autonomous_commit_tag_execution_blocked_reason": blocked_reason,
        }

    expected_set = set(safe_changed_files)
    seen_set = set(parsed_status.keys())
    if not expected_set.issubset(seen_set):
        status = "commit_tag_execution_blocked_preflight"
        next_action = "manual_review_required"
        missing = sorted(expected_set - seen_set)
        blocked_reason = f"expected_files_missing_from_git_status:{','.join(missing[:5])}"
        return {
            "project_browser_autonomous_commit_tag_execution_status": status,
            "project_browser_autonomous_commit_tag_execution_next_action": next_action,
            "project_browser_autonomous_commit_tag_execution_enabled": bool(execution_enabled),
            "project_browser_autonomous_commit_tag_execution_execute_enabled": bool(
                execute_enabled
            ),
            "project_browser_autonomous_commit_tag_execution_commit_message": commit_message,
            "project_browser_autonomous_commit_tag_execution_tag_name": tag_name,
            "project_browser_autonomous_commit_tag_execution_changed_files": safe_changed_files,
            "project_browser_autonomous_commit_tag_execution_commit_sha": commit_sha,
            "project_browser_autonomous_commit_tag_execution_tag_created": bool(tag_created),
            "project_browser_autonomous_commit_tag_execution_git_status_short": git_status_short,
            "project_browser_autonomous_commit_tag_execution_post_git_status_short": (
                post_git_status_short
            ),
            "project_browser_autonomous_commit_tag_execution_blocked_reason": blocked_reason,
        }
    extras = sorted(seen_set - expected_set)
    if extras:
        status = "commit_tag_execution_blocked_unexpected_changes"
        next_action = "manual_review_required"
        blocked_reason = f"unexpected_changed_files:{','.join(extras[:5])}"
        return {
            "project_browser_autonomous_commit_tag_execution_status": status,
            "project_browser_autonomous_commit_tag_execution_next_action": next_action,
            "project_browser_autonomous_commit_tag_execution_enabled": bool(execution_enabled),
            "project_browser_autonomous_commit_tag_execution_execute_enabled": bool(
                execute_enabled
            ),
            "project_browser_autonomous_commit_tag_execution_commit_message": commit_message,
            "project_browser_autonomous_commit_tag_execution_tag_name": tag_name,
            "project_browser_autonomous_commit_tag_execution_changed_files": safe_changed_files,
            "project_browser_autonomous_commit_tag_execution_commit_sha": commit_sha,
            "project_browser_autonomous_commit_tag_execution_tag_created": bool(tag_created),
            "project_browser_autonomous_commit_tag_execution_git_status_short": git_status_short,
            "project_browser_autonomous_commit_tag_execution_post_git_status_short": (
                post_git_status_short
            ),
            "project_browser_autonomous_commit_tag_execution_blocked_reason": blocked_reason,
        }

    try:
        tag_check_run = subprocess.run(
            ["git", "tag", "--list", tag_name],
            cwd=str(repo_path_obj),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        status = "commit_tag_execution_blocked_git_failed"
        next_action = "manual_review_required"
        blocked_reason = "git_tag_list_failed"
        return {
            "project_browser_autonomous_commit_tag_execution_status": status,
            "project_browser_autonomous_commit_tag_execution_next_action": next_action,
            "project_browser_autonomous_commit_tag_execution_enabled": bool(execution_enabled),
            "project_browser_autonomous_commit_tag_execution_execute_enabled": bool(
                execute_enabled
            ),
            "project_browser_autonomous_commit_tag_execution_commit_message": commit_message,
            "project_browser_autonomous_commit_tag_execution_tag_name": tag_name,
            "project_browser_autonomous_commit_tag_execution_changed_files": safe_changed_files,
            "project_browser_autonomous_commit_tag_execution_commit_sha": commit_sha,
            "project_browser_autonomous_commit_tag_execution_tag_created": bool(tag_created),
            "project_browser_autonomous_commit_tag_execution_git_status_short": git_status_short,
            "project_browser_autonomous_commit_tag_execution_post_git_status_short": (
                post_git_status_short
            ),
            "project_browser_autonomous_commit_tag_execution_blocked_reason": blocked_reason,
        }
    if int(tag_check_run.returncode) != 0:
        status = "commit_tag_execution_blocked_git_failed"
        next_action = "manual_review_required"
        blocked_reason = "git_tag_list_nonzero_exit"
        return {
            "project_browser_autonomous_commit_tag_execution_status": status,
            "project_browser_autonomous_commit_tag_execution_next_action": next_action,
            "project_browser_autonomous_commit_tag_execution_enabled": bool(execution_enabled),
            "project_browser_autonomous_commit_tag_execution_execute_enabled": bool(
                execute_enabled
            ),
            "project_browser_autonomous_commit_tag_execution_commit_message": commit_message,
            "project_browser_autonomous_commit_tag_execution_tag_name": tag_name,
            "project_browser_autonomous_commit_tag_execution_changed_files": safe_changed_files,
            "project_browser_autonomous_commit_tag_execution_commit_sha": commit_sha,
            "project_browser_autonomous_commit_tag_execution_tag_created": bool(tag_created),
            "project_browser_autonomous_commit_tag_execution_git_status_short": git_status_short,
            "project_browser_autonomous_commit_tag_execution_post_git_status_short": (
                post_git_status_short
            ),
            "project_browser_autonomous_commit_tag_execution_blocked_reason": blocked_reason,
        }
    if _normalize_text(tag_check_run.stdout, default=""):
        status = "commit_tag_execution_blocked_existing_tag"
        next_action = "manual_review_required"
        blocked_reason = "tag_already_exists"
        return {
            "project_browser_autonomous_commit_tag_execution_status": status,
            "project_browser_autonomous_commit_tag_execution_next_action": next_action,
            "project_browser_autonomous_commit_tag_execution_enabled": bool(execution_enabled),
            "project_browser_autonomous_commit_tag_execution_execute_enabled": bool(
                execute_enabled
            ),
            "project_browser_autonomous_commit_tag_execution_commit_message": commit_message,
            "project_browser_autonomous_commit_tag_execution_tag_name": tag_name,
            "project_browser_autonomous_commit_tag_execution_changed_files": safe_changed_files,
            "project_browser_autonomous_commit_tag_execution_commit_sha": commit_sha,
            "project_browser_autonomous_commit_tag_execution_tag_created": bool(tag_created),
            "project_browser_autonomous_commit_tag_execution_git_status_short": git_status_short,
            "project_browser_autonomous_commit_tag_execution_post_git_status_short": (
                post_git_status_short
            ),
            "project_browser_autonomous_commit_tag_execution_blocked_reason": blocked_reason,
        }

    commit_attempted = False
    try:
        add_run = subprocess.run(
            ["git", "add", "--", *safe_changed_files],
            cwd=str(repo_path_obj),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        status = "commit_tag_execution_blocked_git_failed"
        next_action = "manual_review_required"
        blocked_reason = "git_add_failed"
    else:
        if int(add_run.returncode) != 0:
            status = "commit_tag_execution_blocked_git_failed"
            next_action = "manual_review_required"
            blocked_reason = "git_add_nonzero_exit"
        else:
            commit_attempted = True
            try:
                commit_run = subprocess.run(
                    ["git", "commit", "-m", commit_message],
                    cwd=str(repo_path_obj),
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,
                )
            except (OSError, subprocess.SubprocessError):
                status = "commit_tag_execution_blocked_git_failed"
                next_action = "manual_review_required"
                blocked_reason = "git_commit_failed"
            else:
                if int(commit_run.returncode) != 0:
                    status = "commit_tag_execution_blocked_git_failed"
                    next_action = "manual_review_required"
                    blocked_reason = "git_commit_nonzero_exit"
                else:
                    try:
                        sha_run = subprocess.run(
                            ["git", "rev-parse", "HEAD"],
                            cwd=str(repo_path_obj),
                            capture_output=True,
                            text=True,
                            timeout=30,
                            check=False,
                        )
                    except (OSError, subprocess.SubprocessError):
                        status = "commit_tag_execution_blocked_git_failed"
                        next_action = "manual_review_required"
                        blocked_reason = "git_rev_parse_failed"
                    else:
                        if int(sha_run.returncode) != 0:
                            status = "commit_tag_execution_blocked_git_failed"
                            next_action = "manual_review_required"
                            blocked_reason = "git_rev_parse_nonzero_exit"
                        else:
                            commit_sha = _normalize_text(sha_run.stdout, default="")
                            tag_message = _compact(
                                f"Prompt276 local tag: {review_summary or commit_message}",
                                max_chars=200,
                            )
                            try:
                                tag_run = subprocess.run(
                                    ["git", "tag", "-a", tag_name, "-m", tag_message],
                                    cwd=str(repo_path_obj),
                                    capture_output=True,
                                    text=True,
                                    timeout=60,
                                    check=False,
                                )
                            except (OSError, subprocess.SubprocessError):
                                status = "commit_tag_execution_committed_tag_failed"
                                next_action = "manual_review_required"
                                blocked_reason = "git_tag_failed"
                            else:
                                if int(tag_run.returncode) != 0:
                                    status = "commit_tag_execution_committed_tag_failed"
                                    next_action = "manual_review_required"
                                    blocked_reason = "git_tag_nonzero_exit"
                                else:
                                    status = "commit_tag_execution_committed_and_tagged"
                                    next_action = "update_pr_queue_or_prepare_next_pr"
                                    blocked_reason = "none"
                                    tag_created = True
    if commit_attempted:
        try:
            post_status_run = subprocess.run(
                ["git", "status", "--short"],
                cwd=str(repo_path_obj),
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            post_git_status_short = ""
        else:
            post_git_status_short = _compact(post_status_run.stdout, max_chars=4000)
            if (
                status == "commit_tag_execution_committed_and_tagged"
                and _normalize_text(post_status_run.stdout, default="")
            ):
                parsed_post, ambiguous_post = _parse_git_status_short(post_status_run.stdout)
                if ambiguous_post:
                    status = "commit_tag_execution_blocked_preflight"
                    next_action = "manual_review_required"
                    blocked_reason = ambiguous_post[0]
                else:
                    remaining = set(parsed_post.keys())
                    if remaining.intersection(set(safe_changed_files)):
                        status = "commit_tag_execution_blocked_preflight"
                        next_action = "manual_review_required"
                        blocked_reason = "post_status_not_clean_for_expected_files"

    return {
        "project_browser_autonomous_commit_tag_execution_status": status,
        "project_browser_autonomous_commit_tag_execution_next_action": next_action,
        "project_browser_autonomous_commit_tag_execution_enabled": bool(execution_enabled),
        "project_browser_autonomous_commit_tag_execution_execute_enabled": bool(
            execute_enabled
        ),
        "project_browser_autonomous_commit_tag_execution_commit_message": commit_message,
        "project_browser_autonomous_commit_tag_execution_tag_name": tag_name,
        "project_browser_autonomous_commit_tag_execution_changed_files": safe_changed_files,
        "project_browser_autonomous_commit_tag_execution_commit_sha": commit_sha,
        "project_browser_autonomous_commit_tag_execution_tag_created": bool(tag_created),
        "project_browser_autonomous_commit_tag_execution_git_status_short": git_status_short,
        "project_browser_autonomous_commit_tag_execution_post_git_status_short": (
            post_git_status_short
        ),
        "project_browser_autonomous_commit_tag_execution_blocked_reason": blocked_reason,
    }

def _build_project_browser_autonomous_chatgpt_diff_review_route_state() -> dict[str, Any]:
    response_dir = Path("/tmp/codex-local-runner-decision/chatgpt_diff_review_response")
    route_dir = Path("/tmp/codex-local-runner-decision/chatgpt_diff_review_route")
    review_decision_path = response_dir / "review_decision.json"
    route_decision_path = route_dir / "review_route_decision.json"
    route_summary_path = route_dir / "review_route_summary.md"
    artifact_paths = {
        "expected_review_decision_json": str(review_decision_path),
        "review_route_decision_json": str(route_decision_path),
        "review_route_summary_md": str(route_summary_path),
    }

    status = "blocked_missing_review_decision"
    next_action = "wait_for_chatgpt_diff_review_response"
    selected_route = "none"
    decision = "manual_review"
    confidence = "low"
    safe_to_commit = False
    requires_fix = False
    requires_revert = False
    blocked_reason = "missing_review_decision"
    safety_downgrades: list[str] = []
    probe_file_path = "tmp_runner_live_write_probe.txt"
    probe_file_present = False
    probe_file_classification = "unknown"
    probe_file_approve_guard = "not_applicable"
    runtime_posture = [
        "metadata_only_route_preparation",
        "no_codex_invocation",
        "no_commit_or_tag_execution",
        "no_push_or_pr_or_merge",
        "authoritative_probe_file_guard",
    ]

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

    parsed: Mapping[str, Any] | None = None
    if review_decision_path.exists():
        try:
            loaded = json.loads(review_decision_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            blocked_reason = "invalid_review_decision_json"
            safety_downgrades.append("invalid_review_decision_json_downgraded_to_manual_review")
        else:
            if isinstance(loaded, Mapping):
                parsed = loaded
            else:
                blocked_reason = "review_decision_not_object"
                safety_downgrades.append("review_decision_not_object_downgraded_to_manual_review")
    else:
        blocked_reason = "missing_review_decision"

    authoritative_changed_files_path = Path(
        "/tmp/codex-local-runner-decision/local_git_diff_capture/changed_files.json"
    )
    review_request_json_path = Path(
        "/tmp/codex-local-runner-decision/chatgpt_diff_review_request/chatgpt_review_request.json"
    )
    authoritative_probe_detection_available = False
    if authoritative_changed_files_path.exists():
        try:
            changed_files_payload = json.loads(
                authoritative_changed_files_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            changed_files_payload = None
        if isinstance(changed_files_payload, Mapping):
            authoritative_probe_detection_available = True
            changed_files_list = _normalize_string_list(
                changed_files_payload.get("changed_files")
            )
            if probe_file_path in changed_files_list:
                probe_file_present = True
                probe_file_classification = "probe_disposable_local_change"
            payload_entries = changed_files_payload.get("changed_files")
            if isinstance(payload_entries, list):
                for entry in payload_entries:
                    if isinstance(entry, Mapping):
                        if _normalize_text(entry.get("path"), default="") != probe_file_path:
                            continue
                        probe_file_present = True
                        # Local diff capture is authoritative; normalize probe tagging to disposable.
                        probe_file_classification = "probe_disposable_local_change"
                        break
                    if _normalize_text(entry, default="") == probe_file_path:
                        probe_file_present = True
                        probe_file_classification = "probe_disposable_local_change"
                        break
    if review_request_json_path.exists():
        try:
            review_request_payload = json.loads(
                review_request_json_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            review_request_payload = None
        if isinstance(review_request_payload, Mapping):
            request_probe_classification = _normalize_text(
                review_request_payload.get("tmp_runner_live_write_probe_classification"),
                default="",
            ).lower()
            if request_probe_classification or "changed_files" in review_request_payload:
                authoritative_probe_detection_available = True
            if request_probe_classification:
                probe_file_classification = request_probe_classification
            if request_probe_classification == "probe_disposable_local_change":
                probe_file_present = True
            request_changed_files = _normalize_string_list(
                review_request_payload.get("changed_files")
            )
            if probe_file_path in request_changed_files:
                probe_file_present = True

    if isinstance(parsed, Mapping):
        decision = _normalize_decision(parsed.get("decision"))
        confidence = _normalize_confidence(parsed.get("confidence"))
        safe_to_commit = _coerce_bool(parsed.get("safe_to_commit"), default=False)
        requires_fix = _coerce_bool(parsed.get("requires_fix"), default=False)
        requires_revert = _coerce_bool(parsed.get("requires_revert"), default=False)

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
            contradictory = True
            safety_downgrades.append("low_confidence_downgraded_to_manual_review")
        approve_candidate = bool(
            decision == "approve"
            and safe_to_commit
            and not requires_fix
            and not requires_revert
            and confidence in {"high", "medium"}
        )
        if approve_candidate and not authoritative_probe_detection_available:
            status = "blocked_missing_authoritative_probe_signal"
            selected_route = "none"
            next_action = "wait_for_chatgpt_diff_review_response"
            blocked_reason = "authoritative_probe_detection_unavailable"
            probe_file_approve_guard = "blocked_missing_authoritative_probe_signal"
        elif decision == "approve" and probe_file_present:
            contradictory = True
            safety_downgrades.append(
                "probe_file_present_requires_exclusion_before_approve"
            )
            probe_file_approve_guard = "blocked_probe_file_present_manual_exclusion_required"
        elif decision == "approve":
            probe_file_approve_guard = "passed"

        if status == "blocked_missing_authoritative_probe_signal":
            pass
        elif contradictory or decision == "manual_review":
            selected_route = "manual_review"
            next_action = "manual_review_required"
            status = (
                "chatgpt_diff_review_route_completed_with_downgrade"
                if safety_downgrades
                else "chatgpt_diff_review_route_completed"
            )
            blocked_reason = (
                "manual_review_required_by_safety"
                if safety_downgrades
                else "manual_review_decision"
            )
        elif decision == "approve":
            if (
                safe_to_commit
                and not requires_fix
                and not requires_revert
                and confidence in {"high", "medium"}
            ):
                selected_route = "approve"
                next_action = "prepare_commit_tag_readiness"
                status = "chatgpt_diff_review_route_completed"
                blocked_reason = "none"
                if probe_file_approve_guard == "not_applicable":
                    probe_file_approve_guard = "passed"
            else:
                selected_route = "manual_review"
                next_action = "manual_review_required"
                status = "chatgpt_diff_review_route_completed_with_downgrade"
                blocked_reason = "unsafe_approve"
                safety_downgrades.append("unsafe_approve_downgraded_to_manual_review")
        elif decision == "fix":
            selected_route = "fix"
            next_action = "prepare_codex_fix_prompt"
            status = "chatgpt_diff_review_route_completed"
            blocked_reason = "none"
        elif decision == "revert" or requires_revert:
            selected_route = "revert"
            next_action = "prepare_safe_revert_route"
            status = "chatgpt_diff_review_route_completed"
            blocked_reason = "none"
        else:
            selected_route = "manual_review"
            next_action = "manual_review_required"
            status = "chatgpt_diff_review_route_completed_with_downgrade"
            blocked_reason = "unknown_or_invalid_decision"
            safety_downgrades.append("unknown_decision_downgraded_to_manual_review")

    route_payload = {
        "status": status,
        "next_action": next_action,
        "selected_route": selected_route,
        "decision": decision,
        "confidence": confidence,
        "safe_to_commit": bool(safe_to_commit),
        "requires_fix": bool(requires_fix),
        "requires_revert": bool(requires_revert),
        "blocked_reason": blocked_reason,
        "probe_file_present": bool(probe_file_present),
        "probe_file_classification": probe_file_classification,
        "probe_file_approve_guard": probe_file_approve_guard,
        "safety_downgrades": _normalize_string_list(safety_downgrades),
        "artifact_paths": artifact_paths,
    }
    summary_lines = [
        "# ChatGPT Diff Review Route",
        "",
        f"- Status: `{status}`",
        f"- Next action: `{next_action}`",
        f"- Selected route: `{selected_route}`",
        f"- Decision: `{decision}`",
        f"- Confidence: `{confidence}`",
        f"- Safe to commit: `{str(bool(safe_to_commit)).lower()}`",
        f"- Requires fix: `{str(bool(requires_fix)).lower()}`",
        f"- Requires revert: `{str(bool(requires_revert)).lower()}`",
        f"- Blocked reason: `{blocked_reason}`",
        f"- Probe file present: `{str(bool(probe_file_present)).lower()}`",
        f"- Probe file classification: `{probe_file_classification}`",
        f"- Probe file approve guard: `{probe_file_approve_guard}`",
        "",
        "## Safety Downgrades",
    ]
    if safety_downgrades:
        for item in _normalize_string_list(safety_downgrades):
            summary_lines.append(f"- {item}")
    else:
        summary_lines.append("- none")

    try:
        route_dir.mkdir(parents=True, exist_ok=True)
        route_decision_path.write_text(
            json.dumps(route_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        route_summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    except OSError:
        status = "chatgpt_diff_review_route_blocked_write_failed"
        next_action = "manual_review_required"
        blocked_reason = "review_route_artifact_write_failed"

    return {
        "project_browser_autonomous_chatgpt_diff_review_route_status": status,
        "project_browser_autonomous_chatgpt_diff_review_route_next_action": next_action,
        "project_browser_autonomous_chatgpt_diff_review_route_decision": decision,
        "project_browser_autonomous_chatgpt_diff_review_route_confidence": confidence,
        "project_browser_autonomous_chatgpt_diff_review_route_safe_to_commit": bool(
            safe_to_commit
        ),
        "project_browser_autonomous_chatgpt_diff_review_route_requires_fix": bool(
            requires_fix
        ),
        "project_browser_autonomous_chatgpt_diff_review_route_requires_revert": bool(
            requires_revert
        ),
        "project_browser_autonomous_chatgpt_diff_review_route_selected_route": selected_route,
        "project_browser_autonomous_chatgpt_diff_review_route_blocked_reason": blocked_reason,
        "project_browser_autonomous_chatgpt_diff_review_route_probe_file_present": bool(
            probe_file_present
        ),
        "project_browser_autonomous_chatgpt_diff_review_route_probe_file_classification": (
            probe_file_classification
        ),
        "project_browser_autonomous_chatgpt_diff_review_route_probe_file_approve_guard": (
            probe_file_approve_guard
        ),
        "project_browser_autonomous_chatgpt_diff_review_route_artifact_paths": artifact_paths,
        "project_browser_autonomous_chatgpt_diff_review_route_safety_downgrades": (
            _normalize_string_list(safety_downgrades)
        ),
        "project_browser_autonomous_chatgpt_diff_review_route_runtime_posture": runtime_posture,
    }

def _build_project_browser_autonomous_commit_tag_readiness_from_review_route_state(
    *,
    repository_path: str,
) -> dict[str, Any]:
    route_dir = Path("/tmp/codex-local-runner-decision/chatgpt_diff_review_route")
    capture_dir = Path("/tmp/codex-local-runner-decision/local_git_diff_capture")
    output_dir = Path("/tmp/codex-local-runner-decision/commit_tag_readiness")

    route_decision_path = route_dir / "review_route_decision.json"
    changed_files_path = capture_dir / "changed_files.json"
    diff_summary_path = capture_dir / "diff_summary.md"
    reviewable_patch_path = capture_dir / "reviewable_diff.patch"

    readiness_json_path = output_dir / "commit_tag_readiness.json"
    readiness_summary_path = output_dir / "commit_tag_readiness_summary.md"
    commit_plan_path = output_dir / "commit_plan.sh"

    status = "commit_tag_readiness_blocked_missing_review_route"
    next_action = "blocked_route_not_approve"
    blocked_reason = "missing_review_route_decision"
    selected_route = "none"
    safe_to_commit = False
    probe_file_absent = False
    commit_candidates: list[str] = []
    excluded_runtime_artifacts: list[str] = []
    runtime_artifacts_would_be_staged = False

    runtime_posture = [
        "metadata_only_commit_tag_readiness_preparation",
        "no_commit_execution",
        "no_tag_execution",
        "no_push_or_pr_or_merge",
        "runtime_artifacts_excluded_from_candidates",
    ]
    artifact_paths = {
        "input_review_route_decision_json": str(route_decision_path),
        "input_changed_files_json": str(changed_files_path),
        "input_diff_summary_md": str(diff_summary_path),
        "input_reviewable_diff_patch": str(reviewable_patch_path),
        "commit_tag_readiness_json": str(readiness_json_path),
        "commit_tag_readiness_summary_md": str(readiness_summary_path),
        "commit_plan_sh": str(commit_plan_path),
    }

    route_payload: Mapping[str, Any] | None = None
    if route_decision_path.exists():
        try:
            loaded = json.loads(route_decision_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            blocked_reason = "invalid_review_route_decision_json"
        else:
            if isinstance(loaded, Mapping):
                route_payload = loaded
            else:
                blocked_reason = "review_route_decision_not_object"

    route_safe_to_commit = False
    route_requires_fix = True
    route_requires_revert = True
    route_probe_present = True
    if isinstance(route_payload, Mapping):
        selected_route = _normalize_text(
            route_payload.get("selected_route"),
            default="none",
        )
        route_safe_to_commit = bool(route_payload.get("safe_to_commit", False))
        route_requires_fix = bool(route_payload.get("requires_fix", True))
        route_requires_revert = bool(route_payload.get("requires_revert", True))
        route_probe_present = bool(route_payload.get("probe_file_present", True))

    changed_files_payload: Mapping[str, Any] | None = None
    if changed_files_path.exists():
        try:
            loaded_changed_files = json.loads(changed_files_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            loaded_changed_files = None
        if isinstance(loaded_changed_files, Mapping):
            changed_files_payload = loaded_changed_files

    probe_file_present_in_capture = False
    reviewable_paths_seen: list[str] = []
    if isinstance(changed_files_payload, Mapping):
        entries = changed_files_payload.get("changed_files")
        if isinstance(entries, list):
            for entry in entries:
                if not isinstance(entry, Mapping):
                    continue
                path_text = _normalize_text(entry.get("path"), default="")
                if not path_text:
                    continue
                normalized_path = path_text.replace("\\", "/")
                is_runtime_artifact = bool(entry.get("runtime_only", False)) or normalized_path.startswith(
                    "artifacts/runtime_commands/"
                )
                if normalized_path == "tmp_runner_live_write_probe.txt":
                    probe_file_present_in_capture = True
                if is_runtime_artifact:
                    excluded_runtime_artifacts.append(normalized_path)
                    continue
                if normalized_path == "tmp_runner_live_write_probe.txt":
                    continue
                if not bool(entry.get("reviewable", False)):
                    continue
                if normalized_path.endswith("/"):
                    continue
                reviewable_paths_seen.append(normalized_path)

    repository_probe_path = Path(repository_path) / "tmp_runner_live_write_probe.txt"
    probe_file_absent = bool(
        not route_probe_present
        and not probe_file_present_in_capture
        and not repository_probe_path.exists()
    )
    commit_candidates = sorted(set(reviewable_paths_seen))
    runtime_artifacts_would_be_staged = any(
        path.startswith("artifacts/runtime_commands/") for path in commit_candidates
    )
    safe_to_commit = bool(
        selected_route == "approve"
        and route_safe_to_commit
        and not route_requires_fix
        and not route_requires_revert
    )

    commit_message = "Prompt290 approved route commit readiness"
    tag_name = "prompt290-approved-route-ready"
    commit_stage_snippet = ""
    def _quote_for_single_sh(value: str) -> str:
        return "'" + value.replace("'", "'\"'\"'") + "'"
    if commit_candidates:
        quoted_paths = " ".join(_quote_for_single_sh(path) for path in commit_candidates)
        commit_stage_snippet = f"git add -- {quoted_paths}"

    if not isinstance(route_payload, Mapping):
        status = "commit_tag_readiness_blocked_missing_review_route"
        next_action = "blocked_route_not_approve"
    elif selected_route != "approve":
        status = "commit_tag_readiness_blocked_route_not_approve"
        next_action = "blocked_route_not_approve"
        blocked_reason = f"selected_route_not_approve:{selected_route or 'none'}"
    elif not safe_to_commit:
        status = "commit_tag_readiness_blocked_unsafe_candidates"
        next_action = "manual_review_required"
        blocked_reason = "route_not_safe_to_commit"
    elif not probe_file_absent:
        status = "commit_tag_readiness_blocked_unsafe_candidates"
        next_action = "manual_review_required"
        blocked_reason = "probe_file_present"
    elif runtime_artifacts_would_be_staged:
        status = "commit_tag_readiness_blocked_unsafe_candidates"
        next_action = "manual_review_required"
        blocked_reason = "runtime_artifacts_would_be_staged"
    elif not isinstance(changed_files_payload, Mapping):
        status = "commit_tag_readiness_blocked_unsafe_candidates"
        next_action = "manual_review_required"
        blocked_reason = "commit_candidates_not_determinable"
    elif not commit_candidates:
        status = "commit_tag_readiness_blocked_unsafe_candidates"
        next_action = "manual_review_required"
        blocked_reason = "no_reviewable_commit_candidates"
    else:
        status = "commit_tag_readiness_ready"
        next_action = "ready_for_bounded_commit_tag_execution"
        blocked_reason = "none"

    readiness_payload = {
        "status": status,
        "next_action": next_action,
        "selected_route": selected_route,
        "safe_to_commit": bool(safe_to_commit),
        "commit_candidates": commit_candidates,
        "excluded_runtime_artifacts": sorted(set(excluded_runtime_artifacts)),
        "excluded_runtime_artifact_count": len(sorted(set(excluded_runtime_artifacts))),
        "probe_file_absent": bool(probe_file_absent),
        "runtime_artifacts_would_be_staged": bool(runtime_artifacts_would_be_staged),
        "commit_message": commit_message,
        "tag_name": tag_name,
        "blocked_reason": blocked_reason,
        "artifact_paths": artifact_paths,
    }
    summary_lines = [
        "# Commit/Tag Readiness",
        "",
        f"- Status: `{status}`",
        f"- Next action: `{next_action}`",
        f"- Selected route: `{selected_route}`",
        f"- Safe to commit: `{str(bool(safe_to_commit)).lower()}`",
        f"- Commit candidates: `{len(commit_candidates)}`",
        f"- Excluded runtime artifacts: `{len(sorted(set(excluded_runtime_artifacts)))}`",
        f"- Probe file absent: `{str(bool(probe_file_absent)).lower()}`",
        f"- Blocked reason: `{blocked_reason}`",
    ]
    plan_lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        f"cd '{repository_path}'",
        "",
        "# Metadata-only plan prepared by Prompt290. Do not execute automatically.",
        "# Stages only approved reviewable files; excludes runtime artifacts and probe file.",
    ]
    if commit_stage_snippet:
        plan_lines.extend(
            [
                commit_stage_snippet,
                f"git commit -m {_quote_for_single_sh(commit_message)}",
                f"git tag -a {_quote_for_single_sh(tag_name)} -m {_quote_for_single_sh(tag_name)}",
                "# Do not push in this plan.",
            ]
        )
    else:
        plan_lines.append("# No commit candidates available.")

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        readiness_json_path.write_text(
            json.dumps(readiness_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        readiness_summary_path.write_text(
            "\n".join(summary_lines) + "\n",
            encoding="utf-8",
        )
        commit_plan_path.write_text("\n".join(plan_lines) + "\n", encoding="utf-8")
    except OSError:
        status = "commit_tag_readiness_blocked_write_failed"
        next_action = "manual_review_required"
        blocked_reason = "commit_tag_readiness_artifact_write_failed"

    return {
        "project_browser_autonomous_commit_tag_readiness_status": status,
        "project_browser_autonomous_commit_tag_readiness_next_action": next_action,
        "project_browser_autonomous_commit_tag_readiness_selected_route": selected_route,
        "project_browser_autonomous_commit_tag_readiness_safe_to_commit": bool(
            safe_to_commit
        ),
        "project_browser_autonomous_commit_tag_readiness_commit_candidates": commit_candidates,
        "project_browser_autonomous_commit_tag_readiness_excluded_runtime_artifacts": (
            sorted(set(excluded_runtime_artifacts))
        ),
        "project_browser_autonomous_commit_tag_readiness_excluded_runtime_artifact_count": (
            len(sorted(set(excluded_runtime_artifacts)))
        ),
        "project_browser_autonomous_commit_tag_readiness_probe_file_absent": bool(
            probe_file_absent
        ),
        "project_browser_autonomous_commit_tag_readiness_commit_plan_path": str(
            commit_plan_path
        ),
        "project_browser_autonomous_commit_tag_readiness_blocked_reason": blocked_reason,
        "project_browser_autonomous_commit_tag_readiness_runtime_posture": runtime_posture,
        "project_browser_autonomous_commit_tag_readiness_artifact_paths": artifact_paths,
    }

def _build_project_browser_autonomous_smoke_prompt_override_state(
    *,
    repository_path: str,
    override_env_value: str,
) -> dict[str, Any]:
    allowed_statuses = {
        "smoke_override_selected",
        "blocked_override_not_requested",
        "blocked_override_not_allowed",
        "blocked_prompt_path_missing",
        "blocked_prompt_path_unexpected",
        "blocked_prompt_path_symlink",
        "blocked_prompt_empty",
        "blocked_prompt_too_large",
        "blocked_dirty_worktree_before",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "run_write_codex_invocation_later",
        "wait_for_manual_smoke_prompt",
        "manual_review_required",
        "insufficient_truth",
    }
    next_prompt_path = "/tmp/codex-local-runner-decision/generated_next_prompt.txt"
    fix_prompt_path = "/tmp/codex-local-runner-decision/generated_fix_prompt.txt"
    allowed_paths = [next_prompt_path, fix_prompt_path]
    max_prompt_size_bytes = 20000
    runtime_posture = [
        "smoke_override_explicit_only",
        "disabled_by_default",
        "manual_prompt_selection_only",
        "no_prompt_generation",
        "no_patch_apply",
        "no_git_cleanup",
        "no_rollback",
        "no_commit",
        "no_github_mutation",
    ]

    normalized_repository_path = _normalize_text(repository_path, default="")
    normalized_override_value = _normalize_text(override_env_value, default="")
    override_requested = normalized_override_value == "1"
    override_allowed = False
    override_used = False
    override_prompt_kind = "none"
    override_prompt_path = ""
    override_prompt_path_is_exact = False
    override_prompt_path_exists = False
    override_prompt_path_is_symlink = False
    override_prompt_file_non_empty = False
    override_prompt_file_size_bytes = 0
    override_prompt_file_too_large = False
    selected_prompt_kind = "none"
    selected_prompt_path = ""
    selected_prompt_ready = False
    worktree_clean_before = False
    worktree_status_before = ""
    human_review_bypass_for_smoke = False
    max_invocations = 1
    status = "blocked_override_not_requested"
    source_status = "override_not_requested"
    block_reason = "override_not_requested"
    next_action = "wait_for_manual_smoke_prompt"
    missing_inputs: list[str] = []

    if not override_requested:
        pass
    elif not normalized_repository_path:
        status = "blocked_override_not_allowed"
        source_status = "repository_path_missing"
        block_reason = "repository_path_missing"
        next_action = "insufficient_truth"
        missing_inputs.append("repository_path")
    else:
        try:
            status_cp = _run_git(
                normalized_repository_path,
                ["status", "--short"],
                timeout_seconds=10.0,
            )
            worktree_status_before = _normalize_text(status_cp.stdout, default="")
            worktree_clean_before = bool(
                status_cp.returncode == 0 and not worktree_status_before
            )
        except (subprocess.TimeoutExpired, OSError):
            status = "insufficient_truth"
            source_status = "worktree_truth_unavailable"
            block_reason = "worktree_truth_unavailable"
            next_action = "insufficient_truth"
            missing_inputs.append("worktree_status_before")
            worktree_clean_before = False

        if status == "blocked_override_not_requested":
            if not worktree_clean_before:
                status = "blocked_dirty_worktree_before"
                source_status = "worktree_not_clean_before"
                block_reason = "dirty_worktree_before"
                next_action = "manual_review_required"
            else:
                safe_candidates: list[tuple[str, str, int]] = []
                candidate_issues: list[str] = []
                for candidate_path in allowed_paths:
                    candidate_obj = Path(candidate_path)
                    candidate_is_exact = candidate_path in {next_prompt_path, fix_prompt_path}
                    candidate_exists = candidate_obj.exists()
                    candidate_is_symlink = bool(candidate_exists and candidate_obj.is_symlink())
                    candidate_size = 0
                    if candidate_exists and not candidate_is_symlink:
                        try:
                            candidate_size = max(0, int(candidate_obj.stat().st_size))
                        except OSError:
                            candidate_size = 0
                    candidate_non_empty = candidate_size > 0
                    candidate_too_large = candidate_size > max_prompt_size_bytes
                    candidate_kind = "next" if candidate_path == next_prompt_path else "fix"

                    if not candidate_is_exact:
                        candidate_issues.append("blocked_prompt_path_unexpected")
                        continue
                    if not candidate_exists:
                        candidate_issues.append("blocked_prompt_path_missing")
                        continue
                    if candidate_is_symlink:
                        candidate_issues.append("blocked_prompt_path_symlink")
                        continue
                    if not candidate_non_empty:
                        candidate_issues.append("blocked_prompt_empty")
                        continue
                    if candidate_too_large:
                        candidate_issues.append("blocked_prompt_too_large")
                        continue
                    safe_candidates.append((candidate_kind, candidate_path, candidate_size))

                if safe_candidates:
                    chosen_kind, chosen_path, chosen_size = safe_candidates[0]
                    override_allowed = True
                    override_used = True
                    human_review_bypass_for_smoke = True
                    override_prompt_kind = chosen_kind
                    override_prompt_path = chosen_path
                    override_prompt_path_is_exact = True
                    override_prompt_path_exists = True
                    override_prompt_path_is_symlink = False
                    override_prompt_file_non_empty = True
                    override_prompt_file_size_bytes = chosen_size
                    override_prompt_file_too_large = False
                    selected_prompt_kind = chosen_kind
                    selected_prompt_path = chosen_path
                    selected_prompt_ready = True
                    status = "smoke_override_selected"
                    source_status = "explicit_smoke_override_selected"
                    block_reason = "none"
                    next_action = "run_write_codex_invocation_later"
                else:
                    status = candidate_issues[0] if candidate_issues else "blocked_prompt_path_missing"
                    source_status = "no_safe_manual_prompt"
                    block_reason = (
                        "manual_prompt_missing_or_unsafe"
                        if status != "blocked_prompt_path_missing"
                        else "manual_prompt_missing"
                    )
                    next_action = "wait_for_manual_smoke_prompt"
                    if status == "blocked_prompt_path_missing":
                        missing_inputs.append("generated_next_or_fix_prompt_file")

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"

    return {
        "project_browser_autonomous_smoke_prompt_override_status": status,
        "project_browser_autonomous_smoke_prompt_override_source_status": source_status,
        "project_browser_autonomous_smoke_prompt_override_block_reason": block_reason,
        "project_browser_autonomous_smoke_prompt_override_override_requested": bool(
            override_requested
        ),
        "project_browser_autonomous_smoke_prompt_override_override_allowed": bool(
            override_allowed
        ),
        "project_browser_autonomous_smoke_prompt_override_override_used": bool(
            override_used
        ),
        "project_browser_autonomous_smoke_prompt_override_override_prompt_kind": (
            override_prompt_kind
        ),
        "project_browser_autonomous_smoke_prompt_override_override_prompt_path": (
            override_prompt_path
        ),
        "project_browser_autonomous_smoke_prompt_override_override_prompt_path_is_exact": bool(
            override_prompt_path_is_exact
        ),
        "project_browser_autonomous_smoke_prompt_override_override_prompt_path_exists": bool(
            override_prompt_path_exists
        ),
        "project_browser_autonomous_smoke_prompt_override_override_prompt_path_is_symlink": bool(
            override_prompt_path_is_symlink
        ),
        "project_browser_autonomous_smoke_prompt_override_override_prompt_file_non_empty": bool(
            override_prompt_file_non_empty
        ),
        "project_browser_autonomous_smoke_prompt_override_override_prompt_file_size_bytes": int(
            override_prompt_file_size_bytes
        ),
        "project_browser_autonomous_smoke_prompt_override_override_prompt_file_too_large": bool(
            override_prompt_file_too_large
        ),
        "project_browser_autonomous_smoke_prompt_override_selected_prompt_kind": (
            selected_prompt_kind
        ),
        "project_browser_autonomous_smoke_prompt_override_selected_prompt_path": (
            selected_prompt_path
        ),
        "project_browser_autonomous_smoke_prompt_override_selected_prompt_ready": bool(
            selected_prompt_ready
        ),
        "project_browser_autonomous_smoke_prompt_override_worktree_clean_before": bool(
            worktree_clean_before
        ),
        "project_browser_autonomous_smoke_prompt_override_worktree_status_before": (
            worktree_status_before
        ),
        "project_browser_autonomous_smoke_prompt_override_human_review_bypass_for_smoke": bool(
            human_review_bypass_for_smoke
        ),
        "project_browser_autonomous_smoke_prompt_override_max_invocations": int(
            max_invocations
        ),
        "project_browser_autonomous_smoke_prompt_override_next_action": next_action,
        "project_browser_autonomous_smoke_prompt_override_runtime_posture": runtime_posture,
        "project_browser_autonomous_smoke_prompt_override_missing_inputs": (
            _serialize_required_signals(missing_inputs)
        ),
    }


__all__ = [
    "_build_project_browser_autonomous_dispatch_state",
    "_build_project_browser_autonomous_prompt222_n2_bridge_readiness_phase_state",
    "_build_project_browser_autonomous_commit_tag_execution_state_prompt276",
    "_build_project_browser_autonomous_chatgpt_diff_review_route_state",
    "_build_project_browser_autonomous_commit_tag_readiness_from_review_route_state",
    "_build_project_browser_autonomous_smoke_prompt_override_state",
]

from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence
from automation.orchestration.planned_runner.project_browser.constants import (
    _PROJECT_BROWSER_AUTONOMOUS_ACTION_DUPLICATE_STATUSES,
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
    _PROJECT_BROWSER_AUTONOMOUS_DUPLICATE_POLICY_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_DUPLICATE_REASONS,
    _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_BRIDGE_SOURCE_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_BRIDGE_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS,
    _PROJECT_BROWSER_AUTONOMOUS_GATE_RUNTIME_POSTURES,
    _PROJECT_BROWSER_AUTONOMOUS_MANUAL_OVERRIDE_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_RETRY_BUDGET_POSTURES,
    _PROJECT_BROWSER_AUTONOMOUS_SAFETY_SWITCH_STATUSES,
    _PROJECT_BROWSER_AUTONOMOUS_SAFE_STOP_STATUSES,
)
from automation.orchestration.planned_runner.utils import (
    _as_non_negative_int,
    _first_true_reason,
    _normalize_string_list,
    _normalize_text,
    _serialize_required_signals,
)

def _build_project_browser_autonomous_continuation_gate_state(
    *,
    autonomous_dev_assimilation_status: str,
    autonomous_dev_outcome: str,
    autonomous_dev_next_action: str,
    same_prompt_retry_policy: str,
    same_prompt_retry_reason: str,
    next_prompt_draft_status: str,
    next_prompt_kind: str,
    next_prompt_scope: str,
    next_prompt_block_reason: str,
    md_update_draft_status: str,
    md_update_command_draft_status: str,
    md_update_block_reason: str,
) -> dict[str, Any]:
    assimilation_status = _normalize_text(
        autonomous_dev_assimilation_status,
        default="insufficient_truth",
    )
    outcome = _normalize_text(autonomous_dev_outcome, default="insufficient_truth")
    next_action = _normalize_text(autonomous_dev_next_action, default="stop")
    retry_policy = _normalize_text(same_prompt_retry_policy, default="insufficient_truth")
    retry_reason = _normalize_text(same_prompt_retry_reason, default="insufficient_truth")
    prompt_draft_status = _normalize_text(next_prompt_draft_status, default="insufficient_truth")
    prompt_kind = _normalize_text(next_prompt_kind, default="none")
    prompt_scope = _normalize_text(next_prompt_scope, default="none")
    prompt_block_reason = _normalize_text(
        next_prompt_block_reason,
        default="insufficient_truth",
    )
    md_draft_status = _normalize_text(md_update_draft_status, default="insufficient_truth")
    md_command_status = _normalize_text(
        md_update_command_draft_status,
        default="insufficient_truth",
    )
    md_block_reason = _normalize_text(
        md_update_block_reason,
        default="insufficient_truth",
    )

    gate_status = "insufficient_truth"
    gate_next_action = "stop"
    gate_block_reason = "insufficient_truth"
    duplicate_policy_status = "insufficient_truth"
    duplicate_reason = "insufficient_truth"
    retry_budget_posture = "insufficient_truth"

    if prompt_kind != "retry_same_prompt":
        retry_budget_posture = "not_applicable"
    elif retry_policy == "allowed_candidate":
        retry_budget_posture = "available"
    elif retry_policy == "retry_budget_exhausted":
        retry_budget_posture = "exhausted"
    elif retry_policy == "cooldown_required":
        retry_budget_posture = "cooldown_required"
    elif retry_policy == "insufficient_truth":
        retry_budget_posture = "insufficient_truth"
    else:
        retry_budget_posture = "not_applicable"

    if prompt_kind == "retry_same_prompt":
        if retry_policy == "allowed_candidate":
            if retry_reason == "transient_timeout":
                duplicate_policy_status = "retry_same_prompt_allowed"
                duplicate_reason = "allowed_after_timeout"
            elif retry_reason == "response_unavailable":
                duplicate_policy_status = "retry_same_prompt_allowed"
                duplicate_reason = "allowed_after_response_unavailable"
            elif retry_reason == "page_reload_completed":
                duplicate_policy_status = "retry_same_prompt_allowed"
                duplicate_reason = "allowed_after_page_reload"
            elif retry_reason == "new_chat_opened":
                duplicate_policy_status = "retry_same_prompt_allowed"
                duplicate_reason = "allowed_after_new_chat"
            elif retry_reason == "login_resumed":
                duplicate_policy_status = "retry_same_prompt_allowed"
                duplicate_reason = "allowed_after_login_resume"
            elif retry_reason == "rate_limit":
                duplicate_policy_status = "retry_same_prompt_allowed"
                duplicate_reason = "allowed_after_timeout"
            elif retry_reason in {"same_failure", "no_context_change"}:
                duplicate_policy_status = "duplicate_blocked"
                duplicate_reason = (
                    "no_context_change"
                    if retry_reason == "no_context_change"
                    else "same_failure"
                )
            elif retry_reason == "invalid_response_retry_candidate":
                duplicate_policy_status = "loop_suspected"
                duplicate_reason = "loop_suspected"
            else:
                duplicate_policy_status = "insufficient_truth"
                duplicate_reason = "insufficient_truth"
        elif retry_policy == "blocked_duplicate":
            duplicate_policy_status = "duplicate_blocked"
            duplicate_reason = (
                "no_context_change"
                if retry_reason == "no_context_change"
                else "same_failure"
            )
        elif retry_policy == "retry_budget_exhausted":
            duplicate_policy_status = "duplicate_blocked"
            duplicate_reason = "retry_budget_exhausted"
        elif retry_policy == "cooldown_required":
            duplicate_policy_status = "cooldown_required"
            duplicate_reason = "cooldown_required"
        elif retry_policy == "human_review_required":
            duplicate_policy_status = "human_review_required"
            duplicate_reason = "insufficient_truth"
        elif retry_policy == "insufficient_truth":
            duplicate_policy_status = "insufficient_truth"
            duplicate_reason = "insufficient_truth"
        else:
            duplicate_policy_status = "insufficient_truth"
            duplicate_reason = "insufficient_truth"
    else:
        duplicate_policy_status = "clear"
        duplicate_reason = "none"

    if assimilation_status == "inactive":
        gate_status = "inactive"
        gate_next_action = "none"
        gate_block_reason = "none"
    elif assimilation_status == "insufficient_truth":
        gate_status = "insufficient_truth"
        gate_next_action = "stop"
        gate_block_reason = "insufficient_truth"
    elif assimilation_status == "pause_required" or next_action == "pause_for_login":
        gate_status = "pause_required"
        gate_next_action = "pause_for_login"
        gate_block_reason = "pause_for_login"
    elif (
        next_action == "human_review_required"
        or prompt_draft_status == "human_review_required"
        or md_draft_status == "human_review_required"
    ):
        gate_status = "human_review_required"
        gate_next_action = "human_review"
        gate_block_reason = "human_review_required"
    elif next_action == "draft_md_update":
        if md_draft_status == "ready" and md_command_status == "ready":
            gate_status = "allowed"
            gate_next_action = "use_md_update_draft"
            gate_block_reason = "none"
        elif md_draft_status == "insufficient_truth" or md_command_status == "insufficient_truth":
            gate_status = "insufficient_truth"
            gate_next_action = "stop"
            gate_block_reason = "insufficient_truth"
        else:
            gate_status = "blocked"
            gate_next_action = "stop"
            gate_block_reason = "md_update_missing"
    elif next_action in {"draft_next_prompt", "draft_repair_prompt", "stop"}:
        if prompt_draft_status == "ready" and prompt_kind in {
            "next_pr_prompt",
            "repair_prompt",
            "stop_prompt",
        }:
            gate_status = "allowed"
            gate_next_action = "use_next_prompt_draft"
            gate_block_reason = "none"
        elif prompt_draft_status == "insufficient_truth":
            gate_status = "insufficient_truth"
            gate_next_action = "stop"
            gate_block_reason = "insufficient_truth"
        else:
            gate_status = "blocked"
            gate_next_action = "stop"
            gate_block_reason = "draft_missing"
    elif next_action == "retry_same_prompt_candidate":
        if prompt_draft_status == "ready" and prompt_kind == "retry_same_prompt":
            if (
                duplicate_policy_status == "retry_same_prompt_allowed"
                and retry_budget_posture == "available"
            ):
                gate_status = "allowed"
                gate_next_action = "retry_same_prompt"
                gate_block_reason = "none"
            elif (
                duplicate_policy_status == "cooldown_required"
                or retry_budget_posture == "cooldown_required"
            ):
                gate_status = "blocked"
                gate_next_action = "stop"
                gate_block_reason = "cooldown_required"
            elif retry_budget_posture == "exhausted":
                gate_status = "blocked"
                gate_next_action = "stop"
                gate_block_reason = "retry_budget_exhausted"
            elif duplicate_policy_status == "loop_suspected":
                gate_status = "blocked"
                gate_next_action = "stop"
                gate_block_reason = "loop_suspected"
            elif duplicate_policy_status == "duplicate_blocked":
                gate_status = "blocked"
                gate_next_action = "stop"
                gate_block_reason = "duplicate_blocked"
            elif duplicate_policy_status == "human_review_required":
                gate_status = "human_review_required"
                gate_next_action = "human_review"
                gate_block_reason = "human_review_required"
            else:
                gate_status = "insufficient_truth"
                gate_next_action = "stop"
                gate_block_reason = "insufficient_truth"
        elif prompt_draft_status == "insufficient_truth":
            gate_status = "insufficient_truth"
            gate_next_action = "stop"
            gate_block_reason = "insufficient_truth"
        else:
            gate_status = "blocked"
            gate_next_action = "stop"
            gate_block_reason = "draft_missing"
    elif next_action == "none":
        gate_status = "inactive"
        gate_next_action = "none"
        gate_block_reason = "none"
    else:
        gate_status = "blocked"
        gate_next_action = "stop"
        gate_block_reason = (
            "retry_policy_blocked"
            if prompt_scope == "retry_same_prompt_only"
            else (
                "md_update_missing"
                if md_block_reason in {"prior_pr_summary_missing", "md_anchor_missing"}
                else "draft_missing"
            )
        )

    if gate_status not in _PROJECT_BROWSER_AUTONOMOUS_CONTINUATION_GATE_STATUSES:
        gate_status = "insufficient_truth"
    if gate_next_action not in _PROJECT_BROWSER_AUTONOMOUS_CONTINUATION_NEXT_ACTIONS:
        gate_next_action = "stop"
    if (
        gate_block_reason
        not in _PROJECT_BROWSER_AUTONOMOUS_CONTINUATION_BLOCK_REASONS
    ):
        gate_block_reason = "insufficient_truth"
    if duplicate_policy_status not in _PROJECT_BROWSER_AUTONOMOUS_DUPLICATE_POLICY_STATUSES:
        duplicate_policy_status = "insufficient_truth"
    if duplicate_reason not in _PROJECT_BROWSER_AUTONOMOUS_DUPLICATE_REASONS:
        duplicate_reason = "insufficient_truth"
    if retry_budget_posture not in _PROJECT_BROWSER_AUTONOMOUS_RETRY_BUDGET_POSTURES:
        retry_budget_posture = "insufficient_truth"

    runtime_posture = [
        "metadata_only",
        "no_prompt_send",
        "no_md_write",
        "no_shell_execution",
        "no_browser_action",
        "no_queue_mutation",
        "no_retry_execution",
        "no_continuation_execution",
        "no_controller_loop",
    ]
    runtime_posture = [
        token
        for token in runtime_posture
        if token in _PROJECT_BROWSER_AUTONOMOUS_GATE_RUNTIME_POSTURES
    ]

    return {
        "project_browser_autonomous_continuation_gate_status": gate_status,
        "project_browser_autonomous_continuation_next_action": gate_next_action,
        "project_browser_autonomous_continuation_block_reason": gate_block_reason,
        "project_browser_autonomous_duplicate_policy_status": duplicate_policy_status,
        "project_browser_autonomous_duplicate_reason": duplicate_reason,
        "project_browser_autonomous_retry_budget_posture": retry_budget_posture,
        "project_browser_autonomous_gate_runtime_posture": runtime_posture,
        "project_browser_autonomous_gate_runtime_metadata_only": True,
        "project_browser_autonomous_gate_runtime_no_prompt_send": True,
        "project_browser_autonomous_gate_runtime_no_md_write": True,
        "project_browser_autonomous_gate_runtime_no_shell_execution": True,
        "project_browser_autonomous_gate_runtime_no_browser_action": True,
        "project_browser_autonomous_gate_runtime_no_queue_mutation": True,
        "project_browser_autonomous_gate_runtime_no_retry_execution": True,
        "project_browser_autonomous_gate_runtime_no_continuation_execution": True,
        "project_browser_autonomous_gate_runtime_no_controller_loop": True,
    }

def _build_project_browser_autonomous_controller_state(
    *,
    autonomous_dev_assimilation_status: str,
    autonomous_dev_outcome: str,
    autonomous_dev_next_action: str,
    same_prompt_retry_policy: str,
    same_prompt_retry_reason: str,
    next_prompt_draft_status: str,
    next_prompt_kind: str,
    md_update_draft_status: str,
    md_update_command_draft_status: str,
    continuation_gate_status: str,
    continuation_next_action: str,
    continuation_block_reason: str,
    duplicate_policy_status: str,
    duplicate_reason: str,
    retry_budget_posture: str,
) -> dict[str, Any]:
    assimilation_status = _normalize_text(
        autonomous_dev_assimilation_status,
        default="insufficient_truth",
    )
    outcome = _normalize_text(autonomous_dev_outcome, default="insufficient_truth")
    dev_next_action = _normalize_text(autonomous_dev_next_action, default="stop")
    retry_policy = _normalize_text(same_prompt_retry_policy, default="insufficient_truth")
    retry_reason = _normalize_text(same_prompt_retry_reason, default="insufficient_truth")
    prompt_draft_status = _normalize_text(next_prompt_draft_status, default="insufficient_truth")
    prompt_kind = _normalize_text(next_prompt_kind, default="none")
    md_draft_status = _normalize_text(md_update_draft_status, default="insufficient_truth")
    md_command_status = _normalize_text(
        md_update_command_draft_status,
        default="insufficient_truth",
    )
    gate_status = _normalize_text(continuation_gate_status, default="insufficient_truth")
    gate_next_action = _normalize_text(continuation_next_action, default="stop")
    gate_block_reason = _normalize_text(
        continuation_block_reason,
        default="insufficient_truth",
    )
    dup_policy_status = _normalize_text(duplicate_policy_status, default="insufficient_truth")
    dup_reason = _normalize_text(duplicate_reason, default="insufficient_truth")
    retry_budget = _normalize_text(retry_budget_posture, default="insufficient_truth")

    controller_status = "insufficient_truth"
    controller_action = "none"
    action_source = "insufficient_truth"
    stop_reason = "insufficient_truth"
    receipt_status = "insufficient_truth"
    receipt_kind = "none"

    if gate_status == "inactive":
        controller_status = "inactive"
        controller_action = "none"
        action_source = "pr111_gate"
        stop_reason = "gate_inactive"
        receipt_status = "not_created"
    elif gate_status == "pause_required":
        controller_status = "pause_required"
        controller_action = "pause_for_login"
        action_source = "pr111_gate"
        stop_reason = "pause_for_login"
        receipt_status = "pause_required"
        receipt_kind = "pause_for_login_controller_receipt"
    elif gate_status == "human_review_required":
        controller_status = "human_review_required"
        controller_action = "human_review"
        action_source = "pr111_gate"
        stop_reason = "human_review_required"
        receipt_status = "human_review_required"
        receipt_kind = "human_review_controller_receipt"
    elif gate_status == "blocked":
        controller_status = "blocked"
        controller_action = "stop"
        action_source = "pr111_gate"
        if gate_block_reason == "duplicate_blocked":
            stop_reason = "duplicate_blocked"
        elif gate_block_reason == "retry_budget_exhausted":
            stop_reason = "retry_budget_exhausted"
        elif gate_block_reason == "cooldown_required":
            stop_reason = "cooldown_required"
        else:
            stop_reason = "gate_blocked"
        receipt_status = "blocked"
        receipt_kind = "blocked_controller_receipt"
    elif gate_status == "insufficient_truth":
        controller_status = "insufficient_truth"
        controller_action = "none"
        action_source = "pr111_gate"
        stop_reason = "insufficient_truth"
        receipt_status = "insufficient_truth"
    elif gate_status == "allowed":
        candidates: list[str] = []
        cand_pause = bool(
            gate_next_action == "pause_for_login" or assimilation_status == "pause_required"
        )
        cand_human = bool(
            gate_next_action == "human_review" or dev_next_action == "human_review_required"
        )
        cand_md = bool(
            md_draft_status == "ready"
            and md_command_status == "ready"
            and (
                gate_next_action == "use_md_update_draft"
                or dev_next_action == "draft_md_update"
            )
        )
        cand_retry = bool(
            prompt_draft_status == "ready"
            and prompt_kind == "retry_same_prompt"
            and retry_policy == "allowed_candidate"
            and dup_policy_status == "retry_same_prompt_allowed"
            and retry_budget == "available"
            and retry_reason
            in {
                "transient_timeout",
                "response_unavailable",
                "page_reload_completed",
                "new_chat_opened",
                "login_resumed",
                "rate_limit",
                "invalid_response_retry_candidate",
            }
            and (
                gate_next_action == "retry_same_prompt"
                or dev_next_action == "retry_same_prompt_candidate"
            )
        )
        cand_next = bool(
            prompt_draft_status == "ready"
            and prompt_kind in {"next_pr_prompt", "repair_prompt", "stop_prompt"}
            and (
                gate_next_action == "use_next_prompt_draft"
                or dev_next_action in {"draft_next_prompt", "draft_repair_prompt"}
            )
        )
        cand_stop = bool(
            gate_next_action == "stop"
            or dev_next_action == "stop"
            or outcome == "insufficient_truth"
        )

        if cand_pause:
            candidates.append("pause_for_login")
        if cand_human:
            candidates.append("human_review")
        if cand_md:
            candidates.append("use_md_update_draft")
        if cand_retry:
            candidates.append("retry_same_prompt")
        if cand_next:
            candidates.append("use_next_prompt_draft")
        if cand_stop:
            candidates.append("stop")

        if "pause_for_login" in candidates:
            selected = "pause_for_login"
        elif "human_review" in candidates:
            selected = "human_review"
        elif "use_md_update_draft" in candidates:
            selected = "use_md_update_draft"
        elif "retry_same_prompt" in candidates:
            selected = "retry_same_prompt"
        elif "use_next_prompt_draft" in candidates:
            selected = "use_next_prompt_draft"
        elif "stop" in candidates:
            selected = "stop"
        else:
            selected = ""

        if selected:
            controller_status = "selected_one_action"
            controller_action = selected
            action_source = (
                "pr111_gate"
                if (
                    gate_next_action
                    in {
                        "pause_for_login",
                        "human_review",
                        "use_md_update_draft",
                        "retry_same_prompt",
                        "use_next_prompt_draft",
                        "stop",
                    }
                )
                else (
                    "pr110_draft"
                    if selected in {
                        "use_md_update_draft",
                        "use_next_prompt_draft",
                        "retry_same_prompt",
                    }
                    else "pr109_assimilation"
                )
            )
            stop_reason = "one_action_selected"
            receipt_status = "ready"
            receipt_kind = "one_pr_controller_receipt"
        else:
            controller_status = "ready"
            controller_action = "none"
            action_source = (
                "pr110_draft"
                if prompt_draft_status in {"ready", "blocked", "human_review_required"}
                or md_draft_status in {"ready", "blocked", "human_review_required"}
                else (
                    "pr109_assimilation"
                    if assimilation_status in {"assimilated", "blocked", "failed", "pause_required"}
                    else "pr111_gate"
                )
            )
            if dup_policy_status == "duplicate_blocked" or dup_reason in {"same_failure", "no_context_change"}:
                controller_status = "blocked"
                controller_action = "stop"
                stop_reason = "duplicate_blocked"
                receipt_status = "blocked"
                receipt_kind = "blocked_controller_receipt"
            elif retry_budget in {"exhausted"}:
                controller_status = "blocked"
                controller_action = "stop"
                stop_reason = "retry_budget_exhausted"
                receipt_status = "blocked"
                receipt_kind = "blocked_controller_receipt"
            elif retry_budget in {"cooldown_required"} or dup_policy_status == "cooldown_required":
                controller_status = "blocked"
                controller_action = "stop"
                stop_reason = "cooldown_required"
                receipt_status = "blocked"
                receipt_kind = "blocked_controller_receipt"
            elif gate_next_action in {"use_md_update_draft"} and (
                md_draft_status != "ready" or md_command_status != "ready"
            ):
                controller_status = "blocked"
                controller_action = "stop"
                stop_reason = "gate_blocked"
                receipt_status = "blocked"
                receipt_kind = "blocked_controller_receipt"
            elif gate_next_action in {"use_next_prompt_draft", "retry_same_prompt"} and (
                prompt_draft_status != "ready"
            ):
                controller_status = "blocked"
                controller_action = "stop"
                stop_reason = "gate_blocked"
                receipt_status = "blocked"
                receipt_kind = "blocked_controller_receipt"
            else:
                stop_reason = "insufficient_truth"
                receipt_status = "insufficient_truth"
    else:
        controller_status = "insufficient_truth"
        controller_action = "none"
        action_source = "insufficient_truth"
        stop_reason = "insufficient_truth"
        receipt_status = "insufficient_truth"

    if controller_status not in _PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_STATUSES:
        controller_status = "insufficient_truth"
    if controller_action not in _PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_ACTIONS:
        controller_action = "none"
    if action_source not in _PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_ACTION_SOURCES:
        action_source = "insufficient_truth"
    if stop_reason not in _PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_STOP_REASONS:
        stop_reason = "insufficient_truth"
    if receipt_status not in _PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_RECEIPT_STATUSES:
        receipt_status = "insufficient_truth"
    if receipt_kind not in _PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_RECEIPT_KINDS:
        receipt_kind = "none"

    runtime_posture = [
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
    ]
    runtime_posture = [
        token
        for token in runtime_posture
        if token in _PROJECT_BROWSER_AUTONOMOUS_CONTROLLER_RUNTIME_POSTURES
    ]

    return {
        "project_browser_autonomous_controller_status": controller_status,
        "project_browser_autonomous_controller_action": controller_action,
        "project_browser_autonomous_controller_action_source": action_source,
        "project_browser_autonomous_controller_stop_reason": stop_reason,
        "project_browser_autonomous_controller_receipt_status": receipt_status,
        "project_browser_autonomous_controller_receipt_kind": receipt_kind,
        "project_browser_autonomous_controller_runtime_posture": runtime_posture,
        "project_browser_autonomous_controller_runtime_metadata_only": True,
        "project_browser_autonomous_controller_runtime_no_prompt_send": True,
        "project_browser_autonomous_controller_runtime_no_md_write": True,
        "project_browser_autonomous_controller_runtime_no_shell_execution": True,
        "project_browser_autonomous_controller_runtime_no_browser_action": True,
        "project_browser_autonomous_controller_runtime_no_queue_mutation": True,
        "project_browser_autonomous_controller_runtime_no_retry_execution": True,
        "project_browser_autonomous_controller_runtime_no_continuation_execution": True,
        "project_browser_autonomous_controller_runtime_no_multi_action": True,
        "project_browser_autonomous_controller_runtime_no_controller_loop": True,
        "project_browser_autonomous_controller_runtime_no_background_runtime": True,
    }

def _build_project_browser_autonomous_rolling_gate_state(
    *,
    autonomous_multistep_budget_status: str,
    autonomous_multistep_permission: str,
    autonomous_multistep_next_step_candidate: str,
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
    autonomous_step_score_band: str,
    autonomous_step_auto_approval_posture: str,
    autonomous_step_receipt_status: str,
    autonomous_step_stop_reason: str,
    autonomous_batch_evaluation_status: str,
    autonomous_batch_continue_permission: str,
    autonomous_batch_continue_reason: str,
    autonomous_batch_next_action: str,
    current_browser_ui_failure_status: str,
    current_browser_response_status: str,
    current_browser_response_assimilation_status: str,
    prior_compact_state: Mapping[str, Any] | None,
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
    step_score_band = _normalize_text(
        autonomous_step_score_band,
        default="insufficient_truth",
    )
    step_auto_approval_posture = _normalize_text(
        autonomous_step_auto_approval_posture,
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

    batch_evaluation_status = _normalize_text(
        autonomous_batch_evaluation_status,
        default="insufficient_truth",
    )
    batch_continue_permission = _normalize_text(
        autonomous_batch_continue_permission,
        default="insufficient_truth",
    )
    batch_continue_reason = _normalize_text(
        autonomous_batch_continue_reason,
        default="insufficient_truth",
    )
    batch_next_action = _normalize_text(autonomous_batch_next_action, default="none")

    ui_failure_status = _normalize_text(
        current_browser_ui_failure_status,
        default="insufficient_truth",
    )
    response_status = _normalize_text(
        current_browser_response_status,
        default="insufficient_truth",
    )
    response_assimilation_status = _normalize_text(
        current_browser_response_assimilation_status,
        default="insufficient_truth",
    )
    prior = dict(prior_compact_state or {})

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
        rolling_gate_status: str,
        rolling_continue_permission: str,
        rolling_continue_reason: str,
        cooldown_status: str,
        cooldown_reason: str,
        retry_hardening_status: str,
        same_prompt_retry_remaining: int,
        same_failure_count: int,
        loop_risk_status: str,
        loop_risk_reason: str,
        rolling_next_action: str,
    ) -> dict[str, Any]:
        return {
            "project_browser_autonomous_rolling_gate_status": rolling_gate_status,
            "project_browser_autonomous_rolling_continue_permission": rolling_continue_permission,
            "project_browser_autonomous_rolling_continue_reason": rolling_continue_reason,
            "project_browser_autonomous_cooldown_status": cooldown_status,
            "project_browser_autonomous_cooldown_reason": cooldown_reason,
            "project_browser_autonomous_retry_hardening_status": retry_hardening_status,
            "project_browser_autonomous_same_prompt_retry_remaining": same_prompt_retry_remaining,
            "project_browser_autonomous_same_failure_count": same_failure_count,
            "project_browser_autonomous_loop_risk_status": loop_risk_status,
            "project_browser_autonomous_loop_risk_reason": loop_risk_reason,
            "project_browser_autonomous_rolling_next_action": rolling_next_action,
            "project_browser_autonomous_rolling_runtime_posture": runtime_posture,
            "project_browser_autonomous_rolling_runtime_metadata_only": True,
            "project_browser_autonomous_rolling_runtime_no_next_step_start": True,
            "project_browser_autonomous_rolling_runtime_no_prompt_send": True,
            "project_browser_autonomous_rolling_runtime_no_md_write": True,
            "project_browser_autonomous_rolling_runtime_no_shell_execution": True,
            "project_browser_autonomous_rolling_runtime_no_codex_execution": True,
            "project_browser_autonomous_rolling_runtime_no_browser_action": True,
            "project_browser_autonomous_rolling_runtime_no_playwright": True,
            "project_browser_autonomous_rolling_runtime_no_dom_interaction": True,
            "project_browser_autonomous_rolling_runtime_no_queue_mutation": True,
            "project_browser_autonomous_rolling_runtime_no_retry_execution": True,
            "project_browser_autonomous_rolling_runtime_no_repair_execution": True,
            "project_browser_autonomous_rolling_runtime_no_restart_execution": True,
            "project_browser_autonomous_rolling_runtime_no_approval_execution": True,
            "project_browser_autonomous_rolling_runtime_no_continuation_execution": True,
            "project_browser_autonomous_rolling_runtime_no_loop_execution": True,
            "project_browser_autonomous_rolling_runtime_no_background_runtime": True,
        }

    def _insufficient_truth_state() -> dict[str, Any]:
        return _base_state(
            rolling_gate_status="insufficient_truth",
            rolling_continue_permission="insufficient_truth",
            rolling_continue_reason="insufficient_truth",
            cooldown_status="insufficient_truth",
            cooldown_reason="insufficient_truth",
            retry_hardening_status="insufficient_truth",
            same_prompt_retry_remaining=0,
            same_failure_count=0,
            loop_risk_status="insufficient_truth",
            loop_risk_reason="insufficient_truth",
            rolling_next_action="none",
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
    if batch_evaluation_status not in {
        "inactive",
        "continue_candidate",
        "stopped",
        "blocked",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state()
    if batch_continue_permission not in {
        "allowed_candidate",
        "blocked",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state()
    if batch_continue_reason not in {
        "none",
        "score_auto_safe",
        "score_below_auto_safe",
        "budget_remaining",
        "budget_exhausted",
        "failure_budget_exhausted",
        "retry_budget_exhausted",
        "duplicate_risk",
        "pause_required",
        "human_review_required",
        "step_receipt_missing",
        "insufficient_truth",
    }:
        return _insufficient_truth_state()
    if batch_next_action not in {
        "none",
        "continue_later",
        "stop",
        "pause_for_login",
        "human_review",
    }:
        return _insufficient_truth_state()

    if (
        budget_source_status in {"inconsistent", "insufficient_truth"}
        or bridge_source_status in {"inconsistent", "insufficient_truth"}
    ):
        return _insufficient_truth_state()

    required_counter_keys = (
        "project_browser_autonomous_multistep_remaining_steps",
        "project_browser_autonomous_multistep_remaining_failures",
        "project_browser_autonomous_multistep_same_prompt_retry_remaining",
    )
    if any(key not in multistep_state for key in required_counter_keys):
        return _insufficient_truth_state()

    def _read_optional_non_negative_int(value: Any) -> tuple[int, bool]:
        if value is None or value == "":
            return 0, False
        if isinstance(value, bool):
            return 0, True
        if isinstance(value, int):
            return (value if value >= 0 else 0), value < 0
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return 0, False
            if text.isdigit():
                return int(text), False
            return 0, True
        return 0, True

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

    remaining_steps, remaining_steps_invalid = _read_required_non_negative_int(
        multistep_state.get("project_browser_autonomous_multistep_remaining_steps")
    )
    remaining_failures, remaining_failures_invalid = _read_required_non_negative_int(
        multistep_state.get("project_browser_autonomous_multistep_remaining_failures")
    )
    same_prompt_retry_remaining, same_prompt_retry_remaining_invalid = (
        _read_required_non_negative_int(
            multistep_state.get(
                "project_browser_autonomous_multistep_same_prompt_retry_remaining"
            )
        )
    )
    if (
        remaining_steps_invalid
        or remaining_failures_invalid
        or same_prompt_retry_remaining_invalid
    ):
        return _insufficient_truth_state()

    prior_same_failure_count, prior_same_failure_invalid = _read_optional_non_negative_int(
        prior.get("project_browser_autonomous_same_failure_count")
    )
    if prior_same_failure_invalid:
        return _insufficient_truth_state()
    prior_last_stop_reason = _normalize_text(
        prior.get("project_browser_autonomous_last_stop_reason"),
        default="none",
    )
    same_failure_signature = step_stop_reason if step_stop_reason != "none" else batch_continue_reason
    same_failure_count = 0
    if same_failure_signature in {
        "retry_budget_exhausted",
        "failure_budget_exhausted",
        "step_budget_exhausted",
        "duplicate_risk",
        "bridge_or_budget_not_ready",
        "score_below_auto_safe",
    }:
        if prior_last_stop_reason == same_failure_signature:
            same_failure_count = max(2, prior_same_failure_count + 1)
        else:
            same_failure_count = 1
    else:
        same_failure_count = 0

    prior_ui_failure_status = _normalize_text(
        prior.get("project_browser_ui_failure_status"),
        default="",
    )
    prior_response_status = _normalize_text(
        prior.get("project_browser_response_status"),
        default="",
    )
    prior_response_assimilation_status = _normalize_text(
        prior.get("project_browser_response_assimilation_status"),
        default="",
    )

    repeated_timeout = bool(
        ui_failure_status == "loading_timeout"
        and prior_ui_failure_status == "loading_timeout"
    )
    repeated_response_unavailable = bool(
        (
            ui_failure_status == "response_unavailable"
            and prior_ui_failure_status == "response_unavailable"
        )
        or (
            response_status == "unavailable"
            and prior_response_status == "unavailable"
        )
    )
    repeated_invalid_response = bool(
        (
            response_status == "invalid_response"
            and prior_response_status == "invalid_response"
        )
        or (
            response_assimilation_status == "invalid_response"
            and prior_response_assimilation_status == "invalid_response"
        )
    )

    retry_exhausted = bool(
        next_step_candidate == "retry_same_prompt" and same_prompt_retry_remaining <= 0
    )
    failure_exhausted = remaining_failures <= 0
    step_exhausted = remaining_steps <= 0
    duplicate_prompt_or_action = duplicate_status in {
        "duplicate_action",
        "duplicate_prompt",
    }

    loop_risk_status = "clear"
    loop_risk_reason = "none"
    if duplicate_status == "duplicate_action":
        loop_risk_status = "blocked"
        loop_risk_reason = "duplicate_action"
    elif duplicate_status == "duplicate_prompt":
        loop_risk_status = "blocked"
        loop_risk_reason = "duplicate_prompt"
    elif retry_exhausted:
        loop_risk_status = "blocked"
        loop_risk_reason = "exhausted_retry_budget"
    elif same_failure_count >= 2:
        loop_risk_status = "blocked"
        loop_risk_reason = "same_failure_no_context_change"
    elif step_action == "retry_same_prompt" and same_failure_count >= 1:
        loop_risk_status = "suspected"
        loop_risk_reason = "repeated_retry_without_progress"

    cooldown_status = "not_required"
    cooldown_reason = "none"
    if retry_exhausted:
        cooldown_status = "blocked"
        cooldown_reason = "retry_budget_exhausted"
    elif repeated_timeout:
        cooldown_status = "required"
        cooldown_reason = "repeated_timeout"
    elif repeated_response_unavailable:
        cooldown_status = "required"
        cooldown_reason = "repeated_response_unavailable"
    elif repeated_invalid_response:
        cooldown_status = "required"
        cooldown_reason = "repeated_invalid_response"
    elif same_failure_count >= 2:
        cooldown_status = "required"
        cooldown_reason = "same_failure_repeated"
    elif loop_risk_status in {"suspected", "blocked"}:
        cooldown_status = "required"
        cooldown_reason = "loop_suspected"

    retry_hardening_status = "not_required"
    if step_action == "retry_same_prompt" or next_step_candidate == "retry_same_prompt":
        retry_hardening_status = "available" if same_prompt_retry_remaining > 0 else "exhausted"
    if loop_risk_status == "blocked" and retry_hardening_status != "exhausted":
        retry_hardening_status = "blocked"

    def _map_batch_reason_to_rolling(reason: str) -> str:
        if reason == "none":
            return "none"
        if reason == "score_auto_safe":
            return "score_auto_safe"
        if reason == "budget_exhausted":
            return "step_budget_exhausted"
        if reason == "failure_budget_exhausted":
            return "failure_budget_exhausted"
        if reason == "retry_budget_exhausted":
            return "retry_budget_exhausted"
        if reason == "duplicate_risk":
            return "duplicate_risk"
        if reason == "pause_required":
            return "pause_required"
        if reason == "human_review_required":
            return "human_review_required"
        if reason == "score_below_auto_safe":
            return "human_review_required"
        if reason in {"step_receipt_missing", "insufficient_truth"}:
            return "insufficient_truth"
        if reason == "budget_remaining":
            return "pr118_continue_allowed"
        return "insufficient_truth"

    mapped_batch_reason = _map_batch_reason_to_rolling(batch_continue_reason)
    if mapped_batch_reason == "insufficient_truth" and batch_continue_reason not in {
        "score_below_auto_safe",
        "step_receipt_missing",
        "insufficient_truth",
    }:
        return _insufficient_truth_state()

    if batch_evaluation_status == "inactive":
        return _base_state(
            rolling_gate_status="inactive",
            rolling_continue_permission="insufficient_truth",
            rolling_continue_reason="none",
            cooldown_status="not_required",
            cooldown_reason="none",
            retry_hardening_status=retry_hardening_status,
            same_prompt_retry_remaining=same_prompt_retry_remaining,
            same_failure_count=same_failure_count,
            loop_risk_status=loop_risk_status,
            loop_risk_reason=loop_risk_reason,
            rolling_next_action="none",
        )
    if batch_evaluation_status == "pause_required":
        return _base_state(
            rolling_gate_status="pause_required",
            rolling_continue_permission="pause_required",
            rolling_continue_reason="pause_required",
            cooldown_status=cooldown_status,
            cooldown_reason=cooldown_reason,
            retry_hardening_status=retry_hardening_status,
            same_prompt_retry_remaining=same_prompt_retry_remaining,
            same_failure_count=same_failure_count,
            loop_risk_status=loop_risk_status,
            loop_risk_reason=loop_risk_reason,
            rolling_next_action="pause_for_login",
        )
    if batch_evaluation_status == "human_review_required":
        return _base_state(
            rolling_gate_status="human_review_required",
            rolling_continue_permission="human_review_required",
            rolling_continue_reason="human_review_required",
            cooldown_status=cooldown_status,
            cooldown_reason=cooldown_reason,
            retry_hardening_status=retry_hardening_status,
            same_prompt_retry_remaining=same_prompt_retry_remaining,
            same_failure_count=same_failure_count,
            loop_risk_status=loop_risk_status,
            loop_risk_reason=loop_risk_reason,
            rolling_next_action="human_review",
        )
    if batch_evaluation_status == "insufficient_truth":
        return _insufficient_truth_state()
    if batch_evaluation_status == "blocked":
        reason = mapped_batch_reason
        if reason == "none":
            reason = "insufficient_truth"
        return _base_state(
            rolling_gate_status="blocked",
            rolling_continue_permission="blocked",
            rolling_continue_reason=reason,
            cooldown_status=cooldown_status,
            cooldown_reason=cooldown_reason,
            retry_hardening_status=retry_hardening_status,
            same_prompt_retry_remaining=same_prompt_retry_remaining,
            same_failure_count=same_failure_count,
            loop_risk_status=loop_risk_status,
            loop_risk_reason=loop_risk_reason,
            rolling_next_action="stop",
        )

    if batch_continue_permission != "allowed_candidate":
        if batch_continue_permission == "pause_required":
            return _base_state(
                rolling_gate_status="pause_required",
                rolling_continue_permission="pause_required",
                rolling_continue_reason="pause_required",
                cooldown_status=cooldown_status,
                cooldown_reason=cooldown_reason,
                retry_hardening_status=retry_hardening_status,
                same_prompt_retry_remaining=same_prompt_retry_remaining,
                same_failure_count=same_failure_count,
                loop_risk_status=loop_risk_status,
                loop_risk_reason=loop_risk_reason,
                rolling_next_action="pause_for_login",
            )
        if batch_continue_permission == "human_review_required":
            return _base_state(
                rolling_gate_status="human_review_required",
                rolling_continue_permission="human_review_required",
                rolling_continue_reason="human_review_required",
                cooldown_status=cooldown_status,
                cooldown_reason=cooldown_reason,
                retry_hardening_status=retry_hardening_status,
                same_prompt_retry_remaining=same_prompt_retry_remaining,
                same_failure_count=same_failure_count,
                loop_risk_status=loop_risk_status,
                loop_risk_reason=loop_risk_reason,
                rolling_next_action="human_review",
            )
        if batch_continue_permission in {"blocked", "insufficient_truth"}:
            return _base_state(
                rolling_gate_status=(
                    "blocked"
                    if batch_continue_permission == "blocked"
                    else "insufficient_truth"
                ),
                rolling_continue_permission=batch_continue_permission,
                rolling_continue_reason=(
                    mapped_batch_reason
                    if batch_continue_permission == "blocked"
                    else "insufficient_truth"
                ),
                cooldown_status=cooldown_status,
                cooldown_reason=cooldown_reason,
                retry_hardening_status=retry_hardening_status,
                same_prompt_retry_remaining=same_prompt_retry_remaining,
                same_failure_count=same_failure_count,
                loop_risk_status=loop_risk_status,
                loop_risk_reason=loop_risk_reason,
                rolling_next_action="stop",
            )
        return _insufficient_truth_state()

    if step_exhausted:
        return _base_state(
            rolling_gate_status="blocked",
            rolling_continue_permission="blocked",
            rolling_continue_reason="step_budget_exhausted",
            cooldown_status=cooldown_status,
            cooldown_reason=cooldown_reason,
            retry_hardening_status="exhausted",
            same_prompt_retry_remaining=same_prompt_retry_remaining,
            same_failure_count=same_failure_count,
            loop_risk_status=loop_risk_status,
            loop_risk_reason=loop_risk_reason,
            rolling_next_action="stop",
        )
    if failure_exhausted:
        return _base_state(
            rolling_gate_status="blocked",
            rolling_continue_permission="blocked",
            rolling_continue_reason="failure_budget_exhausted",
            cooldown_status=cooldown_status,
            cooldown_reason=cooldown_reason,
            retry_hardening_status="exhausted",
            same_prompt_retry_remaining=same_prompt_retry_remaining,
            same_failure_count=same_failure_count,
            loop_risk_status=loop_risk_status,
            loop_risk_reason=loop_risk_reason,
            rolling_next_action="stop",
        )
    if retry_exhausted:
        return _base_state(
            rolling_gate_status="blocked",
            rolling_continue_permission="blocked",
            rolling_continue_reason="retry_budget_exhausted",
            cooldown_status="blocked",
            cooldown_reason="retry_budget_exhausted",
            retry_hardening_status="exhausted",
            same_prompt_retry_remaining=same_prompt_retry_remaining,
            same_failure_count=same_failure_count,
            loop_risk_status="blocked",
            loop_risk_reason="exhausted_retry_budget",
            rolling_next_action="stop",
        )
    if duplicate_prompt_or_action:
        return _base_state(
            rolling_gate_status="blocked",
            rolling_continue_permission="blocked",
            rolling_continue_reason="duplicate_risk",
            cooldown_status="required",
            cooldown_reason="loop_suspected",
            retry_hardening_status="blocked",
            same_prompt_retry_remaining=same_prompt_retry_remaining,
            same_failure_count=same_failure_count,
            loop_risk_status="blocked",
            loop_risk_reason=(
                "duplicate_action"
                if duplicate_status == "duplicate_action"
                else "duplicate_prompt"
            ),
            rolling_next_action="stop",
        )
    if same_failure_count >= 2:
        return _base_state(
            rolling_gate_status="blocked",
            rolling_continue_permission="blocked",
            rolling_continue_reason="same_failure_repeated",
            cooldown_status="required",
            cooldown_reason="same_failure_repeated",
            retry_hardening_status="blocked",
            same_prompt_retry_remaining=same_prompt_retry_remaining,
            same_failure_count=same_failure_count,
            loop_risk_status="blocked",
            loop_risk_reason="same_failure_no_context_change",
            rolling_next_action="cooldown",
        )
    if cooldown_status == "required":
        return _base_state(
            rolling_gate_status="cooldown_required",
            rolling_continue_permission="cooldown_required",
            rolling_continue_reason="cooldown_required",
            cooldown_status=cooldown_status,
            cooldown_reason=cooldown_reason,
            retry_hardening_status=retry_hardening_status,
            same_prompt_retry_remaining=same_prompt_retry_remaining,
            same_failure_count=same_failure_count,
            loop_risk_status=loop_risk_status,
            loop_risk_reason=loop_risk_reason,
            rolling_next_action="cooldown",
        )
    if cooldown_status == "blocked":
        return _base_state(
            rolling_gate_status="blocked",
            rolling_continue_permission="blocked",
            rolling_continue_reason=(
                "retry_budget_exhausted"
                if cooldown_reason == "retry_budget_exhausted"
                else "cooldown_required"
            ),
            cooldown_status=cooldown_status,
            cooldown_reason=cooldown_reason,
            retry_hardening_status=retry_hardening_status,
            same_prompt_retry_remaining=same_prompt_retry_remaining,
            same_failure_count=same_failure_count,
            loop_risk_status=loop_risk_status,
            loop_risk_reason=loop_risk_reason,
            rolling_next_action="stop",
        )
    if retry_hardening_status in {"exhausted", "blocked"}:
        return _base_state(
            rolling_gate_status="blocked",
            rolling_continue_permission="blocked",
            rolling_continue_reason="retry_budget_exhausted",
            cooldown_status=cooldown_status,
            cooldown_reason=cooldown_reason,
            retry_hardening_status=retry_hardening_status,
            same_prompt_retry_remaining=same_prompt_retry_remaining,
            same_failure_count=same_failure_count,
            loop_risk_status=loop_risk_status,
            loop_risk_reason=loop_risk_reason,
            rolling_next_action="stop",
        )
    if loop_risk_status != "clear":
        return _base_state(
            rolling_gate_status="blocked",
            rolling_continue_permission="blocked",
            rolling_continue_reason="loop_suspected",
            cooldown_status=cooldown_status,
            cooldown_reason="loop_suspected",
            retry_hardening_status="blocked",
            same_prompt_retry_remaining=same_prompt_retry_remaining,
            same_failure_count=same_failure_count,
            loop_risk_status=loop_risk_status,
            loop_risk_reason=loop_risk_reason,
            rolling_next_action="stop",
        )

    hard_gates_clear = bool(
        batch_evaluation_status == "continue_candidate"
        and batch_continue_permission == "allowed_candidate"
        and step_score_band == "auto_safe_without_approval"
        and step_auto_approval_posture == "allowed_without_human"
        and step_receipt_status == "ready"
        and remaining_steps > 0
        and remaining_failures > 0
        and cooldown_status == "not_required"
        and retry_hardening_status not in {"exhausted", "blocked"}
        and loop_risk_status == "clear"
        and safety_switch_status in {"enabled", "inactive"}
        and manual_override_status in {"inactive", "clear"}
        and safe_stop_status == "not_required"
        and execution_permission == "allowed_candidate"
        and bridge_status == "ready"
        and bridge_permission == "allowed_candidate"
        and bridge_source_status == "valid"
        and budget_status == "ready"
        and multistep_permission == "allowed_candidate"
    )
    if next_step_candidate == "retry_same_prompt" and same_prompt_retry_remaining <= 0:
        hard_gates_clear = False

    if hard_gates_clear:
        return _base_state(
            rolling_gate_status="allowed_candidate",
            rolling_continue_permission="allowed_candidate",
            rolling_continue_reason="pr118_continue_allowed",
            cooldown_status="not_required",
            cooldown_reason="none",
            retry_hardening_status=retry_hardening_status,
            same_prompt_retry_remaining=same_prompt_retry_remaining,
            same_failure_count=same_failure_count,
            loop_risk_status="clear",
            loop_risk_reason="none",
            rolling_next_action="continue_short_batch_later",
        )
    if step_score_band == "auto_safe_without_approval":
        if (
            safe_stop_status == "pause_after_current_step"
            or manual_override_status == "requested"
        ):
            return _base_state(
                rolling_gate_status="pause_required",
                rolling_continue_permission="pause_required",
                rolling_continue_reason="pause_required",
                cooldown_status=cooldown_status,
                cooldown_reason=cooldown_reason,
                retry_hardening_status=retry_hardening_status,
                same_prompt_retry_remaining=same_prompt_retry_remaining,
                same_failure_count=same_failure_count,
                loop_risk_status=loop_risk_status,
                loop_risk_reason=loop_risk_reason,
                rolling_next_action="pause_for_login",
            )
        if (
            safe_stop_status == "human_review_required"
            or manual_override_status in {"required", "blocked"}
        ):
            return _base_state(
                rolling_gate_status="human_review_required",
                rolling_continue_permission="human_review_required",
                rolling_continue_reason="human_review_required",
                cooldown_status=cooldown_status,
                cooldown_reason=cooldown_reason,
                retry_hardening_status=retry_hardening_status,
                same_prompt_retry_remaining=same_prompt_retry_remaining,
                same_failure_count=same_failure_count,
                loop_risk_status=loop_risk_status,
                loop_risk_reason=loop_risk_reason,
                rolling_next_action="human_review",
            )
        return _base_state(
            rolling_gate_status="blocked",
            rolling_continue_permission="blocked",
            rolling_continue_reason="insufficient_truth",
            cooldown_status=cooldown_status,
            cooldown_reason=cooldown_reason,
            retry_hardening_status=retry_hardening_status,
            same_prompt_retry_remaining=same_prompt_retry_remaining,
            same_failure_count=same_failure_count,
            loop_risk_status=loop_risk_status,
            loop_risk_reason=loop_risk_reason,
            rolling_next_action="stop",
        )

    if step_score_band == "auto_candidate":
        return _base_state(
            rolling_gate_status="human_review_required",
            rolling_continue_permission="human_review_required",
            rolling_continue_reason="human_review_required",
            cooldown_status=cooldown_status,
            cooldown_reason=cooldown_reason,
            retry_hardening_status=retry_hardening_status,
            same_prompt_retry_remaining=same_prompt_retry_remaining,
            same_failure_count=same_failure_count,
            loop_risk_status=loop_risk_status,
            loop_risk_reason=loop_risk_reason,
            rolling_next_action="human_review",
        )
    if step_score_band in {"human_review_recommended", "blocked"}:
        return _base_state(
            rolling_gate_status="blocked",
            rolling_continue_permission="blocked",
            rolling_continue_reason="human_review_required",
            cooldown_status=cooldown_status,
            cooldown_reason=cooldown_reason,
            retry_hardening_status=retry_hardening_status,
            same_prompt_retry_remaining=same_prompt_retry_remaining,
            same_failure_count=same_failure_count,
            loop_risk_status=loop_risk_status,
            loop_risk_reason=loop_risk_reason,
            rolling_next_action="human_review",
        )

    return _insufficient_truth_state()

def _build_project_browser_autonomous_rolling_controller_candidate_state(
    *,
    autonomous_resume_status: str,
    autonomous_resume_permission: str,
    autonomous_resume_source_status: str,
    autonomous_resume_block_reason: str,
    autonomous_resume_receipt_status: str,
    autonomous_resume_next_allowed_action: str,
    autonomous_watchdog_status: str,
    autonomous_watchdog_permission: str,
    autonomous_watchdog_source_status: str,
    autonomous_watchdog_block_reason: str,
    autonomous_watchdog_receipt_status: str,
    autonomous_short_batch_stop_reason: str,
    autonomous_short_batch_steps_attempted: int,
    autonomous_run_ledger_persistence_status: str,
    autonomous_run_ledger_counter_posture: str,
    autonomous_run_ledger_persistence_target_status: str,
    autonomous_cooldown_status: str,
    autonomous_loop_risk_status: str,
) -> dict[str, Any]:
    resume_status = _normalize_text(
        autonomous_resume_status,
        default="insufficient_truth",
    )
    resume_permission = _normalize_text(
        autonomous_resume_permission,
        default="insufficient_truth",
    )
    resume_source_status = _normalize_text(
        autonomous_resume_source_status,
        default="insufficient_truth",
    )
    resume_block_reason = _normalize_text(
        autonomous_resume_block_reason,
        default="insufficient_truth",
    )
    resume_receipt_status = _normalize_text(
        autonomous_resume_receipt_status,
        default="insufficient_truth",
    )
    resume_next_allowed_action = _normalize_text(
        autonomous_resume_next_allowed_action,
        default="none",
    )
    watchdog_status = _normalize_text(
        autonomous_watchdog_status,
        default="insufficient_truth",
    )
    watchdog_permission = _normalize_text(
        autonomous_watchdog_permission,
        default="insufficient_truth",
    )
    watchdog_source_status = _normalize_text(
        autonomous_watchdog_source_status,
        default="insufficient_truth",
    )
    watchdog_block_reason = _normalize_text(
        autonomous_watchdog_block_reason,
        default="insufficient_truth",
    )
    watchdog_receipt_status = _normalize_text(
        autonomous_watchdog_receipt_status,
        default="insufficient_truth",
    )
    short_batch_stop_reason = _normalize_text(
        autonomous_short_batch_stop_reason,
        default="insufficient_truth",
    )
    short_batch_steps_attempted = _as_non_negative_int(
        autonomous_short_batch_steps_attempted,
        default=0,
    )
    run_ledger_status = _normalize_text(
        autonomous_run_ledger_persistence_status,
        default="insufficient_truth",
    )
    run_ledger_counter_posture = _normalize_text(
        autonomous_run_ledger_counter_posture,
        default="insufficient_truth",
    )
    run_ledger_persistence_target_status = _normalize_text(
        autonomous_run_ledger_persistence_target_status,
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

    runtime_posture = [
        "metadata_only_candidate",
        "bounded_rolling_controller_candidate_only",
        "no_next_batch_start",
        "no_resume_execution",
        "no_prompt_send",
        "no_md_write",
        "no_shell_execution",
        "no_browser_action",
        "no_playwright",
        "no_dom_interaction",
        "no_queue_mutation",
        "no_retry_execution",
        "no_repair_execution",
        "no_restart_execution",
        "no_approval_execution",
        "no_continuation_execution",
        "no_background_runtime",
    ]

    def _base_state(
        *,
        status: str,
        kind: str,
        permission: str,
        source_status: str,
        block_reason: str,
        receipt_status: str,
        receipt_kind: str,
        next_action: str,
    ) -> dict[str, Any]:
        return {
            "project_browser_autonomous_rolling_controller_status": status,
            "project_browser_autonomous_rolling_controller_kind": kind,
            "project_browser_autonomous_rolling_controller_permission": permission,
            "project_browser_autonomous_rolling_controller_source_status": source_status,
            "project_browser_autonomous_rolling_controller_block_reason": block_reason,
            "project_browser_autonomous_rolling_controller_receipt_status": receipt_status,
            "project_browser_autonomous_rolling_controller_receipt_kind": receipt_kind,
            "project_browser_autonomous_rolling_controller_next_action": next_action,
            "project_browser_autonomous_rolling_controller_runtime_posture": runtime_posture,
        }

    def _insufficient_truth_state(*, block_reason: str) -> dict[str, Any]:
        normalized_block_reason = (
            block_reason
            if block_reason in {"source_inconsistent", "insufficient_truth"}
            else "insufficient_truth"
        )
        return _base_state(
            status="insufficient_truth",
            kind="insufficient_truth_rolling_controller_candidate",
            permission="insufficient_truth",
            source_status="insufficient_truth",
            block_reason=normalized_block_reason,
            receipt_status="insufficient_truth",
            receipt_kind="insufficient_truth_rolling_controller_candidate_receipt",
            next_action="hold_insufficient_truth",
        )

    if resume_status not in {
        "inactive",
        "checkpoint_ready",
        "blocked",
        "stale",
        "failed",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if resume_permission not in _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if resume_source_status not in {"valid", "inconsistent", "insufficient_truth"}:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if resume_block_reason not in {
        "none",
        "short_batch_blocked",
        "short_batch_not_stopped_safely",
        "step_failed",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
        "source_inconsistent",
        "ledger_not_persisted",
        "cooldown_required",
        "loop_suspected",
        "manual_stop",
        "missing_receipt",
        "stale_receipt",
        "duplicate_receipt",
        "budget_exhausted",
        "failure_budget_exhausted",
        "retry_budget_exhausted",
        "duplicate_detected",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if resume_receipt_status not in {
        "ready",
        "blocked",
        "failed",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if resume_next_allowed_action not in {
        "none",
        "resume_from_checkpoint",
        "resume_next_short_batch_later",
        "hold_pause",
        "hold_human_review",
        "hold_insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if watchdog_status not in {
        "clear",
        "stale",
        "missing_receipt",
        "duplicate_receipt",
        "manual_stop",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if watchdog_permission not in _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if watchdog_source_status not in {"valid", "inconsistent", "insufficient_truth"}:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if watchdog_block_reason not in {
        "none",
        "insufficient_truth",
        "source_inconsistent",
        "manual_stop",
        "stale_receipt",
        "missing_receipt",
        "duplicate_receipt",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if watchdog_receipt_status not in {
        "ready",
        "blocked",
        "failed",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if short_batch_stop_reason not in {
        "none",
        "max_steps_reached",
        "budget_exhausted",
        "failure_budget_exhausted",
        "retry_budget_exhausted",
        "cooldown_required",
        "loop_suspected",
        "duplicate_detected",
        "ledger_not_persisted",
        "source_inconsistent",
        "step_failed",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if run_ledger_status not in {
        "inactive",
        "persisted",
        "prepared",
        "skipped",
        "blocked",
        "failed",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if run_ledger_counter_posture not in {
        "no_change",
        "would_increment_step",
        "would_increment_failure",
        "would_increment_retry",
        "persisted",
        "blocked",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if run_ledger_persistence_target_status not in {
        "unavailable",
        "existing_path_available",
        "metadata_only",
        "blocked",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if cooldown_status not in {"not_required", "required", "blocked", "insufficient_truth"}:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if loop_risk_status not in {"clear", "suspected", "blocked", "insufficient_truth"}:
        return _insufficient_truth_state(block_reason="source_inconsistent")

    if short_batch_steps_attempted > 3:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if (
        resume_source_status in {"inconsistent", "insufficient_truth"}
        or watchdog_source_status in {"inconsistent", "insufficient_truth"}
    ):
        return _insufficient_truth_state(
            block_reason=(
                "source_inconsistent"
                if "inconsistent" in {resume_source_status, watchdog_source_status}
                else "insufficient_truth"
            )
        )

    if (
        resume_permission == "insufficient_truth"
        or resume_status == "insufficient_truth"
        or resume_receipt_status == "insufficient_truth"
    ):
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if resume_permission == "pause_required" or resume_status == "pause_required":
        return _base_state(
            status="pause_required",
            kind="pause_rolling_controller_candidate",
            permission="pause_required",
            source_status="valid",
            block_reason="pause_required",
            receipt_status="pause_required",
            receipt_kind="pause_rolling_controller_candidate_receipt",
            next_action="hold_pause",
        )
    if resume_permission == "human_review_required" or resume_status == "human_review_required":
        return _base_state(
            status="human_review_required",
            kind="human_review_rolling_controller_candidate",
            permission="human_review_required",
            source_status="valid",
            block_reason="human_review_required",
            receipt_status="human_review_required",
            receipt_kind="human_review_rolling_controller_candidate_receipt",
            next_action="hold_human_review",
        )
    if resume_permission == "blocked" or resume_status in {"blocked", "failed", "stale"}:
        return _base_state(
            status="blocked",
            kind="blocked_rolling_controller_candidate",
            permission="blocked",
            source_status="valid",
            block_reason=(
                resume_block_reason
                if resume_block_reason
                in {
                    "step_failed",
                    "ledger_not_persisted",
                    "cooldown_required",
                    "loop_suspected",
                    "manual_stop",
                    "missing_receipt",
                    "stale_receipt",
                    "duplicate_receipt",
                }
                else "resume_not_allowed"
            ),
            receipt_status="blocked",
            receipt_kind="blocked_rolling_controller_candidate_receipt",
            next_action="none",
        )
    if resume_status == "inactive":
        return _base_state(
            status="inactive",
            kind="none",
            permission="blocked",
            source_status="valid",
            block_reason="resume_inactive",
            receipt_status="not_created",
            receipt_kind="none",
            next_action="none",
        )

    if (
        watchdog_status == "insufficient_truth"
        or watchdog_permission == "insufficient_truth"
        or watchdog_receipt_status == "insufficient_truth"
    ):
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if watchdog_status == "stale":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_controller_candidate",
            permission="blocked",
            source_status="valid",
            block_reason="stale_receipt",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_controller_candidate_receipt",
            next_action="none",
        )
    if watchdog_status == "missing_receipt":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_controller_candidate",
            permission="blocked",
            source_status="valid",
            block_reason="missing_receipt",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_controller_candidate_receipt",
            next_action="none",
        )
    if watchdog_status == "duplicate_receipt":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_controller_candidate",
            permission="blocked",
            source_status="valid",
            block_reason="duplicate_receipt",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_controller_candidate_receipt",
            next_action="none",
        )
    if watchdog_status == "manual_stop":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_controller_candidate",
            permission="blocked",
            source_status="valid",
            block_reason="manual_stop",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_controller_candidate_receipt",
            next_action="none",
        )
    if watchdog_permission in {"pause_required", "human_review_required"}:
        return _base_state(
            status=watchdog_permission,
            kind=(
                "pause_rolling_controller_candidate"
                if watchdog_permission == "pause_required"
                else "human_review_rolling_controller_candidate"
            ),
            permission=watchdog_permission,
            source_status="valid",
            block_reason=watchdog_permission,
            receipt_status=watchdog_permission,
            receipt_kind=(
                "pause_rolling_controller_candidate_receipt"
                if watchdog_permission == "pause_required"
                else "human_review_rolling_controller_candidate_receipt"
            ),
            next_action=(
                "hold_pause"
                if watchdog_permission == "pause_required"
                else "hold_human_review"
            ),
        )
    if watchdog_permission == "blocked":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_controller_candidate",
            permission="blocked",
            source_status="valid",
            block_reason=(
                watchdog_block_reason
                if watchdog_block_reason
                in {
                    "manual_stop",
                    "stale_receipt",
                    "missing_receipt",
                    "duplicate_receipt",
                }
                else "watchdog_not_allowed"
            ),
            receipt_status="blocked",
            receipt_kind="blocked_rolling_controller_candidate_receipt",
            next_action="none",
        )

    if resume_receipt_status != "ready":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_controller_candidate",
            permission="blocked",
            source_status="valid",
            block_reason="resume_receipt_not_ready",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_controller_candidate_receipt",
            next_action="none",
        )
    if watchdog_receipt_status != "ready":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_controller_candidate",
            permission="blocked",
            source_status="valid",
            block_reason="watchdog_receipt_not_ready",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_controller_candidate_receipt",
            next_action="none",
        )
    if resume_next_allowed_action != "resume_next_short_batch_later":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_controller_candidate",
            permission="blocked",
            source_status="valid",
            block_reason="next_action_not_allowed",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_controller_candidate_receipt",
            next_action="none",
        )
    if short_batch_stop_reason == "insufficient_truth":
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if short_batch_stop_reason != "max_steps_reached":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_controller_candidate",
            permission="blocked",
            source_status="valid",
            block_reason="short_batch_not_terminal_for_rolling",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_controller_candidate_receipt",
            next_action="none",
        )
    if (
        run_ledger_status == "insufficient_truth"
        or run_ledger_counter_posture == "insufficient_truth"
        or run_ledger_persistence_target_status == "insufficient_truth"
    ):
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if run_ledger_status == "prepared" or run_ledger_persistence_target_status == "metadata_only":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_controller_candidate",
            permission="blocked",
            source_status="valid",
            block_reason="ledger_not_persisted",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_controller_candidate_receipt",
            next_action="none",
        )
    if run_ledger_status != "persisted" or run_ledger_counter_posture != "persisted":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_controller_candidate",
            permission="blocked",
            source_status="valid",
            block_reason="ledger_not_persisted",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_controller_candidate_receipt",
            next_action="none",
        )
    if cooldown_status == "insufficient_truth" or loop_risk_status == "insufficient_truth":
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if cooldown_status != "not_required":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_controller_candidate",
            permission="blocked",
            source_status="valid",
            block_reason="cooldown_required",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_controller_candidate_receipt",
            next_action="none",
        )
    if loop_risk_status != "clear":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_controller_candidate",
            permission="blocked",
            source_status="valid",
            block_reason="loop_suspected",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_controller_candidate_receipt",
            next_action="none",
        )
    if resume_permission != "allowed_candidate" or watchdog_permission != "allowed_candidate":
        return _base_state(
            status="blocked",
            kind="blocked_rolling_controller_candidate",
            permission="blocked",
            source_status="valid",
            block_reason="resume_not_allowed",
            receipt_status="blocked",
            receipt_kind="blocked_rolling_controller_candidate_receipt",
            next_action="none",
        )

    return _base_state(
        status="prepared",
        kind="rolling_controller_candidate",
        permission="allowed_candidate",
        source_status="valid",
        block_reason="none",
        receipt_status="ready",
        receipt_kind="one_rolling_controller_candidate_receipt",
        next_action="prepare_next_short_batch_later",
    )

def _build_project_browser_autonomous_safe_patch_apply_gate_state(
    *,
    patch_candidate_status: str,
    patch_candidate_source_status: str,
    patch_candidate_block_reason: str,
    response_status: str,
    output_kind: str,
    expected_patch_path: str,
    touched_files: list[str] | None,
    forbidden_touched_files: list[str] | None,
    allowed_files: list[str] | None,
    forbidden_files: list[str] | None,
    unsafe_operation_flags: list[str] | None,
    human_review_required: bool,
    rollback_required: bool,
    worktree_status: str,
    worktree_dirty: bool | None,
) -> dict[str, Any]:
    allowed_output_kinds = {
        "patch_plan",
        "unified_diff",
        "full_file_replacement",
        "manual_steps",
        "instructions_only",
        "none",
    }
    patch_like_output_kinds = {"unified_diff", "full_file_replacement"}
    runtime_posture = [
        "metadata_only_safe_patch_apply_gate",
        "no_patch_writing",
        "no_patch_generation",
        "no_patch_application",
        "no_git_apply_execution",
        "no_git_reset",
        "no_git_clean",
        "no_autonomous_loop",
        "no_github_mutation",
    ]
    allowed_next_actions = {
        "wait_for_valid_patch_candidate",
        "prepare_dry_run_apply_later",
        "human_review_required",
        "rollback_required",
        "manual_fix_patch_candidate",
        "insufficient_truth",
    }

    normalized_patch_candidate_status = _normalize_text(
        patch_candidate_status,
        default="insufficient_truth",
    )
    normalized_patch_candidate_source_status = _normalize_text(
        patch_candidate_source_status,
        default="insufficient_truth",
    )
    normalized_patch_candidate_block_reason = _normalize_text(
        patch_candidate_block_reason,
        default="insufficient_truth",
    )
    normalized_response_status = _normalize_text(
        response_status,
        default="insufficient_truth",
    )
    normalized_output_kind = _normalize_text(output_kind, default="none")
    if normalized_output_kind not in allowed_output_kinds:
        normalized_output_kind = "none"
    normalized_expected_patch_path = _normalize_text(expected_patch_path, default="")
    normalized_touched_files = _normalize_string_list(touched_files or [])
    normalized_forbidden_touched_files = _normalize_string_list(
        forbidden_touched_files or []
    )
    normalized_allowed_files = _normalize_string_list(allowed_files or [])
    normalized_forbidden_files = _normalize_string_list(forbidden_files or [])
    normalized_unsafe_operation_flags = _normalize_string_list(
        unsafe_operation_flags or []
    )

    required_inputs = [
        "patch_candidate_status",
        "response_status",
        "output_kind",
        "expected_patch_path",
        "touched_files",
        "allowed_files",
        "forbidden_files",
    ]
    available_inputs: list[str] = []
    if normalized_patch_candidate_status:
        available_inputs.append("patch_candidate_status")
    if normalized_response_status:
        available_inputs.append("response_status")
    if normalized_output_kind and normalized_output_kind != "none":
        available_inputs.append("output_kind")
    if normalized_expected_patch_path:
        available_inputs.append("expected_patch_path")
    if normalized_touched_files:
        available_inputs.append("touched_files")
    if normalized_allowed_files:
        available_inputs.append("allowed_files")
    if normalized_forbidden_files:
        available_inputs.append("forbidden_files")
    missing_inputs = _serialize_required_signals(
        [
            input_name
            for input_name in required_inputs
            if input_name not in set(available_inputs)
        ]
    )

    normalized_worktree_status = _normalize_text(worktree_status, default="insufficient_truth")
    worktree_dirty_known = isinstance(worktree_dirty, bool)
    normalized_worktree_dirty = bool(worktree_dirty) if worktree_dirty_known else False
    if normalized_worktree_status in {"clean", "dirty"}:
        normalized_worktree_dirty = normalized_worktree_status == "dirty"
        worktree_dirty_known = True
    elif worktree_dirty_known:
        normalized_worktree_status = "dirty" if normalized_worktree_dirty else "clean"
    else:
        normalized_worktree_status = "insufficient_truth"

    def _normalize_repo_path(path_text: str) -> str:
        value = _normalize_text(path_text, default="")
        if not value:
            return ""
        value = value.replace("\\", "/")
        if value.startswith("a/") or value.startswith("b/"):
            value = value[2:]
        value = value.strip().strip("`").strip("\"")
        if value == "/dev/null":
            return ""
        return value

    def _path_matches_scope(candidate: str, scope_items: list[str]) -> bool:
        normalized_candidate = _normalize_repo_path(candidate)
        if not normalized_candidate:
            return False
        for scope_item in scope_items:
            normalized_scope = _normalize_repo_path(scope_item)
            if not normalized_scope:
                continue
            if normalized_candidate == normalized_scope:
                return True
            if normalized_candidate.startswith(normalized_scope.rstrip("/") + "/"):
                return True
        return False

    outside_allowed_files = _serialize_required_signals(
        [
            path
            for path in normalized_touched_files
            if normalized_allowed_files
            and not _path_matches_scope(path, normalized_allowed_files)
        ]
    )

    status = "insufficient_truth"
    source_status = "insufficient_truth"
    block_reason = "insufficient_truth"
    next_action = "insufficient_truth"
    dry_run_required = False
    dry_run_status = "not_ready"
    apply_allowed = False
    apply_performed = False
    validation_required = False
    validation_commands: list[str] = []

    if rollback_required:
        status = "blocked_rollback_required"
        source_status = "rollback_required"
        block_reason = "rollback_required"
        next_action = "rollback_required"
    elif human_review_required:
        status = "blocked_human_review_required"
        source_status = "human_review_required"
        block_reason = "human_review_required"
        next_action = "human_review_required"
    elif normalized_response_status == "waiting_for_manual_response":
        status = "blocked_waiting_for_manual_response"
        source_status = "response_waiting_for_manual_response"
        block_reason = "waiting_for_manual_response"
        next_action = "wait_for_valid_patch_candidate"
    elif normalized_patch_candidate_status == "insufficient_truth":
        status = "insufficient_truth"
        source_status = normalized_patch_candidate_source_status
        block_reason = "insufficient_truth"
        next_action = "insufficient_truth"
    elif normalized_patch_candidate_status == "waiting":
        status = "blocked_no_patch_candidate"
        source_status = normalized_patch_candidate_source_status
        block_reason = "patch_candidate_waiting"
        next_action = "wait_for_valid_patch_candidate"
    elif normalized_patch_candidate_status == "blocked":
        status = "blocked_invalid_candidate"
        source_status = normalized_patch_candidate_source_status
        block_reason = normalized_patch_candidate_block_reason or "invalid_patch_candidate"
        next_action = "manual_fix_patch_candidate"
    elif normalized_patch_candidate_status != "candidate_ready_for_later_gate":
        status = "blocked_no_patch_candidate"
        source_status = normalized_patch_candidate_source_status
        block_reason = "patch_candidate_not_ready"
        next_action = "wait_for_valid_patch_candidate"
    elif normalized_output_kind not in patch_like_output_kinds:
        status = "blocked_output_kind"
        source_status = "patch_candidate_ready"
        block_reason = "patch_candidate_output_kind_not_patch_like"
        next_action = "manual_fix_patch_candidate"
    elif normalized_output_kind == "full_file_replacement":
        status = "blocked_output_kind"
        source_status = "patch_candidate_ready"
        block_reason = "full_file_replacement_requires_human_review"
        next_action = "human_review_required"
    elif not normalized_expected_patch_path:
        status = "blocked_missing_patch_path"
        source_status = "patch_candidate_ready"
        block_reason = "missing_expected_patch_path"
        next_action = "manual_fix_patch_candidate"
        missing_inputs = _serialize_required_signals(
            [*missing_inputs, "expected_patch_path"]
        )
    elif not Path(normalized_expected_patch_path).exists():
        status = "blocked_missing_patch_path"
        source_status = "patch_candidate_ready"
        block_reason = "expected_patch_path_unavailable"
        next_action = "manual_fix_patch_candidate"
    elif not normalized_touched_files:
        status = "blocked_missing_touched_files"
        source_status = "patch_candidate_ready"
        block_reason = "missing_touched_files_for_patch_like_candidate"
        next_action = "manual_fix_patch_candidate"
        missing_inputs = _serialize_required_signals([*missing_inputs, "touched_files"])
    elif not normalized_allowed_files or not normalized_forbidden_files:
        status = "insufficient_truth"
        source_status = "missing_scope_constraints"
        block_reason = "missing_scope_constraints"
        next_action = "insufficient_truth"
        if not normalized_allowed_files:
            missing_inputs = _serialize_required_signals([*missing_inputs, "allowed_files"])
        if not normalized_forbidden_files:
            missing_inputs = _serialize_required_signals([*missing_inputs, "forbidden_files"])
    elif normalized_forbidden_touched_files or outside_allowed_files:
        status = "blocked_forbidden_files"
        source_status = "patch_candidate_ready"
        block_reason = "forbidden_or_out_of_scope_files_touched"
        next_action = "manual_fix_patch_candidate"
    elif normalized_unsafe_operation_flags:
        status = "blocked_unsafe_operations"
        source_status = "patch_candidate_ready"
        block_reason = "unsafe_operations_detected"
        next_action = "manual_fix_patch_candidate"
    elif not worktree_dirty_known or normalized_worktree_status == "insufficient_truth":
        status = "insufficient_truth"
        source_status = "worktree_truth_unavailable"
        block_reason = "worktree_truth_unavailable"
        next_action = "insufficient_truth"
    elif normalized_worktree_dirty:
        status = "blocked_dirty_worktree"
        source_status = "worktree_dirty"
        block_reason = "dirty_worktree"
        next_action = "manual_fix_patch_candidate"
    else:
        status = "ready_for_dry_run_later"
        source_status = "safe_patch_candidate_ready"
        block_reason = "none"
        next_action = "prepare_dry_run_apply_later"
        dry_run_required = True
        dry_run_status = "required_not_performed"
        validation_required = True
        validation_commands = [
            f"git apply --check {normalized_expected_patch_path}",
        ]

    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"

    safe_candidate_status = "insufficient_truth"
    if normalized_patch_candidate_status == "candidate_ready_for_later_gate":
        safe_candidate_status = "candidate_ready_for_later_gate"
    elif normalized_patch_candidate_status in {"blocked", "waiting", "insufficient_truth"}:
        safe_candidate_status = normalized_patch_candidate_status

    validation_status = status
    validation_source_status = source_status
    validation_block_reason = block_reason
    validation_next_action = next_action

    return {
        "project_browser_autonomous_safe_patch_apply_gate_status": status,
        "project_browser_autonomous_safe_patch_apply_gate_source_status": source_status,
        "project_browser_autonomous_safe_patch_apply_gate_block_reason": block_reason,
        "project_browser_autonomous_safe_patch_apply_gate_patch_candidate_status": (
            normalized_patch_candidate_status
        ),
        "project_browser_autonomous_safe_patch_apply_gate_expected_patch_path": (
            normalized_expected_patch_path
        ),
        "project_browser_autonomous_safe_patch_apply_gate_touched_files": (
            normalized_touched_files
        ),
        "project_browser_autonomous_safe_patch_apply_gate_forbidden_touched_files": (
            _serialize_required_signals(
                [*normalized_forbidden_touched_files, *outside_allowed_files]
            )
        ),
        "project_browser_autonomous_safe_patch_apply_gate_allowed_files": (
            normalized_allowed_files
        ),
        "project_browser_autonomous_safe_patch_apply_gate_forbidden_files": (
            normalized_forbidden_files
        ),
        "project_browser_autonomous_safe_patch_apply_gate_worktree_status": (
            normalized_worktree_status
        ),
        "project_browser_autonomous_safe_patch_apply_gate_worktree_dirty": (
            bool(normalized_worktree_dirty)
        ),
        "project_browser_autonomous_safe_patch_apply_gate_dry_run_required": (
            bool(dry_run_required)
        ),
        "project_browser_autonomous_safe_patch_apply_gate_dry_run_status": (
            dry_run_status
        ),
        "project_browser_autonomous_safe_patch_apply_gate_apply_allowed": (
            bool(apply_allowed)
        ),
        "project_browser_autonomous_safe_patch_apply_gate_apply_performed": (
            bool(apply_performed)
        ),
        "project_browser_autonomous_safe_patch_apply_gate_validation_required": (
            bool(validation_required)
        ),
        "project_browser_autonomous_safe_patch_apply_gate_validation_commands": (
            _normalize_string_list(validation_commands)
        ),
        "project_browser_autonomous_safe_patch_apply_gate_missing_inputs": (
            missing_inputs
        ),
        "project_browser_autonomous_safe_patch_apply_gate_next_action": next_action,
        "project_browser_autonomous_safe_patch_apply_gate_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_safe_patch_apply_candidate_status": (
            safe_candidate_status
        ),
        "project_browser_autonomous_safe_patch_apply_candidate_source_status": (
            normalized_patch_candidate_source_status
        ),
        "project_browser_autonomous_safe_patch_apply_candidate_block_reason": (
            normalized_patch_candidate_block_reason
        ),
        "project_browser_autonomous_safe_patch_apply_candidate_patch_candidate_status": (
            normalized_patch_candidate_status
        ),
        "project_browser_autonomous_safe_patch_apply_candidate_expected_patch_path": (
            normalized_expected_patch_path
        ),
        "project_browser_autonomous_safe_patch_apply_candidate_touched_files": (
            normalized_touched_files
        ),
        "project_browser_autonomous_safe_patch_apply_candidate_forbidden_touched_files": (
            _serialize_required_signals(
                [*normalized_forbidden_touched_files, *outside_allowed_files]
            )
        ),
        "project_browser_autonomous_safe_patch_apply_candidate_allowed_files": (
            normalized_allowed_files
        ),
        "project_browser_autonomous_safe_patch_apply_candidate_forbidden_files": (
            normalized_forbidden_files
        ),
        "project_browser_autonomous_safe_patch_apply_candidate_worktree_status": (
            normalized_worktree_status
        ),
        "project_browser_autonomous_safe_patch_apply_candidate_worktree_dirty": (
            bool(normalized_worktree_dirty)
        ),
        "project_browser_autonomous_safe_patch_apply_candidate_dry_run_required": (
            bool(dry_run_required)
        ),
        "project_browser_autonomous_safe_patch_apply_candidate_dry_run_status": (
            dry_run_status
        ),
        "project_browser_autonomous_safe_patch_apply_candidate_apply_allowed": (
            bool(apply_allowed)
        ),
        "project_browser_autonomous_safe_patch_apply_candidate_apply_performed": (
            bool(apply_performed)
        ),
        "project_browser_autonomous_safe_patch_apply_candidate_validation_required": (
            bool(validation_required)
        ),
        "project_browser_autonomous_safe_patch_apply_candidate_validation_commands": (
            _normalize_string_list(validation_commands)
        ),
        "project_browser_autonomous_safe_patch_apply_candidate_next_action": (
            next_action
        ),
        "project_browser_autonomous_safe_patch_apply_candidate_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_safe_patch_apply_validation_status": (
            validation_status
        ),
        "project_browser_autonomous_safe_patch_apply_validation_source_status": (
            validation_source_status
        ),
        "project_browser_autonomous_safe_patch_apply_validation_block_reason": (
            validation_block_reason
        ),
        "project_browser_autonomous_safe_patch_apply_validation_patch_candidate_status": (
            normalized_patch_candidate_status
        ),
        "project_browser_autonomous_safe_patch_apply_validation_expected_patch_path": (
            normalized_expected_patch_path
        ),
        "project_browser_autonomous_safe_patch_apply_validation_touched_files": (
            normalized_touched_files
        ),
        "project_browser_autonomous_safe_patch_apply_validation_forbidden_touched_files": (
            _serialize_required_signals(
                [*normalized_forbidden_touched_files, *outside_allowed_files]
            )
        ),
        "project_browser_autonomous_safe_patch_apply_validation_allowed_files": (
            normalized_allowed_files
        ),
        "project_browser_autonomous_safe_patch_apply_validation_forbidden_files": (
            normalized_forbidden_files
        ),
        "project_browser_autonomous_safe_patch_apply_validation_worktree_status": (
            normalized_worktree_status
        ),
        "project_browser_autonomous_safe_patch_apply_validation_worktree_dirty": (
            bool(normalized_worktree_dirty)
        ),
        "project_browser_autonomous_safe_patch_apply_validation_dry_run_required": (
            bool(dry_run_required)
        ),
        "project_browser_autonomous_safe_patch_apply_validation_dry_run_status": (
            dry_run_status
        ),
        "project_browser_autonomous_safe_patch_apply_validation_apply_allowed": (
            bool(apply_allowed)
        ),
        "project_browser_autonomous_safe_patch_apply_validation_apply_performed": (
            bool(apply_performed)
        ),
        "project_browser_autonomous_safe_patch_apply_validation_validation_required": (
            bool(validation_required)
        ),
        "project_browser_autonomous_safe_patch_apply_validation_validation_commands": (
            _normalize_string_list(validation_commands)
        ),
        "project_browser_autonomous_safe_patch_apply_validation_missing_inputs": (
            missing_inputs
        ),
        "project_browser_autonomous_safe_patch_apply_validation_next_action": (
            validation_next_action
        ),
        "project_browser_autonomous_safe_patch_apply_validation_runtime_posture": (
            runtime_posture
        ),
    }

def _build_project_browser_autonomous_bounded_continuation_controller_state(
    *,
    source_status: str,
    source_post_reentry_cycle_status: str,
    source_post_reentry_cycle_passed: bool,
    source_post_reentry_cycle_failed: bool,
    source_post_reentry_cycle_blocked: bool,
    source_post_reentry_cycle_block_reason: str,
    source_continuation_candidate: bool,
    source_continuation_prompt_kind: str,
    source_continuation_next_action: str,
    source_rollback_candidate: bool,
    source_rollback_reason: str,
    source_human_review_required: bool,
    source_manual_review_required: bool,
    source_next_action: str,
    reentry_invocation_attempted: bool,
    existing_cycle_index: int,
    existing_fix_attempt_index: int,
    existing_reentry_invocations_used: int,
    existing_failure_count: int,
) -> dict[str, Any]:
    allowed_statuses = {
        "continuation_allowed_next",
        "continuation_allowed_fix",
        "continuation_blocked_rollback_required",
        "continuation_blocked_manual_review_required",
        "continuation_blocked_cycle_budget_exhausted",
        "continuation_blocked_fix_budget_exhausted",
        "continuation_blocked_failure_budget_exhausted",
        "continuation_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "generate_next_prompt",
        "generate_fix_prompt",
        "prepare_rollback",
        "manual_review_required",
        "stop_bounded_continuation",
        "insufficient_truth",
    }
    max_cycles = 2
    max_fix_attempts = 1
    max_reentry_invocations = 1
    failure_budget = 1
    runtime_posture = [
        "prompt183_bounded_continuation_controller",
        "metadata_only_controller",
        "authoritative_prompt182_source",
        "no_prompt_generation",
        "no_codex_invocation",
        "no_cycle_start",
        "no_rollback_execution",
        "no_commit",
    ]

    normalized_source_status = _normalize_text(source_status, default="insufficient_truth")
    normalized_cycle_status = _normalize_text(
        source_post_reentry_cycle_status,
        default="insufficient_truth",
    )
    normalized_cycle_block_reason = _normalize_text(
        source_post_reentry_cycle_block_reason,
        default="",
    )
    normalized_continuation_prompt_kind = _normalize_text(
        source_continuation_prompt_kind,
        default="none",
    )
    if normalized_continuation_prompt_kind not in {"next", "fix", "none"}:
        normalized_continuation_prompt_kind = "none"
    normalized_continuation_next_action = _normalize_text(
        source_continuation_next_action,
        default="",
    )
    normalized_rollback_reason = _normalize_text(source_rollback_reason, default="")
    normalized_source_next_action = _normalize_text(source_next_action, default="")

    cycle_index = _as_non_negative_int(existing_cycle_index, default=1)
    if cycle_index <= 0:
        cycle_index = 1
    remaining_cycles = max(max_cycles - cycle_index, 0)

    fix_attempt_index = _as_non_negative_int(existing_fix_attempt_index, default=0)
    remaining_fix_attempts = max(max_fix_attempts - fix_attempt_index, 0)

    reentry_invocations_used = _as_non_negative_int(
        existing_reentry_invocations_used,
        default=1 if reentry_invocation_attempted else 0,
    )

    prompt182_failed = bool(source_post_reentry_cycle_failed) or bool(
        normalized_source_status
        in {
            "post_reentry_safety_refresh_validation_failed",
            "post_reentry_safety_refresh_invocation_failure",
        }
    )
    failure_count = _as_non_negative_int(
        existing_failure_count,
        default=1 if prompt182_failed else 0,
    )

    authoritative_continuation_source = (
        "project_browser_autonomous_post_reentry_safety_refresh"
        if normalized_source_status
        else "none"
    )
    continuation_allowed = False
    continuation_block_reason = "blocked_insufficient_continuation_truth"
    continuation_prompt_kind = "none"
    continuation_next_action = "manual_review_required"
    rollback_required = False
    rollback_candidate = bool(source_rollback_candidate)
    rollback_reason = normalized_rollback_reason
    should_generate_next_prompt = False
    should_generate_fix_prompt = False
    should_invoke_codex = False
    should_start_next_cycle = False
    should_rollback = False
    should_commit = False
    human_review_required = bool(source_human_review_required)
    manual_review_required = bool(source_manual_review_required)
    stop_reason = "insufficient_truth"
    next_action = "manual_review_required"
    status = "continuation_blocked_insufficient_truth"

    unsafe_or_timeout_source = bool(
        source_rollback_candidate
        or normalized_source_status
        in {
            "blocked_post_reentry_unsafe_changes",
            "post_reentry_safety_refresh_validation_timeout",
            "post_reentry_safety_refresh_invocation_timeout",
        }
    )
    if unsafe_or_timeout_source and not rollback_reason:
        rollback_reason = "post_reentry_rollback_required"

    # Priority 1: manual review
    if bool(source_human_review_required) or bool(source_manual_review_required):
        status = "continuation_blocked_manual_review_required"
        continuation_allowed = False
        continuation_block_reason = "manual_review_required"
        rollback_required = bool(source_rollback_candidate)
        stop_reason = "manual_review_required"
        next_action = "manual_review_required"
        human_review_required = True
        manual_review_required = True
    # Priority 2: rollback / unsafe / timeout
    elif unsafe_or_timeout_source:
        status = "continuation_blocked_rollback_required"
        continuation_allowed = False
        continuation_block_reason = "rollback_required"
        rollback_required = True
        rollback_candidate = True
        stop_reason = "rollback_required"
        next_action = "prepare_rollback"
        human_review_required = bool(source_human_review_required)
        manual_review_required = bool(source_manual_review_required)
    # Priority 3: budget exhaustion
    elif (
        normalized_continuation_prompt_kind == "next"
        and remaining_cycles <= 0
        and bool(source_continuation_candidate)
    ):
        status = "continuation_blocked_cycle_budget_exhausted"
        continuation_allowed = False
        continuation_block_reason = "cycle_budget_exhausted"
        stop_reason = "cycle_budget_exhausted"
        next_action = "stop_bounded_continuation"
        human_review_required = False
        manual_review_required = False
    elif (
        normalized_continuation_prompt_kind == "fix"
        and remaining_fix_attempts <= 0
        and bool(source_continuation_candidate)
    ):
        status = "continuation_blocked_fix_budget_exhausted"
        continuation_allowed = False
        continuation_block_reason = "fix_budget_exhausted"
        rollback_candidate = True
        rollback_reason = "fix_budget_exhausted"
        stop_reason = "fix_budget_exhausted"
        next_action = "prepare_rollback"
        human_review_required = False
        manual_review_required = False
    elif failure_count > failure_budget:
        status = "continuation_blocked_failure_budget_exhausted"
        continuation_allowed = False
        continuation_block_reason = "failure_budget_exhausted"
        rollback_candidate = True
        rollback_reason = "failure_budget_exhausted"
        stop_reason = "failure_budget_exhausted"
        next_action = "prepare_rollback"
        human_review_required = False
        manual_review_required = False
    # Priority 4: next continuation allowed
    elif (
        bool(source_post_reentry_cycle_passed)
        and bool(source_continuation_candidate)
        and normalized_continuation_prompt_kind == "next"
        and not bool(source_human_review_required)
        and not bool(source_rollback_candidate)
        and remaining_cycles > 0
    ):
        status = "continuation_allowed_next"
        continuation_allowed = True
        continuation_block_reason = ""
        continuation_prompt_kind = "next"
        continuation_next_action = (
            "generate_next_prompt"
            if normalized_continuation_next_action != "generate_next_prompt"
            else normalized_continuation_next_action
        )
        should_generate_next_prompt = True
        should_generate_fix_prompt = False
        rollback_required = False
        rollback_candidate = False
        rollback_reason = ""
        human_review_required = False
        manual_review_required = False
        stop_reason = ""
        next_action = "generate_next_prompt"
    # Priority 5: fix continuation allowed
    elif (
        bool(source_post_reentry_cycle_failed)
        and bool(source_continuation_candidate)
        and normalized_continuation_prompt_kind == "fix"
        and not bool(source_human_review_required)
        and remaining_fix_attempts > 0
        and failure_count <= failure_budget
    ):
        status = "continuation_allowed_fix"
        continuation_allowed = True
        continuation_block_reason = ""
        continuation_prompt_kind = "fix"
        continuation_next_action = (
            "generate_fix_prompt"
            if normalized_continuation_next_action != "generate_fix_prompt"
            else normalized_continuation_next_action
        )
        should_generate_next_prompt = False
        should_generate_fix_prompt = True
        rollback_required = False
        human_review_required = False
        manual_review_required = False
        stop_reason = ""
        next_action = "generate_fix_prompt"
    # Priority 6: fallback insufficient truth
    else:
        status = "continuation_blocked_insufficient_truth"
        continuation_allowed = False
        continuation_block_reason = "blocked_insufficient_continuation_truth"
        continuation_prompt_kind = (
            normalized_continuation_prompt_kind
            if normalized_continuation_prompt_kind in {"fix", "next"}
            else "none"
        )
        continuation_next_action = (
            normalized_continuation_next_action
            if normalized_continuation_next_action
            else normalized_source_next_action
        )
        human_review_required = True
        manual_review_required = True
        stop_reason = "insufficient_truth"
        next_action = "manual_review_required"

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"
    if continuation_next_action not in {
        "generate_next_prompt",
        "generate_fix_prompt",
        "prepare_rollback",
        "manual_review_required",
        "stop_bounded_continuation",
        "",
    }:
        continuation_next_action = "manual_review_required"

    return {
        "project_browser_autonomous_bounded_continuation_controller_status": status,
        "project_browser_autonomous_bounded_continuation_controller_authoritative_continuation_source": (
            authoritative_continuation_source
        ),
        "project_browser_autonomous_bounded_continuation_controller_continuation_allowed": bool(
            continuation_allowed
        ),
        "project_browser_autonomous_bounded_continuation_controller_continuation_block_reason": (
            continuation_block_reason
        ),
        "project_browser_autonomous_bounded_continuation_controller_continuation_prompt_kind": (
            continuation_prompt_kind
        ),
        "project_browser_autonomous_bounded_continuation_controller_continuation_next_action": (
            continuation_next_action
        ),
        "project_browser_autonomous_bounded_continuation_controller_max_cycles": int(max_cycles),
        "project_browser_autonomous_bounded_continuation_controller_cycle_index": int(
            cycle_index
        ),
        "project_browser_autonomous_bounded_continuation_controller_remaining_cycles": int(
            remaining_cycles
        ),
        "project_browser_autonomous_bounded_continuation_controller_max_fix_attempts": int(
            max_fix_attempts
        ),
        "project_browser_autonomous_bounded_continuation_controller_fix_attempt_index": int(
            fix_attempt_index
        ),
        "project_browser_autonomous_bounded_continuation_controller_remaining_fix_attempts": int(
            remaining_fix_attempts
        ),
        "project_browser_autonomous_bounded_continuation_controller_max_reentry_invocations": int(
            max_reentry_invocations
        ),
        "project_browser_autonomous_bounded_continuation_controller_reentry_invocations_used": int(
            reentry_invocations_used
        ),
        "project_browser_autonomous_bounded_continuation_controller_failure_budget": int(
            failure_budget
        ),
        "project_browser_autonomous_bounded_continuation_controller_failure_count": int(
            failure_count
        ),
        "project_browser_autonomous_bounded_continuation_controller_rollback_required": bool(
            rollback_required
        ),
        "project_browser_autonomous_bounded_continuation_controller_rollback_candidate": bool(
            rollback_candidate
        ),
        "project_browser_autonomous_bounded_continuation_controller_rollback_reason": (
            rollback_reason
        ),
        "project_browser_autonomous_bounded_continuation_controller_should_generate_next_prompt": bool(
            should_generate_next_prompt
        ),
        "project_browser_autonomous_bounded_continuation_controller_should_generate_fix_prompt": bool(
            should_generate_fix_prompt
        ),
        "project_browser_autonomous_bounded_continuation_controller_should_invoke_codex": bool(
            should_invoke_codex
        ),
        "project_browser_autonomous_bounded_continuation_controller_should_start_next_cycle": bool(
            should_start_next_cycle
        ),
        "project_browser_autonomous_bounded_continuation_controller_should_rollback": bool(
            should_rollback
        ),
        "project_browser_autonomous_bounded_continuation_controller_should_commit": bool(
            should_commit
        ),
        "project_browser_autonomous_bounded_continuation_controller_human_review_required": bool(
            human_review_required
        ),
        "project_browser_autonomous_bounded_continuation_controller_manual_review_required": bool(
            manual_review_required
        ),
        "project_browser_autonomous_bounded_continuation_controller_stop_reason": stop_reason,
        "project_browser_autonomous_bounded_continuation_controller_next_action": next_action,
        "project_browser_autonomous_bounded_continuation_controller_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_bounded_continuation_controller_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_source_status,
                    normalized_cycle_status,
                    normalized_cycle_block_reason,
                    normalized_source_next_action,
                    "authoritative_source_missing"
                    if authoritative_continuation_source == "none"
                    else "",
                ]
            )
        ),
    }

def _build_project_browser_autonomous_lane_contract_guard_state(
    *,
    terminal_lane_status: str,
    selected_lane: str,
    selected_lane_allowed: bool,
    selected_lane_block_reason: str,
    selected_lane_source: str,
    selected_lane_priority: str,
    lane_contract_ready: bool,
    lane_contract_kind: str,
    lane_contract_action: str,
    lane_contract_payload: Any,
    lane_conflict_detected: bool,
    conflicting_lanes: Sequence[Any],
    controller_status: str,
    controller_next_action: str,
    controller_allowed: bool,
    manual_review_required: bool,
    should_stop: bool,
    stop_reason: str,
    should_generate_next_prompt: bool,
    should_generate_fix_prompt: bool,
    should_prepare_rollback: bool,
    should_prepare_commit: bool,
    should_prepare_github_handoff: bool,
    should_invoke_codex: bool,
    should_execute_rollback: bool,
    should_execute_commit: bool,
    should_push: bool,
    next_action: str,
    multi_cycle_controller_status: str,
    commit_tag_result_assimilation_status: str,
    post_rollback_fix_reentry_result_assimilation_status: str,
) -> dict[str, Any]:
    allowed_lanes = {
        "next_prompt_lane",
        "fix_prompt_lane",
        "rollback_readiness_lane",
        "commit_readiness_lane",
        "manual_stop_lane",
        "github_readiness_lane",
    }
    validated_lanes = {
        "next_prompt_lane",
        "fix_prompt_lane",
        "rollback_readiness_lane",
        "commit_readiness_lane",
        "manual_stop_lane",
    }
    allowed_statuses = {
        "lane_contract_guard_valid_next_prompt",
        "lane_contract_guard_valid_fix_prompt",
        "lane_contract_guard_valid_rollback_readiness",
        "lane_contract_guard_valid_commit_readiness",
        "lane_contract_guard_manual_stop",
        "lane_contract_guard_blocked_malformed_contract",
        "lane_contract_guard_blocked_conflict",
        "lane_contract_guard_blocked_github_not_enabled",
        "lane_contract_guard_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "refresh_next_prompt_lane",
        "refresh_fix_prompt_lane",
        "refresh_rollback_readiness_lane",
        "refresh_commit_readiness_lane",
        "manual_review_required",
        "insufficient_truth",
    }
    runtime_posture = [
        "prompt199_lane_contract_guard",
        "metadata_only",
        "single_lane_validation",
        "no_execution",
        "no_codex_invocation",
        "no_git_mutation",
        "no_rollback_execution",
        "no_push",
    ]
    lane_action_allowlist: dict[str, str] = {
        "next_prompt_lane": "prepare_next_prompt_generation",
        "fix_prompt_lane": "prepare_fix_prompt_generation",
        "rollback_readiness_lane": "prepare_rollback_readiness",
        "commit_readiness_lane": "prepare_commit_tag_readiness",
        "manual_stop_lane": "manual_review_required",
    }

    normalized_terminal_lane_status = _normalize_text(terminal_lane_status, default="insufficient_truth")
    normalized_selected_lane = _normalize_text(selected_lane, default="")
    normalized_selected_lane_block_reason = _normalize_text(selected_lane_block_reason, default="")
    normalized_selected_lane_source = _normalize_text(selected_lane_source, default="")
    normalized_selected_lane_priority = _normalize_text(selected_lane_priority, default="")
    normalized_lane_contract_kind = _normalize_text(lane_contract_kind, default="")
    normalized_lane_contract_action = _normalize_text(lane_contract_action, default="")
    normalized_controller_status = _normalize_text(controller_status, default="insufficient_truth")
    normalized_controller_next_action = _normalize_text(controller_next_action, default="")
    normalized_stop_reason = _normalize_text(stop_reason, default="")
    normalized_next_action = _normalize_text(next_action, default="")
    normalized_multi_cycle_controller_status = _normalize_text(
        multi_cycle_controller_status,
        default="insufficient_truth",
    )
    normalized_commit_tag_result_assimilation_status = _normalize_text(
        commit_tag_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_post_rollback_fix_reentry_result_assimilation_status = _normalize_text(
        post_rollback_fix_reentry_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_conflicting_lanes = _normalize_string_list(conflicting_lanes)
    payload_mapping = dict(lane_contract_payload) if isinstance(lane_contract_payload, Mapping) else None
    payload_object = payload_mapping if payload_mapping is not None else {}
    payload_lane = _normalize_text(payload_object.get("lane"), default="")
    payload_source = _normalize_text(payload_object.get("source"), default="")
    payload_next_action = _normalize_text(payload_object.get("next_action"), default="")
    payload_prompt_kind = _normalize_text(payload_object.get("prompt_kind"), default="")

    contract_schema_valid = bool(
        isinstance(payload_mapping, Mapping)
        and bool(payload_lane)
        and bool(payload_source)
        and bool(payload_next_action)
    )
    contract_payload_lane_matches_selection = bool(
        contract_schema_valid
        and payload_lane == normalized_selected_lane
        and normalized_lane_contract_kind == normalized_selected_lane
    )
    contract_action_matches_payload = bool(
        contract_schema_valid and normalized_lane_contract_action == payload_next_action
    )

    lane_action_allowed = False
    lane_requirement_valid = False
    if normalized_selected_lane == "next_prompt_lane":
        lane_action_allowed = payload_next_action == lane_action_allowlist["next_prompt_lane"]
        lane_requirement_valid = bool(
            payload_prompt_kind == "next"
            and _as_non_negative_int(payload_object.get("remaining_cycles"), default=-1) >= 0
            and _as_non_negative_int(payload_object.get("max_cycles"), default=0) >= 1
        )
    elif normalized_selected_lane == "fix_prompt_lane":
        lane_action_allowed = payload_next_action == lane_action_allowlist["fix_prompt_lane"]
        lane_requirement_valid = bool(
            payload_prompt_kind == "fix"
            and _as_non_negative_int(payload_object.get("remaining_fix_attempts"), default=-1) >= 0
        )
    elif normalized_selected_lane == "rollback_readiness_lane":
        lane_action_allowed = payload_next_action == lane_action_allowlist["rollback_readiness_lane"]
        lane_requirement_valid = bool(
            _as_non_negative_int(payload_object.get("remaining_rollback_attempts"), default=-1) >= 0
        )
    elif normalized_selected_lane == "commit_readiness_lane":
        lane_action_allowed = payload_next_action == lane_action_allowlist["commit_readiness_lane"]
        lane_requirement_valid = bool(
            _as_non_negative_int(payload_object.get("remaining_commits"), default=-1) >= 0
        )
    elif normalized_selected_lane == "manual_stop_lane":
        lane_action_allowed = payload_next_action == lane_action_allowlist["manual_stop_lane"]
        lane_requirement_valid = bool(_normalize_text(payload_object.get("stop_reason"), default=""))
    elif normalized_selected_lane == "github_readiness_lane":
        lane_action_allowed = False
        lane_requirement_valid = False

    contract_action_allowed = bool(
        contract_schema_valid and contract_action_matches_payload and lane_action_allowed and lane_requirement_valid
    )
    github_lane_trace_detected = bool(
        normalized_selected_lane == "github_readiness_lane"
        or normalized_lane_contract_kind == "github_readiness_lane"
        or payload_lane == "github_readiness_lane"
        or payload_source == "github_readiness_lane"
        or normalized_selected_lane_block_reason in {
            "github_readiness_not_enabled",
            "github_lane_not_enabled",
        }
        or payload_next_action == "github_readiness_not_enabled"
    )
    contract_manual_stop = bool(
        normalized_selected_lane == "manual_stop_lane" or manual_review_required or should_stop
    )
    contract_conflict_detected = bool(lane_conflict_detected)

    block_reason = ""
    if normalized_terminal_lane_status in {"insufficient_truth", ""}:
        block_reason = "blocked_terminal_lane_not_ready"
    elif not normalized_selected_lane:
        block_reason = "blocked_selected_lane_missing"
    elif github_lane_trace_detected:
        block_reason = "blocked_github_lane_not_enabled"
    elif normalized_selected_lane not in validated_lanes:
        block_reason = "blocked_selected_lane_not_allowed"
    elif not selected_lane_allowed:
        block_reason = "blocked_selected_lane_not_allowed"
    elif not lane_contract_ready:
        block_reason = "blocked_lane_contract_not_ready"
    elif not isinstance(payload_mapping, Mapping):
        block_reason = "blocked_lane_contract_not_dict"
    elif not payload_lane:
        block_reason = "blocked_lane_payload_missing_lane"
    elif not payload_source:
        block_reason = "blocked_lane_payload_missing_source"
    elif not payload_next_action:
        block_reason = "blocked_lane_payload_missing_next_action"
    elif payload_lane != normalized_selected_lane:
        block_reason = "blocked_lane_payload_mismatch"
    elif normalized_lane_contract_kind != normalized_selected_lane:
        block_reason = "blocked_lane_kind_mismatch"
    elif normalized_lane_contract_action != payload_next_action:
        block_reason = "blocked_lane_action_mismatch"
    elif not lane_action_allowed or not lane_requirement_valid:
        block_reason = "blocked_lane_action_not_allowed"
    elif contract_conflict_detected:
        block_reason = "blocked_lane_conflict_detected"
    elif normalized_conflicting_lanes:
        block_reason = "blocked_conflicting_lanes_present"
    elif should_invoke_codex:
        block_reason = "blocked_unexpected_codex_invocation_flag"
    elif should_execute_rollback:
        block_reason = "blocked_unexpected_rollback_execution_flag"
    elif should_execute_commit:
        block_reason = "blocked_unexpected_commit_execution_flag"
    elif should_push:
        block_reason = "blocked_unexpected_push_flag"
    elif not contract_schema_valid or not contract_payload_lane_matches_selection:
        block_reason = "blocked_insufficient_lane_contract_truth"

    status = "lane_contract_guard_blocked_insufficient_truth"
    guarded_lane = "manual_stop_lane"
    guarded_lane_allowed = False
    guarded_lane_block_reason = block_reason or "blocked_insufficient_lane_contract_truth"
    guarded_lane_source = normalized_selected_lane_source or "terminal_lane_decision"
    guarded_contract_ready = False
    guarded_contract_kind = "manual_stop_lane"
    guarded_contract_action = "manual_review_required"
    guarded_contract_payload: dict[str, Any] = {
        "lane": "manual_stop_lane",
        "source": guarded_lane_source,
        "stop_reason": normalized_stop_reason or guarded_lane_block_reason,
        "next_action": "manual_review_required",
    }
    downstream_refresh_allowed = False
    downstream_refresh_kind = "manual_stop_lane"
    out_should_generate_next_prompt = False
    out_should_generate_fix_prompt = False
    out_should_prepare_rollback = False
    out_should_prepare_commit = False
    out_should_prepare_github_handoff = False
    out_should_invoke_codex = False
    out_should_execute_rollback = False
    out_should_execute_commit = False
    out_should_push = False
    out_manual_review_required = True
    out_should_stop = True
    out_stop_reason = normalized_stop_reason or guarded_lane_block_reason
    out_next_action = "manual_review_required"

    status_by_lane = {
        "next_prompt_lane": "lane_contract_guard_valid_next_prompt",
        "fix_prompt_lane": "lane_contract_guard_valid_fix_prompt",
        "rollback_readiness_lane": "lane_contract_guard_valid_rollback_readiness",
        "commit_readiness_lane": "lane_contract_guard_valid_commit_readiness",
    }

    if contract_manual_stop:
        status = "lane_contract_guard_manual_stop"
        guarded_lane = "manual_stop_lane"
        guarded_lane_allowed = False
        guarded_lane_block_reason = (
            normalized_selected_lane_block_reason
            or normalized_stop_reason
            or block_reason
            or "manual_stop_lane_selected"
        )
        if github_lane_trace_detected:
            guarded_lane_block_reason = "github_lane_not_enabled"
        guarded_contract_ready = True
        guarded_contract_kind = "manual_stop_lane"
        guarded_contract_action = "manual_review_required"
        guarded_contract_payload = {
            "lane": "manual_stop_lane",
            "source": guarded_lane_source,
            "stop_reason": (
                "github_lane_not_enabled"
                if github_lane_trace_detected
                else (
                    normalized_stop_reason
                    or normalized_selected_lane_block_reason
                    or "manual_stop_lane_selected"
                )
            ),
            "next_action": "manual_review_required",
        }
        downstream_refresh_allowed = False
        downstream_refresh_kind = "manual_stop_lane"
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = (
            "github_lane_not_enabled"
            if github_lane_trace_detected
            else (
                normalized_stop_reason
                or normalized_selected_lane_block_reason
                or "manual_stop_lane_selected"
            )
        )
        out_next_action = "manual_review_required"
    elif (
        not block_reason
        and normalized_selected_lane in status_by_lane
        and selected_lane_allowed
        and lane_contract_ready
        and contract_schema_valid
        and contract_payload_lane_matches_selection
        and contract_action_allowed
        and not contract_conflict_detected
        and not normalized_conflicting_lanes
        and not manual_review_required
        and not should_stop
        and not should_invoke_codex
        and not should_execute_rollback
        and not should_execute_commit
        and not should_push
    ):
        status = status_by_lane[normalized_selected_lane]
        guarded_lane = normalized_selected_lane
        guarded_lane_allowed = True
        guarded_lane_block_reason = ""
        guarded_contract_ready = True
        guarded_contract_kind = normalized_selected_lane
        guarded_contract_action = payload_next_action
        guarded_contract_payload = dict(payload_mapping or {})
        downstream_refresh_allowed = True
        downstream_refresh_kind = normalized_selected_lane
        out_should_generate_next_prompt = bool(
            normalized_selected_lane == "next_prompt_lane" and should_generate_next_prompt
        )
        out_should_generate_fix_prompt = bool(
            normalized_selected_lane == "fix_prompt_lane" and should_generate_fix_prompt
        )
        out_should_prepare_rollback = bool(
            normalized_selected_lane == "rollback_readiness_lane" and should_prepare_rollback
        )
        out_should_prepare_commit = bool(
            normalized_selected_lane == "commit_readiness_lane" and should_prepare_commit
        )
        out_should_prepare_github_handoff = False
        out_manual_review_required = False
        out_should_stop = False
        out_stop_reason = ""
        out_next_action = f"refresh_{normalized_selected_lane}"
    else:
        if guarded_lane_block_reason == "blocked_github_lane_not_enabled":
            status = "lane_contract_guard_blocked_github_not_enabled"
        elif guarded_lane_block_reason in {
            "blocked_lane_contract_not_ready",
            "blocked_lane_contract_not_dict",
            "blocked_lane_payload_missing_lane",
            "blocked_lane_payload_missing_source",
            "blocked_lane_payload_missing_next_action",
            "blocked_lane_payload_mismatch",
            "blocked_lane_kind_mismatch",
            "blocked_lane_action_mismatch",
            "blocked_lane_action_not_allowed",
        }:
            status = "lane_contract_guard_blocked_malformed_contract"
        elif guarded_lane_block_reason in {
            "blocked_lane_conflict_detected",
            "blocked_conflicting_lanes_present",
        }:
            status = "lane_contract_guard_blocked_conflict"
        else:
            status = "lane_contract_guard_blocked_insufficient_truth"

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if out_next_action not in allowed_next_actions:
        out_next_action = "insufficient_truth"
    if guarded_contract_action not in allowed_next_actions:
        guarded_contract_action = "insufficient_truth"
    if status == "insufficient_truth":
        guarded_lane = "manual_stop_lane"
        guarded_lane_allowed = False
        guarded_lane_block_reason = "blocked_insufficient_lane_contract_truth"
        guarded_contract_ready = False
        guarded_contract_kind = "manual_stop_lane"
        guarded_contract_action = "manual_review_required"
        guarded_contract_payload = {
            "lane": "manual_stop_lane",
            "source": guarded_lane_source,
            "stop_reason": "insufficient_lane_contract_truth",
            "next_action": "manual_review_required",
        }
        downstream_refresh_allowed = False
        downstream_refresh_kind = "manual_stop_lane"
        out_should_generate_next_prompt = False
        out_should_generate_fix_prompt = False
        out_should_prepare_rollback = False
        out_should_prepare_commit = False
        out_should_prepare_github_handoff = False
        out_should_invoke_codex = False
        out_should_execute_rollback = False
        out_should_execute_commit = False
        out_should_push = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_lane_contract_truth"
        out_next_action = "manual_review_required"

    return {
        "project_browser_autonomous_lane_contract_guard_status": status,
        "project_browser_autonomous_lane_contract_guard_guarded_lane": guarded_lane,
        "project_browser_autonomous_lane_contract_guard_guarded_lane_allowed": bool(
            guarded_lane_allowed
        ),
        "project_browser_autonomous_lane_contract_guard_guarded_lane_block_reason": (
            guarded_lane_block_reason
        ),
        "project_browser_autonomous_lane_contract_guard_guarded_lane_source": guarded_lane_source,
        "project_browser_autonomous_lane_contract_guard_guarded_contract_ready": bool(
            guarded_contract_ready
        ),
        "project_browser_autonomous_lane_contract_guard_guarded_contract_kind": (
            guarded_contract_kind
        ),
        "project_browser_autonomous_lane_contract_guard_guarded_contract_action": (
            guarded_contract_action
        ),
        "project_browser_autonomous_lane_contract_guard_guarded_contract_payload": (
            guarded_contract_payload
        ),
        "project_browser_autonomous_lane_contract_guard_contract_schema_valid": bool(
            contract_schema_valid
        ),
        "project_browser_autonomous_lane_contract_guard_contract_payload_lane_matches_selection": bool(
            contract_payload_lane_matches_selection
        ),
        "project_browser_autonomous_lane_contract_guard_contract_action_allowed": bool(
            contract_action_allowed
        ),
        "project_browser_autonomous_lane_contract_guard_contract_manual_stop": bool(
            contract_manual_stop
        ),
        "project_browser_autonomous_lane_contract_guard_contract_conflict_detected": bool(
            contract_conflict_detected
        ),
        "project_browser_autonomous_lane_contract_guard_conflicting_lanes": (
            normalized_conflicting_lanes
        ),
        "project_browser_autonomous_lane_contract_guard_downstream_refresh_allowed": bool(
            downstream_refresh_allowed
        ),
        "project_browser_autonomous_lane_contract_guard_downstream_refresh_kind": (
            downstream_refresh_kind
        ),
        "project_browser_autonomous_lane_contract_guard_should_generate_next_prompt": bool(
            out_should_generate_next_prompt
        ),
        "project_browser_autonomous_lane_contract_guard_should_generate_fix_prompt": bool(
            out_should_generate_fix_prompt
        ),
        "project_browser_autonomous_lane_contract_guard_should_prepare_rollback": bool(
            out_should_prepare_rollback
        ),
        "project_browser_autonomous_lane_contract_guard_should_prepare_commit": bool(
            out_should_prepare_commit
        ),
        "project_browser_autonomous_lane_contract_guard_should_prepare_github_handoff": bool(
            out_should_prepare_github_handoff
        ),
        "project_browser_autonomous_lane_contract_guard_should_invoke_codex": bool(
            out_should_invoke_codex
        ),
        "project_browser_autonomous_lane_contract_guard_should_execute_rollback": bool(
            out_should_execute_rollback
        ),
        "project_browser_autonomous_lane_contract_guard_should_execute_commit": bool(
            out_should_execute_commit
        ),
        "project_browser_autonomous_lane_contract_guard_should_push": bool(out_should_push),
        "project_browser_autonomous_lane_contract_guard_manual_review_required": bool(
            out_manual_review_required
        ),
        "project_browser_autonomous_lane_contract_guard_should_stop": bool(out_should_stop),
        "project_browser_autonomous_lane_contract_guard_stop_reason": out_stop_reason,
        "project_browser_autonomous_lane_contract_guard_next_action": out_next_action,
        "project_browser_autonomous_lane_contract_guard_runtime_posture": runtime_posture,
        "project_browser_autonomous_lane_contract_guard_missing_inputs": _serialize_required_signals(
            [
                normalized_terminal_lane_status,
                normalized_selected_lane,
                normalized_selected_lane_block_reason,
                normalized_selected_lane_source,
                normalized_selected_lane_priority,
                normalized_lane_contract_kind,
                normalized_lane_contract_action,
                normalized_controller_status,
                normalized_controller_next_action,
                normalized_next_action,
                normalized_multi_cycle_controller_status,
                normalized_commit_tag_result_assimilation_status,
                normalized_post_rollback_fix_reentry_result_assimilation_status,
                "contract_not_schema_valid" if not contract_schema_valid else "",
                "contract_payload_lane_mismatch"
                if not contract_payload_lane_matches_selection
                else "",
                "contract_action_not_allowed" if not contract_action_allowed else "",
                "lane_conflict_detected_true" if contract_conflict_detected else "",
                "manual_review_required_true" if manual_review_required else "",
                "should_stop_true" if should_stop else "",
                "should_invoke_codex_true" if should_invoke_codex else "",
                "should_execute_rollback_true" if should_execute_rollback else "",
                "should_execute_commit_true" if should_execute_commit else "",
                "should_push_true" if should_push else "",
            ]
        ),
    }

def _build_project_browser_autonomous_guarded_lane_dispatch_state(
    *,
    lane_contract_guard_status: str,
    guarded_lane: str,
    guarded_lane_allowed: bool,
    guarded_lane_block_reason: str,
    guarded_lane_source: str,
    guarded_contract_ready: bool,
    guarded_contract_kind: str,
    guarded_contract_action: str,
    guarded_contract_payload: Any,
    contract_schema_valid: bool,
    contract_payload_lane_matches_selection: bool,
    contract_action_allowed: bool,
    contract_manual_stop: bool,
    contract_conflict_detected: bool,
    conflicting_lanes: Sequence[Any],
    downstream_refresh_allowed: bool,
    downstream_refresh_kind: str,
    should_generate_next_prompt: bool,
    should_generate_fix_prompt: bool,
    should_prepare_rollback: bool,
    should_prepare_commit: bool,
    should_prepare_github_handoff: bool,
    should_invoke_codex: bool,
    should_execute_rollback: bool,
    should_execute_commit: bool,
    should_push: bool,
    manual_review_required: bool,
    should_stop: bool,
    stop_reason: str,
    next_action: str,
    terminal_lane_status: str,
    multi_cycle_controller_status: str,
) -> dict[str, Any]:
    allowed_statuses = {
        "guarded_lane_dispatch_next_prompt_refresh_ready",
        "guarded_lane_dispatch_fix_prompt_refresh_ready",
        "guarded_lane_dispatch_rollback_readiness_refresh_ready",
        "guarded_lane_dispatch_commit_readiness_refresh_ready",
        "guarded_lane_dispatch_manual_stop",
        "guarded_lane_dispatch_blocked",
        "guarded_lane_dispatch_blocked_refresh_conflict",
        "guarded_lane_dispatch_blocked_github_not_enabled",
        "guarded_lane_dispatch_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "execute_next_prompt_generation",
        "execute_fix_prompt_generation",
        "execute_rollback_readiness_refresh",
        "execute_commit_readiness_refresh",
        "manual_review_required",
        "insufficient_truth",
    }
    runtime_posture = [
        "prompt200_guarded_lane_dispatch",
        "metadata_only",
        "single_lane_refresh_dispatch",
        "no_execution",
        "no_codex_invocation",
        "no_git_mutation",
        "no_rollback_execution",
        "no_push",
    ]
    supported_dispatch_lanes = {
        "next_prompt_lane",
        "fix_prompt_lane",
        "rollback_readiness_lane",
        "commit_readiness_lane",
    }

    normalized_guard_status = _normalize_text(lane_contract_guard_status, default="insufficient_truth")
    normalized_guarded_lane = _normalize_text(guarded_lane, default="")
    normalized_guarded_lane_block_reason = _normalize_text(guarded_lane_block_reason, default="")
    normalized_guarded_lane_source = _normalize_text(guarded_lane_source, default="terminal_lane_decision")
    normalized_guarded_contract_kind = _normalize_text(guarded_contract_kind, default="")
    normalized_guarded_contract_action = _normalize_text(guarded_contract_action, default="")
    normalized_downstream_refresh_kind = _normalize_text(downstream_refresh_kind, default="")
    normalized_stop_reason = _normalize_text(stop_reason, default="")
    normalized_next_action = _normalize_text(next_action, default="")
    normalized_terminal_lane_status = _normalize_text(terminal_lane_status, default="insufficient_truth")
    normalized_multi_cycle_controller_status = _normalize_text(
        multi_cycle_controller_status,
        default="insufficient_truth",
    )
    normalized_conflicting_lanes = _normalize_string_list(conflicting_lanes)
    payload_mapping = dict(guarded_contract_payload) if isinstance(guarded_contract_payload, Mapping) else {}
    payload_lane = _normalize_text(payload_mapping.get("lane"), default="")
    payload_next_action = _normalize_text(payload_mapping.get("next_action"), default="")
    github_lane_detected = bool(
        normalized_guarded_lane == "github_readiness_lane"
        or normalized_guarded_contract_kind == "github_readiness_lane"
        or payload_lane == "github_readiness_lane"
        or payload_next_action == "github_readiness_not_enabled"
    )

    dispatch_allowed = False
    dispatch_applied = False
    dispatch_block_reason = ""
    dispatch_source = normalized_guarded_lane_source or "lane_contract_guard"
    selected_lane = normalized_guarded_lane
    selected_lane_action = normalized_guarded_contract_action
    selected_lane_payload: dict[str, Any] = dict(payload_mapping)
    refreshed_downstream_kind = ""
    refreshed_downstream_source = ""
    next_prompt_refresh_allowed = False
    fix_prompt_refresh_allowed = False
    rollback_readiness_refresh_allowed = False
    commit_readiness_refresh_allowed = False
    manual_stop_refresh_applied = False
    downstream_execution_allowed_next = False
    downstream_execution_kind = ""
    downstream_execution_action = ""
    downstream_execution_payload: dict[str, Any] = {}
    out_should_generate_next_prompt = False
    out_should_generate_fix_prompt = False
    out_should_prepare_rollback = False
    out_should_prepare_commit = False
    out_should_invoke_codex = False
    out_should_execute_rollback = False
    out_should_execute_commit = False
    out_should_push = False
    out_manual_review_required = True
    out_should_stop = True
    out_stop_reason = normalized_stop_reason or "blocked_insufficient_guarded_lane_dispatch_truth"
    out_next_action = "manual_review_required"
    status = "guarded_lane_dispatch_blocked_insufficient_truth"

    if (
        normalized_guarded_lane == "manual_stop_lane"
        or contract_manual_stop
        or manual_review_required
        or should_stop
    ):
        status = "guarded_lane_dispatch_manual_stop"
        dispatch_allowed = False
        dispatch_applied = True
        dispatch_block_reason = (
            normalized_guarded_lane_block_reason
            or normalized_stop_reason
            or "manual_stop_lane_selected"
        )
        selected_lane = "manual_stop_lane"
        selected_lane_action = "manual_review_required"
        selected_lane_payload = {
            "lane": "manual_stop_lane",
            "source": dispatch_source,
            "stop_reason": normalized_stop_reason
            or normalized_guarded_lane_block_reason
            or "manual_stop_lane_selected",
            "next_action": "manual_review_required",
        }
        manual_stop_refresh_applied = True
        downstream_execution_allowed_next = False
        downstream_execution_kind = "manual_stop_lane"
        downstream_execution_action = "manual_review_required"
        downstream_execution_payload = dict(selected_lane_payload)
        out_should_generate_next_prompt = False
        out_should_generate_fix_prompt = False
        out_should_prepare_rollback = False
        out_should_prepare_commit = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = (
            normalized_stop_reason
            or normalized_guarded_lane_block_reason
            or "manual_stop_lane_selected"
        )
        out_next_action = "manual_review_required"
    else:
        if not guarded_lane_allowed:
            dispatch_block_reason = "blocked_guarded_lane_not_allowed"
        elif not guarded_contract_ready:
            dispatch_block_reason = "blocked_guarded_contract_not_ready"
        elif not downstream_refresh_allowed:
            dispatch_block_reason = "blocked_downstream_refresh_not_allowed"
        elif not contract_schema_valid:
            dispatch_block_reason = "blocked_contract_schema_invalid"
        elif not contract_payload_lane_matches_selection:
            dispatch_block_reason = "blocked_lane_payload_mismatch"
        elif not contract_action_allowed:
            dispatch_block_reason = "blocked_lane_action_not_allowed"
        elif contract_conflict_detected:
            dispatch_block_reason = "blocked_lane_conflict_detected"
        elif manual_review_required:
            dispatch_block_reason = "blocked_manual_review_required"
        elif should_stop:
            dispatch_block_reason = "blocked_should_stop"
        elif should_invoke_codex:
            dispatch_block_reason = "blocked_unexpected_codex_invocation_flag"
        elif should_execute_rollback:
            dispatch_block_reason = "blocked_unexpected_rollback_execution_flag"
        elif should_execute_commit:
            dispatch_block_reason = "blocked_unexpected_commit_execution_flag"
        elif should_push:
            dispatch_block_reason = "blocked_unexpected_push_flag"
        elif github_lane_detected:
            dispatch_block_reason = "github_lane_not_enabled"
        elif normalized_guarded_lane not in supported_dispatch_lanes:
            dispatch_block_reason = "blocked_unknown_guarded_lane"
        elif not normalized_guarded_lane:
            dispatch_block_reason = "blocked_insufficient_guarded_lane_dispatch_truth"

        if dispatch_block_reason:
            status = (
                "guarded_lane_dispatch_blocked_github_not_enabled"
                if dispatch_block_reason == "github_lane_not_enabled"
                else "guarded_lane_dispatch_blocked"
            )
            dispatch_allowed = False
            dispatch_applied = False
            out_should_generate_next_prompt = False
            out_should_generate_fix_prompt = False
            out_should_prepare_rollback = False
            out_should_prepare_commit = False
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = normalized_stop_reason or dispatch_block_reason
            out_next_action = "manual_review_required"
            downstream_execution_allowed_next = False
            downstream_execution_kind = ""
            downstream_execution_action = ""
            downstream_execution_payload = {}
        else:
            dispatch_allowed = True
            dispatch_applied = True
            dispatch_block_reason = ""
            refreshed_downstream_source = "prompt200_guarded_lane_dispatch"
            selected_lane = normalized_guarded_lane
            selected_lane_action = normalized_guarded_contract_action
            selected_lane_payload = dict(payload_mapping)
            downstream_execution_allowed_next = True
            downstream_execution_payload = dict(payload_mapping)
            out_should_invoke_codex = False
            out_should_execute_rollback = False
            out_should_execute_commit = False
            out_should_push = False
            out_manual_review_required = False
            out_should_stop = False
            out_stop_reason = ""

            if normalized_guarded_lane == "next_prompt_lane":
                status = "guarded_lane_dispatch_next_prompt_refresh_ready"
                next_prompt_refresh_allowed = True
                refreshed_downstream_kind = "next_prompt_generation"
                downstream_execution_kind = "next_prompt_generation"
                downstream_execution_action = "execute_next_prompt_generation"
                out_should_generate_next_prompt = True
                out_should_generate_fix_prompt = False
                out_should_prepare_rollback = False
                out_should_prepare_commit = False
                out_next_action = "execute_next_prompt_generation"
            elif normalized_guarded_lane == "fix_prompt_lane":
                status = "guarded_lane_dispatch_fix_prompt_refresh_ready"
                fix_prompt_refresh_allowed = True
                refreshed_downstream_kind = "fix_prompt_generation"
                downstream_execution_kind = "fix_prompt_generation"
                downstream_execution_action = "execute_fix_prompt_generation"
                out_should_generate_next_prompt = False
                out_should_generate_fix_prompt = True
                out_should_prepare_rollback = False
                out_should_prepare_commit = False
                out_next_action = "execute_fix_prompt_generation"
            elif normalized_guarded_lane == "rollback_readiness_lane":
                status = "guarded_lane_dispatch_rollback_readiness_refresh_ready"
                rollback_readiness_refresh_allowed = True
                refreshed_downstream_kind = "rollback_readiness"
                downstream_execution_kind = "rollback_readiness"
                downstream_execution_action = "execute_rollback_readiness_refresh"
                out_should_generate_next_prompt = False
                out_should_generate_fix_prompt = False
                out_should_prepare_rollback = True
                out_should_prepare_commit = False
                out_next_action = "execute_rollback_readiness_refresh"
            elif normalized_guarded_lane == "commit_readiness_lane":
                status = "guarded_lane_dispatch_commit_readiness_refresh_ready"
                commit_readiness_refresh_allowed = True
                refreshed_downstream_kind = "commit_tag_readiness"
                downstream_execution_kind = "commit_tag_readiness"
                downstream_execution_action = "execute_commit_readiness_refresh"
                out_should_generate_next_prompt = False
                out_should_generate_fix_prompt = False
                out_should_prepare_rollback = False
                out_should_prepare_commit = True
                out_next_action = "execute_commit_readiness_refresh"

    refresh_flags = [
        next_prompt_refresh_allowed,
        fix_prompt_refresh_allowed,
        rollback_readiness_refresh_allowed,
        commit_readiness_refresh_allowed,
        manual_stop_refresh_applied,
    ]
    if sum(1 for flag in refresh_flags if flag) > 1:
        status = "guarded_lane_dispatch_blocked_refresh_conflict"
        dispatch_allowed = False
        dispatch_applied = False
        dispatch_block_reason = "blocked_multiple_downstream_refreshes"
        next_prompt_refresh_allowed = False
        fix_prompt_refresh_allowed = False
        rollback_readiness_refresh_allowed = False
        commit_readiness_refresh_allowed = False
        manual_stop_refresh_applied = False
        downstream_execution_allowed_next = False
        downstream_execution_kind = ""
        downstream_execution_action = ""
        downstream_execution_payload = {}
        out_should_generate_next_prompt = False
        out_should_generate_fix_prompt = False
        out_should_prepare_rollback = False
        out_should_prepare_commit = False
        out_should_invoke_codex = False
        out_should_execute_rollback = False
        out_should_execute_commit = False
        out_should_push = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "multiple_downstream_refreshes_selected"
        out_next_action = "manual_review_required"

    if not dispatch_block_reason and not dispatch_allowed and not dispatch_applied and status in {
        "guarded_lane_dispatch_blocked",
        "guarded_lane_dispatch_blocked_insufficient_truth",
    }:
        dispatch_block_reason = "blocked_insufficient_guarded_lane_dispatch_truth"

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if out_next_action not in allowed_next_actions:
        out_next_action = "insufficient_truth"
    if status == "insufficient_truth":
        dispatch_allowed = False
        dispatch_applied = False
        dispatch_block_reason = "blocked_insufficient_guarded_lane_dispatch_truth"
        selected_lane = "manual_stop_lane"
        selected_lane_action = "manual_review_required"
        selected_lane_payload = {}
        refreshed_downstream_kind = ""
        refreshed_downstream_source = ""
        next_prompt_refresh_allowed = False
        fix_prompt_refresh_allowed = False
        rollback_readiness_refresh_allowed = False
        commit_readiness_refresh_allowed = False
        manual_stop_refresh_applied = False
        downstream_execution_allowed_next = False
        downstream_execution_kind = ""
        downstream_execution_action = ""
        downstream_execution_payload = {}
        out_should_generate_next_prompt = False
        out_should_generate_fix_prompt = False
        out_should_prepare_rollback = False
        out_should_prepare_commit = False
        out_should_invoke_codex = False
        out_should_execute_rollback = False
        out_should_execute_commit = False
        out_should_push = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "blocked_insufficient_guarded_lane_dispatch_truth"
        out_next_action = "manual_review_required"

    return {
        "project_browser_autonomous_guarded_lane_dispatch_status": status,
        "project_browser_autonomous_guarded_lane_dispatch_dispatch_allowed": bool(dispatch_allowed),
        "project_browser_autonomous_guarded_lane_dispatch_dispatch_applied": bool(dispatch_applied),
        "project_browser_autonomous_guarded_lane_dispatch_dispatch_block_reason": dispatch_block_reason,
        "project_browser_autonomous_guarded_lane_dispatch_dispatch_source": dispatch_source,
        "project_browser_autonomous_guarded_lane_dispatch_selected_lane": selected_lane,
        "project_browser_autonomous_guarded_lane_dispatch_selected_lane_action": selected_lane_action,
        "project_browser_autonomous_guarded_lane_dispatch_selected_lane_payload": selected_lane_payload,
        "project_browser_autonomous_guarded_lane_dispatch_refreshed_downstream_kind": (
            refreshed_downstream_kind
        ),
        "project_browser_autonomous_guarded_lane_dispatch_refreshed_downstream_source": (
            refreshed_downstream_source
        ),
        "project_browser_autonomous_guarded_lane_dispatch_next_prompt_refresh_allowed": bool(
            next_prompt_refresh_allowed
        ),
        "project_browser_autonomous_guarded_lane_dispatch_fix_prompt_refresh_allowed": bool(
            fix_prompt_refresh_allowed
        ),
        "project_browser_autonomous_guarded_lane_dispatch_rollback_readiness_refresh_allowed": bool(
            rollback_readiness_refresh_allowed
        ),
        "project_browser_autonomous_guarded_lane_dispatch_commit_readiness_refresh_allowed": bool(
            commit_readiness_refresh_allowed
        ),
        "project_browser_autonomous_guarded_lane_dispatch_manual_stop_refresh_applied": bool(
            manual_stop_refresh_applied
        ),
        "project_browser_autonomous_guarded_lane_dispatch_downstream_execution_allowed_next": bool(
            downstream_execution_allowed_next
        ),
        "project_browser_autonomous_guarded_lane_dispatch_downstream_execution_kind": (
            downstream_execution_kind
        ),
        "project_browser_autonomous_guarded_lane_dispatch_downstream_execution_action": (
            downstream_execution_action
        ),
        "project_browser_autonomous_guarded_lane_dispatch_downstream_execution_payload": (
            downstream_execution_payload
        ),
        "project_browser_autonomous_guarded_lane_dispatch_should_generate_next_prompt": bool(
            out_should_generate_next_prompt
        ),
        "project_browser_autonomous_guarded_lane_dispatch_should_generate_fix_prompt": bool(
            out_should_generate_fix_prompt
        ),
        "project_browser_autonomous_guarded_lane_dispatch_should_prepare_rollback": bool(
            out_should_prepare_rollback
        ),
        "project_browser_autonomous_guarded_lane_dispatch_should_prepare_commit": bool(
            out_should_prepare_commit
        ),
        "project_browser_autonomous_guarded_lane_dispatch_should_invoke_codex": bool(
            out_should_invoke_codex
        ),
        "project_browser_autonomous_guarded_lane_dispatch_should_execute_rollback": bool(
            out_should_execute_rollback
        ),
        "project_browser_autonomous_guarded_lane_dispatch_should_execute_commit": bool(
            out_should_execute_commit
        ),
        "project_browser_autonomous_guarded_lane_dispatch_should_push": bool(out_should_push),
        "project_browser_autonomous_guarded_lane_dispatch_manual_review_required": bool(
            out_manual_review_required
        ),
        "project_browser_autonomous_guarded_lane_dispatch_should_stop": bool(out_should_stop),
        "project_browser_autonomous_guarded_lane_dispatch_stop_reason": out_stop_reason,
        "project_browser_autonomous_guarded_lane_dispatch_next_action": out_next_action,
        "project_browser_autonomous_guarded_lane_dispatch_runtime_posture": runtime_posture,
        "project_browser_autonomous_guarded_lane_dispatch_missing_inputs": _serialize_required_signals(
            [
                normalized_guard_status,
                normalized_guarded_lane,
                normalized_guarded_lane_block_reason,
                normalized_guarded_lane_source,
                normalized_guarded_contract_kind,
                normalized_guarded_contract_action,
                normalized_downstream_refresh_kind,
                normalized_stop_reason,
                normalized_next_action,
                normalized_terminal_lane_status,
                normalized_multi_cycle_controller_status,
                "contract_schema_invalid" if not contract_schema_valid else "",
                "contract_payload_lane_mismatch"
                if not contract_payload_lane_matches_selection
                else "",
                "contract_action_not_allowed" if not contract_action_allowed else "",
                "contract_conflict_detected_true" if contract_conflict_detected else "",
                "guarded_lane_allowed_false" if not guarded_lane_allowed else "",
                "guarded_contract_ready_false" if not guarded_contract_ready else "",
                "downstream_refresh_not_allowed" if not downstream_refresh_allowed else "",
                "manual_review_required_true" if manual_review_required else "",
                "should_stop_true" if should_stop else "",
                "should_invoke_codex_true" if should_invoke_codex else "",
                "should_execute_rollback_true" if should_execute_rollback else "",
                "should_execute_commit_true" if should_execute_commit else "",
                "should_push_true" if should_push else "",
                "conflicting_lanes_present" if normalized_conflicting_lanes else "",
            ]
        ),
    }

def _build_project_browser_autonomous_bounded_local_control_decision_state(
    *,
    next_step_launch_result_assimilation_status: str,
    result_selected: bool,
    result_available: bool,
    result_class: str,
    result_block_reason: str,
    source_selected_launch_kind: str,
    source_selected_launch_action: str,
    source_execution_status: str,
    source_execution_completed: bool,
    source_execution_failed: bool,
    non_selected_launches_noop_confirmed: bool,
    delegated_existing_path_kind: str,
    delegated_existing_status: str,
    generated_prompt_reentry_result_status: str,
    rollback_execution_result_status: str,
    commit_execution_result_status: str,
    controller_feedback_ready: bool,
    controller_feedback_kind: str,
    controller_feedback_source: str,
    controller_feedback_payload: Any,
    next_controller_input_ready: bool,
    next_controller_input_kind: str,
    next_controller_input_source: str,
    next_controller_action_hint: str,
    should_continue_local_loop: bool,
    should_prepare_reentry_result_assimilation: bool,
    should_prepare_rollback_result_assimilation: bool,
    should_prepare_commit_result_assimilation: bool,
    should_prepare_next_controller_decision: bool,
    should_invoke_codex: bool,
    should_execute_rollback: bool,
    should_execute_commit: bool,
    should_push: bool,
    manual_review_required: bool,
    should_stop: bool,
    stop_reason: str,
    next_action: str,
    next_step_launch_execution_status: str,
    next_step_launch_contract_status: str,
    bounded_local_loop_contract_status: str,
    multi_cycle_controller_status: str,
    reentry_result_assimilation_status: str,
    rollback_result_assimilation_status: str,
    commit_tag_result_assimilation_status: str,
) -> dict[str, Any]:
    allowed_statuses = {
        "bounded_local_control_decision_reentry_result_assimilation_ready",
        "bounded_local_control_decision_rollback_result_assimilation_ready",
        "bounded_local_control_decision_commit_result_assimilation_ready",
        "bounded_local_control_decision_manual_stop",
        "bounded_local_control_decision_blocked",
        "bounded_local_control_decision_blocked_conflict",
        "bounded_local_control_decision_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "dispatch_reentry_result_assimilation",
        "dispatch_rollback_result_assimilation",
        "dispatch_commit_result_assimilation",
        "manual_review_required",
        "insufficient_truth",
    }
    runtime_posture = [
        "prompt207_bounded_local_control_decision",
        "metadata_only",
        "exactly_one_control_contract",
        "no_dispatch_execution",
        "no_codex_invocation",
        "no_rollback_execution",
        "no_commit_execution",
        "no_push",
    ]

    normalized_result_assimilation_status = _normalize_text(
        next_step_launch_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_result_class = _normalize_text(result_class, default="insufficient_truth")
    normalized_result_block_reason = _normalize_text(result_block_reason, default="")
    normalized_source_selected_launch_kind = _normalize_text(
        source_selected_launch_kind,
        default="",
    )
    normalized_source_selected_launch_action = _normalize_text(
        source_selected_launch_action,
        default="",
    )
    normalized_source_execution_status = _normalize_text(
        source_execution_status,
        default="insufficient_truth",
    )
    normalized_delegated_existing_path_kind = _normalize_text(
        delegated_existing_path_kind,
        default="none",
    )
    normalized_delegated_existing_status = _normalize_text(
        delegated_existing_status,
        default="insufficient_truth",
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
    normalized_controller_feedback_kind = _normalize_text(controller_feedback_kind, default="none")
    normalized_next_controller_input_kind = _normalize_text(
        next_controller_input_kind,
        default="none",
    )
    normalized_next_controller_input_source = _normalize_text(
        next_controller_input_source,
        default="",
    )
    normalized_next_controller_action_hint = _normalize_text(
        next_controller_action_hint,
        default="manual_review_required",
    )
    normalized_stop_reason = _normalize_text(stop_reason, default="")
    normalized_next_action = _normalize_text(next_action, default="manual_review_required")
    normalized_next_step_launch_execution_status = _normalize_text(
        next_step_launch_execution_status,
        default="insufficient_truth",
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
    _normalized_controller_feedback_payload = (
        dict(controller_feedback_payload)
        if isinstance(controller_feedback_payload, Mapping)
        else {}
    )

    authoritative_selected = bool(
        bool(normalized_result_assimilation_status)
        and bool(normalized_result_class)
        and bool(normalized_source_selected_launch_kind)
        and (
            bool(result_selected)
            or normalized_result_assimilation_status
            in {
                "next_step_launch_result_manual_stop",
                "next_step_launch_result_failed",
                "next_step_launch_result_blocked",
                "next_step_launch_result_blocked_non_selected_launch_activity",
                "next_step_launch_result_blocked_insufficient_truth",
            }
        )
    )

    reentry_terminal_statuses = {
        "reentry_invocation_completed_with_changes",
        "reentry_invocation_completed_no_changes",
        "reentry_invocation_completed_failure",
        "reentry_invocation_completed_timeout",
        "reentry_assimilation_completed_with_changes",
        "reentry_assimilation_completed_no_changes",
        "reentry_assimilation_completed_failure",
        "reentry_assimilation_completed_timeout",
    }
    rollback_terminal_statuses = {
        "rollback_execution_completed",
        "rollback_execution_partial_failure",
        "rollback_execution_failed",
        "rollback_execution_timeout",
        "rollback_result_assimilation_completed_clean",
        "rollback_result_assimilation_completed_expected_dirty",
        "rollback_result_assimilation_partial_failure",
        "rollback_result_assimilation_failed",
        "rollback_result_assimilation_timeout",
        "rollback_result_assimilation_unexpected_dirty",
        "rollback_result_assimilation_not_required",
    }
    commit_terminal_statuses = {
        "commit_tag_execution_completed",
        "commit_tag_execution_failed_git_add",
        "commit_tag_execution_failed_git_commit",
        "commit_tag_execution_failed_git_tag",
        "commit_tag_execution_partial_commit_tag_failed",
        "commit_tag_execution_timeout",
        "commit_tag_result_assimilation_completed",
        "commit_tag_result_assimilation_partial_commit_tag_failed",
        "commit_tag_result_assimilation_failed_git_add",
        "commit_tag_result_assimilation_failed_git_commit",
        "commit_tag_result_assimilation_failed_git_tag",
        "commit_tag_result_assimilation_timeout",
        "commit_tag_result_assimilation_blocked",
    }
    delegated_status_terminal = bool(
        (
            normalized_delegated_existing_path_kind == "generated_prompt_reentry"
            and normalized_delegated_existing_status in reentry_terminal_statuses
        )
        or (
            normalized_delegated_existing_path_kind == "rollback_execution"
            and normalized_delegated_existing_status in rollback_terminal_statuses
        )
        or (
            normalized_delegated_existing_path_kind == "commit_execution"
            and normalized_delegated_existing_status in commit_terminal_statuses
        )
        or normalized_delegated_existing_path_kind == "none"
    )

    reentry_candidate_base = bool(
        normalized_result_class == "generated_prompt_reentry_completed"
        and normalized_next_controller_input_kind == "reentry_result_assimilation_ready"
        and bool(should_prepare_reentry_result_assimilation)
        and normalized_delegated_existing_path_kind == "generated_prompt_reentry"
        and bool(normalized_delegated_existing_status)
        and bool(non_selected_launches_noop_confirmed)
        and not bool(manual_review_required)
        and not bool(should_stop)
    )
    rollback_candidate_base = bool(
        normalized_result_class == "rollback_execution_completed"
        and normalized_next_controller_input_kind == "rollback_result_assimilation_ready"
        and bool(should_prepare_rollback_result_assimilation)
        and normalized_delegated_existing_path_kind == "rollback_execution"
        and bool(normalized_delegated_existing_status)
        and bool(non_selected_launches_noop_confirmed)
        and not bool(manual_review_required)
        and not bool(should_stop)
    )
    commit_candidate_base = bool(
        normalized_result_class == "commit_execution_completed"
        and normalized_next_controller_input_kind == "commit_result_assimilation_ready"
        and bool(should_prepare_commit_result_assimilation)
        and normalized_delegated_existing_path_kind == "commit_execution"
        and bool(normalized_delegated_existing_status)
        and bool(non_selected_launches_noop_confirmed)
        and not bool(manual_review_required)
        and not bool(should_stop)
    )

    delegated_terminal_required = bool(
        reentry_candidate_base or rollback_candidate_base or commit_candidate_base
    )
    delegated_status_not_terminal = bool(
        delegated_terminal_required and not delegated_status_terminal
    )

    reentry_result_assimilation_candidate = bool(
        reentry_candidate_base and delegated_status_terminal
    )
    rollback_result_assimilation_candidate = bool(
        rollback_candidate_base and delegated_status_terminal
    )
    commit_result_assimilation_candidate = bool(
        commit_candidate_base and delegated_status_terminal
    )
    manual_stop_candidate = bool(
        normalized_result_class == "manual_stop"
        or bool(manual_review_required)
        or bool(should_stop)
        or normalized_result_assimilation_status == "next_step_launch_result_manual_stop"
    )
    blocked_candidate = bool(
        normalized_result_class
        in {
            "failed",
            "blocked",
            "insufficient_truth",
            "blocked_non_selected_launch_activity",
        }
        or normalized_result_assimilation_status
        in {
            "next_step_launch_result_failed",
            "next_step_launch_result_blocked",
            "next_step_launch_result_blocked_non_selected_launch_activity",
            "next_step_launch_result_blocked_insufficient_truth",
        }
    )

    non_stop_candidates: list[str] = []
    if reentry_result_assimilation_candidate:
        non_stop_candidates.append("reentry_result_assimilation")
    if rollback_result_assimilation_candidate:
        non_stop_candidates.append("rollback_result_assimilation")
    if commit_result_assimilation_candidate:
        non_stop_candidates.append("commit_result_assimilation")
    non_stop_candidates = sorted(non_stop_candidates)

    status = "bounded_local_control_decision_blocked_insufficient_truth"
    control_contract_available = False
    control_contract_allowed = False
    control_contract_block_reason = "blocked_insufficient_bounded_local_control_decision_truth"
    control_contract_source = "prompt206_next_step_launch_result_assimilation"
    control_contract_kind = "blocked"
    control_contract_action = "manual_review_required"
    control_contract_payload: dict[str, Any] = {}
    exactly_one_control_contract = False
    control_conflict_detected = False
    conflicting_control_contracts: list[str] = []
    continue_to_reentry_result_assimilation = False
    continue_to_rollback_result_assimilation = False
    continue_to_commit_result_assimilation = False
    manual_stop_contract = False
    blocked_contract = False
    selected_next_control_kind = "blocked"
    selected_next_control_action = "manual_review_required"
    selected_next_control_payload: dict[str, Any] = {}
    next_control_ready_for_dispatch = False
    result_feedback_kind = normalized_controller_feedback_kind
    result_feedback_status = normalized_result_assimilation_status
    out_should_continue_local_loop = False
    out_should_prepare_reentry_result_assimilation = False
    out_should_prepare_rollback_result_assimilation = False
    out_should_prepare_commit_result_assimilation = False
    out_should_prepare_next_controller_decision = False
    out_should_invoke_codex = False
    out_should_execute_rollback = False
    out_should_execute_commit = False
    out_should_push = False
    out_manual_review_required = True
    out_should_stop = True
    out_stop_reason = normalized_stop_reason or "insufficient_bounded_local_control_decision_truth"
    out_next_action = "manual_review_required"

    if not authoritative_selected:
        status = "bounded_local_control_decision_blocked_insufficient_truth"
        control_contract_available = False
        control_contract_allowed = False
        control_contract_block_reason = "blocked_insufficient_bounded_local_control_decision_truth"
        blocked_contract = True
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_bounded_local_control_decision_truth"
        out_next_action = "manual_review_required"
    elif len(non_stop_candidates) > 1:
        status = "bounded_local_control_decision_blocked_conflict"
        control_contract_available = True
        control_contract_allowed = False
        control_contract_block_reason = "conflicting_bounded_local_control_candidates"
        exactly_one_control_contract = False
        control_conflict_detected = True
        conflicting_control_contracts = list(non_stop_candidates)
        blocked_contract = True
        selected_next_control_kind = "blocked"
        selected_next_control_action = "manual_review_required"
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "conflicting_bounded_local_control_candidates"
        out_next_action = "manual_review_required"
    elif manual_stop_candidate:
        status = "bounded_local_control_decision_manual_stop"
        control_contract_available = True
        control_contract_allowed = False
        control_contract_block_reason = ""
        control_contract_kind = "manual_stop"
        control_contract_action = "manual_review_required"
        control_contract_payload = {
            "control_kind": "manual_stop",
            "source": "prompt206_next_step_launch_result_assimilation",
            "stop_reason": normalized_stop_reason or "manual_stop",
            "next_action": "manual_review_required",
        }
        exactly_one_control_contract = True
        manual_stop_contract = True
        selected_next_control_kind = "manual_stop"
        selected_next_control_action = "manual_review_required"
        selected_next_control_payload = dict(control_contract_payload)
        next_control_ready_for_dispatch = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = normalized_stop_reason or "manual_stop"
        out_next_action = "manual_review_required"
    elif blocked_candidate or delegated_status_not_terminal:
        status = "bounded_local_control_decision_blocked"
        control_contract_available = True
        control_contract_allowed = False
        control_contract_block_reason = (
            "blocked_delegated_status_not_terminal"
            if delegated_status_not_terminal
            else (normalized_result_block_reason or "next_step_launch_result_not_safe")
        )
        control_contract_kind = "blocked"
        control_contract_action = "manual_review_required"
        control_contract_payload = {
            "control_kind": "blocked",
            "source": "prompt206_next_step_launch_result_assimilation",
            "stop_reason": (
                "blocked_delegated_status_not_terminal"
                if delegated_status_not_terminal
                else (
                    normalized_stop_reason
                    or normalized_result_block_reason
                    or "next_step_launch_result_not_safe"
                )
            ),
            "next_action": "manual_review_required",
        }
        exactly_one_control_contract = True
        blocked_contract = True
        selected_next_control_kind = "blocked"
        selected_next_control_action = "manual_review_required"
        selected_next_control_payload = dict(control_contract_payload)
        next_control_ready_for_dispatch = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = (
            "blocked_delegated_status_not_terminal"
            if delegated_status_not_terminal
            else (
                normalized_stop_reason
                or normalized_result_block_reason
                or "next_step_launch_result_not_safe"
            )
        )
        out_next_action = "manual_review_required"
    elif reentry_result_assimilation_candidate:
        status = "bounded_local_control_decision_reentry_result_assimilation_ready"
        control_contract_available = True
        control_contract_allowed = True
        control_contract_block_reason = ""
        control_contract_kind = "reentry_result_assimilation"
        control_contract_action = "dispatch_reentry_result_assimilation"
        control_contract_payload = {
            "control_kind": "reentry_result_assimilation",
            "source": "prompt206_next_step_launch_result_assimilation",
            "delegated_existing_status": normalized_delegated_existing_status,
            "next_action": "dispatch_reentry_result_assimilation",
        }
        exactly_one_control_contract = True
        continue_to_reentry_result_assimilation = True
        selected_next_control_kind = "reentry_result_assimilation"
        selected_next_control_action = "dispatch_reentry_result_assimilation"
        selected_next_control_payload = dict(control_contract_payload)
        next_control_ready_for_dispatch = True
        out_should_prepare_reentry_result_assimilation = True
        out_should_prepare_next_controller_decision = False
        out_manual_review_required = False
        out_should_stop = False
        out_stop_reason = ""
        out_next_action = "dispatch_reentry_result_assimilation"
    elif rollback_result_assimilation_candidate:
        status = "bounded_local_control_decision_rollback_result_assimilation_ready"
        control_contract_available = True
        control_contract_allowed = True
        control_contract_block_reason = ""
        control_contract_kind = "rollback_result_assimilation"
        control_contract_action = "dispatch_rollback_result_assimilation"
        control_contract_payload = {
            "control_kind": "rollback_result_assimilation",
            "source": "prompt206_next_step_launch_result_assimilation",
            "delegated_existing_status": normalized_delegated_existing_status,
            "next_action": "dispatch_rollback_result_assimilation",
        }
        exactly_one_control_contract = True
        continue_to_rollback_result_assimilation = True
        selected_next_control_kind = "rollback_result_assimilation"
        selected_next_control_action = "dispatch_rollback_result_assimilation"
        selected_next_control_payload = dict(control_contract_payload)
        next_control_ready_for_dispatch = True
        out_should_prepare_rollback_result_assimilation = True
        out_should_prepare_next_controller_decision = False
        out_manual_review_required = False
        out_should_stop = False
        out_stop_reason = ""
        out_next_action = "dispatch_rollback_result_assimilation"
    elif commit_result_assimilation_candidate:
        status = "bounded_local_control_decision_commit_result_assimilation_ready"
        control_contract_available = True
        control_contract_allowed = True
        control_contract_block_reason = ""
        control_contract_kind = "commit_result_assimilation"
        control_contract_action = "dispatch_commit_result_assimilation"
        control_contract_payload = {
            "control_kind": "commit_result_assimilation",
            "source": "prompt206_next_step_launch_result_assimilation",
            "delegated_existing_status": normalized_delegated_existing_status,
            "next_action": "dispatch_commit_result_assimilation",
        }
        exactly_one_control_contract = True
        continue_to_commit_result_assimilation = True
        selected_next_control_kind = "commit_result_assimilation"
        selected_next_control_action = "dispatch_commit_result_assimilation"
        selected_next_control_payload = dict(control_contract_payload)
        next_control_ready_for_dispatch = True
        out_should_prepare_commit_result_assimilation = True
        out_should_prepare_next_controller_decision = False
        out_manual_review_required = False
        out_should_stop = False
        out_stop_reason = ""
        out_next_action = "dispatch_commit_result_assimilation"
    else:
        status = "bounded_local_control_decision_blocked_insufficient_truth"
        control_contract_available = False
        control_contract_allowed = False
        control_contract_block_reason = "insufficient_bounded_local_control_decision_truth"
        blocked_contract = True
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_bounded_local_control_decision_truth"
        out_next_action = "manual_review_required"

    if not selected_next_control_payload:
        selected_next_control_payload = (
            dict(control_contract_payload)
            if isinstance(control_contract_payload, Mapping)
            else {}
        )
    if not control_contract_payload:
        control_contract_payload = (
            dict(selected_next_control_payload)
            if isinstance(selected_next_control_payload, Mapping)
            else {}
        )

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if out_next_action not in allowed_next_actions:
        out_next_action = "insufficient_truth"
    if control_contract_action not in allowed_next_actions:
        control_contract_action = "manual_review_required"
    if selected_next_control_action not in allowed_next_actions:
        selected_next_control_action = "manual_review_required"
    if status == "insufficient_truth":
        status = "bounded_local_control_decision_blocked_insufficient_truth"
        control_contract_available = False
        control_contract_allowed = False
        control_contract_block_reason = "insufficient_bounded_local_control_decision_truth"
        control_contract_source = "prompt206_next_step_launch_result_assimilation"
        control_contract_kind = "blocked"
        control_contract_action = "manual_review_required"
        control_contract_payload = {
            "control_kind": "blocked",
            "source": "prompt206_next_step_launch_result_assimilation",
            "stop_reason": "insufficient_bounded_local_control_decision_truth",
            "next_action": "manual_review_required",
        }
        exactly_one_control_contract = False
        control_conflict_detected = False
        conflicting_control_contracts = []
        continue_to_reentry_result_assimilation = False
        continue_to_rollback_result_assimilation = False
        continue_to_commit_result_assimilation = False
        manual_stop_contract = False
        blocked_contract = True
        selected_next_control_kind = "blocked"
        selected_next_control_action = "manual_review_required"
        selected_next_control_payload = dict(control_contract_payload)
        next_control_ready_for_dispatch = False
        out_should_continue_local_loop = False
        out_should_prepare_reentry_result_assimilation = False
        out_should_prepare_rollback_result_assimilation = False
        out_should_prepare_commit_result_assimilation = False
        out_should_prepare_next_controller_decision = False
        out_should_invoke_codex = False
        out_should_execute_rollback = False
        out_should_execute_commit = False
        out_should_push = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_bounded_local_control_decision_truth"
        out_next_action = "manual_review_required"

    return {
        "project_browser_autonomous_bounded_local_control_decision_status": status,
        "project_browser_autonomous_bounded_local_control_decision_control_contract_available": bool(
            control_contract_available
        ),
        "project_browser_autonomous_bounded_local_control_decision_control_contract_allowed": bool(
            control_contract_allowed
        ),
        "project_browser_autonomous_bounded_local_control_decision_control_contract_block_reason": (
            control_contract_block_reason
        ),
        "project_browser_autonomous_bounded_local_control_decision_control_contract_source": (
            control_contract_source
        ),
        "project_browser_autonomous_bounded_local_control_decision_control_contract_kind": (
            control_contract_kind
        ),
        "project_browser_autonomous_bounded_local_control_decision_control_contract_action": (
            control_contract_action
        ),
        "project_browser_autonomous_bounded_local_control_decision_control_contract_payload": (
            control_contract_payload if isinstance(control_contract_payload, Mapping) else {}
        ),
        "project_browser_autonomous_bounded_local_control_decision_exactly_one_control_contract": bool(
            exactly_one_control_contract
        ),
        "project_browser_autonomous_bounded_local_control_decision_control_conflict_detected": bool(
            control_conflict_detected
        ),
        "project_browser_autonomous_bounded_local_control_decision_conflicting_control_contracts": (
            conflicting_control_contracts
        ),
        "project_browser_autonomous_bounded_local_control_decision_continue_to_reentry_result_assimilation": bool(
            continue_to_reentry_result_assimilation
        ),
        "project_browser_autonomous_bounded_local_control_decision_continue_to_rollback_result_assimilation": bool(
            continue_to_rollback_result_assimilation
        ),
        "project_browser_autonomous_bounded_local_control_decision_continue_to_commit_result_assimilation": bool(
            continue_to_commit_result_assimilation
        ),
        "project_browser_autonomous_bounded_local_control_decision_manual_stop_contract": bool(
            manual_stop_contract
        ),
        "project_browser_autonomous_bounded_local_control_decision_blocked_contract": bool(
            blocked_contract
        ),
        "project_browser_autonomous_bounded_local_control_decision_selected_next_control_kind": (
            selected_next_control_kind
        ),
        "project_browser_autonomous_bounded_local_control_decision_selected_next_control_action": (
            selected_next_control_action
        ),
        "project_browser_autonomous_bounded_local_control_decision_selected_next_control_payload": (
            selected_next_control_payload if isinstance(selected_next_control_payload, Mapping) else {}
        ),
        "project_browser_autonomous_bounded_local_control_decision_next_control_ready_for_dispatch": bool(
            next_control_ready_for_dispatch
        ),
        "project_browser_autonomous_bounded_local_control_decision_result_feedback_kind": (
            result_feedback_kind
        ),
        "project_browser_autonomous_bounded_local_control_decision_result_feedback_status": (
            result_feedback_status
        ),
        "project_browser_autonomous_bounded_local_control_decision_delegated_existing_path_kind": (
            normalized_delegated_existing_path_kind
        ),
        "project_browser_autonomous_bounded_local_control_decision_delegated_existing_status": (
            normalized_delegated_existing_status
        ),
        "project_browser_autonomous_bounded_local_control_decision_non_selected_launches_noop_confirmed": bool(
            non_selected_launches_noop_confirmed
        ),
        "project_browser_autonomous_bounded_local_control_decision_should_continue_local_loop": bool(
            out_should_continue_local_loop
        ),
        "project_browser_autonomous_bounded_local_control_decision_should_prepare_reentry_result_assimilation": bool(
            out_should_prepare_reentry_result_assimilation
        ),
        "project_browser_autonomous_bounded_local_control_decision_should_prepare_rollback_result_assimilation": bool(
            out_should_prepare_rollback_result_assimilation
        ),
        "project_browser_autonomous_bounded_local_control_decision_should_prepare_commit_result_assimilation": bool(
            out_should_prepare_commit_result_assimilation
        ),
        "project_browser_autonomous_bounded_local_control_decision_should_prepare_next_controller_decision": bool(
            out_should_prepare_next_controller_decision
        ),
        "project_browser_autonomous_bounded_local_control_decision_should_invoke_codex": bool(
            out_should_invoke_codex
        ),
        "project_browser_autonomous_bounded_local_control_decision_should_execute_rollback": bool(
            out_should_execute_rollback
        ),
        "project_browser_autonomous_bounded_local_control_decision_should_execute_commit": bool(
            out_should_execute_commit
        ),
        "project_browser_autonomous_bounded_local_control_decision_should_push": bool(
            out_should_push
        ),
        "project_browser_autonomous_bounded_local_control_decision_manual_review_required": bool(
            out_manual_review_required
        ),
        "project_browser_autonomous_bounded_local_control_decision_should_stop": bool(
            out_should_stop
        ),
        "project_browser_autonomous_bounded_local_control_decision_stop_reason": (
            out_stop_reason
        ),
        "project_browser_autonomous_bounded_local_control_decision_next_action": (
            out_next_action
        ),
        "project_browser_autonomous_bounded_local_control_decision_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_bounded_local_control_decision_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_result_assimilation_status,
                    normalized_result_class,
                    normalized_result_block_reason,
                    normalized_source_selected_launch_kind,
                    normalized_source_selected_launch_action,
                    normalized_source_execution_status,
                    normalized_delegated_existing_path_kind,
                    normalized_delegated_existing_status,
                    normalized_generated_prompt_reentry_result_status,
                    normalized_rollback_execution_result_status,
                    normalized_commit_execution_result_status,
                    normalized_controller_feedback_kind,
                    normalized_next_controller_input_kind,
                    normalized_next_controller_input_source,
                    normalized_next_controller_action_hint,
                    normalized_stop_reason,
                    normalized_next_action,
                    normalized_next_step_launch_execution_status,
                    normalized_next_step_launch_contract_status,
                    normalized_bounded_local_loop_contract_status,
                    normalized_multi_cycle_controller_status,
                    normalized_reentry_result_assimilation_status,
                    normalized_rollback_result_assimilation_status,
                    normalized_commit_tag_result_assimilation_status,
                    "authoritative_result_not_selected" if not authoritative_selected else "",
                    "blocked_delegated_status_not_terminal"
                    if delegated_status_not_terminal
                    else "",
                ]
            )
        ),
    }

def _build_project_browser_autonomous_control_contract_dispatch_state(
    *,
    bounded_local_control_decision_status: str,
    control_contract_available: bool,
    control_contract_allowed: bool,
    control_contract_block_reason: str,
    control_contract_source: str,
    control_contract_kind: str,
    control_contract_action: str,
    control_contract_payload: Any,
    exactly_one_control_contract: bool,
    control_conflict_detected: bool,
    conflicting_control_contracts: Sequence[Any],
    continue_to_reentry_result_assimilation: bool,
    continue_to_rollback_result_assimilation: bool,
    continue_to_commit_result_assimilation: bool,
    manual_stop_contract: bool,
    blocked_contract: bool,
    selected_next_control_kind: str,
    selected_next_control_action: str,
    selected_next_control_payload: Any,
    next_control_ready_for_dispatch: bool,
    result_feedback_kind: str,
    result_feedback_status: str,
    delegated_existing_path_kind: str,
    delegated_existing_status: str,
    non_selected_launches_noop_confirmed: bool,
    should_continue_local_loop: bool,
    should_prepare_reentry_result_assimilation: bool,
    should_prepare_rollback_result_assimilation: bool,
    should_prepare_commit_result_assimilation: bool,
    should_prepare_next_controller_decision: bool,
    should_invoke_codex: bool,
    should_execute_rollback: bool,
    should_execute_commit: bool,
    should_push: bool,
    manual_review_required: bool,
    should_stop: bool,
    stop_reason: str,
    next_action: str,
    next_step_launch_result_assimilation_status: str,
    next_step_launch_execution_status: str,
    multi_cycle_controller_status: str,
    reentry_result_assimilation_status: str,
    rollback_result_assimilation_status: str,
    commit_tag_result_assimilation_status: str,
) -> dict[str, Any]:
    allowed_statuses = {
        "control_contract_dispatch_reentry_result_assimilation_ready",
        "control_contract_dispatch_rollback_result_assimilation_ready",
        "control_contract_dispatch_commit_result_assimilation_ready",
        "control_contract_dispatch_manual_stop",
        "control_contract_dispatch_blocked",
        "control_contract_dispatch_blocked_conflict",
        "control_contract_dispatch_blocked_multiple_dispatches",
        "control_contract_dispatch_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "refresh_reentry_result_assimilation",
        "refresh_rollback_result_assimilation",
        "refresh_commit_result_assimilation",
        "manual_review_required",
        "insufficient_truth",
    }
    runtime_posture = [
        "prompt208_control_contract_dispatch",
        "metadata_only",
        "exactly_one_dispatch_path",
        "no_assimilation_execution",
        "no_codex_invocation",
        "no_rollback_execution",
        "no_commit_execution",
        "no_push",
    ]
    manual_or_blocked_statuses = {
        "bounded_local_control_decision_manual_stop",
        "bounded_local_control_decision_blocked",
        "bounded_local_control_decision_blocked_conflict",
        "bounded_local_control_decision_blocked_insufficient_truth",
    }

    normalized_control_status = _normalize_text(
        bounded_local_control_decision_status,
        default="insufficient_truth",
    )
    normalized_control_contract_block_reason = _normalize_text(
        control_contract_block_reason,
        default="",
    )
    normalized_control_contract_source = _normalize_text(control_contract_source, default="")
    normalized_control_contract_kind = _normalize_text(control_contract_kind, default="")
    normalized_control_contract_action = _normalize_text(control_contract_action, default="")
    normalized_selected_next_control_kind = _normalize_text(
        selected_next_control_kind,
        default="",
    )
    normalized_selected_next_control_action = _normalize_text(
        selected_next_control_action,
        default="",
    )
    normalized_result_feedback_kind = _normalize_text(result_feedback_kind, default="")
    normalized_result_feedback_status = _normalize_text(result_feedback_status, default="")
    normalized_delegated_existing_path_kind = _normalize_text(
        delegated_existing_path_kind,
        default="none",
    )
    normalized_delegated_existing_status = _normalize_text(
        delegated_existing_status,
        default="",
    )
    normalized_stop_reason = _normalize_text(stop_reason, default="")
    normalized_next_action = _normalize_text(next_action, default="manual_review_required")
    normalized_next_step_launch_result_assimilation_status = _normalize_text(
        next_step_launch_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_next_step_launch_execution_status = _normalize_text(
        next_step_launch_execution_status,
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
    normalized_conflicting_control_contracts = _normalize_string_list(
        conflicting_control_contracts
    )
    normalized_control_contract_payload = (
        dict(control_contract_payload) if isinstance(control_contract_payload, Mapping) else {}
    )
    normalized_selected_next_control_payload = (
        dict(selected_next_control_payload)
        if isinstance(selected_next_control_payload, Mapping)
        else {}
    )

    authoritative_selected = bool(
        bool(normalized_control_status)
        and bool(normalized_selected_next_control_kind)
        and bool(normalized_selected_next_control_action)
        and (
            (
                bool(exactly_one_control_contract)
                and bool(control_contract_available)
                and normalized_control_status not in manual_or_blocked_statuses
            )
            or normalized_control_status in manual_or_blocked_statuses
        )
    )

    reentry_dispatch_candidate = bool(
        bool(control_contract_allowed)
        and normalized_selected_next_control_kind == "reentry_result_assimilation"
        and normalized_selected_next_control_action
        == "dispatch_reentry_result_assimilation"
        and bool(continue_to_reentry_result_assimilation)
        and bool(next_control_ready_for_dispatch)
        and normalized_delegated_existing_path_kind == "generated_prompt_reentry"
        and bool(normalized_delegated_existing_status)
        and not bool(manual_review_required)
        and not bool(should_stop)
    )
    rollback_dispatch_candidate = bool(
        bool(control_contract_allowed)
        and normalized_selected_next_control_kind == "rollback_result_assimilation"
        and normalized_selected_next_control_action
        == "dispatch_rollback_result_assimilation"
        and bool(continue_to_rollback_result_assimilation)
        and bool(next_control_ready_for_dispatch)
        and normalized_delegated_existing_path_kind == "rollback_execution"
        and bool(normalized_delegated_existing_status)
        and not bool(manual_review_required)
        and not bool(should_stop)
    )
    commit_dispatch_candidate = bool(
        bool(control_contract_allowed)
        and normalized_selected_next_control_kind == "commit_result_assimilation"
        and normalized_selected_next_control_action == "dispatch_commit_result_assimilation"
        and bool(continue_to_commit_result_assimilation)
        and bool(next_control_ready_for_dispatch)
        and normalized_delegated_existing_path_kind == "commit_execution"
        and bool(normalized_delegated_existing_status)
        and not bool(manual_review_required)
        and not bool(should_stop)
    )
    manual_stop_dispatch_candidate = bool(
        normalized_selected_next_control_kind == "manual_stop"
        or bool(manual_stop_contract)
        or bool(manual_review_required)
        or bool(should_stop)
        or normalized_control_status == "bounded_local_control_decision_manual_stop"
    )
    blocked_dispatch_candidate = bool(
        normalized_selected_next_control_kind == "blocked"
        or bool(blocked_contract)
        or normalized_control_status
        in {
            "bounded_local_control_decision_blocked",
            "bounded_local_control_decision_blocked_conflict",
            "bounded_local_control_decision_blocked_insufficient_truth",
        }
    )

    non_stop_candidates: list[str] = []
    if reentry_dispatch_candidate:
        non_stop_candidates.append("reentry_result_assimilation")
    if rollback_dispatch_candidate:
        non_stop_candidates.append("rollback_result_assimilation")
    if commit_dispatch_candidate:
        non_stop_candidates.append("commit_result_assimilation")
    non_stop_candidates = sorted(non_stop_candidates)

    status = "control_contract_dispatch_blocked_insufficient_truth"
    dispatch_contract_available = False
    dispatch_contract_allowed = False
    dispatch_contract_block_reason = "insufficient_control_contract_dispatch_truth"
    dispatch_contract_source = (
        normalized_control_contract_source or "prompt207_bounded_local_control_decision"
    )
    selected_control_kind = "blocked"
    selected_control_action = "manual_review_required"
    selected_control_payload: dict[str, Any] = {}
    exactly_one_dispatch_path = False
    dispatch_conflict_detected = False
    conflicting_dispatch_paths: list[str] = []
    reentry_result_assimilation_dispatch_ready = False
    rollback_result_assimilation_dispatch_ready = False
    commit_result_assimilation_dispatch_ready = False
    manual_stop_dispatch_ready = False
    blocked_dispatch_ready = False
    downstream_assimilation_kind = ""
    downstream_assimilation_action = ""
    downstream_assimilation_payload: dict[str, Any] = {}
    downstream_refresh_allowed = False
    downstream_refresh_source = ""
    downstream_refresh_applied = False
    downstream_refresh_block_reason = ""
    non_selected_dispatch_paths_noop = True
    out_should_dispatch_reentry_result_assimilation = False
    out_should_dispatch_rollback_result_assimilation = False
    out_should_dispatch_commit_result_assimilation = False
    out_should_continue_local_loop = False
    out_should_prepare_next_controller_decision = False
    out_should_invoke_codex = False
    out_should_execute_rollback = False
    out_should_execute_commit = False
    out_should_push = False
    out_manual_review_required = True
    out_should_stop = True
    out_stop_reason = normalized_stop_reason or "insufficient_control_contract_dispatch_truth"
    out_next_action = "manual_review_required"

    if not authoritative_selected:
        status = "control_contract_dispatch_blocked_insufficient_truth"
        dispatch_contract_available = False
        dispatch_contract_allowed = False
        dispatch_contract_block_reason = "insufficient_control_contract_dispatch_truth"
        blocked_dispatch_ready = True
    elif bool(manual_review_required) or bool(should_stop) or manual_stop_dispatch_candidate:
        status = "control_contract_dispatch_manual_stop"
        dispatch_contract_available = True
        dispatch_contract_allowed = False
        dispatch_contract_block_reason = ""
        selected_control_kind = "manual_stop"
        selected_control_action = "manual_review_required"
        selected_control_payload = (
            dict(normalized_selected_next_control_payload)
            if normalized_selected_next_control_payload
            else {
                "control_kind": "manual_stop",
                "source": "prompt207_bounded_local_control_decision",
                "stop_reason": normalized_stop_reason or "manual_stop",
                "next_action": "manual_review_required",
            }
        )
        exactly_one_dispatch_path = True
        manual_stop_dispatch_ready = True
        downstream_refresh_allowed = False
        downstream_refresh_source = "prompt208_control_contract_dispatch"
        downstream_refresh_applied = False
        downstream_refresh_block_reason = "manual_stop_selected"
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = normalized_stop_reason or "manual_stop"
        out_next_action = "manual_review_required"
    elif blocked_dispatch_candidate:
        status = "control_contract_dispatch_blocked"
        dispatch_contract_available = True
        dispatch_contract_allowed = False
        dispatch_contract_block_reason = (
            normalized_control_contract_block_reason
            or "bounded_local_control_not_safe"
        )
        selected_control_kind = "blocked"
        selected_control_action = "manual_review_required"
        selected_control_payload = (
            dict(normalized_selected_next_control_payload)
            if normalized_selected_next_control_payload
            else {
                "control_kind": "blocked",
                "source": "prompt207_bounded_local_control_decision",
                "stop_reason": (
                    normalized_stop_reason
                    or normalized_control_contract_block_reason
                    or "bounded_local_control_not_safe"
                ),
                "next_action": "manual_review_required",
            }
        )
        exactly_one_dispatch_path = True
        blocked_dispatch_ready = True
        downstream_refresh_allowed = False
        downstream_refresh_source = "prompt208_control_contract_dispatch"
        downstream_refresh_applied = False
        downstream_refresh_block_reason = "blocked_control_contract"
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = (
            normalized_stop_reason
            or normalized_control_contract_block_reason
            or "bounded_local_control_not_safe"
        )
        out_next_action = "manual_review_required"
    elif len(non_stop_candidates) > 1:
        status = "control_contract_dispatch_blocked_conflict"
        dispatch_contract_available = True
        dispatch_contract_allowed = False
        dispatch_contract_block_reason = "conflicting_control_contract_dispatch_paths"
        exactly_one_dispatch_path = False
        dispatch_conflict_detected = True
        conflicting_dispatch_paths = list(non_stop_candidates)
        downstream_refresh_allowed = False
        downstream_refresh_source = "prompt208_control_contract_dispatch"
        downstream_refresh_applied = False
        downstream_refresh_block_reason = "conflicting_control_contract_dispatch_paths"
        non_selected_dispatch_paths_noop = False
        blocked_dispatch_ready = True
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "conflicting_control_contract_dispatch_paths"
        out_next_action = "manual_review_required"
    elif reentry_dispatch_candidate:
        status = "control_contract_dispatch_reentry_result_assimilation_ready"
        dispatch_contract_available = True
        dispatch_contract_allowed = True
        dispatch_contract_block_reason = ""
        selected_control_kind = "reentry_result_assimilation"
        selected_control_action = "dispatch_reentry_result_assimilation"
        selected_control_payload = (
            dict(normalized_selected_next_control_payload)
            if normalized_selected_next_control_payload
            else dict(normalized_control_contract_payload)
        )
        exactly_one_dispatch_path = True
        reentry_result_assimilation_dispatch_ready = True
        downstream_assimilation_kind = "reentry_result_assimilation"
        downstream_assimilation_action = "refresh_reentry_result_assimilation"
        downstream_assimilation_payload = dict(selected_control_payload)
        downstream_refresh_allowed = True
        downstream_refresh_source = "prompt208_control_contract_dispatch"
        downstream_refresh_applied = True
        out_should_dispatch_reentry_result_assimilation = True
        out_manual_review_required = False
        out_should_stop = False
        out_stop_reason = ""
        out_next_action = "refresh_reentry_result_assimilation"
    elif rollback_dispatch_candidate:
        status = "control_contract_dispatch_rollback_result_assimilation_ready"
        dispatch_contract_available = True
        dispatch_contract_allowed = True
        dispatch_contract_block_reason = ""
        selected_control_kind = "rollback_result_assimilation"
        selected_control_action = "dispatch_rollback_result_assimilation"
        selected_control_payload = (
            dict(normalized_selected_next_control_payload)
            if normalized_selected_next_control_payload
            else dict(normalized_control_contract_payload)
        )
        exactly_one_dispatch_path = True
        rollback_result_assimilation_dispatch_ready = True
        downstream_assimilation_kind = "rollback_result_assimilation"
        downstream_assimilation_action = "refresh_rollback_result_assimilation"
        downstream_assimilation_payload = dict(selected_control_payload)
        downstream_refresh_allowed = True
        downstream_refresh_source = "prompt208_control_contract_dispatch"
        downstream_refresh_applied = True
        out_should_dispatch_rollback_result_assimilation = True
        out_manual_review_required = False
        out_should_stop = False
        out_stop_reason = ""
        out_next_action = "refresh_rollback_result_assimilation"
    elif commit_dispatch_candidate:
        status = "control_contract_dispatch_commit_result_assimilation_ready"
        dispatch_contract_available = True
        dispatch_contract_allowed = True
        dispatch_contract_block_reason = ""
        selected_control_kind = "commit_result_assimilation"
        selected_control_action = "dispatch_commit_result_assimilation"
        selected_control_payload = (
            dict(normalized_selected_next_control_payload)
            if normalized_selected_next_control_payload
            else dict(normalized_control_contract_payload)
        )
        exactly_one_dispatch_path = True
        commit_result_assimilation_dispatch_ready = True
        downstream_assimilation_kind = "commit_result_assimilation"
        downstream_assimilation_action = "refresh_commit_result_assimilation"
        downstream_assimilation_payload = dict(selected_control_payload)
        downstream_refresh_allowed = True
        downstream_refresh_source = "prompt208_control_contract_dispatch"
        downstream_refresh_applied = True
        out_should_dispatch_commit_result_assimilation = True
        out_manual_review_required = False
        out_should_stop = False
        out_stop_reason = ""
        out_next_action = "refresh_commit_result_assimilation"
    else:
        status = "control_contract_dispatch_blocked_insufficient_truth"
        dispatch_contract_available = False
        dispatch_contract_allowed = False
        dispatch_contract_block_reason = "insufficient_control_contract_dispatch_truth"
        blocked_dispatch_ready = True
        downstream_refresh_allowed = False
        downstream_refresh_source = "prompt208_control_contract_dispatch"
        downstream_refresh_applied = False
        downstream_refresh_block_reason = "insufficient_control_contract_dispatch_truth"
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_control_contract_dispatch_truth"
        out_next_action = "manual_review_required"

    selected_refresh_count = sum(
        1
        for flag in (
            reentry_result_assimilation_dispatch_ready,
            rollback_result_assimilation_dispatch_ready,
            commit_result_assimilation_dispatch_ready,
            manual_stop_dispatch_ready,
            blocked_dispatch_ready,
        )
        if flag
    )
    if selected_refresh_count > 1:
        status = "control_contract_dispatch_blocked_multiple_dispatches"
        dispatch_contract_allowed = False
        dispatch_contract_block_reason = "multiple_downstream_refreshes_selected"
        dispatch_conflict_detected = True
        conflicting_dispatch_paths = _normalize_string_list(
            [
                "reentry_result_assimilation"
                if reentry_result_assimilation_dispatch_ready
                else "",
                "rollback_result_assimilation"
                if rollback_result_assimilation_dispatch_ready
                else "",
                "commit_result_assimilation"
                if commit_result_assimilation_dispatch_ready
                else "",
                "manual_stop" if manual_stop_dispatch_ready else "",
                "blocked" if blocked_dispatch_ready else "",
            ]
        )
        reentry_result_assimilation_dispatch_ready = False
        rollback_result_assimilation_dispatch_ready = False
        commit_result_assimilation_dispatch_ready = False
        manual_stop_dispatch_ready = False
        blocked_dispatch_ready = True
        downstream_assimilation_kind = ""
        downstream_assimilation_action = ""
        downstream_assimilation_payload = {}
        downstream_refresh_allowed = False
        downstream_refresh_applied = False
        downstream_refresh_block_reason = "multiple_downstream_refreshes_selected"
        non_selected_dispatch_paths_noop = False
        out_should_dispatch_reentry_result_assimilation = False
        out_should_dispatch_rollback_result_assimilation = False
        out_should_dispatch_commit_result_assimilation = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "multiple_downstream_refreshes_selected"
        out_next_action = "manual_review_required"

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if out_next_action not in allowed_next_actions:
        out_next_action = "insufficient_truth"
    if status == "insufficient_truth":
        status = "control_contract_dispatch_blocked_insufficient_truth"
        dispatch_contract_available = False
        dispatch_contract_allowed = False
        dispatch_contract_block_reason = "insufficient_control_contract_dispatch_truth"
        selected_control_kind = "blocked"
        selected_control_action = "manual_review_required"
        selected_control_payload = {}
        exactly_one_dispatch_path = False
        dispatch_conflict_detected = False
        conflicting_dispatch_paths = []
        reentry_result_assimilation_dispatch_ready = False
        rollback_result_assimilation_dispatch_ready = False
        commit_result_assimilation_dispatch_ready = False
        manual_stop_dispatch_ready = False
        blocked_dispatch_ready = True
        downstream_assimilation_kind = ""
        downstream_assimilation_action = ""
        downstream_assimilation_payload = {}
        downstream_refresh_allowed = False
        downstream_refresh_source = "prompt208_control_contract_dispatch"
        downstream_refresh_applied = False
        downstream_refresh_block_reason = "insufficient_control_contract_dispatch_truth"
        non_selected_dispatch_paths_noop = True
        out_should_dispatch_reentry_result_assimilation = False
        out_should_dispatch_rollback_result_assimilation = False
        out_should_dispatch_commit_result_assimilation = False
        out_should_continue_local_loop = False
        out_should_prepare_next_controller_decision = False
        out_should_invoke_codex = False
        out_should_execute_rollback = False
        out_should_execute_commit = False
        out_should_push = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_control_contract_dispatch_truth"
        out_next_action = "manual_review_required"

    return {
        "project_browser_autonomous_control_contract_dispatch_status": status,
        "project_browser_autonomous_control_contract_dispatch_dispatch_contract_available": bool(
            dispatch_contract_available
        ),
        "project_browser_autonomous_control_contract_dispatch_dispatch_contract_allowed": bool(
            dispatch_contract_allowed
        ),
        "project_browser_autonomous_control_contract_dispatch_dispatch_contract_block_reason": (
            dispatch_contract_block_reason
        ),
        "project_browser_autonomous_control_contract_dispatch_dispatch_contract_source": (
            dispatch_contract_source
        ),
        "project_browser_autonomous_control_contract_dispatch_selected_control_kind": (
            selected_control_kind
        ),
        "project_browser_autonomous_control_contract_dispatch_selected_control_action": (
            selected_control_action
        ),
        "project_browser_autonomous_control_contract_dispatch_selected_control_payload": (
            selected_control_payload if isinstance(selected_control_payload, Mapping) else {}
        ),
        "project_browser_autonomous_control_contract_dispatch_exactly_one_dispatch_path": bool(
            exactly_one_dispatch_path
        ),
        "project_browser_autonomous_control_contract_dispatch_dispatch_conflict_detected": bool(
            dispatch_conflict_detected
        ),
        "project_browser_autonomous_control_contract_dispatch_conflicting_dispatch_paths": (
            conflicting_dispatch_paths
        ),
        "project_browser_autonomous_control_contract_dispatch_reentry_result_assimilation_dispatch_ready": bool(
            reentry_result_assimilation_dispatch_ready
        ),
        "project_browser_autonomous_control_contract_dispatch_rollback_result_assimilation_dispatch_ready": bool(
            rollback_result_assimilation_dispatch_ready
        ),
        "project_browser_autonomous_control_contract_dispatch_commit_result_assimilation_dispatch_ready": bool(
            commit_result_assimilation_dispatch_ready
        ),
        "project_browser_autonomous_control_contract_dispatch_manual_stop_dispatch_ready": bool(
            manual_stop_dispatch_ready
        ),
        "project_browser_autonomous_control_contract_dispatch_blocked_dispatch_ready": bool(
            blocked_dispatch_ready
        ),
        "project_browser_autonomous_control_contract_dispatch_downstream_assimilation_kind": (
            downstream_assimilation_kind
        ),
        "project_browser_autonomous_control_contract_dispatch_downstream_assimilation_action": (
            downstream_assimilation_action
        ),
        "project_browser_autonomous_control_contract_dispatch_downstream_assimilation_payload": (
            downstream_assimilation_payload
            if isinstance(downstream_assimilation_payload, Mapping)
            else {}
        ),
        "project_browser_autonomous_control_contract_dispatch_downstream_refresh_allowed": bool(
            downstream_refresh_allowed
        ),
        "project_browser_autonomous_control_contract_dispatch_downstream_refresh_source": (
            downstream_refresh_source
        ),
        "project_browser_autonomous_control_contract_dispatch_downstream_refresh_applied": bool(
            downstream_refresh_applied
        ),
        "project_browser_autonomous_control_contract_dispatch_downstream_refresh_block_reason": (
            downstream_refresh_block_reason
        ),
        "project_browser_autonomous_control_contract_dispatch_non_selected_dispatch_paths_noop": bool(
            non_selected_dispatch_paths_noop
        ),
        "project_browser_autonomous_control_contract_dispatch_should_dispatch_reentry_result_assimilation": bool(
            out_should_dispatch_reentry_result_assimilation
        ),
        "project_browser_autonomous_control_contract_dispatch_should_dispatch_rollback_result_assimilation": bool(
            out_should_dispatch_rollback_result_assimilation
        ),
        "project_browser_autonomous_control_contract_dispatch_should_dispatch_commit_result_assimilation": bool(
            out_should_dispatch_commit_result_assimilation
        ),
        "project_browser_autonomous_control_contract_dispatch_should_continue_local_loop": bool(
            out_should_continue_local_loop
        ),
        "project_browser_autonomous_control_contract_dispatch_should_prepare_next_controller_decision": bool(
            out_should_prepare_next_controller_decision
        ),
        "project_browser_autonomous_control_contract_dispatch_should_invoke_codex": bool(
            out_should_invoke_codex
        ),
        "project_browser_autonomous_control_contract_dispatch_should_execute_rollback": bool(
            out_should_execute_rollback
        ),
        "project_browser_autonomous_control_contract_dispatch_should_execute_commit": bool(
            out_should_execute_commit
        ),
        "project_browser_autonomous_control_contract_dispatch_should_push": bool(
            out_should_push
        ),
        "project_browser_autonomous_control_contract_dispatch_manual_review_required": bool(
            out_manual_review_required
        ),
        "project_browser_autonomous_control_contract_dispatch_should_stop": bool(
            out_should_stop
        ),
        "project_browser_autonomous_control_contract_dispatch_stop_reason": (
            out_stop_reason
        ),
        "project_browser_autonomous_control_contract_dispatch_next_action": (
            out_next_action
        ),
        "project_browser_autonomous_control_contract_dispatch_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_control_contract_dispatch_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_control_status,
                    normalized_control_contract_kind,
                    normalized_control_contract_action,
                    normalized_selected_next_control_kind,
                    normalized_selected_next_control_action,
                    normalized_result_feedback_kind,
                    normalized_result_feedback_status,
                    normalized_delegated_existing_path_kind,
                    normalized_delegated_existing_status,
                    normalized_stop_reason,
                    normalized_next_action,
                    normalized_next_step_launch_result_assimilation_status,
                    normalized_next_step_launch_execution_status,
                    normalized_multi_cycle_controller_status,
                    normalized_reentry_result_assimilation_status,
                    normalized_rollback_result_assimilation_status,
                    normalized_commit_tag_result_assimilation_status,
                    "authoritative_control_contract_not_selected"
                    if not authoritative_selected
                    else "",
                    "control_contract_conflict_detected"
                    if bool(control_conflict_detected)
                    else "",
                    "non_selected_launches_activity_not_confirmed"
                    if not bool(non_selected_launches_noop_confirmed)
                    else "",
                    "conflicting_control_contracts_present"
                    if normalized_conflicting_control_contracts
                    else "",
                ]
            )
        ),
    }

def _build_project_browser_autonomous_control_dispatch_refresh_state(
    *,
    control_contract_dispatch_status: str,
    dispatch_contract_available: bool,
    dispatch_contract_allowed: bool,
    dispatch_contract_block_reason: str,
    dispatch_contract_source: str,
    selected_control_kind: str,
    selected_control_action: str,
    selected_control_payload: Any,
    exactly_one_dispatch_path: bool,
    dispatch_conflict_detected: bool,
    conflicting_dispatch_paths: Sequence[Any],
    reentry_result_assimilation_dispatch_ready: bool,
    rollback_result_assimilation_dispatch_ready: bool,
    commit_result_assimilation_dispatch_ready: bool,
    manual_stop_dispatch_ready: bool,
    blocked_dispatch_ready: bool,
    downstream_assimilation_kind: str,
    downstream_assimilation_action: str,
    downstream_assimilation_payload: Any,
    downstream_refresh_allowed: bool,
    downstream_refresh_source: str,
    downstream_refresh_applied: bool,
    downstream_refresh_block_reason: str,
    non_selected_dispatch_paths_noop: bool,
    should_dispatch_reentry_result_assimilation: bool,
    should_dispatch_rollback_result_assimilation: bool,
    should_dispatch_commit_result_assimilation: bool,
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
    bounded_local_control_decision_status: str,
    next_step_launch_result_assimilation_status: str,
    reentry_result_assimilation_status: str,
    reentry_result_assimilation_next_action: str,
    rollback_result_assimilation_status: str,
    rollback_result_assimilation_next_action: str,
    commit_tag_result_assimilation_status: str,
    commit_tag_result_assimilation_next_action: str,
    multi_cycle_controller_status: str,
) -> dict[str, Any]:
    allowed_statuses = {
        "control_dispatch_refresh_reentry_result_assimilation_completed",
        "control_dispatch_refresh_rollback_result_assimilation_completed",
        "control_dispatch_refresh_commit_result_assimilation_completed",
        "control_dispatch_refresh_manual_stop",
        "control_dispatch_refresh_blocked_not_allowed",
        "control_dispatch_refresh_blocked_multiple_refreshes",
        "control_dispatch_refresh_blocked_unknown_kind",
        "control_dispatch_refresh_blocked_existing_assimilation",
        "control_dispatch_refresh_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "assimilate_control_dispatch_refresh_result",
        "manual_review_required",
        "insufficient_truth",
    }
    runtime_posture = [
        "prompt209_control_dispatch_refresh",
        "metadata_only",
        "exactly_one_assimilation_refresh_path",
        "no_codex_invocation",
        "no_rollback_execution",
        "no_commit_execution",
        "no_git_mutation",
        "no_push",
    ]
    allowed_selected_kinds = {
        "reentry_result_assimilation",
        "rollback_result_assimilation",
        "commit_result_assimilation",
    }

    normalized_dispatch_status = _normalize_text(
        control_contract_dispatch_status,
        default="insufficient_truth",
    )
    normalized_dispatch_contract_block_reason = _normalize_text(
        dispatch_contract_block_reason,
        default="",
    )
    normalized_dispatch_contract_source = _normalize_text(dispatch_contract_source, default="")
    normalized_selected_control_kind = _normalize_text(selected_control_kind, default="")
    normalized_selected_control_action = _normalize_text(selected_control_action, default="")
    normalized_downstream_assimilation_kind = _normalize_text(
        downstream_assimilation_kind,
        default="",
    )
    normalized_downstream_assimilation_action = _normalize_text(
        downstream_assimilation_action,
        default="",
    )
    normalized_downstream_refresh_source = _normalize_text(downstream_refresh_source, default="")
    normalized_downstream_refresh_block_reason = _normalize_text(
        downstream_refresh_block_reason,
        default="",
    )
    normalized_stop_reason = _normalize_text(stop_reason, default="")
    normalized_next_action = _normalize_text(next_action, default="manual_review_required")
    normalized_bounded_local_control_decision_status = _normalize_text(
        bounded_local_control_decision_status,
        default="insufficient_truth",
    )
    normalized_next_step_launch_result_assimilation_status = _normalize_text(
        next_step_launch_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_reentry_result_assimilation_status = _normalize_text(
        reentry_result_assimilation_status,
        default="",
    )
    normalized_reentry_result_assimilation_next_action = _normalize_text(
        reentry_result_assimilation_next_action,
        default="",
    )
    normalized_rollback_result_assimilation_status = _normalize_text(
        rollback_result_assimilation_status,
        default="",
    )
    normalized_rollback_result_assimilation_next_action = _normalize_text(
        rollback_result_assimilation_next_action,
        default="",
    )
    normalized_commit_result_assimilation_status = _normalize_text(
        commit_tag_result_assimilation_status,
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
    normalized_conflicting_dispatch_paths = _normalize_string_list(
        conflicting_dispatch_paths
    )
    normalized_selected_control_payload = (
        dict(selected_control_payload) if isinstance(selected_control_payload, Mapping) else {}
    )
    normalized_downstream_assimilation_payload = (
        dict(downstream_assimilation_payload)
        if isinstance(downstream_assimilation_payload, Mapping)
        else {}
    )

    authoritative_selected = bool(
        bool(normalized_dispatch_status)
        and bool(normalized_selected_control_kind)
        and bool(normalized_selected_control_action)
        and (
            (
                bool(dispatch_contract_available)
                and bool(exactly_one_dispatch_path)
                and normalized_selected_control_kind in allowed_selected_kinds
            )
            or normalized_dispatch_status
            in {
                "control_contract_dispatch_manual_stop",
                "control_contract_dispatch_blocked",
                "control_contract_dispatch_blocked_conflict",
                "control_contract_dispatch_blocked_multiple_dispatches",
                "control_contract_dispatch_blocked_insufficient_truth",
            }
        )
    )

    reentry_candidate = bool(
        bool(dispatch_contract_allowed)
        and normalized_selected_control_kind == "reentry_result_assimilation"
        and normalized_selected_control_action == "dispatch_reentry_result_assimilation"
        and bool(should_dispatch_reentry_result_assimilation)
        and bool(reentry_result_assimilation_dispatch_ready)
        and normalized_downstream_assimilation_kind == "reentry_result_assimilation"
        and normalized_downstream_assimilation_action
        == "refresh_reentry_result_assimilation"
        and not bool(manual_review_required)
        and not bool(should_stop)
    )
    rollback_candidate = bool(
        bool(dispatch_contract_allowed)
        and normalized_selected_control_kind == "rollback_result_assimilation"
        and normalized_selected_control_action == "dispatch_rollback_result_assimilation"
        and bool(should_dispatch_rollback_result_assimilation)
        and bool(rollback_result_assimilation_dispatch_ready)
        and normalized_downstream_assimilation_kind == "rollback_result_assimilation"
        and normalized_downstream_assimilation_action
        == "refresh_rollback_result_assimilation"
        and not bool(manual_review_required)
        and not bool(should_stop)
    )
    commit_candidate = bool(
        bool(dispatch_contract_allowed)
        and normalized_selected_control_kind == "commit_result_assimilation"
        and normalized_selected_control_action == "dispatch_commit_result_assimilation"
        and bool(should_dispatch_commit_result_assimilation)
        and bool(commit_result_assimilation_dispatch_ready)
        and normalized_downstream_assimilation_kind == "commit_result_assimilation"
        and normalized_downstream_assimilation_action == "refresh_commit_result_assimilation"
        and not bool(manual_review_required)
        and not bool(should_stop)
    )
    manual_stop_candidate = bool(
        normalized_selected_control_kind == "manual_stop"
        or bool(manual_stop_dispatch_ready)
        or bool(manual_review_required)
        or bool(should_stop)
        or normalized_dispatch_status == "control_contract_dispatch_manual_stop"
    )
    blocked_candidate = bool(
        normalized_selected_control_kind == "blocked"
        or bool(blocked_dispatch_ready)
        or normalized_dispatch_status
        in {
            "control_contract_dispatch_blocked",
            "control_contract_dispatch_blocked_conflict",
            "control_contract_dispatch_blocked_multiple_dispatches",
            "control_contract_dispatch_blocked_insufficient_truth",
        }
    )
    non_stop_candidates: list[str] = []
    if reentry_candidate:
        non_stop_candidates.append("reentry_result_assimilation")
    if rollback_candidate:
        non_stop_candidates.append("rollback_result_assimilation")
    if commit_candidate:
        non_stop_candidates.append("commit_result_assimilation")
    non_stop_candidates = sorted(non_stop_candidates)

    status = "control_dispatch_refresh_blocked_insufficient_truth"
    refresh_allowed = False
    refresh_attempted = False
    refresh_completed = False
    refresh_failed = False
    refresh_block_reason = "blocked_insufficient_control_dispatch_refresh_truth"
    refresh_source = (
        normalized_dispatch_contract_source or "prompt208_control_contract_dispatch"
    )
    selected_assimilation_kind = normalized_selected_control_kind or "blocked"
    selected_assimilation_action = (
        normalized_selected_control_action or "manual_review_required"
    )
    selected_assimilation_payload = (
        dict(normalized_selected_control_payload)
        if normalized_selected_control_payload
        else dict(normalized_downstream_assimilation_payload)
    )
    exactly_one_refresh_path = False
    refresh_conflict_detected = False
    conflicting_refresh_paths: list[str] = []
    non_selected_refresh_paths_noop = True
    reentry_result_assimilation_refresh_executed = False
    rollback_result_assimilation_refresh_executed = False
    commit_result_assimilation_refresh_executed = False
    manual_stop_refresh_executed = False
    blocked_refresh_executed = False
    delegated_assimilation_path_kind = "none"
    delegated_assimilation_status = ""
    delegated_assimilation_next_action = ""
    result_class = "blocked"
    out_should_continue_local_loop = False
    out_should_prepare_next_controller_decision = False
    out_should_invoke_codex = False
    out_should_execute_rollback = False
    out_should_execute_commit = False
    out_should_push = False
    out_manual_review_required = True
    out_should_stop = True
    out_stop_reason = (
        normalized_stop_reason or "blocked_insufficient_control_dispatch_refresh_truth"
    )
    out_next_action = "manual_review_required"

    if manual_stop_candidate:
        status = "control_dispatch_refresh_manual_stop"
        refresh_allowed = False
        refresh_attempted = False
        refresh_completed = False
        refresh_failed = False
        refresh_block_reason = (
            normalized_dispatch_contract_block_reason
            or normalized_stop_reason
            or "manual_stop"
        )
        selected_assimilation_kind = "manual_stop"
        selected_assimilation_action = "manual_review_required"
        exactly_one_refresh_path = True
        manual_stop_refresh_executed = True
        delegated_assimilation_path_kind = "manual_stop"
        delegated_assimilation_status = normalized_dispatch_status
        delegated_assimilation_next_action = "manual_review_required"
        result_class = "manual_stop"
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = normalized_stop_reason or "manual_stop"
        out_next_action = "manual_review_required"
    elif blocked_candidate:
        status = "control_dispatch_refresh_blocked_not_allowed"
        refresh_allowed = False
        refresh_attempted = False
        refresh_completed = False
        refresh_failed = False
        refresh_block_reason = (
            normalized_dispatch_contract_block_reason
            or normalized_downstream_refresh_block_reason
            or "blocked_insufficient_control_dispatch_refresh_truth"
        )
        selected_assimilation_kind = "blocked"
        selected_assimilation_action = "manual_review_required"
        exactly_one_refresh_path = True
        blocked_refresh_executed = True
        delegated_assimilation_path_kind = "blocked"
        delegated_assimilation_status = normalized_dispatch_status
        delegated_assimilation_next_action = "manual_review_required"
        result_class = "blocked"
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = (
            normalized_stop_reason
            or refresh_block_reason
            or "blocked_insufficient_control_dispatch_refresh_truth"
        )
        out_next_action = "manual_review_required"
    elif not authoritative_selected:
        status = "control_dispatch_refresh_blocked_insufficient_truth"
        refresh_block_reason = "blocked_insufficient_control_dispatch_refresh_truth"
        blocked_refresh_executed = True
    else:
        if not bool(dispatch_contract_allowed):
            refresh_block_reason = "blocked_dispatch_contract_not_allowed"
            status = "control_dispatch_refresh_blocked_not_allowed"
        elif not bool(downstream_refresh_allowed):
            refresh_block_reason = "blocked_downstream_refresh_not_allowed"
            status = "control_dispatch_refresh_blocked_not_allowed"
        elif not bool(downstream_refresh_applied):
            refresh_block_reason = "blocked_downstream_refresh_not_applied"
            status = "control_dispatch_refresh_blocked_not_allowed"
        elif not bool(exactly_one_dispatch_path):
            refresh_block_reason = "blocked_not_exactly_one_dispatch_path"
            status = "control_dispatch_refresh_blocked_not_allowed"
        elif bool(dispatch_conflict_detected):
            refresh_block_reason = "blocked_dispatch_conflict_detected"
            status = "control_dispatch_refresh_blocked_not_allowed"
        elif not bool(non_selected_dispatch_paths_noop):
            refresh_block_reason = "blocked_non_selected_dispatch_paths_not_noop"
            status = "control_dispatch_refresh_blocked_not_allowed"
        elif bool(manual_review_required):
            refresh_block_reason = "blocked_manual_review_required"
            status = "control_dispatch_refresh_blocked_not_allowed"
        elif bool(should_stop):
            refresh_block_reason = "blocked_should_stop"
            status = "control_dispatch_refresh_blocked_not_allowed"
        elif bool(should_invoke_codex):
            refresh_block_reason = "blocked_unexpected_codex_invocation_flag"
            status = "control_dispatch_refresh_blocked_not_allowed"
        elif bool(should_execute_rollback):
            refresh_block_reason = "blocked_unexpected_rollback_execution_flag"
            status = "control_dispatch_refresh_blocked_not_allowed"
        elif bool(should_execute_commit):
            refresh_block_reason = "blocked_unexpected_commit_execution_flag"
            status = "control_dispatch_refresh_blocked_not_allowed"
        elif bool(should_push):
            refresh_block_reason = "blocked_unexpected_push_flag"
            status = "control_dispatch_refresh_blocked_not_allowed"
        elif normalized_selected_control_kind not in allowed_selected_kinds:
            refresh_block_reason = "blocked_unknown_selected_control_kind"
            status = "control_dispatch_refresh_blocked_unknown_kind"
        elif len(non_stop_candidates) > 1:
            refresh_block_reason = "blocked_multiple_refreshes"
            status = "control_dispatch_refresh_blocked_multiple_refreshes"
        elif len(non_stop_candidates) != 1:
            refresh_block_reason = "blocked_insufficient_control_dispatch_refresh_truth"
            status = "control_dispatch_refresh_blocked_insufficient_truth"
        else:
            refresh_allowed = True
            refresh_attempted = True
            exactly_one_refresh_path = True
            refresh_block_reason = ""
            out_manual_review_required = False
            out_should_stop = False
            out_stop_reason = ""
            out_next_action = "assimilate_control_dispatch_refresh_result"
            result_class = "blocked"

            if normalized_selected_control_kind == "reentry_result_assimilation":
                reentry_result_assimilation_refresh_executed = True
                delegated_assimilation_path_kind = "reentry_result_assimilation"
                delegated_assimilation_status = normalized_reentry_result_assimilation_status
                delegated_assimilation_next_action = (
                    normalized_reentry_result_assimilation_next_action
                )
                if delegated_assimilation_status:
                    status = "control_dispatch_refresh_reentry_result_assimilation_completed"
                    refresh_completed = True
                    result_class = "reentry_result_assimilation_refreshed"
                else:
                    status = "control_dispatch_refresh_blocked_existing_assimilation"
                    refresh_allowed = False
                    refresh_completed = False
                    refresh_block_reason = "blocked_existing_assimilation_status_missing"
            elif normalized_selected_control_kind == "rollback_result_assimilation":
                rollback_result_assimilation_refresh_executed = True
                delegated_assimilation_path_kind = "rollback_result_assimilation"
                delegated_assimilation_status = normalized_rollback_result_assimilation_status
                delegated_assimilation_next_action = (
                    normalized_rollback_result_assimilation_next_action
                )
                if delegated_assimilation_status:
                    status = "control_dispatch_refresh_rollback_result_assimilation_completed"
                    refresh_completed = True
                    result_class = "rollback_result_assimilation_refreshed"
                else:
                    status = "control_dispatch_refresh_blocked_existing_assimilation"
                    refresh_allowed = False
                    refresh_completed = False
                    refresh_block_reason = "blocked_existing_assimilation_status_missing"
            elif normalized_selected_control_kind == "commit_result_assimilation":
                commit_result_assimilation_refresh_executed = True
                delegated_assimilation_path_kind = "commit_result_assimilation"
                delegated_assimilation_status = normalized_commit_result_assimilation_status
                delegated_assimilation_next_action = (
                    normalized_commit_result_assimilation_next_action
                )
                if delegated_assimilation_status:
                    status = "control_dispatch_refresh_commit_result_assimilation_completed"
                    refresh_completed = True
                    result_class = "commit_result_assimilation_refreshed"
                else:
                    status = "control_dispatch_refresh_blocked_existing_assimilation"
                    refresh_allowed = False
                    refresh_completed = False
                    refresh_block_reason = "blocked_existing_assimilation_status_missing"

            if status == "control_dispatch_refresh_blocked_existing_assimilation":
                refresh_failed = False
                result_class = "blocked"
                out_manual_review_required = True
                out_should_stop = True
                out_stop_reason = refresh_block_reason
                out_next_action = "manual_review_required"

    if len(non_stop_candidates) > 1:
        status = "control_dispatch_refresh_blocked_multiple_refreshes"
        refresh_allowed = False
        refresh_attempted = False
        refresh_completed = False
        refresh_failed = False
        refresh_block_reason = "blocked_multiple_refreshes"
        exactly_one_refresh_path = False
        refresh_conflict_detected = True
        conflicting_refresh_paths = list(non_stop_candidates)
        non_selected_refresh_paths_noop = False
        reentry_result_assimilation_refresh_executed = False
        rollback_result_assimilation_refresh_executed = False
        commit_result_assimilation_refresh_executed = False
        manual_stop_refresh_executed = False
        blocked_refresh_executed = True
        delegated_assimilation_path_kind = "blocked"
        delegated_assimilation_status = normalized_dispatch_status
        delegated_assimilation_next_action = "manual_review_required"
        result_class = "blocked"
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "blocked_multiple_refreshes"
        out_next_action = "manual_review_required"

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if out_next_action not in allowed_next_actions:
        out_next_action = "insufficient_truth"
    if status == "insufficient_truth":
        status = "control_dispatch_refresh_blocked_insufficient_truth"
        refresh_allowed = False
        refresh_attempted = False
        refresh_completed = False
        refresh_failed = False
        refresh_block_reason = "blocked_insufficient_control_dispatch_refresh_truth"
        selected_assimilation_kind = "blocked"
        selected_assimilation_action = "manual_review_required"
        selected_assimilation_payload = {}
        exactly_one_refresh_path = False
        refresh_conflict_detected = False
        conflicting_refresh_paths = []
        non_selected_refresh_paths_noop = True
        reentry_result_assimilation_refresh_executed = False
        rollback_result_assimilation_refresh_executed = False
        commit_result_assimilation_refresh_executed = False
        manual_stop_refresh_executed = False
        blocked_refresh_executed = True
        delegated_assimilation_path_kind = "blocked"
        delegated_assimilation_status = normalized_dispatch_status
        delegated_assimilation_next_action = "manual_review_required"
        result_class = "blocked"
        out_should_continue_local_loop = False
        out_should_prepare_next_controller_decision = False
        out_should_invoke_codex = False
        out_should_execute_rollback = False
        out_should_execute_commit = False
        out_should_push = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "blocked_insufficient_control_dispatch_refresh_truth"
        out_next_action = "manual_review_required"

    return {
        "project_browser_autonomous_control_dispatch_refresh_status": status,
        "project_browser_autonomous_control_dispatch_refresh_refresh_allowed": bool(
            refresh_allowed
        ),
        "project_browser_autonomous_control_dispatch_refresh_refresh_attempted": bool(
            refresh_attempted
        ),
        "project_browser_autonomous_control_dispatch_refresh_refresh_completed": bool(
            refresh_completed
        ),
        "project_browser_autonomous_control_dispatch_refresh_refresh_failed": bool(
            refresh_failed
        ),
        "project_browser_autonomous_control_dispatch_refresh_refresh_block_reason": (
            refresh_block_reason
        ),
        "project_browser_autonomous_control_dispatch_refresh_refresh_source": refresh_source,
        "project_browser_autonomous_control_dispatch_refresh_selected_assimilation_kind": (
            selected_assimilation_kind
        ),
        "project_browser_autonomous_control_dispatch_refresh_selected_assimilation_action": (
            selected_assimilation_action
        ),
        "project_browser_autonomous_control_dispatch_refresh_selected_assimilation_payload": (
            selected_assimilation_payload
            if isinstance(selected_assimilation_payload, Mapping)
            else {}
        ),
        "project_browser_autonomous_control_dispatch_refresh_exactly_one_refresh_path": bool(
            exactly_one_refresh_path
        ),
        "project_browser_autonomous_control_dispatch_refresh_refresh_conflict_detected": bool(
            refresh_conflict_detected
        ),
        "project_browser_autonomous_control_dispatch_refresh_conflicting_refresh_paths": (
            conflicting_refresh_paths
        ),
        "project_browser_autonomous_control_dispatch_refresh_non_selected_refresh_paths_noop": bool(
            non_selected_refresh_paths_noop
        ),
        "project_browser_autonomous_control_dispatch_refresh_reentry_result_assimilation_refresh_executed": bool(
            reentry_result_assimilation_refresh_executed
        ),
        "project_browser_autonomous_control_dispatch_refresh_rollback_result_assimilation_refresh_executed": bool(
            rollback_result_assimilation_refresh_executed
        ),
        "project_browser_autonomous_control_dispatch_refresh_commit_result_assimilation_refresh_executed": bool(
            commit_result_assimilation_refresh_executed
        ),
        "project_browser_autonomous_control_dispatch_refresh_manual_stop_refresh_executed": bool(
            manual_stop_refresh_executed
        ),
        "project_browser_autonomous_control_dispatch_refresh_blocked_refresh_executed": bool(
            blocked_refresh_executed
        ),
        "project_browser_autonomous_control_dispatch_refresh_delegated_assimilation_path_kind": (
            delegated_assimilation_path_kind
        ),
        "project_browser_autonomous_control_dispatch_refresh_delegated_assimilation_status": (
            delegated_assimilation_status
        ),
        "project_browser_autonomous_control_dispatch_refresh_delegated_assimilation_next_action": (
            delegated_assimilation_next_action
        ),
        "project_browser_autonomous_control_dispatch_refresh_reentry_result_assimilation_status": (
            normalized_reentry_result_assimilation_status
        ),
        "project_browser_autonomous_control_dispatch_refresh_rollback_result_assimilation_status": (
            normalized_rollback_result_assimilation_status
        ),
        "project_browser_autonomous_control_dispatch_refresh_commit_result_assimilation_status": (
            normalized_commit_result_assimilation_status
        ),
        "project_browser_autonomous_control_dispatch_refresh_result_class": result_class,
        "project_browser_autonomous_control_dispatch_refresh_control_dispatch_refresh_result_ready_for_assimilation": True,
        "project_browser_autonomous_control_dispatch_refresh_control_dispatch_refresh_result_assimilation_source": (
            "prompt209_control_dispatch_refresh"
        ),
        "project_browser_autonomous_control_dispatch_refresh_control_dispatch_refresh_result_next_stage": (
            "control_dispatch_refresh_result_assimilation"
        ),
        "project_browser_autonomous_control_dispatch_refresh_should_continue_local_loop": bool(
            out_should_continue_local_loop
        ),
        "project_browser_autonomous_control_dispatch_refresh_should_prepare_next_controller_decision": bool(
            out_should_prepare_next_controller_decision
        ),
        "project_browser_autonomous_control_dispatch_refresh_should_invoke_codex": bool(
            out_should_invoke_codex
        ),
        "project_browser_autonomous_control_dispatch_refresh_should_execute_rollback": bool(
            out_should_execute_rollback
        ),
        "project_browser_autonomous_control_dispatch_refresh_should_execute_commit": bool(
            out_should_execute_commit
        ),
        "project_browser_autonomous_control_dispatch_refresh_should_push": bool(
            out_should_push
        ),
        "project_browser_autonomous_control_dispatch_refresh_manual_review_required": bool(
            out_manual_review_required
        ),
        "project_browser_autonomous_control_dispatch_refresh_should_stop": bool(
            out_should_stop
        ),
        "project_browser_autonomous_control_dispatch_refresh_stop_reason": (
            out_stop_reason
        ),
        "project_browser_autonomous_control_dispatch_refresh_next_action": (
            out_next_action
        ),
        "project_browser_autonomous_control_dispatch_refresh_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_control_dispatch_refresh_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_dispatch_status,
                    normalized_selected_control_kind,
                    normalized_selected_control_action,
                    normalized_downstream_assimilation_kind,
                    normalized_downstream_assimilation_action,
                    normalized_downstream_refresh_source,
                    normalized_downstream_refresh_block_reason,
                    normalized_stop_reason,
                    normalized_next_action,
                    normalized_bounded_local_control_decision_status,
                    normalized_next_step_launch_result_assimilation_status,
                    normalized_reentry_result_assimilation_status,
                    normalized_reentry_result_assimilation_next_action,
                    normalized_rollback_result_assimilation_status,
                    normalized_rollback_result_assimilation_next_action,
                    normalized_commit_result_assimilation_status,
                    normalized_commit_result_assimilation_next_action,
                    normalized_multi_cycle_controller_status,
                    "authoritative_dispatch_not_selected"
                    if not authoritative_selected
                    else "",
                    "dispatch_conflict_detected" if bool(dispatch_conflict_detected) else "",
                    "conflicting_dispatch_paths_present"
                    if normalized_conflicting_dispatch_paths
                    else "",
                ]
            )
        ),
    }

def _build_project_browser_autonomous_final_runtime_continuation_guard_state(
    *,
    control_dispatch_refresh_result_assimilation_status: str,
    result_selected: bool,
    result_available: bool,
    result_class: str,
    result_block_reason: str,
    source_selected_assimilation_kind: str,
    source_selected_assimilation_action: str,
    source_refresh_status: str,
    source_refresh_completed: bool,
    source_refresh_failed: bool,
    non_selected_refresh_paths_noop_confirmed: bool,
    delegated_assimilation_path_kind: str,
    delegated_assimilation_status: str,
    delegated_assimilation_next_action: str,
    reentry_result_assimilation_status: str,
    rollback_result_assimilation_status: str,
    commit_result_assimilation_status: str,
    controller_feedback_ready: bool,
    controller_feedback_kind: str,
    controller_feedback_source: str,
    controller_feedback_payload: Any,
    final_step_result_kind: str,
    final_step_result_status: str,
    next_bounded_control_target_ready: bool,
    next_bounded_control_target_kind: str,
    next_bounded_control_target_action: str,
    next_bounded_control_target_payload: Any,
    continue_to_multi_cycle_controller: bool,
    manual_stop_target: bool,
    blocked_target: bool,
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
    control_dispatch_refresh_status: str,
    control_contract_dispatch_status: str,
    bounded_local_control_decision_status: str,
    next_step_launch_result_assimilation_status: str,
    multi_cycle_controller_status: str,
    cycle_budget_remaining: int,
    codex_budget_remaining: int,
    rollback_budget_remaining: int,
    commit_budget_remaining: int,
) -> dict[str, Any]:
    allowed_statuses = {
        "final_runtime_continuation_guard_multi_cycle_handback_ready",
        "final_runtime_continuation_guard_manual_stop",
        "final_runtime_continuation_guard_blocked",
        "final_runtime_continuation_guard_blocked_conflict",
        "final_runtime_continuation_guard_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "prepare_next_multi_cycle_decision",
        "manual_review_required",
        "insufficient_truth",
    }
    runtime_posture = [
        "prompt211_final_runtime_continuation_guard",
        "metadata_only",
        "bounded_handback_guard",
        "no_execution",
        "no_unbounded_loop",
        "no_codex_invocation",
        "no_rollback_execution",
        "no_commit_execution",
        "no_push",
    ]

    normalized_assimilation_status = _normalize_text(
        control_dispatch_refresh_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_result_class = _normalize_text(result_class, default="")
    normalized_result_block_reason = _normalize_text(result_block_reason, default="")
    normalized_source_selected_kind = _normalize_text(source_selected_assimilation_kind, default="")
    normalized_source_selected_action = _normalize_text(
        source_selected_assimilation_action,
        default="",
    )
    normalized_source_refresh_status = _normalize_text(source_refresh_status, default="")
    normalized_delegated_assimilation_status = _normalize_text(
        delegated_assimilation_status,
        default="",
    )
    normalized_controller_feedback_kind = _normalize_text(controller_feedback_kind, default="")
    normalized_controller_feedback_source = _normalize_text(
        controller_feedback_source,
        default="",
    )
    normalized_final_step_result_kind = _normalize_text(final_step_result_kind, default="")
    normalized_final_step_result_status = _normalize_text(
        final_step_result_status,
        default="",
    )
    normalized_target_kind = _normalize_text(next_bounded_control_target_kind, default="")
    normalized_target_action = _normalize_text(next_bounded_control_target_action, default="")
    normalized_stop_reason = _normalize_text(stop_reason, default="")
    normalized_next_action = _normalize_text(next_action, default="manual_review_required")
    normalized_multi_cycle_controller_status = _normalize_text(
        multi_cycle_controller_status,
        default="insufficient_truth",
    )
    normalized_control_dispatch_refresh_status = _normalize_text(
        control_dispatch_refresh_status,
        default="insufficient_truth",
    )
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
    _normalized_feedback_payload = (
        dict(controller_feedback_payload)
        if isinstance(controller_feedback_payload, Mapping)
        else {}
    )
    _normalized_target_payload = (
        dict(next_bounded_control_target_payload)
        if isinstance(next_bounded_control_target_payload, Mapping)
        else {}
    )

    out_cycle_budget_remaining = _as_non_negative_int(cycle_budget_remaining, default=0)
    out_codex_budget_remaining = _as_non_negative_int(codex_budget_remaining, default=0)
    out_rollback_budget_remaining = _as_non_negative_int(rollback_budget_remaining, default=0)
    out_commit_budget_remaining = _as_non_negative_int(commit_budget_remaining, default=0)
    budget_guard_checked = bool(
        out_cycle_budget_remaining >= 0
        and out_codex_budget_remaining >= 0
        and out_rollback_budget_remaining >= 0
        and out_commit_budget_remaining >= 0
    )

    authoritative_selected = bool(
        bool(normalized_assimilation_status)
        and bool(normalized_result_class)
        and bool(normalized_controller_feedback_source == "prompt209_control_dispatch_refresh")
        and (
            bool(normalized_target_kind)
            or normalized_assimilation_status
            in {
                "control_dispatch_refresh_result_manual_stop",
                "control_dispatch_refresh_result_failed",
                "control_dispatch_refresh_result_blocked",
                "control_dispatch_refresh_result_blocked_non_selected_refresh_activity",
                "control_dispatch_refresh_result_blocked_insufficient_truth",
            }
        )
        and (
            bool(controller_feedback_ready)
            or normalized_result_class
            in {"manual_stop", "failed", "blocked", "insufficient_truth", "blocked_non_selected_refresh_activity"}
        )
    )

    multi_cycle_handback_candidate = bool(
        normalized_result_class
        in {
            "reentry_result_assimilation_completed",
            "rollback_result_assimilation_completed",
            "commit_result_assimilation_completed",
        }
        and normalized_target_kind == "multi_cycle_controller"
        and normalized_target_action == "prepare_next_multi_cycle_decision"
        and bool(continue_to_multi_cycle_controller)
        and bool(should_prepare_next_controller_decision)
        and bool(controller_feedback_ready)
        and not bool(manual_review_required)
        and not bool(should_stop)
        and not bool(should_invoke_codex)
        and not bool(should_execute_rollback)
        and not bool(should_execute_commit)
        and not bool(should_push)
        and bool(non_selected_refresh_paths_noop_confirmed)
        and out_cycle_budget_remaining > 0
    )
    manual_stop_candidate = bool(
        normalized_result_class == "manual_stop"
        or bool(manual_stop_target)
        or bool(manual_review_required)
        or bool(should_stop)
        or normalized_assimilation_status == "control_dispatch_refresh_result_manual_stop"
    )
    blocked_candidate = bool(
        normalized_result_class
        in {
            "failed",
            "blocked",
            "insufficient_truth",
            "blocked_non_selected_refresh_activity",
        }
        or bool(blocked_target)
        or normalized_assimilation_status
        in {
            "control_dispatch_refresh_result_failed",
            "control_dispatch_refresh_result_blocked",
            "control_dispatch_refresh_result_blocked_non_selected_refresh_activity",
            "control_dispatch_refresh_result_blocked_insufficient_truth",
        }
    )

    unsupported_non_stop_targets: list[str] = []
    if _normalize_text(_normalized_target_payload.get("target"), default="") not in {
        "",
        "multi_cycle_controller",
        "manual_stop",
    }:
        unsupported_non_stop_targets.append(
            _normalize_text(_normalized_target_payload.get("target"), default="")
        )
    non_stop_candidates: list[str] = []
    if multi_cycle_handback_candidate:
        non_stop_candidates.append("multi_cycle_controller")
    non_stop_candidates = sorted(non_stop_candidates)

    unsafe_state_detected = bool(
        "unsafe" in normalized_result_class
        or "unsafe" in normalized_final_step_result_kind
        or "unsafe" in normalized_final_step_result_status
        or "unexpected_dirty" in normalized_final_step_result_status
    )
    dirty_state_requires_stop = bool(
        "dirty" in normalized_final_step_result_status
        and "expected_dirty" not in normalized_final_step_result_status
    )
    conflict_requires_stop = bool(
        bool(unsupported_non_stop_targets)
        or "conflict" in normalized_assimilation_status
        or "conflict" in normalized_control_dispatch_refresh_status
        or "conflict" in normalized_control_contract_dispatch_status
        or "conflict" in normalized_bounded_local_control_decision_status
        or "conflict" in normalized_next_step_launch_result_assimilation_status
    )

    status = "final_runtime_continuation_guard_blocked_insufficient_truth"
    continuation_guard_available = False
    continuation_guard_allowed = False
    continuation_guard_block_reason = "blocked_insufficient_final_runtime_continuation_truth"
    continuation_guard_source = "prompt210_control_dispatch_refresh_result_assimilation"
    next_control_target_kind = "blocked"
    next_control_target_action = "manual_review_required"
    next_control_target_payload: dict[str, Any] = {}
    multi_cycle_handback_ready = False
    manual_stop_ready = False
    blocked_ready = False
    exactly_one_continuation_target = False
    continuation_conflict_detected = False
    conflicting_continuation_targets: list[str] = []
    out_should_continue_local_loop = False
    out_should_prepare_next_controller_decision = False
    out_should_start_unbounded_loop = False
    out_should_invoke_codex = False
    out_should_execute_rollback = False
    out_should_execute_commit = False
    out_should_push = False
    out_manual_review_required = True
    out_should_stop = True
    out_stop_reason = normalized_stop_reason or "insufficient_final_runtime_continuation_truth"
    out_next_action = "manual_review_required"

    if not authoritative_selected:
        continuation_guard_block_reason = "blocked_authoritative_prompt210_missing"
        blocked_ready = True
        continuation_guard_available = False
    elif bool(manual_review_required):
        status = "final_runtime_continuation_guard_manual_stop"
        continuation_guard_available = True
        continuation_guard_allowed = False
        continuation_guard_block_reason = "blocked_manual_review_required"
        next_control_target_kind = "manual_stop"
        next_control_target_action = "manual_review_required"
        next_control_target_payload = {
            "target": "manual_stop",
            "source": "prompt211_final_runtime_continuation_guard",
            "stop_reason": normalized_stop_reason or "manual_stop",
            "next_action": "manual_review_required",
        }
        manual_stop_ready = True
        exactly_one_continuation_target = True
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = normalized_stop_reason or "manual_stop"
        out_next_action = "manual_review_required"
    elif bool(should_stop):
        status = "final_runtime_continuation_guard_manual_stop"
        continuation_guard_available = True
        continuation_guard_allowed = False
        continuation_guard_block_reason = "blocked_should_stop"
        next_control_target_kind = "manual_stop"
        next_control_target_action = "manual_review_required"
        next_control_target_payload = {
            "target": "manual_stop",
            "source": "prompt211_final_runtime_continuation_guard",
            "stop_reason": normalized_stop_reason or "manual_stop",
            "next_action": "manual_review_required",
        }
        manual_stop_ready = True
        exactly_one_continuation_target = True
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = normalized_stop_reason or "manual_stop"
        out_next_action = "manual_review_required"
    elif bool(should_invoke_codex):
        status = "final_runtime_continuation_guard_blocked"
        continuation_guard_available = True
        continuation_guard_block_reason = "blocked_unexpected_codex_invocation_flag"
        blocked_ready = True
        exactly_one_continuation_target = True
        out_stop_reason = continuation_guard_block_reason
    elif bool(should_execute_rollback):
        status = "final_runtime_continuation_guard_blocked"
        continuation_guard_available = True
        continuation_guard_block_reason = "blocked_unexpected_rollback_execution_flag"
        blocked_ready = True
        exactly_one_continuation_target = True
        out_stop_reason = continuation_guard_block_reason
    elif bool(should_execute_commit):
        status = "final_runtime_continuation_guard_blocked"
        continuation_guard_available = True
        continuation_guard_block_reason = "blocked_unexpected_commit_execution_flag"
        blocked_ready = True
        exactly_one_continuation_target = True
        out_stop_reason = continuation_guard_block_reason
    elif bool(should_push):
        status = "final_runtime_continuation_guard_blocked"
        continuation_guard_available = True
        continuation_guard_block_reason = "blocked_unexpected_push_flag"
        blocked_ready = True
        exactly_one_continuation_target = True
        out_stop_reason = continuation_guard_block_reason
    elif not bool(non_selected_refresh_paths_noop_confirmed):
        status = "final_runtime_continuation_guard_blocked"
        continuation_guard_available = True
        continuation_guard_block_reason = "blocked_non_selected_refresh_paths_not_noop"
        blocked_ready = True
        exactly_one_continuation_target = True
        out_stop_reason = continuation_guard_block_reason
    elif out_cycle_budget_remaining <= 0:
        status = "final_runtime_continuation_guard_blocked"
        continuation_guard_available = True
        continuation_guard_block_reason = "blocked_cycle_budget_exhausted"
        blocked_ready = True
        exactly_one_continuation_target = True
        out_stop_reason = "cycle_budget_exhausted_after_guard"
    elif unsafe_state_detected:
        status = "final_runtime_continuation_guard_blocked"
        continuation_guard_available = True
        continuation_guard_block_reason = "blocked_unsafe_state"
        blocked_ready = True
        exactly_one_continuation_target = True
        out_stop_reason = "unsafe_state_detected"
    elif dirty_state_requires_stop:
        status = "final_runtime_continuation_guard_blocked"
        continuation_guard_available = True
        continuation_guard_block_reason = "blocked_dirty_state"
        blocked_ready = True
        exactly_one_continuation_target = True
        out_stop_reason = "dirty_state_requires_stop"
    elif conflict_requires_stop:
        status = "final_runtime_continuation_guard_blocked_conflict"
        continuation_guard_available = True
        continuation_guard_block_reason = "blocked_conflict_state"
        continuation_conflict_detected = True
        blocked_ready = True
        exactly_one_continuation_target = False
        conflicting_continuation_targets = _normalize_string_list(
            non_stop_candidates + unsupported_non_stop_targets
        )
        out_stop_reason = "conflicting_final_runtime_continuation_targets"
    elif len(non_stop_candidates) > 1:
        status = "final_runtime_continuation_guard_blocked_conflict"
        continuation_guard_available = True
        continuation_guard_block_reason = "blocked_continuation_conflict"
        continuation_conflict_detected = True
        conflicting_continuation_targets = list(non_stop_candidates)
        blocked_ready = True
        out_stop_reason = "conflicting_final_runtime_continuation_targets"
    elif manual_stop_candidate:
        status = "final_runtime_continuation_guard_manual_stop"
        continuation_guard_available = True
        continuation_guard_allowed = False
        continuation_guard_block_reason = ""
        next_control_target_kind = "manual_stop"
        next_control_target_action = "manual_review_required"
        next_control_target_payload = {
            "target": "manual_stop",
            "source": "prompt211_final_runtime_continuation_guard",
            "stop_reason": normalized_stop_reason or "manual_stop",
            "next_action": "manual_review_required",
        }
        manual_stop_ready = True
        exactly_one_continuation_target = True
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = normalized_stop_reason or "manual_stop"
        out_next_action = "manual_review_required"
    elif blocked_candidate:
        status = "final_runtime_continuation_guard_blocked"
        continuation_guard_available = True
        continuation_guard_allowed = False
        continuation_guard_block_reason = (
            normalized_result_block_reason or "final_runtime_continuation_not_safe"
        )
        next_control_target_kind = "blocked"
        next_control_target_action = "manual_review_required"
        next_control_target_payload = {
            "target": "manual_stop",
            "source": "prompt211_final_runtime_continuation_guard",
            "stop_reason": normalized_stop_reason
            or normalized_result_block_reason
            or "final_runtime_continuation_not_safe",
            "next_action": "manual_review_required",
        }
        blocked_ready = True
        exactly_one_continuation_target = True
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = (
            normalized_stop_reason
            or normalized_result_block_reason
            or "final_runtime_continuation_not_safe"
        )
        out_next_action = "manual_review_required"
    elif multi_cycle_handback_candidate:
        status = "final_runtime_continuation_guard_multi_cycle_handback_ready"
        continuation_guard_available = True
        continuation_guard_allowed = True
        continuation_guard_block_reason = ""
        next_control_target_kind = "multi_cycle_controller"
        next_control_target_action = "prepare_next_multi_cycle_decision"
        next_control_target_payload = {
            "target": "multi_cycle_controller",
            "source": "prompt211_final_runtime_continuation_guard",
            "final_step_result_kind": normalized_final_step_result_kind,
            "final_step_result_status": normalized_final_step_result_status,
            "next_action": "prepare_next_multi_cycle_decision",
        }
        multi_cycle_handback_ready = True
        exactly_one_continuation_target = True
        out_should_continue_local_loop = False
        out_should_prepare_next_controller_decision = True
        out_manual_review_required = False
        out_should_stop = False
        out_stop_reason = ""
        out_next_action = "prepare_next_multi_cycle_decision"
    elif not bool(controller_feedback_ready):
        status = "final_runtime_continuation_guard_blocked"
        continuation_guard_available = True
        continuation_guard_allowed = False
        continuation_guard_block_reason = "blocked_controller_feedback_not_ready"
        blocked_ready = True
        exactly_one_continuation_target = True
        out_stop_reason = "controller_feedback_not_ready"
    elif normalized_target_kind != "multi_cycle_controller":
        status = "final_runtime_continuation_guard_blocked"
        continuation_guard_available = True
        continuation_guard_allowed = False
        continuation_guard_block_reason = "blocked_wrong_next_control_target"
        blocked_ready = True
        exactly_one_continuation_target = True
        out_stop_reason = "wrong_next_control_target"
    else:
        status = "final_runtime_continuation_guard_blocked_insufficient_truth"
        continuation_guard_available = False
        continuation_guard_allowed = False
        continuation_guard_block_reason = "blocked_insufficient_final_runtime_continuation_truth"
        blocked_ready = True
        out_stop_reason = "insufficient_final_runtime_continuation_truth"

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if out_next_action not in allowed_next_actions:
        out_next_action = "insufficient_truth"
    if status == "insufficient_truth":
        status = "final_runtime_continuation_guard_blocked_insufficient_truth"
        continuation_guard_available = False
        continuation_guard_allowed = False
        continuation_guard_block_reason = "blocked_insufficient_final_runtime_continuation_truth"
        next_control_target_kind = "blocked"
        next_control_target_action = "manual_review_required"
        next_control_target_payload = {}
        multi_cycle_handback_ready = False
        manual_stop_ready = False
        blocked_ready = True
        exactly_one_continuation_target = False
        continuation_conflict_detected = False
        conflicting_continuation_targets = []
        out_should_continue_local_loop = False
        out_should_prepare_next_controller_decision = False
        out_should_start_unbounded_loop = False
        out_should_invoke_codex = False
        out_should_execute_rollback = False
        out_should_execute_commit = False
        out_should_push = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_final_runtime_continuation_truth"
        out_next_action = "manual_review_required"

    return {
        "project_browser_autonomous_final_runtime_continuation_guard_status": status,
        "project_browser_autonomous_final_runtime_continuation_guard_continuation_guard_available": bool(
            continuation_guard_available
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_continuation_guard_allowed": bool(
            continuation_guard_allowed
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_continuation_guard_block_reason": (
            continuation_guard_block_reason
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_continuation_guard_source": (
            continuation_guard_source
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_next_control_target_kind": (
            next_control_target_kind
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_next_control_target_action": (
            next_control_target_action
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_next_control_target_payload": (
            next_control_target_payload
            if isinstance(next_control_target_payload, Mapping)
            else {}
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_multi_cycle_handback_ready": bool(
            multi_cycle_handback_ready
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_manual_stop_ready": bool(
            manual_stop_ready
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_blocked_ready": bool(
            blocked_ready
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_exactly_one_continuation_target": bool(
            exactly_one_continuation_target
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_continuation_conflict_detected": bool(
            continuation_conflict_detected
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_conflicting_continuation_targets": (
            conflicting_continuation_targets
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_controller_feedback_kind": (
            normalized_controller_feedback_kind
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_final_step_result_kind": (
            normalized_final_step_result_kind
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_final_step_result_status": (
            normalized_final_step_result_status
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_delegated_assimilation_status": (
            normalized_delegated_assimilation_status
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_unsafe_state_detected": bool(
            unsafe_state_detected
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_dirty_state_requires_stop": bool(
            dirty_state_requires_stop
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_conflict_requires_stop": bool(
            conflict_requires_stop
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_budget_guard_checked": bool(
            budget_guard_checked
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_cycle_budget_remaining": int(
            out_cycle_budget_remaining
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_codex_budget_remaining": int(
            out_codex_budget_remaining
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_rollback_budget_remaining": int(
            out_rollback_budget_remaining
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_commit_budget_remaining": int(
            out_commit_budget_remaining
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_should_continue_local_loop": bool(
            out_should_continue_local_loop
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_should_prepare_next_controller_decision": bool(
            out_should_prepare_next_controller_decision
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_should_start_unbounded_loop": bool(
            out_should_start_unbounded_loop
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_should_invoke_codex": bool(
            out_should_invoke_codex
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_should_execute_rollback": bool(
            out_should_execute_rollback
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_should_execute_commit": bool(
            out_should_execute_commit
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_should_push": bool(
            out_should_push
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_manual_review_required": bool(
            out_manual_review_required
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_should_stop": bool(
            out_should_stop
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_stop_reason": (
            out_stop_reason
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_next_action": (
            out_next_action
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_final_runtime_continuation_guard_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_assimilation_status,
                    normalized_result_class,
                    normalized_result_block_reason,
                    normalized_source_selected_kind,
                    normalized_source_selected_action,
                    normalized_source_refresh_status,
                    normalized_delegated_assimilation_status,
                    normalized_controller_feedback_kind,
                    normalized_controller_feedback_source,
                    normalized_final_step_result_kind,
                    normalized_final_step_result_status,
                    normalized_target_kind,
                    normalized_target_action,
                    normalized_stop_reason,
                    normalized_next_action,
                    normalized_control_dispatch_refresh_status,
                    normalized_control_contract_dispatch_status,
                    normalized_bounded_local_control_decision_status,
                    normalized_next_step_launch_result_assimilation_status,
                    normalized_reentry_result_assimilation_status,
                    normalized_rollback_result_assimilation_status,
                    normalized_commit_result_assimilation_status,
                    normalized_multi_cycle_controller_status,
                    "authoritative_prompt210_missing" if not authoritative_selected else "",
                    "cycle_budget_exhausted" if out_cycle_budget_remaining <= 0 else "",
                    "non_selected_refresh_paths_not_noop"
                    if not bool(non_selected_refresh_paths_noop_confirmed)
                    else "",
                ]
            )
        ),
    }

def _build_project_browser_autonomous_stale_fresh_ordering_gate_state(
    *,
    one_bounded_continuation_coordinator_status: str,
    coordinator_available: bool,
    coordinator_allowed: bool,
    coordinator_block_reason: str,
    coordinator_source: str,
    handback_kind: str,
    handback_action: str,
    handback_payload: Any,
    one_bounded_step_ready: bool,
    one_bounded_step_allowed: bool,
    one_bounded_step_contract: Any,
    multi_cycle_controller_handback_ready: bool,
    manual_stop_handback_ready: bool,
    blocked_handback_ready: bool,
    exactly_one_handback_target: bool,
    handback_conflict_detected: bool,
    conflicting_handback_targets: Sequence[Any],
    budget_checked: bool,
    cycle_budget_remaining: int,
    codex_budget_remaining: int,
    rollback_budget_remaining: int,
    commit_budget_remaining: int,
    stale_state_check_required_next: bool,
    fresh_execution_ordering_required_next: bool,
    should_continue_local_loop: bool,
    should_start_unbounded_loop: bool,
    should_prepare_next_controller_decision: bool,
    should_invoke_codex: bool,
    should_execute_rollback: bool,
    should_execute_commit: bool,
    should_push: bool,
    manual_review_required: bool,
    should_stop: bool,
    stop_reason: str,
    next_action: str,
    final_runtime_continuation_guard_status: str,
    control_dispatch_refresh_result_assimilation_status: str,
    multi_cycle_controller_status: str,
    multi_cycle_controller_next_action: str,
    terminal_lane_decision_status: str,
    lane_contract_guard_status: str,
    guarded_lane_dispatch_status: str,
    next_step_launch_contract_status: str,
    next_step_launch_execution_status: str,
    next_step_launch_result_assimilation_status: str,
) -> dict[str, Any]:
    allowed_statuses = {
        "stale_fresh_ordering_gate_retrigger_ready",
        "stale_fresh_ordering_gate_manual_stop",
        "stale_fresh_ordering_gate_blocked",
        "stale_fresh_ordering_gate_blocked_stale_state",
        "stale_fresh_ordering_gate_blocked_conflict",
        "stale_fresh_ordering_gate_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "prepare_direct_retrigger",
        "manual_review_required",
        "insufficient_truth",
    }
    runtime_posture = [
        "prompt213_stale_fresh_ordering_gate",
        "metadata_only",
        "stale_state_and_fresh_ordering_verification",
        "direct_retrigger_preflight_only",
        "no_execution",
        "no_unbounded_loop",
        "no_codex_invocation",
        "no_git_mutation",
        "no_push",
    ]

    normalized_coordinator_status = _normalize_text(
        one_bounded_continuation_coordinator_status,
        default="insufficient_truth",
    )
    normalized_coordinator_block_reason = _normalize_text(coordinator_block_reason, default="")
    normalized_coordinator_source = _normalize_text(coordinator_source, default="")
    normalized_handback_kind = _normalize_text(handback_kind, default="")
    normalized_handback_action = _normalize_text(handback_action, default="")
    normalized_stop_reason = _normalize_text(stop_reason, default="")
    normalized_next_action = _normalize_text(next_action, default="manual_review_required")
    normalized_guard_status = _normalize_text(
        final_runtime_continuation_guard_status,
        default="insufficient_truth",
    )
    normalized_refresh_result_assimilation_status = _normalize_text(
        control_dispatch_refresh_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_multi_cycle_controller_status = _normalize_text(
        multi_cycle_controller_status,
        default="insufficient_truth",
    )
    normalized_multi_cycle_controller_next_action = _normalize_text(
        multi_cycle_controller_next_action,
        default="",
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
    normalized_handback_payload = dict(handback_payload) if isinstance(handback_payload, Mapping) else {}
    normalized_one_bounded_step_contract = (
        dict(one_bounded_step_contract) if isinstance(one_bounded_step_contract, Mapping) else {}
    )
    normalized_conflicting_handback_targets = _normalize_string_list(conflicting_handback_targets)

    out_cycle_budget_remaining = _as_non_negative_int(cycle_budget_remaining, default=0)
    out_codex_budget_remaining = _as_non_negative_int(codex_budget_remaining, default=0)
    out_rollback_budget_remaining = _as_non_negative_int(rollback_budget_remaining, default=0)
    out_commit_budget_remaining = _as_non_negative_int(commit_budget_remaining, default=0)
    out_budget_checked = bool(budget_checked)

    contract_kind = _normalize_text(
        normalized_one_bounded_step_contract.get("contract_kind"),
        default="",
    )
    contract_handback_kind = _normalize_text(
        normalized_one_bounded_step_contract.get("handback_kind"),
        default="",
    )
    contract_handback_action = _normalize_text(
        normalized_one_bounded_step_contract.get("handback_action"),
        default="",
    )
    max_next_steps = _as_non_negative_int(
        normalized_one_bounded_step_contract.get("max_next_steps"),
        default=0,
    )
    allow_unbounded_loop = bool(
        normalized_one_bounded_step_contract.get("allow_unbounded_loop", True)
    )
    stale_state_check_required = bool(
        normalized_one_bounded_step_contract.get("requires_stale_state_check", False)
    )
    fresh_execution_ordering_required = bool(
        normalized_one_bounded_step_contract.get(
            "requires_fresh_execution_ordering_guard",
            False,
        )
    )

    authoritative_selected = bool(
        bool(normalized_coordinator_status)
        and (
            bool(coordinator_available)
            or normalized_coordinator_status
            in {
                "one_bounded_continuation_coordinator_manual_stop",
                "one_bounded_continuation_coordinator_blocked",
                "one_bounded_continuation_coordinator_blocked_insufficient_truth",
            }
        )
        and (
            bool(normalized_handback_kind)
            or normalized_coordinator_status
            in {
                "one_bounded_continuation_coordinator_manual_stop",
                "one_bounded_continuation_coordinator_blocked",
                "one_bounded_continuation_coordinator_blocked_insufficient_truth",
            }
        )
        and (
            normalized_handback_kind != "multi_cycle_controller"
            or isinstance(normalized_one_bounded_step_contract, Mapping)
        )
    )

    one_bounded_step_contract_valid = bool(
        bool(one_bounded_step_allowed)
        and bool(one_bounded_step_ready)
        and normalized_handback_kind == "multi_cycle_controller"
        and normalized_handback_action == "prepare_next_multi_cycle_decision"
        and isinstance(normalized_one_bounded_step_contract, Mapping)
        and contract_kind == "one_bounded_local_continuation"
        and max_next_steps == 1
        and not allow_unbounded_loop
        and stale_state_check_required
        and fresh_execution_ordering_required
        and bool(should_continue_local_loop)
        and not bool(should_start_unbounded_loop)
        and not bool(manual_review_required)
        and not bool(should_stop)
    )

    stale_state_detected = False
    stale_state_reason = ""
    stale_state_source = ""
    if not normalized_coordinator_source:
        stale_state_detected = True
        stale_state_reason = "missing_prompt212_source_status"
        stale_state_source = "prompt212_one_bounded_continuation_coordinator"
    elif not isinstance(normalized_one_bounded_step_contract, Mapping) or not normalized_one_bounded_step_contract:
        stale_state_detected = True
        stale_state_reason = "missing_one_bounded_step_contract"
        stale_state_source = "prompt212_one_bounded_continuation_coordinator"
    elif not normalized_multi_cycle_controller_status:
        stale_state_detected = True
        stale_state_reason = "missing_multi_cycle_controller_status"
        stale_state_source = "prompt197_multi_cycle_controller"
    elif normalized_coordinator_source != "prompt211_final_runtime_continuation_guard":
        stale_state_detected = True
        stale_state_reason = "mismatched_prompt212_source_marker"
        stale_state_source = "prompt212_one_bounded_continuation_coordinator"
    elif normalized_guard_status in {
        "final_runtime_continuation_guard_manual_stop",
        "final_runtime_continuation_guard_blocked",
        "final_runtime_continuation_guard_blocked_conflict",
        "final_runtime_continuation_guard_blocked_insufficient_truth",
    }:
        stale_state_detected = True
        stale_state_reason = "upstream_guard_blocked_or_manual_stop"
        stale_state_source = "prompt211_final_runtime_continuation_guard"
    elif normalized_refresh_result_assimilation_status in {
        "control_dispatch_refresh_result_manual_stop",
        "control_dispatch_refresh_result_failed",
        "control_dispatch_refresh_result_blocked",
        "control_dispatch_refresh_result_blocked_non_selected_refresh_activity",
        "control_dispatch_refresh_result_blocked_insufficient_truth",
    }:
        stale_state_detected = True
        stale_state_reason = "upstream_refresh_result_blocked_or_manual_stop"
        stale_state_source = "prompt210_control_dispatch_refresh_result_assimilation"
    elif (
        normalized_handback_kind != "manual_stop"
        and normalized_handback_kind != "blocked"
        and normalized_handback_kind != "multi_cycle_controller"
    ):
        stale_state_detected = True
        stale_state_reason = "conflicting_current_handback_kind"
        stale_state_source = "prompt212_one_bounded_continuation_coordinator"
    elif (
        out_cycle_budget_remaining < 0
        or out_codex_budget_remaining < 0
        or out_rollback_budget_remaining < 0
        or out_commit_budget_remaining < 0
    ):
        stale_state_detected = True
        stale_state_reason = "invalid_negative_budget_values"
        stale_state_source = "prompt197_multi_cycle_controller"
    elif out_cycle_budget_remaining <= 0:
        stale_state_detected = True
        stale_state_reason = "cycle_budget_exhausted"
        stale_state_source = "prompt197_multi_cycle_controller"

    fresh_execution_required = bool(
        one_bounded_step_contract_valid
        and bool(stale_state_check_required_next)
        and bool(fresh_execution_ordering_required_next)
        and not bool(manual_stop_handback_ready)
        and not bool(blocked_handback_ready)
        and not bool(manual_review_required)
        and not bool(should_stop)
    )
    fresh_execution_allowed = False
    fresh_execution_block_reason = ""
    reuse_existing_state_allowed = False
    reuse_existing_state_block_reason = ""

    commit_retrigger_candidate = bool(
        normalized_multi_cycle_controller_next_action == "prepare_commit_tag_readiness"
        and out_commit_budget_remaining > 0
    )
    rollback_retrigger_candidate = bool(
        normalized_multi_cycle_controller_next_action == "prepare_rollback_readiness"
        and out_rollback_budget_remaining > 0
    )
    codex_retrigger_candidate = bool(
        normalized_next_step_launch_contract_status
        == "next_step_launch_contract_generated_prompt_reentry_ready"
        and out_codex_budget_remaining > 0
    )
    fix_prompt_retrigger_candidate = bool(
        normalized_multi_cycle_controller_next_action == "generate_fix_prompt"
        and out_codex_budget_remaining > 0
    )
    next_prompt_retrigger_candidate = bool(
        normalized_multi_cycle_controller_next_action == "generate_next_prompt"
        and out_codex_budget_remaining > 0
    )
    manual_stop_candidate = bool(
        bool(manual_stop_handback_ready)
        or bool(manual_review_required)
        or bool(should_stop)
    )
    blocked_candidate = bool(
        bool(blocked_handback_ready)
        or stale_state_detected
        or not out_budget_checked
        or out_cycle_budget_remaining <= 0
        or bool(handback_conflict_detected)
        or bool(should_start_unbounded_loop)
        or bool(should_invoke_codex)
        or bool(should_execute_rollback)
        or bool(should_execute_commit)
        or bool(should_push)
    )

    non_stop_candidates: list[str] = []
    if commit_retrigger_candidate:
        non_stop_candidates.append("commit_retrigger_candidate")
    if rollback_retrigger_candidate:
        non_stop_candidates.append("rollback_retrigger_candidate")
    if codex_retrigger_candidate:
        non_stop_candidates.append("codex_retrigger_candidate")
    if fix_prompt_retrigger_candidate:
        non_stop_candidates.append("fix_prompt_retrigger_candidate")
    if next_prompt_retrigger_candidate:
        non_stop_candidates.append("next_prompt_retrigger_candidate")
    non_stop_candidates = sorted(non_stop_candidates)

    selected_retrigger_kind = "blocked"
    selected_retrigger_action = "manual_review_required"
    selected_retrigger_source = ""

    status = "stale_fresh_ordering_gate_blocked_insufficient_truth"
    ordering_gate_available = False
    ordering_gate_allowed = False
    ordering_gate_block_reason = "blocked_insufficient_stale_fresh_ordering_truth"
    ordering_gate_source = "prompt212_one_bounded_continuation_coordinator"
    fresh_execution_required_out = bool(fresh_execution_required)
    exact_one_retrigger_candidate = False
    retrigger_conflict_detected = False
    conflicting_retrigger_candidates: list[str] = []
    out_should_continue_local_loop = False
    out_should_start_unbounded_loop = False
    out_should_prepare_next_controller_decision = False
    out_should_invoke_codex = False
    out_should_execute_rollback = False
    out_should_execute_commit = False
    out_should_push = False
    out_manual_review_required = True
    out_should_stop = True
    out_stop_reason = normalized_stop_reason or "insufficient_stale_fresh_ordering_truth"
    out_next_action = "manual_review_required"
    prompt214_retrigger_ready = False
    prompt214_retrigger_source = ""
    prompt214_retrigger_contract: dict[str, Any] = {}

    if not authoritative_selected:
        status = "stale_fresh_ordering_gate_blocked_insufficient_truth"
        ordering_gate_available = False
        ordering_gate_allowed = False
        ordering_gate_block_reason = "blocked_insufficient_stale_fresh_ordering_truth"
    elif manual_stop_candidate:
        status = "stale_fresh_ordering_gate_manual_stop"
        ordering_gate_available = True
        ordering_gate_allowed = False
        ordering_gate_block_reason = "blocked_manual_review_required"
        selected_retrigger_kind = "manual_stop"
        selected_retrigger_action = "manual_review_required"
        selected_retrigger_source = "prompt212_one_bounded_continuation_coordinator"
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = normalized_stop_reason or "manual_stop"
        out_next_action = "manual_review_required"
        reuse_existing_state_allowed = False
        reuse_existing_state_block_reason = "manual_stop_selected"
    else:
        if not one_bounded_step_contract_valid:
            ordering_gate_block_reason = "blocked_one_bounded_contract_invalid"
        elif stale_state_detected:
            ordering_gate_block_reason = "blocked_stale_state_detected"
        elif bool(manual_review_required):
            ordering_gate_block_reason = "blocked_manual_review_required"
        elif bool(should_stop):
            ordering_gate_block_reason = "blocked_should_stop"
        elif not out_budget_checked:
            ordering_gate_block_reason = "blocked_budget_not_checked"
        elif out_cycle_budget_remaining <= 0:
            ordering_gate_block_reason = "blocked_cycle_budget_exhausted"
        elif out_codex_budget_remaining <= 0 and (
            codex_retrigger_candidate or fix_prompt_retrigger_candidate or next_prompt_retrigger_candidate
        ):
            ordering_gate_block_reason = "blocked_codex_budget_exhausted"
        elif out_rollback_budget_remaining <= 0 and rollback_retrigger_candidate:
            ordering_gate_block_reason = "blocked_rollback_budget_exhausted"
        elif out_commit_budget_remaining <= 0 and commit_retrigger_candidate:
            ordering_gate_block_reason = "blocked_commit_budget_exhausted"
        elif bool(should_start_unbounded_loop):
            ordering_gate_block_reason = "blocked_unexpected_unbounded_loop_flag"
        elif bool(should_invoke_codex):
            ordering_gate_block_reason = "blocked_unexpected_codex_invocation_flag"
        elif bool(should_execute_rollback):
            ordering_gate_block_reason = "blocked_unexpected_rollback_execution_flag"
        elif bool(should_execute_commit):
            ordering_gate_block_reason = "blocked_unexpected_commit_execution_flag"
        elif bool(should_push):
            ordering_gate_block_reason = "blocked_unexpected_push_flag"
        elif bool(handback_conflict_detected):
            ordering_gate_block_reason = "blocked_retrigger_conflict"

        if len(non_stop_candidates) > 1:
            retrigger_conflict_detected = True
            conflicting_retrigger_candidates = list(non_stop_candidates)
            ordering_gate_block_reason = "blocked_retrigger_conflict"

        if not non_stop_candidates and not ordering_gate_block_reason:
            ordering_gate_block_reason = "blocked_no_retrigger_candidate"

        if ordering_gate_block_reason:
            status = (
                "stale_fresh_ordering_gate_blocked_stale_state"
                if ordering_gate_block_reason == "blocked_stale_state_detected"
                else "stale_fresh_ordering_gate_blocked_conflict"
                if ordering_gate_block_reason == "blocked_retrigger_conflict"
                else "stale_fresh_ordering_gate_blocked"
            )
            ordering_gate_available = True
            ordering_gate_allowed = False
            selected_retrigger_kind = "blocked"
            selected_retrigger_action = "manual_review_required"
            selected_retrigger_source = "prompt213_stale_fresh_ordering_gate"
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = ordering_gate_block_reason
            out_next_action = "manual_review_required"
            fresh_execution_allowed = False
            fresh_execution_block_reason = ordering_gate_block_reason
            reuse_existing_state_allowed = False
            reuse_existing_state_block_reason = ordering_gate_block_reason
        else:
            exact_one_retrigger_candidate = len(non_stop_candidates) == 1
            if non_stop_candidates:
                selected_retrigger_kind = non_stop_candidates[0].replace("_candidate", "")
                selected_retrigger_action = {
                    "commit_retrigger": "retrigger_commit_path",
                    "rollback_retrigger": "retrigger_rollback_path",
                    "codex_retrigger": "retrigger_codex_reentry_path",
                    "fix_prompt_retrigger": "retrigger_fix_prompt_path",
                    "next_prompt_retrigger": "retrigger_next_prompt_path",
                }.get(selected_retrigger_kind, "manual_review_required")
                selected_retrigger_source = "multi_cycle_controller"

            fresh_execution_allowed = bool(
                fresh_execution_required
                and not stale_state_detected
                and exact_one_retrigger_candidate
                and not retrigger_conflict_detected
                and out_budget_checked
                and out_cycle_budget_remaining > 0
                and not bool(should_start_unbounded_loop)
                and not bool(should_invoke_codex)
                and not bool(should_execute_rollback)
                and not bool(should_execute_commit)
                and not bool(should_push)
                and not bool(manual_review_required)
                and not bool(should_stop)
            )
            if fresh_execution_allowed:
                status = "stale_fresh_ordering_gate_retrigger_ready"
                ordering_gate_available = True
                ordering_gate_allowed = True
                ordering_gate_block_reason = ""
                out_manual_review_required = False
                out_should_stop = False
                out_stop_reason = ""
                out_next_action = "prepare_direct_retrigger"
                prompt214_retrigger_ready = True
                prompt214_retrigger_source = "prompt213_stale_fresh_ordering_gate"
                prompt214_retrigger_contract = {
                    "contract_kind": "direct_retrigger_preflight",
                    "source": "prompt213_stale_fresh_ordering_gate",
                    "selected_retrigger_kind": selected_retrigger_kind,
                    "selected_retrigger_action": selected_retrigger_action,
                    "max_retrigger_attempts": 1,
                    "allow_unbounded_loop": False,
                    "allow_retry": False,
                    "requires_existing_bounded_path": True,
                    "requires_result_handoff": True,
                    "cycle_budget_remaining": out_cycle_budget_remaining,
                    "codex_budget_remaining": out_codex_budget_remaining,
                    "rollback_budget_remaining": out_rollback_budget_remaining,
                    "commit_budget_remaining": out_commit_budget_remaining,
                    "next_action": "prepare_direct_retrigger",
                }
                fresh_execution_block_reason = ""
                reuse_existing_state_allowed = False
                reuse_existing_state_block_reason = "fresh_execution_required"
            else:
                status = "stale_fresh_ordering_gate_blocked"
                ordering_gate_available = True
                ordering_gate_allowed = False
                ordering_gate_block_reason = (
                    ordering_gate_block_reason
                    or "blocked_insufficient_stale_fresh_ordering_truth"
                )
                out_manual_review_required = True
                out_should_stop = True
                out_stop_reason = ordering_gate_block_reason
                out_next_action = "manual_review_required"
                fresh_execution_block_reason = ordering_gate_block_reason
                reuse_existing_state_allowed = False
                reuse_existing_state_block_reason = ordering_gate_block_reason

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if out_next_action not in allowed_next_actions:
        out_next_action = "insufficient_truth"
    if status == "insufficient_truth":
        status = "stale_fresh_ordering_gate_blocked_insufficient_truth"
        ordering_gate_available = False
        ordering_gate_allowed = False
        ordering_gate_block_reason = "blocked_insufficient_stale_fresh_ordering_truth"
        one_bounded_step_contract_valid = False
        stale_state_detected = True
        stale_state_reason = "insufficient_truth"
        stale_state_source = "prompt213_stale_fresh_ordering_gate"
        fresh_execution_required_out = False
        fresh_execution_allowed = False
        fresh_execution_block_reason = "blocked_insufficient_stale_fresh_ordering_truth"
        reuse_existing_state_allowed = False
        reuse_existing_state_block_reason = "blocked_insufficient_stale_fresh_ordering_truth"
        selected_retrigger_kind = "blocked"
        selected_retrigger_action = "manual_review_required"
        selected_retrigger_source = ""
        exact_one_retrigger_candidate = False
        retrigger_conflict_detected = False
        conflicting_retrigger_candidates = []
        prompt214_retrigger_ready = False
        prompt214_retrigger_source = ""
        prompt214_retrigger_contract = {}
        out_should_continue_local_loop = False
        out_should_start_unbounded_loop = False
        out_should_prepare_next_controller_decision = False
        out_should_invoke_codex = False
        out_should_execute_rollback = False
        out_should_execute_commit = False
        out_should_push = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_stale_fresh_ordering_truth"
        out_next_action = "manual_review_required"

    return {
        "project_browser_autonomous_stale_fresh_ordering_gate_status": status,
        "project_browser_autonomous_stale_fresh_ordering_gate_ordering_gate_available": bool(
            ordering_gate_available
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_ordering_gate_allowed": bool(
            ordering_gate_allowed
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_ordering_gate_block_reason": (
            ordering_gate_block_reason
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_ordering_gate_source": (
            ordering_gate_source
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_one_bounded_step_contract_valid": bool(
            one_bounded_step_contract_valid
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_handback_kind": (
            normalized_handback_kind
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_handback_action": (
            normalized_handback_action
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_max_next_steps": int(
            max_next_steps
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_allow_unbounded_loop": bool(
            allow_unbounded_loop
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_stale_state_check_required": bool(
            stale_state_check_required
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_fresh_execution_ordering_required": bool(
            fresh_execution_ordering_required
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_stale_state_detected": bool(
            stale_state_detected
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_stale_state_reason": (
            stale_state_reason
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_stale_state_source": (
            stale_state_source
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_fresh_execution_required": bool(
            fresh_execution_required_out
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_fresh_execution_allowed": bool(
            fresh_execution_allowed
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_fresh_execution_block_reason": (
            fresh_execution_block_reason
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_reuse_existing_state_allowed": bool(
            reuse_existing_state_allowed
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_reuse_existing_state_block_reason": (
            reuse_existing_state_block_reason
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_selected_retrigger_kind": (
            selected_retrigger_kind
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_selected_retrigger_action": (
            selected_retrigger_action
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_selected_retrigger_source": (
            selected_retrigger_source
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_exactly_one_retrigger_candidate": bool(
            exact_one_retrigger_candidate
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_retrigger_conflict_detected": bool(
            retrigger_conflict_detected
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_conflicting_retrigger_candidates": (
            conflicting_retrigger_candidates
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_codex_retrigger_candidate": bool(
            codex_retrigger_candidate
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_rollback_retrigger_candidate": bool(
            rollback_retrigger_candidate
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_commit_retrigger_candidate": bool(
            commit_retrigger_candidate
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_next_prompt_retrigger_candidate": bool(
            next_prompt_retrigger_candidate
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_fix_prompt_retrigger_candidate": bool(
            fix_prompt_retrigger_candidate
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_manual_stop_candidate": bool(
            manual_stop_candidate
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_blocked_candidate": bool(
            blocked_candidate
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_cycle_budget_remaining": int(
            out_cycle_budget_remaining
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_codex_budget_remaining": int(
            out_codex_budget_remaining
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_rollback_budget_remaining": int(
            out_rollback_budget_remaining
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_commit_budget_remaining": int(
            out_commit_budget_remaining
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_budget_checked": bool(
            out_budget_checked
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_should_continue_local_loop": bool(
            out_should_continue_local_loop
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_should_start_unbounded_loop": bool(
            out_should_start_unbounded_loop
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_should_prepare_next_controller_decision": bool(
            out_should_prepare_next_controller_decision
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_should_invoke_codex": bool(
            out_should_invoke_codex
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_should_execute_rollback": bool(
            out_should_execute_rollback
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_should_execute_commit": bool(
            out_should_execute_commit
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_should_push": bool(
            out_should_push
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_manual_review_required": bool(
            out_manual_review_required
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_should_stop": bool(
            out_should_stop
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_stop_reason": (
            out_stop_reason
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_next_action": (
            out_next_action
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_prompt214_retrigger_ready": bool(
            prompt214_retrigger_ready
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_prompt214_retrigger_source": (
            prompt214_retrigger_source
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_prompt214_retrigger_contract": (
            prompt214_retrigger_contract
            if isinstance(prompt214_retrigger_contract, Mapping)
            else {}
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_stale_fresh_ordering_gate_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_coordinator_status,
                    normalized_coordinator_block_reason,
                    normalized_coordinator_source,
                    normalized_handback_kind,
                    normalized_handback_action,
                    normalized_stop_reason,
                    normalized_next_action,
                    normalized_guard_status,
                    normalized_refresh_result_assimilation_status,
                    normalized_multi_cycle_controller_status,
                    normalized_multi_cycle_controller_next_action,
                    normalized_terminal_lane_decision_status,
                    normalized_lane_contract_guard_status,
                    normalized_guarded_lane_dispatch_status,
                    normalized_next_step_launch_contract_status,
                    normalized_next_step_launch_execution_status,
                    normalized_next_step_launch_result_assimilation_status,
                    "authoritative_prompt212_missing" if not authoritative_selected else "",
                    "stale_state_detected" if stale_state_detected else "",
                    "retrigger_conflict_detected" if retrigger_conflict_detected else "",
                ]
            )
        ),
    }

def _build_project_browser_autonomous_direct_retrigger_followup_guard_state(
    *,
    direct_retrigger_result_assimilation_status: str,
    result_selected: bool,
    result_available: bool,
    result_class: str,
    result_block_reason: str,
    source_selected_retrigger_kind: str,
    source_selected_retrigger_action: str,
    source_retrigger_status: str,
    source_retrigger_attempted: bool,
    source_retrigger_completed: bool,
    source_retrigger_failed: bool,
    non_selected_retriggers_noop_confirmed: bool,
    delegated_existing_path_kind: str,
    delegated_existing_status: str,
    delegated_existing_next_action: str,
    fresh_attempt_detected: bool,
    existing_truth_surface_detected: bool,
    stale_truth_only_detected: bool,
    callable_existing_path_detected: bool,
    existing_path_not_callable_detected: bool,
    terminal_result_detected: bool,
    terminal_result_source: str,
    controller_feedback_ready: bool,
    controller_feedback_kind: str,
    controller_feedback_source: str,
    controller_feedback_payload: Any,
    next_bounded_control_target_ready: bool,
    next_bounded_control_target_kind: str,
    next_bounded_control_target_action: str,
    next_bounded_control_target_payload: Any,
    should_prepare_result_assimilation_chain: bool,
    should_prepare_next_controller_decision: bool,
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
    cycle_budget_remaining: int,
    codex_budget_remaining: int,
    rollback_budget_remaining: int,
    commit_budget_remaining: int,
    budget_checked: bool,
    direct_retrigger_coordinator_status: str,
    stale_fresh_ordering_gate_status: str,
    one_bounded_continuation_coordinator_status: str,
    final_runtime_continuation_guard_status: str,
    multi_cycle_controller_status: str,
    codex_reentry_invocation_status: str,
    rollback_execution_status: str,
    commit_tag_execution_status: str,
    fix_prompt_generation_status: str,
    next_prompt_generation_status: str,
) -> dict[str, Any]:
    allowed_statuses = {
        "direct_retrigger_followup_guard_multistep_ready",
        "direct_retrigger_followup_guard_result_assimilation_ready",
        "direct_retrigger_followup_guard_manual_stop",
        "direct_retrigger_followup_guard_blocked",
        "direct_retrigger_followup_guard_blocked_conflict",
        "direct_retrigger_followup_guard_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "prepare_bounded_multi_step_coordinator",
        "prepare_result_assimilation_chain",
        "manual_review_required",
        "insufficient_truth",
    }
    runtime_posture = [
        "prompt216_direct_retrigger_followup_guard",
        "metadata_only",
        "followup_contract_selection_only",
        "exactly_one_followup_target",
        "no_execution",
        "no_retry",
        "no_loop",
        "no_push",
        "no_github_mutation",
    ]

    normalized_status = _normalize_text(
        direct_retrigger_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_result_class = _normalize_text(result_class, default="")
    normalized_result_block_reason = _normalize_text(result_block_reason, default="")
    normalized_source_kind = _normalize_text(source_selected_retrigger_kind, default="")
    normalized_source_action = _normalize_text(source_selected_retrigger_action, default="")
    normalized_source_retrigger_status = _normalize_text(source_retrigger_status, default="")
    normalized_delegated_kind = _normalize_text(delegated_existing_path_kind, default="")
    normalized_delegated_status = _normalize_text(delegated_existing_status, default="")
    normalized_delegated_next_action = _normalize_text(
        delegated_existing_next_action,
        default="",
    )
    normalized_terminal_result_source = _normalize_text(terminal_result_source, default="")
    normalized_feedback_kind = _normalize_text(controller_feedback_kind, default="")
    normalized_feedback_source = _normalize_text(controller_feedback_source, default="")
    normalized_next_target_kind = _normalize_text(next_bounded_control_target_kind, default="")
    normalized_next_target_action = _normalize_text(
        next_bounded_control_target_action,
        default="",
    )
    normalized_stop_reason = _normalize_text(stop_reason, default="")
    normalized_next_action = _normalize_text(next_action, default="manual_review_required")
    normalized_coordinator_status = _normalize_text(
        direct_retrigger_coordinator_status,
        default="insufficient_truth",
    )
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
    normalized_rollback_execution_status = _normalize_text(
        rollback_execution_status,
        default="insufficient_truth",
    )
    normalized_commit_execution_status = _normalize_text(
        commit_tag_execution_status,
        default="insufficient_truth",
    )
    normalized_fix_generation_status = _normalize_text(
        fix_prompt_generation_status,
        default="insufficient_truth",
    )
    normalized_next_generation_status = _normalize_text(
        next_prompt_generation_status,
        default="insufficient_truth",
    )

    normalized_feedback_payload = (
        dict(controller_feedback_payload)
        if isinstance(controller_feedback_payload, Mapping)
        else {}
    )
    normalized_next_target_payload = (
        dict(next_bounded_control_target_payload)
        if isinstance(next_bounded_control_target_payload, Mapping)
        else {}
    )

    out_cycle_budget_remaining = _as_non_negative_int(cycle_budget_remaining, default=0)
    out_codex_budget_remaining = _as_non_negative_int(codex_budget_remaining, default=0)
    out_rollback_budget_remaining = _as_non_negative_int(rollback_budget_remaining, default=0)
    out_commit_budget_remaining = _as_non_negative_int(commit_budget_remaining, default=0)
    out_budget_checked = bool(budget_checked)

    source_status_indicates_manual = normalized_status == "direct_retrigger_result_manual_stop"
    source_status_indicates_blocked = "blocked" in normalized_status
    source_status_indicates_failed = normalized_status == "direct_retrigger_result_failed"
    source_status_indicates_insufficient = normalized_status in {
        "direct_retrigger_result_blocked_insufficient_truth",
        "insufficient_truth",
    }

    authoritative_selected = bool(
        bool(normalized_status)
        and bool(normalized_result_class)
        and (
            normalized_feedback_source == "prompt214_direct_retrigger_coordinator"
            or source_status_indicates_manual
            or source_status_indicates_blocked
            or source_status_indicates_failed
            or source_status_indicates_insufficient
        )
        and (
            bool(normalized_source_kind)
            or source_status_indicates_manual
            or source_status_indicates_blocked
            or source_status_indicates_failed
            or source_status_indicates_insufficient
        )
    )

    result_assimilation_chain_candidate = bool(
        normalized_result_class
        in {"completed_fresh_attempt", "completed_existing_truth_surface"}
        and bool(terminal_result_detected)
        and bool(should_prepare_result_assimilation_chain)
        and bool(controller_feedback_ready)
        and bool(non_selected_retriggers_noop_confirmed)
        and not bool(manual_review_required)
        and not bool(should_stop)
        and not bool(should_start_unbounded_loop)
        and not bool(should_push)
    )
    bounded_multi_step_candidate = bool(
        result_assimilation_chain_candidate
        and bool(next_bounded_control_target_ready)
        and normalized_next_target_kind == "direct_retrigger_result_followup"
        and normalized_next_target_action == "prepare_result_followup"
        and normalized_result_class
        in {"completed_fresh_attempt", "completed_existing_truth_surface"}
        and bool(normalized_source_kind)
        and bool(terminal_result_detected)
    )
    manual_stop_candidate = bool(
        normalized_result_class == "manual_stop"
        or bool(manual_review_required)
        or bool(should_stop)
        or source_status_indicates_manual
    )
    blocked_candidate = bool(
        normalized_result_class
        in {
            "blocked_stale_truth_only",
            "blocked_existing_path_not_callable",
            "blocked_non_selected_retrigger_activity",
            "failed",
            "blocked",
            "insufficient_truth",
        }
        or bool(stale_truth_only_detected)
        or bool(existing_path_not_callable_detected)
        or source_status_indicates_blocked
        or source_status_indicates_failed
        or source_status_indicates_insufficient
    )

    status = "direct_retrigger_followup_guard_blocked_insufficient_truth"
    followup_guard_available = False
    followup_guard_allowed = False
    followup_guard_block_reason = "blocked_insufficient_direct_retrigger_followup_truth"
    followup_guard_source = "prompt215_direct_retrigger_result_assimilation"
    selected_followup_kind = "blocked"
    selected_followup_action = "manual_review_required"
    selected_followup_payload: dict[str, Any] = {}
    exactly_one_followup_target = False
    followup_conflict_detected = False
    conflicting_followup_targets: list[str] = []
    continue_to_result_assimilation_chain = False
    continue_to_bounded_multi_step_coordinator = False
    manual_stop_followup = False
    blocked_followup = True
    fresh_attempt_followup_allowed = False
    existing_truth_followup_allowed = False
    stale_truth_followup_blocked = bool(stale_truth_only_detected)
    not_callable_followup_blocked = bool(existing_path_not_callable_detected)
    out_should_continue_local_loop = False
    out_should_start_unbounded_loop = False
    out_should_prepare_result_assimilation_chain = False
    out_should_prepare_next_controller_decision = False
    out_should_invoke_codex = False
    out_should_execute_rollback = False
    out_should_execute_commit = False
    out_should_push = False
    out_manual_review_required = True
    out_should_stop = True
    out_stop_reason = normalized_stop_reason or "insufficient_direct_retrigger_followup_truth"
    out_next_action = "manual_review_required"
    prompt217_multistep_ready = False
    prompt217_multistep_source = ""
    prompt217_multistep_contract: dict[str, Any] = {}

    if not authoritative_selected:
        status = "direct_retrigger_followup_guard_blocked_insufficient_truth"
        followup_guard_available = False
        followup_guard_allowed = False
        followup_guard_block_reason = "blocked_insufficient_direct_retrigger_followup_truth"
        blocked_followup = True
    elif manual_stop_candidate:
        status = "direct_retrigger_followup_guard_manual_stop"
        followup_guard_available = True
        followup_guard_allowed = False
        followup_guard_block_reason = "blocked_manual_review_required"
        selected_followup_kind = "manual_stop"
        selected_followup_action = "manual_review_required"
        selected_followup_payload = {
            "followup_kind": "manual_stop",
            "source": "prompt216_direct_retrigger_followup_guard",
            "stop_reason": normalized_stop_reason or "manual_stop",
            "next_action": "manual_review_required",
        }
        exactly_one_followup_target = True
        manual_stop_followup = True
        blocked_followup = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = normalized_stop_reason or "manual_stop"
        out_next_action = "manual_review_required"
    elif blocked_candidate:
        status = "direct_retrigger_followup_guard_blocked"
        followup_guard_available = True
        followup_guard_allowed = False
        followup_guard_block_reason = (
            normalized_result_block_reason or "direct_retrigger_followup_not_safe"
        )
        selected_followup_kind = "blocked"
        selected_followup_action = "manual_review_required"
        selected_followup_payload = {
            "followup_kind": "blocked",
            "source": "prompt216_direct_retrigger_followup_guard",
            "stop_reason": normalized_stop_reason
            or normalized_result_block_reason
            or "direct_retrigger_followup_not_safe",
            "next_action": "manual_review_required",
        }
        exactly_one_followup_target = True
        blocked_followup = True
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = (
            normalized_stop_reason
            or normalized_result_block_reason
            or "direct_retrigger_followup_not_safe"
        )
        out_next_action = "manual_review_required"
    else:
        non_stop_candidates: list[str] = []
        if bounded_multi_step_candidate:
            non_stop_candidates.append("bounded_multi_step_coordinator")
        elif result_assimilation_chain_candidate:
            non_stop_candidates.append("result_assimilation_chain")

        if len(non_stop_candidates) > 1:
            status = "direct_retrigger_followup_guard_blocked_conflict"
            followup_guard_available = True
            followup_guard_allowed = False
            followup_guard_block_reason = "conflicting_direct_retrigger_followup_targets"
            selected_followup_kind = "blocked"
            selected_followup_action = "manual_review_required"
            selected_followup_payload = {
                "followup_kind": "blocked",
                "source": "prompt216_direct_retrigger_followup_guard",
                "stop_reason": "conflicting_direct_retrigger_followup_targets",
                "next_action": "manual_review_required",
            }
            followup_conflict_detected = True
            conflicting_followup_targets = sorted(non_stop_candidates)
            blocked_followup = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = "conflicting_direct_retrigger_followup_targets"
            out_next_action = "manual_review_required"
        elif len(non_stop_candidates) == 1 and non_stop_candidates[0] == "bounded_multi_step_coordinator":
            status = "direct_retrigger_followup_guard_multistep_ready"
            followup_guard_available = True
            followup_guard_allowed = True
            followup_guard_block_reason = ""
            selected_followup_kind = "bounded_multi_step_coordinator"
            selected_followup_action = "prepare_bounded_multi_step_coordinator"
            selected_followup_payload = {
                "followup_kind": "bounded_multi_step_coordinator",
                "source": "prompt216_direct_retrigger_followup_guard",
                "source_result_class": normalized_result_class,
                "source_selected_retrigger_kind": normalized_source_kind,
                "next_action": "prepare_bounded_multi_step_coordinator",
            }
            exactly_one_followup_target = True
            continue_to_bounded_multi_step_coordinator = True
            blocked_followup = False
            fresh_attempt_followup_allowed = bool(fresh_attempt_detected)
            existing_truth_followup_allowed = bool(existing_truth_surface_detected)
            stale_truth_followup_blocked = False
            not_callable_followup_blocked = False
            out_should_prepare_result_assimilation_chain = True
            out_manual_review_required = False
            out_should_stop = False
            out_stop_reason = ""
            out_next_action = "prepare_bounded_multi_step_coordinator"
            prompt217_multistep_ready = True
            prompt217_multistep_source = "prompt216_direct_retrigger_followup_guard"
            prompt217_multistep_contract = {
                "contract_kind": "bounded_multi_step_preflight",
                "source": "prompt216_direct_retrigger_followup_guard",
                "selected_followup_kind": "bounded_multi_step_coordinator",
                "source_result_class": normalized_result_class,
                "source_selected_retrigger_kind": normalized_source_kind,
                "fresh_attempt_detected": bool(fresh_attempt_detected),
                "existing_truth_surface_detected": bool(existing_truth_surface_detected),
                "allow_unbounded_loop": False,
                "max_next_steps": 1,
                "requires_stop_policy_guard": True,
                "requires_budget_guard": True,
                "requires_result_assimilation": True,
                "next_action": "prepare_bounded_multi_step_coordinator",
            }
        elif len(non_stop_candidates) == 1 and non_stop_candidates[0] == "result_assimilation_chain":
            status = "direct_retrigger_followup_guard_result_assimilation_ready"
            followup_guard_available = True
            followup_guard_allowed = True
            followup_guard_block_reason = ""
            selected_followup_kind = "result_assimilation_chain"
            selected_followup_action = "prepare_result_assimilation_chain"
            selected_followup_payload = {
                "followup_kind": "result_assimilation_chain",
                "source": "prompt216_direct_retrigger_followup_guard",
                "source_result_class": normalized_result_class,
                "source_selected_retrigger_kind": normalized_source_kind,
                "next_action": "prepare_result_assimilation_chain",
            }
            exactly_one_followup_target = True
            continue_to_result_assimilation_chain = True
            blocked_followup = False
            fresh_attempt_followup_allowed = bool(fresh_attempt_detected)
            existing_truth_followup_allowed = bool(existing_truth_surface_detected)
            stale_truth_followup_blocked = False
            not_callable_followup_blocked = False
            out_should_prepare_result_assimilation_chain = True
            out_manual_review_required = False
            out_should_stop = False
            out_stop_reason = ""
            out_next_action = "prepare_result_assimilation_chain"
        else:
            status = "direct_retrigger_followup_guard_blocked_insufficient_truth"
            followup_guard_available = False
            followup_guard_allowed = False
            followup_guard_block_reason = "blocked_insufficient_direct_retrigger_followup_truth"
            selected_followup_kind = "blocked"
            selected_followup_action = "manual_review_required"
            selected_followup_payload = {
                "followup_kind": "blocked",
                "source": "prompt216_direct_retrigger_followup_guard",
                "stop_reason": "insufficient_direct_retrigger_followup_truth",
                "next_action": "manual_review_required",
            }
            blocked_followup = True
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = "insufficient_direct_retrigger_followup_truth"
            out_next_action = "manual_review_required"

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if out_next_action not in allowed_next_actions:
        out_next_action = "insufficient_truth"
    if status == "insufficient_truth":
        status = "direct_retrigger_followup_guard_blocked_insufficient_truth"
        followup_guard_available = False
        followup_guard_allowed = False
        followup_guard_block_reason = "blocked_insufficient_direct_retrigger_followup_truth"
        followup_guard_source = "prompt215_direct_retrigger_result_assimilation"
        selected_followup_kind = "blocked"
        selected_followup_action = "manual_review_required"
        selected_followup_payload = {}
        exactly_one_followup_target = False
        followup_conflict_detected = False
        conflicting_followup_targets = []
        continue_to_result_assimilation_chain = False
        continue_to_bounded_multi_step_coordinator = False
        manual_stop_followup = False
        blocked_followup = True
        fresh_attempt_followup_allowed = False
        existing_truth_followup_allowed = False
        stale_truth_followup_blocked = False
        not_callable_followup_blocked = False
        prompt217_multistep_ready = False
        prompt217_multistep_source = ""
        prompt217_multistep_contract = {}
        out_should_continue_local_loop = False
        out_should_start_unbounded_loop = False
        out_should_prepare_result_assimilation_chain = False
        out_should_prepare_next_controller_decision = False
        out_should_invoke_codex = False
        out_should_execute_rollback = False
        out_should_execute_commit = False
        out_should_push = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_direct_retrigger_followup_truth"
        out_next_action = "manual_review_required"

    return {
        "project_browser_autonomous_direct_retrigger_followup_guard_status": status,
        "project_browser_autonomous_direct_retrigger_followup_guard_followup_guard_available": bool(
            followup_guard_available
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_followup_guard_allowed": bool(
            followup_guard_allowed
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_followup_guard_block_reason": (
            followup_guard_block_reason
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_followup_guard_source": (
            followup_guard_source
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_selected_followup_kind": (
            selected_followup_kind
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_selected_followup_action": (
            selected_followup_action
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_selected_followup_payload": (
            selected_followup_payload
            if isinstance(selected_followup_payload, Mapping)
            else {}
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_exactly_one_followup_target": bool(
            exactly_one_followup_target
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_followup_conflict_detected": bool(
            followup_conflict_detected
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_conflicting_followup_targets": (
            _normalize_string_list(conflicting_followup_targets)
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_continue_to_result_assimilation_chain": bool(
            continue_to_result_assimilation_chain
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_continue_to_bounded_multi_step_coordinator": bool(
            continue_to_bounded_multi_step_coordinator
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_manual_stop_followup": bool(
            manual_stop_followup
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_blocked_followup": bool(
            blocked_followup
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_fresh_attempt_followup_allowed": bool(
            fresh_attempt_followup_allowed
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_existing_truth_followup_allowed": bool(
            existing_truth_followup_allowed
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_stale_truth_followup_blocked": bool(
            stale_truth_followup_blocked
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_not_callable_followup_blocked": bool(
            not_callable_followup_blocked
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_source_result_class": (
            normalized_result_class
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_source_selected_retrigger_kind": (
            normalized_source_kind
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_source_retrigger_status": (
            normalized_source_retrigger_status
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_terminal_result_detected": bool(
            terminal_result_detected
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_terminal_result_source": (
            normalized_terminal_result_source
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_cycle_budget_remaining": int(
            out_cycle_budget_remaining
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_codex_budget_remaining": int(
            out_codex_budget_remaining
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_rollback_budget_remaining": int(
            out_rollback_budget_remaining
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_commit_budget_remaining": int(
            out_commit_budget_remaining
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_budget_checked": bool(
            out_budget_checked
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_prompt217_multistep_ready": bool(
            prompt217_multistep_ready
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_prompt217_multistep_source": (
            prompt217_multistep_source
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_prompt217_multistep_contract": (
            prompt217_multistep_contract
            if isinstance(prompt217_multistep_contract, Mapping)
            else {}
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_should_continue_local_loop": bool(
            out_should_continue_local_loop
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_should_start_unbounded_loop": bool(
            out_should_start_unbounded_loop
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_should_prepare_result_assimilation_chain": bool(
            out_should_prepare_result_assimilation_chain
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_should_prepare_next_controller_decision": bool(
            out_should_prepare_next_controller_decision
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_should_invoke_codex": bool(
            out_should_invoke_codex
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_should_execute_rollback": bool(
            out_should_execute_rollback
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_should_execute_commit": bool(
            out_should_execute_commit
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_should_push": bool(
            out_should_push
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_manual_review_required": bool(
            out_manual_review_required
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_should_stop": bool(
            out_should_stop
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_stop_reason": (
            out_stop_reason
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_next_action": (
            out_next_action
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_direct_retrigger_followup_guard_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_status,
                    normalized_result_class,
                    normalized_result_block_reason,
                    normalized_source_kind,
                    normalized_source_action,
                    normalized_source_retrigger_status,
                    normalized_delegated_kind,
                    normalized_delegated_status,
                    normalized_delegated_next_action,
                    normalized_terminal_result_source,
                    normalized_feedback_kind,
                    normalized_feedback_source,
                    normalized_next_target_kind,
                    normalized_next_target_action,
                    normalized_stop_reason,
                    normalized_next_action,
                    normalized_coordinator_status,
                    normalized_stale_gate_status,
                    normalized_one_bounded_status,
                    normalized_final_guard_status,
                    normalized_multi_cycle_status,
                    normalized_codex_reentry_status,
                    normalized_rollback_execution_status,
                    normalized_commit_execution_status,
                    normalized_fix_generation_status,
                    normalized_next_generation_status,
                    "authoritative_prompt215_missing" if not authoritative_selected else "",
                    "source_result_not_selected" if not bool(result_selected) else "",
                    "source_result_not_available" if not bool(result_available) else "",
                    "source_retrigger_not_attempted" if not bool(source_retrigger_attempted) else "",
                    "source_retrigger_not_completed" if not bool(source_retrigger_completed) else "",
                    "source_retrigger_failed" if bool(source_retrigger_failed) else "",
                    "non_selected_retriggers_not_noop"
                    if not bool(non_selected_retriggers_noop_confirmed)
                    else "",
                    "callable_existing_path_not_detected"
                    if not bool(callable_existing_path_detected)
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
                    "feedback_payload_missing"
                    if controller_feedback_ready and not normalized_feedback_payload
                    else "",
                    "next_target_payload_missing"
                    if bool(next_bounded_control_target_ready)
                    and not normalized_next_target_payload
                    else "",
                    "budget_not_checked" if not out_budget_checked else "",
                ]
            )
        ),
    }

def _build_project_browser_autonomous_bounded_n2_policy_conformance_gate_state(
    *,
    policy_status: str,
    policy_next_action: str,
    selected_reason_policy: str,
    root_cause_reason_policy: str,
    readiness_policy: str,
    downstream_action_policy: str,
    remediation_policy: str,
    prompt229_allowed_by_policy: bool,
    prompt229_block_reason: str,
    policy_should_prepare_prompt229: bool,
    policy_should_prepare_manual_review: bool,
    policy_should_preserve_manual_stop: bool,
    policy_should_route_by_selected_reason_family: bool,
    policy_should_route_remediation_by_root_cause_family: bool,
    policy_warnings: Any,
    readout_status: str,
    selected_reason_family: str,
    selected_primary_reason: str,
    root_cause_reason_family: str,
    root_cause_primary_reason: str,
    prompt224_reason_family: str,
    prompt225_reason_family: str,
    prompt226_reason_family: str,
    prompt227_reason_family: str,
    prompt228_reason_family: str,
    prompt228_e2e_flow_check_ready: bool,
    prompt228_fresh_runtime_evidence_ready: bool,
) -> dict[str, Any]:
    allowed_statuses = {
        "bounded_n2_policy_conformance_passed",
        "bounded_n2_policy_conformance_passed_manual_stop",
        "bounded_n2_policy_conformance_blocked",
        "bounded_n2_policy_conformance_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "prepare_prompt229_preflight",
        "manual_review_required",
        "insufficient_truth",
    }

    normalized_policy_status = _normalize_text(policy_status, default="")
    normalized_policy_next_action = _normalize_text(policy_next_action, default="")
    normalized_selected_reason_policy = _normalize_text(selected_reason_policy, default="")
    normalized_root_cause_reason_policy = _normalize_text(
        root_cause_reason_policy,
        default="",
    )
    normalized_readiness_policy = _normalize_text(readiness_policy, default="")
    normalized_prompt229_block_reason = _normalize_text(prompt229_block_reason, default="")
    normalized_selected_reason_family = _normalize_text(
        selected_reason_family,
        default="unknown",
    )
    normalized_root_cause_reason_family = _normalize_text(
        root_cause_reason_family,
        default="unknown",
    )
    normalized_selected_primary_reason = _normalize_text(selected_primary_reason, default="")
    normalized_root_cause_primary_reason = _normalize_text(
        root_cause_primary_reason,
        default="",
    )
    normalized_readout_status = _normalize_text(readout_status, default="")
    normalized_downstream_action_policy = _normalize_text(downstream_action_policy, default="")
    normalized_remediation_policy = _normalize_text(remediation_policy, default="")

    prompt229_ready_from_prompt228_booleans = bool(
        bool(prompt228_e2e_flow_check_ready) or bool(prompt228_fresh_runtime_evidence_ready)
    )

    policy_surface_available = bool(
        normalized_policy_status
        and normalized_selected_reason_policy
        and normalized_root_cause_reason_policy
        and normalized_readiness_policy
    )
    reason_family_routing_available = bool(
        normalized_selected_reason_family
        and normalized_selected_reason_family != "unknown"
        and bool(policy_should_route_by_selected_reason_family)
    )
    root_cause_routing_available = bool(
        normalized_root_cause_reason_family
        and normalized_root_cause_reason_family != "unknown"
        and bool(policy_should_route_remediation_by_root_cause_family)
    )
    prompt229_readiness_policy_available = bool(
        normalized_readiness_policy
        == "prompt229_readiness_requires_explicit_prompt228_ready_boolean"
    )
    prompt229_readiness_policy_respected = bool(
        not (bool(prompt229_allowed_by_policy) and not prompt229_ready_from_prompt228_booleans)
    )

    reason_family_chain = [
        _normalize_text(prompt224_reason_family, default=""),
        _normalize_text(prompt225_reason_family, default=""),
        _normalize_text(prompt226_reason_family, default=""),
        _normalize_text(prompt227_reason_family, default=""),
        _normalize_text(prompt228_reason_family, default=""),
    ]
    taxonomy_chain_available = all(bool(item) for item in reason_family_chain)

    policy_surface_authoritative = bool(
        policy_surface_available
        and bool(normalized_readout_status)
        and reason_family_routing_available
        and root_cause_routing_available
        and prompt229_readiness_policy_available
        and taxonomy_chain_available
    )

    legacy_token_only_routing_detected = bool(
        policy_surface_available
        and (
            (
                normalized_selected_reason_family in {"", "unknown"}
                and normalized_selected_primary_reason.startswith("blocked_")
            )
            or (
                normalized_root_cause_reason_family in {"", "unknown"}
                and normalized_root_cause_primary_reason.startswith("blocked_")
            )
        )
    )

    conformance_block_reason = _first_true_reason(
        [
            (not policy_surface_available, "missing_policy_surface"),
            (not policy_surface_authoritative, "policy_surface_not_authoritative"),
            (not reason_family_routing_available, "selected_reason_family_routing_unavailable"),
            (not root_cause_routing_available, "root_cause_reason_family_routing_unavailable"),
            (
                not prompt229_readiness_policy_available,
                "prompt229_readiness_policy_unavailable",
            ),
            (
                not prompt229_readiness_policy_respected,
                "prompt229_readiness_policy_not_respected",
            ),
            (legacy_token_only_routing_detected, "legacy_token_only_routing_detected"),
        ],
        default="",
    )

    compatibility_warnings = _normalize_string_list(policy_warnings)
    if bool(legacy_token_only_routing_detected):
        compatibility_warnings.append("legacy_token_only_routing_detected")
    if bool(policy_surface_available) and not bool(prompt229_readiness_policy_respected):
        compatibility_warnings.append("prompt229_readiness_policy_not_respected")
    compatibility_warnings = _normalize_string_list(compatibility_warnings)
    compatibility_warning_required = bool(compatibility_warnings)

    conformance_passed = bool(
        policy_surface_authoritative
        and reason_family_routing_available
        and root_cause_routing_available
        and prompt229_readiness_policy_available
        and prompt229_readiness_policy_respected
        and not legacy_token_only_routing_detected
    )

    status = "bounded_n2_policy_conformance_insufficient_truth"
    next_action = "manual_review_required"
    should_prepare_prompt229 = False
    should_prepare_manual_review = True
    should_stop = True

    if conformance_passed:
        if bool(policy_should_preserve_manual_stop):
            status = "bounded_n2_policy_conformance_passed_manual_stop"
            next_action = "manual_review_required"
            should_prepare_prompt229 = False
            should_prepare_manual_review = True
            should_stop = True
        else:
            status = "bounded_n2_policy_conformance_passed"
            should_prepare_prompt229 = bool(
                bool(policy_should_prepare_prompt229) and bool(prompt229_allowed_by_policy)
            )
            if should_prepare_prompt229:
                next_action = "prepare_prompt229_preflight"
                should_prepare_manual_review = False
                should_stop = False
            else:
                next_action = (
                    normalized_policy_next_action
                    if normalized_policy_next_action in {"manual_review_required", "prepare_prompt229_preflight"}
                    else "manual_review_required"
                )
                should_prepare_manual_review = bool(policy_should_prepare_manual_review)
                should_stop = bool(should_prepare_manual_review)
    elif policy_surface_available:
        status = "bounded_n2_policy_conformance_blocked"
        next_action = "manual_review_required"
        should_prepare_prompt229 = False
        should_prepare_manual_review = True
        should_stop = True
    else:
        status = "bounded_n2_policy_conformance_insufficient_truth"
        next_action = "manual_review_required"
        should_prepare_prompt229 = False
        should_prepare_manual_review = True
        should_stop = True

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"
    if status == "insufficient_truth":
        status = "bounded_n2_policy_conformance_insufficient_truth"
        next_action = "manual_review_required"
        policy_surface_available = False
        policy_surface_authoritative = False
        conformance_passed = False
        conformance_block_reason = "insufficient_n2_policy_conformance_truth"
        should_prepare_prompt229 = False
        should_prepare_manual_review = True
        should_stop = True
        if not compatibility_warnings:
            compatibility_warnings = ["insufficient_n2_policy_conformance_truth"]
        compatibility_warning_required = bool(compatibility_warnings)

    return {
        "project_browser_autonomous_bounded_n2_policy_conformance_gate_status": status,
        "project_browser_autonomous_bounded_n2_policy_conformance_gate_next_action": next_action,
        "project_browser_autonomous_bounded_n2_policy_conformance_gate_policy_surface_available": bool(
            policy_surface_available
        ),
        "project_browser_autonomous_bounded_n2_policy_conformance_gate_policy_surface_authoritative": bool(
            policy_surface_authoritative
        ),
        "project_browser_autonomous_bounded_n2_policy_conformance_gate_legacy_token_only_routing_detected": bool(
            legacy_token_only_routing_detected
        ),
        "project_browser_autonomous_bounded_n2_policy_conformance_gate_reason_family_routing_available": bool(
            reason_family_routing_available
        ),
        "project_browser_autonomous_bounded_n2_policy_conformance_gate_root_cause_routing_available": bool(
            root_cause_routing_available
        ),
        "project_browser_autonomous_bounded_n2_policy_conformance_gate_prompt229_readiness_policy_available": bool(
            prompt229_readiness_policy_available
        ),
        "project_browser_autonomous_bounded_n2_policy_conformance_gate_prompt229_readiness_policy_respected": bool(
            prompt229_readiness_policy_respected
        ),
        "project_browser_autonomous_bounded_n2_policy_conformance_gate_selected_reason_family": (
            normalized_selected_reason_family
        ),
        "project_browser_autonomous_bounded_n2_policy_conformance_gate_root_cause_reason_family": (
            normalized_root_cause_reason_family
        ),
        "project_browser_autonomous_bounded_n2_policy_conformance_gate_prompt229_allowed_by_policy": bool(
            prompt229_allowed_by_policy
        ),
        "project_browser_autonomous_bounded_n2_policy_conformance_gate_prompt229_ready_from_prompt228_booleans": bool(
            prompt229_ready_from_prompt228_booleans
        ),
        "project_browser_autonomous_bounded_n2_policy_conformance_gate_conformance_passed": bool(
            conformance_passed
        ),
        "project_browser_autonomous_bounded_n2_policy_conformance_gate_conformance_block_reason": (
            conformance_block_reason
        ),
        "project_browser_autonomous_bounded_n2_policy_conformance_gate_compatibility_warning_required": bool(
            compatibility_warning_required
        ),
        "project_browser_autonomous_bounded_n2_policy_conformance_gate_compatibility_warnings": (
            compatibility_warnings
        ),
        "project_browser_autonomous_bounded_n2_policy_conformance_gate_should_prepare_prompt229": bool(
            should_prepare_prompt229
        ),
        "project_browser_autonomous_bounded_n2_policy_conformance_gate_should_prepare_manual_review": bool(
            should_prepare_manual_review
        ),
        "project_browser_autonomous_bounded_n2_policy_conformance_gate_should_stop": bool(
            should_stop
        ),
        "project_browser_autonomous_bounded_n2_policy_conformance_gate_readiness_policy": (
            normalized_readiness_policy
        ),
        "project_browser_autonomous_bounded_n2_policy_conformance_gate_downstream_action_policy": (
            normalized_downstream_action_policy
        ),
        "project_browser_autonomous_bounded_n2_policy_conformance_gate_remediation_policy": (
            normalized_remediation_policy
        ),
    }

def _build_project_browser_autonomous_fresh_runtime_e2e_readiness_gate_state(
    *,
    handoff_status: str,
    handoff_next_action: str,
    handoff_ready: bool,
    handoff_source: str,
    handoff_stage: str,
    conformance_passed: bool,
    policy_surface_authoritative: bool,
    selected_reason_family: str,
    selected_primary_reason: str,
    root_cause_reason_family: str,
    root_cause_primary_reason: str,
    root_cause_upstream_reason_source: str,
    prompt229_allowed_by_policy: bool,
    prompt229_ready_from_prompt228_booleans: bool,
    prompt229_e2e_flow_check_ready: bool,
    prompt229_fresh_runtime_evidence_ready: bool,
    selected_prompt229_path: str,
    prompt229_handoff_block_reason: str,
    should_prepare_prompt229: bool,
    should_prepare_manual_review: bool,
    should_stop: bool,
    handoff_payload: Any,
) -> dict[str, Any]:
    allowed_statuses = {
        "fresh_runtime_e2e_readiness_e2e_ready",
        "fresh_runtime_e2e_readiness_fresh_evidence_ready",
        "fresh_runtime_e2e_readiness_manual_stop_fresh_evidence_required",
        "fresh_runtime_e2e_readiness_manual_stop",
        "fresh_runtime_e2e_readiness_blocked",
        "fresh_runtime_e2e_readiness_blocked_conflict",
        "fresh_runtime_e2e_readiness_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "prepare_e2e_readiness_check",
        "prepare_fresh_runtime_evidence_check",
        "manual_review_required",
        "insufficient_truth",
    }
    allowed_selected_paths = {
        "e2e_flow_check",
        "fresh_runtime_evidence",
        "none",
        "conflict",
    }

    normalized_handoff_status = _normalize_text(handoff_status, default="")
    normalized_handoff_next_action = _normalize_text(handoff_next_action, default="")
    normalized_handoff_source = _normalize_text(handoff_source, default="")
    normalized_handoff_stage = _normalize_text(handoff_stage, default="")
    normalized_selected_reason_family = _normalize_text(
        selected_reason_family,
        default="unknown",
    )
    normalized_selected_primary_reason = _normalize_text(selected_primary_reason, default="")
    normalized_root_cause_reason_family = _normalize_text(
        root_cause_reason_family,
        default="unknown",
    )
    normalized_root_cause_primary_reason = _normalize_text(root_cause_primary_reason, default="")
    normalized_root_cause_upstream_reason_source = _normalize_text(
        root_cause_upstream_reason_source,
        default="",
    )
    normalized_selected_prompt229_path = _normalize_text(selected_prompt229_path, default="none")
    normalized_prompt229_handoff_block_reason = _normalize_text(
        prompt229_handoff_block_reason,
        default="",
    )

    if normalized_selected_prompt229_path not in allowed_selected_paths:
        normalized_selected_prompt229_path = "none"

    manual_stop_selected = bool(
        normalized_selected_reason_family == "manual_stop"
        or normalized_selected_primary_reason == "blocked_manual_review_required"
        or bool(should_prepare_manual_review)
        or bool(should_stop)
    )
    fresh_runtime_evidence_required = bool(
        normalized_root_cause_reason_family == "fresh_surface_missing"
    )
    prompt228_ready_conflict = bool(
        bool(prompt229_e2e_flow_check_ready)
        and bool(prompt229_fresh_runtime_evidence_ready)
    )

    readiness_gate_available = bool(normalized_handoff_status)
    readiness_gate_authoritative = bool(
        readiness_gate_available
        and bool(normalized_handoff_source)
        and bool(normalized_handoff_stage)
        and bool(conformance_passed)
        and bool(policy_surface_authoritative)
    )

    status = "fresh_runtime_e2e_readiness_blocked_insufficient_truth"
    next_action = "manual_review_required"
    selected_check_kind = "blocked"
    selected_check_action = "manual_review_required"
    fresh_runtime_evidence_available = False
    fresh_runtime_evidence_check_ready = False
    e2e_readiness_check_ready = False
    e2e_flow_check_ready = False
    prompt230_check_ready = False
    prompt230_check_source = ""
    prompt230_check_contract: dict[str, Any] = {}
    check_command_contract: dict[str, Any] = {}
    expected_output_files: list[str] = []
    success_criteria: list[str] = []
    failure_triage_fields: list[str] = [
        "root_cause_reason_family",
        "prompt229_handoff_block_reason",
        "selected_reason_family",
        "manual_review_required",
        "should_stop",
    ]
    manual_review_required = True
    should_prepare_manual_review_out = True
    should_prepare_fresh_runtime_evidence_check = False
    should_prepare_e2e_readiness_check = False
    should_prepare_prompt230 = False
    should_stop_out = True
    prompt229_handoff_ready = bool(handoff_ready)
    prompt229_handoff_block_reason_out = normalized_prompt229_handoff_block_reason

    if not readiness_gate_available:
        status = "fresh_runtime_e2e_readiness_blocked_insufficient_truth"
        next_action = "manual_review_required"
        prompt229_handoff_block_reason_out = "insufficient_prompt229_handoff_truth"
    elif prompt228_ready_conflict:
        status = "fresh_runtime_e2e_readiness_blocked_conflict"
        next_action = "manual_review_required"
        prompt229_handoff_block_reason_out = "prompt229_readiness_conflict"
    elif (
        bool(handoff_ready)
        and bool(prompt229_allowed_by_policy)
        and bool(prompt229_ready_from_prompt228_booleans)
        and normalized_selected_prompt229_path == "e2e_flow_check"
    ):
        status = "fresh_runtime_e2e_readiness_e2e_ready"
        next_action = "prepare_e2e_readiness_check"
        selected_check_kind = "e2e_readiness_check"
        selected_check_action = "prepare_e2e_readiness_check"
        fresh_runtime_evidence_available = bool(not fresh_runtime_evidence_required)
        fresh_runtime_evidence_check_ready = False
        e2e_readiness_check_ready = True
        e2e_flow_check_ready = True
        prompt230_check_ready = True
        prompt230_check_source = "prompt229_fresh_runtime_e2e_readiness_gate"
        manual_review_required = False
        should_prepare_manual_review_out = False
        should_prepare_fresh_runtime_evidence_check = False
        should_prepare_e2e_readiness_check = True
        should_prepare_prompt230 = True
        should_stop_out = False
    elif (
        bool(handoff_ready)
        and bool(prompt229_allowed_by_policy)
        and bool(prompt229_ready_from_prompt228_booleans)
        and normalized_selected_prompt229_path == "fresh_runtime_evidence"
    ):
        status = "fresh_runtime_e2e_readiness_fresh_evidence_ready"
        next_action = "prepare_fresh_runtime_evidence_check"
        selected_check_kind = "fresh_runtime_evidence_check"
        selected_check_action = "prepare_fresh_runtime_evidence_check"
        fresh_runtime_evidence_available = False
        fresh_runtime_evidence_check_ready = True
        e2e_readiness_check_ready = False
        e2e_flow_check_ready = False
        prompt230_check_ready = True
        prompt230_check_source = "prompt229_fresh_runtime_e2e_readiness_gate"
        manual_review_required = False
        should_prepare_manual_review_out = False
        should_prepare_fresh_runtime_evidence_check = True
        should_prepare_e2e_readiness_check = False
        should_prepare_prompt230 = True
        should_stop_out = False
    elif fresh_runtime_evidence_required:
        status = "fresh_runtime_e2e_readiness_manual_stop_fresh_evidence_required"
        next_action = "manual_review_required"
        selected_check_kind = "fresh_runtime_evidence_check"
        selected_check_action = "prepare_fresh_runtime_evidence_check"
        fresh_runtime_evidence_available = False
        fresh_runtime_evidence_check_ready = True
        e2e_readiness_check_ready = False
        e2e_flow_check_ready = False
        prompt230_check_ready = True
        prompt230_check_source = "prompt229_fresh_runtime_e2e_readiness_gate"
        manual_review_required = True
        should_prepare_manual_review_out = True
        should_prepare_fresh_runtime_evidence_check = True
        should_prepare_e2e_readiness_check = False
        should_prepare_prompt230 = True
        should_stop_out = True
        if not prompt229_handoff_block_reason_out:
            prompt229_handoff_block_reason_out = (
                "selected_manual_stop_or_prompt228_not_ready"
                if manual_stop_selected
                else "fresh_runtime_evidence_required"
            )
    elif manual_stop_selected:
        status = "fresh_runtime_e2e_readiness_manual_stop"
        next_action = "manual_review_required"
        selected_check_kind = "manual_review"
        selected_check_action = "manual_review_required"
        fresh_runtime_evidence_available = False
        prompt230_check_ready = False
        manual_review_required = True
        should_prepare_manual_review_out = True
        should_prepare_prompt230 = False
        should_stop_out = True
        if not prompt229_handoff_block_reason_out:
            prompt229_handoff_block_reason_out = "manual_stop"
    else:
        status = "fresh_runtime_e2e_readiness_blocked"
        next_action = "manual_review_required"
        selected_check_kind = "blocked"
        selected_check_action = "manual_review_required"
        fresh_runtime_evidence_available = False
        prompt230_check_ready = False
        manual_review_required = True
        should_prepare_manual_review_out = True
        should_prepare_prompt230 = False
        should_stop_out = True
        if not prompt229_handoff_block_reason_out:
            prompt229_handoff_block_reason_out = _first_true_reason(
                [
                    (
                        not bool(prompt229_allowed_by_policy),
                        "prompt229_not_allowed_by_policy",
                    ),
                    (
                        not bool(prompt229_ready_from_prompt228_booleans),
                        "prompt228_not_ready",
                    ),
                    (
                        normalized_handoff_next_action == "manual_review_required",
                        "manual_review_required",
                    ),
                ],
                default="readiness_gate_blocked",
            )

    if prompt230_check_ready:
        expected_output_files = [
            "approved_restart_execution_contract.json",
            "run_state.json",
        ]
        success_criteria = [
            "fresh_runtime_evidence_available=true in a later stage",
            "one_step_accounting_valid=true in a later stage",
            "completed_fresh_surface_detected=true in a later stage",
        ]
        check_command_contract = {
            "repo_path": "/home/rai/codex-local-runner",
            "artifacts_dir": "/tmp/codex-local-runner-decision/artifacts",
            "suggested_out_dir_prefix": "/tmp/codex-local-runner-checks/prompt230_fresh_runtime_evidence",
            "transport_mode": "dry-run",
            "job_id_prefix": "prompt230-fresh-runtime-evidence",
            "expected_contract_file": "approved_restart_execution_contract.json",
            "expected_run_state_file": "run_state.json",
            "required_evidence_fields": [
                "fresh runtime execution attempted/completed fields",
                "generated prompt/receipt/result surfaces",
                "one-step accounting validity",
                "stop policy result",
                "no push/no GitHub/no unbounded-loop guarantees",
            ],
            "success_criteria": success_criteria,
            "failure_triage_fields": failure_triage_fields,
        }
        prompt230_check_contract = {
            "contract_kind": (
                "fresh_runtime_evidence_check_preflight"
                if selected_check_kind == "fresh_runtime_evidence_check"
                else "e2e_readiness_check_preflight"
            ),
            "source": "prompt229_fresh_runtime_e2e_readiness_gate",
            "selected_check_kind": selected_check_kind,
            "selected_check_action": selected_check_action,
            "root_cause_reason_family": normalized_root_cause_reason_family,
            "selected_reason_family": normalized_selected_reason_family,
            "prompt229_handoff_block_reason": prompt229_handoff_block_reason_out,
            "check_command_contract": check_command_contract,
            "next_action": next_action,
        }

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"
    if status == "insufficient_truth":
        status = "fresh_runtime_e2e_readiness_blocked_insufficient_truth"
        next_action = "manual_review_required"
        readiness_gate_available = False
        readiness_gate_authoritative = False
        selected_check_kind = "blocked"
        selected_check_action = "manual_review_required"
        fresh_runtime_evidence_available = False
        fresh_runtime_evidence_check_ready = False
        e2e_readiness_check_ready = False
        e2e_flow_check_ready = False
        prompt230_check_ready = False
        prompt230_check_source = ""
        prompt230_check_contract = {}
        check_command_contract = {}
        expected_output_files = []
        success_criteria = []
        manual_review_required = True
        should_prepare_manual_review_out = True
        should_prepare_fresh_runtime_evidence_check = False
        should_prepare_e2e_readiness_check = False
        should_prepare_prompt230 = False
        should_stop_out = True
        prompt229_handoff_block_reason_out = "insufficient_prompt229_handoff_truth"

    return {
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_status": status,
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_next_action": next_action,
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_readiness_gate_available": bool(
            readiness_gate_available
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_readiness_gate_authoritative": bool(
            readiness_gate_authoritative
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_selected_check_kind": (
            selected_check_kind
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_selected_check_action": (
            selected_check_action
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_fresh_runtime_evidence_required": bool(
            fresh_runtime_evidence_required
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_fresh_runtime_evidence_available": bool(
            fresh_runtime_evidence_available
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_fresh_runtime_evidence_check_ready": bool(
            fresh_runtime_evidence_check_ready
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_e2e_readiness_check_ready": bool(
            e2e_readiness_check_ready
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_e2e_flow_check_ready": bool(
            e2e_flow_check_ready
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_root_cause_reason_family": (
            normalized_root_cause_reason_family
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_selected_reason_family": (
            normalized_selected_reason_family
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_prompt229_handoff_ready": bool(
            prompt229_handoff_ready
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_prompt229_handoff_block_reason": (
            prompt229_handoff_block_reason_out
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_prompt230_check_ready": bool(
            prompt230_check_ready
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_prompt230_check_source": (
            prompt230_check_source
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_prompt230_check_contract": (
            prompt230_check_contract
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_check_command_contract": (
            check_command_contract
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_expected_output_files": (
            expected_output_files
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_success_criteria": (
            success_criteria
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_failure_triage_fields": (
            failure_triage_fields
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_manual_review_required": bool(
            manual_review_required
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_should_stop": bool(
            should_stop_out
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_should_prepare_manual_review": bool(
            should_prepare_manual_review_out
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_should_prepare_fresh_runtime_evidence_check": bool(
            should_prepare_fresh_runtime_evidence_check
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_should_prepare_e2e_readiness_check": bool(
            should_prepare_e2e_readiness_check
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_should_prepare_prompt230": bool(
            should_prepare_prompt230
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_should_invoke_codex": False,
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_should_execute_rollback": False,
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_should_execute_commit": False,
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_should_push": False,
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_should_start_unbounded_loop": False,
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_root_cause_primary_reason": (
            normalized_root_cause_primary_reason
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_root_cause_upstream_reason_source": (
            normalized_root_cause_upstream_reason_source
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_handoff_source": (
            normalized_handoff_source
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_handoff_stage": (
            normalized_handoff_stage
        ),
        "project_browser_autonomous_fresh_runtime_e2e_readiness_gate_handoff_payload": (
            dict(handoff_payload) if isinstance(handoff_payload, Mapping) else {}
        ),
    }

def _build_project_browser_autonomous_bounded_artifact_existence_read_parse_gate_state(
    *,
    prompt249_status: str,
    prompt249_surface_available: bool,
    prompt249_surface_authoritative: bool,
    should_prepare_prompt250: bool,
    prompt250_gate_ready: bool,
    required_supplied_path_fields: Any,
    supplied_path_payload_detected: bool,
    accepted_supplied_path_fields: Any,
    missing_supplied_path_fields: Any,
    rejected_supplied_path_fields: Any,
    normalized_supplied_artifact_paths: Any,
    supplied_artifact_path_map: Any,
    artifact_supply_out_dir: str,
    artifact_supply_job_id: str,
    artifact_supply_transport_mode: str,
    same_run_scope_conformance: str,
    artifact_name_conformance: str,
    path_source_conformance: str,
    review_permission_unlock_preconditions_ready: bool,
    existence_review_permission: bool,
    read_permission: bool,
    parse_permission: bool,
    prompt250_gate_block_reason: str,
    observed_outputs_available: bool,
    fresh_runtime_evidence_detected: bool,
    fresh_runtime_evidence_valid: bool,
    completed_fresh_surface_detected: bool,
    one_step_accounting_valid: bool,
    stop_policy_passed: bool,
    prompt222_update_allowed: bool,
    n2_readiness_allowed: bool,
    bounded_continuation_allowed: bool,
) -> dict[str, Any]:
    allowed_statuses = {
        "bounded_artifact_existence_read_parse_gate_ready",
        "bounded_artifact_existence_read_parse_gate_blocked_missing_supplied_path_payload",
        "bounded_artifact_existence_read_parse_gate_blocked_prompt249_not_ready",
        "bounded_artifact_existence_read_parse_gate_blocked_metadata_preconditions",
        "bounded_artifact_existence_read_parse_gate_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "prepare_prompt251_artifact_content_review_fresh_evidence_validity_assimilation",
        "manual_review_required",
        "insufficient_truth",
    }
    required_path_field_set = {
        "approved_restart_execution_contract_json_path",
        "run_state_json_path",
        "manifest_json_path",
    }
    artifact_access_safety_limits = [
        "explicit_paths_only",
        "required_artifacts_only",
        "no_glob_expansion",
        "no_filesystem_discovery",
        "no_log_scraping",
        "no_command_execution",
        "bounded_file_count_max_3",
        "json_artifacts_only",
        "no_git_mutation",
    ]
    forbidden_actions = [
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
        "prompt222_update",
        "n2_reevaluation",
        "bounded_continuation_execution",
    ]

    normalized_prompt249_status = _normalize_text(prompt249_status, default="")
    normalized_required_supplied_path_fields = _normalize_string_list(
        required_supplied_path_fields
    )
    normalized_required_path_field_set = set(normalized_required_supplied_path_fields)
    required_fields_present = required_path_field_set.issubset(
        normalized_required_path_field_set
    )
    normalized_accepted_supplied_path_fields = _normalize_string_list(
        accepted_supplied_path_fields
    )
    normalized_missing_supplied_path_fields = _normalize_string_list(
        missing_supplied_path_fields
    )
    normalized_rejected_supplied_path_fields = _normalize_string_list(
        rejected_supplied_path_fields
    )
    normalized_normalized_supplied_artifact_paths = _normalize_string_list(
        normalized_supplied_artifact_paths
    )
    normalized_supplied_artifact_path_map = (
        dict(supplied_artifact_path_map)
        if isinstance(supplied_artifact_path_map, Mapping)
        else {}
    )
    normalized_artifact_supply_out_dir = _normalize_text(artifact_supply_out_dir, default="")
    normalized_artifact_supply_job_id = _normalize_text(artifact_supply_job_id, default="")
    normalized_artifact_supply_transport_mode = _normalize_text(
        artifact_supply_transport_mode, default=""
    )
    normalized_same_run_scope_conformance = _normalize_text(
        same_run_scope_conformance, default=""
    )
    normalized_artifact_name_conformance = _normalize_text(
        artifact_name_conformance, default=""
    )
    normalized_path_source_conformance = _normalize_text(
        path_source_conformance, default=""
    )
    normalized_prompt250_gate_block_reason = _normalize_text(
        prompt250_gate_block_reason, default=""
    )

    status = "bounded_artifact_existence_read_parse_gate_blocked_prompt249_not_ready"
    next_action = "manual_review_required"
    bounded_existence_validation_gate_ready = False
    bounded_existence_validation_allowed = False
    bounded_existence_validation_status = "blocked_prompt249_not_ready"
    bounded_file_read_gate_ready = False
    bounded_file_read_allowed = False
    bounded_file_read_status = "blocked_prompt249_not_ready"
    bounded_json_parse_gate_ready = False
    bounded_json_parse_allowed = False
    bounded_json_parse_status = "blocked_prompt249_not_ready"
    artifact_access_plan_ready = False
    artifact_access_plan_status = "blocked_prompt249_not_ready"
    artifact_access_plan: list[str] = []
    artifact_review_ready = False
    artifact_review_status = "blocked_artifact_access_not_allowed"
    fresh_evidence_validity_gate_ready = False
    fresh_evidence_validity_gate_status = "blocked_artifact_review_not_ready"
    prompt251_ready = False
    prompt251_block_reason = "prompt249_not_ready"
    should_prepare_prompt251 = False

    authoritative_ready = bool(
        prompt249_surface_available
        and prompt249_surface_authoritative
        and should_prepare_prompt250
        and prompt250_gate_ready
        and required_fields_present
        and normalized_prompt249_status
    )

    if authoritative_ready:
        bounded_existence_validation_gate_ready = True
        bounded_file_read_gate_ready = True
        bounded_json_parse_gate_ready = True
        artifact_access_plan_ready = True
        prompt251_ready = True
        should_prepare_prompt251 = True
        next_action = (
            "prepare_prompt251_artifact_content_review_fresh_evidence_validity_assimilation"
        )

        missing_payload = bool(
            not supplied_path_payload_detected
            or normalized_missing_supplied_path_fields
            or not normalized_normalized_supplied_artifact_paths
        )

        if missing_payload:
            status = (
                "bounded_artifact_existence_read_parse_gate_blocked_missing_supplied_path_payload"
            )
            bounded_existence_validation_allowed = False
            bounded_existence_validation_status = "blocked_missing_supplied_path_payload"
            bounded_file_read_allowed = False
            bounded_file_read_status = "blocked_missing_supplied_path_payload"
            bounded_json_parse_allowed = False
            bounded_json_parse_status = "blocked_missing_supplied_path_payload"
            artifact_access_plan_status = "blocked_missing_supplied_path_payload"
            artifact_access_plan = []
            artifact_review_ready = False
            artifact_review_status = "blocked_artifact_access_not_allowed"
            fresh_evidence_validity_gate_ready = False
            fresh_evidence_validity_gate_status = "blocked_artifact_review_not_ready"
            prompt251_block_reason = (
                normalized_prompt250_gate_block_reason or "missing_supplied_path_payload"
            )
        else:
            metadata_permissions_ready = bool(
                len(normalized_accepted_supplied_path_fields) == 3
                and not normalized_rejected_supplied_path_fields
                and len(normalized_normalized_supplied_artifact_paths) == 3
                and review_permission_unlock_preconditions_ready
                and existence_review_permission
                and read_permission
                and parse_permission
                and normalized_same_run_scope_conformance
                not in {"blocked_missing_supplied_path_payload", ""}
                and normalized_artifact_name_conformance
                not in {"blocked_missing_supplied_path_payload", ""}
                and normalized_path_source_conformance
                not in {"blocked_missing_supplied_path_payload", ""}
                and normalized_artifact_supply_out_dir
                and normalized_artifact_supply_job_id
                and normalized_artifact_supply_transport_mode == "dry-run"
            )
            if metadata_permissions_ready:
                status = "bounded_artifact_existence_read_parse_gate_ready"
                bounded_existence_validation_allowed = True
                bounded_existence_validation_status = (
                    "ready_for_bounded_existence_validation"
                )
                bounded_file_read_allowed = True
                bounded_file_read_status = "ready_for_bounded_file_read"
                bounded_json_parse_allowed = True
                bounded_json_parse_status = "ready_for_bounded_json_parse"
                artifact_access_plan_status = "ready_for_bounded_artifact_access"
                artifact_access_plan = [
                    "bounded_validate_required_artifact_existence",
                    "bounded_read_required_artifacts_only",
                    "bounded_parse_required_json_only",
                ]
                artifact_review_ready = True
                artifact_review_status = "ready_for_bounded_artifact_review"
                fresh_evidence_validity_gate_ready = True
                fresh_evidence_validity_gate_status = (
                    "ready_for_fresh_evidence_validity_gate"
                )
                prompt251_block_reason = ""
            else:
                status = "bounded_artifact_existence_read_parse_gate_blocked_metadata_preconditions"
                bounded_existence_validation_allowed = False
                bounded_existence_validation_status = "blocked_metadata_preconditions"
                bounded_file_read_allowed = False
                bounded_file_read_status = "blocked_metadata_preconditions"
                bounded_json_parse_allowed = False
                bounded_json_parse_status = "blocked_metadata_preconditions"
                artifact_access_plan_status = "blocked_metadata_preconditions"
                artifact_access_plan = []
                artifact_review_ready = False
                artifact_review_status = "blocked_artifact_access_not_allowed"
                fresh_evidence_validity_gate_ready = False
                fresh_evidence_validity_gate_status = "blocked_artifact_review_not_ready"
                prompt251_block_reason = "metadata_preconditions_not_met"
    elif normalized_prompt249_status:
        status = "bounded_artifact_existence_read_parse_gate_blocked_prompt249_not_ready"
        prompt251_block_reason = "prompt249_not_ready"
    else:
        status = "bounded_artifact_existence_read_parse_gate_blocked_insufficient_truth"
        prompt251_block_reason = "insufficient_truth"

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"
    if status == "insufficient_truth":
        status = "bounded_artifact_existence_read_parse_gate_blocked_insufficient_truth"
        next_action = "manual_review_required"
        normalized_required_supplied_path_fields = []
        normalized_accepted_supplied_path_fields = []
        normalized_missing_supplied_path_fields = []
        normalized_rejected_supplied_path_fields = []
        normalized_normalized_supplied_artifact_paths = []
        normalized_supplied_artifact_path_map = {}
        normalized_artifact_supply_out_dir = ""
        normalized_artifact_supply_job_id = ""
        normalized_artifact_supply_transport_mode = ""
        bounded_existence_validation_gate_ready = False
        bounded_existence_validation_allowed = False
        bounded_existence_validation_status = "blocked_insufficient_truth"
        bounded_file_read_gate_ready = False
        bounded_file_read_allowed = False
        bounded_file_read_status = "blocked_insufficient_truth"
        bounded_json_parse_gate_ready = False
        bounded_json_parse_allowed = False
        bounded_json_parse_status = "blocked_insufficient_truth"
        artifact_access_plan_ready = False
        artifact_access_plan_status = "blocked_insufficient_truth"
        artifact_access_plan = []
        artifact_access_safety_limits = []
        artifact_review_ready = False
        artifact_review_status = "blocked_insufficient_truth"
        fresh_evidence_validity_gate_ready = False
        fresh_evidence_validity_gate_status = "blocked_insufficient_truth"
        prompt251_ready = False
        prompt251_block_reason = "insufficient_truth"
        should_prepare_prompt251 = False
        forbidden_actions = []

    return {
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_status": status,
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_source": (
            "prompt250_bounded_artifact_existence_read_parse_gate"
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_prompt249_surface_available": bool(
            prompt249_surface_available
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_prompt249_surface_authoritative": bool(
            prompt249_surface_authoritative
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_required_supplied_path_fields": (
            normalized_required_supplied_path_fields
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_supplied_path_payload_detected": bool(
            supplied_path_payload_detected
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_accepted_supplied_path_fields": (
            normalized_accepted_supplied_path_fields
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_missing_supplied_path_fields": (
            normalized_missing_supplied_path_fields
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_rejected_supplied_path_fields": (
            normalized_rejected_supplied_path_fields
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_normalized_supplied_artifact_paths": (
            normalized_normalized_supplied_artifact_paths
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_supplied_artifact_path_map": (
            normalized_supplied_artifact_path_map
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_artifact_supply_out_dir": (
            normalized_artifact_supply_out_dir
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_artifact_supply_job_id": (
            normalized_artifact_supply_job_id
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_artifact_supply_transport_mode": (
            normalized_artifact_supply_transport_mode
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_review_permission_unlock_preconditions_ready": bool(
            review_permission_unlock_preconditions_ready
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_existence_review_permission": bool(
            existence_review_permission
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_read_permission": bool(
            read_permission
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_parse_permission": bool(
            parse_permission
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_bounded_existence_validation_gate_ready": bool(
            bounded_existence_validation_gate_ready
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_bounded_existence_validation_allowed": bool(
            bounded_existence_validation_allowed
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_bounded_existence_validation_status": (
            _normalize_text(bounded_existence_validation_status, default="")
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_bounded_file_read_gate_ready": bool(
            bounded_file_read_gate_ready
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_bounded_file_read_allowed": bool(
            bounded_file_read_allowed
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_bounded_file_read_status": (
            _normalize_text(bounded_file_read_status, default="")
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_bounded_json_parse_gate_ready": bool(
            bounded_json_parse_gate_ready
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_bounded_json_parse_allowed": bool(
            bounded_json_parse_allowed
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_bounded_json_parse_status": (
            _normalize_text(bounded_json_parse_status, default="")
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_artifact_access_plan_ready": bool(
            artifact_access_plan_ready
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_artifact_access_plan_status": (
            _normalize_text(artifact_access_plan_status, default="")
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_artifact_access_plan": (
            artifact_access_plan
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_artifact_access_safety_limits": (
            artifact_access_safety_limits
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_artifact_review_ready": bool(
            artifact_review_ready
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_artifact_review_status": (
            _normalize_text(artifact_review_status, default="")
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_fresh_evidence_validity_gate_ready": bool(
            fresh_evidence_validity_gate_ready
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_fresh_evidence_validity_gate_status": (
            _normalize_text(fresh_evidence_validity_gate_status, default="")
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_prompt251_ready": bool(
            prompt251_ready
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_prompt251_block_reason": (
            _normalize_text(prompt251_block_reason, default="")
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_forbidden_actions": (
            forbidden_actions
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_observed_outputs_available": bool(
            observed_outputs_available
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_fresh_runtime_evidence_detected": bool(
            fresh_runtime_evidence_detected
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_fresh_runtime_evidence_valid": bool(
            fresh_runtime_evidence_valid
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_completed_fresh_surface_detected": bool(
            completed_fresh_surface_detected
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_one_step_accounting_valid": bool(
            one_step_accounting_valid
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_stop_policy_passed": bool(
            stop_policy_passed
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_prompt222_update_allowed": bool(
            False and prompt222_update_allowed
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_n2_readiness_allowed": bool(
            False and n2_readiness_allowed
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_bounded_continuation_allowed": bool(
            False and bounded_continuation_allowed
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_should_prepare_prompt251": bool(
            should_prepare_prompt251
        ),
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_should_read_files": False,
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_should_parse_json": False,
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_should_validate_file_existence": False,
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_should_scan_filesystem": False,
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_should_execute_manual_command": False,
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_should_execute_runbook": False,
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_should_execute_check_command": False,
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_should_invoke_codex": False,
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_should_execute_commit": False,
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_should_execute_rollback": False,
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_should_push": False,
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_should_start_unbounded_loop": False,
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_should_update_prompt222": False,
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_should_re_evaluate_n2": False,
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_should_start_bounded_continuation": False,
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_should_stop": True,
        "project_browser_autonomous_bounded_artifact_existence_read_parse_gate_next_action": (
            next_action
        ),
    }

def _build_project_browser_autonomous_commit_tag_gate_state(
    *,
    chatgpt_diff_review_decision_state: Mapping[str, Any] | None,
    codex_capture_gate_state: Mapping[str, Any] | None,
    approved_restart_payload: Mapping[str, Any] | None,
    prior_approved_restart_execution_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    review_state = (
        dict(chatgpt_diff_review_decision_state)
        if isinstance(chatgpt_diff_review_decision_state, Mapping)
        else {}
    )
    capture_state = dict(codex_capture_gate_state) if isinstance(codex_capture_gate_state, Mapping) else {}
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

    def _compact(text: Any, *, max_chars: int = 240) -> str:
        value = _normalize_text(text, default="")
        if not value:
            return ""
        normalized = " ".join(value.split())
        if len(normalized) <= max_chars:
            return normalized
        return normalized[:max_chars]

    def _is_unsafe_changed_path(path_text: str) -> tuple[bool, str]:
        text = _normalize_text(path_text, default="")
        if not text:
            return (True, "empty_path")
        if Path(text).is_absolute() or text.startswith("/") or text.startswith("\\"):
            return (True, f"absolute_path:{text}")
        if "://" in text:
            return (True, f"malformed_path:{text}")
        if ".." in text.split("/"):
            return (True, f"parent_traversal:{text}")
        normalized = text.replace("\\", "/")
        if normalized == ".git" or normalized.startswith(".git/"):
            return (True, f"git_internal_path:{text}")
        if normalized.startswith("../") or "/../" in normalized:
            return (True, f"outside_repo_path:{text}")
        if normalized.startswith("./"):
            normalized = normalized[2:]
        if not normalized:
            return (True, "malformed_path")
        return (False, "")

    gate_enabled = _read_flag(
        "project_browser_autonomous_commit_tag_gate_enabled",
        default=False,
    )
    allow_missing_validation = False
    for key in (
        "project_browser_autonomous_commit_tag_gate_allow_missing_validation",
        "project_browser_autonomous_allow_missing_validation",
    ):
        if key in approved_restart or key in prior_payload:
            allow_missing_validation = _read_flag(key, default=False)
            break

    review_status = _normalize_text(
        review_state.get("project_browser_autonomous_chatgpt_diff_review_decision_status"),
        default="",
    )
    review_next_action = _normalize_text(
        review_state.get("project_browser_autonomous_chatgpt_diff_review_decision_next_action"),
        default="",
    )
    review_decision = _normalize_text(
        review_state.get("project_browser_autonomous_chatgpt_diff_review_decision"),
        default="",
    )
    review_confidence = 0.0
    confidence_value = review_state.get("project_browser_autonomous_chatgpt_diff_review_confidence")
    if isinstance(confidence_value, (int, float)) and not isinstance(confidence_value, bool):
        review_confidence = max(0.0, min(1.0, float(confidence_value)))
    review_risk = _normalize_text(
        review_state.get("project_browser_autonomous_chatgpt_diff_review_risk"),
        default="high",
    ).lower()
    review_blocking_issues = _normalize_string_list(
        review_state.get("project_browser_autonomous_chatgpt_diff_review_blocking_issues")
    )
    review_commit_recommendation = bool(
        review_state.get("project_browser_autonomous_chatgpt_diff_review_commit_recommendation", False)
    )
    review_summary = _compact(
        review_state.get("project_browser_autonomous_chatgpt_diff_review_summary"),
        max_chars=280,
    )

    changed_files = _normalize_string_list(
        capture_state.get("project_browser_autonomous_codex_capture_gate_changed_files")
    )
    diff_summary = _compact(
        capture_state.get("project_browser_autonomous_codex_capture_gate_diff_summary"),
        max_chars=240,
    )
    validation_summary = _compact(
        capture_state.get("project_browser_autonomous_codex_capture_gate_validation_summary"),
        max_chars=240,
    )
    codex_output_summary = _compact(
        capture_state.get("project_browser_autonomous_codex_capture_gate_codex_output_summary"),
        max_chars=240,
    )
    capture_output_path = _normalize_text(
        capture_state.get("project_browser_autonomous_codex_capture_gate_capture_output_path"),
        default="",
    )
    capture_artifact_paths = _normalize_string_list(
        capture_state.get("project_browser_autonomous_codex_capture_gate_capture_artifact_paths")
    )
    prompt_kind = _normalize_text(
        capture_state.get("project_browser_autonomous_codex_capture_gate_prompt_kind"),
        default="",
    )
    prompt_fingerprint = _normalize_text(
        capture_state.get("project_browser_autonomous_codex_capture_gate_prompt_fingerprint"),
        default="",
    )

    status = "commit_tag_gate_not_requested"
    next_action = "enable_commit_tag_gate"
    ready = False
    blocked_reason = "commit_tag_gate_disabled"
    fix_recommendations: list[str] = []

    approval_valid = bool(
        review_status == "chatgpt_diff_review_decision_approved_for_commit_gate"
        and review_decision == "approve"
        and review_next_action == "prepare_commit_or_pr_gate"
    )

    unsafe_path_reasons: list[str] = []
    safe_changed_files: list[str] = []
    for path in changed_files:
        unsafe, reason = _is_unsafe_changed_path(path)
        if unsafe:
            unsafe_path_reasons.append(reason)
        else:
            safe_changed_files.append(path)

    validation_lower = validation_summary.lower()
    validation_failing = any(
        token in validation_lower for token in ("error", "failed", "failure", "diff_check_has_errors")
    )
    validation_missing = (not validation_summary) or any(
        token in validation_lower for token in ("not_available", "unavailable", "missing")
    )

    policy_failed_reasons: list[str] = []
    if review_confidence < 0.80:
        policy_failed_reasons.append("confidence_below_threshold")
    if review_risk not in {"low", "medium"}:
        policy_failed_reasons.append("risk_not_allowed")
    if review_blocking_issues:
        policy_failed_reasons.append("blocking_issues_present")
    if not review_commit_recommendation:
        policy_failed_reasons.append("commit_recommendation_false")
    if not safe_changed_files:
        policy_failed_reasons.append("no_changed_files")

    if gate_enabled:
        if not approval_valid:
            status = "commit_tag_gate_blocked_missing_approval"
            next_action = "request_or_recheck_chatgpt_approve_decision"
            blocked_reason = "review_approval_not_ready"
            fix_recommendations = [
                "regenerate diff review and require approve decision",
                "request manual review if decision remains unclear",
            ]
        elif unsafe_path_reasons:
            status = "commit_tag_gate_blocked_unsafe_paths"
            next_action = "inspect_unsafe_changed_paths"
            blocked_reason = unsafe_path_reasons[0]
            fix_recommendations = [
                "inspect unsafe changed paths",
                "regenerate capture with repo-local relative paths only",
            ]
        elif validation_failing or (validation_missing and not allow_missing_validation):
            status = "commit_tag_gate_blocked_validation"
            next_action = "rerun_validation_and_review"
            blocked_reason = (
                "validation_failed"
                if validation_failing
                else "validation_missing_without_allowance"
            )
            fix_recommendations = [
                "rerun validation",
                "fix validation failures before commit/tag readiness",
                "request manual review if validation cannot be produced",
            ]
        elif policy_failed_reasons:
            status = "commit_tag_gate_blocked_policy"
            next_action = "resolve_commit_tag_gate_policy_issues"
            blocked_reason = policy_failed_reasons[0]
            fix_recommendations = [
                "fix blocking issues in review result",
                "regenerate diff review with clearer evidence",
                "request manual review",
            ]
        else:
            status = "commit_tag_gate_ready"
            next_action = "prepare_explicit_commit_tag_execution_step"
            blocked_reason = "none"
            ready = True

    short_fp_source = prompt_fingerprint
    if not short_fp_source:
        short_fp_source = hashlib.sha256(
            "|".join([review_summary, ",".join(safe_changed_files)]).encode("utf-8")
        ).hexdigest()
    short_fp = short_fp_source[:10]
    file_count = len(safe_changed_files)
    top_files = ", ".join(safe_changed_files[:3]) if safe_changed_files else "no-files"
    prompt_label = prompt_kind if prompt_kind else "change"
    commit_message = (
        f"chore: {prompt_label} review-approved ({file_count} files) - {review_summary or top_files}"
    )
    commit_message = _compact(commit_message, max_chars=120)
    tag_name = f"prompt275-commit-gate-{short_fp}"
    tag_name = "".join(
        char if (char.isalnum() or char in {"-", "_", "."}) else "-"
        for char in tag_name
    ).strip("-")
    if not tag_name:
        tag_name = "prompt275-commit-gate-unknown"

    if not fix_recommendations and not ready:
        fix_recommendations = [
            "rerun validation",
            "request manual review",
            "regenerate diff review",
        ]

    readiness_summary = (
        f"review={review_status or 'unknown'}; confidence={review_confidence:.2f}; "
        f"risk={review_risk or 'unknown'}; changed_files={file_count}; "
        f"validation={validation_summary or 'missing'}; diff={diff_summary or 'n/a'}; "
        f"capture={capture_output_path or 'n/a'}; artifacts={len(capture_artifact_paths)}; "
        f"codex={codex_output_summary or 'n/a'}"
    )

    return {
        "project_browser_autonomous_commit_tag_gate_status": status,
        "project_browser_autonomous_commit_tag_gate_next_action": next_action,
        "project_browser_autonomous_commit_tag_gate_enabled": bool(gate_enabled),
        "project_browser_autonomous_commit_tag_gate_ready": bool(ready),
        "project_browser_autonomous_commit_tag_gate_commit_message": commit_message,
        "project_browser_autonomous_commit_tag_gate_tag_name": tag_name,
        "project_browser_autonomous_commit_tag_gate_changed_files": (
            _normalize_string_list(safe_changed_files)
        ),
        "project_browser_autonomous_commit_tag_gate_validation_summary": validation_summary,
        "project_browser_autonomous_commit_tag_gate_review_summary": (
            _compact(f"{review_summary}; {readiness_summary}", max_chars=480)
        ),
        "project_browser_autonomous_commit_tag_gate_blocked_reason": blocked_reason,
        "project_browser_autonomous_commit_tag_gate_fix_recommendations": (
            _normalize_string_list(fix_recommendations)
        ),
    }


__all__ = [
    "_build_project_browser_autonomous_continuation_gate_state",
    "_build_project_browser_autonomous_controller_state",
    "_build_project_browser_autonomous_rolling_gate_state",
    "_build_project_browser_autonomous_rolling_controller_candidate_state",
    "_build_project_browser_autonomous_safe_patch_apply_gate_state",
    "_build_project_browser_autonomous_bounded_continuation_controller_state",
    "_build_project_browser_autonomous_lane_contract_guard_state",
    "_build_project_browser_autonomous_guarded_lane_dispatch_state",
    "_build_project_browser_autonomous_bounded_local_control_decision_state",
    "_build_project_browser_autonomous_control_contract_dispatch_state",
    "_build_project_browser_autonomous_control_dispatch_refresh_state",
    "_build_project_browser_autonomous_final_runtime_continuation_guard_state",
    "_build_project_browser_autonomous_stale_fresh_ordering_gate_state",
    "_build_project_browser_autonomous_direct_retrigger_followup_guard_state",
    "_build_project_browser_autonomous_bounded_n2_policy_conformance_gate_state",
    "_build_project_browser_autonomous_fresh_runtime_e2e_readiness_gate_state",
    "_build_project_browser_autonomous_bounded_artifact_existence_read_parse_gate_state",
    "_build_project_browser_autonomous_commit_tag_gate_state",
]

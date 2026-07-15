from __future__ import annotations
from typing import Any
from typing import Mapping
from typing import Sequence
from automation.orchestration.planned_runner.project_browser.constants import (
    _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS,
    _PROJECT_BROWSER_AUTONOMOUS_MANUAL_OVERRIDE_STATUSES,
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

def _build_project_browser_autonomous_resume_watchdog_state(
    *,
    autonomous_short_batch_status: str,
    autonomous_short_batch_permission: str,
    autonomous_short_batch_steps_attempted: int,
    autonomous_short_batch_stop_reason: str,
    autonomous_short_batch_current_step_status: str,
    autonomous_short_batch_next_action: str,
    autonomous_short_batch_source_status: str,
    autonomous_short_batch_receipt_status: str,
    autonomous_short_batch_receipt_kind: str,
    autonomous_run_ledger_persistence_status: str,
    autonomous_run_ledger_permission: str,
    autonomous_run_ledger_source_status: str,
    autonomous_run_ledger_counter_posture: str,
    autonomous_run_ledger_duplicate_status: str,
    autonomous_run_ledger_persistence_target_status: str,
    autonomous_run_ledger_receipt_status: str,
    autonomous_cooldown_status: str,
    autonomous_loop_risk_status: str,
    autonomous_safety_switch_status: str,
    autonomous_manual_override_status: str,
    autonomous_safe_stop_status: str,
) -> dict[str, Any]:
    short_batch_status = _normalize_text(
        autonomous_short_batch_status,
        default="insufficient_truth",
    )
    short_batch_permission = _normalize_text(
        autonomous_short_batch_permission,
        default="insufficient_truth",
    )
    short_batch_steps_attempted = _as_non_negative_int(
        autonomous_short_batch_steps_attempted,
        default=0,
    )
    short_batch_stop_reason = _normalize_text(
        autonomous_short_batch_stop_reason,
        default="insufficient_truth",
    )
    short_batch_current_step_status = _normalize_text(
        autonomous_short_batch_current_step_status,
        default="insufficient_truth",
    )
    short_batch_next_action = _normalize_text(
        autonomous_short_batch_next_action,
        default="none",
    )
    short_batch_source_status = _normalize_text(
        autonomous_short_batch_source_status,
        default="insufficient_truth",
    )
    short_batch_receipt_status = _normalize_text(
        autonomous_short_batch_receipt_status,
        default="insufficient_truth",
    )
    short_batch_receipt_kind = _normalize_text(
        autonomous_short_batch_receipt_kind,
        default="insufficient_truth_short_batch_receipt",
    )
    run_ledger_status = _normalize_text(
        autonomous_run_ledger_persistence_status,
        default="insufficient_truth",
    )
    run_ledger_permission = _normalize_text(
        autonomous_run_ledger_permission,
        default="insufficient_truth",
    )
    run_ledger_source_status = _normalize_text(
        autonomous_run_ledger_source_status,
        default="insufficient_truth",
    )
    run_ledger_counter_posture = _normalize_text(
        autonomous_run_ledger_counter_posture,
        default="insufficient_truth",
    )
    run_ledger_duplicate_status = _normalize_text(
        autonomous_run_ledger_duplicate_status,
        default="insufficient_truth",
    )
    run_ledger_persistence_target_status = _normalize_text(
        autonomous_run_ledger_persistence_target_status,
        default="insufficient_truth",
    )
    run_ledger_receipt_status = _normalize_text(
        autonomous_run_ledger_receipt_status,
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

    runtime_posture = [
        "metadata_only",
        "checkpoint_only",
        "watchdog_only",
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
    shared_receipt_kind = "one_pr133_resume_checkpoint_watchdog_receipt"

    def _base_state(
        *,
        resume_status: str,
        resume_kind: str,
        resume_permission: str,
        resume_source_status: str,
        resume_block_reason: str,
        resume_receipt_status: str,
        resume_checkpoint_status: str,
        resume_checkpoint_kind: str,
        resume_next_allowed_action: str,
        watchdog_status: str,
        watchdog_kind: str,
        watchdog_permission: str,
        watchdog_source_status: str,
        watchdog_block_reason: str,
        watchdog_receipt_status: str,
        watchdog_stale_posture: str,
        watchdog_missing_receipt_posture: str,
        watchdog_duplicate_receipt_posture: str,
        watchdog_manual_stop_posture: str,
    ) -> dict[str, Any]:
        return {
            "project_browser_autonomous_resume_status": resume_status,
            "project_browser_autonomous_resume_kind": resume_kind,
            "project_browser_autonomous_resume_permission": resume_permission,
            "project_browser_autonomous_resume_source_status": resume_source_status,
            "project_browser_autonomous_resume_block_reason": resume_block_reason,
            "project_browser_autonomous_resume_receipt_status": resume_receipt_status,
            "project_browser_autonomous_resume_receipt_kind": shared_receipt_kind,
            "project_browser_autonomous_resume_checkpoint_status": resume_checkpoint_status,
            "project_browser_autonomous_resume_checkpoint_kind": resume_checkpoint_kind,
            "project_browser_autonomous_resume_next_allowed_action": resume_next_allowed_action,
            "project_browser_autonomous_resume_runtime_posture": runtime_posture,
            "project_browser_autonomous_watchdog_status": watchdog_status,
            "project_browser_autonomous_watchdog_kind": watchdog_kind,
            "project_browser_autonomous_watchdog_permission": watchdog_permission,
            "project_browser_autonomous_watchdog_source_status": watchdog_source_status,
            "project_browser_autonomous_watchdog_block_reason": watchdog_block_reason,
            "project_browser_autonomous_watchdog_receipt_status": watchdog_receipt_status,
            "project_browser_autonomous_watchdog_receipt_kind": shared_receipt_kind,
            "project_browser_autonomous_watchdog_stale_posture": watchdog_stale_posture,
            "project_browser_autonomous_watchdog_missing_receipt_posture": (
                watchdog_missing_receipt_posture
            ),
            "project_browser_autonomous_watchdog_duplicate_receipt_posture": (
                watchdog_duplicate_receipt_posture
            ),
            "project_browser_autonomous_watchdog_manual_stop_posture": (
                watchdog_manual_stop_posture
            ),
            "project_browser_autonomous_watchdog_runtime_posture": runtime_posture,
        }

    def _insufficient_truth_state(*, block_reason: str) -> dict[str, Any]:
        normalized_block_reason = (
            block_reason
            if block_reason in {"source_inconsistent", "insufficient_truth"}
            else "insufficient_truth"
        )
        return _base_state(
            resume_status="insufficient_truth",
            resume_kind="insufficient_truth_resume_checkpoint_watchdog",
            resume_permission="insufficient_truth",
            resume_source_status="insufficient_truth",
            resume_block_reason=normalized_block_reason,
            resume_receipt_status="insufficient_truth",
            resume_checkpoint_status="insufficient_truth",
            resume_checkpoint_kind="insufficient_truth_resume_checkpoint",
            resume_next_allowed_action="hold_insufficient_truth",
            watchdog_status="insufficient_truth",
            watchdog_kind="insufficient_truth_resume_watchdog_monitor",
            watchdog_permission="insufficient_truth",
            watchdog_source_status="insufficient_truth",
            watchdog_block_reason=normalized_block_reason,
            watchdog_receipt_status="insufficient_truth",
            watchdog_stale_posture="insufficient_truth",
            watchdog_missing_receipt_posture="insufficient_truth",
            watchdog_duplicate_receipt_posture="insufficient_truth",
            watchdog_manual_stop_posture="insufficient_truth",
        )

    if short_batch_status not in {
        "inactive",
        "completed",
        "stopped",
        "blocked",
        "failed",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if short_batch_permission not in _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS:
        return _insufficient_truth_state(block_reason="insufficient_truth")
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
    if short_batch_current_step_status not in {
        "none",
        "ready",
        "executed",
        "blocked",
        "failed",
        "timeout",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if short_batch_next_action not in {
        "none",
        "run_one_md_apply",
        "run_one_browser_command",
        "run_one_codex_attempt",
        "assimilate_result",
        "persist_ledger",
        "stop",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if short_batch_source_status not in {"valid", "inconsistent", "insufficient_truth"}:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if short_batch_receipt_status not in {
        "not_created",
        "ready",
        "blocked",
        "failed",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if short_batch_receipt_kind not in {
        "none",
        "short_batch_receipt",
        "blocked_short_batch_receipt",
        "failed_short_batch_receipt",
        "pause_short_batch_receipt",
        "human_review_short_batch_receipt",
        "insufficient_truth_short_batch_receipt",
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
    if run_ledger_permission not in _PROJECT_BROWSER_AUTONOMOUS_EXECUTION_PERMISSIONS:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if run_ledger_source_status not in {"valid", "inconsistent", "insufficient_truth"}:
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
    if run_ledger_duplicate_status not in {"clear", "duplicate_detected", "insufficient_truth"}:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if run_ledger_persistence_target_status not in {
        "unavailable",
        "existing_path_available",
        "metadata_only",
        "blocked",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if run_ledger_receipt_status not in {
        "not_created",
        "ready",
        "skipped",
        "blocked",
        "failed",
        "pause_required",
        "human_review_required",
        "insufficient_truth",
    }:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if cooldown_status not in {"not_required", "required", "blocked", "insufficient_truth"}:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if loop_risk_status not in {"clear", "suspected", "blocked", "insufficient_truth"}:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if safety_switch_status not in _PROJECT_BROWSER_AUTONOMOUS_SAFETY_SWITCH_STATUSES:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if manual_override_status not in _PROJECT_BROWSER_AUTONOMOUS_MANUAL_OVERRIDE_STATUSES:
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if safe_stop_status not in _PROJECT_BROWSER_AUTONOMOUS_SAFE_STOP_STATUSES:
        return _insufficient_truth_state(block_reason="insufficient_truth")

    if short_batch_steps_attempted > 3:
        return _insufficient_truth_state(block_reason="source_inconsistent")

    source_status = "valid"
    if (
        short_batch_source_status == "insufficient_truth"
        or run_ledger_source_status == "insufficient_truth"
        or run_ledger_counter_posture == "insufficient_truth"
        or run_ledger_duplicate_status == "insufficient_truth"
        or cooldown_status == "insufficient_truth"
        or loop_risk_status == "insufficient_truth"
        or safety_switch_status == "insufficient_truth"
        or manual_override_status == "insufficient_truth"
        or safe_stop_status == "insufficient_truth"
    ):
        source_status = "insufficient_truth"
    elif (
        short_batch_source_status == "inconsistent"
        or run_ledger_source_status == "inconsistent"
        or short_batch_stop_reason == "source_inconsistent"
    ):
        source_status = "inconsistent"

    manual_stop_posture = "clear"
    if source_status == "insufficient_truth":
        manual_stop_posture = "insufficient_truth"
    elif (
        safety_switch_status
        in {"manual_review_required", "pause_required", "disabled", "stop_all", "pause_after_current_step"}
        or manual_override_status in {"requested", "required"}
        or safe_stop_status in {"pause_required", "stop_required"}
    ):
        manual_stop_posture = "manual_stop_detected"

    duplicate_receipt_posture = "clear"
    if source_status == "insufficient_truth":
        duplicate_receipt_posture = "insufficient_truth"
    elif (
        run_ledger_duplicate_status == "duplicate_detected"
        or short_batch_stop_reason == "duplicate_detected"
    ):
        duplicate_receipt_posture = "duplicate_detected"

    terminal_short_batch_statuses = {
        "completed",
        "stopped",
        "blocked",
        "failed",
        "pause_required",
        "human_review_required",
    }
    missing_receipt_posture = "clear"
    if source_status == "insufficient_truth":
        missing_receipt_posture = "insufficient_truth"
    elif (
        short_batch_status in terminal_short_batch_statuses
        and short_batch_receipt_status == "not_created"
    ):
        missing_receipt_posture = "missing_receipt"

    stale_receipt_posture = "clear"
    if source_status == "insufficient_truth":
        stale_receipt_posture = "insufficient_truth"
    elif (
        short_batch_status in terminal_short_batch_statuses
        and short_batch_next_action != "stop"
    ):
        stale_receipt_posture = "stale_receipt"
    elif (
        short_batch_status in terminal_short_batch_statuses
        and short_batch_current_step_status in {"none", "ready"}
        and short_batch_receipt_status
        in {"ready", "blocked", "failed", "pause_required", "human_review_required"}
    ):
        stale_receipt_posture = "stale_receipt"
    elif (
        short_batch_status in {"completed", "stopped"}
        and short_batch_receipt_kind == "none"
    ):
        stale_receipt_posture = "stale_receipt"

    watchdog_status = "clear"
    if (
        manual_stop_posture == "insufficient_truth"
        or duplicate_receipt_posture == "insufficient_truth"
        or missing_receipt_posture == "insufficient_truth"
        or stale_receipt_posture == "insufficient_truth"
    ):
        watchdog_status = "insufficient_truth"
    elif manual_stop_posture == "manual_stop_detected":
        watchdog_status = "manual_stop"
    elif duplicate_receipt_posture == "duplicate_detected":
        watchdog_status = "duplicate_receipt"
    elif missing_receipt_posture == "missing_receipt":
        watchdog_status = "missing_receipt"
    elif stale_receipt_posture == "stale_receipt":
        watchdog_status = "stale"

    watchdog_block_reason = "none"
    watchdog_permission = "allowed_candidate"
    watchdog_receipt_status = "ready"
    if watchdog_status == "insufficient_truth":
        watchdog_block_reason = "insufficient_truth"
        watchdog_permission = "insufficient_truth"
        watchdog_receipt_status = "insufficient_truth"
    elif watchdog_status == "manual_stop":
        watchdog_block_reason = "manual_stop"
        watchdog_permission = "blocked"
    elif watchdog_status == "duplicate_receipt":
        watchdog_block_reason = "duplicate_receipt"
        watchdog_permission = "blocked"
    elif watchdog_status == "missing_receipt":
        watchdog_block_reason = "missing_receipt"
        watchdog_permission = "blocked"
    elif watchdog_status == "stale":
        watchdog_block_reason = "stale_receipt"
        watchdog_permission = "blocked"

    if source_status == "insufficient_truth":
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if source_status == "inconsistent":
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if short_batch_stop_reason == "insufficient_truth":
        return _insufficient_truth_state(block_reason="insufficient_truth")

    if short_batch_status == "pause_required":
        return _base_state(
            resume_status="pause_required",
            resume_kind="pause_resume_checkpoint_watchdog",
            resume_permission="pause_required",
            resume_source_status="valid",
            resume_block_reason="pause_required",
            resume_receipt_status="pause_required",
            resume_checkpoint_status="blocked",
            resume_checkpoint_kind="none",
            resume_next_allowed_action="hold_pause",
            watchdog_status=watchdog_status,
            watchdog_kind="resume_watchdog_monitor",
            watchdog_permission=watchdog_permission,
            watchdog_source_status="valid",
            watchdog_block_reason=watchdog_block_reason,
            watchdog_receipt_status=watchdog_receipt_status,
            watchdog_stale_posture=stale_receipt_posture,
            watchdog_missing_receipt_posture=missing_receipt_posture,
            watchdog_duplicate_receipt_posture=duplicate_receipt_posture,
            watchdog_manual_stop_posture=manual_stop_posture,
        )
    if short_batch_status == "human_review_required":
        return _base_state(
            resume_status="human_review_required",
            resume_kind="human_review_resume_checkpoint_watchdog",
            resume_permission="human_review_required",
            resume_source_status="valid",
            resume_block_reason="human_review_required",
            resume_receipt_status="human_review_required",
            resume_checkpoint_status="blocked",
            resume_checkpoint_kind="none",
            resume_next_allowed_action="hold_human_review",
            watchdog_status=watchdog_status,
            watchdog_kind="resume_watchdog_monitor",
            watchdog_permission=watchdog_permission,
            watchdog_source_status="valid",
            watchdog_block_reason=watchdog_block_reason,
            watchdog_receipt_status=watchdog_receipt_status,
            watchdog_stale_posture=stale_receipt_posture,
            watchdog_missing_receipt_posture=missing_receipt_posture,
            watchdog_duplicate_receipt_posture=duplicate_receipt_posture,
            watchdog_manual_stop_posture=manual_stop_posture,
        )
    if short_batch_status == "failed":
        return _base_state(
            resume_status="failed",
            resume_kind="failed_resume_checkpoint_watchdog",
            resume_permission="blocked",
            resume_source_status="valid",
            resume_block_reason="step_failed",
            resume_receipt_status="failed",
            resume_checkpoint_status="blocked",
            resume_checkpoint_kind="none",
            resume_next_allowed_action="none",
            watchdog_status=watchdog_status,
            watchdog_kind="resume_watchdog_monitor",
            watchdog_permission=watchdog_permission,
            watchdog_source_status="valid",
            watchdog_block_reason=watchdog_block_reason,
            watchdog_receipt_status=watchdog_receipt_status,
            watchdog_stale_posture=stale_receipt_posture,
            watchdog_missing_receipt_posture=missing_receipt_posture,
            watchdog_duplicate_receipt_posture=duplicate_receipt_posture,
            watchdog_manual_stop_posture=manual_stop_posture,
        )
    if short_batch_status == "blocked":
        return _base_state(
            resume_status="blocked",
            resume_kind="blocked_resume_checkpoint_watchdog",
            resume_permission="blocked",
            resume_source_status="valid",
            resume_block_reason="short_batch_blocked",
            resume_receipt_status="blocked",
            resume_checkpoint_status="blocked",
            resume_checkpoint_kind="none",
            resume_next_allowed_action="none",
            watchdog_status=watchdog_status,
            watchdog_kind="resume_watchdog_monitor",
            watchdog_permission=watchdog_permission,
            watchdog_source_status="valid",
            watchdog_block_reason=watchdog_block_reason,
            watchdog_receipt_status=watchdog_receipt_status,
            watchdog_stale_posture=stale_receipt_posture,
            watchdog_missing_receipt_posture=missing_receipt_posture,
            watchdog_duplicate_receipt_posture=duplicate_receipt_posture,
            watchdog_manual_stop_posture=manual_stop_posture,
        )

    if watchdog_status != "clear":
        return _base_state(
            resume_status="stale" if watchdog_status == "stale" else "blocked",
            resume_kind=(
                "stale_resume_checkpoint_watchdog"
                if watchdog_status == "stale"
                else "blocked_resume_checkpoint_watchdog"
            ),
            resume_permission="blocked",
            resume_source_status="valid",
            resume_block_reason=watchdog_block_reason,
            resume_receipt_status="ready",
            resume_checkpoint_status="stale" if watchdog_status == "stale" else "blocked",
            resume_checkpoint_kind="none",
            resume_next_allowed_action="none",
            watchdog_status=watchdog_status,
            watchdog_kind=(
                "stale_resume_watchdog_monitor"
                if watchdog_status == "stale"
                else "blocked_resume_watchdog_monitor"
            ),
            watchdog_permission=watchdog_permission,
            watchdog_source_status="valid",
            watchdog_block_reason=watchdog_block_reason,
            watchdog_receipt_status=watchdog_receipt_status,
            watchdog_stale_posture=stale_receipt_posture,
            watchdog_missing_receipt_posture=missing_receipt_posture,
            watchdog_duplicate_receipt_posture=duplicate_receipt_posture,
            watchdog_manual_stop_posture=manual_stop_posture,
        )

    if short_batch_status == "inactive":
        return _base_state(
            resume_status="inactive",
            resume_kind="none",
            resume_permission="blocked",
            resume_source_status="valid",
            resume_block_reason="none",
            resume_receipt_status="ready",
            resume_checkpoint_status="not_created",
            resume_checkpoint_kind="none",
            resume_next_allowed_action="none",
            watchdog_status="clear",
            watchdog_kind="resume_watchdog_monitor",
            watchdog_permission="allowed_candidate",
            watchdog_source_status="valid",
            watchdog_block_reason="none",
            watchdog_receipt_status="ready",
            watchdog_stale_posture="clear",
            watchdog_missing_receipt_posture="clear",
            watchdog_duplicate_receipt_posture="clear",
            watchdog_manual_stop_posture="clear",
        )

    if short_batch_status not in {"completed", "stopped"}:
        return _insufficient_truth_state(block_reason="source_inconsistent")
    if short_batch_receipt_status not in {
        "ready",
        "blocked",
        "failed",
        "pause_required",
        "human_review_required",
    }:
        return _base_state(
            resume_status="blocked",
            resume_kind="blocked_resume_checkpoint_watchdog",
            resume_permission="blocked",
            resume_source_status="valid",
            resume_block_reason="missing_receipt",
            resume_receipt_status="ready",
            resume_checkpoint_status="blocked",
            resume_checkpoint_kind="none",
            resume_next_allowed_action="none",
            watchdog_status="missing_receipt",
            watchdog_kind="blocked_resume_watchdog_monitor",
            watchdog_permission="blocked",
            watchdog_source_status="valid",
            watchdog_block_reason="missing_receipt",
            watchdog_receipt_status="ready",
            watchdog_stale_posture=stale_receipt_posture,
            watchdog_missing_receipt_posture="missing_receipt",
            watchdog_duplicate_receipt_posture=duplicate_receipt_posture,
            watchdog_manual_stop_posture=manual_stop_posture,
        )

    if run_ledger_status == "pause_required" or run_ledger_permission == "pause_required":
        return _base_state(
            resume_status="pause_required",
            resume_kind="pause_resume_checkpoint_watchdog",
            resume_permission="pause_required",
            resume_source_status="valid",
            resume_block_reason="pause_required",
            resume_receipt_status="pause_required",
            resume_checkpoint_status="blocked",
            resume_checkpoint_kind="none",
            resume_next_allowed_action="hold_pause",
            watchdog_status="clear",
            watchdog_kind="resume_watchdog_monitor",
            watchdog_permission="allowed_candidate",
            watchdog_source_status="valid",
            watchdog_block_reason="none",
            watchdog_receipt_status="ready",
            watchdog_stale_posture=stale_receipt_posture,
            watchdog_missing_receipt_posture=missing_receipt_posture,
            watchdog_duplicate_receipt_posture=duplicate_receipt_posture,
            watchdog_manual_stop_posture=manual_stop_posture,
        )
    if run_ledger_status == "human_review_required" or run_ledger_permission == "human_review_required":
        return _base_state(
            resume_status="human_review_required",
            resume_kind="human_review_resume_checkpoint_watchdog",
            resume_permission="human_review_required",
            resume_source_status="valid",
            resume_block_reason="human_review_required",
            resume_receipt_status="human_review_required",
            resume_checkpoint_status="blocked",
            resume_checkpoint_kind="none",
            resume_next_allowed_action="hold_human_review",
            watchdog_status="clear",
            watchdog_kind="resume_watchdog_monitor",
            watchdog_permission="allowed_candidate",
            watchdog_source_status="valid",
            watchdog_block_reason="none",
            watchdog_receipt_status="ready",
            watchdog_stale_posture=stale_receipt_posture,
            watchdog_missing_receipt_posture=missing_receipt_posture,
            watchdog_duplicate_receipt_posture=duplicate_receipt_posture,
            watchdog_manual_stop_posture=manual_stop_posture,
        )

    if run_ledger_status == "insufficient_truth" or run_ledger_receipt_status == "insufficient_truth":
        return _insufficient_truth_state(block_reason="insufficient_truth")
    if run_ledger_status == "prepared" or run_ledger_persistence_target_status == "metadata_only":
        return _base_state(
            resume_status="blocked",
            resume_kind="blocked_resume_checkpoint_watchdog",
            resume_permission="blocked",
            resume_source_status="valid",
            resume_block_reason="ledger_not_persisted",
            resume_receipt_status="ready",
            resume_checkpoint_status="blocked",
            resume_checkpoint_kind="none",
            resume_next_allowed_action="none",
            watchdog_status="clear",
            watchdog_kind="resume_watchdog_monitor",
            watchdog_permission="allowed_candidate",
            watchdog_source_status="valid",
            watchdog_block_reason="none",
            watchdog_receipt_status="ready",
            watchdog_stale_posture=stale_receipt_posture,
            watchdog_missing_receipt_posture=missing_receipt_posture,
            watchdog_duplicate_receipt_posture=duplicate_receipt_posture,
            watchdog_manual_stop_posture=manual_stop_posture,
        )

    ledger_persisted = bool(
        run_ledger_status == "persisted"
        and run_ledger_permission == "allowed"
        and run_ledger_source_status == "valid"
        and run_ledger_counter_posture == "persisted"
        and run_ledger_persistence_target_status == "existing_path_available"
        and run_ledger_receipt_status == "ready"
    )
    if not ledger_persisted:
        return _base_state(
            resume_status="blocked",
            resume_kind="blocked_resume_checkpoint_watchdog",
            resume_permission="blocked",
            resume_source_status="valid",
            resume_block_reason="ledger_not_persisted",
            resume_receipt_status="ready",
            resume_checkpoint_status="blocked",
            resume_checkpoint_kind="none",
            resume_next_allowed_action="none",
            watchdog_status="clear",
            watchdog_kind="resume_watchdog_monitor",
            watchdog_permission="allowed_candidate",
            watchdog_source_status="valid",
            watchdog_block_reason="none",
            watchdog_receipt_status="ready",
            watchdog_stale_posture=stale_receipt_posture,
            watchdog_missing_receipt_posture=missing_receipt_posture,
            watchdog_duplicate_receipt_posture=duplicate_receipt_posture,
            watchdog_manual_stop_posture=manual_stop_posture,
        )

    if cooldown_status != "not_required":
        return _base_state(
            resume_status="blocked",
            resume_kind="blocked_resume_checkpoint_watchdog",
            resume_permission="blocked",
            resume_source_status="valid",
            resume_block_reason="cooldown_required",
            resume_receipt_status="ready",
            resume_checkpoint_status="blocked",
            resume_checkpoint_kind="none",
            resume_next_allowed_action="none",
            watchdog_status="clear",
            watchdog_kind="resume_watchdog_monitor",
            watchdog_permission="allowed_candidate",
            watchdog_source_status="valid",
            watchdog_block_reason="none",
            watchdog_receipt_status="ready",
            watchdog_stale_posture=stale_receipt_posture,
            watchdog_missing_receipt_posture=missing_receipt_posture,
            watchdog_duplicate_receipt_posture=duplicate_receipt_posture,
            watchdog_manual_stop_posture=manual_stop_posture,
        )
    if loop_risk_status != "clear":
        return _base_state(
            resume_status="blocked",
            resume_kind="blocked_resume_checkpoint_watchdog",
            resume_permission="blocked",
            resume_source_status="valid",
            resume_block_reason="loop_suspected",
            resume_receipt_status="ready",
            resume_checkpoint_status="blocked",
            resume_checkpoint_kind="none",
            resume_next_allowed_action="none",
            watchdog_status="clear",
            watchdog_kind="resume_watchdog_monitor",
            watchdog_permission="allowed_candidate",
            watchdog_source_status="valid",
            watchdog_block_reason="none",
            watchdog_receipt_status="ready",
            watchdog_stale_posture=stale_receipt_posture,
            watchdog_missing_receipt_posture=missing_receipt_posture,
            watchdog_duplicate_receipt_posture=duplicate_receipt_posture,
            watchdog_manual_stop_posture=manual_stop_posture,
        )

    if short_batch_stop_reason == "max_steps_reached":
        return _base_state(
            resume_status="checkpoint_ready",
            resume_kind="resume_checkpoint_watchdog",
            resume_permission="allowed_candidate",
            resume_source_status="valid",
            resume_block_reason="none",
            resume_receipt_status="ready",
            resume_checkpoint_status="created",
            resume_checkpoint_kind="one_resume_checkpoint",
            resume_next_allowed_action="resume_next_short_batch_later",
            watchdog_status="clear",
            watchdog_kind="resume_watchdog_monitor",
            watchdog_permission="allowed_candidate",
            watchdog_source_status="valid",
            watchdog_block_reason="none",
            watchdog_receipt_status="ready",
            watchdog_stale_posture="clear",
            watchdog_missing_receipt_posture="clear",
            watchdog_duplicate_receipt_posture="clear",
            watchdog_manual_stop_posture="clear",
        )
    if short_batch_stop_reason == "none":
        return _base_state(
            resume_status="blocked",
            resume_kind="blocked_resume_checkpoint_watchdog",
            resume_permission="blocked",
            resume_source_status="valid",
            resume_block_reason="short_batch_not_stopped_safely",
            resume_receipt_status="ready",
            resume_checkpoint_status="blocked",
            resume_checkpoint_kind="none",
            resume_next_allowed_action="none",
            watchdog_status="clear",
            watchdog_kind="resume_watchdog_monitor",
            watchdog_permission="allowed_candidate",
            watchdog_source_status="valid",
            watchdog_block_reason="none",
            watchdog_receipt_status="ready",
            watchdog_stale_posture="clear",
            watchdog_missing_receipt_posture="clear",
            watchdog_duplicate_receipt_posture="clear",
            watchdog_manual_stop_posture="clear",
        )

    if short_batch_stop_reason == "pause_required":
        return _base_state(
            resume_status="pause_required",
            resume_kind="pause_resume_checkpoint_watchdog",
            resume_permission="pause_required",
            resume_source_status="valid",
            resume_block_reason="pause_required",
            resume_receipt_status="pause_required",
            resume_checkpoint_status="blocked",
            resume_checkpoint_kind="none",
            resume_next_allowed_action="hold_pause",
            watchdog_status="clear",
            watchdog_kind="resume_watchdog_monitor",
            watchdog_permission="allowed_candidate",
            watchdog_source_status="valid",
            watchdog_block_reason="none",
            watchdog_receipt_status="ready",
            watchdog_stale_posture=stale_receipt_posture,
            watchdog_missing_receipt_posture=missing_receipt_posture,
            watchdog_duplicate_receipt_posture=duplicate_receipt_posture,
            watchdog_manual_stop_posture=manual_stop_posture,
        )
    if short_batch_stop_reason == "human_review_required":
        return _base_state(
            resume_status="human_review_required",
            resume_kind="human_review_resume_checkpoint_watchdog",
            resume_permission="human_review_required",
            resume_source_status="valid",
            resume_block_reason="human_review_required",
            resume_receipt_status="human_review_required",
            resume_checkpoint_status="blocked",
            resume_checkpoint_kind="none",
            resume_next_allowed_action="hold_human_review",
            watchdog_status="clear",
            watchdog_kind="resume_watchdog_monitor",
            watchdog_permission="allowed_candidate",
            watchdog_source_status="valid",
            watchdog_block_reason="none",
            watchdog_receipt_status="ready",
            watchdog_stale_posture=stale_receipt_posture,
            watchdog_missing_receipt_posture=missing_receipt_posture,
            watchdog_duplicate_receipt_posture=duplicate_receipt_posture,
            watchdog_manual_stop_posture=manual_stop_posture,
        )

    return _base_state(
        resume_status="blocked",
        resume_kind="blocked_resume_checkpoint_watchdog",
        resume_permission="blocked",
        resume_source_status="valid",
        resume_block_reason=(
            short_batch_stop_reason
            if short_batch_stop_reason
            in {
                "cooldown_required",
                "loop_suspected",
                "duplicate_detected",
                "ledger_not_persisted",
                "budget_exhausted",
                "failure_budget_exhausted",
                "retry_budget_exhausted",
                "step_failed",
            }
            else "short_batch_not_stopped_safely"
        ),
        resume_receipt_status="ready",
        resume_checkpoint_status="blocked",
        resume_checkpoint_kind="none",
        resume_next_allowed_action="none",
        watchdog_status="clear",
        watchdog_kind="resume_watchdog_monitor",
        watchdog_permission="allowed_candidate",
        watchdog_source_status="valid",
        watchdog_block_reason="none",
        watchdog_receipt_status="ready",
        watchdog_stale_posture=stale_receipt_posture,
        watchdog_missing_receipt_posture=missing_receipt_posture,
        watchdog_duplicate_receipt_posture=duplicate_receipt_posture,
        watchdog_manual_stop_posture=manual_stop_posture,
    )

def _build_project_browser_autonomous_post_reentry_safety_refresh_state(
    *,
    repository_path: str,
    source_assimilation_status: str,
    source_authoritative_kind: str,
    source_authoritative_selected: bool,
    source_authoritative_block_reason: str,
    source_result_class: str,
    source_status: str,
    source_prompt_kind: str,
    source_prompt_path: str,
    source_changed_files: list[str] | None,
    source_changed_files_count: int,
    expected_changed_files: list[str] | None,
    allowed_changed_files: list[str] | None,
    unexpected_changed_files: list[str] | None,
    forbidden_changed_files: list[str] | None,
    too_many_changed_files: bool,
    safe_for_validation_routing: bool,
    validation_routing_candidate: bool,
    validation_routing_block_reason: str,
    prompt170_compat_source_status: str,
    prompt170_compat_result_class: str,
    prompt170_compat_changed_files: list[str] | None,
    prompt170_compat_safe_for_validation_routing: bool,
    prompt170_compat_human_review_required: bool,
    source_human_review_required: bool,
    source_next_action: str,
) -> dict[str, Any]:
    allowed_statuses = {
        "post_reentry_safety_refresh_validation_passed",
        "post_reentry_safety_refresh_validation_failed",
        "post_reentry_safety_refresh_validation_timeout",
        "post_reentry_safety_refresh_invocation_failure",
        "post_reentry_safety_refresh_invocation_timeout",
        "blocked_no_post_reentry_py_compile_candidates",
        "blocked_post_reentry_validation_routing",
        "blocked_post_reentry_unsafe_changes",
        "blocked_insufficient_post_reentry_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "prepare_bounded_continuation",
        "generate_fix_prompt",
        "manual_review_required",
        "wait_for_more_truth",
        "insufficient_truth",
    }
    runtime_posture = [
        "prompt182_post_reentry_safety_refresh",
        "prompt181_precedence_consumption",
        "bounded_py_compile_only",
        "no_codex_invocation",
        "no_loop_start",
        "no_rollback_execution",
        "metadata_continuation_only",
    ]

    normalized_repository_path = _normalize_text(repository_path, default="")
    normalized_source_assimilation_status = _normalize_text(
        source_assimilation_status,
        default="insufficient_truth",
    )
    normalized_source_authoritative_kind = _normalize_text(
        source_authoritative_kind,
        default="none",
    )
    if normalized_source_authoritative_kind not in {"reentry", "normal_write", "none"}:
        normalized_source_authoritative_kind = "none"
    normalized_source_authoritative_selected = bool(source_authoritative_selected)
    normalized_source_authoritative_block_reason = _normalize_text(
        source_authoritative_block_reason,
        default="",
    )
    normalized_source_result_class = _normalize_text(source_result_class, default="blocked")
    normalized_source_status = _normalize_text(source_status, default="insufficient_truth")
    normalized_source_prompt_kind = _normalize_text(source_prompt_kind, default="none")
    if normalized_source_prompt_kind not in {"fix", "next", "none"}:
        normalized_source_prompt_kind = "none"
    normalized_source_prompt_path = _normalize_text(source_prompt_path, default="")
    normalized_source_changed_files = _normalize_string_list(source_changed_files or [])
    normalized_source_changed_files_count = _as_non_negative_int(
        source_changed_files_count,
        default=len(normalized_source_changed_files),
    )
    normalized_expected_changed_files = _normalize_string_list(expected_changed_files or [])
    normalized_allowed_changed_files = _normalize_string_list(allowed_changed_files or [])
    normalized_unexpected_changed_files = _normalize_string_list(
        unexpected_changed_files or []
    )
    normalized_forbidden_changed_files = _normalize_string_list(
        forbidden_changed_files or []
    )
    normalized_too_many_changed_files = bool(too_many_changed_files)
    normalized_safe_for_validation_routing = bool(safe_for_validation_routing)
    normalized_validation_routing_candidate = bool(validation_routing_candidate)
    normalized_validation_routing_block_reason = _normalize_text(
        validation_routing_block_reason,
        default="",
    )
    normalized_prompt170_compat_source_status = _normalize_text(
        prompt170_compat_source_status,
        default="insufficient_truth",
    )
    normalized_prompt170_compat_result_class = _normalize_text(
        prompt170_compat_result_class,
        default="insufficient_truth",
    )
    normalized_prompt170_compat_changed_files = _normalize_string_list(
        prompt170_compat_changed_files or []
    )
    normalized_prompt170_compat_safe_for_validation_routing = bool(
        prompt170_compat_safe_for_validation_routing
    )
    normalized_prompt170_compat_human_review_required = bool(
        prompt170_compat_human_review_required
    )
    normalized_source_human_review_required = bool(source_human_review_required)
    normalized_source_next_action = _normalize_text(source_next_action, default="")

    post_reentry_validation_routing_allowed = False
    post_reentry_validation_routing_block_reason = "blocked_post_reentry_validation_routing"
    post_reentry_validation_target_files: list[str] = []
    post_reentry_py_compile_candidate_files: list[str] = []
    post_reentry_validation_executed = False
    post_reentry_validation_passed = False
    post_reentry_validation_failed = False
    post_reentry_validation_timeout = False
    post_reentry_py_compile_results: list[dict[str, Any]] = []
    post_reentry_cycle_status = "post_reentry_cycle_blocked"
    post_reentry_cycle_passed = False
    post_reentry_cycle_failed = False
    post_reentry_cycle_blocked = True
    post_reentry_cycle_block_reason = "blocked_insufficient_post_reentry_truth"
    continuation_candidate = False
    continuation_prompt_kind = "none"
    continuation_next_action = "manual_review_required"
    rollback_candidate = False
    rollback_reason = ""
    human_review_required = True
    manual_review_required = True
    status = "blocked_insufficient_post_reentry_truth"
    next_action = "manual_review_required"
    missing_inputs: list[str] = []

    unsafe_changes = bool(
        normalized_forbidden_changed_files
        or normalized_unexpected_changed_files
        or normalized_too_many_changed_files
    )
    routing_precedence_allowed = bool(
        normalized_source_authoritative_kind == "reentry"
        and normalized_source_authoritative_selected
        and normalized_validation_routing_candidate
        and normalized_safe_for_validation_routing
        and not normalized_source_human_review_required
    )

    if unsafe_changes:
        status = "blocked_post_reentry_unsafe_changes"
        post_reentry_cycle_status = "post_reentry_cycle_blocked_unsafe_changes"
        post_reentry_cycle_blocked = True
        post_reentry_cycle_block_reason = "unsafe_post_reentry_changes"
        rollback_candidate = True
        rollback_reason = "unsafe_post_reentry_changes"
        human_review_required = True
        manual_review_required = True
        next_action = "manual_review_required"
        post_reentry_validation_routing_block_reason = "blocked_post_reentry_unsafe_changes"
    elif normalized_source_result_class == "completed_timeout":
        status = "post_reentry_safety_refresh_invocation_timeout"
        post_reentry_cycle_status = "post_reentry_cycle_blocked_invocation_timeout"
        post_reentry_cycle_blocked = True
        post_reentry_cycle_block_reason = "post_reentry_invocation_timeout"
        rollback_candidate = True
        rollback_reason = "post_reentry_invocation_timeout"
        human_review_required = True
        manual_review_required = True
        next_action = "manual_review_required"
        post_reentry_validation_routing_block_reason = "blocked_reentry_invocation_timeout"
    elif normalized_source_result_class == "completed_failure":
        status = "post_reentry_safety_refresh_invocation_failure"
        post_reentry_cycle_status = "post_reentry_cycle_failed_invocation"
        post_reentry_cycle_failed = True
        post_reentry_cycle_blocked = False
        post_reentry_cycle_block_reason = "post_reentry_invocation_failure"
        continuation_candidate = True
        continuation_prompt_kind = "fix"
        continuation_next_action = "generate_fix_prompt"
        rollback_candidate = True
        rollback_reason = "post_reentry_invocation_failure"
        human_review_required = False
        manual_review_required = False
        next_action = "generate_fix_prompt"
        post_reentry_validation_routing_block_reason = "blocked_reentry_invocation_failure"
    elif not routing_precedence_allowed:
        status = "blocked_post_reentry_validation_routing"
        post_reentry_cycle_status = "post_reentry_cycle_blocked_validation_routing"
        post_reentry_cycle_blocked = True
        post_reentry_cycle_block_reason = (
            normalized_validation_routing_block_reason
            or "blocked_post_reentry_validation_routing"
        )
        human_review_required = bool(
            normalized_source_human_review_required
            or normalized_prompt170_compat_human_review_required
        )
        manual_review_required = bool(human_review_required)
        next_action = (
            "manual_review_required"
            if human_review_required
            else "wait_for_more_truth"
        )
        post_reentry_validation_routing_block_reason = (
            normalized_validation_routing_block_reason
            or "blocked_post_reentry_validation_routing"
        )
        if not normalized_source_authoritative_selected:
            missing_inputs.append("authoritative_source_selected")
        if normalized_source_authoritative_kind != "reentry":
            missing_inputs.append("authoritative_source_kind_reentry")
        if not normalized_validation_routing_candidate:
            missing_inputs.append("validation_routing_candidate")
        if not normalized_safe_for_validation_routing:
            missing_inputs.append("safe_for_validation_routing")
    else:
        post_reentry_validation_routing_allowed = True
        post_reentry_validation_routing_block_reason = ""
        allowed_set = set(normalized_allowed_changed_files)
        expected_set = set(normalized_expected_changed_files)
        post_reentry_validation_target_files = sorted(
            set(
                path
                for path in normalized_source_changed_files
                if path in allowed_set or path in expected_set
            )
        )
        post_reentry_py_compile_candidate_files = sorted(
            [path for path in post_reentry_validation_target_files if path.endswith(".py")]
        )
        if not post_reentry_py_compile_candidate_files:
            status = "blocked_no_post_reentry_py_compile_candidates"
            post_reentry_cycle_status = "post_reentry_cycle_blocked_no_py_compile_candidates"
            post_reentry_cycle_blocked = True
            post_reentry_cycle_block_reason = "blocked_no_post_reentry_py_compile_candidates"
            human_review_required = True
            manual_review_required = True
            next_action = "manual_review_required"
        else:
            validation_state = _build_project_browser_autonomous_post_write_validation_execution_state(
                repository_path=normalized_repository_path,
                source_routing_status="validation_routing_allowed",
                source_validation_allowed=True,
                source_validation_block_reason="",
                validation_target_files=post_reentry_validation_target_files,
                py_compile_candidate_files=post_reentry_py_compile_candidate_files,
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
            post_reentry_validation_executed = bool(
                validation_state.get(
                    "project_browser_autonomous_post_write_validation_execution_validation_executed",
                    False,
                )
            )
            post_reentry_validation_passed = bool(
                validation_state.get(
                    "project_browser_autonomous_post_write_validation_execution_validation_passed",
                    False,
                )
            )
            post_reentry_validation_failed = bool(
                validation_state.get(
                    "project_browser_autonomous_post_write_validation_execution_validation_failed",
                    False,
                )
            )
            post_reentry_validation_timeout = bool(validation_status == "validation_timeout")
            post_reentry_py_compile_results = list(
                validation_state.get(
                    "project_browser_autonomous_post_write_validation_execution_py_compile_results",
                    [],
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

            if post_reentry_validation_passed:
                status = "post_reentry_safety_refresh_validation_passed"
                post_reentry_cycle_status = "post_reentry_cycle_passed"
                post_reentry_cycle_passed = True
                post_reentry_cycle_failed = False
                post_reentry_cycle_blocked = False
                post_reentry_cycle_block_reason = ""
                continuation_candidate = True
                continuation_prompt_kind = "next"
                continuation_next_action = "prepare_bounded_continuation"
                rollback_candidate = False
                rollback_reason = ""
                human_review_required = False
                manual_review_required = False
                next_action = "prepare_bounded_continuation"
            elif post_reentry_validation_timeout:
                status = "post_reentry_safety_refresh_validation_timeout"
                post_reentry_cycle_status = "post_reentry_cycle_blocked_validation_timeout"
                post_reentry_cycle_blocked = True
                post_reentry_cycle_block_reason = "post_reentry_validation_timeout"
                continuation_candidate = False
                rollback_candidate = True
                rollback_reason = "post_reentry_validation_timeout"
                human_review_required = True
                manual_review_required = True
                next_action = "manual_review_required"
            elif post_reentry_validation_failed:
                status = "post_reentry_safety_refresh_validation_failed"
                post_reentry_cycle_status = "post_reentry_cycle_failed_validation"
                post_reentry_cycle_failed = True
                post_reentry_cycle_blocked = False
                post_reentry_cycle_block_reason = "post_reentry_validation_failed"
                continuation_candidate = True
                continuation_prompt_kind = "fix"
                continuation_next_action = "generate_fix_prompt"
                rollback_candidate = True
                rollback_reason = "post_reentry_validation_failed"
                human_review_required = False
                manual_review_required = False
                next_action = "generate_fix_prompt"
            else:
                status = "blocked_insufficient_post_reentry_truth"
                post_reentry_cycle_status = "post_reentry_cycle_blocked_insufficient_truth"
                post_reentry_cycle_blocked = True
                post_reentry_cycle_block_reason = "blocked_insufficient_post_reentry_truth"
                human_review_required = True
                manual_review_required = True
                next_action = "manual_review_required"
                missing_inputs.append("post_reentry_validation_outcome")

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if continuation_prompt_kind not in {"fix", "next", "none"}:
        continuation_prompt_kind = "none"
    if continuation_next_action not in {
        "prepare_bounded_continuation",
        "generate_fix_prompt",
        "manual_review_required",
    }:
        continuation_next_action = "manual_review_required"
    if next_action not in allowed_next_actions:
        next_action = "insufficient_truth"

    return {
        "project_browser_autonomous_post_reentry_safety_refresh_status": status,
        "project_browser_autonomous_post_reentry_safety_refresh_source_assimilation_status": (
            normalized_source_assimilation_status
        ),
        "project_browser_autonomous_post_reentry_safety_refresh_source_authoritative_kind": (
            normalized_source_authoritative_kind
        ),
        "project_browser_autonomous_post_reentry_safety_refresh_source_result_class": (
            normalized_source_result_class
        ),
        "project_browser_autonomous_post_reentry_safety_refresh_source_changed_files": (
            normalized_source_changed_files
        ),
        "project_browser_autonomous_post_reentry_safety_refresh_source_changed_files_count": int(
            normalized_source_changed_files_count
        ),
        "project_browser_autonomous_post_reentry_safety_refresh_post_reentry_validation_routing_allowed": bool(
            post_reentry_validation_routing_allowed
        ),
        "project_browser_autonomous_post_reentry_safety_refresh_post_reentry_validation_routing_block_reason": (
            post_reentry_validation_routing_block_reason
        ),
        "project_browser_autonomous_post_reentry_safety_refresh_post_reentry_validation_target_files": (
            post_reentry_validation_target_files
        ),
        "project_browser_autonomous_post_reentry_safety_refresh_post_reentry_py_compile_candidate_files": (
            post_reentry_py_compile_candidate_files
        ),
        "project_browser_autonomous_post_reentry_safety_refresh_post_reentry_validation_executed": bool(
            post_reentry_validation_executed
        ),
        "project_browser_autonomous_post_reentry_safety_refresh_post_reentry_validation_passed": bool(
            post_reentry_validation_passed
        ),
        "project_browser_autonomous_post_reentry_safety_refresh_post_reentry_validation_failed": bool(
            post_reentry_validation_failed
        ),
        "project_browser_autonomous_post_reentry_safety_refresh_post_reentry_validation_timeout": bool(
            post_reentry_validation_timeout
        ),
        "project_browser_autonomous_post_reentry_safety_refresh_post_reentry_py_compile_results": (
            post_reentry_py_compile_results
        ),
        "project_browser_autonomous_post_reentry_safety_refresh_post_reentry_cycle_status": (
            post_reentry_cycle_status
        ),
        "project_browser_autonomous_post_reentry_safety_refresh_post_reentry_cycle_passed": bool(
            post_reentry_cycle_passed
        ),
        "project_browser_autonomous_post_reentry_safety_refresh_post_reentry_cycle_failed": bool(
            post_reentry_cycle_failed
        ),
        "project_browser_autonomous_post_reentry_safety_refresh_post_reentry_cycle_blocked": bool(
            post_reentry_cycle_blocked
        ),
        "project_browser_autonomous_post_reentry_safety_refresh_post_reentry_cycle_block_reason": (
            post_reentry_cycle_block_reason
        ),
        "project_browser_autonomous_post_reentry_safety_refresh_continuation_candidate": bool(
            continuation_candidate
        ),
        "project_browser_autonomous_post_reentry_safety_refresh_continuation_prompt_kind": (
            continuation_prompt_kind
        ),
        "project_browser_autonomous_post_reentry_safety_refresh_continuation_next_action": (
            continuation_next_action
        ),
        "project_browser_autonomous_post_reentry_safety_refresh_rollback_candidate": bool(
            rollback_candidate
        ),
        "project_browser_autonomous_post_reentry_safety_refresh_rollback_reason": rollback_reason,
        "project_browser_autonomous_post_reentry_safety_refresh_manual_review_required": bool(
            manual_review_required
        ),
        "project_browser_autonomous_post_reentry_safety_refresh_human_review_required": bool(
            human_review_required
        ),
        "project_browser_autonomous_post_reentry_safety_refresh_next_action": next_action,
        "project_browser_autonomous_post_reentry_safety_refresh_runtime_posture": runtime_posture,
        "project_browser_autonomous_post_reentry_safety_refresh_missing_inputs": (
            _serialize_required_signals(
                [
                    *missing_inputs,
                    normalized_source_authoritative_block_reason,
                    normalized_prompt170_compat_source_status,
                    normalized_prompt170_compat_result_class,
                    normalized_source_next_action,
                    "prompt170_compat_safe"
                    if normalized_prompt170_compat_safe_for_validation_routing
                    else "",
                    "prompt170_compat_human_review"
                    if normalized_prompt170_compat_human_review_required
                    else "",
                    "prompt170_compat_changed_files"
                    if normalized_prompt170_compat_changed_files
                    else "",
                    normalized_source_prompt_path,
                    normalized_source_prompt_kind,
                ]
            )
        ),
    }

def _build_project_browser_autonomous_one_bounded_continuation_coordinator_state(
    *,
    final_runtime_continuation_guard_status: str,
    continuation_guard_available: bool,
    continuation_guard_allowed: bool,
    continuation_guard_block_reason: str,
    continuation_guard_source: str,
    next_control_target_kind: str,
    next_control_target_action: str,
    next_control_target_payload: Any,
    multi_cycle_handback_ready: bool,
    manual_stop_ready: bool,
    blocked_ready: bool,
    exactly_one_continuation_target: bool,
    continuation_conflict_detected: bool,
    conflicting_continuation_targets: Sequence[Any],
    controller_feedback_kind: str,
    final_step_result_kind: str,
    final_step_result_status: str,
    delegated_assimilation_status: str,
    unsafe_state_detected: bool,
    dirty_state_requires_stop: bool,
    conflict_requires_stop: bool,
    budget_guard_checked: bool,
    cycle_budget_remaining: int,
    codex_budget_remaining: int,
    rollback_budget_remaining: int,
    commit_budget_remaining: int,
    should_continue_local_loop: bool,
    should_prepare_next_controller_decision: bool,
    should_start_unbounded_loop: bool,
    should_invoke_codex: bool,
    should_execute_rollback: bool,
    should_execute_commit: bool,
    should_push: bool,
    manual_review_required: bool,
    should_stop: bool,
    stop_reason: str,
    next_action: str,
    control_dispatch_refresh_result_assimilation_status: str,
    multi_cycle_controller_status: str,
    terminal_lane_decision_status: str,
    lane_contract_guard_status: str,
    guarded_lane_dispatch_status: str,
) -> dict[str, Any]:
    allowed_statuses = {
        "one_bounded_continuation_coordinator_handback_ready",
        "one_bounded_continuation_coordinator_manual_stop",
        "one_bounded_continuation_coordinator_blocked",
        "one_bounded_continuation_coordinator_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "prepare_next_multi_cycle_decision",
        "manual_review_required",
        "insufficient_truth",
    }
    runtime_posture = [
        "prompt212_one_bounded_continuation_coordinator",
        "metadata_only",
        "one_bounded_continuation_only",
        "no_execution",
        "no_unbounded_loop",
        "no_codex_invocation",
        "no_git_mutation",
        "no_push",
    ]

    normalized_guard_status = _normalize_text(
        final_runtime_continuation_guard_status,
        default="insufficient_truth",
    )
    normalized_guard_block_reason = _normalize_text(continuation_guard_block_reason, default="")
    normalized_guard_source = _normalize_text(
        continuation_guard_source,
        default="prompt211_final_runtime_continuation_guard",
    )
    normalized_target_kind = _normalize_text(next_control_target_kind, default="")
    normalized_target_action = _normalize_text(next_control_target_action, default="")
    normalized_controller_feedback_kind = _normalize_text(controller_feedback_kind, default="")
    normalized_final_step_result_kind = _normalize_text(final_step_result_kind, default="")
    normalized_final_step_result_status = _normalize_text(final_step_result_status, default="")
    normalized_delegated_assimilation_status = _normalize_text(
        delegated_assimilation_status,
        default="",
    )
    normalized_stop_reason = _normalize_text(stop_reason, default="")
    normalized_next_action = _normalize_text(next_action, default="manual_review_required")
    normalized_refresh_result_assimilation_status = _normalize_text(
        control_dispatch_refresh_result_assimilation_status,
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
    normalized_conflicting_continuation_targets = _normalize_string_list(
        conflicting_continuation_targets
    )
    normalized_target_payload = (
        dict(next_control_target_payload)
        if isinstance(next_control_target_payload, Mapping)
        else {}
    )

    out_cycle_budget_remaining = _as_non_negative_int(cycle_budget_remaining, default=0)
    out_codex_budget_remaining = _as_non_negative_int(codex_budget_remaining, default=0)
    out_rollback_budget_remaining = _as_non_negative_int(rollback_budget_remaining, default=0)
    out_commit_budget_remaining = _as_non_negative_int(commit_budget_remaining, default=0)
    budget_checked = bool(budget_guard_checked)

    authoritative_selected = bool(
        bool(normalized_guard_status)
        and (
            bool(continuation_guard_available)
            or normalized_guard_status
            in {
                "final_runtime_continuation_guard_manual_stop",
                "final_runtime_continuation_guard_blocked",
                "final_runtime_continuation_guard_blocked_conflict",
                "final_runtime_continuation_guard_blocked_insufficient_truth",
            }
        )
        and (
            bool(normalized_target_kind)
            or normalized_guard_status
            in {
                "final_runtime_continuation_guard_manual_stop",
                "final_runtime_continuation_guard_blocked",
                "final_runtime_continuation_guard_blocked_conflict",
                "final_runtime_continuation_guard_blocked_insufficient_truth",
            }
        )
    )

    multi_cycle_handback_candidate = bool(
        bool(continuation_guard_allowed)
        and bool(multi_cycle_handback_ready)
        and normalized_target_kind == "multi_cycle_controller"
        and normalized_target_action == "prepare_next_multi_cycle_decision"
        and bool(exactly_one_continuation_target)
        and not bool(continuation_conflict_detected)
        and not bool(manual_review_required)
        and not bool(should_stop)
        and not bool(unsafe_state_detected)
        and not bool(dirty_state_requires_stop)
        and not bool(conflict_requires_stop)
        and bool(budget_checked)
        and out_cycle_budget_remaining > 0
        and not bool(should_continue_local_loop)
        and not bool(should_start_unbounded_loop)
        and not bool(should_invoke_codex)
        and not bool(should_execute_rollback)
        and not bool(should_execute_commit)
        and not bool(should_push)
    )
    manual_stop_candidate = bool(
        bool(manual_stop_ready)
        or bool(manual_review_required)
        or bool(should_stop)
    )
    blocked_candidate = bool(
        bool(blocked_ready)
        or normalized_guard_status
        in {
            "final_runtime_continuation_guard_blocked",
            "final_runtime_continuation_guard_blocked_conflict",
            "final_runtime_continuation_guard_blocked_insufficient_truth",
        }
    )

    non_stop_targets: list[str] = []
    if multi_cycle_handback_candidate:
        non_stop_targets.append("multi_cycle_controller")
    non_stop_targets = sorted(non_stop_targets)

    status = "one_bounded_continuation_coordinator_blocked_insufficient_truth"
    coordinator_available = False
    coordinator_allowed = False
    coordinator_block_reason = "blocked_insufficient_one_bounded_continuation_truth"
    coordinator_source = normalized_guard_source or "prompt211_final_runtime_continuation_guard"
    handback_kind = "blocked"
    handback_action = "manual_review_required"
    handback_payload: dict[str, Any] = {}
    one_bounded_step_ready = False
    one_bounded_step_allowed = False
    one_bounded_step_contract: dict[str, Any] = {}
    multi_cycle_controller_handback_ready = False
    manual_stop_handback_ready = False
    blocked_handback_ready = False
    exactly_one_handback_target = False
    handback_conflict_detected = False
    conflicting_handback_targets: list[str] = []
    stale_state_check_required_next = False
    fresh_execution_ordering_required_next = False
    out_should_continue_local_loop = False
    out_should_start_unbounded_loop = False
    out_should_prepare_next_controller_decision = False
    out_should_invoke_codex = False
    out_should_execute_rollback = False
    out_should_execute_commit = False
    out_should_push = False
    out_manual_review_required = True
    out_should_stop = True
    out_stop_reason = normalized_stop_reason or "insufficient_one_bounded_continuation_truth"
    out_next_action = "manual_review_required"

    if not authoritative_selected:
        status = "one_bounded_continuation_coordinator_blocked_insufficient_truth"
        coordinator_available = False
        coordinator_allowed = False
        coordinator_block_reason = "blocked_insufficient_one_bounded_continuation_truth"
        blocked_handback_ready = True
    elif manual_stop_candidate:
        status = "one_bounded_continuation_coordinator_manual_stop"
        coordinator_available = True
        coordinator_allowed = False
        coordinator_block_reason = (
            normalized_guard_block_reason or "blocked_manual_review_required"
        )
        handback_kind = "manual_stop"
        handback_action = "manual_review_required"
        handback_payload = {
            "target": "manual_stop",
            "source": "prompt212_one_bounded_continuation_coordinator",
            "stop_reason": normalized_stop_reason or "manual_stop",
            "next_action": "manual_review_required",
        }
        one_bounded_step_ready = False
        one_bounded_step_allowed = False
        manual_stop_handback_ready = True
        exactly_one_handback_target = True
        out_should_continue_local_loop = False
        out_should_start_unbounded_loop = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = normalized_stop_reason or "manual_stop"
        out_next_action = "manual_review_required"
    else:
        if not bool(continuation_guard_allowed):
            coordinator_block_reason = "blocked_continuation_guard_not_allowed"
        elif not bool(multi_cycle_handback_ready):
            coordinator_block_reason = "blocked_multi_cycle_handback_not_ready"
        elif normalized_target_kind != "multi_cycle_controller" or normalized_target_action != "prepare_next_multi_cycle_decision":
            coordinator_block_reason = "blocked_wrong_next_control_target"
        elif bool(manual_review_required):
            coordinator_block_reason = "blocked_manual_review_required"
        elif bool(should_stop):
            coordinator_block_reason = "blocked_should_stop"
        elif bool(unsafe_state_detected):
            coordinator_block_reason = "blocked_unsafe_state"
        elif bool(dirty_state_requires_stop):
            coordinator_block_reason = "blocked_dirty_state"
        elif bool(conflict_requires_stop):
            coordinator_block_reason = "blocked_conflict_state"
        elif not bool(budget_checked):
            coordinator_block_reason = "blocked_budget_not_checked"
        elif out_cycle_budget_remaining <= 0:
            coordinator_block_reason = "blocked_cycle_budget_exhausted"
        elif bool(should_continue_local_loop):
            coordinator_block_reason = "blocked_unexpected_continue_flag_from_prompt211"
        elif bool(should_start_unbounded_loop):
            coordinator_block_reason = "blocked_unexpected_unbounded_loop_flag"
        elif bool(should_invoke_codex):
            coordinator_block_reason = "blocked_unexpected_codex_invocation_flag"
        elif bool(should_execute_rollback):
            coordinator_block_reason = "blocked_unexpected_rollback_execution_flag"
        elif bool(should_execute_commit):
            coordinator_block_reason = "blocked_unexpected_commit_execution_flag"
        elif bool(should_push):
            coordinator_block_reason = "blocked_unexpected_push_flag"
        elif bool(continuation_conflict_detected):
            coordinator_block_reason = "blocked_handback_conflict"
        elif not bool(exactly_one_continuation_target):
            coordinator_block_reason = "blocked_handback_conflict"
        elif len(non_stop_targets) > 1:
            coordinator_block_reason = "blocked_handback_conflict"

        if not coordinator_block_reason and multi_cycle_handback_candidate:
            status = "one_bounded_continuation_coordinator_handback_ready"
            coordinator_available = True
            coordinator_allowed = True
            coordinator_block_reason = ""
            coordinator_source = "prompt211_final_runtime_continuation_guard"
            handback_kind = "multi_cycle_controller"
            handback_action = "prepare_next_multi_cycle_decision"
            handback_payload = (
                dict(normalized_target_payload) if normalized_target_payload else {}
            )
            multi_cycle_controller_handback_ready = True
            exactly_one_handback_target = True
            one_bounded_step_ready = True
            one_bounded_step_allowed = True
            stale_state_check_required_next = True
            fresh_execution_ordering_required_next = True
            one_bounded_step_contract = {
                "contract_kind": "one_bounded_local_continuation",
                "source": "prompt212_one_bounded_continuation_coordinator",
                "handback_kind": "multi_cycle_controller",
                "handback_action": "prepare_next_multi_cycle_decision",
                "max_next_steps": 1,
                "allow_unbounded_loop": False,
                "requires_stale_state_check": True,
                "requires_fresh_execution_ordering_guard": True,
                "cycle_budget_remaining": out_cycle_budget_remaining,
                "codex_budget_remaining": out_codex_budget_remaining,
                "rollback_budget_remaining": out_rollback_budget_remaining,
                "commit_budget_remaining": out_commit_budget_remaining,
                "next_action": "prepare_next_multi_cycle_decision",
            }
            out_should_continue_local_loop = True
            out_should_start_unbounded_loop = False
            out_should_prepare_next_controller_decision = True
            out_manual_review_required = False
            out_should_stop = False
            out_stop_reason = ""
            out_next_action = "prepare_next_multi_cycle_decision"
        else:
            status = "one_bounded_continuation_coordinator_blocked"
            coordinator_available = True
            coordinator_allowed = False
            coordinator_block_reason = (
                coordinator_block_reason
                or "blocked_insufficient_one_bounded_continuation_truth"
            )
            handback_kind = "blocked"
            handback_action = "manual_review_required"
            handback_payload = {
                "target": "manual_stop",
                "source": "prompt212_one_bounded_continuation_coordinator",
                "stop_reason": coordinator_block_reason,
                "next_action": "manual_review_required",
            }
            blocked_handback_ready = True
            exactly_one_handback_target = True
            out_should_continue_local_loop = False
            out_should_start_unbounded_loop = False
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = coordinator_block_reason
            out_next_action = "manual_review_required"

    if bool(continuation_conflict_detected) or len(non_stop_targets) > 1:
        handback_conflict_detected = True
        conflicting_handback_targets = _normalize_string_list(
            non_stop_targets + normalized_conflicting_continuation_targets
        )
        if status == "one_bounded_continuation_coordinator_handback_ready":
            status = "one_bounded_continuation_coordinator_blocked"
            coordinator_allowed = False
            coordinator_block_reason = "blocked_handback_conflict"
            one_bounded_step_ready = False
            one_bounded_step_allowed = False
            one_bounded_step_contract = {}
            multi_cycle_controller_handback_ready = False
            blocked_handback_ready = True
            out_should_continue_local_loop = False
            out_should_start_unbounded_loop = False
            out_should_prepare_next_controller_decision = False
            out_manual_review_required = True
            out_should_stop = True
            out_stop_reason = "conflicting_handback_targets"
            out_next_action = "manual_review_required"

    if status not in allowed_statuses:
        status = "insufficient_truth"
    if out_next_action not in allowed_next_actions:
        out_next_action = "insufficient_truth"
    if status == "insufficient_truth":
        status = "one_bounded_continuation_coordinator_blocked_insufficient_truth"
        coordinator_available = False
        coordinator_allowed = False
        coordinator_block_reason = "blocked_insufficient_one_bounded_continuation_truth"
        handback_kind = "blocked"
        handback_action = "manual_review_required"
        handback_payload = {}
        one_bounded_step_ready = False
        one_bounded_step_allowed = False
        one_bounded_step_contract = {}
        multi_cycle_controller_handback_ready = False
        manual_stop_handback_ready = False
        blocked_handback_ready = True
        exactly_one_handback_target = False
        handback_conflict_detected = False
        conflicting_handback_targets = []
        stale_state_check_required_next = False
        fresh_execution_ordering_required_next = False
        out_should_continue_local_loop = False
        out_should_start_unbounded_loop = False
        out_should_prepare_next_controller_decision = False
        out_should_invoke_codex = False
        out_should_execute_rollback = False
        out_should_execute_commit = False
        out_should_push = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_one_bounded_continuation_truth"
        out_next_action = "manual_review_required"

    return {
        "project_browser_autonomous_one_bounded_continuation_coordinator_status": status,
        "project_browser_autonomous_one_bounded_continuation_coordinator_coordinator_available": bool(
            coordinator_available
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_coordinator_allowed": bool(
            coordinator_allowed
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_coordinator_block_reason": (
            coordinator_block_reason
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_coordinator_source": (
            coordinator_source
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_handback_kind": (
            handback_kind
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_handback_action": (
            handback_action
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_handback_payload": (
            handback_payload if isinstance(handback_payload, Mapping) else {}
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_one_bounded_step_ready": bool(
            one_bounded_step_ready
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_one_bounded_step_allowed": bool(
            one_bounded_step_allowed
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_one_bounded_step_contract": (
            one_bounded_step_contract
            if isinstance(one_bounded_step_contract, Mapping)
            else {}
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_multi_cycle_controller_handback_ready": bool(
            multi_cycle_controller_handback_ready
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_manual_stop_handback_ready": bool(
            manual_stop_handback_ready
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_blocked_handback_ready": bool(
            blocked_handback_ready
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_exactly_one_handback_target": bool(
            exactly_one_handback_target
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_handback_conflict_detected": bool(
            handback_conflict_detected
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_conflicting_handback_targets": (
            conflicting_handback_targets
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_budget_checked": bool(
            budget_checked
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_cycle_budget_remaining": int(
            out_cycle_budget_remaining
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_codex_budget_remaining": int(
            out_codex_budget_remaining
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_rollback_budget_remaining": int(
            out_rollback_budget_remaining
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_commit_budget_remaining": int(
            out_commit_budget_remaining
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_stale_state_check_required_next": bool(
            stale_state_check_required_next
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_fresh_execution_ordering_required_next": bool(
            fresh_execution_ordering_required_next
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_should_continue_local_loop": bool(
            out_should_continue_local_loop
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_should_start_unbounded_loop": bool(
            out_should_start_unbounded_loop
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_should_prepare_next_controller_decision": bool(
            out_should_prepare_next_controller_decision
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_should_invoke_codex": bool(
            out_should_invoke_codex
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_should_execute_rollback": bool(
            out_should_execute_rollback
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_should_execute_commit": bool(
            out_should_execute_commit
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_should_push": bool(
            out_should_push
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_manual_review_required": bool(
            out_manual_review_required
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_should_stop": bool(
            out_should_stop
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_stop_reason": (
            out_stop_reason
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_next_action": (
            out_next_action
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_one_bounded_continuation_coordinator_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_guard_status,
                    normalized_guard_block_reason,
                    normalized_guard_source,
                    normalized_target_kind,
                    normalized_target_action,
                    normalized_controller_feedback_kind,
                    normalized_final_step_result_kind,
                    normalized_final_step_result_status,
                    normalized_delegated_assimilation_status,
                    normalized_stop_reason,
                    normalized_next_action,
                    normalized_refresh_result_assimilation_status,
                    normalized_multi_cycle_controller_status,
                    normalized_terminal_lane_decision_status,
                    normalized_lane_contract_guard_status,
                    normalized_guarded_lane_dispatch_status,
                    "authoritative_guard_missing" if not authoritative_selected else "",
                    "continuation_conflict_detected" if bool(continuation_conflict_detected) else "",
                    "unexpected_continue_flag_from_prompt211"
                    if bool(should_continue_local_loop)
                    else "",
                ]
            )
        ),
    }

def _build_project_browser_autonomous_bounded_continuation_decision_state(
    *,
    bounded_multistep_execution_result_assimilation_status: str,
    result_selected: bool,
    result_available: bool,
    result_class: str,
    result_block_reason: str,
    source_selected_action_kind: str,
    source_selected_action_action: str,
    source_execution_status: str,
    source_execution_attempted: bool,
    source_execution_completed: bool,
    source_execution_failed: bool,
    non_selected_actions_noop_confirmed: bool,
    delegated_existing_path_kind: str,
    delegated_existing_status: str,
    delegated_existing_next_action: str,
    delegated_existing_attempted: bool,
    delegated_existing_completed: bool,
    fresh_bounded_action_detected: bool,
    existing_truth_revalidated_detected: bool,
    existing_truth_revalidation_failed_detected: bool,
    existing_path_blocked_detected: bool,
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
    should_prepare_next_multistep_decision: bool,
    should_prepare_result_assimilation_chain: bool,
    should_prepare_manual_review: bool,
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
    bounded_multistep_execution_coordinator_status: str,
    bounded_multistep_handoff_guard_status: str,
    direct_retrigger_followup_guard_status: str,
    direct_retrigger_result_assimilation_status: str,
    direct_retrigger_coordinator_status: str,
    multi_cycle_controller_status: str,
    cycle_budget_remaining: int,
    codex_budget_remaining: int,
    rollback_budget_remaining: int,
    commit_budget_remaining: int,
    budget_checked: bool,
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
        "bounded_continuation_decision_n_step_ready",
        "bounded_continuation_decision_result_assimilation_ready",
        "bounded_continuation_decision_manual_stop",
        "bounded_continuation_decision_blocked",
        "bounded_continuation_decision_blocked_conflict",
        "bounded_continuation_decision_blocked_insufficient_truth",
        "insufficient_truth",
    }
    allowed_next_actions = {
        "prepare_bounded_n_step_coordinator",
        "prepare_result_assimilation_chain",
        "manual_review_required",
        "insufficient_truth",
    }
    runtime_posture = [
        "prompt220_bounded_continuation_decision",
        "metadata_only",
        "bounded_continuation_decision_only",
        "no_execution",
        "no_retry",
        "no_loop",
        "no_codex_invocation",
        "no_rollback_execution",
        "no_commit_execution",
        "no_push",
    ]

    normalized_status = _normalize_text(
        bounded_multistep_execution_result_assimilation_status,
        default="insufficient_truth",
    )
    normalized_result_class = _normalize_text(result_class, default="insufficient_truth")
    normalized_result_block_reason = _normalize_text(result_block_reason, default="")
    normalized_source_selected_action_kind = _normalize_text(
        source_selected_action_kind,
        default="",
    )
    normalized_source_selected_action_action = _normalize_text(
        source_selected_action_action,
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
        default="",
    )
    normalized_delegated_existing_next_action = _normalize_text(
        delegated_existing_next_action,
        default="",
    )
    normalized_terminal_result_source = _normalize_text(terminal_result_source, default="")
    normalized_controller_feedback_kind = _normalize_text(
        controller_feedback_kind,
        default="none",
    )
    normalized_controller_feedback_source = _normalize_text(
        controller_feedback_source,
        default="",
    )
    normalized_next_target_kind = _normalize_text(next_bounded_control_target_kind, default="")
    normalized_next_target_action = _normalize_text(
        next_bounded_control_target_action,
        default="",
    )
    normalized_source_stop_reason = _normalize_text(source_stop_reason, default="")
    normalized_source_next_action = _normalize_text(source_next_action, default="")
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
    normalized_direct_retrigger_coordinator_status = _normalize_text(
        direct_retrigger_coordinator_status,
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
    normalized_controller_feedback_payload = (
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
    out_rollback_budget_remaining = _as_non_negative_int(
        rollback_budget_remaining,
        default=0,
    )
    out_commit_budget_remaining = _as_non_negative_int(commit_budget_remaining, default=0)
    out_budget_checked = bool(budget_checked)

    status_is_manual = normalized_status == "bounded_multistep_execution_result_manual_stop"
    status_is_blocked = "blocked" in normalized_status
    status_is_failed = normalized_status == "bounded_multistep_execution_result_failed"
    status_is_insufficient = normalized_status in {
        "bounded_multistep_execution_result_blocked_insufficient_truth",
        "insufficient_truth",
    }

    authoritative_selected = bool(
        bool(normalized_status)
        and bool(normalized_result_class)
        and (
            normalized_controller_feedback_source
            == "prompt218_bounded_multistep_execution_coordinator"
            or status_is_manual
            or status_is_blocked
            or status_is_failed
            or status_is_insufficient
        )
        and (
            bool(normalized_source_selected_action_kind)
            or status_is_manual
            or status_is_blocked
            or status_is_failed
            or status_is_insufficient
        )
    )

    bounded_n_step_candidate = bool(
        normalized_result_class
        in {"completed_fresh_action", "completed_existing_truth_revalidated"}
        and bool(next_bounded_control_target_ready)
        and normalized_next_target_kind == "bounded_next_step_decision"
        and normalized_next_target_action == "prepare_bounded_next_step_decision"
        and bool(controller_feedback_ready)
        and bool(terminal_result_detected)
        and bool(non_selected_actions_noop_confirmed)
        and not bool(source_manual_review_required)
        and not bool(source_should_stop)
        and not bool(source_should_continue_local_loop)
        and not bool(source_should_start_unbounded_loop)
        and not bool(source_should_push)
    )
    result_assimilation_chain_candidate = bool(
        bool(should_prepare_result_assimilation_chain)
        and normalized_result_class
        in {"completed_fresh_action", "completed_existing_truth_revalidated"}
        and bool(controller_feedback_ready)
        and not bool(source_manual_review_required)
        and not bool(source_should_stop)
    )
    manual_stop_candidate = bool(
        normalized_result_class == "manual_stop"
        or bool(should_prepare_manual_review)
        or bool(source_manual_review_required)
        or bool(source_should_stop)
        or status_is_manual
    )
    blocked_candidate = bool(
        normalized_result_class
        in {
            "blocked_existing_truth_revalidation",
            "blocked_existing_path",
            "blocked_non_selected_action_activity",
            "failed",
            "blocked",
            "insufficient_truth",
        }
        or bool(existing_truth_revalidation_failed_detected)
        or bool(existing_path_blocked_detected)
        or status_is_blocked
        or status_is_failed
        or status_is_insufficient
    )

    existing_truth_requires_guarded_continuation = bool(
        normalized_result_class == "completed_existing_truth_revalidated"
        and bool(existing_truth_revalidated_detected)
    )
    n_step_continuation_confidence = "none"
    if normalized_result_class == "completed_fresh_action":
        n_step_continuation_confidence = "high"
    elif normalized_result_class == "completed_existing_truth_revalidated":
        n_step_continuation_confidence = "guarded"

    non_stop_targets: list[str] = []
    if bounded_n_step_candidate:
        non_stop_targets.append("bounded_n_step_coordinator")
    if result_assimilation_chain_candidate:
        non_stop_targets.append("result_assimilation_chain")

    conflict_detected = len(non_stop_targets) > 1
    conflict_targets = _normalize_string_list(sorted(non_stop_targets))

    blocked_reason = _first_true_reason(
        [
            (not authoritative_selected, "blocked_prompt219_not_authoritative"),
            (bool(source_manual_review_required), "blocked_manual_review_required"),
            (bool(source_should_stop), "blocked_should_stop"),
            (
                bool(existing_truth_revalidation_failed_detected),
                "blocked_existing_truth_revalidation",
            ),
            (bool(existing_path_blocked_detected), "blocked_existing_path"),
            (
                normalized_result_class == "blocked_non_selected_action_activity",
                "blocked_non_selected_action_activity",
            ),
            (normalized_result_class == "failed", "blocked_result_failed"),
            (normalized_result_class == "blocked", "blocked_result_blocked"),
            (
                bool(source_should_start_unbounded_loop),
                "blocked_unbounded_loop_requested",
            ),
            (
                "retry" in normalized_source_next_action
                or "retry" in normalized_source_execution_status,
                "blocked_retry_requested",
            ),
            (bool(source_should_continue_local_loop), "blocked_unexpected_continue_flag"),
            (bool(source_should_push), "blocked_unexpected_push_flag"),
            (conflict_detected, "blocked_continuation_conflict"),
        ],
        default="blocked_insufficient_bounded_continuation_truth",
    )

    out_status = "bounded_continuation_decision_blocked_insufficient_truth"
    continuation_decision_available = False
    continuation_decision_allowed = False
    continuation_decision_block_reason = "blocked_insufficient_bounded_continuation_truth"
    continuation_decision_source = "prompt219_bounded_multistep_execution_result_assimilation"
    selected_continuation_kind = "blocked"
    selected_continuation_action = "manual_review_required"
    selected_continuation_payload: dict[str, Any] = {}
    exactly_one_continuation_target = False
    continuation_conflict_detected = False
    conflicting_continuation_targets: list[str] = []
    max_continuation_steps = 0
    allow_unbounded_loop = False
    allow_retry = False
    requires_stop_policy_guard = False
    requires_budget_guard = False
    requires_result_assimilation = False
    prompt221_n_step_ready = False
    prompt221_n_step_source = ""
    prompt221_n_step_contract: dict[str, Any] = {}
    out_should_continue_local_loop = False
    out_should_start_unbounded_loop = False
    out_should_invoke_codex = False
    out_should_execute_rollback = False
    out_should_execute_commit = False
    out_should_push = False
    out_manual_review_required = True
    out_should_stop = True
    out_stop_reason = normalized_source_stop_reason or "insufficient_bounded_continuation_truth"
    out_next_action = "manual_review_required"

    if not authoritative_selected:
        out_status = "bounded_continuation_decision_blocked_insufficient_truth"
        continuation_decision_available = False
        continuation_decision_allowed = False
        continuation_decision_block_reason = "blocked_prompt219_not_authoritative"
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_bounded_continuation_truth"
    elif manual_stop_candidate:
        out_status = "bounded_continuation_decision_manual_stop"
        continuation_decision_available = True
        continuation_decision_allowed = False
        continuation_decision_block_reason = (
            blocked_reason if blocked_reason else "blocked_manual_review_required"
        )
        selected_continuation_kind = "manual_stop"
        selected_continuation_action = "manual_review_required"
        selected_continuation_payload = {
            "target": "manual_stop",
            "source": "prompt220_bounded_continuation_decision",
            "stop_reason": normalized_source_stop_reason or "manual_stop",
            "next_action": "manual_review_required",
        }
        exactly_one_continuation_target = True
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = normalized_source_stop_reason or "manual_stop"
        out_next_action = "manual_review_required"
    elif blocked_candidate:
        out_status = "bounded_continuation_decision_blocked"
        continuation_decision_available = True
        continuation_decision_allowed = False
        continuation_decision_block_reason = blocked_reason
        selected_continuation_kind = "blocked"
        selected_continuation_action = "manual_review_required"
        selected_continuation_payload = {
            "target": "blocked",
            "source": "prompt220_bounded_continuation_decision",
            "stop_reason": normalized_source_stop_reason
            or normalized_result_block_reason
            or "bounded_continuation_not_safe",
            "next_action": "manual_review_required",
        }
        exactly_one_continuation_target = True
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = (
            normalized_source_stop_reason
            or normalized_result_block_reason
            or "bounded_continuation_not_safe"
        )
        out_next_action = "manual_review_required"
    elif conflict_detected:
        out_status = "bounded_continuation_decision_blocked_conflict"
        continuation_decision_available = True
        continuation_decision_allowed = False
        continuation_decision_block_reason = "blocked_continuation_conflict"
        selected_continuation_kind = "blocked"
        selected_continuation_action = "manual_review_required"
        selected_continuation_payload = {
            "target": "blocked",
            "source": "prompt220_bounded_continuation_decision",
            "stop_reason": "conflicting_bounded_continuation_targets",
            "next_action": "manual_review_required",
        }
        exactly_one_continuation_target = False
        continuation_conflict_detected = True
        conflicting_continuation_targets = conflict_targets
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "conflicting_bounded_continuation_targets"
        out_next_action = "manual_review_required"
    elif bounded_n_step_candidate:
        out_status = "bounded_continuation_decision_n_step_ready"
        continuation_decision_available = True
        continuation_decision_allowed = True
        continuation_decision_block_reason = ""
        continuation_decision_source = "prompt219_bounded_multistep_execution_result_assimilation"
        selected_continuation_kind = "bounded_n_step_coordinator"
        selected_continuation_action = "prepare_bounded_n_step_coordinator"
        selected_continuation_payload = {
            "target": "bounded_n_step_coordinator",
            "source": "prompt220_bounded_continuation_decision",
            "next_action": "prepare_bounded_n_step_coordinator",
        }
        exactly_one_continuation_target = True
        max_continuation_steps = 1
        allow_unbounded_loop = False
        allow_retry = False
        requires_stop_policy_guard = True
        requires_budget_guard = True
        requires_result_assimilation = True
        prompt221_n_step_ready = True
        prompt221_n_step_source = "prompt220_bounded_continuation_decision"
        prompt221_n_step_contract = {
            "contract_kind": "bounded_n_step_preflight",
            "source": "prompt220_bounded_continuation_decision",
            "selected_continuation_kind": "bounded_n_step_coordinator",
            "source_result_class": normalized_result_class,
            "source_selected_action_kind": normalized_source_selected_action_kind,
            "fresh_bounded_action_detected": bool(fresh_bounded_action_detected),
            "existing_truth_revalidated_detected": bool(
                existing_truth_revalidated_detected
            ),
            "existing_truth_requires_guarded_continuation": bool(
                existing_truth_requires_guarded_continuation
            ),
            "n_step_continuation_confidence": n_step_continuation_confidence,
            "max_continuation_steps": max_continuation_steps,
            "allow_unbounded_loop": False,
            "allow_retry": False,
            "requires_stop_policy_guard": True,
            "requires_budget_guard": True,
            "requires_result_assimilation": True,
            "next_action": "prepare_bounded_n_step_coordinator",
        }
        out_manual_review_required = False
        out_should_stop = False
        out_stop_reason = ""
        out_next_action = "prepare_bounded_n_step_coordinator"
    elif result_assimilation_chain_candidate:
        out_status = "bounded_continuation_decision_result_assimilation_ready"
        continuation_decision_available = True
        continuation_decision_allowed = True
        continuation_decision_block_reason = ""
        continuation_decision_source = "prompt219_bounded_multistep_execution_result_assimilation"
        selected_continuation_kind = "result_assimilation_chain"
        selected_continuation_action = "prepare_result_assimilation_chain"
        selected_continuation_payload = {
            "target": "result_assimilation_chain",
            "source": "prompt220_bounded_continuation_decision",
            "next_action": "prepare_result_assimilation_chain",
        }
        exactly_one_continuation_target = True
        out_manual_review_required = False
        out_should_stop = False
        out_stop_reason = ""
        out_next_action = "prepare_result_assimilation_chain"
    else:
        out_status = "bounded_continuation_decision_blocked_insufficient_truth"
        continuation_decision_available = False
        continuation_decision_allowed = False
        continuation_decision_block_reason = "blocked_insufficient_bounded_continuation_truth"
        selected_continuation_kind = "blocked"
        selected_continuation_action = "manual_review_required"
        selected_continuation_payload = {
            "target": "blocked",
            "source": "prompt220_bounded_continuation_decision",
            "stop_reason": "insufficient_bounded_continuation_truth",
            "next_action": "manual_review_required",
        }
        exactly_one_continuation_target = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_bounded_continuation_truth"
        out_next_action = "manual_review_required"

    if out_status not in allowed_statuses:
        out_status = "insufficient_truth"
    if out_next_action not in allowed_next_actions:
        out_next_action = "insufficient_truth"
    if out_status == "insufficient_truth":
        out_status = "bounded_continuation_decision_blocked_insufficient_truth"
        continuation_decision_available = False
        continuation_decision_allowed = False
        continuation_decision_block_reason = "blocked_insufficient_bounded_continuation_truth"
        selected_continuation_kind = "blocked"
        selected_continuation_action = "manual_review_required"
        selected_continuation_payload = {}
        exactly_one_continuation_target = False
        continuation_conflict_detected = False
        conflicting_continuation_targets = []
        bounded_n_step_candidate = False
        result_assimilation_chain_candidate = False
        manual_stop_candidate = False
        blocked_candidate = True
        n_step_continuation_confidence = "none"
        max_continuation_steps = 0
        allow_unbounded_loop = False
        allow_retry = False
        requires_stop_policy_guard = False
        requires_budget_guard = False
        requires_result_assimilation = False
        prompt221_n_step_ready = False
        prompt221_n_step_source = ""
        prompt221_n_step_contract = {}
        out_should_continue_local_loop = False
        out_should_start_unbounded_loop = False
        out_should_invoke_codex = False
        out_should_execute_rollback = False
        out_should_execute_commit = False
        out_should_push = False
        out_manual_review_required = True
        out_should_stop = True
        out_stop_reason = "insufficient_bounded_continuation_truth"
        out_next_action = "manual_review_required"

    return {
        "project_browser_autonomous_bounded_continuation_decision_status": out_status,
        "project_browser_autonomous_bounded_continuation_decision_continuation_decision_available": bool(
            continuation_decision_available
        ),
        "project_browser_autonomous_bounded_continuation_decision_continuation_decision_allowed": bool(
            continuation_decision_allowed
        ),
        "project_browser_autonomous_bounded_continuation_decision_continuation_decision_block_reason": (
            continuation_decision_block_reason
        ),
        "project_browser_autonomous_bounded_continuation_decision_continuation_decision_source": (
            continuation_decision_source
        ),
        "project_browser_autonomous_bounded_continuation_decision_selected_continuation_kind": (
            selected_continuation_kind
        ),
        "project_browser_autonomous_bounded_continuation_decision_selected_continuation_action": (
            selected_continuation_action
        ),
        "project_browser_autonomous_bounded_continuation_decision_selected_continuation_payload": (
            selected_continuation_payload if isinstance(selected_continuation_payload, Mapping) else {}
        ),
        "project_browser_autonomous_bounded_continuation_decision_exactly_one_continuation_target": bool(
            exactly_one_continuation_target
        ),
        "project_browser_autonomous_bounded_continuation_decision_continuation_conflict_detected": bool(
            continuation_conflict_detected
        ),
        "project_browser_autonomous_bounded_continuation_decision_conflicting_continuation_targets": (
            _normalize_string_list(conflicting_continuation_targets)
        ),
        "project_browser_autonomous_bounded_continuation_decision_bounded_n_step_candidate": bool(
            bounded_n_step_candidate
        ),
        "project_browser_autonomous_bounded_continuation_decision_result_assimilation_chain_candidate": bool(
            result_assimilation_chain_candidate
        ),
        "project_browser_autonomous_bounded_continuation_decision_manual_stop_candidate": bool(
            manual_stop_candidate
        ),
        "project_browser_autonomous_bounded_continuation_decision_blocked_candidate": bool(
            blocked_candidate
        ),
        "project_browser_autonomous_bounded_continuation_decision_source_result_class": (
            normalized_result_class
        ),
        "project_browser_autonomous_bounded_continuation_decision_source_selected_action_kind": (
            normalized_source_selected_action_kind
        ),
        "project_browser_autonomous_bounded_continuation_decision_source_execution_status": (
            normalized_source_execution_status
        ),
        "project_browser_autonomous_bounded_continuation_decision_fresh_bounded_action_detected": bool(
            fresh_bounded_action_detected
        ),
        "project_browser_autonomous_bounded_continuation_decision_existing_truth_revalidated_detected": bool(
            existing_truth_revalidated_detected
        ),
        "project_browser_autonomous_bounded_continuation_decision_existing_truth_requires_guarded_continuation": bool(
            existing_truth_requires_guarded_continuation
        ),
        "project_browser_autonomous_bounded_continuation_decision_terminal_result_detected": bool(
            terminal_result_detected
        ),
        "project_browser_autonomous_bounded_continuation_decision_terminal_result_source": (
            normalized_terminal_result_source
        ),
        "project_browser_autonomous_bounded_continuation_decision_n_step_continuation_confidence": (
            n_step_continuation_confidence
        ),
        "project_browser_autonomous_bounded_continuation_decision_max_continuation_steps": int(
            max_continuation_steps
        ),
        "project_browser_autonomous_bounded_continuation_decision_allow_unbounded_loop": bool(
            allow_unbounded_loop
        ),
        "project_browser_autonomous_bounded_continuation_decision_allow_retry": bool(
            allow_retry
        ),
        "project_browser_autonomous_bounded_continuation_decision_requires_stop_policy_guard": bool(
            requires_stop_policy_guard
        ),
        "project_browser_autonomous_bounded_continuation_decision_requires_budget_guard": bool(
            requires_budget_guard
        ),
        "project_browser_autonomous_bounded_continuation_decision_requires_result_assimilation": bool(
            requires_result_assimilation
        ),
        "project_browser_autonomous_bounded_continuation_decision_cycle_budget_remaining": int(
            out_cycle_budget_remaining
        ),
        "project_browser_autonomous_bounded_continuation_decision_codex_budget_remaining": int(
            out_codex_budget_remaining
        ),
        "project_browser_autonomous_bounded_continuation_decision_rollback_budget_remaining": int(
            out_rollback_budget_remaining
        ),
        "project_browser_autonomous_bounded_continuation_decision_commit_budget_remaining": int(
            out_commit_budget_remaining
        ),
        "project_browser_autonomous_bounded_continuation_decision_budget_checked": bool(
            out_budget_checked
        ),
        "project_browser_autonomous_bounded_continuation_decision_prompt221_n_step_ready": bool(
            prompt221_n_step_ready
        ),
        "project_browser_autonomous_bounded_continuation_decision_prompt221_n_step_source": (
            prompt221_n_step_source
        ),
        "project_browser_autonomous_bounded_continuation_decision_prompt221_n_step_contract": (
            prompt221_n_step_contract if isinstance(prompt221_n_step_contract, Mapping) else {}
        ),
        "project_browser_autonomous_bounded_continuation_decision_should_continue_local_loop": bool(
            out_should_continue_local_loop
        ),
        "project_browser_autonomous_bounded_continuation_decision_should_start_unbounded_loop": bool(
            out_should_start_unbounded_loop
        ),
        "project_browser_autonomous_bounded_continuation_decision_should_invoke_codex": bool(
            out_should_invoke_codex
        ),
        "project_browser_autonomous_bounded_continuation_decision_should_execute_rollback": bool(
            out_should_execute_rollback
        ),
        "project_browser_autonomous_bounded_continuation_decision_should_execute_commit": bool(
            out_should_execute_commit
        ),
        "project_browser_autonomous_bounded_continuation_decision_should_push": bool(
            out_should_push
        ),
        "project_browser_autonomous_bounded_continuation_decision_manual_review_required": bool(
            out_manual_review_required
        ),
        "project_browser_autonomous_bounded_continuation_decision_should_stop": bool(
            out_should_stop
        ),
        "project_browser_autonomous_bounded_continuation_decision_stop_reason": (
            out_stop_reason
        ),
        "project_browser_autonomous_bounded_continuation_decision_next_action": (
            out_next_action
        ),
        "project_browser_autonomous_bounded_continuation_decision_runtime_posture": (
            runtime_posture
        ),
        "project_browser_autonomous_bounded_continuation_decision_missing_inputs": (
            _serialize_required_signals(
                [
                    normalized_status,
                    normalized_result_class,
                    normalized_result_block_reason,
                    normalized_source_selected_action_kind,
                    normalized_source_selected_action_action,
                    normalized_source_execution_status,
                    normalized_delegated_existing_path_kind,
                    normalized_delegated_existing_status,
                    normalized_delegated_existing_next_action,
                    normalized_terminal_result_source,
                    normalized_controller_feedback_kind,
                    normalized_controller_feedback_source,
                    normalized_next_target_kind,
                    normalized_next_target_action,
                    normalized_source_stop_reason,
                    normalized_source_next_action,
                    normalized_execution_coordinator_status,
                    normalized_handoff_guard_status,
                    normalized_direct_retrigger_followup_guard_status,
                    normalized_direct_retrigger_result_assimilation_status,
                    normalized_direct_retrigger_coordinator_status,
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
                    "prompt219_not_authoritative" if not authoritative_selected else "",
                    "source_result_not_selected" if not bool(result_selected) else "",
                    "source_result_not_available" if not bool(result_available) else "",
                    "source_execution_not_attempted"
                    if not bool(source_execution_attempted)
                    else "",
                    "source_execution_not_completed"
                    if not bool(source_execution_completed)
                    else "",
                    "source_execution_failed" if bool(source_execution_failed) else "",
                    "non_selected_actions_not_noop"
                    if not bool(non_selected_actions_noop_confirmed)
                    else "",
                    "delegated_existing_not_attempted"
                    if not bool(delegated_existing_attempted)
                    else "",
                    "delegated_existing_not_completed"
                    if not bool(delegated_existing_completed)
                    else "",
                    "existing_truth_revalidation_failed"
                    if bool(existing_truth_revalidation_failed_detected)
                    else "",
                    "existing_path_blocked_detected"
                    if bool(existing_path_blocked_detected)
                    else "",
                    "feedback_payload_missing"
                    if bool(controller_feedback_ready)
                    and not normalized_controller_feedback_payload
                    else "",
                    "next_target_payload_missing"
                    if bool(next_bounded_control_target_ready)
                    and not normalized_next_target_payload
                    else "",
                    "should_prepare_next_multistep_decision_false"
                    if not bool(should_prepare_next_multistep_decision)
                    else "",
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

# Imported after definitions to avoid circular import edges between split builder modules.
from automation.orchestration.planned_runner.project_browser.local_loop_state import (
    _build_project_browser_autonomous_post_write_validation_execution_state,
)

__all__ = [
    "_build_project_browser_autonomous_resume_watchdog_state",
    "_build_project_browser_autonomous_post_reentry_safety_refresh_state",
    "_build_project_browser_autonomous_one_bounded_continuation_coordinator_state",
    "_build_project_browser_autonomous_bounded_continuation_decision_state",
]
